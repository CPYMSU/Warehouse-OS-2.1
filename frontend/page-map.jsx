/* ============================================================
   7 · 倉庫地圖 / 庫位管理 — 空間化平面圖
   ============================================================ */
const { useState: useStateMap } = React;

// 平面佈局 (網格座標)
const LAYOUT = [
  { id: "A", x: 0, y: 0, w: 2, h: 2 },
  { id: "B", x: 2, y: 0, w: 1, h: 1 },
  { id: "G", x: 3, y: 0, w: 1, h: 1 },
  { id: "B2", ref: "B", x: 2, y: 1, w: 2, h: 1 },
  { id: "C", x: 0, y: 2, w: 2, h: 1 },
  { id: "D", x: 2, y: 2, w: 1, h: 1 },
  { id: "E", x: 3, y: 2, w: 1, h: 1 },
  { id: "F", x: 0, y: 3, w: 2, h: 1 },
  { id: "H", x: 2, y: 3, w: 2, h: 1 },
];

const PageMap = () => {
  const emptyZone = { id: "—", name: "—", color: "#6B7A90", cap: 0, racks: 0, alert: 0, items: 0 };
  const zones = window.ZONES && window.ZONES.length ? window.ZONES : [emptyZone];
  const [sel, setSel] = useStateMap(zones[6] || zones[0]); // G區
  const [lowOnly, setLowOnly] = useStateMap(false);
  const getZone = (id) => zones.find(z => z.id === id) || emptyZone;
  const lowCount = zones.filter(z => z.alert > 0).length;
  const warehouseName = ((window.WAREHOUSES || []).filter(Boolean)[0]) || "—";

  return (
    <div className="col gap-18">
      <PageHead title="倉庫地圖 / 庫位管理" sub={`${warehouseName} · 視覺化庫位 · ${zones.length} 個功能區`}
        actions={<>
          <button className="btn btn-sm"><Icon name="scan" size={15}/>掃碼定位</button>
          <button className="btn btn-sm" onClick={() => setLowOnly(v => !v)} style={lowOnly ? { background: "var(--danger-soft)", color: "var(--danger)" } : undefined}><Icon name="filter" size={15}/>{lowOnly ? `只看有預警庫位 (${lowCount})` : "篩選低庫存庫位"}</button>
        </>}/>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 360px", gap: 18, alignItems: "flex-start" }}>
        {/* 平面圖 */}
        <div className="card fade-up" style={{ padding: 24, background: "linear-gradient(135deg,#F7FAFE,#EEF3FA)" }}>
          <div className="row spread" style={{ marginBottom: 18 }}>
            <SecHead title="倉庫平面圖" sub="點擊區域查看庫位詳情"/>
            <div className="row gap-16" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "var(--ok)" }}/>正常</span>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "var(--warn)" }}/>有預警</span>
              <span className="row gap-6"><span style={{ width: 9, height: 9, borderRadius: 3, background: "var(--danger)" }}/>缺貨</span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gridTemplateRows: "repeat(4, 100px)", gap: 12,
            perspective: "1200px" }}>
            {LAYOUT.map((cell,i) => {
              const z = getZone(cell.ref || cell.id);
              const active = sel.id === z.id;
              const dimmed = lowOnly && !(z.alert > 0);
              return (
                <button key={i} onClick={() => setSel(z)} style={{
                  gridColumn: `${cell.x+1} / span ${cell.w}`, gridRow: `${cell.y+1} / span ${cell.h}`,
                  borderRadius: 14, padding: 14, textAlign: "left", position: "relative", overflow: "hidden",
                  border: active ? `2px solid ${z.color}` : "1px solid var(--line)",
                  background: active ? z.color+"18" : "rgba(255,255,255,0.85)",
                  boxShadow: active ? `0 12px 30px ${z.color}33` : "var(--sh-sm)",
                  transform: active ? "translateY(-3px)" : "none", transition: "all .2s",
                  opacity: dimmed ? 0.3 : 1, filter: dimmed ? "grayscale(0.7)" : "none",
                }}>
                  <div className="row spread" style={{ alignItems: "flex-start" }}>
                    <div style={{ width: 30, height: 30, borderRadius: 9, background: z.color+"22", color: z.color, display: "grid", placeItems: "center", fontWeight: 800, fontSize: 14 }}>{z.id}</div>
                    {z.alert > 0 && <span className="badge badge-danger" style={{ height: 19, fontSize: 10.5 }}>{z.alert}</span>}
                  </div>
                  <div style={{ fontSize: 12.5, fontWeight: 700, marginTop: 8, color: "var(--ink)" }}>{z.name}</div>
                  <div className="num muted" style={{ fontSize: 11, marginTop: 2 }}>{z.racks} 貨架 · {z.items} 種</div>
                  {/* 容量條 */}
                  <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 4, background: "#EEF2F7" }}>
                    <div style={{ height: "100%", width: z.cap+"%", background: z.cap>85?"var(--danger)":z.cap>70?"var(--warn)":z.color }}/>
                  </div>
                </button>
              );
            })}
          </div>
          <div className="row center gap-8" style={{ marginTop: 16, fontSize: 11.5, color: "var(--ink-4)" }}><Icon name="map2" size={14}/>入口 / 卸貨區</div>
        </div>

        {/* 區域詳情 */}
        <RackDetail zone={sel}/>
      </div>
    </div>
  );
};

const RackDetail = ({ zone }) => {
  const racks = Array.from({ length: zone.racks }, (_,i) => {
    const cap = 42 + ((i * 37 + zone.cap) % 56);
    const alert = i < zone.alert;
    return { no: `${zone.id}-${String(Math.floor(i/3)+1).padStart(2,"0")}-${String(i%3+1).padStart(2,"0")}`, cap, alert };
  });
  const zonePrefix = String(zone.id || "").toUpperCase();
  const sampleItems = Array.from(new Set((window.INVENTORY || [])
    .filter(item => zonePrefix && String(item.loc || "").toUpperCase().startsWith(zonePrefix))
    .map(item => item.name)
    .filter(Boolean))).slice(0, 8);

  return (
    <div className="card fade-up" style={{ padding: 0, position: "sticky", top: 0, overflow: "hidden", animation: "fadeUp .3s ease both" }}>
      <div style={{ padding: 20, background: zone.color+"14", borderBottom: "1px solid var(--line)" }}>
        <div className="row gap-12">
          <div style={{ width: 44, height: 44, borderRadius: 13, background: zone.color, color: "#fff", display: "grid", placeItems: "center", fontWeight: 800, fontSize: 20 }}>{zone.id}</div>
          <div className="col gap-2"><div style={{ fontSize: 17, fontWeight: 700 }}>{zone.name}</div><div className="muted" style={{ fontSize: 12 }}>{zone.racks} 個貨架 · {zone.items} 種物資</div></div>
        </div>
        <div className="row gap-10" style={{ marginTop: 16 }}>
          <div className="col gap-2" style={{ flex: 1, padding: 12, borderRadius: 11, background: "rgba(255,255,255,0.7)" }}><span className="muted" style={{ fontSize: 11 }}>容量使用率</span><span className="num" style={{ fontSize: 20, fontWeight: 700, color: zone.cap>85?"var(--danger)":"var(--ink)" }}>{zone.cap}%</span></div>
          <div className="col gap-2" style={{ flex: 1, padding: 12, borderRadius: 11, background: "rgba(255,255,255,0.7)" }}><span className="muted" style={{ fontSize: 11 }}>預警庫位</span><span className="num" style={{ fontSize: 20, fontWeight: 700, color: zone.alert>0?"var(--danger)":"var(--ok)" }}>{zone.alert}</span></div>
        </div>
      </div>

      <div className="scroll-y" style={{ padding: 20, maxHeight: "calc(100vh - 320px)" }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>主要存放物資</div>
        <div className="row gap-8" style={{ flexWrap: "wrap", marginBottom: 20 }}>
          {sampleItems.length ? sampleItems.map(t => <span key={t} className="badge badge-gray">{t}</span>) : <span className="muted" style={{ fontSize: 12.5 }}>暫無真實庫位物資</span>}
        </div>

        <div className="eyebrow" style={{ marginBottom: 10 }}>貨架庫位 · {zone.racks} 個</div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 8 }}>
          {racks.map((r,i) => (
            <div key={i} className="row spread" style={{ padding: "10px 12px", borderRadius: 10, background: r.alert?"var(--danger-soft)":"var(--surface-2)", border: r.alert?"1px solid rgba(239,68,68,0.16)":"1px solid var(--line-soft)" }}>
              <div className="col gap-3">
                <span className="num" style={{ fontSize: 12, fontWeight: 700 }}>{r.no}</span>
                <div style={{ width: 50, height: 4, borderRadius: 2, background: "#E5EAF1", overflow: "hidden" }}><div style={{ height: "100%", width: r.cap+"%", background: r.cap>85?"var(--danger)":r.cap>70?"var(--warn)":"var(--ok)" }}/></div>
              </div>
              {r.alert ? <Icon name="alert" size={15} color="var(--danger)"/> : <span className="num muted" style={{ fontSize: 11 }}>{r.cap}%</span>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

window.PageMap = PageMap;
