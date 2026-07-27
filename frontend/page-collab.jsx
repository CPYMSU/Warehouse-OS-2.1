/* ============================================================
   AI 秘書台：統一轉述、跟進、任務、共創與預算協調
   ============================================================ */
const {
  useEffect: useCollabEffect,
  useMemo: useCollabMemo,
  useRef: useCollabRef,
  useState: useCollabState,
} = React;

const COLLAB_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
// 「查看原話」暫時隱藏(2026-06 需求);要恢復時把這裡改回 true 即可
const COLLAB_SHOW_ORIGINAL_TEXT = false;
const collabFetch = async (path, options) => {
  const res = await (window.authFetch || fetch)(COLLAB_API_BASE + path, options);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
};

const SECRETARY_UI = {
  ink: "#1D1D1F",
  sub: "#6E6E73",
  hair: "rgba(29,29,31,0.12)",
  blue: "#0071E3",
  green: "#34C759",
  orange: "#FF9F0A",
  red: "#FF3B30",
  indigo: "#5856D6",
  bg: "#F5F5F7",
};

const collabPriority = {
  urgent: { text: "緊急", cls: "badge-danger" },
  high: { text: "重要", cls: "badge-warn" },
  normal: { text: "普通", cls: "badge-info" },
  low: { text: "低", cls: "badge-gray" },
};
const collabStatus = {
  sent: { text: "未讀", cls: "badge-warn" },
  read: { text: "已讀", cls: "badge-info" },
  replied: { text: "已回覆", cls: "badge-ok" },
  done: { text: "已完成", cls: "badge-ok" },
  archived: { text: "已歸檔", cls: "badge-gray" },
};
const ideaStatus = {
  planning: { text: "規劃中", cls: "badge-info" },
  active: { text: "推進中", cls: "badge-ok" },
  paused: { text: "暫停", cls: "badge-warn" },
  completed: { text: "已完成", cls: "badge-ok" },
  archived: { text: "已歸檔", cls: "badge-gray" },
};
const ideaTaskStatus = {
  todo: { text: "待辦", cls: "badge-gray" },
  doing: { text: "進行中", cls: "badge-info" },
  done: { text: "完成", cls: "badge-ok" },
  blocked: { text: "受阻", cls: "badge-danger" },
};

const secretaryModes = [
  {
    id: "message",
    label: "轉述",
    icon: "forward",
    headline: "轉述消息",
    cta: "讓秘書轉述",
    color: SECRETARY_UI.blue,
    placeholder: "例如：請幫我告訴王工，明天上午盤點 C 區安全工器具，順便確認 3 副絕緣手套的檢驗日期。",
  },
  {
    id: "task",
    label: "任務",
    icon: "clipboard",
    headline: "分配任務",
    cta: "交辦任務",
    color: SECRETARY_UI.green,
    placeholder: "例如：請李工今天 16:00 前核對武旗一線檢修工具清單，完成後把缺件發回來。",
  },
  {
    id: "followup",
    label: "跟進",
    icon: "bell",
    headline: "跟進提醒",
    cta: "發出跟進",
    color: SECRETARY_UI.orange,
    placeholder: "例如：請幫我提醒一下張工，昨天那批入庫單還差照片和驗收人簽字。",
  },
  {
    id: "idea",
    label: "共創",
    icon: "sparkle",
    headline: "共創計劃",
    cta: "生成計劃",
    color: SECRETARY_UI.indigo,
    placeholder: "例如：把安全工器具檢驗到期提醒做成自動分派，每週把風險清單發給班組負責人，先在一個班組試點。",
  },
];
const secretaryModeMap = secretaryModes.reduce((acc, mode) => ({ ...acc, [mode.id]: mode }), {});

const freshIdeaForm = () => ({
  title: "",
  raw_text: "",
  task_structure: "",
  budget_total: "",
  budget_currency: "CNY",
  budget_note: "",
  participant_user_ids: [],
});

const CollabBadge = ({ map, value }) => {
  const item = map[value] || { text: value || "—", cls: "badge-gray" };
  return <span className={`badge ${item.cls}`} style={{ height: 22 }}>{item.text}</span>;
};

const moneyText = (value, currency = "CNY") => {
  const n = Number(value || 0);
  const symbol = currency === "CNY" ? "¥" : `${currency || ""} `;
  return `${symbol}${Number.isFinite(n) ? n.toLocaleString("zh-CN", { maximumFractionDigits: 2 }) : "0"}`;
};

const previewText = (value, max = 92) => {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > max ? `${text.slice(0, max)}…` : text;
};

const replaceIdea = (items, nextIdea) => items.map((item) => item.id === nextIdea.id ? { ...item, ...nextIdea } : item);

const SecretaryCanvas = () => {
  const ref = useCollabRef(null);
  useCollabEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let raf = 0;
    let width = 0;
    let height = 0;
    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      width = Math.max(1, Math.floor(rect.width));
      height = Math.max(1, Math.floor(rect.height));
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    const draw = (t) => {
      ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = "#fbfbfd";
      ctx.fillRect(0, 0, width, height);
      for (let i = 0; i < 7; i += 1) {
        const y = 34 + i * 38;
        const shift = Math.sin(t / 1300 + i) * 18;
        ctx.beginPath();
        ctx.moveTo(-20, y);
        ctx.bezierCurveTo(width * 0.24, y - 28 + shift, width * 0.58, y + 30 - shift, width + 20, y + 4);
        ctx.strokeStyle = i % 2 === 0 ? "rgba(0,113,227,0.16)" : "rgba(29,29,31,0.07)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }
      for (let i = 0; i < 9; i += 1) {
        const x = 32 + i * 54;
        const h = 18 + Math.sin(t / 700 + i) * 8;
        ctx.fillStyle = i % 3 === 0 ? "rgba(52,199,89,0.20)" : "rgba(0,113,227,0.14)";
        ctx.fillRect(x % Math.max(width, 1), height - 34 - h, 3, h);
      }
      raf = requestAnimationFrame(draw);
    };
    resize();
    window.addEventListener("resize", resize);
    raf = requestAnimationFrame(draw);
    return () => {
      window.removeEventListener("resize", resize);
      cancelAnimationFrame(raf);
    };
  }, []);
  return <canvas ref={ref} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 1 }}/>;
};

const SecretaryMetric = ({ icon, label, value, tone, sub }) => (
  <div className="row gap-10" style={{ minHeight: 58, padding: "10px 12px", border: `1px solid ${SECRETARY_UI.hair}`, borderRadius: 8, background: "#fff" }}>
    <div style={{ width: 34, height: 34, borderRadius: 8, display: "grid", placeItems: "center", background: SECRETARY_UI.bg, color: tone }}>
      <Icon name={icon} size={16}/>
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 11.5, color: SECRETARY_UI.sub }}>{label}</div>
      <div className="num" style={{ fontSize: 20, fontWeight: 850, color: SECRETARY_UI.ink, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{value}</div>
      {sub && <div style={{ fontSize: 11, color: SECRETARY_UI.sub }}>{sub}</div>}
    </div>
  </div>
);

const SegmentButton = ({ active, icon, children, onClick, disabled }) => (
  <button
    className="row gap-7"
    onClick={onClick}
    disabled={disabled}
    style={{
      minHeight: 34,
      padding: "0 11px",
      borderRadius: 999,
      border: active ? "none" : `1px solid ${SECRETARY_UI.hair}`,
      background: active ? SECRETARY_UI.ink : "#fff",
      color: active ? "#fff" : SECRETARY_UI.ink,
      fontSize: 12.5,
      fontWeight: 800,
      opacity: disabled ? 0.55 : 1,
      whiteSpace: "nowrap",
    }}
  >
    {icon && <Icon name={icon} size={14}/>}
    {children}
  </button>
);

const SecretarySuggestion = ({ item }) => (
  <div style={{ display: "grid", gridTemplateColumns: "32px minmax(0, 1fr) auto", gap: 10, alignItems: "start", padding: "12px 0", borderTop: `1px solid ${SECRETARY_UI.hair}` }}>
    <div style={{ width: 32, height: 32, borderRadius: 8, display: "grid", placeItems: "center", background: SECRETARY_UI.bg, color: item.tone }}>
      <Icon name={item.icon} size={15}/>
    </div>
    <div style={{ minWidth: 0 }}>
      <div style={{ fontSize: 13.5, fontWeight: 850, color: SECRETARY_UI.ink, overflowWrap: "anywhere" }}>{item.title}</div>
      <div style={{ fontSize: 12, color: SECRETARY_UI.sub, lineHeight: 1.5, marginTop: 3, overflowWrap: "anywhere" }}>{item.body}</div>
    </div>
    <button className="btn btn-sm" onClick={item.onClick} style={{ alignSelf: "center", whiteSpace: "nowrap" }}>{item.cta}</button>
  </div>
);

const SecretaryComposer = ({
  mode,
  setMode,
  recipientId,
  setRecipientId,
  recipientOptions,
  priority,
  setPriority,
  text,
  setText,
  ideaForm,
  setIdeaForm,
  toggleIdeaPerson,
  busy,
  onSubmit,
}) => {
  const modeInfo = secretaryModeMap[mode] || secretaryModeMap.message;
  const isIdea = mode === "idea";
  const canSubmit = isIdea ? !!ideaForm.raw_text.trim() : !!text.trim();
  const submitOnEnter = (event) => {
    if (event.key !== "Enter" || event.shiftKey || busy || !canSubmit) return;
    event.preventDefault();
    onSubmit();
  };

  return (
    <div style={{ padding: 18, borderRadius: 8, background: "#fff", border: `1px solid ${SECRETARY_UI.hair}`, boxShadow: "0 1px 2px rgba(0,0,0,0.04)" }} className="col gap-14">
      <div className="row spread" style={{ gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div className="col gap-4" style={{ minWidth: 220 }}>
          <div className="row gap-8" style={{ fontSize: 15, fontWeight: 900, color: SECRETARY_UI.ink }}>
            <Icon name={modeInfo.icon} size={17} color={modeInfo.color}/>
            委託 AI 秘書
          </div>
          <div style={{ fontSize: 12.5, color: SECRETARY_UI.sub, lineHeight: 1.5 }}>{modeInfo.headline}</div>
        </div>
        <div className="row gap-7" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
          {secretaryModes.map((item) => (
            <SegmentButton key={item.id} active={mode === item.id} icon={item.icon} onClick={() => setMode(item.id)} disabled={busy}>
              {item.label}
            </SegmentButton>
          ))}
        </div>
      </div>

      {!isIdea && (
        <>
          <textarea
            className="input"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={submitOnEnter}
            rows={5}
            placeholder={modeInfo.placeholder}
            style={{ height: "auto", minHeight: 126, padding: 13, resize: "vertical", lineHeight: 1.6, fontSize: 13.5 }}
          />
          <details>
            <summary style={{ cursor: "pointer", fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>手動指定</summary>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 12, marginTop: 10 }}>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 750, color: SECRETARY_UI.ink }}>接收人
                <select className="input" value={recipientId} onChange={(e) => setRecipientId(e.target.value)}>
                  <option value="">由 AI 秘書識別</option>
                  {recipientOptions.map((p) => (
                    <option key={p.id} value={p.id}>{p.display_name || p.username}{p.role_names?.[0] ? ` · ${p.role_names[0]}` : ""}</option>
                  ))}
                </select>
              </label>
              <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 750, color: SECRETARY_UI.ink }}>優先級
                <select className="input" value={priority} onChange={(e) => setPriority(e.target.value)}>
                  <option value="auto">由 AI 秘書判斷</option>
                  <option value="normal">普通</option>
                  <option value="high">重要</option>
                  <option value="urgent">緊急</option>
                  <option value="low">低</option>
                </select>
              </label>
            </div>
          </details>
        </>
      )}

      {isIdea && (
        <>
          <input className="input" value={ideaForm.title} onChange={(e) => setIdeaForm({ ...ideaForm, title: e.target.value })} placeholder="計劃標題，可選"/>
          <textarea
            className="input"
            value={ideaForm.raw_text}
            onChange={(e) => setIdeaForm({ ...ideaForm, raw_text: e.target.value })}
            onKeyDown={submitOnEnter}
            rows={5}
            placeholder={modeInfo.placeholder}
            style={{ height: "auto", minHeight: 132, padding: 13, resize: "vertical", lineHeight: 1.6, fontSize: 13.5 }}
          />
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 750, color: SECRETARY_UI.ink }}>預算估算
              <input className="input num" type="number" min="0" step="100" value={ideaForm.budget_total} onChange={(e) => setIdeaForm({ ...ideaForm, budget_total: e.target.value })} placeholder="0"/>
            </label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 750, color: SECRETARY_UI.ink }}>幣種
              <select className="input" value={ideaForm.budget_currency} onChange={(e) => setIdeaForm({ ...ideaForm, budget_currency: e.target.value })}>
                <option value="CNY">CNY</option>
                <option value="USD">USD</option>
              </select>
            </label>
            <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 750, color: SECRETARY_UI.ink }}>預算說明
              <input className="input" value={ideaForm.budget_note} onChange={(e) => setIdeaForm({ ...ideaForm, budget_note: e.target.value })} placeholder="採購、人力、培訓或試點成本"/>
            </label>
          </div>
          <div className="col gap-8">
            <div style={{ fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>協作人</div>
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              {recipientOptions.length === 0 && <span style={{ fontSize: 12.5, color: SECRETARY_UI.sub }}>暫無可邀請的企業成員</span>}
              {recipientOptions.map((p) => {
                const checked = ideaForm.participant_user_ids.includes(p.id);
                return (
                  <label key={p.id} className="row gap-6" style={{ minHeight: 32, padding: "0 10px", borderRadius: 8, border: checked ? `1px solid ${SECRETARY_UI.blue}` : `1px solid ${SECRETARY_UI.hair}`, background: checked ? "rgba(0,113,227,0.08)" : SECRETARY_UI.bg, fontSize: 12.5, fontWeight: 750, cursor: "pointer" }}>
                    <input type="checkbox" checked={checked} onChange={() => toggleIdeaPerson(p.id)}/>
                    {p.display_name || p.username}
                  </label>
                );
              })}
            </div>
          </div>
          <details>
            <summary style={{ cursor: "pointer", fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>任務拆解偏好</summary>
            <textarea
              className="input"
              value={ideaForm.task_structure}
              onChange={(e) => setIdeaForm({ ...ideaForm, task_structure: e.target.value })}
              rows={4}
              placeholder={"逐行寫任務步驟，可用「標題：說明」。留空時由 AI 秘書自動拆解。"}
              style={{ height: "auto", minHeight: 96, marginTop: 9, padding: 12, resize: "vertical", lineHeight: 1.6 }}
            />
          </details>
        </>
      )}

      <div className="row spread" style={{ gap: 12, flexWrap: "wrap" }}>
        <span style={{ fontSize: 12, color: SECRETARY_UI.sub }}>接收人和優先級默認由 AI 秘書識別。</span>
        <button className="btn btn-primary" disabled={busy || !canSubmit} onClick={onSubmit} style={{ height: 40, minWidth: 134 }}>
          <Icon name={modeInfo.icon} size={16}/>
          {busy ? "處理中…" : modeInfo.cta}
        </button>
      </div>
    </div>
  );
};

const MessageThreadRow = ({ item, activeReplyId, setActiveReplyId, onAction, onReply, onFollowup, busy }) => {
  const [reply, setReply] = useCollabState("");
  const incoming = item.is_incoming;
  const counterpart = incoming ? item.sender_name : item.recipient_name;
  const direction = incoming ? `${counterpart} 的 AI 秘書 → 我` : `我的 AI 秘書 → ${counterpart}`;
  const canReply = incoming && item.status !== "done" && item.status !== "archived";
  const isWaiting = item.is_outgoing && ["sent", "read"].includes(item.status);
  const submitReply = () => {
    if (!reply.trim()) return;
    onReply(item, reply).then((ok) => {
      if (ok) {
        setReply("");
        setActiveReplyId(null);
      }
    });
  };

  return (
    <div style={{ display: "grid", gridTemplateColumns: "38px minmax(0, 1fr) auto", gap: 12, alignItems: "start", padding: "14px 0", borderTop: `1px solid ${SECRETARY_UI.hair}` }}>
      <div style={{ width: 38, height: 38, borderRadius: 8, display: "grid", placeItems: "center", background: incoming ? "rgba(0,113,227,0.08)" : "rgba(52,199,89,0.10)", color: incoming ? SECRETARY_UI.blue : SECRETARY_UI.green }}>
        <Icon name={incoming ? "sparkle" : "forward"} size={17}/>
      </div>
      <div className="col gap-8" style={{ minWidth: 0 }}>
        <div className="row spread" style={{ gap: 10, alignItems: "flex-start", flexWrap: "wrap" }}>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13.5, fontWeight: 900, color: SECRETARY_UI.ink, overflowWrap: "anywhere" }}>{direction}</div>
            <div className="num" style={{ fontSize: 11.5, color: SECRETARY_UI.sub, marginTop: 3 }}>{item.message_no} · {item.created_at || "—"}</div>
          </div>
          <div className="row gap-6" style={{ flexWrap: "wrap" }}>
            <CollabBadge map={collabPriority} value={item.priority}/>
            <CollabBadge map={collabStatus} value={item.status}/>
          </div>
        </div>
        <div style={{ padding: 12, borderRadius: 8, background: incoming ? SECRETARY_UI.bg : "rgba(0,113,227,0.06)", border: `1px solid ${SECRETARY_UI.hair}`, lineHeight: 1.65, fontSize: 13.2, color: SECRETARY_UI.ink, overflowWrap: "anywhere" }}>
          {item.assistant_text}
        </div>
        <div className="row gap-8" style={{ flexWrap: "wrap", fontSize: 12, color: SECRETARY_UI.sub }}>
          <span>意圖：<b style={{ color: SECRETARY_UI.ink }}>{item.intent || "協作請求"}</b></span>
          {item.parent_message_id && <span className="badge badge-gray" style={{ height: 20 }}>回覆鏈路</span>}
        </div>
        {item.reply_assistant_text && (
          <div style={{ padding: 10, borderRadius: 8, background: "rgba(52,199,89,0.09)", border: "1px solid rgba(52,199,89,0.22)", lineHeight: 1.55, fontSize: 12.5, color: SECRETARY_UI.ink }}>
            <b>已回覆：</b>{item.reply_assistant_text}
          </div>
        )}
        {COLLAB_SHOW_ORIGINAL_TEXT && (
          <details>
            <summary style={{ cursor: "pointer", fontSize: 12, color: SECRETARY_UI.sub, fontWeight: 750 }}>查看原話</summary>
            <div style={{ marginTop: 7, fontSize: 12.5, color: SECRETARY_UI.sub, lineHeight: 1.6, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{item.original_text}</div>
          </details>
        )}
        <div className="row gap-7" style={{ flexWrap: "wrap" }}>
          {incoming && item.status === "sent" && <button className="btn btn-sm" disabled={busy} onClick={() => onAction(item, "read")}><Icon name="check" size={14}/>已讀</button>}
          {canReply && <button className="btn btn-sm" disabled={busy} onClick={() => setActiveReplyId(activeReplyId === item.id ? null : item.id)}><Icon name="forward" size={14}/>回覆</button>}
          {incoming && item.status !== "done" && item.status !== "archived" && <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => onAction(item, "done")}><Icon name="checkCircle" size={14}/>完成</button>}
          {incoming && item.status !== "archived" && <button className="btn btn-sm" disabled={busy} onClick={() => onAction(item, "archive")}><Icon name="clipboard" size={14}/>歸檔</button>}
          {isWaiting && <button className="btn btn-sm" disabled={busy} onClick={() => onFollowup(item)}><Icon name="bell" size={14}/>跟進</button>}
        </div>
        {activeReplyId === item.id && (
          <div className="col gap-8" style={{ paddingTop: 4 }}>
            <textarea className="input" value={reply} onChange={(e) => setReply(e.target.value)} rows={3}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !busy && reply.trim()) { e.preventDefault(); submitReply(); } }}
              placeholder="把回覆交給你的 AI 秘書..."
              style={{ height: "auto", padding: 12, resize: "vertical", minHeight: 84, lineHeight: 1.6 }}/>
            <div className="row gap-8">
              <button className="btn btn-primary btn-sm" disabled={busy || !reply.trim()} onClick={submitReply}><Icon name="sparkle" size={14}/>轉述回覆</button>
              <button className="btn btn-sm" onClick={() => setActiveReplyId(null)}>取消</button>
            </div>
          </div>
        )}
      </div>
      <div style={{ justifySelf: "end", minWidth: 0 }}/>
    </div>
  );
};

const IdeaRow = ({ idea, busy, onTaskStatus, onIdeaStatus }) => {
  const tasks = idea.tasks || [];
  const members = idea.members || [];
  const budgetItems = idea.budget_items || [];
  const taskTotal = Number(idea.task_total ?? tasks.length ?? 0);
  const taskDone = Number(idea.task_done ?? tasks.filter((t) => t.status === "done").length ?? 0);
  const blocked = Number(idea.task_blocked ?? tasks.filter((t) => t.status === "blocked").length ?? 0);
  const progress = taskTotal ? Math.round((taskDone / taskTotal) * 100) : 0;
  const budgetTotal = Number(idea.budget_total || idea.budget_planned || 0);
  const openTasks = tasks.filter((task) => task.status !== "done");

  return (
    <div style={{ padding: "16px 0", borderTop: `1px solid ${SECRETARY_UI.hair}` }} className="col gap-12">
      <div className="row spread" style={{ gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div className="col gap-5" style={{ minWidth: 0, flex: "1 1 280px" }}>
          <div className="row gap-7" style={{ flexWrap: "wrap" }}>
            <span className="num" style={{ fontSize: 11.5, color: SECRETARY_UI.sub }}>{idea.idea_no}</span>
            <CollabBadge map={ideaStatus} value={idea.status}/>
            {blocked > 0 && <span className="badge badge-danger" style={{ height: 22 }}>{blocked} 項受阻</span>}
            {!!idea.my_open_tasks && <span className="badge badge-info" style={{ height: 22 }}>我的任務 {idea.my_open_tasks}</span>}
          </div>
          <div style={{ fontSize: 15.5, fontWeight: 900, color: SECRETARY_UI.ink, lineHeight: 1.35, overflowWrap: "anywhere" }}>{idea.title}</div>
          <div style={{ fontSize: 12, color: SECRETARY_UI.sub }}>發起人：{idea.creator_name || "—"} · {idea.created_at || "—"}</div>
        </div>
        <div style={{ minWidth: 150 }}>
          <div className="row spread" style={{ fontSize: 11.5, color: SECRETARY_UI.sub, marginBottom: 6 }}>
            <span>進度</span><span className="num">{progress}%</span>
          </div>
          <div style={{ height: 7, borderRadius: 999, background: SECRETARY_UI.bg, overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${Math.max(3, progress)}%`, background: progress >= 100 ? SECRETARY_UI.green : SECRETARY_UI.blue }}/>
          </div>
        </div>
      </div>

      <div style={{ fontSize: 12.8, color: SECRETARY_UI.ink, lineHeight: 1.6, overflowWrap: "anywhere" }}>
        {idea.ai_summary || idea.raw_text}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8 }}>
        <SecretaryMetric icon="user" label="協作人" value={members.length || 1} tone={SECRETARY_UI.blue}/>
        <SecretaryMetric icon="clipboard" label="任務" value={`${taskDone}/${taskTotal || 0}`} tone={SECRETARY_UI.green}/>
        <SecretaryMetric icon="chart" label="預算" value={moneyText(budgetTotal, idea.budget_currency)} tone={SECRETARY_UI.orange}/>
      </div>

      {!!members.length && (
        <div className="row gap-7" style={{ flexWrap: "wrap" }}>
          {members.slice(0, 8).map((m) => (
            <span key={`${idea.id}-${m.user_id}`} className="badge badge-gray" style={{ height: "auto", minHeight: 23, padding: "3px 8px", whiteSpace: "normal" }}>
              {m.display_name || `用戶 ${m.user_id}`} · {m.responsibility || "參與"}
            </span>
          ))}
        </div>
      )}

      <div className="col gap-8">
        <div style={{ fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>下一步任務</div>
        {openTasks.length === 0 && <div style={{ fontSize: 12.5, color: SECRETARY_UI.sub }}>沒有未完成任務。</div>}
        {openTasks.slice(0, 5).map((task) => (
          <div key={task.id} style={{ display: "grid", gridTemplateColumns: "minmax(0, 1fr) auto", gap: 10, padding: 10, borderRadius: 8, background: SECRETARY_UI.bg }}>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontSize: 12.8, fontWeight: 850, color: SECRETARY_UI.ink, overflowWrap: "anywhere" }}>{task.title}</div>
              <div style={{ fontSize: 11.5, color: SECRETARY_UI.sub, lineHeight: 1.45, marginTop: 3 }}>負責人：{task.assignee_name || "待定"}{task.due_text ? ` · ${task.due_text}` : ""}</div>
            </div>
            <div className="row gap-5" style={{ justifyContent: "flex-end", flexWrap: "wrap" }}>
              {["doing", "done", "blocked"].map((status) => (
                <button key={status} className={task.status === status ? "btn btn-primary btn-sm" : "btn btn-sm"} disabled={busy || task.status === status}
                  onClick={() => onTaskStatus(idea, task, status)}>
                  {ideaTaskStatus[status].text}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {!!budgetItems.length && (
        <details>
          <summary style={{ cursor: "pointer", fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>預算拆分</summary>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, marginTop: 9 }}>
            {budgetItems.map((item) => (
              <div key={item.id} style={{ padding: 10, borderRadius: 8, border: `1px solid ${SECRETARY_UI.hair}`, background: "#fff" }}>
                <div style={{ fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>{item.item_name}</div>
                <div className="num" style={{ fontSize: 15, fontWeight: 900, marginTop: 5, color: SECRETARY_UI.orange }}>{moneyText(item.amount, idea.budget_currency)}</div>
                {item.note && <div style={{ fontSize: 11.5, color: SECRETARY_UI.sub, lineHeight: 1.45, marginTop: 4 }}>{item.note}</div>}
              </div>
            ))}
          </div>
        </details>
      )}

      <div className="row gap-7" style={{ flexWrap: "wrap" }}>
        {[
          ["planning", "規劃"],
          ["active", "推進"],
          ["paused", "暫停"],
          ["completed", "完成"],
          ["archived", "歸檔"],
        ].map(([status, label]) => (
          <button key={status} className={idea.status === status ? "btn btn-primary btn-sm" : "btn btn-sm"} disabled={busy || idea.status === status}
            onClick={() => onIdeaStatus(idea, status)}>
            {label}
          </button>
        ))}
      </div>
    </div>
  );
};

const editReqStatus = {
  pending: { text: "待 AI 複核", cls: "badge-warn" },
  applied: { text: "已生效", cls: "badge-ok" },
  approved: { text: "已審核", cls: "badge-ok" },
  rejected: { text: "AI 未通過", cls: "badge-gray" },
  failed: { text: "失敗", cls: "badge-danger" },
};
const EDIT_FIELD_LABELS = { summary: "摘要", source_unit: "來源單位", handler: "經辦人", department: "部門", target: "去向", business_type: "業務類型" };
const EditRequestRow = ({ req, busy, onDecide }) => {
  const st = editReqStatus[req.status] || { text: req.status, cls: "badge-gray" };
  const fields = (req.changes && req.changes.fields) || {};
  const lb = req.changes && req.changes.link_budget;
  return (
    <div style={{ padding: 14, borderRadius: 8, border: `1px solid ${SECRETARY_UI.hair}`, background: "#fff" }} className="col gap-8">
      <div className="row spread" style={{ gap: 10, alignItems: "flex-start" }}>
        <div className="col gap-3" style={{ minWidth: 0 }}>
          <div style={{ fontSize: 13.5, fontWeight: 850, color: SECRETARY_UI.ink, overflowWrap: "anywhere" }}>{req.target_no} · {req.target_title || "庫存單據"}</div>
          <div style={{ fontSize: 12, color: SECRETARY_UI.sub }}>{req.proposer_name} 提交補充{req.decided_by_name ? ` · ${req.decided_by_name} 審核` : " · 等待 AI 秘書"}</div>
        </div>
        <span className={`badge ${st.cls}`} style={{ height: 20 }}>{st.text}</span>
      </div>
      {req.reason && <div style={{ fontSize: 12.5, color: SECRETARY_UI.ink, background: SECRETARY_UI.bg, borderRadius: 6, padding: "8px 10px" }}>{req.reason}</div>}
      {(Object.keys(fields).length > 0 || lb) && (
        <div className="row gap-6" style={{ flexWrap: "wrap" }}>
          {Object.entries(fields).map(([k, v]) => (
            <span key={k} className="badge badge-info" style={{ height: 20 }}>{EDIT_FIELD_LABELS[k] || k}：{String(v).slice(0, 24)}</span>
          ))}
          {lb && <span className="badge badge-warn" style={{ height: 20 }}>掛預算 ¥{lb.amount}</span>}
        </div>
      )}
      {req.apply_note && req.status !== "pending" && <div style={{ fontSize: 11.5, color: SECRETARY_UI.sub }}>{req.apply_note}</div>}
      {req.status === "pending" && req.can_decide && (
        <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-sm" disabled={busy} onClick={() => onDecide(req, false)}>兜底拒絕</button>
          <button className="btn btn-sm btn-primary" disabled={busy} onClick={() => onDecide(req, true)}>兜底生效</button>
        </div>
      )}
    </div>
  );
};

const PageCollab = () => {
  const [view, setView] = useCollabState("brief");
  const [threadFilter, setThreadFilter] = useCollabState("needs");
  const [people, setPeople] = useCollabState([]);
  const [messages, setMessages] = useCollabState([]);
  const [summary, setSummary] = useCollabState({});
  const [ideas, setIdeas] = useCollabState([]);
  const [ideaSummary, setIdeaSummary] = useCollabState({});
  const [ideaScope, setIdeaScope] = useCollabState("active");
  const [mode, setMode] = useCollabState("message");
  const [recipientId, setRecipientId] = useCollabState("");
  const [text, setText] = useCollabState("");
  const [priority, setPriority] = useCollabState("auto");
  const [ideaForm, setIdeaForm] = useCollabState(freshIdeaForm());
  const [busy, setBusy] = useCollabState(false);
  const [messagesLoading, setMessagesLoading] = useCollabState(true);
  const [ideasLoading, setIdeasLoading] = useCollabState(true);
  const [error, setError] = useCollabState("");
  const [notice, setNotice] = useCollabState("");
  const [activeReplyId, setActiveReplyId] = useCollabState(null);
  const [editRequests, setEditRequests] = useCollabState([]);
  const [editBox, setEditBox] = useCollabState("incoming");
  const [editLoading, setEditLoading] = useCollabState(false);

  const recipientOptions = useCollabMemo(() => people.filter((p) => !p.is_me), [people]);

  const computed = useCollabMemo(() => {
    const me = people.find((p) => p.is_me);
    const myId = me?.id;
    const incoming = messages.filter((item) => item.is_incoming);
    const outgoing = messages.filter((item) => item.is_outgoing);
    const unread = incoming.filter((item) => item.status === "sent");
    const needsMe = incoming.filter((item) => ["sent", "read"].includes(item.status));
    const waitingSent = outgoing.filter((item) => ["sent", "read"].includes(item.status));
    const taskRows = ideas.flatMap((idea) => (idea.tasks || []).map((task) => ({ ...task, idea })));
    const myTasks = taskRows.filter((task) => task.assignee_user_id === myId && task.status !== "done");
    const blockedTasks = taskRows.filter((task) => task.status === "blocked");
    const activeIdeas = ideas.filter((idea) => ["planning", "active", "paused"].includes(idea.status));
    const budgetTotal = activeIdeas.reduce((sum, idea) => sum + Number(idea.budget_total || idea.budget_planned || 0), 0);
    return { me, incoming, outgoing, unread, needsMe, waitingSent, taskRows, myTasks, blockedTasks, activeIdeas, budgetTotal };
  }, [people, messages, ideas]);

  const filteredMessages = useCollabMemo(() => {
    if (threadFilter === "delegated") return computed.outgoing;
    if (threadFilter === "waiting") return computed.waitingSent;
    if (threadFilter === "all") return messages;
    return computed.needsMe;
  }, [threadFilter, computed, messages]);

  const loadPeople = () =>
    collabFetch("/api/collab/people")
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "人員載入失敗");
        setPeople(data.people || []);
      });

  const loadMessages = () => {
    setMessagesLoading(true);
    setError("");
    return collabFetch("/api/collab/messages?box=all&status=active&limit=220")
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "消息載入失敗");
        setMessages(data.messages || []);
        setSummary(data.summary || {});
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setMessagesLoading(false));
  };

  const loadIdeas = (scope = ideaScope) => {
    setIdeasLoading(true);
    setError("");
    return collabFetch(`/api/collab/ideas?scope=${encodeURIComponent(scope)}&limit=80`)
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "共創計劃載入失敗");
        setIdeas(data.ideas || []);
        setIdeaSummary(data.summary || {});
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setIdeasLoading(false));
  };

  const loadEditRequests = (box = editBox) => {
    setEditLoading(true);
    return collabFetch(`/api/collab/edit-requests?box=${encodeURIComponent(box)}&limit=80`)
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "改單請求載入失敗");
        setEditRequests(data.requests || []);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setEditLoading(false));
  };

  const decideEditRequest = (req, approve) => {
    if (busy) return;
    if (!approve && !window.confirm(`人工兜底拒絕「${req.proposer_name}」對 ${req.target_no} 的修改?`)) return;
    setBusy(true);
    setError("");
    const path = `/api/collab/edit-requests/${req.id}/${approve ? "approve" : "reject"}`;
    collabFetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({}) })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "操作失敗");
        setNotice(approve ? `已人工兜底生效:${req.target_no}` : `已人工兜底拒絕:${req.target_no}`);
        loadEditRequests(editBox);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  useCollabEffect(() => {
    Promise.all([loadPeople(), loadMessages(), loadIdeas("active"), loadEditRequests("incoming")]).catch((e) => setError(e.message || String(e)));
  }, []);

  const refreshCurrent = () => {
    if (view === "ideas") return loadIdeas(ideaScope);
    if (view === "edits") return loadEditRequests(editBox);
    return Promise.all([loadPeople(), loadMessages(), loadIdeas(ideaScope), loadEditRequests(editBox)]);
  };

  const toggleIdeaPerson = (id) => {
    setIdeaForm((form) => {
      const exists = form.participant_user_ids.includes(id);
      return {
        ...form,
        participant_user_ids: exists ? form.participant_user_ids.filter((value) => value !== id) : [...form.participant_user_ids, id],
      };
    });
  };

  const composeText = () => {
    const clean = text.trim();
    if (mode === "task") return `任務委託：${clean}`;
    if (mode === "followup") return `跟進提醒：${clean}`;
    return clean;
  };

  const submitMessage = () => {
    if (busy || !text.trim()) return;
    setError("");
    setNotice("");
    // 未手動指定接收人 → 交給統一 AI 秘書(內核):它能理解「告訴所有人 / 跟李工說 / 提醒張三」,
    // 自行查人並轉述送達或廣播。手動指定接收人時才走下方精確直投。
    if (!recipientId) {
      const verb = mode === "task" ? "把這件事交辦下去" : mode === "followup" ? "發出跟進提醒" : "幫我轉述這條消息";
      const prompt = `請以協作秘書身份,${verb}:${text.trim()}`;
      if (window.openUnifiedAgent) {
        window.openUnifiedAgent(prompt, { autoAsk: true });
        setText("");
        setNotice("已交給 AI 秘書處理,可在右下角秘書面板看到逐步執行過程。");
      } else {
        setError("AI 秘書尚未載入,請稍後再試,或用「手動指定」直接選擇接收人。");
      }
      return;
    }
    setBusy(true);
    const payload = { text: composeText(), mode, recipient_user_id: Number(recipientId) };
    if (priority !== "auto") payload.priority = priority;
    collabFetch("/api/collab/messages", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(({ ok, data }) => {
        if (!ok) {
          const candidates = (data.recipient_candidates || []).map((p) => p.display_name || p.username).filter(Boolean);
          const hint = candidates.length ? ` 候選：${candidates.join("、")}` : "";
          throw new Error(`${data.error || "發送失敗"}${hint}`);
        }
        setText("");
        setRecipientId("");
        setPriority("auto");
        setThreadFilter("delegated");
        setView("threads");
        const message = data.message || {};
        const priorityText = collabPriority[message.priority]?.text || "自動";
        const recipientText = message.recipient_name ? `給 ${message.recipient_name}` : "";
        setNotice(mode === "task" ? `AI 秘書已${recipientText}交辦任務 · ${priorityText}` : mode === "followup" ? `AI 秘書已${recipientText}發出跟進提醒 · ${priorityText}` : `AI 秘書已${recipientText}完成轉述 · ${priorityText}`);
        return loadMessages();
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const createIdea = () => {
    if (busy || !ideaForm.raw_text.trim()) return;
    setBusy(true);
    setError("");
    setNotice("");
    collabFetch("/api/collab/ideas", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...ideaForm,
        budget_total: ideaForm.budget_total === "" ? 0 : Number(ideaForm.budget_total),
      }),
    })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "共創計劃創建失敗");
        setIdeaForm(freshIdeaForm());
        setIdeaScope("active");
        setView("ideas");
        setNotice("AI 秘書已生成共創計劃、任務和預算草案");
        return Promise.all([loadIdeas("active"), loadMessages()]);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const submitSecretary = () => {
    if (mode === "idea") createIdea();
    else submitMessage();
  };

  const action = (item, act) => {
    setBusy(true);
    setError("");
    setNotice("");
    return collabFetch(`/api/collab/messages/${item.id}/${act}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "操作失敗");
        setNotice(act === "done" ? "已標記完成" : act === "read" ? "已標記已讀" : "已歸檔");
        return loadMessages();
      })
      .then(() => true)
      .catch((e) => { setError(e.message || String(e)); return false; })
      .finally(() => setBusy(false));
  };

  const reply = (item, replyText) => {
    setBusy(true);
    setError("");
    setNotice("");
    return collabFetch(`/api/collab/messages/${item.id}/reply`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: replyText }),
    })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "回覆失敗");
        setNotice("你的 AI 秘書已轉述回覆");
        return loadMessages();
      })
      .then(() => true)
      .catch((e) => { setError(e.message || String(e)); return false; })
      .finally(() => setBusy(false));
  };

  const updateTaskStatus = (idea, task, status) => {
    setBusy(true);
    setError("");
    setNotice("");
    return collabFetch(`/api/collab/ideas/${idea.id}/tasks/${task.id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "任務狀態更新失敗");
        setIdeas((items) => replaceIdea(items, data.idea));
        setNotice("任務狀態已更新");
        return loadIdeas(ideaScope);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const updateIdeaStatus = (idea, status) => {
    setBusy(true);
    setError("");
    setNotice("");
    return collabFetch(`/api/collab/ideas/${idea.id}/status`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    })
      .then(({ ok, data }) => {
        if (!ok) throw new Error(data.error || "計劃狀態更新失敗");
        setIdeas((items) => status === "archived" && ideaScope !== "archived" ? items.filter((item) => item.id !== idea.id) : replaceIdea(items, data.idea));
        setNotice("共創計劃狀態已更新");
        return loadIdeas(ideaScope);
      })
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setBusy(false));
  };

  const startFollowup = (item) => {
    const targetId = item.is_incoming ? item.sender_user_id : item.recipient_user_id;
    setMode("followup");
    setRecipientId(String(targetId || ""));
    setPriority("auto");
    setText(`請幫我跟進這件事：${previewText(item.assistant_text || item.original_text, 420)}`);
    setView("brief");
    setNotice("已放入跟進委託框");
  };

  const suggestions = [];
  if (computed.unread.length) {
    suggestions.push({
      icon: "bell",
      tone: SECRETARY_UI.red,
      title: `${computed.unread.length} 條新消息需要處理`,
      body: `最新來自 ${computed.unread[0].sender_name || "同事"}：${previewText(computed.unread[0].assistant_text)}`,
      cta: "查看",
      onClick: () => { setThreadFilter("needs"); setView("threads"); },
    });
  }
  if (computed.waitingSent.length) {
    suggestions.push({
      icon: "clock",
      tone: SECRETARY_UI.orange,
      title: `${computed.waitingSent.length} 條委託等待對方回應`,
      body: `可先跟進 ${computed.waitingSent[0].recipient_name || "對方"}：${previewText(computed.waitingSent[0].assistant_text)}`,
      cta: "跟進",
      onClick: () => startFollowup(computed.waitingSent[0]),
    });
  }
  if (computed.blockedTasks.length) {
    suggestions.push({
      icon: "alert",
      tone: SECRETARY_UI.red,
      title: `${computed.blockedTasks.length} 項共創任務受阻`,
      body: `${computed.blockedTasks[0].idea?.title || "共創計劃"} 需要協調資源或重新分工。`,
      cta: "處理",
      onClick: () => { setIdeaScope("tasks"); loadIdeas("tasks"); setView("ideas"); },
    });
  }
  if (computed.myTasks.length) {
    suggestions.push({
      icon: "clipboard",
      tone: SECRETARY_UI.green,
      title: `${computed.myTasks.length} 項任務分配給我`,
      body: `${computed.myTasks[0].title || "待辦任務"} · ${computed.myTasks[0].idea?.title || "共創計劃"}`,
      cta: "查看",
      onClick: () => { setIdeaScope("tasks"); loadIdeas("tasks"); setView("ideas"); },
    });
  }
  if (!suggestions.length) {
    suggestions.push({
      icon: "checkCircle",
      tone: SECRETARY_UI.green,
      title: "目前沒有緊急協作阻塞",
      body: "可以直接把下一個轉述、任務或共創想法交給 AI 秘書。",
      cta: "新委託",
      onClick: () => { setMode("message"); setView("brief"); },
    });
  }

  return (
    <div className="col gap-18">
      <PageHead
        title="AI 秘書台"
        sub="一個入口承接轉述、任務、跟進、共創和預算協調"
        actions={<button className="btn btn-primary btn-sm" onClick={refreshCurrent} disabled={busy || messagesLoading || ideasLoading}><Icon name="refresh" size={15}/>刷新</button>}
      />

      <div style={{ position: "relative", overflow: "hidden", borderRadius: 8, border: `1px solid ${SECRETARY_UI.hair}`, background: "#fbfbfd", minHeight: 186 }}>
        <SecretaryCanvas/>
        <div style={{ position: "relative", padding: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: 16, alignItems: "end" }}>
          <div className="col gap-10" style={{ minWidth: 0 }}>
            <div className="row gap-8" style={{ color: SECRETARY_UI.blue, fontSize: 12, fontWeight: 900, letterSpacing: 0 }}>
              <Icon name="sparkle" size={15}/>
              AGI Secretary
            </div>
            <div style={{ fontSize: 34, lineHeight: 1.05, fontWeight: 900, color: SECRETARY_UI.ink, maxWidth: 620 }}>
              每個人只面對一個 AI 秘書
            </div>
            <div style={{ fontSize: 13, lineHeight: 1.65, color: SECRETARY_UI.sub, maxWidth: 620 }}>
              人與人之間的消息、任務、創意和預算都由秘書整理、轉述、跟進，避免用戶在多個 AI 窗口之間選擇。
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(128px, 1fr))", gap: 9 }}>
            <SecretaryMetric icon="bell" label="待我處理" value={computed.needsMe.length || summary.inbox_open || 0} tone={SECRETARY_UI.red}/>
            <SecretaryMetric icon="clock" label="等待對方" value={computed.waitingSent.length || summary.sent_waiting || 0} tone={SECRETARY_UI.orange}/>
            <SecretaryMetric icon="sparkle" label="共創進行" value={ideaSummary.active || computed.activeIdeas.length || 0} tone={SECRETARY_UI.indigo}/>
            <SecretaryMetric icon="clipboard" label="我的任務" value={computed.myTasks.length || ideaSummary.my_tasks || 0} tone={SECRETARY_UI.green}/>
          </div>
        </div>
      </div>

      <SecretaryComposer
        mode={mode}
        setMode={setMode}
        recipientId={recipientId}
        setRecipientId={setRecipientId}
        recipientOptions={recipientOptions}
        priority={priority}
        setPriority={setPriority}
        text={text}
        setText={setText}
        ideaForm={ideaForm}
        setIdeaForm={setIdeaForm}
        toggleIdeaPerson={toggleIdeaPerson}
        busy={busy}
        onSubmit={submitSecretary}
      />

      {notice && <div style={{ padding: 12, borderRadius: 8, border: "1px solid rgba(52,199,89,0.22)", background: "rgba(52,199,89,0.08)", color: "#137A3A", fontWeight: 800, fontSize: 13 }}>{notice}</div>}
      {error && <div style={{ padding: 12, borderRadius: 8, border: "1px solid rgba(255,59,48,0.22)", background: "rgba(255,59,48,0.08)", color: SECRETARY_UI.red, fontWeight: 800, fontSize: 13 }}>{error}</div>}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(310px, 1fr))", gap: 14, alignItems: "start" }}>
        <div style={{ padding: 18, borderRadius: 8, background: "#fff", border: `1px solid ${SECRETARY_UI.hair}` }} className="col gap-12">
          <div className="row spread" style={{ gap: 12 }}>
            <div style={{ fontSize: 15, fontWeight: 900, color: SECRETARY_UI.ink }}>今日秘書簡報</div>
            <span className="num" style={{ fontSize: 12, color: SECRETARY_UI.sub }}>{new Date().toLocaleDateString("zh-CN")}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(132px, 1fr))", gap: 8 }}>
            <SecretaryMetric icon="bell" label="未讀" value={computed.unread.length || summary.inbox_unread || 0} tone={SECRETARY_UI.red}/>
            <SecretaryMetric icon="chart" label="預算池" value={moneyText(computed.budgetTotal)} tone={SECRETARY_UI.orange}/>
          </div>
          <div>
            {suggestions.slice(0, 4).map((item, index) => <SecretarySuggestion key={index} item={item}/>)}
          </div>
        </div>

        <div style={{ padding: 18, borderRadius: 8, background: "#fff", border: `1px solid ${SECRETARY_UI.hair}` }} className="col gap-14">
          <div className="row spread" style={{ gap: 12, alignItems: "flex-start", flexWrap: "wrap" }}>
            <div className="col gap-4">
              <div style={{ fontSize: 15, fontWeight: 900, color: SECRETARY_UI.ink }}>協作中樞</div>
              <div style={{ fontSize: 12.5, color: SECRETARY_UI.sub }}>消息線索、跟進狀態和共創計劃在這裡集中處理。</div>
            </div>
            <div className="row gap-7" style={{ flexWrap: "wrap", justifyContent: "flex-end" }}>
              <SegmentButton active={view === "brief"} icon="sparkle" onClick={() => setView("brief")}>簡報</SegmentButton>
              <SegmentButton active={view === "threads"} icon="forward" onClick={() => setView("threads")}>消息線索</SegmentButton>
              <SegmentButton active={view === "ideas"} icon="chart" onClick={() => setView("ideas")}>共創計劃</SegmentButton>
              <SegmentButton active={view === "edits"} icon="edit" onClick={() => { setView("edits"); loadEditRequests(editBox); }}>
                AI 補錄審核{editRequests.filter((r) => r.status === "pending" && r.can_decide).length ? ` (${editRequests.filter((r) => r.status === "pending" && r.can_decide).length})` : ""}
              </SegmentButton>
            </div>
          </div>

          {view === "brief" && (
            <div className="col gap-8">
              <div style={{ fontSize: 12.5, fontWeight: 850, color: SECRETARY_UI.ink }}>最新協作</div>
              {messagesLoading && <div style={{ fontSize: 13, color: SECRETARY_UI.sub }}>讀取消息中…</div>}
              {!messagesLoading && messages.length === 0 && <div style={{ padding: 26, textAlign: "center", color: SECRETARY_UI.sub, background: SECRETARY_UI.bg, borderRadius: 8, fontSize: 13 }}>暫無協作消息</div>}
              {!messagesLoading && messages.slice(0, 5).map((item) => (
                <MessageThreadRow key={item.id} item={item} activeReplyId={activeReplyId} setActiveReplyId={setActiveReplyId} onAction={action} onReply={reply} onFollowup={startFollowup} busy={busy}/>
              ))}
            </div>
          )}

          {view === "threads" && (
            <div className="col gap-12">
              <div className="row gap-7" style={{ flexWrap: "wrap" }}>
                <SegmentButton active={threadFilter === "needs"} onClick={() => setThreadFilter("needs")}>需要我處理</SegmentButton>
                <SegmentButton active={threadFilter === "waiting"} onClick={() => setThreadFilter("waiting")}>等待對方</SegmentButton>
                <SegmentButton active={threadFilter === "delegated"} onClick={() => setThreadFilter("delegated")}>我委託的</SegmentButton>
                <SegmentButton active={threadFilter === "all"} onClick={() => setThreadFilter("all")}>全部</SegmentButton>
              </div>
              {messagesLoading && <div style={{ fontSize: 13, color: SECRETARY_UI.sub }}>讀取消息中…</div>}
              {!messagesLoading && filteredMessages.length === 0 && <div style={{ padding: 32, textAlign: "center", color: SECRETARY_UI.sub, background: SECRETARY_UI.bg, borderRadius: 8, fontSize: 13 }}>沒有符合條件的消息線索</div>}
              {!messagesLoading && filteredMessages.map((item) => (
                <MessageThreadRow key={item.id} item={item} activeReplyId={activeReplyId} setActiveReplyId={setActiveReplyId} onAction={action} onReply={reply} onFollowup={startFollowup} busy={busy}/>
              ))}
            </div>
          )}

          {view === "ideas" && (
            <div className="col gap-12">
              <div className="row gap-7" style={{ flexWrap: "wrap" }}>
                {[
                  ["active", "進行中"],
                  ["mine", "我發起"],
                  ["tasks", "我的任務"],
                  ["archived", "已歸檔"],
                ].map(([scope, label]) => (
                  <SegmentButton key={scope} active={ideaScope === scope} disabled={ideasLoading} onClick={() => { setIdeaScope(scope); loadIdeas(scope); }}>
                    {label}
                  </SegmentButton>
                ))}
              </div>
              {ideasLoading && <div style={{ fontSize: 13, color: SECRETARY_UI.sub }}>讀取共創計劃中…</div>}
              {!ideasLoading && ideas.length === 0 && <div style={{ padding: 32, textAlign: "center", color: SECRETARY_UI.sub, background: SECRETARY_UI.bg, borderRadius: 8, fontSize: 13 }}>暫無共創計劃</div>}
              {!ideasLoading && ideas.map((idea) => (
                <IdeaRow key={idea.id} idea={idea} busy={busy} onTaskStatus={updateTaskStatus} onIdeaStatus={updateIdeaStatus}/>
              ))}
            </div>
          )}

          {view === "edits" && (
            <div className="col gap-12">
              <div style={{ fontSize: 12.5, color: SECRETARY_UI.sub }}>
                AI 待辦流裡「有問題的單據」對所有人可見;補充/修改會交給 AI 秘書審核,安全補充字段通過後立即生效。這裡保留歷史記錄和人工兜底。
              </div>
              <div className="row gap-7" style={{ flexWrap: "wrap" }}>
                <SegmentButton active={editBox === "incoming"} disabled={editLoading} onClick={() => { setEditBox("incoming"); loadEditRequests("incoming"); }}>AI 待複核</SegmentButton>
                <SegmentButton active={editBox === "outgoing"} disabled={editLoading} onClick={() => { setEditBox("outgoing"); loadEditRequests("outgoing"); }}>我提交的</SegmentButton>
                <SegmentButton active={editBox === "all"} disabled={editLoading} onClick={() => { setEditBox("all"); loadEditRequests("all"); }}>全部</SegmentButton>
              </div>
              {editLoading && <div style={{ fontSize: 13, color: SECRETARY_UI.sub }}>讀取改單請求中…</div>}
              {!editLoading && editRequests.length === 0 && <div style={{ padding: 32, textAlign: "center", color: SECRETARY_UI.sub, background: SECRETARY_UI.bg, borderRadius: 8, fontSize: 13 }}>暫無改單請求</div>}
              {!editLoading && editRequests.map((req) => <EditRequestRow key={req.id} req={req} busy={busy} onDecide={decideEditRequest}/>)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

window.PageCollab = PageCollab;
