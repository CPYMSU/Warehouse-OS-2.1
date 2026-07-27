/* ============================================================
   操作日誌 — 全流程時間戳 / 操作人 / 權限留痕
   ============================================================ */
const { useEffect: useLogEffect, useMemo: useLogMemo, useState: useLogState } = React;

const AUDIT_API = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const fmtLogValue = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value, null, 2);
  return String(value);
};

const actionLabel = (action) => ({
  create_inbound_order: "新增入庫",
  create_outbound_order: "新增出庫",
  save_settings: "保存設置",
  invoke_ai_database_hook: "AI Action 調用",
  write_audit_log: "寫入日誌",
  deepseek_fallback: "AI 解析降級",
}[action] || action || "—");

const sourceBadge = (source) => {
  if (source === "ai") return "badge-purple";
  if (source === "user") return "badge-info";
  return "badge-gray";
};

const statusBadge = (status) => {
  if (status === "executed" || status === "completed") return "badge-ok";
  if (status === "pending") return "badge-warn";
  if (status === "failed" || status === "error") return "badge-danger";
  return "badge-gray";
};

const CLI_KIND_STYLE = {
  "SQL 終端": { color: "#E0245E", icon: "database" },
  "Python 腳本": { color: "#E0245E", icon: "terminal" },
  "CLI 指令": { color: "#E8830C", icon: "command" },
  "平台終端": { color: "#E8830C", icon: "server" },
  "被拒絕": { color: "#EF4444", icon: "alert" },
  "只讀查詢": { color: "#6B7A90", icon: "search" },
};

const CliAuditView = () => {
  const [rows, setRows] = useLogState([]);
  const [summary, setSummary] = useLogState({});
  const [busy, setBusy] = useLogState(true);
  const [err, setErr] = useLogState("");
  const [q, setQ] = useLogState("");
  const [kind, setKind] = useLogState("");
  const [days, setDays] = useLogState("30");
  const [reads, setReads] = useLogState(true);
  const [open, setOpen] = useLogState(null);

  const load = () => {
    setBusy(true); setErr("");
    const qs = new URLSearchParams({ limit: "800" });
    if (q.trim()) qs.set("q", q.trim());
    if (kind) qs.set("kind", kind);
    if (days) qs.set("days", days);
    if (!reads) qs.set("reads", "0");
    (window.authFetch || fetch)(`${AUDIT_API}/api/audit/cli?${qs.toString()}`)
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((data) => { setRows(data.rows || []); setSummary(data.summary || {}); })
      .catch((e) => setErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };
  useLogEffect(() => { load(); }, [kind, days, reads]);

  const cards = [
    { label: "高危執行", value: summary.total || 0, unit: "次", icon: "shield", color: "var(--blue)" },
    { label: "寫庫操作", value: summary.writes || 0, unit: "次", icon: "edit", color: "var(--teal)" },
    { label: "被拒絕(越權)", value: summary.denied || 0, unit: "次", icon: "alert", color: "var(--danger)" },
    { label: "涉及人員", value: summary.operators || 0, unit: "人", icon: "users", color: "var(--purple)" },
  ];

  return (
    <div className="col gap-18">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14 }}>
        {cards.map((s, i) => (
          <div key={s.label} className="card fade-up row gap-12" style={{ padding: 18, animationDelay: `${i * .04}s` }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", background: "var(--surface-2)" }}>
              <Icon name={s.icon} size={21} color={s.color}/>
            </div>
            <div className="col gap-3">
              <span className="muted" style={{ fontSize: 12 }}>{s.label}</span>
              <span className="num" style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.value}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 3 }}>{s.unit}</span></span>
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: 14 }}>
        <div className="row gap-8" style={{ flexWrap: "wrap", alignItems: "center" }}>
          <input className="input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load(); }}
            placeholder="搜索操作人 / 指令內容…" style={{ width: 220, height: 32 }}/>
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)} style={{ width: 130, height: 32 }}>
            <option value="">全部類型</option>
            <option value="admin_sql">SQL 終端</option>
            <option value="run_script">Python 腳本</option>
            <option value="cli_exec">CLI 指令</option>
            <option value="platform_cli_exec">平台終端</option>
            <option value="cli_denied">被拒絕(越權)</option>
            <option value="db_query">只讀查詢</option>
          </select>
          <select className="input" value={days} onChange={(e) => setDays(e.target.value)} style={{ width: 110, height: 32 }}>
            <option value="1">近 1 天</option>
            <option value="7">近 7 天</option>
            <option value="30">近 30 天</option>
            <option value="90">近 90 天</option>
            <option value="">全部</option>
          </select>
          <label className="row gap-6" style={{ fontSize: 12.5, cursor: "pointer" }}>
            <input type="checkbox" checked={reads} onChange={(e) => setReads(e.target.checked)}/>含只讀查詢
          </label>
          <button className="btn btn-primary btn-sm" onClick={load} disabled={busy}><Icon name="refresh" size={15}/>{busy ? "讀取中…" : "刷新"}</button>
          {summary.by_kind && Object.keys(summary.by_kind).length > 0 && (
            <div className="row gap-6" style={{ marginLeft: "auto", flexWrap: "wrap" }}>
              {Object.entries(summary.by_kind).map(([k, c]) => (
                <span key={k} className="badge" style={{ height: 19, fontSize: 10.5, color: (CLI_KIND_STYLE[k] || {}).color || "#6B7A90", background: ((CLI_KIND_STYLE[k] || {}).color || "#6B7A90") + "18" }}>{k} {c}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      {err && <div className="card" style={{ padding: 14, color: "var(--danger)", borderColor: "rgba(239,68,68,.22)" }}>讀取失敗：{err}</div>}

      <div className="card fade-up table-scroll" style={{ padding: 0 }}>
        <table className="tbl">
          <thead>
            <tr><th>時間</th><th>操作人員</th><th>類型</th><th>指令 / SQL / 腳本</th><th>寫庫</th><th>狀態</th><th>詳情</th></tr>
          </thead>
          <tbody>
            {!rows.length && (
              <tr><td colSpan="7" className="muted" style={{ textAlign: "center", padding: 28 }}>{busy ? "正在讀取…" : "該範圍內暫無高危 CLI 操作"}</td></tr>
            )}
            {rows.map((r) => {
              const ks = CLI_KIND_STYLE[r.kind] || { color: "#6B7A90", icon: "command" };
              return (
                <React.Fragment key={r.id}>
                  <tr>
                    <td className="num" style={{ whiteSpace: "nowrap" }}>{r.when || "—"}</td>
                    <td>{r.operator || "—"}<div className="num muted" style={{ fontSize: 11.5 }}>{r.role || "—"} · L{r.level ?? "?"}</div></td>
                    <td><span className="badge" style={{ color: ks.color, background: ks.color + "1c", fontWeight: 700 }}><Icon name={ks.icon} size={12}/> {r.kind}</span></td>
                    <td style={{ maxWidth: 360 }}>
                      <code style={{ fontSize: 11.5, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", display: "block", maxWidth: 360 }}>{r.command || "—"}</code>
                    </td>
                    <td>{r.write === null ? <span className="muted">—</span> : r.write ? <span className="badge badge-warn">寫</span> : <span className="badge badge-gray">讀</span>}</td>
                    <td><span className={`badge ${statusBadge(r.status)}`}><span className="dot"/>{r.status}</span></td>
                    <td><button className="btn btn-sm" onClick={() => setOpen(open === r.id ? null : r.id)}><Icon name="clipboard" size={14}/>{open === r.id ? "收起" : "查看"}</button></td>
                  </tr>
                  {open === r.id && (
                    <tr>
                      <td colSpan="7" style={{ background: "var(--surface-2)", padding: 16 }}>
                        <div className="col gap-10">
                          <div className="card" style={{ padding: 12, boxShadow: "none" }}>
                            <div className="eyebrow" style={{ marginBottom: 8 }}>完整指令</div>
                            <pre className="muted" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, lineHeight: 1.5, maxHeight: 260, overflow: "auto", margin: 0 }}>{r.command || "—"}</pre>
                          </div>
                          <div className="row gap-8" style={{ flexWrap: "wrap" }}>
                            {r.detail && r.detail.missing_permission && <span className="badge badge-danger">缺權限：{r.detail.missing_permission}</span>}
                            {r.detail && r.detail.backup && <span className="badge badge-info">已備份：{r.detail.backup}</span>}
                            {r.detail && r.detail.exit_code !== null && r.detail.exit_code !== undefined && <span className="badge badge-gray">退出碼 {r.detail.exit_code}</span>}
                            {r.detail && r.detail.api && <span className="badge badge-gray">{r.detail.api}</span>}
                            {r.detail && r.detail.mode && <span className="badge badge-gray">模式 {r.detail.mode}</span>}
                            <span className="badge badge-gray">來源 {r.source || "—"}</span>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const PageAuditLogs = () => {
  const [tab, setTab] = useLogState("all");
  const [rows, setRows] = useLogState([]);
  const [summary, setSummary] = useLogState({});
  const [busy, setBusy] = useLogState(true);
  const [err, setErr] = useLogState("");
  const [q, setQ] = useLogState("");
  const [open, setOpen] = useLogState(null);

  const load = () => {
    setBusy(true);
    setErr("");
    const url = `${AUDIT_API}/api/audit/logs?limit=500${q.trim() ? `&q=${encodeURIComponent(q.trim())}` : ""}`;
    (window.authFetch || fetch)(url)
      .then((res) => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((data) => {
        setRows(data.rows || []);
        setSummary(data.summary || {});
      })
      .catch((error) => setErr(error.message || String(error)))
      .finally(() => setBusy(false));
  };

  useLogEffect(() => { load(); }, []);

  const stats = useLogMemo(() => {
    const deletes = rows.filter((r) => r.deleted_at || /^delete|remove|disable/.test(r.action || "")).length;
    const updates = rows.filter((r) => r.updated_at || /^update|save/.test(r.action || "")).length;
    return [
      { label: "日誌總數", value: summary.total || rows.length, unit: "條", icon: "clipboard", color: "var(--blue)" },
      { label: "寫庫操作", value: summary.writes || 0, unit: "次", icon: "edit", color: "var(--teal)" },
      { label: "修改記錄", value: updates, unit: "次", icon: "refresh", color: "var(--purple)" },
      { label: "刪除/停用", value: deletes, unit: "次", icon: "alert", color: "var(--danger)" },
    ];
  }, [rows, summary]);

  return (
    <div className="col gap-18">
      <PageHead title="操作日誌 · 全流程留痕" sub="時間戳 · 操作人員 · 權限快照 · 新增 / 修改 / 刪除 / AI Action 寫庫記錄"
        actions={
          <div className="row gap-8" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
            {tab === "all" && <input className="input" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") load(); }}
              placeholder="搜索操作人、動作、單號…" style={{ width: 220, height: 32 }}/>}
            {tab === "all" && <button className="btn btn-primary btn-sm" onClick={load} disabled={busy}><Icon name="refresh" size={15}/>{busy ? "讀取中…" : "刷新"}</button>}
          </div>
        }/>

      <div className="row gap-4" style={{ background: "var(--surface-2)", borderRadius: 11, padding: 4, alignSelf: "flex-start" }}>
        {[["all", "全部留痕", "clipboard"], ["cli", "高危 CLI 審計", "shield"]].map(([k, label, icon]) => (
          <button key={k} className={`btn btn-sm ${tab === k ? "btn-primary" : ""}`} onClick={() => setTab(k)}
            style={{ background: tab === k ? undefined : "transparent", boxShadow: tab === k ? undefined : "none" }}>
            <Icon name={icon} size={14}/>{label}
          </button>
        ))}
      </div>

      {tab === "cli" && <CliAuditView/>}
      {tab === "all" && (
        <React.Fragment>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14 }}>
        {stats.map((s, i) => (
          <div key={s.label} className="card fade-up row gap-12" style={{ padding: 18, animationDelay: `${i * .04}s` }}>
            <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center", background: "var(--surface-2)" }}>
              <Icon name={s.icon} size={21} color={s.color}/>
            </div>
            <div className="col gap-3">
              <span className="muted" style={{ fontSize: 12 }}>{s.label}</span>
              <span className="num" style={{ fontSize: 24, fontWeight: 800, color: s.color }}>{s.value}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 3 }}>{s.unit}</span></span>
            </div>
          </div>
        ))}
      </div>

      {err && <div className="card" style={{ padding: 14, color: "var(--danger)", borderColor: "rgba(239,68,68,.22)" }}>日誌讀取失敗：{err}</div>}

      <div className="card fade-up table-scroll" style={{ padding: 0 }}>
        <div className="row spread" style={{ padding: "18px 22px 14px", minWidth: 980 }}>
          <div className="row gap-10">
            <Icon name="clock" size={18} color="var(--blue)"/>
            <span className="sec-title">資料庫操作流水</span>
          </div>
          <span className="muted num" style={{ fontSize: 12 }}>最新：{summary.latest || "—"}</span>
        </div>
        <table className="tbl">
          <thead>
            <tr>
              <th>時間戳</th><th>操作人員</th><th>角色 / 權限</th><th>操作類型</th>
              <th>對象</th><th>來源</th><th>狀態</th><th>建立/修改/刪除時間</th><th>詳情</th>
            </tr>
          </thead>
          <tbody>
            {!rows.length && (
              <tr><td colSpan="9" className="muted" style={{ textAlign: "center", padding: 28 }}>{busy ? "正在讀取日誌…" : "暫無日誌記錄"}</td></tr>
            )}
            {rows.map((r) => (
              <React.Fragment key={r.id}>
                <tr>
                  <td className="num">{r.occurred_at || r.created_at || "—"}</td>
                  <td>{r.operator_name || r.actor || "—"}<div className="muted" style={{ fontSize: 11.5 }}>{r.actor || "—"}</div></td>
                  <td>{r.operator_role || "—"}<div className="num muted" style={{ fontSize: 11.5 }}>Level {r.permission_level ?? "—"}</div></td>
                  <td style={{ fontWeight: 700, color: "var(--ink)" }}>{actionLabel(r.action)}</td>
                  <td>{r.entity_type || "—"}<div className="num muted" style={{ fontSize: 11.5 }}>{r.entity_id || "—"}</div></td>
                  <td><span className={`badge ${sourceBadge(r.source)}`}>{r.source || "system"}</span></td>
                  <td><span className={`badge ${statusBadge(r.operation_status)}`}><span className="dot"/>{r.operation_status || "completed"}</span></td>
                  <td className="num muted">建 {r.created_at || "—"}<div>改 {r.updated_at || "—"} · 刪 {r.deleted_at || "—"}</div></td>
                  <td><button className="btn btn-sm" onClick={() => setOpen(open === r.id ? null : r.id)}><Icon name="clipboard" size={14}/>{open === r.id ? "收起" : "查看"}</button></td>
                </tr>
                {open === r.id && (
                  <tr>
                    <td colSpan="9" style={{ background: "var(--surface-2)", padding: 16 }}>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(260px, 1fr))", gap: 12 }}>
                        {[
                          ["請求", r.request],
                          ["操作前", r.before],
                          ["操作後", r.after],
                          ["權限快照", r.permission_snapshot],
                        ].map(([label, value]) => (
                          <div key={label} className="card" style={{ padding: 12, boxShadow: "none" }}>
                            <div className="eyebrow" style={{ marginBottom: 8 }}>{label}</div>
                            <pre className="muted" style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, lineHeight: 1.5, maxHeight: 220, overflow: "auto" }}>{fmtLogValue(value)}</pre>
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
        </React.Fragment>
      )}
    </div>
  );
};

window.PageAuditLogs = PageAuditLogs;
