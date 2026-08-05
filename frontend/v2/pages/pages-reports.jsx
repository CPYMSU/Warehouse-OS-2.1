/* WAREHOUSE 2.1 · 報表 — Swiss 版式,真後端(/api/reports/summary) */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "報表": "Reports",
  "經營報表駕駛艙 · 出入庫走勢 · 儲值與消耗 · 頁面只讀,生成與導出交秘書":
    "Business reporting cockpit · in/out trends · value & consumption · read-only, generation and export via Secretary",
  "導出匯總 CSV": "Export summary CSV",
  "問秘書": "Ask Secretary",
  "刷新": "Refresh",
  "正在從資料庫計算報表…": "Computing reports from the database…",
  "COMPUTING": "COMPUTING",
  "暫無數據": "No data yet",
  // KPI(後端中文 key)
  "本期入庫": "Inbound orders", "本期出庫": "Outbound orders",
  "庫存總儲值": "Total stock value", "緊急搶修單": "Urgent repair orders",
  "單": "", "件": "", "萬": "×10k", "按單價估算": "by unit price", "本期": "this period",
  "{n} 件": "{n} pcs",
  // 走勢
  "出入庫走勢": "In / out trend", "單據量 · 按月": "Orders per month",
  "近 6 月": "Last 6 mo", "全週期": "All time",
  "入庫": "Inbound", "出庫": "Outbound",
  "還沒有出入庫流水": "No in/out records yet",
  "產生單據後,月度走勢會出現在這裡。": "Monthly trends will appear here once orders exist.",
  // 儲值分佈
  "庫存儲值分佈": "Stock value by category", "總儲值": "Total value",
  "暫無帶單價的庫存資料": "No priced stock data yet",
  "對秘書說「幫物資補上單價」,儲值分析就會出現。": "Tell the Secretary to fill in unit prices and this analysis will appear.",
  // 消耗
  "物資消耗 TOP 5": "Top 5 consumed items", "出庫 / 領用數量排行": "by outbound / requisition quantity",
  "分析消耗結構": "Analyze consumption",
  "暫無出庫消耗資料": "No consumption data yet",
  "有出庫或領用後,排行自動生成。": "The ranking builds itself once outbound activity exists.",
  // 預警與週轉
  "預警處理與週轉": "Alerts & turnover", "AI 掃描 · 人工拍板": "AI scans · humans decide",
  "處理率": "Handled rate", "累計預警": "Total alerts", "已處理": "Handled",
  "待歸還": "Pending returns", "庫存週轉率": "Stock turnover", "逐條處置": "Handle each",
  // 報表目錄
  "報表目錄": "Report catalogue", "1.0 全部報表 · 生成與導出交秘書": "All 1.0 reports · generate & export via Secretary",
  "月度出入庫匯總表": "Monthly in/out summary",
  "庫存儲值與週轉分析": "Stock value & turnover analysis",
  "物資消耗排行": "Consumption ranking",
  "未關閉預警清單": "Open alerts list",
  "全部入庫與出庫單據流水,含物資、數量與時間,按月匯總。": "Every inbound and outbound order line with item, quantity and time, summarized by month.",
  "按分類統計庫存儲值,配合週轉率看資金佔用是否健康。": "Stock value by category, with turnover rate to judge capital efficiency.",
  "出庫與領用數量排行,找出消耗最快、最該盯緊的物資。": "Ranking by outbound and requisition quantity — the items burning fastest.",
  "全部未關閉預警與處置建議,含待歸還工器具。": "All open alerts with suggested actions, including tools pending return.",
  "業務": "OPS", "財務": "FIN", "安全": "SAFETY", "月報": "MONTHLY", "週報": "WEEKLY",
  "秘書生成導出": "Generate & export", "問要點": "Key points", "關鍵數字": "Key figure",
  "入庫 {a} 單 · 出庫 {b} 單": "In {a} · Out {b}", "週轉": "turnover",
  "{n} 條未關閉": "{n} open",
  "2.1 約定:頁面只讀,報表由秘書按最新數據生成與導出,全程留痕。":
    "2.1 covenant: the page is read-only. Reports are generated and exported by the Secretary from live data, fully audited.",
  // 秘書指令
  "把本期經營報表的要點講給我聽:出入庫、庫存儲值、消耗排行、預警處理,各給關鍵數字和一句判斷":
    "Walk me through this period's reports: in/out, stock value, consumption ranking, alert handling — key figures plus one-line verdicts",
  "生成本期出入庫匯總表,整理成表格給我,並導出 CSV":
    "Generate this period's in/out summary as a table and export it to CSV",
  "分析本期物資消耗結構:哪些消耗最快、是否合理、要不要調整安全庫存":
    "Analyze consumption structure: what burns fastest, is it reasonable, should safety stocks change",
  "把未關閉的預警和待歸還工器具逐條列出,給出處置建議,經我確認後執行":
    "List every open alert and pending tool return with suggested actions; execute after my confirmation",
  "生成「{name}」({cycle}),先用表格把要點給我,再導出 CSV":
    "Generate \"{name}\" ({cycle}): show key points as a table first, then export CSV",
  "「{name}」這份報表,直接把本期要點和異常講給我":
    "For \"{name}\": give me this period's key points and anomalies directly",
});
const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, StackBar, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);
/* 後端動態文案(如「123 件」)的可譯處理:數字+單位拆開走 {n} 詞條 */
const tExtra = (x) => {
  const m = /^(\d+(?:\.\d+)?)\s*件$/.exec(String(x));
  return m ? t("{n} 件", { n: m[1] }) : t(x);
};

/* ── 報表目錄(1.0 exportable 的說明與圖標;後端返回時以後端名單為準)── */
const CATALOG = [
  { name: "月度出入庫匯總表", type: "業務", cycle: "月報", icon: "swap",
    desc: "全部入庫與出庫單據流水,含物資、數量與時間,按月匯總。" },
  { name: "庫存儲值與週轉分析", type: "財務", cycle: "月報", icon: "wallet",
    desc: "按分類統計庫存儲值,配合週轉率看資金佔用是否健康。" },
  { name: "物資消耗排行", type: "業務", cycle: "月報", icon: "trend",
    desc: "出庫與領用數量排行,找出消耗最快、最該盯緊的物資。" },
  { name: "未關閉預警清單", type: "安全", cycle: "週報", icon: "alert",
    desc: "全部未關閉預警與處置建議,含待歸還工器具。" },
];

/* ── 分組柱狀圖(Swiss:矩形、無圓角,墨=入庫 / 灰=出庫)── */
const Bars2 = ({ labels, a, b }) => {
  const H = 150;
  const max = Math.max(1, ...a.map(num), ...b.map(num));
  const hOf = (v) => { const n = num(v); return n > 0 ? Math.max(3, Math.round(n / max * H)) : 1; };
  return (
    <div style={{ overflowX: "auto", paddingTop: 6 }}>
      <div className="row" style={{ alignItems: "flex-end", minWidth: Math.max(280, labels.length * 46) }}>
        {labels.map((lb, i) => (
          <div key={i} className="col" style={{ flex: 1, alignItems: "center", gap: 7, padding: "0 4px" }}>
            <div className="row" style={{ gap: 3, alignItems: "flex-end", height: H, borderBottom: "1px solid var(--hair)", width: "100%", justifyContent: "center" }}>
              <i title={t("入庫") + " " + num(a[i])} style={{ display: "block", width: 11, height: hOf(a[i]), background: "var(--ink)" }}/>
              <i title={t("出庫") + " " + num(b[i])} style={{ display: "block", width: 11, height: hOf(b[i]), background: "#85806F" }}/>
            </div>
            <span className="num muted" style={{ fontSize: 10 }}>{lb}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
const LegendSq = ({ color, label }) => (
  <span className="row g6" style={{ fontSize: 11.5, color: "var(--ink-2)" }}>
    <span style={{ width: 9, height: 9, background: color, flexShrink: 0 }}/>{label}
  </span>
);

const Page = ({ boot }) => {
  const [data, setData] = _s(null);
  const [rng, setRng] = _s("m6");
  const [tick, setTick] = _s(0);
  _e(() => {
    let alive = true;
    W2.json("/api/reports/summary").then(d => alive && setData(d && typeof d === "object" ? d : {})).catch(() => alive && setData({}));
    return () => { alive = false; };
  }, [tick]);

  const d = data || {};
  /* KPI:後端數組;缺失時退回固定四格(值 —) */
  const kpisRaw = Array.isArray(d.kpis) && d.kpis.length ? d.kpis
    : [{ key: "本期入庫", unit: "單" }, { key: "本期出庫", unit: "單" }, { key: "庫存總儲值", unit: "萬" }, { key: "緊急搶修單", unit: "單" }];
  const kpis = kpisRaw.slice(0, 4);
  const kByKey = {};
  kpis.forEach(k => { if (k && k.key) kByKey[k.key] = k; });

  /* 走勢 */
  const tr = d.trend && typeof d.trend === "object" ? d.trend : {};
  const tLabels = Array.isArray(tr.labels) ? tr.labels : [];
  const tIn = Array.isArray(tr.inbound) ? tr.inbound : [];
  const tOut = Array.isArray(tr.outbound) ? tr.outbound : [];
  const hasTrend = tLabels.length > 0 && (tIn.some(v => num(v) > 0) || tOut.some(v => num(v) > 0));
  const cut = rng === "m6" ? 6 : tLabels.length;
  const vLabels = tLabels.slice(-cut), vIn = tIn.slice(-cut), vOut = tOut.slice(-cut);

  /* 儲值分佈(顏色統一映射到 Swiss 圖表色) */
  const dist = (Array.isArray(d.value_dist) ? d.value_dist : []).filter(x => x && num(x.value) > 0);
  const totalVal = dist.reduce((s, x) => s + num(x.value), 0);
  const stack = dist.map((x, i) => ({ value: num(x.value), color: W2.CHART_COLORS[i % W2.CHART_COLORS.length], label: x.label || "—" }));

  /* 消耗 Top */
  const top = (Array.isArray(d.top_consume) ? d.top_consume : []).filter(x => x && x.name);
  const topMax = top.reduce((m, x) => Math.max(m, num(x.value)), 0) || 1;

  /* 預警統計與週轉 */
  const as = d.alert_stats && typeof d.alert_stats === "object" ? d.alert_stats : {};
  const aTotal = num(as.total), aHandled = num(as.handled);
  const aRate = as.rate != null ? num(as.rate) : (aTotal ? Math.round(aHandled / aTotal * 100) : 0);
  const aPending = num(as.pending_returns);
  const turnover = d.turnover != null ? d.turnover : null;
  const bootAlerts = Array.isArray(boot && boot.ALERTS) ? boot.ALERTS.length : 0;
  const openAlerts = d.alert_stats ? Math.max(0, aTotal - aHandled) : bootAlerts;

  /* 報表目錄:後端 exportable 為準,補上本地說明;缺失時退回固定四份 */
  const exportable = Array.isArray(d.exportable) && d.exportable.length ? d.exportable : CATALOG;
  const figOf = (name) => {
    if (name === "月度出入庫匯總表") {
      const a = kByKey["本期入庫"], b = kByKey["本期出庫"];
      return (a && a.value != null) || (b && b.value != null)
        ? t("入庫 {a} 單 · 出庫 {b} 單", { a: a && a.value != null ? a.value : "—", b: b && b.value != null ? b.value : "—" }) : "—";
    }
    if (name === "庫存儲值與週轉分析")
      return totalVal > 0 ? "¥" + totalVal.toFixed(1) + t("萬") + (turnover != null ? " · " + t("週轉") + " " + turnover : "") : "—";
    if (name === "物資消耗排行") return top.length ? "TOP1 · " + top[0].name : "—";
    if (name === "未關閉預警清單") return t("{n} 條未關閉", { n: openAlerts });
    return "—";
  };
  const reports = exportable.map(r => {
    const meta = CATALOG.find(c => c.name === (r && r.name)) || {};
    return { name: (r && r.name) || "—", type: (r && r.type) || meta.type || "業務",
      cycle: (r && r.cycle) || meta.cycle || "月報", icon: meta.icon || "doc",
      desc: meta.desc || "", fig: figOf(r && r.name) };
  });

  const folio = (
    <Folio no="12" en="REPORTS" title={t("報表")}
      sub={t("經營報表駕駛艙 · 出入庫走勢 · 儲值與消耗 · 頁面只讀,生成與導出交秘書")}
      right={<>
        <B icon="refresh" onClick={() => { setData(null); setTick(v => v + 1); }}>{t("刷新")}</B>
        <B icon="doc" onClick={() => ask(t("生成本期出入庫匯總表,整理成表格給我,並導出 CSV"))}>{t("導出匯總 CSV")}</B>
        <B kind="primary" icon="sparkle" onClick={() => ask(t("把本期經營報表的要點講給我聽:出入庫、庫存儲值、消耗排行、預警處理,各給關鍵數字和一句判斷"))}>{t("問秘書")}</B>
      </>}/>
  );

  if (data === null) return (<>
    {folio}
    <div className="col g10 rise" style={{ padding: "72px 0", alignItems: "center" }}>
      <LB dim>{t("COMPUTING")}</LB>
      <div className="muted" style={{ fontSize: 13 }}>{t("正在從資料庫計算報表…")}</div>
    </div>
  </>);

  return (<>
    {folio}

    <div className="kpi-band">
      {kpis.map((k, i) => {
        const red = (k.key === "緊急搶修單") && num(k.value) > 0;
        return (
          <Kpi key={k.key || i} label={t(k.key || "—")} value={k.value != null ? k.value : "—"}
            unit={k.unit ? t(k.unit) : ""} red={red} delay={i * .05}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{k.extra ? tExtra(k.extra) : t("暫無數據")}</span>}/>
        );
      })}
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 0 }}>
      <Band no="A" title={t("出入庫走勢")} sub={t("單據量 · 按月")} delay={.1}
        right={<div className="row g14">
          <LegendSq color="var(--ink)" label={t("入庫")}/>
          <LegendSq color="#85806F" label={t("出庫")}/>
          <div className="seg">
            {[["m6", "近 6 月"], ["all", "全週期"]].map(([id, label]) => (
              <button key={id} className={rng === id ? "on" : ""} onClick={() => setRng(id)}>{t(label)}</button>
            ))}
          </div>
        </div>}>
        <div style={{ paddingRight: 28 }}>
          {hasTrend
            ? <Bars2 labels={vLabels} a={vIn} b={vOut}/>
            : <EM icon="chart" title={t("還沒有出入庫流水")} sub={t("產生單據後,月度走勢會出現在這裡。")}/>}
        </div>
      </Band>

      <Band no="B" title={t("庫存儲值分佈")} sub={totalVal > 0 ? t("總儲值") + " ¥" + totalVal.toFixed(1) + t("萬") : t("暫無數據")} delay={.15}>
        {stack.length ? (
          <div className="col g16" style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
            <StackBar data={stack}/>
            <div className="col g8">
              {stack.map(x => (
                <div key={x.label} className="row g10" style={{ fontSize: 12.5 }}>
                  <span style={{ width: 10, height: 10, background: x.color, flexShrink: 0 }}/>
                  <span className="ink2" style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{x.label}</span>
                  <span className="num" style={{ fontWeight: 700 }}>¥{x.value.toFixed(1)}{t("萬")}</span>
                  <span className="muted num" style={{ fontSize: 11, width: 34, textAlign: "right" }}>{totalVal ? Math.round(x.value / totalVal * 100) : 0}%</span>
                </div>
              ))}
            </div>
          </div>
        ) : <EM icon="wallet" title={t("暫無帶單價的庫存資料")} sub={t("對秘書說「幫物資補上單價」,儲值分析就會出現。")}/>}
      </Band>
    </div>

    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 0 }}>
      <Band no="C" title={t("物資消耗 TOP 5")} sub={t("出庫 / 領用數量排行")} delay={.2}
        right={!!top.length && <B size="sm" icon="sparkle" onClick={() => ask(t("分析本期物資消耗結構:哪些消耗最快、是否合理、要不要調整安全庫存"))}>{t("分析消耗結構")}</B>}>
        {top.length ? (
          <div style={{ borderTop: "2px solid var(--rule)", paddingRight: 28 }}>
            {top.slice(0, 5).map((x, i) => (
              <div key={x.name || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <span style={{ flex: 1, minWidth: 0, fontWeight: 650, fontSize: 13.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{x.name}</span>
                <div className="bar" style={{ width: 170 }}>
                  <i style={{ width: Math.min(100, num(x.value) / (num(x.max) || topMax) * 100) + "%", background: i === 0 ? "var(--ink)" : "#85806F" }}/>
                </div>
                <span className="num" style={{ fontWeight: 700, width: 56, textAlign: "right" }}>{num(x.value)}</span>
              </div>
            ))}
          </div>
        ) : <EM icon="trend" title={t("暫無出庫消耗資料")} sub={t("有出庫或領用後,排行自動生成。")}/>}
      </Band>

      <Band no="D" title={t("預警處理與週轉")} sub={t("AI 掃描 · 人工拍板")} delay={.25}
        right={(openAlerts > 0 || aPending > 0) && <B size="sm" icon="sparkle" onClick={() => ask(t("把未關閉的預警和待歸還工器具逐條列出,給出處置建議,經我確認後執行"))}>{t("逐條處置")}</B>}>
        <div className="col g16" style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
          <div className="row g8" style={{ alignItems: "baseline" }}>
            <span className="num" style={{ fontSize: 46, fontWeight: 700, letterSpacing: "-.04em" }}>{aRate}<span style={{ fontSize: 18 }}>%</span></span>
            <span className="muted" style={{ fontSize: 12 }}>{t("處理率")}</span>
          </div>
          <Meter label={t("已處理")} count={aHandled} total={aTotal} color="var(--ink)"/>
          <div className="col g8">
            {[[t("累計預警"), aTotal, false], [t("已處理"), aHandled, false], [t("待歸還"), aPending, aPending > 0], [t("庫存週轉率"), turnover != null ? turnover : "—", false]].map(([k, v, red]) => (
              <div key={k} className="row spread" style={{ fontSize: 12.5, borderBottom: "1px solid var(--hair-soft)", paddingBottom: 6 }}>
                <span className="ink2">{k}</span>
                <span className="num" style={{ fontWeight: 700, color: red ? "var(--red)" : "var(--ink)" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      </Band>
    </div>

    <Band no="E" title={t("報表目錄")} sub={t("1.0 全部報表 · 生成與導出交秘書")} delay={.3}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 14 }}>
        {reports.map((r, i) => (
          <div key={r.name + i} className="panel rise" style={{ padding: "16px 18px", borderTop: "2px solid var(--rule)", animationDelay: (.3 + i * .05) + "s" }}>
            <div className="row spread" style={{ marginBottom: 8 }}>
              <div className="row g10">
                <I name={r.icon} size={15}/>
                <span style={{ fontWeight: 750, fontSize: 15, letterSpacing: "-.02em" }}>{t(r.name)}</span>
              </div>
              <span className="mono" style={{ fontSize: 11, color: "var(--ink-4)" }}>{pad2(i + 1)}</span>
            </div>
            {r.desc && <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.6, minHeight: 40 }}>{t(r.desc)}</div>}
            <div className="row g10" style={{ margin: "10px 0 14px" }}>
              <T tone={r.type === "安全" ? "warn" : "plain"}>{t(r.type)}</T>
              <LB dim style={{ fontSize: 9 }}>{t(r.cycle)}</LB>
              <span style={{ flex: 1 }}/>
              <span className="num" style={{ fontWeight: 700, fontSize: 12.5 }}>{r.fig}</span>
            </div>
            <div className="row g8">
              <B size="sm" icon="sparkle" onClick={() => ask(t("生成「{name}」({cycle}),先用表格把要點給我,再導出 CSV", { name: t(r.name), cycle: t(r.cycle) }))}>{t("秘書生成導出")}</B>
              <B size="sm" kind="ghost" onClick={() => ask(t("「{name}」這份報表,直接把本期要點和異常講給我", { name: t(r.name) }))}>{t("問要點")}</B>
            </div>
          </div>
        ))}
      </div>
      <div className="muted" style={{ fontSize: 10.5, marginTop: 14, lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,報表由秘書按最新數據生成與導出,全程留痕。")}</div>
    </Band>
  </>);
};

window.W2.PAGES["reports"] = Page;
})();
