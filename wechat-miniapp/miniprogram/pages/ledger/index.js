const member = require('../../services/member');
const context = require('../../services/context');
const money = require('../../utils/money');
const time = require('../../utils/time');
const companyUtil = require('../../utils/company');

const PAGE_SIZE = 5;

const SETTLEMENT_LABELS = {
  operator_wallet: '商家直接扣款',
  direct_wallet: '余额直接扣款',
  one_time_payment_code: '一次性付款码',
  consumer_confirmed_card: '用户确认扣费卡',
};

function pageView(receipts, requestedPage) {
  const pageCount = Math.max(1, Math.ceil(receipts.length / PAGE_SIZE));
  const page = Math.max(0, Math.min(pageCount - 1, Number(requestedPage) || 0));
  return {
    visibleReceipts: receipts.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE),
    page,
    pageCount,
    pageText: `${String(page + 1).padStart(2, '0')} / ${String(pageCount).padStart(2, '0')}`,
  };
}

function receiptView(card, companyName) {
  const lines = (card.lines || []).map((line) => ({
    ...line,
    typeText: line.item_type === 'service'
      ? 'SERVICE'
      : line.item_type === 'product' ? 'PRODUCT' : 'CUSTOM',
    unitPriceText: money.formatMinor(line.unit_price_minor),
    lineTotalText: money.formatMinor(line.line_total_minor),
  }));
  return {
    ...card,
    companyName,
    amountText: money.formatMinor(card.amount_minor),
    createdText: time.formatLocalDateTime(card.created_at),
    receiptNo: card.consumption_order_no || card.card_no,
    settlementText: SETTLEMENT_LABELS[card.settlement_method] || '会员余额扣款',
    descriptionText: card.description || (lines.length
      ? lines.map((line) => line.item_name).join(' · ')
      : '会员消费'),
    lines,
  };
}

Page({
  data: {
    loading: true,
    receipts: [],
    visibleReceipts: [],
    page: 0,
    pageCount: 1,
    pageText: '01 / 01',
    totalSpentText: '0.00',
    error: '',
    companyName: '',
    companyMode: '',
  },
  onShow() { this.load(); },
  async load() {
    try {
      this.setData({ loading: true, error: '' });
      const selected = await context.requireCompany();
      if (!selected) {
        this.setData({ loading: false, receipts: [], visibleReceipts: [] });
        return;
      }
      const result = await member.transactionCards(selected.code);
      const receipts = (result.cards || [])
        .filter((card) => card.type === 'charge' && card.status === 'completed')
        .map((card) => receiptView(card, selected.company.name));
      const totalSpentMinor = receipts.reduce(
        (total, card) => total + Number(card.amount_minor || 0),
        0,
      );
      this.setData({
        loading: false,
        receipts,
        ...pageView(receipts, 0),
        totalSpentText: money.formatMinor(totalSpentMinor),
        error: '',
        companyName: selected.company.name,
        companyMode: companyUtil.modeLabel(selected.company),
      });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '消费记录加载失败' });
    }
  },
  changePage(event) {
    const delta = Number(event.currentTarget.dataset.delta) || 0;
    this.setData(pageView(this.data.receipts, this.data.page + delta));
    wx.pageScrollTo({ selector: '#consumptionArchive', duration: 220 });
  },
});
