const member = require('../../services/member');
const session = require('../../store/session');
const money = require('../../utils/money');

const WEEKDAYS = [
  { value: '0', label: '一' },
  { value: '1', label: '二' },
  { value: '2', label: '三' },
  { value: '3', label: '四' },
  { value: '4', label: '五' },
  { value: '5', label: '六' },
  { value: '6', label: '日' },
];

const TIMEZONES = [
  { value: 'Asia/Singapore', label: '新加坡 / Singapore' },
  { value: 'Asia/Shanghai', label: '中国大陆 / Shanghai' },
  { value: 'Asia/Hong_Kong', label: '香港 / Hong Kong' },
  { value: 'Asia/Taipei', label: '台北 / Taipei' },
];

function checkedWeekdays(selected) {
  return WEEKDAYS.map((item) => ({
    ...item,
    checked: (selected || []).indexOf(item.value) >= 0,
  }));
}

function schedulePeriodsFromRules(rules, keyPrefix) {
  const grouped = {};
  (rules || []).forEach((rule) => {
    const key = `${rule.start}|${rule.end}`;
    if (!grouped[key]) grouped[key] = { start: rule.start, end: rule.end, days: [] };
    grouped[key].days.push(String(rule.weekday));
  });
  return Object.keys(grouped).map((key, index) => {
    const group = grouped[key];
    const selectedWeekdays = Array.from(new Set(group.days)).sort();
    return {
      key: `${keyPrefix}-${index}-${group.start.replace(':', '')}`,
      start: group.start,
      end: group.end,
      selectedWeekdays,
      weekdays: checkedWeekdays(selectedWeekdays),
    };
  }).sort((a, b) => (
    Number(a.selectedWeekdays[0] || 7) - Number(b.selectedWeekdays[0] || 7)
    || a.start.localeCompare(b.start)
  ));
}

function openingPeriodsFromRules(rules) {
  if (rules && rules.length) return schedulePeriodsFromRules(rules, 'opening');
  const selectedWeekdays = ['0', '1', '2', '3', '4'];
  return [{
    key: 'opening-default',
    start: '09:00',
    end: '18:00',
    selectedWeekdays,
    weekdays: checkedWeekdays(selectedWeekdays),
  }];
}

function periodsFromOpening(openingPeriods, keyPrefix) {
  return (openingPeriods || []).map((period, index) => {
    const selectedWeekdays = (period.selectedWeekdays || []).slice();
    return {
      key: `${keyPrefix}-${Date.now().toString(36)}-${index}`,
      start: period.start,
      end: period.end,
      selectedWeekdays,
      weekdays: checkedWeekdays(selectedWeekdays),
    };
  });
}

function timeMinutes(value) {
  const parts = String(value || '').split(':');
  return (Number(parts[0]) * 60) + Number(parts[1]);
}

function maximumOpenOverlap(period, openingPeriods) {
  const merged = (openingPeriods || [])
    .map((item) => ({ start: timeMinutes(item.start), end: timeMinutes(item.end) }))
    .sort((a, b) => a.start - b.start)
    .reduce((all, item) => {
      const previous = all[all.length - 1];
      if (previous && item.start <= previous.end) {
        previous.end = Math.max(previous.end, item.end);
      } else {
        all.push({ ...item });
      }
      return all;
    }, []);
  const start = timeMinutes(period.start);
  const end = timeMinutes(period.end);
  return merged.reduce((best, opening) => (
    Math.max(best, Math.min(end, opening.end) - Math.max(start, opening.start))
  ), 0);
}

function mergeMinuteWindows(windows) {
  return (windows || [])
    .map((item) => ({ start: Number(item.start), end: Number(item.end) }))
    .filter((item) => Number.isFinite(item.start) && Number.isFinite(item.end) && item.start < item.end)
    .sort((a, b) => a.start - b.start || a.end - b.end)
    .reduce((all, item) => {
      const previous = all[all.length - 1];
      if (previous && item.start <= previous.end) {
        previous.end = Math.max(previous.end, item.end);
      } else {
        all.push({ ...item });
      }
      return all;
    }, []);
}

function weekdayWindows(periods, weekday) {
  const day = String(weekday);
  return mergeMinuteWindows((periods || [])
    .filter((period) => (period.selectedWeekdays || []).indexOf(day) >= 0)
    .map((period) => ({ start: timeMinutes(period.start), end: timeMinutes(period.end) })));
}

function intersectMinuteWindows(left, right) {
  const intersections = [];
  (left || []).forEach((leftWindow) => {
    (right || []).forEach((rightWindow) => {
      const start = Math.max(leftWindow.start, rightWindow.start);
      const end = Math.min(leftWindow.end, rightWindow.end);
      if (start < end) intersections.push({ start, end });
    });
  });
  return mergeMinuteWindows(intersections);
}

function hasAlignedSlot(windows, duration, interval, bufferBefore, bufferAfter) {
  const before = Number(bufferBefore || 0);
  const after = Number(bufferAfter || 0);
  return (windows || []).some((window) => {
    // The cadence is anchored to each concrete opening window, matching the
    // server.  For example, a 09:15 opening with a 30-minute interval yields
    // 09:15, 09:45, ... rather than being shifted to 09:30.
    const firstStart = window.start + before;
    return firstStart + duration + after <= window.end;
  });
}

function validatePeriodRows(periods, label) {
  if (!periods || !periods.length) throw new Error(`${label}请至少添加一个时段`);
  const byWeekday = {};
  periods.forEach((period, periodIndex) => {
    if (!period.selectedWeekdays || !period.selectedWeekdays.length) {
      throw new Error(`${label}时段 ${periodIndex + 1} 请至少选择一个星期`);
    }
    if (period.end <= period.start) {
      throw new Error(`${label}时段 ${periodIndex + 1} 的结束时间必须晚于开始时间`);
    }
    period.selectedWeekdays.forEach((weekday) => {
      if (!byWeekday[weekday]) byWeekday[weekday] = [];
      byWeekday[weekday].push({ start: period.start, end: period.end });
    });
  });
  Object.keys(byWeekday).forEach((weekday) => {
    const rows = byWeekday[weekday].sort((a, b) => a.start.localeCompare(b.start));
    for (let index = 1; index < rows.length; index += 1) {
      if (rows[index].start < rows[index - 1].end) {
        throw new Error(`${label}星期${WEEKDAYS[Number(weekday)].label}的时段互相重叠`);
      }
    }
  });
}

function timezoneIndex(value) {
  const index = TIMEZONES.findIndex((item) => item.value === value);
  return index >= 0 ? index : 0;
}

function minorAllowZero(value) {
  const text = String(value == null ? '' : value).trim();
  if (!/^\d+(?:\.\d{0,2})?$/.test(text)) throw new Error('请输入正确金额');
  const minor = Math.round(Number(text) * 100);
  if (!Number.isSafeInteger(minor) || minor < 0) throw new Error('金额不能小于 0');
  return minor;
}

Page({
  data: {
    loading: true,
    saving: false,
    error: '',
    companyCode: '',
    companyName: '',
    location: {
      name: '',
      address: '',
      start: '09:00',
      end: '18:00',
      interval: '30',
      notice: '60',
      timezone: TIMEZONES[0].value,
    },
    timezoneNames: TIMEZONES.map((item) => item.label),
    timezoneIndex: 0,
    openingPeriods: openingPeriodsFromRules([]),
    selectedWeekdays: ['0', '1', '2', '3', '4'],
    weekdays: checkedWeekdays(['0', '1', '2', '3', '4']),
    services: [],
    staff: [],
    timeBlocks: [],
    diagnostics: [],
  },

  onLoad() { this.load(); },

  async load() {
    const code = session.operatorCompany();
    if (!code) {
      this.setData({ loading: false, error: '请先选择经营公司' });
      return;
    }
    try {
      const dashboard = await member.operatorBooking(code);
      const sourceLocation = (dashboard.locations || []).find((item) => item.active) || {};
      const locationRules = (dashboard.schedule_rules || []).filter(
        (item) => item.scope_type === 'location' && item.scope_code === sourceLocation.code && item.active,
      );
      const openingPeriods = openingPeriodsFromRules(locationRules);
      const selectedWeekdays = Array.from(new Set(
        openingPeriods.reduce((all, period) => all.concat(period.selectedWeekdays), []),
      )).sort();
      const locationStart = openingPeriods[0].start;
      const locationEnd = openingPeriods[0].end;
      const services = (dashboard.services || []).filter((item) => item.active).map((item) => ({
        code: item.code,
        name: item.name,
        duration: String(item.duration_minutes),
        price: money.formatMinor(item.price_minor),
        deposit: money.formatMinor(item.deposit_minor),
        description: item.description || '',
        bufferBefore: Number(item.buffer_before_minutes || 0),
        bufferAfter: Number(item.buffer_after_minutes || 0),
        capacity: Number(item.capacity || 1),
        customSchedule: (dashboard.schedule_rules || []).some(
          (rule) => rule.scope_type === 'service' && rule.scope_code === item.code && rule.active,
        ),
        periods: (() => {
          const serviceRules = (dashboard.schedule_rules || []).filter(
            (rule) => rule.scope_type === 'service' && rule.scope_code === item.code && rule.active,
          );
          return serviceRules.length
            ? schedulePeriodsFromRules(serviceRules, `service-${item.code}`)
            : periodsFromOpening(openingPeriods, `service-${item.code}`);
        })(),
      }));
      const locationTimezone = sourceLocation.timezone || TIMEZONES[0].value;
      const staff = (dashboard.staff || []).filter((item) => item.active).map((item) => {
        const staffRules = (dashboard.schedule_rules || []).filter(
          (rule) => rule.scope_type === 'staff' && rule.scope_code === item.code && rule.active,
        );
        return {
          code: item.code,
          name: item.name,
          title: item.title || '',
          customSchedule: staffRules.length > 0,
          periods: staffRules.length
            ? schedulePeriodsFromRules(staffRules, `staff-${item.code}`)
            : periodsFromOpening(openingPeriods, `staff-${item.code}`),
        };
      });
      this.setData({
        loading: false,
        companyCode: code,
        companyName: dashboard.company.name,
        location: {
          name: sourceLocation.name || dashboard.company.name,
          address: sourceLocation.address || '',
          start: locationStart,
          end: locationEnd,
          interval: String(sourceLocation.slot_interval_minutes || 30),
          notice: String(sourceLocation.min_notice_minutes || 60),
          timezone: locationTimezone,
        },
        timezoneIndex: timezoneIndex(locationTimezone),
        openingPeriods,
        selectedWeekdays,
        weekdays: checkedWeekdays(selectedWeekdays),
        services: services.length ? services : [{
          code: 'service-1', name: '', duration: '60', price: '0.00', deposit: '0.00',
          description: '', bufferBefore: 0, bufferAfter: 0, capacity: 1,
          customSchedule: false,
          periods: periodsFromOpening(openingPeriods, 'service-service-1'),
        }],
        staff,
        timeBlocks: Array.isArray(dashboard.time_blocks) ? dashboard.time_blocks : [],
        diagnostics: Array.isArray(dashboard.diagnostics) ? dashboard.diagnostics : [],
      });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '设置加载失败' });
    }
  },

  onLocationInput(event) {
    const field = event.currentTarget.dataset.field;
    this.setData({ [`location.${field}`]: event.detail.value });
  },

  onTimezoneChange(event) {
    const index = Number(event.detail.value) || 0;
    this.setData({
      timezoneIndex: index,
      'location.timezone': TIMEZONES[index].value,
    });
  },
  onOpeningWeekdays(event) {
    const index = Number(event.currentTarget.dataset.index);
    const selectedWeekdays = event.detail.value || [];
    this.setData({
      [`openingPeriods[${index}].selectedWeekdays`]: selectedWeekdays,
      [`openingPeriods[${index}].weekdays`]: checkedWeekdays(selectedWeekdays),
    }, () => this.syncLocationWeekdays());
  },

  onOpeningStartChange(event) {
    const index = Number(event.currentTarget.dataset.index);
    this.setData(
      { [`openingPeriods[${index}].start`]: event.detail.value },
      () => this.syncLocationWeekdays(),
    );
  },

  onOpeningEndChange(event) {
    const index = Number(event.currentTarget.dataset.index);
    this.setData(
      { [`openingPeriods[${index}].end`]: event.detail.value },
      () => this.syncLocationWeekdays(),
    );
  },

  syncLocationWeekdays() {
    const selectedWeekdays = Array.from(new Set(
      this.data.openingPeriods.reduce(
        (all, period) => all.concat(period.selectedWeekdays || []), [],
      ),
    )).sort();
    const first = this.data.openingPeriods[0];
    const services = this.data.services.map((service, index) => (
      service.customSchedule ? service : {
        ...service,
        periods: periodsFromOpening(
          this.data.openingPeriods,
          `service-${service.code || index}`,
        ),
      }
    ));
    this.setData({
      selectedWeekdays,
      weekdays: checkedWeekdays(selectedWeekdays),
      'location.start': first ? first.start : '09:00',
      'location.end': first ? first.end : '18:00',
      services,
    });
  },

  addOpeningPeriod() {
    const index = this.data.openingPeriods.length;
    const openingPeriods = this.data.openingPeriods.concat([{
      key: `opening-${Date.now().toString(36)}-${index}`,
      start: '09:00',
      end: '18:00',
      selectedWeekdays: [],
      weekdays: checkedWeekdays([]),
    }]);
    this.setData({ openingPeriods });
  },

  removeOpeningPeriod(event) {
    if (this.data.openingPeriods.length <= 1) return;
    const index = Number(event.currentTarget.dataset.index);
    const openingPeriods = this.data.openingPeriods.filter((_item, row) => row !== index);
    this.setData({ openingPeriods }, () => this.syncLocationWeekdays());
  },

  onServiceInput(event) {
    const index = Number(event.currentTarget.dataset.index);
    const field = event.currentTarget.dataset.field;
    this.setData({ [`services[${index}].${field}`]: event.detail.value });
  },

  onServiceScheduleToggle(event) {
    const index = Number(event.currentTarget.dataset.index);
    const customSchedule = Boolean(event.detail.value);
    const service = this.data.services[index];
    const periods = service.periods && service.periods.length
      ? service.periods
      : periodsFromOpening(this.data.openingPeriods, `service-${service.code || index}`);
    this.setData({
      [`services[${index}].customSchedule`]: customSchedule,
      [`services[${index}].periods`]: periods,
    });
  },

  addServicePeriod(event) {
    const serviceIndex = Number(event.currentTarget.dataset.index);
    const service = this.data.services[serviceIndex];
    const periodIndex = (service.periods || []).length;
    const firstOpening = this.data.openingPeriods[0] || {
      start: '09:00', end: '18:00', selectedWeekdays: [],
    };
    const selectedWeekdays = (firstOpening.selectedWeekdays || []).slice();
    const periods = (service.periods || []).concat([{
      key: `service-${service.code || serviceIndex}-${Date.now().toString(36)}-${periodIndex}`,
      start: firstOpening.start,
      end: firstOpening.end,
      selectedWeekdays,
      weekdays: checkedWeekdays(selectedWeekdays),
    }]);
    this.setData({ [`services[${serviceIndex}].periods`]: periods });
  },

  removeServicePeriod(event) {
    const serviceIndex = Number(event.currentTarget.dataset.serviceIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    const service = this.data.services[serviceIndex];
    if (!service.periods || service.periods.length <= 1) return;
    this.setData({
      [`services[${serviceIndex}].periods`]: service.periods.filter(
        (_period, index) => index !== periodIndex,
      ),
    });
  },

  onServiceWeekdays(event) {
    const serviceIndex = Number(event.currentTarget.dataset.serviceIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    const selectedWeekdays = event.detail.value || [];
    this.setData({
      [`services[${serviceIndex}].periods[${periodIndex}].selectedWeekdays`]: selectedWeekdays,
      [`services[${serviceIndex}].periods[${periodIndex}].weekdays`]: checkedWeekdays(selectedWeekdays),
    });
  },

  onServiceStartChange(event) {
    const serviceIndex = Number(event.currentTarget.dataset.serviceIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    this.setData({
      [`services[${serviceIndex}].periods[${periodIndex}].start`]: event.detail.value,
    });
  },

  onServiceEndChange(event) {
    const serviceIndex = Number(event.currentTarget.dataset.serviceIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    this.setData({
      [`services[${serviceIndex}].periods[${periodIndex}].end`]: event.detail.value,
    });
  },

  onStaffInput(event) {
    const index = Number(event.currentTarget.dataset.index);
    const field = event.currentTarget.dataset.field;
    this.setData({ [`staff[${index}].${field}`]: event.detail.value });
  },

  onStaffScheduleToggle(event) {
    const index = Number(event.currentTarget.dataset.index);
    const customSchedule = Boolean(event.detail.value);
    const staff = this.data.staff[index];
    const periods = staff.periods && staff.periods.length
      ? staff.periods
      : periodsFromOpening(this.data.openingPeriods, `staff-${staff.code || index}`);
    this.setData({
      [`staff[${index}].customSchedule`]: customSchedule,
      [`staff[${index}].periods`]: periods,
    });
  },

  addStaffPeriod(event) {
    const staffIndex = Number(event.currentTarget.dataset.index);
    const person = this.data.staff[staffIndex];
    const periodIndex = (person.periods || []).length;
    const firstOpening = this.data.openingPeriods[0] || {
      start: '09:00', end: '18:00', selectedWeekdays: [],
    };
    const selectedWeekdays = (firstOpening.selectedWeekdays || []).slice();
    const periods = (person.periods || []).concat([{
      key: `staff-${person.code || staffIndex}-${Date.now().toString(36)}-${periodIndex}`,
      start: firstOpening.start,
      end: firstOpening.end,
      selectedWeekdays,
      weekdays: checkedWeekdays(selectedWeekdays),
    }]);
    this.setData({ [`staff[${staffIndex}].periods`]: periods });
  },

  removeStaffPeriod(event) {
    const staffIndex = Number(event.currentTarget.dataset.staffIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    const person = this.data.staff[staffIndex];
    if (!person.periods || person.periods.length <= 1) return;
    this.setData({
      [`staff[${staffIndex}].periods`]: person.periods.filter(
        (_period, index) => index !== periodIndex,
      ),
    });
  },

  onStaffWeekdays(event) {
    const staffIndex = Number(event.currentTarget.dataset.staffIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    const selectedWeekdays = event.detail.value || [];
    this.setData({
      [`staff[${staffIndex}].periods[${periodIndex}].selectedWeekdays`]: selectedWeekdays,
      [`staff[${staffIndex}].periods[${periodIndex}].weekdays`]: checkedWeekdays(selectedWeekdays),
    });
  },

  onStaffStartChange(event) {
    const staffIndex = Number(event.currentTarget.dataset.staffIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    this.setData({
      [`staff[${staffIndex}].periods[${periodIndex}].start`]: event.detail.value,
    });
  },

  onStaffEndChange(event) {
    const staffIndex = Number(event.currentTarget.dataset.staffIndex);
    const periodIndex = Number(event.currentTarget.dataset.periodIndex);
    this.setData({
      [`staff[${staffIndex}].periods[${periodIndex}].end`]: event.detail.value,
    });
  },

  addService() {
    const services = this.data.services.concat([{
      code: `service-${this.data.services.length + 1}`,
      name: '',
      duration: '60',
      price: '0.00',
      deposit: '0.00',
      description: '',
      bufferBefore: 0,
      bufferAfter: 0,
      capacity: 1,
      customSchedule: false,
      periods: periodsFromOpening(
        this.data.openingPeriods,
        `service-service-${this.data.services.length + 1}`,
      ),
    }]);
    this.setData({ services });
  },

  removeService(event) {
    if (this.data.services.length <= 1) return;
    const index = Number(event.currentTarget.dataset.index);
    this.setData({ services: this.data.services.filter((item, row) => row !== index) });
  },

  addStaff() {
    const staff = this.data.staff.concat([{
      code: `staff-${this.data.staff.length + 1}`,
      name: '',
      title: '',
      customSchedule: false,
      periods: periodsFromOpening(
        this.data.openingPeriods,
        `staff-staff-${this.data.staff.length + 1}`,
      ),
    }]);
    this.setData({ staff });
  },

  removeStaff(event) {
    const index = Number(event.currentTarget.dataset.index);
    this.setData({ staff: this.data.staff.filter((item, row) => row !== index) });
  },

  async save() {
    if (this.data.saving) return;
    try {
      if (!this.data.location.name.trim()) throw new Error('请填写工作室名称');
      if (!this.data.openingPeriods.length) throw new Error('请至少添加一个开放时段');
      const interval = Number(this.data.location.interval);
      const notice = Number(this.data.location.notice);
      if (!Number.isInteger(interval) || interval < 5 || interval > 240) {
        throw new Error('预约开始间隔必须是 5–240 分钟的整数');
      }
      if (!Number.isInteger(notice) || notice < 0 || notice > 43200) {
        throw new Error('提前预约分钟数必须是 0–43200 的整数');
      }
      const intervalsByWeekday = {};
      this.data.openingPeriods.forEach((period, index) => {
        if (!period.selectedWeekdays.length) {
          throw new Error(`开放时段 ${index + 1} 请至少选择一个星期`);
        }
        if (period.end <= period.start) {
          throw new Error(`开放时段 ${index + 1} 的结束时间必须晚于开始时间`);
        }
        period.selectedWeekdays.forEach((weekday) => {
          if (!intervalsByWeekday[weekday]) intervalsByWeekday[weekday] = [];
          intervalsByWeekday[weekday].push({
            start: period.start,
            end: period.end,
            index: index + 1,
          });
        });
      });
      Object.keys(intervalsByWeekday).forEach((weekday) => {
        const intervals = intervalsByWeekday[weekday].sort(
          (a, b) => a.start.localeCompare(b.start),
        );
        for (let index = 1; index < intervals.length; index += 1) {
          if (intervals[index].start < intervals[index - 1].end) {
            throw new Error(`星期${WEEKDAYS[Number(weekday)].label}的开放时段互相重叠`);
          }
        }
      });
      const services = this.data.services.map((item, index) => {
        if (!item.code.trim() || !item.name.trim()) throw new Error(`请完整填写服务 ${index + 1}`);
        const duration = Number(item.duration);
        if (!Number.isInteger(duration) || duration < 5) throw new Error('单次预约占用必须是至少 5 分钟的整数');
        if (item.customSchedule) {
          if (!item.periods || !item.periods.length) {
            throw new Error(`服务 ${index + 1} 请至少添加一个可预约时段`);
          }
          const serviceIntervals = {};
          item.periods.forEach((period, periodIndex) => {
            if (!period.selectedWeekdays.length) {
              throw new Error(`服务 ${index + 1} 的时段 ${periodIndex + 1} 请至少选择一个星期`);
            }
            if (period.end <= period.start) {
              throw new Error(`服务 ${index + 1} 的时段 ${periodIndex + 1} 结束时间必须晚于开始时间`);
            }
            period.selectedWeekdays.forEach((weekday) => {
              const studioIntervals = intervalsByWeekday[weekday] || [];
              const availableMinutes = maximumOpenOverlap(period, studioIntervals);
              if (availableMinutes <= 0) {
                throw new Error(
                  `服务 ${index + 1} 在星期${WEEKDAYS[Number(weekday)].label}与工作室开放时段没有交集`,
                );
              }
              if (!serviceIntervals[weekday]) serviceIntervals[weekday] = [];
              serviceIntervals[weekday].push({
                start: period.start,
                end: period.end,
              });
            });
          });
          Object.keys(serviceIntervals).forEach((weekday) => {
            const intervals = serviceIntervals[weekday].sort(
              (a, b) => a.start.localeCompare(b.start),
            );
            for (let row = 1; row < intervals.length; row += 1) {
              if (intervals[row].start < intervals[row - 1].end) {
                throw new Error(
                  `服务 ${index + 1} 在星期${WEEKDAYS[Number(weekday)].label}的时段互相重叠`,
                );
              }
            }
            const mergedServiceIntervals = intervals.reduce((all, interval) => {
              const previous = all[all.length - 1];
              if (previous && interval.start === previous.end) {
                previous.end = interval.end;
              } else {
                all.push({ ...interval });
              }
              return all;
            }, []);
            const availableMinutes = mergedServiceIntervals.reduce((best, interval) => (
              Math.max(
                best,
                maximumOpenOverlap(interval, intervalsByWeekday[weekday] || []),
              )
            ), 0);
            if (availableMinutes < duration) {
              throw new Error(
                `服务「${item.name.trim() || index + 1}」星期${WEEKDAYS[Number(weekday)].label}`
                + `的共同可用时段最长 ${availableMinutes} 分钟，放不下 ${duration} 分钟的服务；`
                + '请延长开放时间、调整服务时段或缩短单次预约占用',
              );
            }
          });
        }
        return {
          code: item.code.trim().toLowerCase(),
          name: item.name.trim(),
          duration_minutes: duration,
          description: item.description || '',
          buffer_before_minutes: Number(item.bufferBefore || 0),
          buffer_after_minutes: Number(item.bufferAfter || 0),
          capacity: Number(item.capacity || 1),
          price_minor: minorAllowZero(item.price),
          deposit_minor: minorAllowZero(item.deposit),
          sort_order: index,
        };
      });
      const serviceCodes = services.map((item) => item.code);
      const staff = this.data.staff.map((item, index) => {
        if (!item.code.trim() || !item.name.trim()) throw new Error(`请完整填写员工 ${index + 1}`);
        if (item.customSchedule) validatePeriodRows(item.periods, `员工「${item.name.trim()}」`);
        return {
          code: item.code.trim().toLowerCase(),
          name: item.name.trim(),
          title: item.title.trim(),
          service_codes: serviceCodes,
          sort_order: index,
          customSchedule: item.customSchedule,
          periods: item.periods || [],
        };
      });

      // 严格检查完整链路，而不是只检查“工作室 × 服务”。只要某个服务在某天
      // 对外开放，就必须能在预约间隔网格上放下完整服务；存在员工时，还必须
      // 至少有一名员工在同一窗口内可用，避免保存成功后消费者得到 0 个时段。
      services.forEach((service, serviceIndex) => {
        const sourceService = this.data.services[serviceIndex];
        WEEKDAYS.forEach((weekday) => {
          const locationWindows = weekdayWindows(
            this.data.openingPeriods,
            weekday.value,
          );
          if (!locationWindows.length) return;
          const serviceWindows = sourceService.customSchedule
            ? intersectMinuteWindows(
              locationWindows,
              weekdayWindows(sourceService.periods, weekday.value),
            )
            : locationWindows;
          // A custom service schedule may intentionally omit this weekday.
          if (!serviceWindows.length) return;
          if (!hasAlignedSlot(
            serviceWindows,
            service.duration_minutes,
            interval,
            service.buffer_before_minutes,
            service.buffer_after_minutes,
          )) {
            const occupiedMinutes = service.duration_minutes
              + service.buffer_before_minutes + service.buffer_after_minutes;
            throw new Error(
              `服务「${service.name}」星期${weekday.label}的工作室与服务共同时间`
              + `无法按 ${interval} 分钟间隔放下 ${occupiedMinutes} 分钟（含前后缓冲）；`
              + '请延长时段或调整预约间隔',
            );
          }
          if (!staff.length) return;
          const availableStaff = staff.filter((person) => {
            if (!person.customSchedule) return true;
            const staffWindows = weekdayWindows(person.periods, weekday.value);
            return hasAlignedSlot(
              intersectMinuteWindows(serviceWindows, staffWindows),
              service.duration_minutes,
              interval,
              service.buffer_before_minutes,
              service.buffer_after_minutes,
            );
          });
          if (!availableStaff.length) {
            throw new Error(
              `服务「${service.name}」星期${weekday.label}没有任何员工拥有`
              + `可放下 ${service.duration_minutes} 分钟服务及前后缓冲的共同空闲时间；`
              + '请为至少一名员工补充该日时段',
            );
          }
        });
      });
      const rules = [];
      this.data.openingPeriods.forEach((period) => {
        period.selectedWeekdays.forEach((weekday) => {
          rules.push({
            scope_type: 'location',
            scope_code: 'main',
            weekday: Number(weekday),
            start: period.start,
            end: period.end,
          });
        });
      });
      this.data.services.filter((item) => item.customSchedule).forEach((item) => {
        const serviceCode = item.code.trim().toLowerCase();
        item.periods.forEach((period) => {
          period.selectedWeekdays.forEach((weekday) => {
            rules.push({
              scope_type: 'service',
              scope_code: serviceCode,
              weekday: Number(weekday),
              start: period.start,
              end: period.end,
            });
          });
        });
      });
      staff.filter((person) => person.customSchedule).forEach((person) => {
        person.periods.forEach((period) => {
          period.selectedWeekdays.forEach((weekday) => {
            rules.push({
              scope_type: 'staff',
              scope_code: person.code,
              weekday: Number(weekday),
              start: period.start,
              end: period.end,
            });
          });
        });
      });
      this.setData({ saving: true, error: '' });
      await member.saveBookingSetup(this.data.companyCode, {
        location: {
          code: 'main',
          name: this.data.location.name.trim(),
          address: this.data.location.address.trim(),
          timezone: this.data.location.timezone,
          booking_horizon_days: 60,
          min_notice_minutes: notice,
          slot_interval_minutes: interval,
          auto_confirm: true,
        },
        services,
        staff,
        schedule_rules: rules,
        time_blocks: this.data.timeBlocks,
      });
      wx.showToast({ title: '营业设置已保存', icon: 'success' });
      setTimeout(() => wx.navigateBack(), 500);
    } catch (error) {
      this.setData({ error: error.message || '保存失败' });
    } finally {
      this.setData({ saving: false });
    }
  },
});
