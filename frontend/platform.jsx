/* ============================================================
   平台運營後台(P2)— 平台審批 + 租戶管理
   獨立於租戶應用,走 /api/platform/* 端點與 platform.db。
   ============================================================ */
const { useState, useEffect } = React;

const API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const PTOKEN_KEY = "platform_auth_token";
const ptoken = () => window.localStorage.getItem(PTOKEN_KEY) || "";
const setPtoken = (t) => { t ? window.localStorage.setItem(PTOKEN_KEY, t) : window.localStorage.removeItem(PTOKEN_KEY); };

const pfetch = async (path, options = {}) => {
  const headers = new Headers(options.headers || {});
  headers.set("Content-Type", "application/json");
  const t = ptoken();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  const res = await fetch(API_BASE + path, { ...options, headers });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
};

// 復用主應用「超級終端」(page-terminal.jsx / window.PageTerminal)的配置。
// 返回原始 Response(終端要 res.json()/res.ok/res.body 流式),帶平台運營 token。
const ptermFetch = (url, options = {}) => {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const t = ptoken();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  return fetch(url, { ...options, headers });
};
const PLATFORM_TERM_CFG = {
  fetch: ptermFetch,
  apiBase: API_BASE,
  commandsMethod: "POST",
  paths: {
    exec: "/api/platform/cli/exec",
    stream: "/api/platform/agent/run/stream",
    sql: "/api/platform/admin/sql",
    commands: "/api/platform/cli/commands",
  },
  title: "運營後台 · 超級終端",
  subtitle: "與主應用終端同款:指令 + AI 會話 + SQL + 補全 · 選公司後以該公司管理員身份全權執行",
  height: "72vh",
  welcome: [
    { type: "info", text: "運營後台超級終端 — 指令模式直接輸入 WCS 指令(Tab 補全、↑↓ 歷史);輸入 ai 進入 AI 會話模式(自然語言逐步執行);sql <語句> 開發直連庫。" },
    { type: "info", text: "AI 會話兩種身份,按右上角「目標公司」自動切換:不選公司 = 平台級 AI(管平台本身:審批入駐、開通/停用公司、加運營員、看各公司狀況);選了公司 = 該公司管理員秘書(辦該公司的庫存/財務/單據)。" },
    { type: "info", text: "指令同理:不選 = 平台指令(tenants/operators/signups/company…),選定 = 該公司業務指令。所有寫操作全程審計,歸屬你的運營員賬號。sql 需先選公司。" },
  ],
};

const SIGNUP_BADGE = { pending: "badge-warn", approved: "badge-ok", rejected: "badge-danger" };
const SIGNUP_LABEL = { pending: "待審批", approved: "已開通", rejected: "已駁回" };

const PlatformPasswordInput = ({ value, onChange, autoComplete, placeholder, inputStyle = {} }) => {
  const [visible, setVisible] = useState(false);
  const label = visible ? "隱藏密碼" : "顯示密碼";
  return (
    <div style={{ position: "relative", width: "100%" }}>
      <input
        className="input"
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        placeholder={placeholder}
        style={{ width: "100%", paddingRight: 54, ...inputStyle }}
      />
      <button
        type="button"
        aria-label={label}
        title={label}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setVisible((next) => !next)}
        style={{
          position: "absolute",
          right: 6,
          top: "50%",
          transform: "translateY(-50%)",
          height: 30,
          padding: "0 8px",
          border: "none",
          borderRadius: 8,
          background: "transparent",
          color: "var(--blue)",
          cursor: "pointer",
          fontSize: 12,
          fontWeight: 800,
        }}
      >
        {visible ? "隱藏" : "顯示"}
      </button>
    </div>
  );
};

/* ---------- 運營後台終端(平台級指令 + 選公司跑業務指令)---------- */
const pTermRowsOf = (data) => {
  if (Array.isArray(data)) return data.every((r) => r && typeof r === "object" && !Array.isArray(r)) ? data : null;
  if (data && Array.isArray(data.rows)) return data.rows;
  if (data && Array.isArray(data.tenants)) return data.tenants;
  if (data && Array.isArray(data.operators)) return data.operators;
  if (data && Array.isArray(data.signups)) return data.signups;
  if (data && Array.isArray(data.categories)) return data.categories;
  if (data && Array.isArray(data.modules)) return data.modules;
  return null;
};
const PTermTable = ({ rows }) => {
  const cols = Object.keys(rows[0] || {}).slice(0, 8);
  return (
    <div style={{ overflowX: "auto", margin: "6px 0" }}>
      <table style={{ borderCollapse: "collapse", fontSize: 12, whiteSpace: "nowrap" }}>
        <thead><tr>{cols.map((c) => <th key={c} style={{ textAlign: "left", padding: "3px 12px 3px 0", color: "#7dd3fc", borderBottom: "1px solid rgba(125,211,252,0.3)" }}>{c}</th>)}</tr></thead>
        <tbody>{rows.slice(0, 40).map((r, i) => <tr key={i}>{cols.map((c) => <td key={c} style={{ padding: "2px 12px 2px 0", color: "#d1fae5" }}>{r[c] === null || r[c] === undefined ? "—" : (typeof r[c] === "object" ? JSON.stringify(r[c]) : String(r[c]))}</td>)}</tr>)}</tbody>
      </table>
      <div style={{ color: "#64748b", fontSize: 11, marginTop: 3 }}>共 {rows.length} 行{rows.length > 40 ? ",僅顯示前 40 行" : ""}</div>
    </div>
  );
};
const PTermHelp = ({ commands }) => (
  <div style={{ margin: "6px 0" }}>
    {commands.map((c, i) => (
      <div key={i} style={{ marginBottom: 6, opacity: c.allowed === false ? 0.45 : 1 }}>
        <span style={{ color: c.writes ? "#fbbf24" : "#7dd3fc", fontWeight: 700 }}>{c.usage}</span>
        {c.writes && <span style={{ color: "#f87171", fontSize: 10.5, marginLeft: 8, border: "1px solid rgba(248,113,113,0.45)", borderRadius: 4, padding: "0 5px" }}>寫</span>}
        <div style={{ color: "#94a3b8", fontSize: 12 }}>{c.description}</div>
      </div>
    ))}
    <div style={{ color: "#64748b", fontSize: 11.5 }}>本地指令:help、clear。含空格的值用雙引號。</div>
  </div>
);
const PTermBlock = ({ item }) => {
  if (item.type === "cmd") return <div style={{ color: "#e2e8f0", marginTop: 10 }}><span style={{ color: "#34d399", fontWeight: 800 }}>{item.prompt || "plat>"}</span> {item.text}</div>;
  if (item.type === "info") return <div style={{ color: "#94a3b8" }}>{item.text}</div>;
  if (item.type === "error") return <div style={{ color: "#f87171" }}>✗ {item.text}{item.usage && <div style={{ color: "#fbbf24", fontSize: 12 }}>用法:{item.usage}</div>}{item.hint && <div style={{ color: "#94a3b8", fontSize: 12 }}>{item.hint}</div>}</div>;
  const env = item.env || {}, data = env.data, rows = pTermRowsOf(data);
  return (
    <div>
      <div style={{ color: "#34d399", fontSize: 12 }}>✓ {env.command}{typeof env.status === "number" ? ` · ${env.status}` : ""}{typeof env.elapsed_ms === "number" ? ` · ${env.elapsed_ms}ms` : ""}{env.writes ? " · 已寫庫(已審計)" : ""}</div>
      {data && data.commands ? <PTermHelp commands={data.commands}/>
        : rows ? <PTermTable rows={rows}/>
        : typeof (data && (data.message || data.reply)) === "string" ? <div style={{ color: "#d1fae5", whiteSpace: "pre-wrap", margin: "4px 0" }}>{data.message || data.reply}</div>
        : <pre style={{ color: "#d1fae5", fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: "4px 0", maxHeight: 360, overflowY: "auto" }}>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
};

const PlatformTerminal = ({ companies }) => {
  const [items, setItems] = useState([{ type: "info", text: "運營後台終端 · 輸入 help 查看平台指令。選擇目標公司後可跑該公司業務指令(以該公司管理員身份執行,記入審計)。" }]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [slug, setSlug] = useState("");
  const [history, setHistory] = useState([]);
  const histRef = React.useRef(-1);
  const bottomRef = React.useRef(null);
  const inputRef = React.useRef(null);
  const active = (companies || []).filter((t) => t.status === "active" || !t.status);
  useEffect(() => { bottomRef.current && bottomRef.current.scrollIntoView({ block: "end" }); }, [items, busy]);
  const push = (...b) => setItems((p) => [...p, ...b]);
  const prompt = slug ? `${slug}>` : "plat>";
  const run = async (line) => {
    const text = line.trim(); if (!text) return;
    setHistory((h) => [...h, text]); histRef.current = -1;
    push({ type: "cmd", text, prompt });
    if (text === "clear") { setItems([]); return; }
    setBusy(true);
    try {
      const { data: env } = await pfetch("/api/platform/cli/exec", { method: "POST", body: JSON.stringify({ line: text, tenant_slug: slug || undefined }) });
      if (env && env.ok) push({ type: "result", env });
      else push({ type: "error", text: (env && env.error) || "執行失敗", usage: env && env.usage, hint: env && env.hint });
    } catch (e) { push({ type: "error", text: "無法連接指令路由器:" + (e.message || e) }); }
    finally { setBusy(false); inputRef.current && inputRef.current.focus(); }
  };
  const onKeyDown = (e) => {
    if (e.key === "Enter" && !busy) { const v = input; setInput(""); run(v); }
    else if (e.key === "ArrowUp") { e.preventDefault(); if (!history.length) return; histRef.current = histRef.current === -1 ? history.length - 1 : Math.max(0, histRef.current - 1); setInput(history[histRef.current]); }
    else if (e.key === "ArrowDown") { e.preventDefault(); if (histRef.current === -1) return; histRef.current = histRef.current + 1 >= history.length ? -1 : histRef.current + 1; setInput(histRef.current === -1 ? "" : history[histRef.current]); }
  };
  return (
    <div className="col gap-10">
      <div className="row gap-10" style={{ alignItems: "center", flexWrap: "wrap" }}>
        <span className="muted" style={{ fontSize: 12.5 }}>目標:</span>
        <select className="input" style={{ maxWidth: 260, height: 34 }} value={slug} onChange={(e) => setSlug(e.target.value)}>
          <option value="">平臺(平台級指令)</option>
          {active.map((t) => <option key={t.slug} value={t.slug}>{t.name}(/{t.slug})· 業務指令</option>)}
        </select>
        <button className="btn btn-sm" disabled={busy} onClick={() => run("help")}>指令一覽</button>
        <span className="muted" style={{ fontSize: 11.5 }}>{slug ? "已選公司:可跑 inv/ledger/inbound… 業務指令" : "平台級:tenants/company/operators/signups…"}</span>
      </div>
      <div onClick={() => inputRef.current && inputRef.current.focus()} style={{
        height: "62vh", borderRadius: 14, border: "1px solid rgba(125,211,252,0.18)", background: "#0b1220",
        boxShadow: "inset 0 0 40px rgba(2,6,23,0.6)", padding: "14px 16px", overflowY: "auto", cursor: "text",
        fontFamily: "ui-monospace, SFMono-Regular, Consolas, Menlo, monospace", fontSize: 13, lineHeight: 1.65,
      }}>
        {items.map((item, i) => <PTermBlock key={i} item={item}/>)}
        {busy && <div style={{ color: "#7dd3fc" }}>… 執行中</div>}
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <span style={{ color: "#34d399", fontWeight: 800 }}>{prompt}</span>
          <input ref={inputRef} value={input} disabled={busy} autoFocus spellCheck={false}
            onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
            placeholder={busy ? "" : (slug ? "業務指令,如 inv list / ledger list --category safety_tool" : "平台指令,如 tenants list / help")}
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "#e2e8f0", fontFamily: "inherit", fontSize: 13, caretColor: "#34d399" }}/>
        </div>
        <div ref={bottomRef}/>
      </div>
    </div>
  );
};

/* ---------- 平台運營登入 / 初始化 ---------- */
const OperatorAuth = ({ needsSetup, onLogin }) => {
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = (e) => {
    e.preventDefault();
    if (busy) return;
    setErr(""); setBusy(true);
    const path = needsSetup ? "/api/platform/bootstrap" : "/api/platform/login";
    const body = needsSetup ? { username, display_name: displayName || username, password } : { username, password };
    pfetch(path, { method: "POST", body: JSON.stringify(body) })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || (needsSetup ? "初始化失敗" : "登入失敗"));
        setPtoken(data.token);
        onLogin(data.user);
      })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusy(false));
  };

  return (
    <form onSubmit={submit} className="card col gap-14" style={{ padding: 22 }}>
      <div className="row gap-12" style={{ alignItems: "center", borderBottom: "1px solid var(--border)", paddingBottom: 14 }}>
        <img src="v2/brand/bonfire-platform-mark.png" width="42" height="42" alt=""/>
        <div>
          <div style={{ fontSize: 17, fontWeight: 850 }}>WAREHOUSE OS 2.0</div>
          <div className="muted" style={{ fontSize: 9.5, letterSpacing: ".12em", marginTop: 3 }}>BONFIRE WORKSHOP · PLATFORM OPERATIONS</div>
        </div>
      </div>
      <div style={{ fontSize: 16, fontWeight: 800 }}>{needsSetup ? "初始化平台運營賬號" : "平台運營登入"}</div>
      <div className="muted" style={{ fontSize: 12.5, marginTop: -8 }}>{needsSetup ? "建立平台的第一個運營管理賬號(平台方,非企業用戶)。" : "登入後審批公司申請、管理租戶。"}</div>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>帳號
        <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username"/>
      </label>
      {needsSetup && (
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>顯示名稱
          <input className="input" value={displayName} onChange={(e) => setDisplayName(e.target.value)}/>
        </label>
      )}
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>密碼
        <PlatformPasswordInput value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={needsSetup ? "new-password" : "current-password"}/>
      </label>
      {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>{err}</div>}
      <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 42 }}>{busy ? "處理中…" : needsSetup ? "建立運營賬號" : "登入"}</button>
      {!needsSetup && (
        <div className="muted center" style={{ fontSize: 11.5 }}>忘記密碼？請其他運營管理員代為重置;若無人可重置,用服務器 CLI:<br/><code>python3 scripts/reset_password.py --platform --user 你的帳號</code></div>
      )}
    </form>
  );
};

/* 運營員層級徽章 + 授權公司 chips */
const OpTierBadge = ({ role, scopes }) => {
  if ((role || "full") === "full") return <span className="badge badge-info" style={{ height: 20 }}>全平台</span>;
  const list = scopes || [];
  return (
    <span className="row gap-4" style={{ flexWrap: "wrap", alignItems: "center" }}>
      <span className="badge badge-warn" style={{ height: 20 }}>限定 {list.length} 家</span>
      {list.map((s) => <span key={s.slug} className="badge badge-gray" style={{ height: 18, fontSize: 11 }}>{s.name || s.slug}</span>)}
    </span>
  );
};

/* 公司多選(授權範圍選擇器) */
const CompanyScopePicker = ({ candidates, value, onChange }) => {
  const toggle = (slug) => {
    const set = new Set(value || []);
    set.has(slug) ? set.delete(slug) : set.add(slug);
    onChange(Array.from(set));
  };
  if (!candidates.length) return <div className="muted" style={{ fontSize: 12 }}>（你名下暫無可授權的公司）</div>;
  return (
    <div className="row gap-6" style={{ flexWrap: "wrap" }}>
      {candidates.map((c) => {
        const on = (value || []).includes(c.slug);
        return (
          <button key={c.slug} type="button" onClick={() => toggle(c.slug)} className="btn btn-sm"
            style={{ background: on ? "var(--blue)" : "var(--surface-2)", color: on ? "#fff" : "var(--ink-2)", fontSize: 12 }}>
            {on ? "✓ " : ""}{c.name || c.slug}
          </button>
        );
      })}
    </div>
  );
};

/* ---------- 運營控制台 ---------- */
const Console = ({ user, onLogout }) => {
  const [tab, setTab] = useState("pending");
  const [signups, setSignups] = useState([]);
  const [pendingCount, setPendingCount] = useState(0);
  const [tenants, setTenants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [busyId, setBusyId] = useState(null);
  const [note, setNote] = useState({});
  const [operators, setOperators] = useState([]);
  const [opForm, setOpForm] = useState({ username: "", display_name: "", password: "", role: "scoped", scopes: [] });
  const [opResetInfo, setOpResetInfo] = useState(null);
  const [showChangePw, setShowChangePw] = useState(false);
  const [manageSlug, setManageSlug] = useState(null);
  const [scopeEdit, setScopeEdit] = useState(null); // 正在編輯權限的運營員

  // 當前運營員的層級與可授權公司範圍
  const meFull = ((user || {}).role || "full") === "full";
  const myScopes = (user || {}).scopes || [];
  // 可授予給(子)運營員的候選公司:全平台→全部公司;限定→自己被授權的公司
  const grantableCompanies = meFull ? tenants.map((t) => ({ slug: t.slug, name: t.name })) : myScopes;

  const setTenantStatus = (slug, status) => {
    if (busyId) return;
    const action = status === "suspended" ? "suspended" : "active";
    setBusyId("t" + slug); setErr("");
    pfetch(`/api/platform/tenants/${slug}/status/${action}`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "操作失敗"); load(); })
      .catch((e) => setErr(e.message || String(e)))
      .finally(() => setBusyId(null));
  };

  const load = () => {
    setLoading(true); setErr("");
    const status = (tab === "tenants" || tab === "operators") ? "pending" : tab;
    Promise.all([pfetch(`/api/platform/signups?status=${status}`), pfetch("/api/platform/tenants"), pfetch("/api/platform/operators")])
      .then(([a, b, c]) => {
        if (a.status === 401 || b.status === 401) { onLogout(); return; }
        setSignups(a.data.signups || []);
        setPendingCount(a.data.pending_count || 0);
        setTenants(b.data.tenants || []);
        setOperators(c.data.operators || []);
      })
      .catch((e) => setErr(e.message || String(e)))
      .finally(() => setLoading(false));
  };
  useEffect(load, [tab]);

  const decide = (s, action) => {
    if (busyId) return;
    setBusyId(s.id); setErr("");
    pfetch(`/api/platform/signups/${s.id}/${action}`, { method: "POST", body: JSON.stringify({ note: note[s.id] || "" }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "操作失敗"); load(); })
      .catch((e) => setErr(e.message || String(e)))
      .finally(() => setBusyId(null));
  };

  const addOperator = (e) => {
    e.preventDefault();
    if (busyId) return;
    if (opForm.role === "scoped" && !(opForm.scopes || []).length) { setErr("限定公司級至少需勾選一家公司"); return; }
    setBusyId("add-op"); setErr("");
    pfetch("/api/platform/operators", { method: "POST", body: JSON.stringify(opForm) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "新增失敗"); setOpForm({ username: "", display_name: "", password: "", role: "scoped", scopes: [] }); load(); })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusyId(null));
  };

  const saveScope = (op, role, scopes) => {
    if (busyId) return;
    if (role === "scoped" && !scopes.length) { setErr("限定公司級至少需勾選一家公司"); return; }
    setBusyId("scope" + op.id); setErr("");
    pfetch(`/api/platform/operators/${op.id}/scope`, { method: "POST", body: JSON.stringify({ role, scopes }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setScopeEdit(null); load(); })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusyId(null));
  };

  const resetOperator = (op) => {
    if (busyId) return;
    if (!window.confirm(`確定重置運營賬號「${op.display_name}」(@${op.username})的密碼?其登入會立即失效。`)) return;
    setBusyId("op" + op.id); setErr("");
    pfetch(`/api/platform/operators/${op.id}/reset-password`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "重置失敗"); setOpResetInfo({ name: op.display_name, username: op.username, password: data.temp_password }); })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusyId(null));
  };

  const Tab = ({ id, label, count }) => (
    <button onClick={() => setTab(id)} className="btn btn-sm" style={{ background: tab === id ? "var(--blue)" : "var(--surface-2)", color: tab === id ? "#fff" : "var(--ink-2)" }}>
      {label}{count ? ` (${count})` : ""}
    </button>
  );

  return (
    <div className="col gap-18" style={{ maxWidth: 980, margin: "0 auto", padding: "28px 20px" }}>
      <div className="row spread">
        <div className="row gap-12" style={{ alignItems: "center" }}>
          <img src="v2/brand/bonfire-platform-mark.png" width="46" height="46" alt=""/>
          <div className="col gap-3">
            <div style={{ fontSize: 20, fontWeight: 800 }}>WAREHOUSE OS 2.0</div>
            <div className="muted" style={{ fontSize: 12.5 }}>BONFIRE WORKSHOP · 平台運營後台</div>
          </div>
        </div>
        <div className="row gap-10" style={{ alignItems: "center" }}>
          <span className="muted" style={{ fontSize: 12.5 }}>運營員:{(user || {}).display_name}</span>
          <OpTierBadge role={(user || {}).role} scopes={myScopes}/>
          <button className="btn btn-sm" onClick={() => setShowChangePw(true)}>修改密碼</button>
          <button className="btn btn-sm" onClick={load}>刷新</button>
          <button className="btn btn-sm" onClick={onLogout} style={{ color: "var(--danger)" }}>登出</button>
        </div>
      </div>

      <div className="row gap-8">
        <Tab id="pending" label="待審批" count={pendingCount}/>
        <Tab id="approved" label="已開通"/>
        <Tab id="rejected" label="已駁回"/>
        <Tab id="tenants" label="公司管理" count={tenants.length}/>
        <Tab id="operators" label="運營賬號" count={operators.length}/>
        <Tab id="terminal" label="終端"/>
      </div>

      {err && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>{err}</div>}
      {loading && <div className="muted" style={{ fontSize: 13 }}>載入中…</div>}

      {!loading && ["pending", "approved", "rejected"].includes(tab) && (
        <div className="col gap-12">
          {signups.length === 0 && <div className="card muted" style={{ padding: 28, textAlign: "center", fontSize: 13 }}>暫無{SIGNUP_LABEL[tab]}申請</div>}
          {signups.map((s) => (
            <div key={s.id} className="card" style={{ padding: 18 }}>
              <div className="row spread" style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 15, fontWeight: 800 }}>{s.company_name} <span className="num muted" style={{ fontSize: 12 }}>/{s.slug}</span></div>
                <span className={`badge ${SIGNUP_BADGE[s.status]}`} style={{ height: 22 }}>{SIGNUP_LABEL[s.status]}</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 10, marginBottom: 12, fontSize: 12.5 }}>
                {[["行業模板", s.template_name], ["管理員帳號", s.admin_username], ["管理員", s.admin_display_name], ["聯繫方式", s.contact], ["申請時間", s.created_at], ["備註", s.reason]].map(([k, v], i) => (
                  <div key={i} className="col gap-3"><span className="muted" style={{ fontSize: 11 }}>{k}</span><span>{v || "—"}</span></div>
                ))}
              </div>
              {s.status === "pending" ? (
                <div className="col gap-10" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
                  <input className="input" placeholder="審批備註 / 駁回理由(可選)" value={note[s.id] || ""} onChange={(e) => setNote({ ...note, [s.id]: e.target.value })}/>
                  <div className="row gap-8">
                    <button className="btn btn-primary btn-sm" disabled={busyId === s.id} onClick={() => decide(s, "approve")}>通過並開通企業空間</button>
                    <button className="btn btn-sm" disabled={busyId === s.id} style={{ color: "var(--danger)" }} onClick={() => decide(s, "reject")}>駁回</button>
                  </div>
                </div>
              ) : (
                <div className="muted" style={{ fontSize: 12, borderTop: "1px solid var(--line)", paddingTop: 10 }}>
                  {s.reviewer_name ? `審批人:${s.reviewer_name}` : ""}{s.review_note ? ` · 備註:${s.review_note}` : ""}{s.reviewed_at ? ` · ${s.reviewed_at}` : ""}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && tab === "tenants" && !meFull && (
        <div className="muted" style={{ fontSize: 12.5 }}>你是限定公司級運營員,僅顯示並可管理你被授權的 {myScopes.length} 家公司。</div>
      )}
      {!loading && tab === "tenants" && (
        tenants.length === 0
          ? <div className="card muted" style={{ padding: 28, textAlign: "center", fontSize: 13 }}>{meFull ? "暫無公司" : "你名下暫無被授權的公司"}</div>
          :
        <div className="card" style={{ padding: 0, overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>
              {["企業", "企業代碼", "行業模板", "成員", "身份衝突", "狀態", "操作"].map((h) => <th key={h} style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12 }}>{h}</th>)}
            </tr></thead>
            <tbody>
              {tenants.map((t) => (
                <tr key={t.id} style={{ borderTop: "1px solid var(--line)" }}>
                  <td style={{ padding: "12px 16px", fontWeight: 700 }}>{t.name}</td>
                  <td style={{ padding: "12px 16px" }} className="num muted">/{t.slug}</td>
                  <td style={{ padding: "12px 16px" }}>{t.template_name || t.industry_template || "—"}</td>
                  <td style={{ padding: "12px 16px" }} className="num">{t.member_count != null ? t.member_count : "—"}</td>
                  <td style={{ padding: "12px 16px" }}>
                    {Number(t.identity_conflict_count || 0) > 0
                      ? <span className="badge badge-danger" title="已隔離同一租戶帳號綁定多個全局身份的記錄,需平台人工核對">待核對 {t.identity_conflict_count}</span>
                      : <span className="muted">0</span>}
                  </td>
                  <td style={{ padding: "12px 16px" }}><span className={`badge ${t.status === "active" ? "badge-ok" : "badge-danger"}`} style={{ height: 20 }}>{t.status === "active" ? "啟用" : "停用"}</span></td>
                  <td style={{ padding: "12px 16px" }}>
                    <div className="row gap-6">
                      <button className="btn btn-sm" onClick={() => setManageSlug(t.slug)}>管理</button>
                      {t.status === "active"
                        ? <button className="btn btn-sm" disabled={busyId === "t" + t.slug} style={{ color: "var(--danger)" }} onClick={() => setTenantStatus(t.slug, "suspended")}>停用</button>
                        : <button className="btn btn-sm" disabled={busyId === "t" + t.slug} style={{ color: "var(--ok)" }} onClick={() => setTenantStatus(t.slug, "active")}>恢復</button>}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {manageSlug && <CompanyManageModal slug={manageSlug} onClose={() => setManageSlug(null)} onChanged={load}/>}

      {tab === "terminal" && (window.PageTerminal
        ? React.createElement(window.PageTerminal, { cfg: { ...PLATFORM_TERM_CFG, companies: tenants } })
        : <div className="card muted" style={{ padding: 28, textAlign: "center" }}>終端組件載入中…(請刷新)</div>)}

      {!loading && tab === "operators" && (
        <div className="col gap-14">
          <form onSubmit={addOperator} className="card col gap-10" style={{ padding: 18 }}>
            <div style={{ fontSize: 14, fontWeight: 800 }}>新增運營賬號</div>
            <div className="muted" style={{ fontSize: 12, marginTop: -6 }}>
              {meFull ? "全平台級可管理所有公司;限定公司級只能管理你勾選的公司。" : "你是限定級,只能建限定級子賬號,且授權範圍不超過你自己。"}
            </div>
            <div className="row gap-10" style={{ flexWrap: "wrap" }}>
              <input className="input" style={{ maxWidth: 160 }} placeholder="帳號" value={opForm.username} onChange={(e) => setOpForm({ ...opForm, username: e.target.value })}/>
              <input className="input" style={{ maxWidth: 160 }} placeholder="顯示名稱" value={opForm.display_name} onChange={(e) => setOpForm({ ...opForm, display_name: e.target.value })}/>
              <input className="input" style={{ maxWidth: 160 }} type="password" placeholder="密碼(≥8位)" value={opForm.password} onChange={(e) => setOpForm({ ...opForm, password: e.target.value })}/>
            </div>
            <div className="row gap-8" style={{ alignItems: "center" }}>
              <span className="muted" style={{ fontSize: 12.5 }}>權限級別:</span>
              {meFull && (
                <button type="button" className="btn btn-sm" onClick={() => setOpForm({ ...opForm, role: "full" })}
                  style={{ background: opForm.role === "full" ? "var(--blue)" : "var(--surface-2)", color: opForm.role === "full" ? "#fff" : "var(--ink-2)" }}>全平台</button>
              )}
              <button type="button" className="btn btn-sm" onClick={() => setOpForm({ ...opForm, role: "scoped" })}
                style={{ background: opForm.role === "scoped" ? "var(--blue)" : "var(--surface-2)", color: opForm.role === "scoped" ? "#fff" : "var(--ink-2)" }}>限定公司</button>
            </div>
            {opForm.role === "scoped" && (
              <div className="col gap-6">
                <span className="muted" style={{ fontSize: 12 }}>選擇可管理的公司:</span>
                <CompanyScopePicker candidates={grantableCompanies} value={opForm.scopes} onChange={(v) => setOpForm({ ...opForm, scopes: v })}/>
              </div>
            )}
            <div className="row"><button className="btn btn-primary btn-sm" type="submit" disabled={busyId === "add-op"}>新增運營賬號</button></div>
          </form>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>
                {["運營員", "帳號", "權限", "狀態", "操作"].map((h) => <th key={h} style={{ padding: "12px 16px", fontWeight: 700, fontSize: 12 }}>{h}</th>)}
              </tr></thead>
              <tbody>
                {operators.length === 0 && (
                  <tr><td colSpan={5} className="muted" style={{ padding: "18px 16px", textAlign: "center", fontSize: 13 }}>暫無可管理的運營賬號</td></tr>
                )}
                {operators.map((o) => (
                  <tr key={o.id} style={{ borderTop: "1px solid var(--line)" }}>
                    <td style={{ padding: "12px 16px", fontWeight: 700 }}>{o.display_name}{o.is_self ? <span className="muted" style={{ fontWeight: 400, fontSize: 11 }}> (你)</span> : ""}</td>
                    <td className="num muted" style={{ padding: "12px 16px" }}>@{o.username}</td>
                    <td style={{ padding: "12px 16px" }}><OpTierBadge role={o.role} scopes={o.scopes}/></td>
                    <td style={{ padding: "12px 16px" }}><span className={`badge ${o.active ? "badge-ok" : "badge-gray"}`} style={{ height: 20 }}>{o.active ? "啟用" : "停用"}</span></td>
                    <td style={{ padding: "12px 16px" }}>
                      <div className="row gap-6" style={{ flexWrap: "wrap" }}>
                        <button className="btn btn-sm" disabled={busyId === "op" + o.id} onClick={() => resetOperator(o)}>重置密碼</button>
                        {!o.is_self && <button className="btn btn-sm" onClick={() => setScopeEdit({ id: o.id, name: o.display_name, role: o.role, scopes: (o.scopes || []).map((s) => s.slug) })}>編輯權限</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {opResetInfo && (
        <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={() => setOpResetInfo(null)}>
          <div className="card col gap-12" style={{ width: "min(380px, 100%)", padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 800 }}>密碼已重置</div>
            <div className="muted" style={{ fontSize: 12.5 }}>請把臨時密碼告知運營員 <b>{opResetInfo.name}</b>（@{opResetInfo.username}）。只顯示這一次,登入後請立即修改。</div>
            <div className="num" style={{ fontSize: 22, fontWeight: 800, letterSpacing: 1, textAlign: "center", padding: "14px 0", background: "var(--surface-2)", borderRadius: 12 }}>{opResetInfo.password}</div>
            <button className="btn btn-primary" onClick={() => setOpResetInfo(null)} style={{ height: 40 }}>我已記下,關閉</button>
          </div>
        </div>
      )}

      {scopeEdit && (
        <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={() => setScopeEdit(null)}>
          <div className="card col gap-12" style={{ width: "min(440px, 100%)", padding: 24 }} onClick={(e) => e.stopPropagation()}>
            <div style={{ fontSize: 16, fontWeight: 800 }}>編輯權限 · {scopeEdit.name}</div>
            <div className="row gap-8" style={{ alignItems: "center" }}>
              <span className="muted" style={{ fontSize: 12.5 }}>權限級別:</span>
              {meFull && (
                <button type="button" className="btn btn-sm" onClick={() => setScopeEdit({ ...scopeEdit, role: "full" })}
                  style={{ background: scopeEdit.role === "full" ? "var(--blue)" : "var(--surface-2)", color: scopeEdit.role === "full" ? "#fff" : "var(--ink-2)" }}>全平台</button>
              )}
              <button type="button" className="btn btn-sm" onClick={() => setScopeEdit({ ...scopeEdit, role: "scoped" })}
                style={{ background: scopeEdit.role === "scoped" ? "var(--blue)" : "var(--surface-2)", color: scopeEdit.role === "scoped" ? "#fff" : "var(--ink-2)" }}>限定公司</button>
            </div>
            {scopeEdit.role === "scoped" && (
              <div className="col gap-6">
                <span className="muted" style={{ fontSize: 12 }}>可管理的公司:</span>
                <CompanyScopePicker candidates={grantableCompanies} value={scopeEdit.scopes} onChange={(v) => setScopeEdit({ ...scopeEdit, scopes: v })}/>
              </div>
            )}
            <div className="row gap-8">
              <button className="btn btn-primary" style={{ flex: 1, height: 40 }} disabled={busyId === "scope" + scopeEdit.id} onClick={() => saveScope(scopeEdit, scopeEdit.role, scopeEdit.scopes)}>保存</button>
              <button className="btn" style={{ height: 40 }} onClick={() => setScopeEdit(null)}>取消</button>
            </div>
          </div>
        </div>
      )}

      {showChangePw && <PlatformChangePwModal onClose={() => setShowChangePw(false)}/>}
    </div>
  );
};

/* ---------- 運營員自助改密 ---------- */
const PlatformChangePwModal = ({ onClose }) => {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const submit = (e) => {
    e.preventDefault();
    if (busy) return;
    setErr("");
    if (next !== confirm) { setErr("兩次輸入的新密碼不一致"); return; }
    setBusy(true);
    pfetch("/api/platform/change-password", { method: "POST", body: JSON.stringify({ current_password: current, new_password: next }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "修改失敗"); setDone(true); })
      .catch((e2) => setErr(e2.message || String(e2)))
      .finally(() => setBusy(false));
  };
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={submit} className="card col gap-12" style={{ width: "min(380px, 100%)", padding: 24 }}>
        <div style={{ fontSize: 16, fontWeight: 800 }}>修改密碼</div>
        {done ? (
          <>
            <div style={{ color: "var(--ok)", fontSize: 13, fontWeight: 700 }}>密碼已修改,其他設備上的登入已失效。</div>
            <button type="button" className="btn btn-primary" onClick={onClose} style={{ height: 40 }}>完成</button>
          </>
        ) : (
          <>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>當前密碼
              <PlatformPasswordInput value={current} onChange={(e) => setCurrent(e.target.value)} autoComplete="current-password"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>新密碼（至少 8 位）
              <PlatformPasswordInput value={next} onChange={(e) => setNext(e.target.value)} autoComplete="new-password"/></label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>確認新密碼
              <PlatformPasswordInput value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password"/></label>
            {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>{err}</div>}
            <div className="row gap-8">
              <button className="btn btn-primary" type="submit" disabled={busy} style={{ flex: 1, height: 40 }}>{busy ? "處理中…" : "確認修改"}</button>
              <button className="btn" type="button" onClick={onClose} style={{ height: 40 }}>取消</button>
            </div>
          </>
        )}
      </form>
    </div>
  );
};

/* ---------- 公司管理詳情(統計 + 編輯 + 成員 + 重置)---------- */
const TEMPLATES_FALLBACK = [{ key: "generic_warehouse", name: "通用倉儲" }, { key: "power_system", name: "電力系統" }];
const CompanyManageModal = ({ slug, onClose, onChanged }) => {
  const [data, setData] = useState(null);
  const [templates, setTemplates] = useState(TEMPLATES_FALLBACK);
  const [form, setForm] = useState({ name: "", industry_template: "" });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [savedMsg, setSavedMsg] = useState("");
  const [resetInfo, setResetInfo] = useState(null);
  const [navList, setNavList] = useState(null); // [{id, group, default_label, label, hidden}] 按顯示順序
  const [navMsg, setNavMsg] = useState("");
  const [modules, setModules] = useState(null);   // 自定義模塊列表
  const [modEdit, setModEdit] = useState(null);    // 正在編輯/新建的模塊
  const [modMsg, setModMsg] = useState("");
  const [cats, setCats] = useState(null);          // 物資台賬分類列表
  const [catEdit, setCatEdit] = useState(null);    // 正在編輯/新建的分類

  const reload = () => {
    pfetch(`/api/platform/tenants/${slug}/detail`).then(({ ok, data }) => {
      if (!ok) { setErr(data.error || "載入失敗"); return; }
      setData(data);
      setForm({ name: data.tenant.name, industry_template: data.tenant.industry_template || "generic_warehouse" });
    });
  };
  const reloadNav = () => {
    pfetch(`/api/platform/tenants/${slug}/nav`).then(({ ok, data }) => {
      if (!ok) return;
      const cfg = (data.config && data.config.items) || {};
      // 按 catalog 順序建表,再按各組 config.order(若有)穩定排序
      const rows = (data.catalog || []).map((c, idx) => {
        const ov = cfg[c.id] || {};
        return { id: c.id, group: c.group, default_label: c.default_label, label: ov.label || "", hidden: !!ov.hidden, _o: (ov.order != null ? ov.order : idx), _i: idx };
      });
      rows.sort((a, b) => (a.group === b.group ? (a._o - b._o || a._i - b._i) : 0));
      setNavList(rows);
    });
  };
  const reloadModules = () => {
    pfetch(`/api/platform/tenants/${slug}/modules`).then(({ ok, data }) => { if (ok) setModules(data.modules || []); });
  };
  const reloadCats = () => {
    pfetch(`/api/platform/tenants/${slug}/categories`).then(({ ok, data }) => { if (ok) setCats(data.categories || []); });
  };
  useEffect(() => {
    reload(); reloadNav(); reloadModules(); reloadCats();
    fetch(API_BASE + "/api/platform/templates").then((r) => r.json()).then((d) => d.templates && setTemplates(d.templates)).catch(() => {});
  }, [slug]);

  const catNew = () => setCatEdit({ id: "", name: "", requires_return: false, description: "", _new: true });
  const saveCat = () => {
    setBusy(true); setErr("");
    const body = { id: catEdit.id, name: catEdit.name, requires_return: !!catEdit.requires_return, description: catEdit.description || null };
    pfetch(`/api/platform/tenants/${slug}/categories`, { method: "POST", body: JSON.stringify(body) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setCatEdit(null); reloadCats(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };
  const deleteCat = (c) => {
    if (!window.confirm(`刪除分類「${c.name}」?`)) return;
    setBusy(true); setErr("");
    pfetch(`/api/platform/tenants/${slug}/categories/${c.id}/delete`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "刪除失敗"); reloadCats(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };

  const NAV_GROUPS = ["ERP 工作台", "物資台賬", "庫存作業", "系統管理"];
  const FIELD_TYPES = [["text", "文本"], ["textarea", "多行文本"], ["number", "數字"], ["date", "日期"], ["select", "下拉"], ["checkbox", "開關"]];
  const modNew = () => setModEdit({ key: "", name: "", icon: "layers", nav_group: "系統管理", fields: [{ key: "", label: "", type: "text", required: false, options: "" }] });
  const modOpen = (m) => setModEdit({ ...m, fields: (m.fields || []).map((f) => ({ ...f, options: (f.options || []).join(", ") })) });
  const modAddField = () => setModEdit((m) => ({ ...m, fields: m.fields.concat([{ key: "", label: "", type: "text", required: false, options: "" }]) }));
  const modSetField = (i, patch) => setModEdit((m) => ({ ...m, fields: m.fields.map((f, idx) => idx === i ? { ...f, ...patch } : f) }));
  const modDelField = (i) => setModEdit((m) => ({ ...m, fields: m.fields.filter((_, idx) => idx !== i) }));
  const saveModule = () => {
    setBusy(true); setErr(""); setModMsg("");
    const payload = {
      key: modEdit.key, name: modEdit.name, icon: modEdit.icon || "layers", nav_group: modEdit.nav_group,
      fields: modEdit.fields.map((f) => ({ key: f.key, label: f.label, type: f.type, required: !!f.required,
        options: f.type === "select" ? String(f.options || "").split(/[,，]/).map((s) => s.trim()).filter(Boolean) : [] })),
    };
    pfetch(`/api/platform/tenants/${slug}/modules`, { method: "POST", body: JSON.stringify(payload) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setModEdit(null); setModMsg("模塊已保存,該公司用戶刷新後生效"); reloadModules(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };
  const deleteModule = (m) => {
    if (!window.confirm(`刪除模塊「${m.name}」及其全部記錄?此操作不可恢復。`)) return;
    setBusy(true); setErr("");
    pfetch(`/api/platform/tenants/${slug}/modules/${m.key}/delete`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "刪除失敗"); reloadModules(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };

  const navMove = (id, dir) => {
    setNavList((list) => {
      const arr = list.slice();
      const i = arr.findIndex((x) => x.id === id);
      if (i < 0) return list;
      // 只在同組內、相鄰可見/隱藏項間移動
      let j = dir < 0 ? i - 1 : i + 1;
      while (j >= 0 && j < arr.length && arr[j].group !== arr[i].group) j += dir;
      if (j < 0 || j >= arr.length || arr[j].group !== arr[i].group) return list;
      [arr[i], arr[j]] = [arr[j], arr[i]];
      return arr;
    });
  };
  const navSetLabel = (id, v) => setNavList((list) => list.map((x) => x.id === id ? { ...x, label: v } : x));
  const navToggleHidden = (id) => setNavList((list) => list.map((x) => x.id === id ? { ...x, hidden: !x.hidden } : x));
  const saveNav = () => {
    setBusy(true); setErr(""); setNavMsg("");
    const perGroup = {};
    const items = {};
    (navList || []).forEach((x) => {
      const ord = (perGroup[x.group] = (perGroup[x.group] || 0)); perGroup[x.group] += 1;
      const e = { order: ord };
      const lab = (x.label || "").trim();
      if (lab && lab !== x.default_label) e.label = lab;
      if (x.hidden) e.hidden = true;
      items[x.id] = e;
    });
    pfetch(`/api/platform/tenants/${slug}/nav`, { method: "POST", body: JSON.stringify({ items }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setNavMsg("導航已保存,該公司用戶刷新後生效"); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };

  const saveEdit = () => {
    const templateChanged = !!(data && data.tenant && form.industry_template !== data.tenant.industry_template);
    if (templateChanged && !window.confirm("切換行業模板會同步新部門與崗位,並封存未使用的舊模板項。確認繼續?")) return;
    setBusy(true); setErr(""); setSavedMsg("");
    pfetch(`/api/platform/tenants/${slug}/edit`, { method: "POST", body: JSON.stringify({ ...form, confirm_template_change: templateChanged }) })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "保存失敗"); setSavedMsg("已保存"); reload(); onChanged && onChanged(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };
  const resetMember = (m) => {
    if (!window.confirm(`重置 ${m.display_name}(@${m.username})的密碼?其登入會立即失效。`)) return;
    setBusy(true); setErr("");
    pfetch(`/api/platform/tenants/${slug}/members/${m.global_user_id}/reset-password`, { method: "POST", body: "{}" })
      .then(({ ok, data }) => { if (!ok) throw new Error(data.error || "重置失敗"); setResetInfo({ name: m.display_name, username: m.username, password: data.temp_password }); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };

  const st = data && data.stats;
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <div className="card col gap-16" style={{ width: "min(640px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="row spread"><div style={{ fontSize: 17, fontWeight: 800 }}>公司管理 · {data ? data.tenant.name : slug}</div>
          {/* platform.html 不載入 components.jsx,這裡不用 Icon,用文字 ✕ */}
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, fontWeight: 700, color: "var(--ink-3)", lineHeight: 1 }}>✕</button></div>
        {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {err}</div>}
        {!data ? <div className="muted" style={{ fontSize: 13 }}>載入中…</div> : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }}>
              {[["成員", st.members], ["用戶", st.users], ["物資", st.items], ["倉庫", st.warehouses]].map(([k, v]) => (
                <div key={k} className="col gap-2" style={{ padding: 12, borderRadius: 10, background: "var(--surface-2)" }}>
                  <span className="muted" style={{ fontSize: 11 }}>{k}</span><span className="num" style={{ fontSize: 22, fontWeight: 800 }}>{v}</span>
                </div>
              ))}
            </div>
            <div className="col gap-8">
              <div style={{ fontSize: 13.5, fontWeight: 800 }}>編輯</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>公司名稱
                  <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}/></label>
                <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>行業模板
                  <select className="input" value={form.industry_template} onChange={(e) => setForm({ ...form, industry_template: e.target.value })}>
                    {templates.map((t) => <option key={t.key} value={t.key}>{t.name}</option>)}
                  </select></label>
              </div>
              <div className="row gap-8" style={{ alignItems: "center" }}>
                <button className="btn btn-primary btn-sm" disabled={busy} onClick={saveEdit}>保存修改</button>
                {savedMsg && <span style={{ color: "var(--ok)", fontSize: 12.5, fontWeight: 700 }}>{savedMsg}</span>}
                <span className="num muted" style={{ fontSize: 11 }}>代碼 /{data.tenant.slug} · 狀態 {data.tenant.status}</span>
              </div>
            </div>
            <div className="col gap-8">
              <div className="row spread">
                <div style={{ fontSize: 13.5, fontWeight: 800 }}>導航設置(按公司自定義側欄)</div>
                <div className="row gap-8" style={{ alignItems: "center" }}>
                  {navMsg && <span style={{ color: "var(--ok)", fontSize: 12, fontWeight: 700 }}>{navMsg}</span>}
                  <button className="btn btn-primary btn-sm" disabled={busy || !navList} onClick={saveNav}>保存導航</button>
                </div>
              </div>
              <div className="muted" style={{ fontSize: 11.5, marginTop: -4 }}>重命名、顯示/隱藏、上下調序;此公司用戶的側欄將按此顯示。「系統設置」不可隱藏。</div>
              {!navList ? <div className="muted" style={{ fontSize: 12 }}>載入中…</div> : (
                <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
                  {["ERP 工作台", "物資台賬", "庫存作業", "系統管理"].map((g) => {
                    const rows = navList.filter((x) => x.group === g);
                    if (!rows.length) return null;
                    return (
                      <div key={g}>
                        <div className="eyebrow" style={{ padding: "8px 14px", background: "var(--surface-2)", fontSize: 11 }}>{g}</div>
                        {rows.map((x, i) => (
                          <div key={x.id} className="row gap-8" style={{ padding: "8px 14px", borderTop: "1px solid var(--line)", alignItems: "center", opacity: x.hidden ? 0.5 : 1 }}>
                            <div className="col gap-2" style={{ width: 18 }}>
                              <button className="btn-icon" disabled={i === 0} onClick={() => navMove(x.id, -1)} style={{ fontSize: 11, lineHeight: 1, opacity: i === 0 ? 0.3 : 1, background: "none", border: "none", cursor: "pointer" }}>▲</button>
                              <button className="btn-icon" disabled={i === rows.length - 1} onClick={() => navMove(x.id, 1)} style={{ fontSize: 11, lineHeight: 1, opacity: i === rows.length - 1 ? 0.3 : 1, background: "none", border: "none", cursor: "pointer" }}>▼</button>
                            </div>
                            <input className="input" style={{ flex: 1, height: 32, fontSize: 12.5 }} placeholder={x.default_label} value={x.label} onChange={(e) => navSetLabel(x.id, e.target.value)}/>
                            <span className="num muted" style={{ fontSize: 10.5, width: 90, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{x.id}</span>
                            <button className="btn btn-sm" disabled={x.id === "settings"} onClick={() => navToggleHidden(x.id)}
                              style={{ background: x.hidden ? "var(--surface-2)" : "var(--ok-soft)", color: x.hidden ? "var(--ink-3)" : "var(--ok)", minWidth: 56 }}>
                              {x.id === "settings" ? "必顯" : (x.hidden ? "已隱藏" : "顯示中")}
                            </button>
                          </div>
                        ))}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            <div className="col gap-8">
              <div className="row spread">
                <div style={{ fontSize: 13.5, fontWeight: 800 }}>物資台賬分類</div>
                <button className="btn btn-sm" onClick={catNew}>+ 新增分類</button>
              </div>
              <div className="muted" style={{ fontSize: 11.5, marginTop: -4 }}>每個分類自動對應一個「物資台賬」導航項與台賬頁。有數據的分類不可刪除。</div>
              {!cats ? <div className="muted" style={{ fontSize: 12 }}>載入中…</div> : cats.length === 0 ? (
                <div className="muted" style={{ fontSize: 12.5, padding: 10, background: "var(--surface-2)", borderRadius: 10 }}>暫無分類。</div>
              ) : (
                <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
                  {cats.map((c) => (
                    <div key={c.id} className="row spread" style={{ padding: "10px 14px", borderTop: "1px solid var(--line)" }}>
                      <div className="col gap-2">
                        <span style={{ fontSize: 13, fontWeight: 700 }}>{c.name} <span className="num muted" style={{ fontSize: 11 }}>/{c.id}</span></span>
                        <span className="muted" style={{ fontSize: 11 }}>{c.requires_return ? "需歸還" : "消耗"} · {c.usage_count} 項數據</span>
                      </div>
                      <div className="row gap-6">
                        <button className="btn btn-sm" onClick={() => setCatEdit({ ...c, _new: false })}>編輯</button>
                        <button className="btn btn-sm" disabled={busy || c.usage_count > 0} title={c.usage_count > 0 ? "有數據,不可刪除" : ""} style={{ color: c.usage_count > 0 ? "var(--ink-4)" : "var(--danger)" }} onClick={() => deleteCat(c)}>刪除</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="col gap-8">
              <div className="row spread">
                <div style={{ fontSize: 13.5, fontWeight: 800 }}>自定義模塊(按公司加功能)</div>
                <div className="row gap-8" style={{ alignItems: "center" }}>
                  {modMsg && <span style={{ color: "var(--ok)", fontSize: 12, fontWeight: 700 }}>{modMsg}</span>}
                  <button className="btn btn-sm" onClick={modNew}>+ 新增模塊</button>
                </div>
              </div>
              <div className="muted" style={{ fontSize: 11.5, marginTop: -4 }}>定義模塊與字段,系統自動為該公司生成側欄入口 + 增刪改查頁面 + 後端存儲。</div>
              {!modules ? <div className="muted" style={{ fontSize: 12 }}>載入中…</div> : modules.length === 0 ? (
                <div className="muted" style={{ fontSize: 12.5, padding: 10, background: "var(--surface-2)", borderRadius: 10 }}>暫無自定義模塊。</div>
              ) : (
                <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
                  {modules.map((m) => (
                    <div key={m.key} className="row spread" style={{ padding: "10px 14px", borderTop: "1px solid var(--line)" }}>
                      <div className="col gap-2">
                        <span style={{ fontSize: 13, fontWeight: 700 }}>{m.name} <span className="num muted" style={{ fontSize: 11 }}>/{m.key}</span></span>
                        <span className="muted" style={{ fontSize: 11 }}>{m.nav_group} · {(m.fields || []).length} 個字段</span>
                      </div>
                      <div className="row gap-6">
                        <button className="btn btn-sm" onClick={() => modOpen(m)}>編輯</button>
                        <button className="btn btn-sm" style={{ color: "var(--danger)" }} onClick={() => deleteModule(m)}>刪除</button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="col gap-8">
              <div style={{ fontSize: 13.5, fontWeight: 800 }}>成員({data.members.length})</div>
              <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
                  <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>{["成員", "帳號", "角色", "狀態", "操作"].map((h) => <th key={h} style={{ padding: "10px 14px", fontWeight: 700, fontSize: 11.5 }}>{h}</th>)}</tr></thead>
                  <tbody>
                    {data.members.map((m) => (
                      <tr key={m.global_user_id} style={{ borderTop: "1px solid var(--line)" }}>
                        <td style={{ padding: "10px 14px", fontWeight: 700 }}>{m.display_name}</td>
                        <td className="num muted" style={{ padding: "10px 14px" }}>@{m.username}</td>
                        <td style={{ padding: "10px 14px" }}>{m.role || "—"}</td>
                        <td style={{ padding: "10px 14px" }}><span className={`badge ${m.status === "active" ? "badge-ok" : "badge-gray"}`} style={{ height: 19 }}>{m.status}</span></td>
                        <td style={{ padding: "10px 14px" }}><button className="btn btn-sm" disabled={busy} onClick={() => resetMember(m)}>重置密碼</button></td>
                      </tr>
                    ))}
                    {data.members.length === 0 && <tr><td colSpan={5} className="muted" style={{ padding: 14, textAlign: "center" }}>暫無成員</td></tr>}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
        {resetInfo && (
          <div className="col gap-8" style={{ padding: 14, borderRadius: 12, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,.2)" }}>
            <div style={{ fontSize: 13, fontWeight: 700 }}>已重置 {resetInfo.name}(@{resetInfo.username})的密碼,臨時密碼(只顯示一次):</div>
            <div className="num" style={{ fontSize: 20, fontWeight: 800, letterSpacing: 1, textAlign: "center", padding: "10px 0", background: "var(--surface)", borderRadius: 10 }}>{resetInfo.password}</div>
          </div>
        )}
        {catEdit && (
          <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", zIndex: 60, padding: 24 }} onClick={() => setCatEdit(null)}>
            <div className="card col gap-12" style={{ width: "min(460px, 100%)", padding: 24 }} onClick={(e) => e.stopPropagation()}>
              <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>{catEdit._new ? "新增分類" : "編輯分類"}</div>
                <button onClick={() => setCatEdit(null)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, fontWeight: 700, color: "var(--ink-3)" }}>✕</button></div>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>分類名稱
                <input className="input" value={catEdit.name} onChange={(e) => setCatEdit({ ...catEdit, name: e.target.value })} placeholder="例如:備品備件"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>分類代碼(小寫字母/數字/下劃線)
                <input className="input" value={catEdit.id} disabled={!catEdit._new} onChange={(e) => setCatEdit({ ...catEdit, id: e.target.value })} placeholder="例如:spare_parts" style={!catEdit._new ? { opacity: 0.6 } : undefined}/></label>
              <label className="row gap-10" style={{ fontSize: 13, fontWeight: 700, alignItems: "center" }}>
                <input type="checkbox" checked={!!catEdit.requires_return} onChange={(e) => setCatEdit({ ...catEdit, requires_return: e.target.checked })}/>借用後需歸還(生成歸還提醒)</label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>說明
                <textarea className="input" rows={2} value={catEdit.description || ""} onChange={(e) => setCatEdit({ ...catEdit, description: e.target.value })} style={{ height: "auto", padding: 12, resize: "none" }}/></label>
              <div className="row gap-8">
                <button className="btn btn-primary" style={{ flex: 1, height: 42 }} disabled={busy} onClick={saveCat}>保存分類</button>
                <button className="btn" style={{ height: 42 }} onClick={() => setCatEdit(null)}>取消</button>
              </div>
            </div>
          </div>
        )}
        {modEdit && (
          <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.45)", zIndex: 60, padding: 24 }} onClick={() => setModEdit(null)}>
            <div className="card col gap-12" style={{ width: "min(620px, 100%)", padding: 24, maxHeight: "90vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
              <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>{modEdit.fields && modules && modules.some((m) => m.key === modEdit.key) ? "編輯模塊" : "新增模塊"}</div>
                <button onClick={() => setModEdit(null)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 16, fontWeight: 700, color: "var(--ink-3)" }}>✕</button></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <label className="col gap-6" style={{ fontSize: 12, fontWeight: 700 }}>模塊名稱
                  <input className="input" value={modEdit.name} onChange={(e) => setModEdit({ ...modEdit, name: e.target.value })} placeholder="例如:工程變更單"/></label>
                <label className="col gap-6" style={{ fontSize: 12, fontWeight: 700 }}>模塊代碼(英數)
                  <input className="input" value={modEdit.key} onChange={(e) => setModEdit({ ...modEdit, key: e.target.value })} placeholder="例如:ecn"/></label>
                <label className="col gap-6" style={{ fontSize: 12, fontWeight: 700 }}>導航分組
                  <select className="input" value={modEdit.nav_group} onChange={(e) => setModEdit({ ...modEdit, nav_group: e.target.value })}>
                    {NAV_GROUPS.map((g) => <option key={g} value={g}>{g}</option>)}</select></label>
                <label className="col gap-6" style={{ fontSize: 12, fontWeight: 700 }}>圖標(可選)
                  <input className="input" value={modEdit.icon} onChange={(e) => setModEdit({ ...modEdit, icon: e.target.value })} placeholder="layers / clipboard / box…"/></label>
              </div>
              <div className="row spread"><span style={{ fontSize: 12.5, fontWeight: 800 }}>字段</span>
                <button className="btn btn-sm" onClick={modAddField}>+ 加字段</button></div>
              <div className="col gap-8">
                {modEdit.fields.map((f, i) => (
                  <div key={i} className="col gap-6" style={{ padding: 10, borderRadius: 10, background: "var(--surface-2)" }}>
                    <div className="row gap-6" style={{ flexWrap: "wrap", alignItems: "center" }}>
                      <input className="input" style={{ flex: 1, minWidth: 110, height: 32 }} placeholder="字段名(顯示)" value={f.label} onChange={(e) => modSetField(i, { label: e.target.value })}/>
                      <input className="input" style={{ width: 110, height: 32 }} placeholder="代碼(英數)" value={f.key} onChange={(e) => modSetField(i, { key: e.target.value })}/>
                      <select className="input" style={{ width: 110, height: 32 }} value={f.type} onChange={(e) => modSetField(i, { type: e.target.value })}>
                        {FIELD_TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
                      <button type="button" className="btn btn-sm" onClick={() => modSetField(i, { required: !f.required })}
                        style={{ background: f.required ? "var(--blue)" : "var(--surface)", color: f.required ? "#fff" : "var(--ink-3)" }}>必填</button>
                      <button type="button" className="btn btn-sm" style={{ color: "var(--danger)" }} onClick={() => modDelField(i)}>✕</button>
                    </div>
                    {f.type === "select" && (
                      <input className="input" style={{ height: 32 }} placeholder="選項,用逗號分隔:設計變更, 現場變更" value={f.options} onChange={(e) => modSetField(i, { options: e.target.value })}/>
                    )}
                  </div>
                ))}
              </div>
              <div className="row gap-8">
                <button className="btn btn-primary" style={{ flex: 1, height: 42 }} disabled={busy} onClick={saveModule}>保存模塊</button>
                <button className="btn" style={{ height: 42 }} onClick={() => setModEdit(null)}>取消</button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/* ---------- 根 ---------- */
function PlatformApp() {
  const [checked, setChecked] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    pfetch("/api/platform/me")
      .then(({ data }) => { setNeedsSetup(Boolean(data.needs_setup)); if (data.authenticated) setUser(data.user); })
      .catch(() => {})
      .finally(() => setChecked(true));
  }, []);

  const logout = () => {
    pfetch("/api/platform/logout", { method: "POST" }).catch(() => {});
    setPtoken(""); setUser(null);
  };

  if (!checked) return <div className="center" style={{ minHeight: "100vh" }}><div className="card row gap-12" style={{ padding: 22, alignItems: "center" }}><img src="v2/brand/bonfire-platform-mark.png" width="38" height="38" alt=""/><div><div style={{ fontWeight: 800 }}>WAREHOUSE OS 2.0</div><div className="muted" style={{ fontSize: 11 }}>連接平台服務中…</div></div></div></div>;
  if (user) return <Console user={user} onLogout={logout}/>;

  return (
    <div className="center" style={{ minHeight: "100vh", padding: 24 }}>
      <div style={{ width: "min(420px, 100%)" }}>
        <OperatorAuth needsSetup={needsSetup} onLogin={setUser}/>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<PlatformApp/>);
