/* WAREHOUSE 2.0 · ERP 中樞 — Swiss 版式,真後端(/api/erp/overview 駕駛艙子集) */
(() => {
const W2 = window.W2;
const { t, lang } = window.W2_LANG;
const L = lang();
window.W2_LANG.addEN({
  "ERP 中樞": "ERP Hub",
  "預算 · 採購 · 閉環 · {p} · 頁面只讀,操作交秘書": "Budget · Procurement · Closure · {p} · Read-only, actions via Secretary",
  "刷新": "Refresh",
  "問秘書": "Ask Secretary",
  "ERP 現在最需要處理什麼?按預算、採購、閉環分類,給我優先級清單": "What needs attention in ERP right now? Give me a prioritised list across budgets, procurement and closure",
  "當前期間": "Current period",
  "讀取 ERP 數據…": "Loading ERP data…",
  "可用預算": "Available budget",
  "元": "CNY",
  "萬元": "×10K CNY",
  "億元": "×100M CNY",
  "總額 {a} · 已用 {u}%": "Total {a} · {u}% used",
  "預算使用率": "Budget usage",
  "已佔用 {r} · 已支出 {s}": "Reserved {r} · Spent {s}",
  "未掛預算單據": "Unlinked documents",
  "張": "docs",
  "讓秘書關聯 →": "Secretary: link →",
  "全部閉環": "All closed",
  "把所有未掛預算的庫存單據列出來,逐張關聯到合適的可用預算,先給我方案": "List every inventory document without a budget link and link each to a suitable available budget; propose a plan first",
  "活躍預警": "Open alerts",
  "條": "items",
  "交秘書處置 →": "Secretary: handle →",
  "無預警": "No alerts",
  "把 ERP 相關的活躍預警列出來,按風險排序給我處置方案": "List the open ERP-related alerts sorted by risk and give me handling plans",
  "成本中心": "Cost centers",
  "進行工單": "Open work orders",
  "進行採購": "Open purchases",
  "活躍供應商": "Active suppliers",
  "庫存單據": "Inventory documents",
  "預算": "Budgets",
  "進行 {a} · 待閉環 {r} · 歸檔 {c}": "Active {a} · Review {r} · Archived {c}",
  "進行中": "Active",
  "待閉環": "Pending closure",
  "已歸檔": "Archived",
  "全部": "All",
  "編號": "No.",
  "成本中心 / 科目": "Cost center / Account",
  "期間": "Period",
  "額度": "Amount",
  "可用": "Available",
  "使用率": "Usage",
  "狀態": "Status",
  "交給秘書": "To Secretary",
  "預算中心": "Budget center",
  "交秘書": "Secretary",
  "草稿": "Draft",
  "計劃": "Planned",
  "暫停": "Paused",
  "完成": "Completed",
  "凍結": "Frozen",
  "已關閉": "Closed",
  "已佔用": "Reserved",
  "已批准": "Approved",
  "已提交": "Submitted",
  "已下單": "Ordered",
  "已到貨": "Received",
  "已支出": "Spent",
  "已釋放": "Released",
  "已取消": "Cancelled",
  "已確認": "Confirmed",
  "已過賬": "Posted",
  "待處理": "Pending",
  "AI 閉環": "AI closed",
  "異常": "Exception",
  "預算「{no}」({cc} · {acc})顯示{st},原因:{r}。請核對並完成閉環或結項,先給方案,我確認後執行": "Budget \"{no}\" ({cc} · {acc}) shows {st}, reason: {r}. Verify and close or finalise it; propose a plan and execute after my confirmation",
  "分析預算「{no}」({cc} · {acc}):額度 {amt},可用 {av},使用率 {u}%。有無風險?給下一步建議": "Analyse budget \"{no}\" ({cc} · {acc}): amount {amt}, available {av}, usage {u}%. Any risks? Suggest next steps",
  "還沒有預算": "No budgets yet",
  "對秘書說「為◯◯成本中心建立◯◯預算 50000 元」即可開始。": "Tell the Secretary \"create a 50,000 budget for cost center X\" to get started.",
  "讓秘書建預算": "Create via Secretary",
  "我要建立一筆預算,請追問成本中心、科目、期間和金額後執行": "I want to create a budget; ask me for the cost center, account, period and amount, then execute",
  "當前篩選下沒有預算": "No budgets under this filter",
  "採購申請": "Purchase requests",
  "進行 {o} · 歸檔 {a} · 供應商 {s}": "Open {o} · Archived {a} · Suppliers {s}",
  "申請號": "Request no.",
  "業務全鏈": "Business trail",
  "查看全鏈": "View trail",
  "標題 / 明細": "Title / Lines",
  "供應商": "Supplier",
  "金額": "Amount",
  "未指定供應商": "No supplier",
  "未命名物資": "Unnamed item",
  "未填明細": "No lines",
  "{p} 等 {n} 項": "{p} · {n} lines",
  "緊急": "Urgent",
  "提交": "Submit",
  "提交並建立採購工作流": "Submit and start the procurement workflow",
  "到採購待辦按節點審批": "Handle the approval through procurement workflow tasks",
  "等待工作流簽發正式 PO": "Wait for the workflow to issue the formal PO",
  "使用已簽發 PO 登記採購收貨": "Register the purchase receipt against the issued PO",
  "採購申請「{no} · {title}」當前狀態「{st}」;金額 {amt},供應商 {sp}。請核對關聯工作流與業務全鏈,下一步按「{nx}」辦理;不得直接改成批准、下單或到貨": "Purchase request \"{no} · {title}\" is currently \"{st}\"; amount {amt}, supplier {sp}. Verify the linked workflow and business trail, then proceed via \"{nx}\"; never directly set it to approved, ordered or received",
  "看看採購申請「{no} · {title}」的情況,給我下一步建議": "Review purchase request \"{no} · {title}\" and suggest next steps",
  "還沒有採購申請": "No purchase requests yet",
  "對秘書說「採購一批◯◯,預算 5000」即可發起。": "Tell the Secretary \"purchase some X with a 5,000 budget\" to start one.",
  "讓秘書發起採購": "Start via Secretary",
  "我要發起一筆採購申請:請追問物資、數量、預算、供應商和適用採購流程;建立真實 ERP 主單後必須同步綁定並啟動該工作流,不得建立孤立流程或直接批准": "Raise a purchase request: ask for items, quantities, budget, supplier and the applicable procurement workflow. After creating the real ERP master record, bind and start that workflow synchronously; never create an orphan workflow or approve directly.",
  "當前篩選下沒有採購申請": "No purchase requests under this filter",
  "未閉環事項": "Open-loop items",
  "{n} 項待處理": "{n} pending",
  "一鍵全部交秘書": "Hand all to Secretary",
  "把 ERP 未閉環事項(未掛預算單據、預算佔用、進行中盤點)逐項給我處置方案,我確認後執行": "Go through the ERP open-loop items (unlinked documents, budget reservations, running stocktakes) one by one with handling plans; execute after my confirmation",
  "未掛預算": "No budget link",
  "預算佔用": "Budget reservation",
  "盤點": "Stocktake",
  "明細 {n} 項": "{n} lines",
  "差異 {n} 項": "{n} diffs",
  "全庫": "Whole warehouse",
  "沒有未閉環事項": "No open-loop items",
  "佔用、單據與盤點全部閉環。秘書持續盯守,有異常會出現在這裡。": "All reservations, documents and stocktakes are closed. The Secretary keeps watch; exceptions surface here.",
  "把庫存單據「{no}」關聯到合適的可用預算,金額按單據核定;先給我方案,確認後執行": "Link inventory document \"{no}\" to a suitable available budget, amount per the document; propose a plan first and execute after confirmation",
  "預算佔用「{no}」({title},金額 {amt})該如何閉環?可批准、記支出或釋放;給我建議,確認後執行": "How should budget reservation \"{no}\" ({title}, amount {amt}) be closed? Approve, mark spent or release; advise me and execute after confirmation",
  "盤點任務「{no}」({name})還未閉環,差異 {n} 項;幫我跟進收尾": "Stocktake task \"{no}\" ({name}) is still open with {n} diffs; help me follow up and close it",
  "手動": "Manual",
  "共創計劃": "Collab plan",
  "工單": "Work order",
  "採購": "Purchase",
  "其他": "Other",
  // 統計圖
  "資金節奏": "Funding rhythm", "撥款 / 支出 · 按月": "appropriation / spend · monthly",
  "撥款": "Appropriation", "支出": "Spend",
  "還沒有資金流水": "No journal entries yet",
  "撥款或支出後,月度節奏會出現在這裡。": "The monthly rhythm appears once funds move.",
  "成本中心資金": "Cost center funds", "按額度 · 前 {n}": "top {n} by amount", "尚未設置": "not set",
  "還沒有成本中心預算": "No cost-center budgets yet",
  "預算執行": "Budget execution",
  "已支出": "Spent", "已佔用": "Reserved",
  "採購管道": "Purchase pipeline", "按流程階段 · 金額與單數": "by stage · amount & count",
  "{n} 張": "{n} reqs",
  "成本中心「{name}」的預算使用情況怎麼樣?哪裡緊張?": "How is cost center \"{name}\" using its budgets? Where is it tight?",
  "處於「{st}」階段的採購申請有哪些?下一步怎麼推進?": "Which purchase requests are at the \"{st}\" stage? How do we move them forward?",
});

const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Empty: EM, Kpi, Folio, Band, pad2, num, MirrorBars, HBar } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 三段執行條(Swiss:實心=已支出 · 中灰=已佔用 · 底=可用,2px 縫) ── */
const SegBar = ({ spent, reserved, amount }) => {
  const a = Math.max(num(amount), num(spent) + num(reserved)) || 1;
  const sp = Math.min(100, num(spent) / a * 100);
  const rv = Math.min(100 - sp, num(reserved) / a * 100);
  return (
    <span className="hbar-track" style={{ display: "flex", gap: 2, background: "var(--paper-2)", overflow: "hidden" }}>
      {sp > 0 && <i style={{ width: sp + "%", background: "var(--ink)", flexShrink: 0 }}/>}
      {rv > 0 && <i style={{ width: rv + "%", background: "#85806F", flexShrink: 0 }}/>}
    </span>
  );
};
const SegLegend = () => (
  <div className="row g12 wrap" style={{ marginTop: 10, fontSize: 11, color: "var(--ink-2)" }}>
    <span className="row g6"><i style={{ width: 9, height: 9, background: "var(--ink)" }}/>{t("已支出")}</span>
    <span className="row g6"><i style={{ width: 9, height: 9, background: "#85806F" }}/>{t("已佔用")}</span>
    <span className="row g6"><i style={{ width: 9, height: 9, background: "var(--paper-2)", border: "1px solid var(--hair)" }}/>{t("可用")}</span>
  </div>
);
/* 三段條排行行:名稱 + SegBar + 使用率 + 可用額 */
const SegRow = ({ idx, name, sub, spent, reserved, amount, onClick, title }) => {
  const a = Math.max(num(amount), num(spent) + num(reserved));
  const u = a ? Math.min(100, Math.round((num(spent) + num(reserved)) / a * 100)) : 0;
  const av = num(amount) - num(spent) - num(reserved);
  return (
    <div className="hbar-row" title={title} style={onClick ? { cursor: "pointer" } : undefined} onClick={onClick}>
      <span className="hb-idx">{pad2(idx)}</span>
      {/* display:block:類的 text-overflow ellipsis 在 flex 容器上不生效 */}
      <span className="hb-name" title={sub ? name + " · " + sub : name} style={{ display: "block" }}>
        {name}{sub ? <span className="muted" style={{ fontWeight: 400, fontSize: 10.5 }}> · {sub}</span> : null}
      </span>
      <SegBar spent={spent} reserved={reserved} amount={amount}/>
      <span className="hb-val num" style={av < 0 ? { color: "var(--red)" } : undefined}>{kMoney(av)[0]}{t(kMoney(av)[1])}</span>
      <span className="hb-pct num" style={u > 90 ? { color: "var(--red)" } : undefined}>{u}%</span>
    </div>
  );
};

/* ── 格式化 ── */
const money = (v, c) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return ((!c || c === "CNY") ? "¥" : c + " ") + n.toLocaleString("zh-CN", { maximumFractionDigits: 2 });
};
const kMoney = (v) => {
  const n = Number(v) || 0;
  const a = Math.abs(n);
  if (a >= 1e8) return [+(n / 1e8).toFixed(1), "億元"];
  if (a >= 1e4) return [+(n / 1e4).toFixed(1), "萬元"];
  return [Math.round(n), "元"];
};

/* ── 後端狀態字典(語氣 + 繁中) ── */
const ST = {
  draft: ["plain", "草稿"], planned: ["plain", "計劃"], active: ["ok", "進行中"], paused: ["warn", "暫停"],
  completed: ["ok", "完成"], frozen: ["warn", "凍結"], closed: ["plain", "已關閉"], reserved: ["warn", "已佔用"],
  approved: ["ok", "已批准"], submitted: ["warn", "已提交"], ordered: ["warn", "已下單"], received: ["ok", "已到貨"],
  spent: ["bad", "已支出"], released: ["plain", "已釋放"], cancelled: ["plain", "已取消"], confirmed: ["ok", "已確認"],
  posted: ["ok", "已過賬"], pending: ["warn", "待處理"], pending_closure: ["warn", "待閉環"],
  auto_closed: ["ok", "AI 閉環"], exception: ["bad", "異常"],
};
const stKey = (v) => String(v == null ? "" : v).trim().toLowerCase();
const stText = (v) => { const m = ST[stKey(v)]; return m ? t(m[1]) : (v || "—"); };
const StTag = ({ v, dot }) => { const m = ST[stKey(v)]; return <T tone={m ? m[0] : "plain"} dot={dot}>{m ? t(m[1]) : (v || "—")}</T>; };
const SRC = { manual: "手動", collab_idea: "共創計劃", work_task: "工單", purchase_request: "採購", inventory_document: "庫存單據", other: "其他" };

/* ── 業務判定(照 1.0 口徑,全部防禦) ── */
const usageOf = (b) => { const a = num(b.amount); return a ? Math.min(100, Math.round((num(b.reserved) + num(b.spent)) / a * 100)) : 0; };
const budgetState = (b) => {
  const ai = b.ai_status || "";
  if (b.status === "closed" || ai === "auto_closed" || ai === "closed") return "archived";
  if (ai === "pending_closure" || ai === "exception") return "review";
  return "active";
};
const DOC_DONE = ["confirmed", "posted", "closed", "cancelled", "completed", "done", "已完成"];
const docOpen = (x) => !DOC_DONE.includes(stKey(x.status)) && !x.confirmed_at && !x.cancelled_at;
const docUnlinked = (x) => x.budget_unlinked_open === true
  || (x.budget_unlinked_open == null && docOpen(x) && x.needs_budget && !x.budget_reservation_id);
const rsvActive = (r) => !["spent", "released", "cancelled", "closed"].includes(stKey(r.status));
const stkOpen = (x) => !["completed", "closed", "cancelled", "done", "已完成"].includes(stKey(x.status));
const prOpen = (p) => !["received", "cancelled", "completed", "closed"].includes(stKey(p.status || "draft"));
const PR_NEXT = {
  draft: "提交並建立採購工作流",
  submitted: "到採購待辦按節點審批",
  approved: "等待工作流簽發正式 PO",
  ordered: "使用已簽發 PO 登記採購收貨",
};

const linePreview = (p) => {
  const lines = Array.isArray(p.lines) ? p.lines : [];
  if (!lines.length) return t("未填明細");
  const prev = lines.slice(0, 2).map((l) => (l.item_name || t("未命名物資")) + " ×" + num(l.quantity) + (l.unit || "")).join("、");
  return lines.length > 2 ? t("{p} 等 {n} 項", { p: prev, n: lines.length }) : prev;
};
const purchaseEntityRef = (purchase) => {
  const supplied = purchase && W2.parseEntityRef && W2.parseEntityRef(purchase.entity_ref);
  if (supplied && supplied.type === "erp_purchase_request") return supplied.entity_ref;
  const id = Number(purchase && purchase.id);
  return Number.isInteger(id) && id > 0 ? W2.entityRef("erp_purchase_request", id) : "";
};

const Page = ({ boot, reload }) => {
  const [data, setData] = _s(null);
  const [tick, setTick] = _s(0);
  const [bScope, setBScope] = _s("active");
  const [pScope, setPScope] = _s("open");

  _e(() => {
    let on = true;
    W2.json("/api/erp/overview")
      .then((d) => { if (on) setData(d && typeof d === "object" ? d : {}); })
      .catch(() => { if (on) setData({}); });
    return () => { on = false; };
  }, [tick]);

  const d = data || {};
  const summary = d.summary || {};
  const budgets = Array.isArray(d.budgets) ? d.budgets : [];
  const purchases = Array.isArray(d.purchase_requests) ? d.purchase_requests : [];
  const reservations = Array.isArray(d.reservations) ? d.reservations : [];
  const docs = Array.isArray(d.inventory_documents) ? d.inventory_documents : [];
  const alerts = Array.isArray(d.open_alerts) ? d.open_alerts : [];
  const stocktakes = Array.isArray(d.stocktake_tasks) ? d.stocktake_tasks : [];
  const centers = Array.isArray(d.cost_centers) ? d.cost_centers : [];
  const monthly = d.monthly && typeof d.monthly === "object" ? d.monthly : {};

  /* ── 統計圖數據 ── */
  // 01 資金節奏:撥款 vs 支出(複式分錄按月),金額大時降到萬元刻度
  const fLabels = (Array.isArray(monthly.labels) ? monthly.labels : []).slice(-12);
  const fCut = (Array.isArray(monthly.labels) ? monthly.labels : []).length - fLabels.length;
  const fAppr = (Array.isArray(monthly.appropriation) ? monthly.appropriation : []).slice(fCut > 0 ? fCut : 0);
  const fSpend = (Array.isArray(monthly.spend) ? monthly.spend : []).slice(fCut > 0 ? fCut : 0);
  const hasFlow = fLabels.length > 0 && (fAppr.some(v => num(v) > 0) || fSpend.some(v => num(v) > 0));
  const flowScale = Math.max(...fAppr.map(num), ...fSpend.map(num), 0) >= 1e4 ? 1e4 : 1;
  // 柱高:負淨撥款(調減多於撥入)夾到 0,精確值看懸停;小額非零保底 0.1 格,避免縮尺後消失
  const fScl = (v) => { const r = num(v); if (r <= 0) return 0; return Math.max(+(r / flowScale).toFixed(1), .1); };
  const fApprS = fAppr.map(fScl);
  const fSpendS = fSpend.map(fScl);
  const monLabel = (l) => L === "en" ? String(l).replace(/^(\d{2})月$/, "$1") : l;
  const fTitle = (i) => `${monLabel(fLabels[i])} · ${t("撥款")} ${money(num(fAppr[i]))} · ${t("支出")} ${money(num(fSpend[i]))}`;
  // 02 成本中心資金(後端已聚合 budget_amount/reserved/spent)
  const ccTop = _mm(() => centers.filter(c => num(c.budget_amount) > 0)
    .sort((a, b) => num(b.budget_amount) - num(a.budget_amount)).slice(0, 6), [centers]);
  // 03 預算執行:進行中預算按額度取前 6
  const bTop = _mm(() => budgets.filter(b => budgetState(b) === "active" && num(b.amount) > 0)
    .sort((a, b) => num(b.amount) - num(a.amount)).slice(0, 6), [budgets]);
  // 04 採購管道:按流程階段彙總金額與單數
  const PIPE_STAGES = ["draft", "submitted", "approved", "ordered", "received"];
  const pipe = _mm(() => PIPE_STAGES.map(stg => {
    const rows = purchases.filter(p => stKey(p.status || "draft") === stg);
    return { stg, count: rows.length, amount: rows.reduce((s, p) => s + num(p.total_amount), 0) };
  }), [purchases]);
  const pipeMaxAmt = pipe.reduce((m, x) => Math.max(m, x.amount), 0);
  const pipeMaxCnt = pipe.reduce((m, x) => Math.max(m, x.count), 0);
  const hasPipe = pipe.some(x => x.count > 0);

  const unlinkedDocs = docs.filter(docUnlinked);
  const openRsv = reservations.filter(rsvActive);
  const openStk = stocktakes.filter(stkOpen);
  const openPr = purchases.filter(prOpen);
  const archPr = purchases.filter((p) => !prOpen(p));

  const unlinkedCount = Math.max(unlinkedDocs.length, num(summary.inventory_unlinked));
  const alertCount = Math.max(alerts.length, num(summary.open_alerts));
  const usage = num(summary.budget_amount)
    ? Math.min(100, Math.round((num(summary.budget_reserved) + num(summary.budget_spent)) / num(summary.budget_amount) * 100))
    : 0;
  const [avVal, avUnit] = kMoney(summary.budget_available);
  const period = (summary.active_period && summary.active_period.period_name) || t("當前期間");

  const byState = _mm(() => {
    const g = { active: [], review: [], archived: [] };
    budgets.forEach((b) => g[budgetState(b)].push(b));
    return g;
  }, [budgets]);
  const bList = bScope === "all" ? [...byState.review, ...byState.active, ...byState.archived] : (byState[bScope] || []);
  const pList = pScope === "open" ? openPr : pScope === "arch" ? archPr : purchases;

  const bPrompt = (b) => {
    const no = b.budget_no || b.account_name || "—";
    const cc = b.center_name || "—";
    const acc = b.account_name || "—";
    if (budgetState(b) === "review") {
      return t("預算「{no}」({cc} · {acc})顯示{st},原因:{r}。請核對並完成閉環或結項,先給方案,我確認後執行",
        { no, cc, acc, st: stText(b.ai_status || b.status), r: b.ai_status_reason || "—" });
    }
    return t("分析預算「{no}」({cc} · {acc}):額度 {amt},可用 {av},使用率 {u}%。有無風險?給下一步建議",
      { no, cc, acc, amt: money(num(b.amount), b.currency), av: money(num(b.available), b.currency), u: usageOf(b) });
  };
  const pPrompt = (p) => {
    const no = p.request_no || "—";
    const title = p.title || "—";
    const nx = PR_NEXT[stKey(p.status || "draft")];
    if (nx) {
      return t("採購申請「{no} · {title}」當前狀態「{st}」;金額 {amt},供應商 {sp}。請核對關聯工作流與業務全鏈,下一步按「{nx}」辦理;不得直接改成批准、下單或到貨",
        { no, title, st: stText(p.status || "draft"), nx: t(nx), amt: money(num(p.total_amount), p.currency), sp: p.supplier_name || t("未指定供應商") });
    }
    return t("看看採購申請「{no} · {title}」的情況,給我下一步建議", { no, title });
  };

  const closure = [
    ...unlinkedDocs.map((x, i) => ({
      key: "doc" + (x.id || x.document_no || i),
      icon: "doc", tagTone: "bad", tagText: t("未掛預算"),
      title: x.document_no || t("庫存單據"),
      sub: [x.business_type || x.document_type || t("庫存單據"), x.summary, x.line_count != null ? t("明細 {n} 項", { n: num(x.line_count) }) : ""].filter(Boolean).join(" · "),
      right: <StTag v={x.status}/>,
      prompt: t("把庫存單據「{no}」關聯到合適的可用預算,金額按單據核定;先給我方案,確認後執行", { no: x.document_no || "—" }),
    })),
    ...openRsv.map((r, i) => ({
      key: "rsv" + (r.id || r.reservation_no || i),
      icon: "clock", tagTone: "warn", tagText: t("預算佔用"),
      title: r.source_title || r.note || r.reservation_no || t("預算佔用"),
      sub: [r.reservation_no, r.center_name, r.account_name, SRC[r.source_type] ? t(SRC[r.source_type]) : ""].filter(Boolean).join(" · "),
      right: <span className="row g8"><span className="num" style={{ fontWeight: 700 }}>{money(num(r.amount), r.currency)}</span><StTag v={r.status}/></span>,
      prompt: t("預算佔用「{no}」({title},金額 {amt})該如何閉環?可批准、記支出或釋放;給我建議,確認後執行",
        { no: r.reservation_no || "—", title: r.source_title || r.note || "—", amt: money(num(r.amount), r.currency) }),
    })),
    ...openStk.map((x, i) => ({
      key: "stk" + (x.task_no || i),
      icon: "scan", tagTone: "plain", tagText: t("盤點"),
      title: x.task_name || x.task_no || t("盤點"),
      sub: [x.task_no, x.area || t("全庫"), t("差異 {n} 項", { n: num(x.diff_count) })].filter(Boolean).join(" · "),
      right: <span className="num muted" style={{ fontSize: 12 }}>{num(x.progress)}%</span>,
      prompt: t("盤點任務「{no}」({name})還未閉環,差異 {n} 項;幫我跟進收尾",
        { no: x.task_no || "—", name: x.task_name || "—", n: num(x.diff_count) }),
    })),
  ];

  const rightTh = { textAlign: "right" };

  return (
    <>
      <Folio no="07" en="ERP" title={t("ERP 中樞")}
        sub={t("預算 · 採購 · 閉環 · {p} · 頁面只讀,操作交秘書", { p: period })}
        right={<>
          <B icon="refresh" onClick={() => { setData(null); setTick((k) => k + 1); }}>{t("刷新")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(t("ERP 現在最需要處理什麼?按預算、採購、閉環分類,給我優先級清單"))}>{t("問秘書")}</B>
        </>}/>

      {data === null ? (
        <div className="muted rise" style={{ padding: "42px 0", fontSize: 12.5 }}>{t("讀取 ERP 數據…")}</div>
      ) : (<>
        <div className="kpi-band">
          <Kpi label={t("可用預算")} value={avVal} unit={t(avUnit)} red={num(summary.budget_available) < 0} delay={0}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("總額 {a} · 已用 {u}%", { a: money(num(summary.budget_amount)), u: usage })}</span>}/>
          <Kpi label={t("預算使用率")} value={usage} unit="%" red={usage > 90} delay={.05}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("已佔用 {r} · 已支出 {s}", { r: money(num(summary.budget_reserved)), s: money(num(summary.budget_spent)) })}</span>}/>
          <Kpi label={t("未掛預算單據")} value={unlinkedCount} unit={t("張")} red={unlinkedCount > 0} delay={.1}
            foot={unlinkedCount
              ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把所有未掛預算的庫存單據列出來,逐張關聯到合適的可用預算,先給我方案"))}>{t("讓秘書關聯 →")}</button>
              : <T tone="ok" dot>{t("全部閉環")}</T>}/>
          <Kpi label={t("活躍預警")} value={alertCount} unit={t("條")} red={alertCount > 0} delay={.15}
            foot={alertCount
              ? <button className="tag bad" style={{ cursor: "pointer" }} onClick={() => ask(t("把 ERP 相關的活躍預警列出來,按風險排序給我處置方案"))}>{t("交秘書處置 →")}</button>
              : <T tone="ok" dot>{t("無預警")}</T>}/>
        </div>

        <div className="row g24 wrap rise" style={{ padding: "14px 0", borderBottom: "1px solid var(--hair)", animationDelay: ".05s" }}>
          {[
            [t("成本中心"), num(summary.cost_centers)],
            [t("進行工單"), num(summary.work_tasks_open)],
            [t("進行採購"), num(summary.purchase_open) || openPr.length],
            [t("活躍供應商"), num(summary.suppliers_active)],
            [t("庫存單據"), num(summary.inventory_documents) || docs.length],
          ].map(([k, v]) => (
            <div key={k} className="row g8">
              <span className="label dim">{k}</span>
              <span className="num" style={{ fontWeight: 700, fontSize: 15 }}>{v}</span>
            </div>
          ))}
        </div>

        {/* ═══ 統計圖:資金節奏 / 成本中心 ═══ */}
        <div className="dash-r1">
          <Band no="01" title={t("資金節奏")} sub={t("撥款 / 支出 · 按月") + (hasFlow && flowScale === 1e4 ? " · " + t("萬元") : "")} delay={.08}
            right={hasFlow ? <div className="row g14">
              <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}><span style={{ width: 14, height: 9, background: "var(--ink)", flexShrink: 0 }}/>{t("撥款")}</span>
              <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}><span className="sw-hatch" style={{ width: 14, height: 9, flexShrink: 0 }}/>{t("支出")}</span>
            </div> : null}>
            <div className="dash-gap-r">
              {hasFlow
                ? <MirrorBars labels={fLabels.map(monLabel)} up={fApprS} down={fSpendS} upName={t("撥款")} downName={t("支出")} titleOf={fTitle} h={230}/>
                : <EM icon="chart" title={t("還沒有資金流水")} sub={t("撥款或支出後,月度節奏會出現在這裡。")}/>}
            </div>
          </Band>
          <Band no="02" title={t("成本中心資金")} sub={ccTop.length ? t("按額度 · 前 {n}", { n: ccTop.length }) : t("尚未設置")} delay={.1}>
            <div className="dash-gap-l">
              {ccTop.length ? (<>
                {ccTop.map((c, i) => (
                  <SegRow key={c.id || c.center_code || i} idx={i + 1} name={c.center_name || "—"}
                    spent={c.budget_spent} reserved={c.budget_reserved} amount={c.budget_amount}
                    title={`${c.center_name || "—"} · ${money(num(c.budget_amount))} · ${t("可用")} ${money(num(c.budget_available))}`}
                    onClick={() => ask(t("成本中心「{name}」的預算使用情況怎麼樣?哪裡緊張?", { name: c.center_name || "—" }))}/>
                ))}
                <SegLegend/>
              </>) : <EM icon="building" title={t("還沒有成本中心預算")} sub={t("對秘書說「為◯◯成本中心建立◯◯預算 50000 元」即可開始。")}/>}
            </div>
          </Band>
        </div>

        {/* ═══ 統計圖:預算執行 / 採購管道 ═══ */}
        <div className="dash-r1">
          <Band no="03" title={t("預算執行")} sub={bTop.length ? t("按額度 · 前 {n}", { n: bTop.length }) : t("尚未設置")} delay={.12}>
            <div className="dash-gap-r">
              {bTop.length ? (<>
                {bTop.map((b, i) => (
                  <SegRow key={b.id || b.budget_no || i} idx={i + 1}
                    name={b.center_name || "—"} sub={b.account_name || ""}
                    spent={b.spent} reserved={b.reserved} amount={b.amount}
                    title={`${b.budget_no || "—"} · ${money(num(b.amount), b.currency)} · ${t("可用")} ${money(num(b.available), b.currency)}`}
                    onClick={() => ask(bPrompt(b))}/>
                ))}
                <SegLegend/>
              </>) : <EM icon="wallet" title={t("還沒有預算")} sub={t("對秘書說「為◯◯成本中心建立◯◯預算 50000 元」即可開始。")}/>}
            </div>
          </Band>
          <Band no="04" title={t("採購管道")} sub={t("按流程階段 · 金額與單數")} delay={.14}>
            <div className="dash-gap-l">
              {hasPipe ? pipe.map((x, i) => (
                <HBar key={x.stg} idx={i + 1} name={stText(x.stg)}
                  w={pipeMaxAmt > 0 ? Math.max(x.amount / pipeMaxAmt * 100, x.count ? 2 : 0) : (pipeMaxCnt ? x.count / pipeMaxCnt * 100 : 0)}
                  color={x.count ? "var(--ink)" : "var(--paper-2)"}
                  val={x.amount > 0 ? kMoney(x.amount)[0] + t(kMoney(x.amount)[1]) : "—"}
                  sub={t("{n} 張", { n: x.count })}
                  title={`${stText(x.stg)} · ${t("{n} 張", { n: x.count })} · ${money(x.amount)}`}
                  onClick={() => ask(t("處於「{st}」階段的採購申請有哪些?下一步怎麼推進?", { st: stText(x.stg) }))}/>
              )) : <EM icon="inbound" title={t("還沒有採購申請")} sub={t("對秘書說「採購一批◯◯,預算 5000」即可發起。")}/>}
            </div>
          </Band>
        </div>

        <Band no="05" title={t("預算")}
          sub={t("進行 {a} · 待閉環 {r} · 歸檔 {c}", { a: byState.active.length, r: byState.review.length, c: byState.archived.length })}
          right={
            <div className="seg">
              {[["active", "進行中"], ["review", "待閉環"], ["archived", "已歸檔"], ["all", "全部"]].map(([id, label]) => (
                <button key={id} className={bScope === id ? "on" : ""} onClick={() => setBScope(id)}>{t(label)}</button>
              ))}
            </div>
          } delay={.1}>
          {budgets.length === 0 ? (
            <EM icon="wallet" title={t("還沒有預算")} sub={t("對秘書說「為◯◯成本中心建立◯◯預算 50000 元」即可開始。")}
              action={<B icon="sparkle" onClick={() => ask(t("我要建立一筆預算,請追問成本中心、科目、期間和金額後執行"))}>{t("讓秘書建預算")}</B>}/>
          ) : bList.length === 0 ? (
            <EM icon="search" title={t("當前篩選下沒有預算")}/>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("編號")}</th><th>{t("成本中心 / 科目")}</th><th>{t("期間")}</th>
                  <th style={rightTh}>{t("額度")}</th><th style={rightTh}>{t("可用")}</th>
                  <th>{t("使用率")}</th><th>{t("狀態")}</th><th style={{ width: 96 }}>{t("交給秘書")}</th>
                </tr></thead>
                <tbody>
                  {bList.map((b, i) => {
                    const u = usageOf(b);
                    return (
                      <tr key={(b.id || b.budget_no || i) + ":" + i}>
                        <td>
                          <div className="col g4">
                            <span className="num" style={{ fontWeight: 600 }}>{b.budget_no || "—"}</span>
                            {b.budget_kind === "center" && <span className="mono" style={{ fontSize: 9, letterSpacing: ".12em", color: "var(--ink-3)" }}>{t("預算中心")}</span>}
                          </div>
                        </td>
                        <td>
                          <div className="col g4">
                            <span style={{ fontWeight: 650 }}>{b.center_name || "—"}</span>
                            <span className="muted" style={{ fontSize: 11.5 }}>{b.account_name || "—"}</span>
                          </div>
                        </td>
                        <td className="muted" style={{ fontSize: 12.5 }}>{b.period_name || "—"}</td>
                        <td style={rightTh}><span className="num" style={{ fontWeight: 700 }}>{money(num(b.amount), b.currency)}</span></td>
                        <td style={rightTh}><span className="num" style={{ fontWeight: 700, color: num(b.available) < 0 ? "var(--red)" : undefined }}>{money(num(b.available), b.currency)}</span></td>
                        <td>
                          <div className="row g8">
                            <div className="bar" style={{ width: 64 }}><i style={{ width: u + "%", background: u > 90 ? "var(--red)" : "var(--ink)" }}/></div>
                            <span className="num muted" style={{ fontSize: 11 }}>{u}%</span>
                          </div>
                        </td>
                        <td><StTag v={b.ai_status || b.status}/></td>
                        <td><B size="sm" icon="sparkle" onClick={() => ask(bPrompt(b))}>{t("交秘書")}</B></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Band>

        <Band no="06" title={t("採購申請")}
          sub={t("進行 {o} · 歸檔 {a} · 供應商 {s}", { o: openPr.length, a: archPr.length, s: num(summary.suppliers_active) })}
          right={
            <div className="seg">
              {[["open", "進行中"], ["arch", "已歸檔"], ["all", "全部"]].map(([id, label]) => (
                <button key={id} className={pScope === id ? "on" : ""} onClick={() => setPScope(id)}>{t(label)}</button>
              ))}
            </div>
          } delay={.15}>
          {purchases.length === 0 ? (
            <EM icon="inbound" title={t("還沒有採購申請")} sub={t("對秘書說「採購一批◯◯,預算 5000」即可發起。")}
              action={<B icon="sparkle" onClick={() => ask(t("我要發起一筆採購申請:請追問物資、數量、預算、供應商和適用採購流程;建立真實 ERP 主單後必須同步綁定並啟動該工作流,不得建立孤立流程或直接批准"))}>{t("讓秘書發起採購")}</B>}/>
          ) : pList.length === 0 ? (
            <EM icon="search" title={t("當前篩選下沒有採購申請")}/>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("申請號")}</th><th>{t("標題 / 明細")}</th><th>{t("供應商")}</th>
                  <th style={rightTh}>{t("金額")}</th><th>{t("狀態")}</th><th style={{ width: 190 }}>{t("業務全鏈")}</th>
                </tr></thead>
                <tbody>
                  {pList.map((p, i) => {
                    const entityRef = purchaseEntityRef(p);
                    return (
                    <tr key={(p.id || p.request_no || i) + ":" + i} style={{ cursor: entityRef ? "pointer" : undefined }}
                      onClick={() => entityRef && W2.openEntity(entityRef, { tab: "overview" })}>
                      <td><span className="num" style={{ fontWeight: 600 }}>{p.request_no || "—"}</span></td>
                      <td>
                        <div className="col g4" style={{ minWidth: 0 }}>
                          <span className="row g8" style={{ fontWeight: 650 }}>
                            {p.priority === "urgent" && <I name="flame" size={12} color="var(--red)"/>}
                            {p.title || "—"}
                            {p.priority === "urgent" && <T tone="bad">{t("緊急")}</T>}
                          </span>
                          <span className="muted" style={{ fontSize: 11.5 }}>{linePreview(p)}</span>
                        </div>
                      </td>
                      <td className="muted" style={{ fontSize: 12.5 }}>{p.supplier_name || t("未指定供應商")}</td>
                      <td style={rightTh}><span className="num" style={{ fontWeight: 700 }}>{money(num(p.total_amount), p.currency)}</span></td>
                      <td><StTag v={p.status || "draft"}/></td>
                      <td onClick={(event) => event.stopPropagation()}>
                        <div className="row g4 wrap">
                          {entityRef && <B size="sm" icon="layers" onClick={() => W2.openEntity(entityRef, { tab: "overview" })}>{t("查看全鏈")}</B>}
                          <B size="sm" icon="sparkle" onClick={() => ask(pPrompt(p))}>{t("交秘書")}</B>
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Band>

        <Band no="07" title={t("未閉環事項")}
          sub={closure.length ? t("{n} 項待處理", { n: closure.length }) : t("全部閉環")}
          right={closure.length
            ? <B size="sm" icon="sparkle" onClick={() => ask(t("把 ERP 未閉環事項(未掛預算單據、預算佔用、進行中盤點)逐項給我處置方案,我確認後執行"))}>{t("一鍵全部交秘書")}</B>
            : null} delay={.2}>
          {closure.length === 0 ? (
            <EM icon="checkCircle" title={t("沒有未閉環事項")} sub={t("佔用、單據與盤點全部閉環。秘書持續盯守,有異常會出現在這裡。")}/>
          ) : (
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {closure.map((c, i) => (
                <div key={c.key} className="ledger-row">
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <I name={c.icon} size={15} color="var(--ink-3)"/>
                  <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                    <span className="row g8 wrap" style={{ fontWeight: 650, fontSize: 13.5 }}>{c.title}<T tone={c.tagTone}>{c.tagText}</T></span>
                    {c.sub && <span className="muted num" style={{ fontSize: 11.5 }}>{c.sub}</span>}
                  </div>
                  <div className="row g10">{c.right}</div>
                  <B size="sm" icon="sparkle" onClick={() => ask(c.prompt)}>{t("交秘書")}</B>
                </div>
              ))}
            </div>
          )}
        </Band>
      </>)}
    </>
  );
};

window.W2.PAGES["erp"] = Page;
})();
