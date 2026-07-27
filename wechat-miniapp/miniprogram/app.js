const member = require('./services/member');
const session = require('./store/session');
const env = require('./config/env');
const theme = require('./utils/theme');

function normalizeCompanyCode(value) {
  const code = String(value || '').trim().toLowerCase();
  return /^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$/.test(code) ? code : '';
}

function companyFromScene(value) {
  let scene = String(value || '').trim();
  if (!scene) return '';
  try { scene = decodeURIComponent(scene); } catch (error) { return ''; }
  const direct = normalizeCompanyCode(scene);
  if (direct) return direct;
  const parts = scene.split('&');
  for (let index = 0; index < parts.length; index += 1) {
    const pair = parts[index].split('=');
    const key = String(pair.shift() || '').trim().toLowerCase();
    if (key !== 'company') continue;
    return normalizeCompanyCode(pair.join('='));
  }
  return '';
}

function companyFromOptions(options) {
  const query = options && options.query || {};
  return normalizeCompanyCode(query.company) || companyFromScene(query.scene);
}

App({
  globalData: {
    booting: null,
  },

  onLaunch(options) {
    theme.applyChrome(theme.current());
    const companyCode = companyFromOptions(options) || env.defaultCompanyCode;
    if (companyCode) session.setInviteCompany(companyCode);
  },

  onShow(options) {
    theme.applyChrome(theme.current());
    // 热启动从新的二维码/分享卡进入时不会再次触发 onLaunch。这里只记录
    // 公司邀请代码；是否加入仍由公司页的公开预览与用户明确同意决定。
    const companyCode = companyFromOptions(options);
    if (companyCode) session.setInviteCompany(companyCode);
  },

  ensureSession(companyCode) {
    if (session.token()) return Promise.resolve(session.token());
    if (this.globalData.booting) return this.globalData.booting;
    this.globalData.booting = member.login(companyCode || session.company())
      .then((result) => {
        const appContext = result.context || {};
        if (!session.portal() && appContext.default_portal) {
          session.setPortal(appContext.default_portal);
        }
        const operatorCompanies = appContext.operator_companies || [];
        if (!session.operatorCompany() && operatorCompanies[0]) {
          session.setOperatorCompany(operatorCompanies[0].public_code);
        }
        return result.token;
      })
      .finally(() => { this.globalData.booting = null; });
    return this.globalData.booting;
  },
});
