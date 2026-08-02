/* WAREHOUSE 2.1 · 公司總覽 — permission-scoped executive cockpit */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { Icon: I, Btn: B, Tag: T, Empty: EM, Kpi, MirrorBars, TrendArea, Meter, Folio } = W2;
const { useEffect, useMemo, useState } = React;

window.W2_LANG.addEN({
  "公司總覽": "Company overview",
  "跨財務、營運、資產與治理的管理駕駛艙": "Management cockpit across finance, operations, assets and governance",
  "管理訊號": "Management signals",
  "授權模組": "Authorised modules",
  "本年淨利": "Net profit · YTD",
  "公司現金": "Company cash",
  "預算使用率": "Budget utilisation",
  "最高預算使用率": "Highest budget utilisation",
  "金融資產市值": "Financial assets",
  "伺服器按目前帳號逐域裁切": "Server-filtered domain by domain for the current account",
  "刷新總覽": "Refresh overview",
  "資料更新於": "Data updated",
  "財務脈搏": "Financial pulse",
  "收入、成本、利潤與現金": "revenue, cost, profit and cash",
  "營業收入": "Revenue",
  "成本費用": "Cost & expenses",
  "當月現金淨變動": "Monthly cash change",
  "待處理財務事件": "Pending finance events",
  "應收": "Receivable",
  "應付": "Payable",
  "資產負債表平衡": "Balance sheet balanced",
  "資產負債表待覆核": "Balance sheet needs review",
  "預算與執行": "Budget & execution",
  "撥款、佔用、支出與可用額": "appropriation, reservation, spend and availability",
  "預算總額": "Budget total",
  "已支出": "Spent",
  "已佔用": "Reserved",
  "可用": "Available",
  "待關聯庫存單據": "Unlinked inventory documents",
  "開放工單": "Open work orders",
  "開放採購": "Open purchases",
  "庫管健康": "Warehouse health",
  "庫存、收發、在途與異常": "inventory, flows, transit and exceptions",
  "在管 SKU": "Managed SKUs",
  "低庫存": "Low stock",
  "待入庫": "Open inbound",
  "待出庫": "Open outbound",
  "在途": "In transit",
  "延誤": "Delayed",
  "採購漏斗": "Procurement funnel",
  "待辦、逾期與流程閉環": "tasks, overdue work and process closure",
  "待辦": "Inbox",
  "逾期": "Overdue",
  "進行中": "Running",
  "已閉環": "Closed",
  "全公司視角": "Company scope",
  "個人可見視角": "Personal visible scope",
  "風險與決策": "Risk & decisions",
  "跨模組按嚴重度排序": "ranked across modules by severity",
  "目前沒有需要管理層關注的訊號": "No signals currently require management attention",
  "資產版圖": "Asset landscape",
  "金融資產與數字資產": "financial and digital assets",
  "浮動盈虧": "Unrealised P&L",
  "數字資產估值": "Digital asset valuation",
  "已上架": "Listed",
  "治理與履約": "Governance & obligations",
  "合同、事務、檔案與組織控制": "contracts, cases, records and organisational controls",
  "生效合同": "Active contracts",
  "高風險合同": "High-risk contracts",
  "到期證照": "Expired licences",
  "待履約里程碑": "Open milestones",
  "開放事務": "Open cases",
  "高風險事務": "High-risk cases",
  "檔案總數": "Records",
  "公司運行面": "Company operating surface",
  "每個入口均沿用原有路由與權限": "Every entry preserves its original route and permissions",
  "模組視覺圖譜": "Module visual atlas",
  "每個獲授權功能都有一個可展開、可直達的管理視角": "Every authorised module has an expandable management view with direct access",
  "主要指標": "Primary metric",
  "資料軌跡": "Data trace",
  "可視化詳情": "Visual details",
  "配置就緒": "Configuration readiness",
  "定位完整率": "Location completeness",
  "預警處理率": "Alert handling rate",
  "可匯出報表": "Exportable reports",
  "規則啟用": "Rules enabled",
  "AI 已配置": "AI configured",
  "AI 已連接": "AI connected",
  "權限可見範圍": "Permission-visible scope",
  "完整公司視角": "Full company scope",
  "受限組織視角": "Restricted organisation scope",
  "四級風險頻譜": "Four-level risk spectrum",
  "盤點閉環": "Stocktake closure",
  "開放任務": "Open tasks",
  "已閉環任務": "Closed tasks",
  "捕捉記錄": "Captured records",
  "資本配置": "Capital allocation",
  "流程狀態": "Workflow state",
  "履約風險": "Obligation risk",
  "營運報告節奏": "Operating report rhythm",
  "組織授權拓撲": "Organisation access topology",
  "審計事件帶": "Audit event band",
  "事務與檔案週期": "Case and record lifecycle",
  "已閉環事務": "Closed cases",
  "有效檔案": "Active records",
  "歸檔": "Archived",
  "展開詳情": "Expand details",
  "收起詳情": "Collapse details",
  "進入功能": "Open module",
  "資料暫時不可用": "Data temporarily unavailable",
  "沒有把載入失敗顯示成零值": "A load failure is not shown as a zero",
  "公司總覽載入失敗": "Company overview failed to load",
  "請重試；其他功能不受影響。": "Retry; other modules are unaffected.",
  "盤點差異": "Stocktake differences",
  "未定位庫位": "Unlocated locations",
  "有效委派": "Active delegations",
  "已指派用戶": "Assigned users",
  "角色指派": "Role assignments",
  "權限分享": "Permission shares",
  "失敗審計事件": "Failed audit events",
  "預警": "Alerts",
  "升級預警": "Escalated alerts",
  "負利潤": "Negative profit",
  "負現金流": "Negative cash flow",
  "預算超額": "Budget overrun",
  "採購逾期": "Procurement overdue",
  "待處理財務事件": "Pending finance events",
  "庫管異常": "Warehouse exception",
  "合同風險": "Contract risk",
  "事務風險": "Case risk",
  "審計失敗": "Audit failure",
  "AI 連接異常": "AI connection issue",
  "模組詳情": "Module details",
  "多幣別": "Multiple currencies",
  "幣別": "currencies",
  "本期沒有預算數據": "No budget data for this period",
  "案件總覽": "Case overview",
  "案件、工作、卷宗、機構與倫理規則的學術協作總覽": "Academic collaboration overview for cases, work, records, institutions, and ethics rules",
  "待關注事項": "Items requiring attention",
  "可用工作區": "Available workspaces",
  "按目前帳號的職位與案件權限顯示": "Shown according to the current account's position and case access",
  "刷新案件總覽": "Refresh case overview",
  "目前沒有需要關注的案件工作": "No case work currently needs attention",
  "法律工作概覽": "Legal work overview",
  "案件、卷宗、機構與程序記錄": "cases, records, institutions, and procedure history",
  "進行中案件": "Active cases",
  "優先關注案件": "Priority cases",
  "卷宗總數": "Case files",
  "工作區一覽": "Workspace overview",
  "每個獲授權工作區均保留原有路由與權限": "Every authorised workspace preserves its existing route and access rules",
  "案件關注": "Case attention",
  "按程序期限與核查狀態排序": "Ranked by procedure deadlines and review status",
  "案件待核查": "Cases requiring review",
  "程序記錄待核查": "Procedure entries requiring review",
  "程序與卷宗週期": "Procedure and record lifecycle",
  "案件總數": "Cases",
  "進行中案件": "Active cases",
  "已結案案件": "Concluded cases",
  "有效卷宗": "Active records",
  "法律倫理規則": "Legal ethics rules",
  "機構職位": "Institution positions",
  "秘書連接": "Secretary connection",
  "學術工作區就緒": "Academic workspace readiness",
  "案件總覽載入失敗": "Case overview failed to load",
});

const DASHBOARD_BIU_COPY = Object.freeze({
  "公司總覽": "案件總覽",
  "跨財務、營運、資產與治理的管理駕駛艙": "案件、工作、卷宗、機構與倫理規則的學術協作總覽",
  "管理訊號": "待關注事項", "授權模組": "可用工作區",
  "伺服器按目前帳號逐域裁切": "按目前帳號的職位與案件權限顯示",
  "刷新總覽": "刷新案件總覽",
  "目前沒有需要管理層關注的訊號": "目前沒有需要關注的案件工作",
  "治理與履約": "法律工作概覽", "合同、事務、檔案與組織控制": "案件、卷宗、機構與程序記錄",
  "開放事務": "進行中案件", "高風險事務": "優先關注案件", "檔案總數": "卷宗總數",
  "模組視覺圖譜": "工作區一覽",
  "每個獲授權功能都有一個可展開、可直達的管理視角": "每個獲授權工作區均保留原有路由與權限",
  "風險與決策": "案件關注", "跨模組按嚴重度排序": "按程序期限與核查狀態排序",
  "事務風險": "案件待核查", "審計失敗": "程序記錄待核查",
  "公司總覽載入失敗": "案件總覽載入失敗",
});
const dashboardText = (biu, value) => t(biu ? (DASHBOARD_BIU_COPY[value] || value) : value);

const n = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
};
const fmt = (value, digits = 0) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return number.toLocaleString(undefined, { maximumFractionDigits: digits });
};
const money = (value) => {
  if (value === null || value === undefined || value === "") return ["—", ""];
  const number = Number(value);
  if (!Number.isFinite(number)) return ["—", ""];
  if (Math.abs(number) >= 100000000) return [fmt(number / 100000000, 2), t("億")];
  if (Math.abs(number) >= 10000) return [fmt(number / 10000, 2), t("萬")];
  return [fmt(number, 0), ""];
};
const currencyText = (values) => {
  const rows = Object.entries(values || {}).filter(([, value]) => Number.isFinite(Number(value)));
  if (!rows.length) return "—";
  if (rows.length > 1) return t("多幣別") + " · " + rows.map(([key, value]) => `${key} ${fmt(value, 2)}`).join(" / ");
  return rows[0][0] + " " + fmt(rows[0][1], 2);
};
const currencyAmount = (currency, value) => {
  const compact = money(value);
  return `${currency || "—"} ${compact[0]}${compact[1] ? " " + compact[1] : ""}`;
};
const go = (route) => { location.hash = "#/" + route; };

const ExecCard = ({ id, no, title, sub, route, expanded, onToggle, children, detail, wide = false }) => (
  <section className={`exec-card rise${wide ? " wide" : ""}`} aria-labelledby={`exec-title-${id}`}>
    <header className="exec-card-head">
      <div>
        <span className="exec-card-no">{no}</span>
        <h2 id={`exec-title-${id}`}>{title}</h2>
        {sub && <p>{sub}</p>}
      </div>
      <div className="row g6 wrap exec-card-actions">
        {detail && <button type="button" className="btn sm" aria-expanded={!!expanded}
          aria-controls={`exec-detail-${id}`} onClick={onToggle}>
          <I name="chevronDown" size={12} style={expanded ? { transform: "rotate(180deg)" } : undefined}/>{t(expanded ? "收起詳情" : "展開詳情")}
        </button>}
        {route && <a className="btn sm" href={`#/${route}`}>{t("進入功能")} →</a>}
      </div>
    </header>
    <div className="exec-card-body">{children}</div>
    {detail && expanded && <div id={`exec-detail-${id}`} className="exec-card-detail">{detail}</div>}
  </section>
);

const Stat = ({ label, value, unit, bad, note }) => (
  <div className={`exec-stat${bad ? " bad" : ""}`}>
    <span>{label}</span>
    <strong className="num">{value}<small>{unit || ""}</small></strong>
    {note && <em>{note}</em>}
  </div>
);

const Unavailable = () => <EM icon="alert" title={t("資料暫時不可用")} sub={t("沒有把載入失敗顯示成零值")}/>;

const EXECUTIVE_VISUAL_ROUTES = [
  "warehouse", "alerts", "stocktake", "erp", "finance", "assets", "procurement",
  "legal", "gis", "reports", "perms", "logs", "cases", "settings",
];
const BIU_DASHBOARD_ROUTES = new Set(["dashboard", "tasks", "cases", "perms", "logs", "settings"]);
const EXECUTIVE_VISUAL_SPECS = {
  warehouse: { key: "warehouse", access: ["warehouse"], kind: "bars" },
  alerts: { key: "alerts", access: ["alerts"], kind: "radial" },
  stocktake: { key: "stocktake", access: ["stocktake"], kind: "bars" },
  erp: { key: "erp", access: ["erp"], kind: "radial" },
  finance: { key: "finance", access: ["finance"], kind: "line" },
  assets: { key: "assets", access: ["assets_financial", "assets_digital"], kind: "radial" },
  procurement: { key: "procurement", access: ["procurement"], kind: "funnel" },
  legal: { key: "legal", access: ["legal"], kind: "bars" },
  gis: { key: "gis", access: ["gis"], kind: "nodes" },
  reports: { key: "reports", access: ["reports"], kind: "line" },
  perms: { key: "permissions", access: ["permissions"], kind: "nodes" },
  logs: { key: "audit", access: ["audit"], kind: "radial" },
  cases: { key: "cases", access: ["cases", "records"], kind: "bars" },
  settings: { key: "settings", access: ["settings"], kind: "matrix" },
};
const finite = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};
const metricText = (value, digits = 0) => value == null ? "—" : fmt(value, digits);
const compactMetric = (value) => {
  const number = finite(value);
  if (number == null) return "—";
  if (Math.abs(number) >= 1000000000) return `${fmt(number / 1000000000, 1)}B`;
  if (Math.abs(number) >= 1000000) return `${fmt(number / 1000000, 1)}M`;
  if (Math.abs(number) >= 1000) return `${fmt(number / 1000, 1)}K`;
  return fmt(number, 1);
};
const cleanSeries = (series) => (series || []).flatMap(item => {
  const value = finite(item && item.value);
  return value == null ? [] : [{ ...item, value }];
});

const ModuleGraphic = ({ kind, series, matrix, scaleMax, label }) => {
  const prepared = cleanSeries(series);
  const rows = (kind === "line" ? prepared.slice(-12) : prepared.slice(0, 8));
  const description = rows.map(row => `${row.label || "—"}: ${fmt(row.value, 2)}`).join(" · ");
  if (kind === "matrix") {
    const rawTotal = finite(matrix && matrix.total);
    const rawValue = finite(matrix && matrix.value);
    if (rawTotal == null || rawValue == null || rawTotal <= 0) return <div className="exec-viz-empty" role="img" aria-label={label}>—</div>;
    const total = Math.max(0, rawTotal);
    const value = Math.max(0, Math.min(total, rawValue));
    const active = total > 0 ? Math.round(value / total * 24) : 0;
    return <div className="exec-viz-matrix" role="img" aria-label={`${label} · ${value}/${total || "—"}`}>
      {Array.from({ length: 24 }, (_, index) => <i key={index} className={index < active ? "on" : ""}/>) }
    </div>;
  }
  if (!rows.length) return <div className="exec-viz-empty" role="img" aria-label={label}>—</div>;
  if (kind === "funnel") {
    const max = Math.max(1, ...rows.map(row => Math.abs(row.value)));
    return <div className="exec-viz-funnel" role="img" aria-label={label}>
      {rows.slice(0, 5).map((row, index) => <div key={(row.label || "—") + index}>
        <span>{row.label || "—"}</span><i style={{ width: Math.max(12, Math.abs(row.value) / max * 100) + "%" }} className={row.bad ? "bad" : ""}/><b className="num">{fmt(row.value)}</b>
      </div>)}
    </div>;
  }
  if (kind === "radial") {
    const base = finite(scaleMax) || Math.max(1, Math.abs(rows[0].value), ...rows.map(row => Math.abs(row.value)));
    return <svg className="exec-viz-svg radial" viewBox="0 0 280 106" role="img" aria-label={label}>
      <title>{label}</title><desc>{description}</desc>
      <g transform="translate(140 53) rotate(-90)">
        {rows.slice(0, 4).map((row, index) => {
          const radius = 42 - index * 9;
          const circumference = 2 * Math.PI * radius;
          const progress = Math.min(1, Math.abs(row.value) / base);
          return <React.Fragment key={(row.label || "—") + index}>
            <circle className="track" cx="0" cy="0" r={radius}/>
            <circle className={row.bad ? "signal bad" : "signal"} cx="0" cy="0" r={radius}
              strokeDasharray={`${circumference * progress} ${circumference}`}/>
          </React.Fragment>;
        })}
      </g>
      <text x="140" y="50" textAnchor="middle" className="value">{compactMetric(rows[0].value)}</text>
      <text x="140" y="66" textAnchor="middle" className="caption">{String(rows[0].label || "").slice(0, 12)}</text>
    </svg>;
  }
  if (kind === "nodes") {
    const max = Math.max(1, ...rows.map(row => Math.abs(row.value)));
    const positions = [[42,58],[105,28],[151,73],[220,35],[245,82],[88,88]];
    return <svg className="exec-viz-svg nodes" viewBox="0 0 280 106" role="img" aria-label={label}>
      <title>{label}</title><desc>{description}</desc>
      {positions.slice(1, rows.length).map((point, index) => <line key={index} x1={positions[index][0]} y1={positions[index][1]} x2={point[0]} y2={point[1]}/>) }
      {rows.slice(0, positions.length).map((row, index) => {
        const point = positions[index];
        const radius = 6 + Math.abs(row.value) / max * 13;
        return <g key={(row.label || "—") + index}><circle className={row.bad ? "bad" : ""} cx={point[0]} cy={point[1]} r={radius}/><text x={point[0]} y={point[1] + 3} textAnchor="middle">{compactMetric(row.value)}</text></g>;
      })}
    </svg>;
  }
  if (kind === "line") {
    const values = rows.map(row => row.value);
    const min = Math.min(0, ...values);
    const max = Math.max(0, ...values);
    const span = Math.max(1, max - min);
    const coords = rows.map((row, index) => {
      const x = rows.length === 1 ? 140 : 12 + index / (rows.length - 1) * 256;
      const y = 91 - (row.value - min) / span * 70;
      return [x, y];
    });
    const baseline = 91 - (0 - min) / span * 70;
    const points = coords.map(point => point.join(",")).join(" ");
    return <svg className="exec-viz-svg line" viewBox="0 0 280 106" role="img" aria-label={label}>
      <title>{label}</title><desc>{description}</desc>
      {[21,56,91].map(y => <line className="grid" key={y} x1="10" y1={y} x2="270" y2={y}/>)}
      <line className="baseline" x1="10" y1={baseline} x2="270" y2={baseline}/>
      <polygon points={`${coords[0][0]},${baseline} ${points} ${coords[coords.length - 1][0]},${baseline}`}/>
      <polyline points={points}/>
      {coords.map((point, index) => <circle key={index} className={rows[index].bad ? "bad" : ""} cx={point[0]} cy={point[1]} r="2.8"><title>{`${rows[index].label || "—"}: ${fmt(rows[index].value, 2)}`}</title></circle>)}
    </svg>;
  }
  const max = Math.max(1, ...rows.map(row => Math.abs(row.value)));
  const width = Math.min(31, 202 / rows.length);
  return <svg className="exec-viz-svg bars" viewBox="0 0 280 106" role="img" aria-label={label}>
    <title>{label}</title><desc>{description}</desc>
    {[24,56,88].map(y => <line className="grid" key={y} x1="10" y1={y} x2="270" y2={y}/>)}
    {rows.map((row, index) => {
      const slot = 250 / rows.length;
      const x = 15 + index * slot + (slot - width) / 2;
      const height = Math.max(row.value ? 3 : 1, Math.abs(row.value) / max * 70);
      return <g key={(row.label || "—") + index}><rect className={row.bad ? "bad" : ""} x={x} y={90 - height} width={width} height={height}/><title>{`${row.label || "—"}: ${fmt(row.value, 2)}`}</title></g>;
    })}
  </svg>;
};

const ModuleVisualCard = ({ item, index, model, expanded, onToggle }) => {
  const detailId = `exec-module-detail-${item.id}`;
  const legendRows = cleanSeries(model.series);
  const visibleLegend = (model.kind === "line" ? legendRows.slice(-4) : legendRows.slice(0, 4));
  return <article className={`exec-module-viz-card${model.available ? "" : " unavailable"}`} data-module={item.id}>
    <header>
      <span className="num">{String(index + 1).padStart(2, "0")}</span>
      <I name={item.id === "warehouse" ? "inventory" : item.id} size={15}/>
      <div><b>{t(item.label)}</b><em>{t(model.kicker || "資料軌跡")}</em></div>
      {model.available && <button type="button" aria-expanded={!!expanded} aria-controls={detailId} onClick={onToggle}
        aria-label={t(expanded ? "收起詳情" : "展開詳情")} title={t(expanded ? "收起詳情" : "展開詳情")}><I name="chevronDown" size={13} style={expanded ? { transform: "rotate(180deg)" } : undefined}/></button>}
    </header>
    {model.available ? <>
      <button type="button" className="exec-module-viz-hit" onClick={onToggle} aria-expanded={!!expanded} aria-controls={detailId}
        aria-label={`${t(expanded ? "收起詳情" : "展開詳情")} · ${t(item.label)}`}>
        <div className="exec-module-viz-value"><span>{t("主要指標")}</span><strong className={model.bad ? "num bad" : "num"}>{model.value}<small>{model.unit || ""}</small></strong></div>
        <div className="exec-module-viz-graphic">
          <ModuleGraphic kind={model.kind} series={model.series} matrix={model.matrix} scaleMax={model.scaleMax} label={`${t(item.label)} · ${t(model.kicker || "資料軌跡")}`}/>
          {!!visibleLegend.length && <div className="exec-module-viz-legend">
            {visibleLegend.map((row, rowIndex) => <span key={(row.label || "—") + rowIndex}><i className={row.bad ? "bad" : ""}/><em>{t(row.label || "—")}</em><b className="num">{compactMetric(row.value)}</b></span>)}
          </div>}
        </div>
      </button>
      <p>{model.summary || "—"}</p>
      <div className="exec-module-viz-detail" id={detailId} hidden={!expanded}>
        {(model.details || []).map((row, detailIndex) => <div key={(row.label || "—") + detailIndex}><span>{t(row.label)}</span><b className={row.bad ? "num bad" : "num"}>{row.value == null ? "—" : row.value}</b></div>)}
      </div>
    </> : model.pending
      ? <div className="exec-loading-note"><span className="label">{t("COMPUTING")}</span></div>
      : <Unavailable/>}
    <footer><span className="mono">PERMISSION-FILTERED</span><a href={`#/${item.id}`}>{t("進入功能")} →</a></footer>
  </article>;
};

const PageExecutiveDashboard = ({ boot, navItems = [], warehouseTabs = [], templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const [snapshot, setSnapshot] = useState(null);
  const [refreshedHub, setRefreshedHub] = useState(null);
  const [hubRefreshFailed, setHubRefreshFailed] = useState(false);
  const [error, setError] = useState(null);
  const [reloadNo, setReloadNo] = useState(0);
  const [expanded, setExpanded] = useState({});
  useEffect(() => {
    let alive = true;
    setSnapshot(null); setError(null);
    setHubRefreshFailed(false);
    if (reloadNo > 0) setRefreshedHub(null);
    W2.json("/api/overview/executive")
      .then(data => {
        if (!alive) return;
        if (!data || data.scope !== "permission-filtered" || !data.modules) throw new Error(t("公司總覽載入失敗"));
        setSnapshot(data);
        if (reloadNo > 0 && data.access && data.access.warehouse) {
          W2.json("/api/bootstrap")
            .then(nextBoot => {
              if (!alive) return;
              const nextHub = nextBoot && nextBoot.WAREHOUSE_HUB;
              if (!nextHub || nextHub.scope !== "permission-filtered") throw new Error("warehouse hub unavailable");
              setRefreshedHub(nextHub);
            })
            .catch(() => alive && setHubRefreshFailed(true));
        }
      })
      .catch(reason => alive && setError(reason));
    return () => { alive = false; };
  }, [reloadNo]);

  const visible = useMemo(() => new Set((navItems || []).map(item => item.id)), [navItems]);
  const visibleWarehouseRoutes = useMemo(() => new Set((warehouseTabs || []).map(item => item.id)), [warehouseTabs]);
  const access = snapshot && snapshot.access || {};
  const modules = snapshot && snapshot.modules || {};
  const initialHub = boot && boot.WAREHOUSE_HUB && boot.WAREHOUSE_HUB.scope === "permission-filtered"
    ? boot.WAREHOUSE_HUB : null;
  const hubCandidate = reloadNo > 0 ? (refreshedHub || initialHub) : initialHub;
  const hub = snapshot && access.warehouse && !hubRefreshFailed ? hubCandidate : null;
  const canShow = (route) => visible.has(route) && (!biu || BIU_DASHBOARD_ROUTES.has(route));
  const ready = (key, route) => canShow(route) && modules[key] && modules[key].status === "ready";
  const authorised = (key, route) => canShow(route) && access[key];
  const toggle = (key) => setExpanded(value => ({ ...value, [key]: !value[key] }));

  const priorities = useMemo(() => {
    if (!snapshot) return [];
    const out = [];
    const add = (key, label, count, route, severity = "medium") => {
      const value = n(count);
      if (value > 0 && canShow(route === "inventory" || route === "inbound" || route === "outbound" || route === "shipments" ? "warehouse" : route)) {
        out.push({ key, label, count: value, route, severity });
      }
    };
    if (hub && canShow("warehouse")) (hub.anomalies || []).forEach(item => {
      if (visibleWarehouseRoutes.has(item.route)) add("warehouse:" + item.key, item.label || t("庫管異常"), item.count, item.route, item.severity === "high" ? "high" : "medium");
    });
    const alerts = modules.alerts || {};
    if (ready("alerts", "alerts")) {
      add("alerts:red", t("預警"), alerts.red, "alerts", "high");
      add("alerts:escalated", t("升級預警"), alerts.escalated, "alerts", "high");
    }
    const finance = modules.finance || {};
    if (ready("finance", "finance")) {
      add("finance:pending", t("待處理財務事件"), finance.pending_events, "finance", "medium");
      add("finance:profit", t("負利潤"), n(finance.profit) < 0 ? 1 : 0, "finance", "high");
      add("finance:cash", t("負現金流"), n(finance.cash_net_month) < 0 ? 1 : 0, "finance", "medium");
      add("finance:balance", t("資產負債表待覆核"), finance.balanced === false ? 1 : 0, "finance", "high");
    }
    const erp = modules.erp || {};
    if (ready("erp", "erp")) {
      add("erp:unlinked", t("待關聯庫存單據"), erp.inventory_unlinked, "erp", "medium");
      add("erp:budget", t("預算超額"), erp.budget_overrun_currencies || (n(erp.budget_usage) > 100 ? 1 : 0), "erp", "high");
    }
    const procurement = modules.procurement || {};
    if (ready("procurement", "procurement")) add("procurement:overdue", t("採購逾期"), procurement.overdue, "procurement", "high");
    const legal = modules.legal || {};
    if (ready("legal", "legal")) {
      add("legal:risk", t("合同風險"), n(legal.high_risk) + n(legal.license_expired), "legal", "high");
      add("legal:milestone", t("待履約里程碑"), legal.milestone_open, "legal", "medium");
    }
    const cases = modules.cases || {};
    if (ready("cases", "cases") && cases.cases) add("cases:risk", dashboardText(biu, "事務風險"), n(cases.cases.high) + n(cases.cases.overdue), "cases", "high");
    const stocktake = modules.stocktake || {};
    if (ready("stocktake", "stocktake")) add("stocktake:diff", t("盤點差異"), stocktake.differences, "stocktake", "medium");
    const audit = modules.audit || {};
    if (ready("audit", "logs")) add("audit:failed", dashboardText(biu, "審計失敗"), audit.failed, "logs", "high");
    const settingsStatus = modules.settings || {};
    if (ready("settings", "settings")) add("settings:ai", t("AI 連接異常"), settingsStatus.ai_configured && !settingsStatus.ai_connected ? 1 : 0, "settings", "medium");
    const order = { high: 0, medium: 1, low: 2 };
    return out.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9) || b.count - a.count || a.label.localeCompare(b.label));
  }, [snapshot, hub, visible, visibleWarehouseRoutes, biu]);

  if (error) return <>
    <Folio no="01" en={biu ? "CASE OVERVIEW" : "EXECUTIVE OVERVIEW"} title={dashboardText(biu, "公司總覽")} sub={dashboardText(biu, "跨財務、營運、資產與治理的管理駕駛艙")}/>
    <EM icon="alert" title={dashboardText(biu, "公司總覽載入失敗")} sub={t("請重試；其他功能不受影響。")}
      action={<B icon="refresh" onClick={() => setReloadNo(value => value + 1)}>{t("刷新總覽")}</B>}/>
  </>;

  const finance = modules.finance || {};
  const erp = modules.erp || {};
  const budgetRows = Array.isArray(erp.budgets_by_currency) ? erp.budgets_by_currency : [];
  const budgetUsage = erp.budget_max_usage == null ? erp.budget_usage : erp.budget_max_usage;
  const multiBudget = budgetRows.length > 1;
  const procurement = modules.procurement || {};
  const assets = modules.assets || {};
  const legal = modules.legal || {};
  const cases = modules.cases || {};
  const alerts = modules.alerts || {};
  const stocktake = modules.stocktake || {};
  const gis = modules.gis || {};
  const permissions = modules.permissions || {};
  const audit = modules.audit || {};
  const reports = modules.reports || {};
  const settings = modules.settings || {};
  const hubInventory = hub && hub.inventory || {};
  const hubOrders = hub && hub.orders || {};
  const hubShipments = hub && hub.shipments || {};
  const financialAsset = assets.financial || null;
  const digitalAsset = assets.digital || null;
  const [profitValue, profitUnit] = money(finance.profit);
  const [cashValue, cashUnit] = money(finance.cash);
  const [marketValue, marketUnit] = money(financialAsset && financialAsset.market_value);
  const availableModuleCount = snapshot ? (biu
    ? (navItems || []).filter(item => item.id !== "dashboard" && BIU_DASHBOARD_ROUTES.has(item.id)).length
    : (navItems || []).filter(item => {
    if (item.id === "dashboard") return false;
    const spec = EXECUTIVE_VISUAL_SPECS[item.id];
    if (!spec || !spec.access.some(key => access[key] === true)) return false;
    return item.id === "warehouse" ? !!hub : !!(modules[spec.key] && modules[spec.key].status === "ready");
  }).length) : 0;
  const signalCount = priorities.reduce((sum, item) => sum + item.count, 0);
  const hour = new Date().getHours();
  const greet = t(hour < 6 ? "夜深了" : hour < 12 ? "早安" : hour < 18 ? "午後好" : "晚上好");
  const user = window.W2_USER || {};
  const name = user.display_name || user.username || "";
  const headline = <>{greet}{name ? `，${name}` : ""}。{snapshot
    ? (signalCount ? <>{dashboardText(biu, "管理訊號")} <span className="num exec-head-signal">{fmt(signalCount)}</span></> : dashboardText(biu, "目前沒有需要管理層關注的訊號"))
    : t("COMPUTING")}</>;

  const kpis = [];
  if (ready("finance", "finance")) {
    kpis.push(<Kpi key="profit" label={t("本年淨利")} value={profitValue} unit={profitUnit} red={n(finance.profit) < 0}/>);
    kpis.push(<Kpi key="cash" label={t("公司現金")} value={cashValue} unit={cashUnit} red={n(finance.cash) < 0}/>);
  }
  if (ready("erp", "erp")) kpis.push(<Kpi key="budget" label={t(multiBudget ? "最高預算使用率" : "預算使用率")} value={budgetUsage == null ? "—" : fmt(budgetUsage, 1)} unit={budgetUsage == null ? "" : "%"} red={n(budgetUsage) > 100}/>);
  if (ready("assets", "assets") && financialAsset) kpis.push(<Kpi key="assets" label={t("金融資產市值")} value={marketValue} unit={marketUnit}/>);
  kpis.push(<Kpi key="signals" label={dashboardText(biu, "管理訊號")} value={snapshot ? fmt(signalCount) : "—"} red={signalCount > 0}/>);
  kpis.push(<Kpi key="modules" label={dashboardText(biu, "授權模組")} value={snapshot ? fmt(availableModuleCount) : "—"}/>);

  const visibleModuleKeys = new Set((navItems || []).flatMap(item => {
    if (biu && !BIU_DASHBOARD_ROUTES.has(item.id)) return [];
    const spec = EXECUTIVE_VISUAL_SPECS[item.id];
    return spec ? [spec.key] : [];
  }));
  const unavailable = snapshot ? Object.entries(modules).flatMap(([key, value]) => {
    if (biu && !visibleModuleKeys.has(key)) return [];
    if (!value) return [];
    if (value.status === "unavailable") return [key];
    if (value.partial && Array.isArray(value.unavailable)) {
      return value.unavailable.map(child => `${key}.${child}`);
    }
    return [];
  }).concat(!biu && hubRefreshFailed ? ["warehouse"] : []) : [];
  const moduleVisualModel = (id) => {
    const spec = EXECUTIVE_VISUAL_SPECS[id];
    const base = { available: false, pending: !snapshot, kind: spec && spec.kind, kicker: "資料軌跡", value: "—", unit: "", series: [], details: [] };
    if (!spec || !snapshot) return base;
    const permitted = spec.access.some(key => access[key] === true);
    const source = id === "warehouse" ? hub : modules[spec.key];
    if (!permitted || !source || (id !== "warehouse" && source.status !== "ready")) return { ...base, pending: false };
    const detail = (label, value, bad = false) => ({ label, value: value == null ? "—" : value, bad });
    const numberSeries = (rows) => (rows || []).map(row => ({ ...row, value: finite(row.value) }));

    if (id === "warehouse") {
      const categories = (hub.category_mix || []).slice(0, 6).map(row => ({ label: row.label || "—", value: row.skus }));
      return { ...base, available: true, pending: false, kicker: "庫存結構", value: metricText(finite(hubInventory.skus)), unit: " SKU",
        series: categories.length ? categories : [{ label: "在管 SKU", value: hubInventory.skus }, { label: "低庫存", value: hubInventory.low_skus, bad: finite(hubInventory.low_skus) > 0 }, { label: "零庫存", value: hubInventory.zero_skus, bad: finite(hubInventory.zero_skus) > 0 }],
        summary: `${t("待入庫")} ${metricText(finite(hubOrders.inbound_open))} · ${t("待出庫")} ${metricText(finite(hubOrders.outbound_open))} · ${t("在途")} ${metricText(finite(hubShipments.active))}`,
        details: [detail("在管 SKU", metricText(finite(hubInventory.skus))), detail("可用 SKU", metricText(finite(hubInventory.available_skus))), detail("低庫存", metricText(finite(hubInventory.low_skus)), finite(hubInventory.low_skus) > 0), detail("零庫存", metricText(finite(hubInventory.zero_skus)), finite(hubInventory.zero_skus) > 0)] };
    }
    if (id === "alerts") {
      const levels = numberSeries((alerts.levels || []).map(row => ({ label: row.label || "—", value: row.value, bad: row.label === "red" })));
      return { ...base, available: true, pending: false, kicker: "四級風險頻譜", value: metricText(finite(alerts.open)), unit: ` ${t("個")}`, bad: finite(alerts.red) > 0, series: levels,
        summary: `${t("升級預警")} ${metricText(finite(alerts.escalated))} · RED ${metricText(finite(alerts.red))}`,
        details: [detail("預警", metricText(finite(alerts.open))), detail("紅色預警", metricText(finite(alerts.red)), finite(alerts.red) > 0), detail("升級預警", metricText(finite(alerts.escalated)), finite(alerts.escalated) > 0), detail("關鍵唯讀", metricText(finite(alerts.critical_readonly)))] };
    }
    if (id === "stocktake") {
      const differences = finite(stocktake.differences);
      const taskTotal = finite(stocktake.tasks);
      const taskOpen = finite(stocktake.open);
      const taskClosed = taskTotal != null && taskOpen != null ? Math.max(0, taskTotal - taskOpen) : null;
      return { ...base, available: true, pending: false, kicker: "盤點閉環", value: metricText(differences), unit: ` ${t("項")}`, bad: differences > 0,
        series: [{ label: "開放任務", value: taskOpen }, { label: "已閉環任務", value: taskClosed }],
        summary: `${t("任務")} ${metricText(taskTotal)} · ${t("開放")} ${metricText(taskOpen)} · ${t("盤點差異")} ${metricText(differences)}`,
        details: [detail("盤點任務", metricText(taskTotal)), detail("開放任務", metricText(taskOpen)), detail("捕捉記錄", metricText(finite(stocktake.captures))), detail("盤點差異", metricText(differences), differences > 0)] };
    }
    if (id === "erp") {
      const usage = finite(budgetUsage);
      const currencies = numberSeries(budgetRows.map(row => ({ label: row.currency || "—", value: row.usage, bad: finite(row.usage) > 100 })));
      return { ...base, available: true, pending: false, kicker: "預算與執行", value: metricText(usage, 1), unit: usage == null ? "" : "%", bad: usage > 100, scaleMax: 100,
        series: currencies.length ? currencies : [{ label: "工單", value: erp.work_tasks_open }, { label: "採購", value: erp.purchase_open }, { label: "未關聯", value: erp.inventory_unlinked, bad: finite(erp.inventory_unlinked) > 0 }],
        summary: `${t("開放工單")} ${metricText(finite(erp.work_tasks_open))} · ${t("開放採購")} ${metricText(finite(erp.purchase_open))}`,
        details: [detail("最高預算使用率", usage == null ? "—" : `${fmt(usage, 1)}%`, usage > 100), detail("開放工單", metricText(finite(erp.work_tasks_open))), detail("開放採購", metricText(finite(erp.purchase_open))), detail("待關聯庫存單據", metricText(finite(erp.inventory_unlinked)), finite(erp.inventory_unlinked) > 0)] };
    }
    if (id === "finance") {
      const profit = finite(finance.profit);
      const profitMoney = money(profit);
      return { ...base, available: true, pending: false, kicker: "財務脈搏", value: profitMoney[0], unit: profitMoney[1], bad: profit < 0,
        series: (finance.trend || []).map(row => ({ label: String(row.month || "—").slice(5), value: row.profit, bad: finite(row.profit) < 0 })),
        summary: `${t("營業收入")} ${money(finite(finance.revenue)).join(" ")} · ${t("成本費用")} ${money(finite(finance.cost)).join(" ")}`,
        details: [detail("營業收入", money(finite(finance.revenue)).join(" ")), detail("成本費用", money(finite(finance.cost)).join(" ")), detail("當月現金淨變動", money(finite(finance.cash_net_month)).join(" "), finite(finance.cash_net_month) < 0), detail("待處理財務事件", metricText(finite(finance.pending_events)), finite(finance.pending_events) > 0)] };
    }
    if (id === "assets") {
      const allocation = financialAsset && (financialAsset.allocation || []).map(row => ({ label: row.label || row.name || row.type || "—", value: row.value != null ? row.value : (row.value_cny != null ? row.value_cny : row.market_value) })) || [];
      const kinds = digitalAsset && (digitalAsset.kinds || []).map(row => ({ label: row.label || row.name || row.kind || "—", value: row.value != null ? row.value : row.count })) || [];
      const primary = financialAsset ? finite(financialAsset.market_value) : finite(digitalAsset && digitalAsset.valuation);
      const primaryMoney = money(primary);
      return { ...base, available: true, pending: false, kicker: "資本配置", value: primaryMoney[0], unit: primaryMoney[1], series: allocation.length ? allocation : kinds,
        summary: `${t("浮動盈虧")} ${financialAsset ? money(finite(financialAsset.unrealized_pnl)).join(" ") : "—"} · ${t("已上架")} ${metricText(finite(digitalAsset && digitalAsset.listed))}`,
        details: [detail("金融資產市值", financialAsset ? money(finite(financialAsset.market_value)).join(" ") : "—"), detail("浮動盈虧", financialAsset ? money(finite(financialAsset.unrealized_pnl)).join(" ") : "—", finite(financialAsset && financialAsset.unrealized_pnl) < 0), detail("數字資產估值", digitalAsset ? money(finite(digitalAsset.valuation)).join(" ") : "—"), detail("已上架", metricText(finite(digitalAsset && digitalAsset.listed)))] };
    }
    if (id === "procurement") {
      const statuses = numberSeries((procurement.statuses || []).map(row => ({ label: row.label || "—", value: row.value })));
      const overdue = finite(procurement.overdue);
      return { ...base, available: true, pending: false, kicker: "流程狀態", value: metricText(finite(procurement.inbox)), unit: ` ${t("項")}`, bad: overdue > 0,
        series: statuses.length ? statuses : [{ label: "待辦", value: procurement.inbox }, { label: "進行中", value: procurement.running }, { label: "已閉環", value: procurement.closed }],
        summary: `${t("逾期")} ${metricText(overdue)} · ${t(procurement.scope === "all" ? "全公司視角" : "個人可見視角")}`,
        details: [detail("待辦", metricText(finite(procurement.inbox))), detail("逾期", metricText(overdue), overdue > 0), detail("進行中", metricText(finite(procurement.running))), detail("已閉環", metricText(finite(procurement.closed)))] };
    }
    if (id === "legal") {
      const highRisk = finite(legal.high_risk);
      const statuses = numberSeries((legal.statuses || []).map(row => ({ label: row.label || "—", value: row.value })));
      return { ...base, available: true, pending: false, kicker: "履約風險", value: metricText(highRisk), unit: ` ${t("項")}`, bad: highRisk > 0,
        series: statuses.length ? statuses : [{ label: "生效合同", value: legal.active_contracts }, { label: "高風險", value: legal.high_risk, bad: highRisk > 0 }, { label: "里程碑", value: legal.milestone_open }],
        summary: `${t("生效合同")} ${metricText(finite(legal.active_contracts))} · ${t("待履約里程碑")} ${metricText(finite(legal.milestone_open))}`,
        details: [detail("生效合同", metricText(finite(legal.active_contracts))), detail("高風險合同", metricText(highRisk), highRisk > 0), detail("到期證照", metricText(finite(legal.license_expired)), finite(legal.license_expired) > 0), detail("待履約里程碑", metricText(finite(legal.milestone_open)), finite(legal.milestone_open) > 0)] };
    }
    if (id === "gis") {
      const warehouses = finite(gis.warehouses);
      const located = finite(gis.located);
      const rate = warehouses != null && warehouses > 0 && located != null ? located / warehouses * 100 : null;
      return { ...base, available: true, pending: false, kicker: "定位完整率", value: metricText(rate, 1), unit: rate == null ? "" : "%", bad: finite(gis.unlocated) > 0 || finite(gis.unlocated_locations) > 0,
        series: [{ label: "倉庫", value: warehouses }, { label: "已定位倉庫", value: located }, { label: "庫位", value: gis.locations }, { label: "未定位庫位", value: gis.unlocated_locations, bad: finite(gis.unlocated_locations) > 0 }],
        summary: `${t("倉庫")} ${metricText(warehouses)} · ${t("未定位庫位")} ${metricText(finite(gis.unlocated_locations))}`,
        details: [detail("倉庫", metricText(warehouses)), detail("已定位倉庫", metricText(located)), detail("庫位", metricText(finite(gis.locations))), detail("未定位庫位", metricText(finite(gis.unlocated_locations)), finite(gis.unlocated_locations) > 0)] };
    }
    if (id === "reports") {
      const trend = reports.trend || {};
      const labels = Array.isArray(trend.labels) ? trend.labels : [];
      const inbound = Array.isArray(trend.inbound) ? trend.inbound : [];
      const outbound = Array.isArray(trend.outbound) ? trend.outbound : [];
      const urgent = Array.isArray(trend.urgent) ? trend.urgent : [];
      const rhythm = labels.map((label, index) => {
        const inValue = finite(inbound[index]); const outValue = finite(outbound[index]);
        return { label, value: inValue == null || outValue == null ? null : inValue + outValue, bad: finite(urgent[index]) > 0 };
      });
      const handled = finite(reports.handled_rate);
      return { ...base, available: true, pending: false, kicker: "營運報告節奏", value: metricText(handled, 1), unit: handled == null ? "" : "%", bad: handled != null && handled < 80, series: rhythm,
        summary: `${t("本期入庫")} ${metricText(finite(reports.inbound_total))} · ${t("本期出庫")} ${metricText(finite(reports.outbound_total))}`,
        details: [detail("預警處理率", handled == null ? "—" : `${fmt(handled, 1)}%`, handled != null && handled < 80), detail("緊急搶修單", metricText(finite(reports.urgent_total)), finite(reports.urgent_total) > 0), detail("待歸還", metricText(finite(reports.pending_returns)), finite(reports.pending_returns) > 0), detail("可匯出報表", metricText(finite(reports.exports)))] };
    }
    if (id === "perms") {
      const fullView = typeof permissions.full_view === "boolean" ? permissions.full_view : null;
      const scopeText = fullView == null ? "—" : t(fullView ? "完整公司視角" : "受限組織視角");
      return { ...base, available: true, pending: false, kicker: "組織授權拓撲", value: metricText(finite(permissions.users)), unit: ` ${t("人")}`,
        series: [{ label: "用戶", value: permissions.users }, { label: "已指派用戶", value: permissions.assigned_users }, { label: "角色", value: permissions.roles }],
        summary: `${t("已指派用戶")} ${metricText(finite(permissions.assigned_users))} / ${metricText(finite(permissions.users))} · ${t("角色")} ${metricText(finite(permissions.roles))} · ${scopeText}`,
        details: [detail("用戶", metricText(finite(permissions.users))), detail("已指派用戶", metricText(finite(permissions.assigned_users))), detail("角色指派", metricText(finite(permissions.role_assignments))), detail("權限分享", metricText(finite(permissions.delegations))), detail("權限可見範圍", scopeText)] };
    }
    if (id === "logs") {
      const failed = finite(audit.failed);
      return { ...base, available: true, pending: false, kicker: "審計事件帶", value: metricText(finite(audit.events)), unit: ` ${t("條")}`, bad: failed > 0,
        series: [{ label: "事件", value: audit.events }, { label: "寫入", value: audit.writes }, { label: "失敗", value: audit.failed, bad: failed > 0 }],
        summary: `${t("寫入")} ${metricText(finite(audit.writes))} · ${t("失敗審計事件")} ${metricText(failed)}`,
        details: [detail("事件", metricText(finite(audit.events))), detail("寫入", metricText(finite(audit.writes))), detail("失敗審計事件", metricText(failed), failed > 0), detail("資料更新於", audit.latest ? String(audit.latest).replace("T", " ") : "—")] };
    }
    if (id === "cases") {
      const caseData = cases.cases || {};
      const recordData = cases.records || {};
      const primary = cases.cases ? finite(caseData.open) : finite(recordData.total);
      const caseTotal = finite(caseData.total);
      const caseOpen = finite(caseData.open);
      const caseClosed = caseTotal != null && caseOpen != null ? Math.max(0, caseTotal - caseOpen) : null;
      const high = finite(caseData.high);
      const overdue = finite(caseData.overdue);
      return biu
        ? { ...base, available: true, pending: false, kicker: "程序與卷宗週期", value: metricText(primary), unit: ` ${t("項")}`, bad: high > 0 || overdue > 0,
          series: [{ label: "進行中案件", value: caseOpen }, { label: "已結案案件", value: caseClosed }, { label: "有效卷宗", value: recordData.total }, { label: "歸檔", value: recordData.archived }],
          summary: `${t("進行中案件")} ${metricText(caseOpen)} · ${t("卷宗總數")} ${metricText(finite(recordData.total))}`,
          details: [detail("進行中案件", metricText(caseOpen)), detail("案件待核查", metricText(high), high > 0), detail("卷宗總數", metricText(finite(recordData.total))), detail("即將到期", metricText(finite(recordData.expiring)), finite(recordData.expiring) > 0)] }
        : { ...base, available: true, pending: false, kicker: "事務與檔案週期", value: metricText(primary), unit: ` ${t("項")}`, bad: high > 0 || overdue > 0,
          series: [{ label: "開放事務", value: caseOpen }, { label: "已閉環事務", value: caseClosed }, { label: "有效檔案", value: recordData.total }, { label: "歸檔", value: recordData.archived }],
          summary: `${t("開放事務")} ${metricText(finite(caseData.open))} · ${t("檔案總數")} ${metricText(finite(recordData.total))}`,
          details: [detail("開放事務", metricText(finite(caseData.open))), detail("高風險事務", metricText(high), high > 0), detail("檔案總數", metricText(finite(recordData.total))), detail("即將到期", metricText(finite(recordData.expiring)), finite(recordData.expiring) > 0)] };
    }
    const rulesEnabled = finite(settings.rules_enabled);
    const rulesTotal = finite(settings.rules_total);
    const aiConfigured = typeof settings.ai_configured === "boolean" ? settings.ai_configured : null;
    const aiConnected = typeof settings.ai_connected === "boolean" ? settings.ai_connected : null;
    const integrationKnown = aiConfigured != null && aiConnected != null;
    const readinessValue = rulesEnabled == null ? null : rulesEnabled + (aiConnected === true ? 1 : 0);
    const readinessTotal = rulesTotal == null ? null : rulesTotal + (integrationKnown ? 1 : 0);
    const aiConnectionBad = aiConfigured === true && aiConnected === false;
    return biu
      ? { ...base, available: true, pending: false, kicker: "學術工作區就緒", value: `${metricText(rulesEnabled)}/${metricText(rulesTotal)}`, bad: aiConnectionBad,
        matrix: { value: readinessValue, total: readinessTotal },
        summary: `${t("法律倫理規則")} ${metricText(rulesEnabled)}/${metricText(rulesTotal)} · ${t("機構職位")} ${metricText(finite(settings.roles))}`,
        details: [detail("法律倫理規則", `${metricText(rulesEnabled)}/${metricText(rulesTotal)}`), detail("機構職位", metricText(finite(settings.roles))), detail("AI 已配置", aiConfigured == null ? "—" : t(aiConfigured ? "是" : "否")), detail("秘書連接", aiConnected == null ? "—" : t(aiConnected ? "是" : "否"), aiConnectionBad)] }
      : { ...base, available: true, pending: false, kicker: "配置就緒", value: `${metricText(rulesEnabled)}/${metricText(rulesTotal)}`, bad: aiConnectionBad,
        matrix: { value: readinessValue, total: readinessTotal },
        summary: `${t("倉庫")} ${metricText(finite(settings.warehouses))} · ${t("分類")} ${metricText(finite(settings.categories))} · ${t("角色")} ${metricText(finite(settings.roles))}`,
        details: [detail("規則啟用", `${metricText(rulesEnabled)}/${metricText(rulesTotal)}`), detail("AI 已配置", aiConfigured == null ? "—" : t(aiConfigured ? "是" : "否")), detail("AI 已連接", aiConnected == null ? "—" : t(aiConnected ? "是" : "否"), aiConnectionBad), detail("配置就緒", `${metricText(finite(settings.warehouses))} / ${metricText(finite(settings.categories))} / ${metricText(finite(settings.roles))}`)] };
  };
  const moduleVisualItems = (navItems || []).filter(item => {
    if (biu && !BIU_DASHBOARD_ROUTES.has(item.id)) return false;
    if (item.id === "dashboard" || !EXECUTIVE_VISUAL_ROUTES.includes(item.id)) return false;
    if (!snapshot) return true;
    const spec = EXECUTIVE_VISUAL_SPECS[item.id];
    return !!(spec && spec.access.some(key => access[key] === true));
  });

  return <>
    <Folio no="01" en={biu ? "CASE OVERVIEW" : "EXECUTIVE OVERVIEW"} title={headline}
      sub={dashboardText(biu, "跨財務、營運、資產與治理的管理駕駛艙")}
      right={<B icon="refresh" onClick={() => setReloadNo(value => value + 1)}>{dashboardText(biu, "刷新總覽")}</B>}/>

    <div className="exec-scope row spread wrap g10 rise">
      <span className="row g8"><I name="shield" size={13} color="var(--red)"/><b>{dashboardText(biu, "公司總覽")}</b> · {dashboardText(biu, "伺服器按目前帳號逐域裁切")}</span>
      <span className="mono muted">{snapshot ? `${t("資料更新於")} ${String(snapshot.generated_at || "").replace("T", " ")}` : t("COMPUTING")}</span>
    </div>

    <div className="kpi-band exec-kpis">{kpis}</div>
    {!!unavailable.length && <div className="exec-unavailable row g8"><I name="alert" size={13}/>{t("資料暫時不可用")} · {unavailable.map(key => key.toUpperCase()).join(" / ")}</div>}

    <div className="exec-grid">
      {authorised("finance", "finance") && <ExecCard id="finance" no="A" title={t("財務脈搏")} sub={t("收入、成本、利潤與現金")}
        route="finance" wide expanded={expanded.finance} onToggle={() => toggle("finance")}
        detail={ready("finance", "finance") ? <div className="exec-detail-grid">
          <div><span>{t("應收")}</span><strong>{currencyText(finance.receivable_by_currency)}</strong></div>
          <div><span>{t("應付")}</span><strong>{currencyText(finance.payable_by_currency)}</strong></div>
          <div><span>{t("待處理財務事件")}</span><strong className="num">{fmt(finance.pending_events)}</strong></div>
          <div><span>{finance.balanced ? t("資產負債表平衡") : t("資產負債表待覆核")}</span><T tone={finance.balanced ? "ok" : "bad"} dot>{finance.balanced ? "OK" : "CHECK"}</T></div>
        </div> : null}>
        {ready("finance", "finance") ? <>
          <div className="exec-stat-row">
            <Stat label={t("營業收入")} value={money(finance.revenue)[0]} unit={money(finance.revenue)[1]}/>
            <Stat label={t("成本費用")} value={money(finance.cost)[0]} unit={money(finance.cost)[1]}/>
            <Stat label={t("本年淨利")} value={profitValue} unit={profitUnit} bad={n(finance.profit) < 0}/>
            <Stat label={t("當月現金淨變動")} value={money(finance.cash_net_month)[0]} unit={money(finance.cash_net_month)[1]} bad={n(finance.cash_net_month) < 0}/>
          </div>
          {(finance.trend || []).length > 1 && <div className="exec-chart-link" role="link" tabIndex="0" onClick={() => go("finance")} onKeyDown={event => event.key === "Enter" && go("finance")}>
            <MirrorBars labels={finance.trend.map(row => String(row.month || "").slice(5))}
              up={finance.trend.map(row => n(row.revenue))} down={finance.trend.map(row => n(row.cost) + n(row.expense))}
              upName={t("營業收入")} downName={t("成本費用")}/>
          </div>}
        </> : <Unavailable/>}
      </ExecCard>}

      {authorised("erp", "erp") && <ExecCard id="erp" no="B" title={t("預算與執行")} sub={t("撥款、佔用、支出與可用額")}
        route="erp" expanded={expanded.erp} onToggle={() => toggle("erp")}
        detail={ready("erp", "erp") ? <div className="exec-detail-grid">
          <div><span>{t("開放工單")}</span><strong className="num">{fmt(erp.work_tasks_open)}</strong></div>
          <div><span>{t("開放採購")}</span><strong className="num">{fmt(erp.purchase_open)}</strong></div>
          <div><span>{t("待關聯庫存單據")}</span><strong className="num">{fmt(erp.inventory_unlinked)}</strong></div>
          <div><span>{t("可用")}</span><strong className="num">{budgetRows.length === 1 ? currencyAmount(budgetRows[0].currency, budgetRows[0].available) : (budgetRows.length ? `${budgetRows.length} ${t("幣別")}` : "—")}</strong></div>
        </div> : null}>
        {ready("erp", "erp") ? <>
          <div className="exec-budget-hero"><strong className="num">{budgetUsage == null ? "—" : fmt(budgetUsage, 1) + "%"}</strong><span>{t(multiBudget ? "最高預算使用率" : "預算使用率")}</span></div>
          {budgetRows.length ? <div className="exec-budget-currencies">
            {budgetRows.map(row => <div className="exec-budget-currency" key={row.currency}>
              <div className="exec-budget-currency-head"><b className="mono">{row.currency}</b><span className="num">{row.usage == null ? "—" : fmt(row.usage, 1) + "%"}</span></div>
              <Meter label={t("已支出")} count={n(row.spent) + n(row.reserved)} total={n(row.amount) || 1} color={n(row.usage) > 100 ? "var(--red)" : "var(--ink)"}/>
              <div className="exec-mini-ledger">
                <span>{t("預算總額")}<b className="num">{currencyAmount(row.currency, row.amount)}</b></span>
                <span>{t("已支出")}<b className="num">{currencyAmount(row.currency, row.spent)}</b></span>
                <span>{t("已佔用")}<b className="num">{currencyAmount(row.currency, row.reserved)}</b></span>
                <span>{t("可用")}<b className="num">{currencyAmount(row.currency, row.available)}</b></span>
              </div>
            </div>)}
          </div> : <span className="muted">{t("本期沒有預算數據")}</span>}
        </> : <Unavailable/>}
      </ExecCard>}

      {canShow("warehouse") && hub && <ExecCard id="warehouse" no="C" title={t("庫管健康")} sub={t("庫存、收發、在途與異常")}
        route="warehouse" expanded={expanded.warehouse} onToggle={() => toggle("warehouse")}
        detail={<div className="exec-detail-grid">
          <div><span>{t("待入庫")}</span><strong className="num">{fmt(hubOrders.inbound_open)}</strong></div>
          <div><span>{t("待出庫")}</span><strong className="num">{fmt(hubOrders.outbound_open)}</strong></div>
          <div><span>{t("在途")}</span><strong className="num">{fmt(hubShipments.active)}</strong></div>
          <div><span>{t("延誤")}</span><strong className="num">{fmt(hubShipments.delayed)}</strong></div>
        </div>}>
        <div className="exec-warehouse-score">
          <div><strong className="num">{fmt(hubInventory.skus)}</strong><span>{t("在管 SKU")}</span></div>
          <div className={n(hubInventory.low_skus) ? "bad" : ""}><strong className="num">{fmt(hubInventory.low_skus)}</strong><span>{t("低庫存")}</span></div>
          <div className={n(hubInventory.zero_skus) ? "bad" : ""}><strong className="num">{fmt(hubInventory.zero_skus)}</strong><span>{t("零庫存")}</span></div>
        </div>
        {(hub.category_mix || []).length > 0 && <div className="exec-category-bars">
          {(hub.category_mix || []).slice(0, 5).map((row, index, all) => {
            const max = Math.max(1, ...all.map(item => n(item.skus)));
            return <div key={(row.label || "—") + index}><span>{row.label || "—"}</span><i><b style={{ width: Math.min(100, n(row.skus) / max * 100) + "%" }}/></i><strong className="num">{fmt(row.skus)}</strong></div>;
          })}
        </div>}
      </ExecCard>}

      {authorised("procurement", "procurement") && <ExecCard id="procurement" no="D" title={t("採購漏斗")} sub={t("待辦、逾期與流程閉環")}
        route="procurement" expanded={expanded.procurement} onToggle={() => toggle("procurement")}
        detail={ready("procurement", "procurement") ? <div className="exec-due-list">
          {(procurement.due || []).length ? procurement.due.map((row, index) => <div key={index}><span>{row.title}</span><b className="mono">{row.due_at || "—"}</b></div>) : <span className="muted">—</span>}
        </div> : null}>
        {ready("procurement", "procurement") ? <>
          <div className="exec-stat-row two">
            <Stat label={t("待辦")} value={fmt(procurement.inbox)} bad={n(procurement.inbox) > 0}/>
            <Stat label={t("逾期")} value={fmt(procurement.overdue)} bad={n(procurement.overdue) > 0}/>
            <Stat label={t("進行中")} value={fmt(procurement.running)}/>
            <Stat label={t("已閉環")} value={fmt(procurement.closed)}/>
          </div>
          <div className="exec-scope-note">{t(procurement.scope === "all" ? "全公司視角" : "個人可見視角")}</div>
        </> : <Unavailable/>}
      </ExecCard>}

      <ExecCard id="risk" no="E" title={dashboardText(biu, "風險與決策")} sub={dashboardText(biu, "跨模組按嚴重度排序")}
        wide expanded={expanded.risk} onToggle={() => toggle("risk")}
        detail={priorities.length > 6 ? <div className="exec-priority-list compact">{priorities.slice(6).map((item, index) => <a key={item.key} href={`#/${item.route}`}><span className="num">{String(index + 7).padStart(2, "0")}</span><i className={item.severity}/><b>{t(item.label)}</b><strong className="num">{fmt(item.count)}</strong><em>→</em></a>)}</div> : null}>
        {!snapshot ? <div className="exec-loading-note"><span className="label">{t("COMPUTING")}</span></div>
          : priorities.length ? <div className="exec-priority-list">{priorities.slice(0, 6).map((item, index) => <a key={item.key} href={`#/${item.route}`}><span className="num">{String(index + 1).padStart(2, "0")}</span><i className={item.severity}/><b>{t(item.label)}</b><strong className="num">{fmt(item.count)}</strong><em>→</em></a>)}</div>
          : <EM icon="checkCircle" title={dashboardText(biu, "目前沒有需要管理層關注的訊號")}/>}
      </ExecCard>

      {(authorised("assets_financial", "assets") || authorised("assets_digital", "assets")) && <ExecCard id="assets" no="F" title={t("資產版圖")} sub={t("金融資產與數字資產")}
        route="assets" expanded={expanded.assets} onToggle={() => toggle("assets")}
        detail={ready("assets", "assets") ? <div className="exec-detail-grid">
          {financialAsset && <><div><span>{t("浮動盈虧")}</span><strong className="num">{money(financialAsset.unrealized_pnl).join(" ")}</strong></div><div><span>{t("持倉")}</span><strong className="num">{fmt(financialAsset.holdings)}</strong></div></>}
          {digitalAsset && <><div><span>{t("數字資產估值")}</span><strong className="num">{money(digitalAsset.valuation).join(" ")}</strong></div><div><span>{t("已上架")}</span><strong className="num">{fmt(digitalAsset.listed)}</strong></div></>}
        </div> : null}>
        {ready("assets", "assets") ? <div className="exec-assets-split">
          {financialAsset && <div><span>{t("金融資產市值")}</span><strong className="num">{marketValue}<small>{marketUnit}</small></strong><em className={n(financialAsset.unrealized_pnl) < 0 ? "bad" : ""}>{t("浮動盈虧")} · {money(financialAsset.unrealized_pnl).join(" ")}</em></div>}
          {digitalAsset && <div><span>{t("數字資產估值")}</span><strong className="num">{money(digitalAsset.valuation)[0]}<small>{money(digitalAsset.valuation)[1]}</small></strong><em>{fmt(digitalAsset.assets)} {t("個")}</em></div>}
        </div> : <Unavailable/>}
      </ExecCard>}

      {(authorised("legal", "legal") || authorised("cases", "cases") || authorised("records", "cases")) && <ExecCard id="governance" no="G" title={dashboardText(biu, "治理與履約")} sub={dashboardText(biu, "合同、事務、檔案與組織控制")}
        expanded={expanded.governance} onToggle={() => toggle("governance")}
        detail={<div className="exec-governance-links">
          {canShow("legal") && <a href="#/legal">{t("法務")} →</a>}
          {canShow("cases") && <a href="#/cases">{t("檔案")} →</a>}
        </div>}>
        <div className="exec-governance-grid">
          {ready("legal", "legal") && <>
            <Stat label={t("生效合同")} value={fmt(legal.active_contracts)}/>
            <Stat label={t("高風險合同")} value={fmt(legal.high_risk)} bad={n(legal.high_risk) > 0}/>
            <Stat label={t("到期證照")} value={fmt(legal.license_expired)} bad={n(legal.license_expired) > 0}/>
            <Stat label={t("待履約里程碑")} value={fmt(legal.milestone_open)} bad={n(legal.milestone_open) > 0}/>
          </>}
          {ready("cases", "cases") && cases.cases && <>
            <Stat label={dashboardText(biu, "開放事務")} value={fmt(cases.cases.open)} bad={n(cases.cases.open) > 0}/>
            <Stat label={dashboardText(biu, "高風險事務")} value={fmt(cases.cases.high)} bad={n(cases.cases.high) > 0}/>
          </>}
          {ready("cases", "cases") && cases.records && <Stat label={dashboardText(biu, "檔案總數")} value={fmt(cases.records.total)}/>}
        </div>
      </ExecCard>}
    </div>

    <section className="exec-module-map rise" aria-labelledby="exec-module-map-title">
      <header><span>H</span><div><h2 id="exec-module-map-title">{dashboardText(biu, "模組視覺圖譜")}</h2><p>{dashboardText(biu, "每個獲授權功能都有一個可展開、可直達的管理視角")}</p></div></header>
      <div className="exec-module-viz-grid">
        {moduleVisualItems.map((item, index) => {
          const key = `visual:${item.id}`;
          return <ModuleVisualCard key={item.id} item={item} index={index} model={moduleVisualModel(item.id)}
            expanded={!!expanded[key]} onToggle={() => toggle(key)}/>;
        })}
      </div>
    </section>

    {(ready("stocktake", "stocktake") || ready("gis", "gis") || ready("permissions", "perms") || ready("audit", "logs")) && <div className="exec-control-strip rise">
      {ready("stocktake", "stocktake") && <a href="#/stocktake"><span>{t("盤點差異")}</span><b className="num">{fmt(stocktake.differences)}</b></a>}
      {ready("gis", "gis") && <a href="#/gis"><span>{t("未定位庫位")}</span><b className="num">{fmt(gis.unlocated_locations)}</b></a>}
      {ready("permissions", "perms") && <a href="#/perms"><span>{t("已指派用戶")}</span><b className="num">{metricText(finite(permissions.assigned_users))}</b></a>}
      {ready("audit", "logs") && <a href="#/logs"><span>{t("失敗審計事件")}</span><b className="num">{fmt(audit.failed)}</b></a>}
    </div>}
  </>;
};

W2.PAGES.dashboard = PageExecutiveDashboard;
})();
