/* Bonfire research cockpit: registered evidence and versioned researcher assessments. */
(() => {
const W2=window.W2;
const {useState,useEffect,useRef}=React;
const text=value=>value==null?"":String(value);
const stamp=value=>value?text(value).replace("T"," ").slice(0,16):"—";
const dimensions=[['paper','論文','MANUSCRIPT'],['data','資料','DATA'],['theory','理論','THEORY'],['model','模型','MODEL']];
const statusNames={unassessed:'待評估',missing:'有缺口',in_progress:'處理中',ready:'已檢查',planned:'已規劃',blocked:'待解決',completed:'已記錄完成'};
const paperStages=[['','尚未標記'],['planning','界定問題'],['outline','章節規劃'],['drafting','寫作中'],['analysis','分析與論證'],['revision','修訂中'],['submission','投稿準備'],['published','已發表']];
const draftKey=project=>{
  const user=window.W2_USER||{};
  return 'w2_research_cockpit:v1:'+ [W2.tenant()||'default',user.id||user.user_id||user.username||'anonymous',project.id].map(value=>encodeURIComponent(text(value))).join(':');
};
const readLocal=key=>{try{return JSON.parse(localStorage.getItem(key)||'null');}catch(_error){return null;}};
const assessmentFrom=dashboard=>Object.fromEntries((dashboard.dimensions||[]).map(dimension=>[dimension.key,{
  ...(dimension.key==='paper'?{stage:dimension.stage||null}:{}),
  items:Object.fromEntries((dimension.items||[]).map(item=>[item.key,{status:item.status||'unassessed',note:item.note||'',file_version_ids:[...(item.file_version_ids||[])]}]))
}]));
const factSummary=(dimension,files)=>{
  const facts=dimension.facts||{};
  if(dimension.key==='paper'){
    const main=(files||[]).find(file=>/\.docx$/i.test(text(file.logical_path)) && file.asset_class==='manuscript') || (files||[]).find(file=>/\.docx$/i.test(text(file.logical_path)));
    return main?'主稿 V'+main.version+' 已登記'+(facts.source_changed_drafts?' · 草稿來源有更新':''):'尚未登記主稿';
  }
  if(dimension.key==='data')return facts.data_files||facts.database_files?'已登記 '+(facts.data_files||0)+' 份資料 · '+(facts.database_files||0)+' 個資料庫':'尚未登記資料或資料庫';
  if(dimension.key==='theory')return facts.claims?'已登記 '+facts.claims+' 項主張 · '+(facts.evidence_links||0)+' 個證據連結':'尚未登記主張與證據連結';
  return facts.successful_executions||facts.completed_runs?'已登記 '+(facts.successful_executions||0)+' 次成功運算 · '+(facts.completed_runs||0)+' 個完成 Run':'尚未登記模型執行結果';
};
const Artifact=({artifact,onOpen})=><button type="button" className="rcp-artifact" data-testid="research-cockpit-artifact" data-file-version-id={artifact.file_version_id}
  onClick={()=>onOpen(artifact)}><b>V{artifact.version||'—'}</b><span>{artifact.logical_path||artifact.display_name||'固定版本研究物件'}</span><i>↗</i></button>;
const evidenceLabels={insufficient:'證據不足',partial:'部分支持',supported:'已有引證支持'};
const defenseLabels={unassessed:'尚未答辯',unclear:'理解仍不清楚',developing:'理解待補充',clear:'解釋清楚'};
const reviewDimension=(review,dimension)=>((review && review.result||{}).dimensions||[]).find(item=>item.key===dimension);
const reviewFor=(reviews,dimension)=>reviews.filter(review=>review.dimension===dimension||(review.dimensions||[]).includes(dimension))
  .sort((a,b)=>text(b.updated_at||b.created_at).localeCompare(text(a.updated_at||a.created_at))||Number(b.revision)-Number(a.revision))[0]||null;

const AIReviewPanel=({project,dimension,serverVersion,review,files,checks,RichText,canWrite,manualDirty,onResult,onReload,onBusy,onOpenFile,onNavigate})=>{
  const [answers,setAnswers]=useState(()=>Object.fromEntries(dimensions.map(([name])=>{
    const local=readLocal(draftKey(project)+':ai:'+name);
    return [name,local && typeof local.answer==='string'?{answer:local.answer.slice(0,16000),file_version_ids:Array.isArray(local.file_version_ids)?local.file_version_ids:[],review_id:local.review_id||''}:{answer:'',file_version_ids:[],review_id:''}];
  })));
  const [working,setWorking]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const lock=useRef(false),alive=useRef(true),controller=useRef(null),localVersion=useRef(serverVersion);
  localVersion.current=Math.max(localVersion.current,serverVersion);
  const base='/api/research/projects/'+encodeURIComponent(project.id)+'/assessment/ai-reviews';
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;if(controller.current)controller.current.abort();onBusy(false);};},[]);
  useEffect(()=>{setError('');setNotice('');},[dimension]);
  const answer=answers[dimension]||{answer:'',file_version_ids:[],review_id:''};
  const updateAnswer=(name,patch)=>{
    setAnswers(current=>{
      const next={...(current[name]||{answer:'',file_version_ids:[]}),...patch};
      try{localStorage.setItem(draftKey(project)+':ai:'+name,JSON.stringify(next));}catch(_error){}
      return {...current,[name]:next};
    });
  };
  const run=async(kind,refreshContext=false)=>{
    if(!canWrite || lock.current || (kind==='reply' && (!review || !answer.answer.trim())))return;
    lock.current=true;const selected=dimension,sourceReview=review,submitted={...answer,file_version_ids:[...(answer.file_version_ids||[])]};
    const expected=localVersion.current,requestController=new AbortController();controller.current=requestController;
    setWorking({kind,dimension:selected});setError('');setNotice('');onBusy(true);
    try{
      const payload=kind==='initial'?{dimension:selected,expected_dmp_version:expected}:{expected_dmp_version:expected,expected_revision:sourceReview.revision,
        answer:submitted.answer.trim(),file_version_ids:submitted.file_version_ids,...(refreshContext?{refresh_context:true}:{})};
      const result=await W2.json(kind==='initial'?base:base+'/'+encodeURIComponent(sourceReview.id)+'/reply',{
        method:'POST',headers:{'Content-Type':'application/json'},signal:requestController.signal,body:JSON.stringify(payload),
      });
      if(!alive.current || requestController.signal.aborted)return;
      if(!result.review || !result.review.result)throw new Error('AI 尚未回傳可用的評估，請稍後重試。');
      localVersion.current=Math.max(localVersion.current,Number(result.dmp_version)||0);
      await onResult(result,expected);
      if(!alive.current)return;
      if(kind==='reply'){
        updateAnswer(selected,{answer:'',file_version_ids:[],review_id:result.review.id});
        setNotice('答辯與重評已保存；請對照本輪依據與上一輪判斷。');
      }else setNotice('AI 初評已保存，請確認依據並回答追問。');
    }catch(reason){
      if(!alive.current || reason.name==='AbortError')return;
      setError((reason.status===409?'研究材料或評估版本已更新；答辯草稿仍保留。':'')+text(reason.message||reason));
      if(reason.status===409){try{const latest=await onReload();if(alive.current && latest)localVersion.current=Math.max(localVersion.current,Number(latest.research_dashboard && latest.research_dashboard.dmp_version)||0);}catch(_error){}}
    }finally{lock.current=false;if(alive.current){setWorking(null);onBusy(false);}}
  };
  const result=reviewDimension(review,dimension),history=review && Array.isArray(review.history)?[...review.history].sort((a,b)=>Number(a.revision)-Number(b.revision)):[];
  const previous=history.length>1?((history[history.length-2].result||{}).dimensions||[]).find(item=>item.key===dimension):null;
  const questions=((review && review.result||{}).questions||[]).filter(item=>!item.dimension||item.dimension===dimension).slice(0,3);
  const pinned=review && review.pinned_files||[];
  const busy=Boolean(working),sameDimension=working && working.dimension===dimension;
  const title=(dimensions.find(item=>item[0]===dimension)||[])[1]||dimension;
  const Body=({body,className='rcp-ai-richtext',testId})=>RichText?<RichText body={body} className={className} testId={testId||'research-cockpit-ai-richtext'}/>:<p className={className}>{text(body)}</p>;
  const citation=(item,index)=>{
    const file=pinned.find(entry=>entry.file_version_id===item.file_version_id);
    const record=item.record_type;
    return <div className="rcp-ai-citation" data-testid="research-cockpit-ai-citation" key={index}>
      <span>{item.source_kind==='saved_draft'?'精修草稿 REV '+item.draft_revision:record?item.label||record+' '+text(item.record_id).slice(0,8):file?'V'+file.version+' · '+file.logical_path:'固定版本 · '+text(item.file_version_id).slice(0,8)}</span>
      {item.quote && <Body body={item.quote}/>}
      {item.source_kind!=='saved_draft' && file && <button type="button" onClick={()=>onOpenFile(file)}>核對來源 ↗</button>}
      {record && <button type="button" onClick={()=>onNavigate({section:record==='execution'?'execution':record==='protocol'||record==='run'?'workflow':'evidence',...(record==='execution'?{execution_id:item.record_id}:{})})}>查看研究紀錄 ↗</button>}
    </div>;
  };
  return <section className="rcp-ai" data-testid="research-cockpit-ai-panel" aria-label={title+' AI 初評與答辯'} aria-busy={busy}>
    <header><div><span>BONFIRE AI / {text(dimension).toUpperCase()}</span><h3>{title} · AI 初評與答辯</h3><small>AI 判斷獨立保存，人工檢查由研究者確認。</small></div>
      <button type="button" className="primary" data-testid="research-cockpit-ai-start" disabled={!canWrite||busy} onClick={()=>run('initial')}>{review?'重新進行 AI 初評':'Bonfire AI 初評'} ↗</button></header>
    {manualDirty && <p className="rcp-ai-context-note">AI 讀取已保存的研究紀錄；目前人工檢查仍有未保存的編輯。</p>}
    {working && <div className="rcp-ai-loading" data-testid="research-cockpit-ai-loading" role="status"><i/><div><b>{sameDimension?(working.kind==='reply'?'正在核對答辯與證據，重新評估…':'正在閱讀固定版本材料，整理判斷與追問…'):'另一個研究面向正在進行 AI 評估…'}</b><span>讀取材料 → 核對依據 → 提出可回答的問題</span></div></div>}
    {error && <div className="rcp-ai-error" data-testid="research-cockpit-ai-error" role="alert"><p>{error}</p><button type="button" data-testid="research-cockpit-ai-refresh" disabled={busy} onClick={async()=>{try{await onReload();setError('');}catch(reason){setError(text(reason.message||reason));}}}>重新讀取材料與紀錄 ↻</button></div>}
    {review && result?<>
      <div className="rcp-ai-source"><b>AI 初評 · 待確認</b><span>評估 R{review.revision} · 來源 DMP V{review.source_dmp_version} · {stamp(review.updated_at||review.created_at)}</span>
        <details><summary>本輪固定材料 · {pinned.length} 份</summary>{pinned.map(file=><Artifact key={file.file_version_id} artifact={file} onOpen={onOpenFile}/>)}
          <small>來源指紋 {text(review.source_fingerprint).slice(0,12)}</small></details></div>
      {review.stale && <p className="rcp-ai-stale" data-testid="research-cockpit-ai-stale">材料或研究紀錄已有更新。以下為舊版本初評；可保留答辯，讀取最新材料後重新評估。</p>}
      <div className="rcp-ai-grid"><section className="rcp-ai-verdict" data-testid="research-cockpit-ai-verdict">
        <div className="rcp-ai-levels"><div data-testid="research-cockpit-ai-evidence-verdict"><span>研究證據</span><strong className={result.evidence_verdict}>{evidenceLabels[result.evidence_verdict]||'待判斷'}</strong>
          {previous && <small>上一輪：{evidenceLabels[previous.evidence_verdict]||'待判斷'}</small>}</div>
          <div data-testid="research-cockpit-ai-defense-verdict"><span>答辯理解</span><strong>{defenseLabels[result.defense_verdict]||'尚未答辯'}</strong>{previous && <small>上一輪：{defenseLabels[previous.defense_verdict]||'尚未答辯'}</small>}</div></div>
        <Body body={result.summary||review.result.summary} testId="research-cockpit-ai-summary"/>
        {!!(result.gaps||[]).length && <div className="rcp-ai-gaps"><span>這一輪仍要補齊</span><ul>{(result.gaps||[]).slice(0,2).map((gap,index)=><li key={index}><Body body={gap}/></li>)}</ul>
          {result.gaps.length>2 && <details><summary>另外 {result.gaps.length-2} 項待補充</summary><ul>{result.gaps.slice(2).map((gap,index)=><li key={index}><Body body={gap}/></li>)}</ul></details>}</div>}
        <details className="rcp-ai-basis"><summary>逐項判斷與來源依據 · {(result.criteria||[]).length} 項</summary>{(result.criteria||[]).map(item=><article key={item.key}><header><b>{((checks||[]).find(check=>check.key===item.key)||{}).label||item.key}</b><span>{evidenceLabels[item.evidence_verdict]||'待判斷'} · {item.basis_source==='defense_argument'?'答辯論證':item.basis_source==='project_evidence'?'研究材料':'依據不足'}</span></header>
          <Body body={item.basis}/>{(item.gaps||[]).map((gap,index)=><Body key={index} body={gap}/>)}{(item.citations||[]).map(citation)}</article>)}{(result.citations||[]).map(citation)}</details>
        <p className="rcp-ai-separation">答辯理解反映解釋是否清楚；研究證據以可核對的文件、推導與結果為依據。</p>
      </section><section className="rcp-ai-defense">
        <header><span>DEFEND / 回應追問</span><b>{questions.length} 個問題</b></header>
        <ol className="rcp-ai-questions">{questions.slice(0,2).map((question,index)=><li key={question.id||index} data-testid="research-cockpit-ai-question"><b>{String(index+1).padStart(2,'0')}</b><Body body={question.question}/></li>)}</ol>
        {questions.length>2 && <details className="rcp-ai-more-question"><summary>再看一個追問</summary><div data-testid="research-cockpit-ai-question"><Body body={questions[2].question}/></div></details>}
        {answer.review_id && answer.review_id!==review.id && answer.answer && <p className="rcp-ai-context-note">已保留上一輪答辯草稿，請依目前追問調整後提交。</p>}
        <label className="rcp-ai-answer-label"><span>您的答辯 · 可依序回應上方問題</span><textarea data-testid="research-cockpit-ai-answer" value={answer.answer} maxLength={16000} disabled={!canWrite||busy} placeholder="可依序回應上方問題，解釋推導、假設與邊界；有實證或模型結果時，附上下面的固定版本證據。"
          onChange={event=>updateAnswer(dimension,{answer:event.target.value,review_id:review.id})}/></label>
        <details className="rcp-ai-attachments"><summary>附上目前課題的固定版本證據 · {(answer.file_version_ids||[]).length} 份</summary>
          <div className="rcp-file-checks">{files.map(file=><label key={file.file_version_id}><input type="checkbox" data-testid="research-cockpit-ai-evidence" data-file-version-id={file.file_version_id} disabled={!canWrite||busy} checked={(answer.file_version_ids||[]).includes(file.file_version_id)} onChange={event=>updateAnswer(dimension,{file_version_ids:event.target.checked?[...(answer.file_version_ids||[]),file.file_version_id]:(answer.file_version_ids||[]).filter(id=>id!==file.file_version_id),review_id:review.id})}/><span>V{file.version} · {file.logical_path}</span></label>)}</div>
          {(answer.file_version_ids||[]).filter(id=>!files.some(file=>file.file_version_id===id)).map(id=><label className="rcp-ai-retained-evidence" key={id}><input type="checkbox" checked disabled={!canWrite||busy} onChange={()=>updateAnswer(dimension,{file_version_ids:(answer.file_version_ids||[]).filter(item=>item!==id)})}/><span>保留的舊固定版本 · {id.slice(0,12)}</span></label>)}
        </details>
        <footer><small>答辯草稿保留在這部裝置；提交後進入本課題的評估紀錄。</small>
          <button type="button" className="primary" data-testid="research-cockpit-ai-submit" disabled={!canWrite||busy||!answer.answer.trim()||Boolean(review.stale)} onClick={()=>run('reply')}>提交答辯並重評 ↗</button>
          {review.stale && <button type="button" data-testid="research-cockpit-ai-refresh-reply" disabled={!canWrite||busy||!answer.answer.trim()} onClick={()=>run('reply',true)}>讀取最新材料並重新評估 ↗</button>}</footer>
      </section></div>
      <details className="rcp-ai-history" data-testid="research-cockpit-ai-history"><summary>初評與答辯歷史 · {history.length} 輪</summary>{[...history].reverse().map(entry=>{
        const value=((entry.result||{}).dimensions||[]).find(item=>item.key===dimension);
        return <article key={entry.revision}><header><b>R{entry.revision} · {entry.kind==='reply'?'答辯重評':'AI 初評'}</b><time>{stamp(entry.created_at)}</time></header>
          {value && <p className="rcp-ai-history-level">研究證據：{evidenceLabels[value.evidence_verdict]||'待判斷'} · 答辯理解：{defenseLabels[value.defense_verdict]||'尚未答辯'}</p>}
          {entry.context_refreshed && <small>本輪已讀取最新材料</small>}{entry.answer && <details><summary>查看這次答辯</summary><Body body={entry.answer}/></details>}{value && <Body body={value.summary}/>}</article>;
      })}</details>
    </>:!busy && <p className="rcp-ai-empty">請 Bonfire AI 根據這個課題已保存的材料初評，提出具體追問，再用答辯與證據接續研究。</p>}
    {notice && <p className="rcp-ai-notice" role="status">{notice}</p>}
  </section>;
};

W2.ResearchCockpit=function ResearchCockpit({project,projects,workflow,busy,canWrite,onProject,onNavigate,onOpenFile,onSave,onReload,onAdvanced,RichText}){
  const dashboard=workflow && project && text((workflow.project||{}).id)===text(project.id)?workflow.research_dashboard:null;
  const [activeDimension,setActiveDimension]=useState('paper');
  const [activeStage,setActiveStage]=useState('');
  const [draft,setDraft]=useState({});
  const [baseVersion,setBaseVersion]=useState(0);
  const [dirty,setDirty]=useState(false);
  const [saving,setSaving]=useState(false);
  const [conflict,setConflict]=useState(false);
  const [message,setMessage]=useState('');
  const [aiLocal,setAILocal]=useState({}),[aiWorking,setAIWorking]=useState(false);
  const baseVersionRef=useRef(baseVersion);baseVersionRef.current=baseVersion;
  const initialized=useRef(false),dirtyRef=useRef(false),alive=useRef(true),savingRef=useRef(false),tabs=useRef({});
  const key=project?draftKey(project):'';
  const serverVersion=Number(dashboard && dashboard.dmp_version)||0;
  const aiRecords=new Map((Array.isArray(dashboard && dashboard.ai_reviews)?dashboard.ai_reviews:[]).map(review=>[review.id,review]));
  Object.values(aiLocal).forEach(review=>{const saved=aiRecords.get(review.id);if(!saved || Number(saved.revision)<Number(review.revision))aiRecords.set(review.id,review);});
  const aiFingerprint=text(dashboard && dashboard.ai_current_fingerprint);
  const aiReviews=Array.from(aiRecords.values()).map(review=>({...review,stale:Boolean(review.stale || (aiFingerprint && review.source_fingerprint!==aiFingerprint))}));
  useEffect(()=>()=>{alive.current=false;},[]);
  useEffect(()=>{
    if(!dashboard)return;
    if(!initialized.current){
      const local=readLocal(key);
      if(local && local.assessment && Number.isInteger(local.expected_dmp_version)){
        setDraft(local.assessment);setBaseVersion(local.expected_dmp_version);setDirty(true);dirtyRef.current=true;
        setConflict(local.expected_dmp_version!==serverVersion);
      }else{setDraft(assessmentFrom(dashboard));setBaseVersion(serverVersion);}
      initialized.current=true;
    }else if(!dirtyRef.current){setDraft(assessmentFrom(dashboard));setBaseVersion(serverVersion);setConflict(false);}
    else if(baseVersion!==serverVersion)setConflict(true);
  },[dashboard,serverVersion,key]);
  useEffect(()=>{
    if(!key || !dirty || !canWrite)return;
    try{localStorage.setItem(key,JSON.stringify({expected_dmp_version:baseVersion,assessment:draft}));}catch(_error){}
  },[key,draft,baseVersion,dirty,canWrite]);
  const changeItem=(dimension,item,patch)=>{
    dirtyRef.current=true;setDirty(true);setMessage('');
    setDraft(current=>({...current,[dimension]:{...(current[dimension]||{}),items:{...((current[dimension]||{}).items||{}),[item]:{...(((current[dimension]||{}).items||{})[item]||{}),...patch}}}}));
  };
  const save=async()=>{
    if(!project || !dashboard || !canWrite || savingRef.current || aiWorking || conflict || !dirty)return;
    savingRef.current=true;setSaving(true);setMessage('');
    try{
      const result=await onSave({expected_dmp_version:baseVersion,assessment:draft});
      if(!alive.current)return;
      setBaseVersion(Number(result.dmp && result.dmp.version)||serverVersion);dirtyRef.current=false;setDirty(false);setConflict(false);
      try{localStorage.removeItem(key);}catch(_error){}
      setMessage('評估已保存為 DMP 新版本。');
    }catch(reason){if(alive.current){if(reason.status===409)setConflict(true);setMessage(text(reason.message||reason));}}
    finally{savingRef.current=false;if(alive.current)setSaving(false);}
  };
  const reload=async()=>{
    if(savingRef.current)return;
    try{
      const result=await onReload();
      if(!alive.current || !result || !result.research_dashboard)return;
      const latest=result.research_dashboard;
      setDraft(assessmentFrom(latest));setBaseVersion(Number(latest.dmp_version)||0);
      dirtyRef.current=false;setDirty(false);setConflict(false);setMessage('已載入最新評估。');
      try{localStorage.removeItem(key);}catch(_error){}
    }catch(reason){if(alive.current)setMessage(text(reason.message||reason));}
  };
  const acceptAIResult=async(result,expectedVersion)=>{
    if(!alive.current)return;
    setAILocal(current=>({...current,[result.review.id]:result.review}));
    const version=Number(result.dmp_version)||0;
    if(baseVersionRef.current===expectedVersion && version){setBaseVersion(version);baseVersionRef.current=version;setConflict(false);}
    try{await onReload();}catch(reason){if(alive.current)setMessage('AI 評估已保存；面板重新讀取失敗：'+text(reason.message||reason));}
  };
  const graph=dashboard && dashboard.stage_graph || {},nodes=graph.nodes||[];
  const selectedStage=nodes.find(node=>node.key===activeStage)||nodes.find(node=>node.key===graph.current_stage)||nodes[0];
  const selectedDimension=(dashboard && dashboard.dimensions||[]).find(item=>item.key===activeDimension);
  const chooseDimension=dimension=>{
    setActiveDimension(dimension);
    const first=nodes.find(node=>node.dimension===dimension);
    if(first)setActiveStage(first.key);
  };
  const keyboardTab=(event,index)=>{
    const next=event.key==='ArrowRight'?(index+1)%4:event.key==='ArrowLeft'?(index+3)%4:event.key==='Home'?0:event.key==='End'?3:null;
    if(next==null)return;
    event.preventDefault();const dimension=dimensions[next][0];chooseDimension(dimension);if(tabs.current[dimension])tabs.current[dimension].focus();
  };
  const files=dashboard && dashboard.files||[];
  const runStatus={queued:'排隊中',preparing:'準備中',running:'執行中',succeeded:'成功',failed:'失敗',cancelled:'已取消',timed_out:'逾時'};
  const act=action=>{if(action)onNavigate(action);};
  return <div className="rcp" data-testid="research-cockpit">
    <header className="rcp-head"><div><span>PROJECT / RESEARCH CONTROL</span><h2>研究面板</h2></div>
      <label><span>目前課題</span><select data-testid="research-cockpit-project" value={text(project && project.id)} onChange={event=>onProject(event.target.value)}>
        {!projects.length && <option value="">尚無研究課題</option>}{projects.map(item=><option key={item.id} value={text(item.id)}>{item.title}</option>)}</select></label>
      <div className="rcp-version"><b>{project?text(project.slug||project.title).match(/MK\d+/i)?.[0]||'PROJECT':'—'}</b><span>{dashboard?'DMP V'+serverVersion:busy?'讀取中':'未選課題'}</span></div>
    </header>
    <nav className="rcp-tools" aria-label="研究工作區"><button type="button" disabled={!project} onClick={()=>act({section:'projects',asset_class:'dataset'})}>資料與資料庫 ↗</button>
      <button type="button" disabled={!project} onClick={()=>act({section:'refinement'})}>論文精修 ↗</button><button type="button" disabled={!project} onClick={()=>act({section:'execution'})}>模型執行與結果 ↗</button>
      <button type="button" disabled={!project} onClick={()=>act({section:'disciplines'})}>專業研究流程 ↗</button><button type="button" disabled={!project || busy} onClick={async()=>{try{await onReload();}catch(reason){setMessage(text(reason.message||reason));}}}>重新整理 ↻</button></nav>
    {!project?<p className="rcp-empty">選擇或建立課題，將論文、資料、推導與模型放回同一個研究脈絡。</p>:!dashboard?<p className="rcp-empty" role="status">{message || (busy?'正在讀取課題的登記資料與評估…':'研究面板尚未載入，請重新整理。')}</p>:<>
      <div className="rcp-dimensions" role="tablist" aria-label="四個研究面向">{dimensions.map(([dimension,title,en],index)=>{
        const item=(dashboard.dimensions||[]).find(entry=>entry.key===dimension)||{key:dimension,completed:null,total:0};
        const aiReview=reviewFor(aiReviews,dimension),aiResult=reviewDimension(aiReview,dimension);
        return <button key={dimension} ref={node=>{tabs.current[dimension]=node;}} type="button" role="tab" aria-selected={activeDimension===dimension}
          aria-controls={'rcp-assessment-'+project.id} tabIndex={activeDimension===dimension?0:-1} className={'rcp-dimension '+dimension+(activeDimension===dimension?' selected':'')}
          data-testid={'research-cockpit-dimension-'+dimension} onKeyDown={event=>keyboardTab(event,index)} onClick={()=>chooseDimension(dimension)}>
          <header><span>{String(index+1).padStart(2,'0')} / {en}</span><b>↗</b></header><h3>{title}</h3>
          <strong className={item.completed==null?'unknown'+(aiReview?' ai-reviewed':''):''}>{item.completed==null?(aiReview?(aiReview.stale?'需要重評':'AI 已初評'):'待評估'):item.completed+' / '+item.total}</strong>
          <small>{item.completed==null?(aiReview?'人工檢查仍待研究者確認':'尚未完成研究者檢查'):'已完成的人工檢查項目'}</small>
          {aiReview && <span className={'rcp-ai-card-flag'+(aiReview.stale?' stale':'')} data-testid="research-cockpit-ai-card-status" data-dimension={dimension}>{aiReview.stale?'AI 初評已過期':(evidenceLabels[aiResult && aiResult.evidence_verdict]||'AI 初評')+' · 待確認'}</span>}
          <footer>{factSummary(item,files)}</footer>
        </button>;
      })}</div>
      <div className="rcp-evidence-key"><span><i/>實際登記：文件、資料與執行紀錄</span><span><i/>研究者評估：檢查項目與缺口</span><small>檢查數量表示紀錄覆蓋，研究結論仍需證據與覆核。</small></div>
      <section className="rcp-route" aria-label="完整研究路線"><header><div><span>01 / RESEARCH ROUTE</span><h3>從問題走到論證</h3></div><small>{graph.current_stage?'目前紀錄：'+text((nodes.find(node=>node.key===graph.current_stage)||{}).title):'目前階段尚未標記'}</small></header>
        <ol>{nodes.map((node,index)=><li key={node.key}><button type="button" className={text(node.status)+(selectedStage && selectedStage.key===node.key?' active':'')}
          data-testid={'research-cockpit-stage-'+node.key} aria-pressed={Boolean(selectedStage && selectedStage.key===node.key)} onClick={()=>{setActiveStage(node.key);if(dimensions.some(item=>item[0]===node.dimension))setActiveDimension(node.dimension);}}>
          <span>{String(index+1).padStart(2,'0')}<i>{statusNames[node.status]||'待標記'}</i></span><strong>{node.title}</strong><small>{(node.evidence||[]).length?(node.evidence||[]).length+' 份固定版本證據':'尚未連結證據'}</small></button></li>)}</ol>
        {!nodes.length && <p className="rcp-empty">尚未建立專業研究路線。可在專業與流程中選擇這個課題的方法。</p>}
      </section>
      <AIReviewPanel project={project} dimension={activeDimension} serverVersion={serverVersion} review={reviewFor(aiReviews,activeDimension)} files={files}
        checks={selectedDimension && selectedDimension.items||[]} RichText={RichText} canWrite={canWrite&&!saving} manualDirty={dirty} onResult={acceptAIResult}
        onReload={onReload} onBusy={setAIWorking} onOpenFile={onOpenFile} onNavigate={onNavigate}/>
      <div className="rcp-workgrid"><section className="rcp-stage" data-testid="research-cockpit-stage-detail">
        <header><span>02 / STAGE DETAIL</span><b>{selectedStage?statusNames[selectedStage.status]||'待標記':'待建立'}</b></header>
        <h3>{selectedStage?selectedStage.title:'選擇一個研究步驟'}</h3>
        {selectedStage && <><dl>{[['plan','本步計畫'],['findings','研究發現'],['blockers','尚待解決'],['next_action','下一個動作']].map(([name,label])=>{
          const value=text((selectedStage.task||{})[name]);return value?<div key={name}><dt>{label}</dt><dd>{value}</dd></div>:null;
        })}</dl>{!['plan','findings','blockers','next_action'].some(name=>text((selectedStage.task||{})[name]).trim()) && <p className="rcp-empty">這一步尚未記錄計畫、發現與下一個動作。</p>}
          <div className="rcp-stage-evidence"><span>固定版本證據</span>{(selectedStage.evidence||[]).map((artifact,index)=><Artifact key={artifact.file_version_id||index} artifact={artifact} onOpen={onOpenFile}/>)}
            {!(selectedStage.evidence||[]).length && <p>尚未連結本步證據；已有論文不會自動完成這個步驟。</p>}</div>
          <footer><small>研究紀錄 V{selectedStage.revision||0} · {(selectedStage.task||{}).assignee==='codex'?'Codex':(selectedStage.task||{}).assignee==='user'?'研究者':'共同協作'}</small>
            <button type="button" onClick={()=>act({section:'disciplines',stage_key:selectedStage.key})}>{canWrite?'編輯本步紀錄':'查看本步紀錄'} ↗</button>
            <button type="button" onClick={()=>act(selectedStage.action||{section:'disciplines'})}>對應工作區 ↗</button></footer></>}
        {!!(dashboard.blockers||[]).length && <div className="rcp-gaps"><span>目前要補齊</span>{(dashboard.blockers||[]).filter(item=>!selectedStage || !item.dimension || item.dimension===selectedStage.dimension).slice(0,5).map((item,index)=><button key={item.key||index} type="button" onClick={()=>{if(item.dimension)chooseDimension(item.dimension);if(item.action)act(item.action);}}>{item.label}<b>→</b></button>)}</div>}
      </section>
      <section className="rcp-assessment" id={'rcp-assessment-'+project.id} role="tabpanel" aria-label={(selectedDimension||{}).title||'研究者評估'}>
        <header><div><span>03 / RESEARCHER CHECK</span><h3>{(selectedDimension||{}).title||'研究者評估'}檢查</h3></div><b>{canWrite?(dirty?'有未保存編輯':'DMP V'+baseVersion):'唯讀'}</b></header>
        {activeDimension==='paper' && <label className="rcp-paper-stage"><span>論文目前階段</span><select data-testid="research-cockpit-paper-stage" disabled={!canWrite||saving} value={(draft.paper||{}).stage||''} onChange={event=>{
          dirtyRef.current=true;setDirty(true);setDraft(current=>({...current,paper:{...(current.paper||{}),stage:event.target.value||null}}));
        }}>{paperStages.map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>}
        <div className="rcp-checklist">{(selectedDimension && selectedDimension.items||[]).map(item=>{
          const value=(((draft[activeDimension]||{}).items||{})[item.key])||item;
          return <article key={item.key} className={value.status||'unassessed'}><div><label htmlFor={'rcp-check-'+activeDimension+'-'+item.key}>{item.label}</label>
            <select id={'rcp-check-'+activeDimension+'-'+item.key} data-testid={'research-cockpit-check-'+activeDimension+'-'+item.key} value={value.status||'unassessed'} disabled={!canWrite||saving}
              onChange={event=>changeItem(activeDimension,item.key,{status:event.target.value})}>{['unassessed','missing','in_progress','ready'].map(status=><option key={status} value={status}>{statusNames[status]}</option>)}</select></div>
            <details><summary>備註與證據{(value.file_version_ids||[]).length?' · '+value.file_version_ids.length+' 份':''}{value.note?' · 已有紀錄':''}</summary>
              <textarea aria-label={item.label+'的評估備註'} data-testid={'research-cockpit-note-'+activeDimension+'-'+item.key} disabled={!canWrite||saving} value={value.note||''} maxLength={8000}
                placeholder="這項檢查的判斷、缺口與證據位置" onChange={event=>changeItem(activeDimension,item.key,{note:event.target.value})}/>
              <div className="rcp-file-checks">{files.map(file=><label key={file.file_version_id}><input type="checkbox" disabled={!canWrite||saving} checked={(value.file_version_ids||[]).includes(file.file_version_id)} onChange={event=>changeItem(activeDimension,item.key,{file_version_ids:event.target.checked?[...(value.file_version_ids||[]),file.file_version_id]:(value.file_version_ids||[]).filter(id=>id!==file.file_version_id)})}/><span>V{file.version} · {file.logical_path}</span></label>)}</div>
              {(item.evidence||[]).map((artifact,index)=><Artifact key={artifact.file_version_id||index} artifact={artifact} onOpen={onOpenFile}/>)}</details></article>;
        })}</div>
        {conflict && <div className="rcp-conflict" role="alert">伺服器評估已有新版本；本機編輯仍保留。可先複製備註，再放棄本機評估並載入最新版本。
          <button type="button" data-testid="research-cockpit-reload" disabled={saving} onClick={reload}>放棄本機評估，載入最新</button></div>}
        {message && <p className={'rcp-message'+(conflict?' error':'')} data-testid="research-cockpit-message" role="status">{message}</p>}
        <footer><span>研究者逐項標記 · 版本化保存</span><button type="button" data-testid="research-cockpit-save" disabled={!canWrite||!dirty||saving||aiWorking||conflict} onClick={save}>{saving?'正在保存…':'保存評估'}</button></footer>
      </section></div>
      {dashboard.next_action && <section className="rcp-next"><span>NEXT / 建議接續</span><strong>{dashboard.next_action.label}</strong><button type="button" onClick={()=>{if(dashboard.next_action.dimension)chooseDimension(dashboard.next_action.dimension);if(dashboard.next_action.action)act(dashboard.next_action.action);}}>處理這一步 →</button></section>}
      <div className="rcp-register-grid"><section className="rcp-register"><header><span>04 / REGISTERED MATERIAL</span><h3>文件與資料版本</h3><b>{files.length}</b></header>
        {files.map(file=><div key={file.file_version_id} className="rcp-file-row"><Artifact artifact={file} onOpen={onOpenFile}/><small>{file.asset_class||'其他'} · {file.version_count||1} 個版本{file.source_changed?' · 草稿來源已更新':''}</small></div>)}
        {!files.length && <p className="rcp-empty">尚未登記文件。可從資料工作區上傳論文、資料與代碼。</p>}</section>
        <section className="rcp-register"><header><span>05 / EXECUTION & ACTIVITY</span><h3>結果與最近活動</h3></header>
          {(workflow.executions||[]).slice(0,4).map(run=><button className={'rcp-run '+run.status} type="button" key={run.id} onClick={()=>act({section:'execution',execution_id:run.id})}><b>{runStatus[run.status]||run.status}</b><span>{run.title||run.entrypoint||run.id}</span><small>{stamp(run.finished_at||run.created_at)}</small></button>)}
          {!(workflow.executions||[]).length && <p className="rcp-empty">尚未登記模型執行結果；可先登記資料、代碼及方法，再執行與檢查。</p>}
          <ol className="rcp-activity">{(dashboard.activity||[]).slice(0,6).map((item,index)=><li key={index}><span>{item.label}</span><time>{stamp(item.created_at)}</time></li>)}</ol>
        </section></div>
      <button className="rcp-advanced-link" type="button" onClick={onAdvanced}>進階：資料管理計畫、研究協議與 Run 設定 ↓</button>
    </>}
  </div>;
};
})();
