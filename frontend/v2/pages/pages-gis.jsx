/* WAREHOUSE 2.0 · 倉庫地圖 MAP / GIS — Swiss 版式,真後端(內置 MapLibre 實景地圖) */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "倉庫地圖": "Warehouse map",
  "盤點": "Stocktake",
  "倉庫 GIS 定位 · 內置實景地圖 · 頁面只讀,定位與找貨交秘書": "Warehouse GIS · built-in live map · read-only, locate & find via Secretary",
  "倉庫地圖上現在有什麼要處理的?哪些倉庫還沒定位、哪些庫區有風險?": "Anything to handle on the warehouse map? Which warehouses lack GIS location, which zones are at risk?",
  "在管倉庫": "Warehouses",
  "座": "", "個": "", "種": "SKUs",
  "庫存合計 {n}": "Total stock {n}",
  "未定位倉庫": "Unlocated",
  "讓秘書定位 →": "Locate via Secretary →",
  "全部已定位": "All located",
  "把還沒有 GIS 定位的倉庫列出來,逐個追問地址或經緯度後幫我保存定位": "List warehouses without GIS location; ask me for each address or coordinates, then save the locations",
  "庫區": "Zones",
  "共 {n} 個貨位": "{n} slots in total",
  "風險庫區": "Zones at risk",
  "無風險": "No risk",
  "交秘書處置": "Secretary resolve",
  "分析有預警的庫區,按風險排序給我處置建議": "Analyse zones with alerts, rank by risk and give me resolution advice",
  /* 地圖 Band */
  "實景地圖": "Live map",
  "{a} 已定位 · {b} 未定位": "{a} located · {b} unlocated",
  "地圖組件載入中…": "Loading map engine…",
  "地圖組件尚未就緒": "Map engine not ready",
  "可能是網絡較慢或地圖庫尚未載入;下方清單與數據不受影響。": "The map library may still be loading on a slow network; the register below is unaffected.",
  "重試": "Retry",
  "此環境不支持 WebGL": "WebGL is unavailable here",
  "已自動降級為清單視圖,全部數據仍可在下方查看與交秘書處理。": "Degraded to list view — everything remains available below and via the Secretary.",
  "地圖已就緒 · 尚無已定位倉庫": "Map ready · no located warehouses yet",
  "在下方清單選一個倉庫進入定位模式,點地圖取得座標後交秘書保存。": "Pick a warehouse below to enter locate mode, click the map for coordinates, then hand them to the Secretary.",
  "定位模式": "Locate mode",
  "點擊地圖任意位置,為「{name}」選取座標": "Click anywhere on the map to pick coordinates for “{name}”",
  "已選": "Picked",
  "交秘書定位到此處": "Secretary: locate here",
  "退出定位": "Exit",
  "把倉庫「{name}」的 GIS 定位設置為:緯度 {lat}、經度 {lng}(WGS-84 十進制),請確認無誤後保存": "Set the GIS location of warehouse \"{name}\" to latitude {lat}, longitude {lng} (WGS-84 decimal); confirm with me, then save",
  "選未定位倉庫進入定位模式:": "Enter locate mode for an unlocated warehouse:",
  "地圖瓦片加載較慢或失敗,不影響清單與秘書操作。": "Map tiles are slow or failing; the register and Secretary are unaffected.",
  /* 抽屜 */
  "在地圖上定位": "Locate on the map",
  "飛到此倉庫": "Fly to this warehouse",
  "進入定位模式": "Enter locate mode",
  "未編碼": "Uncoded",
  "物資種類": "SKUs",
  "庫存量": "Stock qty",
  "容量使用": "Capacity",
  "座標": "Coordinates",
  "此倉庫存 Top": "Top stock here",
  "此倉庫暫無庫存記錄": "No stock records for this warehouse",
  "問情況": "Status",
  "調撥": "Transfer",
  "我要從倉庫「{name}」調撥物資到其他倉庫,請追問物資、數量和目標倉庫後辦理": "Transfer stock out of warehouse \"{name}\" — ask me for the item, quantity and destination warehouse, then proceed",
  "幫我為倉庫「{name}」安排一次盤點,請追問盤點範圍後辦理": "Arrange a stocktake for warehouse \"{name}\" — ask me for the scope, then proceed",
  /* 清單 Band */
  "倉庫清單": "Warehouse register",
  "{n} 座 · 同一後端實時": "{n} warehouses · live from the same backend",
  "庫存分佈": "Stock distribution",
  "倉庫": "Warehouse", "編碼 / 類型": "Code / Type", "地址": "Address",
  "物資 / 庫存": "Items / Stock", "容量": "Capacity", "定位": "Location",
  "默認庫": "DEFAULT", "已定位": "Located", "未定位": "Unlocated", "未分類": "untyped",
  "交給秘書": "To Secretary",
  "問秘書": "Ask Secretary",
  "倉庫「{name}」現在的物資、庫存和預警情況怎麼樣?": "How are items, stock and alerts in warehouse \"{name}\" right now?",
  "還沒有倉庫資料": "No warehouses yet",
  "對秘書說「幫我登記一個倉庫」,登記後即可在地圖上定位。": "Tell the Secretary to register a warehouse; once registered you can locate it on the map.",
  "幫我登記一個新倉庫,請追問名稱、類型和地址後辦理": "Register a new warehouse for me — ask for name, type and address, then proceed",
  "登記倉庫": "Register warehouse",
  "庫區與貨位": "Zones & slots",
  "{z} 個庫區 · {r} 個貨位": "{z} zones · {r} slots",
  "找物資位置": "Find an item",
  "幫我找物資的存放位置,請追問物資名稱後告訴我它在哪個倉庫、哪個庫位": "Find where an item is stored — ask me for the item name, then tell me its warehouse and slot",
  "{r} 貨位 · {i} 種": "{r} slots · {i} SKUs",
  "{n} 風險": "{n} at risk",
  "正常": "OK",
  "問這個庫區": "Ask about zone",
  "庫區「{name}」({id})現在存了哪些物資?有沒有低庫存或風險?": "What is stored in zone \"{name}\" ({id})? Any low stock or risks?",
  "點擊查看 Swiss 庫位矩陣": "Open Swiss slot matrix",
  "庫位矩陣": "Slot matrix",
  "{n} 個庫位 · 點格子查看明細": "{n} slots · select a cell for details",
  "實時庫位資料": "Live slot data",
  "實時 + 匯總": "Live + summary",
  "匯總生成": "Generated from summary",
  "貨位詳情": "Slot details",
  "空貨位": "Empty",
  "低庫存": "Low stock",
  "風險": "Risk",
  "規劃貨位": "Planned slot",
  "安全庫存": "Safety stock",
  "示例物資": "Sample items",
  "暫無物資": "No items here",
  "貨架 / 樓層": "Rack / floor",
  "未配置": "Not configured",
  "問這個貨位": "Ask about slot",
  "貨位「{code}」目前有哪些物資、庫存和預警?請按物資列出數量並給我處置建議": "What items, stock and alerts are currently at slot \"{code}\"? List quantities by item and recommend next actions",
  "安排盤點": "Arrange stocktake",
  "幫我為庫區「{zone}」的貨位「{code}」安排一次盤點,請確認範圍後辦理": "Arrange a stocktake for slot \"{code}\" in zone \"{zone}\"; confirm the scope with me, then proceed",
  "實時明細載入中,目前按庫區匯總生成矩陣。": "Live details are loading; the matrix is currently generated from the zone summary.",
  "實時明細暫不可用,目前按庫區匯總生成矩陣。": "Live details are unavailable; the matrix is currently generated from the zone summary.",
  "部分貨位尚無實時明細,已用規劃格補齊;規劃格不會發起貨位操作。": "Some slots have no live details and are completed with planned cells; planned cells cannot start slot actions.",
  "此格由庫區貨位數量生成,尚未取得真實貨位編碼。": "This cell is generated from the zone slot count; its real slot code is not available yet.",
  "此庫區尚未配置貨位": "No slots are configured for this zone",
  "選擇左側貨位查看庫存、容量與預警明細。": "Select a slot on the left to inspect stock, capacity and alerts.",
  "關閉庫位矩陣": "Close slot matrix",
  "矩陣狀態": "Matrix status",
  "風險貨位": "Risk slots",
  "預警項": "Alert items",
  "還沒有庫區資料": "No zones yet",
  "對秘書說「幫我從庫存整理生成庫區與貨位」。": "Tell the Secretary to derive zones and slots from stock data.",
  "幫我從現有庫存資料自動整理生成庫區和貨位": "Derive zones and slots automatically from the current stock data",
  "讓秘書整理庫位": "Organise via Secretary",
  "載入中…": "Loading…",
  "內置實景地圖已啟用;點標記看詳情,定位與改動交秘書執行。": "Built-in live map enabled; click a marker for detail — locating and changes run through the Secretary.",
});
const { useState: _s, useEffect: _e, useMemo: _mm, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, StackBar, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* 底圖:與 1.0(page-warehouse-gis.jsx)同源 openfreemap;positron=淡色,最接近紙墨 */
const MAP_STYLE = "https://tiles.openfreemap.org/styles/positron";
const MAP_CENTER = [111.7490, 40.8417];

/* 數量顯示:非數字給 —,大數帶千分位 */
const fq = (v) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return (Math.round(n * 10) / 10).toLocaleString();
};
const capColor = (c) => c >= 90 ? "var(--red)" : c >= 70 ? "var(--warn)" : "var(--ink)";
/* 已定位 = lat/lng 同時存在且為有效數字(髒數據如 "" / "abc" 一律視為未定位,避免 NaN 上屏) */
const hasLL = (w) => w != null && w.lat != null && w.lng != null &&
  Number.isFinite(Number(w.lat)) && Number.isFinite(Number(w.lng));
const kOf = (w) => w && w.id != null ? "id:" + w.id : "nm:" + ((w && w.name) || "?");
const pctOf = (v) => {
  if (v == null || String(v).trim() === "") return null;
  const n = Number(v);
  return Number.isFinite(n) ? Math.min(140, Math.max(0, n)) : null;
};
const zoneCodeOf = (z) => String((z && (z.zone_code != null ? z.zone_code : z.id)) || "—");
const zoneNameOf = (z) => (z && (z.zone_name || z.name)) || "—";
const zoneWarehouseOf = (z) => z && z.warehouse_id != null
  ? String(z.warehouse_id)
  : String((z && z.warehouse_name) || "");
const zoneRecordIdOf = (z) => z && z.zone_id != null
  ? String(z.zone_id)
  : (z && z.zone_code != null && z.id != null ? String(z.id) : "");
const zoneKeyOf = (z) => "zone:" + zoneWarehouseOf(z) + ":" + zoneCodeOf(z) + ":" + zoneRecordIdOf(z);
const zoneRackCount = (z) => num(z && (z.rack_count != null ? z.rack_count : z.racks));
const zoneItemCount = (z) => num(z && (z.item_count != null ? z.item_count : z.items));
const zoneAlertCount = (z) => num(z && (z.alert_count != null ? z.alert_count : z.alert));
const locationCodeOf = (loc) => String((loc && (loc.location_code || loc.rack_code || loc.code)) || "—");
const locationKeyOf = (loc) => {
  if (loc && loc.id != null) return "location:" + String(loc.id);
  return "location:" + String((loc && loc.warehouse_id) || "") + ":" + locationCodeOf(loc);
};
const locationMatchesZone = (loc, zone) => {
  if (!loc || !zone) return false;
  const lw = loc.warehouse_id != null ? String(loc.warehouse_id) : String(loc.warehouse_name || "");
  const zw = zoneWarehouseOf(zone);
  if (lw && zw && lw !== zw) return false;
  const zoneDbId = zoneRecordIdOf(zone);
  if (loc.zone_id != null && zoneDbId != null && String(loc.zone_id) === String(zoneDbId)) return true;
  if (String(loc.zone_code || "") !== zoneCodeOf(zone)) return false;
  return !lw || !zw || lw === zw;
};
const locationsForZone = (rows, zone) => (Array.isArray(rows) ? rows : [])
  .filter((loc) => locationMatchesZone(loc, zone))
  .slice()
  .sort((a, b) => locationCodeOf(a).localeCompare(locationCodeOf(b), undefined, { numeric: true, sensitivity: "base" }));
const slotStatus = (loc) => {
  const raw = String((loc && loc.alert_status) || "").toLowerCase();
  if (raw === "risk" || raw === "danger" || raw === "alert") return "risk";
  if (raw === "low_stock" || raw === "low" || raw === "warning") return "low_stock";
  if (raw === "empty") return "empty";
  if (num(loc && loc.low_stock_count) > 0) return "risk";
  const stock = Number(loc && loc.stock_total);
  const safe = Number(loc && loc.safe_total);
  if (Number.isFinite(stock) && stock <= 0) return "empty";
  if (num(loc && loc.item_count) <= 0 && !Number.isFinite(stock)) return "empty";
  if (Number.isFinite(stock) && Number.isFinite(safe) && safe > 0 && stock < safe) return "low_stock";
  return "normal";
};
const slotStatusLabel = (status) => status === "risk"
  ? t("風險")
  : status === "low_stock"
    ? t("低庫存")
    : status === "empty"
      ? t("空貨位")
      : t("正常");
const slotTone = (status) => status === "risk" ? "bad" : status === "low_stock" ? "warn" : status === "normal" ? "ok" : "plain";
const slotCapacity = (loc) => {
  const direct = pctOf(loc && loc.capacity_usage);
  if (direct != null) return direct;
  const stock = Number(loc && loc.stock_total);
  const safe = Number(loc && loc.safe_total);
  return Number.isFinite(stock) && Number.isFinite(safe) && safe > 0 ? pctOf(stock / safe * 100) : null;
};
const zoneCapacity = (zone, liveSlots) => {
  const caps = (liveSlots || []).map(slotCapacity).filter((v) => v != null);
  if (caps.length) return Math.round(caps.reduce((sum, v) => sum + v, 0) / caps.length);
  return pctOf(zone && (zone.capacity_usage != null ? zone.capacity_usage : zone.cap));
};
const zoneRiskCount = (zone, liveSlots) => {
  if (Array.isArray(liveSlots) && liveSlots.length) {
    return liveSlots.filter((loc) => {
      const status = slotStatus(loc);
      return status === "risk" || status === "low_stock";
    }).length;
  }
  return zoneAlertCount(zone);
};
const buildZoneSlots = (zone, rows) => {
  if (!zone) return [];
  const live = locationsForZone(rows, zone).map((loc) => ({ ...loc, __planned: false }));
  const target = Math.max(zoneRackCount(zone), live.length);
  let serial = 1;
  while (live.length < target) {
    const code = "#" + pad2(serial++);
    live.push({
      id: "planned:" + zoneKeyOf(zone) + ":" + code,
      warehouse_id: zone && zone.warehouse_id,
      zone_id: zone && zone.id,
      zone_code: zoneCodeOf(zone),
      location_code: code,
      item_count: 0,
      stock_total: 0,
      safe_total: 0,
      capacity_usage: 0,
      alert_status: "empty",
      sample_items: [],
      __planned: true,
    });
  }
  return live;
};
const webglOk = () => {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (e) { return false; }
};

/* Swiss 化圖面:filter 只壓 canvas(底圖),DOM 標記不受影響 */
const GIS_CSS = `
.w2gis-wrap { position: relative; height: 480px; background: var(--paper-2); border: 1px solid var(--hair); border-top: 2px solid var(--rule); }
.w2gis-wrap .maplibregl-canvas { filter: grayscale(1) sepia(.14) brightness(1.05) contrast(.95); }
.w2gis-wrap .maplibregl-ctrl-group { border-radius: 0 !important; box-shadow: none !important; border: 1px solid var(--ink); background: var(--white); }
.w2gis-wrap .maplibregl-ctrl-group button { border-radius: 0 !important; }
.w2gis-wrap .maplibregl-ctrl-attrib { border-radius: 0 !important; font-family: var(--f-mono); font-size: 10px; background: rgba(252,251,247,.85) !important; }
.w2gis-wrap .maplibregl-ctrl-scale { border-radius: 0; border-color: var(--ink); background: rgba(252,251,247,.7); font-family: var(--f-mono); font-size: 10px; }
.w2gis-pin { display: flex; flex-direction: column; align-items: center; background: none; border: 0; padding: 0; cursor: pointer; }
.w2gis-pin .p-tag { display: flex; align-items: center; gap: 7px; background: var(--ink); color: var(--paper); border: 1px solid var(--white); padding: 4px 8px; font-family: var(--f-mono); font-size: 10px; font-weight: 700; letter-spacing: .05em; white-space: nowrap; }
.w2gis-pin .p-name { max-width: 132px; overflow: hidden; text-overflow: ellipsis; }
.w2gis-pin .p-cap { opacity: .82; }
.w2gis-pin .p-stem { width: 1px; height: 8px; background: var(--ink); }
.w2gis-pin.hot .p-tag { background: var(--red); color: #fff; }
.w2gis-pin.hot .p-stem { background: var(--red); }
.w2gis-pin.on .p-tag { outline: 2px solid var(--red); outline-offset: 1px; }
.w2gis-pin.hot.on .p-tag { outline-color: var(--ink); }
.w2gis-pick { width: 12px; height: 12px; background: var(--red); border: 2px solid #fff; }
.w2zone-card { display: flex; flex-direction: column; min-width: 0; border-right: 1px solid var(--hair-soft); border-bottom: 1px solid var(--hair-soft); }
.w2zone-card-hit { display: flex; flex: 1; flex-direction: column; gap: 8px; width: 100%; padding: 16px 16px 13px; border: 0; background: transparent; color: inherit; text-align: left; cursor: pointer; }
.w2zone-card-hit:hover { background: var(--paper-2); }
.w2zone-card-hit:focus-visible { outline: 2px solid var(--red); outline-offset: -2px; }
.w2zone-card-foot { display: flex; padding: 0 16px 14px; }
.w2zone-open { display: inline-flex; align-items: center; gap: 7px; margin-top: 3px; color: var(--red); font-family: var(--f-mono); font-size: 9.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
.w2zone-open::after { content: "↗"; font-size: 13px; line-height: 1; }
.w2zone-matrix-backdrop { position: fixed; inset: 0; z-index: 140; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(10,10,10,.62); }
.w2zone-matrix-dialog { display: grid; grid-template-rows: auto auto minmax(0,1fr); width: min(1120px, calc(100vw - 32px)); max-height: calc(100dvh - 32px); overflow: hidden; border: 2px solid var(--ink); background: var(--paper); color: var(--ink); }
.w2zone-dialog-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; padding: 18px 20px 16px; border-bottom: 2px solid var(--rule); }
.w2zone-dialog-code { font-family: var(--f-mono); font-size: clamp(38px, 5vw, 68px); font-weight: 800; letter-spacing: -.06em; line-height: .9; }
.w2zone-dialog-title { margin-top: 7px; font-size: 17px; font-weight: 750; line-height: 1.2; }
.w2zone-dialog-close { display: inline-grid; place-items: center; width: 34px; height: 34px; flex: 0 0 auto; border: 1px solid var(--ink); background: transparent; color: inherit; cursor: pointer; }
.w2zone-dialog-close:hover, .w2zone-dialog-close:focus-visible { background: var(--ink); color: var(--paper); outline: 0; }
.w2zone-summary { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); border-bottom: 2px solid var(--rule); }
.w2zone-summary-cell { min-width: 0; padding: 11px 14px; border-right: 1px solid var(--hair-soft); }
.w2zone-summary-cell:last-child { border-right: 0; }
.w2zone-summary-cell strong { display: block; margin-top: 3px; font-family: var(--f-mono); font-size: 19px; line-height: 1.1; }
.w2zone-matrix-body { display: grid; grid-template-columns: minmax(0,1fr) 310px; min-height: 0; }
.w2zone-matrix-main { min-width: 0; overflow: auto; padding: 18px 20px 22px; }
.w2zone-matrix-meta { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 12px; }
.w2zone-legend { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 5px; }
.w2zone-matrix-grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); border-top: 1px solid var(--ink); border-left: 1px solid var(--ink); }
.w2zone-slot { position: relative; display: flex; min-width: 0; min-height: 124px; flex-direction: column; justify-content: space-between; gap: 10px; padding: 12px; border: 0; border-right: 1px solid var(--ink); border-bottom: 1px solid var(--ink); border-top: 4px solid var(--ok); background: var(--white); color: var(--ink); text-align: left; cursor: pointer; }
.w2zone-slot.is-risk { border-top-color: var(--red); }
.w2zone-slot.is-low_stock { border-top-color: var(--warn); }
.w2zone-slot.is-empty { border-top-color: var(--hair); background-color: var(--paper-2); background-image: repeating-linear-gradient(135deg, transparent 0, transparent 7px, rgba(120,120,120,.09) 7px, rgba(120,120,120,.09) 8px); }
.w2zone-slot:hover { outline: 2px solid var(--red); outline-offset: -2px; z-index: 1; }
.w2zone-slot:focus-visible { outline: 3px solid var(--red); outline-offset: -3px; z-index: 2; }
.w2zone-slot.is-selected { background: var(--ink); background-image: none; color: var(--paper); outline: 3px solid var(--ink); outline-offset: -3px; z-index: 1; }
.w2zone-slot.is-selected .muted { color: var(--paper); opacity: .72; }
.w2zone-slot.is-selected .bar { background: rgba(255,255,255,.22); }
.w2zone-slot-code { overflow: hidden; font-family: var(--f-mono); font-size: 17px; font-weight: 800; line-height: 1; text-overflow: ellipsis; white-space: nowrap; }
.w2zone-slot-cap { font-family: var(--f-mono); font-size: 25px; font-weight: 800; letter-spacing: -.04em; line-height: 1; }
.w2zone-slot-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; font-family: var(--f-mono); font-size: 10px; }
.w2zone-inspector { min-width: 0; overflow: auto; border-left: 2px solid var(--rule); background: var(--white); }
.w2zone-inspector-head { padding: 16px; border-bottom: 2px solid var(--rule); }
.w2zone-inspector-body { display: flex; flex-direction: column; gap: 14px; padding: 16px; }
.w2zone-detail-grid { display: grid; grid-template-columns: 1fr 1fr; border-top: 1px solid var(--ink); border-left: 1px solid var(--ink); }
.w2zone-detail-cell { min-width: 0; padding: 10px; border-right: 1px solid var(--ink); border-bottom: 1px solid var(--ink); }
.w2zone-detail-cell strong { display: block; margin-top: 4px; overflow: hidden; font-family: var(--f-mono); font-size: 15px; text-overflow: ellipsis; white-space: nowrap; }
.w2zone-source-note { padding: 9px 10px; border-left: 3px solid var(--warn); background: var(--paper-2); font-size: 11.5px; line-height: 1.55; }
@media (max-width: 900px) {
  .w2zone-matrix-grid { grid-template-columns: repeat(3, minmax(0,1fr)); }
  .w2zone-matrix-body { grid-template-columns: minmax(0,1fr) 280px; }
}
@media (max-width: 720px) {
  .w2zone-matrix-backdrop { align-items: flex-end; padding: 0; }
  .w2zone-matrix-dialog { width: 100%; max-height: 94dvh; border-width: 2px 0 0; }
  .w2zone-summary { grid-template-columns: 1fr 1fr; }
  .w2zone-summary-cell:nth-child(2) { border-right: 0; }
  .w2zone-summary-cell:nth-child(-n+2) { border-bottom: 1px solid var(--hair-soft); }
  .w2zone-matrix-body { display: block; overflow: auto; }
  .w2zone-matrix-main { overflow: visible; padding: 16px 14px 20px; }
  .w2zone-inspector { overflow: visible; border-top: 2px solid var(--rule); border-left: 0; }
}
@media (max-width: 500px) {
  .w2zone-dialog-head { position: relative; padding: 15px 56px 15px 14px; }
  .w2zone-dialog-head > .row { max-width: 100%; align-items: flex-start !important; }
  .w2zone-dialog-close { position: absolute; top: 14px; right: 14px; }
  .w2zone-matrix-meta { align-items: flex-start; flex-direction: column; }
  .w2zone-legend { justify-content: flex-start; }
  .w2zone-matrix-grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
  .w2zone-slot { min-height: 112px; padding: 10px; }
}
`;

const ZoneMatrixDialog = ({ zone, slots, selectedKey, overviewState, onSelect, onClose }) => {
  const dialogRef = _r(null);
  const closeRef = _r(null);
  const liveSlots = slots.filter((loc) => !loc.__planned);
  const selected = slots.find((loc) => locationKeyOf(loc) === selectedKey) || null;
  const statusCounts = slots.reduce((acc, loc) => {
    const status = slotStatus(loc);
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, { normal: 0, low_stock: 0, risk: 0, empty: 0 });
  const cap = zoneCapacity(zone, liveSlots);
  const sourceLive = liveSlots.length > 0;
  const sourceComplete = overviewState === "ready" && slots.length > 0 && liveSlots.length === slots.length;
  const sourceMixed = sourceLive && liveSlots.length < slots.length;
  const alertCount = zoneRiskCount(zone, liveSlots);
  const selectedStatus = selected ? slotStatus(selected) : "empty";
  const selectedCap = selected ? slotCapacity(selected) : null;
  const samples = selected && Array.isArray(selected.sample_items) ? selected.sample_items : [];
  const rackFloor = selected
    ? [selected.rack_code || null, selected.floor_no != null ? selected.floor_no : null].filter((v) => v != null && v !== "").join(" / ")
    : "";

  _e(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const timer = setTimeout(() => {
      if (closeRef.current) closeRef.current.focus();
    }, 0);
    return () => {
      clearTimeout(timer);
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const trapDialogFocus = (e) => {
    if (e.key !== "Tab" || !dialogRef.current) return;
    const focusable = Array.from(dialogRef.current.querySelectorAll(
      'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
    )).filter((node) => node.offsetParent !== null);
    if (!focusable.length) return;
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  return (
    <div className="w2zone-matrix-backdrop" onMouseDown={onClose}>
      <section ref={dialogRef} className="w2zone-matrix-dialog" role="dialog" aria-modal="true"
        aria-label={t("庫位矩陣")} onKeyDown={trapDialogFocus} onMouseDown={(e) => e.stopPropagation()}>
        <header className="w2zone-dialog-head">
          <div className="row g16" style={{ alignItems: "flex-end", minWidth: 0 }}>
            <div className="w2zone-dialog-code">{zoneCodeOf(zone)}</div>
            <div className="col g5" style={{ minWidth: 0 }}>
              <LB red>ZONE / SWISS MATRIX</LB>
              <div className="w2zone-dialog-title">{zoneNameOf(zone)}</div>
              <div className="row g5 wrap">
                {zone.warehouse_name && <T tone="plain">{zone.warehouse_name}</T>}
                <T tone={sourceComplete ? "ok" : sourceMixed ? "warn" : "plain"} dot={sourceComplete}>
                  {sourceComplete ? t("實時庫位資料") : sourceMixed ? t("實時 + 匯總") : t("匯總生成")}
                </T>
              </div>
            </div>
          </div>
          <button ref={closeRef} type="button" className="w2zone-dialog-close" title={t("關閉庫位矩陣")}
            aria-label={t("關閉庫位矩陣")} onClick={onClose}><I name="x" size={15}/></button>
        </header>

        <div className="w2zone-summary">
          <div className="w2zone-summary-cell"><LB dim>{t("庫位矩陣")}</LB><strong>{slots.length}</strong></div>
          <div className="w2zone-summary-cell"><LB dim>{t("物資種類")}</LB><strong>{zoneItemCount(zone)}</strong></div>
          <div className="w2zone-summary-cell"><LB dim>{t("容量使用")}</LB><strong style={{ color: cap == null ? "inherit" : capColor(cap) }}>{cap == null ? "—" : Math.round(cap) + "%"}</strong></div>
          <div className="w2zone-summary-cell"><LB dim>{sourceLive ? t("風險貨位") : t("預警項")}</LB><strong style={{ color: alertCount > 0 ? "var(--red)" : "inherit" }}>{alertCount}</strong></div>
        </div>

        <div className="w2zone-matrix-body">
          <div className="w2zone-matrix-main">
            <div className="w2zone-matrix-meta">
              <div className="col g4">
                <LB dim>{t("矩陣狀態")}</LB>
                <div style={{ fontWeight: 750, fontSize: 14 }}>{t("{n} 個庫位 · 點格子查看明細", { n: slots.length })}</div>
              </div>
              <div className="w2zone-legend">
                <T tone="ok" dot>{t("正常")} {statusCounts.normal}</T>
                <T tone="warn">{t("低庫存")} {statusCounts.low_stock}</T>
                <T tone="bad" dot>{t("風險")} {statusCounts.risk}</T>
                <T tone="plain">{t("空貨位")} {statusCounts.empty}</T>
              </div>
            </div>

            {!sourceComplete && (
              <div className="w2zone-source-note" style={{ marginBottom: 12 }}>
                {overviewState === "loading"
                  ? t("實時明細載入中,目前按庫區匯總生成矩陣。")
                  : overviewState === "fallback" || !sourceLive
                    ? t("實時明細暫不可用,目前按庫區匯總生成矩陣。")
                    : t("部分貨位尚無實時明細,已用規劃格補齊;規劃格不會發起貨位操作。")}
              </div>
            )}

            {slots.length ? (
              <div className="w2zone-matrix-grid">
                {slots.map((loc) => {
                  const key = locationKeyOf(loc);
                  const status = slotStatus(loc);
                  const locCap = slotCapacity(loc);
                  return (
                    <button type="button" key={key}
                      className={"w2zone-slot is-" + status + (key === selectedKey ? " is-selected" : "")}
                      aria-pressed={key === selectedKey} onClick={() => onSelect(key)}>
                      <div className="row spread g8">
                        <span className="w2zone-slot-code">{locationCodeOf(loc)}</span>
                        <span className="label" style={{ color: status === "risk" ? "var(--red)" : "currentColor" }}>{slotStatusLabel(status)}</span>
                      </div>
                      <div className="col g6">
                        <div className="w2zone-slot-cap">{locCap == null ? "—" : Math.round(locCap) + "%"}</div>
                        <div className="bar"><i style={{ width: Math.min(100, locCap == null ? 0 : locCap) + "%", background: status === "risk" ? "var(--red)" : status === "low_stock" ? "var(--warn)" : "currentColor" }}/></div>
                      </div>
                      <div className="w2zone-slot-foot">
                        <span>{num(loc.item_count)} {t("種")}</span>
                        <span>{fq(loc.stock_total)}</span>
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <EM icon="layers" title={t("此庫區尚未配置貨位")} sub={t("選擇左側貨位查看庫存、容量與預警明細。")}/>
            )}
          </div>

          <aside className="w2zone-inspector">
            <div className="w2zone-inspector-head">
              <LB red>{t("貨位詳情")}</LB>
              <div style={{ marginTop: 6, fontFamily: "var(--f-mono)", fontSize: 23, fontWeight: 800 }}>
                {selected ? locationCodeOf(selected) : "—"}
              </div>
            </div>
            {selected ? (
              <div className="w2zone-inspector-body">
                <div className="row g6 wrap">
                  <T tone={slotTone(selectedStatus)} dot={selectedStatus === "normal" || selectedStatus === "risk"}>{slotStatusLabel(selectedStatus)}</T>
                  {selected.__planned && <T tone="plain">{t("規劃貨位")}</T>}
                  {selected.derived && <T tone="plain">{t("實時庫位資料")}</T>}
                </div>
                <div className="w2zone-detail-grid">
                  <div className="w2zone-detail-cell"><LB dim>{t("物資種類")}</LB><strong>{num(selected.item_count)}</strong></div>
                  <div className="w2zone-detail-cell"><LB dim>{t("容量使用")}</LB><strong>{selectedCap == null ? "—" : Math.round(selectedCap) + "%"}</strong></div>
                  <div className="w2zone-detail-cell"><LB dim>{t("庫存量")}</LB><strong>{fq(selected.stock_total)}</strong></div>
                  <div className="w2zone-detail-cell"><LB dim>{t("安全庫存")}</LB><strong>{fq(selected.safe_total)}</strong></div>
                </div>
                <div className="col g5">
                  <LB dim>{t("貨架 / 樓層")}</LB>
                  <span className="mono" style={{ fontSize: 12.5, fontWeight: 700 }}>{rackFloor || t("未配置")}</span>
                </div>
                <div className="col g5">
                  <LB dim>{t("示例物資")}</LB>
                  {samples.length ? samples.map((name, i) => (
                    <div key={String(name) + ":" + i} className="row g8" style={{ padding: "7px 0", borderBottom: "1px solid var(--hair-soft)" }}>
                      <span className="lr-idx">{pad2(i + 1)}</span>
                      <span style={{ minWidth: 0, overflow: "hidden", fontSize: 12.5, fontWeight: 650, textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{name}</span>
                    </div>
                  )) : <span className="muted" style={{ fontSize: 12 }}>{t("暫無物資")}</span>}
                </div>
                {selected.__planned ? (
                  <>
                    <div className="w2zone-source-note">{t("此格由庫區貨位數量生成,尚未取得真實貨位編碼。")}</div>
                    <B size="sm" icon="sparkle" onClick={() => ask(t("庫區「{name}」({id})現在存了哪些物資?有沒有低庫存或風險?", { name: zoneNameOf(zone), id: zoneCodeOf(zone) }))}>{t("問這個庫區")}</B>
                  </>
                ) : (
                  <div className="row g6 wrap">
                    <B size="sm" icon="sparkle" onClick={() => ask(t("貨位「{code}」目前有哪些物資、庫存和預警?請按物資列出數量並給我處置建議", { code: locationCodeOf(selected) }))}>{t("問這個貨位")}</B>
                    <B size="sm" icon="clipboard" onClick={() => ask(t("幫我為庫區「{zone}」的貨位「{code}」安排一次盤點,請確認範圍後辦理", { zone: zoneNameOf(zone), code: locationCodeOf(selected) }))}>{t("安排盤點")}</B>
                  </div>
                )}
              </div>
            ) : (
              <div className="muted" style={{ padding: 16, fontSize: 12.5, lineHeight: 1.7 }}>{t("選擇左側貨位查看庫存、容量與預警明細。")}</div>
            )}
          </aside>
        </div>
      </section>
    </div>
  );
};

const PageGis = ({ boot }) => {
  const [geo, setGeo] = _s(null); // null=載入中,之後恆為對象
  const [overview, setOverview] = _s(null);
  const [overviewState, setOverviewState] = _s("loading"); // loading | ready | fallback
  const [selKey, setSelKey] = _s(null);       // 抽屜選中倉庫(kOf)
  const [zoneSel, setZoneSel] = _s(null);     // { key, code, warehouse }
  const [slotSelKey, setSlotSelKey] = _s(null);
  const [locate, setLocate] = _s(null);       // 定位模式中的倉庫對象
  const [pick, setPick] = _s(null);           // 定位模式選中的 {lat,lng}
  const [glState, setGlState] = _s("wait");   // wait | ok | none(庫未載入) | fail(WebGL 不可用)
  const [glTry, setGlTry] = _s(0);
  const [mapLive, setMapLive] = _s(false);
  const [tileSlow, setTileSlow] = _s(false);

  const mapNode = _r(null);
  const mapRef = _r(null);
  const markersRef = _r([]);
  const pickMarkRef = _r(null);
  const locateRef = _r(null);
  const fitRef = _r(false);
  const zoneTriggerRef = _r(null);

  _e(() => { W2.json("/api/warehouses/geo").then((d) => setGeo(d || {})).catch(() => setGeo({})); }, []);
  _e(() => {
    let alive = true;
    W2.json("/api/gis/overview").then((d) => {
      if (!alive) return;
      setOverview(d || {});
      setOverviewState("ready");
    }).catch(() => {
      if (!alive) return;
      setOverviewState("fallback");
    });
    return () => { alive = false; };
  }, []);

  const whs = (geo && Array.isArray(geo.warehouses)) ? geo.warehouses : [];
  const bootZones = (boot && Array.isArray(boot.ZONES)) ? boot.ZONES : [];
  const zones = (overview && Array.isArray(overview.zones)) ? overview.zones : bootZones;
  const locations = (overview && Array.isArray(overview.locations)) ? overview.locations : [];
  const located = whs.filter(hasLL);
  const unlocatedList = whs.filter((w) => !hasLL(w));
  const unlocated = unlocatedList.length;
  const totalRacks = zones.reduce((s, z) => s + zoneRackCount(z), 0);
  const riskZones = zones.filter((z) => zoneRiskCount(z, locationsForZone(locations, z)) > 0);
  const stockTotal = whs.reduce((s, w) => s + num(w.stock_total), 0);
  const sel = whs.find((w) => kOf(w) === selKey) || null;
  const selectedZone = zoneSel
    ? zones.find((z) => zoneKeyOf(z) === zoneSel.key)
      || zones.find((z) => zoneCodeOf(z) === zoneSel.code
        && (!zoneSel.warehouse || !zoneWarehouseOf(z) || zoneWarehouseOf(z) === zoneSel.warehouse))
      || null
    : null;
  const matrixSlots = _mm(() => buildZoneSlots(selectedZone, locations), [selectedZone, overview]);
  const matrixSlotKeys = matrixSlots.map(locationKeyOf).join("|");

  function openZoneMatrix(zone, trigger) {
    zoneTriggerRef.current = trigger || null;
    setZoneSel({ key: zoneKeyOf(zone), code: zoneCodeOf(zone), warehouse: zoneWarehouseOf(zone) });
    setSlotSelKey(null);
  }
  function closeZoneMatrix() {
    const trigger = zoneTriggerRef.current;
    setZoneSel(null);
    setSlotSelKey(null);
    setTimeout(() => {
      if (trigger && trigger.isConnected) trigger.focus();
    }, 0);
  }

  const stack = _mm(() => whs
    .map((w, i) => ({ value: num(w.stock_total), color: W2.CHART_COLORS[i % W2.CHART_COLORS.length], label: w.name || "—" }))
    .filter((d) => d.value > 0), [geo]);

  /* 抽屜:該倉庫存 Top(來自 bootstrap INVENTORY,按倉庫名匹配) */
  const topItems = _mm(() => {
    if (!sel) return [];
    const inv = (boot && Array.isArray(boot.INVENTORY)) ? boot.INVENTORY : [];
    return inv.filter((i) => i && i.wh === sel.name)
      .slice().sort((a, b) => num(b.stock) - num(a.stock)).slice(0, 5);
  }, [boot, geo, selKey]);

  _e(() => {
    if (!selectedZone) return;
    if (!matrixSlots.length) {
      if (slotSelKey != null) setSlotSelKey(null);
      return;
    }
    if (!matrixSlots.some((loc) => locationKeyOf(loc) === slotSelKey)) {
      setSlotSelKey(locationKeyOf(matrixSlots[0]));
    }
  }, [zoneSel, matrixSlotKeys]);

  _e(() => {
    if (!selectedZone) return;
    const onKey = (e) => {
      if (e.key === "Escape") closeZoneMatrix();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [zoneSel]);

  /* ── maplibre defer 加載:輪詢就緒,不就緒給重試/降級 ── */
  _e(() => {
    let alive = true, n = 0;
    const tick = () => {
      if (!alive) return;
      if (window.maplibregl) { setGlState("ok"); return; }
      if (++n > 24) { setGlState("none"); return; } // ~6s
      setTimeout(tick, 250);
    };
    tick();
    return () => { alive = false; };
  }, [glTry]);
  const retryGl = () => { setGlState("wait"); setGlTry((n) => n + 1); };

  /* ── 地圖初始化(glState=ok 且容器就緒) ── */
  _e(() => {
    if (glState !== "ok" || mapRef.current || !mapNode.current) return;
    if (!webglOk()) { setGlState("fail"); return; }
    const gl = window.maplibregl;
    let map;
    try {
      map = new gl.Map({
        container: mapNode.current, style: MAP_STYLE,
        center: MAP_CENTER, zoom: 3.6,
        attributionControl: { compact: true },
      });
    } catch (e) { setGlState("fail"); return; }
    map.addControl(new gl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new gl.ScaleControl({ unit: "metric" }), "bottom-left");
    /* 瓦片慢/字型缺失不上 console,只給一行溫和提示 */
    map.on("error", () => setTileSlow(true));
    map.on("styleimagemissing", (e) => {
      try { if (e && e.id && !map.hasImage(e.id)) map.addImage(e.id, { width: 1, height: 1, data: new Uint8Array(4) }); } catch (err) {}
    });
    /* 定位模式:點地圖取座標(經 ref 讀最新模式,避免閉包過期) */
    map.on("click", (e) => {
      if (!locateRef.current) return;
      setPick({ lat: +e.lngLat.lat.toFixed(6), lng: +e.lngLat.lng.toFixed(6) });
    });
    mapRef.current = map;
    setMapLive(true);
    setTimeout(() => { try { map.resize(); } catch (e) {} }, 90);
    return () => {
      try { map.remove(); } catch (e) {}
      mapRef.current = null; markersRef.current = []; pickMarkRef.current = null;
      setMapLive(false);
    };
  }, [glState]);

  /* ── 標記:方角墨底紙字小牌(倉庫名+容量%,>=90 紅底);只上已定位倉庫 ── */
  _e(() => {
    const gl = window.maplibregl, map = mapRef.current;
    if (!gl || !map || !mapLive) return;
    markersRef.current.forEach((m) => { try { m.mk.remove(); } catch (e) {} });
    markersRef.current = [];
    located.forEach((w) => {
      const cap = Number(w.capacity_usage);
      const hasCap = w.capacity_usage != null && Number.isFinite(cap);
      const hot = hasCap && cap >= 90;
      const el = document.createElement("button");
      el.type = "button";
      el.className = "w2gis-pin" + (hot ? " hot" : "");
      const tag = document.createElement("span"); tag.className = "p-tag";
      const nm = document.createElement("span"); nm.className = "p-name"; nm.textContent = w.name || "—";
      tag.appendChild(nm);
      if (hasCap) { const cp = document.createElement("span"); cp.className = "p-cap"; cp.textContent = Math.round(cap) + "%"; tag.appendChild(cp); }
      const stem = document.createElement("span"); stem.className = "p-stem";
      el.appendChild(tag); el.appendChild(stem);
      el.addEventListener("click", (ev) => {
        ev.stopPropagation(); // 別觸發地圖 click(定位模式取點)
        setSelKey(kOf(w));
        try { map.flyTo({ center: [+w.lng, +w.lat], zoom: Math.max(map.getZoom(), 9), duration: 600 }); } catch (e) {}
      });
      const mk = new gl.Marker({ element: el, anchor: "bottom" }).setLngLat([+w.lng, +w.lat]).addTo(map);
      markersRef.current.push({ key: kOf(w), el, mk });
    });
    /* 首次載入:一次性 fitBounds 到全部已定位倉庫 */
    if (located.length && !fitRef.current) {
      try {
        const b = new gl.LngLatBounds();
        located.forEach((w) => b.extend([+w.lng, +w.lat]));
        map.fitBounds(b, { padding: 90, maxZoom: 11, duration: 0 });
        fitRef.current = true;
      } catch (e) {}
    }
  }, [geo, mapLive]);

  /* 選中標記高亮 */
  _e(() => {
    markersRef.current.forEach((m) => m.el.classList.toggle("on", m.key === selKey));
  }, [selKey, geo, mapLive]);

  /* ── 定位模式開關 ── */
  _e(() => {
    locateRef.current = locate;
    const map = mapRef.current;
    if (map) { try { map.getCanvas().style.cursor = locate ? "crosshair" : ""; } catch (e) {} }
    if (!locate) setPick(null);
  }, [locate]);

  /* 取點標記(紅方塊) */
  _e(() => {
    const gl = window.maplibregl, map = mapRef.current;
    if (!gl || !map || !mapLive) return;
    if (!pick) {
      if (pickMarkRef.current) { try { pickMarkRef.current.remove(); } catch (e) {} pickMarkRef.current = null; }
      return;
    }
    if (!pickMarkRef.current) {
      const el = document.createElement("span");
      el.className = "w2gis-pick";
      pickMarkRef.current = new gl.Marker({ element: el, anchor: "center" }).setLngLat([pick.lng, pick.lat]).addTo(map);
    } else pickMarkRef.current.setLngLat([pick.lng, pick.lat]);
  }, [pick, mapLive]);

  const flyTo = (w) => {
    const map = mapRef.current;
    if (map && hasLL(w)) { try { map.flyTo({ center: [+w.lng, +w.lat], zoom: Math.max(map.getZoom(), 10), duration: 700 }); } catch (e) {} }
  };
  const enterLocate = (w) => { setLocate(w); setSelKey(kOf(w)); };
  /* 頁面不 POST:座標交秘書保存 */
  const sendLocate = () => {
    if (!locate || !pick) return;
    ask(t("把倉庫「{name}」的 GIS 定位設置為:緯度 {lat}、經度 {lng}(WGS-84 十進制),請確認無誤後保存",
      { name: locate.name || "—", lat: pick.lat.toFixed(6), lng: pick.lng.toFixed(6) }));
    setLocate(null);
  };

  const mapReady = glState === "ok";
  const degraded = glState === "none" || glState === "fail";

  return (
    <>
      <style>{GIS_CSS}</style>
      <Folio no="11" en="MAP / GIS" title={t("倉庫地圖")}
        sub={t("倉庫 GIS 定位 · 內置實景地圖 · 頁面只讀,定位與找貨交秘書")}
        right={<B kind="primary" icon="sparkle" onClick={() => ask(t("倉庫地圖上現在有什麼要處理的?哪些倉庫還沒定位、哪些庫區有風險?"))}>{t("問秘書")}</B>}/>

      <div className="kpi-band">
        <Kpi label={t("在管倉庫")} value={whs.length} unit={t("座")} delay={0}
          foot={<><span className="muted" style={{ fontSize: 11.5 }}>{t("庫存合計 {n}", { n: fq(stockTotal) })}</span><T tone="plain">GEO</T></>}/>
        <Kpi label={t("未定位倉庫")} value={unlocated} unit={t("座")} red={unlocated > 0} delay={.05}
          foot={unlocated > 0
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把還沒有 GIS 定位的倉庫列出來,逐個追問地址或經緯度後幫我保存定位"))}>{t("讓秘書定位 →")}</button>
            : <T tone="ok" dot>{t("全部已定位")}</T>}/>
        <Kpi label={t("庫區")} value={zones.length} unit={t("個")} delay={.1}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("共 {n} 個貨位", { n: totalRacks })}</span>}/>
        <Kpi label={t("風險庫區")} value={riskZones.length} unit={t("個")} red={riskZones.length > 0} delay={.15}
          foot={riskZones.length
            ? <button className="tag bad" style={{ cursor: "pointer" }} onClick={() => ask(t("分析有預警的庫區,按風險排序給我處置建議"))}>{t("交秘書處置")}</button>
            : <T tone="ok" dot>{t("無風險")}</T>}/>
      </div>

      {/* ═══ A · 實景地圖 ═══ */}
      <Band no="A" title={t("實景地圖")} delay={.08}
        sub={whs.length ? t("{a} 已定位 · {b} 未定位", { a: located.length, b: unlocated }) : ""}
        right={<span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".18em" }}>MAPLIBRE · OPENFREEMAP</span>}>

        {/* 定位模式:紅色提示條 */}
        {locate && (
          <div className="row spread wrap g10" style={{ background: "var(--red)", color: "#fff", padding: "10px 14px", marginBottom: 10 }}>
            <div className="row g10 wrap">
              <span className="label" style={{ color: "#fff" }}>{t("定位模式")}</span>
              <span style={{ fontSize: 13, fontWeight: 700 }}>{t("點擊地圖任意位置,為「{name}」選取座標", { name: locate.name || "—" })}</span>
            </div>
            <div className="row g8 wrap">
              {pick && (
                <span className="num" style={{ fontSize: 12.5, fontWeight: 700 }}>
                  {t("已選")} {pick.lat.toFixed(4)}, {pick.lng.toFixed(4)}
                </span>
              )}
              {pick && (
                <button onClick={sendLocate}
                  style={{ height: 28, padding: "0 12px", background: "#fff", color: "var(--red)", fontWeight: 700, fontSize: 12, border: "1px solid #fff" }}>
                  {t("交秘書定位到此處")}
                </button>
              )}
              <button onClick={() => setLocate(null)}
                style={{ height: 28, padding: "0 10px", background: "transparent", color: "#fff", fontWeight: 700, fontSize: 12, border: "1px solid #fff" }}>
                {t("退出定位")}
              </button>
            </div>
          </div>
        )}

        {/* 選未定位倉庫 → 進入定位模式 */}
        {!locate && mapLive && unlocatedList.length > 0 && (
          <div className="row g8 wrap" style={{ marginBottom: 12 }}>
            <span className="label dim">{t("定位模式")}</span>
            <span className="muted" style={{ fontSize: 11.5 }}>{t("選未定位倉庫進入定位模式:")}</span>
            {unlocatedList.slice(0, 6).map((w, i) => (
              <button key={kOf(w) + i} className="chip" onClick={() => enterLocate(w)}>
                <I name="scan" size={12}/>{w.name || "—"}
              </button>
            ))}
            {unlocatedList.length > 6 && <span className="muted num" style={{ fontSize: 11 }}>+{unlocatedList.length - 6}</span>}
          </div>
        )}

        <div className="row g20" style={{ alignItems: "stretch" }}>
          {/* 地圖容器:髮絲邊框 + 2px 墨頂規線 */}
          <div className="w2gis-wrap" style={{ flex: 1, minWidth: 0 }}>
            {mapReady ? (
              <div ref={mapNode} style={{ position: "absolute", inset: 0 }}/>
            ) : (
              <div className="col g10" style={{ position: "absolute", inset: 0, alignItems: "center", justifyContent: "center", padding: 24 }}>
                <I name={glState === "wait" ? "map" : "alert"} size={26} color="var(--ink-4)"/>
                {glState === "wait" ? (
                  <span className="muted" style={{ fontSize: 12.5 }}>{t("地圖組件載入中…")}</span>
                ) : (
                  <>
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{glState === "fail" ? t("此環境不支持 WebGL") : t("地圖組件尚未就緒")}</div>
                    <div className="muted" style={{ fontSize: 12, maxWidth: 380, textAlign: "center", lineHeight: 1.7 }}>
                      {glState === "fail" ? t("已自動降級為清單視圖,全部數據仍可在下方查看與交秘書處理。") : t("可能是網絡較慢或地圖庫尚未載入;下方清單與數據不受影響。")}
                    </div>
                    {glState === "none" && <B size="sm" icon="refresh" onClick={retryGl}>{t("重試")}</B>}
                  </>
                )}
              </div>
            )}
            {/* 空態:地圖照常初始化 + 引導文案 */}
            {mapLive && geo !== null && located.length === 0 && !locate && (
              <div className="col g6" style={{ position: "absolute", left: 14, top: 14, zIndex: 5, maxWidth: 300, background: "var(--white)", border: "1px solid var(--ink)", padding: "12px 14px" }}>
                <LB red>{t("地圖已就緒 · 尚無已定位倉庫")}</LB>
                <span className="muted" style={{ fontSize: 12, lineHeight: 1.7 }}>{t("在下方清單選一個倉庫進入定位模式,點地圖取得座標後交秘書保存。")}</span>
              </div>
            )}
          </div>

          {/* 右側抽屜:倉庫詳情 + 該倉庫存 Top + 秘書動作 */}
          {sel && (
            <aside className="drawer" style={{ position: "static", maxHeight: 480, overflowY: "auto" }}>
              <div className="row spread" style={{ padding: "14px 16px", borderBottom: "2px solid var(--rule)" }}>
                <div className="col g4">
                  <LB dim>WAREHOUSE</LB>
                  <div style={{ fontWeight: 800, fontSize: 17, letterSpacing: "-.02em" }}>{sel.name || "—"}</div>
                </div>
                <button className="btn ghost sm" style={{ padding: "0 8px" }} onClick={() => setSelKey(null)}><I name="x" size={13}/></button>
              </div>
              <div className="col g14" style={{ padding: 16 }}>
                <div className="row g6 wrap">
                  <T tone="plain">{sel.code || t("未編碼")}</T>
                  <T tone="plain">{sel.warehouse_type || t("未分類")}</T>
                  {sel.is_default ? <T tone="inv">{t("默認庫")}</T> : null}
                  {hasLL(sel) ? <T tone="ok" dot>{t("已定位")}</T> : <T tone="warn">{t("未定位")}</T>}
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", borderTop: "2px solid var(--rule)" }}>
                  <div className="col g4" style={{ padding: "10px 12px", borderBottom: "1px solid var(--hair-soft)", borderRight: "1px solid var(--hair-soft)" }}>
                    <LB dim>{t("物資種類")}</LB>
                    <span className="num" style={{ fontWeight: 700, fontSize: 17 }}>{num(sel.item_count)}</span>
                  </div>
                  <div className="col g4" style={{ padding: "10px 12px", borderBottom: "1px solid var(--hair-soft)" }}>
                    <LB dim>{t("庫存量")}</LB>
                    <span className="num" style={{ fontWeight: 700, fontSize: 17 }}>{fq(sel.stock_total)}</span>
                  </div>
                  <div className="col g4" style={{ padding: "10px 12px", borderBottom: "1px solid var(--hair-soft)", borderRight: "1px solid var(--hair-soft)" }}>
                    <LB dim>{t("容量使用")}</LB>
                    {(sel.capacity_usage != null && Number.isFinite(Number(sel.capacity_usage))) ? (
                      <span className="num" style={{ fontWeight: 700, fontSize: 17, color: capColor(Number(sel.capacity_usage)) }}>{Math.round(Number(sel.capacity_usage))}%</span>
                    ) : <span className="muted">—</span>}
                  </div>
                  <div className="col g4" style={{ padding: "10px 12px", borderBottom: "1px solid var(--hair-soft)" }}>
                    <LB dim>{t("座標")}</LB>
                    {hasLL(sel)
                      ? <span className="num" style={{ fontWeight: 700, fontSize: 12.5 }}>{Number(sel.lat).toFixed(4)}, {Number(sel.lng).toFixed(4)}</span>
                      : <span className="muted">—</span>}
                  </div>
                </div>
                {sel.address && <div className="muted" style={{ fontSize: 12, lineHeight: 1.6 }}>{sel.address}</div>}

                <div className="col g6">
                  <LB dim>{t("此倉庫存 Top")}</LB>
                  {topItems.length ? topItems.map((it, i) => (
                    <div key={(it.id != null ? it.id : i) + ":" + i} className="row g10" style={{ padding: "7px 0", borderBottom: "1px solid var(--hair-soft)" }}>
                      <span className="lr-idx">{pad2(i + 1)}</span>
                      <span style={{ flex: 1, fontSize: 12.5, fontWeight: 600, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>{it.name || "—"}</span>
                      <span className="num" style={{ fontWeight: 700, fontSize: 13 }}>{fq(it.stock)}</span>
                      <span className="muted" style={{ fontSize: 11 }}>{it.unit || ""}</span>
                    </div>
                  )) : <span className="muted" style={{ fontSize: 12 }}>{t("此倉庫暫無庫存記錄")}</span>}
                </div>

                <div className="row g6 wrap">
                  <B size="sm" icon="sparkle" onClick={() => ask(t("倉庫「{name}」現在的物資、庫存和預警情況怎麼樣?", { name: sel.name || "—" }))}>{t("問情況")}</B>
                  <B size="sm" icon="swap" onClick={() => ask(t("我要從倉庫「{name}」調撥物資到其他倉庫,請追問物資、數量和目標倉庫後辦理", { name: sel.name || "—" }))}>{t("調撥")}</B>
                  <B size="sm" icon="clipboard" onClick={() => ask(t("幫我為倉庫「{name}」安排一次盤點,請追問盤點範圍後辦理", { name: sel.name || "—" }))}>{t("盤點")}</B>
                </div>
                {!hasLL(sel) && mapLive && (
                  <B kind="red" size="sm" icon="scan" onClick={() => enterLocate(sel)}>{t("在地圖上定位")}</B>
                )}
              </div>
            </aside>
          )}
        </div>
        {tileSlow && !degraded && (
          <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>{t("地圖瓦片加載較慢或失敗,不影響清單與秘書操作。")}</div>
        )}
      </Band>

      {/* ═══ B · 倉庫清單(行點擊 → 地圖 flyTo) ═══ */}
      <Band no="B" title={t("倉庫清單")} sub={whs.length ? t("{n} 座 · 同一後端實時", { n: whs.length }) : ""} delay={.12}
        right={<B size="sm" icon="plus" onClick={() => ask(t("幫我登記一個新倉庫,請追問名稱、類型和地址後辦理"))}>{t("登記倉庫")}</B>}>
        {stack.length > 1 && (
          <div className="col g10" style={{ marginBottom: 20 }}>
            <LB dim>{t("庫存分佈")}</LB>
            <StackBar data={stack}/>
            <div className="row g16 wrap" style={{ fontSize: 11.5 }}>
              {stack.map((d) => (
                <span key={d.label} className="row g6">
                  <span style={{ width: 9, height: 9, background: d.color, flexShrink: 0 }}/>
                  <span className="ink2">{d.label}</span>
                  <span className="num" style={{ fontWeight: 700 }}>{fq(d.value)}</span>
                </span>
              ))}
            </div>
          </div>
        )}
        {whs.length ? (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th style={{ width: 40 }}>#</th><th>{t("倉庫")}</th><th>{t("編碼 / 類型")}</th><th>{t("地址")}</th>
                <th>{t("物資 / 庫存")}</th><th>{t("容量")}</th><th>{t("定位")}</th><th style={{ width: 96 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {whs.map((w, i) => {
                  const hasGeo = hasLL(w);
                  const cap = Number(w.capacity_usage);
                  const hasCap = w.capacity_usage != null && Number.isFinite(cap);
                  return (
                    <tr key={kOf(w) + ":" + i} className={selKey === kOf(w) ? "on" : ""} style={{ cursor: "pointer" }}
                      onClick={() => { setSelKey(kOf(w)); flyTo(w); }}>
                      <td className="num muted">{pad2(i + 1)}</td>
                      <td>
                        <span className="row g8" style={{ fontWeight: 650 }}>
                          {w.name || "—"}{w.is_default ? <T tone="inv">{t("默認庫")}</T> : null}
                        </span>
                      </td>
                      <td>
                        <div className="col g4">
                          <span className="num" style={{ fontWeight: 600 }}>{w.code || "—"}</span>
                          <span className="muted" style={{ fontSize: 11 }}>{w.warehouse_type || t("未分類")}</span>
                        </div>
                      </td>
                      <td className="muted" style={{ fontSize: 12.5 }}>
                        <span style={{ display: "block", maxWidth: 220, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={w.address || ""}>{w.address || "—"}</span>
                      </td>
                      <td>
                        <span className="num" style={{ fontWeight: 700, fontSize: 15 }}>{num(w.item_count)}</span>
                        <span className="muted" style={{ fontSize: 11.5 }}> {t("種")}</span>
                        <span className="num muted" style={{ fontSize: 11.5 }}> · {fq(w.stock_total)}</span>
                      </td>
                      <td>
                        {hasCap ? (
                          <>
                            <span className="num" style={{ fontWeight: 700, color: capColor(cap) }}>{Math.round(cap)}%</span>
                            <div className="bar" style={{ width: 76, marginTop: 5 }}>
                              <i style={{ width: Math.min(100, Math.max(0, cap)) + "%", background: capColor(cap) }}/>
                            </div>
                          </>
                        ) : <span className="muted">—</span>}
                      </td>
                      <td>
                        {hasGeo ? (
                          <div className="col g4">
                            <T tone="ok" dot>{t("已定位")}</T>
                            <span className="num muted" style={{ fontSize: 10.5 }}>{Number(w.lat).toFixed(4)}, {Number(w.lng).toFixed(4)}</span>
                          </div>
                        ) : <T tone="warn">{t("未定位")}</T>}
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div className="row g4">
                          {hasGeo ? (
                            <button className="btn sm" title={t("飛到此倉庫")} style={{ padding: "0 8px" }}
                              onClick={() => { setSelKey(kOf(w)); flyTo(w); }}><I name="map" size={12}/></button>
                          ) : (
                            <button className="btn sm" title={t("進入定位模式")} style={{ padding: "0 8px", borderColor: "var(--red)", color: "var(--red)" }}
                              disabled={!mapLive}
                              onClick={() => enterLocate(w)}><I name="scan" size={12}/></button>
                          )}
                          <button className="btn sm" title={t("問秘書")} style={{ padding: "0 8px" }}
                            onClick={() => ask(t("倉庫「{name}」現在的物資、庫存和預警情況怎麼樣?", { name: w.name || "—" }))}><I name="sparkle" size={12}/></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : geo === null ? (
          <div className="muted" style={{ padding: "28px 0", fontSize: 12.5 }}>{t("載入中…")}</div>
        ) : (
          <EM icon="map" title={t("還沒有倉庫資料")} sub={t("對秘書說「幫我登記一個倉庫」,登記後即可在地圖上定位。")}
            action={<B size="sm" icon="sparkle" onClick={() => ask(t("幫我登記一個新倉庫,請追問名稱、類型和地址後辦理"))}>{t("登記倉庫")}</B>}/>
        )}
      </Band>

      {/* ═══ C · 庫區與貨位 ═══ */}
      <Band no="C" title={t("庫區與貨位")} sub={zones.length ? t("{z} 個庫區 · {r} 個貨位", { z: zones.length, r: totalRacks }) : ""} delay={.16}
        right={<B size="sm" icon="search" onClick={() => ask(t("幫我找物資的存放位置,請追問物資名稱後告訴我它在哪個倉庫、哪個庫位"))}>{t("找物資位置")}</B>}>
        {zones.length ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(230px, 1fr))", borderTop: "2px solid var(--rule)" }}>
            {zones.map((z, i) => {
              const live = locationsForZone(locations, z);
              const cap = zoneCapacity(z, live);
              const capValue = cap == null ? 0 : Math.round(cap);
              const alert = zoneRiskCount(z, live);
              const racks = Math.max(zoneRackCount(z), live.length);
              return (
                <article key={zoneKeyOf(z) + ":" + i} className="w2zone-card">
                  <button type="button" className="w2zone-card-hit" aria-haspopup="dialog"
                    title={t("點擊查看 Swiss 庫位矩陣")} onClick={(e) => openZoneMatrix(z, e.currentTarget)}>
                    <div className="row spread">
                      <span className="mono" style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-.02em" }}>{zoneCodeOf(z)}</span>
                      {alert > 0 ? <T tone="bad" dot>{t("{n} 風險", { n: alert })}</T> : <T tone="ok" dot>{t("正常")}</T>}
                    </div>
                    <div style={{ fontWeight: 650, fontSize: 13.5, lineHeight: 1.3 }}>{zoneNameOf(z)}</div>
                    <div className="muted num" style={{ fontSize: 11.5 }}>{t("{r} 貨位 · {i} 種", { r: racks, i: zoneItemCount(z) })}</div>
                    <div className="row g8">
                      <div className="bar" style={{ flex: 1 }}><i style={{ width: Math.min(100, capValue) + "%", background: capColor(capValue) }}/></div>
                      <span className="num muted" style={{ fontSize: 11 }}>{cap == null ? "—" : capValue + "%"}</span>
                    </div>
                    <span className="w2zone-open">{t("點擊查看 Swiss 庫位矩陣")}</span>
                  </button>
                  <div className="w2zone-card-foot">
                    <B size="sm" icon="sparkle" style={{ justifyContent: "flex-start" }}
                      onClick={() => ask(t("庫區「{name}」({id})現在存了哪些物資?有沒有低庫存或風險?", { name: zoneNameOf(z), id: zoneCodeOf(z) }))}>{t("問這個庫區")}</B>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <EM icon="layers" title={t("還沒有庫區資料")} sub={t("對秘書說「幫我從庫存整理生成庫區與貨位」。")}
            action={<B size="sm" icon="sparkle" onClick={() => ask(t("幫我從現有庫存資料自動整理生成庫區和貨位"))}>{t("讓秘書整理庫位")}</B>}/>
        )}
        <div className="row g8" style={{ marginTop: 18 }}>
          <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".18em" }}>GIS LIVE · MAPLIBRE BUILT-IN</span>
          <span className="muted" style={{ fontSize: 11 }}>{t("內置實景地圖已啟用;點標記看詳情,定位與改動交秘書執行。")}</span>
        </div>
      </Band>

      {selectedZone && (
        <ZoneMatrixDialog zone={selectedZone} slots={matrixSlots} selectedKey={slotSelKey}
          overviewState={overviewState} onSelect={setSlotSelKey} onClose={closeZoneMatrix}/>
      )}
    </>
  );
};

window.W2.PAGES["gis"] = PageGis;
})();
