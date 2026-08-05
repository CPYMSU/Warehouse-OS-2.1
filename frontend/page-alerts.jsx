/* ============================================================
   智能預警 — 風險態勢頁
   AI 入口統一交給公司 AI 秘書；本頁只負責風險態勢、篩選、手動處置與規則可視化。
   ============================================================ */
const { useEffect: useEffectAl, useMemo: useMemoAl, useState: useStateAl } = React;
const ALERTS_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const LEVELS = {
  red:    { label: "緊急", color: "#EF4444", soft: "#FEE2E2", icon: "flame" },
  orange: { label: "需處置", color: "#F59E0B", soft: "#FEF3C7", icon: "alert" },
  yellow: { label: "需關注", color: "#EAB308", soft: "#FEF9C3", icon: "clock" },
  blue:   { label: "提示", color: "#3B82F6", soft: "#E0EDFF", icon: "trend" },
};
const LEVEL_ORDER = ["red", "orange", "yellow", "blue"];
const STATUS_LABEL = { open: "待處理", resolved: "已處理", dismissed: "已忽略", handled: "自動關閉" };

const alertLevel = (a) => LEVELS[a && a.level] || LEVELS.blue;
const alertSource = (s) => s === "risk_engine" ? "智能引擎" : (s || "人工/歷史");
const alertDate = (v) => v ? String(v).replace("T", " ").slice(0, 16) : "—";
const fmtNum = (v, suffix = "") => {
  if (v == null || v === "") return "—";
  const n = Number(v);
  return Number.isFinite(n) ? `${n.toLocaleString("zh-CN", { maximumFractionDigits: 2 })}${suffix}` : String(v);
};
const compact = (v, max = 200) => {
  if (v == null || v === "") return "—";
  const t = typeof v === "object" ? JSON.stringify(v) : String(v);
  return t.length > max ? t.slice(0, max) + "…" : t;
};
const evidenceRows = (e) => Object.entries(e || {}).filter(([, v]) => v != null && v !== "").slice(0, 14);
const matchText = (a) => [a.id, a.riskCategory, a.level, a.type, a.item, a.code, a.scope, a.suggest].filter(Boolean).join(" ").toLowerCase();

const alertsRequest = (path, options = {}) => {
  const url = window.authFetch ? path : `${ALERTS_API_BASE}${path}`;
  return (window.authFetch || fetch)(url, options);
};
const readJson = (res, msg) => res.json().catch(() => ({})).then((d) => { if (!res.ok) throw new Error(d.error || msg || `HTTP ${res.status}`); return d; });

const SECRETARY_PROMPTS = [
  "分析當前智能預警風險態勢，給出今天優先處理順序",
  "只看紅色高危和超時未處理預警，列出處理建議",
  "檢查超期借用相關預警，判斷哪些需要催還或標記處理",
  "說明目前預警規則和可調整的閾值",
  "幫我設計一個新的 KPI 越界監控",
];
const EMPTY_SUMMARY = { levels: {}, categories: [], criticalCount: 0, hiddenCount: 0, open: 0 };

const riskVerdict = (levels, mineOpen) => {
  const red = levels.red || 0, orange = levels.orange || 0;
  if (red >= 5) return { word: "嚴重", color: "#EF4444" };
  if (red >= 1 || orange >= 8) return { word: "偏高", color: "#F59E0B" };
  if (mineOpen > 0) return { word: "需關注", color: "#EAB308" };
  return { word: "良好", color: "#10B981" };
};

const PageAlerts = ({ go } = {}) => {
  const [alerts, setAlerts] = useStateAl([]);
  const [critical, setCritical] = useStateAl([]);
  const [hidden, setHidden] = useStateAl([]);
  const [summary, setSummary] = useStateAl(EMPTY_SUMMARY);
  const [briefing, setBriefing] = useStateAl(null);
  const [rulesOpen, setRulesOpen] = useStateAl(false);
  const [rules, setRules] = useStateAl(null);
  const [kpi, setKpi] = useStateAl(null);
  const [canSeeAll, setCanSeeAll] = useStateAl(false);
  const [view, setView] = useStateAl({});               // {level, category, keyword, ids}
  const [selected, setSelected] = useStateAl(null);     // 詳情抽屜
  const [showAll, setShowAll] = useStateAl(false);
  const [density, setDensity] = useStateAl("auto");   // auto | card | table
  const [sortKey, setSortKey] = useStateAl("severity"); // severity | due | category | time
  const [groupBy, setGroupBy] = useStateAl("none");   // none | level | category
  const [collapsed, setCollapsed] = useStateAl({});   // {groupKey:true}
  const [loading, setLoading] = useStateAl(true);
  const [scanning, setScanning] = useStateAl(false);
  const [actionId, setActionId] = useStateAl("");
  const [error, setError] = useStateAl("");

  const loadAlerts = (silent) => {
    if (!silent) setLoading(true);
    setError("");
    return alertsRequest("/api/alerts?status=open&limit=1000")
      .then((res) => readJson(res, "預警載入失敗"))
      .then((d) => {
        setAlerts(d.mine || d.alerts || []); setCritical(d.critical || []); setHidden(d.hidden || []);
        setSummary({ ...EMPTY_SUMMARY, ...(d.summary || {}) }); setCanSeeAll(!!d.canSeeAll);
        window.ALERTS = d.mine || [];
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false));
  };
  const loadBriefing = () => alertsRequest("/api/alerts/briefing").then((res) => readJson(res, "簡報載入失敗")).then(setBriefing).catch(() => {});
  const loadRules = () => alertsRequest("/api/alerts/rules").then((res) => readJson(res, "規則載入失敗")).then(setRules).catch(() => {});
  const resetRule = (key) => alertsRequest("/api/alerts/rules/apply", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reset: [key] }) })
    .then((res) => readJson(res, "恢復失敗")).then(() => { loadRules(); refreshAll(); }).catch((e) => setError(e.message || String(e)));
  const loadKpi = () => alertsRequest("/api/alerts/kpi").then((res) => readJson(res, "KPI 載入失敗")).then(setKpi).catch(() => {});
  const removeKpi = (id) => alertsRequest("/api/alerts/kpi/apply", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ remove: id }) })
    .then((res) => readJson(res, "移除失敗")).then(() => { loadKpi(); refreshAll(); }).catch((e) => setError(e.message || String(e)));

  const refreshAll = () => { loadAlerts(true); loadBriefing(); if (window.reloadData) window.reloadData(); };

  useEffectAl(() => {
    loadAlerts(false); loadBriefing();
    if (window.ALERTS_FOCUS_KEYWORD) { setView({ keyword: window.ALERTS_FOCUS_KEYWORD }); window.ALERTS_FOCUS_KEYWORD = null; }
  }, []);
  useEffectAl(() => {
    const onFocus = (event) => {
      const v = event.detail || {};
      setView({ level: v.level || "", category: v.category || "", keyword: v.keyword || "", ids: v.alert_ids || v.ids || null });
    };
    const onChanged = () => refreshAll();
    window.addEventListener("alerts-agent-focus-view", onFocus);
    window.addEventListener("alerts-agent-changed", onChanged);
    return () => {
      window.removeEventListener("alerts-agent-focus-view", onFocus);
      window.removeEventListener("alerts-agent-changed", onChanged);
    };
  }, []);

  const filtered = useMemoAl(() => {
    const k = (view.keyword || "").toLowerCase();
    const ids = view.ids && view.ids.length ? new Set(view.ids) : null;
    return alerts.filter((a) => {
      if (view.level && (a.level || "blue") !== view.level) return false;
      if (view.category && view.category !== "全部" && (a.riskCategory || "通用風險") !== view.category) return false;
      if (ids && !ids.has(a.id)) return false;
      if (k && !matchText(a).includes(k)) return false;
      return true;
    });
  }, [alerts, view]);

  const sorted = useMemoAl(() => {
    const arr = filtered.slice();
    const lv = (a) => ({ red: 0, orange: 1, yellow: 2, blue: 3 }[a.level || "blue"]);
    const cmp = {
      severity: (a, b) => lv(a) - lv(b) || (b.severity || 0) - (a.severity || 0),
      due: (a, b) => (a.dueAt || "9999").localeCompare(b.dueAt || "9999"),
      category: (a, b) => String(a.riskCategory || "").localeCompare(String(b.riskCategory || "")) || lv(a) - lv(b),
      time: (a, b) => String(b.updatedAt || b.at || "").localeCompare(String(a.updatedAt || a.at || "")),
    }[sortKey] || (() => 0);
    return arr.sort(cmp);
  }, [filtered, sortKey]);

  const levels = summary.levels || {};
  const verdict = riskVerdict(levels, alerts.length);
  const viewActive = !!(view.level || view.category || view.keyword || (view.ids && view.ids.length));
  const effDensity = density === "auto" ? (sorted.length > 12 ? "table" : "card") : density;

  const riskContext = () => {
    const cats = (summary.categories || []).slice(0, 4).map((c) => `${c.name}${c.count}`).join("、") || "暫無";
    const focus = viewActive ? `當前聚焦:${view.level || view.category || view.keyword || "指定預警"}` : "當前未聚焦";
    return `智能預警頁上下文:待處理${alerts.length}條,紅色${levels.red || 0}條,橙色${levels.orange || 0}條,高危兜底${summary.criticalCount || 0}條,主要類別:${cats};${focus}。`;
  };

  const openSecretary = (prompt) => {
    const q = (prompt || SECRETARY_PROMPTS[0]).trim();
    const full = `${riskContext()}\n\n${q}`;
    if (window.openUnifiedAgent) window.openUnifiedAgent(full, { autoAsk: true });
    else window.dispatchEvent(new CustomEvent("company-secretary-open", { detail: { prompt: full, autoAsk: true } }));
  };

  const handleAlert = (a, action) => {
    if (!a || !a.id || actionId) return;
    setActionId(a.id);
    alertsRequest(`/api/alerts/${encodeURIComponent(a.id)}/${action}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((res) => readJson(res, "操作失敗")).then(() => { setSelected(null); refreshAll(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setActionId(""));
  };

  const scan = () => {
    if (scanning) return; setScanning(true); setError("");
    alertsRequest("/api/alerts/scan", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((res) => readJson(res, "掃描失敗")).then(() => refreshAll())
      .catch((e) => setError(e.message || String(e))).finally(() => setScanning(false));
  };

  return (
    <div className="risk-page">
      <div className="risk-topbar">
        <div><div className="risk-title">智能預警</div><div className="risk-sub">{canSeeAll ? "全部風險可見" : "僅顯示你負責的;紅色高危始終可見"}</div></div>
        <div className="row gap-8">
          <button className="btn btn-sm" onClick={() => { setRulesOpen(true); loadRules(); loadKpi(); }}><Icon name="shield" size={14}/>預警規則</button>
          <button className="btn btn-sm" onClick={() => { loadAlerts(false); loadBriefing(); }} disabled={loading}><Icon name="refresh" size={14}/>刷新</button>
          <button className="btn btn-sm" onClick={scan} disabled={scanning}><Icon name="scan" size={14}/>{scanning ? "掃描中" : "掃描"}</button>
        </div>
      </div>
      {error && <div className="risk-err"><Icon name="alert" size={15}/>{error}</div>}

      <div className="risk-grid">
        {/* ===== 左:風險態勢畫布 ===== */}
        <div className="risk-canvas">
          {/* Hero */}
          <div className="risk-hero card">
            <div className="risk-hero-l">
              <div className="risk-hero-eyebrow">整體風險態勢</div>
              <div className="risk-hero-word" style={{ color: verdict.color }}>{verdict.word}</div>
              <div className="risk-hero-line">{briefing ? briefing.oneLiner : `你有 ${alerts.length} 條風險待處理。`}</div>
            </div>
            <div className="risk-hero-r">
              <div className="risk-hero-big" style={{ color: verdict.color }}>{alerts.length}</div>
              <div className="risk-hero-cap">需我處理</div>
              {briefing && briefing.todayNew > 0 && <div className="risk-today">今日新增 {briefing.todayNew}</div>}
            </div>
          </div>

          {/* 態勢圖表(點圖例可篩選) */}
          <div className="risk-sec risk-list-head" style={{ marginBottom: 0 }}>
            態勢概覽
            {viewActive && <button className="risk-clear" onClick={() => { setView({}); setShowAll(false); }}>清除聚焦 ✕</button>}
          </div>
          <div className="risk-charts">
            <SeverityDonut levels={levels} total={alerts.length} active={view.level}
              crit={summary.criticalCount} hidden={summary.hiddenCount}
              onPick={(lv) => setView(view.level === lv ? {} : { level: lv })}/>
            <CategoryDonut cats={summary.categories || []} active={view.category}
              onPick={(name) => setView(view.category === name ? {} : { category: name })}/>
            <TrendChart data={(briefing && briefing.trend) || []}/>
            <HandleProgress handled7d={briefing ? briefing.handled7d : 0} open={alerts.length} handledToday={briefing ? briefing.handledToday : 0}/>
          </div>

          {/* 紅色高危兜底 */}
          {critical.length > 0 && (
            <div className="risk-critical card">
              <div className="risk-sec" style={{ color: "#B91C1C" }}>🔴 紅色高危(需相關負責人 · {critical.length})</div>
              <div className="risk-critical-list">
                {critical.slice(0, 6).map((c) => (
                  <div key={c.id} className="risk-critical-item"><b>{c.item}</b> · {c.type} <span className="muted">— {c.owner}</span></div>
                ))}
                {critical.length > 6 && <div className="muted" style={{ fontSize: 11.5 }}>還有 {critical.length - 6} 條…</div>}
              </div>
            </div>
          )}

          {/* 預警卡流 */}
          <div className="risk-listbar">
            <div className="risk-listbar-l">{viewActive ? "聚焦結果" : "預警"} · <b>{sorted.length}</b> 條</div>
            <div className="risk-listbar-r">
              <div className="risk-seg">
                <button className={effDensity === "card" ? "on" : ""} onClick={() => setDensity("card")}>卡片</button>
                <button className={effDensity === "table" ? "on" : ""} onClick={() => setDensity("table")}>表格</button>
              </div>
              <select className="risk-select" value={sortKey} onChange={(e) => setSortKey(e.target.value)} title="排序">
                <option value="severity">嚴重度</option><option value="due">到期</option>
                <option value="category">類別</option><option value="time">時間</option>
              </select>
              <select className="risk-select" value={groupBy} onChange={(e) => setGroupBy(e.target.value)} title="分組">
                <option value="none">不分組</option><option value="level">按嚴重度</option><option value="category">按類別</option><option value="item">按物資</option>
              </select>
            </div>
          </div>
          {loading ? <div className="risk-empty card"><Icon name="refresh" size={22} color="var(--ink-4)"/><span>載入中…</span></div>
            : sorted.length === 0 ? (
              <div className="risk-empty card">
                <Icon name="checkCircle" size={30} color="var(--ok)"/>
                <span style={{ fontWeight: 800, fontSize: 15 }}>{alerts.length ? "此聚焦下沒有預警" : "你負責的範圍內暫無預警 ✓"}</span>
                <span className="muted" style={{ fontSize: 12 }}>{viewActive ? "可清除聚焦，或交給公司 AI 秘書重新收窄。" : (summary.criticalCount ? `但全局有 ${summary.criticalCount} 條紅色高危見上方。` : "")}</span>
              </div>
            ) : (
              <AlertList items={sorted} density={effDensity} groupBy={groupBy}
                collapsed={collapsed} onToggle={(k) => setCollapsed((c) => ({ ...c, [k]: !c[k] }))}
                onSelect={setSelected}/>
            )}
        </div>

        {/* ===== 右:公司 AI 秘書 ===== */}
        <div className="risk-copilot card">
          <div className="risk-cop-head">
            <span className="row gap-8" style={{ alignItems: "center" }}><Icon name="sparkle" size={18} color="var(--blue)"/><b style={{ fontSize: 15 }}>公司 AI 秘書</b></span>
            <button className="btn btn-primary btn-sm" onClick={() => openSecretary()}><Icon name="arrow" size={14}/>打開</button>
          </div>
          <div className="risk-cop-chat">
            <div className="risk-cop-hello">
              <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.65 }}>
                智能預警的問答、查詢、批量處置和修復建議都進入公司 AI 秘書。
              </div>
              {SECRETARY_PROMPTS.map((c) => <button key={c} className="risk-cop-chip" onClick={() => openSecretary(c)}>{c}</button>)}
            </div>
            <div className="risk-evidence" style={{ margin: "12px 12px 0" }}>
              <div><span>待處理</span><b className="num">{alerts.length}</b></div>
              <div><span>紅色</span><b className="num">{levels.red || 0}</b></div>
              <div><span>橙色</span><b className="num">{levels.orange || 0}</b></div>
              <div><span>高危兜底</span><b className="num">{summary.criticalCount || 0}</b></div>
            </div>
          </div>
        </div>
      </div>

      {selected && <DetailDrawer alert={selected} busy={!!actionId} onClose={() => setSelected(null)} onResolve={() => handleAlert(selected, "resolve")} onDismiss={() => handleAlert(selected, "dismiss")} onAsk={(q) => { setSelected(null); openSecretary(q); }} onViewInventory={go ? ((a) => { window.INVENTORY_FOCUS = a.item; go("inventory"); }) : null}/>}
      {rulesOpen && <RulesDrawer data={rules} kpi={kpi} alerts={alerts} onClose={() => setRulesOpen(false)} onAsk={(q) => { setRulesOpen(false); openSecretary(q); }} onReset={resetRule} onRemoveKpi={removeKpi} onSelectAlert={(a) => { setRulesOpen(false); setSelected(a); }}/>}
    </div>
  );
};

const DetailDrawer = ({ alert, busy, onClose, onResolve, onDismiss, onAsk, onViewInventory }) => {
  const L = alertLevel(alert);
  const rows = evidenceRows(alert.evidence);
  const actions = Array.isArray(alert.actions) ? alert.actions : [];
  const isOpen = (alert.status || "open") === "open";
  return (
    <div className="risk-drawer-mask" onClick={onClose}>
      <div className="risk-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="risk-drawer-head" style={{ background: L.soft }}>
          <div className="row gap-10" style={{ alignItems: "center" }}>
            <div className="risk-drawer-icon" style={{ background: L.color }}><Icon name={L.icon} size={18} color="#fff"/></div>
            <div><div style={{ fontSize: 16, fontWeight: 800 }}>{alert.item}</div><div className="num muted" style={{ fontSize: 12 }}>{alert.type} · {alert.riskCategory}</div></div>
          </div>
          <button className="btn btn-sm" onClick={onClose}><Icon name="x" size={16}/></button>
        </div>
        <div className="risk-drawer-body">
          {alert.escalated && <div className="risk-esc-banner">⚠ 已超時 {alert.ageDays} 天未處理 —— 建議盡快處理或升級給負責人。</div>}
          {(alert.why || []).length > 0 && (
            <div className="risk-why">
              <span className="risk-why-label">為什麼嚴重</span>
              {alert.why.map((w, i) => <span key={i} className="risk-why-tag">{w}</span>)}
              <span className="risk-why-score">嚴重度 {alert.severity == null ? "—" : Math.round(alert.severity)}</span>
            </div>
          )}
          <div className="risk-kpis">
            <div><span>當前數量</span><b className="num">{fmtNum(alert.stock)}</b></div>
            <div><span>參考閾值</span><b className="num">{fmtNum(alert.safe)}</b></div>
            <div><span>支撐天數</span><b className="num">{alert.days == null ? "—" : fmtNum(alert.days, " 天")}</b></div>
            <div><span>到期/截止</span><b className="num">{alertDate(alert.dueAt)}</b></div>
          </div>
          <div className="risk-drawer-sug">{alert.suggest}</div>
          {onViewInventory && alert.itemId && (
            <button className="risk-inv-link" onClick={() => onViewInventory(alert)}>
              <Icon name="pkg" size={14}/>在庫存中查看此物資<Icon name="arrow" size={13}/>
            </button>
          )}
          {!!rows.length && (
            <div className="risk-drawer-sec"><div className="eyebrow">證據數據</div>
              <div className="risk-evidence">{rows.map(([k, v]) => <div key={k}><span>{k}</span><b className="num">{compact(v, 160)}</b></div>)}</div>
            </div>
          )}
          {!!actions.length && (
            <div className="risk-drawer-sec"><div className="eyebrow">建議動作(交給公司 AI 秘書)</div>
              <div className="row gap-6" style={{ flexWrap: "wrap" }}>
                {actions.map((a) => <button key={a} className="risk-cop-chip" onClick={() => onAsk(`針對「${alert.item}」(${alert.id}):${a}`)}>{a}</button>)}
              </div>
            </div>
          )}
          <div className="risk-drawer-sec"><div className="eyebrow">關聯</div>
            <div className="risk-evidence">
              <div><span>預警編號</span><b className="num">{alert.id}</b></div>
              <div><span>來源</span><b>{alertSource(alert.source)}</b></div>
              <div><span>狀態</span><b>{STATUS_LABEL[alert.status] || alert.status}</b></div>
              <div><span>更新</span><b className="num">{alertDate(alert.updatedAt || alert.at)}</b></div>
            </div>
          </div>
        </div>
        {isOpen && (
          <div className="risk-drawer-foot">
            <button className="btn btn-primary" disabled={busy} onClick={onResolve}><Icon name="check" size={15}/>{busy ? "處理中" : "標記已處理"}</button>
            <button className="btn" disabled={busy} onClick={onDismiss}><Icon name="x" size={15}/>忽略</button>
            <button className="btn" onClick={() => onAsk(`處理這條:${alert.item}(${alert.id})`)}><Icon name="sparkle" size={15}/>交給秘書</button>
          </div>
        )}
      </div>
    </div>
  );
};

// 預警規則抽屜:透明化(只讀)+ 行業模板分層 + 引導用 AI 修改
const whOf = (s) => { if (!s) return "未分庫"; const t = String(s).split(/[·;,，]/)[0].trim(); return t.split(/\s+/)[0] || "未分庫"; };
const RuleCard = ({ r, alerts, onAsk, onReset, onSelectAlert }) => {
  const [open, setOpen] = useStateAl(false);
  const triggered = (alerts || []).filter((a) => (a.riskCategory || "通用風險") === r.category);
  const byWh = [];
  triggered.forEach((a) => { const w = whOf(a.scope); let g = byWh.find((x) => x.wh === w); if (!g) { g = { wh: w, items: [] }; byWh.push(g); } g.items.push(a); });
  byWh.forEach((g) => g.items.sort((a, b) => (b.severity || 0) - (a.severity || 0)));
  return (
    <div className="rules-card">
      <div className="rules-card-head">
        <span className="row gap-8" style={{ alignItems: "center" }}>
          <Icon name={r.icon || "alert"} size={16} color="var(--blue)"/>
          <b style={{ fontSize: 14 }}>{r.category}</b>
          <span className={`rules-pill ${r.enabled ? "on" : "off"}`}>{r.enabled ? "啟用中" : "已停用"}</span>
          {r.customized && <span className="rules-pill cust">已自定義</span>}
        </span>
        <span className="num muted" style={{ fontSize: 11.5 }}>{r.coverage != null ? `在管 ${r.coverage} · ` : ""}已觸發 {r.openCount}</span>
      </div>
      <div className="rules-what">{r.what}</div>
      <div className="rules-conds">{r.conditions.map((c, i) => <div key={i} className="rules-cond">{c}</div>)}</div>
      {(r.fields || []).length > 0 && (
        <div className="rules-fields">
          {r.fields.map((f) => <span key={f.field} className="rules-field"><span>{f.label}</span><b className="num">{f.value}{f.unit || ""}</b></span>)}
        </div>
      )}
      {triggered.length > 0 && (
        <button className="rules-drill" onClick={() => setOpen((v) => !v)}>
          <Icon name={open ? "chevronDown" : "chevronRight"} size={13}/>{open ? "收起貨物明細" : `查看受影響貨物 (${triggered.length})`}
        </button>
      )}
      {open && (
        <div className="rules-drill-body">
          {byWh.map((g) => (
            <div key={g.wh} className="rules-wh">
              <div className="rules-wh-title"><Icon name="box" size={12} color="var(--ink-3)"/>{g.wh}<span className="num">{g.items.length}</span></div>
              {g.items.map((a) => {
                const L = alertLevel(a);
                return (
                  <button key={a.id} className="rules-wh-row" onClick={() => onSelectAlert(a)}>
                    <span className="rules-wh-dot" style={{ background: L.color }}/>
                    <span className="rules-wh-item" title={a.item}>{a.escalated && <span style={{ color: "#B91C1C" }}>⚠ </span>}{a.item}</span>
                    <span className="muted" style={{ fontSize: 11, flex: "0 0 auto" }}>{a.type}</span>
                    <span className="num" style={{ color: L.color, fontWeight: 800, flex: "0 0 auto" }}>{a.severity == null ? "—" : Math.round(a.severity)}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      )}
      <div className="rules-card-foot">
        <span className="muted" style={{ fontSize: 11 }}>負責:{r.owner}</span>
        <span className="row gap-8">
          {r.customized && r.canEdit && <button className="rules-reset" onClick={() => onReset(r.key)}><Icon name="refresh" size={12}/>恢復行業默認</button>}
          {r.canEdit && <button className="rules-edit" onClick={() => onAsk(`我想調整「${r.category}」的預警規則`)}><Icon name="sparkle" size={12}/>讓秘書改</button>}
        </span>
      </div>
    </div>
  );
};

const KpiLevel = { red: "#EF4444", orange: "#F59E0B", yellow: "#EAB308" };
const RulesDrawer = ({ data, kpi, alerts, onClose, onAsk, onReset, onRemoveKpi, onSelectAlert }) => {
  const rules = (data && data.rules) || [];
  const kpiRules = (kpi && kpi.rules) || [];
  const groups = [];
  rules.forEach((r) => {
    let g = groups.find((x) => x.label === r.domainLabel);
    if (!g) { g = { label: r.domainLabel, items: [] }; groups.push(g); }
    g.items.push(r);
  });
  return (
    <div className="risk-drawer-mask" onClick={onClose}>
      <div className="risk-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="risk-drawer-head" style={{ background: "var(--blue-soft)" }}>
          <div className="row gap-10" style={{ alignItems: "center" }}>
            <div className="risk-drawer-icon" style={{ background: "var(--blue)" }}><Icon name="shield" size={18} color="#fff"/></div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 800 }}>預警規則</div>
              <div className="muted" style={{ fontSize: 12 }}>行業模板:{(data && data.templateName) || "—"} · 共 {rules.length} 類</div>
            </div>
          </div>
          <button className="btn btn-sm" onClick={onClose}><Icon name="x" size={16}/></button>
        </div>
        <div className="risk-drawer-body">
          <div className="rules-aibar">
            <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.6 }}>規則隨<b>行業模板</b>自動配置;想改?<b>交給公司 AI 秘書</b>,例如:</div>
            <div className="row gap-6" style={{ flexWrap: "wrap", marginTop: 8 }}>
              {["效期提前 45 天就提醒我", "借用超 5 天才算紅色", "關閉資料品質預警"].map((s) => (
                <button key={s} className="risk-cop-chip" onClick={() => onAsk(s)}>{s}</button>
              ))}
            </div>
          </div>
          {/* 自定義 KPI 指標監控 */}
          {kpi && kpi.canUse && (
            <div className="rules-group">
              <div className="rules-group-title">自訂指標監控 (KPI)<span className="num">{kpiRules.length}</span></div>
              <div className="kpi-hint">任意指標設上下限即報警。交給公司 AI 秘書即可新增,例如:
                <div className="row gap-6" style={{ flexWrap: "wrap", marginTop: 6 }}>
                  {["現金低於 50 萬提醒我", "逾期應收超過 100 萬報警", "未處理預警超過 20 條提醒"].map((s) => (
                    <button key={s} className="risk-cop-chip" onClick={() => onAsk(s)}>{s}</button>
                  ))}
                </div>
              </div>
              {kpiRules.map((k) => (
                <div key={k.id} className="kpi-card">
                  <span className="kpi-dot" style={{ background: KpiLevel[k.level] || "#F59E0B" }}/>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)" }}>{k.label || k.metricLabel}</div>
                    <div className="num" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                      當 {k.metricLabel} {k.opSym} {k.threshold}{k.unit} · 當前 {k.value == null ? "—" : k.value}{k.unit}
                    </div>
                  </div>
                  {k.canEdit && <button className="kpi-del" onClick={() => onRemoveKpi(k.id)} title="移除"><Icon name="x" size={13}/></button>}
                </div>
              ))}
              {kpiRules.length === 0 && <div className="muted" style={{ fontSize: 11.5, padding: "2px 2px 4px" }}>還沒有自定義監控。</div>}
            </div>
          )}

          {!data && <div className="muted" style={{ fontSize: 12, padding: 12 }}>載入中…</div>}
          {groups.map((g) => (
            <div key={g.label} className="rules-group">
              <div className="rules-group-title">{g.label}<span className="num">{g.items.length}</span></div>
              {g.items.map((r) => <RuleCard key={r.key} r={r} alerts={alerts} onAsk={onAsk} onReset={onReset} onSelectAlert={onSelectAlert}/>)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ===== 預警列表:卡片網格 / 虛擬表格 / 分組折疊 =====
const CardGrid = ({ items, onSelect }) => {
  const CAP = 80;
  const show = items.slice(0, CAP);
  return (
    <div className="risk-cardgrid">
      {show.map((a) => {
        const L = alertLevel(a);
        return (
          <button key={a.id} className="risk-card" style={{ borderLeftColor: L.color }} onClick={() => onSelect(a)}>
            <div className="risk-card-dot" style={{ background: L.soft, color: L.color }}><Icon name={L.icon} size={16}/></div>
            <div className="risk-card-body">
              <div className="risk-card-title"><span>{a.item}</span><span className="risk-tag" style={{ color: L.color, background: L.soft }}>{a.type}</span>{a.escalated && <span className="risk-esc">⚠ 超時 {a.ageDays}天</span>}</div>
              <div className="risk-card-sug">{a.suggest}</div>
              <div className="risk-card-meta num">{a.riskCategory} · {a.scope}</div>
            </div>
            <div className="risk-card-score" style={{ color: L.color }}>{a.severity == null ? "—" : Math.round(a.severity)}</div>
          </button>
        );
      })}
      {items.length > CAP && <div className="risk-more">還有 {items.length - CAP} 條,切「表格」視圖或交給公司 AI 秘書收窄條件查看。</div>}
    </div>
  );
};

const TableHead = () => (
  <div className="risk-trow risk-thead">
    <span className="c-lvl"/><span className="c-item">物資</span><span className="c-cat">類別</span>
    <span className="c-sev">嚴重</span><span className="c-due">到期</span><span className="c-type">類型</span>
  </div>
);
const tableRow = (a, onSelect, style) => {
  const L = alertLevel(a);
  return (
    <button key={a.id} className="risk-trow" style={style} onClick={() => onSelect(a)}>
      <span className="c-lvl"><span className="risk-leg-dot" style={{ background: L.color }}/></span>
      <span className="c-item" title={a.item}>{a.escalated && <span title={`超時 ${a.ageDays} 天未處理`} style={{ color: "#B91C1C" }}>⚠ </span>}{a.item}</span>
      <span className="c-cat">{a.riskCategory}</span>
      <span className="c-sev num" style={{ color: L.color, fontWeight: 800 }}>{a.severity == null ? "—" : Math.round(a.severity)}</span>
      <span className="c-due num">{a.dueAt ? String(a.dueAt).slice(0, 10) : "—"}</span>
      <span className="c-type">{a.type}</span>
    </button>
  );
};

const VirtualTable = ({ items, onSelect }) => {
  const ROW = 44, MAXH = 560, OVER = 6;
  const [st, setSt] = useStateAl(0);
  const total = items.length;
  const viewH = Math.min(MAXH, Math.max(ROW * 2, total * ROW));
  const start = Math.max(0, Math.floor(st / ROW) - OVER);
  const end = Math.min(total, Math.ceil((st + viewH) / ROW) + OVER);
  const slice = items.slice(start, end);
  return (
    <div className="risk-table card">
      <TableHead/>
      <div className="risk-tbody" style={{ height: viewH }} onScroll={(e) => setSt(e.target.scrollTop)}>
        <div style={{ height: total * ROW, position: "relative" }}>
          {slice.map((a, i) => tableRow(a, onSelect, { position: "absolute", left: 0, right: 0, top: (start + i) * ROW, height: ROW }))}
        </div>
      </div>
    </div>
  );
};

const CappedTable = ({ items, onSelect }) => {
  const CAP = 100;
  const show = items.slice(0, CAP);
  return (
    <div className="risk-table card">
      <TableHead/>
      <div>{show.map((a) => tableRow(a, onSelect, { height: 44 }))}</div>
      {items.length > CAP && <div className="risk-more">還有 {items.length - CAP} 條,收起其他組或用公司 AI 秘書收窄。</div>}
    </div>
  );
};

const AlertList = ({ items, density, groupBy, collapsed, onToggle, onSelect }) => {
  const Body = ({ arr, grouped }) => density === "table"
    ? (grouped ? <CappedTable items={arr} onSelect={onSelect}/> : <VirtualTable items={arr} onSelect={onSelect}/>)
    : <CardGrid items={arr} onSelect={onSelect}/>;
  if (groupBy === "none") return <Body arr={items}/>;
  let groups;
  if (groupBy === "level") {
    groups = LEVEL_ORDER.map((lv) => ({ key: lv, label: LEVELS[lv].label, color: LEVELS[lv].color, items: items.filter((a) => (a.level || "blue") === lv) })).filter((g) => g.items.length);
  } else if (groupBy === "item") {
    const m = new Map();
    items.forEach((a) => { const it = a.item || "—"; if (!m.has(it)) m.set(it, []); m.get(it).push(a); });
    groups = [...m.entries()].sort((a, b) => b[1].length - a[1].length).map(([k, v]) => ({ key: k, label: k, color: alertLevel(v[0]).color, items: v }));
  } else {
    const m = new Map();
    items.forEach((a) => { const c = a.riskCategory || "通用風險"; if (!m.has(c)) m.set(c, []); m.get(c).push(a); });
    groups = [...m.entries()].map(([k, v], i) => ({ key: k, label: k, color: CAT_COLORS[i % CAT_COLORS.length], items: v }));
  }
  return (
    <div className="risk-groups">
      {groups.map((g) => (
        <div key={g.key} className="risk-group card">
          <button className="risk-group-head" onClick={() => onToggle(g.key)}>
            <span className="risk-leg-dot" style={{ background: g.color }}/>
            <b>{g.label}</b><span className="num risk-group-n">{g.items.length}</span>
            <span className="risk-group-caret">{collapsed[g.key] ? "▸" : "▾"}</span>
          </button>
          {!collapsed[g.key] && <div className="risk-group-body"><Body arr={g.items} grouped/></div>}
        </div>
      ))}
    </div>
  );
};

// ===== 態勢圖表(純 SVG,不引圖表庫)=====
const CAT_COLORS = ["#1B6BFF", "#07B6A2", "#F59E0B", "#8B5CF6", "#EF4444", "#0EA5E9", "#10B981", "#EAB308"];

const DonutChart = ({ title, segments, centerBig, centerSub, footer }) => {
  const data = (segments || []).filter((s) => s.value > 0);
  const total = data.reduce((a, s) => a + s.value, 0) || 1;
  const S = 116, st = 15, r = (S - st) / 2, C = 2 * Math.PI * r;
  let acc = 0;
  return (
    <div className="risk-chart card">
      <div className="risk-chart-title">{title}</div>
      <div className="risk-chart-body">
        <div className="risk-donut" style={{ width: S, height: S }}>
          <svg width={S} height={S}>
            <circle cx={S / 2} cy={S / 2} r={r} fill="none" stroke="var(--line)" strokeWidth={st}/>
            {data.map((s, i) => {
              const frac = s.value / total;
              const el = <circle key={i} cx={S / 2} cy={S / 2} r={r} fill="none" stroke={s.color} strokeWidth={st}
                strokeDasharray={`${C * frac} ${C * (1 - frac)}`} strokeDashoffset={-C * acc}
                transform={`rotate(-90 ${S / 2} ${S / 2})`}/>;
              acc += frac;
              return el;
            })}
          </svg>
          <div className="risk-donut-center"><b>{centerBig}</b><span>{centerSub}</span></div>
        </div>
        <div className="risk-donut-legend">
          {(segments || []).map((s, i) => (
            <button key={i} className={`risk-leg ${s.active ? "on" : ""}`} onClick={s.onClick} disabled={!s.onClick} style={{ cursor: s.onClick ? "pointer" : "default" }}>
              <span className="risk-leg-dot" style={{ background: s.color }}/><span className="risk-leg-name">{s.label}</span><span className="num risk-leg-v">{s.value}</span>
            </button>
          ))}
        </div>
      </div>
      {footer && <div className="risk-chart-foot">{footer}</div>}
    </div>
  );
};

const SeverityDonut = ({ levels, total, active, crit, hidden, onPick }) => (
  <DonutChart title="嚴重度分布"
    centerBig={total} centerSub="待處理"
    segments={LEVEL_ORDER.map((lv) => ({ label: LEVELS[lv].label, value: levels[lv] || 0, color: LEVELS[lv].color, active: active === lv, onClick: () => onPick(lv) }))}
    footer={`共 ${total} 條${crit ? ` · 紅色高危 ${crit}` : ""}${hidden ? ` · 其他類別 ${hidden}` : ""}`}/>
);

const CategoryDonut = ({ cats, active, onPick }) => {
  const totalc = (cats || []).reduce((a, c) => a + c.count, 0);
  return (
    <DonutChart title="風險類別分布"
      centerBig={(cats || []).length} centerSub="個類別"
      segments={(cats || []).map((c, i) => ({ label: c.name, value: c.count, color: CAT_COLORS[i % CAT_COLORS.length], active: active === c.name, onClick: () => onPick(c.name) }))}
      footer={totalc ? `合計 ${totalc} 條` : "暫無"}/>
  );
};

const TrendChart = ({ data }) => {
  const d = (data || []).slice();
  const maxV = Math.max(1, ...d.map((x) => Math.max(x.new || 0, x.handled || 0)));
  const W = 240, H = 84, pad = 8;
  const xs = (i) => d.length > 1 ? pad + i * (W - 2 * pad) / (d.length - 1) : W / 2;
  const ys = (v) => H - pad - ((v || 0) / maxV) * (H - 2 * pad);
  const line = (k) => d.map((x, i) => `${xs(i).toFixed(1)},${ys(x[k]).toFixed(1)}`).join(" ");
  const last = d[d.length - 1] || { new: 0, handled: 0 };
  return (
    <div className="risk-chart card">
      <div className="risk-chart-title">近 7 天態勢</div>
      <div className="risk-chart-body" style={{ justifyContent: "center", minHeight: 116 }}>
        {d.length ? (
          <svg width="100%" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ maxWidth: 260 }}>
            <polyline fill="none" stroke="#EF4444" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" points={line("new")}/>
            <polyline fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" points={line("handled")}/>
          </svg>
        ) : <span className="muted" style={{ fontSize: 12 }}>暫無數據</span>}
      </div>
      <div className="risk-chart-foot" style={{ display: "flex", gap: 14, justifyContent: "center" }}>
        <span className="risk-leg" style={{ padding: 0 }}><span className="risk-leg-dot" style={{ background: "#EF4444" }}/>今日新增 {last.new}</span>
        <span className="risk-leg" style={{ padding: 0 }}><span className="risk-leg-dot" style={{ background: "#10B981" }}/>今日處置 {last.handled}</span>
      </div>
    </div>
  );
};

const HandleProgress = ({ handled7d, open, handledToday }) => {
  const tot = (handled7d || 0) + (open || 0);
  const rate = tot ? Math.round((handled7d / tot) * 100) : 0;
  return (
    <DonutChart title="處置進度(近7天)"
      centerBig={`${rate}%`} centerSub="處置率"
      segments={[
        { label: "已處置", value: handled7d || 0, color: "#10B981" },
        { label: "待處理", value: open || 0, color: "#F59E0B" },
      ]}
      footer={`今日已處置 ${handledToday || 0} 條`}/>
  );
};

window.PageAlerts = PageAlerts;
