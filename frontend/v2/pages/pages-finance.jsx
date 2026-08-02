/* WAREHOUSE 2.1 · 財務 — Swiss 版式,真後端
   複式總賬駕駛艙(只讀):利潤表 / 資產負債表 / 現金流量表 / AP·AR 賬齡 / 記賬憑證
   一切動賬 = 交給財務秘書;借貸平衡由後端 GL 引擎保證 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "財務": "Finance", "問秘書": "Ask Secretary", "交給秘書": "Secretary",
  "2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.1 contract: pages are read-only; changes run through the Secretary with full audit.",
  "複式總賬即時推算 · 頁面只讀,動賬交秘書,借貸平衡由後端保證": "Computed live from the double-entry ledger · read-only page, postings via Secretary, balance guaranteed by the backend",
  "本期財務怎麼樣?利潤、現金、應收應付撿重點講,有風險直接說。": "How are the finances this period? Hit the highlights — profit, cash, AR/AP — and flag any risk directly.",
  "月末結賬": "Close period",
  "幫我做 {p} 的期末結賬結轉損益(用 fin close);結賬會鎖定期間,執行前先跟我確認。": "Run the {p} period close and transfer P&L (fin close); closing locks the period, confirm with me before executing.",
  "本月": "Month", "本季": "Quarter", "本年": "Year",
  "動賬交秘書": "Post via Secretary",
  "補錄流水": "Backfill entry",
  "幫我補錄一筆賬:先問我是收款、非採購開銷還是其他事項;若是付供應商,不得用通用補錄,必須改為選擇已完成採購工作流、已收貨且有未結應付的正式 PO ID,再確認本次付款金額。": "Backfill an entry: first ask whether it is a receipt, a non-procurement expense or another event. Supplier payments must never use generic backfill; instead select a formal PO whose procurement workflow is complete, which has been received and has an open payable, then confirm the payment amount.",
  "收客戶款": "Record receipt",
  "幫我記一筆收款:收到客戶 ___ ¥___(用 fin receive),請追問客戶和金額後執行。": "Record a receipt: customer ___ paid ¥___ (fin receive); ask me for the customer and amount, then execute.",
  "付供應商款": "Record payment",
  "幫我支付供應商款:請先列出已完成採購工作流、已收貨且有未結應付的正式 PO,讓我選擇 PO ID 和本次付款金額;只能使用 fin pay --purchase-order,供應商、幣別和應付均由 PO 權威帶入。": "Pay a supplier: first list formal POs whose procurement workflow is complete, which have been received and have an open payable. Let me select the PO ID and this payment amount. Use only fin pay --purchase-order; supplier, currency and payable are authoritative from the PO.",
  "採購收貨轉固定資產": "Capitalise purchase receipt",
  "把已完成採購工作流並綁定正式 PO 的已確認入庫單 ID ___ 轉為固定資產:請追問資產名稱和折舊月數後使用 fin asset add --inventory-document;原值、供應商和幣別只能從入庫單與 PO 帶入。": "Capitalise confirmed inbound document ID ___ that is bound to a formal PO and completed procurement workflow. Ask for the asset name and depreciation months, then use fin asset add --inventory-document; original cost, supplier and currency must come only from the receipt and PO.",
  "記 AA 開銷": "AA expense",
  "幫我記一筆 AA 共享開銷:墊付人、金額、項目、怎麼分攤,逐項追問我(用 fin expense)。": "Record a shared AA expense: ask me one by one for the payer, amount, item and how to split it (fin expense).",
  "本期利潤": "Profit · period", "現金及銀行": "Cash & bank", "應收未收": "AR outstanding", "應付未付": "AP outstanding",
  "元": "CNY", "萬元": "×10⁴ CNY", "億元": "×10⁸ CNY",
  "收入 {v}": "Revenue {v}",
  "本期淨流 {v}": "Net cash {v}",
  "{n} 個客戶": "{n} customers", "{n} 個供應商": "{n} suppliers",
  "讓秘書催收 →": "Chase via Secretary →",
  "把應收賬款按賬齡列出來,幫我催收拖得最久的那幾筆,起草催款話術。": "List receivables by age and help me chase the oldest ones — draft the reminder message.",
  "總賬還是空的——這正常,不是沒同步。": "The ledger is still empty — that is normal, not a sync problem.",
  "總賬是事件驅動的:只在新發生的採購、銷售、收付款時自動記賬,不會倒灌歷史庫存。做一次期初建賬,財務就和現有家底對上;物資要有單價才有價值。": "The ledger is event-driven: it posts automatically only on new purchases, sales and payments — it never back-fills historical stock. Run an opening-balance setup once and the books will match what you own; items need a unit price to carry value.",
  "讓秘書期初建賬": "Opening balances via Secretary",
  "幫我做期初建賬,把現有庫存價值計入總賬(用 fin init-balances);期初現金和銀行金額你來追問我。": "Set up opening balances and post current inventory value to the ledger (fin init-balances); ask me for the opening cash and bank amounts.",
  "三大報表": "Financial statements",
  "口徑:{p} · 即時從總賬推算": "Basis: {p} · computed live from the ledger",
  "讓秘書解讀": "Explain via Secretary",
  "把本期利潤表、資產負債表、現金流量表用大白話講一遍,指出異常和風險。": "Walk me through this period's P&L, balance sheet and cash flow in plain words, and point out anomalies and risks.",
  "利潤表": "Profit & loss", "資產負債表": "Balance sheet", "現金流量表": "Cash flow",
  "營業收入": "Revenue", "營業成本": "Cost of sales", "費用": "Expenses", "淨利潤": "Net profit",
  "資產合計": "Total assets", "負債合計": "Total liabilities", "本年利潤": "Current-year profit", "權益合計": "Total equity",
  "現金流入": "Cash in", "現金流出": "Cash out", "淨增加": "Net change",
  "平衡": "Balanced", "不平衡": "Unbalanced",
  "截至 {d}": "As of {d}",
  "往來對賬": "Receivables & payables",
  "賬齡分桶 0-30 / 31-60 / 61-90 / >90 天": "Aging buckets 0-30 / 31-60 / 61-90 / >90 days",
  "讓秘書對賬": "Reconcile via Secretary",
  "把應收應付逐個往來方對一遍賬,列出賬齡最久的幾筆,給出催收和付款建議。": "Reconcile AR and AP party by party, list the oldest open items, and recommend chasing and payment actions.",
  "應收賬款 · 客戶欠我": "AR · owed by customers",
  "應付賬款 · 我欠供應商": "AP · owed to suppliers",
  "多幣別": "Multi-currency",
  "天": "d",
  "暫無未結往來": "No open items",
  "讓秘書催收": "Chase payment", "安排付款": "Schedule payment",
  "客戶「{p}」還欠 {amt}:幫我催收,起草催款話術並登記跟進;若款已到就記收款核銷(fin receive)。": "Customer \"{p}\" still owes {amt}: help me chase it — draft a reminder and log the follow-up; if the money arrived, record the receipt and settle it (fin receive).",
  "還欠供應商「{p}」{amt}:請列出該供應商已完成採購工作流、已收貨且未結清的正式 PO,讓我選 PO ID 與本次金額;只能用 fin pay --purchase-order 核銷,不得按供應商自由入賬。": "We still owe supplier \"{p}\" {amt}. List that supplier's formal POs whose procurement workflow is complete, which have been received and remain unsettled; let me choose the PO ID and payment amount. Settle only via fin pay --purchase-order, never by free-form supplier posting.",
  "記賬憑證": "Vouchers",
  "最近 {n} 張 · 業務發生自動生成,每張借貸平衡": "Latest {n} · auto-generated from business events, each one balanced",
  "憑證號": "Voucher no.", "日期": "Date", "摘要": "Summary", "分錄": "Entries", "金額": "Amount",
  "來源業務": "Source business", "回到來源": "Open source",
  "借": "DR", "貸": "CR",
  "暫無憑證": "No vouchers yet",
  "載入失敗": "Load failed", "重新載入": "Reload",
  "財務資料讀取中…": "Loading financial data…",
  "財務資料暫時無法載入，未顯示為零或空賬。": "Financial data is temporarily unavailable. It is not being shown as zero or an empty ledger.",
  "以下資料載入失敗：{items}": "The following data failed to load: {items}",
  "伺服器返回的憑證格式不正確。": "The server returned an invalid voucher response.",
  "伺服器返回的財務事件格式不正確。": "The server returned an invalid finance event response.",
  "待處理財務事件": "Pending finance events", "待補資料": "Needs information", "待確認過賬": "Ready for posting confirmation",
  "另有 {n} 筆待處理事件未顯示，請交由秘書繼續處理。": "{n} more pending events are not shown; ask the Secretary to continue processing them.",
  "AI 已錄入但尚未進入總賬的事件 · 前端只讀，交由秘書補齊或確認後過賬": "Events recorded by AI but not yet posted to the general ledger · this page is read-only; ask the Secretary to complete or confirm them",
  "事件號": "Event no.", "用途": "Purpose", "狀態": "Status", "交秘書處理": "Ask Secretary",
  "請處理財務事件 {no}（ID {id}，目前狀態 {status}）：先核對並補齊缺失資料；資料完整後向我複述過賬預覽並取得明確確認，才可使用 fin event post --id {id} 過賬。不要另建重複事件。": "Handle finance event {no} (ID {id}, current status {status}): first verify and complete any missing information; once complete, repeat the posting preview and obtain my explicit confirmation before using fin event post --id {id}. Do not create a duplicate event.",
  "出入庫、採購、銷售、收付款發生後會自動生成憑證;歷史賬讓秘書補錄即可。": "Vouchers are generated automatically after stock moves, purchases, sales and payments; ask the Secretary to backfill history.",
  "補錄一筆": "Backfill one",
  "解釋憑證 {no}({s}):這筆賬怎麼來的?借貸分錄逐條講給我聽。": "Explain voucher {no} ({s}): where did this posting come from? Walk me through each debit/credit line.",
  "問這張": "Explain",
});

const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);
const voucherSourceEntityRef = (voucher) => {
  const suppliedValue = voucher && voucher.source_entity_ref;
  if (suppliedValue != null && suppliedValue !== "") {
    const supplied = W2.parseEntityRef && W2.parseEntityRef(suppliedValue);
    return supplied && W2.isBusinessEntityRef(supplied.entity_ref) ? supplied.entity_ref : "";
  }
  const sourceId = Number(voucher && voucher.source_id);
  const typeMap = {
    purchase_request: "erp_purchase_request",
    erp_purchase_request: "erp_purchase_request",
    wf_instance: "wf_instance",
  };
  const type = typeMap[String(voucher && voucher.source_type || "")];
  const ref = type && Number.isInteger(sourceId) && sourceId > 0 ? W2.entityRef(type, sourceId) : "";
  return W2.isBusinessEntityRef(ref) ? ref : "";
};

/* 金額:全額(表格)與巨數縮寫(KPI 帶) */
const money = (v) => {
  const n = Number(v);
  return "¥" + (Number.isFinite(n) ? n : 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const moneyIn = (v, currency) => {
  const c = String(currency || "CNY").toUpperCase();
  const n = Number(v);
  return c === "CNY" ? money(n) : c + " " + (Number.isFinite(n) ? n : 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};
const currencyTotals = (d) => Object.entries((d && d.totals_by_currency) || {})
  .filter(([, value]) => Number.isFinite(Number(value)))
  .sort(([a], [b]) => a.localeCompare(b));
const currencyTotalsText = (d) => {
  const entries = currencyTotals(d);
  return entries.length ? entries.map(([currency, value]) => moneyIn(value, currency)).join(" · ") : money(d && d.total_outstanding);
};
const kAmt = (v) => {
  const n = Number(v) || 0, a = Math.abs(n);
  if (a >= 1e8) return [(n / 1e8).toFixed(2), t("億元")];
  if (a >= 1e5) return [(n / 1e4).toFixed(1), t("萬元")];
  return [n.toLocaleString("zh-CN", { maximumFractionDigits: 0 }), t("元")];
};
const periodsOf = () => {
  const d = new Date(), y = d.getFullYear(), m = d.getMonth() + 1, q = Math.floor((m - 1) / 3) + 1;
  return [
    { id: y + "-" + pad2(m), label: "本月" },
    { id: y + "-Q" + q, label: "本季" },
    { id: String(y), label: "本年" },
  ];
};

/* 報表行:年報式髮絲行,合計行加粗頂線 */
const SRow = ({ k, v, strong, tone, dim }) => (
  <div className="row spread" style={{ padding: "9px 2px", gap: 12, borderTop: strong ? "2px solid var(--rule)" : "1px solid var(--hair-soft)" }}>
    <span style={{ fontSize: 12.5, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      fontWeight: strong ? 700 : 500, color: dim ? "var(--ink-3)" : strong ? "var(--ink)" : "var(--ink-2)", paddingLeft: dim ? 12 : 0 }}>{k}</span>
    <span className="num" style={{ flexShrink: 0, fontSize: strong ? 15 : 12.5, fontWeight: strong ? 700 : 550,
      color: tone || (dim ? "var(--ink-3)" : "var(--ink)") }}>{v}</span>
  </div>
);
const Stmt = ({ title, meta, tag, rows }) => (
  <div className="col" style={{ minWidth: 0 }}>
    <div className="row spread" style={{ paddingBottom: 10, borderBottom: "2px solid var(--rule)", gap: 10 }}>
      <LB>{title}</LB>
      <span className="row g8">{tag}{meta && <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".08em" }}>{meta}</span>}</span>
    </div>
    <div className="col">{rows.map((r, i) => <SRow key={i} {...r}/>)}</div>
  </div>
);
const LoadFailure = ({ detail, onRetry }) => (
  <div style={{ minWidth: 0 }} role="alert">
    <EM icon="alert" title={t("載入失敗")}
      sub={detail || t("財務資料暫時無法載入，未顯示為零或空賬。")}
      action={<B size="sm" icon="refresh" onClick={onRetry}>{t("重新載入")}</B>}/>
  </div>
);
const LoadPending = () => (
  <div className="muted row g8" aria-busy="true" style={{ minHeight: 84, alignItems: "center", justifyContent: "center" }}>
    <I name="clock" size={15}/><span style={{ fontSize: 12.5 }}>{t("財務資料讀取中…")}</span>
  </div>
);

/* 往來方塊:合計 + 賬齡桶 + 各往來方(每行交秘書追賬) */
const PartyBlock = ({ title, data, isAR }) => {
  const d = data || {};
  const parties = Array.isArray(d.by_party) ? d.by_party : [];
  const aging = d.aging || {};
  const totals = currencyTotals(d);
  const agingByCurrency = d.aging_by_currency || {};
  const agingValues = (bucket) => {
    const values = Object.entries(agingByCurrency)
      .map(([currency, buckets]) => [currency, num(buckets && buckets[bucket])])
      .filter(([, value]) => value > 0);
    if (values.length) return values.map(([currency, value]) => moneyIn(value, currency)).join(" · ");
    return moneyIn(aging[bucket], d.currency || "CNY");
  };
  const anyAging = (bucket) => Object.values(agingByCurrency).some(buckets => num(buckets && buckets[bucket]) > 0) || num(aging[bucket]) > 0;
  return (
    <div className="col g12" style={{ minWidth: 0 }}>
      <div className="row spread" style={{ paddingBottom: 10, borderBottom: "2px solid var(--rule)", gap: 10 }}>
        <LB>{title}</LB>
        <span className="col g2" style={{ alignItems: "flex-end" }}>
          {(totals.length ? totals : [[d.currency || "CNY", d.total_outstanding || 0]]).map(([currency, value]) => (
            <span key={currency} className="num" style={{ fontSize: 14, fontWeight: 700, color: num(value) > 0 ? "var(--ink)" : "var(--ink-3)" }}>
              {moneyIn(value, currency)}
            </span>
          ))}
        </span>
      </div>
      <div className="row g6 wrap">
        {["0-30", "31-60", "61-90", ">90"].map(k => (
          <span key={k} className="chip" style={{ cursor: "default", color: anyAging(k) ? "var(--ink)" : "var(--ink-4)" }}>
            <span className="mono" style={{ fontSize: 10, letterSpacing: ".06em" }}>{k}{t("天")}</span>
            <b className="num" style={{ fontSize: 11.5 }}>{agingValues(k)}</b>
          </span>
        ))}
      </div>
      {parties.length ? (
        <div style={{ borderTop: "1px solid var(--hair)" }}>
          {parties.slice(0, 6).map((p, i) => (
            <div key={(p.party || "p") + i} className="ledger-row" style={{ gap: 12 }}>
              <span className="lr-idx">{pad2(i + 1)}</span>
              <span style={{ flex: 1, minWidth: 0, fontWeight: 650, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p.party || "—"}</span>
              <span className="num" style={{ fontWeight: 700, fontSize: 14 }}>{moneyIn(p.outstanding, p.currency)}</span>
              <B size="sm" icon="sparkle" onClick={() => ask(isAR
                ? t("客戶「{p}」還欠 {amt}:幫我催收,起草催款話術並登記跟進;若款已到就記收款核銷(fin receive)。", { p: p.party || "—", amt: moneyIn(p.outstanding, p.currency) })
                : t("還欠供應商「{p}」{amt}:請列出該供應商已完成採購工作流、已收貨且未結清的正式 PO,讓我選 PO ID 與本次金額;只能用 fin pay --purchase-order 核銷,不得按供應商自由入賬。", { p: p.party || "—", amt: moneyIn(p.outstanding, p.currency) }))}>
                {isAR ? t("讓秘書催收") : t("安排付款")}
              </B>
            </div>
          ))}
        </div>
      ) : <div className="muted" style={{ fontSize: 12.5, padding: "16px 2px", borderTop: "1px solid var(--hair)" }}>{t("暫無未結往來")}</div>}
    </div>
  );
};

const Page = ({ boot }) => {
  const periods = _mm(() => periodsOf(), []);
  const [period, setPeriod] = _s(periods[0].id);
  const [incD, setIncD] = _s(null);
  const [cfD, setCfD] = _s(null);
  const [bsD, setBsD] = _s(null);
  const [apD, setApD] = _s(null);
  const [arD, setArD] = _s(null);
  const [vs, setVs] = _s(null);
  const [eventRows, setEventRows] = _s(null);
  const [eventTotal, setEventTotal] = _s(0);
  const [loadErrors, setLoadErrors] = _s({});
  const [reloadNo, setReloadNo] = _s(0);

  const errorMessage = (e) => (e && e.message) || t("財務資料暫時無法載入，未顯示為零或空賬。");
  const requireObject = (d, label) => {
    if (!d || typeof d !== "object" || Array.isArray(d)) throw new Error(label);
    return d;
  };
  const clearErrors = (keys) => setLoadErrors(prev => {
    const next = { ...prev };
    keys.forEach(key => delete next[key]);
    return next;
  });
  const saveError = (key, e) => setLoadErrors(prev => ({ ...prev, [key]: errorMessage(e) }));
  const reload = () => setReloadNo(n => n + 1);

  _e(() => {
    let on = true;
    setIncD(null);
    setCfD(null);
    clearErrors(["income", "cashflow"]);
    W2.json("/api/erp/gl/income?period=" + encodeURIComponent(period))
      .then(d => on && setIncD(requireObject(d, t("利潤表") + " · " + t("載入失敗"))))
      .catch(e => on && saveError("income", e));
    W2.json("/api/erp/gl/cashflow?period=" + encodeURIComponent(period))
      .then(d => on && setCfD(requireObject(d, t("現金流量表") + " · " + t("載入失敗"))))
      .catch(e => on && saveError("cashflow", e));
    return () => { on = false; };
  }, [period, reloadNo]);
  _e(() => {
    let on = true;
    setBsD(null);
    setApD(null);
    setArD(null);
    setVs(null);
    setEventRows(null);
    setEventTotal(0);
    clearErrors(["balanceSheet", "ap", "ar", "vouchers", "events"]);
    W2.json("/api/erp/gl/balance-sheet")
      .then(d => on && setBsD(requireObject(d, t("資產負債表") + " · " + t("載入失敗"))))
      .catch(e => on && saveError("balanceSheet", e));
    W2.json("/api/erp/gl/ap")
      .then(d => {
        const value = requireObject(d, t("應付賬款 · 我欠供應商") + " · " + t("載入失敗"));
        if (!Array.isArray(value.items) || !Array.isArray(value.by_party)) throw new Error(t("應付賬款 · 我欠供應商") + " · " + t("載入失敗"));
        if (on) setApD(value);
      })
      .catch(e => on && saveError("ap", e));
    W2.json("/api/erp/gl/ar")
      .then(d => {
        const value = requireObject(d, t("應收賬款 · 客戶欠我") + " · " + t("載入失敗"));
        if (!Array.isArray(value.items) || !Array.isArray(value.by_party)) throw new Error(t("應收賬款 · 客戶欠我") + " · " + t("載入失敗"));
        if (on) setArD(value);
      })
      .catch(e => on && saveError("ar", e));
    W2.json("/api/erp/gl/vouchers?limit=30")
      .then(d => {
        if (!on) return;
        if (!d || !Array.isArray(d.vouchers)) throw new Error(t("伺服器返回的憑證格式不正確。"));
        setVs(d.vouchers);
      })
      .catch(e => on && saveError("vouchers", e));
    W2.json("/api/erp/finance/events?statuses=draft%2Cneeds_clarification%2Cready&ledger_scope=company&unposted=true&limit=50")
      .then(d => {
        if (!on) return;
        if (!d || !Array.isArray(d.events)) throw new Error(t("伺服器返回的財務事件格式不正確。"));
        setEventRows(d.events);
        setEventTotal(Number.isFinite(Number(d.total)) ? Number(d.total) : d.events.length);
      })
      .catch(e => on && saveError("events", e));
    return () => { on = false; };
  }, [reloadNo]);

  const inc = incD || {}, cf = cfD || {}, bs = bsD || {}, ap = apD || {}, ar = arD || {};
  const vouchers = Array.isArray(vs) ? vs : [];
  const pLabel = t((periods.find(x => x.id === period) || periods[0]).label);
  const cashTotal = (Array.isArray(bs.asset_lines) ? bs.asset_lines : [])
    .filter(l => l && (l.code === "1001" || l.code === "1002"))
    .reduce((a, l) => a + num(l.amount), 0);
  const arCurrencyTotals = currencyTotals(ar), apCurrencyTotals = currencyTotals(ap);
  const arMixed = arCurrencyTotals.length > 1, apMixed = apCurrencyTotals.length > 1;
  const arCurrency = arCurrencyTotals.length === 1 ? arCurrencyTotals[0][0] : (ar.currency || "CNY");
  const apCurrency = apCurrencyTotals.length === 1 ? apCurrencyTotals[0][0] : (ap.currency || "CNY");
  const arTotal = arCurrencyTotals.length === 1 ? num(arCurrencyTotals[0][1]) : num(ar.total_outstanding);
  const apTotal = apCurrencyTotals.length === 1 ? num(apCurrencyTotals[0][1]) : num(ap.total_outstanding);
  const arAnyOutstanding = arCurrencyTotals.length ? arCurrencyTotals.some(([, value]) => num(value) > 0) : arTotal > 0;
  const apAnyOutstanding = apCurrencyTotals.length ? apCurrencyTotals.some(([, value]) => num(value) > 0) : apTotal > 0;
  const [profitV, profitU] = kAmt(inc.profit);
  const [cashV, cashU] = kAmt(cashTotal);
  const [arV, arU] = arMixed ? [t("多幣別"), ""] : arCurrency === "CNY"
    ? kAmt(arTotal) : [arTotal.toLocaleString("zh-CN", { maximumFractionDigits: 2 }), arCurrency];
  const [apV, apU] = apMixed ? [t("多幣別"), ""] : apCurrency === "CNY"
    ? kAmt(apTotal) : [apTotal.toLocaleString("zh-CN", { maximumFractionDigits: 2 }), apCurrency];
  const ledgerEmpty = !loadErrors.vouchers && vs !== null && vouchers.length === 0;
  const loadLabels = {
    income: t("利潤表"), cashflow: t("現金流量表"), balanceSheet: t("資產負債表"),
    ap: t("應付賬款 · 我欠供應商"), ar: t("應收賬款 · 客戶欠我"), vouchers: t("記賬憑證"),
    events: t("待處理財務事件"),
  };
  const failedLoads = Object.keys(loadErrors).filter(key => loadErrors[key]);
  const cashFailed = loadErrors.balanceSheet || loadErrors.cashflow;
  const incomeLoading = incD === null && !loadErrors.income;
  const cashLoading = (bsD === null || cfD === null) && !cashFailed;
  const arLoading = arD === null && !loadErrors.ar;
  const apLoading = apD === null && !loadErrors.ap;
  const vouchersLoading = vs === null && !loadErrors.vouchers;
  const eventsLoading = eventRows === null && !loadErrors.events;
  const pendingEvents = (Array.isArray(eventRows) ? eventRows : []).filter(e =>
    e && (!e.ledger_scope || e.ledger_scope === "company") && !e.voucher_id
      && ["draft", "needs_clarification", "ready"].includes(e.status));

  const backfillPrompt = () => W2.openBusinessAction("fin_event_draft");
  const quick = [
    ["補錄流水", "幫我補錄一筆賬:先問我是收款、非採購開銷還是其他事項;若是付供應商,不得用通用補錄,必須改為選擇已完成採購工作流、已收貨且有未結應付的正式 PO ID,再確認本次付款金額。"],
    ["收客戶款", "幫我記一筆收款:收到客戶 ___ ¥___(用 fin receive),請追問客戶和金額後執行。"],
    ["付供應商款", "幫我支付供應商款:請先列出已完成採購工作流、已收貨且有未結應付的正式 PO,讓我選擇 PO ID 和本次付款金額;只能使用 fin pay --purchase-order,供應商、幣別和應付均由 PO 權威帶入。"],
    ["採購收貨轉固定資產", "把已完成採購工作流並綁定正式 PO 的已確認入庫單 ID ___ 轉為固定資產:請追問資產名稱和折舊月數後使用 fin asset add --inventory-document;原值、供應商和幣別只能從入庫單與 PO 帶入。"],
    ["記 AA 開銷", "幫我記一筆 AA 共享開銷:墊付人、金額、項目、怎麼分攤,逐項追問我(用 fin expense)。"],
  ];

  /* 三大報表行(全部字段防禦性取值) */
  const plRows = [
    { k: t("營業收入"), v: money(inc.revenue) },
    { k: t("營業成本"), v: "− " + money(inc.cost) },
    { k: t("費用"), v: "− " + money(inc.expense) },
    ...(Array.isArray(inc.lines) ? inc.lines.slice(0, 4).map(l => ({ k: ((l && l.code) ? l.code + " " : "") + ((l && l.name) || "—"), v: money(l && l.amount), dim: true })) : []),
    { k: t("淨利潤"), v: money(inc.profit), strong: true, tone: num(inc.profit) < 0 ? "var(--red)" : "var(--ink)" },
  ];
  const bsRows = [
    { k: t("資產合計"), v: money(bs.assets) },
    ...(Array.isArray(bs.asset_lines) ? bs.asset_lines.slice(0, 3).map(l => ({ k: ((l && l.code) ? l.code + " " : "") + ((l && l.name) || "—"), v: money(l && l.amount), dim: true })) : []),
    { k: t("負債合計"), v: money(bs.liabilities) },
    { k: t("本年利潤"), v: money(bs.current_profit), dim: true },
    { k: t("權益合計"), v: money(bs.total_equity), strong: true },
  ];
  const cfRows = [
    { k: t("現金流入"), v: money(cf.inflow), tone: num(cf.inflow) > 0 ? "var(--ok)" : undefined },
    { k: t("現金流出"), v: "− " + money(cf.outflow), tone: num(cf.outflow) > 0 ? "var(--red)" : undefined },
    ...(Array.isArray(cf.accounts) ? cf.accounts.slice(0, 3).map(a => ({ k: ((a && a.code) ? a.code + " " : "") + ((a && a.name) || "—"), v: money(a && a.net), dim: true })) : []),
    { k: t("淨增加"), v: money(cf.net_change), strong: true, tone: num(cf.net_change) < 0 ? "var(--red)" : "var(--ink)" },
  ];
  const shown = vouchers.slice(0, 12);

  return (<>
    <Folio no="08" en="FINANCE" title={t("財務")}
      sub={t("複式總賬即時推算 · 頁面只讀,動賬交秘書,借貸平衡由後端保證")}
      right={<>
        <B icon="check" onClick={() => ask(t("幫我做 {p} 的期末結賬結轉損益(用 fin close);結賬會鎖定期間,執行前先跟我確認。", { p: period }))}>{t("月末結賬")}</B>
        <B kind="primary" icon="sparkle" onClick={() => ask(t("本期財務怎麼樣?利潤、現金、應收應付撿重點講,有風險直接說。"))}>{t("問秘書")}</B>
      </>}/>

    {/* 期間 + 動賬快捷指令(全部交秘書) */}
    <div className="row g14 wrap rise" style={{ padding: "18px 0 16px", borderBottom: "1px solid var(--hair)", animationDelay: ".05s" }}>
      <div className="seg">
        {periods.map(p => <button key={p.id} className={period === p.id ? "on" : ""} onClick={() => setPeriod(p.id)}>{t(p.label)}</button>)}
      </div>
      <span style={{ width: 1, height: 22, background: "var(--hair)" }}/>
      <LB dim>{t("動賬交秘書")}</LB>
      <div className="row g6 wrap">
        {quick.map(([label, prompt]) => (
          <button key={label} className="chip" onClick={() => ask(t(prompt))}><I name="sparkle" size={11}/>{t(label)}</button>
        ))}
      </div>
    </div>

    {failedLoads.length > 0 && (
      <div className="row spread wrap rise" role="alert" style={{ marginTop: 18, padding: "14px 16px", gap: 14,
        border: "1px solid var(--red)", background: "var(--white)" }}>
        <div className="col g4" style={{ minWidth: 240 }}>
          <LB red>{t("載入失敗")}</LB>
          <span style={{ fontSize: 13, fontWeight: 650 }}>
            {t("以下資料載入失敗：{items}", { items: failedLoads.map(key => loadLabels[key] || key).join("、") })}
          </span>
          <span className="muted" style={{ fontSize: 11.5 }}>{t("財務資料暫時無法載入，未顯示為零或空賬。")}</span>
        </div>
        <B icon="refresh" onClick={reload}>{t("重新載入")}</B>
      </div>
    )}

    {/* KPI 帶:巨型數字 */}
    <div className="kpi-band">
      <Kpi label={t("本期利潤")} value={incomeLoading ? "…" : loadErrors.income ? "—" : profitV} unit={(incomeLoading || loadErrors.income) ? "" : profitU}
        red={!loadErrors.income && num(inc.profit) < 0} delay={0}
        foot={incomeLoading ? <span className="muted" style={{ fontSize: 11.5 }}>{t("財務資料讀取中…")}</span>
          : loadErrors.income ? <span className="muted" style={{ fontSize: 11.5 }}>{t("載入失敗")}</span>
          : <><span className="muted" style={{ fontSize: 11.5 }}>{t("收入 {v}", { v: money(inc.revenue) })}</span><T tone="plain">{pLabel}</T></>}/>
      <Kpi label={t("現金及銀行")} value={cashLoading ? "…" : cashFailed ? "—" : cashV} unit={(cashLoading || cashFailed) ? "" : cashU} delay={.05}
        foot={cashLoading ? <span className="muted" style={{ fontSize: 11.5 }}>{t("財務資料讀取中…")}</span>
          : cashFailed ? <span className="muted" style={{ fontSize: 11.5 }}>{t("載入失敗")}</span>
          : <span className="muted num" style={{ fontSize: 11.5, color: num(cf.net_change) < 0 ? "var(--red)" : undefined }}>{t("本期淨流 {v}", { v: money(cf.net_change) })}</span>}/>
      <Kpi label={t("應收未收")} value={arLoading ? "…" : loadErrors.ar ? "—" : arV} unit={(arLoading || loadErrors.ar) ? "" : arU}
        red={!loadErrors.ar && arAnyOutstanding} delay={.1}
        foot={arLoading ? <span className="muted" style={{ fontSize: 11.5 }}>{t("財務資料讀取中…")}</span>
          : loadErrors.ar ? <span className="muted" style={{ fontSize: 11.5 }}>{t("載入失敗")}</span> : arMixed
          ? <span className="muted num" style={{ fontSize: 11 }}>{currencyTotalsText(ar)}</span> : arAnyOutstanding
          ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把應收賬款按賬齡列出來,幫我催收拖得最久的那幾筆,起草催款話術。"))}>{t("讓秘書催收 →")}</button>
          : <span className="muted" style={{ fontSize: 11.5 }}>{t("{n} 個客戶", { n: (Array.isArray(ar.by_party) ? ar.by_party : []).length })}</span>}/>
      <Kpi label={t("應付未付")} value={apLoading ? "…" : loadErrors.ap ? "—" : apV} unit={(apLoading || loadErrors.ap) ? "" : apU} delay={.15}
        foot={apLoading ? <span className="muted" style={{ fontSize: 11.5 }}>{t("財務資料讀取中…")}</span>
          : loadErrors.ap ? <span className="muted" style={{ fontSize: 11.5 }}>{t("載入失敗")}</span>
          : apMixed ? <span className="muted num" style={{ fontSize: 11 }}>{currencyTotalsText(ap)}</span>
          : <span className="muted" style={{ fontSize: 11.5 }}>{t("{n} 個供應商", { n: (Array.isArray(ap.by_party) ? ap.by_party : []).length })}</span>}/>
    </div>

    {/* 空賬引導:總賬事件驅動,先期初建賬 */}
    {ledgerEmpty && (
      <div className="rise" style={{ border: "1px solid var(--ink)", background: "var(--white)", padding: "20px 24px", marginTop: 24,
        display: "flex", flexWrap: "wrap", gap: 18, alignItems: "center", justifyContent: "space-between" }}>
        <div className="col g6" style={{ maxWidth: 720, minWidth: 260 }}>
          <LB red>LEDGER EMPTY</LB>
          <div style={{ fontSize: 15, fontWeight: 700, letterSpacing: "-.02em" }}>{t("總賬還是空的——這正常,不是沒同步。")}</div>
          <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("總賬是事件驅動的:只在新發生的採購、銷售、收付款時自動記賬,不會倒灌歷史庫存。做一次期初建賬,財務就和現有家底對上;物資要有單價才有價值。")}</div>
        </div>
        <B kind="primary" icon="sparkle" onClick={() => ask(t("幫我做期初建賬,把現有庫存價值計入總賬(用 fin init-balances);期初現金和銀行金額你來追問我。"))}>{t("讓秘書期初建賬")}</B>
      </div>
    )}

    {/* AI 事件待處理閉環：前端只讀，不直接調用過賬接口 */}
    {(eventsLoading || loadErrors.events || pendingEvents.length > 0) && (
      <Band no="00" title={t("待處理財務事件")}
        sub={loadErrors.events ? t("載入失敗") : t("AI 已錄入但尚未進入總賬的事件 · 前端只讀，交由秘書補齊或確認後過賬")}
        delay={.08}>
        {eventsLoading ? (
          <LoadPending/>
        ) : loadErrors.events ? (
          <LoadFailure detail={loadErrors.events} onRetry={reload}/>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th style={{ width: 40 }}>#</th><th>{t("事件號")}</th><th>{t("日期")}</th><th>{t("用途")}</th>
                <th style={{ textAlign: "right" }}>{t("金額")}</th><th>{t("狀態")}</th><th style={{ width: 120 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {pendingEvents.map((event, i) => {
                  const statusLabel = event.status === "ready" ? t("待確認過賬") : t("待補資料");
                  const eventNo = event.event_no || ("#" + event.id);
                  return (
                    <tr key={event.id || eventNo || i}>
                      <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                      <td><span className="num" style={{ fontWeight: 650 }}>{eventNo}</span></td>
                      <td><span className="num muted" style={{ fontSize: 12 }}>{event.event_date || "—"}</span></td>
                      <td><span style={{ fontWeight: 600, fontSize: 13 }}>{event.business_purpose || event.event_type || "—"}</span></td>
                      <td style={{ textAlign: "right" }}>
                        <div className="col g4" style={{ alignItems: "flex-end" }}>
                          <span className="num" style={{ fontWeight: 700, fontSize: 14 }}>
                            {event.orig_currency && event.orig_amount != null
                              ? event.orig_currency + " " + Number(event.orig_amount).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                              : money(event.amount)}
                          </span>
                          {event.orig_currency && event.orig_amount != null && event.orig_currency !== "CNY" && (
                            <span className="mono muted" style={{ fontSize: 9.5 }}>
                              @ {Number(event.fx_rate).toLocaleString("zh-CN", { maximumFractionDigits: 6 })} = {money(event.amount)}
                            </span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="col g4">
                          <T tone={event.status === "ready" ? "warn" : "bad"} dot>{statusLabel}</T>
                          <span className="mono muted" style={{ fontSize: 9.5 }}>{event.status}</span>
                        </div>
                      </td>
                      <td>
                        <B size="sm" icon="sparkle" onClick={() => ask(t(
                          "請處理財務事件 {no}（ID {id}，目前狀態 {status}）：先核對並補齊缺失資料；資料完整後向我複述過賬預覽並取得明確確認，才可使用 fin event post --id {id} 過賬。不要另建重複事件。",
                          { no: eventNo, id: event.id, status: event.status }
                        ))}>{t("交秘書處理")}</B>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {eventTotal > pendingEvents.length && (
              <div className="muted" style={{ padding: "12px 2px 2px", fontSize: 12 }}>
                {t("另有 {n} 筆待處理事件未顯示，請交由秘書繼續處理。", { n: eventTotal - pendingEvents.length })}
              </div>
            )}
          </div>
        )}
      </Band>
    )}

    {/* 01 · 三大報表 */}
    <Band no="01" title={t("三大報表")} sub={t("口徑:{p} · 即時從總賬推算", { p: pLabel })} delay={.1}
      right={<B size="sm" icon="sparkle" onClick={() => ask(t("把本期利潤表、資產負債表、現金流量表用大白話講一遍,指出異常和風險。"))}>{t("讓秘書解讀")}</B>}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 28 }}>
        {incomeLoading ? <LoadPending/> : loadErrors.income
          ? <LoadFailure detail={loadErrors.income} onRetry={reload}/>
          : <Stmt title={t("利潤表")} meta={inc.from ? inc.from + " ~ " + (inc.to || "") : pLabel} rows={plRows}/>}
        {bsD === null && !loadErrors.balanceSheet ? <LoadPending/> : loadErrors.balanceSheet
          ? <LoadFailure detail={loadErrors.balanceSheet} onRetry={reload}/>
          : <Stmt title={t("資產負債表")} meta={bs.as_of ? t("截至 {d}", { d: bs.as_of }) : null}
              tag={bs.as_of ? <T tone={bs.balanced ? "ok" : "bad"} dot>{bs.balanced ? t("平衡") : t("不平衡")}</T> : null} rows={bsRows}/>}
        {cfD === null && !loadErrors.cashflow ? <LoadPending/> : loadErrors.cashflow
          ? <LoadFailure detail={loadErrors.cashflow} onRetry={reload}/>
          : <Stmt title={t("現金流量表")} meta={cf.from ? cf.from + " ~ " + (cf.to || "") : pLabel} rows={cfRows}/>}
      </div>
    </Band>

    {/* 02 · 往來對賬(AP / AR + 賬齡) */}
    <Band no="02" title={t("往來對賬")} sub={t("賬齡分桶 0-30 / 31-60 / 61-90 / >90 天")} delay={.15}
      right={<B size="sm" icon="sparkle" onClick={() => ask(t("把應收應付逐個往來方對一遍賬,列出賬齡最久的幾筆,給出催收和付款建議。"))}>{t("讓秘書對賬")}</B>}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 380px), 1fr))", gap: 28 }}>
        {arLoading ? <LoadPending/> : loadErrors.ar
          ? <LoadFailure detail={loadErrors.ar} onRetry={reload}/>
          : <PartyBlock title={t("應收賬款 · 客戶欠我")} data={ar} isAR={true}/>}
        {apLoading ? <LoadPending/> : loadErrors.ap
          ? <LoadFailure detail={loadErrors.ap} onRetry={reload}/>
          : <PartyBlock title={t("應付賬款 · 我欠供應商")} data={ap} isAR={false}/>}
      </div>
    </Band>

    {/* 03 · 記賬憑證 */}
    <Band no="03" title={t("記賬憑證")} sub={t("最近 {n} 張 · 業務發生自動生成,每張借貸平衡", { n: (vouchersLoading || loadErrors.vouchers) ? "—" : shown.length })} delay={.2}
      right={<B size="sm" icon="plus" onClick={backfillPrompt}>{t("補錄一筆")}</B>}>
      {vouchersLoading ? (
        <LoadPending/>
      ) : loadErrors.vouchers ? (
        <LoadFailure detail={loadErrors.vouchers} onRetry={reload}/>
      ) : shown.length ? (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl2">
            <thead><tr>
              <th style={{ width: 40 }}>#</th><th>{t("憑證號")}</th><th>{t("日期")}</th><th>{t("摘要")}</th><th>{t("分錄")}</th>
              <th style={{ textAlign: "right" }}>{t("金額")}</th><th style={{ width: 190 }}>{t("來源業務")}</th>
            </tr></thead>
            <tbody>
              {shown.map((v, i) => {
                const lines = Array.isArray(v.lines) ? v.lines : [];
                const sourceEntityRef = voucherSourceEntityRef(v);
                return (
                  <tr key={v.id || v.voucher_no || i}>
                    <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                    <td><span className="num" style={{ fontWeight: 650 }}>{v.voucher_no || "—"}</span></td>
                    <td><span className="num muted" style={{ fontSize: 12 }}>{v.voucher_date || "—"}</span></td>
                    <td>
                      <div className="col g4" style={{ minWidth: 160 }}>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{v.summary || "—"}</span>
                        {v.source_type && <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".08em" }}>{v.source_type}</span>}
                      </div>
                    </td>
                    <td>
                      <div className="col g4">
                        {lines.slice(0, 4).map((l, j) => (
                          <span key={j} className="num" style={{ fontSize: 11, color: num(l && l.debit) > 0 ? "var(--ink)" : "var(--ink-3)" }}>
                            {num(l && l.debit) > 0 ? t("借") : t("貸")} {(l && l.code) || ""} {(l && l.name) || ""} {moneyIn(num(l && l.debit) || num(l && l.credit), v.currency)}
                          </span>
                        ))}
                        {lines.length > 4 && <span className="muted num" style={{ fontSize: 10.5 }}>+{lines.length - 4}</span>}
                      </div>
                    </td>
                    <td style={{ textAlign: "right" }}><span className="num" style={{ fontWeight: 700, fontSize: 14 }}>{moneyIn(v.total_amount, v.currency)}</span></td>
                    <td>
                      <div className="row g4 wrap">
                        {sourceEntityRef && <B size="sm" icon="arrow" onClick={() => W2.openEntity(sourceEntityRef, { tab: "overview" })}>{t("回到來源")}</B>}
                        <B size="sm" icon="sparkle" onClick={() => ask(t("解釋憑證 {no}({s}):這筆賬怎麼來的?借貸分錄逐條講給我聽。", { no: v.voucher_no || v.id || "—", s: v.summary || "—" }))}>{t("問這張")}</B>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EM icon="doc" title={t("暫無憑證")}
          sub={t("出入庫、採購、銷售、收付款發生後會自動生成憑證;歷史賬讓秘書補錄即可。")}
          action={<B size="sm" icon="plus" onClick={backfillPrompt}>{t("補錄一筆")}</B>}/>
      )}
    </Band>

    <div className="muted" style={{ fontSize: 10.5, padding: "16px 0 0", lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
  </>);
};

window.W2.PAGES["finance"] = Page;
})();
