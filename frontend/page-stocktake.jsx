/* ============================================================
   6 · 盤點管理
   ============================================================ */
const { useState: useStateSt } = React;
const STOCKTAKE_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const CreateStocktakeModal = ({ onClose }) => {
  const [f, setF] = useStateSt({ task_name: "", area: "", owner: "", total_count: "" });
  const [busy, setBusy] = useStateSt(false);
  const [error, setError] = useStateSt("");
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = () => {
    if (!f.task_name.trim()) { setError("請填寫任務名稱"); return; }
    setBusy(true); setError("");
    (window.authFetch || fetch)(`${STOCKTAKE_API_BASE}/api/stocktake`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_name: f.task_name.trim(), area: f.area || null, owner: f.owner || null, total_count: f.total_count === "" ? 0 : Number(f.total_count) }),
    })
      .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
      .then(({ ok, d }) => { if (!ok) throw new Error(d.error || "創建失敗"); if (window.reloadData) window.reloadData(); onClose(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };
  return (
    <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
      <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); submit(); }} className="card col gap-14" style={{ width: "min(440px, 100%)", padding: 24 }}>
        <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>新建盤點任務</div>
          <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>任務名稱
          <input className="input" value={f.task_name} onChange={up("task_name")} placeholder="例如:2026 年 6 月全庫盤點"/></label>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>盤點區域
            <input className="input" value={f.area} onChange={up("area")} placeholder="例如:A 區 / 全庫"/></label>
          <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>負責人
            <input className="input" value={f.owner} onChange={up("owner")}/></label>
        </div>
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>計劃盤點品類數
          <input className="input" type="number" min="0" value={f.total_count} onChange={up("total_count")} placeholder="可選"/></label>
        {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
        <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 42 }}>{busy ? "創建中…" : "創建任務"}</button>
      </form>
    </div>
  );
};

const PageStocktake = () => {
  const [showCreate, setShowCreate] = useStateSt(false);
  const stMap = { "已完成": "badge-ok", "進行中": "badge-info", "未開始": "badge-gray" };
  const diffStMap = { "待處理": "badge-warn", "已調整": "badge-ok" };
  const tasks = window.STOCKTAKE || [];
  const diffs = window.STOCKTAKE_DIFF || [];
  const overall = tasks.length ? Math.round(tasks.reduce((s,t)=>s+t.progress,0)/tasks.length) : 0;
  const doneItems = tasks.reduce((s,t)=>s+Number(t.done || 0),0);

  return (
    <div className="col gap-18">
      <PageHead title="盤點管理" sub="定期盤點 · 掃碼核對 · 差異分析"
        actions={<>
          <button className="btn btn-sm"><Icon name="scan" size={15}/>掃碼盤點</button>
          <button className="btn btn-primary btn-sm" onClick={() => setShowCreate(true)}><Icon name="plus" size={15}/>新建盤點任務</button>
        </>}/>
      {showCreate && <CreateStocktakeModal onClose={() => setShowCreate(false)}/>}

      {/* 總進度 */}
      <div className="card fade-up" style={{ padding: 22, display: "flex", gap: 28, alignItems: "center" }}>
        <Ring value={overall} size={120} stroke={12} sub="整體進度"/>
        <div style={{ flex: 1, display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 20 }}>
          {[["盤點任務", tasks.length || "—", "個", "var(--blue)"], ["進行中", tasks.filter(t=>t.status==="進行中").length || "—", "個", "var(--info)"], ["已盤物資", doneItems || "—", "種", "var(--teal)"], ["發現差異", diffs.length || "—", "項", "var(--warn)"]].map(([k,v,u,c],i) => (
            <div key={i} className="col gap-4" style={{ paddingLeft: 16, borderLeft: `3px solid ${c}` }}>
              <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{k}</span>
              <span className="num" style={{ fontSize: 28, fontWeight: 700 }}>{v}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 3 }}>{u}</span></span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.3fr 1fr", gap: 18, alignItems: "flex-start" }}>
        {/* 任務卡片 */}
        <div className="col gap-14">
          <div className="sec-title">盤點任務</div>
          {tasks.map((t,i) => (
            <div key={t.id} className="card fade-up" style={{ padding: 18, animationDelay: i*.05+"s" }}>
              <div className="row spread" style={{ marginBottom: 14 }}>
                <div className="col gap-3">
                  <div className="row gap-8"><span style={{ fontSize: 14.5, fontWeight: 700 }}>{t.name}</span><span className={"badge " + stMap[t.status]}>{t.status}</span></div>
                  <div className="num muted" style={{ fontSize: 12 }}>{t.id} · {t.area} · 負責人 {t.owner}</div>
                </div>
                {t.diff > 0 && <span className="badge badge-warn">差異 {t.diff}</span>}
              </div>
              <div className="row spread" style={{ marginBottom: 6, fontSize: 12 }}>
                <span className="muted">完成進度 <b className="num" style={{ color: "var(--ink)" }}>{t.done}/{t.total}</b></span>
                <span className="num" style={{ fontWeight: 700, color: t.progress===100?"var(--ok)":"var(--blue)" }}>{t.progress}%</span>
              </div>
              <div style={{ height: 8, borderRadius: 4, background: "#EEF2F7", overflow: "hidden" }}>
                <div style={{ height: "100%", width: t.progress+"%", borderRadius: 4, background: t.progress===100?"var(--ok)":"var(--grad)", transition: "width .8s ease" }}/>
              </div>
            </div>
          ))}
        </div>

        {/* 區域地圖 + 差異明細 */}
        <div className="col gap-18">
          <div className="card fade-up" style={{ padding: 20, animationDelay: ".1s" }}>
            <SecHead title="盤點區域進度" sub="按倉庫區域"/>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 8 }}>
              {window.ZONES.map(z => {
                const task = tasks.find(t => t.area.startsWith(z.id+"區"));
                const p = task ? task.progress : (z.id==="B"||z.id==="D"||z.id==="E"||z.id==="H" ? 100 : 0);
                return (
                  <div key={z.id} title={z.name} style={{ aspectRatio: "1", borderRadius: 11, display: "grid", placeItems: "center", position: "relative", overflow: "hidden",
                    background: p===100 ? "var(--ok-soft)" : p>0 ? "var(--info-soft)" : "var(--surface-2)", border: "1px solid var(--line)" }}>
                    <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: p+"%", background: p===100?"rgba(16,185,129,0.16)":"rgba(59,130,246,0.14)", transition: "height .8s ease" }}/>
                    <span className="num" style={{ fontSize: 18, fontWeight: 800, color: p===100?"var(--ok)":p>0?"var(--info)":"var(--ink-4)", zIndex: 1 }}>{z.id}</span>
                  </div>
                );
              })}
            </div>
            <div className="row gap-16" style={{ marginTop: 14, fontSize: 11.5, color: "var(--ink-3)" }}>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "var(--ok)" }}/>已完成</span>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "var(--info)" }}/>進行中</span>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "#CBD5E3" }}/>未開始</span>
            </div>
          </div>

          <div className="card fade-up" style={{ padding: 0, overflow: "hidden", animationDelay: ".16s" }}>
            <div className="row spread" style={{ padding: "18px 20px 14px" }}><span className="sec-title">差異明細</span><span className="badge badge-warn">{diffs.length || "—"} 項</span></div>
            <table className="tbl">
              <thead><tr><th>物資</th><th>賬面</th><th>實際</th><th>差異</th><th>狀態</th></tr></thead>
              <tbody>
                {diffs.map((d,i) => (
                  <tr key={i}>
                    <td><div className="col gap-2"><span style={{ fontWeight: 600 }}>{d.item}</span><span className="muted" style={{ fontSize: 11.5 }}>{d.reason}</span></div></td>
                    <td className="num">{d.book}</td>
                    <td className="num">{d.real}</td>
                    <td><span className="num" style={{ fontWeight: 700, color: d.diff<0?"var(--danger)":"var(--ok)" }}>{d.diff>0?"+":""}{d.diff}</span></td>
                    <td><span className={"badge " + diffStMap[d.status]}>{d.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

window.PageStocktake = PageStocktake;
