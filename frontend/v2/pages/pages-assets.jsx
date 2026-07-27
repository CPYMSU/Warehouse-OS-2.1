/* WAREHOUSE 2.0 · 資產 — Swiss 版式,真後端
   駕駛艙子集:金融資產組合(/api/assets + /api/assets/portfolio)
   + 數字資產托管(/api/digital-assets + /api/digital-assets/summary)
   + 數字資產市場(/api/digital-assets/listings|trades|revenue)。
   頁面只讀;接入/評估/記交易/上架/購買/分潤全部交秘書。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "資產": "Assets",
  "金融資產組合 + 數字資產托管與市場 · 頁面只讀,接入交易上架全交秘書": "Financial portfolio + digital asset custody & market · read-only page, onboarding, trades & listings via the Secretary",
  // 三區子導航
  "金融資產": "Financial assets", "數字資產": "Digital assets", "交易中心": "Trading center",
  "總成本": "Total cost", "今日波動": "Day change", "回報率": "Return",
  "托管資產": "Assets in custody", "托管工作區": "Hosted workspaces", "估值總額": "Valuation total", "已上架": "Listed",
  "累計分潤": "Total allocated", "待跟進": "To follow up", "{n} 筆": "{n} trades",
  "待驗收 {n} · 待付分潤 {m}": "{n} pending acceptance · {m} unpaid distributions",
  "待驗收 {n} · 爭議 {d} · 待付分潤 {m}": "{n} pending · {d} disputed · {m} unpaid distributions",
  "全部妥當": "All settled", "行情延遲以公開接口為準": "quotes from public feeds, may lag",
  "評估分佈 {d}": "Grades {d}",
  "記一筆交易": "Record a trade",
  "問秘書": "Ask Secretary",
  "金融資產市值": "Portfolio value",
  "浮動盈虧": "Unrealized P&L",
  "市場在售": "Live listings",
  "累計成交": "Total traded",
  "元": "CNY", "萬元": "×10k CNY", "億元": "×100M CNY", "檔": "live", "項": "items", "個": "",
  "持倉 {h} 項 · 觀察 {w} 項": "{h} holdings · {w} watching",
  "尚未登記金融資產": "No financial assets yet",
  "回報率 {p}": "Return {p}",
  "全部達標": "All good",
  "數字資產可上架交易": "Digital assets can be listed",
  "讓秘書上架 →": "List via Secretary →",
  "已分潤 {v}": "Distributed {v}",
  "暫無成交": "No trades yet",
  "金融資產組合": "Financial portfolio",
  "行情來自公開接口,可能延遲 · 買賣分紅自動生成記賬憑證": "Quotes from public feeds, may lag · trades & dividends auto-post to GL",
  "持倉": "Holdings", "觀察": "Watching", "全部": "All",
  "總成本": "Total cost", "已實現+分紅": "Realized + dividends", "今日波動": "Day change", "資產配置": "Allocation",
  "類型": "Type", "數量": "Qty", "現價": "Price", "漲跌": "Chg", "市值 CNY": "Value CNY", "交給秘書": "Via Secretary",
  "股票": "Stock", "基金": "Fund", "黃金": "Gold", "加密": "Crypto", "其他": "Other",
  "買": "Buy", "賣": "Sell", "息": "Div",
  "待補代碼": "No symbol", "待刷新": "Stale", "未填代碼": "no symbol",
  "還沒有登記金融資產": "No financial assets registered yet",
  "當前篩選下沒有資產": "No assets under this filter",
  "換個範圍,或直接吩咐秘書。": "Change the scope, or just tell the Secretary.",
  "對秘書說「我買了 100 股◯◯,幫我登記」即可開始。": "Tell the Secretary \"I bought 100 shares of X, register it\" to get started.",
  "讓秘書登記": "Register via Secretary",
  "持有數量": "Quantity", "成本均價": "Avg cost", "現價(原幣)": "Price (ccy)", "今日漲跌": "Day chg", "市值(CNY)": "Value (CNY)", "行情更新": "Quote time",
  "觀察倉 · 只跟蹤行情,不參與記賬": "Watch-only · quotes tracked, no accounting",
  "直接吩咐秘書": "Tell the Secretary",
  "記買入": "Record buy", "記賣出": "Record sell", "記分紅": "Record dividend", "深度解讀": "Deep dive",
  "轉為持倉": "Convert to holding", "補代碼 / 行情": "Fix symbol / quote",
  "2.0 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.0 rule: this page is read-only; changes run through the Secretary with a full audit trail.",
  "行情僅供參考,不構成投資建議 · 買賣分紅自動生成記賬憑證,可在財務模塊查賬": "Quotes for reference only, not investment advice · trades & dividends auto-post vouchers, see Finance",
  "數字資產市場": "Digital asset market",
  "條款鋼印 · 擔保交付 · 平台不碰資金": "Sealed terms · guaranteed delivery · platform never touches funds",
  "上架諮詢": "Listing advice",
  "在售 {n} 檔": "{n} live",
  "上架": "Listing", "權益": "Right", "AI 評估": "AI grade", "單價": "Price", "剩餘": "Remaining", "已售": "Sold",
  "《{ti}》": "“{ti}”",
  "使用權": "License", "訂閱": "Subscription", "收益權": "Revenue share", "份額權": "Fractional",
  "面議": "Negotiable", "不限": "Unlimited", "未評估": "Not assessed",
  "{n} 份": "{n} units",
  "詳情": "Details", "購買": "Buy",
  "市場虛位以待": "The market awaits its first listing",
  "確權 → 估值 → 合規 → 上架,秘書全程代辦。": "Rights → valuation → compliance → listing, the Secretary handles it all.",
  "交給秘書上架": "List via Secretary",
  "成交與分潤": "Trades & distribution",
  "最近成交": "Recent trades", "收益與分潤": "Revenue & distribution",
  "記一筆收益": "Record revenue",
  "累計 {v}": "Total {v}", "已分潤": "Distributed",
  "待付分潤": "Distribution due",
  "憑證 #{n}": "Voucher #{n}",
  "買方 {c}": "buyer {c}",
  "待驗收": "Pending acceptance", "已驗收": "Accepted", "爭議": "Disputed",
  "收入": "Revenue", "授權費": "Royalty", "調用費": "Usage fee", "分紅": "Dividend", "成本": "Cost",
  "暫無成交。結算後自動出現在這裡。": "No trades yet. Settlements appear here automatically.",
  "暫無收益事件。": "No revenue events yet.",
  // 數字資產 · 托管
  "數字資產 · 托管": "Digital assets · Custody",
  "確權 → 托管 → 評估 → 上架 · 站點與數據庫由平台托管": "Rights → custody → assessment → listing · sites & databases hosted by the platform",
  "接入新資產": "Onboard new asset",
  "托管工作區": "Hosted workspaces", "已上架": "Listed", "估值總額": "Valuation total", "評估分佈": "Grade mix",
  "托管": "Hosting", "估值": "Valuation", "狀態": "Status", "時間": "Updated",
  "站點": "Site", "訪問站點": "Open site", "未托管": "Not hosted", "未估值": "No valuation",
  "在售": "Live", "未上架": "Unlisted",
  "數據資產": "Data asset", "流程資產": "Process asset", "知識資產": "Knowledge asset", "軟件資產": "Software asset",
  "算法模型": "Model", "AI Agent": "AI Agent", "項目資產": "Project asset",
  "發現": "Discover", "標準化": "Standardize", "托管中": "In custody", "交易中": "Trading",
  "草稿": "Draft", "已登記": "Registered", "已托管": "Custodied", "已歸檔": "Archived",
  "低風險": "Low risk", "中風險": "Medium risk", "高風險": "High risk", "嚴重風險": "Critical risk",
  "編號": "Asset no.", "階段": "Stage", "風險": "Risk", "負責人": "Owner", "合規": "Compliance",
  "權益數": "Rights", "上架數": "Listings", "建立": "Created", "更新": "Updated",
  "數據庫": "Database", "運行狀態": "Runtime", "工作區": "Workspace", "摘要": "Summary",
  "評估資產": "Assess asset", "上架到市場": "List on market", "訪問與收入": "Traffic & revenue",
  "開通托管工作區": "Provision workspace", "工作區控制台": "Workspace console",
  "評": "Grade", "架": "List",
  "還沒有托管的數字資產": "No digital assets onboarded yet",
  "對秘書說「幫我接入第一個數字資產」,開通工作區或登記現有能力即可開始。": "Tell the Secretary \"onboard my first digital asset\" — provision a workspace or register an existing capability to get started.",
  "讓秘書接入": "Onboard via Secretary",
  "我要接入一個新的數字資產:請先問我是要開通托管工作區(網頁+專屬數據庫+API Key)還是登記已有的數據/軟件/模型能力,追問項目名稱、資產類型和一句話說明,確認後執行並把接入步驟和 Key 保管注意事項整理給我": "I want to onboard a new digital asset: first ask whether I need a hosted workspace (site + dedicated database + API key) or to register an existing data/software/model capability, ask for the project name, asset kind and a one-line summary, then execute and give me the onboarding steps and key-safekeeping notes.",
  "幫我評估數字資產「{name}」(#{id}):出 AI 評估報告,講清等級、分數、關鍵證據、風險旗標和建議定價區間": "Assess digital asset \"{name}\" (#{id}): produce the AI assessment report and explain the grade, score, key evidence, risk flags and suggested price range.",
  "把數字資產「{name}」(#{id})上架到市場:先出 AI 評估與合規預審,再和我確定權益類型、定價與份額,確認後上架": "List digital asset \"{name}\" (#{id}) on the market: run the AI assessment and compliance pre-check first, then agree right type, pricing and units with me, and list it after my confirmation.",
  "看看數字資產「{name}」(#{id})的訪問與收入情況:站點訪問、接口調用、成交與收益分潤都查一遍,匯總成結論講給我": "Show me the traffic and revenue of digital asset \"{name}\" (#{id}): check site visits, API calls, trades and revenue distributions, and summarize the conclusions for me.",
  "幫我為數字資產「{name}」(#{id})開通托管工作區:網頁+專屬數據庫+API Key,開通後把客戶接入步驟整理給我": "Provision a hosted workspace for digital asset \"{name}\" (#{id}): site + dedicated database + API key, then give me the client onboarding steps.",
  "打開數字資產「{name}」的托管工作區({ws}):匯報站點、數據庫與 API Key 狀態,然後問我要做什麼(部署網頁/建表/查數/改數)再逐步執行": "Open the hosted workspace of digital asset \"{name}\" ({ws}): report site, database and API key status, then ask me what to do (deploy site / create tables / query / update data) and execute step by step.",
  // 秘書指令
  "資產這塊現在有什麼要我拍板的?組合異動、缺代碼缺行情的資產、市場待處理訂單和待付分潤都列出來": "What asset decisions are waiting on me? List portfolio movers, assets missing symbols or quotes, pending market orders and unpaid distributions.",
  "我要記一筆金融資產交易(買入/賣出/分紅),請按資產、數量、成交價或總額、手續費、賬戶、日期逐項追問,確認後登記並生成記賬憑證": "I want to record a financial asset trade (buy/sell/dividend). Ask me for asset, quantity, price or total, fees, account and date one by one, then register it and post the voucher.",
  "我要登記一種金融資產(股票/基金/黃金/加密),請追問名稱、代碼、數量、總成本,確認後登記建檔": "I want to register a financial asset (stock/fund/gold/crypto). Ask me for name, symbol, quantity and total cost, then create it.",
  "我買入了「{name}」({sym}),請追問數量、成交價/總額、手續費、支付賬戶和日期,然後登記並記賬": "I bought \"{name}\" ({sym}). Ask me for quantity, price/total, fees, paying account and date, then register and post it.",
  "我賣出了「{name}」({sym}),請追問數量、成交價/總額、手續費、收款賬戶和日期,計算已實現盈虧並記賬": "I sold \"{name}\" ({sym}). Ask me for quantity, price/total, fees, receiving account and date, compute realized P&L and post it.",
  "「{name}」有分紅/派息,請追問金額、稅費、到賬賬戶和日期,登記並記賬": "\"{name}\" paid a dividend. Ask me for amount, tax, receiving account and date, then register and post it.",
  "請對「{name}」({sym})做深度解讀:先查最新行情與走勢,再跑量化與風險分析,用人話講結論和風險": "Deep-dive \"{name}\" ({sym}): check latest quote and trend, run quant and risk analysis, and explain conclusions and risks in plain words.",
  "「{name}」是觀察倉,我想登記買入轉為持倉:請追問數量、成交價、手續費、賬戶和日期後執行": "\"{name}\" is watch-only. I want to record a buy and convert it to a holding: ask me for quantity, price, fees, account and date, then execute.",
  "「{name}」缺代碼或行情,請搜索候選代碼讓我確認,然後刷新現價、匯率和漲跌幅": "\"{name}\" is missing a symbol or quote. Search candidate symbols for my confirmation, then refresh price, FX and change.",
  "我想把一項數字資產上架交易:請列出已登記資產讓我選,先出 AI 評估與合規預審,再和我確定權益類型與定價,確認後上架": "I want to list a digital asset for trading: show me registered assets to choose from, run the AI assessment and compliance pre-check first, agree right type and pricing with me, then list it.",
  "數字市場上架《{title}》(資產「{a}」,{r},單價 {p}):請調出完整檔案與 AI 評估,幫我判斷值不值得買": "Market listing \"{title}\" (asset \"{a}\", {r}, price {p}): pull its full file and AI assessment and help me judge whether it is worth buying.",
  "我想購買上架《{title}》(單價 {p}):請追問買方名稱、實名聯繫方式和份數,登記訂單並講解受理 → 付款申報 → 收款確認 → 結算交付的流程": "I want to buy listing \"{title}\" (price {p}): ask me for buyer name, verified contact and units, register the order and walk me through review → payment declaration → receipt confirmation → settlement & delivery.",
  "成交 #{id}「{a}」《{ti}》× {u},買方 {c},金額 {amt}:請查交付與驗收狀態,需要我跟進的列出來": "Trade #{id} \"{a}\" listing \"{ti}\" × {u}, buyer {c}, amount {amt}: check delivery and acceptance status and list anything I need to follow up.",
  "收益事件 #{id}({a},{ty},{amt}):請帶出分潤明細與支付狀態,未付的列出應付名單": "Revenue event #{id} ({a}, {ty}, {amt}): show the distribution breakdown and payment status, and list unpaid payees.",
  "我要登記一筆數字資產收益並分潤:請追問是哪個資產、金額、收益來源,登記後把每位持有人的分潤明細列給我": "I want to record a digital asset revenue event and distribute it: ask me which asset, the amount and the source, then register it and show each holder's share.",
});
const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, StackBar, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 格式化(防禦性:任何字段可缺) ── */
const fin = (v) => v != null && Number.isFinite(Number(v));
const cny = (v, d = 0) => fin(v) ? "¥" + Number(v).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: Math.max(d, 2) }) : "—";
const nfmt = (v, mx = 4) => fin(v) ? Number(v).toLocaleString("zh-CN", { maximumFractionDigits: mx }) : "—";
const pctf = (v) => fin(v) ? (Number(v) >= 0 ? "+" : "") + Number(v).toFixed(2) + "%" : "—";
const toneOf = (v) => fin(v) && Number(v) < 0 ? "var(--red)" : "var(--ink)";
const qtime = (v) => v ? String(v).replace("T", " ").slice(5, 16) : "";
/* KPI 巨型數字用緊湊制:值 + 單位 */
const kfmt = (v) => {
  if (!fin(v)) return ["—", ""];
  const n = Number(v), a = Math.abs(n);
  if (a >= 1e8) return [(n / 1e8).toFixed(a >= 1e10 ? 0 : 2), t("億元")];
  if (a >= 1e4) return [(n / 1e4).toFixed(a >= 1e6 ? 0 : 1), t("萬元")];
  return [Math.round(n).toLocaleString("zh-CN"), t("元")];
};

const TYPE_L = { stock: "股票", fund: "基金", gold: "黃金", crypto: "加密", other: "其他" };
const RIGHT_L = { license: "使用權", subscription: "訂閱", revenue_share: "收益權", fractional: "份額權" };
const EVENT_L = { revenue: "收入", royalty: "授權費", usage_fee: "調用費", dividend: "分紅", cost: "成本" };
const ACCEPT_L = { pending: "待驗收", accepted: "已驗收", disputed: "爭議" };
/* 數字資產(/api/digital-assets)字典 */
const DKIND_L = { data: "數據資產", process: "流程資產", knowledge: "知識資產", software: "軟件資產", model: "算法模型", agent: "AI Agent", project: "項目資產", other: "其他" };
const DSTAGE_L = { discover: "發現", standardize: "標準化", custody: "托管中", valuation: "估值", listing: "上架", trading: "交易中" };
const DSTATUS_L = { draft: "草稿", registered: "已登記", custodied: "已托管", listed: "已上架", archived: "已歸檔" };
const DRISK_L = { low: "低風險", medium: "中風險", high: "高風險", critical: "嚴重風險" };
const gradeTone = (g) => g === "A" ? "inv" : g === "B" ? "ok" : g === "C" ? "warn" : g === "D" ? "bad" : "plain";
const assessScore = (as) => as ? (fin(as.overall_score) ? as.overall_score : (fin(as.score) ? as.score : null)) : null;
const wsHref = (ws) => (ws && (ws.public_url || ws.public_path)) || null;

/* ── 金融資產抽屜 ── */
const AssetDrawer = ({ a, onClose }) => {
  const sym = a.symbol || t("未填代碼");
  const watch = !!a.watch_only;
  const acts = watch ? [
    ["inbound", "轉為持倉", t("「{name}」是觀察倉,我想登記買入轉為持倉:請追問數量、成交價、手續費、賬戶和日期後執行", { name: a.name })],
    ["scan", "補代碼 / 行情", t("「{name}」缺代碼或行情,請搜索候選代碼讓我確認,然後刷新現價、匯率和漲跌幅", { name: a.name })],
    ["sparkle", "深度解讀", t("請對「{name}」({sym})做深度解讀:先查最新行情與走勢,再跑量化與風險分析,用人話講結論和風險", { name: a.name, sym })],
  ] : [
    ["inbound", "記買入", t("我買入了「{name}」({sym}),請追問數量、成交價/總額、手續費、支付賬戶和日期,然後登記並記賬", { name: a.name, sym })],
    ["outbound", "記賣出", t("我賣出了「{name}」({sym}),請追問數量、成交價/總額、手續費、收款賬戶和日期,計算已實現盈虧並記賬", { name: a.name, sym })],
    ["wallet", "記分紅", t("「{name}」有分紅/派息,請追問金額、稅費、到賬賬戶和日期,登記並記賬", { name: a.name })],
    ["sparkle", "深度解讀", t("請對「{name}」({sym})做深度解讀:先查最新行情與走勢,再跑量化與風險分析,用人話講結論和風險", { name: a.name, sym })],
  ];
  const cells = [
    [t("持有數量"), watch ? "—" : nfmt(a.quantity)],
    [t("成本均價"), watch ? "—" : cny(a.avg_cost_cny, 2)],
    [t("現價(原幣)"), fin(a.last_price) ? nfmt(a.last_price) + " " + (a.last_price_currency || "") : "—"],
    [t("今日漲跌"), pctf(a.last_change_pct)],
    [t("市值(CNY)"), watch ? "—" : cny(a.market_value_cny)],
    [t("浮動盈虧"), watch ? "—" : cny(a.unrealized_pnl_cny)],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <T tone={watch ? "plain" : (fin(a.last_change_pct) && Number(a.last_change_pct) < 0 ? "bad" : "ok")} dot>
            {watch ? t("觀察") : t("持倉")}
          </T>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.25 }}>{a.name || "—"}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{sym} · {t(TYPE_L[a.asset_type] || a.asset_type || "其他")}</div>
        {watch && <div className="muted" style={{ fontSize: 10.5, marginTop: 8 }}>{t("觀察倉 · 只跟蹤行情,不參與記賬")}</div>}
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {cells.map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 14, fontWeight: 650, color: k === t("浮動盈虧") || k === t("今日漲跌") ? toneOf(k === t("今日漲跌") ? a.last_change_pct : a.unrealized_pnl_cny) : "var(--ink)" }}>{v}</span>
            </div>
          ))}
        </div>
        {a.last_quote_at && (
          <div className="row g8" style={{ marginBottom: 16 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("行情更新")}</LB>
            <span className="num muted" style={{ fontSize: 11 }}>{qtime(a.last_quote_at)}</span>
          </div>
        )}
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

/* ── 數字資產(托管)抽屜 ── */
const DigitalDrawer = ({ a, assess, onClose }) => {
  const ws = a.workspace || null;
  const url = wsHref(ws);
  const val = a.latest_valuation || null;
  const lc = a.latest_compliance || null;
  const score = assessScore(assess);
  const listed = a.status === "listed" || num(a.listings_count) > 0;
  const cells = [
    [t("編號"), a.asset_no || "—"],
    [t("類型"), t(DKIND_L[a.asset_kind] || a.kind_label || "其他")],
    [t("狀態"), t(DSTATUS_L[a.status] || a.status || "—")],
    [t("階段"), t(DSTAGE_L[a.lifecycle_stage] || a.lifecycle_stage || "—")],
    [t("風險"), t(DRISK_L[a.risk_level] || a.risk_level || "—")],
    [t("負責人"), a.owner_name || a.created_by || "—"],
    [t("AI 評估"), assess && assess.grade ? assess.grade + (score != null ? " · " + score : "") : t("未評估")],
    [t("估值"), val && fin(val.valuation_cny) ? cny(val.valuation_cny) : t("未估值")],
    [t("權益數"), nfmt(a.rights_count, 0)],
    [t("上架數"), nfmt(a.listings_count, 0)],
    [t("建立"), (a.created_at || "").slice(0, 10) || "—"],
    [t("更新"), (a.updated_at || "").slice(0, 10) || "—"],
  ];
  const acts = [
    ["scan", "評估資產", t("幫我評估數字資產「{name}」(#{id}):出 AI 評估報告,講清等級、分數、關鍵證據、風險旗標和建議定價區間", { name: a.name || "—", id: a.id ?? "—" })],
    ["trend", "上架到市場", t("把數字資產「{name}」(#{id})上架到市場:先出 AI 評估與合規預審,再和我確定權益類型、定價與份額,確認後上架", { name: a.name || "—", id: a.id ?? "—" })],
    ["chart", "訪問與收入", t("看看數字資產「{name}」(#{id})的訪問與收入情況:站點訪問、接口調用、成交與收益分潤都查一遍,匯總成結論講給我", { name: a.name || "—", id: a.id ?? "—" })],
    ws
      ? ["cpu", "工作區控制台", t("打開數字資產「{name}」的托管工作區({ws}):匯報站點、數據庫與 API Key 狀態,然後問我要做什麼(部署網頁/建表/查數/改數)再逐步執行", { name: a.name || "—", ws: ws.workspace_key || "—" })]
      : ["pkg", "開通托管工作區", t("幫我為數字資產「{name}」(#{id})開通托管工作區:網頁+專屬數據庫+API Key,開通後把客戶接入步驟整理給我", { name: a.name || "—", id: a.id ?? "—" })],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            {listed ? <T tone="ok" dot>{t("在售")}</T> : <T tone="plain">{t(DSTATUS_L[a.status] || a.status || "未上架")}</T>}
            {assess && assess.grade && <T tone={gradeTone(assess.grade)}>AI·{assess.grade}</T>}
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.25 }}>{a.name || "—"}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{a.asset_no || "—"} · {t(DKIND_L[a.asset_kind] || a.kind_label || "其他")}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {cells.map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 14, fontWeight: 650 }}>{v}</span>
            </div>
          ))}
        </div>
        {ws && (
          <div className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8, marginBottom: 16 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("托管")}</LB>
            <span className="num" style={{ fontSize: 13, fontWeight: 650 }}>{ws.workspace_key || "—"}</span>
            {url && (
              <a href={url} target="_blank" rel="noopener noreferrer" className="num"
                style={{ fontSize: 11.5, color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3, wordBreak: "break-all" }}>
                {url} ↗
              </a>
            )}
            <span className="num muted" style={{ fontSize: 11 }}>
              {t("數據庫")} {ws.database_name || "—"} · {t("運行狀態")} {ws.runtime_status || "—"}{ws.runtime_type ? " · " + ws.runtime_type : ""}
            </span>
          </div>
        )}
        {lc && (lc.status || lc.conclusion) && (
          <div className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8, marginBottom: 16 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("合規")}</LB>
            <span style={{ fontSize: 12, lineHeight: 1.6 }}>{[lc.status, lc.conclusion].filter(Boolean).join(" · ") || "—"}</span>
          </div>
        )}
        {a.summary && (
          <div className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8, marginBottom: 16 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("摘要")}</LB>
            <span className="ink2" style={{ fontSize: 12, lineHeight: 1.6 }}>{a.summary}</span>
          </div>
        )}
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

/* ── 09 · 資產:內部三區(金融資產 / 數字資產 / 交易中心)── */
const TABS = [["fin", "金融資產"], ["dig", "數字資產"], ["trade", "交易中心"]];
const tabInit = () => { try { const v = sessionStorage.getItem("w2_assets_tab"); return TABS.some(([id]) => id === v) ? v : "fin"; } catch (e) { return "fin"; } };

const Page = ({ boot }) => {
  const [assets, setAssets] = _s(null);      // /api/assets → {assets:[]}
  const [pf, setPf] = _s(null);              // /api/assets/portfolio
  const [listings, setListings] = _s(null);  // /api/digital-assets/listings
  const [commonListings, setCommonListings] = _s(null); // /api/digital-assets/common-market
  const [trades, setTrades] = _s(null);      // /api/digital-assets/trades
  const [rev, setRev] = _s(null);            // /api/digital-assets/revenue
  const [das, setDas] = _s(null);            // /api/digital-assets → {assets:[]}(托管的數字資產本身)
  const [dsum, setDsum] = _s(null);          // /api/digital-assets/summary
  const [scope, setScope] = _s("all");
  const [sel, setSel] = _s(null);
  const [dsel, setDsel] = _s(null);
  const [tab, setTabRaw] = _s(tabInit);
  const setTab = (id) => { setTabRaw(id); setSel(null); setDsel(null); try { sessionStorage.setItem("w2_assets_tab", id); } catch (e) {} };

  _e(() => {
    W2.json("/api/assets").then(d => setAssets((d && d.assets) || [])).catch(() => setAssets([]));
    W2.json("/api/assets/portfolio").then(d => setPf(d || {})).catch(() => setPf({}));
    W2.json("/api/digital-assets?limit=300").then(d => setDas((d && d.assets) || [])).catch(() => setDas([]));
    W2.json("/api/digital-assets/summary").then(d => setDsum(d || {})).catch(() => setDsum({}));
    W2.json("/api/digital-assets/listings?status=listed&limit=100").then(d => setListings((d && d.listings) || [])).catch(() => setListings([]));
    W2.json("/api/digital-assets/common-market").then(d => setCommonListings((d && d.listings) || [])).catch(() => setCommonListings([]));
    W2.json("/api/digital-assets/trades?limit=50").then(d => setTrades(d || {})).catch(() => setTrades({}));
    W2.json("/api/digital-assets/revenue?limit=50").then(d => setRev(d || {})).catch(() => setRev({}));
    const h = (e) => { if (e.key === "Escape") { setSel(null); setDsel(null); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const all = assets || [];
  const P = pf || {};
  const holdings = all.filter(a => !a.watch_only);
  const watching = all.filter(a => !!a.watch_only);
  const list = scope === "hold" ? holdings : scope === "watch" ? watching : all;
  const ownLive = listings || [];
  const live = commonListings || [];
  const tradeRows = (trades && trades.trades) || [];
  const revRows = (rev && rev.events) || [];

  const pnl = fin(P.unrealized_pnl_cny) ? Number(P.unrealized_pnl_cny) : null;
  const retPct = pnl != null && fin(P.total_cost_cny) && Number(P.total_cost_cny) ? pnl / Number(P.total_cost_cny) * 100 : null;
  const [mvV, mvU] = kfmt(P.total_value_cny);
  const [pnlV, pnlU] = kfmt(pnl);
  const [trdV, trdU] = kfmt(trades && trades.total_amount_cny);
  const distTotal = rev && rev.total_distributed_cny;
  /* 三區 KPI 補充。待跟進優先用後端全表統計(rows 受 limit 截斷),舊後端無字段時退回掃當前窗口 */
  const [costV, costU] = kfmt(P.total_cost_cny);
  const [dayV, dayU] = kfmt(P.day_change_cny);
  const [distV, distU] = kfmt(distTotal);
  const pendingTrades = fin(trades && trades.pending_acceptance) ? Number(trades.pending_acceptance)
    : tradeRows.filter(x => x && x.acceptance_status === "pending").length;
  const disputedTrades = fin(trades && trades.disputed_count) ? Number(trades.disputed_count)
    : tradeRows.filter(x => x && x.acceptance_status === "disputed").length;
  const isUnpaidEv = (ev) => ev && ev.allocation && Array.isArray(ev.allocation.allocations) && ev.allocation.allocations.length > 0 && !ev.allocation.paid;
  const unpaidDist = fin(rev && rev.unpaid_allocations) ? Number(rev.unpaid_allocations) : revRows.filter(isUnpaidEv).length;
  const followUp = pendingTrades + disputedTrades + unpaidDist;
  const followUpKnown = !!(trades && Array.isArray(trades.trades)) && !!(rev && Array.isArray(rev.events));

  const stack = _mm(() => (Array.isArray(P.allocation) ? P.allocation : [])
    .filter(s => num(s.value_cny) > 0)
    .map((s, i) => ({ value: num(s.value_cny), color: W2.CHART_COLORS[i % W2.CHART_COLORS.length], label: t(TYPE_L[s.type] || s.label || s.type || "其他"), pct: s.pct })), [pf]);

  /* ── 數字資產 · 托管:登記冊 + summary 小計 ── */
  const dRows = das || [];
  const DS = dsum || {};
  /* 資產列表本身不帶評估;由市場上架行的 assessment(按 asset_id)反推,無則「未評估」 */
  const assessMap = _mm(() => {
    const m = {};
    (listings || []).forEach(l => { if (l && l.asset_id != null && l.assessment) m[l.asset_id] = l.assessment; });
    return m;
  }, [listings]);
  const dAssess = (a) => (a && a.assessment) || assessMap[a && a.id] || null;
  const dSumAssets = Array.isArray(DS.by_kind) ? DS.by_kind.reduce((s, x) => s + (Number(x && x.count) || 0), 0) : null;
  const dSumListed = Array.isArray(DS.listings) ? Number((DS.listings.find(x => x && x.status === "listed") || {}).count || 0) : null;
  const gradeDist = _mm(() => {
    const c = {};
    (das || []).forEach(a => { const g = (dAssess(a) || {}).grade; if (g) c[g] = (c[g] || 0) + 1; });
    return ["A", "B", "C", "D"].filter(g => c[g]).map(g => g + "×" + c[g]).join(" · ");
  }, [das, listings]);
  const hasDSum = dSumAssets != null || fin(DS.workspaces) || (fin(DS.latest_valuation_total_cny) && Number(DS.latest_valuation_total_cny) > 0);
  const onboardPrompt = () => ask(t("我要接入一個新的數字資產:請先問我是要開通托管工作區(網頁+專屬數據庫+API Key)還是登記已有的數據/軟件/模型能力,追問項目名稱、資產類型和一句話說明,確認後執行並把接入步驟和 Key 保管注意事項整理給我"));

  const askListing = (l, buy) => {
    const ref = l.ref || l.asset_no || l.id || "—";
    const seller = l.company || l.tenant_slug || "—";
    return ask(buy
      ? t("我想購買共同市場上架《{title}》(引用 {ref},賣方 {seller},單價 {p}):請先鎖定這一筆跨公司上架,再追問買方名稱、實名聯繫方式和份數,登記訂單並講解受理 → 付款申報 → 收款確認 → 結算交付的流程", { title: l.title || "—", ref, seller, p: fin(l.price_cny) ? cny(l.price_cny) : t("面議") })
      : t("共同市場上架《{title}》(引用 {ref},賣方 {seller},資產「{a}」,{r},單價 {p}):請鎖定這一筆跨公司上架,調出可見檔案與 AI 評估,幫我判斷值不值得買", { title: l.title || "—", ref, seller, a: l.asset_name || "—", r: t(RIGHT_L[l.listing_type] || l.listing_type || "—"), p: fin(l.price_cny) ? cny(l.price_cny) : t("面議") }));
  };

  const folioRight = tab === "fin" ? (<>
    <B icon="plus" onClick={() => ask(t("我要記一筆金融資產交易(買入/賣出/分紅),請按資產、數量、成交價或總額、手續費、賬戶、日期逐項追問,確認後登記並生成記賬憑證"))}>{t("記一筆交易")}</B>
    <B kind="primary" icon="sparkle" onClick={() => ask(t("資產這塊現在有什麼要我拍板的?組合異動、缺代碼缺行情的資產、市場待處理訂單和待付分潤都列出來"))}>{t("問秘書")}</B>
  </>) : tab === "dig" ? (<>
    <B icon="plus" onClick={onboardPrompt}>{t("接入新資產")}</B>
    <B kind="primary" icon="sparkle" onClick={() => ask(t("資產這塊現在有什麼要我拍板的?組合異動、缺代碼缺行情的資產、市場待處理訂單和待付分潤都列出來"))}>{t("問秘書")}</B>
  </>) : (<>
    <B icon="plus" onClick={() => ask(t("我要登記一筆數字資產收益並分潤:請追問是哪個資產、金額、收益來源,登記後把每位持有人的分潤明細列給我"))}>{t("記一筆收益")}</B>
    <B kind="primary" icon="sparkle" onClick={() => ask(t("資產這塊現在有什麼要我拍板的?組合異動、缺代碼缺行情的資產、市場待處理訂單和待付分潤都列出來"))}>{t("問秘書")}</B>
  </>);
  const tabCount = { fin: all.length, dig: dRows.length, trade: live.length };

  return (<>
    <Folio no="09" en="ASSETS" title={t("資產")}
      sub={t("金融資產組合 + 數字資產托管與市場 · 頁面只讀,接入交易上架全交秘書")}
      right={folioRight}/>

    <div className="subnav rise" style={{ animationDelay: ".03s" }}>
      {TABS.map(([id, label], i) => (
        <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>
          <span className="sn-no">{pad2(i + 1)}</span>{t(label)}
          <span className="sn-count">{tabCount[id]}</span>
        </button>
      ))}
    </div>

    {/* ═══ 一 · 金融資產 ═══ */}
    {tab === "fin" && (<>
    <div className="kpi-band">
      <Kpi label={t("金融資產市值")} value={mvV} unit={mvU} delay={0}
        foot={all.length
          ? <span className="muted" style={{ fontSize: 11.5 }}>{t("持倉 {h} 項 · 觀察 {w} 項", { h: holdings.length, w: watching.length })}</span>
          : <span className="muted" style={{ fontSize: 11.5 }}>{t("尚未登記金融資產")}</span>}/>
      <Kpi label={t("浮動盈虧")} value={pnlV} unit={pnlU} red={pnl != null && pnl < 0} delay={.05}
        foot={retPct != null
          ? <T tone={retPct < 0 ? "bad" : "ok"} dot>{t("回報率 {p}", { p: pctf(retPct) })}</T>
          : <span className="muted" style={{ fontSize: 11.5 }}>—</span>}/>
      <Kpi label={t("總成本")} value={costV} unit={costU} delay={.1}
        foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("已實現+分紅")} {cny(fin(P.realized_pnl_cny) || fin(P.dividends_cny) ? (Number(P.realized_pnl_cny) || 0) + (Number(P.dividends_cny) || 0) : null)}</span>}/>
      <Kpi label={t("今日波動")} value={dayV} unit={dayU} red={fin(P.day_change_cny) && Number(P.day_change_cny) < 0} delay={.15}
        foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("行情延遲以公開接口為準")}</span>}/>
    </div>

    <Band no="01" title={t("金融資產組合")} sub={t("行情來自公開接口,可能延遲 · 買賣分紅自動生成記賬憑證")} delay={.1}
      right={<div className="seg">
        {[["all", "全部"], ["hold", "持倉"], ["watch", "觀察"]].map(([id, label]) => (
          <button key={id} className={scope === id ? "on" : ""} onClick={() => { setScope(id); setSel(null); }}>{t(label)}</button>
        ))}
      </div>}>
      {!all.length ? (
        <EM icon="chart" title={t("還沒有登記金融資產")} sub={t("對秘書說「我買了 100 股◯◯,幫我登記」即可開始。")}
          action={<B icon="sparkle" size="sm" onClick={() => ask(t("我要登記一種金融資產(股票/基金/黃金/加密),請追問名稱、代碼、數量、總成本,確認後登記建檔"))}>{t("讓秘書登記")}</B>}/>
      ) : (<>
        {!!stack.length && (
          <div className="col g8" style={{ marginBottom: 18, borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
            <LB dim style={{ fontSize: 8.5 }}>{t("資產配置")}</LB>
            <StackBar data={stack}/>
            <div className="row g12 wrap" style={{ fontSize: 11.5 }}>
              {stack.map(s => (
                <span key={s.label} className="row g6">
                  <span style={{ width: 9, height: 9, background: s.color, flexShrink: 0 }}/>
                  <span className="ink2">{s.label}</span>
                  <span className="num muted">{fin(s.pct) ? s.pct + "%" : ""}</span>
                </span>
              ))}
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th style={{ width: 34 }}>#</th><th>{t("資產")}</th><th>{t("類型")}</th><th>{t("數量")}</th><th>{t("現價")}</th><th>{t("漲跌")}</th><th>{t("市值 CNY")}</th><th>{t("浮動盈虧")}</th><th style={{ width: 128 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {list.map((a, i) => {
                  const watch = !!a.watch_only;
                  const sym = a.symbol || t("未填代碼");
                  return (
                    <tr key={a.id || i} className={sel && sel.id === a.id ? "on" : ""} style={{ cursor: "pointer" }} onClick={() => setSel(a)}>
                      <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                      <td>
                        <div className="col g4">
                          <span className="row g8" style={{ fontWeight: 650 }}>{a.name || "—"}{watch && <T tone="plain">{t("觀察")}</T>}</span>
                          <span className="num muted" style={{ fontSize: 11 }}>{sym}</span>
                        </div>
                      </td>
                      <td className="muted">{t(TYPE_L[a.asset_type] || a.asset_type || "其他")}</td>
                      <td className="num">{watch ? "—" : nfmt(a.quantity)}</td>
                      <td>
                        {!a.symbol ? <T tone="warn">{t("待補代碼")}</T>
                          : !fin(a.last_price) ? <T tone="plain">{t("待刷新")}</T>
                          : <div className="col g2">
                              <span className="num" style={{ fontWeight: 600 }}>{nfmt(a.last_price)} <span className="muted" style={{ fontSize: 10.5 }}>{a.last_price_currency || ""}</span></span>
                              {a.last_quote_at && <span className="num muted" style={{ fontSize: 10 }}>{qtime(a.last_quote_at)}</span>}
                            </div>}
                      </td>
                      <td className="num" style={{ fontWeight: 700, color: toneOf(a.last_change_pct) }}>{pctf(a.last_change_pct)}</td>
                      <td className="num" style={{ fontWeight: 650 }}>{watch ? "—" : cny(a.market_value_cny)}</td>
                      <td className="num" style={{ fontWeight: 700, color: toneOf(a.unrealized_pnl_cny) }}>
                        {watch ? "—" : <>{cny(a.unrealized_pnl_cny)}{fin(a.unrealized_pnl_pct) ? <span className="muted" style={{ fontWeight: 400, fontSize: 11 }}> ({pctf(a.unrealized_pnl_pct)})</span> : null}</>}
                      </td>
                      <td onClick={e => e.stopPropagation()}>
                        <div className="row g4">
                          <button className="btn sm" style={{ padding: "0 9px" }} title={t("記買入")}
                            onClick={() => ask(watch
                              ? t("「{name}」是觀察倉,我想登記買入轉為持倉:請追問數量、成交價、手續費、賬戶和日期後執行", { name: a.name })
                              : t("我買入了「{name}」({sym}),請追問數量、成交價/總額、手續費、支付賬戶和日期,然後登記並記賬", { name: a.name, sym }))}>{t("買")}</button>
                          {!watch && <button className="btn sm" style={{ padding: "0 9px" }} title={t("記賣出")}
                            onClick={() => ask(t("我賣出了「{name}」({sym}),請追問數量、成交價/總額、手續費、收款賬戶和日期,計算已實現盈虧並記賬", { name: a.name, sym }))}>{t("賣")}</button>}
                          {!watch && <button className="btn sm" style={{ padding: "0 9px" }} title={t("記分紅")}
                            onClick={() => ask(t("「{name}」有分紅/派息,請追問金額、稅費、到賬賬戶和日期,登記並記賬", { name: a.name }))}>{t("息")}</button>}
                          <button className="btn sm" style={{ padding: "0 8px" }} title={t("深度解讀")}
                            onClick={() => ask(t("請對「{name}」({sym})做深度解讀:先查最新行情與走勢,再跑量化與風險分析,用人話講結論和風險", { name: a.name, sym }))}><I name="sparkle" size={12}/></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!list.length && <EM icon="search" title={t("當前篩選下沒有資產")} sub={t("換個範圍,或直接吩咐秘書。")}/>}
            <div className="muted" style={{ fontSize: 10.5, marginTop: 12 }}>{t("行情僅供參考,不構成投資建議 · 買賣分紅自動生成記賬憑證,可在財務模塊查賬")}</div>
          </div>
          {sel && <AssetDrawer a={sel} onClose={() => setSel(null)}/>}
        </div>
      </>)}
    </Band>
    </>)}

    {/* ═══ 二 · 數字資產(托管登記冊)═══ */}
    {tab === "dig" && (<>
    <div className="kpi-band">
      <Kpi label={t("托管資產")} value={dSumAssets != null ? dSumAssets : dRows.length} unit={t("項")} delay={0}
        foot={gradeDist
          ? <span className="muted num" style={{ fontSize: 11.5 }}>{t("評估分佈 {d}", { d: gradeDist })}</span>
          : <span className="muted" style={{ fontSize: 11.5 }}>{t("未評估")}</span>}/>
      <Kpi label={t("托管工作區")} value={fin(DS.workspaces) ? DS.workspaces : "—"} unit={t("個")} delay={.05}
        foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("確權 → 托管 → 評估 → 上架 · 站點與數據庫由平台托管").split(" · ")[0]}</span>}/>
      <Kpi label={t("估值總額")} value={kfmt(DS.latest_valuation_total_cny)[0]} unit={kfmt(DS.latest_valuation_total_cny)[1]} delay={.1}
        foot={<span className="muted num" style={{ fontSize: 11.5 }}>{fin(DS.latest_valuation_total_cny) && Number(DS.latest_valuation_total_cny) > 0 ? cny(DS.latest_valuation_total_cny) : "—"}</span>}/>
      <Kpi label={t("已上架")} value={dSumListed != null ? dSumListed : "—"} unit={t("檔")} delay={.15}
        foot={ownLive.length
          ? <span className="muted" style={{ fontSize: 11.5 }}>{t("本公司在售 {n} 檔", { n: ownLive.length })}</span>
          : <button className="tag inv" style={{ cursor: "pointer" }} onClick={() => ask(t("我想把一項數字資產上架交易:請列出已登記資產讓我選,先出 AI 評估與合規預審,再和我確定權益類型與定價,確認後上架"))}>{t("讓秘書上架 →")}</button>}/>
    </div>

    <Band no="01" title={t("數字資產 · 托管")} sub={t("確權 → 托管 → 評估 → 上架 · 站點與數據庫由平台托管")} delay={.1}
      right={<B size="sm" icon="plus" onClick={onboardPrompt}>{t("接入新資產")}</B>}>
      {!dRows.length ? (
        <EM icon="cpu" title={t("還沒有托管的數字資產")} sub={t("對秘書說「幫我接入第一個數字資產」,開通工作區或登記現有能力即可開始。")}
          action={<B icon="sparkle" size="sm" onClick={onboardPrompt}>{t("讓秘書接入")}</B>}/>
      ) : (<>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th style={{ width: 34 }}>#</th><th>{t("資產")}</th><th>{t("托管")}</th><th>{t("AI 評估")}</th><th>{t("估值")}</th><th>{t("上架")}</th><th>{t("時間")}</th><th style={{ width: 118 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {dRows.map((a, i) => {
                  const ws = a.workspace || null;
                  const url = wsHref(ws);
                  const as = dAssess(a);
                  const score = assessScore(as);
                  const listed = a.status === "listed" || num(a.listings_count) > 0;
                  const val = a.latest_valuation;
                  return (
                    <tr key={a.id || i} className={dsel && dsel.id === a.id ? "on" : ""} style={{ cursor: "pointer" }} onClick={() => setDsel(a)}>
                      <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                      <td>
                        <div className="col g4" style={{ minWidth: 0 }}>
                          <span className="row g8" style={{ fontWeight: 650 }}>{a.name || "—"}<T tone="plain">{t(DKIND_L[a.asset_kind] || a.kind_label || "其他")}</T></span>
                          <span className="num muted" style={{ fontSize: 11 }}>{a.asset_no || "—"}{a.lifecycle_stage ? " · " + t(DSTAGE_L[a.lifecycle_stage] || a.lifecycle_stage) : ""}</span>
                        </div>
                      </td>
                      <td>
                        {ws ? (
                          <div className="col g2" style={{ minWidth: 0 }}>
                            <span className="num" style={{ fontSize: 11.5, fontWeight: 600 }}>{ws.workspace_key || "—"}</span>
                            {url && (
                              <a href={url} target="_blank" rel="noopener noreferrer" className="num" onClick={e => e.stopPropagation()}
                                style={{ fontSize: 10.5, color: "var(--ink)", textDecoration: "underline", textUnderlineOffset: 3 }}>
                                {t("訪問站點")} ↗
                              </a>
                            )}
                          </div>
                        ) : <span className="muted" style={{ fontSize: 11.5 }}>{t("未托管")}</span>}
                      </td>
                      <td>{as && as.grade
                        ? <T tone={gradeTone(as.grade)}>AI·{as.grade}{score != null ? " · " + score : ""}</T>
                        : <span className="muted" style={{ fontSize: 11.5 }}>{t("未評估")}</span>}</td>
                      <td className="num" style={{ fontWeight: 650 }}>{val && fin(val.valuation_cny) ? cny(val.valuation_cny) : <span className="muted" style={{ fontWeight: 400, fontSize: 11.5 }}>{t("未估值")}</span>}</td>
                      <td>{a.status === "archived" ? <T tone="plain">{t("已歸檔")}</T> : listed ? <T tone="ok" dot>{t("在售")}</T> : <T tone="plain">{t("未上架")}</T>}</td>
                      <td className="num muted" style={{ fontSize: 11 }}>{((a.updated_at || a.created_at) || "").slice(0, 10) || "—"}</td>
                      <td onClick={e => e.stopPropagation()}>
                        <div className="row g4">
                          <button className="btn sm" style={{ padding: "0 9px" }} title={t("評估資產")}
                            onClick={() => ask(t("幫我評估數字資產「{name}」(#{id}):出 AI 評估報告,講清等級、分數、關鍵證據、風險旗標和建議定價區間", { name: a.name || "—", id: a.id ?? "—" }))}>{t("評")}</button>
                          <button className="btn sm" style={{ padding: "0 9px" }} title={t("上架到市場")}
                            onClick={() => ask(t("把數字資產「{name}」(#{id})上架到市場:先出 AI 評估與合規預審,再和我確定權益類型、定價與份額,確認後上架", { name: a.name || "—", id: a.id ?? "—" }))}>{t("架")}</button>
                          <button className="btn sm" style={{ padding: "0 8px" }} title={t("訪問與收入")}
                            onClick={() => ask(t("看看數字資產「{name}」(#{id})的訪問與收入情況:站點訪問、接口調用、成交與收益分潤都查一遍,匯總成結論講給我", { name: a.name || "—", id: a.id ?? "—" }))}><I name="sparkle" size={12}/></button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {dsel && <DigitalDrawer a={dsel} assess={dAssess(dsel)} onClose={() => setDsel(null)}/>}
        </div>
      </>)}
    </Band>
    </>)}

    {/* ═══ 三 · 交易中心(市場 + 成交 + 分潤)═══ */}
    {tab === "trade" && (<>
    <div className="kpi-band">
      <Kpi label={t("共同市場在售")} value={live.length} unit={t("檔")} delay={0}
        foot={live.length
          ? <span className="muted" style={{ fontSize: 11.5 }}>{t("數字資產可上架交易")}</span>
          : <button className="tag inv" style={{ cursor: "pointer" }} onClick={() => ask(t("我想把一項數字資產上架交易:請列出已登記資產讓我選,先出 AI 評估與合規預審,再和我確定權益類型與定價,確認後上架"))}>{t("讓秘書上架 →")}</button>}/>
      <Kpi label={t("累計成交")} value={trdV} unit={trdU} delay={.05}
        foot={<span className="muted" style={{ fontSize: 11.5 }}>{tradeRows.length ? t("{n} 筆", { n: fin(trades && trades.trade_count) ? trades.trade_count : tradeRows.length }) : t("暫無成交")}</span>}/>
      <Kpi label={t("累計分潤")} value={distV} unit={distU} delay={.1}
        foot={<span className="muted num" style={{ fontSize: 11.5 }}>{fin(distTotal) && Number(distTotal) > 0 ? cny(distTotal) : "—"}</span>}/>
      <Kpi label={t("待跟進")} value={followUpKnown ? followUp : "—"} unit={t("項")} red={followUpKnown && followUp > 0} delay={.15}
        foot={!followUpKnown
          ? <span className="muted num" style={{ fontSize: 11.5 }}>—</span>
          : followUp > 0
          ? <span className="muted" style={{ fontSize: 11.5 }}>{disputedTrades > 0
              ? t("待驗收 {n} · 爭議 {d} · 待付分潤 {m}", { n: pendingTrades, d: disputedTrades, m: unpaidDist })
              : t("待驗收 {n} · 待付分潤 {m}", { n: pendingTrades, m: unpaidDist })}</span>
          : <T tone="ok" dot>{t("全部妥當")}</T>}/>
    </div>

    <Band no="01" title={t("共同市場")} sub={t("只顯示 visibility=public 且 listed 的跨公司上架 · 條款鋼印 · 擔保交付")} delay={.2}
      right={<B size="sm" icon="sparkle" onClick={() => ask(t("我想把一項數字資產上架交易:請列出已登記資產讓我選,先出 AI 評估與合規預審,再和我確定權益類型與定價,確認後上架"))}>{t("上架諮詢")}</B>}>
      {!live.length ? (
        <EM icon="layers" title={t("市場虛位以待")} sub={t("確權 → 估值 → 合規 → 上架,秘書全程代辦。")}
          action={<B icon="sparkle" size="sm" onClick={() => ask(t("我想把一項數字資產上架交易:請列出已登記資產讓我選,先出 AI 評估與合規預審,再和我確定權益類型與定價,確認後上架"))}>{t("交給秘書上架")}</B>}/>
      ) : (
        <div style={{ overflowX: "auto" }}>
          <table className="tbl2">
            <thead><tr>
              <th style={{ width: 34 }}>#</th><th>{t("上架")}</th><th>{t("權益")}</th><th>{t("AI 評估")}</th><th>{t("單價")}</th><th>{t("剩餘")}</th><th>{t("已售")}</th><th style={{ width: 150 }}>{t("交給秘書")}</th>
            </tr></thead>
            <tbody>
              {live.map((l, i) => {
                const as = l.assessment;
                const soldPct = fin(l.units_offered) && Number(l.units_offered) > 0
                  ? Math.min(100, Math.round(100 * (Number(l.units_sold) || 0) / Number(l.units_offered))) : null;
                return (
                  <tr key={l.id || i}>
                    <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                    <td>
                      <div className="col g4" style={{ minWidth: 0 }}>
                        <span style={{ fontWeight: 650 }}>{t("《{ti}》", { ti: l.title || "—" })}</span>
                        <span className="num muted" style={{ fontSize: 11 }}>{l.ref ? l.ref + " · " : ""}{l.company || l.tenant_slug || "—"} · {l.asset_name || "—"}</span>
                      </div>
                    </td>
                    <td><T tone="plain">{t(RIGHT_L[l.listing_type] || l.listing_type || "—")}</T></td>
                    <td>{as && as.grade
                      ? <T tone="inv">AI·{as.grade}{fin(as.overall_score) ? " · " + as.overall_score : (fin(as.score) ? " · " + as.score : "")}</T>
                      : <span className="muted" style={{ fontSize: 11.5 }}>{t("未評估")}</span>}</td>
                    <td className="num" style={{ fontWeight: 700 }}>{fin(l.price_cny) ? cny(l.price_cny) : t("面議")}</td>
                    <td className="num">{l.units_remaining == null ? t("不限") : t("{n} 份", { n: nfmt(l.units_remaining) })}</td>
                    <td>
                      {soldPct == null ? <span className="muted" style={{ fontSize: 11 }}>—</span>
                        : <div className="col g4" style={{ width: 90 }}>
                            <div className="bar"><i style={{ width: soldPct + "%", background: "var(--ink)" }}/></div>
                            <span className="num muted" style={{ fontSize: 10 }}>{soldPct}%</span>
                          </div>}
                    </td>
                    <td>
                      <div className="row g4">
                        <button className="btn sm" onClick={() => askListing(l, false)}>{t("詳情")}</button>
                        <button className="btn sm" onClick={() => askListing(l, true)}><I name="sparkle" size={11}/>{t("購買")}</button>
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

    <Band no="02" title={t("成交與分潤")}
      sub={fin(trades && trades.total_amount_cny) && Number(trades.total_amount_cny) > 0 ? t("累計 {v}", { v: cny(trades.total_amount_cny) }) : null} delay={.25}
      right={<B size="sm" icon="plus" onClick={() => ask(t("我要登記一筆數字資產收益並分潤:請追問是哪個資產、金額、收益來源,登記後把每位持有人的分潤明細列給我"))}>{t("記一筆收益")}</B>}>
      <div style={{ display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: 0 }}>
        <div style={{ paddingRight: 28 }}>
          <div className="row spread" style={{ borderBottom: "2px solid var(--rule)", paddingBottom: 8 }}>
            <LB>{t("最近成交")}</LB>
            <span className="num muted" style={{ fontSize: 11 }}>{tradeRows.length}</span>
          </div>
          {!tradeRows.length && <div className="muted" style={{ fontSize: 12, padding: "16px 0" }}>{t("暫無成交。結算後自動出現在這裡。")}</div>}
          {[...tradeRows].sort((a, b) =>
            ((a && (a.acceptance_status === "pending" || a.acceptance_status === "disputed")) ? 0 : 1)
            - ((b && (b.acceptance_status === "pending" || b.acceptance_status === "disputed")) ? 0 : 1)
          ).slice(0, 8).map((tr, i) => {
            const st = ACCEPT_L[tr.acceptance_status];
            return (
              <div key={tr.id || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontWeight: 650, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {tr.asset_name || "—"}{t("《{ti}》", { ti: tr.listing_title || "—" })}{fin(tr.units) ? " × " + nfmt(tr.units) : ""}
                  </span>
                  <span className="muted num" style={{ fontSize: 11 }}>
                    {t("買方 {c}", { c: tr.counterparty_name || "—" })} · {(tr.settled_at || tr.created_at || "").slice(0, 10) || "—"}
                    {tr.voucher_id ? " · " + t("憑證 #{n}", { n: tr.voucher_id }) : ""}
                  </span>
                </div>
                {st && <T tone={tr.acceptance_status === "disputed" ? "bad" : tr.acceptance_status === "accepted" ? "ok" : "plain"} dot={tr.acceptance_status === "disputed"}>{t(st)}</T>}
                <span className="num" style={{ fontWeight: 700 }}>{cny(tr.amount_cny)}</span>
                <button className="btn sm" style={{ padding: "0 8px" }} title={t("問秘書")}
                  onClick={() => ask(t("成交 #{id}「{a}」《{ti}》× {u},買方 {c},金額 {amt}:請查交付與驗收狀態,需要我跟進的列出來",
                    { id: tr.id || "—", a: tr.asset_name || "—", ti: tr.listing_title || "—", u: nfmt(tr.units), c: tr.counterparty_name || "—", amt: cny(tr.amount_cny) }))}>
                  <I name="sparkle" size={12}/>
                </button>
              </div>
            );
          })}
        </div>
        <div style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
          <div className="row spread" style={{ borderBottom: "2px solid var(--rule)", paddingBottom: 8 }}>
            <LB>{t("收益與分潤")}</LB>
            {fin(distTotal) && Number(distTotal) > 0 && <span className="num muted" style={{ fontSize: 11 }}>{t("已分潤")} {cny(distTotal)}</span>}
          </div>
          {!revRows.length && <div className="muted" style={{ fontSize: 12, padding: "16px 0" }}>{t("暫無收益事件。")}</div>}
          {[...revRows].sort((a, b) => (isUnpaidEv(a) ? 0 : 1) - (isUnpaidEv(b) ? 0 : 1)).slice(0, 8).map((ev, i) => {
            const alloc = ev.allocation || {};
            const hasAlloc = Array.isArray(alloc.allocations) && alloc.allocations.length > 0;
            return (
              <div key={ev.id || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span className="row g8" style={{ fontWeight: 650, fontSize: 13 }}>
                    <T tone={ev.event_type === "cost" ? "warn" : "plain"}>{t(EVENT_L[ev.event_type] || ev.event_type || "收入")}</T>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ev.asset_name || "—"}</span>
                  </span>
                  <span className="muted num" style={{ fontSize: 11 }}>{(ev.created_at || "").slice(0, 10) || "—"}{ev.source_ref ? " · " + ev.source_ref : ""}</span>
                </div>
                {hasAlloc && (alloc.paid ? <T tone="ok" dot>{t("已分潤")}</T> : <T tone="bad" dot>{t("待付分潤")}</T>)}
                <span className="num" style={{ fontWeight: 700, color: ev.event_type === "cost" ? "var(--red)" : "var(--ink)" }}>{cny(ev.amount_cny)}</span>
                <button className="btn sm" style={{ padding: "0 8px" }} title={t("問秘書")}
                  onClick={() => ask(t("收益事件 #{id}({a},{ty},{amt}):請帶出分潤明細與支付狀態,未付的列出應付名單",
                    { id: ev.id || "—", a: ev.asset_name || "—", ty: t(EVENT_L[ev.event_type] || ev.event_type || "收入"), amt: cny(ev.amount_cny) }))}>
                  <I name="sparkle" size={12}/>
                </button>
              </div>
            );
          })}
        </div>
      </div>
    </Band>
    </>)}
  </>);
};

window.W2.PAGES["assets"] = Page;
})();
