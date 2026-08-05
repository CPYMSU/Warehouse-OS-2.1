/* ============================================================
   智能數據中轉站 — 上傳任意數據文件(Excel/CSV/JSON/SQLite)→
   AI 在只讀 Python 沙箱裡像 Claude Code 一樣逐步分析結構 →
   給出無損轉換建議 → 確認後落地為平台數據模塊(新建或對接更新)。
   ============================================================ */
const { useState: useStateDH, useEffect: useEffectDH, useRef: useRefDH } = React;

const dhPost = async (url, body) => {
  const res = await (window.authFetch || fetch)(url, body instanceof FormData
    ? { method: "POST", body }
    : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, data };
};

// NDJSON 流式:逐事件回調
async function dhStream(url, payload, onEvent) {
  const res = await (window.authFetch || fetch)(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!res.ok || !res.body) { let m = res.statusText; try { m = (await res.json()).error || m; } catch (e) {} throw new Error(m); }
  const reader = res.body.getReader(); const dec = new TextDecoder(); let buf = "";
  for (;;) {
    const { done, value } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true }); let i;
    while ((i = buf.indexOf("\n")) >= 0) { const ln = buf.slice(0, i).trim(); buf = buf.slice(i + 1); if (ln) { try { onEvent(JSON.parse(ln)); } catch (e) {} } }
  }
}

// 終端裡的一個步驟塊
const DHStep = ({ it }) => {
  if (it.kind === "info") return <div style={{ color: "#94a3b8" }}>{it.text}</div>;
  if (it.kind === "final") return <div style={{ color: "#d1fae5", whiteSpace: "pre-wrap", marginTop: 8, borderTop: "1px solid rgba(125,211,252,0.2)", paddingTop: 8 }}>{it.text}</div>;
  if (it.tool === "run_python") return (
    <div style={{ margin: "8px 0" }}>
      <div style={{ color: "#34d399", fontSize: 12 }}>▸ 運行 Python {it.ok === false ? <span style={{ color: "#f87171" }}>✗</span> : "✓"}</div>
      {it.code && <pre style={{ color: "#7dd3fc", fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: "3px 0", padding: "6px 10px", background: "rgba(125,211,252,0.06)", borderRadius: 8 }}>{it.code}</pre>}
      {it.stdout && <pre style={{ color: "#cbd5e1", fontSize: 12, whiteSpace: "pre-wrap", margin: "2px 0", maxHeight: 160, overflowY: "auto" }}>{it.stdout}</pre>}
      {it.error && <div style={{ color: "#fbbf24", fontSize: 12 }}>{it.error}</div>}
    </div>
  );
  return <div style={{ color: "#7dd3fc", fontSize: 12, margin: "4px 0" }}>▸ {it.tool === "list_target_modules" ? "查看已有模塊" : it.tool === "propose_plan" ? "生成無損轉換計劃" : it.tool}</div>;
};

const PageDataHub = () => {
  const [phase, setPhase] = useStateDH("upload"); // upload | session | done
  const [busy, setBusy] = useStateDH(false);
  const [err, setErr] = useStateDH("");
  const [job, setJob] = useStateDH(null);
  const [items, setItems] = useStateDH([]);        // 終端步驟
  const [plan, setPlan] = useStateDH(null);         // 待確認 datasets:[{...editable}]
  const [committing, setCommitting] = useStateDH(false);
  const [done, setDone] = useStateDH(null);
  const [jobs, setJobs] = useStateDH([]);
  const fileRef = useRefDH(null);
  const termRef = useRefDH(null);

  const loadJobs = () => dhPost("/api/datahub/jobs", {}).catch(() => ({})); // jobs is GET; load below
  useEffectDH(() => {
    (window.authFetch || fetch)("/api/datahub/jobs").then(r => r.json()).then(d => setJobs(d.jobs || [])).catch(() => {});
  }, [done]);
  useEffectDH(() => { if (termRef.current) termRef.current.scrollTop = termRef.current.scrollHeight; }, [items]);

  const push = (it) => setItems((p) => [...p, it]);

  const reset = () => { setPhase("upload"); setJob(null); setItems([]); setPlan(null); setDone(null); setErr(""); };

  // 把 AI proposal(或啟發式兜底)轉成可確認的 datasets
  const toPlan = (proposal, analyzeData) => {
    if (proposal && (proposal.datasets || []).length) {
      return proposal.datasets.map((d) => ({
        name: d.source, include: true, mode: d.mode === "append" ? "append" : "new",
        module_key: d.module_key || "", module_name: d.module_name || d.source,
        dedup_key: d.dedup_key || "", fields: d.fields || [],
      }));
    }
    // 兜底:用 analyze 的啟發式 proposed
    return (analyzeData.datasets || []).map((d) => ({
      name: d.name, include: true, mode: "new", module_key: "",
      module_name: d.proposed.module_name, dedup_key: "", fields: d.proposed.fields,
    }));
  };

  const onPick = (file) => {
    if (!file) return;
    reset(); setBusy(true); setPhase("session");
    push({ kind: "info", text: "📤 正在上傳並解析文件…" });
    const fd = new FormData(); fd.append("file", file);
    dhPost("/api/datahub/analyze", fd).then(({ ok, data }) => {
      if (!ok) throw new Error(data.error || "解析失敗");
      setJob(data);
      if (data.vision_note) push({ kind: "info", text: "🖼 " + data.vision_note });
      push({ kind: "info", text: `🐍 Python 已加載 · 識別到 ${data.datasets.length} 個數據表(${data.kind})· AI 開始分析…` });
      // 流式跑 AI 分析智能體
      return dhStream("/api/datahub/agent/stream", { job_id: data.job_id }, (e) => {
        if (e.event === "step" || e.event === "step_start") {
          if (e.event === "step") push({ tool: e.tool, code: e.code, ok: e.ok, stdout: e.stdout, error: e.error, result: e.result });
        } else if (e.event === "final") {
          if (e.degraded) push({ kind: "info", text: "⚠ AI 引擎未配置,已退回快速識別(可直接確認落地)。" });
          if (e.message) push({ kind: "final", text: e.message });
          setPlan(toPlan(e.proposal, data));
        } else if (e.event === "error") {
          push({ kind: "info", text: "✗ " + (e.error || "分析出錯") });
          setPlan(toPlan(null, data)); // 退回兜底
        }
      });
    }).catch((e) => { setErr(e.message || String(e)); }).finally(() => setBusy(false));
  };

  const patch = (i, p) => setPlan((pl) => pl.map((d, idx) => idx === i ? { ...d, ...p } : d));

  const commit = () => {
    const chosen = (plan || []).filter((d) => d.include);
    if (!chosen.length) { setErr("請至少勾選一個數據表"); return; }
    setCommitting(true); setErr("");
    dhPost("/api/datahub/commit", { job_id: job.job_id, datasets: plan }).then(({ ok, data }) => {
      if (!ok) throw new Error(data.error || "落地失敗");
      setDone(data); setPhase("done");
      if (window.reloadData) window.reloadData();
    }).catch((e) => setErr(e.message || String(e))).finally(() => setCommitting(false));
  };

  return (
    <div className="col gap-18">
      <PageHead title="智能數據中轉站" sub="上傳任意數據文件 → AI 用 Python 逐步分析結構與內容(僅分析,不建表;要建記錄請到庫存/ERP)"
        actions={phase !== "upload" && <button className="btn btn-sm" onClick={reset}>重新開始</button>}/>
      {err && <div className="card" style={{ padding: 12, color: "var(--danger)", fontWeight: 700, fontSize: 13 }}>⚠ {err}</div>}

      {phase === "upload" && (
        <div className="card col center gap-12" style={{ padding: 40, border: "2px dashed var(--line)", textAlign: "center" }}
          onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); onPick(e.dataTransfer.files[0]); }}>
          <div style={{ width: 56, height: 56, borderRadius: 16, background: "var(--grad-soft)", display: "grid", placeItems: "center" }}><Icon name="inbound" size={26} color="var(--blue)"/></div>
          <div style={{ fontSize: 15, fontWeight: 800 }}>拖入文件,或點擊選擇</div>
          <div className="muted" style={{ fontSize: 12.5 }}>支持 Excel(.xlsx/.xls)、CSV、JSON、SQLite(.db),以及<b>圖片(.jpg/.png)</b>。圖片會自動識別出其中的表格,再交給智能分析引擎處理。</div>
          <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv,.json,.db,.sqlite,.db3,.sqlite3,.jpg,.jpeg,.png,.webp,.bmp" style={{ display: "none" }} onChange={(e) => onPick(e.target.files[0])}/>
          <button className="btn btn-primary" onClick={() => fileRef.current && fileRef.current.click()}>選擇文件</button>
        </div>
      )}

      {(phase === "session" || phase === "done") && (
        <div ref={termRef} style={{
          borderRadius: 14, border: "1px solid rgba(125,211,252,0.18)", background: "#0b1220",
          padding: "14px 16px", maxHeight: "42vh", overflowY: "auto",
          fontFamily: "ui-monospace, SFMono-Regular, Consolas, Menlo, monospace", fontSize: 13, lineHeight: 1.6,
        }}>
          {items.map((it, i) => <DHStep key={i} it={it}/>)}
          {busy && <div style={{ color: "#7dd3fc" }}>… AI 分析中</div>}
        </div>
      )}

      {/* AI 分析結果(只讀;數據中轉站僅分析,不再落地建獨立表) */}
      {phase === "session" && plan && (
        <div className="col gap-12">
          <div className="card col gap-6" style={{ padding: 14, borderLeft: "3px solid var(--blue)" }}>
            <div style={{ fontWeight: 800, fontSize: 13.5 }}>AI 識別到的數據結構(僅分析)</div>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.55 }}>數據中轉站只做分析,不會生成獨立數據表。要把這些數據建成正式記錄,請到「庫存管理」(新增物資 / 管理分類)或 ERP 錄入,讓數據正確歸位。</div>
          </div>
          {plan.map((d, i) => (
            <div key={i} className="card col gap-8" style={{ padding: 16 }}>
              <div className="row gap-8" style={{ alignItems: "center", flexWrap: "wrap" }}>
                <span style={{ fontWeight: 800, fontSize: 13.5 }}>數據表「{d.name}」</span>
                <span className="muted" style={{ fontSize: 11.5 }}>{(d.fields || []).length} 個字段</span>
              </div>
              <div className="muted" style={{ fontSize: 11.5 }}>字段:{(d.fields || []).map((f) => (f.label || f.source) + (f.type ? `(${f.type})` : "")).join("、")}</div>
            </div>
          ))}
        </div>
      )}

      {/* 歷史 */}
      {phase === "upload" && jobs.length > 0 && (
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: 13.5, fontWeight: 800, marginBottom: 8 }}>轉換歷史</div>
          <div className="col gap-6">
            {jobs.map((j) => (
              <div key={j.id} className="row spread" style={{ fontSize: 12.5, padding: "6px 0", borderTop: "1px solid var(--line)" }}>
                <span>{j.filename} <span className="num muted">· {j.kind}</span></span>
                <span className="muted">{j.status === "committed" ? `已轉換 ${(j.result || []).reduce((a, m) => a + (m.imported || 0), 0)} 行` : j.status} · {j.created_at}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

window.PageDataHub = PageDataHub;
