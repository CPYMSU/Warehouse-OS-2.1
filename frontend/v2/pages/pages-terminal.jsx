/* WAREHOUSE OS 2.1 · 超級終端
   保留終端的 Codex 式高密度視覺；輸入只描述業務目標，資料只經受權限
   保護的 Runtime 世界快照與共用 Auto Runtime 流動。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { useEffect, useRef, useState } = React;
const { Icon: I, Folio, Label: LB } = W2;

window.W2_LANG.addEN({
  "超級終端": "Super Terminal",
  "以你的權限讀取 PostgreSQL 世界狀態；描述目標，由 Runtime 規劃。": "Reads the PostgreSQL world through your permissions; describe a goal and let Runtime plan.",
  "目標": "Goal",
  "世界": "World",
  "活動": "Activity",
  "Skills": "Skills",
  "能力目錄": "Capability catalogue",
  "可探索的能力宇宙，不會直接執行命令。": "An explorable ability universe; it never directly executes commands.",
  "搜尋 Skills…": "Search Skills…",
  "讀取 Skills 中…": "Loading Skills…",
  "Skills 目錄暫時不可用": "Skills catalogue is temporarily unavailable",
  "顯示全部 {n} 個 Skills": "Show all {n} Skills",
  "收起 Skills": "Collapse Skills",
  "可用": "Ready",
  "待接入": "Adapter pending",
  "需治理授權": "Governance required",
  "需權限": "Permission required",
  "寫入需確認": "Writes require confirmation",
  "以此能力建立目標": "Create a goal from this Skill",
  "快捷工作流": "Quick workflows",
  "點擊填入輸入行，不會自動執行": "Click to fill the input line — never auto-runs",
  "新工作集": "New workset",
  "清屏": "Clear",
  "重新讀取 Skills": "Refresh Skills",
  "請描述你想達到的業務結果…": "Describe the business outcome you want…",
  "例如：找出低於安全庫存的物資，規劃本週補貨優先順序。": "For example: find items below safety stock and plan this week's replenishment priorities.",
  "工作集已重置。": "Workset reset.",
  "無法連接 Auto Runtime：": "Cannot connect to Auto Runtime: ",
  "尚未收到 Runtime 輸出。": "No Runtime output received yet.",
  "正在觀察世界": "Observing world",
  "正在制定能力計畫": "Planning capabilities",
  "已完成本輪理解": "Turn understood",
  "觀察": "Observe",
  "規劃": "Plan",
  "反思": "Reflect",
  "回答": "Response",
  "Runtime 目前提供目標理解、世界觀察與規劃；任何業務寫入都必須經專用能力與明確確認。": "Runtime currently provides goal understanding, world observation, and planning; every business write requires a dedicated capability and explicit confirmation.",
  "今天倉庫有哪些需要我優先處理的風險？": "What warehouse risks should I prioritize today?",
  "找出低於安全庫存的物資，規劃本週補貨優先順序。": "Find items below safety stock and plan this week's replenishment priorities.",
  "根據目前世界快照，整理待入庫、待出庫與在途工作。": "Use the current world snapshot to summarize inbound, outbound, and in-transit work.",
  "請解釋目前庫存與運輸異常的可能影響，列出需要補足的證據。": "Explain the likely impact of current inventory and shipment anomalies, and list evidence still needed.",
  "我想降低本週關鍵物資短缺風險，先給我可驗證的計畫。": "I want to reduce this week's critical material stockout risk. Give me a verifiable plan first.",
  "請根據我有權查看的資料，建立今日營運簡報大綱。": "Use only data I may view to draft an outline for today's operating brief.",
  "請回顧這輪目標的下一步與尚未確認的假設。": "Review the next step for this goal and the assumptions still unverified.",
});

const MONO = { fontFamily: "var(--f-mono)" };
const D = {
  paper: "var(--paper)", dim: "var(--ink-4)", dimmer: "var(--ink-3)", red: "var(--red)",
  hair: "rgba(245,242,235,.20)", hairSoft: "rgba(245,242,235,.10)",
};
const DBTN = { ...MONO, fontSize: 9.5, letterSpacing: ".12em", color: D.dim,
  border: "1px solid " + D.hair, background: "transparent", padding: "4px 10px" };
const clean = value => String(value == null ? "" : value).trim();
const numeric = value => typeof value === "number" && Number.isFinite(value) ? value : null;
const value = (item, fallback = "—") => {
  const number = numeric(item);
  return number == null ? fallback : new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(number);
};

const ART = [
  "█   █   ███    ████",
  "█   █  █   █  █    ",
  "█ █ █  █   █   ███ ",
  "█ █ █  █   █      █",
  " █ █    ███   ████ ",
].join("\n");

const LENSES = {
  goal: {
    label: "目標",
    chips: ["今天倉庫有哪些需要我優先處理的風險？", "我想降低本週關鍵物資短缺風險，先給我可驗證的計畫。", "請根據我有權查看的資料，建立今日營運簡報大綱。"],
  },
  world: {
    label: "世界",
    chips: ["找出低於安全庫存的物資，規劃本週補貨優先順序。", "根據目前世界快照，整理待入庫、待出庫與在途工作。", "請解釋目前庫存與運輸異常的可能影響，列出需要補足的證據。"],
  },
  activity: {
    label: "活動",
    chips: ["請回顧這輪目標的下一步與尚未確認的假設。", "請根據我有權查看的資料，建立今日營運簡報大綱。", "今天倉庫有哪些需要我優先處理的風險？"],
  },
  skills: { label: "Skills", chips: [] },
};

const skillState = skill => {
  if (skill && skill.ready) return { label: t("可用"), color: "#8FD19D" };
  if (skill && skill.authorized === false) return { label: t("需權限"), color: D.dimmer };
  if (skill && skill.state === "requires_l11_governance") return { label: t("需治理授權"), color: "#fbbf24" };
  return { label: t("待接入"), color: D.dim };
};

const SkillExplorer = ({ catalogue, loading, error, onSelect }) => {
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState(false);
  const skills = catalogue && Array.isArray(catalogue.skills) ? catalogue.skills : [];
  const terms = clean(query).toLowerCase();
  const filtered = skills.filter(skill => {
    if (!terms) return true;
    return [skill.name, skill.description, skill.category, skill.category_label, skill.skill_id]
      .some(item => clean(item).toLowerCase().includes(terms));
  });
  const limit = expanded ? filtered.length : 18;
  if (loading && !catalogue) return <div style={{ ...MONO, color: D.dim, fontSize: 10.5, padding: "10px 0" }}>… {t("讀取 Skills 中…")}</div>;
  if (!catalogue) return <div style={{ ...MONO, color: D.red, fontSize: 10.5, padding: "10px 0" }}>! {t("Skills 目錄暫時不可用")}{error ? " · " + error : ""}</div>;
  return <div style={{ borderTop: "1px solid " + D.hairSoft, borderBottom: "1px solid " + D.hairSoft, marginBottom: 14, padding: "11px 0 10px" }}>
    <div className="row spread wrap g10">
      <div><div style={{ ...MONO, color: D.paper, fontSize: 10.5, fontWeight: 700, letterSpacing: ".16em" }}>SKILLS — {value(catalogue.total, "0")}</div><div style={{ color: D.dim, fontSize: 11, marginTop: 3 }}>{t("可探索的能力宇宙，不會直接執行命令。")}</div></div>
      <div className="row g8"><span style={{ ...MONO, color: "#8FD19D", fontSize: 10 }}>{value(catalogue.ready, "0")} {t("可用")}</span><input value={query} onChange={event => { setQuery(event.target.value); setExpanded(false); }} placeholder={t("搜尋 Skills…")} style={{ width: 210, maxWidth: "48vw", background: "transparent", border: "1px solid " + D.hair, padding: "5px 8px", outline: "none", color: D.paper, ...MONO, fontSize: 11 }}/></div>
    </div>
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 1, background: D.hairSoft, marginTop: 10 }}>
      {filtered.slice(0, limit).map(skill => {
        const state = skillState(skill);
        return <button key={skill.skill_id} type="button" onClick={() => onSelect && onSelect(skill)} style={{ minWidth: 0, textAlign: "left", background: "rgba(0,0,0,.16)", border: 0, color: D.paper, padding: "9px 10px", cursor: "pointer" }} title={t("以此能力建立目標")}>
          <div className="row spread g8"><span style={{ ...MONO, fontSize: 11, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{clean(skill.name) || clean(skill.skill_id)}</span><span style={{ ...MONO, fontSize: 8.5, color: state.color, letterSpacing: ".06em", whiteSpace: "nowrap" }}>{state.label}</span></div>
          <div style={{ color: D.dim, fontSize: 10.5, lineHeight: 1.5, marginTop: 4, minHeight: 31 }}>{clean(skill.description) || "—"}</div>
          <div className="row g6 wrap" style={{ ...MONO, fontSize: 8.5, color: D.dimmer, marginTop: 5 }}><span>{clean(skill.category_label) || clean(skill.category)}</span>{skill.writes && <span style={{ color: "#fbbf24" }}>· {t("寫入需確認")}</span>}</div>
        </button>;
      })}
    </div>
    {!filtered.length && <div style={{ ...MONO, color: D.dimmer, fontSize: 10.5, paddingTop: 10 }}>—</div>}
    {filtered.length > 18 && <button type="button" style={{ ...DBTN, marginTop: 10 }} onClick={() => setExpanded(value => !value)}>{expanded ? "▴ " + t("收起 Skills") : "▾ " + t("顯示全部 {n} 個 Skills", { n: filtered.length })}</button>}
  </div>;
};

const StateMark = ({ phase }) => {
  const icon = phase === "observe" ? "eye" : phase === "plan" ? "layers" : "checkCircle";
  const label = phase === "observe" ? t("觀察") : phase === "plan" ? t("規劃") : t("反思");
  return <span style={{ ...MONO, display: "inline-flex", alignItems: "center", gap: 6, fontSize: 9.5, letterSpacing: ".12em", color: phase === "reflect" ? "#8FD19D" : D.dim }}><I name={icon} size={11}/>{label.toUpperCase()}</span>;
};

const Plan = ({ items }) => {
  const plan = Array.isArray(items) ? items : [];
  if (!plan.length) return null;
  return <ol style={{ ...MONO, margin: "6px 0 3px", paddingLeft: 22, color: D.dim, fontSize: 11, lineHeight: 1.65 }}>{plan.map((item, index) => <li key={index}>{clean(item)}</li>)}</ol>;
};

const Answer = ({ item }) => {
  const html = W2.mdToHtml ? W2.mdToHtml(item.message) : null;
  return <div style={{ margin: "8px 0 4px", maxWidth: 920 }}>
    <div style={{ background: D.paper, color: "var(--ink)", padding: "12px 14px", borderLeft: "3px solid " + D.red }}>
      {html != null ? <div className="md" style={{ fontSize: 12.5, lineHeight: 1.7, wordBreak: "break-word" }} dangerouslySetInnerHTML={{ __html: html }}/>
        : <div style={{ whiteSpace: "pre-wrap", fontSize: 12.5, lineHeight: 1.7 }}>{clean(item.message)}</div>}
    </div>
    <div style={{ ...MONO, marginTop: 4, fontSize: 9.5, letterSpacing: ".06em", color: D.dimmer }}>AUTO RUNTIME · {clean(item.model) || "—"} · {clean(item.status) || "succeeded"}</div>
  </div>;
};

const Output = ({ item }) => {
  if (item.kind === "goal") return <div style={{ marginTop: 14 }}><span style={{ ...MONO, display: "inline-block", maxWidth: "100%", padding: "3px 9px", background: D.paper, color: "var(--ink)", fontSize: 12, fontWeight: 700, wordBreak: "break-word" }}>goal&gt; {item.text}</span></div>;
  if (item.kind === "notice") return <div style={{ marginTop: 5, color: item.error ? D.red : D.dim, fontSize: 12, whiteSpace: "pre-wrap" }}>{item.text}</div>;
  if (item.kind === "observe") return <div style={{ marginTop: 8 }}><StateMark phase="observe"/></div>;
  if (item.kind === "plan") return <div style={{ marginTop: 8 }}><StateMark phase="plan"/><Plan items={item.plan}/></div>;
  if (item.kind === "reflect") return <div style={{ marginTop: 8 }}><StateMark phase="reflect"/><div style={{ fontSize: 11.5, lineHeight: 1.6, color: D.dim, marginTop: 4 }}>{t("Runtime 目前提供目標理解、世界觀察與規劃；任何業務寫入都必須經專用能力與明確確認。")}</div></div>;
  if (item.kind === "answer") return <Answer item={item}/>;
  return null;
};

const Welcome = () => <div style={{ paddingBottom: 8 }}>
  <pre style={{ fontFamily: "ui-monospace, Consolas, Menlo, monospace", fontSize: 11, lineHeight: 1.25, color: D.paper, margin: 0 }}>{ART}</pre>
  <div style={{ width: 72, height: 8, background: D.red, margin: "10px 0 12px" }}/>
  <div style={{ ...MONO, fontSize: 10, letterSpacing: ".2em", color: D.dim, marginBottom: 12 }}>WAREHOUSE OS 2.1 · CODEX TERMINAL</div>
  <div className="col g6" style={{ fontSize: 12, color: D.dim, maxWidth: 850, lineHeight: 1.7 }}>
    <div><span style={{ ...MONO, fontWeight: 700, color: D.paper }}>goal&gt;&nbsp;</span>{t("以你的權限讀取 PostgreSQL 世界狀態；描述目標，由 Runtime 規劃。")}</div>
    <div><span style={{ ...MONO, fontWeight: 700, color: D.paper }}>plan&gt;&nbsp; </span>observe → understand → plan → act → reflect</div>
    <div style={{ color: D.red, fontWeight: 650 }}>{t("Runtime 目前提供目標理解、世界觀察與規劃；任何業務寫入都必須經專用能力與明確確認。")}</div>
  </div>
</div>;

const Page = () => {
  const [items, setItems] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [lens, setLens] = useState("goal");
  const [history, setHistory] = useState([]);
  const [skills, setSkills] = useState(null);
  const [skillsLoading, setSkillsLoading] = useState(true);
  const [skillsError, setSkillsError] = useState("");
  const runRef = useRef(null);
  const inputRef = useRef(null);
  const outputRef = useRef(null);
  const historyCursor = useRef(-1);

  const loadSkills = async () => {
    setSkillsLoading(true);
    setSkillsError("");
    try {
      const next = await W2.json("/api/runtime/skills", { cache: "no-store" });
      setSkills(next && typeof next === "object" ? next : null);
    } catch (error) {
      setSkillsError(clean(error && error.message ? error.message : error));
    } finally { setSkillsLoading(false); }
  };

  useEffect(() => { loadSkills(); }, []);
  useEffect(() => { if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight; }, [items, busy]);

  const push = (...next) => setItems(previous => [...previous, ...next]);
  const focus = () => setTimeout(() => inputRef.current && inputRef.current.focus(), 40);
  const reset = () => {
    runRef.current = null;
    setItems([]);
    push({ kind: "notice", text: t("工作集已重置。") });
    focus();
  };
  const run = async text => {
    const goal = clean(text);
    if (!goal || busy) return;
    setInput("");
    setBusy(true);
    setHistory(previous => [...previous, goal]);
    historyCursor.current = -1;
    push({ kind: "goal", text: goal });
    try {
      await W2.agentStream({ text: goal, conversation_id: runRef.current, surface: "super_terminal" }, event => {
        if (!event || !event.event) return;
        if (event.event === "run_start") { runRef.current = event.conversation_id || runRef.current; return; }
        if (event.event === "runtime_state" && event.phase === "observe") {
          push({ kind: "observe" });
          return;
        }
        if (event.event === "runtime_state" && event.phase === "plan") { push({ kind: "plan", plan: event.plan }); return; }
        if (event.event === "runtime_state" && event.phase === "reflect") { push({ kind: "reflect" }); return; }
        if (event.event === "final") push({ kind: "answer", message: event.message || t("尚未收到 Runtime 輸出。"), model: event.engine, status: event.status });
      });
    } catch (error) {
      push({ kind: "notice", error: true, text: t("無法連接 Auto Runtime：") + clean(error && error.message ? error.message : error) });
    } finally { setBusy(false); focus(); }
  };
  const onKeyDown = event => {
    if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); run(input); return; }
    if (event.key === "ArrowUp") {
      if (!history.length) return;
      event.preventDefault();
      historyCursor.current = historyCursor.current < 0 ? history.length - 1 : Math.max(0, historyCursor.current - 1);
      setInput(history[historyCursor.current]);
      return;
    }
    if (event.key === "ArrowDown") {
      if (historyCursor.current < 0) return;
      event.preventDefault();
      historyCursor.current = historyCursor.current + 1 >= history.length ? -1 : historyCursor.current + 1;
      setInput(historyCursor.current < 0 ? "" : history[historyCursor.current]);
    }
  };
  const activeLens = LENSES[lens] || LENSES.goal;
  const company = clean(W2.tenant()) || "—";

  return <>
    <Folio no="16" en="TERMINAL" title={t("超級終端")} sub={t("Codex 式終端 · 全程審計")}
      right={<span className="label" style={{ color: "var(--red)" }}>AUDIT ON · RUNTIME</span>}/>
    <div className="row g14 wrap rise" style={{ padding: "16px 0 12px" }}>
      <div className="seg">{Object.keys(LENSES).map(key => <button key={key} className={lens === key ? "on" : ""} type="button" onClick={() => setLens(key)}>{t(LENSES[key].label)}</button>)}</div>
      <LB dim title={t("點擊填入輸入行，不會自動執行")}>{lens === "skills" ? t("能力目錄") : t("快捷工作流")}</LB>
      <div className="row g6 wrap" style={{ flex: 1, minWidth: 260 }}>{lens === "skills"
        ? <span style={{ ...MONO, color: D.dim, fontSize: 10.5 }}>{skillsLoading ? t("讀取 Skills 中…") : value(skills && skills.total, "0") + " · " + t("可探索的能力宇宙，不會直接執行命令。")}</span>
        : activeLens.chips.map(chip => <button key={chip} type="button" className="chip mono" style={{ fontSize: 11, maxWidth: 390, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", display: "inline-block", lineHeight: "28px" }} title={t(chip)} onClick={() => { setInput(t(chip)); focus(); }}>{t(chip)}</button>)}</div>
    </div>
    <div className="rise" style={{ borderTop: "2px solid var(--rule)", animationDelay: ".05s" }}>
      <div className="col" style={{ background: "var(--ink)", height: "calc(100vh - 348px)", minHeight: 480 }}>
        <div className="row spread" style={{ padding: "10px 16px", borderBottom: "1px solid " + D.hair, flexShrink: 0 }}>
          <span style={{ ...MONO, fontSize: 10.5, fontWeight: 600, letterSpacing: ".18em", color: D.paper }}>TERMINAL — {company} · <span style={{ color: D.red }}>AUDIT ON</span></span>
          <div className="row g10"><span style={{ ...MONO, fontSize: 9, letterSpacing: ".16em", color: D.dimmer }}>MODE: {lens.toUpperCase()}{busy ? " · BUSY" : ""}</span>{lens === "skills" && <button type="button" style={DBTN} disabled={skillsLoading} onClick={loadSkills}><I name="refresh" size={11}/> {t("重新讀取 Skills")}</button>}<button type="button" style={DBTN} onClick={reset}>{t("新工作集")}</button><button type="button" style={DBTN} onClick={() => setItems([])} title="clear">{t("清屏")}</button></div>
        </div>
        <div ref={outputRef} onClick={focus} style={{ flex: 1, minHeight: 0, overflowY: "auto", padding: "14px 16px", cursor: "text", fontSize: 12.5, lineHeight: 1.65, color: D.paper }}>
          {lens === "skills" && <SkillExplorer catalogue={skills} loading={skillsLoading} error={skillsError} onSelect={skill => { setLens("goal"); setInput("我想以「" + clean(skill.name) + "」這項能力完成："); focus(); }}/>}
          <Welcome/>
          {items.map((item, index) => <Output key={index} item={item}/>)}
          {busy && <div style={{ ...MONO, fontSize: 11, color: D.dim, marginTop: 8 }}>… {t("正在觀察世界")}</div>}
        </div>
        <div style={{ padding: "7px 16px", borderTop: "1px solid " + D.hairSoft, color: D.dimmer, fontSize: 10.5, lineHeight: 1.5 }}>{t("Runtime 目前提供目標理解、世界觀察與規劃；任何業務寫入都必須經專用能力與明確確認。")}</div>
        <div className="row g10" style={{ padding: "11px 16px", borderTop: "1px solid " + D.hair, flexShrink: 0 }}>
          <span style={{ ...MONO, fontSize: 13, fontWeight: 800, color: D.paper }}>goal&gt;</span>
          <input ref={inputRef} value={input} disabled={busy} autoFocus spellCheck={false} onChange={event => setInput(event.target.value)} onKeyDown={onKeyDown} placeholder={busy ? "" : t("請描述你想達到的業務結果…")} title={t("例如：找出低於安全庫存的物資，規劃本週補貨優先順序。")} style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: D.paper, ...MONO, fontSize: 13 }}/>
          <span className="blink-dot" style={{ background: busy ? D.red : D.dimmer, width: 7, height: 7 }}/>
        </div>
      </div>
    </div>
  </>;
};

window.W2.PAGES["terminal"] = Page;
})();
