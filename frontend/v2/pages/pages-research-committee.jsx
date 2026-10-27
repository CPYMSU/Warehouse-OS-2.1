/* The defense room is a simulated, project-scoped practice conversation. */
(() => {
const W2 = window.W2;
const {useState, useEffect, useRef} = React;
const value = x => x == null ? '' : String(x);
const number = x => String(x).padStart(2, '0');
const date = x => x ? value(x).replace('T', ' ').slice(0, 16) : '—';
const storageKey = (project, session) => {
  const user = window.W2_USER || {};
  return 'w2_committee_answer:v2:' + [W2.tenant() || 'default', user.gid || user.global_user_id || user.id || user.user_id || user.username || 'anonymous', project, session.id].map(x => encodeURIComponent(value(x))).join(':');
};
const savedDrafts = key => { try { const parsed = JSON.parse(localStorage.getItem(key) || '{}'); return parsed && typeof parsed === 'object' ? parsed : {}; } catch (_error) { return {}; } };
const draftId = (revision, question) => value(revision) + '|' + value(question);
const keepAnswer = (key, revision, question, answer) => { try {
  const drafts = savedDrafts(key);
  const id = draftId(revision, question);
  if (answer) drafts[id] = {question: value(question), answer}; else delete drafts[id];
  if (Object.keys(drafts).length) localStorage.setItem(key, JSON.stringify(drafts)); else localStorage.removeItem(key);
} catch (_error) {} };
const read = path => W2.json(path, {cache: 'no-store', transientGetRetries: 6});
const post = (path, payload) => W2.json(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
const errorText = error => {
  if (error && error.status === 409) return '研究材料或本場記錄已更新。你的草稿仍保留，請重新讀取後確認。';
  if (error && (error.status >= 500 || !error.status)) return '委員暫時無法回應，請稍後重試。你的回答草稿仍保留。';
  const message = value(error && error.message);
  return message && message.length < 200 ? message : '暫時無法完成操作，請稍後重試。';
};

W2.ResearchCommittee = function ResearchCommittee({project, projects, onProject, canWrite}) {
  const projectId = value(project && project.id);
  const base = '/api/research/projects/' + encodeURIComponent(projectId) + '/committee';
  const [professors, setProfessors] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [session, setSession] = useState(null);
  const [chosen, setChosen] = useState('');
  const [answer, setAnswer] = useState('');
  const [recovered, setRecovered] = useState([]);
  const [sourceChanged, setSourceChanged] = useState(false);
  const [nextOffset, setNextOffset] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingOlder, setLoadingOlder] = useState(false);
  const [working, setWorking] = useState('');
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const epoch = useRef(0);
  const lock = useRef(false);
  const liveSession = session && value(session.id);
  const selected = sessions.find(item => value(item.id) === chosen) || session;
  const latest = selected && value(selected.id) === liveSession;
  const activeId = selected && selected.current && selected.current.professor_id;
  const selectedSourceChanged = Boolean(selected && (selected.source_changed || (latest && sourceChanged)));
  const active = professors.find(person => value(person.id) === value(activeId));
  const turns = selected && Array.isArray(selected.turns) ? selected.turns : [];
  const key = selected ? storageKey(projectId, selected) : '';
  const replace = next => {
    setSession(next);
    setSessions(current => [next, ...current.filter(item => value(item.id) !== value(next.id))]);
    setChosen(value(next.id));
  };
  const load = async requestEpoch => {
    if (!projectId) return;
    setLoading(true); setError('');
    try {
      const data = await read(base);
      if (requestEpoch !== epoch.current) return;
      setProfessors(Array.isArray(data.professors) ? data.professors : []);
      const all = Array.isArray(data.sessions) ? data.sessions : [];
      setSessions(all);
      setNextOffset(data.next_offset == null ? null : data.next_offset);
      setSession(data.session || null);
      setChosen(current => all.some(item => value(item.id) === current) ? current : value(data.session && data.session.id));
      setSourceChanged(Boolean(data.source_changed));
    } catch (reason) { if (requestEpoch === epoch.current) setError(errorText(reason)); }
    finally { if (requestEpoch === epoch.current) setLoading(false); }
  };
  useEffect(() => {
    const requestEpoch = ++epoch.current;
    setProfessors([]); setSessions([]); setSession(null); setChosen(''); setAnswer(''); setRecovered([]); setError(''); setNotice(''); setSourceChanged(false); setNextOffset(null); setLoadingOlder(false); setWorking('');
    lock.current = false;
    load(requestEpoch);
    return () => { epoch.current += 1; };
  }, [projectId]);
  useEffect(() => {
    const drafts = key ? savedDrafts(key) : {}, revision = selected && value(selected.revision), question = value(selected && selected.current && selected.current.question);
    const id = draftId(revision, question), draft = drafts[id];
    setAnswer(draft && draft.question === question ? value(draft.answer) : '');
    setRecovered(Object.entries(drafts).reverse().filter(([savedId, item]) => item && item.answer && savedId !== id).map(([, item]) => item));
  }, [key, selected && selected.revision, selected && selected.current && selected.current.question]);
  const start = async () => {
    if (!canWrite || !projectId || lock.current) return;
    const requestEpoch = epoch.current;
    lock.current = true; setWorking('start'); setError(''); setNotice('');
    try {
      const result = await post(base + '/start', {});
      if (requestEpoch !== epoch.current) return;
      if (!result.session) throw new Error('缺少答辯記錄');
      if (Array.isArray(result.professors)) setProfessors(result.professors);
      replace(result.session); setSourceChanged(false); setNotice('新一場答辯已開始。');
    } catch (reason) { if (requestEpoch === epoch.current) setError(errorText(reason)); }
    finally { if (requestEpoch === epoch.current) { lock.current = false; setWorking(''); } }
  };
  const older = async () => {
    if (nextOffset == null || loadingOlder || lock.current) return;
    const requestEpoch = epoch.current;
    setLoadingOlder(true); setError('');
    try {
      const data = await read(base + '?offset=' + encodeURIComponent(nextOffset));
      if (requestEpoch !== epoch.current) return;
      setSessions(current => [...current, ...(data.sessions || []).filter(item => !current.some(old => value(old.id) === value(item.id)))]);
      setNextOffset(data.next_offset == null ? null : data.next_offset);
    } catch (reason) { if (requestEpoch === epoch.current) setError(errorText(reason)); }
    finally { if (requestEpoch === epoch.current) setLoadingOlder(false); }
  };
  const submit = async event => {
    event.preventDefault();
    if (!canWrite || !selected || !selected.current || !answer.trim() || selectedSourceChanged || lock.current) return;
    const requestEpoch = epoch.current, submittedKey = key, submittedRevision = selected.revision, submittedQuestion = selected.current.question;
    lock.current = true; setWorking('answer'); setError(''); setNotice('');
    try {
      const result = await post(base + '/' + encodeURIComponent(selected.id) + '/answer', {expected_revision: selected.revision, answer: answer.trim()});
      if (requestEpoch !== epoch.current) return;
      if (!result.session) throw new Error('缺少答辯記錄');
      keepAnswer(submittedKey, submittedRevision, submittedQuestion, '');
      if (Array.isArray(result.professors)) setProfessors(result.professors);
      replace(result.session); setSourceChanged(Boolean(result.session.source_changed)); setAnswer(''); setNotice('回答已保存，請查看委員的回應。');
    } catch (reason) { if (requestEpoch === epoch.current) setError(errorText(reason)); }
    finally { if (requestEpoch === epoch.current) { lock.current = false; setWorking(''); } }
  };
  const professor = id => professors.find(person => value(person.id) === value(id)) || {number: id, title: '模擬委員'};
  const answered = new Set(turns.map(turn => value(turn.professor_id)));
  return <div className="bcm" data-testid="research-committee">
    <section className="bcm-masthead">
      <div className="bcm-heading"><div className="bcm-kicker"><span>THE DEFENSE ROOM</span><span>RESEARCH / 21</span></div>
        <h2>把研究，<br/><em>說給世界聽。</em></h2>
        <p>21 位 AI 模擬教授，從最簡單的問題開始。練習用自己的話，讓每個人都能明白你的研究。</p>
        <div className="bcm-tags"><span>01 / 聽懂問題</span><span>02 / 說清想法</span><span>03 / 繼續交流</span></div>
      </div>
      <aside className="bcm-index"><span>SIMULATED COMMITTEE</span><strong>21<span>席</span></strong><small>AI 模擬教授與學術委員<br/>圍繞目前課題交流</small><i>✳</i></aside>
    </section>
    <section className="bcm-control"><div><span>CURRENT RESEARCH / 目前課題</span><label htmlFor="bcm-project" className="bcm-sr-only">選擇答辯課題</label>
      <select id="bcm-project" data-testid="research-committee-project" value={projectId} disabled={Boolean(working)} onChange={event => onProject(event.target.value)}>
        {!projectId && <option value="">請先建立或選擇課題</option>}{(projects || []).map(item => <option key={item.id} value={item.id}>{item.title}</option>)}
      </select></div><div className="bcm-control-note"><b>由你的論文出發</b><span>提問關注研究問題、概念、方法與現實意義。</span></div>
      <button type="button" className="bcm-start" data-testid="research-committee-start" disabled={!canWrite || !projectId || loading || Boolean(working)} onClick={start}>{working === 'start' ? '委員正在準備…' : session ? '開啟新一場 ↗' : '開始模擬答辯 ↗'}</button>
    </section>
    {loading && <div className="bcm-status" role="status"><span className="bcm-spinner"/><div><b>正在準備答辯室</b><small>讀取課題與歷史對話</small></div></div>}
    {working && <div className="bcm-status" role="status" aria-live="polite"><span className="bcm-spinner"/><div><b>{working === 'start' ? '委員正在閱讀你的研究…' : '委員正在理解你的回答…'}</b><small>閱讀上下文 → 整理簡短回應</small></div></div>}
    {error && <div className="bcm-error" role="alert"><span>{error}</span><button type="button" onClick={() => load(epoch.current)} disabled={loading || Boolean(working)}>重新讀取 ↻</button></div>}
    {notice && <p className="bcm-notice" role="status">{notice}</p>}
    {selectedSourceChanged && selected && <div className="bcm-warning">課題材料已有變動。這場對話仍然保留；開啟新一場可根據最新材料提問。</div>}
    {project && !loading && <>
      <section className="bcm-room" aria-label="模擬答辯委員席"><div className="bcm-room-title"><div><span>THE COMMITTEE / 模擬委員席</span><h3>一個問題，一次交流。</h3></div><div className="bcm-progress"><strong>{number(turns.length)}<small> / 21</small></strong><span>已完成的對話</span></div></div>
        <div className="bcm-seats" aria-label="21 位虛擬委員">{(professors.length ? professors : Array.from({length: 21}, (_, i) => ({id:i+1,number:i+1,title:'虛擬委員'}))).map((person, index) => {
          const id = value(person.id), isActive = id === value(activeId), isDone = answered.has(id);
          return <div key={id || index} className={'bcm-seat' + (isActive ? ' active' : '') + (isDone ? ' done' : '')} aria-label={(person.title || '虛擬委員') + '，' + (person.focus || '研究交流') + (isActive ? '，正在提問' : isDone ? '，已完成' : '，待交流')}><span>{number(person.number || index + 1)}</span><b>{person.title || '虛擬委員'}</b><small>{person.focus || '研究交流'}</small></div>;
        })}</div><div className="bcm-room-foot"><span><i/> 正在提問</span><span><i/> 已完成交流</span><span>VIRTUAL FACULTY / 21 SEATS</span></div>
      </section>
      {!selected && !working && <div className="bcm-empty"><span>READY WHEN YOU ARE / 01</span><h3>準備好，就坐下來聊聊。</h3><p>委員會將先讀取你的課題材料，再提出一個容易開始的問題。每次回答後會收到簡短回應。</p>{!canWrite && <small>此帳戶可閱讀已保存的對話；開始答辯需要研究寫入權限。</small>}</div>}
      {selected && <section className="bcm-conversation" data-testid="research-committee-conversation">
        <header><div><span>CONVERSATION / 答辯交流</span><h3>{latest ? '現在的這一場' : '過往答辯記錄'}</h3></div><label>查看場次 <select data-testid="research-committee-session" value={value(selected.id)} onChange={event => {setChosen(event.target.value); setNotice(''); setError('');}} disabled={Boolean(working)}>{sessions.map((item, index) => <option key={item.id} value={item.id}>{index === 0 ? '目前場次' : '過往場次'} · {date(item.started_at)}</option>)}</select>{nextOffset != null && <button type="button" className="bcm-older" disabled={loadingOlder || Boolean(working)} onClick={older}>{loadingOlder ? '載入中…' : '載入更早場次'}</button>}</label></header>
        {turns.length > 0 && <div className="bcm-transcript"><div className="bcm-transcript-heading"><span>已完成的交流</span><b>{number(turns.length)}</b></div>{turns.map((turn, index) => {
          const who = professor(turn.professor_id), feedback = turn.feedback || {};
          return <article className="bcm-turn" key={value(turn.answered_at) + '-' + index} data-testid="research-committee-turn"><div className="bcm-turn-index">{number(index + 1)}</div><div className="bcm-turn-content"><div className="bcm-turn-name">{who.title || '模擬委員'} <span>{who.focus || ''}</span></div><p className="bcm-turn-question">{turn.question}</p><div className="bcm-answer"><span>你的回答</span><p>{turn.answer}</p></div>{feedback.reply && <div className="bcm-feedback"><span>委員回應</span><p>{feedback.reply}</p>{feedback.next_action && <small>{feedback.next_action}</small>}</div>}</div></article>;
        })}</div>}
        {recovered.map((draft, index) => <div className="bcm-recovered" data-testid="research-committee-recovered" key={index}><b>先前問題的未提交草稿仍保留</b><p>之前的問題：{draft.question}</p><textarea aria-label="先前的回答草稿，可選取複製" readOnly value={draft.answer}/><small>請先對照當前問題，再自行複製或修改；不會自動提交。</small></div>)}
        {selected.current && <div className="bcm-current"><div className="bcm-current-meta"><span>NOW SPEAKING / {number(active && active.number || activeId)}</span><b>{active && active.title || '模擬委員'}</b><small>{active && active.focus || '研究交流'}</small></div><div className="bcm-current-main"><span>委員的問題</span><h4 data-testid="research-committee-question">{selected.current.question}</h4>{selected.current.hint && <p className="bcm-hint">思考方向：{selected.current.hint}</p>}
          {selected.current.source && selected.current.source.text && <details className="bcm-source"><summary>查看提問參考段落</summary><small>{selected.current.source.label || '論文段落'}</small><p>{selected.current.source.text}</p></details>}
          <form onSubmit={submit}><label htmlFor="bcm-answer">你的回答 <small>不用完美，就像在向朋友解釋。</small></label><textarea id="bcm-answer" data-testid="research-committee-answer" value={answer} maxLength={6000} disabled={!canWrite || Boolean(working) || selectedSourceChanged} onChange={event => {setAnswer(event.target.value); if (key) keepAnswer(key, selected.revision, selected.current.question, event.target.value);}} placeholder="用你自己的話，從最簡單的地方開始…"/><div className="bcm-form-foot"><span>草稿保存在此瀏覽器</span><button type="submit" data-testid="research-committee-submit" disabled={!canWrite || !answer.trim() || Boolean(working) || selectedSourceChanged}>{working === 'answer' ? '委員正在回應…' : '提交回答 ↗'}</button></div></form>
        </div></div>}
        {!selected.current && <div className="bcm-finished"><span>SESSION COMPLETE / 21</span><h4>這一場交流完成了。</h4><p>你可以回看每一題與委員回應，也可以開啟新一場繼續練習。</p></div>}
      </section>}
    </>}
  </div>;
};
})();
