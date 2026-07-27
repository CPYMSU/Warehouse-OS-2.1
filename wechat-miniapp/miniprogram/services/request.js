const env = require('../config/env');
const session = require('../store/session');

let requestSequence = 0;

function requestId(prefix) {
  requestSequence = (requestSequence + 1) % 1000000;
  const fallback = () => `${prefix || 'req'}-${Date.now()}-${requestSequence}`;
  if (typeof wx.getRandomValues !== 'function') return Promise.resolve(fallback());
  return new Promise((resolve) => {
    wx.getRandomValues({
      length: 16,
      success(result) {
        const bytes = new Uint8Array(result.randomValues);
        const entropy = Array.prototype.map.call(
          bytes,
          (value) => (`0${value.toString(16)}`).slice(-2),
        ).join('');
        resolve(`${prefix || 'req'}-${Date.now()}-${entropy}`);
      },
      fail() { resolve(fallback()); },
    });
  });
}

function request({ path, method = 'GET', data, auth = true, idempotencyKey }) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth && session.token()) headers.Authorization = `Bearer ${session.token()}`;
  if (idempotencyKey) headers['Idempotency-Key'] = idempotencyKey;
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${env.apiBaseUrl}${path}`,
      method,
      data,
      header: headers,
      timeout: 12000,
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300) {
          resolve(response.data || {});
          return;
        }
        if (auth && response.statusCode === 401) session.setToken('');
        const error = new Error((response.data && response.data.error) || `请求失败 ${response.statusCode}`);
        error.statusCode = response.statusCode;
        reject(error);
      },
      fail(error) { reject(new Error(error.errMsg || '网络连接失败')); },
    });
  });
}

module.exports = { request, requestId };
