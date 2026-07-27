const member = require('../../services/member');
const session = require('../../store/session');
const context = require('../../services/context');
const money = require('../../utils/money');
const companyUtil = require('../../utils/company');

Page({
  previewSequence: 0,
  data: {
    loading: true,
    previewing: false,
    error: '',
    companies: [],
    selected: '',
    joinCode: '',
    joinPreview: null,
    handledInvite: '',
    joinButtonLabel: '加入公司会员空间',
    consented: false,
  },
  onShow() { this.load(); },
  async load() {
    try {
      const result = await context.loadMemberships();
      const companies = (result.companies || []).map((account) => ({
        code: account.company.code,
        name: account.company.name,
        levelName: account.level_name || '普通会员',
        balance: money.formatMinor(account.balance_minor),
        modeLabel: companyUtil.modeLabel(account.company),
      }));
      const selected = session.company() || '';
      const inviteCode = session.inviteCompany() || '';
      const inviteChanged = Boolean(inviteCode && inviteCode !== this.data.handledInvite);
      // A hot-start company QR can arrive while this tab is already alive. In
      // that case the invitation replaces stale typed input without changing
      // the user's currently selected membership.
      const inviteIsMembership = companies.some((company) => company.code === inviteCode);
      const joinCode = inviteChanged
        ? (inviteIsMembership ? '' : inviteCode)
        : this.data.joinCode;
      this.setData({
        companies,
        selected,
        joinCode,
        handledInvite: inviteCode || this.data.handledInvite,
        loading: false,
        error: '',
      });
      if (inviteCode && inviteIsMembership) {
        session.setCompany(inviteCode);
        session.setInviteCompany('');
        this.setData({ selected: inviteCode, handledInvite: '', joinCode: '' });
      }
      if (joinCode && !companies.some((company) => company.code === joinCode)) {
        await this.previewCompany(joinCode);
      }
    } catch (error) { this.setData({ loading: false, error: error.message }); }
  },
  select(event) {
    session.setCompany(event.currentTarget.dataset.code);
    session.setInviteCompany('');
    this.setData({ selected: event.currentTarget.dataset.code, handledInvite: '' });
    wx.showToast({ title: '已切换公司', icon: 'success' });
    setTimeout(() => {
      if (getCurrentPages().length > 1) wx.navigateBack();
      else wx.switchTab({ url: '/pages/home/index' });
    }, 450);
  },
  inputCode(event) {
    this.previewSequence += 1;
    this.setData({
      joinCode: event.detail.value.trim().toLowerCase(),
      joinPreview: null,
      joinButtonLabel: '加入公司会员空间',
      consented: false,
      previewing: false,
      error: '',
    });
  },
  previewFromInput() { this.previewCompany(this.data.joinCode); },
  async previewCompany(value) {
    const code = String(value || '').trim().toLowerCase();
    if (!code) return null;
    const sequence = this.previewSequence + 1;
    this.previewSequence = sequence;
    try {
      this.setData({ previewing: true, error: '' });
      const result = await member.company(code);
      if (sequence !== this.previewSequence || code !== this.data.joinCode) return null;
      const company = result.company;
      const consent = result.consent || company.consent || {};
      const preview = {
        code: company.code,
        name: company.name,
        currency: company.currency || 'CNY',
        modeLabel: companyUtil.modeLabel(company),
        consentVersion: String(consent.version || '').trim(),
        consentText: String(consent.text || '').trim(),
      };
      this.setData({
        joinCode: preview.code,
        joinPreview: preview,
        joinButtonLabel: `加入「${preview.name}」`,
        previewing: false,
      });
      return preview;
    } catch (error) {
      if (sequence !== this.previewSequence) return null;
      this.setData({
        previewing: false,
        joinPreview: null,
        joinButtonLabel: '加入公司会员空间',
        consented: false,
        error: error.message,
      });
      return null;
    }
  },
  showRules() {
    const preview = this.data.joinPreview;
    if (!preview || !preview.consentText || !preview.consentVersion) {
      this.setData({ error: '该公司的正式会员服务与隐私规则暂不可用，请稍后再试' });
      return;
    }
    wx.showModal({
      title: `${preview.name} · 会员规则`,
      content: preview.consentText,
      showCancel: false,
      confirmText: '我已了解',
    });
  },
  toggleConsent(event) { this.setData({ consented: (event.detail.value || []).includes('agree') }); },
  async join() {
    if (!this.data.joinCode) return;
    let preview = this.data.joinPreview;
    if (!preview || preview.code !== this.data.joinCode) {
      preview = await this.previewCompany(this.data.joinCode);
      if (!preview) return;
    }
    if (!this.data.consented) {
      this.setData({ error: '请先明确同意会员服务与隐私规则' });
      return;
    }
    if (!preview.consentVersion || !preview.consentText) {
      this.setData({ error: '无法取得服务端发布的正式规则，暂不能加入' });
      return;
    }
    try {
      await member.join(this.data.joinCode, preview.consentVersion);
      session.setCompany(this.data.joinCode);
      session.setInviteCompany('');
      this.setData({
        consented: false,
        joinPreview: null,
        handledInvite: '',
        joinButtonLabel: '加入公司会员空间',
      });
      await this.load();
      wx.showToast({ title: `已加入${preview.name}`, icon: 'success' });
    } catch (error) { this.setData({ error: error.message }); }
  },
});
