const member = require('../../services/member');
const context = require('../../services/context');
const session = require('../../store/session');
const pending = require('../../store/pending');
const money = require('../../utils/money');
const time = require('../../utils/time');
const companyUtil = require('../../utils/company');

function decodePayload(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  try {
    return decodeURIComponent(raw);
  } catch (error) {
    return raw;
  }
}

function parseGiftPayload(value) {
  const payload = String(value || '').trim();
  const match = /^BFW1:G:([a-z0-9-]+):(G[A-F0-9]{32})$/.exec(payload);
  if (!match) throw new Error('这不是有效的 Bonfirework 礼品卡');
  return {
    payload,
    companyCode: match[1],
  };
}

Page({
  claimInFlight: false,
  data: {
    loading: false,
    scanning: false,
    claiming: false,
    error: '',
    payload: '',
    companyCode: '',
    companyName: '',
    companyMode: '',
    gift: null,
    amountText: '0.00',
    fundingText: '',
    expiresText: '',
    joined: false,
    consentVersion: '',
    consentText: '',
    consented: false,
    result: null,
  },

  onLoad(options) {
    this.initialPayload = decodePayload(options && options.payload);
  },

  onShow() {
    if (this.initialPayload) {
      const payload = this.initialPayload;
      this.initialPayload = '';
      this.loadGift(payload);
      return;
    }
    if (!this.data.payload) this.ensureSession();
  },

  onPullDownRefresh() {
    const task = this.data.payload
      ? this.loadGift(this.data.payload)
      : this.ensureSession();
    Promise.resolve(task).finally(() => wx.stopPullDownRefresh());
  },

  async ensureSession() {
    try {
      this.setData({ loading: true, error: '' });
      await context.loadMemberships();
      this.setData({ loading: false });
    } catch (error) {
      this.setData({
        loading: false,
        error: error.message || '无法建立会员登录状态',
      });
    }
  },

  async loadGift(rawPayload) {
    let parsed;
    try {
      parsed = parseGiftPayload(rawPayload);
    } catch (error) {
      this.setData({
        loading: false,
        gift: null,
        result: null,
        error: error.message,
      });
      return;
    }
    try {
      this.setData({
        loading: true,
        error: '',
        payload: parsed.payload,
        companyCode: parsed.companyCode,
        gift: null,
        result: null,
        consented: false,
      });
      const [memberships, companyResult, previewResult] = await Promise.all([
        context.loadMemberships(),
        member.company(parsed.companyCode),
        member.giftCardPreview(parsed.companyCode, parsed.payload),
      ]);
      const accounts = memberships.companies || [];
      const joined = accounts.some(
        (account) => account.company
          && account.company.code === parsed.companyCode,
      );
      const company = companyResult.company;
      const consent = companyResult.consent || company.consent || {};
      const gift = previewResult.gift_card;
      if (joined) session.setCompany(parsed.companyCode);
      this.setData({
        loading: false,
        companyName: company.name,
        companyMode: companyUtil.modeLabel(company),
        gift,
        amountText: money.formatMinor(gift.amount_minor),
        fundingText: gift.funding_type === 'promotional'
          ? 'PROMOTIONAL / 商家赠送'
          : 'SOLD / 已线下结算',
        expiresText: gift.expires_at
          ? time.formatLocalDateTime(gift.expires_at)
          : '长期有效',
        joined,
        consentVersion: String(consent.version || '').trim(),
        consentText: String(consent.text || '').trim(),
      });
    } catch (error) {
      this.setData({
        loading: false,
        gift: null,
        result: null,
        error: error.message || '礼品卡读取失败',
      });
    }
  },

  async scanGift() {
    if (this.data.scanning) return;
    this.setData({ scanning: true, error: '' });
    try {
      const scan = await new Promise((resolve, reject) => wx.scanCode({
        scanType: ['qrCode'],
        success: resolve,
        fail: reject,
      }));
      await this.loadGift(scan.result);
    } catch (error) {
      if (!String(error && error.errMsg || '').includes('cancel')) {
        this.setData({ error: error.message || '扫描礼品卡失败' });
      }
    } finally {
      this.setData({ scanning: false });
    }
  },

  toggleConsent(event) {
    this.setData({
      consented: (event.detail.value || []).includes('agree'),
    });
  },

  showRules() {
    if (!this.data.consentText || !this.data.consentVersion) {
      this.setData({ error: '该公司尚未发布可验证的会员规则' });
      return;
    }
    wx.showModal({
      title: `${this.data.companyName} · 会员规则`,
      content: this.data.consentText,
      showCancel: false,
      confirmText: '我已了解',
    });
  },

  async claimGift() {
    if (
      this.claimInFlight
      || !this.data.gift
      || this.data.gift.status !== 'active'
    ) return;
    if (!this.data.joined && !this.data.consented) {
      this.setData({ error: '请先核对公司并同意会员服务与隐私规则' });
      return;
    }
    if (
      !this.data.joined
      && (!this.data.consentVersion || !this.data.consentText)
    ) {
      this.setData({ error: '当前无法取得正式会员规则，暂不能领取' });
      return;
    }
    this.claimInFlight = true;
    const requestScope = `${this.data.companyCode}:${this.data.gift.gift_no}`;
    this.setData({ claiming: true, error: '' });
    try {
      let requestId = pending.get('gift-claim', requestScope);
      if (!requestId) {
        requestId = await member.newRequestId('gift-claim');
        pending.set('gift-claim', requestScope, requestId);
      }
      if (!this.data.joined) {
        await member.join(this.data.companyCode, this.data.consentVersion);
        session.setCompany(this.data.companyCode);
      }
      const result = await member.claimGiftCard(
        this.data.companyCode,
        this.data.payload,
        requestId,
      );
      pending.clear('gift-claim', requestScope);
      this.setData({
        claiming: false,
        joined: true,
        consented: false,
        gift: result.gift_card,
        result: {
          balanceText: money.formatMinor(result.balance_minor),
          principalText: money.formatMinor(result.principal_minor),
          bonusText: money.formatMinor(result.bonus_minor),
          cardNo: result.card && result.card.card_no,
        },
      });
      wx.showToast({ title: '礼品卡已入账', icon: 'success' });
    } catch (error) {
      this.setData({
        claiming: false,
        error: error.message || '礼品卡领取失败',
      });
    } finally {
      this.claimInFlight = false;
    }
  },

  openTransactions() {
    if (this.data.companyCode) session.setCompany(this.data.companyCode);
    wx.navigateTo({ url: '/pages/recharge/index' });
  },
});
