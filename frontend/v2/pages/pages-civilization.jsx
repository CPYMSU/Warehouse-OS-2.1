/* WAREHOUSE OS 2.1 · CIVILIZATION
   A shared Swiss register for questions, lenses, methods and intellectual lineage. */
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
  "問題對象": "Question object", "關聯": "Relations", "選中": "Selected", "當前問題": "Current question",
  "連接到": "Connected to", "海報閱讀": "Poster reading", "複製分享": "Copy share link",
  "刪除草稿": "Delete draft", "思想形成": "Idea formation",
  "時間軸不表示思想越來越正確，而是保留問題如何被重新提出、修正和連接。": "The chronology does not claim that ideas become more correct; it preserves how questions are reframed, revised and connected.",
  "換一個角度": "Change the lens", "一個問題 · 多種視角": "One question · many lenses",
  "複製這個思考的鏈接": "Copy this thought link", "沒有符合條件的思考對象": "No thought objects match these filters",
  "記錄問題": "Record question", "領域": "Domain", "問題": "Question", "一句引子": "Short prompt",
  "核心判斷": "Core proposition", "保存為此設備草稿": "Save as a draft on this device",
  "草稿只保存在當前設備；平台共享發布機制將在內容模型確認後接入。": "Drafts stay on this device; platform publishing will be connected after the content model is confirmed.",
  "取消": "Cancel", "此設備草稿": "Device draft", "草稿已保存到此設備": "Draft saved on this device",
  "草稿已刪除": "Draft deleted", "確認刪除此設備上的草稿？": "Delete this draft from this device?",
  "思想鏈接已複製": "Thought link copied", "無法自動複製，請從地址欄複製": "Could not copy automatically; copy it from the address bar",
  "共享觀看方式": "Shared ways of seeing", "提問": "Question", "視角": "Lens", "方法": "Method", "譜系": "Lineage",
  "事實層": "Evidence", "時間層": "Time", "關係層": "Relations",
  "什麼已被證據支持，什麼仍只是願望？": "What is supported by evidence, and what remains a wish?",
  "把判斷放到更長的時間尺度會發生什麼？": "What changes when the judgement is placed on a longer timescale?",
  "誰受益、誰承擔代價、誰沒有被看見？": "Who benefits, who bears the cost, and who remains unseen?",
});

const DOMAINS = [
  { key: "all", zh: "全部", en: "All", color: "var(--red)" },
  { key: "judgement", zh: "判斷", en: "Judgement", color: "#D62B20" },
  { key: "technology", zh: "技術", en: "Technology", color: "#174A96" },
  { key: "organization", zh: "組織", en: "Organization", color: "#1F654B" },
  { key: "time", zh: "時間", en: "Time", color: "#9B4F1B" },
  { key: "ethics", zh: "倫理", en: "Ethics", color: "#6B3C78" },
];
const pair = (zh, en) => ({ zh, en });
const BUILTIN_THOUGHTS = [
  {
    id: "order-control", no: "01", domain: "judgement", date: "2021—11", year: "2021",
    title: pair("秩序與控制，區別在哪裡？", "Where does order end and control begin?"),
    short: pair("當結構開始替人作決定，秩序是否已經變成控制？", "When structure starts deciding for people, has order already become control?"),
    thesis: pair("好的秩序減少無意義的摩擦，卻不替人取消判斷。判斷一個系統時，不只看它是否整齊，也看它是否保留退出、質疑與修正的空間。", "Good order reduces meaningless friction without cancelling judgement. Assess a system not only by its neatness, but by whether it preserves room to exit, question and revise."),
    relations: [pair("組織的記憶", "Organizational memory"), pair("責任的時間", "The time of responsibility")],
    lenses: [
      { name: pair("自由的負空間", "Freedom as negative space"), text: pair("真正的秩序會主動保留不被安排的部分。", "Real order deliberately leaves some things unarranged.") },
      { name: pair("可逆性", "Reversibility"), text: pair("一個決定能否被撤回，是秩序與控制的重要分界。", "Whether a decision can be reversed is a key boundary between order and control.") },
      { name: pair("最小必要規則", "Minimum necessary rule"), text: pair("只建立足以協作的規則，不把可選擇的事變成命令。", "Create only enough rules for coordination; do not turn choices into commands.") },
    ],
  },
  {
    id: "efficiency-progress", no: "02", domain: "technology", date: "2022—05", year: "2022",
    title: pair("效率一定意味著進步嗎？", "Does efficiency always mean progress?"),
    short: pair("節省下來的時間，最終回到了誰的手中？", "Whose hands receive the time that efficiency saves?"),
    thesis: pair("效率只是投入與產出的關係，不自動回答方向是否值得。真正的進步還要追問：節省出的時間如何分配，風險轉移給了誰，人的能力是否因此生長。", "Efficiency only describes the relation between input and output; it does not tell us whether the direction is worthwhile. Progress must also ask how saved time is distributed, who receives the risk, and whether human capability grows."),
    relations: [pair("技術的邊界", "Limits of technology"), pair("責任的時間", "The time of responsibility")],
    lenses: [
      { name: pair("分配", "Distribution"), text: pair("效率收益是否被共同分享，而不是只被少數節點吸收？", "Are efficiency gains shared, or absorbed by only a few nodes?") },
      { name: pair("反脆弱", "Antifragility"), text: pair("高度優化是否消除了系統面對意外所需的冗餘？", "Has optimization removed the redundancy needed to face surprise?") },
      { name: pair("能力生長", "Capability growth"), text: pair("工具替代勞動後，人是否獲得了更高層次的判斷能力？", "After tools replace labour, do people gain higher-order judgement?") },
    ],
  },
  {
    id: "organizational-memory", no: "03", domain: "organization", date: "2023—02", year: "2023",
    title: pair("組織應該記住什麼，又忘記什麼？", "What should an organization remember—and forget?"),
    short: pair("記憶帶來連續性，也可能把過去變成未來的枷鎖。", "Memory creates continuity, but can also turn the past into a constraint on the future."),
    thesis: pair("組織需要記住決策的理由、證據與責任，卻不應把人的一次錯誤永久固化為身份。好的記憶保存可學習的脈絡，好的遺忘保護重新開始的可能。", "Organizations should remember the reasons, evidence and responsibility behind decisions without permanently turning one mistake into a person's identity. Good memory preserves learnable context; good forgetting protects the possibility of beginning again."),
    relations: [pair("秩序與控制", "Order and control"), pair("證據與願望", "Evidence and desire")],
    lenses: [
      { name: pair("制度記憶", "Institutional memory"), text: pair("保存為何如此決定，而不只保存最後結果。", "Preserve why a decision was made, not only its final outcome.") },
      { name: pair("人格保護", "Protection of personhood"), text: pair("事件可以被審計，人不應被一條記錄永久定義。", "Events can be audited; a person should not be permanently defined by one record.") },
      { name: pair("知識半衰期", "Knowledge half-life"), text: pair("為每種經驗標注適用條件與失效時間。", "Mark the conditions and expiry horizon of each lesson.") },
    ],
  },
  {
    id: "future-timescale", no: "04", domain: "time", date: "2024—04", year: "2024",
    title: pair("對未來負責，需要多長的時間尺度？", "How long a timescale does responsibility require?"),
    short: pair("季度、任期和一生，會導向完全不同的決定。", "A quarter, a term of office and a lifetime produce very different decisions."),
    thesis: pair("責任的時間尺度應至少覆蓋決策主要後果的生命週期。當後果超出個人任期，制度就要替尚未到場的人保留發言位置。", "The timescale of responsibility should cover the life cycle of a decision's main consequences. When consequences outlast an individual's term, institutions must preserve a voice for people not yet present."),
    relations: [pair("效率與進步", "Efficiency and progress"), pair("技術的邊界", "Limits of technology")],
    lenses: [
      { name: pair("後果週期", "Consequence cycle"), text: pair("不要用預算週期替代事物真正的生命週期。", "Do not substitute budget cycles for the real life cycle of things.") },
      { name: pair("未來代表", "Future representation"), text: pair("誰在今天的會議裡代表尚未出生的人？", "Who represents people not yet born in today's meeting?") },
      { name: pair("可維護性", "Maintainability"), text: pair("把維護成本視為設計本身，而不是留給後人的附註。", "Treat maintenance cost as part of design, not a footnote left to successors.") },
    ],
  },
  {
    id: "evidence-desire", no: "05", domain: "judgement", date: "2025—01", year: "2025",
    title: pair("當證據與願望衝突，如何繼續判斷？", "How do we judge when evidence conflicts with desire?"),
    short: pair("事實不保證舒適，但判斷不能只服務於希望。", "Facts do not guarantee comfort, but judgement cannot serve hope alone."),
    thesis: pair("先把『我希望如此』與『目前證據支持如此』分開記錄，再尋找能推翻當前結論的新證據。成熟的判斷不是沒有立場，而是允許立場被現實修正。", "Record 'I hope this is true' separately from 'current evidence supports this', then seek evidence capable of overturning the present conclusion. Mature judgement is not positionless; it allows reality to revise the position."),
    relations: [pair("組織的記憶", "Organizational memory"), pair("責任的時間", "The time of responsibility")],
    lenses: [
      { name: pair("可證偽性", "Falsifiability"), text: pair("提前寫下什麼證據會讓自己改變看法。", "Write down in advance what evidence would change your view.") },
      { name: pair("雙欄記錄", "Two-column record"), text: pair("把觀察到的事實與對事實的解釋分開。", "Separate observed facts from interpretations of those facts.") },
      { name: pair("反方鋼人", "Steelman the opposition"), text: pair("先構造對方最強的論證，再檢查自己的結論。", "Build the strongest opposing argument before checking your conclusion.") },
    ],
  },
  {
    id: "technology-stop", no: "06", domain: "ethics", date: "2026—08", year: "2026",
    title: pair("技術應該在哪裡主動停下來？", "Where should technology choose to stop?"),
    short: pair("能做到，不等於應該做到；可以收集，也不等於值得保留。", "Can does not imply should; collectible does not imply worth retaining."),
    thesis: pair("技術邊界不只由能力決定，也由尊嚴、可逆性和權力差決定。越難拒絕、越不可撤回、越影響人的核心身份，就越需要主動降低技術的侵入性。", "Technical boundaries are shaped not only by capability, but by dignity, reversibility and power asymmetry. The harder something is to refuse, reverse, or keep away from core identity, the more deliberately technology should reduce its intrusion."),
    relations: [pair("效率與進步", "Efficiency and progress"), pair("秩序與控制", "Order and control")],
    lenses: [
      { name: pair("有意義的同意", "Meaningful consent"), text: pair("拒絕是否真的可行，還是只存在於條款文字裡？", "Is refusal genuinely possible, or only present in the terms?") },
      { name: pair("最小收集", "Data minimization"), text: pair("沒有明確用途與保存期限的資料，就不應被收集。", "Data without a clear purpose and retention period should not be collected.") },
      { name: pair("人類保留權", "Human reserve"), text: pair("某些決定應保留由人承擔、解釋與改變的權利。", "Some decisions should preserve the human right to take responsibility, explain and change them.") },
    ],
  },
];

const domainOf = key => DOMAINS.find(item => item.key === key) || DOMAINS[1];
const localText = value => {
  if (value == null) return "";
  if (typeof value === "string") return value;
  return lang() === "en" ? value.en : t(value.zh);
};
const thoughtText = (thought, key) => localText(thought && thought[key]);
const thoughtLenses = thought => Array.isArray(thought && thought.lenses) ? thought.lenses : [];
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

const CivilizationComposer = ({ onClose, onSave }) => {
  useEffect(() => {
    const close = event => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", close);
    return () => document.removeEventListener("keydown", close);
  }, [onClose]);
  const submit = event => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave({
      domain: String(form.get("domain") || "judgement"),
      title: String(form.get("title") || "").trim(),
      short: String(form.get("short") || "").trim(),
      thesis: String(form.get("thesis") || "").trim(),
    });
  };
  return <div className="civ-composer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <form className="civ-composer-card" role="dialog" aria-modal="true" aria-labelledby="civ-composer-title" onSubmit={submit}>
      <header className="civ-composer-head"><b>C1</b><div><span className="civ-eyebrow">NEW THOUGHT OBJECT</span><h2 id="civ-composer-title">{t("記錄問題")}</h2></div><button type="button" className="civ-composer-close" onClick={onClose} aria-label={t("取消")}>×</button></header>
      <div className="civ-composer-body">
        <label>{t("領域")}<select name="domain" defaultValue="judgement">{DOMAINS.slice(1).map(domain => <option key={domain.key} value={domain.key}>{lang() === "en" ? domain.en : t(domain.zh)}</option>)}</select></label>
        <label>{t("一句引子")}<input name="short" maxLength="180" required/></label>
        <label className="is-wide">{t("問題")}<input name="title" maxLength="160" autoFocus required/></label>
        <label className="is-wide">{t("核心判斷")}<textarea name="thesis" maxLength="1200" required/></label>
      </div>
      <footer className="civ-composer-foot"><span>{t("草稿只保存在當前設備；平台共享發布機制將在內容模型確認後接入。")}</span><button type="submit">{t("保存為此設備草稿")}</button></footer>
    </form>
  </div>;
};

const Page = () => {
  const initialMemory = useMemo(readMemory, []);
  const params = useMemo(routeParams, []);
  const [view, setView] = useState(["a", "b", "c"].includes(params.get("view")) ? params.get("view") : (initialMemory.view || "a"));
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState(params.get("thought") || initialMemory.selected || BUILTIN_THOUGHTS[0].id);
  const [lens, setLens] = useState(0);
  const [drafts, setDrafts] = useState(Array.isArray(initialMemory.drafts) ? initialMemory.drafts : []);
  const [composer, setComposer] = useState(false);
  const [toast, setToast] = useState("");
  const allThoughts = useMemo(() => BUILTIN_THOUGHTS.concat(drafts), [drafts]);
  const visible = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return allThoughts.filter(thought => {
      if (filter !== "all" && thought.domain !== filter) return false;
      if (!needle) return true;
      const haystack = [thoughtText(thought, "title"), thoughtText(thought, "short"), thoughtText(thought, "thesis"), ...thought.relations.map(localText), ...thoughtLenses(thought).flatMap(item => [localText(item.name), localText(item.text)])].join(" ").toLowerCase();
      return haystack.includes(needle);
    });
  }, [allThoughts, filter, query]);
  const selected = allThoughts.find(item => item.id === selectedId) || visible[0] || allThoughts[0];

  useEffect(() => {
    if (visible.length && !visible.some(item => item.id === selectedId)) setSelectedId(visible[0].id);
  }, [visible, selectedId]);
  useEffect(() => { setLens(0); }, [selectedId]);
  useEffect(() => {
    writeMemory({ view, selected: selectedId, drafts, updated_at: new Date().toISOString() });
  }, [view, selectedId, drafts]);
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
  const saveDraft = value => {
    if (!value.title || !value.thesis) return;
    const now = new Date();
    const no = String(allThoughts.length + 1).padStart(2, "0");
    const draft = {
      ...value, id: "draft-" + now.getTime().toString(36), no, draft: true,
      date: `${now.getFullYear()}—${String(now.getMonth() + 1).padStart(2, "0")}`, year: String(now.getFullYear()),
      relations: [t("此設備草稿")], lenses: [
        { name: t("事實層"), text: t("什麼已被證據支持，什麼仍只是願望？") },
        { name: t("時間層"), text: t("把判斷放到更長的時間尺度會發生什麼？") },
        { name: t("關係層"), text: t("誰受益、誰承擔代價、誰沒有被看見？") },
      ],
    };
    setDrafts(current => current.concat(draft)); setSelectedId(draft.id); setComposer(false); setToast(t("草稿已保存到此設備"));
  };
  const removeDraft = thought => {
    if (!thought.draft || !window.confirm(t("確認刪除此設備上的草稿？"))) return;
    setDrafts(current => current.filter(item => item.id !== thought.id)); setSelectedId(BUILTIN_THOUGHTS[0].id); setToast(t("草稿已刪除"));
  };
  const selectedDomain = domainOf(selected.domain);
  const selectedLenses = thoughtLenses(selected);

  const atlas = <div className="civ-atlas-layout">
    <div className="civ-atlas-register">
      <div className="civ-register-head"><span>NO.</span><span>DOMAIN</span><span>QUESTION / OBJECT</span><span>RELATION</span><span>TIME</span></div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : visible.map(thought => {
        const domain = domainOf(thought.domain);
        return <button type="button" className="civ-thought-row" key={thought.id} aria-selected={thought.id === selected.id} onClick={() => selectThought(thought.id)}>
          <span className="civ-row-no">{thought.no}</span>
          <span className="civ-row-domain" style={{ "--civ-signal": domain.color }}><i/>{lang() === "en" ? domain.en : t(domain.zh)}<br/>{domain.en.toUpperCase()}</span>
          <span className="civ-row-copy"><small>{thought.draft ? t("此設備草稿").toUpperCase() : "QUESTION OBJECT"}</small><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span>
          <span className="civ-row-links"><small>{t("連接到").toUpperCase()}</small><b>{thought.relations.map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thought.relations.length - 1 && <br/>}</React.Fragment>)}</b></span>
          <span className="civ-row-year">{thought.year}</span>
        </button>;
      })}
    </div>
    <aside className="civ-atlas-detail" style={{ "--civ-signal": selectedDomain.color }}>
      <div className="civ-detail-meta"><span>{selectedDomain.en.toUpperCase()} / {selected.date}</span><span>{t("選中").toUpperCase()}</span></div>
      <div className="civ-detail-no">{selected.no}</div><span className="civ-micro">{t("當前問題")}</span>
      <h2>{thoughtText(selected, "title")}</h2><p>{thoughtText(selected, "thesis")}</p>
      <div className="civ-detail-actions"><button type="button" onClick={() => setView("c")}>{t("海報閱讀")} →</button><button type="button" onClick={() => selected.draft ? removeDraft(selected) : copyLink(selected)}>{selected.draft ? t("刪除草稿") : t("複製分享")} ↗</button></div>
    </aside>
  </div>;

  const chronology = <div className="civ-chronology">
    <aside className="civ-chronology-side"><span className="civ-micro">CHRONOLOGY / {t("思想形成")}</span><strong>{visible.length}×</strong><p>{t("時間軸不表示思想越來越正確，而是保留問題如何被重新提出、修正和連接。")}</p><div className="civ-chronology-legend">○ FIRST QUESTION<br/>□ REVISED LENS<br/>— RELATED THOUGHT<br/>● CURRENT READING</div></aside>
    <div className="civ-timeline"><div className="civ-timeline-axis">{["2021", "2022", "2023", "2024", "2025", "2026"].map(year => <span key={year}>{year}</span>)}</div>
      {!visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <ol className="civ-timeline-list">{visible.map(thought => <li className="civ-timeline-item" key={thought.id}><time className="civ-timeline-date">{thought.date}</time><div className="civ-timeline-node"><button type="button" aria-selected={thought.id === selected.id} onClick={() => selectThought(thought.id)}><span><span className="civ-eyebrow">{domainOf(thought.domain).en.toUpperCase()} · {thought.draft ? t("此設備草稿") : "QUESTION OBJECT"}</span><h2>{thoughtText(thought, "title")}</h2><p>{thoughtText(thought, "short")}</p></span><aside>{thought.relations.map((item, index) => <React.Fragment key={index}>↳ {localText(item)}{index < thought.relations.length - 1 && <br/>}</React.Fragment>)}</aside></button></div></li>)}</ol>}
    </div>
  </div>;

  const reader = !visible.length ? <div className="civ-empty">{t("沒有符合條件的思考對象")}</div> : <div className="civ-reader">
    <nav className="civ-reader-rail" aria-label={t("問題")}>{visible.map(thought => <button type="button" key={thought.id} className={thought.id === selected.id ? "is-active" : ""} onClick={() => selectThought(thought.id)}>{thought.no} · {domainOf(thought.domain).en.toUpperCase()}</button>)}</nav>
    <article className="civ-reader-poster"><div className="civ-poster-label"><span>CIVILIZATION · QUESTION {selected.no}</span><span>{selectedDomain.en.toUpperCase()}</span></div><h2 className="civ-poster-question"><PosterQuestion>{thoughtText(selected, "title")}</PosterQuestion></h2><p className="civ-poster-thesis">{thoughtText(selected, "thesis")}</p><footer className="civ-poster-foot"><span>ONE QUESTION · MANY LENSES</span><span>{selected.date}</span></footer></article>
    <aside className="civ-reader-notes"><span className="civ-micro">CHANGE THE LENS / {t("換一個角度")}</span><h3>{thoughtText(selected, "title")}</h3><p>{thoughtText(selected, "short")}</p><div className="civ-lens-list">{selectedLenses.map((item, index) => <button type="button" key={index} className={lens === index ? "is-active" : ""} onClick={() => setLens(index)}><b>{String(index + 1).padStart(2, "0")}</b><span><strong>{localText(item.name)}</strong><br/>{localText(item.text)}</span></button>)}</div><button type="button" className="civ-read-action" onClick={() => selected.draft ? removeDraft(selected) : copyLink(selected)}>{selected.draft ? t("刪除草稿") : t("複製這個思考的鏈接")} →</button></aside>
  </div>;

  return <div className="civilization-page">
    <header className="civ-toolbar"><div className="civ-toolbar-brand"><span className="civ-toolbar-mark" aria-hidden="true"/><span>BONFIRE PLATFORM<br/>CIVILIZATION / {t("文明")}</span></div><nav className="civ-view-switch" aria-label={t("閱讀海報")}>{[["a", "問題拓撲"], ["b", "思想時間軸"], ["c", "閱讀海報"]].map(([id, label]) => <button type="button" key={id} aria-selected={view === id} onClick={() => setView(id)}>{id.toUpperCase()} {t(label)}</button>)}</nav><div className="civ-toolbar-right"><span>{String(allThoughts.length).padStart(2, "0")} QUESTIONS · {String(allThoughts.reduce((sum, item) => sum + thoughtLenses(item).length, 0)).padStart(2, "0")} LENSES</span><button type="button" className="civ-new-button" onClick={() => setComposer(true)}>＋ {t("記錄一個問題")}</button></div></header>
    <section className="civ-masthead"><div className="civ-mast-copy"><span className="civ-kicker">MODULE C1 · {t("共享觀看方式").toUpperCase()}</span><h1 className="civ-mast-title">{t("文明")}<span>CIVILIZATION</span></h1><p className="civ-mast-lead">{t("分享答案之前，先分享我們如何提出問題。")} {t("這裡保存觀察世界的方法、判斷事物的尺度，以及思想彼此連接和變化的過程。")}</p></div><aside className="civ-mast-index"><span className="civ-micro">LIVE INDEX / {new Date().getFullYear()}</span><strong>C1</strong><p>{t("提問").toUpperCase()}<br/>{t("視角").toUpperCase()}<br/>{t("方法").toUpperCase()}<br/>{t("譜系").toUpperCase()}</p></aside></section>
    <section className="civ-filters"><div className="civ-filter-label"><b>FILTER / {t("篩選")}</b><small>{String(visible.length).padStart(2, "0")} {t("個對象").toUpperCase()}</small></div><div className="civ-filter-buttons" role="group" aria-label={t("篩選")}>{DOMAINS.map(domain => <button type="button" key={domain.key} className={filter === domain.key ? "is-active" : ""} onClick={() => setFilter(domain.key)}>{lang() === "en" ? domain.en : t(domain.zh)}</button>)}</div><label className="civ-search"><span>⌕</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={t("搜索問題、方法或角度")}/></label></section>
    <main className="civ-view">{view === "a" ? atlas : view === "b" ? chronology : reader}</main>
    <footer className="civ-footer"><span>INFORMATION BEFORE DECORATION</span><span>LIST ↔ LINEAGE ↔ READING</span></footer>
    {composer && <CivilizationComposer onClose={() => setComposer(false)} onSave={saveDraft}/>} {toast && <div className="civ-toast" role="status">{toast}</div>}
  </div>;
};

window.W2.PAGES["civilization"] = Page;
})();
