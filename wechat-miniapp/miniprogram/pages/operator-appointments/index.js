const member = require('../../services/member');
const session = require('../../store/session');
const pending = require('../../store/pending');
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
    return '用户报告商家爽约';
  }
  if (item.fulfilment_outcome === 'merchant_no_show') {
    return '商家爽约已确认';
  }
  if (item.fulfilment_outcome === 'consumer_no_show') {
    return '用户爽约已扣分';
  }
  return STATUS[item.status] || item.status;
}

Page({
  data: {
    loading: true,
    error: '',
    companyCode: '',
    appointments: [],
  },

  onShow() { this.load(); },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },

  async load() {
    const code = session.operatorCompany();
    if (!code) {
      this.setData({ loading: false, error: '请先选择经营公司' });
      return;
    }
    this.setData({ loading: true, error: '' });
    try {
      const result = await member.operatorAppointments(code);
      const rows = (result.appointments || []).map((item) => ({
        ...item,
        statusText: appointmentStatus(item),
        timeText: item.local_start || time.formatLocalDateTime(item.starts_at),
        priceText: money.formatMinor(item.price_minor),
        canConfirm: item.status === 'pending'
          && item.fulfilment_outcome !== 'merchant_no_show_reported',
        canFinish: item.status === 'confirmed'
          && item.fulfilment_outcome !== 'merchant_no_show_reported',
        canConsumerNoShow: Boolean(item.can_mark_consumer_no_show),
        canCancel: (
          item.status === 'pending' || item.status === 'confirmed'
        ) && item.fulfilment_outcome !== 'merchant_no_show_reported',
        merchantIncident: item.merchant_no_show_report,
        consumerIncident: item.consumer_no_show_penalty,
      }));
      this.setData({ loading: false, companyCode: code, appointments: rows });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '预约管理加载失败' });
    }
  },

  async act(event) {
    if (this.actionInFlight) return;
    const appointmentNo = event.currentTarget.dataset.no;
    const status = event.currentTarget.dataset.status;
    const labels = {
      confirmed: '确认这次预约？',
      completed: '标记为已完成？',
      consumer_no_show: '确认客户未到店？系统会立即按强规则扣除其上一次消费获得的积分，用户无需再次确认。',
      cancelled: '取消这次预约？',
    };
    const confirmed = await new Promise((resolve) => {
      wx.showModal({
        title: '更新预约',
        content: labels[status] || '确认更新状态？',
        confirmColor: status === 'cancelled' ? theme.current().accent : theme.current().ink,
        success: (result) => resolve(result.confirm),
        fail: () => resolve(false),
      });
    });
    if (!confirmed) return;
    this.actionInFlight = true;
    try {
      await member.updateAppointmentStatus(
        this.data.companyCode,
        appointmentNo,
        status,
        '经营者在 APP 中更新',
      );
      wx.showToast({ title: '状态已更新', icon: 'success' });
      await this.load();
    } catch (error) {
      wx.showModal({ title: '更新失败', content: error.message || '请稍后重试', showCancel: false });
    } finally {
      this.actionInFlight = false;
    }
  },

  async resolveMerchantNoShow(event) {
    if (this.resolveInFlight) return;
    const appointmentNo = event.currentTarget.dataset.no;
    const decision = event.currentTarget.dataset.decision;
    let confirmed = false;
    try {
      confirmed = await new Promise((resolve, reject) => wx.showModal({
        title: decision === 'confirm' ? '确认商家爽约' : '不确认爽约报告',
        content: decision === 'confirm'
          ? '确认后，系统会自动补给用户上一次消费获得的全部积分，并把预约写入不可变事件及 Warehouse 档案草稿。'
          : '拒绝后不会补分，报告会保留为已拒绝记录。',
        confirmText: decision === 'confirm' ? '确认补分' : '拒绝报告',
        confirmColor: decision === 'confirm' ? '#167A55' : theme.current().accent,
        success: (result) => resolve(result.confirm),
        fail: () => reject(new Error('爽约处理窗口打开失败，请重试')),
      }));
    } catch (error) {
      wx.showToast({ title: error.message || '爽约处理窗口打开失败', icon: 'none' });
      return;
    }
    if (!confirmed) return;
    this.resolveInFlight = true;
    const scope = `${this.data.companyCode}:${appointmentNo}:${decision}`;
    try {
      let requestId = pending.get('merchant-no-show-resolution', scope);
      if (!requestId) {
        requestId = await member.newRequestId(`merchant-no-show-${decision}`);
        pending.set('merchant-no-show-resolution', scope, requestId);
      }
      await member.operatorResolveMerchantNoShow(
        this.data.companyCode,
        appointmentNo,
        decision,
        decision === 'confirm'
          ? '经营者确认商家未按预约履约'
          : '经营者不确认该爽约报告',
        requestId,
      );
      pending.clear('merchant-no-show-resolution', scope);
      wx.showToast({
        title: decision === 'confirm' ? '已补偿积分' : '报告已拒绝',
        icon: 'success',
      });
      await this.load();
    } catch (error) {
      wx.showModal({
        title: '处理失败',
        content: error.message || '请稍后重试',
        showCancel: false,
      });
    } finally {
      this.resolveInFlight = false;
    }
  },
});
