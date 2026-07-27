/* ============================================================
   iPhone 17 Mobile ERP Workbench
   ============================================================ */
const { useEffect: useMobileEffect, useState: useMobileState } = React;

const MOBILE_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const MOBILE_AUTH_KEY = "warehouse_auth_token";
const MOBILE_TENANT_KEY = "warehouse_current_tenant";
const MOBILE_LANG_KEY = "warehouse_mobile_lang";

const MOBILE_EMPTY_BOOTSTRAP = {
  NAV_CONFIG: { items: {} }, CUSTOM_MODULES: [],
  WAREHOUSES: ["—"], CATEGORIES: [], LEDGER_CATEGORIES: [], INVENTORY: [], ALERTS: [], INBOUND: [],
  OUTBOUND: [], FAULT_TYPES: [], STOCKTAKE: [], STOCKTAKE_DIFF: [], ZONES: [],
  AI_TASKS: [], AI_LOG: [], PEOPLE: [], ROLES: [], FLOW: { title: "—", steps: [] },
};

const mobileApplyBootstrap = (payload) => Object.assign(window, { ...MOBILE_EMPTY_BOOTSTRAP, ...(payload || {}) });
const mobileToken = () => window.localStorage.getItem(MOBILE_AUTH_KEY) || "";
const mobileSetToken = (token) => token ? window.localStorage.setItem(MOBILE_AUTH_KEY, token) : window.localStorage.removeItem(MOBILE_AUTH_KEY);
const mobileTenant = () => window.localStorage.getItem(MOBILE_TENANT_KEY) || "";
const mobileSetTenant = (slug) => slug ? window.localStorage.setItem(MOBILE_TENANT_KEY, slug) : window.localStorage.removeItem(MOBILE_TENANT_KEY);
const mobileLang = () => window.localStorage.getItem(MOBILE_LANG_KEY) || "zh-Hant";
const mobileSetLang = (lang) => window.localStorage.setItem(MOBILE_LANG_KEY, lang === "zh-Hans" ? "zh-Hans" : "zh-Hant");
const mobileApiUrl = (url) => /^https?:\/\//.test(url) ? url : MOBILE_API_BASE + url;
const mobileMoney = (value) => "¥" + Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 });
const mobileNumber = (value) => Number(value || 0).toLocaleString("zh-CN");
const mobileCount = (value) => {
  const n = Number(value || 0);
  return Number.isFinite(n) ? n : 0;
};
const MOBILE_ARCHIVED_PURCHASE_STATUSES = new Set(["received", "cancelled", "completed", "closed"]);
const MOBILE_ARCHIVED_INVENTORY_STATUSES = new Set(["confirmed", "posted", "closed", "cancelled", "completed", "done"]);
const mobileStatusIn = (statuses, value) => statuses.has(String(value || "").trim().toLowerCase());
const mobilePurchaseOpen = (purchase) => !mobileStatusIn(MOBILE_ARCHIVED_PURCHASE_STATUSES, purchase?.status || "draft");
const mobileBudgetUnlinkedOpen = (doc) => {
  if (doc?.budget_unlinked_open === true) return true;
  if (doc?.budget_unlinked_open === false) return false;
  return Boolean(doc?.needs_budget && !doc?.budget_reservation_id && !mobileStatusIn(MOBILE_ARCHIVED_INVENTORY_STATUSES, doc?.status || "draft") && !doc?.confirmed_at && !doc?.cancelled_at);
};

const MOBILE_I18N = {
  "zh-Hant": {
    "lang.name": "繁", "lang.next": "简",
    "nav.erp": "ERP 中樞", "nav.erp.short": "ERP",
    "nav.unified": "統一", "nav.unified.short": "統一",
    "nav.finance": "AI 財務", "nav.finance.short": "財務",
    "nav.overview": "倉儲總覽", "nav.overview.short": "倉儲",
    "nav.collab": "AI 協作", "nav.collab.short": "協作",
    "nav.alerts": "智能預警", "nav.alerts.short": "預警",
    "auth.login": "登入", "auth.register": "申請註冊",
    "auth.title": "ERP 工作台", "auth.registerTitle": "申請註冊",
    "auth.loginSub": "登入後建立安全會話，下次可直接進入",
    "auth.registerSub": "提交後由企業管理員審批",
    "auth.account": "帳號 / 郵箱", "auth.password": "密碼",
    "auth.companyCode": "企業代碼", "auth.displayName": "顯示名稱",
    "auth.confirmPassword": "確認密碼", "auth.role": "期望角色",
    "auth.department": "部門 / 班組", "auth.contact": "聯絡方式",
    "auth.reason": "申請理由", "auth.submit": "提交申請",
    "auth.processing": "處理中...", "auth.foot": "公共設備使用後請登出；會話失效時系統會自動回到登入頁。",
    "auth.errAccount": "請輸入帳號或郵箱", "auth.errPassword": "請輸入密碼",
    "auth.errConfirm": "兩次輸入的密碼不一致", "auth.errCompany": "請填寫企業代碼",
    "auth.registerFailed": "註冊申請提交失敗", "auth.registerSubmitted": "申請已提交，等待管理員審批後即可登入",
    "auth.loginFailed": "登入失敗", "auth.needLogin": "請先登入",
    "auth.phCompanyCode": "例如 uhv / acme", "auth.phDisplayName": "姓名或工作名",
    "auth.phConfirm": "再次輸入密碼", "auth.optionAdminRole": "由管理員指定",
    "auth.phDepartment": "方便管理員核實", "auth.phContact": "手機 / 郵箱",
    "auth.phReason": "簡述用途，供管理員審批",
    "company": "公司", "company.none": "未選擇公司", "logout": "登出",
    "loading": "正在連接資料庫…", "updating": "正在更新資料…",
    "ai.entry": "AI 操作入口", "ai.audit": "審計留痕", "ai.placeholder": "直接說要查什麼或做什麼",
    "ai.send": "交給 AI", "ai.reset": "重置", "ai.uploadPhoto": "照片", "ai.uploadFile": "文件",
    "ai.uploading": "正在上傳並分析…", "ai.analyzing": "AI 正在分析資料結構…", "ai.uploadDone": "分析完成",
    "ai.noUpload": "可上傳照片、Excel、CSV、JSON 或 SQLite，走資料中轉站分析流程。",
    "ai.importFlow": "DataHub 分析導入流程", "ai.failed": "分析失敗", "ai.processing": "AI 正在處理…",
    "ai.done": "AI 已完成。", "ai.error": "錯誤", "fields": "欄位", "rows": "行",
    "error.request": "請求失敗",
  },
  "zh-Hans": {
    "lang.name": "简", "lang.next": "繁",
    "nav.erp": "ERP 中枢", "nav.erp.short": "ERP",
    "nav.unified": "统一", "nav.unified.short": "统一",
    "nav.finance": "AI 财务", "nav.finance.short": "财务",
    "nav.overview": "仓储总览", "nav.overview.short": "仓储",
    "nav.collab": "AI 协作", "nav.collab.short": "协作",
    "nav.alerts": "智能预警", "nav.alerts.short": "预警",
    "auth.login": "登录", "auth.register": "申请注册",
    "auth.title": "ERP 工作台", "auth.registerTitle": "申请注册",
    "auth.loginSub": "登录后建立安全会话，下次可直接进入",
    "auth.registerSub": "提交后由企业管理员审批",
    "auth.account": "账号 / 邮箱", "auth.password": "密码",
    "auth.companyCode": "企业代码", "auth.displayName": "显示名称",
    "auth.confirmPassword": "确认密码", "auth.role": "期望角色",
    "auth.department": "部门 / 班组", "auth.contact": "联系方式",
    "auth.reason": "申请理由", "auth.submit": "提交申请",
    "auth.processing": "处理中...", "auth.foot": "公共设备使用后请登出；会话失效时系统会自动回到登录页。",
    "auth.errAccount": "请输入账号或邮箱", "auth.errPassword": "请输入密码",
    "auth.errConfirm": "两次输入的密码不一致", "auth.errCompany": "请填写企业代码",
    "auth.registerFailed": "注册申请提交失败", "auth.registerSubmitted": "申请已提交，等待管理员审批后即可登录",
    "auth.loginFailed": "登录失败", "auth.needLogin": "请先登录",
    "auth.phCompanyCode": "例如 uhv / acme", "auth.phDisplayName": "姓名或工作名",
    "auth.phConfirm": "再次输入密码", "auth.optionAdminRole": "由管理员指定",
    "auth.phDepartment": "方便管理员核实", "auth.phContact": "手机 / 邮箱",
    "auth.phReason": "简述用途，供管理员审批",
    "company": "公司", "company.none": "未选择公司", "logout": "登出",
    "loading": "正在连接数据库…", "updating": "正在更新数据…",
    "ai.entry": "AI 操作入口", "ai.audit": "审计留痕", "ai.placeholder": "直接说要查什么或做什么",
    "ai.send": "交给 AI", "ai.reset": "重置", "ai.uploadPhoto": "照片", "ai.uploadFile": "文件",
    "ai.uploading": "正在上传并分析…", "ai.analyzing": "AI 正在分析数据结构…", "ai.uploadDone": "分析完成",
    "ai.noUpload": "可上传照片、Excel、CSV、JSON 或 SQLite，走资料中转站分析流程。",
    "ai.importFlow": "DataHub 分析导入流程", "ai.failed": "分析失败", "ai.processing": "AI 正在处理…",
    "ai.done": "AI 已完成。", "ai.error": "错误", "fields": "字段", "rows": "行",
    "error.request": "请求失败",
  },
};

const MOBILE_PHRASES_HANS = {
  "ERP 工作台": "ERP 工作台", "ERP 中樞": "ERP 中枢", "統一": "统一", "AI 財務": "AI 财务",
  "倉儲總覽": "仓储总览", "AI 協作": "AI 协作", "智能預警": "智能预警",
  "暫無資料": "暂无资料", "暫無真實預警": "暂无真实预警", "暫無協作消息": "暂无协作消息",
  "低庫存物資": "低库存物资", "預警清單": "预警清单", "待處理事項": "待处理事项",
  "財務快捷": "财务快捷", "最新協作": "最新协作", "統一概覽": "统一概览",
  "風險信號": "风险信号", "跨模塊": "跨模块", "本期": "本期",
  "當前可用預算": "当前可用预算", "使用率": "使用率", "預算總額": "预算总额",
  "已佔用": "已占用", "進行工單": "进行工单", "採購申請": "采购申请",
  "未關閉預警": "未关闭预警", "需要處理": "需要处理", "庫存未掛預算": "库存未挂预算",
  "張單據待閉環": "张单据待闭环", "未指定供應商": "未指定供应商", "暫無高優先級待辦": "暂无高优先级待办",
  "ERP 可用": "ERP 可用", "本期利潤": "本期利润", "庫存件數": "库存件数",
  "待處理協作": "待处理协作", "營業收入": "营业收入", "應收賬款": "应收账款",
  "應付賬款": "应付账款", "付供應商款": "付供应商款", "收客戶款": "收客户款",
  "月末結賬": "月末结账", "執行": "执行", "物資種類": "物资种类",
  "低庫存": "低库存", "本期出入庫": "本期出入库", "活躍消息": "活跃消息",
  "共創計劃": "共创计划", "預警總數": "预警总数", "高風險": "高风险",
  "待處理": "待处理", "暫無低庫存": "暂无低库存", "預警": "预警", "錯誤": "错误", "失敗": "失败",
};
const mobileT = (key, lang = window.MOBILE_LANG || "zh-Hant") => (MOBILE_I18N[lang] || MOBILE_I18N["zh-Hant"])[key] || MOBILE_I18N["zh-Hant"][key] || key;
const mobilePhrase = (text, lang = window.MOBILE_LANG || "zh-Hant") => {
  if (text == null || lang !== "zh-Hans") return text;
  return Object.entries(MOBILE_PHRASES_HANS)
    .sort((a, b) => b[0].length - a[0].length)
    .reduce((value, [from, to]) => value.split(from).join(to), String(text));
};

window.authFetch = async (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  const token = mobileToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const tenant = mobileTenant();
  if (tenant) headers.set("X-Tenant-Slug", tenant);
  const res = await fetch(mobileApiUrl(url), { ...options, headers, credentials: options.credentials || "include" });
  if (res.status === 401) {
    mobileSetToken("");
    window.dispatchEvent(new Event("warehouse-auth-expired"));
  }
  return res;
};

const mobileJson = async (path, options) => {
  const res = await (window.authFetch || fetch)(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText || mobileT("error.request"));
  return data;
};

const mobileStreamJson = async (path, payload, onEvent) => {
  const res = await (window.authFetch || fetch)(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload || {}),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || res.statusText || mobileT("error.request"));
  }
  if (!res.body || !res.body.getReader) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (line) {
        try { onEvent(JSON.parse(line)); } catch (e) {}
      }
    }
  }
};

const MOBILE_NAV = [
  { id: "erp", label: "ERP 中樞", labelKey: "nav.erp", short: "ERP", shortKey: "nav.erp.short", icon: "layers" },
  { id: "unified", label: "統一", labelKey: "nav.unified", short: "統一", shortKey: "nav.unified.short", icon: "grid" },
  { id: "finance", label: "AI 財務", labelKey: "nav.finance", short: "財務", shortKey: "nav.finance.short", icon: "chart" },
  { id: "overview", label: "倉儲總覽", labelKey: "nav.overview", short: "倉儲", shortKey: "nav.overview.short", icon: "box" },
  { id: "collab", label: "AI 協作", labelKey: "nav.collab", short: "協作", shortKey: "nav.collab.short", icon: "sparkle" },
  { id: "alerts", label: "智能預警", labelKey: "nav.alerts", short: "預警", shortKey: "nav.alerts.short", icon: "alert" },
];

const MOBILE_BOTTOM = ["erp", "finance", "overview", "collab", "alerts"];
const navById = (id) => MOBILE_NAV.find(item => item.id === id) || MOBILE_NAV[0];

const MobileMetric = ({ label, value, tone, hint }) => (
  <div className="m-metric">
    <div className="m-metric-label">{mobilePhrase(label)}</div>
    <div className="m-metric-value" style={{ color: tone || "var(--m-ink)" }}>{value}</div>
    {hint && <div className="m-list-sub" style={{ whiteSpace: "normal" }}>{mobilePhrase(hint)}</div>}
  </div>
);

const MobileCardTitle = ({ title, right }) => (
  <div className="m-row" style={{ marginBottom: 10 }}>
    <div className="m-section-title">{mobilePhrase(title)}</div>
    {right}
  </div>
);

const MobileEmpty = ({ text = "暫無資料" }) => (
  <div className="m-card" style={{ color: "var(--m-muted)", fontSize: 13 }}>{mobilePhrase(text)}</div>
);

const MobileListRow = ({ icon = "layers", tone = "var(--m-blue)", title, sub, right }) => (
  <div className="m-list-row">
    <div className="m-list-icon" style={{ background: `${tone}14`, color: tone }}>
      <Icon name={icon} size={17}/>
    </div>
    <div className="m-list-main">
      <div className="m-list-title">{mobilePhrase(title || "—")}</div>
      <div className="m-list-sub">{mobilePhrase(sub || "—")}</div>
    </div>
    {right}
  </div>
);

const MobileLogin = ({ onLogin, lang, setLang }) => {
  const [mode, setMode] = useMobileState("login");
  const [username, setUsername] = useMobileState("");
  const [displayName, setDisplayName] = useMobileState("");
  const [companyCode, setCompanyCode] = useMobileState("");
  const [password, setPassword] = useMobileState("");
  const [confirmPassword, setConfirmPassword] = useMobileState("");
  const [department, setDepartment] = useMobileState("");
  const [contact, setContact] = useMobileState("");
  const [reason, setReason] = useMobileState("");
  const [requestedRoleId, setRequestedRoleId] = useMobileState("");
  const [roles, setRoles] = useMobileState([]);
  const [busy, setBusy] = useMobileState(false);
  const [err, setErr] = useMobileState("");
  const [notice, setNotice] = useMobileState("");
  const isRegister = mode === "register";

  useMobileEffect(() => {
    if (!isRegister) return;
    const code = companyCode.trim().toLowerCase();
    if (code.length < 3) {
      setRoles([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(mobileApiUrl(`/api/auth/roles?tenant=${encodeURIComponent(code)}`), { credentials: "include" })
        .then(res => res.json())
        .then(data => setRoles(data.roles || []))
        .catch(() => setRoles([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [isRegister, companyCode]);

  const switchMode = (nextMode) => {
    setMode(nextMode);
    setErr("");
    setNotice("");
    setPassword("");
    setConfirmPassword("");
    setRequestedRoleId("");
  };

  const submit = (event) => {
    event.preventDefault();
    if (busy) return;
    if (!username.trim()) {
      setErr(mobileT("auth.errAccount", lang));
      return;
    }
    if (!password) {
      setErr(mobileT("auth.errPassword", lang));
      return;
    }
    if (isRegister && password !== confirmPassword) {
      setErr(mobileT("auth.errConfirm", lang));
      return;
    }
    if (isRegister && !companyCode.trim()) {
      setErr(mobileT("auth.errCompany", lang));
      return;
    }
    setBusy(true);
    setErr("");
    setNotice("");

    if (isRegister) {
      fetch(mobileApiUrl("/api/auth/register"), {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: username.trim(),
          tenant_slug: companyCode.trim().toLowerCase(),
          display_name: displayName.trim() || username.trim(),
          password,
          department,
          contact,
          reason,
          requested_role_id: requestedRoleId || null,
        }),
      })
        .then(res => res.json().then(data => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) throw new Error(data.error || mobileT("auth.registerFailed", lang));
          switchMode("login");
          setNotice(data.message || mobileT("auth.registerSubmitted", lang));
        })
        .catch(error => setErr(error.message || String(error)))
        .finally(() => setBusy(false));
      return;
    }

    fetch(mobileApiUrl("/api/auth/login"), {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: username.trim(), password }),
    })
      .then(res => res.json().then(data => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || mobileT("auth.loginFailed", lang));
        mobileSetToken(data.token);
        const active = (data.companies || []).filter(c => c.status === "active");
        mobileSetTenant(data.default_tenant || active[0]?.slug || "");
        onLogin(data.user, active);
      })
      .catch(error => setErr(error.message || String(error)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="mobile-login">
      <form className={"mobile-login-card mobile-stack " + (isRegister ? "is-register" : "")} onSubmit={submit}>
        <div>
          <div className="m-row">
            <div className="mobile-kicker">MOBILE ERP</div>
            <button type="button" className="m-badge" onClick={() => setLang(lang === "zh-Hans" ? "zh-Hant" : "zh-Hans")}>{mobileT("lang.next", lang)}</button>
          </div>
          <div className="mobile-title">{isRegister ? mobileT("auth.registerTitle", lang) : mobileT("auth.title", lang)}</div>
          <div className="mobile-sub" style={{ whiteSpace: "normal" }}>{isRegister ? mobileT("auth.registerSub", lang) : mobileT("auth.loginSub", lang)}</div>
        </div>

        <div className="mobile-auth-tabs">
          <button type="button" className={mode === "login" ? "is-active" : ""} onClick={() => switchMode("login")}>{mobileT("auth.login", lang)}</button>
          <button type="button" className={mode === "register" ? "is-active" : ""} onClick={() => switchMode("register")}>{mobileT("auth.register", lang)}</button>
        </div>

        {notice && <div className="mobile-notice is-ok">{notice}</div>}
        {err && <div className="mobile-notice is-error">{err}</div>}

        {isRegister && (
          <>
            <label className="mobile-field-label">{mobileT("auth.companyCode", lang)}
              <input className="mobile-field" value={companyCode} onChange={e => { setCompanyCode(e.target.value); setRequestedRoleId(""); }} placeholder={mobileT("auth.phCompanyCode", lang)}/>
            </label>
            <label className="mobile-field-label">{mobileT("auth.displayName", lang)}
              <input className="mobile-field" value={displayName} onChange={e => setDisplayName(e.target.value)} placeholder={mobileT("auth.phDisplayName", lang)}/>
            </label>
          </>
        )}

        <label className="mobile-field-label">{mobileT("auth.account", lang)}
          <input className="mobile-field" value={username} onChange={e => setUsername(e.target.value)} placeholder={mobileT("auth.account", lang)} autoComplete="username"/>
        </label>
        <label className="mobile-field-label">{mobileT("auth.password", lang)}
          <PasswordInput className="mobile-field" value={password} onChange={e => setPassword(e.target.value)} placeholder={mobileT("auth.password", lang)} autoComplete={isRegister ? "new-password" : "current-password"}/>
        </label>

        {isRegister && (
          <>
            <label className="mobile-field-label">{mobileT("auth.confirmPassword", lang)}
              <PasswordInput className="mobile-field" value={confirmPassword} onChange={e => setConfirmPassword(e.target.value)} placeholder={mobileT("auth.phConfirm", lang)} autoComplete="new-password"/>
            </label>
            <label className="mobile-field-label">{mobileT("auth.role", lang)}
              <select className="mobile-field" value={requestedRoleId} onChange={e => setRequestedRoleId(e.target.value)}>
                <option value="">{mobileT("auth.optionAdminRole", lang)}</option>
                {roles.map(role => <option key={role.id} value={role.id}>{role.role_name}</option>)}
              </select>
            </label>
            <label className="mobile-field-label">{mobileT("auth.department", lang)}
              <input className="mobile-field" value={department} onChange={e => setDepartment(e.target.value)} placeholder={mobileT("auth.phDepartment", lang)}/>
            </label>
            <label className="mobile-field-label">{mobileT("auth.contact", lang)}
              <input className="mobile-field" value={contact} onChange={e => setContact(e.target.value)} placeholder={mobileT("auth.phContact", lang)}/>
            </label>
            <label className="mobile-field-label">{mobileT("auth.reason", lang)}
              <textarea className="mobile-field mobile-textarea" value={reason} onChange={e => setReason(e.target.value)} placeholder={mobileT("auth.phReason", lang)}/>
            </label>
          </>
        )}

        <button className="m-primary" disabled={busy} style={{ width: "100%" }}>
          <Icon name={isRegister ? "shield" : "forward"} size={15}/>{busy ? mobileT("auth.processing", lang) : isRegister ? mobileT("auth.submit", lang) : mobileT("auth.login", lang)}
        </button>
        <div className="mobile-auth-foot">{mobileT("auth.foot", lang)}</div>
      </form>
    </div>
  );
};

const MobileAgentBox = ({ seed, onRun, onUpload, uploadJob }) => {
  const [text, setText] = useMobileState(seed || "");
  const photoRef = React.useRef(null);
  const fileRef = React.useRef(null);
  return (
    <div className="m-card m-ai-box mobile-stack">
      <MobileCardTitle title={mobileT("ai.entry")} right={<span className="m-badge">{mobileT("ai.audit")}</span>}/>
      <textarea className="m-ai-input" value={text} onChange={e => setText(e.target.value)} placeholder={mobileT("ai.placeholder")}/>
      <input ref={photoRef} type="file" accept="image/*" capture="environment" style={{ display: "none" }}
        onChange={e => { const f = e.target.files && e.target.files[0]; e.target.value = ""; if (f) onUpload && onUpload(f); }}/>
      <input ref={fileRef} type="file" accept=".xlsx,.xlsm,.xls,.csv,.json,.db,.sqlite,.db3,.sqlite3,.jpg,.jpeg,.png,.webp,.bmp,.gif" style={{ display: "none" }}
        onChange={e => { const f = e.target.files && e.target.files[0]; e.target.value = ""; if (f) onUpload && onUpload(f); }}/>
      <div className="m-row">
        <button className="m-secondary" onClick={() => photoRef.current && photoRef.current.click()}><Icon name="inbound" size={14}/>{mobileT("ai.uploadPhoto")}</button>
        <button className="m-secondary" onClick={() => fileRef.current && fileRef.current.click()}><Icon name="box" size={14}/>{mobileT("ai.uploadFile")}</button>
      </div>
      <div className="m-row">
        <button className="m-secondary" onClick={() => setText(seed || "")}><Icon name="refresh" size={14}/>{mobileT("ai.reset")}</button>
        <button className="m-primary" onClick={() => onRun(text)} disabled={!text.trim()}><Icon name="sparkle" size={15}/>{mobileT("ai.send")}</button>
      </div>
      <MobileUploadStatus job={uploadJob}/>
    </div>
  );
};

const MobileUploadStatus = ({ job }) => {
  if (!job) return <div className="m-upload-hint">{mobileT("ai.noUpload")}</div>;
  return (
    <div className="m-upload-status">
      <div className="m-row">
        <strong>{job.filename || mobileT("ai.importFlow")}</strong>
        <span className={"m-upload-pill " + (job.status === "error" ? "is-error" : job.status === "done" ? "is-ok" : "")}>
          {job.status === "done" ? mobileT("ai.uploadDone") : job.status === "error" ? mobileT("ai.error") : mobileT("ai.analyzing")}
        </span>
      </div>
      {job.message && <div className="m-upload-line">{mobilePhrase(job.message)}</div>}
      {!!(job.datasets || []).length && (
        <div className="m-upload-datasets">
          {job.datasets.slice(0, 3).map((d, i) => (
            <div key={i}>
              <b>{d.name || d.source || `Dataset ${i + 1}`}</b>
              <span>{(d.fields || d.proposed?.fields || []).length} {mobileT("fields")} · {d.row_count || d.rows || 0} {mobileT("rows")}</span>
            </div>
          ))}
        </div>
      )}
      {!!(job.lines || []).length && <div className="m-upload-log">{job.lines.slice(-4).map((line, i) => <div key={i}>{mobilePhrase(line)}</div>)}</div>}
    </div>
  );
};

const PageMobileERP = ({ erp, runAgent, onUpload, uploadJob }) => {
  const s = erp.summary || {};
  const usage = s.budget_amount ? Math.round(((Number(s.budget_reserved || 0) + Number(s.budget_spent || 0)) / Number(s.budget_amount || 1)) * 100) : 0;
  const openPurchases = (erp.purchase_requests || []).filter(mobilePurchaseOpen);
  const openAlertCount = mobileCount(s.open_alerts);
  const unlinkedDocs = (erp.inventory_documents || []).filter(mobileBudgetUnlinkedOpen);
  const inventoryUnlinkedCount = unlinkedDocs.length;
  const pendingCount = openPurchases.length + openAlertCount + inventoryUnlinkedCount;
  return (
    <div className="mobile-stack">
      <div className="m-card is-hero mobile-stack">
        <div className="m-row">
          <div>
            <div style={{ fontSize: 12, opacity: .82, fontWeight: 800 }}>{mobileT("nav.erp")}</div>
            <div style={{ fontSize: 28, fontWeight: 950, lineHeight: 1.05 }}>{mobileMoney(s.budget_available)}</div>
            <div style={{ fontSize: 12.5, opacity: .84 }}>{mobilePhrase("當前可用預算")} · {mobilePhrase("使用率")} {usage}%</div>
          </div>
          <Icon name="layers" size={34} color="#fff"/>
        </div>
      </div>
      <div className="m-grid2">
        <MobileMetric label="預算總額" value={mobileMoney(s.budget_amount)}/>
        <MobileMetric label="已佔用" value={mobileMoney(s.budget_reserved)} tone="var(--m-orange)"/>
        <MobileMetric label="進行工單" value={mobileNumber(s.work_tasks_open)} tone="var(--m-blue)"/>
        <MobileMetric label="採購申請" value={mobileNumber(openPurchases.length)} tone="var(--m-green)"/>
      </div>
      <div className="m-card">
        <MobileCardTitle title="待處理事項" right={<span className="m-badge">{pendingCount}</span>}/>
        <div className="m-list">
          {openAlertCount > 0 && <MobileListRow icon="alert" tone="var(--m-red)" title="未關閉預警" sub={`${openAlertCount} 項需要處理`}/>}
          {inventoryUnlinkedCount > 0 && <MobileListRow icon="link" tone="var(--m-orange)" title="庫存未掛預算" sub={`${inventoryUnlinkedCount} 張單據待閉環`}/>}
          {openPurchases.slice(0, 3).map(p => <MobileListRow key={p.id} icon="inbound" tone="var(--m-green)" title={p.title} sub={`${p.request_no || "—"} · ${p.supplier_name || "未指定供應商"}`}/>)}
          {!pendingCount && <div className="m-list-sub">{mobilePhrase("暫無高優先級待辦")}</div>}
        </div>
      </div>
      <MobileAgentBox seed="請解釋 ERP 中樞目前狀態,並告訴我今天先處理什麼。" onRun={runAgent} onUpload={onUpload} uploadJob={uploadJob}/>
    </div>
  );
};

const PageMobileUnified = ({ erp, finance, collab, data }) => {
  const s = erp.summary || {};
  const inventory = data.INVENTORY || [];
  const alerts = data.ALERTS || [];
  const totalStock = inventory.reduce((sum, item) => sum + Number(item.stock || 0), 0);
  const incoming = (collab.messages || []).filter(m => m.is_incoming && ["sent", "read", "replied"].includes(m.status || ""));
  return (
    <div className="mobile-stack">
      <div className="m-card">
        <MobileCardTitle title="統一概覽" right={<span className="m-badge">{mobilePhrase("跨模塊")}</span>}/>
        <div className="m-grid2">
          <MobileMetric label="ERP 可用" value={mobileMoney(s.budget_available)} tone="var(--m-blue)"/>
          <MobileMetric label="本期利潤" value={mobileMoney(finance.profit)} tone={Number(finance.profit || 0) >= 0 ? "var(--m-green)" : "var(--m-red)"}/>
          <MobileMetric label="庫存件數" value={mobileNumber(totalStock)}/>
          <MobileMetric label="待處理協作" value={mobileNumber(incoming.length)} tone="var(--m-purple)"/>
        </div>
      </div>
      <div className="m-card">
        <MobileCardTitle title="風險信號" right={<span className="m-badge">{alerts.length}</span>}/>
        <div className="m-list">
          {alerts.slice(0, 4).map(a => <MobileListRow key={a.id} icon="alert" tone={a.level === "red" ? "var(--m-red)" : "var(--m-orange)"} title={a.item} sub={a.suggest || a.type}/>)}
          {!alerts.length && <div className="m-list-sub">{mobilePhrase("暫無真實預警")}</div>}
        </div>
      </div>
    </div>
  );
};

const BAR_TONES = ["var(--m-blue)", "var(--m-green)", "var(--m-purple)", "var(--m-orange)", "var(--m-red)", "#0ea5e9", "#14b8a6", "#f59e0b"];

const MobileBar = ({ label, amount, pct, tone }) => (
  <div style={{ marginBottom: 9 }}>
    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, marginBottom: 3, gap: 8 }}>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label || "—"}</span>
      <span style={{ opacity: 0.75, flexShrink: 0 }}>{mobileMoney(amount)} · {pct}%</span>
    </div>
    <div style={{ height: 8, borderRadius: 6, background: "rgba(148,163,184,0.18)", overflow: "hidden" }}>
      <div style={{ height: "100%", width: `${Math.max(2, Math.min(100, Number(pct) || 0))}%`, background: tone, borderRadius: 6 }}/>
    </div>
  </div>
);

const PageMobileFinance = ({ finance, runAgent, onUpload, uploadJob }) => {
  const L = finance.ledger || {};
  const cats = L.by_category || [];
  const payers = L.by_payer || [];
  const recent = L.recent || [];
  const balances = L.balances || [];
  const settlement = L.settlement || [];
  const hasData = (L.expense_count || 0) > 0 || balances.length > 0;
  const netTone = (n) => (n > 0 ? "var(--m-green)" : n < 0 ? "var(--m-red)" : "#94a3b8");
  return (
    <div className="mobile-stack">
      <div className="m-card">
        <MobileCardTitle title={mobilePhrase("賬本")} right={<span className="m-badge">{L.period || mobilePhrase("全部")}</span>}/>
        <div className="m-grid2">
          <MobileMetric label={mobilePhrase("總支出")} value={mobileMoney(L.total_spent || 0)} tone="var(--m-blue)"/>
          <MobileMetric label={mobilePhrase("筆數")} value={mobileNumber(L.expense_count || 0)}/>
          <MobileMetric label={mobilePhrase("應收")} value={mobileMoney(finance.ar)} tone="var(--m-purple)"/>
          <MobileMetric label={mobilePhrase("應付")} value={mobileMoney(finance.ap)} tone="var(--m-orange)"/>
        </div>
      </div>

      {!hasData && (
        <div className="m-card">
          <div className="m-list-sub">{mobilePhrase("還沒有記賬數據。用下面的 AI 入賬:拍一張賬單照片,或直接說「阿迪絲墊付 740 高鐵票,我和她平攤」,秘書會幫你記進賬。")}</div>
        </div>
      )}

      {!!cats.length && (
        <div className="m-card">
          <MobileCardTitle title={mobilePhrase("花在什麼上")} right={<span className="m-badge">{mobilePhrase("占比")}</span>}/>
          <div>{cats.slice(0, 8).map((c, i) => <MobileBar key={i} label={c.name} amount={c.amount} pct={c.pct} tone={BAR_TONES[i % BAR_TONES.length]}/>)}</div>
        </div>
      )}

      {!!payers.length && (
        <div className="m-card">
          <MobileCardTitle title={mobilePhrase("誰花的")} right={<span className="m-badge">{mobilePhrase("墊付占比")}</span>}/>
          <div>{payers.slice(0, 8).map((p, i) => <MobileBar key={i} label={p.name} amount={p.amount} pct={p.pct} tone="var(--m-blue)"/>)}</div>
        </div>
      )}

      {balances.length > 0 && (
        <div className="m-card">
          <MobileCardTitle title={mobilePhrase("往來結算")} right={<span className="m-badge">{settlement.length ? `${settlement.length} ${mobilePhrase("筆擺平")}` : mobilePhrase("已平")}</span>}/>
          <div className="m-list">
            {balances.map((b, i) => (
              <MobileListRow key={i} icon={b.net >= 0 ? "forward" : "inbound"} tone={netTone(b.net)}
                title={b.party}
                sub={`${mobilePhrase("墊付")} ${mobileMoney(b.paid_for_group)} · ${mobilePhrase("分攤")} ${mobileMoney(b.your_share)}`}
                right={<b style={{ color: netTone(b.net) }}>{b.net > 0 ? mobilePhrase("應收") + " " : b.net < 0 ? mobilePhrase("應付") + " " : ""}{mobileMoney(Math.abs(b.net))}</b>}/>
            ))}
          </div>
          {!!settlement.length && (
            <div style={{ marginTop: 10, paddingTop: 10, borderTop: "1px solid rgba(148,163,184,0.2)" }}>
              <div className="m-list-sub" style={{ marginBottom: 6 }}>{mobilePhrase("最優結算")}（{mobilePhrase("最少")} {settlement.length} {mobilePhrase("筆")}）:</div>
              {settlement.map((t, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "5px 0", fontSize: 14 }}>
                  <span style={{ color: "var(--m-red)" }}>{t.from}</span>
                  <Icon name="forward" size={13}/>
                  <span style={{ color: "var(--m-green)" }}>{t.to}</span>
                  <b style={{ marginLeft: "auto" }}>{mobileMoney(t.amount)}</b>
                </div>
              ))}
              <button className="m-secondary" style={{ width: "100%", marginTop: 8 }}
                onClick={() => runAgent("請按最優結算方案把這幾筆轉賬登記平賬（fin settle-record），登記前把每筆複述給我確認。")}>
                <Icon name="sparkle" size={14}/>{mobilePhrase("讓秘書登記結算")}
              </button>
            </div>
          )}
          {Math.abs(L.imbalance || 0) >= 0.01 && (
            <div className="m-list-sub" style={{ marginTop: 8, color: "var(--m-orange)" }}>
              ⚠ {mobilePhrase("淨額未平")} {mobileMoney(L.imbalance)}：{mobilePhrase("可能有開銷沒記分攤,核對一下。")}
            </div>
          )}
        </div>
      )}

      {!!recent.length && (
        <div className="m-card">
          <MobileCardTitle title={mobilePhrase("消費明細")} right={<span className="m-badge">{recent.length}</span>}/>
          <div className="m-list">
            {recent.map((r, i) => (
              <div key={i} style={{ padding: "8px 0", borderBottom: i < recent.length - 1 ? "1px solid rgba(148,163,184,0.12)" : "none" }}>
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                  <span style={{ fontWeight: 600 }}>{r.item}</span>
                  <b style={{ flexShrink: 0 }}>{mobileMoney(r.amount)}</b>
                </div>
                <div style={{ fontSize: 12, opacity: 0.7, marginTop: 2 }}>
                  {r.payer} {mobilePhrase("墊付")} · {r.event_date}
                  {!!(r.split || []).length && <span> · {r.split.map(s => `${s.name} ${mobileMoney(s.amount)}`).join(" / ")}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="m-card">
        <MobileCardTitle title={mobilePhrase("公司財務")} right={<span className="m-badge">{finance.period || mobilePhrase("本期")}</span>}/>
        <div className="m-grid2">
          <MobileMetric label={mobilePhrase("本期利潤")} value={mobileMoney(finance.profit)} tone={Number(finance.profit || 0) >= 0 ? "var(--m-green)" : "var(--m-red)"}/>
          <MobileMetric label={mobilePhrase("營業收入")} value={mobileMoney(finance.revenue)} tone="var(--m-blue)"/>
        </div>
      </div>

      <MobileAgentBox seed="拍張賬單照片或直接告訴我這筆花費,例如「阿迪絲墊付 740 元高鐵票,我、她、蔡培元三人平攤」,我幫你記進賬。" onRun={runAgent} onUpload={onUpload} uploadJob={uploadJob}/>
    </div>
  );
};

const PageMobileOverview = ({ data }) => {
  const inventory = data.INVENTORY || [];
  const inbound = data.INBOUND || [];
  const outbound = data.OUTBOUND || [];
  const low = inventory.filter(i => Number(i.stock || 0) < Number(i.safe || 0));
  const totalStock = inventory.reduce((sum, item) => sum + Number(item.stock || 0), 0);
  return (
    <div className="mobile-stack">
      <div className="m-card">
        <MobileCardTitle title="倉儲總覽" right={<span className="m-badge">{data.WAREHOUSES?.[0] || "—"}</span>}/>
        <div className="m-grid2">
          <MobileMetric label="物資種類" value={mobileNumber(inventory.length)} tone="var(--m-blue)"/>
          <MobileMetric label="庫存件數" value={mobileNumber(totalStock)} tone="var(--m-green)"/>
          <MobileMetric label="低庫存" value={mobileNumber(low.length)} tone={low.length ? "var(--m-red)" : "var(--m-green)"}/>
          <MobileMetric label="本期出入庫" value={mobileNumber(inbound.length + outbound.length)}/>
        </div>
      </div>
      <div className="m-card">
        <MobileCardTitle title="低庫存物資" right={<span className="m-badge">{low.length}</span>}/>
        <div className="m-list">
          {low.slice(0, 5).map(item => <MobileListRow key={item.id} icon="box" tone="var(--m-red)" title={item.name} sub={`${item.code} · ${item.wh} · ${item.loc}`} right={<span className="m-badge">{item.stock}/{item.safe}</span>}/>)}
          {!low.length && <div className="m-list-sub">{mobilePhrase("暫無低庫存")}</div>}
        </div>
      </div>
    </div>
  );
};

const PageMobileCollab = ({ collab, runAgent, onUpload, uploadJob }) => {
  const messages = collab.messages || [];
  const ideas = collab.ideas || [];
  return (
    <div className="mobile-stack">
      <div className="m-card">
        <MobileCardTitle title="AI 協作" right={<span className="m-badge">{messages.length}</span>}/>
        <div className="m-grid2">
          <MobileMetric label="活躍消息" value={mobileNumber(messages.length)} tone="var(--m-purple)"/>
          <MobileMetric label="共創計劃" value={mobileNumber(ideas.length)} tone="var(--m-blue)"/>
        </div>
      </div>
      <div className="m-card">
        <MobileCardTitle title="最新協作"/>
        <div className="m-list">
          {messages.slice(0, 5).map(m => <MobileListRow key={m.id} icon="sparkle" tone={m.priority === "urgent" ? "var(--m-red)" : "var(--m-purple)"} title={m.assistant_text || m.original_text} sub={`${m.sender_name || "—"} → ${m.recipient_name || "—"} · ${m.status || "—"}`}/>)}
          {!messages.length && <div className="m-list-sub">{mobilePhrase("暫無協作消息")}</div>}
        </div>
      </div>
      <MobileAgentBox seed="幫我整理目前需要跟進的協作消息和任務。" onRun={runAgent} onUpload={onUpload} uploadJob={uploadJob}/>
    </div>
  );
};

const PageMobileAlerts = ({ data }) => {
  const alerts = data.ALERTS || [];
  const red = alerts.filter(a => a.level === "red").length;
  const orange = alerts.filter(a => a.level === "orange").length;
  return (
    <div className="mobile-stack">
      <div className="m-card">
        <MobileCardTitle title="智能預警" right={<span className="m-badge">{alerts.length}</span>}/>
        <div className="m-grid2">
          <MobileMetric label="預警總數" value={mobileNumber(alerts.length)} tone="var(--m-orange)"/>
          <MobileMetric label="高風險" value={mobileNumber(red)} tone={red ? "var(--m-red)" : "var(--m-green)"}/>
          <MobileMetric label="低庫存" value={mobileNumber(orange)} tone="var(--m-orange)"/>
          <MobileMetric label="待處理" value={mobileNumber(alerts.length)} />
        </div>
      </div>
      <div className="m-card">
        <MobileCardTitle title="預警清單"/>
        <div className="m-list">
          {alerts.slice(0, 8).map(a => (
            <MobileListRow key={a.id} icon="alert" tone={a.level === "red" ? "var(--m-red)" : a.level === "orange" ? "var(--m-orange)" : "var(--m-blue)"}
              title={a.item} sub={a.suggest || `${a.type || "預警"} · ${a.scope || "—"}`} right={<span className="m-badge">{a.stock ?? "—"}/{a.safe ?? "—"}</span>}/>
          ))}
          {!alerts.length && <div className="m-list-sub">{mobilePhrase("暫無真實預警")}</div>}
        </div>
      </div>
    </div>
  );
};

const MobileApp = () => {
  const [lang, setLangState] = useMobileState(mobileLang());
  const [authChecked, setAuthChecked] = useMobileState(false);
  const [user, setUser] = useMobileState(null);
  const [companies, setCompanies] = useMobileState([]);
  const [tenant, setTenant] = useMobileState(mobileTenant());
  const [active, setActive] = useMobileState("erp");
  const [data, setData] = useMobileState(MOBILE_EMPTY_BOOTSTRAP);
  const [erp, setErp] = useMobileState({});
  const [finance, setFinance] = useMobileState({});
  const [collab, setCollab] = useMobileState({ messages: [], ideas: [] });
  const [busy, setBusy] = useMobileState(false);
  const [toast, setToast] = useMobileState("");
  const [uploadJob, setUploadJob] = useMobileState(null);
  window.MOBILE_LANG = lang;

  const setLang = (nextLang) => {
    const safe = nextLang === "zh-Hans" ? "zh-Hans" : "zh-Hant";
    mobileSetLang(safe);
    setLangState(safe);
  };

  const loadFinance = async () => {
    const d = new Date();
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    const [income, ap, ar, ledger] = await Promise.all([
      mobileJson(`/api/erp/gl/income?period=${encodeURIComponent(period)}`),
      mobileJson("/api/erp/gl/ap"),
      mobileJson("/api/erp/gl/ar"),
      mobileJson("/api/erp/finance/ledger-summary?limit=20").catch(() => ({})),
    ]);
    return {
      period,
      profit: income.profit || 0,
      revenue: income.revenue || 0,
      ap: ap.total_outstanding || 0,
      ar: ar.total_outstanding || 0,
      ledger: ledger || {},
    };
  };

  const loadAll = async () => {
    setBusy(true);
    setToast("");
    try {
      const [bootstrap, erpData, finData, messages, ideas] = await Promise.all([
        mobileJson("/api/bootstrap"),
        mobileJson("/api/erp/overview").catch(() => ({})),
        loadFinance().catch(() => ({})),
        mobileJson("/api/collab/messages?box=all&status=active&limit=30").catch(() => ({ messages: [] })),
        mobileJson("/api/collab/ideas?scope=all&limit=20").catch(() => ({ ideas: [] })),
      ]);
      mobileApplyBootstrap(bootstrap);
      setData({ ...MOBILE_EMPTY_BOOTSTRAP, ...bootstrap });
      setErp(erpData);
      setFinance(finData);
      setCollab({ messages: messages.messages || [], ideas: ideas.ideas || [] });
    } catch (error) {
      setToast(error.message || String(error));
    } finally {
      setBusy(false);
      setAuthChecked(true);
    }
  };

  const checkAuth = async () => {
    try {
      let status = await mobileJson("/api/auth/me");
      if ((!status.authenticated || !status.user) && mobileToken()) {
        mobileSetToken("");
        status = await mobileJson("/api/auth/me");
      }
      if (!status.authenticated || !status.user) {
        mobileSetToken("");
        setUser(null);
        setCompanies([]);
        setTenant("");
        setAuthChecked(true);
        return;
      }
      setUser(status.user);
      setCompanies(status.companies || []);
      const activeCompanies = (status.companies || []).filter(c => c.status === "active");
      const nextTenant = mobileTenant() || status.tenant || activeCompanies[0]?.slug || "";
      if (nextTenant) {
        mobileSetTenant(nextTenant);
        setTenant(nextTenant);
      }
      await loadAll();
    } catch {
      mobileSetToken("");
      setUser(null);
      setTenant("");
      setAuthChecked(true);
    }
  };

  useMobileEffect(() => { checkAuth(); }, []);
  useMobileEffect(() => { document.documentElement.lang = lang; }, [lang]);

  const finishLogin = (nextUser, nextCompanies) => {
    setUser(nextUser);
    setCompanies(nextCompanies || []);
    setTenant(mobileTenant());
    loadAll();
  };

  const switchCompany = async (slug) => {
    if (!slug || slug === tenant || busy) return;
    const prevTenant = tenant;
    mobileSetTenant(slug);
    setTenant(slug);
    setActive("erp");
    setBusy(true);
    setToast("");
    try {
      const status = await mobileJson("/api/auth/me");
      if (!status.authenticated || !status.user) throw new Error(mobileT("auth.needLogin", lang));
      setUser(status.user);
      setCompanies(status.companies || []);
      await loadAll();
      setToast(`${mobileT("company", lang)}: ${(status.companies || []).find(c => c.slug === slug)?.name || slug}`);
    } catch (error) {
      mobileSetTenant(prevTenant);
      setTenant(prevTenant);
      setToast(error.message || String(error));
    } finally {
      setBusy(false);
    }
  };

  const logout = () => {
    window.authFetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    mobileSetToken("");
    mobileSetTenant("");
    setUser(null);
    setTenant("");
    setUploadJob(null);
    mobileApplyBootstrap(MOBILE_EMPTY_BOOTSTRAP);
  };

  const uploadDataFile = async (file) => {
    if (!file || busy) return;
    setBusy(true);
    setActive("collab");
    setToast(mobileT("ai.uploading", lang));
    setUploadJob({ filename: file.name, status: "uploading", lines: [mobileT("ai.uploading", lang)] });
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await window.authFetch("/api/datahub/analyze", { method: "POST", body: fd });
      const analyzed = await res.json().catch(() => ({}));
      if (!res.ok || !analyzed.ok) throw new Error(analyzed.error || mobileT("ai.failed", lang));
      setUploadJob({
        filename: analyzed.filename || file.name,
        status: "analyzing",
        message: analyzed.vision_note || `${analyzed.kind || "file"} · ${(analyzed.datasets || []).length} datasets`,
        datasets: analyzed.datasets || [],
        lines: [mobileT("ai.uploadDone", lang), mobileT("ai.analyzing", lang)],
      });
      await mobileStreamJson("/api/datahub/agent/stream", { job_id: analyzed.job_id }, (event) => {
        if (event.event === "step" && event.tool) {
          setUploadJob(prev => ({ ...(prev || {}), lines: [...((prev && prev.lines) || []), event.tool] }));
        }
        if (event.event === "final") {
          setUploadJob(prev => ({
            ...(prev || {}),
            status: "done",
            message: event.message || prev?.message || mobileT("ai.uploadDone", lang),
            proposal: event.proposal || null,
            lines: [...((prev && prev.lines) || []), mobileT("ai.uploadDone", lang)],
          }));
        }
        if (event.event === "error") {
          setUploadJob(prev => ({ ...(prev || {}), status: "error", message: event.error || mobileT("ai.failed", lang) }));
        }
      });
      setToast(mobileT("ai.uploadDone", lang));
    } catch (error) {
      setUploadJob(prev => ({ ...(prev || { filename: file.name }), status: "error", message: error.message || String(error) }));
      setToast(error.message || String(error));
    } finally {
      setBusy(false);
    }
  };

  const runAgent = async (text) => {
    const content = (text || "").trim();
    if (!content) return;
    setToast(mobileT("ai.processing", lang));
    try {
      const result = await mobileJson("/api/agent/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: content, page: active }),
      });
      setToast(result.message || result.answer || result.final_message || mobileT("ai.done", lang));
      await loadAll();
    } catch (error) {
      setToast(error.message || String(error));
    }
  };

  if (!authChecked) {
    return <div className="mobile-root"><div className="mobile-login"><div className="mobile-login-card">{mobileT("loading", lang)}</div></div></div>;
  }
  if (!user) return <div className="mobile-root"><MobileLogin onLogin={finishLogin} lang={lang} setLang={setLang}/></div>;

  const current = navById(active);
  const page = active === "erp" ? <PageMobileERP erp={erp} runAgent={runAgent} onUpload={uploadDataFile} uploadJob={uploadJob}/>
    : active === "unified" ? <PageMobileUnified erp={erp} finance={finance} collab={collab} data={data}/>
    : active === "finance" ? <PageMobileFinance finance={finance} runAgent={runAgent} onUpload={uploadDataFile} uploadJob={uploadJob}/>
    : active === "overview" ? <PageMobileOverview data={data}/>
    : active === "collab" ? <PageMobileCollab collab={collab} runAgent={runAgent} onUpload={uploadDataFile} uploadJob={uploadJob}/>
    : active === "alerts" ? <PageMobileAlerts data={data}/>
    : <MobileEmpty/>;

  return (
    <div className="mobile-root">
      <div className="mobile-shell">
        <header className="mobile-top">
          <div className="mobile-brand">
            <div className="mobile-kicker">{mobileT("auth.title", lang)}</div>
            <div className="mobile-title">{mobileT(current.labelKey, lang)}</div>
            <label className="mobile-company-line">
              <span>{mobileT("company", lang)}</span>
              <select value={tenant || ""} onChange={(e) => switchCompany(e.target.value)} disabled={busy || companies.length <= 1}>
                {!companies.length && <option value="">{mobileT("company.none", lang)}</option>}
                {companies.map(c => <option key={c.slug} value={c.slug}>{c.name || c.slug}</option>)}
              </select>
            </label>
          </div>
          <div className="mobile-top-actions">
            <button className="mobile-icon-btn is-text" onClick={() => setLang(lang === "zh-Hans" ? "zh-Hant" : "zh-Hans")} title="Language">{mobileT("lang.next", lang)}</button>
            <button className="mobile-icon-btn" onClick={logout} title={mobileT("logout", lang)}><Icon name="x" size={17}/></button>
          </div>
        </header>

        <nav className="mobile-tabs">
          {MOBILE_NAV.map(item => (
            <button key={item.id} className={"mobile-tab " + (active === item.id ? "is-active" : "")} onClick={() => setActive(item.id)}>
              <Icon name={item.icon} size={14}/>{mobileT(item.labelKey, lang)}
            </button>
          ))}
        </nav>

        {toast && <div className="m-card" style={{ padding: 10, fontSize: 12.5, color: /失敗|失败|錯|错|error/i.test(toast) ? "var(--m-red)" : "var(--m-blue)" }}>{mobilePhrase(toast)}</div>}

        <main className="mobile-page">
          {busy && <div className="m-card" style={{ fontSize: 12.5, color: "var(--m-muted)", marginBottom: 10 }}>{mobileT("updating", lang)}</div>}
          {page}
        </main>

        <nav className="mobile-bottom">
          {MOBILE_BOTTOM.map(id => {
            const item = navById(id);
            return (
              <button key={id} className={active === id ? "is-active" : ""} onClick={() => setActive(id)}>
                <Icon name={item.icon} size={17}/><span>{mobileT(item.shortKey, lang)}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<MobileApp/>);
