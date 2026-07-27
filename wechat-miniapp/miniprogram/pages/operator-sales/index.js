const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');
const pending = require('../../store/pending');
const money = require('../../utils/money');
const time = require('../../utils/time');
const theme = require('../../utils/theme');
const qr = require('../../utils/qr');

function receiptView(card) {
  return {
    ...card,
    amountText: money.formatMinor(card.amount_minor),
    createdText: time.formatLocalDateTime(card.created_at),
    lines: (card.lines || []).map((line) => ({
      ...line,
      unitPriceText: money.formatMinor(line.unit_price_minor),
      lineTotalText: money.formatMinor(line.line_total_minor),
      typeText: line.item_type === 'service'
        ? 'SERVICE'
        : line.item_type === 'product' ? 'PRODUCT' : 'CUSTOM',
    })),
    stateText: card.status === 'completed' ? 'PAID' : 'AWAITING CUSTOMER',
    stateNote: card.status === 'completed' ? '双方已完成' : '等待客户确认扣费',
  };
}

function paged(items, requestedPage, pageSize) {
  const pageCount = Math.max(1, Math.ceil(items.length / pageSize));
  const page = Math.max(0, Math.min(pageCount - 1, Number(requestedPage) || 0));
  return {
    items: items.slice(page * pageSize, (page + 1) * pageSize),
    page,
    pageCount,
    pageText: `${String(page + 1).padStart(2, '0')} / ${String(pageCount).padStart(2, '0')}`,
  };
}

function compactSearch(value) {
  return String(value || '').toLowerCase().replace(/[\s()+-]/g, '');
}

function customerView(item) {
  const displayName = String(item.display_name || '').trim();
  const nickname = String(item.nickname || '').trim();
  const phone = String(item.phone || '').trim();
  const nameText = displayName || nickname || '未命名会员';
  const searchText = [displayName, nickname, phone, item.member_no]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return {
    ...item,
    display_name: displayName,
    nickname,
    phone,
    nameText,
    searchText,
    searchCompact: compactSearch(searchText),
    balanceText: money.formatMinor(item.balance_minor),
    identityText: item.identity_status === 'unclaimed' ? '待本人认领' : '已连接小程序',
  };
}

function filteredCustomers(customers, search, limit) {
  const query = String(search || '').trim().toLowerCase();
  const compact = compactSearch(query);
  return (customers || []).filter((item) => (
    !query
    || item.searchText.includes(query)
    || (compact && item.searchCompact.includes(compact))
  )).slice(0, limit || 24);
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
    activeSection: 'checkout',
    checkoutStep: 'customer',
    catalog: [],
    visibleCatalog: [],
    catalogPage: 0,
    catalogPageCount: 1,
    catalogPageText: '01 / 01',
    customers: [],
    visibleCustomers: [],
    customerSearch: '',
    selectedCustomer: null,
    recentReceipts: [],
    visibleReceipts: [],
    receiptPage: 0,
    receiptPageCount: 1,
    receiptPageText: '01 / 01',
    featuredReceipt: null,
    canManageCatalog: false,
    canManageCustomers: false,
    canRechargeCustomers: false,
    showCustomerEditor: false,
    savingCustomer: false,
    customerForm: { displayName: '', nickname: '', phone: '' },
    showCustomerCreator: false,
    creatingCustomer: false,
    customerCreateForm: { displayName: '', nickname: '', phone: '' },
    issuingClaim: false,
    issuedClaim: null,
    showRechargeEditor: false,
    rechargingCustomer: false,
    rechargeForm: { amount: '', note: '' },
    showEditor: false,
    itemTypeLabels: ['服务 / SERVICE', '产品 / PRODUCT'],
    form: {
      itemCode: '', itemTypeIndex: 0, itemName: '', unitName: '次',
      price: '', description: '', active: true, sortOrder: 0,
    },
    savingItem: false,
    importing: false,
    memberNo: '',
    selectedCustomerName: '',
    saleNote: '',
    checkoutModeLabels: ['立即直接扣款', '发送扣费确认卡'],
    checkoutModeIndex: 0,
    showCustomEditor: false,
    customLines: [],
    customForm: { name: '', unitName: '项', price: '', quantity: '1' },
    cartLines: [],
    cartTotalMinor: 0,
    cartTotalText: '0.00',
    checkoutBusy: false,
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
      });
      if (!companies.length) {
        this.setData({ loading: false, selected: null });
        return;
      }
      await this.loadCompany(index);
    } catch (error) {
      this.setData({ loading: false, error: error.message || '销售管理加载失败' });
    }
  },

  async loadCompany(index, options) {
    const selected = this.data.companies[index];
    if (!selected) return;
    session.setOperatorCompany(selected.public_code);
    this.setData({ loading: true, selected, error: '' });
    try {
      const dashboard = await member.operatorSales(selected.public_code);
      dashboard.stats.grossText = money.formatMinor(dashboard.stats.gross_minor);
      const oldQuantities = {};
      const customLines = options && options.keepCart ? this.data.customLines : [];
      if (options && options.keepCart) {
        this.data.catalog.forEach((item) => { oldQuantities[item.item_code] = item.quantity || 0; });
      }
      const catalog = (dashboard.catalog || []).map((item) => ({
        ...item,
        priceText: money.formatMinor(item.price_minor),
        typeText: item.item_type === 'service' ? 'SERVICE / 服务' : 'PRODUCT / 产品',
        quantity: item.active ? (oldQuantities[item.item_code] || 0) : 0,
      }));
      const customers = (dashboard.customers || []).map(customerView);
      const selectedCustomer = customers.find((item) => item.member_no === this.data.memberNo) || null;
      const recentReceipts = (dashboard.recent_receipts || []).map(receiptView);
      const catalogView = paged(catalog, this.data.catalogPage, 6);
      const receiptViewPage = paged(recentReceipts, this.data.receiptPage, 5);
      this.setData({
        loading: false,
        dashboard,
        catalog,
        visibleCatalog: catalogView.items,
        catalogPage: catalogView.page,
        catalogPageCount: catalogView.pageCount,
        catalogPageText: catalogView.pageText,
        customers,
        visibleCustomers: filteredCustomers(customers, this.data.customerSearch, 16),
        selectedCustomer,
        selectedCustomerName: selectedCustomer ? selectedCustomer.nameText : '',
        recentReceipts,
        visibleReceipts: receiptViewPage.items,
        receiptPage: receiptViewPage.page,
        receiptPageCount: receiptViewPage.pageCount,
        receiptPageText: receiptViewPage.pageText,
        canManageCatalog: ['owner', 'manager'].includes(dashboard.company.operator_role),
        canManageCustomers: ['owner', 'manager'].includes(dashboard.company.operator_role),
        canRechargeCustomers: ['owner', 'manager', 'cashier'].includes(
          dashboard.company.operator_role,
        ),
        customLines,
      });
      this.rebuildCart(catalog, customLines);
    } catch (error) {
      this.setData({ loading: false, error: error.message || '销售资料加载失败' });
    }
  },

  onCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    this.setData({
      companyIndex: index,
      activeSection: 'checkout',
      checkoutStep: 'customer',
      catalogPage: 0,
      receiptPage: 0,
      featuredReceipt: null,
      memberNo: '',
      selectedCustomerName: '',
      selectedCustomer: null,
      customerSearch: '',
      saleNote: '',
      showEditor: false,
      showCustomerEditor: false,
      showCustomerCreator: false,
      showRechargeEditor: false,
      issuedClaim: null,
      showCustomEditor: false,
      customLines: [],
      cartLines: [],
      cartTotalMinor: 0,
      cartTotalText: '0.00',
    });
    this.loadCompany(index);
  },

  switchSection(event) {
    const section = event.currentTarget.dataset.section;
    if (!['checkout', 'customers', 'catalog', 'receipts'].includes(section)) return;
    this.setData({ activeSection: section, error: '' });
    wx.pageScrollTo({ selector: '#salesWorkspace', duration: 260 });
  },

  switchCheckoutStep(event) {
    const step = event.currentTarget.dataset.step;
    if (!['customer', 'items', 'confirm'].includes(step)) return;
    if (step !== 'customer' && !this.data.memberNo) {
      wx.showToast({ title: '请先选择客户', icon: 'none' });
      return;
    }
    if (step === 'confirm' && !this.data.cartLines.length) {
      wx.showToast({ title: '请先选择消费内容', icon: 'none' });
      return;
    }
    this.setData({ checkoutStep: step, error: '' });
    wx.pageScrollTo({ selector: '#checkoutFlow', duration: 220 });
  },

  changeCatalogPage(event) {
    const view = paged(
      this.data.catalog,
      this.data.catalogPage + (Number(event.currentTarget.dataset.delta) || 0),
      6,
    );
    this.setData({
      visibleCatalog: view.items,
      catalogPage: view.page,
      catalogPageCount: view.pageCount,
      catalogPageText: view.pageText,
    });
    wx.pageScrollTo({ selector: '#catalogList', duration: 220 });
  },

  changeReceiptPage(event) {
    const view = paged(
      this.data.recentReceipts,
      this.data.receiptPage + (Number(event.currentTarget.dataset.delta) || 0),
      5,
    );
    this.setData({
      visibleReceipts: view.items,
      receiptPage: view.page,
      receiptPageCount: view.pageCount,
      receiptPageText: view.pageText,
      featuredReceipt: null,
    });
    wx.pageScrollTo({ selector: '#receiptList', duration: 220 });
  },

  startAdd() {
    if (!this.data.canManageCatalog) return;
    this.setData({
      showEditor: true,
      form: {
        itemCode: `sale-${Date.now().toString(36)}`,
        itemTypeIndex: 0,
        itemName: '',
        unitName: '次',
        price: '',
        description: '',
        active: true,
        sortOrder: this.data.catalog.length,
      },
    });
  },

  editItem(event) {
    if (!this.data.canManageCatalog) return;
    const item = this.data.catalog.find((row) => row.item_code === event.currentTarget.dataset.code);
    if (!item) return;
    this.setData({
      showEditor: true,
      form: {
        itemCode: item.item_code,
        itemTypeIndex: item.item_type === 'product' ? 1 : 0,
        itemName: item.item_name,
        unitName: item.unit_name,
        price: item.priceText,
        description: item.description || '',
        active: item.active,
        sortOrder: item.sort_order,
      },
    });
  },

  closeEditor() { this.setData({ showEditor: false }); },
  onFormInput(event) {
    this.setData({ [`form.${event.currentTarget.dataset.field}`]: event.detail.value });
  },
  onTypeChange(event) {
    const itemTypeIndex = Number(event.detail.value) || 0;
    this.setData({
      'form.itemTypeIndex': itemTypeIndex,
      'form.unitName': itemTypeIndex === 0 ? '次' : '件',
    });
  },
  onActiveChange(event) { this.setData({ 'form.active': Boolean(event.detail.value) }); },

  async saveItem() {
    if (this.data.savingItem || !this.data.selected) return;
    const form = this.data.form;
    if (!form.itemName.trim() || !form.unitName.trim()) {
      this.setData({ error: '请填写销售名称和单位' });
      return;
    }
    let priceMinor = 0;
    try {
      priceMinor = money.yuanToMinor(form.price);
    } catch (error) {
      this.setData({ error: error.message || '销售价格无效' });
      return;
    }
    this.setData({ savingItem: true, error: '' });
    try {
      await member.saveSalesCatalogItem(this.data.selected.public_code, {
        item_code: form.itemCode,
        item_type: form.itemTypeIndex === 1 ? 'product' : 'service',
        item_name: form.itemName.trim(),
        unit_name: form.unitName.trim(),
        price_minor: priceMinor,
        description: form.description.trim(),
        active: Boolean(form.active),
        sort_order: Number(form.sortOrder) || 0,
      });
      this.setData({ showEditor: false });
      await this.loadCompany(this.data.companyIndex, { keepCart: true });
      wx.showToast({ title: '项目已保存', icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '销售项目保存失败' });
    } finally {
      this.setData({ savingItem: false });
    }
  },

  async importBookingServices() {
    if (this.data.importing || !this.data.selected) return;
    this.setData({ importing: true, error: '' });
    try {
      const result = await member.importBookingServicesToSales(this.data.selected.public_code);
      await this.loadCompany(this.data.companyIndex, { keepCart: true });
      wx.showToast({ title: `已导入 ${result.imported || 0} 项`, icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '预约服务导入失败' });
    } finally {
      this.setData({ importing: false });
    }
  },

  adjustQuantity(event) {
    const code = event.currentTarget.dataset.code;
    const delta = Number(event.currentTarget.dataset.delta) || 0;
    const catalog = this.data.catalog.map((item) => {
      if (item.item_code !== code || !item.active) return item;
      return { ...item, quantity: Math.max(0, Math.min(99, (item.quantity || 0) + delta)) };
    });
    this.setData({ catalog });
    this.rebuildCart(catalog, this.data.customLines);
  },

  rebuildCart(catalog, customLines) {
    const catalogLines = (catalog || this.data.catalog)
      .filter((item) => item.active && item.quantity > 0)
      .map((item) => ({
        key: `catalog:${item.item_code}`,
        kind: 'catalog',
        item_code: item.item_code,
        item_name: item.item_name,
        quantity: item.quantity,
        lineTotalMinor: item.price_minor * item.quantity,
        lineTotalText: money.formatMinor(item.price_minor * item.quantity),
      }));
    const custom = (customLines || []).map((item) => ({ ...item }));
    const cartLines = catalogLines.concat(custom);
    const cartTotalMinor = cartLines.reduce((sum, item) => sum + item.lineTotalMinor, 0);
    this.setData({
      cartLines,
      cartTotalMinor,
      cartTotalText: money.formatMinor(cartTotalMinor),
    });
  },

  onSaleInput(event) {
    const field = event.currentTarget.dataset.field;
    const value = event.detail.value;
    this.setData({ [field]: value });
  },

  onCustomerSearch(event) {
    const customerSearch = String(event.detail.value || '');
    const visibleCustomers = filteredCustomers(this.data.customers, customerSearch, 24);
    this.setData({ customerSearch, visibleCustomers });
  },

  openCustomerCreator() {
    if (!this.data.canManageCustomers) return;
    this.setData({
      showCustomerCreator: true,
      showCustomerEditor: false,
      issuedClaim: null,
      customerCreateForm: { displayName: '', nickname: '', phone: '' },
      error: '',
    });
  },

  closeCustomerCreator() {
    if (!this.data.creatingCustomer) this.setData({ showCustomerCreator: false });
  },

  onCustomerCreateInput(event) {
    this.setData({
      [`customerCreateForm.${event.currentTarget.dataset.field}`]: event.detail.value,
    });
  },

  async createCustomer() {
    if (this.data.creatingCustomer || !this.data.canManageCustomers || !this.data.selected) return;
    const form = this.data.customerCreateForm;
    if (![form.displayName, form.nickname, form.phone].some((value) => String(value || '').trim())) {
      this.setData({ error: '请至少填写客户姓名、昵称或手机号' });
      return;
    }
    const scope = [
      this.data.selected.public_code,
      form.displayName.trim(),
      form.nickname.trim(),
      form.phone.trim(),
    ].join('|');
    this.setData({ creatingCustomer: true, error: '' });
    try {
      let requestId = pending.get('operator-customer-create', scope);
      if (!requestId) {
        requestId = await member.newRequestId('operator-customer-create');
        pending.set('operator-customer-create', scope, requestId);
      }
      const result = await member.createOperatorCustomer(
        this.data.selected.public_code,
        {
          display_name: form.displayName.trim(),
          nickname: form.nickname.trim(),
          phone: form.phone.trim(),
        },
        requestId,
      );
      pending.clear('operator-customer-create', scope);
      const created = result.member;
      this.setData({
        memberNo: created.member_no,
        showCustomerCreator: false,
        customerCreateForm: { displayName: '', nickname: '', phone: '' },
      });
      await this.loadCompany(this.data.companyIndex);
      this.setData({ activeSection: 'customers' });
      wx.showToast({ title: '待认领客户已建立', icon: 'success' });
    } catch (error) {
      const message = error.message || '客户建立失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    } finally {
      this.setData({ creatingCustomer: false });
    }
  },

  selectCustomer(event) {
    const customer = this.data.customers.find(
      (item) => item.member_no === event.currentTarget.dataset.member,
    );
    if (!customer) return;
    this.setData({
      memberNo: customer.member_no,
      selectedCustomerName: customer.nameText,
      selectedCustomer: customer,
      customerSearch: '',
      visibleCustomers: [customer],
      showCustomerEditor: false,
      showRechargeEditor: false,
    });
  },

  manageCustomer(event) {
    const customer = this.data.customers.find(
      (item) => item.member_no === event.currentTarget.dataset.member,
    );
    if (!customer) return;
    this.setData({
      memberNo: customer.member_no,
      selectedCustomerName: customer.nameText,
      selectedCustomer: customer,
      issuedClaim: null,
      showCustomerCreator: false,
      showRechargeEditor: false,
      error: '',
    });
  },

  clearCustomer() {
    this.setData({
      memberNo: '',
      selectedCustomerName: '',
      selectedCustomer: null,
      customerSearch: '',
      visibleCustomers: this.data.customers.slice(0, 16),
      showCustomerEditor: false,
      showRechargeEditor: false,
      rechargeForm: { amount: '', note: '' },
    });
  },

  openCustomerEditor() {
    const customer = this.data.selectedCustomer;
    if (!this.data.canManageCustomers || !customer) return;
    this.setData({
      showCustomerEditor: true,
      showRechargeEditor: false,
      customerForm: {
        displayName: customer.display_name || '',
        nickname: customer.nickname || '',
        phone: customer.phone || '',
      },
      error: '',
    });
  },

  closeCustomerEditor() {
    if (!this.data.savingCustomer) this.setData({ showCustomerEditor: false });
  },

  async issueCustomerClaim(event) {
    if (this.data.issuingClaim || !this.data.canManageCustomers || !this.data.selected) return;
    const memberNo = event.currentTarget.dataset.member
      || (this.data.selectedCustomer && this.data.selectedCustomer.member_no);
    const customer = this.data.customers.find((item) => item.member_no === memberNo);
    if (!customer || customer.identity_status !== 'unclaimed') return;
    const scope = `${this.data.selected.public_code}:${memberNo}`;
    this.setData({ issuingClaim: true, error: '', selectedCustomer: customer });
    try {
      let requestId = pending.get('customer-claim-code', scope);
      if (!requestId) {
        requestId = await member.newRequestId('customer-claim-code');
        pending.set('customer-claim-code', scope, requestId);
      }
      const result = await member.issueCustomerClaimCode(
        this.data.selected.public_code,
        memberNo,
        15,
        requestId,
      );
      pending.clear('customer-claim-code', scope);
      const claim = {
        ...result.claim,
        customerName: customer.nameText,
        balanceText: money.formatMinor(result.claim.customer.balance_minor),
        expiresText: time.formatLocalDateTime(result.claim.expires_at),
      };
      this.setData({ issuedClaim: claim }, () => {
        qr.draw(this, '#customerClaimQr', claim.qr_payload).catch((error) => {
          this.setData({ error: error.message || '认领二维码绘制失败' });
        });
      });
      wx.pageScrollTo({ selector: '#customerClaimCard', duration: 300 });
    } catch (error) {
      const message = error.message || '认领码生成失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    } finally {
      this.setData({ issuingClaim: false });
    }
  },

  closeCustomerClaim() { this.setData({ issuedClaim: null }); },
  copyCustomerClaim() {
    if (!this.data.issuedClaim) return;
    wx.setClipboardData({ data: this.data.issuedClaim.qr_payload });
  },

  onCustomerFormInput(event) {
    this.setData({
      [`customerForm.${event.currentTarget.dataset.field}`]: event.detail.value,
    });
  },

  async saveCustomerProfile() {
    const customer = this.data.selectedCustomer;
    if (this.data.savingCustomer || !this.data.canManageCustomers || !customer) return;
    const form = this.data.customerForm;
    this.setData({ savingCustomer: true, error: '' });
    try {
      const result = await member.saveOperatorMemberProfile(
        this.data.selected.public_code,
        customer.member_no,
        {
          display_name: form.displayName.trim(),
          nickname: form.nickname.trim(),
          phone: form.phone.trim(),
        },
      );
      const customers = this.data.customers.map((item) => (
        item.member_no === customer.member_no
          ? customerView({ ...item, ...(result.member || {}) })
          : item
      ));
      const selectedCustomer = customers.find((item) => item.member_no === customer.member_no);
      this.setData({
        customers,
        visibleCustomers: filteredCustomers(customers, this.data.customerSearch, 24),
        selectedCustomer,
        selectedCustomerName: selectedCustomer.nameText,
        showCustomerEditor: false,
      });
      wx.showToast({ title: '会员资料已保存', icon: 'success' });
    } catch (error) {
      const message = error.message || '会员资料保存失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    } finally {
      this.setData({ savingCustomer: false });
    }
  },

  openRechargeEditor() {
    if (!this.data.canRechargeCustomers || !this.data.selectedCustomer) return;
    this.setData({
      showRechargeEditor: true,
      showCustomerEditor: false,
      rechargeForm: { amount: '', note: '' },
      error: '',
    });
  },

  closeRechargeEditor() {
    if (!this.data.rechargingCustomer) this.setData({ showRechargeEditor: false });
  },

  onRechargeFormInput(event) {
    this.setData({
      [`rechargeForm.${event.currentTarget.dataset.field}`]: event.detail.value,
    });
  },

  async rechargeSelectedCustomer() {
    const customer = this.data.selectedCustomer;
    if (this.data.rechargingCustomer || !this.data.canRechargeCustomers || !customer) return;
    let amountMinor = 0;
    try {
      amountMinor = money.yuanToMinor(this.data.rechargeForm.amount);
    } catch (error) {
      const message = error.message || '充值金额无效';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
      return;
    }
    let confirmed = false;
    try {
      confirmed = await new Promise((resolve, reject) => wx.showModal({
        title: '确认线下充值',
        content: `将为「${customer.nameText}」充值 ¥${money.formatMinor(amountMinor)}。`
          + '请确认你已经线下收到对应款项；确认后余额会立即增加并生成双边交易卡。',
        confirmText: '确认入账',
        confirmColor: '#167A55',
        success: (result) => resolve(Boolean(result.confirm)),
        fail: () => reject(new Error('充值确认窗口打开失败，请重试')),
      }));
    } catch (error) {
      const message = error.message || '充值确认窗口打开失败，请重试';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
      return;
    }
    if (!confirmed) return;

    const note = this.data.rechargeForm.note.trim();
    const scope = [
      this.data.selected.public_code,
      customer.member_no,
      amountMinor,
      note,
    ].join(':');
    this.setData({ rechargingCustomer: true, error: '' });
    try {
      let requestId = pending.get('operator-member-recharge', scope);
      if (!requestId) {
        requestId = await member.newRequestId('operator-member-recharge');
        pending.set('operator-member-recharge', scope, requestId);
      }
      const result = await member.operatorRechargeCustomer(
        this.data.selected.public_code,
        customer.member_no,
        { amount_minor: amountMinor, note },
        requestId,
      );
      pending.clear('operator-member-recharge', scope);
      const balanceMinor = Number(result.card && result.card.balance_minor);
      const customers = this.data.customers.map((item) => (
        item.member_no === customer.member_no && Number.isFinite(balanceMinor)
          ? customerView({ ...item, balance_minor: balanceMinor })
          : item
      ));
      const selectedCustomer = customers.find((item) => item.member_no === customer.member_no);
      this.setData({
        customers,
        visibleCustomers: filteredCustomers(customers, this.data.customerSearch, 24),
        selectedCustomer,
        selectedCustomerName: selectedCustomer.nameText,
        showRechargeEditor: false,
        rechargeForm: { amount: '', note: '' },
      });
      wx.showModal({
        title: '充值已入账',
        content: `¥${money.formatMinor(amountMinor)} 已写入「${selectedCustomer.nameText}」的公司会员余额，双边交易卡也已生成。`,
        showCancel: false,
      });
    } catch (error) {
      const message = error.message || '客户充值失败';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
    } finally {
      this.setData({ rechargingCustomer: false });
    }
  },

  onCheckoutModeChange(event) {
    this.setData({ checkoutModeIndex: Number(event.detail.value) || 0 });
  },

  openCustomEditor() {
    this.setData({
      showCustomEditor: true,
      customForm: { name: '', unitName: '项', price: '', quantity: '1' },
    });
  },

  closeCustomEditor() { this.setData({ showCustomEditor: false }); },
  onCustomInput(event) {
    this.setData({ [`customForm.${event.currentTarget.dataset.field}`]: event.detail.value });
  },

  addCustomLine() {
    const form = this.data.customForm;
    if (!form.name.trim() || !form.unitName.trim()) {
      this.setData({ error: '请填写自定义消费名称和单位' });
      return;
    }
    let unitPriceMinor = 0;
    let quantity = 0;
    try {
      unitPriceMinor = money.yuanToMinor(form.price);
      if (!/^\d+$/.test(String(form.quantity || ''))) throw new Error('数量必须是整数');
      quantity = Number(form.quantity);
      if (quantity < 1 || quantity > 999) throw new Error('数量必须在 1–999 之间');
    } catch (error) {
      this.setData({ error: error.message || '自定义消费资料无效' });
      return;
    }
    const customLines = this.data.customLines.concat({
      key: `custom:${Date.now().toString(36)}`,
      kind: 'custom',
      item_name: form.name.trim(),
      unit_name: form.unitName.trim(),
      unit_price_minor: unitPriceMinor,
      quantity,
      lineTotalMinor: unitPriceMinor * quantity,
      lineTotalText: money.formatMinor(unitPriceMinor * quantity),
    });
    this.setData({ customLines, showCustomEditor: false, error: '' });
    this.rebuildCart(this.data.catalog, customLines);
  },

  removeCustomLine(event) {
    const key = event.currentTarget.dataset.key;
    const customLines = this.data.customLines.filter((item) => item.key !== key);
    this.setData({ customLines });
    this.rebuildCart(this.data.catalog, customLines);
  },

  async checkout() {
    if (this.data.checkoutBusy || !this.data.selected) return;
    const memberNo = this.data.memberNo.trim().toUpperCase();
    if (!/^M[A-F0-9]{14}$/.test(memberNo)) {
      this.setData({ error: '请选择客户或输入完整会员编号' });
      return;
    }
    if (!this.data.cartLines.length || this.data.cartTotalMinor <= 0) {
      this.setData({ error: '请先选择至少一个有价格的服务或产品' });
      return;
    }
    const confirmationMode = this.data.checkoutModeIndex === 1;
    const content = [
      `${this.data.selectedCustomerName || memberNo}`,
      `${this.data.cartLines.length} 项明细 · 合计 ¥${this.data.cartTotalText}`,
      confirmationMode
        ? '确认后会向客户发送逐项扣费卡；客户确认时才扣除余额。'
        : '确认后将立即扣除客户当前公司会员余额，并同时生成双方不可变消费收据。',
    ].join('\n');
    let confirmed = false;
    try {
      confirmed = await new Promise((resolve, reject) => wx.showModal({
        title: confirmationMode ? '确认发送扣费卡' : '确认直接扣款',
        content,
        confirmText: confirmationMode ? '发送卡片' : '确认扣款',
        confirmColor: theme.current().accent,
        success: (result) => resolve(result.confirm),
        fail: () => reject(new Error('扣款确认窗口打开失败，请重试')),
      }));
    } catch (error) {
      const message = error.message || '扣款确认窗口打开失败，请重试';
      this.setData({ error: message });
      wx.showToast({ title: message, icon: 'none' });
      return;
    }
    if (!confirmed) return;
    const lines = this.data.cartLines.map((item) => (item.kind === 'custom'
      ? {
        custom_name: item.item_name,
        unit_name: item.unit_name,
        unit_price_minor: item.unit_price_minor,
        quantity: item.quantity,
      }
      : { item_code: item.item_code, quantity: item.quantity }));
    const scope = [
      this.data.selected.public_code,
      memberNo,
      JSON.stringify(lines),
      this.data.saleNote.trim(),
      confirmationMode ? 'confirm' : 'direct',
    ].join('|');
    this.setData({ checkoutBusy: true, error: '' });
    try {
      const pendingKind = confirmationMode
        ? 'operator-sale-charge-card'
        : 'operator-direct-sale';
      let requestId = pending.get(pendingKind, scope);
      if (!requestId) {
        requestId = await member.newRequestId(pendingKind);
        pending.set(pendingKind, scope, requestId);
      }
      const payload = { member_no: memberNo, lines, note: this.data.saleNote.trim() };
      const result = confirmationMode
        ? await member.operatorCreateSaleChargeCard(
          this.data.selected.public_code, payload, requestId,
        )
        : await member.operatorDirectSale(
          this.data.selected.public_code, payload, requestId,
        );
      pending.clear(pendingKind, scope);
      const featuredReceipt = receiptView(result.receipt || result.card);
      const catalog = this.data.catalog.map((item) => ({ ...item, quantity: 0 }));
      this.setData({
        featuredReceipt,
        activeSection: 'receipts',
        checkoutStep: 'customer',
        receiptPage: 0,
        catalog,
        saleNote: '',
        customLines: [],
        cartLines: [],
        cartTotalMinor: 0,
        cartTotalText: '0.00',
      });
      await this.loadCompany(this.data.companyIndex);
      this.setData({ featuredReceipt, activeSection: 'receipts' });
      wx.pageScrollTo({ selector: '#issuedReceipt', duration: 480 });
    } catch (error) {
      this.setData({ error: error.message || '直接扣款失败' });
    } finally {
      this.setData({ checkoutBusy: false });
    }
  },
});
