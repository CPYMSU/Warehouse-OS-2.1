/* WAREHOUSE 2.0 · AI 批量自治盤庫
   現場只連續採集,AI 在草稿區批量整理,負責人最後一次整單入賬。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "AI 批量自治盤庫": "AI autonomous stocktake",
  "連續採集,不逐筆確認 · AI 整理全部草稿 · 最後整單入賬": "Capture continuously · AI prepares the entire draft · commit once at the end",
  "連續採集": "Continuous capture",
  "草稿復核": "Draft review",
  "盤庫草稿": "Stocktake draft",
  "AI 整理全部草稿": "AI organize entire draft",
  "整單確認入賬": "Confirm & post entire stocktake",
  "等待負責人整單確認": "Waiting for supervisor confirmation",
  "庫位拓撲": "Location topology",
  "分類拓撲": "Category topology",
  "掃條碼、輸入編碼或名稱後按回車": "Scan a barcode, enter a code or name, then press Enter",
  "直接數量": "Direct quantity",
  "箱／包數": "Packages",
  "每箱／包": "Units per package",
  "散裝數": "Loose units",
  "本次合計": "Capture total",
  "開始掃碼": "Open scanner",
  "停止錄音": "Stop listening",
  "語音錄入": "Voice capture",
  "已加入草稿,可繼續下一種": "Added to draft — continue with the next item",
  "精確匹配": "Exact",
  "AI 匹配": "AI matched",
  "異常": "Exceptions",
  "總件數": "Total units",
  "品種／草稿行": "SKUs / draft lines",
  "沒有需要顯示的草稿行": "No draft lines to display",
  "批量整理中": "Organizing draft",
  "正式庫存只會在最後一次整單確認後改變。": "Inventory changes only after the final whole-draft confirmation.",
});

const {
  useState, useEffect, useMemo, useRef, useCallback,
} = React;
const { Btn: B, Tag: T, Folio, Band, Empty: EM, Icon: I, pad2 } = W2;
const n = value => Number.isFinite(Number(value)) ? Number(value) : 0;
const text = value => value == null ? "" : String(value);
const present = value => value != null && value !== "";
const firstArray = (...values) => values.find(Array.isArray) || [];
const nested = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
const apiData = data => {
  const result = nested(data && data.result);
  return { ...(nested(data)), ...result };
};
const uuid = prefix => {
  try { return (prefix || "st") + "-" + crypto.randomUUID(); }
  catch (e) { return (prefix || "st") + "-" + Date.now() + "-" + Math.random().toString(36).slice(2); }
};
const valueForApi = value => /^\d+$/.test(String(value || "")) ? Number(value) : (value || null);
const looksLikeBarcode = value => /^[0-9A-Z][0-9A-Z._\/-]{4,}$/i.test(String(value || "").trim());
const activeCaptureTenant = () => text((W2.tenant && W2.tenant()) || "unknown");
const captureActorKey = boot => {
  const actor = nested(window.W2_USER || (boot
    && (boot.user || boot.USER || boot.me || boot.AUTH_USER || nested(boot.auth).user)));
  return text(actor.gid ?? actor.global_user_id ?? actor.username ?? actor.id ?? "anonymous").toLowerCase();
};
const stocktakeDeviceForTenant = (tenantSlug, actorKey) => {
  const key = "w2.stocktake." + tenantSlug + "." + encodeURIComponent(actorKey) + ".device";
  try {
    const existing = localStorage.getItem(key);
    if (existing) return existing;
    const created = uuid("device");
    localStorage.setItem(key, created);
    return localStorage.getItem(key) === created ? created : "";
  } catch (e) { return ""; }
};
// One browser owns one recoverable device identity. Web Locks serialize queue
// writes when the same browser opens more than one tab.
const captureStoreKey = (tenantSlug, deviceId, suffix) => "w2.stocktake." + tenantSlug + "." + deviceId + "." + suffix;
const withCaptureLock = (tenantSlug, deviceId, callback) => {
  if (navigator.locks && navigator.locks.request) {
    return navigator.locks.request(captureStoreKey(tenantSlug, deviceId, "queue-lock"), callback);
  }
  return Promise.reject(new Error("此瀏覽器缺少安全離線佇列鎖，請升級 Safari／Chrome 後再開始盤點"));
};
const captureLockSupported = () => !!(navigator.locks && navigator.locks.request);
const storedCaptureList = (tenantSlug, deviceId, suffix) => {
  try {
    const value = JSON.parse(localStorage.getItem(captureStoreKey(tenantSlug, deviceId, suffix)) || "[]");
    return Array.isArray(value) ? value.filter(item => item && item.task_id && item.event
      && String(item.tenant_slug || tenantSlug) === String(tenantSlug))
      .map(item => ({ ...item, tenant_slug: item.tenant_slug || tenantSlug })) : [];
  } catch (e) { return []; }
};
const saveCaptureList = (tenantSlug, deviceId, suffix, value) => {
  try { localStorage.setItem(captureStoreKey(tenantSlug, deviceId, suffix), JSON.stringify(value)); return true; }
  catch (e) { return false; }
};
const sequenceStoreKey = (tenantSlug, deviceId, taskId) => captureStoreKey(tenantSlug, deviceId, "sequence." + text(taskId));
const storedDeviceSequence = (tenantSlug, deviceId, taskId) => {
  try { return Math.max(0, n(localStorage.getItem(sequenceStoreKey(tenantSlug, deviceId, taskId)))); }
  catch (e) { return 0; }
};
const saveDeviceSequence = (tenantSlug, deviceId, taskId, sequence) => {
  try { localStorage.setItem(sequenceStoreKey(tenantSlug, deviceId, taskId), String(sequence)); return true; }
  catch (e) { return false; }
};

const stocktakeRecordId = (...values) => {
  for (const value of values) {
    const raw = text(value).trim();
    if (/^[1-9]\d*$/.test(raw)) {
      const parsed = Number(raw);
      if (Number.isSafeInteger(parsed)) return parsed;
    }
  }
  return "";
};
const normalizeTask = (task, index) => {
  task = nested(task);
  const id = stocktakeRecordId(task.id, task.task_id);
  const taskNo = task.task_no || task.no || (!id ? task.id : id);
  const total = n(task.total_count ?? task.total ?? task.planned ?? task.line_count);
  const done = n(task.done_count ?? task.done ?? task.counted);
  const rawStatus = text(task.status);
  const status = /completed|closed|done|已完成/i.test(rawStatus) ? "done"
    : /active|progress|open|doing|capture|counting|ready|review|draft|進行|进行/i.test(rawStatus) ? "active" : "pending";
  return {
    ...task,
    id,
    key: text(id || "task") + ":" + index,
    task_no: taskNo,
    name: task.task_name || task.name || task.scope || task.area || task.task_no || "盤點任務",
    area: task.area || task.scope || "全庫",
    owner: task.owner || task.owner_name || "—",
    raw_status: rawStatus,
    status,
    total,
    done,
    progress: present(task.progress) ? Math.max(0, Math.min(100, n(task.progress))) : (total ? Math.round(done / total * 100) : 0),
  };
};

const normalizeLine = (line, index) => {
  line = nested(line);
  const id = line.id ?? line.line_id ?? line.draft_line_id ?? index;
  const counted = n(line.counted_quantity ?? line.quantity ?? line.real_quantity ?? line.actual_quantity);
  const book = n(line.book_quantity_snapshot ?? line.book_quantity ?? line.book);
  const method = text(line.match_method || line.match_type || line.source).toLowerCase();
  const status = text(line.status || (line.item_id ? "matched" : "unresolved")).toLowerCase();
  const confidence = present(line.confidence) ? n(line.confidence) : null;
  const exception = !!line.exception || /unresolved|exception|conflict|duplicate|review|recount|error|待確認|待确认/i.test(status)
    || (confidence != null && confidence < .65);
  return {
    ...line,
    id,
    key: text(id) + ":" + text(line.line_key || index),
    version: n(line.version),
    item_name: line.item_name || line.name || line.raw_name || "待識別物資",
    spec_model: line.spec_model || line.spec || line.model || "",
    barcode: line.barcode || line.item_barcode || "",
    category_id: line.category_id ?? "",
    category_name: line.category_name || line.category || "未分類",
    warehouse_id: line.warehouse_id ?? "",
    warehouse_name: line.warehouse_name || line.warehouse || "未指定倉庫",
    location_id: line.location_id ?? "",
    location_code: line.location_code || line.location || "未指定庫位",
    counted_quantity: counted,
    book_quantity_snapshot: book,
    diff_quantity: present(line.diff_quantity) ? n(line.diff_quantity) : counted - book,
    unit: line.unit || "件",
    match_method: method,
    status,
    confidence,
    exception,
    observation_count: n(line.observation_count || 1),
  };
};

const normalizeDiff = (diff, index) => {
  diff = nested(diff);
  const book = n(diff.book ?? diff.book_quantity);
  const actual = n(diff.real ?? diff.real_quantity);
  return {
    key: text(diff.id || diff.item || index),
    item: diff.item || diff.item_name || "—",
    book,
    actual,
    diff: present(diff.diff ?? diff.diff_quantity) ? n(diff.diff ?? diff.diff_quantity) : actual - book,
    status: diff.status || "待處理",
  };
};

const actorCanAdjust = (boot, isOwner) => {
  const actor = nested(boot && (boot.user || boot.USER || boot.me || boot.AUTH_USER || nested(boot.auth).user));
  const roles = Array.isArray(actor.roles) ? actor.roles : [];
  const level = Math.max(n(actor.role_level), n(actor.topology_level), ...roles.map(role => n(role && role.level)));
  if (isOwner || actor.is_platform_owner || level >= 10) return true;
  const authoritative = Array.isArray(actor.permissions);
  if (!authoritative) return null;
  return actor.permissions.includes("inventory.adjust");
};

const actorCanCount = (boot, isOwner) => {
  const actor = nested(boot && (boot.user || boot.USER || boot.me || boot.AUTH_USER || nested(boot.auth).user));
  const roles = Array.isArray(actor.roles) ? actor.roles : [];
  const level = Math.max(n(actor.role_level), n(actor.topology_level), ...roles.map(role => n(role && role.level)));
  if (isOwner || actor.is_platform_owner || level >= 10) return true;
  if (!Array.isArray(actor.permissions)) return null;
  return actor.permissions.includes("inventory.read") || actor.permissions.includes("inventory.adjust");
};

const authMeCanAdjust = (raw, isOwner) => {
  const data = apiData(raw);
  const actor = nested(data.user || nested(data.result).user);
  const roles = Array.isArray(actor.roles) ? actor.roles : [];
  const level = Math.max(n(actor.role_level), n(actor.topology_level), ...roles.map(role => n(role && role.level)));
  if (isOwner || data.is_platform_owner || actor.is_platform_owner || level >= 10) return true;
  return Array.isArray(actor.permissions) && actor.permissions.includes("inventory.adjust");
};

const authMeCanCount = (raw, isOwner) => {
  const data = apiData(raw);
  const actor = nested(data.user || nested(data.result).user);
  const roles = Array.isArray(actor.roles) ? actor.roles : [];
  const level = Math.max(n(actor.role_level), n(actor.topology_level), ...roles.map(role => n(role && role.level)));
  if (isOwner || data.is_platform_owner || actor.is_platform_owner || level >= 10) return true;
  return Array.isArray(actor.permissions)
    && (actor.permissions.includes("inventory.read") || actor.permissions.includes("inventory.adjust"));
};

const successFeedback = () => {
  try { navigator.vibrate && navigator.vibrate(45); } catch (e) {}
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const context = new AudioCtx();
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.type = "sine";
    oscillator.frequency.setValueAtTime(740, context.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(1040, context.currentTime + .09);
    gain.gain.setValueAtTime(.0001, context.currentTime);
    gain.gain.exponentialRampToValueAtTime(.05, context.currentTime + .015);
    gain.gain.exponentialRampToValueAtTime(.0001, context.currentTime + .13);
    oscillator.connect(gain); gain.connect(context.destination);
    oscillator.start(); oscillator.stop(context.currentTime + .14);
    oscillator.onended = () => context.close().catch(() => {});
  } catch (e) {}
};

const CameraScanner = ({ onDetect, onClose }) => {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const stoppedRef = useRef(false);
  const detectBusyRef = useRef(false);
  const codePresenceRef = useRef(new Map());
  const [error, setError] = useState("");
  const [starting, setStarting] = useState(true);
  const [engine, setEngine] = useState("");
  const [lastCode, setLastCode] = useState("");
  const [acceptedCount, setAcceptedCount] = useState(0);
  const [scanState, setScanState] = useState("ready");

  useEffect(() => {
    let timer = null;
    let statusTimer = null;
    let detector = null;
    let zxingControls = null;
    stoppedRef.current = false;
    detectBusyRef.current = false;
    codePresenceRef.current = new Map();
    const stop = () => {
      stoppedRef.current = true;
      if (timer) clearTimeout(timer);
      if (statusTimer) clearTimeout(statusTimer);
      if (zxingControls && zxingControls.stop) {
        try { zxingControls.stop(); } catch (e) {}
      }
      if (streamRef.current) streamRef.current.getTracks().forEach(track => track.stop());
      streamRef.current = null;
    };
    const acceptObservedCodes = async rawCodes => {
      if (stoppedRef.current || detectBusyRef.current) return;
      const codes = [...new Set((rawCodes || []).map(value => String(value || "").trim()).filter(Boolean))];
      if (!codes.length) return;
      const observedAt = Date.now();
      const eligible = [];
      codes.forEach(code => {
        const previous = codePresenceRef.current.get(code);
        // Each code owns its own visibility window.  This prevents an A/B/A/B
        // decoder callback pattern from repeatedly counting both labels.
        if (!previous || observedAt - previous.lastSeen >= 1800) eligible.push(code);
        codePresenceRef.current.set(code, {
          accepted: !!(previous && previous.accepted),
          lastSeen: observedAt,
        });
      });
      if (!eligible.length) return;
      detectBusyRef.current = true;
      try {
        for (const code of eligible) {
          if (stoppedRef.current) return;
          setScanState("queueing");
          let queued = false;
          try { queued = await Promise.resolve(onDetect(code)); }
          catch (e) { queued = false; }
          if (stoppedRef.current) return;
          const presence = codePresenceRef.current.get(code) || { accepted: false, lastSeen: observedAt };
          codePresenceRef.current.set(code, {
            accepted: presence.accepted || queued === true,
            lastSeen: Date.now(),
          });
          if (queued === true) {
            setLastCode(code);
            setAcceptedCount(count => count + 1);
            setScanState("accepted");
          } else {
            setScanState("retry");
          }
          // Let React publish the reset quantity/input state before a second
          // distinct barcode from the same frame enters the shared path.
          if (eligible.length > 1) await new Promise(resolve => setTimeout(resolve, 0));
        }
      } finally {
        const finishedAt = Date.now();
        codes.forEach(code => {
          const presence = codePresenceRef.current.get(code);
          if (presence) codePresenceRef.current.set(code, { ...presence, lastSeen: finishedAt });
        });
        detectBusyRef.current = false;
        if (!stoppedRef.current) {
          if (statusTimer) clearTimeout(statusTimer);
          statusTimer = setTimeout(() => { if (!stoppedRef.current) setScanState("ready"); }, 850);
        }
      }
    };
    const start = async () => {
      const hasNativeDetector = "BarcodeDetector" in window;
      const hasZxingFallback = !!(window.ZXingBrowser && window.ZXingBrowser.BrowserMultiFormatReader);
      if (!("BarcodeDetector" in window)) {
        if (!hasZxingFallback) {
          setStarting(false);
          setError("Safari 相容解碼器未載入。請刷新頁面重試，或使用下方文字框輸入／貼上條碼。");
          return;
        }
      }
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        setStarting(false);
        setError("此瀏覽器無法開啟相機,請改用手動條碼輸入。");
        return;
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        if (stoppedRef.current) { stream.getTracks().forEach(track => track.stop()); return; }
        streamRef.current = stream;
        const video = videoRef.current;
        video.srcObject = stream;
        await video.play();
        setStarting(false);
        if (hasNativeDetector) {
          detector = new window.BarcodeDetector();
          setEngine("原生解碼");
          const detect = async () => {
            if (stoppedRef.current || !videoRef.current) return;
            try {
              const found = await detector.detect(videoRef.current);
              const candidates = (Array.isArray(found) ? found : []).filter(result => result && result.rawValue);
              const video = videoRef.current;
              const frameWidth = n(video && (video.videoWidth || video.clientWidth));
              const frameHeight = n(video && (video.videoHeight || video.clientHeight));
              const frameCenter = { x: frameWidth / 2, y: frameHeight / 2 };
              const centerDistance = result => {
                const box = result && result.boundingBox;
                if (!frameWidth || !frameHeight || !box
                    || !Number.isFinite(Number(box.x)) || !Number.isFinite(Number(box.y))) {
                  return Number.MAX_SAFE_INTEGER;
                }
                const x = Number(box.x) + n(box.width) / 2;
                const y = Number(box.y) + n(box.height) / 2;
                return Math.pow(x - frameCenter.x, 2) + Math.pow(y - frameCenter.y, 2);
              };
              // Dense shelves can expose several neighbouring labels at once.
              // Count only the label closest to the reticle; the operator moves
              // the reticle to the next SKU instead of silently accepting all.
              const selected = candidates.reduce((best, result) => (
                !best || centerDistance(result) < centerDistance(best) ? result : best
              ), null);
              if (selected) await acceptObservedCodes([selected.rawValue]);
            } catch (e) {}
            if (!stoppedRef.current) timer = setTimeout(detect, 220);
          };
          detect();
        } else {
          setEngine("Safari 相容解碼");
          const reader = new window.ZXingBrowser.BrowserMultiFormatReader(undefined, {
            delayBetweenScanAttempts: 220,
            delayBetweenScanSuccess: 220,
          });
          const controls = await reader.decodeFromStream(stream, video, result => {
            if (stoppedRef.current) return;
            if (!result) return;
            const code = typeof result.getText === "function" ? result.getText() : result.text;
            if (code) acceptObservedCodes([code]);
          });
          if (stoppedRef.current) {
            if (controls && controls.stop) controls.stop();
          } else {
            zxingControls = controls;
          }
        }
      } catch (e) {
        stop();
        setStarting(false);
        const denied = e && (e.name === "NotAllowedError" || e.name === "PermissionDeniedError");
        setError(denied
          ? "相機權限被拒絕。請在 Safari／瀏覽器網站設定中允許相機,或改用手動輸入。"
          : "相機啟動失敗,請關閉其他正在使用相機的程式後重試,或改用手動輸入。");
      }
    };
    start();
    return stop;
  }, []);

  return (
    <div className="stx-camera" role="dialog" aria-label="條碼掃描器">
      <div className="stx-camera-head">
        <span className="stx-kicker">LIVE BARCODE</span>
        <button type="button" className="stx-icon-button" onClick={onClose} aria-label="關閉掃碼">×</button>
      </div>
      {!error && <div className="stx-video-wrap">
        <video ref={videoRef} muted playsInline/>
        <span className="stx-scan-line"/>
      </div>}
      {starting && <div className="stx-camera-note">正在啟動後置相機…</div>}
      {error && <div className="stx-action-error"><I name="alert" size={18}/><span>{error}</span></div>}
      {!error && <div className={"stx-camera-status " + scanState} aria-live="polite">
        <span>{scanState === "queueing" ? "正在安全入隊…" : scanState === "accepted" ? "已加入草稿，請掃下一種" : scanState === "retry" ? "這筆未入隊，請查看提示後重掃" : "鏡頭持續開啟，可連續掃描"}</span>
        <b>{acceptedCount} 筆</b>
      </div>}
      <div className="stx-camera-note">{engine ? engine + " · " : ""}將條碼保持在框內；識別成功後鏡頭不會關閉，也不會彈出逐筆確認。{lastCode ? " 最近：" + lastCode : ""}</div>
    </div>
  );
};

const DraftRow = ({ line, index, categories, warehouses, locations, canCount, canReview, saving,
  onSave, onMerge, onExclude }) => {
  const rowLocations = locations.filter(location => !line.warehouse_id
    || String(location.warehouse_id) === String(line.warehouse_id));
  const saveText = (field, original, value) => {
    const clean = String(value == null ? "" : value).trim();
    if (clean !== String(original == null ? "" : original)) onSave(line, { [field]: clean });
  };
  const saveNumber = target => {
    const raw = String(target.value == null ? "" : target.value).trim();
    const parsed = Number(raw);
    if (raw === "" || !Number.isFinite(parsed) || parsed < 0) {
      target.value = String(line.counted_quantity);
      return;
    }
    const next = parsed;
    if (next !== line.counted_quantity) onSave(line, { counted_quantity: next });
  };
  const setLocation = value => {
    const location = locations.find(item => String(item.id ?? item.location_id) === String(value));
    onSave(line, {
      location_id: valueForApi(value),
      warehouse_id: location ? valueForApi(location.warehouse_id) : valueForApi(line.warehouse_id),
    });
  };
  const tone = line.exception ? "bad" : /ai/.test(line.match_method) ? "warn" : "ok";
  const method = line.exception ? "待整理" : /ai/.test(line.match_method) ? "AI" : /exact|barcode|sku|item/.test(line.match_method) ? "精確" : "已匹配";
  return (
    <tr className={line.exception ? "stx-row-exception" : ""}>
      <td><span className="lr-idx">{pad2(index + 1)}</span></td>
      <td>
        <input className="stx-cell-input stx-name" defaultValue={line.item_name}
          key={line.id + ":name:" + line.version} disabled={!canReview || saving}
          onBlur={event => saveText("item_name", line.item_name, event.target.value)}/>
        {line.barcode && <div className="mono stx-sub">{line.barcode}</div>}
      </td>
      <td><input className="stx-cell-input" defaultValue={line.spec_model}
        key={line.id + ":spec:" + line.version} disabled={!canReview || saving}
        placeholder="規格／型號" onBlur={event => saveText("spec_model", line.spec_model, event.target.value)}/></td>
      <td>
        <select className="stx-cell-select" value={String(line.category_id || "")} disabled={!canReview || saving}
          onChange={event => onSave(line, { category_id: valueForApi(event.target.value) })}>
          <option value="">未分類</option>
          {categories.map(category => <option key={category.id ?? category.category_id}
            value={category.id ?? category.category_id}>{category.name || category.category_name}</option>)}
        </select>
      </td>
      <td>
        <select className="stx-cell-select" value={String(line.location_id || "")} disabled={!canCount || saving}
          onChange={event => setLocation(event.target.value)}>
          <option value="">未指定庫位</option>
          {rowLocations.map(location => <option key={location.id ?? location.location_id}
            value={location.id ?? location.location_id}>{location.location_code || location.code || location.name}</option>)}
        </select>
        <div className="stx-sub">{line.warehouse_name}</div>
      </td>
      <td><input className="stx-cell-input stx-number" type="number" min="0" step="any"
        defaultValue={line.counted_quantity} key={line.id + ":qty:" + line.version} disabled={!canCount || saving}
        onKeyDown={event => { if (event.key === "Enter") event.currentTarget.blur(); }}
        onBlur={event => saveNumber(event.target)}/></td>
      <td><span className="num">{line.unit}</span></td>
      <td><span className="num">{line.book_quantity_snapshot}</span></td>
      <td><span className="num stx-diff" data-negative={line.diff_quantity < 0 ? "1" : "0"}>{line.diff_quantity > 0 ? "+" : ""}{line.diff_quantity}</span></td>
      <td>
        <T tone={tone} dot>{saving ? "保存中" : method}</T>
        {line.confidence != null && <div className="mono stx-sub">{Math.round(line.confidence * 100)}%</div>}
        {line.status === "recount_required" && canCount && !saving && <button type="button" className="tag redinv"
          onClick={() => onSave(line, { counted_quantity: line.counted_quantity, recount_confirmed: true })}>已重新清點</button>}
        {line.status === "possible_duplicate" && canReview && !saving && <button type="button" className="tag redinv"
          onClick={() => onMerge(line)}>合併疑似重複</button>}
        {canReview && !saving && <button type="button" className="tag" onClick={() => onExclude(line)}>排除誤掃</button>}
      </td>
    </tr>
  );
};

const LegacyFallback = ({ tasks, diffs, onStart }) => (
  <Band no="L" title="歷史盤點" sub="舊版任務／差異資料仍完整保留">
    {tasks.length ? <div className="stx-legacy-list">{tasks.map((task, index) => (
      <div className="ledger-row" key={task.key}>
        <span className="lr-idx">{pad2(index + 1)}</span>
        <div className="col g4" style={{ flex: 1 }}><strong>{task.name}</strong><span className="muted mono">{task.task_no} · {task.area} · {task.owner}</span></div>
        <span className="num">{task.done}/{task.total || "—"}</span><T tone={task.status === "done" ? "ok" : task.status === "active" ? "inv" : "plain"}>{task.progress}%</T>
      </div>
    ))}</div> : (
      <EM icon="clipboard" title="還沒有盤點任務" action={<B onClick={onStart}>發起盤點</B>}/>
    )}
    {diffs.length > 0 && <div className="stx-legacy-diffs">{diffs.slice(0, 12).map(diff => (
      <div className="row spread" key={diff.key}><span>{diff.item}</span><span className="num">{diff.book} → {diff.actual} ({diff.diff > 0 ? "+" : ""}{diff.diff})</span></div>
    ))}</div>}
  </Band>
);

const Page = ({ boot = {}, isOwner = false }) => {
  const liveTenant = activeCaptureTenant();
  const liveActorKey = captureActorKey(boot);
  const [captureContext, setCaptureContext] = useState(() => {
    const tenantSlug = activeCaptureTenant();
    const actorKey = captureActorKey(boot);
    return { tenantSlug, actorKey, deviceId: stocktakeDeviceForTenant(tenantSlug, actorKey) };
  });
  const { tenantSlug, actorKey, deviceId } = captureContext;
  const legacyTasks = useMemo(() => firstArray(boot.STOCKTAKE).map(normalizeTask), [boot]);
  const legacyDiffs = useMemo(() => firstArray(boot.STOCKTAKE_DIFF).map(normalizeDiff), [boot]);
  const bootAdjust = actorCanAdjust(boot, isOwner);
  const bootCount = actorCanCount(boot, isOwner);
  const [canAdjust, setCanAdjust] = useState(bootAdjust === true);
  const [canCount, setCanCount] = useState(bootCount === true);
  const [tasks, setTasks] = useState(legacyTasks);
  const [selectedId, setSelectedId] = useState("");
  const [task, setTask] = useState(null);
  const [summaryRaw, setSummaryRaw] = useState({});
  const [lines, setLines] = useState([]);
  const [categories, setCategories] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [locations, setLocations] = useState([]);
  const [captureSessions, setCaptureSessions] = useState([]);
  const [missingExpected, setMissingExpected] = useState([]);
  const [rejectedSequences, setRejectedSequences] = useState([]);
  const [loading, setLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [notice, setNotice] = useState(null);
  const [workMode, setWorkMode] = useState("capture");
  const [topologyMode, setTopologyMode] = useState("location");
  const [topologyFilter, setTopologyFilter] = useState(null);
  const [search, setSearch] = useState("");
  const [linePage, setLinePage] = useState(0);
  const [captureInput, setCaptureInput] = useState("");
  const [directQuantity, setDirectQuantity] = useState("1");
  const [quantityTouched, setQuantityTouched] = useState(false);
  const [packageCount, setPackageCount] = useState("");
  const [unitsPerPackage, setUnitsPerPackage] = useState("");
  const [looseQuantity, setLooseQuantity] = useState("");
  const [selectedLocation, setSelectedLocation] = useState("");
  const [unit, setUnit] = useState("件");
  const [unitTouched, setUnitTouched] = useState(false);
  const [captureBusy, setCaptureBusy] = useState(false);
  const [cameraOpen, setCameraOpen] = useState(false);
  const [voicePartial, setVoicePartial] = useState("");
  const [classifyBusy, setClassifyBusy] = useState(false);
  const [classifyError, setClassifyError] = useState("");
  const [draftDirty, setDraftDirty] = useState(false);
  const [savingIds, setSavingIds] = useState(new Set());
  const [commitBusy, setCommitBusy] = useState(false);
  const [sessionBusy, setSessionBusy] = useState(false);
  const [registrationBusy, setRegistrationBusy] = useState(false);
  const [deviceRegistered, setDeviceRegistered] = useState(false);
  const [localCloseMarker, setLocalCloseMarker] = useState("");
  const [commitResult, setCommitResult] = useState(null);
  const [captureQueue, setCaptureQueue] = useState(() => storedCaptureList(tenantSlug, deviceId, "pending"));
  const [captureFailures, setCaptureFailures] = useState(() => storedCaptureList(tenantSlug, deviceId, "failed"));
  const [repairCapture, setRepairCapture] = useState(null);
  const [expectedCapture, setExpectedCapture] = useState(null);
  const inputRef = useRef(null);
  const directQuantityRef = useRef(null);
  const captureFormRef = useRef(null);
  const captureRef = useRef(null);
  const commitRequestRef = useRef("");
  const selectedIdRef = useRef("");
  const detailSequenceRef = useRef(0);
  const captureQueueRef = useRef(captureQueue);
  const captureFailuresRef = useRef(captureFailures);
  const captureFlushRef = useRef(false);
  const captureFlushTokenRef = useRef("");
  const captureRetryRef = useRef(0);
  const deviceRegistrationRef = useRef(null);
  const registeredTaskRef = useRef("");
  const captureGenerationRef = useRef(0);
  const captureClosingRef = useRef(false);
  const deviceCloseInFlightRef = useRef(false);
  const flushTimerRef = useRef(null);
  const missingRefreshKeyRef = useRef("");
  const cameraCaptureContextRef = useRef(null);
  const voiceCaptureContextRef = useRef(null);
  selectedIdRef.current = selectedId;
  captureQueueRef.current = captureQueue;
  captureFailuresRef.current = captureFailures;

  useEffect(() => {
    const syncSharedQueue = event => {
      if (event.key === captureStoreKey(tenantSlug, deviceId, "pending")) {
        const next = storedCaptureList(tenantSlug, deviceId, "pending"); captureQueueRef.current = next; setCaptureQueue(next);
      }
      if (event.key === captureStoreKey(tenantSlug, deviceId, "failed")) {
        const next = storedCaptureList(tenantSlug, deviceId, "failed"); captureFailuresRef.current = next; setCaptureFailures(next);
      }
      if (selectedIdRef.current && event.key === captureStoreKey(tenantSlug, deviceId, "closed." + selectedIdRef.current)) {
        setLocalCloseMarker(event.newValue || "");
      }
    };
    window.addEventListener("storage", syncSharedQueue);
    return () => window.removeEventListener("storage", syncSharedQueue);
  }, [tenantSlug, deviceId]);

  useEffect(() => {
    if (liveTenant === tenantSlug && liveActorKey === actorKey) return;
    captureGenerationRef.current += 1;
    captureClosingRef.current = true;
    captureFlushRef.current = false;
    captureFlushTokenRef.current = "";
    if (flushTimerRef.current) window.clearTimeout(flushTimerRef.current);
    const next = { tenantSlug: liveTenant, actorKey: liveActorKey,
      deviceId: stocktakeDeviceForTenant(liveTenant, liveActorKey) };
    const nextQueue = storedCaptureList(next.tenantSlug, next.deviceId, "pending");
    const nextFailures = storedCaptureList(next.tenantSlug, next.deviceId, "failed");
    captureQueueRef.current = nextQueue; captureFailuresRef.current = nextFailures;
    setCaptureQueue(nextQueue); setCaptureFailures(nextFailures); setCaptureSessions([]);
    setRepairCapture(null); setExpectedCapture(null);
    registeredTaskRef.current = ""; setDeviceRegistered(false); setRegistrationBusy(false);
    setCaptureContext(next);
    captureClosingRef.current = false;
  }, [liveTenant, liveActorKey, tenantSlug, actorKey]);

  useEffect(() => () => {
    captureGenerationRef.current += 1;
    captureClosingRef.current = true;
    if (flushTimerRef.current) window.clearTimeout(flushTimerRef.current);
  }, []);

  useEffect(() => {
    const knownAdjust = actorCanAdjust(boot, isOwner);
    const knownCount = actorCanCount(boot, isOwner);
    if (knownAdjust != null && knownCount != null) {
      setCanAdjust(knownAdjust); setCanCount(knownCount); return undefined;
    }
    let alive = true;
    W2.json("/api/auth/me").then(data => {
      if (alive) {
        setCanAdjust(authMeCanAdjust(data, isOwner));
        setCanCount(authMeCanCount(data, isOwner));
      }
    }).catch(() => { if (alive) { setCanAdjust(false); setCanCount(false); } });
    return () => { alive = false; };
  }, [boot, isOwner]);

  const applyDetail = useCallback(data => {
    data = apiData(data);
    const nextTask = nested(data.task || data.stocktake);
    if (Object.keys(nextTask).length) setTask(normalizeTask(nextTask, 0));
    setSummaryRaw(nested(data.summary));
    setLines(firstArray(data.lines, data.draft_lines, data.items).map(normalizeLine));
    setCategories(firstArray(data.categories, nested(data.lookups).categories));
    setWarehouses(firstArray(data.warehouses, nested(data.lookups).warehouses));
    setLocations(firstArray(data.locations, nested(data.lookups).locations));
    setMissingExpected(firstArray(data.missing_expected));
    setRejectedSequences(firstArray(data.rejected_sequences).map(row => ({
      ...row, server_record: true, task_id: nextTask.id ?? nextTask.task_id,
      error: row.error || "服務器記錄的失敗採集", event: nested(row.event),
    })));
    const nextSessions = firstArray(data.capture_sessions, data.device_sessions);
    setCaptureSessions(nextSessions);
    const localSession = nextSessions.find(session => String(session.device_id) === deviceId);
    registeredTaskRef.current = localSession ? String(nextTask.id ?? nextTask.task_id ?? "") : "";
    setDeviceRegistered(!!localSession);
    if (localSession && (nextTask.id ?? nextTask.task_id)) {
      saveDeviceSequence(tenantSlug, deviceId, nextTask.id ?? nextTask.task_id, Math.max(
        storedDeviceSequence(tenantSlug, deviceId, nextTask.id ?? nextTask.task_id),
        n(localSession.last_sequence_received), n(localSession.last_sequence_reported),
        n(localSession.closed_sequence),
      ));
    }
  }, [tenantSlug, deviceId]);

  const loadDetail = useCallback(async (id, silent) => {
    const canonicalId = stocktakeRecordId(id);
    if (!canonicalId) return;
    const taskId = String(canonicalId);
    const sequence = ++detailSequenceRef.current;
    if (!silent) setLoading(true);
    setDetailError("");
    try {
      const data = await W2.json("/api/stocktake/" + encodeURIComponent(canonicalId));
      if (sequence !== detailSequenceRef.current || selectedIdRef.current !== taskId) return;
      applyDetail(data);
    } catch (error) {
      if (sequence !== detailSequenceRef.current || selectedIdRef.current !== taskId) return;
      setDetailError(error.message || "無法讀取盤點草稿");
    } finally {
      if (!silent && sequence === detailSequenceRef.current && selectedIdRef.current === taskId) setLoading(false);
    }
  }, [applyDetail]);

  const loadTasks = useCallback(async () => {
    try {
      const raw = await W2.json("/api/stocktake");
      const data = apiData(raw);
      const next = firstArray(data.tasks, data.stocktake, data.items).map(normalizeTask);
      if (next.length || !legacyTasks.length) setTasks(next);
    } catch (e) {}
  }, [legacyTasks.length]);

  useEffect(() => { loadTasks(); }, [loadTasks]);

  useEffect(() => {
    const refreshAfterSecretary = () => {
      loadTasks();
      if (selectedIdRef.current) loadDetail(selectedIdRef.current, true);
    };
    window.addEventListener("w2-agent-complete", refreshAfterSecretary);
    return () => window.removeEventListener("w2-agent-complete", refreshAfterSecretary);
  }, [loadTasks, loadDetail]);

  useEffect(() => {
    if (!tasks.length) { setSelectedId(""); return; }
    if (tasks.some(item => String(item.id) === String(selectedId))) return;
    const active = tasks.find(item => item.status === "active") || tasks[0];
    setSelectedId(String(active.id));
  }, [tasks, selectedId]);

  useEffect(() => {
    if (!selectedId) return;
    detailSequenceRef.current += 1;
    captureClosingRef.current = false;
    cameraCaptureContextRef.current = null;
    voiceCaptureContextRef.current = null;
    setCameraOpen(false);
    setLocalCloseMarker(localStorage.getItem(captureStoreKey(tenantSlug, deviceId, "closed." + selectedId)) || "");
    setTask(tasks.find(item => String(item.id) === String(selectedId)) || null);
    setLines([]); setCaptureSessions([]); setMissingExpected([]); setRejectedSequences([]); setRepairCapture(null); setExpectedCapture(null); setTopologyFilter(null); setCommitResult(null); setDraftDirty(false);
    registeredTaskRef.current = ""; setDeviceRegistered(false);
    commitRequestRef.current = "";
    missingRefreshKeyRef.current = "";
    loadDetail(selectedId, false);
  }, [selectedId, tenantSlug, deviceId]);

  useEffect(() => {
    const missingCount = n(summaryRaw.missing_expected_count);
    if (!selectedId || missingExpected.length || missingCount <= 0 || loading) return;
    const key = String(selectedId) + ":" + n(summaryRaw.draft_version) + ":" + missingCount;
    if (missingRefreshKeyRef.current === key) return;
    missingRefreshKeyRef.current = key;
    loadDetail(selectedId, true);
  }, [selectedId, missingExpected.length, summaryRaw.missing_expected_count,
    summaryRaw.draft_version, loading, loadDetail]);

  const selectedTask = task || tasks.find(item => String(item.id) === String(selectedId));
  const queueLockAvailable = captureLockSupported() && !!deviceId;
  const finalized = !!(selectedTask && (selectedTask.status === "done" || selectedTask.committed_document_id));
  const fullTask = !!(selectedTask && selectedTask.task_mode === "full");
  const captureClosed = !!(selectedTask && selectedTask.capture_closed_at) || !!summaryRaw.capture_closed;
  const currentDeviceSession = captureSessions.find(session => String(session.device_id) === deviceId);
  const deviceClosed = !!localCloseMarker || !!(currentDeviceSession && currentDeviceSession.status === "closed");
  const mutationBusy = classifyBusy || commitBusy || sessionBusy || savingIds.size > 0;
  const pendingCaptureCount = captureQueue.filter(entry => String(entry.task_id) === String(selectedId)).length;
  const selectedCaptureFailures = captureFailures.filter(entry => String(entry.task_id) === String(selectedId));
  const failedCaptureCount = selectedCaptureFailures.length;

  useEffect(() => {
    if (finalized || captureClosed) setWorkMode("review");
  }, [finalized, captureClosed]);

  const packageMode = packageCount !== "" || unitsPerPackage !== "" || looseQuantity !== "";
  const computedQuantity = packageMode
    ? Math.max(0, n(packageCount) * n(unitsPerPackage) + n(looseQuantity))
    : Math.max(0, n(directQuantity));

  const updateFromMutation = (data, lineMode = "replace") => {
    data = apiData(data);
    const responseLines = firstArray(data.lines, data.draft_lines);
    if (responseLines.length || Array.isArray(data.lines)) {
      const normalized = responseLines.map(normalizeLine);
      if (lineMode === "merge") {
        setLines(current => {
          const byId = new Map(current.map(line => [String(line.id), line]));
          normalized.forEach(line => byId.set(String(line.id), line));
          return [...byId.values()].sort((a, b) => n(a.id) - n(b.id));
        });
      } else setLines(normalized);
    }
    if (data.summary) setSummaryRaw(current => ({ ...current, ...nested(data.summary) }));
    if (data.task) setTask(normalizeTask(data.task, 0));
  };

  const deviceSequenceForTask = taskId => Math.max(
    storedDeviceSequence(tenantSlug, deviceId, taskId),
    String(taskId) === String(selectedId) ? n(currentDeviceSession && currentDeviceSession.last_sequence_received) : 0,
    String(taskId) === String(selectedId) ? n(currentDeviceSession && currentDeviceSession.last_sequence_reported) : 0,
    String(taskId) === String(selectedId) ? n(currentDeviceSession && currentDeviceSession.closed_sequence) : 0,
    ...captureQueueRef.current.filter(entry => String(entry.task_id) === String(taskId))
      .map(entry => n(entry.event && entry.event.device_sequence)),
    ...captureFailuresRef.current.filter(entry => String(entry.task_id) === String(taskId))
      .map(entry => n(entry.event && entry.event.device_sequence)),
  );

  const ensureDeviceRegistered = async (taskId, explicitTail) => {
    taskId = String(taskId);
    if (!queueLockAvailable) {
      setNotice({ tone: "bad", text: deviceId
        ? "此瀏覽器缺少安全離線佇列鎖，尚未登記設備；請先升級 Safari／Chrome。"
        : "此瀏覽器無法持久保存設備身份，尚未登記設備；請退出隱私模式或釋放網站儲存空間。" });
      return false;
    }
    if (activeCaptureTenant() !== tenantSlug || captureActorKey(null) !== actorKey || captureClosingRef.current) return false;
    if (registeredTaskRef.current === taskId && currentDeviceSession
        && currentDeviceSession.status !== "closed") return true;
    if (deviceRegistrationRef.current) return deviceRegistrationRef.current;
    const generation = captureGenerationRef.current;
    const tail = explicitTail == null ? deviceSequenceForTask(taskId) : n(explicitTail);
    setRegistrationBusy(true);
    deviceRegistrationRef.current = W2.post(
      "/api/stocktake/" + encodeURIComponent(taskId) + "/devices/" + encodeURIComponent(deviceId) + "/open",
      { last_sequence_reported: tail },
    ).then(data => {
      const response = apiData(data);
      captureRetryRef.current = 0;
      const session = nested(response.device_session);
      if (generation !== captureGenerationRef.current || activeCaptureTenant() !== tenantSlug) return false;
      if (String(selectedIdRef.current) === taskId) {
        setCaptureSessions(current => [
          ...current.filter(item => String(item.device_id) !== deviceId), session,
        ]);
        setDeviceRegistered(true);
      }
      registeredTaskRef.current = taskId;
      saveDeviceSequence(tenantSlug, deviceId, taskId, Math.max(
        tail, n(session.last_sequence_received), n(session.last_sequence_reported), n(session.closed_sequence),
      ));
      if (session.status === "closed" || response.requires_reopen || session.requires_reopen) {
        if (String(selectedIdRef.current) === taskId) {
          setNotice({ tone: "bad", text: "本設備此前已結束採集；請先選擇“本機續盤”。" });
        }
        return false;
      }
      return true;
    }).catch(error => {
      if (generation === captureGenerationRef.current && activeCaptureTenant() === tenantSlug
          && String(selectedIdRef.current) === taskId) {
        setNotice({ tone: "bad", text: (error.message || "設備登記失敗") + "。首次採集尚未入隊；請恢復網絡後重試。" });
      }
      return false;
    }).finally(() => {
      if (generation === captureGenerationRef.current) setRegistrationBusy(false);
      deviceRegistrationRef.current = null;
    });
    return deviceRegistrationRef.current;
  };

  const flushCaptureQueue = async () => {
    if (captureFlushRef.current || !queueLockAvailable || activeCaptureTenant() !== tenantSlug
        || captureActorKey(null) !== actorKey) return;
    captureFlushRef.current = true;
    const flushToken = uuid("flush");
    captureFlushTokenRef.current = flushToken;
    setCaptureBusy(true);
    const generation = captureGenerationRef.current;
    let taskId = "";
    try {
      const snapshot = await withCaptureLock(tenantSlug, deviceId, () => {
        const pending = storedCaptureList(tenantSlug, deviceId, "pending")
          .filter(entry => String(entry.tenant_slug) === tenantSlug && String(entry.actor_key) === actorKey);
        const failures = storedCaptureList(tenantSlug, deviceId, "failed");
        if (!pending.length) return { pending, failures, empty: true };
        const nextTaskId = String(pending[0].task_id);
        const batch = pending.filter(entry => String(entry.task_id) === nextTaskId).slice(0, 200);
        const queueTail = Math.max(
          storedDeviceSequence(tenantSlug, deviceId, nextTaskId),
          ...pending.filter(entry => String(entry.task_id) === nextTaskId).map(entry => n(entry.event.device_sequence)),
          ...failures.filter(entry => String(entry.task_id) === nextTaskId).map(entry => n(entry.event.device_sequence)),
        );
        return { taskId: nextTaskId, batch, queueTail, pending, failures, empty: false };
      });
      if (!snapshot || generation !== captureGenerationRef.current || activeCaptureTenant() !== tenantSlug
          || captureActorKey(null) !== actorKey) return;
      captureQueueRef.current = snapshot.pending; captureFailuresRef.current = snapshot.failures;
      setCaptureQueue(snapshot.pending); setCaptureFailures(snapshot.failures);
      if (snapshot.empty) return;
      taskId = snapshot.taskId;
      const { batch, queueTail } = snapshot;
      const sentIds = new Set(batch.map(entry => entry.event.client_event_id));
      if (!(await ensureDeviceRegistered(taskId, queueTail))) return;
      if (generation !== captureGenerationRef.current || activeCaptureTenant() !== tenantSlug
          || captureActorKey(null) !== actorKey) return;
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/capture", {
        device_id: deviceId,
        queue_tail_sequence: queueTail,
        events: batch.map(entry => entry.event), auto_rebuild: true,
      });
      if (generation !== captureGenerationRef.current || activeCaptureTenant() !== tenantSlug
          || captureActorKey(null) !== actorKey) return;
      const response = apiData(data);
      const rejected = Array.isArray(response.rejected) ? response.rejected : [];
      const failed = batch.map((entry, index) => ({
        entry, rejection: rejected.find(item => n(item.index) === index),
      })).filter(item => item.rejection).map(item => ({
        ...item.entry, error: item.rejection.error || "採集資料不完整",
        error_code: item.rejection.error_code || "validation_error",
      }));
      const persisted = await withCaptureLock(tenantSlug, deviceId, () => {
        const latestPending = storedCaptureList(tenantSlug, deviceId, "pending");
        const latestFailures = storedCaptureList(tenantSlug, deviceId, "failed");
        const failureById = new Map(latestFailures.map(entry => [entry.event.client_event_id, entry]));
        sentIds.forEach(eventId => failureById.delete(eventId));
        failed.forEach(entry => failureById.set(entry.event.client_event_id, entry));
        const nextFailures = [...failureById.values()];
        const nextPending = latestPending.filter(entry => !sentIds.has(entry.event.client_event_id));
        if (!saveCaptureList(tenantSlug, deviceId, "failed", nextFailures)) {
          throw new Error("本機儲存空間不足，失敗採集尚未移出待同步佇列");
        }
        if (!saveDeviceSequence(tenantSlug, deviceId, taskId, queueTail)) {
          throw new Error("無法保存設備同步序號，資料將保留並安全重試");
        }
        if (!saveCaptureList(tenantSlug, deviceId, "pending", nextPending)) {
          throw new Error("無法更新本機待同步佇列，服務器已按事件編號去重，可安全重試");
        }
        return { nextPending, nextFailures };
      });
      if (generation !== captureGenerationRef.current || activeCaptureTenant() !== tenantSlug
          || captureActorKey(null) !== actorKey) return;
      captureQueueRef.current = persisted.nextPending; captureFailuresRef.current = persisted.nextFailures;
      setCaptureQueue(persisted.nextPending); setCaptureFailures(persisted.nextFailures);
      const coveredLines = firstArray(response.lines, response.draft_lines);
      if (coveredLines.length) {
        setMissingExpected(current => current.filter(expected => !coveredLines.some(line =>
          n(line.item_id) === n(expected.item_id)
          && n(line.warehouse_id) === n(expected.warehouse_id)
          && n(line.location_id) === n(expected.location_id))));
      }
      if (selectedIdRef.current === taskId) {
        updateFromMutation(data, "merge");
        if (n(response.accepted)) setDraftDirty(true);
        const duplicates = n(response.duplicates);
        setNotice(failed.length
          ? { tone: "bad", text: failed.length + " 筆未通過校驗，已保留在失敗佇列；其餘資料已同步。" }
          : { tone: "ok", text: duplicates ? "重複採集事件已安全忽略" : t("已加入草稿,可繼續下一種") });
        if (failed.length) loadDetail(taskId, true);
      }
    } catch (error) {
      captureRetryRef.current = Math.min(captureRetryRef.current + 1, 5);
      if (activeCaptureTenant() === tenantSlug && selectedIdRef.current === taskId) setNotice({ tone: "bad", text: (error.message || "同步失敗") + "。待同步資料已保存在本機，網絡恢復後會用原事件編號安全續傳。" });
    } finally {
      const stillOwnsFlush = captureFlushTokenRef.current === flushToken;
      if (stillOwnsFlush) { captureFlushRef.current = false; captureFlushTokenRef.current = ""; }
      if (stillOwnsFlush && generation === captureGenerationRef.current
          && activeCaptureTenant() === tenantSlug && captureActorKey(null) === actorKey) {
        setCaptureBusy(false);
        const remaining = storedCaptureList(tenantSlug, deviceId, "pending");
        captureQueueRef.current = remaining;
        if (remaining.length) {
          const retryDelay = Math.min(30000, 2000 * Math.pow(2, Math.max(0, captureRetryRef.current - 1)));
          flushTimerRef.current = window.setTimeout(flushCaptureQueue, retryDelay);
        }
      }
    }
  };

  useEffect(() => {
    if (!captureQueue.length || captureFlushRef.current) return undefined;
    flushTimerRef.current = window.setTimeout(flushCaptureQueue, 80);
    return () => { if (flushTimerRef.current) window.clearTimeout(flushTimerRef.current); };
  }, [captureQueue.length, tenantSlug, deviceId]);

  const sendCaptureEvent = async (event, targetTaskId, targetTenant, options = {}) => {
    const taskId = String(targetTaskId || selectedId || "");
    const eventTenant = String(targetTenant || tenantSlug);
    if (!taskId || taskId !== String(selectedIdRef.current) || eventTenant !== tenantSlug
        || eventTenant !== activeCaptureTenant() || captureActorKey(null) !== actorKey || !queueLockAvailable
        || !canCount || finalized || captureClosed || deviceClosed
        || captureClosingRef.current || sessionBusy || registrationBusy
        || activeCaptureTenant() !== tenantSlug) return;
    if (!(await ensureDeviceRegistered(taskId))) return;
    let queued = null;
    try {
      queued = await withCaptureLock(tenantSlug, deviceId, () => {
        if (localStorage.getItem(captureStoreKey(tenantSlug, deviceId, "closed." + taskId))) {
          throw new Error("本設備已結束採集；請先在草稿頁選擇“本機續盤”");
        }
        const pending = storedCaptureList(tenantSlug, deviceId, "pending");
        const failures = storedCaptureList(tenantSlug, deviceId, "failed");
        const nextSequence = Math.max(
          storedDeviceSequence(tenantSlug, deviceId, taskId),
          n(currentDeviceSession && currentDeviceSession.last_sequence_received),
          n(currentDeviceSession && currentDeviceSession.last_sequence_reported),
          n(currentDeviceSession && currentDeviceSession.closed_sequence),
          ...pending.filter(entry => String(entry.task_id) === taskId).map(entry => n(entry.event.device_sequence)),
          ...failures.filter(entry => String(entry.task_id) === taskId).map(entry => n(entry.event.device_sequence)),
        ) + 1;
        let deviceSequence = nextSequence;
        let nextFailures = failures;
        if (options.repair) {
          const originalEventId = options.original_client_event_id || event.client_event_id;
          const failedEntry = failures.find(entry => entry.event.client_event_id === originalEventId
            && n(entry.event.device_sequence) === n(event.device_sequence)
            && String(entry.task_id) === taskId && String(entry.tenant_slug) === tenantSlug
            && String(entry.actor_key) === actorKey && String(entry.event.device_id) === deviceId);
          if (!failedEntry) throw new Error("找不到要修正的原失敗事件，請刷新後重試");
          deviceSequence = n(failedEntry.event.device_sequence);
          nextFailures = failures.filter(entry => entry !== failedEntry);
        }
        const deviceEvent = { ...event, device_id: deviceId, device_sequence: deviceSequence };
        const nextEntry = { tenant_slug: tenantSlug, actor_key: actorKey, task_id: taskId,
          event: deviceEvent, queued_at: new Date().toISOString() };
        const nextPending = [...pending, nextEntry];
        if (!saveCaptureList(tenantSlug, deviceId, "pending", nextPending)) return null;
        if (options.repair && !saveCaptureList(tenantSlug, deviceId, "failed", nextFailures)) {
          throw new Error("修正事件已排隊，但無法清理失敗副本；事件編號會阻止重複計數");
        }
        saveDeviceSequence(tenantSlug, deviceId, taskId, deviceSequence);
        captureQueueRef.current = nextPending; captureFailuresRef.current = nextFailures;
        setCaptureQueue(nextPending); setCaptureFailures(nextFailures);
        return nextEntry;
      });
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "無法取得本機採集鎖；請只保留一個盤點分頁後重試。" });
      return;
    }
    if (!queued) {
      setNotice({ tone: "bad", text: "本機儲存空間不足，這筆尚未安全保存；請先不要移動貨品並釋放瀏覽器空間。" });
      return;
    }
    setNotice({ tone: "ok", text: "已进入本机待同步队列，可立即继续下一种。" });
    successFeedback();
    setCaptureInput(""); setVoicePartial("");
    setDirectQuantity("1"); setQuantityTouched(false);
    setPackageCount(""); setUnitsPerPackage(""); setLooseQuantity("");
    window.setTimeout(() => inputRef.current && inputRef.current.focus(), 20);
    return true;
  };

  const retryFailedCaptures = async () => {
    try {
      const retryCount = await withCaptureLock(tenantSlug, deviceId, () => {
        const pending = storedCaptureList(tenantSlug, deviceId, "pending");
        const failures = storedCaptureList(tenantSlug, deviceId, "failed");
        const retry = failures.filter(entry => String(entry.task_id) === String(selectedId));
        if (!retry.length) return 0;
        const keep = failures.filter(entry => String(entry.task_id) !== String(selectedId));
        const pendingById = new Map(pending.map(entry => [entry.event.client_event_id, entry]));
        retry.forEach(({ error, ...entry }) => pendingById.set(entry.event.client_event_id, entry));
        const nextPending = [...pendingById.values()];
        if (!saveCaptureList(tenantSlug, deviceId, "pending", nextPending)
            || !saveCaptureList(tenantSlug, deviceId, "failed", keep)) {
          throw new Error("本機儲存空間不足，失敗資料仍完整保留");
        }
        captureQueueRef.current = nextPending; captureFailuresRef.current = keep;
        setCaptureQueue(nextPending); setCaptureFailures(keep);
        return retry.length;
      });
      if (retryCount) setNotice({ tone: "ok", text: retryCount + " 筆失敗資料已用原事件編號重新排隊。" });
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "失敗資料重新排隊失敗。" });
    }
  };

  const beginRepairCapture = async entry => {
    const event = entry.event || {};
    if (entry.server_record) {
      try {
        await withCaptureLock(tenantSlug, deviceId, () => {
          const failures = storedCaptureList(tenantSlug, deviceId, "failed");
          if (failures.some(item => item.event.client_event_id === event.client_event_id)) return;
          const imported = { tenant_slug: tenantSlug, actor_key: actorKey,
            task_id: String(entry.task_id || selectedId), event, error: entry.error,
            error_code: entry.error_code || "validation_error", queued_at: new Date().toISOString() };
          const nextFailures = [...failures, imported];
          if (!saveCaptureList(tenantSlug, deviceId, "failed", nextFailures)) throw new Error("無法恢復服務器失敗事件到本機");
          captureFailuresRef.current = nextFailures; setCaptureFailures(nextFailures);
        });
      } catch (error) {
        setNotice({ tone: "bad", text: error.message || "失敗事件恢復失敗。" }); return;
      }
    }
    setRepairCapture({ ...entry, bound_task_id: String(selectedId), bound_tenant: tenantSlug, bound_actor: actorKey });
    setCaptureInput(event.barcode || event.raw_text || event.item_name || "");
    setDirectQuantity(event.quantity == null ? "" : String(event.quantity));
    setQuantityTouched(event.quantity != null);
    setPackageCount(event.package_count == null ? "" : String(event.package_count));
    setUnitsPerPackage(event.package_size == null ? "" : String(event.package_size));
    setLooseQuantity(event.loose_quantity == null ? "" : String(event.loose_quantity));
    setUnit(event.unit || "件"); setUnitTouched(!!event.unit);
    setSelectedLocation(event.location_id == null ? "" : String(event.location_id));
    setNotice({ tone: "bad", text: "已載入設備序號 " + n(event.device_sequence) + " 到上方表單；請補填實盤數量，再保存修正。原事件編號不變，不會重複計數。" });
    setWorkMode("capture");
    window.requestAnimationFrame(() => {
      const target = event.quantity == null ? directQuantityRef.current : inputRef.current;
      if (captureFormRef.current) captureFormRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      window.setTimeout(() => {
        if (target) { target.focus(); if (typeof target.select === "function") target.select(); }
      }, 250);
    });
  };

  const resolveAcceptedSequenceConflict = async entry => {
    const event = entry.event || {};
    try {
      await withCaptureLock(tenantSlug, deviceId, () => {
        const pending = storedCaptureList(tenantSlug, deviceId, "pending");
        const failures = storedCaptureList(tenantSlug, deviceId, "failed");
        const original = failures.find(item => item.event.client_event_id === event.client_event_id
          && String(item.task_id) === String(entry.task_id));
        if (!original) throw new Error("此衝突事件已在另一分頁處理");
        let nextPending = pending;
        if (entry.error_code === "device_sequence_already_accepted") {
          if (localStorage.getItem(captureStoreKey(tenantSlug, deviceId, "closed." + entry.task_id))) {
            throw new Error("本設備已結束，請先續盤後再重新編號");
          }
          const nextSequence = n(original.replay_sequence) || (Math.max(
            storedDeviceSequence(tenantSlug, deviceId, entry.task_id),
            n(currentDeviceSession && currentDeviceSession.last_sequence_received),
            n(currentDeviceSession && currentDeviceSession.last_sequence_reported),
            ...pending.filter(item => String(item.task_id) === String(entry.task_id)).map(item => n(item.event.device_sequence)),
            ...failures.filter(item => String(item.task_id) === String(entry.task_id)).map(item => n(item.event.device_sequence)),
          ) + 1);
          const replayEventId = original.replay_event_id || (String(event.client_event_id).slice(0, 185) + "-replay");
          if (!original.replay_sequence || !original.replay_event_id) {
            const journaledFailures = failures.map(item => item === original
              ? { ...item, replay_sequence: nextSequence, replay_event_id: replayEventId } : item);
            if (!saveCaptureList(tenantSlug, deviceId, "failed", journaledFailures)) {
              throw new Error("無法建立重新編號恢復日誌，原失敗資料仍保留");
            }
          }
          const replay = { ...event, client_event_id: replayEventId, device_id: deviceId,
            device_sequence: nextSequence };
          const pendingById = new Map(pending.map(item => [item.event.client_event_id, item]));
          pendingById.set(replayEventId, { ...entry, error: undefined, error_code: undefined,
            event: replay, queued_at: new Date().toISOString() });
          nextPending = [...pendingById.values()];
          if (!saveCaptureList(tenantSlug, deviceId, "pending", nextPending)) {
            throw new Error("新序號尚未安全入隊，原失敗資料仍保留");
          }
          saveDeviceSequence(tenantSlug, deviceId, entry.task_id, nextSequence);
        }
        const nextFailures = failures.filter(item => item.event.client_event_id !== event.client_event_id);
        if (!saveCaptureList(tenantSlug, deviceId, "failed", nextFailures)) throw new Error("本機失敗佇列更新失敗");
        captureFailuresRef.current = nextFailures; captureQueueRef.current = nextPending;
        setCaptureFailures(nextFailures); setCaptureQueue(nextPending);
      });
      if (entry.error_code === "device_sequence_already_accepted") {
        setNotice({ tone: "ok", text: "衝突事件已用新序號重新入隊，不會漏計。" });
      } else {
        setNotice({ tone: "ok", text: "服務器已確認原序號進入草稿，本機衝突副本已清除。" });
      }
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "處理已接收序號衝突失敗。" });
    }
  };

  const voidFailedCapture = async entry => {
    const event = entry.event || {};
    const reason = window.prompt("請填寫作廢原因（至少 4 個字）。作廢只跳過這個誤掃序號，不會建立草稿行：", "現場確認為誤掃");
    if (!reason) return;
    const targetDeviceId = event.device_id || entry.device_id || deviceId;
    const targetSequence = event.device_sequence || entry.device_sequence;
    const foreignDevice = String(targetDeviceId) !== deviceId;
    if (foreignDevice && !canAdjust) {
      setNotice({ tone: "bad", text: "只能由原設備處理；庫存負責人可審計接管作廢。" }); return;
    }
    try {
      await withCaptureLock(tenantSlug, deviceId, async () => {
        const pending = storedCaptureList(tenantSlug, deviceId, "pending");
        const failures = storedCaptureList(tenantSlug, deviceId, "failed");
        const stillFailed = failures.some(item => item.event.client_event_id === event.client_event_id
          && n(item.event.device_sequence) === n(event.device_sequence)
          && String(item.task_id) === String(entry.task_id));
        if (!stillFailed && !entry.server_record) throw new Error("此失敗事件已在另一分頁處理，請刷新");
        await W2.post("/api/stocktake/" + encodeURIComponent(entry.task_id) + "/devices/"
          + encodeURIComponent(targetDeviceId) + "/sequences/"
          + encodeURIComponent(targetSequence) + "/void", {
            confirmed: true, reason, override: foreignDevice,
            override_reason: foreignDevice ? reason : undefined,
          });
        const nextFailures = failures.filter(item => item.event.client_event_id !== event.client_event_id);
        const nextPending = pending.filter(item => item.event.client_event_id !== event.client_event_id);
        if (!saveCaptureList(tenantSlug, deviceId, "failed", nextFailures)
            || !saveCaptureList(tenantSlug, deviceId, "pending", nextPending)) {
          throw new Error("服務器已作廢，但本機佇列更新失敗；刷新後可安全重試");
        }
        captureFailuresRef.current = nextFailures; captureQueueRef.current = nextPending;
        setCaptureFailures(nextFailures); setCaptureQueue(nextPending);
      });
      if (repairCapture && repairCapture.event.client_event_id === event.client_event_id) setRepairCapture(null);
      await loadDetail(entry.task_id, true);
      setNotice({ tone: "ok", text: "設備序號 " + n(targetSequence) + " 已審計作廢；它不會進入盤點草稿。" });
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "作廢失敗採集失敗。" });
    }
  };

  const captureMissingAsZero = expected => {
    const itemName = expected.item_name || "既有物資";
    sendCaptureEvent({
      client_event_id: uuid("missing-zero"), capture_type: "manual",
      item_id: expected.item_id, item_name: itemName, spec_model: expected.spec_model || null,
      quantity: 0, unit: expected.unit || "件",
      warehouse_id: expected.warehouse_id || null, location_id: expected.location_id || null,
      warehouse_name: expected.warehouse_name || null, location_code: expected.location_code || null,
      raw_text: itemName + " 明確實盤為 0",
    }, String(selectedId), tenantSlug);
  };

  const locateMissingCapture = expected => {
    setExpectedCapture({ ...expected, bound_task_id: String(selectedId), bound_tenant: tenantSlug, bound_actor: actorKey });
    setSelectedLocation(expected.location_id ? String(expected.location_id) : "");
    setCaptureInput(expected.item_name || "");
    setDirectQuantity("1"); setQuantityTouched(false);
    setWorkMode("capture");
    window.setTimeout(() => inputRef.current && inputRef.current.focus(), 40);
  };

  const submitCapture = useCallback(({ value, captureType, taskId, captureTenant: eventTenant } = {}) => {
    const targetTaskId = String(taskId || selectedId || "");
    const targetTenant = String(eventTenant || tenantSlug);
    if (targetTaskId !== String(selectedIdRef.current) || targetTenant !== activeCaptureTenant()) {
      setNotice({ tone: "bad", text: "盤點任務或公司已切換，晚到的掃碼／語音沒有入隊；請在目前任務重新採集。" });
      return;
    }
    if (repairCapture && (repairCapture.bound_task_id !== targetTaskId
        || repairCapture.bound_tenant !== targetTenant || repairCapture.bound_actor !== actorKey)) {
      setRepairCapture(null);
      setNotice({ tone: "bad", text: "失敗事件屬於另一個任務或帳號，已取消修正。" });
      return;
    }
    if (expectedCapture && (expectedCapture.bound_task_id !== targetTaskId
        || expectedCapture.bound_tenant !== targetTenant || expectedCapture.bound_actor !== actorKey)) {
      setExpectedCapture(null);
      setNotice({ tone: "bad", text: "缺盤項屬於另一個任務或帳號，請重新選擇。" });
      return;
    }
    const raw = String(value != null ? value : captureInput).trim();
    if (!raw) { setNotice({ tone: "bad", text: "請掃描條碼,或輸入／說出物資名稱。" }); inputRef.current && inputRef.current.focus(); return; }
    if (!packageMode && captureType !== "voice" && String(directQuantity).trim() === "") {
      setNotice({ tone: "bad", text: "請明確輸入實盤數量；輸入數字 0 才表示實盤為零。" }); return;
    }
    if (packageMode && ((packageCount !== "" || unitsPerPackage !== "")
        && (packageCount === "" || unitsPerPackage === ""))) {
      setNotice({ tone: "bad", text: "包裝換算請同時填寫箱／包數與每箱／包數；明確填 0 可表示零庫存。" }); return;
    }
    if (n(directQuantity) < 0 || n(packageCount) < 0 || n(unitsPerPackage) < 0 || n(looseQuantity) < 0) {
      setNotice({ tone: "bad", text: "盤點數量不能小於 0；明確輸入 0 可表示該物資實盤為零。" }); return;
    }
    const type = captureType || (looksLikeBarcode(raw) ? "barcode" : "manual");
    const location = locations.find(item => String(item.id ?? item.location_id) === String(selectedLocation));
    const useExplicitQuantity = type !== "voice" || quantityTouched || packageMode;
    const repairEvent = repairCapture && repairCapture.event ? repairCapture.event : null;
    const event = {
      client_event_id: repairEvent
        ? (repairCapture.error_code === "client_event_id_conflict" ? uuid("capture-repair") : repairEvent.client_event_id)
        : uuid("capture"),
      device_id: repairEvent ? repairEvent.device_id : undefined,
      device_sequence: repairEvent ? repairEvent.device_sequence : undefined,
      capture_type: type,
      barcode: type === "barcode" ? raw : null,
      raw_text: type === "barcode" ? null : raw,
      item_name: type === "manual" && !looksLikeBarcode(raw) ? raw : null,
      item_id: (expectedCapture && expectedCapture.item_id) || (repairEvent && repairEvent.item_id) || null,
      spec_model: (expectedCapture && expectedCapture.spec_model) || (repairEvent && repairEvent.spec_model) || null,
      quantity: useExplicitQuantity ? computedQuantity : null,
      unit: unitTouched ? (unit || "件") : null,
      package_count: packageMode ? n(packageCount) : null,
      units_per_package: packageMode ? n(unitsPerPackage) : null,
      package_size: packageMode ? n(unitsPerPackage) : null,
      loose_quantity: packageMode ? n(looseQuantity) : null,
      warehouse_id: location ? valueForApi(location.warehouse_id)
        : ((expectedCapture && expectedCapture.warehouse_id) || (repairEvent && repairEvent.warehouse_id) || null),
      location_id: selectedLocation ? valueForApi(selectedLocation)
        : ((expectedCapture && expectedCapture.location_id) || (repairEvent && repairEvent.location_id) || null),
      location_code: location ? (location.location_code || location.code || location.name || null)
        : ((expectedCapture && expectedCapture.location_code) || (repairEvent && repairEvent.location_code) || null),
    };
    const queued = sendCaptureEvent(event, targetTaskId, targetTenant, {
      repair: !!repairEvent,
      original_client_event_id: repairEvent ? repairEvent.client_event_id : null,
    });
    return Promise.resolve(queued).then(ok => {
      if (ok) { setRepairCapture(null); setExpectedCapture(null); }
      return ok;
    });
  }, [captureInput, packageMode, quantityTouched, computedQuantity, locations, selectedLocation, unit, unitTouched, selectedId, tenantSlug, canCount, finalized, captureClosed, deviceClosed, repairCapture, expectedCapture]);
  captureRef.current = submitCapture;

  const voiceHook = W2.useVoice || (() => ({ listening: false, error: "語音模組尚未載入", supported: false, micClick: () => {} }));
  const voice = voiceHook(
    transcript => {
      const context = voiceCaptureContextRef.current || {};
      return captureRef.current && captureRef.current({ value: transcript, captureType: "voice",
        taskId: context.taskId, captureTenant: context.tenantSlug });
    },
    partial => setVoicePartial(partial || ""),
  );

  const classifyDraft = useCallback(async () => {
    if (!selectedId || classifyBusy || !lines.length || finalized) return;
    const taskId = String(selectedId);
    setClassifyBusy(true); setClassifyError("");
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/classify", {});
      if (selectedIdRef.current !== taskId) return;
      updateFromMutation(data);
      setDraftDirty(false);
      const response = apiData(data);
      setNotice({ tone: "ok", text: "AI 已按整份草稿批量匹配、去重和分類；請只處理集中列出的異常。" });
      if (n(response.unresolved)) setClassifyError("仍有 " + n(response.unresolved) + " 個品種需要抽查或補充資料。");
    } catch (error) {
      setClassifyError(error.message || "AI 整理失敗,請重試");
    } finally { setClassifyBusy(false); }
  }, [selectedId, classifyBusy, lines.length, finalized]);

  const finishDeviceCapture = async () => {
    if (!selectedId || sessionBusy || finalized) return;
    if (cameraOpen || voice.listening || voice.finalizing) {
      setNotice({ tone: "bad", text: "請先完成目前的掃碼／語音，等待它入隊同步後再結束本機採集。" });
      return;
    }
    if (pendingCaptureCount || failedCaptureCount || captureBusy) {
      setNotice({ tone: "bad", text: "本設備仍有待同步或失敗資料；全部歸零後才能安全結束採集。" });
      return;
    }
    const taskId = String(selectedId);
    if (!(await ensureDeviceRegistered(taskId))) return;
    captureClosingRef.current = true;
    setCameraOpen(false);
    deviceCloseInFlightRef.current = true;
    setSessionBusy(true);
    let closed = false;
    try {
      const finalSequence = await withCaptureLock(tenantSlug, deviceId, async () => {
        const pending = storedCaptureList(tenantSlug, deviceId, "pending")
          .filter(entry => String(entry.task_id) === taskId);
        const failed = storedCaptureList(tenantSlug, deviceId, "failed")
          .filter(entry => String(entry.task_id) === taskId);
        if (pending.length || failed.length || captureFlushRef.current) {
          throw new Error("本設備仍有待同步或失敗資料；全部歸零後才能安全結束採集");
        }
        const tail = deviceSequenceForTask(taskId);
        const closedKey = captureStoreKey(tenantSlug, deviceId, "closed." + taskId);
        const closingMarker = "closing:" + uuid("close") + ":" + tail;
        localStorage.setItem(closedKey, closingMarker);
        try {
          await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/devices/"
            + encodeURIComponent(deviceId) + "/close", { final_sequence: tail });
          if (localStorage.getItem(closedKey) === closingMarker) {
            localStorage.setItem(closedKey, "closed"); setLocalCloseMarker("closed");
          }
        } catch (error) {
          if (localStorage.getItem(closedKey) === closingMarker) {
            localStorage.removeItem(closedKey); setLocalCloseMarker("");
          }
          throw error;
        }
        return tail;
      });
      closed = true;
      if (selectedIdRef.current !== taskId) return;
      await loadDetail(taskId, true);
      setWorkMode("review");
      setNotice({ tone: "ok", text: "本設備 " + finalSequence + " 筆採集已全部到達服務器並安全結束；可集中復核草稿。" });
      if (draftDirty && lines.length) classifyDraft();
    } catch (error) {
      if (selectedIdRef.current === taskId) setNotice({ tone: "bad", text: error.message || "設備仍有採集序號缺口，請先完成同步。" });
    } finally { deviceCloseInFlightRef.current = false; if (!closed) captureClosingRef.current = false; setSessionBusy(false); }
  };

  const reopenDeviceCapture = async () => {
    if (!selectedId || sessionBusy || finalized || captureClosed) return;
    const taskId = String(selectedId);
    setSessionBusy(true);
    try {
      await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/devices/"
        + encodeURIComponent(deviceId) + "/reopen", { confirmed: true });
      await withCaptureLock(tenantSlug, deviceId, () => {
        localStorage.removeItem(captureStoreKey(tenantSlug, deviceId, "closed." + taskId));
      });
      setLocalCloseMarker("");
      if (selectedIdRef.current !== taskId) return;
      await loadDetail(taskId, true);
      captureClosingRef.current = false;
      setWorkMode("capture");
      setNotice({ tone: "ok", text: "本設備已重新開放，會從下一個連續序號安全續傳。" });
    } catch (error) {
      if (selectedIdRef.current === taskId) setNotice({ tone: "bad", text: error.message || "無法重新開放本設備。" });
    } finally { setSessionBusy(false); }
  };

  const closeAllCapture = async () => {
    if (!selectedId || sessionBusy || finalized || captureClosed || !canAdjust) return;
    const taskId = String(selectedId);
    const voidedCount = n(summaryRaw.voided_sequence_count);
    if (voidedCount > 0 && !window.confirm("本單有 " + voidedCount + " 筆失敗採集已審計作廢，確認已逐筆核對後鎖定全部採集？")) return;
    setSessionBusy(true);
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/close", {
        confirmed: true, acknowledged_void_count: voidedCount,
      });
      if (selectedIdRef.current !== taskId) return;
      applyDetail(data);
      captureClosingRef.current = true;
      setWorkMode("review");
      setNotice({ tone: "ok", text: "全部設備均已同步結束，整單採集已鎖定；現在只需集中處理異常並最後確認入賬。" });
    } catch (error) {
      if (selectedIdRef.current === taskId) {
        setNotice({ tone: "bad", text: error.message || "仍有設備未結束或未同步，暫時不能鎖定整單。" });
        loadDetail(taskId, true);
      }
    } finally { setSessionBusy(false); }
  };

  const abandonLostDevice = async session => {
    if (!canAdjust || sessionBusy) return;
    const missing = Math.max(0, n(session.last_sequence_reported) - n(session.last_sequence_received));
    const reason = window.prompt(
      "高風險接管：此設備有 " + missing + " 個尚未到達服務器的序號。請填寫至少 8 個字的設備遺失／資料放棄原因：",
      "設備遺失且本地資料無法恢復",
    );
    if (!reason || !window.confirm("確認接管設備並審計作廢所有缺失序號？這些未上傳資料無法還原。")) return;
    const taskId = String(selectedId);
    setSessionBusy(true);
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/devices/"
        + encodeURIComponent(session.device_id) + "/abandon", {
          confirmed: true, reason,
          expected_last_sequence_reported: n(session.last_sequence_reported),
        });
      if (selectedIdRef.current !== taskId) return;
      applyDetail(data);
      setNotice({ tone: "ok", text: "遺失設備已安全關閉；" + n(apiData(data).voided_missing_count) + " 個缺失序號已逐號留痕，鎖單時仍需確認作廢總數。" });
    } catch (error) {
      if (selectedIdRef.current === taskId) setNotice({ tone: "bad", text: error.message || "遺失設備接管失敗。" });
    } finally { setSessionBusy(false); }
  };

  const reopenAllCapture = async () => {
    if (!selectedId || sessionBusy || finalized || !captureClosed || !canAdjust) return;
    const taskId = String(selectedId);
    setSessionBusy(true);
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/reopen", { confirmed: true });
      if (selectedIdRef.current !== taskId) return;
      applyDetail(data);
      setWorkMode("review");
      setNotice({ tone: "ok", text: "整單鎖定已解除；既有設備仍保持安全結束，只需在要補盤的那台設備按“本機續盤”。" });
    } catch (error) {
      if (selectedIdRef.current === taskId) setNotice({ tone: "bad", text: error.message || "無法重新開放整單採集。" });
    } finally { setSessionBusy(false); }
  };

  const switchMode = next => {
    if (next === "capture" && captureClosed) {
      setNotice({ tone: "bad", text: "整單採集已鎖定；需由負責人重新開放後才能繼續。" });
      return;
    }
    setWorkMode(next);
    if (next === "review" && workMode !== "review" && draftDirty && lines.length) classifyDraft();
    if (next === "capture") window.setTimeout(() => inputRef.current && inputRef.current.focus(), 80);
  };

  const saveLine = async (line, patch) => {
    if (!selectedId || !canCount || finalized || savingIds.has(String(line.id))) return;
    const taskId = String(selectedId);
    const id = String(line.id);
    const previous = line;
    setSavingIds(current => new Set([...current, id]));
    setLines(current => current.map(item => String(item.id) === id ? { ...item, ...patch } : item));
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/lines/" + encodeURIComponent(line.id), {
        version: line.version,
        ...patch,
      });
      if (selectedIdRef.current !== taskId) return;
      const response = apiData(data);
      const saved = normalizeLine(response.line || response.draft_line || response, 0);
      setLines(current => current.map(item => String(item.id) === id ? saved : item));
      if (response.summary) setSummaryRaw(current => ({ ...current, ...nested(response.summary) }));
    } catch (error) {
      if (selectedIdRef.current !== taskId) return;
      setLines(current => current.map(item => String(item.id) === id ? previous : item));
      if (error.status === 409) {
        setNotice({ tone: "bad", text: "此草稿行已被其他同事更新,已重新載入最新版本。" });
        loadDetail(selectedId, true);
      } else setNotice({ tone: "bad", text: error.message || "草稿保存失敗" });
    } finally {
      setSavingIds(current => { const next = new Set(current); next.delete(id); return next; });
    }
  };

  const mergePossibleDuplicate = async source => {
    if (!selectedId || !canAdjust || finalized) return;
    const candidates = lines.filter(line => String(line.id) !== String(source.id)
      && (line.status === "possible_duplicate" || (line.manual_override
        && line.match_method === "manual_merge"
        && ["ready", "recount_required"].includes(line.status)))
      && n(line.warehouse_id) === n(source.warehouse_id)
      && n(line.location_id) === n(source.location_id)
      && String(line.unit || "") === String(source.unit || "")
      && text(line.normalized_name || line.item_name) === text(source.normalized_name || source.item_name)
      && text(line.normalized_spec || line.spec_model) === text(source.normalized_spec || source.spec_model)
      && String(line.category_id || "") === String(source.category_id || ""));
    if (!candidates.length) {
      setNotice({ tone: "bad", text: "找不到同標準品名、規格、分類、庫位與單位的疑似重複行。" }); return;
    }
    let target = candidates[0];
    if (candidates.length > 1) {
      const answer = window.prompt("輸入要保留的目標行 ID：\n" + candidates.map(line =>
        "#" + line.id + " " + line.item_name + " · " + line.counted_quantity + line.unit).join("\n"), String(target.id));
      target = candidates.find(line => String(line.id) === String(answer));
      if (!target) return;
    } else if (!window.confirm("將 #" + source.id + "「" + source.item_name + "」的 "
      + source.counted_quantity + source.unit + " 合併到 #" + target.id + "「" + target.item_name + "」？")) return;
    const ids = [String(source.id), String(target.id)];
    setSavingIds(current => new Set([...current, ...ids]));
    try {
      await W2.post("/api/stocktake/" + encodeURIComponent(selectedId) + "/lines/"
        + encodeURIComponent(source.id) + "/merge", {
          target_line_id: target.id, source_version: source.version, target_version: target.version,
          confirmed: true,
        });
      await loadDetail(selectedId, true);
      setNotice({ tone: "ok", text: "疑似重複草稿已人工確認合併，數量與全部觀測證據均已保留。" });
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "草稿合併失敗。" });
      if (error.status === 409) loadDetail(selectedId, true);
    } finally {
      setSavingIds(current => { const next = new Set(current); ids.forEach(id => next.delete(id)); return next; });
    }
  };

  const excludeDraftLine = async line => {
    if (!selectedId || !canAdjust || finalized) return;
    const reason = window.prompt("請填寫排除原因（誤掃行不會進正式庫存，原始觀測仍保留）：", "現場確認為誤掃");
    if (!reason) return;
    const id = String(line.id);
    setSavingIds(current => new Set([...current, id]));
    try {
      await W2.post("/api/stocktake/" + encodeURIComponent(selectedId) + "/lines/"
        + encodeURIComponent(line.id) + "/exclude", { version: line.version, reason });
      await loadDetail(selectedId, true);
      setNotice({ tone: "ok", text: "誤掃草稿已排除並保留審計；若它屬於全庫既有物資，會重新出現在缺盤清單。" });
    } catch (error) {
      setNotice({ tone: "bad", text: error.message || "排除誤掃失敗。" });
      if (error.status === 409) loadDetail(selectedId, true);
    } finally {
      setSavingIds(current => { const next = new Set(current); next.delete(id); return next; });
    }
  };

  const summary = useMemo(() => {
    const totalUnits = lines.reduce((sum, line) => sum + n(line.counted_quantity), 0);
    const exact = lines.filter(line => /exact|barcode|sku|item/.test(line.match_method) && !line.exception).length;
    const ai = lines.filter(line => /ai/.test(line.match_method) && !line.exception).length;
    const lineExceptions = lines.filter(line => line.exception).length;
    const unresolved = n(summaryRaw.exception_count ?? summaryRaw.unresolved_count ?? summaryRaw.unresolved ?? summaryRaw.exceptions ?? lineExceptions);
    const missingExpected = n(summaryRaw.missing_expected_count);
    return {
      totalUnits: n(summaryRaw.total_units ?? summaryRaw.counted_units ?? summaryRaw.counted_quantity ?? totalUnits),
      lineCount: n(summaryRaw.line_count ?? summaryRaw.unique_skus ?? summaryRaw.unique_items ?? lines.length),
      exact: n(summaryRaw.exact_count ?? summaryRaw.exact_matched ?? exact),
      ai: n(summaryRaw.ai_count ?? summaryRaw.ai_matched ?? ai),
      expected: n(summaryRaw.expected_line_count),
      covered: n(summaryRaw.covered_line_count),
      missingExpected,
      exceptions: unresolved + missingExpected,
    };
  }, [lines, summaryRaw]);

  const locationById = useMemo(() => {
    const map = new Map();
    locations.forEach(location => map.set(String(location.id ?? location.location_id), location));
    return map;
  }, [locations]);
  const warehouseById = useMemo(() => {
    const map = new Map();
    warehouses.forEach(warehouse => map.set(String(warehouse.id ?? warehouse.warehouse_id), warehouse));
    return map;
  }, [warehouses]);
  const categoryById = useMemo(() => {
    const map = new Map();
    categories.forEach(category => map.set(String(category.id ?? category.category_id), category));
    return map;
  }, [categories]);

  const areaOf = line => {
    const location = locationById.get(String(line.location_id)) || {};
    const explicit = location.area || location.area_name || location.zone || location.zone_name || location.zone_code || line.area;
    if (explicit) return String(explicit);
    const code = line.location_code || location.location_code || location.code || "未分區";
    return String(code).split(/[-/]/)[0] || "未分區";
  };
  const groupLines = (type, getter) => {
    const map = new Map();
    lines.forEach(line => {
      const result = getter(line);
      const key = String(result.key == null || result.key === "" ? "__none__" : result.key);
      const old = map.get(key) || { key, label: result.label || "未分類", lines: 0, units: 0, exceptions: 0, type };
      old.lines += 1; old.units += n(line.counted_quantity); old.exceptions += line.exception ? 1 : 0;
      map.set(key, old);
    });
    return [...map.values()].sort((a, b) => b.lines - a.lines || b.units - a.units);
  };
  const warehouseGroups = useMemo(() => groupLines("warehouse", line => {
    const reference = warehouseById.get(String(line.warehouse_id)) || {};
    return { key: line.warehouse_id || "__none__", label: line.warehouse_name || reference.name || reference.warehouse_name || "未指定倉庫" };
  }), [lines, warehouseById]);
  const areaGroups = useMemo(() => groupLines("area", line => ({ key: areaOf(line), label: areaOf(line) })), [lines, locationById]);
  const categoryGroups = useMemo(() => groupLines("category", line => {
    const reference = categoryById.get(String(line.category_id)) || {};
    return { key: line.category_id || "__none__", label: line.category_name || reference.name || reference.category_name || "未分類" };
  }), [lines, categoryById]);

  const matchesTopology = line => {
    if (!topologyFilter) return true;
    if (topologyFilter.type === "warehouse") return String(line.warehouse_id || "__none__") === topologyFilter.key;
    if (topologyFilter.type === "category") return String(line.category_id || "__none__") === topologyFilter.key;
    if (topologyFilter.type === "area") return areaOf(line) === topologyFilter.key;
    return true;
  };
  const filteredLines = useMemo(() => {
    const query = search.trim().toLowerCase();
    return lines.filter(line => matchesTopology(line) && (!query || [line.item_name, line.spec_model, line.barcode, line.location_code, line.category_name]
      .some(value => String(value || "").toLowerCase().includes(query))));
  }, [lines, topologyFilter, search, locationById]);
  const linePageSize = 50;
  const linePageCount = Math.max(1, Math.ceil(filteredLines.length / linePageSize));
  const visibleLines = useMemo(() => filteredLines.slice(
    linePage * linePageSize, (linePage + 1) * linePageSize,
  ), [filteredLines, linePage]);
  useEffect(() => { setLinePage(0); }, [search, topologyFilter, selectedId]);
  useEffect(() => {
    if (linePage >= linePageCount) setLinePage(Math.max(0, linePageCount - 1));
  }, [linePage, linePageCount]);

  const selectTopology = group => setTopologyFilter(current => current && current.type === group.type && current.key === group.key ? null : { type: group.type, key: group.key, label: group.label });
  const topologyNodes = (groups, limit) => {
    const shown = groups.slice(0, limit);
    return <div className="stx-node-grid">{shown.map(group => {
      const active = topologyFilter && topologyFilter.type === group.type && topologyFilter.key === group.key;
      return <button type="button" key={group.type + group.key} className={"stx-node " + (active ? "on" : "")} onClick={() => selectTopology(group)}>
        <span className="stx-node-code">{group.type === "warehouse" ? "WH" : group.type === "area" ? "AR" : "CT"}</span>
        <strong>{group.label}</strong><span className="num">{group.lines} 種 · {group.units} 件</span>
        {group.exceptions > 0 && <em>{group.exceptions} 異常</em>}
      </button>;
    })}{groups.length > shown.length && <div className="stx-node stx-node-more"><strong>+{groups.length - shown.length}</strong><span>其餘分組<br/>可在草稿搜尋</span></div>}</div>;
  };

  const currentDraftVersion = task
    ? n(summaryRaw.draft_version ?? task.draft_version)
    : n(summaryRaw.draft_version);
  const taskMatchesDetail = !!(task && String(task.id) === String(selectedId));
  const openDeviceCount = n(summaryRaw.open_device_count);
  const unsyncedDeviceCount = n(summaryRaw.unsynced_device_count);
  const captureBarrierRequired = n(selectedTask && selectedTask.capture_protocol_version) >= 1
    || fullTask || n(summaryRaw.device_count) > 0;
  const captureBarrierReady = !captureBarrierRequired || (
    captureClosed && n(summaryRaw.device_count) > 0 && openDeviceCount === 0 && unsyncedDeviceCount === 0
  );
  const reviewReady = taskMatchesDetail && !finalized && !draftDirty && !classifyBusy
    && !sessionBusy && savingIds.size === 0 && pendingCaptureCount === 0 && failedCaptureCount === 0
    && captureBarrierReady
    && summary.exceptions === 0 && lines.length > 0;

  const commitDraft = async () => {
    if (!selectedId || commitBusy || !canAdjust || !reviewReady) return;
    const taskId = String(selectedId);
    if (!commitRequestRef.current) commitRequestRef.current = uuid("stocktake-commit-" + taskId);
    setCommitBusy(true); setNotice(null);
    try {
      const data = await W2.post("/api/stocktake/" + encodeURIComponent(taskId) + "/commit", {
        request_id: commitRequestRef.current, confirmed: true,
        draft_version: currentDraftVersion,
      });
      if (selectedIdRef.current !== taskId) return;
      const result = apiData(data);
      setCommitResult(result);
      setNotice({ tone: "ok", text: result.already_committed ? "此盤點單已安全入賬,沒有重複過賬。" : "整份盤點草稿已完成入賬並生成差異單。" });
      loadDetail(taskId, true);
    } catch (error) {
      if (selectedIdRef.current !== taskId) return;
      setNotice({ tone: "bad", text: error.message || (error.status === 409
        ? "盤點狀態或賬面快照已變更，請刷新草稿後再整單確認。"
        : "整單入賬失敗,可使用同一請求安全重試。") });
    } finally { setCommitBusy(false); }
  };

  const askStart = () => W2.openSecretary("發起一次盤點任務。請先追問全庫覆蓋(full)還是抽盤(spot)，並先查實際庫存規模再按規模給建議，不要假設庫存量。再確認任務名稱、倉庫/庫位範圍、負責人與計劃品類數後創建");

  return (<>
    <style>{`
      .stx-shell{border-top:2px solid var(--rule);background:var(--surface);}
      .stx-modebar{display:flex;align-items:stretch;border-bottom:1px solid var(--hair);background:var(--surface);}
      .stx-mode{min-height:58px;padding:0 22px;border:0;border-right:1px solid var(--hair);background:transparent;color:var(--ink);font:700 13px/1 var(--font);cursor:pointer;letter-spacing:.02em}
      .stx-mode.on{background:var(--ink);color:var(--paper)}
      .stx-mode-status{margin-left:auto;padding:12px 18px;display:flex;align-items:center;gap:10px;font-size:11px;color:var(--ink-3)}
      .stx-capture{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(250px,.65fr);gap:0;border-bottom:2px solid var(--rule)}
      .stx-capture-main{padding:24px;border-right:1px solid var(--hair)}
      .stx-capture-side{padding:24px;background:var(--surface-2)}
      .stx-kicker{font:700 10px/1 var(--mono);letter-spacing:.18em;color:var(--red);text-transform:uppercase}
      .stx-task-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0 20px}
      .stx-field{display:flex;flex-direction:column;gap:6px}.stx-field label{font:650 10px/1 var(--mono);letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}
      .stx-control,.stx-capture-input,.stx-qty,.stx-cell-input,.stx-cell-select{min-height:44px;border:1px solid var(--rule);border-radius:0;background:var(--surface);color:var(--ink);padding:0 11px;font:600 14px/1.2 var(--font);outline:none}
      .stx-control:focus,.stx-capture-input:focus,.stx-qty:focus,.stx-cell-input:focus,.stx-cell-select:focus{border-color:var(--red);box-shadow:inset 0 -2px 0 var(--red)}
      .stx-input-row{display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:8px}.stx-capture-input{height:58px;font-size:17px;padding:0 16px}
      .stx-big-action{min-width:58px;border:1px solid var(--rule);background:var(--ink);color:var(--paper);cursor:pointer}.stx-big-action.alt{background:var(--surface);color:var(--ink)}.stx-big-action.listening{background:var(--red);color:white}
      .stx-big-action:disabled{opacity:.45;cursor:not-allowed}
      .stx-amounts{display:grid;grid-template-columns:repeat(4,minmax(92px,1fr));gap:10px;margin-top:16px}.stx-qty{width:100%;font-size:16px}.stx-total{min-height:44px;display:flex;align-items:center;border-bottom:2px solid var(--rule);font:800 22px/1 var(--mono)}
      .stx-capture-note{margin-top:14px;font-size:11.5px;line-height:1.6;color:var(--ink-3)}
      .stx-notice{margin-top:12px;padding:10px 12px;border:1px solid var(--hair);display:flex;align-items:center;gap:9px;font-size:12px;line-height:1.45}.stx-notice.ok{border-color:var(--ok);color:var(--ok)}.stx-notice.bad{border-color:var(--red);color:var(--red)}
      .stx-sessionbar{margin-bottom:16px;padding:14px;border:2px solid var(--rule);display:flex;align-items:center;justify-content:space-between;gap:14px;background:var(--surface-2)}.stx-sessioncopy{display:flex;flex-direction:column;gap:5px}.stx-sessioncopy strong{font-size:14px}.stx-sessioncopy span{font-size:11px;line-height:1.5;color:var(--ink-3)}.stx-sessionactions{display:flex;gap:8px;flex-wrap:wrap}
      .stx-missing{margin-bottom:16px;border:2px solid var(--red);background:var(--surface)}.stx-missing-head{padding:13px 15px;border-bottom:1px solid var(--red);display:flex;justify-content:space-between;gap:12px}.stx-missing-row{padding:10px 15px;border-bottom:1px solid var(--hair);display:grid;grid-template-columns:minmax(180px,1fr) auto auto;align-items:center;gap:10px}.stx-missing-row:last-child{border-bottom:0}.stx-missing-row small{display:block;color:var(--ink-3);margin-top:3px}.stx-missing-actions{display:flex;gap:7px}
      .stx-failures{margin-top:10px;border:1px solid var(--red)}.stx-failure{padding:9px 11px;border-bottom:1px solid var(--hair);display:grid;grid-template-columns:1fr auto;gap:10px;align-items:center}.stx-failure:last-child{border-bottom:0}.stx-failure strong{display:block;font-size:11px;color:var(--red)}.stx-failure small{display:block;margin-top:3px;color:var(--ink-3)}.stx-failure-actions{display:flex;gap:6px}
      .stx-action-error{padding:14px;border:1px solid var(--red);color:var(--red);display:flex;align-items:flex-start;gap:10px;font-size:12px;line-height:1.55}
      .stx-live-count{font:800 clamp(42px,8vw,92px)/.9 var(--mono);letter-spacing:-.07em}.stx-live-label{margin-top:9px;font-size:12px;color:var(--ink-3)}
      .stx-side-rule{height:1px;background:var(--hair);margin:20px 0}.stx-side-list{display:grid;gap:9px}.stx-side-list div{display:flex;justify-content:space-between;font-size:12px}.stx-side-list b{font-family:var(--mono)}
      .stx-camera{margin-top:18px;border:2px solid var(--rule);background:var(--surface);padding:12px}.stx-camera-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}.stx-icon-button{width:40px;height:40px;border:1px solid var(--rule);background:var(--surface);font-size:25px;cursor:pointer}.stx-video-wrap{position:relative;aspect-ratio:16/9;background:#111;overflow:hidden}.stx-video-wrap video{width:100%;height:100%;object-fit:cover}.stx-scan-line{position:absolute;left:12%;right:12%;top:50%;height:2px;background:#ff3028;box-shadow:0 0 10px #ff3028}.stx-camera-status{min-height:38px;margin-top:9px;padding:0 10px;border:1px solid var(--hair);display:flex;align-items:center;justify-content:space-between;gap:10px;font-size:11px}.stx-camera-status b{font-family:var(--mono)}.stx-camera-status.queueing{border-color:var(--ink-3)}.stx-camera-status.accepted{border-color:var(--ok);color:var(--ok)}.stx-camera-status.retry{border-color:var(--red);color:var(--red)}.stx-camera-note{margin-top:9px;font-size:11px;line-height:1.55;color:var(--ink-3)}
      .stx-summary{display:grid;grid-template-columns:repeat(5,1fr);border:2px solid var(--rule);margin-bottom:18px}.stx-stat{min-height:112px;padding:15px;border-right:1px solid var(--hair);display:flex;flex-direction:column;justify-content:space-between}.stx-stat:last-child{border-right:0}.stx-stat span{font:650 10px/1.2 var(--mono);letter-spacing:.1em;color:var(--ink-3)}.stx-stat strong{font:800 30px/1 var(--mono)}.stx-stat.red strong{color:var(--red)}
      .stx-topology{display:grid;grid-template-columns:210px minmax(0,1fr);border:2px solid var(--rule);background:var(--surface);margin-bottom:18px}.stx-root{padding:18px;border-right:1px solid var(--rule);background:var(--ink);color:var(--paper);display:flex;flex-direction:column;justify-content:space-between;min-height:190px}.stx-root strong{font:800 32px/.95 var(--mono)}.stx-root span{font-size:11px;line-height:1.5;color:var(--ink-4)}
      .stx-topology-body{padding:14px;position:relative}.stx-topology-head{display:flex;justify-content:space-between;align-items:center;gap:10px;margin-bottom:12px}.stx-node-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(155px,1fr));gap:8px}.stx-node{min-height:88px;padding:11px;border:1px solid var(--rule);background:var(--surface);color:var(--ink);text-align:left;display:flex;flex-direction:column;gap:4px;cursor:pointer;position:relative}.stx-node:before{content:"";position:absolute;left:-9px;top:21px;width:8px;border-top:1px solid var(--rule)}.stx-node:hover,.stx-node.on{background:var(--ink);color:var(--paper)}.stx-node strong{font-size:13px}.stx-node .num{font-size:10px;opacity:.7}.stx-node em{font:700 9px/1 var(--mono);color:var(--red);font-style:normal}.stx-node-code{font:700 8px/1 var(--mono);letter-spacing:.12em;color:var(--red)}.stx-node-more{cursor:default;justify-content:center;align-items:center;text-align:center}.stx-node-more strong{font:800 24px/1 var(--mono)}
      .stx-review-actions{display:flex;gap:9px;align-items:center;flex-wrap:wrap;margin-bottom:14px}.stx-search{height:42px;min-width:240px;flex:1;border:1px solid var(--rule);background:var(--surface);padding:0 12px;color:var(--ink);font-size:14px}.stx-filter-chip{height:42px;border:1px solid var(--red);background:var(--surface);color:var(--red);padding:0 12px;cursor:pointer}
      .stx-table-wrap{overflow:auto;border-top:2px solid var(--rule);border-bottom:1px solid var(--rule)}.stx-table{border-collapse:collapse;width:100%;min-width:1180px}.stx-table th{height:42px;padding:0 8px;border-bottom:1px solid var(--rule);text-align:left;font:700 9px/1 var(--mono);letter-spacing:.1em;color:var(--ink-3);white-space:nowrap}.stx-table td{padding:8px;border-bottom:1px solid var(--hair);vertical-align:middle}.stx-table tr:last-child td{border-bottom:0}.stx-row-exception{background:color-mix(in srgb,var(--red) 5%,transparent)}.stx-cell-input,.stx-cell-select{width:100%;min-height:38px;padding:0 8px;font-size:13px;border-color:transparent;background:transparent}.stx-cell-input:hover,.stx-cell-select:hover{border-color:var(--hair)}.stx-cell-input:disabled,.stx-cell-select:disabled{opacity:.72}.stx-name{font-weight:700;min-width:160px}.stx-number{width:92px;font-family:var(--mono);font-size:16px}.stx-sub{font-size:9.5px;color:var(--ink-3);margin:3px 8px 0}.stx-diff{font-weight:800}.stx-diff[data-negative="1"]{color:var(--red)}
      .stx-pagination{min-height:48px;border-bottom:1px solid var(--rule);display:flex;align-items:center;justify-content:space-between;gap:10px;padding:7px 10px}.stx-pagination-actions{display:flex;align-items:center;gap:7px}
      .stx-commit{margin-top:20px;border:2px solid var(--rule);display:grid;grid-template-columns:minmax(0,1fr) auto;background:var(--surface)}.stx-commit-copy{padding:20px}.stx-commit-copy h3{margin:5px 0 8px;font-size:22px}.stx-commit-copy p{margin:0;color:var(--ink-3);font-size:12px;line-height:1.65}.stx-commit-button{min-width:250px;border:0;border-left:2px solid var(--rule);background:var(--red);color:white;padding:22px;font:800 17px/1.2 var(--font);cursor:pointer}.stx-commit-button:disabled{background:var(--ink-4);cursor:not-allowed}.stx-readonly{min-width:250px;padding:22px;border-left:2px solid var(--rule);display:flex;align-items:center;font-weight:750;background:var(--surface-2)}
      .stx-legacy-list{border-top:2px solid var(--rule)}.stx-legacy-diffs{margin-top:14px;border-top:1px solid var(--hair)}.stx-legacy-diffs>div{padding:9px 3px;border-bottom:1px solid var(--hair);font-size:12px}
      @media(max-width:760px){.stx-modebar{position:sticky;top:0;z-index:6}.stx-mode{padding:0 14px;flex:1}.stx-mode-status{display:none}.stx-capture{grid-template-columns:1fr}.stx-capture-main{padding:16px;border-right:0}.stx-capture-side{padding:18px;border-top:1px solid var(--rule)}.stx-task-row{grid-template-columns:1fr}.stx-input-row{grid-template-columns:minmax(0,1fr) 54px 54px}.stx-amounts{grid-template-columns:1fr 1fr}.stx-control,.stx-capture-input,.stx-qty,.stx-cell-input,.stx-cell-select,.stx-search{font-size:16px}.stx-summary{grid-template-columns:1fr 1fr}.stx-stat{min-height:92px}.stx-stat:nth-child(2n){border-right:0}.stx-stat:last-child{grid-column:1/-1;border-top:1px solid var(--hair)}.stx-sessionbar{align-items:stretch;flex-direction:column}.stx-sessionactions>*{flex:1}.stx-missing-row{grid-template-columns:1fr}.stx-missing-actions>*{flex:1}.stx-topology{grid-template-columns:1fr}.stx-root{min-height:112px;border-right:0;border-bottom:1px solid var(--rule)}.stx-root strong{font-size:28px}.stx-node-grid{display:flex;overflow-x:auto;padding-bottom:4px}.stx-node{min-width:160px}.stx-commit{grid-template-columns:1fr}.stx-commit-button,.stx-readonly{min-width:0;border-left:0;border-top:2px solid var(--rule);min-height:70px}.stx-review-actions .btn{min-height:44px}.stx-search{min-width:100%}}
    `}</style>

    <Folio no="06" en="AI STOCKTAKE" title={t("AI 批量自治盤庫")}
      sub={t("連續採集,不逐筆確認 · AI 整理全部草稿 · 最後整單入賬")}
      right={<><B icon="refresh" onClick={() => { loadTasks(); if (selectedId) loadDetail(selectedId, false); }}>刷新</B><B kind="primary" icon="clipboard" onClick={askStart}>發起盤點</B></>}/>

    <div className="stx-shell">
      <div className="stx-modebar">
        <button className={"stx-mode " + (workMode === "capture" ? "on" : "")} onClick={() => switchMode("capture")}>01 · {t("連續採集")}</button>
        <button className={"stx-mode " + (workMode === "review" ? "on" : "")} onClick={() => switchMode("review")}>02 · {t("草稿復核")} {lines.length ? "(" + lines.length + ")" : ""}</button>
        <div className="stx-mode-status"><span className="stx-kicker">ONE FINAL GATE</span><span>{t("正式庫存只會在最後一次整單確認後改變。")}</span></div>
      </div>

      {tasks.length > 0 && <div className="stx-task-row" style={{ padding: "16px 20px 0", margin: 0 }}>
        <div className="stx-field"><label>盤點任務 / TASK</label><select className="stx-control" value={selectedId} disabled={mutationBusy || captureBusy || registrationBusy || cameraOpen || voice.listening || voice.finalizing || !!repairCapture || !!expectedCapture} onChange={event => setSelectedId(event.target.value)}>{tasks.map(item => <option value={String(item.id)} key={item.key}>{item.task_no} · {item.name}</option>)}</select></div>
        <div className="stx-field"><label>目前狀態 / STATUS</label><div className="stx-control row spread"><span>{selectedTask ? selectedTask.area : "—"} · {selectedTask && selectedTask.task_mode === "full" ? "全库覆盖" : "抽盘"}</span><T tone={selectedTask && selectedTask.status === "done" ? "ok" : "inv"}>{selectedTask ? selectedTask.progress + "%" : "—"}</T></div></div>
      </div>}

      {loading && <div style={{ padding: 26 }} className="muted">正在載入盤庫草稿…</div>}
      {!loading && detailError && <div style={{ padding: 20 }}><div className="stx-action-error"><I name="alert" size={18}/><span>{detailError}。下方仍顯示既有任務與差異資料。</span></div></div>}

      {!loading && !detailError && selectedId && workMode === "capture" && !finalized && <div className="stx-capture">
        <section className="stx-capture-main" ref={captureFormRef}>
          <span className="stx-kicker">CAPTURE WITHOUT INTERRUPTION</span>
          <h2 style={{ margin: "8px 0 6px", fontSize: 25 }}>掃一次／說一次,直接進草稿</h2>
          <p className="stx-capture-note" style={{ marginTop: 0 }}>不要求逐筆分類或確認。AI 會在轉入草稿復核時,一次整理所有未解決的品種。</p>
          <div className="stx-task-row">
            <div className="stx-field"><label>庫位 / LOCATION</label><select className="stx-control" value={selectedLocation} onChange={event => setSelectedLocation(event.target.value)}><option value="">未指定（稍後 AI／人工整理）</option>{locations.map(location => <option key={location.id ?? location.location_id} value={location.id ?? location.location_id}>{location.location_code || location.code || location.name} · {location.warehouse_name || ""}</option>)}</select></div>
            <div className="stx-field"><label>基礎單位 / BASE UNIT</label><input className="stx-control" value={unit} onChange={event => { setUnit(event.target.value); setUnitTouched(true); }} inputMode="text"/></div>
          </div>
          <div className="stx-input-row">
            <input ref={inputRef} className="stx-capture-input" value={captureInput} autoComplete="off" autoCapitalize="off"
              placeholder={t("掃條碼、輸入編碼或名稱後按回車")} onChange={event => setCaptureInput(event.target.value)}
              onKeyDown={event => { if (event.key === "Enter") { event.preventDefault(); submitCapture(); } }}/>
            <button className="stx-big-action alt" type="button" title={t("開始掃碼")} disabled={!canCount || deviceClosed || captureClosed || sessionBusy || registrationBusy} onClick={() => { cameraCaptureContextRef.current = { taskId: String(selectedId), tenantSlug }; setCameraOpen(true); }}><I name="scan" size={23}/></button>
            <button className={"stx-big-action " + (voice.listening ? "listening" : "")} type="button" title={voice.listening ? t("停止錄音") : t("語音錄入")} disabled={!canCount || deviceClosed || captureClosed || sessionBusy || registrationBusy || voice.finalizing || voice.supported === false} onClick={() => { if (!voice.listening) voiceCaptureContextRef.current = { taskId: String(selectedId), tenantSlug }; voice.micClick(); }}><I name="mic" size={23}/></button>
          </div>
          {(voicePartial || voice.listening) && <div className="stx-notice"><span className="stx-kicker">VOICE</span><span>{voicePartial || "正在聆聽…說完後自動加入草稿"}</span></div>}
          {voice.error && <div className="stx-action-error" style={{ marginTop: 10 }}><I name="alert" size={18}/><span>{voice.error}</span></div>}
          <div className="stx-amounts">
            <div className="stx-field"><label>{t("直接數量")}</label><input ref={directQuantityRef} className="stx-qty" type="number" min="0" step="any" value={directQuantity} disabled={packageMode} onChange={event => { setDirectQuantity(event.target.value); setQuantityTouched(true); }}/></div>
            <div className="stx-field"><label>{t("箱／包數")}</label><input className="stx-qty" type="number" min="0" step="any" inputMode="decimal" value={packageCount} placeholder="0" onChange={event => { setPackageCount(event.target.value); setQuantityTouched(true); }}/></div>
            <div className="stx-field"><label>{t("每箱／包")}</label><input className="stx-qty" type="number" min="0" step="any" inputMode="decimal" value={unitsPerPackage} placeholder="0" onChange={event => { setUnitsPerPackage(event.target.value); setQuantityTouched(true); }}/></div>
            <div className="stx-field"><label>{t("散裝數")}</label><input className="stx-qty" type="number" min="0" step="any" inputMode="decimal" value={looseQuantity} placeholder="0" onChange={event => { setLooseQuantity(event.target.value); setQuantityTouched(true); }}/></div>
          </div>
          <div className="row spread" style={{ marginTop: 14, gap: 12, alignItems: "end" }}><div><span className="stx-kicker">{t("本次合計")}</span><div className="stx-total">{computedQuantity} {unit || "件"}</div></div><B kind="primary" icon="plus" disabled={!queueLockAvailable || !canCount || deviceClosed || captureClosed || sessionBusy || registrationBusy} onClick={() => submitCapture()}>{repairCapture ? "保存修正並繼續" : "加入草稿並繼續"}</B></div>
          {(captureBusy || pendingCaptureCount > 0 || failedCaptureCount > 0) && <div className="stx-notice" aria-live="polite"><I name="swap" size={17}/><span>{captureBusy ? "后台同步中 · " : ""}待同步 {pendingCaptureCount} · 失败 {failedCaptureCount}</span>{failedCaptureCount > 0 && <button type="button" className="tag redinv" onClick={retryFailedCaptures}>重新排队失败项</button>}</div>}
          {!queueLockAvailable && <div className="stx-action-error" style={{ marginTop: 10 }}><I name="alert" size={18}/><span>{deviceId ? "此瀏覽器缺少安全離線佇列鎖，系統不會登記設備或接收採集。請升級 Safari／Chrome 後再開始。" : "瀏覽器無法持久保存設備身份，系統不會登記臨時設備。請退出隱私模式或釋放網站儲存空間。"}</span></div>}
          {repairCapture && <div className="stx-notice bad"><I name="alert" size={17}/><span>修正序號 {n(repairCapture.event.device_sequence)}：請修改上方資料，再保存修正。</span><button type="button" className="tag" onClick={() => setRepairCapture(null)}>取消</button></div>}
          {expectedCapture && <div className="stx-notice"><I name="clipboard" size={17}/><span>正在清點既有物資「{expectedCapture.item_name}」；本次數量會綁定到指定倉庫／庫位。</span><button type="button" className="tag" onClick={() => setExpectedCapture(null)}>取消</button></div>}
          {selectedCaptureFailures.length > 0 && <div className="stx-failures">{selectedCaptureFailures.slice(0, 12).map(entry => {
            const acceptedConflict = entry.error_code === "sequence_already_accepted"
              || entry.error_code === "device_sequence_already_accepted";
            return <div className="stx-failure" key={entry.event.client_event_id}><div><strong>序號 {n(entry.event.device_sequence)} · {entry.error || "校驗失敗"}</strong><small>{entry.event.barcode || entry.event.raw_text || entry.event.item_name || "未命名採集"} · {present(entry.event.quantity) ? entry.event.quantity : "未解析"} {entry.event.unit || "自動單位"}</small></div><div className="stx-failure-actions">{acceptedConflict ? <B onClick={() => resolveAcceptedSequenceConflict(entry)}>{entry.error_code === "device_sequence_already_accepted" ? "重新編號入隊" : "清除已入賬副本"}</B> : <><B onClick={() => beginRepairCapture(entry)}>載入修正</B><B onClick={() => voidFailedCapture(entry)}>審計作廢</B></>}</div></div>;
          })}</div>}
          {notice && <div className={"stx-notice " + notice.tone} aria-live="polite"><I name={notice.tone === "ok" ? "checkCircle" : "alert"} size={17}/><span>{notice.text}</span></div>}
          {cameraOpen && (
            <CameraScanner onClose={() => setCameraOpen(false)} onDetect={code => {
              const context = cameraCaptureContextRef.current || {};
              setCaptureInput(code);
              return captureRef.current && captureRef.current({ value: code, captureType: "barcode",
                taskId: context.taskId, captureTenant: context.tenantSlug });
            }}/>
          )}
        </section>
        <aside className="stx-capture-side"><span className="stx-kicker">LIVE DRAFT</span><div className="stx-live-count">{summary.totalUnits}</div><div className="stx-live-label">已採集總件數 · {summary.lineCount} 個品種草稿</div><div className="stx-side-rule"/><div className="stx-side-list"><div><span>{t("精確匹配")}</span><b>{summary.exact}</b></div><div><span>{t("AI 匹配")}</span><b>{summary.ai}</b></div>{summary.expected > 0 && <div><span>全庫覆蓋</span><b>{summary.covered}/{summary.expected}</b></div>}<div><span>本機序號</span><b>{deviceSequenceForTask(selectedId)}</b></div><div><span>{t("異常")}</span><b style={{ color: summary.exceptions ? "var(--red)" : "var(--ok)" }}>{summary.exceptions}</b></div></div><div className="stx-side-rule"/><p className="stx-capture-note">同一物資重複出現會合併到品種草稿；本機採集按連續序號同步，服務器確認無缺號後才可結束。首次錄入會先在線登記，之後斷網仍可連續採集。</p>{deviceClosed ? <B style={{ width: "100%", marginTop: 12 }} icon="refresh" disabled={sessionBusy || captureClosed} onClick={reopenDeviceCapture}>本機繼續採集</B> : <B style={{ width: "100%", marginTop: 12 }} icon="arrow" disabled={sessionBusy || captureBusy || registrationBusy || cameraOpen || voice.listening || voice.finalizing || pendingCaptureCount > 0 || failedCaptureCount > 0} onClick={finishDeviceCapture}>{registrationBusy ? "登記設備中…" : sessionBusy ? "核對序號中…" : "本機完成採集並復核"}</B>}</aside>
      </div>}

      {!loading && !detailError && selectedId && workMode === "review" && <div style={{ padding: "20px" }}>
        {captureBarrierRequired && <div className="stx-sessionbar"><div className="stx-sessioncopy"><span className="stx-kicker">MULTI-DEVICE CAPTURE BARRIER</span><strong>{captureClosed ? "整單採集已鎖定" : "等待所有採集設備安全收尾"}</strong><span>設備 {n(summaryRaw.device_count)} 台 · 未結束 {openDeviceCount} 台 · 未同步 {unsyncedDeviceCount} 台。{captureClosed ? "任何設備都不能再追加，現在可完成集中復核。" : "每台先按“本機完成采集”，全部归零后由负责人锁定。"}</span></div><div className="stx-sessionactions">{currentDeviceSession && !deviceClosed && !captureClosed && <B icon="checkCircle" disabled={sessionBusy || registrationBusy || cameraOpen || voice.listening || voice.finalizing || pendingCaptureCount > 0 || failedCaptureCount > 0} onClick={finishDeviceCapture}>本機結束</B>}{currentDeviceSession && deviceClosed && !captureClosed && <B icon="refresh" disabled={sessionBusy} onClick={reopenDeviceCapture}>本機續盤</B>}{canAdjust && !captureClosed && <B kind="primary" icon="shield" disabled={sessionBusy || openDeviceCount > 0 || unsyncedDeviceCount > 0 || n(summaryRaw.device_count) === 0} onClick={closeAllCapture}>{sessionBusy ? "鎖定中…" : "鎖定全部採集"}</B>}{canAdjust && captureClosed && !finalized && <B icon="refresh" disabled={sessionBusy} onClick={reopenAllCapture}>重新開放採集</B>}</div></div>}
        {!captureClosed && captureSessions.some(session => session.status !== "closed" || !session.synced) && <div className="stx-missing"><div className="stx-missing-head"><div><span className="stx-kicker">BLOCKING DEVICES</span><strong style={{ display: "block", marginTop: 4 }}>尚未收尾的採集設備</strong></div><span className="muted">定位到人與序號缺口</span></div>{captureSessions.filter(session => session.status !== "closed" || !session.synced).map(session => <div className="stx-missing-row" key={session.id}><div><strong>{session.opened_by || "未知盤點員"} · {String(session.device_id).slice(0, 14)}…</strong><small>已到達 {n(session.last_sequence_received)} / 已上報 {n(session.last_sequence_reported)} · 待同步 {n(session.pending_sequence_count)} · {session.status === "closed" ? "已結束" : "未結束"}</small></div><T tone={session.synced ? "warn" : "bad"}>{session.synced ? "待本人結束" : "有缺口"}</T><div className="stx-missing-actions">{String(session.device_id) === deviceId ? <><B onClick={finishDeviceCapture}>本機收尾</B>{canAdjust && n(session.pending_sequence_count) > 0 && <B onClick={() => abandonLostDevice(session)}>本機資料已遺失</B>}</> : canAdjust ? <B onClick={() => abandonLostDevice(session)}>接管遺失設備</B> : <span className="muted">請聯繫原盤點員</span>}</div></div>)}</div>}
        {rejectedSequences.length > 0 && <div className="stx-missing"><div className="stx-missing-head"><div><span className="stx-kicker">REJECTED / VOID AUDIT</span><strong style={{ display: "block", marginTop: 4 }}>失敗待處理 {n(summaryRaw.rejected_sequence_count)} · 已作廢 {n(summaryRaw.voided_sequence_count)}</strong></div><span className="muted">{summaryRaw.rejected_sequence_list_truncated ? "項目較多，先顯示待處理與前 200 筆；處理後刷新" : "主管鎖單前逐筆可見"}</span></div>{rejectedSequences.map(row => {
          const event = row.event || {};
          const ownDevice = String(row.device_id) === deviceId;
          return <div className="stx-missing-row" key={row.id}><div><strong>{row.status === "voided" ? "已作廢" : "待處理"} · 設備序號 {row.device_sequence}</strong><small>{event.barcode || event.raw_text || event.item_name || row.client_event_id} · {row.status === "voided" ? (row.void_reason + " · " + (row.voided_by || "—") + " · " + (row.voided_at || "")) : row.error}</small></div><span className="mono">{String(row.device_id || "").slice(0, 14)}…</span><div className="stx-missing-actions">{row.status === "rejected" && ownDevice ? <><B onClick={() => beginRepairCapture(row)}>載入修正</B><B onClick={() => voidFailedCapture(row)}>審計作廢</B></> : row.status === "rejected" && canAdjust ? <B onClick={() => voidFailedCapture(row)}>主管審計作廢</B> : <T tone={row.status === "voided" ? "ok" : "warn"}>{row.status === "voided" ? "已留痕" : "等待原設備"}</T>}</div></div>;
        })}</div>}
        {missingExpected.length > 0 && <div className="stx-missing"><div className="stx-missing-head"><div><span className="stx-kicker">CENTRALIZED COVERAGE EXCEPTIONS</span><strong style={{ display: "block", marginTop: 4 }}>尚缺 {summary.missingExpected} 個既有物資／庫位</strong></div><span className="muted">只集中處理這些例外</span></div>{missingExpected.map(expected => <div className="stx-missing-row" key={expected.id}><div><strong>{expected.item_name}</strong><small>{expected.spec_model || "無規格"} · {expected.warehouse_name || "未指定倉庫"} / {expected.location_code || "整倉"} · 賬面 {n(expected.book_quantity_snapshot)} {expected.unit || "件"}</small></div><span className="num">#{expected.item_id}</span><div className="stx-missing-actions"><B onClick={() => locateMissingCapture(expected)}>去清點</B><B kind="primary" disabled={!canCount || captureClosed || sessionBusy} onClick={() => captureMissingAsZero(expected)}>確認實盤 0</B></div></div>)}</div>}
        <div className="stx-summary">
          {[ ["總件數", summary.totalUnits], ["品種／草稿行", summary.lineCount], ["精確匹配", summary.exact], ["AI 匹配", summary.ai], ["異常", summary.exceptions] ].map(([label, value], index) => <div className={"stx-stat " + (index === 4 && value ? "red" : "")} key={label}><span>{t(label)}</span><strong>{value}</strong></div>)}
        </div>
        <div className="stx-topology"><div className="stx-root"><span className="stx-kicker">STOCKTAKE TOPOLOGY</span><strong>{summary.lineCount}<br/>SKUs</strong><span>{selectedTask ? selectedTask.name : "盤庫草稿"}<br/>{summary.totalUnits} 件 · {summary.exceptions} 異常</span></div><div className="stx-topology-body"><div className="stx-topology-head"><div><span className="stx-kicker">SWISS TOPOLOGY</span><div style={{ fontWeight: 750, marginTop: 4 }}>{topologyMode === "location" ? t("庫位拓撲") : t("分類拓撲")}</div></div><div className="seg"><button className={topologyMode === "location" ? "on" : ""} onClick={() => { setTopologyMode("location"); setTopologyFilter(null); }}>庫位</button><button className={topologyMode === "category" ? "on" : ""} onClick={() => { setTopologyMode("category"); setTopologyFilter(null); }}>分類</button></div></div>{topologyMode === "location" ? <><div className="stx-kicker" style={{ margin: "8px 0" }}>WAREHOUSE</div>{topologyNodes(warehouseGroups, 8)}<div className="stx-kicker" style={{ margin: "14px 0 8px" }}>AREA</div>{topologyNodes(areaGroups, 10)}</> : topologyNodes(categoryGroups, 14)}</div></div>
        <div className="stx-review-actions"><input className="stx-search" value={search} onChange={event => setSearch(event.target.value)} placeholder="搜尋物資、條碼、規格、分類或庫位"/>{topologyFilter && <button className="stx-filter-chip" onClick={() => setTopologyFilter(null)}>× {topologyFilter.label}</button>}<B kind="primary" icon="sparkle" disabled={classifyBusy || !lines.length || finalized} onClick={classifyDraft}>{classifyBusy ? t("批量整理中") : t("AI 整理全部草稿")}</B></div>
        {classifyError && <div className="stx-action-error" style={{ marginBottom: 12 }}><I name="alert" size={18}/><span>{classifyError}</span><button className="tag redinv" onClick={classifyDraft}>重試</button></div>}
        {notice && <div className={"stx-notice " + notice.tone} style={{ marginBottom: 12 }}><I name={notice.tone === "ok" ? "checkCircle" : "alert"} size={17}/><span>{notice.text}</span></div>}
        {visibleLines.length ? (
          <><div className="stx-table-wrap"><table className="stx-table"><thead><tr><th>#</th><th>物資</th><th>規格／型號</th><th>AI 分類</th><th>庫位</th><th>實盤數</th><th>單位</th><th>賬面</th><th>差異</th><th>匹配</th></tr></thead><tbody>{visibleLines.map((line, index) => <DraftRow key={line.key + ":" + line.version} line={line} index={linePage * linePageSize + index} categories={categories} warehouses={warehouses} locations={locations} canCount={canCount && !finalized} canReview={canAdjust && !finalized} saving={savingIds.has(String(line.id))} onSave={saveLine} onMerge={mergePossibleDuplicate} onExclude={excludeDraftLine}/>)}</tbody></table></div>{filteredLines.length > linePageSize && <div className="stx-pagination"><span className="muted">顯示 {linePage * linePageSize + 1}–{Math.min(filteredLines.length, (linePage + 1) * linePageSize)} / {filteredLines.length} 個品種</span><div className="stx-pagination-actions"><B disabled={linePage <= 0} onClick={() => setLinePage(page => Math.max(0, page - 1))}>上一頁</B><span className="mono">{linePage + 1}/{linePageCount}</span><B disabled={linePage + 1 >= linePageCount} onClick={() => setLinePage(page => Math.min(linePageCount - 1, page + 1))}>下一頁</B></div></div>}</>
        ) : (
          <EM icon="search" title={t("沒有需要顯示的草稿行")} sub={lines.length ? "清除拓撲篩選或搜尋條件後重試。" : "回到連續採集,掃描或說出第一種物資。"}/>
        )}
        <div className="stx-commit"><div className="stx-commit-copy"><span className="stx-kicker">FINAL DETERMINISTIC GATE</span><h3>{summary.lineCount} 個品種 · {summary.totalUnits} 件 · {summary.exceptions} 項異常</h3><p>{t("正式庫存只會在最後一次整單確認後改變。")} AI 可自主建立和整理全部草稿；入賬時系統按實盤數與賬面快照確定性計算差異,並保留完整審計記錄。{summary.missingExpected > 0 ? " 全庫模式仍缺 " + summary.missingExpected + " 個既有物資／庫位。" : ""}{captureBarrierRequired && !captureClosed ? " 需先让每台设备结束同步，再锁定全部采集。" : ""}</p>{(commitResult || finalized) && <T tone="ok" dot>已入賬 · {(commitResult && (commitResult.document_no || commitResult.document_id)) || selectedTask.committed_document_id || "完成"}</T>}</div>{finalized ? <div className="stx-readonly"><I name="checkCircle" size={20}/><span style={{ marginLeft: 9 }}>本單已完成，草稿只讀</span></div> : canAdjust ? <button className="stx-commit-button" disabled={commitBusy || !reviewReady || !!commitResult} onClick={commitDraft}>{commitBusy ? "整單入賬中…" : commitResult ? "本單已完成入賬" : captureBarrierRequired && !captureClosed ? "请先锁定全部采集" : !captureBarrierReady ? "仍有设备未同步结束" : draftDirty ? "请先让 AI 整理最新草稿" : summary.missingExpected ? "全库覆盖尚未完成" : summary.exceptions ? "请先处理全部异常" : t("整單確認入賬")}</button> : <div className="stx-readonly"><I name="shield" size={20}/><span style={{ marginLeft: 9 }}>{t("等待負責人整單確認")}</span></div>}</div>
      </div>}
    </div>

    {(!selectedId || detailError) && (
      <LegacyFallback tasks={tasks.length ? tasks : legacyTasks} diffs={legacyDiffs} onStart={askStart}/>
    )}
  </>);
};

window.W2.PAGES.stocktake = Page;
})();
