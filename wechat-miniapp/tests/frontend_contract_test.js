'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');

function read(relativePath) {
  return fs.readFileSync(path.join(ROOT, relativePath), 'utf8');
}

function filesBelow(relativePath, extension) {
  const result = [];
  function walk(directory) {
    fs.readdirSync(directory, { withFileTypes: true }).forEach((entry) => {
      const absolute = path.join(directory, entry.name);
      if (entry.isDirectory()) walk(absolute);
      else if (entry.name.endsWith(extension)) result.push(absolute);
    });
  }
  walk(path.join(ROOT, relativePath));
  return result;
}

function setDataValue(target, dataPath, value) {
  const parts = String(dataPath).replace(/\[(\d+)\]/g, '.$1').split('.');
  let cursor = target;
  parts.slice(0, -1).forEach((part, index) => {
    if (cursor[part] == null) cursor[part] = /^\d+$/.test(parts[index + 1]) ? [] : {};
    cursor = cursor[part];
  });
  cursor[parts[parts.length - 1]] = value;
}

function loadPageRuntime(relativePath, mocks, wxRuntime) {
  let definition = null;
  const sandbox = {
    Page(value) { definition = value; },
    require(request) {
      if (Object.prototype.hasOwnProperty.call(mocks, request)) return mocks[request];
      throw new Error(`Unexpected page dependency: ${request}`);
    },
    wx: wxRuntime || {},
    Date,
    Intl,
    Promise,
    Uint8Array,
    setTimeout(callback) { if (typeof callback === 'function') callback(); return 1; },
    clearTimeout() {},
    console,
  };
  vm.runInNewContext(read(relativePath), sandbox, { filename: relativePath });
  assert.ok(definition, `${relativePath} must register a Page`);
  const page = {
    ...definition,
    data: JSON.parse(JSON.stringify(definition.data || {})),
    setData(update, callback) {
      Object.keys(update || {}).forEach((key) => setDataValue(this.data, key, update[key]));
      if (typeof callback === 'function') callback();
    },
  };
  return { page, sandbox };
}

function testDirectPageGuards() {
  ['ledger', 'level', 'recharge', 'pay-code', 'lottery', 'booking', 'appointments'].forEach((page) => {
    const source = read(`miniprogram/pages/${page}/index.js`);
    assert.match(source, /context\.requireCompany\(\)/, `${page} must verify session and membership`);
  });
  const home = read('miniprogram/pages/home/index.js');
  assert.match(home, /context\.loadAppContext\(\)/);
  assert.match(home, /appContext\.operator_companies/);
  assert.match(home, /appContext\.consumer_companies/);
  assert.doesNotMatch(home, /member\.account\(session\.company\(\)\)/);

  const context = read('miniprogram/services/context.js');
  assert.match(context, /openCompanies\(\)/);
  assert.match(context, /companies\.find/);

  const app = read('miniprogram/app.js');
  assert.match(app, /onShow\(options\)/, 'hot-start deep links must be captured');
  assert.match(app, /companyFromOptions\(options\)/);
  assert.match(app, /query\.scene/, 'mini program QR scene must resolve a company invite');
  assert.match(app, /session\.setInviteCompany\(companyCode\)/,
    'company invitations must not overwrite the active membership');

  const companies = read('miniprogram/pages/companies/index.js');
  assert.match(companies, /inviteChanged/,
    'a hot-start invite must replace stale join input on the live company page');
  assert.match(companies, /session\.inviteCompany\(\)/);
}

function testUnifiedPortalAndBookingContracts() {
  const app = JSON.parse(read('miniprogram/app.json'));
  [
    'pages/booking/index',
    'pages/appointments/index',
    'pages/operator/index',
    'pages/operator-finance/index',
    'pages/operator-sales/index',
    'pages/operator-register/index',
    'pages/operator-setup/index',
    'pages/operator-appointments/index',
    'pages/warehouse-link/index',
    'pages/gift-claim/index',
  ].forEach((page) => assert.ok(app.pages.includes(page), `${page} must be registered`));

  const member = read('miniprogram/services/member.js');
  assert.match(member, /\/api\/miniapp\/v1\/app-context/);
  assert.match(member, /\/booking\/slots/);
  assert.match(member, /createAppointment/);
  assert.match(member, /operatorAppointments/);
  assert.match(member, /\/gift-cards\/preview/);
  assert.match(member, /\/gift-cards\/claim/);
  assert.match(member, /\/merchant-no-show/);
  assert.match(member, /\/api\/miniapp\/v1\/auth\/warehouse/);
  assert.doesNotMatch(member, /\/api\/auth\/login/);
  assert.match(member, /\/sales\/checkout/);
  assert.match(member, /\/sales\/charge-card/);
  assert.match(member, /operatorRechargeCustomer/);
  assert.match(member, /saveOperatorMemberProfile/);
  assert.match(member, /operatorFinance/);
  assert.match(member, /recordOperatorFinance/);
  assert.match(member, /createOperatorCustomer/);
  assert.match(member, /issueCustomerClaimCode/);
  assert.match(member, /customerClaimPreview/);
  assert.match(member, /claimCustomerProfile/);

  const sales = read('miniprogram/pages/operator-sales/index.js');
  const salesTemplate = read('miniprogram/pages/operator-sales/index.wxml');
  const operator = read('miniprogram/pages/operator/index.js');
  const operatorTemplate = read('miniprogram/pages/operator/index.wxml');
  assert.match(sales, /member\.operatorSales/);
  assert.match(sales, /visibleCustomers/);
  assert.match(sales, /operatorDirectSale/);
  assert.match(sales, /operatorCreateSaleChargeCard/);
  assert.match(sales, /member\.operatorRechargeCustomer/);
  assert.match(sales, /member\.saveOperatorMemberProfile/);
  assert.match(sales, /member\.createOperatorCustomer/);
  assert.match(sales, /member\.issueCustomerClaimCode/);
  assert.match(sales, /phone/);
  assert.match(sales, /unit_price_minor/);
  assert.match(salesTemplate, /从客户数据库选择/);
  assert.match(salesTemplate, /搜索姓名、昵称、手机号或会员编号/);
  assert.match(salesTemplate, /直接充值/);
  assert.match(salesTemplate, /编辑会员资料/);
  assert.match(salesTemplate, /手动添加客户/);
  assert.match(salesTemplate, /生成本人认领二维码/);
  assert.match(salesTemplate, /自定义项目/);
  assert.match(salesTemplate, /TOTAL \/ 合计/);
  assert.doesNotMatch(salesTemplate, /输入完整会员编号/);
  assert.match(operator, /activeSection: 'overview'/);
  assert.match(operator, /switchSection\(event\)/);
  assert.match(operator, /transactionPageView/);
  assert.match(operatorTemplate, /data-section="transactions"/);
  assert.match(operatorTemplate, /activeSection === 'gifts'/);
  assert.match(operatorTemplate, /visibleTransactionCards/);
  assert.match(operatorTemplate, /id="issuedGift"/);
  assert.match(operatorTemplate, /财务系统/);
  assert.match(operator, /openFinance/);
  assert.match(operator, /礼品卡已生成/);
  assert.match(operator, /selector: '#issuedGift'/);
  assert.match(sales, /activeSection: 'checkout'/);
  assert.match(sales, /checkoutStep: 'customer'/);
  assert.match(sales, /switchCheckoutStep\(event\)/);
  assert.match(sales, /changeCatalogPage\(event\)/);
  assert.match(sales, /changeReceiptPage\(event\)/);
  assert.match(salesTemplate, /data-section="catalog"/);
  assert.match(salesTemplate, /checkoutStep === 'items'/);
  assert.match(salesTemplate, /checkoutStep === 'confirm'/);
  assert.match(salesTemplate, /visibleCatalog/);
  assert.match(salesTemplate, /visibleReceipts/);
  assert.match(read('miniprogram/pages/operator/index.wxss'), /\.workspace-nav \{[^}]*display: flex/);
  assert.match(read('miniprogram/pages/operator-sales/index.wxss'), /\.sales-workspace-nav \{[^}]*display: flex/);

  const finance = read('miniprogram/pages/operator-finance/index.js');
  const financeTemplate = read('miniprogram/pages/operator-finance/index.wxml');
  assert.match(finance, /member\.operatorFinance/);
  assert.match(finance, /member\.recordOperatorFinance/);
  assert.match(financeTemplate, /APP 本地账本|APP LEDGER/);
  assert.match(financeTemplate, /Warehouse 财务草稿/);
  assert.match(financeTemplate, /非会员消费/);

  const profile = read('miniprogram/pages/profile/index.js');
  const profileTemplate = read('miniprogram/pages/profile/index.wxml');
  assert.match(profile, /wx\.scanCode/);
  assert.match(profile, /member\.customerClaimPreview/);
  assert.match(profile, /member\.claimCustomerProfile/);
  assert.match(profile, /confirmText: '同意认领'/,
    'customer claim confirmation must stay within the WeChat four-character limit');
  assert.doesNotMatch(profile, /confirmText: '同意并认领'/);
  assert.match(profileTemplate, /扫描本人客户认领码/);

  const booking = read('miniprogram/pages/booking/index.js');
  assert.match(booking, /pending\.get\('appointment'/);
  assert.match(booking, /pending\.set\('appointment'/);
  assert.match(booking, /member\.createAppointment/);
  assert.match(booking, /slotKey:/, 'staff-specific slots need stable unique render keys');
  assert.match(booking, /search_days: searchDays/);
  assert.match(booking, /tryOtherServices/,
    'booking must try services available on the selected date before skipping to another day');
  assert.match(booking, /findNearestSlots/);
  assert.match(booking, /onCompanyChange/,
    'booking must use the same persisted company selection as home');
  assert.match(booking, /session\.setCompany\(code\)/);
  assert.match(read('miniprogram/pages/booking/index.wxml'), /wx:key="slotKey"/);

  const appointments = read('miniprogram/pages/appointments/index.js');
  assert.match(appointments, /onCompanyChange/,
    'personal appointments must expose the same company selector as booking');
  assert.match(appointments, /session\.setCompany\(code\)/);

  const homeTemplate = read('miniprogram/pages/home/index.wxml');
  assert.match(homeTemplate, /warehouseAccountName/,
    'a verified Warehouse identity must display its account name');
  assert.match(homeTemplate, /身份管理/);

  const setup = read('miniprogram/pages/operator-setup/index.js');
  const setupTemplate = read('miniprogram/pages/operator-setup/index.wxml');
  assert.match(setup, /Asia\/Singapore/);
  assert.match(setup, /customSchedule/);
  assert.match(setup, /openingPeriodsFromRules/);
  assert.match(setup, /addOpeningPeriod/);
  assert.match(setup, /intervalsByWeekday/);
  assert.match(setup, /scope_type: 'service'/);
  assert.match(setup, /scope_type: 'staff'/);
  assert.match(setup, /onServiceScheduleToggle/);
  assert.match(setup, /addServicePeriod/);
  assert.match(setup, /maximumOpenOverlap/);
  assert.match(setup, /availableMinutes <= 0/,
    'service schedule saving must reject windows with no studio overlap');
  assert.match(setup, /availableMinutes < duration/,
    'an impossible service duration must be rejected before it empties consumer slots');
  assert.match(setup, /共同可用时段最长/);
  assert.match(setup, /addStaffPeriod/);
  assert.match(setup, /staff.*periods|periods.*staff/s,
    'staff schedules must retain multiple periods instead of collapsing to one row');
  assert.match(setup, /time_blocks: this\.data\.timeBlocks/,
    'booking setup saves must preserve server time blocks');
  assert.match(setup, /没有任何员工拥有/,
    'setup must reject a location-service weekday that has no usable staff overlap');
  assert.match(setupTemplate, /bindtap="addOpeningPeriod"/);
  assert.match(setupTemplate, /bindtap="addServicePeriod"/);
  assert.match(setupTemplate, /bindtap="addStaffPeriod"/);
  assert.match(setupTemplate, /wx:for="\{\{item\.periods\}\}"/);
  assert.match(setupTemplate, /bindchange="onOpeningWeekdays"/);
  assert.match(setupTemplate, /bindchange="onServiceWeekdays"/);
  assert.match(setupTemplate, /bindchange="onStaffWeekdays"/);
  assert.match(setupTemplate, /bindchange="onTimezoneChange"/);
  assert.match(setupTemplate, /data-contract="booking-start-interval"/);
  assert.match(setupTemplate, /data-contract="booking-occupancy-duration"/);
  assert.match(setupTemplate, /工作室 × 服务时间自动取交集/);

  assert.match(booking, /refreshBookingDate/);
  assert.match(booking, /companyTimezone/);
  assert.match(booking, /availabilityDiagnostics/);
  assert.match(read('miniprogram/pages/booking/index.wxml'), /排班诊断/);
  assert.match(operator, /session\.setCompany\(this\.data\.selected\.public_code\)/,
    'consumer preview must switch to the company currently open in operator mode');

  assert.match(sales, /confirmText: confirmationMode \? '发送卡片' : '确认扣款'/);
  assert.doesNotMatch(sales, /扣款并出票/);
  assert.match(sales, /扣款确认窗口打开失败/);
  const operatorAppointments = read('miniprogram/pages/operator-appointments/index.js');
  assert.match(operatorAppointments, /confirmText: decision === 'confirm' \? '确认补分'/);
  assert.doesNotMatch(operatorAppointments, /确认并补分/);
  assert.match(operatorAppointments, /爽约处理窗口打开失败/);

  const register = read('miniprogram/pages/operator-register/index.js');
  assert.match(register, /consent_version: this\.data\.consent\.version/);
  assert.doesNotMatch(register, /consent_version:\s*['"]2026-/);

  const warehouseLink = read('miniprogram/pages/warehouse-link/index.js');
  assert.match(warehouseLink, /member\.warehouseSignIn/);
  assert.match(warehouseLink, /appContext\.warehouse\.companies/);
  assert.match(warehouseLink, /pages\/operator-register\/index/);
  assert.doesNotMatch(warehouseLink, /setStorageSync\([^)]*(?:password|warehouse_token)/i);
}

function testCompanyAndConsentContracts() {
  const companies = read('miniprogram/pages/companies/index.js');
  const template = read('miniprogram/pages/companies/index.wxml');
  assert.match(companies, /member\.company\(code\)/, 'join must preview public company data');
  assert.match(companies, /result\.consent \|\| company\.consent/);
  assert.match(companies, /preview\.consentVersion/);
  assert.match(companies, /member\.join\(this\.data\.joinCode, preview\.consentVersion\)/);
  assert.doesNotMatch(companies, /member\.join\([^\n]*['"]2026-/);
  assert.match(template, /joinPreview\.consentText/);
  assert.match(template, /MEMBERSHIP PAYEE \/ 会员收款方/);

  const recharge = read('miniprogram/pages/recharge/index.wxml');
  const payCode = read('miniprogram/pages/pay-code/index.wxml');
  const lottery = read('miniprogram/pages/lottery/index.wxml');
  assert.match(recharge, /companyName/);
  assert.match(recharge, /会员收款方/);
  assert.match(payCode, /companyName/);
  assert.match(payCode, /本次消费公司/);
  assert.match(payCode, /scroll-y="true"/);
  assert.match(lottery, /companyName/);
  assert.match(lottery, /活动公司/);
}

function testPresentationContracts() {
  filesBelow('miniprogram', '.wxml').forEach((absolute) => {
    const source = fs.readFileSync(absolute, 'utf8');
    const relative = path.relative(ROOT, absolute);
    assert.doesNotMatch(source, /\{\{[^}]*\/\s*100[^}]*\}\}/, `${relative} must not calculate money in WXML`);
    assert.doesNotMatch(source, /Warehouse 2\.0 (?:已)?联动/, `${relative} overstates Warehouse linkage`);
    assert.doesNotMatch(source, /<(?:b|small|i)(?:\s|>)/,
      `${relative} must use native WXML components instead of HTML-only tags`);
    assert.doesNotMatch(
      source,
      /[\u2190-\u21ff\u2794\u276f\u203a]|⌄|⌗/u,
      `${relative} must use textual Swiss commands instead of arrow glyphs`,
    );
  });
  const ledger = read('miniprogram/pages/ledger/index.js');
  const ledgerTemplate = read('miniprogram/pages/ledger/index.wxml');
  assert.match(ledger, /member\.transactionCards\(selected\.code\)/);
  assert.match(ledger, /card\.type === 'charge' && card\.status === 'completed'/);
  assert.match(ledger, /time\.formatLocalDateTime\(card\.created_at\)/);
  assert.doesNotMatch(ledger, /member\.ledger\(/);
  assert.match(ledgerTemplate, /消费记录/);
  assert.match(ledgerTemplate, /item\.lines/);
  assert.match(ledgerTemplate, /item\.unitPriceText/);
  assert.match(ledgerTemplate, /本地时间/);
  assert.match(ledgerTemplate, /双方同号留存/);
  assert.match(read('miniprogram/pages/home/index.wxml'), /消费记录/);

  const profile = read('miniprogram/pages/profile/index.js');
  const profileTemplate = read('miniprogram/pages/profile/index.wxml');
  assert.match(profile, /money\.formatMinor\(account\.balance_minor\)/);
  assert.match(profile, /companyUtil\.modeLabel\(account\.company\)/);
  assert.match(profile, /theme\.save/);
  assert.match(profile, /saveCustomTheme/);
  assert.match(profileTemplate, /Swiss 配色/);
  assert.match(profileTemplate, /themeDraftAccent/);
  assert.match(profileTemplate, /themeDraftInk/);
  filesBelow('miniprogram/pages', '.wxml').forEach((absolute) => {
    const source = fs.readFileSync(absolute, 'utf8').trim();
    assert.ok(source.startsWith('<theme-provider'),
      `${path.relative(ROOT, absolute)} must inherit the saved Swiss theme`);
    assert.ok(source.endsWith('</theme-provider>'),
      `${path.relative(ROOT, absolute)} must close the Swiss theme provider`);
  });
  const appConfig = JSON.parse(read('miniprogram/app.json'));
  assert.strictEqual(
    appConfig.usingComponents['theme-provider'],
    '/components/theme-provider/index',
  );
  assert.match(read('miniprogram/app.wxss'), /var\(--swiss-accent/);
  assert.match(read('miniprogram/app.wxss'), /var\(--swiss-ink/);
  assert.match(read('miniprogram/utils/company.js'), /已绑定 · 财务草稿联动/);
}

function testLotteryIdempotencyContract() {
  const lottery = read('miniprogram/pages/lottery/index.js');
  const member = read('miniprogram/services/member.js');
  const getIndex = lottery.indexOf("pending.get('lottery-draw', scope)");
  const setIndex = lottery.indexOf("pending.set('lottery-draw', scope, requestId)");
  const drawIndex = lottery.indexOf('member.draw(companyCode, campaignCode, requestId)');
  const clearIndex = lottery.indexOf("pending.clear('lottery-draw', scope)");
  assert.ok(getIndex >= 0 && setIndex > getIndex && drawIndex > setIndex && clearIndex > drawIndex,
    'draw key must be read, persisted before request, and cleared only after success');
  assert.match(member, /async function draw\(code, campaignCode, idempotencyKey\)/);
  assert.match(member, /idempotencyKey: key/);
  assert.doesNotMatch(lottery, /campaignCode:\s*['"]launch['"]/);
  assert.match(lottery, /member\.lotteryCampaigns\(selected\.code\)/);
  assert.match(lottery, /member\.rewards\(selected\.code\)/);
  assert.match(read('miniprogram/pages/lottery/index.wxml'), /我的奖品/);
  assert.match(lottery, /result: companyChanged \? null : this\.data\.result/,
    'a draw result must never survive a company switch');
  assert.match(lottery, /this\.drawInFlight/,
    'rapid taps must not start two server draws with different keys');
}

function testCompanyScopedEphemeralState() {
  const payCode = read('miniprogram/pages/pay-code/index.js');
  assert.match(payCode, /companyChanged/);
  assert.match(payCode, /nextData\.paymentCode = ''/,
    'a one-time payment code must be cleared when switching companies');
  assert.match(payCode, /qr\.draw/);
  assert.match(read('miniprogram/pages/pay-code/index.wxml'), /canvas type="2d"/);
  assert.match(read('miniprogram/pages/pay-code/index.wxml'), /bonfire-platform-mark\.png/);
  const lotteryTemplate = read('miniprogram/pages/lottery/index.wxml');
  assert.match(lotteryTemplate, /!contextLoading && result/,
    'stale lottery results must be hidden while company context is changing');
}

function testRechargeIdempotencyContract() {
  const recharge = read('miniprogram/pages/recharge/index.js');
  const rechargeTemplate = read('miniprogram/pages/recharge/index.wxml');
  const member = read('miniprogram/services/member.js');
  const getIndex = recharge.indexOf("pending.get('recharge', requestScope)");
  const setIndex = recharge.indexOf("pending.set('recharge', requestScope, requestId)");
  const requestIndex = recharge.indexOf('member.recharge(companyCode, amount, requestId)');
  const clearIndex = recharge.indexOf("pending.clear('recharge', requestScope)");
  assert.ok(getIndex >= 0 && setIndex > getIndex && requestIndex > setIndex && clearIndex > requestIndex,
    'recharge key must survive an unknown HTTP result and clear only after a known response');
  assert.match(recharge, /this\.submitInFlight/);
  assert.match(member, /async function recharge\(code, amountMinor, idempotencyKey\)/);
  assert.match(recharge, /member\.transactionCards/);
  assert.match(recharge, /member\.acknowledgeTransactionCard/);
  assert.match(recharge, /member\.confirmChargeCard/);
  assert.match(recharge, /member\.declineChargeCard/);
  assert.match(member, /operatorConfirmTransactionCard/);
  assert.match(member, /operatorCreateChargeCard/);
  assert.match(rechargeTemplate, /不调用微信商户 API/);
  assert.doesNotMatch(recharge, /wx\.requestPayment/);

  const operator = read('miniprogram/pages/operator/index.js');
  const operatorTemplate = read('miniprogram/pages/operator/index.wxml');
  const sales = read('miniprogram/pages/operator-sales/index.js');
  const salesTemplate = read('miniprogram/pages/operator-sales/index.wxml');
  assert.match(sales, /member\.operatorCreateSaleChargeCard/);
  assert.match(operator, /wx\.scanCode/);
  assert.match(operator, /member\.operatorRedeemPaymentCode/);
  assert.match(operator, /member\.operatorCreateGiftCard/);
  assert.match(operatorTemplate, /数据库选客/);
  assert.match(salesTemplate, /发送逐项扣费确认卡/);
  assert.match(operatorTemplate, /扫描用户付款 QR/);
}

function testGiftCardContract() {
  const gift = read('miniprogram/pages/gift-claim/index.js');
  const giftTemplate = read('miniprogram/pages/gift-claim/index.wxml');
  const member = read('miniprogram/services/member.js');
  const operator = read('miniprogram/pages/operator/index.js');
  const operatorTemplate = read('miniprogram/pages/operator/index.wxml');

  assert.match(gift, /context\.loadMemberships\(\)/,
    'gift deep links must establish a consumer session without assuming membership');
  assert.match(gift, /member\.giftCardPreview/);
  assert.match(gift, /member\.join\(this\.data\.companyCode, this\.data\.consentVersion\)/);
  assert.match(gift, /wx\.scanCode/);
  assert.match(giftTemplate, /bonfire-platform-mark\.png/);
  assert.match(giftTemplate, /确认领取并写入会员余额/);

  const claimGet = gift.indexOf("pending.get('gift-claim', requestScope)");
  const claimSet = gift.indexOf("pending.set('gift-claim', requestScope, requestId)");
  const claimRequest = gift.indexOf('member.claimGiftCard(');
  const claimClear = gift.indexOf("pending.clear('gift-claim', requestScope)");
  assert.ok(
    claimGet >= 0 && claimSet > claimGet
      && claimRequest > claimSet && claimClear > claimRequest,
    'gift claim must retain one idempotency key until the server response is known',
  );

  const issueGet = operator.indexOf("pending.get('gift-issue', requestScope)");
  const issueSet = operator.indexOf("pending.set('gift-issue', requestScope, requestId)");
  const issueRequest = operator.indexOf('member.operatorCreateGiftCard(');
  const issueClear = operator.indexOf("pending.clear('gift-issue', requestScope)");
  assert.ok(
    issueGet >= 0 && issueSet > issueGet
      && issueRequest > issueSet && issueClear > issueRequest,
    'gift issue must converge on the same encrypted server card after an unknown response',
  );
  assert.match(operator, /onShareAppMessage/);
  assert.match(operator, /qr\.draw\(this, '#giftQr'/);
  assert.match(operator, /confirmText: '确认发行'/,
    'sold gift confirmation must stay within the WeChat four-character limit');
  assert.doesNotMatch(operator, /confirmText: '确认并发行'/);
  assert.match(operator, /收款确认窗口打开失败，请重试/,
    'modal API failures must be visible instead of looking like a cancelled tap');
  assert.match(operatorTemplate, /open-type="share"/);
  assert.match(operatorTemplate, /发行礼品卡/);
  assert.match(member, /operatorCreateGiftCard/);
  assert.match(member, /claimGiftCard/);
}

function testCompactWorkspaceControls() {
  const operatorStyles = read('miniprogram/pages/operator/index.wxss');
  const salesStyles = read('miniprogram/pages/operator-sales/index.wxss');
  assert.match(operatorStyles, /\.workspace-tab \{[^}]*width: 136rpx/);
  assert.match(operatorStyles, /\.workspace-tab \.workspace-tab-label \{[^}]*font-size: 22rpx/);
  assert.match(salesStyles, /\.sales-workspace-tab \{[^}]*width: 0[^}]*flex: 1/);
  assert.match(salesStyles, /\.sales-workspace-tab \.sales-workspace-label \{[^}]*font-size: 22rpx/);
  assert.match(salesStyles, /\.checkout-stage \{[^}]*width: 150rpx/);
  assert.match(salesStyles, /\.checkout-stage \.checkout-stage-label \{[^}]*font-size: 21rpx/);
  assert.match(salesStyles, /\.checkout-submit \{[^}]*width: auto[^}]*font-size: 25rpx/);
}

function testNoShowRuleContract() {
  const consumer = read('miniprogram/pages/appointments/index.js');
  const consumerTemplate = read('miniprogram/pages/appointments/index.wxml');
  const operator = read('miniprogram/pages/operator-appointments/index.js');
  const operatorTemplate = read('miniprogram/pages/operator-appointments/index.wxml');
  const member = read('miniprogram/services/member.js');

  assert.match(member, /reportMerchantNoShow/);
  assert.match(member, /operatorResolveMerchantNoShow/);
  assert.match(consumer, /item\.can_report_merchant_no_show/);
  assert.match(consumerTemplate, /商家未履约 · 提交确认报告/);
  assert.match(operator, /status="consumer_no_show"|consumer_no_show/);
  assert.match(operatorTemplate, /用户爽约 · 自动扣分/);
  assert.match(operatorTemplate, /确认爽约并补分/);

  const reportGet = consumer.indexOf("pending.get('merchant-no-show-report', scope)");
  const reportSet = consumer.indexOf("pending.set('merchant-no-show-report', scope, requestId)");
  const reportRequest = consumer.indexOf('member.reportMerchantNoShow(');
  const reportClear = consumer.indexOf("pending.clear('merchant-no-show-report', scope)");
  assert.ok(
    reportGet >= 0 && reportSet > reportGet
      && reportRequest > reportSet && reportClear > reportRequest,
    'merchant no-show report must preserve its idempotency key across unknown responses',
  );

  const resolveGet = operator.indexOf("pending.get('merchant-no-show-resolution', scope)");
  const resolveSet = operator.indexOf("pending.set('merchant-no-show-resolution', scope, requestId)");
  const resolveRequest = operator.indexOf('member.operatorResolveMerchantNoShow(');
  const resolveClear = operator.indexOf("pending.clear('merchant-no-show-resolution', scope)");
  assert.ok(
    resolveGet >= 0 && resolveSet > resolveGet
      && resolveRequest > resolveSet && resolveClear > resolveRequest,
    'merchant no-show resolution must preserve its idempotency key across unknown responses',
  );
}

function testMembershipProgramContract() {
  const level = read('miniprogram/pages/level/index.js');
  const template = read('miniprogram/pages/level/index.wxml');
  const member = read('miniprogram/services/member.js');
  assert.match(member, /membership-program/);
  assert.match(member, /lottery\/campaigns/);
  assert.match(member, /companies\/\$\{code\}\/rewards/);
  assert.match(level, /member\.membershipProgram\(selected\.code\)/);
  assert.match(level, /program\.progress\.basis_points/);
  assert.match(level, /benefitRows\(level\.benefits\)/);
  assert.match(template, /当前权益/);
  assert.match(template, /下一等级/);
}

async function testBookingScheduleRuntime() {
  const timeBlocks = [{
    scope_type: 'location',
    scope_code: 'main',
    block_type: 'unavailable',
    starts_at: '2026-08-01 02:00:00',
    ends_at: '2026-08-01 03:00:00',
    note: '设备维护',
  }];
  const dashboard = {
    company: { name: 'Weekend Studio' },
    locations: [{
      code: 'main', name: 'Weekend Studio', active: true,
      timezone: 'Asia/Shanghai', slot_interval_minutes: 30, min_notice_minutes: 0,
    }],
    services: [{
      code: 'consult', name: '咨询', active: true, duration_minutes: 30,
      price_minor: 10000, deposit_minor: 0,
    }],
    staff: [{ code: 'alice', name: 'Alice', title: '顾问', active: true }],
    schedule_rules: [
      { scope_type: 'location', scope_code: 'main', weekday: 5, start: '09:00', end: '12:00', active: true },
      { scope_type: 'location', scope_code: 'main', weekday: 6, start: '10:00', end: '14:00', active: true },
      { scope_type: 'staff', scope_code: 'alice', weekday: 5, start: '09:00', end: '10:00', active: true },
      { scope_type: 'staff', scope_code: 'alice', weekday: 5, start: '11:00', end: '12:00', active: true },
      { scope_type: 'staff', scope_code: 'alice', weekday: 6, start: '10:00', end: '14:00', active: true },
    ],
    time_blocks: timeBlocks,
  };
  const saved = [];
  const runtime = loadPageRuntime('miniprogram/pages/operator-setup/index.js', {
    '../../services/member': {
      async operatorBooking() { return dashboard; },
      async saveBookingSetup(code, payload) { saved.push({ code, payload }); return {}; },
    },
    '../../store/session': { operatorCompany() { return 'weekend-studio'; } },
    '../../utils/money': { formatMinor(value) { return (Number(value || 0) / 100).toFixed(2); } },
  }, {
    showToast() {},
    navigateBack() {},
  });
  const page = runtime.page;
  await page.load();
  assert.strictEqual(page.data.staff[0].periods.length, 3,
    'two Saturday windows and one Sunday window must survive dashboard loading');
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(page.data.staff[0].periods.map((period) => ({
      start: period.start,
      end: period.end,
      days: Array.from(period.selectedWeekdays),
    })))),
    [
      { start: '09:00', end: '10:00', days: ['5'] },
      { start: '11:00', end: '12:00', days: ['5'] },
      { start: '10:00', end: '14:00', days: ['6'] },
    ],
  );
  await page.save();
  assert.strictEqual(saved.length, 1);
  assert.strictEqual(saved[0].payload.location.slot_interval_minutes, 30);
  assert.deepStrictEqual(JSON.parse(JSON.stringify(saved[0].payload.time_blocks)), timeBlocks,
    'server time blocks must round-trip unchanged');
  const staffRules = saved[0].payload.schedule_rules.filter(
    (rule) => rule.scope_type === 'staff' && rule.scope_code === 'alice',
  );
  assert.deepStrictEqual(
    JSON.parse(JSON.stringify(staffRules)),
    [
      { scope_type: 'staff', scope_code: 'alice', weekday: 5, start: '09:00', end: '10:00' },
      { scope_type: 'staff', scope_code: 'alice', weekday: 5, start: '11:00', end: '12:00' },
      { scope_type: 'staff', scope_code: 'alice', weekday: 6, start: '10:00', end: '14:00' },
    ],
    'multi-period weekend staff rules must round-trip without collapsing',
  );

  page.data.staff[0].periods = page.data.staff[0].periods.filter(
    (period) => period.selectedWeekdays.indexOf('6') < 0,
  );
  await page.save();
  assert.strictEqual(saved.length, 1, 'invalid Sunday staff coverage must not reach the API');
  assert.match(page.data.error, /星期日没有任何员工拥有/);
}

async function testBookingDateAndOperatorCompanyRuntime() {
  let requestedDate = '';
  const selected = {
    code: 'weekend-studio',
    company: { code: 'weekend-studio', name: 'Weekend Studio' },
    memberships: [{ company: { code: 'weekend-studio', name: 'Weekend Studio' } }],
  };
  const bookingRuntime = loadPageRuntime('miniprogram/pages/booking/index.js', {
    '../../services/context': { async requireCompany() { return selected; }, openCompanies() {} },
    '../../services/member': {
      async bookingCatalog() {
        return {
          locations: [{ code: 'main', timezone: 'Asia/Shanghai' }],
          services: [{ code: 'consult', name: '咨询', duration_minutes: 30, price_minor: 0 }],
          staff: [],
        };
      },
      async bookingSlots(_code, params) {
        requestedDate = params.date;
        return {
          date: params.date,
          searched_through: params.date,
          slots: [],
          diagnostics: [{ code: 'location_closed', message: '工作室在所选日期没有开放时段' }],
        };
      },
    },
    '../../store/pending': {},
    '../../store/session': { setCompany() {} },
    '../../utils/money': { formatMinor() { return '0.00'; } },
  }, {});
  const booking = bookingRuntime.page;
  booking.bookingDateReady = true;
  booking.data.selectedDate = '2000-01-01';
  await booking.load();
  const expectedParts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date()).reduce((all, part) => ({ ...all, [part.type]: part.value }), {});
  const expectedShanghaiDate = `${expectedParts.year}-${expectedParts.month}-${expectedParts.day}`;
  assert.strictEqual(booking.data.minDate, expectedShanghaiDate);
  assert.strictEqual(booking.data.selectedDate, expectedShanghaiDate);
  assert.strictEqual(requestedDate, expectedShanghaiDate,
    'stale device dates must be refreshed in the company timezone before slot lookup');
  assert.deepStrictEqual(
    Array.from(booking.data.availabilityDiagnostics),
    ['工作室在所选日期没有开放时段'],
  );

  let companyCode = '';
  let portal = '';
  let switchedUrl = '';
  const operatorRuntime = loadPageRuntime('miniprogram/pages/operator/index.js', {
    '../../services/context': {},
    '../../services/member': {},
    '../../store/session': {
      setCompany(value) { companyCode = value; },
      setPortal(value) { portal = value; },
    },
    '../../store/pending': {},
    '../../utils/money': {},
    '../../utils/time': {},
    '../../utils/qr': {},
    '../../utils/theme': {},
  }, {
    switchTab(options) { switchedUrl = options.url; },
  });
  operatorRuntime.page.data.selected = { public_code: 'weekend-studio' };
  operatorRuntime.page.openConsumer();
  assert.strictEqual(companyCode, 'weekend-studio');
  assert.strictEqual(portal, 'consumer');
  assert.strictEqual(switchedUrl, '/pages/home/index');
}

async function testBookingAutomaticallySelectsAvailableServiceRuntime() {
  const calls = [];
  const selected = {
    code: 'yuanqi',
    company: { code: 'yuanqi', name: 'Yuanqi Studio' },
    memberships: [{ company: { code: 'yuanqi', name: 'Yuanqi Studio' } }],
  };
  const runtime = loadPageRuntime('miniprogram/pages/booking/index.js', {
    '../../services/context': { async requireCompany() { return selected; }, openCompanies() {} },
    '../../services/member': {
      async bookingCatalog() {
        return {
          locations: [{ code: 'main', timezone: 'Asia/Singapore' }],
          services: [
            { code: 'weekday', name: 'Weekday entry', duration_minutes: 30, price_minor: 0 },
            { code: 'weekend', name: 'Weekend entry', duration_minutes: 30, price_minor: 0 },
          ],
          staff: [],
        };
      },
      async bookingSlots(_code, params) {
        calls.push({ ...params });
        const common = {
          requested_date: params.date,
          date: params.date,
          searched_through: params.date,
          timezone: 'Asia/Singapore',
          today: params.date,
          auto_advanced: false,
        };
        if (params.service_code === 'weekend') {
          return {
            ...common,
            slots: [{
              starts_at: `${params.date} 07:30:00`,
              ends_at: `${params.date} 08:00:00`,
              local_start: '15:30',
              local_end: '16:00',
              staff: null,
            }],
            diagnostics: [],
          };
        }
        return {
          ...common,
          slots: [],
          diagnostics: [{ code: 'service_closed', message: 'Weekday service is closed' }],
        };
      },
    },
    '../../store/pending': {},
    '../../store/session': { setCompany() {} },
    '../../utils/money': { formatMinor() { return '0.00'; } },
  }, {});
  const booking = runtime.page;
  await booking.load();
  assert.deepStrictEqual(
    calls.slice(0, 2).map((item) => [item.service_code, item.search_days]),
    [['weekday', 0], ['weekend', 0]],
    'initial booking load must check every service on the selected date before skipping ahead',
  );
  assert.strictEqual(booking.data.serviceIndex, 1);
  assert.strictEqual(booking.data.selectedService.code, 'weekend');
  assert.strictEqual(booking.data.slots[0].local_start, '15:30');
  assert.match(booking.data.slotNotice, /Weekend entry/);
}

async function testRequestIdRuntime() {
  const requestPath = path.join(ROOT, 'miniprogram/services/request.js');
  delete require.cache[require.resolve(requestPath)];
  let argument = null;
  global.wx = {
    getRandomValues(options) {
      argument = options;
      const values = new Uint8Array(options.length);
      values.fill(0xab);
      options.success({ randomValues: values });
    },
  };
  const api = require(requestPath);
  const value = await api.requestId('draw');
  assert.strictEqual(typeof argument, 'object');
  assert.strictEqual(argument.length, 16);
  assert.match(value, /^draw-\d+-abababababababababababababababab$/);
}

function testPendingRuntime() {
  const pendingPath = path.join(ROOT, 'miniprogram/store/pending.js');
  delete require.cache[require.resolve(pendingPath)];
  const storage = {};
  global.wx = {
    getStorageSync(key) { return storage[key]; },
    setStorageSync(key, value) { storage[key] = value; },
  };
  const pending = require(pendingPath);
  pending.set('lottery-draw', 'alpha:launch', 'draw-1');
  assert.strictEqual(pending.get('lottery-draw', 'alpha:launch'), 'draw-1');
  pending.clear('lottery-draw', 'alpha:launch');
  assert.strictEqual(pending.get('lottery-draw', 'alpha:launch'), '');
  for (let index = 0; index < 25; index += 1) pending.set('test', String(index), `id-${index}`);
  assert.ok(Object.keys(storage['warehouse.member.pending.requests']).length <= 20);
}

function testSessionCompanyIsolationRuntime() {
  const sessionPath = path.join(ROOT, 'miniprogram/store/session.js');
  delete require.cache[require.resolve(sessionPath)];
  const storage = {};
  global.wx = {
    getStorageSync(key) { return storage[key]; },
    setStorageSync(key, value) { storage[key] = value; },
    removeStorageSync(key) { delete storage[key]; },
  };
  const session = require(sessionPath);
  session.setCompany('active-company');
  session.setInviteCompany('invited-company');
  assert.strictEqual(session.company(), 'active-company');
  assert.strictEqual(session.inviteCompany(), 'invited-company');
  session.clear();
  assert.strictEqual(session.company(), '');
  assert.strictEqual(session.inviteCompany(), '');
}

function testUtilitiesRuntime() {
  const money = require(path.join(ROOT, 'miniprogram/utils/money.js'));
  const time = require(path.join(ROOT, 'miniprogram/utils/time.js'));
  assert.strictEqual(money.formatMinor(12345), '123.45');
  assert.strictEqual(time.parseUtc('2026-07-16 12:34:56').getTime(), Date.UTC(2026, 6, 16, 12, 34, 56));
  assert.match(time.formatLocalDateTime('2026-07-16 12:34:56'), /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
}

function testThemeRuntime() {
  const themePath = path.join(ROOT, 'miniprogram/utils/theme.js');
  delete require.cache[require.resolve(themePath)];
  const storage = {};
  global.wx = {
    getStorageSync(key) { return storage[key]; },
    setStorageSync(key, value) { storage[key] = value; },
    removeStorageSync(key) { delete storage[key]; },
    setNavigationBarColor() {},
    setTabBarStyle() {},
  };
  const theme = require(themePath);
  assert.strictEqual(theme.current().accent, '#E0261C');
  const selected = theme.save({ accent: '#f2c94c', ink: '#172a46' });
  assert.strictEqual(selected.accent, '#F2C94C');
  assert.strictEqual(selected.onAccent, '#000000');
  assert.match(theme.style(selected), /--swiss-accent:#F2C94C/);
  assert.match(theme.style(selected), /--swiss-ink:#172A46/);
  assert.throws(() => theme.save({ accent: 'red', ink: '#000' }), /#RRGGBB/);
  assert.strictEqual(theme.reset().id, 'classic-red');
}

function testServerLogoutContract() {
  const member = read('miniprogram/services/member.js');
  const profile = read('miniprogram/pages/profile/index.js');
  assert.match(member, /\/api\/miniapp\/v1\/auth\/logout/);
  const revokeIndex = profile.indexOf('await member.logout(allSessions)');
  const clearIndex = profile.indexOf('session.clear()');
  assert.ok(revokeIndex >= 0 && clearIndex > revokeIndex, 'server revoke must happen before local clear');
}

async function main() {
  testDirectPageGuards();
  testCompanyAndConsentContracts();
  testPresentationContracts();
  testLotteryIdempotencyContract();
  testCompanyScopedEphemeralState();
  testRechargeIdempotencyContract();
  testGiftCardContract();
  testCompactWorkspaceControls();
  testNoShowRuleContract();
  testMembershipProgramContract();
  testUnifiedPortalAndBookingContracts();
  await testBookingScheduleRuntime();
  await testBookingDateAndOperatorCompanyRuntime();
  await testBookingAutomaticallySelectsAvailableServiceRuntime();
  testSessionCompanyIsolationRuntime();
  await testRequestIdRuntime();
  testPendingRuntime();
  testUtilitiesRuntime();
  testThemeRuntime();
  testServerLogoutContract();
  process.stdout.write('wechat miniapp frontend contracts: ok\n');
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error}\n`);
  process.exitCode = 1;
});
