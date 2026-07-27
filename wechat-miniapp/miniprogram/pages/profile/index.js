const member = require('../../services/member');
const session = require('../../store/session');
const context = require('../../services/context');
const money = require('../../utils/money');
const companyUtil = require('../../utils/company');
const theme = require('../../utils/theme');

Page({
  data: {
    loading: true,
    sessionBusy: false,
    companies: [],
    operatorCompanies: [],
    consumer: null,
    warehouse: { linked: false },
    warehouseAccountName: '',
    warehouseUsername: '',
    consent: {},
    claimBusy: false,
    selectedCompany: '',
    portal: 'consumer',
    error: '',
    themePresets: [],
    themeName: '',
    themeDraftAccent: '#E0261C',
    themeDraftInk: '#141414',
    themePreviewStyle: '',
    themeError: '',
  },
  onShow() {
    this.loadTheme();
    this.load();
  },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },
  async load() {
    const loadSequence = (this.loadSequence || 0) + 1;
    this.loadSequence = loadSequence;
    try {
      this.setData({ loading: true, error: '' });
      const result = await context.loadAppContext();
      if (loadSequence !== this.loadSequence) return;
      const companies = (result.consumer_companies || []).map((account) => ({
        code: account.company.code,
        name: account.company.name,
        balance: money.formatMinor(account.balance_minor),
        modeLabel: companyUtil.modeLabel(account.company),
      }));
      let selectedCompany = session.company();
      if (!companies.some((company) => company.code === selectedCompany)) {
        selectedCompany = companies[0] ? companies[0].code : '';
        session.setCompany(selectedCompany);
      }
      const warehouse = result.warehouse || { linked: false };
      const warehouseUser = warehouse.global_user || {};
      this.setData({
        loading: false,
        companies,
        operatorCompanies: (result.operator_companies || []).map((company) => ({
          code: company.public_code,
          name: company.company_name,
          role: company.operator_role,
          linked: company.mode === 'warehouse_linked',
        })),
        consumer: result.consumer,
        warehouse,
        warehouseAccountName: warehouse.linked
          ? (warehouseUser.display_name || warehouseUser.username || 'Warehouse 账号')
          : '',
        warehouseUsername: warehouseUser.username || '',
        consent: result.consent || {},
        selectedCompany,
        portal: session.portal() || result.default_portal || 'consumer',
        error: '',
      });
    } catch (error) {
      if (loadSequence !== this.loadSequence) return;
      this.setData({ loading: false, error: error.message });
    }
  },
  loadTheme() {
    const selected = theme.current();
    this.setData({
      themePresets: theme.presets().map((item) => ({
        ...item,
        selected: item.accent === selected.accent && item.ink === selected.ink,
      })),
      themeName: selected.name,
      themeDraftAccent: selected.accent,
      themeDraftInk: selected.ink,
      themePreviewStyle: theme.style(selected),
      themeError: '',
    });
  },
  refreshThemeProvider() {
    const provider = this.selectComponent('#themeProvider');
    if (provider && provider.refresh) provider.refresh();
  },
  applySelectedTheme(selected, message) {
    this.setData({
      themePresets: theme.presets().map((item) => ({
        ...item,
        selected: item.accent === selected.accent && item.ink === selected.ink,
      })),
      themeName: selected.name,
      themeDraftAccent: selected.accent,
      themeDraftInk: selected.ink,
      themePreviewStyle: theme.style(selected),
      themeError: '',
    }, () => this.refreshThemeProvider());
    wx.showToast({ title: message || '配色已应用', icon: 'success' });
  },
  selectThemePreset(event) {
    const preset = this.data.themePresets.find(
      (item) => item.id === event.currentTarget.dataset.id,
    );
    if (!preset) return;
    this.applySelectedTheme(theme.save(preset), preset.name);
  },
  onThemeInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [field]: event.detail.value, themeError: '' }, () => {
      const accent = theme.normalizeHex(this.data.themeDraftAccent);
      const ink = theme.normalizeHex(this.data.themeDraftInk);
      if (accent && ink) this.setData({ themePreviewStyle: theme.style({ accent, ink }) });
    });
  },
  saveCustomTheme() {
    try {
      const selected = theme.save({
        accent: this.data.themeDraftAccent,
        ink: this.data.themeDraftInk,
      });
      this.applySelectedTheme(selected, '自定义配色已应用');
    } catch (error) {
      const message = error.message || '颜色格式无效';
      this.setData({ themeError: message });
      wx.showToast({ title: message, icon: 'none' });
    }
  },
  resetTheme() {
    this.applySelectedTheme(theme.reset(), '已恢复经典红黑');
  },
  async scanCustomerClaim() {
    if (this.data.claimBusy) return;
    this.setData({ claimBusy: true, error: '' });
    try {
      const scan = await new Promise((resolve, reject) => wx.scanCode({
        scanType: ['qrCode'],
        success: resolve,
        fail: reject,
      }));
      const payload = String(scan.result || '').trim();
      const match = /^BFW1:C:([a-z0-9-]+):(C[A-F0-9]{32})$/.exec(payload);
      if (!match) throw new Error('这不是 Bonfirework 客户认领二维码');
      const companyCode = match[1];
      const previewResult = await member.customerClaimPreview(companyCode, payload);
      const claim = previewResult.claim;
      const customer = claim.customer || {};
      const customerName = customer.display_name || customer.nickname || customer.member_no;
      const consent = this.data.consent || {};
      if (!consent.version || !consent.text) {
        throw new Error('暂时无法取得当前会员服务与隐私规则，请稍后重试');
      }
      const confirmed = await new Promise((resolve, reject) => wx.showModal({
        title: `认领「${claim.company.name}」客户资料`,
        content: [
          `商家记录姓名：${customerName}`,
          `手机尾号：${customer.phone_masked || '未登记'}`,
          `现有余额：¥${money.formatMinor(customer.balance_minor)}`,
          `现有积分：${customer.points_balance || 0}`,
          '',
          '确认后，这份原有资料、余额、消费与预约记录会绑定到当前微信身份，不会复制成第二份。',
          '',
          consent.text,
        ].join('\n'),
        confirmText: '同意认领',
        confirmColor: theme.current().accent,
        success: (result) => resolve(Boolean(result.confirm)),
        fail: reject,
      }));
      if (!confirmed) return;
      await member.claimCustomerProfile(
        companyCode,
        payload,
        consent.version,
      );
      session.setCompany(companyCode);
      session.setPortal('consumer');
      await this.load();
      wx.showModal({
        title: '客户资料已连接',
        content: '原有余额、积分、消费卡片与预约记录现已归入你的当前小程序账号。',
        showCancel: false,
        confirmText: '完成',
        confirmColor: theme.current().accent,
      });
    } catch (error) {
      if (error && /cancel/i.test(String(error.errMsg || ''))) return;
      const message = error.message || '客户资料认领失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    } finally {
      this.setData({ claimBusy: false });
    }
  },
  companies() { wx.navigateTo({ url: '/pages/companies/index' }); },
  openWarehouseLink() { wx.navigateTo({ url: '/pages/warehouse-link/index' }); },
  selectCompany(event) {
    const code = event.currentTarget.dataset.code;
    if (!code) return;
    session.setCompany(code);
    session.setPortal('consumer');
    this.setData({ selectedCompany: code, portal: 'consumer' });
    wx.showToast({ title: '已切换公司', icon: 'success' });
  },
  openOperator(event) {
    const code = event.currentTarget.dataset.code;
    if (code) session.setOperatorCompany(code);
    session.setPortal('operator');
    wx.switchTab({ url: '/pages/home/index' });
  },
  async resetSession(allSessions) {
    try {
      this.setData({ sessionBusy: true, error: '' });
      // 先让服务器撤销旧令牌，再清除本地会话，避免只在前端“假退出”。
      try {
        await member.logout(allSessions);
      } catch (error) {
        // 401 表示旧令牌在服务端已经无效，等价于撤销完成；其余错误不能
        // 静默清本地，否则用户会误以为其他设备也已退出。
        if (!error || error.statusCode !== 401) throw error;
      }
      session.clear();
      this.setData({
        companies: [],
        operatorCompanies: [],
        consumer: null,
        warehouse: { linked: false },
        warehouseAccountName: '',
        warehouseUsername: '',
        consent: {},
      });
      await getApp().ensureSession();
      await this.load();
      wx.showToast({ title: allSessions ? '所有设备已退出' : '本设备已重新登录', icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '会话重置失败' });
    } finally {
      this.setData({ sessionBusy: false });
    }
  },
  logoutDevice() { this.resetSession(false); },
  logoutAll() {
    wx.showModal({
      title: '退出所有设备？',
      content: '所有已登录设备的会员会话都会立即失效，本设备随后会建立新的微信登录会话。',
      confirmText: '全部退出',
      confirmColor: theme.current().accent,
      success: (result) => { if (result.confirm) this.resetSession(true); },
    });
  },
});
