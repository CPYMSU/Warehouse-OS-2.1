function formatMinor(value) {
  const minor = Number(value || 0);
  return (minor / 100).toFixed(2);
}

function yuanToMinor(value) {
  const text = String(value == null ? '' : value).trim();
  if (!/^\d+(?:\.\d{0,2})?$/.test(text)) throw new Error('请输入正确金额');
  const minor = Math.round(Number(text) * 100);
  if (!Number.isSafeInteger(minor) || minor <= 0) throw new Error('充值金额必须大于 0');
  return minor;
}

module.exports = { formatMinor, yuanToMinor };
