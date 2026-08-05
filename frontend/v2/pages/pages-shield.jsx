/* WAREHOUSE 2.1 · SHIELD 值守駕駛艙 — ADMIN 權力面,真後端
   系統體徵(/api/shield/status,5s 可見頁輪詢)+ 白名單修復(POST /api/shield/repair,
   逐字對齊 scripts/shieldctl.py ACTIONS)+ 值守記錄(status 內時間線/守護日誌/風險事件)。
   政策:允許直接調管理端點;每個動作行內確認;失敗把後端 error 原文紅字呈現;全程審計。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "SHIELD 值守": "SHIELD Watch",
  "權力面 · 全程審計": "POWER PLANE · FULLY AUDITED",
  "系統體徵 · 白名單修復 · 值守記錄 —— 管理端點直連,每個動作行內確認並寫入審計": "System vitals · whitelist repairs · watch log — direct admin endpoints, inline confirmation, fully audited",
  "刷新": "Refresh",
  "暫停輪詢": "Pause polling",
  "繼續輪詢": "Resume polling",
  "狀態拉取失敗": "Status fetch failed",
  /* 拒絕面 */
  "權限不足": "ACCESS DENIED",
  "SHIELD 值守是 ADMIN 權力面:僅平台所有者或 L11 平台超級管理員可進入,其他身分一律拒絕。": "SHIELD Watch is an ADMIN power plane: platform owners or L11 platform super-admins only — every other identity is refused.",
  "當前身分": "Current identity",
  "問秘書怎麼開通權限": "Ask Secretary about access",
  "我在 SHIELD 值守頁被擋住了,提示沒有 ADMIN 權限。幫我看看誰能授權、怎麼開通": "I'm blocked on the SHIELD page — no ADMIN access. Find out who can grant it and how",
  /* Band A */
  "系統體徵": "System vitals",
  "5 秒即時輪詢 /api/shield/status · 頁面隱藏時自動休眠": "live-polls /api/shield/status every 5s · sleeps while hidden",
  "跑一次體檢": "Run healthcheck",
  "體檢中…": "Checking…",
  "API 存活": "API alive",
  "在線": "Online", "離線": "Offline",
  "完整性": "Integrity",
  "一致": "Consistent", "告警": "Alert",
  "未關閉事件": "Open incidents",
  "待覆核 AI 風險": "Open AI risks",
  "宗": "", "條": "", "行": "",
  "待連接": "Awaiting link",
  "全部關閉": "All closed",
  "無待覆核": "None open",
  "去覆核 →": "Review →",
  "總體態勢": "Posture",
  "嚴重度": "Severity",
  "健康": "Healthy", "觀察": "Watch", "降級": "Degraded", "容量風險": "Capacity risk",
  "運行抖動": "Flapping", "事件中": "Incident", "完整性告警": "Integrity alert",
  "攻擊態勢": "Under attack", "未接入": "Offline",
  "內存佔用": "Memory used", "磁盤佔用": "Disk used",
  "請求速率": "Req rate", "5xx 錯誤率": "5xx rate", "主進程 FD": "Main FD",
  "登入失敗率": "Login fails", "SSH 失敗率": "SSH fails",
  "最新指標": "Latest metric",
  "即時遙測牆": "Live telemetry wall", "健康分": "Health score", "核心採樣": "Kernel sample",
  "樣本年齡": "Sample age", "服務運行": "Service uptime", "API 延遲": "API latency", "已開 FD": "Open FD",
  "運算": "Compute", "記憶體": "Memory", "儲存": "Storage", "網路與 API": "Network & API",
  "安全訊號": "Security signals", "服務矩陣": "Service matrix", "邏輯核心": "Logical cores",
  "CPU 使用率": "CPU usage", "CPU 負載": "CPU load", "負載 1 / 5 / 15 分": "Load 1 / 5 / 15m",
  "程序 CPU": "Process CPU", "系統已運行": "System uptime", "總容量": "Total", "可用": "Available",
  "Swap 使用": "Swap used", "程序 RSS": "Process RSS", "程序執行緒": "Process threads",
  "FD 使用": "FD usage", "根磁碟": "Root volume", "系統磁碟": "System volume", "資料磁碟": "Data volume",
  "資料磁碟狀態": "Data volume state", "資料磁碟可用": "Data volume free", "掛載位置": "Mountpoint",
  "檔案系統": "Filesystem", "已掛載": "Mounted", "未掛載": "Unmounted", "裝置不符": "Unexpected device",
  "磁碟可用": "Disk free", "磁碟增長": "Disk growth",
  "備份數": "Backups", "下載速率": "RX rate", "上傳速率": "TX rate", "累計下載": "RX total",
  "累計上傳": "TX total", "TCP 已連線": "TCP established", "TCP 監聽": "TCP listening",
  "請求速率": "Request rate", "5xx 比例": "5xx ratio", "登入失敗 / 2 分": "Login failures / 2m",
  "SSH 失敗 / 2 分": "SSH failures / 2m", "新監聽訊號": "New-listener signal", "完整性漂移": "Integrity drift",
  "無異常": "Clear", "未知": "Unknown", "過期": "Stale", "警報": "Alert", "核心": "cores",
  "採樣暖機中": "Sampler warming up", "溫度": "Temperature", "不可用": "Unavailable",
  "主機核心": "Kernel", "消防員資料": "Firefighter data", "守護防線": "Guardian", "資料結構": "Schema",
  "實時採樣資料尚未返回。": "Live telemetry has not returned yet.",
  "warehouse-api": "Warehouse API", "nginx": "Nginx gateway", "firefighter": "Firefighter",
  "guardian": "Integrity guardian", "database": "Database", "ai-engine": "AI engine",
  "online": "Online", "offline": "Offline", "stale": "Stale", "degraded": "Degraded", "alert": "Alert", "unknown": "Unknown",
  "AI 引擎": "AI engine", "已接入": "Connected",
  "消防員": "Firefighter",
  "體徵指標待接入:消防員數據庫尚未回報,或後端未返回 live_metrics。": "Vitals pending: the firefighter database has not reported yet, or the backend returned no live_metrics.",
  "健康探活結論": "Healthcheck verdict",
  "只讀動作:POST /api/shield/repair {action:\"healthcheck\"},探活含數據庫的 /api/health,不需確認。": "Read-only: POST /api/shield/repair {action:\"healthcheck\"} probes database-aware /api/health — no confirmation needed.",
  "體檢未通過": "Check failed",
  "通過": "Passed",
  "成功 · 空響應": "OK · empty response",
  "耗時": "took",
  "狀態碼": "HTTP",
  /* Band B */
  "修復動作": "Repair actions",
  "五個白名單動作 · 委派 shieldctl · 絕不裸 shell · 每一下都寫入審計": "Five whitelisted actions · delegated to shieldctl · never raw shell · every click audited",
  "高風險": "HIGH RISK", "低風險": "LOW RISK",
  "重啟 API 服務": "Restart API service",
  "重啟當前藍綠 API 容器,重啟前後各跑一次健康探活。": "Restarts the active blue/green API container, with health probes before and after.",
  "重啟期間 API 短暫斷檔,進行中的請求會中斷。": "API briefly unavailable during restart; in-flight requests are dropped.",
  "重啟消防員守護": "Restart firefighter daemon",
  "重啟受限的 warehouse-shield-agent 消防員服務。": "Restarts the restricted warehouse-shield-agent firefighter service.",
  "值守短暫空窗,不影響業務 API。": "Brief watch gap; business API unaffected.",
  "重載 Nginx 配置": "Reload Nginx config",
  "先 nginx -t 驗證配置,通過才 systemctl reload nginx。": "Runs nginx -t first; reloads only if the config test passes.",
  "平滑重載,不中斷現有連接。": "Graceful reload; existing connections stay alive.",
  "重啟 Nginx 服務": "Restart Nginx service",
  "先 nginx -t 驗證配置,通過才 systemctl restart nginx。": "Runs nginx -t first; restarts only if the config test passes.",
  "入口斷流數秒,全站短暫不可達。": "Gateway down for seconds; the whole site is briefly unreachable.",
  "清除健康失敗計數": "Clear health-fail flag",
  "刪除 shared/shield/health_fail 固定標記檔。": "Deletes the fixed shared/shield/health_fail flag file.",
  "只清標記,不動服務;守護將重新計數。": "Clears the flag only; no service touched — the guardian recounts.",
  "作用": "Action", "風險": "Risk",
  "執行": "Execute",
  "確認執行「{name}」?": "Confirm executing \"{name}\"?",
  "確認執行": "Confirm run", "取消": "Cancel",
  "執行中…": "Executing…",
  "完成": "Done",
  "已實際執行": "Applied",
  "DRY-RUN 演練": "DRY-RUN rehearsal",
  "後端未開 SHIELD_REPAIR_APPLY,本次僅演練未動系統。": "SHIELD_REPAIR_APPLY is off on the backend — rehearsal only, nothing touched.",
  "退出碼": "Exit code",
  "後端返回": "Backend result",
  /* Band C */
  "值守記錄": "Watch log",
  "消防員時間線 · 守護日誌 · AI 風險事件(取自 status 快照)": "Firefighter timeline · guardian tail · AI risk events (from the status snapshot)",
  "事件流見審計頁 →": "Full trail on Audit page →",
  "進行中事件": "Open incidents",
  "消防員最近事件": "Recent firefighter events",
  "守護日誌尾": "Guardian log tail",
  "AI 風險事件": "AI risk events",
  "暫無": "None",
  "進行中": "open",
  "暫無值守事件": "No watch events yet",
  "消防員尚未接入或暫無事件;完整操作留痕見審計頁。": "Firefighter not linked or no events yet; the full operation trail lives on the Audit page.",
  "去審計頁": "Open Audit",
  "偵測": "Detect", "觸發": "Trigger", "診斷": "Diagnose", "脈衝": "Pulse",
  "狀態轉移": "Transition", "解除": "Resolve",
  "修復計劃": "Repair plan", "修復執行": "Repair exec", "修復復檢": "Repair verify",
  "修復失敗": "Repair failed", "修復完成": "Repair resolved", "修復": "Repair", "事件": "Event",
  "未完成": "not done", "已記錄": "logged", "狀態異常": "state anomaly",
  "ADMIN 權力面:每一次修復都由後端寫入審計日誌(shield_repair),並受 SHIELD_REPAIR_APPLY 雙閘保護。": "ADMIN power plane: every repair is audit-logged by the backend (shield_repair) and double-gated by SHIELD_REPAIR_APPLY.",
});

const { useState: _s, useEffect: _e, useMemo: _mm, useCallback: _cb, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 詞表與小工具 ── */
const S = (v) => (v === null || v === undefined || v === "") ? "—" : String(v);
const fmtTs = (v) => v ? String(v).replace("T", " ").slice(0, 19) : "—";
const STATE_META = {
  healthy: ["ok", "健康"], watch: ["warn", "觀察"], degraded: ["warn", "降級"],
  "capacity-risk": ["warn", "容量風險"], "runtime-flapping": ["warn", "運行抖動"],
  incident: ["bad", "事件中"], "integrity-alert": ["bad", "完整性告警"],
  "under-attack": ["bad", "攻擊態勢"], offline: ["plain", "未接入"],
};
const StateTag = ({ st }) => {
  const meta = STATE_META[String(st || "")];
  return meta ? <T tone={meta[0]} dot>{t(meta[1])}</T> : <T tone="plain">{st || "—"}</T>;
};
const KIND_META = {
  detect: ["warn", "偵測"], trigger: ["warn", "觸發"], diagnose: ["inv", "診斷"], pulse: ["inv", "脈衝"],
  transition: ["plain", "狀態轉移"], resolve: ["ok", "解除"],
  repair_plan: ["warn", "修復計劃"], repair_execute: ["ok", "修復執行"], repair_verify: ["ok", "修復復檢"],
  repair_failed: ["bad", "修復失敗"], repair_resolved: ["ok", "修復完成"],
};
const kindMeta = (k) => KIND_META[k] || (String(k || "").indexOf("repair_") === 0 ? ["ok", "修復"] : ["plain", k || "事件"]);
const parseJ = (v) => {
  if (v && typeof v === "object") return v;
  if (typeof v !== "string") return null;
  try { return JSON.parse(v); } catch (e) { return null; }
};
const tlText = (it) => {
  const kind = String((it && it.kind) || "");
  const p = parseJ(it && it.content);
  if (p) {
    if (kind.indexOf("repair_") === 0) return (p.action || "repair") + " · " + (p.ok === false ? t("未完成") : t("已記錄")) + (p.reason ? " · " + String(p.reason).slice(0, 60) : "");
    if (kind === "detect") return String(p.state || t("狀態異常"));
    if (kind === "trigger") return String(p.type || "trigger");
    if (p.summary) return String(p.summary).slice(0, 150);
    try { return JSON.stringify(p).slice(0, 150); } catch (e) { return "—"; }
  }
  return String(it && it.content != null ? it.content : "—").slice(0, 150);
};
const GUARD_ALERT_RE = /INTEGRITY VIOLATION|HEALTH FAIL|WATCHDOG/;
const PRE = { fontFamily: "var(--f-mono)", fontSize: 10.5, lineHeight: 1.55, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 150, overflow: "auto", background: "var(--paper-2)", border: "1px solid var(--hair-soft)", padding: 10, margin: "8px 0 0" };
const SHIELD_POLL_MS = 5000;
const SHIELD_HISTORY_LIMIT = 72;
const finite = (v) => typeof v === "number" && Number.isFinite(v);
const clampPct = (v) => finite(v) ? Math.max(0, Math.min(100, v)) : 0;
const fmtNum = (v, digits = 1) => finite(v)
  ? Number(v).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: digits })
  : "—";
const fmtPct = (v, digits = 0) => finite(v) ? fmtNum(v, digits) + "%" : "—";
const fmtBytes = (v) => {
  if (!finite(v) || v < 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = v; let idx = 0;
  while (value >= 1024 && idx < units.length - 1) { value /= 1024; idx += 1; }
  return fmtNum(value, value >= 100 || idx === 0 ? 0 : 1) + " " + units[idx];
};
const fmtRate = (v) => finite(v) ? fmtBytes(v) + "/s" : "—";
const fmtDuration = (v) => {
  if (!finite(v) || v < 0) return "—";
  const seconds = Math.floor(v);
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return days + "d " + hours + "h";
  if (hours) return hours + "h " + minutes + "m";
  if (minutes) return minutes + "m";
  return seconds + "s";
};
const fmtAge = (v) => !finite(v) ? "—" : v < 1 ? "<1s" : Math.floor(v) + "s";
const toneFor = (value, warning, critical) => !finite(value) ? "unknown" : value >= critical ? "critical" : value >= warning ? "warning" : "normal";

const ShieldSparkline = ({ values, label }) => {
  const points = (values || []).filter(finite);
  if (!points.length) return <svg className="sv-sparkline" viewBox="0 0 100 42" role="img" aria-label={`${label} · ${t("採樣暖機中")}`}><line className="grid" x1="0" y1="21" x2="100" y2="21"/></svg>;
  const source = points.length === 1 ? [points[0], points[0]] : points;
  const lo = Math.min(...source); const hi = Math.max(...source); const span = Math.max(hi - lo, 1);
  const path = source.map((value, index) => {
    const x = index * 100 / Math.max(1, source.length - 1);
    const y = 37 - ((value - lo) / span) * 32;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(" ");
  const last = path.split(" ").slice(-1)[0].split(",");
  return <svg className="sv-sparkline" viewBox="0 0 100 42" preserveAspectRatio="none" role="img" aria-label={`${label} · ${fmtNum(points[points.length - 1], 1)}`}>
    <line className="grid" x1="0" y1="37" x2="100" y2="37"/>
    <polyline className="line" points={path}/>
    <circle className="point" cx={last[0]} cy={last[1]} r="1.8" vectorEffect="non-scaling-stroke"/>
  </svg>;
};

const ShieldResource = ({ index, label, value, unit, meter, tone, history, footLeft, footRight }) => (
  <article className="sv-resource" data-tone={tone || "normal"}>
    <div className="sv-resource-head"><span className="sv-cell-label">{label}</span><span className="sv-resource-index">{index}</span></div>
    <div className="sv-resource-value">{finite(value) ? fmtNum(value, value < 10 ? 2 : 1) : "—"}<small>{unit || ""}</small></div>
    <div className="sv-meter-track" aria-hidden="true"><div className="sv-meter-fill" style={{ width: clampPct(meter) + "%" }}/></div>
    <ShieldSparkline values={history} label={label}/>
    <div className="sv-resource-foot"><span>{footLeft || "—"}</span><span>{footRight || ""}</span></div>
  </article>
);

const ShieldLedger = ({ rows }) => <div className="sv-ledger">
  {(rows || []).map((row) => <div className="sv-ledger-row" key={row.label}>
    <span>{row.label}</span><strong className={row.bad ? "bad" : ""}>{row.value == null ? "—" : row.value}</strong>
  </div>)}
</div>;

const ShieldTelemetryWall = ({ vitals, history, sampleAge, stale }) => {
  if (!vitals || typeof vitals !== "object") return <div className="shield-vitals-wall"><div className="sv-source-line">{t("實時採樣資料尚未返回。")}</div></div>;
  const cpu = vitals.cpu || {}; const memory = vitals.memory || {}; const storage = vitals.storage || {};
  const storageVolumes = Array.isArray(storage.volumes) ? storage.volumes.filter((item) => item && typeof item === "object") : [];
  const rootVolume = storageVolumes.find((item) => item.id === "root") || storage;
  const dataVolume = storageVolumes.find((item) => item.id === "warehouse-data") || null;
  const dataVolumeReady = !!(dataVolume && dataVolume.mounted === true && dataVolume.available === true && dataVolume.state !== "unexpected-device");
  const dataVolumeState = !dataVolume ? t("未接入")
    : dataVolume.state === "mounted" ? t("已掛載")
    : dataVolume.state === "unexpected-device" ? t("裝置不符")
    : dataVolume.state === "unavailable" ? t("不可用") : t("未掛載");
  const network = vitals.network || {}; const process = vitals.process || {}; const thermal = vitals.thermal || {};
  const traffic = vitals.traffic || {}; const security = vitals.security || {}; const resilience = vitals.resilience || {};
  const runtime = vitals.runtime || {}; const services = Array.isArray(vitals.services) ? vitals.services : [];
  const sources = vitals.data_sources || {}; const alerts = Array.isArray(vitals.alerts) ? vitals.alerts : [];
  const score = finite(vitals.health_score) ? Math.round(vitals.health_score) : null;
  const severity = finite(vitals.severity) ? Math.round(vitals.severity) : 0;
  const stateMeta = STATE_META[String(vitals.state || "")] || ["plain", vitals.state || "未知"];
  const historyValues = (key) => (history || []).map((item) => item[key]).filter(finite);
  const fdText = finite(process.fd_open)
    ? fmtNum(process.fd_open, 0) + (finite(process.fd_limit) ? " / " + fmtNum(process.fd_limit, 0) : "")
    : "—";
  const serviceState = (state) => t(String(state || "unknown"));
  const signal = (v) => finite(v) ? (v > 0 ? t("警報") : t("無異常")) : t("未知");
  const ffSource = sources.firefighter || {};
  const guardSource = sources.guardian || {};
  const combinedNet = finite(network.rx_bytes_per_second) || finite(network.tx_bytes_per_second)
    ? (finite(network.rx_bytes_per_second) ? network.rx_bytes_per_second : 0)
      + (finite(network.tx_bytes_per_second) ? network.tx_bytes_per_second : 0)
    : null;

  return <div className="shield-vitals-wall" data-state={stale ? "stale" : String(vitals.state || "unknown")}>
    {!stale && <span className="sv-telemetry-scan" aria-hidden="true"/>}
    <header className="sv-command-head">
      <div className={`sv-score${severity >= 3 ? " is-critical" : ""}`}>
        <span className="sv-kicker">SHIELD / {t("即時遙測牆")}</span>
        <div className="sv-score-main"><strong className="sv-score-value">{score == null ? "—" : score}</strong><span className="sv-score-unit">/ 100</span></div>
        <div className="sv-score-state"><i className={`sv-live-dot${stale || severity >= 3 ? " bad" : ""}`}/><span>{stale ? t("過期") : t(stateMeta[1])}</span></div>
      </div>
      <div className={`sv-head-cell${severity >= 3 ? " is-danger" : ""}`}><span className="sv-cell-label">{t("嚴重度")}</span><strong>{severity}/5</strong><small>{alerts.length ? alerts.length + " SIGNALS" : "NO ACTIVE SIGNAL"}</small></div>
      <div className={`sv-head-cell${stale ? " is-danger" : ""}`}><span className="sv-cell-label">{t("樣本年齡")}</span><strong>{fmtAge(sampleAge)}</strong><small>{t("核心採樣")} · {vitals.poll_hint_seconds || 5}s</small></div>
      <div className="sv-head-cell"><span className="sv-cell-label">{t("服務運行")}</span><strong>{fmtDuration(process.uptime_seconds)}</strong><small>{t("系統已運行")} · {fmtDuration(runtime.uptime_seconds)}</small></div>
      <div className="sv-head-cell"><span className="sv-cell-label">{t("已開 FD")}</span><strong>{finite(process.fd_open) ? fmtNum(process.fd_open, 0) : "—"}</strong><small>{finite(process.fd_limit) ? "LIMIT " + fmtNum(process.fd_limit, 0) : t("不可用")}</small></div>
    </header>

    {(stale || alerts.length > 0) && <div className="sv-alert-strip" role="status" aria-live="polite">
      <span className="sv-cell-label">{stale ? "STALE" : "SIGNAL"}</span>
      <span>{stale ? t("最新指標") + " · " + fmtAge(sampleAge) : alerts.slice(0, 3).map((item) => `${item.label} ${fmtNum(item.value, 1)}${item.unit || ""}`).join(" · ")}</span>
    </div>}

    <section className="sv-resource-grid" aria-label={t("系統體徵")}>
      <ShieldResource index="01" label="CPU" value={cpu.usage_pct} unit="%" meter={cpu.usage_pct}
        tone={toneFor(cpu.usage_pct, 85, 96)} history={historyValues("cpu")}
        footLeft={finite(cpu.usage_pct) ? t("CPU 使用率") : t("採樣暖機中")} footRight={finite(process.cpu_pct) ? "PROC " + fmtPct(process.cpu_pct, 1) : ""}/>
      <ShieldResource index="02" label={t("記憶體")} value={memory.used_pct} unit="%" meter={memory.used_pct}
        tone={toneFor(memory.used_pct, 82, 94)} history={historyValues("memory")}
        footLeft={fmtBytes(memory.used_bytes)} footRight={fmtBytes(memory.total_bytes)}/>
      <ShieldResource index="03" label={t("系統磁碟")} value={rootVolume.used_pct} unit="%" meter={rootVolume.used_pct}
        tone={toneFor(rootVolume.used_pct, 82, 94)} history={historyValues("storage")}
        footLeft={fmtBytes(rootVolume.used_bytes)} footRight={fmtBytes(rootVolume.total_bytes)}/>
      <ShieldResource index="04" label={t("資料磁碟")} value={dataVolume && dataVolume.used_pct} unit="%" meter={dataVolume && dataVolume.used_pct}
        tone={dataVolume && !dataVolumeReady ? "critical" : toneFor(dataVolume && dataVolume.used_pct, 82, 94)} history={historyValues("dataStorage")}
        footLeft={dataVolumeReady ? fmtBytes(dataVolume.used_bytes) : dataVolumeState} footRight={dataVolumeReady ? fmtBytes(dataVolume.total_bytes) : ""}/>
      <ShieldResource index="05" label={t("CPU 負載")} value={cpu.load_1m} unit=" / 1m" meter={cpu.load_normalized_pct}
        tone={toneFor(cpu.load_normalized_pct, 100, 160)} history={historyValues("load")}
        footLeft={finite(cpu.logical_cores) ? fmtNum(cpu.logical_cores, 0) + " " + t("核心") : "—"} footRight={fmtPct(cpu.load_normalized_pct, 0)}/>
    </section>

    <section className="sv-detail-grid">
      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("運算")}</h3><span className="sv-detail-no">A / COMPUTE</span></div><ShieldLedger rows={[
        { label: t("邏輯核心"), value: finite(cpu.logical_cores) ? fmtNum(cpu.logical_cores, 0) : "—" },
        { label: t("負載 1 / 5 / 15 分"), value: [cpu.load_1m, cpu.load_5m, cpu.load_15m].map((v) => fmtNum(v, 2)).join(" / ") },
        { label: t("程序 CPU"), value: fmtPct(process.cpu_pct, 2), bad: finite(process.cpu_pct) && process.cpu_pct >= 90 },
        { label: t("系統已運行"), value: fmtDuration(runtime.uptime_seconds) },
        { label: t("溫度"), value: thermal.available ? fmtNum(thermal.temperature_c, 1) + " °C" : t("不可用"), bad: finite(thermal.temperature_c) && thermal.temperature_c >= 75 },
        { label: "OS / KERNEL", value: [runtime.platform, runtime.kernel, runtime.architecture].filter(Boolean).join(" · ") || "—" },
      ]}/></article>

      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("記憶體")}</h3><span className="sv-detail-no">B / MEMORY</span></div><ShieldLedger rows={[
        { label: t("總容量"), value: fmtBytes(memory.total_bytes) },
        { label: t("可用"), value: fmtBytes(memory.available_bytes) },
        { label: t("Swap 使用"), value: finite(memory.swap_used_pct) ? fmtPct(memory.swap_used_pct, 1) + " · " + fmtBytes(memory.swap_used_bytes) : fmtBytes(memory.swap_used_bytes), bad: finite(memory.swap_used_pct) && memory.swap_used_pct >= 55 },
        { label: t("程序 RSS"), value: fmtBytes(process.rss_bytes) },
        { label: t("程序執行緒"), value: fmtNum(process.threads, 0) },
        { label: t("FD 使用"), value: fdText },
      ]}/></article>

      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("儲存")}</h3><span className="sv-detail-no">C / STORAGE</span></div><ShieldLedger rows={[
        { label: t("系統磁碟"), value: fmtPct(rootVolume.used_pct, 1), bad: finite(rootVolume.used_pct) && rootVolume.used_pct >= 82 },
        { label: t("總容量"), value: fmtBytes(rootVolume.total_bytes) },
        { label: t("磁碟可用"), value: fmtBytes(rootVolume.free_bytes) },
        { label: t("資料磁碟狀態"), value: dataVolumeState, bad: !!(dataVolume && !dataVolumeReady) },
        { label: t("資料磁碟"), value: dataVolumeReady ? fmtPct(dataVolume.used_pct, 1) : "—", bad: finite(dataVolume && dataVolume.used_pct) && dataVolume.used_pct >= 82 },
        { label: t("資料磁碟可用"), value: dataVolumeReady ? fmtBytes(dataVolume.free_bytes) : "—" },
        { label: t("掛載位置"), value: dataVolume && dataVolume.mountpoint || "—" },
        { label: t("檔案系統"), value: dataVolume ? [dataVolume.device, dataVolume.filesystem, dataVolume.filesystem_label].filter(Boolean).join(" · ") || "—" : "—" },
        { label: t("磁碟增長"), value: finite(resilience.disk_growth_gb_per_day) ? fmtNum(resilience.disk_growth_gb_per_day, 2) + " GB/d" : "—" },
        { label: t("備份數"), value: fmtNum(resilience.backup_count, 0) },
        { label: "SWAP OBSERVED", value: finite(resilience.swap_used_mb_observed) ? fmtNum(resilience.swap_used_mb_observed, 1) + " MB" : "—" },
      ]}/></article>

      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("網路與 API")}</h3><span className="sv-detail-no">D / I·O</span></div><ShieldLedger rows={[
        { label: t("下載速率"), value: fmtRate(network.rx_bytes_per_second) },
        { label: t("上傳速率"), value: fmtRate(network.tx_bytes_per_second) },
        { label: t("累計下載") + " / " + t("累計上傳"), value: fmtBytes(network.rx_bytes) + " / " + fmtBytes(network.tx_bytes) },
        { label: t("TCP 已連線") + " / " + t("TCP 監聽"), value: fmtNum(network.established_tcp, 0) + " / " + fmtNum(network.listening_tcp, 0) },
        { label: t("請求速率"), value: finite(traffic.requests_per_second) ? fmtNum(traffic.requests_per_second, 3) + " req/s" : "—" },
        { label: t("API 延遲"), value: finite(traffic.api_health_latency_ms) ? fmtNum(traffic.api_health_latency_ms, 0) + " ms" : "—" },
      ]}/></article>

      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("安全訊號")}</h3><span className="sv-detail-no">E / SECURITY</span></div><ShieldLedger rows={[
        { label: t("5xx 比例"), value: fmtPct(traffic.errors_5xx_pct, 3), bad: finite(traffic.errors_5xx_pct) && traffic.errors_5xx_pct > 0 },
        { label: t("登入失敗 / 2 分"), value: fmtNum(security.login_failures, 0), bad: finite(security.login_failures) && security.login_failures > 0 },
        { label: t("SSH 失敗 / 2 分"), value: fmtNum(security.ssh_failures, 0), bad: finite(security.ssh_failures) && security.ssh_failures > 0 },
        { label: t("新監聽訊號"), value: signal(security.new_listener_signal), bad: finite(security.new_listener_signal) && security.new_listener_signal > 0 },
        { label: t("完整性漂移"), value: signal(security.integrity_mismatch), bad: finite(security.integrity_mismatch) && security.integrity_mismatch > 0 },
        { label: "NET I/O", value: fmtRate(combinedNet) },
      ]}/></article>

      <article className="sv-detail"><div className="sv-detail-head"><h3>{t("服務矩陣")}</h3><span className="sv-detail-no">F / SERVICES</span></div><div className="sv-service-grid">
        {services.map((item) => <div className="sv-service" data-state={String(item.state || "unknown")} key={item.id}>
          <div className="sv-service-name"><i/><span>{t(item.id)}</span></div>
          <small>{serviceState(item.state)}{finite(item.latency_ms) ? " · " + fmtNum(item.latency_ms, 0) + "ms" : ""}{item.detail ? " · " + item.detail : ""}</small>
        </div>)}
      </div></article>
    </section>

    <footer className="sv-source-line">
      <span><b>{t("主機核心")}</b> · {serviceState((sources.kernel || {}).state)}</span>
      <span className={ffSource.state === "stale" || ffSource.state === "offline" ? "stale" : ""}><b>{t("消防員資料")}</b> · {serviceState(ffSource.state)}{finite(ffSource.age_seconds) ? " · " + fmtAge(ffSource.age_seconds) : ""}</span>
      <span className={guardSource.state === "alert" ? "stale" : ""}><b>{t("守護防線")}</b> · {serviceState(guardSource.state)}</span>
      <span><b>{t("最新指標")}</b> · {fmtTs(vitals.sampled_at)}</span>
      <span><b>{t("資料結構")}</b> · V{vitals.schema_version || 1}</span>
    </footer>
  </div>;
};

/* 修復失敗:後端 error 原文(結果體 error → stderr → 頂層 error) */
const failText = (resp) => {
  const r = (resp && resp.result) || {};
  return String(r.error || (resp && resp.stderr) || (resp && resp.error) || "").trim();
};

/* ── 白名單動作卡(逐字對齊 scripts/shieldctl.py ACTIONS)── */
const REPAIRS = [
  { id: "restart-api", icon: "cpu", high: true, name: "重啟 API 服務",
    does: "重啟當前藍綠 API 容器,重啟前後各跑一次健康探活。",
    risk: "重啟期間 API 短暫斷檔,進行中的請求會中斷。" },
  { id: "restart-firefighter", icon: "flame", high: false, name: "重啟消防員守護",
    does: "重啟受限的 warehouse-shield-agent 消防員服務。",
    risk: "值守短暫空窗,不影響業務 API。" },
  { id: "reload-nginx", icon: "refresh", high: false, name: "重載 Nginx 配置",
    does: "先 nginx -t 驗證配置,通過才 systemctl reload nginx。",
    risk: "平滑重載,不中斷現有連接。" },
  { id: "restart-nginx", icon: "swap", high: true, name: "重啟 Nginx 服務",
    does: "先 nginx -t 驗證配置,通過才 systemctl restart nginx。",
    risk: "入口斷流數秒,全站短暫不可達。" },
  { id: "clear-health-flag", icon: "checkCircle", high: false, name: "清除健康失敗計數",
    does: "刪除 shared/shield/health_fail 固定標記檔。",
    risk: "只清標記,不動服務;守護將重新計數。" },
];

const RepairResult = ({ resp, err }) => {
  if (err) return (
    <div className="mono" style={{ fontSize: 11, color: "var(--red)", wordBreak: "break-word", lineHeight: 1.6 }}>✗ {err}</div>
  );
  if (!resp) return null;
  const empty = Object.keys(resp).length === 0;
  const failed = resp.ok === false;
  const meta = [
    resp.elapsed_ms != null ? t("耗時") + " " + resp.elapsed_ms + "ms" : "",
    resp.returncode != null ? t("退出碼") + " " + resp.returncode : "",
  ].filter(Boolean).join(" · ");
  if (failed) {
    const errText = failText(resp);
    return (
      <div className="col g6">
        <div className="row g8 wrap">
          <T tone="bad" dot>{t("修復失敗")}</T>
          {meta && <span className="num muted" style={{ fontSize: 10.5 }}>{meta}</span>}
        </div>
        <div className="mono" style={{ fontSize: 11, color: "var(--red)", wordBreak: "break-word", lineHeight: 1.6 }}>✗ {errText || t("體檢未通過")}</div>
        {resp.result && Object.keys(resp.result || {}).length > 0 && <pre style={PRE}>{JSON.stringify(resp.result, null, 2)}</pre>}
      </div>
    );
  }
  return (
    <div className="col g6">
      <div className="row g8 wrap">
        <T tone="inv"><I name="check" size={10}/>{t("完成")}</T>
        {empty && <T tone="plain">{t("成功 · 空響應")}</T>}
        {resp.applied === true && <T tone="ok" dot>{t("已實際執行")}</T>}
        {resp.applied === false && <T tone="warn">{t("DRY-RUN 演練")}</T>}
        {meta && <span className="num muted" style={{ fontSize: 10.5 }}>{meta}</span>}
      </div>
      {resp.applied === false && <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>{t("後端未開 SHIELD_REPAIR_APPLY,本次僅演練未動系統。")}</div>}
      {resp.result && Object.keys(resp.result || {}).length > 0 && (
        <details>
          <summary className="mono muted" style={{ fontSize: 10, letterSpacing: ".08em", cursor: "pointer" }}>{t("後端返回")}</summary>
          <pre style={PRE}>{JSON.stringify(resp.result, null, 2)}</pre>
        </details>
      )}
    </div>
  );
};

const RepairCard = ({ a, idx }) => {
  const [phase, setPhase] = _s("idle"); // idle | confirm | busy | done
  const [resp, setResp] = _s(null);
  const [err, setErr] = _s("");
  const run = () => {
    setPhase("busy"); setErr(""); setResp(null);
    W2.post("/api/shield/repair", { action: a.id, confirm: true, apply: true })
      .then((d) => { setResp(d && typeof d === "object" ? d : {}); setPhase("done"); })
      .catch((e) => { setErr(e.message || String(e)); setPhase("done"); });
  };
  return (
    <div className="panel rise" style={{ padding: 18, borderColor: a.high ? "var(--red)" : "var(--hair)", animationDelay: (idx * .05) + "s", display: "flex", flexDirection: "column", gap: 10 }}>
      <div className="row spread g10">
        <div className="row g10">
          <I name={a.icon} size={16} color={a.high ? "var(--red)" : "var(--ink)"}/>
          <span style={{ fontWeight: 750, fontSize: 14.5, letterSpacing: "-.02em" }}>{t(a.name)}</span>
        </div>
        {a.high ? <T tone="redinv">{t("高風險")}</T> : <T tone="plain">{t("低風險")}</T>}
      </div>
      <div className="mono muted" style={{ fontSize: 10, letterSpacing: ".08em" }}>{a.id}</div>
      <div style={{ fontSize: 12, lineHeight: 1.6, color: "var(--ink-2)" }}>
        <span className="label dim" style={{ fontSize: 8.5, marginRight: 6 }}>{t("作用")}</span>{t(a.does)}
      </div>
      <div style={{ fontSize: 12, lineHeight: 1.6, color: a.high ? "var(--red)" : "var(--ink-3)" }}>
        <span className="label" style={{ fontSize: 8.5, marginRight: 6, color: a.high ? "var(--red)" : "var(--ink-3)" }}>{t("風險")}</span>{t(a.risk)}
      </div>
      <div style={{ marginTop: "auto" }}>
        {phase === "confirm" ? (
          <div className="col g8" style={{ border: "1px solid var(--red)", background: "var(--red-soft)", padding: 10 }}>
            <span style={{ fontSize: 12.5, fontWeight: 700, color: "var(--red)" }}>{t("確認執行「{name}」?", { name: t(a.name) })}</span>
            <div className="row g8">
              <B size="sm" kind="red" onClick={run}>{t("確認執行")}</B>
              <B size="sm" kind="ghost" onClick={() => setPhase("idle")}>{t("取消")}</B>
            </div>
          </div>
        ) : phase === "busy" ? (
          <div className="step-line"><I name="refresh" size={10}/>{t("執行中…")}</div>
        ) : (
          <div className="col g10">
            {phase === "done" && <RepairResult resp={resp} err={err}/>}
            <B size="sm" kind={a.high ? "red" : ""} icon="arrow" onClick={() => setPhase("confirm")}>{t("執行")}</B>
          </div>
        )}
      </div>
    </div>
  );
};

/* ── 頁面 ── */
const Page = () => {
  const user = window.W2_USER || {};
  const lvl = Math.max(0, ...((user.roles || []).map((r) => Number(r.level) || 0)));
  // SHIELD 快照同時要求平台 L11 身分與 audit.read；前端不向缺權用戶探測受保護端點。
  const effectivePermissions = new Set(Array.isArray(user.permissions) ? user.permissions : []);
  const allowed = (!!window.W2_IS_OWNER || lvl >= 11)
    && effectivePermissions.has("audit.read");

  const [st, setSt] = _s(null);        // /api/shield/status 快照
  const [stErr, setStErr] = _s("");
  const [beat, setBeat] = _s(null);    // 最近一次成功輪詢
  const [attemptAt, setAttemptAt] = _s(null);
  const [responseMs, setResponseMs] = _s(null);
  const [now, setNow] = _s(() => new Date());
  const [history, setHistory] = _s([]);
  const [paused, setPaused] = _s(false);
  const [hc, setHc] = _s(null);        // 體檢響應
  const [hcErr, setHcErr] = _s("");
  const [hcBusy, setHcBusy] = _s(false);
  const [hcAt, setHcAt] = _s(null);
  const inFlight = _r(null);
  const requestSeq = _r(0);
  const alive = _r(true);

  const load = _cb(() => {
    if (inFlight.current) return inFlight.current;
    const seq = ++requestSeq.current;
    const started = (window.performance && performance.now) ? performance.now() : Date.now();
    const job = W2.json("/api/shield/status")
      .then((d) => {
        if (!alive.current || seq !== requestSeq.current) return;
        const data = d && typeof d === "object" ? d : {};
        const at = new Date();
        setSt(data); setStErr(""); setBeat(at); setAttemptAt(at);
        const elapsed = ((window.performance && performance.now) ? performance.now() : Date.now()) - started;
        setResponseMs(Math.max(0, Math.round(elapsed)));
        const v = data.system_vitals;
        if (v && typeof v === "object") {
          const sampledStorage = v.storage || {};
          const sampledVolumes = Array.isArray(sampledStorage.volumes) ? sampledStorage.volumes : [];
          const sampledRoot = sampledVolumes.find((item) => item && item.id === "root") || sampledStorage;
          const sampledData = sampledVolumes.find((item) => item && item.id === "warehouse-data") || {};
          const sample = {
            at: v.sampled_at || at.toISOString(),
            cpu: (v.cpu || {}).usage_pct,
            memory: (v.memory || {}).used_pct,
            storage: sampledRoot.used_pct,
            dataStorage: sampledData.used_pct,
            load: (v.cpu || {}).load_1m,
            network: (finite((v.network || {}).rx_bytes_per_second) ? (v.network || {}).rx_bytes_per_second : 0)
              + (finite((v.network || {}).tx_bytes_per_second) ? (v.network || {}).tx_bytes_per_second : 0),
          };
          setHistory((previous) => {
            if (previous.length && previous[previous.length - 1].at === sample.at) return previous;
            return previous.concat([sample]).slice(-SHIELD_HISTORY_LIMIT);
          });
        }
      })
      .catch((e) => {
        if (!alive.current || seq !== requestSeq.current) return;
        setSt((previous) => previous || {});
        setStErr(e.message || String(e));
        setAttemptAt(new Date());
      })
      .then(() => { if (inFlight.current === job) inFlight.current = null; });
    inFlight.current = job;
    return job;
  }, []);

  _e(() => {
    alive.current = true;
    return () => { alive.current = false; requestSeq.current += 1; };
  }, []);
  _e(() => {
    if (!allowed || paused) return undefined;
    let cancelled = false; let timer = null;
    const cycle = () => {
      timer = null;
      if (cancelled || document.visibilityState === "hidden") return;
      load().then(() => {
        if (!cancelled && document.visibilityState !== "hidden") timer = setTimeout(cycle, SHIELD_POLL_MS);
      });
    };
    const onVisibility = () => {
      if (!cancelled && document.visibilityState !== "hidden" && !timer) cycle();
    };
    cycle();
    document.addEventListener("visibilitychange", onVisibility);
    return () => { cancelled = true; if (timer) clearTimeout(timer); document.removeEventListener("visibilitychange", onVisibility); };
  }, [paused, allowed, load]);
  _e(() => {
    if (!allowed) return undefined;
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, [allowed]);

  const runHealthcheck = () => {
    if (hcBusy) return;
    setHcBusy(true); setHcErr(""); setHc(null);
    W2.post("/api/shield/repair", { action: "healthcheck" })
      .then((d) => setHc(d && typeof d === "object" ? d : {}))
      .catch((e) => setHcErr(e.message || String(e)))
      .then(() => { setHcBusy(false); setHcAt(new Date()); });
  };

  const ready = !!(st && st.ok === true);
  const disconnected = !!(st && st.ok === false);
  const incidents = (st && Array.isArray(st.open_incidents)) ? st.open_incidents : [];
  const timeline = (st && Array.isArray(st.recent_timeline)) ? st.recent_timeline : [];
  const guardian = (st && Array.isArray(st.guardian_tail)) ? st.guardian_tail : [];
  const risks = (st && Array.isArray(st.recent_ai_risk_events)) ? st.recent_ai_risk_events : [];
  const vitals = (st && st.system_vitals && typeof st.system_vitals === "object") ? st.system_vitals : null;
  const guardAlert = guardian.some((l) => GUARD_ALERT_RE.test(String(l)));
  const stateBad = ["incident", "integrity-alert", "under-attack"].indexOf(String(st && st.state)) >= 0;
  const openRisk = st && st.open_ai_risk_events != null ? num(st.open_ai_risk_events) : null;
  const sampleTime = vitals && vitals.sampled_at ? Date.parse(vitals.sampled_at) : NaN;
  const sampleAge = Number.isFinite(sampleTime) ? Math.max(0, (now.getTime() - sampleTime) / 1000) : null;
  const staleAfter = Math.max(15, Number(vitals && vitals.poll_hint_seconds || 5) * 3);
  const stale = !!(vitals && (vitals.stale || (finite(sampleAge) && sampleAge > staleAfter))) || (!!stErr && !!st);
  const countdown = paused || !beat ? null : Math.max(0, Math.ceil((SHIELD_POLL_MS - (now.getTime() - beat.getTime())) / 1000));

  const clock = (d) => d ? pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds()) : "—";
  const pending = <T tone="plain">{t("待連接")}</T>;

  /* 體檢結論分級 */
  const hcGrade = _mm(() => {
    if (hcErr) return ["bad", t("體檢未通過")];
    if (!hc) return null;
    const r = hc.result || {};
    if (hc.ok === false || r.status === "unhealthy") return ["bad", t("體檢未通過")];
    if (r.status === "healthy") return ["ok", t("健康")];
    if (Object.keys(hc).length === 0) return ["plain", t("成功 · 空響應")];
    return ["ok", t("通過")];
  }, [hc, hcErr]);

  /* ── 頂部:ADMIN 徽記 + 心跳 ── */
  const adminStrip = (
    <div className="row spread wrap g10" style={{ padding: "14px 0 0" }}>
      <span className="label" style={{ color: "var(--red)" }}>ADMIN — {t("權力面 · 全程審計")}</span>
      {allowed && <div className="row g10">
        {!paused && <span className="blink-dot" style={{ background: stErr || stale ? "var(--danger)" : "var(--ok)" }}/>}
        <span className="mono" style={{ fontSize: 10.5, letterSpacing: ".12em", color: "var(--ink-2)" }}>
          {paused ? "PAUSED" : stale ? "STALE" : "LIVE"} · {clock(beat || attemptAt)} · {countdown == null ? "—" : countdown + "s"}{responseMs != null ? " · " + responseMs + "ms" : ""}
        </span>
      </div>}
    </div>
  );

  const folio = (
    <Folio no="17" en="SHIELD" title={t("SHIELD 值守")}
      sub={t("系統體徵 · 白名單修復 · 值守記錄 —— 管理端點直連,每個動作行內確認並寫入審計")}
      right={allowed && <>
        <B icon={paused ? "arrow" : "clock"} onClick={() => setPaused((v) => !v)}>{paused ? t("繼續輪詢") : t("暫停輪詢")}</B>
        <B icon="refresh" onClick={load}>{t("刷新")}</B>
        <B kind="primary" icon="shield" disabled={hcBusy} onClick={runHealthcheck}>{hcBusy ? t("體檢中…") : t("跑一次體檢")}</B>
      </>}/>
  );

  /* ── 權限拒絕面 ── */
  if (!allowed) return (<>
    {adminStrip}
    {folio}
    <div className="rise" style={{ animationDelay: ".05s", padding: "40px 0" }}>
      <div className="panel" style={{ borderColor: "var(--red)", maxWidth: 560, margin: "0 auto", padding: "34px 34px 30px" }}>
        <LB red style={{ marginBottom: 14 }}>ACCESS DENIED</LB>
        <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: "-.035em", color: "var(--red)", marginBottom: 14 }}>{t("權限不足")}</div>
        <div style={{ fontSize: 13, lineHeight: 1.7, color: "var(--ink-2)", marginBottom: 10 }}>
          {t("SHIELD 值守是 ADMIN 權力面:僅平台所有者或 L11 平台超級管理員可進入,其他身分一律拒絕。")}
        </div>
        <div className="mono muted" style={{ fontSize: 11, marginBottom: 22 }}>
          {t("當前身分")} · {S(user.display_name || user.username)} · L{lvl}{window.W2_IS_OWNER ? " · OWNER" : ""}
        </div>
        <B icon="sparkle" onClick={() => ask(t("我在 SHIELD 值守頁被擋住了,提示沒有 ADMIN 權限。幫我看看誰能授權、怎麼開通"))}>{t("問秘書怎麼開通權限")}</B>
      </div>
    </div>
  </>);

  return (<>
    {adminStrip}
    {folio}
    {stErr && (
      <div className="mono" style={{ fontSize: 11, color: "var(--red)", padding: "10px 0 0", wordBreak: "break-word" }}>
        ✗ {t("狀態拉取失敗")}:{stErr}
      </div>
    )}

    {/* ═══ Band A · 系統體徵 ═══ */}
    <div className="kpi-band" style={{ marginTop: 8 }}>
      <Kpi label={t("API 存活")} value={stErr || disconnected ? t("離線") : ready ? t("在線") : "—"} red={!!stErr || disconnected} delay={0}
        foot={ready ? <StateTag st={st.state}/> : stErr || disconnected ? <T tone="bad" dot>{t("離線")}</T> : pending}/>
      <Kpi label={t("完整性")}
        value={guardian.length ? (guardAlert ? t("告警") : t("一致")) : "—"}
        red={guardAlert} delay={.05}
        foot={guardian.length
          ? <span className="muted num" style={{ fontSize: 11.5 }}>{t("守護日誌尾")} · {guardian.length} {t("行")}</span>
          : pending}/>
      <Kpi label={t("未關閉事件")} value={st === null ? "—" : ready || st.open_incidents ? incidents.length : "—"} unit={t("宗")}
        red={incidents.length > 0 || stateBad} delay={.1}
        foot={incidents.length
          ? <span className="muted" style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{S(incidents[0].title || incidents[0].signature)}</span>
          : ready ? <T tone="ok" dot>{t("全部關閉")}</T> : pending}/>
      <Kpi label={t("待覆核 AI 風險")} value={openRisk == null ? "—" : openRisk} unit={t("條")} red={!!openRisk} delay={.15}
        foot={openRisk
          ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => { location.hash = "#/logs"; }}>{t("去覆核 →")}</button>
          : openRisk === 0 ? <T tone="ok" dot>{t("無待覆核")}</T> : pending}/>
    </div>

    <Band no="A" title={t("系統體徵")} sub={t("5 秒即時輪詢 /api/shield/status · 頁面隱藏時自動休眠")} delay={.1}
      right={<div className="row g10 wrap">
        {ready && <span className="mono muted" style={{ fontSize: 10.5 }}>{t("嚴重度")} {num(st.severity)}/5</span>}
        {ready && <StateTag st={st.state}/>}
      </div>}>
      <ShieldTelemetryWall vitals={vitals} history={history} sampleAge={sampleAge} stale={stale}/>

      {/* 體檢結論 */}
      <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--hair)" }}>
        <div className="row spread wrap g10" style={{ marginBottom: 8 }}>
          <div className="row g10">
            <LB dim>{t("健康探活結論")}</LB>
            {hcAt && <span className="mono muted" style={{ fontSize: 10 }}>{clock(hcAt)}</span>}
          </div>
          <B size="sm" icon="shield" disabled={hcBusy} onClick={runHealthcheck}>{hcBusy ? t("體檢中…") : t("跑一次體檢")}</B>
        </div>
        {hcBusy && <div className="step-line"><I name="refresh" size={10}/>{t("體檢中…")}</div>}
        {!hcBusy && hcGrade && (
          <div className="col g6">
            <div className="row g8 wrap">
              <T tone={hcGrade[0]} dot={hcGrade[0] !== "plain"}>{hcGrade[1]}</T>
              {hc && hc.elapsed_ms != null && <span className="num muted" style={{ fontSize: 10.5 }}>{t("耗時")} {hc.elapsed_ms}ms</span>}
              {hc && hc.result && hc.result.http_status != null && <span className="num muted" style={{ fontSize: 10.5 }}>{t("狀態碼")} {hc.result.http_status}</span>}
            </div>
            {(hcErr || (hc && (hc.ok === false || (hc.result || {}).status === "unhealthy"))) && (
              <div className="mono" style={{ fontSize: 11, color: "var(--red)", wordBreak: "break-word", lineHeight: 1.6 }}>
                ✗ {hcErr || failText(hc) || t("體檢未通過")}
              </div>
            )}
          </div>
        )}
        {!hcBusy && !hcGrade && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{t("只讀動作:POST /api/shield/repair {action:\"healthcheck\"},探活含數據庫的 /api/health,不需確認。")}</div>}
      </div>
    </Band>

    {/* ═══ Band B · 修復動作 ═══ */}
    <Band no="B" title={t("修復動作")} sub={t("五個白名單動作 · 委派 shieldctl · 絕不裸 shell · 每一下都寫入審計")} delay={.15}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 14 }}>
        {REPAIRS.map((a, i) => <RepairCard key={a.id} a={a} idx={i}/>)}
      </div>
      <div className="muted" style={{ fontSize: 10.5, marginTop: 14, lineHeight: 1.6 }}>
        {t("ADMIN 權力面:每一次修復都由後端寫入審計日誌(shield_repair),並受 SHIELD_REPAIR_APPLY 雙閘保護。")}
      </div>
    </Band>

    {/* ═══ Band C · 值守記錄 ═══ */}
    <Band no="C" title={t("值守記錄")} sub={t("消防員時間線 · 守護日誌 · AI 風險事件(取自 status 快照)")} delay={.2}
      right={<B size="sm" kind="ghost" icon="clipboard" onClick={() => { location.hash = "#/logs"; }}>{t("事件流見審計頁 →")}</B>}>
      {(incidents.length || timeline.length || guardian.length || risks.length) ? (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "24px 48px" }}>
          <div className="col" style={{ minWidth: 0 }}>
            {!!incidents.length && (<>
              <LB red style={{ fontSize: 8.5, marginBottom: 6 }}>{t("進行中事件")}</LB>
              <div style={{ borderTop: "2px solid var(--rule)", marginBottom: 16 }}>
                {incidents.map((inc, i) => (
                  <div key={inc.id != null ? inc.id : "i" + i} className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <span className="mono" style={{ fontSize: 11, fontWeight: 700, flexShrink: 0 }}>INC-{S(inc.id)}</span>
                    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                      <span style={{ fontWeight: 650, fontSize: 12.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{S(inc.title || inc.signature)}</span>
                      <span className="num muted" style={{ fontSize: 10.5 }}>{fmtTs(inc.opened_at)} · {t("嚴重度")} {num(inc.severity)}</span>
                    </div>
                    <StateTag st={inc.state}/>
                  </div>
                ))}
              </div>
            </>)}
            <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{t("消防員最近事件")}</LB>
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {timeline.length ? timeline.map((it, i) => {
                const meta = kindMeta(String(it.kind || ""));
                return (
                  <div key={"t" + i} className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <span className="num muted" style={{ width: 128, fontSize: 11, flexShrink: 0 }}>{fmtTs(it.ts)}</span>
                    <T tone={meta[0]}>{t(meta[1])}</T>
                    <span className="muted" style={{ flex: 1, minWidth: 0, fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{tlText(it)}</span>
                  </div>
                );
              }) : <div className="muted" style={{ fontSize: 12, padding: "12px 0" }}>{t("暫無")}</div>}
            </div>
          </div>
          <div className="col" style={{ minWidth: 0 }}>
            <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{t("守護日誌尾")}</LB>
            <div style={{ borderTop: "2px solid var(--rule)", padding: "10px 0 16px" }}>
              {guardian.length ? guardian.slice(-8).map((line, i) => (
                <div key={"g" + i} className="mono" style={{ fontSize: 10.5, lineHeight: 1.7, wordBreak: "break-word", color: GUARD_ALERT_RE.test(String(line)) ? "var(--red)" : "var(--ink-3)" }}>{String(line)}</div>
              )) : <div className="muted" style={{ fontSize: 12 }}>{t("暫無")}</div>}
            </div>
            <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{t("AI 風險事件")}</LB>
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {risks.length ? risks.map((r, i) => (
                <div key={r.id != null ? r.id : "r" + i} className="ledger-row">
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                    <span className="mono" style={{ fontSize: 11.5, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{S(r.command)}</span>
                    <span className="num muted" style={{ fontSize: 10.5 }}>{fmtTs(r.created_at)} · {S(r.actor_name)}</span>
                  </div>
                  {String(r.status || "") === "open" ? <T tone="warn" dot>{t("進行中")}</T> : <T tone="plain">{S(r.status)}</T>}
                </div>
              )) : <div className="muted" style={{ fontSize: 12, padding: "12px 0" }}>{t("暫無")}</div>}
            </div>
          </div>
        </div>
      ) : (
        <EM icon="shield" title={t("暫無值守事件")} sub={t("消防員尚未接入或暫無事件;完整操作留痕見審計頁。")}
          action={<B size="sm" icon="clipboard" onClick={() => { location.hash = "#/logs"; }}>{t("去審計頁")}</B>}/>
      )}
    </Band>
  </>);
};

window.W2.PAGES["shield"] = Page;
})();
