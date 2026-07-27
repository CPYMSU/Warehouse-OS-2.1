/* ============================================================
   AIHistoryDrawer — 可复用的 AI 历史抽屉(标配于每个 AI 聊天端口)
   props: { open, channel, currentId, onClose, onSelect(id), onNew, title }
   自取 /api/ai/conversations?channel=...(搜索 + 时间分组 + 分页);position:absolute 覆盖最近的定位祖先。
   ============================================================ */
const AIH_CH = {
  assistant: { t: "秘書", c: "var(--blue)" }, agent: { t: "秘書", c: "var(--blue)" },
  alerts: { t: "預警", c: "#F59E0B" }, datahub: { t: "數據", c: "var(--teal)" }, procurement: { t: "招採", c: "#8B5CF6" },
};
const aihBase = () => (typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090");
const aihReq = (path) => (window.authFetch || fetch)(window.authFetch ? path : `${aihBase()}${path}`).then(r => r.ok ? r.json() : { rows: [] });
const aihDiff = (s) => { if (!s) return 9999; const d = new Date(String(s).replace(" ", "T") + "Z"); const n = (Date.now() - d.getTime()) / 86400000; return isNaN(n) ? 9999 : n; };
const aihBucket = (s) => { const n = aihDiff(s); return n < 1 ? "今天" : n < 7 ? "近 7 天" : n < 30 ? "近 30 天" : "更早"; };
const AIH_ORDER = ["今天", "近 7 天", "近 30 天", "更早"];

const AIHistoryDrawer = ({ open, channel, currentId, onClose, onSelect, onNew, title }) => {
  const { useState, useEffect } = React;
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [more, setMore] = useState(false);
  const ch = channel || "assistant";
  const load = (qq = "", offset = 0, append = false) =>
    aihReq(`/api/ai/conversations?limit=30&channel=${ch}&offset=${offset}` + (qq ? `&q=${encodeURIComponent(qq)}` : ""))
      .then(d => { const rows = d.rows || []; setItems(p => append ? [...p, ...rows] : rows); setMore(!!d.hasMore); }).catch(() => {});
  useEffect(() => { if (open) load(q.trim()); }, [open]);
  useEffect(() => { if (!open) return; const h = setTimeout(() => load(q.trim()), 280); return () => clearTimeout(h); }, [q]);
  if (!open) return null;
  const groups = q ? [["", items]] : AIH_ORDER.map(g => [g, items.filter(it => aihBucket(it.last_message_at) === g)]).filter(x => x[1].length);
  return (
    <div onClick={onClose} style={{ position: "absolute", inset: 0, zIndex: 20, background: "rgba(14,26,43,0.32)" }}>
      <div onClick={e => e.stopPropagation()} className="col gap-8"
        style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 290, maxWidth: "88%", background: "var(--surface)", borderRight: "1px solid var(--line)", boxShadow: "var(--sh-lg)", padding: 12 }}>
        <div className="row spread" style={{ padding: "2px 2px 4px", alignItems: "center" }}>
          <span className="eyebrow">{title || "歷史對話"}</span>
          <button className="btn btn-primary btn-sm" style={{ height: 24, padding: "0 10px" }} onClick={() => { onNew && onNew(); onClose && onClose(); }}><Icon name="plus" size={12}/>新建</button>
        </div>
        <div style={{ position: "relative" }}>
          <Icon name="search" size={14} color="var(--ink-4)" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }}/>
          <input className="input" value={q} onChange={e => setQ(e.target.value)} placeholder="搜索歷史(標題/內容)" style={{ height: 32, paddingLeft: 30, fontSize: 12.5 }}/>
        </div>
        <div className="col gap-8 scroll-y" style={{ flex: 1, paddingRight: 2 }}>
          {items.length === 0 && <span className="muted" style={{ fontSize: 12, padding: 8 }}>{q ? "沒有匹配的對話" : "暫無歷史對話"}</span>}
          {groups.map(([grp, list]) => (
            <div key={grp || "all"} className="col gap-6">
              {grp && <span className="eyebrow" style={{ fontSize: 10.5, paddingLeft: 2 }}>{grp}</span>}
              {list.map(it => {
                const c = AIH_CH[it.channel] || AIH_CH.assistant;
                return (
                  <button key={it.id} onClick={() => { onSelect && onSelect(it.id); onClose && onClose(); }} className="col gap-3"
                    style={{ alignItems: "flex-start", textAlign: "left", padding: 9, borderRadius: 10, border: `1px solid ${it.id === currentId ? "rgba(27,107,255,0.28)" : "var(--line)"}`, background: it.id === currentId ? "var(--blue-soft)" : "var(--surface)" }}>
                    <span className="row gap-6" style={{ alignItems: "center", width: "100%" }}>
                      <span style={{ width: 6, height: 6, borderRadius: 2, background: c.c, flex: "0 0 auto" }}/>
                      <span style={{ fontSize: 12.5, fontWeight: 800, color: it.id === currentId ? "var(--blue)" : "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{it.title}</span>
                    </span>
                    {it.snippet && <span className="muted" style={{ fontSize: 11, lineHeight: 1.4 }}>{it.snippet}</span>}
                    <span className="muted num" style={{ fontSize: 10.5 }}>{it.message_count || 0} 條 · {(it.last_message_at || "").slice(5, 16)}</span>
                  </button>
                );
              })}
            </div>
          ))}
          {more && !q && <button className="btn btn-sm" onClick={() => load("", items.length, true)}>載入更多</button>}
        </div>
      </div>
    </div>
  );
};
window.AIHistoryDrawer = AIHistoryDrawer;
