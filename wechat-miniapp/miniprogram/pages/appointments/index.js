const context = require('../../services/context');
const member = require('../../services/member');
const pending = require('../../store/pending');
const session = require('../../store/session');
const time = require('../../utils/time');
const money = require('../../utils/money');
const theme = require('../../utils/theme');

const STATUS = {
  pending: '待确认',
  confirmed: '已确认',
  completed: '已完成',
  cancelled: '已取消',
  no_show: '未到店',
};

function appointmentStatus(item) {
  if (item.fulfilment_outcome === 'merchant_no_show_reported') {
    return '已报告商家爽约 · 待确认';
  }
  if (item.fulfilment_outcome === 'merchant_no_show') {
    return '商家爽约 · 已补偿';
  }
  if (item.fulfilment_outcome === 'consumer_no_show') {
    return '用户爽约 · 已扣分';
  }
  return STATUS[item.status] || item.status;
}

Page({
  data: {
    loading: true,
    error: '',
    companyCode: '',
    companyName: '',
    companyCodes: [],
    companyNames: [],
    companyIndex: 0,
    appointments: [],
    activeCount: 0,
    completedCount: 0,
  },

  onShow() { this.load(); },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },

  async load() {
    const loadSequence = (this.loadSequence || 0) + 1;
    this.loadSequence = loadSequence;
    this.setData({
      loading: true,
      error: '',
      appointments: [],
      activeCount: 0,
      completedCount: 0,
    });
    try {
      const selected = await context.requireCompany();
      if (loadSequence !== this.loadSequence) return;
      if (!selected) {
        this.setData({ loading: false, appointments: [] });
        return;
      }
      const result = await member.appointments(selected.code);
      if (loadSequence !== this.loadSequence) return;
      const memberships = selected.memberships || [];
      const companyCodes = memberships.map((item) => item.company.code);
      let companyIndex = companyCodes.indexOf(selected.code);
      if (companyIndex < 0) companyIndex = 0;
      const rows = (result.appointments || []).map((item) => ({
        ...item,
        timeText: item.local_start || time.formatLocalDateTime(item.starts_at),
        priceText: money.formatMinor(item.price_minor),
        statusText: appointmentStatus(item),
        cancellable: (
          item.status === 'pending' || item.status === 'confirmed'
        ) && item.fulfilment_outcome !== 'merchant_no_show_reported',
        canReportMerchantNoShow: Boolean(item.can_report_merchant_no_show),
        merchantIncident: item.merchant_no_show_report,
        consumerIncident: item.consumer_no_show_penalty,
      }));
      this.setData({
        loading: false,
        companyCode: selected.code,
        companyName: selected.company.name,
        companyCodes,
        companyNames: memberships.map((item) => item.company.name),
        companyIndex,
        appointments: rows,
        activeCount: rows.filter(
          (item) => item.status === 'pending' || item.status === 'confirmed',
        ).length,
        completedCount: rows.filter((item) => item.status === 'completed').length,
      });
    } catch (error) {
      if (loadSequence !== this.loadSequence) return;
      this.setData({ loading: false, error: error.message || '预约记录加载失败' });
    }
  },

  onCompanyChange(event) {
    const index = Number(event.detail.value) || 0;
    const code = this.data.companyCodes[index];
    if (!code || code === this.data.companyCode) return;
    session.setCompany(code);
    this.setData({
      companyIndex: index,
      companyCode: code,
      companyName: this.data.companyNames[index] || '',
    });
    this.load();
  },

  async cancel(event) {
    if (this.cancelInFlight) return;
    const appointmentNo = event.currentTarget.dataset.no;
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '取消预约',
        content: '确定取消这次预约吗？',
        confirmColor: theme.current().accent,
        success: (result) => resolve(result.confirm),
        fail: () => resolve(false),
      });
    });
    if (!confirmed) return;
    this.cancelInFlight = true;
    try {
      await member.cancelAppointment(this.data.companyCode, appointmentNo, '消费者在 APP 中取消');
      wx.showToast({ title: '已取消', icon: 'success' });
      await this.load();
    } catch (error) {
      wx.showModal({ title: '取消失败', content: error.message || '请稍后重试', showCancel: false });
    } finally {
      this.cancelInFlight = false;
    }
  },

  async reportMerchantNoShow(event) {
    if (this.reportInFlight) return;
    const appointmentNo = event.currentTarget.dataset.no;
    const confirmed = await new Promise((resolve) => wx.showModal({
      title: '报告商家爽约',
      content: '提交后不会立即补分。商家确认未履约后，系统会自动补回你上一次消费获得的全部积分，并保留不可变事件记录。',
      confirmText: '提交报告',
      confirmColor: theme.current().accent,
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    }));
    if (!confirmed) return;
    this.reportInFlight = true;
    const scope = `${this.data.companyCode}:${appointmentNo}`;
    try {
      let requestId = pending.get('merchant-no-show-report', scope);
      if (!requestId) {
        requestId = await member.newRequestId('merchant-no-show-report');
        pending.set('merchant-no-show-report', scope, requestId);
      }
      await member.reportMerchantNoShow(
        this.data.companyCode,
        appointmentNo,
        '用户在 APP 中报告商家未按预约提供服务',
        requestId,
      );
      pending.clear('merchant-no-show-report', scope);
      wx.showToast({ title: '已等待商家确认', icon: 'success' });
      await this.load();
    } catch (error) {
      wx.showModal({
        title: '报告失败',
        content: error.message || '请稍后重试',
        showCancel: false,
      });
    } finally {
      this.reportInFlight = false;
    }
  },

  openBooking() { wx.switchTab({ url: '/pages/booking/index' }); },
  openCompanies() { context.openCompanies(); },
});
