/* WAREHOUSE 2.0 · 出庫 — Swiss 版式,真後端 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "領用出庫 · 借用歸還 · 搶修綠色通道 · 頁面只讀,操作交秘書": "Issues · loans & returns · emergency fast lane · read-only, actions via Secretary",
  "新建領用單": "New issue order",
  "緊急搶修出庫": "Emergency issue",
  "我要新建一張領用單,請逐項追問:用途(檢修/工程/搶修/借用/日常領用)、領用部門、關聯地點/項目、經辦人、物資明細(名稱/數量/單位),確認後執行出庫": "I want a new issue order. Ask me step by step: purpose (maintenance / engineering / emergency / loan / daily), department, site or project, handler, and item lines (name / qty / unit), then execute the issue.",
  "緊急搶修!走搶修綠色通道:請立刻追問故障類型與關聯地點,按預案清單快速出庫並標記為搶修,事後補全審批": "EMERGENCY! Use the fast lane: immediately ask me the fault type and site, issue the playbook kit at once, flag it urgent, and complete approval afterwards.",
  "出庫單 · 全部": "Outbound orders",
  "單": "orders", "筆": "",
  "今日 {n} 單": "{n} today",
  "搶修出庫": "Emergency issues",
  "無搶修": "No emergencies",
  "覆核搶修單 →": "Review →",
  "檢查最近的搶修出庫單,確認事後審批和庫存扣減都已補全": "Check recent emergency issues and confirm the after-the-fact approvals and stock deductions are complete.",
  "借用未還": "Loans out",
  "無逾期": "None overdue",
  "逾期 {n} 筆 · 催還 →": "{n} overdue · chase →",
  "審批中": "In approval",
  "無待審": "None waiting",
  "跟進審批 →": "Follow up →",
  "把審批中的出庫單列出來,幫我逐張跟進審批進度": "List the outbound orders still in approval and follow up on each one for me.",
  "出庫 / 領用流水": "Outbound / issue flow",
  "共 {n} 張單據": "{n} orders",
  "搜索單號 / 部門 / 物資 / 地點": "Search no. / dept / item / site",
  "全部用途": "All purposes",
  "搶修單": "Emergency",
  "單號": "Order no.",
  "時間": "Time",
  "領用部門": "Department",
  "用途": "Purpose",
  "關聯地點 / 項目": "Site / project",
  "{n} 項物資": "{n} lines",
  "已出庫": "Issued",
  "還沒有出庫記錄": "No outbound records yet",
  "對秘書說「出庫 2 雙絕緣手套給檢修一班」,第一張單就會出現在這裡。": "Say \"issue 2 pairs of insulated gloves to Repair Team 1\" to the Secretary — your first order will appear here.",
  "當前篩選下沒有單據": "No orders under current filter",
  "換個關鍵詞或篩選,或直接問秘書「幫我找某張出庫單」。": "Try another keyword or filter, or just ask the Secretary to find the order.",
  "照此單再出一單:{no},部門 {dept},地點 {target},物資 {list}。請追問是否有調整,確認後執行": "Repeat this order: {no}, department {dept}, site {target}, items {list}. Ask me for adjustments, then execute.",
  "查一下出庫單「{no}」的完整明細與審計記錄": "Show me the full lines and audit trail of outbound order \"{no}\".",
  "出庫單「{no}」還在審批中,幫我跟進並催辦審批": "Outbound order \"{no}\" is still in approval — follow up and chase it for me.",
  "出庫單「{no}」的物資已經還回,幫我登記歸還": "The items of order \"{no}\" have come back — register the return for me.",
  "再出一單": "Repeat",
  "問單據": "Ask",
  "搶修": "Emergency",
  "領用": "Issue",
  "檢修": "Maintenance",
  "工程": "Engineering",
  "借用": "Loan",
  "日常領用": "Daily issue",
  "物資明細": "Item lines",
  "物資項數": "Lines",
  "暫無物資明細": "No line details",
  "查詢審計記錄": "Audit trail",
  "催辦審批": "Chase approval",
  "登記歸還": "Register return",
  "借用未還清單": "Outstanding loans",
  "到期越近越靠前 · 逾期標紅": "nearest due first · overdue in red",
  "全部催還": "Chase all",
  "把所有借用未還的物資按逾期程度列出來,逐筆生成催還提醒並通知借用人": "List every outstanding loan by how overdue it is, create a return reminder for each and notify the borrower.",
  "沒有未歸還的借用": "No outstanding loans",
  "庫內 {n} 種借用類物資都已歸還。借用出庫時,秘書會自動登記歸還期限。": "All {n} loanable SKUs are back. When a loan is issued via the Secretary, a due date is registered automatically.",
  "預計歸還": "Due",
  "逾期 {n} 天": "{n} days overdue",
  "還有 {n} 天": "{n} days left",
  "今天到期": "Due today",
  "逾期": "Overdue",
  "已提醒": "Reminded",
  "待還": "On loan",
  "催還": "Chase",
  "催還「{item}」:單據 {tx},{qty} {unit},地點 {loc},預計歸還 {due}。生成催還提醒並通知經辦人": "Chase the return of \"{item}\": doc {tx}, {qty} {unit}, site {loc}, due {due}. Create a reminder and notify the handler.",
  "「{item}」已經還回來了(單據 {tx}),幫我登記歸還": "\"{item}\" has been returned (doc {tx}) — register the return for me.",
  "搶修綠色通道": "Emergency fast lane",
  "故障預案 · 一句話整單出庫": "Fault playbooks · one-sentence kit issue",
  "共 {n} 類故障": "{n} fault types",
  "備料齊全": "Stock ready",
  "{n} 項缺料": "{n} short",
  "關鍵": "KEY",
  "庫存 {n}": "stock {n}",
  "需 ×{n}": "need ×{n}",
  "按預案搶修出庫": "Issue per playbook",
  "緊急搶修:發生「{f}」,按預案出庫:{list}。請追問關聯地點/項目後立即出庫並標記為搶修,事後補全審批": "EMERGENCY: \"{f}\" occurred. Issue the playbook kit: {list}. Ask me the site / project, issue immediately flagged urgent, complete approval afterwards.",
  "尚未配置搶修預案": "No emergency playbooks yet",
  "配置好故障類型與必需物資後,現場一句話即可整單出庫。": "Once fault types and required materials are configured, one sentence on site issues the whole kit.",
  "幫我配置搶修綠色通道:建立常見故障類型與對應必需物資清單": "Set up the emergency fast lane for me: define common fault types and their required material lists.",
  "讓秘書建預案": "Set up via Secretary",
  "載入中…": "Loading…",
});
const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 數據規整:真後端(order_no/lines)與精簡形狀(no/item/to)都兜住 ── */
const normOrder = (r, i) => {
  r = r || {};
  const lines = Array.isArray(r.lines) && r.lines.length
    ? r.lines.map(l => ({ name: (l && l.name) || "—", qty: num(l && l.qty), unit: (l && l.unit) || "", loc: (l && l.loc) || "—" }))
    : (r.item ? [{ name: r.item, qty: num(r.qty), unit: r.unit || "", loc: r.wh || "—" }] : []);
  return {
    key: (r.id != null ? String(r.id) : "o") + ":" + i,
    no: String(r.no || r.id || "—"),
    time: String(r.time || r.date || "—"),
    dept: r.dept || r.to || "—",
    use: r.use || (r.urgent ? "搶修" : "領用"),
    target: r.target || "—",
    urgent: !!r.urgent,
    status: r.status === "done" ? "已出庫" : r.status === "pending" ? "審批中" : (r.status || "—"),
    summary: typeof r.qty === "string" ? r.qty : "",
    count: num(r.count) || lines.length,
    lines,
  };
};
const stTone = (s) => /已出庫|已出库|完成|issued|done/i.test(s) ? "ok" : /審批|审批|待|pending|approv/i.test(s) ? "warn" : "plain";
const lineText = (o) => o.lines.length ? o.lines.map(l => `${l.name}×${l.qty}${l.unit}`).join("、") : (o.summary || "—");
const DAY = 86400000;

const normBorrow = (r, i) => {
  r = r || {};
  const due = String(r.expected_return_at || "");
  const dueMs = Date.parse(due.replace(" ", "T"));
  const days = Number.isFinite(dueMs) ? Math.ceil((dueMs - Date.now()) / DAY) : null;
  return {
    key: (r.reminder_id != null ? String(r.reminder_id) : "b") + ":" + i,
    tx: r.transaction_no || "—",
    item: r.item_name || "—",
    cat: r.category_name || "—",
    qty: num(r.quantity),
    unit: r.unit || "",
    loc: r.work_location || "—",
    purpose: r.purpose || r.task_type || "—",
    due: due || "—",
    dueMs: Number.isFinite(dueMs) ? dueMs : Infinity,
    days,
    overdue: r.reminder_status === "overdue" || (days != null && days < 0),
    status: r.reminder_status || "pending",
  };
};

/* ── 出庫單抽屜 ── */
const OutDrawer = ({ o, onClose }) => {
  const approving = stTone(o.status) === "warn";
  const acts = [
    ["outbound", "再出一單", t("照此單再出一單:{no},部門 {dept},地點 {target},物資 {list}。請追問是否有調整,確認後執行", { no: o.no, dept: o.dept, target: o.target, list: lineText(o) })],
    ["doc", "查詢審計記錄", t("查一下出庫單「{no}」的完整明細與審計記錄", { no: o.no })],
  ];
  if (approving) acts.push(["clock", "催辦審批", t("出庫單「{no}」還在審批中,幫我跟進並催辦審批", { no: o.no })]);
  if (/借用|loan/i.test(o.use)) acts.push(["swap", "登記歸還", t("出庫單「{no}」的物資已經還回,幫我登記歸還", { no: o.no })]);
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            {o.urgent && <T tone="redinv" dot>{t("搶修")}</T>}
            <T tone={stTone(o.status)} dot>{t(o.status)}</T>
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div className="num" style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.02em", lineHeight: 1.25, color: o.urgent ? "var(--red)" : "var(--ink)" }}>{o.no}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{o.time}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {[[t("領用部門"), o.dept], [t("用途"), t(o.use)], [t("關聯地點 / 項目"), o.target], [t("物資項數"), `${o.count}`]].map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span style={{ fontSize: 14, fontWeight: 650 }}>{v}</span>
            </div>
          ))}
        </div>
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("物資明細")}</LB>
        <div style={{ borderTop: "2px solid var(--rule)", marginBottom: 18 }}>
          {o.lines.length ? o.lines.map((l, i) => (
            <div key={i} className="row g10" style={{ padding: "9px 2px", borderBottom: "1px solid var(--hair-soft)", fontSize: 12.5 }}>
              <span className="lr-idx" style={{ width: 20 }}>{pad2(i + 1)}</span>
              <span style={{ flex: 1, fontWeight: 600 }}>{l.name}</span>
              <span className="num" style={{ fontWeight: 700 }}>×{l.qty} {l.unit}</span>
              {l.loc !== "—" && <span className="num muted" style={{ fontSize: 11 }}>{l.loc}</span>}
            </div>
          )) : <div className="muted" style={{ fontSize: 12, padding: "10px 0" }}>{o.summary || t("暫無物資明細")}</div>}
        </div>
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {acts.map(([icon, label, prompt]) => (
            <button key={label} className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(prompt)}>
              <I name={icon} size={14}/>{t(label)}
            </button>
          ))}
        </div>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("2.0 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
      </div>
    </div>
  );
};

/* ── 頁面 ── */
const Page = ({ boot }) => {
  const orders = _mm(() => (Array.isArray(boot.OUTBOUND) ? boot.OUTBOUND : []).map(normOrder), [boot]);
  const faults = Array.isArray(boot.FAULT_TYPES) ? boot.FAULT_TYPES : [];
  const inv = Array.isArray(boot.INVENTORY) ? boot.INVENTORY : [];
  const loanableSkus = inv.filter(it => it && it.requiresReturn).length;

  const [pending, setPending] = _s(null);          // null = 載入中
  const [scope, setScope] = _s("all");             // all | urgent | approving
  const [useF, setUseF] = _s("all");
  const [q, setQ] = _s("");
  const [sel, setSel] = _s(null);

  _e(() => {
    W2.json("/api/returns/pending")
      .then(d => setPending(Array.isArray(d && d.rows) ? d.rows.map(normBorrow) : []))
      .catch(() => setPending([]));
    const h = (e) => { if (e.key === "Escape") setSel(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const borrows = _mm(() => [...(pending || [])].sort((a, b) => a.dueMs - b.dueMs), [pending]);
  const overdueN = borrows.filter(b => b.overdue).length;
  const urgentN = orders.filter(o => o.urgent).length;
  const approvingN = orders.filter(o => stTone(o.status) === "warn").length;
  const d0 = new Date();
  const todayStr = `${d0.getFullYear()}-${pad2(d0.getMonth() + 1)}-${pad2(d0.getDate())}`;
  const todayN = orders.filter(o => o.time.slice(0, 10) === todayStr).length;
  const uses = _mm(() => Array.from(new Set(orders.map(o => o.use))).slice(0, 6), [orders]);

  let list = orders;
  if (scope === "urgent") list = list.filter(o => o.urgent);
  if (scope === "approving") list = list.filter(o => stTone(o.status) === "warn");
  if (useF !== "all") list = list.filter(o => o.use === useF);
  if (q) {
    const k = q.toLowerCase();
    list = list.filter(o => (o.no + o.dept + o.target + o.use + lineText(o)).toLowerCase().includes(k));
  }

  return (
    <>
      <Folio no="04" en="OUTBOUND" title={t("出庫")}
        sub={t("領用出庫 · 借用歸還 · 搶修綠色通道 · 頁面只讀,操作交秘書")}
        right={<>
          <B icon="plus" onClick={() => ask(t("我要新建一張領用單,請逐項追問:用途(檢修/工程/搶修/借用/日常領用)、領用部門、關聯地點/項目、經辦人、物資明細(名稱/數量/單位),確認後執行出庫"))}>{t("新建領用單")}</B>
          <B kind="red" icon="flame" onClick={() => ask(t("緊急搶修!走搶修綠色通道:請立刻追問故障類型與關聯地點,按預案清單快速出庫並標記為搶修,事後補全審批"))}>{t("緊急搶修出庫")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={t("出庫單 · 全部")} value={orders.length} unit={t("單")} delay={0}
          foot={<><span className="muted" style={{ fontSize: 11.5 }}>{t("今日 {n} 單", { n: todayN })}</span><T tone="plain">FLOW</T></>}/>
        <Kpi label={t("搶修出庫")} value={urgentN} unit={t("單")} red={urgentN > 0} delay={.05}
          foot={urgentN
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("檢查最近的搶修出庫單,確認事後審批和庫存扣減都已補全"))}>{t("覆核搶修單 →")}</button>
            : <T tone="ok" dot>{t("無搶修")}</T>}/>
        <Kpi label={t("借用未還")} value={pending === null ? "—" : borrows.length} unit={t("筆")} red={overdueN > 0} delay={.1}
          foot={pending === null
            ? <span className="muted" style={{ fontSize: 11.5 }}>{t("載入中…")}</span>
            : overdueN
              ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把所有借用未還的物資按逾期程度列出來,逐筆生成催還提醒並通知借用人"))}>{t("逾期 {n} 筆 · 催還 →", { n: overdueN })}</button>
              : <T tone="ok" dot>{t("無逾期")}</T>}/>
        <Kpi label={t("審批中")} value={approvingN} unit={t("單")} delay={.15}
          foot={approvingN
            ? <button className="tag warn" style={{ cursor: "pointer" }} onClick={() => ask(t("把審批中的出庫單列出來,幫我逐張跟進審批進度"))}>{t("跟進審批 →")}</button>
            : <T tone="plain">{t("無待審")}</T>}/>
      </div>

      <Band no="A" title={t("出庫 / 領用流水")} sub={t("共 {n} 張單據", { n: orders.length })} delay={.1}>
        <div className="row g14 wrap" style={{ paddingBottom: 16, borderBottom: "1px solid var(--hair)", marginBottom: 2 }}>
          <div style={{ position: "relative", flex: 1, minWidth: 240 }}>
            <I name="search" size={15} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="field" style={{ paddingLeft: 26, height: 38 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t("搜索單號 / 部門 / 物資 / 地點")}/>
          </div>
          <div className="seg">
            {[["all", "全部"], ["urgent", "搶修單"], ["approving", "審批中"]].map(([id, label]) => (
              <button key={id} className={scope === id ? "on" : ""} onClick={() => setScope(id)}>{t(label)}</button>
            ))}
          </div>
          <div className="row g6 wrap">
            <button className={"chip" + (useF === "all" ? " on" : "")} onClick={() => setUseF("all")}>{t("全部用途")}</button>
            {uses.map(u => (
              <button key={u} className={"chip" + (useF === u ? " on" : "")} onClick={() => setUseF(u)}>
                {u === "搶修" && <I name="flame" size={10}/>}{t(u)}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("單號")}</th><th>{t("時間")}</th><th>{t("領用部門")}</th><th>{t("用途")}</th><th>{t("關聯地點 / 項目")}</th><th>{t("物資")}</th><th>{t("狀態")}</th><th style={{ width: 96 }}>{t("交給秘書")}</th>
                </tr></thead>
                <tbody>
                  {list.map(o => (
                    <tr key={o.key} className={sel && sel.key === o.key ? "on" : ""} onClick={() => setSel(o)} style={{ cursor: "pointer" }}>
                      <td>
                        <span className="row g6">
                          {o.urgent && <I name="flame" size={12} color="var(--red)"/>}
                          <span className="num" style={{ fontWeight: 700, color: o.urgent ? "var(--red)" : "var(--ink)" }}>{o.no}</span>
                        </span>
                      </td>
                      <td className="num muted" style={{ fontSize: 12 }}>{o.time}</td>
                      <td style={{ fontWeight: 600 }}>{o.dept}</td>
                      <td>{o.urgent || o.use === "搶修" ? <T tone="redinv">{t("搶修")}</T> : <T tone="plain">{t(o.use)}</T>}</td>
                      <td className="muted">{o.target}</td>
                      <td>
                        <div className="col g2">
                          <span style={{ fontSize: 12.5 }}>{o.lines.length ? t("{n} 項物資", { n: o.lines.length }) : (o.summary || "—")}</span>
                          {!!o.lines.length && <span className="muted" style={{ fontSize: 11, maxWidth: 260, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{lineText(o)}</span>}
                        </div>
                      </td>
                      <td><T tone={stTone(o.status)} dot>{t(o.status)}</T></td>
                      <td onClick={e => e.stopPropagation()}>
                        <div className="row g4">
                          <button className="btn sm" title={t("再出一單")} style={{ padding: "0 8px" }} onClick={() => ask(t("照此單再出一單:{no},部門 {dept},地點 {target},物資 {list}。請追問是否有調整,確認後執行", { no: o.no, dept: o.dept, target: o.target, list: lineText(o) }))}><I name="outbound" size={12}/></button>
                          <button className="btn sm" title={t("問單據")} style={{ padding: "0 8px" }} onClick={() => ask(t("查一下出庫單「{no}」的完整明細與審計記錄", { no: o.no }))}><I name="sparkle" size={12}/></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!list.length && (orders.length
              ? <EM icon="search" title={t("當前篩選下沒有單據")} sub={t("換個關鍵詞或篩選,或直接問秘書「幫我找某張出庫單」。")}/>
              : <EM icon="outbound" title={t("還沒有出庫記錄")} sub={t("對秘書說「出庫 2 雙絕緣手套給檢修一班」,第一張單就會出現在這裡。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(t("我要新建一張領用單,請逐項追問:用途(檢修/工程/搶修/借用/日常領用)、領用部門、關聯地點/項目、經辦人、物資明細(名稱/數量/單位),確認後執行出庫"))}>{t("新建領用單")}</B>}/>)}
          </div>
          {sel && <OutDrawer o={sel} onClose={() => setSel(null)}/>}
        </div>
      </Band>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
        <div style={{ paddingRight: 28, minWidth: 0 }}>
        <Band no="B" title={t("借用未還清單")} sub={t("到期越近越靠前 · 逾期標紅")} delay={.15}
          right={!!borrows.length && <B size="sm" icon="sparkle" onClick={() => ask(t("把所有借用未還的物資按逾期程度列出來,逐筆生成催還提醒並通知借用人"))}>{t("全部催還")}</B>}>
          <div>
            {borrows.length ? (
              <div style={{ borderTop: "2px solid var(--rule)" }}>
                {borrows.map((b, i) => (
                  <div key={b.key} className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <div className="col g4" style={{ flex: 1.3, minWidth: 0 }}>
                      <span style={{ fontWeight: 650, fontSize: 13 }}>{b.item}</span>
                      <span className="num muted" style={{ fontSize: 10.5 }}>{b.tx} · {b.cat}</span>
                    </div>
                    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                      <span className="num" style={{ fontSize: 12.5, fontWeight: 700 }}>×{b.qty} {b.unit}</span>
                      <span className="muted" style={{ fontSize: 10.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{b.loc}</span>
                    </div>
                    <div className="col g4" style={{ width: 108, flexShrink: 0 }}>
                      <span className="num" style={{ fontSize: 11.5, fontWeight: 650, color: b.overdue ? "var(--red)" : "var(--ink-2)" }}>{b.due.slice(0, 10) || "—"}</span>
                      <span className="num" style={{ fontSize: 10.5, color: b.overdue ? "var(--red)" : "var(--ink-3)" }}>
                        {b.days == null ? "—" : b.days < 0 ? t("逾期 {n} 天", { n: -b.days }) : b.days === 0 ? t("今天到期") : t("還有 {n} 天", { n: b.days })}
                      </span>
                    </div>
                    {b.overdue ? <T tone="bad" dot>{t("逾期")}</T> : b.status === "sent" ? <T tone="warn">{t("已提醒")}</T> : <T tone="plain">{t("待還")}</T>}
                    <div className="col g4">
                      <button className={"btn sm" + (b.overdue ? " red" : "")} style={{ padding: "0 10px" }}
                        onClick={() => ask(t("催還「{item}」:單據 {tx},{qty} {unit},地點 {loc},預計歸還 {due}。生成催還提醒並通知經辦人", { item: b.item, tx: b.tx, qty: b.qty, unit: b.unit, loc: b.loc, due: b.due }))}>{t("催還")}</button>
                      <button className="btn sm" style={{ padding: "0 10px" }}
                        onClick={() => ask(t("「{item}」已經還回來了(單據 {tx}),幫我登記歸還", { item: b.item, tx: b.tx }))}>{t("登記歸還")}</button>
                    </div>
                  </div>
                ))}
              </div>
            ) : pending === null
              ? <div className="muted" style={{ fontSize: 12, padding: "24px 0" }}>{t("載入中…")}</div>
              : <EM icon="swap" title={t("沒有未歸還的借用")} sub={t("庫內 {n} 種借用類物資都已歸還。借用出庫時,秘書會自動登記歸還期限。", { n: loanableSkus })}/>}
          </div>
        </Band>
        </div>

        <div style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)", minWidth: 0 }}>
        <Band no="C" title={t("搶修綠色通道")} sub={faults.length ? t("共 {n} 類故障", { n: faults.length }) : t("故障預案 · 一句話整單出庫")} delay={.2}>
          <div className="col g12">
            {faults.length ? faults.map((f, fi) => {
              const items = Array.isArray(f && f.items) ? f.items : [];
              const shortN = items.filter(it => num(it && it.stock) < num(it && it.qty)).length;
              const listStr = items.map(it => `${(it && it.name) || "—"}×${num(it && it.qty)}${(it && it.unit) || ""}`).join("、");
              return (
                <div key={(f && f.id) || fi} className="panel" style={{ padding: "14px 16px", borderColor: shortN ? "var(--red)" : "var(--hair)" }}>
                  <div className="row spread" style={{ marginBottom: 10 }}>
                    <span className="row g8" style={{ fontWeight: 700, fontSize: 13.5 }}><I name="flame" size={13} color="var(--red)"/>{(f && f.name) || "—"}</span>
                    {shortN ? <T tone="bad" dot>{t("{n} 項缺料", { n: shortN })}</T> : <T tone="ok" dot>{t("備料齊全")}</T>}
                  </div>
                  <div style={{ borderTop: "1px solid var(--hair-soft)", marginBottom: 10 }}>
                    {items.slice(0, 5).map((it, ii) => {
                      const short = num(it && it.stock) < num(it && it.qty);
                      return (
                        <div key={ii} className="row g8" style={{ padding: "7px 0", borderBottom: "1px solid var(--hair-soft)", fontSize: 12 }}>
                          <span style={{ flex: 1, fontWeight: 600 }}>{(it && it.name) || "—"}{it && it.key && <span className="mono" style={{ fontSize: 8.5, letterSpacing: ".12em", color: "var(--red)", marginLeft: 6 }}>{t("關鍵")}</span>}</span>
                          <span className="num muted" style={{ fontSize: 11 }}>{t("需 ×{n}", { n: num(it && it.qty) })} {(it && it.unit) || ""}</span>
                          <span className="num" style={{ fontSize: 11, fontWeight: 650, color: short ? "var(--red)" : "var(--ink-3)" }}>{t("庫存 {n}", { n: num(it && it.stock) })}</span>
                        </div>
                      );
                    })}
                  </div>
                  <button className="btn red sm" style={{ width: "100%" }}
                    onClick={() => ask(t("緊急搶修:發生「{f}」,按預案出庫:{list}。請追問關聯地點/項目後立即出庫並標記為搶修,事後補全審批", { f: (f && f.name) || "—", list: listStr || "—" }))}>
                    <I name="flame" size={12}/>{t("按預案搶修出庫")}
                  </button>
                </div>
              );
            }) : <EM icon="flame" title={t("尚未配置搶修預案")} sub={t("配置好故障類型與必需物資後,現場一句話即可整單出庫。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(t("幫我配置搶修綠色通道:建立常見故障類型與對應必需物資清單"))}>{t("讓秘書建預案")}</B>}/>}
          </div>
        </Band>
        </div>
      </div>
    </>
  );
};

window.W2.PAGES["outbound"] = Page;
})();
