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
const committeeLabels={meets_standard:'符合本輪標準',needs_work:'仍需補充'};
const reviewDimension=(review,dimension)=>((review && review.result||{}).dimensions||[]).find(item=>item.key===dimension);
const reviewFor=(reviews,dimension)=>reviews.filter(review=>!review.stage_key && !review.criterion_key && (review.dimension===dimension||(review.dimensions||[]).includes(dimension)))
  .sort((a,b)=>text(b.updated_at||b.created_at).localeCompare(text(a.updated_at||a.created_at))||Number(b.revision)-Number(a.revision))[0]||null;
const stageReviewFor=(reviews,discipline,stage)=>reviews.filter(review=>review.stage_key===stage && review.discipline===discipline)
  .sort((a,b)=>text(b.updated_at||b.created_at).localeCompare(text(a.updated_at||a.created_at))||Number(b.revision)-Number(a.revision))[0]||null;
const itemReviewFor=(reviews,dimension,item)=>reviews.filter(review=>!review.stage_key && review.dimension===dimension && review.criterion_key===item)
  .sort((a,b)=>text(b.updated_at||b.created_at).localeCompare(text(a.updated_at||a.created_at))||Number(b.revision)-Number(a.revision))[0]||null;
const canonical=value=>Array.isArray(value)?value.map(canonical):value&&typeof value==='object'?Object.fromEntries(Object.keys(value).sort().map(key=>[key,canonical(value[key])])):value;
const manualUnchanged=(workflow,base,current)=>{
  const rows=workflow && Array.isArray(workflow.dmp_history)?workflow.dmp_history:[];
  const latest=current===0?{}:rows.find(row=>Number(row.version)===current);
  const previous=base===0?{}:rows.find(row=>Number(row.version)===base);
  if(!latest || !previous)return false;
  const content=(row,version)=>version===0?{}:row.content&&typeof row.content==='object'&&!Array.isArray(row.content)?row.content.research_dashboard_assessment||{}:null;
  const before=content(previous,base),after=content(latest,current);
  return before!==null && after!==null && JSON.stringify(canonical(before))===JSON.stringify(canonical(after));
};
const specialistNames={paper:'學術論文評審 Agent',data:'數據治理與統計 Agent',theory:'理論與論證 Agent',model:'模型與方法 Agent'};
const specialistFor=(review,dimension)=>{
  if(!review)return null;
  if(review.specialist)return review.specialist;
  const roles=review.specialists;
  if(Array.isArray(roles)){
    const index=Array.isArray(review.dimensions)?review.dimensions.indexOf(dimension):-1;
    return index>=0?roles[index]||null:null;
  }
  return roles && typeof roles==='object'?roles[dimension]||null:null;
};
const aiErrorMessage=reason=>{
  const message=typeof reason==='string'?reason.trim():reason && typeof reason.message==='string'?reason.message.trim():'';
  if(reason && reason.status===409)return '研究材料或評估版本已更新；答辯草稿仍保留。'+(message && message!=='Error'?message:'');
  if(reason && reason.status>=500 && (!message || /^(error|bad gateway|gateway timeout|service unavailable|internal server error)$/i.test(message)))
    return 'Bonfire AI 暫時無法完成評估，請稍後重試；答辯草稿仍會保留。';
  if(!message || /^(error|failed to fetch|load failed|networkerror.*)$/i.test(message))
    return '暫時無法完成評估，請檢查連線後重試；答辯草稿仍會保留。';
  return message;
};

const AIReviewPanel=({project,dimension,stage,item,discipline,serverVersion,review,otherReviews,files,checks,RichText,canWrite,manualDirty,onResult,onReload,onBusy,onOpenFile,onNavigate})=>{
  const [answers,setAnswers]=useState({});
  const [working,setWorking]=useState(null),[error,setError]=useState(''),[notice,setNotice]=useState('');
  const [failedRequest,setFailedRequest]=useState(null),[retryChecking,setRetryChecking]=useState(false);
  const [acknowledged,setAcknowledged]=useState('');
  const lock=useRef(false),alive=useRef(true),controller=useRef(null),localVersion=useRef(serverVersion);
  localVersion.current=Math.max(localVersion.current,serverVersion);
  const base='/api/research/projects/'+encodeURIComponent(project.id)+'/assessment/ai-reviews';
  useEffect(()=>{alive.current=true;return()=>{alive.current=false;if(controller.current)controller.current.abort();onBusy(false);};},[]);
  const scope=stage?'stage:'+discipline+':'+stage.key:item?'item:'+dimension+':'+item.key:dimension;
  const target=useRef({});target.current={scope,reviewId:review && review.id || '',revision:review && review.revision || 0};
  useEffect(()=>{setError('');setNotice('');setFailedRequest(null);},[scope]);
  const answerKey=(name,id)=>draftKey(project)+':ai:'+name+':review:'+encodeURIComponent(text(id));
  const currentKey=answerKey(scope,review && review.id);
  const storedAnswer=readLocal(currentKey);
  const legacyAnswer=review && !stage && !item?readLocal(draftKey(project)+':ai:'+scope):null;
  const localAnswer=storedAnswer||(legacyAnswer && legacyAnswer.review_id===review.id?legacyAnswer:null);
  const answer=answers[currentKey]||(localAnswer && typeof localAnswer.answer==='string'?{...localAnswer,file_version_ids:Array.isArray(localAnswer.file_version_ids)?localAnswer.file_version_ids:[]}:{answer:'',file_version_ids:[],review_id:''});
  const answerTooLong=answer.answer.length>6000;
  const committee=review && review.result && review.result.committee_feedback;
  const roundKey=review?text(review.id)+':'+text(review.revision):'';
  const readyForAnswer=!committee || acknowledged===roundKey;
  const updateAnswer=(name,patch,id=review && review.id)=>{
    const localKey=answerKey(name,id);
    setAnswers(current=>{
      const saved=readLocal(localKey);
      const old=readLocal(draftKey(project)+':ai:'+name);
      const next={...(current[localKey]||saved||(old && old.review_id===id?old:null)||{answer:'',file_version_ids:[]}),...patch};
      try{localStorage.setItem(localKey,JSON.stringify(next));}catch(_error){}
      return {...current,[localKey]:next};
    });
  };
  const run=async(kind,refreshContext=false)=>{
    if(!canWrite || lock.current || (kind==='reply' && (!review || !readyForAnswer || !answer.answer.trim() || answerTooLong)))return;
    lock.current=true;const selected=scope,sourceReview=review,submitted={...answer,file_version_ids:[...(answer.file_version_ids||[])]};
    const expected=localVersion.current,requestController=new AbortController();controller.current=requestController;
    setWorking({kind,dimension:selected});setError('');setNotice('');setFailedRequest(null);onBusy(true);
    try{
      const payload=kind==='initial'?{dimension,...(stage?{stage_key:stage.key}:item?{criterion_key:item.key}:{}),expected_dmp_version:expected}:{expected_dmp_version:expected,expected_revision:sourceReview.revision,
        answer:submitted.answer.trim(),file_version_ids:submitted.file_version_ids,...(committee?{acknowledged_revision:sourceReview.revision}:{}),...(refreshContext?{refresh_context:true}:{})};
      const result=await W2.json(kind==='initial'?base:base+'/'+encodeURIComponent(sourceReview.id)+'/reply',{
        method:'POST',headers:{'Content-Type':'application/json'},signal:requestController.signal,body:JSON.stringify(payload),
      });
      if(!alive.current || requestController.signal.aborted)return;
      if(!result.review || !result.review.result)throw new Error('AI 尚未回傳可用的評估，請稍後重試。');
      localVersion.current=Math.max(localVersion.current,Number(result.dmp_version)||0);
      await onResult(result,expected);
      if(!alive.current)return;
      if(kind==='reply'){
        updateAnswer(selected,{answer:'',file_version_ids:[],review_id:result.review.id},sourceReview.id);
        setNotice('答辯與委員會回覆已保存，請先查看本輪判斷。');
      }else setNotice('AI 初評已保存，請確認依據並回答追問。');
    }catch(reason){
      if(!alive.current || reason.name==='AbortError' || target.current.scope!==selected)return;
      setError(aiErrorMessage(reason));
      if(!reason.status || reason.status>=500)setFailedRequest({kind,refreshContext,scope:selected,
        reviewId:sourceReview && sourceReview.id || '',revision:sourceReview && sourceReview.revision || 0,expected});
      if(reason.status===409){try{const latest=await onReload();if(alive.current && latest)localVersion.current=Math.max(localVersion.current,Number(latest.research_dashboard && latest.research_dashboard.dmp_version)||0);}catch(_error){}}
    }finally{lock.current=false;if(alive.current){setWorking(null);onBusy(false);}}
  };
  const retryFailed=async()=>{
    if(!failedRequest || retryChecking || lock.current || !canWrite)return;
    lock.current=true;const failed=failedRequest;setRetryChecking(true);onBusy(true);
    try{
      const latest=await onReload();
      if(!alive.current)return;
      const version=latest && latest.research_dashboard && latest.research_dashboard.dmp_version;
      if(!Number.isInteger(version))throw new Error('無法確認最新研究紀錄，請重新讀取後再試。');
      localVersion.current=Math.max(localVersion.current,version);
      if(version!==failed.expected){
        setFailedRequest(null);
        setError('研究紀錄已有更新，請先確認目前評估；答辯草稿仍保留。');
        return;
      }
      const current=target.current;
      if(current.scope!==failed.scope || current.reviewId!==failed.reviewId || current.revision!==failed.revision)return;
      setRetryChecking(false);onBusy(false);
      lock.current=false;
      await run(failed.kind,failed.refreshContext);
    }catch(reason){if(alive.current)setError(aiErrorMessage(reason));}
    finally{lock.current=false;if(alive.current){setRetryChecking(false);onBusy(false);}}
  };
  const result=reviewDimension(review,dimension),history=review && Array.isArray(review.history)?[...review.history].sort((a,b)=>Number(a.revision)-Number(b.revision)):[];
  const previous=history.length>1?((history[history.length-2].result||{}).dimensions||[]).find(item=>item.key===dimension):null;
  const previousRound=history.length>1?history[history.length-2]:null;
  const previousCommittee=previousRound && previousRound.result && previousRound.result.committee_feedback;
  const lastAnswer=history.length?history[history.length-1].answer:'';
  const questions=((review && review.result||{}).questions||[]).filter(item=>!item.dimension||item.dimension===dimension).slice(0,3);
  const pinned=review && review.pinned_files||[];
  const busy=Boolean(working || retryChecking),sameDimension=working && working.dimension===scope;
  const title=stage?stage.title:item?item.label:(dimensions.find(entry=>entry[0]===dimension)||[])[1]||dimension;
  const scopeLabel=stage?'研究流程步驟：'+stage.title:item?'單項檢查：'+item.label:title+'整體';
  const oldScopeQuestions=Boolean(review && Number(review.question_policy_version||0)<2 &&
    ((!stage && !item && dimension==='paper') || (item && dimension==='paper' && item.key==='question') ||
     (stage && stage.key==='question')));
  const specialist=(specialistFor(review,dimension)||{}).name||(review?'Bonfire AI（既有評估）':stage?'本步專業 Agent':specialistNames[dimension]||'研究評估 Agent');
  const Body=({body,className='rcp-ai-richtext',testId,formula=false})=>RichText?<RichText body={body} formula={formula} className={className} testId={testId||'research-cockpit-ai-richtext'}/>:<p className={className}>{text(body)}</p>;
  const citation=(item,index)=>{
    const file=pinned.find(entry=>entry.file_version_id===item.file_version_id);
    const record=item.record_type;
    return <div className="rcp-ai-citation" data-testid="research-cockpit-ai-citation" key={index}>
      <span>{item.source_kind==='saved_draft'?'精修草稿 REV '+item.draft_revision:record?item.label||record+' '+text(item.record_id).slice(0,8):file?'V'+file.version+' · '+file.logical_path:'固定版本 · '+text(item.file_version_id).slice(0,8)}</span>
      {item.quote && !item.source_latex && <Body body={item.quote}/>}
      {item.source_latex && <div className="rcp-question-formula" data-testid="research-cockpit-question-formula"><span>同一來源的原稿公式</span><Body body={item.source_latex} formula/></div>}
      {item.quote && item.source_latex && <details className="rcp-question-original"><summary>查看原文摘錄</summary><pre className="rcp-question-raw-quote">{item.quote}</pre></details>}
      {item.source_kind!=='saved_draft' && file && <button type="button" onClick={()=>onOpenFile(file)}>核對來源 ↗</button>}
      {record && <button type="button" onClick={()=>onNavigate({section:record==='execution'?'execution':record==='protocol'||record==='run'?'workflow':'evidence',...(record==='execution'?{execution_id:item.record_id}:{})})}>查看研究紀錄 ↗</button>}
    </div>;
  };
  const hasQuestionGroups=questions.some(question=>['theory','method','evidence'].includes(question.category));
  const questionGroups=[
    {key:'theory',title:discipline==='econometrics'?'第一組：經濟學理論與機制':'第一組：理論與核心機制'},
    {key:'method',title:discipline==='econometrics'?'第二組：方法與識別':'第二組：研究方法與檢驗'},
    {key:'evidence',title:'第三組：資料與證據'},
    {key:'other',title:'其他追問'},
  ].map(group=>({...group,items:questions.map((question,index)=>({question,index})).filter(({question})=>group.key==='other'?!['theory','method','evidence'].includes(question.category):question.category===group.key)})).filter(group=>group.items.length);
  let questionNumber=0;questionGroups.forEach(group=>group.items.forEach(entry=>{entry.displayIndex=questionNumber++;}));
  const questionRow=(question,index)=><li key={question.id||index} data-testid="research-cockpit-ai-question"><b>{String(index+1).padStart(2,'0')}</b><div><Body body={question.question}/>
    {question.hint && <div className="rcp-question-hint" data-testid="research-cockpit-question-hint"><span>思考方向</span><Body body={question.hint}/></div>}
    {Array.isArray(question.citations) && question.citations.length>0 && <div className="rcp-question-source" data-testid="research-cockpit-question-source"><span>來源段落摘錄</span>{question.citations.slice(0,1).map(citation)}
      {question.citations.length>1 && <details><summary>更多依據 · {question.citations.length-1} 項</summary>{question.citations.slice(1).map(citation)}</details>}</div>}
  </div></li>;
  return <section className="rcp-ai" data-testid="research-cockpit-ai-panel" aria-label={title+' AI 初評與答辯'} aria-busy={busy}>
    <header><div><span>BONFIRE AI / {stage?'STAGE':item?'CHECK':'DIMENSION'} / {text(dimension).toUpperCase()}</span><h3>{title} · 專家評估與答辯</h3><small data-testid="research-cockpit-review-scope">範圍：{scopeLabel} · 與其他範圍的答辯分開保存</small><br/><small>{specialist} · AI 判斷獨立保存，人工檢查由研究者確認。</small></div>
      <button type="button" className="primary" data-testid="research-cockpit-ai-start" disabled={!canWrite||busy} onClick={()=>run('initial')}>{review?'重新進行專家評估':item?'為此項產生答辯問題':'請專家評估'} ↗</button></header>
    {oldScopeQuestions && <p className="rcp-ai-context-note" data-testid="research-cockpit-scope-update">這份問題在範圍區分更新前產生，可能與其他部分相似。可重新進行專家評估；已有答辯與草稿會保留。</p>}
    {review && answer.answer.trim() && <p className="rcp-ai-context-note">重新評估會建立新紀錄；未提交的草稿會保留在「其他評估紀錄」中。</p>}
    {manualDirty && <p className="rcp-ai-context-note">AI 讀取已保存的研究紀錄；目前人工檢查仍有未保存的編輯。</p>}
    {working && <div className="rcp-ai-loading" data-testid="research-cockpit-ai-loading" role="status"><i/><div><b>{sameDimension?(working.kind==='reply'?'正在核對答辯與證據，重新評估…':'正在閱讀固定版本材料，整理判斷與追問…'):'另一個研究面向正在進行 AI 評估…'}</b><span>讀取材料 → 核對依據 → 提出可回答的問題</span></div></div>}
    {error && <div className="rcp-ai-error" data-testid="research-cockpit-ai-error" role="alert"><p>{error}</p>
      {failedRequest && failedRequest.scope===scope && failedRequest.reviewId===(review && review.id || '') && failedRequest.revision===(review && review.revision || 0) && <button type="button" data-testid="research-cockpit-ai-retry" disabled={busy||!canWrite||(failedRequest.kind==='reply'&&(!answer.answer.trim()||answerTooLong||!readyForAnswer))} onClick={retryFailed}>{retryChecking?'正在核對紀錄…':failedRequest.kind==='reply'?'重試提交答辯 ↻':'重試專家評估 ↻'}</button>}
      <button type="button" data-testid="research-cockpit-ai-refresh" disabled={busy} onClick={async()=>{try{await onReload();setError('');setFailedRequest(null);}catch(reason){setError(aiErrorMessage(reason));}}}>重新讀取材料與紀錄 ↻</button></div>}
    {review && result?<>
      <div className="rcp-ai-source"><b>AI 初評 · 待確認</b><span>評估 R{review.revision} · 來源 DMP V{review.source_dmp_version} · {stamp(review.updated_at||review.created_at)}</span>
        <details><summary>本輪固定材料 · {pinned.length} 份</summary>{pinned.map(file=><Artifact key={file.file_version_id} artifact={file} onOpen={onOpenFile}/>)}
          <small>來源指紋 {text(review.source_fingerprint).slice(0,12)}</small></details>
        {review.context_scope && (review.context_scope.truncated || review.context_scope.economic_theory_text_available===false || (review.context_scope.stage_artifacts_not_read||[]).length>0 || (review.context_scope.item_artifacts_not_read||[]).length>0) && <small className="rcp-ai-scope" data-testid="research-cockpit-ai-scope" role="note">
          {review.context_scope.truncated?'本輪僅評估部分材料摘錄。':''}{review.context_scope.economic_theory_text_available===false?' 尚未讀到可供理論提問的正文。':''}{(review.context_scope.stage_artifacts_not_read||[]).length>0?' '+review.context_scope.stage_artifacts_not_read.length+' 份固定階段材料未能讀取。':''}{(review.context_scope.item_artifacts_not_read||[]).length>0?' '+review.context_scope.item_artifacts_not_read.length+' 份本項固定材料未能讀取。':''}
        </small>}</div>
      {review.stale && <p className="rcp-ai-stale" data-testid="research-cockpit-ai-stale">材料或研究紀錄已有更新。以下為舊版本初評；可保留答辯，讀取最新材料後重新評估。</p>}
      {committee && <section className="rcp-committee" data-testid="research-cockpit-committee" aria-label="AI 模擬委員會回覆">
        <header><div><span>COMMITTEE / ROUND {review.revision-1}</span><h4>AI 模擬委員會回覆</h4></div><strong className={committee.decision} data-testid="research-cockpit-committee-decision">{committeeLabels[committee.decision]||'待判斷'}</strong></header>
        <div className="rcp-committee-body"><div><b>本輪標準</b><Body body={committee.standard}/></div>
          <div><b>對您回答的答覆</b><Body body={committee.reply} testId="research-cockpit-committee-reply"/></div>
          <div><b>下一步</b><Body body={committee.next_action}/></div></div>
        {lastAnswer && <details className="rcp-committee-answer"><summary>查看本輪提交的答辯</summary><Body body={lastAnswer}/></details>}
        {previous && <div className="rcp-committee-previous" data-testid="research-cockpit-committee-previous"><span>上一輪 · R{previousRound && previousRound.revision}</span><strong>{previousCommittee?'委員會：'+(committeeLabels[previousCommittee.decision]||'待判斷')+' · ':''}{evidenceLabels[previous.evidence_verdict]||'待判斷'} · {defenseLabels[previous.defense_verdict]||'尚未答辯'}</strong><Body body={previousCommittee && previousCommittee.reply || previous.summary}/></div>}
      </section>}
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
        {review && review.result && (review.result.question_overlap_warning===true || Number(review.result.omitted_repeated_questions)>0) && <p className="rcp-ai-context-note" data-testid="research-cockpit-question-overlap" role="note">{Number(review.result.omitted_repeated_questions)>0?'已略去重複題。':''}{review.result.question_overlap_warning===true?'本輪問題仍可能與其他部分重複，可重新產生。':''}</p>}
        {hasQuestionGroups?<div className="rcp-question-groups" data-testid="research-cockpit-question-groups">{questionGroups.map((group,index)=>group.key==='theory'||index===0?
          <section className="rcp-question-group" key={group.key} data-testid={'research-cockpit-question-group-'+group.key}><h4>{group.title}</h4><ol className="rcp-ai-questions">{group.items.map(({question,displayIndex})=>questionRow(question,displayIndex))}</ol></section>:
          <details className="rcp-question-group rcp-question-group-more" key={group.key} data-testid={'research-cockpit-question-group-'+group.key}><summary>{group.title} · {group.items.length} 題</summary><ol className="rcp-ai-questions">{group.items.map(({question,displayIndex})=>questionRow(question,displayIndex))}</ol></details>)}</div>:
          <><p className="rcp-question-legacy">本輪提問尚未分類；可重新進行專家評估，原答辯紀錄仍會保留。</p><ol className="rcp-ai-questions">{questions.slice(0,2).map(questionRow)}</ol>
          {questions.length>2 && <details className="rcp-ai-more-question"><summary>再看一個追問</summary><ol className="rcp-ai-questions">{questionRow(questions[2],2)}</ol></details>}</>}
        {!readyForAnswer && <div className="rcp-committee-gate"><p>請先查看上方委員會答覆，再開始下一輪。</p><button type="button" data-testid="research-cockpit-committee-continue" disabled={!canWrite||busy} onClick={()=>setAcknowledged(roundKey)}>已閱讀，進入下一輪 ↗</button></div>}
        {readyForAnswer && <>
        {answer.review_id && answer.review_id!==review.id && answer.answer && <p className="rcp-ai-context-note">已保留上一輪答辯草稿，請依目前追問調整後提交。</p>}
        <label className="rcp-ai-answer-label"><span>您的答辯 · 可依序回應上方問題（最多 6000 字）</span><textarea data-testid="research-cockpit-ai-answer" value={answer.answer} maxLength={6000} disabled={!canWrite||busy} placeholder="可依序回應上方問題，解釋推導、假設與邊界；有實證或模型結果時，附上下面的固定版本證據。"
          onChange={event=>updateAnswer(scope,{answer:event.target.value,review_id:review.id})}/></label>
        {answerTooLong && <p className="rcp-ai-context-note" role="alert">已保留完整的舊草稿；請精簡至 6000 字以內再提交。</p>}
        <details className="rcp-ai-attachments"><summary>附上目前課題的固定版本證據 · {(answer.file_version_ids||[]).length} 份</summary>
          <div className="rcp-file-checks">{files.map(file=><label key={file.file_version_id}><input type="checkbox" data-testid="research-cockpit-ai-evidence" data-file-version-id={file.file_version_id} disabled={!canWrite||busy} checked={(answer.file_version_ids||[]).includes(file.file_version_id)} onChange={event=>updateAnswer(scope,{file_version_ids:event.target.checked?[...(answer.file_version_ids||[]),file.file_version_id]:(answer.file_version_ids||[]).filter(id=>id!==file.file_version_id),review_id:review.id})}/><span>V{file.version} · {file.logical_path}</span></label>)}</div>
          {(answer.file_version_ids||[]).filter(id=>!files.some(file=>file.file_version_id===id)).map(id=><label className="rcp-ai-retained-evidence" key={id}><input type="checkbox" checked disabled={!canWrite||busy} onChange={()=>updateAnswer(scope,{file_version_ids:(answer.file_version_ids||[]).filter(item=>item!==id)})}/><span>保留的舊固定版本 · {id.slice(0,12)}</span></label>)}
          <button type="button" className="rcp-committee-upload" data-testid="research-cockpit-committee-upload" disabled={!canWrite||busy} onClick={()=>onNavigate({section:'projects'})}>上傳新材料 ↗</button>
        </details>
        <footer><small>答辯草稿保留在這部裝置；提交後進入本課題的評估紀錄。</small>
          <button type="button" className="primary" data-testid="research-cockpit-ai-submit" disabled={!canWrite||busy||!answer.answer.trim()||answerTooLong||Boolean(review.stale)} onClick={()=>run('reply')}>提交答辯並重評 ↗</button>
          {review.stale && <button type="button" data-testid="research-cockpit-ai-refresh-reply" disabled={!canWrite||busy||!answer.answer.trim()||answerTooLong} onClick={()=>run('reply',true)}>讀取最新材料並重新評估 ↗</button>}</footer>
        </>}
      </section></div>
      <details className="rcp-ai-history" data-testid="research-cockpit-ai-history"><summary>初評與答辯歷史 · {history.length} 輪</summary>{[...history].reverse().map(entry=>{
        const value=((entry.result||{}).dimensions||[]).find(item=>item.key===dimension);
        return <article key={entry.revision}><header><b>R{entry.revision} · {entry.kind==='reply'?'答辯重評':'AI 初評'}</b><time>{stamp(entry.created_at)}</time></header>
          {value && <p className="rcp-ai-history-level">研究證據：{evidenceLabels[value.evidence_verdict]||'待判斷'} · 答辯理解：{defenseLabels[value.defense_verdict]||'尚未答辯'}</p>}
          {entry.context_refreshed && <small>本輪已讀取最新材料</small>}{entry.answer && <details><summary>查看這次答辯</summary><Body body={entry.answer}/></details>}
          {entry.result && entry.result.committee_feedback && <div className="rcp-committee-history"><b>AI 模擬委員會 · {committeeLabels[entry.result.committee_feedback.decision]||'待判斷'}</b><Body body={entry.result.committee_feedback.reply}/></div>}
          {value && <Body body={value.summary}/>}</article>;
      })}</details>
      {!!otherReviews.length && <details className="rcp-ai-history" data-testid="research-cockpit-ai-previous-reviews"><summary>其他評估紀錄 · {otherReviews.length} 次</summary>{otherReviews.map(old=>{
        const oldResult=reviewDimension(old,dimension),oldSpecialist=specialistFor(old,dimension),legacyDraft=!stage&&!item?readLocal(draftKey(project)+':ai:'+scope):null;
        const pastDraft=answers[answerKey(scope,old.id)]||readLocal(answerKey(scope,old.id))||(legacyDraft && legacyDraft.review_id===old.id?legacyDraft:null);
        const pastHistory=Array.isArray(old.history)?[...old.history].sort((a,b)=>Number(a.revision)-Number(b.revision)):[];
        return <article key={old.id}><header><b>{oldSpecialist && oldSpecialist.name||'既有 AI 評估'} · R{old.revision}</b><time>{stamp(old.updated_at||old.created_at)}</time></header>
          {old.stale && <small>材料已更新</small>}{oldResult && <><p className="rcp-ai-history-level">研究證據：{evidenceLabels[oldResult.evidence_verdict]||'待判斷'} · 答辯理解：{defenseLabels[oldResult.defense_verdict]||'尚未答辯'}</p><Body body={oldResult.summary}/></>}
          {pastDraft && typeof pastDraft.answer==='string' && pastDraft.answer.trim() && <details className="rcp-past-review-draft" data-testid="research-cockpit-past-draft"><summary>查看這份紀錄的未提交草稿</summary><pre>{pastDraft.answer}</pre></details>}
          {!!pastHistory.length && <details className="rcp-past-review-rounds" data-testid="research-cockpit-past-rounds"><summary>查看過往問題與答辯 · {pastHistory.length} 輪</summary>{pastHistory.map(entry=><div className="rcp-past-review-round" key={entry.revision}><b>R{entry.revision} · {entry.kind==='reply'?'答辯重評':'AI 初評'}</b>
            {entry.answer && <><small>本輪答辯</small><Body body={entry.answer}/></>}
            {entry.result && entry.result.committee_feedback && <><small>AI 模擬委員會 · {committeeLabels[entry.result.committee_feedback.decision]||'待判斷'}</small><Body body={entry.result.committee_feedback.reply}/></>}
            {!!(entry.result && entry.result.questions||[]).length && <><small>{entry.kind==='reply'?'接續追問':'初評問題'}</small>{entry.result.questions.map((question,index)=><Body key={question.id||index} body={question.question}/>)}</>}
          </div>)}</details>}
        </article>;
      })}</details>}
    </>:!busy && <p className="rcp-ai-empty">請 Bonfire AI 根據這個課題已保存的材料初評，提出具體追問，再用答辯與證據接續研究。</p>}
    {notice && <p className="rcp-ai-notice" role="status">{notice}</p>}
  </section>;
};

W2.ResearchCockpit=function ResearchCockpit({project,projects,workflow,busy,canWrite,onProject,onNavigate,onOpenFile,onSave,onReload,onAdvanced,RichText}){
  const dashboard=workflow && project && text((workflow.project||{}).id)===text(project.id)?workflow.research_dashboard:null;
  const [activeDimension,setActiveDimension]=useState('paper');
  const [activeStage,setActiveStage]=useState('');
  const [activeItem,setActiveItem]=useState('');
  const [aiTarget,setAITarget]=useState('dimension');
  const [draft,setDraft]=useState({});
  const [baseVersion,setBaseVersion]=useState(0);
  const [dirty,setDirty]=useState(false);
  const [saving,setSaving]=useState(false);
  const [conflict,setConflict]=useState(false);
  const [message,setMessage]=useState('');
  const [aiLocal,setAILocal]=useState({}),[aiWorking,setAIWorking]=useState(false);
  const [batch,setBatch]=useState(null);
  const baseVersionRef=useRef(baseVersion);baseVersionRef.current=baseVersion;
  const initialized=useRef(false),dirtyRef=useRef(false),alive=useRef(true),savingRef=useRef(false),tabs=useRef({}),aiPanelRef=useRef(null);
  const batchLock=useRef(false),batchStop=useRef(false),batchController=useRef(null);
  const key=project?draftKey(project):'';
  const serverVersion=Number(dashboard && dashboard.dmp_version)||0;
  const aiRecords=new Map((Array.isArray(dashboard && dashboard.ai_reviews)?dashboard.ai_reviews:[]).map(review=>[review.id,review]));
  Object.values(aiLocal).forEach(review=>{const saved=aiRecords.get(review.id);if(!saved || Number(saved.revision)<Number(review.revision))aiRecords.set(review.id,review);});
  const aiFingerprint=text(dashboard && dashboard.ai_current_fingerprint);
  const aiReviews=Array.from(aiRecords.values()).map(review=>({...review,stale:Boolean(review.stale || (aiFingerprint && review.source_fingerprint!==aiFingerprint))}));
  useEffect(()=>()=>{alive.current=false;if(batchController.current)batchController.current.abort();},[]);
  useEffect(()=>{
    if(!dashboard)return;
    if(!initialized.current){
      const local=readLocal(key);
      if(local && local.assessment && Number.isInteger(local.expected_dmp_version)){
        const rebased=local.expected_dmp_version!==serverVersion && manualUnchanged(workflow,local.expected_dmp_version,serverVersion);
        setDraft(local.assessment);setBaseVersion(rebased?serverVersion:local.expected_dmp_version);setDirty(true);dirtyRef.current=true;
        setConflict(!rebased && local.expected_dmp_version!==serverVersion);
        if(rebased)setMessage('已保留本機編輯並同步最新版本，可繼續答辯或保存。');
      }else{setDraft(assessmentFrom(dashboard));setBaseVersion(serverVersion);}
      initialized.current=true;
    }else if(!dirtyRef.current){setDraft(assessmentFrom(dashboard));setBaseVersion(serverVersion);setConflict(false);}
    else if(baseVersion!==serverVersion){
      if(manualUnchanged(workflow,baseVersion,serverVersion)){setBaseVersion(serverVersion);baseVersionRef.current=serverVersion;setConflict(false);setMessage('已保留本機編輯並同步最新版本，可繼續答辯或保存。');}
      else setConflict(true);
    }
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
  const acceptAIResult=async(result,expectedVersion,skipReload=false)=>{
    if(!alive.current)return;
    setAILocal(current=>({...current,[result.review.id]:result.review}));
    const version=Number(result.dmp_version)||0;
    if(baseVersionRef.current===expectedVersion && version){setBaseVersion(version);baseVersionRef.current=version;setConflict(false);}
    if(!skipReload)try{await onReload();}catch(reason){if(alive.current)setMessage('AI 評估已保存；面板重新讀取失敗：'+text(reason.message||reason));}
  };
  const graph=dashboard && dashboard.stage_graph || {},nodes=graph.nodes||[];
  const selectedStage=nodes.find(node=>node.key===activeStage)||nodes.find(node=>node.key===graph.current_stage)||nodes[0];
  const selectedDimension=(dashboard && dashboard.dimensions||[]).find(item=>item.key===activeDimension);
  const selectedItem=((selectedDimension && selectedDimension.items)||[]).find(item=>item.key===activeItem);
  const revealAI=()=>window.requestAnimationFrame(()=>{if(aiPanelRef.current){aiPanelRef.current.focus({preventScroll:true});aiPanelRef.current.scrollIntoView({behavior:'smooth',block:'start'});}});
  const openStageDefense=stage=>{if(!stage)return;setActiveStage(stage.key);setAITarget('stage');if(dimensions.some(item=>item[0]===stage.dimension))setActiveDimension(stage.dimension);revealAI();};
  const openItemDefense=item=>{setActiveItem(item.key);setAITarget('item');revealAI();};
  const exportDraft=()=>{
    const blob=new Blob([JSON.stringify({project:project.id,expected_dmp_version:baseVersion,assessment:draft},null,2)],{type:'application/json;charset=utf-8'});
    const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='research-assessment-draft-'+text(project.slug||project.id)+'.json';link.click();
    window.setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  const chooseDimension=dimension=>{
    setActiveDimension(dimension);setAITarget('dimension');
    const first=nodes.find(node=>node.dimension===dimension);
    if(first)setActiveStage(first.key);
  };
  const keyboardTab=(event,index)=>{
    const next=event.key==='ArrowRight'?(index+1)%4:event.key==='ArrowLeft'?(index+3)%4:event.key==='Home'?0:event.key==='End'?3:null;
    if(next==null)return;
    event.preventDefault();const dimension=dimensions[next][0];chooseDimension(dimension);if(tabs.current[dimension])tabs.current[dimension].focus();
  };
  const files=dashboard && dashboard.files||[];
  const discipline=graph.discipline;
  const overviewItem=aiTarget==='item'&&selectedItem?((reviewDimension(reviewFor(aiReviews,activeDimension),activeDimension)||{}).criteria||[]).find(entry=>entry.key===selectedItem.key):null;
  const overviewReview=aiTarget==='item'?reviewFor(aiReviews,activeDimension):null;
  const pendingTasks=[...dimensions.filter(([dimension])=>{const review=reviewFor(aiReviews,dimension);return !review||review.stale||!specialistFor(review,dimension);})
    .map(([dimension,title])=>({dimension,title,kind:'dimension'})),
    ...nodes.filter(node=>{const review=stageReviewFor(aiReviews,discipline,node.key);return !review||review.stale||!specialistFor(review,node.dimension);})
      .map(node=>({dimension:node.dimension,stage_key:node.key,title:node.title,kind:'stage'}))];
  const runBatch=async()=>{
    if(!project||!dashboard||!canWrite||savingRef.current||aiWorking||batchLock.current||!pendingTasks.length)return;
    batchLock.current=true;batchStop.current=false;setAIWorking(true);
    const tasks=pendingTasks.slice(),controller=new AbortController();batchController.current=controller;
    let version=Math.max(serverVersion,baseVersionRef.current),done=0;const failures=[];
    setBatch({running:true,done,total:tasks.length,current:'',failures:[],stopping:false});
    try{
      for(const task of tasks){
        if(batchStop.current||!alive.current)break;
        setBatch({running:true,done,total:tasks.length,current:task.title,failures:[...failures],stopping:false});
        try{
          const payload={dimension:task.dimension,expected_dmp_version:version,...(task.stage_key?{stage_key:task.stage_key}:{})};
          const result=await W2.json('/api/research/projects/'+encodeURIComponent(project.id)+'/assessment/ai-reviews',{
            method:'POST',headers:{'Content-Type':'application/json'},signal:controller.signal,body:JSON.stringify(payload)});
          if(!alive.current||controller.signal.aborted)return;
          if(!result.review||!result.review.result||!Number.isInteger(result.dmp_version))throw new Error('AI 未返回可用的評估。');
          await acceptAIResult(result,version,true);version=result.dmp_version;
        }catch(reason){
          if(!alive.current||controller.signal.aborted)return;
          failures.push({title:task.title,message:aiErrorMessage(reason)});
          if(reason.status===409){done++;break;}
        }
        done++;
      }
      if(alive.current){
        try{await onReload();}catch(reason){failures.push({title:'重新讀取',message:aiErrorMessage(reason)});}
        if(alive.current)setBatch({running:false,done,total:tasks.length,current:'',failures:[...failures],stopped:batchStop.current});
      }
    }finally{batchLock.current=false;batchController.current=null;if(alive.current)setAIWorking(false);}
  };
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
      <section className="rcp-experts" aria-label="專家團隊評估">
        <div><span>EXPERT TEAM / BONFIRE AI</span><h3>專家評估研究全程</h3><small>分別檢查四個研究面向與每個流程步驟，提供依據與答辯追問。</small></div>
        <button type="button" data-testid="research-cockpit-ai-batch" disabled={!canWrite||saving||aiWorking||!pendingTasks.length} onClick={runBatch}>
          {pendingTasks.length?'評估全部待評項目 · '+pendingTasks.length+' ↗':'全部已有專家評估'}</button>
        {batch && <div className="rcp-batch-progress" data-testid="research-cockpit-ai-batch-progress" role="status" aria-live="polite">
          <div><b>{batch.running?(batch.stopping?'完成目前項目後停止':'專家正在評估'):(batch.stopped?'已暫停':'本輪已結束')}</b>
            <span>{batch.done} / {batch.total}{batch.current?' · '+batch.current:''}</span></div>
          <progress max={batch.total||1} value={batch.done}/>
          {batch.running && <button type="button" data-testid="research-cockpit-ai-batch-stop" disabled={batch.stopping} onClick={()=>{batchStop.current=true;setBatch(current=>({...current,stopping:true}));}}>完成本項後停止</button>}
          {!!batch.failures.length && <details><summary>{batch.failures.length} 項未完成 · 可再次評估待評項</summary>{batch.failures.map((item,index)=><p key={index}>{item.title}：{item.message}</p>)}</details>}
        </div>}
      </section>
      <div className="rcp-dimensions" role="tablist" aria-label="四個研究面向">{dimensions.map(([dimension,title,en],index)=>{
        const item=(dashboard.dimensions||[]).find(entry=>entry.key===dimension)||{key:dimension,completed:null,total:0};
        const aiReview=reviewFor(aiReviews,dimension),aiResult=reviewDimension(aiReview,dimension);
        return <button key={dimension} ref={node=>{tabs.current[dimension]=node;}} type="button" role="tab" aria-selected={activeDimension===dimension}
          aria-controls={'rcp-assessment-'+project.id} tabIndex={activeDimension===dimension?0:-1} className={'rcp-dimension '+dimension+(activeDimension===dimension?' selected':'')}
          data-testid={'research-cockpit-dimension-'+dimension} onKeyDown={event=>keyboardTab(event,index)} onClick={()=>chooseDimension(dimension)}>
          <header><span>{String(index+1).padStart(2,'0')} / {en}</span><b>↗</b></header><h3>{title}</h3>
          <strong className={item.completed==null?'unknown'+(aiReview?' ai-reviewed':''):''}>{item.completed==null?(aiReview?(aiReview.stale?'需要重評':specialistFor(aiReview,dimension)?'AI 已初評':'待專家評估'):'待評估'):item.completed+' / '+item.total}</strong>
          <small>{item.completed==null?(aiReview?'人工檢查仍待研究者確認':'尚未完成研究者檢查'):'已完成的人工檢查項目'}</small>
          {aiReview && <span className={'rcp-ai-card-flag'+(aiReview.stale?' stale':'')} data-testid="research-cockpit-ai-card-status" data-dimension={dimension}>{aiReview.stale?'AI 初評已過期':!specialistFor(aiReview,dimension)?'既有 AI · 待專家評估':(evidenceLabels[aiResult && aiResult.evidence_verdict]||'AI 初評')+' · 待確認'}</span>}
          <footer>{factSummary(item,files)}</footer>
        </button>;
      })}</div>
      <div className="rcp-evidence-key"><span><i/>實際登記：文件、資料與執行紀錄</span><span><i/>研究者評估：檢查項目與缺口</span><small>檢查數量表示紀錄覆蓋，研究結論仍需證據與覆核。</small></div>
      <section className="rcp-route" aria-label="完整研究路線"><header><div><span>01 / RESEARCH ROUTE</span><h3>從問題走到論證</h3></div><small>{graph.current_stage?'目前紀錄：'+text((nodes.find(node=>node.key===graph.current_stage)||{}).title):'目前階段尚未標記'} · 點選任一步驟查看評估與答辯</small></header>
        <ol>{nodes.map((node,index)=>{const review=stageReviewFor(aiReviews,discipline,node.key),result=reviewDimension(review,node.dimension);return <li key={node.key}><button type="button" className={text(node.status)+(selectedStage && selectedStage.key===node.key && aiTarget==='stage'?' active':'')}
          data-testid={'research-cockpit-stage-'+node.key} aria-pressed={Boolean(selectedStage && selectedStage.key===node.key && aiTarget==='stage')} onClick={()=>openStageDefense(node)}>
          <span>{String(index+1).padStart(2,'0')}<i data-testid={'research-cockpit-stage-ai-'+node.key}>{review?(review.stale?'AI 需重評':'AI：'+(evidenceLabels[result && result.evidence_verdict]||'已評估')):'AI 待評估'}</i></span><strong>{node.title}</strong><small>人工：{statusNames[node.status]||'待標記'} · {(node.evidence||[]).length?(node.evidence||[]).length+' 份證據':'尚未連結證據'}</small></button></li>;})}</ol>
        {!nodes.length && <p className="rcp-empty">尚未建立專業研究路線。可在專業與流程中選擇這個課題的方法。</p>}
      </section>
      <div ref={aiPanelRef} className="rcp-ai-target" role="region" aria-label="專家答辯區" tabIndex={-1}>
        {aiTarget==='item'&&selectedItem&&!itemReviewFor(aiReviews,activeDimension,selectedItem.key)&&overviewItem && <div className="rcp-item-overview" data-testid="research-cockpit-item-overview"><b>面向初評 · {selectedItem.label}</b><span>{overviewReview && overviewReview.stale?'材料已更新，需重新評估':evidenceLabels[overviewItem.evidence_verdict]||'待判斷'}</span>{overviewItem.basis && (RichText?<RichText body={overviewItem.basis} className="rcp-ai-richtext" testId="research-cockpit-item-overview-basis"/>:<p>{overviewItem.basis}</p>)}<small>為此項產生專屬追問後，可以單獨答辯。</small></div>}
        <AIReviewPanel project={project} discipline={discipline} dimension={aiTarget==='stage'&&selectedStage?selectedStage.dimension:activeDimension} stage={aiTarget==='stage'?selectedStage:null} item={aiTarget==='item'?selectedItem:null}
        serverVersion={serverVersion} review={aiTarget==='stage'&&selectedStage?stageReviewFor(aiReviews,discipline,selectedStage.key):aiTarget==='item'&&selectedItem?itemReviewFor(aiReviews,activeDimension,selectedItem.key):reviewFor(aiReviews,activeDimension)} files={files}
        otherReviews={aiReviews.filter(review=>aiTarget==='stage'&&selectedStage?review.stage_key===selectedStage.key&&review.discipline===discipline&&review.id!==(stageReviewFor(aiReviews,discipline,selectedStage.key)||{}).id:aiTarget==='item'&&selectedItem?review.criterion_key===selectedItem.key&&review.dimension===activeDimension&&review.id!==(itemReviewFor(aiReviews,activeDimension,selectedItem.key)||{}).id:!review.stage_key&&!review.criterion_key&&(review.dimension===activeDimension||(review.dimensions||[]).includes(activeDimension))&&review.id!==(reviewFor(aiReviews,activeDimension)||{}).id).sort((a,b)=>text(b.updated_at||b.created_at).localeCompare(text(a.updated_at||a.created_at)))}
        checks={aiTarget==='stage'&&selectedStage?[{key:selectedStage.key,label:selectedStage.title}]:aiTarget==='item'&&selectedItem?[selectedItem]:selectedDimension && selectedDimension.items||[]} RichText={RichText} canWrite={canWrite&&!saving&&!(batch && batch.running)} manualDirty={dirty} onResult={acceptAIResult}
        onReload={onReload} onBusy={setAIWorking} onOpenFile={onOpenFile} onNavigate={onNavigate}/></div>
      <div className="rcp-workgrid"><section className="rcp-stage" data-testid="research-cockpit-stage-detail">
        <header><span>02 / STAGE DETAIL</span><b>{selectedStage?'人工：'+(statusNames[selectedStage.status]||'待標記'):'待建立'}</b></header>
        <h3>{selectedStage?selectedStage.title:'選擇一個研究步驟'}</h3>
        {selectedStage && <><dl>{[['plan','本步計畫'],['findings','研究發現'],['blockers','尚待解決'],['next_action','下一個動作']].map(([name,label])=>{
          const value=text((selectedStage.task||{})[name]);return value?<div key={name}><dt>{label}</dt><dd>{value}</dd></div>:null;
        })}</dl>{!['plan','findings','blockers','next_action'].some(name=>text((selectedStage.task||{})[name]).trim()) && <p className="rcp-empty">這一步尚未記錄計畫、發現與下一個動作。</p>}
          <div className="rcp-stage-evidence"><span>固定版本證據</span>{(selectedStage.evidence||[]).map((artifact,index)=><Artifact key={artifact.file_version_id||index} artifact={artifact} onOpen={onOpenFile}/>)}
            {!(selectedStage.evidence||[]).length && <p>尚未連結本步證據；已有論文不會自動完成這個步驟。</p>}</div>
          <footer><small>研究紀錄 V{selectedStage.revision||0} · {(selectedStage.task||{}).assignee==='codex'?'Codex':(selectedStage.task||{}).assignee==='user'?'研究者':'共同協作'}</small>
            <button type="button" className="rcp-defend-stage" data-testid="research-cockpit-stage-defend" onClick={()=>openStageDefense(selectedStage)}>針對本步答辯 ↗</button>
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
          const focusedReview=itemReviewFor(aiReviews,activeDimension,item.key),currentReview=focusedReview||reviewFor(aiReviews,activeDimension),aiItem=((reviewDimension(currentReview,activeDimension)||{}).criteria||[]).find(entry=>entry.key===item.key);
          return <article key={item.key} className={(value.status||'unassessed')+(aiTarget==='item'&&activeItem===item.key?' rcp-check-selected':'')}><div><label htmlFor={'rcp-check-'+activeDimension+'-'+item.key}>{item.label}<small className="rcp-check-ai" data-testid={'research-cockpit-check-ai-'+activeDimension+'-'+item.key}>{currentReview?(currentReview.stale?'AI 需重評':aiItem?(focusedReview?'AI 專項：':'AI 面向：')+(evidenceLabels[aiItem.evidence_verdict]||'待判斷'):'AI 待評估'):'AI 待評估'}</small></label>
            <select id={'rcp-check-'+activeDimension+'-'+item.key} data-testid={'research-cockpit-check-'+activeDimension+'-'+item.key} value={value.status||'unassessed'} disabled={!canWrite||saving}
              aria-label={item.label+' 人工檢查'} onChange={event=>changeItem(activeDimension,item.key,{status:event.target.value})}>{['unassessed','missing','in_progress','ready'].map(status=><option key={status} value={status}>{'人工：'+statusNames[status]}</option>)}</select></div>
            <button type="button" className="rcp-defend-item" data-testid={'research-cockpit-item-defend-'+activeDimension+'-'+item.key} aria-pressed={aiTarget==='item'&&activeItem===item.key} onClick={()=>openItemDefense(item)}>{focusedReview?'查看本項答辯':'針對此項答辯'} ↗</button>
            <details><summary>備註與證據{(value.file_version_ids||[]).length?' · '+value.file_version_ids.length+' 份':''}{value.note?' · 已有紀錄':''}</summary>
              <textarea aria-label={item.label+'的評估備註'} data-testid={'research-cockpit-note-'+activeDimension+'-'+item.key} disabled={!canWrite||saving} value={value.note||''} maxLength={8000}
                placeholder="這項檢查的判斷、缺口與證據位置" onChange={event=>changeItem(activeDimension,item.key,{note:event.target.value})}/>
              <div className="rcp-file-checks">{files.map(file=><label key={file.file_version_id}><input type="checkbox" disabled={!canWrite||saving} checked={(value.file_version_ids||[]).includes(file.file_version_id)} onChange={event=>changeItem(activeDimension,item.key,{file_version_ids:event.target.checked?[...(value.file_version_ids||[]),file.file_version_id]:(value.file_version_ids||[]).filter(id=>id!==file.file_version_id)})}/><span>V{file.version} · {file.logical_path}</span></label>)}</div>
              {(item.evidence||[]).map((artifact,index)=><Artifact key={artifact.file_version_id||index} artifact={artifact} onOpen={onOpenFile}/>)}</details></article>;
        })}</div>
        {conflict && <div className="rcp-conflict" role="alert">伺服器的人工評估也有更新，本機編輯仍保留；你可以繼續答辯，並下載草稿後再對照處理。
          <button type="button" data-testid="research-cockpit-export-draft" disabled={saving} onClick={exportDraft}>下載本機草稿</button>
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
