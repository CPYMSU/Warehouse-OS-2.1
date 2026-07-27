const context = require('../../services/context');
const member = require('../../services/member');
const pending = require('../../store/pending');
const session = require('../../store/session');
const money = require('../../utils/money');

const NEAREST_SEARCH_DAYS = 21;
const KNOWN_TIMEZONE_OFFSETS = {
  'Asia/Singapore': 480,
  'Asia/Shanghai': 480,
  'Asia/Hong_Kong': 480,
  'Asia/Taipei': 480,
};

function dateText(offset) {
  const value = new Date(Date.now() + (offset || 0) * 86400000);
  const two = (part) => (`0${part}`).slice(-2);
  return `${value.getFullYear()}-${two(value.getMonth() + 1)}-${two(value.getDate())}`;
}

function validIsoDate(value) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(value || ''));
}

function dateInTimezone(timezone) {
  const zone = String(timezone || '').trim();
  try {
    if (zone && typeof Intl !== 'undefined' && Intl.DateTimeFormat) {
      const parts = new Intl.DateTimeFormat('en-US', {
        timeZone: zone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
      }).formatToParts(new Date());
      const values = {};
      parts.forEach((part) => { values[part.type] = part.value; });
      if (values.year && values.month && values.day) {
        return `${values.year}-${values.month}-${values.day}`;
      }
    }
  } catch (error) {
    // Older base libraries may not ship full IANA timezone data. The supported
    // operator timezone list has an explicit UTC-minute fallback below.
  }
  if (Object.prototype.hasOwnProperty.call(KNOWN_TIMEZONE_OFFSETS, zone)) {
    const shifted = new Date(Date.now() + KNOWN_TIMEZONE_OFFSETS[zone] * 60000);
    const two = (part) => (`0${part}`).slice(-2);
    return `${shifted.getUTCFullYear()}-${two(shifted.getUTCMonth() + 1)}-${two(shifted.getUTCDate())}`;
  }
  return dateText(0);
}

function diagnosticMessages(result) {
  const source = result && (result.availability_diagnostics || result.diagnostics);
  if (!source) return [];
  let rows = Array.isArray(source) ? source : [];
  if (!rows.length && typeof source === 'object') {
    rows = source.messages || source.items || source.reasons || source.blockers || [];
    if (!Array.isArray(rows)) rows = [rows];
    if (!rows.length && (source.message || source.reason || source.detail)) rows = [source];
  }
  if (!rows.length && typeof source === 'string') rows = [source];
  return Array.from(new Set(rows.map((item) => {
    if (typeof item === 'string') return item.trim();
    if (!item || typeof item !== 'object') return '';
    return String(item.message || item.detail || item.reason || item.label || '').trim();
  }).filter(Boolean)));
}

Page({
  data: {
    loading: true,
    loadingSlots: false,
    error: '',
    companyCode: '',
    companyName: '',
    companyCodes: [],
    companyNames: [],
    companyIndex: 0,
    services: [],
    serviceNames: [],
    serviceIndex: 0,
    staff: [],
    staffNames: ['任意工作人员'],
    staffIndex: 0,
    minDate: dateText(0),
    selectedDate: dateText(0),
    companyTimezone: '',
    slots: [],
    selectedService: null,
    slotNotice: '',
    emptySlotsText: '',
    availabilityDiagnostics: [],
  },

  onShow() {
    this.refreshBookingDate(this.data.companyTimezone);
    this.load();
  },
  onPullDownRefresh() { this.load().finally(() => wx.stopPullDownRefresh()); },

  async load() {
    const loadSequence = (this.loadSequence || 0) + 1;
    this.loadSequence = loadSequence;
    this.slotSequence = (this.slotSequence || 0) + 1;
    this.setData({
      loading: true,
      error: '',
      services: [],
      serviceNames: [],
      staff: [],
      availableStaff: [],
      staffNames: ['任意工作人员'],
      serviceIndex: 0,
      staffIndex: 0,
      slots: [],
      selectedService: null,
      slotNotice: '',
      emptySlotsText: '',
      availabilityDiagnostics: [],
    });
    try {
      const selected = await context.requireCompany();
      if (loadSequence !== this.loadSequence) return;
      if (!selected) {
        this.setData({ loading: false });
        return;
      }
      const catalog = await member.bookingCatalog(selected.code);
      if (loadSequence !== this.loadSequence) return;
      const memberships = selected.memberships || [];
      const companyCodes = memberships.map((item) => item.company.code);
      let companyIndex = companyCodes.indexOf(selected.code);
      if (companyIndex < 0) companyIndex = 0;
      const services = (catalog.services || []).map((item) => ({
        ...item,
        priceText: money.formatMinor(item.price_minor),
      }));
      const staff = catalog.staff || [];
      const location = (catalog.locations || [])[0] || {};
      const dateState = this.bookingDateState(location.timezone || '');
      this.setData({
        loading: false,
        companyCode: selected.code,
        companyName: selected.company.name,
        companyCodes,
        companyNames: memberships.map((item) => item.company.name),
        companyIndex,
        services,
        serviceNames: services.map((item) => item.name),
        staff,
        serviceIndex: 0,
        staffIndex: 0,
        selectedService: services[0] || null,
        companyTimezone: location.timezone || '',
        minDate: dateState.minDate,
        selectedDate: dateState.selectedDate,
      });
      this.refreshStaff();
      if (services.length) {
        await this.loadSlots({ findNearest: true, tryOtherServices: true });
      }
    } catch (error) {
      if (loadSequence !== this.loadSequence) return;
      this.setData({ loading: false, error: error.message || '预约服务加载失败' });
    }
  },

  refreshStaff() {
    const selectedService = this.data.services[this.data.serviceIndex];
    const staff = (this.data.staff || []).filter((person) => {
      const codes = person.service_codes || [];
      return !codes.length || (selectedService && codes.indexOf(selectedService.code) >= 0);
    });
    this.setData({
      availableStaff: staff,
      staffNames: ['任意工作人员'].concat(staff.map((item) => item.name)),
      staffIndex: 0,
      selectedService: selectedService || null,
    });
  },

  bookingDateState(timezone, serverToday) {
    const today = validIsoDate(serverToday) ? serverToday : dateInTimezone(timezone);
    const timezoneChanged = Boolean(
      timezone && timezone !== (this.data.companyTimezone || ''),
    );
    let selectedDate = this.data.selectedDate;
    if (!this.bookingDateReady || timezoneChanged || !validIsoDate(selectedDate) || selectedDate < today) {
      selectedDate = today;
    }
    this.bookingDateReady = true;
    return { minDate: today, selectedDate };
  },

  refreshBookingDate(timezone, serverToday) {
    const state = this.bookingDateState(timezone, serverToday);
    this.setData(state);
    return state;
  },

  async loadSlots(options) {
    const services = this.data.services || [];
    if (!services.length || !this.data.companyCode) return;
    const initialServiceIndex = Math.min(
      Math.max(Number(this.data.serviceIndex) || 0, 0),
      services.length - 1,
    );
    const findNearest = Boolean(options && options.findNearest);
    const tryOtherServices = Boolean(options && options.tryOtherServices);
    const person = this.data.staffIndex > 0
      ? (this.data.availableStaff || [])[this.data.staffIndex - 1]
      : null;
    const requestedDate = this.data.selectedDate;
    const slotSequence = (this.slotSequence || 0) + 1;
    this.slotSequence = slotSequence;
    this.setData({
      loadingSlots: true,
      error: '',
      slots: [],
      slotNotice: '',
      emptySlotsText: '',
      availabilityDiagnostics: [],
    });
    try {
      const indexes = tryOtherServices
        ? services.map((_item, index) => index)
        : [initialServiceIndex];
      const requestService = async (index, searchDays) => ({
        index,
        result: await member.bookingSlots(this.data.companyCode, {
          service_code: services[index].code,
          date: requestedDate,
          staff_code: index === initialServiceIndex && person ? person.code : undefined,
          search_days: searchDays,
        }),
      });
      let entries = await Promise.all(indexes.map((index) => (
        requestService(index, tryOtherServices ? 0 : (findNearest ? NEAREST_SEARCH_DAYS : 0))
      )));
      if (slotSequence !== this.slotSequence) return;
      const hasSlots = (entry) => Boolean(
        entry && entry.result && Array.isArray(entry.result.slots) && entry.result.slots.length,
      );
      let chosen = entries.find((entry) => (
        entry.index === initialServiceIndex && hasSlots(entry)
      )) || entries.find(hasSlots) || entries.find((entry) => (
        entry.index === initialServiceIndex
      )) || entries[0];

      if (!hasSlots(chosen) && findNearest && tryOtherServices) {
        entries = await Promise.all(indexes.map((index) => (
          requestService(index, NEAREST_SEARCH_DAYS)
        )));
        if (slotSequence !== this.slotSequence) return;
        const available = entries.filter(hasSlots).sort((left, right) => {
          const leftFirst = (left.result.slots[0] || {}).starts_at || '';
          const rightFirst = (right.result.slots[0] || {}).starts_at || '';
          const leftRank = `${left.result.date || requestedDate}:${leftFirst}`;
          const rightRank = `${right.result.date || requestedDate}:${rightFirst}`;
          if (leftRank !== rightRank) return leftRank < rightRank ? -1 : 1;
          if (left.index === initialServiceIndex) return -1;
          if (right.index === initialServiceIndex) return 1;
          return left.index - right.index;
        });
        chosen = available[0] || entries.find((entry) => (
          entry.index === initialServiceIndex
        )) || entries[0] || chosen;
      }

      const result = chosen.result;
      const chosenServiceIndex = chosen.index;
      const chosenService = services[chosenServiceIndex];
      const switchedService = chosenServiceIndex !== initialServiceIndex;
      const slots = (result.slots || []).map((item) => ({
        ...item,
        slotKey: `${item.starts_at}:${item.staff ? item.staff.code : 'location'}`,
      }));
      const dateState = this.bookingDateState(
        result.timezone || this.data.companyTimezone,
        result.today || result.local_today,
      );
      const responseDate = validIsoDate(result.date) ? result.date : dateState.selectedDate;
      const resolvedDate = responseDate < dateState.minDate
        ? dateState.selectedDate
        : responseDate;
      const diagnostics = diagnosticMessages(
        result.auto_advanced && result.requested_date_diagnostics
          ? { diagnostics: result.requested_date_diagnostics }
          : result,
      );
      const emptySlotsText = slots.length
        ? ''
        : findNearest
          ? `已检查至 ${result.searched_through || resolvedDate}，仍没有可预约时间。`
            + `当前服务单次占用为 ${chosenService.duration_minutes} 分钟，请经营者检查它是否能完整放入工作室与服务排班。`
          : '所选日期暂无可预约时间；你可以更换日期，或让系统寻找最近真正可约的一天。';
      const availableStaff = (this.data.staff || []).filter((item) => {
        const codes = item.service_codes || [];
        return !codes.length || codes.indexOf(chosenService.code) >= 0;
      });
      const notices = [];
      if (switchedService) {
        notices.push(`已自动切换到当天可预约服务「${chosenService.name}」`);
      }
      if (result.auto_advanced) {
        notices.push(`已自动跳至最近可预约日期 ${resolvedDate}`);
      }
      this.setData({
        slots,
        loadingSlots: false,
        serviceIndex: chosenServiceIndex,
        selectedService: chosenService,
        availableStaff,
        staffNames: ['任意工作人员'].concat(availableStaff.map((item) => item.name)),
        staffIndex: switchedService ? 0 : this.data.staffIndex,
        selectedDate: resolvedDate,
        minDate: dateState.minDate,
        slotNotice: notices.join('；'),
        emptySlotsText,
        availabilityDiagnostics: diagnostics,
      });
    } catch (error) {
      if (slotSequence !== this.slotSequence) return;
      this.setData({ loadingSlots: false, error: error.message || '可预约时间加载失败' });
    }
  },

  onServiceChange(event) {
    this.setData({ serviceIndex: Number(event.detail.value) || 0 });
    this.refreshStaff();
    this.loadSlots({ findNearest: true });
  },

  onStaffChange(event) {
    this.setData({ staffIndex: Number(event.detail.value) || 0 });
    this.loadSlots({ findNearest: true });
  },

  onDateChange(event) {
    this.setData({ selectedDate: event.detail.value });
    return this.loadSlots({ tryOtherServices: true });
  },

  findNearestSlots() {
    return this.loadSlots({ findNearest: true, tryOtherServices: true });
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

  async book(event) {
    if (this.bookingInFlight) return;
    const slot = this.data.slots[Number(event.currentTarget.dataset.index)];
    const service = this.data.services[this.data.serviceIndex];
    if (!slot || !service) return;
    const confirm = await new Promise((resolve) => {
      wx.showModal({
        title: '确认预约',
        content: `${this.data.companyName}\n${service.name}\n${slot.local_date} ${slot.local_start}–${slot.local_end}${slot.staff ? `\n${slot.staff.name}` : ''}`,
        confirmText: '确认预约',
        success: (result) => resolve(result.confirm),
        fail: () => resolve(false),
      });
    });
    if (!confirm) return;
    const scope = `${this.data.companyCode}:${service.code}:${slot.starts_at}:${slot.staff ? slot.staff.code : 'any'}`;
    this.bookingInFlight = true;
    wx.showLoading({ title: '正在预约', mask: true });
    try {
      let requestId = pending.get('appointment', scope);
      if (!requestId) {
        requestId = await member.newRequestId('appointment');
        pending.set('appointment', scope, requestId);
      }
      await member.createAppointment(this.data.companyCode, {
        service_code: service.code,
        starts_at: slot.starts_at,
        staff_code: slot.staff && slot.staff.code,
      }, requestId);
      pending.clear('appointment', scope);
      wx.showToast({ title: '预约成功', icon: 'success' });
      setTimeout(() => wx.switchTab({ url: '/pages/appointments/index' }), 500);
    } catch (error) {
      if (error && error.statusCode) pending.clear('appointment', scope);
      wx.showModal({ title: '预约未完成', content: error.message || '请稍后重试', showCancel: false });
      this.loadSlots();
    } finally {
      wx.hideLoading();
      this.bookingInFlight = false;
    }
  },

  openCompanies() { context.openCompanies(); },
});
