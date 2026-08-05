/* ============================================================
   1 · 倉儲總覽 Dashboard
   ============================================================ */
const PageOverview = ({ go }) => {
  const inv = window.INVENTORY || [];
  const inbound = window.INBOUND || [];
  const outbound = window.OUTBOUND || [];
  const alerts = window.ALERTS || [];
  const zones = window.ZONES || [];
  const today = "2026-06-02";
  const inboundToday = inbound.filter(r => (r.time || "").startsWith(today)).length;
  const outboundToday = outbound.filter(r => (r.time || "").startsWith(today)).length;
  const redAlerts = alerts.filter(a => a.level === "red");
  const avgCap = zones.length ? Math.round(zones.reduce((s, z) => s + Number(z.cap || 0), 0) / zones.length) : 0;
  const highZones = zones.filter(z => Number(z.cap || 0) >= 85).map(z => `${z.id}區 ${z.cap}%`).join(" · ") || "—";
  const dangerZone = zones.find(z => z.name.includes("危險品"));
  const healthy = inv.filter(x => x.status === "ok").length;
  const lowStock = inv.filter(x => Number(x.stock || 0) < Number(x.safe || 0)).length;
  const dueSoon = inv.filter(x => x.checkDue && x.checkDue !== "—" && x.checkDue <= "2026-06-10").length;
  const health = [
    { label: "正常", value: healthy, color: "#10B981" },
    { label: "低庫存", value: lowStock, color: "#F59E0B" },
    { label: "超期未檢", value: dueSoon, color: "#EAB308" },
    { label: "待報廢", value: 0, color: "#EF4444" },
  ];
  const recent = [
    ...outbound.map(r => ({ item: r.qty || "—", dept: r.dept || "—", time: (r.time || "—").slice(11, 16) || "—", io: "out", urgent: !!r.urgent })),
    ...inbound.map(r => ({ item: r.qty || "—", dept: r.source || "—", time: (r.time || "—").slice(11, 16) || "—", io: "in" })),
  ].slice(0, 5);
  const quick = [
    { icon: "inbound", label: "入庫", color: "var(--blue)", go: "inbound" },
    { icon: "outbound", label: "出庫", color: "var(--teal)", go: "outbound" },
    { icon: "clipboard", label: "盤點", color: "var(--purple)", go: "stocktake" },
    { icon: "pkg", label: "申請領用", color: "#F59E0B", go: "outbound" },
  ];

  return (
    <div className="col gap-20">
      <PageHead title="倉儲總覽" sub="物資保障 · 實時運行監測中心"
        actions={<>
          <button className="btn btn-sm" onClick={() => go("stocktake")}><Icon name="clipboard" size={15}/>快速盤點</button>
          <button className="btn btn-primary btn-sm" onClick={() => go("ai")}><Icon name="sparkle" size={15}/>查看 AI 調度</button>
        </>}/>

      {/* 核心數據卡 */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 18 }}>
        <StatCard idx={0} icon="layers" label="庫存總量 (SKU)" value={inv.length || "—"} unit="種" delta={`倉庫 ${window.WAREHOUSES.length || "—"} 個`} deltaUp accent="var(--blue)" spark={[40,42,41,45,44,48,52]}/>
        <StatCard idx={1} icon="inbound" label="今日入庫" value={inboundToday || "—"} unit="批次" delta={`總入庫 ${inbound.length || "—"} 批`} deltaUp accent="var(--teal)" spark={[10,14,9,18,22,20,34]} sparkColor="var(--teal)"/>
        <StatCard idx={2} icon="outbound" label="今日出庫" value={outboundToday || "—"} unit="批次" delta={`搶修 ${outbound.filter(r=>r.urgent).length || "—"} 批`} deltaUp accent="#8B5CF6" spark={[20,18,24,16,22,26,28]} sparkColor="#8B5CF6"/>
        <StatCard idx={3} icon="alert" label="預警物資" value={alerts.length || "—"} unit="項" delta={`高風險 ${redAlerts.length || "—"} 項`} danger spark={[8,9,7,12,10,14,9]} sparkColor="#EF4444"/>
      </div>

      {/* 第二層 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.1fr 1.4fr", gap: 18 }}>
        {/* 容量使用率 */}
        <div className="card fade-up" style={{ padding: 22, animationDelay: ".1s" }}>
          <SecHead title="倉庫容量使用率" sub={`呼和浩特中心庫 · ${zones.length || "—"} 個區域`}/>
          <div className="row" style={{ gap: 26 }}>
            <Ring value={avgCap} size={148} stroke={14} sub="已使用容量"/>
            <div className="col gap-12" style={{ flex: 1 }}>
              {[["可用庫位", "—", "var(--ok)"], ["高負荷區域", highZones, "var(--warn)"], ["危險品區", dangerZone ? `${dangerZone.cap}% 安全範圍` : "—", "var(--info)"]].map(([k,v,c],i) => (
                <div key={i} className="row spread" style={{ paddingBottom: 12, borderBottom: i < 2 ? "1px solid var(--line-soft)" : "none" }}>
                  <span className="row gap-8" style={{ fontSize: 13, color: "var(--ink-3)" }}><span style={{ width: 7, height: 7, borderRadius: 2, background: c }}/>{k}</span>
                  <span className="num" style={{ fontSize: 13.5, fontWeight: 700, color: "var(--ink)" }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 物資健康狀態 */}
        <div className="card fade-up" style={{ padding: 22, animationDelay: ".16s" }}>
          <SecHead title="物資健康狀態" sub={`全庫 ${inv.length || "—"} 種物資狀態分佈`} right={<button className="btn btn-ghost btn-sm" onClick={() => go("alerts")} style={{ color: "var(--blue)" }}>查看預警<Icon name="chevron" size={14}/></button>}/>
          <div className="row" style={{ gap: 30 }}>
            <div style={{ position: "relative", flexShrink: 0 }}>
              <Donut data={health} size={148} stroke={18}/>
              <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
                <div><div className="num" style={{ fontSize: 26, fontWeight: 700 }}>{inv.length ? Math.round(healthy / inv.length * 100) : "—"}%</div><div style={{ fontSize: 11, color: "var(--ink-3)" }}>健康率</div></div>
              </div>
            </div>
            <div className="col gap-10" style={{ flex: 1 }}>
              {health.map((h,i) => (
                <div key={i} className="row spread">
                  <span className="row gap-8" style={{ fontSize: 13, color: "var(--ink-2)", fontWeight: 500 }}><span style={{ width: 9, height: 9, borderRadius: 3, background: h.color }}/>{h.label}</span>
                  <span className="num" style={{ fontSize: 14, fontWeight: 700 }}>{h.value.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 第三層 */}
      <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr", gap: 18 }}>
        {/* 最近出入庫 */}
        <div className="card fade-up" style={{ padding: 22, animationDelay: ".22s" }}>
          <SecHead title="最近出入庫記錄" right={<button className="btn btn-ghost btn-sm" style={{ color: "var(--ink-3)" }} onClick={() => go && go("logs")}>全部記錄</button>}/>
          <div className="col gap-2">
            {recent.map((r,i) => (
              <div key={i} className="row spread" style={{ padding: "11px 0", borderBottom: i < recent.length-1 ? "1px solid var(--line-soft)" : "none" }}>
                <div className="row gap-12">
                  <div style={{ width: 34, height: 34, borderRadius: 10, display: "grid", placeItems: "center", background: r.io === "in" ? "var(--teal-soft)" : "var(--blue-soft)", color: r.io === "in" ? "var(--teal)" : "var(--blue)" }}>
                    <Icon name={r.io === "in" ? "inbound" : "outbound"} size={17}/>
                  </div>
                  <div className="col gap-2">
                    <div className="row gap-8"><span style={{ fontSize: 13.5, fontWeight: 600 }}>{r.item}</span>{r.urgent && <span className="badge badge-danger" style={{ height: 19, fontSize: 10.5 }}>搶修</span>}</div>
                    <div style={{ fontSize: 12, color: "var(--ink-4)" }}>{r.dept}</div>
                  </div>
                </div>
                <span className="num" style={{ fontSize: 12.5, color: "var(--ink-4)" }}>{r.time}</span>
              </div>
            ))}
          </div>
        </div>

        {/* 重要預警 + 快捷 */}
        <div className="col gap-18">
          <div className="card fade-up" style={{ padding: 20, animationDelay: ".28s", borderColor: "rgba(239,68,68,0.2)" }}>
            <SecHead title="高風險預警" right={<span className="badge badge-danger">3 項緊急</span>}/>
            <div className="col gap-10">
              {redAlerts.map(a => (
                <button key={a.id} onClick={() => go("alerts")} className="row gap-10" style={{ width: "100%", textAlign: "left", padding: 12, borderRadius: 12, background: "var(--danger-soft)", border: "1px solid rgba(239,68,68,0.14)" }}>
                  <Icon name="flame" size={18} color="var(--danger)"/>
                  <div className="col gap-2" style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{a.item}</div>
                    <div style={{ fontSize: 11.5, color: "var(--danger)" }}>庫存 {a.stock}/{a.safe} · 可支撐搶修 {a.days} 天</div>
                  </div>
                  <Icon name="chevron" size={15} color="var(--danger)"/>
                </button>
              ))}
            </div>
          </div>

          <div className="card fade-up" style={{ padding: 20, animationDelay: ".34s" }}>
            <div className="sec-title" style={{ marginBottom: 14 }}>快捷操作</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {quick.map((q,i) => (
                <button key={i} onClick={() => go(q.go)} className="col center gap-8" style={{ padding: "16px 0", borderRadius: 14, border: "1px solid var(--line)", background: "var(--surface-2)", transition: "all .16s" }}
                  onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "var(--sh)"; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = "none"; e.currentTarget.style.boxShadow = "none"; }}>
                  <div style={{ width: 40, height: 40, borderRadius: 12, display: "grid", placeItems: "center", background: "var(--grad-soft)", color: q.color }}><Icon name={q.icon} size={20}/></div>
                  <span style={{ fontSize: 13, fontWeight: 600 }}>{q.label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
window.PageOverview = PageOverview;
