/* ============================================================
   真實台賬頁 — 按當前公司物資分類動態生成
   ============================================================ */
const { useEffect: useEffectLedger, useMemo: useMemoLedger, useRef: useRefLedger, useState: useStateLedger } = React;

const API_BASE = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";

// 台賬頁配置改為按分類動態生成(取代寫死的電網三類),分類來自當前租戶 bootstrap
const LEDGER_ACCENTS = ["var(--blue)", "var(--danger)", "var(--purple)", "var(--teal)"];
const LEDGER_ICON_BY_ID = { hardware_material: "link", safety_tool: "shield", maintenance_tool: "gear", consumable: "link", returnable: "swap" };

function ledgerConfigFor(categoryId, index) {
  const list = window.LEDGER_CATEGORIES || [];
  const cat = list.find(c => c.id === categoryId) || { id: categoryId, name: categoryId, requires_return: false };
  const idx = (index === undefined || index < 0) ? 0 : index;
  return {
    title: cat.name,
    sub: cat.requires_return ? "借用歸還 · 自動生成歸還提醒 · 真實資料庫台賬" : "領用即消耗 · 不生成歸還提醒 · 真實資料庫台賬",
    endpoint: `/api/ledger?category=${encodeURIComponent(cat.id)}`,
    category: cat.id,
    accent: LEDGER_ACCENTS[idx % LEDGER_ACCENTS.length],
    icon: LEDGER_ICON_BY_ID[cat.id] || (cat.requires_return ? "shield" : "link"),
    returnable: !!cat.requires_return,
  };
}

async function apiJson(path, options) {
  const response = await (window.authFetch || fetch)(API_BASE + path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || response.statusText);
  return data;
}

function fmtValue(value) {
  if (value === null || value === undefined || value === "") return "—";
  return value;
}

function actionLabel(action) {
  return {
    inbound: "入庫",
    outbound: "領用",
    borrow: "借用",
    return: "歸還",
    adjust: "調整",
    stocktake: "盤點",
  }[action] || action;
}

function useDragScroll() {
  const ref = useRefLedger(null);
  const state = useRefLedger({ active: false, startX: 0, scrollLeft: 0 });
  const down = (event) => {
    const el = ref.current;
    if (!el || event.button !== 0) return;
    state.current = { active: true, startX: event.pageX, scrollLeft: el.scrollLeft };
    el.classList.add("dragging");
  };
  const move = (event) => {
    const el = ref.current;
    if (!el || !state.current.active) return;
    event.preventDefault();
    el.scrollLeft = state.current.scrollLeft - (event.pageX - state.current.startX);
  };
  const up = () => {
    const el = ref.current;
    state.current.active = false;
    if (el) el.classList.remove("dragging");
  };
  return { ref, onMouseDown: down, onMouseMove: move, onMouseUp: up, onMouseLeave: up };
}

const LedgerPage = ({ categoryId, index }) => {
  const cfg = ledgerConfigFor(categoryId, index);
  const [rows, setRows] = useStateLedger([]);
  const [mapped, setMapped] = useStateLedger({ rows: [], visible_columns: [], hidden_columns: [], summary: {}, source: "" });
  const [returns, setReturns] = useStateLedger([]);
  const [loading, setLoading] = useStateLedger(true);
  const [error, setError] = useStateLedger("");
  const [refreshKey, setRefreshKey] = useStateLedger(0);
  const [assistantOpen, setAssistantOpen] = useStateLedger(false);

  useEffectLedger(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    Promise.all([
      apiJson(cfg.endpoint),
      apiJson(`/api/database/mapped-ledger?category=${cfg.category}`),
      cfg.returnable ? apiJson("/api/returns/pending") : Promise.resolve({ rows: [] }),
    ])
      .then(([ledger, mappedData, pending]) => {
        if (cancelled) return;
        setRows(ledger.rows || []);
        setMapped(mappedData || { rows: [], visible_columns: [], hidden_columns: [], summary: {}, source: "" });
        setReturns((pending.rows || []).filter(r => cfg.returnable && r.category_name === cfg.title));
      })
      .catch(err => !cancelled && setError(err.message))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [categoryId, refreshKey]);

  const stats = useMemoLedger(() => {
    const total = mapped.rows?.length || rows.length;
    const borrow = rows.filter(r => r.action_type === "borrow").length;
    const outbound = rows.filter(r => r.action_type === "outbound").length;
    const pending = returns.length;
    const hidden = mapped.hidden_columns?.length || 0;
    return { total, borrow, outbound, pending, hidden };
  }, [rows, returns, mapped]);

  return (
    <div className="col gap-18">
      <PageHead
        title={cfg.title}
        sub={cfg.sub}
        actions={<>
          <button className="btn btn-sm" onClick={() => setRefreshKey(x => x + 1)}><Icon name="refresh" size={15}/>刷新</button>
          <span className="badge badge-info" style={{ height: 32 }}>API {API_BASE}</span>
        </>}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 16 }}>
        <RealStat label="映射資料" value={stats.total || "—"} unit="條" icon="clipboard" color={cfg.accent}/>
        <RealStat label={cfg.returnable ? "借用記錄" : "領用記錄"} value={(cfg.returnable ? stats.borrow : stats.outbound) || "—"} unit="條" icon={cfg.returnable ? "outbound" : "pkg"} color="var(--teal)"/>
        <RealStat label="待歸還提醒" value={stats.pending} unit="條" icon="clock" color={stats.pending ? "var(--danger)" : "var(--ok)"}/>
        <RealStat label="已隱藏字段" value={stats.hidden || "—"} unit="列" icon="filter" color="var(--blue)"/>
      </div>

      <div className="col gap-18">
        {/* 導入功能已統一遷移至「數據中轉站」 */}
        <MappedDatabaseTable cfg={cfg} data={mapped} loading={loading} error={error}/>
        <LedgerTable cfg={cfg} rows={rows} loading={loading} error={error}/>
        {cfg.returnable && <ReturnPanel rows={returns}/>}
      </div>

      <FloatingAIAssistant
        cfg={cfg}
        open={assistantOpen}
        setOpen={setAssistantOpen}
        onDone={() => setRefreshKey(x => x + 1)}
      />
    </div>
  );
};

const LedgerImportPanel = ({ cfg, onDone }) => {
  const [file, setFile] = useStateLedger(null);
  const [busy, setBusy] = useStateLedger(false);
  const [result, setResult] = useStateLedger(null);
  const [error, setError] = useStateLedger("");

  const submit = async () => {
    if (!file) {
      setError("請先選擇文件");
      return;
    }
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const form = new FormData();
      form.append("category_id", cfg.category);
      form.append("file", file);
      const data = await apiJson("/api/import/ledger-upload", { method: "POST", body: form });
      setResult(data);
      setFile(null);
      const input = document.getElementById(`ledger-import-${cfg.category}`);
      if (input) input.value = "";
      onDone && onDone();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card fade-up" style={{ padding: "16px 18px" }}>
      <div className="row spread gap-12" style={{ alignItems: "center", flexWrap: "wrap" }}>
        <div className="row gap-12" style={{ alignItems: "center", minWidth: 260, flex: 1 }}>
          <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center", background: "var(--grad-soft)", color: cfg.accent }}>
            <Icon name="inbound" size={18}/>
          </div>
          <div className="col gap-4">
            <span className="sec-title" style={{ fontSize: 15 }}>Excel 導入</span>
            <span className="muted" style={{ fontSize: 12 }}>{file ? file.name : "xlsx / csv"}</span>
          </div>
        </div>
        <div className="row gap-8" style={{ alignItems: "center", flexWrap: "wrap" }}>
          <input
            id={`ledger-import-${cfg.category}`}
            type="file"
            accept=".xlsx,.csv,.xls"
            onChange={(event) => {
              setFile(event.target.files?.[0] || null);
              setError("");
              setResult(null);
            }}
            style={{ maxWidth: 260 }}
          />
          <button className="btn btn-primary btn-sm" onClick={submit} disabled={busy || !file}>
            <Icon name={busy ? "refresh" : "inbound"} size={15}/>{busy ? "導入中" : "導入"}
          </button>
        </div>
      </div>
      {(result || error) && (
        <div style={{ marginTop: 12 }}>
          {error && <div className="badge badge-danger" style={{ height: "auto", padding: "8px 10px" }}>{error}</div>}
          {result && (
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              <span className="badge badge-info">批次 #{result.batch_id}</span>
              <span className="badge">讀取 {result.rows_seen || 0}</span>
              <span className="badge badge-ok">導入 {result.rows_imported || 0}</span>
              <span className="badge badge-info">更新 {result.rows_updated || 0}</span>
              <span className="badge">跳過 {result.rows_skipped || 0}</span>
              <span className={`badge ${result.rows_conflicted ? "badge-danger" : "badge-ok"}`}>衝突 {result.rows_conflicted || 0}</span>
            </div>
          )}
          {result?.conflicts?.length > 0 && (
            <div className="table-scroll" style={{ marginTop: 10, maxHeight: 180 }}>
              <table>
                <thead><tr><th>Sheet</th><th>行</th><th>物資</th><th>衝突</th></tr></thead>
                <tbody>
                  {result.conflicts.slice(0, 8).map((row, idx) => (
                    <tr key={idx}>
                      <td>{row.sheet}</td>
                      <td>{row.row_no}</td>
                      <td>{row.item_name}</td>
                      <td>{row.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const RealStat = ({ label, value, unit, icon, color }) => (
  <div className="card fade-up row spread" style={{ padding: "16px 18px" }}>
    <div className="col gap-4">
      <span style={{ fontSize: 12.5, color: "var(--ink-3)" }}>{label}</span>
      <span className="num" style={{ fontSize: 26, fontWeight: 700 }}>{value}<span style={{ fontSize: 12, color: "var(--ink-4)", marginLeft: 4 }}>{unit}</span></span>
    </div>
    <div style={{ width: 38, height: 38, borderRadius: 11, display: "grid", placeItems: "center", background: "var(--grad-soft)", color }}>
      <Icon name={icon} size={19}/>
    </div>
  </div>
);

const MappedDatabaseTable = ({ cfg, data, loading, error }) => {
  const [query, setQuery] = useStateLedger("");
  const [showAll, setShowAll] = useStateLedger(false);
  const [expanded, setExpanded] = useStateLedger(null);
  const drag = useDragScroll();
  const rows = data?.rows || [];
  const visibleCols = showAll ? (data?.columns || []) : (data?.visible_columns || []);
  const hiddenCols = data?.hidden_columns || [];
  const filtered = useMemoLedger(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter(row => Object.values(row).some(value => String(value ?? "").toLowerCase().includes(q)));
  }, [rows, query]);

  return (
    <div className="card fade-up table-scroll" style={{ padding: 0 }}>
      <div className="row spread" style={{ padding: "18px 20px 12px", gap: 14, flexWrap: "wrap", minWidth: 1120 }}>
        <div className="col gap-3">
          <span className="sec-title">資料庫直接映射</span>
          <span className="muted" style={{ fontSize: 12 }}>
            {data?.summary?.source_note || "SQLite 原始資料"} · 重要字段優先展示
          </span>
        </div>
        <div className="row gap-8" style={{ flexWrap: "wrap" }}>
          <div style={{ position: "relative" }}>
            <Icon name="search" size={15} color="var(--ink-4)" style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="input" value={query} onChange={e => setQuery(e.target.value)} placeholder="搜索任意字段"
              style={{ height: 34, width: 210, paddingLeft: 34, fontSize: 12.5 }}/>
          </div>
          <button className="btn btn-sm" onClick={() => setShowAll(!showAll)}>
            <Icon name="filter" size={14}/>{showAll ? "隱藏次要字段" : `顯示全部字段${hiddenCols.length ? ` (${hiddenCols.length})` : ""}`}
          </button>
          <span className="badge badge-gray">{filtered.length} / {rows.length} 條</span>
        </div>
      </div>

      {error && <div style={{ margin: "0 20px 14px", padding: 12, borderRadius: 10, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 13 }}>{error}</div>}

      <div className="table-scroll ledger-drag-scroll force-x-scroll" ref={drag.ref} onMouseDown={drag.onMouseDown} onMouseMove={drag.onMouseMove} onMouseUp={drag.onMouseUp} onMouseLeave={drag.onMouseLeave} style={{ maxHeight: 560, overflowY: "auto" }}>
        <table className="tbl" style={{ minWidth: Math.max(1480, visibleCols.length * 220 + 160) }}>
          <thead>
            <tr>
              {visibleCols.map(col => <th key={col}>{col.replace(/^_/, "")}</th>)}
              <th style={{ width: 86 }}>詳情</th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={visibleCols.length + 1} className="muted">正在載入資料庫映射資料…</td></tr>}
            {!loading && filtered.length === 0 && <tr><td colSpan={visibleCols.length + 1} className="muted">暫無資料。請確認台賬文件已導入。</td></tr>}
            {!loading && filtered.map((row, idx) => {
              const rowId = row._id || idx;
              const open = expanded === rowId;
              return (
                <React.Fragment key={rowId}>
                  <tr>
                    {visibleCols.map((col, colIdx) => (
                      <td key={col} style={{ minWidth: colIdx === 0 ? 300 : 220 }}>
                        <div style={{
                          fontWeight: colIdx === 0 ? 700 : 500,
                          color: colIdx === 0 ? "var(--ink)" : "var(--ink-2)",
                          whiteSpace: "nowrap",
                        }}>{fmtValue(row[col])}</div>
                      </td>
                    ))}
                    <td>
                      <button className="btn btn-sm" onClick={() => setExpanded(open ? null : rowId)} style={{ height: 28 }}>
                        {open ? "收起" : "查看"}
                      </button>
                    </td>
                  </tr>
                  {open && (
                    <tr>
                      <td colSpan={visibleCols.length + 1} style={{ background: "var(--surface-2)", padding: 16 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 10 }}>
                          {(data?.columns || Object.keys(row)).map(col => (
                            <div key={col} style={{ padding: 10, borderRadius: 10, background: "var(--surface)", border: "1px solid var(--line)" }}>
                              <div className="muted" style={{ fontSize: 11, marginBottom: 5 }}>{col.replace(/^_/, "")}</div>
                              <div style={{ fontSize: 12.5, color: "var(--ink)", lineHeight: 1.45, wordBreak: "break-word" }}>{fmtValue(row[col])}</div>
                            </div>
                          ))}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const LedgerTable = ({ cfg, rows, loading, error }) => (
  <LedgerTableInner cfg={cfg} rows={rows} loading={loading} error={error}/>
);

const LedgerTableInner = ({ cfg, rows, loading, error }) => {
  const drag = useDragScroll();
  return (
  <div className="card fade-up table-scroll" style={{ padding: 0 }}>
    <div className="row spread" style={{ padding: "18px 20px 12px" }}>
      <div className="col gap-3">
        <span className="sec-title">最近 AI 生成台賬</span>
        <span className="muted" style={{ fontSize: 12 }}>記錄清楚哪條線、作業內容、作業時間和物資流向</span>
      </div>
      <span className="badge badge-gray">{rows.length} 條</span>
    </div>
    {error && <div style={{ margin: "0 20px 14px", padding: 12, borderRadius: 10, background: "var(--danger-soft)", color: "var(--danger)", fontSize: 13 }}>{error}</div>}
    <div className="table-scroll ledger-drag-scroll force-x-scroll" ref={drag.ref} onMouseDown={drag.onMouseDown} onMouseMove={drag.onMouseMove} onMouseUp={drag.onMouseUp} onMouseLeave={drag.onMouseLeave} style={{ maxHeight: 460, overflowY: "auto" }}>
      <table className="tbl" style={{ minWidth: cfg.returnable ? 1320 : 1180 }}>
        <thead>
          <tr>
            <th>單號</th><th>物資</th><th>動作</th><th>數量</th><th>線路</th><th>作業</th><th>作業時間</th>{cfg.returnable && <th>歸還時間</th>}<th>狀態</th>
          </tr>
        </thead>
        <tbody>
          {loading && <tr><td colSpan={cfg.returnable ? 9 : 8} className="muted">正在載入真實資料…</td></tr>}
          {!loading && rows.length === 0 && <tr><td colSpan={cfg.returnable ? 9 : 8} className="muted">暫無記錄。可在右側用 AI 生成第一條台賬。</td></tr>}
          {!loading && rows.map(row => (
            <tr key={row.id}>
              <td className="num" style={{ color: cfg.accent, fontWeight: 700 }}>{row.transaction_no}</td>
              <td style={{ fontWeight: 700, color: "var(--ink)" }}>{fmtValue(row.item_name)}</td>
              <td><span className="badge badge-info">{actionLabel(row.action_type)}</span></td>
              <td className="num">{fmtValue(row.quantity)} {fmtValue(row.unit)}</td>
              <td style={{ minWidth: 260 }}>{fmtValue(row.work_location)}<div className="muted" style={{ fontSize: 11.5, whiteSpace: "nowrap" }}>{fmtValue(row.purpose)}</div></td>
              <td>{fmtValue(row.task_type)}</td>
              <td className="num">{fmtValue(row.task_time)}</td>
              {cfg.returnable && <td className="num">{fmtValue(row.expected_return_at)}</td>}
              <td><span className="badge badge-ok">{fmtValue(row.status)}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
  );
};

const ReturnPanel = ({ rows }) => (
  <div className="card fade-up" style={{ padding: 20 }}>
    <SecHead title="待歸還提醒" sub="可歸還物資借用後自動生成"/>
    <div className="col gap-10">
      {rows.length === 0 && <div className="muted" style={{ fontSize: 13 }}>暫無待歸還提醒。</div>}
      {rows.map(row => (
        <div key={row.reminder_id} className="row spread" style={{ padding: 12, borderRadius: 12, background: "var(--warn-soft)", border: "1px solid rgba(245,158,11,0.18)" }}>
          <div className="col gap-3">
            <span style={{ fontSize: 13.5, fontWeight: 700 }}>{row.item_name} · {row.quantity}{row.unit}</span>
            <span className="num muted" style={{ fontSize: 12 }}>{row.transaction_no} · {row.work_location}</span>
          </div>
          <span className="num" style={{ fontSize: 12.5, fontWeight: 700, color: "var(--warn)" }}>{row.expected_return_at}</span>
        </div>
      ))}
    </div>
  </div>
);

const FloatingAIAssistant = ({ cfg, open, setOpen, onDone }) => (
  <div className={`ai-ledger-float ${open ? "open" : ""}`}>
    {!open ? (
      <button className="ai-ledger-fab" onClick={() => setOpen(true)}>
        <Icon name="sparkle" size={18}/>
        <span>AI 台賬助手</span>
      </button>
    ) : (
      <div className="ai-ledger-window card fade-up">
        <div className="row spread" style={{ padding: "14px 16px", borderBottom: "1px solid var(--line)", background: "var(--grad-soft)" }}>
          <div className="row gap-10">
            <div style={{ width: 34, height: 34, borderRadius: 11, display: "grid", placeItems: "center", background: "var(--grad)", color: "#fff" }}>
              <Icon name="sparkle" size={17}/>
            </div>
            <div className="col gap-2">
              <span style={{ fontSize: 14.5, fontWeight: 800 }}>AI 台賬助手</span>
              <span className="muted" style={{ fontSize: 11.5 }}>直接對話 · 可查詢、生成與確認台賬</span>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => setOpen(false)} style={{ width: 30, padding: 0 }}>
            <Icon name="x" size={15}/>
          </button>
        </div>
        <AIAssistantPanel cfg={cfg} onDone={onDone}/>
      </div>
    )}
  </div>
);

const renderMiniMarkdown = (text) => {
  const inline = (line, keyPrefix) => {
    const parts = String(line || "").split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, idx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={`${keyPrefix}-${idx}`}>{part.slice(2, -2)}</strong>;
      }
      return <React.Fragment key={`${keyPrefix}-${idx}`}>{part}</React.Fragment>;
    });
  };
  return String(text || "").split("\n").map((line, idx) => {
    if (/^#{1,3}\s+/.test(line)) {
      return <div key={idx} className="mini-md-heading">{inline(line.replace(/^#{1,3}\s+/, ""), `h${idx}`)}</div>;
    }
    if (/^\s*[-*]\s+/.test(line)) {
      return <div key={idx} className="mini-md-list">{inline(line.replace(/^\s*[-*]\s+/, ""), `li${idx}`)}</div>;
    }
    return <div key={idx}>{inline(line, `p${idx}`)}</div>;
  });
};

const AIAssistantPanel = ({ cfg, onDone }) => {
  const [text, setText] = useStateLedger("");
  const [parsed, setParsed] = useStateLedger(null);
  const [conversationId, setConversationId] = useStateLedger(() => Number(localStorage.getItem("mk3-ledger-ai-conversation") || 0) || null);
  const [chatMessages, setChatMessages] = useStateLedger([]);
  const [busy, setBusy] = useStateLedger(false);
  const [msg, setMsg] = useStateLedger("");
  const [listening, setListening] = useStateLedger(false);
  const [voiceSupported] = useStateLedger(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition));
  const recognitionRef = useRefLedger(null);

  useEffectLedger(() => () => {
    if (recognitionRef.current) recognitionRef.current.stop();
  }, []);

  const voiceLang = () => {
    const appLang = localStorage.getItem("mk3-language") || document.documentElement.lang || "zh-Hant";
    return appLang === "zh-Hans" ? "zh-CN" : "zh-TW";
  };

  const toggleVoice = () => {
    if (!voiceSupported) {
      setMsg("目前瀏覽器不支持語音輸入，請使用 Chrome 或新版 Edge。");
      return;
    }
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.lang = voiceLang();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognitionRef.current = recognition;

    recognition.onstart = () => {
      setListening(true);
      setMsg("正在聽取語音，說完後可再次點擊麥克風停止。");
    };
    recognition.onresult = (event) => {
      let finalText = "";
      let interimText = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const piece = event.results[i][0].transcript.trim();
        if (event.results[i].isFinal) finalText += piece;
        else interimText += piece;
      }
      if (finalText) {
        setText(prev => `${prev ? prev + " " : ""}${finalText}`.trim());
        setMsg("語音已轉成文字，可繼續補充或點擊 AI 解析。");
      } else if (interimText) {
        setMsg(`正在識別：${interimText}`);
      }
    };
    recognition.onerror = (event) => {
      const reason = event.error === "not-allowed" ? "瀏覽器未授權麥克風權限" : event.error;
      setMsg(`語音輸入失敗：${reason}`);
      setListening(false);
    };
    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };
    recognition.start();
  };

  const runAssistant = async () => {
    const content = text.trim();
    if (!content) return;
    setBusy(true); setMsg("");
    const appendAssistantChunk = (chunk) => {
      setChatMessages(prev => prev.map((item, idx) => (
        idx === prev.length - 1 && item.streaming ? { ...item, content: (item.content || "") + chunk } : item
      )));
    };
    const patchStreamingAssistant = (patch) => {
      setChatMessages(prev => prev.map((item, idx) => (
        idx === prev.length - 1 && item.streaming ? { ...item, ...patch, streaming: false } : item
      )));
    };
    setChatMessages(prev => [...prev, { role: "user", content }, { role: "assistant", content: "", streaming: true }].slice(-8));
    setText("");
    // 統一走內核(/api/agent/run/stream):直接調指令、寫庫、寫審計,取代只解析/待確認的弱路徑。
    const stepLines = [];
    try {
      const result = await window.agentRunCompat({ conversation_id: conversationId, text: content }, {
        onStep: (ev, phase) => {
          if (phase !== "start") return;
          stepLines.push("▸ " + (ev.command || ev.tool_name || "執行中"));
          setChatMessages(prev => prev.map((item, idx) => (
            idx === prev.length - 1 && item.streaming ? { ...item, content: "正在執行：\n" + stepLines.join("\n") } : item
          )));
        },
      });
      if (result.conversation_id) {
        setConversationId(result.conversation_id);
        localStorage.setItem("mk3-ledger-ai-conversation", String(result.conversation_id));
      }
      patchStreamingAssistant({ role: "assistant", content: result.answer || "（已執行，詳見下方台賬）" });
      setParsed(null);
      setMsg("");
      onDone();   // 內核可能已寫庫,刷新台賬/庫存
    } catch (err) {
      patchStreamingAssistant({ role: "assistant", content: "AI 執行失敗：" + err.message });
      setMsg("AI 助手調度失敗：" + err.message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async () => {
    if (!parsed?.ai_command_id) return;
    setBusy(true); setMsg("");
    try {
      const result = await apiJson("/api/ai/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command_id: parsed.ai_command_id, expected_return_hours: 24, parsed_override: parsed }),
      });
      setMsg(`已生成台賬：${result.transaction_no}`);
      setParsed(null);
      onDone();
    } catch (err) {
      setMsg("確認失敗：" + err.message);
    } finally {
      setBusy(false);
    }
  };

  const editParsed = (field, value) => {
    setParsed(prev => {
      if (!prev) return prev;
      const next = { ...prev, [field]: value };
      if (field === "quantity") next.quantity = Number(value) || 0;
      if (field === "requires_return") {
        next.requires_return = value;
        if (!value) next.expected_return_at = null;
      }
      if (field === "category_id") {
        const cat = (window.LEDGER_CATEGORIES || []).find(c => c.id === value);
        const req = cat ? !!cat.requires_return : false;
        next.requires_return = req;
        if (!req && next.action_type === "borrow") next.action_type = "outbound";
        if (req && next.action_type === "outbound") next.action_type = "borrow";
      }
      const missing = new Set(next.missing_fields || []);
      if (value !== "" && value !== null && value !== undefined) missing.delete(field);
      if (!next.requires_return) missing.delete("expected_return_at");
      next.missing_fields = Array.from(missing);
      return next;
    });
  };

  const needsModel = parsed?.missing_fields?.includes("item_model");
  const candidateItems = parsed?.candidate_items || [];

  return (
    <div style={{ padding: 16 }} className="col gap-14">
        <div className="mini-chat-log">
          {chatMessages.length === 0 ? (
            <div className="mini-chat-empty">
              <Icon name="sparkle" size={24} color="var(--blue)"/>
              <span>直接和 AI 助手對話，可以查庫存、查台賬、生成領用/借用/入庫記錄。</span>
            </div>
          ) : chatMessages.filter(item => item.content).map((item, idx) => (
            <div key={idx} className={`mini-chat-msg ${item.role}`}>
              <div>{renderMiniMarkdown(item.content)}</div>
            </div>
          ))}
        </div>
        <div style={{ position: "relative" }}>
          <textarea className="input" rows={5} value={text} onChange={e => setText(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runAssistant(); } }}
            placeholder="直接輸入你的要求，例如：查某個物資庫存；或：領用 1 件耗材用於現場作業"
            style={{ height: 128, resize: "none", padding: "12px 48px 12px 12px", lineHeight: 1.55 }}/>
          <button
            onClick={toggleVoice}
            title={voiceSupported ? (listening ? "停止語音輸入" : "開始語音輸入") : "瀏覽器不支持語音輸入"}
            style={{
              position: "absolute", right: 10, bottom: 10, width: 34, height: 34, borderRadius: 10,
              display: "grid", placeItems: "center",
              background: listening ? "var(--danger-soft)" : "var(--surface-2)",
              color: listening ? "var(--danger)" : voiceSupported ? "var(--blue)" : "var(--ink-4)",
              border: listening ? "1px solid rgba(239,68,68,0.28)" : "1px solid var(--line)",
              boxShadow: listening ? "0 0 0 4px rgba(239,68,68,0.10)" : "none",
            }}
          >
            <Icon name="mic" size={17}/>
          </button>
        </div>
        <div className="row spread" style={{ marginTop: -6 }}>
          <span className="muted" style={{ fontSize: 11.5 }}>{voiceSupported ? "支持語音輸入，識別後仍需確認再寫入資料庫" : "此瀏覽器暫不支持語音輸入"}</span>
          {listening && <span className="badge badge-danger pulse-danger" style={{ height: 22 }}>聽取中</span>}
        </div>
        <button className="btn btn-primary" onClick={runAssistant} disabled={busy || !text.trim()}><Icon name="sparkle" size={16}/>{busy ? "發送中…" : "發送"}</button>

        {msg && <div style={{ padding: 13, borderRadius: 12, background: parsed ? "var(--blue-soft)" : "var(--surface-2)", color: "var(--ink-2)", fontSize: 13, lineHeight: 1.6 }}>{msg}</div>}

        {parsed && (
          <div className="col gap-10" style={{ padding: 14, borderRadius: 12, border: "1px solid var(--line)", background: "var(--surface-2)" }}>
            <div className="row spread">
              <span className="sec-title" style={{ fontSize: 14 }}>解析結果可編輯</span>
              <span className="badge badge-warn" style={{ height: 22 }}>AI Action 待確認</span>
            </div>
            <div className="ai-edit-grid">
              <label><span>分類</span><select className="input" value={parsed.category_id || ""} onChange={e => editParsed("category_id", e.target.value)}>
                <option value="">未選</option>{(window.LEDGER_CATEGORIES || []).map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select></label>
              <label><span>動作</span><select className="input" value={parsed.action_type || ""} onChange={e => editParsed("action_type", e.target.value)}>
                <option value="inbound">入庫</option><option value="outbound">領用</option><option value="borrow">借用</option><option value="return">歸還</option><option value="adjust">調整</option><option value="stocktake">盤點</option>
              </select></label>
              <label><span>物資名稱</span><input className="input" value={parsed.item_name || ""} onChange={e => editParsed("item_name", e.target.value)}/></label>
              <label><span>數量</span><input className="input" type="number" step="0.01" value={parsed.quantity ?? ""} onChange={e => editParsed("quantity", e.target.value)}/></label>
              <label><span>單位</span><input className="input" value={parsed.unit || ""} onChange={e => editParsed("unit", e.target.value)}/></label>
              <label><span>線路 / 地點</span><input className="input" value={parsed.work_location || ""} onChange={e => editParsed("work_location", e.target.value)}/></label>
              <label><span>作業內容</span><input className="input" value={parsed.task_type || ""} onChange={e => editParsed("task_type", e.target.value)}/></label>
              <label><span>作業時間</span><input className="input" value={parsed.task_time || ""} onChange={e => editParsed("task_time", e.target.value)} placeholder="2026-06-03 14:30"/></label>
              <label><span>操作人</span><input className="input" value={parsed.person_name || ""} onChange={e => editParsed("person_name", e.target.value)}/></label>
              <label><span>班組</span><input className="input" value={parsed.team || ""} onChange={e => editParsed("team", e.target.value)}/></label>
              <label><span>是否歸還</span><select className="input" value={parsed.requires_return ? "1" : "0"} onChange={e => editParsed("requires_return", e.target.value === "1")}>
                <option value="0">不需要</option><option value="1">需要</option>
              </select></label>
              {parsed.requires_return && <label><span>預計歸還</span><input className="input" value={parsed.expected_return_at || ""} onChange={e => editParsed("expected_return_at", e.target.value)} placeholder="2026-06-04 18:00"/></label>}
            </div>
            <label className="col gap-6" style={{ fontSize: 12, color: "var(--ink-3)", fontWeight: 700 }}>
              用途 / 備註
              <textarea className="input" value={parsed.purpose || ""} onChange={e => editParsed("purpose", e.target.value)} rows={3} style={{ height: 76, resize: "vertical", padding: 10, lineHeight: 1.5 }}/>
            </label>
            <div className="muted" style={{ fontSize: 11.5 }}>來源：AI 助手 Action · 模型：{fmtValue(parsed.model_name || parsed.source)} · 置信度：{fmtValue(parsed.confidence)}</div>
            {candidateItems.length > 0 && (
              <div className="col gap-8" style={{ paddingTop: 4 }}>
                <div className="muted" style={{ fontSize: 12 }}>請先選擇具體型號</div>
                {candidateItems.slice(0, 6).map(item => (
                  <button
                    key={item.id}
                    className="btn btn-sm"
                    onClick={() => {
                      setParsed(prev => {
                        const missing = (prev?.missing_fields || []).filter(x => x !== "item_model");
                        return {
                          ...prev,
                          item_name: item.item_name,
                          unit: prev?.unit || item.unit,
                          requested_item_name: prev?.requested_item_name || prev?.item_name,
                          resolved_item_id: item.id,
                          resolved_item_name: item.item_name,
                          resolved_spec_model: item.spec_model,
                          candidate_items: [],
                          missing_fields: missing,
                        };
                      });
                      setMsg(`已選擇型號：${item.item_name} / ${item.spec_model || "無型號"}，可繼續編輯或直接確認。`);
                    }}
                    style={{ justifyContent: "flex-start", height: "auto", minHeight: 34, padding: "8px 10px", textAlign: "left", lineHeight: 1.4 }}
                  >
                    <Icon name="checkCircle" size={14}/>
                    <span>{item.item_name} · {item.spec_model || "無型號"} · 庫存 {item.stock || 0}{item.unit || ""}</span>
                  </button>
                ))}
              </div>
            )}
            <button className="btn btn-primary" onClick={confirm} disabled={busy || needsModel}>
              <Icon name="check" size={15}/>{needsModel ? "請先確認型號" : "確認並生成台賬"}
            </button>
          </div>
        )}
      </div>
  );
};

Object.assign(window, { LedgerPage });
