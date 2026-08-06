/* WAREHOUSE OS 2.1 · RESEARCH VAULT
   Swiss data workspace: native Git commits, inline previews and semantic diffs. */
(() => {
const W2 = window.W2;
const { useState, useEffect, useMemo, useRef } = React;
const { Folio, Band } = W2;

const clean = value => value == null ? "" : String(value);
const compact = value => {
  const size = Number(value) || 0;
  if (size >= 1024 * 1024 * 1024) return (size / 1024 / 1024 / 1024).toFixed(1) + " GB";
  if (size >= 1024 * 1024) return (size / 1024 / 1024).toFixed(1) + " MB";
  if (size >= 1024) return (size / 1024).toFixed(1) + " KB";
  return size + " B";
};
const shortSha = value => clean(value).slice(0, 8) || "—";
const stamp = value => value ? clean(value).replace("T", " ").slice(0, 16) : "—";
const kindName = {
  document: "TEXT", pdf: "PDF", html: "HTML", dataset: "DATA",
  database: "DB", code: "CODE", notebook: "NOTEBOOK", image: "IMAGE", binary: "BINARY",
};
const ASSET_TAXONOMY = [
  ["all", "ALL", "全部"],
  ["manuscript", "PAPER", "論文"],
  ["literature", "LIT", "文獻"],
  ["code", "CODE", "代碼"],
  ["dataset", "DATA", "數據"],
  ["database", "DB", "數據庫"],
  ["notebook", "NOTE", "分析簿"],
  ["figure", "FIG", "圖表"],
  ["administration", "ADMIN", "管理"],
  ["other", "OTHER", "其他"],
];
const assetClassOf = file => {
  if (clean(file && file.asset_class)) return clean(file.asset_class);
  const path = clean(file && file.logical_path).toLowerCase().replace(/\\/g, "/");
  const extension = (path.match(/\.[a-z0-9]+$/) || [""])[0];
  const tokens = new Set(path.split(/[^a-z0-9]+/).filter(Boolean));
  if ([".py", ".r", ".jl", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cc", ".cpp", ".h", ".hpp", ".go", ".rs", ".swift", ".sh", ".zsh"].includes(extension)) return "code";
  if (file && file.file_kind === "database") return "database";
  if (file && file.file_kind === "notebook") return "notebook";
  if (file && file.file_kind === "image") return "figure";
  if (file && file.file_kind === "dataset") return "dataset";
  if (["administration", "admin", "manifest", "metadata", "governance", "protocol", "dmp", "config"].some(token => tokens.has(token))) return "administration";
  if (["literature", "reference", "references", "bibliography", "citation", "citations", "sources"].some(token => tokens.has(token))) return "literature";
  if (["manuscript", "article", "thesis", "dissertation", "submission", "preprint", "draft"].some(token => tokens.has(token))) return "manuscript";
  if (["data", "dataset", "datasets", "results", "outputs", "inputs"].some(token => tokens.has(token)) || [".json", ".jsonl", ".ndjson"].includes(extension)) return "dataset";
  if (file && ["document", "html", "pdf"].includes(file.file_kind)) return "manuscript";
  return file && file.file_kind === "code" ? "code" : "other";
};
const assetTaxon = key => ASSET_TAXONOMY.find(item => item[0] === key) || ASSET_TAXONOMY[9];
const apiError = async response => {
  const payload = await response.json().catch(() => ({}));
  const detail = payload.detail || payload.message || response.statusText;
  return new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
};
const RESEARCH_TABS = [
  ["overview", "總覽"],
  ["guide", "論文導引"],
  ["projects", "課題庫"],
  ["workflow", "研究流程"],
  ["evidence", "證據與覆核"],
  ["execution", "重現運算"],
  ["revisions", "版本譜系"],
  ["formats", "格式能力"],
];
const FORMAT_ROWS = [
  ["DOCX", "WORD / OPENXML", "原貌渲染 · 可選文字", "字符批注 · 語義 DIFF"],
  ["PDF", "PAGED DOCUMENT", "原文內嵌", "提取文字 DIFF"],
  ["HTML", "WEB DOCUMENT", "安全沙箱", "語義文字 DIFF"],
  ["CSV / TSV", "TABULAR DATA", "表格閱覽", "行級 DIFF"],
  ["SQLITE", "DATABASE", "Schema + 樣本", "Schema / 內容 DIFF"],
  ["CODE", "SOURCE FILES", "等寬原文", "逐行 DIFF"],
  ["IPYNB", "NOTEBOOK", "Cell 閱覽", "語義文字 DIFF"],
  ["IMAGE", "RESEARCH FIGURE", "原圖內嵌", "校驗值 DIFF"],
];
const RESEARCH_MEMORY_VERSION = 1;
const RESEARCH_READER_TABS = new Set(["review", "preview", "diff", "versions"]);
const researchMemoryKey = () => {
  const user = window.W2_USER || {};
  const actor = clean(user.id || user.user_id || user.username || "anonymous");
  return "w2_research_memory:v1:" + encodeURIComponent(W2.tenant() || "default") +
    ":" + encodeURIComponent(actor);
};
const readResearchMemory = () => {
  try {
    const value = JSON.parse(localStorage.getItem(researchMemoryKey()) || "{}");
    return value && value.version === RESEARCH_MEMORY_VERSION && typeof value === "object"
      ? value : { version: RESEARCH_MEMORY_VERSION, project_id: "", projects: {} };
  } catch (_error) {
    return { version: RESEARCH_MEMORY_VERSION, project_id: "", projects: {} };
  }
};
const writeResearchMemory = updater => {
  try {
    const current = readResearchMemory();
    const next = updater(current) || current;
    localStorage.setItem(researchMemoryKey(), JSON.stringify({
      ...next, version: RESEARCH_MEMORY_VERSION, updated_at: Date.now(),
    }));
    return true;
  } catch (_error) { return false; }
};
const rememberedResearchProject = () => clean(readResearchMemory().project_id);
const rememberedResearchFile = projectId => {
  const entry = (readResearchMemory().projects || {})[clean(projectId)] || {};
  return clean(entry.file_id);
};
const rememberedResearchTab = (projectId, fileId, fallback = "preview") => {
  const entry = (readResearchMemory().projects || {})[clean(projectId)] || {};
  return clean(entry.file_id) === clean(fileId) && RESEARCH_READER_TABS.has(entry.tab)
    ? entry.tab : fallback;
};
const rememberResearchSelection = ({ projectId, fileId, tab, section }) => {
  writeResearchMemory(current => {
    const projects = { ...(current.projects || {}) };
    const id = clean(projectId || current.project_id);
    if (id) {
      const before = projects[id] || {};
      const nextFile = clean(fileId || before.file_id);
      projects[id] = {
        ...before,
        file_id: nextFile,
        tab: RESEARCH_READER_TABS.has(tab) ? tab : before.tab,
        opened_at: Date.now(),
        positions: nextFile === clean(before.file_id) ? before.positions || {} : {},
      };
    }
    const retained = Object.fromEntries(Object.entries(projects)
      .sort((left, right) => Number(right[1].opened_at) - Number(left[1].opened_at))
      .slice(0, 24));
    return {
      ...current,
      project_id: id,
      section: RESEARCH_TABS.some(item => item[0] === section) ? section : current.section,
      projects: retained,
    };
  });
};
const researchReadingPosition = (projectId, fileId, tab) => {
  const entry = (readResearchMemory().projects || {})[clean(projectId)] || {};
  if (clean(entry.file_id) !== clean(fileId)) return null;
  const position = (entry.positions || {})[tab];
  return position && Number.isFinite(Number(position.top)) ? position : null;
};
const saveResearchReadingPosition = (element, projectId, fileId, tab) => {
  if (!element || !projectId || !fileId || !RESEARCH_READER_TABS.has(tab)) return;
  const top = Math.max(0, Math.round(Number(element.scrollTop) || 0));
  const range = Math.max(0, Number(element.scrollHeight) - Number(element.clientHeight));
  writeResearchMemory(current => {
    const projects = { ...(current.projects || {}) };
    const before = projects[clean(projectId)] || {};
    if (clean(before.file_id) !== clean(fileId)) return current;
    projects[clean(projectId)] = {
      ...before,
      positions: {
        ...(before.positions || {}),
        [tab]: { top, ratio: range ? top / range : 0, saved_at: Date.now() },
      },
    };
    return { ...current, projects };
  });
};
const restoreResearchReadingPosition = (element, projectId, fileId, tab) => {
  const position = researchReadingPosition(projectId, fileId, tab);
  if (!element || !position) return false;
  const range = Math.max(0, Number(element.scrollHeight) - Number(element.clientHeight));
  const ratio = Math.max(0, Math.min(1, Number(position.ratio) || 0));
  element.scrollTop = Math.min(range, range > 0 ? Math.round(range * ratio) : Number(position.top) || 0);
  return true;
};

const Metric = ({ label, value, note }) => (
  <div className="rv-metric">
    <span>{label}</span>
    <strong className="num">{value}</strong>
    <small>{note}</small>
  </div>
);

const EmptyPanel = ({ title, copy }) => (
  <div className="rv-empty">
    <span>∅</span>
    <strong>{title}</strong>
    <p>{copy}</p>
  </div>
);

const CommandButton = ({ tool, command, note, args, disabled = false }) => (
  <button type="button" className="rv-command" disabled={disabled}
    data-command={command}
    onClick={() => W2.openBusinessAction({ tool_name: tool, arguments: args || {} })}>
    <span>CMD</span>
    <code>{command}</code>
    <small>{note}</small>
    <b>↗</b>
  </button>
);

const ProjectRail = ({ projects, projectId, onSelect, emptyCopy }) => (
  <aside className="rv-projects">
    <header><span>PROJECTS</span><b>{String(projects.length).padStart(2, "0")}</b></header>
    {!projects.length && <EmptyPanel title="尚無科研課題" copy={emptyCopy || "建立第一個課題後即可托管文件與版本。"}/>}
    {projects.map((project, index) => (
      <button key={project.id} className={clean(project.id) === clean(projectId) ? "active" : ""}
        onClick={() => onSelect(clean(project.id))}>
        <em>{String(index + 1).padStart(2, "0")}</em>
        <span><strong>{project.title}</strong><small>{project.research_area || "GENERAL RESEARCH"}</small></span>
        <i>{project.file_count || 0}</i>
      </button>
    ))}
  </aside>
);

const TextPreview = ({ text }) => (
  <pre className="rv-code">{clean(text) || "此版本沒有可提取的文字。"}</pre>
);

const DatasetPreview = ({ table }) => {
  const columns = Array.isArray(table && table.columns) ? table.columns : [];
  const rows = Array.isArray(table && table.rows) ? table.rows : [];
  if (!columns.length) return <EmptyPanel title="空數據集" copy="文件中沒有可顯示的欄位。"/>;
  return (
    <div className="rv-table-wrap">
      <table className="rv-table">
        <thead><tr>{columns.map((column, index) => <th key={index}>{column || "COLUMN " + (index + 1)}</th>)}</tr></thead>
        <tbody>{rows.map((row, rowIndex) => (
          <tr key={rowIndex}>{columns.map((_, cellIndex) => <td key={cellIndex}>{clean(row[cellIndex])}</td>)}</tr>
        ))}</tbody>
      </table>
      {table.truncated && <div className="rv-limit">PREVIEW LIMITED · 僅顯示前 {rows.length} 行</div>}
    </div>
  );
};

const DatabasePreview = ({ metadata, schema }) => {
  const tables = Array.isArray(metadata && metadata.tables) ? metadata.tables : [];
  if (!tables.length) return <TextPreview text={schema}/>;
  return (
    <div className="rv-database">
      <aside>
        <span>SCHEMA OBJECTS</span>
        {tables.map(table => (
          <a key={table.name} href={"#rv-db-" + encodeURIComponent(table.name)}>
            <strong>{table.name}</strong>
            <small>{table.type} · {(table.columns || []).length} COL</small>
          </a>
        ))}
      </aside>
      <div>
        {tables.map(table => (
          <section id={"rv-db-" + encodeURIComponent(table.name)} key={table.name}>
            <header>
              <strong>{table.name}</strong>
              <span>{table.sample_rows || 0} SAMPLE ROWS</span>
            </header>
            <DatasetPreview table={{ columns: table.columns || [], rows: table.rows || [] }}/>
          </section>
        ))}
        {metadata.truncated && <div className="rv-limit">SCHEMA LIMITED · 僅顯示前 20 個對象</div>}
      </div>
    </div>
  );
};

const DiffPreview = ({ data }) => {
  if (!data || data.available === false) {
    return <EmptyPanel title="第一個版本" copy="上傳下一個版本後，這裡會出現語義差異。"/>;
  }
  const diff = data.diff || {};
  if (diff.mode === "tabular") {
    const groups = [
      ["ADDED", diff.added || [], "add"],
      ["REMOVED", diff.removed || [], "del"],
      ["CHANGED", diff.changed || [], "chg"],
    ];
    return (
      <div className="rv-tab-diff">
        <div className="rv-diff-summary">
          <b>+{(diff.summary || {}).added || 0}</b>
          <b>−{(diff.summary || {}).removed || 0}</b>
          <b>Δ{(diff.summary || {}).changed || 0}</b>
          <span>KEY · {diff.key_column || "row"}</span>
        </div>
        {groups.map(([label, rows, tone]) => rows.length ? (
          <section key={label}>
            <h4>{label}</h4>
            {rows.map((row, index) => (
              <pre className={"rv-diff-card " + tone} key={index}>{JSON.stringify(row, null, 2)}</pre>
            ))}
          </section>
        ) : null)}
        {diff.truncated && <div className="rv-limit">DIFF LIMITED · {diff.row_limit} ROWS</div>}
      </div>
    );
  }
  if (diff.mode === "semantic_text") {
    return (
      <div>
        <div className="rv-diff-summary">
          <b>+{(diff.summary || {}).added || 0}</b>
          <b>−{(diff.summary || {}).removed || 0}</b>
          <span>{shortSha((data.git || {}).from)} → {shortSha((data.git || {}).to)}</span>
        </div>
        <pre className="rv-code rv-diff-lines">{(diff.lines || []).map((line, index) => (
          <span className={line.startsWith("+") ? "add" : line.startsWith("-") ? "del" : line.startsWith("@@") ? "mark" : ""} key={index}>{line + "\n"}</span>
        ))}</pre>
      </div>
    );
  }
  return (
    <div className="rv-binary-diff">
      <strong>{diff.changed ? "BINARY CHANGED" : "IDENTICAL CONTENT"}</strong>
      <span>{compact((diff.summary || {}).before_bytes)} → {compact((diff.summary || {}).after_bytes)}</span>
    </div>
  );
};

const textRangeFor = (root, quote) => {
  if (!root || !quote) return null;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  let textValue = "";
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    nodes.push([node, textValue.length, textValue.length + node.nodeValue.length]);
    textValue += node.nodeValue;
  }
  const start = textValue.indexOf(quote);
  if (start < 0) return null;
  const end = start + quote.length;
  const first = nodes.find(item => item[2] > start);
  const last = [...nodes].reverse().find(item => item[1] < end);
  if (!first || !last) return null;
  const range = document.createRange();
  range.setStart(first[0], Math.max(0, start - first[1]));
  range.setEnd(last[0], Math.min(last[0].nodeValue.length, end - last[1]));
  return range;
};

const capturePaperSelection = (root, onSelect) => {
  const selection = window.getSelection && window.getSelection();
  if (!root || !selection || selection.rangeCount < 1 || selection.isCollapsed) return;
  const range = selection.getRangeAt(0);
  if (!root.contains(range.commonAncestorContainer)) return;
  const quote = selection.toString().trim();
  if (!quote) return;
  const before = document.createRange();
  before.selectNodeContents(root);
  before.setEnd(range.startContainer, range.startOffset);
  const rendered = clean(root.textContent);
  const start = before.toString().length;
  onSelect({
    quote,
    prefix: rendered.slice(Math.max(0, start - 240), start),
    suffix: rendered.slice(start + quote.length, start + quote.length + 240),
    rendered_start: start,
  });
};

const RESEARCH_DOCX_CACHE_LIMIT = 4;
const researchDocxCache = new Map();
const researchDocxCacheKey = contentUrl => researchMemoryKey() + ":docx:" + clean(contentUrl);
const pruneResearchDocxCache = protectedKey => {
  const candidates = [...researchDocxCache.entries()]
    .filter(([key]) => key !== protectedKey)
    .sort((left, right) => Number(left[1].used_at) - Number(right[1].used_at));
  while (researchDocxCache.size > RESEARCH_DOCX_CACHE_LIMIT && candidates.length) {
    researchDocxCache.delete(candidates.shift()[0]);
  }
};
const researchDocxEntry = contentUrl => {
  const key = researchDocxCacheKey(contentUrl);
  let entry = researchDocxCache.get(key);
  if (!entry) {
    entry = { key, content_url: clean(contentUrl), used_at: Date.now(), render_promise: null, rendered: null };
    researchDocxCache.set(key, entry);
  }
  entry.used_at = Date.now();
  pruneResearchDocxCache(key);
  return entry;
};
const renderResearchDocx = entry => {
  if (entry.rendered) return Promise.resolve(entry);
  if (entry.render_promise) return entry.render_promise;
  entry.render_promise = W2.fetch(entry.content_url).then(async response => {
    if (!response.ok) throw await apiError(response);
    if (!window.docx || typeof window.docx.renderAsync !== "function") {
      throw new Error("Word renderer is unavailable");
    }
    const blob = await response.blob();
    const staging = document.createElement("div");
    await window.docx.renderAsync(blob, staging, staging, {
      className: "rv-word",
      inWrapper: true,
      breakPages: true,
      ignoreLastRenderedPageBreak: false,
      renderHeaders: true,
      renderFooters: true,
      renderFootnotes: true,
      renderEndnotes: true,
      renderComments: false,
      renderAltChunks: true,
      experimental: true,
      useBase64URL: true,
    });
    entry.rendered = staging;
    entry.render_promise = null;
    entry.used_at = Date.now();
    return entry;
  }).catch(reason => {
    entry.render_promise = null;
    entry.rendered = null;
    if (researchDocxCache.get(entry.key) === entry) researchDocxCache.delete(entry.key);
    throw reason;
  });
  return entry.render_promise;
};
const adoptResearchDocx = (entry, root) => {
  if (!entry || !entry.rendered || !root) return false;
  root.replaceChildren(...[...entry.rendered.childNodes].map(node => node.cloneNode(true)));
  entry.used_at = Date.now();
  return true;
};

const DocxPaper = ({ contentUrl, title, paperRef, onSelect, onError, onReady }) => {
  const [state, setState] = useState("loading");
  useEffect(() => {
    let alive = true;
    const root = paperRef.current;
    if (!root || !contentUrl) return () => { alive = false; };
    root.replaceChildren();
    setState("loading");
    const entry = researchDocxEntry(contentUrl);
    renderResearchDocx(entry).then(cached => {
      if (!alive || !adoptResearchDocx(cached, root)) return;
      if (alive) {
        setState("ready");
        window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
          if (alive && onReady) onReady();
        }));
      }
    }).catch(reason => {
      if (!alive) return;
      setState("failed");
      onError(clean(reason.message || reason));
    });
    return () => { alive = false; };
  }, [contentUrl]);
  return (
    <div className="rv-paper-stage">
      <div className="rv-paper-status">
        <b>{state === "ready" ? "OPENXML · LIVE TEXT" : state === "failed" ? "RENDER FAILED" : "RENDERING WORD…"}</b>
        <span>{title}</span>
        <small>FORMULA · IMAGE · TABLE · TYPOGRAPHY</small>
      </div>
      <div ref={paperRef} className="rv-docx-paper" role="document"
        onMouseUp={() => capturePaperSelection(paperRef.current, onSelect)}
        onKeyUp={() => capturePaperSelection(paperRef.current, onSelect)}/>
    </div>
  );
};

const SemanticPaper = ({ blocks, paperRef, onSelect }) => (
  <div className="rv-paper-stage">
    <div className="rv-paper-status"><b>STRUCTURED TEXT · LIVE</b><span>VERSION-PINNED READING LAYER</span><small>SELECT ANY CHARACTER RANGE</small></div>
    <article ref={paperRef} className="rv-semantic-paper" role="document"
      onMouseUp={() => capturePaperSelection(paperRef.current, onSelect)}
      onKeyUp={() => capturePaperSelection(paperRef.current, onSelect)}>
      {(blocks || []).map(block => {
        const Tag = block.block_type === "title" ? "h1" : block.block_type === "heading"
          ? "h" + Math.min(6, Math.max(2, Number(block.heading_level) || 2)) : "p";
        return <Tag key={block.id} data-block={block.ordinal}>{block.content}</Tag>;
      })}
    </article>
  </div>
);

const ReviewWorkspace = ({ project, file, preview, canAnnotate, onError }) => {
  const [workspace, setWorkspace] = useState(null);
  const [selection, setSelection] = useState(null);
  const [panel, setPanel] = useState("annotations");
  const [comment, setComment] = useState("");
  const [question, setQuestion] = useState("");
  const [working, setWorking] = useState("");
  const paperRef = useRef(null);
  const readingRef = useRef(null);
  const scrollTimer = useRef(null);
  const commentRef = useRef(null);
  const questionRef = useRef(null);
  const base = project && file
    ? "/api/research/projects/" + encodeURIComponent(project.id) + "/files/" + encodeURIComponent(file.id)
    : "";
  const load = () => {
    if (!base) return Promise.resolve(null);
    return W2.json(base + "/review").then(data => { setWorkspace(data); return data; });
  };
  useEffect(() => {
    let alive = true;
    setWorkspace(null); setSelection(null); setWorking("");
    load().catch(reason => alive && onError(clean(reason.message || reason)));
    return () => { alive = false; };
  }, [base]);
  useEffect(() => {
    const state = workspace && workspace.index && workspace.index.distillation_status;
    if (!["queued", "processing"].includes(state)) return () => {};
    const timer = window.setTimeout(() => load().catch(() => {}), 5000);
    return () => window.clearTimeout(timer);
  }, [base, workspace && workspace.index && workspace.index.distillation_status]);
  const versionMarker = workspace && workspace.version && (
    workspace.version.id || workspace.version.version || workspace.version.git_sha
  );
  useEffect(() => {
    if (!workspace || !readingRef.current || !project || !file) return () => {};
    const element = readingRef.current;
    let frame = window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      restoreResearchReadingPosition(element, project.id, file.id, "review");
    }));
    const save = () => saveResearchReadingPosition(element, project.id, file.id, "review");
    const onScroll = () => {
      if (scrollTimer.current != null) window.clearTimeout(scrollTimer.current);
      scrollTimer.current = window.setTimeout(() => {
        scrollTimer.current = null;
        save();
      }, 180);
    };
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.cancelAnimationFrame(frame);
      element.removeEventListener("scroll", onScroll);
      if (scrollTimer.current != null) window.clearTimeout(scrollTimer.current);
      scrollTimer.current = null;
      save();
    };
  }, [clean(project && project.id), clean(file && file.id), clean(versionMarker)]);

  const focusQuote = quote => {
    const range = textRangeFor(paperRef.current, clean(quote));
    if (!range) return;
    if (window.Highlight && window.CSS && CSS.highlights) {
      CSS.highlights.set("research-review-focus", new Highlight(range));
    } else {
      const selected = window.getSelection();
      selected.removeAllRanges(); selected.addRange(range);
    }
    const node = range.startContainer.parentElement;
    if (node && node.scrollIntoView) node.scrollIntoView({ behavior: "smooth", block: "center" });
  };
  const chooseSelection = anchor => {
    setSelection(anchor);
    if (window.CSS && CSS.highlights) CSS.highlights.delete("research-review-focus");
  };
  const saveAnnotation = async () => {
    if (!selection || !comment.trim() || !canAnnotate) return;
    setWorking("annotation");
    try {
      await W2.post(base + "/annotations", {
        version: (workspace.version || {}).version,
        anchor: selection,
        body: comment.trim(),
      });
      setComment(""); setSelection(null); await load();
    } catch (reason) { onError(clean(reason.message || reason)); }
    finally { setWorking(""); }
  };
  const askAI = async preset => {
    const prompt = clean(preset || question).trim() || (selection
      ? "請解釋選中的文字，說明它在本文論證中的含義、前提與作用。"
      : "請概括這份文件的核心問題、方法、證據與結論。");
    setWorking("ai"); setPanel("ai");
    try {
      await W2.post(base + "/questions", {
        version: (workspace.version || {}).version,
        question: prompt,
        anchor: selection || undefined,
      });
      setQuestion(""); await load();
    } catch (reason) { onError(clean(reason.message || reason)); }
    finally { setWorking(""); }
  };
  const toggleResolved = async annotation => {
    setWorking(clean(annotation.id));
    try {
      await W2.post("/api/research/document-annotations/" + encodeURIComponent(annotation.id) + "/status", {
        resolved: annotation.status !== "resolved",
      });
      await load();
    } catch (reason) { onError(clean(reason.message || reason)); }
    finally { setWorking(""); }
  };
  const reply = async (annotation, body) => {
    if (!body.trim()) return;
    setWorking("reply-" + annotation.id);
    try {
      await W2.post("/api/research/document-annotations/" + encodeURIComponent(annotation.id) + "/messages", { body: body.trim() });
      await load();
    } catch (reason) { onError(clean(reason.message || reason)); }
    finally { setWorking(""); }
  };
  if (!workspace) return <div className="rv-loading block">BUILDING VERSIONED READING INDEX…</div>;
  const index = workspace.index || {};
  const annotations = workspace.annotations || [];
  const questions = workspace.questions || [];
  const isDocx = clean((workspace.version || {}).filename).toLowerCase().endsWith(".docx");
  return (
    <div className="rv-review-workspace">
      <main ref={readingRef} className="rv-review-reading">
        <header className="rv-review-ledger">
          <div><span>VERSION-PINNED PAPER REVIEW</span><strong>V{(workspace.version || {}).version} · {shortSha((workspace.version || {}).git_sha)}</strong></div>
          <div><span>STRUCTURAL INDEX</span><strong>{index.block_count || 0} BLOCKS · {index.character_count || 0} CHARS</strong></div>
          <div><span>CONTEXT DISTILLATION</span><strong className={index.distillation_status === "ready" ? "ok" : ""}>{clean(index.distillation_status || "queued").toUpperCase()}</strong></div>
        </header>
        {selection && (
          <div className="rv-selection-dock">
            <span>SELECTED · {selection.quote.length} CHAR</span>
            <q>{selection.quote.slice(0, 220)}</q>
            <button onClick={() => { setPanel("annotations"); window.setTimeout(() => commentRef.current && commentRef.current.focus(), 0); }}>加批注</button>
            <button className="ai" onClick={() => askAI()}>問 AI</button>
            <button className="clear" onClick={() => setSelection(null)}>×</button>
          </div>
        )}
        {isDocx ? (
          <DocxPaper contentUrl={preview && preview.content_url} title={file.logical_path}
            paperRef={paperRef} onSelect={chooseSelection} onError={onError}
            onReady={() => restoreResearchReadingPosition(readingRef.current, project.id, file.id, "review")}/>
        ) : (
          <SemanticPaper blocks={workspace.blocks} paperRef={paperRef} onSelect={chooseSelection}/>
        )}
      </main>
      <aside className="rv-review-inspector">
        <nav>
          <button className={panel === "annotations" ? "active" : ""} onClick={() => setPanel("annotations")}>
            批注 <b>{annotations.filter(item => item.status === "open").length}</b>
          </button>
          <button className={panel === "ai" ? "active" : ""} onClick={() => setPanel("ai")}>
            ASK AI <b>{questions.length}</b>
          </button>
        </nav>
        {panel === "annotations" && <div className="rv-review-panel">
          <header><span>PERSONAL / PEER NOTES</span><small>批注固定於本文件版本與字符範圍</small></header>
          <div className="rv-note-composer">
            <blockquote>{selection ? selection.quote : "先在左側論文中選中任意文字。"}</blockquote>
            <textarea ref={commentRef} value={comment} disabled={!selection || !canAnnotate}
              onChange={event => setComment(event.target.value)} placeholder="寫下判斷、問題、修改意見或審閱結論…"/>
            <button disabled={!selection || !comment.trim() || working === "annotation" || !canAnnotate}
              onClick={saveAnnotation}>{working === "annotation" ? "SAVING…" : "保存版本化批注"}</button>
          </div>
          <div className="rv-annotation-list">
            {!annotations.length && <EmptyPanel title="尚無批注" copy="選中一個字、一句話或跨段內容後加入第一條批注。"/>}
            {annotations.map((item, index) => <AnnotationCard key={item.id} item={item} index={index}
              busy={working} onFocus={focusQuote} onToggle={toggleResolved} onReply={reply}/>) }
          </div>
        </div>}
        {panel === "ai" && <div className="rv-review-panel ai">
          <header><span>GROUNDED RESEARCH AI</span><small>每個答案回指版本固定的段落與字符位置</small></header>
          <div className="rv-ai-index-card">
            <b>{index.distillation_status === "ready" ? "CONTEXT READY" : "DISTILLING CONTEXT"}</b>
            <strong>{(index.concepts || []).length} CONCEPTS · {index.block_count || 0} BLOCKS</strong>
            <p>{index.summary || "結構索引已可查詢；AI 正在後台蒸餾概念、別名與論證位置。"}</p>
          </div>
          {selection && <button className="rv-ai-selection" onClick={() => askAI()}>
            <span>ASK ABOUT SELECTION</span><q>{selection.quote.slice(0, 180)}</q><b>↗</b>
          </button>}
          <div className="rv-ai-composer">
            <textarea ref={questionRef} value={question} onChange={event => setQuestion(event.target.value)}
              placeholder="問一個概念、公式、方法、論證或任意問題…"
              onKeyDown={event => { if ((event.metaKey || event.ctrlKey) && event.key === "Enter") askAI(); }}/>
            <button disabled={working === "ai"} onClick={() => askAI()}>{working === "ai" ? "READING INDEX…" : "提問 · ⌘ ENTER"}</button>
          </div>
          <div className="rv-question-list">
            {!questions.length && <EmptyPanel title="等待第一個問題" copy="可先選中文字直接提問，也可不選文字詢問整份論文。"/>}
            {questions.map(item => <article key={item.id}>
              <header><span>Q · {stamp(item.created_at)}</span><small>{item.model || "RESEARCH AI"}</small></header>
              {item.selection_anchor && <q>{clean(item.selection_anchor.quote).slice(0, 200)}</q>}
              <h4>{item.question}</h4><p>{item.answer}</p>
              <div>{(item.citations || []).map((citation, index) => (
                <button key={index} onClick={() => focusQuote(citation.quote)}>
                  <b>{citation.block}</b><span>{(citation.heading_path || []).join(" / ") || "ROOT"}</span>
                  <q>{citation.quote}</q>
                </button>
              ))}</div>
            </article>)}
          </div>
        </div>}
      </aside>
    </div>
  );
};

const AnnotationCard = ({ item, index, busy, onFocus, onToggle, onReply }) => {
  const [replyBody, setReplyBody] = useState("");
  return (
    <article className={"rv-annotation " + item.status}>
      <header><b>{String(index + 1).padStart(2, "0")}</b><span>{item.author_name || "RESEARCHER"} · {stamp(item.created_at)}</span><small>{item.status.toUpperCase()}</small></header>
      <button className="rv-anchor-quote" onClick={() => onFocus(item.quote)}><q>{item.quote}</q><span>定位原文 ↗</span></button>
      <p>{item.body}</p>
      {(item.messages || []).map(message => <div className="rv-note-reply" key={message.id}><b>{message.author_name || message.message_kind}</b><p>{message.body}</p></div>)}
      <footer>
        <input value={replyBody} onChange={event => setReplyBody(event.target.value)} placeholder="回覆這條批注…"
          onKeyDown={event => { if (event.key === "Enter" && replyBody.trim()) { onReply(item, replyBody); setReplyBody(""); } }}/>
        <button disabled={busy === item.id} onClick={() => onToggle(item)}>{item.status === "resolved" ? "重新開啟" : "標記完成"}</button>
      </footer>
    </article>
  );
};

const Viewer = ({ project, file, preview, diff, tab, onTab, blobUrl, busy, canAnnotate, onError }) => {
  const canvasRef = useRef(null);
  const scrollTimer = useRef(null);
  const versionMarker = preview && preview.version && (
    preview.version.id || preview.version.version || preview.version.git_sha
  );
  useEffect(() => {
    if (!project || !file || busy || tab === "review" || !canvasRef.current) return () => {};
    const element = canvasRef.current;
    const frame = window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      restoreResearchReadingPosition(element, project.id, file.id, tab);
    }));
    const save = () => saveResearchReadingPosition(element, project.id, file.id, tab);
    const onScroll = () => {
      if (scrollTimer.current != null) window.clearTimeout(scrollTimer.current);
      scrollTimer.current = window.setTimeout(() => {
        scrollTimer.current = null;
        save();
      }, 180);
    };
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.cancelAnimationFrame(frame);
      element.removeEventListener("scroll", onScroll);
      if (scrollTimer.current != null) window.clearTimeout(scrollTimer.current);
      scrollTimer.current = null;
      save();
    };
  }, [clean(project && project.id), clean(file && file.id), tab, busy, clean(versionMarker)]);
  if (!file) return busy
    ? <div className="rv-loading block">READING RESEARCH INDEX…</div>
    : <EmptyPanel title="選擇一份科研文件" copy="文件、版本與 Git 提交會在同一閱讀面板中保持同步。"/>;
  const version = preview && preview.version;
  const mode = preview && preview.mode;
  const html = preview && preview.html && window.DOMPurify
    ? window.DOMPurify.sanitize(preview.html, { WHOLE_DOCUMENT: true })
    : clean(preview && preview.html);
  return (
    <div className="rv-viewer">
      <div className="rv-viewer-head">
        <div>
          <span>{kindName[file.file_kind] || clean(file.file_kind).toUpperCase()}</span>
          <h3>{file.logical_path}</h3>
          <small>v{(version || {}).version || file.current_version} · {shortSha((version || {}).git_sha || file.git_sha)} · {compact((version || {}).size_bytes || file.size_bytes)}</small>
        </div>
        <a className="rv-inline-link" href={preview && preview.content_url || "#"} target="_blank" rel="noreferrer">原文 ↗</a>
      </div>
      <nav className="rv-tabs">
        <button className={tab === "review" ? "active" : ""} onClick={() => onTab("review")}>REVIEW / 批注與 AI</button>
        <button className={tab === "preview" ? "active" : ""} onClick={() => onTab("preview")}>PREVIEW / 閱覽</button>
        <button className={tab === "diff" ? "active" : ""} onClick={() => onTab("diff")}>DIFF / 差異</button>
        <button className={tab === "versions" ? "active" : ""} onClick={() => onTab("versions")}>VERSIONS / 版本</button>
      </nav>
      <div ref={canvasRef} className="rv-canvas">
        {busy && <div className="rv-loading">READING OBJECT…</div>}
        {!busy && tab === "review" && (
          <ReviewWorkspace project={project} file={file} preview={preview}
            canAnnotate={canAnnotate} onError={onError}/>
        )}
        {!busy && tab === "diff" && <DiffPreview data={diff}/>}
        {!busy && tab === "versions" && (
          <div className="rv-version-list">
            {(file.versions || []).map(item => (
              <article key={item.id}>
                <b>V{item.version}</b>
                <div><strong>{item.commit_message || "Update research object"}</strong><small>{stamp(item.created_at)}</small></div>
                <code>{shortSha(item.git_sha)} · {compact(item.size_bytes)}</code>
              </article>
            ))}
          </div>
        )}
        {!busy && tab === "preview" && mode === "dataset" && <DatasetPreview table={preview.table}/>}
        {!busy && tab === "preview" && mode === "html" && (
          <iframe className="rv-html" title={file.display_name} sandbox="" srcDoc={html}/>
        )}
        {!busy && tab === "preview" && mode === "pdf" && blobUrl && (
          <iframe className="rv-pdf" title={file.display_name} src={blobUrl}/>
        )}
        {!busy && tab === "preview" && mode === "image" && blobUrl && (
          <div className="rv-image"><img src={blobUrl} alt={file.display_name}/></div>
        )}
        {!busy && tab === "preview" && mode === "database" && (
          <DatabasePreview metadata={preview.metadata} schema={preview.text}/>
        )}
        {!busy && tab === "preview" && ["document", "code", "notebook"].includes(mode) && (
          <TextPreview text={preview.text}/>
        )}
        {!busy && tab === "preview" && mode === "binary" && (
          <EmptyPanel title="二進制對象已托管" copy="此格式暫無內嵌渲染器，但仍具有完整 Git 版本、校驗值與下載能力。"/>
        )}
      </div>
    </div>
  );
};

const Page = () => {
  const [section, setSection] = useState(() => {
    try {
      const saved = sessionStorage.getItem("w2_research_tab");
      const remembered = readResearchMemory().section;
      return RESEARCH_TABS.some(item => item[0] === saved) ? saved
        : RESEARCH_TABS.some(item => item[0] === remembered) ? remembered : "overview";
    } catch (_error) { return "overview"; }
  });
  const [projectsMounted, setProjectsMounted] = useState(() => section === "projects");
  const [projects, setProjects] = useState([]);
  const [projectId, setProjectId] = useState("");
  const [detail, setDetail] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [executionDetail, setExecutionDetail] = useState(null);
  const [fileId, setFileId] = useState("");
  const [assetFilter, setAssetFilter] = useState("all");
  const [preview, setPreview] = useState(null);
  const [diff, setDiff] = useState(null);
  const [tab, setTab] = useState("review");
  const [busy, setBusy] = useState(true);
  const [detailBusy, setDetailBusy] = useState(false);
  const [viewerBusy, setViewerBusy] = useState(false);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [mutating, setMutating] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [blobUrl, setBlobUrl] = useState("");
  const [executionPinMode, setExecutionPinMode] = useState("all");
  const [executionInputIds, setExecutionInputIds] = useState([]);
  const [executionInputFilter, setExecutionInputFilter] = useState("");
  const [executionEntrypoint, setExecutionEntrypoint] = useState("");
  const fileInput = useRef(null);
  const detailRequestSerial = useRef(0);

  const canWrite = W2.hasPermission("research.write");
  const canReview = W2.hasPermission("research.review");
  const selectedProject = projects.find(item => clean(item.id) === clean(projectId)) || null;
  const selectedFile = detail && (detail.files || []).find(item => clean(item.id) === clean(fileId)) || null;
  const totals = useMemo(() => projects.reduce((sum, item) => ({
    files: sum.files + (Number(item.file_count) || 0),
    versions: sum.versions + (Number(item.version_count) || 0),
    commits: sum.commits + (Number(item.commit_count) || 0),
    bytes: sum.bytes + (Number(item.stored_bytes) || 0),
  }), { files: 0, versions: 0, commits: 0, bytes: 0 }), [projects]);
  const sectionMeta = {
    overview: ["R01", "RESEARCH VAULT", "科研總覽", "研究不是文件堆積，而是一條可閱讀、可比較、可重現的證據鏈。"],
    guide: ["R02", "RESEARCH COMPASS", "論文導引", "把一個模糊想法推進為可提交論文：每一步都有產出、完成條件與下一個動作。"],
    projects: ["R03", "PROJECT LIBRARY", "課題庫", "每個課題都是獨立 Git 空間；文件、數據、代碼與提交保持同步。"],
    workflow: ["R04", "RESEARCH OPERATING MODEL", "研究流程", "把研究問題、資料治理、協議與每一次 Run 連成可執行的工作流。"],
    evidence: ["R05", "CLAIM — EVIDENCE", "證據與覆核", "每項主張都必須指向精確資料版本或 Run，經覆核後才進入研究發布。"],
    execution: ["R06", "REPRODUCIBLE COMPUTE", "重現運算", "把固定文件版本送進受控計算環境，讓日誌、產物與結果雜湊回到證據鏈。"],
    revisions: ["R07", "REVISION LINEAGE", "版本譜系", "沿提交時間線閱讀研究推進，定位每一次論證與數據變更。"],
    formats: ["R08", "FORMAT CAPABILITIES", "格式能力", "同一托管邊界內直接閱覽異構科研材料，並按格式選擇差異策略。"],
  }[section];
  const sectionCounts = {
    overview: projects.length,
    guide: selectedProject ? "09" : "—",
    projects: totals.files,
    workflow: workflow ? (workflow.stats.protocols + workflow.stats.runs) : 0,
    evidence: workflow ? workflow.stats.claims : 0,
    execution: workflow ? workflow.stats.executions : 0,
    revisions: totals.commits,
    formats: FORMAT_ROWS.length,
  };
  const selectSection = next => {
    setSection(next);
    if (next === "projects") setProjectsMounted(true);
    try { sessionStorage.setItem("w2_research_tab", next); } catch (_error) {}
    rememberResearchSelection({ projectId, fileId, tab, section: next });
  };
  const selectProject = id => {
    setProjectId(id);
    setDetail(null);
    setWorkflow(null);
    setFileId("");
    setDetailBusy(Boolean(id));
    setAssetFilter("all");
    setTab("review");
    rememberResearchSelection({ projectId: id, section });
  };

  const loadProjects = async preferred => {
    const data = await W2.json("/api/research/projects");
    const next = Array.isArray(data.projects) ? data.projects : [];
    setProjects(next);
    setProjectId(current => {
      const available = candidate => next.some(item => clean(item.id) === clean(candidate));
      const selected = [preferred, current, rememberedResearchProject(), (next[0] || {}).id]
        .map(clean).find(available) || "";
      if (selected) rememberResearchSelection({ projectId: selected, section });
      return selected;
    });
    return next;
  };
  const loadDetail = async id => {
    const request = ++detailRequestSerial.current;
    if (!id) { setDetail(null); setFileId(""); setDetailBusy(false); return null; }
    setDetailBusy(true);
    try {
      const data = await W2.json("/api/research/projects/" + encodeURIComponent(id));
      if (request !== detailRequestSerial.current) return null;
      setDetail(data);
      const files = Array.isArray(data.files) ? data.files : [];
      setFileId(current => {
        const available = candidate => files.some(item => clean(item.id) === clean(candidate));
        const selected = [current, rememberedResearchFile(id), (files[0] || {}).id]
          .map(clean).find(available) || "";
        const file = files.find(item => clean(item.id) === selected);
        const fallbackTab = file && ["document", "pdf"].includes(file.file_kind) ? "review" : "preview";
        const nextTab = rememberedResearchTab(id, selected, fallbackTab);
        setTab(nextTab);
        if (selected) rememberResearchSelection({ projectId: id, fileId: selected, tab: nextTab, section });
        return selected;
      });
      return data;
    } finally {
      if (request === detailRequestSerial.current) setDetailBusy(false);
    }
  };
  const loadWorkflow = async id => {
    if (!id) { setWorkflow(null); return; }
    setWorkflowBusy(true);
    try {
      setWorkflow(await W2.json("/api/research/projects/" + encodeURIComponent(id) + "/workflow"));
    } finally {
      setWorkflowBusy(false);
    }
  };
  const loadExecution = async (id, executionId) => {
    if (!id || !executionId) { setExecutionDetail(null); return null; }
    const data = await W2.json("/api/research/projects/" + encodeURIComponent(id) +
      "/executions/" + encodeURIComponent(executionId));
    setExecutionDetail(data);
    return data;
  };

  useEffect(() => {
    let alive = true;
    setBusy(true);
    loadProjects().catch(reason => alive && setError(clean(reason.message || reason)))
      .finally(() => alive && setBusy(false));
    return () => { alive = false; };
  }, []);
  useEffect(() => {
    let alive = true;
    setError("");
    loadDetail(projectId).catch(reason => alive && setError(clean(reason.message || reason)));
    loadWorkflow(projectId).catch(reason => alive && setError(clean(reason.message || reason)));
    return () => { alive = false; detailRequestSerial.current += 1; };
  }, [projectId]);
  useEffect(() => {
    if (projectId && fileId) {
      rememberResearchSelection({ projectId, fileId, tab, section });
    }
  }, [projectId, fileId, tab]);
  useEffect(() => {
    if (section !== "execution" || !projectId || !workflow) return () => {};
    const active = (workflow.executions || []).some(item =>
      ["queued", "preparing", "running"].includes(item.status));
    if (!active) return () => {};
    const timer = window.setInterval(() => {
      loadWorkflow(projectId).catch(reason => setError(clean(reason.message || reason)));
      const current = executionDetail && executionDetail.execution;
      if (current && ["queued", "preparing", "running"].includes(current.status)) {
        loadExecution(projectId, current.id).catch(reason => setError(clean(reason.message || reason)));
      }
    }, 3000);
    return () => window.clearInterval(timer);
  }, [section, projectId, workflow && workflow.stats.running_executions,
    executionDetail && executionDetail.execution && executionDetail.execution.id]);
  useEffect(() => {
    let alive = true;
    if (!projectId || !fileId) { setPreview(null); setDiff(null); return () => {}; }
    setViewerBusy(true);
    const base = "/api/research/projects/" + encodeURIComponent(projectId) + "/files/" + encodeURIComponent(fileId);
    Promise.all([
      W2.json(base + "/preview"),
      W2.json(base + "/diff").catch(() => ({ available: false })),
    ]).then(([nextPreview, nextDiff]) => {
      if (!alive) return;
      setPreview(nextPreview);
      setDiff(nextDiff);
    }).catch(reason => alive && setError(clean(reason.message || reason)))
      .finally(() => alive && setViewerBusy(false));
    return () => { alive = false; };
  }, [projectId, fileId]);
  useEffect(() => {
    let alive = true;
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    setBlobUrl("");
    if (!preview || !["pdf", "image"].includes(preview.mode) || !preview.content_url) return () => { alive = false; };
    W2.fetch(preview.content_url).then(async response => {
      if (!response.ok) throw await apiError(response);
      const url = URL.createObjectURL(await response.blob());
      if (!alive) { URL.revokeObjectURL(url); return; }
      setBlobUrl(url);
    }).catch(reason => alive && setError(clean(reason.message || reason)));
    return () => { alive = false; };
  }, [preview && preview.content_url]);
  useEffect(() => () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }, [blobUrl]);

  const createProject = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setCreating(true); setError("");
    try {
      const result = await W2.post("/api/research/projects", {
        title: clean(form.get("title")).trim(),
        research_area: clean(form.get("research_area")).trim(),
        summary: clean(form.get("summary")).trim(),
      });
      const id = clean((result.project || {}).id);
      await loadProjects(id);
      setShowCreate(false);
      event.currentTarget.reset();
    } catch (reason) { setError(clean(reason.message || reason)); }
    finally { setCreating(false); }
  };
  const uploadFile = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    if (!form.get("file") || !projectId) return;
    setUploading(true); setError("");
    try {
      const response = await W2.fetch(
        "/api/research/projects/" + encodeURIComponent(projectId) + "/files",
        { method: "POST", body: form },
      );
      if (!response.ok) throw await apiError(response);
      const result = await response.json();
      await loadProjects(projectId);
      await loadDetail(projectId);
      setFileId(clean((result.file || {}).id));
      setAssetFilter(clean((result.file || {}).asset_class) || "all");
      setTab(clean((result.file || {}).file_kind) === "document" ? "review" : "preview");
      event.currentTarget.reset();
    } catch (reason) { setError(clean(reason.message || reason)); }
    finally { setUploading(false); }
  };
  const workflowMutation = async (name, path, method, payload) => {
    if (!projectId) return null;
    setMutating(name); setError("");
    try {
      const data = await W2.json(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      });
      await loadWorkflow(projectId);
      return data;
    } catch (reason) {
      setError(clean(reason.message || reason));
      return null;
    } finally {
      setMutating("");
    }
  };
  const saveDmpForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const content = {};
    ["research_question", "hypothesis", "data_collection", "ethics_legal_security",
      "storage_preservation", "sharing_reuse", "responsibilities"].forEach(key => {
      content[key] = clean(form.get(key)).trim();
    });
    await workflowMutation("dmp",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/dmp", "PUT", { content });
  };
  const createProtocolForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await workflowMutation("protocol",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/protocols", "POST", {
        title: clean(form.get("title")).trim(),
        objective: clean(form.get("objective")).trim(),
        specification: { procedure: clean(form.get("procedure")).trim() },
      });
    if (result) event.currentTarget.reset();
  };
  const createRunForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await workflowMutation("run",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/runs", "POST", {
        title: clean(form.get("title")).trim(),
        protocol_id: clean(form.get("protocol_id")).trim() || null,
        inputs: { description: clean(form.get("inputs")).trim() },
        environment: { description: clean(form.get("environment")).trim() },
      });
    if (result) event.currentTarget.reset();
  };
  const completeRun = run => workflowMutation("run-" + run.id,
    "/api/research/projects/" + encodeURIComponent(projectId) + "/runs/" + encodeURIComponent(run.id),
    "PATCH", { status: "completed" });
  const createClaimForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await workflowMutation("claim",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/claims", "POST", {
        statement: clean(form.get("statement")).trim(),
        confidence: clean(form.get("confidence")).trim() || null,
      });
    if (result) event.currentTarget.reset();
  };
  const linkEvidenceForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const source = clean(form.get("source"));
    const separator = source.indexOf(":");
    if (separator < 1) return;
    const sourceType = source.slice(0, separator);
    const sourceId = source.slice(separator + 1);
    const claimId = clean(form.get("claim_id"));
    const payload = {
      relation: clean(form.get("relation")) || "supports",
      note: clean(form.get("note")).trim(),
    };
    payload[sourceType === "run" ? "run_id" : "file_version_id"] = sourceId;
    const result = await workflowMutation("evidence",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/claims/" +
        encodeURIComponent(claimId) + "/evidence", "POST", payload);
    if (result) event.currentTarget.reset();
  };
  const submitReviewForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const target = clean(form.get("target"));
    const separator = target.indexOf(":");
    if (separator < 1) return;
    const result = await workflowMutation("review",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/reviews", "POST", {
        target_type: target.slice(0, separator),
        target_id: target.slice(separator + 1),
        decision: clean(form.get("decision")),
        comment: clean(form.get("comment")).trim(),
      });
    if (result) event.currentTarget.reset();
  };
  const reproduce = () => workflowMutation("reproduce",
    "/api/research/projects/" + encodeURIComponent(projectId) + "/reproducibility-checks",
    "POST", {});
  const createReleaseForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const result = await workflowMutation("release",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/releases", "POST", {
        title: clean(form.get("title")).trim(),
        access_level: clean(form.get("access_level")) || "restricted",
        license: clean(form.get("license")).trim(),
      });
    if (result) event.currentTarget.reset();
  };
  const executionMutation = async (name, path, payload) => {
    setMutating(name); setError("");
    try {
      const result = await W2.json(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      });
      await loadWorkflow(projectId);
      const executionId = clean((result.execution || {}).id) ||
        clean(executionDetail && executionDetail.execution && executionDetail.execution.id);
      if (executionId) await loadExecution(projectId, executionId);
      return result;
    } catch (reason) {
      setError(clean(reason.message || reason));
      return null;
    } finally { setMutating(""); }
  };
  const submitExecutionForm = async event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    let argumentsValue = [];
    try {
      argumentsValue = JSON.parse(clean(form.get("arguments")).trim() || "[]");
      if (!Array.isArray(argumentsValue)) throw new Error("參數必須是 JSON 陣列");
    } catch (reason) {
      setError("執行參數格式錯誤：" + clean(reason.message || reason));
      return;
    }
    const entrypoint = clean(form.get("entrypoint"));
    const payload = {
      title: clean(form.get("title")).trim(),
      runtime: "python-3.13",
      entrypoint,
      arguments: argumentsValue,
      run_id: clean(form.get("run_id")) || null,
      resource_limits: {
        timeout_seconds: Number(form.get("timeout_seconds")) || 300,
        memory_mb: Number(form.get("memory_mb")) || 1024,
      },
    };
    if (executionPinMode === "custom") {
      const entrypointFile = ((detail && detail.files) || []).find(item =>
        clean(item.logical_path) === entrypoint);
      const entrypointVersionId = clean(entrypointFile && entrypointFile.versions &&
        entrypointFile.versions[0] && entrypointFile.versions[0].id);
      payload.input_file_version_ids = Array.from(new Set([
        ...executionInputIds,
        ...(entrypointVersionId ? [entrypointVersionId] : []),
      ]));
    }
    const result = await executionMutation("execution-submit",
      "/api/research/projects/" + encodeURIComponent(projectId) + "/executions", payload);
    if (result) event.currentTarget.reset();
  };
  const cancelExecution = item => executionMutation("execution-cancel",
    "/api/research/projects/" + encodeURIComponent(projectId) + "/executions/" +
      encodeURIComponent(item.id) + "/cancel", {});
  const retryExecution = item => executionMutation("execution-retry",
    "/api/research/projects/" + encodeURIComponent(projectId) + "/executions/" +
      encodeURIComponent(item.id) + "/retry", {});
  const promoteArtifact = async artifact => {
    const item = executionDetail && executionDetail.execution;
    if (!item) return;
    const result = await executionMutation("artifact-" + artifact.id,
      "/api/research/projects/" + encodeURIComponent(projectId) + "/executions/" +
      encodeURIComponent(item.id) + "/artifacts/" + encodeURIComponent(artifact.id) +
      "/promote", {});
    if (result) await loadDetail(projectId);
  };
  const openArtifact = async artifact => {
    const item = executionDetail && executionDetail.execution;
    if (!item) return;
    setError("");
    try {
      const response = await W2.fetch("/api/research/projects/" + encodeURIComponent(projectId) +
        "/executions/" + encodeURIComponent(item.id) + "/artifacts/" +
        encodeURIComponent(artifact.id) + "/content");
      if (!response.ok) throw await apiError(response);
      const url = URL.createObjectURL(await response.blob());
      window.open(url, "_blank", "noopener");
      window.setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (reason) { setError(clean(reason.message || reason)); }
  };
  const workflowStats = workflow && workflow.stats || {
    dmp_version: 0, protocols: 0, locked_protocols: 0, runs: 0,
    completed_runs: 0, claims: 0, accepted_claims: 0, evidence_links: 0,
    reviews: 0, reproduction_status: "not_checked", releases: 0,
    executions: 0, successful_executions: 0, running_executions: 0,
  };
  const codeFiles = ((detail && detail.files) || []).filter(item =>
    clean(item.logical_path).toLowerCase().endsWith(".py"));
  const dmpContent = workflow && workflow.dmp && workflow.dmp.content || {};
  const evidenceSources = [
    ...((workflow && workflow.runs) || []).map(item => ({
      value: "run:" + item.id,
      label: item.run_code + " · " + item.title,
    })),
    ...((detail && detail.files) || []).filter(item => (item.versions || []).length).map(item => ({
      value: "file_version:" + item.versions[0].id,
      label: "V" + item.versions[0].version + " · " + item.logical_path,
    })),
  ];
  const reviewTargets = [
    ...(workflow && workflow.dmp ? [{
      value: "dmp:" + workflow.dmp.id,
      label: "DMP v" + workflow.dmp.version,
    }] : []),
    ...((workflow && workflow.protocols) || []).map(item => ({
      value: "protocol:" + item.id,
      label: item.protocol_code + " · " + item.title,
    })),
    ...((workflow && workflow.claims) || []).map(item => ({
      value: "claim:" + item.id,
      label: item.claim_code + " · " + item.statement,
    })),
  ];
  const researchFiles = (detail && detail.files) || [];
  const assetCounts = researchFiles.reduce((counts, file) => {
    const key = assetClassOf(file);
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});
  const visibleResearchFiles = assetFilter === "all" ? researchFiles :
    researchFiles.filter(file => assetClassOf(file) === assetFilter);
  const selectAssetFilter = key => {
    setAssetFilter(key);
    const visible = key === "all" ? researchFiles :
      researchFiles.filter(file => assetClassOf(file) === key);
    if (!visible.some(file => clean(file.id) === clean(fileId)) && visible.length) {
      const next = visible[0];
      setFileId(clean(next.id));
      setTab(next.file_kind === "document" || next.file_kind === "pdf" ? "review" : "preview");
    }
  };
  const currentInput = file => {
    const versions = Array.isArray(file.versions) ? file.versions : [];
    const version = versions.find(item => Number(item.version) === Number(file.current_version)) || versions[0];
    return version ? {
      id: clean(version.id),
      logical_path: clean(file.logical_path),
      version: Number(version.version) || Number(file.current_version) || 1,
      size_bytes: Number(version.size_bytes) || Number(file.size_bytes) || 0,
      file_kind: clean(file.file_kind),
    } : null;
  };
  const allExecutionInputs = researchFiles.map(currentInput).filter(Boolean);
  const executionInputSignature = allExecutionInputs.map(item => item.id).join("|");
  useEffect(() => {
    setExecutionPinMode("all");
    setExecutionInputIds(allExecutionInputs.map(item => item.id));
    setExecutionInputFilter("");
    setExecutionEntrypoint(current => codeFiles.some(item => item.logical_path === current)
      ? current : clean((codeFiles[0] || {}).logical_path));
  }, [projectId, executionInputSignature]);
  const chooseExecutionEntrypoint = value => {
    setExecutionEntrypoint(value);
    const input = allExecutionInputs.find(item => item.logical_path === value);
    if (input) setExecutionInputIds(current => current.includes(input.id) ? current : [...current, input.id]);
  };
  const toggleExecutionInput = input => {
    if (input.logical_path === executionEntrypoint) return;
    setExecutionInputIds(current => current.includes(input.id)
      ? current.filter(id => id !== input.id) : [...current, input.id]);
  };
  const visibleExecutionInputs = allExecutionInputs.filter(item =>
    !executionInputFilter || item.logical_path.toLowerCase().includes(executionInputFilter.toLowerCase()));
  const pinnedExecutionInputs = executionPinMode === "all" ? allExecutionInputs :
    allExecutionInputs.filter(item => executionInputIds.includes(item.id) || item.logical_path === executionEntrypoint);
  const pinnedExecutionBytes = pinnedExecutionInputs.reduce((sum, item) => sum + item.size_bytes, 0);
  const hasPath = terms => researchFiles.some(item => {
    const path = clean(item.logical_path).toLowerCase();
    return terms.some(term => path.includes(term));
  });
  const journey = [
    { no: "01", key: "frame", title: "FRAME THE QUESTION", zh: "界定問題", output: "研究問題 · 可證偽假設 · 邊界", section: "workflow", tool: "research_dmp_update", command: "research dmp update", write: true,
      complete: Boolean(dmpContent.research_question && dmpContent.hypothesis) },
    { no: "02", key: "map", title: "MAP THE FIELD", zh: "建立文獻地圖", output: "來源庫 · 爭論矩陣 · 研究缺口", section: "projects", tool: "research_upload_contract", command: "research upload contract", write: true,
      complete: hasPath(["literature", "reference", "bibliograph", "sources/"]) },
    { no: "03", key: "design", title: "DESIGN THE METHOD", zh: "設計方法", output: "方法協議 · 變量 · 判定標準", section: "workflow", tool: "research_protocol_create", command: "research protocol create", write: true,
      complete: workflowStats.locked_protocols > 0 },
    { no: "04", key: "build", title: "BUILD THE MATERIAL", zh: "整理資料", output: "資料字典 · 來源 · 清理規則", section: "projects", tool: "research_upload_contract", command: "research upload contract", write: true,
      complete: researchFiles.some(item => ["dataset", "database"].includes(item.file_kind)) },
    { no: "05", key: "analyse", title: "ANALYSE", zh: "分析與重現", output: "固定輸入 · 日誌 · 結果產物", section: "execution", tool: "research_execution_submit", command: "research execution submit", write: true,
      complete: workflowStats.successful_executions > 0 || workflowStats.completed_runs > 0 || hasPath(["results/", "output/"]) },
    { no: "06", key: "write", title: "WRITE THE ARGUMENT", zh: "寫作與修訂", output: "主稿 · 章節 · 圖表 · 引用", section: "projects", tool: "research_project_show", command: "research project show",
      complete: hasPath(["manuscript/", "dissertation", "paper/", "thesis/"]) },
    { no: "07", key: "argue", title: "LINK CLAIMS", zh: "連結主張與證據", output: "主張 · 證據版本 · 限制", section: "evidence", tool: "research_claim_create", command: "research claim create", write: true,
      complete: workflowStats.claims > 0 && workflowStats.evidence_links > 0 },
    { no: "08", key: "review", title: "CHALLENGE IT", zh: "同行覆核", output: "評論 · 修改要求 · 決定", section: "evidence", tool: "research_review_submit", command: "research review submit", review: true,
      complete: workflowStats.reviews > 0 },
    { no: "09", key: "release", title: "RELEASE", zh: "重現與發布", output: "通過清單 · RO-Crate · 版本", section: "evidence", tool: "research_release_create", command: "research release create", review: true,
      complete: workflowStats.releases > 0 },
  ];
  const journeyComplete = journey.filter(item => item.complete).length;
  const nextJourney = journey.find(item => !item.complete) || journey[journey.length - 1];
  const paperSpine = [
    ["01", "ABSTRACT", "問題 → 方法 → 核心結果 → 貢獻；最後寫，最先讀。"],
    ["02", "INTRODUCTION", "背景 → 缺口 → 問題 → 主張 → 貢獻 → 文章路線。"],
    ["03", "LITERATURE", "不是作者名單；把學術爭論分組，精確定位缺口。"],
    ["04", "METHODS", "讓另一位研究者僅依此節即可重做同一研究。"],
    ["05", "RESULTS", "先報告觀察與不確定性，不把討論偷渡進結果。"],
    ["06", "DISCUSSION", "解釋機制、比較文獻、處理替代解釋與限制。"],
    ["07", "CONCLUSION", "直接回答研究問題，界定可推廣範圍與下一步。"],
  ];

  return (
    <div className="rv-page" data-testid="research-vault">
      <Folio no={sectionMeta[0]} en={sectionMeta[1]} title={sectionMeta[2]}
        sub={sectionMeta[3]}
        right={<div className="rv-head-actions">
          <span className="rv-live"><i/>POSTGRESQL + GIT</span>
          <button className="btn" data-command="research project list"
            onClick={() => W2.openBusinessAction("research_project_list")}>指令中心</button>
          {canWrite && <button className="btn primary" onClick={() => {
            selectSection("projects");
            setShowCreate(value => !value);
          }}>＋ 新建課題</button>}
        </div>}/>

      <nav className="subnav rise rv-subnav" aria-label="科研子頁">
        {RESEARCH_TABS.map(([key, label], index) => (
          <button type="button" key={key} className={section === key ? "on" : ""}
            data-testid={"research-tab-" + key} onClick={() => selectSection(key)}>
            <span className="sn-no">{String(index + 1).padStart(2, "0")}</span>
            {label}
            <span className="sn-count">{sectionCounts[key]}</span>
          </button>
        ))}
      </nav>

      {error && <div className="rv-error" role="alert"><b>SYSTEM NOTE</b>{error}<button onClick={() => setError("")}>×</button></div>}
      {showCreate && (
        <form className="rv-create" onSubmit={createProject}>
          <label><span>PROJECT TITLE</span><input name="title" required placeholder="例如：丙二酸反應動力學"/></label>
          <label><span>RESEARCH AREA</span><input name="research_area" placeholder="CHEMISTRY / COMPUTATION"/></label>
          <label className="wide"><span>ABSTRACT NOTE</span><input name="summary" placeholder="一句話界定課題問題與研究邊界"/></label>
          <button className="btn primary" disabled={creating}>{creating ? "CREATING…" : "建立 Git 課題"}</button>
        </form>
      )}

      {section === "overview" && <>
        <section className="rv-poster-grid" aria-label="科研數據海報">
          <article className="rv-poster rv-poster-main">
            <span className="rv-poster-index">RESEARCH / 01—04</span>
            <p>VERSIONED<br/>ARGUMENTS</p>
            <strong>{String(projects.length).padStart(2, "0")}</strong>
            <footer><b>科研資產</b><span>每一次結論都保留來路</span></footer>
          </article>
          <article className="rv-poster rv-poster-blue">
            <span>OBJECTS / FILES</span>
            <strong>{String(totals.files).padStart(2, "0")}</strong>
            <p>WORD<br/>PDF<br/>DATA<br/>CODE</p>
            <small>INLINE / READABLE / TENANT-SCOPED</small>
          </article>
          <article className="rv-poster rv-poster-signal">
            <span>REPRODUCIBILITY SIGNAL</span>
            <div className="rv-signal-mark"><i/><i/><i/><i/></div>
            <strong>{totals.commits}</strong>
            <p>GIT COMMITS<br/>ON MAIN</p>
          </article>
          <article className="rv-poster rv-poster-type">
            <span>HEAD / LATEST</span>
            <code>{shortSha(selectedProject && selectedProject.head_git_sha)}</code>
            <p>{selectedProject ? selectedProject.title : "NO PROJECT YET"}</p>
            <small>{selectedProject ? selectedProject.research_area || "GENERAL RESEARCH" : "CREATE THE FIRST VERSIONED STUDY"}</small>
          </article>
        </section>

        <div className="rv-metrics">
          <Metric label="PROJECTS" value={projects.length} note="科研課題"/>
          <Metric label="OBJECTS" value={totals.files} note="可閱覽文件"/>
          <Metric label="VERSIONS" value={totals.versions} note="不可變版本"/>
          <Metric label="COMMITS" value={totals.commits} note="Git 提交"/>
          <Metric label="STORAGE" value={compact(totals.bytes)} note="歷史總量"/>
        </div>

        <Band no="01" title="COMMAND DECK" sub="按鈕即指令 · 終端 / AI / 手動操作同源">
          <div className="rv-command-grid">
            <CommandButton tool="research_formats_list" command="research formats list" note="格式、閱覽與上傳限制"/>
            <CommandButton tool="research_project_list" command="research project list" note="取得科研課題索引"/>
            <CommandButton tool="research_project_create" command="research project create" note="建立 Git 課題空間"/>
            <CommandButton tool="research_project_show" command="research project show"
              args={selectedProject ? { project: clean(selectedProject.id) } : {}}
              disabled={!selectedProject} note="文件與提交譜系"/>
            <CommandButton tool="research_upload_contract" command="research upload contract"
              args={selectedProject ? { project: clean(selectedProject.id) } : {}}
              disabled={!selectedProject || !canWrite} note="生成終端上傳 API 契約"/>
            <CommandButton tool="research_git_log" command="research git log"
              args={selectedProject ? { project: clean(selectedProject.id) } : {}}
              disabled={!selectedProject} note="讀取原生 Git 提交"/>
            <CommandButton tool="research_file_versions" command="research file versions"
              args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
              disabled={!selectedProject || !selectedFile} note="不可變文件版本"/>
            <CommandButton tool="research_file_preview" command="research file preview"
              args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
              disabled={!selectedProject || !selectedFile} note="內嵌閱覽當前版本"/>
            <CommandButton tool="research_file_diff" command="research file diff"
              args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
              disabled={!selectedProject || !selectedFile} note="比較最近兩個版本"/>
          </div>
        </Band>

        <Band no="02" title="RECENT RESEARCH" sub="當前公司 · 不製造示例數據"
          right={<button className="btn sm" onClick={() => selectSection("projects")}>進入課題庫 →</button>}>
          {busy ? <div className="rv-loading">INDEXING RESEARCH OBJECTS…</div> : projects.length ? (
            <div className="rv-overview-projects">
              {projects.slice(0, 6).map((project, index) => (
                <button key={project.id} onClick={() => { selectProject(clean(project.id)); selectSection("projects"); }}>
                  <em>{String(index + 1).padStart(2, "0")}</em>
                  <div><strong>{project.title}</strong><small>{project.research_area || "GENERAL RESEARCH"}</small></div>
                  <span>{project.file_count || 0}<small>OBJECTS</small></span>
                  <code>{shortSha(project.head_git_sha)}</code>
                </button>
              ))}
            </div>
          ) : <EmptyPanel title="科研索引尚未建立" copy="建立第一個課題後，總覽會只呈現真實的文件、版本與提交數據。"/>}
        </Band>
      </>}

      {section === "guide" && <>
        <section className="rv-guide-binding" data-testid="research-guide-paper-selector"
          aria-label="選擇論文">
          <div className="rv-guide-binding-index">
            <span>00 / PAPER CONTEXT</span>
            <b>{selectedProject ? "BOUND" : "SELECT"}</b>
            <small>課題即論文<br/>一次只導引一篇</small>
          </div>
          <label>
            <span>SELECT PAPER / 選擇論文</span>
            <select value={projectId} disabled={!projects.length}
              onChange={event => selectProject(clean(event.target.value))}>
              {!projects.length && <option value="">尚無可選論文</option>}
              {projects.map((project, index) => (
                <option key={project.id} value={clean(project.id)}>
                  {String(index + 1).padStart(2, "0")} · {project.title}
                </option>
              ))}
            </select>
            <small>切換後，九道關卡、完成度與下一步都會依這篇論文的真實資料重新計算。</small>
          </label>
          <article>
            <span>CURRENT PAPER / 當前綁定</span>
            <strong>{selectedProject ? selectedProject.title : "尚未選擇論文"}</strong>
            <p>{selectedProject
              ? selectedProject.summary || "這篇論文尚未填寫研究摘要。"
              : "先建立或選擇一個課題，論文導引才會開始。"}</p>
            <footer>
              <code>main@{shortSha(selectedProject && selectedProject.head_git_sha)}</code>
              <span>{selectedProject ? (selectedProject.file_count || 0) + " OBJECTS" : "NO CONTEXT"}</span>
            </footer>
          </article>
          <button type="button" onClick={() => selectSection("projects")}>管理論文 →</button>
        </section>

        <section className="rv-guide-poster" aria-label="論文研究導引">
          <header><span>RESEARCH COMPASS / NINE GATES</span><code>{selectedProject ? selectedProject.title : "SELECT A PROJECT"}</code></header>
          <div className="rv-guide-score">
            <span>READINESS</span>
            <strong>{String(journeyComplete).padStart(2, "0")}<i>/09</i></strong>
            <small>依課題中的真實 DMP、文件、Run、證據與覆核計算</small>
          </div>
          <article>
            <span>WRITE A PAPER THAT CAN BE CHECKED</span>
            <p>QUESTION<br/>BECOMES<br/><b>EVIDENCE.</b></p>
            <small>IDEA → DESIGN → MATERIAL → ANALYSIS → ARGUMENT → REVIEW</small>
          </article>
          <aside>
            <span>NEXT RECOMMENDED GATE</span>
            <b>{nextJourney.no}</b>
            <strong>{nextJourney.zh}</strong>
            <p>{nextJourney.output}</p>
            <button type="button" onClick={() => selectSection(nextJourney.section)}>前往這一步 →</button>
          </aside>
        </section>

        {!selectedProject ? <EmptyPanel title="先選擇或建立研究課題" copy="論文導引只根據真實課題資料計算，不用示例進度冒充完成。"/> : <>
          <Band no="01" title="RESEARCH JOURNEY" sub="九道關卡 · 每一步都有產出與可驗證完成條件">
            <div className="rv-journey-grid">
              {journey.map(item => {
                const state = item.complete ? "complete" : item.key === nextJourney.key ? "next" : "open";
                return <button type="button" key={item.key} className={state}
                  onClick={() => selectSection(item.section)}>
                  <header><b>{item.no}</b><span>{state === "complete" ? "DONE" : state === "next" ? "NEXT" : "OPEN"}</span></header>
                  <strong>{item.title}</strong>
                  <h3>{item.zh}</h3>
                  <p>{item.output}</p>
                  <footer>{item.complete ? "已找到對應科研產出" : "打開工作區 →"}</footer>
                </button>;
              })}
            </div>
          </Band>

          <div className="rv-guide-columns">
            <Band no="02" title="PAPER SPINE" sub="七個部分共同服務同一條論證主線">
              <div className="rv-paper-spine">
                {paperSpine.map(item => <article key={item[0]}>
                  <b>{item[0]}</b><strong>{item[1]}</strong><p>{item[2]}</p>
                </article>)}
              </div>
            </Band>
            <Band no="03" title="NEXT ACTION" sub="系統只推薦尚未具備真實產出的最前一步">
              <div className="rv-next-action">
                <span>{nextJourney.no} / {nextJourney.title}</span>
                <strong>{nextJourney.zh}</strong>
                <p>這一步需要形成：{nextJourney.output}。完成後，導引會根據課題的實際資料重新計算，而不是手動勾選。</p>
                <button className="btn primary" onClick={() => selectSection(nextJourney.section)}>進入對應工作區</button>
                <CommandButton tool={nextJourney.tool} command={nextJourney.command}
                  args={{ project: selectedProject.id }}
                  disabled={(nextJourney.write && !canWrite) || (nextJourney.review && !canReview)}
                  note="以同一能力契約交給終端或 AI 執行"/>
              </div>
            </Band>
          </div>

          <Band no="04" title="WRITING RULES" sub="讓每一次修訂都推動論證，而不只是增加字數">
            <div className="rv-writing-rules">
              <article><b>01</b><strong>ONE QUESTION</strong><p>每一章都必須回到同一個核心問題；無法回去的內容移入附錄或刪除。</p></article>
              <article><b>02</b><strong>CLAIM BEFORE PROSE</strong><p>先寫本節要證明的主張，再選證據與段落；不要用長篇背景代替論證。</p></article>
              <article><b>03</b><strong>VERSION WITH REASON</strong><p>每次上傳寫清修改目的，讓 Git diff 回答「為什麼變」，不只回答「哪裡變」。</p></article>
              <article><b>04</b><strong>LIMITS ARE RESULTS</strong><p>主動記錄失敗、偏差與適用邊界；它們是可信度的一部分，不是需要隱藏的瑕疵。</p></article>
            </div>
          </Band>
        </>}
      </>}

      {projectsMounted && <div hidden={section !== "projects"} aria-hidden={section !== "projects"}>
        <section className="rv-library-poster" data-testid="research-library-poster" aria-label="課題庫海報">
          <article className="rv-library-title">
            <span>CATALOGUE / BONFIRE</span>
            <strong>{String(projects.length).padStart(2, "0")}</strong>
            <p>PROJECT<br/>LIBRARY</p>
            <small>研究課題不是文件夾<br/>而是持續生長的論證單位</small>
          </article>
          <article className="rv-library-focus">
            <header>
              <span>SELECTED RESEARCH / {selectedProject ? "ACTIVE" : "NONE"}</span>
              <code>main@{shortSha(selectedProject && selectedProject.head_git_sha)}</code>
            </header>
            <h2>{selectedProject ? selectedProject.title : "選擇一項研究課題"}</h2>
            <p>{selectedProject
              ? selectedProject.summary || "此課題尚未填寫研究摘要。"
              : "左側索引會定位課題，文件、版本與閱讀器隨之同步。"}
            </p>
            <footer>
              <b>{selectedProject ? selectedProject.research_area || "GENERAL RESEARCH" : "RESEARCH AREA"}</b>
              <span>POSTGRESQL / GIT / SHA-256</span>
            </footer>
          </article>
          <article className="rv-library-data">
            <span>ACTIVE DOSSIER</span>
            <div><strong>{selectedProject ? selectedProject.file_count || 0 : "—"}</strong><small>OBJECTS</small></div>
            <div><strong>{selectedProject ? selectedProject.version_count || 0 : "—"}</strong><small>VERSIONS</small></div>
            <div><strong>{selectedProject ? selectedProject.commit_count || 0 : "—"}</strong><small>COMMITS</small></div>
            <code>{selectedProject ? compact(selectedProject.stored_bytes) : "—"}</code>
          </article>
        </section>
        <div className="rv-page-command">
          <span>ACTIVE COMMANDS</span>
          <CommandButton tool="research_project_list" command="research project list" note="刷新課題索引"/>
          <CommandButton tool="research_project_show" command="research project show"
            args={selectedProject ? { project: clean(selectedProject.id) } : {}}
            disabled={!selectedProject} note="查看當前課題"/>
          <CommandButton tool="research_upload_contract" command="research upload contract"
            args={selectedProject ? { project: clean(selectedProject.id) } : {}}
            disabled={!selectedProject || !canWrite} note="終端上傳 API"/>
        </div>
        <Band no="01" title="RESEARCH INDEX" sub="課題 / 文件 / 閱讀器">
          {busy ? <div className="rv-loading block">INDEXING RESEARCH OBJECTS…</div> : (
            <div className={"rv-workbench rv-library-workbench " + (tab === "review" ? "reviewing" : "")}>
              <ProjectRail projects={projects} projectId={projectId} onSelect={selectProject}/>

              <section className="rv-files">
                <header>
                  <div><span>OBJECT REGISTER</span><h2>{selectedProject ? selectedProject.title : "—"}</h2></div>
                  <code>main@{shortSha(selectedProject && selectedProject.head_git_sha)}</code>
                </header>
                {selectedProject && <section className="rv-object-topology" data-testid="research-object-topology">
                  <header>
                    <div><span>SWISS OBJECT TOPOLOGY</span><strong>科研資產分類</strong></div>
                    <code>{visibleResearchFiles.length}/{researchFiles.length}</code>
                  </header>
                  <nav aria-label="按科研用途篩選文件">
                    {ASSET_TAXONOMY.map(([key, en, zh], index) => {
                      const count = key === "all" ? researchFiles.length : (assetCounts[key] || 0);
                      return <button type="button" key={key}
                        className={(assetFilter === key ? "active " : "") + key}
                        onClick={() => selectAssetFilter(key)} aria-pressed={assetFilter === key}>
                        <em>{String(index).padStart(2, "0")}</em>
                        <b>{en}</b>
                        <span>{zh}</span>
                        <strong>{count}</strong>
                      </button>;
                    })}
                  </nav>
                </section>}
                {canWrite && selectedProject && (
                  <form className="rv-upload" onSubmit={uploadFile}>
                    <input ref={fileInput} type="file" name="file" required
                      accept=".docx,.pdf,.html,.htm,.csv,.tsv,.sql,.dbml,.db,.sqlite,.sqlite3,.py,.r,.jl,.js,.jsx,.ts,.tsx,.ipynb,.md,.txt,.json,.yaml,.yml,.xml,.png,.jpg,.jpeg,.gif,.webp,.svg"/>
                    <input name="logical_path" placeholder="邏輯路徑（留空使用文件名）"/>
                    <input name="commit_message" placeholder="本次修改說明"/>
                    <button className="btn" disabled={uploading}>{uploading ? "COMMITTING…" : "上傳並提交"}</button>
                  </form>
                )}
                {!selectedProject && <EmptyPanel title="科研索引為空" copy="用「新建課題」建立獨立的 Git 研究空間。"/>}
                {selectedProject && !(detail && detail.files || []).length && (
                  <EmptyPanel title="此課題尚無文件" copy="上傳 Word、PDF、HTML、CSV、代碼或圖像，第一次提交會自動建立版本。"/>
                )}
                {selectedProject && researchFiles.length > 0 && !visibleResearchFiles.length && (
                  <EmptyPanel title="此分類尚無文件" copy="可切換其他拓撲節點，或按科研用途上傳新的文件。"/>
                )}
                <div className="rv-file-list">
                  {visibleResearchFiles.map((file, index) => {
                    const taxon = assetTaxon(assetClassOf(file));
                    return (
                    <button key={file.id} className={clean(file.id) === clean(fileId) ? "active" : ""}
                      onClick={() => { setFileId(clean(file.id)); setTab(file.file_kind === "document" || file.file_kind === "pdf" ? "review" : "preview"); }}>
                      <em>{String(index + 1).padStart(2, "0")}</em>
                      <span className={"rv-asset-class " + taxon[0]}>{taxon[1]}<small>{taxon[2]}</small></span>
                      <span><strong>{file.logical_path}</strong><small>{kindName[file.file_kind] || "FILE"} · v{file.current_version} · {compact(file.size_bytes)} · {stamp(file.version_created_at)}</small></span>
                      <code>{shortSha(file.git_sha)}</code>
                    </button>
                    );
                  })}
                </div>
              </section>

              <Viewer project={selectedProject} file={selectedFile} preview={preview}
                diff={diff} tab={tab} onTab={setTab} blobUrl={blobUrl} busy={detailBusy || viewerBusy}
                canAnnotate={canWrite || canReview} onError={setError}/>
            </div>
          )}
        </Band>
      </div>}

      {section === "workflow" && <>
        <section className="rv-flow-poster" aria-label="研究生命週期">
          <header>
            <span>RESEARCH OPERATING MODEL / 01—09</span>
            <code>{selectedProject ? selectedProject.title : "SELECT A PROJECT"}</code>
          </header>
          <div className="rv-flow-word">FROM<br/>QUESTION<br/>TO EVIDENCE</div>
          <div className="rv-flow-stages">
            {[
              ["01", "PLAN", "研究問題"],
              ["02", "GOVERN", "動態 DMP"],
              ["03", "PROTOCOL", "協議鎖版"],
              ["04", "RUN", "執行批次"],
              ["05", "EXECUTE", "隔離重跑"],
              ["06", "EVIDENCE", "證據連結"],
              ["07", "REVIEW", "同行覆核"],
              ["08", "REPRODUCE", "重現檢查"],
              ["09", "RELEASE", "研究發布"],
            ].map(item => <article key={item[0]}><b>{item[0]}</b><strong>{item[1]}</strong><small>{item[2]}</small></article>)}
          </div>
          <footer><b>{workflowStats.reproduction_status.toUpperCase()}</b><span>REPRODUCIBILITY STATUS</span></footer>
        </section>

        <div className="rv-workflow-metrics">
          <Metric label="DMP" value={"V" + workflowStats.dmp_version} note="動態資料計畫"/>
          <Metric label="PROTOCOL" value={workflowStats.locked_protocols + "/" + workflowStats.protocols} note="已鎖版 / 全部"/>
          <Metric label="RUN" value={workflowStats.completed_runs + "/" + workflowStats.runs} note="已完成 / 全部"/>
          <Metric label="CLAIMS" value={workflowStats.claims} note="待證據與覆核"/>
          <Metric label="RELEASE" value={workflowStats.releases} note="不可變發布"/>
        </div>

        <Band no="01" title="WORKFLOW COMMANDS" sub="手動表單、終端與 AI 使用同一能力契約">
          <div className="rv-command-grid">
            <CommandButton tool="research_workflow_show" command="research workflow show"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject}
              note="讀取完整研究生命週期"/>
            <CommandButton tool="research_dmp_update" command="research dmp update"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="建立下一版資料管理計畫"/>
            <CommandButton tool="research_protocol_create" command="research protocol create"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="建立可鎖版研究協議"/>
            <CommandButton tool="research_run_start" command="research run start"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="開始一次研究 Run"/>
          </div>
        </Band>

        {!selectedProject ? <EmptyPanel title="先選擇研究課題" copy="研究流程會永久綁定一個課題，避免跨課題混用資料和證據。"/> :
        workflowBusy && !workflow ? <div className="rv-loading block">LOADING RESEARCH OPERATING MODEL…</div> : <>
          <Band no="02" title="LIVING DATA MANAGEMENT PLAN" sub="SNSF / ETH 式動態 DMP · 每次保存生成新版本"
            right={<span className={"rv-status " + clean(workflow && workflow.dmp && workflow.dmp.status)}>
              {workflow && workflow.dmp ? "V" + workflow.dmp.version + " · " + workflow.dmp.status : "NOT STARTED"}
            </span>}>
            <form className="rv-dmp-grid" onSubmit={saveDmpForm} key={workflow && workflow.dmp && workflow.dmp.id || "empty"}>
              <label><span>01 · RESEARCH QUESTION</span><textarea name="research_question" defaultValue={dmpContent.research_question || ""} placeholder="這項研究要回答什麼問題？"/></label>
              <label><span>02 · HYPOTHESIS</span><textarea name="hypothesis" defaultValue={dmpContent.hypothesis || ""} placeholder="可以被證偽的假設與成功標準"/></label>
              <label><span>03 · COLLECTION</span><textarea name="data_collection" defaultValue={dmpContent.data_collection || ""} placeholder="資料如何產生、收集與文件化"/></label>
              <label><span>04 · ETHICS / LEGAL / SECURITY</span><textarea name="ethics_legal_security" defaultValue={dmpContent.ethics_legal_security || ""} placeholder="倫理、同意、個資、保密與智慧財產"/></label>
              <label><span>05 · STORAGE / PRESERVATION</span><textarea name="storage_preservation" defaultValue={dmpContent.storage_preservation || ""} placeholder="備份、格式、保存期限與責任人"/></label>
              <label><span>06 · SHARING / REUSE</span><textarea name="sharing_reuse" defaultValue={dmpContent.sharing_reuse || ""} placeholder="公開、禁運或限制存取；授權與儲存庫"/></label>
              <label className="wide"><span>07 · RESPONSIBILITIES</span><textarea name="responsibilities" defaultValue={dmpContent.responsibilities || ""} placeholder="PI、研究者、資料管理人與審查者的責任"/></label>
              {canWrite && <button className="btn primary" disabled={mutating === "dmp"}>{mutating === "dmp" ? "VERSIONING…" : "保存為下一版 DMP"}</button>}
            </form>
          </Band>

          <div className="rv-workflow-columns">
            <Band no="03" title="PROTOCOL REGISTER" sub="先鎖定方法，再開始產生證據">
              {canWrite && <form className="rv-mini-form" onSubmit={createProtocolForm}>
                <input name="title" required placeholder="協議名稱"/>
                <input name="objective" placeholder="協議目的"/>
                <textarea name="procedure" placeholder="步驟、樣品、設備與分析計畫"/>
                <button className="btn" disabled={mutating === "protocol"}>建立協議</button>
              </form>}
              <div className="rv-operating-list">
                {((workflow && workflow.protocols) || []).map(item => <article key={item.id}>
                  <code>{item.protocol_code} / V{item.version}</code>
                  <div><strong>{item.title}</strong><small>{item.objective || "尚未描述協議目的"}</small></div>
                  <span className={"rv-status " + item.status}>{item.status}</span>
                </article>)}
                {workflow && !workflow.protocols.length && <EmptyPanel title="尚無研究協議" copy="協議把方法、設備和分析計畫固定成可審查基線。"/>}
              </div>
            </Band>
            <Band no="04" title="RUN REGISTER" sub="每一次執行保留協議、輸入、環境與偏差">
              {canWrite && <form className="rv-mini-form" onSubmit={createRunForm}>
                <input name="title" required placeholder="Run 名稱"/>
                <select name="protocol_id"><option value="">不指定協議</option>
                  {((workflow && workflow.protocols) || []).map(item =>
                    <option value={item.id} key={item.id}>{item.protocol_code} · {item.title}</option>)}
                </select>
                <input name="inputs" placeholder="輸入、樣品或參數"/>
                <input name="environment" placeholder="設備、軟體與環境"/>
                <button className="btn" disabled={mutating === "run"}>開始 Run</button>
              </form>}
              <div className="rv-operating-list">
                {((workflow && workflow.runs) || []).map(item => <article key={item.id}>
                  <code>{item.run_code}</code>
                  <div><strong>{item.title}</strong><small>{item.protocol_code || "NO PROTOCOL"} · {stamp(item.started_at)}</small></div>
                  <span className={"rv-status " + item.status}>{item.status}</span>
                  {canWrite && item.status === "running" && <button className="btn sm" onClick={() => completeRun(item)}
                    disabled={mutating === "run-" + item.id}>完成</button>}
                </article>)}
                {workflow && !workflow.runs.length && <EmptyPanel title="尚無研究 Run" copy="開始執行後，時間、環境和輸入會成為證據鏈的一部分。"/>}
              </div>
            </Band>
          </div>
        </>}
      </>}

      {section === "evidence" && <>
        <section className="rv-evidence-poster">
          <div><span>CLAIM</span><strong>{String(workflowStats.claims).padStart(2, "0")}</strong><small>可檢驗主張</small></div>
          <div><span>EVIDENCE</span><strong>{String(workflowStats.evidence_links).padStart(2, "0")}</strong><small>精確證據連結</small></div>
          <article><span>RESEARCH INTEGRITY</span><p>NO CLAIM<br/>WITHOUT<br/><b>EVIDENCE.</b></p><small>FILE VERSION / RUN / REVIEW / RELEASE</small></article>
          <div className={"rv-repro-signal " + workflowStats.reproduction_status}>
            <span>REPRODUCE</span><strong>{workflowStats.reproduction_status.replace("_", " ").toUpperCase()}</strong><small>{workflowStats.releases} RELEASES</small>
          </div>
        </section>

        <Band no="01" title="EVIDENCE COMMANDS" sub="每個操作都在業務能力拓撲中可見">
          <div className="rv-command-grid">
            <CommandButton tool="research_claim_create" command="research claim create"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="建立待驗證研究主張"/>
            <CommandButton tool="research_evidence_link" command="research evidence link"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="連結文件版本或 Run"/>
            <CommandButton tool="research_review_submit" command="research review submit"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canReview}
              note="同行覆核與正式決定"/>
            <CommandButton tool="research_reproduce_check" command="research reproduce check"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canWrite}
              note="檢查研究清單完整性"/>
            <CommandButton tool="research_release_create" command="research release create"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject || !canReview}
              note="建立不可變 RO-Crate 發布"/>
          </div>
        </Band>

        {!selectedProject ? <EmptyPanel title="先選擇研究課題" copy="主張、證據與覆核不會跨越課題邊界。"/> : <>
          <div className="rv-evidence-forms">
            <Band no="02" title="NEW CLAIM" sub="先寫下可被支持或反駁的主張">
              {canWrite ? <form className="rv-mini-form" onSubmit={createClaimForm}>
                <textarea name="statement" required placeholder="例如：在既定條件下，升溫使材料強度下降。"/>
                <input name="confidence" type="number" min="0" max="1" step="0.01" placeholder="信心 0—1"/>
                <button className="btn primary" disabled={mutating === "claim"}>提交主張</button>
              </form> : <EmptyPanel title="僅可閱讀" copy="需要 research.write 權限才能建立主張。"/>}
            </Band>
            <Band no="03" title="LINK EVIDENCE" sub="連到不可變文件版本或具體 Run">
              {canWrite && workflow && workflow.claims.length && evidenceSources.length ? <form className="rv-mini-form" onSubmit={linkEvidenceForm}>
                <select name="claim_id" required>{workflow.claims.map(item =>
                  <option value={item.id} key={item.id}>{item.claim_code} · {item.statement}</option>)}</select>
                <select name="source" required>{evidenceSources.map(item =>
                  <option value={item.value} key={item.value}>{item.label}</option>)}</select>
                <select name="relation"><option value="supports">支持</option><option value="contradicts">反駁</option><option value="method">方法</option><option value="context">脈絡</option></select>
                <input name="note" placeholder="證據如何支持或限制此主張"/>
                <button className="btn" disabled={mutating === "evidence"}>建立證據連結</button>
              </form> : <EmptyPanel title="還不能連結證據" copy="先建立主張，並至少具有一個 Run 或科研文件版本。"/>}
            </Band>
          </div>

          <Band no="04" title="CLAIM — EVIDENCE GRAPH" sub="從結論直接回到 Run、文件雜湊和 Git 提交">
            <div className="rv-claim-list">
              {((workflow && workflow.claims) || []).map((claim, index) => <article key={claim.id}>
                <header><em>{String(index + 1).padStart(2, "0")}</em><code>{claim.claim_code}</code>
                  <span className={"rv-status " + claim.status}>{claim.status}</span></header>
                <p>{claim.statement}</p>
                <div>{(claim.evidence || []).map(item => <span key={item.id}>
                  <b>{item.relation.toUpperCase()}</b>
                  {item.run_code ? item.run_code + " · " + item.run_title : "V" + item.file_version + " · " + item.logical_path}
                  {item.git_sha && <code>{shortSha(item.git_sha)}</code>}
                </span>)}</div>
                {!claim.evidence.length && <small className="rv-warning">NO EVIDENCE LINKED</small>}
              </article>)}
              {workflow && !workflow.claims.length && <EmptyPanel title="尚無研究主張" copy="主張是證據鏈的中心，不是普通備註。"/>}
            </div>
          </Band>

          <div className="rv-review-release">
            <Band no="05" title="PEER REVIEW" sub="四眼覆核 · 決定與理由全程稽核">
              {canReview && reviewTargets.length ? <form className="rv-mini-form" onSubmit={submitReviewForm}>
                <select name="target" required>{reviewTargets.map(item =>
                  <option value={item.value} key={item.value}>{item.label}</option>)}</select>
                <select name="decision"><option value="approve">批准</option><option value="changes_requested">要求修改</option><option value="reject">駁回</option><option value="comment">評論</option></select>
                <textarea name="comment" placeholder="覆核依據與修改要求"/>
                <button className="btn primary" disabled={mutating === "review"}>提交覆核</button>
              </form> : <EmptyPanel title="無可覆核對象或權限" copy="DMP、協議和主張建立後，research.review 角色可以正式覆核。"/>}
              <div className="rv-review-list">{((workflow && workflow.reviews) || []).slice(0, 8).map(item =>
                <article key={item.id}><code>{item.target_type.toUpperCase()}</code><strong>{item.decision}</strong><span>{item.reviewer_name || "Reviewer"} · {stamp(item.created_at)}</span><p>{item.comment || "—"}</p></article>)}</div>
            </Band>
            <Band no="06" title="REPRODUCE / RELEASE" sub="先通過研究清單檢查，再凍結發布">
              <div className="rv-release-gate">
                <span>LAST CHECK</span>
                <strong>{workflowStats.reproduction_status.toUpperCase()}</strong>
                <small>DMP · PROTOCOL · RUN · ENVIRONMENT · HASH · EVIDENCE</small>
                {canWrite && <button className="btn" onClick={reproduce} disabled={mutating === "reproduce"}>
                  {mutating === "reproduce" ? "CHECKING…" : "執行重現檢查"}
                </button>}
              </div>
              {workflow && workflow.reproduction_checks.length > 0 && <div className="rv-findings">
                {(workflow.reproduction_checks[0].findings || []).map((item, index) =>
                  <span key={index} className={item.severity}><b>{item.code}</b>{item.detail || ""}</span>)}
                {!workflow.reproduction_checks[0].findings.length && <span className="pass"><b>MANIFEST COMPLETE</b>研究清單完整</span>}
              </div>}
              {canReview && <form className="rv-mini-form rv-release-form" onSubmit={createReleaseForm}>
                <input name="title" placeholder="研究發布標題（留空自動生成）"/>
                <select name="access_level"><option value="restricted">限制存取</option><option value="embargoed">禁運期</option><option value="open">公開</option></select>
                <input name="license" placeholder="授權，例如 CC-BY-4.0"/>
                <button className="btn primary" disabled={mutating === "release" || workflowStats.reproduction_status !== "passed"}>建立 RO-Crate 發布</button>
              </form>}
              <div className="rv-release-list">{((workflow && workflow.releases) || []).map(item =>
                <article key={item.id}><b>V{item.version}</b><div><strong>{item.title}</strong><small>{item.release_code} · {item.access_level}</small></div><code>{shortSha(item.manifest_sha256)}</code></article>)}</div>
            </Band>
          </div>
        </>}
      </>}

      {section === "execution" && <>
        <section className="rv-execution-poster" aria-label="科研重現運算海報">
          <header><span>REPRODUCIBLE COMPUTE / CONTROLLED RUNNER</span><code>PYTHON 3.13</code></header>
          <div className="rv-execution-type">RUN<br/><b>WHAT<br/>YOU<br/>CITE.</b></div>
          <div className="rv-execution-grid">
            <article><b>01</b><strong>PIN</strong><small>FILE VERSION + SHA-256</small></article>
            <article><b>02</b><strong>ISOLATE</strong><small>NO NETWORK / NO SHELL</small></article>
            <article><b>03</b><strong>EXECUTE</strong><small>TIME / MEMORY / PROCESS LIMITS</small></article>
            <article><b>04</b><strong>RETURN</strong><small>LOG + ARTIFACT + GIT</small></article>
          </div>
          <footer>
            <strong>{String(workflowStats.successful_executions).padStart(2, "0")}</strong>
            <span>VERIFIED RUNS</span>
            <b>{workflowStats.running_executions ? "WORKER ACTIVE" : "QUEUE READY"}</b>
          </footer>
        </section>

        <div className="rv-workflow-metrics">
          <Metric label="EXECUTIONS" value={workflowStats.executions} note="持久任務"/>
          <Metric label="SUCCEEDED" value={workflowStats.successful_executions} note="退出碼 0"/>
          <Metric label="ACTIVE" value={workflowStats.running_executions} note="排隊 / 執行"/>
          <Metric label="NETWORK" value="OFF" note="無外網隔離"/>
          <Metric label="RUNTIME" value="PY 3.13" note="NumPy / Pandas / SciPy"/>
        </div>

        <Band no="01" title="EXECUTION COMMANDS" sub="介面、終端與 AI 共用同一個持久佇列">
          <div className="rv-command-grid">
            <CommandButton tool="research_execution_runtimes" command="research execution runtimes"
              note="查看運行時與隔離契約"/>
            <CommandButton tool="research_execution_list" command="research execution list"
              args={selectedProject ? { project: selectedProject.id } : {}} disabled={!selectedProject}
              note="讀取課題任務佇列"/>
            <CommandButton tool="research_execution_submit" command="research execution submit"
              args={selectedProject ? { project: selectedProject.id } : {}}
              disabled={!selectedProject || !canWrite} note="提交版本固定運算"/>
            <CommandButton tool="research_execution_show" command="research execution show"
              args={selectedProject && executionDetail ? {
                project: selectedProject.id, execution: executionDetail.execution.id,
              } : {}} disabled={!selectedProject || !executionDetail} note="查看日誌與產物"/>
          </div>
        </Band>

        {!selectedProject ? <EmptyPanel title="先選擇研究課題" copy="重現任務只能執行該課題中已固定 SHA-256 的文件版本。"/> : <>
          <Band no="02" title="RUN COMPOSER" sub="定義任務、固定輸入、設定預算，檢查完成後才送入隔離佇列">
            {canWrite && codeFiles.length ? <form className="rv-run-composer" onSubmit={submitExecutionForm}>
              <header>
                <div><span>VERSION-PINNED EXECUTION</span><strong>提交一個可被再次執行、再次引用的分析任務</strong></div>
                <code>PYTHON 3.13 · NETWORK OFF</code>
              </header>
              <div className="rv-run-compose-grid">
                <section className="rv-run-definition">
                  <div className="rv-run-step"><b>01</b><span>TASK DEFINITION</span><small>說明這次分析要回答什麼，而不只是程式名稱</small></div>
                  <label className="wide"><span>TITLE / 任務名稱</span><input name="title" required placeholder="例如：以固定種子重跑衝擊係數與比較圖"/></label>
                  <label className="wide"><span>ENTRYPOINT / Python 入口</span><select name="entrypoint" required
                    value={executionEntrypoint} onChange={event => chooseExecutionEntrypoint(event.target.value)}>{codeFiles.map(item =>
                    <option key={item.id} value={item.logical_path}>V{item.current_version} · {item.logical_path}</option>)}</select>
                    <small>入口文件必定包含在固定輸入中，不能從本次清單排除。</small></label>
                  <label className="wide"><span>ARGUMENTS / JSON ARRAY</span><input name="arguments" defaultValue="[]" placeholder='["--seed","42"]'/>
                    <small>無參數使用 []；系統不接受 shell 字串或臨時貼入程式。</small></label>
                </section>
                <aside className="rv-run-context">
                  <div className="rv-run-step"><b>02</b><span>CONTEXT + BUDGET</span><small>讓資源與研究批次一起被稽核</small></div>
                  <label><span>LINKED RESEARCH RUN</span><select name="run_id"><option value="">不關聯實驗 Run</option>
                    {((workflow && workflow.runs) || []).map(item => <option key={item.id} value={item.id}>{item.run_code} · {item.title}</option>)}</select></label>
                  <div className="rv-run-budget">
                    <label><span>TIME LIMIT</span><select name="timeout_seconds" defaultValue="300"><option value="60">01 MIN</option><option value="300">05 MIN</option><option value="600">10 MIN</option><option value="900">15 MIN</option></select></label>
                    <label><span>MEMORY</span><select name="memory_mb" defaultValue="1024"><option value="512">512 MB</option><option value="1024">1 GB</option><option value="2048">2 GB</option></select></label>
                  </div>
                  <div className="rv-run-guardrails">
                    <span><i/>NO INTERNET</span><span><i/>READ-ONLY INPUTS</span><span><i/>HASHED OUTPUTS</span><span><i/>BOUNDED PROCESS</span>
                  </div>
                </aside>
              </div>
              <section className="rv-run-inputs">
                <header>
                  <div><b>03</b><span>PIN INPUT VERSIONS</span><small>執行開始後，輸入不會跟著課題的新版本漂移</small></div>
                  <nav>
                    <button type="button" className={executionPinMode === "all" ? "active" : ""} onClick={() => setExecutionPinMode("all")}>全部最新版本</button>
                    <button type="button" className={executionPinMode === "custom" ? "active" : ""} onClick={() => setExecutionPinMode("custom")}>自選固定版本</button>
                  </nav>
                </header>
                {executionPinMode === "all" ? <div className="rv-run-auto-pin">
                  <strong>{allExecutionInputs.length}</strong><span>個最新文件版本將在提交瞬間固定</span><small>{compact(pinnedExecutionBytes)} · 包含入口、資料、配置、文稿與當前結果</small>
                </div> : <>
                  <div className="rv-run-input-tools">
                    <input type="search" value={executionInputFilter} onChange={event => setExecutionInputFilter(event.target.value)} placeholder="依邏輯路徑篩選文件…"/>
                    <button type="button" onClick={() => setExecutionInputIds(allExecutionInputs.map(item => item.id))}>全選</button>
                    <button type="button" onClick={() => {
                      const entry = allExecutionInputs.find(item => item.logical_path === executionEntrypoint);
                      setExecutionInputIds(entry ? [entry.id] : []);
                    }}>只留入口</button>
                  </div>
                  <div className="rv-run-input-list">
                    {visibleExecutionInputs.map(input => {
                      const forced = input.logical_path === executionEntrypoint;
                      const checked = forced || executionInputIds.includes(input.id);
                      return <label key={input.id} className={checked ? "selected" : ""}>
                        <input type="checkbox" checked={checked} disabled={forced} onChange={() => toggleExecutionInput(input)}/>
                        <span className={"rv-kind " + input.file_kind}>{kindName[input.file_kind] || "FILE"}</span>
                        <strong>{input.logical_path}</strong><small>V{input.version} · {compact(input.size_bytes)}</small>
                        {forced && <b>ENTRY</b>}
                      </label>;
                    })}
                    {!visibleExecutionInputs.length && <EmptyPanel title="沒有符合篩選的文件" copy="修改搜尋文字，或切回全部最新版本。"/>}
                  </div>
                </>}
              </section>
              <footer className="rv-run-preflight">
                <div><b>04</b><span>PRE-FLIGHT</span><strong>{pinnedExecutionInputs.length} FILES · {compact(pinnedExecutionBytes)}</strong>
                  <small>{executionEntrypoint || "NO ENTRYPOINT"}</small></div>
                <button className="btn primary" disabled={mutating === "execution-submit" || !pinnedExecutionInputs.length}>{mutating === "execution-submit" ? "PACKAGING IMMUTABLE INPUTS…" : "固定版本並提交運算 →"}</button>
              </footer>
            </form> : <EmptyPanel title={codeFiles.length ? "僅可閱讀" : "尚無 Python 入口"}
              copy={codeFiles.length ? "需要 research.write 權限才能提交執行。" : "先把 .py 程式上傳到課題庫；執行器不接受臨時貼入的任意程式。"}/>}
          </Band>

          <Band no="03" title="RUN HISTORY / OUTPUTS" sub="佇列是分析階段的執行記錄，不是科研流程本身">
          <div className="rv-execution-workbench">
            <section className="rv-execution-queue">
              <header><span>RUN QUEUE / HISTORY</span><b>{String(workflowStats.executions).padStart(2, "0")}</b></header>
              {((workflow && workflow.executions) || []).map((item, index) => <button key={item.id}
                className={executionDetail && clean(executionDetail.execution.id) === clean(item.id) ? "active" : ""}
                onClick={() => loadExecution(projectId, item.id).catch(reason => setError(clean(reason.message || reason)))}>
                <em>{String(index + 1).padStart(2, "0")}</em>
                <div><code>{item.job_code}</code><strong>{item.title}</strong><small>{stamp(item.created_at)} · {item.runtime}</small></div>
                <span className={"rv-status " + item.status}>{item.status}</span>
                <b>{item.artifact_count || 0}</b>
              </button>)}
              {workflow && !workflow.executions.length && <EmptyPanel title="佇列為空" copy="提交第一個固定版本運算後，生命週期會在這裡即時更新。"/>}
            </section>

            <section className="rv-execution-detail">
              {!executionDetail ? <EmptyPanel title="選擇一個重現任務" copy="查看固定輸入、執行日誌、退出碼與產物校驗值。"/> : <>
                <header>
                  <div><code>{executionDetail.execution.job_code}</code><h2>{executionDetail.execution.title}</h2>
                    <small>{shortSha(executionDetail.execution.manifest_sha256)} · {executionDetail.execution.runtime}</small></div>
                  <span className={"rv-status " + executionDetail.execution.status}>{executionDetail.execution.status}</span>
                </header>
                <div className="rv-execution-actions">
                  {["queued", "preparing", "running"].includes(executionDetail.execution.status) && canWrite &&
                    <button className="btn" onClick={() => cancelExecution(executionDetail.execution)} disabled={mutating === "execution-cancel"}>取消任務</button>}
                  {["failed", "cancelled", "timed_out", "succeeded"].includes(executionDetail.execution.status) && canWrite &&
                    <button className="btn" onClick={() => retryExecution(executionDetail.execution)} disabled={mutating === "execution-retry"}>以相同版本重跑</button>}
                  <CommandButton tool="research_execution_show" command="research execution show"
                    args={{ project: projectId, execution: executionDetail.execution.id }} note="打開完整指令回執"/>
                </div>
                <div className="rv-execution-manifest">
                  <span>PINNED INPUTS</span>
                  {(executionDetail.execution.input_manifest.inputs || []).map(item => <article key={item.file_version_id}>
                    <strong>{item.logical_path}</strong><small>V{item.version} · {compact(item.size_bytes)}</small><code>{shortSha(item.content_sha256)}</code>
                  </article>)}
                </div>
                <div className="rv-log-grid">
                  <article><header>STDOUT</header><pre>{executionDetail.execution.stdout_excerpt || "—"}</pre></article>
                  <article><header>STDERR</header><pre>{executionDetail.execution.stderr_excerpt || "—"}</pre></article>
                </div>
                <div className="rv-artifacts">
                  <header><span>VERIFIED ARTIFACTS</span><b>{executionDetail.artifacts.length}</b></header>
                  {executionDetail.artifacts.map(item => <article key={item.id}>
                    <div><strong>{item.relative_path}</strong><small>{compact(item.size_bytes)} · {item.content_type}</small></div>
                    <code>{shortSha(item.content_sha256)}</code>
                    <button className="btn" onClick={() => openArtifact(item)}>閱覽</button>
                    {item.promoted_file_version_id ? <span className="rv-status published">IN GIT</span> : canWrite &&
                      <button className="btn primary" onClick={() => promoteArtifact(item)} disabled={mutating === "artifact-" + item.id}>提升為科研文件</button>}
                  </article>)}
                  {!executionDetail.artifacts.length && <EmptyPanel title="尚無輸出產物" copy="程式把文件寫入 RESEARCH_OUTPUT_DIR 後，完成時會自動雜湊並登記。"/>}
                </div>
              </>}
            </section>
          </div>
          </Band>
        </>}
      </>}

      {section === "revisions" && <>
        <section className="rv-revision-poster">
          <span>GIT / MAIN</span>
          <strong>{shortSha(selectedProject && selectedProject.head_git_sha)}</strong>
          <p>EVERY CHANGE<br/>HAS AN AUTHOR,<br/>A TIME,<br/>A REASON.</p>
          <small>{selectedProject ? selectedProject.title : "SELECT A RESEARCH PROJECT"}</small>
        </section>
        <Band no="01" title="REVISION LINEAGE" sub="選擇課題後閱讀不可變提交時間線">
          <div className="rv-lineage">
            <ProjectRail projects={projects} projectId={projectId} onSelect={selectProject}
              emptyCopy="建立並提交科研文件後，這裡會生成版本譜系。"/>
            <div className="rv-lineage-main">
              <header>
                <div><span>COMMIT LEDGER</span><h2>{selectedProject ? selectedProject.title : "—"}</h2></div>
                <CommandButton tool="research_project_show" command="research project show"
                  args={selectedProject ? { project: clean(selectedProject.id) } : {}}
                  disabled={!selectedProject} note="讀取完整譜系"/>
                <CommandButton tool="research_git_log" command="research git log"
                  args={selectedProject ? { project: clean(selectedProject.id) } : {}}
                  disabled={!selectedProject} note="讀取 Git 日誌"/>
              </header>
              {selectedProject && (detail && detail.commits || []).length ? (
                <div className="rv-commits">
                  {(detail.commits || []).map((commit, index) => (
                    <article key={commit.git_sha}>
                      <em>{String(index + 1).padStart(2, "0")}</em>
                      <code>{shortSha(commit.git_sha)}</code>
                      <div><strong>{commit.message}</strong><small>{commit.author_name || "Warehouse OS Research"} · {stamp(commit.created_at)}</small></div>
                      <span>{commit.branch_name}</span>
                    </article>
                  ))}
                </div>
              ) : <EmptyPanel title="尚無提交" copy="每次新增或更新科研文件，都會在這裡留下 Git 提交。"/>}
            </div>
          </div>
        </Band>
        <Band no="02" title="FILE VERSIONS" sub="文件級版本與差異入口">
          {selectedProject && (detail && detail.files || []).length ? (
            <div className="rv-version-register">
              <nav>{(detail.files || []).map((file, index) => (
                <button key={file.id} className={clean(file.id) === clean(fileId) ? "active" : ""}
                  onClick={() => setFileId(clean(file.id))}>
                  <em>{String(index + 1).padStart(2, "0")}</em>
                  <span>{file.logical_path}</span>
                  <b>V{file.current_version}</b>
                </button>
              ))}</nav>
              <section>
                <div className="rv-version-actions">
                  <CommandButton tool="research_file_preview" command="research file preview"
                    args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
                    disabled={!selectedFile} note="閱覽指定文件"/>
                  <CommandButton tool="research_file_diff" command="research file diff"
                    args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
                    disabled={!selectedFile} note="比較最新版本"/>
                  <CommandButton tool="research_file_versions" command="research file versions"
                    args={selectedProject && selectedFile ? { project: clean(selectedProject.id), file: clean(selectedFile.id) } : {}}
                    disabled={!selectedFile} note="讀取不可變版本"/>
                  <button className="btn" onClick={() => selectSection("projects")}>打開閱讀器 →</button>
                </div>
                <div className="rv-version-list">
                  {(selectedFile && selectedFile.versions || []).map(item => (
                    <article key={item.id}>
                      <b>V{item.version}</b>
                      <div><strong>{item.commit_message || "Update research object"}</strong><small>{stamp(item.created_at)}</small></div>
                      <code>{shortSha(item.git_sha)} · {compact(item.size_bytes)}</code>
                    </article>
                  ))}
                </div>
              </section>
            </div>
          ) : <EmptyPanel title="尚無文件版本" copy="先在課題庫提交科研文件，版本資料會自動出現在這裡。"/>}
        </Band>
      </>}

      {section === "formats" && <>
        <section className="rv-format-posters" aria-label="科研格式海報">
          <article><span>08</span><p>FORMATS<br/>ONE<br/>LINEAGE</p><small>READ / DIFF / CITE</small></article>
          <article><b>A</b><p>DOCUMENTS<br/>ARE<br/>EVIDENCE</p><span>DOCX · PDF · HTML</span></article>
          <article><b>Δ</b><p>DATA<br/>MUST<br/>MOVE</p><span>CSV · SQLITE · CODE</span></article>
        </section>
        <Band no="01" title="FORMAT MATRIX" sub="格式感知的閱覽與差異策略">
          <div className="rv-page-command">
            <span>LIVE CONTRACT</span>
            <CommandButton tool="research_formats_list" command="research formats list"
              note="讀取後端實際格式能力"/>
          </div>
          <div className="rv-format-matrix">
            <header><span>FORMAT</span><span>OBJECT CLASS</span><span>INLINE VIEW</span><span>DIFF STRATEGY</span></header>
            {FORMAT_ROWS.map((row, index) => (
              <article key={row[0]}>
                <em>{String(index + 1).padStart(2, "0")}</em>
                <strong>{row[0]}</strong>
                <span>{row[1]}</span>
                <span>{row[2]}</span>
                <span>{row[3]}</span>
              </article>
            ))}
          </div>
        </Band>
        <Band no="02" title="STORAGE CONTRACT" sub="科研資產不是附件箱">
          <div className="rv-contract">
            <article><b>01</b><strong>CONTENT ADDRESS</strong><p>每個版本以 SHA-256 內容地址保存，重複內容不重複佔用。</p></article>
            <article><b>02</b><strong>NATIVE GIT</strong><p>文件版本同步生成 Git commit，可沿課題主分支追溯。</p></article>
            <article><b>03</b><strong>INLINE FIRST</strong><p>優先在系統內閱讀；原文下載是補充，不是唯一入口。</p></article>
            <article><b>04</b><strong>TENANT BOUNDARY</strong><p>課題、對象與內容都按當前公司和科研權限隔離。</p></article>
          </div>
        </Band>
      </>}
    </div>
  );
};

W2.PAGES = W2.PAGES || {};
W2.PAGES.research = Page;
})();
