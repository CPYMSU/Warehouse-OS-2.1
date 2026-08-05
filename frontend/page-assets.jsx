/* ============================================================
   資產管理 — 金融資產 + 企業數字資產市場
   金融資產:股票/基金/黃金/加密等可在線交易兌現的資產;
   數字資產:項目/軟件/數據/流程/模型/AI Agent 等可確權、估值、流通的能力資產。
   登記 → AI 補代碼 → 行情接入 → 數據科學分析 → 業財一體化
   數據全部來自 /api/assets/*;買賣分紅由後端自動生成記賬憑證。
   ============================================================ */
const { useState: useDamState, useEffect: useDamEffect, useRef: useDamRef, useCallback: useDamCallback } = React;

const DAM_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const DAM_C = { ink: "#1D1D1F", sub: "#6E6E73", hair: "rgba(29,29,31,0.12)", blue: "#0071E3", green: "#34C759", orange: "#FF9F0A", red: "#FF3B30", indigo: "#5856D6", gold: "#B8860B" };
const DAM_TYPE_META = {
  stock: { label: "股票", color: DAM_C.blue },
  fund: { label: "基金", color: DAM_C.indigo },
  gold: { label: "黃金", color: DAM_C.gold },
  crypto: { label: "加密", color: DAM_C.orange },
  other: { label: "其他", color: DAM_C.sub },
};

const damJson = async (path, options) => {
  const res = await (window.authFetch || fetch)(DAM_API_BASE + path, options);
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.error || res.statusText || "請求失敗");
  return d;
};
const damPost = (path, body) => damJson(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
});
const damFormPost = async (path, formData) => {
  const res = await (window.authFetch || fetch)(DAM_API_BASE + path, { method: "POST", body: formData });
  const d = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(d.error || res.statusText || "上傳失敗");
  return d;
};
const damCny = (v, digits = 0) => (v === null || v === undefined) ? "—"
  : "¥" + Number(v).toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: Math.max(digits, 2) });
const damNum = (v, max = 4) => (v === null || v === undefined) ? "—"
  : Number(v).toLocaleString("zh-CN", { maximumFractionDigits: max });
const damPct = (v) => (v === null || v === undefined) ? "—" : (v >= 0 ? "+" : "") + Number(v).toFixed(2) + "%";
const damTone = (v) => v === null || v === undefined ? DAM_C.sub : v > 0 ? DAM_C.red : v < 0 ? DAM_C.green : DAM_C.sub; // A股慣例:紅漲綠跌
const damQuoteTime = (v) => {
  if (!v) return "";
  const d = new Date(String(v).replace(" ", "T"));
  if (Number.isNaN(d.getTime())) return String(v);
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false });
};
const damAsk = (prompt, options = {}) => {
  if (window.openUnifiedAgent) window.openUnifiedAgent(prompt, { autoAsk: true, ...options });
};

/* ---------- Canvas 走勢圖 ---------- */
const DamChart = ({ series, height = 220 }) => {
  const ref = useDamRef(null);
  useDamEffect(() => {
    const cv = ref.current;
    if (!cv || !series || series.length < 2) return;
    const W = cv.clientWidth || 600, H = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const closes = series.map(p => p.close);
    const lo = Math.min(...closes), hi = Math.max(...closes);
    const padL = 8, padR = 64, padT = 14, padB = 22;
    const span = hi - lo || 1;
    const x = (i) => padL + (W - padL - padR) * (i / (series.length - 1));
    const y = (v) => padT + (H - padT - padB) * (1 - (v - lo) / span);
    // 網格 + 右側刻度
    ctx.font = "10px -apple-system, sans-serif";
    ctx.fillStyle = DAM_C.sub;
    ctx.strokeStyle = "rgba(29,29,31,.07)";
    for (let i = 0; i <= 4; i++) {
      const v = lo + span * i / 4, gy = y(v);
      ctx.beginPath(); ctx.moveTo(padL, gy); ctx.lineTo(W - padR + 6, gy); ctx.stroke();
      ctx.fillText(Number(v).toLocaleString("zh-CN", { maximumFractionDigits: v < 10 ? 4 : 2 }), W - padR + 10, gy + 3);
    }
    // MA20
    if (closes.length >= 20) {
      ctx.beginPath();
      for (let i = 19; i < closes.length; i++) {
        let s = 0; for (let k = i - 19; k <= i; k++) s += closes[k];
        const v = s / 20;
        i === 19 ? ctx.moveTo(x(i), y(v)) : ctx.lineTo(x(i), y(v));
      }
      ctx.strokeStyle = "rgba(255,159,10,.8)"; ctx.lineWidth = 1; ctx.stroke();
    }
    // 收盤線 + 漸變填充
    const up = closes[closes.length - 1] >= closes[0];
    const line = up ? DAM_C.red : DAM_C.green;
    const grad = ctx.createLinearGradient(0, padT, 0, H - padB);
    grad.addColorStop(0, up ? "rgba(255,59,48,.16)" : "rgba(52,199,89,.16)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.beginPath();
    series.forEach((p, i) => i ? ctx.lineTo(x(i), y(p.close)) : ctx.moveTo(x(i), y(p.close)));
    ctx.strokeStyle = line; ctx.lineWidth = 1.8; ctx.lineJoin = "round"; ctx.stroke();
    ctx.lineTo(x(series.length - 1), H - padB); ctx.lineTo(x(0), H - padB); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    // 首尾日期
    ctx.fillStyle = DAM_C.sub;
    ctx.fillText(series[0].date, padL, H - 7);
    const endText = series[series.length - 1].date;
    ctx.fillText(endText, W - padR - ctx.measureText(endText).width, H - 7);
  }, [series, height]);
  if (!series || series.length < 2) return <div className="muted" style={{ fontSize: 12, padding: "30px 0", textAlign: "center" }}>暫無走勢數據 — 點「拉取歷史」或讓秘書跑 asset history</div>;
  return <canvas ref={ref} style={{ width: "100%", height }} />;
};

/* 火花線:卡片內 60 日迷你走勢 */
const DamSpark = ({ closes, height = 34 }) => {
  const ref = useDamRef(null);
  useDamEffect(() => {
    const cv = ref.current;
    if (!cv || !closes || closes.length < 2) return;
    const W = cv.clientWidth || 200, H = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const lo = Math.min(...closes), hi = Math.max(...closes);
    const span = hi - lo || 1;
    const x = i => 2 + (W - 4) * i / (closes.length - 1);
    const y = v => 3 + (H - 6) * (1 - (v - lo) / span);
    const up = closes[closes.length - 1] >= closes[0];
    const tone = up ? DAM_C.red : DAM_C.green;
    const grad = ctx.createLinearGradient(0, 0, 0, H);
    grad.addColorStop(0, up ? "rgba(255,59,48,.18)" : "rgba(52,199,89,.18)");
    grad.addColorStop(1, "rgba(255,255,255,0)");
    ctx.beginPath();
    closes.forEach((c, i) => i ? ctx.lineTo(x(i), y(c)) : ctx.moveTo(x(i), y(c)));
    ctx.strokeStyle = tone; ctx.lineWidth = 1.5; ctx.lineJoin = "round"; ctx.stroke();
    ctx.lineTo(x(closes.length - 1), H); ctx.lineTo(x(0), H); ctx.closePath();
    ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath(); ctx.arc(x(closes.length - 1), y(closes[closes.length - 1]), 2.2, 0, Math.PI * 2);
    ctx.fillStyle = tone; ctx.fill();
  }, [JSON.stringify((closes || []).slice(-3)), (closes || []).length, height]);
  if (!closes || closes.length < 2) return <div className="da-spark-empty">60 日走勢建檔中…</div>;
  return <canvas ref={ref} style={{ width: "100%", height, display: "block" }}/>;
};

/* ---------- 登記資產彈窗 ---------- */
const DamRegister = ({ onClose, onDone }) => {
  const [form, setForm] = useDamState({ name: "", asset_type: "stock", symbol: "", quantity: "", cost: "", watch_only: false, notes: "" });
  const [busy, setBusy] = useDamState(false);
  const [err, setErr] = useDamState("");
  const [candidates, setCandidates] = useDamState([]);
  const searchTimer = useDamRef(null);
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const searchSymbol = (q) => {
    clearTimeout(searchTimer.current);
    if (!q || q.trim().length < 2) { setCandidates([]); return; }
    searchTimer.current = setTimeout(() => {
      damJson(`/api/assets/search?q=${encodeURIComponent(q.trim())}`)
        .then(d => setCandidates(d.candidates || []))
        .catch(() => setCandidates([]));
    }, 300);
  };

  const submit = async () => {
    if (busy) return;
    setErr("");
    if (!form.name.trim()) { setErr("請填資產名稱"); return; }
    setBusy(true);
    try {
      const r = await damPost("/api/assets/create", {
        name: form.name.trim(), asset_type: form.asset_type, symbol: form.symbol.trim() || null,
        quantity: Number(form.quantity || 0), cost_total_cny: Number(form.cost || 0),
        watch_only: form.watch_only, notes: form.notes.trim() || null,
      });
      onDone(r);
    } catch (e) { setErr(e.message || String(e)); } finally { setBusy(false); }
  };

  const field = { width: "100%", border: `1px solid ${DAM_C.hair}`, borderRadius: 8, padding: "9px 11px", fontSize: 13.5, outline: "none", background: "#fff" };
  return (
    <div className="da-modal-mask" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="da-modal da-register-modal col gap-12">
        <div className="row spread">
          <div style={{ fontSize: 16, fontWeight: 900 }}>登記金融資產</div>
          <button className="btn btn-sm" onClick={onClose}>關閉</button>
        </div>
        <div className="row gap-8">
          {Object.entries(DAM_TYPE_META).map(([k, m]) => (
            <button key={k} className="btn btn-sm" onClick={() => set("asset_type", k)}
              style={form.asset_type === k ? { background: m.color, color: "#fff", borderColor: m.color } : {}}>{m.label}</button>
          ))}
        </div>
        <input style={field} placeholder="資產名稱,如 貴州茅台 / 易方達消費 / 國際現貨黃金" value={form.name}
          onChange={e => { set("name", e.target.value); searchSymbol(e.target.value); }} />
        <div className="col gap-4">
          <input style={field} placeholder="代碼(可不填,讓 AI 秘書補全):sh600519 / AAPL / 110022 / XAU / BTC"
            value={form.symbol} onChange={e => set("symbol", e.target.value)} />
          {!!candidates.length && (
            <div style={{ border: `1px solid ${DAM_C.hair}`, borderRadius: 8, overflow: "hidden" }}>
              {candidates.slice(0, 6).map(c => (
                <button key={c.symbol} className="row spread" style={{ width: "100%", padding: "7px 11px", fontSize: 12.5, borderBottom: `1px solid ${DAM_C.hair}`, background: "#fff", textAlign: "left" }}
                  onClick={() => { set("symbol", c.symbol); setCandidates([]); }}>
                  <span><b>{c.name}</b> <span className="muted">{c.symbol}</span></span>
                  <span className="muted">{c.market}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="row gap-8">
          <input style={{ ...field, flex: 1 }} placeholder="持有數量(觀察倉可空)" value={form.quantity} onChange={e => set("quantity", e.target.value)} />
          <input style={{ ...field, flex: 1 }} placeholder="總成本(人民幣)" value={form.cost} onChange={e => set("cost", e.target.value)} />
        </div>
        <label className="row gap-6" style={{ fontSize: 13, cursor: "pointer" }}>
          <input type="checkbox" checked={form.watch_only} onChange={e => set("watch_only", e.target.checked)} />
          只觀察不持有(跟蹤行情,不參與記賬)
        </label>
        <input style={field} placeholder="備註(可選)" value={form.notes} onChange={e => set("notes", e.target.value)} />
        {err && <div style={{ color: DAM_C.red, fontSize: 12.5 }}>{err}</div>}
        <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-sm" onClick={() => damAsk(`幫我登記一項金融資產:${form.name || "(名稱)"},類型${DAM_TYPE_META[form.asset_type].label},並幫我搜索並確認證券代碼。`)}>交給秘書辦</button>
          <button className="btn btn-primary btn-sm" disabled={busy} onClick={submit}>{busy ? "提交中…" : "登記"}</button>
        </div>
      </div>
    </div>
  );
};

/* ---------- 資產詳情(走勢 + 指標 + 交易) ---------- */
const DamDetail = ({ asset, onClose, onChanged }) => {
  const [analysis, setAnalysis] = useDamState(null);
  const [quant, setQuant] = useDamState(null);
  const [txns, setTxns] = useDamState([]);
  const [busy, setBusy] = useDamState(false);
  const [msg, setMsg] = useDamState("");

  const load = useDamCallback(() => {
    damJson(`/api/assets/${asset.id}/analysis`).then(setAnalysis).catch(e => setAnalysis({ ok: false, error: e.message }));
    damJson(`/api/assets/${asset.id}/txns`).then(d => setTxns(d.txns || [])).catch(() => {});
  }, [asset.id]);
  useDamEffect(load, [load]);

  const fetchHistory = async () => {
    setBusy(true); setMsg("正在拉取日線歷史…");
    try {
      const r = await damPost(`/api/assets/${asset.id}/fetch-history`, { days: 500 });
      setMsg(`已入庫 ${r.imported} 個交易日`); load(); onChanged && onChanged();
    } catch (e) { setMsg(e.message || String(e)); } finally { setBusy(false); }
  };

  const runQuant = async () => {
    setBusy(true); setMsg("正在運行差分 / 回歸 / SARIMAX 量化模型…");
    try {
      const q = await damJson(`/api/assets/${asset.id}/quant?days=500&horizon=5`);
      setQuant(q);
      setMsg(`量化分析已保存: run #${q.run_id || "—"}`);
    } catch (e) { setMsg(e.message || String(e)); } finally { setBusy(false); }
  };

  const m = (analysis && analysis.metrics) || {};
  const q = quant || {};
  const capm = q.capm || {};
  const sarimax = q.sarimax || {};
  const forecasts = (sarimax.forecast_return || []).filter(v => typeof v === "number" && Number.isFinite(v));
  const metricRows = [
    ["區間收益", damPct(m.period_return_pct), damTone(m.period_return_pct)],
    ["年化收益", damPct(m.ann_return_pct), damTone(m.ann_return_pct)],
    ["年化波動率", m.ann_volatility_pct != null ? m.ann_volatility_pct + "%" : "—", DAM_C.ink],
    ["最大回撤", damPct(m.max_drawdown_pct), DAM_C.green],
    ["夏普比率", m.sharpe != null ? m.sharpe : "—", DAM_C.ink],
    ["52週位置", m.pos_in_52w_pct != null ? m.pos_in_52w_pct + "%" : "—", DAM_C.ink],
    ["MA20 / MA60", `${damNum(m.ma20)} / ${damNum(m.ma60)}`, DAM_C.ink],
    ["趨勢", m.trend || "—", DAM_C.ink],
  ];
  const txnLabel = { buy: "買入", sell: "賣出", dividend: "分紅", fee: "費用" };
  return (
    <div className="da-modal-mask da-detail-mask" onClick={onClose}>
      <div onClick={e => e.stopPropagation()} className="da-detail-modal col gap-14">
        <div className="row spread" style={{ alignItems: "flex-start" }}>
          <div className="col gap-2">
            <div style={{ fontSize: 17, fontWeight: 900 }}>{asset.name} <span className="muted" style={{ fontSize: 13 }}>{asset.symbol || "未填代碼"}</span></div>
            <div className="row gap-8" style={{ fontSize: 12.5, color: DAM_C.sub }}>
              <span>{(DAM_TYPE_META[asset.asset_type] || {}).label}</span>
              {asset.watch_only && <span className="badge badge-info" style={{ height: 20 }}>觀察倉 · 不記賬</span>}
              {asset.last_price != null && <span className="num">現價 {damNum(asset.last_price)} {asset.last_price_currency}</span>}
              {asset.last_change_pct != null && <span className="num" style={{ color: damTone(asset.last_change_pct), fontWeight: 800 }}>{damPct(asset.last_change_pct)}</span>}
              {asset.last_quote_at && <span className="num">更新 {damQuoteTime(asset.last_quote_at)}</span>}
              {!asset.watch_only && asset.market_value_cny > 0 && <span className="num">市值 {damCny(asset.market_value_cny)}</span>}
              {!asset.watch_only && asset.unrealized_pnl_cny != null && <span className="num" style={{ color: damTone(asset.unrealized_pnl_cny) }}>浮動 {damCny(asset.unrealized_pnl_cny)}({damPct(asset.unrealized_pnl_pct)})</span>}
            </div>
          </div>
          <div className="row gap-6">
            <button className="btn btn-sm" disabled={busy} onClick={fetchHistory}>拉取歷史</button>
            <button className="btn btn-sm" disabled={busy} onClick={runQuant}>量化模型</button>
            <button className="btn btn-sm" onClick={() => damAsk(`請對金融資產「${asset.name}」(id=${asset.id})做深入分析:先 asset analyze --id ${asset.id},再 asset quant --id ${asset.id},然後用通俗語言解讀差分、線性回歸、CAPM/SARIMAX 指標。`)}>AI 深度解讀</button>
            <button className="btn btn-sm" onClick={onClose}>關閉</button>
          </div>
        </div>
        {msg && <div style={{ fontSize: 12.5, color: DAM_C.blue }}>{msg}</div>}
        <DamChart series={(analysis && analysis.series) || []} />
        {analysis && analysis.ok === false && <div style={{ color: DAM_C.orange, fontSize: 12.5 }}>{analysis.error}</div>}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          {metricRows.map(([k, v, tone]) => (
            <div key={k} style={{ border: `1px solid ${DAM_C.hair}`, borderRadius: 10, padding: "10px 12px" }}>
              <div style={{ fontSize: 11.5, color: DAM_C.sub }}>{k}</div>
              <div className="num" style={{ fontSize: 15.5, fontWeight: 800, color: tone }}>{v}</div>
            </div>
          ))}
        </div>
        {analysis && analysis.disclaimer && <div className="muted" style={{ fontSize: 11 }}>{analysis.disclaimer}</div>}
        {quant && (
          <div className="col gap-8" style={{ border: `1px solid ${DAM_C.hair}`, borderRadius: 10, padding: 12 }}>
            <div className="row spread">
              <div style={{ fontSize: 14, fontWeight: 900 }}>量化模型 <span className="muted" style={{ fontSize: 12, fontWeight: 500 }}>run #{q.run_id}</span></div>
              <span className="muted" style={{ fontSize: 11 }}>{sarimax.model || "model"}</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
              {[
                ["差分自相關", q.difference?.return_autocorr_lag1 ?? "—"],
                ["線性回歸 R²", q.linear_regression?.r2 ?? "—"],
                ["CAPM β", capm.beta ?? "—"],
                ["預測均值", forecasts.length ? damPct(forecasts.reduce((a, b) => a + b, 0) / forecasts.length * 100) : "—"],
              ].map(([k, v]) => (
                <div key={k} style={{ background: "#f8fbff", borderRadius: 8, padding: "8px 10px" }}>
                  <div className="muted" style={{ fontSize: 11 }}>{k}</div>
                  <div className="num" style={{ fontSize: 14, fontWeight: 900 }}>{v}</div>
                </div>
              ))}
            </div>
            {sarimax.note && <div className="muted" style={{ fontSize: 11 }}>{sarimax.note}</div>}
          </div>
        )}
        <div className="col gap-6">
          <div style={{ fontSize: 14, fontWeight: 900 }}>交易記錄</div>
          {!txns.length && <div className="muted" style={{ fontSize: 12.5 }}>
            {asset.watch_only ? "觀察倉只跟蹤行情,暫無交易記錄。需要持倉時可讓秘書登記買入並轉為持倉。" : `暫無交易。可讓秘書登記:「${asset.name} 買入 100 股,花了 ___ 元」`}
          </div>}
          {txns.map(t => (
            <div key={t.id} className="row spread" style={{ fontSize: 12.5, padding: "7px 0", borderTop: `1px solid ${DAM_C.hair}` }}>
              <span>{t.txn_date} · <b>{txnLabel[t.txn_type] || t.txn_type}</b>{t.quantity ? ` x${damNum(t.quantity)}` : ""}</span>
              <span className="num">{damCny(t.amount_cny)}{t.realized_pnl_cny != null ? <span style={{ color: damTone(t.realized_pnl_cny), marginLeft: 8 }}>盈虧 {damCny(t.realized_pnl_cny)}</span> : null}{t.voucher_id ? <span className="muted" style={{ marginLeft: 8 }}>憑證#{t.voucher_id}</span> : null}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/* ---------- 可視化小組件 ---------- */
// 橫條:label + 數值 + 比例條(用於波動結構/風險貢獻/權重)
const DamHBar = ({ label, value, max, text, tone = DAM_C.blue, sub }) => (
  <div className="da-hbar">
    <span className="da-hbar-label" title={label}>{label}</span>
    <span className="da-hbar-track"><i style={{ width: `${Math.max(2, Math.min(100, (value || 0) / (max || 1) * 100))}%`, background: tone }}/></span>
    <b className="num">{text}</b>
    {sub && <em>{sub}</em>}
  </div>
);

// 區間儀:在 [lo,hi] 標尺上標記當前值(RSI/布林位置/Hurst)
const DamRange = ({ label, value, lo, hi, zones, fmt }) => {
  const pct = value == null ? null : Math.max(0, Math.min(100, (value - lo) / (hi - lo) * 100));
  return (
    <div className="da-range">
      <div className="da-range-head"><span>{label}</span><b className="num">{value == null ? "—" : (fmt ? fmt(value) : value)}</b></div>
      <div className="da-range-track">
        {(zones || []).map((z, i) => <i key={i} style={{ left: `${(z[0] - lo) / (hi - lo) * 100}%`, width: `${(z[1] - z[0]) / (hi - lo) * 100}%`, background: z[2] }}/>)}
        {pct != null && <u style={{ left: `${pct}%` }}/>}
      </div>
    </div>
  );
};

// 相關矩陣熱力圖(CSS grid)
const DamHeat = ({ names, matrix }) => {
  if (!matrix || !matrix.length) return null;
  const n = names.length;
  const cell = (c) => {
    const a = Math.min(Math.abs(c || 0), 1) * 0.8;
    return c >= 0 ? `rgba(255,59,48,${a})` : `rgba(0,113,227,${a})`;
  };
  return (
    <div className="da-heat" style={{ gridTemplateColumns: `minmax(56px, auto) repeat(${n}, 1fr)` }}>
      <span/>
      {names.map((nm, j) => <span key={"h" + j} className="da-heat-name" title={nm}>{nm.slice(0, 4)}</span>)}
      {matrix.map((row, i) => (
        <React.Fragment key={"r" + i}>
          <span className="da-heat-name" title={names[i]}>{names[i].slice(0, 4)}</span>
          {row.map((c, j) => (
            <span key={j} className="da-heat-cell num" style={{ background: cell(c), color: Math.abs(c || 0) > 0.55 ? "#fff" : "var(--ink-2)" }} title={`${names[i]} × ${names[j]} = ${c}`}>
              {i === j ? "1" : (c == null ? "—" : c.toFixed(2).replace("0.", "."))}
            </span>
          ))}
        </React.Fragment>
      ))}
    </div>
  );
};

// 風險-收益散點(canvas):x=年化波動, y=年化收益
const DamScatter = ({ rows, height = 210 }) => {
  const ref = useDamRef(null);
  const pts = (rows || []).filter(r => r.ann_vol_pct != null && r.ann_return_pct != null);
  useDamEffect(() => {
    const cv = ref.current;
    if (!cv || pts.length < 2) return;
    const W = cv.clientWidth || 500, H = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const xs = pts.map(p => p.ann_vol_pct), ys = pts.map(p => p.ann_return_pct);
    const x0 = 0, x1 = Math.max(...xs) * 1.15 || 1;
    const ylo = Math.min(0, ...ys) * 1.15, yhi = Math.max(...ys) * 1.15 || 1;
    const PL = 44, PR = 14, PT = 12, PB = 26;
    const X = v => PL + (W - PL - PR) * (v - x0) / (x1 - x0);
    const Y = v => PT + (H - PT - PB) * (1 - (v - ylo) / (yhi - ylo));
    ctx.font = "10px -apple-system, sans-serif";
    ctx.strokeStyle = "rgba(29,29,31,.08)";
    ctx.fillStyle = DAM_C.sub;
    for (let i = 0; i <= 4; i++) {
      const vy = ylo + (yhi - ylo) * i / 4;
      ctx.beginPath(); ctx.moveTo(PL, Y(vy)); ctx.lineTo(W - PR, Y(vy)); ctx.stroke();
      ctx.fillText(vy.toFixed(0) + "%", 6, Y(vy) + 3);
      const vx = x0 + (x1 - x0) * i / 4;
      ctx.fillText(vx.toFixed(0) + "%", X(vx) - 8, H - 8);
    }
    if (ylo < 0) { ctx.strokeStyle = "rgba(29,29,31,.3)"; ctx.beginPath(); ctx.moveTo(PL, Y(0)); ctx.lineTo(W - PR, Y(0)); ctx.stroke(); }
    pts.forEach((p, i) => {
      const tone = ["#0071E3", "#FF9F0A", "#34C759", "#5856D6", "#FF3B30", "#B8860B"][i % 6];
      ctx.beginPath(); ctx.arc(X(p.ann_vol_pct), Y(p.ann_return_pct), 5, 0, Math.PI * 2);
      ctx.fillStyle = tone; ctx.fill();
      ctx.fillStyle = "#1D1D1F";
      ctx.fillText(p.name, X(p.ann_vol_pct) + 8, Y(p.ann_return_pct) + 3);
    });
    ctx.fillStyle = DAM_C.sub;
    ctx.fillText("年化波動 →", W - 74, H - 8);
  }, [JSON.stringify(pts), height]);
  if (pts.length < 2) return null;
  return <canvas ref={ref} style={{ width: "100%", height }}/>;
};

// 三線財富路徑(真實/擬合/基準)— MK50 累積擬合路徑診斷
const DamPaths = ({ paths, height = 210 }) => {
  const ref = useDamRef(null);
  useDamEffect(() => {
    const cv = ref.current;
    if (!cv || !paths || paths.length < 2) return;
    const W = cv.clientWidth || 600, H = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const keys = [["real", "#1D1D1F", "真實"], ["fit", "#0071E3", "Eq.(5) 擬合"], ["bench", "#FF9F0A", "基準"]];
    const all = paths.flatMap(p => keys.map(([k]) => p[k])).filter(v => v != null);
    const lo = Math.min(...all), hi = Math.max(...all);
    const span = hi - lo || 1;
    const PL = 8, PR = 52, PT = 12, PB = 22;
    const x = i => PL + (W - PL - PR) * i / (paths.length - 1);
    const y = v => PT + (H - PT - PB) * (1 - (v - lo) / span);
    ctx.font = "10px -apple-system, sans-serif";
    ctx.strokeStyle = "rgba(29,29,31,.07)";
    ctx.fillStyle = "#6E6E73";
    for (let i = 0; i <= 4; i++) {
      const v = lo + span * i / 4, gy = y(v);
      ctx.beginPath(); ctx.moveTo(PL, gy); ctx.lineTo(W - PR + 4, gy); ctx.stroke();
      ctx.fillText(v.toFixed(2), W - PR + 8, gy + 3);
    }
    keys.forEach(([k, tone]) => {
      ctx.beginPath();
      paths.forEach((p, i) => { const v = p[k]; if (v == null) return; i ? ctx.lineTo(x(i), y(v)) : ctx.moveTo(x(i), y(v)); });
      ctx.strokeStyle = tone; ctx.lineWidth = k === "real" ? 1.9 : 1.4;
      if (k === "bench") ctx.setLineDash([4, 3]);
      ctx.stroke(); ctx.setLineDash([]);
    });
    // 圖例 + 首尾日期
    let lx = PL + 4;
    keys.forEach(([k, tone, label]) => {
      ctx.fillStyle = tone; ctx.fillRect(lx, 6, 14, 3);
      ctx.fillStyle = "#1D1D1F"; ctx.fillText(label, lx + 18, 11);
      lx += 18 + ctx.measureText(label).width + 14;
    });
    ctx.fillStyle = "#6E6E73";
    ctx.fillText(paths[0].date, PL, H - 7);
    const endText = paths[paths.length - 1].date;
    ctx.fillText(endText, W - PR - ctx.measureText(endText).width, H - 7);
  }, [paths && paths.length, paths && paths.length ? paths[paths.length - 1].date : "", height]);
  if (!paths || paths.length < 2) return null;
  return <canvas ref={ref} style={{ width: "100%", height }}/>;
};

// MK59 狀態機圖:四條診斷軌跡(0..1)+ 底部狀態色帶
const DAM_REGIME_TONES = { "風險偏好": "#34C759", "中性震盪": "#A8A8AD", "壓力": "#FF9F0A", "危機": "#FF3B30" };
const DamRegimeChart = ({ series, height = 230 }) => {
  const ref = useDamRef(null);
  useDamEffect(() => {
    const cv = ref.current;
    if (!cv || !series || series.length < 2) return;
    const W = cv.clientWidth || 600, H = height;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    cv.width = W * dpr; cv.height = H * dpr;
    const ctx = cv.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, W, H);
    const PL = 8, PR = 40, PT = 14, PB = 36, BAND = 10;
    const x = i => PL + (W - PL - PR) * i / (series.length - 1);
    const y = v => PT + (H - PT - PB - BAND) * (1 - v);
    ctx.font = "10px -apple-system, sans-serif";
    ctx.strokeStyle = "rgba(29,29,31,.07)";
    ctx.fillStyle = "#6E6E73";
    for (let i = 0; i <= 4; i++) {
      const v = i / 4, gy = y(v);
      ctx.beginPath(); ctx.moveTo(PL, gy); ctx.lineTo(W - PR + 4, gy); ctx.stroke();
      ctx.fillText(v.toFixed(2), W - PR + 8, gy + 3);
    }
    const lines = [["risk_on", "#34C759", "風險偏好"], ["stress", "#FF3B30", "壓力"], ["contagion", "#5856D6", "傳染"], ["drawdown_risk", "#FF9F0A", "回撤風險"]];
    lines.forEach(([k, tone]) => {
      ctx.beginPath();
      series.forEach((p, i) => i ? ctx.lineTo(x(i), y(p[k])) : ctx.moveTo(x(i), y(p[k])));
      ctx.strokeStyle = tone; ctx.lineWidth = 1.5; ctx.stroke();
    });
    // 狀態色帶
    series.forEach((p, i) => {
      ctx.fillStyle = DAM_REGIME_TONES[p.regime] || "#A8A8AD";
      const x0 = i ? (x(i - 1) + x(i)) / 2 : x(0);
      const x1 = i < series.length - 1 ? (x(i) + x(i + 1)) / 2 : x(i);
      ctx.fillRect(x0, H - PB - BAND + 4, Math.max(1, x1 - x0 + 0.5), BAND);
    });
    // 圖例 + 首尾日期
    let lx = PL + 2;
    lines.forEach(([k, tone, label]) => {
      ctx.fillStyle = tone; ctx.fillRect(lx, 4, 12, 3);
      ctx.fillStyle = "#1D1D1F"; ctx.fillText(label, lx + 16, 9);
      lx += 16 + ctx.measureText(label).width + 12;
    });
    ctx.fillStyle = "#6E6E73";
    ctx.fillText(series[0].date, PL, H - 6);
    const endText = series[series.length - 1].date;
    ctx.fillText(endText, W - PR - ctx.measureText(endText).width, H - 6);
  }, [series && series.length, series && series.length ? series[series.length - 1].date : "", height]);
  if (!series || series.length < 2) return null;
  return <canvas ref={ref} style={{ width: "100%", height }}/>;
};

/* ---------- 數據科學工作台(Quant Lab v2) ---------- */
const DAM_LAB_TABS = [
  ["quant", "計量建模"], ["risk", "風險診斷"], ["shock", "韌性"], ["regime", "狀態機"],
  ["port", "組合優化"], ["compare", "對比"], ["panel", "Panel"], ["runs", "記錄"],
];
const DAM_LAB_RUN_LABEL = { quant: "運行 Quant", risk: "運行風險診斷", shock: "運行韌性診斷", regime: "運行狀態機", port: "運行組合優化", compare: "運行對比", panel: "運行 Panel" };

const DamScienceLab = ({ assets, ask }) => {
  const tradable = (assets || []).filter(a => a.symbol);
  const [tab, setTab] = useDamState("quant");
  const [assetId, setAssetId] = useDamState("");
  const [benchmarkId, setBenchmarkId] = useDamState("");
  const [days, setDays] = useDamState(500);
  const [horizon, setHorizon] = useDamState(5);
  const [compareIds, setCompareIds] = useDamState([]);
  const [results, setResults] = useDamState({});   // {quant, risk, port, compare, panel}
  const [runs, setRuns] = useDamState([]);
  const [busy, setBusy] = useDamState("");
  const [msg, setMsg] = useDamState("");

  useDamEffect(() => {
    if (!assetId && tradable[0]) setAssetId(String(tradable[0].id));
    if (!compareIds.length && tradable.length >= 2) setCompareIds(tradable.slice(0, 4).map(a => String(a.id)));
  }, [tradable.length]);

  const selected = tradable.find(a => String(a.id) === String(assetId));
  const benchmark = tradable.find(a => String(a.id) === String(benchmarkId));
  const setResult = (key, val) => setResults(r => ({ ...r, [key]: val }));

  const loadRuns = async (switchTab = true, silent = false) => {
    if (!silent) { setBusy("runs"); setMsg(""); }
    try {
      const d = await damJson("/api/assets/analysis-runs?limit=14");
      setRuns(d.runs || []);
      if (switchTab) setTab("runs");
    } catch (e) { if (!silent) setMsg(e.message || String(e)); } finally { if (!silent) setBusy(""); }
  };

  const runTab = async (which) => {
    const target = which || tab;
    if (["quant", "risk", "shock"].includes(target) && !assetId) { setMsg("請先選擇一項有代碼的資產"); return; }
    setBusy(target); setMsg("");
    const b = benchmarkId ? `&benchmark_id=${encodeURIComponent(benchmarkId)}` : "";
    const D = Number(days) || 500;
    try {
      let d;
      if (target === "quant") d = await damJson(`/api/assets/${assetId}/quant?days=${D}&horizon=${Number(horizon) || 5}${b}`);
      else if (target === "risk") d = await damJson(`/api/assets/${assetId}/risk?days=${D}`);
      else if (target === "shock") d = await damJson(`/api/assets/${assetId}/shock?days=${D}&series=1${b}`);
      else if (target === "regime") d = await damJson(`/api/assets/regime?days=${D}&series=1`);
      else if (target === "port") d = await damJson(`/api/assets/portfolio-risk?days=${Math.min(D, 500)}`);
      else if (target === "compare") {
        if (compareIds.length < 2) { setMsg("對比至少勾選 2 個資產"); setBusy(""); return; }
        d = await damJson(`/api/assets/compare?ids=${compareIds.join(",")}&days=${Math.min(D, 500)}`);
      } else if (target === "panel") d = await damJson(`/api/assets/panel?days=${D}${b}`);
      if (d && d.ok === false) throw new Error(d.error || "運算失敗");
      setResult(target, d);
      setTab(target);
      setMsg(`已完成並留痕: run #${d.run_id || "—"}`);
      loadRuns(false, true);
    } catch (e) { setMsg(e.message || String(e)); } finally { setBusy(""); }
  };

  const runHistory = async () => {
    if (!assetId) { setMsg("請先選擇一項資產"); return; }
    setBusy("history"); setMsg("正在補充日線歷史數據…");
    try {
      const d = await damPost(`/api/assets/${assetId}/fetch-history`, { days: Number(days) || 500 });
      setMsg(`已入庫 ${d.imported || 0} 個交易日`);
    } catch (e) { setMsg(e.message || String(e)); } finally { setBusy(""); }
  };

  const askLab = () => {
    const map = {
      quant: `對「${selected?.name || "主要持倉"}」做計量建模:asset quant --id ${assetId}${benchmarkId ? ` --benchmark-id ${benchmarkId}` : ""},解讀差分/回歸/CAPM/SARIMAX,講人話。`,
      risk: `對「${selected?.name || "主要持倉"}」做風險診斷:asset risk --id ${assetId},解讀 VaR/CVaR、EWMA/GARCH 波動結構、Hurst、RSI/布林,講人話。`,
      shock: `對「${selected?.name || "主要持倉"}」做 MK50 衝擊韌性診斷:asset shock --id ${assetId}${benchmarkId ? ` --benchmark-id ${benchmarkId}` : ""},解讀 γ 衝擊加速係數、累積擬合路徑缺口和衝擊窗口復原力,講人話。`,
      regime: "跑 asset regime(MK59 市場狀態機):告訴我現在處於什麼行情狀態、已持續幾天、對比歷史中位還能持續多久、哪些前兆特徵值得盯,講人話。",
      port: "對整個倉做組合優化:asset portfolio-risk,解讀相關性、風險貢獻、三套權重建議,告訴我目前配置的問題。",
      compare: `對比這些資產:asset compare --ids ${compareIds.join(",")},告訴我哪個性價比高、相關性如何。`,
      panel: "對倉內資產跑 asset panel 面板回歸,解讀固定效應和共同市場因子。",
      runs: "查 asset runs 運行記錄,挑最近一次結果解讀。",
    };
    ask(map[tab] || map.quant);
  };

  /* --- 各標籤結果視圖 --- */
  const quant = results.quant;
  const qFit = (quant && quant.linear_regression) || {};
  const qCapm = (quant && quant.capm) || {};
  const qSarimax = (quant && quant.sarimax) || {};
  const forecast = ((qSarimax.forecast_return) || []).filter(v => typeof v === "number" && Number.isFinite(v));
  const forecastMean = forecast.length ? forecast.reduce((a, b) => a + b, 0) / forecast.length * 100 : null;
  const coefRows = qFit.coef ? Object.entries(qFit.coef) : [];

  const risk = results.risk;
  const rTail = (risk && risk.tail_risk) || {};
  const rVol = (risk && risk.volatility) || {};
  const rStr = (risk && risk.structure) || {};
  const rDist = (risk && risk.distribution) || {};
  const volBars = risk ? [
    ["全樣本", rVol.full_sample_ann_pct], ["EWMA(近期加權)", rVol.ewma_ann_pct],
    ["近20日", rVol.rolling20_ann_pct], ["近60日", rVol.rolling60_ann_pct],
    ["GARCH 當前", rVol.garch11?.current_ann_pct], ["GARCH 長期", rVol.garch11?.long_run_ann_pct],
  ].filter(x => x[1] != null) : [];
  const volMax = Math.max(1, ...volBars.map(x => x[1]));

  const port = results.port;
  const pNames = ((port && port.assets) || []).map(a => a.name);
  const pCur = (port && port.current) || {};
  const pSug = (port && port.suggestions) || {};
  const weightPlans = port ? [
    ["當前", pCur.weights_pct, DAM_C.ink],
    ["最小方差", pSug.min_variance_weights_pct, DAM_C.blue],
    ["風險平價", pSug.inverse_vol_weights_pct, DAM_C.indigo],
    ["最大夏普", pSug.max_sharpe && pSug.max_sharpe.weights_pct, DAM_C.orange],
  ].filter(p => Array.isArray(p[1])) : [];

  const compare = results.compare;
  const cmpRows = ((compare && compare.rows) || []).filter(r => !r.error);

  const panel = results.panel;
  const pFit = (panel && panel.fit) || {};
  const panelRows = (panel && panel.assets) || [];
  const featureRows = pFit.coef ? Object.entries(pFit.coef) : [];

  const emptyHint = (text) => (
    <div className="da-lab-empty">
      <b>{text}</b>
      <span>選好參數後點右上「{DAM_LAB_RUN_LABEL[tab] || "運行"}」,或直接交給秘書跑並解讀。</span>
      <button className="btn btn-sm" onClick={askLab}><Icon name="sparkle" size={12}/>讓秘書跑並解讀</button>
    </div>
  );

  const runBadgeTone = { quant: "badge-info", risk: "badge-warn", portfolio_risk: "badge-info", compare: "badge-gray", panel: "badge-gray" };

  return (
    <section className="da-science card">
      <div className="da-science-head">
        <div>
          <div className="risk-hero-eyebrow">Quant Lab</div>
          <h3>數據科學工作台</h3>
          <p>六類算法直連後端:計量建模(差分/回歸/CAPM/SARIMAX)、風險診斷(VaR/GARCH/Hurst/技術位)、組合優化(相關/風險貢獻/權重建議)、多資產對比、Panel 面板回歸。每次運算留痕,秘書可調用同一套算法並解讀。</p>
        </div>
        <div className="da-science-tabs">
          {DAM_LAB_TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "on" : ""} onClick={() => id === "runs" ? loadRuns() : setTab(id)}>{label}</button>
          ))}
        </div>
      </div>

      <div className="da-science-controls">
        {!["compare", "regime"].includes(tab) && <label>資產
          <select value={assetId} onChange={e => setAssetId(e.target.value)} disabled={["port", "panel"].includes(tab)}>
            {!tradable.length && <option value="">暫無有代碼資產</option>}
            {tradable.map(a => <option key={a.id} value={a.id}>{a.name} · {a.symbol}</option>)}
          </select>
        </label>}
        {["quant", "panel", "shock"].includes(tab) && <label>Benchmark
          <select value={benchmarkId} onChange={e => setBenchmarkId(e.target.value)}>
            <option value="">等權/無基準</option>
            {tradable.map(a => <option key={a.id} value={a.id}>{a.name} · {a.symbol}</option>)}
          </select>
        </label>}
        <label>窗口期
          <input type="number" min="60" max="1500" value={days} onChange={e => setDays(e.target.value)} />
        </label>
        {tab === "quant" && <label>預測步數
          <input type="number" min="1" max="60" value={horizon} onChange={e => setHorizon(e.target.value)} />
        </label>}
        <div className="da-science-actions">
          <button className="btn btn-sm" disabled={!!busy || !assetId} onClick={runHistory}>{busy === "history" ? "拉取中…" : "拉取歷史"}</button>
          {tab !== "runs" && <button className="btn btn-primary btn-sm" disabled={!!busy} onClick={() => runTab()}>{busy === tab ? "運算中…" : (DAM_LAB_RUN_LABEL[tab] || "運行")}</button>}
          <button className="btn btn-sm" onClick={askLab}><Icon name="sparkle" size={13}/>問秘書</button>
        </div>
      </div>
      {tab === "compare" && (
        <div className="da-cmp-picker">
          {tradable.map(a => {
            const on = compareIds.includes(String(a.id));
            return <button key={a.id} className={"da-cmp-chip" + (on ? " on" : "")}
              onClick={() => setCompareIds(ids => on ? ids.filter(x => x !== String(a.id)) : [...ids, String(a.id)])}>{a.name}</button>;
          })}
        </div>
      )}
      {msg && <div className="da-science-msg">{msg}</div>}

      {/* ===== 計量建模 ===== */}
      {tab === "quant" && (
        <div className="da-science-body">
          {!quant ? emptyHint("差分平穩性 · 線性回歸 · CAPM β/α · SARIMAX 預測") : (<>
          <div className="da-model-grid">
            {[
              ["樣本", `${quant.observations || 0} 日`, "歷史收盤價"],
              ["差分自相關", quant?.difference?.return_autocorr_lag1 ?? "—", "lag1 return"],
              ["OLS R²", qFit.r2 ?? "—", "return ~ lag1"],
              ["CAPM β", qCapm.beta ?? "—", (qCapm.benchmark && qCapm.benchmark.name) || (benchmark ? benchmark.name : "自動:倉內等權代理")],
              ["年化 α", qCapm.alpha_annual_pct != null ? damPct(qCapm.alpha_annual_pct) : "—", "CAPM alpha"],
              ["預測均值", forecastMean != null ? damPct(forecastMean) : "—", qSarimax.model || "SARIMAX/ARX"],
            ].map(([k, v, sub]) => (
              <div className="da-model-card" key={k}><span>{k}</span><b className="num">{v}</b><em>{sub}</em></div>
            ))}
          </div>
          <div className="da-science-split">
            <div>
              <div className="da-science-title">線性回歸係數</div>
              <div className="da-coef-list">
                {coefRows.map(([k, v]) => <div key={k}><span>{k}</span><b className="num">{damNum(v, 8)}</b></div>)}
              </div>
            </div>
            <div>
              <div className="da-science-title">未來 {forecast.length} 步收益率預測</div>
              <div className="da-forecast-bars">
                {forecast.map((v, i) => {
                  const h = Math.min(100, Math.abs(v) * 2500);
                  return <div key={i} className="da-forecast-bar" title={damPct(v * 100)}>
                    <i style={{ height: `${Math.max(6, h)}%`, background: v >= 0 ? DAM_C.red : DAM_C.green, alignSelf: v >= 0 ? "flex-end" : "flex-start" }}/>
                    <span className="num">{damPct(v * 100)}</span>
                  </div>;
                })}
              </div>
              {qSarimax.note && <p className="da-science-note">{qSarimax.note}</p>}
            </div>
          </div>
          </>)}
        </div>
      )}

      {/* ===== 風險診斷 ===== */}
      {tab === "risk" && (
        <div className="da-science-body">
          {!risk ? emptyHint("VaR/CVaR · EWMA/GARCH 波動結構 · Hurst · RSI/MACD/布林") : (<>
          <div className="da-model-grid">
            {[
              ["日 VaR 95%", rTail.var95_daily_pct != null ? rTail.var95_daily_pct + "%" : "—", rTail.var95_daily_cny ? `≈${damCny(rTail.var95_daily_cny)}` : "95% 的交易日虧損不超過此值"],
              ["日 CVaR 95%", rTail.cvar95_daily_pct != null ? rTail.cvar95_daily_pct + "%" : "—", "最糟 5% 天的平均虧損"],
              ["日 VaR 99%", rTail.var99_daily_pct != null ? rTail.var99_daily_pct + "%" : "—", "極端日防線"],
              ["偏度", rDist.skewness ?? "—", rDist.skewness != null ? (rDist.skewness < -0.3 ? "左尾偏厚(暴跌傾向)" : rDist.skewness > 0.3 ? "右尾偏厚" : "大致對稱") : ""],
              ["超額峰度", rDist.excess_kurtosis ?? "—", rDist.normal_rejected ? "非正態:極端日比鐘形曲線多" : "接近正態"],
              ["連漲/連跌", rStr.streaks ? `${rStr.streaks.max_up_streak} / ${rStr.streaks.max_down_streak}` : "—", rStr.streaks ? `上漲日佔比 ${rStr.streaks.up_day_pct}%` : ""],
            ].map(([k, v, sub]) => (
              <div className="da-model-card" key={k}><span>{k}</span><b className="num">{v}</b><em>{sub}</em></div>
            ))}
          </div>
          <div className="da-science-split">
            <div>
              <div className="da-science-title">年化波動結構(%)</div>
              <div className="col gap-6">
                {volBars.map(([k, v]) => <DamHBar key={k} label={k} value={v} max={volMax} text={v + "%"}
                  tone={k.includes("GARCH 當前") || k.includes("EWMA") ? DAM_C.orange : DAM_C.blue}/>)}
              </div>
              {rVol.garch11 && <p className="da-science-note">GARCH(1,1) α={rVol.garch11.alpha} β={rVol.garch11.beta};{rVol.garch11.current_ann_pct > rVol.garch11.long_run_ann_pct ? "當前波動高於長期均值 → 正處於比平時更顛簸的階段" : "當前波動低於長期均值 → 市場相對平靜"}</p>}
            </div>
            <div className="col gap-10">
              <div className="da-science-title">技術位置</div>
              <DamRange label="RSI(14)" value={rStr.rsi14} lo={0} hi={100}
                zones={[[0, 30, "rgba(52,199,89,.25)"], [70, 100, "rgba(255,59,48,.25)"]]} fmt={v => v.toFixed(1)}/>
              <DamRange label="布林帶位置" value={(rStr.bollinger || {}).position_pct} lo={0} hi={100}
                zones={[[0, 15, "rgba(52,199,89,.25)"], [85, 100, "rgba(255,59,48,.25)"]]} fmt={v => v.toFixed(0) + "%"}/>
              <DamRange label="Hurst 指數" value={rStr.hurst} lo={0.2} hi={0.8}
                zones={[[0.2, 0.45, "rgba(0,113,227,.22)"], [0.55, 0.8, "rgba(255,159,10,.25)"]]} fmt={v => v.toFixed(3)}/>
              <p className="da-science-note">RSI/布林:綠=偏冷區、紅=偏熱區(統計提示,非買賣信號)。Hurst:藍=均值回歸傾向、橙=趨勢慣性、中間=隨機遊走。{rStr.macd ? ` MACD ${rStr.macd.hist >= 0 ? "柱>0(短期動能偏多)" : "柱<0(短期動能偏空)"}。` : ""}</p>
            </div>
          </div>
          </>)}
        </div>
      )}

      {/* ===== MK50 衝擊韌性 ===== */}
      {tab === "shock" && (() => {
        const shock = results.shock;
        const eq5 = (shock && shock.eq5) || {};
        const cum = (shock && shock.cumulative) || {};
        const res = (shock && shock.resilience) || {};
        const sw = (shock && shock.shock_windows) || [];
        const lamSens = (shock && shock.lambda_sensitivity) || [];
        const split = (shock && shock.split_regression) || {};
        return (
          <div className="da-science-body">
            {!shock ? emptyHint("MK50 衝擊增強市場模型:γ 加速係數 · 累積擬合路徑 · 衝擊窗口復原力") : (<>
            <div className="da-model-grid">
              {[
                ["衝擊加速 γ", eq5.gamma ?? "—", eq5.acceleration_vulnerability ? "顯著為負:波動升級期額外受傷" : "未檢出顯著加速脆弱性"],
                ["γ 的 t 值", eq5.t_gamma ?? "—", "|t|>1.96 即 5% 顯著"],
                ["市場暴露 β", eq5.beta ?? "—", shock.benchmark],
                ["年化 α", eq5.alpha_annual_pct != null ? eq5.alpha_annual_pct + "%" : "—", "Eq.(5) 截距複利"],
                ["擬合缺口", cum.fitted_gap_pct != null ? damPct(cum.fitted_gap_pct) : "—", "正=真實跑贏模型(韌性證據)"],
                ["復原力", res.median_recovery_days != null ? `${res.median_recovery_days} 日` : "—", `${res.recovered ?? 0}/${res.windows ?? 0} 個衝擊窗口已復原`],
              ].map(([k, v, sub]) => (
                <div className="da-model-card" key={k}><span>{k}</span><b className="num">{v}</b><em>{sub}</em></div>
              ))}
            </div>
            <div className="da-science-title">累積擬合路徑診斷(真實 vs Eq.(5) 擬合 vs 基準,財富指數起點=1)</div>
            <DamPaths paths={shock.paths || []}/>
            <div className="da-science-split">
              <div>
                <div className="da-science-title">衝擊窗口與復原(Δσ 升級期)</div>
                <div className="da-panel-table">
                  <div className="da-panel-row da-shock-row da-panel-head"><span>窗口</span><span>天數</span><span>窗內收益</span><span>復原</span></div>
                  {sw.map((w, i) => (
                    <div className="da-panel-row da-shock-row" key={i}>
                      <span>{w.start}{w.days > 1 ? ` ~ ${w.end}` : ""}</span>
                      <span className="num">{w.days}</span>
                      <span className="num" style={{ color: damTone(w.in_window_return_pct) }}>{damPct(w.in_window_return_pct)}</span>
                      <span className="num">{w.recovery_days != null ? <b style={{ color: DAM_C.green }}>{w.recovery_days} 日</b> : <b style={{ color: DAM_C.orange }}>未復原</b>}</span>
                    </div>
                  ))}
                  {!sw.length && <div className="da-panel-empty">樣本內未檢出顯著衝擊窗口。</div>}
                </div>
              </div>
              <div className="col gap-10">
                <div className="da-science-title">穩健性檢驗</div>
                <div className="da-coef-list">
                  {lamSens.map(s => <div key={s.lambda}><span>λ={s.lambda} 時 γ</span><b className="num">{s.gamma}(t={s.t})</b></div>)}
                  {split.break_date && <div><span>前半樣本(至 {split.break_date})</span><b className="num">β={split.first_half?.beta} γ={split.first_half?.gamma}</b></div>}
                  {split.break_date && <div><span>後半樣本</span><b className="num">β={split.second_half?.beta} γ={split.second_half?.gamma}</b></div>}
                </div>
                {shock.verdict && <p className="da-science-note"><b>結論:</b>{shock.verdict}</p>}
                <p className="da-science-note">{shock.disclaimer}</p>
              </div>
            </div>
            </>)}
          </div>
        );
      })()}

      {/* ===== MK59 市場狀態機 ===== */}
      {tab === "regime" && (() => {
        const rg = results.regime;
        const now = (rg && rg.regime_now) || {};
        const idx = (rg && rg.indices_now) || {};
        const chg = (rg && rg.indices_change_30d) || {};
        const durs = (rg && rg.duration_stats) || [];
        const signals = (rg && rg.shift_signals) || {};
        const quality = (rg && rg.model_quality_spearman) || {};
        const nowTone = DAM_REGIME_TONES[now.label] || DAM_C.sub;
        const medNow = (durs.find(d => d.regime === now.label) || {}).median_days;
        return (
          <div className="da-science-body">
            {!rg ? emptyHint("MK59 ABM-FDP:整個倉的市場狀態診斷 · 持續時長 · 換擋前兆") : (<>
            <div className="da-regime-hero">
              <div className="da-regime-now" style={{ borderColor: nowTone }}>
                <span>當前市場狀態</span>
                <b style={{ color: nowTone }}>{now.label}</b>
                <em>自 {now.since} 已持續 <u className="num">{now.days}</u> 個交易日{medNow ? ` · 歷史中位 ${medNow} 日` : ""}</em>
              </div>
              <div className="da-model-grid" style={{ flex: 1 }}>
                {Object.entries(idx).map(([k, v]) => (
                  <div className="da-model-card" key={k}>
                    <span>{k}</span><b className="num">{v}</b>
                    <em className="num" style={{ color: damTone(chg[k]) }}>30日 {chg[k] > 0 ? "+" : ""}{chg[k]}</em>
                  </div>
                ))}
                <div className="da-model-card">
                  <span>系統張力分位</span><b className="num">{rg.energy_percentile}%</b>
                  <em>{rg.energy_percentile > 85 ? "歷史高位" : rg.energy_percentile < 30 ? "低位平靜" : "中等水平"}</em>
                </div>
              </div>
            </div>
            <div className="da-science-title">診斷軌跡與狀態色帶(綠=風險偏好 灰=中性 橙=壓力 紅=危機)</div>
            <DamRegimeChart series={rg.series || []}/>
            <div className="da-science-split">
              <div>
                <div className="da-science-title">狀態持續時長統計</div>
                <div className="da-panel-table">
                  <div className="da-panel-row da-regime-row da-panel-head"><span>狀態</span><span>次數</span><span>中位天數</span><span>最長</span></div>
                  {durs.map(d => (
                    <div className="da-panel-row da-regime-row" key={d.regime}>
                      <span><i className="da-type-dot" style={{ background: DAM_REGIME_TONES[d.regime] }}/>{d.regime}</span>
                      <span className="num">{d.episodes}</span><span className="num">{d.median_days}</span><span className="num">{d.max_days}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="col gap-10">
                <div className="da-science-title">換擋前兆(歷史上先動的特徵)</div>
                <div className="da-coef-list">
                  {Object.entries(signals).map(([k, feats]) => (
                    <div key={k}><span>{k}</span><b>{(feats || []).join(" · ") || "—"}</b></div>
                  ))}
                  {Object.entries(quality).map(([k, v]) => (
                    <div key={k}><span>擬合質量 {k}(秩相關)</span><b className="num" style={{ color: v != null && v < 0.5 ? DAM_C.orange : DAM_C.ink }}>{v}</b></div>
                  ))}
                </div>
                <p className="da-science-note">{rg.model} · 樣本 {rg.observations} 日 × {rg.assets_used} 資產。{rg.disclaimer}</p>
              </div>
            </div>
            </>)}
          </div>
        );
      })()}

      {/* ===== 組合優化 ===== */}
      {tab === "port" && (
        <div className="da-science-body">
          {!port ? emptyHint("相關矩陣 · 組合 VaR · 風險貢獻 · 三套權重建議") : (<>
          <div className="da-model-grid">
            {[
              ["組合年化波動", pCur.ann_vol_pct != null ? pCur.ann_vol_pct + "%" : "—", `樣本 ${port.observations} 個共同交易日`],
              ["組合日 VaR 95%", pCur.var95_daily_pct != null ? pCur.var95_daily_pct + "%" : "—", pCur.var95_daily_cny ? `≈${damCny(pCur.var95_daily_cny)}` : ""],
              ["分散化比率", pCur.diversification_ratio ?? "—", "越大於 1 分散效果越好"],
              ["集中度 HHI", pCur.hhi ?? "—", `最大持倉 ${pCur.max_weight_pct ?? "—"}%`],
            ].map(([k, v, sub]) => (
              <div className="da-model-card" key={k}><span>{k}</span><b className="num">{v}</b><em>{sub}</em></div>
            ))}
          </div>
          <div className="da-science-split">
            <div>
              <div className="da-science-title">相關矩陣(紅=同漲跌 藍=反向)</div>
              <DamHeat names={pNames} matrix={port.correlation}/>
              <div className="da-science-title" style={{ marginTop: 12 }}>風險貢獻(誰在貢獻組合的顛簸)</div>
              <div className="col gap-6">
                {pNames.map((nm, i) => <DamHBar key={nm} label={nm} value={pCur.risk_contribution_pct?.[i]} max={100}
                  text={(pCur.risk_contribution_pct?.[i] ?? "—") + "%"} tone={(pCur.risk_contribution_pct?.[i] || 0) > 40 ? DAM_C.red : DAM_C.indigo}/>)}
              </div>
            </div>
            <div>
              <div className="da-science-title">權重方案對比(%)</div>
              <div className="da-weight-table">
                <div className="da-weight-row da-weight-head"><span>資產</span>{weightPlans.map(([nm]) => <b key={nm}>{nm}</b>)}</div>
                {pNames.map((nm, i) => (
                  <div className="da-weight-row" key={nm}>
                    <span title={nm}>{nm}</span>
                    {weightPlans.map(([pn, ws, tone]) => (
                      <b key={pn} className="num">
                        <i style={{ width: `${Math.min(100, ws[i] || 0)}%`, background: tone }}/>
                        <u>{ws[i] ?? "—"}</u>
                      </b>
                    ))}
                  </div>
                ))}
              </div>
              {pSug.max_sharpe && <p className="da-science-note">最大夏普方案:夏普 {pSug.max_sharpe.sharpe},年化收益 {pSug.max_sharpe.ann_return_pct}% / 波動 {pSug.max_sharpe.ann_vol_pct}%(蒙特卡洛 4000 組,歷史口徑)。{port.disclaimer}</p>}
            </div>
          </div>
          </>)}
        </div>
      )}

      {/* ===== 對比 ===== */}
      {tab === "compare" && (
        <div className="da-science-body">
          {!compare ? emptyHint("多資產收益/波動/回撤/夏普橫比 + 風險收益散點") : (<>
          <DamScatter rows={cmpRows}/>
          <div className="da-panel-table">
            <div className="da-panel-row da-cmp-row da-panel-head"><span>資產</span><span>年化收益</span><span>年化波動</span><span>最大回撤</span><span>夏普</span><span>與首項相關</span></div>
            {cmpRows.map(r => (
              <div className="da-panel-row da-cmp-row" key={r.id}>
                <span>{r.name}<em>{r.symbol}</em></span>
                <span className="num" style={{ color: damTone(r.ann_return_pct) }}>{damPct(r.ann_return_pct)}</span>
                <span className="num">{r.ann_vol_pct}%</span>
                <span className="num" style={{ color: DAM_C.green }}>{r.max_drawdown_pct}%</span>
                <span className="num" style={{ fontWeight: 800 }}>{r.sharpe ?? "—"}</span>
                <span className="num">{r.corr_vs_first ?? "—"}</span>
              </div>
            ))}
          </div>
          {!!(compare.ranking_by_sharpe || []).length && <p className="da-science-note">按夏普(風險調整後收益)排序:{compare.ranking_by_sharpe.join(" > ")}。{compare.disclaimer}</p>}
          </>)}
        </div>
      )}

      {/* ===== Panel ===== */}
      {tab === "panel" && (
        <div className="da-science-body">
          {!panel ? emptyHint("倉內多資產 Panel data 固定效應回歸") : (<>
          <div className="da-panel-summary">
            <div><span>模型</span><b>{panel.model || "pooled OLS + fixed effects"}</b></div>
            <div><span>樣本</span><b className="num">{panel.observations || "—"}</b></div>
            <div><span>R²</span><b className="num">{pFit.r2 ?? "—"}</b></div>
            <div><span>市場因子</span><b className="num">{pFit.coef?.market_return ?? "—"}</b></div>
          </div>
          <div className="da-panel-table">
            <div className="da-panel-row da-panel-head"><span>資產</span><span>樣本</span><span>年化收益</span><span>年化波動</span></div>
            {panelRows.map(r => (
              <div className="da-panel-row" key={r.id}><span>{r.name}<em>{r.symbol}</em></span><span className="num">{r.observations}</span><span className="num">{damPct(r.ann_return_pct)}</span><span className="num">{damPct(r.ann_vol_pct)}</span></div>
            ))}
          </div>
          {!!featureRows.length && <div className="da-science-note">固定效應係數: {featureRows.slice(0, 6).map(([k, v]) => `${k}=${damNum(v, 6)}`).join(" · ")}</div>}
          </>)}
        </div>
      )}

      {/* ===== 運行記錄 ===== */}
      {tab === "runs" && (
        <div className="da-run-list">
          {runs.map(r => (
            <div className="da-run-item" key={r.id}>
              <span className={"badge " + (runBadgeTone[r.analysis_type] || "badge-gray")}>{r.analysis_type}</span>
              <b>run #{r.id}</b>
              <em>{r.summary?.asset || r.summary?.model || "組合模型"}</em>
              <span className="num">{r.window_days} 天 · {r.created_at}</span>
            </div>
          ))}
          {!runs.length && <div className="da-panel-empty">暫無量化運行記錄。</div>}
        </div>
      )}
    </section>
  );
};

/* 提示詞工程全部在後端(DIGITAL_ASSET_AGENT_GUIDE 注入秘書 system prompt),
   前端只發用戶能讀懂的自然語言請求,不在聊天內容裡夾帶規則。 */
/* ============================================================
   數字資產 AI 駕駛艙 — 頁面只讀:實時狀態、待辦雷達、場景指令。
   所有功能與流程(開通/部署/確權/估值/上架/訂單/結算/分潤)
   全部交給 AI 秘書通過 dm 工具鏈執行,寫操作留審計與 GL 憑證。
   ============================================================ */

const DAM_STAGE_LABELS = { created: "已登記", custody: "托管中", valuation: "已估值", listing: "上架中", trading: "交易中" };
const DAM_ORDER_STATUS_LABEL = { intent: "意向", pending_review: "合規覆核", accepted: "已受理", rejected: "已拒絕", cancelled: "已取消", settled: "已結算" };
const DAM_LISTING_TYPE = { license: "使用權", subscription: "訂閱", revenue_share: "收益權", fractional: "份額權" };
const DAM_EVENT_TYPE = { revenue: "收入", royalty: "授權費", usage_fee: "調用費", dividend: "分紅", cost: "成本" };

/* 場景指令:全部立即交給秘書;缺的信息由秘書在對話裡逐項問用戶,一問一答完成 */
const DAM_SCENES = [
  { icon: "sparkle", tone: "#0071E3", title: "開通工作區", desc: "網頁 + 專屬數據庫 + API Key,對話開通",
    prompt: "我要開通一個托管工作區。請先問我項目名稱(以及可選的資產類型和一句話說明),拿到後用 dm provision 開通,把 API Key(提醒我明文只顯示一次,立即保存)和客戶接入步驟整理給我。" },
  { icon: "pkg", tone: "#5856D6", title: "部署網頁 / 管數據庫", desc: "替客戶部署站點、建表、查數、改數",
    prompt: "我要操作某個托管工作區。請先用 dm list 把有工作區的資產列出來讓我選,然後問我要做什麼(部署/更新網頁、建表、查數、改數),再用 dm console / dm site put / dm db query / dm db exec 逐步執行,每一步把結果回報給我。" },
  { icon: "clipboard", tone: "#1D1D1F", title: "客戶接入指引", desc: "Key 簽發 + dam.py CLI 自助接入教程",
    prompt: "我要給客戶整理自助接入指引。請先用 dm list 列出資產讓我選;選定後用 dm console 檢查它的 Key 狀態,未簽發就問我是否現在簽發(dm key issue,明文只顯示一次),然後給出 dam.py 的下載命令(curl -o dam.py <域名>/api/dam/cli)與 deploy / db query / db exec / listings / order 的用法示例。" },
  { icon: "scan", tone: "#34C759", title: "盤點與確權", desc: "識別可資產化能力,登記、版本、托管",
    prompt: "請掃描當前系統,列出可資產化的數據、流程、知識、軟件、模型和 Agent 候選(dm scan),挑出最有價值的幾項給出登記與確權托管方案,逐項問我是否落庫,確認後用 dm create / dm custody 執行。" },
  { icon: "chart", tone: "#B8860B", title: "估值定價", desc: "成本 / 收益 / 市場 / AI 綜合估值留痕",
    prompt: "我要給資產估值。請先用 dm list 列出資產讓我選;選定後 dm show 看現狀,再問我開發成本、月收入、月調用量(不知道可以跳過),然後用 dm valuate 估值並解釋每個因子的影響。" },
  { icon: "shield", tone: "#FF9F0A", title: "合規上架", desc: "AI 評估 → 權益設計 → 合規預審 → 掛牌",
    prompt: "我要把資產上架交易。請先用 dm list 列資產讓我選;選定後先 dm assess 出 AI 評估報告(把分數、證據、定價建議區間講給我聽),再問我權益類型(使用權/授權權/收益權/份額權)、定價(以建議區間為基準)、份額與最小單位,用 dm compliance 做合規預審並解讀結論,通過後經我確認再 dm listing create 上架。" },
  { icon: "cpu", tone: "#16323C", title: "AI 評估官", desc: "事實評分 + 定價建議 + 巡檢,全鋼印",
    prompt: "請做一輪市場質量管理:先 dm inspect 巡檢全部在售上架(交付物哈希、工作區存活、評估時效),把問題清單和處置建議列給我;然後對還沒有評估報告或評估超過 30 天的資產逐個 dm assess,把各自的等級、分數、關鍵證據和定價建議匯總成一張表。" },
  { icon: "inbound", tone: "#0071E3", title: "處理訂單與結算", desc: "覆核、受理、收款結算,自動鋼印+交付",
    prompt: "請用 dm orders 查出全部待處理訂單(intent / pending_review / accepted),逐筆給出受理或拒絕建議(份額是否充足、合規結論、買方實名情況),先列清單問我怎麼處理;已受理的訂單問我款是否到賬、流水號是多少,確認後用 dm settle --payment-ref 結算——結算會自動鋼印封存條款並簽發限時交付鏈接,把鏈接和驗真碼整理給我發買方。" },
  { icon: "layers", tone: "#FF3B30", title: "收益與分潤", desc: "登記收入、自動分潤、付款核銷",
    prompt: "我要登記一筆資產收益並分潤。請先 dm revenues 給我看台賬,然後問我:哪個資產、金額多少、收益來源(訂閱/授權/調用等),用 dm revenue record 登記並把每位持有人的分潤明細列給我;之後問我款項是否已付給持有人,付了就用 dm revenue pay 核銷。" },
];

const DamDigitalAssetDesk = ({ ask }) => {
  const [summary, setSummary] = useDamState(null);
  const [assets, setAssets] = useDamState([]);
  const [orders, setOrders] = useDamState([]);
  const [listings, setListings] = useDamState([]);
  const [trades, setTrades] = useDamState(null);
  const [revenue, setRevenue] = useDamState(null);
  const [cmd, setCmd] = useDamState("");

  useDamEffect(() => {
    damJson("/api/digital-assets/summary").then(setSummary).catch(() => {});
    damJson("/api/digital-assets?limit=300").then(d => setAssets(d.assets || [])).catch(() => {});
    damJson("/api/digital-assets/orders?limit=100").then(d => setOrders(d.orders || [])).catch(() => {});
    damJson("/api/digital-assets/listings?limit=100").then(d => setListings(d.listings || [])).catch(() => {});
    damJson("/api/digital-assets/trades?limit=50").then(setTrades).catch(() => {});
    damJson("/api/digital-assets/revenue?limit=8").then(setRevenue).catch(() => {});
  }, []);

  const askNow = (p) => ask(p); // 帶數字資產上下文,立即交給秘書;缺的信息秘書在對話裡追問
  const go = () => { if (!cmd.trim()) return; askNow(cmd.trim()); setCmd(""); };

  /* ---- 實時統計 ---- */
  const assetCount = summary ? (summary.by_kind || []).reduce((s, x) => s + (x.count || 0), 0) : null;
  const listedCount = listings.filter(l => l.status === "listed").length;
  const stats = [
    ["資產", assetCount, DAM_C.ink],
    ["托管工作區", summary ? summary.workspaces : null, DAM_C.indigo],
    ["在售", summary ? listedCount : null, DAM_C.blue],
    ["估值總額", summary ? damCny(summary.latest_valuation_total_cny) : null, DAM_C.gold],
    ["累計成交", trades ? damCny(trades.total_amount_cny) : null, DAM_C.green],
    ["已分潤", revenue ? damCny(revenue.total_distributed_cny) : null, DAM_C.orange],
  ];

  /* ---- 待辦雷達(每項都能一鍵交給秘書) ---- */
  const fmtOrders = (list) => list.slice(0, 6).map(o => `#${o.id}《${o.listing_title}》買方 ${o.counterparty_name || "—"} ${o.units}份 ${o.amount_cny != null ? damCny(o.amount_cny) : ""}`).join(";");
  const pendReview = orders.filter(o => o.status === "pending_review");
  const pendIntent = orders.filter(o => o.status === "intent");
  const pendSettle = orders.filter(o => o.status === "accepted");
  const verifyLocked = orders.filter(o => o.payment_verify_status === "mismatch" && !["rejected", "cancelled", "settled"].includes(o.status));
  const awaitPay = pendSettle.filter(o => !o.payment_declared_at);
  const awaitReceipt = pendSettle.filter(o => o.payment_declared_at && !o.receipt_confirmed_at && o.payment_verify_status !== "mismatch");
  const readySettle = pendSettle.filter(o => o.receipt_confirmed_at && o.payment_verify_status !== "mismatch");
  const unpaidDist = (revenue?.events || []).filter(e => (e.allocation?.allocations || []).length && !e.allocation.paid);
  const reviewListings = listings.filter(l => l.status === "review");
  const disputedTrades = (trades?.trades || []).filter(t => t.acceptance_status === "disputed");
  const awaitTrades = (trades?.trades || []).filter(t => (t.acceptance_status || "pending") === "pending");
  const todos = [
    { n: pendReview.length, label: "訂單待合規覆核", tone: DAM_C.orange,
      prompt: `這些訂單在合規覆核中:${fmtOrders(pendReview)}。請逐筆核對上架合規結論與買方情況,給出受理/拒絕建議,我確認後用 dm order accept / dm order reject 執行。` },
    { n: pendIntent.length, label: "意向訂單待受理", tone: DAM_C.blue,
      prompt: `這些意向訂單等待受理:${fmtOrders(pendIntent)}。請核對剩餘份額後給出建議,我確認後用 dm order accept 受理。` },
    { n: awaitPay.length, label: "待買方付款申報", tone: DAM_C.sub,
      prompt: `這些已受理訂單還沒有買方付款申報:${fmtOrders(awaitPay)}。請列出每筆應付金額與買方聯繫方式,擬一條付款提醒(含對公賬戶要求和申報方式:買方可用自己的 Key 調 /api/dam/v1/payment/declare 或 dam.py pay);買方線下報來流水號的,用 dm payment declare 代錄。` },
    { n: awaitReceipt.length, label: "買方已付款,待賣方確認收款", tone: DAM_C.orange,
      prompt: `這些訂單買方已申報付款、等賣方確認到賬:${awaitReceipt.slice(0, 6).map(o => `#${o.id} 流水 ${o.payment_ref_declared || "—"} ${o.amount_cny != null ? damCny(o.amount_cny) : ""}${o.payment_verify_status === "match" ? "(回單已核驗一致)" : ""}`).join(";")}。請逐筆核對申報金額與流水;對大額或有疑問的先用 dm payment verify 取核對清單引導我做銀行官網回單核驗;賣方確認到賬的用 dm receipt confirm。` },
    { n: verifyLocked.length, label: "回單核驗不一致,結算已鎖", tone: DAM_C.red,
      prompt: `這些訂單回單核驗結論為「不一致」,結算已被系統鎖死:${verifyLocked.slice(0, 6).map(o => `#${o.id} ${o.counterparty_name || "—"} 流水 ${o.payment_ref_declared || "—"}:${(o.payment_verify_notes || "").slice(0, 50)}`).join(";")}。請給出處理建議(聯繫買方補證重新核驗 dm payment verify --result match,或 dm order reject 拒單),我確認後執行。` },
    { n: readySettle.length, label: "雙確認齊備可結算", tone: DAM_C.indigo,
      prompt: `這些訂單已完成付款申報+收款確認,可以結算放貨:${fmtOrders(readySettle)}。請逐筆用 dm settle 結算(自動鋼印條款、簽發限時交付鏈接並過 GL),把每筆的交付鏈接和驗真碼整理給我發買方。` },
    { n: unpaidDist.length, label: "分潤待支付", tone: DAM_C.red,
      prompt: `這些收益事件的分潤還未支付:${unpaidDist.slice(0, 6).map(e => `事件#${e.id} ${e.asset_name} 應付 ${damCny(e.allocation.total_paid_cny)}`).join(";")}。請列出每位持有人的應付明細;我付款後用 dm revenue pay --payment-ref 核銷。` },
    { n: reviewListings.length, label: "上架合規覆核中", tone: DAM_C.gold,
      prompt: `這些上架在合規覆核狀態:${reviewListings.slice(0, 6).map(l => `#${l.id}《${l.title}》(${DAM_LISTING_TYPE[l.listing_type] || l.listing_type})`).join(";")}。請解讀各自的合規結論並說明放行需要什麼條件。` },
    { n: disputedTrades.length, label: "成交爭議待處理", tone: DAM_C.red,
      prompt: `這些成交有爭議待處理:${disputedTrades.slice(0, 6).map(t => `成交#${t.id} ${t.asset_name}《${t.listing_title}》買方 ${t.counterparty_name || "—"}:${(t.dispute_reason || "").slice(0, 60)}`).join(";")}。請逐筆給出處理建議(補發交付/退款沖銷/駁回),我確認後用 dm trade resolve 完結。` },
    { n: awaitTrades.length, label: "交付待驗收", tone: DAM_C.indigo,
      prompt: `這些成交已交付待買方驗收:${awaitTrades.slice(0, 6).map(t => `成交#${t.id} ${t.asset_name} 買方 ${t.counterparty_name || "—"} 期限 ${t.acceptance_deadline || "—"}${t.delivered_at ? "(已取貨)" : "(未取貨)"}`).join(";")}。請檢查哪些臨期或還沒取貨,需要提醒買方的列出來;買方已確認的用 dm trade accept 完結。` },
  ].filter(t => t.n > 0);

  const cell = { borderTop: `1px solid ${DAM_C.hair}`, padding: "7px 4px", fontSize: 12.5 };
  const board = { border: `1px solid ${DAM_C.hair}`, borderRadius: 14, background: "var(--surface, #fff)", padding: "14px 16px", minWidth: 0 };
  const rowBtn = { cursor: "pointer", borderRadius: 8 };
  const hover = {
    onMouseEnter: (e) => { e.currentTarget.style.background = "rgba(0,113,227,0.06)"; },
    onMouseLeave: (e) => { e.currentTarget.style.background = "transparent"; },
  };

  return (
    <div className="da-canvas">
      {/* ===== Hero:標題 + 命令欄 + 實時數據 ===== */}
      <div className="da-hero da-digital-hero" style={{ alignItems: "flex-start" }}>
        <div style={{ flex: "1 1 380px" }}>
          <div className="risk-hero-eyebrow">AI 數字資產市場</div>
          <div className="da-hero-word" style={{ fontSize: 26 }}>跟秘書說,就辦好了</div>
          <div className="risk-hero-line">開通、部署、確權、估值、上架、交易、分潤——全部由 AI 秘書調用後端工具完成,每一步留審計、過總賬。</div>
          <div className="row gap-8" style={{ marginTop: 14, alignItems: "center" }}>
            <input className="input" style={{ flex: 1, minWidth: 220, height: 38, fontSize: 13.5 }}
              placeholder='直接吩咐:如「給客戶官網開個工作區」「3 號訂單款到了,流水 2026...,結算」'
              value={cmd} onChange={e => setCmd(e.target.value)} onKeyDown={e => e.key === "Enter" && go()}/>
            <button className="btn btn-primary" style={{ height: 38, flex: "none" }} onClick={go} disabled={!cmd.trim()}>
              <Icon name="sparkle" size={14}/>交給秘書
            </button>
          </div>
        </div>
        <div className="row gap-10" style={{ flex: "none", flexWrap: "wrap", justifyContent: "flex-end", maxWidth: 400 }}>
          {stats.map(([k, v, tone]) => (
            <div key={k} style={{ textAlign: "right", minWidth: 88 }}>
              <div className="num" style={{ fontSize: 19, fontWeight: 900, color: tone }}>{v === null || v === undefined ? "—" : v}</div>
              <div style={{ fontSize: 11, color: DAM_C.sub, fontWeight: 800 }}>{k}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ===== 待辦雷達 ===== */}
      {todos.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: `repeat(auto-fit, minmax(190px, 1fr))`, gap: 10 }}>
          {todos.map(t => (
            <button key={t.label} onClick={() => askNow(t.prompt)}
              style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 14px", borderRadius: 12, textAlign: "left",
                border: `1px solid ${t.tone}55`, background: t.tone + "0D", cursor: "pointer" }}>
              <span className="num" style={{ fontSize: 24, fontWeight: 900, color: t.tone, flex: "none" }}>{t.n}</span>
              <span style={{ minWidth: 0 }}>
                <b style={{ display: "block", fontSize: 13, color: DAM_C.ink }}>{t.label}</b>
                <em style={{ fontSize: 11, color: DAM_C.sub, fontStyle: "normal" }}>點擊交給秘書處理</em>
              </span>
            </button>
          ))}
        </div>
      )}

      {/* ===== 場景指令 ===== */}
      <section className="da-digital-section">
        <div className="da-digital-section-head">
          <div>
            <h3>場景指令</h3>
            <p>點任意卡片即交給秘書:它會先做查詢準備,缺的信息(項目名、金額、流水號)在對話裡逐項問你,一問一答辦完全程。</p>
          </div>
        </div>
        <div className="da-digital-type-grid">
          {DAM_SCENES.map(s => (
            <button key={s.title} className="da-digital-type" onClick={() => askNow(s.prompt)}>
              <span style={{ background: s.tone + "18", color: s.tone }}><Icon name={s.icon} size={18}/></span>
              <b>{s.title}</b>
              <em>{s.desc}</em>
              <strong style={{ color: s.tone }}>交給秘書 →</strong>
            </button>
          ))}
        </div>
      </section>

      {/* ===== 實況看板(只讀;點任意行帶上下文問秘書) ===== */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(330px, 1fr))", gap: 12 }}>
        <div style={board}>
          <div className="row spread" style={{ alignItems: "center", marginBottom: 6 }}>
            <b style={{ fontSize: 13.5 }}>資產實況 · {assets.length}</b>
            <button className="btn btn-sm" onClick={() => askNow("請用 dm summary 和 dm list 給我一份資產台賬總覽:各類型數量、生命週期分布、估值總額,並指出哪些資產該推進下一步。")}>台賬總覽</button>
          </div>
          {assets.length === 0 ? <div className="da-panel-empty">暫無資產。用「開通工作區」或「盤點與確權」開始。</div> : assets.slice(0, 8).map(a => (
            <div key={a.id} className="row spread" style={{ ...cell, ...rowBtn, alignItems: "center" }} {...hover}
              onClick={() => askNow(`資產 #${a.id}「${a.name}」(${a.asset_no},${a.kind_label || a.asset_kind},階段 ${DAM_STAGE_LABELS[a.lifecycle_stage] || a.lifecycle_stage || "—"})。請 dm show 查看詳情,匯報確權、估值、上架與工作區狀態,並建議下一步。`)}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                <b>{a.name}</b> <span style={{ color: DAM_C.sub, fontSize: 11.5 }}>{a.kind_label || a.asset_kind} · {DAM_STAGE_LABELS[a.lifecycle_stage] || a.lifecycle_stage || "—"}</span>
              </span>
              <span className="row gap-8" style={{ flex: "none", alignItems: "center" }}>
                {a.workspace && <span className="badge badge-info" style={{ fontSize: 10.5, height: 18 }}>已托管</span>}
                <span className="num" style={{ fontSize: 12, color: DAM_C.sub }}>{a.latest_valuation ? damCny(a.latest_valuation.valuation_cny) : "未估值"}</span>
              </span>
            </div>
          ))}
        </div>

        <div style={board}>
          <div className="row spread" style={{ alignItems: "center", marginBottom: 6 }}>
            <b style={{ fontSize: 13.5 }}>市場實況 · 在售 {listedCount}</b>
            <button className="btn btn-sm" onClick={() => askNow("請用 dm listings 和 dm trades 給我市場總覽:在售上架、近期成交、累計成交額,並指出哪些上架可以推一把。")}>市場總覽</button>
          </div>
          {listings.filter(l => l.status === "listed").slice(0, 4).map(l => (
            <div key={l.id} className="row spread" style={{ ...cell, ...rowBtn, alignItems: "center" }} {...hover}
              onClick={() => askNow(`上架 #${l.id}《${l.title}》(${l.asset_name},${DAM_LISTING_TYPE[l.listing_type] || l.listing_type},單價 ${l.price_cny != null ? damCny(l.price_cny) : "面議"})。我想為它登記一筆買單:請先問我買方名稱和份數,確認金額後用 dm order create 執行,並告訴我後續受理與結算流程。`)}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                <b>《{l.title}》</b> <span style={{ color: DAM_C.sub, fontSize: 11.5 }}>{l.asset_name} · {DAM_LISTING_TYPE[l.listing_type] || l.listing_type}</span>
              </span>
              <span className="num" style={{ flex: "none", fontSize: 12.5, fontWeight: 800 }}>{l.price_cny != null ? damCny(l.price_cny) : "面議"}</span>
            </div>
          ))}
          {(trades?.trades || []).slice(0, 3).map(t => (
            <div key={"t" + t.id} className="row spread" style={{ ...cell, alignItems: "center" }}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: DAM_C.sub, fontSize: 12 }}>
                成交 · {t.asset_name}《{t.listing_title}》× {damNum(t.units)} · {t.counterparty_name || "—"}
              </span>
              <span className="row gap-6" style={{ flex: "none", alignItems: "center" }}>
                <b className="num" style={{ fontSize: 12.5, color: DAM_C.green }}>{damCny(t.amount_cny)}</b>
                {t.voucher_id && <span style={{ fontSize: 10.5, color: DAM_C.sub }}>憑證#{t.voucher_id}</span>}
              </span>
            </div>
          ))}
          {(revenue?.events || []).slice(0, 3).map(ev => (
            <div key={"r" + ev.id} className="row spread" style={{ ...cell, ...rowBtn, alignItems: "center" }} {...hover}
              onClick={() => askNow(`收益事件 #${ev.id}(${ev.asset_name},${DAM_EVENT_TYPE[ev.event_type] || ev.event_type},${damCny(ev.amount_cny)})。請用 dm revenues 帶出它的分潤明細與支付狀態,未付的列出應付名單。`)}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: DAM_C.sub, fontSize: 12 }}>
                {DAM_EVENT_TYPE[ev.event_type] || ev.event_type} · {ev.asset_name}{ev.source_ref ? ` · ${ev.source_ref}` : ""}
              </span>
              <span className="row gap-6" style={{ flex: "none", alignItems: "center" }}>
                <b className="num" style={{ fontSize: 12.5, color: ev.event_type === "cost" ? DAM_C.red : DAM_C.ink }}>{damCny(ev.amount_cny)}</b>
                {(ev.allocation?.allocations || []).length > 0 && (
                  <span style={{ fontSize: 10.5, fontWeight: 800, color: ev.allocation.paid ? DAM_C.green : DAM_C.orange }}>
                    {ev.allocation.paid ? "已分潤" : "待付分潤"}
                  </span>
                )}
              </span>
            </div>
          ))}
          {listedCount === 0 && !(trades?.trades || []).length && <div className="da-panel-empty">暫無在售與成交。用「合規上架」把資產推向市場。</div>}
        </div>
      </div>

      <div className="muted" style={{ fontSize: 11.5, textAlign: "center", padding: "2px 0 6px" }}>
        本頁只讀。所有寫操作由 AI 秘書執行並留審計;資金動作自動生成總賬憑證,平台不收款、不託管資金。
      </div>
    </div>
  );
};

/* ============================================================
   數字市場 — 在售資產櫥窗(只讀):瀏覽、行情、點卡片交給秘書。
   下單/結算/分潤全部走秘書對話與安全交易鏈,本頁不出現任何表單。
   ============================================================ */
const DAM_MARKET_RIGHT_META = {
  license: ["使用權", "#0071E3"], subscription: ["訂閱", "#34C759"],
  revenue_share: ["收益權", "#FF9F0A"], fractional: ["份額權", "#FF3B30"],
};
const DAM_MARKET_KIND_META = {
  software: ["軟件", "pkg"], agent: ["AI Agent", "sparkle"], data: ["數據", "inbound"],
  model: ["算法模型", "cpu"], knowledge: ["知識", "layers"], process: ["流程", "clipboard"],
  project: ["項目", "chart"], other: ["其他", "layers"],
};

const DamMarketDesk = ({ ask }) => {
  const [listings, setListings] = useDamState(null);
  const [trades, setTrades] = useDamState(null);
  const [revenue, setRevenue] = useDamState(null);
  const [ftype, setFtype] = useDamState("all");
  const [fkind, setFkind] = useDamState("all");
  const [cmd, setCmd] = useDamState("");
  const [mscope, setMscope] = useDamState("own");      // own=本公司市場 / common=共同市場
  const [common, setCommon] = useDamState(null);        // {listings, current_tenant}

  useDamEffect(() => {
    damJson("/api/digital-assets/listings?status=listed&limit=200").then(d => setListings(d.listings || [])).catch(() => setListings([]));
    damJson("/api/digital-assets/trades?limit=30").then(setTrades).catch(() => {});
    damJson("/api/digital-assets/revenue?limit=1").then(setRevenue).catch(() => {});
  }, []);
  useDamEffect(() => {
    if (mscope === "common" && common === null) {
      damJson("/api/digital-assets/common-market").then(setCommon).catch(() => setCommon({ listings: [] }));
    }
  }, [mscope]);

  const go = () => { if (!cmd.trim()) return; ask(cmd.trim()); setCmd(""); };
  const askDetail = (l) => ask(`數字市場上架 #${l.id}《${l.title}》——資產「${l.asset_name}」(${l.asset_no},${(DAM_MARKET_KIND_META[l.asset_kind] || [l.asset_kind])[0]}),權益類型 ${(DAM_MARKET_RIGHT_META[l.listing_type] || [l.listing_type])[0]},單價 ${l.price_cny != null ? damCny(l.price_cny) : "面議"},剩餘 ${l.units_remaining == null ? "不限" : damNum(l.units_remaining)} 份${l.assessment ? `,AI 評估 ${l.assessment.grade}(${l.assessment.overall_score ?? l.assessment.score} 分)` : ",尚無 AI 評估"}。請 dm show 帶出該資產的完整檔案(簡介、版本、確權托管、估值、合規結論)${l.assessment ? ",並引用最新 AI 評估報告的維度分與證據" : ",並建議先 dm assess 出 AI 評估報告"},幫我判斷這個上架值不值得買。`);
  const askOrder = (l) => ask(`我想購買數字市場上架 #${l.id}《${l.title}》(${l.asset_name},單價 ${l.price_cny != null ? damCny(l.price_cny) : "面議"})。請先問我買方名稱、實名聯繫方式和購買份數,核對剩餘份額後用 dm order create 登記訂單,然後告訴我接下來的安全交易流程(受理 → 對公轉賬 → 付款申報 → 收款確認 → 結算交付)。`);

  const isCommon = mscope === "common";
  const all = isCommon ? ((common && common.listings) || []) : (listings || []);
  const loading = isCommon ? common === null : listings === null;
  const myTenant = (common && common.current_tenant) || "";
  const kinds = [...new Set(all.map(l => l.asset_kind))];
  const items = all.filter(l => (ftype === "all" || l.listing_type === ftype) && (fkind === "all" || l.asset_kind === fkind));
  const askForeign = (l) => ask(`共同市場上架「${l.company}」公司的 ${l.ref}《${l.title}》(${l.asset_name},${(DAM_MARKET_RIGHT_META[l.listing_type] || [l.listing_type])[0]},單價 ${l.price_cny != null ? damCny(l.price_cny) : "面議"}${l.assessment ? `,AI 評估 ${l.assessment.grade}` : ""})。我想跨公司購買:請給我兩條路——① 自助下單:用我的工作區 API Key 執行 python dam.py order ${l.ref} --units 份數 --contact 實名聯繫方式(下單後 dam.py orders 跟蹤、dam.py pay ${l.ref.split("#")[0]}#訂單號 申報付款、confirm 驗收),把命令和完整流程寫清楚;② 沒有 Key 的話,先問我買方名稱與聯繫方式,整理正式購買意向書(含上架全局編號、價格、AI 評估徽章)讓我發給「${l.company}」。`);
  const tradeRows = trades?.trades || [];
  const monthKey = new Date().toISOString().slice(0, 7);
  const monthAmt = tradeRows.filter(t => (t.settled_at || "").startsWith(monthKey)).reduce((s, t) => s + (t.amount_cny || 0), 0);
  const topAssets = Object.entries(tradeRows.reduce((m, t) => { m[t.asset_name] = (m[t.asset_name] || 0) + (t.amount_cny || 0); return m; }, {}))
    .sort((a, b) => b[1] - a[1]).slice(0, 4);

  const soldPct = (l) => {
    if (l.units_offered == null || !l.units_offered) return null;
    return Math.min(100, Math.round(100 * (l.units_sold || 0) / l.units_offered));
  };

  return (
    <div className="da-canvas">
      <div className="da-market-hero">
        <div style={{ flex: "1 1 360px", minWidth: 0 }}>
          <div className="da-market-eyebrow">企業數字資產市場</div>
          <div className="da-market-title">數字市場</div>
          <div className="da-market-line">軟件、數據、模型、Agent 的使用權與權益在這裡流通——條款鋼印、擔保交付、全程過賬。買賣都交給 AI 秘書。</div>
          <div className="row gap-8" style={{ marginTop: 14, alignItems: "center" }}>
            <input className="input da-market-ask" placeholder='想找什麼?直接問:「有沒有能直接用的庫存分析模型」「幫我把 XX 上架」'
              value={cmd} onChange={e => setCmd(e.target.value)} onKeyDown={e => e.key === "Enter" && go()}/>
            <button className="btn btn-primary" style={{ height: 38, flex: "none" }} disabled={!cmd.trim()} onClick={go}><Icon name="sparkle" size={14}/>問秘書</button>
          </div>
        </div>
        <div className="da-market-stats">
          {[["在售", all.length, "#7CC4FF"],
            ["本月成交", damCny(monthAmt), "#7CFFB2"],
            ["累計成交", trades ? damCny(trades.total_amount_cny) : "—", "#FFD479"],
            ["已分潤", revenue ? damCny(revenue.total_distributed_cny) : "—", "#FFA8A8"]].map(([k, v, tone]) => (
            <div key={k}><b className="num" style={{ color: tone }}>{v}</b><span>{k}</span></div>
          ))}
        </div>
      </div>

      <div className="da-market-chips">
        <span className="da-market-chip-label">貨架</span>
        <button className={!isCommon ? "on" : ""} onClick={() => setMscope("own")}>本公司市場</button>
        <button className={isCommon ? "on" : ""} onClick={() => setMscope("common")} style={isCommon ? {} : { borderColor: "#1c2340", color: "#1c2340", fontWeight: 800 }}>
          🌐 共同市場{common && common.listings ? ` · ${common.listings.length}` : ""}
        </button>
        <span className="da-market-chip-label" style={{ marginLeft: 10 }}>權益</span>
        {[["all", "全部"], ...Object.entries(DAM_MARKET_RIGHT_META).map(([k, [label]]) => [k, label])].map(([k, label]) => (
          <button key={k} className={ftype === k ? "on" : ""} onClick={() => setFtype(k)}>{label}</button>
        ))}
        {kinds.length > 1 && <>
          <span className="da-market-chip-label" style={{ marginLeft: 10 }}>類型</span>
          {[["all", "全部"], ...kinds.map(k => [k, (DAM_MARKET_KIND_META[k] || [k])[0]])].map(([k, label]) => (
            <button key={"k" + k} className={fkind === k ? "on" : ""} onClick={() => setFkind(k)}>{label}</button>
          ))}
        </>}
      </div>

      {loading ? (
        <div className="da-panel-empty">載入{isCommon ? "共同" : ""}市場…</div>
      ) : items.length === 0 ? (
        <section className="da-digital-section" style={{ padding: "38px 20px", textAlign: "center" }}>
          <div style={{ fontSize: 15, fontWeight: 800, marginBottom: 6 }}>{all.length === 0 ? (isCommon ? "共同市場暫無上架" : "市場虛位以待") : "沒有符合篩選的上架"}</div>
          <div className="muted" style={{ fontSize: 12.5, marginBottom: 14 }}>{all.length === 0 ? (isCommon ? "成為第一個發布者:有 AI 評估報告的資產,上架時選「共同市場」即可全平台可見。" : "把第一個資產推上貨架:確權 → 估值 → 合規 → 上架,秘書全程代辦。") : "換個篩選條件,或讓秘書幫你找。"}</div>
          <button className="btn btn-primary btn-sm" onClick={() => ask(all.length === 0 ? (isCommon ? "我想把資產發布到共同市場。請先 dm list 列資產讓我選,沒有評估報告的先 dm assess,然後 dm listing create --market public 或對已有上架 dm listing visibility --to public。" : "我想把一個資產上架到數字市場。請先 dm list 列出已登記資產讓我選(沒有就先幫我登記),然後走權益設計 → dm compliance 合規預審 → dm listing create 上架。") : "請用 dm listings 幫我找:" + (ftype !== "all" ? (DAM_MARKET_RIGHT_META[ftype] || [ftype])[0] + "類" : "") + "在售資產,並推薦最值得看的。")}>
            <Icon name="sparkle" size={13}/>{all.length === 0 ? (isCommon ? "發布到共同市場" : "交給秘書上架") : "讓秘書找找"}
          </button>
        </section>
      ) : (
        <div className="da-market-grid">
          {items.map(l => {
            const [rightLabel, tone] = DAM_MARKET_RIGHT_META[l.listing_type] || [l.listing_type, "#6E6E73"];
            const [kindLabel, kindIcon] = DAM_MARKET_KIND_META[l.asset_kind] || [l.asset_kind, "layers"];
            const pct = soldPct(l);
            const foreign = isCommon && l.tenant_slug && l.tenant_slug !== myTenant;
            return (
              <div key={l.ref || l.id} className="da-market-card" onClick={() => (foreign ? askForeign(l) : askDetail(l))} role="button" tabIndex={0}>
                <div className="da-market-card-head">
                  <span className="da-market-kind"><Icon name={kindIcon} size={15}/>{kindLabel}{isCommon && l.company ? <span style={{ color: foreign ? "#1c2340" : DAM_C.blue, fontWeight: 900 }}> · {l.company}{foreign ? "" : "(本公司)"}</span> : null}</span>
                  <span className="row gap-6" style={{ alignItems: "center" }}>
                    {l.assessment && (
                      <span className="da-market-right" title={`AI 評估 ${l.assessment.overall_score ?? l.assessment.score} 分(準則鋼印可驗真)`}
                        style={{ color: ({ A: "#0a7f3f", B: "#0071E3", C: "#FF9F0A", D: "#FF3B30" })[l.assessment.grade] || "#6E6E73",
                                 borderColor: "transparent", background: ({ A: "#0a7f3f", B: "#0071E3", C: "#FF9F0A", D: "#FF3B30" })[l.assessment.grade] + "16" }}>
                        AI·{l.assessment.grade}
                      </span>
                    )}
                    <span className="da-market-right" style={{ color: tone, borderColor: tone + "66", background: tone + "12" }}>{rightLabel}</span>
                  </span>
                </div>
                <div className="da-market-card-title">《{l.title}》</div>
                <div className="da-market-card-asset num">{l.asset_no} · {l.asset_name}</div>
                <div className="da-market-card-summary">{l.asset_summary || "賣方未填寫簡介——點卡片讓秘書調出完整檔案。"}</div>
                <div className="da-market-card-price">
                  <b className="num">{l.price_cny != null ? damCny(l.price_cny) : "面議"}</b>
                  <span>{l.units_remaining == null ? "不限量" : `剩餘 ${damNum(l.units_remaining)} 份`}{l.min_unit > 1 ? ` · ${damNum(l.min_unit)} 份起` : ""}</span>
                </div>
                {pct !== null && (
                  <div className="da-market-bar" title={`已售 ${pct}%`}><i style={{ width: pct + "%", background: tone }}/></div>
                )}
                <div className="da-market-card-actions">
                  {foreign ? (
                    <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); askForeign(l); }}><Icon name="sparkle" size={12}/>購買意向</button>
                  ) : (<>
                    <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); askDetail(l); }}>詳情</button>
                    <button className="btn btn-primary btn-sm" onClick={(e) => { e.stopPropagation(); askOrder(l); }}><Icon name="sparkle" size={12}/>我要購買</button>
                  </>)}
                </div>
              </div>
            );
          })}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1fr)", gap: 12 }}>
        <section className="da-digital-section" style={{ padding: "14px 16px" }}>
          <b style={{ fontSize: 13.5 }}>最近成交</b>
          {tradeRows.length === 0 ? <div className="muted" style={{ fontSize: 12.5, padding: "8px 0" }}>暫無成交。</div> : tradeRows.slice(0, 6).map(t => (
            <div key={t.id} className="row spread" style={{ fontSize: 12.5, padding: "6px 0", borderTop: "1px solid rgba(29,29,31,.08)", alignItems: "center" }}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {t.asset_name}《{t.listing_title}》× {damNum(t.units)} <span className="muted">· {t.counterparty_name || "—"} · {(t.settled_at || "").slice(0, 10)}</span>
              </span>
              <b className="num" style={{ flex: "none", color: DAM_C.green }}>{damCny(t.amount_cny)}</b>
            </div>
          ))}
        </section>
        <section className="da-digital-section" style={{ padding: "14px 16px" }}>
          <b style={{ fontSize: 13.5 }}>成交榜</b>
          {topAssets.length === 0 ? <div className="muted" style={{ fontSize: 12.5, padding: "8px 0" }}>成交後自動生成。</div> : topAssets.map(([name, amt], i) => (
            <div key={name} className="row spread" style={{ fontSize: 12.5, padding: "6px 0", borderTop: "1px solid rgba(29,29,31,.08)", alignItems: "center" }}>
              <span style={{ minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}><b className="num" style={{ color: DAM_C.sub, marginRight: 8 }}>{i + 1}</b>{name}</span>
              <b className="num" style={{ flex: "none" }}>{damCny(amt)}</b>
            </div>
          ))}
        </section>
      </div>

      <div className="muted" style={{ fontSize: 11.5, textAlign: "center", padding: "2px 0 6px" }}>
        交易走安全鏈:實名下單 → 合規閘 → 付款申報/收款確認(鋼印)→ 結算交付(限時鏈接+驗收期)。平台不收款、不託管資金。
      </div>
    </div>
  );
};

/* ---------- 主頁面 ---------- */
const PageAssets = () => {
  const [assets, setAssets] = useDamState([]);
  const [portfolio, setPortfolio] = useDamState({});
  const [loading, setLoading] = useDamState(true);
  const [refreshing, setRefreshing] = useDamState(false);
  const [toast, setToast] = useDamState("");
  const [showRegister, setShowRegister] = useDamState(false);
  const [detail, setDetail] = useDamState(null);
  const [assetScope, setAssetScope] = useDamState("financial");

  const [autoOn, setAutoOn] = useDamState(() => (window.localStorage.getItem("dam.autorefresh") || "1") === "1");
  const [lastUpdate, setLastUpdate] = useDamState(null);
  const refreshLock = useDamRef(false);
  const [sparks, setSparks] = useDamState({});      // {assetId: [closes...60日]}
  const sparkLoaded = useDamRef(new Set());

  const load = useDamCallback(async () => {
    try {
      const [a, p] = await Promise.all([damJson("/api/assets"), damJson("/api/assets/portfolio")]);
      setAssets(a.assets || []);
      setPortfolio(p || {});
    } catch (e) { setToast(e.message || String(e)); }
    setLoading(false);
  }, []);
  useDamEffect(() => { load(); }, [load]);

  const refresh = async () => {
    if (refreshing) return;
    setRefreshing(true); setToast("正在刷新行情…");
    try {
      const r = await damPost("/api/assets/refresh", {});
      const fails = Object.values(r.results || {}).filter(x => !x.ok).length;
      setToast(`已刷新 ${r.refreshed}/${r.total} 項行情` + (fails ? `(${fails} 項失敗,詳見資產卡)` : ""));
      await load();
      setLastUpdate(new Date());
    } catch (e) { setToast(e.message || String(e)); }
    setRefreshing(false);
  };

  // 自動更新:服務器心跳每分鐘刷新行情並落庫;頁面每 30 秒輕量讀庫同步
  // (不觸發外部行情調用,秘書剛記的賬、後台剛拉的歷史都能及時反映)。
  const silentRefresh = useDamCallback(async () => {
    if (refreshLock.current || document.hidden) return;
    refreshLock.current = true;
    try {
      await load();
      setLastUpdate(new Date());
    } catch {} finally { refreshLock.current = false; }
  }, [load]);

  useDamEffect(() => {
    window.localStorage.setItem("dam.autorefresh", autoOn ? "1" : "0");
    if (!autoOn) return;
    silentRefresh();
    const timer = setInterval(silentRefresh, 30000);
    const onVis = () => { if (!document.hidden) silentRefresh(); };
    document.addEventListener("visibilitychange", onVis);
    return () => { clearInterval(timer); document.removeEventListener("visibilitychange", onVis); };
  }, [autoOn, silentRefresh]);

  // 火花線:每個有代碼的資產取 60 日收盤入卡片(讀庫,輕量;每資產只取一次)
  useDamEffect(() => {
    const targets = assets.filter(a => a.symbol && !sparkLoaded.current.has(a.id));
    if (!targets.length) return;
    targets.forEach(a => sparkLoaded.current.add(a.id));
    Promise.all(targets.map(a =>
      damJson(`/api/assets/${a.id}/history?days=60`)
        .then(d => [a.id, (d.series || []).map(p => p.close)])
        .catch(() => [a.id, null])
    )).then(pairs => {
      setSparks(prev => {
        const next = { ...prev };
        pairs.forEach(([id, closes]) => { if (closes && closes.length > 1) next[id] = closes; });
        return next;
      });
    });
  }, [assets]);

  const holdings = assets.filter(a => !a.watch_only);
  const watching = assets.filter(a => a.watch_only);
  const pnl = portfolio.unrealized_pnl_cny;
  const missingCode = assets.filter(a => !a.symbol);
  const missingQuote = assets.filter(a => a.symbol && a.last_price == null);
  const volatileAssets = assets.filter(a => Math.abs(Number(a.last_change_pct || 0)) >= (a.asset_type === "crypto" ? 8 : 3));
  const health = missingCode.length || missingQuote.length ? { word: "待接入", tone: DAM_C.orange }
    : volatileAssets.length ? { word: "波動中", tone: DAM_C.red }
    : { word: "已托管", tone: DAM_C.green };
  const ask = (prompt) => damAsk(prompt); // 持倉明細秘書自己用 asset 工具查,不塞進聊天內容
  const askDigital = (prompt) => damAsk(prompt); // 規則在後端 system prompt,聊天只發自然語言
  const askAsset = (a, action) => {
    const base = `「${a.name}」(id=${a.id},代碼${a.symbol || "未填"},類型${(DAM_TYPE_META[a.asset_type] || {}).label || a.asset_type},${a.watch_only ? "觀察倉不記賬" : `持有${a.quantity || 0}`},現價${a.last_price ?? "未取"})`;
    if (action === "quote") return ask(`請處理 ${base} 的代碼與行情:缺代碼先 asset resolve 搜候選並讓我確認,已有代碼則刷新行情、匯率和漲跌幅,最後列出資料來源與更新時間。`);
    if (action === "buy") return ask(`我要${a.watch_only ? "把觀察倉轉成持倉並" : ""}買入 ${base}。請追問買入數量、成交價/總額、手續費、支付賬戶和交易日期,然後用 asset buy 登記並生成財務記賬。`);
    if (a.watch_only) return ask(`請先說明 ${base} 是觀察倉:只跟蹤行情、不參與賣出/分紅/記賬。若我要交易,先追問是否登記買入轉為持倉。`);
    if (action === "sell") return ask(`我要賣出 ${base}。請追問賣出數量、成交價/總額、手續費、收款賬戶和交易日期,計算已實現盈虧,然後用 asset sell 登記並生成財務記賬。`);
    if (action === "dividend") return ask(`我要登記 ${base} 的分紅/派息。請追問分紅金額、稅費、到賬賬戶和日期,然後用 asset dividend 登記並生成財務記賬。`);
  };

  const Th = ({ children, right }) => <th style={{ fontSize: 11.5, color: DAM_C.sub, fontWeight: 700, textAlign: right ? "right" : "left", padding: "8px 10px", borderBottom: `1px solid ${DAM_C.hair}`, whiteSpace: "nowrap" }}>{children}</th>;
  const Td = ({ children, right, tone, bold }) => <td className="num" style={{ fontSize: 12.5, padding: "9px 10px", textAlign: right ? "right" : "left", color: tone || DAM_C.ink, fontWeight: bold ? 800 : 500, borderBottom: `1px solid ${DAM_C.hair}`, whiteSpace: "nowrap" }}>{children}</td>;

  const quoteStatus = (a) => {
    if (!a.symbol) return <span className="da-quote-cell pending"><b>待補代碼</b></span>;
    if (a.last_price == null) return <span className="da-quote-cell pending"><b>待刷新</b></span>;
    return <span className="da-quote-cell"><b>{damNum(a.last_price)} {a.last_price_currency || ""}</b>{a.last_quote_at && <em>更新 {damQuoteTime(a.last_quote_at)}</em>}</span>;
  };

  const assetRow = (a) => (
    <tr key={a.id} style={{ cursor: "pointer" }} onClick={() => setDetail(a)}>
      <Td bold>
        <span style={{ display: "inline-block", width: 8, height: 8, borderRadius: 2, background: (DAM_TYPE_META[a.asset_type] || {}).color, marginRight: 7 }} />
        {a.name} <span className="muted" style={{ fontWeight: 500 }}>{a.symbol || "未填代碼"}</span>
        {!a.symbol && <button className="btn btn-sm" style={{ marginLeft: 8, fontSize: 11 }} onClick={e => { e.stopPropagation(); askAsset(a, "quote"); }}>讓秘書補代碼</button>}
      </Td>
      <Td>{(DAM_TYPE_META[a.asset_type] || {}).label}</Td>
      <Td right>{damNum(a.quantity)}</Td>
      <Td right>{damCny(a.avg_cost_cny, 2)}</Td>
      <Td right>{quoteStatus(a)}</Td>
      <Td right tone={damTone(a.last_change_pct)} bold>{damPct(a.last_change_pct)}</Td>
      <Td right bold>{damCny(a.market_value_cny)}</Td>
      <Td right tone={damTone(a.unrealized_pnl_cny)} bold>
        {`${damCny(a.unrealized_pnl_cny)}${a.unrealized_pnl_pct != null ? `(${damPct(a.unrealized_pnl_pct)})` : ""}`}
      </Td>
      <Td right>
        <span className="da-actions" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-sm" title="AI 補行情" onClick={e => { e.stopPropagation(); askAsset(a, "quote"); }}>AI</button>
          <button className="btn btn-sm" title="登記買入" onClick={e => { e.stopPropagation(); askAsset(a, "buy"); }}>買</button>
          <button className="btn btn-sm" title="登記賣出" onClick={e => { e.stopPropagation(); askAsset(a, "sell"); }}>賣</button>
          <button className="btn btn-sm" title="登記分紅" onClick={e => { e.stopPropagation(); askAsset(a, "dividend"); }}>息</button>
        </span>
      </Td>
    </tr>
  );

  const watchCard = (a) => {
    const tone = (DAM_TYPE_META[a.asset_type] || {}).color || DAM_C.sub;
    const spark = sparks[a.id];
    const spark60 = spark && spark.length > 1 ? (spark[spark.length - 1] / spark[0] - 1) * 100 : null;
    return (
      <div key={a.id} className="da-watch-card" onClick={() => setDetail(a)}>
        <div className="da-watch-card-head">
          <div className="da-watch-name">
            <b><i className="da-type-dot" style={{ background: tone }}/>{a.name}</b>
            <em>{a.symbol || "未填代碼"} · {(DAM_TYPE_META[a.asset_type] || {}).label || a.asset_type}</em>
          </div>
          <span className="da-change-chip num" style={{ background: a.last_change_pct == null ? "rgba(110,110,115,.1)" : (a.last_change_pct >= 0 ? "rgba(255,59,48,.1)" : "rgba(52,199,89,.12)"), color: damTone(a.last_change_pct) }}>
            {damPct(a.last_change_pct)}
          </span>
        </div>
        <div className="da-watch-price">
          <strong className="num">{a.last_price != null ? damNum(a.last_price) : "—"}</strong>
          <span>{a.last_price != null ? (a.last_price_currency || "") : (a.symbol ? "待刷新" : "先補代碼")}</span>
          {spark60 != null && <em className="num" style={{ color: damTone(spark60) }}>60日 {damPct(spark60)}</em>}
        </div>
        <div className="da-watch-spark"><DamSpark closes={spark}/></div>
        <div className="da-watch-foot" onClick={e => e.stopPropagation()}>
          <em>{a.last_quote_at ? `更新 ${damQuoteTime(a.last_quote_at)}` : "未更新"}{a.watch_only ? " · 觀察倉" : ""}</em>
          <span className="da-watch-actions">
            {!a.symbol && <button className="btn btn-sm" onClick={() => askAsset(a, "quote")}>補代碼</button>}
            <button className="btn btn-sm" title="風險診斷+白話解讀" onClick={() => ask(`對「${a.name}」(id=${a.id})做風險診斷:asset risk --id ${a.id},解讀 VaR、波動結構、RSI/布林位置,講人話。`)}>AI 解讀</button>
            <button className="btn btn-primary btn-sm" onClick={() => askAsset(a, "buy")}>登記買入</button>
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="da-page">
      <div className="risk-topbar">
        <div>
          <div className="risk-title">資產管理</div>
          <div className="risk-sub">金融資產 + 數字資產市場 — 股票、基金、項目、軟件、模型和 AI Agent 分層管理</div>
        </div>
        <div className="row gap-8" style={{ flexWrap: "wrap", alignItems: "center" }}>
          {assetScope === "financial" ? (<>
            {lastUpdate && <span className="muted num" style={{ fontSize: 11.5 }}>更新 {lastUpdate.toLocaleTimeString("zh-CN", { hour12: false })}</span>}
            <button className="btn btn-sm" title="服務器每分鐘自動刷新行情;開啟後頁面每 30 秒同步顯示" onClick={() => setAutoOn(v => !v)}
              style={autoOn ? { background: DAM_C.green, color: "#fff", borderColor: DAM_C.green } : {}}>
              {autoOn ? "自動更新:開" : "自動更新:關"}
            </button>
            <button className="btn btn-sm" disabled={refreshing} onClick={refresh}>{refreshing ? "刷新中…" : "刷新行情"}</button>
            <button className="btn btn-sm" onClick={() => ask("請給我金融資產組合總覽:先 asset portfolio,再挑持倉和觀察倉中漲跌最大的資產說明情況。")}>問秘書</button>
            <button className="btn btn-primary btn-sm" onClick={() => setShowRegister(true)}>+ 登記金融資產</button>
          </>) : assetScope === "market" ? (<>
            <button className="btn btn-sm" onClick={() => askDigital("請用 dm listings 和 dm trades 給我市場簡報:在售結構、近期成交、值得關注的上架。")}>市場簡報</button>
            <button className="btn btn-primary btn-sm" onClick={() => askDigital("我想把一個資產上架到數字市場。請先 dm list 列出已登記資產讓我選,然後走權益設計 → dm compliance 合規預審 → dm listing create 上架。")}>上架資產</button>
          </>) : (<>
            <button className="btn btn-sm" onClick={() => askDigital("請掃描當前系統,列出最值得先資產化的項目、軟件、數據、流程、模型和 Agent。")}>識別資產</button>
            <button className="btn btn-primary btn-sm" onClick={() => askDigital("請把一個開發者項目設計成可交易的數字資產份額,包含權利、定價、分潤、限制轉讓和合規審查。")}>設計份額</button>
          </>)}
        </div>
      </div>

      <div className="da-scope-tabs" role="tablist" aria-label="數字資產分層">
        <button className={assetScope === "financial" ? "on" : ""} onClick={() => setAssetScope("financial")} role="tab" aria-selected={assetScope === "financial"}>
          <Icon name="chart" size={16}/>
          <span><b>金融資產</b><em>股票 / 基金 / 黃金 / 加密</em></span>
        </button>
        <button className={assetScope === "digital" ? "on" : ""} onClick={() => setAssetScope("digital")} role="tab" aria-selected={assetScope === "digital"}>
          <Icon name="layers" size={16}/>
          <span><b>數字資產</b><em>項目 / 軟件 / 數據 / Agent</em></span>
        </button>
        <button className={assetScope === "market" ? "on" : ""} onClick={() => setAssetScope("market")} role="tab" aria-selected={assetScope === "market"}>
          <Icon name="sparkle" size={16}/>
          <span><b>數字市場</b><em>在售櫥窗 / 行情 / 交易</em></span>
        </button>
      </div>

      {toast && <div style={{ fontSize: 12.5, color: DAM_C.blue }}>{toast}</div>}

      {assetScope === "digital" ? <DamDigitalAssetDesk ask={askDigital}/> : assetScope === "market" ? <DamMarketDesk ask={askDigital}/> : (<>
      <div className="da-grid">
        <div className="da-canvas">
          <div className="da-hero card">
            <div>
              <div className="risk-hero-eyebrow">AI 投資資產態勢</div>
              <div className="da-hero-word" style={{ color: health.tone }}>{health.word}</div>
              <div className="risk-hero-line">AI 秘書統一讀取資產台賬、公開行情、交易歷史和財務憑證,負責補代碼、解釋波動、追問買賣分紅字段並調用後端命令記賬。</div>
              <div className="da-hero-actions">
                <button className="btn btn-sm" onClick={() => ask("請補全缺失代碼和缺行情的資產,先列出需要我確認的候選,確認後調 asset set / asset refresh。")}><Icon name="sparkle" size={13}/>補代碼/行情</button>
                <button className="btn btn-sm" onClick={() => ask("我想新增一筆金融資產買入,請按資產名稱、類型、代碼、數量、成交價、手續費、支付賬戶和日期追問,然後登記並記賬。")}><Icon name="sparkle" size={13}/>口述買入</button>
              </div>
            </div>
            <div className="da-hero-score"><b className="num">{missingCode.length + missingQuote.length}</b><span>待 AI 補全</span></div>
          </div>

          <div className="da-signal-grid">
            {[
              ["待補代碼", missingCode.length, "讓秘書搜索候選並回寫代碼", DAM_C.orange, "scan"],
              ["缺行情", missingQuote.length, "需要刷新現價、匯率或漲跌幅", DAM_C.blue, "trend"],
              ["大波動", volatileAssets.length, "按股票/基金/黃金 3%,加密 8% 判定", DAM_C.red, "alert"],
              ["待記賬", 0, "買賣分紅由 asset 命令生成憑證", DAM_C.indigo, "chart"],
            ].map(([t, n, sub, tone, icon]) => (
              <button key={t} className="da-signal card" onClick={() => ask(`請處理「${t}」: ${sub}`)}>
                <span style={{ background: tone + "18", color: tone }}><Icon name={icon} size={17}/></span>
                <b>{t}</b><em>{sub}</em><strong className="num" style={{ color: tone }}>{n}</strong>
              </button>
            ))}
          </div>

          {/* 組合指標 */}
          <div className="da-metric-grid">
        {[
          ["總市值", damCny(portfolio.total_value_cny), DAM_C.ink, `持倉 ${portfolio.holdings ?? 0} 項 · 觀察 ${portfolio.watching ?? 0} 項`],
          ["總成本", damCny(portfolio.total_cost_cny), DAM_C.ink, null],
          ["浮動盈虧", damCny(pnl), damTone(pnl), portfolio.total_cost_cny ? damPct(pnl != null ? pnl / portfolio.total_cost_cny * 100 : null) : null],
          ["已實現+分紅", damCny((portfolio.realized_pnl_cny || 0) + (portfolio.dividends_cny || 0)), damTone(portfolio.realized_pnl_cny), `分紅 ${damCny(portfolio.dividends_cny)}`],
          ["今日波動", damCny(portfolio.day_change_cny), damTone(portfolio.day_change_cny), "按最新漲跌幅估算"],
        ].map(([k, v, tone, hint]) => (
          <div key={k} className="da-metric">
            <div className="da-metric-label">{k}</div>
            <div className="num da-metric-value" style={{ color: tone }}>{v}</div>
            {hint && <div className="da-metric-hint">{hint}</div>}
          </div>
        ))}
          </div>

          <DamScienceLab assets={assets} ask={ask}/>

      {/* 配置條 */}
      {!!(portfolio.allocation || []).length && (
        <div style={{ border: `1px solid ${DAM_C.hair}`, borderRadius: 10, background: "#fff", padding: 14 }} className="col gap-8">
          <div style={{ fontSize: 13, fontWeight: 800 }}>資產配置</div>
          <div className="row" style={{ height: 14, borderRadius: 7, overflow: "hidden", gap: 0 }}>
            {portfolio.allocation.map(s => (
              <div key={s.type} title={`${s.label} ${s.pct}%`} style={{ width: `${s.pct}%`, background: (DAM_TYPE_META[s.type] || {}).color, minWidth: 3 }} />
            ))}
          </div>
          <div className="row gap-10" style={{ flexWrap: "wrap", fontSize: 12 }}>
            {portfolio.allocation.map(s => (
              <span key={s.type} className="row gap-4" style={{ alignItems: "center" }}>
                <i style={{ width: 9, height: 9, borderRadius: 2, background: (DAM_TYPE_META[s.type] || {}).color, display: "inline-block" }} />
                {s.label} {s.pct}% <span className="muted">{damCny(s.value_cny)}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* 持倉表 */}
      <div style={{ border: `1px solid ${DAM_C.hair}`, borderRadius: 10, background: "#fff", padding: "4px 8px", overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead><tr>
            <Th>資產</Th><Th>類型</Th><Th right>數量</Th><Th right>成本均價</Th><Th right>現價(原幣)</Th><Th right>漲跌</Th><Th right>市值(CNY)</Th><Th right>浮動盈虧</Th><Th right>操作</Th>
          </tr></thead>
          <tbody>
            {loading && <tr><Td>載入中…</Td></tr>}
            {!loading && !holdings.length && <tr><td colSpan={9} style={{ padding: 18, fontSize: 13, color: DAM_C.sub }}>
              還沒有持倉。點「+ 登記金融資產」,或直接對 AI 秘書說:「我買了 100 股貴州茅台,花了 17 萬,幫我登記」。
            </td></tr>}
            {holdings.map(assetRow)}
          </tbody>
        </table>
      </div>

      {/* 觀察倉 */}
      {!!watching.length && (
        <div className="col gap-6">
          <div style={{ fontSize: 14, fontWeight: 900 }}>觀察倉 <span className="muted" style={{ fontSize: 12, fontWeight: 500 }}>只跟蹤行情,不參與記賬</span></div>
          <div className="da-watch-grid">{watching.map(watchCard)}</div>
        </div>
      )}

          <div className="muted" style={{ fontSize: 11 }}>行情來源於公開接口,可能有延遲;分析僅供參考,不構成投資建議。買賣分紅自動生成記賬憑證(借1101/貸1002 等),可在「AI 財務」查賬。</div>
        </div>

        <aside className="da-copilot card">
          <div className="risk-cop-head">
            <span className="row gap-8" style={{ alignItems: "center" }}><Icon name="sparkle" size={18} color="var(--blue)"/><b style={{ fontSize: 15 }}>公司 AI 秘書</b></span>
            <span className="badge badge-info" style={{ height: 22 }}>投資資產</span>
          </div>
          <div className="da-cop-body">
            <div className="da-ai-bubble">我會帶著本頁持倉、觀察倉、行情缺口和盈虧摘要工作。行情先查公開來源;買賣分紅追問必要字段後調 asset/fin 命令記賬;量化模型跑完用人話解讀。這不是投資建議。</div>
            {[
              ["行情與代碼", [
                ["補全代碼", "請補全所有缺失交易代碼,標出市場、幣種和資料來源,需要我確認候選時先停下來。"],
                ["刷新行情", "請刷新所有持倉和觀察倉行情,列出現價、漲跌幅、匯率和更新時間;失敗項給出原因。"],
              ]],
              ["交易記賬", [
                ["登記買入", "我買入了一項資產,請按字段追問並登記到金融資產台賬和財務憑證。"],
                ["登記賣出", "我賣出了一項資產,請計算已實現盈虧並生成收款/投資收益記賬。"],
                ["登記分紅", "我收到分紅/派息,請追問金額、稅費、到賬賬戶並記賬。"],
              ]],
              ["量化分析", [
                ["風險診斷", "對波動最大的資產跑 asset risk,解讀 VaR/CVaR、EWMA/GARCH 波動結構、Hurst 和 RSI/布林位置,講人話並給出觀察建議。"],
                ["衝擊韌性", "對主要資產跑 asset shock(MK50 衝擊增強市場模型):解讀 γ 衝擊加速係數、累積擬合路徑缺口和衝擊窗口復原天數,告訴我它抗不抗跌。"],
                ["市場狀態機", "跑 asset regime(MK59 ABM-FDP):現在什麼行情狀態、持續幾天了、對比歷史中位還能多久、哪些前兆特徵要盯。"],
                ["組合優化", "跑 asset portfolio-risk:解讀相關矩陣、風險貢獻和集中度,對比最小方差/風險平價/最大夏普三套權重,告訴我目前配置的問題。"],
                ["資產對比", "用 asset compare 把倉內資產橫向對比(收益/波動/回撤/夏普/相關),告訴我哪個性價比最高。"],
                ["計量建模", "對主要持倉運行 asset quant,解讀差分、線性回歸、CAPM 和 SARIMAX/ARX 預測,說明模型的局限。"],
                ["Panel 分析", "請對倉內多個金融資產運行 asset panel,用面板數據分析資產固定效應、共同市場因子和年化風險收益。"],
              ]],
            ].map(([group, items]) => (
              <div key={group} className="da-cop-group">
                <div className="da-cop-group-title">{group}</div>
                <div className="da-cop-group-chips">
                  {items.map(([label, prompt]) => <button key={label} className="risk-cop-chip" onClick={() => ask(prompt)}><Icon name="sparkle" size={12}/>{label}</button>)}
                </div>
              </div>
            ))}
            <div className="da-command-stack">
              <div className="legal-command-title">秘書會調用</div>
              {["asset portfolio", "asset risk", "asset shock", "asset regime", "asset portfolio-risk", "asset compare", "asset quant", "asset panel", "asset runs", "asset buy/sell/dividend"].map((cmd) => <code key={cmd}>{cmd}</code>)}
            </div>
          </div>
        </aside>
      </div>

      {showRegister && <DamRegister onClose={() => setShowRegister(false)} onDone={(r) => { setShowRegister(false); setToast(r.hint || "已登記"); load(); }} />}
      {detail && <DamDetail asset={detail} onClose={() => setDetail(null)} onChanged={load} />}
      </>)}
    </div>
  );
};

window.PageAssets = PageAssets;
