const member = require('../../services/member');
const context = require('../../services/context');
const money = require('../../utils/money');
const companyUtil = require('../../utils/company');

function benefitRows(benefits) {
  return Object.keys(benefits || {}).map((key) => {
    const raw = benefits[key];
    const value = raw && typeof raw === 'object' ? JSON.stringify(raw) : String(raw);
    return { key, value };
  });
}

function levelRow(level) {
  if (!level) return null;
  return {
    ...level,
    threshold: money.formatMinor(level.min_spend_minor),
    pointsPerYuan: (Number(level.points_rate_bps || 0) / 10000).toFixed(2),
    benefitRows: benefitRows(level.benefits),
  };
}

Page({
  data: {
    loading: true,
    program: null,
    current: null,
    next: null,
    levels: [],
    spent: '0.00',
    remaining: '0.00',
    progressPercent: 0,
    error: '',
    companyName: '',
    companyMode: '',
  },
  onShow() { this.load(); },
  async load() {
    try {
      this.setData({ loading: true, error: '' });
      const selected = await context.requireCompany();
      if (!selected) {
        this.setData({ loading: false, program: null });
        return;
      }
      const program = await member.membershipProgram(selected.code);
      const current = levelRow(program.current_level || program.current);
      const next = levelRow(program.next_level || program.next);
      this.setData({
        loading: false,
        program,
        current,
        next,
        levels: (program.levels || []).map(levelRow),
        spent: money.formatMinor(program.cumulative_spend_minor),
        remaining: money.formatMinor(program.progress && program.progress.remaining_spend_minor),
        progressPercent: Math.max(0, Math.min(100, Number(
          program.progress && program.progress.basis_points || 0,
        ) / 100)),
        companyName: selected.company.name,
        companyMode: companyUtil.modeLabel(selected.company),
        error: '',
      });
    } catch (error) {
      this.setData({ loading: false, error: error.message || '无法读取会员等级' });
    }
  },
});
