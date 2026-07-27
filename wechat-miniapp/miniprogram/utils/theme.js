'use strict';

const STORAGE_KEY = 'warehouse.member.swiss-theme.v1';

const DEFAULT_THEME = Object.freeze({
  id: 'classic-red',
  name: 'Helvetica 红黑',
  accent: '#E0261C',
  ink: '#141414',
});

const PRESETS = Object.freeze([
  DEFAULT_THEME,
  Object.freeze({ id: 'basel-blue', name: 'Basel 蓝墨', accent: '#0057B8', ink: '#102A43' }),
  Object.freeze({ id: 'zurich-green', name: 'Zürich 绿墨', accent: '#167A55', ink: '#17251E' }),
  Object.freeze({ id: 'geneva-violet', name: 'Genève 紫墨', accent: '#7040A0', ink: '#21192A' }),
  Object.freeze({ id: 'ticino-orange', name: 'Ticino 橙墨', accent: '#C94A16', ink: '#241A16' }),
  Object.freeze({ id: 'luzern-yellow', name: 'Luzern 黄蓝', accent: '#F2C94C', ink: '#172A46' }),
]);

function normalizeHex(value) {
  let hex = String(value || '').trim().replace(/^#/, '');
  if (/^[0-9a-fA-F]{3}$/.test(hex)) {
    hex = hex.split('').map((part) => `${part}${part}`).join('');
  }
  if (!/^[0-9a-fA-F]{6}$/.test(hex)) return '';
  return `#${hex.toUpperCase()}`;
}

function rgb(hex) {
  const normalized = normalizeHex(hex) || DEFAULT_THEME.ink;
  return {
    r: parseInt(normalized.slice(1, 3), 16),
    g: parseInt(normalized.slice(3, 5), 16),
    b: parseInt(normalized.slice(5, 7), 16),
  };
}

function relativeLuminance(hex) {
  const color = rgb(hex);
  return ['r', 'g', 'b'].reduce((sum, channel, index) => {
    const value = color[channel] / 255;
    const linear = value <= 0.03928
      ? value / 12.92
      : ((value + 0.055) / 1.055) ** 2.4;
    return sum + linear * [0.2126, 0.7152, 0.0722][index];
  }, 0);
}

function readableText(background) {
  const luminance = relativeLuminance(background);
  const whiteContrast = 1.05 / (luminance + 0.05);
  const blackContrast = (luminance + 0.05) / 0.05;
  return whiteContrast >= blackContrast ? '#FFFFFF' : '#000000';
}

function blend(first, second, secondWeight) {
  const a = rgb(first);
  const b = rgb(second);
  const weight = Math.max(0, Math.min(1, secondWeight));
  const value = ['r', 'g', 'b'].map((channel) => (
    Math.round(a[channel] * (1 - weight) + b[channel] * weight)
      .toString(16).padStart(2, '0')
  )).join('');
  return `#${value.toUpperCase()}`;
}

function normalize(value) {
  const accent = normalizeHex(value && value.accent) || DEFAULT_THEME.accent;
  const ink = normalizeHex(value && value.ink) || DEFAULT_THEME.ink;
  const preset = PRESETS.find((item) => item.accent === accent && item.ink === ink);
  return {
    id: preset ? preset.id : 'custom',
    name: preset ? preset.name : '自定义 Swiss',
    accent,
    ink,
    onAccent: readableText(accent),
    onInk: readableText(ink),
  };
}

function current() {
  try {
    return normalize(wx.getStorageSync(STORAGE_KEY));
  } catch (error) {
    return normalize(DEFAULT_THEME);
  }
}

function style(value) {
  const selected = normalize(value || current());
  const accent = rgb(selected.accent);
  const ink = rgb(selected.ink);
  const markFilter = selected.onAccent === '#000000'
    ? 'brightness(0)'
    : 'brightness(0) invert(1)';
  return [
    `--swiss-accent:${selected.accent}`,
    `--swiss-accent-rgb:${accent.r}, ${accent.g}, ${accent.b}`,
    `--swiss-ink:${selected.ink}`,
    `--swiss-ink-rgb:${ink.r}, ${ink.g}, ${ink.b}`,
    `--swiss-on-accent:${selected.onAccent}`,
    `--swiss-on-ink:${selected.onInk}`,
    `--swiss-mark-filter:${markFilter}`,
  ].join(';');
}

function applyChrome(value) {
  if (typeof wx === 'undefined') return;
  const selected = normalize(value || current());
  if (typeof wx.setNavigationBarColor === 'function') {
    wx.setNavigationBarColor({
      frontColor: selected.onInk.toLowerCase(),
      backgroundColor: selected.ink,
      animation: { duration: 180, timingFunc: 'easeIn' },
      fail() {},
    });
  }
  if (typeof wx.setTabBarStyle === 'function') {
    wx.setTabBarStyle({
      color: blend(selected.ink, selected.onInk, 0.58),
      selectedColor: selected.onInk,
      backgroundColor: selected.ink,
      borderStyle: selected.onInk === '#FFFFFF' ? 'black' : 'white',
      fail() {},
    });
  }
}

function save(value) {
  const accent = normalizeHex(value && value.accent);
  const ink = normalizeHex(value && value.ink);
  if (!accent || !ink) throw new Error('颜色必须使用 #RRGGBB 或 #RGB 格式');
  const selected = normalize({ accent, ink });
  wx.setStorageSync(STORAGE_KEY, {
    id: selected.id,
    accent: selected.accent,
    ink: selected.ink,
  });
  applyChrome(selected);
  return selected;
}

function reset() {
  try { wx.removeStorageSync(STORAGE_KEY); } catch (error) { /* use default */ }
  const selected = normalize(DEFAULT_THEME);
  applyChrome(selected);
  return selected;
}

function presets() {
  return PRESETS.map((item) => ({ ...normalize(item), id: item.id, name: item.name }));
}

module.exports = {
  STORAGE_KEY,
  DEFAULT_THEME,
  normalizeHex,
  current,
  style,
  save,
  reset,
  presets,
  applyChrome,
};
