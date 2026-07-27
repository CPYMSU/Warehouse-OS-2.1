/* WAREHOUSE 2.0 · 入庫 — Swiss 版式,真後端 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "入庫": "Inbound",
  "本月 {m} 批 · 在管 {n} 張入庫單 · 頁面只讀,操作交秘書": "{m} batches this month · {n} orders on file · read-only, actions go to the secretary",
  "登記到貨": "Register arrival",
  "補單": "Backfill order",
  "問秘書": "Ask secretary",
  "有一批物資到貨了,幫我登記入庫:請先追問入庫類型;若是採購,必須追問已簽發正式 PO ID,並只按 PO 的供應商、幣別、成本與可收明細建單;若是調撥或退庫,再追問內部來源、物資明細與數量": "A batch of goods has arrived. Ask for the inbound type first. For a purchase, require an issued formal PO ID and create the receipt only from the PO's supplier, currency, cost and receivable lines. For transfers or returns, ask for the internal source, item lines and quantities.",
  "之前有一批到貨漏登了,幫我補登入庫:若屬採購,必須先核對已完成工作流、已簽發 PO ID 與尚可收數量,不得用來源單位或自由成本補造採購入庫;內部調撥或退庫再追問到貨時間、來源與明細": "Backfill a missed inbound receipt. For purchases, first verify the completed workflow, issued PO ID and remaining receivable quantity; never fabricate a purchase receipt from a free-form source or cost. For internal transfers or returns, ask for the arrival time, source and lines.",
  "入庫方面現在有什麼要處理的?把待審核、質檢中的單都列出來給我": "What needs attention on the inbound side right now? List all orders pending review or in QC",
  "本月入庫": "Inbound this month",
  "批": "batches",
  "單": "orders",
  "件": "units",
  "待審核": "Pending review",
  "質檢中": "In QC",
  "已入庫": "Received",
  "已取消": "Cancelled",
  "本月入庫件數": "Units received this month",
  "累計 {n} 張入庫單": "{n} inbound orders in total",
  "最近一批 {d}": "Latest batch {d}",
  "尚無入庫記錄": "No inbound records yet",
  "無待審核": "None pending",
  "讓秘書催辦 →": "Have secretary expedite →",
  "把待審核的入庫單逐一列出,幫我跟進催辦": "List every inbound order pending review and help me follow up and expedite them",
  "質檢通道暢通": "QC lane clear",
  "搜索單號 / 來源 / 經辦人 / 物資": "Search order no. / source / handler / item",
  "全部狀態": "All status",
  "全部類型": "All types",
  "採購入庫": "Purchase",
  "調撥入庫": "Transfer-in",
  "退庫": "Return to store",
  "按類型構成": "Mix by type",
  "全部入庫單的類型分佈": "Type distribution of all inbound orders",
  "分析近期入庫按類型與來源的構成,有沒有異常或值得注意的趨勢?": "Analyse the recent inbound mix by type and source. Any anomalies or trends worth noting?",
  "讓秘書分析": "Secretary analysis",
  "還沒有入庫數據": "No inbound data yet",
  "第一批到貨時,對秘書說「登記到貨」即可建單。": "When the first batch arrives, just tell the secretary to register it.",
  "來源單位": "Source units",
  "按單數排序 · 前 {n}": "By order count · top {n}",
  "尚無來源統計": "No source stats yet",
  "入庫單登記後,這裡會呈現供應商與調撥來源的構成。": "Once orders are registered, supplier and transfer-source mix appears here.",
  "入庫單清單": "Inbound orders",
  "{n} 張單": "{n} orders",
  "單號": "Order no.",
  "時間": "Time",
  "類型": "Type",
  "物資明細": "Items",
  "批次": "Batch",
  "經辦人": "Handler",
  "狀態": "Status",
  "交給秘書": "To secretary",
  "{n} 項物資": "{n} items",
  "追查": "Trace",
  "補正": "Amend",
  "追查入庫單「{no}」:來源「{src}」,給我這張單的完整經過、物資明細與關聯庫存變動": "Trace inbound order \"{no}\" from \"{src}\": give me its full history, item lines and related stock movements",
  "入庫單「{no}」需要補充或更正資料,請追問要改哪裡後執行": "Inbound order \"{no}\" needs data added or corrected. Ask me what to change, then apply it",
  "當前篩選下沒有入庫單": "No inbound orders under current filters",
  "換個關鍵詞或狀態,或直接對秘書說「幫我找◯◯的入庫單」。": "Try another keyword or status, or just ask the secretary to find the order.",
  "登記第一批到貨": "Register the first arrival",
  "還沒有入庫單": "No inbound orders yet",
  "採購到貨、調撥入庫、檢修退庫都從這裡留痕。對秘書說一句就能建單。": "Purchase arrivals, transfer-ins and maintenance returns are all recorded here. One sentence to the secretary creates the order.",
  "此單暫無物資明細,可讓秘書補全。": "This order has no item lines yet — the secretary can complete them.",
  "來源": "Source",
  "件數": "Units",
  "庫位": "Location",
  "合格": "Qualified",
  "待檢": "Awaiting QC",
  "不合格": "Rejected",
  "明細 · {n} 項": "Lines · {n}",
  "直接吩咐秘書": "Tell the secretary",
  "追查此單": "Trace this order",
  "補充更正": "Amend data",
  "跟進進度": "Chase progress",
  "同源再入庫": "Repeat inbound",
  "跟進入庫單「{no}」的當前進度(審核/質檢/上架),需要推動就幫我催辦": "Follow up inbound order \"{no}\" (review / QC / put-away). If it is stuck, expedite it for me",
  "入庫單「{no}」的來源「{src}」又有一批到貨:若原單是採購,請核對原正式 PO 及剩餘可收數量後按 PO 收貨;若是內部流轉,才可參照原單來源與明細建新單": "Another batch arrived for inbound order \"{no}\" from \"{src}\". If the original was a purchase, verify the formal PO and remaining receivable quantity and receive against that PO; only internal movements may copy the prior source and lines.",
  "2.0 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.0 rule: pages are read-only; changes run through the secretary with confirmation and a full audit trail.",
});
const { useState: _s, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, StackBar, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 防禦性取值:兼容後端 bootstrap 形狀與舊/簡化形狀 ── */
const ordNo = (r) => String(r.order_no || r.no || r.id || "—");
const ordTime = (r) => String(r.time || r.date || "—");
const ordType = (r) => r.type || "—";
const ordSrc = (r) => r.source || r.supplier || "—";
const ordHandler = (r) => r.handler || r.operator || "—";
const ordLines = (r) => (Array.isArray(r.lines) ? r.lines : []);
const ordUnits = (r) => {
  const ls = ordLines(r);
  if (ls.length) return ls.reduce((s, l) => s + num(l && l.qty), 0);
  return num(r.count) || num(r.qty);
};
const ordDetail = (r) => {
  const ls = ordLines(r);
  if (ls.length) return t("{n} 項物資", { n: ls.length });
  if (r.item) return `${r.item} ×${num(r.qty)} ${r.unit || ""}`.trim();
  return (typeof r.qty === "string" && r.qty) ? r.qty : "—";
};
const ordBatches = (r) => {
  const set = [];
  ordLines(r).forEach(l => { if (l && l.batch && !set.includes(l.batch)) set.push(l.batch); });
  return set;
};
const stKey = (r) => {
  const v = String(r.status || "");
  if (["已入庫", "done", "completed", "confirmed", "已完成"].includes(v)) return "done";
  if (["待審核", "pending", "審核中", "待批"].includes(v)) return "review";
  if (["質檢中", "待質檢", "質檢"].includes(v)) return "qc";
  if (["已取消", "cancelled", "作廢", "已作廢"].includes(v)) return "void";
  return "other";
};
const stTag = (r) => {
  const k = stKey(r);
  if (k === "done") return <T tone="ok" dot>{t("已入庫")}</T>;
  if (k === "review") return <T tone="warn" dot>{t("待審核")}</T>;
  if (k === "qc") return <T tone="warn">{t("質檢中")}</T>;
  if (k === "void") return <T tone="plain">{t("已取消")}</T>;
  return <T tone="plain">{r.status || "—"}</T>;
};
const QTONE = { "合格": "ok", "待檢": "warn", "不合格": "bad" };
const BASE_TYPES = ["採購入庫", "調撥入庫", "退庫"];

const InbDrawer = ({ row, onClose }) => {
  const no = ordNo(row), src = ordSrc(row);
  const lines = ordLines(row);
  const acts = [
    ["search", "追查此單", t("追查入庫單「{no}」:來源「{src}」,給我這張單的完整經過、物資明細與關聯庫存變動", { no, src })],
    ["doc", "補充更正", t("入庫單「{no}」需要補充或更正資料,請追問要改哪裡後執行", { no })],
    ["clock", "跟進進度", t("跟進入庫單「{no}」的當前進度(審核/質檢/上架),需要推動就幫我催辦", { no })],
    ["inbound", "同源再入庫", t("入庫單「{no}」的來源「{src}」又有一批到貨:若原單是採購,請核對原正式 PO 及剩餘可收數量後按 PO 收貨;若是內部流轉,才可參照原單來源與明細建新單", { src, no })],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          {stTag(row)}
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div className="num" style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.02em", lineHeight: 1.25 }}>{no}</div>
        <div className="muted" style={{ fontSize: 11.5, marginTop: 5 }}>{ordType(row)} · {ordTime(row)}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {[[t("來源"), src], [t("經辦人"), ordHandler(row)], [t("件數"), `${ordUnits(row) || "—"}`], [t("批次"), ordBatches(row).join(" · ") || "—"]].map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 14, fontWeight: 650, overflowWrap: "anywhere" }}>{v}</span>
            </div>
          ))}
        </div>
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("明細 · {n} 項", { n: lines.length })}</LB>
        <div style={{ borderTop: "1px solid var(--hair)", marginBottom: 18 }}>
          {lines.length ? lines.map((l, i) => (
            <div key={i} className="ledger-row" style={{ padding: "10px 2px", gap: 12 }}>
              <span className="lr-idx">{pad2(i + 1)}</span>
              <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                <span style={{ fontWeight: 650, fontSize: 13 }}>{(l && l.name) || "—"}</span>
                <span className="muted num" style={{ fontSize: 11 }}>
                  ×{num(l && l.qty)} {(l && l.unit) || ""}
                  {l && l.loc && l.loc !== "—" ? " · " + t("庫位") + " " + l.loc : ""}
                  {l && l.batch ? " · " + t("批次") + " " + l.batch : ""}
                </span>
              </div>
              {l && l.quality ? <T tone={QTONE[l.quality] || "plain"}>{t(l.quality)}</T> : null}
            </div>
          )) : <div className="muted" style={{ fontSize: 12, padding: "12px 0" }}>{t("此單暫無物資明細,可讓秘書補全。")}</div>}
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

const Page = ({ boot }) => {
  const rows = Array.isArray(boot && boot.INBOUND) ? boot.INBOUND : [];
  const [q, setQ] = _s("");
  const [ty, setTy] = _s("all");
  const [st, setSt] = _s("all");
  const [sel, setSel] = _s(null);

  const now = new Date();
  const mPrefix = now.getFullYear() + "-" + pad2(now.getMonth() + 1);
  const monthRows = rows.filter(r => ordTime(r).startsWith(mPrefix));
  const review = rows.filter(r => stKey(r) === "review");
  const qc = rows.filter(r => stKey(r) === "qc");
  const monthUnits = monthRows.reduce((s, r) => s + ordUnits(r), 0);
  const lastTime = rows.map(ordTime).filter(v => v !== "—").sort().pop() || "—";

  const types = _mm(() => {
    const set = [...BASE_TYPES];
    rows.forEach(r => { const v = ordType(r); if (v && v !== "—" && !set.includes(v)) set.push(v); });
    return set;
  }, [rows]);

  const typeStack = _mm(() => types.map((name, i) => ({
    label: name,
    value: rows.filter(r => ordType(r) === name).length,
    color: W2.CHART_COLORS[i % W2.CHART_COLORS.length],
  })).filter(d => d.value > 0), [rows, types]);

  const topSources = _mm(() => {
    const m = {};
    rows.forEach(r => { const s = ordSrc(r); if (s && s !== "—") m[s] = (m[s] || 0) + 1; });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 5);
  }, [rows]);

  let list = rows;
  if (ty !== "all") list = list.filter(r => ordType(r) === ty);
  if (st !== "all") list = list.filter(r => stKey(r) === st);
  if (q) {
    const k = q.toLowerCase();
    list = list.filter(r => (ordNo(r) + " " + ordSrc(r) + " " + ordHandler(r) + " " + ordLines(r).map(l => (l && l.name) || "").join(" ") + " " + (r.item || "")).toLowerCase().includes(k));
  }
  const sorted = _mm(() => [...list].sort((a, b) => ordTime(b).localeCompare(ordTime(a))), [list]);

  const regPrompt = t("有一批物資到貨了,幫我登記入庫:請先追問入庫類型;若是採購,必須追問已簽發正式 PO ID,並只按 PO 的供應商、幣別、成本與可收明細建單;若是調撥或退庫,再追問內部來源、物資明細與數量");

  return (
    <>
      <Folio no="03" en="INBOUND" title={t("入庫")}
        sub={t("本月 {m} 批 · 在管 {n} 張入庫單 · 頁面只讀,操作交秘書", { m: monthRows.length, n: rows.length })}
        right={<>
          <B icon="doc" onClick={() => ask(t("之前有一批到貨漏登了,幫我補登入庫:若屬採購,必須先核對已完成工作流、已簽發 PO ID 與尚可收數量,不得用來源單位或自由成本補造採購入庫;內部調撥或退庫再追問到貨時間、來源與明細"))}>{t("補單")}</B>
          <B icon="inbound" onClick={() => ask(regPrompt)}>{t("登記到貨")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(t("入庫方面現在有什麼要處理的?把待審核、質檢中的單都列出來給我"))}>{t("問秘書")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={t("本月入庫")} value={monthRows.length} unit={t("批")} delay={0}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{lastTime !== "—" ? t("最近一批 {d}", { d: String(lastTime).slice(0, 16) }) : t("尚無入庫記錄")}</span>}/>
        <Kpi label={t("待審核")} value={review.length} unit={t("單")} red={review.length > 0} delay={.05}
          foot={review.length
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把待審核的入庫單逐一列出,幫我跟進催辦"))}>{t("讓秘書催辦 →")}</button>
            : <T tone="ok" dot>{t("無待審核")}</T>}/>
        <Kpi label={t("質檢中")} value={qc.length} unit={t("單")} delay={.1}
          foot={qc.length ? <T tone="warn" dot>{t("質檢中")}</T> : <T tone="plain">{t("質檢通道暢通")}</T>}/>
        <Kpi label={t("本月入庫件數")} value={monthUnits} unit={t("件")} delay={.15}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("累計 {n} 張入庫單", { n: rows.length })}</span>}/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
        <Band no="A" title={t("按類型構成")} sub={t("全部入庫單的類型分佈")} delay={.1}
          right={rows.length ? <B size="sm" icon="sparkle" onClick={() => ask(t("分析近期入庫按類型與來源的構成,有沒有異常或值得注意的趨勢?"))}>{t("讓秘書分析")}</B> : null}>
          {typeStack.length ? (
            <div className="col g16" style={{ paddingRight: 28 }}>
              <StackBar data={typeStack}/>
              <div className="col g8">
                {typeStack.map(d => (
                  <div key={d.label} className="row g10" style={{ fontSize: 12.5 }}>
                    <span style={{ width: 10, height: 10, background: d.color, flexShrink: 0 }}/>
                    <span className="ink2" style={{ flex: 1 }}>{t(d.label)}</span>
                    <span className="num" style={{ fontWeight: 700 }}>{d.value}</span>
                    <span className="muted num" style={{ fontSize: 11 }}>{Math.round(d.value / (rows.length || 1) * 100)}%</span>
                  </div>
                ))}
              </div>
            </div>
          ) : <EM icon="inbound" title={t("還沒有入庫數據")} sub={t("第一批到貨時,對秘書說「登記到貨」即可建單。")}/>}
        </Band>
        <Band no="B" title={t("來源單位")} sub={topSources.length ? t("按單數排序 · 前 {n}", { n: topSources.length }) : ""} delay={.15}>
          {topSources.length ? (
            <div className="col g14" style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
              {topSources.map(([name, count]) => (
                <Meter key={name} label={name} count={count} total={rows.length} color="var(--ink)"/>
              ))}
            </div>
          ) : <EM icon="building" title={t("尚無來源統計")} sub={t("入庫單登記後,這裡會呈現供應商與調撥來源的構成。")}/>}
        </Band>
      </div>

      <Band no="C" title={t("入庫單清單")} sub={t("{n} 張單", { n: sorted.length })} delay={.2}
        right={<div className="row g14 wrap">
          <div style={{ position: "relative", minWidth: 230 }}>
            <I name="search" size={14} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="field" style={{ paddingLeft: 24, height: 32, fontSize: 12.5 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t("搜索單號 / 來源 / 經辦人 / 物資")}/>
          </div>
          <div className="seg">
            {[["all", "全部狀態"], ["done", "已入庫"], ["review", "待審核"], ["qc", "質檢中"]].map(([id, label]) => (
              <button key={id} className={st === id ? "on" : ""} onClick={() => setSt(id)}>{t(label)}</button>
            ))}
          </div>
        </div>}>
        <div className="row g6 wrap" style={{ marginBottom: 14 }}>
          <button className={"chip" + (ty === "all" ? " on" : "")} onClick={() => setTy("all")}>{t("全部類型")}</button>
          {types.map(name => (
            <button key={name} className={"chip" + (ty === name ? " on" : "")} onClick={() => setTy(name)}>{t(name)}</button>
          ))}
        </div>

        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("單號")}</th><th>{t("時間")}</th><th>{t("類型")}</th><th>{t("來源單位")}</th><th>{t("物資明細")}</th><th>{t("批次")}</th><th>{t("經辦人")}</th><th>{t("狀態")}</th><th style={{ width: 90 }}>{t("交給秘書")}</th>
                </tr></thead>
                <tbody>
                  {sorted.map((r, idx) => {
                    const no = ordNo(r);
                    const batches = ordBatches(r);
                    const on = sel && ordNo(sel) === no;
                    return (
                      <tr key={no + ":" + idx} className={on ? "on" : ""} onClick={() => setSel(on ? null : r)} style={{ cursor: "pointer" }}>
                        <td><span className="num" style={{ fontWeight: 700 }}>{no}</span></td>
                        <td><span className="num muted" style={{ fontSize: 12 }}>{ordTime(r)}</span></td>
                        <td><T tone="plain">{t(ordType(r))}</T></td>
                        <td style={{ fontWeight: 550 }}>{ordSrc(r)}</td>
                        <td className="muted" style={{ fontSize: 12.5 }}>{ordDetail(r)}</td>
                        <td><span className="num muted" style={{ fontSize: 12 }}>{batches.length ? batches[0] + (batches.length > 1 ? " +" + (batches.length - 1) : "") : "—"}</span></td>
                        <td>{ordHandler(r)}</td>
                        <td>{stTag(r)}</td>
                        <td onClick={e => e.stopPropagation()}>
                          <div className="row g4">
                            <button className="btn sm" title={t("追查")} style={{ padding: "0 8px" }} onClick={() => ask(t("追查入庫單「{no}」:來源「{src}」,給我這張單的完整經過、物資明細與關聯庫存變動", { no, src: ordSrc(r) }))}><I name="search" size={12}/></button>
                            <button className="btn sm" title={t("補正")} style={{ padding: "0 8px" }} onClick={() => ask(t("入庫單「{no}」需要補充或更正資料,請追問要改哪裡後執行", { no }))}><I name="doc" size={12}/></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!sorted.length && (rows.length
              ? <EM icon="search" title={t("當前篩選下沒有入庫單")} sub={t("換個關鍵詞或狀態,或直接對秘書說「幫我找◯◯的入庫單」。")}/>
              : <EM icon="inbound" title={t("還沒有入庫單")} sub={t("採購到貨、調撥入庫、檢修退庫都從這裡留痕。對秘書說一句就能建單。")}
                  action={<B icon="sparkle" onClick={() => ask(regPrompt)}>{t("登記第一批到貨")}</B>}/>)}
          </div>
          {sel && <InbDrawer row={sel} onClose={() => setSel(null)}/>}
        </div>
      </Band>
    </>
  );
};

window.W2.PAGES["inbound"] = Page;
})();
