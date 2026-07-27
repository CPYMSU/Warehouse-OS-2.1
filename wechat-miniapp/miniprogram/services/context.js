const member = require('./member');
const session = require('../store/session');

function openCompanies() {
  const pages = getCurrentPages();
  const current = pages.length ? pages[pages.length - 1].route : '';
  if (current !== 'pages/companies/index') {
    wx.navigateTo({ url: '/pages/companies/index' });
  }
}

async function loadMemberships() {
  await getApp().ensureSession(session.company());
  try {
    return await member.companies();
  } catch (error) {
    if (error && error.statusCode === 401) {
      await getApp().ensureSession(session.company());
      return member.companies();
    }
    throw error;
  }
}

async function loadAppContext() {
  await getApp().ensureSession(session.company());
  try {
    return await member.appContext();
  } catch (error) {
    if (error && error.statusCode === 401) {
      await getApp().ensureSession(session.company());
      return member.appContext();
    }
    throw error;
  }
}

async function requireCompany() {
  const result = await loadMemberships();
  const companies = result.companies || [];
  let code = session.company();
  if (code) {
    const selected = companies.find((item) => item.company && item.company.code === code);
    if (selected) {
      return { code, account: selected, company: selected.company, memberships: companies };
    }
    // A removed or otherwise stale selection must not trap every tab. Company
    // invitations live in their own storage key and are handled by the company
    // directory, so it is safe to recover to the first active membership here.
    session.setCompany('');
  }
  const first = companies[0];
  if (!first || !first.company || !first.company.code) {
    openCompanies();
    return null;
  }
  code = first.company.code;
  session.setCompany(code);
  return { code, account: first, company: first.company, memberships: companies };
}

module.exports = {
  loadMemberships,
  loadAppContext,
  requireCompany,
  openCompanies,
};
