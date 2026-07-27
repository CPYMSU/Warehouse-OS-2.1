const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');

Page({
  data: {
    loading: true,
    submitting: false,
    error: '',
    companyName: '',
    publicCode: '',
    displayName: '',
    consent: null,
    agreed: false,
  },

  onLoad() { this.load(); },

  async load() {
    try {
      const appContext = await context.loadAppContext();
      this.setData({ loading: false, consent: appContext.consent || null });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '规则加载失败' });
    }
  },

  onInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: event.detail.value });
  },

  onAgree(event) {
    this.setData({ agreed: (event.detail.value || []).indexOf('agree') >= 0 });
  },

  async submit() {
    if (this.data.submitting) return;
    if (!this.data.companyName.trim() || !this.data.publicCode.trim()) {
      this.setData({ error: '请填写经营名称和唯一公司代码' });
      return;
    }
    if (!this.data.agreed || !this.data.consent) {
      this.setData({ error: '请阅读并同意会员服务与隐私规则' });
      return;
    }
    this.setData({ submitting: true, error: '' });
    try {
      const result = await member.createOperatorCompany({
        company_name: this.data.companyName.trim(),
        public_code: this.data.publicCode.trim().toLowerCase(),
        display_name: this.data.displayName.trim(),
        consent_version: this.data.consent.version,
      });
      session.setPortal('operator');
      session.setOperatorCompany(result.company.public_code);
      session.setCompany(result.company.public_code);
      wx.showToast({ title: '经营空间已建立', icon: 'success' });
      setTimeout(() => wx.switchTab({ url: '/pages/home/index' }), 500);
    } catch (error) {
      this.setData({ error: error.message || '注册失败' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
