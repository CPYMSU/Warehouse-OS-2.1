/* ============================================================
   Company AI Secretary - one AI entry for the whole app
   ============================================================ */

const AGENT_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const AGENT_PAGE_CATEGORY = {
  hardware: "hardware_material",
  safety: "safety_tool",
  maintenance: "maintenance_tool",
};

const AGENT_MODULES = {
  hardware: "金具材料",
  safety: "安全工器具",
  maintenance: "檢修工器具",
  overview: "倉儲總覽",
  inventory: "庫存管理",
  inbound: "入庫管理",
  outbound: "出庫領用",
  alerts: "智能預警",
  stocktake: "盤點管理",
  map: "庫位地圖",
  erp: "ERP 中樞",
  finance: "AI 財務",
  assets: "資產管理",
  ai: "AI",
  collab: "AI 協作",
  procurement: "招采工作流",
  reports: "報表中心",
  logs: "審計日誌",
  perms: "權限管理",
  settings: "系統設置",
  companies: "公司管理",
  "platform-console": "運營後台",
};

const AGENT_STORAGE = {
  conversation: "warehouse.agent.conversationId",
};

// P1 助理綁賬號:對話 id 按「租戶 + 賬號」分開存,換賬號/換公司不串對話
const agentConvKey = () => {
  const uid = (window.CURRENT_USER && window.CURRENT_USER.id) || "anon";
  const slug = window.localStorage.getItem("warehouse_current_tenant") || "uhv";
  return `${AGENT_STORAGE.conversation}.${slug}.${uid}`;
};
const readStoredConversation = () => Number(localStorage.getItem(agentConvKey())) || null;

const AGENT_OPEN_EVENT = "company-secretary-open";
const LEGACY_AGENT_OPEN_EVENT = "warehouse-agent-open";

async function agentJson(path, options) {
  const apiFetch = window.authFetch || fetch;
  const res = await apiFetch(AGENT_API_BASE + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

// P4:秘書面板直連 AI 內核(與平臺終端同一 /api/agent/run/stream,NDJSON 逐事件)
async function agentRunStream(body, onEvent, options = {}) {
  const apiFetch = window.authFetch || fetch;
  const res = await apiFetch(AGENT_API_BASE + "/api/agent/run/stream", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal: options.signal,
  });
  if (!res.ok || !res.body) {
    let msg = res.statusText;
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, idx).trim();
      buf = buf.slice(idx + 1);
      if (!line) continue;
      try { onEvent(JSON.parse(line)); } catch (e) {}
    }
  }
}
window.agentRunStream = agentRunStream;

// 統一秘書:把舊「只聊天不執行」的 /api/ai/chat 頁面也接到內核 /api/agent/run/stream(真的調指令、寫庫、寫審計)。
// handlers.onStep(ev, phase) 可即時顯示正在執行的指令;回傳兼容舊頁面的 {conversation_id, answer, steps}。
async function agentRunCompat(body, handlers = {}) {
  let conversationId = (body && body.conversation_id) || null;
  const steps = [];
  let finalMessage = "";
  await agentRunStream({ text: body.text, conversation_id: conversationId }, (ev) => {
    const name = ev.event;
    if (name === "run_start") {
      conversationId = ev.conversation_id || conversationId;
      handlers.onStart && handlers.onStart(ev);
    } else if (name === "step_start") {
      handlers.onStep && handlers.onStep(ev, "start");
    } else if (name === "step") {
      steps.push(ev);
      handlers.onStep && handlers.onStep(ev, "done");
    } else if (name === "final") {
      finalMessage = ev.message || (ev.payload && ev.payload.message) || "";
      handlers.onFinal && handlers.onFinal(ev);
    }
  });
  return { conversation_id: conversationId, answer: finalMessage, steps };
}
window.agentRunCompat = agentRunCompat;

async function aiStreamJson(apiBase, path, options = {}, handlers = {}) {
  if (!window.TextDecoder) throw new Error("streaming is not supported by this browser");
  const apiFetch = window.authFetch || fetch;
  const res = await apiFetch(apiBase + path, options);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let message = text || res.statusText;
    try {
      const data = JSON.parse(text);
      message = data.error || message;
    } catch {}
    throw new Error(message);
  }
  if (!res.body || !res.body.getReader) throw new Error("streaming response is not readable");
  const reader = res.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";
  let finalPayload = null;
  let streamError = "";
  const handleLine = (line) => {
    if (!line.trim()) return;
    const event = JSON.parse(line);
    handlers.onEvent?.(event);
    if (event.event === "delta") handlers.onDelta?.(event.text || "", event);
    if (event.event === "status") handlers.onStatus?.(event.message || "", event);
    if (event.event === "meta") handlers.onMeta?.(event);
    if (event.event === "final") {
      finalPayload = event.payload || event.data || event;
      handlers.onFinal?.(finalPayload, event);
    }
    if (event.event === "error") streamError = event.error || "stream failed";
  };
  while (true) {
    const { value, done } = await reader.read();
    if (value) {
      buffer += decoder.decode(value, { stream: !done });
      const lines = buffer.split(/\r?\n/);
      buffer = lines.pop() || "";
      lines.forEach(handleLine);
    }
    if (done) break;
  }
  buffer += decoder.decode();
  if (buffer.trim()) handleLine(buffer);
  if (streamError) throw new Error(streamError);
  return finalPayload;
}

window.aiStreamJson = aiStreamJson;

/* ============================================================
   秘書語音對話 Hook:雲端(/api/voice/*,真人感)→ 瀏覽器原生兜底
   - micClick:點一下說話、再點結束 → 轉寫文本直接發給秘書
   - mode(語音對話):回覆自動朗讀,朗讀完自動再聆聽
   ============================================================ */
function useAgentVoice(onTranscript, onPartial) {
  const [listening, setListening] = React.useState(false);
  const [mode, setMode] = React.useState(false);
  const st = React.useRef({ cloud: false, recorder: null, recog: null, audio: null, stopTimer: null, lastVoice: false, mode: false, listenFn: null, listening_: false, gen: 0, partialBusy: false });
  const apiFetch = window.authFetch || fetch;

  React.useEffect(() => {
    apiFetch(AGENT_API_BASE + "/api/voice/status").then(r => r.json())
      .then(d => { st.current.cloud = !!(d.configured && d.asr); }).catch(() => {});
    if (window.speechSynthesis) speechSynthesis.getVoices();
  }, []);

  const trim = (text) => {
    let t = (text || "")
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
    if (t.length > 280) {
      const cut = t.slice(0, 280);
      const pos = Math.max(cut.lastIndexOf("。"), cut.lastIndexOf("!"), cut.lastIndexOf("?"), cut.lastIndexOf("!"));
      t = pos > 80 ? cut.slice(0, pos + 1) : cut;
    }
    return t;
  };
  const zhVoice = () => {
    const vs = window.speechSynthesis ? speechSynthesis.getVoices() : [];
    return vs.find(v => /xiaoxiao|曉|晓/i.test(v.name) && /natural|online/i.test(v.name))
        || vs.find(v => /^zh/i.test(v.lang) && /natural|online/i.test(v.name))
        || vs.find(v => /^zh/i.test(v.lang)) || null;
  };
  const loopNext = () => {
    const again = st.current.mode;
    st.current.lastVoice = false;
    if (again) setTimeout(() => st.current.listenFn && st.current.listenFn(), 350);
  };
  // Barge-in:朗讀時輕量監聽(AEC+0.35s 門檻),用戶插話 → 掐斷朗讀轉聆聽
  const armBargeIn = async (gen) => {
    if (!st.current.mode || !navigator.mediaDevices) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const ac = new (window.AudioContext || window.webkitAudioContext)();
      const an = ac.createAnalyser();
      an.fftSize = 256;
      ac.createMediaStreamSource(stream).connect(an);
      const buf = new Uint8Array(an.frequencyBinCount);
      let aboveMs = 0, last = Date.now();
      const cleanup = () => { stream.getTracks().forEach(t => t.stop()); try { ac.close(); } catch (e) {} };
      const tick = () => {
        if (st.current.gen !== gen || !st.current.speaking) { cleanup(); return; }
        an.getByteFrequencyData(buf);
        let s = 0;
        for (let i = 0; i < buf.length; i++) s += buf[i];
        const now = Date.now();
        if (s / buf.length > 24) aboveMs += now - last; else aboveMs = Math.max(0, aboveMs - (now - last) * 2);
        last = now;
        if (aboveMs > 350) {
          cleanup();
          st.current.speaking = false;
          if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
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
    const clean = trim(text);
    if (!clean) { loopNext(); return; }
    const gen = ++st.current.gen;
    st.current.speaking = true;
    armBargeIn(gen);
    const done = () => { if (st.current.gen === gen) { st.current.speaking = false; loopNext(); } };
    try {
      if (st.current.cloud) {
        const res = await apiFetch(AGENT_API_BASE + "/api/voice/speak", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text: clean }),
        });
        if (res.ok) {
          if (st.current.gen !== gen || !st.current.speaking) return;  // 已被打斷
          const url = URL.createObjectURL(await res.blob());
          st.current.audio = new Audio(url);
          st.current.audio.onended = () => { URL.revokeObjectURL(url); done(); };
          st.current.audio.onerror = () => { URL.revokeObjectURL(url); done(); };
          await st.current.audio.play();
          return;
        }
      }
    } catch (e) {}
    if (st.current.gen !== gen || !st.current.speaking) return;
    if ("speechSynthesis" in window) {
      const u = new SpeechSynthesisUtterance(clean);
      const v = zhVoice();
      if (v) { u.voice = v; u.lang = v.lang; } else u.lang = "zh-TW";
      u.rate = 1.05;
      u.onend = done;
      u.onerror = done;
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
    } else done();
  };
  const stop = () => {
    clearTimeout(st.current.stopTimer);
    if (st.current.recorder && st.current.recorder.state !== "inactive") { try { st.current.recorder.stop(); } catch (e) {} }
    if (st.current.recog) { try { st.current.recog.stop(); } catch (e) {} }
  };
  const listen = async () => {
    if (st.current.listening_) return;
    if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
    if (window.speechSynthesis) speechSynthesis.cancel();
    const mark = (on) => { st.current.listening_ = on; setListening(on); };
    if (st.current.cloud && navigator.mediaDevices && window.MediaRecorder) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const gen = ++st.current.gen;
        const mime = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : (MediaRecorder.isTypeSupported("audio/mp4") ? "audio/mp4" : "");
        const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
        const chunks = [];
        let lastPartialAt = 0;
        st.current.partialBusy = false;
        // 流式體驗:1s 切片累積,每 ~2.2s 部分識別上屏;停止後完整定稿
        const transcribe = async (isFinal) => {
          if (!isFinal && (st.current.partialBusy || !chunks.length)) return;
          const blob = new Blob(chunks, { type: mime || "audio/webm" });
          if (blob.size < 2500) { if (isFinal) loopNext(); return; }  // 太短(沒說話)→ 連續模式繼續聽
          st.current.partialBusy = true;
          try {
            const res = await apiFetch(AGENT_API_BASE + "/api/voice/transcribe?lang=zh" + (isFinal ? "&correct=1" : ""), {
              method: "POST", headers: { "Content-Type": blob.type }, body: blob,
            });
            const d = await res.json().catch(() => ({}));
            if (st.current.gen !== gen) return;
            if (d.ok && d.text) {
              if (isFinal) { st.current.lastVoice = true; onTranscript(d.text); }
              else if (onPartial) onPartial(d.text + " …");
            } else if (isFinal) { loopNext(); }   // 沒識別到內容 → 繼續聽,不卡死
          } catch (e) { if (isFinal) loopNext(); }  // 識別出錯 → 繼續聽
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
        // VAD 端點:說過話之後持續靜音 ~1.1s → 自動停止並發送(零點擊)
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
              else if (now - silenceSince > 2300) { stop(); return; }  // 2.3s 靜音才算說完,容忍說話中的自然停頓
            } else silenceSince = 0;
            vraf = requestAnimationFrame(pump);
          };
          vraf = requestAnimationFrame(pump);
        } catch (e) {}
        rec.onstop = () => {
          stream.getTracks().forEach(t => t.stop());
          if (vraf) cancelAnimationFrame(vraf);
          if (vac) { try { vac.close(); } catch (e) {} }
          clearTimeout(st.current.stopTimer);
          mark(false);
          const waitIdle = () => st.current.partialBusy ? setTimeout(waitIdle, 120) : transcribe(true);
          waitIdle();
        };
        st.current.recorder = rec;
        rec.start(1000);
        if (onPartial) onPartial("");
        mark(true);
        st.current.stopTimer = setTimeout(stop, 30000);
        return;
      } catch (e) { return; }
    }
    const R = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!R) return;
    const r = new R();
    r.lang = "zh-CN";
    r.interimResults = true;  // 原生識別也流式上屏
    r.onresult = (e) => {
      let interim = "", final = "";
      for (const res of e.results) (res.isFinal ? (final += res[0].transcript) : (interim += res[0].transcript));
      if (interim && onPartial) onPartial(interim + " …");
      if (final.trim()) { st.current.lastVoice = true; onTranscript(final.trim()); }
    };
    r.onend = () => mark(false);
    r.onerror = () => mark(false);
    st.current.recog = r;
    r.start();
    mark(true);
  };
  st.current.listenFn = listen;
  const micClick = () => st.current.listening_ ? stop() : listen();
  const toggleMode = () => {
    const next = !st.current.mode;
    st.current.mode = next;
    setMode(next);
    if (next) listen();
    else { stop(); if (window.speechSynthesis) speechSynthesis.cancel(); if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} } }
  };
  const shutdown = () => {
    st.current.mode = false;
    st.current.lastVoice = false;
    st.current.speaking = false;
    ++st.current.gen;
    setMode(false);
    if (st.current.recog) {
      st.current.recog.onresult = null;
      try { st.current.recog.abort(); } catch (e) {}
    }
    stop();
    st.current.listening_ = false;
    setListening(false);
    if (window.speechSynthesis) speechSynthesis.cancel();
    if (st.current.audio) { try { st.current.audio.pause(); } catch (e) {} }
  };
  return { listening, mode, micClick, toggleMode, speakReply, shutdown };
}

const AgentMicIcon = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>
  </svg>
);

function inferAgentCategory(page) {
  // 物資台賬頁 id 形如 "ledger:<分類id>",直接取分類 id
  if (page && page.indexOf("ledger:") === 0) return page.slice("ledger:".length);
  return AGENT_PAGE_CATEGORY[page] || null;
}

function agentModuleLabel(page) {
  if (page && page.indexOf("ledger:") === 0) {
    const cat = (window.LEDGER_CATEGORIES || []).find(c => c.id === page.slice("ledger:".length));
    return cat ? cat.name : "庫存";
  }
  return AGENT_MODULES[page] || "業務模組";
}

function agentFieldValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

const AgentCard = ({ card, actionRequest, onConfirm, onCancel, busy }) => {
  if (!card) return null;
  const type = card.card_type || "result";
  const requestId = card.action_request_id || actionRequest?.id;
  const tone = type === "confirmation" ? "var(--warn-soft)" : type === "risk" ? "var(--danger-soft)" : "var(--surface-2)";
  return (
    <div style={{ padding: 12, borderRadius: 12, background: tone, border: "1px solid var(--line)" }} className="col gap-10">
      <div className="row spread" style={{ gap: 10, alignItems: "flex-start" }}>
        <div className="col gap-4" style={{ minWidth: 0 }}>
          <span style={{ fontSize: 13.5, fontWeight: 800, color: "var(--ink)" }}>{card.title || "秘書結果"}</span>
          {card.summary && <span style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{card.summary}</span>}
        </div>
        {type === "confirmation" && <span className="badge badge-warn" style={{ height: 22 }}>待確認</span>}
      </div>

      {type === "download" && !!card.downloads?.length && (
        <div className="row gap-8" style={{ flexWrap: "wrap" }}>
          {card.downloads.map((d, idx) => (
            <a key={idx} className="btn btn-primary btn-sm" style={{ textDecoration: "none" }}
              href={AGENT_API_BASE + d.url} download={d.filename || true} target="_blank" rel="noopener noreferrer">
              <Icon name="inbound" size={13}/>{d.label || d.filename || "下載"}
            </a>
          ))}
        </div>
      )}

      {!!card.fields?.length && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: 8 }}>
          {card.fields.map((field, idx) => (
            <div key={idx} style={{ padding: 8, borderRadius: 9, background: "var(--surface)", border: "1px solid var(--line)" }}>
              <div className="muted" style={{ fontSize: 11, marginBottom: 3 }}>{field.label}</div>
              <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink)", wordBreak: "break-word" }}>{agentFieldValue(field.value)}</div>
            </div>
          ))}
        </div>
      )}

      {!!card.candidates?.length && (
        <div className="col gap-7">
          {card.candidates.slice(0, 6).map(item => (
            <button key={item.id} className="btn btn-sm" style={{ justifyContent: "flex-start", height: "auto", minHeight: 34, padding: "8px 10px", textAlign: "left", lineHeight: 1.4 }}>
              <Icon name="checkCircle" size={14}/>
              <span>{item.item_name} · {item.spec_model || "無型號"} · 庫存 {item.stock || 0}{item.unit || ""}</span>
            </button>
          ))}
        </div>
      )}

      {!!card.risks?.length && (
        <div className="col gap-7">
          {card.risks.slice(0, 5).map(risk => (
            <div key={risk.title} className="row spread" style={{ fontSize: 12.5, padding: "7px 0", borderBottom: "1px solid var(--line-soft)" }}>
              <span style={{ fontWeight: 800, color: risk.level === "high" ? "var(--danger)" : "var(--ink-2)" }}>{risk.title}</span>
              <span className="num muted">{risk.count}</span>
            </div>
          ))}
        </div>
      )}

      {!!card.rows?.length && (
        <div className="col gap-7" style={{ maxHeight: 220, overflow: "auto" }}>
          {card.rows.slice(0, 8).map((row, idx) => (
            <div key={row.id || idx} style={{ padding: 9, borderRadius: 9, background: "var(--surface)", border: "1px solid var(--line)" }}>
              <div style={{ fontSize: 12.5, fontWeight: 800, color: "var(--ink)" }}>{row.title || row.item_name || row.transaction_no || row.alert_no || `結果 ${idx + 1}`}</div>
              <div className="muted" style={{ marginTop: 3, fontSize: 12, lineHeight: 1.45 }}>{row.body || row.summary || row.suggestion || JSON.stringify(row)}</div>
            </div>
          ))}
        </div>
      )}

      {type === "confirmation" && requestId && (
        <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-sm" onClick={() => onCancel(requestId)} disabled={busy}>取消</button>
          <button className="btn btn-primary btn-sm" onClick={() => onConfirm(requestId)} disabled={busy}>
            <Icon name="check" size={14}/>{busy ? "確認中…" : "確認執行"}
          </button>
        </div>
      )}
    </div>
  );
};

const AGENT_ACTION_LABELS = { borrow: "借用", outbound: "領用/出庫", inbound: "入庫", return: "歸還", stocktake: "盤點", adjust: "調整" };

function agentRequestCards(request, fallbackCards = []) {
  if (fallbackCards?.length) return fallbackCards;
  return request?.cards || [];
}

function agentDraftNeedsEdit(request) {
  if (!request || request.status !== "pending" || !request.parsed_command) return false;
  const pc = request.parsed_command || {};
  const cards = request.cards || [];
  if ((pc.candidate_items || []).length) return true;
  if ((pc.missing_fields || []).length) return true;
  return cards.some((card) => ["clarification", "candidates"].includes(card.card_type));
}

const toLocalDt = (v) => {
  if (!v) return "";
  const s = String(v).trim().replace(" ", "T");
  return s.length >= 16 ? s.slice(0, 16) : s;
};

const AgentDraftForm = ({ request, onSend, busy }) => {
  const pc = request.parsed_command || {};
  const cands = pc.candidate_items || [];
  const requiresReturn = !!pc.requires_return && pc.action_type !== "return";
  const itemName = pc.resolved_item_name || pc.item_name || "物資";
  const [model, setModel] = React.useState(pc.resolved_item_id ? String(pc.resolved_item_id) : "");
  const [qty, setQty] = React.useState(pc.quantity != null ? String(pc.quantity) : "");
  const [unit, setUnit] = React.useState(pc.unit || "");
  const [loc, setLoc] = React.useState(pc.work_location || "");
  const [task, setTask] = React.useState(pc.task_type || "");
  const [ret, setRet] = React.useState(toLocalDt(pc.expected_return_at));
  const [err, setErr] = React.useState("");

  const submit = () => {
    setErr("");
    const merged = { ...pc };
    if (cands.length) {
      const chosen = cands.find((c) => String(c.id) === String(model));
      if (!chosen) { setErr("請選擇具體型號"); return; }
      merged.resolved_item_id = chosen.id;
      merged.resolved_item_name = chosen.item_name;
      merged.resolved_spec_model = chosen.spec_model;
      merged.item_name = chosen.item_name;
      merged.unit = (unit || merged.unit || chosen.unit) || "";
      merged.candidate_items = [];
    }
    if (!qty || Number(qty) <= 0) { setErr("請填寫數量"); return; }
    merged.quantity = Number(qty);
    if (unit) merged.unit = unit;
    if (loc) merged.work_location = loc;
    if (task) merged.task_type = task;
    if (requiresReturn) {
      if (!ret) { setErr("借用需要填寫預計歸還時間"); return; }
      merged.expected_return_at = ret.replace("T", " ");
    }
    merged.missing_fields = (merged.missing_fields || []).filter((f) => !(
      (f === "item_model" && merged.resolved_item_id) ||
      (f === "quantity" && merged.quantity) ||
      (f === "expected_return_at" && merged.expected_return_at) ||
      (f === "work_location" && merged.work_location) ||
      (f === "task_type" && merged.task_type) ||
      (f === "item_name" && merged.item_name)
    ));
    onSend(request.id, merged);
  };

  const fieldStyle = { padding: 8, borderRadius: 9, background: "var(--surface)", border: "1px solid var(--line)" };
  const actionLabel = AGENT_ACTION_LABELS[pc.action_type] || pc.action_type || "庫存動作";
  return (
    <div style={{ padding: 12, borderRadius: 12, background: "var(--warn-soft)", border: "1px solid var(--line)" }} className="col gap-9">
      <div className="row spread"><span style={{ fontSize: 13, fontWeight: 800 }}>確認並補全{actionLabel}</span><span className="badge badge-warn" style={{ height: 20 }}>待發送</span></div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <div style={fieldStyle}><div className="muted" style={{ fontSize: 11, marginBottom: 3 }}>動作</div><div style={{ fontSize: 12.5, fontWeight: 700 }}>{AGENT_ACTION_LABELS[pc.action_type] || pc.action_type || "—"}</div></div>
        <div style={fieldStyle}><div className="muted" style={{ fontSize: 11, marginBottom: 3 }}>物資</div><div style={{ fontSize: 12.5, fontWeight: 700 }}>{itemName}</div></div>
      </div>

      {cands.length > 0 ? (
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}><span style={{ color: model ? "var(--ink-2)" : "var(--danger)" }}>型號 {model ? "" : "（必選）"}</span>
          <select className="input" value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="">請選擇型號…</option>
            {cands.map((c) => <option key={c.id} value={c.id}>{(c.spec_model || "無型號") + " · 庫存 " + (c.stock != null ? c.stock : "?") + (c.unit || "")}</option>)}
          </select>
        </label>
      ) : (
        <div style={fieldStyle}><div className="muted" style={{ fontSize: 11, marginBottom: 3 }}>型號</div><div style={{ fontSize: 12.5, fontWeight: 700 }}>{pc.resolved_spec_model || pc.spec_model || "無型號"}</div></div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}>數量
          <input className="input" type="number" min="0" value={qty} onChange={(e) => setQty(e.target.value)} placeholder="數量"/></label>
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}>單位
          <input className="input" value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="根/组/套…"/></label>
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}>地點
          <input className="input" value={loc} onChange={(e) => setLoc(e.target.value)} placeholder="作業地點"/></label>
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}>作業
          <input className="input" value={task} onChange={(e) => setTask(e.target.value)} placeholder="作業內容"/></label>
      </div>
      {requiresReturn && (
        <label className="col gap-4" style={{ fontSize: 11.5, fontWeight: 700 }}><span style={{ color: ret ? "var(--ink-2)" : "var(--danger)" }}>預計歸還時間 {ret ? "" : "（必填）"}</span>
          <input className="input" type="datetime-local" value={ret} onChange={(e) => setRet(e.target.value)}/></label>
      )}
      {err && <div style={{ color: "var(--danger)", fontSize: 12, fontWeight: 700 }}>{err}</div>}
      <button className="btn btn-primary btn-sm" disabled={busy} onClick={submit} style={{ height: 36 }}>
        <Icon name="check" size={14}/>{busy ? "發送中…" : "發送並完成記錄"}
      </button>
    </div>
  );
};

// 輕量 Markdown 渲染(無依賴,純 React 節點,不用 innerHTML):支持標題/粗體/斜體/
// 行內代碼/表格/有序無序列表/引用。秘書回答用它,使「標題、黑體、表格」正確顯示。
const mdInline = (text) => {
  const nodes = [];
  const re = /(\*\*([^*]+)\*\*|__([^_]+)__|`([^`]+)`|\*([^*]+)\*)/;
  let rest = String(text == null ? "" : text);
  let k = 0;
  while (rest) {
    const m = rest.match(re);
    if (!m) { nodes.push(rest); break; }
    if (m.index > 0) nodes.push(rest.slice(0, m.index));
    if (m[2] != null || m[3] != null) nodes.push(<strong key={k++}>{m[2] != null ? m[2] : m[3]}</strong>);
    else if (m[4] != null) nodes.push(<code key={k++} style={{ background: "rgba(99,102,241,0.12)", color: "#4f46e5", padding: "1px 5px", borderRadius: 5, fontSize: "0.92em", fontFamily: "ui-monospace, Consolas, monospace" }}>{m[4]}</code>);
    else if (m[5] != null) nodes.push(<em key={k++}>{m[5]}</em>);
    rest = rest.slice(m.index + m[0].length);
  }
  return nodes;
};

const mdRow = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
const mdIsTableSep = (line) => {
  if (!line || line.indexOf("|") < 0) return false;
  const cells = mdRow(line);
  return cells.length > 0 && cells.every((c) => /^:?-{1,}:?$/.test(c));
};

const MarkdownView = ({ text }) => {
  const lines = String(text == null ? "" : text).replace(/\r/g, "").split("\n");
  const blocks = [];
  let i = 0, key = 0;
  while (i < lines.length) {
    const line = lines[i];
    // 表格:當前行含 | 且下一行是分隔行
    if (line.indexOf("|") >= 0 && i + 1 < lines.length && mdIsTableSep(lines[i + 1])) {
      const header = mdRow(line);
      const rows = [];
      i += 2;
      while (i < lines.length && lines[i].indexOf("|") >= 0 && lines[i].trim()) {
        rows.push(mdRow(lines[i]));
        i += 1;
      }
      blocks.push(
        <div key={key++} style={{ overflowX: "auto", margin: "6px 0" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: 12.5 }}>
            <thead><tr>{header.map((h, j) => <th key={j} style={{ textAlign: "left", padding: "6px 10px", borderBottom: "2px solid var(--line)", color: "var(--ink)", fontWeight: 800, whiteSpace: "nowrap" }}>{mdInline(h)}</th>)}</tr></thead>
            <tbody>{rows.map((r, ri) => <tr key={ri} style={{ borderBottom: "1px solid var(--line)" }}>{header.map((_, ci) => <td key={ci} style={{ padding: "5px 10px", color: "var(--ink-2)", verticalAlign: "top" }}>{mdInline(r[ci] == null ? "" : r[ci])}</td>)}</tr>)}</tbody>
          </table>
        </div>
      );
      continue;
    }
    // 標題
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      const lvl = h[1].length;
      const size = [17, 16, 15, 14, 13.5, 13][lvl - 1];
      blocks.push(<div key={key++} style={{ fontSize: size, fontWeight: 800, color: "var(--ink)", margin: blocks.length ? "10px 0 4px" : "0 0 4px", lineHeight: 1.3 }}>{mdInline(h[2])}</div>);
      i += 1;
      continue;
    }
    // 引用
    if (/^>\s?/.test(line)) {
      blocks.push(<div key={key++} style={{ borderLeft: "3px solid var(--line)", paddingLeft: 10, color: "var(--ink-3)", margin: "4px 0" }}>{mdInline(line.replace(/^>\s?/, ""))}</div>);
      i += 1;
      continue;
    }
    // 列表(連續行)
    if (/^\s*([-*+]|\d+\.)\s+/.test(line)) {
      const items = [];
      const ordered = /^\s*\d+\.\s+/.test(line);
      while (i < lines.length && /^\s*([-*+]|\d+\.)\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*([-*+]|\d+\.)\s+/, ""));
        i += 1;
      }
      const Tag = ordered ? "ol" : "ul";
      blocks.push(<Tag key={key++} style={{ margin: "4px 0", paddingLeft: 22, lineHeight: 1.55 }}>{items.map((it, j) => <li key={j} style={{ marginBottom: 2 }}>{mdInline(it)}</li>)}</Tag>);
      continue;
    }
    // 空行
    if (!line.trim()) { i += 1; continue; }
    // 段落(合併連續非空非塊行)
    const para = [line];
    i += 1;
    while (i < lines.length && lines[i].trim() && !/^(#{1,6}\s|>\s?|\s*([-*+]|\d+\.)\s)/.test(lines[i]) && !(lines[i].indexOf("|") >= 0 && i + 1 < lines.length && mdIsTableSep(lines[i + 1]))) {
      para.push(lines[i]);
      i += 1;
    }
    blocks.push(<div key={key++} style={{ margin: "3px 0", lineHeight: 1.55, whiteSpace: "pre-wrap" }}>{mdInline(para.join("\n"))}</div>);
  }
  return <div>{blocks}</div>;
};

// P4:內核執行步驟(實時 ⚙→✓/✗,與平臺終端同款信息)
const agentStepOutcome = (step) => {
  const status = String((step && step.status) || "");
  if (step && step.running) return { mark: "⚙", color: "#7dd3fc", suffix: " · 執行中…", pending: false };
  if (status === "confirmation_required" || status === "pending_confirmation") {
    return { mark: "⏳", color: "#fbbf24", suffix: " · 待確認", pending: true };
  }
  if (status === "partial") return { mark: "⚠", color: "#fbbf24", suffix: " · 部分完成", pending: false };
  if (step && step.ok) return { mark: "✓", color: "#86efac", suffix: "", pending: false };
  return { mark: "✗", color: "#f87171", suffix: "", pending: false };
};

const AgentSteps = ({ steps }) => (
  <div className="col gap-3" style={{ padding: "8px 11px", borderRadius: 11, background: "#0b1220", border: "1px solid var(--line)" }}>
    {steps.map((s) => {
      const outcome = agentStepOutcome(s);
      return (
        <div key={s.step_no} style={{
          fontSize: 11.5, fontFamily: "ui-monospace, Consolas, Menlo, monospace",
          color: outcome.color,
        }}>
          {outcome.mark} {s.command || s.tool_name}
          {s.args && Object.keys(s.args).length ? " " + JSON.stringify(s.args) : ""}
          {outcome.suffix}
          {!outcome.pending && !s.running && s.error ? <span style={{ color: "#fbbf24" }}> · {s.error}</span> : null}
        </div>
      );
    })}
  </div>
);

const AgentMessage = ({ item, onConfirm, onCancel, onSend, busy }) => {
  if (!item.content && !item.action_request && !item.cards?.length && !(item.steps || []).length && !item.streaming) return null;
  const isUser = item.role === "user";
  const cards = agentRequestCards(item.action_request, item.cards || []);
  const draft = !isUser && agentDraftNeedsEdit(item.action_request);
  const waitingForTool = !isUser && item.streaming && !(item.steps || []).length && !item.content && !draft && !cards.length;
  return (
    <div className="row" style={{ justifyContent: isUser ? "flex-end" : "flex-start" }}>
      <div className="col gap-8" style={{ maxWidth: "88%", alignItems: isUser ? "flex-end" : "stretch" }}>
        {!isUser && !!(item.steps || []).length && <AgentSteps steps={item.steps}/>}
        {waitingForTool && <div className="muted" style={{ padding: "8px 11px", borderRadius: 11, background: "var(--surface)", border: "1px dashed var(--line)", fontSize: 12.5 }}>
          正在判斷是否需要調用工具;開始執行後會在這裡顯示 dm / asset / legal 等指令。
        </div>}
        {(item.content || isUser) && <div style={{
          padding: "10px 12px",
          borderRadius: 13,
          background: isUser ? "var(--blue)" : "var(--surface)",
          color: isUser ? "#fff" : "var(--ink-2)",
          border: isUser ? "none" : "1px solid var(--line)",
          boxShadow: isUser ? "var(--sh-blue)" : "none",
          whiteSpace: isUser ? "pre-wrap" : "normal",
          fontSize: 13,
          lineHeight: 1.55,
        }}>
          {isUser ? item.content : <MarkdownView text={item.content}/>}
        </div>}
        {draft && <AgentDraftForm request={item.action_request} onSend={onSend} busy={busy}/>}
        {!isUser && !draft && !!cards?.length && cards.map((card, idx) => (
          <AgentCard
            key={idx}
            card={card}
            actionRequest={item.action_request}
            onConfirm={onConfirm}
            onCancel={onCancel}
            busy={busy}
          />
        ))}
      </div>
    </div>
  );
};

const UnifiedAgentAssistant = ({ page, warehouse }) => {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [restoring, setRestoring] = React.useState(false);
  const [restoreReady, setRestoreReady] = React.useState(false);
  const [conversationId, setConversationId] = React.useState(readStoredConversation);
  const [pendingAutoPrompt, setPendingAutoPrompt] = React.useState("");
  const [thread, setThread] = React.useState([
    {
      role: "assistant",
      content: "我是你的專屬 AI 助理。直接說要做什麼——我會在你的權限範圍內實時逐步執行:查庫存/ERP、出入庫、物資建檔、預算調整、佔用、工單、採購、供應商;每一步你都看得見,全部寫入審計,可用平臺終端 runs show 回放。也可以讓我解釋任何頁面和指標。",
      cards: [],
    },
  ]);
  const [error, setError] = React.useState("");
  const [histOpen, setHistOpen] = React.useState(false);
  const restoreGenerationRef = React.useRef(0);
  const identityGenerationRef = React.useRef(0);
  const streamGenerationRef = React.useRef(0);
  const streamAbortRef = React.useRef(null);
  const voiceCtlRef = React.useRef(null);
  const restorePromiseRef = React.useRef(Promise.resolve(null));
  const restoreReadyRef = React.useRef(false);
  const conversationRef = React.useRef(readStoredConversation());
  const openRef = React.useRef(false);
  const busyRef = React.useRef(false);
  openRef.current = open;
  busyRef.current = busy;

  const AGENT_WELCOME = { role: "assistant", content: "新對話已開啟。直接說要做什麼——我會在你的權限範圍內逐步執行,每步可見、全部寫審計。", cards: [] };
  const loadAgentConversation = async (id = null) => {
    if (busyRef.current) return null;
    const generation = ++restoreGenerationRef.current;
    const identityGeneration = identityGenerationRef.current;
    ++streamGenerationRef.current;
    restoreReadyRef.current = false;
    setRestoreReady(false);
    setRestoring(true);
    setError("");
    const restore = (async () => {
    try {
      const query = id ? `?conversation_id=${encodeURIComponent(id)}&message_limit=80`
        : "?message_limit=80";
      const r = await agentJson("/api/assistant/bootstrap" + query);
      const msgs = (r.messages || []).map(m => m.role === "user"
        ? { role: "user", content: m.content }
        : { role: "assistant", content: m.content, steps: (m.metadata && m.metadata.steps) || [], cards: [] });
      const restoredActions = (r.confirmation_actions || []).map((action) => ({
        card_type: "result",
        title: action.title || "已保存的確認操作",
        summary: `${action.status || "unknown"} · 此舊版面板以唯讀方式恢復；需確認或 Passkey 驗證時請到 Warehouse 2.0 秘書。`,
        fields: action.fields || [],
        restored_action: action,
      }));
      if (restoredActions.length) {
        msgs.push({
          role: "assistant",
          content: "已從服務端恢復確認卡；以下狀態以服務端最新版本為準。",
          cards: restoredActions,
        });
      }
      if (generation !== restoreGenerationRef.current
          || identityGeneration !== identityGenerationRef.current) return null;
      setThread(msgs.length ? msgs : [AGENT_WELCOME]);
      const restoredId = r.conversation && r.conversation.id;
      conversationRef.current = restoredId || null;
      setConversationId(restoredId || null);
      if (restoredId) localStorage.setItem(agentConvKey(), String(restoredId));
      else localStorage.removeItem(agentConvKey());
      restoreReadyRef.current = true;
      setRestoreReady(true);
      return r;
    } catch (e) {
      if (generation !== restoreGenerationRef.current
          || identityGeneration !== identityGenerationRef.current) return null;
      localStorage.removeItem(agentConvKey());
      conversationRef.current = null;
      setConversationId(null);
      setThread([AGENT_WELCOME]);
      restoreReadyRef.current = false;
      setRestoreReady(false);
      setError("載入歷史失敗:" + (e.message || e));
      return null;
    } finally {
      if (generation === restoreGenerationRef.current
          && identityGeneration === identityGenerationRef.current) setRestoring(false);
    }
    })();
    restorePromiseRef.current = restore;
    return restore;
  };
  const newAgentConversation = async () => {
    ++restoreGenerationRef.current;
    const identityGeneration = identityGenerationRef.current;
    const streamGeneration = ++streamGenerationRef.current;
    const isCurrent = () => identityGeneration === identityGenerationRef.current
      && streamGeneration === streamGenerationRef.current;
    restoreReadyRef.current = false;
    setRestoreReady(false);
    setRestoring(true);
    try {
      const r = await agentJson("/api/ai/conversations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ title: "新對話", channel: "agent" }) });
      if (!isCurrent()) return;
      conversationRef.current = r.conversation.id;
      setConversationId(r.conversation.id);
      localStorage.setItem(agentConvKey(), String(r.conversation.id));
      restoreReadyRef.current = true;
      setRestoreReady(true);
      setError("");
    } catch (e) {
      if (!isCurrent()) return;
      conversationRef.current = null;
      setConversationId(null);
      localStorage.removeItem(agentConvKey());
      setError("建立新對話失敗:" + (e.message || e));
    } finally {
      if (isCurrent()) setRestoring(false);
    }
    if (isCurrent()) setThread([AGENT_WELCOME]);
  };

  React.useEffect(() => {
    const openAgent = (event) => {
      // 全平台對話式:帶任務打開秘書一律直接開始對話,缺的信息由秘書在對話裡追問,
      // 不再用「草稿放輸入框等用戶補完」的形式。
      const prompt = event.detail?.prompt || "";
      const wasOpen = openRef.current;
      setOpen(true);
      if (!wasOpen && !busyRef.current) loadAgentConversation();
      if (prompt) {
        setText("");
        setPendingAutoPrompt(prompt);
      }
    };
    window.addEventListener(AGENT_OPEN_EVENT, openAgent);
    window.addEventListener(LEGACY_AGENT_OPEN_EVENT, openAgent);
    const openSecretary = (prompt = "", options = {}) => window.dispatchEvent(new CustomEvent(AGENT_OPEN_EVENT, { detail: { prompt, autoAsk: !!options.autoAsk } }));
    window.openUnifiedAgent = openSecretary;
    window.openCompanySecretary = openSecretary;
    return () => {
      window.removeEventListener(AGENT_OPEN_EVENT, openAgent);
      window.removeEventListener(LEGACY_AGENT_OPEN_EVENT, openAgent);
    };
  }, []);

  React.useEffect(() => {
    if (conversationId) localStorage.setItem(agentConvKey(), String(conversationId));
  }, [conversationId]);

  // 單次權威 bootstrap 同時恢復對話、結構化任務狀態與三類確認卡。
  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        if (!cancelled) await loadAgentConversation();
      } catch (_) { /* 未登入或無歷史:保持歡迎語 */ }
    })();
    return () => { cancelled = true; };
  }, []);

  // 換賬號/換公司:切到該賬號自己的對話,並清空屏上的上一個賬號會話
  React.useEffect(() => {
    const onUserChanged = () => {
      ++restoreGenerationRef.current;
      ++identityGenerationRef.current;
      ++streamGenerationRef.current;
      if (streamAbortRef.current) streamAbortRef.current.abort();
      streamAbortRef.current = null;
      if (voiceCtlRef.current) voiceCtlRef.current.shutdown();
      restoreReadyRef.current = false;
      restorePromiseRef.current = Promise.resolve(null);
      setRestoreReady(false);
      busyRef.current = false;
      setBusy(false);
      conversationRef.current = null;
      setConversationId(null);
      setThread([AGENT_WELCOME]);
      setText("");
      setError("");
      if (openRef.current) loadAgentConversation();
    };
    const onStorage = event => {
      if (event.key === "warehouse_current_tenant" || event.key === "warehouse_auth_token") {
        onUserChanged();
      }
    };
    window.addEventListener("warehouse-user-changed", onUserChanged);
    window.addEventListener("storage", onStorage);
    return () => {
      window.removeEventListener("warehouse-user-changed", onUserChanged);
      window.removeEventListener("storage", onStorage);
      ++streamGenerationRef.current;
      if (streamAbortRef.current) streamAbortRef.current.abort();
      streamAbortRef.current = null;
      if (voiceCtlRef.current) voiceCtlRef.current.shutdown();
    };
  }, []);

  const updateStreamingAssistant = (updater) => {
    setThread(prev => {
      const next = [...prev];
      for (let i = next.length - 1; i >= 0; i -= 1) {
        if (next[i]?.streaming) {
          next[i] = updater(next[i]);
          return next;
        }
      }
      return prev;
    });
  };

  // 語音對話:部分識別灰字上屏(流式體感),定稿後直接交給 ask
  const askRef = React.useRef(null);
  const voiceCtl = useAgentVoice(
    (t) => { if (askRef.current) askRef.current(t); },
    (partial) => setText(partial),
  );
  voiceCtlRef.current = voiceCtl;

  const receiptInputRef = React.useRef(null);
  // 上傳收據/發票/合同 → 後端視覺識別 → 自動把識別結果喂進內核建單(不用打字)
  const uploadReceipt = async (file) => {
    if (!file || busyRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    await restorePromiseRef.current;
    if (!restoreReadyRef.current
        || identityGeneration !== identityGenerationRef.current) return;
    const streamGeneration = ++streamGenerationRef.current;
    if (streamAbortRef.current) streamAbortRef.current.abort();
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    streamAbortRef.current = controller;
    const isCurrentStream = () => (
      identityGeneration === identityGenerationRef.current
      && streamGeneration === streamGenerationRef.current
    );
    busyRef.current = true;
    setBusy(true);
    setError("");
    setThread(prev => [...prev, { role: "user", content: `🧾 上傳收據:${file.name}` }, { role: "assistant", content: "正在識別收據…", steps: [], streaming: true }]);
    let suggested = "";
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await (window.authFetch || fetch)(AGENT_API_BASE + "/api/agent/receipt", {
        method: "POST", body: fd, signal: controller && controller.signal,
      });
      const d = await res.json().catch(() => ({}));
      if (!isCurrentStream()) return;
      if (!res.ok || !d.ok) throw new Error(d.error || d.message || "識別失敗");
      const r = d.receipt || {};
      const items = (r.items || []).map(it => `${it.name || "物品"} ${it.qty || ""}${it.unit || ""} ¥${it.amount != null ? it.amount : (it.unit_price != null ? it.unit_price : "?")}`).join("、");
      updateStreamingAssistant(() => ({ role: "assistant", content: `🧾 已識別 ${r.doc_type || "收據"}:供應商 ${r.supplier || "未標"},日期 ${r.date || "未標"},總計 ¥${r.total != null ? r.total : "?"}\n明細:${items || "(見識別結果)"}\n\n正在為你入賬…`, steps: [], streaming: true }));
      suggested = d.suggested_text;
    } catch (e) {
      if (!isCurrentStream()) return;
      updateStreamingAssistant(() => ({ role: "assistant", content: "收據識別失敗:" + (e.message || e) + "\n(若未配置圖片識別,請到「系統設置」配置全局 API Key)", steps: [], streaming: false }));
      busyRef.current = false;
      setBusy(false);
      return;
    }
    // 識別結果驅動內核建單(複用流式)
    try {
      await agentRunStream({ text: suggested, conversation_id: conversationRef.current }, (ev) => {
        if (!isCurrentStream()) return;
        if (ev.event === "run_start") {
          conversationRef.current = ev.conversation_id || conversationRef.current;
          setConversationId(conversationRef.current);
        }
        else if (ev.event === "step_start") updateStreamingAssistant((item) => ({ ...item, steps: [...(item.steps || []), { ...ev, running: true }] }));
        else if (ev.event === "step") updateStreamingAssistant((item) => ({ ...item, steps: (item.steps || []).map(s => (s.step_no === ev.step_no && s.running ? { ...ev, running: false } : s)) }));
        else if (ev.event === "final") updateStreamingAssistant((item) => ({ ...item, content: (item.content || "") + "\n\n" + (ev.message || ""), run_id: ev.run_id, engine: ev.engine }));
      }, { signal: controller && controller.signal });
      if (!isCurrentStream()) return;
      updateStreamingAssistant((item) => ({ ...item, streaming: false }));
    } catch (e) {
      if (!isCurrentStream()) return;
      if (e && e.name === "AbortError") return;
      updateStreamingAssistant((item) => ({ ...item, streaming: false, content: (item.content || "") + "\n建單失敗:" + (e.message || e) }));
    } finally {
      if (isCurrentStream()) {
        streamAbortRef.current = null;
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  const ask = async (nextText = text) => {
    const content = (nextText || "").trim();
    if (!content || busyRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    await restorePromiseRef.current;
    if (!restoreReadyRef.current
        || identityGeneration !== identityGenerationRef.current) return;
    const streamGeneration = ++streamGenerationRef.current;
    if (streamAbortRef.current) streamAbortRef.current.abort();
    const controller = typeof window.AbortController === "function"
      ? new window.AbortController() : null;
    streamAbortRef.current = controller;
    const isCurrentStream = () => (
      identityGeneration === identityGenerationRef.current
      && streamGeneration === streamGenerationRef.current
    );
    busyRef.current = true;
    setBusy(true);
    setError("");
    setThread(prev => [...prev, { role: "user", content }, { role: "assistant", content: "", steps: [], cards: [], streaming: true }]);
    setText("");
    // P4:直連 AI 內核(與平臺終端同一鏈路:權限過濾工具→逐步執行→審計→run 可回放)
    try {
      await agentRunStream({
        text: content,
        conversation_id: conversationRef.current,
        page,
        warehouse,
        page_context: { page, module: agentModuleLabel(page), warehouse },
      }, (ev) => {
        if (!isCurrentStream()) return;
        if (ev.event === "run_start") {
          conversationRef.current = ev.conversation_id || conversationRef.current;
          setConversationId(conversationRef.current);
        } else if (ev.event === "step_start") {
          updateStreamingAssistant((item) => ({ ...item, steps: [...(item.steps || []), { ...ev, running: true }] }));
        } else if (ev.event === "step") {
          updateStreamingAssistant((item) => ({
            ...item,
            steps: (item.steps || []).map((s) => (s.step_no === ev.step_no && s.running ? { ...ev, running: false } : s)),
          }));
        } else if (ev.event === "final") {
          if (ev.view) window.dispatchEvent(new CustomEvent("alerts-agent-focus-view", { detail: ev.view }));
          if (ev.changed) {
            window.dispatchEvent(new CustomEvent("alerts-agent-changed", { detail: ev }));
            if (window.reloadData) window.reloadData();
          }
          updateStreamingAssistant((item) => ({
            ...item,
            content: ev.message || "已完成。",
            run_id: ev.run_id,
            engine: ev.engine,
            cards: ev.cards || item.cards || [],
          }));
          voiceCtl.speakReply(ev.message || "已完成。");
        }
      }, { signal: controller && controller.signal });
      if (!isCurrentStream()) return;
      updateStreamingAssistant((item) => ({ ...item, streaming: false }));
    } catch (err) {
      if (!isCurrentStream()) return;
      if (err && err.name === "AbortError") return;
      setError(err.message);
      updateStreamingAssistant((item) => ({
        ...item,
        streaming: false,
        content: item.content || ("助理暫時無法完成請求：" + err.message),
      }));
    } finally {
      if (isCurrentStream()) {
        streamAbortRef.current = null;
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  askRef.current = ask;

  React.useEffect(() => {
    if (!open || !pendingAutoPrompt || busy || restoring || !restoreReady) return;
    const prompt = pendingAutoPrompt;
    setPendingAutoPrompt("");
    ask(prompt);
  }, [open, pendingAutoPrompt, busy, restoring, restoreReady]);

  const confirmAction = async (id) => {
    if (busyRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    const operationGeneration = ++streamGenerationRef.current;
    const isCurrent = () => identityGeneration === identityGenerationRef.current
      && operationGeneration === streamGenerationRef.current;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      const result = await agentJson(`/api/agent/actions/${id}/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!isCurrent()) return;
      const execution = result.execution?.result || result.execution || {};
      setThread(prev => [
        ...prev,
        {
          role: "assistant",
          content: execution.transaction_no
            ? `已執行：${execution.transaction_no}${execution.ledger_no ? `，記錄 ${execution.ledger_no}` : ""}。`
            : "已執行並完成審計留痕。",
          cards: [{ card_type: "result", title: "執行結果", summary: "動作已完成。", result }],
        },
      ]);
      if (window.reloadData) window.reloadData();
    } catch (err) {
      if (!isCurrent()) return;
      setError(err.message);
      setThread(prev => [...prev, { role: "assistant", content: "確認未執行：" + err.message, cards: [] }]);
    } finally {
      if (isCurrent()) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  const cancelAction = async (id) => {
    if (busyRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    const operationGeneration = ++streamGenerationRef.current;
    const isCurrent = () => identityGeneration === identityGenerationRef.current
      && operationGeneration === streamGenerationRef.current;
    busyRef.current = true;
    setBusy(true);
    try {
      await agentJson(`/api/agent/actions/${id}/cancel`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!isCurrent()) return;
      setThread(prev => [...prev, { role: "assistant", content: "已取消這個待確認動作。", cards: [] }]);
    } catch (err) {
      if (!isCurrent()) return;
      setError(err.message);
    } finally {
      if (isCurrent()) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  // 編輯草稿(補全字段)→ 若已無缺漏則直接確認執行,完成領用/歸還記錄
  const sendDraft = async (id, mergedParsed) => {
    if (busyRef.current) return;
    const identityGeneration = identityGenerationRef.current;
    const operationGeneration = ++streamGenerationRef.current;
    const isCurrent = () => identityGeneration === identityGenerationRef.current
      && operationGeneration === streamGenerationRef.current;
    busyRef.current = true;
    setBusy(true);
    setError("");
    try {
      const edited = await agentJson(`/api/agent/actions/${id}/edit`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ parsed_command: mergedParsed }),
      });
      if (!isCurrent()) return;
      const ar = edited.action_request || {};
      const ready = (ar.cards || []).some((c) => c.card_type === "confirmation");
      if (!ready) {
        setThread((prev) => [...prev, {
          role: "assistant",
          content: (ar.cards && ar.cards[0] && ar.cards[0].summary) || "還需補充信息後才能發送。",
          cards: [],
          action_request: ar.parsed_command ? ar : null,
        }]);
        busyRef.current = false;
        setBusy(false);
        return;
      }
      const result = await agentJson(`/api/agent/actions/${id}/confirm`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      if (!isCurrent()) return;
      const execution = result.execution?.result || result.execution || {};
      setThread((prev) => [...prev, {
        role: "assistant",
        content: execution.transaction_no
          ? `✅ 已完成：${execution.transaction_no}${execution.ledger_no ? `，記錄 ${execution.ledger_no}` : ""}。`
          : "✅ 已完成並寫入庫存記錄與審計。",
        cards: [{ card_type: "result", title: "執行結果", summary: "已校驗庫存、生成記錄、寫入流水與審計留痕。", result }],
      }]);
      if (window.reloadData) window.reloadData();
    } catch (err) {
      if (!isCurrent()) return;
      setError(err.message);
      setThread((prev) => [...prev, { role: "assistant", content: "發送失敗：" + err.message, cards: [] }]);
    } finally {
      if (isCurrent()) {
        busyRef.current = false;
        setBusy(false);
      }
    }
  };

  const quickPrompts = page === "alerts" ? [
    "分析當前智能預警風險態勢",
    "只看紅色高危和超時未處理",
    "檢查超期借用並給出處置建議",
  ] : page === "procurement" ? [
    "分析當前招采待辦和流程阻塞點",
    "檢查招標採購流程節點權限傳遞風險",
    "整理今天可推進的招采動作清單",
  ] : [
    `${agentModuleLabel(page)}：解釋這個頁面和我現在應該關注什麼`,
    "幫我自查庫存、ERP 和待歸還風險",
    "幫我把今天的待辦整理成可執行清單",
  ];

  return (
    <>
      {!open && (
        <button
          className="agent-fab"
          onClick={() => setOpen(true)}
          style={{
            position: "fixed",
            right: 24,
            bottom: 24,
            zIndex: 70,
            height: 48,
            padding: "0 18px",
            borderRadius: 14,
            background: "var(--grad)",
            color: "#fff",
            boxShadow: "var(--sh-blue)",
            display: "flex",
            alignItems: "center",
            gap: 9,
            fontSize: 14,
            fontWeight: 800,
          }}
        >
          <Icon name="sparkle" size={18}/>公司 AI 秘書
        </button>
      )}

      {open && (
        <div className="agent-overlay" style={{ position: "fixed", inset: 0, zIndex: 75, pointerEvents: "none" }}>
          <div onClick={() => setOpen(false)} style={{ position: "absolute", inset: 0, background: "rgba(14,26,43,0.22)", pointerEvents: "auto" }}/>
          <aside
            className="card fade-up agent-panel"
            style={{
              position: "absolute",
              right: 18,
              top: 18,
              bottom: 18,
              width: "min(520px, calc(100vw - 36px))",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              pointerEvents: "auto",
            }}
          >
            <div className="row spread" style={{ padding: "15px 16px", borderBottom: "1px solid var(--line)", background: "linear-gradient(120deg, rgba(27,107,255,0.08), rgba(7,182,162,0.08))" }}>
              <div className="row gap-10">
                <div style={{ width: 36, height: 36, borderRadius: 11, background: "var(--grad)", color: "#fff", display: "grid", placeItems: "center" }}>
                  <Icon name="sparkle" size={18}/>
                </div>
                <div className="col gap-2">
                  <span style={{ fontSize: 15, fontWeight: 900 }}>公司 AI 秘書</span>
                  <span className="muted" style={{ fontSize: 11.5 }}>{agentModuleLabel(page)} · 解釋 / 草擬 / 確認後寫庫</span>
                </div>
              </div>
              <div className="row gap-6">
                <button className="btn btn-ghost btn-sm" disabled={busy || restoring} onClick={() => setHistOpen(true)} title="歷史對話" style={{ padding: "0 8px" }}><Icon name="clock" size={15}/></button>
                <button className="btn btn-ghost btn-sm" disabled={busy || restoring} onClick={newAgentConversation} title="新建對話" style={{ padding: "0 8px" }}><Icon name="plus" size={15}/></button>
                <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} style={{ width: 30, padding: 0 }}><Icon name="x" size={15}/></button>
              </div>
            </div>
            {window.AIHistoryDrawer && <AIHistoryDrawer open={histOpen} channel="agent" currentId={conversationId} onClose={() => setHistOpen(false)} onSelect={loadAgentConversation} onNew={newAgentConversation}/>}

            <div className="scroll-y col gap-12" style={{ flex: 1, padding: 16, background: "var(--surface-2)" }}>
              {thread.map((item, idx) => (
                <AgentMessage key={idx} item={item} onConfirm={confirmAction} onCancel={cancelAction} onSend={sendDraft} busy={busy}/>
              ))}
              {busy && <div className="muted" style={{ fontSize: 12.5 }}>公司 AI 秘書正在處理…</div>}
              {restoring && <div className="muted" style={{ fontSize: 12.5 }}>正在恢復服務端會話…</div>}
              {error && <div className="col gap-7" style={{ padding: 10, borderRadius: 10, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 12.5 }}><span>{error}</span><button className="btn btn-sm" disabled={restoring} onClick={() => loadAgentConversation()}>重新載入會話</button></div>}
            </div>

            <div style={{ padding: 14, borderTop: "1px solid var(--line)", background: "var(--surface)" }} className="col gap-10">
              <div className="row gap-7" style={{ flexWrap: "wrap" }}>
                <input ref={receiptInputRef} type="file" accept="image/*" style={{ display: "none" }}
                  onChange={e => { const f = e.target.files && e.target.files[0]; e.target.value = ""; if (f) uploadReceipt(f); }}/>
                <button className="btn btn-sm" onClick={() => receiptInputRef.current && receiptInputRef.current.click()} disabled={busy || restoring || !restoreReady}
                  title="上傳收據/發票/合同,秘書自動識別並建單記賬"
                  style={{ fontSize: 12, fontWeight: 700, background: "var(--grad)", color: "#fff", border: "none" }}>
                  <Icon name="inbound" size={13} color="#fff"/>上傳收據
                </button>
                {quickPrompts.map(prompt => (
                  <button key={prompt} className="btn btn-sm" onClick={() => ask(prompt)} disabled={busy || restoring || !restoreReady} style={{ fontSize: 12 }}>{prompt}</button>
                ))}
              </div>
              <div className="row gap-8">
                <textarea
                  className="input"
                  value={text}
                  disabled={busy || restoring || !restoreReady}
                  onChange={e => setText(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      ask();
                    }
                  }}
                  placeholder="直接輸入：解釋頁面、查庫存/ERP、草擬單據、借用歸還、協作跟進…"
                  style={{ height: 52, resize: "none", padding: 10, lineHeight: 1.4 }}
                />
                <div className="col gap-4">
                  <button className="btn btn-primary" onClick={() => ask()} disabled={busy || restoring || !restoreReady || !text.trim()} style={{ height: 30, minWidth: 76, padding: "0 10px" }}>
                    <Icon name="arrow" size={14}/>發送
                  </button>
                  <div className="row gap-4">
                    <button className="btn btn-sm"
                      title={voiceCtl.mode ? "點擊退出語音對話" : "點擊進入語音對話:之後無需再點,說完自動發送、回覆自動朗讀、可隨時插話打斷"}
                      disabled={busy || restoring || !restoreReady}
                      onClick={voiceCtl.toggleMode}
                      style={voiceCtl.mode
                        ? { background: (voiceCtl.listening ? "var(--danger)" : "var(--blue)"), color: "#fff", borderColor: voiceCtl.listening ? "var(--danger)" : "var(--blue)", minWidth: 36 }
                        : { minWidth: 36 }}>
                      <AgentMicIcon size={14}/>
                    </button>
                    <button className="btn btn-sm" title="單次語音輸入:點一下說一句,自動發送" disabled={busy || restoring || !restoreReady} onClick={voiceCtl.micClick}
                      style={(voiceCtl.listening && !voiceCtl.mode) ? { background: "var(--danger)", color: "#fff", borderColor: "var(--danger)", minWidth: 36 } : { minWidth: 36 }}>
                      <Icon name="sparkle" size={13}/>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </aside>
        </div>
      )}
    </>
  );
};

const UnifiedAgentLanding = () => (
  <div className="card fade-up" style={{ padding: 18, background: "linear-gradient(120deg, rgba(27,107,255,0.08), rgba(7,182,162,0.08))" }}>
    <div className="row spread" style={{ gap: 16, alignItems: "center" }}>
      <div className="row gap-12">
        <div style={{ width: 42, height: 42, borderRadius: 12, background: "var(--grad)", color: "#fff", display: "grid", placeItems: "center", flexShrink: 0 }}>
          <Icon name="sparkle" size={20}/>
        </div>
        <div className="col gap-4">
          <span style={{ fontSize: 16, fontWeight: 900 }}>公司 AI 秘書</span>
          <span className="muted" style={{ fontSize: 12.5 }}>全站只保留一個 AI 入口；解釋、查詢、分析、草擬和確認都在右側秘書中完成。</span>
        </div>
      </div>
      <div className="row gap-8" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
        <button className="btn btn-primary" onClick={() => window.openUnifiedAgent?.("幫我自查低庫存和待歸還問題", { autoAsk: true })}><Icon name="scan" size={15}/>自查風險</button>
        <button className="btn" onClick={() => window.openUnifiedAgent?.("查接地線庫存和待歸還", { autoAsk: true })}><Icon name="search" size={15}/>查庫存</button>
      </div>
    </div>
  </div>
);

// ============================================================
// 就地浮層簡答 — 點擊面板元素時,元素旁彈出秘書 2-4 句簡明解釋
// 取代「自動發一段固定長話術」。觸發:window.explainInline({label, context, deepPrompt})
// ============================================================
const InlineExplainHost = () => {
  const [st, setSt] = React.useState(null); // {x,y,label,context,deepPrompt,loading,message,error}

  React.useEffect(() => {
    if (!window.__lastPointer) window.__lastPointer = { x: window.innerWidth / 2, y: 120 };
    const track = (e) => { window.__lastPointer = { x: e.clientX, y: e.clientY }; };
    document.addEventListener("mousedown", track, true);
    const onOpen = (e) => {
      const d = e.detail || {};
      const p = window.__lastPointer || { x: window.innerWidth / 2, y: 120 };
      setSt({ x: p.x, y: p.y, label: d.label || "這個項目", context: d.context || {}, deepPrompt: d.deepPrompt || "", loading: true, message: "", error: "" });
    };
    window.explainInline = (detail) => window.dispatchEvent(new CustomEvent("inline-explain", { detail }));
    window.addEventListener("inline-explain", onOpen);
    const onKey = (e) => { if (e.key === "Escape") setSt(null); };
    window.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", track, true);
      window.removeEventListener("inline-explain", onOpen);
      window.removeEventListener("keydown", onKey);
    };
  }, []);

  const loading = st && st.loading;
  React.useEffect(() => {
    if (!loading) return undefined;
    let cancelled = false;
    (async () => {
      try {
        const res = await (window.authFetch || fetch)(AGENT_API_BASE + "/api/agent/explain", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ label: st.label, context: st.context }),
        });
        const d = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (!res.ok || d.ok === false) setSt((s) => s && ({ ...s, loading: false, error: d.message || d.error || "解釋失敗" }));
        else setSt((s) => s && ({ ...s, loading: false, message: d.message || "" }));
      } catch (err) {
        if (!cancelled) setSt((s) => s && ({ ...s, loading: false, error: err.message || "解釋失敗" }));
      }
    })();
    return () => { cancelled = true; };
  }, [loading]); // eslint-disable-line

  if (!st) return null;
  const W = 348;
  const left = Math.min(Math.max(12, st.x - W / 2), window.innerWidth - W - 12);
  const top = Math.min(st.y + 18, window.innerHeight - 230);
  const close = () => setSt(null);
  const expand = () => {
    const dp = st.deepPrompt || `關於「${st.label}」,請詳細解釋它的含義、與預算/工單/採購/庫存閉環的關係,以及下一步建議。相關數據:${JSON.stringify(st.context)}`;
    if (window.openUnifiedAgent) window.openUnifiedAgent(dp, { autoAsk: true });
    close();
  };
  return (
    <>
      <div onClick={close} style={{ position: "fixed", inset: 0, zIndex: 90 }}/>
      <div className="fade-up" style={{
        position: "fixed", left, top, width: W, zIndex: 91,
        background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 14,
        boxShadow: "0 18px 60px rgba(0,0,0,0.22)", overflow: "hidden",
      }}>
        <div className="row spread" style={{ padding: "11px 13px", borderBottom: "1px solid var(--line)", alignItems: "center" }}>
          <div className="row gap-7" style={{ alignItems: "center", minWidth: 0 }}>
            <span style={{ width: 22, height: 22, borderRadius: 7, background: "var(--grad)", display: "grid", placeItems: "center", flexShrink: 0 }}>
              <Icon name="sparkle" size={13} color="#fff"/>
            </span>
            <span style={{ fontSize: 12.5, fontWeight: 800, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{st.label}</span>
          </div>
          <button onClick={close} style={{ width: 24, height: 24, borderRadius: 7, display: "grid", placeItems: "center", background: "transparent", flexShrink: 0 }}>
            <Icon name="x" size={13} color="var(--ink-3)"/>
          </button>
        </div>
        <div style={{ padding: "12px 13px", maxHeight: 280, overflowY: "auto", fontSize: 13, lineHeight: 1.6, color: "var(--ink-2)" }}>
          {st.loading ? (
            <div className="row gap-8" style={{ color: "var(--ink-3)", fontSize: 12.5 }}>
              <span className="spin" style={{ width: 14, height: 14, borderRadius: "50%", border: "2px solid var(--line)", borderTopColor: "var(--blue)", display: "inline-block" }}/>
              秘書正在看…
            </div>
          ) : st.error ? (
            <div style={{ color: "var(--danger)", fontSize: 12.5 }}>{st.error}</div>
          ) : (
            <MarkdownView text={st.message}/>
          )}
        </div>
        <div className="row" style={{ padding: "9px 13px", borderTop: "1px solid var(--line)", justifyContent: "flex-end", gap: 8 }}>
          <button onClick={expand} className="row gap-5" style={{ height: 30, padding: "0 12px", borderRadius: 8, background: "var(--grad)", color: "#fff", fontSize: 12, fontWeight: 800 }}>
            <Icon name="forward" size={13} color="#fff"/>展開對話
          </button>
        </div>
      </div>
    </>
  );
};

Object.assign(window, { UnifiedAgentAssistant, UnifiedAgentLanding, InlineExplainHost });
