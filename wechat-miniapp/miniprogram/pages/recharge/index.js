const member = require('../../services/member');
const context = require('../../services/context');
const pending = require('../../store/pending');
const money = require('../../utils/money');
const companyUtil = require('../../utils/company');
const time = require('../../utils/time');
const theme = require('../../utils/theme');

const STATUS = {
  awaiting_operator: '待商家核对 · 余额未变化',
  awaiting_consumer: '商家已入账 · 待我核对归档',
  completed: '双方已完成',
  declined: '商家未确认收款',
  cancelled: '已取消',
  expired: '已过期',
};

function statusText(card) {
  if (card.type === 'charge' && card.status === 'awaiting_consumer') {
    return '商家请求扣费 · 待我确认';
  }
  if (card.type === 'charge' && card.status === 'completed') {
    return card.settlement_method === 'operator_wallet'
      ? '商家直接扣款 · 双方收据已生成'
      : '扣费已确认完成';
  }
  if (card.type === 'charge' && card.status === 'declined') {
    return '我已拒绝扣费';
  }
  return STATUS[card.status] || card.status;
}

const EVENT = {
  'member.recharge.requested': '用户建立充值卡',
  'member.recharge.operator_issued': '商家为会员建立充值卡',
  'member.recharge.operator_confirmed': '商家确认已收款',
  'member.recharge.credited': '系统写入会员余额',
  'member.transaction.consumer_acknowledged': '用户确认已入账',
  'member.recharge.declined': '商家拒绝充值卡',
  'member.transaction.consumer_cancelled': '用户取消充值卡',
  'member.charge.requested': '商家发出扣费卡',
  'member.charge.consumer_confirmed': '用户确认扣费',
  'member.charge.debited': '系统扣除会员余额',
  'member.charge.consumer_declined': '用户拒绝扣费',
  'member.gift_card.claimed': '用户领取一次性礼品卡',
  'member.gift_card.credited': '系统写入礼品卡余额',
};

Page({
  submitInFlight: false,
  data: {
    presets: [100, 300, 500, 1000],
    selected: 300,
    custom: '',
    busy: false,
    contextLoading: true,
    error: '',
    companyCode: '',
    companyName: '',
    companyMode: '',
    companyCurrency: 'CNY',
    cards: [],
  },
  onShow() { this.loadContext(); },
  async loadContext() {
    try {
      this.setData({ contextLoading: true, error: '' });
      const selected = await context.requireCompany();
      if (!selected) {
        this.setData({ contextLoading: false, companyCode: '' });
        return;
      }
      this.setData({
        contextLoading: false,
        companyCode: selected.code,
        companyName: selected.company.name,
        companyMode: companyUtil.modeLabel(selected.company),
        companyCurrency: selected.company.currency || selected.account.currency || 'CNY',
      });
      await this.loadCards(selected.code);
    } catch (error) {
      this.setData({ contextLoading: false, error: error.message || '无法读取公司' });
    }
  },
  async loadCards(companyCode) {
    const result = await member.transactionCards(companyCode);
    const cards = (result.cards || []).map((card) => ({
      ...card,
      amountText: money.formatMinor(card.amount_minor),
      createdText: time.formatLocalDateTime(card.created_at),
      typeText: card.type === 'charge'
        ? 'CHARGE / 扣费'
        : card.type === 'gift_card'
          ? 'GIFT / 礼品卡'
          : 'RECHARGE / 充值',
      statusText: statusText(card),
      canAcknowledge: card.type === 'recharge' && card.status === 'awaiting_consumer',
      canCancel: card.type === 'recharge' && card.status === 'awaiting_operator',
      canConfirmCharge: card.type === 'charge' && card.status === 'awaiting_consumer',
      canDeclineCharge: card.type === 'charge' && card.status === 'awaiting_consumer',
      lines: (card.lines || []).map((line) => ({
        ...line,
        unitPriceText: money.formatMinor(line.unit_price_minor),
        lineTotalText: money.formatMinor(line.line_total_minor),
        typeText: line.item_type === 'service'
          ? 'SERVICE'
          : line.item_type === 'product' ? 'PRODUCT' : 'CUSTOM',
      })),
      events: (card.events || []).map((event) => ({
        ...event,
        label: EVENT[event.type] || event.type,
        timeText: time.formatLocalDateTime(event.created_at),
      })),
    }));
    this.setData({ cards });
  },
  choose(event) { this.setData({ selected: Number(event.currentTarget.dataset.value), custom: '' }); },
  input(event) { this.setData({ custom: event.detail.value, selected: 0 }); },
  openGiftClaim() { wx.navigateTo({ url: '/pages/gift-claim/index' }); },
  async submit() {
    if (!this.data.companyCode || this.submitInFlight) return;
    this.submitInFlight = true;
    let requestScope = '';
    try {
      this.setData({ busy: true, error: '' });
      const amount = money.yuanToMinor(this.data.custom || this.data.selected);
      const companyCode = this.data.companyCode;
      requestScope = `${companyCode}:${amount}`;
      let requestId = pending.get('recharge', requestScope);
      if (!requestId) {
        requestId = await member.newRequestId('recharge');
        pending.set('recharge', requestScope, requestId);
      }
      await member.recharge(companyCode, amount, requestId);
      // Once the HTTP response is known, later user actions are new intents.
      // If the response is lost, the key remains and a retry converges on the
      // already-created server order instead of creating a duplicate.
      pending.clear('recharge', requestScope);
      await this.loadCards(companyCode);
      wx.showModal({
        title: '充值卡已发送',
        content: `请使用你与「${this.data.companyName}」约定的现金、转账或其他方式付款。商家确认收款前，余额不会增加。`,
        showCancel: false,
      });
    } catch (error) { this.setData({ error: error.message || '充值失败' }); }
    finally {
      this.submitInFlight = false;
      this.setData({ busy: false });
    }
  },
  async acknowledge(event) {
    if (this.cardActionInFlight) return;
    this.cardActionInFlight = true;
    try {
      await member.acknowledgeTransactionCard(
        this.data.companyCode,
        event.currentTarget.dataset.no,
      );
      await member.account(this.data.companyCode);
      await this.loadCards(this.data.companyCode);
      wx.showToast({ title: '交易卡已归档', icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '确认失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
  async cancelCard(event) {
    if (this.cardActionInFlight) return;
    const confirmed = await new Promise((resolve) => wx.showModal({
      title: '取消充值卡',
      content: '只有商家尚未处理时可以取消。确定继续吗？',
      confirmColor: theme.current().accent,
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    }));
    if (!confirmed) return;
    this.cardActionInFlight = true;
    try {
      await member.cancelTransactionCard(
        this.data.companyCode,
        event.currentTarget.dataset.no,
      );
      await this.loadCards(this.data.companyCode);
    } catch (error) {
      this.setData({ error: error.message || '取消失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
  async confirmCharge(event) {
    if (this.cardActionInFlight) return;
    const cardNo = event.currentTarget.dataset.no;
    const card = this.data.cards.find((item) => item.card_no === cardNo);
    const lineSummary = card && card.lines && card.lines.length
      ? `\n${card.lines.slice(0, 4).map((line) => `${line.item_name} × ${line.quantity}`).join('、')}`
      : '';
    const confirmed = await new Promise((resolve) => wx.showModal({
      title: '确认商家扣费',
      content: `确认后将从当前会员余额扣除 ¥${card ? card.amountText : ''}，请先核对消费明细。${lineSummary}`,
      confirmText: '确认扣费',
      confirmColor: '#167A55',
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    }));
    if (!confirmed) return;
    this.cardActionInFlight = true;
    try {
      await member.confirmChargeCard(this.data.companyCode, cardNo);
      await member.account(this.data.companyCode);
      await this.loadCards(this.data.companyCode);
      wx.showToast({ title: '扣费已完成', icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '扣费确认失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
  async declineCharge(event) {
    if (this.cardActionInFlight) return;
    this.cardActionInFlight = true;
    try {
      await member.declineChargeCard(
        this.data.companyCode,
        event.currentTarget.dataset.no,
      );
      await this.loadCards(this.data.companyCode);
    } catch (error) {
      this.setData({ error: error.message || '拒绝失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
});
