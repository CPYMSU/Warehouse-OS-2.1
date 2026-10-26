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
    return saved && typeof saved.notes === "string" && ["planned", "in_progress", "blocked", "completed"].includes(saved.status)
      && Number.isInteger(saved.base_revision) ? saved : null;
  } catch (_error) { return null; }
};
const StageEditor = ({ project, template, stage, saved, canWrite, onSaved, onError, onReload, onNavigate }) => {
  const key = stageDraftKey(project, template.key, stage);
  const [draft] = useState(() => readDraft(key));
  const [notes, setNotes] = useState(draft ? draft.notes : saved.notes || "");
  const [status, setStatus] = useState(draft ? draft.status : saved.status || "planned");
  const [baseRevision, setBaseRevision] = useState(draft ? draft.base_revision : saved.revision || 0);
  const [fields, setFields] = useState(() => {
    const source = draft && draft.fields || saved;
    return {plan:String(source.plan || ""),findings:String(source.findings || ""),blockers:String(source.blockers || ""),
      next_action:String(source.next_action || ""),assignee:["user","codex","shared"].includes(source.assignee)?source.assignee:"shared"};
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const conflict = baseRevision !== (saved.revision || 0);
  const dirty = notes !== (saved.notes || "") || status !== (saved.status || "planned") ||
    Object.entries(fields).some(([name,value]) => value !== (saved[name] || (name === "assignee" ? "shared" : "")));
  useEffect(() => {
    if (!canWrite || !dirty) return;
    try { localStorage.setItem(key, JSON.stringify({ notes, status, fields, base_revision: baseRevision })); } catch (_error) {}
  }, [key, notes, status, fields, baseRevision, dirty, canWrite]);
  const persist = async artifacts => {
    if (!canWrite || saving || conflict) throw new Error("請先處理版本衝突，再保存本步研究紀錄。");
    setSaving(true); setMessage("");
    try {
      const result = await W2.json("/api/research/projects/" + encodeURIComponent(project.id) +
        "/discipline-workflow/stages/" + encodeURIComponent(stage.key), {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ discipline: template.key, notes, status, expected_revision: baseRevision, ...fields,
          ...(Array.isArray(artifacts) ? {artifacts:artifacts.map(item => ({file_version_id:item.file_version_id,role:item.role || "other",title:item.title || ""}))} : {}) }),
      });
      try { localStorage.removeItem(key); } catch (_error) {}
      onSaved(Array.isArray(artifacts) ? {...result,artifacts_changed:true} : result);
      return result;
    } catch (reason) { setMessage(String(reason.message || reason)); onError(String(reason.message || reason)); throw reason; }
    finally { setSaving(false); }
  };
  const save = async event => { event.preventDefault(); try { await persist(); } catch (_error) {} };
  const attach = artifact => persist([...(saved.artifacts || []).filter(item => item.file_version_id !== artifact.file_version_id),artifact]);
  const setField = (name,value) => setFields(current => ({...current,[name]:value}));
  return <form className="rd-stage-editor" onSubmit={save} data-testid="research-stage-editor">
    <div className="rd-stage-brief"><span>RESEARCH PROMPT / 思考與驗證</span><p>{stage.prompt}</p></div>
    <div className="rc-research-fields"><label><span>本步設計與計畫</span><textarea name="stage_plan" value={fields.plan} maxLength={16000} readOnly={!canWrite}
      onChange={event=>setField("plan",event.target.value)} placeholder="要完成什麼、採用哪些方法、需要哪些資料與產出？"/></label></div>
    <label><span>研究筆記與本步產出 <small>{dirty ? "本機草稿 · 尚未保存至伺服器" : "版本 " + (saved.revision || 0)}</small></span>
      <textarea name="stage_notes" value={notes} maxLength={32000} readOnly={!canWrite}
        onChange={event => setNotes(event.target.value)} placeholder={stage.output + "。可記錄方程、變量、資料版本、證據位置與尚待解決的問題。"}/></label>
    <div className="rc-research-fields rc-research-details"><label><span>發現與研究細節</span><textarea name="stage_findings" value={fields.findings} maxLength={32000} readOnly={!canWrite}
      onChange={event=>setField("findings",event.target.value)} placeholder="記錄結果、模型假設、變量關係、限制與證據位置。"/></label>
      <label><span>下一步行動</span><textarea name="stage_next_action" value={fields.next_action} maxLength={8000} readOnly={!canWrite}
        onChange={event=>setField("next_action",event.target.value)} placeholder="下一個具體動作，以及由誰接續。"/></label>
      <label><span>待解問題與需要用戶補充的內容</span><textarea name="stage_blockers" value={fields.blockers} maxLength={8000} readOnly={!canWrite}
        onChange={event=>setField("blockers",event.target.value)} placeholder="缺少的資料、需要討論的假設或尚未通過的驗證。"/></label></div>
    {conflict && <div className="rd-conflict" role="alert"><b>已有較新的研究紀錄；你的草稿仍保留在本機。</b>
      <details><summary>比較伺服器上的內容</summary><pre>{saved.notes || "尚無筆記"}</pre></details>
      <button type="button" className="btn" onClick={() => setBaseRevision(saved.revision || 0)}>保留草稿，以此版本繼續編輯</button></div>}
    <div className="rd-stage-save"><label><span>研究進度</span><select name="stage_status" value={status} disabled={!canWrite}
      onChange={event => setStatus(event.target.value)}><option value="planned">未開始</option><option value="in_progress">進行中</option><option value="blocked">待補充／有阻礙</option><option value="completed">研究者確認完成</option></select></label>
      <label><span>協作分工</span><select name="stage_assignee" value={fields.assignee} disabled={!canWrite} onChange={event=>setField("assignee",event.target.value)}>
        <option value="shared">用戶與 Codex 共同處理</option><option value="user">用戶處理</option><option value="codex">Codex 處理</option></select></label>
      {canWrite && <button className="btn primary" disabled={saving || conflict || (status === "completed" && !notes.trim())}>{saving ? "正在保存…" : "保存這一步"}</button>}
      <button type="button" className="btn" onClick={onReload}>重新載入版本</button></div>
    <p className="rd-save-note" role="status">{message || (saved.updated_at ? "上次保存：" + String(saved.updated_at).replace("T", " ").slice(0, 16) + " · 每次保存均保留一版研究計畫。" : "填寫產出後可確認完成；研究者標記的進度與同行覆核分開記錄。")}</p>
    {W2.ResearchStageCollaboration && <W2.ResearchStageCollaboration project={project} template={template} stage={stage} saved={saved}
      canWrite={canWrite} hasDraft={canWrite && dirty} saving={saving || conflict || (status === "completed" && !notes.trim())} onAttach={attach} onError={onError}/>}
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
  const progress = template.stages.reduce((sum,item)=>{
    const entry=state.stages[item.key] || {};
    if(entry.status === "in_progress")sum.active++;
    if(entry.status === "blocked")sum.blocked++;
    (entry.artifacts || []).forEach(artifact=>sum.outputs.add(artifact.file_version_id));
    return sum;
  },{active:0,blocked:0,outputs:new Set()});
  const nextStep = template.stages.find(item=>(state.stages[item.key]||{}).status === "blocked") ||
    template.stages.find(item=>(state.stages[item.key]||{}).status !== "completed");
  return <section className={"rd-workspace rd-" + template.color} data-testid="research-discipline-workspace">
    <div className="rd-project-context"><label><span>RESEARCH CONTEXT / 選擇課題</span><select value={project ? project.id : ""} onChange={event => onProject(event.target.value)}>
      <option value="" disabled>選擇一個課題</option>{projects.map(item => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>
      {project && <form key={project.id + ":" + selectedKey} onSubmit={event => { event.preventDefault(); onClassify(new FormData(event.currentTarget).get("discipline")); }}>
        <label><span>課題專業</span><select name="discipline" defaultValue={selectedKey} disabled={!canWrite || classifying}><option value="unclassified">待分類</option>{catalogue.map(item => <option key={item.key} value={item.key}>{item.title}</option>)}</select></label>
        {canWrite && <button className="btn" disabled={classifying}>{classifying ? "正在保存…" : "保存分類"}</button>}</form>}
    </div>
    <div className="rd-flow-hero"><div><span>{template.code} / DISCIPLINE WORKFLOW</span><h2>{template.title}</h2><p>{template.motto}</p><small>{template.summary}</small></div>
      <aside><DisciplineMark code={template.code}/><b>{String(state.completed).padStart(2, "0")}<i>/{String(template.stages.length).padStart(2, "0")}</i></b><span>研究者確認完成</span></aside></div>
    {bound && <section className="rc-project-progress" aria-label="項目研究進度" data-testid="research-project-progress">
      <div className="rc-progress-metrics"><article><span>COMPLETED / 已完成</span><b>{state.completed}<i>/{template.stages.length}</i></b></article>
        <article><span>IN PROGRESS / 進行中</span><b>{progress.active}</b></article><article className={progress.blocked ? "has-blockers" : ""}><span>NEEDS INPUT / 待補充</span><b>{progress.blocked}</b></article>
        <article><span>OUTPUTS / 版本化產物</span><b>{progress.outputs.size}</b></article></div>
      <div className="rc-progress-track" aria-label="研究步驟進度">{template.stages.map((item,number)=><button type="button" key={item.key}
        className={(state.stages[item.key]||{}).status || "planned"} onClick={()=>setStageKey(item.key)} title={item.title} aria-label={String(number+1)+" · "+item.title}>{String(number+1).padStart(2,"0")}</button>)}</div>
      {nextStep && <button type="button" className="rc-next-step" onClick={()=>setStageKey(nextStep.key)}><span>NEXT / 下一步</span><strong>{nextStep.title}</strong><p>{(state.stages[nextStep.key]||{}).next_action || (state.stages[nextStep.key]||{}).blockers || nextStep.output}</p><b>接續研究 →</b></button>}
    </section>}
    {!bound && <p className="rd-context-note">{busy ? "正在載入此課題的研究紀錄…" : project ? "此課題尚未分類。上方保存專業後，即可記錄這套流程；既有研究資料會保留。" : "目前顯示流程預覽。請選擇或新建此專業的課題，再開始保存研究筆記。"}</p>}
    <div className="rd-flow-body"><nav className="rd-step-list" aria-label={template.title + "研究步驟"}>{template.stages.map((item, number) => {
      const status = (state.stages[item.key] || {}).status || "planned";
      return <button type="button" key={item.key} className={(item.key === stage.key ? "is-selected " : "") + status}
        aria-current={item.key === stage.key ? "step" : undefined} onClick={() => setStageKey(item.key)} data-stage={item.key}>
        <b>{String(number + 1).padStart(2, "0")}</b><div><strong>{item.title}</strong><small>{item.en}</small>
          {(state.stages[item.key]||{}).assignee && <em className="rc-step-assignee">{{user:"用戶",codex:"Codex",shared:"共同協作"}[(state.stages[item.key]||{}).assignee]}</em>}</div><i aria-label={status === "completed" ? "已完成" : status === "blocked" ? "待補充" : status === "in_progress" ? "進行中" : "未開始"}/></button>;
    })}</nav><article className="rd-step-detail"><header><span>STEP {String(index).padStart(2, "0")} / {stage.en}</span><h3>{stage.title}</h3><p><b>本步產出</b>{stage.output}</p></header>
      {bound ? <StageEditor key={project.id + ":" + template.key + ":" + stage.key + ":" + ((state.stages[stage.key] || {}).revision || 0)}
        project={project} template={template} stage={stage} saved={state.stages[stage.key] || {}} canWrite={canWrite}
        onSaved={onSaved} onReload={onReload} onNavigate={onNavigate} onError={onError}/> : <div className="rd-stage-preview"><span>研究提示</span><p>{stage.prompt}</p></div>}
    </article></div>
    <footer className="rd-flow-footer"><b>ITERATE / RETURN / VERIFY</b><span>研究可以回到前一步修正假設與模型。專業流程保存思考過程，證據與覆核決定研究結論的可信度。</span></footer>
  </section>;
};
})();
