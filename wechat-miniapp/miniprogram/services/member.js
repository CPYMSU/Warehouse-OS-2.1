const session = require('../store/session');
const api = require('./request');

function wxLoginCode() {
  return new Promise((resolve, reject) => {
    wx.login({ success: ({ code }) => code ? resolve(code) : reject(new Error('微信登录失败')), fail: reject });
  });
}

async function login(companyCode) {
  const code = await wxLoginCode();
  const result = await api.request({
    path: '/api/miniapp/v1/auth/wechat',
    method: 'POST',
    auth: false,
    // 登录只建立外部消费者身份；加入某家公司必须由用户在公司页明确同意。
    data: { code },
  });
  session.setToken(result.token);
  return result;
}

function appContext() { return api.request({ path: '/api/miniapp/v1/app-context' }); }
function companies() { return api.request({ path: '/api/miniapp/v1/me/companies' }); }
function company(code) { return api.request({ path: `/api/miniapp/v1/companies/${code}`, auth: false }); }
function account(code) { return api.request({ path: `/api/miniapp/v1/companies/${code}/account` }); }
function ledger(code) { return api.request({ path: `/api/miniapp/v1/companies/${code}/ledger` }); }
function membershipProgram(code) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/membership-program` });
}
function lotteryCampaigns(code) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/lottery/campaigns` });
}
function rewards(code) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/rewards` });
}
function logout(allSessions) {
  return api.request({
    path: '/api/miniapp/v1/auth/logout',
    method: 'POST',
    data: { all_sessions: Boolean(allSessions) },
  });
}
function rechargeOrder(code, orderNo) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/recharge-orders/${orderNo}` });
}
function transactionCards(code, status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/transaction-cards${query}`,
  });
}
function join(code, consentVersion) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/join`, method: 'POST', data: { consent_version: consentVersion } });
}
async function recharge(code, amountMinor, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('recharge');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/recharge-orders`,
    method: 'POST',
    idempotencyKey: key,
    data: { amount_minor: amountMinor, client_request_id: key },
  });
}
async function paymentCode(code, amountMinor) {
  const key = await api.requestId('paycode');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/payment-codes`,
    method: 'POST',
    idempotencyKey: key,
    data: { amount_minor: amountMinor, client_request_id: key },
  });
}
function giftCardPreview(code, qrPayload) {
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/gift-cards/preview`,
    method: 'POST',
    data: { qr_payload: qrPayload },
  });
}
async function claimGiftCard(code, qrPayload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('gift-claim');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/gift-cards/claim`,
    method: 'POST',
    idempotencyKey: key,
    data: { qr_payload: qrPayload, client_request_id: key },
  });
}
function newRequestId(prefix) { return api.requestId(prefix); }
async function draw(code, campaignCode, idempotencyKey) {
  const key = idempotencyKey || await newRequestId('draw');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/lottery/draw`,
    method: 'POST',
    idempotencyKey: key,
    data: { campaign_code: campaignCode, client_request_id: key },
  });
}

function warehouseSignIn(username, password) {
  return api.request({
    path: '/api/miniapp/v1/auth/warehouse',
    method: 'POST',
    data: { username, password },
  });
}
async function acknowledgeTransactionCard(code, cardNo) {
  const key = await api.requestId('transaction-ack');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/transaction-cards/${cardNo}/acknowledge`,
    method: 'POST',
    idempotencyKey: key,
    data: { client_request_id: key },
  });
}
async function cancelTransactionCard(code, cardNo) {
  const key = await api.requestId('transaction-cancel');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/transaction-cards/${cardNo}/cancel`,
    method: 'POST',
    idempotencyKey: key,
    data: { client_request_id: key },
  });
}
async function confirmChargeCard(code, cardNo) {
  const key = await api.requestId('charge-confirm');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/transaction-cards/${cardNo}/confirm`,
    method: 'POST',
    idempotencyKey: key,
    data: { client_request_id: key },
  });
}
async function declineChargeCard(code, cardNo) {
  const key = await api.requestId('charge-decline');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/transaction-cards/${cardNo}/decline`,
    method: 'POST',
    idempotencyKey: key,
    data: { client_request_id: key },
  });
}

function operatorCompanies() {
  return api.request({ path: '/api/miniapp/v1/operator/companies' });
}

function createOperatorCompany(payload) {
  return api.request({
    path: '/api/miniapp/v1/operator/companies',
    method: 'POST',
    data: payload,
  });
}

function bookingCatalog(code) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/booking/catalog` });
}

function bookingSlots(code, params) {
  const query = Object.keys(params || {})
    .filter((key) => params[key] !== undefined && params[key] !== null && params[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(params[key])}`)
    .join('&');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/booking/slots${query ? `?${query}` : ''}`,
  });
}

async function createAppointment(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('appointment');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/appointments`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

function appointments(code) {
  return api.request({ path: `/api/miniapp/v1/companies/${code}/appointments` });
}

async function cancelAppointment(code, appointmentNo, reason) {
  const key = await api.requestId('appointment-cancel');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/appointments/${appointmentNo}/cancel`,
    method: 'POST',
    idempotencyKey: key,
    data: { reason, client_request_id: key },
  });
}

function operatorBooking(code) {
  return api.request({ path: `/api/miniapp/v1/operator/companies/${code}/booking` });
}

function operatorSales(code) {
  return api.request({ path: `/api/miniapp/v1/operator/companies/${code}/sales` });
}

function operatorFinance(code) {
  return api.request({ path: `/api/miniapp/v1/operator/companies/${code}/finance` });
}

async function recordOperatorFinance(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-finance');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/finance`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

async function createOperatorCustomer(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-customer');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/members`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

async function issueCustomerClaimCode(code, memberNo, expiresMinutes, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('customer-claim-code');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/members/${memberNo}/claim-code`,
    method: 'POST',
    idempotencyKey: key,
    data: { expires_minutes: expiresMinutes || 15, client_request_id: key },
  });
}

function customerClaimPreview(code, qrPayload) {
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/member-claims/preview`,
    method: 'POST',
    data: { qr_payload: qrPayload },
  });
}

async function claimCustomerProfile(code, qrPayload, consentVersion, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('customer-profile-claim');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/member-claims/claim`,
    method: 'POST',
    idempotencyKey: key,
    data: {
      qr_payload: qrPayload,
      consent_version: consentVersion,
      client_request_id: key,
    },
  });
}

function saveOperatorMemberProfile(code, memberNo, payload) {
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/members/${memberNo}`,
    method: 'POST',
    data: payload,
  });
}

async function operatorRechargeCustomer(code, memberNo, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-member-recharge');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/members/${memberNo}/recharge`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

function saveSalesCatalogItem(code, item) {
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/sales/catalog`,
    method: 'POST',
    data: { item },
  });
}

function importBookingServicesToSales(code) {
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/sales/catalog/import-booking`,
    method: 'POST',
    data: {},
  });
}

async function operatorDirectSale(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-direct-sale');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/sales/checkout`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

async function operatorCreateSaleChargeCard(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-sale-charge-card');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/sales/charge-card`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}

function saveBookingSetup(code, setup) {
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/booking/setup`,
    method: 'POST',
    data: setup,
  });
}

function operatorAppointments(code, status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/appointments${query}`,
  });
}
function operatorTransactionCards(code, status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/transaction-cards${query}`,
  });
}
async function operatorCreateChargeCard(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-charge');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/transaction-cards`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, type: 'charge', client_request_id: key },
  });
}
async function operatorRedeemPaymentCode(code, qrPayload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-payment-scan');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/payment-codes/redeem`,
    method: 'POST',
    idempotencyKey: key,
    data: {
      qr_payload: qrPayload,
      description: '经营端扫码消费',
      client_request_id: key,
    },
  });
}
async function operatorCreateGiftCard(code, payload, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('operator-gift');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/gift-cards`,
    method: 'POST',
    idempotencyKey: key,
    data: { ...payload, client_request_id: key },
  });
}
async function operatorConfirmTransactionCard(code, cardNo, note) {
  const key = await api.requestId('operator-transaction-confirm');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/transaction-cards/${cardNo}/confirm`,
    method: 'POST',
    idempotencyKey: key,
    data: { note, client_request_id: key },
  });
}
async function operatorDeclineTransactionCard(code, cardNo, reason) {
  const key = await api.requestId('operator-transaction-decline');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/transaction-cards/${cardNo}/decline`,
    method: 'POST',
    idempotencyKey: key,
    data: { reason, client_request_id: key },
  });
}
async function reportMerchantNoShow(code, appointmentNo, reason, idempotencyKey) {
  const key = idempotencyKey || await api.requestId('merchant-no-show-report');
  return api.request({
    path: `/api/miniapp/v1/companies/${code}/appointments/${appointmentNo}/merchant-no-show`,
    method: 'POST',
    idempotencyKey: key,
    data: { reason, client_request_id: key },
  });
}

async function updateAppointmentStatus(code, appointmentNo, status, note) {
  const key = await api.requestId('appointment-status');
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/appointments/${appointmentNo}/status`,
    method: 'POST',
    idempotencyKey: key,
    data: { status, note, client_request_id: key },
  });
}
async function operatorResolveMerchantNoShow(
  code,
  appointmentNo,
  decision,
  note,
  idempotencyKey,
) {
  const key = idempotencyKey || await api.requestId(`merchant-no-show-${decision}`);
  return api.request({
    path: `/api/miniapp/v1/operator/companies/${code}/appointments/${appointmentNo}/merchant-no-show/${decision}`,
    method: 'POST',
    idempotencyKey: key,
    data: { note, client_request_id: key },
  });
}

module.exports = {
  login,
  logout,
  appContext,
  companies,
  company,
  account,
  ledger,
  membershipProgram,
  lotteryCampaigns,
  rewards,
  rechargeOrder,
  transactionCards,
  join,
  recharge,
  paymentCode,
  giftCardPreview,
  claimGiftCard,
  acknowledgeTransactionCard,
  cancelTransactionCard,
  confirmChargeCard,
  declineChargeCard,
  newRequestId,
  draw,
  warehouseSignIn,
  operatorCompanies,
  createOperatorCompany,
  bookingCatalog,
  bookingSlots,
  createAppointment,
  appointments,
  cancelAppointment,
  reportMerchantNoShow,
  operatorBooking,
  operatorSales,
  operatorFinance,
  recordOperatorFinance,
  createOperatorCustomer,
  issueCustomerClaimCode,
  customerClaimPreview,
  claimCustomerProfile,
  saveOperatorMemberProfile,
  operatorRechargeCustomer,
  saveSalesCatalogItem,
  importBookingServicesToSales,
  operatorDirectSale,
  operatorCreateSaleChargeCard,
  saveBookingSetup,
  operatorAppointments,
  operatorTransactionCards,
  operatorCreateChargeCard,
  operatorRedeemPaymentCode,
  operatorCreateGiftCard,
  operatorConfirmTransactionCard,
  operatorDeclineTransactionCard,
  updateAppointmentStatus,
  operatorResolveMerchantNoShow,
};
