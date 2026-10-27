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

W2.ResearchCockpit=function ResearchCockpit({project,projects,workflow,busy,canWrite,onProject,onNavigate,onOpenFile,onSave,onReload,onAdvanced}){
  const dashboard=workflow && project && text((workflow.project||{}).id)===text(project.id)?workflow.research_dashboard:null;
  const [activeDimension,setActiveDimension]=useState('paper');
  const [activeStage,setActiveStage]=useState('');
  const [draft,setDraft]=useState({});
  const [baseVersion,setBaseVersion]=useState(0);
  const [dirty,setDirty]=useState(false);
  const [saving,setSaving]=useState(false);
  const [conflict,setConflict]=useState(false);
  const [message,setMessage]=useState('');
  const initialized=useRef(false),dirtyRef=useRef(false),alive=useRef(true),savingRef=useRef(false),tabs=useRef({});
  const key=project?draftKey(project):'';
  const serverVersion=Number(dashboard && dashboard.dmp_version)||0;
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
    if(!project || !dashboard || !canWrite || savingRef.current || conflict || !dirty)return;
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
        return <button key={dimension} ref={node=>{tabs.current[dimension]=node;}} type="button" role="tab" aria-selected={activeDimension===dimension}
          aria-controls={'rcp-assessment-'+project.id} tabIndex={activeDimension===dimension?0:-1} className={'rcp-dimension '+dimension+(activeDimension===dimension?' selected':'')}
          data-testid={'research-cockpit-dimension-'+dimension} onKeyDown={event=>keyboardTab(event,index)} onClick={()=>chooseDimension(dimension)}>
          <header><span>{String(index+1).padStart(2,'0')} / {en}</span><b>↗</b></header><h3>{title}</h3>
          <strong className={item.completed==null?'unknown':''}>{item.completed==null?'待評估':item.completed+' / '+item.total}</strong>
          <small>{item.completed==null?'尚未完成研究者檢查':'已完成的檢查項目'}</small><footer>{factSummary(item,files)}</footer>
        </button>;
      })}</div>
      <div className="rcp-evidence-key"><span><i/>實際登記：文件、資料與執行紀錄</span><span><i/>研究者評估：檢查項目與缺口</span><small>檢查數量表示紀錄覆蓋，研究結論仍需證據與覆核。</small></div>
      <section className="rcp-route" aria-label="完整研究路線"><header><div><span>01 / RESEARCH ROUTE</span><h3>從問題走到論證</h3></div><small>{graph.current_stage?'目前紀錄：'+text((nodes.find(node=>node.key===graph.current_stage)||{}).title):'目前階段尚未標記'}</small></header>
        <ol>{nodes.map((node,index)=><li key={node.key}><button type="button" className={text(node.status)+(selectedStage && selectedStage.key===node.key?' active':'')}
          data-testid={'research-cockpit-stage-'+node.key} aria-pressed={Boolean(selectedStage && selectedStage.key===node.key)} onClick={()=>{setActiveStage(node.key);if(dimensions.some(item=>item[0]===node.dimension))setActiveDimension(node.dimension);}}>
          <span>{String(index+1).padStart(2,'0')}<i>{statusNames[node.status]||'待標記'}</i></span><strong>{node.title}</strong><small>{(node.evidence||[]).length?(node.evidence||[]).length+' 份固定版本證據':'尚未連結證據'}</small></button></li>)}</ol>
        {!nodes.length && <p className="rcp-empty">尚未建立專業研究路線。可在專業與流程中選擇這個課題的方法。</p>}
      </section>
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
        <footer><span>研究者逐項標記 · 版本化保存</span><button type="button" data-testid="research-cockpit-save" disabled={!canWrite||!dirty||saving||conflict} onClick={save}>{saving?'正在保存…':'保存評估'}</button></footer>
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
