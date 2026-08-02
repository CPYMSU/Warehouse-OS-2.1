/* WAREHOUSE 2.1 · 跨倉在途 — Swiss 版式,真後端(冷鏈 + 到貨 ETA) */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "跨倉在途": "In-transit",
  "在途 {a} · 延誤 {d} · 近期到貨 {r} · 發運到貨可一鍵手動,複雜調撥交秘書": "{a} in transit · {d} delayed · {r} arrived · dispatch/receive in one click, complex transfers via secretary",
  "發運": "Dispatch",
  "問秘書": "Ask secretary",
  "跨倉在途現在有什麼要處理的?把延誤的、快到貨的在途單列出來": "What needs attention on cross-warehouse transit right now? List the delayed and soon-arriving shipments",
  "在途批次": "In transit", "延誤": "Delayed", "近期到貨": "Arrived recently",
  "批": "batches", "無在途": "None in transit", "全部達時": "All on time",
  "快捷發運": "Quick dispatch",
  "物資": "Item", "數量": "Qty", "源倉(不填自動選)": "From (auto if blank)", "目標倉": "To warehouse",
  "確認發運": "Confirm dispatch", "取消": "Cancel", "處理中…": "Working…",
  "已發運 {n}": "Dispatched {n}", "操作失敗": "Action failed", "請填寫正的數量": "Enter a positive quantity",
  "請選擇目標倉": "Choose a destination warehouse",
  "全部": "All", "在途": "In transit", "已到貨": "Arrived", "已撤銷": "Cancelled",
  "單號": "No.", "批次": "Batch", "路線": "Route", "距離": "Distance", "到貨": "ETA / Arrival", "狀態": "Status", "操作": "Action",
  "冷鏈": "Cold-chain",
  "約 {h}h 到": "~{h}h to go", "逾時 {h}h": "{h}h overdue", "已到貨 {d}": "Arrived {d}", "已撤銷": "Cancelled",
  "一鍵到貨": "Receive", "撤銷退回": "Cancel & return",
  "確認要撤銷 {no} 並退回源倉嗎?": "Cancel {no} and return goods to the source warehouse?",
  "已到貨入庫 {no}": "Received {no}", "已撤銷 {no}": "Cancelled {no}",
  "當前篩選下沒有在途單": "No shipments under this filter",
  "換個篩選,或對秘書說「幫我發運◯◯到◯倉」。": "Try another filter, or tell the secretary “dispatch ◯◯ to warehouse ◯”.",
  "幫我發運物資到別的倉庫,請追問物資、數量、目標倉與源倉,確認後發運並估到貨時間": "Dispatch goods to another warehouse for me. Ask for the item, quantity, destination and source warehouse, then dispatch and estimate the arrival time after confirmation",
  "冷鏈在途,注意溫控與時效": "Cold-chain shipment — watch temperature and timing",
});

const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, num } = W2;
const ask = (p) => W2.openSecretary(p);

const fmtEta = (s) => {
  if (s.status === "arrived") return { tone: "ok", text: t("已到貨 {d}", { d: (s.arrivedAt || "").slice(5, 16) }) };
  if (s.status === "cancelled") return { tone: "plain", text: t("已撤銷") };
  const h = s.hoursToEta;
  if (h == null) return { tone: "plain", text: s.eta || "—" };
  if (h < 0) return { tone: "bad", text: t("逾時 {h}h", { h: Math.abs(h) }) };
  return { tone: h <= 3 ? "warn" : "plain", text: t("約 {h}h 到", { h }) };
};

const Page = ({ boot, reload }) => {
  const whs = boot.WAREHOUSES || [];
  const canManage = W2.hasPermission ? W2.hasPermission("inventory.shipment") : false;
  const [rows, setRows] = _s(boot.SHIPMENTS || []);
  const [flt, setFlt] = _s("in_transit");
  const [busy, setBusy] = _s("");
  const [msg, setMsg] = _s(null);
  const [qd, setQd] = _s(null);   // 快捷發運表單 { item, qty, to, from }

  const refetch = () => W2.json("/api/inventory/shipments").then(d => d && d.shipments && setRows(d.shipments)).catch(() => {});
  _e(() => { refetch(); }, []);

  const stats = _mm(() => ({
    inTransit: rows.filter(r => r.status === "in_transit" || r.delayed).length,
    delayed: rows.filter(r => r.delayed).length,
    arrived: rows.filter(r => r.status === "arrived").length,
  }), [rows]);

  const list = _mm(() => {
    let l = rows;
    if (flt === "in_transit") l = l.filter(r => r.status === "in_transit" || r.delayed);
    else if (flt === "delayed") l = l.filter(r => r.delayed);
    else if (flt === "arrived") l = l.filter(r => r.status === "arrived");
    else if (flt === "cancelled") l = l.filter(r => r.status === "cancelled");
    return l;
  }, [rows, flt]);

  const doArrive = async (s) => {
    if (!canManage) return;
    setBusy(s.shipmentNo + "a"); setMsg(null);
    try {
      await W2.post("/api/inventory/shipments/arrive", { shipment_no: s.shipmentNo });
      setMsg({ ok: true, text: t("已到貨入庫 {no}", { no: s.shipmentNo }) });
      await refetch(); reload && reload();
    } catch (e) { setMsg({ ok: false, text: e.message || t("操作失敗") }); }
    finally { setBusy(""); }
  };
  const doCancel = async (s) => {
    if (!canManage) return;
    if (!window.confirm(t("確認要撤銷 {no} 並退回源倉嗎?", { no: s.shipmentNo }))) return;
    setBusy(s.shipmentNo + "c"); setMsg(null);
    try {
      await W2.post("/api/inventory/shipments/cancel", { shipment_no: s.shipmentNo });
      setMsg({ ok: true, text: t("已撤銷 {no}", { no: s.shipmentNo }) });
      await refetch(); reload && reload();
    } catch (e) { setMsg({ ok: false, text: e.message || t("操作失敗") }); }
    finally { setBusy(""); }
  };
  const runDispatch = async () => {
    if (!canManage) return;
    const n = Number(qd.qty);
    if (!Number.isFinite(n) || n <= 0) { setMsg({ ok: false, text: t("請填寫正的數量") }); return; }
    if (!(qd.item || "").trim()) { setMsg({ ok: false, text: t("物資") + " ?" }); return; }
    if (!(qd.to || "").trim()) { setMsg({ ok: false, text: t("請選擇目標倉") }); return; }
    setBusy("dispatch"); setMsg(null);
    try {
      const r = await W2.post("/api/inventory/shipments/dispatch", {
        item: qd.item.trim(), qty: n, to: qd.to, from: (qd.from || "").trim() || undefined,
      });
      setQd(null);
      setMsg({ ok: true, text: r.message || t("已發運 {n}", { n }) });
      await refetch(); reload && reload();
    } catch (e) { setMsg({ ok: false, text: e.message || t("操作失敗") }); }
    finally { setBusy(""); }
  };

  return (
    <>
      <Folio no="05" en="IN-TRANSIT" title={t("跨倉在途")}
        sub={t("在途 {a} · 延誤 {d} · 近期到貨 {r} · 發運到貨可一鍵手動,複雜調撥交秘書", { a: stats.inTransit, d: stats.delayed, r: stats.arrived })}
        right={<>
          {canManage && <B icon="outbound" onClick={() => setQd(qd ? null : { item: "", qty: "", to: (whs[0] || ""), from: "" })}>{t("發運")}</B>}
          <B kind="primary" icon="sparkle" onClick={() => ask(t("跨倉在途現在有什麼要處理的?把延誤的、快到貨的在途單列出來"))}>{t("問秘書")}</B>
        </>}/>

      <div className="row g14 wrap" style={{ padding: "16px 0", borderBottom: "1px solid var(--hair)" }}>
        <Kpi label={t("在途批次")} value={stats.inTransit} unit={t("批")} foot={stats.inTransit ? undefined : t("無在途")}/>
        <Kpi label={t("延誤")} value={stats.delayed} unit={t("批")} red={stats.delayed > 0} foot={stats.delayed ? undefined : t("全部達時")}/>
        <Kpi label={t("近期到貨")} value={stats.arrived} unit={t("批")}/>
      </div>

      {qd && (
        <div className="row g10 wrap" style={{ alignItems: "center", padding: "12px 14px", background: "var(--paper-2)", borderBottom: "1px solid var(--hair)" }}>
          <span className="label" style={{ fontSize: 9 }}>{t("快捷發運")}</span>
          <input className="field boxed" style={{ width: 160, height: 32 }} value={qd.item} placeholder={t("物資")} onChange={e => setQd({ ...qd, item: e.target.value })}/>
          <input className="field boxed" type="number" min="0" style={{ width: 90, height: 32 }} value={qd.qty} placeholder={t("數量")} onChange={e => setQd({ ...qd, qty: e.target.value })}/>
          <select className="field boxed" style={{ width: 150, height: 32 }} value={qd.from} onChange={e => setQd({ ...qd, from: e.target.value })}>
            <option value="">{t("源倉(不填自動選)")}</option>
            {whs.map(w => <option key={w} value={w}>{w}</option>)}
          </select>
          <span style={{ color: "var(--ink-4)" }}>→</span>
          <select className="field boxed" style={{ width: 150, height: 32 }} value={qd.to} onChange={e => setQd({ ...qd, to: e.target.value })}>
            {whs.map(w => <option key={w} value={w}>{w}</option>)}
          </select>
          <B size="sm" kind="primary" icon="check" disabled={busy === "dispatch"} onClick={runDispatch}>{busy === "dispatch" ? t("處理中…") : t("確認發運")}</B>
          <B size="sm" onClick={() => setQd(null)}>{t("取消")}</B>
        </div>
      )}

      {msg && <div className="row g6" style={{ padding: "10px 14px", fontSize: 12, color: msg.ok ? "var(--ok)" : "var(--red)", fontWeight: 600 }}>
        <I name={msg.ok ? "checkCircle" : "x"} size={14} color={msg.ok ? "var(--ok)" : "var(--red)"}/>{msg.text}</div>}

      <div className="row g6 wrap" style={{ padding: "14px 0" }}>
        {[["in_transit", "在途"], ["delayed", "延誤"], ["arrived", "已到貨"], ["cancelled", "已撤銷"], ["all", "全部"]].map(([id, lb]) => (
          <button key={id} className={"chip" + (flt === id ? " on" : "")} onClick={() => setFlt(id)}>{t(lb)}</button>
        ))}
      </div>

      <div style={{ overflowX: "auto" }}>
        <table className="tbl2">
          <thead><tr>
            <th>{t("單號")}</th><th>{t("物資")}</th><th>{t("數量")}</th><th>{t("路線")}</th><th>{t("距離")}</th><th>{t("到貨")}</th><th>{t("狀態")}</th><th style={{ width: 150 }}>{t("操作")}</th>
          </tr></thead>
          <tbody>
            {list.map((s) => {
              const eta = fmtEta(s);
              const isTransit = s.delayed || s.status === "in_transit";
              return (
                <tr key={s.shipmentNo}>
                  <td><span className="num" style={{ fontWeight: 600, fontSize: 11.5 }}>{s.shipmentNo}</span></td>
                  <td>
                    <div className="col g2">
                      <span className="row g6" style={{ fontWeight: 650 }}>{s.item}{s.coldChain && <T tone="bad" dot>{t("冷鏈")}</T>}</span>
                      {s.batchNo && <span className="num muted" style={{ fontSize: 10 }}>{s.batchNo}{s.expireAt ? " · " + s.expireAt : ""}</span>}
                    </div>
                  </td>
                  <td><span className="num" style={{ fontWeight: 700 }}>{num(s.qty)}</span> <span className="muted num" style={{ fontSize: 11 }}>{s.unit}</span></td>
                  <td><span className="num" style={{ fontSize: 11.5 }}>{s.from} <span style={{ color: "var(--ink-4)" }}>→</span> {s.to}</span></td>
                  <td><span className="num muted" style={{ fontSize: 11.5 }}>{s.distanceKm != null ? s.distanceKm + " km" : "—"}</span></td>
                  <td><T tone={eta.tone} dot={eta.tone !== "plain"}>{eta.text}</T></td>
                  <td>{s.delayed ? <T tone="bad" dot>{t("延誤")}</T> : isTransit ? <T tone="warn" dot>{t("在途")}</T> : s.status === "arrived" ? <T tone="ok" dot>{t("已到貨")}</T> : <T tone="plain">{t("已撤銷")}</T>}</td>
                  <td>
                    {isTransit && canManage ? (
                      <div className="row g4">
                        <B size="sm" kind="primary" icon="inbound" disabled={busy === s.shipmentNo + "a"} onClick={() => doArrive(s)}>{busy === s.shipmentNo + "a" ? "…" : t("一鍵到貨")}</B>
                        <button className="btn sm" title={t("撤銷退回")} style={{ padding: "0 8px" }} disabled={busy === s.shipmentNo + "c"} onClick={() => doCancel(s)}><I name="x" size={12}/></button>
                      </div>
                    ) : <span className="muted" style={{ fontSize: 11 }}>—</span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!list.length && <EM icon="outbound" title={t("當前篩選下沒有在途單")} sub={t("換個篩選,或對秘書說「幫我發運◯◯到◯倉」。")}/>}
      <div className="muted" style={{ fontSize: 10.5, marginTop: 14, lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
    </>
  );
};

window.W2.PAGES["shipments"] = Page;
})();
