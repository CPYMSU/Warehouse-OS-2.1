/* ============================================================
   系統設置 — 倉庫 · 物資分類 · AI 規則 · 權限 · 通用（真實資料 + 持久化）
   ============================================================ */
const { useState: useStateSet, useEffect: useEffectSet } = React;

const SETTINGS_API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

const RISK_COLOR = { critical: "#E0245E", high: "#E8830C", normal: "#1B6BFF", low: "#6B7A90" };

async function settingsJson(path, options) {
  const res = await (window.authFetch || fetch)(SETTINGS_API_BASE + path, options);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

const saveSettings = (group, values) =>
  (window.authFetch || fetch)(`${SETTINGS_API_BASE}/api/settings/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ group, values }),
  }).then((r) => r.json());

const saveDeepSeekConfig = (apiKey) =>
  settingsJson("/api/integrations/deepseek/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey }),
  });

const validateDeepSeekConfig = (apiKey) =>
  settingsJson("/api/integrations/deepseek/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(apiKey ? { api_key: apiKey } : {}),
  });

const validateVisionConfig = (apiKey) =>
  settingsJson("/api/integrations/vision/validate", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(apiKey ? { api_key: apiKey } : {}),
  });

const saveVisionConfig = (apiKey) =>
  settingsJson("/api/integrations/vision/save", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ api_key: apiKey }),
  });

const VisionKeySet = () => {
  const [status, setStatus] = useStateSet({});
  const [apiKey, setApiKey] = useStateSet("");
  const [busy, setBusy] = useStateSet("");
  const [result, setResult] = useStateSet(null);
  const [editing, setEditing] = useStateSet(false);
  useEffectSet(() => {
    settingsJson("/api/integrations/vision").then((d) => {
      setStatus(d.vision || {});
    }).catch(() => {});
  }, []);

  const validate = async () => {
    setBusy("validate"); setResult(null);
    try {
      const payload = await validateVisionConfig(apiKey.trim());
      if (payload.vision) setStatus(payload.vision);
      setResult(payload);
    } catch (err) { setResult({ ok: false, error: err.message }); }
    finally { setBusy(""); }
  };

  const save = async () => {
    const key = apiKey.trim();
    if (!key) { setResult({ ok: false, error: "請先輸入 API Key。" }); return; }
    setBusy("save"); setResult(null);
    try {
      const d = await saveVisionConfig(key);
      if (!d.ok) throw new Error(d.error || "保存失敗");
      if (d.vision) setStatus(d.vision);
      setApiKey(""); setEditing(false);
      const check = d.validation || {};
      setResult(check.ok
        ? { ...check, message: "全局密鑰已保存並驗證成功，所有用戶後續都會共用此 key 進行圖片識別。" }
        : { ...check, ok: false, error: "密鑰未保存：" + (check.error || "請檢查 API Key 或網絡。") });
    } catch (err) { setResult({ ok: false, error: err.message }); }
    finally { setBusy(""); }
  };

  const configured = !!status.configured;
  const connection = status.connection || {};
  const connected = configured && !!(status.connected || connection.ok || status.connection_status === "connected");
  const failed = configured && (status.connection_status === "failed" || connection.status === "failed");
  const showEditor = !connected || editing;
  const badgeClass = connected ? "badge-ok" : failed ? "badge-danger" : "badge-warn";
  const badgeText = connected ? "可連接" : failed ? "連接失敗" : configured ? "待驗證" : "未配置";
  const displayModel = connected ? (status.model || connection.model || "—") : "—";
  return (
    <SetCard title="圖片識別全局 API 密鑰"
      sub="只需要管理員配置一次，密鑰保存到系統資料庫；所有用戶共用此 key，不需要每個人單獨註冊"
      action={<span className={`badge ${badgeClass}`} style={{ height: 22 }}>{badgeText}</span>}>
      <div className="col gap-14">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>全局狀態</div>
            <div style={{ fontSize: 12.5, fontWeight: 800, color: connected ? "var(--ok)" : failed ? "var(--danger)" : "var(--warn)" }}>{badgeText}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>共用 Key</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{status.masked_key || "—"}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>當前模型</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800, wordBreak: "break-all" }}>{displayModel}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>最近驗證</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{connection.checked_at || "—"}</div>
          </div>
        </div>

        {connected && (
          <div className="row spread" style={{ padding: 13, borderRadius: 12, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,0.18)" }}>
            <div className="row gap-8" style={{ color: "var(--ok)", fontSize: 13, fontWeight: 800 }}>
              <Icon name="checkCircle" size={16}/>圖片識別連接正常，所有用戶會共用資料庫中的全局 key。
            </div>
            <div className="row gap-6">
              <button className="btn btn-sm" onClick={() => { setEditing(true); setResult(null); }} disabled={!!busy}><Icon name="edit" size={14}/>更換密鑰</button>
              <button className="btn btn-sm" onClick={validate} disabled={!!busy}><Icon name="refresh" size={14}/>{busy === "validate" ? "驗證中…" : "重新驗證"}</button>
            </div>
          </div>
        )}

        {failed && (
          <div style={{ padding: 12, borderRadius: 11, background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid rgba(239,68,68,0.18)", fontSize: 12.5, lineHeight: 1.55 }}>
            連接失敗：{connection.error || "請檢查 API Key、模型權限或服務器網絡。"}
          </div>
        )}

        {showEditor && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 190px", gap: 12, alignItems: "end" }}>
            <label className="col gap-6" style={{ fontSize: 12, color: "var(--ink-3)", fontWeight: 700 }}>
              {configured ? "更新全局 API Key" : "全局 API Key"}
              <input className="input" style={{ fontFamily: "var(--font-mono, monospace)" }} type="password" autoComplete="off"
                placeholder="sk-..." value={apiKey} onChange={(e) => setApiKey(e.target.value)}/>
            </label>
            <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
              <button className="btn" disabled={!!busy || !apiKey.trim()} onClick={validate}><Icon name="checkCircle" size={15}/>{busy === "validate" ? "驗證中…" : "驗證"}</button>
              <button className="btn btn-primary" disabled={!!busy || !apiKey.trim()} onClick={save}><Icon name="shield" size={15}/>{busy === "save" ? "保存中…" : "保存並驗證"}</button>
            </div>
          </div>
        )}

        {result && (
          <div style={{ padding: 12, borderRadius: 11, background: result.ok ? "var(--ok-soft)" : "var(--danger-soft)",
            color: result.ok ? "var(--ok)" : "var(--danger)", border: `1px solid ${result.ok ? "rgba(16,185,129,0.18)" : "rgba(239,68,68,0.18)"}`,
            fontSize: 12.5, lineHeight: 1.55 }}>
            {result.ok ? (result.message || `驗證成功，延遲 ${result.latency_ms || "—"} ms。`) : `驗證失敗：${result.error || "請檢查 API Key 或網絡。"}`}
          </div>
        )}
      </div>
    </SetCard>
  );
};

/* 語音功能全局 API 密鑰 —— 與圖片識別卡完全同款設計,內核換成語音(識別+朗讀),
   保存時後端按 base_url 自動識別 key 類型並配好識別/合成模型。 */
const VoiceKeySet = () => {
  const [status, setStatus] = useStateSet({});
  const [apiKey, setApiKey] = useStateSet("");
  const [busy, setBusy] = useStateSet("");
  const [result, setResult] = useStateSet(null);
  const [editing, setEditing] = useStateSet(false);
  useEffectSet(() => {
    settingsJson("/api/integrations/voice").then((d) => {
      setStatus(d.voice || {});
    }).catch(() => {});
  }, []);

  const validate = async () => {
    setBusy("validate"); setResult(null);
    try {
      const payload = await settingsJson("/api/integrations/voice/validate", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(apiKey.trim() ? { api_key: apiKey.trim() } : {}),
      });
      if (payload.voice) setStatus(payload.voice);
      setResult(payload);
    } catch (err) { setResult({ ok: false, error: err.message }); }
    finally { setBusy(""); }
  };

  const save = async () => {
    const key = apiKey.trim();
    if (!key) { setResult({ ok: false, error: "請先輸入 API Key。" }); return; }
    setBusy("save"); setResult(null);
    try {
      const d = await settingsJson("/api/integrations/voice/save", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: key }),
      });
      if (!d.ok) throw new Error(d.error || "保存失敗");
      if (d.voice) setStatus(d.voice);
      setApiKey(""); setEditing(false);
      const check = d.validation || {};
      setResult(check.ok
        ? { ...check, message: "全局密鑰已保存並驗證成功，所有用戶後續都會共用此 key 進行語音識別與朗讀。" }
        : { ...check, ok: false, error: "密鑰未保存：" + (check.error || "請檢查 API Key 或網絡。") });
    } catch (err) { setResult({ ok: false, error: err.message }); }
    finally { setBusy(""); }
  };

  const configured = !!status.configured;
  const connection = status.connection || {};
  const connected = configured && !!(status.connected || connection.ok || status.connection_status === "connected");
  const failed = configured && (status.connection_status === "failed" || connection.status === "failed");
  const showEditor = !connected || editing;
  const badgeClass = connected ? "badge-ok" : failed ? "badge-danger" : "badge-warn";
  const badgeText = connected ? "可連接" : failed ? "連接失敗" : configured ? "待驗證" : "未配置";
  const displayModel = connected ? (status.model || connection.model || "—") : "—";
  return (
    <SetCard title="語音功能全局 API 密鑰"
      sub="只需要管理員配置一次，密鑰保存到系統資料庫；所有用戶共用此 key 做語音識別與真人感朗讀，未配置時自動降級瀏覽器原生語音"
      action={<span className={`badge ${badgeClass}`} style={{ height: 22 }}>{badgeText}</span>}>
      <div className="col gap-14">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>全局狀態</div>
            <div style={{ fontSize: 12.5, fontWeight: 800, color: connected ? "var(--ok)" : failed ? "var(--danger)" : "var(--warn)" }}>{badgeText}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>共用 Key</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{status.masked_key || "—"}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>當前模型</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800, wordBreak: "break-all" }}>{displayModel}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>最近驗證</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{connection.checked_at || "—"}</div>
          </div>
        </div>

        {connected && (
          <div className="row spread" style={{ padding: 13, borderRadius: 12, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,0.18)" }}>
            <div className="row gap-8" style={{ color: "var(--ok)", fontSize: 13, fontWeight: 800 }}>
              <Icon name="checkCircle" size={16}/>語音功能連接正常，所有用戶會共用資料庫中的全局 key（識別＋朗讀）。
            </div>
            <div className="row gap-6">
              <button className="btn btn-sm" onClick={() => { setEditing(true); setResult(null); }} disabled={!!busy}><Icon name="edit" size={14}/>更換密鑰</button>
              <button className="btn btn-sm" onClick={validate} disabled={!!busy}><Icon name="refresh" size={14}/>{busy === "validate" ? "驗證中…" : "重新驗證"}</button>
            </div>
          </div>
        )}

        {failed && (
          <div style={{ padding: 12, borderRadius: 11, background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid rgba(239,68,68,0.18)", fontSize: 12.5, lineHeight: 1.55 }}>
            連接失敗：{connection.error || "請檢查 API Key 或服務器網絡。"}
          </div>
        )}

        {showEditor && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 190px", gap: 12, alignItems: "end" }}>
            <label className="col gap-6" style={{ fontSize: 12, color: "var(--ink-3)", fontWeight: 700 }}>
              {configured ? "更新全局 API Key" : "全局 API Key"}
              <input className="input" style={{ fontFamily: "var(--font-mono, monospace)" }} type="password" autoComplete="off"
                placeholder="sk-...（保存時自動識別 key 類型並配好識別/合成模型）" value={apiKey} onChange={(e) => setApiKey(e.target.value)}/>
            </label>
            <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
              <button className="btn" disabled={!!busy || !apiKey.trim()} onClick={validate}><Icon name="checkCircle" size={15}/>{busy === "validate" ? "驗證中…" : "驗證"}</button>
              <button className="btn btn-primary" disabled={!!busy || !apiKey.trim()} onClick={save}><Icon name="shield" size={15}/>{busy === "save" ? "保存中…" : "保存並驗證"}</button>
            </div>
          </div>
        )}

        {result && (
          <div style={{ padding: 12, borderRadius: 11, background: result.ok ? "var(--ok-soft)" : "var(--danger-soft)",
            color: result.ok ? "var(--ok)" : "var(--danger)", border: `1px solid ${result.ok ? "rgba(16,185,129,0.18)" : "rgba(239,68,68,0.18)"}`,
            fontSize: 12.5, lineHeight: 1.55 }}>
            {result.ok ? (result.message || `驗證成功，延遲 ${result.latency_ms || "—"} ms。`) : `驗證失敗：${result.error || "請檢查 API Key 或網絡。"}`}
          </div>
        )}
      </div>
    </SetCard>
  );
};

const postJson = (path, body) =>
  settingsJson(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

const downloadDatabaseCsvZip = async (includeViews = false) => {
  const qs = includeViews ? "?include_views=1" : "";
  const res = await (window.authFetch || fetch)(`${SETTINGS_API_BASE}/api/database/export-csv${qs}`);
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.error || res.statusText || "導出失敗");
  }
  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition") || "";
  let filename = "database-csv-export.zip";
  const match = cd.match(/filename\*=UTF-8''([^;]+)/);
  if (match) {
    try { filename = decodeURIComponent(match[1].replace(/"/g, "")); } catch (_) {}
  }
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return { filename, size: blob.size };
};

// 通用編輯浮窗外殼
const SetModal = ({ title, onClose, onSubmit, busy, error, submitLabel, children }) => (
  <div className="center" style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 50, padding: 24 }} onClick={onClose}>
    <form onClick={(e) => e.stopPropagation()} onSubmit={(e) => { e.preventDefault(); onSubmit(); }}
      className="card col gap-14" style={{ width: "min(480px, 100%)", padding: 24, maxHeight: "86vh", overflowY: "auto" }}>
      <div className="row spread"><div style={{ fontSize: 16, fontWeight: 800 }}>{title}</div>
        <button type="button" onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer" }}><Icon name="x" size={18} color="var(--ink-3)"/></button></div>
      {children}
      {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700 }}>⚠ {error}</div>}
      <button className="btn btn-primary" type="submit" disabled={busy} style={{ height: 42 }}>{busy ? "處理中…" : (submitLabel || "保存")}</button>
    </form>
  </div>
);

// 導航設計:AI 依公司行業自動編排側欄(改名/排序/隱藏),可預覽再採用;也支持手動微調
const buildNavGrouped = (catalog, items) => {
  const order = [];
  const byGroup = {};
  catalog.forEach((c, idx) => {
    if (!byGroup[c.group]) { byGroup[c.group] = []; order.push(c.group); }
    const ov = items[c.id] || {};
    byGroup[c.group].push({ ...c, _idx: idx, curLabel: ov.label || c.default_label, hidden: !!ov.hidden, order: ov.order != null ? ov.order : idx });
  });
  return order.map((g) => ({ group: g, items: byGroup[g].slice().sort((a, b) => a.order - b.order) }));
};

const NavDesignSet = () => {
  const [catalog, setCatalog] = useStateSet([]);
  const [cfg, setCfg] = useStateSet({ items: {} });
  const [desc, setDesc] = useStateSet("");
  const [rationale, setRationale] = useStateSet("");
  const [busy, setBusy] = useStateSet("");
  const [msg, setMsg] = useStateSet(null);
  const [dirty, setDirty] = useStateSet(false);

  useEffectSet(() => {
    settingsJson("/api/nav").then((d) => { setCatalog(d.catalog || []); setCfg(d.config && d.config.items ? d.config : { items: {} }); }).catch((e) => setMsg({ ok: false, error: e.message }));
  }, []);

  const grouped = buildNavGrouped(catalog, cfg.items);

  const move = (groupName, id, dir) => {
    const g = grouped.find((x) => x.group === groupName); if (!g) return;
    const arr = g.items.map((i) => i.id);
    const i = arr.indexOf(id); const j = i + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[i], arr[j]] = [arr[j], arr[i]];
    const items = { ...cfg.items };
    arr.forEach((cid, seq) => { items[cid] = { ...(items[cid] || {}), order: seq }; });
    setCfg({ ...cfg, items }); setDirty(true);
  };
  const toggleHide = (id) => {
    if (id === "settings") return;
    const ov = { ...(cfg.items[id] || {}) };
    if (ov.hidden) delete ov.hidden; else ov.hidden = true;
    const items = { ...cfg.items, [id]: ov };
    if (Object.keys(ov).length === 0) delete items[id];
    setCfg({ ...cfg, items }); setDirty(true);
  };
  const setLabel = (id, val, def) => {
    const ov = { ...(cfg.items[id] || {}) };
    const v = (val || "").trim();
    if (!v || v === def) delete ov.label; else ov.label = v.slice(0, 40);
    const items = { ...cfg.items, [id]: ov };
    if (Object.keys(ov).length === 0) delete items[id];
    setCfg({ ...cfg, items }); setDirty(true);
  };
  const aiDesign = () => {
    setBusy("ai"); setMsg(null);
    postJson("/api/nav/ai-design", { description: desc.trim() || undefined })
      .then((d) => {
        setCfg(d.config && d.config.items ? d.config : { items: {} });
        setRationale(d.rationale || "");
        setDirty(true);
        setMsg({ ok: !!d.ai, message: d.ai ? "AI 已生成導航設計,核對下方預覽後點「保存導航」生效。" : (d.rationale || "AI 未生成設計"), error: d.ai ? undefined : (d.rationale || "AI 未生成設計") });
      })
      .catch((e) => setMsg({ ok: false, error: e.message }))
      .finally(() => setBusy(""));
  };
  const save = () => {
    setBusy("save"); setMsg(null);
    postJson("/api/nav/save", { items: cfg.items })
      .then(() => { setDirty(false); setMsg({ ok: true, message: "導航已保存。公司成員下次刷新或重新登入即可看到新導航。" }); })
      .catch((e) => setMsg({ ok: false, error: e.message }))
      .finally(() => setBusy(""));
  };
  const resetDefault = () => { setCfg({ items: {} }); setRationale(""); setDirty(true); setMsg(null); };

  return (
    <>
      <SetCard title="AI 智能設計導航"
        sub="讓 AI 根據你公司的行業與業務,自動把側欄導航重新編排(改名 / 排序 / 隱藏無關頁面)。預覽滿意後保存即生效。"
        action={dirty ? <span className="badge badge-warn" style={{ height: 22 }}>有未保存改動</span> : <span className="badge badge-ok" style={{ height: 22 }}>已是最新</span>}>
        <div className="col gap-12">
          <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink-3)" }}>
            業務補充說明(可選,越具體 AI 設計越貼合)
            <textarea className="input" rows={2} value={desc} onChange={(e) => setDesc(e.target.value)}
              placeholder="例如:我們主要管理門店食材庫存、供應商合同和每日進貨,不需要顯示無關模塊。"/>
          </label>
          <div className="row gap-8" style={{ flexWrap: "wrap" }}>
            <button className="btn btn-primary" disabled={!!busy} onClick={aiDesign}>
              <Icon name="sparkle" size={15}/>{busy === "ai" ? "AI 設計中…" : "讓 AI 設計導航"}
            </button>
            <button className="btn" disabled={!!busy || !dirty} onClick={save}><Icon name="check" size={15}/>{busy === "save" ? "保存中…" : "保存導航"}</button>
            <button className="btn" disabled={!!busy} onClick={resetDefault}><Icon name="refresh" size={15}/>還原默認</button>
          </div>
          {rationale && <div style={{ padding: 11, borderRadius: 10, background: "var(--blue-soft)", color: "var(--blue)", fontSize: 12.5, fontWeight: 700 }}><Icon name="sparkle" size={13}/> {rationale}</div>}
          {msg && <div style={{ fontSize: 12.5, fontWeight: 700, color: msg.ok ? "var(--ok)" : "var(--danger)" }}>{msg.ok ? msg.message : "⚠ " + (msg.error || msg.message)}</div>}
        </div>
      </SetCard>

      <SetCard title="導航預覽與微調" sub="拖動順序由 ↑↓ 控制;可改名、隱藏;「系統設置」受保護不可隱藏。改動需點上方「保存導航」生效。">
        <div className="col gap-16">
          {grouped.map((g) => (
            <div key={g.group} className="col gap-8">
              <div style={{ fontSize: 12, fontWeight: 800, color: "var(--ink-3)", letterSpacing: 1 }}>{g.group}</div>
              {g.items.map((it, idx) => (
                <div key={it.id} className="row gap-8" style={{ alignItems: "center", padding: "8px 10px", borderRadius: 10, border: "1px solid var(--line)", background: it.hidden ? "var(--surface-2)" : "var(--surface)", opacity: it.hidden ? 0.55 : 1 }}>
                  <div className="col gap-2" style={{ flexShrink: 0, width: 36 }}>
                    <button className="btn btn-xs" disabled={idx === 0} onClick={() => move(g.group, it.id, -1)} style={{ height: 18, padding: "0 4px" }}>↑</button>
                    <button className="btn btn-xs" disabled={idx === g.items.length - 1} onClick={() => move(g.group, it.id, 1)} style={{ height: 18, padding: "0 4px" }}>↓</button>
                  </div>
                  <input className="input" style={{ flex: 1, height: 32 }} value={it.curLabel} onChange={(e) => setLabel(it.id, e.target.value, it.default_label)}/>
                  <span className="num muted" style={{ fontSize: 11, width: 92, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{it.id}</span>
                  <button className="btn btn-sm" disabled={it.id === "settings"} onClick={() => toggleHide(it.id)} style={{ flexShrink: 0 }}>
                    {it.hidden ? "顯示" : (it.id === "settings" ? "鎖定" : "隱藏")}
                  </button>
                </div>
              ))}
            </div>
          ))}
          {grouped.length === 0 && <div className="muted" style={{ fontSize: 13 }}>載入導航目錄中…</div>}
        </div>
      </SetCard>
    </>
  );
};

// 「導航與分類」合一:物資分類驅動庫存頁的分類組織,放一起管理。
// 上方管理分類(增刪改);下方設計導航(AI 編排 + 微調)。分類增刪後 bump key 讓導航設計重取目錄,新分類即時出現。
const NavAndCategorySet = ({ data, reload }) => {
  const [navKey, setNavKey] = useStateSet(0);
  const bumpReload = () => { reload && reload(); setNavKey((k) => k + 1); };
  return (
    <>
      <CategorySet data={data} reload={bumpReload}/>
      <NavDesignSet key={navKey}/>
    </>
  );
};

const PageSettings = () => {
  const [tab, setTab] = useStateSet("warehouse");
  const [data, setData] = useStateSet(null);
  const [state, setState] = useStateSet("loading");
  const tabs = [
    { id: "warehouse", label: "倉庫管理", icon: "map2" },
    { id: "nav", label: "導航與分類", icon: "grid" },
    { id: "ai", label: "AI 規則", icon: "cpu" },
    { id: "roles", label: "權限角色", icon: "shield" },
    { id: "general", label: "通用設置", icon: "gear" },
  ];

  const load = () => {
    (window.authFetch || fetch)(`${SETTINGS_API_BASE}/api/settings`)
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then((d) => { setData(d); setState("ok"); })
      .catch(() => setState("error"));
  };
  useEffectSet(() => { load(); }, []);

  return (
    <div className="col gap-18">
      <PageHead title="系統設置" sub="倉庫 · 導航與分類 · AI 規則 · 權限角色 · 通用"/>
      {state === "error" && <div className="card" style={{ padding: 16, color: "var(--danger)", fontSize: 13 }}>無法連接設置服務，請確認 AI 服務 {SETTINGS_API_BASE} 已啟動。</div>}
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 18, alignItems: "flex-start" }}>
        <div className="card fade-up" style={{ padding: 8, position: "sticky", top: 0 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} className="row gap-10" style={{ width: "100%", height: 42, padding: "0 12px", borderRadius: 10, fontSize: 13.5, fontWeight: 600, textAlign: "left",
              color: tab === t.id ? "var(--blue)" : "var(--ink-2)", background: tab === t.id ? "var(--blue-soft)" : "transparent" }}>
              <Icon name={t.icon} size={17}/>{t.label}
            </button>
          ))}
        </div>

        <div className="col gap-18" key={tab}>
          {tab === "warehouse" && <WarehouseSet data={data} reload={load}/>}
          {tab === "nav" && <NavAndCategorySet data={data} reload={load}/>}
          {tab === "ai" && <AIRuleSet data={data}/>}
          {tab === "roles" && <RoleSet data={data} reload={load}/>}
          {tab === "general" && <GeneralSet data={data}/>}
        </div>
      </div>
    </div>
  );
};

const SetCard = ({ title, sub, children, action }) => (
  <div className="card fade-up" style={{ padding: 22 }}>
    <SecHead title={title} sub={sub} right={action}/>
    {children}
  </div>
);

const WarehouseModal = ({ initial, onClose, reload }) => {
  const editing = !!(initial && initial.id);
  const [f, setF] = useStateSet({ name: initial?.name || "", code: initial?.code || "", capacity_usage: initial?.cap ?? "" });
  const [busy, setBusy] = useStateSet(false);
  const [error, setError] = useStateSet("");
  const submit = () => {
    if (!f.name.trim()) { setError("請填寫倉庫名稱"); return; }
    setBusy(true); setError("");
    const body = { name: f.name.trim(), code: f.code || null, capacity_usage: f.capacity_usage === "" ? null : Number(f.capacity_usage) };
    postJson(editing ? `/api/warehouses/${initial.id}` : "/api/warehouses", body)
      .then(() => { reload && reload(); onClose(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };
  return (
    <SetModal title={editing ? "編輯倉庫" : "新增倉庫"} onClose={onClose} onSubmit={submit} busy={busy} error={error}>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>倉庫名稱
        <input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })}/></label>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>倉庫編碼
        <input className="input" value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} placeholder="例如:WH-01"/></label>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>容量使用率(%)
        <input className="input" type="number" min="0" max="100" value={f.capacity_usage} onChange={(e) => setF({ ...f, capacity_usage: e.target.value })}/></label>
    </SetModal>
  );
};

const WarehouseSet = ({ data, reload }) => {
  const whInfo = (data && data.warehouses) || [];
  const totalZones = whInfo.reduce((s, w) => s + (w.zones || 0), 0);
  const [modal, setModal] = useStateSet(null); // null | {} (新增) | row (編輯)
  const [busyId, setBusyId] = useStateSet(null);
  const [error, setError] = useStateSet("");
  const remove = (w) => {
    if (busyId) return;
    if (w.can_delete === false) { setError(w.delete_hint || "默認倉庫不能刪除"); return; }
    if (!window.confirm(`刪除倉庫「${w.name}」?\n${w.delete_hint || "無關聯數據將直接刪除;若有庫存/被引用則改為停用。"}`)) return;
    setBusyId(w.id); setError("");
    postJson(`/api/warehouses/${w.id}/delete`, {})
      .then(() => { reload && reload(); if (window.reloadData) window.reloadData(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusyId(null));
  };
  return (
    <SetCard title="倉庫管理" sub={`${whInfo.length} 個倉庫 · ${totalZones} 個功能區`} action={<button className="btn btn-primary btn-sm" onClick={() => setModal({})}><Icon name="plus" size={15}/>新增倉庫</button>}>
      {modal && <WarehouseModal initial={modal} onClose={() => setModal(null)} reload={reload}/>}
      {error && <div style={{ color: "var(--danger)", fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{error}</div>}
      <div className="col gap-12">
        {whInfo.map((w, i) => (
          <div key={i} className="row spread" style={{ padding: 16, borderRadius: 13, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
            <div className="row gap-14">
              <div style={{ width: 44, height: 44, borderRadius: 12, background: "var(--grad-soft)", color: "var(--blue)", display: "grid", placeItems: "center" }}><Icon name="map2" size={22}/></div>
              <div className="col gap-3">
                <span className="row gap-8" style={{ fontSize: 14.5, fontWeight: 700 }}>{w.name}{w.main && <span className="badge badge-info" style={{ height: 19, fontSize: 10.5 }}>默認庫</span>}</span>
                <span className="num muted" style={{ fontSize: 12 }}>{w.code} · {w.zones} 個功能區</span>
              </div>
            </div>
            <div className="row gap-20">
              <div className="col" style={{ alignItems: "flex-end", gap: 4, width: 120 }}>
                <span className="muted" style={{ fontSize: 11 }}>容量使用率 {w.cap}%</span>
                <div style={{ width: "100%", height: 6, borderRadius: 3, background: "#E5EAF1", overflow: "hidden" }}><div style={{ height: "100%", width: w.cap + "%", background: "var(--grad)" }}/></div>
              </div>
              <button className="btn btn-sm" onClick={() => setModal(w)}><Icon name="edit" size={14}/>編輯</button>
              <button className="btn btn-sm" disabled={!!busyId || w.can_delete === false} title={w.can_delete === false ? (w.delete_hint || "默認倉庫不能刪除") : (w.delete_hint || "刪除倉庫")} style={{ color: "var(--danger)" }} onClick={() => remove(w)}>{busyId === w.id ? "刪除中..." : "刪除"}</button>
            </div>
          </div>
        ))}
      </div>
    </SetCard>
  );
};

const CategoryModal = ({ onClose, reload, editing }) => {
  const isEdit = !!editing;
  const [f, setF] = useStateSet({ id: editing?.id || "", name: editing?.name || "", requires_return: !!editing?.requires_return, description: editing?.description || "" });
  const [busy, setBusy] = useStateSet(false);
  const [error, setError] = useStateSet("");
  const submit = () => {
    if ((!isEdit && !f.id.trim()) || !f.name.trim()) { setError("分類代碼與名稱均必填"); return; }
    setBusy(true); setError("");
    const path = isEdit ? `/api/categories/${editing.id}` : "/api/categories";
    const body = isEdit
      ? { name: f.name.trim(), requires_return: f.requires_return, description: f.description || null }
      : { id: f.id.trim(), name: f.name.trim(), requires_return: f.requires_return, description: f.description || null };
    postJson(path, body)
      .then(() => { reload && reload(); if (window.reloadData) window.reloadData(); onClose(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };
  return (
    <SetModal title={isEdit ? "編輯物資分類" : "新增物資分類"} onClose={onClose} onSubmit={submit} busy={busy} error={error}>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>分類代碼(小寫字母/數字/下劃線)
        <input className="input" value={f.id} disabled={isEdit} onChange={(e) => setF({ ...f, id: e.target.value })} placeholder="例如:spare_parts" style={isEdit ? { opacity: 0.6 } : undefined}/></label>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>分類名稱
        <input className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} placeholder="例如:備品備件"/></label>
      <label className="row gap-10" style={{ fontSize: 13, fontWeight: 700, alignItems: "center" }}>
        <input type="checkbox" checked={f.requires_return} onChange={(e) => setF({ ...f, requires_return: e.target.checked })}/>借用後需歸還(生成歸還提醒)</label>
      <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>說明
        <textarea className="input" rows={2} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} style={{ height: "auto", padding: 12, resize: "none" }}/></label>
      <div className="muted" style={{ fontSize: 11.5 }}>新增後會出現在「庫存管理」的分類標籤和出入庫的分類選項中。</div>
    </SetModal>
  );
};

const CategorySet = ({ data, reload }) => {
  const cats = (data && data.ledger_categories) || [];
  const [modal, setModal] = useStateSet(null); // "new" | 分類對象(編輯) | null
  const [busyId, setBusyId] = useStateSet("");
  const [err, setErr] = useStateSet("");
  const del = async (c) => {
    if (!window.confirm(`刪除分類「${c.name}」?該分類在庫存中的標籤會一併移除。`)) return;
    setBusyId(c.id); setErr("");
    const post = (force) => (window.authFetch || fetch)(`${SETTINGS_API_BASE}/api/categories/${c.id}/delete`,
      { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(force ? { force: true } : {}) });
    try {
      let res = await post(false);
      if (res.status === 409) {
        const data = await res.json().catch(() => ({}));
        // 分類下還有物資/出入庫/台賬數據 → 詢問是否強制清空並刪除
        if (window.confirm(`${data.error || "該分類下還有數據"}\n\n確定要「強制清空並刪除」嗎?這會一併刪除該分類下的所有物資、出入庫與台賬記錄,且不可恢復。`)) {
          res = await post(true);
        } else {
          setBusyId(""); return;
        }
      }
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || res.statusText);
      reload && reload(); if (window.reloadData) window.reloadData();
    } catch (e) {
      setErr(e.message || String(e));
    } finally { setBusyId(""); }
  };
  return (
    <SetCard title="物資分類" sub={`${cats.length} 個功能分類 · 驅動台賬與 AI`} action={<button className="btn btn-primary btn-sm" onClick={() => setModal("new")}><Icon name="plus" size={15}/>新增分類</button>}>
      {modal && <CategoryModal onClose={() => setModal(null)} reload={reload} editing={modal === "new" ? null : modal}/>}
      {err && <div style={{ color: "var(--danger)", fontSize: 12.5, fontWeight: 700, marginBottom: 8 }}>⚠ {err}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 12 }}>
        {cats.length === 0 && <span className="muted" style={{ fontSize: 13 }}>暫無分類。點「新增分類」建立第一個。</span>}
        {cats.map((c, i) => (
          <div key={i} className="row spread" style={{ padding: 14, borderRadius: 12, border: "1px solid var(--line)" }}>
            <span className="col gap-3" style={{ minWidth: 0 }}>
              <span style={{ fontSize: 13.5, fontWeight: 600 }}>{c.name}</span>
              <span className="num muted" style={{ fontSize: 11 }}>{c.id}</span>
            </span>
            <span className="row gap-6" style={{ alignItems: "center" }}>
              <span className={`badge ${c.requires_return ? "badge-warn" : "badge-gray"}`} style={{ height: 20 }}>{c.requires_return ? "需歸還" : "消耗"}</span>
              <button className="btn btn-sm" onClick={() => setModal(c)}>編輯</button>
              <button className="btn btn-sm" disabled={busyId === c.id} style={{ color: "var(--danger)" }} onClick={() => del(c)}>刪除</button>
            </span>
          </div>
        ))}
      </div>
    </SetCard>
  );
};

const Toggle = ({ on, onToggle }) => (
  <button onClick={onToggle} style={{ width: 44, height: 26, borderRadius: 13, background: on ? "var(--grad)" : "#D5DCE6", position: "relative", transition: "background .2s", flexShrink: 0 }}>
    <span style={{ position: "absolute", top: 3, left: on ? 21 : 3, width: 20, height: 20, borderRadius: "50%", background: "#fff", boxShadow: "0 1px 3px rgba(0,0,0,0.2)", transition: "left .2s" }}/>
  </button>
);

const SavedTip = ({ show }) => show ? <span className="badge badge-ok" style={{ height: 22 }}><Icon name="check" size={12}/>已保存</span> : null;

const DeepSeekKeySet = ({ initial }) => {
  const [status, setStatus] = useStateSet(initial || {});
  const [apiKey, setApiKey] = useStateSet("");
  const [busy, setBusy] = useStateSet("");
  const [result, setResult] = useStateSet(null);
  const [editing, setEditing] = useStateSet(false);

  useEffectSet(() => { if (initial) setStatus(initial); }, [initial]);

  const validate = async () => {
    setBusy("validate");
    setResult(null);
    try {
      const payload = await validateDeepSeekConfig(apiKey.trim());
      if (payload.deepseek) setStatus(payload.deepseek);
      setResult(payload);
    } catch (err) {
      setResult({ ok: false, error: err.message });
    } finally {
      setBusy("");
    }
  };

  const save = async () => {
    const key = apiKey.trim();
    if (!key) {
      setResult({ ok: false, error: "請先輸入 API Key。" });
      return;
    }
    setBusy("save");
    setResult(null);
    try {
      const payload = await saveDeepSeekConfig(key);
      setStatus(payload.deepseek || {});
      setApiKey(""); setEditing(false);
      const check = payload.validation || {};
      setResult(check.ok
        ? { ...check, message: "全局密鑰已保存並驗證成功，所有用戶後續都會共用此 key 調用智能引擎。" }
        : { ...check, ok: false, error: "密鑰已保存，但驗證失敗：" + (check.error || "請檢查 API Key 或網絡。") }
      );
    } catch (err) {
      setResult({ ok: false, error: err.message });
    } finally {
      setBusy("");
    }
  };

  const configured = !!status.configured;
  const connected = configured && !!(status.connected || status.connection?.ok || status.connection_status === "connected");
  const failed = configured && (status.connection_status === "failed" || status.connection?.status === "failed");
  const showEditor = !connected || editing;
  const connection = status.connection || {};
  const badgeClass = connected ? "badge-ok" : failed ? "badge-danger" : "badge-warn";
  const badgeText = connected ? "可連接" : failed ? "連接失敗" : configured ? "待驗證" : "未配置";
  return (
    <SetCard
      title="智能引擎 API 密鑰"
      sub="只需要管理員配置一次，密鑰保存到系統資料庫；所有用戶共用此 key，不需要每個人單獨註冊"
      action={<span className={`badge ${badgeClass}`} style={{ height: 22 }}>{badgeText}</span>}
    >
      <div className="col gap-14">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 10 }}>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>全局狀態</div>
            <div style={{ fontSize: 12.5, fontWeight: 800, color: connected ? "var(--ok)" : failed ? "var(--danger)" : "var(--warn)" }}>{badgeText}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>共用 Key</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{status.masked_key || "—"}</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>當前引擎</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>智能引擎</div>
          </div>
          <div style={{ padding: 11, borderRadius: 10, background: "var(--surface-2)", border: "1px solid var(--line)" }}>
            <div className="muted" style={{ fontSize: 11.5, marginBottom: 4 }}>最近驗證</div>
            <div className="num" style={{ fontSize: 12.5, fontWeight: 800 }}>{connection.checked_at || status.updated_at || "—"}</div>
          </div>
        </div>

        {connected && (
          <div className="row spread" style={{ padding: 13, borderRadius: 12, background: "var(--ok-soft)", border: "1px solid rgba(16,185,129,0.18)" }}>
            <div className="row gap-8" style={{ color: "var(--ok)", fontSize: 13, fontWeight: 800 }}>
              <Icon name="checkCircle" size={16}/>智能引擎連接正常，所有用戶會共用資料庫中的全局 key。
            </div>
            <div className="row gap-6">
              <button className="btn btn-sm" onClick={() => { setEditing(true); setResult(null); }} disabled={!!busy}><Icon name="edit" size={14}/>更換密鑰</button>
              <button className="btn btn-sm" onClick={validate} disabled={!!busy}><Icon name="refresh" size={14}/>{busy === "validate" ? "驗證中…" : "重新驗證"}</button>
            </div>
          </div>
        )}

        {failed && (
          <div style={{ padding: 12, borderRadius: 11, background: "var(--danger-soft)", color: "var(--danger)", border: "1px solid rgba(239,68,68,0.18)", fontSize: 12.5, lineHeight: 1.55 }}>
            連接失敗：{connection.error || "請檢查 API Key、餘額、模型權限或服務器網絡。"}
          </div>
        )}

        {showEditor && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 190px", gap: 12, alignItems: "end" }}>
            <label className="col gap-6" style={{ fontSize: 12, color: "var(--ink-3)", fontWeight: 700 }}>
              {configured ? "更新全局 API Key" : "全局 API Key"}
              <input
                className="input"
                type="password"
                autoComplete="off"
                value={apiKey}
                onChange={e => setApiKey(e.target.value)}
                placeholder="sk-..."
                style={{ fontFamily: "var(--font-mono, monospace)" }}
              />
            </label>
            <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
              <button className="btn" onClick={validate} disabled={!!busy || !apiKey.trim()}>
                <Icon name="checkCircle" size={15}/>{busy === "validate" ? "驗證中…" : "驗證輸入"}
              </button>
              <button className="btn btn-primary" onClick={save} disabled={!!busy || !apiKey.trim()}>
                <Icon name="shield" size={15}/>{busy === "save" ? "保存中…" : "保存並驗證"}
              </button>
            </div>
          </div>
        )}

        {result && (
          <div style={{
            padding: 12,
            borderRadius: 11,
            background: result.ok ? "var(--ok-soft)" : "var(--danger-soft)",
            color: result.ok ? "var(--ok)" : "var(--danger)",
            border: `1px solid ${result.ok ? "rgba(16,185,129,0.18)" : "rgba(239,68,68,0.18)"}`,
            fontSize: 12.5,
            lineHeight: 1.55,
          }}>
            {result.ok
              ? (result.message || `驗證成功，延遲 ${result.latency_ms || "—"} ms。`)
              : `驗證失敗：${result.error || "請檢查 API Key 或網絡。"}`
            }
          </div>
        )}
      </div>
    </SetCard>
  );
};

const AIRuleSet = ({ data }) => {
  const [rules, setRules] = useStateSet(null);
  const [saved, setSaved] = useStateSet(false);
  useEffectSet(() => { if (data && data.ai_rules) setRules(data.ai_rules); }, [data]);
  const items = [
    { k: "low", t: "低庫存自動預警", d: "庫存低於安全庫存時自動生成預警並推送倉管" },
    { k: "expire", t: "超期未檢提醒", d: "距檢驗到期 ≤15 天自動推送計量班" },
    { k: "abnormal", t: "異常出庫檢測", d: "出庫頻率超正常波動 3σ 觸發盤點建議" },
    { k: "repair", t: "應急缺口預測", d: "結合關聯地點與需求記錄預測應急物資缺口" },
    { k: "auto", t: "AI 自動草擬單據", d: "AI 可自動草擬補貨/調撥單(高風險仍進覆核)" },
    { k: "gis", t: "AI 托管分庫", d: "AI 可根據庫存資料整理倉庫、庫區與庫位關聯" },
  ];
  const toggle = (k) => {
    const next = { ...rules, [k]: !rules[k] };
    setRules(next);
    saveSettings("ai_rules", next).then(() => { setSaved(true); setTimeout(() => setSaved(false), 1500); });
  };
  if (!rules) return <SetCard title="AI 監測規則" sub="載入中…"><div/></SetCard>;
  return (
    <>
      <DeepSeekKeySet initial={data?.deepseek}/>
      <VisionKeySet/>
      <VoiceKeySet/>
      <SetCard title="AI 監測規則" sub="AI 受控托管,全程審計" action={<SavedTip show={saved}/>}>
        <div className="col gap-12">
          {items.map(it => (
            <div key={it.k} className="row spread" style={{ padding: 16, borderRadius: 12, border: "1px solid var(--line)", background: rules[it.k] ? "var(--surface-2)" : "var(--surface)" }}>
              <div className="col gap-3" style={{ flex: 1 }}>
                <span style={{ fontSize: 13.5, fontWeight: 700 }}>{it.t}</span>
                <span className="muted" style={{ fontSize: 12 }}>{it.d}</span>
              </div>
              <Toggle on={rules[it.k]} onToggle={() => toggle(it.k)}/>
            </div>
          ))}
        </div>
      </SetCard>
      <SetCard title="AI 操作邊界" sub="不可逾越的安全紅線">
        <div className="row gap-12" style={{ flexWrap: "wrap" }}>
          {["禁止任意刪庫", "禁止自動大額出庫", "禁止私自改權限", "禁止繞過審批", "禁止替人簽字"].map(t => (
            <span key={t} className="badge badge-danger" style={{ height: 30 }}><Icon name="shield" size={13}/>{t}</span>
          ))}
        </div>
      </SetCard>
    </>
  );
};

const RoleModal = ({ initial, onClose, reload }) => {
  const editing = !!(initial && initial.id);
  const [name, setName] = useStateSet(initial?.name || "");
  const [level, setLevel] = useStateSet(initial?.level || 3);
  const [color, setColor] = useStateSet(initial?.color || "#1B6BFF");
  const [perms, setPerms] = useStateSet(new Set(initial?.perms || []));
  const [allPerms, setAllPerms] = useStateSet([]);
  const [busy, setBusy] = useStateSet(false);
  const [error, setError] = useStateSet("");
  useEffectSet(() => {
    settingsJson("/api/permissions").then((d) => setAllPerms(d.permissions || [])).catch(() => setAllPerms([]));
  }, []);
  const togglePerm = (k) => { const n = new Set(perms); n.has(k) ? n.delete(k) : n.add(k); setPerms(n); };
  const toggleGroup = (items, on) => { const n = new Set(perms); items.forEach((p) => on ? n.add(p.key) : n.delete(p.key)); setPerms(n); };
  const permGroups = React.useMemo(() => {
    const order = []; const map = {};
    allPerms.forEach((p) => { const g = p.group || "其他"; if (!map[g]) { map[g] = []; order.push(g); } map[g].push(p); });
    return order.map((name) => ({ name, items: map[name] }));
  }, [allPerms]);
  const submit = () => {
    if (!name.trim()) { setError("請填寫角色名稱"); return; }
    setBusy(true); setError("");
    const body = { role_name: name.trim(), level: Number(level) || 3, color, permissions: Array.from(perms) };
    postJson(editing ? `/api/roles/${initial.id}` : "/api/roles", body)
      .then(() => { reload && reload(); onClose(); })
      .catch((e) => setError(e.message || String(e))).finally(() => setBusy(false));
  };
  return (
    <SetModal title={editing ? "配置角色" : "新增角色"} onClose={onClose} onSubmit={submit} busy={busy} error={error}>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 80px 80px", gap: 10 }}>
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>角色名稱
          <input className="input" value={name} onChange={(e) => setName(e.target.value)}/></label>
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>等級
          <input className="input" type="number" min="1" max="10" value={level} onChange={(e) => setLevel(e.target.value)}/></label>
        <label className="col gap-6" style={{ fontSize: 12.5, fontWeight: 700 }}>顏色
          <input className="input" type="color" value={color} onChange={(e) => setColor(e.target.value)} style={{ padding: 2, height: 38 }}/></label>
      </div>
      <div className="col gap-6">
        <span style={{ fontSize: 12.5, fontWeight: 700 }}>權限與 CLI 能力({perms.size} 項)</span>
        <div className="col gap-10" style={{ maxHeight: 300, overflowY: "auto", border: "1px solid var(--line)", borderRadius: 10, padding: 10 }}>
          {permGroups.map((grp) => {
            const allOn = grp.items.every((p) => perms.has(p.key));
            return (
              <div key={grp.name} className="col gap-4">
                <div className="row spread" style={{ alignItems: "center" }}>
                  <span style={{ fontSize: 11.5, fontWeight: 800, color: "var(--muted)", letterSpacing: .3 }}>{grp.name}</span>
                  <button type="button" className="btn btn-xs" style={{ fontSize: 10.5, padding: "2px 8px" }}
                    onClick={() => toggleGroup(grp.items, !allOn)}>{allOn ? "清空本組" : "全選本組"}</button>
                </div>
                {grp.items.map((p) => (
                  <label key={p.key} className="row gap-8" style={{ fontSize: 12.5, alignItems: "center", cursor: "pointer" }}>
                    <input type="checkbox" checked={perms.has(p.key)} onChange={() => togglePerm(p.key)}/>
                    <span style={{ fontWeight: 600 }}>{p.description}</span>
                    {p.risk && p.risk !== "normal" && p.risk !== "low" && (
                      <span className="badge" style={{ height: 17, fontSize: 9.5, color: RISK_COLOR[p.risk], background: RISK_COLOR[p.risk] + "1c" }}>
                        {p.risk === "critical" ? "致命" : "高危"}</span>
                    )}
                    <span className="num muted" style={{ fontSize: 10.5 }}>{p.key}</span>
                  </label>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </SetModal>
  );
};

const RoleSet = ({ data, reload }) => {
  const roles = (data && data.roles) || [];
  const [modal, setModal] = useStateSet(null);
  const [permMeta, setPermMeta] = useStateSet({});
  useEffectSet(() => {
    settingsJson("/api/permissions").then((d) => {
      const m = {}; (d.permissions || []).forEach((p) => { m[p.key] = p; }); setPermMeta(m);
    }).catch(() => setPermMeta({}));
  }, []);
  return (
    <SetCard title="權限角色" sub={`${roles.length} 類角色 · 分級授權 · 高危能力一眼可見`} action={<button className="btn btn-primary btn-sm" onClick={() => setModal({})}><Icon name="plus" size={15}/>新增角色</button>}>
      {modal && <RoleModal initial={modal} onClose={() => setModal(null)} reload={reload}/>}
      <div className="col gap-12">
        {roles.map((r, i) => {
          const perms = r.perms || [];
          const cli = perms.filter((p) => permMeta[p] && permMeta[p].kind === "cli")
            .map((p) => permMeta[p])
            .sort((a, b) => (b.critical ? 1 : 0) - (a.critical ? 1 : 0));
          const bizCount = perms.filter((p) => !permMeta[p] || permMeta[p].kind !== "cli").length;
          return (
            <div key={i} className="row spread" style={{ padding: 16, borderRadius: 13, border: "1px solid var(--line)" }}>
              <div className="row gap-14" style={{ alignItems: "flex-start" }}>
                <div style={{ width: 40, height: 40, borderRadius: 11, background: r.color + "1c", color: r.color, display: "grid", placeItems: "center", flexShrink: 0 }}><Icon name="shield" size={20}/></div>
                <div className="col gap-6">
                  <span className="row gap-8" style={{ fontSize: 14, fontWeight: 700 }}>{r.name}<span className="badge" style={{ height: 19, fontSize: 10.5, color: r.color, background: r.color + "18" }}>L{r.level}</span></span>
                  <div className="row gap-6" style={{ flexWrap: "wrap", alignItems: "center" }}>
                    <span className="badge badge-gray" style={{ height: 19, fontSize: 10.5 }}>業務權限 {bizCount} 項</span>
                    {cli.map((p) => (
                      <span key={p.key} className="badge" title={p.key}
                        style={{ height: 19, fontSize: 10.5, color: RISK_COLOR[p.risk] || RISK_COLOR.normal, background: (RISK_COLOR[p.risk] || RISK_COLOR.normal) + "18", fontWeight: 700 }}>
                        {p.critical ? "⚠ " : ""}{p.description}</span>
                    ))}
                    {cli.length === 0 && <span className="num muted" style={{ fontSize: 10.5 }}>無 CLI 高危能力</span>}
                  </div>
                </div>
              </div>
              <button className="btn btn-sm" onClick={() => setModal(r)} style={{ flexShrink: 0 }}><Icon name="edit" size={14}/>配置</button>
            </div>
          );
        })}
      </div>
    </SetCard>
  );
};

const DatabaseExportSet = () => {
  const [includeViews, setIncludeViews] = useStateSet(false);
  const [busy, setBusy] = useStateSet(false);
  const [msg, setMsg] = useStateSet(null);
  const download = async () => {
    if (busy) return;
    if (!window.confirm("將導出當前公司完整資料庫表為 CSV 壓縮包,可能包含用戶、權限、Token、審計日誌等敏感資料。確定繼續?")) return;
    setBusy(true);
    setMsg(null);
    try {
      const result = await downloadDatabaseCsvZip(includeViews);
      setMsg({ ok: true, message: `已生成下載:${result.filename} (${Math.max(1, Math.round(result.size / 1024))} KB)` });
    } catch (err) {
      setMsg({ ok: false, error: err.message || String(err) });
    } finally {
      setBusy(false);
    }
  };
  return (
    <SetCard title="資料庫 CSV 導出" sub="將當前公司租戶庫導出為 zip:每張表一個 UTF-8 CSV,並附帶 schema.sql 和 manifest.json。">
      <div className="col gap-12">
        <div className="row spread" style={{ gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <label className="row gap-8" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--ink-3)", alignItems: "center" }}>
            <input type="checkbox" checked={includeViews} onChange={(e) => setIncludeViews(e.target.checked)}/>
            同時導出視圖 CSV
          </label>
          <button className="btn btn-primary" disabled={busy} onClick={download}>
            <Icon name="outbound" size={15}/>{busy ? "正在打包…" : "下載 CSV 壓縮包"}
          </button>
        </div>
        <div style={{ padding: 12, borderRadius: 11, background: "var(--warn-soft, rgba(245,158,11,0.10))", color: "var(--warn)", border: "1px solid rgba(245,158,11,0.20)", fontSize: 12.5, lineHeight: 1.55 }}>
          完整導出包含敏感表,例如用戶、角色、Token、審計日誌和 AI 對話記錄。下載後請按內部數據安全要求保存和傳輸。
        </div>
        {msg && <div style={{ fontSize: 12.5, fontWeight: 700, color: msg.ok ? "var(--ok)" : "var(--danger)" }}>{msg.ok ? msg.message : "⚠ " + (msg.error || "導出失敗")}</div>}
      </div>
    </SetCard>
  );
};

const GeneralSet = ({ data }) => {
  const [g, setG] = useStateSet(null);
  const [saved, setSaved] = useStateSet(false);
  useEffectSet(() => { if (data && data.general) setG(data.general); }, [data]);
  const toggle = (k) => {
    const next = { ...g, [k]: !g[k] };
    setG(next);
    saveSettings("general", next).then(() => { setSaved(true); setTimeout(() => setSaved(false), 1500); });
  };
  if (!g) return <SetCard title="通知與交互" sub="載入中…"><div/></SetCard>;
  return (
    <>
      <SetCard title="通知與交互" action={<SavedTip show={saved}/>}>
        <div className="col gap-12">
          {[["scan", "掃碼槍快速入口", "現場 PDA / 掃碼槍一鍵入出庫"], ["push", "預警消息推送", "高風險預警即時推送至負責人"], ["sound", "預警提示音", ""], ["dark", "深色駕駛艙模式", "切換為深色科技底色"]].map(([k, t, d]) => (
            <div key={k} className="row spread" style={{ padding: 16, borderRadius: 12, border: "1px solid var(--line)" }}>
              <div className="col gap-3"><span style={{ fontSize: 13.5, fontWeight: 700 }}>{t}</span>{d && <span className="muted" style={{ fontSize: 12 }}>{d}</span>}</div>
              <Toggle on={g[k]} onToggle={() => toggle(k)}/>
            </div>
          ))}
        </div>
      </SetCard>
      <DatabaseExportSet/>
      <SetCard title="系統信息">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: 14 }}>
          {((data && data.system_info) || []).map(([k, v], i) => (
            <div key={i} className="row spread" style={{ padding: "12px 14px", borderRadius: 11, background: "var(--surface-2)" }}><span className="muted" style={{ fontSize: 12.5 }}>{k}</span><span className="num" style={{ fontSize: 13, fontWeight: 600 }}>{v}</span></div>
          ))}
        </div>
      </SetCard>
    </>
  );
};

window.PageSettings = PageSettings;
