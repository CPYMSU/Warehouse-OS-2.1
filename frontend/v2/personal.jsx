(() => {
const { useEffect, useMemo, useRef, useState } = React;
const { Icon } = W2;

const PERSONAL_INVITE_KEY = "w2_personal_pending_invite";
const personalRequest = async (path, options = {}) => {
  const headers = new Headers(options.headers || {});
  const response = await fetch(W2.API_BASE + path, { ...options, headers, credentials: "include" });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && !/^\/api\/personal\/auth\/(?:login|register)$/.test(path)) {
    window.dispatchEvent(new Event("personal-auth-expired"));
  }
  if (!response.ok) {
    const error = new Error(data.error || data.message || response.statusText);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
};
const personalGet = (path) => personalRequest(path);
const personalPost = (path, body) => personalRequest(path, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body || {}),
});

const personalStream = async (path, body, { signal, onEvent }) => {
  const response = await fetch(W2.API_BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body || {}),
    signal,
  });
  if (response.status === 401) window.dispatchEvent(new Event("personal-auth-expired"));
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = new Error(data.error || data.message || response.statusText);
    error.status = response.status;
    error.data = data;
    throw error;
  }
  if (!response.body) throw new Error("瀏覽器無法讀取管家回應串流。");
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let pending = "";
  const emitLine = (line) => {
    const clean = String(line || "").trim();
    if (!clean) return;
    try { onEvent(JSON.parse(clean)); }
    catch (error) { console.warn("Skipped malformed assistant stream event", clean); }
  };
  while (true) {
    const { value, done } = await reader.read();
    pending += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = pending.split(/\r?\n/);
    pending = lines.pop() || "";
    lines.forEach(emitLine);
    if (done) break;
  }
  emitLine(pending);
};

const EXPENSE_CATEGORIES = ["購物", "服務", "交通", "餐飲", "居住", "家庭", "健康", "教育", "娛樂", "其他"];
const EXPENSE_DEFAULT_TITLE = {
  購物: "日用品", 服務: "生活服務", 交通: "交通", 餐飲: "餐飲", 居住: "居住支出",
  家庭: "家庭支出", 健康: "健康", 教育: "教育", 娛樂: "娛樂", 其他: "其他開銷",
};
const makeLocalId = (prefix = "local") => `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
const PERSONAL_IMAGE_SOURCE_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"]);
const PERSONAL_IMAGE_SOURCE_ACCEPT = "image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif";
const PERSONAL_IMAGE_SOURCE_MAX_BYTES = 50 * 1024 * 1024;
const PERSONAL_IMAGE_UPLOAD_MAX_BYTES = 2 * 1024 * 1024;
const PERSONAL_IMAGE_MAX_DIMENSION = 2048;
const PERSONAL_IMAGE_MAX_PIXELS = 4_000_000;
const assistantAttachmentText = (value, fallback = "") => String(value || "").trim().replace(/\s+/g, " ").slice(0, 320) || fallback;

const personalImageSourceType = (file) => {
  const declared = String(file?.type || "").toLowerCase();
  if (PERSONAL_IMAGE_SOURCE_TYPES.has(declared)) return declared;
  const name = String(file?.name || "").toLowerCase();
  if (/\.jpe?g$/.test(name)) return "image/jpeg";
  if (/\.png$/.test(name)) return "image/png";
  if (/\.webp$/.test(name)) return "image/webp";
  if (/\.heic$/.test(name)) return "image/heic";
  if (/\.heif$/.test(name)) return "image/heif";
  return declared;
};

const personalImageError = (message) => {
  const error = new Error(message);
  error.name = "PersonalImageNormalizeError";
  return error;
};

const assertPersonalImageSource = (file) => {
  const type = personalImageSourceType(file);
  if (!PERSONAL_IMAGE_SOURCE_TYPES.has(type)) throw personalImageError("請選擇 JPEG、PNG、WebP 或 HEIC 圖片。");
  if (!Number(file?.size) || file.size > PERSONAL_IMAGE_SOURCE_MAX_BYTES) throw personalImageError("圖片請小於 50 MB 後再試。");
  return type;
};

const createPersonalImageCanvas = (width, height) => {
  if (typeof document === "undefined") throw personalImageError("此瀏覽器無法在本機處理圖片。");
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  return canvas;
};

const canvasToImageBlob = (canvas, type, quality) => new Promise((resolve, reject) => {
  if (typeof canvas?.toBlob !== "function") { reject(personalImageError("此瀏覽器無法在本機處理圖片。")); return; }
  canvas.toBlob((blob) => {
    if (!blob?.size) { reject(personalImageError("圖片壓縮失敗，請換一張圖片再試。")); return; }
    resolve(blob);
  }, type, quality);
});

const decodePersonalImage = async (file) => {
  if (typeof window?.createImageBitmap === "function") {
    try {
      const bitmap = await window.createImageBitmap(file, { imageOrientation: "from-image" });
      if (bitmap.width > 0 && bitmap.height > 0) return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close?.() };
      bitmap.close?.();
    } catch (error) {
      try {
        const bitmap = await window.createImageBitmap(file);
        if (bitmap.width > 0 && bitmap.height > 0) return { source: bitmap, width: bitmap.width, height: bitmap.height, close: () => bitmap.close?.() };
        bitmap.close?.();
      } catch (fallbackError) {}
    }
  }
  if (typeof Image === "undefined" || !window?.URL?.createObjectURL) throw personalImageError("此瀏覽器無法在本機處理這張圖片，請改用 JPEG、PNG 或 WebP。");
  const objectUrl = URL.createObjectURL(file);
  const image = new Image();
  image.decoding = "async";
  try {
    image.src = objectUrl;
    if (typeof image.decode === "function") await image.decode();
    else await new Promise((resolve, reject) => { image.onload = resolve; image.onerror = reject; });
    if (!image.naturalWidth || !image.naturalHeight) throw new Error("image dimensions unavailable");
    return { source: image, width: image.naturalWidth, height: image.naturalHeight, close: () => URL.revokeObjectURL(objectUrl) };
  } catch (error) {
    URL.revokeObjectURL(objectUrl);
    throw personalImageError("此瀏覽器無法在本機處理這張圖片，請改用 JPEG、PNG 或 WebP。");
  }
};

const drawPersonalImage = (source, width, height) => {
  const canvas = createPersonalImageCanvas(width, height);
  const context = canvas.getContext("2d", { alpha: false }) || canvas.getContext("2d");
  if (!context) throw personalImageError("此瀏覽器無法在本機處理圖片。");
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, width, height);
  context.imageSmoothingEnabled = true;
  if ("imageSmoothingQuality" in context) context.imageSmoothingQuality = "high";
  context.drawImage(source, 0, 0, width, height);
  return canvas;
};

const imageOutputName = (file, mimeType) => {
  const original = String(file?.name || "photo").replace(/\.[^.]+$/, "").slice(0, 72) || "photo";
  return `${original}-normalized.${mimeType === "image/webp" ? "webp" : "jpg"}`;
};

const normalizePersonalImage = async (file) => {
  assertPersonalImageSource(file);
  let decoded;
  try {
    decoded = await decodePersonalImage(file);
  } catch (error) {
    throw error?.name === "PersonalImageNormalizeError" ? error : personalImageError("此瀏覽器無法在本機處理這張圖片，請改用 JPEG、PNG 或 WebP。");
  }
  try {
    const initialScale = Math.min(1, PERSONAL_IMAGE_MAX_DIMENSION / Math.max(decoded.width, decoded.height), Math.sqrt(PERSONAL_IMAGE_MAX_PIXELS / (decoded.width * decoded.height)));
    let width = Math.max(1, Math.round(decoded.width * initialScale));
    let height = Math.max(1, Math.round(decoded.height * initialScale));
    let best = null;
    for (let pass = 0; pass < 8; pass += 1) {
      const canvas = drawPersonalImage(decoded.source, width, height);
      let smallestThisPass = null;
      for (const mimeType of ["image/webp", "image/jpeg"]) {
        for (const quality of [0.86, 0.76, 0.66, 0.56, 0.46, 0.36]) {
          let blob;
          try { blob = await canvasToImageBlob(canvas, mimeType, quality); }
          catch (error) { continue; }
          if (blob.type !== mimeType) continue;
          const candidate = { blob, mimeType, width, height };
          if (!best || candidate.blob.size < best.blob.size) best = candidate;
          if (!smallestThisPass || candidate.blob.size < smallestThisPass.blob.size) smallestThisPass = candidate;
          if (blob.size <= PERSONAL_IMAGE_UPLOAD_MAX_BYTES) {
            const name = imageOutputName(file, mimeType);
            const output = typeof File === "function" ? new File([blob], name, { type: mimeType, lastModified: Date.now() }) : blob;
            return { file: output, name, mimeType, width, height, sourceType: personalImageSourceType(file), sourceBytes: file.size };
          }
        }
      }
      if (!smallestThisPass || (width <= 320 && height <= 320)) break;
      const ratio = Math.max(0.45, Math.min(0.78, Math.sqrt(PERSONAL_IMAGE_UPLOAD_MAX_BYTES / smallestThisPass.blob.size) * 0.9));
      width = Math.max(1, Math.round(width * ratio));
      height = Math.max(1, Math.round(height * ratio));
    }
    if (!best || best.blob.size > PERSONAL_IMAGE_UPLOAD_MAX_BYTES) throw personalImageError("圖片無法在本機壓縮到 2 MB，請裁切後再試。");
    const name = imageOutputName(file, best.mimeType);
    const output = typeof File === "function" ? new File([best.blob], name, { type: best.mimeType, lastModified: Date.now() }) : best.blob;
    return { file: output, name, mimeType: best.mimeType, width: best.width, height: best.height, sourceType: personalImageSourceType(file), sourceBytes: file.size };
  } finally {
    decoded.close?.();
  }
};

const shortName = (name) => Array.from(String(name || "家"))[0] || "家";
const AVATAR_TONES = ["ink", "red", "blue", "yellow", "green", "pink"];
const AVATAR_PRESETS = ["我", "AB", "✨", "🍳", "🏠", "🌿"];
const avatarTone = (member, fallback = "") => AVATAR_TONES.includes(member?.avatar_tone) ? member.avatar_tone : fallback;
const avatarMark = (member, fallback = "家") => String(member?.avatar_value || fallback || "家").slice(0, 16);
const apiTaskToUi = (task) => ({
  id: task.id,
  title: task.title,
  note: task.note || "沒有補充說明，家人可以自由接手。",
  area: task.area || "全屋",
  createdBy: shortName(task.created_by?.display_name),
  createdByName: task.created_by?.display_name || "家人",
  createdAt: task.created_at || "剛剛",
  preferredMember: task.preferred_member?.display_name || "任何人",
  due: task.due_label || "不限",
  status: task.status,
  claimedBy: task.claimed_by ? shortName(task.claimed_by.display_name) : null,
  claimedById: task.claimed_by?.id || null,
  claimedByName: task.claimed_by?.display_name || null,
  completedBy: task.completed_by ? shortName(task.completed_by.display_name) : null,
  completedByName: task.completed_by?.display_name || null,
  completedAt: task.completed_at,
  reminder: task.my_reminder,
  version: task.version,
});
const apiEventToUi = (event) => ({
  who: shortName(event.actor?.display_name),
  text: event.text,
  time: event.created_at || "NOW",
});
const formatApiTime = (value) => {
  const raw = String(value || "");
  if (!raw) return "";
  const parsed = new Date(raw.includes("T") ? raw : `${raw.replace(" ", "T")}Z`);
  if (Number.isNaN(parsed.getTime())) return raw;
  return new Intl.DateTimeFormat("zh-Hant", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }).format(parsed);
};
const reminderIsDue = (reminder, now = new Date()) => {
  if (!reminder?.snoozed_until) return false;
  const raw = String(reminder.snoozed_until);
  const dueAt = new Date(raw.includes("T") ? raw : `${raw.replace(" ", "T")}Z`);
  return !Number.isNaN(dueAt.getTime()) && dueAt <= now;
};

const NAV = [
  ["today", "home", "今日"],
  ["items", "box", "物品"],
  ["places", "map", "位置"],
  ["ledger", "wallet", "賬本"],
  ["family", "user", "小家"],
];

const ROOMS = [
  { id: "kitchen", code: "R01", name: "廚房", pct: 92, foot: "38 件 · 今日清點" },
  { id: "living", code: "R02", name: "客廳", pct: 78, foot: "24 件 · 2 日前" },
  { id: "bath", code: "R03", name: "浴室", pct: 64, foot: "12 件 · 待補 2", alert: true },
  { id: "store", code: "R04", name: "儲物間", pct: 86, foot: "47 件 · 昨日" },
];

const INITIAL_ITEMS = [
  { id: 1, name: "洗衣液", qty: 1, unit: "瓶", safe: 2, place: "浴室 · 洗手台下", category: "清潔" },
  { id: 2, name: "AA 電池", qty: 8, unit: "粒", safe: 4, place: "儲物間 · B02", category: "耗材" },
  { id: 3, name: "意大利麵", qty: 4, unit: "包", safe: 2, place: "廚房 · 吊櫃 A", category: "食品" },
  { id: 4, name: "衛生紙", qty: 2, unit: "提", safe: 3, place: "浴室 · 高櫃", category: "日用" },
  { id: 5, name: "急救包", qty: 1, unit: "套", safe: 1, place: "客廳 · 電視櫃", category: "安全" },
];

const INITIAL_ACTIVITY = [
  { who: "慧", text: "把洗衣液移到浴室洗手台下", time: "2 MIN", tone: "red" },
  { who: "蔡", text: "記錄超市採購 ¥286.40，三人共享", time: "18 MIN" },
  { who: "安", text: "完成廚房吊櫃 A 清點", time: "1 HR", tone: "gray" },
];

const INITIAL_TASKS = [
  {
    id: 1,
    title: "衣服需要洗一下",
    note: "洗衣籃快滿了，今晚有空時幫忙啟動洗衣機。",
    area: "浴室 · 洗衣區",
    createdBy: "蔡",
    createdAt: "12 分鐘前",
    preferredMember: "任何人",
    due: "今晚",
    status: "claimed",
    claimedBy: "慧",
  },
  {
    id: 2,
    title: "貓砂需要鏟一下",
    note: "貓砂盆今天需要整理，做完記得補一點新砂。",
    area: "客廳 · 貓咪角",
    createdBy: "慧",
    createdAt: "剛剛",
    preferredMember: "任何人",
    due: "今天",
    status: "open",
  },
  {
    id: 3,
    title: "把廚房垃圾帶下樓",
    note: "廚餘和一般垃圾已經分類好。",
    area: "廚房 · 門邊",
    createdBy: "安",
    createdAt: "1 小時前",
    preferredMember: "任何人",
    due: "今天",
    status: "completed",
    completedBy: "蔡",
    completedAt: "18 分鐘前",
  },
];

const DEFAULT_SALARY = {
  type: "monthly",
  amount: 18000,
  hoursPerDay: 8,
  daysPerWeek: 5,
  payday: 10,
  startTime: "09:00",
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, Number(value) || min));

const timeParts = (value) => {
  const match = String(value || "09:00").match(/^(\d{1,2}):(\d{2})$/);
  return match ? [clamp(match[1], 0, 23), clamp(match[2], 0, 59)] : [9, 0];
};

const clockText = (seconds) => {
  const value = Math.max(0, Math.floor(seconds || 0));
  const h = String(Math.floor(value / 3600)).padStart(2, "0");
  const m = String(Math.floor((value % 3600) / 60)).padStart(2, "0");
  const s = String(value % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
};

const workdaySet = (daysPerWeek) => {
  const count = clamp(daysPerWeek, 1, 7);
  if (count === 7) return new Set([0, 1, 2, 3, 4, 5, 6]);
  return new Set(Array.from({ length: count }, (_, index) => index + 1));
};

const salarySnapshot = (config, now = new Date()) => {
  const safe = { ...DEFAULT_SALARY, ...(config || {}) };
  const monthly = safe.type === "annual" ? Number(safe.amount || 0) / 12 : Number(safe.amount || 0);
  const hours = clamp(safe.hoursPerDay, .5, 24);
  const duration = hours * 3600;
  const days = workdaySet(safe.daysPerWeek);
  const year = now.getFullYear(), month = now.getMonth(), today = now.getDate();
  const monthDays = new Date(year, month + 1, 0).getDate();
  let scheduledDays = 0, completedDays = 0;
  for (let day = 1; day <= monthDays; day += 1) {
    if (!days.has(new Date(year, month, day).getDay())) continue;
    scheduledDays += 1;
    if (day < today) completedDays += 1;
  }
  const [startHour, startMinute] = timeParts(safe.startTime);
  const startSecond = startHour * 3600 + startMinute * 60;
  const nowSecond = now.getHours() * 3600 + now.getMinutes() * 60 + now.getSeconds();
  const scheduledToday = days.has(now.getDay());
  const elapsedToday = scheduledToday ? Math.min(duration, Math.max(0, nowSecond - startSecond)) : 0;
  const workedSeconds = completedDays * duration + elapsedToday;
  const totalSeconds = Math.max(1, scheduledDays * duration);
  const ratePerSecond = monthly / totalSeconds;
  const endMinutes = (startHour * 60 + startMinute + Math.round(hours * 60)) % (24 * 60);
  const endTime = `${String(Math.floor(endMinutes / 60)).padStart(2, "0")}:${String(endMinutes % 60).padStart(2, "0")}`;
  const live = scheduledToday && nowSecond >= startSecond && nowSecond < startSecond + duration;
  const status = !scheduledToday ? "REST DAY" : nowSecond < startSecond ? `STARTS ${safe.startTime}` : live ? "LIVE" : "DAY COMPLETE";

  const payDate = (y, m) => new Date(y, m, Math.min(clamp(safe.payday, 1, 31), new Date(y, m + 1, 0).getDate()));
  const todayStart = new Date(year, month, today);
  let nextPay = payDate(year, month);
  if (nextPay < todayStart) nextPay = payDate(year, month + 1);
  const daysToPay = Math.max(0, Math.ceil((nextPay - todayStart) / 86400000));

  return {
    monthly,
    monthEarned: Math.min(monthly, workedSeconds * ratePerSecond),
    todayEarned: elapsedToday * ratePerSecond,
    hourlyRate: ratePerSecond * 3600,
    elapsedToday,
    progress: Math.min(100, workedSeconds / totalSeconds * 100),
    live,
    status,
    schedule: `${safe.startTime}–${endTime}`,
    nextPay,
    daysToPay,
    scheduledDays,
  };
};

const yuan = (n) => "¥" + Number(n || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const Avatar = ({ member, name, tone = "" }) => <span className={`avatar ${avatarTone(member, tone)}`}>{avatarMark(member, name)}</span>;

const Status = ({ children, tone = "" }) => <span className={`status-mark ${tone}`}>{children}</span>;

const SectionHead = ({ no, title, meta }) => (
  <div className="section-head">
    <div className="section-title">
      <div className="section-kicker">{no}</div>
      <h2>{title}</h2>
    </div>
    {meta && <span className="section-meta">{meta}</span>}
  </div>
);

const Folio = ({ no, en, title, sub }) => (
  <header className="home-folio">
    <div className="folio-line">{no} / {en}</div>
    <h1>{title}</h1>
    {sub && <p>{sub}</p>}
  </header>
);

const Metric = ({ label, value, unit, note, red }) => (
  <div className="home-metric">
    <div className="metric-label">{label}</div>
    <div className={`metric-value ${red ? "red" : ""}`}>{value}{unit && <small>{unit}</small>}</div>
    <div className="metric-note">{note}</div>
  </div>
);

const Presence = ({ members = [], sharedMode = true }) => {
  const shown = members.length ? members : [
    { id: "cai", display_name: "蔡培元" },
    { id: "hui", display_name: "超慧" },
    { id: "an", display_name: "安" },
  ];
  return (
  <div className="presence-row">
    <div className="presence-copy">
      <strong>{sharedMode ? `${shown.length} 位成員正在共同管理` : "你的私人空間"}</strong>
      <span>剛剛已同步</span>
    </div>
    <div className="avatar-stack" aria-label="家庭成員">
      {shown.slice(0, 4).map((member, index) => <Avatar key={member.id || member.display_name} member={member} name={shortName(member.display_name)} tone={index === 1 ? "red" : index > 1 ? "gray" : ""}/>)}
    </div>
  </div>
  );
};

const ListRow = ({ index, title, sub, right }) => (
  <div className="list-row">
    <span className="list-index">{String(index).padStart(2, "0")}</span>
    <div className="list-copy"><strong>{title}</strong><p>{sub}</p></div>
    {right}
  </div>
);

const IncomeClock = ({ config, now, openSettings }) => {
  const snapshot = salarySnapshot(config, now);
  const payLabel = `${String(snapshot.nextPay.getMonth() + 1).padStart(2, "0")}.${String(snapshot.nextPay.getDate()).padStart(2, "0")}`;
  const earnedText = yuan(snapshot.monthEarned);
  return <section className={`income-clock ${snapshot.live ? "live" : ""}`} data-testid="income-clock">
    <div className="income-top">
      <div>
        <div className="section-kicker">A / INCOME CLOCK · PRIVATE</div>
        <h2>工作收入正在累計</h2>
      </div>
      <div className="income-tools">
        <span className={`income-status ${snapshot.live ? "on" : ""}`}><i/>{snapshot.status}</span>
        <button className="income-settings" data-testid="income-settings" onClick={openSettings} aria-label="設定收入時鐘"><Icon name="gear" size={16}/></button>
      </div>
    </div>
    <div className={`income-value ${earnedText.length > 11 ? "compact" : ""}`} data-testid="income-amount" aria-live="off">{earnedText}</div>
    <div className="income-facts">
      <span>今日 <strong>{yuan(snapshot.todayEarned)}</strong></span>
      <span>每小時 <strong>{yuan(snapshot.hourlyRate)}</strong></span>
      <span>已工作 <strong>{clockText(snapshot.elapsedToday)}</strong></span>
    </div>
    <div className="income-progress"><i style={{ width: snapshot.progress + "%" }}/></div>
    <div className="income-foot">
      <span>{snapshot.schedule} · 每週 {config.daysPerWeek} 天</span>
      <span>發薪 {payLabel} · {snapshot.daysToPay === 0 ? "今天" : `${snapshot.daysToPay} 天後`}</span>
    </div>
  </section>;
};

const memberTone = (name) => name === "慧" ? "red" : name === "安" ? "gray" : "";

const ChoreCard = ({ task, currentUser, currentUserId, onAction, onRemind, celebrating, compact = false }) => {
  const open = task.status === "open";
  const claimed = task.status === "claimed";
  const completed = task.status === "completed";
  const mine = task.claimedById ? task.claimedById === currentUserId : task.claimedBy === currentUser;
  const reminderDue = reminderIsDue(task.reminder);
  const status = completed ? "DONE" : claimed ? "IN HAND" : "OPEN";
  const response = completed
    ? `${task.completedBy} 完成了 · ${task.completedAt || "剛剛"}`
    : claimed
      ? `${task.claimedBy} 已接手 · 正在處理`
      : task.reminder
        ? (reminderDue ? `提醒時間到了 · ${task.reminder.label}` : `已延後至 ${formatApiTime(task.reminder.snoozed_until)} · 任務仍保持可處理`)
        : "還沒有人接手";

  return <article
    className={`chore-card ${compact ? "compact" : ""} ${completed ? "is-complete" : ""} ${celebrating ? "just-completed" : ""}`}
    data-testid={`chore-${task.id}`}
    data-state={task.status}
    data-snoozed={task.reminder ? "true" : "false"}
  >
    <div className="chore-head">
      <div className="chore-author">
        <Avatar name={task.createdBy} tone={memberTone(task.createdBy)}/>
        <div><strong>{task.createdBy} 發佈</strong><span>{task.createdAt} · 希望{task.due}完成</span></div>
      </div>
      <Status tone={completed ? "ok" : ""}>{status}</Status>
    </div>
    <div className="chore-copy">
      <h3>{task.title}</h3>
      <p>{task.note}</p>
      <span className="chore-place"><Icon name="map" size={12}/>{task.area} · {task.preferredMember === "任何人" ? "任何人可接" : `希望${task.preferredMember}處理`}</span>
    </div>
    <div className={`chore-response ${completed ? "done" : ""}`} aria-live="polite">
      <Icon name={completed ? "checkCircle" : claimed ? "user" : "clock"} size={14}/>
      <span>{response}</span>
    </div>
    {!completed && <div className={`chore-actions ${claimed && !mine ? "single" : ""}`}>
      {(!claimed || mine) && <button className="chore-action quiet" data-testid={`chore-wait-${task.id}`} onClick={() => onRemind(task.id)}>
        <Icon name="clock" size={14}/><span>{task.reminder ? (reminderDue ? "再次提醒" : "改提醒") : "等一下"}</span>
      </button>}
      {open && <button className="chore-action claim" data-testid={`chore-claim-${task.id}`} onClick={() => onAction(task.id, "claim")}>
        <Icon name="user" size={14}/><span>我來做</span>
      </button>}
      {(open || mine) && <button className="chore-action complete" data-testid={`chore-complete-${task.id}`} onClick={() => onAction(task.id, "complete")}>
        <Icon name="check" size={14}/><span>完成</span>
      </button>}
      {claimed && !mine && <div className="chore-in-hand"><Icon name="checkCircle" size={14}/><span>{task.claimedBy}正在處理，完成後會通知全家。</span></div>}
    </div>}
  </article>;
};

const HouseholdProgress = ({ tasks }) => {
  const weekStart = new Date();
  const weekday = weekStart.getDay() || 7;
  weekStart.setHours(0, 0, 0, 0);
  weekStart.setDate(weekStart.getDate() - weekday + 1);
  const weekDone = tasks.filter((task) => {
    if (task.status !== "completed" || !task.completedAt) return false;
    const raw = String(task.completedAt);
    const completedAt = new Date(raw.includes("T") ? raw : `${raw.replace(" ", "T")}Z`);
    return !Number.isNaN(completedAt.getTime()) && completedAt >= weekStart;
  }).length;
  const goal = Math.max(5, tasks.filter((task) => task.status !== "completed").length + weekDone);
  return <section className="house-progress" data-testid="household-progress">
    <div className="house-progress-copy">
      <div><span className="section-kicker">THIS WEEK / TOGETHER</span><h2>這週一起完成的家務</h2></div>
      <strong>{weekDone}<small> / {goal}</small></strong>
    </div>
    <div className="house-progress-track"><i style={{ width: Math.min(100, weekDone / goal * 100) + "%" }}/></div>
    <p>只記錄小家的共同進度，不比較每個人做了多少。</p>
  </section>;
};

const CompletionMoment = ({ achievement }) => {
  if (!achievement) return null;
  return <div className="completion-moment" data-testid="chore-achievement" role="status" aria-live="assertive">
    <div className="completion-rail"><i/><i/><i/></div>
    <div className="completion-index">HOUSE +01</div>
    <div className="completion-copy"><strong>小家共同完成一件事</strong><span>{achievement.completedBy === achievement.createdBy ? `${achievement.completedBy}把這件事安排妥當` : `${achievement.completedBy}接住了${achievement.createdBy}的需要`} · {achievement.title}</span></div>
    <Icon name="checkCircle" size={24}/>
  </div>;
};

const nestedLocationIds = (locations, rootId) => {
  const ids = new Set(rootId == null ? [] : [rootId]);
  let changed = true;
  while (changed) {
    changed = false;
    locations.forEach((location) => {
      if (!ids.has(location.id) && ids.has(location.parent_id)) {
        ids.add(location.id);
        changed = true;
      }
    });
  }
  return ids;
};

const LOCATION_TYPES = [
  ["room", "房間", "room", null],
  ["cabinet", "櫃子", "facility", "cabinet"],
  ["fridge", "冰箱", "facility", "fridge"],
  ["freezer", "冷凍櫃", "facility", "freezer"],
  ["table", "桌子", "facility", "table"],
  ["pantry", "食品櫃", "facility", "pantry"],
  ["shelf", "層板", "shelf", null],
];
const locationTypeMeta = (location) => {
  if (location?.kind === "room") return { label: "房間", icon: "home" };
  if (location?.kind === "shelf") return { label: "層板", icon: "layers" };
  const label = LOCATION_TYPES.find((entry) => entry[3] === location?.facility_type)?.[1] || "設施";
  return { label, icon: location?.facility_type === "fridge" || location?.facility_type === "freezer" ? "clock" : "box" };
};
const locationDepth = (location, locations, roomId) => {
  const byId = new Map(locations.map((entry) => [entry.id, entry]));
  let depth = 0;
  let current = location;
  const seen = new Set();
  while (current?.parent_id && current.parent_id !== roomId && !seen.has(current.parent_id)) {
    seen.add(current.parent_id);
    current = byId.get(current.parent_id);
    depth += 1;
  }
  return Math.min(depth, 4);
};
const ingredientText = (ingredient) => typeof ingredient === "string" ? ingredient : ingredient?.name || ingredient?.title || "";
const recipeList = (recipe, field) => (Array.isArray(recipe?.[field]) ? recipe[field] : []).map(ingredientText).filter(Boolean);
const recipeUseFirstList = (recipe, items) => (Array.isArray(recipe?.use_first) ? recipe.use_first : []).filter((ingredient) => {
  if (!ingredient || typeof ingredient === "string" || ingredient.batch_id == null) return true;
  const batch = items.find((item) => item.id === ingredient.batch_id);
  return batch && batch.qty > 0 && batch.expiry_status !== "expired";
}).map((ingredient) => {
  const name = ingredientText(ingredient);
  if (!name || typeof ingredient === "string" || ingredient.days_to_expiry == null) return name;
  const days = Number(ingredient.days_to_expiry);
  if (!Number.isFinite(days)) return name;
  return days === 0 ? `${name}（今天到期）` : days > 0 ? `${name}（${days} 天內到期）` : name;
}).filter(Boolean);
const localDateInput = (value = new Date(), timezoneName = "") => {
  const dateOnly = typeof value === "string" ? value.match(/^(\d{4}-\d{2}-\d{2})(?:$|[ T])/) : null;
  if (dateOnly) return dateOnly[1];
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  if (timezoneName) {
    try {
      const parts = new Intl.DateTimeFormat("en-CA", { timeZone: timezoneName, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
      const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
      if (byType.year && byType.month && byType.day) return `${byType.year}-${byType.month}-${byType.day}`;
    } catch (_error) {
      // Fall through to the device-local date when an old browser rejects the IANA zone.
    }
  }
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
};
const localDatePlusDays = (dateText, days, timezoneName = "") => {
  const fallback = localDateInput(new Date(), timezoneName);
  const parts = String(dateText || fallback).match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const amount = Math.max(0, Math.min(3650, Math.floor(Number(days) || 0)));
  if (!parts || !amount) return parts ? dateText : fallback;
  const date = new Date(Number(parts[1]), Number(parts[2]) - 1, Number(parts[3]), 12, 0, 0);
  date.setDate(date.getDate() + amount);
  return localDateInput(date, timezoneName);
};
const foodStatusMeta = (item) => {
  if (item?.expiry_status === "expired") return { code: "EXPIRED", label: "已過期／不要食用", tone: "expired" };
  if (item?.expiry_status === "soon") {
    const days = Math.max(0, Number(item.days_to_expiry) || 0);
    return { code: "SOON", label: days === 0 ? "今天到期" : `還有 ${days} 天`, tone: "soon" };
  }
  if (item?.expiry_status === "none") return {
    code: "NO EXPIRY",
    label: item?.stored_at ? `已存放 ${Math.max(0, Number(item.stored_days) || 0)} 天／未設到期日` : "未設存放與到期日",
    tone: "tracked",
  };
  return { code: "FRESH", label: `已存放 ${Math.max(0, Number(item?.stored_days) || 0)} 天`, tone: "fresh" };
};

const TodayView = ({ items, locations, activity, tasks, members, currentUserId, currentUserShort, currentUserName, sharedMode, openAction, openFamily, taskAction, selectedRoom, selectRoom, salaryConfig, now }) => {
  const low = items.filter((i) => i.qty < i.safe).length;
  const located = items.filter((item) => item.location_id || (item.place && item.place !== "未指定位置")).length;
  const locatedPct = items.length ? Math.round(located / items.length * 100) : 0;
  const activeTasks = tasks.filter((task) => task.status !== "completed");
  const rooms = locations.filter((location) => location.kind === "room");
  const featuredTask = activeTasks.find((task) => task.status === "open") || activeTasks[0];
  const pending = activeTasks.length;
  return <div className="home-view personal-rise">
    <Folio no="01" en="TODAY" title={<>晚上好，{currentUserName}。<br/>{sharedMode ? "小家" : "今天"}有 {pending} 件事待完成。</>} sub={sharedMode ? "先看看家人的需要，再處理今天真正重要的事。" : "先整理自己的生活，也可以隨時邀請家人加入。"}/>
    <Presence members={members} sharedMode={sharedMode}/>
    <section className="home-band collaboration-band">
      <SectionHead no="A / TOGETHER" title={sharedMode ? "家人需要你回應" : "我的生活待辦"} meta={`${activeTasks.length} ACTIVE`}/>
      {featuredTask && <ChoreCard task={featuredTask} currentUser={currentUserShort} currentUserId={currentUserId} compact onAction={taskAction} onRemind={(id) => openAction("reminder", { taskId: id })}/>}
      <div className="collaboration-footer">
        <button className="text-action" data-testid="household-publish" onClick={() => openAction("task")}><Icon name="plus" size={14}/>{sharedMode ? "發一件家務" : "新增生活待辦"}</button>
        <button className="text-action primary" onClick={openFamily}>查看全部 {activeTasks.length} 件<Icon name="arrow" size={14}/></button>
      </div>
    </section>
    <IncomeClock config={salaryConfig} now={now} openSettings={() => openAction("salary")}/>
    <div className="metric-grid three">
      <Metric label="ITEMS / 在管物品" value={items.length} unit="筆" note={items.length ? "已同步到目前空間" : "從掃描新增第一筆"}/>
      <Metric label="PLACE / 已歸位" value={locatedPct} unit="%" note={`${items.length - located} 筆尚未定位`}/>
      <Metric label="LOW / 待補貨" value={low} unit="件" note={low ? (sharedMode ? "需要家庭成員留意" : "記得安排補貨") : "目前庫存安靜"} red={low > 0}/>
    </div>

    <section className="home-band">
      <SectionHead no="B / QUICK LOG" title="快速記錄" meta="一擊完成 · 可撤銷"/>
      <div className="quick-grid" data-testid="quick-add">
        {[
          ["expense", "wallet", "記一筆"],
          ["item", "outbound", "取用"],
          ["move", "swap", "移位置"],
          ["scan", "scan", "掃一掃"],
        ].map(([id, icon, label]) => (
          <button key={id} className="quick-action" data-testid={`quick-${id}`} onClick={() => openAction(id)}>
            <span className="quick-icon"><Icon name={icon} size={17}/></span>
            <span>{label}</span>
          </button>
        ))}
      </div>
    </section>

    <section className="home-band">
      <SectionHead no="C / HOME MAP" title="小家地圖" meta={`${rooms.length} ROOMS`}/>
      {rooms.length ? <div className="room-grid">
        {rooms.map((room) => {
          const roomIds = nestedLocationIds(locations, room.id);
          const count = items.filter((item) => roomIds.has(item.location_id)).length;
          return <button key={room.id} className={`room-cell ${selectedRoom === room.id ? "on" : ""}`} onClick={() => selectRoom(room.id)}>
            <span className="room-code">{room.code || `R${room.id}`}</span>
            <div className="room-name">{room.name}</div>
            <div className="room-value">{count}</div>
            <div className="room-foot">筆庫存記錄</div>
            <i className="room-rule" style={{ width: items.length ? Math.max(4, count / items.length * 100) + "%" : "0%" }}/>
          </button>;
        })}
      </div> : <div className="empty-band">建立房間後，小家地圖會出現在這裏。</div>}
    </section>

    <section className="home-band">
      <SectionHead no="D / LIVE" title={sharedMode ? "家庭動態" : "我的動態"} meta="LIVE SYNC"/>
      {activity.length ? <div className="list">
        {activity.slice(0, 4).map((a, i) => <ListRow key={i} index={i + 1} title={`${a.who} · ${a.text}`} sub="已寫入家庭活動記錄" right={<span className="list-meta">{a.time}</span>}/>) }
      </div> : <div className="empty-band">第一個家庭操作完成後，動態會出現在這裏。</div>}
    </section>
  </div>;
};

const RECIPE_GOALS = [
  ["balanced", "均衡", "BALANCED"],
  ["fat_loss", "減脂", "FAT LOSS"],
  ["high_calorie", "高熱量", "HIGH ENERGY"],
];
const RECIPE_MODES = [
  ["inventory_first", "優先用現有"],
  ["flexible", "可補食材"],
];

const ItemsView = ({ items, recipes = [], plannedRecipes = [], changeItem, openAction, sharedMode, workspaceId, planRecipes }) => {
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const [recipeGoal, setRecipeGoal] = useState("balanced");
  const [recipeMode, setRecipeMode] = useState("inventory_first");
  const [recipeServings, setRecipeServings] = useState(2);
  const [recipeNote, setRecipeNote] = useState("");
  const [recipeBusy, setRecipeBusy] = useState(false);
  const [recipeError, setRecipeError] = useState("");
  const [recipeMeta, setRecipeMeta] = useState(null);
  const safeFoods = items.filter((item) => item.is_food && item.qty > 0 && item.expiry_status !== "expired");
  const cookFirstRecipes = safeFoods.length ? recipes.map((recipe) => ({
    ...recipe,
    safeMatched: recipeList(recipe, "matched_ingredients"),
  })).filter((recipe) => recipe.safeMatched.length).slice(0, 4) : [];
  const plannedRecipeResults = plannedRecipes.map((recipe) => ({
    ...recipe,
    safeMatched: recipeList(recipe, "matched_ingredients"),
  })).slice(0, 4);
  const requestRecipePlan = async () => {
    if (recipeBusy || typeof planRecipes !== "function") return;
    setRecipeBusy(true);
    setRecipeError("");
    try {
      const response = await planRecipes({
        workspace_id: workspaceId,
        goal: recipeGoal,
        mode: recipeMode,
        servings: Number(recipeServings),
        note: recipeNote.trim(),
      });
      setRecipeMeta({ goal: response?.goal || recipeGoal, mode: response?.mode || recipeMode });
    } catch (requestError) {
      setRecipeError(requestError.message || "暫時無法安排食譜，請再試一次。");
    } finally {
      setRecipeBusy(false);
    }
  };
  const renderRecipeRow = (recipe, index, prefix = "") => {
    const missing = recipeList(recipe, "missing_ingredients");
    const shopping = recipeList(recipe, "shopping_list");
    const useFirst = recipeUseFirstList(recipe, items);
    return <button className="recipe-row" key={`${prefix}${recipe.id || `${recipe.title}-${index}`}`} onClick={() => openAction("recipe", { recipeId: recipe.id, recipe })}>
      <span className="recipe-index">{String(index + 1).padStart(2, "0")}</span>
      <span className="recipe-copy">
        <span className="recipe-flags">{useFirst.length > 0 && <b>USE FIRST</b>}<i>{Number(recipe.minutes) || 20} MIN</i></span>
        <strong>{recipe.title}</strong>
        <span className="recipe-reason">{recipe.reason || "利用家中現有食材，減少浪費。"}</span>
        <span className="recipe-stock"><em>已備 {recipe.safeMatched.join("、") || "依方案準備"}</em>{missing.length > 0 && <em>缺 {missing.join("、")}</em>}</span>
        {shopping.length > 0 && <span className="recipe-shopping">SHOPPING · {shopping.join("、")}</span>}
      </span>
      <Icon name="chevron" size={15}/>
    </button>;
  };
  const shown = items.filter((i) => {
    const hit = !query || `${i.name}${i.place}${i.category}`.toLowerCase().includes(query.toLowerCase());
    return hit && (filter === "all" || (filter === "low" && i.qty < i.safe) || (filter === "placed" && !!i.location_id) || (filter === "food" && i.is_food));
  }).sort((a, b) => {
    if (!!a.is_food !== !!b.is_food) return a.is_food ? -1 : 1;
    if (!a.is_food) return 0;
    const expiredDelta = Number(b.expiry_status === "expired") - Number(a.expiry_status === "expired");
    if (expiredDelta) return expiredDelta;
    if (!a.expires_at && !b.expires_at) return 0;
    if (!a.expires_at) return 1;
    if (!b.expires_at) return -1;
    return String(a.expires_at).localeCompare(String(b.expires_at));
  });
  return <div className="home-view personal-rise">
    <Folio no="02" en="ITEMS" title="每件東西，都知道自己在哪裏。" sub={`${items.length} 筆庫存記錄 · ${items.filter(i => i.qty < i.safe).length} 筆低於安全存量`}/>
    <section className="recipe-band" data-testid="recipe-suggestions">
      <SectionHead no="A / COOK FIRST" title="在食材變質前，先做一頓好吃的" meta={`${cookFirstRecipes.length} RECIPES`}/>
      {cookFirstRecipes.length ? <div className="recipe-list">
        {cookFirstRecipes.map((recipe, index) => renderRecipeRow(recipe, index, "cook-first-"))}
      </div> : <div className="recipe-empty">
        <Icon name={items.some((item) => item.is_food && item.expiry_status === "expired") ? "alert" : "sparkle"} size={18}/>
        <div><strong>{safeFoods.length ? "暫時沒有合適食譜" : "冰箱裏還沒有安全可用的食材"}</strong><span>{safeFoods.length ? "補充食材或更新存量後，管家會重新分析。" : "已過期食材不會用於食譜推薦；入庫新鮮食材後再來看看。"}</span></div>
      </div>}
      <div className="recipe-planner" data-testid="recipe-planner">
        <div className="recipe-plan-title"><span className="field-label">B / YOUR PLAN</span><strong>不只限於冰箱裏現有的食材。</strong></div>
        <div className="recipe-planner-head"><span className="field-label">GOAL / 飲食目標</span><span>{safeFoods.length} SAFE INGREDIENTS</span></div>
        <div className="recipe-goal-grid">{RECIPE_GOALS.map(([value, label, en]) => <button type="button" key={value} data-testid={`recipe-goal-${value}`} className={recipeGoal === value ? "on" : ""} onClick={() => setRecipeGoal(value)}><strong>{label}</strong><small>{en}</small></button>)}</div>
        <div className="recipe-plan-options">
          <div><span className="field-label">MODE / 食材範圍</span><div className="recipe-mode-control">{RECIPE_MODES.map(([value, label]) => <button type="button" key={value} className={recipeMode === value ? "on" : ""} onClick={() => setRecipeMode(value)}>{label}</button>)}</div></div>
          <div><span className="field-label">SERVES / 份數</span><div className="recipe-serving-control">{[1, 2, 4].map((value) => <button type="button" key={value} className={Number(recipeServings) === value ? "on" : ""} onClick={() => setRecipeServings(value)}>{value}</button>)}</div></div>
        </div>
        <label className="recipe-note"><span className="field-label">NOTE / 偏好（選填）</span><textarea value={recipeNote} maxLength="160" onChange={(event) => setRecipeNote(event.target.value)} placeholder="例如：20 分鐘內完成、不吃香菜" aria-label="食譜偏好"/></label>
        <button type="button" className="recipe-plan-submit" data-testid="recipe-plan-submit" onClick={requestRecipePlan} disabled={recipeBusy || typeof planRecipes !== "function"}><Icon name="sparkle" size={15}/><span>{recipeBusy ? "正在安排…" : "安排這一餐"}</span><i>{recipeMode === "flexible" ? "可列出需要補充的食材" : "優先使用現有食材"}</i></button>
        {recipeMeta && <div className="recipe-plan-meta"><Icon name="checkCircle" size={14}/><span>{RECIPE_GOALS.find(([value]) => value === recipeMeta.goal)?.[1] || "均衡"} · {recipeMeta.mode === "flexible" ? "可補食材方案" : "優先現有食材方案"}</span></div>}
        {recipeError && <div className="recipe-plan-error" role="alert"><Icon name="alert" size={14}/><span>{recipeError}</span></div>}
        {plannedRecipeResults.length > 0 && <div className="recipe-plan-results"><div className="recipe-plan-results-head"><span>PLAN RESULTS / 本次建議</span><b>{plannedRecipeResults.length} RECIPES</b></div>{plannedRecipeResults.map((recipe, index) => renderRecipeRow(recipe, index, "planned-"))}</div>}
      </div>
    </section>
    <div className="tool-row">
      <label className="search-box"><Icon name="search" size={15}/><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="搜尋物品或位置"/></label>
      {[['all','全部'],['food','食材'],['low','待補'],['placed','已定位']].map(([id,label]) => <button key={id} className={`filter-button ${filter === id ? "on" : ""}`} onClick={() => setFilter(id)}>{label}</button>)}
    </div>
    <SectionHead no="B / INVENTORY" title={sharedMode ? "家庭物品" : "我的物品"} meta={`${shown.length} RESULTS`}/>
    <div>
      {shown.map((item) => {
        const low = item.qty < item.safe;
        const foodStatus = item.is_food ? foodStatusMeta(item) : null;
        return <div key={item.id} className={`item-row ${low ? "low" : ""} ${foodStatus?.tone === "expired" ? "food-expired" : ""}`}>
          <div className="item-main">
            <h3>{item.name}</h3>
            {(item.brand || item.package_size) && <div className="item-product-meta">{[item.brand, item.package_size].filter(Boolean).join(" · ")}</div>}
            <p><Icon name="map" size={11}/> {item.place}</p>
            <div className="item-tags"><Status>{item.category}</Status>{item.is_food && <Status>BATCH</Status>}{low && <Status tone="red">LOW {item.safe}</Status>}{foodStatus && <span className={`food-status ${foodStatus.tone}`}><b>{foodStatus.code}</b> · {foodStatus.label}</span>}</div>
          </div>
          <div className="item-controls">
            {item.is_food && <button className="food-edit" title="編輯存放與到期日期" aria-label={`編輯${item.name}保鮮資料`} onClick={() => openAction("food", { itemId: item.id })}><Icon name="clock" size={15}/></button>}
            <div className="qty-control" aria-label={`${item.name}數量`}>
              <button disabled={item.qty <= 0} title={foodStatus?.tone === "expired" ? `丟棄整批${item.name}` : `減少${item.name}`} aria-label={foodStatus?.tone === "expired" ? `丟棄整批${item.name}` : `減少${item.name}`} onClick={() => changeItem(item.id, foodStatus?.tone === "expired" ? -item.qty : -Math.min(1, item.qty), false, foodStatus?.tone === "expired" ? "discard" : "consume")}>−</button>
              <strong>{item.qty}</strong>
              <button title={item.is_food ? "新增一批同款食材" : `增加${item.name}`} aria-label={item.is_food ? `新增一批${item.name}` : `增加${item.name}`} onClick={() => item.is_food ? openAction("scan", { itemId: item.id }) : changeItem(item.id, 1)}>+</button>
            </div>
          </div>
        </div>;
      })}
      {!shown.length && <div className="place-detail"><h3>沒有符合的物品</h3><p className="sheet-copy">換一個關鍵詞或查看全部物品。</p></div>}
    </div>
    <div style={{ padding: 18 }}><button className="text-action primary" style={{ width: "100%", minHeight: 46 }} onClick={() => openAction("scan")}><Icon name="scan" size={14}/>掃描新增物品</button></div>
  </div>;
};

const PlacesView = ({ selectedRoom, selectRoom, items, locations, openAction }) => {
  const rooms = locations.filter((location) => location.kind === "room");
  const room = rooms.find((entry) => entry.id === selectedRoom) || rooms[0];
  const roomIds = room ? nestedLocationIds(locations, room.id) : new Set();
  const roomItems = room ? items.filter((item) => roomIds.has(item.location_id)) : [];
  const roomLocations = room ? locations.filter((location) => location.id !== room.id && roomIds.has(location.id)).sort((a, b) => (a.path || a.name).localeCompare(b.path || b.name, "zh-Hant")) : [];
  const located = items.filter((item) => item.location_id).length;
  const locatedPct = items.length ? Math.round(located / items.length * 100) : 0;
  return <div className="home-view personal-rise">
    <Folio no="03" en="PLACES" title="不是找東西，是直接知道它在哪裏。" sub="家 → 房間 → 櫃子 → 層板，逐級定位。"/>
    <div className="place-summary">
      <div><h2>位置完成度</h2><p>{located} / {items.length} 筆庫存已有明確收納點</p></div>
      <div className="big-percent">{locatedPct}%</div>
    </div>
    <SectionHead no="A / ROOMS" title="選擇房間" meta="TAP TO INSPECT"/>
    {rooms.length ? <div className="room-grid">
      {rooms.map((entry) => {
        const ids = nestedLocationIds(locations, entry.id);
        const count = items.filter((item) => ids.has(item.location_id)).length;
        return <button key={entry.id} className={`room-cell ${selectedRoom === entry.id ? "on" : ""}`} onClick={() => selectRoom(entry.id)}>
          <span className="room-code">{entry.code || `R${entry.id}`}</span><div className="room-name">{entry.name}</div><div className="room-value">{count}</div><div className="room-foot">筆庫存記錄</div><i className="room-rule" style={{ width: items.length ? Math.max(4, count / items.length * 100) + "%" : "0%" }}/>
        </button>;
      })}
    </div> : <div className="empty-band">目前空間還沒有房間。</div>}
    <div className="place-create-bar"><button className="text-action" onClick={() => openAction("location")}><Icon name="plus" size={14}/>新增房間</button></div>
    {room && <>
      <SectionHead no="B / HIERARCHY" title={`${room.name}的設施`} meta={`${roomLocations.length} PLACES`}/>
      <div className="place-detail">
        <div className="place-path">HOME / {room.code || `R${room.id}`}</div>
        <div className="place-parent-actions"><button className="text-action" onClick={() => openAction("location", { locationId: room.id })}><Icon name="plus" size={14}/>在房間內新增設施</button></div>
        {roomLocations.length ? <div className="location-tree">
          {roomLocations.map((location) => {
            const meta = locationTypeMeta(location);
            const directItems = items.filter((item) => item.location_id === location.id).length;
            return <div className="location-node" key={location.id} style={{ "--location-depth": locationDepth(location, locations, room.id) }}>
              <span className="location-node-icon"><Icon name={meta.icon} size={15}/></span>
              <span className="location-node-copy"><b>{location.name}</b><small>{meta.label} · {location.path}{directItems ? ` · ${directItems} 件` : ""}</small></span>
              {(location.kind === "facility" || location.kind === "room") && <button className="location-add" title={`在${location.name}內新增`} aria-label={`在${location.name}內新增位置`} onClick={() => openAction("location", { locationId: location.id })}><Icon name="plus" size={14}/></button>}
            </div>;
          })}
        </div> : <div className="empty-sheet">這個房間還沒有櫃子、冰箱或其他設施。</div>}
        <h3 className="place-items-title">這裏的物品</h3>
        {roomItems.length ? <div className="place-slots">
          {roomItems.slice(0, 6).map((item, index) => <div className="place-slot" key={item.id}><span>ITEM {String(index + 1).padStart(2, "0")}</span><strong>{item.name}</strong><small>{item.place}</small></div>)}
        </div> : <div className="empty-sheet">還沒有物品放在這個房間。</div>}
        <div className="sheet-actions"><button className="text-action" onClick={() => openAction("location", { locationId: room.id })}><Icon name="plus" size={14}/>新增設施</button><button className="text-action primary" onClick={() => openAction("move", { locationId: room.id })} disabled={!items.length}><Icon name="swap" size={14}/>移動到這裏</button></div>
      </div>
    </>}
    {!room && <div style={{ padding: 18 }}><button className="text-action primary" style={{ width: "100%", minHeight: 46 }} onClick={() => openAction("location")}><Icon name="plus" size={14}/>建立第一個房間</button></div>}
  </div>;
};

const LedgerView = ({ spend, entries, openAction, sharedMode }) => {
  const monthEntries = entries || [];
  const payerTotals = Object.values(monthEntries.reduce((totals, entry) => {
    const key = entry.paid_by?.id || entry.paid_by?.display_name;
    totals[key] = totals[key] || { name: entry.paid_by?.display_name || "家人", amount: 0 };
    totals[key].amount += Number(entry.amount || 0);
    return totals;
  }, {})).sort((a, b) => b.amount - a.amount);
  return <div className="home-view personal-rise">
    <Folio no="04" en="LEDGER" title={sharedMode ? "家庭花費清楚，但不製造壓力。" : "自己的花費，也值得清楚掌握。"} sub={sharedMode ? "本月共同賬本 · 所有分攤都有來源和操作者。" : "本月私人賬本 · 只在你的私人空間內可見。"}/>
    <div className="ledger-hero">
      <div className="folio-line">THIS MONTH / SHARED SPEND</div>
      <div className="ledger-total"><small>¥</small>{Number(spend).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
      <div className="ledger-note">{monthEntries.length} 筆已同步開銷 · 金額精確到分</div>
      <button className="text-action primary" style={{ width: "100%", minHeight: 46, marginTop: 15 }} onClick={() => openAction("expense")}><Icon name="plus" size={14}/>記一筆{sharedMode ? "家庭" : "私人"}開銷</button>
    </div>
    <SectionHead no="A / PAID BY" title="誰先墊付" meta="THIS MONTH"/>
    {payerTotals.length ? <div className="bar-list">
      {payerTotals.map((payer, index) => {
        const pct = spend ? Math.round(payer.amount / spend * 100) : 0;
        return <div className="bar-row" key={payer.name}><div className="bar-copy"><span>{payer.name}</span><span>{yuan(payer.amount)} · {pct}%</span></div><div className="bar-track"><div className={`bar-fill ${index === 1 ? "red" : index > 1 ? "gray" : ""}`} style={{ width: pct + "%" }}/></div></div>;
      })}
    </div> : <div className="empty-band">還沒有共同開銷。</div>}
    <SectionHead no="B / RECENT" title="最近明細" meta="AUDITED"/>
    {monthEntries.length ? <div className="list">
      {monthEntries.slice(0, 8).map((entry, index) => <ListRow key={entry.id} index={index + 1} title={entry.title} sub={`${entry.category || "其他"} · ${entry.paid_by?.display_name || "本人"}記錄 · ${entry.shares?.length || 1} 人分攤 · ${formatApiTime(entry.happened_at)}`} right={<strong className="num">{yuan(entry.amount)}</strong>}/>) }
    </div> : <div className="empty-band">記錄第一筆開銷後，分攤明細會出現在這裏。</div>}
  </div>;
};

const FamilyView = ({ activity, tasks, members, currentUser, currentUserId, currentUserShort, currentWorkspace, taskAction, openAction, celebratingTaskId }) => {
  const sharedMode = currentWorkspace?.type === "household";
  const completed = tasks.filter((task) => task.status === "completed").length;
  return <div className="home-view personal-rise">
    <Folio no="05" en="HOUSEHOLD" title={sharedMode ? "家務不是命令，是讓彼此接住生活。" : "先整理自己的生活，再邀請重要的人加入。"} sub={sharedMode ? "發出需要、溫柔回應、一起完成；每一步都讓全家知道。" : "私人待辦只對你可見；建立或加入小家後即可共同協作。"}/>
    <Presence members={members} sharedMode={sharedMode}/>
    {!sharedMode && <div className="task-publish-wrap"><button className="text-action" onClick={() => openAction("household")}><Icon name="home" size={14}/>建立一個小家</button><button className="text-action primary" onClick={() => openAction("join")}><Icon name="plus" size={14}/>加入現有小家</button></div>}
    <SectionHead no="A / PERSONAL MARK" title="我的頭像" meta="IDENTITY"/>
    <div className="avatar-profile-row">
      <Avatar member={currentUser} name={shortName(currentUser?.display_name)} />
      <div><strong>{currentUser?.display_name || "我"}</strong><span>在你的私人空間與小家中同步顯示</span></div>
      <button className="avatar-edit-button" onClick={() => openAction("avatar")} aria-label="設計我的頭像" title="設計我的頭像"><Icon name="gear" size={16}/></button>
    </div>
    <HouseholdProgress tasks={tasks}/>

    <SectionHead no="B / HOUSE REQUESTS" title="生活協作" meta={`${completed} DONE · ${tasks.length - completed} ACTIVE`}/>
    <div className="task-publish-wrap">
      <button className="text-action primary" data-testid="task-add" onClick={() => openAction("task")}><Icon name="plus" size={14}/>{sharedMode ? "發佈一件家務" : "新增一件待辦"}</button>
    </div>
    <div className="chore-list" data-testid="chore-list">
      {tasks.map((task) => <ChoreCard
        key={task.id}
        task={task}
        currentUser={currentUserShort}
        currentUserId={currentUserId}
        onAction={taskAction}
        onRemind={(id) => openAction("reminder", { taskId: id })}
        celebrating={celebratingTaskId === task.id}
      />)}
      {!tasks.length && <div className="empty-band">還沒有家務。發出第一個生活請求，家人就能回應。</div>}
    </div>

    <SectionHead no="C / MEMBERS" title={sharedMode ? "家庭成員" : "目前成員"} meta={`${members.length} ACTIVE`}/>
    <div>
      {members.map((member, index) => <div className="member-row" key={member.id}><Avatar member={member} name={shortName(member.display_name)} tone={index === 1 ? "red" : index > 1 ? "gray" : ""}/><div className="member-copy"><strong>{member.display_name}</strong><span>{String(member.role || "member").toUpperCase()} · {sharedMode ? "家庭成員" : "私人空間"}</span></div><Status tone="ok">ACTIVE</Status></div>)}
    </div>
    {currentWorkspace?.type === "household" && currentWorkspace?.role === "owner" && <div className="member-invite"><button className="text-action" onClick={() => openAction("invite")}><Icon name="plus" size={14}/>邀請家庭成員</button></div>}

    <SectionHead no="D / ACTIVITY" title="共同記錄" meta="TRACEABLE"/>
    <div className="list" data-testid="activity-feed">
      {activity.slice(0, 7).map((a, i) => <ListRow key={`${a.time}-${i}`} index={i+1} title={`${a.who} · ${a.text}`} sub={`${sharedMode ? "家庭" : "私人"}空間 · 可追溯`} right={<span className="list-meta">{a.time}</span>}/>) }
    </div>
  </div>;
};

const assistantText = (value) => {
  if (typeof value === "string") return value;
  if (Array.isArray(value)) return value.map(assistantText).filter(Boolean).join("\n");
  if (!value || typeof value !== "object") return "";
  return assistantText(value.text || value.content || value.message || value.output || value.result || value.final || value.payload);
};

const assistantActionResultText = (response) => {
  const result = response?.result || response?.action?.result || null;
  const invite = result?.invite;
  if (invite?.code) {
    return `### 家庭邀請碼\n\n**${invite.code}**\n\n有效至 ${invite.expires_at || "建立後 7 天"}。請只分享給你信任的家庭成員。`;
  }
  return assistantText(response);
};

const PersonalMarkdown = ({ children }) => {
  const source = String(children || "");
  const rendered = typeof W2.mdToHtml === "function" ? W2.mdToHtml(source) : null;
  const html = rendered == null || !window.DOMPurify ? rendered : window.DOMPurify.sanitize(rendered, {
    ALLOWED_TAGS: ["p", "br", "strong", "b", "em", "i", "del", "h1", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "hr", "pre", "code", "table", "thead", "tbody", "tr", "th", "td", "a"],
    ALLOWED_ATTR: ["href", "title", "target", "rel"],
  });
  return html != null
    ? <div className="assistant-markdown md" dangerouslySetInnerHTML={{ __html: html }}/>
    : <div className="assistant-plain">{source}</div>;
};

const normalizeAssistantHistory = (data) => {
  const latestConversation = data?.conversation || data?.conversations?.[0] || null;
  const base = Array.isArray(data) ? data : data?.messages || data?.history || data?.items || latestConversation?.messages || [];
  const knownActions = new Set(base.map((entry) => String(entry.action_id || entry.action?.id || "")).filter(Boolean));
  const historyActions = (Array.isArray(data?.actions) ? data.actions : []).filter((action) => !knownActions.has(String(action.action_id || action.id || ""))).map((action) => ({ ...action, type: "confirmation_required" }));
  const raw = [...base, ...historyActions];
  const messages = raw.map((entry) => {
    const kind = entry.type || entry.event || entry.role || "assistant";
    if (kind === "step" || kind === "step_start") return {
      id: `history-step-${entry.id || entry.step_id || makeLocalId("step")}`, role: "step",
      label: entry.label || entry.title || entry.name || assistantText(entry) || "執行步驟",
      detail: entry.detail || entry.summary || "", status: entry.status || (kind === "step_start" ? "running" : "done"),
    };
    if (kind === "confirmation_required" || kind === "confirm") {
      const action = entry.action || entry;
      return {
        id: `history-action-${action.action_id || action.id || entry.message_id || makeLocalId("confirm")}`, role: "confirm",
        actionId: action.action_id || action.id, title: action.title || action.label || action.tool_name || "需要你的確認",
        detail: action.summary || action.description || assistantText(action) || (action.args ? JSON.stringify(action.args, null, 2) : ""), status: action.status || "pending",
      };
    }
    return {
      id: `history-message-${entry.id || entry.message_id || makeLocalId("message")}`,
      role: kind === "user" ? "user" : "assistant",
      content: assistantText(entry),
    };
  }).filter((entry) => entry.role === "step" || entry.role === "confirm" || entry.content);
  return {
    conversationId: data?.conversation_id || latestConversation?.id || raw.find((entry) => entry.conversation_id)?.conversation_id || null,
    messages,
  };
};

const HousekeeperView = ({ workspace, onClose, onRefresh }) => {
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [actionBusy, setActionBusy] = useState(null);
  const [error, setError] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [voiceNote, setVoiceNote] = useState("");
  const [imageAttachment, setImageAttachment] = useState(null);
  const [imageRecognizing, setImageRecognizing] = useState(false);
  const [imageNote, setImageNote] = useState("");
  const [imageError, setImageError] = useState("");
  const abortRef = useRef(null);
  const runIdRef = useRef(null);
  const listRef = useRef(null);
  const voiceRecorderRef = useRef(null);
  const voiceStreamRef = useRef(null);
  const voiceChunksRef = useRef([]);
  const voiceAbortRef = useRef(null);
  const voiceCancelledRef = useRef(false);
  const voiceMountedRef = useRef(true);
  const imageCameraRef = useRef(null);
  const imageUploadRef = useRef(null);
  const imageAbortRef = useRef(null);
  const imagePreviewUrlRef = useRef("");
  const imageMountedRef = useRef(true);
  const sharedMode = workspace?.type === "household";
  const quickPrompts = sharedMode
    ? ["今天家裏最需要處理什麼？", "用快到期食材安排一餐", "新增一件家務：今晚倒垃圾"]
    : ["今天我最需要處理什麼？", "用快到期食材安排一餐", "幫我記一筆餐飲開銷"];

  useEffect(() => {
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError("");
    personalRequest(`/api/personal/assistant/history?workspace_id=${encodeURIComponent(workspace.id)}`, { signal: controller.signal })
      .then((data) => {
        const normalized = normalizeAssistantHistory(data);
        setMessages(normalized.messages);
        setConversationId(normalized.conversationId);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message || "暫時無法載入管家記錄。");
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [workspace.id]);

  useEffect(() => () => {
    voiceMountedRef.current = false;
    voiceCancelledRef.current = true;
    voiceAbortRef.current?.abort();
    const recorder = voiceRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try { recorder.stop(); } catch (stopError) {}
    }
    voiceStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    voiceStreamRef.current = null;
    imageMountedRef.current = false;
    imageAbortRef.current?.abort();
    if (imagePreviewUrlRef.current) URL.revokeObjectURL(imagePreviewUrlRef.current);
    imagePreviewUrlRef.current = "";
  }, []);

  useEffect(() => {
    const node = listRef.current;
    if (node) node.scrollTo({ top: node.scrollHeight, behavior: "smooth" });
  }, [messages, busy]);

  const replaceImageAttachment = (nextAttachment) => {
    const nextPreviewUrl = String(nextAttachment?.previewUrl || "");
    if (imagePreviewUrlRef.current && imagePreviewUrlRef.current !== nextPreviewUrl) URL.revokeObjectURL(imagePreviewUrlRef.current);
    imagePreviewUrlRef.current = nextPreviewUrl;
    setImageAttachment(nextAttachment || null);
  };
  const clearImageAttachment = () => {
    replaceImageAttachment(null);
    setImageNote("");
    setImageError("");
  };

  const applyStreamEvent = (event) => {
    const type = event.type || event.event;
    if (type === "error") {
      setError(event.error || event.message || "管家串流中斷，請稍後重試。");
      return;
    }
    if (type === "run_start") {
      runIdRef.current = event.run_id || null;
      if (event.conversation_id || event.conversation?.id) setConversationId(event.conversation_id || event.conversation.id);
      if (event.image_attachment_used === true) clearImageAttachment();
      return;
    }
    if (type === "step_start") {
      const step = event.step || event;
      const stepId = `stream-step-${runIdRef.current || "current"}-${step.step_id || step.id || step.step_no || makeLocalId("step")}`;
      setMessages((current) => [...current, {
        id: stepId, role: "step", status: "running",
        label: step.label || step.title || step.name || step.tool_name || "管家正在處理", detail: step.detail || step.summary || "",
      }]);
      return;
    }
    if (type === "step") {
      const step = event.step || event;
      const rawStepId = step.step_id || step.id || step.step_no;
      const stepId = rawStepId ? `stream-step-${runIdRef.current || "current"}-${rawStepId}` : null;
      setMessages((current) => {
        let updated = false;
        const next = current.map((message) => {
          const isTarget = message.role === "step" && (stepId ? String(message.id) === String(stepId) : !updated && message.status === "running");
          if (!isTarget) return message;
          updated = true;
          return {
            ...message, status: step.status || "done", label: step.label || step.title || step.tool_name || message.label,
            detail: step.detail || step.summary || step.message || step.error || assistantText(step) || message.detail,
          };
        });
        return updated ? next : [...next, {
          id: stepId || makeLocalId("step"), role: "step", status: step.status || "done",
          label: step.label || step.title || step.tool_name || "已完成一步", detail: step.detail || step.summary || step.message || step.error || assistantText(step),
        }];
      });
      return;
    }
    if (type === "confirmation_required") {
      const action = event.action || event.payload || event;
      setMessages((current) => [...current, {
        id: event.message_id || makeLocalId("confirm"), role: "confirm", status: "pending",
        actionId: action.action_id || event.action_id || action.id,
        title: action.title || action.label || "需要你的確認",
        detail: action.summary || action.description || assistantText(action),
      }]);
      return;
    }
    if (type === "final") {
      const content = assistantText(event);
      if (content) setMessages((current) => [...current, { id: makeLocalId("assistant"), role: "assistant", content }]);
      return;
    }
  };

  const sendPrompt = async (prompt = input) => {
    const requestedText = String(prompt || "").trim();
    const activeAttachment = imageAttachment?.id ? imageAttachment : null;
    if ((!requestedText && !activeAttachment) || busy || loading || imageRecognizing) return;
    const text = requestedText || "請分析這張圖片。";
    const userAttachment = activeAttachment ? {
      kind: activeAttachment.kind || "image",
      label: activeAttachment.fileName || "已附上一張圖片",
      summary: activeAttachment.summary || "圖片已交給管家分析。",
      details: activeAttachment.details || "",
    } : null;
    setInput("");
    setError("");
    setBusy(true);
    setMessages((current) => [...current, { id: makeLocalId("user"), role: "user", content: text, attachment: userAttachment }]);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await personalStream("/api/personal/assistant/run/stream", {
        workspace_id: workspace.id, conversation_id: conversationId, text,
        ...(activeAttachment ? { image_attachment_id: activeAttachment.id } : {}),
      }, { signal: controller.signal, onEvent: applyStreamEvent });
    } catch (requestError) {
      if (requestError.name !== "AbortError") setError(requestError.message || "管家回應中斷，請再試一次。");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  };

  const recognizeAssistantImage = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || imageRecognizing || busy || loading) return;
    setImageRecognizing(true);
    setImageError("");
    setImageNote("正在本機壓縮圖片…");
    imageAbortRef.current?.abort();
    const controller = new AbortController();
    imageAbortRef.current = controller;
    try {
      const normalized = await normalizePersonalImage(file);
      if (!imageMountedRef.current || controller.signal.aborted) return;
      setImageNote("已在本機壓縮，正在建立圖片分析附件…");
      const form = new FormData();
      form.append("file", normalized.file, normalized.name);
      form.append("workspace_id", String(workspace.id || ""));
      if (conversationId != null && String(conversationId).trim()) form.append("conversation_id", String(conversationId));
      const response = await personalRequest("/api/personal/assistant/images/recognize", {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      const attachment = response?.attachment;
      const id = String(attachment?.id || "").trim();
      if (!response?.ok || !id) throw new Error("圖片暫時無法建立分析附件，請換一張清楚的圖片再試。");
      if (!imageMountedRef.current || controller.signal.aborted) return;
      replaceImageAttachment({
        id,
        kind: assistantAttachmentText(attachment?.kind, "image"),
        fileName: assistantAttachmentText(file.name, "已選擇圖片"),
        summary: assistantAttachmentText(attachment?.summary, "圖片已就緒，可在訊息中告訴管家你想了解什麼。"),
        details: assistantAttachmentText(attachment?.details),
        expiresInSeconds: Number(attachment?.expires_in_seconds) || null,
        previewUrl: URL.createObjectURL(normalized.file),
      });
      setImageNote("圖片已壓縮，可補充問題後傳送。");
    } catch (requestError) {
      if (requestError.name === "AbortError" || !imageMountedRef.current) return;
      setImageNote("");
      setImageError(requestError.message || "圖片分析暫時無法完成，請稍後再試。");
    } finally {
      if (imageMountedRef.current && imageAbortRef.current === controller) setImageRecognizing(false);
    }
  };

  const stopVoiceTracks = () => {
    voiceStreamRef.current?.getTracks?.().forEach((track) => track.stop());
    voiceStreamRef.current = null;
  };
  const cancelVoiceCapture = () => {
    voiceCancelledRef.current = true;
    voiceAbortRef.current?.abort();
    const recorder = voiceRecorderRef.current;
    if (recorder && recorder.state !== "inactive") {
      try { recorder.stop(); } catch (stopError) {}
    }
    stopVoiceTracks();
    setRecording(false);
    setTranscribing(false);
  };
  const stopVoiceCapture = () => {
    const recorder = voiceRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    setVoiceNote("正在轉成文字…");
    try { recorder.stop(); } catch (stopError) { setVoiceNote("語音錄製沒有正常停止，請再試一次。"); }
  };
  const startVoiceCapture = async () => {
    if (recording) { stopVoiceCapture(); return; }
    if (busy || loading || transcribing) return;
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setVoiceNote("這個瀏覽器無法錄製語音，請直接輸入文字。");
      return;
    }
    voiceCancelledRef.current = false;
    setVoiceNote("");
    setError("");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      if (voiceCancelledRef.current || !voiceMountedRef.current) {
        stream.getTracks?.().forEach((track) => track.stop());
        return;
      }
      voiceStreamRef.current = stream;
      const preferredType = ["audio/webm;codecs=opus", "audio/webm"].find((type) => !window.MediaRecorder.isTypeSupported || window.MediaRecorder.isTypeSupported(type));
      const recorder = preferredType ? new window.MediaRecorder(stream, { mimeType: preferredType }) : new window.MediaRecorder(stream);
      voiceRecorderRef.current = recorder;
      voiceChunksRef.current = [];
      recorder.ondataavailable = (event) => { if (event.data?.size) voiceChunksRef.current.push(event.data); };
      recorder.onerror = () => {
        if (!voiceMountedRef.current) return;
        setRecording(false);
        setVoiceNote("語音錄製失敗，請再試一次。");
        stopVoiceTracks();
      };
      recorder.onstop = async () => {
        const chunks = voiceChunksRef.current;
        const mimeType = recorder.mimeType || preferredType || "audio/webm";
        voiceRecorderRef.current = null;
        stopVoiceTracks();
        if (voiceCancelledRef.current || !voiceMountedRef.current) return;
        setRecording(false);
        const audio = new Blob(chunks, { type: mimeType });
        if (audio.size < 200) {
          setVoiceNote("沒有錄到足夠的語音，請靠近麥克風後再試一次。");
          return;
        }
        setTranscribing(true);
        setVoiceNote("正在轉成文字…");
        const controller = new AbortController();
        voiceAbortRef.current = controller;
        try {
          const response = await personalRequest("/api/personal/voice/transcribe?lang=zh&correct=1", {
            method: "POST",
            headers: { "Content-Type": mimeType || "audio/webm" },
            body: audio,
            signal: controller.signal,
          });
          const text = String(response?.text || "").trim();
          if (!response?.ok || !text) throw new Error("沒有辨識到清楚的語音，請再說一次。");
          if (!voiceMountedRef.current || controller.signal.aborted) return;
          setInput((current) => current.trim() ? `${current.trimEnd()} ${text}` : text);
          setVoiceNote("已轉成文字，可以修改後再傳送。");
        } catch (requestError) {
          if (requestError.name !== "AbortError" && voiceMountedRef.current) setVoiceNote(requestError.message || "語音轉文字暫時無法完成。");
        } finally {
          if (voiceMountedRef.current && voiceAbortRef.current === controller) setTranscribing(false);
        }
      };
      recorder.start();
      setRecording(true);
      setVoiceNote("正在聆聽，再按一次完成。");
    } catch (requestError) {
      stopVoiceTracks();
      if (!voiceMountedRef.current) return;
      setRecording(false);
      setVoiceNote(requestError.name === "NotAllowedError" ? "麥克風權限被拒絕，請在瀏覽器設定中允許後再試。" : requestError.message || "無法開啟麥克風。");
    }
  };

  const decideAction = async (message, decision) => {
    if (!message.actionId || actionBusy) return;
    setActionBusy(message.actionId);
    setError("");
    try {
      const result = await personalPost(`/api/personal/assistant/actions/${encodeURIComponent(message.actionId)}/${decision}`, {});
      setMessages((current) => current.map((entry) => entry.id === message.id ? { ...entry, status: decision === "confirm" ? "confirmed" : "rejected" } : entry));
      const resultText = assistantActionResultText(result);
      if (resultText) setMessages((current) => [...current, { id: makeLocalId("assistant"), role: "assistant", content: resultText }]);
      if (decision === "confirm") await onRefresh();
    } catch (requestError) {
      if (requestError.status === 409 || requestError.status >= 500) {
        const status = String(requestError.message || "").includes("過期") ? "expired" : "failed";
        setMessages((current) => current.map((entry) => entry.id === message.id ? { ...entry, status } : entry));
      }
      setError(requestError.message || "未能處理確認，請再試一次。");
    } finally {
      setActionBusy(null);
    }
  };

  const close = () => {
    abortRef.current?.abort();
    cancelVoiceCapture();
    onClose();
  };

  return <section className="housekeeper-view personal-rise" role="dialog" aria-modal="true" aria-label="AI 管家">
    <header className="housekeeper-head">
      <button className="housekeeper-back" onClick={close} aria-label="返回"><Icon name="arrow" size={17}/></button>
      <div><span>AI HOUSEKEEPER</span><strong>{workspace.name}</strong></div>
      <span className="housekeeper-scope"><Icon name="shield" size={13}/>{sharedMode ? "小家" : "私人"}</span>
    </header>
    <div className="housekeeper-log" ref={listRef} aria-live="polite">
      <div className="housekeeper-intro"><span>HOME / ASSISTANT</span><h2>把生活說給管家聽。</h2><p>{sharedMode ? "管家可以分析這個小家的庫存、家務與賬本；任何會改變資料的操作都會先請你確認。" : "這段對話只屬於目前私人空間；任何會改變資料的操作都會先請你確認。"}</p></div>
      {loading && <div className="assistant-loading"><i/><span>正在載入這個空間的對話</span></div>}
      {!loading && !messages.length && <div className="assistant-empty">還沒有對話。從一個生活問題開始。</div>}
      <div className="assistant-messages">
        {messages.map((message) => message.role === "step" ? <div className={`assistant-step ${message.status}`} key={message.id}>
          <span>{message.status === "running" ? <i/> : <Icon name="check" size={13}/>}</span><div><strong>{message.label}</strong>{message.detail && <p>{message.detail}</p>}</div>
        </div> : message.role === "confirm" ? <article className={`assistant-confirm ${message.status}`} key={message.id}>
          <span className="field-label">CONFIRMATION REQUIRED</span><h3>{message.title}</h3>{message.detail && <PersonalMarkdown>{message.detail}</PersonalMarkdown>}
          {message.status === "pending" ? <div className="assistant-confirm-actions"><button disabled={!!actionBusy} onClick={() => decideAction(message, "reject")}>拒絕</button><button className="primary" disabled={!!actionBusy} onClick={() => decideAction(message, "confirm")}><Icon name="check" size={14}/>{actionBusy === message.actionId ? "處理中…" : "確認執行"}</button></div> : <div className="assistant-decision"><Icon name={message.status === "confirmed" ? "checkCircle" : message.status === "rejected" ? "x" : message.status === "executing" ? "clock" : "alert"} size={14}/>{message.status === "confirmed" ? "已確認並更新資料" : message.status === "rejected" ? "已拒絕，不會改變資料" : message.status === "expired" ? "確認已過期，資料沒有因此再次變更" : message.status === "executing" ? "操作結果仍在核對中，請稍後刷新" : "操作未完成，請檢查目前資料後再試"}</div>}
        </article> : <div className={`assistant-message ${message.role}`} key={message.id}><span>{message.role === "user" ? "YOU" : "HOME"}</span><PersonalMarkdown>{message.content}</PersonalMarkdown>{message.attachment && <div className="assistant-message-attachment"><Icon name="scan" size={14}/><div><strong>{message.attachment.label}</strong><small>{message.attachment.summary}</small>{message.attachment.details && <small>{message.attachment.details}</small>}</div></div>}</div>)}
        {busy && <div className="assistant-thinking"><i/><i/><i/><span>管家正在思考</span></div>}
      </div>
      {error && <div className="assistant-error" role="alert"><Icon name="alert" size={15}/><span>{error}</span></div>}
    </div>
    <footer className="housekeeper-compose">
      <div className="assistant-prompts">{quickPrompts.map((prompt) => <button key={prompt} disabled={busy || loading || imageRecognizing} onClick={() => sendPrompt(prompt)}>{prompt}</button>)}</div>
      {imageAttachment && <section className="assistant-image-attachment" data-testid="assistant-image-attachment" aria-label="已選擇的圖片附件">
        <img src={imageAttachment.previewUrl} alt="已選擇的圖片預覽"/>
        <div><span className="field-label">IMAGE READY / ONE-TIME</span><strong>{imageAttachment.fileName}</strong><p>{imageAttachment.summary}</p>{imageAttachment.details && <small>{imageAttachment.details}</small>}</div>
        <button type="button" onClick={clearImageAttachment} disabled={busy} aria-label="移除圖片附件" title="移除圖片附件"><Icon name="x" size={15}/></button>
      </section>}
      {imageNote && <div className={`assistant-image-note ${imageRecognizing ? "recognizing" : ""}`} role="status"><Icon name={imageRecognizing ? "clock" : "checkCircle"} size={14}/><span>{imageNote}</span></div>}
      {imageError && <div className="assistant-image-error" role="alert"><Icon name="alert" size={14}/><span>{imageError}</span></div>}
      {voiceNote && <div className={`assistant-voice-note ${recording ? "recording" : ""}`} role="status"><Icon name={recording ? "mic" : transcribing ? "clock" : "checkCircle"} size={14}/><span>{voiceNote}</span></div>}
      <div className="assistant-input"><textarea rows="1" disabled={loading} value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendPrompt(); } }} placeholder={imageAttachment ? "告訴管家想從圖片了解什麼…" : "對管家說…"} aria-label="給管家的訊息"/><button className="assistant-image-button" type="button" disabled={busy || loading || imageRecognizing} onClick={() => imageCameraRef.current?.click()} aria-label="拍照加入對話" title="拍照加入對話"><Icon name="scan" size={16}/></button><button className="assistant-upload-button" type="button" disabled={busy || loading || imageRecognizing} onClick={() => imageUploadRef.current?.click()} aria-label="上傳圖片加入對話" title="上傳圖片加入對話"><Icon name="box" size={16}/></button><button className={`assistant-voice-button ${recording ? "recording" : ""}`} disabled={busy || loading || imageRecognizing || (transcribing && !recording)} onClick={startVoiceCapture} aria-label={recording ? "完成語音輸入" : "語音輸入"} title={recording ? "完成語音輸入" : "語音輸入"}><Icon name="mic" size={16}/></button><button disabled={busy || loading || imageRecognizing || (!input.trim() && !imageAttachment?.id)} onClick={() => sendPrompt()} aria-label="發送"><Icon name="arrow" size={17}/></button></div>
      <input ref={imageCameraRef} className="visually-hidden" data-testid="assistant-image-camera-input" type="file" accept={PERSONAL_IMAGE_SOURCE_ACCEPT} capture="environment" onChange={recognizeAssistantImage}/>
      <input ref={imageUploadRef} className="visually-hidden" data-testid="assistant-image-upload-input" type="file" accept={PERSONAL_IMAGE_SOURCE_ACCEPT} onChange={recognizeAssistantImage}/>
    </footer>
  </section>;
};

const TUTORIAL_STEPS = [
  { code: "01 / HOUSEKEEPER", icon: "sparkle", title: "先問管家，再決定怎麼做。", copy: "管家會讀懂目前空間的庫存、家務和賬本，整理出下一步；涉及改動時一定先請你確認。" },
  { code: "02 / BARCODE", icon: "scan", title: "掃一下，物品資料自動帶入。", copy: "相機只在你主動開啟時使用。也可以上傳照片、輸入條碼，或完全手動入庫。" },
  { code: "03 / TOGETHER", icon: "user", title: "把生活請求交給小家。", copy: "家人可以接手、稍後提醒或標記完成。每次互動都保留清楚的共同記錄。" },
  { code: "04 / YOUR CONTROL", icon: "shield", title: "確認權始終在你手上。", copy: "私人空間與收入不會自動分享；管家提出的寫入、移動或記賬操作，沒有確認就不會執行。" },
];

const TutorialOverlay = ({ onComplete }) => {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const current = TUTORIAL_STEPS[step];
  const next = async () => {
    if (step < TUTORIAL_STEPS.length - 1) { setStep((value) => value + 1); return; }
    setBusy(true);
    setError("");
    try { await onComplete(); }
    catch (requestError) { setError(requestError.message || "暫時無法保存教學進度。"); setBusy(false); }
  };
  return <section className="tutorial-overlay" role="dialog" aria-modal="true" aria-label="個人模式快速導覽">
    <header><div className="home-mark"><Icon name="home" size={18}/></div><strong>HOME<i>.</i></strong><span>{String(step + 1).padStart(2, "0")} / 04</span></header>
    <div className="tutorial-progress">{TUTORIAL_STEPS.map((entry, index) => <i className={index <= step ? "on" : ""} key={entry.code}/>)}</div>
    <main>
      <span className="tutorial-icon"><Icon name={current.icon} size={26}/></span>
      <span className="folio-line">{current.code}</span>
      <h2>{current.title}</h2><p>{current.copy}</p>
      {step === 3 && <div className="tutorial-rule"><Icon name="check" size={15}/><span>先預覽，再確認，最後才寫入。</span></div>}
      {error && <div className="assistant-error" role="alert"><Icon name="alert" size={14}/><span>{error}</span></div>}
    </main>
    <footer><button disabled={busy || step === 0} onClick={() => setStep((value) => Math.max(0, value - 1))}>上一步</button><button className="primary" disabled={busy} onClick={next}>{busy ? "正在保存…" : step === 3 ? "進入 HOME" : "下一步"}<Icon name="arrow" size={14}/></button></footer>
  </section>;
};

const BARCODE_FORMATS = ["ean_8", "ean_13", "upc_a", "upc_e", "code_128"];
const createBarcodeDetector = async () => {
  if (!("BarcodeDetector" in window)) return null;
  try {
    const supported = typeof window.BarcodeDetector.getSupportedFormats === "function" ? await window.BarcodeDetector.getSupportedFormats() : BARCODE_FORMATS;
    const formats = BARCODE_FORMATS.filter((format) => supported.includes(format));
    return formats.length ? new window.BarcodeDetector({ formats }) : null;
  } catch (error) {
    return null;
  }
};

const BarcodeScanner = ({ onCode, onProduct }) => {
  const [active, setActive] = useState(false);
  const [manualCode, setManualCode] = useState("");
  const [status, setStatus] = useState("相機尚未啟動");
  const [error, setError] = useState("");
  const [lookingUp, setLookingUp] = useState(false);
  const [product, setProduct] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const videoRef = useRef(null);
  const fileRef = useRef(null);
  const streamRef = useRef(null);
  const readerRef = useRef(null);
  const controlsRef = useRef(null);
  const frameRef = useRef(null);
  const lookupAbortRef = useRef(null);
  const runningRef = useRef(false);
  const detectedRef = useRef(false);
  const mountedRef = useRef(true);

  const stopCamera = () => {
    runningRef.current = false;
    if (frameRef.current) cancelAnimationFrame(frameRef.current);
    frameRef.current = null;
    try { controlsRef.current?.stop?.(); } catch (error) {}
    try { readerRef.current?.reset?.(); } catch (error) {}
    controlsRef.current = null;
    readerRef.current = null;
    streamRef.current?.getTracks?.().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) { videoRef.current.pause(); videoRef.current.srcObject = null; }
    if (mountedRef.current) setActive(false);
  };

  useEffect(() => () => {
    mountedRef.current = false;
    lookupAbortRef.current?.abort();
    stopCamera();
  }, []);

  const lookup = async (value) => {
    const code = String(value || "").trim();
    if (!code || lookingUp) return;
    stopCamera();
    if (!/^\d{8,14}$/.test(code)) {
      detectedRef.current = false;
      setStatus("這個條碼不能用於商品查找");
      setError("目前商品庫只接受 8 到 14 位數字 EAN、UPC 或 GTIN。");
      return;
    }
    detectedRef.current = true;
    setManualCode(code);
    onCode(code);
    setProduct(null);
    onProduct({ code, found: false, reset: true }, code);
    setLookingUp(true);
    setError("");
    setCandidates([]);
    setStatus(`正在查找 ${code}`);
    lookupAbortRef.current?.abort();
    const controller = new AbortController();
    lookupAbortRef.current = controller;
    try {
      const response = await personalRequest("/api/personal/barcodes/lookup", {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ barcode: code }), signal: controller.signal,
      });
      if (!mountedRef.current || controller.signal.aborted) return;
      const nextProduct = { ...(response.product || response), found: response.found !== false };
      const nextCandidates = Array.isArray(response.candidates) ? response.candidates : [];
      setCandidates(nextCandidates);
      if (nextProduct?.name) {
        setProduct(nextProduct);
        onProduct(nextProduct, code);
      } else {
        setProduct(null);
      }
      setStatus(nextProduct?.name
        ? "商品資料已帶入，核對後即可入庫"
        : nextCandidates.length
          ? "找到相同條碼的網頁候選，請選擇後核對"
          : response.message || "沒有完整商品資料，請補充名稱後入庫");
    } catch (requestError) {
      if (requestError.name === "AbortError" || !mountedRef.current) return;
      setProduct(null);
      setCandidates([]);
      setStatus("條碼已保留，可以繼續手動入庫");
      setError(requestError.status === 404 ? "商品庫暫時沒有這個條碼，請手動補充資料。" : requestError.message || "商品資料查找失敗。");
    } finally {
      if (mountedRef.current && lookupAbortRef.current === controller) setLookingUp(false);
    }
  };

  const detectCode = (value) => {
    const code = String(value || "").trim();
    if (!mountedRef.current || !code || detectedRef.current) return;
    detectedRef.current = true;
    lookup(code);
  };

  const runDetectorLoop = (detector) => {
    const tick = async () => {
      if (!runningRef.current || detectedRef.current || !videoRef.current) return;
      try {
        const results = await detector.detect(videoRef.current);
        if (results[0]?.rawValue) { detectCode(results[0].rawValue); return; }
      } catch (requestError) {}
      if (runningRef.current) frameRef.current = requestAnimationFrame(tick);
    };
    frameRef.current = requestAnimationFrame(tick);
  };

  const startCamera = async () => {
    if (active || lookingUp) return;
    detectedRef.current = false;
    setError("");
    setProduct(null);
    setCandidates([]);
    if (!navigator.mediaDevices?.getUserMedia) { setError("這個瀏覽器無法開啟相機，請改用照片或手動條碼。"); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" } }, audio: false });
      if (!mountedRef.current) { stream.getTracks().forEach((track) => track.stop()); return; }
      streamRef.current = stream;
      runningRef.current = true;
      setActive(true);
      setStatus("把商品條碼放進取景框");
      const video = videoRef.current;
      video.srcObject = stream;
      await video.play();
      const detector = await createBarcodeDetector();
      if (detector) { runDetectorLoop(detector); return; }
      const Reader = window.ZXingBrowser?.BrowserMultiFormatReader;
      if (!Reader) throw new Error("掃碼工具尚未載入，請改用照片或手動條碼。");
      const reader = new Reader();
      readerRef.current = reader;
      controlsRef.current = await reader.decodeFromStream(stream, video, (result) => {
        const code = result?.getText?.() || result?.text;
        if (code) detectCode(code);
      });
    } catch (requestError) {
      stopCamera();
      if (!mountedRef.current) return;
      setStatus("相機未啟動");
      setError(requestError.name === "NotAllowedError" ? "相機權限被拒絕，請改用照片或手動條碼。" : requestError.message || "無法開啟相機。");
    }
  };

  const scanPhoto = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    stopCamera();
    detectedRef.current = false;
    setProduct(null);
    setCandidates([]);
    setError("");
    setStatus("正在辨識照片中的條碼");
    let bitmap;
    let objectUrl;
    try {
      const detector = await createBarcodeDetector();
      let code = "";
      if (detector && window.createImageBitmap) {
        bitmap = await createImageBitmap(file);
        const results = await detector.detect(bitmap);
        code = results[0]?.rawValue || "";
      } else {
        const Reader = window.ZXingBrowser?.BrowserMultiFormatReader;
        if (!Reader) throw new Error("這個瀏覽器無法辨識照片條碼。");
        objectUrl = URL.createObjectURL(file);
        const reader = new Reader();
        readerRef.current = reader;
        const result = await reader.decodeFromImageUrl(objectUrl);
        code = result?.getText?.() || result?.text || "";
      }
      if (!code) throw new Error("照片中沒有找到可辨識的條碼。");
      detectCode(code);
    } catch (requestError) {
      if (!mountedRef.current) return;
      setStatus("沒有辨識到條碼");
      setError(requestError.message || "照片條碼辨識失敗，請改用手動輸入。");
    } finally {
      bitmap?.close?.();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      try { readerRef.current?.reset?.(); } catch (error) {}
      readerRef.current = null;
    }
  };

  const useCandidate = (candidate) => {
    const name = String(candidate?.name || "").trim();
    if (!name) return;
    const sourceHost = String(candidate?.source_host || "").trim();
    const selected = {
      code: manualCode,
      name,
      source: sourceHost ? `WEB · ${sourceHost}` : "WEB SEARCH",
      found: false,
      is_food: false,
    };
    setProduct(selected);
    setCandidates([]);
    onProduct(selected, manualCode);
    setStatus("已帶入網路候選，請核對名稱後入庫");
  };

  return <div className="barcode-scanner" data-testid="barcode-scanner">
    <div className={`barcode-viewport ${active ? "active" : ""}`}>
      <video ref={videoRef} muted playsInline aria-label="條碼相機預覽"/>
      <div className="barcode-frame"><i/><i/><i/><i/><span>{active ? "SCAN / LIVE" : "CAMERA / OFF"}</span></div>
    </div>
    <div className="barcode-status"><span className={active ? "live" : ""}/><strong>{lookingUp ? "正在查找商品…" : status}</strong></div>
    <div className="barcode-actions"><button className="text-action primary" type="button" onClick={active ? stopCamera : startCamera} disabled={lookingUp}><Icon name={active ? "x" : "scan"} size={15}/>{active ? "停止相機" : "開啟相機"}</button><button className="text-action" type="button" onClick={() => fileRef.current?.click()} disabled={lookingUp}><Icon name="box" size={15}/>選擇照片</button><input ref={fileRef} className="visually-hidden" type="file" accept="image/*" onChange={scanPhoto}/></div>
    <div className="barcode-manual"><label><span className="field-label">BARCODE / 手動輸入</span><input className="home-field" inputMode="numeric" autoComplete="off" value={manualCode} onChange={(event) => { detectedRef.current = false; setManualCode(event.target.value.replace(/\D/g, "").slice(0, 14)); }} placeholder="8–14 位 EAN / UPC / GTIN"/></label><button type="button" onClick={() => lookup(manualCode)} disabled={lookingUp || manualCode.length < 8} aria-label="查找條碼"><Icon name="search" size={16}/></button></div>
    {product?.name && <div className="barcode-product">{product.image_url ? <img src={product.image_url} alt="" referrerPolicy="no-referrer"/> : <span><Icon name="box" size={18}/></span>}<div><strong>{product.name}</strong><small>{[product.brand, product.package_size, product.source].filter(Boolean).join(" · ")}</small></div><Icon name="checkCircle" size={17}/></div>}
    {!!candidates.length && <div className="barcode-candidates"><span className="field-label">WEB CANDIDATES / 相同條碼候選</span>{candidates.map((candidate) => <button key={candidate.id || candidate.source_url} type="button" onClick={() => useCandidate(candidate)}><span><strong>{candidate.name}</strong><small>{[candidate.source_host, candidate.evidence].filter(Boolean).join(" · ")}</small></span><Icon name="arrow" size={15}/></button>)}</div>}
    {error && <div className="barcode-error" role="alert"><Icon name="alert" size={14}/><span>{error}</span></div>}
  </div>;
};

const FOOD_PHOTO_CONFIDENCE = { high: "HIGH", medium: "CHECK", low: "REVIEW" };

const FoodPhotoRecognizer = ({ workspaceId, onSuggestion }) => {
  const [recognizing, setRecognizing] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [suggestion, setSuggestion] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const cameraRef = useRef(null);
  const uploadRef = useRef(null);
  const abortRef = useRef(null);
  const mountedRef = useRef(true);
  const previewUrlRef = useRef("");

  const replacePreview = (nextUrl = "") => {
    if (previewUrlRef.current && previewUrlRef.current !== nextUrl) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = nextUrl;
    setPreviewUrl(nextUrl);
  };

  useEffect(() => () => {
    mountedRef.current = false;
    abortRef.current?.abort();
    if (previewUrlRef.current) URL.revokeObjectURL(previewUrlRef.current);
    previewUrlRef.current = "";
  }, []);

  const recognize = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || recognizing) return;
    setRecognizing(true);
    setError("");
    setSuggestion(null);
    replacePreview("");
    setStatus("正在本機壓縮照片…");
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      const normalized = await normalizePersonalImage(file);
      if (!mountedRef.current || controller.signal.aborted) return;
      replacePreview(URL.createObjectURL(normalized.file));
      setStatus("已在本機壓縮，正在辨識食材與保存方式…");
      const form = new FormData();
      form.append("file", normalized.file, normalized.name);
      form.append("workspace_id", String(workspaceId || ""));
      const response = await personalRequest("/api/personal/foods/recognize", {
        method: "POST",
        body: form,
        signal: controller.signal,
      });
      const nextSuggestion = response?.suggestion;
      if (!nextSuggestion?.name) throw new Error("沒有辨識到可用的食材名稱，請改拍清楚的包裝或食材。");
      if (!mountedRef.current || controller.signal.aborted) return;
      setSuggestion(nextSuggestion);
      onSuggestion?.(nextSuggestion);
      setStatus("已壓縮並填入下方欄位。");
    } catch (requestError) {
      if (requestError.name === "AbortError" || !mountedRef.current) return;
      setStatus("");
      setError(requestError.message || "圖片識別暫時無法完成，請直接手動填寫。");
    } finally {
      if (mountedRef.current && abortRef.current === controller) setRecognizing(false);
    }
  };

  return <section className="food-photo-recognizer" data-testid="food-photo-recognizer">
    <div className="food-photo-head"><span className="field-label">AI FOOD VISION / 拍照識材</span><span>EDIT BEFORE SAVE</span></div>
    <p>拍食材或外包裝，核對欄位後再入庫。</p>
    <div className="food-photo-actions">
      <button type="button" className="text-action primary" onClick={() => cameraRef.current?.click()} disabled={recognizing}><Icon name="scan" size={15}/>{recognizing ? "正在識別…" : "拍照識別"}</button>
      <button type="button" className="text-action" onClick={() => uploadRef.current?.click()} disabled={recognizing}><Icon name="box" size={15}/>上傳照片</button>
      <input ref={cameraRef} className="visually-hidden" data-testid="food-photo-camera-input" type="file" accept={PERSONAL_IMAGE_SOURCE_ACCEPT} capture="environment" onChange={recognize}/>
      <input ref={uploadRef} className="visually-hidden" data-testid="food-photo-upload-input" type="file" accept={PERSONAL_IMAGE_SOURCE_ACCEPT} onChange={recognize}/>
    </div>
    {status && <div className="food-photo-status"><Icon name="checkCircle" size={14}/><span>{status}</span></div>}
    {previewUrl && <div className="food-photo-preview" data-testid="food-photo-normalized-preview"><img src={previewUrl} alt="已壓縮的食材照片預覽"/><span><Icon name="checkCircle" size={16}/></span></div>}
    {suggestion && <div className="food-photo-suggestion"><span><Icon name="sparkle" size={15}/></span><div><strong>{suggestion.name}</strong><small>{[suggestion.brand, suggestion.storage_hint, suggestion.expiry_days != null ? `${suggestion.expiry_days} 天內建議食用` : ""].filter(Boolean).join(" · ")}</small></div><b>{FOOD_PHOTO_CONFIDENCE[String(suggestion.confidence || "").toLowerCase()] || "AI"}</b></div>}
    {error && <div className="food-photo-error" role="alert"><Icon name="alert" size={14}/><span>{error}</span></div>}
  </section>;
};

const ActionSheet = ({ type, items, members = [], workspaces = [], locations = [], currentUser, currentUserId, currentWorkspaceId, selectedLocationId, sharedMode, onClose, onSave, onLogout, onNavigate, currentSpace, householdTimezone, salaryConfig = DEFAULT_SALARY, selectedTask, selectedItem, selectedRecipe }) => {
  const consumableItems = items.filter((item) => item.qty > 0 && (!item.is_food || item.expiry_status !== "expired"));
  const selectedLocation = locations.find((location) => location.id === selectedLocationId);
  const [amount, setAmount] = useState("86.40");
  const [title, setTitle] = useState("日用品");
  const [expenseCategory, setExpenseCategory] = useState("購物");
  const [payer, setPayer] = useState(currentUserId || members[0]?.id || "");
  const [shared, setShared] = useState(!!sharedMode);
  const [itemId, setItemId] = useState(selectedItem?.id || (type === "item" ? consumableItems[0] : items[0])?.id || "");
  const [destination, setDestination] = useState(selectedLocationId || locations[0]?.id || "");
  const [salaryType, setSalaryType] = useState(salaryConfig.type);
  const [salaryAmount, setSalaryAmount] = useState(String(salaryConfig.amount));
  const [hoursPerDay, setHoursPerDay] = useState(String(salaryConfig.hoursPerDay));
  const [daysPerWeek, setDaysPerWeek] = useState(String(salaryConfig.daysPerWeek));
  const [payday, setPayday] = useState(String(salaryConfig.payday));
  const [startTime, setStartTime] = useState(salaryConfig.startTime);
  const [salarySentence, setSalarySentence] = useState(`${salaryConfig.type === "annual" ? "年薪" : "月薪"} ${salaryConfig.amount}，每天工作 ${salaryConfig.hoursPerDay} 小時，每週工作 ${salaryConfig.daysPerWeek} 天，每月 ${salaryConfig.payday} 號發薪，早上 ${Number(String(salaryConfig.startTime).split(":")[0])} 點上班`);
  const [parseNote, setParseNote] = useState("");
  const [choreTitle, setChoreTitle] = useState("");
  const [choreArea, setChoreArea] = useState(locations[0]?.path || "全屋");
  const [choreTarget, setChoreTarget] = useState("any");
  const [choreDue, setChoreDue] = useState("今天");
  const [choreNote, setChoreNote] = useState("");
  const [reminderChoice, setReminderChoice] = useState("20 分鐘後");
  const [newItemName, setNewItemName] = useState(selectedItem?.name || "");
  const [newItemQty, setNewItemQty] = useState("1");
  const [newItemUnit, setNewItemUnit] = useState(selectedItem?.unit || "件");
  const [newItemSafe, setNewItemSafe] = useState(String(selectedItem?.safe ?? 1));
  const [newItemCategory, setNewItemCategory] = useState(selectedItem?.category || "日用");
  const [newItemLocation, setNewItemLocation] = useState(selectedItem?.location_id || selectedLocationId || locations[0]?.id || "");
  const [newItemIsFood, setNewItemIsFood] = useState(!!selectedItem?.is_food);
  const [newItemStoredAt, setNewItemStoredAt] = useState(() => localDateInput(new Date(), householdTimezone));
  const [newItemExpiresAt, setNewItemExpiresAt] = useState("");
  const [newItemBarcode, setNewItemBarcode] = useState(selectedItem?.barcode || "");
  const [newItemBrand, setNewItemBrand] = useState(selectedItem?.brand || "");
  const [newItemPackageSize, setNewItemPackageSize] = useState(selectedItem?.package_size || "");
  const [newItemImageUrl, setNewItemImageUrl] = useState(selectedItem?.product_image_url || selectedItem?.image_url || "");
  const [newItemProductSource, setNewItemProductSource] = useState(selectedItem?.product_source || "");
  const [foodStoredAt, setFoodStoredAt] = useState(localDateInput(selectedItem?.stored_at || new Date(), householdTimezone));
  const [foodExpiresAt, setFoodExpiresAt] = useState(selectedItem?.expires_at ? localDateInput(selectedItem.expires_at) : "");
  const [householdName, setHouseholdName] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [joinPreview, setJoinPreview] = useState(null);
  const [locationName, setLocationName] = useState("");
  const [locationType, setLocationType] = useState(selectedLocation?.kind === "facility" ? "shelf" : selectedLocation?.kind === "room" ? "cabinet" : "room");
  const [locationParent, setLocationParent] = useState(selectedLocationId || "");
  const [inviteReceipt, setInviteReceipt] = useState(null);
  const [copyNote, setCopyNote] = useState("");
  const [avatarValue, setAvatarValue] = useState(currentUser?.avatar_value || shortName(currentUser?.display_name));
  const [avatarToneValue, setAvatarToneValue] = useState(avatarTone(currentUser, "ink") || "ink");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const newItemLocationTouched = useRef(false);
  const scannerAutofillRef = useRef(null);
  const [clientRequestId] = useState(() => window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`);

  const titles = { expense: "記一筆", item: "取用物品", move: "移動位置", scan: "掃一掃", food: "編輯食材保鮮", recipe: "食譜建議", invite: "邀請成員", join: "加入小家", household: "建立小家", location: "新增位置", space: "切換空間", salary: "設定收入時鐘", task: "發佈家務", reminder: "晚一點提醒我", avatar: "設計我的頭像" };
  const parseSalarySentence = () => {
    const text = salarySentence.replace(/,/g, "");
    let found = 0;
    const pay = text.match(/(月薪|年薪)\s*(?:是|為|为)?\s*[¥￥]?\s*([\d.]+)/);
    if (pay) { setSalaryType(pay[1] === "年薪" ? "annual" : "monthly"); setSalaryAmount(pay[2]); found += 1; }
    const hours = text.match(/每天(?:工作)?\s*([\d.]+)\s*(?:小時|小时|H)/i);
    if (hours) { setHoursPerDay(hours[1]); found += 1; }
    const days = text.match(/每(?:週|周)(?:工作)?\s*(\d+)\s*天/);
    if (days) { setDaysPerWeek(days[1]); found += 1; }
    const day = text.match(/每月\s*(\d+)\s*(?:號|号)/);
    if (day) { setPayday(day[1]); found += 1; }
    const start = text.match(/(?:早上|上午|上班(?:時間|时间)?(?:是|為|为)?)[^\d]*(\d{1,2})(?:[:：](\d{2}))?\s*(?:點|点|時|时)?/);
    if (start) { setStartTime(`${String(clamp(start[1], 0, 23)).padStart(2, "0")}:${String(clamp(start[2] || 0, 0, 59)).padStart(2, "0")}`); found += 1; }
    setParseNote(found ? `已識別 ${found} 項設定，請核對後保存。` : "沒有識別到薪資設定，請按示例重新描述。");
  };
  const preferFoodLocation = () => {
    if (selectedItem || newItemLocationTouched.current) return;
    const preferred = ["fridge", "freezer", "pantry"].map((facilityType) => locations.find((location) => location.kind === "facility" && location.facility_type === facilityType)).find(Boolean);
    if (preferred) setNewItemLocation(preferred.id);
  };
  const toggleNewItemFood = () => setNewItemIsFood((current) => {
    const next = !current;
    if (next) preferFoodLocation();
    return next;
  });
  const clearScannerAutofill = (barcode) => {
    const previous = scannerAutofillRef.current;
    if (previous) {
      if (previous.name != null && newItemName === previous.name) setNewItemName("");
      if (previous.category != null && newItemCategory === previous.category) setNewItemCategory("日用");
      if (previous.unit != null && newItemUnit === previous.unit) setNewItemUnit("件");
      if (previous.brand != null && newItemBrand === previous.brand) setNewItemBrand("");
      if (previous.packageSize != null && newItemPackageSize === previous.packageSize) setNewItemPackageSize("");
      if (previous.imageUrl != null && newItemImageUrl === previous.imageUrl) setNewItemImageUrl("");
      if (previous.source != null && newItemProductSource === previous.source) setNewItemProductSource("");
      if (typeof previous.isFood === "boolean" && newItemIsFood === previous.isFood) {
        setNewItemIsFood(false);
        setNewItemStoredAt(localDateInput(new Date(), householdTimezone));
        setNewItemExpiresAt("");
      }
    }
    setNewItemBarcode(barcode || "");
    scannerAutofillRef.current = null;
  };
  const applyScannedProduct = (product, barcode) => {
    if (!product) return;
    if (product.reset) {
      clearScannerAutofill(product.code || barcode || "");
      return;
    }
    const hasProductField = (key) => Object.prototype.hasOwnProperty.call(product, key);
    if (product.name) setNewItemName(product.name);
    if (product.category) setNewItemCategory(product.category);
    if (product.unit) setNewItemUnit(product.unit);
    setNewItemBarcode(product.code || barcode || "");
    if (hasProductField("brand")) setNewItemBrand(product.brand || "");
    if (hasProductField("package_size")) setNewItemPackageSize(product.package_size || "");
    if (hasProductField("image_url")) setNewItemImageUrl(product.image_url || "");
    if (hasProductField("source")) setNewItemProductSource(product.source || "");
    const hasFoodValue = typeof product.is_food === "boolean" || product.is_food === 0 || product.is_food === 1;
    if (hasFoodValue) {
      const isFood = Boolean(product.is_food);
      setNewItemIsFood(isFood);
      if (isFood) preferFoodLocation();
    }
    scannerAutofillRef.current = {
      name: product.name || null,
      category: product.category || null,
      unit: product.unit || null,
      brand: hasProductField("brand") ? (product.brand || "") : null,
      packageSize: hasProductField("package_size") ? (product.package_size || "") : null,
      imageUrl: hasProductField("image_url") ? (product.image_url || "") : null,
      source: hasProductField("source") ? (product.source || "") : null,
      isFood: hasFoodValue ? Boolean(product.is_food) : undefined,
    };
  };
  const applyFoodPhotoSuggestion = (suggestion) => {
    if (!suggestion || typeof suggestion !== "object") return;
    const text = (value) => typeof value === "string" ? value.trim() : "";
    const name = text(suggestion.name);
    const brand = text(suggestion.brand);
    const category = text(suggestion.category);
    const unit = text(suggestion.unit);
    const packageSize = text(suggestion.package_size);
    const storageHint = text(suggestion.storage_hint).toLowerCase();
    const source = text(suggestion.source);
    const quantity = Number(suggestion.quantity);
    const expiryDays = Number(suggestion.expiry_days);
    if (name) setNewItemName(name);
    if (brand) setNewItemBrand(brand);
    if (category) setNewItemCategory(category);
    if (unit) setNewItemUnit(unit);
    if (packageSize) setNewItemPackageSize(packageSize);
    if (Number.isFinite(quantity) && quantity > 0) setNewItemQty(String(Math.max(1, Math.round(quantity * 100) / 100)));
    setNewItemIsFood(true);
    preferFoodLocation();
    if (!newItemLocationTouched.current && storageHint) {
      const preferredTypes = storageHint.includes("freez") || storageHint.includes("冷凍")
        ? ["freezer", "fridge", "pantry"]
        : storageHint.includes("pantry") || storageHint.includes("常溫") || storageHint.includes("室溫")
          ? ["pantry", "fridge", "freezer"]
          : ["fridge", "freezer", "pantry"];
      const preferred = preferredTypes.map((facilityType) => locations.find((location) => location.kind === "facility" && location.facility_type === facilityType)).find(Boolean);
      if (preferred) setNewItemLocation(preferred.id);
    }
    if (Number.isFinite(expiryDays) && expiryDays >= 0) setNewItemExpiresAt(localDatePlusDays(newItemStoredAt, expiryDays, householdTimezone));
    setNewItemProductSource(source ? `AI VISION · ${source}` : "AI VISION");
    scannerAutofillRef.current = null;
  };
  const chooseExpenseCategory = (category) => {
    setTitle((current) => !current.trim() || current === EXPENSE_DEFAULT_TITLE[expenseCategory] ? EXPENSE_DEFAULT_TITLE[category] : current);
    setExpenseCategory(category);
  };
  const salaryDraft = {
    type: salaryType,
    amount: Number(salaryAmount),
    hoursPerDay: Number(hoursPerDay),
    daysPerWeek: Number(daysPerWeek),
    payday: Number(payday),
    startTime,
  };
  const salaryPreview = salarySnapshot(salaryDraft, new Date());
  const locationTypeConfig = LOCATION_TYPES.find((entry) => entry[0] === locationType) || LOCATION_TYPES[0];
  const locationParentOptions = locations.filter((location) => locationTypeConfig[2] === "facility" ? location.kind === "room" : locationTypeConfig[2] === "shelf" ? location.kind === "facility" : false);
  const chooseLocationType = (nextType) => {
    const nextConfig = LOCATION_TYPES.find((entry) => entry[0] === nextType) || LOCATION_TYPES[0];
    const nextParents = locations.filter((location) => nextConfig[2] === "facility" ? location.kind === "room" : nextConfig[2] === "shelf" ? location.kind === "facility" : false);
    const preferredParent = nextConfig[2] === "facility"
      ? (selectedLocation?.kind === "room" ? selectedLocation.id : selectedLocation?.parent_id)
      : nextConfig[2] === "shelf" && selectedLocation?.kind === "facility" ? selectedLocation.id : null;
    setLocationType(nextType);
    setLocationParent((current) => {
      if (nextConfig[2] === "room") return "";
      if (nextParents.some((location) => String(location.id) === String(current))) return current;
      if (nextParents.some((location) => location.id === preferredParent)) return preferredParent;
      return nextParents[0]?.id || "";
    });
  };
  const invalidFoodDates = (isFood, storedAt, expiresAt) => !!isFood && (!storedAt || (!!expiresAt && expiresAt < storedAt));
  const formatJoinCode = (value) => {
    const clean = String(value || "").toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
    return clean.length > 4 ? `${clean.slice(0, 4)}-${clean.slice(4)}` : clean;
  };
  const runSheetAction = async (action) => {
    if (saving) return null;
    setSaving(true);
    setSaveError("");
    try {
      return await action();
    } catch (error) {
      setSaveError(error.message || "現在無法完成操作，請稍後再試。");
      return null;
    } finally {
      setSaving(false);
    }
  };
  const save = () => runSheetAction(async () => {
    const item = items.find((i) => i.id === Number(itemId));
    if (type === "task" && !choreTitle.trim()) return null;
    const payload = {
      amount: Number(amount), title, category: expenseCategory, payer, shared, item,
      destination: locations.find((location) => location.id === Number(destination)), salary: salaryDraft,
      task: { title: choreTitle.trim(), note: choreNote.trim(), area: choreArea, preferredMemberId: choreTarget, due: choreDue },
      taskId: selectedTask?.id,
      reminder: reminderChoice,
      newItem: { name: newItemName.trim(), quantity: Number(newItemQty), unit: newItemUnit.trim(), safe_quantity: Number(newItemSafe), category: newItemCategory.trim(), location_id: Number(newItemLocation) || null, is_food: newItemIsFood, stored_at: newItemIsFood ? newItemStoredAt : null, expires_at: newItemIsFood && newItemExpiresAt ? newItemExpiresAt : null, barcode: newItemBarcode || null, brand: newItemBrand.trim() || null, package_size: newItemPackageSize.trim() || null, image_url: newItemImageUrl || null, product_source: newItemProductSource || null },
      food: { is_food: true, stored_at: foodStoredAt, expires_at: foodExpiresAt || null, expected_version: selectedItem?.version },
      household: { name: householdName.trim(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Singapore" },
      location: { name: locationName.trim(), kind: locationTypeConfig[2], facility_type: locationTypeConfig[3], parent_id: locationTypeConfig[2] === "room" ? null : Number(locationParent) || null },
      avatar: { avatar_value: avatarValue.trim(), avatar_tone: avatarToneValue },
      code: joinCode,
      clientRequestId,
    };
    if (type === "join") {
      if (!joinPreview) {
        const result = await onSave("joinPreview", payload);
        if (result?.invite) setJoinPreview(result.invite);
        return result;
      }
      return onSave("joinAccept", payload);
    }
    const result = await onSave(type, payload);
    if (type === "invite" && result?.invite) setInviteReceipt(result.invite);
    return result;
  });
  const chooseWorkspace = (workspace) => runSheetAction(() => onSave("space", { workspace }));
  const logout = () => runSheetAction(onLogout);
  const copyInvite = async () => {
    if (!inviteReceipt?.code) return;
    const message = `加入「${currentSpace}」：家庭邀請碼 ${inviteReceipt.code}`;
    try {
      await navigator.clipboard.writeText(message);
      setCopyNote("已複製，可直接傳給家人。");
    } catch (error) {
      setCopyNote(`請記下邀請碼：${inviteReceipt.code}`);
    }
  };

  const saveLabel = type === "scan" ? (selectedItem?.is_food ? "建立新批次" : "確認入庫") : type === "food" ? "保存保鮮資料" : type === "invite" ? "建立邀請碼" : type === "join" ? (joinPreview ? "確認加入" : "查看邀請") : type === "household" ? "建立小家" : type === "location" ? "建立位置" : type === "salary" ? "保存收入時鐘" : type === "avatar" ? "保存頭像" : type === "task" ? (sharedMode ? "發佈到小家" : "保存待辦") : type === "reminder" ? "設定提醒" : "確認記錄";
  const saveDisabled = saving
    || (type === "task" && !choreTitle.trim())
    || (type === "scan" && (!newItemName.trim() || invalidFoodDates(newItemIsFood, newItemStoredAt, newItemExpiresAt)))
    || (type === "food" && (!selectedItem || invalidFoodDates(true, foodStoredAt, foodExpiresAt)))
    || (type === "item" && !consumableItems.length)
    || (type === "move" && !items.length)
    || (type === "move" && !destination)
    || (type === "expense" && (!title.trim() || !Number.isFinite(Number(amount)) || Number(amount) <= 0))
    || (type === "household" && !householdName.trim())
    || (type === "join" && formatJoinCode(joinCode).replace("-", "").length !== 8)
    || (type === "location" && (!locationName.trim() || (locationTypeConfig[2] !== "room" && !locationParent)));
  const selectedRecipeMatched = recipeList(selectedRecipe, "matched_ingredients");
  const selectedRecipeUseFirst = recipeUseFirstList(selectedRecipe, items);
  const selectedRecipeSteps = recipeList(selectedRecipe, "steps");
  const selectedRecipeShopping = recipeList(selectedRecipe, "shopping_list");

  return <div className="sheet-layer" role="presentation" onMouseDown={saving ? undefined : onClose}>
    <section className="action-sheet" data-testid="quick-sheet" role="dialog" aria-modal="true" aria-label={titles[type]} onMouseDown={(e) => e.stopPropagation()}>
      <div className="sheet-head"><div><div className="folio-line" style={{ marginBottom: 3 }}>QUICK ACTION</div><h2>{titles[type]}</h2></div><button className="sheet-close" onClick={onClose} disabled={saving} aria-label="關閉"><Icon name="x" size={17}/></button></div>
      <div className="sheet-body">
        {type === "avatar" && <>
          <div className="avatar-studio-preview">
            <Avatar member={{ avatar_value: avatarValue.trim() || shortName(currentUser?.display_name), avatar_tone: avatarToneValue }} name={shortName(currentUser?.display_name)} />
            <div><span className="field-label">PREVIEW / 頭像預覽</span><strong>{currentUser?.display_name || "我"}</strong></div>
          </div>
          <div className="form-group"><label className="field-label">MARK / 文字、字母或 EMOJI</label><input className="home-field avatar-mark-input" data-testid="avatar-value" maxLength="8" value={avatarValue} onChange={(event) => setAvatarValue(event.target.value)} autoFocus/></div>
          <div className="form-group"><label className="field-label">QUICK MARKS / 預選</label><div className="avatar-mark-options">{AVATAR_PRESETS.map((mark) => <button type="button" key={mark} className={avatarValue === mark ? "on" : ""} onClick={() => setAvatarValue(mark)} aria-label={`使用 ${mark} 作為頭像`}>{mark}</button>)}</div></div>
          <div className="form-group"><label className="field-label">BACKGROUND / 預選底色</label><div className="avatar-tone-options">{AVATAR_TONES.map((tone) => <button type="button" key={tone} className={avatarToneValue === tone ? "on" : ""} onClick={() => setAvatarToneValue(tone)} aria-label={`選擇 ${tone} 底色`} title={`選擇 ${tone} 底色`}><span className={`avatar-tone-swatch ${tone}`}/></button>)}</div></div>
        </>}
        {type === "task" && <>
          <p className="sheet-copy">把需要說清楚，讓家人自由接手。這不是指令，而是一個可以被回應的生活請求。</p>
          <div className="form-group"><label className="field-label">WHAT / 要做什麼</label><input className="home-field" data-testid="chore-title" maxLength="56" value={choreTitle} onChange={(e) => setChoreTitle(e.target.value)} placeholder="例如：衣服需要洗一下" autoFocus/></div>
          <div className="form-group"><label className="field-label">WHERE / 在哪裏</label><select className="home-field" data-testid="chore-area" value={choreArea} onChange={(e) => setChoreArea(e.target.value)}>{[...locations.map((location) => location.path), "全屋"].filter((value, index, all) => all.indexOf(value) === index).map((value) => <option key={value}>{value}</option>)}</select></div>
          <div className="form-group"><label className="field-label">FOR / 希望誰處理</label><div className="seg-control">{[["any","任何人"], ...members.map((member) => [String(member.id), shortName(member.display_name)])].map(([id, label]) => <button key={id} className={String(choreTarget) === id ? "on" : ""} onClick={() => setChoreTarget(id)}>{label}</button>)}</div></div>
          <div className="form-group"><label className="field-label">WHEN / 希望何時完成</label><div className="seg-control due-control">{["今天","今晚","本週","不限"].map((due) => <button key={due} className={choreDue === due ? "on" : ""} onClick={() => setChoreDue(due)}>{due}</button>)}</div></div>
          <div className="form-group"><label className="field-label">NOTE / 補充說明（選填）</label><textarea className="home-field chore-note" data-testid="chore-note" maxLength="120" value={choreNote} onChange={(e) => setChoreNote(e.target.value)} placeholder="補充一點背景，語氣可以很自然。"/></div>
        </>}
        {type === "reminder" && <>
          <div className="reminder-task"><span className="field-label">REMIND ME ABOUT</span><strong>{selectedTask?.title || "這件家務"}</strong><p>{selectedTask?.area}</p></div>
          <div className="reminder-grid" data-testid="reminder-options">
            {["20 分鐘後","1 小時後","今晚 20:00","明天 09:00"].map((choice) => <button key={choice} className={reminderChoice === choice ? "on" : ""} onClick={() => setReminderChoice(choice)}><Icon name="clock" size={14}/>{choice}</button>)}
          </div>
          <p className="sheet-copy reminder-note">只延後你的提醒，其他家庭成員仍然可以接手或完成。</p>
        </>}
        {type === "expense" && <>
          <div className="form-group"><label className="field-label">AMOUNT / 金額</label><input className="home-field amount-field" type="number" inputMode="decimal" min="0.01" step="0.01" required value={amount} onChange={(e) => setAmount(e.target.value)} aria-label="金額"/></div>
          <div className="form-group"><label className="field-label">CATEGORY / 分類</label><div className="expense-category-grid">{EXPENSE_CATEGORIES.map((category) => <button type="button" key={category} className={expenseCategory === category ? "on" : ""} onClick={() => chooseExpenseCategory(category)}>{category}</button>)}</div></div>
          <div className="form-group"><label className="field-label">ITEM / 項目</label><input className="home-field" value={title} onChange={(e) => setTitle(e.target.value)} aria-label="開銷項目"/></div>
          <div className="form-group"><label className="field-label">PAID BY / 誰先墊付</label><div className="seg-control">{members.map((member) => <button key={member.id} className={Number(payer) === member.id ? "on" : ""} onClick={() => setPayer(member.id)}>{shortName(member.display_name)}</button>)}</div></div>
          {sharedMode ? <div className="form-group toggle-row"><div className="toggle-copy"><strong>家庭共同開銷</strong><span>保存後由 {members.length || 1} 位成員平均分攤</span></div><button className={`square-toggle ${shared ? "on" : ""}`} onClick={() => setShared((v) => !v)} aria-label="家庭共同開銷"><Icon name="check" size={14}/></button></div> : <p className="sheet-copy">這筆記錄只保存在你的私人空間。</p>}
        </>}
        {type === "salary" && <>
          <p className="sheet-copy">薪資設定屬於你的私人資料，家庭成員不可見。收入只在設定的工作日與工作時段內逐秒增加；下班和休息日自動暫停。</p>
          <div className="form-group salary-ask">
            <label className="field-label">TELL THE HOUSEKEEPER / 對管家說</label>
            <textarea className="home-field salary-sentence" data-testid="salary-sentence" value={salarySentence} onChange={(e) => setSalarySentence(e.target.value)} aria-label="用一句話描述薪資設定"/>
            <button className="text-action" data-testid="salary-parse" style={{ width: "100%", marginTop: 8 }} onClick={parseSalarySentence}><Icon name="sparkle" size={14}/>套用這句話</button>
            {parseNote && <div className="salary-parse-note">{parseNote}</div>}
          </div>
          <div className="form-group"><label className="field-label">SALARY TYPE / 薪資方式</label><div className="seg-control"><button className={salaryType === "monthly" ? "on" : ""} onClick={() => setSalaryType("monthly")}>月薪</button><button className={salaryType === "annual" ? "on" : ""} onClick={() => setSalaryType("annual")}>年薪</button></div></div>
          <div className="form-group"><label className="field-label">AMOUNT / {salaryType === "annual" ? "年薪" : "月薪"}</label><input className="home-field amount-field" data-testid="salary-amount" type="number" min="0" step="100" value={salaryAmount} onChange={(e) => setSalaryAmount(e.target.value)} aria-label="薪資金額"/></div>
          <div className="salary-grid form-group">
            <label><span className="field-label">HOURS / 每天小時</span><input className="home-field" data-testid="salary-hours" type="number" min="0.5" max="24" step="0.5" value={hoursPerDay} onChange={(e) => setHoursPerDay(e.target.value)}/></label>
            <label><span className="field-label">DAYS / 每週天數</span><input className="home-field" data-testid="salary-days" type="number" min="1" max="7" step="1" value={daysPerWeek} onChange={(e) => setDaysPerWeek(e.target.value)}/></label>
            <label><span className="field-label">PAYDAY / 發薪日</span><input className="home-field" data-testid="salary-payday" type="number" min="1" max="31" step="1" value={payday} onChange={(e) => setPayday(e.target.value)}/></label>
            <label><span className="field-label">START / 上班時間</span><input className="home-field" data-testid="salary-start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)}/></label>
          </div>
          <div className="salary-preview">
            <span>預計月薪</span><strong>{yuan(salaryPreview.monthly)}</strong>
            <span>每小時收入</span><strong>{yuan(salaryPreview.hourlyRate)}</strong>
            <span>本月工作日</span><strong>{salaryPreview.scheduledDays} 天</strong>
          </div>
          <p className="sheet-copy" style={{ marginTop: 10 }}>每週工作天數按週一開始連續計算，例如 5 天代表週一至週五。</p>
        </>}
        {type === "item" && <>
          <p className="sheet-copy">選擇剛剛取用的物品。過期食材不會出現在清單；請從庫存列直接標記丟棄。</p>
          {consumableItems.length ? <div className="form-group"><label className="field-label">ITEM / 物品</label><select className="home-field" value={itemId} onChange={(e) => setItemId(Number(e.target.value))}>{consumableItems.map((i) => <option key={i.id} value={i.id}>{i.name} · 現有 {i.qty}{i.unit}{i.is_food ? " · BATCH" : ""}</option>)}</select></div> : <div className="empty-sheet">目前沒有可取用的物品。</div>}
        </>}
        {type === "move" && <>
          {items.length ? <div className="form-group"><label className="field-label">ITEM / 物品</label><select className="home-field" value={itemId} onChange={(e) => setItemId(Number(e.target.value))}>{items.map((i) => <option key={i.id} value={i.id}>{i.name} · {i.place}</option>)}</select></div> : <div className="empty-sheet">還沒有物品可以移動。</div>}
          <div className="form-group"><label className="field-label">TO / 新位置</label><select className="home-field" value={destination} onChange={(e) => setDestination(Number(e.target.value))}>{locations.map((location) => <option key={location.id} value={location.id}>{location.path}</option>)}</select></div>
        </>}
        {type === "scan" && <>
          <p className="sheet-copy">{selectedItem?.is_food ? `為「${selectedItem.name}」建立獨立的新批次；存放與到期時間不會和舊批混在一起。` : "掃描後核對名稱和數量；也可以直接手動輸入。"}</p>
          <BarcodeScanner onCode={setNewItemBarcode} onProduct={applyScannedProduct}/>
          <FoodPhotoRecognizer workspaceId={currentWorkspaceId} onSuggestion={applyFoodPhotoSuggestion}/>
          <div className="form-group"><label className="field-label">ITEM / 物品名稱</label><input className="home-field" data-testid="new-item-name" value={newItemName} onChange={(event) => setNewItemName(event.target.value)} placeholder="例如：洗衣液"/></div>
          <div className="product-fields-grid form-group">
            <label><span className="field-label">BRAND / 品牌</span><input className="home-field" value={newItemBrand} onChange={(event) => setNewItemBrand(event.target.value)} placeholder="選填"/></label>
            <label><span className="field-label">PACKAGE / 包裝規格</span><input className="home-field" value={newItemPackageSize} onChange={(event) => setNewItemPackageSize(event.target.value)} placeholder="例如：500 ml"/></label>
          </div>
          {(newItemBarcode || newItemProductSource) && <div className="product-trace"><span>BARCODE {newItemBarcode || "--"}</span>{newItemProductSource && <span>SOURCE {newItemProductSource}</span>}</div>}
          <div className="salary-grid form-group">
            <label><span className="field-label">QTY / 數量</span><input className="home-field" type="number" min="0" step="1" value={newItemQty} onChange={(event) => setNewItemQty(event.target.value)}/></label>
            <label><span className="field-label">UNIT / 單位</span><input className="home-field" value={newItemUnit} onChange={(event) => setNewItemUnit(event.target.value)}/></label>
            <label><span className="field-label">SAFE / 安全數量</span><input className="home-field" type="number" min="0" step="1" value={newItemSafe} onChange={(event) => setNewItemSafe(event.target.value)}/></label>
            <label><span className="field-label">CATEGORY / 分類</span><input className="home-field" value={newItemCategory} onChange={(event) => setNewItemCategory(event.target.value)}/></label>
          </div>
          <div className="form-group"><label className="field-label">PLACE / 收納位置</label><select className="home-field" value={newItemLocation} onChange={(event) => { newItemLocationTouched.current = true; setNewItemLocation(Number(event.target.value)); }}>{locations.map((location) => <option key={location.id} value={location.id}>{location.path}</option>)}</select></div>
          <div className="form-group toggle-row"><div className="toggle-copy"><strong>這是食材</strong><span>按批次追蹤存放日與到期日</span></div><button className={`square-toggle ${newItemIsFood ? "on" : ""}`} onClick={toggleNewItemFood} aria-label="這是食材"><Icon name="check" size={14}/></button></div>
          {newItemIsFood && <>
            <div className="food-date-grid form-group">
              <label><span className="field-label">STORED / 存放日</span><input className="home-field" type="date" value={newItemStoredAt} onChange={(event) => setNewItemStoredAt(event.target.value)}/></label>
              <label><span className="field-label">EXPIRES / 到期日</span><input className="home-field" type="date" min={newItemStoredAt} value={newItemExpiresAt} onChange={(event) => setNewItemExpiresAt(event.target.value)}/></label>
            </div>
            {newItemExpiresAt && newItemExpiresAt < newItemStoredAt && <div className="food-date-error">到期日不能早於存放日。</div>}
            <p className="food-safety-note">每次補貨建立新批次，避免混淆到期日。到期日依家庭記錄計算；如有異味、變色或包裝異常，應直接丟棄。</p>
          </>}
        </>}
        {type === "food" && <>
          <div className="food-sheet-item"><span className="location-node-icon"><Icon name="clock" size={16}/></span><div><span className="field-label">FOOD BATCH / 食材批次</span><strong>{selectedItem?.name || "食材"}</strong><small>{selectedItem?.place}</small></div></div>
          <div className="food-timeline">
            <span>STORED</span><i/><span>EXPIRY</span>
            <strong>{selectedItem?.stored_days ?? 0} 天</strong><b className={foodStatusMeta(selectedItem).tone}>{foodStatusMeta(selectedItem).label}</b>
          </div>
          <div className="food-date-grid form-group">
            <label><span className="field-label">STORED / 存放日</span><input className="home-field" type="date" value={foodStoredAt} onChange={(event) => setFoodStoredAt(event.target.value)}/></label>
            <label><span className="field-label">EXPIRES / 到期日</span><input className="home-field" type="date" min={foodStoredAt} value={foodExpiresAt} onChange={(event) => setFoodExpiresAt(event.target.value)}/></label>
          </div>
          {foodExpiresAt && foodExpiresAt < foodStoredAt && <div className="food-date-error">到期日不能早於存放日。</div>}
          <p className="food-safety-note">每次補貨建立新批次，避免混淆到期日。到期日依家庭記錄計算；如有異味、變色或包裝異常，應直接丟棄。</p>
        </>}
        {type === "recipe" && <>
          <div className="recipe-sheet-head"><span className="recipe-index"><Icon name="sparkle" size={14}/></span><div><span className="field-label">COOK WITH WHAT YOU HAVE</span><h3>{selectedRecipe?.title || "食譜建議"}</h3><p>{selectedRecipe?.reason}</p></div><strong>{Number(selectedRecipe?.minutes) || 20}<small> MIN</small></strong></div>
          {selectedRecipeUseFirst.length > 0 && <div className="recipe-sheet-priority"><span>USE FIRST / 優先使用</span><strong>{selectedRecipeUseFirst.join("、")}</strong></div>}
          <div className="recipe-sheet-stock">
            <div><span className="field-label">READY / 已備原料</span><p>{selectedRecipeMatched.join("、") || "沒有安全可用的已備原料"}</p></div>
            <div><span className="field-label">MISSING / 缺少原料</span><p>{recipeList(selectedRecipe, "missing_ingredients").join("、") || "主要原料已齊；份量請再確認"}</p></div>
          </div>
          {selectedRecipeShopping.length > 0 && <div className="recipe-sheet-shopping"><span className="field-label">SHOPPING LIST / 需要補充</span><p>{selectedRecipeShopping.join("、")}</p></div>}
          <div className="recipe-steps"><span className="field-label">METHOD / 做法</span>{selectedRecipeSteps.length ? selectedRecipeSteps.map((step, index) => <div key={`${step}-${index}`}><b>{String(index + 1).padStart(2, "0")}</b><p>{step}</p></div>) : <div><b>--</b><p>目前沒有做法步驟。</p></div>}</div>
          <p className="food-safety-note">已過期食材不會列入可用原料；烹飪前仍請檢查氣味、顏色與包裝狀態。</p>
        </>}
        {type === "invite" && <>
          {inviteReceipt ? <div className="invite-receipt sheet-receipt" data-testid="invite-receipt"><span className="field-label">INVITE CODE / 家庭邀請碼</span><strong>{inviteReceipt.code}</strong><p>七天內可使用一次；收入與私人空間不會共享。</p><button className="text-action primary" style={{ width: "100%", marginTop: 14 }} onClick={copyInvite}><Icon name="clipboard" size={14}/>複製邀請資訊</button>{copyNote && <div className="salary-parse-note">{copyNote}</div>}</div> : <><p className="sheet-copy">建立一組單次邀請碼。家人加入「{currentSpace}」後，可以共同管理家務、物品與家庭賬本，但看不到你的私人收入。</p><div className="invite-sheet-note"><Icon name="shield" size={18}/><span>邀請碼七天內有效，使用一次後立即失效。</span></div></>}
        </>}
        {type === "household" && <>
          <p className="sheet-copy">建立共享空間後，可以邀請家人共同管理物品、家務與家庭賬本；你的私人收入仍然只對自己可見。</p>
          <div className="form-group"><label className="field-label">HOUSEHOLD NAME / 小家名稱</label><input className="home-field" value={householdName} maxLength="40" onChange={(event) => setHouseholdName(event.target.value)} placeholder="例如：蔡家" autoFocus/></div>
        </>}
        {type === "join" && <>
          {joinPreview ? <div className="invite-preview"><span className="field-label">HOUSEHOLD</span><strong>{joinPreview.household.name}</strong><p>{joinPreview.inviter_name}邀請你加入 · {joinPreview.household.member_count} 位成員。私人資料不會自動共享。</p></div> : <><p className="sheet-copy">輸入家人提供的八位邀請碼，確認小家資訊後再加入。</p><div className="form-group"><label className="field-label">INVITE CODE / 邀請碼</label><input className="home-field invite-code-field" value={joinCode} maxLength="9" onChange={(event) => setJoinCode(formatJoinCode(event.target.value))} placeholder="ABCD-EFGH" autoFocus/></div></>}
        </>}
        {type === "location" && <>
          <p className="sheet-copy">先建立房間，再把櫃子、冰箱、桌子與層板放進真實的上一層位置。</p>
          <div className="form-group"><label className="field-label">TYPE / 位置類型</label><div className="location-type-grid">{LOCATION_TYPES.map(([id, label]) => <button key={id} className={locationType === id ? "on" : ""} onClick={() => chooseLocationType(id)}>{label}</button>)}</div></div>
          <div className="form-group"><label className="field-label">NAME / 名稱</label><input className="home-field" value={locationName} maxLength="60" onChange={(event) => setLocationName(event.target.value)} placeholder={locationType === "room" ? "例如：書房" : locationType === "fridge" ? "例如：廚房冰箱" : locationType === "shelf" ? "例如：第二層" : `例如：${locationTypeConfig[1]}`} autoFocus/></div>
          {locationTypeConfig[2] !== "room" && <div className="form-group"><label className="field-label">PARENT / 上一層位置</label><select className="home-field" value={locationParent} onChange={(event) => setLocationParent(Number(event.target.value))}><option value="">{locationTypeConfig[2] === "facility" ? "選擇房間" : "選擇設施"}</option>{locationParentOptions.map((location) => <option key={location.id} value={location.id}>{locationTypeMeta(location).label} · {location.path}</option>)}</select></div>}
        </>}
        {type === "space" && <>
          {workspaces.map((workspace) => <button key={workspace.id} className="space-option" disabled={saving} onClick={() => chooseWorkspace(workspace)}><span><strong>{workspace.name}</strong><span>{workspace.type === "personal" ? "PERSONAL · PRIVATE" : `HOUSEHOLD · ${workspace.member_count} MEMBERS`}</span></span>{workspace.id === currentWorkspaceId && <Icon name="check" size={15} color="var(--red)"/>}</button>)}
          <button className="space-option" disabled={saving} onClick={() => onNavigate("household")}><span><strong>建立一個小家</strong><span>新增家庭共享空間</span></span><Icon name="plus" size={14}/></button>
          <button className="space-option" disabled={saving} onClick={() => onNavigate("join")}><span><strong>加入現有小家</strong><span>使用家人的邀請碼</span></span><Icon name="arrow" size={14}/></button>
          <button className="space-option space-logout" disabled={saving} onClick={logout}><span><strong>退出個人模式</strong><span>清除此裝置上的個人登入</span></span><Icon name="arrow" size={14}/></button>
        </>}
        <EntryError>{saveError}</EntryError>
        {type === "recipe" ? <div className="sheet-actions single"><button className="text-action primary" onClick={onClose}>關閉食譜</button></div> : type !== "space" && <div className="sheet-actions"><button className="text-action" onClick={onClose} disabled={saving}>{inviteReceipt ? "完成" : "取消"}</button>{!inviteReceipt && <button className={`text-action ${["task", "reminder", "join", "household", "location", "food", "avatar"].includes(type) ? "primary" : "red"}`} data-testid={type === "task" ? "chore-submit" : "sheet-save"} onClick={save} disabled={saveDisabled}><Icon name={type === "scan" ? "scan" : type === "task" || type === "household" || type === "location" ? "plus" : type === "reminder" || type === "food" ? "clock" : "check"} size={14}/>{saving ? "正在保存…" : saveLabel}</button>}</div>}
      </div>
    </section>
  </div>;
};

const PersonalAuthShell = ({ step, en, title, sub, children, footer }) => <div className="personal-entry personal-rise">
  <header className="entry-top"><div className="entry-mark"><Icon name="home" size={18}/></div><strong>HOME<i>.</i></strong><span>{step}</span></header>
  <main className="entry-main">
    <div className="entry-folio"><div className="folio-line">{step} / {en}</div><h1>{title}</h1><p>{sub}</p></div>
    <div className="entry-form">{children}</div>
  </main>
  {footer && <footer className="entry-footer">{footer}</footer>}
</div>;

const EntryError = ({ children }) => children ? <div className="entry-error" role="alert"><Icon name="alert" size={15}/><span>{children}</span></div> : null;

const PersonalAuth = ({ onAuthenticated, initialError = "" }) => {
  const [mode, setMode] = useState("login");
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(initialError);
  const register = mode === "register";

  const changeMode = (next) => {
    setMode(next);
    setError("");
    setPassword("");
    setConfirm("");
  };
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    if (register && password !== confirm) {
      setError("兩次輸入的密碼不一致。");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const data = await personalPost(`/api/personal/auth/${register ? "register" : "login"}`, {
        username, display_name: displayName, password,
      });
      await onAuthenticated(data);
    } catch (requestError) {
      setError(requestError.message || "現在無法連線，請稍後再試。");
    } finally {
      setBusy(false);
    }
  };

  return <PersonalAuthShell
    step="01"
    en={register ? "ACCOUNT · CREATE" : "ACCOUNT · SIGN IN"}
    title={register ? "建立你的帳號" : "登入"}
    sub={register ? "先建立私人空間，再決定是否和家人共享。" : "回到你的私人空間與小家。"}
    footer={<span>PRIVATE BY DEFAULT · SHARED BY CHOICE</span>}
  >
    <div className="entry-segment" role="tablist" aria-label="登入或註冊">
      <button className={!register ? "on" : ""} onClick={() => changeMode("login")}>登入</button>
      <button className={register ? "on" : ""} onClick={() => changeMode("register")}>註冊</button>
    </div>
    <form className="entry-fields" onSubmit={submit}>
      {register && <label><span className="field-label">DISPLAY NAME / 怎麼稱呼你</span><input className="home-field" data-testid="auth-display-name" autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required/></label>}
      <label><span className="field-label">ACCOUNT / 帳號</span><input className="home-field" data-testid="auth-username" autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required/></label>
      <label><span className="field-label">PASSWORD / 密碼</span><span className="password-wrap"><input className="home-field" data-testid="auth-password" type={showPassword ? "text" : "password"} autoComplete={register ? "new-password" : "current-password"} minLength="8" value={password} onChange={(event) => setPassword(event.target.value)} required/><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "隱藏密碼" : "顯示密碼"}><Icon name={showPassword ? "eyeOff" : "eye"} size={16}/></button></span></label>
      {register && <label><span className="field-label">CONFIRM / 再次輸入密碼</span><input className="home-field" data-testid="auth-confirm" type={showPassword ? "text" : "password"} autoComplete="new-password" minLength="8" value={confirm} onChange={(event) => setConfirm(event.target.value)} required/><small className="entry-hint">至少 8 個字元</small></label>}
      <EntryError>{error}</EntryError>
      <button className="entry-submit" data-testid="auth-submit" disabled={busy}>{busy ? (register ? "正在建立…" : "正在登入…") : (register ? "建立帳號" : "登入 HOME")}{!busy && <Icon name="arrow" size={15}/>}</button>
    </form>
  </PersonalAuthShell>;
};

const PersonalOnboarding = ({ session, initialInvite, onReady, onLogout }) => {
  const [screen, setScreen] = useState(initialInvite ? "join" : "start");
  const [householdName, setHouseholdName] = useState(`${shortName(session.user?.display_name)}家`);
  const [code, setCode] = useState(initialInvite || "");
  const [preview, setPreview] = useState(null);
  const [created, setCreated] = useState(null);
  const [invite, setInvite] = useState(null);
  const [joined, setJoined] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const run = async (action) => {
    if (busy) return null;
    setBusy(true);
    setError("");
    try { return await action(); }
    catch (requestError) { setError(requestError.message); return null; }
    finally { setBusy(false); }
  };
  const previewInvite = async (value = code) => {
    const data = await run(() => personalPost("/api/personal/invites/preview", { code: value }));
    if (data) { setCode(data.invite.code); setPreview(data.invite); setScreen("preview"); }
  };
  useEffect(() => {
    if (initialInvite) previewInvite(initialInvite);
  }, []);
  const dismissInvite = () => {
    sessionStorage.removeItem(PERSONAL_INVITE_KEY);
    setCode("");
    setPreview(null);
    setScreen("start");
  };

  if (joined) return <PersonalAuthShell step="02" en="JOIN · COMPLETE" title={`你已加入${joined.name}`} sub="邀請已完成；如果資料載入中斷，可以安全地繼續，不會再次使用邀請碼。">
    <div className="created-house"><div className="created-check"><Icon name="check" size={24}/></div><p>你的私人空間仍然只對自己可見。</p></div>
    <EntryError>{error}</EntryError>
    <button className="entry-submit" disabled={busy} onClick={() => run(onReady)}>{busy ? "正在載入…" : "進入今日"}{!busy && <Icon name="arrow" size={15}/>}</button>
  </PersonalAuthShell>;

  if (screen === "start") return <PersonalAuthShell step="02" en="SET UP · 01 / 02" title="你要從哪裏開始？" sub="私人物品和私人賬本不會因加入小家而自動共享。" footer={<button className="entry-link" onClick={onLogout}>退出此帳號</button>}>
    <div className="entry-options">
      <button onClick={() => setScreen("create")}><span><strong>建立一個小家</strong><small>建立共享物品、家務與家庭賬本。</small></span><Icon name="arrow" size={16}/></button>
      <button onClick={() => setScreen("join")}><span><strong>加入現有小家</strong><small>使用家人傳給你的邀請連結或邀請碼。</small></span><Icon name="arrow" size={16}/></button>
      <button disabled={busy} onClick={() => run(async () => { await personalPost("/api/personal/onboarding/skip", {}); sessionStorage.removeItem(PERSONAL_INVITE_KEY); await onReady(); })}><span><strong>先使用我的空間</strong><small>只管理自己的物品和賬本。</small></span><Icon name="arrow" size={16}/></button>
    </div>
  </PersonalAuthShell>;

  if (screen === "create") return <PersonalAuthShell step="02" en="SET UP · 02 / 02" title="給這個小家一個名字" sub="只需要一個名字，房間和物品可以稍後慢慢整理。">
    <div className="entry-fields">
      <label><span className="field-label">HOUSEHOLD NAME / 小家名稱</span><input className="home-field" data-testid="household-name" maxLength="40" value={householdName} onChange={(event) => setHouseholdName(event.target.value)} placeholder="例如：蔡家" autoFocus/></label>
      <EntryError>{error}</EntryError>
      <div className="entry-actions"><button className="text-action" onClick={() => setScreen("start")}>返回</button><button className="entry-submit" data-testid="household-create" disabled={busy || !householdName.trim()} onClick={() => run(() => personalPost("/api/personal/households", { name: householdName.trim(), timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Singapore" })).then((data) => { if (data) { setCreated(data.workspace); setScreen("created"); } })}>{busy ? "正在建立…" : "建立小家"}</button></div>
    </div>
  </PersonalAuthShell>;

  if (screen === "created") return <PersonalAuthShell step="02" en="HOUSEHOLD · CREATED" title={`${created?.name || householdName}已建立`} sub="你現在是這個小家的管理者。">
    <div className="created-house"><div className="created-check"><Icon name="check" size={24}/></div>{invite ? <div className="invite-receipt"><span className="field-label">INVITE CODE / 家庭邀請碼</span><strong>{invite.code}</strong><p>七天內可使用一次。可以把這組代碼傳給家人。</p></div> : <p>先邀請家人一起管理，或直接進入今日。</p>}</div>
    <EntryError>{error}</EntryError>
    <div className="entry-actions vertical">
      <button className="text-action" disabled={busy || !!invite} onClick={() => run(() => personalPost("/api/personal/invites", { household_id: created.id })).then((data) => data && setInvite(data.invite))}><Icon name="plus" size={14}/>{invite ? "邀請已建立" : "邀請家人"}</button>
      <button className="entry-submit" disabled={busy} onClick={() => run(onReady)}>{busy ? "正在載入…" : "進入今日"}{!busy && <Icon name="arrow" size={15}/>}</button>
    </div>
  </PersonalAuthShell>;

  if (screen === "preview" && preview) return <PersonalAuthShell step="02" en="JOIN · PREVIEW" title={`${preview.inviter_name}邀請你加入`} sub="確認後才會共享家庭物品、家務與賬本。">
    <div className="invite-preview"><span className="field-label">HOUSEHOLD</span><strong>{preview.household.name}</strong><p>{preview.household.member_count} 位成員 · 你的私人空間仍只有你能看到。</p></div>
    <EntryError>{error}</EntryError>
    <div className="entry-actions"><button className="text-action" onClick={dismissInvite}>不是這個小家</button><button className="entry-submit" data-testid="invite-accept" disabled={busy} onClick={() => run(async () => { const response = await personalPost("/api/personal/invites/accept", { code }); sessionStorage.removeItem(PERSONAL_INVITE_KEY); setJoined(response.workspace); await onReady(); })}>{busy ? "正在加入…" : "確認加入"}</button></div>
  </PersonalAuthShell>;

  return <PersonalAuthShell step="02" en="JOIN · HOUSEHOLD" title="輸入家人給你的邀請碼" sub="邀請碼只用來確認小家，不會公開你的私人資料。">
    <div className="entry-fields">
      <label><span className="field-label">INVITE CODE / 邀請碼</span><input className="home-field invite-code-field" data-testid="invite-code" maxLength="9" value={code} onChange={(event) => setCode(event.target.value.toUpperCase())} placeholder="ABCD-EFGH" autoFocus/></label>
      <EntryError>{error}</EntryError>
      <div className="entry-actions"><button className="text-action" onClick={dismissInvite}>返回</button><button className="entry-submit" data-testid="invite-preview" disabled={busy || code.replace(/-/g, "").length !== 8} onClick={() => previewInvite()}>{busy ? "正在確認…" : "查看邀請"}</button></div>
    </div>
  </PersonalAuthShell>;
};

const PersonalLoading = () => <div className="entry-loading" data-testid="personal-loading"><div className="entry-mark"><Icon name="home" size={18}/></div><strong>HOME<i>.</i></strong><span>正在確認私人空間</span><div className="loading-rule"><i/></div></div>;

const TopBar = ({ space, openSpace, openHousekeeper, notify }) => <header className="home-top">
  <div className="home-mark"><Icon name="home" size={19}/></div>
  <div className="home-wordmark">HOME<i>.</i></div>
  <button className="space-switch" onClick={openSpace}><Icon name="home" size={13}/><span>{space}</span><Icon name="chevronDown" size={11}/></button>
  <button className="top-icon housekeeper-open" onClick={openHousekeeper} aria-label="開啟 AI 管家" title="AI 管家"><Icon name="sparkle" size={17}/></button>
  <button className="top-icon" onClick={notify} aria-label="通知"><Icon name="bell" size={17}/><i className="notify-dot"/></button>
</header>;

const BottomNav = ({ active, onChange }) => <nav className="home-nav" data-testid="bottom-nav" aria-label="主要導航">
  {NAV.map(([id, icon, label]) => <button key={id} data-testid={`tab-${id}`} className={`nav-item ${active === id ? "on" : ""}`} onClick={() => onChange(id)} aria-current={active === id ? "page" : undefined}>
    <Icon name={icon} size={17}/><span className="nav-label">{label}</span>
  </button>)}
</nav>;

const PersonalHomeApp = ({ initialData, onLogout }) => {
  const [active, setActive] = useState("today");
  const [sheet, setSheet] = useState(null);
  const [sheetTaskId, setSheetTaskId] = useState(null);
  const [sheetLocationId, setSheetLocationId] = useState(null);
  const [sheetItemId, setSheetItemId] = useState(null);
  const [sheetRecipeId, setSheetRecipeId] = useState(null);
  const [sheetRecipe, setSheetRecipe] = useState(null);
  const [housekeeperOpen, setHousekeeperOpen] = useState(false);
  const [tutorialCompleted, setTutorialCompleted] = useState(initialData.tutorial_completed !== false);
  const [toast, setToast] = useState(null);
  const [achievement, setAchievement] = useState(null);
  const [workspace, setWorkspace] = useState(initialData.current_workspace);
  const [workspaces, setWorkspaces] = useState(initialData.workspaces || []);
  const [members, setMembers] = useState(initialData.members || []);
  const [locations, setLocations] = useState(initialData.locations || []);
  const [items, setItems] = useState(initialData.items || []);
  const [recipes, setRecipes] = useState(initialData.recipes || []);
  const [plannedRecipes, setPlannedRecipes] = useState([]);
  const [activity, setActivity] = useState(() => (initialData.activity || []).map(apiEventToUi));
  const [tasks, setTasks] = useState(() => (initialData.tasks || []).map(apiTaskToUi));
  const [spend, setSpend] = useState(initialData.ledger?.month_total || 0);
  const [ledgerEntries, setLedgerEntries] = useState(initialData.ledger?.entries || []);
  const [selectedRoom, setSelectedRoom] = useState(() => (initialData.locations || []).find((location) => location.kind === "room")?.id || null);
  const [salaryConfig, setSalaryConfig] = useState({ ...DEFAULT_SALARY, ...(initialData.income || {}) });
  const [now, setNow] = useState(() => new Date());
  const sheetRef = useRef(null);
  const syncBusyRef = useRef(false);
  const syncVersionRef = useRef(0);
  const reminderAlertsRef = useRef(new Set());
  const [currentUser, setCurrentUser] = useState(initialData.user);
  const currentUserShort = shortName(currentUser.display_name);
  const sharedMode = workspace?.type === "household";

  const applyBootstrap = (data) => {
    if (data.user) setCurrentUser(data.user);
    setWorkspace(data.current_workspace);
    setWorkspaces(data.workspaces || []);
    setMembers(data.members || []);
    const nextLocations = data.locations || [];
    setLocations(nextLocations);
    setSelectedRoom((current) => nextLocations.some((location) => location.id === current) ? current : nextLocations.find((location) => location.kind === "room")?.id || null);
    setItems(data.items || []);
    setRecipes(data.recipes || []);
    setActivity((data.activity || []).map(apiEventToUi));
    setTasks((data.tasks || []).map(apiTaskToUi));
    setSpend(data.ledger?.month_total || 0);
    setLedgerEntries(data.ledger?.entries || []);
    setSalaryConfig({ ...DEFAULT_SALARY, ...(data.income || {}) });
    if (typeof data.tutorial_completed === "boolean") setTutorialCompleted((current) => current || data.tutorial_completed);
    return data;
  };

  const reloadHome = async () => {
    const requestVersion = ++syncVersionRef.current;
    const data = await personalGet("/api/personal/bootstrap");
    if (requestVersion === syncVersionRef.current) applyBootstrap(data);
    return data;
  };
  const refreshAfterWrite = async () => {
    try {
      await reloadHome();
      return true;
    } catch (error) {
      window.setTimeout(() => reloadHome().catch(() => {}), 1200);
      return false;
    }
  };
  const planRecipes = async (draft) => {
    const response = await personalPost("/api/personal/recipes/plan", {
      workspace_id: workspace.id,
      goal: draft.goal,
      mode: draft.mode,
      servings: Number(draft.servings),
      note: String(draft.note || "").trim(),
    });
    if (!Array.isArray(response?.recipes)) throw new Error("食譜規劃回應無效，請再試一次。");
    setPlannedRecipes(response.recipes);
    return response;
  };

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => { setPlannedRecipes([]); }, [workspace?.id]);
  useEffect(() => { sheetRef.current = sheet || (housekeeperOpen ? "housekeeper" : null); }, [sheet, housekeeperOpen]);
  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      if (cancelled || document.visibilityState === "hidden" || sheetRef.current || syncBusyRef.current) return;
      syncBusyRef.current = true;
      try {
        await reloadHome();
      } catch (error) {
        if (!cancelled && error.status !== 401) flash(error.message || "家庭資料同步失敗。", "error");
      } finally {
        syncBusyRef.current = false;
      }
    };
    const visible = () => { if (document.visibilityState === "visible") sync(); };
    const timer = window.setInterval(sync, 8000);
    window.addEventListener("focus", sync);
    document.addEventListener("visibilitychange", visible);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
      window.removeEventListener("focus", sync);
      document.removeEventListener("visibilitychange", visible);
    };
  }, []);

  const flash = (message, tone = "success") => {
    setToast({ message, tone });
    window.clearTimeout(window.__homeToastTimer);
    window.__homeToastTimer = window.setTimeout(() => setToast(null), 3000);
  };
  useEffect(() => {
    for (const task of tasks) {
      if (!reminderIsDue(task.reminder, now)) {
        reminderAlertsRef.current.delete(task.id);
        continue;
      }
      if (!reminderAlertsRef.current.has(task.id)) {
        reminderAlertsRef.current.add(task.id);
        flash(`提醒：${task.title}`);
      }
    }
  }, [now, tasks]);

  const openSheet = (type, context = {}) => {
    setToast(null);
    setSheetTaskId(context.taskId || null);
    setSheetLocationId(context.locationId || null);
    setSheetItemId(context.itemId || null);
    setSheetRecipeId(context.recipeId || null);
    setSheetRecipe(type === "recipe" ? context.recipe || null : null);
    setSheet(type);
  };
  const openHousekeeper = () => {
    setSheet(null);
    setToast(null);
    setHousekeeperOpen(true);
  };
  const completeTutorial = async () => {
    await personalPost("/api/personal/tutorial/complete", {});
    setTutorialCompleted(true);
  };

  const pushActivity = (text, who = currentUserShort) => setActivity((prev) => [{ who, text, time: "NOW" }, ...prev]);

  const changeItem = async (id, delta, throwOnError = false, operation = delta > 0 ? "stock" : "consume") => {
    syncVersionRef.current += 1;
    const current = items.find((i) => i.id === id);
    if (!current || current.qty + delta < 0) return false;
    try {
      const response = await personalPost(`/api/personal/items/${id}/adjust`, { delta, operation, expected_version: current.version });
      setItems((prev) => prev.map((item) => item.id === id ? response.item : item));
      if (Array.isArray(response.recipes)) setRecipes(response.recipes);
      pushActivity(`${operation === "discard" ? "丟棄了" : delta > 0 ? "補入" : "取用"}${current.name} ${Math.abs(delta)}${current.unit}`);
      flash(operation === "discard" ? `${current.name}這一批已標記丟棄` : `${current.name} ${delta > 0 ? "+" : "−"}${Math.abs(delta)}，已同步到${sharedMode ? "小家" : "私人空間"}`);
      return true;
    } catch (requestError) {
      if (throwOnError) throw requestError;
      flash(requestError.message, "error");
      return false;
    }
  };

  const handleTaskAction = async (id, action) => {
    syncVersionRef.current += 1;
    const task = tasks.find((t) => t.id === id);
    if (!task) return;
    try {
      const response = await personalPost(`/api/personal/tasks/${id}/${action}`, { expected_version: task.version });
      const nextTask = apiTaskToUi(response.task);
      setTasks((prev) => prev.map((item) => item.id === id ? nextTask : item));
      pushActivity(`${action === "claim" ? "接手了" : "完成了"}「${task.title}」`);
      if (action === "claim") {
        flash(`你已接手「${task.title}」`);
      } else {
        setToast(null);
        setAchievement({ taskId: id, title: task.title, createdBy: task.createdBy, completedBy: currentUserShort });
        window.clearTimeout(window.__homeAchievementTimer);
        window.__homeAchievementTimer = window.setTimeout(() => setAchievement(null), 3000);
      }
    } catch (requestError) {
      if (requestError.data?.current) {
        const current = apiTaskToUi(requestError.data.current);
        setTasks((prev) => prev.map((item) => item.id === id ? current : item));
      }
      flash(requestError.message, "error");
    }
  };

  const handleSave = async (type, data) => {
    syncVersionRef.current += 1;
    try {
      if (type === "space") {
        await personalPost("/api/personal/workspaces/select", { workspace_id: data.workspace.id });
        setSheet(null);
        await refreshAfterWrite();
        flash(`已切換到 ${data.workspace.name}`);
        return { ok: true };
      }
      if (type === "avatar") {
        const response = await personalPost("/api/personal/profile/avatar", data.avatar);
        const updatedUser = response.user;
        setCurrentUser(updatedUser);
        setMembers((previous) => previous.map((member) => member.id === updatedUser.id ? { ...member, ...updatedUser } : member));
        setSheet(null);
        flash("頭像已更新，已同步到你的空間與小家");
        return response;
      }
      if (type === "household") {
        const response = await personalPost("/api/personal/households", data.household);
        setSheet(null);
        await refreshAfterWrite();
        flash(`「${response.workspace.name}」已建立，可以開始邀請家人`);
        return response;
      }
      if (type === "joinPreview") {
        return personalPost("/api/personal/invites/preview", { code: data.code });
      }
      if (type === "joinAccept") {
        const response = await personalPost("/api/personal/invites/accept", { code: data.code });
        sessionStorage.removeItem(PERSONAL_INVITE_KEY);
        setSheet(null);
        await refreshAfterWrite();
        flash(`已加入「${response.workspace?.name || "小家"}」`);
        return response;
      }
      if (type === "task") {
        const draft = data.task;
        if (!draft?.title) return;
        const response = await personalPost("/api/personal/tasks", {
          workspace_id: workspace.id,
          title: draft.title,
          note: draft.note,
          area: draft.area,
          preferred_member_id: draft.preferredMemberId === "any" ? null : Number(draft.preferredMemberId),
          due_label: draft.due,
          client_request_id: data.clientRequestId,
        });
        setTasks((prev) => [apiTaskToUi(response.task), ...prev]);
        pushActivity(`${sharedMode ? "發佈了一件家務" : "新增了一件待辦"}「${draft.title}」`);
        flash(sharedMode ? `已發佈「${draft.title}」，家人都能看到` : `「${draft.title}」已保存到私人空間`);
      } else if (type === "reminder") {
        const response = await personalPost(`/api/personal/tasks/${data.taskId}/reminder`, { label: data.reminder, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Singapore" });
        setTasks((prev) => prev.map((item) => item.id === data.taskId ? apiTaskToUi(response.task) : item));
        flash(`已延後到${data.reminder}${sharedMode ? "，任務仍可被家人接手" : ""}`);
      } else if (type === "expense") {
        const amount = Number(data.amount);
        if (!Number.isFinite(amount) || amount <= 0) throw new Error("金額必須大於 0。");
        const fallbackTitle = sharedMode ? "家庭開銷" : "私人開銷";
        const response = await personalPost("/api/personal/ledger", { workspace_id: workspace.id, title: data.title || fallbackTitle, category: data.category || "其他", amount, paid_by_id: Number(data.payer) || currentUser.id, shared: sharedMode && data.shared, client_request_id: data.clientRequestId });
        setSpend(response.month_total);
        setLedgerEntries((prev) => [response.entry, ...prev]);
        pushActivity(`記錄${data.title || fallbackTitle} ${yuan(amount)}`);
        flash(`${data.title || "開銷"} ${yuan(amount)} 已記入${sharedMode ? "家庭" : "私人"}賬本`);
      } else if (type === "item") {
        if (!data.item) throw new Error("請選擇要取用的物品。");
        await changeItem(data.item.id, -Math.min(1, data.item.qty), true);
      } else if (type === "move") {
        if (!data.item || !data.destination) throw new Error("請選擇物品和新位置。");
        const response = await personalPost(`/api/personal/items/${data.item.id}/move`, { location_id: data.destination.id, expected_version: data.item.version });
        setItems((prev) => prev.map((item) => item.id === data.item.id ? response.item : item));
        if (Array.isArray(response.recipes)) setRecipes(response.recipes);
        pushActivity(`把${data.item.name}移到${data.destination.path}`);
        flash(`${data.item.name}已移到${data.destination.path}`);
      } else if (type === "scan") {
        const response = await personalPost("/api/personal/items", { workspace_id: workspace.id, ...data.newItem });
        setItems((prev) => [response.item, ...prev]);
        if (Array.isArray(response.recipes)) setRecipes(response.recipes);
        else if (data.newItem.is_food) await refreshAfterWrite();
        pushActivity(`加入了${response.item.name} ${response.item.qty}${response.item.unit}`);
        flash(`${response.item.name}已作為${response.item.is_food ? "新食材批次" : "物品"}寫入目前空間`);
      } else if (type === "food") {
        if (!data.item) throw new Error("找不到要更新的食材批次。");
        const response = await personalPost(`/api/personal/items/${data.item.id}/food`, data.food);
        setItems((prev) => prev.map((item) => item.id === data.item.id ? response.item : item));
        if (Array.isArray(response.recipes)) setRecipes(response.recipes);
        else await refreshAfterWrite();
        pushActivity(`更新了${response.item.name}的保鮮資料`);
        flash(`${response.item.name}這一批的存放與到期時間已更新`);
      } else if (type === "location") {
        const response = await personalPost("/api/personal/locations", { workspace_id: workspace.id, ...data.location });
        setSheet(null);
        await refreshAfterWrite();
        flash(`位置「${response.location.path}」已建立`);
      } else if (type === "invite") {
        const response = await personalPost("/api/personal/invites", { household_id: workspace.id });
        return response;
      } else if (type === "salary") {
        const salary = {
          type: data.salary.type === "annual" ? "annual" : "monthly",
          amount: Math.max(0, Number(data.salary.amount) || 0),
          hoursPerDay: clamp(data.salary.hoursPerDay, .5, 24),
          daysPerWeek: Math.round(clamp(data.salary.daysPerWeek, 1, 7)),
          payday: Math.round(clamp(data.salary.payday, 1, 31)),
          startTime: /^\d{2}:\d{2}$/.test(data.salary.startTime) ? data.salary.startTime : "09:00",
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Singapore",
        };
        const response = await personalPost("/api/personal/income", salary);
        setSalaryConfig({ ...DEFAULT_SALARY, ...response.income });
        setNow(new Date());
        flash("私人收入時鐘已安全保存，只對你可見");
      }
      setSheet(null);
      return { ok: true };
    } catch (requestError) {
      flash(requestError.message, "error");
      throw requestError;
    }
  };

  const view = useMemo(() => {
    if (active === "items") return <ItemsView items={items} recipes={recipes} plannedRecipes={plannedRecipes} changeItem={changeItem} openAction={openSheet} sharedMode={sharedMode} workspaceId={workspace.id} planRecipes={planRecipes}/>;
    if (active === "places") return <PlacesView selectedRoom={selectedRoom} selectRoom={setSelectedRoom} items={items} locations={locations} openAction={openSheet}/>;
    if (active === "ledger") return <LedgerView spend={spend} entries={ledgerEntries} openAction={openSheet} sharedMode={sharedMode}/>;
    if (active === "family") return <FamilyView activity={activity} tasks={tasks} members={members} currentUser={currentUser} currentUserId={currentUser.id} currentUserShort={currentUserShort} currentWorkspace={workspace} taskAction={handleTaskAction} openAction={openSheet} celebratingTaskId={achievement?.taskId}/>;
    return <TodayView items={items} locations={locations} activity={activity} tasks={tasks} members={members} currentUserId={currentUser.id} currentUserShort={currentUserShort} currentUserName={currentUser.display_name} sharedMode={sharedMode} openAction={openSheet} openFamily={() => setActive("family")} taskAction={handleTaskAction} selectedRoom={selectedRoom} selectRoom={setSelectedRoom} salaryConfig={salaryConfig} now={now}/>;
  }, [active, activity, achievement, currentUser, items, ledgerEntries, locations, members, now, plannedRecipes, recipes, salaryConfig, selectedRoom, spend, tasks, workspace]);

  return <div className="home-app" data-testid="personal-app">
    <TopBar space={workspace.name} openSpace={() => openSheet("space")} openHousekeeper={openHousekeeper} notify={() => flash(`今天 ${tasks.filter((task) => task.status !== "completed").length} 條${sharedMode ? "家庭" : "生活"}提醒`)}/>
    <main className="home-main" data-testid="main-scroll" key={active}>{view}</main>
    <BottomNav active={active} onChange={setActive}/>
    {sheet && <ActionSheet
      key={`${sheet}-${sheetTaskId || "new"}-${sheetLocationId || "root"}-${sheetItemId || "item"}-${sheetRecipeId || sheetRecipe?.title || "recipe"}`}
      type={sheet} items={items} members={members} workspaces={workspaces} locations={locations}
      currentUser={currentUser} currentUserId={currentUser.id} currentWorkspaceId={workspace.id} selectedLocationId={sheetLocationId}
      sharedMode={sharedMode} currentSpace={workspace.name} householdTimezone={workspace.timezone} salaryConfig={salaryConfig}
      selectedTask={tasks.find((task) => task.id === sheetTaskId)} onClose={() => setSheet(null)}
      selectedItem={items.find((item) => item.id === sheetItemId)} selectedRecipe={sheetRecipe || recipes.find((recipe) => String(recipe.id) === String(sheetRecipeId))}
      onSave={handleSave} onLogout={onLogout} onNavigate={openSheet}
    />}
    {housekeeperOpen && <HousekeeperView key={workspace.id} workspace={workspace} onClose={() => setHousekeeperOpen(false)} onRefresh={reloadHome}/>}
    {!tutorialCompleted && <TutorialOverlay onComplete={completeTutorial}/>}
    <CompletionMoment achievement={achievement}/>
    {toast && <div className={`home-toast ${toast.tone === "error" ? "error" : ""}`} role={toast.tone === "error" ? "alert" : "status"}><Icon name={toast.tone === "error" ? "alert" : "checkCircle"} size={16}/><span>{toast.message}</span></div>}
  </div>;
};

const PersonalEntry = () => {
  const [phase, setPhase] = useState("checking");
  const [session, setSession] = useState(null);
  const [bootstrap, setBootstrap] = useState(null);
  const [entryError, setEntryError] = useState("");
  const [pendingInvite, setPendingInvite] = useState(() => {
    const code = new URLSearchParams(location.search).get("invite") || sessionStorage.getItem(PERSONAL_INVITE_KEY) || "";
    if (code) sessionStorage.setItem(PERSONAL_INVITE_KEY, code);
    return code;
  });

  const loadHome = async () => {
    const data = await personalGet("/api/personal/bootstrap");
    setPendingInvite(sessionStorage.getItem(PERSONAL_INVITE_KEY) || "");
    setSession(data);
    setBootstrap(data);
    setPhase("home");
    return data;
  };
  const routeSession = async (data) => {
    setSession(data);
    if (pendingInvite || !data.onboarding_completed) setPhase("onboarding");
    else await loadHome();
  };
  useEffect(() => {
    if (new URLSearchParams(location.search).has("invite")) {
      const cleanUrl = new URL(location.href);
      cleanUrl.searchParams.delete("invite");
      history.replaceState(null, "", cleanUrl.pathname + cleanUrl.search + cleanUrl.hash);
    }
    const expired = () => { setBootstrap(null); setSession(null); setEntryError("登入已失效，請重新登入。"); setPhase("auth"); };
    window.addEventListener("personal-auth-expired", expired);
    personalGet("/api/personal/auth/me")
      .then((data) => data.authenticated ? routeSession(data) : setPhase("auth"))
      .catch((error) => { setEntryError(error.message || "現在無法連線，請稍後再試。"); setPhase("auth"); });
    return () => window.removeEventListener("personal-auth-expired", expired);
  }, []);

  const logout = async () => {
    await personalPost("/api/personal/auth/logout", {});
    setBootstrap(null);
    setSession(null);
    setEntryError("");
    setPhase("auth");
  };

  if (phase === "checking") return <PersonalLoading/>;
  if (phase === "auth") return <PersonalAuth initialError={entryError} onAuthenticated={routeSession}/>;
  if (phase === "onboarding") return <PersonalOnboarding session={session} initialInvite={pendingInvite} onReady={loadHome} onLogout={logout}/>;
  return <PersonalHomeApp initialData={bootstrap} onLogout={logout}/>;
};

ReactDOM.createRoot(document.getElementById("root")).render(<PersonalEntry/>);
})();
