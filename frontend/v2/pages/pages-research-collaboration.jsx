/* Version-pinned research artifacts and portable Codex collaboration tasks. */
(() => {
const W2 = window.W2;
const { useState, useEffect, useRef } = React;
const text = value => value == null ? "" : String(value);
const roles = {design:"研究設計",dataset:"資料",code:"程式",visualization:"視覺化",report:"研究報告",other:"其他產物"};
const errorText = async response => {
  const value = await response.json().catch(() => ({}));
  return text(value.detail || value.message || "讀取失敗（" + response.status + "）");
};
const scopedPath = (projectId, candidate) => {
  if (typeof candidate !== "string" || !candidate.startsWith("/api/research/projects/")) return "";
  try {
    const url = new URL(candidate, location.origin);
    return url.origin === location.origin && url.pathname.startsWith("/api/research/projects/" + encodeURIComponent(projectId) + "/")
      && !candidate.includes("\\") ? url.pathname + url.search : "";
  } catch (_error) { return ""; }
};
const contentPath = (projectId, artifact, preview = false) => {
  const version = Number(artifact.version);
  const explicit = scopedPath(projectId, preview ? artifact.preview_path : artifact.download_path || artifact.content_path);
  if (explicit) return explicit;
  if (!artifact.file_id || !Number.isInteger(version) || version < 1) return "";
  return "/api/research/projects/" + encodeURIComponent(projectId) + "/files/" + encodeURIComponent(artifact.file_id) +
    (preview ? "/preview" : "/content") + "?version=" + version;
};
const saveText = (name, value, mime = "text/plain;charset=utf-8") => {
  const url = URL.createObjectURL(new Blob([value], {type:mime}));
  const link = document.createElement("a"); link.href = url; link.download = name;
  link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
};
const sandboxDocument = source => {
  const policy = "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' blob:; style-src 'unsafe-inline'; img-src data: blob:; font-src data:; media-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none'; navigate-to 'none'";
  const clean = source.replace(/<base\b[^>]*>/gi, "").replace(/<meta\b[^>]*http-equiv\s*=\s*["']?refresh[^>]*>/gi, "")
    .replace(/\s(?:href|action|formaction)\s*=\s*(["'])(?!#|data:|blob:)[\s\S]*?\1/gi, "");
  return "<!doctype html><meta charset=\"utf-8\"><meta http-equiv=\"Content-Security-Policy\" content=\"" + policy + "\">" + clean;
};

function ArtifactPreview({ project, artifact, onClose }) {
  const [state, setState] = useState({busy:true});
  useEffect(() => {
    const controller = new AbortController(); let alive = true, url = "";
    setState({busy:true});
    (async () => {
      const type = text(artifact.content_type).toLowerCase(), kind = text(artifact.file_kind);
      const isHtml = kind === "html" || type.includes("text/html");
      const isImage = kind === "image" || type.startsWith("image/");
      const isPdf = kind === "pdf" || type === "application/pdf";
      const path = contentPath(project.id, artifact, !(isHtml || isImage || isPdf));
      if (!path) throw new Error("這個產物缺少可驗證的文件版本，請重新載入。");
      if (isHtml || isImage || isPdf) {
        if (type.includes("svg")) { if(alive)setState({notice:"SVG 產物可下載檢視。"}); return; }
        const response = await W2.fetch(path, {signal:controller.signal,cache:"no-store",redirect:"error"});
        if (!response.ok) throw new Error(await errorText(response));
        const blob = await response.blob();
        if (!alive) return;
        if (isHtml) setState({html:sandboxDocument(await blob.text())});
        else { url = URL.createObjectURL(blob); setState(isImage ? {image:url} : {pdf:url}); }
      } else {
        const preview = await W2.json(path,{signal:controller.signal,cache:"no-store",redirect:"error"});
        if (alive) setState({table:preview.table,text:preview.text || "",notice:!preview.table&&!preview.text?"此產物可下載至研究工作環境檢視。":""});
      }
    })().catch(error => { if (alive && error.name !== "AbortError") setState({error:text(error.message || error)}); });
    return () => { alive=false;controller.abort();if(url)URL.revokeObjectURL(url); };
  }, [project.id,artifact.file_version_id]);
  return <section className="rc-artifact-preview" aria-label="研究產物預覽" data-testid="research-artifact-preview">
    <header><div><span>PINNED OUTPUT / V{text(artifact.version || "—")}</span><strong>{artifact.title || artifact.logical_path || "研究產物"}</strong></div><button type="button" onClick={onClose} aria-label="關閉產物預覽">×</button></header>
    {state.busy && <div className="rc-inline-status" role="status"><i/>正在載入研究產物…</div>}
    {state.error && <p className="rc-inline-error" role="alert">{state.error}</p>}
    {state.notice && <p className="rc-empty">{state.notice}</p>}
    {state.image && <img src={state.image} alt={artifact.title || "研究圖表"}/>}
    {state.html != null && <iframe title="研究視覺化" sandbox="allow-scripts" referrerPolicy="no-referrer" srcDoc={state.html}/>}
    {state.pdf && <iframe title="研究 PDF" sandbox="" referrerPolicy="no-referrer" src={state.pdf}/>}
    {state.table && <div className="rc-table-scroll"><table><thead><tr>{(state.table.columns || []).map((value,index)=><th key={index}>{text(value)}</th>)}</tr></thead>
      <tbody>{(state.table.rows || []).slice(0,100).map((row,index)=><tr key={index}>{row.map((value,column)=><td key={column}>{text(value)}</td>)}</tr>)}</tbody></table>
      <small>資料預覽 · 最多顯示 100 行，完整資料可下載。</small></div>}
    {!state.table && state.text && <pre>{state.text.slice(0,50000)}</pre>}
  </section>;
}

W2.ResearchStageCollaboration = function ResearchStageCollaboration({ project, template, stage, saved, canWrite, saving, hasDraft, onAttach, onError }) {
  const [context, setContext] = useState(null),[loading,setLoading] = useState(true),[failure,setFailure] = useState("");
  const [open,setOpen] = useState(false),[copyStatus,setCopyStatus] = useState("");
  const [role,setRole] = useState("visualization"),[uploading,setUploading] = useState(false),[uploadMessage,setUploadMessage] = useState("");
  const [selected,setSelected] = useState(null),[linkId,setLinkId] = useState("");
  const downloadController = useRef(null),uploadController = useRef(null),fileInput = useRef(null);
  const currentIdentity = useRef(""); currentIdentity.current = project.id + ":" + stage.key;
  useEffect(() => {
    const controller = new AbortController();let alive=true;
    currentIdentity.current = project.id + ":" + stage.key;
    setLoading(true);setFailure("");setContext(null);setSelected(null);
    W2.json("/api/research/projects/"+encodeURIComponent(project.id)+"/collaboration?stage="+encodeURIComponent(stage.key),{cache:"no-store",signal:controller.signal})
      .then(value=>{if(alive)setContext(value);}).catch(error=>{if(alive&&error.name!=="AbortError")setFailure(text(error.message||error));})
      .finally(()=>{if(alive)setLoading(false);});
    return ()=>{alive=false;currentIdentity.current="";controller.abort();if(downloadController.current)downloadController.current.abort();if(uploadController.current)uploadController.current.abort();};
  },[project.id,stage.key,saved.revision]);
  const artifacts = context && Array.isArray(context.artifacts) ? context.artifacts : (saved.artifacts || []);
  const files = context && Array.isArray(context.files) ? context.files : [];
  const prompt = text(context && (context.prompt || context.agent_prompt));
  const copyPrompt = async () => {
    try { await navigator.clipboard.writeText(prompt);setCopyStatus("協作任務已複製，可交給 Codex 接續。"); }
    catch(_error) { setCopyStatus("瀏覽器未開放複製，請下載協作說明。"); }
  };
  const download = async artifact => {
    const path = contentPath(project.id,artifact);
    if(!path){onError("這個產物缺少可驗證的下載版本。");return;}
    if(downloadController.current)downloadController.current.abort();
    const controller = new AbortController();downloadController.current=controller;
    try {
      const response = await W2.fetch(path,{signal:controller.signal,cache:"no-store",redirect:"error"});
      if(!response.ok)throw new Error(await errorText(response));
      const blob=await response.blob();if(controller.signal.aborted)return;
      const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=text(artifact.logical_path||artifact.title||"research-artifact").split("/").pop();link.click();
      window.setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(error){if(error.name!=="AbortError")onError(text(error.message||error));}
  };
  const upload = async event => {
    const file=event.target.files && event.target.files[0];if(!file||!canWrite||uploading||saving)return;
    const identity=currentIdentity.current;let uploaded=null;
    const controller=new AbortController();uploadController.current=controller;
    setUploading(true);setUploadMessage("");
    try {
      const form=new FormData(),name=text(file.name).split(/[\\/]/).pop()||"artifact";
      form.set("file",file);form.set("logical_path","stages/"+template.key+"/"+stage.key+"/"+name);
      form.set("commit_message","Add "+stage.key+" research "+role);
      const response=await W2.fetch("/api/research/projects/"+encodeURIComponent(project.id)+"/files",{method:"POST",body:form,redirect:"error",signal:controller.signal});
      if(!response.ok)throw new Error(await errorText(response));
      uploaded=await response.json();
      if(currentIdentity.current!==identity)return;
      const version=uploaded.version||{};
      if(!version.id)throw new Error("上傳成功，但回應缺少文件版本。");
      await onAttach({file_version_id:version.id,role,title:name});
      setUploadMessage("產物與本步研究紀錄已保存。");
    }catch(error){
      if(currentIdentity.current!==identity)return;
      const message=uploaded?"文件已保存至課題庫，但尚未連結此步驟。請重新載入，再從既有文件連結。 "+text(error.message||error):text(error.message||error);
      setUploadMessage(message);onError(message);
    }finally{if(currentIdentity.current===identity){setUploading(false);if(fileInput.current)fileInput.current.value="";}}
  };
  const linkExisting = async () => {
    if(!linkId||!canWrite||saving)return;
    const file=files.find(item=>text(item.file_version_id||item.id)===linkId);if(!file)return;
    try{await onAttach({file_version_id:linkId,role,title:file.title||text(file.logical_path).split("/").pop()});}
    catch(error){setUploadMessage(text(error.message||error));}
  };
  return <section className="rc-stage-collaboration" data-testid="research-stage-collaboration">
    <div className="rc-handoff-heading"><div><span>HUMAN + CODEX / SHARED RESEARCH</span><h4>把這一步交給 Codex 協作。</h4><p>帶上當前研究背景、資料版本與產出要求，完成後將成果回到同一項目。</p></div>
      <button type="button" className="btn primary" aria-expanded={open} onClick={()=>setOpen(value=>!value)} data-testid="research-codex-open">{open?"收起協作任務":"與 Codex 協作 ↗"}</button></div>
    {open && <div className="rc-handoff" data-testid="research-codex-handoff">
      {loading?<div className="rc-inline-status" role="status"><i/>正在整理此步研究背景…</div>:failure?<p className="rc-inline-error" role="alert">{failure}</p>:<>
        <p>複製協作任務或下載說明，交給你正在使用的 Codex。它會依項目權限讀取資料、提交產物並回寫進度。</p>
        {hasDraft && <p className="rc-draft-note">這一步有尚未保存的編輯，請先「保存這一步」，讓 Codex 取得最新的研究設計。</p>}
        <div className="rc-handoff-actions"><button type="button" className="btn primary" onClick={copyPrompt} disabled={!prompt||hasDraft} data-testid="research-codex-copy">複製協作任務</button>
          <button type="button" className="btn" onClick={()=>saveText("AGENTS.md",prompt)} disabled={!prompt||hasDraft}>下載協作說明</button>
          <button type="button" className="btn" onClick={()=>saveText("research-collaboration.json",JSON.stringify(context,null,2),"application/json;charset=utf-8")}>下載項目契約</button></div>
        <details><summary>查看此次交接內容</summary><pre>{prompt}</pre></details>
        <p className="rc-copy-status" role="status">{copyStatus || "研究資料與金鑰分開處理；此交接內容不包含登入憑證。"}</p>
        <details className="rc-connect"><summary>第一次連接 Codex</summary><p>在 Codex 工作環境安裝科研工具，並配置你自己的科研 API Key。完成後即可重複使用每一步的協作任務。</p>
          {typeof W2.openBusinessAction === "function" && <div><button type="button" className="btn" onClick={()=>W2.openBusinessAction("research_cli_show")}>查看科研工具安裝方式</button>
            <button type="button" className="btn" onClick={()=>W2.openBusinessAction("research_api_key_issue")}>取得我的科研金鑰</button></div>}</details>
      </>}
    </div>}
    <div className="rc-artifact-heading"><div><span>OUTPUT REGISTER / VERSIONED ARTIFACTS</span><h4>研究產物與視覺化 <b>{artifacts.length}</b></h4></div><small>設計 · 資料 · 程式 · 圖表 · 報告</small></div>
    {loading && !artifacts.length?<div className="rc-inline-status" role="status"><i/>正在讀取本步產物…</div>:artifacts.length?<div className="rc-artifact-grid">{artifacts.map((artifact,index)=><article key={artifact.file_version_id||index} className={selected&&selected.file_version_id===artifact.file_version_id?"is-selected":""} data-testid="research-artifact-card">
      <header><span>{roles[artifact.role]||"研究產物"}</span><code>V{artifact.version||"—"}</code></header><h5>{artifact.title||text(artifact.logical_path).split("/").pop()||"研究產物"}</h5>
      <small>{artifact.logical_path || "已連結固定文件版本"}</small><footer><button type="button" onClick={()=>setSelected(artifact)} disabled={!artifact.file_id}>預覽 ↗</button><button type="button" onClick={()=>download(artifact)} disabled={!contentPath(project.id,artifact)}>下載 ↓</button></footer>
    </article>)}</div>:<p className="rc-empty">此步尚未連結研究產物。可上傳設計、資料與圖表，或讓 Codex 完成後回寫。</p>}
    {selected && <ArtifactPreview project={project} artifact={selected} onClose={()=>setSelected(null)}/>}
    {canWrite && <div className="rc-artifact-tools"><label><span>產物類型</span><select value={role} onChange={event=>setRole(event.target.value)} disabled={uploading||saving}>{Object.entries(roles).map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
      <label className="rc-upload"><span>{uploading?"正在保存產物…":"上傳並連結產物 ↑"}</span><input type="file" ref={fileInput} onChange={upload} disabled={uploading||saving} data-testid="research-artifact-upload"/></label>
      <div className="rc-existing"><select aria-label="選擇既有研究產物" value={linkId} onChange={event=>setLinkId(event.target.value)} disabled={saving||uploading}><option value="">連結課題庫中的既有版本</option>
        {files.map(file=><option key={file.file_version_id||file.id} value={file.file_version_id||file.id}>{file.logical_path||file.title} · V{file.version}</option>)}</select><button type="button" className="btn" onClick={linkExisting} disabled={!linkId||saving||uploading}>連結</button></div>
    </div>}
    {uploadMessage && <p className="rc-upload-status" role="status">{uploadMessage}</p>}
  </section>;
};
})();
