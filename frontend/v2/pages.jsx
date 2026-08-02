/* ============================================================
   WAREHOUSE 2.1 · pages — Swiss 版式 · 三語(tw/cn/en)
   ============================================================ */
(() => {
const W2 = window.W2;
const { t, lang } = window.W2_LANG;
const L = lang();
const { useState: _s, useEffect: _e, useMemo: _mm, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, StackBar, Spark2, MirrorBars, TrendArea, UnitMatrix } = W2;

window.W2_LANG.addEN({
  // 手動快捷四件套(出庫/入庫/補貨/預警)
  "快捷出庫": "Quick issue", "快捷盤盈": "Stock-gain adjustment", "手動盤盈調整": "Manual stock-gain adjustment",
  "數量": "Qty", "領用班組 / 去向": "Team / destination", "借用(需歸還)": "Borrow (returnable)",
  "確認出庫": "Confirm issue", "確認盤盈": "Confirm stock gain", "處理中…": "Working…",
  "已出庫 {n}": "Issued {n}", "已盤盈入庫 {n}": "Stock gain recorded: {n}", "請填寫正的數量": "Enter a positive quantity",
  "盤盈調整": "Stock-gain adjustment",
  "跨倉調撥": "Warehouse transfer", "借用登記": "Register loan",
  "「{name}」需要跨倉調撥,請追問目標倉與數量後辦理": "Transfer \"{name}\" between warehouses — ask for destination and quantity, then proceed",
  "「{name}」需要借用,請追問借用人、去向與數量後辦理": "Loan \"{name}\" — ask for borrower, destination and quantity, then proceed",
  "公司已切換，請重新開啟此操作": "The company changed; reopen this action in the current company",
  "操作失敗": "Action failed", "補貨申請": "Replenish request", "默認庫": "Default warehouse",
  "已提補貨申請 {n}(待秘書覆核)": "Replenish request for {n} submitted (pending Secretary review)",
  "出庫單已建立，但總賬憑證待系統重試": "Issue document created; the GL voucher is queued for retry",
  "入庫單已建立，但總賬憑證待系統重試": "Receipt document created; the GL voucher is queued for retry",
  "寫入即留痕,可在審計查回": "Writes are audited and traceable",
  "在管 SKU": "Managed SKUs", "可用 SKU": "Available SKUs",
  "跨倉合併口徑": "consolidated across warehouses", "估算儲值": "estimated value",
  "可用 {a} 種 · 零庫存 {z} 種 · 出入庫可一鍵手動,複雜操作交秘書 · 按": "{a} available · {z} out of stock · one-click in/out, complex actions via Secretary · press",
  "已處置": "Resolve", "忽略": "Dismiss",
  // 總覽 · 年報式統計模塊
  "庫存總儲值": "Total stock value", "庫存週轉率": "Stock turnover",
  "按單價估算": "by unit price", "出庫量 ÷ 儲值": "outbound ÷ value",
  "出入庫節奏": "In / out rhythm", "單據量 · 按月": "orders per month",
  "入庫": "Inbound", "出庫": "Outbound", "緊急": "urgent", "搶修峰值": "Repair peak",
  "※ {m} 搶修高峰 · {n} 張緊急單": "※ {m} repair peak · {n} urgent orders",
  "還沒有出入庫流水": "No in/out records yet",
  "產生單據後,月度節奏會出現在這裡。": "The monthly rhythm appears once orders exist.",
  "庫存總量走勢": "Total stock trend", "全部物資合計": "all items combined",
  "近 {n} 期淨減 {v} 件({p}%)": "Net −{v} units over {n} periods ({p}%)",
  "近 {n} 期淨增 {v} 件({p}%)": "Net +{v} units over {n} periods ({p}%)",
  "近 {n} 期持平": "Flat over {n} periods",
  "點任意月份可讓秘書解釋當月變動。": "Click any month and the Secretary explains the change.",
  "還沒有庫存趨勢資料": "No stock trend yet",
  "有出入庫流水後,總量走勢會出現在這裡。": "The aggregate trend appears once stock moves.",
  "儲值構成": "Value composition", "按分類 · 金額": "by category · value",
  "暫無帶單價的庫存資料": "No priced stock data yet",
  "對秘書說「幫物資補上單價」,儲值分析就會出現。": "Tell the Secretary to fill in unit prices and this analysis will appear.",
  "其他": "Other", "其餘分類": "Other categories", "萬": "×10k",
  "解釋 {m} 的庫存總量變動:主要是哪些物資、什麼單據造成的?": "Explain the total-stock change in {m}: which items and which orders drove it?",
  "消耗 TOP 5": "Top 5 consumed", "出庫 / 領用數量排行": "by outbound quantity",
  "暫無出庫消耗資料": "No consumption data yet",
  "有出庫或領用後,排行自動生成。": "The ranking builds itself once outbound activity exists.",
  "紅色 = 消耗快且已低於安全線,建議優先補貨。": "Red = burning fast and already below safety line — restock first.",
  "預警與處置": "Alerts & handling", "{n} 條活躍": "{n} open",
  "歷史處理率": "Handled rate", "待歸還工具": "Pending returns",
  "倉庫很安靜": "All quiet", "沒有需要處理的預警。": "No alerts to handle.",
  "待處理": "Open", "紅色高危": "Red critical", "超時升級": "Escalated", "近 7 日已處置": "Handled · 7 days",
  "風險態勢": "Risk posture", "近 7 日收斂": "7-day containment", "風險類別 TOP": "Top risk categories",
  "點擊風險級別篩選待處理清單": "Select a risk level to filter the action list",
  "點擊類別篩選待處理清單": "Select a category to filter the action list",
  "新增": "New", "處置": "Handled", "今日新增 {n}": "{n} new today", "今日已處置 {n}": "{n} handled today",
  "可見 {visible} · 跨域 {critical}": "Visible {visible} · cross-domain {critical}",
  "處置清單": "Action list", "依照權限顯示可操作預警": "Actionable alerts within your permissions",
  "篩選中": "Filtered", "清除篩選": "Clear filters", "篩選後沒有符合的預警": "No alerts match the current filters",
  "跨域紅色高危": "Cross-domain red critical", "唯讀兜底 · 由相關責任人處置": "Read-only safety net · handled by the responsible owner",
  "唯讀": "Read only", "負責人": "Owner", "權限外風險摘要": "Out-of-scope risk summary",
  "僅顯示聚合數字,不展示明細": "Aggregates only; no underlying details are exposed",
  "其餘權限外風險": "Other out-of-scope risks", "部分資料載入失敗": "Some risk data could not be loaded",
  "預警資料暫不可用": "Alert data is temporarily unavailable", "正在載入權限範圍內的風險態勢…": "Loading the risk posture within your permissions…",
  "近 7 日沒有新增或處置事件": "No new or handled events in the past 7 days",
  "資料未載入": "Data unavailable", "可操作": "Actionable", "超時仍未處置": "Overdue and still open",
  "一格一種物資 · 紅格該補貨": "one cell per item · red needs restock",
  "安全線達標率": "safety coverage", "暫無數據": "No data yet",
  "COMPUTING": "COMPUTING",
  // 秘書指令
  "把近幾個月的出入庫節奏講給我:哪個月異常、為什麼": "Walk me through the in/out rhythm of recent months: which month is unusual and why",
  "庫存總量最近在變化嗎?主要是哪些物資造成的?": "Is total stock changing lately? Which items drive it?",
  "分析庫存儲值構成:資金主要壓在哪些分類,健康嗎?": "Analyze stock value composition: where is capital tied up, and is it healthy?",
  "分析本期物資消耗結構:哪些消耗最快、是否合理、要不要調整安全庫存": "Analyze consumption structure: what burns fastest, is it reasonable, should safety stocks change",
  "把當前全部活躍預警按風險排序,逐條給我處置方案": "Sort all open alerts by risk and give me a plan for each",
  "「{name}」最近的領用和庫存走勢怎麼樣?": "How are recent usage and stock trends for \"{name}\"?",
});

const num = (v) => { const n = Number(v); return Number.isFinite(n) ? n : 0; };
const newInventoryRequestId = (kind) => `${kind}-web-` + (
  window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
);
const inventoryPendingKey = (itemId, mode) => `warehouse.pending.${encodeURIComponent((W2.tenant && W2.tenant()) || "no-tenant")}.quick.${mode}.${itemId}`;
const pendingInventoryRequestId = (itemId, mode) => {
  const key = inventoryPendingKey(itemId, mode);
  try {
    const existing = window.sessionStorage.getItem(key);
    if (existing) return { requestId: existing, requestKey: key };
    const created = newInventoryRequestId(mode === "out" ? "outbound" : "inbound");
    window.sessionStorage.setItem(key, created);
    return { requestId: created, requestKey: key };
  } catch (e) { return { requestId: newInventoryRequestId(mode === "out" ? "outbound" : "inbound"), requestKey: key }; }
};
const clearPendingInventoryRequestId = (key, requestId) => {
  try { if (window.sessionStorage.getItem(key) === requestId) window.sessionStorage.removeItem(key); } catch (e) {}
};
const health2 = (it) => num(it.stock) <= 0 ? "zero" : num(it.stock) < num(it.safe) ? "low" : "ok";
const trendOf = (it) => {
  const tr = Array.isArray(it.stockTrend) ? it.stockTrend.map(p => num(p.stock)) : [];
  return tr.length >= 2 ? tr : null;
};
const ask = (p) => W2.openSecretary(p);
const pad2 = (n) => String(n).padStart(2, "0");

const Folio = ({ no, en, title, sub, right }) => (
  <div className="folio rise">
    <div>
      <div className="folio-no">{no} — {en}</div>
      <h1>{title}</h1>
      {sub && <div className="folio-sub">{sub}</div>}
    </div>
    {right && <div className="row g10" style={{ paddingBottom: 4 }}>{right}</div>}
  </div>
);
const Band = ({ no, title, sub, right, children, delay }) => (
  <section className="band rise" style={delay ? { animationDelay: delay + "s" } : undefined}>
    <div className="band-head">
      <h2><span className="bh-no">{no}</span>{title}</h2>
      <div className="row g12">{sub && <span className="bh-sub">{sub}</span>}{right}</div>
    </div>
    {children}
  </section>
);

/* ═══ 01 · 總覽(年報式高密度:六格 KPI + 六個統計模塊)═══ */
const HBar = ({ idx, name, w, val, sub, color = "var(--ink)", red, title, onClick }) => (
  <div className="hbar-row" title={title} style={onClick ? { cursor: "pointer" } : undefined} onClick={onClick}>
    <span className="hb-idx">{pad2(idx)}</span>
    <span className="hb-name">{red && <I name="flame" size={11} color="var(--red)"/>}{name}</span>
    <span className="hbar-track"><i className="hbar-fill" style={{ width: Math.min(100, w) + "%", background: red ? "var(--red)" : color }}/></span>
    <span className="hb-val num" style={red ? { color: "var(--red)" } : undefined}>{val}</span>
    <span className="hb-pct num">{sub}</span>
  </div>
);
const Computing = () => (
  <div className="col g8" style={{ padding: "36px 0", alignItems: "center" }}>
    <LB dim>{t("COMPUTING")}</LB>
  </div>
);
const VALUE_RAMP = ["var(--ink)", "#4A4740", "#85806F", "#85806F", "#B4AE9C", "#B4AE9C"];
const LEVEL_DOT = { red: ["高危", "var(--danger)"], orange: ["重要", "var(--warn)"], yellow: ["留意", "#85806F"], blue: ["提示", "var(--ink-4)"] };

const PageDashboard = ({ boot }) => {
  const inv = boot.INVENTORY || [];
  const alerts = boot.ALERTS || [];
  const [rep, setRep] = _s(null);
  _e(() => {
    let alive = true;
    W2.json("/api/reports/summary").then(d => alive && setRep(d && typeof d === "object" ? d : {})).catch(() => alive && setRep({}));
    return () => { alive = false; };
  }, []);

  /* bootstrap 行按庫存餘額展開,同一物資多倉會重複;整頁「種」口徑統一為物資級(庫存/安全線跨倉合計) */
  const items = _mm(() => {
    const m = new Map();
    for (const it of inv) {
      const k = it.itemId != null ? it.itemId : it.id;
      const g = m.get(k);
      if (!g) m.set(k, { ...it, stock: num(it.stock), safe: num(it.safe) });
      else { g.stock += num(it.stock); g.safe += num(it.safe); }
    }
    return [...m.values()];
  }, [inv]);
  const low = items.filter(i => health2(i) === "low");
  const zero = items.filter(i => health2(i) === "zero");
  const ok = items.length - low.length - zero.length;
  const avail = items.filter(i => num(i.stock) > 0);
  const attn = [...low, ...zero].sort((a, b) => (num(a.stock) / (num(a.safe) || 1)) - (num(b.stock) / (num(b.safe) || 1))).slice(0, 6);
  const hour = new Date().getHours();
  const greet = t(hour < 6 ? "夜深了" : hour < 12 ? "早安" : hour < 18 ? "午後好" : "晚上好");
  const uname = (window.W2_USER && (window.W2_USER.display_name || window.W2_USER.username)) || "";
  const headline = L === "en"
    ? <>{greet}{uname ? ", " + uname : ""}. {attn.length ? <>You have <span style={{ color: "var(--red)" }} className="num">{attn.length}</span> decisions waiting.</> : "All quiet in the warehouse."}</>
    : <>{greet}{uname ? "," + uname : ""}。{attn.length ? <>{t("今天有")} <span style={{ color: "var(--red)" }} className="num">{attn.length}</span> {t("件事等你拍板。")}</> : t("倉庫一切如常。")}</>;

  /* KPI:儲值與週轉來自 /api/reports/summary */
  const kv = {};
  (rep && Array.isArray(rep.kpis) ? rep.kpis : []).forEach(k => { if (k && k.key) kv[k.key] = k; });
  const stockValue = kv["庫存總儲值"];
  const turnover = rep && rep.turnover != null ? rep.turnover : null;

  /* A · 出入庫節奏(urgent = 每月緊急搶修單數,峰值月整柱標紅) */
  const tr = rep && rep.trend && typeof rep.trend === "object" ? rep.trend : {};
  const mLabels = (Array.isArray(tr.labels) ? tr.labels : []).slice(-12);
  const nCut = (Array.isArray(tr.labels) ? tr.labels : []).length - mLabels.length;
  const mIn = (Array.isArray(tr.inbound) ? tr.inbound : []).slice(nCut > 0 ? nCut : 0);
  const mOut = (Array.isArray(tr.outbound) ? tr.outbound : []).slice(nCut > 0 ? nCut : 0);
  const mUrg = (Array.isArray(tr.urgent) ? tr.urgent : []).slice(nCut > 0 ? nCut : 0);
  const hasRhythm = mLabels.length > 0 && (mIn.some(v => num(v) > 0) || mOut.some(v => num(v) > 0));
  let urgIdx = -1;   // 緊急單最多的月份,並列取最近
  mUrg.forEach((v, i) => { if (num(v) > 0 && (urgIdx < 0 || num(v) >= num(mUrg[urgIdx]))) urgIdx = i; });
  const urgNote = urgIdx >= 0 ? t("※ {m} 搶修高峰 · {n} 張緊急單", { m: mLabels[urgIdx], n: num(mUrg[urgIdx]) }) : "";
  const mTitle = (i) => {
    const base = `${mLabels[i]} · ${t("入庫")} ${num(mIn[i])} ${t("單")} · ${t("出庫")} ${num(mOut[i])} ${t("單")}`;
    return num(mUrg[i]) > 0 ? `${base} · ${t("緊急")} ${num(mUrg[i])} ${t("單")}` : base;
  };

  /* B · 庫存總量走勢:逐物資 stockTrend 去重聚合(bootstrap 行按庫存餘額展開,同一物資會重複);
     後端對無流水物資會回推出一條「平線」佔位趨勢——全倉都無真實流水時不畫線,走空態 */
  const agg = _mm(() => {
    const seen = new Set();
    const sums = []; let labels = null; let hasHistory = false;
    for (const it of inv) {
      const key = it.itemId != null ? it.itemId : it.id;
      if (seen.has(key)) continue;
      seen.add(key);
      if (it.hasTrendHistory) hasHistory = true;
      const trd = Array.isArray(it.stockTrend) ? it.stockTrend : [];
      if (!trd.length) continue;
      if (!labels || trd.length > labels.length) labels = trd.map(p => p.label || p.month || "");
      trd.forEach((p, i) => { sums[i] = (sums[i] || 0) + num(p.stock); });
    }
    if (!labels || sums.length < 2 || !hasHistory) return null;
    const first = sums[0], lastV = sums[sums.length - 1], net = lastV - first;
    return { labels, points: sums.map(v => Math.round(v)), net: Math.round(net), pct: first ? Math.round(net / first * 1000) / 10 : 0 };
  }, [inv]);

  /* C · 儲值構成:前 5 + 其餘合併(不靜默截斷);後端本身有「其他」兜底分類,先併入尾桶避免同名兩行 */
  const distAll = (rep && Array.isArray(rep.value_dist) ? rep.value_dist : []).filter(x => x && num(x.value) > 0);
  const distNamed = distAll.filter(x => (x.label || "") !== "其他");
  const distOtherV = distAll.filter(x => (x.label || "") === "其他").reduce((s, x) => s + num(x.value), 0);
  const distHead = distNamed.slice(0, 5);
  const distRest = distNamed.slice(5).reduce((s, x) => s + num(x.value), 0) + distOtherV;
  const dist = distRest > 0 ? [...distHead, { label: t("其餘分類"), value: Math.round(distRest * 10) / 10 }] : distHead;
  const distTotal = distAll.reduce((s, x) => s + num(x.value), 0);
  const distMax = dist.reduce((m, x) => Math.max(m, num(x.value)), 0) || 1;

  /* D · 消耗 TOP 5(紅 = 消耗快且已低於安全線) */
  const lowNames = _mm(() => new Set([...low, ...zero].map(i => i.name)), [items]);
  const top = (rep && Array.isArray(rep.top_consume) ? rep.top_consume : []).filter(x => x && x.name).slice(0, 5);
  const topMax = top.reduce((m, x) => Math.max(m, num(x.value)), 0) || 1;

  /* E · 預警與處置 */
  const dotGroups = ["red", "orange", "yellow", "blue"]
    .map(lv => ({ lv, arr: alerts.filter(a => (a.level || "orange") === lv) }))
    .filter(g => g.arr.length);
  const as = rep && rep.alert_stats && typeof rep.alert_stats === "object" ? rep.alert_stats : null;

  /* F · 一格一種物資(物資級:跨倉合計後分級) */
  const cellsMx = _mm(() => {
    const rank = { ok: 0, low: 1, zero: 2 };
    const colorOf = { ok: "var(--ink)", low: "var(--red)", zero: "var(--ink-4)" };
    return items.map(it => ({ it, h: health2(it) }))
      .sort((a, b) => rank[a.h] - rank[b.h])
      .map(({ it, h }) => ({
        color: colorOf[h],
        title: `${it.name} · ${it.stock}/${it.safe} ${it.unit || ""}`,
        name: it.name, health: h,
      }));
  }, [items]);

  return (
    <>
      <Folio no="01" en="OVERVIEW" title={headline}
        right={<B kind="primary" icon="sparkle" onClick={() => ask(t("看看今天倉庫和經營上有什麼需要處理的,按優先級列出來"))}>{t("吩咐秘書")}</B>}/>

      <div className="kpi-band six">
        <Kpi label={t("在庫物資 · SKU")} value={avail.length} unit={t("種")} delay={0}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("共 {n} 種在管", { n: items.length })}</span>}/>
        <Kpi label={t("低於安全庫存")} value={low.length} unit={t("種")} red={low.length > 0} delay={.04}
          foot={low.length
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把低於安全庫存的物資列出來,給我合併補貨方案"))}>{t("讓秘書補齊 →")}</button>
            : <T tone="ok" dot>{t("全部達標")}</T>}/>
        <Kpi label={t("零庫存")} value={zero.length} unit={t("種")} delay={.08}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("檔案保留 · 可追溯")}</span>}/>
        <Kpi label={t("活躍預警")} value={alerts.length} unit={t("條")} red={alerts.length > 0} delay={.12}
          foot={alerts.length
            ? <a href="#/alerts" className="tag bad" style={{ textDecoration: "none" }}>{t("去處置 →")}</a>
            : <T tone="ok" dot>{t("無預警")}</T>}/>
        <Kpi label={t("庫存總儲值")} value={stockValue && stockValue.value != null ? stockValue.value : "—"} unit={stockValue ? t(stockValue.unit || "萬") : ""} delay={.16}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("按單價估算")}</span>}/>
        <Kpi label={t("庫存週轉率")} value={turnover != null ? turnover : "—"} delay={.2}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("出庫量 ÷ 儲值")}</span>}/>
      </div>

      <div className="dash-r1">
        <Band no="A" title={t("出入庫節奏")} sub={t("單據量 · 按月")} delay={.08}
          right={<div className="row g14">
            <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}><span style={{ width: 14, height: 9, background: "var(--ink)", flexShrink: 0 }}/>{t("入庫")}</span>
            <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}><span className="sw-hatch" style={{ width: 14, height: 9, flexShrink: 0 }}/>{t("出庫")}</span>
            {urgIdx >= 0 && <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}><span style={{ width: 14, height: 9, background: "var(--red)", flexShrink: 0 }}/>{t("搶修峰值")}</span>}
            <B size="sm" icon="sparkle" onClick={() => ask(t("把近幾個月的出入庫節奏講給我:哪個月異常、為什麼"))}>{t("問秘書")}</B>
          </div>}>
          <div className="dash-gap-r">
            {rep === null ? <Computing/>
              : hasRhythm ? <MirrorBars labels={mLabels} up={mIn} down={mOut} upName={t("入庫")} downName={t("出庫")} unit={" " + t("單")}
                  emph={urgIdx} note={urgNote} titleOf={mTitle}/>
              : <EM icon="chart" title={t("還沒有出入庫流水")} sub={t("產生單據後,月度節奏會出現在這裡。")}/>}
          </div>
        </Band>
        <Band no="B" title={t("庫存總量走勢")} sub={t("全部物資合計")} delay={.12}
          right={<B size="sm" icon="sparkle" onClick={() => ask(t("庫存總量最近在變化嗎?主要是哪些物資造成的?"))}>{t("問秘書")}</B>}>
          <div className="dash-gap-l">
            {agg ? (
              <>
                <TrendArea points={agg.points} labels={agg.labels}
                  onMonth={(m) => ask(t("解釋 {m} 的庫存總量變動:主要是哪些物資、什麼單據造成的?", { m }))}/>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 10, lineHeight: 1.6 }}>
                  {agg.net === 0
                    ? t("近 {n} 期持平", { n: agg.labels.length })
                    : <b className="num" style={{ color: agg.net < 0 ? "var(--red)" : "var(--ink)" }}>
                        {t(agg.net < 0 ? "近 {n} 期淨減 {v} 件({p}%)" : "近 {n} 期淨增 {v} 件({p}%)",
                          { n: agg.labels.length, v: Math.abs(agg.net), p: Math.abs(agg.pct) })}
                      </b>}
                  {" · "}{t("點任意月份可讓秘書解釋當月變動。")}
                </div>
              </>
            ) : <EM icon="trend" title={t("還沒有庫存趨勢資料")} sub={t("有出入庫流水後,總量走勢會出現在這裡。")}/>}
          </div>
        </Band>
      </div>

      <div className="dash-r2">
        <Band no="C" title={t("儲值構成")} sub={distTotal > 0 ? "¥" + distTotal.toFixed(1) + t("萬") : t("按分類 · 金額")} delay={.14}>
          <div className="dash-gap-r">
            {rep === null ? <Computing/>
              : dist.length ? dist.map((x, i) => (
                  <HBar key={(x.label || "—") + ":" + i} idx={i + 1} name={x.label || "—"}
                    w={num(x.value) / distMax * 100} color={VALUE_RAMP[Math.min(i, VALUE_RAMP.length - 1)]}
                    val={"¥" + num(x.value).toFixed(1) + t("萬")}
                    sub={(distTotal ? Math.round(num(x.value) / distTotal * 100) : 0) + "%"}
                    title={(x.label || "—") + " · ¥" + num(x.value).toFixed(1) + t("萬")}
                    onClick={() => ask(t("分析庫存儲值構成:資金主要壓在哪些分類,健康嗎?"))}/>
                ))
              : <EM icon="wallet" title={t("暫無帶單價的庫存資料")} sub={t("對秘書說「幫物資補上單價」,儲值分析就會出現。")}/>}
          </div>
        </Band>
        <Band no="D" title={t("消耗 TOP 5")} sub={t("出庫 / 領用數量排行")} delay={.18}>
          <div className="dash-gap-l">
            {rep === null ? <Computing/>
              : top.length ? (
                <>
                  {top.map((x, i) => (
                    <HBar key={x.name || i} idx={i + 1} name={x.name} red={lowNames.has(x.name)}
                      w={num(x.value) / topMax * 100} val={num(x.value)} sub={""}
                      title={x.name + " · " + num(x.value) + (lowNames.has(x.name) ? " · " + t("低於安全線") : "")}
                      onClick={() => ask(lowNames.has(x.name)
                        ? t("「{name}」低於安全庫存,幫我生成補貨申請", { name: x.name })
                        : t("「{name}」最近的領用和庫存走勢怎麼樣?", { name: x.name }))}/>
                  ))}
                  <div className="muted" style={{ fontSize: 10.5, marginTop: 10 }}>{t("紅色 = 消耗快且已低於安全線,建議優先補貨。")}</div>
                </>
              ) : <EM icon="trend" title={t("暫無出庫消耗資料")} sub={t("有出庫或領用後,排行自動生成。")}/>}
          </div>
        </Band>
        <Band no="E" title={t("預警與處置")} sub={alerts.length ? t("{n} 條活躍", { n: alerts.length }) : t("無預警")} delay={.22}
          right={!!alerts.length && <B size="sm" icon="sparkle" onClick={() => ask(t("把當前全部活躍預警按風險排序,逐條給我處置方案"))}>{t("問秘書")}</B>}>
          <div className="dash-gap-l">
            {dotGroups.length ? dotGroups.map(({ lv, arr }) => {
              const [label, color] = LEVEL_DOT[lv] || [lv, "var(--ink-4)"];
              const shown = arr.slice(0, 40);
              return (
                <div key={lv} className="dm-row" style={{ cursor: "pointer" }}
                  onClick={() => ask(t("把當前全部活躍預警按風險排序,逐條給我處置方案"))}>
                  <span className="dm-label">{t(label)}</span>
                  <span className="dm-dots">
                    {shown.map((a, i) => <i key={i} title={(a.item || a.type || "") + (a.suggest && a.suggest !== "—" ? " · " + a.suggest : "")} style={{ background: color }}/>)}
                    {arr.length > shown.length && <span className="muted num" style={{ fontSize: 10 }}>+{arr.length - shown.length}</span>}
                  </span>
                  <span className="dm-n">{arr.length}</span>
                </div>
              );
            }) : <div className="muted" style={{ fontSize: 12, padding: "10px 0" }}>{t("沒有需要處理的預警。")}</div>}
            {as && (
              <div className="col g10" style={{ marginTop: 14 }}>
                <Meter label={t("歷史處理率")} count={num(as.handled)} total={num(as.total)} color="var(--ink)"/>
                <div className="row spread" style={{ fontSize: 11.5, borderBottom: "1px solid var(--hair-soft)", paddingBottom: 6 }}>
                  <span className="ink2">{t("待歸還工具")}</span>
                  <span className="num" style={{ fontWeight: 700, color: num(as.pending_returns) > 0 ? "var(--warn)" : "var(--ink)" }}>{num(as.pending_returns)}</span>
                </div>
              </div>
            )}
          </div>
        </Band>
      </div>

      <div className="dash-r3">
        <Band no="F" title={t("庫存健康")} sub={t("一格一種物資 · 紅格該補貨")} delay={.26}>
          <div className="dash-gap-r">
            <div className="row g8" style={{ alignItems: "baseline", marginBottom: 14 }}>
              <span className="num" style={{ fontSize: 46, fontWeight: 700, letterSpacing: "-.04em" }}>{items.length ? Math.round(ok / items.length * 100) : 100}<span style={{ fontSize: 18 }}>%</span></span>
              <span className="muted" style={{ fontSize: 12 }}>{t("安全線達標率")}</span>
            </div>
            <UnitMatrix cells={cellsMx} onCell={(c) => ask(c.health === "ok"
              ? t("「{name}」最近的領用和庫存走勢怎麼樣?", { name: c.name })
              : t("「{name}」低於安全庫存,幫我生成補貨申請", { name: c.name }))}/>
            <div className="row g12 wrap" style={{ marginTop: 12, fontSize: 11, color: "var(--ink-2)" }}>
              <span className="row g6"><i style={{ width: 9, height: 9, background: "var(--ink)" }}/>{t("達標")} <b className="num">{ok}</b></span>
              <span className="row g6"><i style={{ width: 9, height: 9, background: "var(--red)" }}/>{t("低於安全線")} <b className="num">{low.length}</b></span>
              <span className="row g6"><i style={{ width: 9, height: 9, background: "var(--ink-4)" }}/>{t("零庫存")} <b className="num">{zero.length}</b></span>
            </div>
          </div>
        </Band>
        <Band no="G" title={t("需要關注")} sub={t("按缺口嚴重度排序")} delay={.3}
          right={!!attn.length && <B size="sm" icon="sparkle" onClick={() => ask(t("把這 {n} 種告急物資一次性生成合併補貨計劃", { n: attn.length }))}>{t("一鍵全部補齊")}</B>}>
          <div className="dash-gap-l">
            {attn.length ? (
              <div style={{ borderTop: "2px solid var(--rule)" }}>
                {attn.map((it, i) => {
                  const z = health2(it) === "zero";
                  const pct = Math.min(100, Math.round(num(it.stock) / (num(it.safe) || 1) * 100));
                  return (
                    <div key={it.id || it.code || i} className="ledger-row">
                      <span className="lr-idx">{pad2(i + 1)}</span>
                      <div className="col g4" style={{ flex: 1.4, minWidth: 0 }}>
                        <span className="row g8" style={{ fontWeight: 650, fontSize: 13.5 }}>
                          {it.critical && <I name="flame" size={12} color="var(--red)"/>}{it.name}
                        </span>
                        <span className="muted num" style={{ fontSize: 11 }}>{it.code}{it.wh ? " · " + it.wh : ""}</span>
                      </div>
                      <div className="col g4" style={{ flex: 1 }}>
                        <div className="row g6" style={{ alignItems: "baseline" }}>
                          <span className="num" style={{ fontSize: 18, fontWeight: 700, color: z ? "var(--ink-3)" : "var(--red)" }}>{it.stock}</span>
                          <span className="muted num" style={{ fontSize: 11 }}>{t("/ 安全")} {it.safe} {it.unit || ""}</span>
                        </div>
                        <div className="bar" style={{ width: 150 }}><i style={{ width: pct + "%", background: z ? "var(--ink-4)" : "var(--red)" }}/></div>
                      </div>
                      {z ? <T tone="plain">{t("零庫存")}</T> : <T tone="bad" dot>{t("低庫存")}</T>}
                      <B size="sm" onClick={() => ask(t("「{name}」低於安全庫存,幫我生成補貨申請", { name: it.name }))}>{t("讓秘書補貨")}</B>
                    </div>
                  );
                })}
              </div>
            ) : <EM icon="checkCircle" title={t("倉庫很安靜")} sub={t("沒有需要處理的預警。")}/>}
          </div>
        </Band>
      </div>
    </>
  );
};

/* ═══ 02 · 庫存 ═══ */
const PageInventory2 = ({ boot, reload }) => {
  const inv = boot.INVENTORY || [];
  const cats = boot.LEDGER_CATEGORIES || [];
  const whs = boot.WAREHOUSES || [];
  const warehouseHub = boot && boot.WAREHOUSE_HUB;
  const inventoryStats = (
    warehouseHub
    && warehouseHub.scope === "permission-filtered"
    && warehouseHub.access
    && warehouseHub.access.inventory
    && warehouseHub.inventory
    && typeof warehouseHub.inventory === "object"
  ) ? warehouseHub.inventory : null;
  const inventoryMetric = (key, digits = 0) => {
    const raw = inventoryStats && inventoryStats[key];
    const value = raw === null || raw === undefined || raw === "" ? NaN : Number(raw);
    return Number.isFinite(value)
      ? value.toLocaleString(undefined, { maximumFractionDigits: digits })
      : "—";
  };
  const managedSkus = inventoryMetric("skus");
  const availableSkus = inventoryMetric("available_skus");
  const lowSkus = inventoryMetric("low_skus");
  const zeroSkus = inventoryMetric("zero_skus");
  const stockValue = inventoryMetric("stock_value", 2);
  const hasLowStock = !!(inventoryStats && Number(inventoryStats.low_skus) > 0);
  const hasZeroStock = !!(inventoryStats && Number(inventoryStats.zero_skus) > 0);
  const canInbound = W2.hasPermission ? W2.hasPermission("inventory.inbound") : false;
  const canOutbound = W2.hasPermission ? W2.hasPermission("inventory.outbound") : false;
  const canShipment = W2.hasPermission ? W2.hasPermission("inventory.shipment") : false;
  const canAdjust = W2.hasPermission ? W2.hasPermission("inventory.adjust") : false;
  const [q, setQ] = _s("");
  const [cat, setCat] = _s("all");
  const [scope, setScope] = _s("avail");
  const [sort, setSort] = _s("urgency");
  const [dir, setDir] = _s(1);
  const [sel, setSel] = _s(null);
  const [alertMap, setAlertMap] = _s({});
  const searchRef = _r(null);
  /* 手動快捷:行內迷你表單(出庫/入庫);秘書仍是主路,只多個手動入口。
     按「行 id」(非 itemId)隔離——同物資多倉是多行,itemId 相同會讓表單在所有行同時彈出 */
  const [qa, setQa] = _s(null);       // { id, mode:"out"|"in", qty, dept, wh, borrow }
  const [qaBusy, setQaBusy] = _s(null);  // 正在寫的行 id
  const [qaMsg, setQaMsg] = _s(null);  // { id, ok, text }
  const openQa = (it, mode) => {
    if ((mode === "out" && !canOutbound) || (mode === "in" && !canInbound)) return;
    if (qaBusy != null) return;
    setQaMsg(null);
    setQa((p) => (p && p.id === it.id && p.mode === mode) ? null
      : { id: it.id, mode, qty: "", dept: "", wh: (whs.indexOf(it.wh) >= 0 ? it.wh : (whs[0] || "")), borrow: !!it.requiresReturn, prod: "", shelf: "", ...pendingInventoryRequestId(it.id, mode) });
  };
  _e(() => { setQaMsg(null); setQa(null); }, [q, cat, scope, sort]);  // 篩選/排序變化清掉殘留表單與提示
  const runQa = async (it) => {
    if (!qa || (qa.mode === "out" ? !canOutbound : !canInbound)) return;
    if (inventoryPendingKey(it.id, qa.mode) !== qa.requestKey) { setQaMsg({ id: it.id, ok: false, text: t("公司已切換，請重新開啟此操作") }); return; }
    const n = Number(qa.qty);
    if (!Number.isFinite(n) || n <= 0) { setQaMsg({ id: it.id, ok: false, text: t("請填寫正的數量") }); return; }
    setQaBusy(it.id); setQaMsg(null);
    try {
      if (qa.mode === "out") {
        const dest = (qa.dept || "").trim() || undefined;
        const result = await W2.post("/api/outbound/create", {
          request_id: qa.requestId,
          lines: [{ name: it.name, qty: n, unit: it.unit }],
          use: qa.borrow ? "借用" : "領用", dept: dest, target: dest,
        });
        if (result && result.posting_warning) {
          clearPendingInventoryRequestId(qa.requestKey, qa.requestId);
          setQa(null);
          setQaMsg({ id: it.id, ok: false, partial: true, text: t("出庫單已建立，但總賬憑證待系統重試") });
          reload && reload();
          return;
        }
      } else {
        const line = { name: it.name, qty: n, unit: it.unit };
        if ((qa.prod || "").trim()) line.production_date = qa.prod.trim();
        if (String(qa.shelf || "").trim() && Number(qa.shelf) > 0) line.shelf_life_days = Number(qa.shelf);
        const result = await W2.post("/api/inbound/create", {
          request_id: qa.requestId,
          lines: [line],
          warehouse: qa.wh || undefined, source: t("手動盤盈調整"), type: "盤盈入庫",
        });
        if (result && result.posting_warning) {
          clearPendingInventoryRequestId(qa.requestKey, qa.requestId);
          setQa(null);
          setQaMsg({ id: it.id, ok: false, partial: true, text: t("入庫單已建立，但總賬憑證待系統重試") });
          reload && reload();
          return;
        }
      }
      clearPendingInventoryRequestId(qa.requestKey, qa.requestId);
      setQa(null);
      setQaMsg({ id: it.id, ok: true, text: qa.mode === "out" ? t("已出庫 {n}", { n }) : t("已盤盈入庫 {n}", { n }) });
      reload && reload();
    } catch (e) {
      setQaMsg({ id: it.id, ok: false, text: e.message || t("操作失敗") });
    } finally { setQaBusy(null); }
  };
  const runReplenish = async (it) => {
    setQaBusy(it.id); setQaMsg(null);
    try {
      const need = Math.max(1, num(it.safe) - num(it.stock) + Math.ceil(num(it.safe) * .3));
      await W2.post("/api/replenishment", { item_name: it.name, need, unit: it.unit, stock: num(it.stock), safe: num(it.safe) });
      setQaMsg({ id: it.id, ok: true, text: t("已提補貨申請 {n}(待秘書覆核)", { n: need }) });
    } catch (e) {
      setQaMsg({ id: it.id, ok: false, text: e.message || t("操作失敗") });
    } finally { setQaBusy(null); }
  };

  _e(() => {
    W2.json("/api/alerts/by-item").then(d => d && d.byItem && setAlertMap(d.byItem)).catch(() => {});
    const h = (e) => {
      if (e.key === "/" && document.activeElement !== searchRef.current) { e.preventDefault(); searchRef.current && searchRef.current.focus(); }
      if (e.key === "Escape") setSel(null);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  let list = inv;
  if (scope === "avail") list = list.filter(i => num(i.stock) > 0);
  if (scope === "zero") list = list.filter(i => num(i.stock) <= 0);
  if (cat !== "all") list = list.filter(i => i.categoryId === cat);
  if (q) list = list.filter(i => ((i.name || "") + (i.code || "") + (i.model || "")).toLowerCase().includes(q.toLowerCase()));
  const sorted = _mm(() => {
    const arr = [...list];
    if (sort === "urgency") arr.sort((a, b) => (num(a.stock) / (num(a.safe) || 1)) - (num(b.stock) / (num(b.safe) || 1)));
    if (sort === "stock") arr.sort((a, b) => dir * (num(a.stock) - num(b.stock)));
    if (sort === "name") arr.sort((a, b) => dir * String(a.name).localeCompare(String(b.name), "zh"));
    return arr;
  }, [list, sort, dir]);

  const th = (key, label) => (
    <th style={{ cursor: "pointer", userSelect: "none", color: sort === key ? "var(--red)" : undefined }}
      onClick={() => { if (sort === key) setDir(-dir); else { setSort(key); setDir(1); } }}>
      {label}{sort === key ? (dir > 0 ? " ↑" : " ↓") : ""}
    </th>
  );

  return (
    <>
      <Folio no="02" en="INVENTORY" title={t("庫存")}
        sub={<>{t("可用 {a} 種 · 零庫存 {z} 種 · 出入庫可一鍵手動,複雜操作交秘書 · 按", { a: availableSkus, z: zeroSkus })} <span className="num">/</span> {t("搜索")}</>}
        right={<>
          {canAdjust && <B icon="plus" onClick={() => W2.openBusinessAction("item_create")}>{t("新增物資")}</B>}
          <B kind="primary" icon="sparkle" onClick={() => ask(t("庫存現在最需要處理的是什麼?"))}>{t("問秘書")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={t("在管 SKU")} value={managedSkus} unit={t("種")} delay={0}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("跨倉合併口徑")}</span>}/>
        <Kpi label={t("可用 SKU")} value={availableSkus} unit={t("種")} delay={.04}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("估算儲值")} · <b className="num">{stockValue}</b></span>}/>
        <Kpi label={t("低於安全庫存")} value={lowSkus} unit={t("種")} red={hasLowStock} delay={.08}
          foot={lowSkus === "—"
            ? <span className="muted">—</span>
            : hasLowStock
              ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把低於安全庫存的物資列出來,給我合併補貨方案"))}>{t("讓秘書補齊 →")}</button>
              : <T tone="ok" dot>{t("全部達標")}</T>}/>
        <Kpi label={t("零庫存")} value={zeroSkus} unit={t("種")} red={hasZeroStock} delay={.12}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{zeroSkus === "—" ? "—" : t("檔案保留 · 可追溯")}</span>}/>
      </div>

      <div className="row g14 wrap rise" style={{ padding: "18px 0 16px", borderBottom: "1px solid var(--hair)", animationDelay: ".05s" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
          <I name="search" size={15} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
          <input ref={searchRef} className="field" style={{ paddingLeft: 26, height: 38 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t("搜索名稱 / 編碼 / 型號")}/>
        </div>
        <div className="seg">
          {[["avail", "有庫存"], ["zero", "零庫存"], ["all", "全部"]].map(([id, label]) => (
            <button key={id} className={scope === id ? "on" : ""} onClick={() => setScope(id)}>{t(label)}</button>
          ))}
        </div>
        <div className="row g6 wrap">
          <button className={"chip" + (cat === "all" ? " on" : "")} onClick={() => setCat("all")}>{t("全部分類")}</button>
          {cats.map(c => (
            <button key={c.id} className={"chip" + (cat === c.id ? " on" : "")} onClick={() => setCat(c.id)}>
              {c.name}{c.requires_return ? <I name="swap" size={10}/> : null}
            </button>
          ))}
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start", paddingTop: 18 }}>
        <div className="rise" style={{ flex: 1, minWidth: 0, animationDelay: ".1s" }}>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                {th("name", t("物資"))}<th>{t("編碼 / 型號")}</th><th>{t("分類")}</th>{th("stock", t("庫存 / 安全"))}<th>{t("趨勢")}</th><th>{t("庫位")}</th>{th("urgency", t("狀態"))}<th style={{ width: 110 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {sorted.map((it, idx) => {
                  const h = health2(it);
                  const tr = trendOf(it);
                  const al = alertMap[it.itemId];
                  const qaOpen = qa && qa.id === it.id;
                  const msg = qaMsg && qaMsg.id === it.id ? qaMsg : null;
                  const rowBusy = qaBusy === it.id;
                  return (
                    <React.Fragment key={(it.id || it.code || idx) + ":" + idx}>
                    <tr className={sel && sel.id === it.id ? "on" : ""} onClick={() => setSel(it)} style={{ cursor: "pointer" }}>
                      <td>
                        <div className="col g4">
                          <span className="row g8" style={{ fontWeight: 650 }}>
                            {it.critical && <I name="flame" size={12} color="var(--red)"/>}{it.name}
                          </span>
                          <span className="row g6">
                            {it.critical && <span className="mono" style={{ fontSize: 9, letterSpacing: ".1em", color: "var(--red)" }}>{t("搶修必備")}</span>}
                            {al && <T tone="warn">{al.count} {t("預警")}</T>}
                            {it.perishable && it.expiryDays != null && (
                              <T tone={it.expiryDays < 0 || it.expiryDays <= 7 ? "bad" : it.expiryDays <= 30 ? "warn" : "ok"} dot>
                                {it.expiryDays < 0 ? t("已過期{n}天", { n: -it.expiryDays }) : t("{n}天到期", { n: it.expiryDays })}
                              </T>
                            )}
                          </span>
                        </div>
                      </td>
                      <td><div className="col g2"><span className="num" style={{ fontWeight: 600 }}>{it.code}</span><span className="num muted" style={{ fontSize: 11 }}>{it.model && it.model !== "—" ? it.model : ""}</span></div></td>
                      <td className="muted">
                        <span className="row g6">{it.category || it.cat || "—"}{it.requiresReturn && <T tone="plain">{t("借還")}</T>}</span>
                      </td>
                      <td>
                        <span className="num" style={{ fontWeight: 700, fontSize: 15, color: h === "ok" ? "var(--ink)" : "var(--red)" }}>{it.stock}</span>
                        <span className="num muted"> / {it.safe} {it.unit}</span>
                        <div className="bar" style={{ width: 80, marginTop: 5 }}>
                          <i style={{ width: Math.min(100, num(it.safe) ? num(it.stock) / num(it.safe) * 100 : 0) + "%", background: h === "ok" ? "var(--ink)" : h === "low" ? "var(--red)" : "var(--ink-4)" }}/>
                        </div>
                      </td>
                      <td>{tr ? <Spark2 points={tr} w={84} h={26} color={h === "ok" ? "var(--ink)" : "var(--red)"}/> : <span className="muted" style={{ fontSize: 11 }}>—</span>}</td>
                      <td><span className="num muted" style={{ fontSize: 12 }}>{it.loc || "—"}</span></td>
                      <td>{h === "zero" ? <T tone="plain">{t("零庫存")}</T> : h === "low" ? <T tone="bad" dot>{t("低庫存")}</T> : <T tone="ok" dot>{t("正常")}</T>}</td>
                      <td onClick={e => e.stopPropagation()}>
                        <div className="row g4">
                          {canOutbound && <button className={"btn sm" + (qaOpen && qa.mode === "out" ? " primary" : "")} disabled={qaBusy != null} title={t("出庫")} style={{ padding: "0 8px" }} onClick={() => openQa(it, "out")}><I name="outbound" size={12}/></button>}
                          {canInbound && <button className={"btn sm" + (qaOpen && qa.mode === "in" ? " primary" : "")} disabled={qaBusy != null} title={t("盤盈調整")} style={{ padding: "0 8px" }} onClick={() => openQa(it, "in")}><I name="inbound" size={12}/></button>}
                          {h !== "ok" && <button className="btn sm red" title={t("補貨申請")} style={{ padding: "0 8px" }} disabled={rowBusy} onClick={() => runReplenish(it)}><I name="refresh" size={12}/></button>}
                          <button className="btn sm" title={t("問秘書")} style={{ padding: "0 8px" }} onClick={() => ask(t("「{name}」最近的領用和庫存走勢怎麼樣?", { name: it.name }))}><I name="sparkle" size={12}/></button>
                        </div>
                      </td>
                    </tr>
                    {(qaOpen || msg) && (
                      <tr onClick={e => e.stopPropagation()}>
                        <td colSpan={8} style={{ background: "var(--paper-2)", padding: qaOpen ? "10px 14px" : "6px 14px" }}>
                          {qaOpen && (
                            <div className="row g10 wrap" style={{ alignItems: "center" }}>
                              <span className="label" style={{ fontSize: 9 }}>{qa.mode === "out" ? t("快捷出庫") : t("快捷盤盈")}</span>
                              <span style={{ fontWeight: 650, fontSize: 12.5 }}>{it.name}</span>
                              <input className="field boxed" autoFocus type="number" min="0" disabled={rowBusy} value={qa.qty} placeholder={t("數量")}
                                style={{ width: 90, height: 32 }} onChange={e => setQa({ ...qa, qty: e.target.value })}
                                onKeyDown={e => { if (e.key === "Enter" && !rowBusy) runQa(it); }}/>
                              <span className="muted num" style={{ fontSize: 11 }}>{it.unit}</span>
                              {qa.mode === "out" ? (<>
                                <input className="field boxed" disabled={rowBusy} value={qa.dept} placeholder={t("領用班組 / 去向")}
                                  style={{ width: 150, height: 32 }} onChange={e => setQa({ ...qa, dept: e.target.value })}
                                  onKeyDown={e => { if (e.key === "Enter" && !rowBusy) runQa(it); }}/>
                                <label className="row g6" style={{ fontSize: 12, cursor: "pointer" }}>
                                  <input type="checkbox" disabled={rowBusy} checked={qa.borrow} onChange={e => setQa({ ...qa, borrow: e.target.checked })}/>{t("借用(需歸還)")}
                                </label>
                              </>) : (
                                <>
                                <select className="field boxed" disabled={rowBusy} value={qa.wh} style={{ width: 160, height: 32 }} onChange={e => setQa({ ...qa, wh: e.target.value })}>
                                  {whs.length ? whs.map(w => <option key={w} value={w}>{w}</option>) : <option value="">{t("默認庫")}</option>}
                                </select>
                                {it.perishable && (<>
                                  <label className="row g4" style={{ fontSize: 10.5, color: "var(--ink-4)" }}>{t("生產日期")}
                                    <input className="field boxed" type="date" disabled={rowBusy} value={qa.prod}
                                      style={{ width: 150, height: 32 }} onChange={e => setQa({ ...qa, prod: e.target.value })}/>
                                  </label>
                                  <input className="field boxed" type="number" min="0" disabled={rowBusy} value={qa.shelf} placeholder={t("保鮮期(天)")}
                                    style={{ width: 130, height: 32 }} onChange={e => setQa({ ...qa, shelf: e.target.value })}
                                    onKeyDown={e => { if (e.key === "Enter" && !rowBusy) runQa(it); }}/>
                                </>)}
                                </>
                              )}
                              <B size="sm" kind="primary" icon="check" disabled={rowBusy} onClick={() => runQa(it)}>{rowBusy ? t("處理中…") : (qa.mode === "out" ? t("確認出庫") : t("確認盤盈"))}</B>
                              <B size="sm" disabled={rowBusy} onClick={() => setQa(null)}>{t("取消")}</B>
                              <span className="muted" style={{ fontSize: 10.5, marginLeft: "auto" }}>{t("寫入即留痕,可在審計查回")}</span>
                            </div>
                          )}
                          {msg && <div className="row g6" style={{ fontSize: 11.5, marginTop: qaOpen ? 8 : 0, color: msg.partial ? "var(--warn)" : (msg.ok ? "var(--ok)" : "var(--red)"), fontWeight: 600 }}>
                            <I name={msg.partial ? "alert" : (msg.ok ? "checkCircle" : "x")} size={13} color={msg.partial ? "var(--warn)" : (msg.ok ? "var(--ok)" : "var(--red)")}/>{msg.text}</div>}
                        </td>
                      </tr>
                    )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
          {!sorted.length && <EM icon="search" title={t("當前篩選下沒有物資")} sub={t("換個關鍵詞,或直接對秘書說「幫我找◯◯」。")}/>}
        </div>

        {sel && <InvDrawer2 item={sel} onClose={() => setSel(null)} canInbound={canInbound} canOutbound={canOutbound} canShipment={canShipment} canAdjust={canAdjust}/>}
      </div>
    </>
  );
};

const InvDrawer2 = ({ item, onClose, canInbound, canOutbound, canShipment, canAdjust }) => {
  const h = health2(item);
  const tr = trendOf(item);
  const need = Math.max(0, num(item.safe) - num(item.stock) + Math.ceil(num(item.safe) * .3));
  const [batchData, setBatchData] = _s(null);
  _e(() => {
    if (!item || !item.itemId) { setBatchData(null); return; }
    setBatchData(null);   // 切換物資時先清空,避免抽屜在拉取完成前短暫顯示上一物資的批次
    let alive = true;
    W2.json(`/api/inventory/batches?item_id=${item.itemId}`)
      .then(d => { if (alive) setBatchData(d || { batches: [] }); })
      .catch(() => { if (alive) setBatchData({ batches: [] }); });
    return () => { alive = false; };
  }, [item && item.itemId]);
  const expiryTone = (d) => d == null ? "var(--ink-4)" : (d < 0 || d <= 7) ? "var(--red)" : d <= 30 ? "var(--warn)" : "var(--ink)";
  const acts = [
    canOutbound && ["outbound", "出庫領用", t("出庫「{name}」,請追問數量與領用班組後執行", { name: item.name })],
    canInbound && ["inbound", "入庫上架", t("「{name}」到貨了,請追問數量後入庫上架", { name: item.name })],
    canShipment && ["swap", "跨倉調撥", t("「{name}」需要跨倉調撥,請追問目標倉與數量後辦理", { name: item.name })],
    canOutbound && ["outbound", "借用登記", t("「{name}」需要借用,請追問借用人、去向與數量後辦理", { name: item.name })],
    canAdjust && ["clipboard", "發起盤點", t("幫「{name}」安排一次盤點", { name: item.name })],
  ].filter(Boolean);
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          {h === "zero" ? <T tone="plain">{t("零庫存")}</T> : h === "low" ? <T tone="bad" dot>{t("低庫存")}</T> : <T tone="ok" dot>{t("正常")}</T>}
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.25 }}>{item.name}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{item.code}{item.model && item.model !== "—" ? " · " + item.model : ""}</div>
        {item.critical && <div className="row g6" style={{ marginTop: 8 }}><span className="mono" style={{ fontSize: 9, letterSpacing: ".14em", color: "var(--red)", fontWeight: 700 }}>{t("搶修必備")}</span></div>}
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {[[t("當前庫存"), `${item.stock} ${item.unit || ""}`], [t("安全庫存"), `${item.safe} ${item.unit || ""}`], [t("庫位"), `${item.wh || "—"} · ${item.loc || "—"}`], [t("供應商"), item.supplier || "—"]].map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 14, fontWeight: 650 }}>{v}</span>
            </div>
          ))}
        </div>
        {tr && (
          <div style={{ marginBottom: 18 }}>
            <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("近 7 期庫存趨勢")}</LB>
            <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 12 }}>
              <Spark2 points={tr} w={300} h={50} color={h === "ok" ? "var(--ink)" : "var(--red)"}/>
            </div>
          </div>
        )}
        {batchData && batchData.batches && batchData.batches.length > 0 && (
          <div style={{ marginBottom: 18 }}>
            <div className="row spread" style={{ marginBottom: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{t("批次 · 效期(先過期先出)")}</LB>
              <span className="row g6">
                {batchData.requiredCondition && <T tone="plain">{t("需{c}", { c: t(batchData.requiredCondition) })}</T>}
                {batchData.shelfLife != null && <span className="muted num" style={{ fontSize: 10 }}>{t("保鮮期 {n} 天", { n: batchData.shelfLife })}</span>}
              </span>
            </div>
            <div className="col" style={{ borderTop: "1px solid var(--hair)" }}>
              {batchData.batches.map((b) => (
                <div key={b.id} className="row spread" style={{ fontSize: 11.5, padding: "8px 0", borderBottom: "1px solid var(--hair)", alignItems: "flex-start" }}>
                  <div className="col g2">
                    <span className="row g6">
                      <span className="mono" style={{ fontSize: 8.5, letterSpacing: ".08em", color: "var(--ink-4)" }}>FEFO#{b.fefoRank}</span>
                      <span style={{ fontWeight: 650 }}>{b.batchNo}</span>
                      {b.coldOk === false && <T tone="bad" dot>{t("溫控不當")}</T>}
                    </span>
                    <span className="muted num" style={{ fontSize: 10 }}>
                      {b.productionDate ? t("產 {d}", { d: b.productionDate }) : ""}{b.warehouse ? (b.productionDate ? " · " : "") + b.warehouse : ""}{b.location ? " " + b.location : ""}
                    </span>
                  </div>
                  <div className="col g2" style={{ textAlign: "right" }}>
                    <span className="num" style={{ fontWeight: 700, color: expiryTone(b.days) }}>
                      {b.days == null ? t("無到期日") : b.days < 0 ? t("已過期{n}天", { n: -b.days }) : t("{n}天到期", { n: b.days })}
                    </span>
                    <span className="muted num" style={{ fontSize: 10 }}>{(b.expireAt || "—") + " · " + b.qty + " " + (batchData.unit || item.unit || "")}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {h !== "ok" && (
          <div style={{ padding: "12px 14px", border: "1px solid var(--red)", marginBottom: 18 }}>
            <div className="row g8" style={{ marginBottom: 5 }}><LB red style={{ fontSize: 8.5 }}>{t("秘書建議")}</LB></div>
            <div style={{ fontSize: 12.5, lineHeight: 1.6 }}>{t("低於安全庫存,建議補")} <b className="num">{need} {item.unit || ""}</b> {t("(含 30% 緩衝)。")}</div>
          </div>
        )}
        {!!acts.length && <>
          <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {acts.map(([icon, label, prompt]) => (
              <button key={label} className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(prompt)}>
                <I name={icon} size={14}/>{t(label)}
              </button>
            ))}
          </div>
        </>}
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
      </div>
    </div>
  );
};

/* ═══ 05 · 智能預警 ═══ */
const LEVEL_META = { red: ["bad", "高危"], orange: ["warn", "重要"], yellow: ["warn", "留意"], blue: ["plain", "提示"] };
const ALERT_LEVELS = ["red", "orange", "yellow", "blue"];
const alertNumber = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};
const alertDisplay = (value) => value === null ? "—" : value;

const AlertRiskSpectrum = ({ summary, briefing, selected, onSelect }) => {
  const source = summary || briefing;
  if (!source) return <div className="alerts-viz-empty" aria-label={t("資料未載入")}>—</div>;
  const levels = source.levels && typeof source.levels === "object" ? source.levels : null;
  const critical = alertNumber(source.criticalCount);
  const rows = ALERT_LEVELS.map((level) => {
    const count = levels ? (alertNumber(levels[level]) || 0) : null;
    return { level, count: level === "red" ? (count === null || critical === null ? null : count + critical) : count };
  });
  const max = Math.max(1, ...rows.map(row => row.count === null ? 0 : row.count));
  return (
    <div className="alerts-spectrum">
      {rows.map(({ level, count }) => {
        const label = (LEVEL_META[level] || ["plain", level])[1];
        const active = selected === level;
        return (
          <button key={level} type="button" className={"alerts-spectrum-row " + level + (active ? " on" : "")}
            disabled={count === null} aria-pressed={active} aria-label={`${t(label)} · ${alertDisplay(count)} ${t("條")}`}
            onClick={() => onSelect(active ? "" : level)}>
            <span className="alerts-spectrum-label"><i/>{t(label)}</span>
            <span className="alerts-spectrum-track" aria-hidden="true"><i style={{ width: (count === null ? 0 : count / max * 100) + "%" }}/></span>
            <strong className="num">{alertDisplay(count)}</strong>
          </button>
        );
      })}
    </div>
  );
};

const AlertTrendViz = ({ trend }) => {
  if (trend === null) return <div className="alerts-viz-empty" aria-label={t("資料未載入")}>—</div>;
  const rows = Array.isArray(trend) ? trend.slice(-7) : [];
  if (!rows.length) return <div className="alerts-viz-empty small">{t("近 7 日沒有新增或處置事件")}</div>;
  const values = rows.reduce((all, row) => {
    const created = alertNumber(row.new);
    const handled = alertNumber(row.handled);
    if (created !== null) all.push(created);
    if (handled !== null) all.push(handled);
    return all;
  }, []);
  if (!values.length) return <div className="alerts-viz-empty" aria-label={t("資料未載入")}>—</div>;
  const max = Math.max(1, ...values);
  const xAt = (index) => 38 + index * (484 / Math.max(1, rows.length - 1));
  const yAt = (value) => 126 - (value / max) * 88;
  const points = (key) => rows.map((row, index) => {
    const value = alertNumber(row[key]);
    return value === null ? null : `${xAt(index)},${yAt(value)}`;
  }).filter(Boolean).join(" ");
  return (
    <div className="alerts-trend">
      <svg className="alerts-trend-svg" viewBox="0 0 560 168" role="img" aria-labelledby="alerts-trend-title alerts-trend-desc">
        <title id="alerts-trend-title">{t("近 7 日收斂")}</title>
        <desc id="alerts-trend-desc">{t("新增")} / {t("處置")} · 7 DAYS</desc>
        {[38, 82, 126].map((y) => <line key={y} className="grid" x1="38" y1={y} x2="522" y2={y}/>)}
        <polyline className="new" points={points("new")}/>
        <polyline className="handled" points={points("handled")}/>
        {rows.map((row, index) => {
          const created = alertNumber(row.new);
          const handled = alertNumber(row.handled);
          return (
            <g key={(row.date || "day") + index}>
              {created !== null && <circle className="new" cx={xAt(index)} cy={yAt(created)} r="3.5"/>}
              {handled !== null && <circle className="handled" cx={xAt(index)} cy={yAt(handled)} r="3.5"/>}
              <text x={xAt(index)} y="153" textAnchor="middle">{String(row.date || "—").slice(5)}</text>
            </g>
          );
        })}
      </svg>
      <div className="alerts-trend-legend" aria-hidden="true">
        <span><i className="new"/>{t("新增")}</span><span><i className="handled"/>{t("處置")}</span>
      </div>
    </div>
  );
};

const AlertCategoryViz = ({ categories, selected, onSelect }) => {
  if (categories === null) return <div className="alerts-viz-empty" aria-label={t("資料未載入")}>—</div>;
  const rows = (Array.isArray(categories) ? categories : []).slice(0, 6);
  if (!rows.length) return <div className="alerts-viz-empty small">{t("當前沒有活躍預警")}</div>;
  const max = Math.max(1, ...rows.map(row => alertNumber(row.count) || 0));
  return (
    <div className="alerts-categories">
      {rows.map((row, index) => {
        const name = row.name || row.category || t("其他");
        const count = alertNumber(row.count) || 0;
        const active = selected === name;
        return (
          <button key={name} type="button" className={"alerts-category-row" + (active ? " on" : "")}
            aria-pressed={active} aria-label={`${name} · ${count} ${t("條")}`}
            onClick={() => onSelect(active ? "" : name)}>
            <span className="num alerts-category-index">{pad2(index + 1)}</span>
            <span className="alerts-category-name">{name}</span>
            <span className="alerts-category-track" aria-hidden="true"><i style={{ width: (count / max * 100) + "%" }}/></span>
            <strong className="num">{count}</strong>
          </button>
        );
      })}
    </div>
  );
};

const PageAlerts2 = ({ boot, reload }) => {
  const fallbackAlerts = Array.isArray(boot.ALERTS) ? boot.ALERTS : [];
  const [snapshot, setSnapshot] = _s(null);
  const [briefing, setBriefing] = _s(null);
  const [snapshotError, setSnapshotError] = _s("");
  const [briefingError, setBriefingError] = _s("");
  const [loading, setLoading] = _s(false);
  const [levelFilter, setLevelFilter] = _s("");
  const [categoryFilter, setCategoryFilter] = _s("");
  const [aBusy, setABusy] = _s("");
  const [aErr, setAErr] = _s({});

  const loadAlerts = React.useCallback(async () => {
    setLoading(true);
    setSnapshotError("");
    setBriefingError("");
    const [snapshotResult, briefingResult] = await Promise.allSettled([
      W2.json("/api/alerts?status=open&limit=1000"),
      W2.json("/api/alerts/briefing"),
    ]);
    if (snapshotResult.status === "fulfilled") setSnapshot(snapshotResult.value);
    else {
      setSnapshot(null);
      setSnapshotError((snapshotResult.reason && snapshotResult.reason.message) || t("預警資料暫不可用"));
    }
    if (briefingResult.status === "fulfilled") setBriefing(briefingResult.value);
    else {
      setBriefing(null);
      setBriefingError((briefingResult.reason && briefingResult.reason.message) || t("預警資料暫不可用"));
    }
    setLoading(false);
  }, []);

  _e(() => { loadAlerts(); }, [loadAlerts]);

  const alerts = snapshot
    ? (Array.isArray(snapshot.mine) ? snapshot.mine : (Array.isArray(snapshot.alerts) ? snapshot.alerts : []))
    : fallbackAlerts;
  const filteredAlerts = _mm(() => alerts.filter((alert) => (
    (!levelFilter || (alert.level || "orange") === levelFilter)
    && (!categoryFilter || (alert.riskCategory || "通用風險") === categoryFilter)
  )), [alerts, levelFilter, categoryFilter]);
  const groups = _mm(() => ALERT_LEVELS
    .map(level => [level, filteredAlerts.filter(alert => (alert.level || "orange") === level)])
    .filter(([, rows]) => rows.length), [filteredAlerts]);

  const summary = snapshot && snapshot.summary ? snapshot.summary : null;
  const metricSource = summary || briefing;
  const levels = metricSource && metricSource.levels ? metricSource.levels : null;
  const openCount = summary
    ? (alertNumber(summary.open) !== null ? alertNumber(summary.open) : (Array.isArray(snapshot.mine) ? snapshot.mine.length : null))
    : (briefing ? alertNumber(briefing.mineOpen) : null);
  const visibleRed = levels ? (alertNumber(levels.red) || 0) : null;
  const criticalCount = metricSource ? alertNumber(metricSource.criticalCount) : null;
  const redCount = visibleRed === null || criticalCount === null ? null : visibleRed + criticalCount;
  const escalatedCount = metricSource ? alertNumber(metricSource.escalatedCount) : null;
  const handled7d = briefing ? alertNumber(briefing.handled7d) : null;
  const handledToday = briefing ? alertNumber(briefing.handledToday) : null;
  const todayNew = briefing ? alertNumber(briefing.todayNew) : null;
  const categories = summary && Array.isArray(summary.categories)
    ? summary.categories
    : (briefing && Array.isArray(briefing.categories) ? briefing.categories : null);
  const trend = briefing && Array.isArray(briefing.trend) ? briefing.trend : null;
  const critical = snapshot && Array.isArray(snapshot.critical) ? snapshot.critical : [];
  const hidden = snapshot && Array.isArray(snapshot.hidden) ? snapshot.hidden : [];
  const hiddenCount = summary ? alertNumber(summary.hiddenCount) : null;
  const filtersActive = !!(levelFilter || categoryFilter);

  const refreshAll = async () => {
    await loadAlerts();
    try { if (reload) await Promise.resolve(reload()); } catch (e) {}
  };

  /* 手動快捷:只在 mine 顯示一鍵處置;跨域紅色保持唯讀。 */
  const runAlert = async (a, action) => {
    const aid = a.id || a.rawId;
    if (!aid) return;
    setAErr(p => { const n = { ...p }; delete n[aid]; return n; });
    setABusy(aid + action);
    try {
      await W2.post("/api/alerts/" + encodeURIComponent(aid) + "/" + action, {});
      await loadAlerts();
      try { if (reload) await Promise.resolve(reload()); } catch (e) {}
    } catch (e) {
      setAErr(p => ({ ...p, [aid]: e.message || t("操作失敗") }));
    } finally { setABusy(""); }
  };
  let counter = 0;
  return (
    <div className="alerts-page">
      <Folio no="05" en="ALERTS" title={t("智能預警")}
        sub={briefing && briefing.oneLiner
          ? briefing.oneLiner
          : loading ? t("正在載入權限範圍內的風險態勢…")
            : snapshot ? (alerts.length ? t("{n} 條活躍預警 · AI 掃描,人工拍板", { n: alerts.length }) : t("當前沒有活躍預警"))
              : t("預警資料暫不可用")}
        right={<>
          <B icon="refresh" disabled={loading} onClick={refreshAll}>{loading ? t("處理中…") : t("刷新")}</B>
          {!!alerts.length && <B kind="primary" icon="sparkle" onClick={() => ask(t("把當前全部活躍預警按風險排序,逐條給我處置方案"))}>{t("全部交秘書分析")}</B>}
        </>}/>

      <div className="kpi-band alerts-kpis">
        <Kpi label={t("待處理")} value={alertDisplay(openCount)}
          foot={<span className="muted">{todayNew === null ? "—" : t("今日新增 {n}", { n: todayNew })}</span>}/>
        <Kpi label={t("紅色高危")} value={alertDisplay(redCount)} red={redCount !== null && redCount > 0}
          foot={<span className="muted">{visibleRed === null || criticalCount === null ? "—" : t("可見 {visible} · 跨域 {critical}", { visible: visibleRed, critical: criticalCount })}</span>}/>
        <Kpi label={t("超時升級")} value={alertDisplay(escalatedCount)} red={escalatedCount !== null && escalatedCount > 0}
          foot={<span className="muted">{escalatedCount === null ? "—" : t("超時仍未處置")}</span>}/>
        <Kpi label={t("近 7 日已處置")} value={alertDisplay(handled7d)}
          foot={<span className="muted">{handledToday === null ? "—" : t("今日已處置 {n}", { n: handledToday })}</span>}/>
      </div>

      {(snapshotError || briefingError) && (
        <div className="alerts-load-note" role="status">
          <I name="alert" size={14}/><span>{t("部分資料載入失敗")}</span>
          <span className="muted">{[snapshotError, briefingError].filter(Boolean).join(" · ")}</span>
        </div>
      )}

      <Band no="01" title={t("風險態勢")} sub={t("點擊圖表即可篩選處置清單")}>
        <div className="alerts-swiss-grid">
          <article className="alerts-viz-card">
            <header><span className="num">01</span><div><h3>{t("風險態勢")}</h3><p>{t("點擊風險級別篩選待處理清單")}</p></div></header>
            <AlertRiskSpectrum summary={summary} briefing={briefing} selected={levelFilter} onSelect={setLevelFilter}/>
          </article>
          <article className="alerts-viz-card">
            <header><span className="num">02</span><div><h3>{t("近 7 日收斂")}</h3><p>{t("新增")} / {t("處置")} · 7 DAYS</p></div></header>
            <AlertTrendViz trend={trend}/>
          </article>
          <article className="alerts-viz-card">
            <header><span className="num">03</span><div><h3>{t("風險類別 TOP")}</h3><p>{t("點擊類別篩選待處理清單")}</p></div></header>
            <AlertCategoryViz categories={categories} selected={categoryFilter} onSelect={setCategoryFilter}/>
          </article>
        </div>
      </Band>

      <Band no="02" title={t("處置清單")} sub={t("依照權限顯示可操作預警")}
        right={filtersActive && <button type="button" className="alerts-clear-filter" onClick={() => { setLevelFilter(""); setCategoryFilter(""); }}>
          <I name="x" size={13}/>{t("清除篩選")}
        </button>}>
        {filtersActive && <div className="alerts-filter-state" role="status">
          <LB red>{t("篩選中")}</LB>
          {levelFilter && <T tone={(LEVEL_META[levelFilter] || ["plain"])[0]}>{t((LEVEL_META[levelFilter] || ["", levelFilter])[1])}</T>}
          {categoryFilter && <T>{categoryFilter}</T>}
          <span className="num">{filteredAlerts.length}</span>
        </div>}
        {!alerts.length && <EM icon="checkCircle" title={t("倉庫很安靜")} sub={t("沒有需要處理的預警。秘書持續掃描中,有風險會第一時間出現在這裡。")}/>}
        {!!alerts.length && !filteredAlerts.length && <EM icon="search" title={t("篩選後沒有符合的預警")}
          action={<button type="button" className="btn" onClick={() => { setLevelFilter(""); setCategoryFilter(""); }}>{t("清除篩選")}</button>}
        />}
      {groups.map(([lv, arr], gi) => {
        const [tone, label] = LEVEL_META[lv] || ["plain", lv];
        return (
          <section key={lv} className="alerts-level-group rise" style={{ animationDelay: (gi * .06) + "s" }}>
            <div className="alerts-level-head"><h3><span className="num">{pad2(gi + 1)}</span>{t(label)}</h3><strong className="num">{arr.length}</strong></div>
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {arr.map((a, i) => {
                counter += 1;
                return (
                  <div key={a.id || i} className="ledger-row">
                    <span className="lr-idx">{pad2(counter)}</span>
                    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                      <div className="row g10">
                        <span style={{ fontWeight: 650, fontSize: 13.5 }}>{a.item_name || a.item || a.alert_type || a.type || t("預警")}</span>
                        <T tone={tone} dot>{t(label)}</T>
                        {a.riskCategory && <T tone="plain">{a.riskCategory}</T>}
                        {a.escalated && <T tone="bad">{t("超時升級")}</T>}
                      </div>
                      <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.55 }}>{a.suggestion || a.suggest || a.msg || a.scope || t("待處理")}</div>
                      {aErr[a.id || a.rawId] && <div style={{ fontSize: 10.5, color: "var(--red)" }}>{aErr[a.id || a.rawId]}</div>}
                    </div>
                    {(() => {
                      const rowId = a.id || a.rawId;
                      const rowBusy = aBusy === rowId + "resolve" || aBusy === rowId + "dismiss";
                      return (
                        <div className="row g4 alerts-actions">
                          <B size="sm" icon="check" disabled={rowBusy} onClick={() => runAlert(a, "resolve")}>{aBusy === rowId + "resolve" ? t("處理中…") : t("已處置")}</B>
                          <B size="sm" kind="ghost" disabled={rowBusy} onClick={() => runAlert(a, "dismiss")}>{aBusy === rowId + "dismiss" ? "…" : t("忽略")}</B>
                          <B size="sm" icon="sparkle" title={t("交秘書處置")} onClick={() => ask(t("分析並處置這條預警:{t},級別 {lv};建議「{s}」。給出方案,經我確認後執行。", { t: a.item_name || a.item || a.alert_type || a.type || a.id, lv: a.level || "—", s: a.suggestion || a.suggest || "—" }))}/>
                        </div>
                      );
                    })()}
                  </div>
                );
              })}
            </div>
          </section>
        );
      })}
      </Band>

      {!!critical.length && (
        <Band no="03" title={t("跨域紅色高危")} sub={t("唯讀兜底 · 由相關責任人處置")}
          right={<T tone="bad">{t("唯讀")}</T>}>
          <div className="alerts-critical-list">
            {critical.map((alert, index) => (
              <div className="alerts-critical-row" key={alert.id || alert.rawId || index}>
                <span className="num alerts-critical-index">{pad2(index + 1)}</span>
                <div className="col g4">
                  <div className="row g8 wrap"><strong>{alert.item || alert.type || t("預警")}</strong><T tone="bad" dot>{t("高危")}</T>{alert.riskCategory && <T>{alert.riskCategory}</T>}</div>
                  <p>{alert.suggest || alert.scope || t("待處理")}</p>
                </div>
                <div className="alerts-critical-owner"><span>{t("負責人")}</span><strong>{alert.owner || t("相關負責人")}</strong><T tone="plain">{t("唯讀")}</T></div>
              </div>
            ))}
          </div>
        </Band>
      )}

      {hiddenCount !== null && hiddenCount > 0 && (
        <Band no="04" title={t("權限外風險摘要")} sub={t("僅顯示聚合數字,不展示明細")}>
          <div className="alerts-hidden-grid">
            <div className="alerts-hidden-total"><span>{t("其餘權限外風險")}</span><strong className="num">{hiddenCount}</strong></div>
            {hidden.map((item, index) => (
              <div key={(item.category || "hidden") + index} className="alerts-hidden-cell">
                <span>{item.category || t("其他")}</span><strong className="num">{alertDisplay(alertNumber(item.count))}</strong><small>{item.owner || t("相關負責人")}</small>
              </div>
            ))}
          </div>
        </Band>
      )}
    </div>
  );
};

/* ═══ 橋接頁 ═══ */
const BRIDGE_META = {
  inbound: ["03", "INBOUND", "入庫", "採購到貨 · 檢修退庫 · 調撥入庫,含批次與單據"],
  outbound: ["04", "OUTBOUND", "出庫", "領用出庫 · 借用歸還 · 搶修綠色通道"],
  stocktake: ["06", "STOCKTAKE", "盤點", "盤點計劃 · 差異分析 · 賬實核對"],
  erp: ["07", "ERP", "ERP 中樞", "預算 · 成本中心 · 採購申請 · 業財一體化"],
  finance: ["08", "FINANCE", "財務", "複式總賬 · 憑證 · 三大報表 · AA 記賬"],
  assets: ["09", "ASSETS", "資產", "金融資產 · 數字資產市場 · AI 評估"],
  research: ["R01", "RESEARCH", "科研工作台", "可重現研究 · 文件版本 · 語義差異"],
  procurement: ["10", "PROCUREMENT", "採購招標", "採購流程 · 招標評審 · 供應商"],
  gis: ["11", "MAP / GIS", "倉庫地圖", "倉庫 GIS 定位 · 庫區與貨位可視化"],
  reports: ["12", "REPORTS", "報表", "經營報表 · 導出"],
  perms: ["13", "ACCESS", "權限", "角色 · 審批 · 成員管理"],
  logs: ["16", "AUDIT", "審計日誌", "全平台操作留痕回放"],
  cases: ["17", "RECORDS", "檔案管理", "人員 · 會議 · 培訓 · 安全 · 事務檔案"],
  settings: ["18", "SETTINGS", "設置", "系統與 AI 配置"],
  legal: ["—", "LEGAL", "法務", "合同 · 鋼印鏈 · 爭議"],
  companies: ["—", "COMPANIES", "公司", "多公司開通 · 租戶管理"],
};
const PageBridge = ({ route }) => {
  const [no, en, title, desc] = BRIDGE_META[route] || ["—", "MODULE", "模塊", ""];
  return (
    <>
      <Folio no={no} en={en} title={t(title)} sub={t(desc)}/>
      <div className="rise" style={{ padding: "48px 0", animationDelay: ".05s" }}>
        <div style={{ maxWidth: 620 }}>
          <LB red style={{ marginBottom: 16 }}>REDESIGN IN PROGRESS</LB>
          <div style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-.03em", lineHeight: 1.35, marginBottom: 14 }}>
            {t("此模塊的 2.1 版式在排期中。")}
          </div>
          <div className="row g10" style={{ marginTop: 26 }}>
            <B icon="sparkle" onClick={() => ask(t("關於{t}({d}):現在有什麼需要我處理的?", { t: t(title), d: t(desc) }))}>{t("先問秘書")}</B>
          </div>
          <div className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".18em", marginTop: 30 }}>SAME BACKEND · SAME DATA · ZERO LOSS</div>
        </div>
      </div>
    </>
  );
};

// 共享給各模塊頁文件(pages/pages-*.jsx)的版式原語與工具
Object.assign(W2, { Folio, Band, pad2, num, HBar });

W2.PAGES = W2.PAGES || {};
Object.assign(W2.PAGES, {
  dashboard: PageDashboard,
  inventory: PageInventory2,
  alerts: PageAlerts2,
  __bridge: PageBridge,
});
Object.keys(BRIDGE_META).forEach(k => { if (!W2.PAGES[k]) W2.PAGES[k] = PageBridge; });
})();
