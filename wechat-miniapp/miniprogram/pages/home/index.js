const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');
const money = require('../../utils/money');
const companyUtil = require('../../utils/company');

Page({
  data: {
    loading: true,
    error: '',
    portal: 'consumer',
    canSwitchPortal: false,
    account: null,
    consumerCompanies: [],
    consumerCompanyNames: [],
    consumerCompanyIndex: 0,
    operatorCompany: null,
    operatorCompanies: [],
    operatorCompanyNames: [],
    operatorCompanyIndex: 0,
    operatorDashboard: null,
    balance: '0.00',
    principal: '0.00',
    bonus: '0.00',
    companyMode: '',
    warehouse: { linked: false },
    warehouseAccountName: '',
    warehouseAccountMeta: '',
  },

  onShow() { this.load(); },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },

  async load() {
    const loadSequence = (this.loadSequence || 0) + 1;
    this.loadSequence = loadSequence;
    this.setData({ loading: true, error: '' });
    try {
      const appContext = await context.loadAppContext();
      if (loadSequence !== this.loadSequence) return;
      const portals = appContext.portals || ['consumer'];
      const operatorCompanies = appContext.operator_companies || [];
      const consumerCompanies = appContext.consumer_companies || [];
      if (!operatorCompanies.length) session.setOperatorCompany('');
      let portal = session.portal() || appContext.default_portal || 'consumer';
      if (portals.indexOf(portal) < 0) portal = appContext.default_portal || portals[0] || 'consumer';
      session.setPortal(portal);
      const warehouse = appContext.warehouse || { linked: false };
      const warehouseUser = warehouse.global_user || {};
      const next = {
        loading: false,
        portal,
        canSwitchPortal: portals.length > 1,
        warehouse,
        warehouseAccountName: warehouse.linked
          ? (warehouseUser.display_name || warehouseUser.username || 'Warehouse 账号')
          : '',
        warehouseAccountMeta: warehouse.linked && warehouseUser.username
          ? `@${warehouseUser.username} · ${operatorCompanies.length} 个经营空间`
          : '',
        account: null,
        consumerCompanies,
        consumerCompanyNames: consumerCompanies.map((item) => item.company.name),
        operatorCompany: null,
        operatorCompanies,
        operatorCompanyNames: operatorCompanies.map((item) => item.company_name),
        operatorDashboard: null,
      };
      if (portal === 'operator') {
        let code = session.operatorCompany();
        let operatorCompanyIndex = operatorCompanies.findIndex(
          (item) => item.public_code === code,
        );
        if (operatorCompanyIndex < 0) operatorCompanyIndex = 0;
        const selected = operatorCompanies[operatorCompanyIndex];
        next.operatorCompanyIndex = operatorCompanyIndex;
        if (selected) {
          code = selected.public_code;
          session.setOperatorCompany(code);
          if (consumerCompanies.some((item) => item.company.code === code)) {
            session.setCompany(code);
          }
          next.operatorCompany = selected;
          try {
            next.operatorDashboard = await member.operatorBooking(code);
            if (loadSequence !== this.loadSequence) return;
          } catch (error) {
            if (error.statusCode !== 409) throw error;
          }
        }
      } else {
        let code = session.company();
        let consumerCompanyIndex = consumerCompanies.findIndex(
          (item) => item.company && item.company.code === code,
        );
        if (consumerCompanyIndex < 0) consumerCompanyIndex = 0;
        const account = consumerCompanies[consumerCompanyIndex];
        next.consumerCompanyIndex = consumerCompanyIndex;
        if (account) {
          session.setCompany(account.company.code);
          next.account = account;
          next.balance = money.formatMinor(account.balance_minor);
          next.principal = money.formatMinor(account.principal_minor);
          next.bonus = money.formatMinor(account.bonus_minor);
          next.companyMode = companyUtil.modeLabel(account.company);
        }
      }
      if (loadSequence !== this.loadSequence) return;
      this.setData(next);
    } catch (error) {
      if (loadSequence !== this.loadSequence) return;
      this.setData({ loading: false, error: error.message || '加载失败' });
    }
  },

  switchPortal() {
    const portal = this.data.portal === 'operator' ? 'consumer' : 'operator';
    session.setPortal(portal);
    this.load();
  },

  onConsumerCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    const selected = this.data.consumerCompanies[index];
    if (!selected || !selected.company) return;
    session.setCompany(selected.company.code);
    this.setData({ consumerCompanyIndex: index });
    this.load();
  },

  onOperatorCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    const selected = this.data.operatorCompanies[index];
    if (!selected) return;
    session.setOperatorCompany(selected.public_code);
    if (this.data.consumerCompanies.some(
      (item) => item.company && item.company.code === selected.public_code,
    )) {
      session.setCompany(selected.public_code);
    }
    this.setData({ operatorCompanyIndex: index });
    this.load();
  },

  openCompanies() { context.openCompanies(); },
  openRecharge() { wx.navigateTo({ url: '/pages/recharge/index' }); },
  openPayCode() { wx.navigateTo({ url: '/pages/pay-code/index' }); },
  openLedger() { wx.navigateTo({ url: '/pages/ledger/index' }); },
  openLevel() { wx.navigateTo({ url: '/pages/level/index' }); },
  openLottery() { wx.navigateTo({ url: '/pages/lottery/index' }); },
  openBooking() { wx.switchTab({ url: '/pages/booking/index' }); },
  openAppointments() { wx.switchTab({ url: '/pages/appointments/index' }); },
  openOperator() { wx.navigateTo({ url: '/pages/operator/index' }); },
  openOperatorSales() { wx.navigateTo({ url: '/pages/operator-sales/index' }); },
  openOperatorSetup() { wx.navigateTo({ url: '/pages/operator-setup/index' }); },
  openOperatorAppointments() {
    wx.navigateTo({ url: '/pages/operator-appointments/index' });
  },
  openOperatorRegister() {
    wx.navigateTo({ url: '/pages/operator-register/index' });
  },
  openWarehouseLink() { wx.navigateTo({ url: '/pages/warehouse-link/index' }); },
});
