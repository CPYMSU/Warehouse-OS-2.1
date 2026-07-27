/* ============================================================
   3 · 入庫管理 — 入庫單列表 + 分段新建彈窗
   ============================================================ */
const { useState: useStateIn, useRef: useRefIn } = React;

const INBOUND_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const defaultInboundTime = () => {
  const d = new Date();
  const pad = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
};
const newInboundRequestId = () => "inbound-web-" + (
  window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
);
const inboundPendingStorageKey = () => {
  try { return `warehouse.pending.${encodeURIComponent(window.localStorage.getItem("warehouse_current_tenant") || "no-tenant")}.inbound`; }
  catch (e) { return "warehouse.pending.no-tenant.inbound"; }
};
const pendingInboundRequestId = (key) => {
  try {
    const existing = window.sessionStorage.getItem(key);
    if (existing) return existing;
    const created = newInboundRequestId();
    window.sessionStorage.setItem(key, created);
    return created;
  } catch (e) { return newInboundRequestId(); }
};
const clearPendingInboundRequestId = (key, requestId) => {
  try {
    if (window.sessionStorage.getItem(key) === requestId) window.sessionStorage.removeItem(key);
  } catch (e) {}
};

const PageInbound = () => {
  const [modal, setModal] = useStateIn(false);
  const [type, setType] = useStateIn("採購入庫");
  const [open, setOpen] = useStateIn(null);
  const types = ["採購入庫", "調撥入庫", "退庫"];
  const statusMap = { "已入庫": "badge-ok", "待審核": "badge-warn", "質檢中": "badge-info" };
  const rows = window.INBOUND || [];
  const monthRows = rows.filter(r => (r.time || "").startsWith("2026-06"));
  const counts = [
    ["本月入庫", monthRows.length || "—", "批次", "var(--blue)"],
    ["待審核", rows.filter(r => r.status === "待審核").length || "—", "單", "var(--warn)"],
    ["質檢中", rows.filter(r => r.status === "質檢中").length || "—", "單", "var(--info)"],
    ["本月入庫額", "—", "", "var(--teal)"],
  ];

  return (
    <div className="col gap-18">
      <PageHead title="入庫管理" sub="採購到貨 · 檢修退庫 · 調撥入庫"
        actions={<>
          <button className="btn btn-sm"><Icon name="scan" size={15}/>掃碼入庫</button>
          <button className="btn btn-primary btn-sm" onClick={() => setModal(true)}><Icon name="plus" size={15}/>新建入庫單</button>
        </>}/>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16 }}>
        {counts.map(([k,v,u,c],i) => (
          <div key={i} className="card fade-up row spread" style={{ padding: "16px 18px", animationDelay: i*.05+"s" }}>
            <div className="col gap-4"><span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{k}</span><span className="num" style={{ fontSize: 24, fontWeight: 700 }}>{v}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 3 }}>{u}</span></span></div>
            <div style={{ width: 4, height: 38, borderRadius: 2, background: c }}/>
          </div>
        ))}
      </div>

      {/* 類型 tab */}
      <div className="row gap-10">
        {["全部", ...types].map(t => (
          <button key={t} className="btn btn-sm" style={{ background: type === t ? "var(--ink)" : "var(--surface)", color: type === t ? "#fff" : "var(--ink-2)", border: type === t ? "none" : "1px solid var(--line)" }} onClick={() => setType(t)}>{t}</button>
        ))}
      </div>

      <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
        <table className="tbl">
          <thead><tr><th>入庫單號</th><th>入庫時間</th><th>類型</th><th>來源單位</th><th>物資明細</th><th>經辦人</th><th>狀態</th></tr></thead>
          <tbody>
            {rows.map(r => (
              <React.Fragment key={r.id}>
                <tr onClick={() => setOpen(open === r.id ? null : r.id)} style={{ cursor: "pointer" }}>
                  <td><span className="row gap-6"><Icon name="chevronDown" size={13} color="var(--ink-4)" style={{ transform: open === r.id ? "rotate(180deg)" : "none", transition: "transform .2s" }}/><span className="num" style={{ fontWeight: 700, color: "var(--blue)" }}>{r.id}</span></span></td>
                  <td className="num muted">{r.time}</td>
                  <td><span className="badge badge-gray">{r.type}</span></td>
                  <td style={{ fontWeight: 500, color: "var(--ink)" }}>{r.source}</td>
                  <td className="muted">{(r.lines && r.lines.length) ? `${r.lines.length} 項物資` : r.qty}</td>
                  <td>{r.handler}</td>
                  <td><span className={"badge " + statusMap[r.status]}><span className="dot"/>{r.status}</span></td>
                </tr>
                {open === r.id && (
                  <tr>
                    <td colSpan={7} style={{ padding: 0, background: "var(--surface-2)" }}>
                      <div className="col gap-8" style={{ padding: "14px 22px" }}>
                        {(r.lines && r.lines.length) ? r.lines.map((l, i) => (
                          <div key={i} className="row spread" style={{ fontSize: 12.5, padding: "8px 12px", borderRadius: 9, background: "var(--surface)", border: "1px solid var(--line-soft)" }}>
                            <span className="row gap-10" style={{ fontWeight: 600 }}><Icon name="pkg" size={15} color="var(--blue)"/>{l.name}</span>
                            <span className="row gap-16 muted num">
                              <span>×{l.qty} {l.unit}</span>
                              {l.loc !== "—" && <span>庫位 {l.loc}</span>}
                              {l.batch && <span>批次 {l.batch}</span>}
                              {l.quality && <span className="badge badge-ok" style={{ height: 19 }}>{l.quality}</span>}
                            </span>
                          </div>
                        )) : <span className="muted" style={{ fontSize: 12.5 }}>暫無物資明細</span>}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {modal && <InboundModal type={type === "全部" ? "採購入庫" : type} setType={setType} types={types} onClose={() => setModal(false)}/>}
    </div>
  );
};

const InboundModal = ({ type, setType, types, onClose }) => {
  const requestStorageKey = useRefIn(inboundPendingStorageKey());
  const requestId = useRefIn(pendingInboundRequestId(requestStorageKey.current));
  const [step, setStep] = useStateIn(0);
  const [purchaseOrderId, setPurchaseOrderId] = useStateIn("");
  const [source, setSource] = useStateIn("");
  const [time, setTime] = useStateIn(defaultInboundTime);
  const [handler, setHandler] = useStateIn("");
  const [quality, setQuality] = useStateIn("合格");
  const [batch, setBatch] = useStateIn("");
  const [warehouse, setWarehouse] = useStateIn(() => ((window.WAREHOUSES || []).filter(Boolean)[0]) || "");
  const [location, setLocation] = useStateIn("");
  const [lines, setLines] = useStateIn([
    { name: "", qty: "1", unit: "件" },
  ]);
  const [busy, setBusy] = useStateIn(false);
  const [err, setErr] = useStateIn("");
  const [partial, setPartial] = useStateIn(null);
  const sections = ["基本信息", "物資明細", "質檢信息", "存放位置"];
  const isPurchase = /採購|采购|外購|外购|purchase|procurement/i.test(type || "");
  const filledNames = lines.map(l => (l.name || "").trim()).filter(Boolean);
  const storageHint = filledNames.length
    ? `AI 將根據「${filledNames[0]}」和現有庫位推薦存放位置。`
    : "填寫物資名稱後,AI 將根據現有庫位推薦存放位置。";

  const setLine = (i, k, v) => setLines(ls => ls.map((l, j) => j === i ? { ...l, [k]: v } : l));
  const addLine = () => setLines(ls => [...ls, { name: "", qty: "1", unit: "件" }]);
  const removeLine = (i) => setLines(ls => ls.filter((_, j) => j !== i));

  const submit = () => {
    if (inboundPendingStorageKey() !== requestStorageKey.current) { setErr("公司已切換；請關閉表單後在目前公司重新建立入庫單"); return; }
    if (isPurchase && (!Number.isInteger(Number(purchaseOrderId)) || Number(purchaseOrderId) <= 0)) { setErr("採購收貨必須填寫有效的已簽發採購訂單（PO）ID"); setStep(0); return; }
    const valid = lines.filter(l => l.name.trim() && Number(l.qty) > 0);
    if (!valid.length) { setErr("請至少填寫一條有效物資明細"); setStep(1); return; }
    if (valid.length !== lines.length) { setErr("每一條物資明細都必須填寫名稱與大於 0 的數量；請修正或刪除空白行"); setStep(1); return; }
    setBusy(true); setErr("");
    (window.authFetch || fetch)(`${INBOUND_API_BASE}/api/inbound/create`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId.current, type, handler, time, warehouse,
        ...(isPurchase
          ? { purchase_order_id: Number(purchaseOrderId) }
          : { source }),
        lines: valid.map(l => ({ name: l.name, qty: Number(l.qty), unit: l.unit, location, batch, quality })),
      }),
    })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "入庫失敗");
        clearPendingInboundRequestId(requestStorageKey.current, requestId.current);
        if (window.reloadData) window.reloadData();
        if (d.posting_warning) { setPartial(d); setBusy(false); return; }
        onClose();
      })
      .catch(e => { setErr(e.message); setBusy(false); });
  };

  if (partial) {
    const warning = partial.posting_warning || {};
    return (
      <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 50, background: "rgba(14,26,43,0.32)", display: "grid", placeItems: "center", padding: 24 }}>
        <div onClick={e => e.stopPropagation()} className="card col center gap-14" style={{ width: 480, padding: 32, textAlign: "center" }}>
          <Icon name="alert" size={34} color="var(--warn)"/>
          <div style={{ fontSize: 18, fontWeight: 750 }}>入庫單已建立，總賬憑證待重試</div>
          <div className="muted" style={{ fontSize: 13 }}>{warning.message || "庫存已入庫，但財務過賬尚未完成。"}</div>
          {warning.failure_id && <div className="num" style={{ fontSize: 12 }}>失敗佇列 #{warning.failure_id}</div>}
          <button className="btn btn-primary" onClick={onClose}>我知道了</button>
        </div>
      </div>
    );
  }

  const safeClose = () => { if (!busy) onClose(); };
  return (
    <div onClick={safeClose} style={{ position: "fixed", inset: 0, zIndex: 50, background: "rgba(14,26,43,0.32)", backdropFilter: "blur(4px)", display: "grid", placeItems: "center", padding: 24, animation: "fadeIn .2s ease" }}>
      <div onClick={e => e.stopPropagation()} className="card" style={{ width: 620, maxHeight: "88vh", padding: 0, overflow: "hidden", animation: "pop .3s cubic-bezier(.2,.8,.3,1) both", boxShadow: "var(--sh-lg)" }}>
        <div className="row spread" style={{ padding: "20px 24px", borderBottom: "1px solid var(--line)" }}>
          <div className="col gap-2"><div style={{ fontSize: 18, fontWeight: 700 }}>新建入庫單</div><div className="num muted" style={{ fontSize: 12 }}>提交後自動生成單號</div></div>
          <button onClick={safeClose} disabled={busy} style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: "var(--surface-2)" }}><Icon name="x" size={17}/></button>
        </div>

        {/* 分段進度 */}
        <div className="row" style={{ padding: "16px 24px", gap: 8, borderBottom: "1px solid var(--line-soft)" }}>
          {sections.map((s,i) => (
            <button key={i} onClick={() => setStep(i)} className="row gap-8" style={{ flex: 1 }}>
              <span className="num" style={{ width: 24, height: 24, borderRadius: "50%", display: "grid", placeItems: "center", fontSize: 12, fontWeight: 700, flexShrink: 0,
                background: i <= step ? "var(--grad)" : "var(--surface-2)", color: i <= step ? "#fff" : "var(--ink-4)", border: i <= step ? "none" : "1px solid var(--line)" }}>{i < step ? "✓" : i+1}</span>
              <span style={{ fontSize: 12.5, fontWeight: 600, color: i === step ? "var(--ink)" : "var(--ink-4)", whiteSpace: "nowrap" }}>{s}</span>
            </button>
          ))}
        </div>

        <div className="scroll-y" style={{ padding: 24, maxHeight: "46vh" }}>
          {step === 0 && (
            <div className="col gap-16">
              <div className="col gap-8"><label style={lbl}>入庫類型</label>
                <div className="row gap-8">{types.map(t => <button key={t} onClick={() => setType(t)} className="btn btn-sm" style={{ flex: 1, background: type===t?"var(--blue-soft)":"var(--surface)", color: type===t?"var(--blue)":"var(--ink-2)", borderColor: type===t?"var(--blue)":"var(--line)" }}>{t}</button>)}</div>
              </div>
              {isPurchase ? <>
                <div style={{ padding: 14, borderRadius: 12, background: "var(--blue-soft)", display: "flex", gap: 10, alignItems: "flex-start" }}>
                  <Icon name="shield" size={18} color="var(--blue)"/>
                  <span style={{ fontSize: 12.5, lineHeight: 1.6, color: "var(--ink-2)" }}>
                    採購收貨必須關聯已完成審批並已簽發的採購訂單。供應商、幣別、成本、稅額、預算與可收數量均由 PO 權威帶入，不可在入庫單中另行填寫或改寫。
                  </span>
                </div>
                <Field label="已簽發採購訂單（PO）ID"><input className="input num" type="number" min="1" step="1" value={purchaseOrderId} onChange={e => setPurchaseOrderId(e.target.value)} placeholder="必填，例如 18"/></Field>
                <div className="muted" style={{ fontSize: 12 }}>請先在 ERP 採購業務鏈確認工作流已完成、PO 狀態為 issued；草稿、已取消或已收滿的 PO 均不能入庫。</div>
              </> : (
                <Field label="來源單位 / 內部單號"><input className="input" value={source} onChange={e => setSource(e.target.value)} placeholder="調撥來源 / 退庫單號"/></Field>
              )}
              <div className="row gap-12"><Field label="入庫時間" flex><input className="input" value={time} onChange={e => setTime(e.target.value)}/></Field><Field label="經辦人" flex><input className="input" value={handler} onChange={e => setHandler(e.target.value)} placeholder="姓名"/></Field></div>
            </div>
          )}
          {step === 1 && (
            <div className="col gap-12">
              {lines.map((m,i) => (
                <div key={i} className="row gap-10 card" style={{ padding: 12 }}>
                  <Icon name="pkg" size={18} color="var(--blue)"/>
                  <input className="input" value={m.name} onChange={e => setLine(i, "name", e.target.value)} placeholder="物資名稱" style={{ flex: 1, height: 34 }}/>
                  <input className="input num" value={m.qty} onChange={e => setLine(i, "qty", e.target.value)} style={{ width: 64, height: 34, textAlign: "center" }}/>
                  <input className="input" value={m.unit} onChange={e => setLine(i, "unit", e.target.value)} style={{ width: 54, height: 34, textAlign: "center" }}/>
                  <button onClick={() => removeLine(i)} style={{ width: 30, height: 30, borderRadius: 8, display: "grid", placeItems: "center", background: "var(--surface-2)", color: "var(--ink-4)" }}><Icon name="x" size={14}/></button>
                </div>
              ))}
              <button onClick={addLine} className="btn btn-sm" style={{ borderStyle: "dashed", color: "var(--blue)" }}><Icon name="plus" size={14}/>添加物資</button>
            </div>
          )}
          {step === 2 && (
            <div className="col gap-16">
              <Field label="質檢狀態"><div className="row gap-8">{["合格", "待檢", "不合格"].map((s) => <button key={s} onClick={() => setQuality(s)} className="btn btn-sm" style={{ flex: 1, background: quality===s?"var(--ok-soft)":"var(--surface)", color: quality===s?"var(--ok)":"var(--ink-2)", borderColor: quality===s?"var(--ok)":"var(--line)" }}>{s}</button>)}</div></Field>
              <Field label="批次號"><input className="input num" value={batch} onChange={e => setBatch(e.target.value)}/></Field>
              <Field label="上傳質檢報告 / 照片"><div className="col center gap-8" style={{ height: 90, borderRadius: 12, border: "1.5px dashed var(--line)", background: "var(--surface-2)", color: "var(--ink-4)" }}><Icon name="plus" size={20}/><span style={{ fontSize: 12.5 }}>點擊或拖拽上傳附件</span></div></Field>
            </div>
          )}
          {step === 3 && (
            <div className="col gap-16">
              <Field label="存放倉庫"><input className="input" value={warehouse} onChange={e => setWarehouse(e.target.value)}/></Field>
              <Field label="存放區域 / 庫位"><div className="row gap-12"><input className="input num" value={location} onChange={e => setLocation(e.target.value)} placeholder="庫位編碼" style={{ flex: 1 }}/></div></Field>
              <div style={{ padding: 14, borderRadius: 12, background: "var(--teal-soft)", display: "flex", gap: 10, alignItems: "center" }}>
                <Icon name="sparkle" size={18} color="var(--teal)"/>
                <span style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{storageHint}</span>
              </div>
            </div>
          )}
        </div>

        <div className="col" style={{ borderTop: "1px solid var(--line)" }}>
          {err && <div style={{ padding: "10px 24px 0", color: "var(--danger)", fontSize: 12.5 }}>⚠ {err}</div>}
          <div className="row spread" style={{ padding: "16px 24px" }}>
            <button className="btn" onClick={() => step > 0 ? setStep(step-1) : safeClose()} disabled={busy}>{step > 0 ? "上一步" : "取消"}</button>
            <button className="btn btn-primary" onClick={() => step < 3 ? setStep(step+1) : submit()} disabled={busy}>{busy ? "提交中…" : (step < 3 ? "下一步" : (isPurchase ? "確認收貨入庫" : "確認入庫"))}<Icon name={step<3?"arrow":"check"} size={15}/></button>
          </div>
        </div>
      </div>
    </div>
  );
};

const lbl = { fontSize: 12, fontWeight: 600, color: "var(--ink-3)" };
const Field = ({ label, children, flex }) => (
  <div className="col gap-8" style={{ flex: flex ? 1 : undefined }}><label style={lbl}>{label}</label>{children}</div>
);

window.PageInbound = PageInbound;
