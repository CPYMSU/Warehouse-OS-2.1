/* WAREHOUSE OS 2.1 · CIVILIZATION
   Swiss views over tenant-owned content. Thought bodies are loaded from the API. */
(() => {
const W2 = window.W2;
const { t, lang } = window.W2_LANG;
const { useEffect, useMemo, useState } = React;

window.W2_LANG.addEN({
  "文明": "Civilization",
  "分享答案之前，先分享我們如何提出問題。": "Before sharing answers, share how we frame the question.",
  "這裡保存觀察世界的方法、判斷事物的尺度，以及思想彼此連接和變化的過程。": "A register of ways to observe the world, scales for judgement, and the paths by which ideas connect and change.",
  "問題拓撲": "Question topology", "思想時間軸": "Idea chronology", "閱讀海報": "Poster reading",
  "記錄一個問題": "Record a question", "篩選": "Filter", "全部": "All", "判斷": "Judgement",
  "技術": "Technology", "組織": "Organization", "時間": "Time", "倫理": "Ethics",
  "搜索問題、方法或角度": "Search questions, methods or lenses", "個對象": "objects",
  "選中": "Selected", "當前問題": "Current question", "連接到": "Connected to",
  "海報閱讀": "Poster reading", "複製分享": "Copy share link", "刪除": "Delete",
  "思想形成": "Idea formation",
  "時間軸不表示思想越來越正確，而是保留問題如何被重新提出、修正和連接。": "The chronology does not claim that ideas become more correct; it preserves how questions are reframed, revised and connected.",
  "換一個角度": "Change the lens", "複製這個思考的鏈接": "Copy this thought link",
  "沒有符合條件的思考對象": "No thought objects match these filters",
  "正在讀取文明資料": "Loading Civilization content", "文明資料讀取失敗": "Civilization content could not be loaded",
  "重新讀取": "Try again", "記錄問題": "Record question", "領域": "Domain", "問題": "Question",
  "一句引子": "Short prompt", "核心判斷": "Core proposition", "保存並發布": "Save and publish",
  "保存後公司成員可見；建立者與公司管理員可刪除。": "Once saved, it is visible to company members; its creator and company administrators can delete it.",
  "取消": "Cancel", "正在保存": "Saving", "問題已發布": "Question published",
  "發布失敗": "Publishing failed", "思想已刪除": "Thought deleted", "刪除失敗": "Deletion failed",
  "確認刪除這個思考？此操作會從公司資料中移除它。": "Delete this thought? It will be removed from company data.",
  "思想鏈接已複製": "Thought link copied", "無法自動複製，請從地址欄複製": "Could not copy automatically; copy it from the address bar",
  "共享觀看方式": "Shared ways of seeing", "提問": "Question", "視角": "Lens", "方法": "Method", "譜系": "Lineage",
  "尚未添加視角": "No lenses have been added yet",
});

const DOMAINS = [
  { key: "all", zh: "全部", en: "All", color: "var(--red)" },
  { key: "judgement", zh: "判斷", en: "Judgement", color: "#D62B20" },
  { key: "technology", zh: "技術", en: "Technology", color: "#174A96" },
  { key: "organization", zh: "組織", en: "Organization", color: "#1F654B" },
  { key: "time", zh: "時間", en: "Time", color: "#9B4F1B" },
  { key: "ethics", zh: "倫理", en: "Ethics", color: "#6B3C78" },
];
const domainOf = key => DOMAINS.find(item => item.key === key) || DOMAINS[1];
const localText = value => {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return lang() === "en" ? (value.en || value.zh || "") : (value.zh || value.en || "");
};
const thoughtText = (thought, key) => localText(thought && thought[key]);
const thoughtLenses = thought => Array.isArray(thought && thought.lenses) ? thought.lenses : [];
const thoughtRelations = thought => Array.isArray(thought && thought.relations) ? thought.relations : [];
const memoryKey = () => {
  const actor = window.W2_USER || {};
  const identity = actor.global_user_id || actor.id || actor.username || "anonymous";
  return "w2_civilization:v1:" + encodeURIComponent(W2.tenant ? W2.tenant() : "default") + ":" + encodeURIComponent(identity);
};
const readMemory = () => {
  try {
    const value = JSON.parse(localStorage.getItem(memoryKey()) || "{}");
    return value && typeof value === "object" ? value : {};
  } catch (_error) { return {}; }
};
const writeMemory = value => {
  try { localStorage.setItem(memoryKey(), JSON.stringify(value)); } catch (_error) {}
};
const routeParams = () => {
  const query = String(location.hash || "").split("?", 2)[1] || "";
  return new URLSearchParams(query);
};
const PosterQuestion = ({ children }) => <>{String(children || "").split(/([，,？?])/).map((part, index) => /[，,？?]/.test(part) ? <em key={index}>{part}</em> : <React.Fragment key={index}>{part}</React.Fragment>)}</>;

const CivilizationComposer = ({ busy, error, onClose, onSave }) => {
  useEffect(() => {
    const close = event => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [busy, onClose]);
  const submit = event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave({
      domain: String(form.get("domain") || "judgement"),
      title: String(form.get("title") || "").trim(),
      short: String(form.get("short") || "").trim(),
      thesis: String(form.get("thesis") || "").trim(),
      locale: lang(),
    });
  };
  return <div className="civ-composer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <form className="civ-composer-card" role="dialog" aria-modal="true" aria-labelledby="civ-composer-title" onSubmit={submit}>
      <header className="civ-composer-head"><b>C1</b><div><span className="civ-eyebrow">NEW THOUGHT OBJECT</span><h2 id="civ-composer-title">{t("記錄問題")}</h2></div><button type="button" disabled={busy} className="civ-composer-close" onClick={onClose} aria-label={t("取消")}>×</button></header>
      <div className="civ-composer-body">
        <label>{t("領域")}<select name="domain" defaultValue="judgement">{DOMAINS.slice(1).map(domain => <option key={domain.key} value={domain.key}>{lang() === "en" ? domain.en : t(domain.zh)}</option>)}</select></label>
        <label>{t("一句引子")}<input name="short" maxLength="180" required/></label>
        <label className="is-wide">{t("問題")}<input name="title" maxLength="160" autoFocus required/></label>
        <label className="is-wide">{t("核心判斷")}<textarea name="thesis" maxLength="1200" required/></label>
        {error && <div className="civ-composer-error is-wide" role="alert">{error}</div>}
      </div>
      <footer className="civ-composer-foot"><span>{t("保存後公司成員可見；建立者與公司管理員可刪除。")}</span><button type="submit" disabled={busy}>{busy ? t("正在保存") : t("保存並發布")}</button></footer>
    </form>
  </div>;
};

const Page = () => {
  const initialMemory = useMemo(readMemory, []);
  const params = useMemo(routeParams, []);
  const [view, setView] = useState(["a", "b", "c"].includes(params.get("view")) ? params.get("view") : (initialMemory.view || "a"));
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(params.get("thought") || initialMemory.selected || "");
  const [lens, setLens] = useState(0);
  const [thoughts, setThoughts] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [composer, setComposer] = useState(false);
  const [composerBusy, setComposerBusy] = useState(false);
  const [composerError, setComposerError] = useState("");
  const [toast, setToast] = useState("");

  const loadThoughts = async () => {
    setLoadError("");
    try {
      const data = await W2.json("/api/civilization/thoughts", { cache: "no-store" });
      setThoughts(Array.isArray(data.thoughts) ? data.thoughts : []);
    } catch (error) {
      setThoughts([]);
      setLoadError(error.message || t("文明資料讀取失敗"));
    }
  };
  useEffect(() => { loadThoughts(); }, []);

  const allThoughts = thoughts || [];
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return allThoughts.filter(thought => {
      if (filter !== "all" && thought.domain !== filter) return false;
      if (!needle) return true;
      const haystack = [thoughtText(thought, "title"), thoughtText(thought, "short"), thoughtText(thought, "thesis"), ...thoughtRelations(thought).map(localText), ...thoughtLenses(thought).flatMap(item => [localText(item.name), localText(item.text)])].join(" ").toLowerCase();
      return haystack.includes(needle);
    });
  }, [allThoughts, filter, query]);
  const selected = allThoughts.find(item => item.id === selectedId) || visible[0] || allThoughts[0] || null;
  const selectedDomain = domainOf(selected && selected.domain);
  const selectedLenses = thoughtLenses(selected);

  useEffect(() => {
    if (visible.length && !visible.some(item => item.id === selectedId)) setSelectedId(visible[0].id);
  }, [visible, selectedId]);
  useEffect(() => { setLens(0); }, [selectedId]);
  useEffect(() => { writeMemory({ view, selected: selectedId, updated_at: new Date().toISOString() }); }, [view, selectedId]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 1900);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const selectThought = (id, nextView) => { setSelectedId(id); if (nextView) setView(nextView); };
  const copyLink = async thought => {
    const link = location.href.split("#", 1)[0] + "#/civilization?view=" + encodeURIComponent(view) + "&thought=" + encodeURIComponent(thought.id);
    try { await navigator.clipboard.writeText(link); setToast(t("思想鏈接已複製")); }
    catch (_error) { setToast(t("無法自動複製，請從地址欄複製")); }
  };
  const saveThought = async value => {
    setComposerBusy(true); setComposerError("");
    try {
      const result = await W2.post("/api/civilization/thoughts", value);
      const created = { ...result.thought, no: String(allThoughts.length + 1).padStart(2, "0") };
      setThoughts(current => (current || []).concat(created));
      setSelectedId(created.id); setComposer(false); setToast(t("問題已發布"));
    } catch (error) { setComposerError(error.message || t("發布失敗")); }
    finally { setComposerBusy(false); }
  };
  const removeThought = async thought => {
    if (!thought.can_delete || !window.confirm(t("確認刪除這個思考？此操作會從公司資料中移除它。"))) return;
    try {
      await W2.json("/api/civilization/thoughts/" + encodeURIComponent(thought.id), { method: "DELETE" });
      setThoughts(current => (current || []).filter(item => item.id !== thought.id));
      setSelectedId(""); setToast(t("思想已刪除"));
    } catch (error) { setToast((error.message || t("刪除失敗"))); }
  };

  if (thoughts === null) return <div className="civilization-page"><div className="civ-empty">{t("正在讀取文明資料")}…</div></div>;

  const atlas = <div className="civ-atlas-layout">
    <div className="civ-atlas-register">
      <div className="civ-register-head"><span>NO.</span><span>DOMAIN</span><span>QUESTION / OBJECT</span><span>RELATION</span><span>TIME</span></div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : visible.map(thought => {
        const domain = domainOf(thought.domain);
        return <button type="button" className="civ-thought-row" key={thought.id} aria-selected={selected && thought.id === selected.id} onClick={() => selectThought(thought.id)}>
          <span className="civ-row-no">{thought.no}</span>
          <span className="civ-row-domain" style={{ "--civ-signal": domain.color }}><i/>{lang() === "en" ? domain.en : t(domain.zh)}<br/>{domain.en.toUpperCase()}</span>
          <span className="civ-row-copy"><small>QUESTION OBJECT</small><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span>
          <span className="civ-row-links"><small>{t("連接到").toUpperCase()}</small><b>{thoughtRelations(thought).map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thoughtRelations(thought).length - 1 && <br/>}</React.Fragment>)}</b></span>
          <span className="civ-row-year">{thought.year}</span>
        </button>;
      })}
    </div>
    {selected && <aside className="civ-atlas-detail" style={{ "--civ-signal": selectedDomain.color }}>
      <div className="civ-detail-meta"><span>{selectedDomain.en.toUpperCase()} / {selected.date}</span><span>{t("選中").toUpperCase()}</span></div>
      <div className="civ-detail-no">{selected.no}</div><span className="civ-micro">{t("當前問題")}</span>
      <h2>{thoughtText(selected, "title")}</h2><p>{thoughtText(selected, "thesis")}</p>
      <div className="civ-detail-actions"><button type="button" onClick={() => setView("c")}>{t("海報閱讀")} →</button><button type="button" onClick={() => selected.can_delete ? removeThought(selected) : copyLink(selected)}>{selected.can_delete ? t("刪除") : t("複製分享")} ↗</button></div>
    </aside>}
  </div>;

  const chronology = <div className="civ-chronology">
    <aside className="civ-chronology-side"><span className="civ-micro">CHRONOLOGY / {t("思想形成")}</span><strong>{visible.length}×</strong><p>{t("時間軸不表示思想越來越正確，而是保留問題如何被重新提出、修正和連接。")}</p><div className="civ-chronology-legend">○ FIRST QUESTION<br/>□ REVISED LENS<br/>— RELATED THOUGHT<br/>● CURRENT READING</div></aside>
    <div className="civ-timeline"><div className="civ-timeline-axis">{["2021", "2022", "2023", "2024", "2025", "2026"].map(year => <span key={year}>{year}</span>)}</div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <ol className="civ-timeline-list">{visible.map(thought => <li className="civ-timeline-item" key={thought.id}><time className="civ-timeline-date">{thought.date}</time><div className="civ-timeline-node"><button type="button" aria-selected={selected && thought.id === selected.id} onClick={() => selectThought(thought.id)}><span><span className="civ-eyebrow">{domainOf(thought.domain).en.toUpperCase()} · QUESTION OBJECT</span><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span><aside>{thoughtRelations(thought).map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thoughtRelations(thought).length - 1 && <br/>}</React.Fragment>)}</aside></button></div></li>)}</ol>}
    </div>
  </div>;

  const reader = !selected ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <div className="civ-reader">
    <nav className="civ-reader-rail" aria-label={t("問題")}>{visible.map(thought => <button type="button" key={thought.id} className={thought.id === selected.id ? "is-active" : ""} onClick={() => selectThought(thought.id)}>{thought.no} · {domainOf(thought.domain).en.toUpperCase()}</button>)}</nav>
    <article className="civ-reader-poster"><div className="civ-poster-label"><span>CIVILIZATION · QUESTION {selected.no}</span><span>{selectedDomain.en.toUpperCase()}</span></div><h2 className="civ-poster-question"><PosterQuestion>{thoughtText(selected, "title")}</PosterQuestion></h2><p className="civ-poster-thesis">{thoughtText(selected, "thesis")}</p><footer className="civ-poster-foot"><span>ONE QUESTION · MANY LENSES</span><span>{selected.date}</span></footer></article>
    <aside className="civ-reader-notes"><span className="civ-micro">CHANGE THE LENS / {t("換一個角度")}</span><h3>{thoughtText(selected, "title")}</h3><p>{thoughtText(selected, "short")}</p><div className="civ-lens-list">{selectedLenses.length ? selectedLenses.map((item, index) => <button type="button" key={index} className={lens === index ? "is-active" : ""} onClick={() => setLens(index)}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{localText(item.name)}</strong><br/>{localText(item.text)}</span></button>) : <div className="civ-empty">{t("尚未添加視角")}</div>}</div><button type="button" className="civ-read-action" onClick={() => selected.can_delete ? removeThought(selected) : copyLink(selected)}>{selected.can_delete ? t("刪除") : t("複製這個思考的鏈接")} →</button></aside>
  </div>;

  return <div className="civilization-page">
    <header className="civ-toolbar"><div className="civ-toolbar-brand"><span className="civ-toolbar-mark" aria-hidden="true"/><span>BONFIRE PLATFORM<br/>CIVILIZATION / {t("文明")}</span></div><nav className="civ-view-switch" aria-label={t("閱讀海報")}>{[["a", "問題拓撲"], ["b", "思想時間軸"], ["c", "閱讀海報"]].map(([id, label]) => <button type="button" key={id} aria-selected={view === id} onClick={() => setView(id)}>{id.toUpperCase()} {t(label)}</button>)}</nav><div className="civ-toolbar-right"><span>{String(allThoughts.length).padStart(2, "0")} QUESTIONS · {String(allThoughts.reduce((sum, item) => sum + thoughtLenses(item).length, 0)).padStart(2, "0")} LENSES</span><button type="button" className="civ-new-button" onClick={() => { setComposerError(""); setComposer(true); }}>＋ {t("記錄一個問題")}</button></div></header>
    <section className="civ-masthead"><div className="civ-mast-copy"><span className="civ-kicker">MODULE C1 · {t("共享觀看方式").toUpperCase()}</span><h1 className="civ-mast-title">{t("文明")}<span>CIVILIZATION</span></h1><p className="civ-mast-lead">{t("分享答案之前，先分享我們如何提出問題。")} {t("這裡保存觀察世界的方法、判斷事物的尺度，以及思想彼此連接和變化的過程。")}</p></div><aside className="civ-mast-index"><span className="civ-micro">LIVE INDEX / {new Date().getFullYear()}</span><strong>C1</strong><p>{t("提問").toUpperCase()}<br/>{t("視角").toUpperCase()}<br/>{t("方法").toUpperCase()}<br/>{t("譜系").toUpperCase()}</p></aside></section>
    <section className="civ-filters"><div className="civ-filter-label"><b>FILTER / {t("篩選")}</b><small>{String(visible.length).padStart(2, "0")} {t("個對象").toUpperCase()}</small></div><div className="civ-filter-buttons" role="group" aria-label={t("篩選")}>{DOMAINS.map(domain => <button type="button" key={domain.key} className={filter === domain.key ? "is-active" : ""} onClick={() => setFilter(domain.key)}>{lang() === "en" ? domain.en : t(domain.zh)}</button>)}</div><label className="civ-search"><span>⌕</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={t("搜索問題、方法或角度")}/></label></section>
    {loadError && <div className="civ-load-error" role="alert"><span>{t("文明資料讀取失敗")}: {loadError}</span><button type="button" onClick={loadThoughts}>{t("重新讀取")}</button></div>}
    <main className="civ-view">{view === "a" ? atlas : view === "b" ? chronology : reader}</main>
    <footer className="civ-footer"><span>INFORMATION BEFORE DECORATION</span><span>LIST ↔ LINEAGE ↔ READING</span></footer>
    {composer && <CivilizationComposer busy={composerBusy} error={composerError} onClose={() => setComposer(false)} onSave={saveThought}/>} {toast && <div className="civ-toast" role="status">{toast}</div>}
  </div>;
};

window.W2.PAGES["civilization"] = Page;
})();
