/* ============================================================
   2 · 庫存管理 — 卡片/表格 + 滑出詳情面板
   ============================================================ */
const { useState: useStateInv, useEffect: useEffectInv } = React;

const invNumber = (value) => {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
};

const invQty = (value) => {
  const n = invNumber(value);
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, "");
};

const invDelta = (value, unit) => {
  const n = invNumber(value);
  return `${n > 0 ? "+" : ""}${invQty(n)}${unit || ""}`;
};

const invAutoCodeLike = (value) => /^WZ-\d{4,}$/i.test(String(value || "").trim());
const invModelText = (item) => {
  const model = String(item?.model || "").trim();
  if (!model || model === "—" || invAutoCodeLike(model)) return "—";
  return model;
};

const INV_LEVEL_COLOR = { red: "#EF4444", orange: "#F59E0B", yellow: "#EAB308", blue: "#3B82F6" };

const PageInventory = ({ go } = {}) => {
  const [sel, setSel] = useStateInv(null);
  const [cat, setCat] = useStateInv("全部");
  const [q, setQ] = useStateInv("");
  const [alertMap, setAlertMap] = useStateInv({});
  const [showCreate, setShowCreate] = useStateInv(false);
  const [showWhMgr, setShowWhMgr] = useStateInv(false);
  const [showFilter, setShowFilter] = useStateInv(false);
  const [showCatMgr, setShowCatMgr] = useStateInv(false);
  const [stockScope, setStockScope] = useStateInv("available");
  const [filter, setFilter] = useStateInv({ wh: "全部", lowOnly: false, criticalOnly: false, alertsOnly: false });
  useEffectInv(() => {
    (window.authFetch || fetch)(`${INV_API_BASE}/api/alerts/by-item`)
      .then(r => r.ok ? r.json() : null).then(d => { if (d && d.byItem) setAlertMap(d.byItem); }).catch(() => {});
    if (window.INVENTORY_FOCUS) {
      const name = window.INVENTORY_FOCUS; window.INVENTORY_FOCUS = null;
      setQ(name);
      const hit = (window.INVENTORY || []).find(i => i.name === name);
      if (hit) setSel(hit);
    }
  }, []);
  const openItemAlerts = (it) => { window.ALERTS_FOCUS_KEYWORD = it.name; if (go) go("alerts"); };
  // 主組織維度 = 功能分類(用戶自定義:工具/消耗品/可歸還…),取代原來的備件大類
  const funcCats = window.LEDGER_CATEGORIES || [];
  const whOptions = ["全部", ...Array.from(new Set((window.INVENTORY || []).map(i => i.wh).filter(w => w && w !== "—")))];
  const filterActive = filter.wh !== "全部" || filter.lowOnly || filter.criticalOnly || filter.alertsOnly;

  const allInventory = window.INVENTORY || [];
  const availableCount = allInventory.filter(i => invNumber(i.stock) > 0).length;
  const zeroCount = allInventory.filter(i => invNumber(i.stock) <= 0).length;
  let list = allInventory;
  if (stockScope === "available") list = list.filter(i => invNumber(i.stock) > 0);
  if (stockScope === "zero") list = list.filter(i => invNumber(i.stock) <= 0);
  if (cat !== "全部") list = list.filter(i => i.categoryId === cat);
  if (q) list = list.filter(i => (i.name + i.code + invModelText(i)).toLowerCase().includes(q.toLowerCase()));
  if (filter.wh !== "全部") list = list.filter(i => i.wh === filter.wh);
  if (filter.lowOnly) list = list.filter(i => Number(i.stock) < Number(i.safe));
  if (filter.criticalOnly) list = list.filter(i => i.critical);
  if (filter.alertsOnly) list = list.filter(i => alertMap[i.itemId]);

  return (
    <div style={{ display: "flex", gap: 20 }}>
      <div className="col gap-18" style={{ flex: 1, minWidth: 0 }}>
        <PageHead title="庫存管理" sub={`可用 ${availableCount} 種 · 零庫存 ${zeroCount} 種 · 按分類組織`}
          actions={<>
            <button className="btn btn-sm" onClick={() => setShowFilter(v => !v)} style={filterActive ? { background: "var(--blue-soft)", color: "var(--blue)" } : undefined}><Icon name="filter" size={15}/>篩選{filterActive ? " ●" : ""}</button>
            <button className="btn btn-sm" onClick={() => setShowCatMgr(true)}><Icon name="layers" size={15}/>管理分類</button>
            <button className="btn btn-sm" onClick={() => setShowWhMgr(true)}><Icon name="map2" size={15}/>倉庫管理</button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}><Icon name="plus" size={15}/>新增物資</button>
          </>}/>
        {showCreate && <CreateItemModal onClose={() => setShowCreate(false)}/>}
        {showWhMgr && <WarehouseManageModal onClose={() => setShowWhMgr(false)}/>}
        {showCatMgr && <CategoryQuickManage cats={funcCats} onClose={() => setShowCatMgr(false)}/>}

        {showFilter && (
          <div className="card fade-up" style={{ padding: 16 }}>
            <div className="row gap-16" style={{ flexWrap: "wrap", alignItems: "center" }}>
              <label className="row gap-8" style={{ fontSize: 12.5, fontWeight: 700, alignItems: "center" }}>倉庫
                <select className="input" style={{ width: 180, height: 34 }} value={filter.wh} onChange={(e) => setFilter({ ...filter, wh: e.target.value })}>
                  {whOptions.map(w => <option key={w} value={w}>{w}</option>)}
                </select></label>
              <label className="row gap-8" style={{ fontSize: 13, fontWeight: 700, alignItems: "center", cursor: "pointer" }}>
                <input type="checkbox" checked={filter.lowOnly} onChange={(e) => setFilter({ ...filter, lowOnly: e.target.checked })}/>僅顯示低於安全庫存</label>
              <label className="row gap-8" style={{ fontSize: 13, fontWeight: 700, alignItems: "center", cursor: "pointer" }}>
                <input type="checkbox" checked={filter.criticalOnly} onChange={(e) => setFilter({ ...filter, criticalOnly: e.target.checked })}/>僅顯示關鍵物資</label>
              <label className="row gap-8" style={{ fontSize: 13, fontWeight: 700, alignItems: "center", cursor: "pointer" }}>
                <input type="checkbox" checked={filter.alertsOnly} onChange={(e) => setFilter({ ...filter, alertsOnly: e.target.checked })}/>只看有預警</label>
              <button className="btn btn-sm" style={{ marginLeft: "auto" }} onClick={() => setFilter({ wh: "全部", lowOnly: false, criticalOnly: false, alertsOnly: false })}>清除篩選</button>
            </div>
          </div>
        )}

        {/* 搜索 + 分類 */}
        <div className="card fade-up" style={{ padding: 16 }}>
          <div style={{ position: "relative", marginBottom: 14 }}>
            <Icon name="search" size={17} color="var(--ink-4)" style={{ position: "absolute", left: 14, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="input" value={q} onChange={e => setQ(e.target.value)} placeholder="搜索物資名稱、編碼、型號…" style={{ paddingLeft: 42, background: "var(--surface-2)" }}/>
          </div>
          <div className="row gap-8" style={{ flexWrap: "wrap" }}>
            {[
              ["available", "有庫存", availableCount],
              ["zero", "零庫存", zeroCount],
              ["all", "全庫存", allInventory.length],
            ].map(([id, label, count]) => (
              <button key={id} onClick={() => setStockScope(id)} className="badge" style={{
                height: 30, cursor: "pointer", fontWeight: 700,
                color: stockScope === id ? "#fff" : "var(--ink-3)",
                background: stockScope === id ? "var(--ink)" : "var(--surface)",
                border: stockScope === id ? "none" : "1px solid var(--line)" }}>{label} <span className="num">{count}</span></button>
            ))}
            <button onClick={() => setCat("全部")} className="badge" style={{
              height: 30, cursor: "pointer", fontWeight: 600,
              color: cat === "全部" ? "#fff" : "var(--ink-3)",
              background: cat === "全部" ? "var(--grad)" : "var(--surface-2)",
              border: cat === "全部" ? "none" : "1px solid var(--line)" }}>全部</button>
            {funcCats.map(c => (
              <button key={c.id} onClick={() => setCat(c.id)} className="badge row gap-4" style={{
                height: 30, cursor: "pointer", fontWeight: 600, alignItems: "center",
                color: cat === c.id ? "#fff" : "var(--ink-3)",
                background: cat === c.id ? "var(--grad)" : "var(--surface-2)",
                border: cat === c.id ? "none" : "1px solid var(--line)" }}>
                {c.name}{c.requires_return ? <Icon name="swap" size={12}/> : null}</button>
            ))}
            {funcCats.length === 0 && <span className="muted" style={{ fontSize: 12.5 }}>尚未設置分類 —— 點右上「管理分類」新增</span>}
          </div>
        </div>

        {/* 列表 */}
        <div className="card fade-up" style={{ padding: 0, overflow: "hidden", animationDelay: ".08s" }}>
          <table className="tbl">
            <thead><tr>
              <th>物資</th><th>編碼 / 型號</th><th>分類</th><th>庫存 / 安全</th><th>庫位</th><th>狀態</th><th>預警</th>
            </tr></thead>
            <tbody>
              {list.map((it, idx) => (
                <tr key={`${it.id}-${idx}`} onClick={() => setSel(it)} style={{ cursor: "pointer", background: sel?.id === it.id ? "var(--blue-soft)" : undefined }}>
                  <td>
                    <div className="row gap-10">
                      <div style={{ width: 30, height: 30, borderRadius: 8, background: it.critical ? "var(--danger-soft)" : "var(--grad-soft)", color: it.critical ? "var(--danger)" : "var(--blue)", display: "grid", placeItems: "center", flexShrink: 0 }}>
                        <Icon name={it.critical ? "flame" : "pkg"} size={15}/>
                      </div>
                      <div className="col gap-2">
                        <span style={{ fontWeight: 600, color: "var(--ink)" }}>{it.name}</span>
                        {it.critical && <span style={{ fontSize: 10.5, color: "var(--danger)", fontWeight: 700 }}>搶修必備</span>}
                      </div>
                    </div>
                  </td>
                  <td><div className="col gap-2"><span className="num" style={{ fontWeight: 600 }}>{it.code}</span><span className="num muted" style={{ fontSize: 12 }}>{invModelText(it)}</span></div></td>
                  <td className="muted">
                    <div className="row gap-6" style={{ alignItems: "center" }}>
                      <span>{it.category || it.cat}</span>
                      {it.requiresReturn && <span className="badge badge-info" style={{ height: 18, fontSize: 10 }}>借還</span>}
                    </div>
                  </td>
                  <td>
                    <span className="num" style={{ fontWeight: 700, color: it.stock < it.safe ? "var(--danger)" : "var(--ink)" }}>{it.stock}</span>
                    <span className="num muted"> / {it.safe} {it.unit}</span>
                    <div style={{ width: 64, height: 4, borderRadius: 2, background: "#EEF2F7", marginTop: 4, overflow: "hidden" }}>
                      <div style={{ height: "100%", width: Math.min(100, it.safe ? it.stock/it.safe*100 : 0) + "%", background: it.stock < it.safe ? "var(--danger)" : "var(--ok)" }}/>
                    </div>
                  </td>
                  <td><span className="num badge badge-gray">{it.loc}</span></td>
                  <td>{invNumber(it.stock) <= 0 ? <span className="badge badge-gray"><span className="dot"/>零庫存</span> : <StatusBadge s={it.status}/>}</td>
                  <td>
                    {alertMap[it.itemId]
                      ? <span className="inv-alert-badge" style={{ background: INV_LEVEL_COLOR[alertMap[it.itemId].level] || "#F59E0B" }}
                          title="查看該物資預警" onClick={(e) => { e.stopPropagation(); openItemAlerts(it); }}>
                          <Icon name="alert" size={11} color="#fff"/>{alertMap[it.itemId].count}
                        </span>
                      : <span className="muted" style={{ fontSize: 11 }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!list.length && (
          <div className="card fade-up center" style={{ padding: 28, color: "var(--ink-3)", fontSize: 13 }}>
            {stockScope === "available" ? "暫無可用庫存。已出庫或耗盡的物資可切到「零庫存」查看歷史檔案。" : "當前篩選下沒有物資。"}
          </div>
        )}
      </div>

      {/* 詳情面板 */}
      {sel && <InvDetail item={sel} onClose={() => setSel(null)}/>}
    </div>
  );
};

const InvDetail = ({ item, onClose }) => {
  const trend = Array.isArray(item.stockTrend) ? item.stockTrend : [];
  const curve = trend.length ? trend.map(p => invNumber(p.stock)) : Array(7).fill(invNumber(item.stock));
  const trendStart = trend[0]?.label || "—";
  const trendEnd = trend[trend.length - 1]?.label || "當前";
  const recentMovements = Array.isArray(item.recentMovements) ? item.recentMovements : [];
  const relatedTargets = Array.isArray(item.relatedTargets) ? item.relatedTargets : [];
  const need = Math.max(0, item.safe - item.stock + Math.ceil(item.safe * 0.3));
  const [repBusy, setRepBusy] = useStateInv(false);
  const [repMsg, setRepMsg] = useStateInv("");
  const requestReplenish = () => {
    if (repBusy) return;
    setRepBusy(true); setRepMsg("");
    (window.authFetch || fetch)(`${INV_API_BASE}/api/replenishment`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item_name: item.name, need, unit: item.unit, stock: item.stock, safe: item.safe }),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "生成失敗"); setRepMsg(d.message || "申請已生成"); if (window.reloadData) window.reloadData(); })
      .catch((e) => setRepMsg("⚠ " + (e.message || String(e)))).finally(() => setRepBusy(false));
  };
  return (
    <div className="card fade-up" style={{ width: 360, flexShrink: 0, padding: 0, alignSelf: "flex-start", position: "sticky", top: 0, overflow: "hidden", animation: "fadeUp .35s ease both" }}>
      {/* 頭 */}
      <div style={{ padding: 20, background: item.critical ? "linear-gradient(135deg,#FFF1F1,#FFF8F2)" : "var(--grad-soft)", borderBottom: "1px solid var(--line)" }}>
        <div className="row spread" style={{ marginBottom: 14 }}>
          <StatusBadge s={item.status}/>
          <button onClick={onClose} style={{ width: 30, height: 30, borderRadius: 9, display: "grid", placeItems: "center", background: "rgba(255,255,255,0.7)" }}><Icon name="x" size={16} color="var(--ink-3)"/></button>
        </div>
        <div style={{ fontSize: 18, fontWeight: 700, lineHeight: 1.3 }}>{item.name}</div>
        <div className="num muted" style={{ fontSize: 12.5, marginTop: 6 }}>{item.code}{invModelText(item) !== "—" ? ` · ${invModelText(item)}` : ""}</div>
        {item.critical && <div className="row gap-6" style={{ marginTop: 10, fontSize: 12, color: "var(--danger)", fontWeight: 700 }}><Icon name="flame" size={14}/>搶修必備物資 · 關鍵備件</div>}
      </div>

      <div className="scroll-y" style={{ padding: 20, maxHeight: "calc(100vh - 220px)" }}>
        {/* 基本信息 */}
        <div className="eyebrow" style={{ marginBottom: 10 }}>基本信息</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
          {[["當前庫存", `${item.stock} ${item.unit}`], ["安全庫存", `${item.safe} ${item.unit}`], ["存放位置", item.loc], ["所屬倉庫", item.wh], ["供應商", item.supplier], ["單價", "¥" + item.price.toLocaleString()]].map(([k,v],i) => (
            <div key={i} className="col gap-2"><span style={{ fontSize: 11.5, color: "var(--ink-4)" }}>{k}</span><span className="num" style={{ fontSize: 13.5, fontWeight: 600 }}>{v}</span></div>
          ))}
        </div>

        {/* 庫存曲線 */}
        <div className="eyebrow" style={{ marginBottom: 10 }}>近 7 月庫存趨勢</div>
        <div style={{ padding: 14, borderRadius: 12, background: "var(--surface-2)", marginBottom: 20 }}>
          <Spark points={curve} w={300} h={56} color={item.status==="danger"?"var(--danger)":"var(--blue)"}/>
          <div className="row spread" style={{ marginTop: 6, fontSize: 11, color: "var(--ink-4)" }}><span>{trendStart}</span><span>{trendEnd} {item.stock}{item.unit}</span></div>
        </div>

        {/* 補貨建議 */}
        {item.stock < item.safe && (
          <div style={{ padding: 14, borderRadius: 12, background: "var(--blue-soft)", border: "1px solid rgba(27,107,255,0.16)", marginBottom: 20 }}>
            <div className="row gap-8" style={{ marginBottom: 8 }}><Icon name="sparkle" size={16} color="var(--blue)"/><span style={{ fontSize: 13, fontWeight: 700, color: "var(--blue)" }}>AI 補貨建議</span></div>
            <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.6 }}>低於安全庫存，建議補貨 <b className="num">{need} {item.unit}</b>。請結合實際供應商、可調撥倉庫和使用計劃確認。</div>
            <button className="btn btn-primary btn-sm" style={{ width: "100%", marginTop: 12 }} disabled={repBusy} onClick={requestReplenish}><Icon name="swap" size={14}/>{repBusy ? "生成中…" : "生成補貨/調撥申請"}</button>
            {repMsg && <div style={{ fontSize: 12, fontWeight: 700, marginTop: 8, color: repMsg.startsWith("⚠") ? "var(--danger)" : "var(--ok)" }}>{repMsg}</div>}
          </div>
        )}

        {/* 最近領用 */}
        <div className="eyebrow" style={{ marginBottom: 10 }}>最近領用記錄</div>
        <div className="col gap-8" style={{ marginBottom: 20 }}>
          {recentMovements.length ? recentMovements.map((r,i) => (
            <div key={`${r.date}-${i}`} className="row spread" style={{ fontSize: 12.5, gap: 12 }}>
              <span style={{ color: "var(--ink-2)", fontWeight: 500, minWidth: 0 }}>{r.actor || r.label || "—"} · {r.target || r.label || "—"}</span>
              <span className="num" style={{ fontWeight: 700, color: invNumber(r.delta) < 0 ? "var(--danger)" : "var(--ok)", flexShrink: 0 }}>{invDelta(r.delta, r.unit)} <span className="muted" style={{ fontWeight: 400 }}>{r.date || "—"}</span></span>
            </div>
          )) : <div className="muted" style={{ fontSize: 12.5 }}>暫無真實流水記錄</div>}
        </div>

        {/* 關聯設備 */}
        <div className="eyebrow" style={{ marginBottom: 10 }}>關聯設備 / 線路</div>
        <div className="row gap-8" style={{ flexWrap: "wrap" }}>
          {relatedTargets.length ? relatedTargets.map(t => <span key={t} className="badge badge-info">{t}</span>) : <span className="muted" style={{ fontSize: 12.5 }}>暫無真實關聯</span>}
        </div>
      </div>
    </div>
  );
};

const INV_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const CreateItemModal = ({ onClose }) => {
  const ledgerCats = window.LEDGER_CATEGORIES || [];
  const [f, setF] = useStateInv({
    category_id: (ledgerCats[0] || {}).id || "",
    item_name: "", spec_model: "", unit: "件",
    initial_stock: "", safe_quantity: "",
    warehouse: (window.WAREHOUSES && window.WAREHOUSES[0] !== "—" ? window.WAREHOUSES[0] : "") || "",
  });
  const [busy, setBusy] = useStateInv(false);
  const [error, setError] = useStateInv("");
  const [result, setResult] = useStateInv(null);
  const [classifying, setClassifying] = useStateInv(false);
  const [catHint, setCatHint] = useStateInv(null);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  // AI 自動分類:物資名稱 → 從現有分類裡選最合適的(填好下拉,可手動改)
  const classify = () => {
    const nm = (f.item_name || "").trim();
    if (!nm || classifying) return;
    setClassifying(true); setCatHint(null);
    (window.authFetch || fetch)(`${INV_API_BASE}/api/items/classify`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: nm, spec: f.spec_model || "" }),
    }).then((r) => r.json()).then((d) => {
      if (d.category_id) { setF((prev) => ({ ...prev, category_id: d.category_id })); setCatHint({ name: d.category_name, reason: d.reason, ai: d.ai }); }
      else setCatHint({ none: true, reason: d.reason });
    }).catch(() => {}).finally(() => setClassifying(false));
  };
  const submit = () => {
    if (!f.category_id) { setError("請選擇分類"); return; }
    if (!f.item_name.trim()) { setError("請填寫物資名稱"); return; }
    setBusy(true); setError("");
    const body = { category_id: f.category_id, item_name: f.item_name.trim(), spec_model: f.spec_model || null, unit: f.unit || "件" };
    if (f.initial_stock !== "") { body.initial_stock = Number(f.initial_stock); body.warehouse = f.warehouse || null; }
    if (f.safe_quantity !== "") body.safe_quantity = Number(f.safe_quantity);
    (window.authFetch || fetch)(`${INV_API_BASE}/api/items`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "新增失敗"); setResult(d); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <div className="card col gap-14" style={{ width: "min(500px, 100%)", padding: 24, maxHeight: "86vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>新增物資</div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {result ? (
          <>
            <div className="col center" style={{ gap: 10, padding: "16px 0" }}>
              <div style={{ width: 56, height: 56, borderRadius: "50%", background: "var(--ok-soft)", display: "grid", placeItems: "center" }}><Icon name="check" size={28} color="var(--ok)" sw={2.4}/></div>
              <div style={{ fontSize: 15, fontWeight: 700 }}>物資已新增</div>
              <div className="muted" style={{ fontSize: 13 }}>{result.item_name} · 已寫入主數據</div>
            </div>
            <button className="btn btn-primary" onClick={onClose} style={{ height: 42 }}>完成</button>
          </>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>
                <span className="row spread" style={{ alignItems: "center" }}>分類
                  <button type="button" className="btn" disabled={classifying || !(f.item_name || "").trim()} onClick={classify} style={{ height: 20, padding: "0 7px", fontSize: 11 }}>{classifying ? "AI 分類中…" : "✨ AI 分類"}</button>
                </span>
                <select className="input" value={f.category_id} onChange={(e) => { setCatHint(null); up("category_id")(e); }}>
                  {ledgerCats.length === 0 && <option value="">（無分類,請先在設置新增）</option>}
                  {ledgerCats.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
                {catHint && <span style={{ fontSize: 11, color: catHint.none ? "var(--warn)" : "var(--blue)" }}>{catHint.none ? `AI 未能歸類:${catHint.reason || "請手動選擇"}` : `${catHint.ai ? "🤖 AI 已歸類" : "已匹配"}:${catHint.name}${catHint.reason ? ` · ${catHint.reason}` : ""}`}</span>}
              </label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>單位
                <input className="input" value={f.unit} onChange={up("unit")}/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700, gridColumn: "1 / -1" }}>物資名稱
                <input className="input" value={f.item_name} onChange={up("item_name")} onBlur={classify} placeholder="例如:電鑽 / 接地線成套(輸入後自動歸類)"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700, gridColumn: "1 / -1" }}>規格型號
                <input className="input" value={f.spec_model} onChange={up("spec_model")} placeholder="可選"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>初始庫存
                <input className="input" type="number" min="0" value={f.initial_stock} onChange={up("initial_stock")} placeholder="可選"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>安全庫存
                <input className="input" type="number" min="0" value={f.safe_quantity} onChange={up("safe_quantity")} placeholder="可選"/></label>
              {f.initial_stock !== "" && (
                <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700, gridColumn: "1 / -1" }}>入庫倉庫
                  <input className="input" value={f.warehouse} onChange={up("warehouse")} placeholder="倉庫名稱"/></label>
              )}
            </div>
            {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
            <div className="row gap-8">
              <button className="btn btn-primary" onClick={submit} disabled={busy} style={{ flex: 1, height: 42 }}>{busy ? "新增中…" : "新增物資"}</button>
              <button className="btn" onClick={onClose} style={{ height: 42 }}>取消</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const INV_WH_TYPES = ["中心庫", "搶修庫", "分庫", "週轉庫", "備件庫", "冷庫", "危化品庫", "其他"];

const WarehouseManageModal = ({ onClose }) => {
  const [list, setList] = useStateInv([]);
  const [loading, setLoading] = useStateInv(true);
  const [edit, setEdit] = useStateInv(null); // null | {} (新增) | row(編輯)
  const [busy, setBusy] = useStateInv(false);
  const [error, setError] = useStateInv("");

  const load = () => {
    setLoading(true); setError("");
    (window.authFetch || fetch)(`${INV_API_BASE}/api/warehouses/geo`)
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "載入失敗"); setList(d.warehouses || []); })
      .catch((e) => setError(e.message || String(e))).finally(() => setLoading(false));
  };
  useEffectInv(() => { load(); }, []);

  const save = () => {
    if (!edit.name || !edit.name.trim()) { setError("請填寫倉庫名稱"); return; }
    setBusy(true); setError("");
    const body = { name: edit.name.trim(), code: edit.code || null, warehouse_type: edit.warehouse_type || null, capacity_usage: edit.capacity_usage === "" || edit.capacity_usage == null ? null : Number(edit.capacity_usage) };
    const path = edit.id ? `/api/warehouses/${edit.id}` : "/api/warehouses";
    (window.authFetch || fetch)(`${INV_API_BASE}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "保存失敗"); setEdit(null); load(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };

  const remove = (w) => {
    if (busy) return;
    if (w.can_delete === false) { setError(w.delete_hint || "默認倉庫不能刪除"); return; }
    if (!window.confirm(`刪除倉庫「${w.name}」?\n${w.delete_hint || "無關聯數據將直接刪除;若有庫存/被引用則改為停用(從列表與地圖隱藏)。"}`)) return;
    setBusy(true); setError("");
    (window.authFetch || fetch)(`${INV_API_BASE}/api/warehouses/${w.id}/delete`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "操作失敗"); load(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };

  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <div className="card col gap-14" style={{ width: "min(600px, 100%)", padding: 24, maxHeight: "88vh", overflowY: "auto" }} onClick={(e) => e.stopPropagation()}>
        <div className="row spread">
          <div className="col gap-2"><div style={{ fontSize: 17, fontWeight: 800 }}>倉庫管理</div><div className="muted" style={{ fontSize: 12 }}>編輯倉庫詳細信息(名稱/編碼/類型/容量);位置在「倉庫地圖 GIS」標記</div></div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button>
        </div>
        {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}

        {edit ? (
          <div className="col gap-12" style={{ padding: 14, borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
            <div style={{ fontSize: 14, fontWeight: 800 }}>{edit.id ? "編輯倉庫" : "新增倉庫"}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>名稱
                <input className="input" value={edit.name || ""} onChange={(e) => setEdit({ ...edit, name: e.target.value })}/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>編碼
                <input className="input" value={edit.code || ""} onChange={(e) => setEdit({ ...edit, code: e.target.value })} placeholder="可選"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>類型
                <input className="input" list="inv-wh-types" value={edit.warehouse_type || ""} onChange={(e) => setEdit({ ...edit, warehouse_type: e.target.value })}/>
                <datalist id="inv-wh-types">{INV_WH_TYPES.map((t) => <option key={t} value={t}/>)}</datalist></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>容量使用率(%)
                <input className="input" type="number" min="0" max="100" value={edit.capacity_usage == null ? "" : edit.capacity_usage} onChange={(e) => setEdit({ ...edit, capacity_usage: e.target.value })}/></label>
            </div>
            <div className="row gap-8">
              <button className="btn btn-primary btn-sm" disabled={busy} onClick={save}>{busy ? "保存中…" : "保存"}</button>
              <button className="btn btn-sm" onClick={() => setEdit(null)}>取消</button>
            </div>
          </div>
        ) : (
          <button className="btn btn-primary btn-sm" style={{ alignSelf: "flex-start" }} onClick={() => setEdit({ name: "", code: "", warehouse_type: "中心庫", capacity_usage: "" })}><Icon name="plus" size={14}/>新增倉庫</button>
        )}

        {loading ? <div className="muted" style={{ fontSize: 13 }}>載入中…</div> : (
          <div className="card" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--line)" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead><tr style={{ background: "var(--surface-2)", textAlign: "left" }}>{["倉庫", "編碼", "類型", "容量", "已定位", "操作"].map((h) => <th key={h} style={{ padding: "10px 14px", fontWeight: 700, fontSize: 12 }}>{h}</th>)}</tr></thead>
              <tbody>
                {list.map((w) => (
                  <tr key={w.id} style={{ borderTop: "1px solid var(--line)" }}>
                    <td style={{ padding: "10px 14px", fontWeight: 700 }}>{w.name}{w.is_default && <span className="badge badge-info" style={{ height: 19, marginLeft: 8 }}>默認</span>}</td>
                    <td className="num muted" style={{ padding: "10px 14px" }}>{w.code || "—"}</td>
                    <td style={{ padding: "10px 14px" }}>{w.warehouse_type || "—"}</td>
                    <td className="num" style={{ padding: "10px 14px" }}>{w.capacity_usage != null ? w.capacity_usage + "%" : "—"}</td>
                    <td style={{ padding: "10px 14px" }}>{w.lat != null ? <span className="badge badge-ok" style={{ height: 19 }}>是</span> : <span className="badge badge-gray" style={{ height: 19 }}>否</span>}</td>
                    <td style={{ padding: "10px 14px" }}>
                      <div className="row gap-6">
                        <button className="btn btn-sm" onClick={() => setEdit({ id: w.id, name: w.name, code: w.code, warehouse_type: w.warehouse_type, capacity_usage: w.capacity_usage })}><Icon name="edit" size={13}/>編輯</button>
                        <button className="btn btn-sm" disabled={busy || w.can_delete === false} title={w.can_delete === false ? (w.delete_hint || "默認倉庫不能刪除") : (w.delete_hint || "刪除倉庫")} style={{ color: "var(--danger)" }} onClick={() => remove(w)}>刪除</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {list.length === 0 && <tr><td colSpan={6} className="muted" style={{ padding: 16, textAlign: "center" }}>暫無倉庫,點「新增倉庫」</td></tr>}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

// 在庫存頁直接管理「功能分類」—— 分類由用戶決定增刪;勾「借用歸還」=該分類物資帶借還能力
const CategoryQuickManage = ({ cats, onClose }) => {
  const [name, setName] = useStateInv("");
  const [needReturn, setNeedReturn] = useStateInv(false);
  const [busy, setBusy] = useStateInv(false);
  const [err, setErr] = useStateInv("");
  const genCode = (nm) => {
    const ascii = (nm || "").toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return (ascii && ascii.length >= 2) ? ascii.slice(0, 30) : "cat_" + Date.now().toString(36);
  };
  const add = () => {
    if (!name.trim()) { setErr("請輸入分類名稱"); return; }
    setBusy(true); setErr("");
    (window.authFetch || fetch)(`${INV_API_BASE}/api/categories`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: genCode(name), name: name.trim(), requires_return: needReturn }),
    }).then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "新增失敗"); setName(""); setNeedReturn(false); if (window.reloadData) window.reloadData(); })
      .catch((e) => setErr(e.message || String(e))).finally(() => setBusy(false));
  };
  const del = async (c) => {
    if (!window.confirm(`刪除分類「${c.name}」?`)) return;
    setBusy(true); setErr("");
    const post = (force) => (window.authFetch || fetch)(`${INV_API_BASE}/api/categories/${c.id}/delete`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(force ? { force: true } : {}) });
    try {
      let r = await post(false);
      if (r.status === 409) {
        const d = await r.json().catch(() => ({}));
        if (!window.confirm(`${d.error || "該分類下還有數據"}\n\n強制清空並刪除?(不可恢復)`)) { setBusy(false); return; }
        r = await post(true);
      }
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.error || "刪除失敗");
      if (window.reloadData) window.reloadData();
    } catch (e) { setErr(e.message || String(e)); } finally { setBusy(false); }
  };
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 60, background: "rgba(15,23,42,0.45)", display: "grid", placeItems: "center", padding: 16 }}>
      <div onClick={(e) => e.stopPropagation()} className="card" style={{ width: "min(480px,96vw)", padding: 20 }}>
        <div className="row spread" style={{ marginBottom: 12 }}>
          <span style={{ fontSize: 16, fontWeight: 900 }}>管理物資分類</span>
          <button className="btn btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="muted" style={{ fontSize: 12.5, marginBottom: 12, lineHeight: 1.5 }}>分類由你自己決定。勾「需要借用歸還」的分類(如工具/設備),物資會帶借還與歸還提醒能力;不勾的就是普通庫存(如消耗品)。</div>
        <div className="col gap-8" style={{ marginBottom: 14, maxHeight: 240, overflow: "auto" }}>
          {(cats || []).map((c) => (
            <div key={c.id} className="row spread" style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid var(--line)" }}>
              <span className="row gap-6" style={{ fontWeight: 600, alignItems: "center" }}>{c.name}{c.requires_return && <span className="badge badge-info" style={{ height: 18, fontSize: 10 }}>借還</span>}</span>
              <button className="btn btn-sm" disabled={busy} onClick={() => del(c)}>刪除</button>
            </div>
          ))}
          {(!cats || cats.length === 0) && <div className="muted" style={{ fontSize: 12.5 }}>還沒有分類,在下面新增。</div>}
        </div>
        <div className="col gap-8" style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="新分類名稱,如:工具 / 食材 / 辦公用品"/>
          <label className="row gap-8" style={{ fontSize: 13, fontWeight: 700, cursor: "pointer", alignItems: "center" }}>
            <input type="checkbox" checked={needReturn} onChange={(e) => setNeedReturn(e.target.checked)}/>需要借用歸還(工具 / 設備類)</label>
          {err && <div style={{ color: "var(--danger)", fontSize: 12.5, fontWeight: 700 }}>⚠ {err}</div>}
          <button className="btn btn-primary" disabled={busy} onClick={add}>{busy ? "處理中…" : "新增分類"}</button>
        </div>
      </div>
    </div>
  );
};

window.PageInventory = PageInventory;
