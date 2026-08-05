/* ============================================================
   8 · AI 實時後台調度中樞
   ============================================================ */
const AI_ICON = { red: "flame", orange: "trend", blue: "swap", yellow: "clock" };
const AI_COLOR = { red: "#EF4444", orange: "#F59E0B", blue: "#3B82F6", yellow: "#EAB308" };
const AI_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
// 分類圖標映射: 已知功能分類沿用固定圖標,未知按是否需歸還挑一個。
const AI_CAT_ICON = { hardware_material: "link", safety_tool: "shield", maintenance_tool: "gear", consumable: "link", returnable: "swap" };
// 動態分類: 完全取自當前租戶 bootstrap 的功能分類,不再用演示分類兜底。
const aiCategories = () => {
  const list = window.LEDGER_CATEGORIES || [];
  return list.map((c) => ({ id: c.id, label: c.name, icon: AI_CAT_ICON[c.id] || (c.requires_return ? "shield" : "link") }));
};
const firstCategoryId = () => (aiCategories()[0] || {}).id || "";

const buildAlertRadar = (alerts) => ([
  { level: "red", label: "高風險物資", c: "#EF4444" },
  { level: "orange", label: "低庫存物資", c: "#F59E0B" },
  { level: "yellow", label: "即將到期事項", c: "#EAB308" },
  { level: "blue", label: "數據異常", c: "#3B82F6" },
]).map(group => {
  const rows = alerts.filter(a => a.level === group.level);
  const items = Array.from(new Set(rows.map(a => a.item).filter(Boolean))).slice(0, 4);
  return { ...group, n: rows.length, items };
}).filter(group => group.n > 0);

async function aiJson(path, options) {
  const res = await (window.authFetch || fetch)(AI_API_BASE + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

const PageAI = ({ go }) => {
  const [health, setHealth] = React.useState(null);
  const loadHealth = React.useCallback(() => {
    aiJson("/api/ai/health").then(setHealth).catch(() => setHealth(null));
  }, []);
  React.useEffect(() => { loadHealth(); }, [loadHealth]);
  const aiTasks = window.AI_TASKS || [];
  const aiLogs = window.AI_LOG || [];
  const pendingTasks = aiTasks.filter(t => t.status !== "已自動處理").length;
  const radar = buildAlertRadar(window.ALERTS || []);

  const stat = [
    { k: "AI 運行狀態", v: "在線", live: true, c: "var(--ok)" },
    { k: "理解索引", v: health?.search_documents ?? "—", u: "條", c: "var(--blue)" },
    { k: "對話記憶", v: health ? (health.memories || 0) + (health.lessons || 0) : "—", u: "條", c: "var(--teal)" },
    { k: "待人工確認", v: pendingTasks, u: "項", c: "var(--warn)" },
  ];

  return (
    <div className="col gap-18">
      <PageHead title="AI 實時後台調度中樞" sub="AI 輔助決策 · 人員授權執行 · 連續監測倉儲運行"
        actions={<span className="badge badge-ok" style={{ height: 32, padding: "0 14px" }}><span className="dot pulse-danger" style={{ background: "var(--ok)" }}/>持續監測中</span>}/>

      <AICommandCenter onRefreshHealth={loadHealth}/>

      {/* AI 狀態欄 */}
      <div className="card fade-up" style={{ padding: 0, overflow: "hidden", background: "linear-gradient(120deg, rgba(27,107,255,0.06), rgba(7,182,162,0.06))" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)" }}>
          {stat.map((s,i) => (
            <div key={i} className="row gap-12" style={{ padding: "22px 24px", borderLeft: i?"1px solid var(--line-soft)":"none" }}>
              {s.live && <span style={{ position: "relative", width: 12, height: 12 }}><span style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "var(--ok)" }}/><span className="pulse-danger" style={{ position: "absolute", inset: 0, borderRadius: "50%", background: "var(--ok)" }}/></span>}
              <div className="col gap-3">
                <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{s.k}</span>
                <span className="num" style={{ fontSize: 26, fontWeight: 700, color: s.c }}>{s.v}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 3 }}>{s.u}</span></span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: 18, alignItems: "flex-start" }}>
        {/* AI 風險雷達 */}
        <div className="card fade-up" style={{ padding: 20, animationDelay: ".06s" }}>
          <SecHead title="AI 風險雷達" sub="實時掃描結果"/>
          <div className="col gap-12">
            {radar.length ? radar.map((r,i) => (
              <div key={i} style={{ padding: 14, borderRadius: 12, background: r.c+"0e", border: `1px solid ${r.c}22` }}>
                <div className="row spread" style={{ marginBottom: 8 }}>
                  <span className="row gap-8" style={{ fontSize: 13, fontWeight: 700, color: "var(--ink)" }}><span style={{ width: 9, height: 9, borderRadius: 3, background: r.c }}/>{r.label}</span>
                  <span className="num" style={{ fontSize: 18, fontWeight: 800, color: r.c }}>{r.n}</span>
                </div>
                <div className="row gap-6" style={{ flexWrap: "wrap" }}>
                  {r.items.map(t => <span key={t} className="badge badge-gray" style={{ height: 20, fontSize: 10.5 }}>{t}</span>)}
                </div>
              </div>
            )) : (
              <div className="col center" style={{ minHeight: 132, gap: 10, color: "var(--ink-3)", textAlign: "center", border: "1px dashed var(--line)", borderRadius: 12, background: "var(--surface-2)" }}>
                <Icon name="search" size={22} color="var(--blue)"/>
                <span style={{ fontSize: 12.5 }}>暫無真實預警數據</span>
              </div>
            )}
          </div>
        </div>

        {/* AI 建議卡片 */}
        <div className="col gap-14">
          <div className="row spread"><span className="sec-title">AI 建議事項</span><span className="muted" style={{ fontSize: 12.5 }}>共 {aiTasks.length} 項 · {pendingTasks} 項待人工確認</span></div>
          {aiTasks.length ? aiTasks.map((t,i) => <AICard key={t.id} t={t} idx={i}/>) : (
            <div className="card fade-up" style={{ padding: 18, color: "var(--ink-3)", fontSize: 13 }}>暫無 AI 建議事項</div>
          )}

          {/* AI 邊界 */}
          <div className="card fade-up" style={{ padding: 18, background: "var(--surface-2)" }}>
            <div className="row gap-8" style={{ marginBottom: 10 }}><Icon name="shield" size={17} color="var(--blue)"/><span style={{ fontSize: 13.5, fontWeight: 700 }}>AI 操作邊界 · 受控托管，全程審計</span></div>
            <div className="row gap-20">
              <div className="col gap-6" style={{ flex: 1 }}>
                <span className="eyebrow" style={{ color: "var(--ok)" }}>AI 可以</span>
                {["發現問題 · 分析原因", "推送提醒 · 生成建議", "托管分庫 · 草擬/執行受控動作"].map(t => <span key={t} className="row gap-6" style={{ fontSize: 12, color: "var(--ink-2)" }}><Icon name="check" size={13} color="var(--ok)"/>{t}</span>)}
              </div>
              <div className="col gap-6" style={{ flex: 1 }}>
                <span className="eyebrow" style={{ color: "var(--danger)" }}>AI 不可</span>
                {["任意刪庫/大額出庫", "私自修改權限", "繞過審批 · 替人簽字"].map(t => <span key={t} className="row gap-6" style={{ fontSize: 12, color: "var(--ink-2)" }}><Icon name="x" size={13} color="var(--danger)"/>{t}</span>)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* AI 操作記錄 */}
      <div className="card fade-up" style={{ padding: 0, overflow: "hidden", animationDelay: ".12s" }}>
        <div className="row spread" style={{ padding: "18px 22px 14px" }}><span className="sec-title">AI 操作記錄</span><button className="btn btn-ghost btn-sm" style={{ color: "var(--ink-3)" }} onClick={() => go && go("logs")}>全部日誌</button></div>
        <table className="tbl">
          <thead><tr><th>時間</th><th>AI 發現</th><th>AI 建議</th><th>處理人 / 結果</th><th>是否執行</th></tr></thead>
          <tbody>
            {aiLogs.length ? aiLogs.map((l,i) => (
              <tr key={i}>
                <td className="num muted">{l.time}</td>
                <td style={{ fontWeight: 600, color: "var(--ink)" }}>{l.ai}</td>
                <td className="muted">{l.sug}</td>
                <td>{l.who}</td>
                <td>{l.done ? <span className="badge badge-ok"><Icon name="check" size={12}/>已執行</span> : <span className="badge badge-warn"><span className="dot"/>待確認</span>}</td>
              </tr>
            )) : (
              <tr><td colSpan={5} className="muted" style={{ textAlign: "center", padding: 24 }}>暫無 AI 操作記錄</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const AI_STORAGE = {
  conversation: "mk3.ai.conversationId",
  draft: "mk3.ai.draft",
  category: "mk3.ai.category",
};
const HIST_CH = {
  assistant: { t: "秘書", c: "var(--blue)" }, alerts: { t: "預警", c: "#F59E0B" },
  datahub: { t: "數據", c: "var(--teal)" }, procurement: { t: "招採", c: "#8B5CF6" },
};
const histDayDiff = (s) => { if (!s) return 9999; const d = new Date(String(s).replace(" ", "T") + "Z"); const n = (Date.now() - d.getTime()) / 86400000; return isNaN(n) ? 9999 : n; };
const histBucket = (s) => { const n = histDayDiff(s); return n < 1 ? "今天" : n < 7 ? "近 7 天" : n < 30 ? "近 30 天" : "更早"; };
const HIST_ORDER = ["今天", "近 7 天", "近 30 天", "更早"];

const AICommandCenter = ({ onRefreshHealth }) => {
  const [category, setCategory] = React.useState(() => localStorage.getItem(AI_STORAGE.category) || firstCategoryId());
  const [text, setText] = React.useState(() => localStorage.getItem(AI_STORAGE.draft) || "幫我自查低庫存和待歸還問題");
  const [busy, setBusy] = React.useState(false);
  const [planBusy, setPlanBusy] = React.useState(false);
  const [plan, setPlan] = React.useState(null);
  const [message, setMessage] = React.useState("");
  const [confirming, setConfirming] = React.useState(null);
  const [conversationId, setConversationId] = React.useState(() => Number(localStorage.getItem(AI_STORAGE.conversation)) || null);
  const [conversations, setConversations] = React.useState([]);
  const [histQ, setHistQ] = React.useState("");
  const [histMore, setHistMore] = React.useState(false);
  const [histOpen, setHistOpen] = React.useState(false);   // DeepSeek 式:左上角历史抽屉
  const [toolsOpen, setToolsOpen] = React.useState(false); // 右侧工具面板(默认收起)
  const [messages, setMessages] = React.useState([]);
  const [context, setContext] = React.useState(null);
  const [feedbackTarget, setFeedbackTarget] = React.useState(null);
  const [correction, setCorrection] = React.useState("");
  const [hooks, setHooks] = React.useState([]);
  const [selectedHook, setSelectedHook] = React.useState("");
  const [hookPayload, setHookPayload] = React.useState("{\n  \"confirmed\": false\n}");
  const [hookResult, setHookResult] = React.useState(null);
  const [hookBusy, setHookBusy] = React.useState(false);

  React.useEffect(() => {
    const ids = aiCategories().map((item) => item.id);
    if (ids.length && !ids.includes(category)) setCategory(ids[0]);
    if (!ids.length && category) setCategory("");
  });
  React.useEffect(() => {
    if (category) localStorage.setItem(AI_STORAGE.category, category);
    else localStorage.removeItem(AI_STORAGE.category);
  }, [category]);
  React.useEffect(() => { localStorage.setItem(AI_STORAGE.draft, text); }, [text]);
  React.useEffect(() => {
    if (conversationId) localStorage.setItem(AI_STORAGE.conversation, String(conversationId));
    else localStorage.removeItem(AI_STORAGE.conversation);
  }, [conversationId]);

  const loadConversations = React.useCallback(async (q = "", offset = 0, append = false) => {
    const url = `/api/ai/conversations?limit=30&offset=${offset}` + (q ? `&q=${encodeURIComponent(q)}` : "");
    const result = await aiJson(url);
    const rows = result.rows || [];
    setConversations(prev => append ? [...prev, ...rows] : rows);
    setHistMore(!!result.hasMore);
    return rows;
  }, []);
  // 历史搜索:输入关键词即时检索(去抖)
  React.useEffect(() => {
    const h = setTimeout(() => { loadConversations(histQ.trim()).catch(() => {}); }, 280);
    return () => clearTimeout(h);
  }, [histQ, loadConversations]);

  const loadHooks = React.useCallback(async () => {
    const result = await aiJson("/api/ai/hooks");
    const rows = result.hooks || [];
    setHooks(rows);
    setSelectedHook(prev => prev || rows[0]?.hook_name || "");
    return rows;
  }, []);

  const loadConversation = React.useCallback(async (id) => {
    if (!id) return null;
    try {
      const result = await aiJson(`/api/ai/conversation?id=${encodeURIComponent(id)}`);
      setConversationId(result.conversation.id);
      setMessages(result.messages || []);
      return result;
    } catch (err) {
      if (/not found|不存在|404/i.test(err.message || "")) {
        if (Number(localStorage.getItem(AI_STORAGE.conversation)) === Number(id)) {
          localStorage.removeItem(AI_STORAGE.conversation);
        }
        setConversationId(null);
        setMessages([]);
      }
      throw err;
    }
  }, []);

  const createConversation = React.useCallback(async (title = "新對話") => {
    const result = await aiJson("/api/ai/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    setConversationId(result.conversation.id);
    setMessages(result.messages || []);
    setContext(null);
    await loadConversations();
    onRefreshHealth?.();
    return result;
  }, [loadConversations, onRefreshHealth]);

  React.useEffect(() => {
    let alive = true;
    (async () => {
      try {
        await loadHooks();
        const rows = await loadConversations();
        const saved = Number(localStorage.getItem(AI_STORAGE.conversation)) || null;
        const savedExists = saved && rows.some(row => Number(row.id) === Number(saved));
        if (saved && !savedExists) localStorage.removeItem(AI_STORAGE.conversation);
        const nextId = savedExists ? saved : rows[0]?.id;
        if (!alive) return;
        if (nextId) {
          try {
            await loadConversation(nextId);
          } catch {
            await createConversation("新對話");
          }
        } else {
          await createConversation("新對話");
        }
      } catch (err) {
        setMessage("載入對話記憶失敗：" + err.message);
      }
    })();
    return () => { alive = false; };
  }, [createConversation, loadConversation, loadConversations, loadHooks]);

  const sendChat = async (nextText = text) => {
    const content = (nextText || "").trim();
    if (!content) return;
    setBusy(true);
    setMessage("");
    const tempUserId = `temp-user-${Date.now()}`;
    const tempAssistantId = `temp-assistant-${Date.now()}`;
    const appendAssistantChunk = (chunk) => {
      setMessages(prev => prev.map(msg => msg.id === tempAssistantId ? { ...msg, content: (msg.content || "") + chunk } : msg));
    };
    const patchAssistant = (patch) => {
      setMessages(prev => prev.map(msg => msg.id === tempAssistantId ? { ...msg, ...patch } : msg));
    };
    setMessages(prev => [
      ...prev,
      { id: tempUserId, role: "user", content, metadata: {} },
      { id: tempAssistantId, role: "assistant", content: "", metadata: { source: "stream" } },
    ]);
    setText("");
    localStorage.setItem(AI_STORAGE.draft, "");
    // 統一走內核(/api/agent/run/stream):真的調指令、寫庫、寫審計,而不是只聊天。
    const stepLines = [];
    try {
      const result = await window.agentRunCompat({ conversation_id: conversationId, text: content }, {
        onStep: (ev, phase) => {
          if (phase !== "start") return;
          stepLines.push("▸ " + (ev.command || ev.tool_name || "執行中"));
          patchAssistant({ content: "正在執行：\n" + stepLines.join("\n"), metadata: { source: "agent" } });
        },
      });
      const convId = result.conversation_id || conversationId;
      if (convId) {
        const conv = await aiJson(`/api/ai/conversation?id=${encodeURIComponent(convId)}`);
        setConversationId(conv.conversation.id);
        setMessages(conv.messages || []);
      } else {
        patchAssistant({ content: result.answer || "(本次未產生文字總結)", metadata: { source: "agent" } });
      }
      setContext(null);
      await loadConversations();
      onRefreshHealth?.();
    } catch (err) {
      patchAssistant({ content: "AI 執行失敗：" + err.message, metadata: { source: "error" } });
      setMessage("AI 執行失敗：" + err.message);
    } finally {
      setBusy(false);
    }
  };

  const runPlan = async (nextText = text) => {
    const content = (nextText || "").trim();
    if (!content) return;
    setPlanBusy(true);
    setMessage("");
    try {
      const result = await aiJson("/api/ai/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: content, preferred_category: category }),
      });
      setPlan(result);
      setMessage(result.summary);
      onRefreshHealth?.();
    } catch (err) {
      setMessage("AI 規劃失敗：" + err.message);
    } finally {
      setPlanBusy(false);
    }
  };

  const rebuildIndex = async () => {
    setPlanBusy(true);
    setMessage("");
    try {
      const result = await aiJson("/api/ai/index/rebuild", { method: "POST" });
      setMessage(`索引已重建：${result.documents} 條`);
      onRefreshHealth?.();
    } catch (err) {
      setMessage("索引重建失敗：" + err.message);
    } finally {
      setPlanBusy(false);
    }
  };

  const runPreset = (nextText) => {
    setText(nextText);
    sendChat(nextText);
  };

  const confirmCommand = async (commandId) => {
    setConfirming(commandId);
    try {
      const result = await aiJson("/api/ai/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_id: commandId, expected_return_hours: 24 }),
      });
      setMessage(`已確認生成記錄：${result.transaction_no}`);
      if (window.reloadData) window.reloadData();
      onRefreshHealth?.();
    } catch (err) {
      setMessage("確認未寫入：" + err.message + "。請按提示補充物資型號、地點、數量或歸還時間後再確認。");
    } finally {
      setConfirming(null);
    }
  };

  const submitFeedback = async () => {
    if (!feedbackTarget || !correction.trim()) return;
    setBusy(true);
    try {
      const result = await aiJson("/api/ai/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_id: conversationId,
          message_id: feedbackTarget.id,
          assistant_text: feedbackTarget.content,
          correction_text: correction,
          correction_type: "correction",
        }),
      });
      setContext(prev => ({
        ...(prev || {}),
        lessons: [result.lesson, ...((prev?.lessons || []).filter(item => item.id !== result.lesson.id))],
        memories: [result.memory, ...((prev?.memories || []).filter(item => item.id !== result.memory.id))],
      }));
      setMessage("糾錯已保存為經驗，下次相似問題會優先引用。");
      setFeedbackTarget(null);
      setCorrection("");
      onRefreshHealth?.();
    } catch (err) {
      setMessage("保存糾錯失敗：" + err.message);
    } finally {
      setBusy(false);
    }
  };

  const invokeSelectedHook = async () => {
    if (!selectedHook) return;
    setHookBusy(true);
    setMessage("");
    try {
      let payload = {};
      if (hookPayload.trim()) payload = JSON.parse(hookPayload);
      const result = await aiJson("/api/ai/hooks/invoke", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ hook_name: selectedHook, payload }),
      });
      setHookResult(result);
      setMessage(`${selectedHook}：${result.status}`);
      onRefreshHealth?.();
      if (window.reloadData && result.status === "executed") window.reloadData();
    } catch (err) {
      setHookResult({ error: err.message });
      setMessage("Action 調用失敗：" + err.message);
    } finally {
      setHookBusy(false);
    }
  };

  const activeConversation = conversations.find(item => item.id === conversationId);
  const busyAny = busy || planBusy;

  return (
    <div className="card fade-up" style={{ padding: 0, overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--line)", background: "var(--surface)" }}>
        <div className="row spread" style={{ alignItems: "center", gap: 10 }}>
          <div className="row gap-10" style={{ alignItems: "center", minWidth: 0 }}>
            <button className="btn btn-sm" onClick={() => { setHistOpen(true); loadConversations(histQ.trim()).catch(() => {}); }} title="歷史對話"><Icon name="clock" size={16}/>歷史</button>
            <div className="col" style={{ minWidth: 0 }}>
              <span style={{ fontSize: 15, fontWeight: 800, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 360 }}>{activeConversation?.title || "AI 秘書"}</span>
              <span className="muted" style={{ fontSize: 11 }}>{conversationId ? `對話 #${conversationId} · 已接續上下文` : "全新對話分支"}</span>
            </div>
          </div>
          <div className="row gap-8" style={{ flexShrink: 0 }}>
            <button className="btn btn-sm" onClick={() => setToolsOpen(v => !v)} title="工具 / 上下文 / 文檔" style={toolsOpen ? { background: "var(--blue-soft)", color: "var(--blue)" } : undefined}><Icon name="layers" size={15}/>工具</button>
            <button className="btn btn-primary btn-sm" onClick={() => { createConversation("新對話"); setHistOpen(false); }} disabled={busyAny}><Icon name="plus" size={15}/>新建</button>
          </div>
        </div>
      </div>

      <div style={{ position: "relative", display: "grid", gridTemplateColumns: toolsOpen ? "minmax(0, 1fr) 340px" : "minmax(0, 1fr)", minHeight: 520 }}>
        {histOpen && (
        <div onClick={() => setHistOpen(false)} style={{ position: "absolute", inset: 0, zIndex: 30, background: "rgba(14,26,43,0.28)" }}>
        <div onClick={e => e.stopPropagation()} className="col gap-8" style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 300, maxWidth: "85%", borderRight: "1px solid var(--line)", background: "var(--surface)", boxShadow: "var(--sh-lg)", padding: 12 }}>
          <div className="row spread" style={{ padding: "2px 4px 6px" }}>
            <span className="eyebrow">歷史對話</span>
            <button className="btn btn-primary btn-sm" style={{ height: 24, padding: "0 10px" }} onClick={() => { createConversation("新對話"); setHistOpen(false); }} disabled={busyAny}><Icon name="plus" size={12}/>新話題</button>
          </div>
          <div style={{ position: "relative", marginBottom: 6 }}>
            <Icon name="search" size={14} color="var(--ink-4)" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="input" value={histQ} onChange={e => setHistQ(e.target.value)} placeholder="搜索歷史對話(標題/內容)" style={{ height: 32, paddingLeft: 30, fontSize: 12.5, background: "var(--surface)" }}/>
          </div>
          <div className="col gap-8 scroll-y" style={{ maxHeight: 410, paddingRight: 2 }}>
            {conversations.length === 0 && <span className="muted" style={{ fontSize: 12, padding: 8 }}>{histQ ? "沒有匹配的對話" : "暫無歷史對話"}</span>}
            {(histQ ? [["", conversations]] : HIST_ORDER.map(g => [g, conversations.filter(it => histBucket(it.last_message_at) === g)]).filter(x => x[1].length))
              .map(([grp, items]) => (
                <div key={grp || "all"} className="col gap-6">
                  {grp && <span className="eyebrow" style={{ fontSize: 10.5, paddingLeft: 2 }}>{grp}</span>}
                  {items.map(item => {
                    const ch = HIST_CH[item.channel] || HIST_CH.assistant;
                    return (
                      <button key={item.id} onClick={() => { loadConversation(item.id); setHistOpen(false); }} className="col gap-3"
                        style={{ alignItems: "flex-start", textAlign: "left", padding: 9, borderRadius: 10, border: `1px solid ${item.id === conversationId ? "rgba(27,107,255,0.28)" : "var(--line)"}`, background: item.id === conversationId ? "var(--blue-soft)" : "var(--surface)" }}>
                        <span className="row gap-6" style={{ alignItems: "center", width: "100%" }}>
                          <span style={{ width: 6, height: 6, borderRadius: 2, background: ch.c, flex: "0 0 auto" }}/>
                          <span style={{ fontSize: 12.5, fontWeight: 800, color: item.id === conversationId ? "var(--blue)" : "var(--ink)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{item.title}</span>
                          <span style={{ fontSize: 9.5, fontWeight: 700, color: ch.c, flex: "0 0 auto" }}>{ch.t}</span>
                        </span>
                        {item.snippet && <span className="muted" style={{ fontSize: 11, lineHeight: 1.4 }}>{item.snippet}</span>}
                        <span className="muted num" style={{ fontSize: 10.5 }}>{item.message_count || 0} 條 · {(item.last_message_at || "").slice(5, 16)}</span>
                      </button>
                    );
                  })}
                </div>
              ))}
            {histMore && !histQ && <button className="btn btn-sm" onClick={() => loadConversations("", conversations.length, true)}>載入更多</button>}
          </div>
        </div>
        </div>
        )}

        <div style={{ padding: 16 }} className="col gap-12">
          <div className="scroll-y" style={{ height: 360, padding: 12, borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
            {messages.length === 0 ? (
              <div className="col center" style={{ height: "100%", gap: 10, color: "var(--ink-3)", textAlign: "center" }}>
                <Icon name="sparkle" size={28} color="var(--blue)"/>
                <span style={{ fontSize: 13 }}>開始對話後，AI 會保存上下文並引用本地索引。</span>
              </div>
            ) : messages.map(msg => (
              <ChatMessage key={msg.id} msg={msg} onFeedback={setFeedbackTarget}/>
            ))}
          </div>

          <textarea className="input" value={text} onChange={e => setText(e.target.value)} rows={4}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); } }}
            placeholder="輸入問題或任務，例如：我借用一套設備，明天下午歸還"
            style={{ height: 96, resize: "none", padding: 12, lineHeight: 1.55 }}/>
          <div className="row spread" style={{ gap: 10, flexWrap: "wrap" }}>
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              <button className="btn btn-primary" onClick={() => sendChat()} disabled={busyAny || !text.trim()}><Icon name="sparkle" size={16}/>{busy ? "對話中…" : "發送對話"}</button>
              <button className="btn" onClick={() => runPlan()} disabled={busyAny || !text.trim()}><Icon name="checkCircle" size={15}/>{planBusy ? "規劃中…" : "規劃執行"}</button>
              <button className="btn" onClick={rebuildIndex} disabled={busyAny}><Icon name="refresh" size={15}/>重建索引</button>
            </div>
          </div>
          <div className="row gap-8" style={{ flexWrap: "wrap" }}>
            {["查某個物資的庫存和待歸還", "記住：樣品設備屬於可歸還物資", "幫我自查低庫存和待歸還問題"].map(sample => (
              <button key={sample} className="btn btn-sm" onClick={() => runPreset(sample)} disabled={busyAny} style={{ fontSize: 12 }}>{sample}</button>
            ))}
          </div>
          {message && <div style={{ padding: 12, borderRadius: 10, background: plan?.status === "needs_confirmation" ? "var(--warn-soft)" : "var(--blue-soft)", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.55 }}>{message}</div>}
        </div>

        {toolsOpen && (
        <div style={{ padding: 16, background: "var(--surface-2)", borderLeft: "1px solid var(--line)" }} className="col gap-14 scroll-y">
          <div>
            <div className="eyebrow" style={{ marginBottom: 8 }}>物資分類(對話上下文)</div>
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              {aiCategories().map(item => (
                <button key={item.id} className="btn btn-sm" onClick={() => setCategory(item.id)}
                  style={{ background: category === item.id ? "var(--blue-soft)" : "var(--surface)", color: category === item.id ? "var(--blue)" : "var(--ink-2)" }}>
                  <Icon name={item.icon} size={14}/>{item.label}
                </button>
              ))}
              {!aiCategories().length && <span className="muted" style={{ fontSize: 12 }}>尚未配置物資分類</span>}
            </div>
          </div>
          <ContextPanel context={context}/>
          <div>
            <div className="row spread" style={{ marginBottom: 10 }}>
              <span className="sec-title" style={{ fontSize: 15 }}>安全寫庫計劃</span>
              <span className="badge badge-gray" style={{ height: 20 }}>需確認</span>
            </div>
            <PlanResult plan={plan} onConfirm={confirmCommand} confirming={confirming}/>
          </div>
          <ActionConsole
            hooks={hooks}
            selectedHook={selectedHook}
            setSelectedHook={setSelectedHook}
            hookPayload={hookPayload}
            setHookPayload={setHookPayload}
            hookResult={hookResult}
            hookBusy={hookBusy}
            onInvoke={invokeSelectedHook}
          />
        </div>
        )}
      </div>

      {feedbackTarget && (
        <div style={{ position: "fixed", inset: 0, zIndex: 80, background: "rgba(14,26,43,0.28)", display: "grid", placeItems: "center", padding: 20 }}>
          <div className="card" style={{ width: 520, maxWidth: "100%", padding: 18 }}>
            <div className="row spread" style={{ marginBottom: 12 }}>
              <span style={{ fontSize: 16, fontWeight: 800 }}>保存糾錯經驗</span>
              <button className="btn btn-ghost btn-sm" onClick={() => setFeedbackTarget(null)}><Icon name="x" size={14}/></button>
            </div>
            <div style={{ padding: 10, borderRadius: 10, background: "var(--surface-2)", fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.55, marginBottom: 12, maxHeight: 120, overflow: "auto" }}>{feedbackTarget.content}</div>
            <textarea className="input" value={correction} onChange={e => setCorrection(e.target.value)}
              placeholder="輸入正確規則，例如：樣品設備屬於可歸還物資，借用必須要求歸還時間並生成提醒。"
              style={{ height: 108, resize: "none", padding: 12, lineHeight: 1.55 }}/>
            <div className="row spread" style={{ marginTop: 14 }}>
              <span className="muted" style={{ fontSize: 12 }}>保存後會寫入 lesson 和 memory 索引。</span>
              <button className="btn btn-primary" onClick={submitFeedback} disabled={busy || !correction.trim()}><Icon name="check" size={15}/>保存為經驗</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const ChatMessage = ({ msg, onFeedback }) => {
  if (!msg.content) return null;
  const isUser = msg.role === "user";
  const source = msg.metadata?.source;
  return (
    <div className="row" style={{ justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: 10 }}>
      <div style={{ maxWidth: "78%", padding: "10px 12px", borderRadius: 12, background: isUser ? "var(--blue)" : "var(--surface)", color: isUser ? "#fff" : "var(--ink-2)", border: isUser ? "none" : "1px solid var(--line)", boxShadow: isUser ? "var(--sh-blue)" : "none" }}>
        <div style={{ fontSize: 13, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{msg.content}</div>
        {!isUser && (
          <div className="row spread" style={{ marginTop: 8, gap: 10 }}>
            <span className="muted" style={{ fontSize: 11 }}>{source || "assistant"}</span>
            <button className="btn btn-ghost btn-sm" onClick={() => onFeedback(msg)} style={{ height: 24, padding: "0 8px", fontSize: 11 }}><Icon name="edit" size={12}/>糾錯</button>
          </div>
        )}
      </div>
    </div>
  );
};

const ContextPanel = ({ context }) => {
  if (!context) {
    return (
      <div>
        <div className="row spread" style={{ marginBottom: 10 }}><span className="sec-title" style={{ fontSize: 15 }}>本次引用上下文</span><span className="badge badge-gray" style={{ height: 20 }}>等待</span></div>
        <div className="col center" style={{ minHeight: 180, gap: 10, color: "var(--ink-3)", textAlign: "center", border: "1px solid var(--line)", borderRadius: 12, background: "var(--surface)" }}>
          <Icon name="search" size={24} color="var(--blue)"/>
          <span style={{ fontSize: 12.5 }}>發送對話後顯示索引、記憶和糾錯經驗。</span>
        </div>
      </div>
    );
  }
  const lessons = context.lessons || [];
  const memories = context.memories || [];
  const rows = context.search_results || [];
  const autoActions = context.auto_actions || [];
  return (
    <div>
      <div className="row spread" style={{ marginBottom: 10 }}>
        <span className="sec-title" style={{ fontSize: 15 }}>本次引用上下文</span>
        <span className="badge badge-gray" style={{ height: 20 }}>{lessons.length + memories.length + rows.length + autoActions.length}</span>
      </div>
      <div className="col gap-10 scroll-y" style={{ maxHeight: 248, paddingRight: 2 }}>
        <ContextGroup title="自動 Action" items={autoActions.map((item, idx) => ({
          id: idx,
          title: `${item.hook_name || item.operation} · ${item.status}`,
          body: item.requires_confirmation ? "待自然語言確認後寫庫" : "已由 AI 自動調用",
        }))} color="var(--blue)" bodyKey="body"/>
        <ContextGroup title="糾錯經驗" items={lessons} color="var(--warn)" bodyKey="guidance"/>
        <ContextGroup title="長期記憶" items={memories} color="var(--teal)" bodyKey="content"/>
        <ContextGroup title="資料索引" items={rows} color="var(--blue)" bodyKey="body"/>
        {context.self_check && (
          <div style={{ padding: 10, borderRadius: 10, background: "var(--surface)", border: "1px solid var(--line)" }}>
            <div className="eyebrow" style={{ color: "var(--danger)", marginBottom: 6 }}>系統自查</div>
            <div style={{ fontSize: 12, color: "var(--ink-2)", lineHeight: 1.5 }}>{context.self_check.summary}</div>
          </div>
        )}
      </div>
    </div>
  );
};

const ContextGroup = ({ title, items, color, bodyKey }) => {
  if (!items?.length) return null;
  return (
    <div style={{ padding: 10, borderRadius: 10, background: "var(--surface)", border: "1px solid var(--line)" }}>
      <div className="row spread" style={{ marginBottom: 8 }}>
        <span className="eyebrow" style={{ color }}>{title}</span>
        <span className="num muted" style={{ fontSize: 11 }}>{items.length}</span>
      </div>
      <div className="col gap-7">
        {items.slice(0, 4).map(item => (
          <div key={`${title}-${item.id}`} style={{ fontSize: 12, lineHeight: 1.45, color: "var(--ink-2)" }}>
            <b style={{ color: "var(--ink)" }}>{item.title}</b>
            <div className="muted" style={{ marginTop: 2 }}>{item[bodyKey] || item.body || item.content || item.guidance}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ActionConsole = ({ hooks, selectedHook, setSelectedHook, hookPayload, setHookPayload, hookResult, hookBusy, onInvoke }) => {
  const hook = hooks.find(item => item.hook_name === selectedHook);
  const grouped = hooks.reduce((acc, item) => {
    const key = item.domain || "platform";
    acc[key] = acc[key] || [];
    acc[key].push(item);
    return acc;
  }, {});

  const applyTemplate = (nextHook) => {
    const item = hooks.find(h => h.hook_name === nextHook);
    setSelectedHook(nextHook);
    if (!item) return;
    const base = item.writes_database
      ? { confirmed: false }
      : {};
    if (nextHook === "create_inbound_order") {
      Object.assign(base, { type: "採購入庫", source: "—", handler: "—", lines: [{ name: "樣品物資", qty: 1, unit: "件" }] });
    } else if (nextHook === "create_outbound_order") {
      Object.assign(base, { use: "現場作業", dept: "—", target: "—", lines: [{ name: "樣品物資", qty: 1, unit: "件" }] });
    } else if (nextHook === "create_item") {
      Object.assign(base, { category_id: firstCategoryId(), item_name: "新物資名稱", unit: "件" });
    } else if (nextHook === "save_system_settings") {
      Object.assign(base, { group: "ai", values: { low: true, expire: true, abnormal: true, repair: true, auto: false } });
    } else if (nextHook === "query_inventory") {
      Object.assign(base, { category_id: firstCategoryId() });
    }
    setHookPayload(JSON.stringify(base, null, 2));
  };

  return (
    <div>
      <div className="row spread" style={{ marginBottom: 10 }}>
        <span className="sec-title" style={{ fontSize: 15 }}>平台 Action Console</span>
        <span className="badge badge-gray" style={{ height: 20 }}>{hooks.length}</span>
      </div>
      <div className="col gap-10" style={{ padding: 12, borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface)" }}>
        <select className="input" value={selectedHook} onChange={e => applyTemplate(e.target.value)} style={{ height: 36 }}>
          {Object.entries(grouped).map(([domain, items]) => (
            <optgroup key={domain} label={domain}>
              {items.map(item => <option key={item.hook_name} value={item.hook_name}>{item.hook_name}</option>)}
            </optgroup>
          ))}
        </select>
        {hook && (
          <div className="col gap-6">
            <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{hook.description}</div>
            <div className="row gap-6" style={{ flexWrap: "wrap" }}>
              <span className={"badge " + (hook.writes_database ? "badge-warn" : "badge-ok")} style={{ height: 20 }}>{hook.writes_database ? "寫庫" : "只讀"}</span>
              <span className={"badge " + (hook.requires_confirmation ? "badge-warn" : "badge-gray")} style={{ height: 20 }}>{hook.requires_confirmation ? "需 confirmed=true" : "免確認"}</span>
              <span className="badge badge-gray" style={{ height: 20 }}>{hook.operation}</span>
            </div>
          </div>
        )}
        <textarea className="input" value={hookPayload} onChange={e => setHookPayload(e.target.value)}
          style={{ height: 126, resize: "vertical", padding: 10, fontFamily: "SFMono-Regular, Consolas, monospace", fontSize: 12, lineHeight: 1.45 }}/>
        <button className="btn btn-primary" onClick={onInvoke} disabled={hookBusy || !selectedHook}>
          <Icon name="play" size={15}/>{hookBusy ? "執行中…" : "調用 Action"}
        </button>
        {hookResult && (
          <pre style={{ margin: 0, maxHeight: 180, overflow: "auto", padding: 10, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)", fontSize: 11.5, lineHeight: 1.45, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(hookResult, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
};

const PlanResult = ({ plan, onConfirm, confirming }) => {
  if (!plan) {
    return (
      <div className="col center" style={{ minHeight: 264, gap: 12, color: "var(--ink-3)", textAlign: "center" }}>
        <Icon name="sparkle" size={28} color="var(--blue)"/>
        <span style={{ fontSize: 13 }}>等待 AI 行動計劃</span>
      </div>
    );
  }

  return (
    <div className="col gap-12">
      <div className="row spread">
        <span className="sec-title" style={{ fontSize: 15 }}>計劃 #{plan.plan_id}</span>
        <span className={"badge " + (plan.status === "needs_confirmation" ? "badge-warn" : "badge-ok")}>{plan.status === "needs_confirmation" ? "待確認" : "已完成"}</span>
      </div>
      {plan.steps.map(step => <PlanStep key={step.step_no} step={step} onConfirm={onConfirm} confirming={confirming}/>)}
    </div>
  );
};

const PlanStep = ({ step, onConfirm, confirming }) => {
  const result = step.result || {};
  const rows = result.rows || [];
  const risks = result.risks || [];
  const command = step.operation === "ai_command_parse" ? result : null;
  const commandBlocked = command && (((command.missing_fields || []).length > 0) || ((command.candidate_items || []).length > 0));
  return (
    <div style={{ padding: 12, borderRadius: 10, background: "var(--surface)", border: "1px solid var(--line)" }}>
      <div className="row spread" style={{ gap: 8, marginBottom: 8 }}>
        <div className="row gap-8" style={{ minWidth: 0 }}>
          <span className="num" style={{ width: 20, height: 20, borderRadius: 7, background: "var(--blue-soft)", color: "var(--blue)", display: "grid", placeItems: "center", fontSize: 11, fontWeight: 800, flexShrink: 0 }}>{step.step_no}</span>
          <span style={{ fontSize: 13, fontWeight: 800, color: "var(--ink)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{step.title}</span>
        </div>
        <span className={"badge " + (step.status === "needs_confirmation" ? "badge-warn" : "badge-gray")} style={{ height: 20, fontSize: 10.5 }}>{step.operation}</span>
      </div>

      {rows.length > 0 && (
        <div className="col gap-6">
          {rows.slice(0, 4).map(row => (
            <div key={row.id} style={{ fontSize: 12, lineHeight: 1.45, color: "var(--ink-2)" }}>
              <b>{row.title}</b><div className="muted" style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{row.body}</div>
            </div>
          ))}
        </div>
      )}

      {risks.length > 0 && (
        <div className="col gap-6">
          {risks.slice(0, 4).map(risk => (
            <div key={risk.title} className="row spread" style={{ fontSize: 12 }}>
              <span style={{ fontWeight: 700, color: risk.level === "high" ? "var(--danger)" : "var(--ink-2)" }}>{risk.title}</span>
              <span className="num muted">{risk.count}</span>
            </div>
          ))}
        </div>
      )}

      {command && (
        <div className="col gap-8">
          {[
            ["分類", command.category_id],
            ["動作", command.action_type],
            ["物資", command.item_name],
            ["數量", `${command.quantity || ""}${command.unit || ""}`],
            ["地點", command.work_location],
            ["歸還", command.expected_return_at || "—"],
          ].map(([k, v]) => (
            <div key={k} className="row spread" style={{ fontSize: 12 }}>
              <span className="muted">{k}</span>
              <span className="num" style={{ fontWeight: 700, textAlign: "right" }}>{v || "—"}</span>
            </div>
          ))}
          <div style={{ padding: 10, borderRadius: 9, background: "var(--warn-soft)", color: "var(--ink-2)", fontSize: 12, lineHeight: 1.5 }}>{command.confirmation_prompt}</div>
          <button className="btn btn-primary btn-sm" onClick={() => onConfirm(command.ai_command_id)} disabled={commandBlocked || confirming === command.ai_command_id}>
            <Icon name="check" size={14}/>{commandBlocked ? "需補充信息" : (confirming === command.ai_command_id ? "確認中…" : "確認並生成記錄")}
          </button>
        </div>
      )}

      {!rows.length && !risks.length && !command && (
        <div className="muted" style={{ fontSize: 12, lineHeight: 1.45 }}>{result.summary || result.message || `${result.documents || 0} 條`}</div>
      )}
    </div>
  );
};

const AICard = ({ t, idx }) => {
  const c = AI_COLOR[t.level];
  const auto = t.status === "已自動處理";
  const handled = ["已自動處理", "已確認", "已駁回"].includes(t.status);
  const [busy, setBusy] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [draft, setDraft] = React.useState({ action_suggestion: t.action || "", approver: t.approver || "" });
  const act = (action, body) => {
    if (busy) return;
    setBusy(true);
    aiJson(`/api/ai-tasks/${encodeURIComponent(t.id)}/${action}`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
    })
      .then(() => { if (window.reloadData) window.reloadData(); })
      .catch((e) => alert(e.message || String(e)))
      .finally(() => setBusy(false));
  };
  return (
    <div className="card fade-up" style={{ padding: 18, animationDelay: idx*.05+"s", borderLeft: `4px solid ${c}` }}>
      <div className="row spread" style={{ marginBottom: 12 }}>
        <div className="row gap-12">
          <div style={{ width: 40, height: 40, borderRadius: 11, background: c+"18", color: c, display: "grid", placeItems: "center", flexShrink: 0 }}><Icon name={AI_ICON[t.level]} size={20}/></div>
          <div className="col gap-3">
            <span style={{ fontSize: 14.5, fontWeight: 700 }}>{t.problem}</span>
            <span className="num muted" style={{ fontSize: 12 }}>{t.id} · 影響範圍：{t.scope}</span>
          </div>
        </div>
        <div className="col" style={{ alignItems: "flex-end", gap: 4 }}>
          <span className="badge" style={{ color: c, background: c+"18" }}>置信度 {t.conf}%</span>
          {auto ? <span className="badge badge-ok" style={{ height: 20 }}>已自動處理</span>
            : t.status === "已確認" ? <span className="badge badge-ok" style={{ height: 20 }}>已確認</span>
            : t.status === "已駁回" ? <span className="badge badge-danger" style={{ height: 20 }}>已駁回</span>
            : <span className="badge badge-warn" style={{ height: 20 }}><span className="dot"/>待確認</span>}
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
        <div style={{ padding: 12, borderRadius: 10, background: "var(--surface-2)" }}>
          <div className="eyebrow" style={{ marginBottom: 6 }}>AI 判斷依據</div>
          <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{t.basis}</div>
        </div>
        <div style={{ padding: 12, borderRadius: 10, background: "var(--blue-soft)" }}>
          <div className="eyebrow" style={{ marginBottom: 6, color: "var(--blue)" }}>建議操作</div>
          <div style={{ fontSize: 12.5, color: "var(--ink-2)", lineHeight: 1.5 }}>{t.action}</div>
        </div>
      </div>

      {editing && (
        <div className="col gap-8" style={{ marginBottom: 12, padding: 12, borderRadius: 10, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
          <textarea className="input" rows={2} value={draft.action_suggestion} onChange={(e) => setDraft({ ...draft, action_suggestion: e.target.value })} style={{ height: "auto", padding: 10, resize: "none" }} placeholder="修改建議操作"/>
          <input className="input" value={draft.approver} onChange={(e) => setDraft({ ...draft, approver: e.target.value })} placeholder="審批人"/>
          <div className="row gap-8">
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => { act("edit", draft); setEditing(false); }}>保存修改</button>
            <button className="btn btn-sm" onClick={() => setEditing(false)}>取消</button>
          </div>
        </div>
      )}

      <div className="row spread">
        <span className="muted" style={{ fontSize: 12 }}>需審批：<b style={{ color: "var(--ink-2)" }}>{t.approver}</b></span>
        {!handled && !editing && (
          <div className="row gap-8">
            <button className="btn btn-sm" disabled={busy} onClick={() => act("reject")}>駁回</button>
            <button className="btn btn-sm" disabled={busy} onClick={() => setEditing(true)}>修改</button>
            <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => act("confirm")}><Icon name="forward" size={14}/>{busy ? "處理中…" : "確認並推送"}</button>
          </div>
        )}
      </div>
    </div>
  );
};

window.PageAI = PageAI;
