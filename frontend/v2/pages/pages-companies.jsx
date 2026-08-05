/* WAREHOUSE 2.1 · 公司 / 平臺 — ADMIN 權力面(僅平臺所有者),真後端
   政策:本頁屬管理面,允許直接調用管理端點(含 POST);
   一切破壞性動作帶 Swiss 確認防呆,後端 error 原文紅字呈現,全程審計。
   端點逐字照抄 scripts/ai_service.py 與 1.0 platform.jsx / page-companies.jsx:
     GET  /api/platform/tenants                      → {tenants[], scope_full}
     GET  /api/platform/signups?status=pending       → {signups[], pending_count}
     GET  /api/platform/tenants/<slug>/detail        → {tenant, stats, members[]}
     POST /api/platform/signups/<id>/approve  {note} → {ok, tenant_id, slug}
     POST /api/platform/signups/<id>/reject   {note} → {ok}
     POST /api/platform/tenants/<slug>/status/active|suspended
   後端(含經典版平台後台)無「刪除公司」真刪端點 → 本面如實不提供刪除。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "公司 / 平臺": "Companies / Platform",
  "公司生命週期 · 入駐審批 · 跨公司平臺管理 · 僅平臺所有者": "Company lifecycle · signup approval · cross-company platform management · platform owner only",
  "權力面 · 全程審計": "POWER PLANE · FULLY AUDITED",
  "此頁是平臺權力面,動作直調管理端點、即時生效,僅平臺所有者可用。": "This is the platform power plane — actions call admin endpoints directly and take effect immediately. Platform owner only.",
  "當前帳號": "Current account", "最高權限": "highest role level",
  "無平臺所有者標記(is_platform_owner)。": "no platform-owner flag (is_platform_owner).",
  "回總覽": "Back to overview",
  "刷新": "Refresh",
  "問平台概況": "Platform brief",
  "平台上現在有哪些公司最活躍?哪些長期閒置?給我一份經營摘要": "Which companies are most active on the platform and which sit idle? Give me an operations brief",
  "在營公司": "Active companies", "家": "",
  "待審申請": "Pending signups", "條": "",
  "停用公司": "Suspended", "租戶庫總數": "Tenant databases", "個": "",
  "運行中": "running", "無停用": "none suspended", "無待審": "none pending",
  "全平臺": "PLATFORM", "僅授權範圍": "scoped access",
  "後端錯誤:": "Backend error: ",
  "入駐審批": "Signup approval",
  "{n} 條待審批 · 批准即建租戶庫": "{n} pending · approval provisions the tenant DB",
  "暫無待審批的入駐申請": "No pending signup requests",
  "企業提交入駐申請後會第一時間出現在這裡;批准即建立租戶資料庫與初始管理員。": "New signup requests land here immediately; approval creates the tenant database and its initial admin.",
  "申請人": "Applicant", "聯繫方式": "Contact", "申請於": "Applied", "理由": "Reason",
  "批准開通": "Approve & provision", "駁回": "Reject",
  "確認開通": "Confirm provisioning", "確認駁回": "Confirm rejection", "取消": "Cancel",
  "二次確認:即將開通「{name}」(/{slug} · 模板 {tpl}),初始管理員 @{admin}。開通後立即建庫並可登入。": "Second confirmation: about to provision \"{name}\" (/{slug} · template {tpl}), initial admin @{admin}. The tenant DB is created immediately.",
  "駁回申請 #{id}「{name}」:請輸入駁回原因,確認後寫回申請單。": "Rejecting request #{id} \"{name}\": enter the rejection reason; it is written back onto the request.",
  "駁回原因(必填)": "Rejection reason (required)",
  "已開通「{name}」:租戶 /{slug}(#{id})已建立,管理員 @{admin} 可登入。": "Provisioned \"{name}\": tenant /{slug} (#{id}) created; admin @{admin} can sign in.",
  "已駁回申請 #{id}「{name}」。": "Rejected request #{id} \"{name}\".",
  "執行中…": "Working…",
  "公司台賬": "Company ledger",
  "共 {n} 家 · 點行開抽屜與動作區": "{n} companies · click a row for detail & actions",
  "搜索公司名 / 企業代碼": "Search name / slug",
  "全部": "All", "啟用": "Active", "停用": "Suspended",
  "公司": "Company", "企業代碼": "Slug", "行業模板": "Template", "成員": "Members",
  "建立": "Created", "狀態": "Status",
  "還沒有公司": "No companies yet",
  "當前篩選下沒有公司": "No companies under current filter",
  "換個關鍵詞或狀態試試。": "Try a different keyword or status.",
  "第一家公司可由入駐申請批准開通,或直接吩咐秘書開通。": "The first company can be provisioned by approving a signup, or just tell the Secretary.",
  "載入中…": "Loading…",
  "成員({n})": "Members ({n})", "暫無成員": "No members yet",
  "用戶": "Users", "物資數": "Items", "倉庫數": "Warehouses", "流水筆數": "Transactions",
  "建立於": "Created", "資料庫": "Database",
  "管理動作 · 直調端點": "Admin actions · direct endpoints",
  "切入此公司": "Enter this company",
  "切換當前租戶為 /{slug} 並重載系統": "Switch current tenant to /{slug} and reload",
  "公司已停用,啟用後方可切入。": "Company is suspended — reactivate before entering.",
  "停用公司…": "Suspend company…",
  "啟用公司…": "Reactivate company…",
  "停用後該公司全體成員將立即無法登入。輸入企業代碼": "Suspension immediately locks out all members of this company. Type the company slug",
  "逐字匹配解鎖執行:": "exactly to unlock execution:",
  "執行停用": "Execute suspension",
  "二次確認:重新啟用 /{slug},成員將恢復登入。": "Second confirmation: reactivate /{slug}; members regain access.",
  "確認啟用": "Confirm reactivation",
  "已停用:成員即刻無法登入。": "Suspended: members are locked out immediately.",
  "已啟用:成員可正常登入。": "Reactivated: members can sign in again.",
  "問這家公司近況": "Company brief",
  "公司「{name}」(/{slug})最近的使用情況怎麼樣?成員、物資、流水給我個摘要": "How is company \"{name}\" (/{slug}) doing lately? Summarise members, items and transactions",
  "刪除公司:後端無真刪端點(經典版平台後台亦無),本面如實不提供。": "Company deletion: the backend has no hard-delete endpoint (nor does the classic platform console) — honestly not offered here.",
  "ADMIN 權力面:動作直調管理端點、即時生效,全程審計留痕。": "ADMIN power plane: actions call admin endpoints directly, take effect immediately, and are fully audited.",
  "平台超級管理員 · L11": "Platform Owners · L11",
  "現任 {n} 位 · 同級治理 · 全程審計 · 防鎖死": "{n} current · peer governance · fully audited · lockout-proof",
  "Bonfire 高層 = L11 · L11 可治理同級": "Bonfire leadership = L11 · L11 can govern peers",
  "Bonfire 是平臺歸屬公司。其獲授 L11 的高層即平臺擁有者，擁有全部權限；任何現任 L11 都可依治理決議降級或解聘另一位 L11。": "Bonfire is the platform's home company. Its L11 leaders are platform owners with every permission; any current L11 may demote or offboard another L11 under a governance decision.",
  "尚無 L11 名冊數據": "No L11 roster data",
  "L11 名冊由 global_users.is_platform_owner 定義;若後端未返回數據,請刷新或檢查權限。": "The L11 roster is defined by global_users.is_platform_owner; if the backend returned nothing, refresh or check permissions.",
  "降級（收回 L11）…": "Demote (revoke L11)…",
  "降級只收回平台擁有者身份；帳號與 Bonfire 在冊關係保留，可再調整一般崗位。輸入其用戶名": "Demotion only revokes platform-owner status; the account and Bonfire membership remain, ready for reassignment to a regular position. Type the username",
  "治理理由（必填）": "Governance reason (required)",
  "輸入其用戶名": "Type the username",
  "執行降級": "Execute demotion",
  "已將 @{u} 降級並收回 L11。": "Demoted @{u} and revoked L11.",
  "解聘／停用平台身份…": "Offboard / disable platform identity…",
  "解聘會收回 L11、停用 Bonfire 內部帳號並移出 Bonfire 在冊關係，歷史審計記錄保留；此人在其他公司的普通成員身份不受影響。輸入其用戶名": "Offboarding revokes L11, disables the internal Bonfire account, and removes the Bonfire membership while preserving audit history. Ordinary memberships in other companies are unaffected. Type the username",
  "執行解聘": "Execute offboarding",
  "繼續未完成的解聘…": "Continue incomplete offboarding…",
  "上次解聘在跨庫同步時中斷，平台權力已安全凍結。重新確認後可沿用同一治理記錄完成 Bonfire 停用。": "The previous offboarding was interrupted during cross-database synchronization and platform powers are safely frozen. Reconfirm to finish the Bonfire deactivation under the same governance record.",
  "已解聘 @{u} 並停用其平台身份。": "Offboarded @{u} and disabled the platform identity.",
  "至少保留一位有效 L11；若操作會造成無人治理，系統將拒絕。": "At least one effective L11 must remain; the system rejects any action that would leave the platform without governance.",
  "已授予 @{u} L11 平台超級管理員。": "Granted platform owner (L11) to @{u}.",
  "授予、復職與身份治理": "Grant, restore & identity governance",
  "搜索全局用戶名 / 顯示名": "Search global username / display name",
  "搜索中…": "Searching…",
  "沒有匹配的全局用戶": "No matching global users",
  "候選僅列前 20 條,請換更精確的關鍵詞。": "Only the first 20 candidates are listed — try a more specific keyword.",
  "已是 L11": "Already L11",
  "非 Bonfire 成員 · 不可授": "Not a Bonfire member · ineligible",
  "非 Bonfire 成員 · 權力已凍結": "Not a Bonfire member · powers frozen",
  "已移出 Bonfire": "Removed from Bonfire",
  "平台身份已停用": "Platform identity disabled",
  "Bonfire 內部帳號已停用": "Internal Bonfire account disabled",
  "身份治理同步中": "Identity governance syncing",
  "復職…": "Restore…",
  "啟用／復職…": "Activate / restore…",
  "復職只恢復平台帳號與 Bonfire 在冊關係，不會新授予 L11；若只是修復現任 L11 的 Bonfire 內部帳號，則保留原有 L11。輸入其用戶名": "Restoration only reactivates the platform account and Bonfire membership; it does not newly grant L11. If this only repairs a current L11's internal Bonfire account, the existing L11 role is preserved. Type the username",
  "執行復職": "Execute restoration",
  "已恢復 @{u} 的平台身份與 Bonfire 在冊關係；未授予 L11。": "Restored @{u}'s platform identity and Bonfire membership; L11 was not granted.",
  "已啟用 @{u} 的 Bonfire 內部帳號，並保留其原有 L11。": "Reactivated @{u}'s internal Bonfire account and preserved the existing L11 role.",
  "復職不自動授予 L11": "Restoration does not grant L11 automatically",
  "平臺歸屬 Bonfire:僅 Bonfire 在冊成員可獲授 L11;非成員即使有標記,權力亦被後端凍結。": "The platform belongs to Bonfire: only enrolled Bonfire members can be granted L11; non-members are frozen by the backend even if flagged.",
  "授予…": "Grant…",
  "二次確認:授予後該賬號立即獲得全部 ADMIN 權力面並可跨公司管理,授予需慎重。輸入其用戶名": "Second confirmation: once granted, this account immediately gains the entire ADMIN power plane and cross-company control — grant with care. Type the username",
  "執行授予": "Execute grant",
  "輸入關鍵詞搜索全局用戶；啟用中的 Bonfire 成員可授予 L11，已停用或已移出的身份可先復職。所有動作均須逐字確認。": "Search global users by keyword. Active Bonfire members can be granted L11; disabled or removed identities can be restored first. Every action requires exact username confirmation.",
  "L11 = 平台超級管理員(global_users.is_platform_owner):可見全部 ADMIN 權力面並跨公司管理；L11 可治理同級，降級與解聘設防鎖死，全庫至少保留一位。": "L11 = platform owner (global_users.is_platform_owner): sees the entire ADMIN power plane and manages across companies. L11 can govern peers, while demotion and offboarding are lockout-proof and always preserve at least one owner.",
});
const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

const day = (s) => (s ? String(s).slice(0, 10) : "—");
const ST_TENANT = { active: ["ok", "啟用"], suspended: ["bad", "停用"] };
const TenantTag = ({ st }) => {
  const [tone, label] = ST_TENANT[st] || ["plain", st || "—"];
  return <T tone={tone} dot>{t(label)}</T>;
};

/* ── ADMIN 徽記(頁頂常駐)── */
const AdminMark = () => (
  <div className="row g10" style={{ paddingTop: 14 }}>
    <span className="label" style={{ color: "var(--red)" }}>ADMIN — {t("權力面 · 全程審計")}</span>
  </div>
);

/* ── 後端 error 原文紅字 ── */
const ErrLine = ({ err, style }) => !err ? null : (
  <div className="mono" style={{ color: "var(--red)", fontSize: 11.5, lineHeight: 1.6, wordBreak: "break-word", ...style }}>
    ⚠ {t("後端錯誤:")}{err}
  </div>
);

/* ── 非 owner:Swiss 拒絕面(不裸露任何功能)── */
const Denied = () => {
  const u = window.W2_USER || {};
  const lvl = Math.max(0, ...((u.roles || []).map(r => Number(r.level) || 0)));
  return (<>
    <AdminMark/>
    <Folio no="18" en="COMPANIES / PLATFORM" title={t("公司 / 平臺")}
      sub={t("公司生命週期 · 入駐審批 · 跨公司平臺管理 · 僅平臺所有者")}/>
    <div className="rise" style={{ borderTop: "2px solid var(--red)", padding: "42px 0 64px" }}>
      <div className="mono" style={{ color: "var(--red)", fontSize: 36, fontWeight: 800, letterSpacing: ".05em" }}>ACCESS DENIED</div>
      <div style={{ marginTop: 16, fontSize: 13.5, lineHeight: 1.85, maxWidth: 620 }}>
        {t("此頁是平臺權力面,動作直調管理端點、即時生效,僅平臺所有者可用。")}<br/>
        <span className="muted">
          {t("當前帳號")} {u.display_name || u.username || "—"} · {t("最高權限")} L{lvl} · {t("無平臺所有者標記(is_platform_owner)。")}
        </span>
      </div>
      <div className="row g10" style={{ marginTop: 22 }}>
        <B icon="arrow" onClick={() => { location.hash = "#/dashboard"; }}>{t("回總覽")}</B>
      </div>
    </div>
  </>);
};

/* ── 公司詳情抽屜:/detail + 動作區(切入 / 停用 / 啟用)── */
const CoDrawer = ({ co, refresh, onClose, onChanged }) => {
  const slug = co.slug || "";
  const [d, setD] = _s(null);
  const [act, setAct] = _s(null);      // null | "suspend" | "activate"
  const [gate, setGate] = _s("");      // 停用:逐字輸入 slug 解鎖
  const [busy, setBusy] = _s(false);
  const [err, setErr] = _s("");
  const [ok, setOk] = _s("");

  _e(() => {
    setD(null);
    W2.json("/api/platform/tenants/" + encodeURIComponent(slug) + "/detail")
      .then(x => setD(x && typeof x === "object" ? x : {}))
      .catch(() => setD({}));
  }, [slug, refresh]);
  _e(() => { setAct(null); setGate(""); setErr(""); setOk(""); }, [slug]);

  const ten = (d && d.tenant) || {};
  const stx = (d && d.stats) || {};
  const members = d && Array.isArray(d.members) ? d.members : [];
  const name = ten.name || co.name || "—";
  const status = ten.status || co.status || "active";
  const activeCo = status === "active";
  const v = (x) => (x == null ? "—" : x);

  /* POST /api/platform/tenants/<slug>/status/active|suspended —— 動作由路徑固定 */
  const doStatus = (next) => {
    if (busy) return;
    const action = next === "suspended" ? "suspended" : "active";
    setBusy(true); setErr(""); setOk("");
    W2.post("/api/platform/tenants/" + encodeURIComponent(slug) + "/status/" + action, {})
      .then(() => {
        setOk(next === "suspended" ? t("已停用:成員即刻無法登入。") : t("已啟用:成員可正常登入。"));
        setAct(null); setGate("");
        onChanged();                       // 結果行內呈現後 reload 列表(父級 tick → 列表+本抽屜同步刷新)
      })
      .catch(e => setErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };
  const switchIn = () => { W2.setTenant(slug); location.hash = "#/dashboard"; location.reload(); };

  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            <T tone="redinv">ADMIN</T>
            <TenantTag st={status}/>
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.25 }}>{name}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>
          /{slug}{(ten.template_name || co.template_name) ? " · " + (ten.template_name || co.template_name) : ""}
        </div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        {d === null && <div className="muted" style={{ fontSize: 12.5, marginBottom: 14 }}>{t("載入中…")}</div>}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 16 }}>
          {[[t("成員"), v(stx.members)], [t("用戶"), v(stx.users)], [t("物資數"), v(stx.items)],
            [t("倉庫數"), v(stx.warehouses)], [t("流水筆數"), v(stx.transactions)], [t("建立於"), day(ten.created_at || co.created_at)]].map(([k, val]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 14, fontWeight: 650 }}>{val}</span>
            </div>
          ))}
        </div>
        {ten.db_path && (
          <div className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8, marginBottom: 16 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("資料庫")}</LB>
            <span className="mono" style={{ fontSize: 11, wordBreak: "break-all" }}>{ten.db_path}</span>
          </div>
        )}

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("成員({n})", { n: members.length })}</LB>
        <div style={{ borderTop: "1px solid var(--hair)", marginBottom: 18 }}>
          {!members.length && <div className="muted" style={{ fontSize: 12, padding: "10px 0" }}>{t("暫無成員")}</div>}
          {members.map((m, i) => (
            <div key={m.global_user_id || i} className="row g10" style={{ padding: "8px 0", borderBottom: "1px solid var(--hair-soft)" }}>
              <div className="col g2" style={{ flex: 1, minWidth: 0 }}>
                <span style={{ fontWeight: 650, fontSize: 12.5 }}>{m.display_name || m.username || "—"}</span>
                <span className="num muted" style={{ fontSize: 10.5 }}>@{m.username || "—"}{m.role ? " · " + m.role : ""}</span>
              </div>
              {m.status === "active" ? <T tone="ok" dot>{t("啟用")}</T> : <T tone="plain">{m.status || "—"}</T>}
            </div>
          ))}
        </div>

        <LB red style={{ fontSize: 8.5, marginBottom: 8 }}>{t("管理動作 · 直調端點")}</LB>
        <div className="col g8">
          {ok && <T tone="ok" dot>{ok}</T>}
          <ErrLine err={err}/>

          {/* 切入此公司:W2.setTenant + 重載 */}
          <button className="btn" disabled={!activeCo} style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }}
            title={t("切換當前租戶為 /{slug} 並重載系統", { slug })} onClick={switchIn}>
            <I name="swap" size={14}/>{t("切入此公司")}
            <span className="num muted" style={{ fontSize: 10.5 }}>/{slug}</span>
          </button>
          {!activeCo && <div className="muted" style={{ fontSize: 10.5 }}>{t("公司已停用,啟用後方可切入。")}</div>}

          {/* 停用(重量級:輸入企業代碼逐字匹配解鎖)/ 啟用(輕量:二次點擊)*/}
          {activeCo ? (
            act !== "suspend" ? (
              <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5, color: "var(--red)", borderColor: "var(--red)" }}
                onClick={() => { setAct("suspend"); setGate(""); setErr(""); setOk(""); }}>
                <I name="x" size={14}/>{t("停用公司…")}
              </button>
            ) : (
              <div className="col g8" style={{ border: "1px solid var(--red)", padding: 12 }}>
                <div style={{ fontSize: 12, lineHeight: 1.65 }}>
                  {t("停用後該公司全體成員將立即無法登入。輸入企業代碼")} <b className="mono" style={{ color: "var(--red)" }}>{slug}</b> {t("逐字匹配解鎖執行:")}
                </div>
                <input className="field" value={gate} onChange={e => setGate(e.target.value)} placeholder={slug}
                  autoFocus spellCheck={false} autoComplete="off"/>
                <div className="row g8">
                  <B kind="red" size="sm" disabled={gate !== slug || busy} onClick={() => doStatus("suspended")}>
                    {busy ? t("執行中…") : t("執行停用")}
                  </B>
                  <B size="sm" onClick={() => { setAct(null); setGate(""); }}>{t("取消")}</B>
                </div>
              </div>
            )
          ) : (
            act !== "activate" ? (
              <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }}
                onClick={() => { setAct("activate"); setErr(""); setOk(""); }}>
                <I name="check" size={14}/>{t("啟用公司…")}
              </button>
            ) : (
              <div className="col g8" style={{ border: "1px solid var(--ink)", padding: 12 }}>
                <div style={{ fontSize: 12, lineHeight: 1.65 }}>{t("二次確認:重新啟用 /{slug},成員將恢復登入。", { slug })}</div>
                <div className="row g8">
                  <B kind="primary" size="sm" disabled={busy} onClick={() => doStatus("active")}>
                    {busy ? t("執行中…") : t("確認啟用")}
                  </B>
                  <B size="sm" onClick={() => setAct(null)}>{t("取消")}</B>
                </div>
              </div>
            )
          )}

          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }}
            onClick={() => ask(t("公司「{name}」(/{slug})最近的使用情況怎麼樣?成員、物資、流水給我個摘要", { name, slug }))}>
            <I name="sparkle" size={14}/>{t("問這家公司近況")}
          </button>
        </div>

        <div className="muted" style={{ fontSize: 10.5, marginTop: 14, lineHeight: 1.7 }}>
          {t("刪除公司:後端無真刪端點(經典版平台後台亦無),本面如實不提供。")}<br/>
          {t("ADMIN 權力面:動作直調管理端點、即時生效,全程審計留痕。")}
        </div>
      </div>
    </div>
  );
};

/* ── Band D · 平台超級管理員 L11:名冊 + 同級治理 ──
   GET  /api/platform/owners        → {owners:[{id,username,display_name,active,is_platform_owner}]}
   GET  /api/platform/owners?q=…    → 另返 candidates[](限 20,含 is_platform_owner 標記)
   POST /api/platform/owners/grant   {username,reason,confirm:username}
   POST /api/platform/owners/revoke  {username,reason,confirm:username}
   POST /api/platform/owners/offboard {username,reason,confirm:username}
   POST /api/platform/owners/restore  {username,reason,confirm:username}
   防鎖死:後端拒絕降級/解聘最後一位 owner(error 原文紅字呈現)。 */
const OwnerBand = ({ refresh }) => {
  const [data, setData] = _s(null);          // null=載入中
  const [err, setErr] = _s("");
  const [tick, setTick] = _s(0);
  const [notice, setNotice] = _s("");
  const [busy, setBusy] = _s(false);
  /* 降級:rev=目標用戶名,gate=逐字輸入解鎖,reason=治理依據 */
  const [rev, setRev] = _s(null);
  const [gate, setGate] = _s("");
  const [revReason, setRevReason] = _s("");
  const [revErr, setRevErr] = _s("");
  /* 解聘:單一平台流程同時收回 L11、停用身份、移出 Bonfire */
  const [off, setOff] = _s(null);
  const [offGate, setOffGate] = _s("");
  const [offReason, setOffReason] = _s("");
  const [offErr, setOffErr] = _s("");
  const [resumeOffPick, setResumeOffPick] = _s(null);
  /* 授予:q 防抖搜索 → 候選 → 選中逐字確認 */
  const [q, setQ] = _s("");
  const [cands, setCands] = _s(null);        // null=未搜索
  const [searching, setSearching] = _s(false);
  const [pick, setPick] = _s(null);
  const [confirmTx, setConfirmTx] = _s("");
  const [grantReason, setGrantReason] = _s("");
  const [grantErr, setGrantErr] = _s("");
  /* 復職:只恢復身份與 Bonfire 在冊關係,不自動授 L11 */
  const [restorePick, setRestorePick] = _s(null);
  const [restoreTx, setRestoreTx] = _s("");
  const [restoreReason, setRestoreReason] = _s("");
  const [restoreErr, setRestoreErr] = _s("");

  _e(() => {
    setErr("");
    W2.json("/api/platform/owners")
      .then(d => setData(d && typeof d === "object" ? d : {}))
      .catch(e => { setData({}); setErr(e.message || String(e)); });
  }, [tick, refresh]);

  /* ?q= 防抖(350ms) */
  _e(() => {
    const k = q.trim();
    if (!k) { setCands(null); setSearching(false); return; }
    setSearching(true);
    const h = setTimeout(() => {
      W2.json("/api/platform/owners?q=" + encodeURIComponent(k))
        .then(d => setCands(d && Array.isArray(d.candidates) ? d.candidates : []))
        .catch(() => setCands([]))
        .finally(() => setSearching(false));
    }, 350);
    return () => clearTimeout(h);
  }, [q, tick, refresh]);

  const owners = data && Array.isArray(data.owners) ? data.owners : [];

  const doRevoke = (u) => {
    if (busy) return;
    setBusy(true); setRevErr(""); setNotice("");
    W2.post("/api/platform/owners/revoke", { username: u, reason: revReason.trim(), confirm: u })
      .then(() => { setNotice(t("已將 @{u} 降級並收回 L11。", { u })); setRev(null); setGate(""); setRevReason(""); setTick(v => v + 1); })
      .catch(e => setRevErr(e.message || String(e)))     // 防鎖死 400 原文紅字
      .finally(() => setBusy(false));
  };
  const doOffboard = (u) => {
    if (busy) return;
    setBusy(true); setOffErr(""); setNotice("");
    W2.post("/api/platform/owners/offboard", { username: u, reason: offReason.trim(), confirm: u })
      .then(() => { setNotice(t("已解聘 @{u} 並停用其平台身份。", { u })); setOff(null); setResumeOffPick(null); setOffGate(""); setOffReason(""); setTick(v => v + 1); })
      .catch(e => setOffErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };
  const doGrant = (u) => {
    if (busy) return;
    setBusy(true); setGrantErr(""); setNotice("");
    W2.post("/api/platform/owners/grant", { username: u, reason: grantReason.trim(), confirm: u })
      .then(() => { setNotice(t("已授予 @{u} L11 平台超級管理員。", { u })); setPick(null); setConfirmTx(""); setGrantReason(""); setQ(""); setCands(null); setTick(v => v + 1); })
      .catch(e => setGrantErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };
  const doRestore = (u) => {
    if (busy) return;
    setBusy(true); setRestoreErr(""); setNotice("");
    W2.post("/api/platform/owners/restore", { username: u, reason: restoreReason.trim(), confirm: u })
      .then(result => {
        setNotice(result && result.is_platform_owner
          ? t("已啟用 @{u} 的 Bonfire 內部帳號，並保留其原有 L11。", { u })
          : t("已恢復 @{u} 的平台身份與 Bonfire 在冊關係；未授予 L11。", { u }));
        setRestorePick(null); setRestoreTx(""); setRestoreReason(""); setQ(""); setCands(null); setTick(v => v + 1);
      })
      .catch(e => setRestoreErr(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  return (
    <Band no="C" title={t("平台超級管理員 · L11")} delay={.2}
      sub={data === null ? null : t("現任 {n} 位 · 同級治理 · 全程審計 · 防鎖死", { n: owners.length })}>
      <div style={{ borderTop: "3px solid var(--red)", borderBottom: "1px solid var(--hair)", padding: "13px 0 14px", marginBottom: 14 }}>
        <div className="row g8 wrap">
          <T tone="redinv">{t("Bonfire 高層 = L11 · L11 可治理同級")}</T>
          <T tone="plain">GOVERNANCE</T>
        </div>
        <div style={{ fontSize: 12, lineHeight: 1.75, marginTop: 8, maxWidth: 820 }}>
          {t("Bonfire 是平臺歸屬公司。其獲授 L11 的高層即平臺擁有者，擁有全部權限；任何現任 L11 都可依治理決議降級或解聘另一位 L11。")}
        </div>
        <div className="mono" style={{ color: "var(--red)", fontSize: 10.5, lineHeight: 1.6, marginTop: 6 }}>
          {t("至少保留一位有效 L11；若操作會造成無人治理，系統將拒絕。")}
        </div>
      </div>
      {notice && (
        <div className="row g10 wrap" style={{ padding: "10px 12px", border: "1px solid var(--hair)", background: "var(--paper-2)", marginBottom: 12 }}>
          <T tone="ok" dot>{notice}</T>
        </div>
      )}
      <ErrLine err={err} style={{ paddingBottom: 8 }}/>

      {/* 現任名冊 */}
      {data === null
        ? <div className="muted" style={{ fontSize: 12.5, padding: "16px 0" }}>{t("載入中…")}</div>
        : !owners.length
          ? <EM icon="shield" title={t("尚無 L11 名冊數據")}
              sub={t("L11 名冊由 global_users.is_platform_owner 定義;若後端未返回數據,請刷新或檢查權限。")}/>
          : <div style={{ borderTop: "2px solid var(--rule)" }}>
              {owners.map((o, i) => (
                <div key={o.id != null ? o.id : (o.username || i)}>
                  <div className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <div className="col g2" style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontWeight: 700, fontSize: 13.5 }}>{o.display_name || o.username || "—"}</span>
                      <span className="num muted" style={{ fontSize: 11 }}>@{o.username || "—"}</span>
                    </div>
                    <T tone="redinv">L11</T>
                    {(o.bonfire_member === 0 || o.bonfire_member === false) && <T tone="bad" dot>{t("非 Bonfire 成員 · 權力已凍結")}</T>}
                    {(o.bonfire_user_active === false || o.bonfire_user_active === 0) && <T tone="bad" dot>{t("Bonfire 內部帳號已停用")}</T>}
                    {o.active ? <T tone="ok" dot>{t("啟用")}</T> : <T tone="bad" dot>{t("停用")}</T>}
                    <div className="row g4 wrap" style={{ justifyContent: "flex-end" }}>
                      {(!!o.bonfire_status && (o.active === false || o.active === 0
                        || String(o.bonfire_status).toLowerCase() !== "active"
                        || o.bonfire_user_active === false || o.bonfire_user_active === 0)) &&
                        <B size="sm" disabled={busy} onClick={() => {
                          setRestorePick(o); setRestoreTx(""); setRestoreReason(""); setRestoreErr(""); setNotice("");
                        }}>{t("啟用／復職…")}</B>}
                      <B size="sm" disabled={busy}
                        onClick={() => {
                          setRev(rev === o.username ? null : o.username); setGate(""); setRevReason(""); setRevErr("");
                          setOff(null); setResumeOffPick(null); setOffGate(""); setOffReason(""); setOffErr(""); setNotice("");
                        }}>
                        {t("降級（收回 L11）…")}
                      </B>
                      <B size="sm" kind="red" disabled={busy}
                        onClick={() => {
                          setOff(off === o.username ? null : o.username); setOffGate(""); setOffReason(""); setOffErr("");
                          setResumeOffPick(null); setRev(null); setGate(""); setRevReason(""); setRevErr(""); setNotice("");
                        }}>
                        {t("解聘／停用平台身份…")}
                      </B>
                    </div>
                  </div>
                  {rev === o.username && (
                    <div className="col g8" style={{ borderLeft: "2px solid var(--red)", background: "var(--paper-2)", padding: "12px 14px", margin: "0 0 6px 26px" }}>
                      <div style={{ fontSize: 12, lineHeight: 1.65 }}>
                        {t("降級只收回平台擁有者身份；帳號與 Bonfire 在冊關係保留，可再調整一般崗位。輸入其用戶名")}{" "}
                        <b className="mono" style={{ color: "var(--red)" }}>{o.username}</b> {t("逐字匹配解鎖執行:")}
                      </div>
                      <textarea className="field" rows="2" value={revReason} onChange={e => setRevReason(e.target.value)}
                        placeholder={t("治理理由（必填）")} maxLength={500}/>
                      <input className="field" value={gate} onChange={e => setGate(e.target.value)} placeholder={o.username}
                        autoFocus spellCheck={false} autoComplete="off"/>
                      <div className="mono" style={{ color: "var(--red)", fontSize: 10.5 }}>{t("至少保留一位有效 L11；若操作會造成無人治理，系統將拒絕。")}</div>
                      <div className="row g8">
                        <B size="sm" kind="red" disabled={gate !== o.username || !revReason.trim() || busy} onClick={() => doRevoke(o.username)}>
                          {busy ? t("執行中…") : t("執行降級")}
                        </B>
                        <B size="sm" onClick={() => { setRev(null); setGate(""); setRevReason(""); }}>{t("取消")}</B>
                      </div>
                      <ErrLine err={revErr}/>
                    </div>
                  )}
                  {off === o.username && (
                    <div className="col g8" style={{ borderLeft: "4px solid var(--red)", background: "var(--paper-2)", padding: "12px 14px", margin: "0 0 6px 26px" }}>
                      <div style={{ fontSize: 12, lineHeight: 1.65 }}>
                        {t("解聘會收回 L11、停用 Bonfire 內部帳號並移出 Bonfire 在冊關係，歷史審計記錄保留；此人在其他公司的普通成員身份不受影響。輸入其用戶名")}{" "}
                        <b className="mono" style={{ color: "var(--red)" }}>{o.username}</b> {t("逐字匹配解鎖執行:")}
                      </div>
                      <textarea className="field" rows="2" value={offReason} onChange={e => setOffReason(e.target.value)}
                        placeholder={t("治理理由（必填）")} maxLength={500}/>
                      <input className="field" value={offGate} onChange={e => setOffGate(e.target.value)} placeholder={o.username}
                        autoFocus spellCheck={false} autoComplete="off"/>
                      <div className="mono" style={{ color: "var(--red)", fontSize: 10.5 }}>{t("至少保留一位有效 L11；若操作會造成無人治理，系統將拒絕。")}</div>
                      <div className="row g8">
                        <B size="sm" kind="red" disabled={offGate !== o.username || !offReason.trim() || busy} onClick={() => doOffboard(o.username)}>
                          {busy ? t("執行中…") : t("執行解聘")}
                        </B>
                        <B size="sm" onClick={() => { setOff(null); setOffGate(""); setOffReason(""); }}>{t("取消")}</B>
                      </div>
                      <ErrLine err={offErr}/>
                    </div>
                  )}
                </div>
              ))}
            </div>}

      {/* 授予 / 復職:搜索 → 候選 → 逐字確認 */}
      <div style={{ marginTop: 20 }}>
        <LB red style={{ fontSize: 8.5, marginBottom: 8 }}>{t("授予、復職與身份治理")}</LB>
        <div style={{ position: "relative", maxWidth: 340 }}>
          <I name="search" size={13} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
          <input className="field" style={{ paddingLeft: 22, height: 32, fontSize: 12.5 }} value={q}
            onChange={e => {
              setQ(e.target.value); setPick(null); setConfirmTx(""); setGrantReason(""); setGrantErr("");
              setResumeOffPick(null); setOffGate(""); setOffReason(""); setOffErr("");
              setRestorePick(null); setRestoreTx(""); setRestoreReason(""); setRestoreErr("");
            }}
            placeholder={t("搜索全局用戶名 / 顯示名")} spellCheck={false} autoComplete="off"/>
        </div>
        {!q.trim() && (
          <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>{t("輸入關鍵詞搜索全局用戶；啟用中的 Bonfire 成員可授予 L11，已停用或已移出的身份可先復職。所有動作均須逐字確認。")}</div>
        )}
        {searching && <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>{t("搜索中…")}</div>}
        {!searching && cands !== null && !cands.length && (
          <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
            {t("沒有匹配的全局用戶")} · {t("候選僅列前 20 條,請換更精確的關鍵詞。")}
          </div>
        )}
        {!searching && cands && cands.length > 0 && (
          <div style={{ borderTop: "1px solid var(--hair)", marginTop: 10, maxWidth: 560 }}>
            {cands.map((c, i) => {
              const bonfireStatus = String(c.bonfire_status || c.membership_status || "").toLowerCase();
              const hasBonfireMembership = !!bonfireStatus || c.bonfire_member === true || c.bonfire_member === 1;
              const inactive = c.active === false || c.active === 0
                || c.bonfire_user_active === false || c.bonfire_user_active === 0;
              const removed = !!bonfireStatus && bonfireStatus !== "active";
              const neverMember = !hasBonfireMembership;
              const transitionStatus = String(c.identity_transition_status || "").toLowerCase();
              const transitionStale = c.identity_transition_stale === true || c.identity_transition_stale === 1;
              const activeTransition = !transitionStale && (transitionStatus === "pending" || transitionStatus === "tenant_applied");
              const failedOffboard = bonfireStatus === "transitioning"
                && c.identity_transition_action === "offboard"
                && (transitionStatus === "failed" || transitionStale);
              const needsRestore = !activeTransition && !failedOffboard && !neverMember && (inactive || removed);
              return (
                <div key={c.id != null ? c.id : (c.username || i)} className="row g10" style={{ padding: "8px 0", borderBottom: "1px solid var(--hair-soft)" }}>
                  <div className="col g2" style={{ flex: 1, minWidth: 0 }}>
                    <span style={{ fontWeight: 650, fontSize: 12.5 }}>{c.display_name || c.username || "—"}</span>
                    <span className="num muted" style={{ fontSize: 10.5 }}>@{c.username || "—"}</span>
                  </div>
                  {inactive && <T tone="bad" dot>{t("平台身份已停用")}</T>}
                  {removed && <T tone="plain">{t("已移出 Bonfire")}</T>}
                  {neverMember && <T tone="plain">{t("非 Bonfire 成員 · 不可授")}</T>}
                  {activeTransition
                    ? <T tone="plain" dot>{t("身份治理同步中")}</T>
                    : failedOffboard
                    ? <B size="sm" kind="red" disabled={busy} onClick={() => {
                        setResumeOffPick(c); setOffGate(""); setOffReason(""); setOffErr("");
                        setRestorePick(null); setRestoreTx(""); setRestoreReason(""); setRestoreErr("");
                        setPick(null); setConfirmTx(""); setGrantReason(""); setGrantErr(""); setNotice("");
                      }}>{t("繼續未完成的解聘…")}</B>
                    : needsRestore
                    ? <B size="sm" disabled={busy} onClick={() => {
                        setRestorePick(c); setRestoreTx(""); setRestoreReason(""); setRestoreErr("");
                        setResumeOffPick(null); setPick(null); setConfirmTx(""); setGrantReason(""); setGrantErr(""); setNotice("");
                      }}>{t("啟用／復職…")}</B>
                    : neverMember
                    ? null
                    : c.is_platform_owner
                    ? <T tone="redinv">{t("已是 L11")}</T>
                    : <B size="sm" disabled={busy}
                        onClick={() => {
                          setPick(c); setConfirmTx(""); setGrantReason(""); setGrantErr("");
                          setRestorePick(null); setRestoreTx(""); setRestoreReason(""); setRestoreErr(""); setNotice("");
                        }}>{t("授予…")}</B>}
                </div>
              );
            })}
          </div>
        )}
        {pick && (
          <div className="col g8" style={{ border: "1px solid var(--red)", padding: 12, marginTop: 12, maxWidth: 560 }}>
            <div style={{ fontSize: 12, lineHeight: 1.65 }}>
              {t("二次確認:授予後該賬號立即獲得全部 ADMIN 權力面並可跨公司管理,授予需慎重。輸入其用戶名")}{" "}
              <b className="mono" style={{ color: "var(--red)" }}>{pick.username}</b> {t("逐字匹配解鎖執行:")}
            </div>
            <textarea className="field" rows="2" value={grantReason} onChange={e => setGrantReason(e.target.value)}
              placeholder={t("治理理由（必填）")} maxLength={500}/>
            <input className="field" value={confirmTx} onChange={e => setConfirmTx(e.target.value)} placeholder={pick.username}
              autoFocus spellCheck={false} autoComplete="off"/>
            <div className="row g8">
              <B size="sm" kind="primary" disabled={confirmTx !== pick.username || !grantReason.trim() || busy} onClick={() => doGrant(pick.username)}>
                {busy ? t("執行中…") : t("執行授予")}
              </B>
              <B size="sm" onClick={() => { setPick(null); setConfirmTx(""); setGrantReason(""); }}>{t("取消")}</B>
            </div>
            <ErrLine err={grantErr}/>
          </div>
        )}
        {resumeOffPick && (
          <div className="col g8" style={{ border: "2px solid var(--red)", padding: 12, marginTop: 12, maxWidth: 560 }}>
            <div className="row g8 wrap"><T tone="bad">{t("繼續未完成的解聘…")}</T></div>
            <div style={{ fontSize: 12, lineHeight: 1.65 }}>
              {t("上次解聘在跨庫同步時中斷，平台權力已安全凍結。重新確認後可沿用同一治理記錄完成 Bonfire 停用。")} {t("輸入其用戶名")} {" "}
              <b className="mono" style={{ color: "var(--red)" }}>{resumeOffPick.username}</b> {t("逐字匹配解鎖執行:")}
            </div>
            <textarea className="field" rows="2" value={offReason} onChange={e => setOffReason(e.target.value)}
              placeholder={t("治理理由（必填）")} maxLength={500}/>
            <input className="field" value={offGate} onChange={e => setOffGate(e.target.value)} placeholder={resumeOffPick.username}
              autoFocus spellCheck={false} autoComplete="off"/>
            <div className="row g8">
              <B size="sm" kind="red" disabled={offGate !== resumeOffPick.username || !offReason.trim() || busy}
                onClick={() => doOffboard(resumeOffPick.username)}>
                {busy ? t("執行中…") : t("執行解聘")}
              </B>
              <B size="sm" onClick={() => { setResumeOffPick(null); setOffGate(""); setOffReason(""); setOffErr(""); }}>{t("取消")}</B>
            </div>
            <ErrLine err={offErr}/>
          </div>
        )}
        {restorePick && (
          <div className="col g8" style={{ border: "2px solid var(--rule)", padding: 12, marginTop: 12, maxWidth: 560 }}>
            <div className="row g8 wrap"><T tone="inv">{t("復職不自動授予 L11")}</T></div>
            <div style={{ fontSize: 12, lineHeight: 1.65 }}>
              {t("復職只恢復平台帳號與 Bonfire 在冊關係，不會新授予 L11；若只是修復現任 L11 的 Bonfire 內部帳號，則保留原有 L11。輸入其用戶名")}{" "}
              <b className="mono" style={{ color: "var(--red)" }}>{restorePick.username}</b> {t("逐字匹配解鎖執行:")}
            </div>
            <textarea className="field" rows="2" value={restoreReason} onChange={e => setRestoreReason(e.target.value)}
              placeholder={t("治理理由（必填）")} maxLength={500}/>
            <input className="field" value={restoreTx} onChange={e => setRestoreTx(e.target.value)} placeholder={restorePick.username}
              autoFocus spellCheck={false} autoComplete="off"/>
            <div className="row g8">
              <B size="sm" kind="primary" disabled={restoreTx !== restorePick.username || !restoreReason.trim() || busy}
                onClick={() => doRestore(restorePick.username)}>
                {busy ? t("執行中…") : t("執行復職")}
              </B>
              <B size="sm" onClick={() => { setRestorePick(null); setRestoreTx(""); setRestoreReason(""); }}>{t("取消")}</B>
            </div>
            <ErrLine err={restoreErr}/>
          </div>
        )}
      </div>

      <div className="muted" style={{ fontSize: 10.5, marginTop: 16, lineHeight: 1.7 }}>
        {t("L11 = 平台超級管理員(global_users.is_platform_owner):可見全部 ADMIN 權力面並跨公司管理；L11 可治理同級，降級與解聘設防鎖死，全庫至少保留一位。")}
        <br/>{t("平臺歸屬 Bonfire:僅 Bonfire 在冊成員可獲授 L11;非成員即使有標記,權力亦被後端凍結。")}
        <br/>{t("復職不自動授予 L11")}
      </div>
    </Band>
  );
};

/* ── 主面(僅 owner 到達)── */
const Main = () => {
  const [tenants, setTenants] = _s(null);      // null = 載入中
  const [scopeFull, setScopeFull] = _s(true);
  const [signups, setSignups] = _s(null);
  const [pending, setPending] = _s(0);
  const [loadErr, setLoadErr] = _s("");
  const [sigErr, setSigErr] = _s("");
  const [tick, setTick] = _s(0);
  /* 台賬 */
  const [q, setQ] = _s("");
  const [st, setSt] = _s("all");
  const [sel, setSel] = _s(null);              // 選中公司 slug
  /* 審批行內流程 */
  const [flow, setFlow] = _s(null);            // {id, mode:"approve"|"reject"}
  const [reason, setReason] = _s("");
  const [busyId, setBusyId] = _s(null);
  const [rowErr, setRowErr] = _s({});          // signup id → 後端 error 原文
  const [notice, setNotice] = _s(null);        // {tone, text} 動作結果(reload 後仍可見)

  _e(() => {
    setLoadErr(""); setSigErr("");
    W2.json("/api/platform/tenants")
      .then(d => { setTenants(Array.isArray(d.tenants) ? d.tenants : []); setScopeFull(d.scope_full !== false); })
      .catch(e => { setTenants([]); setLoadErr(e.message || String(e)); });
    W2.json("/api/platform/signups?status=pending")
      .then(d => {
        const arr = Array.isArray(d.signups) ? d.signups : [];
        setSignups(arr); setPending(num(d.pending_count) || arr.length);
      })
      .catch(e => { setSignups([]); setSigErr(e.message || String(e)); });
  }, [tick]);
  _e(() => {
    const h = (e) => { if (e.key === "Escape") { setSel(null); setFlow(null); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const all = tenants || [];
  const actives = all.filter(c => (c.status || "active") === "active");
  const suspended = all.filter(c => c.status === "suspended");
  const sigs = signups || [];
  const list = _mm(() => {
    let arr = all;
    if (st === "active") arr = actives;
    if (st === "suspended") arr = suspended;
    const k = q.trim().toLowerCase();
    if (k) arr = arr.filter(c => ((c.name || "") + " " + (c.slug || "") + " " + (c.template_name || "") + " " + (c.industry_template || "")).toLowerCase().includes(k));
    return arr;
  }, [tenants, st, q]);
  const selCo = sel ? all.find(c => c.slug === sel) : null;

  /* POST /api/platform/signups/<id>/approve|reject {note} —— 逐字照抄 1.0 page-companies.jsx */
  const decide = (s, action) => {
    if (busyId != null) return;
    setBusyId(s.id);
    setRowErr(p => ({ ...p, [s.id]: "" }));
    W2.post("/api/platform/signups/" + encodeURIComponent(s.id) + "/" + action, { note: action === "reject" ? reason.trim() : "" })
      .then(res => {
        setNotice(action === "approve"
          ? { tone: "ok", text: t("已開通「{name}」:租戶 /{slug}(#{id})已建立,管理員 @{admin} 可登入。",
              { name: s.company_name || "—", slug: (res && res.slug) || s.slug || "—", id: (res && res.tenant_id) != null ? res.tenant_id : "—", admin: s.admin_username || "—" }) }
          : { tone: "plain", text: t("已駁回申請 #{id}「{name}」。", { id: s.id, name: s.company_name || "—" }) });
        setFlow(null); setReason("");
        setTick(v => v + 1);                   // 結果呈現後 reload 列表
      })
      .catch(e => setRowErr(p => ({ ...p, [s.id]: e.message || String(e) })))
      .finally(() => setBusyId(null));
  };

  const kv = (x) => (tenants === null ? "—" : x);

  return (<>
    <AdminMark/>
    <Folio no="18" en="COMPANIES / PLATFORM" title={t("公司 / 平臺")}
      sub={t("公司生命週期 · 入駐審批 · 跨公司平臺管理 · 僅平臺所有者")}
      right={<>
        <B icon="refresh" onClick={() => setTick(v => v + 1)}>{t("刷新")}</B>
        <B icon="sparkle" onClick={() => ask(t("平台上現在有哪些公司最活躍?哪些長期閒置?給我一份經營摘要"))}>{t("問平台概況")}</B>
      </>}/>

    {/* Band A · 平臺總覽 */}
    <div className="kpi-band">
      <Kpi label={t("在營公司")} value={kv(actives.length)} unit={t("家")} delay={0}
        foot={actives.length ? <T tone="ok" dot>{t("運行中")}</T> : <span className="muted" style={{ fontSize: 11.5 }}>—</span>}/>
      <Kpi label={t("待審申請")} value={signups === null ? "—" : pending} unit={t("條")} red={pending > 0} delay={.05}
        foot={pending > 0 ? <T tone="redinv">{t("{n} 條待審批 · 批准即建租戶庫", { n: pending })}</T> : <T tone="ok" dot>{t("無待審")}</T>}/>
      <Kpi label={t("停用公司")} value={kv(suspended.length)} unit={t("家")} red={suspended.length > 0} delay={.1}
        foot={suspended.length ? <T tone="bad" dot>{t("停用")}</T> : <T tone="ok" dot>{t("無停用")}</T>}/>
      <Kpi label={t("租戶庫總數")} value={kv(all.length)} unit={t("個")} delay={.15}
        foot={scopeFull ? <T tone="plain">{t("全平臺")}</T> : <T tone="warn">{t("僅授權範圍")}</T>}/>
    </div>
    <ErrLine err={loadErr} style={{ padding: "8px 0 0" }}/>

    {/* Band B · 入駐審批(真調 approve / reject)*/}
    <Band no="A" title={t("入駐審批")} sub={sigs.length ? t("{n} 條待審批 · 批准即建租戶庫", { n: sigs.length }) : null} delay={.1}>
      {notice && (
        <div className="row g10 wrap" style={{ padding: "10px 12px", border: "1px solid var(--hair)", background: "var(--paper-2)", marginBottom: 12 }}>
          <T tone={notice.tone === "ok" ? "ok" : "plain"} dot>{notice.text}</T>
        </div>
      )}
      <ErrLine err={sigErr} style={{ paddingBottom: 8 }}/>
      {signups === null
        ? <div className="muted" style={{ fontSize: 12.5, padding: "16px 0" }}>{t("載入中…")}</div>
        : !sigs.length
          ? <EM icon="clipboard" title={t("暫無待審批的入駐申請")} sub={t("企業提交入駐申請後會第一時間出現在這裡;批准即建立租戶資料庫與初始管理員。")}/>
          : <div style={{ borderTop: "2px solid var(--rule)" }}>
              {sigs.map((s, i) => (
                <div key={s.id != null ? s.id : i}>
                  <div className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <div className="col g4" style={{ flex: 1.6, minWidth: 0 }}>
                      <div className="row g10 wrap">
                        <span style={{ fontWeight: 700, fontSize: 13.5 }}>{s.company_name || "—"}</span>
                        <span className="num muted" style={{ fontSize: 11 }}>/{s.slug || "—"}</span>
                        <T tone="warn" dot>{t("待審申請")}</T>
                      </div>
                      <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>
                        {t("申請人")} {s.admin_display_name || "—"} <span className="num">@{s.admin_username || "—"}</span>
                        {" · "}{t("聯繫方式")} {s.contact || "—"}
                        {" · "}{t("申請於")} <span className="num">{day(s.created_at)}</span>
                        {s.reason ? <> · {t("理由")} {s.reason}</> : null}
                      </div>
                    </div>
                    <T tone="plain">{s.template_name || s.industry_template || "—"}</T>
                    <div className="row g6">
                      <B size="sm" kind="primary" disabled={busyId != null}
                        onClick={() => { setFlow({ id: s.id, mode: "approve" }); setReason(""); setRowErr(p => ({ ...p, [s.id]: "" })); }}>
                        {t("批准開通")}
                      </B>
                      <B size="sm" kind="red" disabled={busyId != null}
                        onClick={() => { setFlow({ id: s.id, mode: "reject" }); setReason(""); setRowErr(p => ({ ...p, [s.id]: "" })); }}>
                        {t("駁回")}
                      </B>
                    </div>
                  </div>
                  {flow && flow.id === s.id && (
                    <div className="col g8" style={{ borderLeft: "2px solid var(--red)", background: "var(--paper-2)", padding: "12px 14px", margin: "0 0 6px 26px" }}>
                      {flow.mode === "approve" ? (<>
                        <div style={{ fontSize: 12, lineHeight: 1.65 }}>
                          {t("二次確認:即將開通「{name}」(/{slug} · 模板 {tpl}),初始管理員 @{admin}。開通後立即建庫並可登入。",
                            { name: s.company_name || "—", slug: s.slug || "—", tpl: s.template_name || s.industry_template || "—", admin: s.admin_username || "—" })}
                        </div>
                        <div className="row g8">
                          <B size="sm" kind="primary" disabled={busyId != null} onClick={() => decide(s, "approve")}>
                            {busyId === s.id ? t("執行中…") : t("確認開通")}
                          </B>
                          <B size="sm" onClick={() => setFlow(null)}>{t("取消")}</B>
                        </div>
                      </>) : (<>
                        <div style={{ fontSize: 12, lineHeight: 1.65 }}>
                          {t("駁回申請 #{id}「{name}」:請輸入駁回原因,確認後寫回申請單。", { id: s.id != null ? s.id : "—", name: s.company_name || "—" })}
                        </div>
                        <input className="field" value={reason} onChange={e => setReason(e.target.value)}
                          placeholder={t("駁回原因(必填)")} autoFocus/>
                        <div className="row g8">
                          <B size="sm" kind="red" disabled={!reason.trim() || busyId != null} onClick={() => decide(s, "reject")}>
                            {busyId === s.id ? t("執行中…") : t("確認駁回")}
                          </B>
                          <B size="sm" onClick={() => setFlow(null)}>{t("取消")}</B>
                        </div>
                      </>)}
                      <ErrLine err={rowErr[s.id]}/>
                    </div>
                  )}
                </div>
              ))}
            </div>}
    </Band>

    {/* Band C · 公司台賬 */}
    <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <Band no="B" title={t("公司台賬")} sub={t("共 {n} 家 · 點行開抽屜與動作區", { n: all.length })} delay={.15}
          right={<div className="row g10 wrap">
            <div style={{ position: "relative", minWidth: 200 }}>
              <I name="search" size={13} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
              <input className="field" style={{ paddingLeft: 22, height: 32, fontSize: 12.5 }} value={q}
                onChange={e => setQ(e.target.value)} placeholder={t("搜索公司名 / 企業代碼")}/>
            </div>
            <div className="seg">
              {[["all", "全部"], ["active", "啟用"], ["suspended", "停用"]].map(([id, label]) => (
                <button key={id} className={st === id ? "on" : ""} onClick={() => setSt(id)}>{t(label)}</button>
              ))}
            </div>
          </div>}>
          {tenants === null
            ? <div className="muted" style={{ fontSize: 12.5, padding: "18px 0" }}>{t("載入中…")}</div>
            : !list.length
              ? <EM icon="building"
                  title={all.length ? t("當前篩選下沒有公司") : t("還沒有公司")}
                  sub={all.length ? t("換個關鍵詞或狀態試試。") : t("第一家公司可由入駐申請批准開通,或直接吩咐秘書開通。")}/>
              : <div style={{ overflowX: "auto" }}>
                  <table className="tbl2">
                    <thead><tr>
                      <th>{t("公司")}</th><th>{t("企業代碼")}</th><th>{t("行業模板")}</th>
                      <th>{t("成員")}</th><th>{t("建立")}</th><th>{t("狀態")}</th>
                    </tr></thead>
                    <tbody>
                      {list.map((c, i) => (
                        <tr key={c.id || c.slug || i} className={sel === c.slug ? "on" : ""}
                          onClick={() => setSel(sel === c.slug ? null : c.slug)} style={{ cursor: "pointer" }}>
                          <td><span style={{ fontWeight: 650 }}>{c.name || "—"}</span></td>
                          <td><span className="num muted">/{c.slug || "—"}</span></td>
                          <td className="muted">{c.template_name || c.industry_template || "—"}</td>
                          <td><span className="num" style={{ fontWeight: 700, fontSize: 15 }}>{c.member_count != null ? c.member_count : "—"}</span></td>
                          <td><span className="num muted" style={{ fontSize: 12 }}>{day(c.created_at)}</span></td>
                          <td><TenantTag st={c.status || "active"}/></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>}
        </Band>
      </div>
      {selCo && <CoDrawer co={selCo} refresh={tick} onClose={() => setSel(null)} onChanged={() => setTick(v => v + 1)}/>}
    </div>

    {/* Band D · 平台超級管理員 L11(授予 / 收回)*/}
    <OwnerBand refresh={tick}/>
  </>);
};

// L11 平台超級管理員(所有者自動合成 L11);後端 /api/platform/* 另有所有者硬閘
const _lvl11 = () => Math.max(0, ...(((window.W2_USER || {}).roles) || []).map(r => Number(r.level) || 0)) >= 11;
const Page = () => ((window.W2_IS_OWNER || _lvl11()) ? <Main/> : <Denied/>);

window.W2.PAGES["companies"] = Page;
})();
