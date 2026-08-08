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

const CivilizationMobileA = props => {
  const {
    view, onView, domains, activeFilter, onFilter, query, onQuery,
    thoughts, allCount, lensCount, chronology, reader, loadError, onRetry,
    onNew, onCli, onRead, onShare, onEdit,
  } = props;
  const setView = next => next === "new" ? onNew() : onView(next);
  const alternateView = view === "b" ? chronology : reader;

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
        <nav className="civ-mobile-domains" aria-label={t("篩選")}>{domains.map(domain => <button type="button" key={domain.key} data-domain={domain.key} style={domain.style} className={activeFilter === domain.key ? "is-active" : ""} onClick={() => onFilter(domain.key)}>{domain.label}</button>)}</nav>
        <label className="civ-mobile-search"><span>⌕</span><input type="search" value={query} onChange={event => onQuery(event.target.value)} placeholder={t("搜索問題、方法或角度")}/></label>
      </section>

      {loadError && <div className="civ-mobile-error" role="alert"><span>{loadError}</span><button type="button" onClick={onRetry}>{t("重新載入")}</button></div>}
      <section className="civ-mobile-feed">
        <header><h2>{t("問題索引")}</h2><span>{String(allCount).padStart(2, "0")} QUESTIONS · {String(lensCount).padStart(2, "0")} LENSES</span></header>
        {!thoughts.length ? <div className="civ-mobile-empty">{t("沒有符合條件的思考對象")}</div> : thoughts.map(thought => <MobileThought key={thought.id} thought={thought} onRead={onRead} onShare={onShare} onEdit={onEdit}/>)}
      </section>
    </> : <main className="civ-mobile-stage">{alternateView}</main>}

    <ViewNavigation view={view} onView={setView}/>
  </section>;
};

W2.CivilizationMobileA = CivilizationMobileA;
})();
