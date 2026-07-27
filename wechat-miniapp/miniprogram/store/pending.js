const PENDING_KEY = 'warehouse.member.pending.requests';
const MAX_ENTRIES = 20;

function readAll() {
  const value = wx.getStorageSync(PENDING_KEY);
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function writeAll(value) {
  const entries = Object.keys(value).map((key) => [key, value[key]]).sort((left, right) => (
    Number(right[1].createdAt || 0) - Number(left[1].createdAt || 0)
  ));
  const limited = {};
  entries.slice(0, MAX_ENTRIES).forEach((entry) => {
    limited[entry[0]] = entry[1];
  });
  wx.setStorageSync(PENDING_KEY, limited);
}

function scopeKey(kind, scope) {
  return `${String(kind || '').trim()}:${String(scope || '').trim()}`;
}

function get(kind, scope) {
  const row = readAll()[scopeKey(kind, scope)];
  return row && row.requestId ? row.requestId : '';
}

function set(kind, scope, requestId) {
  const rows = readAll();
  rows[scopeKey(kind, scope)] = { requestId, createdAt: Date.now() };
  writeAll(rows);
  return requestId;
}

function clear(kind, scope) {
  const rows = readAll();
  delete rows[scopeKey(kind, scope)];
  writeAll(rows);
}

module.exports = { get, set, clear };
