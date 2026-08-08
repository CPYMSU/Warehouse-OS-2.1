/* WAREHOUSE OS 2.1 · CIVILIZATION MOBILE A
   Presentation-only mobile renderer. Data and operations stay owned by pages-civilization.jsx. */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;

window.W2_LANG.addEN({
  "問題索引": "Question index",
  "開啟閱讀": "Open reading",
  "重新載入": "Reload",
  "手機文明視圖": "Mobile Civilization view",
  "思想如何形成": "How thoughts form",
  "按時間閱讀問題如何被提出、修正與連接。": "Read how questions are raised, revised and connected over time.",
  "目前閱讀": "Now reading",
  "閱讀引語": "Reading quote",
  "正文": "Reading",
  "觀看視角": "Lenses",
  "返回問題": "Back to questions",
  "編輯內容": "Edit",
  "尚無可閱讀內容": "No reading content yet",
});

const MobileWordmark = () => <span className="civ-mobile-word" aria-label="CIVILIZATION">
  <i className="civ-mobile-word-bars" aria-hidden="true"><b/><b/><b/></i>
  <span className="civ-mobile-word-layer civ-mobile-word-offset is-red" aria-hidden="true">CIVILIZATION</span>
  <span className="civ-mobile-word-layer civ-mobile-word-offset is-blue" aria-hidden="true">CIVILIZATION</span>
  <span className="civ-mobile-word-layer civ-mobile-word-offset is-green" aria-hidden="true">CIVILIZATION</span>
  <span className="civ-mobile-word-layer civ-mobile-word-color" aria-hidden="true">CIVILIZATION</span>
  <span className="civ-mobile-word-layer civ-mobile-word-outline" aria-hidden="true">CIVILIZATION</span>
</span>;

const ViewNavigation = ({ view, onView }) => <nav className="civ-mobile-bottom-nav" aria-label={t("手機文明視圖")}>
  {[['a', '問題拓撲'], ['b', '思想時間軸'], ['c', '閱讀海報']].map(([id, label]) => <button type="button" key={id} className={view === id ? "is-active" : ""} aria-current={view === id ? "page" : undefined} onClick={() => onView(id)}><b>{id.toUpperCase()}</b><span>{t(label)}</span></button>)}
  <button type="button" className="is-create" onClick={() => onView('new')}><b>＋</b><span>{t("記錄一個問題")}</span></button>
</nav>;

const MobileThought = ({ thought, onRead, onShare, onEdit }) => <article className="civ-mobile-thought" data-domain={thought.domainKey} style={thought.style}>
  <button type="button" className="civ-mobile-thought-main" onClick={() => onRead(thought.id)}>
    <span className="civ-mobile-thought-no">{thought.no}</span>
    <span className="civ-mobile-thought-copy">
      <span className="civ-mobile-thought-meta"><b>{thought.domainEn.toUpperCase()} / {thought.domainLabel}</b><time>{thought.date}</time></span>
      <strong>{thought.title}</strong>
      <span className="civ-mobile-thought-short">{thought.short}</span>
    </span>
  </button>
  <footer><span>{String(thought.lensCount).padStart(2, "0")} LENSES</span><button type="button" onClick={() => onShare(thought.source)}>{t("分享")} ↗</button>{thought.canEdit && <button type="button" onClick={() => onEdit(thought.source)}>{t("編輯")} ↗</button>}<button type="button" onClick={() => onRead(thought.id)}>{t("開啟閱讀")} →</button></footer>
</article>;

const MobileDomainStrip = ({ domains, activeFilter, onFilter }) => <nav className="civ-mobile-domains" aria-label={t("篩選")}>{domains.map(domain => <button type="button" key={domain.key} data-domain={domain.key} style={domain.style} className={activeFilter === domain.key ? "is-active" : ""} onClick={() => onFilter(domain.key)}>{domain.label}</button>)}</nav>;

const MobileChronology = ({ thoughts, domains, activeFilter, onFilter, selectedId, loadError, onRetry, onRead }) => {
  const themeDomain = domains.find(domain => domain.key === activeFilter) || domains[0];
  return <section className="civ-mobile-chronology" data-domain={themeDomain.key} style={themeDomain.style}>
  <header className="civ-mobile-chronology-head">
    <div><span>B / CHRONOLOGY</span><strong>{t("思想如何形成")}</strong><p>{t("按時間閱讀問題如何被提出、修正與連接。")}</p></div>
    <aside><b>{String(thoughts.length).padStart(2, "0")}</b><span>QUESTION<br/>OBJECTS</span></aside>
    <i className="civ-mobile-chrono-disc" aria-hidden="true"/>
    <i className="civ-mobile-chrono-frame" aria-hidden="true"/>
    <i className="civ-mobile-chrono-bar is-red" aria-hidden="true"/>
    <i className="civ-mobile-chrono-bar is-blue" aria-hidden="true"/>
    <i className="civ-mobile-chrono-bar is-green" aria-hidden="true"/>
  </header>
  <MobileDomainStrip domains={domains} activeFilter={activeFilter} onFilter={onFilter}/>
  {loadError && <div className="civ-mobile-error" role="alert"><span>{loadError}</span><button type="button" onClick={onRetry}>{t("重新載入")}</button></div>}
  {!thoughts.length ? <div className="civ-mobile-empty">{t("沒有符合條件的思考對象")}</div> : <ol className="civ-mobile-timeline">{thoughts.map((thought, index) => <li key={thought.id} data-domain={thought.domainKey} style={thought.style} className={thought.id === selectedId ? "is-current" : ""}>
    <div className="civ-mobile-time"><time>{thought.date}</time><b>{String(index + 1).padStart(2, "0")}</b></div>
    <button type="button" className="civ-mobile-time-card" onClick={() => onRead(thought.id)}>
      <span className="civ-mobile-time-domain">{thought.domainEn.toUpperCase()} / {thought.domainLabel}</span>
      <strong>{thought.title}</strong>
      <p>{thought.short}</p>
      {!!thought.relations.length && <small>{thought.relations.slice(0, 2).map((relation, relationIndex) => <span key={relationIndex}>↳ {relation}</span>)}</small>}
      <footer><span>{String(thought.lensCount).padStart(2, "0")} LENSES</span><b>{thought.id === selectedId ? t("目前閱讀") : t("開啟閱讀")} →</b></footer>
    </button>
  </li>)}</ol>}
</section>;
};

const MobileReader = ({ reader, thoughts, onSelect, onBack, onShare, onEdit }) => {
  if (!reader) return <div className="civ-mobile-empty">{t("尚無可閱讀內容")}</div>;
  return <section className="civ-mobile-reader" data-domain={reader.domainKey} style={reader.style}>
    <nav className="civ-mobile-reader-index" aria-label={t("問題")}>{thoughts.map(thought => <button type="button" key={thought.id} data-domain={thought.domainKey} style={thought.style} className={thought.id === reader.id ? "is-active" : ""} onClick={() => onSelect(thought.id)}><b>{thought.no}</b><span>{thought.domainEn.toUpperCase()}</span></button>)}</nav>
    <article className="civ-mobile-reader-cover">
      <header><span>C / READING POSTER</span><time>{reader.date}</time></header>
      <div className="civ-mobile-reader-figure"><strong>{reader.no}</strong><i aria-hidden="true"/><span>{reader.domainEn.toUpperCase()}<br/>{reader.domainLabel}</span></div>
      <span className="civ-mobile-reader-kicker">QUESTION OBJECT / {t("目前閱讀")}</span>
      <h1>{reader.title}</h1>
      {reader.quote && <blockquote><span>READING QUOTE / {t("閱讀引語")}</span>{reader.quote}</blockquote>}
      <p>{reader.thesis || reader.short}</p>
      <footer><button type="button" onClick={onBack}>← {t("返回問題")}</button><button type="button" onClick={() => onShare(reader.source)}>{t("分享")} ↗</button>{reader.canEdit && <button type="button" onClick={() => onEdit(reader.source)}>{t("編輯內容")} ↗</button>}</footer>
    </article>
    <article className="civ-mobile-reading-body">
      <header><span>ARTICLE / {t("正文")}</span><b>{String(reader.sections.length).padStart(2, "0")} SECTIONS</b></header>
      {reader.sections.length ? reader.sections.map((section, index) => <section key={index} className="civ-mobile-reading-section">
        <div><strong>{section.marker || String(index + 1).padStart(2, "0")}</strong><span>{section.kicker || `SECTION ${String(index + 1).padStart(2, "0")}`}</span></div>
        <h2>{section.heading}</h2>
        {section.paragraphs.map((paragraph, paragraphIndex) => <p key={paragraphIndex}>{paragraph}</p>)}
      </section>) : <div className="civ-mobile-empty">{t("尚無可閱讀內容")}</div>}
    </article>
    <section className="civ-mobile-lenses">
      <header><span>CHANGE THE LENS / {t("觀看視角")}</span><b>{String(reader.lenses.length).padStart(2, "0")}</b></header>
      {reader.lenses.length ? reader.lenses.map((lens, index) => <article key={index}><strong>{String(index + 1).padStart(2, "0")}</strong><div><h3>{lens.name}</h3><p>{lens.text}</p></div></article>) : <div className="civ-mobile-empty">{t("尚未添加視角")}</div>}
    </section>
  </section>;
};

const CivilizationMobileA = props => {
  const {
    view, onView, domains, activeFilter, onFilter, query, onQuery,
    thoughts, allCount, lensCount, selectedId, readerModel, loadError, onRetry,
    onNew, onCli, onRead, onShare, onEdit,
  } = props;
  const setView = next => next === "new" ? onNew() : onView(next);

  return <section className="civ-mobile-a" data-view={view}>
    <header className="civ-mobile-topbar">
      <div className="civ-mobile-brand"><i aria-hidden="true"/><span>BONFIRE PLATFORM<br/>CIVILIZATION / {t("文明")}</span></div>
      <div className="civ-mobile-top-actions"><button type="button" onClick={onCli}>CLI</button><button type="button" onClick={onNew}>＋</button></div>
    </header>

    {view === "a" ? <>
      <section className="civ-mobile-hero">
        <span className="civ-mobile-kicker">MODULE C1 · {t("共享觀看方式").toUpperCase()}</span>
        <h1>{t("文明")}</h1>
        <MobileWordmark/>
        <p>{t("分享答案之前，先分享我們如何提出問題。")} {t("這裡保存觀察世界的方法、判斷事物的尺度，以及思想彼此連接和變化的過程。")}</p>
        <aside><small>LIVE INDEX<br/>{new Date().getFullYear()}</small><strong>C1</strong></aside>
        <i className="civ-mobile-geometry" aria-hidden="true"/>
      </section>

      <section className="civ-mobile-filter-panel">
        <MobileDomainStrip domains={domains} activeFilter={activeFilter} onFilter={onFilter}/>
        <label className="civ-mobile-search"><span>⌕</span><input type="search" value={query} onChange={event => onQuery(event.target.value)} placeholder={t("搜索問題、方法或角度")}/></label>
      </section>

      {loadError && <div className="civ-mobile-error" role="alert"><span>{loadError}</span><button type="button" onClick={onRetry}>{t("重新載入")}</button></div>}
      <section className="civ-mobile-feed">
        <header><h2>{t("問題索引")}</h2><span>{String(allCount).padStart(2, "0")} QUESTIONS · {String(lensCount).padStart(2, "0")} LENSES</span></header>
        {!thoughts.length ? <div className="civ-mobile-empty">{t("沒有符合條件的思考對象")}</div> : thoughts.map(thought => <MobileThought key={thought.id} thought={thought} onRead={onRead} onShare={onShare} onEdit={onEdit}/>)}
      </section>
    </> : view === "b" ? <MobileChronology thoughts={thoughts} domains={domains} activeFilter={activeFilter} onFilter={onFilter} selectedId={selectedId} loadError={loadError} onRetry={onRetry} onRead={onRead}/> : <MobileReader reader={readerModel} thoughts={thoughts} onSelect={onRead} onBack={() => onView("a")} onShare={onShare} onEdit={onEdit}/>}

    <ViewNavigation view={view} onView={setView}/>
  </section>;
};

W2.CivilizationMobileA = CivilizationMobileA;
})();
