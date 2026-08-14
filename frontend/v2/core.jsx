/* ============================================================
   WAREHOUSE 2.1 · core — API / 圖標 / Swiss 組件庫 / 秘書塢
   ============================================================ */
(() => {
const W2 = {};
window.W2 = W2;

/* ── API 層 ── */
/* API and WebAuthn must share one origin. Local development is canonicalized
   to localhost by index.html; production naturally stays on its HTTPS host. */
W2.API_BASE = "";
W2.TOKEN_KEY = "warehouse_auth_token";
W2.TENANT_KEY = "warehouse_current_tenant";
W2.storageGet = (key) => {
  try { return localStorage.getItem(key) || ""; } catch (e) { return ""; }
};
W2.storageSet = (key, value) => {
  try {
    if (value) localStorage.setItem(key, value);
    else localStorage.removeItem(key);
    return true;
  } catch (e) { return false; }
};
W2.token = () => W2.storageGet(W2.TOKEN_KEY);
W2.setToken = (t) => W2.storageSet(W2.TOKEN_KEY, t);
W2.tenant = () => W2.storageGet(W2.TENANT_KEY);
W2.setTenant = (s) => W2.storageSet(W2.TENANT_KEY, s);
W2.hasUsableToken = () => {
  const token = W2.token();
  if (!token) return false;
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return false;
    const normalized = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
    const payload = JSON.parse(window.atob(padded));
    return Number.isFinite(Number(payload.exp)) && Number(payload.exp) > Date.now() / 1000 + 5;
  } catch (error) {
    return false;
  }
};

const transientGetStatuses = new Set([502, 503, 504]);
const abortError = () => {
  if (typeof DOMException === "function") return new DOMException("Request aborted", "AbortError");
  const error = new Error("Request aborted");
  error.name = "AbortError";
  return error;
};
const waitForRetry = (delay, signal) => new Promise((resolve, reject) => {
  if (signal && signal.aborted) { reject(abortError()); return; }
  const timer = window.setTimeout(done, delay);
  function done() {
    if (signal) signal.removeEventListener("abort", cancelled);
    resolve();
  }
  function cancelled() {
    window.clearTimeout(timer);
    if (signal) signal.removeEventListener("abort", cancelled);
    reject(abortError());
  }
  if (signal) signal.addEventListener("abort", cancelled, { once: true });
});
const isSameOriginGet = (path, options) => {
  const method = String((options && options.method) || "GET").toUpperCase();
  if (method !== "GET" || (options && options.body != null)) return false;
  try { return new URL(String(path), window.location.href).origin === window.location.origin; }
  catch (error) { return false; }
};
W2.fetch = async (path, options = {}) => {
  const requestOptions = { ...options };
  const suppressAuthExpired = !!requestOptions.suppressAuthExpired;
  const url = /^https?:/.test(path) ? path : W2.API_BASE + path;
  const retryTransientGet = requestOptions.retryTransientGet !== false && isSameOriginGet(url, requestOptions);
  const requestedRetries = Number(requestOptions.transientGetRetries);
  const transientGetRetries = Number.isFinite(requestedRetries)
    ? Math.max(0, Math.min(8, Math.trunc(requestedRetries))) : 2;
  delete requestOptions.suppressAuthExpired;
  delete requestOptions.retryTransientGet;
  delete requestOptions.transientGetRetries;
  const headers = new Headers(options.headers || {});
  const t = W2.token();
  if (t) headers.set("Authorization", "Bearer " + t);
  const slug = W2.tenant();
  if (slug) headers.set("X-Tenant-Slug", slug);
  let res;
  for (let attempt = 0; attempt <= transientGetRetries; attempt += 1) {
    try {
      res = await fetch(url, { ...requestOptions, headers });
    } catch (error) {
      if (!retryTransientGet || attempt >= transientGetRetries ||
          (error && error.name === "AbortError")) throw error;
      const base = Math.min(2400, 220 * Math.pow(2, attempt));
      const jitter = Math.floor(Math.random() * 120);
      await waitForRetry(base + jitter, requestOptions.signal);
      continue;
    }
    if (!retryTransientGet || !transientGetStatuses.has(res.status) ||
        attempt >= transientGetRetries) break;
    /* A short, bounded exponential delay smooths over a service restart.  It
       applies only to same-origin idempotent GETs; writes and WebAuthn
       ceremonies are never replayed. */
    const base = Math.min(2400, 220 * Math.pow(2, attempt));
    const jitter = Math.floor(Math.random() * 90);
    await waitForRetry(base + jitter, requestOptions.signal);
  }
  /* A failed WebAuthn assertion is also a 401, but does not invalidate the
     bearer session.  Security-sensitive callers can suppress only that
     global side effect and still receive the original error response. */
  if (res.status === 401 && !suppressAuthExpired) { W2.setToken(""); window.dispatchEvent(new Event("w2-auth-expired")); }
  return res;
};
W2.json = async (path, options) => {
  const res = await W2.fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const error = new Error(data.error || data.message || data.detail || res.statusText);
    error.status = res.status; error.data = data;
    throw error;
  }
  return data;
};
W2.post = (path, body, options = {}) => W2.json(path, {
  ...options,
  method: "POST",
  headers: { ...(options.headers || {}), "Content-Type": "application/json" },
  body: JSON.stringify(body || {}),
});

/* ── 預警提示音(Web Audio,無外部音檔)──
   - 只有 App 明確啟用後才建立/恢復 AudioContext。
   - 瀏覽器若要求先有用戶互動,下一次 pointer/keyboard 會自動解鎖。
   - 每批新預警只播放一次短促雙音,避免多條預警連續轟炸。 */
const AlertTone = (() => {
  let context = null;
  let enabled = false;
  let active = [];
  let pendingLevel = null;
  let resumePromise = null;

  const audioContext = () => {
    if (context) return context;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) return null;
    try { context = new Ctx(); } catch (e) { context = null; }
    return context;
  };

  const stop = () => {
    active.forEach(({ oscillator, gain }) => {
      try { oscillator.stop(); } catch (e) {}
      try { oscillator.disconnect(); } catch (e) {}
      try { gain.disconnect(); } catch (e) {}
    });
    active = [];
  };

  const unlock = () => {
    if (!enabled) return;
    const ac = audioContext();
    if (!ac) return;
    const flush = () => {
      if (context !== ac) return;
      resumePromise = null;
      if (!enabled || ac.state !== "running" || !pendingLevel) return;
      const level = pendingLevel;
      pendingLevel = null;
      play(level);
    };
    if (ac.state === "running") { flush(); return; }
    if (!resumePromise) resumePromise = ac.resume().then(flush).catch(() => { resumePromise = null; });
  };
  const gesture = () => unlock();

  const setEnabled = (next) => {
    enabled = !!next;
    document.removeEventListener("pointerdown", gesture);
    document.removeEventListener("keydown", gesture);
    if (!enabled) {
      pendingLevel = null;
      stop();
      resumePromise = null;
      const oldContext = context;
      context = null;
      if (oldContext && oldContext.state !== "closed") oldContext.close().catch(() => {});
      return;
    }
    document.addEventListener("pointerdown", gesture, { passive: true });
    document.addEventListener("keydown", gesture);
    /* 登入點擊等既有互動已發生時,瀏覽器通常允許直接恢復。 */
    if (navigator.userActivation && navigator.userActivation.hasBeenActive) unlock();
  };

  const play = (level = "blue") => {
    if (!enabled) return false;
    const ac = audioContext();
    if (!ac || ac.state !== "running") {
      const rank = { red: 0, orange: 1, yellow: 2, blue: 3 };
      if (!pendingLevel || (rank[level] ?? 9) < (rank[pendingLevel] ?? 9)) pendingLevel = level;
      unlock();
      return false;
    }
    pendingLevel = null;
    stop();
    const palette = {
      red: [[880, 0, .16], [659, .19, .24]],
      orange: [[659, 0, .15], [784, .18, .22]],
      yellow: [[523, 0, .14], [659, .17, .20]],
      blue: [[440, 0, .13], [587, .16, .19]],
    };
    const now = ac.currentTime + .012;
    (palette[level] || palette.blue).forEach(([frequency, offset, duration], index) => {
      const oscillator = ac.createOscillator();
      const gain = ac.createGain();
      const start = now + offset;
      const end = start + duration;
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, start);
      gain.gain.setValueAtTime(.0001, start);
      gain.gain.exponentialRampToValueAtTime(index ? .045 : .055, start + .018);
      gain.gain.exponentialRampToValueAtTime(.0001, end);
      oscillator.connect(gain);
      gain.connect(ac.destination);
      oscillator.start(start);
      oscillator.stop(end + .02);
      active.push({ oscillator, gain });
      oscillator.onended = () => {
        active = active.filter(node => node.oscillator !== oscillator);
        try { oscillator.disconnect(); gain.disconnect(); } catch (e) {}
      };
    });
    return true;
  };

  return { setEnabled, play, stop };
})();
W2.setAlertSoundEnabled = AlertTone.setEnabled;
W2.playAlertTone = AlertTone.play;
W2.stopAlertTone = AlertTone.stop;

W2.agentStream = async (body, onEvent, options = {}) => {
  const language = window.W2_LANG && window.W2_LANG.languageContract
    ? window.W2_LANG.languageContract() : { locale: "zh-Hant", language_mode: "auto" };
  const requestBody = {
    ...(body || {}),
    locale: (body && body.locale) || language.locale,
    language_mode: (body && body.language_mode) || language.language_mode,
  };
  const res = await W2.fetch("/api/agent/run/stream", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestBody), signal: options.signal,
  });
  if (!res.ok || !res.body) {
    let msg = res.statusText;
    let payload = null;
    try {
      payload = await res.json();
      msg = payload.error || payload.message || payload.detail || msg;
    } catch (e) {}
    const error = new Error(msg);
    error.status = Number(res.status) || undefined;
    error.data = payload && typeof payload === "object"
      ? payload : { status: error.status, error: msg };
    throw error;
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  let finalSeen = false;
  const acceptLine = line => {
    if (!line) return;
    let event;
    try { event = JSON.parse(line); } catch (e) { return; }
    if (event && event.event === "error") {
      const payload = event.payload && typeof event.payload === "object" ? event.payload : event;
      const error = new Error(event.error || event.message || payload.error || payload.message || "Agent stream failed");
      error.status = Number(event.status || payload.status) || undefined; error.data = payload;
      throw error;
    }
    if (event && event.event === "final") finalSeen = true;
    try { onEvent(event); } catch (e) {}
  };
  for (;;) {
    let chunk;
    try { chunk = await reader.read(); }
    catch (error) { if (finalSeen) break; throw error; }
    const { done, value } = chunk;
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, i).trim();
      buf = buf.slice(i + 1);
      acceptLine(line);
    }
  }
  acceptLine(buf.trim());
  if (!finalSeen) {
    const error = new Error("Agent stream ended before final event");
    error.data = { truncated: true, terminal: false };
    throw error;
  }
};

/* ── 圖標(1.6 描邊,幾何化) ── */
const P = {
  home: <><path d="M4 11.5 12 4l8 7.5"/><path d="M6 10v9.5h12V10"/></>,
  box: <><path d="M21 8 12 3 3 8v8l9 5 9-5V8Z"/><path d="m3 8 9 5 9-5"/><path d="M12 13v8"/></>,
  inbound: <><path d="M12 3v10"/><path d="m8 9 4 4 4-4"/><path d="M4 17v3h16v-3"/></>,
  outbound: <><path d="M12 13V3"/><path d="m8 7 4-4 4 4"/><path d="M4 17v3h16v-3"/></>,
  alert: <><path d="m10.3 3.6-8 14A2 2 0 0 0 4 20.5h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/></>,
  bell: <><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>,
  search: <><circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/></>,
  sparkle: <><path d="M12 3v4M12 17v4M3 12h4M17 12h4"/><path d="M12 8a4 4 0 0 0 4 4 4 4 0 0 0-4 4 4 4 0 0 0-4-4 4 4 0 0 0 4-4Z"/></>,
  chart: <><path d="M3 3v18h18"/><path d="M7 15v-4M12 15V7M17 15v-6"/></>,
  layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5"/><path d="m3 17 9 5 9-5"/></>,
  user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
  gear: <><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M2 12h3M19 12h3M4.9 19.1 7 17M17 7l2.1-2.1"/></>,
  x: <><path d="M18 6 6 18M6 6l12 12"/></>,
  trash: <><path d="M4 7h16M9 3h6l1 4H8l1-4ZM6 7l1 14h10l1-14"/><path d="M10 11v6M14 11v6"/></>,
  check: <path d="m5 12 5 5L20 7"/>,
  checkCircle: <><circle cx="12" cy="12" r="9"/><path d="m9 12 2 2 4-4"/></>,
  chevron: <path d="m9 18 6-6-6-6"/>,
  chevronDown: <path d="m6 9 6 6 6-6"/>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  flame: <><path d="M12 2c1 4 5 5 5 9a5 5 0 0 1-10 0c0-1.5.5-2.5 1-3 0 1.5 1 2 2 2-1-2 0-5 2-8Z"/></>,
  swap: <><path d="m17 2 4 4-4 4"/><path d="M3 11V9a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a4 4 0 0 1-4 4H3"/></>,
  clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
  map: <><circle cx="12" cy="10" r="3"/><path d="M12 21s7-6.5 7-11a7 7 0 1 0-14 0c0 4.5 7 11 7 11Z"/></>,
  shield: <><path d="M12 2 4 5v6c0 5 3.4 8.5 8 10 4.6-1.5 8-5 8-10V5l-8-3Z"/></>,
  clipboard: <><rect x="8" y="2" width="8" height="4"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><path d="m9 14 2 2 4-4"/></>,
  refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/><path d="M3 21v-5h5"/></>,
  eye: <><path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/></>,
  eyeOff: <><path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.2 4.2"/><path d="M9.9 5.2A10.8 10.8 0 0 1 12 5c6.4 0 10 7 10 7a16.5 16.5 0 0 1-3.1 3.8"/><path d="M6.6 6.6A16 16 0 0 0 2 12s3.6 7 10 7a10.8 10.8 0 0 0 4.2-.8"/></>,
  arrow: <><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></>,
  logo: <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z"/>,
  pkg: <><path d="M21 16V8a2 2 0 0 0-1-1.7l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.7l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5M12 22V12"/></>,
  scan: <><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M3 12h18"/></>,
  cpu: <><rect x="6" y="6" width="12" height="12"/><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3"/></>,
  doc: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6Z"/><path d="M14 2v6h6"/></>,
  wallet: <><path d="M20 7H5a2 2 0 0 1 0-4h13v4"/><path d="M4 5v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2"/><circle cx="16.5" cy="14" r="1.4"/></>,
  building: <><rect x="4" y="3" width="16" height="18"/><path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1"/></>,
  trend: <><path d="m22 7-8.5 8.5-5-5L2 17"/><path d="M16 7h6v6"/></>,
  gavel: <><path d="m14 13 6 6-1.5 1.5-6-6"/><path d="m9 8 5 5"/><path d="m7 6 4-4 4 4-4 4-4-4Z"/><path d="M3 21h9"/></>,
  mic: <><path d="M12 2a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v1a7 7 0 0 1-14 0v-1"/><path d="M12 18v4M8 22h8"/></>,
  camera: <><path d="M14.5 6 13 4H7L5.5 6H3v13h18V6h-6.5Z"/><circle cx="12" cy="12.5" r="4"/></>,
  image: <><rect x="3" y="4" width="18" height="16"/><circle cx="9" cy="9" r="2"/><path d="m3 17 5-5 4 4 3-3 6 6"/></>,
  table: <><rect x="3" y="4" width="18" height="16"/><path d="M3 10h18M3 15h18M10 4v16"/></>,
};
const Icon2 = ({ name, size = 17, sw = 1.6, color = "currentColor", style }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
    strokeWidth={sw} strokeLinecap="square" strokeLinejoin="miter" style={style}>{P[name] || null}</svg>
);
W2.Icon = Icon2;

/* ── UI 原子 ── */
const Btn = ({ kind = "", size = "", icon, children, ...rest }) => (
  <button className={`btn ${kind} ${size}`.trim()} {...rest}>{icon && <Icon2 name={icon} size={size === "sm" ? 12 : 14}/>}{children}</button>
);
const Tag = ({ tone = "plain", dot, children, style }) => (
  <span className={`tag ${tone}`} style={style}>{dot && <span className="dot"/>}{children}</span>
);
const Label = ({ red, dim, children, style }) => (
  <div className={"label" + (red ? " red" : "") + (dim ? " dim" : "")} style={style}>{children}</div>
);
const Empty = ({ icon = "box", title, sub, action }) => (
  <div className="col" style={{ alignItems: "center", gap: 12, padding: "48px 20px" }}>
    <Icon2 name={icon} size={26} color="var(--ink-4)"/>
    <div style={{ fontWeight: 700, fontSize: 14 }}>{title}</div>
    {sub && <div className="muted" style={{ fontSize: 12.5, maxWidth: 340, textAlign: "center", lineHeight: 1.6 }}>{sub}</div>}
    {action}
  </div>
);

/* ── 可擴充 Swiss 引導層 ──
   Guide 定義與顯示容器解耦：功能頁只發出帶上下文的 open 請求，App
   根節點唯一的 GuideHost 負責呈現。之後新增引導不需要再建立另一套
   modal、焦點或滾動鎖。 */
const guideDefinitions = new Map();
const guideSubscribers = new Set();
const guideMessageBacklog = [];
let guideRequestSequence = 0;
const publishGuideMessage = message => {
  if (guideSubscribers.size) {
    guideSubscribers.forEach(listener => {
      try { listener(message); } catch (error) {}
    });
  } else {
    guideMessageBacklog.push(message);
  }
};
const Guides = Object.freeze({
  register(id, component) {
    const key = String(id || "").trim();
    if (!key || typeof component !== "function") throw new Error("Guide registration requires an id and component");
    guideDefinitions.set(key, component);
    return () => { if (guideDefinitions.get(key) === component) guideDefinitions.delete(key); };
  },
  resolve(id) { return guideDefinitions.get(String(id || "").trim()) || null; },
  subscribe(listener) {
    if (typeof listener !== "function") throw new Error("Guide subscriber must be a function");
    guideSubscribers.add(listener);
    /* Preserve event order across boot.  An open emitted by a page before
       GuideHost mounts must not disappear; a following close is drained in
       the same FIFO message stream. */
    if (guideMessageBacklog.length) {
      const pending = guideMessageBacklog.splice(0, guideMessageBacklog.length);
      pending.forEach(message => {
        try { listener(message); } catch (error) {}
      });
    }
    return () => guideSubscribers.delete(listener);
  },
  open(id, payload = {}) {
    const key = String(id || "").trim();
    if (!key) throw new Error("Guide id is required");
    const requestId = ++guideRequestSequence;
    const detail = { id: key, requestId, payload: payload && typeof payload === "object" ? payload : {} };
    publishGuideMessage({ type: "open", detail });
    window.dispatchEvent(new CustomEvent("w2-guide-request", { detail }));
    return requestId;
  },
  close(reason = "dismissed") {
    publishGuideMessage({ type: "close", reason });
    window.dispatchEvent(new CustomEvent("w2-guide-close", { detail: { reason } }));
  },
});
W2.Guides = Guides;

const SwissGuideDialog = ({
  guideId = "guide", kicker = "GUIDED SETUP", title, description,
  steps = [], step = 0, busy = false, blocking = false,
  status = "", error = "", onClose, children, footer,
}) => {
  const layerRef = React.useRef(null);
  const titleId = `${guideId}-title`;
  const descriptionId = `${guideId}-description`;
  React.useEffect(() => {
    const previousFocus = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const background = Array.from(document.querySelectorAll(".mast,.main-scroll,.secretary-dock"));
    const snapshots = background.map(node => ({
      node, inert: node.hasAttribute("inert"), ariaHidden: node.getAttribute("aria-hidden"),
    }));
    background.forEach(node => { node.setAttribute("inert", ""); node.setAttribute("aria-hidden", "true"); });
    document.body.style.overflow = "hidden";
    const timer = window.setTimeout(() => {
      const layer = layerRef.current;
      if (!layer) return;
      const target = layer.querySelector("[data-guide-initial],button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled)");
      if (target && typeof target.focus === "function") target.focus();
    }, 0);
    return () => {
      window.clearTimeout(timer);
      document.body.style.overflow = previousOverflow;
      snapshots.forEach(({ node, inert, ariaHidden }) => {
        if (!inert) node.removeAttribute("inert");
        if (ariaHidden == null) node.removeAttribute("aria-hidden"); else node.setAttribute("aria-hidden", ariaHidden);
      });
      if (previousFocus && document.contains(previousFocus) && typeof previousFocus.focus === "function") previousFocus.focus();
    };
  }, []);

  const onKeyDown = event => {
    if (event.key === "Escape") {
      if (!busy && !blocking && onClose) { event.preventDefault(); onClose("escape"); }
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(layerRef.current.querySelectorAll(
      "button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex]:not([tabindex='-1'])"
    )).filter(node => !node.hasAttribute("hidden"));
    if (!focusable.length) { event.preventDefault(); return; }
    const first = focusable[0]; const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  };

  return (
    <div className="swiss-guide-layer" ref={layerRef} onKeyDown={onKeyDown}
      onMouseDown={event => {
        if (event.target === event.currentTarget && !busy && !blocking && onClose) onClose("backdrop");
      }}>
      <section className="swiss-guide-dialog" role="dialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined}>
        <header className="swiss-guide-header">
          <div className="col g8">
            <Label red>{kicker}</Label>
            <h2 id={titleId}>{title}</h2>
          </div>
          {onClose && <button type="button" className="swiss-guide-close" aria-label="Close"
            disabled={busy || blocking} onClick={() => onClose("close")}><Icon2 name="x" size={17}/></button>}
        </header>
        {description && <p id={descriptionId} className="swiss-guide-description">{description}</p>}
        {!!steps.length && <ol className="swiss-guide-progress" aria-label="Progress" style={{ "--guide-step-count": steps.length }}>
          {steps.map((label, index) => <li key={index} className={index === step ? "is-current" : index < step ? "is-done" : ""}
            aria-current={index === step ? "step" : undefined}>
            <span className="num">{String(index + 1).padStart(2, "0")}</span><b>{label}</b>
          </li>)}
        </ol>}
        <div className="swiss-guide-body">{children}</div>
        {(status || error) && <div className={`swiss-guide-status${error ? " is-error" : ""}`}
          role={error ? "alert" : "status"} aria-live={error ? "assertive" : "polite"}>{error || status}</div>}
        {footer && <footer className="swiss-guide-footer">{footer}</footer>}
      </section>
    </div>
  );
};

/* ── KPI 格:巨型數字 ── */
const Kpi = ({ label, value, unit, red, foot, delay = 0 }) => (
  <div className="kpi rise" style={{ animationDelay: delay + "s" }}>
    <div className="k-label"><Label>{label}</Label>{red && <span className="blink-dot"/>}</div>
    <div className={"k-value" + (red ? " red" : "")}>{value}{unit && <span className="k-unit">{unit}</span>}</div>
    <div className="k-foot">{foot || <span/>}</div>
  </div>
);

/* ── 量表 ── */
const Meter = ({ label, count, total, color = "var(--ink)" }) => (
  <div className="meter">
    <div className="row spread" style={{ fontSize: 12.5 }}>
      <span className="ink2">{label}</span>
      <span className="num" style={{ fontWeight: 700 }}>{count}<span className="muted" style={{ fontWeight: 400 }}> / {total}</span></span>
    </div>
    <div className="m-track"><i className="m-fill" style={{ width: (total ? count / total * 100 : 0) + "%", background: color }}/></div>
  </div>
);
const StackBar = ({ data = [] }) => {
  const total = data.reduce((s, d) => s + (Number(d.value) || 0), 0) || 1;
  return (
    <div className="stackbar">
      {data.map((d, i) => <i key={i} style={{ width: (d.value / total * 100) + "%", background: d.color }} title={d.label + " " + d.value}/>)}
    </div>
  );
};
W2.CHART_COLORS = [
  "var(--chart-1)", "var(--chart-2)", "var(--chart-3)",
  "var(--chart-4)", "var(--chart-5)", "var(--chart-6)",
];

const Spark2 = ({ points = [], w = 100, h = 30, color = "var(--ink)", fill = false }) => {
  if (!points || points.length < 2) return <svg width={w} height={h}/>;
  const max = Math.max(...points), min = Math.min(...points), rng = max - min || 1;
  const step = w / (points.length - 1);
  const pts = points.map((p, i) => [i * step, h - ((p - min) / rng) * (h - 6) - 3]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const last = pts[pts.length - 1];
  return (
    <svg width={w} height={h} style={{ display: "block" }}>
      <path d={d} fill="none" stroke={color} strokeWidth="1.5"/>
      <circle cx={last[0]} cy={last[1]} r="2.4" fill={color}/>
    </svg>
  );
};

/* ── 統計圖表原語(總覽/報表共用):鏡像柱狀 / 走勢面積 / 單位點陣 ──
   紀律:方角、髮絲網格、直標極值與端點、雙系列用實心/斜紋(不靠色相)、紅只給異常與現值 */
const useBoxW = (ref, fallback = 560) => {
  const [w, setW] = React.useState(fallback);
  React.useEffect(() => {
    const node = ref.current;
    if (!node || typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver((es) => {
      const cw = Math.round(es[0].contentRect.width);
      if (cw > 0) setW(cw);
    });
    ro.observe(node);
    return () => ro.disconnect();
  }, []);
  return w;
};
const niceStep = (max) => {
  const p = Math.pow(10, Math.floor(Math.log10(Math.max(1, max))));
  for (const k of [1, 2, 5]) if (max / (k * p) <= 4) return k * p;
  return 10 * p;
};

/* 鏡像柱狀:上=系列一(實心墨),下=系列二(45° 斜紋),同一比例尺
   emph = 下系列某月的強調索引(整柱標紅,紅=異常);note = 該月的註記文字;titleOf(i) = 自定義懸停文字 */
const MirrorBars = ({ labels = [], up = [], down = [], h = 250, upName = "", downName = "", unit = "", emph = -1, note = "", titleOf }) => {
  const ref = React.useRef(null);
  const w = useBoxW(ref);
  const n = labels.length;
  if (!n) return <div ref={ref}/>;
  const nums = (arr) => arr.map((v) => Number(v) || 0);
  const U = nums(up), D = nums(down);
  const maxU = Math.max(1, ...U), maxD = Math.max(1, ...D);
  const hasNote = emph >= 0 && emph < n && note;
  const noteH = hasNote ? 18 : 0;   // 註記佔一行,加在 svg 底部,不擠壓繪圖區
  const padL = 14 + String(Math.round(Math.max(maxU, maxD))).length * 5.6, padR = 8, padT = 18, padB = 32;
  const innerH = h - padT - padB;
  const scale = innerH / (maxU + maxD);
  const base = padT + maxU * scale;
  const slot = (w - padL - padR) / n;
  const bw = Math.max(6, Math.min(24, slot * .5));
  const step = niceStep(Math.max(maxU, maxD));
  const grid = [];
  for (let v = step; v <= maxU; v += step) grid.push([v, base - v * scale]);
  for (let v = step; v <= maxD; v += step) grid.push([v, base + v * scale]);
  const iMaxU = U.indexOf(Math.max(...U)), iMaxD = D.indexOf(Math.max(...D));
  return (
    <div ref={ref} className="w2chart">
      <svg width={w} height={h + noteH} style={{ display: "block" }}>
        <defs>
          <pattern id="w2hatch" width="5" height="5" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <rect width="1.6" height="5" fill="#141414"/>
          </pattern>
        </defs>
        {grid.map(([v, y], i) => (
          <g key={i}>
            <line x1={padL} x2={w - padR} y1={y} y2={y} stroke="rgba(20,20,20,.08)"/>
            <text x={padL - 6} y={y + 3} textAnchor="end" fontSize="9" fill="var(--ink-3)">{v}</text>
          </g>
        ))}
        {labels.map((lb, i) => {
          const cx = padL + slot * i + slot / 2;
          const vu = U[i], vd = D[i];
          const hu = vu * scale, hd = vd * scale;
          const isEmph = i === emph;
          return (
            <g key={i}>
              <title>{titleOf ? titleOf(i) : `${lb} · ${upName} ${vu}${unit} · ${downName} ${vd}${unit}`}</title>
              <rect x={cx - bw / 2} y={base - hu} width={bw} height={Math.max(hu, vu > 0 ? 1 : 0)} fill="var(--ink)"/>
              <rect x={cx - bw / 2} y={base + 2} width={bw} height={Math.max(hd, vd > 0 ? 1 : 0)} fill={isEmph ? "var(--red)" : "url(#w2hatch)"}/>
              {i === iMaxU && vu > 0 && <text x={cx} y={base - hu - 5} textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--ink)">{vu}</text>}
              {i === iMaxD && vd > 0 && <text x={cx} y={base + hd + 13} textAnchor="middle" fontSize="10" fontWeight="700" fill={isEmph ? "var(--red)" : "var(--ink)"}>{vd}</text>}
              <text x={cx} y={h - 8} textAnchor="middle" fontSize="9.5" fontWeight={isEmph ? "700" : "400"} fill={isEmph ? "var(--red)" : "var(--ink-3)"}>{lb}</text>
            </g>
          );
        })}
        <line x1={padL} x2={w - padR} y1={base} y2={base} stroke="var(--ink)" strokeWidth="2"/>
        {hasNote && (() => {
          // 註記錨定強調柱下方,左右自動收邊避免裁切
          const cx = padL + slot * emph + slot / 2;
          const anchor = cx > w * .66 ? "end" : cx < w * .34 ? "start" : "middle";
          return <text x={cx} y={h + 8} textAnchor={anchor} fontSize="9.5" fill="var(--red)">{note}</text>;
        })()}
      </svg>
    </div>
  );
};

/* 走勢面積:2px 折線 + 7% 淡染,端點紅點直標現值;onMonth = 點擊某月的回調 */
const TrendArea = ({ points = [], labels = [], h = 200, onMonth }) => {
  const ref = React.useRef(null);
  const w = useBoxW(ref);
  if (points.length < 2) return <div ref={ref}/>;
  const P = points.map((v) => Number(v) || 0);
  const lo0 = Math.min(...P), hi0 = Math.max(...P);
  const span = (hi0 - lo0) || Math.max(1, Math.abs(hi0) * .1 || 1);
  const lo = lo0 - span * .18, hi = hi0 + span * .18;
  const fmtN = (v) => Math.round(v).toLocaleString();
  // 邊距按實際標籤寬度推導(mono tabular-nums 每字寬度穩定),長數字不再被 SVG 邊緣裁掉
  const padL = 12 + fmtN(hi).length * 5.6, padR = 16 + fmtN(P[P.length - 1]).length * 6.5, padT = 14, padB = 24;
  const X = (i) => padL + (w - padL - padR) * i / (P.length - 1);
  const Y = (v) => padT + (h - padT - padB) * (1 - (v - lo) / (hi - lo));
  const step = niceStep(hi - lo);
  const ticks = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) ticks.push(v);
  const pts = P.map((v, i) => [X(i), Y(v)]);
  const d = pts.map((p, i) => (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1)).join(" ");
  const last = pts[pts.length - 1];
  const mid = Math.floor((labels.length - 1) / 2);
  return (
    <div ref={ref} className="w2chart">
      <svg width={w} height={h} style={{ display: "block" }}>
        {ticks.map((v, i) => (
          <g key={i}>
            <line x1={padL} x2={w - padR} y1={Y(v)} y2={Y(v)} stroke="rgba(20,20,20,.08)"/>
            <text x={padL - 6} y={Y(v) + 3} textAnchor="end" fontSize="9" fill="var(--ink-3)">{Math.round(v).toLocaleString()}</text>
          </g>
        ))}
        <path d={`${d} L${last[0].toFixed(1)} ${h - padB} L${pts[0][0].toFixed(1)} ${h - padB} Z`} fill="var(--ink)" opacity=".07"/>
        <path d={d} fill="none" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round"/>
        {P.map((v, i) => (
          <rect key={i} x={X(i) - slotHalf(w, padL, padR, P.length)} y="0" width={slotHalf(w, padL, padR, P.length) * 2} height={h} fill="transparent"
            onClick={onMonth ? () => onMonth(labels[i] || "", v) : undefined}
            style={onMonth ? { cursor: "pointer" } : undefined}>
            <title>{`${labels[i] || ""} · ${v.toLocaleString()}`}</title>
          </rect>
        ))}
        <circle cx={last[0]} cy={last[1]} r="6" fill="var(--paper)"/>
        <circle cx={last[0]} cy={last[1]} r="4" fill="var(--red)"/>
        <text x={last[0] + 9} y={last[1] + 3.5} fontSize="10.5" fontWeight="700" fill="var(--red)">{P[P.length - 1].toLocaleString()}</text>
        <text x={pts[0][0] - 2} y={pts[0][1] - 8} fontSize="9.5" fill="var(--ink-3)">{P[0].toLocaleString()}</text>
        {[0, mid, labels.length - 1].filter((x, i, a) => x >= 0 && a.indexOf(x) === i).map((i) => (
          <text key={i} x={X(i)} y={h - 8} textAnchor="middle" fontSize="9" fill="var(--ink-3)">{labels[i] || ""}</text>
        ))}
        <line x1={padL} x2={w - padR} y1={h - padB} y2={h - padB} stroke="var(--ink)" strokeWidth="2"/>
      </svg>
    </div>
  );
};
const slotHalf = (w, padL, padR, n) => (w - padL - padR) / Math.max(1, n - 1) / 2;

/* 單位點陣(Isotype 傳統):一格 = 一個真實個體 */
const UnitMatrix = ({ cells = [], cap = 720, onCell }) => {
  const shown = cells.slice(0, cap);
  return (
    <div>
      <div className="dotmx">
        {shown.map((c, i) => (
          <i key={i} title={c.title} style={{ background: c.color }} onClick={onCell ? () => onCell(c, i) : undefined}/>
        ))}
      </div>
      {cells.length > cap && <div className="muted num" style={{ fontSize: 10.5, marginTop: 6 }}>+{cells.length - cap}</div>}
    </div>
  );
};

/* ── 公司標識:上傳圖 / Swiss 字標 / 閃電兜底 ── */
/* 字素計數:emoji(ZWJ 組合/旗幟/變體符)佔多個碼位但視覺上是 1 字,字號按字素數定 */
W2.graphemes = (s) => {
  const str = String(s == null ? "" : s);
  try {
    return [...new Intl.Segmenter("zh", { granularity: "grapheme" }).segment(str)].map(x => x.segment);
  } catch (e) { return Array.from(str); }
};
const CompanyMark = ({ size = 34, branding }) => {
  const b = branding || {};
  if (b.type === "upload" && b.data_url) return (
    <img src={b.data_url} width={size} height={size} alt=""
      style={{ display: "block", objectFit: "cover", border: "1px solid var(--hair)", flexShrink: 0 }}/>
  );
  if (b.type === "mono" && b.letters) return (
    <span style={{ width: size, height: size, background: b.bg || "#141414", color: b.fg || "#F5F2EB",
      display: "grid", placeItems: "center", flexShrink: 0, fontFamily: "var(--f-mono)", fontWeight: 700,
      fontSize: Math.round(size * (W2.graphemes(b.letters).length > 1 ? .36 : .52)), letterSpacing: "-.02em",
      userSelect: "none", lineHeight: 1 }}>{b.letters}</span>
  );
  return <Icon2 name="logo" size={Math.round(size * .56)}/>;
};
W2.CompanyMark = CompanyMark;

/* ── 平台品牌:只用於登入、身份、安全與公共狀態；租戶工作區仍使用 CompanyMark ── */
W2.PLATFORM_NAME = "WAREHOUSE OS 2.1";
W2.PLATFORM_BRAND = "BONFIRE WORKSHOP";
W2.PLATFORM_MARK_URL = "brand/bonfire-platform-mark.png";
W2.PLATFORM_SEAL_URL = "brand/bonfire-platform-seal.png";
const PlatformMark = ({ size = 30, className = "", seal = false }) => (
  <img className={className} src={seal ? W2.PLATFORM_SEAL_URL : W2.PLATFORM_MARK_URL}
    width={size} height={size} alt="" aria-hidden="true"
    style={{ display: "block", objectFit: "contain", flexShrink: 0 }}/>
);
W2.PlatformMark = PlatformMark;

const setFavicon = (href) => {
  if (!href) return;
  let link = document.querySelector('link[rel="icon"]');
  if (!link) { link = document.createElement("link"); link.rel = "icon"; document.head.appendChild(link); }
  link.href = href;
};
W2.applyPlatformFavicon = () => {
  try {
    document.title = W2.PLATFORM_NAME;
    setFavicon(W2.PLATFORM_MARK_URL);
  } catch (e) {}
};

/* 動態 favicon:公司標隨租戶變 */
W2.applyBrandingFavicon = (branding) => {
  try {
    const b = branding || {};
    let href = null;
    if (b.type === "upload" && b.data_url) href = b.data_url;
    else if (b.type === "mono" && b.letters) {
      const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" fill="${b.bg || "#141414"}"/><text x="32" y="42" font-family="Space Grotesk,Menlo,monospace" font-size="${W2.graphemes(b.letters).length > 1 ? 26 : 34}" font-weight="700" text-anchor="middle" fill="${b.fg || "#F5F2EB"}">${String(b.letters).replace(/&/g, "&amp;").replace(/</g, "&lt;")}</text></svg>`;
      href = "data:image/svg+xml," + encodeURIComponent(svg);
    }
    document.title = W2.PLATFORM_NAME;
    if (!href) return;
    setFavicon(href);
  } catch (e) {}
};

/* ── Markdown 渲染(秘書回覆:加粗/表格/標題/代碼/鏈接/公式)── */
let _purifyHooked = false;
W2.mdToHtml = (text) => {
  const raw = String(text == null ? "" : text);
  if (!window.marked || !window.DOMPurify) return null;   // CDN 未就緒 → 調用方回退純文本
  // 先把數學段落藏起來,防止 marked 把公式裡的 _ * 當強調解析
  const stash = [];
  const s = raw.replace(/\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\]|\\\((.+?)\\\)|\$([^\n$]+?)\$/g, (m) => {
    stash.push(m);
    return "§§M" + (stash.length - 1) + "§§";
  });
  let html = window.marked.parse(s, { gfm: true, breaks: true });
  html = html.replace(/§§M(\d+)§§/g, (_, i) =>
    stash[+i].replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"));
  if (!_purifyHooked) {
    _purifyHooked = true;
    window.DOMPurify.addHook("afterSanitizeAttributes", (node) => {
      if (node.tagName === "A") { node.setAttribute("target", "_blank"); node.setAttribute("rel", "noopener"); }
    });
  }
  return window.DOMPurify.sanitize(html);
};

const MdBubble = ({ text }) => {
  const ref = React.useRef(null);
  const html = W2.mdToHtml(text);
  React.useEffect(() => {
    if (html != null && ref.current && window.renderMathInElement) {
      try {
        window.renderMathInElement(ref.current, {
          delimiters: [
            { left: "$$", right: "$$", display: true },
            { left: "\\[", right: "\\]", display: true },
            { left: "\\(", right: "\\)", display: false },
            { left: "$", right: "$", display: false },
          ],
          throwOnError: false,
        });
      } catch (e) {}
    }
  }, [text, html]);
  if (html == null) return <div className="bubble-a" style={{ whiteSpace: "pre-wrap" }}>{text}</div>;
  return <div className="bubble-a md" ref={ref} dangerouslySetInnerHTML={{ __html: html }}/>;
};

/* ── 秘書語音對話 Hook(移植自 1.0 agent-assistant.jsx useAgentVoice):
   雲端 /api/voice/*(真人感)→ 瀏覽器原生兜底;
   micClick 點說點停;mode 連續對話 = 回覆自動朗讀 + 朗讀完自動再聆聽 + barge-in 插話打斷 ── */
const useVoice = (onTranscript, onPartial) => {
  const [listening, setListening] = React.useState(false);
  const [finalizing, setFinalizing] = React.useState(false);
  const [mode, setMode] = React.useState(false);
  const [error, setError] = React.useState("");
  const st = React.useRef({ cloudAsr: false, cloudTts: false, recorder: null, recog: null,
    audio: null, audioUrl: "", bargeCleanup: null, stopTimer: null,
    lastVoice: false, mode: false, listenFn: null, listening_: false, finalizing_: false,
    gen: 0, partialBusy: false, speaking: false, restartWhenIdle: false });
  const markFinalizing = (on) => { st.current.finalizing_ = on; setFinalizing(on); };

  React.useEffect(() => {
    const actor = window.W2_USER || null;
    /* permissions is the server-computed effective set (including direct
       denies).  Do not use the owner-bypass navigation helper for a protected
       capability probe: the API still enforces an explicit ai.use grant. */
    const canUseAi = !!(actor && Array.isArray(actor.permissions)
      && actor.permissions.includes("ai.use"));
    if (canUseAi) {
      W2.json("/api/voice/status").then(d => {
        st.current.cloudAsr = !!(d.configured && d.asr && d.asr_ready !== false);
        st.current.cloudTts = !!(d.configured && d.tts
          && d.tts_ready !== false && d.connection_status !== "failed");
      }).catch(() => {});
    } else {
      st.current.cloudAsr = false;
      st.current.cloudTts = false;
    }
    if (window.speechSynthesis) speechSynthesis.getVoices();
  }, []);

  /* 朗讀前剝 Markdown/表格/emoji,截到 280 字內 */
  const trimSpeech = (text) => {
    let s = (text || "")
      .replace(/```[\s\S]*?```/g, "。代碼略過。")
      .replace(/`([^`]*)`/g, "$1")
      .replace(/!?\[([^\]]*)\]\([^)]*\)/g, "$1")
      .replace(/^\s{0,3}#{1,6}\s*/gm, "")
      .replace(/^\s*[-*+•·▪◦]\s+/gm, "")
      .replace(/^\s*\d+[.)、]\s+/gm, "")
      .replace(/^\s*>+\s*/gm, "")
      .replace(/^\s*[-=_*]{3,}\s*$/gm, "")
      .replace(/\|/g, " ")
      .replace(/\*\*|\*|__|_|~~/g, "")
      .replace(/(^|[^\w\d])[-–—]+(?=[^\w\d]|$)/g, "$1 ")
      .replace(/[#>`*_~|►▶▸◀◆◇■□●○★☆✓✔✗✘✦✧※→←↑↓➤➔◐]+/g, "")
      .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}\u{FE0F}]/gu, "")
      .replace(/[ \t]+/g, " ").replace(/\s*\n\s*\n\s*/g, "。").replace(/\s*\n\s*/g, " ").replace(/。(?:\s*。)+/g, "。")
      .trim();
    if (s.length > 280) {
      const cut = s.slice(0, 280);
      const pos = Math.max(cut.lastIndexOf("。"), cut.lastIndexOf("!"), cut.lastIndexOf("?"), cut.lastIndexOf("!"));
      s = pos > 80 ? cut.slice(0, pos + 1) : cut;
    }
    return s;
  };
  const zhVoice = () => {
    const vs = window.speechSynthesis ? speechSynthesis.getVoices() : [];
    return vs.find(v => /xiaoxiao|曉|晓/i.test(v.name) && /natural|online/i.test(v.name))
        || vs.find(v => /^zh/i.test(v.lang) && /natural|online/i.test(v.name))
        || vs.find(v => /^zh/i.test(v.lang)) || null;
  };
  const loopNext = () => {
    st.current.lastVoice = false;
    setTimeout(() => {
      if (st.current.mode && st.current.listenFn) st.current.listenFn();
    }, 350);
  };
  const resumeQueuedListen = () => {
    if (!st.current.mode || !st.current.restartWhenIdle
        || st.current.listening_ || st.current.finalizing_) return;
    st.current.restartWhenIdle = false;
    setTimeout(() => {
      if (st.current.mode && st.current.listenFn) st.current.listenFn();
    }, 0);
  };

  const releaseAudioUrl = () => {
    if (!st.current.audioUrl) return;
    try { URL.revokeObjectURL(st.current.audioUrl); } catch (e) {}
    st.current.audioUrl = "";
  };
  const playbackAudio = () => {
    if (!st.current.audio) {
      const audio = new Audio();
      audio.preload = "auto";
      audio.setAttribute("playsinline", "");
      audio.setAttribute("webkit-playsinline", "");
      st.current.audio = audio;
    }
    return st.current.audio;
  };
  /* iOS/Safari 只允許在用戶手勢內啟動媒體。用同一個 audio 元素播放極短靜音,
     之後雲端 TTS 回來時重用它,避免異步 audio.play() 被瀏覽器攔截。 */
  const unlockPlayback = () => {
    try {
      const audio = playbackAudio();
      releaseAudioUrl();
      audio.onended = null;
      audio.onerror = null;
      audio.onplaying = null;
      audio.src = "data:audio/wav;base64,UklGRsQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YaAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";
      const pending = audio.play();
      if (pending && typeof pending.then === "function") {
        pending.catch(() => {});
      }
    } catch (e) {}
  };
  const stopBargeIn = () => {
    const cleanup = st.current.bargeCleanup;
    st.current.bargeCleanup = null;
    if (cleanup) {
      try { cleanup(); } catch (e) {}
    }
  };
  /* Barge-in 只在音頻真正開始播放後啟動。先量 450ms 回聲/底噪,再判斷持續插話,
     避免 TTS 網絡等待期的環境聲把尚未返回的音頻直接丟棄。 */
  const armBargeIn = async (gen) => {
    if (!st.current.mode || !navigator.mediaDevices) return;
    stopBargeIn();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const an = ac.createAnalyser();
      an.fftSize = 256;
      ac.createMediaStreamSource(stream).connect(an);
      const buf = new Uint8Array(an.frequencyBinCount);
      let aboveMs = 0, last = Date.now(), noise = 0, samples = 0, closed = false;
      const calibrateUntil = Date.now() + 450;
      const cleanup = () => {
        if (closed) return;
        closed = true;
        stream.getTracks().forEach(tr => tr.stop());
        try { ac.close(); } catch (e) {}
        if (st.current.bargeCleanup === cleanup) st.current.bargeCleanup = null;
      };
      if (st.current.gen !== gen || !st.current.speaking) { cleanup(); return; }
      st.current.bargeCleanup = cleanup;
      const tick = () => {
        if (st.current.gen !== gen || !st.current.speaking) { cleanup(); return; }
        an.getByteFrequencyData(buf);
        let s = 0;
        for (let i = 0; i < buf.length; i++) s += buf[i];
        const now = Date.now();
        const avg = s / buf.length;
        if (now <= calibrateUntil) {
          samples += 1;
          noise += (avg - noise) / samples;
          last = now;
          requestAnimationFrame(tick);
          return;
        }
        const threshold = Math.max(18, noise * 1.8);
        if (avg > threshold) aboveMs += now - last;
        else aboveMs = Math.max(0, aboveMs - (now - last) * 2);
        last = now;
        if (aboveMs > 500) {
          cleanup();
          st.current.gen += 1;
          st.current.speaking = false;
          if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
          releaseAudioUrl();
          if (window.speechSynthesis) speechSynthesis.cancel();
          if (st.current.listenFn) st.current.listenFn();
          return;
        }
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    } catch (e) {}
  };

  const speakReply = async (text) => {
    if (!st.current.mode && !st.current.lastVoice) return;
    const clean = trimSpeech(text);
    if (!clean) { loopNext(); return; }
    const gen = ++st.current.gen;
    st.current.speaking = true;
    setError("");
    let fallbackStarted = false;
    const done = () => {
      if (st.current.gen === gen) {
        stopBargeIn();
        releaseAudioUrl();
        st.current.speaking = false;
        loopNext();
      }
    };
    const nativeFallback = () => {
      if (fallbackStarted || st.current.gen !== gen || !st.current.speaking) return;
      fallbackStarted = true;
      stopBargeIn();
      releaseAudioUrl();
      if (st.current.audio) {
        st.current.audio.onended = null;
        st.current.audio.onerror = null;
        st.current.audio.onplaying = null;
        try { st.current.audio.pause(); } catch (e) {}
      }
      if (!("speechSynthesis" in window)) {
        setError("語音播放失敗,請點擊「對話」重新啟用聲音或改用文字");
        done();
        return;
      }
      const u = new SpeechSynthesisUtterance(clean);
      const v = zhVoice();
      if (v) { u.voice = v; u.lang = v.lang; } else u.lang = "zh-TW";
      u.rate = 1.05;
      u.onstart = () => { setError(""); armBargeIn(gen); };
      u.onend = done;
      u.onerror = () => {
        setError("語音播放被瀏覽器阻止,請點擊「對話」重新啟用聲音");
        done();
      };
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    };
    try {
      if (st.current.cloudTts) {
        const res = await W2.fetch("/api/voice/speak", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: clean }),
        });
        if (res.ok) {
          if (st.current.gen !== gen || !st.current.speaking) return;   // 已被打斷
          const contentType = String(res.headers.get("Content-Type") || "").toLowerCase();
          const blob = await res.blob();
          if (st.current.gen !== gen || !st.current.speaking) return;
          if (!contentType.startsWith("audio/") || blob.size < 200) {
            nativeFallback();
            return;
          }
          releaseAudioUrl();
          const url = URL.createObjectURL(blob);
          st.current.audioUrl = url;
          const audio = playbackAudio();
          audio.onended = done;
          audio.onerror = nativeFallback;
          audio.src = url;
          audio.onplaying = () => { setError(""); armBargeIn(gen); };
          await audio.play();
          return;
        }
      }
    } catch (e) {
      nativeFallback();
      return;
    }
    if (st.current.gen !== gen || !st.current.speaking) return;
    nativeFallback();
  };
  const stop = () => {
    clearTimeout(st.current.stopTimer);
    if (st.current.recorder && st.current.recorder.state !== "inactive") { try { st.current.recorder.stop(); } catch (e) {} }
    if (st.current.recog) { try { st.current.recog.stop(); } catch (e) {} }
  };
  const listen = async () => {
    if (st.current.listening_ || st.current.finalizing_) {
      if (st.current.mode) st.current.restartWhenIdle = true;
      return;
    }
    st.current.restartWhenIdle = false;
    setError("");
    if (st.current.speaking) {
      st.current.gen += 1;
      st.current.speaking = false;
      if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
      releaseAudioUrl();
    }
    stopBargeIn();
    if (window.speechSynthesis) speechSynthesis.cancel();
    const mark = (on) => { st.current.listening_ = on; setListening(on); };
    const gen = ++st.current.gen;
    if (st.current.cloudAsr && navigator.mediaDevices && window.MediaRecorder) {
      let stream = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        if (st.current.gen !== gen) {
          stream.getTracks().forEach(track => track.stop());
          return;
        }
        const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : (MediaRecorder.isTypeSupported("audio/mp4") ? "audio/mp4" : "");
        const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
        const chunks = [];
        let lastPartialAt = 0;
        st.current.partialBusy = false;
        /* 流式體驗:1s 切片累積,每 ~2.2s 部分識別上屏;停止後完整定稿 */
        const transcribe = async (isFinal) => {
          if (st.current.gen !== gen) return;
          if (!isFinal && (st.current.partialBusy || !chunks.length)) return;
          const blob = new Blob(chunks, { type: mime || "audio/webm" });
          if (blob.size < 2500) { if (isFinal) loopNext(); return; }   // 太短(沒說話)→ 連續模式繼續聽
          st.current.partialBusy = true;
          try {
            const res = await W2.fetch("/api/voice/transcribe?lang=zh" + (isFinal ? "&correct=1" : ""), {
              method: "POST", headers: { "Content-Type": blob.type }, body: blob,
            });
            const d = await res.json().catch(() => ({}));
            if (st.current.gen !== gen) return;
            if (d.ok && d.text) {
              if (isFinal) { st.current.lastVoice = true; await Promise.resolve(onTranscript(d.text)); }
              else if (onPartial) onPartial(d.text + " …");
            } else if (isFinal) {
              st.current.cloudAsr = false;
              st.current.mode = false;
              st.current.lastVoice = false;
              setMode(false);
              setError(d.error || d.message || "雲端語音識別暫不可用,請再次點擊麥克風使用瀏覽器語音識別");
            }
          } catch (e) {
            if (isFinal && st.current.gen === gen) {
              st.current.cloudAsr = false;
              st.current.mode = false;
              st.current.lastVoice = false;
              setMode(false);
              setError("雲端語音識別連接失敗,請再次點擊麥克風使用瀏覽器語音識別");
            }
          }
          finally { st.current.partialBusy = false; }
        };
        rec.ondataavailable = (e) => {
          if (e.data && e.data.size) chunks.push(e.data);
          const now = Date.now();
          if (rec.state === "recording" && now - lastPartialAt > 2200) {
            lastPartialAt = now;
            transcribe(false);
          }
        };
        /* VAD 端點:說過話之後持續靜音 ~2.3s → 自動停止並發送(零點擊) */
        let vac = null, vraf = null;
        try {
          vac = new (window.AudioContext || window.webkitAudioContext)();
          const an = vac.createAnalyser();
          an.fftSize = 256;
          vac.createMediaStreamSource(stream).connect(an);
          const buf = new Uint8Array(an.frequencyBinCount);
          let noise = 6, frames = 0, spoke = false, silenceSince = 0;
          const startedAt = Date.now();
          const pump = () => {
            if (st.current.gen !== gen || !st.current.listening_) return;
            an.getByteFrequencyData(buf);
            let s = 0;
            for (let i = 0; i < buf.length; i++) s += buf[i];
            const avg = s / buf.length;
            if (avg < noise * 1.5) noise = noise * 0.97 + avg * 0.03;
            const now = Date.now();
            if (!spoke) {
              frames = avg > Math.max(noise * 2.2, 11) ? frames + 1 : 0;
              if (frames >= 4) { spoke = true; silenceSince = 0; }
              if (now - startedAt > 12000) { stop(); return; }
            } else if (avg < Math.max(noise * 1.5, 8)) {
              if (!silenceSince) silenceSince = now;
              else if (now - silenceSince > 2300) { stop(); return; }
            } else silenceSince = 0;
            vraf = requestAnimationFrame(pump);
          };
          vraf = requestAnimationFrame(pump);
        } catch (e) {}
        rec.onstop = () => {
          stream.getTracks().forEach(tr => tr.stop());
          if (vraf) cancelAnimationFrame(vraf);
          if (vac) { try { vac.close(); } catch (e) {} }
          clearTimeout(st.current.stopTimer);
          mark(false);
          if (st.current.gen !== gen) {
            markFinalizing(false);
            resumeQueuedListen();
            return;
          }
          markFinalizing(true);
          const waitIdle = () => st.current.partialBusy ? setTimeout(waitIdle, 120)
            : Promise.resolve(transcribe(true)).finally(() => {
              markFinalizing(false);
              resumeQueuedListen();
            });
          waitIdle();
        };
        st.current.recorder = rec;
        rec.start(1000);
        if (onPartial) onPartial("");
        mark(true);
        st.current.stopTimer = setTimeout(stop, 30000);
        return;
      } catch (e) {
        if (stream) stream.getTracks().forEach(track => track.stop());
        if (st.current.gen !== gen) return;
        const denied = e && (e.name === "NotAllowedError" || e.name === "PermissionDeniedError");
        setError(denied
          ? "麥克風權限被拒絕,請在瀏覽器網站設定中允許麥克風後重試"
          : "無法啟動麥克風,請檢查瀏覽器權限或改用文字輸入");
      }
    }
    if (st.current.gen !== gen) return;
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) {
      setError(current => current || "此瀏覽器暫不支援語音識別,請改用文字輸入或更新瀏覽器");
      return;
    }
    const r = new R();
    r.lang = "zh-CN";
    r.interimResults = true;
    let nativeFinal = "";
    let nativeFailed = false;
    r.onresult = (e) => {
      if (st.current.gen !== gen) return;
      let interim = "";
      for (let i = e.resultIndex || 0; i < e.results.length; i++) {
        const res = e.results[i];
        if (res.isFinal) nativeFinal += res[0].transcript;
        else interim += res[0].transcript;
      }
      if (interim && onPartial) onPartial(interim + " …");
    };
    r.onend = () => {
      mark(false);
      if (st.current.gen !== gen) {
        resumeQueuedListen();
        return;
      }
      const finalText = nativeFinal.trim();
      if (!nativeFailed && finalText) {
        st.current.lastVoice = true;
        markFinalizing(true);
        Promise.resolve(onTranscript(finalText)).finally(() => {
          markFinalizing(false);
          resumeQueuedListen();
        });
      }
    };
    r.onerror = (e) => {
      nativeFailed = true;
      mark(false);
      markFinalizing(false);
      if (st.current.gen !== gen) return;
      const denied = e && (e.error === "not-allowed" || e.error === "service-not-allowed");
      setError(denied
        ? "麥克風權限被拒絕,請在瀏覽器網站設定中允許麥克風後重試"
        : "語音識別失敗,請重試或改用文字輸入");
    };
    st.current.recog = r;
    try { r.start(); mark(true); }
    catch (e) { setError("無法啟動語音識別,請重試或改用文字輸入"); mark(false); }
  };
  st.current.listenFn = listen;
  const micClick = () => {
    if (st.current.listening_) stop();
    else {
      unlockPlayback();
      listen();
    }
  };
  const toggleMode = () => {
    const next = !st.current.mode;
    st.current.mode = next;
    setMode(next);
    if (next) {
      unlockPlayback();
      if (st.current.listening_ || st.current.finalizing_) {
        st.current.restartWhenIdle = true;
      } else {
        listen();
      }
    } else {
      st.current.gen++;
      st.current.speaking = false;
      st.current.lastVoice = false;
      st.current.restartWhenIdle = false;
      stopBargeIn();
      stop();
      releaseAudioUrl();
      if (window.speechSynthesis) speechSynthesis.cancel();
      if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
    }
  };
  /* 徹底熄火(關塢/卸載):gen++ 是關鍵——僅 stop() 仍會觸發 onstop→定稿→自動發送 */
  const shutdown = () => {
    st.current.mode = false;
    setMode(false);
    st.current.gen++;
    st.current.speaking = false;
    st.current.lastVoice = false;
    st.current.restartWhenIdle = false;
    markFinalizing(false);
    stopBargeIn();
    stop();
    releaseAudioUrl();
    if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
    if (window.speechSynthesis) speechSynthesis.cancel();
  };
  const shutdownRef = React.useRef(null);
  shutdownRef.current = shutdown;
  React.useEffect(() => () => { shutdownRef.current && shutdownRef.current(); }, []);
  return {
    listening, finalizing, mode, error,
    supported: !!(navigator.mediaDevices || window.SpeechRecognition || window.webkitSpeechRecognition),
    micClick, toggleMode, speakReply, shutdown,
  };
};

/* 盤點等業務頁可復用同一套雲端 ASR / 瀏覽器兜底,避免各頁另開麥克風實作。 */
W2.useVoice = useVoice;

const SECRETARY_CREDENTIAL_CLIENT_STORAGE_KEY = "w2.secretary.credential-client-id.v1";
let secretaryCredentialClientFallback = "";
const secretaryCredentialClientId = () => {
  const valid = value => /^[A-Za-z0-9_-]{20,128}$/.test(String(value || ""));
  try {
    const stored = window.sessionStorage.getItem(SECRETARY_CREDENTIAL_CLIENT_STORAGE_KEY);
    if (valid(stored)) return stored;
  } catch (error) {}
  if (!valid(secretaryCredentialClientFallback)) {
    const cryptoApi = window.crypto;
    if (cryptoApi && typeof cryptoApi.randomUUID === "function") {
      secretaryCredentialClientFallback = `w2cc_${cryptoApi.randomUUID()}`;
    } else if (cryptoApi && typeof cryptoApi.getRandomValues === "function") {
      const bytes = new Uint8Array(24);
      cryptoApi.getRandomValues(bytes);
      secretaryCredentialClientFallback = "w2cc_" + Array.from(bytes, value => value.toString(16).padStart(2, "0")).join("");
    } else {
      secretaryCredentialClientFallback = `w2cc_${Date.now()}_${Math.random().toString(36).slice(2)}_${Math.random().toString(36).slice(2)}`;
    }
  }
  try {
    window.sessionStorage.setItem(SECRETARY_CREDENTIAL_CLIENT_STORAGE_KEY, secretaryCredentialClientFallback);
  } catch (error) {}
  return secretaryCredentialClientFallback;
};
const secretaryCredentialDeliveryPath = (delivery, operation) => {
  if (!delivery || typeof delivery !== "object" || Array.isArray(delivery)) return "";
  const actionId = Number(delivery.action_id);
  const deliveryId = String(delivery.delivery_id || "").trim();
  if (!Number.isSafeInteger(actionId) || actionId <= 0
      || !/^acd_[A-Za-z0-9_-]{20,80}$/.test(deliveryId)
      || !["fetch", "ack"].includes(operation)) return "";
  const expected = `/api/agent/confirmation-actions/${actionId}/credential-delivery/${operation}`;
  const supplied = String(delivery[`${operation}_path`] || delivery[`${operation}_endpoint`] || expected).trim();
  return supplied === expected ? expected : "";
};
const secretaryCredentialDeliveryEnvelope = (delivery, actionKey = "") => {
  const fetchPath = secretaryCredentialDeliveryPath(delivery, "fetch");
  const ackPath = secretaryCredentialDeliveryPath(delivery, "ack");
  const expectedActionKey = `command:${Number(delivery && delivery.action_id)}`;
  if (!fetchPath || !ackPath || (actionKey && actionKey !== expectedActionKey)) return null;
  return { ...delivery, action_key: expectedActionKey, fetch_path: fetchPath, ack_path: ackPath };
};

const CredentialBubble = ({ credential, deliveryKey = "", credentialDelivery = null, onClear }) => {
  const t = window.W2_LANG.t;
  const [visible, setVisible] = React.useState(false);
  const [copied, setCopied] = React.useState(false);
  const [ackBusy, setAckBusy] = React.useState(false);
  const [ackError, setAckError] = React.useState("");
  if (!credential || !credential.value) return null;
  const delivery = secretaryCredentialDeliveryEnvelope(
    credentialDelivery,
    String(credential.action_key || (credentialDelivery && credentialDelivery.action_key) || ""),
  );
  const copy = async () => {
    try { await navigator.clipboard.writeText(credential.value); setCopied(true); setTimeout(() => setCopied(false), 1600); }
    catch (e) { setVisible(true); }
  };
  const acknowledge = async () => {
    if (ackBusy) return;
    setAckBusy(true); setAckError("");
    try {
      if (credentialDelivery && !delivery) {
        throw new Error(t("一次性憑證安全清除描述無效；卡片已保留，請重新核對"));
      }
      if (delivery) {
        const response = await W2.post(delivery.ack_path, {
          delivery_id: delivery.delivery_id,
          credential_client_id: secretaryCredentialClientId(),
        });
        if (!response || response.ok !== true || response.status !== "acked"
            || response.plaintext_destroyed !== true
            || String(response.delivery_id || "") !== String(delivery.delivery_id)) {
          throw new Error(t("服務端未確認一次性憑證已安全清除"));
        }
      }
      if (typeof onClear === "function") onClear(deliveryKey, delivery && delivery.delivery_id);
    } catch (error) {
      setAckError((error && error.message) || t("安全清除失敗；憑證仍保留在本頁，請稍後重試"));
    } finally { setAckBusy(false); }
  };
  return (
    <div data-credential-delivery={deliveryKey || undefined}
      style={{ alignSelf: "stretch", border: "1px solid var(--red)", padding: 11, background: "var(--surface)" }}>
      <div className="label" style={{ color: "var(--red)" }}>ONE-TIME CREDENTIAL</div>
      <div style={{ fontSize: 12.5, fontWeight: 800, marginTop: 4 }}>{credential.label || t("檔案 CLI 金鑰")}</div>
      <div className="mono" style={{ fontSize: 11, padding: "7px 8px", marginTop: 7, background: "var(--surface-2)", wordBreak: "break-all" }}>
        {visible ? credential.value : (credential.key_hint || "rck_••••••••••••")}
      </div>
      <div className="mono muted" style={{ fontSize: 9.5, marginTop: 5 }}>
        {credential.tenant_slug || "—"} · {(credential.scopes || []).join(",") || "—"} · {credential.expires_at || "—"}
      </div>
      <div className="row g6" style={{ marginTop: 7 }}>
        <button className="btn ghost sm" onClick={() => setVisible(v => !v)}>{visible ? t("隱藏") : t("揭示")}</button>
        <button className="btn sm" onClick={copy}>{copied ? t("已複製") : t("複製")}</button>
        <button className="btn primary sm" disabled={ackBusy} onClick={acknowledge}>
          {ackBusy ? t("安全清除中…") : t("已安全保存，清除")}
        </button>
      </div>
      {ackError && <div role="alert" style={{ color: "var(--danger)", fontSize: 10.5, lineHeight: 1.45, marginTop: 6 }}>{ackError}</div>}
      <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.5, marginTop: 6 }}>
        {credential.note || (delivery
          ? t("明文只在此頁籤短暫顯示；保存後請清除服務端加密副本。")
          : t("明文只顯示這一次，請立即保存。"))}
      </div>
    </div>
  );
};

const RECORD_ACTION_TERMINAL_STATUSES = new Set([
  "completed", "cancelled", "rejected", "failed", "expired", "outcome_unknown",
]);
const restoredRecordActionState = (confirmation, completedState = "confirmed") => {
  const payload = confirmation && confirmation.payload && typeof confirmation.payload === "object"
    ? confirmation.payload : {};
  const action = confirmation && confirmation.action && typeof confirmation.action === "object"
    ? confirmation.action : (payload.action && typeof payload.action === "object" ? payload.action : {});
  const status = String(action.status || payload.status || "").trim().toLowerCase();
  if (status === "pending") return "pending";
  if (status === "executing") return "executing";
  if (status === "completed") return completedState;
  if (status === "rejected" || status === "cancelled") return "rejected";
  if (status === "expired") return "expired";
  // Unknown snapshots are never actionable; only the canonical GET may move
  // an executing card to a terminal result.
  return "terminal";
};

const recordActionPollIdentity = () => `${W2.token()}\u0000${W2.tenant()}`;
const recordActionPollTerminalError = error => !!error && [403, 404, 410].includes(Number(error.status));
const recordActionCanonicalPath = (kind, actionId) => {
  const collection = kind === "record_config" ? "record-config-actions" : "record-actions";
  return `/api/agent/${collection}/${encodeURIComponent(actionId)}`;
};

const RecordCreateConfirmation = ({ confirmation }) => {
  const t = window.W2_LANG.t;
  const [state, setState] = React.useState(() => restoredRecordActionState(confirmation));
  const [error, setError] = React.useState("");
  const [created, setCreated] = React.useState(null);
  const busyRef = React.useRef(false);
  const pollGenerationRef = React.useRef(0);
  const terminalEventRef = React.useRef("");
  const payload = confirmation && confirmation.payload && typeof confirmation.payload === "object" ? confirmation.payload : {};
  const action = confirmation && confirmation.action && typeof confirmation.action === "object" ? confirmation.action : {};
  const actionId = String((confirmation && confirmation.id) || action.id || action.action_id || "");
  React.useEffect(() => {
    if (!busyRef.current) setState(restoredRecordActionState(confirmation));
  }, [action.status]);
  const proposal = [action.proposal, action.record, payload.proposal, payload.record, action.summary]
    .find(value => value && typeof value === "object" && !Array.isArray(value)) || {};
  const title = proposal.title || action.title || payload.title || t("未命名檔案");
  const summary = (typeof proposal.summary === "string" && proposal.summary)
    || (typeof proposal.description === "string" && proposal.description)
    || (typeof action.summary === "string" && action.summary) || "";
  const confirmationExpiresAt = action.expires_at || payload.expires_at || "";
  const fieldValues = proposal.fields && typeof proposal.fields === "object" && !Array.isArray(proposal.fields)
    ? proposal.fields : {};
  const actionFields = Array.isArray(action.fields) ? action.fields.filter(field => field && typeof field === "object") : [];
  const overviewFields = [
    [t("類型"), proposal.type_name || proposal.type_key || action.type_name || action.type_key || action.type],
    [t("分類"), proposal.category_name || proposal.category_key || action.category_name || action.category_key || action.category],
    [t("密級"), proposal.confidentiality || proposal.classification || action.confidentiality],
    [t("狀態"), proposal.status || proposal.initial_status || action.record_status],
  ].filter(([, value]) => value != null && value !== "");
  const text = value => {
    if (value == null || value === "") return "—";
    if (Array.isArray(value)) return value.map(text).join("、");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };
  React.useEffect(() => {
    if (!actionId || !["pending", "executing"].includes(state) || busyRef.current) return undefined;
    const generation = ++pollGenerationRef.current;
    const identity = recordActionPollIdentity();
    let stopped = false;
    let inFlight = false;
    let timer = null;
    let controller = null;
    const current = () => !stopped
      && generation === pollGenerationRef.current
      && identity === recordActionPollIdentity();
    const emitTerminal = (status, canonical) => {
      const key = `${actionId}:${status}`;
      if (terminalEventRef.current === key) return;
      terminalEventRef.current = key;
      if (status === "completed") {
        const record = canonical && canonical.record && typeof canonical.record === "object"
          ? canonical.record
          : { id: canonical && canonical.record_id, record_no: canonical && canonical.record_no };
        setCreated(record);
        emitRecordCreated(Number(record.id), record, actionId);
      } else {
        window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
          detail: { status, action_id: actionId },
        }));
      }
    };
    const schedule = () => {
      if (current() && !timer) timer = setTimeout(refresh, 5000);
    };
    const refresh = async () => {
      if (!current() || inFlight || busyRef.current) return;
      if (timer) { clearTimeout(timer); timer = null; }
      inFlight = true;
      controller = typeof AbortController === "function" ? new AbortController() : null;
      try {
        const response = await W2.json(
          recordActionCanonicalPath("record_create", actionId),
          { cache: "no-store", ...(controller ? { signal: controller.signal } : {}) },
        );
        if (!current()) return;
        const canonical = response && response.action;
        if (!canonical || canonical.kind !== "record_create" || String(canonical.id || "") !== actionId) {
          throw new Error(t("建檔提案權威狀態不匹配"));
        }
        const status = String(canonical.status || "").trim().toLowerCase();
        const nextState = restoredRecordActionState({ action: canonical });
        setError(canonical.error ? String(canonical.error) : "");
        setState(nextState);
        if (!["pending", "executing"].includes(status)) {
          stopped = true;
          emitTerminal(status || "outcome_unknown", canonical);
        }
      } catch (exception) {
        if (!current() || (exception && exception.name === "AbortError")) return;
        setError(exception.message || String(exception));
        if (recordActionPollTerminalError(exception)) {
          stopped = true;
          const status = Number(exception.status) === 410 ? "expired" : "permission_revoked";
          setState(Number(exception.status) === 410 ? "expired" : "terminal");
          emitTerminal(status, null);
        }
      } finally {
        inFlight = false;
        controller = null;
        schedule();
      }
    };
    const wake = () => {
      if (!document.hidden) refresh();
    };
    const invalidate = () => {
      stopped = true;
      ++pollGenerationRef.current;
      if (timer) clearTimeout(timer);
      if (controller) controller.abort();
    };
    const storageChanged = event => {
      if (event.key === W2.TOKEN_KEY || event.key === W2.TENANT_KEY) invalidate();
    };
    window.addEventListener("focus", wake);
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("warehouse-user-changed", invalidate);
    window.addEventListener("w2-auth-expired", invalidate);
    window.addEventListener("storage", storageChanged);
    refresh();
    return () => {
      invalidate();
      window.removeEventListener("focus", wake);
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("warehouse-user-changed", invalidate);
      window.removeEventListener("w2-auth-expired", invalidate);
      window.removeEventListener("storage", storageChanged);
    };
  }, [actionId, state]);
  const decide = async decision => {
    if (!actionId || busyRef.current || state !== "pending") return;
    busyRef.current = true; setState(decision === "confirm" ? "confirming" : "rejecting"); setError("");
    try {
      const endpoint = decision === "confirm"
        ? `/api/agent/record-actions/${encodeURIComponent(actionId)}/confirm`
        : `/api/agent/record-actions/${encodeURIComponent(actionId)}/reject`;
      const response = await W2.post(endpoint, {});
      if (!response || String(response.action_id || "") !== actionId) throw new Error(t("建檔提案回應不匹配"));
      if (decision === "reject") {
        if (response.status !== "rejected") throw new Error(t("拒絕提案未返回完成狀態"));
        setState("rejected");
        window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
          detail: { status: "rejected", action_id: actionId },
        }));
        return;
      }
      if (!response || response.event !== "record_created") throw new Error(t("建檔確認未返回完成事件"));
      const record = [response.record, response.record_summary, response.payload && response.payload.record, response.summary]
        .find(value => value && typeof value === "object" && !Array.isArray(value)) || {};
      const recordId = Number(record.id || record.record_id || response.record_id);
      if (!Number.isInteger(recordId) || recordId <= 0) throw new Error(t("建檔完成事件缺少有效檔案編號"));
      setCreated(record); setState("confirmed");
      emitRecordCreated(recordId, record, actionId);
    } catch (exception) {
      const terminal = exception.status === 410 || !!(exception.data && exception.data.terminal === true);
      setError(exception.message || String(exception));
      setState(terminal ? (exception.status === 410 ? "expired" : "terminal") : "pending");
      if (terminal) window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
        detail: { status: exception.status === 410 ? "expired" : "terminal", action_id: actionId },
      }));
    } finally { busyRef.current = false; }
  };
  return (
    <div style={{ alignSelf: "stretch", border: "1px solid var(--red)", padding: 12, background: "var(--white)" }}>
      <div className="label" style={{ color: "var(--red)" }}>RECORD CREATE · CONFIRMATION</div>
      <div style={{ fontSize: 14, fontWeight: 800, marginTop: 5 }}>{created ? (created.title || title) : title}</div>
      <div className="mono muted" style={{ fontSize: 9.5, marginTop: 5 }}>{actionId || "—"}</div>
      {!!overviewFields.length && <div style={{ display: "grid", gridTemplateColumns: "repeat(2,minmax(0,1fr))", gap: 7, marginTop: 9 }}>{overviewFields.map(([label, value]) => <div key={label} style={{ borderTop: "1px solid var(--hair)", paddingTop: 5 }}><div className="label dim">{label}</div><div style={{ fontSize: 11.5, marginTop: 2 }}>{text(value)}</div></div>)}</div>}
      {summary && <div style={{ fontSize: 11.5, lineHeight: 1.55, marginTop: 9, whiteSpace: "pre-wrap" }}>{summary}</div>}
      <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 6, marginTop: 9 }}><span className="label dim">{t("確認期限")}</span><span className="mono" style={{ float: "right", fontSize: 10.5 }}>{text(confirmationExpiresAt)}</span></div>
      {!!actionFields.length && <div style={{ marginTop: 8, maxHeight: 220, overflowY: "auto" }}>{actionFields.map((field, index) => <div key={field.key || field.label || index} className="row spread g8" style={{ fontSize: 10.5, padding: "3px 0" }}><span className="muted">{field.label || field.key || `#${index + 1}`}</span><span style={{ textAlign: "right", maxWidth: "62%", overflowWrap: "anywhere" }}>{text(field.value)}</span></div>)}</div>}
      {!!Object.keys(fieldValues).length && <div style={{ marginTop: 8, maxHeight: 220, overflowY: "auto" }}>{Object.entries(fieldValues).map(([key, value]) => <div key={key} className="row spread g8" style={{ fontSize: 10.5, padding: "3px 0" }}><span className="muted">{key}</span><span style={{ textAlign: "right", maxWidth: "62%", overflowWrap: "anywhere" }}>{text(value)}</span></div>)}</div>}
      {error && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.5, lineHeight: 1.45, marginTop: 8 }}>{error}</div>}
      {["pending", "confirming", "rejecting"].includes(state) && <div className="row g6" style={{ marginTop: 10 }}><button className="btn ghost sm" disabled={state !== "pending"} onClick={() => decide("reject")}>{t("拒絕")}</button><button className="btn primary sm" disabled={state !== "pending"} onClick={() => decide("confirm")}>{t("確認建立")}</button></div>}
      {(state === "confirming" || state === "rejecting") && <div className="step-line" style={{ marginTop: 9 }}><Icon2 name="refresh" size={10}/>{t(state === "confirming" ? "正在建立檔案…" : "正在拒絕…")}</div>}
      {state === "executing" && <div className="step-line" style={{ marginTop: 9 }}><Icon2 name="refresh" size={10}/>{t("正在核對建檔結果…")}</div>}
      {state === "confirmed" && <div style={{ color: "var(--ok)", fontSize: 11.5, fontWeight: 700, marginTop: 9 }}>{t("檔案已建立")}</div>}
      {state === "rejected" && <div className="muted" style={{ fontSize: 11.5, marginTop: 9 }}>{t("已拒絕，不會建立檔案")}</div>}
      {(state === "expired" || state === "terminal") && <div style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 700, marginTop: 9 }}>{t("提案已失效，請重新召喚秘書開始建檔")}</div>}
    </div>
  );
};

const emitRecordCreated = (recordId, record, actionId, status = "completed") => {
  const event = new CustomEvent("w2-record-created", {
    detail: { record_id: recordId, record, action_id: actionId },
  });
  event.detail.status = status;
  window.dispatchEvent(event);
};

const RecordConfigConfirmation = ({ confirmation }) => {
  const t = window.W2_LANG.t;
  const [state, setState] = React.useState(() => restoredRecordActionState(confirmation));
  const [error, setError] = React.useState("");
  const [committed, setCommitted] = React.useState(null);
  const busyRef = React.useRef(false);
  const pollGenerationRef = React.useRef(0);
  const terminalEventRef = React.useRef("");
  const payload = confirmation && confirmation.payload && typeof confirmation.payload === "object" ? confirmation.payload : {};
  const action = confirmation && confirmation.action && typeof confirmation.action === "object" ? confirmation.action : {};
  const actionId = String((confirmation && confirmation.id) || action.id || action.action_id || payload.action_id || "");
  React.useEffect(() => {
    if (!busyRef.current) setState(restoredRecordActionState(confirmation));
  }, [action.status]);
  const title = action.title || payload.title || t("提交檔案配置");
  const summary = (typeof action.summary === "string" && action.summary)
    || (typeof payload.summary === "string" && payload.summary) || "";
  const confirmationExpiresAt = action.expires_at || payload.expires_at || "";
  const actionFields = Array.isArray(action.fields) ? action.fields.filter(field => field && typeof field === "object") : [];
  const confirmEndpoint = typeof action.confirm_endpoint === "string" ? action.confirm_endpoint : "";
  const rejectEndpoint = typeof action.reject_endpoint === "string" ? action.reject_endpoint : "";
  const submittedField = actionFields.find(field => String(field.label || field.key || "") === "本次提交完整資料");
  const serverPayload = action.payload !== undefined ? action.payload
    : payload.payload !== undefined ? payload.payload
      : submittedField && submittedField.value !== undefined ? submittedField.value : {};
  const text = value => {
    if (value == null || value === "") return "—";
    if (Array.isArray(value)) return value.map(text).join("、");
    if (typeof value === "object") return JSON.stringify(value);
    return String(value);
  };
  const fullPayload = typeof serverPayload === "string" ? serverPayload : JSON.stringify(serverPayload, null, 2);
  const endpointFor = decision => decision === "confirm" ? confirmEndpoint : rejectEndpoint;
  React.useEffect(() => {
    if (!actionId || !["pending", "executing"].includes(state) || busyRef.current) return undefined;
    const generation = ++pollGenerationRef.current;
    const identity = recordActionPollIdentity();
    let stopped = false;
    let inFlight = false;
    let timer = null;
    let controller = null;
    const current = () => !stopped
      && generation === pollGenerationRef.current
      && identity === recordActionPollIdentity();
    const emitTerminal = (status, canonical) => {
      const key = `${actionId}:${status}`;
      if (terminalEventRef.current === key) return;
      terminalEventRef.current = key;
      if (status === "completed") {
        const config = canonical && canonical.config && typeof canonical.config === "object"
          ? canonical.config : {};
        setCommitted(config);
        emitRecordConfigCommitted(actionId, config, null, status);
      } else if (status === "rejected" || status === "cancelled") {
        emitRecordConfigRejected(actionId, "rejected");
      } else {
        window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
          detail: { status, action_id: actionId },
        }));
      }
    };
    const schedule = () => {
      if (current() && !timer) timer = setTimeout(refresh, 5000);
    };
    const refresh = async () => {
      if (!current() || inFlight || busyRef.current) return;
      if (timer) { clearTimeout(timer); timer = null; }
      inFlight = true;
      controller = typeof AbortController === "function" ? new AbortController() : null;
      try {
        const response = await W2.json(
          recordActionCanonicalPath("record_config", actionId),
          { cache: "no-store", ...(controller ? { signal: controller.signal } : {}) },
        );
        if (!current()) return;
        const canonical = response && response.action;
        if (!canonical || canonical.kind !== "record_config" || String(canonical.id || "") !== actionId) {
          throw new Error(t("檔案配置提案權威狀態不匹配"));
        }
        const status = String(canonical.status || "").trim().toLowerCase();
        const nextState = restoredRecordActionState({ action: canonical });
        setError(canonical.error ? String(canonical.error) : "");
        setState(nextState);
        if (!["pending", "executing"].includes(status)) {
          stopped = true;
          emitTerminal(status || "outcome_unknown", canonical);
        }
      } catch (exception) {
        if (!current() || (exception && exception.name === "AbortError")) return;
        setError(exception.message || String(exception));
        if (recordActionPollTerminalError(exception)) {
          stopped = true;
          const status = Number(exception.status) === 410 ? "expired" : "permission_revoked";
          setState(Number(exception.status) === 410 ? "expired" : "terminal");
          emitTerminal(status, null);
        }
      } finally {
        inFlight = false;
        controller = null;
        schedule();
      }
    };
    const wake = () => {
      if (!document.hidden) refresh();
    };
    const invalidate = () => {
      stopped = true;
      ++pollGenerationRef.current;
      if (timer) clearTimeout(timer);
      if (controller) controller.abort();
    };
    const storageChanged = event => {
      if (event.key === W2.TOKEN_KEY || event.key === W2.TENANT_KEY) invalidate();
    };
    window.addEventListener("focus", wake);
    document.addEventListener("visibilitychange", wake);
    window.addEventListener("warehouse-user-changed", invalidate);
    window.addEventListener("w2-auth-expired", invalidate);
    window.addEventListener("storage", storageChanged);
    refresh();
    return () => {
      invalidate();
      window.removeEventListener("focus", wake);
      document.removeEventListener("visibilitychange", wake);
      window.removeEventListener("warehouse-user-changed", invalidate);
      window.removeEventListener("w2-auth-expired", invalidate);
      window.removeEventListener("storage", storageChanged);
    };
  }, [actionId, state]);
  const decide = async decision => {
    if (!actionId || busyRef.current || state !== "pending") return;
    const endpoint = endpointFor(decision);
    if (!endpoint || !endpoint.startsWith("/api/agent/record-config-actions/")) {
      setError(t("檔案配置確認端點不正確"));
      return;
    }
    busyRef.current = true; setState(decision === "confirm" ? "confirming" : "rejecting"); setError("");
    try {
      const response = await W2.post(endpoint, {});
      if (!response || String(response.action_id || "") !== actionId) throw new Error(t("檔案配置提案回應不匹配"));
      if (decision === "reject") {
        if (response.event !== "record_config_rejected" && response.status !== "rejected") throw new Error(t("取消配置未返回完成事件"));
        setState("rejected");
        emitRecordConfigRejected(actionId, "rejected", response);
        return;
      }
      if (response.event !== "record_config_committed") throw new Error(t("配置確認未返回完成事件"));
      const config = response.config && typeof response.config === "object" ? response.config : {};
      setCommitted(config); setState("confirmed");
      emitRecordConfigCommitted(actionId, config, response);
    } catch (exception) {
      const terminal = exception.status === 410 || !!(exception.data && exception.data.terminal === true);
      setError(exception.message || String(exception));
      setState(terminal ? (exception.status === 410 ? "expired" : "terminal") : "pending");
      if (terminal) window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
        detail: { status: exception.status === 410 ? "expired" : "terminal", action_id: actionId },
      }));
    } finally { busyRef.current = false; }
  };
  return (
    <div style={{ alignSelf: "stretch", border: "1px solid var(--red)", padding: 12, background: "var(--white)" }}>
      <div className="label" style={{ color: "var(--red)" }}>RECORD CONFIG · CONFIRMATION</div>
      <div style={{ fontSize: 14, fontWeight: 800, marginTop: 5 }}>{title}</div>
      <div className="mono muted" style={{ fontSize: 9.5, marginTop: 5 }}>{actionId || "—"}</div>
      {summary && <div style={{ fontSize: 11.5, lineHeight: 1.55, marginTop: 9, whiteSpace: "pre-wrap" }}>{summary}</div>}
      <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 6, marginTop: 9 }}><span className="label dim">CONFIRM ENDPOINT</span><div className="mono" style={{ fontSize: 10.5, marginTop: 3, overflowWrap: "anywhere" }}>{confirmEndpoint || "—"}</div></div>
      <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 6, marginTop: 7 }}><span className="label dim">REJECT ENDPOINT</span><div className="mono" style={{ fontSize: 10.5, marginTop: 3, overflowWrap: "anywhere" }}>{rejectEndpoint || "—"}</div></div>
      <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 6, marginTop: 7 }}><span className="label dim">{t("確認期限")}</span><span className="mono" style={{ float: "right", fontSize: 10.5 }}>{text(confirmationExpiresAt)}</span></div>
      {!!actionFields.length && <div style={{ marginTop: 8 }}>{actionFields.map((field, index) => <div key={field.key || field.label || index} className="row spread g8" style={{ fontSize: 10.5, padding: "3px 0", alignItems: "flex-start" }}><span className="muted">{field.label || field.key || `#${index + 1}`}</span><span style={{ textAlign: "right", maxWidth: "62%", overflowWrap: "anywhere", whiteSpace: "pre-wrap" }}>{text(field.value)}</span></div>)}</div>}
      <div style={{ marginTop: 9 }}><div className="label dim">SERVER PAYLOAD</div><pre style={{ margin: "5px 0 0", padding: 9, border: "1px solid var(--hair)", background: "var(--surface-2)", fontSize: 10.5, lineHeight: 1.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{fullPayload || "{}"}</pre></div>
      {error && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.5, lineHeight: 1.45, marginTop: 8 }}>{error}</div>}
      {["pending", "confirming", "rejecting"].includes(state) && <div className="row g6" style={{ marginTop: 10 }}><button className="btn ghost sm" disabled={state !== "pending"} onClick={() => decide("reject")}>{action.reject_label || t("取消提交")}</button><button className="btn primary sm" disabled={state !== "pending"} onClick={() => decide("confirm")}>{action.confirm_label || t("確認提交")}</button></div>}
      {(state === "confirming" || state === "rejecting") && <div className="step-line" style={{ marginTop: 9 }}><Icon2 name="refresh" size={10}/>{t(state === "confirming" ? "正在提交檔案配置…" : "正在取消提交…")}</div>}
      {state === "executing" && <div className="step-line" style={{ marginTop: 9 }}><Icon2 name="refresh" size={10}/>{t("正在核對配置提交結果…")}</div>}
      {state === "confirmed" && <div style={{ color: "var(--ok)", fontSize: 11.5, fontWeight: 700, marginTop: 9 }}>{t("檔案配置已提交")} · {text(committed && committed.key)} · R{text(committed && committed.revision_no)}</div>}
      {state === "rejected" && <div className="muted" style={{ fontSize: 11.5, marginTop: 9 }}>{t("已取消，不會修改檔案配置")}</div>}
      {(state === "expired" || state === "terminal") && <div style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 700, marginTop: 9 }}>{t("配置提案已失效，請重新產生預覽")}</div>}
    </div>
  );
};

const emitRecordConfigCommitted = (actionId, config, response = null, status = "completed") => {
  const detail = { event: "record_config_committed", status, action_id: actionId, config };
  if (response) detail.response = response;
  window.dispatchEvent(new CustomEvent("w2-record-config-committed", { detail }));
};
const emitRecordConfigRejected = (actionId, status = "rejected", response = null) => {
  const detail = { event: "record_config_rejected", status, action_id: actionId };
  if (response) detail.response = response;
  window.dispatchEvent(new CustomEvent("w2-record-config-rejected", { detail }));
};

/* 通用命令確認卡只信任固定 action 契約與固定路由。action_key 同時是
   去重鍵與路由 id 的唯一來源，避免流事件夾帶任意端點。 */
const OPERATION_TERMINAL_STATUSES = new Set(["completed", "cancelled", "failed", "expired", "outcome_unknown"]);
const OPERATION_KNOWN_STATUSES = new Set(["pending", "authorized", "executing", ...OPERATION_TERMINAL_STATUSES]);
const OPERATION_EDIT_TYPES = new Set(["text", "textarea", "boolean", "integer", "number", "select"]);
/* Keep these in lockstep with the server's typed-confirmation compatibility
   path. Strong phrases always enter the no-execution resurface path; weak
   acknowledgements do so only while a pending card is already visible. */
const SECRETARY_STRONG_TEXT_CONFIRMATION_RE = /^\s*(?:確認|确认|同意|yes|confirm|proceed)\s*[。.!！]?\s*$/i;
const SECRETARY_WEAK_TEXT_CONFIRMATION_RE = /^\s*(?:可以|好|好的)\s*[。.!！]?\s*$/i;
const operationConfirmationAction = (source) => {
  if (!source || typeof source !== "object" || Array.isArray(source)) return null;
  const payload = source.payload && typeof source.payload === "object" && !Array.isArray(source.payload)
    ? source.payload : null;
  const candidates = [source.action, payload && payload.action, source, payload];
  for (const candidate of candidates) {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) continue;
    if (candidate.kind !== "command_confirmation") continue;
    const actionKey = typeof candidate.action_key === "string" ? candidate.action_key.trim() : "";
    if (!actionKey.startsWith("command:") || !actionKey.slice("command:".length)) continue;
    const keyId = actionKey.slice("command:".length);
    if (!/^\d+$/.test(keyId)) continue;
    const candidateId = candidate.id != null ? candidate.id : candidate.action_id;
    if (candidateId != null && candidateId !== "" && String(candidateId) !== keyId) continue;
    return candidate;
  }
  return null;
};
const operationConfirmationId = (action) => {
  const key = action && typeof action.action_key === "string" ? action.action_key.trim() : "";
  return key.startsWith("command:") ? key.slice("command:".length) : "";
};
const operationCompletionReceipt = (action) => {
  if (!action || String(action.status || "").toLowerCase() !== "completed") return null;
  const actionId = operationConfirmationId(action);
  if (!/^\d+$/.test(actionId)) return null;
  const outcome = action.outcome && typeof action.outcome === "object" && !Array.isArray(action.outcome)
    ? action.outcome : {};
  const receipt = action.completion_receipt && typeof action.completion_receipt === "object"
    && !Array.isArray(action.completion_receipt) ? action.completion_receipt
    : outcome.completion_receipt && typeof outcome.completion_receipt === "object"
      && !Array.isArray(outcome.completion_receipt) ? outcome.completion_receipt : null;
  if (!receipt || String(outcome.status || "").toLowerCase() !== "completed"
      || outcome.operation_completed !== true
      || String(receipt.status || "").toLowerCase() !== "completed") return null;
  const receiptNo = String(receipt.receipt_no || action.receipt_no || "").trim();
  const completedAt = String(receipt.completed_at || action.completed_at
    || (action.timestamps && action.timestamps.completed_at) || "").trim();
  const receiptMatch = /^ACT-(\d{8,})$/.exec(receiptNo);
  const normalizedReceiptId = receiptMatch && receiptMatch[1].replace(/^0+(?=\d)/, "");
  const normalizedActionId = actionId.replace(/^0+(?=\d)/, "");
  if (!receiptMatch || normalizedReceiptId !== normalizedActionId || !completedAt) return null;
  if (receipt.action_id != null && String(receipt.action_id) !== String(actionId)) return null;
  if (receipt.action_key != null && String(receipt.action_key) !== String(action.action_key)) return null;
  return { ...receipt, receipt_no: receiptNo, completed_at: completedAt };
};
const operationProjectedStatus = (action) => {
  const status = String(action && action.status || "").trim().toLowerCase();
  return status === "completed" && !operationCompletionReceipt(action)
    ? "outcome_unknown" : status;
};
const operationConfirmationEnvelope = (source) => {
  const action = operationConfirmationAction(source);
  if (!action) return null;
  const id = operationConfirmationId(action);
  return id ? { id, action_key: action.action_key, action } : null;
};
const operationConfirmationKey = (confirmation) => {
  const action = confirmation && confirmation.action;
  return action && typeof action.action_key === "string" ? action.action_key : "";
};
const SECRETARY_CONFIRMATION_ROLES = new Set([
  "operation_confirmation", "record_confirmation", "record_config_confirmation",
]);
const secretaryConfirmationItemKey = (item) => {
  if (!item || !SECRETARY_CONFIRMATION_ROLES.has(item.role)) return "";
  if (item.role === "operation_confirmation") return operationConfirmationKey(item.confirmation);
  const confirmation = item.confirmation || {};
  const action = confirmation.action || (confirmation.payload && confirmation.payload.action) || {};
  const id = confirmation.id || action.id || action.action_id;
  return id == null || id === "" ? "" : `${item.role}:${id}`;
};
let secretaryCredentialSequence = 0;
const secretaryCredentialItem = (credential, actionKey = "", ordinal = 0, credentialDelivery = null) => {
  if (!credential || !credential.value) return null;
  const boundActionKey = String(actionKey || credential.action_key || "").trim();
  const delivery = secretaryCredentialDeliveryEnvelope(credentialDelivery, boundActionKey);
  const durablePart = credential.delivery_id || credential.key_id || credential.key_hint;
  const deliveryKey = durablePart
    ? String(credential.delivery_id || `${boundActionKey || "direct"}:${credential.kind || "credential"}:${durablePart}`)
    : `local:${Date.now()}:${++secretaryCredentialSequence}:${ordinal}`;
  return {
    role: "cred",
    credential,
    action_key: boundActionKey,
    delivery_key: deliveryKey,
    credential_delivery: delivery,
  };
};
const secretaryCredentialKey = item => item && item.role === "cred"
  ? String(item.delivery_key || (item.credential && item.credential.delivery_id) || "") : "";

/* Active business drafts are read-only projections from the AI service.  The
   browser deliberately accepts a small, bounded contract so a draft can be
   restored and updated without treating arbitrary server payloads as UI. */
const BUSINESS_DRAFT_TERMINAL_STATUSES = new Set([
  "completed", "cancelled", "rejected", "expired", "archived", "superseded", "inactive",
]);
const businessDraftText = (value, limit = 4000) => {
  if (value == null) return "";
  let text = "";
  if (typeof value === "string") text = value;
  else if (typeof value === "number" || typeof value === "boolean") text = String(value);
  else {
    try { text = JSON.stringify(value, null, 2); }
    catch (error) { text = String(value); }
  }
  return text.slice(0, limit);
};
const businessDraftFieldCandidates = (candidate) => {
  if (Array.isArray(candidate && candidate.fields)) return candidate.fields;
  if (!candidate || !candidate.fields || typeof candidate.fields !== "object") return [];
  return Object.entries(candidate.fields).map(([key, value]) => {
    if (value && typeof value === "object" && !Array.isArray(value)
        && (Object.prototype.hasOwnProperty.call(value, "value")
          || Object.prototype.hasOwnProperty.call(value, "label")
          || Object.prototype.hasOwnProperty.call(value, "missing"))) {
      return { ...value, key: value.key || key };
    }
    return { key, value };
  });
};
const businessDraftMissingField = (value, index) => {
  const candidate = value && typeof value === "object" && !Array.isArray(value)
    ? value : { key: value };
  const key = businessDraftText(candidate.key || candidate.name || candidate.label, 120).trim()
    || `missing-${index + 1}`;
  const label = businessDraftText(candidate.label || candidate.name || candidate.key, 160).trim()
    || key;
  return { key, label };
};
const normalizeBusinessDraft = (candidate, index = 0) => {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  const status = businessDraftText(candidate.status || (candidate.active === false ? "inactive" : "active"), 48)
    .trim().toLowerCase() || "active";
  const kind = businessDraftText(candidate.kind || candidate.domain || candidate.type, 96).trim();
  const title = businessDraftText(candidate.title || candidate.name || candidate.label, 240).trim()
    || `業務草稿 ${index + 1}`;
  const identity = candidate.draft_key != null ? candidate.draft_key
    : candidate.draft_id != null ? candidate.draft_id
      : candidate.id != null ? candidate.id : candidate.key;
  const draftKey = businessDraftText(identity, 180).trim()
    || `business-draft:${kind || "general"}:${title}`.slice(0, 180);
  const rawMissing = Array.isArray(candidate.missing_fields) ? candidate.missing_fields
    : Array.isArray(candidate.missing) ? candidate.missing : [];
  const missingFields = rawMissing.slice(0, 48).map(businessDraftMissingField);
  const missingKeys = new Set(missingFields.map(field => field.key));
  const seenFields = new Set();
  const fields = businessDraftFieldCandidates(candidate).slice(0, 48).reduce((rows, field, fieldIndex) => {
    const source = field && typeof field === "object" && !Array.isArray(field)
      ? field : { value: field };
    const key = businessDraftText(source.key || source.name || source.label, 120).trim()
      || `field-${fieldIndex + 1}`;
    if (seenFields.has(key)) return rows;
    seenFields.add(key);
    const fieldStatus = businessDraftText(source.status, 32).trim().toLowerCase();
    const missing = source.missing === true || missingKeys.has(key) || fieldStatus === "missing";
    rows.push({
      key,
      label: businessDraftText(source.label || source.name || source.key, 160).trim() || key,
      value: source.sensitive === true ? "••••••" : businessDraftText(source.value),
      required: source.required === true,
      missing,
      status: fieldStatus || (missing ? "missing" : "captured"),
    });
    return rows;
  }, []);
  missingFields.forEach((missing) => {
    if (seenFields.has(missing.key) || fields.length >= 48) return;
    seenFields.add(missing.key);
    fields.push({
      key: missing.key, label: missing.label, value: "", required: true,
      missing: true, status: "missing",
    });
  });
  const rawVersion = candidate.version != null ? candidate.version
    : candidate.revision != null ? candidate.revision : "";
  const draftIdCandidate = candidate.draft_id != null ? candidate.draft_id
    : /^business-draft:(\d+)$/.test(draftKey) ? draftKey.split(":").pop() : null;
  const draftId = Number(draftIdCandidate);
  return {
    draft_key: draftKey,
    draft_id: Number.isSafeInteger(draftId) && draftId > 0 ? draftId : null,
    bundle_id: candidate.bundle_id != null ? Number(candidate.bundle_id) : null,
    title,
    kind,
    summary: businessDraftText(candidate.summary || candidate.description, 1200).trim(),
    status,
    active: candidate.active !== false && !BUSINESS_DRAFT_TERMINAL_STATUSES.has(status),
    cancellable: candidate.cancellable === true,
    version: businessDraftText(rawVersion, 48).trim(),
    updated_at: businessDraftText(candidate.updated_at || candidate.updatedAt, 80).trim(),
    fields,
    missing_fields: missingFields,
  };
};
const businessDraftKey = item => item && item.role === "business_draft"
  && item.draft ? String(item.draft.draft_key || "") : "";
const businessDraftVersionRank = draft => {
  const text = String(draft && draft.version || "").trim().replace(/^v/i, "");
  const value = Number(text);
  return Number.isFinite(value) ? value : null;
};
const shouldApplyBusinessDraft = (current, incoming) => {
  if (!incoming) return false;
  if (!current) return true;
  const currentVersion = businessDraftVersionRank(current);
  const incomingVersion = businessDraftVersionRank(incoming);
  if (currentVersion != null && incomingVersion != null && incomingVersion < currentVersion) return false;
  if (currentVersion === incomingVersion) {
    const currentUpdated = Date.parse(current.updated_at || "");
    const incomingUpdated = Date.parse(incoming.updated_at || "");
    if (Number.isFinite(currentUpdated) && Number.isFinite(incomingUpdated)
        && incomingUpdated < currentUpdated) return false;
  }
  return true;
};
const secretaryBusinessDraftItems = (source) => {
  if (!source || typeof source !== "object") return [];
  const candidates = [];
  const add = value => {
    if (Array.isArray(value)) candidates.push(...value);
    else if (value && typeof value === "object") candidates.push(value);
  };
  if (Array.isArray(source)) add(source);
  else {
    const draftSnapshot = source.business_draft_snapshot
      && typeof source.business_draft_snapshot === "object"
      ? source.business_draft_snapshot : null;
    if (draftSnapshot && draftSnapshot.available === true) add(draftSnapshot.items);
    add(source.business_drafts);
    const payload = source.payload && typeof source.payload === "object"
      && !Array.isArray(source.payload) ? source.payload : null;
    if (payload) add(payload.business_drafts);
    const sessionState = source.session_state && typeof source.session_state === "object"
      ? source.session_state : payload && payload.session_state && typeof payload.session_state === "object"
        ? payload.session_state : null;
    if (sessionState) add(sessionState.business_drafts);
    if (source.card_type === "business_draft") add(source.business_draft || source.draft);
    if (payload && payload.card_type === "business_draft") add(payload.business_draft || payload.draft);
  }
  return candidates.map(normalizeBusinessDraft).filter(Boolean)
    .map(draft => ({ role: "business_draft", draft }));
};
const secretaryItemAnchorIndex = (items, item) => {
  const messageId = item && item.anchor_message_id;
  if (messageId != null && messageId !== "") {
    const index = items.findIndex(candidate => candidate && String(candidate.message_id || "") === String(messageId));
    if (index >= 0) return index;
  }
  const action = item && item.role === "operation_confirmation"
    ? operationConfirmationAction(item.confirmation) : null;
  const runId = (item && item.anchor_run_id) || (action && (action.source_run_id || action.run_id));
  if (runId != null && runId !== "") {
    const index = items.findIndex(candidate => candidate && candidate.role === "a"
      && String(candidate.run_id || "") === String(runId));
    if (index >= 0) return index;
  }
  return -1;
};
const insertSecretaryItemAtAnchor = (items, item) => {
  const anchorIndex = secretaryItemAnchorIndex(items, item);
  if (anchorIndex < 0) { items.push(item); return; }
  const anchorMessageId = items[anchorIndex] && items[anchorIndex].message_id;
  const anchorRunId = items[anchorIndex] && items[anchorIndex].run_id;
  let insertion = anchorIndex + 1;
  while (insertion < items.length) {
    const candidate = items[insertion];
    if (!candidate || (!SECRETARY_CONFIRMATION_ROLES.has(candidate.role) && candidate.role !== "cred")) break;
    const sameMessage = anchorMessageId != null && String(candidate.anchor_message_id || "") === String(anchorMessageId);
    const sameRun = anchorRunId != null && String(candidate.anchor_run_id || "") === String(anchorRunId);
    if (!sameMessage && !sameRun) break;
    insertion += 1;
  }
  items.splice(insertion, 0, item);
};
const operationStatusRank = (status) => status === "pending" ? 0
  : status === "authorized" ? 1
    : status === "executing" ? 2 : OPERATION_TERMINAL_STATUSES.has(status) ? 3 : -1;
/* Confirmation state is monotonic.  Transcript cards are proposal-time
   snapshots and may arrive again after the server has already completed the
   action; they must never move a live action backwards. */
const shouldApplyOperationAction = (current, next) => {
  if (!next) return false;
  if (!current) return true;
  const currentKey = typeof current.action_key === "string" ? current.action_key : "";
  const nextKey = typeof next.action_key === "string" ? next.action_key : "";
  if (!currentKey || nextKey !== currentKey) return false;
  const currentRevision = Number(current.revision);
  const nextRevision = Number(next.revision);
  if (Number.isFinite(currentRevision) && Number.isFinite(nextRevision) && nextRevision < currentRevision) return false;
  const currentStatus = operationProjectedStatus(current);
  const nextStatus = operationProjectedStatus(next);
  if (OPERATION_TERMINAL_STATUSES.has(currentStatus) && !OPERATION_TERMINAL_STATUSES.has(nextStatus)) return false;
  if (Number.isFinite(currentRevision) && Number.isFinite(nextRevision) && nextRevision === currentRevision) {
    const currentRank = operationStatusRank(currentStatus);
    const nextRank = operationStatusRank(nextStatus);
    if (currentRank >= 0 && nextRank >= 0 && nextRank < currentRank) return false;
    const currentUpdated = Date.parse(current.updated_at || (current.timestamps && current.timestamps.updated_at) || "");
    const nextUpdated = Date.parse(next.updated_at || (next.timestamps && next.timestamps.updated_at) || "");
    if (currentRank === nextRank && Number.isFinite(currentUpdated) && Number.isFinite(nextUpdated) && nextUpdated < currentUpdated) return false;
  }
  return true;
};
const mergeSecretaryItems = (previous, incoming) => {
  const next = [...previous];
  const ordered = [
    ...incoming.filter(item => !item || item.role !== "cred"),
    ...incoming.filter(item => item && item.role === "cred"),
  ];
  ordered.forEach((item) => {
    if (!item) return;
    if (item.role === "business_draft") {
      const itemKey = businessDraftKey(item);
      if (!itemKey) return;
      const existing = next.findIndex(candidate => businessDraftKey(candidate) === itemKey);
      const currentDraft = existing >= 0 && next[existing] ? next[existing].draft : null;
      if (!shouldApplyBusinessDraft(currentDraft, item.draft)) return;
      if (!item.draft || item.draft.active !== true) {
        if (existing >= 0) next.splice(existing, 1);
        return;
      }
      if (existing >= 0) next[existing] = { ...next[existing], ...item };
      else next.push(item);
      return;
    }
    if (item.role === "cred") {
      const deliveryKey = secretaryCredentialKey(item);
      const existingCredential = deliveryKey
        ? next.findIndex(candidate => secretaryCredentialKey(candidate) === deliveryKey) : -1;
      if (existingCredential >= 0) {
        const current = next[existingCredential];
        next[existingCredential] = {
          ...current,
          ...item,
          credential: { ...(current.credential || {}), ...(item.credential || {}) },
          credential_delivery: item.credential_delivery || current.credential_delivery || null,
        };
        return;
      }
      const actionKey = String(item.action_key || (item.credential && item.credential.action_key) || "");
      const cardIndex = actionKey ? next.findIndex(candidate => candidate && candidate.role === "operation_confirmation"
        && operationConfirmationKey(candidate.confirmation) === actionKey) : -1;
      if (cardIndex < 0) { next.push(item); return; }
      let insertion = cardIndex + 1;
      while (insertion < next.length && next[insertion] && next[insertion].role === "cred"
        && String(next[insertion].action_key || "") === actionKey) insertion += 1;
      next.splice(insertion, 0, item);
      return;
    }
    if (!SECRETARY_CONFIRMATION_ROLES.has(item.role)) { next.push(item); return; }
    const itemKey = secretaryConfirmationItemKey(item);
    if (!itemKey) return;
    const existing = next.findIndex(candidate => secretaryConfirmationItemKey(candidate) === itemKey);
    if (existing >= 0) {
      const currentItem = next[existing];
      if (item.role !== "operation_confirmation") {
        next[existing] = { ...currentItem, ...item };
      } else {
        const currentAction = operationConfirmationAction(currentItem.confirmation);
        const incomingAction = operationConfirmationAction(item.confirmation);
        if (shouldApplyOperationAction(currentAction, incomingAction)) {
          const moveToTail = item.move_to_tail === true;
          const merged = {
            ...currentItem, ...item,
            confirmation: { ...currentItem.confirmation, ...item.confirmation, action: incomingAction },
          };
          delete merged.move_to_tail;
          if (moveToTail) {
            next.splice(existing, 1);
            next.push(merged);
          } else {
            next[existing] = merged;
          }
        }
      }
    } else {
      if (item.role === "operation_confirmation" && item.move_to_tail === true) {
        const appended = { ...item };
        delete appended.move_to_tail;
        next.push(appended);
      } else insertSecretaryItemAtAnchor(next, item);
    }
  });
  return next;
};
const operationEditableFields = (action) => {
  const seen = new Set();
  return (Array.isArray(action && action.editable_fields) ? action.editable_fields : []).filter((field) => {
    if (!field || typeof field !== "object" || Array.isArray(field)) return false;
    const key = typeof field.key === "string" ? field.key.trim() : "";
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  }).map(field => ({ ...field, key: field.key.trim(), type: OPERATION_EDIT_TYPES.has(field.type) ? field.type : "text" }));
};
const operationEditDraft = (action) => {
  const values = {};
  operationEditableFields(action).forEach((field) => {
    if (field.type === "boolean") values[field.key] = field.value === true;
    else if (field.type === "integer" || field.type === "number") values[field.key] = field.value == null ? "" : String(field.value);
    else values[field.key] = field.value == null ? "" : String(field.value);
  });
  return values;
};
const operationText = (value, pretty = false) => {
  if (value == null || value === "") return "—";
  if (typeof value === "string") return value;
  try { return JSON.stringify(value, null, pretty ? 2 : 0); }
  catch (e) { return String(value); }
};
const operationCredentialReceipt = (result) => {
  if (!result || typeof result !== "object" || Array.isArray(result)) return null;
  for (const [field, value] of Object.entries(result)) {
    if (typeof value !== "string" || !value.includes("一次性安全卡")) continue;
    return {
      field,
      hint: result[`${field}_hint`] || result.key_hint || result.api_key_hint || "",
      label: field === "api_key" ? "API Key" : "一次性憑證",
    };
  }
  return null;
};
const operationCredentialDeliveries = (source, nextAction) => {
  const actionKey = String(nextAction && nextAction.action_key || "");
  const nodes = [
    source,
    source && source.payload,
    source && source.action,
    source && source.payload && source.payload.action,
    nextAction,
  ];
  const deliveries = [], seen = new Set();
  nodes.forEach((node) => {
    if (!node || typeof node !== "object" || Array.isArray(node)) return;
    const candidates = [
      ...(Array.isArray(node.credential_deliveries) ? node.credential_deliveries : []),
      ...(node.credential_delivery ? [node.credential_delivery] : []),
    ];
    candidates.forEach((candidate) => {
      const delivery = secretaryCredentialDeliveryEnvelope(candidate, actionKey);
      if (!delivery || delivery.status === "acked" || delivery.status === "expired"
          || seen.has(delivery.delivery_id)) return;
      seen.add(delivery.delivery_id);
      deliveries.push(delivery);
    });
  });
  return deliveries;
};
const operationStatusLabel = (status, t) => ({
  pending: t("待確認"), authorized: t("已授權 · AI 接手"), executing: t("AI 執行中"), completed: t("已完成"), cancelled: t("已取消"),
  failed: t("執行失敗"), expired: t("已逾期"), outcome_unknown: t("結果待核對"),
}[status] || t("狀態異常"));

const OperationConfirmation = ({ confirmation, onActionChange, onTerminal, onMutationStart }) => {
  const t = window.W2_LANG.t;
  const initialAction = operationConfirmationAction(confirmation);
  const [action, setAction] = React.useState(initialAction);
  const actionRef = React.useRef(initialAction);
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState(() => operationEditDraft(initialAction));
  const [phase, setPhase] = React.useState("");
  const [localError, setLocalError] = React.useState("");
  const [syncState, setSyncState] = React.useState("loading");
  const [syncError, setSyncError] = React.useState("");
  const [syncNonce, setSyncNonce] = React.useState(0);
  const [credentialDeliveryVersion, setCredentialDeliveryVersion] = React.useState(0);
  const busyRef = React.useRef(false);
  const passkeyOperationRef = React.useRef(null);
  const passkeyFallbackRef = React.useRef(null);
  const terminalDeliveryRef = React.useRef(new Set());
  const credentialFetchInFlightRef = React.useRef(new Set());
  const credentialFetchDeliveredRef = React.useRef(new Set());
  const mountedRef = React.useRef(true);
  const actionKey = action && typeof action.action_key === "string" ? action.action_key : "";
  const actionId = operationConfirmationId(action);
  const actionPath = actionId ? `/api/agent/confirmation-actions/${encodeURIComponent(actionId)}` : "";
  const status = operationProjectedStatus(action);
  const terminal = OPERATION_TERMINAL_STATUSES.has(status);
  const knownStatus = OPERATION_KNOWN_STATUSES.has(status);
  const revision = action && action.revision;
  const hasRevision = Number.isInteger(revision) && revision >= 0;
  const canMutate = syncState === "ready" && status === "pending" && hasRevision && !!actionPath;
  const editableFields = operationEditableFields(action);
  const presentation = action && action.presentation && typeof action.presentation === "object" && !Array.isArray(action.presentation)
    ? action.presentation : {};
  const presentationFields = Array.isArray(presentation.fields)
    ? presentation.fields.filter(field => field && typeof field === "object" && !Array.isArray(field)) : [];
  const topLevelTimestamps = {};
  ["created_at", "updated_at", "expires_at", "authorized_at", "executing_at", "completed_at", "cancelled_at", "failed_at"].forEach((key) => {
    if (action && action[key] != null && action[key] !== "") topLevelTimestamps[key] = action[key];
  });
  const timestamps = action && action.timestamps && typeof action.timestamps === "object" && !Array.isArray(action.timestamps)
    ? { ...topLevelTimestamps, ...action.timestamps } : topLevelTimestamps;
  const verification = action && action.verification && typeof action.verification === "object" && !Array.isArray(action.verification)
    ? action.verification : null;
  const verificationOperator = verification && (
    (typeof verification.operator === "string" && verification.operator)
    || verification.global_username
    || (verification.operator && typeof verification.operator === "object" && verification.operator.global_username)
  );
  const credentialReceipt = operationCredentialReceipt(action && action.result);
  const completionReceipt = operationCompletionReceipt(action);

  React.useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const operation = passkeyOperationRef.current;
      const fallback = passkeyFallbackRef.current;
      if (operation && !operation.signal.aborted) operation.abort();
      if (fallback && !fallback.signal.aborted) fallback.abort();
      passkeyOperationRef.current = null;
      passkeyFallbackRef.current = null;
      busyRef.current = false;
    };
  }, []);

  const fetchCredentialDeliveries = (source, next, terminalDetail) => {
    if (typeof onTerminal !== "function") return;
    operationCredentialDeliveries(source, next).forEach((delivery) => {
      const deliveryId = delivery.delivery_id;
      if (credentialFetchInFlightRef.current.has(deliveryId)
          || credentialFetchDeliveredRef.current.has(deliveryId)) return;
      credentialFetchInFlightRef.current.add(deliveryId);
      W2.post(delivery.fetch_path, {
        delivery_id: deliveryId,
        credential_client_id: secretaryCredentialClientId(),
      }).then((response) => {
        if (!mountedRef.current) return;
        const responseDelivery = secretaryCredentialDeliveryEnvelope(
          response && response.credential_delivery || delivery,
          next.action_key,
        );
        const credentials = response && Array.isArray(response.credentials)
          ? response.credentials.filter(item => item && item.value) : [];
        if (!response || response.ok !== true || response.action_key !== next.action_key
            || !responseDelivery || responseDelivery.delivery_id !== deliveryId
            || !credentials.length || response.requires_ack !== true) {
          throw new Error(t("一次性憑證領取回應無效；服務端副本仍保留，請重新核對"));
        }
        credentialFetchDeliveredRef.current.add(deliveryId);
        setCredentialDeliveryVersion(version => version + 1);
        onTerminal({
          ...terminalDetail,
          credentials,
          credential_delivery: responseDelivery,
          credential_deliveries: [responseDelivery],
        });
      }).catch((error) => {
        if (mountedRef.current) {
          setLocalError((error && error.message)
            || t("操作已完成，但一次性憑證尚未領取；切回此頁或按重新核對即可重試"));
        }
      }).finally(() => {
        credentialFetchInFlightRef.current.delete(deliveryId);
      });
    });
  };

  const emitOperationTerminal = (source, next) => {
    const nextStatus = operationProjectedStatus(next);
    if (nextStatus !== "authorized" && !OPERATION_TERMINAL_STATUSES.has(nextStatus)) return;
    const nextCompletionReceipt = operationCompletionReceipt(next);
    const continuation = source && source.continuation
      ? source.continuation : next && next.continuation ? next.continuation : null;
    const credentials = source && Array.isArray(source.credentials)
      ? source.credentials : [];
    const continuationDelivery = source && source.continuation_delivery
      && typeof source.continuation_delivery === "object" ? source.continuation_delivery : null;
    const signature = `${next.action_key}:${nextStatus}:${next.revision || ""}:${nextCompletionReceipt && nextCompletionReceipt.receipt_no || ""}:${credentials.length}:${continuation ? "continue" : ""}:${continuationDelivery && continuationDelivery.mode || ""}`;
    const detail = {
      action_key: next.action_key,
      confirmation_action_id: operationConfirmationId(next),
      status: nextStatus,
      outcome: next.outcome || null,
      completion_receipt: nextCompletionReceipt,
      continuation,
      continuation_delivery: continuationDelivery,
      credentials,
    };
    const credentialDeliveries = operationCredentialDeliveries(source, next);
    const directDetail = credentialDeliveries.length ? {
      ...detail,
      credential_delivery: credentialDeliveries.length === 1 ? credentialDeliveries[0] : null,
      credential_deliveries: credentialDeliveries,
    } : detail;
    fetchCredentialDeliveries(source, next, directDetail);
    if (terminalDeliveryRef.current.has(signature)) return;
    terminalDeliveryRef.current.add(signature);
    if (typeof onTerminal === "function") onTerminal(directDetail);
    // Compatibility signal never carries plaintext credentials. Same-page
    // third-party scripts must not be able to observe one-time secrets.
    setTimeout(() => window.dispatchEvent(new CustomEvent("w2-operation-terminal", {
      detail: { ...detail, credentials: [] },
    })), 0);
  };

  const applyServerAction = (source) => {
    const next = operationConfirmationAction(source);
    if (!next || next.action_key !== actionKey) throw new Error(t("確認操作回應不匹配"));
    if (!shouldApplyOperationAction(actionRef.current, next)) return actionRef.current;
    actionRef.current = next;
    setAction(next);
    setDraft(operationEditDraft(next));
    if (operationProjectedStatus(next) !== "pending") setEditing(false);
    if (typeof onActionChange === "function") onActionChange(next);
    emitOperationTerminal(source, next);
    return next;
  };

  React.useEffect(() => {
    const next = operationConfirmationAction(confirmation);
    if (!next || !actionKey || next.action_key !== actionKey) return;
    if (!shouldApplyOperationAction(actionRef.current, next)) return;
    actionRef.current = next;
    setAction(next);
  }, [confirmation]);
  React.useEffect(() => {
    if (status !== "pending") setEditing(false);
  }, [status]);
  /* The message transcript stores the proposal-time snapshot.  Closing the
     secretary unmounts this card, so every mount must rehydrate from the
     actor-scoped, no-store action endpoint before any mutation is enabled. */
  React.useEffect(() => {
    if (!actionPath) {
      setSyncState("error");
      setSyncError(t("確認記錄識別無效，操作已鎖定"));
      return undefined;
    }
    let disposed = false;
    setSyncState("loading");
    setSyncError("");
    W2.json(actionPath).then((response) => {
      if (disposed) return;
      applyServerAction(response);
      setSyncState("ready");
    }).catch((exception) => {
      if (disposed) return;
      setSyncState("error");
      setSyncError(exception && exception.status === 404
        ? t("找不到服務端確認記錄，操作已鎖定")
        : t("無法核對最新狀態，操作已鎖定"));
    });
    return () => { disposed = true; };
  }, [actionPath, syncNonce]);
  /* pending/executing，以及尚未成功領取憑證的 completed 卡，都以固定
     狀態端點低頻核對；切回頁籤時立即核對。
     每個頁籤有獨立 client id，秘密不使用 storage/BroadcastChannel 廣播。 */
  React.useEffect(() => {
    const unresolvedCredentialDelivery = OPERATION_TERMINAL_STATUSES.has(status)
      && operationCredentialDeliveries(action, action).some(delivery =>
        !credentialFetchDeliveredRef.current.has(delivery.delivery_id)
      );
    if ((!["pending", "authorized", "executing"].includes(status) && !unresolvedCredentialDelivery)
        || !actionPath) return undefined;
    let disposed = false;
    let timer = null;
    let inFlight = false;
    const schedule = () => {
      if (disposed) return;
      if (timer) clearTimeout(timer);
      timer = setTimeout(poll, ["authorized", "executing"].includes(status) ? 4000 : 15000);
    };
    const poll = async () => {
      if (disposed || inFlight) return;
      inFlight = true;
      try {
        const response = await W2.json(actionPath);
        if (disposed) return;
        applyServerAction(response);
        setSyncState("ready");
        setSyncError("");
        setLocalError("");
      } catch (exception) {
        if (!disposed) setLocalError(exception.message || t("暫時無法更新執行狀態"));
      } finally {
        inFlight = false;
      }
      schedule();
    };
    const reconcileWhenVisible = () => {
      if (document.visibilityState === "hidden") return;
      if (timer) { clearTimeout(timer); timer = null; }
      poll();
    };
    schedule();
    window.addEventListener("focus", reconcileWhenVisible);
    document.addEventListener("visibilitychange", reconcileWhenVisible);
    return () => {
      disposed = true;
      if (timer) clearTimeout(timer);
      window.removeEventListener("focus", reconcileWhenVisible);
      document.removeEventListener("visibilitychange", reconcileWhenVisible);
    };
  }, [status, actionPath, credentialDeliveryVersion]);

  if (!action || !actionId) return null;

  const buildEditedValues = () => {
    const values = {};
    for (const field of editableFields) {
      const raw = Object.prototype.hasOwnProperty.call(draft, field.key) ? draft[field.key] : "";
      const missing = raw == null || (typeof raw === "string" && !raw.trim());
      if (field.required && missing) return { error: `${field.label || field.key}${t("為必填項")}` };
      if (field.type === "boolean") values[field.key] = raw === true;
      else if (field.type === "integer") {
        if (missing && !field.required) values[field.key] = null;
        else {
          const value = Number(raw);
          if (!Number.isInteger(value)) return { error: `${field.label || field.key}${t("必須是整數")}` };
          values[field.key] = value;
        }
      } else if (field.type === "number") {
        if (missing && !field.required) values[field.key] = null;
        else {
          const value = Number(raw);
          if (!Number.isFinite(value)) return { error: `${field.label || field.key}${t("必須是數字")}` };
          values[field.key] = value;
        }
      } else values[field.key] = String(raw == null ? "" : raw);
    }
    return { values };
  };
  const reconcileUncertainMutation = async (submittedRevision, unchangedMessage = "") => {
    const response = await W2.json(actionPath);
    const latest = applyServerAction(response);
    const changed = latest.status !== "pending" || latest.revision !== submittedRevision;
    if (changed) { setEditing(false); setLocalError(""); return; }
    setLocalError(unchangedMessage || t("網絡中斷，服務端仍顯示待確認；請核對後重試"));
  };
  const mutate = async (operation) => {
    if (!canMutate || busyRef.current) return;
    if (typeof onMutationStart === "function") onMutationStart(actionKey);
    let values = null;
    if (operation === "edit") {
      const built = buildEditedValues();
      if (built.error) { setLocalError(built.error); return; }
      values = built.values;
    }
    const submittedRevision = revision;
    busyRef.current = true; setPhase(operation === "confirm" ? "passkey-options" : operation); setLocalError("");
    let postStarted = false;
    try {
      const body = { expected_revision: submittedRevision };
      if (operation === "edit") body.values = values;
      if (operation === "confirm") {
        if (!W2.Passkeys || typeof W2.Passkeys.supported !== "function"
          || typeof W2.Passkeys.requestStepUp !== "function" || !W2.Passkeys.supported()) {
          throw new Error(t("此確認操作必須使用 Passkey；目前裝置或連線不支援，操作尚未執行"));
        }
        const operationController = typeof window.AbortController === "function"
          ? new window.AbortController() : null;
        const fallbackController = typeof window.AbortController === "function"
          ? new window.AbortController() : null;
        passkeyOperationRef.current = operationController;
        passkeyFallbackRef.current = fallbackController;
        const stepUpToken = await W2.Passkeys.requestStepUp(
          "ai.confirmation.execute",
          { action_id: Number(actionId), revision: Number(action.revision) },
          {
            mode: "platform",
            fallbackToHybrid: true,
            platformTimeoutMs: 30000,
            signal: operationController && operationController.signal,
            fallbackSignal: fallbackController && fallbackController.signal,
            onStatus: stage => {
              const nextPhase = {
                options: "passkey-options",
                authenticator: "passkey",
                "authenticator-platform": "passkey-platform",
                "authenticator-hybrid-timeout": "passkey-hybrid-timeout",
                "authenticator-hybrid-switch": "passkey-hybrid-switch",
                verify: "passkey-verify",
              }[stage];
              if (nextPhase) setPhase(nextPhase);
            },
          },
        );
        if (typeof stepUpToken !== "string" || !stepUpToken.trim()) {
          throw new Error(t("Passkey 驗證沒有返回有效的一次性授權，操作尚未執行"));
        }
        body.step_up_token = stepUpToken;
        body.credential_client_id = secretaryCredentialClientId();
        // The controller owns only options, authenticator and verification.
        // Once a grant exists, the formal write must run to an observable
        // response (or GET reconciliation) and must never be aborted by a
        // card unmount.
        if (passkeyOperationRef.current === operationController) {
          passkeyOperationRef.current = null;
        }
        if (passkeyFallbackRef.current === fallbackController) {
          passkeyFallbackRef.current = null;
        }
        if (operationController && !operationController.signal.aborted) {
          operationController.abort();
        }
        if (fallbackController && !fallbackController.signal.aborted) {
          fallbackController.abort();
        }
        setPhase("confirm");
      }
      postStarted = true;
      const response = await W2.post(`${actionPath}/${operation}`, body);
      applyServerAction(response);
      setEditing(false);
    } catch (exception) {
      if (!postStarted) {
        let friendly = exception;
        if (W2.Passkeys && typeof W2.Passkeys.friendlyError === "function") {
          try { friendly = W2.Passkeys.friendlyError(exception) || exception; } catch (e) {}
        }
        setLocalError((friendly && friendly.message) || t("Passkey 驗證未完成，操作尚未執行"));
      } else {
        const latest = operationConfirmationAction(exception && exception.data);
        if (latest && latest.action_key === actionKey) {
          applyServerAction(latest);
          setEditing(false);
          setLocalError(exception.message || "");
        } else {
          try { await reconcileUncertainMutation(submittedRevision, exception && exception.status ? exception.message : ""); }
          catch (reconcileError) {
            const original = exception && exception.message ? exception.message : t("網絡請求失敗");
            setSyncState("error");
            setSyncError(t("無法核對最新狀態，操作已鎖定"));
            setLocalError(`${original} · ${t("無法向服務端核對結果")}`);
          }
        }
      }
    } finally {
      busyRef.current = false;
      passkeyOperationRef.current = null;
      passkeyFallbackRef.current = null;
      if (mountedRef.current) setPhase("");
    }
  };
  const switchPasskeyToPhone = () => {
    const controller = passkeyFallbackRef.current;
    if (!controller || controller.signal.aborted) return;
    setPhase("passkey-hybrid-switch");
    controller.abort();
  };
  const cancelPasskeyVerification = () => {
    const controller = passkeyOperationRef.current;
    if (!controller || controller.signal.aborted) return;
    controller.abort();
  };
  const updateDraft = (field, value) => setDraft(current => ({ ...current, [field.key]: value }));
  const phaseLabel = phase === "passkey-options" ? t("正在取得安全挑戰…")
    : phase === "passkey-platform" ? t("正在開啟本機 Passkey…")
    : phase === "passkey-hybrid-timeout" ? t("本機 Passkey 未回應，正在自動開啟手機 Passkey QR…")
    : phase === "passkey-hybrid-switch" ? t("正在切換至手機 Passkey QR…")
    : phase === "passkey-verify" ? t("正在驗證 Passkey…")
    : phase === "passkey" ? t("正在使用 Passkey 完成本人驗證…")
    : phase === "confirm" ? t("正在簽署 AI 授權…")
    : phase === "cancel" ? t("正在取消…") : phase === "edit" ? t("正在保存修改…") : "";
  const statusLabel = syncState === "loading" ? t("核對中")
    : syncState === "error" ? t("狀態未核對") : operationStatusLabel(status, t);
  const statusColor = syncState !== "ready" ? "var(--ink-4)" : status === "completed" ? "var(--ok)"
    : ["failed", "expired", "outcome_unknown"].includes(status) ? "var(--danger)"
      : status === "cancelled" ? "var(--ink-4)" : "var(--ink)";
  return (
    <div className={`operation-confirmation-card${status === "completed" ? " is-complete" : ""}`}
      data-action-key={actionKey} data-status={status} data-sync-state={syncState} style={{ alignSelf: "stretch", flex: "0 0 auto", minWidth: 0, border: "2px solid var(--rule)", borderLeft: "5px solid var(--red)", padding: 13, background: "var(--white)", overflow: "visible" }}>
      <style>{`
        @keyframes w2-operation-confirmation-complete{0%{transform:translateY(3px);box-shadow:0 0 0 rgba(24,130,78,0)}45%{transform:translateY(0);box-shadow:0 0 0 7px rgba(24,130,78,.12)}100%{box-shadow:0 0 0 rgba(24,130,78,0)}}
        @keyframes w2-operation-confirmation-check{0%{transform:scale(.65);opacity:0}70%{transform:scale(1.12);opacity:1}100%{transform:scale(1);opacity:1}}
        .operation-confirmation-card.is-complete{animation:w2-operation-confirmation-complete .52s ease-out both}
        .operation-confirmation-card.is-complete .operation-confirmation-check{animation:w2-operation-confirmation-check .4s ease-out both}
        @media (prefers-reduced-motion: reduce){.operation-confirmation-card.is-complete,.operation-confirmation-card.is-complete .operation-confirmation-check{animation:none!important;transform:none!important}}
      `}</style>
      <div className="row spread g8" style={{ alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div className="label" style={{ color: "var(--red)" }}>AI · AUTHORIZATION</div>
          <div style={{ fontSize: 15, fontWeight: 850, lineHeight: 1.3, marginTop: 6, overflowWrap: "anywhere" }}>{presentation.title || t("授權 AI 執行操作")}</div>
        </div>
        <span className="tag" style={{ flexShrink: 0, color: statusColor, borderColor: statusColor }}>{statusLabel}</span>
      </div>
      <div className="mono muted" style={{ fontSize: 9.5, marginTop: 6, overflowWrap: "anywhere" }}>{actionKey} · R{operationText(revision)}</div>
      {presentation.summary && <div style={{ fontSize: 11.5, lineHeight: 1.6, marginTop: 10, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{presentation.summary}</div>}
      {!!presentationFields.length && <div style={{ marginTop: 10, borderTop: "1px solid var(--hair)" }}>{presentationFields.map((field, index) => (
        <div key={field.key || field.label || index} className="row spread g8" style={{ alignItems: "flex-start", borderBottom: "1px solid var(--hair)", padding: "7px 0", fontSize: 10.8 }}>
          <span className="muted" style={{ minWidth: "34%" }}>{field.label || field.key || `#${index + 1}`}</span>
          <span style={{ textAlign: "right", whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{operationText(field.value)}</span>
        </div>
      ))}</div>}

      {editing && canMutate && <div style={{ marginTop: 11, padding: 10, border: "1px solid var(--rule)", background: "var(--surface-2)" }}>
        <div className="label dim">EDIT · SERVER ALLOWLIST</div>
        <div className="col g8" style={{ marginTop: 9 }}>{editableFields.map(field => (
          <label key={field.key} style={{ display: "grid", gap: 4, fontSize: 11 }}>
            <span style={{ fontWeight: 700 }}>{field.label || field.key}{field.required ? " *" : ""}</span>
            {field.type === "textarea" ? <textarea className="field" rows="3" value={draft[field.key] == null ? "" : draft[field.key]} onChange={event => updateDraft(field, event.target.value)}/>
              : field.type === "boolean" ? <span className="row g6"><input type="checkbox" checked={draft[field.key] === true} onChange={event => updateDraft(field, event.target.checked)}/>{draft[field.key] === true ? t("是") : t("否")}</span>
                : field.type === "select" ? <select className="field" value={draft[field.key] == null ? "" : draft[field.key]} onChange={event => updateDraft(field, event.target.value)}>{(Array.isArray(field.choices) ? field.choices : []).map(choice => <option key={String(choice)} value={String(choice)}>{String(choice).toUpperCase()}</option>)}</select>
                  : <input className="field" type={field.type === "integer" || field.type === "number" ? "number" : "text"} step={field.type === "integer" ? "1" : field.type === "number" ? "any" : undefined} value={draft[field.key] == null ? "" : draft[field.key]} onChange={event => updateDraft(field, event.target.value)}/>}
          </label>
        ))}</div>
        <button className="btn primary sm" style={{ marginTop: 10 }} disabled={!!phase} onClick={() => mutate("edit")}>{t("保存修改")}</button>
      </div>}

      {syncState === "loading" && <div className="step-line" style={{ marginTop: 10 }}><Icon2 name="refresh" size={10}/>{t("正在核對服務端確認狀態…")}</div>}
      {(phase || status === "authorized" || status === "executing") && <div className="step-line" style={{ marginTop: 10 }}><Icon2 name="refresh" size={10}/>{phaseLabel || (status === "authorized" ? t("授權信號已返回，AI Runtime 正在領取 Keychain") : t("AI Runtime 正在執行，完成後會自動更新"))}</div>}
      {phase === "passkey-platform" && <button type="button" className="btn sm" style={{ marginTop: 8 }} onClick={switchPasskeyToPhone}>{t("立即改用手機 Passkey（QR）")}</button>}
      {["passkey-options", "passkey", "passkey-platform", "passkey-hybrid-timeout", "passkey-hybrid-switch", "passkey-verify"].includes(phase)
        && <button type="button" className="btn ghost sm" style={{ marginTop: 8, marginLeft: phase === "passkey-platform" ? 6 : 0 }} onClick={cancelPasskeyVerification}>{t("取消驗證")}</button>}
      {(phase === "passkey-hybrid-timeout" || phase === "passkey-hybrid-switch") && <div className="muted" style={{ marginTop: 6, fontSize: 10.5 }}>{t("手機需已有此帳號的 Passkey 才能完成驗證。")}</div>}
      {status === "authorized" && action.authorization_keychain && <div role="status" style={{ marginTop: 10, padding: 9, border: "1px solid var(--rule)", background: "var(--surface-2)", fontSize: 11, lineHeight: 1.55 }}>
        <div className="label">AUTHORIZATION · KEYCHAIN</div>
        <div style={{ marginTop: 5 }}>{t("操作卡只完成授權；業務代碼由 AI Runtime 接手執行。")}</div>
        <div className="mono muted" style={{ marginTop: 4, overflowWrap: "anywhere" }}>{operationText(action.authorization_keychain.keychain_id)}</div>
      </div>}
      {status === "completed" && completionReceipt && <div className="operation-confirmation-check" style={{ color: "var(--ok)", fontSize: 12, fontWeight: 800, marginTop: 11 }}>
        <div className="row g8"><Icon2 name="check" size={15} color="var(--ok)"/>{t("操作已完成並保留在對話中")}</div>
        <div className="mono" style={{ fontSize: 9.8, marginTop: 5 }}>{t("完成回執")} · {completionReceipt.receipt_no} · {operationText(completionReceipt.completed_at)}</div>
      </div>}
      {status === "cancelled" && <div className="muted" style={{ fontSize: 11.5, fontWeight: 700, marginTop: 11 }}>{t("操作已取消，未再執行")}</div>}
      {status === "expired" && <div style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 800, marginTop: 11 }}>{t("確認已逾期，請重新發起操作")}</div>}
      {status === "failed" && <div style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 800, marginTop: 11 }}>{t("操作執行失敗")}</div>}
      {status === "outcome_unknown" && <div style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 800, marginTop: 11 }}>{t("執行結果暫時無法判定，請先核對業務資料，勿重複操作")}</div>}
      {!knownStatus && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.5, fontWeight: 800, marginTop: 11 }}>{t("服務端返回了未知狀態，操作已鎖定")}</div>}
      {action.result != null && <div style={{ marginTop: 10 }}><div className="label dim">RESULT · SERVER</div><pre style={{ margin: "5px 0 0", padding: 9, border: "1px solid var(--hair)", background: "var(--surface-2)", fontSize: 10.5, lineHeight: 1.5, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{operationText(action.result, true)}</pre></div>}
      {credentialReceipt && <div role="status" style={{ marginTop: 10, padding: 9, border: "1px solid var(--ok)", background: "var(--surface-2)", fontSize: 11, lineHeight: 1.55 }}>
        <div className="label" style={{ color: "var(--ok)" }}>{credentialReceipt.label} · ISSUED</div>
        <div style={{ marginTop: 5 }}>{t("明文只在簽發完成時透過一次性安全卡顯示，不會寫入聊天記錄。")}</div>
        {credentialReceipt.hint && <div className="mono muted" style={{ marginTop: 4 }}>{credentialReceipt.hint}</div>}
        <div className="muted" style={{ marginTop: 4 }}>{t("若沒有保存，請明確要求重新簽發；主 Key 會隨之輪換。")}</div>
      </div>}
      {action.error != null && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, lineHeight: 1.5, marginTop: 9, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{operationText(action.error, true)}</div>}
      {syncError && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, lineHeight: 1.5, marginTop: 9 }}>
        {syncError}
        <button type="button" className="btn ghost sm" style={{ marginLeft: 8 }} disabled={syncState === "loading"} onClick={() => setSyncNonce(value => value + 1)}>{t("重新核對")}</button>
      </div>}
      {localError && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, lineHeight: 1.5, marginTop: 9 }}>{localError}</div>}
      {status !== "pending" && verification && (verification.verified === true || verification.method === "webauthn") && <div style={{ marginTop: 10, padding: 9, border: "1px solid var(--ok)", background: "var(--surface-2)" }}>
        <div className="label" style={{ color: "var(--ok)" }}>PASSKEY · {t("已驗證")}</div>
        <div className="mono" style={{ fontSize: 9.8, lineHeight: 1.7, marginTop: 5, overflowWrap: "anywhere" }}>
          {verificationOperator && <div>{t("操作者")} · {operationText(verificationOperator)}</div>}
          {(verification.credential_name || verification.credential_id_hint) && <div>{t("憑證")} · {operationText(verification.credential_name)} · {operationText(verification.credential_id_hint)}</div>}
          {verification.verified_at && <div>{t("驗證時間")} · {operationText(verification.verified_at)}</div>}
          {(verification.rp_id || verification.origin) && <div>RP / ORIGIN · {operationText(verification.rp_id)} · {operationText(verification.origin)}</div>}
          {verification.user_verified === true && <div>USER VERIFICATION · REQUIRED / VERIFIED</div>}
          {verification.sign_count_after != null && <div>SIGN COUNT · {operationText(verification.sign_count_before)} → {operationText(verification.sign_count_after)}</div>}
          {verification.evidence_sha256 && <div>ASSERTION SHA-256 · {operationText(verification.evidence_sha256)}</div>}
          {verification.resource_digest && <div>RESOURCE DIGEST · {operationText(verification.resource_digest)}</div>}
        </div>
      </div>}
      {!!Object.keys(timestamps).length && <div className="mono muted" style={{ fontSize: 9.2, lineHeight: 1.65, marginTop: 9 }}>{Object.entries(timestamps).map(([key, value]) => <div key={key}>{key.toUpperCase()} · {operationText(value)}</div>)}</div>}

      <div className="row g6 wrap" style={{ marginTop: 12, paddingTop: 10, borderTop: "2px solid var(--rule)" }}>
        <button className="btn ghost sm" disabled={!canMutate || !!phase || editing} onClick={() => mutate("cancel")}>{t("取消")}</button>
        <button className="btn ghost sm" disabled={!canMutate || !!phase || !editableFields.length} onClick={() => { setEditing(current => !current); setLocalError(""); }}>{editing ? t("收起編輯") : t("編輯")}</button>
        <button className="btn primary sm" disabled={!canMutate || !!phase || editing} onClick={() => mutate("confirm")}>{t("授權 AI")}</button>
        {status === "pending" && syncState === "ready" && <span className="label dim">PASSKEY REQUIRED</span>}
        {terminal && <span className="label dim" style={{ marginLeft: "auto" }}>TERMINAL · AUDITED</span>}
      </div>
    </div>
  );
};

/* ── Workflow Repair Plan：確定性證據 + 獨立雙 Passkey 共簽 ── */
const WORKFLOW_REPAIR_CLOSED = new Set(["resolved", "cancelled"]);
const WORKFLOW_REPAIR_POLLING = new Set(["applying", "verifying", "retry_wait"]);
const workflowRepairArray = value => Array.isArray(value) ? value.filter(Boolean) : [];
const workflowRepairObject = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
const workflowRepairJsonObject = value => {
  if (value && typeof value === "object" && !Array.isArray(value)) return value;
  if (typeof value !== "string" || !value.trim()) return {};
  try { return workflowRepairObject(JSON.parse(value)); } catch (error) { return {}; }
};
const workflowRepairId = (item, primary, fallback) => {
  const value = item && (item[primary] != null ? item[primary] : item[fallback]);
  return /^\d+$/.test(String(value == null ? "" : value)) ? Number(value) : null;
};
const workflowRepairEnvelope = source => {
  const root = workflowRepairObject(source && source.data && !source.repair_case && !source.case
    ? source.data : source);
  const directLooksLikeCase = root.instance_id != null && (root.anomaly_code || root.case_id != null || root.risk_class);
  const repairCase = workflowRepairObject(
    root.repair_case || root.case || root.repair || (directLooksLikeCase ? root : null)
  );
  const plan = workflowRepairObject(root.current_plan || root.plan || repairCase.current_plan || repairCase.plan);
  const caseId = workflowRepairId(repairCase, "id", "case_id");
  if (caseId == null) return null;
  const planJson = workflowRepairJsonObject(plan.plan_json || plan.plan);
  const requirements = workflowRepairArray(root.requirements || repairCase.requirements || plan.requirements);
  const explicitMissing = workflowRepairArray(root.missing_requirements || repairCase.missing_requirements);
  const derivedMissing = requirements.filter(item => {
    const status = String(item.status || "").toLowerCase();
    return status === "missing" || status === "rejected" || item.missing === true;
  });
  const missingRequirements = explicitMissing.length ? explicitMissing : derivedMissing;
  const evidence = workflowRepairArray(root.evidence || repairCase.evidence || plan.evidence);
  const approvals = workflowRepairArray(root.approvals || plan.approvals || repairCase.approvals);
  const resolution = workflowRepairObject(repairCase.resolution);
  const report = workflowRepairObject(resolution.report);
  const anomalies = workflowRepairArray(root.anomalies || repairCase.anomalies || repairCase.anomaly_codes || report.findings);
  const safetyInvariants = workflowRepairArray(root.safety_invariants || plan.safety_invariants || repairCase.safety_invariants);
  const actions = workflowRepairArray(plan.actions || planJson.actions);
  return {
    raw: root, repairCase, plan, planJson, caseId,
    planId: workflowRepairId(plan, "id", "plan_id"),
    requirements, missingRequirements, evidence, approvals, anomalies, safetyInvariants, actions,
    approvalCount: Number(root.approval_count != null ? root.approval_count
      : plan.approval_count != null ? plan.approval_count
        : approvals.filter(item => String(item.decision || "approve") === "approve").length) || 0,
    requiredApprovals: Number(root.required_approvals != null ? root.required_approvals
      : plan.required_approvals != null ? plan.required_approvals : workflowRepairId(plan, "id", "plan_id") != null ? 2 : 0) || 0,
  };
};
const workflowRepairEnvelopes = source => {
  const root = workflowRepairObject(source && source.data ? source.data : source);
  const list = workflowRepairArray(root.repairs || root.cases || root.items);
  if (list.length) return list.map(item => workflowRepairEnvelope(item)).filter(Boolean);
  const single = workflowRepairEnvelope(root);
  return single ? [single] : [];
};
const workflowRepairText = value => {
  if (value == null || value === "") return "—";
  if (typeof value === "string" || typeof value === "number") return String(value);
  return String(value.label || value.message || value.name || value.code || value.requirement_key || value.evidence_key || "—");
};
const workflowRepairStatusLabel = (status, t) => ({
  detected: t("已偵測"), triaged: t("已分診"), awaiting_input: t("待補件"),
  awaiting_approval: t("待共簽"), ready: t("可套用"), applying: t("套用中"),
  verifying: t("核對中"), retry_wait: t("等待安全重試"), escalated: t("已升級"),
  resolved: t("已修復"), cancelled: t("已取消"), superseded: t("計劃已失效"),
}[String(status || "").toLowerCase()] || workflowRepairText(status));

const RepairPlanCard = ({ repair, onChange, onAsk, compact = false }) => {
  const t = window.W2_LANG.t;
  const [snapshot, setSnapshot] = React.useState(() => workflowRepairEnvelope(repair));
  const [syncState, setSyncState] = React.useState("loading");
  const [busy, setBusy] = React.useState("");
  const [outcomeUncertain, setOutcomeUncertain] = React.useState(false);
  const [error, setError] = React.useState("");
  const applyKeyRef = React.useRef({ planId: null, key: "" });
  const busyRef = React.useRef(false);
  const passkeyOperationRef = React.useRef(null);
  const mountedRef = React.useRef(true);

  React.useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      const operation = passkeyOperationRef.current;
      if (operation && !operation.signal.aborted) operation.abort();
      passkeyOperationRef.current = null;
      busyRef.current = false;
    };
  }, []);

  const publish = React.useCallback(source => {
    const next = workflowRepairEnvelope(source);
    if (!next) throw new Error(t("修復案件回應格式無效，操作已鎖定"));
    setSnapshot(next);
    if (typeof onChange === "function") onChange(next.raw);
    return next;
  }, [onChange]);
  const caseId = snapshot && snapshot.caseId;
  const refresh = React.useCallback(async () => {
    if (caseId == null) throw new Error(t("修復案件識別無效"));
    const response = await W2.json(`/api/wf/repairs/${encodeURIComponent(caseId)}`);
    const next = publish(response);
    setSyncState("ready");
    return next;
  }, [caseId, publish]);

  React.useEffect(() => {
    const next = workflowRepairEnvelope(repair);
    if (next) setSnapshot(next);
  }, [repair]);
  React.useEffect(() => {
    if (caseId == null) { setSyncState("error"); return undefined; }
    let disposed = false;
    setSyncState("loading"); setError("");
    W2.json(`/api/wf/repairs/${encodeURIComponent(caseId)}`).then(response => {
      if (!disposed) { publish(response); setSyncState("ready"); }
    }).catch(exception => {
      if (!disposed) { setSyncState("error"); setError(exception.message || t("無法核對最新修復狀態，操作已鎖定")); }
    });
    return () => { disposed = true; };
  }, [caseId]);
  const caseStatus = String(snapshot && snapshot.repairCase.status || "").toLowerCase();
  React.useEffect(() => {
    if (!caseId || !WORKFLOW_REPAIR_POLLING.has(caseStatus)) return undefined;
    const timer = setTimeout(() => refresh().catch(exception => setError(exception.message || t("暫時無法更新修復狀態"))), 1600);
    return () => clearTimeout(timer);
  }, [caseId, caseStatus, refresh]);
  if (!snapshot) return null;

  const { repairCase, plan, planId, requirements, missingRequirements, evidence,
    approvals, anomalies, safetyInvariants, actions, approvalCount, requiredApprovals } = snapshot;
  const planStatus = String(plan.status || "").toLowerCase();
  const currentGlobalId = Number(window.W2_USER && (
    window.W2_USER.global_user_id || window.W2_USER.global_id || window.W2_USER.gid
  ));
  const alreadySigned = Number.isFinite(currentGlobalId) && approvals.some(item =>
    Number(item.actor_gid != null ? item.actor_gid : item.global_user_id) === currentGlobalId
  );
  const signaturesReady = !!planId && requiredApprovals > 0 && approvalCount >= requiredApprovals;
  const canApprove = syncState === "ready" && !!planId && !alreadySigned
    && approvalCount < requiredApprovals && !missingRequirements.length
    && ["awaiting_approval", "ready"].includes(planStatus);
  const canApply = syncState === "ready" && !!planId && signaturesReady
    && !missingRequirements.length && planStatus === "ready" && !outcomeUncertain;
  const canVerify = syncState === "ready" && !!planId
    && (outcomeUncertain
      || ["applying", "verifying", "resolved", "retry_wait", "escalated"].includes(caseStatus));
  const dueAt = repairCase.due_at || repairCase.sla_due_at || repairCase.next_check_at;
  const owner = repairCase.owner_name || repairCase.owner_username
    || (repairCase.owner_user_id != null ? `#${repairCase.owner_user_id}` : t("待指派"));
  const anomalyRows = anomalies.length ? anomalies : repairCase.anomaly_code ? [repairCase.anomaly_code] : [];
  const planHash = plan.plan_hash || plan.hash;
  const evidenceHash = plan.evidence_set_hash || plan.evidence_hash || repairCase.evidence_set_hash;
  const stateHash = plan.state_fingerprint || plan.before_fingerprint || repairCase.state_fingerprint;

  const nextApplyKey = () => {
    if (applyKeyRef.current.planId === planId && applyKeyRef.current.key) return applyKeyRef.current.key;
    const random = window.crypto && typeof window.crypto.randomUUID === "function"
      ? window.crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    const key = `workflow-repair:${caseId}:${planId}:${random}`;
    applyKeyRef.current = { planId, key };
    return key;
  };
  const mutate = async operation => {
    if (busyRef.current || syncState !== "ready" || !planId) return;
    busyRef.current = true; setBusy(operation); setError("");
    let postStarted = false;
    try {
      let path = `/api/wf/repair-plans/${encodeURIComponent(planId)}/${operation}`;
      let body = {};
      if (operation === "approve") {
        if (!W2.Passkeys || typeof W2.Passkeys.supported !== "function"
          || typeof W2.Passkeys.requestStepUp !== "function" || !W2.Passkeys.supported()) {
          throw new Error(t("第二位共簽必須使用 Passkey；目前裝置或連線不支援，尚未簽署"));
        }
        const operationController = typeof window.AbortController === "function"
          ? new window.AbortController() : null;
        passkeyOperationRef.current = operationController;
        const stepUpToken = await W2.Passkeys.requestStepUp(
          "workflow.repair.approve", { plan_id: Number(planId), decision: "approve" },
          {
            mode: "platform", fallbackToHybrid: true,
            platformTimeoutMs: 30000,
            signal: operationController && operationController.signal,
          },
        );
        if (typeof stepUpToken !== "string" || !stepUpToken.trim()) throw new Error(t("Passkey 未返回有效的一次性授權，尚未簽署"));
        body = { decision: "approve", step_up_token: stepUpToken };
        if (passkeyOperationRef.current === operationController) {
          passkeyOperationRef.current = null;
        }
        if (operationController && !operationController.signal.aborted) {
          operationController.abort();
        }
      } else if (operation === "apply") body = { idempotency_key: nextApplyKey() };
      else if (operation === "verify") body = { reason: "user_requested_verification" };
      postStarted = true;
      const response = await W2.post(path, body);
      publish(response);
      if (operation === "apply" || operation === "verify") setOutcomeUncertain(false);
      setSyncState("ready");
    } catch (exception) {
      let friendly = exception;
      if (!postStarted && W2.Passkeys && typeof W2.Passkeys.friendlyError === "function") {
        try { friendly = W2.Passkeys.friendlyError(exception) || exception; } catch (ignored) {}
      }
      if (postStarted) {
        try { await refresh(); } catch (ignored) {}
      }
      if (operation === "apply"
        && (!exception || !exception.status || Number(exception.status) >= 500)) {
        setOutcomeUncertain(true);
      }
      setError((friendly && friendly.message) || t("修復操作未完成"));
    } finally {
      busyRef.current = false;
      passkeyOperationRef.current = null;
      if (mountedRef.current) setBusy("");
    }
  };
  const askForInput = () => {
    const prompt = `請讀取 Repair Case ${caseId} 的 deterministic evidence 與 missing_requirements；只向我收集服務端明列且我能明確提供的字段，再用 wf repair input set 登記。不得猜供應商、明細、成本中心或審批結論，不得使用 db exec。`;
    if (typeof onAsk === "function") onAsk(prompt); else W2.openSecretary(prompt);
  };
  const askForPlan = () => {
    const prompt = `請先 wf repair show --case ${caseId}，再依 allowed_actions 與證據用 wf repair plan 提出白名單方案。只提案，不得自行 approve/apply/cancel，不得重放任何下游效果。`;
    if (typeof onAsk === "function") onAsk(prompt); else W2.openSecretary(prompt);
  };

  return (
    <section className="workflow-repair-plan-card" data-case-id={caseId} data-plan-id={planId || ""}
      data-status={caseStatus} data-sync-state={syncState}
      style={{ border: "2px solid var(--rule)", borderLeft: "5px solid var(--red)", background: "var(--white)", padding: compact ? 11 : 14, minWidth: 0 }}>
      <div className="row spread g8 wrap" style={{ alignItems: "flex-start" }}>
        <div style={{ minWidth: 0 }}>
          <div className="label" style={{ color: "var(--red)" }}>WORKFLOW · REPAIR CASE #{caseId}</div>
          <div style={{ fontSize: compact ? 14 : 16, fontWeight: 850, marginTop: 5 }}>
            {repairCase.instance_title || repairCase.title || repairCase.instance_no || `${t("流程實例")} #${repairCase.instance_id || "—"}`}
          </div>
        </div>
        <span className="tag">{workflowRepairStatusLabel(caseStatus, t)}</span>
      </div>
      <div className="row g8 wrap" style={{ marginTop: 9, fontSize: 10.5 }}>
        <span><b>{t("風險")}</b> · {repairCase.risk_class || "—"}</span>
        <span><b>OWNER</b> · {owner}</span>
        <span><b>SLA</b> · {dueAt || "—"}</span>
        {repairCase.next_action && <span><b>{t("下一步")}</b> · {workflowRepairText(repairCase.next_action)}</span>}
      </div>
      <div role="note" style={{ marginTop: 10, padding: "8px 10px", border: "1px solid var(--red)", color: "var(--red)", fontSize: 11.2, fontWeight: 750, lineHeight: 1.5 }}>
        {t("安全修復只校正流程控制與正式關聯；禁止重放採購、訂單、入庫、預算、應付或總賬效果。")}
      </div>

      {!!anomalyRows.length && <div style={{ marginTop: 11 }}>
        <div className="label dim">DETERMINISTIC · ANOMALIES</div>
        {anomalyRows.map((item, index) => <div key={item.id || item.code || index} style={{ fontSize: 11.2, lineHeight: 1.55, marginTop: 4 }}>
          <b>{workflowRepairText(item.code || item.anomaly_code || `#${index + 1}`)}</b>{item.message || item.detail ? ` · ${workflowRepairText(item.message || item.detail)}` : ""}
        </div>)}
      </div>}
      {!!evidence.length && <details style={{ marginTop: 10 }}>
        <summary className="label dim" style={{ cursor: "pointer" }}>{t("異常證據")} · {evidence.length}</summary>
        {evidence.map((item, index) => <div key={item.id || item.evidence_key || index} className="row spread g8" style={{ borderBottom: "1px solid var(--hair)", padding: "6px 0", fontSize: 10.5 }}>
          <span>{workflowRepairText(item.evidence_key || item.kind || item.label || `#${index + 1}`)}</span>
          <span className="mono muted" style={{ maxWidth: "55%", overflowWrap: "anywhere", textAlign: "right" }}>{item.sha256 || item.source_ref || item.source_id || "VERIFIED"}</span>
        </div>)}
      </details>}
      <div style={{ marginTop: 11 }}>
        <div className="row spread g8 wrap">
          <div className="label dim">REQUIRED · INPUT</div>
          {!!missingRequirements.length && <button className="btn ghost sm" onClick={askForInput}>{t("由秘書收集明確資料")}</button>}
        </div>
        {missingRequirements.length ? missingRequirements.map((item, index) => <div key={item.id || item.requirement_key || index} style={{ color: "var(--red)", fontSize: 11.2, marginTop: 5 }}>
          ● {workflowRepairText(item.label || item.requirement_key || item)}{item.reason ? ` · ${workflowRepairText(item.reason)}` : ""}
        </div>) : <div style={{ color: "var(--ok)", fontSize: 11.2, marginTop: 5 }}>✓ {t("服務端明列缺件已清零")}</div>}
      </div>

      {planId ? <div style={{ marginTop: 12, paddingTop: 10, borderTop: "2px solid var(--rule)" }}>
        <div className="row spread g8 wrap">
          <div><span className="label">REPAIR PLAN #{planId}</span> · <span className="tag">{workflowRepairStatusLabel(planStatus, t)}</span></div>
          <strong style={{ fontSize: 12 }}>{t("Passkey 共簽")} · {approvalCount}/{requiredApprovals || "—"}</strong>
        </div>
        {!!actions.length && <div className="row g6 wrap" style={{ marginTop: 8 }}>{actions.map((action, index) => (
          <span key={action.kind || index} className="tag">{workflowRepairText(action.kind || action.action_kind || action)}</span>
        ))}</div>}
        <div className="mono muted" style={{ fontSize: 9.2, lineHeight: 1.65, marginTop: 8, overflowWrap: "anywhere" }}>
          {planHash && <div>PLAN HASH · {planHash}</div>}
          {evidenceHash && <div>EVIDENCE SET · {evidenceHash}</div>}
          {stateHash && <div>STATE FINGERPRINT · {stateHash}</div>}
        </div>
        {!!approvals.length && <div style={{ marginTop: 8 }}>{approvals.map((item, index) => <div key={item.id || item.approval_slot || index} className="row spread g8" style={{ fontSize: 10.5, borderTop: "1px solid var(--hair)", padding: "5px 0" }}>
          <span>{t("簽署席位")} {item.approval_slot || index + 1} · {item.actor_name || item.global_username || item.actor_gid || item.global_user_id || "—"}</span>
          <b>{String(item.decision || "approve").toUpperCase()} · PASSKEY</b>
        </div>)}</div>}
      </div> : <div style={{ marginTop: 12, paddingTop: 10, borderTop: "2px solid var(--rule)" }}>
        <button className="btn primary sm" disabled={!!missingRequirements.length || syncState !== "ready"} onClick={askForPlan}>{t("請秘書提出修復計劃")}</button>
      </div>}
      {!!safetyInvariants.length && <details style={{ marginTop: 9 }}>
        <summary className="label dim" style={{ cursor: "pointer" }}>{t("套用前後安全不變式")}</summary>
        {safetyInvariants.map((item, index) => <div key={item.code || index} style={{ fontSize: 10.5, marginTop: 4 }}>✓ {workflowRepairText(item)}</div>)}
      </details>}
      {syncState === "loading" && <div className="step-line" style={{ marginTop: 9 }}><Icon2 name="refresh" size={10}/>{t("正在核對最新修復狀態…")}</div>}
      {error && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, marginTop: 9 }}>{error}</div>}
      {outcomeUncertain && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, fontWeight: 750, marginTop: 9 }}>
        {t("套用回應不確定；已鎖定重試，請只核對正式回執。")}
      </div>}
      <div className="row g6 wrap" style={{ marginTop: 12 }}>
        <button className="btn ghost sm" disabled={!!busy} onClick={() => refresh().catch(exception => setError(exception.message || t("重新核對失敗")))}>{t("重新核對")}</button>
        {!!planId && approvalCount < requiredApprovals && <button className="btn primary sm" disabled={!canApprove || !!busy} onClick={() => mutate("approve")}>
          {busy === "approve" ? t("Passkey 驗證中…") : alreadySigned ? t("本身份已簽署") : t("Passkey 共簽")}
        </button>}
        {!!planId && <button className="btn primary sm" disabled={!canApply || !!busy} onClick={() => mutate("apply")}>
          {busy === "apply" ? t("安全套用中…") : t("套用白名單修復")}
        </button>}
        {!!planId && <button className="btn ghost sm" disabled={!canVerify || !!busy} onClick={() => mutate("verify")}>
          {busy === "verify" ? t("核對中…") : t("核對正式回執")}
        </button>}
        {WORKFLOW_REPAIR_CLOSED.has(caseStatus) && <span className="label dim" style={{ marginLeft: "auto" }}>IMMUTABLE · AUDITED</span>}
      </div>
    </section>
  );
};

/* Secretary download descriptors are tool output, so treat every field as
   untrusted.  Links stay on this origin under /api/; path checks are repeated
   after percent-decoding so encoded dot segments, controls, and backslashes
   cannot be revived by a proxy or backend decoder. */
const SECRETARY_DOWNLOAD_BASE = "https://warehouse.invalid";
const secretaryDecodeDownloadGuards = (value) => value.replace(
  /%(?:25|2e|2f|5c|0[0-9a-f]|1[0-9a-f]|7f)/gi,
  token => String.fromCharCode(Number.parseInt(token.slice(1), 16))
);
const secretaryDownloadEncodingIsSafe = (value) => {
  if (/%(?![0-9a-f]{2})/i.test(value)) return false;
  let decoded = value;
  for (let depth = 0; depth < 4; depth += 1) {
    if (/[\u0000-\u001f\u007f\\]/.test(decoded)) return false;
    const path = decoded.split(/[?#]/, 1)[0];
    if (path.split("/").some(segment => segment === "." || segment === "..")) return false;
    const next = secretaryDecodeDownloadGuards(decoded);
    if (next === decoded) return true;
    decoded = next;
  }
  return false;
};
const secretarySafeApiDownloadUrl = (value) => {
  if (typeof value !== "string" || /[\u0000-\u001f\u007f\\]/.test(value)) return null;
  const raw = value.trim();
  if (!/^\/api\//.test(raw) || !secretaryDownloadEncodingIsSafe(raw)) return null;
  try {
    const parsed = new URL(raw, SECRETARY_DOWNLOAD_BASE);
    if (parsed.origin !== SECRETARY_DOWNLOAD_BASE || !parsed.pathname.startsWith("/api/")) return null;
    return parsed.pathname + parsed.search + parsed.hash;
  } catch (error) { return null; }
};
const secretarySafeDownloadText = (value, limit = 180) => String(value == null ? "" : value)
  .replace(/[\u0000-\u001f\u007f\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "")
  .trim().slice(0, limit);
const secretarySafeDownloadFilename = (value) => {
  const filename = secretarySafeDownloadText(
    String(value == null ? "" : value).split(/[\\/]/).pop()
  );
  return filename === "." || filename === ".." ? "" : filename;
};
const secretarySafeDownloads = (values) => {
  const seen = new Set();
  return (Array.isArray(values) ? values : []).reduce((result, item) => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return result;
    const url = secretarySafeApiDownloadUrl(item.url);
    if (!url || seen.has(url)) return result;
    seen.add(url);
    result.push({
      url,
      filename: secretarySafeDownloadFilename(item.filename),
      label: secretarySafeDownloadText(item.label),
    });
    return result;
  }, []);
};

const secretarySanitizedEvidenceEnvelope = (candidate) => {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  const sourceRunId = Number(candidate.source_run_id);
  const digest = String(candidate.digest || "").trim().toLowerCase();
  const summary = String(candidate.summary || "").trim().slice(0, 1600);
  if (candidate.version !== 1 || candidate.status !== "ready"
      || !Number.isSafeInteger(sourceRunId) || sourceRunId <= 0
      || !/^[0-9a-f]{64}$/.test(digest) || !summary
      || candidate.advisory_only !== true || candidate.authoritative !== false
      || candidate.write_authority !== false || candidate.automatic_submit !== false
      || candidate.filter_status !== "isolated_validated"
      || candidate.continuation_scope !== "read_only_research"
      || candidate.trusted_for_read_continuation !== true) return null;
  const sources = (Array.isArray(candidate.sources) ? candidate.sources : []).reduce((rows, source) => {
    if (!source || typeof source !== "object" || rows.length >= 8) return rows;
    const url = String(source.url || "").trim().slice(0, 2000);
    let parsed = null;
    try { parsed = new URL(url); } catch (e) { return rows; }
    if (!/^https?:$/.test(parsed.protocol)) return rows;
    rows.push({
      url: parsed.href,
      label: String(source.label || source.domain || parsed.hostname || "外部來源").trim().slice(0, 180),
      domain: String(source.domain || parsed.hostname || "").trim().slice(0, 255),
    });
    return rows;
  }, []);
  return {
    version: 1, status: "ready", source_run_id: sourceRunId, digest, summary, sources,
    source_tools: (Array.isArray(candidate.source_tools) ? candidate.source_tools : [])
      .map(value => String(value || "").trim().slice(0, 128)).filter(Boolean).slice(0, 8),
    advisory_only: true, authoritative: false, write_authority: false, automatic_submit: false,
    filter_status: "isolated_validated", continuation_scope: "read_only_research",
    trusted_for_read_continuation: true,
  };
};


/* Runtime/model failures are ordinary turn receipts, never conversation-level
   recovery state.  A taint fence may still carry a sanitized read-only summary;
   expose that summary as evidence without asking the user to clear or replace
   the conversation. */
const secretaryDiagnosticEvidence = (source) => {
  const candidate = source && source.recovery && typeof source.recovery === "object"
    ? source.recovery : source;
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  return secretarySanitizedEvidenceEnvelope(candidate.sanitized_summary);
};

const SecretaryEvidenceCard = ({ evidence, attached = false }) => {
  const t = window.W2_LANG.t;
  if (!evidence) return null;
  return (
    <div className={"secretary-evidence-card" + (attached ? " is-attached" : "")}>
      <Label>{attached ? "SANITIZED CONTEXT · REFERENCE ONLY" : "SANITIZED SUMMARY · REVIEW"}</Label>
      <strong>{t(attached ? "已附加淨化摘要" : "請先審閱淨化摘要")}</strong>
      <span className="secretary-evidence-warning">{t("已通過隔離過濾，可安全用於後續只讀研究；仍不代表事實核驗，也不授權寫入。")}</span>
      <p>{evidence.summary}</p>
      {!!evidence.sources.length && <div className="secretary-evidence-sources">
        {evidence.sources.map((source, index) => <a key={`${source.url}:${index}`} href={source.url}
          target="_blank" rel="noopener noreferrer">{source.label || source.domain}</a>)}
      </div>}
    </div>
  );
};

const BusinessDraftCard = ({ draft, onCancel }) => {
  const t = window.W2_LANG.t;
  const [cancelling, setCancelling] = React.useState(false);
  const [cancelError, setCancelError] = React.useState("");
  if (!draft || draft.active !== true) return null;
  const fields = Array.isArray(draft.fields) ? draft.fields : [];
  const missing = fields.filter(field => field && field.missing === true);
  const version = String(draft.version || "").replace(/^v/i, "") || "—";
  const status = String(draft.status || "active").toUpperCase();
  const cancellable = draft.cancellable === true;
  const updatedAt = draft.updated_at ? new Date(draft.updated_at) : null;
  const updatedLabel = updatedAt && Number.isFinite(updatedAt.getTime())
    ? updatedAt.toLocaleString() : String(draft.updated_at || "—");
  return (
    <article className="business-draft-card" aria-label={`${t("業務草稿")} · ${draft.title}`}>
      <header className="business-draft-head">
        <div className="business-draft-heading">
          <Label red>BUSINESS DRAFT · ACTIVE</Label>
          <strong>{draft.title}</strong>
          {draft.kind && <span className="business-draft-kind">{draft.kind}</span>}
        </div>
        <span className="business-draft-state"><i aria-hidden="true"/>{status}</span>
      </header>
      <div className="business-draft-metrics" aria-label={t("草稿狀態摘要")}>
        <span><small>FIELDS</small><b>{String(fields.length).padStart(2, "0")}</b></span>
        <span className={missing.length ? "has-missing" : ""}><small>MISSING</small><b>{String(missing.length).padStart(2, "0")}</b></span>
        <span><small>STATUS</small><b>{status}</b></span>
        <span><small>VERSION</small><b>V{version}</b></span>
      </div>
      {draft.summary && <p className="business-draft-summary">{draft.summary}</p>}
      <dl className="business-draft-fields">
        {fields.map((field, index) => (
          <div key={field.key || index} className={field.missing ? "is-missing" : "is-captured"}>
            <dt>
              <span>{field.label || field.key || `#${index + 1}`}</span>
              {field.required && <small>REQUIRED</small>}
            </dt>
            <dd>{field.missing ? <em>{t("尚待補齊")}</em>
              : <span>{field.value || "—"}</span>}</dd>
          </div>
        ))}
        {!fields.length && <div className="is-missing business-draft-empty">
          <dt>{t("欄位")}</dt><dd><em>{t("尚未提供草稿欄位")}</em></dd>
        </div>}
      </dl>
      {!!missing.length && <div className="business-draft-missing" role="status">
        <span>MISSING · {String(missing.length).padStart(2, "0")}</span>
        <div>{missing.map(field => <b key={field.key}>{field.label || field.key}</b>)}</div>
      </div>}
      <footer className="business-draft-foot">
        <span>DRAFT · {draft.draft_key}</span>
        <span>UPDATED · {updatedLabel}</span>
      </footer>
      <div className="row g6" style={{ justifyContent: "flex-end", marginTop: 10 }}>
        {!!cancelError && <span className="muted" role="alert" style={{ color: "var(--danger)", marginRight: "auto" }}>{cancelError}</span>}
        {!cancellable && !cancelError && <span className="muted" role="status" style={{ marginRight: "auto" }}>
          {t("此草稿正在執行或等待確認；請先完成或取消相關操作卡")}
        </span>}
        <button className="btn ghost sm" title={!cancellable ? t("目前狀態不可刪除") : ""}
          disabled={cancelling || !cancellable || !draft.draft_id || typeof onCancel !== "function"}
          onClick={async () => {
            setCancelling(true);
            setCancelError("");
            try { await onCancel(draft); }
            catch (error) { setCancelError((error && error.message) || t("刪除草稿失敗")); }
            finally { setCancelling(false); }
          }}>
          <Icon2 name={cancelling ? "refresh" : "trash"} size={12}/>
          {cancelling ? t("刪除中…") : t("刪除草稿")}
        </button>
      </div>
    </article>
  );
};

const SECRETARY_RUNTIME_TERMINAL_STATUSES = new Set([
  "succeeded", "failed", "waiting_confirmation", "requires_user_input",
  "skipped", "stopped",
]);
const secretaryRuntimeActivity = (source) => {
  if (!source || typeof source !== "object" || Array.isArray(source)) return null;
  const activityId = String(source.activity_id || "").trim().slice(0, 180);
  if (!activityId) return null;
  const bounded = (value, limit) => String(value || "").trim().slice(0, limit);
  const activity = {
    activity_id: activityId,
    kind: bounded(source.kind || "runtime", 48),
    phase: bounded(source.phase, 80),
    status: bounded(source.status || "running", 48),
  };
  ["model", "tool_name", "command", "description", "judgment", "result_status"]
    .forEach((key) => {
      const value = bounded(source[key], key === "description" ? 500 : 180);
      if (value) activity[key] = value;
    });
  ["elapsed_ms", "round", "count"].forEach((key) => {
    const value = Number(source[key]);
    if (Number.isFinite(value) && value >= 0) activity[key] = Math.floor(value);
  });
  if (Array.isArray(source.selected_tool_names)) {
    activity.selected_tool_names = source.selected_tool_names
      .map(value => bounded(value, 180)).filter(Boolean).slice(0, 24);
  }
  return activity;
};
const secretaryRuntimeActivities = source => (
  Array.isArray(source) ? source.map(secretaryRuntimeActivity).filter(Boolean) : []
);
const secretaryRuntimePhaseLabel = (activity, t) => {
  if (activity.phase === "secure_credential_delivery") {
    return activity.status === "succeeded"
      ? t("簽發結果已核對，正在送達安全卡")
      : t("密鑰已簽發，AI 正在核對並準備安全卡");
  }
  if (activity.command) return activity.command;
  if (activity.tool_name) return activity.tool_name;
  const labels = {
    route: "理解目標與選擇路由",
    select_tools: "蒸餾可用指令集",
    plan: "形成執行計畫",
    answer_with_context: "整合公司上下文",
    reflect: "核對執行結果",
    capability_selection: "選擇指令集",
    decision: "判斷是否執行",
    execute: "執行指令",
    authorization_keychain: "領取一次性授權 Keychain",
    secure_credential_delivery: "密鑰已簽發，AI 正在核對並準備安全卡",
  };
  if (String(activity.phase || "").startsWith("reflect")) return t("核對執行結果");
  if (String(activity.phase || "").startsWith("continue_select")) return t("補充選擇指令集");
  return t(labels[activity.phase] || activity.phase || "運行處理");
};
const secretaryRuntimeStatusLabel = (status, t) => ({
  running: t("運行中"),
  succeeded: t("已完成"),
  failed: t("失敗"),
  waiting_confirmation: t("待確認"),
  requires_user_input: t("等待補充"),
  skipped: t("未調用"),
  stopped: t("已停止"),
}[status] || t(status || "運行中"));
const secretaryRuntimeElapsed = (value) => {
  const elapsed = Number(value);
  if (!Number.isFinite(elapsed) || elapsed < 0) return "";
  return elapsed < 1000 ? `${Math.round(elapsed)}ms` : `${(elapsed / 1000).toFixed(elapsed < 10000 ? 1 : 0)}s`;
};
const SecretaryRuntimeTrace = ({ trace }) => {
  const t = window.W2_LANG.t;
  const activities = secretaryRuntimeActivities(trace && trace.activities);
  const [expanded, setExpanded] = React.useState(() => !!(trace && trace.running));
  React.useEffect(() => {
    if (trace && trace.running) setExpanded(true);
  }, [trace && trace.running]);
  if (!activities.length) return null;
  const running = !!(trace && trace.running)
    || activities.some(activity => activity.status === "running");
  const commandCount = activities.filter(activity =>
    activity.kind === "capability" && activity.phase === "execute"
  ).length;
  const failed = activities.some(activity => activity.status === "failed");
  return (
    <section className={`secretary-runtime-trace${running ? " is-running" : ""}${failed ? " has-failure" : ""}`}>
      <button type="button" className="secretary-runtime-head" aria-expanded={expanded}
        onClick={() => setExpanded(value => !value)}>
        <span className="secretary-runtime-code">RUN · COMMAND TRACE</span>
        <span className="secretary-runtime-summary">
          {commandCount ? `${commandCount} ${t("個指令")}` : t("推理與路由")}
          <i aria-hidden="true"/>
          {running ? t("運行中") : failed ? t("有失敗") : t("已完成")}
        </span>
        <span className="secretary-runtime-chevron" aria-hidden="true">{expanded ? "−" : "+"}</span>
      </button>
      {expanded && <div className="secretary-runtime-body" role="status" aria-live="polite">
        {activities.map((activity) => {
          const selected = activity.kind === "selection"
            ? activity.selected_tool_names || [] : [];
          return <div className={`secretary-runtime-row status-${activity.status}`}
            key={activity.activity_id}>
            <span className="secretary-runtime-dot" aria-hidden="true"/>
            <div className="secretary-runtime-copy">
              <div className="secretary-runtime-line">
                <strong>{secretaryRuntimePhaseLabel(activity, t)}</strong>
                {activity.model && <span className="secretary-runtime-model">{activity.model}</span>}
              </div>
              {!!selected.length && <div className="secretary-runtime-tools">
                {selected.map(toolName => <code key={toolName}>{toolName}</code>)}
              </div>}
              {activity.description && <span className="secretary-runtime-description">{activity.description}</span>}
            </div>
            <span className="secretary-runtime-state">
              {secretaryRuntimeStatusLabel(activity.status, t)}
              {secretaryRuntimeElapsed(activity.elapsed_ms)
                && <small>{secretaryRuntimeElapsed(activity.elapsed_ms)}</small>}
            </span>
          </div>;
        })}
      </div>}
    </section>
  );
};


const secretaryItemsFromBootstrap = (payload) => {
  const messages = (Array.isArray(payload && payload.messages) ? payload.messages : [])
    .filter(message => message && (message.role === "user" || message.role === "assistant"));
  const confirmationMessageAnchors = new Map();
  messages.forEach((message) => {
    if (!message || message.role !== "assistant") return;
    const metadata = message.metadata && typeof message.metadata === "object"
      ? message.metadata : {};
    (Array.isArray(metadata.confirmation_action_ids) ? metadata.confirmation_action_ids : [])
      .forEach((id) => {
        const key = `command:${id}`;
        if (!confirmationMessageAnchors.has(key)) confirmationMessageAnchors.set(key, message.id);
      });
    if (metadata.confirmation_action_id != null) {
      const key = `command:${metadata.confirmation_action_id}`;
      if (!confirmationMessageAnchors.has(key)) confirmationMessageAnchors.set(key, message.id);
    }
    if (metadata.record_action_id != null) {
      const key = `record_confirmation:${metadata.record_action_id}`;
      if (!confirmationMessageAnchors.has(key)) confirmationMessageAnchors.set(key, message.id);
    }
    if (metadata.record_config_action_id != null) {
      const key = `record_config_confirmation:${metadata.record_config_action_id}`;
      if (!confirmationMessageAnchors.has(key)) confirmationMessageAnchors.set(key, message.id);
    }
  });
  const transcript = messages.reduce((items, message) => {
    const metadata = message.metadata && typeof message.metadata === "object"
      ? message.metadata : {};
    const runtimeActivities = message.role === "assistant"
      ? secretaryRuntimeActivities(metadata.runtime_activities) : [];
    if (runtimeActivities.length) {
      items.push({
        role: "runtime_trace",
        trace_key: `runtime-trace:${metadata.run_id || message.id}`,
        activities: runtimeActivities,
        running: false,
      });
    }
    const outcomeUnknown = message.role === "assistant"
      && Array.isArray(metadata.steps)
      && metadata.steps.some(step => step && step.status === "outcome_unknown");
    items.push({
      role: message.role === "user" ? "u" : "a",
      text: String(message.content || ""),
      message_id: message.id,
      created_at: message.created_at,
      run_id: metadata.run_id || metadata.source_run_id || null,
      metadata,
      outcome_unknown: outcomeUnknown,
    });
    const diagnosticEvidence = message.role === "assistant"
      ? secretaryDiagnosticEvidence(metadata) : null;
    if (diagnosticEvidence) items.push({ role: "evidence", evidence: diagnosticEvidence, attached: false });
    return items;
  }, []);
  const attachedEvidence = secretarySanitizedEvidenceEnvelope(
    payload && payload.sanitized_context
  );
  if (attachedEvidence) transcript.unshift({ role: "evidence", evidence: attachedEvidence, attached: true });
  const cards = [];
  (Array.isArray(payload && payload.confirmation_actions)
    ? payload.confirmation_actions : []).forEach((action) => {
    if (!action || typeof action !== "object") return;
    if (action.kind === "record_create") {
      const anchorKey = `record_confirmation:${action.id || action.action_id || ""}`;
      cards.push({
        role: "record_confirmation",
        confirmation: { id: action.id, action, payload: { action } },
        anchor_message_id: confirmationMessageAnchors.get(anchorKey) || null,
        anchor_run_id: action.source_run_id || action.run_id || null,
      });
      return;
    }
    if (action.kind === "record_config") {
      const anchorKey = `record_config_confirmation:${action.id || action.action_id || ""}`;
      cards.push({
        role: "record_config_confirmation",
        confirmation: { id: action.id, action, payload: { action } },
        anchor_message_id: confirmationMessageAnchors.get(anchorKey) || null,
        anchor_run_id: action.source_run_id || action.run_id || null,
      });
      return;
    }
    const confirmation = operationConfirmationEnvelope(action);
    if (confirmation) cards.push({
      role: "operation_confirmation",
      confirmation,
      anchor_message_id: confirmationMessageAnchors.get(confirmation.action_key) || null,
      anchor_run_id: action.source_run_id || action.run_id || null,
    });
  });
  return mergeSecretaryItems(transcript, [
    ...cards,
    ...secretaryBusinessDraftItems(payload),
  ]);
};

const secretaryHasActiveRecordWorkflow = (payload) => {
  const actions = [
    ...(Array.isArray(payload && payload.pending_actions) ? payload.pending_actions : []),
    ...(Array.isArray(payload && payload.confirmation_actions) ? payload.confirmation_actions : []),
  ];
  return actions.some(action => {
    if (!action || action.kind !== "record_create") return false;
    const status = String(action.status || "pending").trim().toLowerCase();
    return !RECORD_ACTION_TERMINAL_STATUSES.has(status);
  });
};

const secretarySurnameOf = (actor) => {
  if (!actor || typeof actor !== "object") return "";
  const explicitSurname = [
    actor.family_name, actor.surname, actor.last_name,
  ].find(value => typeof value === "string" && value.trim());
  if (explicitSurname) return explicitSurname.trim();

  const displayName = String(
    actor.display_name || actor.name || actor.username || "",
  ).trim();
  if (!displayName) return "";
  const commaSurname = displayName.split(",", 1)[0].trim();
  if (commaSurname && commaSurname !== displayName) return commaSurname;
  if (/^[\u3400-\u9fff]/.test(displayName)) return Array.from(displayName)[0];
  return displayName.split(/\s+/)[0] || displayName;
};

/* ── 秘書塢 ── */
const SecretaryDock = () => {
  const t = window.W2_LANG.t;
  const { useState, useRef, useEffect, useCallback } = React;
  const [open, setOpen] = useState(false);
  const [big, setBig] = useState(false);
  const [items, setItems] = useState([]);
  const [input, setInput] = useState("");
  const [lighthouseDevices, setLighthouseDevices] = useState([]);
  const [lighthouseLoading, setLighthouseLoading] = useState(false);
  const [lighthouseError, setLighthouseError] = useState("");
  const [selectedDeviceId, setSelectedDeviceId] = useState(() => {
    try { return window.localStorage.getItem(`w2.lighthouse.device:${W2.tenant()}`) || ""; }
    catch (e) { return ""; }
  });
  const [runtimeTargetOpen, setRuntimeTargetOpen] = useState(false);
  const [pairingOpen, setPairingOpen] = useState(false);
  const [pairingBusy, setPairingBusy] = useState(false);
  const [pairingChallenge, setPairingChallenge] = useState(null);
  const [busy, setBusy] = useState(false);
  const [upBusy, setUpBusy] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [startingNew, setStartingNew] = useState(false);
  const [freshConversation, setFreshConversation] = useState(false);
  const [restoreReady, setRestoreReady] = useState(false);
  const [restoreError, setRestoreError] = useState("");
  const [sessionState, setSessionState] = useState(null);
  const [credentialGuardActive, setCredentialGuardActive] = useState(false);
  const [reasoningMode, setReasoningMode] = useState(() => {
    const saved = window.localStorage.getItem("w2.secretary.reasoning_mode");
    return saved === "thinking" ? "thinking" : "balanced";
  });
  const [effectiveMode, setEffectiveMode] = useState(reasoningMode);
  const [agentStatus, setAgentStatus] = useState({
    agent: "ai_secretary", status: "ready", label: t("AI 秘書隨時待命"),
  });
  const reasoningModeRef = useRef(reasoningMode);
  const convRef = useRef(null);
  const restoreGenerationRef = useRef(0);
  const restoreAbortRef = useRef(null);
  const identityGenerationRef = useRef(0);
  const streamGenerationRef = useRef(0);
  const streamAbortRef = useRef(null);
  const uploadGenerationRef = useRef(0);
  const uploadAbortRef = useRef(null);
  const startingNewRef = useRef(false);
  const newConversationGenerationRef = useRef(0);
  const newConversationAbortRef = useRef(null);
  const explicitUserTurnGenerationRef = useRef(0);
  const restoreReadyRef = useRef(false);
  const scrollRef = useRef(null);
  const followTailRef = useRef(true);
  const forceTailRef = useRef(false);
  const pendingCredentialRevealRef = useRef("");
  const transientCredentialItemsRef = useRef([]);
  const clearedCredentialDeliveriesRef = useRef(new Set());
  const pendingOperationConfirmationRef = useRef(false);
  const pendingCredentialDeliveriesRef = useRef(new Set());
  const pendingCredentialFetchesRef = useRef(new Map());
  const terminalRefreshActionsRef = useRef(new Set());
  const inputRef = useRef(null);
  const fileRef = useRef(null);
  const sendRef = useRef(null);
  const recordWorkflowRef = useRef({ active: false });
  const businessContextRef = useRef(null);
  const actionContextRef = useRef(null);
  const continuedActionsRef = useRef(new Set());
  const pendingContinuationActionsRef = useRef(new Set());
  const continuationUserTurnRef = useRef(new Map());
  const busyRef = useRef(false);   // send 是 [] 依賴的 useCallback,讀不到 busy 狀態;語音定稿可能在運行中到達,必須用 ref 擋併發流
  const openRef = useRef(false);
  openRef.current = open;

  const refreshLighthouseDevices = useCallback(async () => {
    setLighthouseLoading(true);
    setLighthouseError("");
    try {
      const response = await W2.json("/api/lighthouse/devices");
      const devices = Array.isArray(response && response.devices)
        ? response.devices.filter(device => device && device.status === "active") : [];
      setLighthouseDevices(devices);
      setSelectedDeviceId(current => {
        if (!current || devices.some(device => String(device.id) === String(current))) return current;
        try { window.localStorage.removeItem(`w2.lighthouse.device:${W2.tenant()}`); } catch (e) {}
        return "";
      });
      return devices;
    } catch (error) {
      setLighthouseError(error.message || t("無法載入電腦"));
      return [];
    } finally {
      setLighthouseLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (!open) return undefined;
    let disposed = false;
    const refresh = () => { if (!disposed) refreshLighthouseDevices(); };
    refresh();
    const timer = window.setInterval(refresh, 12000);
    return () => { disposed = true; window.clearInterval(timer); };
  }, [open, refreshLighthouseDevices]);

  const selectLighthouseDevice = (deviceId) => {
    const value = String(deviceId || "");
    setSelectedDeviceId(value);
    setRuntimeTargetOpen(false);
    setPairingOpen(false);
    try {
      const key = `w2.lighthouse.device:${W2.tenant()}`;
      if (value) window.localStorage.setItem(key, value);
      else window.localStorage.removeItem(key);
    } catch (e) {}
  };

  const createLighthousePairing = async () => {
    if (pairingBusy) return;
    setPairingBusy(true);
    setLighthouseError("");
    try {
      const response = await W2.post("/api/lighthouse/pairing-challenges", {
        label: t("我的電腦"),
      });
      if (!response || !response.pairing_code) throw new Error(t("配對碼回應無效"));
      setPairingChallenge(response);
    } catch (error) {
      setLighthouseError(error.message || t("無法建立配對碼"));
    } finally {
      setPairingBusy(false);
    }
  };

  const supersedeInFlightInteraction = useCallback(() => {
    const hadStream = !!(busyRef.current || streamAbortRef.current);
    ++streamGenerationRef.current;
    if (streamAbortRef.current) streamAbortRef.current.abort();
    streamAbortRef.current = null;
    busyRef.current = false;
    setBusy(false);
    if (uploadAbortRef.current) {
      ++uploadGenerationRef.current;
      uploadAbortRef.current.abort();
      uploadAbortRef.current = null;
      setUpBusy(false);
    }
    if (hadStream) {
      setItems(previous => previous.map(item => (
        item && item.role === "step" && item.running
          ? { ...item, running: false, text: item.text + " · " + t("已由新指令接續") }
          : item && item.role === "runtime_trace" && item.running
            ? {
                ...item,
                running: false,
                activities: secretaryRuntimeActivities(item.activities).map(activity =>
                  activity.status === "running"
                    ? { ...activity, status: "stopped" } : activity),
              }
          : item
      )));
    }
  }, [t]);

  const supersedeSecretaryRestore = useCallback(() => {
    ++restoreGenerationRef.current;
    if (restoreAbortRef.current) restoreAbortRef.current.abort();
    restoreAbortRef.current = null;
    setRestoring(false);
  }, []);

  const supersedeNewConversation = useCallback(() => {
    if (!startingNewRef.current && !newConversationAbortRef.current) return;
    ++newConversationGenerationRef.current;
    if (newConversationAbortRef.current) newConversationAbortRef.current.abort();
    newConversationAbortRef.current = null;
    startingNewRef.current = false;
    setStartingNew(false);
  }, []);

  const retainCredentialItems = useCallback((credentialItems) => {
    const safeItems = (Array.isArray(credentialItems) ? credentialItems : []).filter(item => {
      if (!item) return false;
      const deliveryId = String(
        item.credential_delivery && item.credential_delivery.delivery_id
        || item.credential && item.credential.escrow_delivery_id
        || "",
      );
      return !deliveryId || !clearedCredentialDeliveriesRef.current.has(deliveryId);
    });
    if (!safeItems.length) return;
    transientCredentialItemsRef.current = mergeSecretaryItems(
      transientCredentialItemsRef.current,
      safeItems,
    );
    setCredentialGuardActive(true);
    pendingCredentialRevealRef.current = safeItems[safeItems.length - 1].delivery_key;
    setItems(previous => mergeSecretaryItems(previous, safeItems));
  }, []);
  const clearCredentialItems = useCallback((deliveryKey, escrowDeliveryId = "") => {
    if (escrowDeliveryId) {
      clearedCredentialDeliveriesRef.current.add(String(escrowDeliveryId));
      pendingCredentialDeliveriesRef.current.delete(String(escrowDeliveryId));
      pendingCredentialFetchesRef.current.forEach((deliveryIds, actionKey) => {
        deliveryIds.delete(String(escrowDeliveryId));
        if (!deliveryIds.size) pendingCredentialFetchesRef.current.delete(actionKey);
      });
    }
    const shouldKeep = item => {
      if (!item || item.role !== "cred") return true;
      if (deliveryKey && String(item.delivery_key || "") === String(deliveryKey)) return false;
      const deliveryId = String(
        item.credential_delivery && item.credential_delivery.delivery_id
        || item.credential && item.credential.escrow_delivery_id
        || "",
      );
      return !escrowDeliveryId || deliveryId !== String(escrowDeliveryId);
    };
    transientCredentialItemsRef.current = transientCredentialItemsRef.current.filter(shouldKeep);
    setCredentialGuardActive(
      pendingCredentialDeliveriesRef.current.size > 0
      || transientCredentialItemsRef.current.length > 0
    );
    setItems(previous => previous.filter(shouldKeep));
  }, []);

  const restoreSecretarySession = useCallback((conversationId = null) => {
    if (restoreAbortRef.current) restoreAbortRef.current.abort();
    const generation = ++restoreGenerationRef.current;
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    restoreAbortRef.current = controller;
    const previousConversationId = String(convRef.current || "");
    const requestedConversationId = (
      typeof conversationId === "number" || typeof conversationId === "string"
    ) ? String(conversationId).trim().slice(0, 128) : "";
    const bootstrapPath = "/api/assistant/bootstrap?message_limit=80"
      + (requestedConversationId ? "&conversation_id=" + encodeURIComponent(requestedConversationId) : "");
    restoreReadyRef.current = false;
    setRestoreReady(false);
    setRestoring(true);
    setRestoreError("");
    const restore = W2.json(bootstrapPath, { signal: controller && controller.signal })
      .then((payload) => {
        if (generation !== restoreGenerationRef.current) return null;
        const nextConversationId = payload && payload.conversation
          ? payload.conversation.id : null;
        const draftSnapshot = payload && payload.business_draft_snapshot
          && typeof payload.business_draft_snapshot === "object"
          ? payload.business_draft_snapshot : null;
        const authoritativeDraftSnapshot = !!(
          draftSnapshot && draftSnapshot.available === true
          && draftSnapshot.complete === true
          && String(draftSnapshot.conversation_id || "")
            === String(nextConversationId || "")
        );
        const preserveConversationDrafts = !!(
          previousConversationId && nextConversationId != null
          && previousConversationId === String(nextConversationId)
          && !authoritativeDraftSnapshot
        );
        convRef.current = nextConversationId;
        recordWorkflowRef.current.active = secretaryHasActiveRecordWorkflow(payload);
        setSessionState(payload && payload.state ? payload.state : null);
        const restoredItems = mergeSecretaryItems(
          secretaryItemsFromBootstrap(payload),
          transientCredentialItemsRef.current,
        );
        setItems(previous => {
          if (!preserveConversationDrafts) return restoredItems;
          const activeDrafts = previous.filter(item => item && item.role === "business_draft"
            && item.draft && item.draft.active === true);
          return mergeSecretaryItems(restoredItems, activeDrafts);
        });
        setFreshConversation(!!(
          payload && payload.conversation
          && (!Array.isArray(payload.messages) || payload.messages.length === 0)
        ));
        restoreReadyRef.current = true;
        setRestoreReady(true);
        const restoredAtUserTurnGeneration = explicitUserTurnGenerationRef.current;
        (Array.isArray(payload && payload.confirmation_actions)
          ? payload.confirmation_actions : []).forEach((action) => {
          const continuation = action && action.continuation;
          if (!continuation || !action.action_key) return;
          setTimeout(() => window.dispatchEvent(
            new CustomEvent("w2-operation-terminal", {
              detail: {
                action_key: action.action_key,
                status: action.status,
                outcome: action.outcome || null,
                continuation,
                source_user_turn_generation: restoredAtUserTurnGeneration,
                credentials: [],
                credential_deliveries: Array.isArray(action.credential_deliveries)
                  ? action.credential_deliveries : [],
              },
            })
          ), 0);
        });
        return payload;
      })
      .catch((error) => {
        if (generation !== restoreGenerationRef.current) return null;
        if (error && error.name === "AbortError") return null;
        restoreReadyRef.current = false;
        setRestoreReady(false);
        setItems(previous => mergeSecretaryItems(previous, transientCredentialItemsRef.current));
        setFreshConversation(false);
        setRestoreError(error.message || String(error));
        return null;
      })
      .finally(() => {
        if (generation === restoreGenerationRef.current) {
          restoreAbortRef.current = null;
          setRestoring(false);
        }
      });
    return restore;
  }, []);

  const cancelBusinessDraft = useCallback(async (draft) => {
    const conversationId = Number(convRef.current);
    const draftId = Number(draft && draft.draft_id);
    const expectedRevision = Number(draft && draft.version);
    if (!Number.isSafeInteger(conversationId) || conversationId <= 0
        || !Number.isSafeInteger(draftId) || draftId <= 0
        || !Number.isSafeInteger(expectedRevision) || expectedRevision <= 0) {
      throw new Error(t("草稿識別或版本無效，請重新載入會話"));
    }
    let response;
    try {
      response = await W2.post(
        `/api/assistant/business-drafts/${draftId}/cancel`,
        { conversation_id: conversationId, expected_revision: expectedRevision },
      );
    } catch (error) {
      if (!error || Number(error.status) !== 409) throw error;
      const conflictCode = error.data && error.data.code;
      if (conflictCode !== "draft_revision_conflict") {
        throw new Error(
          error.data && (error.data.error || error.data.message)
          || error.message || t("這份草稿目前不可刪除"),
        );
      }
      /* A stale card is only a projection.  Never retry its destructive CAS
         with a guessed revision: reload this exact conversation, require a
         complete authoritative snapshot, then let the user review the live
         version before choosing delete again. */
      const refreshed = await restoreSecretarySession(conversationId);
      if (Number(convRef.current) !== conversationId) {
        return { ok: false, conflict: true, superseded: true };
      }
      const refreshedSnapshot = refreshed && refreshed.business_draft_snapshot;
      const authoritative = !!(
        refreshedSnapshot && refreshedSnapshot.available === true
        && refreshedSnapshot.complete === true
        && Number(refreshedSnapshot.conversation_id) === conversationId
      );
      if (!authoritative) {
        const recoveryError = new Error(t(
          "草稿版本已更新，但無法取得完整最新狀態；請重新載入會話",
        ));
        recoveryError.status = 409;
        recoveryError.data = error.data;
        throw recoveryError;
      }
      const noticeKey = `business-draft-conflict:${draftId}:${expectedRevision}`;
      forceTailRef.current = true;
      setItems(previous => [
        ...previous.filter(item => !item || item.notice_key !== noticeKey),
        {
          role: "step", notice_key: noticeKey, running: false,
          text: t("草稿版本已更新，已重新載入最新內容；請核對後再刪除。"),
        },
      ]);
      return {
        ok: false,
        conflict: true,
        business_draft_snapshot: refreshedSnapshot,
      };
    }
    if (Number(convRef.current) !== conversationId) return response;
    const snapshot = response && response.business_draft_snapshot;
    const snapshotMatches = !!(
      snapshot && snapshot.available === true
      && Number(snapshot.conversation_id) === conversationId
    );
    const authoritative = snapshotMatches && snapshot.complete === true;
    const activeDraftItems = snapshotMatches ? secretaryBusinessDraftItems({
      business_draft_snapshot: snapshot,
    }) : [];
    const terminal = normalizeBusinessDraft(
      response && response.cancelled_draft || draft,
    );
    const cancelledKey = terminal && terminal.draft_key
      ? String(terminal.draft_key) : String(draft.draft_key || "");
    setItems(previous => {
      const withoutCancelled = previous.filter(item =>
        businessDraftKey(item) !== cancelledKey
      );
      if (authoritative) {
        return mergeSecretaryItems(
          withoutCancelled.filter(item => !item || item.role !== "business_draft"),
          activeDraftItems,
        );
      }
      // Exact deletion succeeded even when unrelated drafts exceed the
      // bounded snapshot. Remove that terminal card immediately and merge the
      // partial refresh without treating absence as authoritative.
      return mergeSecretaryItems(withoutCancelled, activeDraftItems);
    });
    return response;
  }, [restoreSecretarySession]);

  useEffect(() => {
    const clearIdentityBoundState = (reload) => {
      ++restoreGenerationRef.current;
      ++identityGenerationRef.current;
      ++streamGenerationRef.current;
      ++uploadGenerationRef.current;
      ++newConversationGenerationRef.current;
      if (restoreAbortRef.current) restoreAbortRef.current.abort();
      restoreAbortRef.current = null;
      if (streamAbortRef.current) streamAbortRef.current.abort();
      streamAbortRef.current = null;
      if (uploadAbortRef.current) uploadAbortRef.current.abort();
      uploadAbortRef.current = null;
      if (newConversationAbortRef.current) newConversationAbortRef.current.abort();
      newConversationAbortRef.current = null;
      if (voiceRef.current) voiceRef.current.shutdown();
      restoreReadyRef.current = false;
      setRestoreReady(false);
      setRestoring(false);
      startingNewRef.current = false;
      setStartingNew(false);
      setRestoreError("");
      busyRef.current = false;
      setBusy(false);
      setUpBusy(false);
      setInput("");
      convRef.current = null;
      recordWorkflowRef.current.active = false;
      businessContextRef.current = null;
      actionContextRef.current = null;
      continuedActionsRef.current.clear();
      pendingContinuationActionsRef.current.clear();
      continuationUserTurnRef.current.clear();
      terminalRefreshActionsRef.current.clear();
      transientCredentialItemsRef.current = [];
      clearedCredentialDeliveriesRef.current.clear();
      pendingCredentialDeliveriesRef.current.clear();
      pendingCredentialFetchesRef.current.clear();
      setCredentialGuardActive(false);
      pendingCredentialRevealRef.current = "";
      followTailRef.current = true;
      forceTailRef.current = false;
      setSessionState(null);
      setItems([]);
      setFreshConversation(false);
      if (reload && openRef.current && W2.token()) restoreSecretarySession();
    };
    const onIdentityChanged = () => clearIdentityBoundState(true);
    const onAuthExpired = () => clearIdentityBoundState(false);
    const onStorage = event => {
      if (event.key === W2.TOKEN_KEY || event.key === W2.TENANT_KEY) onIdentityChanged();
    };
    window.addEventListener("warehouse-user-changed", onIdentityChanged);
    window.addEventListener("w2-auth-expired", onAuthExpired);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("warehouse-user-changed", onIdentityChanged);
      window.removeEventListener("w2-auth-expired", onAuthExpired);
      window.removeEventListener("storage", onStorage);
      ++streamGenerationRef.current;
      ++uploadGenerationRef.current;
      ++restoreGenerationRef.current;
      ++newConversationGenerationRef.current;
      if (restoreAbortRef.current) restoreAbortRef.current.abort();
      restoreAbortRef.current = null;
      if (streamAbortRef.current) streamAbortRef.current.abort();
      streamAbortRef.current = null;
      if (uploadAbortRef.current) uploadAbortRef.current.abort();
      uploadAbortRef.current = null;
      if (newConversationAbortRef.current) newConversationAbortRef.current.abort();
      newConversationAbortRef.current = null;
    };
  }, [restoreSecretarySession]);

  useEffect(() => {
    if (!W2.token()) return undefined;
    restoreSecretarySession();
    return () => {
      if (restoreAbortRef.current) restoreAbortRef.current.abort();
    };
  }, [restoreSecretarySession]);

  /* 語音:定稿直接發給秘書;部分識別灰字上屏(流式體感) */
  const voice = useVoice(
    (text) => { if (sendRef.current) sendRef.current(text); },
    (p) => setInput(p || "")
  );
  const voiceRef = useRef(voice);
  voiceRef.current = voice;

  useEffect(() => {
    const h = (e) => {
      setOpen(true);
      const p = e.detail && e.detail.prompt;
      const displayText = e.detail && e.detail.display_text;
      const intent = e.detail && e.detail.intent;
      const businessContext = secretaryContextOf(e.detail);
      const actionContext = secretaryActionContextOf(e.detail);
      businessContextRef.current = businessContext;
      actionContextRef.current = actionContext;
      if (p) {
        if (sendRef.current) {
          sendRef.current(
            p,
            displayText,
            intent,
            businessContext,
            actionContext ? { action_context: actionContext } : {},
          );
        }
      } else {
        const restored = restoreReadyRef.current
          ? Promise.resolve(null) : restoreSecretarySession();
        restored.finally(() => setTimeout(() => inputRef.current && inputRef.current.focus(), 60));
      }
    };
    window.addEventListener("w2-secretary-open", h);
    return () => window.removeEventListener("w2-secretary-open", h);
  }, [restoreSecretarySession]);
  useEffect(() => {
    const endRecordWorkflow = (event) => {
      recordWorkflowRef.current.active = false;
      const terminalStatus = event && event.detail && event.detail.status;
      setSessionState(previous => previous ? {
        ...previous,
        active_task: { ...(previous.active_task || {}), status: terminalStatus || "completed" },
        pending_actions: [],
      } : previous);
    };
    window.addEventListener("w2-record-created", endRecordWorkflow);
    window.addEventListener("w2-record-workflow-end", endRecordWorkflow);
    window.addEventListener("w2-record-config-committed", endRecordWorkflow);
    window.addEventListener("w2-record-config-rejected", endRecordWorkflow);
    return () => {
      window.removeEventListener("w2-record-created", endRecordWorkflow);
      window.removeEventListener("w2-record-workflow-end", endRecordWorkflow);
      window.removeEventListener("w2-record-config-committed", endRecordWorkflow);
      window.removeEventListener("w2-record-config-rejected", endRecordWorkflow);
    };
  }, []);
  const handleOperationTerminal = useCallback((source) => {
    const detail = source && source.detail && typeof source.detail === "object"
      ? source.detail : source && typeof source === "object" ? source : {};
    const actionKey = typeof detail.action_key === "string" ? detail.action_key : "";
    if (!actionKey) return;
    const terminalStatus = String(detail.status || "").trim().toLowerCase();
    if (actionContextRef.current
        && actionContextRef.current.action_key === actionKey
        && ["completed", "succeeded", "cancelled"].includes(terminalStatus)) {
      actionContextRef.current = null;
    }
    const deliveryCandidates = [
      ...(Array.isArray(detail.credential_deliveries) ? detail.credential_deliveries : []),
      ...(detail.credential_delivery ? [detail.credential_delivery] : []),
    ].map(candidate => secretaryCredentialDeliveryEnvelope(candidate, actionKey)).filter(Boolean);
    if (deliveryCandidates.length) {
      const pendingFetches = pendingCredentialFetchesRef.current.get(actionKey) || new Set();
      deliveryCandidates.forEach((delivery) => {
        pendingCredentialDeliveriesRef.current.add(delivery.delivery_id);
        pendingFetches.add(delivery.delivery_id);
      });
      pendingCredentialFetchesRef.current.set(actionKey, pendingFetches);
      setCredentialGuardActive(true);
    }
    const oneTimeCredentials = Array.isArray(detail.credentials)
      ? detail.credentials.filter(item => item && item.value) : [];
    const pendingFetches = pendingCredentialFetchesRef.current.get(actionKey) || new Set();
    oneTimeCredentials.forEach((credential) => {
      const deliveryId = String(credential.escrow_delivery_id || "");
      if (deliveryId) pendingFetches.delete(deliveryId);
    });
    if (!pendingFetches.size) pendingCredentialFetchesRef.current.delete(actionKey);
    const credentialItems = oneTimeCredentials
      .map((credential, index) => {
        const escrowDeliveryId = String(credential.escrow_delivery_id || "");
        const delivery = deliveryCandidates.find(candidate =>
          escrowDeliveryId && candidate.delivery_id === escrowDeliveryId
        ) || (deliveryCandidates.length === 1 ? deliveryCandidates[0] : null);
        return secretaryCredentialItem(credential, actionKey, index, delivery);
      })
      .filter(Boolean);
    retainCredentialItems(credentialItems);
    if (pendingFetches.size) return;
    const continuation = detail.continuation && typeof detail.continuation === "object"
      ? detail.continuation : null;
    if (!continuation || !continuation.confirmation_action_id) {
      const delivery = detail.continuation_delivery && typeof detail.continuation_delivery === "object"
        ? detail.continuation_delivery : {};
      if (delivery.mode === "server_inline" && !terminalRefreshActionsRef.current.has(actionKey)) {
        terminalRefreshActionsRef.current.add(actionKey);
        const refreshUserTurnGeneration = explicitUserTurnGenerationRef.current;
        setTimeout(() => {
          if (refreshUserTurnGeneration === explicitUserTurnGenerationRef.current
              && !busyRef.current && !startingNewRef.current && W2.token()) restoreSecretarySession();
        }, 80);
      }
      return;
    }
    const sourceUserTurnGeneration = Number(detail.source_user_turn_generation);
    const recordedUserTurnGeneration = continuationUserTurnRef.current.get(actionKey);
    const terminalUserTurnGeneration = Number.isFinite(sourceUserTurnGeneration)
      ? sourceUserTurnGeneration : Number(recordedUserTurnGeneration);
    if (!Number.isFinite(terminalUserTurnGeneration)
        || terminalUserTurnGeneration !== explicitUserTurnGenerationRef.current) {
      continuationUserTurnRef.current.delete(actionKey);
      return;
    }
    if (continuedActionsRef.current.has(actionKey)
        || pendingContinuationActionsRef.current.has(actionKey)) return;
    const continuationUserTurnGeneration = explicitUserTurnGenerationRef.current;
    const continuationConversationId = String(continuation.conversation_id || "");
    const authorizationKeychainId = String(continuation.authorization_keychain_id || "");
    if (!/^[0-9a-f-]{36}$/i.test(authorizationKeychainId)) return;
    if (continuationConversationId && convRef.current != null
        && continuationConversationId !== String(convRef.current)) return;
    pendingContinuationActionsRef.current.add(actionKey);
    const launch = (attempt = 0) => {
      if (continuationUserTurnGeneration !== explicitUserTurnGenerationRef.current
          || !pendingContinuationActionsRef.current.has(actionKey)
          || startingNewRef.current) {
        pendingContinuationActionsRef.current.delete(actionKey);
        continuationUserTurnRef.current.delete(actionKey);
        return;
      }
      if (
        !sendRef.current
        || busyRef.current
      ) {
        if (attempt >= 240) {
          pendingContinuationActionsRef.current.delete(actionKey);
          continuationUserTurnRef.current.delete(actionKey);
          return;
        }
        setTimeout(() => launch(attempt + 1), 250);
        return;
      }
      pendingContinuationActionsRef.current.delete(actionKey);
      continuationUserTurnRef.current.delete(actionKey);
      continuedActionsRef.current.add(actionKey);
      if (continuationConversationId) convRef.current = continuationConversationId;
      sendRef.current(
        continuation.prompt || "請繼續完成原任務的剩餘步驟。",
        continuation.display_text || "繼續完成原任務的剩餘步驟",
        null,
        null,
        {
          resume_confirmation_action_id: continuation.confirmation_action_id,
          authorization_keychain_id: authorizationKeychainId,
          hidden_user_turn: true,
          terminal_event: true,
        },
      );
    };
    setTimeout(() => launch(), 0);
  }, [restoreSecretarySession, retainCredentialItems]);
  useEffect(() => {
    const continueAfterConfirmation = event => handleOperationTerminal(event);
    window.addEventListener("w2-operation-terminal", continueAfterConfirmation);
    // Compatibility with a cached card bundle during rolling deployment.
    window.addEventListener("w2-operation-confirmed", continueAfterConfirmation);
    return () => {
      window.removeEventListener("w2-operation-terminal", continueAfterConfirmation);
      window.removeEventListener("w2-operation-confirmed", continueAfterConfirmation);
    };
  }, [handleOperationTerminal]);
  useEffect(() => {
    if (!open || !scrollRef.current) return undefined;
    const frame = window.requestAnimationFrame(() => {
      const scroller = scrollRef.current;
      if (!scroller) return;
      const deliveryKey = pendingCredentialRevealRef.current;
      if (deliveryKey) {
        const target = Array.from(scroller.querySelectorAll("[data-credential-delivery]"))
          .find(node => node.getAttribute("data-credential-delivery") === deliveryKey);
        pendingCredentialRevealRef.current = "";
        if (target && typeof target.scrollIntoView === "function") {
          target.scrollIntoView({ block: "nearest", behavior: "smooth" });
        }
        followTailRef.current = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight <= 72;
        return;
      }
      if (forceTailRef.current || followTailRef.current) {
        scroller.scrollTop = scroller.scrollHeight;
        followTailRef.current = true;
      }
      forceTailRef.current = false;
    });
    return () => window.cancelAnimationFrame(frame);
  }, [items, open]);

  const rememberOperationAction = useCallback((nextAction) => {
    const confirmation = operationConfirmationEnvelope(nextAction);
    if (!confirmation) return;
    setItems(previous => mergeSecretaryItems(previous, [
      { role: "operation_confirmation", confirmation },
    ]));
  }, []);
  const rememberOperationIntent = useCallback((actionKey) => {
    const key = String(actionKey || "");
    if (key) continuationUserTurnRef.current.set(
      key,
      explicitUserTurnGenerationRef.current,
    );
  }, []);

  const stepLabel = (ev) => {
    let label = ev.title || ev.command || t("執行中…");
    const args = ev && ev.args && typeof ev.args === "object" ? ev.args : {};
    if (args.template) label += " · " + String(args.template);
    return label;
  };

  useEffect(() => {
    pendingOperationConfirmationRef.current = items.some((item) => {
      if (!item || item.role !== "operation_confirmation") return false;
      const confirmation = operationConfirmationEnvelope(item.confirmation || item);
      return !!confirmation
        && String(confirmation.action.status || "pending").trim().toLowerCase() === "pending";
    });
  }, [items]);

  const send = useCallback(async (text, displayText, intent, suppliedBusinessContext, runOptions = {}) => {
    const msg = (text || "").trim();
    if (!msg) return;
    const hiddenUserTurn = runOptions && (
      runOptions.hidden_user_turn === true || runOptions.terminal_event === true
    );
    const strongTextConfirmation = SECRETARY_STRONG_TEXT_CONFIRMATION_RE.test(msg);
    const weakTextConfirmation = SECRETARY_WEAK_TEXT_CONFIRMATION_RE.test(msg);
    const suppliedActionContext = secretaryActionContextOf(runOptions);
    const effectiveActionContext = suppliedActionContext
      || ((strongTextConfirmation || weakTextConfirmation) ? actionContextRef.current : null);
    if (suppliedActionContext) actionContextRef.current = suppliedActionContext;
    else if (!hiddenUserTurn && !strongTextConfirmation && !weakTextConfirmation) {
      actionContextRef.current = null;
    }
    const resurfaceOperationConfirmations = !hiddenUserTurn && (
      strongTextConfirmation
      || (weakTextConfirmation && pendingOperationConfirmationRef.current)
    );
    const explicitUserTurnGeneration = hiddenUserTurn
      ? explicitUserTurnGenerationRef.current : ++explicitUserTurnGenerationRef.current;
    if (!hiddenUserTurn) {
      pendingContinuationActionsRef.current.clear();
      supersedeNewConversation();
    }
    // Restore is an opportunistic projection, never a prerequisite for send.
    // Invalidate it before taking the turn so an older snapshot cannot replace
    // the new user bubble or a newer business draft.
    supersedeSecretaryRestore();
    const identityGeneration = identityGenerationRef.current;
    setRestoreError("");
    const shownText = String(displayText || "").trim() || msg;
    const restoreSubmittedInput = !hiddenUserTurn && !displayText && !intent;
    const recordIntent = intent === "record_create";
    // The newest user message owns the conversational stream.  Abort the old
    // response locally; the server atomically terminalizes its run lease, so
    // it cannot dispatch another tool after the new turn takes ownership.
    if (busyRef.current || streamAbortRef.current || uploadAbortRef.current) {
      supersedeInFlightInteraction();
    }
    if (recordIntent) {
      recordWorkflowRef.current.active = true;
      convRef.current = null;
    }
    const streamGeneration = ++streamGenerationRef.current;
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    streamAbortRef.current = controller;
    const isCurrentStream = () => (
      identityGeneration === identityGenerationRef.current
      && streamGeneration === streamGenerationRef.current
    );
    busyRef.current = true;
    setBusy(true);
    if (!hiddenUserTurn) {
      setInput("");
      forceTailRef.current = true;
      setItems((prev) => [
        ...prev.filter(item => item && item.role !== "send_retry"),
        { role: "u", text: shownText },
      ]);
    }
    const confirmations = [], confirmationSeen = new Set();
    const recordConfigConfirmations = [], recordConfigConfirmationSeen = new Set();
    const operationConfirmations = [], operationConfirmationSeen = new Set();
    let streamBusinessDraftItems = [];
    let confirmationsAppended = false;
    const addConfirmation = (event) => {
      const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
      const action = payload.action && typeof payload.action === "object" ? payload.action
        : event && event.action && typeof event.action === "object" ? event.action : {};
      if (action.kind !== "record_create") return;
      const id = String(action.id || action.action_id || payload.action_id || (event && event.action_id) || "");
      if (!id || confirmationSeen.has(id)) return;
      confirmationSeen.add(id); confirmations.push({ id, action, payload });
    };
    const addRecordConfigConfirmation = (event) => {
      const payload = event && event.payload && typeof event.payload === "object" ? event.payload : {};
      const action = payload.action && typeof payload.action === "object" ? payload.action
        : event && event.action && typeof event.action === "object" ? event.action : {};
      if (action.kind !== "record_config") return;
      const id = String(action.id || action.action_id || payload.action_id || (event && event.action_id) || "");
      if (!id || recordConfigConfirmationSeen.has(id)) return;
      recordConfigConfirmationSeen.add(id); recordConfigConfirmations.push({ id, action, payload });
    };
    const addOperationConfirmation = (event) => {
      const confirmation = operationConfirmationEnvelope(event);
      if (!confirmation) return;
      if (resurfaceOperationConfirmations) forceTailRef.current = true;
      if (operationConfirmationSeen.has(confirmation.action_key)) {
        const existing = operationConfirmations.findIndex(item => item.action_key === confirmation.action_key);
        if (existing >= 0) operationConfirmations[existing] = confirmation;
        return;
      }
      continuationUserTurnRef.current.set(
        confirmation.action_key,
        explicitUserTurnGeneration,
      );
      operationConfirmationSeen.add(confirmation.action_key);
      operationConfirmations.push(confirmation);
    };
    const addBusinessDrafts = (event) => {
      const draftItems = secretaryBusinessDraftItems(event);
      if (!draftItems.length) return;
      streamBusinessDraftItems = mergeSecretaryItems(streamBusinessDraftItems, draftItems);
      setItems(previous => mergeSecretaryItems(previous, draftItems));
    };
    try {
      let finalText = "";
      let assistantDeltaSeen = false;
      let assistantStreamText = "";
      const assistantStreamKey = `assistant-stream:${streamGeneration}`;
      const runtimeTraceKey = `runtime-trace:${streamGeneration}`;
      let finalEvidence = null;
      let finalNeedsVerify = false;
      // 工具結果帶 downloads 標記(如 dm guide 的接入指南)→ 對話裡出下載按鈕;
      // 機制通用:任何工具往 result 塞 downloads/download 都會在這裡浮出
      const dls = [], dlSeen = new Set(), credentialItemsBySignature = new Map();
      let streamCredentialItems = [];
      const addDl = (arr) => secretarySafeDownloads(arr).forEach((download) => {
        if (!dlSeen.has(download.url)) { dlSeen.add(download.url); dls.push(download); }
      });
      const addCredential = (arr, deliverySource = null) => (Array.isArray(arr) ? arr : []).forEach((credential) => {
        if (!credential || !credential.value) return;
        const signature = `${credential.kind || "credential"}:${credential.key_id || ""}:${credential.value}`;
        const existingItem = credentialItemsBySignature.get(signature) || null;
        const rawDeliveries = Array.isArray(deliverySource) ? deliverySource : [
          ...(Array.isArray(deliverySource && deliverySource.credential_deliveries)
            ? deliverySource.credential_deliveries : []),
          ...(deliverySource && deliverySource.credential_delivery
            ? [deliverySource.credential_delivery] : []),
        ];
        const actionKey = String(credential.action_key || "");
        const deliveries = rawDeliveries
          .map(candidate => secretaryCredentialDeliveryEnvelope(
            candidate,
            actionKey || `command:${Number(candidate && candidate.action_id)}`,
          ))
          .filter(Boolean);
        const escrowDeliveryId = String(credential.escrow_delivery_id || "");
        const delivery = deliveries.find(candidate =>
          escrowDeliveryId && candidate.delivery_id === escrowDeliveryId
        ) || (deliveries.length === 1 ? deliveries[0] : null);
        const item = secretaryCredentialItem(
          credential,
          actionKey || (delivery && delivery.action_key) || "",
          credentialItemsBySignature.size,
          delivery,
        );
        if (!item) return;
        if (existingItem) item.delivery_key = existingItem.delivery_key;
        credentialItemsBySignature.set(signature, item);
        streamCredentialItems = mergeSecretaryItems(streamCredentialItems, [item]);
        // Attach at the moment the stream yields the secret. A later network
        // interruption cannot erase a credential that was already delivered.
        retainCredentialItems([item]);
      });
      const agentBody = {
        text: msg,
        conversation_id: convRef.current,
        turn_id: (
          window.crypto && typeof window.crypto.randomUUID === "function"
            ? window.crypto.randomUUID()
            : `turn-${Date.now()}-${Math.random().toString(36).slice(2, 12)}`
        ),
        surface: "secretary",
        context_mode: reasoningModeRef.current,
        ...(effectiveActionContext ? {
          action_context: effectiveActionContext,
        } : {}),
        ...(runOptions && runOptions.resume_confirmation_action_id ? {
          resume_confirmation_action_id: Number(runOptions.resume_confirmation_action_id),
          authorization_keychain_id: String(runOptions.authorization_keychain_id || ""),
          hidden_user_turn: true,
          terminal_event: true,
        } : {}),
      };
      await W2.agentStream(agentBody, (ev) => {
            if (!isCurrentStream()) return;
            addBusinessDrafts(ev);
            if (ev.event === "run_start") {
          convRef.current = ev.conversation_id || convRef.current;
          if (ev.session_state) setSessionState(ev.session_state);
          if (ev.context_mode) setEffectiveMode(ev.context_mode);
          setAgentStatus({
            agent: "ai_secretary",
            status: "coordinating",
            label: t("AI 秘書正在統籌"),
          });
            }
            else if (ev.event === "context_mode") {
          setEffectiveMode(ev.mode || reasoningModeRef.current);
            }
            else if (ev.event === "agent_status") {
          setAgentStatus({
            agent: ev.agent || "ai_secretary",
            status: ev.status || "working",
            label: ev.label || t("AI 秘書正在處理"),
          });
            }
            else if (ev.event === "runtime_activity") {
          const activity = secretaryRuntimeActivity(ev);
          if (!activity) return;
          forceTailRef.current = true;
          setItems(previous => {
            const traceIndex = previous.findIndex(item =>
              item && item.role === "runtime_trace" && item.trace_key === runtimeTraceKey
            );
            if (traceIndex < 0) {
              return [...previous, {
                role: "runtime_trace",
                trace_key: runtimeTraceKey,
                activities: [activity],
                running: true,
              }];
            }
            const next = [...previous];
            const trace = next[traceIndex];
            const activities = secretaryRuntimeActivities(trace.activities);
            const activityIndex = activities.findIndex(candidate =>
              candidate.activity_id === activity.activity_id
            );
            if (activityIndex < 0) activities.push(activity);
            else activities[activityIndex] = { ...activities[activityIndex], ...activity };
            next[traceIndex] = { ...trace, activities, running: true };
            return next;
          });
            }
            else if (ev.event === "assistant_delta") {
          const delta = String(ev.delta || (ev.payload && ev.payload.delta) || "");
          if (!delta) return;
          assistantDeltaSeen = true;
          assistantStreamText += delta;
          setItems(previous => {
            const index = previous.findIndex(
              item => item && item.stream_key === assistantStreamKey
            );
            if (index < 0) return [
              ...previous,
              {
                role: "a", text: assistantStreamText, streaming: true,
                stream_key: assistantStreamKey,
              },
            ];
            const next = [...previous];
            next[index] = {
              ...next[index], text: assistantStreamText, streaming: true,
            };
            return next;
          });
            }
            else if (ev.event === "step_start") setItems((p) => [...p, { role: "step", text: stepLabel(ev), running: true }]);
            else if (ev.event === "step") {
          if (ev.outcome_unknown || ev.needs_verify) finalNeedsVerify = true;
          addDl(ev.downloads);
          addCredential(ev.credentials || (ev.credential ? [ev.credential] : []), ev);
          setItems((p) => {
            const n = [...p];
            for (let i = n.length - 1; i >= 0; i--) if (n[i].role === "step" && n[i].running) {
              const pendingConfirmation =
                ev.status === "confirmation_required" || ev.status === "pending_confirmation";
              const problem = ev.error || ev.preview || t("失敗");
              const outcome = pendingConfirmation
                ? " · ⏳ " + t("待確認")
                : ev.status === "partial"
                  ? " · ⚠ " + t("部分完成")
                  : ev.ok === false ? " · ⚠ " + String(problem) : "";
              n[i] = { ...n[i], running: false, text: n[i].text + outcome };
              break;
            }
            return n;
          });
            }
            else if (ev.event === "confirmation_required" || ev.event === "authorization_completed") { addConfirmation(ev); addRecordConfigConfirmation(ev); addOperationConfirmation(ev); }
            else if (ev.event === "final") {
          addCredential(ev.credentials || (ev.credential ? [ev.credential] : []), ev);
          finalText = ev.message || (ev.payload && ev.payload.message) || "";
          finalNeedsVerify = !!(
            finalNeedsVerify || ev.outcome_unknown || ev.needs_verify
            || (ev.payload && (ev.payload.outcome_unknown || ev.payload.needs_verify))
          );
          finalEvidence = secretaryDiagnosticEvidence(
            ev.recovery || (ev.payload && ev.payload.recovery)
          );
          const finalState = ev.session_state || (ev.payload && ev.payload.session_state);
          if (finalState) setSessionState(finalState);
          addOperationConfirmation(ev);
          const finalCards = Array.isArray(ev.cards) ? ev.cards
            : ev.payload && Array.isArray(ev.payload.cards) ? ev.payload.cards : [];
          finalCards.forEach((c) => {
            if (c && c.card_type === "download") addDl(c.downloads);
            if (c && c.card_type === "credential") addCredential([c.credential], c);
            if (c && c.card_type === "confirmation") { addConfirmation(c); addRecordConfigConfirmation(c); }
            addBusinessDrafts(c);
            addOperationConfirmation(c);
          });
            }
      }, { signal: controller && controller.signal });
      if (!isCurrentStream()) return;
      setItems((p) => {
        const stopped = p.map(item => item && item.role === "step" && item.running
          ? { ...item, running: false, text: item.text + " · " + t("本輪已結束，可繼續交辦") }
          : item && item.role === "runtime_trace" && item.trace_key === runtimeTraceKey
            ? {
                ...item,
                running: false,
                activities: secretaryRuntimeActivities(item.activities).map(activity =>
                  activity.status === "running"
                    ? { ...activity, status: "stopped" } : activity),
              }
            : item).map(item => item && item.stream_key === assistantStreamKey
            ? {
                ...item,
                text: finalText || assistantStreamText || t("(完成,但沒有返回文字)"),
                streaming: false,
                outcome_unknown: finalNeedsVerify,
              }
            : item);
        return mergeSecretaryItems(stopped, [
          ...(!assistantDeltaSeen ? [{
            role: "a",
            text: finalText || t("(完成,但沒有返回文字)"),
            outcome_unknown: finalNeedsVerify,
          }] : []),
          ...(finalEvidence ? [{ role: "evidence", evidence: finalEvidence, attached: false }] : []),
          ...streamBusinessDraftItems,
          ...streamCredentialItems,
          ...confirmations.map((confirmation) => ({ role: "record_confirmation", confirmation })),
          ...recordConfigConfirmations.map((confirmation) => ({ role: "record_config_confirmation", confirmation })),
          ...operationConfirmations.map((confirmation) => ({
            role: "operation_confirmation", confirmation,
            move_to_tail: resurfaceOperationConfirmations,
          })),
          ...(dls.length ? [{ role: "dl", downloads: dls }] : []),
        ]);
      });
      confirmationsAppended = true;
      setAgentStatus({
        agent: "ai_secretary", status: "ready", label: t("AI 秘書隨時待命"),
      });
      window.dispatchEvent(new CustomEvent("w2-agent-complete", {
        detail: { conversation_id: convRef.current },
      }));
      voiceRef.current.speakReply(finalText || "");   // 語音對話模式:回覆自動朗讀,朗讀完自動再聆聽
    } catch (e) {
      if (!isCurrentStream()) return;
      // A failed turn is terminal for this stream only. Release the compose
      // path before any reconciliation request so bootstrap latency can never
      // become a conversation lock.
      streamAbortRef.current = null;
      busyRef.current = false;
      setBusy(false);
      const failedConversationId = convRef.current;
      const resumedActionKey = runOptions && runOptions.resume_confirmation_action_id
        ? `command:${Number(runOptions.resume_confirmation_action_id)}` : "";
      if (resumedActionKey) continuedActionsRef.current.delete(resumedActionKey);
      if (runOptions && runOptions.resume_confirmation_action_id
          && e && Number(e.status) === 409) {
        setTimeout(() => {
          if (isCurrentStream() && !busyRef.current && failedConversationId) {
            restoreSecretarySession(failedConversationId);
          }
        }, 0);
        return;
      }
      if (resumedActionKey && failedConversationId) {
        setTimeout(() => {
          if (isCurrentStream() && !busyRef.current) {
            restoreSecretarySession(failedConversationId);
          }
        }, 800);
      }
      // Error events can carry the newest persisted draft. W2.agentStream
      // raises them before the regular event callback, so merge them here too.
      addBusinessDrafts(e && e.data);
      const streamEvidence = secretaryDiagnosticEvidence(e && e.data);
      setItems((p) => {
        const stopped = p.map(item => item && item.role === "step" && item.running
          ? { ...item, running: false, text: item.text + " · ⚠ " + t("本步已結束，可繼續交辦") }
          : item && item.role === "runtime_trace" && item.trace_key === runtimeTraceKey
            ? {
                ...item,
                running: false,
                activities: secretaryRuntimeActivities(item.activities).map(activity =>
                  activity.status === "running"
                    ? { ...activity, status: "failed" } : activity),
              }
          : item);
        return mergeSecretaryItems(stopped, [
          { role: "a", text: "⚠ " + (e.message || String(e)) },
          ...(streamEvidence ? [{ role: "evidence", evidence: streamEvidence, attached: false }] : []),
          ...streamBusinessDraftItems,
          ...(!confirmationsAppended ? confirmations.map((confirmation) => ({ role: "record_confirmation", confirmation })) : []),
          ...(!confirmationsAppended ? recordConfigConfirmations.map((confirmation) => ({ role: "record_config_confirmation", confirmation })) : []),
          ...(!confirmationsAppended ? operationConfirmations.map((confirmation) => ({
            role: "operation_confirmation", confirmation,
            move_to_tail: resurfaceOperationConfirmations,
          })) : []),
        ]);
      });
      if (restoreSubmittedInput
          && explicitUserTurnGeneration === explicitUserTurnGenerationRef.current) {
        setInput(current => current || msg);
      }
      if (recordIntent && !confirmations.length) window.dispatchEvent(new CustomEvent("w2-record-workflow-end", {
        detail: { status: "initial_error" },
      }));
      setTimeout(() => {
        if (isCurrentStream() && !busyRef.current && failedConversationId) {
          restoreSecretarySession(failedConversationId);
        }
      }, 0);
    } finally {
      if (!isCurrentStream()) return;
      streamAbortRef.current = null;
      busyRef.current = false; setBusy(false);
    }
  }, [supersedeInFlightInteraction, supersedeNewConversation, supersedeSecretaryRestore]);
  const sendToLighthouse = useCallback(async (text) => {
    const msg = String(text || "").trim();
    const deviceId = String(selectedDeviceId || "");
    if (!msg || !deviceId) return;
    if (busyRef.current || streamAbortRef.current || uploadAbortRef.current) {
      supersedeInFlightInteraction();
    }
    supersedeNewConversation();
    supersedeSecretaryRestore();
    const identityGeneration = identityGenerationRef.current;
    const streamGeneration = ++streamGenerationRef.current;
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    streamAbortRef.current = controller;
    const isCurrent = () => identityGeneration === identityGenerationRef.current
      && streamGeneration === streamGenerationRef.current;
    busyRef.current = true;
    setBusy(true);
    setInput("");
    forceTailRef.current = true;
    setItems(previous => [
      ...previous.filter(item => item && item.role !== "send_retry"),
      { role: "u", text: msg },
      { role: "step", text: t("正在把目標交給所選電腦的 Lighthouse"), running: true },
    ]);
    setAgentStatus({
      agent: "lighthouse", status: "coordinating", label: t("Lighthouse 正在接手"),
    });
    let cursor = 0;
    const eventKeys = new Set();
    try {
      const idempotencyKey = window.crypto && typeof window.crypto.randomUUID === "function"
        ? window.crypto.randomUUID() : `lh-${Date.now()}-${Math.random().toString(36).slice(2)}`;
      const created = await W2.json("/api/lighthouse/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
        body: JSON.stringify({
          device_id: deviceId,
          goal: msg,
          conversation_ref: convRef.current == null ? null : String(convRef.current),
          read_only: true,
        }),
        signal: controller && controller.signal,
      });
      if (!isCurrent()) return;
      const remoteRun = created && created.run;
      const runId = remoteRun && remoteRun.id;
      if (!runId) throw new Error(t("Lighthouse Run 回應無效"));
      setItems(previous => previous.map(item => item && item.role === "step" && item.running
        ? { ...item, running: false, text: item.text + (
            created.delivery_state === "sent_unacknowledged"
              ? ` · ${t("已發送，等待電腦確認")}`
              : ` · ${t("電腦離線，等待重連")}`
          ) }
        : item));
      let terminalRun = remoteRun;
      for (let attempt = 0; attempt < 600; attempt += 1) {
        if (controller && controller.signal.aborted) throw new DOMException("Aborted", "AbortError");
        const [eventsResponse, runResponse] = await Promise.all([
          W2.json(`/api/lighthouse/runs/${encodeURIComponent(runId)}/events?after_sequence=${cursor}`, {
            signal: controller && controller.signal,
          }),
          W2.json(`/api/lighthouse/runs/${encodeURIComponent(runId)}`, {
            signal: controller && controller.signal,
          }),
        ]);
        if (!isCurrent()) return;
        const events = Array.isArray(eventsResponse && eventsResponse.events)
          ? eventsResponse.events : [];
        const projected = [];
        events.forEach(event => {
          cursor = Math.max(cursor, Number(event.sequence) || 0);
          const key = String(event.event_id || `${runId}:${event.sequence}`);
          if (eventKeys.has(key)) return;
          eventKeys.add(key);
          const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
          const detail = payload.message || payload.reason || payload.capability
            || payload.presentation && payload.presentation.capability || "";
          projected.push({
            role: "step", running: false,
            text: `${String(event.type || "Lighthouse").replace(/^lighthouse\./, "")}${detail ? ` · ${String(detail).slice(0, 240)}` : ""}`,
          });
        });
        if (projected.length) setItems(previous => [...previous, ...projected]);
        terminalRun = runResponse && runResponse.run ? runResponse.run : terminalRun;
        if (["completed", "failed", "cancelled", "rejected"].includes(String(terminalRun.status))) break;
        await new Promise(resolve => window.setTimeout(resolve, 1000));
      }
      if (!terminalRun || !["completed", "failed", "cancelled", "rejected"].includes(String(terminalRun.status))) {
        throw new Error(t("電腦仍在處理；Run 已保存，可稍後繼續查看"));
      }
      const result = terminalRun.result && typeof terminalRun.result === "object"
        ? terminalRun.result : {};
      const finalText = String(result.message || terminalRun.error || (
        terminalRun.status === "completed" ? t("電腦上的任務已完成") : t("電腦上的任務未完成")
      ));
      setItems(previous => [...previous, { role: "a", text: finalText }]);
      setAgentStatus({
        agent: "lighthouse", status: terminalRun.status,
        label: terminalRun.status === "completed" ? t("Lighthouse 任務已完成") : t("Lighthouse 需要您查看"),
      });
      window.dispatchEvent(new CustomEvent("w2-agent-complete", {
        detail: { lighthouse_run_id: runId, device_id: deviceId },
      }));
      if (voiceRef.current) voiceRef.current.speakReply(finalText);
    } catch (error) {
      if (!isCurrent() || error && error.name === "AbortError") return;
      setItems(previous => previous.map(item => item && item.role === "step" && item.running
        ? { ...item, running: false, text: item.text + ` · ⚠ ${t("已停止")}` }
        : item).concat([{ role: "a", text: `⚠ ${error.message || String(error)}` }]));
      setAgentStatus({ agent: "lighthouse", status: "failed", label: t("Lighthouse 需要您查看") });
    } finally {
      if (!isCurrent()) return;
      streamAbortRef.current = null;
      busyRef.current = false;
      setBusy(false);
    }
  }, [selectedDeviceId, supersedeInFlightInteraction, supersedeNewConversation, supersedeSecretaryRestore, t]);
  sendRef.current = (text, displayText, intent, suppliedBusinessContext, runOptions) => (
    selectedDeviceId && !displayText && !intent
      && !(runOptions && (runOptions.hidden_user_turn || runOptions.terminal_event))
      ? sendToLighthouse(text)
      : send(text, displayText, intent, suppliedBusinessContext, runOptions)
  );
  useEffect(() => {
    reasoningModeRef.current = reasoningMode;
    window.localStorage.setItem(
      "w2.secretary.reasoning_mode", reasoningMode,
    );
  }, [reasoningMode]);
  const submit = () => {
    const text = input;
    if (selectedDeviceId) sendToLighthouse(text);
    else send(text);
  };

  /* 上傳圖片 → /api/agent/vision 通用視覺識別;上傳數據/文本文件 → /api/agent/file 內置引擎嗅探;
     識別結果(suggested_text)直接喂進內核流式會話。輸入框裡已有文字時,當作對這個文件的問題一併帶上 */
  const secretaryImageType = (file) => {
    const declared = String(file && file.type || "").split(";", 1)[0].trim().toLowerCase();
    if (declared) return declared;
    const name = String(file && file.name || "").toLowerCase();
    if (/\.jpe?g$/.test(name)) return "image/jpeg";
    if (/\.png$/.test(name)) return "image/png";
    if (/\.webp$/.test(name)) return "image/webp";
    if (/\.gif$/.test(name)) return "image/gif";
    if (/\.hei[cf]$/.test(name)) return name.endsWith(".heif") ? "image/heif" : "image/heic";
    if (/\.avif$/.test(name)) return "image/avif";
    if (/\.bmp$/.test(name)) return "image/bmp";
    if (/\.tiff?$/.test(name)) return "image/tiff";
    return "";
  };
  const isSecretaryImage = (file) => {
    const declared = secretaryImageType(file);
    if (declared.startsWith("image/")) return true;
    return /\.(?:jpe?g|png|webp|gif|heic|heif|avif|bmp|tiff?)$/i.test(String(file && file.name || ""));
  };
  const secretaryCanvasBlob = (canvas, quality) => new Promise((resolve, reject) => {
    if (!canvas || typeof canvas.toBlob !== "function") {
      reject(new Error(t("此瀏覽器無法轉換圖片,請先另存為 JPEG 或 PNG")));
      return;
    }
    canvas.toBlob((blob) => {
      if (blob && blob.size) resolve(blob);
      else reject(new Error(t("圖片轉換失敗,請先另存為 JPEG 或 PNG")));
    }, "image/jpeg", quality);
  });
  /* OpenAI-compatible vision commonly accepts JPEG/PNG/WebP/GIF, not iPhone
     HEIC/HEIF or AVIF. Convert only unsupported/oversized sources locally so
     the staged attachment and the bytes sent to the model remain identical. */
  const prepareSecretaryImage = async (file) => {
    const type = secretaryImageType(file);
    const passthrough = new Set(["image/jpeg", "image/png", "image/webp"]);
    if (passthrough.has(type) && file.size <= 20 * 1024 * 1024) {
      return { file, name: file.name };
    }
    const convertible = new Set([
      "image/jpeg", "image/png", "image/webp", "image/gif",
      "image/heic", "image/heif", "image/avif", "image/bmp", "image/tiff",
    ]);
    if (!convertible.has(type) || !file.size || file.size > 50 * 1024 * 1024) {
      throw new Error(t("請選擇 50MB 以內的 JPEG、PNG、WebP、GIF、HEIC、AVIF、BMP 或 TIFF 圖片"));
    }
    let source = null, width = 0, height = 0, close = () => {};
    if (typeof window.createImageBitmap === "function") {
      try {
        const bitmap = await window.createImageBitmap(file, { imageOrientation: "from-image" });
        source = bitmap; width = bitmap.width; height = bitmap.height;
        close = () => { if (typeof bitmap.close === "function") bitmap.close(); };
      } catch (e) {
        try {
          const bitmap = await window.createImageBitmap(file);
          source = bitmap; width = bitmap.width; height = bitmap.height;
          close = () => { if (typeof bitmap.close === "function") bitmap.close(); };
        } catch (fallbackError) {}
      }
    }
    if (!source) {
      const url = URL.createObjectURL(file);
      const image = new Image();
      image.decoding = "async";
      try {
        image.src = url;
        if (typeof image.decode === "function") await image.decode();
        else await new Promise((resolve, reject) => {
          image.onload = resolve;
          image.onerror = reject;
        });
        source = image; width = image.naturalWidth; height = image.naturalHeight;
        close = () => URL.revokeObjectURL(url);
      } catch (e) {
        URL.revokeObjectURL(url);
        throw new Error(t("此瀏覽器無法讀取這張圖片,請先另存為 JPEG 或 PNG"));
      }
    }
    try {
      if (!width || !height) throw new Error(t("圖片尺寸無效"));
      const scale = Math.min(1, 4096 / Math.max(width, height), Math.sqrt(12_000_000 / (width * height)));
      let outWidth = Math.max(1, Math.round(width * scale));
      let outHeight = Math.max(1, Math.round(height * scale));
      let smallest = null;
      for (let pass = 0; pass < 4; pass += 1) {
        const canvas = document.createElement("canvas");
        canvas.width = outWidth;
        canvas.height = outHeight;
        const context = canvas.getContext("2d", { alpha: false }) || canvas.getContext("2d");
        if (!context) throw new Error(t("此瀏覽器無法轉換圖片,請先另存為 JPEG 或 PNG"));
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, outWidth, outHeight);
        context.imageSmoothingEnabled = true;
        if ("imageSmoothingQuality" in context) context.imageSmoothingQuality = "high";
        context.drawImage(source, 0, 0, outWidth, outHeight);
        for (const quality of [0.9, 0.78, 0.64]) {
          const blob = await secretaryCanvasBlob(canvas, quality);
          if (!smallest || blob.size < smallest.size) smallest = blob;
          if (blob.size <= 19 * 1024 * 1024) {
            const base = String(file.name || "photo").replace(/\.[^.]+$/, "").slice(0, 72) || "photo";
            const name = `${base}-vision.jpg`;
            const output = typeof File === "function"
              ? new File([blob], name, { type: "image/jpeg", lastModified: Date.now() })
              : blob;
            return { file: output, name };
          }
        }
        outWidth = Math.max(1, Math.round(outWidth * 0.7));
        outHeight = Math.max(1, Math.round(outHeight * 0.7));
      }
      if (!smallest) throw new Error(t("圖片轉換失敗,請先另存為 JPEG 或 PNG"));
      throw new Error(t("圖片轉換後仍超過 20MB,請裁切後重試"));
    } finally {
      close();
    }
  };
  const pickUpload = async (ev) => {
    const f = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!f || upBusy) return;
    ++explicitUserTurnGenerationRef.current;
    pendingContinuationActionsRef.current.clear();
    supersedeNewConversation();
    supersedeSecretaryRestore();
    if (busyRef.current || streamAbortRef.current) supersedeInFlightInteraction();
    const identityGeneration = identityGenerationRef.current;
    const uploadGeneration = ++uploadGenerationRef.current;
    if (uploadAbortRef.current) uploadAbortRef.current.abort();
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    uploadAbortRef.current = controller;
    const isCurrentUpload = () => (
      identityGeneration === identityGenerationRef.current
      && uploadGeneration === uploadGenerationRef.current
    );
    const isImg = isSecretaryImage(f);
    setUpBusy(true);
    const nm = f.name.length > 40 ? f.name.slice(0, 20) + "…" + f.name.slice(-15) : f.name;
    setItems((p) => [...p, { role: "step", text: (isImg ? t("識別圖片中…") : t("解析文件中…")) + " " + nm, running: true }]);
    try {
      const fd = new FormData();
      const prepared = isImg ? await prepareSecretaryImage(f) : { file: f, name: f.name };
      fd.append("file", prepared.file, prepared.name);
      // 聆聽中的灰字部分識別稿不算「對文件的問題」
      const q = (voiceRef.current.listening ? "" : input).replace(/\s*…$/, "").trim();
      if (q) fd.append("question", q);
      const res = await W2.fetch(isImg ? "/api/agent/vision" : "/api/agent/file", {
        method: "POST", body: fd, signal: controller && controller.signal,
      });
      const d = await res.json().catch(() => ({}));
      if (!isCurrentUpload()) return;
      setItems((p) => {
        const n = [...p];
        for (let i = n.length - 1; i >= 0; i--) if (n[i].role === "step" && n[i].running) { n[i] = { ...n[i], running: false }; break; }
        return n;
      });
      if (!res.ok || d.ok === false) {
        throw new Error(d.error || d.warning || d.message || res.statusText || t("識別失敗"));
      }
      if (isImg) {
        const vision = d.vision && typeof d.vision === "object" ? d.vision : {};
        const hasRecognition = !!(
          (typeof vision.summary === "string" && vision.summary.trim())
          || (Array.isArray(vision.details)
            && vision.details.some(item => typeof item === "string" && item.trim()))
        );
        if (d.warning || d.recognition_status !== "completed" || !hasRecognition) {
          throw new Error(d.error || d.warning || t("圖片未完成識別,請檢查視覺 API 配置後重試"));
        }
      }
      if (!d.suggested_text) throw new Error(d.error || d.message || t("識別失敗"));
      setInput("");
      if (sendRef.current) sendRef.current(d.suggested_text);
    } catch (e) {
      if (!isCurrentUpload() || (e && e.name === "AbortError")) return;
      setItems((p) => {
        const n = [...p];
        for (let i = n.length - 1; i >= 0; i--) if (n[i].role === "step" && n[i].running) { n[i] = { ...n[i], running: false }; break; }
        return [...n, { role: "a", text: "⚠ " + (e.message || String(e)) }];
      });
    } finally {
      if (isCurrentUpload()) {
        uploadAbortRef.current = null;
        setUpBusy(false);
      }
    }
  };

  const secretaryActor = sessionState && sessionState.actor && typeof sessionState.actor === "object"
    ? sessionState.actor : (window.W2_USER || {});
  const secretaryActorName = secretarySurnameOf(secretaryActor)
    || secretarySurnameOf(window.W2_USER) || t("使用者");
  const secretaryPendingCount = Array.isArray(sessionState && sessionState.pending_actions)
    ? sessionState.pending_actions.length : 0;
  const secretarySubjects = Array.isArray(sessionState && sessionState.subjects)
    ? sessionState.subjects.slice(0, 2).map(subject => subject && (subject.label || subject.id)).filter(Boolean) : [];
  const secretaryStoredStatus = String(
    sessionState && sessionState.active_task && sessionState.active_task.status || "active"
  ).trim().toLowerCase();
  const secretaryStatusKey = restoreError ? "error" : startingNew ? "starting_new" : restoring ? "restoring" : busy ? "executing"
    : secretaryPendingCount ? "pending" : secretaryStoredStatus;
  const secretaryStatus = ({
    starting_new: { code: "NEW SESSION", label: t("正在開啟新對話"), note: t("長期記憶與學習經驗會保留"), color: "var(--red)" },
    restoring: { code: "RESTORING", label: t("正在恢復記憶"), note: t("正在接續上次工作現場"), color: "var(--ink-4)" },
    executing: {
      code: effectiveMode === "thinking" ? "THINKING" : "BALANCED",
      label: agentStatus.label || t("正在為您處理"),
      note: t("代理狀態與回覆正在即時串流"),
      color: "var(--red)",
    },
    running: {
      code: effectiveMode === "thinking" ? "THINKING" : "BALANCED",
      label: agentStatus.label || t("正在為您處理"),
      note: t("代理狀態與回覆正在即時串流"),
      color: "var(--red)",
    },
    active: { code: "READY", label: t("隨時待命"), note: t("說一句，我就開始"), color: "var(--ink)" },
    completed: { code: "COMPLETED", label: t("任務已完成"), note: t("結果已保存，可以繼續交辦"), color: "var(--ok)" },
    confirmed: { code: "COMPLETED", label: t("任務已完成"), note: t("結果已保存，可以繼續交辦"), color: "var(--ok)" },
    pending: { code: "AWAITING", label: t("等待您的確認"), note: secretaryPendingCount ? `${secretaryPendingCount} ${t("項操作等待確認")}` : t("請查看待確認操作"), color: "var(--red)" },
    waiting_confirmation: { code: "AWAITING", label: t("等待您的確認"), note: t("請查看待確認操作"), color: "var(--red)" },
    partial: { code: "ATTENTION", label: t("任務部分完成"), note: t("請查看尚未完成的步驟"), color: "var(--danger)" },
    step_limit: { code: "ATTENTION", label: t("需要繼續處理"), note: t("已達本輪處理步數上限"), color: "var(--danger)" },
    cancelled: { code: "ATTENTION", label: t("任務已取消"), note: t("可以重新交辦這項工作"), color: "var(--ink-4)" },
    rejected: { code: "ATTENTION", label: t("操作已拒絕"), note: t("被拒絕的操作沒有執行"), color: "var(--danger)" },
    expired: { code: "ATTENTION", label: t("確認已過期"), note: t("請重新提交需要確認的操作"), color: "var(--danger)" },
    failed: { code: "ATTENTION", label: t("需要您查看"), note: t("上一項工作未能完成"), color: "var(--danger)" },
    error: { code: "ATTENTION", label: t("需要您查看"), note: restoreError || t("會話狀態暫時不可用"), color: "var(--danger)" },
    outcome_unknown: { code: "ATTENTION", label: t("結果等待核對"), note: t("請勿重複操作"), color: "var(--danger)" },
  })[secretaryStatusKey] || {
    code: "ATTENTION", label: t("狀態等待核對"), note: t("請重新載入會話狀態"), color: "var(--danger)",
  };
  const secretaryStatusMotion = ["starting_new", "restoring", "executing", "running"].includes(secretaryStatusKey)
    ? "is-moving" : ["pending", "waiting_confirmation"].includes(secretaryStatusKey) ? "is-waiting" : "is-settled";
  const secretaryStatusVisual = ["completed", "confirmed"].includes(secretaryStatusKey)
    ? "is-complete" : secretaryStatusMotion === "is-moving" ? "is-moving"
      : secretaryStatusMotion === "is-waiting" ? "is-waiting"
        : secretaryStatusKey === "active" ? "is-ready" : "is-attention";
  const secretaryStatusDescription = [
    secretaryActorName,
    secretarySubjects.length ? `FOCUS ${secretarySubjects.join(" / ")}` : t("專屬會話已連接"),
    `TASK ${secretaryStatus.code}`,
    secretaryStatus.label,
    secretaryStatus.note,
  ].join(" · ");
  // Business confirmations, credentials, a previous run receipt and restore
  // errors are all independent artifacts; none may disable conversation.
  const secretaryNewConversationBlocked = !!startingNew;
  const startNewSecretaryConversation = async () => {
    if (startingNewRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    const newConversationGeneration = ++newConversationGenerationRef.current;
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    newConversationAbortRef.current = controller;
    ++explicitUserTurnGenerationRef.current;
    pendingContinuationActionsRef.current.clear();
    continuationUserTurnRef.current.clear();
    startingNewRef.current = true;
    setStartingNew(true);
    setRestoreError("");
    supersedeSecretaryRestore();
    supersedeInFlightInteraction();
    convRef.current = null;
    // A draft belongs to one conversation.  Clear the old transcript before
    // creating/restoring the new conversation so active cards cannot be
    // preserved merely because restore is later called with the new id.
    setItems([]);
    setSessionState(null);
    setFreshConversation(false);
    if (voiceRef.current) voiceRef.current.shutdown();
    try {
      const createBody = { title: t("新對話"), channel: "assistant" };
      const created = await W2.post("/api/ai/conversations", createBody, {
        signal: controller && controller.signal,
      });
      if (identityGeneration !== identityGenerationRef.current
          || newConversationGeneration !== newConversationGenerationRef.current) return;
      const conversationId = created && created.conversation && created.conversation.id;
      if (!conversationId) throw new Error(t("無法建立新對話"));
      transientCredentialItemsRef.current = [];
      clearedCredentialDeliveriesRef.current.clear();
      pendingCredentialDeliveriesRef.current.clear();
      pendingCredentialFetchesRef.current.clear();
      setCredentialGuardActive(false);
      pendingCredentialRevealRef.current = "";
      terminalRefreshActionsRef.current.clear();
      continuedActionsRef.current.clear();
      pendingContinuationActionsRef.current.clear();
      followTailRef.current = true;
      forceTailRef.current = true;
      recordWorkflowRef.current.active = false;
      businessContextRef.current = null;
      actionContextRef.current = null;
      const restored = await restoreSecretarySession(conversationId);
      if (restored && identityGeneration === identityGenerationRef.current
          && newConversationGeneration === newConversationGenerationRef.current) {
        setTimeout(() => inputRef.current && inputRef.current.focus(), 60);
      }
    } catch (error) {
      if (identityGeneration === identityGenerationRef.current
          && newConversationGeneration === newConversationGenerationRef.current
          && (!error || error.name !== "AbortError")) {
        setRestoreError(error.message || String(error));
      }
    } finally {
      if (identityGeneration === identityGenerationRef.current
          && newConversationGeneration === newConversationGenerationRef.current) {
        newConversationAbortRef.current = null;
        startingNewRef.current = false;
        setStartingNew(false);
      }
    }
  };
  const selectedLighthouseDevice = lighthouseDevices.find(
    device => String(device && device.id || "") === String(selectedDeviceId || ""),
  ) || null;
  const runtimeTargetLabel = selectedDeviceId
    ? String(selectedLighthouseDevice && selectedLighthouseDevice.label || t("Lighthouse 電腦"))
    : t("Warehouse 雲端");
  const runtimeTargetStatus = selectedDeviceId
    ? selectedLighthouseDevice && selectedLighthouseDevice.online ? t("在線") : t("等待連線")
    : t("雲端就緒");

  if (!open) return (
    <button className="dock-fab" onClick={() => {
      setOpen(true);
      businessContextRef.current = null;
      actionContextRef.current = null;
      const restored = restoreReadyRef.current
        ? Promise.resolve(null) : restoreSecretarySession();
      restored.finally(() =>
        setTimeout(() => inputRef.current && inputRef.current.focus(), 60));
    }}>
      <Icon2 name="sparkle" size={15}/>{t("秘書")}<span className="mono" style={{ fontSize: 9, letterSpacing: ".14em", opacity: .6 }}>AI</span>
    </button>
  );
  return (
    <div className={"dock secretary-dock" + (big ? " big" : "")}>
      <style>{`
        .secretary-dock.big{width:auto}
        .secretary-dock.big>.secretary-command-head,.secretary-dock.big>.dock-scroll,.secretary-dock.big>.dock-compose{width:min(900px,calc(100vw - 56px));box-sizing:border-box}
        .secretary-command-head{border-bottom:2px solid var(--rule);background:var(--white)}
        .secretary-head-main{display:flex;align-items:center;justify-content:space-between;gap:9px;padding:9px 11px}
        .secretary-brand{--secretary-spectrum:linear-gradient(90deg,#df2b1f 0 17%,#ff7a00 17% 33%,#f1cf00 33% 49%,#12a05c 49% 66%,#1685d1 66% 83%,#6947c6 83% 100%);position:relative;display:flex;flex:0 1 780px;align-items:center;gap:10px;min-width:0;padding:6px 11px 8px 7px;overflow:hidden;border:1px solid var(--hair);background:var(--paper)}
        .secretary-brand::before{content:"";position:absolute;right:6px;top:5px;width:5px;height:5px;border-top:1px solid var(--ink-4);border-right:1px solid var(--ink-4);opacity:.55}
        .secretary-brand::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--secretary-spectrum);background-size:100% 100%;opacity:.78}
        .secretary-brand.is-moving::after{background-size:220% 100%;animation:secretary-spectrum-flow 1.65s steps(12,end) infinite;opacity:1}
        .secretary-brand.is-waiting::after{animation:secretary-spectrum-wait 1.8s steps(2,end) infinite}
        .secretary-brand.is-settled::after{animation:secretary-spectrum-arrive .65s steps(10,end) 1 both;transform-origin:left center}
        .secretary-seal{position:relative;width:40px;height:40px;flex:0 0 40px;display:grid;place-items:center;overflow:hidden;background:var(--red);color:var(--on-red);font:800 9px/1 var(--f-mono);letter-spacing:.08em;border:1px solid var(--rule);box-shadow:2px 2px 0 var(--rule)}
        .secretary-seal::after{content:"";position:absolute;left:0;right:0;bottom:0;height:2px;background:var(--secretary-spectrum)}
        .secretary-brand-copy{display:flex;flex:1 1 auto;min-width:0;flex-direction:column;gap:5px}
        .secretary-brand-code{font:750 8px/1 var(--f-mono);letter-spacing:.18em;color:var(--ink-4);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .secretary-brand-title-line{display:flex;align-items:center;gap:10px;min-width:0}
        .secretary-brand-title{flex:0 0 auto;font-size:15px;font-weight:820;letter-spacing:-.025em;line-height:1.1;color:var(--ink)}
        .secretary-inline-status{--secretary-status-color:var(--ink);position:relative;display:flex;flex:1 1 auto;align-items:center;gap:6px;min-width:0;padding-left:11px;overflow:hidden;color:var(--ink)}
        .secretary-inline-divider{position:absolute;left:0;top:0;bottom:0;width:1px;background:var(--rule)}
        .secretary-inline-actor{max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:750 8px/1 var(--f-mono);letter-spacing:.08em;color:var(--ink-3)}
        .secretary-status-glyph{position:relative;width:24px;height:16px;flex:0 0 24px;overflow:hidden;border:1px solid var(--secretary-status-color);background:var(--white);color:var(--secretary-status-color)}
        .secretary-status-glyph::after{content:"";position:absolute;left:2px;right:2px;bottom:1px;height:1px;background:var(--secretary-spectrum);opacity:.72}
        .secretary-status-glyph>i{display:none;position:absolute;bottom:4px;width:2px;background:currentColor}
        .secretary-status-glyph>i:nth-child(1){left:5px}.secretary-status-glyph>i:nth-child(2){left:10px}.secretary-status-glyph>i:nth-child(3){left:15px}
        .secretary-status-glyph.is-moving>i{display:block;height:5px;transform-origin:center bottom;animation:secretary-glyph-run .9s steps(4,end) infinite}
        .secretary-status-glyph.is-moving>i:nth-child(1){height:3px;animation-delay:-.6s}.secretary-status-glyph.is-moving>i:nth-child(2){height:7px;animation-delay:-.3s}
        .secretary-status-glyph.is-waiting>i{display:block;bottom:6px;width:3px;height:3px;animation:secretary-glyph-wait 1.8s steps(2,end) infinite}
        .secretary-status-glyph.is-waiting>i:nth-child(2){opacity:.38;animation:none}
        .secretary-status-glyph.is-complete::before{content:"";position:absolute;left:8px;top:2px;width:4px;height:7px;border:solid currentColor;border-width:0 2px 2px 0;transform:translateY(-1px) rotate(45deg);transform-origin:center;animation:secretary-glyph-complete .65s steps(6,end) 1 both}
        .secretary-status-glyph.is-ready::before{content:"";position:absolute;left:9px;top:4px;width:4px;height:4px;background:currentColor;box-shadow:0 0 0 2px var(--white),0 0 0 3px currentColor}
        .secretary-status-glyph.is-attention::before{content:"!";position:absolute;left:0;right:0;top:1px;text-align:center;font:850 10px/1 var(--f-mono);color:currentColor}
        @keyframes secretary-spectrum-flow{0%{background-position:100% 0}100%{background-position:-120% 0}}
        @keyframes secretary-spectrum-wait{0%,48%{opacity:.84}49%,100%{opacity:.3}}
        @keyframes secretary-spectrum-arrive{0%{transform:scaleX(0);opacity:1}100%{transform:scaleX(1);opacity:.78}}
        @keyframes secretary-glyph-run{0%,100%{transform:scaleY(.3);opacity:.25}50%{transform:scaleY(1);opacity:1}}
        @keyframes secretary-glyph-wait{0%,42%{opacity:1}43%,100%{opacity:.18}}
        @keyframes secretary-glyph-complete{0%{transform:translateY(-1px) rotate(45deg) scale(0);opacity:0}66%{transform:translateY(-1px) rotate(45deg) scale(1.18);opacity:1}100%{transform:translateY(-1px) rotate(45deg) scale(1);opacity:1}}
        @media(prefers-reduced-motion:reduce){.secretary-brand.is-moving::after,.secretary-brand.is-waiting::after,.secretary-brand.is-settled::after,.secretary-status-glyph.is-moving>i,.secretary-status-glyph.is-waiting>i,.secretary-status-glyph.is-complete::before{animation:none}.secretary-brand.is-moving::after{background-size:100% 100%;background-position:0 0}.secretary-brand.is-settled::after{transform:none}}
        .btn.secretary-reasoning-toggle,.btn.secretary-new-conversation{width:32px;height:30px;padding:0}
        .secretary-runtime-target{align-self:stretch;border:1px solid var(--rule);border-left:3px solid var(--accent);background:var(--paper);box-shadow:2px 2px 0 color-mix(in srgb,var(--rule) 22%,transparent)}
        .secretary-runtime-target-head{width:100%;display:grid;grid-template-columns:minmax(0,1fr) auto 20px;align-items:center;gap:8px;padding:9px 10px;border:0;background:transparent;color:var(--ink);text-align:left;cursor:pointer}
        .secretary-runtime-target-head:hover{background:var(--surface-2)}
        .secretary-runtime-target-copy{display:flex;min-width:0;flex-direction:column;gap:4px}
        .secretary-runtime-target-code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:800 8px/1 var(--f-mono);letter-spacing:.15em;color:var(--ink-3)}
        .secretary-runtime-target-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:760 11px/1.2 var(--f-mono);color:var(--ink)}
        .secretary-runtime-target-status{display:flex;align-items:center;gap:5px;white-space:nowrap;font:720 8.5px/1 var(--f-mono);color:var(--ink-3)}
        .secretary-runtime-target-status>i{width:6px;height:6px;border:1px solid currentColor;background:var(--white)}
        .secretary-runtime-target-status.is-online{color:var(--ok)}
        .secretary-runtime-target-status.is-online>i{background:var(--ok);border-color:var(--ok)}
        .secretary-runtime-target-chevron{font:800 14px/1 var(--f-mono);text-align:center}
        .secretary-runtime-target-body{display:flex;flex-direction:column;gap:8px;padding:9px;border-top:1px solid var(--hair)}
        .secretary-runtime-target-options{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:7px}
        .secretary-runtime-target-option{position:relative;display:grid;grid-template-columns:26px minmax(0,1fr) auto;align-items:center;gap:8px;min-height:54px;padding:8px;border:1px solid var(--hair);background:var(--white);color:var(--ink);text-align:left;cursor:pointer}
        .secretary-runtime-target-option:hover{border-color:var(--rule);background:var(--surface-2)}
        .secretary-runtime-target-option.is-selected{border-color:var(--accent);box-shadow:inset 3px 0 0 var(--accent)}
        .secretary-runtime-target-icon{width:26px;height:26px;display:grid;place-items:center;border:1px solid var(--rule);background:var(--paper)}
        .secretary-runtime-target-option-copy{display:flex;min-width:0;flex-direction:column;gap:3px}
        .secretary-runtime-target-option-copy>strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:750 10px/1.2 var(--f-mono)}
        .secretary-runtime-target-option-copy>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9px;line-height:1.3;color:var(--ink-3)}
        .secretary-runtime-target-check{width:15px;height:15px;display:grid;place-items:center;border:1px solid var(--rule);font:850 9px/1 var(--f-mono);color:transparent}
        .secretary-runtime-target-option.is-selected .secretary-runtime-target-check{border-color:var(--accent);background:var(--accent);color:var(--on-red)}
        .secretary-runtime-target-actions{display:flex;align-items:center;justify-content:space-between;gap:7px;flex-wrap:wrap;padding-top:1px}
        .secretary-pairing-panel{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:9px;padding:10px;border:1px solid var(--hair);background:var(--white)}
        .secretary-pairing-copy{min-width:0;display:flex;flex-direction:column;gap:5px}
        .secretary-pairing-copy code{display:block;padding:6px 7px;border:1px solid var(--hair);background:var(--white);overflow:auto;white-space:nowrap;font:700 9px/1.35 var(--f-mono);user-select:all}
        .secretary-pairing-note{font-size:10px;line-height:1.5;color:var(--ink-3)}
        .secretary-device-error{padding:7px 8px;border:1px solid color-mix(in srgb,var(--danger) 45%,var(--hair));background:color-mix(in srgb,var(--danger) 5%,var(--white));color:var(--danger);font-size:10px}
        .btn.secretary-reasoning-toggle{--moon-surface:var(--white);position:relative;overflow:hidden}
        .btn.secretary-reasoning-toggle:hover{--moon-surface:var(--ink)}
        .secretary-mode-moon{position:relative;width:11px;height:11px;display:block;border:1px solid currentColor;border-radius:50%;background:currentColor}
        .secretary-reasoning-toggle.is-balanced .secretary-mode-moon::after{content:"";position:absolute;width:10px;height:10px;left:3px;top:-2px;border-radius:50%;background:var(--moon-surface)}
        .btn.secretary-new-conversation{font:750 9px/1 var(--f-mono);letter-spacing:.06em;white-space:nowrap}
        .secretary-new-label{display:none}
        .secretary-evidence-card{display:flex;width:100%;flex-direction:column;gap:7px;padding:11px 12px;border:1px solid var(--rule);background:var(--paper)}
        .secretary-evidence-card.is-attached{align-self:flex-start;max-width:min(520px,94%);border-left:4px solid var(--accent)}
        .secretary-evidence-card>strong{font-size:12.5px;line-height:1.4}
        .secretary-evidence-card>p{margin:0;white-space:pre-wrap;font-size:12px;line-height:1.7;color:var(--ink-2)}
        .secretary-evidence-warning{font-size:10.5px!important;color:var(--danger)!important;font-weight:650}
        .secretary-evidence-sources{display:flex;flex-wrap:wrap;gap:5px}
        .secretary-evidence-sources a{max-width:100%;padding:4px 7px;border:1px solid var(--rule);color:var(--ink-2);font-size:10px;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .secretary-evidence-sources a:hover{border-color:var(--accent);color:var(--accent)}
        .secretary-runtime-trace{align-self:stretch;border:1px solid var(--rule);background:var(--paper);box-shadow:2px 2px 0 color-mix(in srgb,var(--rule) 22%,transparent)}
        .secretary-runtime-trace.is-running{border-left:3px solid var(--accent)}
        .secretary-runtime-trace.has-failure:not(.is-running){border-left:3px solid var(--danger)}
        .secretary-runtime-head{width:100%;display:grid;grid-template-columns:minmax(0,1fr) auto 20px;align-items:center;gap:8px;padding:8px 9px;border:0;background:transparent;color:var(--ink);text-align:left;cursor:pointer}
        .secretary-runtime-head:hover{background:var(--surface-2)}
        .secretary-runtime-code{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:800 8px/1 var(--f-mono);letter-spacing:.15em;color:var(--ink-3)}
        .secretary-runtime-summary{display:flex;align-items:center;gap:6px;white-space:nowrap;font:700 9px/1 var(--f-mono);color:var(--ink-3)}
        .secretary-runtime-summary>i{width:3px;height:3px;border-radius:50%;background:currentColor;opacity:.55}
        .secretary-runtime-chevron{font:800 14px/1 var(--f-mono);text-align:center}
        .secretary-runtime-body{border-top:1px solid var(--hair)}
        .secretary-runtime-row{display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:8px;align-items:start;padding:8px 9px;border-top:1px solid var(--hair)}
        .secretary-runtime-row:first-child{border-top:0}
        .secretary-runtime-dot{width:6px;height:6px;margin-top:4px;border:1px solid var(--ink-4);background:var(--white)}
        .secretary-runtime-row.status-running .secretary-runtime-dot{background:var(--accent);border-color:var(--accent);animation:secretary-runtime-pulse 1.1s steps(2,end) infinite}
        .secretary-runtime-row.status-succeeded .secretary-runtime-dot{background:var(--ok);border-color:var(--ok)}
        .secretary-runtime-row.status-failed .secretary-runtime-dot{background:var(--danger);border-color:var(--danger)}
        .secretary-runtime-row.status-waiting_confirmation .secretary-runtime-dot,.secretary-runtime-row.status-requires_user_input .secretary-runtime-dot{background:#d79500;border-color:#d79500}
        .secretary-runtime-row.status-skipped .secretary-runtime-dot,.secretary-runtime-row.status-stopped .secretary-runtime-dot{background:var(--ink-4);border-color:var(--ink-4)}
        .secretary-runtime-copy{min-width:0}
        .secretary-runtime-line{display:flex;align-items:baseline;gap:7px;min-width:0}
        .secretary-runtime-line>strong{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:750 10.5px/1.3 var(--f-mono)}
        .secretary-runtime-model{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font:600 8px/1 var(--f-mono);color:var(--ink-4)}
        .secretary-runtime-description{display:block;margin-top:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:9.5px;line-height:1.35;color:var(--ink-3)}
        .secretary-runtime-tools{display:flex;flex-wrap:wrap;gap:3px;margin-top:5px}
        .secretary-runtime-tools>code{padding:2px 4px;border:1px solid var(--hair);background:var(--white);font:650 8.5px/1.2 var(--f-mono);color:var(--ink-2)}
        .secretary-runtime-state{display:flex;align-items:flex-end;gap:3px;white-space:nowrap;font:750 8.5px/1.2 var(--f-mono);color:var(--ink-3)}
        .secretary-runtime-state>small{font:600 7.5px/1 var(--f-mono);color:var(--ink-4)}
        @keyframes secretary-runtime-pulse{0%,48%{opacity:1}49%,100%{opacity:.25}}
        @media(prefers-reduced-motion:reduce){.secretary-runtime-row.status-running .secretary-runtime-dot{animation:none}}
        .secretary-dock .dock-scroll{height:585px;flex-basis:585px}
        .secretary-dock.big .dock-scroll{height:min(78vh,960px);flex-basis:min(78vh,960px)}
        .secretary-compose-input{font-size:13.5px}
        @media(max-width:768px){.secretary-compose-input{font-size:16px!important}.secretary-dock .dock-scroll{height:48vh;height:48dvh;flex-basis:48vh;flex-basis:48dvh;max-height:400px}.secretary-dock.big .dock-scroll{height:54vh;height:54dvh;flex-basis:54vh;flex-basis:54dvh;max-height:480px}}
        @media(max-width:520px){.secretary-head-main{gap:7px;padding:8px}.secretary-brand{gap:8px;padding:5px 8px 7px 5px}.secretary-seal{width:36px;height:36px;flex-basis:36px;box-shadow:1px 1px 0 var(--rule)}.secretary-brand-title-line{gap:7px}.secretary-brand-title{font-size:14px}.secretary-inline-status{gap:4px;padding-left:7px}.secretary-inline-actor{max-width:68px;font-size:7.5px}.secretary-runtime-target-options{grid-template-columns:1fr}.secretary-pairing-panel{grid-template-columns:1fr}}
        @media(max-width:390px){.secretary-brand-code{font-size:7px;letter-spacing:.12em}.secretary-brand-title-line{display:block}.secretary-inline-status{margin-top:5px;padding-left:0}.secretary-inline-divider{display:none}.secretary-inline-actor{max-width:72px}}
      `}</style>
      <div className="secretary-command-head">
        <div className="dock-head secretary-head-main">
          <div className={`secretary-brand ${secretaryStatusMotion}`}>
            <div className="secretary-seal" aria-hidden="true">S/01</div>
            <div className="secretary-brand-copy">
              <span className="secretary-brand-code">SECRETARY · PERSONAL DESK</span>
              <div className="secretary-brand-title-line">
                <span className="secretary-brand-title">{t("公司秘書")}</span>
                <div className={`secretary-inline-status ${secretaryStatusVisual}`} role="status"
                  aria-live="polite" aria-atomic="true" aria-label={secretaryStatusDescription} title={secretaryStatusDescription}
                  style={{ "--secretary-status-color": secretaryStatus.color }}>
                  <span className="secretary-inline-divider" aria-hidden="true"/>
                  <strong className="secretary-inline-actor">{secretaryActorName}</strong>
                  <span className={`secretary-status-glyph ${secretaryStatusVisual}`} aria-hidden="true"><i/><i/><i/></span>
                </div>
              </div>
            </div>
          </div>
          <div className="row g4">
            <button className={`btn ghost sm secretary-reasoning-toggle ${
                reasoningMode === "thinking" ? "is-thinking" : "is-balanced"
              }`}
              aria-pressed={reasoningMode === "thinking"}
              aria-label={reasoningMode === "thinking"
                ? t("Thinking 深度分析模式；點擊切換為均衡模式")
                : t("均衡模式；點擊切換為 Thinking 深度分析模式")}
              title={reasoningMode === "thinking"
                ? t("滿月 · Thinking 深度分析模式")
                : t("新月 · 均衡模式")}
              onClick={() => setReasoningMode(mode => {
                const nextMode = mode === "thinking" ? "balanced" : "thinking";
                reasoningModeRef.current = nextMode;
                setEffectiveMode(nextMode);
                return nextMode;
              })}>
              <span className="secretary-mode-moon" aria-hidden="true"/>
            </button>
            <button className="btn ghost sm secretary-new-conversation" aria-label={t("開啟新對話")}
              title={t("開啟空白對話；目前運行、待確認操作與憑證不會阻止切換，審計記錄仍會保留")}
              disabled={secretaryNewConversationBlocked} onClick={() => startNewSecretaryConversation()}>
              <span aria-hidden="true">＋</span><span className="secretary-new-label">{t("新對話")}</span>
            </button>
            <button className="btn ghost sm" style={{ padding: "0 7px", fontFamily: "var(--f-mono)", fontSize: 12 }} title={big ? "縮小" : "放大"} onClick={() => setBig(v => !v)}>{big ? "⤡" : "⤢"}</button>
            <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={() => { voice.shutdown(); businessContextRef.current = null; actionContextRef.current = null; setOpen(false); }}><Icon2 name="x" size={13}/></button>
          </div>
        </div>
      </div>
      <div ref={scrollRef} className="col g10 dock-scroll"
        onScroll={() => {
          const scroller = scrollRef.current;
          if (!scroller) return;
          followTailRef.current = scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight <= 72;
        }}
        style={{ padding: 16, overflowY: "auto" }}>
        <section className={`secretary-runtime-target${runtimeTargetOpen ? " is-open" : ""}`}
          data-auto-runtime-card="execution-target" aria-label={t("Auto Runtime 執行位置卡片")}>
          <button type="button" className="secretary-runtime-target-head"
            aria-expanded={runtimeTargetOpen} onClick={() => setRuntimeTargetOpen(value => !value)}>
            <span className="secretary-runtime-target-copy">
              <span className="secretary-runtime-target-code">AUTO RUNTIME · EXECUTION ROUTE</span>
              <strong className="secretary-runtime-target-name">{runtimeTargetLabel}</strong>
            </span>
            <span className={`secretary-runtime-target-status ${
                !selectedDeviceId || selectedLighthouseDevice && selectedLighthouseDevice.online ? "is-online" : ""
              }`}><i aria-hidden="true"/>{runtimeTargetStatus}</span>
            <span className="secretary-runtime-target-chevron" aria-hidden="true">{runtimeTargetOpen ? "−" : "+"}</span>
          </button>
          {runtimeTargetOpen && <div className="secretary-runtime-target-body">
            <div className="secretary-runtime-target-options" role="group" aria-label={t("選擇執行位置")}>
              <button type="button" className={`secretary-runtime-target-option${!selectedDeviceId ? " is-selected" : ""}`}
                aria-pressed={!selectedDeviceId} onClick={() => selectLighthouseDevice("")}>
                <span className="secretary-runtime-target-icon" aria-hidden="true"><Icon2 name="sparkle" size={13}/></span>
                <span className="secretary-runtime-target-option-copy">
                  <strong>{t("Warehouse 雲端")}</strong>
                  <span>{t("由雲端 Auto Runtime 安全處理")}</span>
                </span>
                <span className="secretary-runtime-target-check" aria-hidden="true">✓</span>
              </button>
              {lighthouseDevices.map(device => {
                const selected = String(device.id) === String(selectedDeviceId);
                return <button type="button" key={device.id}
                  className={`secretary-runtime-target-option${selected ? " is-selected" : ""}`}
                  aria-pressed={selected} onClick={() => selectLighthouseDevice(device.id)}>
                  <span className="secretary-runtime-target-icon" aria-hidden="true"><Icon2 name="cpu" size={13}/></span>
                  <span className="secretary-runtime-target-option-copy">
                    <strong>{device.label}</strong>
                    <span>{device.online ? t("在線 · 可立即接手") : t("離線 · 上線後接手")}</span>
                  </span>
                  <span className="secretary-runtime-target-check" aria-hidden="true">✓</span>
                </button>;
              })}
            </div>
            {lighthouseLoading && <div className="step-line"><Icon2 name="refresh" size={10}/>{t("正在載入電腦…")}</div>}
            {!lighthouseLoading && !lighthouseDevices.length && !lighthouseError && (
              <div className="secretary-pairing-note">{t("尚未連接本機；您仍可使用 Warehouse 雲端。")}</div>
            )}
            {!!lighthouseError && <div className="secretary-device-error" role="alert">{lighthouseError}</div>}
            <div className="secretary-runtime-target-actions">
              <button type="button" className="btn ghost sm" disabled={lighthouseLoading}
                onClick={refreshLighthouseDevices}><Icon2 name="refresh" size={11}/>{t("重新整理")}</button>
              <button type="button" className="btn sm" onClick={() => {
                setPairingOpen(value => !value);
                if (!pairingOpen && !pairingChallenge) createLighthousePairing();
              }}><Icon2 name="cpu" size={11}/>{pairingOpen ? t("收起配對") : t("連接新電腦")}</button>
            </div>
            {pairingOpen && <div className="secretary-pairing-panel">
              <div className="secretary-pairing-copy">
                <strong>{t("把 Lighthouse 連到這個帳號")}</strong>
                {pairingChallenge ? <>
                  <span className="secretary-pairing-note">{t("在電腦終端執行；配對碼十分鐘後失效且只能使用一次。")}</span>
                  <code>{`lh cloud-pair --warehouse-url ${location.origin} --code ${pairingChallenge.pairing_code} --label "My computer"`}</code>
                </> : <span className="secretary-pairing-note">{pairingBusy ? t("正在建立一次性配對碼…") : t("尚未建立配對碼")}</span>}
              </div>
              <div className="row g4" style={{ alignItems: "flex-start" }}>
                <button type="button" className="btn sm" disabled={pairingBusy} onClick={createLighthousePairing}>
                  <Icon2 name="refresh" size={11}/>{pairingChallenge ? t("換一個碼") : t("建立配對碼")}
                </button>
                <button type="button" className="btn ghost sm" onClick={() => {
                  setPairingOpen(false); refreshLighthouseDevices();
                }}>{t("完成")}</button>
              </div>
            </div>}
          </div>}
        </section>
        {restoring && !items.length && (
          <div className="step-line"><Icon2 name="refresh" size={10}/>{t("正在恢復上次會話…")}</div>
        )}
        {!!restoreError && (
          <div className="col g6" role="alert" style={{ alignItems: "flex-start" }}>
            <div className="step-line">⚠ {restoreError}</div>
            <button className="btn ghost sm" disabled={restoring} onClick={restoreSecretarySession}>{t("重新載入會話")}</button>
          </div>
        )}
        {!restoring && !restoreError && !items.length && (
          <div className="col g10" style={{ margin: "auto 0", alignItems: "center" }}>
            {freshConversation && <div className="step-line"><Icon2 name="check" size={10}/>{t("新對話已建立 · 長期記憶仍連接")}</div>}
            <Label dim>SAY IT · I RUN IT · AUDITED</Label>
            <div style={{ fontSize: 13, fontWeight: 650 }}>{t("吩咐一句,我來執行")}</div>
            <div className="muted" style={{ fontSize: 11.5, textAlign: "center", lineHeight: 1.8 }}>{t("「出庫 2 雙絕緣手套給檢修一班」")}<br/>{t("「今天有什麼要處理的?」·「幫低庫存物資補貨」")}</div>
          </div>
        )}
        {items.map((m, i) =>
          m.role === "u" ? <div key={i} className="bubble-u">{m.text}</div>
          : m.role === "step" ? <div key={i} className="step-line"><Icon2 name={m.running ? "refresh" : "check"} size={10} color={m.running ? "var(--ink-4)" : "var(--ok)"}/>{m.text}</div>
          : m.role === "runtime_trace" ? <SecretaryRuntimeTrace key={m.trace_key || i} trace={m}/>
          : m.role === "cred" ? <CredentialBubble key={m.delivery_key || i} credential={m.credential}
              deliveryKey={m.delivery_key} credentialDelivery={m.credential_delivery} onClear={clearCredentialItems}/>
          : m.role === "record_confirmation" ? <RecordCreateConfirmation key={m.confirmation.id || i} confirmation={m.confirmation}/>
          : m.role === "record_config_confirmation" ? <RecordConfigConfirmation key={m.confirmation.id || i} confirmation={m.confirmation}/>
          : m.role === "operation_confirmation" ? <OperationConfirmation key={m.confirmation.action_key || i}
              confirmation={m.confirmation} onActionChange={rememberOperationAction}
              onMutationStart={rememberOperationIntent} onTerminal={handleOperationTerminal}/>
          : m.role === "business_draft" ? <BusinessDraftCard key={m.draft.draft_key || i}
              draft={m.draft} onCancel={cancelBusinessDraft}/>
          : m.role === "evidence" ? <SecretaryEvidenceCard key={i} evidence={m.evidence} attached={m.attached !== false}/>
          : m.role === "a" && m.streaming ? (
              <div key={m.stream_key || i} className="bubble-a" aria-live="polite">
                {m.text}<span className="secretary-stream-cursor" aria-hidden="true">▍</span>
              </div>
            )
          : m.role === "dl" ? (
              <div key={i} className="row g6 wrap" style={{ alignSelf: "flex-start", paddingLeft: 15 }}>
                {secretarySafeDownloads(m.downloads).map((d) => (
                  <a key={d.url} className="btn sm" style={{ textDecoration: "none" }}
                    href={d.url} download={d.filename || true} target="_blank" rel="noopener noreferrer">
                    <Icon2 name="inbound" size={12}/>{d.label || d.filename || t("下載")}
                  </a>
                ))}
              </div>
            )
          : <MdBubble key={i} text={m.text}/>
        )}
        {busy && <div className="step-line" role="status" aria-live="polite">
          <Icon2 name="refresh" size={10}/>
          {agentStatus.label || t("秘書工作中…")} · {
            effectiveMode === "thinking" ? "Thinking" : t("均衡模式")
          }
        </div>}
      </div>
      <div className="dock-compose" style={{ padding: "12px 14px 14px", borderTop: "1px solid var(--hair)" }}>
        <div className="row g6">
          <input ref={fileRef} type="file" style={{ display: "none" }} onChange={pickUpload}
            accept="image/*,.heic,.heif,.avif,.bmp,.tif,.tiff,.xlsx,.xls,.csv,.json,.db,.sqlite,.sqlite3,.txt,.md,.log,.sql,.tsv,.yaml,.yml,.xml,.html"/>
          <button className="btn ghost" style={{ width: 34, height: 38, padding: 0, flexShrink: 0 }}
            title={t("上傳圖片或文件:圖片走視覺識別,Excel/CSV/JSON/SQLite/文本走內置引擎解析")}
            disabled={upBusy} onClick={() => fileRef.current && fileRef.current.click()}>
            <Icon2 name={upBusy ? "refresh" : "doc"} size={15}/>
          </button>
          <button className="btn ghost" style={{ width: 34, height: 38, padding: 0, flexShrink: 0,
              ...(voice.listening ? { background: "var(--red)", color: "var(--on-red)" } : {}) }}
            title={t("點擊說話,再點結束(說完自動發送)")} disabled={upBusy} onClick={voice.micClick}>
            <Icon2 name="mic" size={15}/>
          </button>
          <button className={"btn" + (voice.mode ? " primary" : " ghost")}
            style={{ height: 38, padding: "0 9px", flexShrink: 0, fontSize: 10.5, fontFamily: "var(--f-mono)", letterSpacing: ".08em" }}
            title={voice.mode ? t("點擊退出語音對話") : t("進入語音對話:說完自動發送、回覆自動朗讀、可隨時插話打斷")}
            disabled={upBusy} onClick={voice.toggleMode}>
            <span className="dock-voice-label">{t("對話")}</span>
            <span className="dock-voice-icon"><Icon2 name="mic" size={13}/></span>
          </button>
          <input ref={inputRef} className="field secretary-compose-input" style={{ flex: 1, minWidth: 0, height: 38 }} value={input}
            onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder={voice.listening ? t("聆聽中…") : t("吩咐秘書…")}/>
          <button className="btn primary" style={{ width: 42, height: 38, padding: 0, flexShrink: 0 }} disabled={!input.trim()} onClick={submit}>
            <Icon2 name="arrow" size={15}/>
          </button>
        </div>
        {voice.error && <div role="alert" style={{ color: "var(--danger)", fontSize: 11.2, lineHeight: 1.45, marginTop: 8 }}>
          {voice.error}
        </div>}
      </div>
    </div>
  );
};

/* ── 統一業務上下文 / entity deep-link ──
   Hash contract:
   #/<module>?entity=<type:id>&tab=<tab>&node=<node_key>&return=<encoded #/route>
   The business-context API is the authority for field and relation visibility. */
const BUSINESS_QUERY_KEYS = ["entity", "tab", "node", "return"];
const BUSINESS_TABS = ["overview", "workflow", "budget", "procurement", "inventory", "finance"];
/* Keep this allowlist in lockstep with GET /api/business-context. Relations may
   mention future entity types, but they must remain non-clickable until the API
   can resolve and authorize them. */
const BUSINESS_CONTEXT_ENTITY_TYPES = new Set(["erp_purchase_request", "wf_instance"]);
const businessHash = (hash = location.hash) => {
  const raw = String(hash || "").replace(/^#\/?/, "");
  const q = raw.indexOf("?");
  const route = (q >= 0 ? raw.slice(0, q) : raw) || "dashboard";
  const params = new URLSearchParams(q >= 0 ? raw.slice(q + 1) : "");
  return { route, params };
};
const validEntityRef = (value) => {
  const ref = String(value || "").trim();
  return ref.length <= 180 && /^[a-z][a-z0-9_]{1,63}:[A-Za-z0-9][A-Za-z0-9._~-]{0,111}$/.test(ref) ? ref : "";
};
const businessContextEntityRef = (value) => {
  const ref = validEntityRef(value);
  if (!ref) return "";
  const split = ref.indexOf(":");
  return BUSINESS_CONTEXT_ENTITY_TYPES.has(ref.slice(0, split)) && /^[1-9]\d*$/.test(ref.slice(split + 1)) ? ref : "";
};
const validBusinessTab = (value) => BUSINESS_TABS.includes(String(value || "")) ? String(value) : "overview";
const validBusinessNodeKey = (value) => {
  const node = String(value || "").trim();
  return node.length <= 120 && /^[A-Za-z0-9][A-Za-z0-9._~-]{0,119}$/.test(node) ? node : "";
};
const secretaryContextOf = (value, useRouteFallback = false) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const entityRef = businessContextEntityRef(value.entity_ref);
  if (!entityRef) return null;
  const nodeKey = validBusinessNodeKey(value.node_key);
  let tab = BUSINESS_TABS.includes(String(value.tab || "")) ? String(value.tab) : "";
  if (!tab && useRouteFallback && W2.businessRoute) {
    const route = W2.businessRoute();
    if (route.entity_ref === entityRef) tab = route.tab;
  }
  return { entity_ref: entityRef, node_key: nodeKey, tab };
};
const secretaryActionContextOf = (value) => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const source = value.action_context && typeof value.action_context === "object"
    && !Array.isArray(value.action_context) ? value.action_context : value;
  const schema = String(source.schema || "");
  if (![
    "warehouse.pages-action-context.v1",
    "warehouse.resource-action-context.v1",
    "warehouse.resource-operation-context.v1",
  ].includes(schema)) return null;
  const actionKey = String(source.action_key || "").trim();
  if (!/^[a-z][a-z0-9_.:-]{2,159}$/.test(actionKey)) return null;
  const validRef = ref => /^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$/.test(String(ref || "").trim());
  const validType = type => /^[a-z][a-z0-9_.:-]{1,127}$/.test(String(type || "").trim());
  const suggestedToolNames = Array.from(new Set(
    (Array.isArray(source.suggested_tool_names) ? source.suggested_tool_names : [])
      .map(name => String(name || "").trim())
      .filter(name => /^[a-z][a-z0-9_]{2,127}$/.test(name)),
  )).slice(0, 8);
  if (schema === "warehouse.pages-action-context.v1") {
    const workspaceRef = String(source.workspace_ref || "").trim();
    const deploymentId = String(source.deployment_id || "").trim();
    if (!actionKey.startsWith("pages.") || !validRef(workspaceRef)) return null;
    if (deploymentId && !validRef(deploymentId)) return null;
    return {
      schema, action_key: actionKey, workspace_ref: workspaceRef,
      ...(deploymentId ? { deployment_id: deploymentId } : {}),
      suggested_tool_names: suggestedToolNames,
    };
  }
  const resourceType = String(source.resource_type || "").trim();
  const resourceRef = String(source.resource_ref || "").trim();
  const resourceVersion = String(source.resource_version || "").trim();
  if (!validType(resourceType) || !validRef(resourceRef)) return null;
  if (resourceVersion && !validRef(resourceVersion)) return null;
  const relatedResources = (Array.isArray(source.related_resources) ? source.related_resources : [])
    .map(item => ({
      resource_type: String(item && item.resource_type || "").trim(),
      resource_ref: String(item && item.resource_ref || "").trim(),
      resource_version: String(item && item.resource_version || "").trim(),
    }))
    .filter(item => validType(item.resource_type) && validRef(item.resource_ref)
      && (!item.resource_version || validRef(item.resource_version)))
    .slice(0, 4)
    .map(item => ({
      resource_type: item.resource_type,
      resource_ref: item.resource_ref,
      ...(item.resource_version ? { resource_version: item.resource_version } : {}),
    }));
  const base = {
    schema, action_key: actionKey, resource_type: resourceType, resource_ref: resourceRef,
    ...(resourceVersion ? { resource_version: resourceVersion } : {}),
    ...(relatedResources.length ? { related_resources: relatedResources } : {}),
    suggested_tool_names: suggestedToolNames,
  };
  if (schema !== "warehouse.resource-operation-context.v1") return base;
  const validTool = name => /^[a-z][a-z0-9_]{2,127}$/.test(String(name || "").trim());
  const validArgument = name => /^[a-z][a-z0-9_-]{0,63}$/.test(String(name || "").trim());
  const validValue = value => {
    const item = String(value || "").trim();
    return item.length > 0 && item.length <= 240 && !/[\u0000\r\n]/.test(item);
  };
  const operationToolName = String(source.operation_tool_name || "").trim();
  const resourceArgumentName = String(source.resource_argument_name || "id").trim();
  if (!validTool(operationToolName) || !validArgument(resourceArgumentName)) return null;
  const observationToolNames = Array.from(new Set(
    (Array.isArray(source.observation_tool_names) ? source.observation_tool_names : [])
      .map(name => String(name || "").trim())
      .filter(name => validTool(name) && name !== operationToolName),
  )).slice(0, 4);
  const boundedArgumentMap = value => Object.fromEntries(
    Object.entries(value && typeof value === "object" && !Array.isArray(value) ? value : {})
      .filter(([key, item]) => validArgument(key) && validValue(item))
      .slice(0, 8)
      .map(([key, item]) => [String(key), String(item).trim()]),
  );
  const operationDefaults = boundedArgumentMap(source.operation_defaults);
  const operationChoices = Object.fromEntries(
    Object.entries(source.operation_choices && typeof source.operation_choices === "object"
      && !Array.isArray(source.operation_choices) ? source.operation_choices : {})
      .filter(([key, values]) => validArgument(key) && Array.isArray(values))
      .slice(0, 8)
      .map(([key, values]) => [String(key), Array.from(new Set(
        values.map(value => String(value || "").trim()).filter(validValue),
      )).slice(0, 32)])
      .filter(([, values]) => values.length),
  );
  if (Object.entries(operationDefaults).some(([key, value]) =>
    operationChoices[key] && !operationChoices[key].includes(value))) return null;
  return {
    ...base,
    operation_tool_name: operationToolName,
    observation_tool_names: observationToolNames,
    resource_argument_name: resourceArgumentName,
    operation_defaults: operationDefaults,
    operation_choices: operationChoices,
  };
};
const validReturnHash = (value) => {
  const hash = String(value || "");
  return hash.length <= 600 && /^#\/[A-Za-z0-9_-]+(?:\?[^\r\n]*)?$/.test(hash) ? hash : "";
};
const hashOf = (route, params) => {
  const query = params.toString();
  return "#/" + route + (query ? "?" + query : "");
};
const cleanBusinessHash = (hash = location.hash) => {
  const state = businessHash(hash);
  BUSINESS_QUERY_KEYS.forEach(key => state.params.delete(key));
  return hashOf(state.route, state.params);
};
W2.entityRef = (type, id) => validEntityRef(String(type || "") + ":" + String(id == null ? "" : id));
W2.isBusinessEntityRef = (value) => !!businessContextEntityRef(value);
W2.parseEntityRef = (value) => {
  const ref = validEntityRef(value);
  if (!ref) return null;
  const split = ref.indexOf(":");
  return { entity_ref: ref, type: ref.slice(0, split), id: ref.slice(split + 1) };
};
W2.businessRoute = () => {
  const state = businessHash();
  return {
    route: state.route,
    entity_ref: businessContextEntityRef(state.params.get("entity")),
    tab: validBusinessTab(state.params.get("tab")),
    node_key: validBusinessNodeKey(state.params.get("node")),
    return_hash: validReturnHash(state.params.get("return")),
  };
};
W2.businessQuerySuffix = () => {
  const source = businessHash().params;
  const entity = businessContextEntityRef(source.get("entity"));
  if (!entity) return "";
  const kept = new URLSearchParams();
  kept.set("entity", entity);
  kept.set("tab", validBusinessTab(source.get("tab")));
  const node = validBusinessNodeKey(source.get("node"));
  const returnHash = validReturnHash(source.get("return"));
  if (node) kept.set("node", node);
  if (returnHash) kept.set("return", returnHash);
  const query = kept.toString();
  return query ? "?" + query : "";
};
W2.openEntity = (entityRef, options = {}) => {
  const ref = businessContextEntityRef(entityRef);
  if (!ref) return false;
  const state = businessHash();
  const priorReturn = validReturnHash(state.params.get("return"));
  const requestedReturn = validReturnHash(options.return_hash || options.returnHash);
  const returnHash = requestedReturn || priorReturn || cleanBusinessHash();
  state.params.set("entity", ref);
  state.params.set("tab", validBusinessTab(options.tab));
  const node = validBusinessNodeKey(options.node_key || options.nodeKey);
  if (node) state.params.set("node", node); else state.params.delete("node");
  if (returnHash) state.params.set("return", returnHash); else state.params.delete("return");
  const target = hashOf(state.route, state.params);
  if (location.hash !== target) {
    if (options.replace === true) location.replace(target);
    else location.hash = target;
  } else {
    window.dispatchEvent(new CustomEvent("w2-business-route", { detail: W2.businessRoute() }));
  }
  return true;
};
W2.setBusinessTab = (tab, options = {}) => {
  const state = businessHash();
  if (!businessContextEntityRef(state.params.get("entity"))) return false;
  state.params.set("tab", validBusinessTab(tab));
  const node = validBusinessNodeKey(options.node_key || options.nodeKey || state.params.get("node"));
  if (node) state.params.set("node", node); else state.params.delete("node");
  const target = hashOf(state.route, state.params);
  if (location.hash !== target) location.replace(target);
  return true;
};
W2.closeEntity = () => {
  const state = businessHash();
  const back = validReturnHash(state.params.get("return"));
  location.replace(back || cleanBusinessHash());
};
W2.clearBusinessContext = () => {
  const target = cleanBusinessHash();
  if (location.hash !== target) location.replace(target);
  else window.dispatchEvent(new CustomEvent("w2-business-route", { detail: W2.businessRoute() }));
};

const businessText = (value) => {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "YES" : "NO";
  if (Array.isArray(value)) return value.map(businessText).join(" · ");
  if (typeof value === "object") return value.label || value.name || value.title || value.no || value.entity_ref || "—";
  return String(value);
};
const BUSINESS_FIELD_LABELS = {
  no: "單號", number: "單號", request_no: "申請號", instance_no: "流程號", voucher_no: "憑證號", document_no: "單據號", po_no: "採購單號", budget_no: "預算號",
  title: "標題", name: "名稱", summary: "摘要", status: "狀態", current_node: "當前節點", current_node_key: "當前節點", node_name: "節點",
  amount: "金額", total_amount: "金額", available: "可用", reserved: "已佔用", spent: "已支出", outstanding: "未結金額", currency: "幣種",
  department_name: "責任部門", position_name: "責任職位", owner_name: "負責人", supplier_name: "供應商", party: "往來方",
  created_at: "建立時間", updated_at: "更新時間", completed_at: "完成時間", due_at: "到期時間", source_type: "來源類型",
  purchase_status: "採購狀態", workflow_status: "流程狀態", workflow_stage: "流程階段", ordered_qty: "已下單數量", received_qty: "已入庫數量",
  current_node_name: "當前節點", workflow_key: "流程模板", allowed_actions: "可用操作",
};
const businessFields = (record) => {
  if (!record || typeof record !== "object" || Array.isArray(record)) return [];
  return Object.keys(BUSINESS_FIELD_LABELS)
    .filter(key => record[key] != null && record[key] !== "")
    .map(key => [BUSINESS_FIELD_LABELS[key], businessText(record[key]), key]);
};
const relationTab = (value) => {
  const key = String(value || "").toLowerCase();
  if (key.includes("workflow") || key.includes("wf_instance")) return "workflow";
  if (key.includes("budget")) return "budget";
  if (key.includes("purchase") || key.includes("procurement") || key.includes("supplier") || key.includes("tender")) return "procurement";
  if (key.includes("inventory") || key.includes("inbound") || key.includes("outbound") || key.includes("stock")) return "inventory";
  if (key.includes("finance") || key.includes("voucher") || key.includes("ledger") || key === "ap" || key === "gl") return "finance";
  return "";
};
const relationArray = (value, group) => {
  const rows = Array.isArray(value) ? value : (value && typeof value === "object" ? [value] : []);
  return rows.filter(row => row && typeof row === "object" && row.visible !== false && row.authorized !== false)
    .map(row => ({ ...row, group: row.group || relationTab(row.relation || row.type) || group }));
};
const normalizeBusinessContext = (payload, requestedRef) => {
  const root = payload && typeof payload === "object" ? (payload.context || payload) : {};
  const access = root.permissions && typeof root.permissions === "object" && !Array.isArray(root.permissions) ? root.permissions
    : root.access && typeof root.access === "object" && !Array.isArray(root.access) ? root.access : {};
  const denied = access.can_view === false || access.visible === false || access.allowed === false;
  const identity = root.identity || root.entity || root.primary || {};
  const relSource = root.relations;
  let relations = [];
  if (Array.isArray(relSource)) relations = relationArray(relSource, "related");
  else if (relSource && typeof relSource === "object") Object.keys(relSource).forEach(group => {
    relations = relations.concat(relationArray(relSource[group], group));
  });
  const sectionAliases = {
    workflow: [root.workflow, root.workflow_context, root.workflow_instances],
    budget: [root.budget, root.budgets, root.budget_context],
    procurement: [root.procurement, root.purchase_order, root.purchase_orders],
    inventory: [root.inventory, root.inventory_documents, root.movements],
    finance: [root.finance, root.vouchers, root.ap, root.ap_entries],
  };
  const sections = {};
  Object.keys(sectionAliases).forEach(tab => { sections[tab] = sectionAliases[tab].find(value => value != null); });
  const tabSpec = Array.isArray(root.tabs) ? root.tabs : Array.isArray(root.allowed_tabs) ? root.allowed_tabs
    : Array.isArray(access.allowed_tabs) ? access.allowed_tabs : null;
  let tabs = tabSpec ? tabSpec.map(item => typeof item === "string" ? item : item && item.id)
    .filter(tab => BUSINESS_TABS.includes(tab) && !(tabSpec.find(item => item && item.id === tab && (item.visible === false || item.allowed === false)))) : null;
  if (!tabs) tabs = BUSINESS_TABS.filter(tab => tab === "overview" || sections[tab] != null || relations.some(row => row.group === tab));
  if (access.tabs && typeof access.tabs === "object" && !Array.isArray(access.tabs)) tabs = tabs.filter(tab => {
    const rule = access.tabs[tab];
    return rule !== false && !(rule && typeof rule === "object" && (rule.visible === false || rule.allowed === false));
  });
  if (!tabs.includes("overview")) tabs.unshift("overview");
  return { root, identity: denied ? {} : identity, relations: denied ? [] : relations, sections: denied ? {} : sections,
    tabs: denied ? ["overview"] : tabs, denied, entity_ref: businessContextEntityRef(root.entity_ref || identity.entity_ref) || businessContextEntityRef(requestedRef) };
};

const businessRecords = (value) => {
  const records = [], seen = new Set();
  const visit = (row, depth) => {
    if (row == null || depth > 2) return;
    if (Array.isArray(row)) { row.forEach(item => visit(item, depth)); return; }
    if (typeof row !== "object") return;
    if (seen.has(row)) return;
    seen.add(row);
    if (businessFields(row).length) records.push(row);
    Object.keys(row).forEach(key => {
      const nested = row[key];
      if (nested && typeof nested === "object") visit(nested, depth + 1);
    });
  };
  visit(value, 0);
  return records;
};
const BusinessFacts = ({ value }) => {
  const records = businessRecords(value);
  if (!records.length) return null;
  return <div className="bw-records">{records.map((record, index) => {
    const fields = businessFields(record);
    return fields.length ? <div className="bw-record" key={record.entity_ref || record.id || index}>{fields.map(([label, text, key]) => (
      <div className="bw-fact" key={key}><span>{label}</span><strong>{text}</strong></div>
    ))}</div> : null;
  })}</div>;
};
const BUSINESS_WORKFLOW_NODE_STATUS = {
  completed: "已完成",
  current: "進行中",
  rejected: "已駁回",
  visited: "已經過",
  bypassed: "未經此路徑",
  pending: "未到",
};
const BUSINESS_WORKFLOW_ACTION = {
  start: "發起",
  activate: "激活",
  approve: "通過",
  reject: "駁回",
  submit: "提交",
  complete: "完成",
  gateway: "分流",
  fork: "並行分叉",
  arrive: "到達匯聚",
  join_fire: "匯聚放行",
  reassign: "轉交",
};
const BUSINESS_WORKFLOW_KIND = {
  form: "填報",
  approval: "審批",
  external_placeholder: "外部留痕",
  system_auto: "系統自動",
  signoff: "簽章",
  gateway_exclusive: "條件分流",
  gateway_parallel: "並行分叉",
  gateway_join: "並行匯聚",
};
const businessWorkflowRuntimeStatus = (node, workflow) => {
  const supplied = String(node && node.runtime_status || "").toLowerCase();
  const nodeKey = node && node.node_key;
  const instanceStatus = String(workflow && workflow.status || "").toLowerCase();
  const currentNodeKey = workflow && workflow.current_node_key;
  const tasks = Array.isArray(workflow && workflow.tasks) ? workflow.tasks.filter(task => task && task.node_key === nodeKey) : [];
  const latestRound = tasks.reduce((value, task) => Math.max(value, Number(task.round_no || 0)), 0);
  const latestTasks = tasks.filter(task => Number(task.round_no || 0) === latestRound);
  const taskStates = latestTasks.map(task => String(task.status || "").toLowerCase());
  const instanceOpen = ["running", "waiting"].includes(instanceStatus);
  if (nodeKey && instanceOpen
    && taskStates.some(status => ["pending", "in_progress"].includes(status))) return "current";
  if (taskStates.includes("rejected")) return "rejected";
  if (taskStates.some(status => ["approved", "completed", "done", "skipped"].includes(status))) return "completed";
  const timeline = Array.isArray(workflow && workflow.timeline) ? workflow.timeline : [];
  const lastTransition = timeline.filter(item => item && item.from_node_key === nodeKey).slice(-1)[0];
  const lastAction = String(lastTransition && lastTransition.action || "").toLowerCase();
  if (lastAction === "reject") return "rejected";
  if (["approve", "submit", "complete", "gateway", "fork", "arrive", "join_fire"].includes(lastAction)
    || (nodeKey && nodeKey === currentNodeKey && instanceStatus === "completed")) return "completed";
  if (nodeKey && instanceOpen && nodeKey === currentNodeKey) return "current";
  if (BUSINESS_WORKFLOW_NODE_STATUS[supplied]) return supplied;
  if (timeline.some(item => item && (item.from_node_key === nodeKey || item.to_node_key === nodeKey))) return "visited";
  return "pending";
};
const businessWorkflowTopologyLayout = (nodes, edges) => {
  const nodeWidth = 154, nodeHeight = 82, columnGap = 48, rowGap = 34, padding = 16;
  const nodeByKey = {};
  const rank = {};
  const indegree = {};
  const outgoing = {};
  nodes.forEach(node => {
    nodeByKey[node.node_key] = node;
    rank[node.node_key] = 0;
    indegree[node.node_key] = 0;
    outgoing[node.node_key] = [];
  });
  (Array.isArray(edges) ? edges : []).forEach(edge => {
    if (!edge || edge.kind === "return" || edge.from_node_key === edge.to_node_key
      || !nodeByKey[edge.from_node_key] || !nodeByKey[edge.to_node_key]) return;
    outgoing[edge.from_node_key].push(edge.to_node_key);
    indegree[edge.to_node_key] += 1;
  });
  const byStep = (a, b) => (Number(nodeByKey[a].step_no || 0) - Number(nodeByKey[b].step_no || 0))
    || String(a).localeCompare(String(b));
  const queue = Object.keys(nodeByKey).filter(key => indegree[key] === 0).sort(byStep);
  const ranked = new Set();
  while (queue.length) {
    const source = queue.shift();
    ranked.add(source);
    outgoing[source].forEach(target => {
      rank[target] = Math.max(rank[target], rank[source] + 1);
      indegree[target] -= 1;
      if (indegree[target] === 0) {
        queue.push(target);
        queue.sort(byStep);
      }
    });
  }
  /* A custom legacy definition may contain a non-return cycle.  Preserve all
     nodes without looping forever; unresolved nodes fall back to their step
     order after the acyclic graph. */
  let fallbackRank = Math.max(0, ...Object.values(rank));
  Object.keys(nodeByKey).filter(key => !ranked.has(key)).sort(byStep).forEach(key => {
    fallbackRank += 1;
    rank[key] = fallbackRank;
  });
  const rankValues = [...new Set(Object.values(rank))].sort((a, b) => a - b);
  const rankColumn = {};
  rankValues.forEach((value, index) => { rankColumn[value] = index; });
  const positions = {};
  let maxRows = 1;
  rankValues.forEach(value => {
    const column = rankColumn[value];
    const columnNodes = nodes.filter(node => rank[node.node_key] === value)
      .sort((a, b) => (Number(a.step_no || 0) - Number(b.step_no || 0)) || String(a.node_key).localeCompare(String(b.node_key)));
    maxRows = Math.max(maxRows, columnNodes.length);
    columnNodes.forEach((node, row) => {
      const x = padding + column * (nodeWidth + columnGap);
      const y = padding + row * (nodeHeight + rowGap);
      positions[node.node_key] = {
        x, y, column,
        left: x,
        right: x + nodeWidth,
        top: y,
        bottom: y + nodeHeight,
        centerX: x + nodeWidth / 2,
        centerY: y + nodeHeight / 2,
      };
    });
  });
  const baseBottom = padding + maxRows * nodeHeight + Math.max(0, maxRows - 1) * rowGap;
  let lane = 0;
  let selfLoopExtension = 0;
  const routedEdges = [];
  (Array.isArray(edges) ? edges : []).forEach((edge, index) => {
    const from = edge && positions[edge.from_node_key];
    const to = edge && positions[edge.to_node_key];
    if (!from || !to) return;
    const returns = edge.kind === "return";
    const selfLoop = edge.from_node_key === edge.to_node_key;
    const routesBelow = selfLoop || returns || to.column <= from.column || to.column - from.column > 1;
    let path;
    if (selfLoop) {
      const laneY = baseBottom + 18 + lane * 14;
      lane += 1;
      const loopRight = from.right + 24;
      selfLoopExtension = Math.max(selfLoopExtension, 32);
      path = "M " + from.centerX + " " + from.bottom
        + " L " + from.centerX + " " + laneY
        + " L " + loopRight + " " + laneY
        + " L " + loopRight + " " + (from.top - 8)
        + " L " + from.centerX + " " + (from.top - 8)
        + " L " + from.centerX + " " + from.top;
    } else if (routesBelow) {
      const laneY = baseBottom + 18 + lane * 14;
      lane += 1;
      path = "M " + from.centerX + " " + from.bottom
        + " L " + from.centerX + " " + laneY
        + " L " + to.centerX + " " + laneY
        + " L " + to.centerX + " " + to.bottom;
    } else if (Math.abs(from.centerY - to.centerY) < 1) {
      path = "M " + from.right + " " + from.centerY
        + " L " + to.left + " " + to.centerY;
    } else {
      const middle = Math.round((from.right + to.left) / 2);
      path = "M " + from.right + " " + from.centerY
        + " L " + middle + " " + from.centerY
        + " L " + middle + " " + to.centerY
        + " L " + to.left + " " + to.centerY;
    }
    routedEdges.push({
      ...edge,
      path,
      returns,
      routesBelow,
      selfLoop,
      key: edge.from_node_key + ">" + edge.to_node_key + ":" + edge.kind + ":" + index,
    });
  });
  return {
    positions,
    edges: routedEdges,
    nodeWidth,
    nodeHeight,
    width: padding * 2 + rankValues.length * nodeWidth
      + Math.max(0, rankValues.length - 1) * columnGap + selfLoopExtension,
    height: baseBottom + (lane ? 20 + lane * 14 : padding),
  };
};
const BusinessWorkflowTopology = ({ workflow, routeNode }) => {
  const topology = workflow && workflow.topology && typeof workflow.topology === "object" ? workflow.topology : {};
  const nodes = (Array.isArray(topology.nodes) ? topology.nodes : [])
    .filter(node => node && node.node_key)
    .map(node => ({ ...node, runtime_status: businessWorkflowRuntimeStatus(node, workflow) }))
    .sort((a, b) => (Number(a.step_no || 0) - Number(b.step_no || 0)) || String(a.node_key).localeCompare(String(b.node_key)));
  const nodeSignature = nodes.map(node => node.node_key).join("|");
  const nodeKeys = new Set(nodes.map(node => node.node_key));
  const routeNodeKnown = nodeKeys.has(routeNode);
  const preferredKey = routeNodeKnown ? routeNode
    : nodeKeys.has(workflow && workflow.current_node_key) ? workflow.current_node_key
    : nodes.length ? nodes[0].node_key : "";
  const [selectedKey, setSelectedKey] = React.useState(preferredKey);
  const graphScrollRef = React.useRef(null);
  React.useEffect(() => {
    setSelectedKey(preferredKey);
    if (preferredKey && routeNode !== preferredKey) {
      W2.setBusinessTab("workflow", { node_key: preferredKey });
    }
  }, [workflow && workflow.id, preferredKey, routeNode, routeNodeKnown, nodeSignature]);
  React.useEffect(() => {
    const selectedNode = graphScrollRef.current
      && graphScrollRef.current.querySelector('[data-selected="true"]');
    if (selectedNode && selectedNode.scrollIntoView) {
      selectedNode.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
        inline: "center",
      });
    }
  }, [selectedKey, nodeSignature]);
  if (!nodes.length) return null;

  const nodeByKey = {};
  nodes.forEach(node => { nodeByKey[node.node_key] = node; });
  const suppliedStages = Array.isArray(topology.stages) ? topology.stages : [];
  const stages = [];
  const stageKeys = new Set();
  suppliedStages.forEach((stage, index) => {
    if (!stage || !stage.key || stageKeys.has(stage.key)) return;
    stageKeys.add(stage.key);
    stages.push({ ...stage, seq: stage.seq == null ? index + 1 : stage.seq });
  });
  nodes.forEach(node => {
    const stageKey = node.stage_key || "__ungrouped";
    if (stageKeys.has(stageKey)) return;
    stageKeys.add(stageKey);
    stages.push({ key: stageKey, name: node.stage_key || "未分組", seq: stages.length + 1 });
  });
  stages.sort((a, b) => (Number(a.seq || 0) - Number(b.seq || 0)) || String(a.key).localeCompare(String(b.key)));

  const tasks = Array.isArray(workflow.tasks) ? workflow.tasks : [];
  const timeline = Array.isArray(workflow.timeline) ? workflow.timeline : [];
  const edges = Array.isArray(topology.edges) ? topology.edges : [];
  const graph = businessWorkflowTopologyLayout(nodes, edges);
  const selected = nodeByKey[selectedKey] || nodeByKey[preferredKey] || nodes[0];
  const selectedTasks = tasks.filter(task => task && task.node_key === selected.node_key)
    .sort((a, b) => Number(b.round_no || 0) - Number(a.round_no || 0) || Number(b.id || 0) - Number(a.id || 0));
  const selectedTimeline = timeline.filter(item => item
    && (item.from_node_key === selected.node_key || item.to_node_key === selected.node_key))
    .slice(-6).reverse();
  const outgoing = edges.filter(edge => edge && edge.from_node_key === selected.node_key && edge.kind !== "return");
  const returns = edges.filter(edge => edge && edge.from_node_key === selected.node_key && edge.kind === "return");
  const nodeName = key => nodeByKey[key] && nodeByKey[key].name || key || "—";
  const stageName = key => {
    const stage = stages.find(item => item.key === (key || "__ungrouped"));
    return stage && stage.name || key || "未分組";
  };
  const progressNodes = nodes.filter(node => node.runtime_status !== "bypassed");
  const completedCount = progressNodes.filter(node => node.runtime_status === "completed").length;
  const progressNodeCount = progressNodes.length;
  const currentCount = nodes.filter(node => node.runtime_status === "current").length;
  const selectNode = node => {
    setSelectedKey(node.node_key);
    W2.setBusinessTab("workflow", { node_key: node.node_key });
  };
  const taskOwner = task => [
    task.assignee_department_name || task.assignee_department_code,
    task.assignee_position_name || task.assignee_position_code,
  ].filter(Boolean).join(" / ") || "尚未指派";
  const responsibility = [
    selected.department_name || selected.department_code,
    selected.position_name || selected.position_code,
  ].filter(Boolean).join(" / ") || "依流程動態指派";
  const markerBase = "bwflow" + String(workflow.id || "context").replace(/[^A-Za-z0-9_-]/g, "");

  return (
    <section className="bw-flow" aria-label="流程拓撲">
      <div className="bw-flow-head">
        <div>
          <div className="bw-section-title">INTERACTIVE FLOW TOPOLOGY · READ ONLY</div>
          <div className="bw-flow-title">{topology.name || workflow.workflow_name || workflow.workflow_key || "流程拓撲"}</div>
          <div className="bw-flow-sub">{workflow.instance_no || workflow.entity_ref || "—"} · {businessText(workflow.status)}</div>
        </div>
        <span className={"bw-flow-state is-" + (currentCount ? "current" : String(workflow.status || "pending").toLowerCase())}>
          {currentCount ? "LIVE" : businessText(workflow.status).toUpperCase()}
        </span>
      </div>
      <div className="bw-flow-kpis" aria-label="流程統計">
        <div><span>STAGES</span><strong>{stages.length}</strong><small>階段</small></div>
        <div><span>NODES</span><strong>{nodes.length}</strong><small>節點</small></div>
        <div><span>COMPLETED</span><strong>{completedCount}</strong><small>已完成</small></div>
        <div><span>CURRENT</span><strong>{currentCount || "—"}</strong><small>{stageName(workflow.current_stage_key)}</small></div>
      </div>
      <div className="bw-flow-progress" role="progressbar" aria-valuemin="0" aria-valuemax={progressNodeCount}
        aria-valuenow={completedCount} aria-label={"已完成 " + completedCount + " / " + progressNodeCount + " 個有效節點"}>
        <span style={{ width: Math.max(0, Math.min(100, progressNodeCount ? completedCount / progressNodeCount * 100 : 0)) + "%" }}/>
      </div>
      <div className="bw-flow-stage-nav" aria-label="流程階段">
        {stages.map((stage, stageIndex) => {
          const stageNodes = nodes.filter(node => (node.stage_key || "__ungrouped") === stage.key);
          const stageCurrent = stageNodes.some(node => node.runtime_status === "current");
          const stageDone = stageNodes.filter(node => node.runtime_status === "completed").length;
          const stageEligible = stageNodes.filter(node => node.runtime_status !== "bypassed").length;
          const stageSelected = stageNodes.some(node => node.node_key === selected.node_key);
          const stageTarget = stageNodes.find(node => node.runtime_status === "current") || stageNodes[0];
          return (
            <button type="button" key={stage.key} disabled={!stageTarget}
              className={(stageCurrent ? "is-current " : "") + (stageSelected ? "is-selected" : "")}
              aria-pressed={stageSelected}
              onClick={() => stageTarget && selectNode(stageTarget)}>
              <span>{String(stageIndex + 1).padStart(2, "0")}</span>
              <strong>{stage.name || stage.key}</strong>
              <small>{stageDone}/{stageEligible}</small>
            </button>
          );
        })}
      </div>
      <div className="bw-flow-scroll" ref={graphScrollRef} tabIndex="0" aria-label="可橫向捲動的流程拓撲">
        <div className="bw-flow-graph" style={{ width: graph.width, height: graph.height }}>
          <svg width={graph.width} height={graph.height} viewBox={"0 0 " + graph.width + " " + graph.height} aria-hidden="true">
            <defs>
              <marker id={markerBase + "-forward"} viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0L8 4L0 8Z"/>
              </marker>
              <marker id={markerBase + "-return"} viewBox="0 0 8 8" refX="7" refY="4"
                markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                <path d="M0 0L8 4L0 8Z"/>
              </marker>
            </defs>
            {graph.edges.map(edge => (
              <path key={edge.key} className={edge.returns ? "is-return" : ""}
                d={edge.path}
                markerEnd={"url(#" + markerBase + (edge.returns ? "-return" : "-forward") + ")"}/>
            ))}
          </svg>
          {nodes.map(node => {
            const status = node.runtime_status;
            const position = graph.positions[node.node_key];
            const nextCount = edges.filter(edge => edge && edge.kind !== "return" && edge.from_node_key === node.node_key).length;
            return position ? (
              <button type="button" key={node.node_key}
                data-selected={selected.node_key === node.node_key ? "true" : "false"}
                className={"bw-flow-node is-" + status}
                style={{ left: position.x, top: position.y, width: graph.nodeWidth, height: graph.nodeHeight }}
                onClick={() => selectNode(node)}
                aria-pressed={selected.node_key === node.node_key}
                aria-current={status === "current" && node.node_key === workflow.current_node_key ? "step" : undefined}
                title={(node.step_no == null ? "" : node.step_no + " · ") + (node.name || node.node_key)}
                aria-label={(node.name || node.node_key) + "，" + BUSINESS_WORKFLOW_NODE_STATUS[status]}>
                <span className="bw-flow-node-meta">
                  <b>{String(node.step_no == null ? "—" : node.step_no).padStart(2, "0")}</b>
                  <i>{BUSINESS_WORKFLOW_NODE_STATUS[status]}</i>
                </span>
                <strong>{node.name || node.node_key}</strong>
                <small>{BUSINESS_WORKFLOW_KIND[node.node_kind] || node.node_kind || "節點"}{nextCount > 1 ? " · 分流 ×" + nextCount : ""}</small>
              </button>
            ) : null;
          })}
        </div>
      </div>
      <div className="bw-flow-legend" aria-label="狀態圖例">
        <span><i className="done"/>已完成</span>
        <span><i className="current"/>當前節點</span>
        <span><i className="rejected"/>已駁回</span>
        <span><i className="visited"/>已到達</span>
        <span><i className="bypassed"/>未經此路徑</span>
        <span><i className="pending"/>未到</span>
      </div>
      <div className="bw-flow-detail" aria-live="polite">
        <div className="bw-flow-detail-head">
          <div>
            <span>NODE · {selected.node_key}</span>
            <strong>{selected.name || selected.node_key}</strong>
          </div>
          <em className={"is-" + selected.runtime_status}>{BUSINESS_WORKFLOW_NODE_STATUS[selected.runtime_status]}</em>
        </div>
        <div className="bw-flow-detail-grid">
          <div><span>階段 / STEP</span><strong>{stageName(selected.stage_key)} · {selected.step_no == null ? "—" : selected.step_no}</strong></div>
          <div><span>節點類型</span><strong>{BUSINESS_WORKFLOW_KIND[selected.node_kind] || selected.node_kind || "節點"}</strong></div>
          <div><span>責任位置</span><strong>{responsibility}</strong></div>
          <div><span>流轉方向</span><strong>{outgoing.length ? outgoing.map(edge => nodeName(edge.to_node_key)).join(" / ") : "流程終點"}</strong></div>
          {!!returns.length && <div><span>退回路徑</span><strong>{returns.map(edge => nodeName(edge.to_node_key)).join(" / ")}</strong></div>}
        </div>
        <div className="bw-flow-runtime">
          <div>
            <div className="bw-flow-runtime-title">TASKS · 節點任務</div>
            {selectedTasks.length ? selectedTasks.map((task, index) => (
              <div className="bw-flow-event" key={task.id || task.task_no || index}>
                <span className={"is-" + String(task.status || "pending").toLowerCase()}>{businessText(task.status)}</span>
                <strong>{taskOwner(task)}</strong>
                <small>{task.decided_at || ("ROUND " + (task.round_no || 1))}</small>
              </div>
            )) : <div className="bw-flow-none">尚未產生此節點任務</div>}
          </div>
          <div>
            <div className="bw-flow-runtime-title">AUDIT TRAIL · 相鄰流轉</div>
            {selectedTimeline.length ? selectedTimeline.map((item, index) => (
              <div className="bw-flow-event" key={item.id || index}>
                <span>{BUSINESS_WORKFLOW_ACTION[item.action] || item.action || "流轉"}</span>
                <strong>{nodeName(item.from_node_key)} → {nodeName(item.to_node_key)}</strong>
                <small>{item.created_at || "—"}</small>
              </div>
            )) : <div className="bw-flow-none">尚無此節點的流轉記錄</div>}
          </div>
        </div>
      </div>
    </section>
  );
};
const BusinessRelation = ({ relation, rootEntityRef }) => {
  const parsedRef = validEntityRef(relation.entity_ref);
  const ref = businessContextEntityRef(parsedRef);
  const unsupported = !!parsedRef && !ref;
  const rootType = (W2.parseEntityRef(rootEntityRef) || {}).type;
  const tab = BUSINESS_TABS.includes(relation.tab) ? relation.tab : relation.group;
  const localTab = rootType === "erp_purchase_request" && BUSINESS_TABS.includes(tab);
  const locked = relation.locked === true || relation.can_open === false || relation.allowed === false || (!ref && !localTab);
  const label = relation.label || relation.title || relation.name || relation.no || relation.request_no || relation.instance_no || parsedRef || "關聯業務";
  const restriction = relation.reason || relation.blocked_reason
    || (unsupported ? (localTab ? "在主單頁籤查看" : "此關聯類型尚未開通") : !parsedRef ? "關聯識別無效" : locked ? "無權進入" : "");
  const meta = [relation.status, restriction].filter(Boolean).join(" · ") || ref;
  const open = () => {
    if (locked) return;
    /* A purchase request is the aggregate root: its workflow, budget, PO,
       inventory and finance relations stay in one workbench and switch tabs. */
    if (localTab) {
      W2.setBusinessTab(tab, { node_key: relation.node_key || relation.current_node_key });
      return;
    }
    W2.openEntity(ref, { tab: BUSINESS_TABS.includes(tab) ? tab : "overview", node_key: relation.node_key || relation.current_node_key, replace: true });
  };
  return (
    <button className={"bw-relation" + (locked ? " locked" : "")} disabled={locked}
      onClick={open}>
      <span className="bw-relation-kind">{relation.group || relation.type || (W2.parseEntityRef(parsedRef) || {}).type || "RELATED"}</span>
      <span className="bw-relation-main"><strong>{label}</strong><small>{meta}</small></span>
      <Icon2 name={locked ? "shield" : "arrow"} size={13}/>
    </button>
  );
};
const BusinessWorkbench = () => {
  const [route, setRoute] = React.useState(() => W2.businessRoute());
  const [state, setState] = React.useState({ loading: false, data: null, error: null });
  const [nonce, setNonce] = React.useState(0);
  React.useEffect(() => {
    const sync = () => setRoute(W2.businessRoute());
    window.addEventListener("hashchange", sync);
    window.addEventListener("w2-business-route", sync);
    return () => { window.removeEventListener("hashchange", sync); window.removeEventListener("w2-business-route", sync); };
  }, []);
  React.useEffect(() => {
    if (!route.entity_ref) { setState({ loading: false, data: null, error: null }); return undefined; }
    let alive = true;
    const requestTenant = W2.tenant();
    const controller = new AbortController();
    setState({ loading: true, data: null, error: null });
    W2.json("/api/business-context?entity_ref=" + encodeURIComponent(route.entity_ref), { signal: controller.signal })
      .then(payload => { if (alive && requestTenant === W2.tenant()) setState({ loading: false, data: normalizeBusinessContext(payload, route.entity_ref), error: null }); })
      .catch(error => { if (alive && requestTenant === W2.tenant() && error.name !== "AbortError") setState({ loading: false, data: null, error }); });
    return () => { alive = false; controller.abort(); };
  }, [route.entity_ref, nonce]);
  React.useEffect(() => {
    if (!route.entity_ref) return undefined;
    const onKey = event => { if (event.key === "Escape") W2.closeEntity(); };
    const refresh = () => setNonce(value => value + 1);
    window.addEventListener("keydown", onKey);
    window.addEventListener("w2-agent-complete", refresh);
    return () => { window.removeEventListener("keydown", onKey); window.removeEventListener("w2-agent-complete", refresh); };
  }, [route.entity_ref]);
  if (!route.entity_ref) return null;
  const context = state.data;
  const activeTab = context && context.tabs.includes(route.tab) ? route.tab : "overview";
  const identity = context && context.identity || {};
  const overview = context ? [identity, context.root.lifecycle, context.root.current_node,
    Array.isArray(context.root.allowed_actions) && context.root.allowed_actions.length ? { allowed_actions: context.root.allowed_actions } : null].filter(Boolean) : [];
  const title = identity.title || identity.name || identity.summary || identity.request_no || identity.instance_no || identity.voucher_no || route.entity_ref;
  const relationRows = context ? context.relations.filter(row => activeTab === "overview" || row.group === activeTab) : [];
  const section = context && activeTab !== "overview" ? context.sections[activeTab] : null;
  const factSource = activeTab === "overview" ? overview : section;
  const hasWorkflowTopology = activeTab === "workflow" && section && section.topology
    && Array.isArray(section.topology.nodes) && section.topology.nodes.length > 0;
  const hasFacts = hasWorkflowTopology || businessRecords(factSource).length > 0;
  const noData = !hasFacts && !relationRows.length;
  const askContext = () => W2.openSecretary(
    `請分析業務對象 ${route.entity_ref}${route.node_key ? `，聚焦節點 ${route.node_key}` : ""}，說明目前狀態、風險與下一步；任何改動先向我確認。`,
    { display_text: `分析 ${title}`, entity_ref: route.entity_ref, node_key: route.node_key }
  );
  return (
    <div className="bw-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) W2.closeEntity(); }}>
      <style>{`
        .bw-layer{position:fixed;inset:0;z-index:85;background:rgba(17,17,17,.24);display:flex;justify-content:flex-end;backdrop-filter:blur(1px)}
        .bw-drawer{width:min(720px,100vw);height:100%;background:var(--paper);border-left:2px solid var(--rule);box-shadow:-18px 0 50px rgba(0,0,0,.14);display:flex;flex-direction:column}
        .bw-head{padding:18px 20px 15px;border-bottom:2px solid var(--rule);background:var(--white)}
        .bw-kicker{font:700 9px/1 var(--f-mono);letter-spacing:.16em;color:var(--red);text-transform:uppercase;overflow-wrap:anywhere}
        .bw-title{font-size:20px;font-weight:760;letter-spacing:-.03em;line-height:1.25;margin-top:8px;overflow-wrap:anywhere}
        .bw-tabs{display:flex;gap:0;overflow-x:auto;border-bottom:1px solid var(--hair);background:var(--white);padding:0 20px}
        .bw-tabs button{flex:0 0 auto;padding:11px 12px 9px;border-bottom:2px solid transparent;font:700 10px/1 var(--f-mono);letter-spacing:.08em;color:var(--ink-3)}
        .bw-tabs button.on{border-bottom-color:var(--red);color:var(--ink)}
        .bw-body{padding:18px 20px 28px;overflow:auto;overscroll-behavior:contain}
        .bw-records{display:grid;gap:10px}.bw-record{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;border-top:1px solid var(--hair);padding-top:12px}
        .bw-fact{min-width:0;display:flex;flex-direction:column;gap:4px}.bw-fact span{font:650 8.5px/1.2 var(--f-mono);letter-spacing:.1em;color:var(--ink-4)}.bw-fact strong{font-size:12.5px;line-height:1.45;overflow-wrap:anywhere}
        .bw-section{margin-top:20px}.bw-section-title{font:700 9px/1 var(--f-mono);letter-spacing:.13em;color:var(--ink-4);margin-bottom:9px}
        .bw-flow{min-width:0}.bw-flow-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;border-top:2px solid var(--rule);padding-top:12px}
        .bw-flow-title{font-size:17px;font-weight:760;letter-spacing:-.025em;line-height:1.25}.bw-flow-sub{margin-top:4px;font:550 9.5px/1.4 var(--f-mono);color:var(--ink-4)}
        .bw-flow-state{flex:0 0 auto;padding:5px 7px;border:1px solid var(--hair);font:750 8px/1 var(--f-mono);letter-spacing:.12em;color:var(--ink-3)}.bw-flow-state.is-current{border-color:var(--red);background:var(--red);color:var(--on-red)}
        .bw-flow-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin-top:14px;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule)}
        .bw-flow-kpis>div{min-width:0;padding:10px 8px;border-right:1px solid var(--hair);display:grid;grid-template-columns:auto 1fr;gap:2px 6px;align-items:baseline}.bw-flow-kpis>div:last-child{border-right:0}
        .bw-flow-kpis span{grid-column:1/-1;font:700 7.5px/1 var(--f-mono);letter-spacing:.12em;color:var(--ink-4)}.bw-flow-kpis strong{font:780 19px/1 var(--f-mono)}.bw-flow-kpis small{min-width:0;font-size:9px;color:var(--ink-4);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .bw-flow-progress{height:3px;background:var(--hair-soft);overflow:hidden}.bw-flow-progress span{display:block;height:100%;background:var(--ink);transition:width .25s ease}
        .bw-flow-stage-nav{display:flex;gap:0;margin-top:14px;overflow-x:auto;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);background:var(--white);scrollbar-width:thin}.bw-flow-stage-nav button{flex:1 0 120px;min-height:48px;padding:8px 9px;border-right:1px solid var(--hair);display:grid;grid-template-columns:auto 1fr auto;gap:6px;align-items:center;text-align:left;color:var(--ink-3)}.bw-flow-stage-nav button:last-child{border-right:0}.bw-flow-stage-nav button:hover:not(:disabled){background:var(--paper)}.bw-flow-stage-nav button.is-selected{box-shadow:inset 0 -2px 0 var(--ink);color:var(--ink)}.bw-flow-stage-nav button.is-current{box-shadow:inset 0 -2px 0 var(--red);color:var(--ink)}.bw-flow-stage-nav button:focus-visible{outline:2px solid var(--red);outline-offset:-2px}.bw-flow-stage-nav span,.bw-flow-stage-nav small{font:700 7.5px/1 var(--f-mono);color:var(--ink-4)}.bw-flow-stage-nav strong{font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .bw-flow-scroll{margin-top:14px;overflow-x:auto;overscroll-behavior-inline:contain;border:1px solid var(--hair);background:var(--white);scrollbar-width:thin}.bw-flow-scroll:focus-visible{outline:2px solid var(--red);outline-offset:2px}
        .bw-flow-graph{position:relative;min-width:100%}.bw-flow-graph svg{position:absolute;inset:0;display:block;overflow:visible}.bw-flow-graph svg>path{fill:none;stroke:var(--ink-3);stroke-width:1}.bw-flow-graph svg marker path{fill:var(--ink-3);stroke:none}.bw-flow-graph svg>path.is-return{stroke:var(--red);stroke-dasharray:4 3}.bw-flow-graph svg marker[id$="-return"] path{fill:var(--red)}
        .bw-flow-node{position:absolute;min-height:64px;padding:9px 10px;border:1px solid var(--ink-4);background:var(--paper);text-align:left;display:flex;flex-direction:column;gap:5px;overflow:hidden;transition:border-color .15s,background .15s,color .15s,transform .15s}.bw-flow-node:hover{transform:translateY(-1px);border-color:var(--ink)}.bw-flow-node:focus-visible{outline:2px solid var(--red);outline-offset:2px}
        .bw-flow-node[aria-pressed="true"]{box-shadow:inset 3px 0 0 var(--red)}.bw-flow-node.is-completed{border-color:var(--ink);background:var(--ink);color:var(--paper)}.bw-flow-node.is-visited{border-color:var(--ink-2);background:var(--white);color:var(--ink)}.bw-flow-node.is-current{border:2px solid var(--red);padding:8px 9px;background:var(--white)}.bw-flow-node.is-rejected{border-color:var(--danger);border-style:dashed}.bw-flow-node.is-bypassed{border-style:dotted;background:var(--white);color:var(--ink-4);opacity:.58}.bw-flow-node.is-pending{color:var(--ink-3)}
        .bw-flow-node-meta{display:flex;align-items:center;justify-content:space-between;gap:8px}.bw-flow-node-meta b,.bw-flow-node-meta i{font:700 7.5px/1 var(--f-mono);letter-spacing:.08em}.bw-flow-node-meta i{font-style:normal;color:var(--ink-4)}.bw-flow-node.is-completed .bw-flow-node-meta i{color:var(--paper);opacity:.7}.bw-flow-node.is-visited .bw-flow-node-meta i{color:var(--ink-2)}.bw-flow-node.is-current .bw-flow-node-meta i{color:var(--red)}.bw-flow-node.is-rejected .bw-flow-node-meta i{color:var(--danger)}
        .bw-flow-node>strong{font-size:11.5px;line-height:1.25;overflow:hidden;overflow-wrap:anywhere;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2}.bw-flow-node>small{font:550 8.5px/1.2 var(--f-mono);color:inherit;opacity:.68;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .bw-flow-legend{display:flex;flex-wrap:wrap;gap:8px 14px;margin-top:9px;font-size:9.5px;color:var(--ink-3)}.bw-flow-legend span{display:flex;align-items:center;gap:5px}.bw-flow-legend i{width:9px;height:9px;border:1px solid var(--ink-4)}.bw-flow-legend i.done{background:var(--ink);border-color:var(--ink)}.bw-flow-legend i.current{border:2px solid var(--red)}.bw-flow-legend i.rejected{border-color:var(--danger);border-style:dashed}.bw-flow-legend i.visited{border-color:var(--ink-2);background:var(--white)}.bw-flow-legend i.bypassed{border-style:dotted;opacity:.58}
        .bw-flow-detail{margin-top:14px;border:1px solid var(--ink);background:var(--white)}.bw-flow-detail-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;padding:12px 13px;border-bottom:1px solid var(--hair)}.bw-flow-detail-head>div{display:flex;min-width:0;flex-direction:column;gap:5px}.bw-flow-detail-head span{font:700 8px/1 var(--f-mono);letter-spacing:.1em;color:var(--ink-4);overflow-wrap:anywhere}.bw-flow-detail-head strong{font-size:14px;line-height:1.3;overflow-wrap:anywhere}.bw-flow-detail-head em{font:750 8px/1 var(--f-mono);font-style:normal;letter-spacing:.08em;padding:5px 7px;border:1px solid var(--hair)}.bw-flow-detail-head em.is-current{border-color:var(--red);color:var(--red)}.bw-flow-detail-head em.is-rejected{border-color:var(--danger);color:var(--danger)}
        .bw-flow-detail-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 14px;padding:4px 13px 10px}.bw-flow-detail-grid>div{display:flex;min-width:0;justify-content:space-between;gap:10px;border-top:1px solid var(--hair-soft);padding:8px 0}.bw-flow-detail-grid span{flex:0 0 auto;font:700 7.5px/1.3 var(--f-mono);letter-spacing:.08em;color:var(--ink-4)}.bw-flow-detail-grid strong{font-size:10.5px;line-height:1.35;text-align:right;overflow-wrap:anywhere}
        .bw-flow-runtime{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--hair)}.bw-flow-runtime>div{min-width:0;padding:11px 13px}.bw-flow-runtime>div+div{border-left:1px solid var(--hair)}.bw-flow-runtime-title{margin-bottom:7px;font:700 8px/1 var(--f-mono);letter-spacing:.1em;color:var(--ink-4)}
        .bw-flow-event{display:grid;grid-template-columns:auto 1fr;gap:3px 8px;padding:7px 0;border-top:1px solid var(--hair-soft);align-items:baseline}.bw-flow-event>span{font:700 8px/1 var(--f-mono);color:var(--red);text-transform:uppercase}.bw-flow-event>strong{font-size:10.5px;line-height:1.35;text-align:right;overflow-wrap:anywhere}.bw-flow-event>small{grid-column:1/-1;font:500 8.5px/1.3 var(--f-mono);color:var(--ink-4);text-align:right;overflow-wrap:anywhere}.bw-flow-none{padding:12px 0;border-top:1px solid var(--hair-soft);font-size:10.5px;color:var(--ink-4)}
        .bw-relations{border-top:2px solid var(--rule)}.bw-relation{display:flex;width:100%;gap:12px;align-items:center;text-align:left;padding:12px 4px;border-bottom:1px solid var(--hair)}
        .bw-relation:hover:not(:disabled){background:var(--white)}.bw-relation.locked{opacity:.55;cursor:not-allowed}.bw-relation-kind{width:100px;flex:0 0 100px;font:700 8.5px/1.3 var(--f-mono);letter-spacing:.08em;color:var(--red);text-transform:uppercase;overflow-wrap:anywhere}
        .bw-relation-main{display:flex;min-width:0;flex:1;flex-direction:column;gap:3px}.bw-relation-main strong{font-size:12.5px;overflow-wrap:anywhere}.bw-relation-main small{font:500 10px/1.35 var(--f-mono);color:var(--ink-4);overflow-wrap:anywhere}
        .bw-empty{padding:36px 4px;text-align:center;color:var(--ink-4);font-size:12.5px;line-height:1.6;border-top:1px solid var(--hair)}
        @media(max-width:640px){.bw-drawer{width:100vw;border-left:0}.bw-head{padding:14px 15px 12px}.bw-tabs{padding:0 8px}.bw-body{padding:15px}.bw-record{grid-template-columns:1fr}.bw-relation-kind{width:78px;flex-basis:78px}.bw-title{font-size:18px}.bw-flow-kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.bw-flow-kpis>div:nth-child(2){border-right:0}.bw-flow-kpis>div:nth-child(-n+2){border-bottom:1px solid var(--hair)}.bw-flow-detail-grid,.bw-flow-runtime{grid-template-columns:1fr}.bw-flow-runtime>div+div{border-left:0;border-top:1px solid var(--hair)}}
      `}</style>
      <aside className="bw-drawer" role="dialog" aria-modal="true" aria-label="業務上下文" onMouseDown={event => event.stopPropagation()}>
        <div className="bw-head">
          <div className="row spread g10">
            <div className="bw-kicker">BUSINESS CONTEXT · {route.entity_ref}</div>
            <div className="row g4">
              <button className="btn ghost sm" onClick={() => setNonce(value => value + 1)} title="刷新"><Icon2 name="refresh" size={12}/></button>
              <button className="btn ghost sm" onClick={W2.closeEntity} title="關閉"><Icon2 name="x" size={13}/></button>
            </div>
          </div>
          <div className="bw-title">{state.loading ? "讀取業務上下文…" : title}</div>
          {route.node_key && <div className="mono muted" style={{ fontSize: 10.5, marginTop: 6 }}>NODE · {route.node_key}</div>}
          {!state.loading && !state.error && !(context && context.denied) && <div className="row g6 wrap" style={{ marginTop: 12 }}>
            <button className="btn primary sm" onClick={askContext}><Icon2 name="sparkle" size={12}/>交秘書研判</button>
            <span className="tag">READ ONLY · AUDITED</span>
          </div>}
        </div>
        {context && <div className="bw-tabs" role="tablist">{context.tabs.map(tab => (
          <button key={tab} className={activeTab === tab ? "on" : ""} onClick={() => W2.setBusinessTab(tab)}>{tab}</button>
        ))}</div>}
        <div className="bw-body">
          {state.loading ? <div className="bw-empty">正在讀取已授權的關聯資料…</div>
            : state.error ? <div className="bw-empty">{state.error.status === 403 ? "無權查看此業務上下文" : state.error.status === 404 ? "找不到此業務對象或關聯已失效" : "業務上下文載入失敗，請稍後重試"}</div>
            : context && context.denied ? <div className="bw-empty">無權查看此業務上下文</div>
            : context ? <>
              {hasWorkflowTopology
                ? <BusinessWorkflowTopology workflow={section} routeNode={route.node_key}/>
                : <BusinessFacts value={factSource}/>}
              {!!relationRows.length && <div className="bw-section"><div className="bw-section-title">RELATED · 可追溯關聯</div><div className="bw-relations">{relationRows.map((relation, index) => <BusinessRelation relation={relation} rootEntityRef={context.entity_ref} key={relation.entity_ref || relation.id || index}/>)}</div></div>}
              {noData && <div className="bw-empty">暫無可查看的關聯資料</div>}
            </> : null}
        </div>
      </aside>
    </div>
  );
};
W2.openSecretary = (prompt, options = {}) => {
  const displayText = typeof options === "string" ? options : options && (options.display_text || options.displayText);
  const intent = options && typeof options === "object" ? options.intent : undefined;
  const businessContext = secretaryContextOf(options, true);
  const actionContext = secretaryActionContextOf(options);
  const detail = { prompt, display_text: displayText, intent };
  if (businessContext) {
    detail.entity_ref = businessContext.entity_ref;
    if (businessContext.node_key) detail.node_key = businessContext.node_key;
    if (businessContext.tab) detail.tab = businessContext.tab;
  }
  if (actionContext) detail.action_context = actionContext;
  window.dispatchEvent(new CustomEvent("w2-secretary-open", { detail }));
};

Object.assign(W2, { Btn, Tag, Label, Empty, Kpi, Meter, StackBar, Spark2, MirrorBars, TrendArea,
  UnitMatrix, SwissGuideDialog, OperationConfirmation, RepairPlanCard, workflowRepairEnvelope,
  workflowRepairEnvelopes, BusinessDraftCard, secretaryBusinessDraftItems,
  SecretaryDock, BusinessWorkflowTopology, BusinessWorkbench });
})();
