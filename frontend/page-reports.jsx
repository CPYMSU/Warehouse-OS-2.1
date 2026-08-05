/* ============================================================
   報表中心 — 出入庫走勢 · 消耗分析 · 庫存儲值（真實資料庫驅動）
   ============================================================ */
const { useState: useStateRpt, useEffect: useEffectRpt } = React;

const REPORTS_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

/* 將任意二維資料轉成 CSV 並觸發下載（帶 BOM 以兼容 Excel 中文） */
const downloadCSV = (filename, headers, rows) => {
  const esc = (v) => {
    const s = v == null ? "" : String(v);
    return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  };
  const lines = [headers.map(esc).join(",")].concat(rows.map((r) => r.map(esc).join(",")));
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const PageReports = () => {
  const [range, setRange] = useStateRpt("全週期");
  const [data, setData] = useStateRpt(null);
  const [state, setState] = useStateRpt("loading"); // loading | ok | error
  const ranges = ["近 30 天", "近 6 月", "全週期"];

  useEffectRpt(() => {
    let alive = true;
    (window.authFetch || fetch)(`${REPORTS_API_BASE}/api/reports/summary`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((d) => { if (alive) { setData(d); setState("ok"); } })
      .catch(() => { if (alive) setState("error"); });
    return () => { alive = false; };
  }, []);

  if (state === "loading") return <RptSkeleton/>;
  if (state === "error" || !data) return <RptError/>;

  const { kpis, value_dist, top_consume, trend, alert_stats, turnover, exportable } = data;
  const totalVal = value_dist.reduce((s, d) => s + d.value, 0) || 1;

  /* 導出：按報表類型組裝真實資料 */
  const exportReport = (item) => {
    if (item.endpoint === "value_dist") {
      downloadCSV("庫存儲值分佈.csv", ["分類", "儲值(萬元)", "佔比"], value_dist.map((d) => [d.label, d.value, (d.value / totalVal * 100).toFixed(1) + "%"]));
    } else if (item.endpoint === "top_consume") {
      downloadCSV("物資消耗排行.csv", ["排名", "物資", "消耗量"], top_consume.map((t, i) => [i + 1, t.name, t.value]));
    } else if (item.endpoint === "alerts") {
      const rows = (window.ALERTS || []).map((a) => [a.id, a.level, a.type, a.item, a.stock, a.safe, a.suggest]);
      downloadCSV("未關閉預警清單.csv", ["預警號", "等級", "類型", "物資", "庫存", "安全庫存", "建議"], rows);
    } else {
      const rows = [];
      (window.INBOUND || []).forEach((o) => (o.lines || []).forEach((l) => rows.push(["入庫", o.id, o.time, l.name, l.qty, l.unit])));
      (window.OUTBOUND || []).forEach((o) => (o.lines || []).forEach((l) => rows.push(["出庫", o.id, o.time, l.name, l.qty, l.unit])));
      downloadCSV("出入庫匯總表.csv", ["方向", "單號", "時間", "物資", "數量", "單位"], rows);
    }
  };

  return (
    <div className="col gap-18">
      <PageHead title="報表中心" sub="出入庫走勢 · 物資消耗分析 · 庫存儲值 · 搶修保障效率"
        actions={<>
          <div className="row gap-6" style={{ background: "var(--surface-2)", border: "1px solid var(--line)", borderRadius: 10, padding: 4 }}>
            {ranges.map(r => <button key={r} onClick={() => setRange(r)} className="btn btn-sm" style={{ height: 30, background: range === r ? "var(--surface)" : "transparent", border: "none", boxShadow: range === r ? "var(--sh-sm)" : "none", color: range === r ? "var(--ink)" : "var(--ink-3)" }}>{r}</button>)}
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => exportReport({ endpoint: "inbound,outbound" })}><Icon name="chart" size={15}/>導出匯總 CSV</button>
        </>}/>

      {/* KPI */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16 }}>
        {kpis.map((k, i) => (
          <div key={i} className="card fade-up" style={{ padding: 18, animationDelay: i * .05 + "s" }}>
            <div className="row spread" style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{k.key}</span>
              <div style={{ width: 34, height: 34, borderRadius: 10, background: "var(--grad-soft)", color: k.color, display: "grid", placeItems: "center" }}><Icon name={k.icon} size={17}/></div>
            </div>
            <div className="row" style={{ alignItems: "baseline", gap: 6 }}>
              <span className="num" style={{ fontSize: 26, fontWeight: 700 }}>{k.value}</span>
              {k.unit && <span className="muted" style={{ fontSize: 12 }}>{k.unit}</span>}
            </div>
            <span className="badge" style={{ marginTop: 10, color: "var(--ink-3)", background: "var(--surface-2)", height: 22 }}>{k.extra}</span>
          </div>
        ))}
      </div>

      {/* 出入庫走勢 + 儲值分佈 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 18 }}>
        <div className="card fade-up" style={{ padding: 22 }}>
          <SecHead title="出入庫走勢" sub={range + " · 單據量"} right={<div className="row gap-16" style={{ fontSize: 12, color: "var(--ink-3)" }}><span className="row gap-6"><span style={{ width: 10, height: 10, borderRadius: 3, background: "var(--blue)" }}/>入庫</span><span className="row gap-6"><span style={{ width: 10, height: 10, borderRadius: 3, background: "var(--teal)" }}/>出庫</span></div>}/>
          <GroupBars labels={trend.labels} series={[{ data: trend.inbound, color: "#1B6BFF" }, { data: trend.outbound, color: "#07B6A2" }]}/>
        </div>

        <div className="card fade-up" style={{ padding: 22, animationDelay: ".06s" }}>
          <SecHead title="庫存儲值分佈" sub={`總儲值 ¥${totalVal.toFixed(1)} 萬`}/>
          {value_dist.length === 0 ? <EmptyHint text="暫無帶單價的庫存資料"/> : (
            <div className="row" style={{ gap: 24 }}>
              <div style={{ position: "relative", flexShrink: 0 }}>
                <Donut data={value_dist} size={140} stroke={18}/>
                <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
                  <div><div className="num" style={{ fontSize: 20, fontWeight: 700 }}>¥{totalVal.toFixed(0)}萬</div><div style={{ fontSize: 11, color: "var(--ink-3)" }}>總儲值</div></div>
                </div>
              </div>
              <div className="col gap-9" style={{ flex: 1 }}>
                {value_dist.map((d, i) => (
                  <div key={i} className="row spread" style={{ fontSize: 12.5 }}>
                    <span className="row gap-8" style={{ color: "var(--ink-2)", fontWeight: 500 }}><span style={{ width: 9, height: 9, borderRadius: 3, background: d.color }}/>{d.label}</span>
                    <span className="num" style={{ fontWeight: 700 }}>{(d.value / totalVal * 100).toFixed(0)}%</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 消耗 Top + 預警統計 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 18 }}>
        <div className="card fade-up" style={{ padding: 22 }}>
          <SecHead title="物資消耗 Top 5" sub="出庫 / 領用數量排行"/>
          {top_consume.length === 0 ? <EmptyHint text="暫無出庫消耗資料"/> : (
            <div className="col gap-14">
              {top_consume.map((t, i) => (
                <div key={i} className="col gap-6">
                  <div className="row spread" style={{ fontSize: 13 }}>
                    <span className="row gap-8" style={{ fontWeight: 600 }}><span className="num muted" style={{ width: 16 }}>{i + 1}</span>{t.name}</span>
                    <span className="num" style={{ fontWeight: 700 }}>{t.value}</span>
                  </div>
                  <div style={{ height: 9, borderRadius: 5, background: "#EEF2F7", overflow: "hidden" }}>
                    <div style={{ height: "100%", width: (t.value / (t.max || 1) * 100) + "%", borderRadius: 5, background: t.color, transition: "width .8s ease" }}/>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card fade-up" style={{ padding: 22, animationDelay: ".06s" }}>
          <SecHead title="預警處理統計" sub={range}/>
          <div className="row gap-12" style={{ marginBottom: 18 }}>
            <Ring value={alert_stats.rate} size={110} stroke={11} sub="處理率"/>
            <div className="col gap-10" style={{ flex: 1 }}>
              {[["累計預警", alert_stats.total, "var(--ink)"], ["已處理", alert_stats.handled, "var(--ok)"], ["待歸還", alert_stats.pending_returns, "var(--warn)"], ["庫存週轉率", turnover, "var(--blue)"]].map(([k, v, c], i) => (
                <div key={i} className="row spread" style={{ fontSize: 12.5 }}><span className="muted">{k}</span><span className="num" style={{ fontWeight: 700, color: c }}>{v}</span></div>
              ))}
            </div>
          </div>
          <div style={{ padding: 14, borderRadius: 12, background: "var(--teal-soft)" }}>
            <div className="row gap-8" style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}><Icon name="sparkle" size={16} color="var(--teal)" style={{ flexShrink: 0, marginTop: 1 }}/><span>本期累計預警 <b className="num">{alert_stats.total}</b> 項,待歸還工器具 <b className="num">{alert_stats.pending_returns}</b> 項,可在 AI 調度中樞一鍵自查。</span></div>
          </div>
        </div>
      </div>

      {/* 可導出報表清單（真實導出） */}
      <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
        <div className="row spread" style={{ padding: "18px 22px 14px" }}><span className="sec-title">可導出報表</span><span className="muted" style={{ fontSize: 12 }}>導出為 CSV(Excel 可直接打開)</span></div>
        <table className="tbl">
          <thead><tr><th>報表名稱</th><th>類型</th><th>週期</th><th></th></tr></thead>
          <tbody>
            {exportable.map((r, i) => (
              <tr key={i}>
                <td style={{ fontWeight: 600, color: "var(--ink)" }}><span className="row gap-10"><Icon name="chart" size={16} color="var(--blue)"/>{r.name}</span></td>
                <td><span className="badge badge-gray">{r.type}</span></td>
                <td className="muted">{r.cycle}</td>
                <td style={{ textAlign: "right" }}><button className="btn btn-sm" onClick={() => exportReport(r)}>導出</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const EmptyHint = ({ text }) => (
  <div className="col center" style={{ padding: 30, gap: 8, color: "var(--ink-4)" }}>
    <Icon name="layers" size={26} color="var(--ink-4)"/><span style={{ fontSize: 12.5 }}>{text}</span>
  </div>
);

const RptSkeleton = () => (
  <div className="col center" style={{ height: "50vh", gap: 14, color: "var(--ink-4)" }}>
    <div style={{ width: 48, height: 48, borderRadius: 14, background: "var(--grad-soft)", display: "grid", placeItems: "center" }}><Icon name="chart" size={24} color="var(--blue)"/></div>
    <span style={{ fontSize: 13.5 }}>正在從資料庫計算報表…</span>
  </div>
);

const RptError = () => (
  <div className="col center" style={{ height: "50vh", gap: 12, color: "var(--ink-4)" }}>
    <Icon name="alert" size={30} color="var(--danger)"/>
    <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-2)" }}>無法連接報表服務</span>
    <span style={{ fontSize: 12.5 }}>請確認 AI 服務已啟動：<b className="num">{REPORTS_API_BASE}</b></span>
  </div>
);

/* 分組柱狀圖 */
const GroupBars = ({ labels, series }) => {
  const max = Math.max(1, ...series.flatMap(s => s.data)) * 1.15;
  const H = 200;
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 0, height: H, marginTop: 10 }}>
      {labels.map((lb, i) => (
        <div key={i} className="col" style={{ flex: 1, alignItems: "center", gap: 8, height: "100%", justifyContent: "flex-end" }}>
          <div className="row" style={{ gap: 5, alignItems: "flex-end", height: H - 24, width: "100%", justifyContent: "center" }}>
            {series.map((s, j) => (
              <div key={j} title={s.data[i]} style={{ width: 14, height: (s.data[i] / max * 100) + "%", borderRadius: "5px 5px 0 0", background: s.color, transition: "height .8s ease", animationDelay: i * .05 + "s", minHeight: 4 }}/>
            ))}
          </div>
          <span className="muted" style={{ fontSize: 11.5 }}>{lb}</span>
        </div>
      ))}
    </div>
  );
};

window.PageReports = PageReports;
