const TOKEN_KEY = 'warehouse.member.token';
const COMPANY_KEY = 'warehouse.member.company';
const INVITE_COMPANY_KEY = 'warehouse.member.invite-company';
const OPERATOR_COMPANY_KEY = 'warehouse.member.operator-company';
const PORTAL_KEY = 'warehouse.member.portal';

function token() { return wx.getStorageSync(TOKEN_KEY) || ''; }
function setToken(value) { value ? wx.setStorageSync(TOKEN_KEY, value) : wx.removeStorageSync(TOKEN_KEY); }
function company() { return wx.getStorageSync(COMPANY_KEY) || ''; }
function setCompany(value) { value ? wx.setStorageSync(COMPANY_KEY, value) : wx.removeStorageSync(COMPANY_KEY); }
function inviteCompany() { return wx.getStorageSync(INVITE_COMPANY_KEY) || ''; }
function setInviteCompany(value) {
  value ? wx.setStorageSync(INVITE_COMPANY_KEY, value) : wx.removeStorageSync(INVITE_COMPANY_KEY);
}
function operatorCompany() { return wx.getStorageSync(OPERATOR_COMPANY_KEY) || ''; }
function setOperatorCompany(value) {
  value ? wx.setStorageSync(OPERATOR_COMPANY_KEY, value) : wx.removeStorageSync(OPERATOR_COMPANY_KEY);
}
function portal() { return wx.getStorageSync(PORTAL_KEY) || ''; }
function setPortal(value) { value ? wx.setStorageSync(PORTAL_KEY, value) : wx.removeStorageSync(PORTAL_KEY); }
function clear() {
  setToken('');
  setCompany('');
  setInviteCompany('');
  setOperatorCompany('');
  setPortal('');
}

module.exports = {
  token,
  setToken,
  company,
  setCompany,
  inviteCompany,
  setInviteCompany,
  operatorCompany,
  setOperatorCompany,
  portal,
  setPortal,
  clear,
};
