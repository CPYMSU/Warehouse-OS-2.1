/* ============================================================
   App 殼層 — 左側導航 + 頂部欄
   ============================================================ */

// 物資台賬導航:按當前租戶的功能分類動態生成(取代寫死的電網三類),id 用 "ledger:<分類id>"
const LEDGER_NAV_ICON = { hardware_material: "link", safety_tool: "shield", maintenance_tool: "gear", consumable: "link", returnable: "swap" };
const ledgerNavItems = () => {
  const cats = Array.isArray(window.LEDGER_CATEGORIES) ? window.LEDGER_CATEGORIES : [];
  return cats.map(c => ({ id: "ledger:" + c.id, icon: LEDGER_NAV_ICON[c.id] || (c.requires_return ? "shield" : "link"), label: c.name }));
};

const buildNavGroups = (isOwner) => [
  {
    title: "ERP 工作台",
    items: [
      { id: "erp", icon: "layers", label: "ERP 中樞", hot: true },
      { id: "finance", icon: "chart", label: "AI 財務", hot: true },
      { id: "assets", icon: "activity", label: "資產管理", hot: true },
      { id: "overview", icon: "grid", label: "倉儲總覽" },
      { id: "collab", icon: "sparkle", label: "AI 協作" },
      { id: "alerts", icon: "alert", label: "智能預警" },
      { id: "procurement", icon: "clipboard", label: "招採工作流", hot: true },
      { id: "legal", icon: "shield", label: "法務合規", hot: true },
    ],
  },
  {
    title: "庫存作業",
    items: [
      { id: "inventory", icon: "box", label: "庫存管理" },
      { id: "inbound", icon: "inbound", label: "入庫管理" },
      { id: "outbound", icon: "outbound", label: "出庫領用" },
      { id: "stocktake", icon: "clipboard", label: "盤點管理" },
      { id: "map", icon: "map", label: "庫位地圖" },
      { id: "wh_gis", icon: "map2", label: "倉庫地圖 GIS" },
    ],
  },
  {
    title: "系統管理",
    items: [
      { id: "ai", icon: "cpu", label: "AI 秘書", hot: true },
      { id: "datahub", icon: "inbound", label: "數據中轉站", hot: true },
      { id: "shield", icon: "shield", label: "安全中樞", hot: true },
      { id: "terminal", icon: "scan", label: "平臺終端" },
      { id: "reports", icon: "chart", label: "報表中心" },
      { id: "logs", icon: "clock", label: "操作日誌" },
      { id: "perms", icon: "shield", label: "人員權限" },
      { id: "settings", icon: "gear", label: "系統設置" },
      // 僅平台擁有者(超級管理員)可見:跨公司管理 + 平台運營後台入口(外鏈,新分頁開啟)
      ...(isOwner ? [
        { id: "companies", icon: "layers", label: "公司管理" },
        { id: "platform-console", icon: "forward", label: "運營後台", href: "platform.html" },
      ] : []),
    ],
  },
];
// 按公司自定義導航:套用平台運營員設置的 window.NAV_CONFIG(逐項覆蓋名稱 / 隱藏 / 排序)
const applyNavConfig = (groups) => {
  const cfg = (window.NAV_CONFIG && window.NAV_CONFIG.items) || {};
  return groups.map(group => {
    const items = group.items
      .map((it, idx) => {
        const ov = cfg[it.id] || {};
        return { ...it, label: ov.label || it.label, _order: (ov.order != null ? ov.order : idx), _hidden: !!ov.hidden };
      })
      .filter(it => !it._hidden)
      .sort((a, b) => a._order - b._order);
    return { ...group, items };
  }).filter(group => group.items.length > 0);
};
// 自定義數據模塊:從 bootstrap 的 CUSTOM_MODULES 注入導航項到其所屬分組(id="custom:<key>")
// 「物資台賬」組已退役 → 歷史落在該組的模塊併入「庫存作業」,避免從導航消失
const navGroupOf = (m) => { const g = m.nav_group || "系統管理"; return g === "物資台賬" ? "庫存作業" : g; };
const injectCustomModules = (groups) => {
  const mods = window.CUSTOM_MODULES || [];
  if (!mods.length) return groups;
  return groups.map(group => {
    const extra = mods.filter(m => navGroupOf(m) === group.title)
      .map(m => ({ id: "custom:" + m.key, icon: m.icon || "layers", label: m.name }));
    return extra.length ? { ...group, items: group.items.concat(extra) } : group;
  });
};
const navGroupsFor = (isOwner) => applyNavConfig(injectCustomModules(buildNavGroups(isOwner)));
const buildNav = (isOwner) => [].concat(...navGroupsFor(isOwner).map(group => group.items));

const Sidebar = ({ active, onNav, brand, isOwner }) => (
  <aside className="app-sidebar" style={{
    width: "var(--side-w)", flexShrink: 0, height: "100vh", position: "relative", zIndex: 5,
    background: "var(--glass-strong)", backdropFilter: "blur(22px) saturate(150%)",
    WebkitBackdropFilter: "blur(22px) saturate(150%)", borderRight: "1px solid var(--line)",
    display: "flex", flexDirection: "column", padding: "0 14px",
  }}>
    <div className="row gap-12 app-sidebar-brand" style={{ height: "var(--top-h)", padding: "0 8px", flexShrink: 0 }}>
      <div style={{ width: 38, height: 38, borderRadius: 11, background: "var(--grad)", display: "grid", placeItems: "center", boxShadow: "var(--sh-blue)", flexShrink: 0 }}>
        <Icon name="logo" size={21} color="#fff" sw={2}/>
      </div>
      <div className="col" style={{ lineHeight: 1.2, minWidth: 0 }}>
        <div style={{ fontWeight: 800, fontSize: 14.5, letterSpacing: "-0.01em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{brand || "倉儲管理"}</div>
        <div style={{ fontSize: 10.5, color: "var(--ink-4)", fontWeight: 600, letterSpacing: ".04em" }}>WAREHOUSE OS 2.0</div>
      </div>
    </div>

    <div className="scroll-y app-sidebar-scroll" style={{ flex: 1, marginTop: 8, paddingBottom: 16 }}>
      {navGroupsFor(isOwner).map((group, idx) => (
        <div key={group.title} className="app-nav-group" style={{ marginTop: idx ? 14 : 0 }}>
          <div className="eyebrow app-nav-group-title" style={{ padding: "10px 10px 7px" }}>{group.title}</div>
          <nav className="col gap-3 app-nav-list">
            {group.items.map(n => <NavItem key={n.id} item={n} active={active === n.id}
              onClick={() => n.href ? window.open(n.href, "_blank", "noopener") : onNav(n.id)}/>)}
          </nav>
        </div>
      ))}
    </div>

    <div style={{ flexShrink: 0, margin: "0 2px 16px", padding: 14, borderRadius: 14,
      background: "linear-gradient(135deg, rgba(27,107,255,0.10), rgba(7,182,162,0.10))",
      border: "1px solid rgba(27,107,255,0.16)" }}>
      <div className="row gap-8" style={{ marginBottom: 8 }}>
        <span style={{ position: "relative", width: 8, height: 8 }}>
          <span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "var(--ok)" }}/>
          <span style={{ position: "absolute", inset: -3, borderRadius: "50%", background: "var(--ok)", opacity: .3, animation: "fadeIn 1s infinite alternate" }}/>
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, color: "var(--ink-2)", whiteSpace: "nowrap" }}>AI 服務</span>
      </div>
      <div style={{ fontSize: 11.5, color: "var(--ink-3)", lineHeight: 1.5 }}>專屬 AI 助理 · 權限內直接執行 · 全程審計可回放</div>
    </div>
  </aside>
);

const NavItem = ({ item, active, onClick }) => (
  <button className={"app-nav-item" + (active ? " is-active" : "")} data-nav-id={item.id} onClick={onClick} style={{
    display: "flex", alignItems: "center", gap: 11, height: 42, padding: "0 12px",
    borderRadius: 11, fontSize: 13.5, fontWeight: 600, width: "100%", textAlign: "left",
    color: active ? "#fff" : "var(--ink-2)",
    background: active ? "var(--grad)" : "transparent",
    boxShadow: active ? "var(--sh-blue)" : "none",
    transition: "all .16s ease", position: "relative",
  }}
  onMouseEnter={e => { if (!active) e.currentTarget.style.background = "rgba(14,26,43,0.05)"; }}
  onMouseLeave={e => { if (!active) e.currentTarget.style.background = "transparent"; }}>
    <Icon name={item.icon} size={18} sw={active ? 2 : 1.8}/>
    <span style={{ flex: 1 }}>{item.label}</span>
    {item.badge && <span style={{ minWidth: 18, height: 18, padding: "0 5px", borderRadius: 9, fontSize: 11, fontWeight: 700,
      display: "grid", placeItems: "center", background: active ? "rgba(255,255,255,0.25)" : "var(--danger)", color: "#fff" }} className="num">{item.badge}</span>}
    {item.hot && !active && <span className="app-nav-hot" style={{ fontSize: 9, fontWeight: 800, letterSpacing: ".06em", color: "var(--teal)", background: "var(--teal-soft)", padding: "2px 6px", borderRadius: 6 }}>統一</span>}
  </button>
);

const NOTIF_KIND_ICON = {
  collab: "sparkle",
  alert: "alert",
  return: "clock",
  ai_action: "cpu",
  finance_clarification: "chart",
  registration: "user",
  membership: "shield",
  erp_inventory: "clipboard",
  company_signup: "layers",
};

const NOTIF_TONES = {
  danger: { color: "var(--danger)", soft: "var(--danger-soft)" },
  urgent: { color: "var(--danger)", soft: "var(--danger-soft)" },
  warning: { color: "var(--warn)", soft: "var(--warn-soft)" },
  info: { color: "var(--blue)", soft: "var(--blue-soft)" },
};

// 頂欄真實日期/星期(本地即時)+ 真實天氣(後端 /api/weather 代理 Open-Meteo)
const TOP_WEEKDAYS = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];
const TopDateWeather = () => {
  const [weather, setWeather] = React.useState(null);
  const now = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  const dateStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const weekday = TOP_WEEKDAYS[now.getDay()];
  React.useEffect(() => {
    const f = window.authFetch || fetch;
    f("/api/weather").then((r) => r.json()).then((d) => { if (d && d.ok) setWeather(d); }).catch(() => {});
  }, []);
  const sub = weather && weather.text
    ? `${weekday} · ${weather.city} ${weather.text}${weather.temperature != null ? " " + Math.round(weather.temperature) + "°" : ""}`
    : weekday;
  return (
    <div className="col" style={{ alignItems: "flex-end", lineHeight: 1.3, whiteSpace: "nowrap" }}>
      <div className="num" style={{ fontSize: 14, fontWeight: 700 }}>{dateStr}</div>
      <div style={{ fontSize: 11, color: "var(--ink-4)" }}>{sub}</div>
    </div>
  );
};

const TopBar = ({ wh, setWh, lang, setLang, currentUser, onLogout, onChangePassword, companies = [], tenant, onSwitchCompany, onJoinCompany, canApplyCompany, onApplyCompany, onNavigate }) => {
  const [open, setOpen] = React.useState(false);
  const [coOpen, setCoOpen] = React.useState(false);
  const [notifOpen, setNotifOpen] = React.useState(false);
  const [notifBusy, setNotifBusy] = React.useState(false);
  const [notifError, setNotifError] = React.useState("");
  const [notifData, setNotifData] = React.useState({ count: 0, counts: {}, items: [] });
  const notifSeenRef = React.useRef(new Set());
  const displayName = currentUser?.display_name || currentUser?.username || "未登入";
  const roleName = (currentUser?.role_names || [])[0] || currentUser?.role || "未綁定角色";
  const initial = (displayName || currentUser?.username || "?").trim().slice(0, 1).toUpperCase();
  const currentCompany = companies.find((c) => c.slug === tenant);
  const loadNotifications = React.useCallback(async () => {
    if (!currentUser?.id) {
      setNotifData({ count: 0, counts: {}, items: [] });
      return;
    }
    setNotifBusy(true);
    setNotifError("");
    try {
      const res = await window.authFetch("/api/notifications/summary");
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || "通知載入失敗");
      setNotifData({
        count: Number(data.count || 0),
        counts: data.counts || {},
        items: Array.isArray(data.items) ? data.items : [],
        updated_at: data.updated_at || "",
      });
    } catch (err) {
      setNotifError(err.message || "通知載入失敗");
    } finally {
      setNotifBusy(false);
    }
  }, [currentUser?.id, tenant]);

  const markNotificationsSeen = React.useCallback(async (items) => {
    if (!currentUser?.id || !Array.isArray(items) || !items.length) return;
    const ids = items
      .filter((item) => item?.kind === "collab" && item?.meta?.seen_action === "read" && item?.meta?.message_id)
      .map((item) => Number(item.meta.message_id))
      .filter((id) => id > 0 && !notifSeenRef.current.has(id));
    if (!ids.length) return;
    ids.forEach((id) => notifSeenRef.current.add(id));

    setNotifData((prev) => {
      const idSet = new Set(ids);
      const removed = (prev.items || []).filter((item) => idSet.has(Number(item?.meta?.message_id))).length;
      const counts = { ...(prev.counts || {}) };
      counts.collab_unread = Math.max(0, Number(counts.collab_unread || 0) - removed);
      return {
        ...prev,
        count: Math.max(0, Number(prev.count || 0) - removed),
        counts,
        items: (prev.items || []).filter((item) => !idSet.has(Number(item?.meta?.message_id))),
      };
    });

    try {
      const res = await window.authFetch("/api/notifications/seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collab_message_ids: ids }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || "通知狀態同步失敗");
      if (data.summary) {
        setNotifData({
          count: Number(data.summary.count || 0),
          counts: data.summary.counts || {},
          items: Array.isArray(data.summary.items) ? data.summary.items : [],
          updated_at: data.summary.updated_at || "",
        });
      }
    } catch (err) {
      ids.forEach((id) => notifSeenRef.current.delete(id));
      setNotifError(err.message || "通知狀態同步失敗");
    }
  }, [currentUser?.id, tenant]);

  // 一鍵全讀:把本賬號所有未讀協作消息(含未展開的)一次標為已讀
  const markAllNotificationsSeen = React.useCallback(async () => {
    if (!currentUser?.id || notifBusy) return;
    setNotifBusy(true);
    setNotifError("");
    try {
      const res = await window.authFetch("/api/notifications/seen", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mark_all: true }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || "全部已讀失敗");
      if (data.summary) {
        setNotifData({
          count: Number(data.summary.count || 0),
          counts: data.summary.counts || {},
          items: Array.isArray(data.summary.items) ? data.summary.items : [],
          updated_at: data.summary.updated_at || "",
        });
      } else {
        await loadNotifications();
      }
    } catch (err) {
      setNotifError(err.message || "全部已讀失敗");
    } finally {
      setNotifBusy(false);
    }
  }, [currentUser?.id, notifBusy, loadNotifications]);

  React.useEffect(() => {
    loadNotifications();
    const timer = window.setInterval(loadNotifications, 60000);
    return () => window.clearInterval(timer);
  }, [loadNotifications]);

  const notifCount = Number(notifData.count || 0);
  const notifItems = Array.isArray(notifData.items) ? notifData.items : [];
  const collabUnread = Number((notifData.counts || {}).collab_unread || 0);
  React.useEffect(() => {
    if (!notifOpen || !notifItems.length) return undefined;
    const timer = window.setTimeout(() => markNotificationsSeen(notifItems), 1200);
    return () => window.clearTimeout(timer);
  }, [notifOpen, notifItems, markNotificationsSeen]);

  const openNotifications = () => {
    setNotifOpen(!notifOpen);
    setOpen(false);
    setCoOpen(false);
    if (!notifOpen) loadNotifications();
  };
  const jumpNotification = (item) => {
    setNotifOpen(false);
    if (item?.kind === "wf_task" && item?.meta?.task_id) window.WF_FOCUS_TASK = item.meta.task_id;  // 工作流待办深链
    if (item?.page && onNavigate) onNavigate(item.page);
    if (item?.meta?.agent_prompt) {
      const open = () => {
        if (window.openUnifiedAgent) window.openUnifiedAgent(item.meta.agent_prompt, { autoAsk: item.meta.agent_auto_ask !== false });
        else window.dispatchEvent(new CustomEvent("company-secretary-open", { detail: { prompt: item.meta.agent_prompt, autoAsk: item.meta.agent_auto_ask !== false } }));
      };
      window.setTimeout(open, 80);
    }
  };

  return (
    <header className="app-topbar" style={{
      height: "var(--top-h)", flexShrink: 0, position: "relative", zIndex: 4,
      display: "flex", alignItems: "center", gap: 18, padding: "0 28px",
      background: "var(--glass)", backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)",
      borderBottom: "1px solid var(--line)",
    }}>
      {/* 公司切換器(Model B:跨公司全局身份)*/}
      <div className="app-company-switcher" style={{ position: "relative" }}>
        <button className="row gap-10" onClick={() => setCoOpen(!coOpen)} title="切換公司"
          style={{ height: 44, padding: "0 14px", borderRadius: 12, border: "1px solid var(--line)", background: "var(--grad-soft)" }}>
          <Icon name="layers" size={17} color="var(--blue)"/>
          <span style={{ fontWeight: 800, fontSize: 14 }}>{currentCompany ? currentCompany.name : (tenant || "—")}</span>
          <Icon name="chevronDown" size={15} color="var(--ink-4)"/>
        </button>
        {coOpen && (
          <div className="card fade-up" style={{ position: "absolute", top: 50, left: 0, width: 248, padding: 6, zIndex: 31 }}>
            <div className="eyebrow" style={{ padding: "8px 10px 6px" }}>我的公司</div>
            {companies.length === 0 && <div className="muted" style={{ padding: "4px 12px 8px", fontSize: 12.5 }}>暫無公司</div>}
            {companies.map((c) => (
              <button key={c.slug} onClick={() => { setCoOpen(false); onSwitchCompany && onSwitchCompany(c.slug); }} className="row spread"
                style={{ width: "100%", minHeight: 40, padding: "6px 12px", borderRadius: 9, fontSize: 13.5, fontWeight: 600, textAlign: "left",
                  color: c.slug === tenant ? "var(--blue)" : "var(--ink-2)", background: c.slug === tenant ? "var(--blue-soft)" : "transparent" }}>
                <span className="col gap-2"><span>{c.name}</span><span className="num muted" style={{ fontSize: 11 }}>/{c.slug}{c.role ? " · " + c.role : ""}</span></span>
                {c.slug === tenant && <Icon name="check" size={15}/>}
              </button>
            ))}
            <div style={{ height: 1, background: "var(--line)", margin: "6px 0" }}/>
            <button className="row gap-8" onClick={() => { setCoOpen(false); onJoinCompany && onJoinCompany(); }}
              style={{ width: "100%", height: 38, padding: "0 12px", borderRadius: 9, fontSize: 13, color: "var(--blue)", fontWeight: 700 }}>
              <Icon name="plus" size={15}/>加入已有公司
            </button>
            {canApplyCompany && (
              <button className="row gap-8" onClick={() => { setCoOpen(false); onApplyCompany && onApplyCompany(); }}
                style={{ width: "100%", height: 38, padding: "0 12px", borderRadius: 9, fontSize: 13, color: "var(--ink-2)", fontWeight: 700 }}>
                <Icon name="layers" size={15}/>申請開通公司
              </button>
            )}
          </div>
        )}
      </div>

      <div className="app-warehouse-switcher" style={{ position: "relative" }}>
        <button className="row gap-10" onClick={() => setOpen(!open)} style={{ height: 44, padding: "0 14px", borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface)" }}>
          <Icon name="map2" size={17} color="var(--blue)"/>
          <span style={{ fontWeight: 700, fontSize: 14 }}>{wh}</span>
          <Icon name="chevronDown" size={15} color="var(--ink-4)"/>
        </button>
        {open && (
          <div className="card fade-up" style={{ position: "absolute", top: 50, left: 0, width: 220, padding: 6, zIndex: 30 }}>
            {window.WAREHOUSES.map(w => (
              <button key={w} onClick={() => { setWh(w); setOpen(false); }} className="row spread" style={{ width: "100%", height: 40, padding: "0 12px", borderRadius: 9, fontSize: 13.5, fontWeight: 600, color: w === wh ? "var(--blue)" : "var(--ink-2)", background: w === wh ? "var(--blue-soft)" : "transparent" }}>
                {w}{w === wh && <Icon name="check" size={15}/>}
              </button>
            ))}
            <div style={{ height: 1, background: "var(--line)", margin: "6px 0" }}/>
            <button className="row gap-8" style={{ width: "100%", height: 38, padding: "0 12px", borderRadius: 9, fontSize: 13, color: "var(--ink-3)", fontWeight: 600 }}><Icon name="layers" size={15}/>全部倉庫匯總</button>
          </div>
        )}
      </div>

      <div className="app-top-spacer" style={{ flex: 1 }}/>

      <div className="row gap-4 app-lang-switcher" style={{ height: 36, padding: 3, borderRadius: 10, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
        {window.I18N.languages.map(item => (
          <button
            key={item.id}
            onClick={() => setLang(item.id)}
            title={item.id === "zh-Hant" ? "繁體中文" : "简体中文"}
            style={{
              minWidth: 34, height: 30, borderRadius: 8, fontSize: 12.5, fontWeight: 800,
              background: lang === item.id ? "var(--surface)" : "transparent",
              color: lang === item.id ? "var(--blue)" : "var(--ink-3)",
              boxShadow: lang === item.id ? "var(--sh-sm)" : "none",
            }}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="app-date-weather"><TopDateWeather/></div>

      <div className="app-notification-switcher" style={{ position: "relative" }}>
        <button onClick={openNotifications} title="通知中心" style={{
          position: "relative", width: 44, height: 44, borderRadius: 12,
          border: "1px solid var(--line)", background: notifOpen ? "var(--blue-soft)" : "var(--surface)",
          display: "grid", placeItems: "center", color: notifCount ? "var(--blue)" : "var(--ink-2)",
        }}>
          <Icon name="bell" size={19} color="currentColor"/>
          {notifCount > 0 && (
            <span className="num" style={{
              position: "absolute", top: 5, right: 5, minWidth: 17, height: 17, padding: "0 4px",
              borderRadius: 9, background: "var(--danger)", color: "#fff", border: "2px solid #fff",
              fontSize: 10, fontWeight: 800, display: "grid", placeItems: "center", lineHeight: 1,
            }}>{notifCount > 99 ? "99+" : notifCount}</span>
          )}
        </button>
        {notifOpen && (
          <div className="card fade-up" style={{
            position: "absolute", top: 50, right: 0, width: 380, maxWidth: "calc(100vw - 32px)",
            padding: 0, zIndex: 42, overflow: "hidden",
          }}>
            <div className="row spread" style={{ padding: "14px 14px 12px", borderBottom: "1px solid var(--line)" }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 800 }}>通知中心</div>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 3 }}>
                  {notifData.updated_at ? "更新 " + notifData.updated_at : "按當前公司匯總"}
                </div>
              </div>
              <div className="row gap-7">
                <button onClick={(e) => { e.stopPropagation(); markAllNotificationsSeen(); }} disabled={notifBusy || collabUnread === 0}
                  title="把所有未讀協作消息標為已讀" style={{ height: 34, padding: "0 11px", borderRadius: 10, display: "flex", alignItems: "center", gap: 6,
                    background: collabUnread ? "var(--grad)" : "var(--surface-2)", color: collabUnread ? "#fff" : "var(--ink-4)",
                    border: collabUnread ? "none" : "1px solid var(--line)", fontSize: 12, fontWeight: 800, cursor: collabUnread && !notifBusy ? "pointer" : "default" }}>
                  <Icon name="checkCircle" size={14} color="currentColor"/>全讀{collabUnread ? ` ${collabUnread}` : ""}
                </button>
                <button onClick={(e) => { e.stopPropagation(); loadNotifications(); }} disabled={notifBusy}
                  title="刷新通知" style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: "var(--surface-2)", border: "1px solid var(--line)" }}>
                  <Icon name="refresh" size={15} color={notifBusy ? "var(--ink-4)" : "var(--ink-3)"}/>
                </button>
              </div>
            </div>
            {notifError && (
              <div style={{ margin: 12, padding: 10, borderRadius: 10, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 12.5, fontWeight: 700 }}>
                {notifError}
              </div>
            )}
            <div className="scroll-y" style={{ maxHeight: 420, padding: notifItems.length ? 8 : 14 }}>
              {!notifItems.length && !notifBusy && (
                <div className="col center" style={{ minHeight: 126, gap: 8, color: "var(--ink-3)", textAlign: "center" }}>
                  <Icon name="checkCircle" size={28} color="var(--ok)"/>
                  <div style={{ fontSize: 13.5, fontWeight: 700 }}>暫無待處理通知</div>
                  <div className="muted" style={{ fontSize: 12 }}>協作消息、預警、審批和 ERP 待辦會出現在這裡。</div>
                </div>
              )}
              {!notifItems.length && notifBusy && (
                <div className="col center" style={{ minHeight: 126, gap: 8, color: "var(--ink-3)", textAlign: "center" }}>
                  <Icon name="refresh" size={24} color="var(--blue)"/>
                  <div style={{ fontSize: 13.5, fontWeight: 700 }}>正在載入通知</div>
                </div>
              )}
              {notifItems.map((item) => {
                const tone = NOTIF_TONES[item.severity] || NOTIF_TONES.info;
                const hasAgentAction = !!item?.meta?.agent_prompt;
                const clickable = hasAgentAction || (item.page && onNavigate);
                return (
                  <div key={item.id} role={clickable ? "button" : undefined} tabIndex={clickable ? 0 : -1}
                    onClick={() => clickable && jumpNotification(item)}
                    onKeyDown={(e) => { if (clickable && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); jumpNotification(item); } }}
                    style={{
                      width: "100%", minHeight: 70, padding: "10px 11px", borderRadius: 10,
                      display: "flex", gap: 10, alignItems: "flex-start", textAlign: "left",
                      background: "transparent", cursor: clickable ? "pointer" : "default",
                    }}
                    onMouseEnter={e => { e.currentTarget.style.background = "var(--surface-2)"; }}
                    onMouseLeave={e => { e.currentTarget.style.background = "transparent"; }}>
                    <span style={{
                      width: 32, height: 32, borderRadius: 9, display: "grid", placeItems: "center",
                      background: tone.soft, color: tone.color, flexShrink: 0,
                    }}>
                      <Icon name={NOTIF_KIND_ICON[item.kind] || "bell"} size={16} color="currentColor"/>
                    </span>
                    <span className="col gap-4" style={{ flex: 1, minWidth: 0 }}>
                      <span className="row spread gap-8" style={{ alignItems: "flex-start" }}>
                        <span style={{ fontSize: 13.2, fontWeight: 800, color: "var(--ink)", lineHeight: 1.35, overflowWrap: "anywhere" }}>{item.title || "通知"}</span>
                        {Number(item.count || 0) > 1 && <span className="num" style={{ fontSize: 11, color: tone.color, fontWeight: 800 }}>x{item.count}</span>}
                      </span>
                      <span style={{ fontSize: 12.2, lineHeight: 1.45, color: "var(--ink-3)", overflowWrap: "anywhere" }}>{item.summary || "需要處理"}</span>
                      <span className="row spread gap-8" style={{ alignItems: "center" }}>
                        {item.created_at && <span className="num muted" style={{ fontSize: 11 }}>{item.created_at}</span>}
                        {hasAgentAction && (
                          <button type="button" className="btn btn-primary btn-sm"
                            onClick={(e) => { e.stopPropagation(); jumpNotification(item); }}
                            style={{ height: 28, padding: "0 10px", borderRadius: 8, fontSize: 12, flexShrink: 0 }}>
                            <Icon name="sparkle" size={13}/>處理
                          </button>
                        )}
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
            {notifCount > notifItems.length && (
              <div style={{ padding: "9px 14px", borderTop: "1px solid var(--line)", color: "var(--ink-3)", fontSize: 12, background: "var(--surface-2)" }}>
                還有 {notifCount - notifItems.length} 條未展開，進入對應模塊可查看完整列表。
              </div>
            )}
          </div>
        )}
      </div>

      <div className="row gap-10 app-user-menu" style={{ paddingLeft: 6 }}>
        <div style={{ width: 40, height: 40, borderRadius: 12, background: "var(--grad)", color: "#fff", display: "grid", placeItems: "center", fontWeight: 700, fontSize: 15 }}>{initial}</div>
        <div className="col" style={{ lineHeight: 1.25 }}>
          <div style={{ fontSize: 13.5, fontWeight: 700 }}>{displayName}</div>
          <div style={{ fontSize: 11, color: "var(--ink-4)" }}>{roleName}</div>
        </div>
        {onChangePassword && (
          <button onClick={onChangePassword} title="修改密碼" style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <Icon name="shield" size={15} color="var(--ink-3)"/>
          </button>
        )}
        <button onClick={onLogout} title="退出登入" style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: "var(--surface-2)", border: "1px solid var(--line)" }}>
          <Icon name="x" size={15} color="var(--ink-3)"/>
        </button>
      </div>
    </header>
  );
};

Object.assign(window, { Sidebar, TopBar, buildNav, buildNavGroups });
