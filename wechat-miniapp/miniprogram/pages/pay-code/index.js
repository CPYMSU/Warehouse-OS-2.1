const member = require('../../services/member');
const context = require('../../services/context');
const money = require('../../utils/money');
const time = require('../../utils/time');
const companyUtil = require('../../utils/company');
const qr = require('../../utils/qr');

Page({
  refreshInFlight: false,
  data: {
    loading: false,
    contextLoading: true,
    error: '',
    companyCode: '',
    companyName: '',
    companyMode: '',
    balanceMinor: 0,
    balance: '0.00',
    amountInput: '',
    authorizedAmount: '0.00',
    paymentCode: '',
    qrPayload: '',
    displayCode: '',
    expiresAt: '',
  },
  onShow() { this.loadContext(); },
  async loadContext() {
    try {
      this.setData({ contextLoading: true, error: '' });
      const selected = await context.requireCompany();
      if (!selected) {
        this.setData({
          contextLoading: false,
          companyCode: '',
          companyName: '',
          companyMode: '',
          balanceMinor: 0,
          balance: '0.00',
          paymentCode: '',
          qrPayload: '',
          displayCode: '',
          authorizedAmount: '0.00',
          expiresAt: '',
        });
        return;
      }
      const companyChanged = Boolean(
        this.data.companyCode && this.data.companyCode !== selected.code,
      );
      const nextData = {
        contextLoading: false,
        companyCode: selected.code,
        companyName: selected.company.name,
        companyMode: companyUtil.modeLabel(selected.company),
        balanceMinor: Number(selected.account.balance_minor || 0),
        balance: money.formatMinor(selected.account.balance_minor),
      };
      if (companyChanged) {
        nextData.amountInput = '';
        nextData.paymentCode = '';
        nextData.qrPayload = '';
        nextData.displayCode = '';
        nextData.authorizedAmount = '0.00';
        nextData.expiresAt = '';
      }
      this.setData(nextData);
    } catch (error) {
      this.setData({
        contextLoading: false,
        companyCode: '',
        companyName: '',
        companyMode: '',
        paymentCode: '',
        qrPayload: '',
        displayCode: '',
        authorizedAmount: '0.00',
        expiresAt: '',
        error: error.message || '无法读取公司',
      });
    }
  },
  inputAmount(event) {
    this.setData({
      amountInput: event.detail.value,
      paymentCode: '',
      qrPayload: '',
      displayCode: '',
      expiresAt: '',
    });
  },
  async drawQr() {
    if (!this.data.qrPayload) return;
    try {
      await qr.draw(this, '#paymentQr', this.data.qrPayload);
    } catch (error) {
      this.setData({ error: error.message || '二维码生成失败' });
    }
  },
  async refresh() {
    if (!this.data.companyCode || this.refreshInFlight) return;
    this.refreshInFlight = true;
    try {
      this.setData({ loading: true, error: '' });
      const amountMinor = money.yuanToMinor(this.data.amountInput);
      if (amountMinor > this.data.balanceMinor) throw new Error('授权金额不能超过当前可用余额');
      const result = await member.paymentCode(this.data.companyCode, amountMinor);
      const displayCode = result.payment_code.replace(/^(M)(\d{3})(\d{3})(\d{4})$/, '$1 $2 $3 $4');
      this.setData({
        loading: false,
        paymentCode: result.payment_code,
        qrPayload: result.qr_payload,
        displayCode,
        authorizedAmount: money.formatMinor(result.amount_minor),
        expiresAt: time.formatLocalDateTime(result.expires_at),
      }, () => this.drawQr());
    } catch (error) { this.setData({ loading: false, error: error.message }); }
    finally { this.refreshInFlight = false; }
  },
  copy() { wx.setClipboardData({ data: this.data.paymentCode }); },
});
