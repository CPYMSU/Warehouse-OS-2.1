const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');

Page({
  data: {
    loading: true,
    username: '',
    password: '',
    submitting: false,
    error: '',
    warehouse: { linked: false },
    operatorCount: 0,
  },

  onLoad() { this.load(); },

  async load() {
    try {
      const appContext = await context.loadAppContext();
      this.setData({
        loading: false,
        warehouse: appContext.warehouse || { linked: false },
        operatorCount: (appContext.operator_companies || []).length,
      });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '身份状态加载失败' });
    }
  },

  onInput(event) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value });
  },

  openRegister() {
    wx.navigateTo({ url: '/pages/operator-register/index' });
  },

  async submit() {
    if (this.data.submitting) return;
    const username = this.data.username.trim();
    const password = this.data.password;
    if (!username || !password) {
      this.setData({ error: '请输入 Warehouse 账号和密码' });
      return;
    }
    this.setData({ submitting: true, error: '' });
    try {
      await context.loadAppContext();
      const linked = await member.warehouseSignIn(username, password);
      this.setData({ password: '' });
      const appContext = linked.context || {};
      const operatorCompanies = appContext.operator_companies || [];
      const warehouseCompanies = (appContext.warehouse && appContext.warehouse.companies) || [];
      if (operatorCompanies[0]) {
        session.setPortal('operator');
        session.setOperatorCompany(operatorCompanies[0].public_code);
      } else {
        session.setPortal('consumer');
        session.setOperatorCompany('');
      }
      this.setData({
        warehouse: appContext.warehouse || { linked: true },
        operatorCount: operatorCompanies.length,
      });
      wx.showModal({
        title: operatorCompanies.length ? '经营端已开启' : '身份验证成功',
        content: operatorCompanies.length
          ? `已同步 ${operatorCompanies.length} 个可管理公司，正在进入经营工作台。`
          : warehouseCompanies.length
            ? '身份已绑定，但当前账号尚未取得公司管理权限。你仍可使用消费者功能，或注册独立经营空间。'
            : '身份已绑定；当前 Warehouse 账号没有有效公司成员关系。',
        showCancel: false,
        success: () => wx.switchTab({ url: '/pages/home/index' }),
      });
    } catch (error) {
      this.setData({ password: '', error: error.message || '绑定失败' });
    } finally {
      this.setData({ submitting: false });
    }
  },
});
