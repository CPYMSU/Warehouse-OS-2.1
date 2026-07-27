/* WAREHOUSE 2.0 · 超級終端 — 即時職責域權力面(全程審計)
   端點照抄 1.0 frontend/page-terminal.jsx 與 scripts/ai_service.py:
   /api/cli/exec {line} → {ok,command,status,elapsed_ms,writes,risk,data:{action?}|error,usage,hint}
   /api/agent/run/stream NDJSON → run_start / step_start / step / final
   /api/cli/attachments multipart(file) → {ok,attachment:{handle,file_name,file_size,expires_at}}
   /api/cli/commands → {commands:[{command,usage,description,permission,writes,allowed}]} */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "超級終端": "Super Terminal",
  "人與 AI 同一指令集 · 即時職責域 · 持久 Passkey 操作卡 · 全程審計": "One command set for people and AI · live duty scope · persistent Passkey action cards · fully audited",
  "DB EXEC — 即時職責域 · PASSKEY": "DB EXEC — LIVE DUTY SCOPE · PASSKEY",
  "以你的權限執行 · 全程審計": "RUNS WITH YOUR PERMISSIONS · FULLY AUDITED",
  "終端以你的賬號權限執行:能做什麼由權限決定,超權指令會被後端拒絕;每個動作全程審計。": "The terminal runs with your account's permissions: what you can do is decided by them, over-privileged commands are rejected by the backend, and every action is fully audited.",
  "AI 會話": "AI Chat",
  "快捷命令": "Quick commands",
  "點擊填入輸入行,不會自動執行": "Click to fill the input line — never auto-runs",
  "清屏": "Clear",
  "CLI 指令模式 — 輸入平臺指令;help 顯示已授權能力;capabilities 關鍵詞可搜尋;Tab 補全;↑↓ 歷史": "CLI mode — type platform commands; help shows authorized abilities; capabilities <query> searches them; Tab completes; ↑↓ history",
  "AI 會話模式 — 說自然語言,內核逐步執行,每一步可見;new 開新對話;!指令直通": "AI chat mode — speak naturally, the kernel executes step by step, every step visible; new resets context; ! passes a raw command through",
  "SQL 模式 — 透過 db exec 套用即時職責域;讀取直接返回,寫入建立持久 Passkey 操作卡": "SQL mode — uses db exec with your live duty scope; reads return directly and writes create a persistent Passkey action card",
  "已切換到 CLI 指令模式:輸入平臺指令,help 查看已授權能力。": "Switched to CLI mode: type platform commands; help shows your authorized abilities.",
  "已進入 AI 會話模式:直接說要做什麼(多輪連續);!開頭直通指令;new 開新對話。": "AI chat mode: just say what to do (multi-turn); prefix ! to pass a raw command; new starts a fresh conversation.",
  "已進入 SQL 模式:語句經 db exec 即時職責域檢查;所有寫入只建立持久操作卡,Passkey 確認後才執行。": "SQL mode: statements pass through db exec live-duty-scope checks; every write only creates a persistent action card and runs after Passkey confirmation.",
  "已退出 AI 會話模式,回到 CLI。": "Left AI chat mode, back to CLI.",
  "已開啟新對話(上下文已重置)。": "New conversation started (context reset).",
  "執行失敗": "Command failed",
  "待確認": "awaiting confirmation",
  "待確認（未寫庫）": "awaiting confirmation (no write yet)",
  "部分完成": "partially completed",
  "無法連接指令路由器:": "Cannot reach the command router: ",
  "AI 會話失敗:": "AI chat failed: ",
  "附件暫存失敗:": "Attachment staging failed: ",
  "附件": "Attachment",
  "選擇附件": "Choose attachment",
  "附件上傳中…": "Uploading attachment…",
  "附件暫存回傳的 handle 無效": "The staged attachment returned an invalid handle",
  "到期": "expires",
  "用法:": "Usage: ",
  "已寫庫(已審計)": "wrote DB (audited)",
  "第 {n} 步": "step {n}",
  "執行中…": "running…",
  "(本次未調用任何工具)": "(no tools were called this run)",
  "(空結果集)": "(empty result set)",
  "sql! 只會把 force=true 寫入持久操作卡;仍須 Passkey 確認": "sql! records force=true on the persistent action card; Passkey confirmation is still required",
  "目前沒有即時職責域 db exec 權限。請確認你的有效任命、主管職位或部門負責人設定。": "No live-duty-scope db exec permission is active. Check your current appointment, manager position, or department-head assignment.",
  "輸入平臺指令…(help 已授權能力 · capabilities 搜尋 · Tab 補全)": "Type a platform command… (help shows authorized abilities · capabilities searches · Tab completes)",
  "跟內核說要做什麼…(!指令直通 · new 開新對話)": "Tell the kernel what to do… (! passes a raw command · new resets context)",
  "輸入 SQL…(經 db exec 職責域檢查 · 寫入建立 Passkey 操作卡)": "Type SQL… (checked by db exec duty scope · writes create a Passkey action card)",
  "AI 智能引擎": "AI engine",
  "規則引擎(非 AI)": "rule engine (non-AI)",
  "寫": "W",
  "需 {p} 權限": "needs {p}",
  "共 {n} 行": "{n} rows total",
  "僅顯示前 {n} 行": "first {n} shown",
  "列已截斷至 {n}": "columns truncated to {n}",
  "展開全部 {n} 行": "Expand all {n} rows",
  "展開全部 {n} 條": "Expand all {n} entries",
  "展開全部 {n} 行輸出": "Expand all {n} output lines",
  "收起": "Collapse",
  "(無返回數據)": "(no data returned)",
  "可用 runs show --id {n} 回看": "replay with runs show --id {n}",
  "… 執行中": "… running",
  "… 內核工作中": "… kernel working",
  "今天倉庫整體情況怎麼樣?": "How is the warehouse doing today?",
  "把低庫存物資列出來,給出補貨建議": "List low-stock items and suggest restocking",
  "最近的審計日誌有沒有異常?": "Any anomalies in the recent audit log?",
  "本地指令:help 已授權能力 · capabilities <關鍵詞/業務域> 搜尋 · clear 清屏": "Local commands: help shows authorized abilities · capabilities <query/domain> searches · clear wipes the screen",
  "Passkey 操作已完成": "Passkey action completed",
  "操作卡已取消或失效": "Action card cancelled or no longer valid",
  "確認卡元件未載入;操作尚未執行,請重新整理頁面。": "The confirmation-card component did not load; nothing was executed. Refresh the page.",
  "業務表請先回 CLI 執行 db schema --domain <你的業務域>,再依可見目錄撰寫 SQL。": "For business tables, first return to CLI and run db schema --domain <your-domain>, then write SQL from the visible catalog.",
  "流程受阻時先用 wf repair scan/plan；禁止用 db exec 或另建單據繞過。": "For a blocked workflow, use wf repair scan/plan first; never bypass it with db exec or a duplicate business document.",
  "修復卡元件未載入;任何修復操作均未執行。": "The repair-card component did not load; no repair operation was executed.",
  "目前沒有修復案件": "No repair cases",
  "流程安全修復": "Safe workflow repair",
});

const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Folio } = W2;

/* ── 墨面板配色(紙墨紅紀律,僅此頁的暗面)── */
const MONO = { fontFamily: "var(--f-mono)" };
const DK = {
  paper: "var(--paper)",
  dim: "var(--ink-4)",
  dimmer: "var(--ink-3)",
  red: "var(--red)",
  hair: "rgba(245,242,235,.20)",
  hairSoft: "rgba(245,242,235,.10)",
};
const DBTN = { ...MONO, fontSize: 9.5, letterSpacing: ".12em", color: DK.dim,
  border: "1px solid " + DK.hair, background: "transparent", padding: "3px 10px" };

const S = (v) => (v === null || v === undefined || v === "") ? "—" : String(v);
const promptOf = (m) => m === "ai" ? "ai>" : m === "sql" ? "sql>" : "$";
/* Python shlex 的單引號安全編碼；SQL 模式仍只走 /api/cli/exec → db exec。 */
const cliQuote = (value) => "'" + String(value).replace(/'/g, "'\"'\"'") + "'";
const attachmentSize = (value) => {
  if (value === null || value === undefined || value === "") return "—";
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  if (bytes >= 1024) return Math.round(bytes / 1024) + " KB";
  return bytes + " B";
};
const attachmentExpiry = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
};
const quoteCliArg = (value) => {
  const text = String(value == null ? "" : value);
  return /^[A-Za-z0-9._~:/+=-]+$/.test(text)
    ? text
    : `"${text.replace(/\\/g, "\\\\").replace(/"/g, '\\"')}"`;
};
const withAttachmentHandle = (line, handle) => {
  const flag = `--handle ${quoteCliArg(handle)}`;
  const withoutOldHandle = String(line || "")
    .replace(/(^|\s)--handle(?:\s+(?:"(?:\\.|[^"])*"|'[^']*'|\S+))?/g, "$1")
    .replace(/[ \t]{2,}/g, " ")
    .trim();
  return withoutOldHandle ? `${withoutOldHandle} ${flag}` : flag;
};
const decodeDownloadGuards = (value) => value.replace(
  /%(?:25|2e|2f|5c|0[0-9a-f]|1[0-9a-f]|7f)/gi,
  token => String.fromCharCode(Number.parseInt(token.slice(1), 16))
);
const downloadEncodingIsSafe = (value) => {
  if (/%(?![0-9a-f]{2})/i.test(value)) return false;
  let decoded = value;
  for (let depth = 0; depth < 4; depth += 1) {
    if (/[\u0000-\u001f\u007f\\]/.test(decoded)) return false;
    const path = decoded.split(/[?#]/, 1)[0];
    if (path.split("/").some(segment => segment === "." || segment === "..")) return false;
    const next = decodeDownloadGuards(decoded);
    if (next === decoded) return true;
    decoded = next;
  }
  return false;
};
const safeApiDownloadUrl = (value) => {
  if (typeof value !== "string") return null;
  const raw = value.trim();
  if (!/^\/api\//.test(raw) || /[\u0000-\u001f\u007f\\]/.test(raw) || !downloadEncodingIsSafe(raw)) return null;
  try {
    const base = "https://warehouse.invalid";
    const parsed = new URL(raw, base);
    if (parsed.origin !== base || !parsed.pathname.startsWith("/api/")) return null;
    return parsed.pathname + parsed.search + parsed.hash;
  } catch (error) { return null; }
};
const safeDownloadText = (value, limit = 180) => String(value == null ? "" : value)
  .replace(/[\u0000-\u001f\u007f\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "")
  .trim().slice(0, limit);
const safeDownloadFilename = (value) => {
  const filename = safeDownloadText(
    String(value == null ? "" : value).split(/[\\/]/).pop()
  );
  return filename === "." || filename === ".." ? "" : filename;
};
const safeDownloads = (values) => {
  const seen = new Set();
  return (Array.isArray(values) ? values : []).reduce((result, item) => {
    if (!item || typeof item !== "object") return result;
    const url = safeApiDownloadUrl(item.url);
    if (!url || seen.has(url)) return result;
    seen.add(url);
    const filename = safeDownloadFilename(item.filename);
    result.push({
      url,
      filename,
      label: safeDownloadText(item.label) || filename || t("下載"),
    });
    return result;
  }, []);
};
/* 結果裡常見的「行集」:{rows:[...]} 或 data 本身是對象數組(照抄 1.0 termRowsOf) */
const rowsOf = (data) => {
  if (Array.isArray(data)) return data.length && data.every((r) => r && typeof r === "object" && !Array.isArray(r)) ? data : null;
  if (data && Array.isArray(data.rows)) return data.rows;
  return null;
};

/* ── mono 表(行數組;>12 行摺疊)── */
const TTable = ({ rows }) => {
  const [open, setOpen] = _s(false);
  const MAXC = 9, LIM = 12, HARD = 200;
  const allCols = Object.keys(rows[0] || {});
  const cols = allCols.slice(0, MAXC);
  const shown = rows.slice(0, open ? HARD : LIM);
  return (
    <div style={{ margin: "6px 0 2px" }}>
      <div style={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", whiteSpace: "nowrap", ...MONO, fontSize: 11.5 }}>
          <thead><tr>{cols.map((c) => (
            <th key={c} style={{ textAlign: "left", padding: "3px 16px 4px 0", fontSize: 9, fontWeight: 600,
              letterSpacing: ".14em", textTransform: "uppercase", color: DK.dim, borderBottom: "1px solid " + DK.hair }}>{c}</th>
          ))}</tr></thead>
          <tbody>{shown.map((r, i) => (
            <tr key={i}>{cols.map((c) => (
              <td key={c} style={{ padding: "3px 16px 3px 0", color: DK.paper, borderBottom: "1px solid " + DK.hairSoft }}>
                {r[c] === null || r[c] === undefined ? "—" : String(r[c])}
              </td>
            ))}</tr>
          ))}</tbody>
        </table>
      </div>
      <div className="row g10" style={{ marginTop: 5 }}>
        <span style={{ ...MONO, fontSize: 9.5, letterSpacing: ".08em", color: DK.dimmer }}>
          {t("共 {n} 行", { n: rows.length })}
          {!open && rows.length > LIM ? " · " + t("僅顯示前 {n} 行", { n: LIM }) : ""}
          {allCols.length > MAXC ? " · " + t("列已截斷至 {n}", { n: MAXC }) : ""}
        </span>
        {rows.length > LIM && (
          <button style={DBTN} onClick={() => setOpen(v => !v)}>
            {open ? "▴ " + t("收起") : "▾ " + t("展開全部 {n} 行", { n: Math.min(rows.length, HARD) })}
          </button>
        )}
      </div>
    </div>
  );
};

/* ── help 指令表(>12 條摺疊)── */
const THelp = ({ commands }) => {
  const [open, setOpen] = _s(false);
  const LIM = 12;
  const list = open ? commands : commands.slice(0, LIM);
  return (
    <div style={{ margin: "6px 0 2px" }}>
      {list.map((c) => (
        <div key={c.command} style={{ marginBottom: 7, opacity: c.allowed === false ? .45 : 1 }}>
          <span style={{ ...MONO, fontSize: 12, fontWeight: 700, color: DK.paper }}>{c.usage || c.command}</span>
          {c.writes && <span style={{ ...MONO, fontSize: 8.5, letterSpacing: ".1em", color: "#fff", background: DK.red, padding: "1px 5px", marginLeft: 8 }}>{t("寫")}</span>}
          {c.allowed === false && <span style={{ ...MONO, fontSize: 9.5, color: DK.dimmer, marginLeft: 8 }}>{t("需 {p} 權限", { p: c.permission || "—" })}</span>}
          <div style={{ fontSize: 11.5, color: DK.dim }}>{c.description || ""}</div>
        </div>
      ))}
      <div className="row g10">
        <span style={{ ...MONO, fontSize: 9.5, letterSpacing: ".08em", color: DK.dimmer }}>{t("本地指令:help 已授權能力 · capabilities <關鍵詞/業務域> 搜尋 · clear 清屏")}</span>
        {commands.length > LIM && (
          <button style={DBTN} onClick={() => setOpen(v => !v)}>
            {open ? "▴ " + t("收起") : "▾ " + t("展開全部 {n} 條", { n: commands.length })}
          </button>
        )}
      </div>
    </div>
  );
};

/* ── 長文本 / JSON(>14 行摺疊)── */
const TPre = ({ text }) => {
  const [open, setOpen] = _s(false);
  const str = String(text == null ? "" : text);
  const lines = str.split("\n");
  const LIM = 14;
  const shown = open || lines.length <= LIM ? str : lines.slice(0, LIM).join("\n");
  return (
    <div style={{ margin: "4px 0 2px" }}>
      <pre style={{ ...MONO, fontSize: 11.5, lineHeight: 1.6, whiteSpace: "pre-wrap", wordBreak: "break-word", color: DK.paper, margin: 0 }}>{shown}</pre>
      {lines.length > LIM && (
        <button style={{ ...DBTN, marginTop: 4 }} onClick={() => setOpen(v => !v)}>
          {open ? "▴ " + t("收起") : "▾ " + t("展開全部 {n} 行輸出", { n: lines.length })}
        </button>
      )}
    </div>
  );
};

const CredentialCard = ({ credential }) => {
  const [visible, setVisible] = _s(false);
  const [copied, setCopied] = _s(false);
  if (!credential || !credential.value) return null;
  const copy = async () => {
    try { await navigator.clipboard.writeText(credential.value); setCopied(true); setTimeout(() => setCopied(false), 1600); }
    catch (e) { setVisible(true); }
  };
  return (
    <div style={{ border: "1px solid var(--red)", background: "rgba(255,255,255,.04)", padding: "10px 12px", margin: "7px 0", maxWidth: 880 }}>
      <div style={{ ...MONO, color: DK.red, fontSize: 10, letterSpacing: ".12em", fontWeight: 800 }}>ONE-TIME CREDENTIAL</div>
      <div style={{ color: DK.paper, fontSize: 12, fontWeight: 750, marginTop: 4 }}>{credential.label || t("檔案 CLI 金鑰")}</div>
      <div style={{ ...MONO, color: DK.paper, background: "rgba(0,0,0,.28)", padding: "7px 9px", marginTop: 7, wordBreak: "break-all" }}>
        {visible ? credential.value : (credential.key_hint || "rck_••••••••••••")}
      </div>
      <div style={{ ...MONO, color: DK.dimmer, fontSize: 9.5, marginTop: 5 }}>
        {credential.tenant_slug || "—"} · {(credential.scopes || []).join(",") || "—"} · {credential.expires_at || "—"}
      </div>
      <div className="row g6" style={{ marginTop: 7 }}>
        <button style={DBTN} onClick={() => setVisible(v => !v)}>{visible ? t("隱藏") : t("揭示")}</button>
        <button style={DBTN} onClick={copy}>{copied ? t("已複製") : t("複製")}</button>
        {credential.cli_download && <span style={{ ...MONO, color: DK.dimmer, fontSize: 9.5 }}>{credential.cli_download}</span>}
      </div>
      <div style={{ color: DK.dimmer, fontSize: 10.5, marginTop: 6 }}>{credential.note || t("明文只顯示這一次，請立即保存。")}</div>
    </div>
  );
};

const DownloadLinks = ({ downloads }) => {
  const items = safeDownloads(downloads);
  if (!items.length) return null;
  return (
    <div className="row g6 wrap" style={{ margin: "7px 0", maxWidth: 880 }}>
      {items.map((download) => (
        <a key={download.url} style={{ ...DBTN, display: "inline-flex", alignItems: "center", gap: 5, textDecoration: "none" }}
          href={download.url} download={download.filename || true} target="_blank" rel="noopener noreferrer">
          <I name="inbound" size={11}/>{download.label}
        </a>
      ))}
    </div>
  );
};

/* ── AI 步驟行(step_start → step 原位落定)── */
const terminalStepOutcome = (step) => {
  const status = String((step && step.status) || "");
  if (step && step.running) return { mark: "…", color: DK.dim, suffix: " · " + t("執行中…"), pending: false };
  if (status === "confirmation_required" || status === "pending_confirmation") {
    return { mark: "⏳", color: "#fbbf24", suffix: " · " + t("待確認"), pending: true };
  }
  if (status === "partial") return { mark: "⚠", color: "#fbbf24", suffix: " · " + t("部分完成"), pending: false };
  if (step && step.ok === false) return { mark: "✗", color: DK.red, suffix: "", pending: false };
  return { mark: "✓", color: DK.paper, suffix: "", pending: false };
};

const StepLine = ({ step }) => {
  const outcome = terminalStepOutcome(step);
  return (
    <div>
      <div style={{ ...MONO, fontSize: 11, letterSpacing: ".03em", color: outcome.color, padding: "1px 0" }}>
        {outcome.mark} {t("第 {n} 步", { n: S(step.step_no) })}{" "}
        <b>{step.command || step.tool_name || "—"}</b>
        {step.args && Object.keys(step.args).length ? <span style={{ color: DK.dimmer }}> {JSON.stringify(step.args).slice(0, 120)}</span> : null}
        {outcome.suffix || (typeof step.duration_ms === "number" ? ` · ${step.duration_ms}ms` : "")}
        {!outcome.pending && !step.running && step.error ? <span style={{ color: DK.red }}> · {step.error}</span> : null}
      </div>
      {!step.running && (step.credentials || (step.credential ? [step.credential] : [])).map((credential, i) =>
        <CredentialCard key={i} credential={credential}/>
      )}
      {!step.running && <DownloadLinks downloads={step.downloads}/>}
    </div>
  );
};

/* ── AI final:紙面小島 + mdToHtml 富文本 ── */
const AiFinal = ({ item }) => {
  const html = W2.mdToHtml ? W2.mdToHtml(item.message) : null;
  return (
    <div style={{ margin: "8px 0 4px" }}>
      <div style={{ background: "var(--paper)", color: "var(--ink)", padding: "12px 14px", borderLeft: "3px solid var(--red)", maxWidth: 880 }}>
        {html != null
          ? <div className="md" style={{ fontSize: 12.5, lineHeight: 1.65, wordBreak: "break-word" }} dangerouslySetInnerHTML={{ __html: html }}/>
          : <div style={{ whiteSpace: "pre-wrap", fontSize: 12.5, lineHeight: 1.65 }}>{S(item.message)}</div>}
      </div>
      <div style={{ ...MONO, fontSize: 9.5, letterSpacing: ".06em", color: DK.dimmer, marginTop: 4 }}>
        run #{S(item.run_id)} · {item.engine === "deepseek" ? t("AI 智能引擎") : t("規則引擎(非 AI)")} · {S(item.status)}
        {item.run_id != null ? " · " + t("可用 runs show --id {n} 回看", { n: item.run_id }) : ""}
      </div>
    </div>
  );
};

/* runs show 實際返回 {run:{id,engine,status,final_message…}, steps:[DB行]}(ok=0/1、args_json 為字串);
   非流式 ai 信封則是頂層 {run_id, steps, message…}。兩種都歸一成 RunBlock 形狀,回放才不會退化成 JSON 傾印 */
const normDbStep = (s) => {
  let args = s.args;
  if (args == null && typeof s.args_json === "string") { try { args = JSON.parse(s.args_json); } catch (e) { args = null; } }
  return { ...s, args, ok: !(s.ok === 0 || s.ok === false) };
};
const runShapeOf = (data) => {
  if (!data) return null;
  if (Array.isArray(data.steps) && data.run_id != null) return data;
  if (data.run && typeof data.run === "object" && Array.isArray(data.steps))
    return { run_id: data.run.id, engine: data.run.engine, status: data.run.status,
             message: data.run.final_message, steps: data.steps.map(normDbStep) };
  return null;
};

/* ── 一次 run 的整體結果(runs show 等)── */
const RunBlock = ({ data }) => (
  <div style={{ margin: "4px 0" }}>
    {(data.steps || []).map((s, i) => <StepLine key={i} step={{ ...s, running: false }}/>)}
    {!(data.steps || []).length && <div style={{ ...MONO, fontSize: 11, color: DK.dimmer }}>{t("(本次未調用任何工具)")}</div>}
    {data.message && <div style={{ color: DK.paper, whiteSpace: "pre-wrap", fontSize: 12.5, marginTop: 6 }}>{String(data.message)}</div>}
    {data.run_id != null && (
      <div style={{ ...MONO, fontSize: 9.5, color: DK.dimmer, marginTop: 4 }}>
        run #{data.run_id} · {data.engine === "deepseek" ? t("AI 智能引擎") : t("規則引擎(非 AI)")} · {S(data.status)}
      </div>
    )}
  </div>
);

/* ── CLI 信封結果 ── */
const ResBlock = ({ env }) => {
  const data = env.data;
  const incomingAction = data && data.action && typeof data.action === "object" && !Array.isArray(data.action)
    ? data.action : null;
  const [action, setAction] = _s(incomingAction);
  const repairCards = typeof W2.workflowRepairEnvelopes === "function"
    ? W2.workflowRepairEnvelopes(data) : [];
  const hasRepairPayload = !!(data && (
    data.repair_case || data.case || data.repair || data.current_plan || data.plan
    || Array.isArray(data.repairs) || Array.isArray(data.cases)
  ));
  const downloads = [
    ...(Array.isArray(env.downloads) ? env.downloads : []),
    ...(data && Array.isArray(data.downloads) ? data.downloads : []),
  ];
  const rows = rowsOf(data);
  const run = runShapeOf(data);
  const actionStatus = String((action && action.status) || "");
  const actionWaiting = actionStatus === "pending" || actionStatus === "executing";
  const actionCompleted = actionStatus === "completed";
  const actionEnded = !!actionStatus && !actionWaiting && !actionCompleted;
  const pendingConfirmation = env.needs_confirmation === true && (!action || actionWaiting);
  const partial = env.partial === true;
  const committedWrite = env.ok === true && env.writes === true && (
    env.command !== "db exec"
    || (!action && data && data.ok === true && ["write", "schema"].includes(String(data.mode || "")))
  );
  const mark = pendingConfirmation ? "⏳" : actionEnded ? "✗" : partial ? "⚠" : "✓";
  const label = pendingConfirmation ? t("待確認（未寫庫）")
    : actionCompleted ? t("Passkey 操作已完成")
    : actionEnded ? t("操作卡已取消或失效")
    : partial ? t("部分完成") : "";
  const color = actionEnded ? DK.red : pendingConfirmation || partial ? "#fbbf24" : DK.dim;
  const OperationConfirmation = W2.OperationConfirmation;
  const RepairPlanCard = W2.RepairPlanCard;
  return (
    <div>
      <div style={{ ...MONO, fontSize: 10, letterSpacing: ".08em", color }}>
        {mark} {S(env.command)}
        {label ? " · " + label : ""}
        {typeof env.status === "number" ? ` · ${env.status}` : ""}
        {typeof env.elapsed_ms === "number" ? ` · ${env.elapsed_ms}ms` : ""}
        {committedWrite ? " · " + t("已寫庫(已審計)") : ""}
      </div>
      <DownloadLinks downloads={downloads}/>
      {action ? (
        <div onClick={event => event.stopPropagation()} style={{ margin: "8px 0 4px", color: "var(--ink)" }}>
          {typeof data.message === "string" && <div style={{ color: DK.dim, fontSize: 11.5, lineHeight: 1.55, marginBottom: 7 }}>{data.message}</div>}
          {typeof OperationConfirmation === "function"
            ? <OperationConfirmation confirmation={{ action }} onActionChange={setAction}/>
            : <div role="alert" style={{ border: "1px solid var(--red)", color: DK.red, padding: 10 }}>{t("確認卡元件未載入;操作尚未執行,請重新整理頁面。")}</div>}
        </div>
      ) : hasRepairPayload ? (
        <div onClick={event => event.stopPropagation()} style={{ display: "grid", gap: 10, margin: "8px 0 4px", color: "var(--ink)" }}>
          {typeof RepairPlanCard !== "function" ? (
            <div role="alert" style={{ border: "1px solid var(--red)", color: DK.red, padding: 10 }}>{t("修復卡元件未載入;任何修復操作均未執行。")}</div>
          ) : repairCards.length ? repairCards.map((repair, index) => (
            <RepairPlanCard key={repair.caseId || index} repair={repair.raw} compact/>
          )) : (
            <div style={{ ...MONO, fontSize: 11, color: DK.dimmer }}>{t("目前沒有修復案件")}</div>
          )}
        </div>
      ) : data && data.api_key ? <CredentialCard credential={{
          label: t("檔案 CLI 金鑰"), value: data.api_key, key_hint: data.key_hint,
          key_id: data.key_id, tenant_slug: data.tenant_slug, scopes: data.scopes,
          expires_at: data.expires_at, cli_download: data.cli_download, note: data.note,
        }}/>
        : data && Array.isArray(data.commands) ? <THelp commands={data.commands}/>
        : run ? <RunBlock data={run}/>
        : rows ? (rows.length ? <TTable rows={rows}/> : <div style={{ ...MONO, fontSize: 11, color: DK.dimmer }}>{t("(空結果集)")}</div>)
        : typeof (data && (data.message || data.reply)) === "string"
          ? <div style={{ color: DK.paper, whiteSpace: "pre-wrap", fontSize: 12.5, margin: "4px 0" }}>{data.message || data.reply}</div>
        : data == null ? <div style={{ ...MONO, fontSize: 11, color: DK.dimmer }}>{t("(無返回數據)")}</div>
        : <TPre text={JSON.stringify(data, null, 2)}/>}
    </div>
  );
};

/* ── 單條輸出塊 ── */
const TBlock = ({ item }) => {
  if (item.k === "cmd") return (
    <div style={{ marginTop: 14 }}>
      <span style={{ ...MONO, fontSize: 12, fontWeight: 700, background: "var(--paper)", color: "var(--ink)", padding: "2px 9px", wordBreak: "break-all" }}>
        {promptOf(item.mode)} {item.text}
      </span>
    </div>
  );
  if (item.k === "info") return <div style={{ fontSize: 12, color: item.red ? DK.red : DK.dim, marginTop: 3, whiteSpace: "pre-wrap" }}>{item.text}</div>;
  if (item.k === "err") return (
    <div style={{ marginTop: 3 }}>
      <div style={{ fontSize: 12.5, fontWeight: 650, color: DK.red, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>✗ {item.text}</div>
      {item.usage && <div style={{ ...MONO, fontSize: 11, color: DK.dim }}>{t("用法:")}{item.usage}</div>}
      {item.hint && <div style={{ fontSize: 11, color: DK.dimmer }}>{item.hint}</div>}
    </div>
  );
  if (item.k === "res") return <ResBlock env={item.env}/>;
  if (item.k === "aistep") return <StepLine step={item.step}/>;
  if (item.k === "aifinal") return <AiFinal item={item}/>;
  return null;
};

/* ── 歡迎屏(mono 藝術字 + 使用說明)── */
const ART = [
  "█   █   ███    ████",
  "█   █  █   █  █    ",
  "█ █ █  █   █   ███ ",
  "█ █ █  █   █      █",
  " █ █    ███   ████ ",
].join("\n");
const Welcome = ({ showSql }) => (
  <div style={{ paddingBottom: 6 }}>
    <pre style={{ fontFamily: "ui-monospace, Consolas, Menlo, monospace", fontSize: 11, lineHeight: 1.25, color: DK.paper, margin: 0 }}>{ART}</pre>
    <div style={{ width: 72, height: 8, background: DK.red, margin: "10px 0 12px" }}/>
    <div style={{ ...MONO, fontSize: 10, letterSpacing: ".2em", color: DK.dim, marginBottom: 12 }}>WAREHOUSE OS 2.0 · SUPER TERMINAL</div>
    <div className="col g6" style={{ fontSize: 12, color: DK.dim, maxWidth: 760, lineHeight: 1.7 }}>
      <div><span style={{ ...MONO, fontWeight: 700, color: DK.paper }}>$&nbsp;&nbsp;&nbsp;</span>{t("CLI 指令模式 — 輸入平臺指令;help 顯示已授權能力;capabilities 關鍵詞可搜尋;Tab 補全;↑↓ 歷史")}</div>
      <div><span style={{ ...MONO, fontWeight: 700, color: DK.paper }}>ai&gt;&nbsp;</span>{t("AI 會話模式 — 說自然語言,內核逐步執行,每一步可見;new 開新對話;!指令直通")}</div>
      {showSql && <div><span style={{ ...MONO, fontWeight: 700, color: DK.paper }}>sql&gt;</span> {t("SQL 模式 — 透過 db exec 套用即時職責域;讀取直接返回,寫入建立持久 Passkey 操作卡")}</div>}
      <div style={{ color: DK.red, fontWeight: 650 }}>{t("終端以你的賬號權限執行:能做什麼由權限決定,超權指令會被後端拒絕;每個動作全程審計。")}</div>
      <div style={{ color: DK.red, fontWeight: 650 }}>{t("流程受阻時先用 wf repair scan/plan；禁止用 db exec 或另建單據繞過。")}</div>
    </div>
  </div>
);

/* ── 快捷命令(點擊填入輸入行,不自動執行;提煉自 1.0 指令集)── */
const CHIPS = {
  cli: ["help", "capabilities finance", "capabilities org", "whoami", "inv list", "alert list", "report summary", "wf inbox", "wf repair list",
        "record meta", "record key list", "erp overview", "fin trial-balance", "audit logs", "users list", "ai health"],
  ai: ["今天倉庫整體情況怎麼樣?", "把低庫存物資列出來,給出補貨建議", "最近的審計日誌有沒有異常?"],
  sql: ["PRAGMA schema_version", "PRAGMA page_count"],
};

/* ── 頁面 ── */
const Page = () => {
  const u = window.W2_USER || {};
  const [me, setMe] = _s(null);
  const actor = (me && me.user) || u;
  const permissionKeys = new Set([
    ...((actor.permissions || []).map(String)),
    ...((actor.derived_permissions || []).map(String)),
    ...((actor.roles || []).flatMap(role => (role && role.permissions || []).map(String))),
  ]);
  const databaseAccess = actor.database_access && typeof actor.database_access === "object"
    ? actor.database_access : {};
  const hasLiveWriteScope = databaseAccess.global_exec === true
    || (Array.isArray(databaseAccess.write_domains) && databaseAccess.write_domains.length > 0);
  // 終端全員可用；SQL 工作區只按後端同源的即時 db exec 入場券顯示。
  // 實際表/業務域仍由服務端按有效任命與部門負責人逐句重算，前端不授權。
  const showSql = hasLiveWriteScope
    && (permissionKeys.has("cli.db.exec") || permissionKeys.has("cli.db.department"));

  const [items, setItems] = _s([]);
  const [mode, setMode] = _s("cli");
  const [input, setInput] = _s("");
  const [busy, setBusy] = _s(false);
  const [attachmentBusy, setAttachmentBusy] = _s(false);
  const [attachment, setAttachment] = _s(null);
  const [history, setHistory] = _s([]);
  const histRef = React.useRef(-1);
  const convRef = React.useRef(null);       // AI 多輪對話 id
  const cmdCacheRef = React.useRef(null);   // Tab 補全緩存
  const outRef = React.useRef(null);
  const inputRef = React.useRef(null);
  const attachmentInputRef = React.useRef(null);

  _e(() => { W2.json("/api/auth/me").then(d => setMe(d || {})).catch(() => setMe({})); }, []);
  _e(() => { outRef.current && (outRef.current.scrollTop = outRef.current.scrollHeight); }, [items, busy]);

  const company = _mm(() => {
    const list = (me && me.companies) || [];
    const hit = list.find(c => c && c.slug === W2.tenant());
    return (hit && hit.name) || W2.tenant() || "—";
  }, [me]);

  const push = (...blocks) => setItems(prev => [...prev, ...blocks]);
  const focus = () => setTimeout(() => inputRef.current && inputRef.current.focus(), 40);

  const stageAttachment = async (selected) => {
    const file = selected && selected[0];
    if (!file || attachmentBusy) return;
    setAttachmentBusy(true);
    try {
      const form = new FormData();
      form.append("file", file, file.name);
      const response = await W2.fetch("/api/cli/attachments", { method: "POST", body: form });
      const data = await response.json().catch(() => ({}));
      const staged = data && data.attachment;
      if (!response.ok || !data.ok || !staged || !staged.handle) {
        throw new Error((data && (data.error || data.message)) || response.statusText || t("執行失敗"));
      }
      const handle = String(staged.handle).trim();
      if (!handle || handle.length > 2048 || /[\u0000\r\n]/.test(handle)) {
        throw new Error(t("附件暫存回傳的 handle 無效"));
      }
      setAttachment({
        file_name: String(staged.file_name || file.name || t("附件")).slice(0, 240),
        file_size: Number.isFinite(Number(staged.file_size)) ? Number(staged.file_size) : null,
        expires_at: staged.expires_at || null,
      });
      setInput(current => withAttachmentHandle(current, handle));
      focus();
    } catch (error) {
      push({ k: "err", text: t("附件暫存失敗:") + (error.message || error) });
    } finally {
      setAttachmentBusy(false);
    }
  };

  /* step 事件:把對應「執行中」行原位落定(照抄 1.0 settleStep) */
  const settleStep = (ev) => setItems(prev => {
    const next = [...prev];
    for (let i = next.length - 1; i >= 0; i--) {
      const it = next[i];
      if (it.k === "aistep" && it.step.running && (ev.step_no == null || it.step.step_no === ev.step_no)) {
        next[i] = { k: "aistep", step: { ...ev, running: false } };
        return next;
      }
    }
    next.push({ k: "aistep", step: { ...ev, running: false } });
    return next;
  });

  const doExec = async (line) => {
    setBusy(true);
    try {
      const env = await W2.post("/api/cli/exec", { line });
      if (env && (env.ok || env.needs_confirmation || env.partial)) push({ k: "res", env });
      else push({ k: "err", text: (env && env.error) || t("執行失敗"), usage: env && env.usage, hint: env && env.hint });
    } catch (e) { push({ k: "err", text: t("無法連接指令路由器:") + (e.message || e) }); }
    finally { setBusy(false); focus(); }
  };

  const doAi = async (text) => {
    setBusy(true);
    try {
      await W2.agentStream({ text, conversation_id: convRef.current }, (ev) => {
        if (ev.event === "run_start") convRef.current = ev.conversation_id || convRef.current;
        else if (ev.event === "step_start") push({ k: "aistep", step: { ...ev, running: true } });
        else if (ev.event === "step") settleStep(ev);
        else if (ev.event === "final") push({ k: "aifinal", message: ev.message || "", run_id: ev.run_id, engine: ev.engine, status: ev.status });
      });
    } catch (e) { push({ k: "err", text: t("AI 會話失敗:") + (e.message || e) }); }
    finally { setBusy(false); focus(); }
  };

  const doSql = async (q, force) => doExec(
    `db exec --sql ${cliQuote(q)}${force ? " --force" : ""}`
  );

  /* SQL 入口:裸語句(sql 模式)或 sql / sql! 前綴。永遠回到 db exec，
     因此寫入只能得到持久化 Passkey 卡，Enter 絕不是最終確認。 */
  const sqlPath = async (text) => {
    if (!showSql) { push({ k: "err", text: t("目前沒有即時職責域 db exec 權限。請確認你的有效任命、主管職位或部門負責人設定。") }); return; }
    let force = false, q = text;
    const m = text.match(/^sql(!?)(\s+|$)/i);
    if (m) { force = m[1] === "!"; q = text.slice(m[0].length).trim(); }
    if (!q) { push({ k: "info", text: t("SQL 模式 — 透過 db exec 套用即時職責域;讀取直接返回,寫入建立持久 Passkey 操作卡") }); return; }
    if (force) push({ k: "info", text: t("sql! 只會把 force=true 寫入持久操作卡;仍須 Passkey 確認") });
    await doSql(q, force);
  };

  const switchMode = (m) => {
    if (m === mode) return;
    setMode(m);
    push({ k: "info", text: m === "ai"
      ? t("已進入 AI 會話模式:直接說要做什麼(多輪連續);!開頭直通指令;new 開新對話。")
      : m === "sql"
        ? t("已進入 SQL 模式:語句經 db exec 即時職責域檢查;所有寫入只建立持久操作卡,Passkey 確認後才執行。")
        : t("已切換到 CLI 指令模式:輸入平臺指令,help 查看已授權能力。") });
    focus();
  };

  const run = async (line) => {
    const text = (line || "").trim();
    if (!text) return;
    setHistory(h => [...h, text]);
    histRef.current = -1;
    push({ k: "cmd", mode, text });
    if (text === "clear" || text === "cls") { setItems([]); return; }
    if (mode === "sql") {
      if (text === "exit" || text === "quit") { switchMode("cli"); return; }
      await sqlPath(text);
      return;
    }
    if (mode === "ai") {
      if (text === "exit" || text === "quit" || text === "q") { setMode("cli"); push({ k: "info", text: t("已退出 AI 會話模式,回到 CLI。") }); return; }
      if (text === "new") { convRef.current = null; push({ k: "info", text: t("已開啟新對話(上下文已重置)。") }); return; }
      if (text.startsWith("!")) { await doExec(text.slice(1).trim()); return; }
      if (text === "help") { await doExec("help"); return; }
      await doAi(text);
      return;
    }
    /* CLI 模式 */
    if (text === "ai") { switchMode("ai"); return; }
    if (text.startsWith("ai ")) { const q = text.slice(3).trim().replace(/^["']+|["']+$/g, ""); if (q) await doAi(q); return; }
    if (/^sql!?(\s|$)/i.test(text)) { await sqlPath(text); return; }
    await doExec(text);
  };

  const ensureCmds = async () => {
    if (!cmdCacheRef.current) {
      try {
        const d = await W2.json("/api/cli/commands");
        cmdCacheRef.current = ((d && d.commands) || []).filter(c => c && c.allowed).map(c => c.command);
      } catch (e) { cmdCacheRef.current = []; }
    }
    return cmdCacheRef.current;
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !busy) { const v = input; setInput(""); run(v); }
    else if (e.key === "Tab") {
      const bang = mode === "ai" && input.startsWith("!");
      if (!(mode === "cli" || bang) || !input.trim()) return;   // 其餘情況不劫持 Tab
      e.preventDefault();
      const raw = bang ? input.slice(1) : input;
      ensureCmds().then(cmds => {
        const pool = bang
          ? cmds
          : [...cmds, "help", "capabilities", "capability search", "clear", "ai"];
        const matches = pool.filter(c => c.startsWith(raw));
        if (!matches.length) return;
        let prefix = matches[0];
        for (const mm of matches) {
          let i = 0;
          while (i < prefix.length && i < mm.length && prefix[i] === mm[i]) i++;
          prefix = prefix.slice(0, i);
        }
        setInput((bang ? "!" : "") + (matches.length === 1 ? matches[0] + " " : prefix));
        if (matches.length > 1 && prefix === raw) push({ k: "info", text: matches.join("    ") });
      });
    }
    else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!history.length) return;
      histRef.current = histRef.current === -1 ? history.length - 1 : Math.max(0, histRef.current - 1);
      setInput(history[histRef.current]);
    }
    else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (histRef.current === -1) return;
      histRef.current = histRef.current + 1 >= history.length ? -1 : histRef.current + 1;
      setInput(histRef.current === -1 ? "" : history[histRef.current]);
    }
  };

  const chips = CHIPS[mode] || CHIPS.cli;
  const placeholder = mode === "ai" ? t("跟內核說要做什麼…(!指令直通 · new 開新對話)")
    : mode === "sql" ? t("輸入 SQL…(經 db exec 職責域檢查 · 寫入建立 Passkey 操作卡)")
    : t("輸入平臺指令…(help 已授權能力 · capabilities 搜尋 · Tab 補全)");

  return (<>
    <Folio no="16" en="TERMINAL" title={t("超級終端")}
      sub={t("人與 AI 同一指令集 · 即時職責域 · 持久 Passkey 操作卡 · 全程審計")}
      right={showSql
        ? <span className="label" style={{ color: "var(--red)" }}>{t("DB EXEC — 即時職責域 · PASSKEY")}</span>
        : <span className="label">{t("以你的權限執行 · 全程審計")}</span>}/>

    {/* 模式 + 快捷命令(chips 只填入輸入行,不自動執行) */}
    <div className="row g14 wrap rise" style={{ padding: "16px 0 12px" }}>
      <div className="seg">
        <button className={mode === "cli" ? "on" : ""} onClick={() => switchMode("cli")}>CLI</button>
        <button className={mode === "ai" ? "on" : ""} onClick={() => switchMode("ai")}>{t("AI 會話")}</button>
        {showSql && <button className={mode === "sql" ? "on" : ""} onClick={() => switchMode("sql")}>SQL</button>}
      </div>
      <LB dim title={t("點擊填入輸入行,不會自動執行")}>{t("快捷命令")}</LB>
      <div className="row g6 wrap" style={{ flex: 1, minWidth: 260 }}>
        {chips.map(c => (
          <button key={c} className="chip mono" style={{ fontSize: 11, maxWidth: 340, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", lineHeight: "28px" }}
            title={mode === "ai" ? t(c) : c}
            onClick={() => { setInput(mode === "ai" ? t(c) : c); focus(); }}>
            {mode === "ai" ? t(c) : c}
          </button>
        ))}
        {mode === "sql" && <span style={{ ...MONO, fontSize: 9.5, color: "var(--ink-4)", alignSelf: "center" }}>
          {t("業務表請先回 CLI 執行 db schema --domain <你的業務域>,再依可見目錄撰寫 SQL。")}
        </span>}
      </div>
    </div>

    {/* 墨黑終端面板:頂部 2px 規線 + mono 標題行 */}
    <div className="rise" style={{ borderTop: "2px solid var(--rule)", animationDelay: ".05s" }}>
      <div className="col" style={{ background: "var(--ink)", height: "calc(100vh - 348px)", minHeight: 430 }}>
        {/* 標題行 */}
        <div className="row spread" style={{ padding: "10px 16px", borderBottom: "1px solid " + DK.hair, flexShrink: 0 }}>
          <span style={{ ...MONO, fontSize: 10.5, fontWeight: 600, letterSpacing: ".18em", color: DK.paper }}>
            TERMINAL — {company} · <span style={{ color: DK.red }}>AUDIT ON</span>
          </span>
          <div className="row g10">
            <span style={{ ...MONO, fontSize: 9, letterSpacing: ".16em", color: DK.dimmer }}>
              MODE: {mode.toUpperCase()}{busy ? " · BUSY" : ""}
            </span>
            <button style={DBTN} onClick={() => setItems([])} title="clear">{t("清屏")}</button>
          </div>
        </div>
        {/* 輸出區 */}
        <div ref={outRef} onClick={() => inputRef.current && inputRef.current.focus()}
          style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "14px 16px", cursor: "text",
            fontSize: 12.5, lineHeight: 1.65, color: DK.paper }}>
          <Welcome showSql={showSql}/>
          {items.map((item, i) => <TBlock key={i} item={item}/>)}
          {busy && <div style={{ ...MONO, fontSize: 11, color: DK.dim, marginTop: 6 }}>{mode === "ai" ? t("… 內核工作中") : t("… 執行中")}</div>}
        </div>
        {/* 附件暫存只保留顯示中繼資料;bytes 由服務端短效 handle 管理 */}
        {attachment && mode !== "sql" && (
          <div className="row g10" style={{ padding: "7px 16px", borderTop: "1px solid " + DK.hairSoft, color: DK.dim, flexShrink: 0 }}>
            <I name="doc" size={12}/>
            <span style={{ ...MONO, fontSize: 10.5, color: DK.paper, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {attachment.file_name}
            </span>
            <span style={{ ...MONO, fontSize: 9.5, whiteSpace: "nowrap" }}>{attachmentSize(attachment.file_size)}</span>
            <span style={{ ...MONO, fontSize: 9.5, whiteSpace: "nowrap" }}>{t("到期")} {attachmentExpiry(attachment.expires_at)}</span>
          </div>
        )}
        {/* 輸入行 */}
        <div className="row g10" style={{ padding: "11px 16px", borderTop: "1px solid " + DK.hair, flexShrink: 0 }}>
          <span style={{ ...MONO, fontSize: 13, fontWeight: 800, color: mode === "sql" ? DK.red : DK.paper }}>
            {promptOf(mode)}
          </span>
          <input ref={inputRef} value={input} disabled={busy} autoFocus spellCheck={false}
            onChange={e => setInput(e.target.value)} onKeyDown={onKeyDown} placeholder={busy ? "" : placeholder}
            style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: DK.paper,
              ...MONO, fontSize: 13, caretColor: mode === "sql" ? DK.red : DK.paper }}/>
          <input ref={attachmentInputRef} type="file" hidden
            onChange={event => {
              const files = Array.from(event.target.files || []);
              event.target.value = "";
              stageAttachment(files);
            }}/>
          {mode !== "sql" && <button type="button" style={{ ...DBTN, opacity: busy || attachmentBusy ? .5 : 1 }}
            disabled={busy || attachmentBusy}
            title={t(attachmentBusy ? "附件上傳中…" : "選擇附件")}
            onClick={() => attachmentInputRef.current && attachmentInputRef.current.click()}>
            <I name="inbound" size={11}/> {t(attachmentBusy ? "附件上傳中…" : "附件")}
          </button>}
          <span className="blink-dot" style={{ background: busy ? DK.red : DK.dimmer, width: 7, height: 7 }}/>
        </div>
      </div>
    </div>
  </>);
};

window.W2.PAGES["terminal"] = Page;
})();
