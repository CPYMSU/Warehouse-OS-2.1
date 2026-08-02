/* Warehouse Browser Runtime · governed real-browser execution and evidence. */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { useState: S, useEffect: E, useCallback: C } = React;
const { Icon: I, Btn: B, Label: L, Empty: EmptyState } = W2;

window.W2_LANG.addEN({
  "瀏覽器執行層": "Browser Runtime",
  "像使用者一樣巡檢前端,每一步都有可覆核證據": "Inspect the frontend like a user, with reviewable evidence at every step",
  "快速巡檢": "Quick smoke",
  "導航巡檢": "Navigation sweep",
  "工作進程": "Workers",
  "在線": "online",
  "允許網域": "Allowed origins",
  "受控動作": "Governed actions",
  "最近執行": "Recent runs",
  "重整": "Refresh",
  "安全協議": "Safety protocol",
  "只接受語義定位器,禁止任意 JavaScript 與跨域跳轉。預設攔截所有寫請求。": "Semantic locators only. Arbitrary JavaScript and cross-origin navigation are forbidden. Writes are blocked by default.",
  "可重用旅程": "Reusable journeys",
  "尚無瀏覽器執行紀錄": "No browser runs yet",
  "按「快速巡檢」建立第一份真實瀏覽器證據。": "Start Quick smoke to create the first real-browser evidence set.",
  "步驟": "Steps",
  "失敗": "failed",
  "證據": "Evidence",
  "下載": "Download",
  "取消執行": "Cancel run",
  "啟動失敗": "Start failed",
  "執行詳情": "Run detail",
});

const iso = value => value ? String(value).replace("T", " ").slice(0, 19) : "—";
const active = state => ["queued", "claimed", "running"].includes(String(state));
const statusLabel = value => ({ queued:"QUEUED", claimed:"CLAIMED", running:"RUNNING", succeeded:"PASSED", failed:"FAILED", cancelled:"CANCELLED", timed_out:"TIMED OUT" }[value] || String(value || "—").toUpperCase());
const Status = ({ value }) => <span className="br-status" data-state={value}>{statusLabel(value)}</span>;
const uid = value => String(value || "").slice(0, 8).toUpperCase();

const QUICK_STEPS = [
  { action:"navigate", path:"/#/dashboard" },
  { action:"wait", milliseconds:700 },
  { action:"observe", kind:"no_console_errors" },
  { action:"observe", kind:"no_failed_requests" },
  { action:"screenshot", full_page:true },
];
const SWEEP_STEPS = ["dashboard", "tasks", "procurement", "finance", "settings"].flatMap(route => [
  { action:"navigate", path:`/#/${route}`, note:`Open ${route}` },
  { action:"wait", milliseconds:450 },
  { action:"screenshot", full_page:true },
]).concat([
  { action:"observe", kind:"no_console_errors" },
  { action:"observe", kind:"no_failed_requests" },
]);

const downloadArtifact = async artifact => {
  const response = await W2.fetch(`/api/browser-runtime/artifacts/${artifact.id}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href; link.download = String(artifact.relative_path || "browser-evidence").split("/").pop();
  document.body.appendChild(link); link.click(); link.remove();
  window.setTimeout(() => URL.revokeObjectURL(href), 1000);
};

const RunDetail = ({ value, onCancel }) => {
  if (!value) return null;
  const run = value.run || {};
  return <section className="br-detail">
    <div className="br-detail-head">
      <div><L dim>{t("執行詳情")} · {uid(run.id)}</L><h3>{run.name || "Browser run"}</h3></div>
      <div className="br-head-actions"><Status value={run.status}/>{active(run.status) && <B small icon="close" onClick={() => onCancel(run.id)}>{t("取消執行")}</B>}</div>
    </div>
    <div className="br-timeline">
      {(value.steps || []).map(step => <div className="br-event" key={step.id}>
        <span className="br-event-index">{String(step.ordinal).padStart(2,"0")}</span>
        <Status value={step.status}/>
        <div className="br-event-body">
          <b>{String(step.action || "").toUpperCase()}</b>
          <p>{step.error || (step.observation && step.observation.url) || "—"}</p>
          {!!((step.observation || {}).evidence || []).length && <div className="row g8" style={{marginTop:7}}>{step.observation.evidence.map(item => <button className="text-btn" key={item.id} onClick={() => downloadArtifact(item)}>{t("證據")} · {item.kind} ↓</button>)}</div>}
        </div>
      </div>)}
      {!!(value.artifacts || []).length && <div className="br-event">
        <span className="br-event-index">Σ</span><span className="mono muted">FILES</span>
        <div className="br-event-body"><b>{t("證據")}</b><div className="row g8" style={{marginTop:7,flexWrap:"wrap"}}>{value.artifacts.map(item => <button className="text-btn" key={item.id} onClick={() => downloadArtifact(item)}>{item.kind} · {Math.ceil(Number(item.size_bytes || 0)/1024)}KB ↓</button>)}</div></div>
      </div>}
    </div>
  </section>;
};

const Page = () => {
  const [cap, setCap] = S(null);
  const [runs, setRuns] = S([]);
  const [journeys, setJourneys] = S([]);
  const [detail, setDetail] = S(null);
  const [busy, setBusy] = S("");
  const [error, setError] = S("");

  const refresh = C(async () => {
    const [c, r, j] = await Promise.all([
      W2.json("/api/browser-runtime/capabilities"),
      W2.json("/api/browser-runtime/runs?limit=100"),
      W2.json("/api/browser-runtime/journeys?limit=100"),
    ]);
    setCap(c); setRuns(r.runs || []); setJourneys(j.journeys || []);
  }, []);
  E(() => { let live=true; refresh().catch(e => live && setError(e.message)); const timer=setInterval(() => { if (!document.hidden) refresh().catch(()=>{}); },5000); return()=>{live=false;clearInterval(timer);}; }, [refresh]);
  E(() => { const id=detail && detail.run && detail.run.id; if (!id || !active(detail.run.status)) return; const timer=setInterval(()=>W2.json(`/api/browser-runtime/runs/${id}`).then(setDetail).then(refresh).catch(()=>{}),1800); return()=>clearInterval(timer); }, [detail && detail.run && detail.run.id, detail && detail.run && detail.run.status, refresh]);

  const open = async id => { setError(""); try { setDetail(await W2.json(`/api/browser-runtime/runs/${id}`)); } catch(e){setError(e.message);} };
  const start = async (kind, steps) => { setBusy(kind); setError(""); try { const result=await W2.post("/api/browser-runtime/runs",{name:kind==="quick"?"Frontend quick smoke":"Core navigation sweep",mode:kind==="quick"?"smoke":"full",auth_mode:"actor",mutation_policy:"read_only",start_path:"/#/dashboard",steps}); await refresh(); await open(result.run.id); } catch(e){setError(`${t("啟動失敗")}: ${e.message}`);} finally {setBusy("");} };
  const cancel = async id => { try { await W2.post(`/api/browser-runtime/runs/${id}/cancel`,{}); await open(id); await refresh(); } catch(e){setError(e.message);} };
  const workers=(cap && cap.workers) || []; const online=workers.filter(w=>w.online).length;
  const passed=runs.filter(r=>r.status==="succeeded").length; const failed=runs.filter(r=>["failed","timed_out"].includes(r.status)).length;

  return <div className="br-runtime">
    <W2.Folio no="20" en="BROWSER RUNTIME" title={t("瀏覽器執行層")} sub={t("像使用者一樣巡檢前端,每一步都有可覆核證據")} right={<div className="br-head-actions"><B icon="play" primary disabled={!!busy || !(cap && cap.available)} onClick={()=>start("quick",QUICK_STEPS)}>{busy==="quick"?"RUNNING…":t("快速巡檢")}</B><B icon="layers" disabled={!!busy || !(cap && cap.available)} onClick={()=>start("sweep",SWEEP_STEPS)}>{busy==="sweep"?"RUNNING…":t("導航巡檢")}</B><B icon="refresh" onClick={()=>refresh().catch(e=>setError(e.message))}>{t("重整")}</B></div>}/>
    {error && <div className="br-error" role="alert">{error}</div>}
    <div className="br-kpis rise">
      <div className="br-kpi"><small>{t("工作進程")}</small><strong>{online}/{workers.length}</strong><span>{t("在線")}</span></div>
      <div className="br-kpi"><small>RUNS</small><strong>{runs.length}</strong><span>{t("最近執行")}</span></div>
      <div className="br-kpi"><small>PASSED</small><strong>{passed}</strong><span>SHA-256 EVIDENCE</span></div>
      <div className="br-kpi"><small>{t("失敗")}</small><strong>{failed}</strong><span>CONSOLE · NETWORK · DOM</span></div>
    </div>
    <W2.Band no="A" title={t("安全協議")} sub={(cap && cap.protocol) || "warehouse-browser-steps/v1"}>
      <div className="br-protocol">
        <div className="br-protocol-side"><b>PLAYWRIGHT · CHROMIUM</b><p>{t("只接受語義定位器,禁止任意 JavaScript 與跨域跳轉。預設攔截所有寫請求。")}</p></div>
        <div className="br-steps">{((cap && cap.actions) || []).map(action=><span className="br-step-token" key={action}>{action}</span>)}</div>
      </div>
    </W2.Band>
    <W2.Band no="B" title={t("最近執行")} sub={`${runs.length} RUNS`}>
      {!runs.length ? <EmptyState title={t("尚無瀏覽器執行紀錄")} text={t("按「快速巡檢」建立第一份真實瀏覽器證據。")} /> : <div className="br-table">{runs.map(run=><div className="br-row" key={run.id} onClick={()=>open(run.id)}><span className="mono">{uid(run.id)}</span><b>{run.name}</b><Status value={run.status}/><span className="mono">{run.step_count || 0} {t("步驟")}</span><span className="mono muted">{iso(run.created_at)}</span><I name="arrow" size={13}/></div>)}</div>}
      <RunDetail value={detail} onCancel={cancel}/>
    </W2.Band>
    <W2.Band no="C" title={t("可重用旅程")} sub={`${journeys.length} JOURNEYS`}>
      <details className="br-journeys"><summary><span>{t("可重用旅程")}</span><span>＋ / −</span></summary>{journeys.length?journeys.map(j=><div className="br-journey" key={j.id}><div><b>{j.name}</b><div className="mono muted" style={{marginTop:5}}>{j.journey_key} · V{j.version}</div></div><button className="text-btn" onClick={()=>start("journey",j.steps)}>RUN →</button></div>):<div className="br-journey muted">EMPTY · 可由 AI 或超級終端建立</div>}</details>
    </W2.Band>
  </div>;
};

window.W2.PAGES["browser"] = Page;
})();
