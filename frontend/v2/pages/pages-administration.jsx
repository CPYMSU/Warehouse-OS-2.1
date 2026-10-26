/* BONFIRE RESEARCH · administrative support, over the existing authorized routes. */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { Folio } = W2;
const { useState, useMemo } = React;

window.W2_LANG.addEN({
  "科研": "Research", "行政工作": "Administration", "主要導航": "Primary navigation", "業務總覽": "Business overview",
  "科研支援工作台": "Research support desk", "把行政事務集中處理，讓研究保持專注。": "Bring administrative work together so research can stay focused.",
  "回到科研": "Back to research", "行政工作子頁": "Administrative workspaces", "行政首頁": "Operations home",
  "研究向前。": "Research moves forward.", "後勤就位。": "Support stays ready.",
  "物資、預算、資產與合規，在同一個工作台協同。": "Materials, budgets, assets and compliance, together in one workspace.",
  "可用工作區": "Available workspaces", "工作分區": "Work areas", "科研主線": "Research comes first",
  "物資與資產": "Materials & assets", "營運與財務": "Operations & finance", "監測與分析": "Monitoring & analysis", "法務與合規": "Legal & compliance",
  "工作入口": "Workspaces", "全部工作": "All work", "搜尋行政功能": "Find a workspace", "名稱或工作內容…": "Name or type of work…",
  "收發、庫存與在途管理": "Receipts, inventory and shipments", "異常訊號與處理追蹤": "Exceptions and follow-up",
  "實物核對與差異處理": "Physical checks and reconciliation", "預算、成本與營運流程": "Budgets, costs and operating workflows",
  "帳務、憑證與收支管理": "Accounts, vouchers and cash flows", "金融與數字資產管理": "Financial and digital assets",
  "採購、供應商與招標流程": "Purchasing, suppliers and tenders", "合約、履約與法律事務": "Contracts, obligations and legal affairs",
  "位置、設施與空間資訊": "Locations, facilities and spatial information", "彙整分析與報表匯出": "Analysis and report exports",
  "跨業務的營運與管理視角": "An operating view across business functions", "進入工作區": "Open workspace",
  "沒有符合的行政功能": "No matching workspaces", "試試其他關鍵字，或切回全部工作。": "Try another search or switch to all work.",
  "集中處理，持續支援。": "Coordinated work. Continuous support.", "從行政回到研究": "Return to your research",
});

const GROUPS = [
  { id: "materials", code: "01", name: "物資與資產", color: "red" },
  { id: "finance", code: "02", name: "營運與財務", color: "yellow" },
  { id: "monitor", code: "03", name: "監測與分析", color: "blue" },
  { id: "legal", code: "04", name: "法務與合規", color: "ink" },
];
const MODULES = {
  warehouse: { code: "A01", en: "WAREHOUSE", group: "materials", copy: "收發、庫存與在途管理", mark: "grid" },
  inventory: { code: "A01", en: "INVENTORY", group: "materials", copy: "收發、庫存與在途管理", mark: "grid" },
  inbound: { code: "A01", en: "INBOUND", group: "materials", copy: "收發、庫存與在途管理", mark: "grid" },
  outbound: { code: "A01", en: "OUTBOUND", group: "materials", copy: "收發、庫存與在途管理", mark: "grid" },
  shipments: { code: "A01", en: "TRANSIT", group: "materials", copy: "收發、庫存與在途管理", mark: "grid" },
  alerts: { code: "A02", en: "SIGNALS", group: "monitor", copy: "異常訊號與處理追蹤", mark: "signal" },
  stocktake: { code: "A03", en: "STOCKTAKE", group: "materials", copy: "實物核對與差異處理", mark: "check" },
  erp: { code: "A04", en: "OPERATIONS", group: "finance", copy: "預算、成本與營運流程", mark: "flow" },
  finance: { code: "A05", en: "FINANCE", group: "finance", copy: "帳務、憑證與收支管理", mark: "ledger" },
  assets: { code: "A06", en: "ASSETS", group: "materials", copy: "金融與數字資產管理", mark: "asset" },
  procurement: { code: "A07", en: "PROCUREMENT", group: "materials", copy: "採購、供應商與招標流程", mark: "flow" },
  legal: { code: "A08", en: "LEGAL", group: "legal", copy: "合約、履約與法律事務", mark: "check" },
  gis: { code: "A09", en: "SPATIAL", group: "monitor", copy: "位置、設施與空間資訊", mark: "map" },
  reports: { code: "A10", en: "REPORTS", group: "monitor", copy: "彙整分析與報表匯出", mark: "ledger" },
  dashboard: { code: "A00", en: "OVERVIEW", group: "finance", copy: "跨業務的營運與管理視角", mark: "signal" },
};
const detailsOf = item => ({ ...MODULES[item.id], ...item });
const activeModule = (items, route) => items.find(item => (item.activeRoutes || [item.id]).includes(route));

const ModuleMark = ({ kind }) => <svg viewBox="0 0 100 64" fill="none" aria-hidden="true">
  <path className="admin-mark-guide" d="M8 54H92M18 8V58M44 8V58M70 8V58"/>
  {kind === "grid" ? <><path d="M24 15H82V49H24ZM24 32H82M43 15V49M63 15V49"/><rect className="admin-mark-accent" x="64" y="34" width="16" height="13"/></>
    : kind === "signal" ? <><path d="M9 38H25L35 15L50 49L63 26L73 38H92"/><circle className="admin-mark-accent" cx="63" cy="26" r="4"/></>
    : kind === "check" ? <><path d="M29 10H75V54H29ZM38 22H65M38 31H54M38 40H51"/><path className="admin-mark-accent-stroke" d="M57 39L64 46L81 28"/></>
    : kind === "map" ? <><path d="M16 15L38 10L62 18L84 12V49L62 55L38 47L16 53ZM38 10V47M62 18V55"/><circle className="admin-mark-accent" cx="55" cy="30" r="5"/></>
    : kind === "asset" ? <><path d="M17 25L50 9L83 25L50 42ZM17 25V43L50 59L83 43V25M50 42V59"/><path className="admin-mark-accent-stroke" d="M34 17L67 33V50"/></>
    : kind === "flow" ? <><path d="M14 18H37V41H14ZM63 18H86V41H63ZM37 29H63M48 21L56 29L48 37"/><rect className="admin-mark-accent" x="19" y="23" width="13" height="13"/></>
    : <><path d="M20 10H80V54H20ZM29 21H71M29 32H71M29 43H71M48 16V49"/><rect className="admin-mark-accent" x="53" y="36" width="16" height="8"/></>}
</svg>;

const AdministrativeFrame = ({ modules = [], route, researchAvailable, children }) => {
  const home = route === "administration";
  const active = activeModule(modules, route);
  return <div className={"admin-workspace" + (home ? " is-home" : " is-module")} data-testid="administrative-workspace">
    {home ? <Folio no="A00" en="RESEARCH SUPPORT / OPERATIONS" title={t("行政工作")} sub={t("把行政事務集中處理，讓研究保持專注。")}
      right={researchAvailable && <a className="btn admin-back-research" href="#/research">{t("回到科研")} ↗</a>}/>
      : <div className="admin-context"><a href="#/administration"><span>OPERATIONS /</span> {t("行政工作")}</a><i>/</i><b>{t(active && active.label || "行政工作")}</b>{researchAvailable && <a className="admin-context-research" href="#/research">{t("回到科研")} ↗</a>}</div>}
    <nav className="admin-subnav" aria-label={t("行政工作子頁")}>
      {[{ id: "administration", label: "行政首頁", code: "00" }, ...modules.map(item => ({ ...item, code: (MODULES[item.id] || {}).code || item.idx }))].map(item => {
        const on = item.id === "administration" ? home : !!active && item.id === active.id;
        return <a key={item.id} href={"#/" + item.id} aria-current={on ? "page" : undefined} className={on ? "active" : ""}><span>{item.code}</span>{t(item.label)}</a>;
      })}
    </nav>
    <div className="admin-workspace-content">{children}</div>
  </div>;
};

const PageAdministration = ({ administrativeItems = [], researchAvailable }) => {
  const [group, setGroup] = useState("all");
  const [query, setQuery] = useState("");
  const items = useMemo(() => administrativeItems.filter(item => item.id !== "dashboard").map(detailsOf), [administrativeItems]);
  const groups = GROUPS.filter(section => items.some(item => item.group === section.id));
  const visible = items.filter(item => (group === "all" || item.group === group) &&
    [item.label, item.en, item.copy, t(item.label), t(item.copy)].join(" ").toLowerCase().includes(query.trim().toLowerCase()));
  const overview = administrativeItems.find(item => item.id === "dashboard");
  return <div className="admin-hub" data-testid="administrative-hub">
    <section className="admin-race-hero" aria-label={t("科研支援工作台")}>
      <div className="admin-hero-copy"><div className="admin-race-kicker"><span className="admin-checker" aria-hidden="true"/> RESEARCH FIRST / SUPPORT READY</div>
        <h2>{t("研究向前。")}<br/><em>{t("後勤就位。")}</em></h2>
        <p>{t("物資、預算、資產與合規，在同一個工作台協同。")}</p>
        <div className="admin-hero-links">{researchAvailable && <a href="#/research">{t("回到科研")} ↗</a>}{overview && <a href="#/dashboard">{t("業務總覽")} →</a>}</div>
      </div>
      <div className="admin-race-board"><div className="admin-board-label"><span>OPERATIONS / SUPPORT GRID</span><span className="admin-checker" aria-hidden="true"/></div>
        <div className="admin-track" aria-hidden="true"><svg viewBox="0 0 500 220" fill="none"><path className="admin-track-wide" d="M24 164H124Q159 164 173 130L203 60Q217 27 252 27H374Q425 27 425 78V138Q425 185 378 185H285"/><path className="admin-track-center" d="M24 164H124Q159 164 173 130L203 60Q217 27 252 27H374Q425 27 425 78V138Q425 185 378 185H285"/><path className="admin-track-signal" d="M24 164H124Q159 164 173 130L203 60Q217 27 252 27H308"/><rect x="304" y="10" width="9" height="34" fill="#f1cf20"/><path d="M239 119H368M239 133H331M239 147H351" stroke="#f4f1e9" strokeWidth="3" opacity=".45"/><text x="34" y="140">SCIENCE</text><text x="287" y="210">SUPPORT</text><circle cx="425" cy="108" r="6" fill="#f1cf20"/></svg></div>
        <div className="admin-race-totals"><div><b>{String(items.length).padStart(2, "0")}</b><span>{t("可用工作區")}</span></div><div><b>{String(groups.length).padStart(2, "0")}</b><span>{t("工作分區")}</span></div><div><b>01</b><span>{t("科研主線")}</span></div></div>
      </div>
    </section>
    <div className="admin-work-controls"><nav aria-label={t("工作分區")}><button type="button" className={group === "all" ? "active" : ""} aria-pressed={group === "all"} onClick={() => setGroup("all")}><span>ALL</span>{t("全部工作")}<b>{items.length}</b></button>{groups.map(section => <button type="button" key={section.id} className={(group === section.id ? "active " : "") + section.color} aria-pressed={group === section.id} onClick={() => setGroup(section.id)}><span>{section.code}</span>{t(section.name)}<b>{items.filter(item => item.group === section.id).length}</b></button>)}</nav>
      <label><span>{t("搜尋行政功能")}</span><input type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder={t("名稱或工作內容…")}/></label>
    </div>
    <section className="admin-module-section"><header><h3><small>WORKSPACES / INDEX</small>{t("工作入口")}</h3><span>{String(visible.length).padStart(2, "0")} / {String(items.length).padStart(2, "0")}</span></header>
      <div className="admin-module-grid">{visible.map(item => {
        const section = GROUPS.find(candidate => candidate.id === item.group) || GROUPS[0];
        return <a key={item.id} href={"#/" + item.id} data-module={item.id} className={"admin-module-card lane-" + section.color}>
          <div className="admin-card-register"><span>{item.code} / {item.en}</span><span className="admin-card-lane"/></div>
          <div className="admin-card-art"><ModuleMark kind={item.mark}/><b>{item.code.slice(1)}</b></div>
          <h4>{t(item.label)}</h4><p>{t(item.copy)}</p>
          <footer><span>{t("進入工作區")}</span><b>↗</b></footer>
        </a>;
      })}</div>
      {!visible.length && <div className="admin-empty" role="status"><h4>{t("沒有符合的行政功能")}</h4><p>{t("試試其他關鍵字，或切回全部工作。")}</p></div>}
    </section>
    <footer className="admin-finish"><span className="admin-checker" aria-hidden="true"/><div><b>{t("集中處理，持續支援。")}</b><small>RESEARCH / OPERATIONS / CONTINUITY</small></div>{researchAvailable && <a href="#/research">{t("從行政回到研究")} ↗</a>}</footer>
  </div>;
};
W2.AdministrativeFrame = AdministrativeFrame;
W2.PAGES.administration = PageAdministration;
})();
