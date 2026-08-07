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
  "保存後公司成員可見；建立者與公司管理員可繼續編輯。": "Once saved, it is visible to company members; its creator and company administrators can continue editing it.",
  "取消": "Cancel", "正在保存": "Saving", "問題已發布": "Question published",
  "發布失敗": "Publishing failed", "思想已刪除": "Thought deleted", "刪除失敗": "Deletion failed",
  "確認刪除這個思考？此操作會從公司資料中移除它。": "Delete this thought? It will be removed from company data.",
  "思想鏈接已複製": "Thought link copied", "無法自動複製，請從地址欄複製": "Could not copy automatically; copy it from the address bar",
  "共享觀看方式": "Shared ways of seeing", "提問": "Question", "視角": "Lens", "方法": "Method", "譜系": "Lineage",
  "尚未添加視角": "No lenses have been added yet",
  "編輯": "Edit", "編輯思考": "Edit thought", "保存修改": "Save changes", "內容已更新": "Content updated",
  "更新失敗": "Update failed", "添加視角": "Add lens", "視角名稱": "Lens name", "視角說明": "Lens description",
  "移除": "Remove", "最多可添加 12 個視角。": "Up to 12 lenses can be added.",
  "思想關聯": "Thought relations", "添加關聯": "Add relation", "關聯文字": "Relation label",
  "關聯顯示於問題拓撲與時間軸；最多 12 條。": "Relations appear in question topology and chronology; up to 12 may be added.",
  "尚未添加關聯": "No relations have been added yet", "例如：一種長期主義": "For example: a form of long-termism",
  "內容已被其他人更新，請重新打開後再編輯。": "Someone else updated this content. Reopen it before editing again.",
  "保存草稿": "Save draft", "草稿已保存": "Draft saved", "發布這一版": "Publish this version",
  "字符與正文": "Characters & body", "版面固定為 Swiss B；你可以編輯其中的全部字符與正文區段。": "The Swiss B layout is locked; every character and body section remains editable.",
  "刊頭文字": "Eyebrow", "分類文字": "Category label", "閱讀引語": "Reading quote",
  "正文區段": "Body sections", "添加區段": "Add section", "區段標記": "Section marker",
  "英文提示": "English kicker", "區段標題": "Section heading", "段落正文": "Paragraphs",
  "段落之間空一行。": "Leave one blank line between paragraphs.", "頁尾左側": "Footer left", "頁尾右側": "Footer right",
  "文明 CLI / API": "Civilization CLI / API", "草稿": "Draft", "已發布": "Published",
  "發布版本": "Published revision", "固定版面": "Locked layout", "正在發布": "Publishing",
  "收起閱讀工具欄": "Collapse reading tools", "展開閱讀工具欄": "Open reading tools",
  "分享": "Share", "公開網頁": "Public page", "私有": "Private", "已公開": "Public",
  "開啟公開分享": "Enable public sharing", "關閉公開分享": "Disable public sharing",
  "複製公開鏈接": "Copy public link", "打開公開網頁": "Open public page", "PNG 明信片": "PNG postcard",
  "只有正式發布的內容會公開；草稿永遠不會進入公開頁。": "Only published content is public; drafts never enter the public page.",
  "關閉後，原公開鏈接會立即失效。": "After disabling it, the existing public link stops working immediately.",
  "分享設定已更新": "Sharing settings updated", "分享設定失敗": "Could not update sharing settings",
  "公開鏈接已複製": "Public link copied", "請先發布這篇文章，再開啟公開分享。": "Publish this post before enabling public sharing.",
  "生成明信片不會上傳內容，由瀏覽器直接產生 PNG。": "The postcard is generated directly in your browser without uploading its content.",
  "公開分享狀態": "Public sharing status", "系統分享": "System share",
});

const DOMAINS = [
  { key: "all", zh: "全部", en: "All", color: "#D62B20", accent: "#F3CE1D", ink: "#141414", pale: "#F4F0E7" },
  { key: "judgement", zh: "判斷", en: "Judgement", color: "#D62B20", accent: "#F3CE1D", ink: "#211A17", pale: "#F7E8D8" },
  { key: "technology", zh: "技術", en: "Technology", color: "#1656A3", accent: "#64D1D4", ink: "#092840", pale: "#DDEDF2" },
  { key: "organization", zh: "組織", en: "Organization", color: "#17694E", accent: "#F1C928", ink: "#102B22", pale: "#DCEBE1" },
  { key: "time", zh: "時間", en: "Time", color: "#B45418", accent: "#F1CF75", ink: "#3A2416", pale: "#F4E8D8" },
  { key: "ethics", zh: "倫理", en: "Ethics", color: "#6C3D8E", accent: "#F0A4C2", ink: "#28172E", pale: "#EDE1F0" },
];
const domainOf = key => DOMAINS.find(item => item.key === key) || DOMAINS[1];
const domainStyle = domain => ({
  "--civ-signal": domain.color,
  "--civ-accent": domain.accent,
  "--civ-domain-ink": domain.ink,
  "--civ-domain-pale": domain.pale,
});
const localText = value => {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return lang() === "en" ? (value.en || value.zh || "") : (value.zh || value.en || "");
};
const thoughtText = (thought, key) => localText(thought && thought[key]);
const thoughtLenses = thought => Array.isArray(thought && thought.lenses) ? thought.lenses : [];
const thoughtRelations = thought => Array.isArray(thought && thought.relations) ? thought.relations : [];
const contentLocale = (thought, includeDraft = false) => {
  const source = includeDraft && thought && thought.draft_content ? thought.draft_content : thought && thought.content;
  const locales = source && source.locales && typeof source.locales === "object" ? source.locales : {};
  const value = lang() === "en" ? (locales.en || locales.zh) : (locales.zh || locales.en);
  if (value && typeof value === "object") return value;
  return {
    eyebrow: "CIVILIZATION · QUESTION",
    category_label: String(thought && thought.domain || "judgement").toUpperCase(),
    title: thoughtText(thought, "title"), short: thoughtText(thought, "short"), thesis: thoughtText(thought, "thesis"),
    quote: thoughtText(thought, "short"), sections: [],
    footer_left: "12 COLUMN SYSTEM · ONE QUESTION / MANY LENSES", footer_right: "INFORMATION BEFORE DECORATION",
  };
};
const proseParagraphs = value => {
  const source = String(value || "").trim();
  if (!source) return [];
  const explicit = source.split(/\n\s*\n/).map(part => part.trim()).filter(Boolean);
  if (explicit.length > 1) return explicit;
  const sentences = source.match(/[^。！？.!?]+[。！？.!?]?/g) || [source];
  const paragraphs = [];
  for (let index = 0; index < sentences.length; index += 2) paragraphs.push(sentences.slice(index, index + 2).join("").trim());
  return paragraphs.filter(Boolean);
};
const readingSections = content => {
  if (Array.isArray(content.sections) && content.sections.length) return content.sections;
  const source = String(content.thesis || "").trim();
  const stages = source.split(/(?=(?:20|30|40|50|60)岁)/).map(part => part.trim()).filter(Boolean);
  if (stages.length > 1) return stages.map((part, index) => {
    const age = part.match(/^(20|30|40|50|60)岁/);
    const stop = part.search(/[。！？.!?]/);
    const heading = stop >= 0 ? part.slice(0, stop + 1) : (age ? `${age[1]}岁` : content.short);
    const body = stop >= 0 ? part.slice(stop + 1).trim() : part;
    return { marker: age ? age[1] : String(index).padStart(2, "0"), kicker: age ? "LIFE / NETWORK" : "PROPOSITION / 核心判断", heading, paragraphs: proseParagraphs(body || part) };
  });
  return [{ marker: "00", kicker: "PROPOSITION / 核心判断", heading: content.short || content.title, paragraphs: proseParagraphs(source) }];
};
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
const DomainGlyph = ({ domain, large = false }) => <span className={`civ-domain-glyph is-${domain.key}${large ? " is-large" : ""}`} style={domainStyle(domain)} aria-hidden="true"><i/><i/><i/><i/></span>;
const PosterMotion = ({ domain }) => <div className={`civ-poster-motion is-${domain.key}`} style={domainStyle(domain)} aria-hidden="true"><i/><i/><i/><i/><b>{domain.en.slice(0, 3).toUpperCase()}</b></div>;

const CivilizationComposer = ({ busy, error, initial, onClose, onSave }) => {
  const editing = !!initial;
  const [domainKey, setDomainKey] = useState(initial ? initial.domain : "judgement");
  const [relations, setRelations] = useState(() => thoughtRelations(initial).map(localText));
  const [lenses, setLenses] = useState(() => thoughtLenses(initial).map(item => ({ name: localText(item.name), text: localText(item.text) })));
  const editorContent = contentLocale(initial, true);
  const [sections, setSections] = useState(() => (Array.isArray(editorContent.sections) ? editorContent.sections : []).map(item => ({ ...item, paragraphs: Array.isArray(item.paragraphs) ? item.paragraphs.join("\n\n") : String(item.paragraphs || "") })));
  const composerDomain = domainOf(domainKey);
  useEffect(() => {
    const close = event => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [busy, onClose]);
  const submit = event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const intent = event.nativeEvent && event.nativeEvent.submitter ? event.nativeEvent.submitter.value : "draft";
    onSave({
      domain: String(form.get("domain") || "judgement"),
      content: {
        eyebrow: String(form.get("eyebrow") || "").trim(), category_label: String(form.get("category_label") || "").trim(),
        title: String(form.get("title") || "").trim(), short: String(form.get("short") || "").trim(),
        thesis: String(form.get("thesis") || "").trim(), quote: String(form.get("quote") || "").trim(),
        sections: sections.map(item => ({ marker: String(item.marker || "").trim(), kicker: String(item.kicker || "").trim(), heading: String(item.heading || "").trim(), paragraphs: String(item.paragraphs || "").split(/\n\s*\n/).map(part => part.trim()).filter(Boolean) })),
        footer_left: String(form.get("footer_left") || "").trim(), footer_right: String(form.get("footer_right") || "").trim(),
      },
      relations: relations.map(item => item.trim()).filter(Boolean),
      lenses: lenses.map(item => ({ name: item.name.trim(), text: item.text.trim() })),
      locale: lang(),
      ...(editing ? { expected_revision: initial.revision } : {}),
    }, initial, intent === "publish");
  };
  const changeRelation = (index, value) => setRelations(current => current.map((item, itemIndex) => itemIndex === index ? value : item));
  const changeLens = (index, key, value) => setLenses(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item));
  const changeSection = (index, key, value) => setSections(current => current.map((item, itemIndex) => itemIndex === index ? { ...item, [key]: value } : item));
  return <div className="civ-composer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <form className="civ-composer-card" role="dialog" aria-modal="true" aria-labelledby="civ-composer-title" onSubmit={submit}>
      <header className="civ-composer-head"><b>C1</b><div><span className="civ-eyebrow">{editing ? "REVISE THOUGHT OBJECT" : "NEW THOUGHT OBJECT"}</span><h2 id="civ-composer-title">{editing ? t("編輯思考") : t("記錄問題")}</h2></div><button type="button" disabled={busy} className="civ-composer-close" onClick={onClose} aria-label={t("取消")}>×</button></header>
      <div className="civ-composer-body">
        <label>{t("領域")}<select name="domain" value={domainKey} onChange={event => setDomainKey(event.target.value)}>{DOMAINS.slice(1).map(domain => <option key={domain.key} value={domain.key}>{lang() === "en" ? domain.en : t(domain.zh)}</option>)}</select></label>
        <div className="civ-composer-domain" data-domain={composerDomain.key} style={domainStyle(composerDomain)}><DomainGlyph domain={composerDomain}/><span><b>{lang() === "en" ? composerDomain.en : t(composerDomain.zh)}</b><small>{composerDomain.en.toUpperCase()} POSTER SYSTEM</small></span></div>
        <div className="civ-template-contract is-wide"><b>SWISS B / INTERNATIONAL GRID</b><span>{t("版面固定為 Swiss B；你可以編輯其中的全部字符與正文區段。")}</span></div>
        <label>{t("刊頭文字")}<input name="eyebrow" maxLength="100" defaultValue={editorContent.eyebrow || "CIVILIZATION · QUESTION"}/></label>
        <label>{t("分類文字")}<input name="category_label" maxLength="80" defaultValue={editorContent.category_label || composerDomain.en.toUpperCase()}/></label>
        <label className="is-wide">{t("問題")}<textarea className="civ-title-input" name="title" maxLength="400" defaultValue={editorContent.title || ""} autoFocus required/></label>
        <label>{t("一句引子")}<textarea name="short" maxLength="800" defaultValue={editorContent.short || ""} required/></label>
        <label>{t("閱讀引語")}<textarea name="quote" maxLength="1200" defaultValue={editorContent.quote || editorContent.short || ""}/></label>
        <label className="is-wide">{t("核心判斷")}<textarea className="civ-thesis-input" name="thesis" maxLength="60000" defaultValue={editorContent.thesis || ""} required/></label>
        <section className="civ-section-editor is-wide"><header><span><b>{t("正文區段")}</b><small>{t("段落之間空一行。")}</small></span><button type="button" disabled={busy || sections.length >= 24} onClick={() => setSections(current => current.concat({ marker: String(current.length).padStart(2, "0"), kicker: "", heading: "", paragraphs: "" }))}>＋ {t("添加區段")}</button></header>{sections.map((item, index) => <div className="civ-section-editor-row" key={index}><b>{String(index + 1).padStart(2, "0")}</b><div className="civ-section-meta"><label>{t("區段標記")}<input value={item.marker || ""} maxLength="20" onChange={event => changeSection(index, "marker", event.target.value)}/></label><label>{t("英文提示")}<input value={item.kicker || ""} maxLength="80" onChange={event => changeSection(index, "kicker", event.target.value)}/></label></div><label>{t("區段標題")}<textarea value={item.heading || ""} maxLength="300" onChange={event => changeSection(index, "heading", event.target.value)} required/></label><label>{t("段落正文")}<textarea className="civ-section-paragraphs" value={item.paragraphs || ""} maxLength="60000" onChange={event => changeSection(index, "paragraphs", event.target.value)} required/></label><button type="button" disabled={busy} onClick={() => setSections(current => current.filter((_item, itemIndex) => itemIndex !== index))}>{t("移除")}</button></div>)}</section>
        <label>{t("頁尾左側")}<input name="footer_left" maxLength="120" defaultValue={editorContent.footer_left || "12 COLUMN SYSTEM · ONE QUESTION / MANY LENSES"}/></label>
        <label>{t("頁尾右側")}<input name="footer_right" maxLength="120" defaultValue={editorContent.footer_right || "INFORMATION BEFORE DECORATION"}/></label>
        <section className="civ-relation-editor is-wide" data-testid="civilization-relations-editor"><header><span><b>{t("思想關聯")}</b><small>{t("關聯顯示於問題拓撲與時間軸；最多 12 條。")}</small></span><button type="button" disabled={busy || relations.length >= 12} onClick={() => setRelations(current => current.concat(""))}>＋ {t("添加關聯")}</button></header>{relations.length ? relations.map((item, index) => <div className="civ-relation-editor-row" key={index}><b>{String(index + 1).padStart(2, "0")}</b><label>{t("關聯文字")}<input value={item} maxLength="160" onChange={event => changeRelation(index, event.target.value)} placeholder={t("例如：一種長期主義")}/></label><button type="button" disabled={busy} onClick={() => setRelations(current => current.filter((_item, itemIndex) => itemIndex !== index))}>{t("移除")}</button></div>) : <div className="civ-relation-empty">{t("尚未添加關聯")}</div>}</section>
        <section className="civ-lens-editor is-wide"><header><span><b>{t("視角")}</b><small>{t("最多可添加 12 個視角。")}</small></span><button type="button" disabled={busy || lenses.length >= 12} onClick={() => setLenses(current => current.concat({ name: "", text: "" }))}>＋ {t("添加視角")}</button></header>{lenses.map((item, index) => <div className="civ-lens-editor-row" key={index}><b>{String(index + 1).padStart(2, "0")}</b><label>{t("視角名稱")}<input value={item.name} maxLength="80" onChange={event => changeLens(index, "name", event.target.value)} required/></label><label>{t("視角說明")}<textarea value={item.text} maxLength="500" onChange={event => changeLens(index, "text", event.target.value)} required/></label><button type="button" disabled={busy} onClick={() => setLenses(current => current.filter((_item, itemIndex) => itemIndex !== index))}>{t("移除")}</button></div>)}</section>
        {error && <div className="civ-composer-error is-wide" role="alert">{error}</div>}
      </div>
      <footer className="civ-composer-foot"><span>{t("保存後公司成員可見；建立者與公司管理員可繼續編輯。")}</span><div><button type="submit" name="intent" value="draft" disabled={busy}>{busy ? t("正在保存") : t("保存草稿")}</button><button type="submit" name="intent" value="publish" className="is-publish" disabled={busy}>{busy ? t("正在發布") : t("發布這一版")}</button></div></footer>
    </form>
  </div>;
};

const CivilizationSharePanel = ({ thought, busy, error, onClose, onToggle, onToast }) => {
  const domain = domainOf(thought.domain);
  const content = contentLocale(thought);
  const publicUrl = thought.public_path ? location.origin + thought.public_path : "";
  useEffect(() => {
    const close = event => { if (event.key === "Escape" && !busy) onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [busy, onClose]);
  const copyPublicUrl = async () => {
    if (!publicUrl) return;
    try { await navigator.clipboard.writeText(publicUrl); onToast(t("公開鏈接已複製")); }
    catch (_error) { onToast(t("無法自動複製，請從地址欄複製")); }
  };
  const downloadPostcard = () => {
    if (!window.CivilizationPostcard) return onToast(t("分享設定失敗"));
    window.CivilizationPostcard.download(thought, publicUrl, lang());
  };
  const systemShare = () => {
    if (!navigator.share || !publicUrl) return;
    navigator.share({ title: String(content.title || thoughtText(thought, "title") || "Civilization"), text: String(content.short || ""), url: publicUrl }).catch(() => {});
  };
  const published = thought.publication_status === "published";
  return <div className="civ-share" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose(); }}>
    <section className="civ-share-card" role="dialog" aria-modal="true" aria-labelledby="civ-share-title" data-domain={domain.key} style={domainStyle(domain)}>
      <header className="civ-share-head"><b>S1</b><div><span className="civ-eyebrow">PUBLIC PAGE / BROWSER POSTCARD</span><h2 id="civ-share-title">{t("分享")}</h2></div><button type="button" disabled={busy} onClick={onClose} aria-label={t("取消")}>×</button></header>
      <div className="civ-share-body">
        <div className="civ-share-status"><span>{t("公開分享狀態")}</span><strong className={thought.public_share_enabled ? "is-public" : ""}>{t(thought.public_share_enabled ? "已公開" : "私有")}</strong><i aria-hidden="true"/></div>
        <div className="civ-share-title"><span>{String(thought.no || "00")} · {domain.en.toUpperCase()}</span><h3>{content.title || thoughtText(thought, "title")}</h3><p>{t("只有正式發布的內容會公開；草稿永遠不會進入公開頁。")}</p></div>
        {publicUrl ? <div className="civ-share-url"><span>{t("公開網頁")}</span><code>{publicUrl}</code></div> : <div className="civ-share-private"><b>PRIVATE / NOT INDEXED</b><span>{published ? t("開啟公開分享") : t("請先發布這篇文章，再開啟公開分享。")}</span></div>}
        <div className="civ-share-actions">
          {publicUrl && <button type="button" onClick={copyPublicUrl}>{t("複製公開鏈接")} ↗</button>}
          {publicUrl && <button type="button" onClick={() => window.open(publicUrl, "_blank", "noopener,noreferrer")}>{t("打開公開網頁")} ↗</button>}
          <button type="button" className="is-postcard" onClick={downloadPostcard}>{t("PNG 明信片")} ↓</button>
          {publicUrl && navigator.share && <button type="button" onClick={systemShare}>{t("系統分享")} ↗</button>}
        </div>
        <p className="civ-share-note">{t("生成明信片不會上傳內容，由瀏覽器直接產生 PNG。")} {thought.public_share_enabled && t("關閉後，原公開鏈接會立即失效。")}</p>
        {error && <div className="civ-share-error" role="alert">{error}</div>}
      </div>
      <footer className="civ-share-foot"><span>SWISS B / SHARE CONTRACT V1</span>{thought.can_edit ? <button type="button" className={thought.public_share_enabled ? "is-disable" : "is-enable"} disabled={busy || (!published && !thought.public_share_enabled)} onClick={() => onToggle(!thought.public_share_enabled)}>{busy ? t("正在保存") : t(thought.public_share_enabled ? "關閉公開分享" : "開啟公開分享")}</button> : <button type="button" onClick={onClose}>{t("取消")}</button>}</footer>
    </section>
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
  const [notesOpen, setNotesOpen] = useState(initialMemory.notes_open !== false);
  const [thoughts, setThoughts] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [composer, setComposer] = useState(null);
  const [composerBusy, setComposerBusy] = useState(false);
  const [composerError, setComposerError] = useState("");
  const [shareId, setShareId] = useState("");
  const [shareBusy, setShareBusy] = useState(false);
  const [shareError, setShareError] = useState("");
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
  const activeDomain = selected || filter === "all" ? selectedDomain : domainOf(filter);
  const selectedLenses = thoughtLenses(selected);
  const selectedContent = contentLocale(selected);
  const selectedReadingSections = readingSections(selectedContent);
  const shareThought = allThoughts.find(item => item.id === shareId) || null;

  useEffect(() => {
    if (visible.length && !visible.some(item => item.id === selectedId)) setSelectedId(visible[0].id);
  }, [visible, selectedId]);
  useEffect(() => { setLens(0); }, [selectedId]);
  useEffect(() => { writeMemory({ view, selected: selectedId, notes_open: notesOpen, updated_at: new Date().toISOString() }); }, [view, selectedId, notesOpen]);
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(""), 1900);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const selectThought = (id, nextView) => { setSelectedId(id); if (nextView) setView(nextView); };
  const openShare = thought => { setShareError(""); setShareId(thought.id); };
  const copyLink = async thought => {
    const link = location.href.split("#", 1)[0] + "#/civilization?view=" + encodeURIComponent(view) + "&thought=" + encodeURIComponent(thought.id);
    try { await navigator.clipboard.writeText(link); setToast(t("思想鏈接已複製")); }
    catch (_error) { setToast(t("無法自動複製，請從地址欄複製")); }
  };
  const saveThought = async (value, initial, publish) => {
    setComposerBusy(true); setComposerError("");
    try {
      if (initial) {
        const result = await W2.json("/api/civilization/thoughts/" + encodeURIComponent(initial.id) + "/draft", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(value),
        });
        const finalResult = publish ? await W2.post("/api/civilization/thoughts/" + encodeURIComponent(initial.id) + "/publish", { expected_revision: result.thought.revision }) : result;
        setThoughts(current => (current || []).map(item => item.id === initial.id ? finalResult.thought : item));
        setSelectedId(finalResult.thought.id); setComposer(null); setToast(t(publish ? "問題已發布" : "草稿已保存"));
      } else {
        const result = await W2.post("/api/civilization/thoughts", { ...value, publish });
        setThoughts(current => (current || []).concat(result.thought));
        setSelectedId(result.thought.id); setComposer(null); setToast(t(publish ? "問題已發布" : "草稿已保存"));
      }
    } catch (error) { setComposerError(error.status === 409 ? t("內容已被其他人更新，請重新打開後再編輯。") : (error.message || t(initial ? "更新失敗" : "發布失敗"))); }
    finally { setComposerBusy(false); }
  };
  const removeThought = async thought => {
    if (!thought.can_delete || !window.confirm(t("確認刪除這個思考？此操作會從公司資料中移除它。"))) return;
    try {
      await W2.json("/api/civilization/thoughts/" + encodeURIComponent(thought.id), { method: "DELETE" });
      setThoughts(current => (current || []).filter(item => item.id !== thought.id));
      setSelectedId(""); if (shareId === thought.id) setShareId(""); setToast(t("思想已刪除"));
    } catch (error) { setToast((error.message || t("刪除失敗"))); }
  };
  const togglePublicShare = async enabled => {
    if (!shareThought) return;
    setShareBusy(true); setShareError("");
    try {
      const result = await W2.json("/api/civilization/thoughts/" + encodeURIComponent(shareThought.id) + "/share", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ expected_revision: shareThought.revision, enabled }),
      });
      setThoughts(current => (current || []).map(item => item.id === shareThought.id ? result.thought : item));
      setToast(t("分享設定已更新"));
    } catch (error) {
      setShareError(error.status === 409 ? t("內容已被其他人更新，請重新打開後再編輯。") : (error.message || t("分享設定失敗")));
    } finally { setShareBusy(false); }
  };

  if (thoughts === null) return <div className="civilization-page"><div className="civ-empty">{t("正在讀取文明資料")}…</div></div>;

  const atlas = <div className="civ-atlas-layout">
    <div className="civ-atlas-register">
      <div className="civ-register-head"><span>NO.</span><span>DOMAIN</span><span>QUESTION / OBJECT</span><span>RELATION</span><span>TIME</span></div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : visible.map(thought => {
        const domain = domainOf(thought.domain);
        return <button type="button" className="civ-thought-row" data-domain={domain.key} style={domainStyle(domain)} key={thought.id} aria-selected={selected && thought.id === selected.id} onClick={() => selectThought(thought.id)}>
          <span className="civ-row-no">{thought.no}</span>
          <span className="civ-row-domain"><DomainGlyph domain={domain}/>{lang() === "en" ? domain.en : t(domain.zh)}<br/>{domain.en.toUpperCase()}</span>
          <span className="civ-row-copy"><small>QUESTION OBJECT</small><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span>
          <span className="civ-row-links"><small>{t("連接到").toUpperCase()}</small><b>{thoughtRelations(thought).map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thoughtRelations(thought).length - 1 && <br/>}</React.Fragment>)}</b></span>
          <span className="civ-row-year">{thought.year}</span>
        </button>;
      })}
    </div>
    {selected && <aside className="civ-atlas-detail" data-domain={selectedDomain.key} style={domainStyle(selectedDomain)}>
      <div className="civ-detail-meta"><span>{selectedDomain.en.toUpperCase()} / {selected.date}</span><span>{t("選中").toUpperCase()}</span></div>
      <div className="civ-detail-figure"><div className="civ-detail-no">{selected.no}</div><DomainGlyph domain={selectedDomain} large/></div><span className="civ-micro">{t("當前問題")}</span>
      <h2>{thoughtText(selected, "title")}</h2><p>{thoughtText(selected, "thesis")}</p>
      <div className="civ-detail-actions"><button type="button" onClick={() => setView("c")}>{t("海報閱讀")} →</button><button type="button" onClick={() => openShare(selected)}>{t("分享")} ↗</button>{selected.can_edit && <button type="button" onClick={() => { setComposerError(""); setComposer({ initial: selected }); }}>{t("編輯")} ↗</button>}<button type="button" onClick={() => selected.can_delete ? removeThought(selected) : copyLink(selected)}>{selected.can_delete ? t("刪除") : t("複製分享")} ↗</button></div>
    </aside>}
  </div>;

  const chronology = <div className="civ-chronology">
    <aside className="civ-chronology-side"><span className="civ-micro">CHRONOLOGY / {t("思想形成")}</span><strong>{visible.length}×</strong><p>{t("時間軸不表示思想越來越正確，而是保留問題如何被重新提出、修正和連接。")}</p><div className="civ-chronology-legend">○ FIRST QUESTION<br/>□ REVISED LENS<br/>— RELATED THOUGHT<br/>● CURRENT READING</div></aside>
    <div className="civ-timeline"><div className="civ-timeline-axis">{["2021", "2022", "2023", "2024", "2025", "2026"].map(year => <span key={year}>{year}</span>)}</div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <ol className="civ-timeline-list">{visible.map(thought => { const domain = domainOf(thought.domain); return <li className="civ-timeline-item" key={thought.id} data-domain={domain.key} style={domainStyle(domain)}><time className="civ-timeline-date">{thought.date}</time><div className="civ-timeline-node"><button type="button" aria-selected={selected && thought.id === selected.id} onClick={() => selectThought(thought.id)}><DomainGlyph domain={domain}/><span><span className="civ-eyebrow">{domain.en.toUpperCase()} · QUESTION OBJECT</span><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span><aside>{thoughtRelations(thought).map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thoughtRelations(thought).length - 1 && <br/>}</React.Fragment>)}</aside></button></div></li>; })}</ol>}
    </div>
  </div>;

  const reader = !selected ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <div className={"civ-reader" + (notesOpen ? "" : " is-notes-collapsed")} data-domain={selectedDomain.key} style={domainStyle(selectedDomain)}>
    <nav className="civ-reader-rail" aria-label={t("問題")}>{visible.map(thought => { const domain = domainOf(thought.domain); return <button type="button" key={thought.id} data-domain={domain.key} style={domainStyle(domain)} className={thought.id === selected.id ? "is-active" : ""} onClick={() => selectThought(thought.id)}>{thought.no} · {domain.en.toUpperCase()}</button>; })}</nav>
    <div className="civ-reader-document">{!notesOpen && <button type="button" className="civ-notes-reopen" data-testid="civilization-notes-open" aria-label={t("展開閱讀工具欄")} onClick={() => setNotesOpen(true)}>TOOLS / {t("視角")} ←</button>}<article className="civ-reader-poster" data-domain={selectedDomain.key} style={domainStyle(selectedDomain)}><PosterMotion domain={selectedDomain}/><div className="civ-poster-label"><span>{selectedContent.eyebrow || "CIVILIZATION · QUESTION"} {selected.no}</span><span>{selectedContent.category_label || selectedDomain.en.toUpperCase()}</span></div><h2 className="civ-poster-question"><PosterQuestion>{selectedContent.title || thoughtText(selected, "title")}</PosterQuestion></h2><p className="civ-poster-thesis">{selectedContent.short || thoughtText(selected, "short")}</p><aside className="civ-poster-index"><span className="civ-micro">LENS INDEX / {String(selectedLenses.length).padStart(2, "0")}</span>{selectedLenses.length ? selectedLenses.slice(0, 3).map((item, index) => <span key={index}><b>{String(index + 1).padStart(2, "0")}</b>{localText(item.name)}</span>) : <span><b>00</b>{t("尚未添加視角")}</span>}</aside><footer className="civ-poster-foot"><span>{selectedContent.footer_left || "12 COLUMN SYSTEM · ONE QUESTION / MANY LENSES"}</span><span>{selected.date}</span></footer></article><article className="civ-article-body">{selectedReadingSections.map((section, index) => <section className="civ-article-section" key={index}><div className="civ-article-marker"><strong>{section.marker || String(index).padStart(2, "0")}</strong><small>{section.kicker || "SECTION / THOUGHT"}</small></div><div className="civ-article-copy"><span className="civ-micro">{section.kicker || `SECTION ${String(index + 1).padStart(2, "0")}`}</span><h3>{section.heading}</h3>{(Array.isArray(section.paragraphs) ? section.paragraphs : proseParagraphs(section.paragraphs)).map((paragraph, paragraphIndex) => <p key={paragraphIndex}>{paragraph}</p>)}</div></section>)}<footer><span>{selectedContent.footer_right || "INFORMATION BEFORE DECORATION"}</span><span>{selected.date}</span></footer></article></div>
    {notesOpen && <aside className="civ-reader-notes" data-domain={selectedDomain.key} style={domainStyle(selectedDomain)}><div className="civ-reader-notes-head"><span className="civ-micro">CHANGE THE LENS / {t("換一個角度")}</span><button type="button" data-testid="civilization-notes-close" aria-label={t("收起閱讀工具欄")} title={t("收起閱讀工具欄")} onClick={() => setNotesOpen(false)}>×</button></div><h3>{selectedContent.title || thoughtText(selected, "title")}</h3><p>{selectedContent.quote || selectedContent.short || thoughtText(selected, "short")}</p><div className="civ-publication-meta"><span><b>{t("固定版面")}</b>SWISS B / V1</span><span><b>{t("發布版本")}</b>{String(selected.published_revision || 0).padStart(2, "0")}{selected.has_draft ? ` · ${t("草稿")}` : ` · ${t("已發布")}`}</span></div><div className="civ-lens-list">{selectedLenses.length ? selectedLenses.map((item, index) => <button type="button" key={index} className={lens === index ? "is-active" : ""} onClick={() => setLens(index)}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{localText(item.name)}</strong><br/>{localText(item.text)}</span></button>) : <div className="civ-empty civ-lens-empty">{t("尚未添加視角")}</div>}</div><div className="civ-read-actions"><button type="button" className="civ-read-action" onClick={() => openShare(selected)}>{t("分享")} →</button>{selected.can_edit && <button type="button" className="civ-read-action" onClick={() => { setComposerError(""); setComposer({ initial: selected }); }}>{t(selectedLenses.length ? "編輯" : "添加視角")} →</button>}<button type="button" className="civ-read-action" onClick={() => selected.can_delete ? removeThought(selected) : copyLink(selected)}>{selected.can_delete ? t("刪除") : t("複製這個思考的鏈接")} →</button></div></aside>}
  </div>;

  return <div className="civilization-page" data-domain={activeDomain.key} style={domainStyle(activeDomain)}>
    <header className="civ-toolbar"><div className="civ-toolbar-brand"><span className="civ-toolbar-mark" aria-hidden="true"/><span>BONFIRE PLATFORM<br/>CIVILIZATION / {t("文明")}</span></div><nav className="civ-view-switch" aria-label={t("閱讀海報")}>{[["a", "問題拓撲"], ["b", "思想時間軸"], ["c", "閱讀海報"]].map(([id, label]) => <button type="button" key={id} aria-selected={view === id} onClick={() => setView(id)}>{id.toUpperCase()} {t(label)}</button>)}</nav><div className="civ-toolbar-right"><span>{String(allThoughts.length).padStart(2, "0")} QUESTIONS · {String(allThoughts.reduce((sum, item) => sum + thoughtLenses(item).length, 0)).padStart(2, "0")} LENSES</span><button type="button" className="civ-cli-button" onClick={() => W2.openBusinessAction("civilization_api_key_issue")}>{t("文明 CLI / API")}</button><button type="button" className="civ-new-button" onClick={() => { setComposerError(""); setComposer({ initial: null }); }}>＋ {t("記錄一個問題")}</button></div></header>
    <section className="civ-masthead"><div className="civ-mast-copy"><span className="civ-kicker">MODULE C1 · {t("共享觀看方式").toUpperCase()}</span><h1 className="civ-mast-title">{t("文明")}<span>CIVILIZATION</span></h1><p className="civ-mast-lead">{t("分享答案之前，先分享我們如何提出問題。")} {t("這裡保存觀察世界的方法、判斷事物的尺度，以及思想彼此連接和變化的過程。")}</p></div><aside className="civ-mast-index"><span className="civ-micro">LIVE INDEX / {new Date().getFullYear()}</span><strong>C1</strong><div className="civ-domain-spectrum" aria-hidden="true">{DOMAINS.slice(1).map(domain => <i key={domain.key} style={domainStyle(domain)}/>)}</div><p>{t("提問").toUpperCase()}<br/>{t("視角").toUpperCase()}<br/>{t("方法").toUpperCase()}<br/>{t("譜系").toUpperCase()}</p></aside></section>
    <section className="civ-filters"><div className="civ-filter-label"><b>FILTER / {t("篩選")}</b><small>{String(visible.length).padStart(2, "0")} {t("個對象").toUpperCase()}</small></div><div className="civ-filter-buttons" role="group" aria-label={t("篩選")}>{DOMAINS.map(domain => <button type="button" key={domain.key} data-domain={domain.key} style={domainStyle(domain)} className={filter === domain.key ? "is-active" : ""} onClick={() => setFilter(domain.key)}>{lang() === "en" ? domain.en : t(domain.zh)}</button>)}</div><label className="civ-search"><span>⌕</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={t("搜索問題、方法或角度")}/></label></section>
    {loadError && <div className="civ-load-error" role="alert"><span>{t("文明資料讀取失敗")}: {loadError}</span><button type="button" onClick={loadThoughts}>{t("重新讀取")}</button></div>}
    <main className="civ-view">{view === "a" ? atlas : view === "b" ? chronology : reader}</main>
    <footer className="civ-footer"><span>INFORMATION BEFORE DECORATION</span><span>LIST ↔ LINEAGE ↔ READING</span></footer>
    {composer && <CivilizationComposer busy={composerBusy} error={composerError} initial={composer.initial} onClose={() => setComposer(null)} onSave={saveThought}/>} {shareThought && <CivilizationSharePanel thought={shareThought} busy={shareBusy} error={shareError} onClose={() => setShareId("")} onToggle={togglePublicShare} onToast={setToast}/>} {toast && <div className="civ-toast" role="status">{toast}</div>}
  </div>;
};

window.W2.PAGES["civilization"] = Page;
})();
