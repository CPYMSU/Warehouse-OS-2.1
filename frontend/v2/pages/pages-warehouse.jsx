/* WAREHOUSE 2.1 · 庫管中心 — virtual hub over the four canonical modules */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { Icon: I, Btn: B, Tag: T, Empty: EM, Kpi, MirrorBars, TrendArea, Folio, Band, HBar } = W2;
const { useEffect, useRef } = React;

window.W2_LANG.addEN({
  "庫管": "Warehouse",
  "庫管中心": "Warehouse control",
  "庫存、收發與在途整合在同一工作區；資料與操作仍按原權限獨立裁切": "Inventory, receipts, issues and transit in one workspace; data and actions remain independently permission-scoped",
  "透視總覽": "Pivot overview",
  "授權工作區": "Authorized workspace",
  "伺服器已按目前帳號權限裁切": "Server-filtered for the current account",
  "在管 SKU": "Managed SKUs",
  "可用 SKU": "Available SKUs",
  "待完成入庫": "Open inbound",
  "待完成出庫": "Open outbound",
  "在途批次": "In transit",
  "90 日 SKU 中位周轉": "Median SKU turnover · 90d",
  "逐 SKU 出庫量 ÷ 現存量的中位數 · 營運估算": "Median of per-SKU outbound ÷ current on-hand · operational estimate",
  "庫存結構": "Stock structure",
  "按功能分類": "by functional category",
  "按倉庫": "by warehouse",
  "庫存量": "quantity",
  "估算儲值": "estimated value",
  "SKU 種數": "SKU count",
  "沒有可分析的庫存結構": "No stock structure to analyse",
  "有庫存資料後會自動形成分佈。": "Distribution appears automatically when stock data is available.",
  "收發趨勢": "Inbound / outbound trend",
  "近六個月 · 單據量": "last six months · documents",
  "尚無近期收發單據": "No recent inbound/outbound documents",
  "產生單據後會按月形成雙向節奏。": "A monthly two-way rhythm appears after documents are created.",
  "在途老化": "Transit ageing",
  "按發運後經過時間": "elapsed time after dispatch",
  "未知": "Unknown",
  "目前沒有在途批次": "No shipments are currently in transit",
  "異常聚焦": "Exception focus",
  "跨庫存、收發與在途": "across inventory, flows and transit",
  "目前沒有需要聚焦的異常": "No exceptions need attention",
  "已按目前可見工作區過濾": "Filtered to currently visible workspaces",
  "透視摘要準備中": "Pivot summary is preparing",
  "請刷新一次；摘要只會由後端從已授權資料生成。": "Refresh once; the server builds this summary only from authorized data.",
  "分析庫管中心的庫存結構、收發節奏、在途老化與異常，按優先級給我建議": "Analyse stock structure, inbound/outbound rhythm, transit ageing and exceptions, then recommend actions by priority",
  "查看": "Open",
  "低於安全線": "Below safety",
  "過期批次庫位": "Locations with expired batches",
  "在途延誤": "Transit delay",
  "緊急出庫": "Urgent outbound",
  "資料範圍": "Data scope",
  "安全線趨勢": "Safety coverage trend",
  "逐 SKU 安全覆蓋率中位數": "median safety coverage across SKUs",
  "90 日耗用強度": "90-day consumption intensity",
  "按 SKU 週轉比排序": "ranked by per-SKU turnover",
  "需要關注": "Attention required",
  "按安全覆蓋率排序": "ranked by safety coverage",
  "查看庫存": "Open inventory",
});

const fmt = (value, digits = 0) => {
  const number = Number(value);
  if (!Number.isFinite(number)) return "—";
  return number.toLocaleString(undefined, { maximumFractionDigits: digits });
};
const tabHref = (id) => "#/" + id;

const WarehouseTabs = ({ routes = [], route }) => {
  const tabs = [{ id: "warehouse", idx: "00", label: "透視總覽" }, ...routes];
  const activeRef = useRef(null);
  const routeKey = tabs.map(tab => tab.id).join("|");
  useEffect(() => {
    if (activeRef.current && activeRef.current.scrollIntoView) {
      activeRef.current.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
    if (activeRef.current && W2.__warehouseKeyboardFocus === route) {
      activeRef.current.focus();
      W2.__warehouseKeyboardFocus = null;
    }
  }, [route, routeKey]);
  const move = (event, index) => {
    let next = index;
    if (event.key === "ArrowRight") next = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") next = (index - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = tabs.length - 1;
    else return;
    event.preventDefault();
    W2.__warehouseKeyboardFocus = tabs[next].id;
    location.hash = tabHref(tabs[next].id);
  };
  return (
    <div className="warehouse-tabs rise" role="tablist" aria-label={t("庫管")}>
      <div className="warehouse-tabs-title">
        <span className="label red">WAREHOUSE</span>
        <strong>{t("庫管")}</strong>
      </div>
      <div className="warehouse-tabs-scroll">
        {tabs.map((tab, index) => (
          <button key={tab.id} type="button" role="tab" id={"warehouse-tab-" + tab.id}
            ref={route === tab.id ? activeRef : null} aria-selected={route === tab.id}
            aria-controls={"warehouse-panel-" + tab.id} tabIndex={route === tab.id ? 0 : -1}
            className={"warehouse-tab" + (route === tab.id ? " on" : "")}
            onKeyDown={event => move(event, index)}
            onClick={() => { location.hash = tabHref(tab.id); }}>
            <span className="num">{tab.idx || "—"}</span>{t(tab.label)}
          </button>
        ))}
      </div>
    </div>
  );
};

const PivotRows = ({ rows, metric }) => {
  const values = (rows || []).map(row => Number(row[metric]) || 0);
  const max = Math.max(1, ...values);
  return rows && rows.length ? (
    <div className="warehouse-pivot-list">
      {rows.slice(0, 8).map((row, index) => (
        <HBar key={(row.label || "—") + ":" + index} idx={index + 1} name={row.label || "—"}
          w={(Number(row[metric]) || 0) / max * 100} val={fmt(row[metric], metric === "value" ? 2 : 0)}
          sub={Number(row.value) > 0 ? `${t("估算儲值")} ${fmt(row.value, 2)}` : "SKU"}/>
      ))}
    </div>
  ) : <EM icon="chart" title={t("沒有可分析的庫存結構")} sub={t("有庫存資料後會自動形成分佈。")}/>;
};

const PageWarehouse = ({ boot, warehouseTabs = [] }) => {
  const hub = boot && boot.WAREHOUSE_HUB;
  const visible = new Set((warehouseTabs || []).map(tab => tab.id));
  if (!hub || hub.scope !== "permission-filtered") return (
    <>
      <Folio no="02" en="WAREHOUSE" title={t("庫管中心")}
        sub={t("庫存、收發與在途整合在同一工作區；資料與操作仍按原權限獨立裁切")}/>
      <EM icon="refresh" title={t("透視摘要準備中")} sub={t("請刷新一次；摘要只會由後端從已授權資料生成。")}/>
    </>
  );

  const access = hub.access || {};
  const inventory = hub.inventory || {};
  const orders = hub.orders || {};
  const shipments = hub.shipments || {};
  const showInventory = access.inventory && visible.has("inventory");
  const showInbound = access.inbound && visible.has("inbound");
  const showOutbound = access.outbound && visible.has("outbound");
  const showShipments = access.shipments && visible.has("shipments");
  const categoryRows = showInventory ? (hub.category_mix || []) : [];
  const warehouseRows = showInventory ? (hub.warehouse_mix || []) : [];
  const turnover = inventory.turnover_90d && typeof inventory.turnover_90d === "object" ? inventory.turnover_90d : null;
  const flow = hub.flow || [];
  const inboundDocs = flow.map(row => showInbound ? Number(row.inbound_docs) || 0 : 0);
  const outboundDocs = flow.map(row => showOutbound ? Number(row.outbound_docs) || 0 : 0);
  const hasFlow = inboundDocs.some(Boolean) || outboundDocs.some(Boolean);
  const aging = showShipments ? ((shipments.aging || []).filter(row => Number(row.value) > 0)) : [];
  const maxAge = Math.max(1, ...aging.map(row => Number(row.value) || 0));
  const coverage = showInventory ? (hub.coverage_trend || []) : [];
  const consumption = showOutbound ? (hub.consumption || []) : [];
  const maxConsumption = Math.max(1, ...consumption.map(row => Number(row.turnover) || 0));
  const attention = showInventory ? (hub.attention || []) : [];
  const anomalies = (hub.anomalies || []).filter(item => visible.has(item.route));

  return (
    <>
      <Folio no="02" en="WAREHOUSE" title={t("庫管中心")}
        sub={t("庫存、收發與在途整合在同一工作區；資料與操作仍按原權限獨立裁切")}
        right={showInventory && <B icon="inventory" onClick={() => { location.hash = "#/inventory"; }}>{t("查看庫存")}</B>}/>

      <div className="warehouse-scope row spread wrap g10 rise">
        <span className="row g8"><I name="shield" size={13} color="var(--red)"/><b>{t("資料範圍")}</b> · {t("伺服器已按目前帳號權限裁切")}</span>
        <span className="mono muted">{String(hub.generated_at || "").replace("T", " ")} · PERMISSION-FILTERED</span>
      </div>

      <div className="kpi-band warehouse-kpis">
        {showInventory && <Kpi label={t("在管 SKU")} value={fmt(inventory.skus)} unit={t("種")}
          foot={<span className="muted">{t("低於安全線")} <b className="num">{fmt(inventory.low_skus)}</b> · {t("零庫存")} <b className="num">{fmt(inventory.zero_skus)}</b></span>}/>}
        {showInventory && <Kpi label={t("可用 SKU")} value={fmt(inventory.available_skus)} unit={t("種")} foot={<span className="muted">{t("估算儲值")} · <b className="num">{fmt(inventory.stock_value, 2)}</b></span>}/>}
        {showInbound && <Kpi label={t("待完成入庫")} value={fmt(orders.inbound_open)} unit={t("單")} red={Number(orders.inbound_open) > 0}/>}
        {showOutbound && <Kpi label={t("待完成出庫")} value={fmt(orders.outbound_open)} unit={t("單")} red={Number(orders.urgent_outbound) > 0}
          foot={<span className="muted">{t("緊急")} · <b className="num">{fmt(orders.urgent_outbound)}</b></span>}/>}
        {showShipments && <Kpi label={t("在途批次")} value={fmt(shipments.active)} unit={t("批")} red={Number(shipments.delayed) > 0}
          foot={<span className="muted">{t("延誤")} <b className="num">{fmt(shipments.delayed)}</b> · 24h <b className="num">{fmt(shipments.due_24h)}</b></span>}/>}
        {showOutbound && <Kpi label={t("90 日 SKU 中位周轉")} value={!turnover || turnover.value == null ? "—" : fmt(turnover.value, 3)}
          foot={<span className="muted">{t("逐 SKU 出庫量 ÷ 現存量的中位數 · 營運估算")}</span>}/>}
      </div>

      {showInventory && <div className="warehouse-pivot-grid">
        <Band no="A" title={t("庫存結構")} sub={`${t("按功能分類")} · ${t("SKU 種數")}`}>
          <PivotRows rows={categoryRows} metric="skus"/>
        </Band>
        <Band no="B" title={t("庫存結構")} sub={`${t("按倉庫")} · ${t("SKU 種數")}`}>
          <PivotRows rows={warehouseRows} metric="skus"/>
        </Band>
      </div>}

      {(showInbound || showOutbound) && <Band no="C" title={t("收發趨勢")} sub={t("近六個月 · 單據量")}
        right={<div className="row g14 wrap">
          {showInbound && <span className="row g6 warehouse-legend"><i/>{t("入庫")}</span>}
          {showOutbound && <span className="row g6 warehouse-legend"><i className="hatched"/>{t("出庫")}</span>}
        </div>}>
        {hasFlow
          ? <MirrorBars labels={flow.map(row => String(row.month || "").slice(5))} up={inboundDocs} down={outboundDocs}
              upName={showInbound ? t("入庫") : "—"} downName={showOutbound ? t("出庫") : "—"} unit={" " + t("單")}/>
          : <EM icon="chart" title={t("尚無近期收發單據")} sub={t("產生單據後會按月形成雙向節奏。")}/>}
      </Band>}

      {(showInventory || showOutbound) && <div className="warehouse-pivot-grid">
        {showInventory && <Band no="F" title={t("安全線趨勢")} sub={t("逐 SKU 安全覆蓋率中位數")}>
          {coverage.length > 1
            ? <><TrendArea points={coverage.map(row => Number(row.coverage) || 0)} labels={coverage.map(row => row.label || "—")}/>
                <div className="muted" style={{ fontSize: 11, marginTop: 10 }}>{t("逐 SKU 安全覆蓋率中位數")} · %</div></>
            : <EM icon="trend" title={t("還沒有庫存趨勢資料")} sub={t("有出入庫流水後,總量走勢會出現在這裡。")}/>}
        </Band>}
        {showOutbound && <Band no="G" title={t("90 日耗用強度")} sub={t("按 SKU 週轉比排序")}>
          {consumption.length ? <div className="warehouse-pivot-list">
            {consumption.slice(0, 8).map((row, index) => <HBar key={(row.item_id || row.name) + ":" + index}
              idx={index + 1} name={row.name || "—"} w={(Number(row.turnover) || 0) / maxConsumption * 100}
              val={fmt(row.turnover, 3)} sub={`${fmt(row.quantity, 2)} ${row.unit || ""}`}
              onClick={() => { location.hash = "#/outbound"; }}/>) }
          </div> : <EM icon="trend" title={t("暫無出庫消耗資料")} sub={t("有出庫或領用後,排行自動生成。")}/>}
        </Band>}
      </div>}

      {showInventory && <Band no="H" title={t("需要關注")} sub={t("按安全覆蓋率排序")}>
        {attention.length ? <div className="warehouse-attention">
          {attention.map((item, index) => <a key={(item.item_id || item.name) + ":" + index} href="#/inventory" className="warehouse-attention-row">
            <span className="num muted">{String(index + 1).padStart(2, "0")}</span>
            <span style={{ flex: 1 }}>{item.name || "—"}</span>
            <b className="num">{fmt(item.stock, 2)} / {fmt(item.safe, 2)} {item.unit || ""}</b>
            <span className="num">{item.coverage == null ? "—" : fmt(item.coverage, 1) + "%"}</span>
          </a>)}
        </div> : <EM icon="checkCircle" title={t("目前沒有需要聚焦的異常")} sub={t("已按目前可見工作區過濾")}/>}
      </Band>}

      <div className="warehouse-pivot-grid">
        {showShipments && <Band no="D" title={t("在途老化")} sub={t("按發運後經過時間")}>
          {aging.length ? <div className="warehouse-pivot-list">
            {aging.map((row, index) => <HBar key={row.label} idx={index + 1} name={t(row.label)}
              w={(Number(row.value) || 0) / maxAge * 100} val={fmt(row.value)} sub={t("批")}/>) }
          </div> : <EM icon="outbound" title={t("目前沒有在途批次")}/>}
        </Band>}
        <Band no="E" title={t("異常聚焦")} sub={t("跨庫存、收發與在途")}>
          {anomalies.length ? <div className="warehouse-attention">
            {anomalies.map((item, index) => (
              <a key={item.key} href={tabHref(item.route)} className="warehouse-attention-row">
                <span className="num muted">{String(index + 1).padStart(2, "0")}</span>
                <span className="row g7" style={{ flex: 1 }}><i/>{t(item.label)}</span>
                <b className="num">{fmt(item.count)}</b><span>{t("查看")} →</span>
              </a>
            ))}
          </div> : <EM icon="checkCircle" title={t("目前沒有需要聚焦的異常")} sub={t("已按目前可見工作區過濾")}/>}
        </Band>
      </div>
    </>
  );
};

W2.WarehouseTabs = WarehouseTabs;
W2.PAGES["warehouse"] = PageWarehouse;
})();
