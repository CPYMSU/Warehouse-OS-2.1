/* Bonfire Research · discipline routes and versioned research notebooks. */
(() => {
const W2 = window.W2;
const { useState, useEffect } = React;
const disciplineOf = project => (project && (project.discipline ||
  (project.metadata || {}).research_discipline)) || "unclassified";
W2.researchDisciplineOf = disciplineOf;

const DisciplineMark = ({ code }) => <svg viewBox="0 0 92 52" aria-hidden="true">
  <path d="M2 44H90M12 2V50M38 2V50M64 2V50M90 2V50M2 18H90" className="rd-mark-grid"/>
  {code === "DS" ? <><path d="M12 36L30 27L45 33L63 13L82 7"/><circle cx="63" cy="13" r="4"/></> :
    code === "ES" ? <><path d="M15 37V12H48V37ZM48 24H80M69 13L80 24L69 35"/></> :
    code === "TS" ? <><path d="M13 39L44 7L76 39ZM28 24H61M44 7V39"/></> :
    <><path d="M12 7V43H83M18 12C38 13 39 37 80 38M18 37C40 36 44 13 80 12"/><circle cx="47" cy="25" r="4"/></>}
</svg>;

W2.ResearchDisciplineIndex = function ResearchDisciplineIndex({ catalogue, projects, filter, onFilter, onOpen, compact }) {
  if (!catalogue.length) return null;
  const count = key => projects.filter(project => disciplineOf(project) === key).length;
  return <section className={"rd-index" + (compact ? " is-compact" : "")} aria-label="科研專業分類" data-testid="research-disciplines">
    <header><div><span>RESEARCH / FOUR DISCIPLINES</span><h2>專業決定路徑。</h2></div>
      <div className="rd-index-filters"><button type="button" aria-pressed={filter === "all"} onClick={() => onFilter("all")}>全部科研 <b>{projects.length}</b></button>
        <button type="button" aria-pressed={filter === "unclassified"} onClick={() => onFilter("unclassified")}>待分類 <b>{count("unclassified")}</b></button></div>
    </header>
    <div className="rd-cards">{catalogue.map((item, index) => <button type="button" key={item.key}
      className={"rd-card rd-" + item.color + (filter === item.key ? " is-active" : "")}
      aria-pressed={filter === item.key} onClick={() => onOpen(item.key)} data-discipline={item.key}>
      <header><span>{String(index + 1).padStart(2, "0")} / {item.en}</span><b title="此專業課題數">{String(count(item.key)).padStart(2, "0")}</b></header>
      <div><h3>{item.title}</h3><DisciplineMark code={item.code}/></div>
      <footer><span>{item.stages.length} 步研究流程</span><span>進入專業 →</span></footer>
    </button>)}</div>
  </section>;
};

const stageDraftKey = (project, discipline, stage) => {
  const user = window.W2_USER || {};
  return "w2_research_discipline_draft:v1:" + [W2.tenant(), user.id || user.user_id || user.username || "anonymous",
    project.id, discipline, stage.key].map(value => encodeURIComponent(String(value || ""))).join(":");
};
const readDraft = key => {
  try { const saved = JSON.parse(localStorage.getItem(key) || "null");
    return saved && typeof saved.notes === "string" && ["planned", "in_progress", "completed"].includes(saved.status)
      && Number.isInteger(saved.base_revision) ? saved : null;
  } catch (_error) { return null; }
};
const StageEditor = ({ project, template, stage, saved, canWrite, onSaved, onError, onReload, onNavigate }) => {
  const key = stageDraftKey(project, template.key, stage);
  const [draft] = useState(() => readDraft(key));
  const [notes, setNotes] = useState(draft ? draft.notes : saved.notes || "");
  const [status, setStatus] = useState(draft ? draft.status : saved.status || "planned");
  const [baseRevision, setBaseRevision] = useState(draft ? draft.base_revision : saved.revision || 0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const conflict = baseRevision !== (saved.revision || 0);
  const dirty = notes !== (saved.notes || "") || status !== (saved.status || "planned");
  useEffect(() => {
    if (!canWrite || !dirty) return;
    try { localStorage.setItem(key, JSON.stringify({ notes, status, base_revision: baseRevision })); } catch (_error) {}
  }, [key, notes, status, baseRevision, dirty, canWrite]);
  const save = async event => {
    event.preventDefault();
    if (!canWrite || saving || conflict) return;
    setSaving(true); setMessage("");
    try {
      const result = await W2.json("/api/research/projects/" + encodeURIComponent(project.id) +
        "/discipline-workflow/stages/" + encodeURIComponent(stage.key), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ discipline: template.key, notes, status, expected_revision: baseRevision }),
      });
      try { localStorage.removeItem(key); } catch (_error) {}
      onSaved(result);
    } catch (reason) { setMessage(String(reason.message || reason)); onError(String(reason.message || reason)); }
    finally { setSaving(false); }
  };
  return <form className="rd-stage-editor" onSubmit={save} data-testid="research-stage-editor">
    <div className="rd-stage-brief"><span>RESEARCH PROMPT / 思考與驗證</span><p>{stage.prompt}</p></div>
    <label><span>研究筆記與本步產出 <small>{dirty ? "本機草稿 · 尚未保存至伺服器" : "版本 " + (saved.revision || 0)}</small></span>
      <textarea name="stage_notes" value={notes} maxLength={32000} readOnly={!canWrite}
        onChange={event => setNotes(event.target.value)} placeholder={stage.output + "。可記錄方程、變量、資料版本、證據位置與尚待解決的問題。"}/></label>
    {conflict && <div className="rd-conflict" role="alert"><b>已有較新的研究紀錄；你的草稿仍保留在本機。</b>
      <details><summary>比較伺服器上的內容</summary><pre>{saved.notes || "尚無筆記"}</pre></details>
      <button type="button" className="btn" onClick={() => setBaseRevision(saved.revision || 0)}>保留草稿，以此版本繼續編輯</button></div>}
    <div className="rd-stage-save"><label><span>研究進度</span><select name="stage_status" value={status} disabled={!canWrite}
      onChange={event => setStatus(event.target.value)}><option value="planned">未開始</option><option value="in_progress">進行中</option><option value="completed">研究者確認完成</option></select></label>
      {canWrite && <button className="btn primary" disabled={saving || conflict || (status === "completed" && !notes.trim())}>{saving ? "正在保存…" : "保存這一步"}</button>}
      <button type="button" className="btn" onClick={onReload}>重新載入版本</button></div>
    <p className="rd-save-note" role="status">{message || (saved.updated_at ? "上次保存：" + String(saved.updated_at).replace("T", " ").slice(0, 16) + " · 每次保存均保留一版研究計畫。" : "填寫產出後可確認完成；研究者標記的進度與同行覆核分開記錄。")}</p>
    <div className="rd-workspace-links"><span>繼續處理研究材料</span><button type="button" onClick={() => onNavigate(stage.workspace)}>進入對應工作區 ↗</button>
      {stage.workspace !== "evidence" && <button type="button" onClick={() => onNavigate("evidence")}>證據與覆核 ↗</button>}</div>
  </form>;
};

W2.ResearchDisciplineWorkspace = function ResearchDisciplineWorkspace({ catalogue, projects, project, filter,
  workflow, busy, canWrite, onProject, onClassify, classifying, onSaved, onReload, onNavigate, onError }) {
  const selectedKey = disciplineOf(project);
  const template = catalogue.find(item => item.key === selectedKey) || catalogue.find(item => item.key === filter) || catalogue[0];
  const [stageKey, setStageKey] = useState("");
  useEffect(() => { setStageKey(""); }, [project && project.id, template && template.key]);
  if (!template) return <div className="rv-loading">正在讀取專業流程…</div>;
  const state = workflow && workflow.discipline_workflow && workflow.discipline_workflow.discipline === template.key
    ? workflow.discipline_workflow : { stages: {}, completed: 0, total: template.stages.length };
  const stage = template.stages.find(item => item.key === stageKey) ||
    template.stages.find(item => (state.stages[item.key] || {}).status !== "completed") || template.stages[0];
  const bound = Boolean(project && selectedKey === template.key && workflow &&
    String(workflow.project.id) === String(project.id) && !busy);
  const index = template.stages.indexOf(stage) + 1;
  return <section className={"rd-workspace rd-" + template.color} data-testid="research-discipline-workspace">
    <div className="rd-project-context"><label><span>RESEARCH CONTEXT / 選擇課題</span><select value={project ? project.id : ""} onChange={event => onProject(event.target.value)}>
      <option value="" disabled>選擇一個課題</option>{projects.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      {project && <form key={project.id + ":" + selectedKey} onSubmit={event => { event.preventDefault(); onClassify(new FormData(event.currentTarget).get("discipline")); }}>
        <label><span>課題專業</span><select name="discipline" defaultValue={selectedKey} disabled={!canWrite || classifying}><option value="unclassified">待分類</option>{catalogue.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}</select></label>
        {canWrite && <button className="btn" disabled={classifying}>{classifying ? "正在保存…" : "保存分類"}</button>}</form>}
    </div>
    <div className="rd-flow-hero"><div><span>{template.code} / DISCIPLINE WORKFLOW</span><h2>{template.title}</h2><p>{template.motto}</p><small>{template.summary}</small></div>
      <aside><DisciplineMark code={template.code}/><b>{String(state.completed).padStart(2, "0")}<i>/{String(template.stages.length).padStart(2, "0")}</i></b><span>研究者確認完成</span></aside></div>
    {!bound && <p className="rd-context-note">{busy ? "正在載入此課題的研究紀錄…" : project ? "此課題尚未分類。上方保存專業後，即可記錄這套流程；既有研究資料會保留。" : "目前顯示流程預覽。請選擇或新建此專業的課題，再開始保存研究筆記。"}</p>}
    <div className="rd-flow-body"><nav className="rd-step-list" aria-label={template.title + "研究步驟"}>{template.stages.map((item, number) => {
      const status = (state.stages[item.key] || {}).status || "planned";
      return <button type="button" key={item.key} className={(item.key === stage.key ? "is-selected " : "") + status}
        aria-current={item.key === stage.key ? "step" : undefined} onClick={() => setStageKey(item.key)} data-stage={item.key}>
        <b>{String(number + 1).padStart(2, "0")}</b><div><strong>{item.title}</strong><small>{item.en}</small></div><i aria-label={status === "completed" ? "已完成" : status === "in_progress" ? "進行中" : "未開始"}/></button>;
    })}</nav><article className="rd-step-detail"><header><span>STEP {String(index).padStart(2, "0")} / {stage.en}</span><h3>{stage.title}</h3><p><b>本步產出</b>{stage.output}</p></header>
      {bound ? <StageEditor key={project.id + ":" + template.key + ":" + stage.key + ":" + ((state.stages[stage.key] || {}).revision || 0)}
        project={project} template={template} stage={stage} saved={state.stages[stage.key] || {}} canWrite={canWrite}
        onSaved={onSaved} onReload={onReload} onNavigate={onNavigate} onError={onError}/> : <div className="rd-stage-preview"><span>研究提示</span><p>{stage.prompt}</p></div>}
    </article></div>
    <footer className="rd-flow-footer"><b>ITERATE / RETURN / VERIFY</b><span>研究可以回到前一步修正假設與模型。專業流程保存思考過程，證據與覆核決定研究結論的可信度。</span></footer>
  </section>;
};
})();
