/* ============================================================
   AI 財務 — 專業財務駕駛艙(只讀展示)+ 動賬一鍵交給財務秘書
   數據全部來自總賬 GL 端點 /api/erp/gl/*;記賬由後端引擎保證借貸平衡。
   ============================================================ */
const { useState: useFinState, useEffect: useFinEffect } = React;

const FIN_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const FIN = { ink: "#1D1D1F", sub: "#6E6E73", hair: "rgba(29,29,31,0.12)", blue: "#0071E3", green: "#34C759", orange: "#FF9F0A", red: "#FF3B30", indigo: "#5856D6", bg: "#F5F5F7" };

const finJson = async (path) => {
  const res = await (window.authFetch || fetch)(FIN_API_BASE + path);
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.error || res.statusText || "財務數據載入失敗");
  return d;
};
const yuan = (v) => "¥" + Number(v || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const askFin = (prompt) => { if (window.openUnifiedAgent) window.openUnifiedAgent(prompt, { autoAsk: false }); };

const FinCard = ({ title, sub, right, children }) => (
  <div style={{ borderRadius: 10, border: `1px solid ${FIN.hair}`, background: "#fff", padding: 18 }} className="col gap-12">
    <div className="row spread" style={{ alignItems: "flex-start", gap: 10 }}>
      <div className="col gap-2"><div style={{ fontSize: 15, fontWeight: 900, color: FIN.ink }}>{title}</div>{sub && <div style={{ fontSize: 12, color: FIN.sub }}>{sub}</div>}</div>
      {right}
    </div>
    {children}
  </div>
);

const Metric = ({ label, value, tone, hint }) => (
  <div style={{ padding: 14, borderRadius: 10, border: `1px solid ${FIN.hair}`, background: "#fff", minWidth: 0 }}>
    <div style={{ fontSize: 12, color: FIN.sub, marginBottom: 5 }}>{label}</div>
    <div className="num" style={{ fontSize: 21, fontWeight: 900, color: tone || FIN.ink, overflowWrap: "anywhere" }}>{value}</div>
    {hint && <div style={{ fontSize: 11, color: FIN.sub, marginTop: 3 }}>{hint}</div>}
  </div>
);

const KV = ({ rows, onDrill }) => (
  <div className="col" style={{ gap: 0 }}>
    {rows.map((r, i) => {
      const clickable = !!(r.drill && onDrill);
      return (
        <div key={i} className="row spread"
          onClick={clickable ? () => onDrill(r.drill, r.k) : undefined}
          title={clickable ? "點擊查看明細構成" : undefined}
          style={{ padding: "8px 0", borderTop: i ? `1px solid ${FIN.hair}` : "none", fontWeight: r.strong ? 800 : 500,
            cursor: clickable ? "pointer" : "default", borderRadius: 6, transition: "background .12s" }}
          onMouseEnter={clickable ? (e) => { e.currentTarget.style.background = "rgba(0,113,227,0.06)"; } : undefined}
          onMouseLeave={clickable ? (e) => { e.currentTarget.style.background = "transparent"; } : undefined}>
          <span style={{ fontSize: 13, color: r.strong ? FIN.ink : FIN.sub, display: "flex", alignItems: "center", gap: 5 }}>
            {r.k}{clickable && <Icon name="search" size={11} color={FIN.blue}/>}
          </span>
          <span className="num" style={{ fontSize: 13.5, color: r.tone || FIN.ink }}>{r.v}</span>
        </div>
      );
    })}
  </div>
);

/* 報表鑽取浮窗:展示某個數字由哪些科目/憑證分錄構成 */
const FinDrill = ({ scope, label, period, asOf, onClose }) => {
  const [data, setData] = useFinState(null);
  const [err, setErr] = useFinState("");
  useFinEffect(() => {
    let alive = true;
    const qs = scope.startsWith("account:")
      ? `scope=account&code=${encodeURIComponent(scope.slice(8))}`
      : `scope=${encodeURIComponent(scope)}`;
    const time = (scope.startsWith("balance") || scope.startsWith("account"))
      ? (asOf ? `&as_of=${asOf}` : "")
      : `&period=${encodeURIComponent(period)}`;
    finJson(`/api/erp/gl/drilldown?${qs}${time}`)
      .then((dd) => { if (alive) setData(dd); })
      .catch((e) => { if (alive) setErr(e.message); });
    return () => { alive = false; };
  }, [scope]);
  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(20,26,40,.45)", zIndex: 700, display: "flex", alignItems: "center", justifyContent: "center", padding: 20 }}>
      <div onClick={(e) => e.stopPropagation()} className="col gap-12"
        style={{ width: 660, maxWidth: "94vw", maxHeight: "86vh", overflowY: "auto", background: "#fff", borderRadius: 14, padding: 22, boxShadow: "0 24px 60px rgba(0,0,0,.25)" }}>
        <div className="row spread" style={{ alignItems: "flex-start" }}>
          <div className="col gap-2">
            <div style={{ fontSize: 16, fontWeight: 900 }}>{label || (data && data.title) || "明細構成"}</div>
            <div style={{ fontSize: 12, color: FIN.sub }}>{data && data.ok ? `${data.title} · ${data.period_label} · 共 ${data.count} 筆` : "載入中…"}</div>
          </div>
          <button className="btn btn-sm" onClick={onClose}><Icon name="x" size={15}/></button>
        </div>
        {err && <div style={{ color: FIN.red, fontSize: 13 }}>{err}</div>}
        {data && data.ok && (
          <>
            <div className="row spread" style={{ padding: "10px 12px", borderRadius: 10, background: FIN.bg }}>
              <span style={{ fontSize: 13, fontWeight: 800 }}>合計</span>
              <span className="num" style={{ fontSize: 17, fontWeight: 900, color: FIN.blue }}>{yuan(data.total)}</span>
            </div>
            {data.accounts.length > 1 && (
              <div className="col gap-2">
                <div style={{ fontSize: 11.5, fontWeight: 800, color: FIN.sub }}>按科目</div>
                {data.accounts.map((a) => (
                  <div key={a.code} className="row spread" style={{ padding: "6px 0", borderBottom: `1px solid ${FIN.hair}` }}>
                    <span style={{ fontSize: 12.5 }}><span className="num" style={{ color: FIN.sub }}>{a.code}</span> {a.name}</span>
                    <span className="num" style={{ fontSize: 12.5, fontWeight: 700 }}>{yuan(a.amount)}</span>
                  </div>
                ))}
              </div>
            )}
            <div className="col gap-2">
              <div style={{ fontSize: 11.5, fontWeight: 800, color: FIN.sub }}>憑證明細(按金額)</div>
              {data.entries.length === 0 && <div className="muted" style={{ fontSize: 12.5, padding: "10px 0" }}>本項暫無發生額。</div>}
              {data.entries.map((e, i) => (
                <div key={i} className="row spread" style={{ padding: "8px 0", borderBottom: `1px solid ${FIN.hair}`, gap: 10, alignItems: "flex-start" }}>
                  <div className="col" style={{ gap: 2, minWidth: 0 }}>
                    <span style={{ fontSize: 12.5, color: FIN.ink, wordBreak: "break-all" }}>{e.summary}</span>
                    <span style={{ fontSize: 11, color: FIN.sub }}>{e.date} · {e.voucher_no || "—"} · {e.account_code} {e.account_name}{e.source_type ? ` · ${e.source_type}` : ""}</span>
                  </div>
                  <span className="num" style={{ fontSize: 13, fontWeight: 700, whiteSpace: "nowrap", color: e.amount >= 0 ? FIN.ink : FIN.red }}>{yuan(e.amount)}</span>
                </div>
              ))}
            </div>
            <div className="muted" style={{ fontSize: 11 }}>口徑與報表一致;明細加總 = 報表該項金額。點背景關閉。</div>
          </>
        )}
      </div>
    </div>
  );
};

const PERIODS = () => {
  const d = new Date(), y = d.getFullYear(), m = d.getMonth() + 1, q = Math.floor((m - 1) / 3) + 1;
  return [
    { id: `${y}-${String(m).padStart(2, "0")}`, label: "本月" },
    { id: `${y}-Q${q}`, label: "本季" },
    { id: `${y}`, label: "本年" },
  ];
};

// 股權結構自動拓撲圖:公司為根,股東為子節點,邊=持股比例;個人/法人區分。SVG 自動佈局。
// 股權結構穿透圖(多層):上游股東在上、本公司居中、子公司在下;邊標持股%,上游標穿透到本公司%。
const EquityTopology = ({ graph, onAsk }) => {
  const nodes = graph?.nodes || [];
  const edges = graph?.edges || [];
  const registerPrompt = "幫我登記一位股東:姓名 ___ 持股本公司 ___%,實繳出資 ___(用 fin equity set)";
  const subPrompt = "幫我登記子公司投資:本公司持有 ___ 公司 ___%(用 fin equity set,party=本公司、entity=該子公司)";
  const upPrompt = "幫我登記法人股東的上層股東:___ 持有 ___ 公司 ___%(用 fin equity set,party=上層股東、entity=該法人股東)";
  const colorOf = (t) => (t === "person" ? FIN.blue : t === "company" ? FIN.ink : FIN.indigo);
  if (nodes.length <= 1) {
    return (
      <FinCard title="股權結構穿透圖" sub="自動生成 · 暫無股權數據">
        <div className="col gap-10" style={{ alignItems: "center", padding: "26px 0" }}>
          <div style={{ fontSize: 13, color: FIN.sub, textAlign: "center", lineHeight: 1.6 }}>尚未登記股權。登記後自動繪製多層穿透圖:<br/>上游(股東及其上層股東) → 本公司 → 下游(子公司長期股權投資)。</div>
          <div className="row gap-8" style={{ flexWrap: "wrap", justifyContent: "center" }}>
            <button className="btn btn-primary btn-sm" onClick={() => onAsk(registerPrompt)}><Icon name="sparkle" size={13}/>登記股東</button>
            <button className="btn btn-sm" onClick={() => onAsk(subPrompt)}><Icon name="sparkle" size={13}/>登記子公司</button>
          </div>
        </div>
      </FinCard>
    );
  }
  const lmin = graph?.level_min ?? 0, lmax = graph?.level_max ?? 0;
  const byLevel = {};
  nodes.forEach((n) => { (byLevel[n.level] = byLevel[n.level] || []).push(n); });
  const levels = [];
  for (let L = lmin; L <= lmax; L++) levels.push(L);
  const NW = 152, NH = 60, colW = 176, rowGap = 122, topPad = 16;
  const W = Math.max(360, ...levels.map((L) => (byLevel[L] || []).length * colW));
  const rowY = (L) => topPad + (L - lmin) * rowGap;
  const posX = (L, i) => { const c = (byLevel[L] || []).length || 1; return (i + 0.5) * (W / c); };
  const posMap = {};
  levels.forEach((L) => (byLevel[L] || []).forEach((n, i) => { posMap[n.id] = { x: posX(L, i), y: rowY(L) }; }));
  const H = rowY(lmax) + NH + topPad;
  const levelLabel = (L) => (L < 0 ? `股東層 ${L}` : L === 0 ? "本公司" : `子公司層 +${L}`);
  return (
    <div className="col gap-14">
      <FinCard title="股權結構穿透圖" sub={`截至 ${graph?.as_of || "今"} · 直接股東 ${graph?.direct_holder_count || 0} · 子公司 ${graph?.subsidiary_count || 0} · 實繳合計 ${yuan(graph?.paid_total)}`}
        right={<span className={`badge ${graph?.balanced ? "badge-ok" : "badge-danger"}`} style={{ height: 20 }}>{graph?.balanced ? "直接持股 100%" : `直接合計 ${Number(graph?.total_share_ratio || 0).toFixed(2)}% ≠ 100%`}</span>}>
        <div style={{ overflowX: "auto", paddingBottom: 6 }}>
          <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{ maxWidth: "100%", minWidth: Math.min(W, 320) }}>
            {/* 邊:holder(上層) → investee(下層),中點標直接持股% */}
            {edges.map((e, i) => {
              const a = posMap[e.from], b = posMap[e.to];
              if (!a || !b) return null;
              const x1 = a.x, y1 = a.y + NH, x2 = b.x, y2 = b.y;
              const midX = (x1 + x2) / 2, midY = (y1 + y2) / 2;
              return (
                <g key={`e${i}`}>
                  <path d={`M ${x1} ${y1} C ${x1} ${y1 + 34}, ${x2} ${y2 - 34}, ${x2} ${y2}`} fill="none" stroke={FIN.hair} strokeWidth="1.6"/>
                  <rect x={midX - 24} y={midY - 10} width="48" height="19" rx="9" fill="#fff" stroke={FIN.sub} strokeWidth="0.8"/>
                  <text x={midX} y={midY + 3} textAnchor="middle" fontSize="10.5" fontWeight="800" fill={FIN.ink}>{Number(e.ratio || 0)}%</text>
                </g>
              );
            })}
            {/* 層標籤 */}
            {levels.map((L) => (byLevel[L] || []).length ? (
              <text key={`L${L}`} x={6} y={rowY(L) + NH / 2} fontSize="10" fill={FIN.sub} fontWeight="700">{levelLabel(L)}</text>
            ) : null)}
            {/* 節點 */}
            {nodes.map((n) => {
              const p = posMap[n.id]; if (!p) return null;
              const c = colorOf(n.type);
              const label = (n.type === "person" ? "👤 " : "🏢 ") + (n.label.length > 9 ? n.label.slice(0, 9) + "…" : n.label);
              return (
                <g key={`n${n.id}`}>
                  <rect x={p.x - NW / 2} y={p.y} width={NW} height={NH} rx="11" fill={n.is_self ? FIN.ink : "#fff"} stroke={n.is_self ? FIN.ink : c} strokeWidth={n.is_self ? 2 : 1.6}/>
                  <text x={p.x} y={p.y + 22} textAnchor="middle" fontSize="12.5" fontWeight="800" fill={n.is_self ? "#fff" : FIN.ink}>{n.is_self ? "★ " + label : label}</text>
                  {n.level < 0 && n.penetrated_to_self != null
                    ? <text x={p.x} y={p.y + 42} textAnchor="middle" fontSize="10.5" fill={n.is_self ? "rgba(255,255,255,0.8)" : c} fontWeight="700">穿透本公司 {Number(n.penetrated_to_self).toFixed(2)}%</text>
                    : <text x={p.x} y={p.y + 42} textAnchor="middle" fontSize="10.5" fill={n.is_self ? "rgba(255,255,255,0.8)" : FIN.sub}>{n.is_self ? "本公司" : (n.level > 0 ? "子公司" : "")}</text>}
                </g>
              );
            })}
          </svg>
        </div>
        <div className="row gap-8" style={{ flexWrap: "wrap" }}>
          <button className="btn btn-sm" onClick={() => onAsk(registerPrompt)}><Icon name="sparkle" size={13}/>登記股東</button>
          <button className="btn btn-sm" onClick={() => onAsk(subPrompt)}><Icon name="sparkle" size={13}/>登記子公司</button>
          <button className="btn btn-sm" onClick={() => onAsk(upPrompt)}><Icon name="sparkle" size={13}/>登記上層股東</button>
          <span style={{ fontSize: 11.5, color: FIN.sub, alignSelf: "center" }}>★ 本公司 · 👤 個人 · 🏢 法人/機構 · 上游標穿透持股</span>
        </div>
      </FinCard>
      <FinCard title="持股關係明細" sub={`${edges.length} 條持有關係`}>
        <div className="row spread" style={{ fontSize: 11, color: FIN.sub, fontWeight: 800, padding: "4px 0", borderBottom: `1px solid ${FIN.hair}` }}>
          <span style={{ flex: 2 }}>持有方</span><span style={{ flex: 2 }}>被投資主體</span><span style={{ flex: 1, textAlign: "right" }}>持股</span><span style={{ flex: 1.4, textAlign: "right" }}>實繳</span>
        </div>
        {edges.map((e, i) => {
          const from = nodes.find((n) => n.id === e.from) || {}, to = nodes.find((n) => n.id === e.to) || {};
          return (
            <div key={i} className="row spread" style={{ padding: "8px 0", borderBottom: `1px solid ${FIN.hair}`, alignItems: "center" }}>
              <span style={{ flex: 2, fontSize: 12.5 }}>{(from.type === "person" ? "👤 " : "🏢 ") + (from.label || "—")}{e.role ? <span className="muted" style={{ fontSize: 11, marginLeft: 5 }}>{e.role}</span> : null}</span>
              <span style={{ flex: 2, fontSize: 12.5 }}>{(to.is_self ? "★ " : (to.type === "person" ? "👤 " : "🏢 ")) + (to.label || "—")}</span>
              <span className="num" style={{ flex: 1, textAlign: "right", fontSize: 13, fontWeight: 800, color: FIN.indigo }}>{Number(e.ratio || 0)}%</span>
              <span className="num" style={{ flex: 1.4, textAlign: "right", fontSize: 12.5 }}>{yuan(e.capital_paid)}</span>
            </div>
          );
        })}
      </FinCard>
    </div>
  );
};

/* ---- AA 分賬·消費明細(與手機版 m.html 同口徑,走 /api/erp/finance/ledger-summary)---- */
const AaBar = ({ label, amt, pct, tone }) => (
  <div className="col gap-2" style={{ marginBottom: 9 }}>
    <div className="row spread" style={{ fontSize: 13, gap: 10 }}>
      <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{label || "—"}</span>
      <span className="num" style={{ fontSize: 12, color: FIN.sub, flexShrink: 0 }}>{yuan(amt)} · {pct || 0}%</span>
    </div>
    <div style={{ height: 7, background: FIN.bg, borderRadius: 5, overflow: "hidden" }}>
      <div style={{ height: "100%", width: Math.max(2, Math.min(100, Number(pct) || 0)) + "%", background: tone || FIN.ink, borderRadius: 5 }}/>
    </div>
  </div>
);

const AaExpenseCard = ({ r, showPayer, top }) => {
  const split = r.split || [];
  const orig = r.orig_currency && r.orig_currency !== "CNY"
    ? ` · 原 ${Number(r.orig_amount || 0).toLocaleString("zh-CN")} ${r.orig_currency}` : "";
  return (
    <div style={{ padding: "10px 0", borderTop: top ? `1px solid ${FIN.hair}` : "none" }}>
      <div className="row spread" style={{ gap: 10 }}>
        <span style={{ fontSize: 13.5, fontWeight: 700, color: FIN.ink }}>{r.item || "支出"}</span>
        <span className="num" style={{ fontSize: 13.5, fontWeight: 800, flexShrink: 0 }}>{yuan(r.amount)}</span>
      </div>
      <div style={{ fontSize: 12, color: FIN.sub, marginTop: 3 }}>
        {showPayer ? <><b style={{ color: FIN.blue }}>{r.payer || "—"}</b> 墊付 · {r.event_date || ""}{orig}</> : `${r.event_date || ""}${orig}`}
      </div>
      {split.length > 0 ? (
        <>
          <div style={{ fontSize: 11, color: FIN.sub, margin: "7px 0 5px" }}>替誰墊(各自承擔)</div>
          <div className="row gap-6" style={{ flexWrap: "wrap" }}>
            {split.map((s, i) => {
              const isPayer = s.name === r.payer;
              return (
                <span key={i} className="num" style={{ fontSize: 11.5, padding: "3px 8px", borderRadius: 7,
                  border: `1px solid ${isPayer ? FIN.blue + "66" : FIN.hair}`, background: isPayer ? FIN.blue + "12" : FIN.bg,
                  color: isPayer ? FIN.blue : FIN.sub }}>
                  {s.name || "—"} <b style={{ color: FIN.ink }}>{yuan(s.amount)}</b>
                </span>
              );
            })}
          </div>
        </>
      ) : <div className="muted" style={{ fontSize: 11.5, marginTop: 6 }}>未登記分攤(個人開銷)</div>}
    </div>
  );
};

const AaLedger = ({ L, onAsk }) => {
  const [mode, setMode] = useFinState("payer");
  const [payerFilter, setPayerFilter] = useFinState("");
  const empty = !L || (!(Number(L.expense_count) > 0) && !((L.balances || []).length));
  if (empty) {
    return (
      <FinCard title="AA 分賬·消費明細" sub="朋友拼賬 / 墊付分攤">
        <div className="muted" style={{ fontSize: 13, lineHeight: 1.75 }}>
          還沒有 AA 分賬數據。直接跟財務秘書說「<b>阿迪絲墊付 740 高鐵票,我和她平攤</b>」就能記一筆;
          一疊賬單照片可在手機端 <b>m.html</b> 拍照識別後批量記。記完這裡和手機端同口徑,實時對賬。
        </div>
        <div className="row gap-8" style={{ marginTop: 4 }}>
          <button className="btn btn-primary btn-sm" onClick={() => onAsk("幫我記一筆 AA 共享開銷:墊付人 ___ 金額 ¥___ 項目 ___,和 ___ 平攤(用 fin expense)")}><Icon name="sparkle" size={13}/>記一筆 AA 開銷</button>
        </div>
      </FinCard>
    );
  }
  const cats = L.by_category || [], payers = L.by_payer || [];
  const balances = L.balances || [], plan = L.settlement || [], recent = L.recent || [];
  const TONES = [FIN.blue, FIN.indigo, FIN.green, FIN.orange, "#7a6f57", "#2e6e4c"];
  const payerNames = [...new Set(recent.map((r) => r.payer).filter(Boolean))];
  const list = payerFilter ? recent.filter((r) => r.payer === payerFilter) : recent;
  const groups = {};
  list.forEach((r) => { const k = r.payer || "—"; (groups[k] = groups[k] || { name: k, items: [], total: 0 }); groups[k].items.push(r); groups[k].total += Number(r.amount || 0); });
  const groupArr = Object.values(groups).sort((a, b) => b.total - a.total);
  const imbalance = Math.abs(L.imbalance || 0) >= 0.01;

  return (
    <div className="col gap-16">
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <Metric label="共享開銷總額" value={yuan(L.total_spent)} tone={FIN.blue} hint={`${L.expense_count || 0} 筆 · ${L.period || "全部期間"}`}/>
        <Metric label="淨額是否平" value={imbalance ? "未平 " + yuan(L.imbalance) : "已平 ✓"} tone={imbalance ? FIN.red : FIN.green} hint={imbalance ? "可能有開銷沒記分攤" : "墊付與分攤對得上"}/>
        <Metric label="參與人數" value={String(payerNames.length || balances.length)} hint="有墊付/分攤的人"/>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 16, alignItems: "start" }}>
        {payers.length > 0 && <FinCard title="誰墊的" sub="墊付占比">{payers.slice(0, 8).map((p, i) => <AaBar key={i} label={p.name} amt={p.amount} pct={p.pct} tone={FIN.ink}/>)}</FinCard>}
        {cats.length > 0 && <FinCard title="花在什麼上" sub="占比">{cats.slice(0, 8).map((c, i) => <AaBar key={i} label={c.name} amt={c.amount} pct={c.pct} tone={TONES[i % TONES.length]}/>)}</FinCard>}
      </div>

      {balances.length > 0 && (
        <FinCard title="往來結算" sub={plan.length ? `最少 ${plan.length} 筆轉賬擺平` : "已平,無需轉賬"}
          right={plan.length > 0 ? <button className="btn btn-sm" onClick={() => onAsk("請按最優結算方案把這幾筆轉賬登記平賬(fin settle-record),登記前把每一筆複述給我確認。")}><Icon name="sparkle" size={13}/>讓秘書登記結算</button> : null}>
          <KV rows={balances.map((b) => ({ k: b.party, v: (b.net > 0 ? "應收 " : b.net < 0 ? "應付 " : "") + yuan(Math.abs(b.net)), strong: true, tone: b.net > 0 ? FIN.green : b.net < 0 ? FIN.red : FIN.sub }))}/>
          {plan.length > 0 && (
            <div className="col" style={{ gap: 0, marginTop: 8 }}>
              {plan.map((t, i) => (
                <div key={i} className="row spread" style={{ padding: "7px 0", borderTop: `1px solid ${FIN.hair}`, fontSize: 13 }}>
                  <span><span style={{ color: FIN.red }}>{t.from}</span> → <span style={{ color: FIN.green }}>{t.to}</span></span>
                  <span className="num" style={{ fontWeight: 800 }}>{yuan(t.amount)}</span>
                </div>
              ))}
            </div>
          )}
        </FinCard>
      )}

      {recent.length > 0 && (
        <FinCard title="消費明細" sub={`全部 ${recent.length} 筆`}
          right={
            <div className="row gap-6" style={{ alignItems: "center", flexWrap: "wrap" }}>
              <div className="row" style={{ border: `1px solid ${FIN.hair}`, borderRadius: 8, overflow: "hidden" }}>
                {[["payer", "按付款人"], ["time", "按時間"]].map(([m, lab]) => (
                  <button key={m} className="btn btn-sm" onClick={() => setMode(m)} style={{ borderRadius: 0, background: mode === m ? FIN.ink : "#fff", color: mode === m ? "#fff" : FIN.sub }}>{lab}</button>
                ))}
              </div>
              <select value={payerFilter} onChange={(e) => setPayerFilter(e.target.value)} className="btn btn-sm" style={{ background: "#fff", color: FIN.ink }}>
                <option value="">全部付款人</option>
                {payerNames.map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>
          }>
          {list.length === 0 ? <div className="muted" style={{ fontSize: 12.5 }}>沒有符合的賬單。</div> :
            mode === "payer" ? (
              <div className="col gap-12">
                {groupArr.map((g, gi) => (
                  <div key={gi} style={{ border: `1px solid ${FIN.hair}`, borderRadius: 10, padding: "0 14px" }}>
                    <div className="row spread" style={{ padding: "11px 0", alignItems: "baseline", borderBottom: `1px solid ${FIN.hair}` }}>
                      <span style={{ fontSize: 14.5, fontWeight: 800 }}>{g.name} <span className="muted" style={{ fontSize: 11, fontWeight: 400 }}>墊付 {g.items.length} 筆</span></span>
                      <span className="num" style={{ fontWeight: 800 }}>{yuan(g.total)}</span>
                    </div>
                    {g.items.map((r, ri) => <AaExpenseCard key={ri} r={r} showPayer={false} top={ri > 0}/>)}
                  </div>
                ))}
              </div>
            ) : (
              <div className="col">{list.map((r, ri) => <AaExpenseCard key={ri} r={r} showPayer={true} top={ri > 0}/>)}</div>
            )}
        </FinCard>
      )}
    </div>
  );
};

const PageFinance = () => {
  const periods = PERIODS();
  const [period, setPeriod] = useFinState(periods[0].id);
  const [tab, setTab] = useFinState("reports");
  const [d, setD] = useFinState({});
  const [state, setState] = useFinState("loading");
  const [err, setErr] = useFinState("");
  const [drill, setDrill] = useFinState(null);   // {scope, label}
  const openDrill = (scope, label) => setDrill({ scope, label });

  const load = (p = period) => {
    setState((s) => (s === "ok" ? "ok" : "loading")); setErr("");
    Promise.all([
      finJson(`/api/erp/gl/income?period=${encodeURIComponent(p)}`),
      finJson(`/api/erp/gl/balance-sheet`),
      finJson(`/api/erp/gl/cashflow?period=${encodeURIComponent(p)}`),
      finJson(`/api/erp/gl/ap`), finJson(`/api/erp/gl/ar`),
      finJson(`/api/erp/gl/assets`), finJson(`/api/erp/gl/tax?period=${encodeURIComponent(p)}`),
      finJson(`/api/erp/gl/trial-balance`), finJson(`/api/erp/gl/vouchers?limit=40`), finJson(`/api/erp/gl/accounts`),
      finJson(`/api/erp/gl/equity-change?period=${encodeURIComponent(p)}`), finJson(`/api/erp/gl/notes?period=${encodeURIComponent(p)}`),
      finJson(`/api/erp/gl/equity-graph`),
      finJson(`/api/erp/finance/ledger-summary?limit=all`).catch(() => ({})),   // AA 分賬(失敗不拖垮報表)
    ]).then(([income, balance, cashflow, ap, ar, assets, tax, trial, vouchers, chart, equityChange, notes, equityGraph, ledger]) => {
      setD({ income, balance, cashflow, ap, ar, assets, tax, trial, vouchers: vouchers.vouchers || [], chart: chart.accounts || [], equityChange, notes, equityGraph, ledger });
      setState("ok");
    }).catch((e) => { setErr(e.message || String(e)); setState("error"); });
  };
  useFinEffect(() => { load(); }, [period]);

  if (state === "loading" && !d.income) return <div className="muted" style={{ fontSize: 13 }}>讀取財務數據中…</div>;
  if (state === "error") return <div className="card" style={{ padding: 16, color: FIN.red, fontSize: 13 }}>⚠ {err}</div>;

  const cash = (d.balance?.asset_lines || []).filter((l) => l.code === "1001" || l.code === "1002").reduce((a, l) => a + Number(l.amount || 0), 0);
  const pLabel = periods.find((x) => x.id === period)?.label || period;

  const tabs = [["reports", "五大報表"], ["aa", "AA 分賬·明細"], ["equity", "股權結構"], ["partners", "往來·賬齡"], ["assets", "固定資產"], ["books", "賬簿·稅務"]];
  const isEmpty = (d.vouchers || []).length === 0;
  const actions = [
    ["期初建賬", "幫我做期初建賬,把現有庫存價值計入總賬(用 fin init-balances);如有期初現金/銀行金額我會告訴你"],
    ["付採購應付款", "請按已收貨且已產生應付的正式 PO ID ___ 支付 ¥___（用 fin pay；供應商與幣別由 PO 帶入）"],
    ["收客戶款", "幫我記一筆收款:收到客戶 ___ ¥___(用 fin receive)"],
    ["賒銷開應收", "幫我記一筆賒銷應收:客戶 ___ 金額 ___,稅率 13(用 fin receivable)"],
    ["採購收貨轉固定資產", "把已完成採購收貨的入庫單 ID ___ 轉為固定資產：名稱 ___，折舊年限 ___ 個月（用 fin asset add）"],
    ["計提折舊", `幫我計提 ${period} 的折舊(用 fin depreciate）`],
    ["月末結賬", `幫我做 ${period} 的期末結賬結轉損益(用 fin close,結賬會鎖期請先確認）`],
    ["記 AA 開銷", "幫我記一筆 AA 共享開銷:墊付人 ___ 金額 ¥___ 項目 ___,和 ___ 平攤(用 fin expense)"],
    ["對齊分賬人名", "幫我跑身分體檢 fin party audit,把未對上主體的賬號、疑似同一個人的主體逐條列出來讓我確認後對齊"],
  ];

  return (
    <div className="col gap-18" style={{ color: FIN.ink }}>
      {/* 頂部:標題 + 期間 */}
      <div className="row spread" style={{ flexWrap: "wrap", gap: 12, alignItems: "flex-end" }}>
        <div className="col gap-4">
          <div className="row gap-8" style={{ alignItems: "center" }}>
            <span style={{ fontSize: 28, fontWeight: 900 }}>AI 財務</span>
            <span className="badge badge-info" style={{ height: 22 }}>複式記賬 · 業財一體</span>
            {d.trial && <span className={`badge ${d.trial.balanced ? "badge-ok" : "badge-danger"}`} style={{ height: 22 }}>{d.trial.balanced ? "試算平衡 ✓" : "試算不平衡"}</span>}
          </div>
          <div style={{ fontSize: 13, color: FIN.sub }}>所有數據從總賬即時推算;要動賬點下方按鈕交給財務秘書,記賬平衡由後端保證。</div>
        </div>
        <div className="row gap-6">
          {periods.map((p) => (
            <button key={p.id} className="btn btn-sm" onClick={() => setPeriod(p.id)}
              style={{ background: period === p.id ? FIN.blue : "var(--surface-2)", color: period === p.id ? "#fff" : FIN.sub }}>{p.label}</button>
          ))}
        </div>
      </div>

      {/* 空賬提示:總賬是事件驅動,需先期初建賬 + 新業務自動同步 */}
      {isEmpty && (
        <div style={{ padding: 14, borderRadius: 10, background: "var(--blue-soft, #EAF2FF)", border: `1px solid ${FIN.blue}33` }} className="col gap-8">
          <div style={{ fontSize: 13.5, fontWeight: 800, color: FIN.blue }}>📒 總賬目前是空的 —— 這正常,不是沒同步</div>
          <div style={{ fontSize: 12.5, color: FIN.sub, lineHeight: 1.6 }}>
            財務總賬是「事件驅動」的:它從現在起,只在<b>新發生</b>的採購入庫/銷售/付款等業務時自動記賬(業財一體化),<b>不會自動倒灌</b>之前已有的庫存。要讓財務和現有家底對上,做一次<b>期初建賬</b>即可。<br/>
            提醒:總賬要記金額,<b>物資得有單價</b>才有價值;沒填單價的物資價值記 0。可在「庫存管理」給物資補單價後再建賬。
          </div>
          <div className="row gap-8">
            <button className="btn btn-primary btn-sm" onClick={() => askFin(actions[0][1])}><Icon name="sparkle" size={13}/>讓秘書做期初建賬</button>
          </div>
        </div>
      )}

      {/* 駕駛艙指標 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12 }}>
        <Metric label={`${pLabel}利潤`} value={yuan(d.income?.profit)} tone={(d.income?.profit || 0) >= 0 ? FIN.green : FIN.red} hint={`收入 ${yuan(d.income?.revenue)} − 成本費用`}/>
        <Metric label="現金及銀行" value={yuan(cash)} tone={FIN.blue}/>
        <Metric label="應收賬款" value={yuan(d.ar?.total_outstanding)} tone={FIN.indigo} hint={`${(d.ar?.by_party || []).length} 個客戶`}/>
        <Metric label="應付賬款" value={yuan(d.ap?.total_outstanding)} tone={FIN.orange} hint={`${(d.ap?.by_party || []).length} 個供應商`}/>
        <Metric label="應納增值稅" value={yuan(d.tax?.payable)} hint={`銷項 ${yuan(d.tax?.output_tax)} − 進項 ${yuan(d.tax?.input_tax)}`}/>
        <Metric label="固定資產淨值" value={yuan(d.assets?.total_net)} hint={`原值 ${yuan(d.assets?.total_cost)}`}/>
      </div>

      {/* 動賬:交給財務秘書 */}
      <div className="row gap-8" style={{ flexWrap: "wrap", padding: 12, borderRadius: 10, background: FIN.bg }}>
        <span style={{ fontSize: 12.5, fontWeight: 800, color: FIN.sub, alignSelf: "center" }}>動賬交給秘書:</span>
        {actions.map(([t, prompt]) => (
          <button key={t} className="btn btn-sm" onClick={() => askFin(prompt)}><Icon name="sparkle" size={13}/>{t}</button>
        ))}
      </div>

      {/* 頁籤 */}
      <div className="row gap-7" style={{ flexWrap: "wrap" }}>
        {tabs.map(([id, label]) => (
          <button key={id} className="btn btn-sm" onClick={() => setTab(id)}
            style={{ background: tab === id ? FIN.ink : "var(--surface-2)", color: tab === id ? "#fff" : FIN.sub }}>{label}</button>
        ))}
      </div>

      {tab === "reports" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 340px), 1fr))", gap: 16, alignItems: "start" }}>
          <FinCard title="利潤表" sub={`${d.income?.from} ~ ${d.income?.to}`}>
            <KV onDrill={openDrill} rows={[
              { k: "營業收入", v: yuan(d.income?.revenue), drill: "income.revenue" },
              { k: "營業成本", v: "-" + yuan(d.income?.cost), drill: "income.cost" },
              { k: "費用", v: "-" + yuan(d.income?.expense), drill: "income.expense" },
              { k: "淨利潤", v: yuan(d.income?.profit), strong: true, tone: (d.income?.profit || 0) >= 0 ? FIN.green : FIN.red },
            ]}/>
            {(d.income?.lines || []).length > 0 && <div style={{ marginTop: 10 }}><KV onDrill={openDrill} rows={(d.income.lines || []).map((l) => ({ k: l.name, v: yuan(l.amount), drill: "account:" + l.code }))}/></div>}
          </FinCard>
          <FinCard title="資產負債表" sub={`截至 ${d.balance?.as_of}`} right={<span className={`badge ${d.balance?.balanced ? "badge-ok" : "badge-danger"}`} style={{ height: 20 }}>{d.balance?.balanced ? "平衡" : "不平衡"}</span>}>
            <KV onDrill={openDrill} rows={[
              { k: "資產合計", v: yuan(d.balance?.assets), strong: true, tone: FIN.blue, drill: "balance.asset" },
              { k: "負債合計", v: yuan(d.balance?.liabilities), drill: "balance.liability" },
              { k: "  其中本年利潤", v: yuan(d.balance?.current_profit), drill: "balance.profit" },
              { k: "權益合計", v: yuan(d.balance?.total_equity), strong: true, tone: FIN.indigo, drill: "balance.equity" },
            ]}/>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginTop: 8 }}>
              <div><div style={{ fontSize: 11.5, fontWeight: 800, color: FIN.sub, marginBottom: 4 }}>資產</div><KV onDrill={openDrill} rows={(d.balance?.asset_lines || []).map((l) => ({ k: l.name, v: yuan(l.amount), drill: "account:" + l.code }))}/></div>
              <div><div style={{ fontSize: 11.5, fontWeight: 800, color: FIN.sub, marginBottom: 4 }}>負債 + 權益</div><KV onDrill={openDrill} rows={[...(d.balance?.liability_lines || []), ...(d.balance?.equity_lines || [])].map((l) => ({ k: l.name, v: yuan(l.amount), drill: "account:" + l.code }))}/></div>
            </div>
          </FinCard>
          <FinCard title="現金流量表" sub={`${pLabel}`}>
            <KV onDrill={openDrill} rows={[
              { k: "現金流入", v: yuan(d.cashflow?.inflow), tone: FIN.green, drill: "cashflow.in" },
              { k: "現金流出", v: "-" + yuan(d.cashflow?.outflow), tone: FIN.red, drill: "cashflow.out" },
              { k: "淨增加", v: yuan(d.cashflow?.net_change), strong: true },
            ]}/>
          </FinCard>
          <FinCard title="所有者權益變動表" sub={`${d.equityChange?.from} ~ ${d.equityChange?.to}`}>
            <KV rows={[
              { k: "期初權益合計", v: yuan(d.equityChange?.opening_total) },
              { k: "本期淨利潤", v: yuan(d.equityChange?.current_profit), tone: (d.equityChange?.current_profit || 0) >= 0 ? FIN.green : FIN.red },
              { k: "期末權益合計", v: yuan(d.equityChange?.closing_total), strong: true, tone: FIN.indigo },
            ]}/>
            {(d.equityChange?.items || []).length > 0 ? (
              <div style={{ marginTop: 8 }}>
                <div className="row spread" style={{ fontSize: 11, color: FIN.sub, fontWeight: 800, padding: "4px 0" }}><span>項目</span><span>期初 / 變動 / 期末</span></div>
                {(d.equityChange.items || []).map((it) => (
                  <div key={it.code} className="row spread" onClick={() => openDrill("account:" + it.code, it.name)}
                    title="點擊查看明細構成"
                    style={{ padding: "7px 0", borderTop: `1px solid ${FIN.hair}`, cursor: "pointer", borderRadius: 6 }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(0,113,227,0.06)"; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; }}>
                    <span style={{ fontSize: 13, display: "flex", alignItems: "center", gap: 5 }}>{it.name}<Icon name="search" size={11} color={FIN.blue}/></span>
                    <span className="num" style={{ fontSize: 12.5 }}>{yuan(it.opening)} <span style={{ color: it.change >= 0 ? FIN.green : FIN.red }}>{it.change >= 0 ? "+" : ""}{yuan(it.change)}</span> {yuan(it.closing)}</span>
                  </div>
                ))}
              </div>
            ) : <div className="muted" style={{ fontSize: 12.5, marginTop: 6 }}>本期權益科目無變動;期末權益 = 期初 + 本期淨利潤。</div>}
          </FinCard>
          <div style={{ gridColumn: "1 / -1" }}>
            <FinCard title="財務報表附注" sub={`自動匯編 · ${d.notes?.period || pLabel}`} right={<button className="btn btn-sm" onClick={() => askFin(`請根據當前財務數據,把「財務報表附注」用更專業的會計語言補充完善(會計政策、關鍵科目說明、股權結構、重大事項與或有事項)。`)}><Icon name="sparkle" size={13}/>讓秘書潤色</button>}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 300px), 1fr))", gap: 14 }}>
                {(d.notes?.sections || []).map((s, i) => (
                  <div key={i} className="col gap-4">
                    <div style={{ fontSize: 13, fontWeight: 800, color: FIN.ink }}>{s.title}</div>
                    {s.body && <div style={{ fontSize: 12.5, color: FIN.sub, lineHeight: 1.6 }}>{s.body}</div>}
                    {(s.items || []).map((it, j) => <div key={j} style={{ fontSize: 12.5, color: FIN.sub, lineHeight: 1.55 }}>· {it}</div>)}
                  </div>
                ))}
              </div>
            </FinCard>
          </div>
        </div>
      )}

      {tab === "aa" && <AaLedger L={d.ledger} onAsk={askFin}/>}

      {tab === "equity" && <EquityTopology graph={d.equityGraph} onAsk={askFin}/>}

      {tab === "partners" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: 16, alignItems: "start" }}>
          {[["應付賬款(欠供應商)", d.ap, FIN.orange], ["應收賬款(客戶欠)", d.ar, FIN.indigo]].map(([title, ag, tone]) => (
            <FinCard key={title} title={title} right={<span className="num" style={{ fontWeight: 900, color: tone }}>{yuan(ag?.total_outstanding)}</span>}>
              <div className="row gap-6" style={{ flexWrap: "wrap" }}>
                {Object.entries(ag?.aging || {}).map(([k, v]) => (
                  <span key={k} className="badge" style={{ height: 26, background: "var(--surface-2)", color: Number(v) > 0 ? FIN.ink : FIN.sub }}>{k}天 {yuan(v)}</span>
                ))}
              </div>
              <KV rows={(ag?.by_party || []).map((p) => ({ k: p.party, v: yuan(p.outstanding), strong: true }))}/>
              {(ag?.items || []).length === 0 && <div className="muted" style={{ fontSize: 12.5, padding: "8px 0" }}>暫無未結往來</div>}
            </FinCard>
          ))}
        </div>
      )}

      {tab === "assets" && (
        <FinCard title="固定資產台賬" right={<span className="num" style={{ fontWeight: 900 }}>淨值 {yuan(d.assets?.total_net)}</span>}>
          <div style={{ overflowX: "auto" }}>
            <table className="tbl"><thead><tr><th>編號</th><th>名稱</th><th>原值</th><th>累計折舊</th><th>淨值</th><th>年限</th><th>狀態</th></tr></thead>
              <tbody>
                {(d.assets?.assets || []).map((a) => (
                  <tr key={a.id}><td className="num">{a.asset_no}</td><td>{a.name}</td><td className="num">{yuan(a.original_cost)}</td>
                    <td className="num muted">{yuan(a.accumulated_dep)}</td><td className="num" style={{ fontWeight: 700 }}>{yuan(a.net_value)}</td>
                    <td className="num muted">{a.useful_months}月</td><td><span className="badge badge-gray">{a.status === "in_use" ? "在用" : "已處置"}</span></td></tr>
                ))}
                {(d.assets?.assets || []).length === 0 && <tr><td colSpan={7} className="muted">暫無固定資產。可點上方「買固定資產」交給秘書建卡。</td></tr>}
              </tbody>
            </table>
          </div>
        </FinCard>
      )}

      {tab === "books" && (
        <div className="col gap-16">
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 320px), 1fr))", gap: 16, alignItems: "start" }}>
            <FinCard title="增值稅" sub={pLabel}>
              <KV rows={[
                { k: "銷項稅額", v: yuan(d.tax?.output_tax) },
                { k: "進項稅額", v: "-" + yuan(d.tax?.input_tax) },
                { k: "應納增值稅", v: yuan(d.tax?.payable), strong: true },
              ]}/>
            </FinCard>
            <FinCard title="試算平衡表" right={<span className={`badge ${d.trial?.balanced ? "badge-ok" : "badge-danger"}`} style={{ height: 20 }}>借 {yuan(d.trial?.total_debit)} / 貸 {yuan(d.trial?.total_credit)}</span>}>
              <div style={{ maxHeight: 260, overflowY: "auto" }}>
                <KV rows={(d.trial?.accounts || []).filter((a) => Math.abs(a.balance) > 0.005).map((a) => ({ k: `${a.code} ${a.name}`, v: yuan(a.balance) }))}/>
              </div>
            </FinCard>
          </div>
          <FinCard title="記賬憑證流水" sub="出入庫/採購/銷售自動生成,每張借貸平衡">
            <div className="col gap-8" style={{ maxHeight: 420, overflowY: "auto" }}>
              {(d.vouchers || []).map((v) => (
                <div key={v.id} style={{ padding: "10px 12px", borderRadius: 8, border: `1px solid ${FIN.hair}` }}>
                  <div className="row spread" style={{ fontSize: 12.5 }}>
                    <span style={{ fontWeight: 800 }}>{v.voucher_no} · {v.summary}</span>
                    <span className="muted">{v.voucher_date} · {yuan(v.total_amount)}</span>
                  </div>
                  <div className="row gap-10" style={{ flexWrap: "wrap", marginTop: 6 }}>
                    {(v.lines || []).map((l, i) => (
                      <span key={i} className="num" style={{ fontSize: 12, color: Number(l.debit) > 0 ? FIN.blue : FIN.orange }}>
                        {Number(l.debit) > 0 ? "借" : "貸"} {l.code} {l.name} {yuan(Number(l.debit) || Number(l.credit))}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
              {(d.vouchers || []).length === 0 && <div className="muted" style={{ fontSize: 12.5 }}>暫無憑證。發生採購入庫/銷售等業務後會自動生成。</div>}
            </div>
          </FinCard>
        </div>
      )}

      {drill && <FinDrill scope={drill.scope} label={drill.label} period={period} asOf={d.balance?.as_of} onClose={() => setDrill(null)}/>}
    </div>
  );
};

window.PageFinance = PageFinance;
