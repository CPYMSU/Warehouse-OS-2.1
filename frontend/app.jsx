/* ============================================================
   主 App — 路由 + 殼層
   ============================================================ */
const { useEffect, useState } = React;

const APP_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const AUTH_TOKEN_KEY = "warehouse_auth_token";
const EMPTY_BOOTSTRAP = {
  NAV_CONFIG: { items: {} }, CUSTOM_MODULES: [],
  WAREHOUSES: ["—"], CATEGORIES: [], LEDGER_CATEGORIES: [], INVENTORY: [], ALERTS: [], INBOUND: [],
  OUTBOUND: [], FAULT_TYPES: [], STOCKTAKE: [], STOCKTAKE_DIFF: [], ZONES: [],
  AI_TASKS: [], AI_LOG: [], PEOPLE: [], ROLES: [], FLOW: { title: "—", steps: [] },
};

const applyBootstrap = (payload) => {
  Object.assign(window, { ...EMPTY_BOOTSTRAP, ...(payload || {}) });
};

const TENANT_KEY = "warehouse_current_tenant";
const authToken = () => window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
const setAuthToken = (token) => {
  if (token) window.localStorage.setItem(AUTH_TOKEN_KEY, token);
  else window.localStorage.removeItem(AUTH_TOKEN_KEY);
};
const currentTenantSlug = () => window.localStorage.getItem(TENANT_KEY) || "";
const setCurrentTenantSlug = (slug) => {
  if (slug) window.localStorage.setItem(TENANT_KEY, slug);
  else window.localStorage.removeItem(TENANT_KEY);
};
const makeApiUrl = (url) => /^https?:\/\//.test(url) ? url : APP_API_BASE + url;
const maxRoleLevel = (user) => Math.max(0, ...((user && user.roles) || []).map((r) => Number(r.level) || 0));

window.authFetch = async (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  const token = authToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  // Model B:帶上當前公司,後端據此解析到對應公司的庫與權限
  const slug = currentTenantSlug();
  if (slug) headers.set("X-Tenant-Slug", slug);
  const res = await fetch(makeApiUrl(url), { ...options, headers });
  if (res.status === 401) {
    setAuthToken("");
    window.dispatchEvent(new Event("warehouse-auth-expired"));
  }
  return res;
};

const PAGES = {
  erp: "PageERP", finance: "PageFinance", overview: "PageOverview", inventory: "PageInventory", inbound: "PageInbound",
  outbound: "PageOutbound", alerts: "PageAlerts", stocktake: "PageStocktake",
  map: "PageMap", wh_gis: "PageWarehouseGIS", ai: "PageAI", collab: "PageCollab", perms: "PagePerms",
  reports: "PageReports", logs: "PageAuditLogs", settings: "PageSettings", terminal: "PageTerminal", shield: "PageShield",
  companies: "PageCompanies", datahub: "PageDataHub", procurement: "PageProcurement", legal: "PageLegal",
  assets: "PageAssets",
};

const Stub = ({ title }) => (
  <div className="col center" style={{ height: "60vh", gap: 14 }}>
    <div style={{ width: 64, height: 64, borderRadius: 18, background: "var(--grad-soft)", display: "grid", placeItems: "center" }}><Icon name="layers" size={28} color="var(--blue)"/></div>
    <div style={{ fontSize: 18, fontWeight: 700 }}>{title}</div>
    <div className="muted" style={{ fontSize: 13 }}>模塊建設中…</div>
  </div>
);

const LoginScreen = ({ needsSetup, onLogin, error }) => {
  // mode: needsSetup 時固定為初始化；否則在 login / register 間切換
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [companyCode, setCompanyCode] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [department, setDepartment] = useState("");
  const [contact, setContact] = useState("");
  const [reason, setReason] = useState("");
  const [requestedRoleId, setRequestedRoleId] = useState("");
  const [roles, setRoles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [localError, setLocalError] = useState("");
  const [notice, setNotice] = useState("");

  const isRegister = !needsSetup && mode === "register";

  // 註冊時按企業代碼載入該公司的可選角色（公開端點，不需登入）
  useEffect(() => {
    if (!isRegister) return;
    const code = companyCode.trim().toLowerCase();
    if (code.length < 3) {
      setRoles([]);
      return;
    }
    const timer = setTimeout(() => {
      fetch(`${APP_API_BASE}/api/auth/roles?tenant=${encodeURIComponent(code)}`)
        .then((res) => res.json())
        .then((data) => setRoles(data.roles || []))
        .catch(() => setRoles([]));
    }, 250);
    return () => clearTimeout(timer);
  }, [isRegister, companyCode]);

  const switchMode = (next) => {
    setMode(next);
    setLocalError("");
    setNotice("");
    setPassword("");
    setConfirmPassword("");
    if (next === "register") {
      setUsername("");
      setCompanyCode("");
    } else {
      setUsername("");
    }
  };

  const submit = (event) => {
    event.preventDefault();
    if (busy) return;
    setLocalError("");
    setNotice("");
    if ((needsSetup || isRegister) && password !== confirmPassword) {
      setLocalError("兩次輸入的密碼不一致");
      return;
    }
    if (isRegister && !companyCode.trim()) {
      setLocalError("請填寫企業代碼");
      return;
    }
    setBusy(true);

    if (isRegister) {
      fetch(`${APP_API_BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username,
          tenant_slug: companyCode.trim().toLowerCase(),
          display_name: displayName || username,
          password,
          department,
          contact,
          reason,
          requested_role_id: requestedRoleId || null,
        }),
      })
        .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
        .then(({ ok, data }) => {
          if (!ok) throw new Error(data.error || "註冊申請提交失敗");
          switchMode("login");
          setNotice(data.message || "申請已提交，等待管理員審批後即可登入");
        })
        .catch((err) => setLocalError(err.message || String(err)))
        .finally(() => setBusy(false));
      return;
    }

    fetch(`${APP_API_BASE}${needsSetup ? "/api/auth/bootstrap" : "/api/auth/login"}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(needsSetup ? { username, display_name: displayName || username, password } : { username, password }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || (needsSetup ? "初始化失敗" : "登入失敗"));
        setAuthToken(data.token);
        // Model B:記住默認公司(全局登入返回 default_tenant + companies)
        const companies = data.companies || [];
        const active = companies.filter((c) => c.status === "active");
        setCurrentTenantSlug(data.default_tenant || (active[0] && active[0].slug) || "");
        onLogin(data.user, active, !!data.is_platform_owner, !!data.can_apply_company);
      })
      .catch((err) => setLocalError(err.message || String(err)))
      .finally(() => setBusy(false));
  };

  const title = needsSetup ? "初始化管理員" : isRegister ? "申請註冊帳號" : "系統登入";
  const subtitle = needsSetup ? "建立第一個超級管理員賬號" : isRegister ? "提交後由管理員審批，通過後即可登入" : "按人員角色控制資料讀寫權限";
  const submitText = needsSetup ? "建立管理員" : isRegister ? "提交申請" : "登入";
  const isMobilePlatform = !!window.WAREHOUSE_MOBILE_PLATFORM;
  const screenStyle = isMobilePlatform ? undefined : { height: "100vh", overflowY: "auto", display: "flex", justifyContent: "center", background: "var(--bg)", padding: 24 };
  const cardStyle = isMobilePlatform ? undefined : { width: "min(440px, 100%)", padding: 24, margin: "auto" };

  return (
    <div className="mobile-login-screen" style={screenStyle}>
      <div className="mobile-login-frame">
        <section className="mobile-login-identity" aria-label="WAREHOUSE OS 2.0">
          <div className="mobile-login-logo" style={{ overflow: "hidden" }}><img src="v2/brand/bonfire-platform-mark.png" width="40" height="40" alt=""/></div>
          <div className="mobile-login-brand-copy">
            <div className="mobile-login-product">WAREHOUSE OS 2.0</div>
            <div className="mobile-login-product-sub">BONFIRE WORKSHOP · PLATFORM</div>
          </div>
        </section>

        <form onSubmit={submit} className={"card col gap-16 mobile-login-card" + (isRegister ? " is-register" : "")} style={cardStyle}>
          <div className="row gap-12 mobile-login-card-head">
            <div className="mobile-login-card-icon" style={{ width: 44, height: 44, borderRadius: 12, background: "var(--grad)", color: "#fff", display: "grid", placeItems: "center" }}>
              <Icon name={isRegister ? "user" : "shield"} size={22}/>
            </div>
            <div className="col gap-3 mobile-login-title-wrap">
              <div className="mobile-login-title">{title}</div>
              <div className="muted mobile-login-subtitle">{subtitle}</div>
            </div>
          </div>

          {!needsSetup && (
            <div className="mobile-login-mode">
              <button type="button" className={!isRegister ? "is-active" : ""} onClick={() => switchMode("login")}>登入</button>
              <button type="button" className={isRegister ? "is-active" : ""} onClick={() => switchMode("register")}>申請註冊</button>
            </div>
          )}

          <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
            帳號
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" autoFocus={!isMobilePlatform} placeholder="請輸入帳號"/>
          </label>
          {(needsSetup || isRegister) && (
            <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
              顯示名稱
              <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)} autoComplete="name" placeholder="姓名或工作名"/>
            </label>
          )}
          {isRegister && (
            <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
              企業代碼
              <input className="input" value={companyCode} onChange={(e) => { setCompanyCode(e.target.value); setRequestedRoleId(""); }} autoComplete="organization" placeholder="向公司管理員索取，例如 acme"/>
            </label>
          )}
          <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
            密碼
            <PasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={needsSetup || isRegister ? "new-password" : "current-password"} placeholder="請輸入密碼"/>
          </label>
          {(needsSetup || isRegister) && (
            <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
              確認密碼
              <PasswordInput value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} autoComplete="new-password" placeholder="再次輸入密碼"/>
            </label>
          )}
          {isRegister && (
            <>
              <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
                期望角色
                <select className="input" value={requestedRoleId} onChange={(e) => setRequestedRoleId(e.target.value)}>
                  <option value="">（由管理員指定）</option>
                  {roles.map((r) => (
                    <option key={r.id} value={r.id}>{r.role_name}</option>
                  ))}
                </select>
              </label>
              <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
                部門 / 班組
                <input className="input" value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="例如：高空檢修班"/>
              </label>
              <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
                聯繫方式（手機 / 郵箱）
                <input className="input" value={contact} onChange={(e) => setContact(e.target.value)} placeholder="方便管理員核實身份"/>
              </label>
              <label className="col gap-6 mobile-login-field" style={{ fontSize: 12.5, fontWeight: 700 }}>
                申請理由 / 備註
                <textarea className="input" value={reason} onChange={e => setReason(e.target.value)} rows={3} style={{ height: "auto", padding: 12, resize: "none" }} placeholder="簡述用途，供管理員審批參考"/>
              </label>
            </>
          )}
          {notice && <div className="mobile-login-message is-ok" style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>{notice}</div>}
          {(localError || error) && <div className="mobile-login-message is-error" style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>{localError || error}</div>}
          <button className="btn btn-primary mobile-login-submit" type="submit" disabled={busy} style={{ height: 42 }}>
            <Icon name={isRegister ? "user" : "shield"} size={16}/>{busy ? "處理中..." : submitText}
          </button>
          {!needsSetup && !isRegister && (
            <div className="muted center mobile-login-help" style={{ fontSize: 11.5 }}>忘記密碼？請聯繫管理員重置。</div>
          )}
          {!isRegister && (
            <div className="center mobile-login-ops" style={{ fontSize: 11.5 }}>
              <a href="platform.html" target="_blank" rel="noopener" className="muted" style={{ fontWeight: 700, textDecoration: "none" }}>
                平台運營後台
              </a>
            </div>
          )}
        </form>
        <div className="mobile-login-footnote">BONFIRE WORKSHOP · 安全會話 · 權限隔離 · 審計留痕</div>
      </div>
    </div>
  );
};

const JoinCompanyModal = ({ onClose }) => {
  const [slug, setSlug] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const submit = (e) => {
    e.preventDefault();
    if (busy || !slug.trim()) return;
    setBusy(true); setError("");
    window.authFetch("/api/companies/join", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slug: slug.trim().toLowerCase() }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "申請失敗"); setDone(data.message || "申請已提交"); })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusy(false));
  };
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="card col gap-14" style={{ width: "min(400px, 100%)", padding: 24 }}>
        <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>加入企業</div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {done ? (
          <>
            <div style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>{done}</div>
            <div className="muted" style={{ fontSize: 12.5 }}>該企業的管理員審批通過後,它會出現在你的公司切換器裡。</div>
            <button type="button" className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        ) : (
          <>
            <div className="muted" style={{ fontSize: 12.5 }}>輸入要加入的企業代碼(向該公司管理員索取)。提交後需其管理員審批。</div>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>企業代碼
              <input className="input" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="例如:acme" autoFocus/></label>
            {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
            <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 40 }}>{busy ? "提交中…" : "提交加入申請"}</button>
          </>
        )}
      </form>
    </div>
  );
};

const ApplyCompanyModal = ({ onClose }) => {
  const [form, setForm] = useState({ company_name: "", slug: "", industry_template: "", contact: "", reason: "" });
  const [templates, setTemplates] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState("");
  const up = (key) => (e) => setForm({ ...form, [key]: key === "slug" ? e.target.value.toLowerCase() : e.target.value });

  useEffect(() => {
    window.authFetch("/api/platform/templates")
      .then((res) => res.json())
      .then((data) => {
        const list = data.templates || [];
        setTemplates(list);
        if (list[0]) setForm((prev) => ({ ...prev, industry_template: prev.industry_template || list[0].key }));
      })
      .catch(() => setTemplates([]));
  }, []);

  const submit = (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true); setError(""); setDone("");
    window.authFetch("/api/companies/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(form),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "申請失敗");
        setDone(data.message || "公司開通申請已提交");
      })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="card col gap-14" style={{ width: "min(460px, 100%)", padding: 24 }}>
        <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>申請開通公司</div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {done ? (
          <>
            <div style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>{done}</div>
            <div className="muted" style={{ fontSize: 12.5 }}>審批通過後，你會成為該公司的系統管理員，公司會出現在頂部切換器裡。</div>
            <button type="button" className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        ) : (
          <>
            <div className="muted" style={{ fontSize: 12.5 }}>提交後由系統管理員審批；通過時系統會自動建立該公司的獨立資料庫與初始表。</div>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>公司名稱
              <input className="input" value={form.company_name} onChange={up("company_name")} placeholder="例如:ACME 倉儲"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>企業代碼
              <input className="input" value={form.slug} onChange={up("slug")} placeholder="3-40 位小寫字母/數字/短橫線"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>行業模板
              <select className="input" value={form.industry_template} onChange={up("industry_template")}>
                {templates.map((t) => <option key={t.key} value={t.key}>{t.name}</option>)}
              </select></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>聯繫方式
              <input className="input" value={form.contact} onChange={up("contact")} placeholder="手機 / 郵箱"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>申請理由
              <textarea className="input" value={form.reason} onChange={up("reason")} rows={3} style={{ height: "auto", padding: 12, resize: "none" }}/></label>
            {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
            <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 40 }}>{busy ? "提交中…" : "提交申請"}</button>
          </>
        )}
      </form>
    </div>
  );
};

const mobileMoneyText = (value) => "¥" + Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 0 });
const mobileCountText = (value) => Number(value || 0).toLocaleString("zh-CN");

const mobileFetchJson = async (path) => {
  const res = await window.authFetch(path);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || data.message || res.statusText || "request failed");
  return data;
};

const MobileActionCenter = ({ active, onNavigate, tenant, dataVersion }) => {
  const [state, setState] = React.useState({ loading: true, error: "", erp: {}, notif: {}, collab: [] });

  const load = React.useCallback(async () => {
    if (!window.WAREHOUSE_MOBILE_PLATFORM || !window.authFetch) return;
    setState((prev) => ({ ...prev, loading: true, error: "" }));
    try {
      const [erp, notif, collab] = await Promise.all([
        mobileFetchJson("/api/erp/overview").catch((err) => ({ _error: err.message })),
        mobileFetchJson("/api/notifications/summary").catch((err) => ({ _error: err.message, items: [], counts: {}, count: 0 })),
        mobileFetchJson("/api/collab/messages?box=all&status=active&limit=20").catch(() => ({ messages: [] })),
      ]);
      setState({
        loading: false,
        error: erp._error || notif._error || "",
        erp: erp._error ? {} : erp,
        notif: notif._error ? { count: 0, counts: {}, items: [] } : notif,
        collab: Array.isArray(collab.messages) ? collab.messages : [],
      });
    } catch (err) {
      setState((prev) => ({ ...prev, loading: false, error: err.message || "手機待辦載入失敗" }));
    }
  }, []);

  React.useEffect(() => { load(); }, [load, tenant, dataVersion]);
  React.useEffect(() => {
    if (!window.WAREHOUSE_MOBILE_PLATFORM) return undefined;
    const onChanged = () => load();
    window.addEventListener("alerts-agent-changed", onChanged);
    window.addEventListener("warehouse-mobile-refresh", onChanged);
    return () => {
      window.removeEventListener("alerts-agent-changed", onChanged);
      window.removeEventListener("warehouse-mobile-refresh", onChanged);
    };
  }, [load]);

  if (!window.WAREHOUSE_MOBILE_PLATFORM) return null;

  const erp = state.erp || {};
  const summary = erp.summary || {};
  const inventoryDocs = (erp.inventory_documents || []).filter((d) => d.budget_unlinked_open === true);
  const alerts = (erp.open_alerts || []).filter((a) => (a.status || "open") !== "closed");
  const purchases = (erp.purchase_requests || []).filter((p) => !["received", "cancelled", "closed", "completed"].includes(p.status || "draft"));
  const collab = (state.collab || []).filter((m) => (m.status || "active") === "active");
  const notifItems = (state.notif?.items || []).slice(0, 3);
  const pendingCount = Number(state.notif?.count || 0)
    + Number(summary.inventory_unlinked || 0)
    + Number(summary.open_alerts || alerts.length || 0)
    + collab.length;

  const openSecretary = (prompt, autoAsk = false) => {
    if (window.openCompanySecretary) window.openCompanySecretary(prompt, { autoAsk });
    else window.dispatchEvent(new CustomEvent("company-secretary-open", { detail: { prompt, autoAsk } }));
  };
  const go = (id) => {
    if (active !== id) onNavigate(id);
    setTimeout(() => document.querySelector(".main-scroll")?.scrollTo({ top: 0, behavior: "smooth" }), 20);
  };

  const taskRows = [
    ...inventoryDocs.slice(0, 3).map((d) => ({
      key: `doc-${d.id}`,
      icon: "link",
      tone: "orange",
      title: d.document_no || "未掛預算單據",
      sub: `${d.business_type || d.document_type || "庫存單據"} · ${d.summary || "待補預算/財務歸屬"}`,
      action: "交給AI",
      onRun: () => openSecretary(`請處理 ERP 單據 ${d.document_no || d.id}:這張採購入庫未掛預算或財務歸屬未完整。請先檢查它是否仍未閉環,再協助補足預算、付款來源、經辦人、摘要和財務入賬信息。`, true),
    })),
    ...alerts.slice(0, 2).map((a) => ({
      key: `alert-${a.id}`,
      icon: "alert",
      tone: a.level === "red" ? "red" : "orange",
      title: a.item_name || a.item || a.alert_type || "智能預警",
      sub: a.suggestion || a.suggest || `${a.level || "open"} · ${a.scope || "待處理"}`,
      action: "分析",
      onRun: () => openSecretary(`請分析並給出處置方案:預警 ${a.item_name || a.item || a.alert_type || a.id},級別 ${a.level || "未知"},建議 ${a.suggestion || a.suggest || "無"}`, true),
    })),
    ...collab.slice(0, 2).map((m) => ({
      key: `collab-${m.id}`,
      icon: "sparkle",
      tone: m.priority === "urgent" ? "red" : "purple",
      title: m.assistant_text || m.original_text || "AI 協作",
      sub: `${m.sender_name || "—"} → ${m.recipient_name || "—"} · ${m.priority || m.status || "active"}`,
      action: "跟進",
      onRun: () => openSecretary(`請跟進這條 AI 協作消息,判斷是否需要形成待辦、補資料或執行動作:${m.assistant_text || m.original_text || m.id}`, true),
    })),
    ...purchases.slice(0, 2).map((p) => ({
      key: `purchase-${p.id}`,
      icon: "clipboard",
      tone: "blue",
      title: p.title || p.request_no || "採購申請",
      sub: `${p.request_no || "—"} · ${p.supplier_name || "未指定供應商"} · ${mobileMoneyText(p.total_amount)}`,
      action: "推進",
      onRun: () => openSecretary(`請檢查採購申請 ${p.request_no || p.id} 的關聯工作流與業務全鏈，按節點順序推進：供應商 ${p.supplier_name || "未指定"}，金額 ${p.total_amount || 0}，當前狀態 ${p.status || "draft"}。不得直接改成批准、下單或到貨；下單只能由完成的工作流簽發正式 PO，到貨只能按該 PO 收貨。`, true),
    })),
  ].slice(0, 6);

  const quickActions = [
    ["付款補錄", "chart", "請幫我補錄一筆付款/報銷流水。請按複式記賬邏輯追問:誰付款、從哪個帳戶、支付方式、收款方帳戶、買了什麼、歸屬誰、是否報銷/投資/股權。"],
    ["股權出資", "layers", "請協助補錄一筆股權出資或股東資金往來。請追問股東、比例、出資方式、到賬帳戶、是否形成實收資本或其他應付款。"],
    ["今天待辦", "scan", "請把今天手機端需要處理的 ERP、財務、預警、協作待辦整理成可執行清單,並標出先後順序。"],
  ];

  return (
    <section className="mobile-action-center" aria-label="手機待辦中心">
      <div className="mobile-action-hero">
        <div className="mobile-action-copy">
          <div className="mobile-action-kicker">手機工作台</div>
          <div className="mobile-action-title">待辦中心</div>
          <div className="mobile-action-sub">
            {state.loading ? "正在同步…" : state.error ? "部分資料暫不可用" : `待處理 ${mobileCountText(pendingCount)} 項`}
          </div>
        </div>
        <button className="mobile-action-refresh" onClick={load} disabled={state.loading} title="刷新">
          <Icon name="refresh" size={15}/>
        </button>
      </div>

      <div className="mobile-action-metrics">
        <button onClick={() => go("erp")}><span>{mobileCountText(summary.inventory_unlinked || 0)}</span><em>未掛預算</em></button>
        <button onClick={() => go("alerts")}><span>{mobileCountText(summary.open_alerts || alerts.length || 0)}</span><em>預警</em></button>
        <button onClick={() => go("collab")}><span>{mobileCountText(collab.length)}</span><em>協作</em></button>
        <button onClick={() => go("finance")}><span>{mobileMoneyText(summary.budget_available || 0)}</span><em>可用預算</em></button>
      </div>

      <div className="mobile-action-quick">
        {quickActions.map(([label, icon, prompt]) => (
          <button key={label} onClick={() => openSecretary(prompt)}>
            <Icon name={icon} size={15}/>{label}
          </button>
        ))}
      </div>

      <div className="mobile-action-list">
        {!!notifItems.length && (
          <div className="mobile-action-notif">
            {notifItems.map((item, idx) => (
              <button key={idx} onClick={() => openSecretary(`請處理這條系統通知:${item.title || item.label || item.kind || ""}。${item.summary || item.description || ""}`, true)}>
                <Icon name={NOTIF_KIND_ICON[item.kind] || "bell"}/>
                <span>{item.title || item.label || item.kind || "通知"}</span>
              </button>
            ))}
          </div>
        )}
        {taskRows.length ? taskRows.map((row) => (
          <article key={row.key} className={`mobile-task-row is-${row.tone}`}>
            <div className="mobile-task-icon"><Icon name={row.icon} size={17}/></div>
            <div className="mobile-task-main">
              <strong>{row.title}</strong>
              <span>{row.sub}</span>
            </div>
            <button onClick={row.onRun}>{row.action}</button>
          </article>
        )) : (
          <div className="mobile-action-empty">
            <Icon name="checkCircle" size={18}/>暫無高優先級待辦
          </div>
        )}
      </div>
    </section>
  );
};

const ChangePasswordModal = ({ onClose }) => {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    if (busy) return;
    setError("");
    if (next !== confirm) { setError("兩次輸入的新密碼不一致"); return; }
    setBusy(true);
    window.authFetch("/api/auth/change-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ current_password: current, new_password: next }),
    })
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "修改失敗"); setDone(true); })
      .catch((err) => setError(err.message || String(err)))
      .finally(() => setBusy(false));
  };

  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="card col gap-14" style={{ width: "min(400px, 100%)", padding: 24 }}>
        <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>修改密碼</div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {done ? (
          <>
            <div style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>密碼已修改成功，其他設備上的登入已失效。</div>
            <button type="button" className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        ) : (
          <>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>當前密碼
              <PasswordInput value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>新密碼（至少 8 位）
              <PasswordInput value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>確認新密碼
              <PasswordInput value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password"/></label>
            {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>{error}</div>}
            <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 40 }}>{busy ? "處理中…" : "確認修改"}</button>
          </>
        )}
      </form>
    </div>
  );
};

function App() {
  const [booted, setBooted] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [tenant, setTenant] = useState(currentTenantSlug());
  const [isOwner, setIsOwner] = useState(false);
  const [canApplyCompany, setCanApplyCompany] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [loginError, setLoginError] = useState("");
  const [active, setActive] = useState("erp");
  const [wh, setWh] = useState("—");
  const [dataVersion, setDataVersion] = useState(0);
  const [lang, setLangState] = useState(window.I18N.getInitialLanguage());
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showJoinCompany, setShowJoinCompany] = useState(false);
  const [showApplyCompany, setShowApplyCompany] = useState(false);
  const go = (id) => { setActive(id); document.querySelector(".main-scroll")?.scrollTo(0, 0); };

  const loadBootstrap = () =>
    window.authFetch("/api/bootstrap")
      .then((res) => {
        if (!res.ok) throw new Error(`bootstrap failed: ${res.status}`);
        return res.json();
      })
      .then((payload) => {
        applyBootstrap(payload);
        setWh((payload.WAREHOUSES && payload.WAREHOUSES[0]) || "—");
        return payload;
      });

  window.reloadData = () =>
    loadBootstrap()
      .then(() => { setDataVersion((v) => v + 1); })
      .catch((err) => console.error("reloadData failed", err));

  const setLang = (nextLang) => {
    window.I18N.saveLanguage(nextLang);
    setLangState(nextLang);
  };

  // 檢查登入狀態;若全局 token 有效但當前公司不對(成員關係不在),自動切到第一家並重試一次
  const runAuthCheck = (allowRetry) =>
    window.authFetch("/api/auth/me")
      .then((res) => res.json().then((data) => ({ ok: res.ok, data, status: res.status })))
      .then(({ ok, data, status }) => {
        if (!ok && status !== 401) throw new Error(data.error || `auth failed: ${status}`);
        setNeedsSetup(Boolean(data.needs_setup));
        const active = (data.companies || []).filter((c) => c.status === "active");
        setCompanies(active);
        setIsOwner(!!data.is_platform_owner);
        setCanApplyCompany(!!data.can_apply_company || maxRoleLevel(data.user) >= 4);
        if (data.authenticated && data.user) {
          setCurrentTenantSlug(data.tenant);
          setTenant(data.tenant);
          setCurrentUser(data.user);
          return loadBootstrap();
        }
        if (allowRetry && active.length) {
          setCurrentTenantSlug(active[0].slug);
          setTenant(active[0].slug);
          return runAuthCheck(false);
        }
        setAuthToken("");
        setCurrentTenantSlug("");
        applyBootstrap(EMPTY_BOOTSTRAP);
        setWh("—");
        return null;
      });

  useEffect(() => {
    const handleExpired = () => {
      setCurrentUser(null);
      setLoginError("登入已失效，請重新登入");
    };
    window.addEventListener("warehouse-auth-expired", handleExpired);
    runAuthCheck(true)
      .catch((err) => {
        console.error(err);
        setAuthToken("");
        setCurrentUser(null);
        applyBootstrap(EMPTY_BOOTSTRAP);
        setWh("—");
      })
      .finally(() => { setBooted(true); setAuthChecked(true); });
    return () => window.removeEventListener("warehouse-auth-expired", handleExpired);
  }, []);

  const finishLogin = (user, activeCompanies, owner, applyCompany) => {
    setCurrentUser(user);
    setCompanies(activeCompanies || []);
    setIsOwner(!!owner);
    setCanApplyCompany(!!applyCompany || maxRoleLevel(user) >= 4);
    setTenant(currentTenantSlug());
    setNeedsSetup(false);
    setLoginError("");
    setBooted(false);
    loadBootstrap()
      .catch((err) => {
        console.error(err);
        setLoginError("登入成功，但讀取資料失敗");
      })
      .finally(() => setBooted(true));
  };

  const switchCompany = (slug) => {
    if (!slug || slug === tenant) return;
    setCurrentTenantSlug(slug);
    setTenant(slug);
    setActive("erp");
    setBooted(false);
    runAuthCheck(false)
      .catch((err) => { console.error(err); })
      .finally(() => setBooted(true));
  };

  const logout = () => {
    window.authFetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    setAuthToken("");
    setCurrentTenantSlug("");
    setCurrentUser(null);
    setCompanies([]);
    setIsOwner(false);
    setCanApplyCompany(false);
    applyBootstrap(EMPTY_BOOTSTRAP);
    setActive("erp");
  };

  // P1 助理綁賬號:暴露當前登入用戶給各組件(助理對話按賬號隔離),變更時廣播
  useEffect(() => {
    window.CURRENT_USER = currentUser || null;
    window.dispatchEvent(new Event("warehouse-user-changed"));
  }, [currentUser, tenant]);

  useEffect(() => {
    window.I18N.saveLanguage(lang);
    setTimeout(() => {
      window.I18N.translateTree(document.getElementById("root"), lang);
      // 白標:標題顯示當前公司名(覆蓋 i18n 預設標題)
      const b = (companies.find((c) => c.slug === tenant) || {}).name;
      if (b) document.title = b;
    }, 0);
  }, [active, authChecked, booted, lang, wh, companies, tenant]);

  if (!authChecked || !booted) {
    return (
      <div className="center" style={{ minHeight: "100vh", background: "var(--bg)" }}>
        <div className="card" style={{ padding: 22, width: 320 }}>
          <div style={{ fontWeight: 800, marginBottom: 8 }}>正在連接資料庫</div>
          <div className="muted" style={{ fontSize: 13 }}>讀取 SQLite 台賬資料與 AI 服務狀態…</div>
        </div>
      </div>
    );
  }

  if (!currentUser) return <LoginScreen needsSetup={needsSetup} onLogin={finishLogin} error={loginError}/>;

  // 物資台賬頁按分類動態路由:active = "ledger:<分類id>"
  const isLedger = active.indexOf("ledger:") === 0;
  const ledgerCategoryId = isLedger ? active.slice("ledger:".length) : null;
  const ledgerIndex = isLedger ? (window.LEDGER_CATEGORIES || []).findIndex(c => c.id === ledgerCategoryId) : -1;
  const LedgerComp = window.LedgerPage;
  // 自定義數據模塊頁:active = "custom:<key>"
  const isCustom = active.indexOf("custom:") === 0;
  const customKey = isCustom ? active.slice("custom:".length) : null;
  const CustomComp = window.PageCustomModule;
  const Comp = (isLedger || isCustom) ? null : window[PAGES[active]];
  const navLabel = (window.buildNav(isOwner).find(n => n.id === active) || {}).label || "";

  return (
    <>
      <div className="app-layout" style={{ display: "flex", height: "100vh", position: "relative", zIndex: 1 }}>
        <Sidebar active={active} onNav={go} brand={(companies.find(c => c.slug === tenant) || {}).name || ""} isOwner={isOwner}/>
        <div className="col app-content" style={{ flex: 1, minWidth: 0 }}>
          <TopBar wh={wh} setWh={setWh} lang={lang} setLang={setLang} currentUser={currentUser} onLogout={logout} onChangePassword={() => setShowChangePassword(true)}
            companies={companies} tenant={tenant} onSwitchCompany={switchCompany} onJoinCompany={() => setShowJoinCompany(true)}
            canApplyCompany={canApplyCompany || isOwner} onApplyCompany={() => setShowApplyCompany(true)} onNavigate={go}/>
          <main className="main-scroll scroll-y app-main-scroll" style={{ flex: 1, padding: "26px 28px 60px" }}>
            <MobileActionCenter active={active} onNavigate={go} tenant={tenant} dataVersion={dataVersion}/>
            <div key={active + ":" + dataVersion} className="fade-in">
              {isLedger
                ? (LedgerComp ? <LedgerComp categoryId={ledgerCategoryId} index={ledgerIndex < 0 ? 0 : ledgerIndex}/> : <Stub title={navLabel}/>)
                : isCustom
                ? (CustomComp ? <CustomComp moduleKey={customKey}/> : <Stub title={navLabel}/>)
                : (Comp ? <Comp go={go} wh={wh}/> : <Stub title={navLabel}/>)}
            </div>
          </main>
        </div>
      </div>
      {window.UnifiedAgentAssistant && <UnifiedAgentAssistant page={active} warehouse={wh}/>}
      {window.WAREHOUSE_MOBILE_PLATFORM && window.UnifiedAgentAssistant && (
        <button
          className="mobile-secretary-entry"
          onClick={() => {
            if (window.openCompanySecretary) window.openCompanySecretary();
            else window.dispatchEvent(new CustomEvent("company-secretary-open", { detail: {} }));
          }}
        >
          <Icon name="sparkle" size={17}/>公司 AI 秘書
        </button>
      )}
      {window.InlineExplainHost && <window.InlineExplainHost/>}
      {showChangePassword && <ChangePasswordModal onClose={() => setShowChangePassword(false)}/>}
      {showJoinCompany && <JoinCompanyModal onClose={() => setShowJoinCompany(false)}/>}
      {showApplyCompany && <ApplyCompanyModal onClose={() => setShowApplyCompany(false)}/>}
    </>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
