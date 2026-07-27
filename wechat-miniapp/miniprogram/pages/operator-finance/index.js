const context = require('../../services/context');
const member = require('../../services/member');
const session = require('../../store/session');
const pending = require('../../store/pending');
const money = require('../../utils/money');

function localDate() {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

function pageView(items, requestedPage, size) {
  const pageCount = Math.max(1, Math.ceil(items.length / size));
  const page = Math.max(0, Math.min(pageCount - 1, Number(requestedPage) || 0));
  return {
    items: items.slice(page * size, (page + 1) * size),
    page,
    pageCount,
    text: `${String(page + 1).padStart(2, '0')} / ${String(pageCount).padStart(2, '0')}`,
  };
}

function recordView(item) {
  const syncLabels = {
    local_only: 'APP 本地账本',
    pending: '等待 Warehouse 同步',
    processing: '正在生成财务草稿',
    completed: 'Warehouse 草稿已建立',
    failed: '联动待重试',
  };
  const directionLabels = {
    inflow: 'CASH IN',
    outflow: 'CASH OUT',
    revenue: 'REVENUE',
  };
  return {
    ...item,
    amountText: money.formatMinor(item.amount_minor),
    directionText: directionLabels[item.direction] || 'EVENT',
    syncText: syncLabels[item.sync_status] || item.sync_status || '已记录',
    counterpartyText: item.counterparty_name || item.member_no || '未填写交易对象',
  };
}

Page({
  data: {
    loading: true,
    saving: false,
    error: '',
    companies: [],
    companyNames: [],
    companyIndex: 0,
    selected: null,
    dashboard: null,
    activeSection: 'overview',
    records: [],
    visibleRecords: [],
    recordPage: 0,
    recordPageCount: 1,
    recordPageText: '01 / 01',
    canWrite: false,
    entryTypeLabels: ['非会员消费', '其他收入', '经营支出'],
    entryKinds: ['non_member_sale', 'income', 'expense'],
    entryTypeIndex: 0,
    categoryLabels: ['线下服务', '商品销售', '临时消费', '其他消费'],
    categoryIndex: 0,
    form: {
      amount: '',
      counterparty: '',
      description: '',
      occurredOn: localDate(),
    },
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
      this.setData({ loading: false, error: error.message || '财务系统加载失败' });
    }
  },

  async loadCompany(index) {
    const selected = this.data.companies[index];
    if (!selected) return;
    session.setOperatorCompany(selected.public_code);
    this.setData({ loading: true, selected, error: '' });
    try {
      const dashboard = await member.operatorFinance(selected.public_code);
      dashboard.stats.cashInText = money.formatMinor(dashboard.stats.cash_in_minor);
      dashboard.stats.cashOutText = money.formatMinor(dashboard.stats.cash_out_minor);
      dashboard.stats.netCashText = money.formatMinor(
        Math.abs(dashboard.stats.net_cash_minor),
      );
      dashboard.stats.netCashPrefix = dashboard.stats.net_cash_minor < 0 ? '−¥' : '¥';
      dashboard.stats.revenueText = money.formatMinor(dashboard.stats.recognized_revenue_minor);
      const records = (dashboard.records || []).map(recordView);
      const view = pageView(records, this.data.recordPage, 8);
      this.setData({
        loading: false,
        dashboard,
        records,
        visibleRecords: view.items,
        recordPage: view.page,
        recordPageCount: view.pageCount,
        recordPageText: view.text,
        canWrite: ['owner', 'manager', 'cashier'].includes(dashboard.company.operator_role),
      });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '财务资料加载失败' });
    }
  },

  onCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    this.setData({ companyIndex: index, recordPage: 0, activeSection: 'overview' });
    this.loadCompany(index);
  },

  switchSection(event) {
    const section = event.currentTarget.dataset.section;
    if (!['overview', 'records', 'entry'].includes(section)) return;
    if (section === 'entry' && !this.data.canWrite) {
      wx.showToast({ title: '当前角色只有查看权限', icon: 'none' });
      return;
    }
    this.setData({ activeSection: section, error: '' });
    wx.pageScrollTo({ selector: '#financeWorkspace', duration: 220 });
  },

  changeRecordPage(event) {
    const view = pageView(
      this.data.records,
      this.data.recordPage + (Number(event.currentTarget.dataset.delta) || 0),
      8,
    );
    this.setData({
      visibleRecords: view.items,
      recordPage: view.page,
      recordPageCount: view.pageCount,
      recordPageText: view.text,
    });
    wx.pageScrollTo({ selector: '#financeRecords', duration: 200 });
  },

  categoriesFor(kind) {
    if (kind === 'expense') return ['进货采购', '房租物业', '工资劳务', '水电网络', '营销推广', '税费', '其他支出'];
    if (kind === 'income') return ['现金收入', '转账收入', '补贴返还', '其他收入'];
    return ['线下服务', '商品销售', '临时消费', '其他消费'];
  },

  onEntryTypeChange(event) {
    const entryTypeIndex = Number(event.detail.value) || 0;
    const categoryLabels = this.categoriesFor(this.data.entryKinds[entryTypeIndex]);
    this.setData({ entryTypeIndex, categoryLabels, categoryIndex: 0 });
  },
  onCategoryChange(event) { this.setData({ categoryIndex: Number(event.detail.value) || 0 }); },
  onDateChange(event) { this.setData({ 'form.occurredOn': event.detail.value }); },
  onFormInput(event) { this.setData({ [`form.${event.currentTarget.dataset.field}`]: event.detail.value }); },

  async saveEntry() {
    if (this.data.saving || !this.data.selected || !this.data.canWrite) return;
    const form = this.data.form;
    if (!String(form.description || '').trim()) {
      this.setData({ error: '请填写这笔交易或支出的具体内容' });
      return;
    }
    let amountMinor = 0;
    try {
      amountMinor = money.yuanToMinor(form.amount);
    } catch (error) {
      this.setData({ error: error.message || '金额无效' });
      return;
    }
    const code = this.data.selected.public_code;
    const scope = `${code}:${this.data.entryKinds[this.data.entryTypeIndex]}:${form.occurredOn}:${amountMinor}`;
    this.setData({ saving: true, error: '' });
    try {
      let requestId = pending.get('operator-finance-entry', scope);
      if (!requestId) {
        requestId = await member.newRequestId('operator-finance-entry');
        pending.set('operator-finance-entry', scope, requestId);
      }
      await member.recordOperatorFinance(code, {
        entry_kind: this.data.entryKinds[this.data.entryTypeIndex],
        amount_minor: amountMinor,
        category: this.data.categoryLabels[this.data.categoryIndex],
        counterparty_name: String(form.counterparty || '').trim(),
        description: String(form.description || '').trim(),
        occurred_on: form.occurredOn,
      }, requestId);
      pending.clear('operator-finance-entry', scope);
      this.setData({
        activeSection: 'records',
        recordPage: 0,
        form: { amount: '', counterparty: '', description: '', occurredOn: localDate() },
      });
      await this.loadCompany(this.data.companyIndex);
      wx.showToast({ title: '经营流水已记录', icon: 'success' });
    } catch (error) {
      this.setData({ error: error.message || '记账失败' });
    } finally {
      this.setData({ saving: false });
    }
  },
});
