/* ============================================================
   4 · 出庫/領用 — 列表 + 搶修模式（亮點）
   ============================================================ */
const { useState: useStateOut, useRef: useRefOut } = React;

const OUTBOUND_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const newOutboundRequestId = () => "outbound-web-" + (
  window.crypto && window.crypto.randomUUID
    ? window.crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`
);
const outboundPendingStorageKey = (kind) => {
  try { return `warehouse.pending.${encodeURIComponent(window.localStorage.getItem("warehouse_current_tenant") || "no-tenant")}.outbound.${kind}`; }
  catch (e) { return `warehouse.pending.no-tenant.outbound.${kind}`; }
};
const pendingOutboundRequestId = (key) => {
  try {
    const existing = window.sessionStorage.getItem(key);
    if (existing) return existing;
    const created = newOutboundRequestId();
    window.sessionStorage.setItem(key, created);
    return created;
  } catch (e) { return newOutboundRequestId(); }
};
const clearPendingOutboundRequestId = (key, requestId) => {
  try { if (window.sessionStorage.getItem(key) === requestId) window.sessionStorage.removeItem(key); } catch (e) {}
};

const PageOutbound = () => {
  const [mode, setMode] = useStateOut("list");
  const [showCreate, setShowCreate] = useStateOut(false);
  return (
    <div className="col gap-18">
      <PageHead title="出庫 / 領用管理" sub="搶修領料 · 檢修領料 · 工程領料"
        actions={<>
          <button className="btn btn-sm"><Icon name="scan" size={15}/>掃碼出庫</button>
          <button className="btn btn-sm" onClick={() => setShowCreate(true)}><Icon name="plus" size={15}/>新建領用單</button>
          <button className="btn btn-danger btn-sm pulse-danger" onClick={() => setMode("repair")}><Icon name="flame" size={15}/>緊急搶修出庫</button>
        </>}/>
      {showCreate && <CreateOutboundModal onClose={() => setShowCreate(false)}/>}

      {/* 模式切換 */}
      <div className="row gap-8" style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 12, padding: 4, width: "fit-content" }}>
        {[["list", "出庫單列表", "outbound"], ["repair", "搶修模式", "flame"]].map(([m,t,ic]) => (
          <button key={m} onClick={() => setMode(m)} className="row gap-8" style={{ height: 38, padding: "0 18px", borderRadius: 9, fontSize: 13.5, fontWeight: 700,
            background: mode===m ? (m==="repair"?"linear-gradient(120deg,#FB6B6B,#EF4444)":"var(--grad)") : "transparent",
            color: mode===m ? "#fff" : "var(--ink-3)", boxShadow: mode===m?"var(--sh-sm)":"none" }}>
            <Icon name={ic} size={16}/>{t}{m==="repair" && mode!==m && <span style={{ fontSize: 9, fontWeight: 800, color: "#EF4444", background: "var(--danger-soft)", padding: "1px 5px", borderRadius: 5 }}>HOT</span>}
          </button>
        ))}
      </div>

      {mode === "list" ? <OutList/> : <RepairMode/>}
    </div>
  );
};

const OutList = () => {
  const [open, setOpen] = useStateOut(null);
  const useMap = { "搶修": "badge-danger", "檢修": "badge-info", "工程": "badge-purple" };
  const stMap = { "已出庫": "badge-ok", "審批中": "badge-warn" };
  return (
    <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
      <table className="tbl">
        <thead><tr><th>領用單號</th><th>領用時間</th><th>領用部門</th><th>用途</th><th>關聯地點/項目</th><th>物資</th><th>審批狀態</th></tr></thead>
        <tbody>
          {window.OUTBOUND.map(r => (
            <React.Fragment key={r.id}>
              <tr onClick={() => setOpen(open === r.id ? null : r.id)} style={{ cursor: "pointer" }}>
                <td><div className="row gap-8"><Icon name="chevronDown" size={13} color="var(--ink-4)" style={{ transform: open === r.id ? "rotate(180deg)" : "none", transition: "transform .2s" }}/><span className="num" style={{ fontWeight: 700, color: r.urgent?"var(--danger)":"var(--teal)" }}>{r.id}</span>{r.urgent && <Icon name="flame" size={14} color="var(--danger)"/>}</div></td>
                <td className="num muted">{r.time}</td>
                <td style={{ fontWeight: 500, color: "var(--ink)" }}>{r.dept}</td>
                <td><span className={"badge " + useMap[r.use]}>{r.use}</span></td>
                <td className="muted">{r.target}</td>
                <td className="muted">{(r.lines && r.lines.length) ? `${r.lines.length} 項物資` : r.qty}</td>
                <td><span className={"badge " + stMap[r.status]}><span className="dot"/>{r.status}</span></td>
              </tr>
              {open === r.id && (
                <tr>
                  <td colSpan={7} style={{ padding: 0, background: "var(--surface-2)" }}>
                    <div className="col gap-8" style={{ padding: "14px 22px" }}>
                      {(r.lines && r.lines.length) ? r.lines.map((l, i) => (
                        <div key={i} className="row spread" style={{ fontSize: 12.5, padding: "8px 12px", borderRadius: 9, background: "var(--surface)", border: "1px solid var(--line-soft)" }}>
                          <span className="row gap-10" style={{ fontWeight: 600 }}><Icon name="pkg" size={15} color="var(--teal)"/>{l.name}</span>
                          <span className="row gap-16 muted num"><span>×{l.qty} {l.unit}</span>{l.loc !== "—" && <span>庫位 {l.loc}</span>}</span>
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
  );
};

const RepairMode = () => {
  const requestStorageKey = useRefOut(outboundPendingStorageKey("repair"));
  const requestId = useRefOut(pendingOutboundRequestId(requestStorageKey.current));
  const [fault, setFault] = useStateOut(null);
  const [target, setTarget] = useStateOut("");
  const [result, setResult] = useStateOut(null);
  const [busy, setBusy] = useStateOut(false);
  const [err, setErr] = useStateOut("");
  const targets = Array.from(new Set((window.OUTBOUND || [])
    .map(row => row.target)
    .filter(t => t && t !== "—"))).slice(0, 6);

  const submit = () => {
    if (!fault || !target) return;
    if (outboundPendingStorageKey("repair") !== requestStorageKey.current) { setErr("公司已切換；請在目前公司重新選擇搶修出庫"); return; }
    setBusy(true); setErr("");
    (window.authFetch || fetch)(`${OUTBOUND_API_BASE}/api/outbound/create`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId.current,
        use: "搶修", urgent: true, target,
        lines: fault.items.map(it => ({ name: it.name, qty: it.qty, unit: it.unit })),
      }),
    })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => {
        if (!ok) throw new Error(d.error || "出庫失敗");
        clearPendingOutboundRequestId(requestStorageKey.current, requestId.current);
        setResult(d);
        if (window.reloadData) window.reloadData();
      })
      .catch(e => { setErr(e.message); })
      .finally(() => setBusy(false));
  };

  if (result) return (
    <div className="card fade-up col center" style={{ padding: 48, gap: 16, textAlign: "center" }}>
      <div className="pulse-danger" style={{ width: 72, height: 72, borderRadius: "50%", background: result.posting_warning ? "var(--warn-soft)" : "var(--ok-soft)", display: "grid", placeItems: "center" }}><Icon name={result.posting_warning ? "alert" : "check"} size={36} color={result.posting_warning ? "var(--warn)" : "var(--ok)"} sw={2.4}/></div>
      <div style={{ fontSize: 20, fontWeight: 700 }}>{result.posting_warning ? "搶修出庫已完成，總賬待重試" : "搶修出庫單已生成"}</div>
      <div className="muted" style={{ fontSize: 13.5 }}>單號 <b className="num" style={{ color: "var(--danger)" }}>{result.order_no}</b> · 已扣減庫存 {result.total} 件 · 寫入出庫記錄與審計</div>
      {result.posting_warning && <div style={{ color: "var(--warn)", fontSize: 12.5 }}>{result.posting_warning.message}{result.posting_warning.failure_id ? ` · 失敗佇列 #${result.posting_warning.failure_id}` : ""}</div>}
      <div className="row gap-12" style={{ marginTop: 8 }}>
        <button className="btn" onClick={() => { requestStorageKey.current = outboundPendingStorageKey("repair"); requestId.current = pendingOutboundRequestId(requestStorageKey.current); setResult(null); setFault(null); setTarget(""); setErr(""); }}>再建一單</button>
      </div>
    </div>
  );

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: 18 }}>
      {/* 左：選擇 */}
      <div className="col gap-18">
        <div className="card fade-up" style={{ padding: 22, borderColor: "rgba(239,68,68,0.2)" }}>
          <div className="row gap-10" style={{ marginBottom: 16 }}>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: "var(--danger-soft)", color: "var(--danger)", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 14 }}>1</div>
            <span className="sec-title">選擇故障類型</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            {window.FAULT_TYPES.map(f => (
              <button key={f.id} onClick={() => setFault(f)} className="col gap-8" style={{ padding: 16, borderRadius: 14, textAlign: "left",
                border: fault?.id===f.id ? `1.5px solid ${f.color}` : "1px solid var(--line)",
                background: fault?.id===f.id ? f.color+"14" : "var(--surface-2)", transition: "all .16s" }}>
                <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center", background: f.color+"1c", color: f.color }}><Icon name={f.icon} size={20}/></div>
                <span style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink)" }}>{f.name}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="card fade-up" style={{ padding: 22, animationDelay: ".06s" }}>
          <div className="row gap-10" style={{ marginBottom: 16 }}>
            <div style={{ width: 30, height: 30, borderRadius: 9, background: "var(--blue-soft)", color: "var(--blue)", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 14 }}>2</div>
            <span className="sec-title">關聯地點 / 項目</span>
          </div>
          <div className="col gap-8">
            <input className="input" value={target} onChange={e => setTarget(e.target.value)} placeholder="輸入關聯地點 / 項目"/>
            {targets.length ? targets.map(t => (
              <button key={t} onClick={() => setTarget(t)} className="row spread" style={{ padding: "13px 16px", borderRadius: 11, textAlign: "left",
                border: target===t ? "1.5px solid var(--blue)" : "1px solid var(--line)", background: target===t ? "var(--blue-soft)" : "var(--surface)" }}>
                <span className="row gap-10" style={{ fontSize: 13.5, fontWeight: 600 }}><Icon name="map2" size={16} color={target===t?"var(--blue)":"var(--ink-4)"}/>{t}</span>
                {target===t && <Icon name="checkCircle" size={18} color="var(--blue)"/>}
              </button>
            )) : <div className="muted" style={{ fontSize: 12.5 }}>暫無歷史地點可選,請手動輸入。</div>}
          </div>
        </div>
      </div>

      {/* 右：推薦 */}
      <div className="card fade-up" style={{ padding: 0, animationDelay: ".1s", overflow: "hidden", alignSelf: "flex-start" }}>
        <div className="row gap-10" style={{ padding: "18px 22px", background: "linear-gradient(120deg, rgba(27,107,255,0.1), rgba(7,182,162,0.1))", borderBottom: "1px solid var(--line)" }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: "var(--grad)", display: "grid", placeItems: "center" }}><Icon name="sparkle" size={18} color="#fff"/></div>
          <div className="col gap-2"><span style={{ fontSize: 15, fontWeight: 700 }}>AI 智能推薦物資</span><span className="muted" style={{ fontSize: 12 }}>根據故障類型與現有庫存</span></div>
        </div>

        {!fault ? (
          <div className="col center" style={{ padding: 60, gap: 12, color: "var(--ink-4)" }}>
            <Icon name="flame" size={36} color="var(--ink-4)"/>
            <span style={{ fontSize: 13.5 }}>請先選擇左側故障類型</span>
          </div>
        ) : (
          <>
            <div style={{ padding: "18px 22px" }}>
              <div className="row spread" style={{ marginBottom: 14 }}>
                <span className="eyebrow">必需物資清單 · {fault.items.length} 項</span>
                <span className="muted" style={{ fontSize: 12 }}>{target || "未填地點"}</span>
              </div>
              <div className="col gap-10">
                {fault.items.map((it,i) => {
                  const short = it.stock < it.qty;
                  return (
                    <div key={i} className="row spread" style={{ padding: "12px 14px", borderRadius: 12, background: short?"var(--danger-soft)":"var(--surface-2)", border: short?"1px solid rgba(239,68,68,0.16)":"1px solid var(--line-soft)" }}>
                      <div className="row gap-10">
                        <Icon name={it.key?"flame":"pkg"} size={17} color={it.key?"var(--danger)":"var(--ink-3)"}/>
                        <div className="col gap-2">
                          <span style={{ fontSize: 13.5, fontWeight: 600 }}>{it.name}{it.key && <span style={{ fontSize: 10, color: "var(--danger)", fontWeight: 800, marginLeft: 6 }}>關鍵</span>}</span>
                          <span className="muted num" style={{ fontSize: 11.5 }}>庫存 {it.stock} {it.unit}{short && <span style={{ color: "var(--danger)", fontWeight: 700 }}> · 庫存不足！</span>}</span>
                        </div>
                      </div>
                      <span className="num" style={{ fontSize: 15, fontWeight: 700, color: short?"var(--danger)":"var(--ink)" }}>×{it.qty}</span>
                    </div>
                  );
                })}
              </div>
            </div>
            <div style={{ padding: "0 22px 18px" }}>
              <div className="row spread" style={{ padding: 14, borderRadius: 12, background: "var(--teal-soft)", marginBottom: 14 }}>
                <span className="row gap-8" style={{ fontSize: 12.5, color: "var(--ink-2)", fontWeight: 600 }}><Icon name="clock" size={15} color="var(--teal)"/>庫存校驗</span>
                <span style={{ fontSize: 12.5, fontWeight: 700 }}>提交後按真實庫存扣減並寫入審計</span>
              </div>
              <button className="btn btn-danger" style={{ width: "100%", height: 46 }} disabled={!target || busy} onClick={submit}>
                <Icon name="flame" size={17}/>{busy ? "生成中…" : "一鍵生成搶修出庫單"}
              </button>
              {err && <div style={{ fontSize: 12, textAlign: "center", marginTop: 8, color: "var(--danger)", fontWeight: 600 }}>⚠ {err}</div>}
              {!target && !err && <div className="muted" style={{ fontSize: 11.5, textAlign: "center", marginTop: 8 }}>請先填寫關聯地點 / 項目</div>}
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const CreateOutboundModal = ({ onClose }) => {
  const requestStorageKey = useRefOut(outboundPendingStorageKey("create"));
  const requestId = useRefOut(pendingOutboundRequestId(requestStorageKey.current));
  const [use, setUse] = useStateOut("檢修");
  const [dept, setDept] = useStateOut("");
  const [target, setTarget] = useStateOut("");
  const [handler, setHandler] = useStateOut("");
  const [lines, setLines] = useStateOut([{ name: "", qty: 1, unit: "件" }]);
  const [busy, setBusy] = useStateOut(false);
  const [err, setErr] = useStateOut("");
  const [result, setResult] = useStateOut(null);

  const setLine = (i, k, v) => setLines(lines.map((l, idx) => idx === i ? { ...l, [k]: v } : l));
  const addLine = () => setLines([...lines, { name: "", qty: 1, unit: "件" }]);
  const delLine = (i) => setLines(lines.length > 1 ? lines.filter((_, idx) => idx !== i) : lines);

  const submit = () => {
    if (outboundPendingStorageKey("create") !== requestStorageKey.current) { setErr("公司已切換；請關閉表單後在目前公司重新建立領用單"); return; }
    const valid = lines.filter(l => (l.name || "").trim() && Number(l.qty) > 0);
    if (!valid.length) { setErr("至少需要一條有效物資明細"); return; }
    if (valid.length !== lines.length) { setErr("每一條物資明細都必須填寫名稱與大於 0 的數量；請修正或刪除空白行"); return; }
    setBusy(true); setErr("");
    (window.authFetch || fetch)(`${OUTBOUND_API_BASE}/api/outbound/create`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ request_id: requestId.current, use, dept: dept || "—", target: target || "—", handler: handler || "—", urgent: false,
        lines: valid.map(l => ({ name: l.name.trim(), qty: Number(l.qty), unit: l.unit || "件" })) }),
    })
      .then(r => r.json().then(d => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "出庫失敗"); clearPendingOutboundRequestId(requestStorageKey.current, requestId.current); setResult(d); if (window.reloadData) window.reloadData(); })
      .catch(e => setErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const safeClose = () => { if (!busy) onClose(); };
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={safeClose}>
      <div className="card col gap-14" style={{ width: "min(560px, 100%)", padding: 24, maxHeight: "86vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
        <div className="row spread"><div style={{ fontSize: 17, fontWeight: 800 }}>新建領用單</div>
          <button onClick={safeClose} disabled={busy} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        {result ? (
          <>
            <div className="col center" style={{ gap: 12, padding: "18px 0" }}>
              <div style={{ width: 60, height: 60, borderRadius: "50%", background: result.posting_warning ? "var(--warn-soft)" : "var(--ok-soft)", display: "grid", placeItems: "center" }}><Icon name={result.posting_warning ? "alert" : "check"} size={30} color={result.posting_warning ? "var(--warn)" : "var(--ok)"} sw={2.4}/></div>
              <div style={{ fontSize: 16, fontWeight: 700 }}>{result.posting_warning ? "領用已完成，總賬憑證待重試" : "領用單已生成"}</div>
              <div className="muted" style={{ fontSize: 13 }}>單號 <b className="num" style={{ color: "var(--teal)" }}>{result.order_no}</b> · 扣減 {result.total} 件 · 已寫入記錄</div>
              {result.posting_warning && <div style={{ color: "var(--warn)", fontSize: 12.5 }}>{result.posting_warning.message}{result.posting_warning.failure_id ? ` · 失敗佇列 #${result.posting_warning.failure_id}` : ""}</div>}
            </div>
            <button className="btn btn-primary" onClick={onClose} style={{ height: 42 }}>完成</button>
          </>
        ) : (
          <>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>用途
                <select className="input" value={use} onChange={e => setUse(e.target.value)}>
                  {["檢修", "工程", "搶修", "借用", "日常領用"].map(u => <option key={u} value={u}>{u}</option>)}
                </select></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>領用部門
                <input className="input" value={dept} onChange={e => setDept(e.target.value)} placeholder="例如:運維班"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>關聯地點 / 項目
                <input className="input" value={target} onChange={e => setTarget(e.target.value)} placeholder="地點 / 項目名稱"/></label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>經辦人
                <input className="input" value={handler} onChange={e => setHandler(e.target.value)} placeholder="姓名"/></label>
            </div>
            <div className="col gap-8">
              <div className="row spread"><span style={{ fontSize: 12.5, fontWeight: 700 }}>物資明細</span>
                <button className="btn btn-sm" onClick={addLine}><Icon name="plus" size={13}/>加一行</button></div>
              {lines.map((l, i) => (
                <div key={i} className="row gap-8">
                  <input className="input" style={{ flex: 2 }} value={l.name} onChange={e => setLine(i, "name", e.target.value)} placeholder="物資名稱"/>
                  <input className="input" style={{ width: 70 }} type="number" min="0" value={l.qty} onChange={e => setLine(i, "qty", e.target.value)}/>
                  <input className="input" style={{ width: 64 }} value={l.unit} onChange={e => setLine(i, "unit", e.target.value)} placeholder="單位"/>
                  <button className="btn btn-sm" onClick={() => delLine(i)} style={{ color: "var(--danger)" }}><Icon name="x" size={13}/></button>
                </div>
              ))}
            </div>
            {err && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {err}</div>}
            <div className="row gap-8">
              <button className="btn btn-primary" onClick={submit} disabled={busy} style={{ flex: 1, height: 42 }}>{busy ? "生成中…" : "生成領用單"}</button>
              <button className="btn" onClick={safeClose} disabled={busy} style={{ height: 42 }}>取消</button>
            </div>
            <div className="muted" style={{ fontSize: 11.5 }}>提交後後端會校驗庫存,庫存不足將被拒絕。</div>
          </>
        )}
      </div>
    </div>
  );
};

window.PageOutbound = PageOutbound;
