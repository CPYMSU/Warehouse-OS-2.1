/* ============================================================
   SVG 圖標庫 (Lucide 風格, 1.8 stroke)
   ============================================================ */
const Icon = ({ name, size = 18, color = "currentColor", sw = 1.8, style }) => {
  const P = { width: size, height: size, viewBox: "0 0 24 24", fill: "none",
    stroke: color, strokeWidth: sw, strokeLinecap: "round", strokeLinejoin: "round", style };
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/></>,
    box: <><path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/></>,
    inbound: <><path d="M12 3v10"/><path d="m8 9 4 4 4-4"/><path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2"/></>,
    outbound: <><path d="M12 13V3"/><path d="m8 7 4-4 4 4"/><path d="M4 17v2a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-2"/></>,
    alert: <><path d="m10.3 3.6-8 14A2 2 0 0 0 4 20.5h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></>,
    clipboard: <><rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/></>,
    map: <><path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2Z"/><path d="M9 4v14"/><path d="M15 6v14"/></>,
    cpu: <><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/><rect x="9" y="9" width="6" height="6" rx="1"/></>,
    shield: <><path d="M12 2 4 5v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V5l-8-3Z"/><circle cx="12" cy="10" r="2.2"/><path d="M8.5 17a3.5 3.5 0 0 1 7 0"/></>,
    chart: <><path d="M3 3v18h18"/><rect x="7" y="11" width="3" height="6" rx="1"/><rect x="12" y="7" width="3" height="10" rx="1"/><rect x="17" y="13" width="3" height="4" rx="1"/></>,
    gear: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-1.8-.3 1.6 1.6 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.6 1.6 0 0 0-1-1.5 1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0 .3-1.8 1.6 1.6 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.6 1.6 0 0 0 1.5-1 1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H9a1.6 1.6 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.6 1.6 0 0 0-1.5 1Z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></>,
    bell: <><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>,
    mic: <><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><path d="M12 19v3"/><path d="M8 22h8"/></>,
    zap: <><path d="M13 2 3 14h7l-1 8 10-12h-7l1-8Z"/></>,
    link: <><path d="M9 17H7A5 5 0 0 1 7 7h2"/><path d="M15 7h2a5 5 0 0 1 0 10h-2"/><path d="M8 12h8"/></>,
    activity: <><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    chevronDown: <path d="m6 9 6 6 6-6"/>,
    plus: <><path d="M12 5v14M5 12h14"/></>,
    scan: <><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M3 12h18"/></>,
    check: <path d="m5 12 5 5L20 7"/>,
    checkCircle: <><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></>,
    x: <><path d="M18 6 6 18M6 6l12 12"/></>,
    trend: <><path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/></>,
    swap: <><path d="m17 2 4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    pkg: <><path d="M16.5 9.4 7.5 4.2"/><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/></>,
    layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></>,
    filter: <path d="M3 4h18l-7 8v6l-4 2v-8L3 4Z"/>,
    map2: <><circle cx="12" cy="10" r="3"/><path d="M12 21s7-6.5 7-11a7 7 0 1 0-14 0c0 4.5 7 11 7 11Z"/></>,
    arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
    sparkle: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4Z"/></>,
    flame: <><path d="M12 2c1 4 5 5 5 9a5 5 0 0 1-10 0c0-1.5.5-2.5 1-3 0 1.5 1 2 2 2-1-2 0-5 2-8Z"/></>,
    dots: <><circle cx="5" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="19" cy="12" r="1.5"/></>,
    edit: <><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5Z"/></>,
    forward: <><path d="M15 14l5-5-5-5"/><path d="M20 9H9a5 5 0 0 0 0 10h1"/></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></>,
    eye: <><path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
    eyeOff: <><path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.2 4.2"/><path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a16.5 16.5 0 0 1-3.1 3.8"/><path d="M6.6 6.6A16 16 0 0 0 2 12s3.6 7 10 7a10.8 10.8 0 0 0 4.2-.8"/></>,
    logo: <><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/></>,
  };
  return <svg {...P}>{paths[name] || null}</svg>;
};

const PasswordInput = ({
  value,
  onChange,
  autoComplete,
  placeholder,
  className = "input",
  disabled = false,
  inputStyle = {},
  buttonStyle = {},
}) => {
  const [visible, setVisible] = React.useState(false);
  const label = visible ? "隱藏密碼" : "顯示密碼";
  return (
    <div style={{ position: "relative", width: "100%" }}>
      <input
        className={className}
        type={visible ? "text" : "password"}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        placeholder={placeholder}
        disabled={disabled}
        style={{ width: "100%", paddingRight: 44, ...inputStyle }}
      />
      <button
        type="button"
        aria-label={label}
        title={label}
        onMouseDown={(event) => event.preventDefault()}
        onClick={() => setVisible((next) => !next)}
        style={{
          position: "absolute",
          right: 6,
          top: "50%",
          transform: "translateY(-50%)",
          width: 32,
          height: 32,
          display: "grid",
          placeItems: "center",
          border: "none",
          borderRadius: 8,
          background: "transparent",
          color: "var(--ink-3)",
          cursor: "pointer",
          ...buttonStyle,
        }}
      >
        <Icon name={visible ? "eyeOff" : "eye"} size={17}/>
      </button>
    </div>
  );
};

/* —— 環形進度 —— */
const Ring = ({ value, size = 132, stroke = 12, color = "var(--blue)", track = "#EAF0F8", label, sub }) => {
  const v = Number.isFinite(value) ? value : 0;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - v / 100);
  const gid = "rg" + Math.round(value) + size;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <defs>
          <linearGradient id={gid} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#1B6BFF"/><stop offset="100%" stopColor="#07B6A2"/>
          </linearGradient>
        </defs>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={track} strokeWidth={stroke}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={`url(#${gid})`} strokeWidth={stroke}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.7,.3,1)" }}/>
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <div className="num" style={{ fontSize: size * 0.26, fontWeight: 700, color: "var(--ink)", lineHeight: 1 }}>{label ?? value + "%"}</div>
        {sub && <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 4 }}>{sub}</div>}
      </div>
    </div>
  );
};

/* —— 環形甜甜圈（多段）—— */
const Donut = ({ data, size = 132, stroke = 16 }) => {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const total = data.reduce((s, d) => s + d.value, 0);
  let acc = 0;
  return (
    <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#EEF2F7" strokeWidth={stroke}/>
      {data.map((d, i) => {
        const frac = total > 0 ? d.value / total : 0;
        const dash = c * frac;
        const el = (
          <circle key={i} cx={size/2} cy={size/2} r={r} fill="none" stroke={d.color} strokeWidth={stroke}
            strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={-acc}
            style={{ transition: "stroke-dasharray .8s ease" }}/>
        );
        acc += dash;
        return el;
      })}
    </svg>
  );
};

/* —— 迷你折線圖 —— */
const Spark = ({ points, w = 120, h = 36, color = "var(--blue)", fill = true }) => {
  const max = Math.max(...points), min = Math.min(...points);
  const rng = max - min || 1;
  const step = w / (points.length - 1);
  const pts = points.map((p, i) => [i * step, h - ((p - min) / rng) * (h - 6) - 3]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const gid = "sp" + Math.round(points[0]) + points.length;
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity="0.22"/><stop offset="100%" stopColor={color} stopOpacity="0"/>
      </linearGradient></defs>
      {fill && <path d={`${d} L ${w} ${h} L 0 ${h} Z`} fill={`url(#${gid})`}/>}
      <path d={d} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
};

/* —— 統計卡 —— */
const StatCard = ({ icon, label, value, unit, delta, deltaUp, accent = "var(--blue)", spark, sparkColor, danger, idx = 0 }) => (
  <div className="card fade-up" style={{ padding: 20, animationDelay: idx * 0.06 + "s", position: "relative", overflow: "hidden" }}>
    <div className="row spread" style={{ alignItems: "flex-start" }}>
      <div className="col gap-4">
        <div style={{ fontSize: 13, color: "var(--ink-3)", fontWeight: 500 }}>{label}</div>
        <div className="row" style={{ alignItems: "baseline", gap: 6, marginTop: 6 }}>
          <span className="num" style={{ fontSize: 32, fontWeight: 700, color: danger ? "var(--danger)" : "var(--ink)", lineHeight: 1 }}>{value}</span>
          {unit && <span style={{ fontSize: 13, color: "var(--ink-3)" }}>{unit}</span>}
        </div>
      </div>
      <div style={{ width: 42, height: 42, borderRadius: 12, display: "grid", placeItems: "center",
        background: danger ? "var(--danger-soft)" : "var(--grad-soft)", color: danger ? "var(--danger)" : accent }}>
        <Icon name={icon} size={20}/>
      </div>
    </div>
    <div className="row spread" style={{ marginTop: 14 }}>
      {delta != null ? (
        <span className="badge" style={{ color: deltaUp ? "var(--ok)" : "var(--danger)", background: deltaUp ? "var(--ok-soft)" : "var(--danger-soft)", height: 22 }}>
          <Icon name={deltaUp ? "trend" : "trend"} size={12} style={{ transform: deltaUp ? "none" : "scaleY(-1)" }}/>{delta}
        </span>
      ) : <span/>}
      {spark && <Spark points={spark} color={sparkColor || accent} w={88} h={30}/>}
    </div>
  </div>
);

/* —— 狀態徽章 —— */
const STATUS_MAP = {
  ok: ["badge-ok", "正常"], warn: ["badge-warn", "低庫存"],
  danger: ["badge-danger", "缺貨"], yellow: ["badge-yellow", "超期未檢"],
};
const StatusBadge = ({ s, text }) => {
  const [cls, label] = STATUS_MAP[s] || ["badge-gray", text || s];
  return <span className={"badge " + cls}><span className="dot"/>{text || label}</span>;
};

/* —— 區塊頭 —— */
const SecHead = ({ title, sub, right }) => (
  <div className="row spread" style={{ marginBottom: 16 }}>
    <div className="col gap-4">
      <div className="sec-title">{title}</div>
      {sub && <div style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{sub}</div>}
    </div>
    {right}
  </div>
);

/* —— 頁面標題 —— */
const PageHead = ({ title, sub, actions }) => (
  <div className="row spread fade-up" style={{ marginBottom: 22, flexWrap: "wrap", gap: 14 }}>
    <div className="col gap-6">
      <h1 style={{ fontSize: 24, fontWeight: 700, letterSpacing: "-0.02em" }}>{title}</h1>
      {sub && <div style={{ fontSize: 13.5, color: "var(--ink-3)" }}>{sub}</div>}
    </div>
    {actions && <div className="row gap-10">{actions}</div>}
  </div>
);

Object.assign(window, { Icon, Ring, Donut, Spark, StatCard, StatusBadge, SecHead, PageHead });
