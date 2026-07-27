/* ============================================================
   平臺終端 — WCS 統一指令集 + AI 會話模式(P3.5)
   兩種用法:
   ① 指令模式(wh>):直接輸入 WCS 指令,Tab 補全,↑↓ 歷史。
   ② AI 會話模式(ai>):輸入 ai 進入;之後直接說自然語言,AI 內核
      像 Claude Code 一樣實時逐步執行平臺指令(流式回顯每一步);
      多輪連續對話;!開頭直通原始指令;new 開新對話;exit 退出。
   同一指令集、同一權限、同一審計(/api/cli/exec 與 /api/agent/run/stream)。
   ============================================================ */
const TERM_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

async function termExec(fetchFn, url, body) {
  const res = await fetchFn(url, {
    method: "POST",
    body: JSON.stringify(body),
  });
  return res.json();
}

// NDJSON 流式:逐事件回調(AI 會話用)
async function termStream(fetchFn, url, payload, onEvent) {
  const res = await fetchFn(url, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;
      try { onEvent(JSON.parse(line)); } catch (e) {}
    }
  }
}

// 結果裡常見的「行集」:{rows:[...]} 或 data 本身是對象數組
const termRowsOf = (data) => {
  if (Array.isArray(data)) return data.every((r) => r && typeof r === "object" && !Array.isArray(r)) ? data : null;
  if (data && Array.isArray(data.rows)) return data.rows;
  return null;
};

const TermTable = ({ rows }) => {
  const MAX_ROWS = 30, MAX_COLS = 9;
  const cols = Object.keys(rows[0] || {}).slice(0, MAX_COLS);
  const shown = rows.slice(0, MAX_ROWS);
  return (
    <div style={{ overflowX: "auto", margin: "6px 0" }}>
      <table style={{ borderCollapse: "collapse", fontSize: 12, whiteSpace: "nowrap" }}>
        <thead>
          <tr>{cols.map((c) => <th key={c} style={{ textAlign: "left", padding: "3px 10px 3px 0", color: "#7dd3fc", borderBottom: "1px solid rgba(125,211,252,0.3)" }}>{c}</th>)}</tr>
        </thead>
        <tbody>
          {shown.map((r, i) => (
            <tr key={i}>{cols.map((c) => <td key={c} style={{ padding: "2px 10px 2px 0", color: "#d1fae5" }}>{r[c] === null || r[c] === undefined ? "—" : String(r[c])}</td>)}</tr>
          ))}
        </tbody>
      </table>
      <div style={{ color: "#64748b", fontSize: 11, marginTop: 3 }}>
        共 {rows.length} 行{rows.length > MAX_ROWS ? `,僅顯示前 ${MAX_ROWS} 行` : ""}{Object.keys(rows[0] || {}).length > MAX_COLS ? ` · 列已截斷至 ${MAX_COLS}` : ""}
      </div>
    </div>
  );
};

// 一次 run 的整體結果(runs show / 非流式 ai)
const classicStepOutcome = (step) => {
  const status = String((step && step.status) || "");
  if (step && step.running) return { mark: "⚙", color: "#7dd3fc", suffix: " · 執行中…", pending: false };
  if (status === "confirmation_required" || status === "pending_confirmation") {
    return { mark: "⏳", color: "#fbbf24", suffix: " · 待確認", pending: true };
  }
  if (status === "partial") return { mark: "⚠", color: "#fbbf24", suffix: " · 部分完成", pending: false };
  if (step && step.ok) return { mark: "✓", color: "#86efac", suffix: "", pending: false };
  return { mark: "✗", color: "#f87171", suffix: "", pending: false };
};

const TermRun = ({ data }) => (
  <div style={{ margin: "4px 0" }}>
    {(data.steps || []).map((s) => {
      const outcome = classicStepOutcome(s);
      return (
        <div key={s.step_no} style={{ fontSize: 12, color: outcome.color }}>
          {outcome.mark} 第{s.step_no}步 <b>{s.command || s.tool_name}</b>
          {s.args && Object.keys(s.args).length ? " " + JSON.stringify(s.args) : ""}
          {outcome.suffix || (typeof s.duration_ms === "number" ? ` · ${s.duration_ms}ms` : "")}
          {!outcome.pending && s.error ? <span style={{ color: "#fbbf24" }}> · {s.error}</span> : null}
        </div>
      );
    })}
    {(data.steps || []).length === 0 && <div style={{ color: "#64748b", fontSize: 12 }}>(本次未調用任何工具)</div>}
    <div style={{ color: "#d1fae5", whiteSpace: "pre-wrap", marginTop: 6 }}>{data.message}</div>
    <div style={{ color: "#64748b", fontSize: 11, marginTop: 4 }}>
      run #{data.run_id} · 引擎 {data.engine === "deepseek" ? "AI 智能引擎" : "規則引擎(非 AI)"} · {data.status}
      {" · "}<span>可用 runs show --id {data.run_id} 回看</span>
    </div>
  </div>
);

// AI 會話:實時單步行(running → 結果)
const TermAiStep = ({ step }) => {
  const outcome = classicStepOutcome(step);
  return (
    <div style={{ fontSize: 12, color: outcome.color }}>
      {outcome.mark} 第{step.step_no}步 <b>{step.command || step.tool_name}</b>
      {step.args && Object.keys(step.args).length ? " " + JSON.stringify(step.args) : ""}
      {outcome.suffix || (typeof step.duration_ms === "number" ? ` · ${step.duration_ms}ms` : "")}
      {!outcome.pending && !step.running && step.error ? <span style={{ color: "#fbbf24" }}> · {step.error}</span> : null}
    </div>
  );
};

const TermHelp = ({ commands }) => (
  <div style={{ margin: "6px 0" }}>
    {commands.map((c) => (
      <div key={c.command} style={{ marginBottom: 7, opacity: c.allowed ? 1 : 0.42 }}>
        <span style={{ color: c.writes ? "#fbbf24" : "#7dd3fc", fontWeight: 700 }}>{c.usage}</span>
        {c.writes && <span style={{ color: "#f87171", fontSize: 10.5, marginLeft: 8, border: "1px solid rgba(248,113,113,0.45)", borderRadius: 4, padding: "0 5px" }}>寫</span>}
        {!c.allowed && <span style={{ color: "#94a3b8", fontSize: 10.5, marginLeft: 8 }}>需 {c.permission}</span>}
        <div style={{ color: "#94a3b8", fontSize: 12 }}>{c.description}</div>
      </div>
    ))}
    <div style={{ color: "#64748b", fontSize: 11.5 }}>本地指令:help(本列表)、clear(清屏)、ai(進入 AI 會話模式)。Tab 補全指令,↑↓ 翻歷史,含空格的值用雙引號。</div>
  </div>
);

// 單條輸出塊
const TermBlock = ({ item }) => {
  if (item.type === "cmd") {
    const isAi = item.prompt === "ai>";
    return <div style={{ color: "#e2e8f0", marginTop: 10 }}><span style={{ color: isAi ? "#c084fc" : "#34d399", fontWeight: 800 }}>{item.prompt || "wh>"}</span> {item.text}</div>;
  }
  if (item.type === "info") return <div style={{ color: "#94a3b8" }}>{item.text}</div>;
  if (item.type === "sql") {
    const r = item.result || {};
    if (r.mode === "read") {
      return (
        <div>
          <div style={{ color: "#34d399", fontSize: 12 }}>✓ 查詢 · {r.count} 行{r.truncated ? "(僅顯示前 500)" : ""}</div>
          {(r.rows || []).length ? <TermTable rows={r.rows}/> : <div style={{ color: "#64748b", fontSize: 12 }}>(空結果集)</div>}
        </div>
      );
    }
    return <div style={{ color: "#fbbf24", fontSize: 12.5 }}>✓ 寫操作完成 · 影響 {r.affected} 行(已提交,已審計)</div>;
  }
  if (item.type === "aistep") return <TermAiStep step={item.step}/>;
  if (item.type === "aifinal") {
    return (
      <div>
        <div style={{ color: "#e9d5ff", whiteSpace: "pre-wrap", marginTop: 5 }}>{item.message}</div>
        <div style={{ color: "#64748b", fontSize: 11, marginTop: 3 }}>
          run #{item.run_id} · {item.engine === "deepseek" ? "AI 智能引擎" : "規則引擎(非 AI)"} · {item.status} · runs show --id {item.run_id} 可回看
        </div>
      </div>
    );
  }
  if (item.type === "error") {
    return (
      <div style={{ color: "#f87171" }}>
        ✗ {item.text}
        {item.usage && <div style={{ color: "#fbbf24", fontSize: 12 }}>用法:{item.usage}</div>}
        {item.hint && <div style={{ color: "#94a3b8", fontSize: 12 }}>{item.hint}</div>}
      </div>
    );
  }
  // result
  const env = item.env || {};
  const data = env.data;
  const rows = termRowsOf(data);
  const pendingConfirmation = env.needs_confirmation === true;
  const partial = env.partial === true;
  const mark = pendingConfirmation ? "⏳" : partial ? "⚠" : "✓";
  const label = pendingConfirmation ? "待確認（未寫庫）" : partial ? "部分完成" : "";
  const color = pendingConfirmation || partial ? "#fbbf24" : "#34d399";
  return (
    <div>
      <div style={{ color, fontSize: 12 }}>
        {mark} {env.command}{label ? " · " + label : ""}{typeof env.status === "number" ? ` · ${env.status}` : ""}{typeof env.elapsed_ms === "number" ? ` · ${env.elapsed_ms}ms` : ""}{env.ok && env.writes ? " · 已寫庫(已審計)" : ""}
      </div>
      {data && data.commands ? <TermHelp commands={data.commands}/>
        : data && Array.isArray(data.steps) && typeof data.run_id === "number" ? <TermRun data={data}/>
        : rows ? <TermTable rows={rows}/>
        : typeof (data && (data.message || data.reply)) === "string" ? <div style={{ color: "#d1fae5", whiteSpace: "pre-wrap", margin: "4px 0" }}>{data.message || data.reply}</div>
        : <pre style={{ color: "#d1fae5", fontSize: 12, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: "4px 0", maxHeight: 360, overflowY: "auto" }}>{JSON.stringify(data, null, 2)}</pre>}
    </div>
  );
};

const TERM_LOCAL_CMDS = ["help", "clear", "ai"];
const TERM_WELCOME = [
  { type: "info", text: "倉儲平臺終端 · WCS 統一指令集 — 輸入 help 查看指令;以你當前賬號的權限執行,寫操作全部記入審計。" },
  { type: "info", text: "輸入 ai 進入 AI 會話模式:直接說自然語言,AI 會實時逐步執行平臺指令(每一步可見、可回放)。" },
  { type: "info", text: "開發模式:sql <語句> 直接操作當前公司數據庫(僅系統管理員,全程審計;DROP/無 WHERE 的 DELETE 等危險操作需改用 sql! 強制)。" },
];

const PageTerminal = ({ cfg }) => {
  // cfg 為空 → 主應用默認(走 window.authFetch + /api/cli/*、當前公司);
  // platform.html 傳入 cfg → 復用同一終端,改走 /api/platform/* 並用公司下拉切換目標公司。
  const C = cfg || {};
  const fetchFn = C.fetch || window.authFetch || ((u, o) => fetch(u, o));
  const apiBase = C.apiBase != null ? C.apiBase : TERM_API_BASE;
  const P = Object.assign(
    { exec: "/api/cli/exec", stream: "/api/agent/run/stream", sql: "/api/admin/sql", commands: "/api/cli/commands" },
    C.paths || {}
  );
  const companies = C.companies || null;        // 有值 → 顯示公司下拉(運營後台模式)
  const title = C.title || "平臺終端";
  const subtitle = C.subtitle || "人與 AI 同一指令集 · 同一權限 · 同一審計";

  const [items, setItems] = React.useState(C.welcome || TERM_WELCOME);
  const [input, setInput] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [aiMode, setAiMode] = React.useState(false);
  const [history, setHistory] = React.useState([]);
  const [slug, setSlug] = React.useState("");   // 運營後台:目標公司(空=平台級)
  const histRef = React.useRef(-1);
  const convRef = React.useRef(null);       // AI 會話的對話 id(多輪連續)
  const cmdCacheRef = React.useRef(null);   // Tab 補全的指令緩存
  const bottomRef = React.useRef(null);
  const inputRef = React.useRef(null);

  // 運營後台模式:把目標公司 slug 併入每個請求體(平台級指令則不帶)
  const slugRef = React.useRef("");
  React.useEffect(() => { slugRef.current = slug; }, [slug]);
  const withTarget = (obj) => (companies ? Object.assign({ tenant_slug: slug || undefined }, obj) : obj);
  const needCompany = () => companies && !slug;   // 運營後台:sql 需先選公司(AI 不選公司=平台級)

  React.useEffect(() => { bottomRef.current && bottomRef.current.scrollIntoView({ block: "end" }); }, [items, busy]);
  React.useEffect(() => {
    const onUserChanged = () => { convRef.current = null; cmdCacheRef.current = null; };
    window.addEventListener("warehouse-user-changed", onUserChanged);
    return () => window.removeEventListener("warehouse-user-changed", onUserChanged);
  }, []);
  // 切換目標公司 → 重置 AI 會話上下文與補全緩存(不同公司不同指令集/數據)
  React.useEffect(() => { convRef.current = null; cmdCacheRef.current = null; }, [slug]);

  const push = (...blocks) => setItems((prev) => [...prev, ...blocks]);

  // step 事件:把對應的「執行中」行原位更新為結果
  const settleStep = (ev) => setItems((prev) => {
    const next = [...prev];
    for (let i = next.length - 1; i >= 0; i--) {
      const it = next[i];
      if (it.type === "aistep" && it.step.step_no === ev.step_no && it.step.running) {
        next[i] = { type: "aistep", step: { ...ev, running: false } };
        return next;
      }
    }
    next.push({ type: "aistep", step: { ...ev, running: false } });
    return next;
  });

  const execCommand = async (text) => {
    setBusy(true);
    try {
      const env = await termExec(fetchFn, apiBase + P.exec, withTarget({ line: text }));
      if (env && (env.ok || env.needs_confirmation || env.partial)) push({ type: "result", env });
      else push({ type: "error", text: (env && env.error) || "執行失敗", usage: env && env.usage, hint: env && env.hint });
    } catch (e) {
      push({ type: "error", text: "無法連接指令路由器:" + (e.message || e) });
    } finally {
      setBusy(false);
      inputRef.current && inputRef.current.focus();
    }
  };

  const streamAi = async (text) => {
    // 運營後台:選了公司 → 跟該公司管理員秘書聊;沒選公司 → 平台級 AI(管平台本身)。後端按 tenant_slug 路由。
    setBusy(true);
    try {
      await termStream(fetchFn, apiBase + P.stream, withTarget({ text, conversation_id: convRef.current }), (ev) => {
        if (ev.event === "run_start") convRef.current = ev.conversation_id;
        else if (ev.event === "step_start") push({ type: "aistep", step: { ...ev, running: true } });
        else if (ev.event === "step") settleStep(ev);
        else if (ev.event === "final") push({ type: "aifinal", message: ev.message, run_id: ev.run_id, engine: ev.engine, status: ev.status });
      });
    } catch (e) {
      push({ type: "error", text: "AI 會話失敗:" + (e.message || e) });
    } finally {
      setBusy(false);
      inputRef.current && inputRef.current.focus();
    }
  };

  const runSql = async (query, force) => {
    if (needCompany()) {
      push({ type: "info", text: "👉 sql 要連某家公司的庫。先在右上角「目標公司」選一家,再執行。" });
      return;
    }
    setBusy(true);
    try {
      const res = await fetchFn(apiBase + P.sql, {
        method: "POST", body: JSON.stringify(withTarget({ sql: query, force })),
      });
      const d = await res.json().catch(() => ({}));
      if (!res.ok) push({ type: "error", text: d.error || "SQL 失敗" });
      else if (d.needs_confirm) push({ type: "error", text: d.message, hint: "確認無誤,把 sql 改成 sql! 重新發送" });
      else push({ type: "sql", result: d });
    } catch (e) {
      push({ type: "error", text: "SQL 失敗:" + (e.message || e) });
    } finally {
      setBusy(false);
      inputRef.current && inputRef.current.focus();
    }
  };

  const run = async (line) => {
    const text = line.trim();
    if (!text) return;
    setHistory((h) => [...h, text]);
    histRef.current = -1;
    push({ type: "cmd", text, prompt: aiMode ? "ai>" : "wh>" });
    if (text === "clear") { setItems([]); return; }
    // SQL 開發模式:sql <語句> 直接執行(危險操作用 sql! 強制),不經指令路由器
    if (text === "sql" || text === "sql!" || text.startsWith("sql ") || text.startsWith("sql!")) {
      const force = text.startsWith("sql!");
      const query = text.slice(force ? 4 : 3).trim();
      if (!query) { push({ type: "info", text: "用法:sql <SQL 語句>(查詢直接執行;DROP/無 WHERE 的 DELETE 等危險操作改用 sql! 強制)。僅系統管理員,全程審計。" }); return; }
      await runSql(query, force);
      return;
    }
    if (!aiMode) {
      if (text === "ai") {
        setAiMode(true);
        push({ type: "info", text: !companies
          ? "已進入 AI 會話模式:直接說要做什麼(多輪連續);!開頭直通指令(如 !inv list);new 開新對話;exit 退出。"
          : (slug
            ? `已進入 AI 會話模式 · 目標公司 /${slug}:我以該公司管理員身份幫你辦該公司的事(庫存/財務/單據…)。多輪連續;!指令直通;new 開新對話;exit 退出。`
            : "已進入 AI 會話模式 · 平台級:叫我管平台本身——審批入駐、開通/停用公司、加運營員、看各公司狀況。要管某家公司的內部業務,先在右上角選該公司。多輪連續;new 開新對話;exit 退出。") });
        return;
      }
      if (text.startsWith("ai ")) {
        const q = text.slice(3).trim().replace(/^["']+|["']+$/g, "");
        if (q) await streamAi(q);
        return;
      }
      await execCommand(text);
      return;
    }
    // —— AI 會話模式 ——
    if (text === "exit" || text === "quit" || text === "q") {
      setAiMode(false);
      push({ type: "info", text: "已退出 AI 會話模式,回到指令模式。" });
      return;
    }
    if (text === "new") {
      convRef.current = null;
      push({ type: "info", text: "已開啟新對話(上下文已重置)。" });
      return;
    }
    if (text.startsWith("!")) { await execCommand(text.slice(1).trim()); return; }
    if (text === "help") { await execCommand("help"); return; }
    await streamAi(text);
  };

  const ensureCmdCache = async () => {
    if (!cmdCacheRef.current) {
      try {
        const method = C.commandsMethod || "GET";
        const opts = method === "GET" ? { method: "GET" } : { method, body: JSON.stringify(withTarget({})) };
        const res = await fetchFn(apiBase + P.commands, opts);
        const d = await res.json();
        cmdCacheRef.current = (d.commands || []).filter((c) => c.allowed).map((c) => c.command);
      } catch (e) {
        cmdCacheRef.current = [];
      }
    }
    return cmdCacheRef.current;
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !busy) { const v = input; setInput(""); run(v); }
    else if (e.key === "Tab") {
      e.preventDefault();
      // 指令模式直接補全;AI 模式只補全 ! 直通指令
      if (aiMode && !input.startsWith("!")) return;
      const raw = aiMode ? input.slice(1) : input;
      ensureCmdCache().then((cmds) => {
        const pool = aiMode ? cmds : [...cmds, ...TERM_LOCAL_CMDS];
        const matches = pool.filter((c) => c.startsWith(raw));
        if (!matches.length) return;
        let prefix = matches[0];
        for (const m of matches) {
          let i = 0;
          while (i < prefix.length && i < m.length && prefix[i] === m[i]) i++;
          prefix = prefix.slice(0, i);
        }
        const completed = matches.length === 1 ? matches[0] + " " : prefix;
        setInput((aiMode ? "!" : "") + completed);
        if (matches.length > 1 && prefix === raw) push({ type: "info", text: matches.join("    ") });
      });
    }
    else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!history.length) return;
      histRef.current = histRef.current === -1 ? history.length - 1 : Math.max(0, histRef.current - 1);
      setInput(history[histRef.current]);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (histRef.current === -1) return;
      histRef.current = histRef.current + 1 >= history.length ? -1 : histRef.current + 1;
      setInput(histRef.current === -1 ? "" : history[histRef.current]);
    }
  };

  const rootHeight = C.height || "calc(100vh - var(--top-h) - 48px)";
  return (
    <div className="col" style={{ height: rootHeight, gap: 12 }}>
      <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 10 }}>
        <div>
          <div style={{ fontSize: 17, fontWeight: 800 }}>{title}</div>
          <div className="muted" style={{ fontSize: 12.5 }}>
            {subtitle}{companies ? (slug ? ` · 目標公司 /${slug}(以該公司管理員身份)` : " · 平台級(未選公司)") : ""}{aiMode ? " · AI 會話中(exit 退出)" : ""}
          </div>
        </div>
        <div className="row" style={{ gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          {companies && (
            <select value={slug} disabled={busy} onChange={(e) => setSlug(e.target.value)}
              style={{ height: 34, maxWidth: 230, borderRadius: 9, padding: "0 10px", fontSize: 12.5,
                border: "1px solid rgba(125,211,252,0.3)", background: "#0b1220", color: "#e2e8f0" }}>
              <option value="">平台級(tenants/operators…)</option>
              {(companies.filter((t) => t.status === "active" || !t.status)).map((t) =>
                <option key={t.slug} value={t.slug}>{(t.name || t.slug)} · /{t.slug}</option>)}
            </select>
          )}
          {!aiMode && <button className="btn" onClick={() => run("ai")} disabled={busy}
            style={{ fontSize: 12.5, padding: "7px 14px", borderRadius: 9, background: "linear-gradient(135deg,#7c3aed,#c026d3)", color: "#fff", fontWeight: 700 }}>
            召喚 AI
          </button>}
          <button className="btn" onClick={() => run(aiMode ? "!help" : "help")} disabled={busy}
            style={{ fontSize: 12.5, padding: "7px 14px", borderRadius: 9, background: "var(--grad)", color: "#fff", fontWeight: 700 }}>
            指令一覽
          </button>
        </div>
      </div>
      <div onClick={() => inputRef.current && inputRef.current.focus()} style={{
        flex: 1, minHeight: 0, borderRadius: 14,
        border: aiMode ? "1px solid rgba(192,132,252,0.35)" : "1px solid rgba(125,211,252,0.18)",
        background: "#0b1220", boxShadow: "inset 0 0 40px rgba(2,6,23,0.6)",
        padding: "14px 16px", overflowY: "auto", cursor: "text",
        fontFamily: "ui-monospace, SFMono-Regular, Consolas, 'Cascadia Mono', Menlo, monospace", fontSize: 13, lineHeight: 1.65,
      }}>
        {items.map((item, i) => <TermBlock key={i} item={item}/>)}
        {busy && <div style={{ color: aiMode ? "#c084fc" : "#7dd3fc" }}>{aiMode ? "… 助理工作中" : "… 執行中"}</div>}
        <div className="row" style={{ gap: 8, marginTop: 8 }}>
          <span style={{ color: aiMode ? "#c084fc" : "#34d399", fontWeight: 800 }}>{aiMode ? "ai>" : "wh>"}</span>
          <input ref={inputRef} value={input} disabled={busy} autoFocus spellCheck={false}
            onChange={(e) => setInput(e.target.value)} onKeyDown={onKeyDown}
            placeholder={busy ? "" : (aiMode ? "跟你的助理說要做什麼…(!指令 直通,new 開新對話,exit 退出)" : "輸入指令,如 inv list / help;輸入 ai 進入 AI 會話")}
            style={{ flex: 1, background: "transparent", border: "none", outline: "none",
              color: "#e2e8f0", fontFamily: "inherit", fontSize: 13, caretColor: aiMode ? "#c084fc" : "#34d399" }}/>
        </div>
        <div ref={bottomRef}/>
      </div>
    </div>
  );
};

window.PageTerminal = PageTerminal;
