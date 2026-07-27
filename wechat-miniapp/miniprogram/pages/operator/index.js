const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');
const pending = require('../../store/pending');
const money = require('../../utils/money');
const time = require('../../utils/time');
const qr = require('../../utils/qr');
const theme = require('../../utils/theme');

const CARD_STATUS = {
  awaiting_operator: '待核对收款',
  awaiting_consumer: '已入账 · 待用户确认',
  completed: '双方已完成',
  declined: '已拒绝',
  cancelled: '用户已取消',
  expired: '已过期',
};

const TRANSACTION_PAGE_SIZE = 5;

function transactionPageView(cards, requestedPage) {
  const pageCount = Math.max(1, Math.ceil(cards.length / TRANSACTION_PAGE_SIZE));
  const page = Math.max(0, Math.min(pageCount - 1, Number(requestedPage) || 0));
  return {
    transactionPage: page,
    transactionPageCount: pageCount,
    transactionPageText: `${String(page + 1).padStart(2, '0')} / ${String(pageCount).padStart(2, '0')}`,
    visibleTransactionCards: cards.slice(
      page * TRANSACTION_PAGE_SIZE,
      (page + 1) * TRANSACTION_PAGE_SIZE,
    ),
  };
}

Page({
  data: {
    loading: true,
    error: '',
    companies: [],
    companyNames: [],
    companyIndex: 0,
    selected: null,
    dashboard: null,
    transactionCards: [],
    visibleTransactionCards: [],
    transactionPage: 0,
    transactionPageCount: 1,
    transactionPageText: '01 / 01',
    activeSection: 'overview',
    giftFundingLabels: ['线下已收款 / 销售型', '商家赠送 / 推广型'],
    giftFundingIndex: 0,
    giftAmount: '',
    giftNote: '',
    giftExpiresDays: '365',
    creatingGift: false,
    issuedGift: null,
    warehouse: { linked: false, errors: [] },
  },

  onShow() { this.load(); },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },

  async load() {
    this.setData({ loading: true, error: '' });
    try {
      const appContext = await context.loadAppContext();
      const companies = appContext.operator_companies || [];
      let index = companies.findIndex((item) => item.public_code === session.operatorCompany());
      if (index < 0) index = 0;
      this.setData({
        companies,
        companyNames: companies.map((item) => item.company_name),
        companyIndex: index,
        warehouse: appContext.warehouse || { linked: false, errors: [] },
      });
      if (!companies.length) {
        this.setData({ loading: false, selected: null, dashboard: null });
        return;
      }
      await this.loadCompany(index);
    } catch (error) {
      this.setData({ loading: false, error: error.message || '经营中心加载失败' });
    }
  },

  async loadCompany(index) {
    const selected = this.data.companies[index];
    if (!selected) return;
    session.setOperatorCompany(selected.public_code);
    this.setData({
      loading: true,
      selected,
      dashboard: null,
      transactionCards: [],
      visibleTransactionCards: [],
      transactionPage: 0,
      transactionPageCount: 1,
      transactionPageText: '01 / 01',
      giftFundingIndex: 0,
      issuedGift: null,
      error: '',
    });
    try {
      const [dashboard, transactions] = await Promise.all([
        member.operatorBooking(selected.public_code),
        member.operatorTransactionCards(selected.public_code),
      ]);
      const transactionCards = (transactions.cards || []).map((card) => ({
        ...card,
        amountText: money.formatMinor(card.amount_minor),
        createdText: time.formatLocalDateTime(card.created_at),
        typeText: card.type === 'charge'
          ? 'CHARGE / 扣费卡'
          : card.type === 'gift_card'
            ? 'GIFT / 礼品卡'
            : 'RECHARGE / 充值卡',
        statusText: card.type === 'charge' && card.status === 'awaiting_consumer'
          ? '等待用户确认扣费'
          : CARD_STATUS[card.status] || card.status,
        actionable: card.type === 'recharge' && card.status === 'awaiting_operator',
        lines: (card.lines || []).map((line) => ({
          ...line,
          unitPriceText: money.formatMinor(line.unit_price_minor),
          lineTotalText: money.formatMinor(line.line_total_minor),
        })),
      }));
      const canIssuePromotional = dashboard.company.operator_role !== 'cashier';
      this.setData({
        loading: false,
        dashboard,
        transactionCards,
        ...transactionPageView(transactionCards, 0),
        giftFundingLabels: canIssuePromotional
          ? ['线下已收款 / 销售型', '商家赠送 / 推广型']
          : ['线下已收款 / 销售型'],
      });
    } catch (error) {
      this.setData({
        loading: false,
        error: error.message || '经营资料加载失败',
      });
    }
  },

  onCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    this.setData({ companyIndex: index, activeSection: 'overview' });
    this.loadCompany(index);
  },

  switchSection(event) {
    const section = event.currentTarget.dataset.section;
    if (!['overview', 'transactions', 'gifts', 'system'].includes(section)) return;
    this.setData({ activeSection: section, error: '' }, () => {
      if (section === 'gifts' && this.data.issuedGift) this.drawGiftQr();
      wx.pageScrollTo({ selector: '#operatorWorkspace', duration: 260 });
    });
  },

  changeTransactionPage(event) {
    const delta = Number(event.currentTarget.dataset.delta) || 0;
    this.setData(transactionPageView(
      this.data.transactionCards,
      this.data.transactionPage + delta,
    ));
    wx.pageScrollTo({ selector: '#transactionList', duration: 220 });
  },

  onGiftInput(event) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value });
  },

  onGiftFundingChange(event) {
    this.setData({ giftFundingIndex: Number(event.detail.value) || 0 });
  },

  async drawGiftQr() {
    if (!this.data.issuedGift || !this.data.issuedGift.qr_payload) return;
    try {
      await qr.draw(this, '#giftQr', this.data.issuedGift.qr_payload, {
        dark: theme.current().ink,
        light: '#FAF8F2',
        correction: 'Q',
      });
    } catch (error) {
      const message = error.message || '礼品卡二维码生成失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    }
  },

  async createGiftCard() {
    if (this.data.creatingGift) return;
    if (!this.data.selected) {
      wx.showToast({ title: '请先选择经营公司', icon: 'none' });
      return;
    }
    let amountMinor = 0;
    let expiresDays = 0;
    try {
      amountMinor = money.yuanToMinor(this.data.giftAmount);
      if (!/^\d+$/.test(String(this.data.giftExpiresDays || ''))) {
        throw new Error('有效天数必须是整数');
      }
      expiresDays = Number(this.data.giftExpiresDays);
      if (expiresDays < 1 || expiresDays > 3650) {
        throw new Error('有效天数必须在 1–3650 天之间');
      }
    } catch (error) {
      const message = error.message || '礼品卡资料无效';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
      return;
    }
    const fundingType = this.data.giftFundingIndex === 1
      ? 'promotional'
      : 'sold';
    if (fundingType === 'sold') {
      let confirmed = false;
      try {
        confirmed = await new Promise((resolve, reject) => wx.showModal({
          title: '确认已线下收款',
          content: '销售型礼品卡会在领取后计入会员本金余额。请确认你已通过现金、转账或双方约定方式收到对应款项。',
          confirmText: '确认发行',
          confirmColor: '#167A55',
          success: (result) => resolve(Boolean(result.confirm)),
          fail: () => reject(new Error('收款确认窗口打开失败，请重试')),
        }));
      } catch (error) {
        const message = error.message || '收款确认窗口打开失败，请重试';
        this.setData({ error: message });
        wx.showToast({ title: message, icon: 'none' });
        return;
      }
      if (!confirmed) return;
    }
    const companyCode = this.data.selected.public_code;
    const note = this.data.giftNote.trim();
    const requestScope = [
      companyCode,
      amountMinor,
      fundingType,
      expiresDays,
      note,
    ].join(':');
    this.setData({ creatingGift: true, error: '' });
    try {
      let requestId = pending.get('gift-issue', requestScope);
      if (!requestId) {
        requestId = await member.newRequestId('gift-issue');
        pending.set('gift-issue', requestScope, requestId);
      }
      const result = await member.operatorCreateGiftCard(
        companyCode,
        {
          amount_minor: amountMinor,
          funding_type: fundingType,
          note,
          expires_days: expiresDays,
        },
        requestId,
      );
      pending.clear('gift-issue', requestScope);
      const gift = result.gift_card;
      this.setData({
        creatingGift: false,
        issuedGift: {
          ...gift,
          amountText: money.formatMinor(gift.amount_minor),
          fundingText: gift.funding_type === 'promotional'
            ? 'PROMOTIONAL / 赠送型'
            : 'SOLD / 销售型',
          expiresText: time.formatLocalDateTime(gift.expires_at),
        },
        giftAmount: '',
        giftNote: '',
      }, () => {
        this.drawGiftQr();
        wx.showToast({ title: '礼品卡已生成', icon: 'success' });
        wx.pageScrollTo({ selector: '#issuedGift', duration: 420 });
      });
    } catch (error) {
      const message = error.message || '礼品卡发行失败';
      this.setData({
        creatingGift: false,
        error: message,
      });
      wx.showToast({ title: message, icon: 'none' });
    }
  },

  copyGiftToken() {
    const gift = this.data.issuedGift;
    if (!gift) return;
    wx.setClipboardData({ data: gift.qr_payload });
  },

  onShareAppMessage() {
    const gift = this.data.issuedGift;
    if (!gift) {
      return {
        title: 'Bonfirework 会员服务',
        path: '/pages/home/index',
      };
    }
    return {
      title: `${this.data.selected.company_name || 'Bonfirework'} · ¥${gift.amountText} 礼品卡`,
      path: `/pages/gift-claim/index?payload=${encodeURIComponent(gift.qr_payload)}`,
      imageUrl: '/assets/brand/bonfire-platform-mark.png',
    };
  },

  async scanPaymentCode() {
    if (this.scanInFlight || !this.data.selected) return;
    this.scanInFlight = true;
    let requestScope = '';
    try {
      const scan = await new Promise((resolve, reject) => wx.scanCode({
        scanType: ['qrCode'],
        success: resolve,
        fail: reject,
      }));
      const payload = String(scan.result || '').trim();
      if (!/^BFW1:P:[a-z0-9-]+:M\d{10}$/.test(payload)) {
        throw new Error('这不是有效的 Bonfirework 一次性付款 QR');
      }
      requestScope = `${this.data.selected.public_code}:${payload}`;
      let requestId = pending.get('payment-scan', requestScope);
      if (!requestId) {
        requestId = await member.newRequestId('payment-scan');
        pending.set('payment-scan', requestScope, requestId);
      }
      const result = await member.operatorRedeemPaymentCode(
        this.data.selected.public_code,
        payload,
        requestId,
      );
      pending.clear('payment-scan', requestScope);
      await this.loadCompany(this.data.companyIndex);
      wx.showModal({
        title: '扫码扣费完成',
        content: `已扣除 ¥${money.formatMinor(
          Number(result.amount_minor)
          || Number(result.principal_used_minor || 0)
            + Number(result.bonus_used_minor || 0),
        )}；余额 ¥${money.formatMinor(result.balance_minor)}。`,
        showCancel: false,
      });
    } catch (error) {
      this.setData({ error: error.message || '扫码扣费失败' });
    } finally {
      this.scanInFlight = false;
    }
  },

  openSetup() { wx.navigateTo({ url: '/pages/operator-setup/index' }); },
  openSales() { wx.navigateTo({ url: '/pages/operator-sales/index' }); },
  openFinance() { wx.navigateTo({ url: '/pages/operator-finance/index' }); },
  openAppointments() { wx.navigateTo({ url: '/pages/operator-appointments/index' }); },
  openRegister() { wx.navigateTo({ url: '/pages/operator-register/index' }); },
  openWarehouseLink() { wx.navigateTo({ url: '/pages/warehouse-link/index' }); },
  async confirmRecharge(event) {
    if (this.cardActionInFlight || !this.data.selected) return;
    const cardNo = event.currentTarget.dataset.no;
    const confirmed = await new Promise((resolve) => wx.showModal({
      title: '确认已实际收款',
      content: '确认后服务端会立即增加该会员余额，并生成不可变交易事件。请先核对线下款项。',
      confirmText: '确认入账',
      confirmColor: '#167A55',
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    }));
    if (!confirmed) return;
    this.cardActionInFlight = true;
    try {
      await member.operatorConfirmTransactionCard(
        this.data.selected.public_code,
        cardNo,
        '商家已核对线下收款',
      );
      wx.showToast({ title: '已入账', icon: 'success' });
      await this.loadCompany(this.data.companyIndex);
    } catch (error) {
      this.setData({ error: error.message || '确认入账失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
  async declineRecharge(event) {
    if (this.cardActionInFlight || !this.data.selected) return;
    const cardNo = event.currentTarget.dataset.no;
    const confirmed = await new Promise((resolve) => wx.showModal({
      title: '拒绝充值卡',
      content: '仅在没有收到对应款项时拒绝；拒绝后不会改变会员余额。',
      confirmText: '确认拒绝',
      confirmColor: theme.current().accent,
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    }));
    if (!confirmed) return;
    this.cardActionInFlight = true;
    try {
      await member.operatorDeclineTransactionCard(
        this.data.selected.public_code,
        cardNo,
        '未核对到对应线下款项',
      );
      await this.loadCompany(this.data.companyIndex);
    } catch (error) {
      this.setData({ error: error.message || '拒绝失败' });
    } finally {
      this.cardActionInFlight = false;
    }
  },
  openConsumer() {
    if (this.data.selected && this.data.selected.public_code) {
      session.setCompany(this.data.selected.public_code);
    }
    session.setPortal('consumer');
    wx.switchTab({ url: '/pages/home/index' });
  },
});
