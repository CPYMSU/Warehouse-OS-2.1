/* ============================================================
   法務合規 P0 —— 合同台賬 + 履約里程碑 + 證照台賬(到期接智能預警合規域)
   數據:/api/legal/*;到期/逾期預警在「智能預警」工作台合規域呈現。
   ============================================================ */
const { useState: useLegalState, useEffect: useLegalEffect } = React;

const LG_API = typeof window.WAREHOUSE_API_BASE === "string" ? window.WAREHOUSE_API_BASE : "http://127.0.0.1:8090";
const LG = { ink: "#1D1D1F", sub: "#6E6E73", hair: "rgba(29,29,31,0.12)", blue: "#0071E3", green: "#34C759", orange: "#FF9F0A", red: "#FF3B30", indigo: "#5856D6", bg: "#F5F5F7" };
const lgYuan = (v) => "¥" + Number(v || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const lgAsk = (p, autoAsk = true) => { if (window.openUnifiedAgent) window.openUnifiedAgent(p, { autoAsk }); };
const LG_CTYPE = { purchase: "採購", sales: "銷售", service: "服務", lease: "租賃", labor: "勞動", framework: "框架", other: "其他" };
const LG_STATUS = { draft: "草稿", reviewing: "審查中", approved: "審查通過", signed: "已簽署", active: "生效中", performing: "履約中", completed: "已完成", terminated: "已終止", expired: "已到期", archived: "已歸檔" };
const LG_CSTATUS = { draft: "草稿", reviewing: "審查中", approved: "已批", signed: "已簽", active: "生效", performing: "履約中", completed: "完成", terminated: "終止", expired: "到期", archived: "歸檔" };
const LG_LTYPE = { business: "營業執照", qualification: "資質證書", permit: "許可證", certification: "認證", personnel: "人員證書", other: "其他" };
const LG_LSTATUS = { valid: "有效", expiring: "臨期", expired: "已過期", revoked: "吊銷" };

const lgGet = async () => {
  const r = await (window.authFetch || fetch)(LG_API + "/api/legal/overview");
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "法務數據載入失敗");
  return d;
};
const lgPost = async (path, body) => {
  const r = await (window.authFetch || fetch)(LG_API + path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "操作失敗");
  return d;
};

const LgCard = ({ title, sub, right, children }) => (
  <div className="legal-card card col gap-12">
    <div className="row spread" style={{ alignItems: "flex-start", gap: 10 }}>
      <div className="col gap-2"><div style={{ fontSize: 15, fontWeight: 900 }}>{title}</div>{sub && <div style={{ fontSize: 12, color: LG.sub }}>{sub}</div>}</div>
      {right}
    </div>
    {children}
  </div>
);
const LgMetric = ({ label, value, tone }) => (
  <div className="legal-metric">
    <div className="legal-metric-label">{label}</div>
    <div className="num legal-metric-value" style={{ color: tone || LG.ink }}>{value}</div>
  </div>
);
const LgField = ({ label, children }) => (
  <label className="col gap-4" style={{ fontSize: 12, color: LG.sub }}>{label}{children}</label>
);
const lgInput = { padding: "7px 9px", borderRadius: 8, border: `1px solid ${LG.hair}`, fontSize: 13, background: "#fff", width: "100%" };

const daysLeftBadge = (dateStr) => {
  if (!dateStr) return null;
  const d = Math.ceil((new Date(dateStr) - new Date()) / 86400000);
  const tone = d < 0 ? LG.red : d <= 30 ? LG.orange : d <= 60 ? "#B8860B" : LG.sub;
  return <span style={{ fontSize: 11, color: tone, fontWeight: 700 }}>{d < 0 ? `逾期${-d}天` : `剩${d}天`}</span>;
};

const PageLegal = () => {
  const [d, setD] = useLegalState(null);
  const [state, setState] = useLegalState("loading");
  const [err, setErr] = useLegalState("");
  const [tab, setTab] = useLegalState("contracts");
  const [busy, setBusy] = useLegalState(false);
  const [form, setForm] = useLegalState(null); // {type:'contract'|'license', data}
  const [openContract, setOpenContract] = useLegalState(null);
  const [msName, setMsName] = useLegalState(""); const [msDue, setMsDue] = useLegalState(""); const [msAmt, setMsAmt] = useLegalState("");
  const [seals, setSeals] = useLegalState({});       // {contractId: [seal...]}
  const [verifyRes, setVerifyRes] = useLegalState(null); // 驗真彈窗

  const loadSeals = async (cid) => {
    try {
      const r = await (window.authFetch || fetch)(LG_API + `/api/compliance/by-subject?type=legal_contract&id=${cid}`);
      const j = await r.json().catch(() => ({}));
      if (r.ok) setSeals((s) => ({ ...s, [cid]: j.seals || [] }));
    } catch (e) {}
  };
  const verifySeal = async (serial) => {
    setVerifyRes({ loading: true });
    try {
      const r = await (window.authFetch || fetch)(LG_API + `/api/compliance/verify?serial=${encodeURIComponent(serial)}`);
      setVerifyRes(await r.json().catch(() => ({ ok: false, error: "驗真請求失敗" })));
    } catch (e) { setVerifyRes({ ok: false, error: e.message }); }
  };
  const downloadCert = (serial) => window.open(LG_API + `/api/compliance/cert?serial=${encodeURIComponent(serial)}`, "_blank", "noopener");
  const SEAL_DOC = { contract_draft: "起草封存", review_passed: "審查通過", seal_use: "用印", signed: "簽署", archived: "歸檔" };

  const load = () => { lgGet().then((x) => { setD(x); setState("ok"); }).catch((e) => { setErr(e.message); setState("error"); }); };
  useLegalEffect(() => { load(); }, []);

  const submit = (path, body, after) => {
    if (busy) return; setBusy(true); setErr("");
    lgPost(path, body).then((x) => { setD(x); setForm(null); if (after) after(x); }).catch((e) => setErr(e.message)).finally(() => setBusy(false));
  };
  const submitReview = async (cid) => {
    if (busy) return; setBusy(true); setErr("");
    const post = (body) => (window.authFetch || fetch)(LG_API + `/api/legal/contracts/${cid}/submit-review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
    try {
      let r = await post({}); let d = await r.json().catch(() => ({}));
      if (r.status === 409 && d.compliance && d.compliance.blocked) {
        const reason = window.prompt("⚠ 相對方命中黑名單/制裁名單,合規準入已阻斷。\n如確需提交,請填寫強制人工放行理由(將留痕審計):");
        if (!reason) { setBusy(false); return; }
        r = await post({ override: true, reason }); d = await r.json().catch(() => ({}));
      }
      if (r.ok) { setD(d); setErr(d.compliance && d.compliance.must_disclose ? "已提交審查 ⚠ 相對方為關聯方,須在審查中披露" : ""); }
      else setErr(d.error || "提交失敗");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };
  const askLegalSecretary = (prompt, autoAsk = true) => {
    if (!window.openUnifiedAgent) { setErr("AI 秘書窗口未就緒"); return; }
    setErr("");
    lgAsk(prompt, autoAsk);
  };
  const askDraft = () => {
    // 不用原生 prompt 彈窗(易被攔截/誤關導致「點了沒反應」):直接喚起秘書,由秘書反問追字段
    askLegalSecretary("我要起草一份合同。請先問清楚我:合同名稱與類型、相對方是誰、標的與金額、關鍵商務條件;我答完後,用 legal overview 查台賬上下文(必要時 web search 查公開線索),為這份合同起草可落地的條款框架、審查清單、履約里程碑建議和合規注意事項。請明確聲明這不是法律意見,需要法務人工覆核。");
  };
  const askNewContract = () => {
    askLegalSecretary("我要新建一份合同並登記進合同台賬。請逐項追問我:①合同名稱 ②類型(purchase/sales/service/lease/labor/framework/other)③相對方名稱(拿到後先用 legal check 做准入核查,有硬闸或關聯方命中要明確告知)④金額 ⑤簽署/生效/到期日期 ⑥風險等級。信息齊全後用 legal contract save 登記(status=draft),回報合同 id,並提醒我可上傳掃描件 OCR 覆核或用 legal contract review 提交審查。");
  };
  const askReview = (contract) => {
    askLegalSecretary(`請審查合同台賬 ID ${contract.id}「${contract.title}」。請先用 legal overview 讀取合同、相對方、履約節點和證照情況;再用 legal check 核查相對方准入,如需要最新外部合規線索再用 web search。請輸出審查問題、合規硬闸/警告、需要補充的文件、用印/簽署前置條件和下一步可執行命令。`);
  };
  const askExpiry = () => {
    askLegalSecretary("請使用 legal overview 和智能預警工具,梳理當前快到期/已逾期的合同、證照和履約里程碑,按風險等級列出續期、續簽、提醒和責任人跟進建議。");
  };
  const askCounterpartyWeb = () => {
    const name = checkInput.trim();
    if (!name) return;
    askLegalSecretary(`請核查相對方「${name}」。先執行 legal check --party "${name}" --web,必要時用 web search / web fetch 查公開失信、制裁、行政處罰、訴訟和資質線索。請區分本地硬闸結果與外部線索,列出來源 URL 和查詢日期,不要給正式法律意見。`);
  };
  const V2_LEGAL_SIGN_URL = "https://bonfirework.org/#/legal";
  const signContract = () => {
    if (busy) return;
    const message = "合同簽署現必須在 WAREHOUSE OS 2.0 上傳最終文件，並以 Face ID / Passkey 完成本人確認。\n\n是否前往 WAREHOUSE OS 2.0 法務頁？";
    if (window.confirm && !window.confirm(message)) {
      setErr("經典版不再提供弱化簽署；請前往 https://bonfirework.org/#/legal 完成安全簽署。");
      return;
    }
    window.location.assign(V2_LEGAL_SIGN_URL);
  };
  const ocrUpload = (file) => {
    if (!file || busy) return; setBusy(true); setErr("");
    const fd = new FormData(); fd.append("file", file);
    (window.authFetch || fetch)(LG_API + "/api/legal/contract-ocr", { method: "POST", body: fd })
      .then(async (r) => { const d = await r.json().catch(() => ({}));
        if (r.ok) { const e = d.extracted || {}; setForm({ type: "contract", data: { title: e.title || "", contract_type: e.contract_type || "purchase", counterparty_name: e.counterparty || "", amount: e.amount || "", sign_date: e.sign_date || "", effective_date: e.effective_date || "", expiry_date: e.expiry_date || "", status: "draft" } }); setErr("OCR 已識別,請覆核後保存(不自動入庫)"); }
        else setErr(d.error || "識別失敗"); })
      .catch((e) => setErr(e.message)).finally(() => setBusy(false));
  };
  const [checkInput, setCheckInput] = useLegalState(""); const [checkRes, setCheckRes] = useLegalState(null);
  const runCheck = async () => {
    if (!checkInput.trim()) return; setBusy(true); setCheckRes(null); setErr("");
    try {
      const r = await (window.authFetch || fetch)(LG_API + `/api/legal/counterparty-check?party_name=${encodeURIComponent(checkInput.trim())}`);
      const d = await r.json().catch(() => ({})); if (r.ok) setCheckRes(d); else setErr(d.error || "核查失敗");
    } catch (e) { setErr(e.message); } finally { setBusy(false); }
  };

  if (state === "loading") return <div className="muted" style={{ fontSize: 13 }}>讀取法務合規數據中…</div>;
  if (state === "error") return <div className="card" style={{ padding: 16, color: LG.red, fontSize: 13 }}>⚠ {err}（需「法務合規管理」權限 legal.manage）</div>;
  const s = d.summary || {};
  const tabs = [["contracts", "合同台賬"], ["licenses", "證照台賬"], ["milestones", "履約里程碑"], ["seals", "印章用印"], ["compliance", "合規核查"]];
  const WL_LABEL = { blacklist: "黑名單", dishonest: "失信", sanction: "制裁", conflict: "利益衝突" };
  const contracts = d.contracts || [];
  const licenses = d.licenses || [];
  const milestones = d.milestones || [];
  const watchlist = d.watchlist || [];
  const daysTo = (dateStr) => dateStr ? Math.ceil((new Date(dateStr) - new Date()) / 86400000) : null;
  const deadlineText = (dateStr) => { const n = daysTo(dateStr); return n === null ? "未設到期日" : (n < 0 ? `逾期${-n}天` : `剩${n}天`); };
  const expiringContracts = contracts.filter((c) => { const n = daysTo(c.expiry_date); return n !== null && n <= 60; });
  const expiringLicenses = licenses.filter((l) => { const n = daysTo(l.expiry_date); return n !== null && n <= 60; });
  const overdueMilestones = milestones.filter((m) => { const n = daysTo(m.due_date); return n !== null && n < 0; });
  const hardWatchlist = watchlist.filter((w) => ["blacklist", "sanction"].includes(w.list_type));
  const riskScore = expiringContracts.length + expiringLicenses.length + overdueMilestones.length + hardWatchlist.length;
  const health = hardWatchlist.length || overdueMilestones.length || (s.license_expired || 0) ? { word: "需處置", tone: LG.red }
    : riskScore ? { word: "需關注", tone: LG.orange } : { word: "穩定", tone: LG.green };
  const signalCards = [
    { icon: "clock", title: "合同到期", value: expiringContracts.length, sub: expiringContracts[0] ? `${expiringContracts[0].title} · ${deadlineText(expiringContracts[0].expiry_date)}` : "60 天內無到期合同", tone: expiringContracts.length ? LG.orange : LG.green },
    { icon: "shield", title: "證照風險", value: expiringLicenses.length, sub: expiringLicenses[0] ? `${expiringLicenses[0].title} · ${deadlineText(expiringLicenses[0].expiry_date)}` : "60 天內無到期證照", tone: expiringLicenses.length ? LG.orange : LG.green },
    { icon: "alert", title: "履約逾期", value: overdueMilestones.length, sub: overdueMilestones[0] ? `${overdueMilestones[0].contract_title} · ${overdueMilestones[0].name}` : "無逾期履約節點", tone: overdueMilestones.length ? LG.red : LG.green },
    { icon: "scan", title: "硬闸名單", value: hardWatchlist.length, sub: hardWatchlist[0] ? `${hardWatchlist[0].party_display || hardWatchlist[0].party_name} · ${WL_LABEL[hardWatchlist[0].list_type]}` : "無黑名單/制裁命中", tone: hardWatchlist.length ? LG.red : LG.green },
  ];
  const secretaryActions = [
    ["起草合同條款", askDraft],
    ["梳理到期風險", askExpiry],
    ["設計審查清單", () => askLegalSecretary("請基於 legal overview 為當前法務合規台賬設計合同審查清單,按相對方准入、付款條款、履約節點、證照、用印和簽署留證分組。")],
    ["檢查合規硬闸", () => askLegalSecretary("請讀取 legal overview,檢查合規名單、在管合同相對方、證照狀態和履約節點,列出所有硬闸、警告和需要人工披露的事項。")],
  ];

  const contractForm = () => {
    const f = form.data;
    const set = (k, v) => setForm({ ...form, data: { ...f, [k]: v } });
    return (
      <div className="risk-drawer-mask" style={{ zIndex: 600 }} onClick={() => setForm(null)}>
        <div className="card" style={{ maxWidth: 560, margin: "6vh auto", padding: 20 }} onClick={(e) => e.stopPropagation()}>
          <div className="row spread" style={{ marginBottom: 14 }}><div style={{ fontSize: 16, fontWeight: 900 }}>{f.id ? "編輯合同" : "新建合同"}</div><button className="btn btn-sm" onClick={() => setForm(null)}><Icon name="x" size={15}/></button></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ gridColumn: "1 / -1" }}><LgField label="合同名稱 *"><input style={lgInput} value={f.title || ""} onChange={(e) => set("title", e.target.value)}/></LgField></div>
            <LgField label="類型"><select style={lgInput} value={f.contract_type || "purchase"} onChange={(e) => set("contract_type", e.target.value)}>{Object.entries(LG_CTYPE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></LgField>
            <LgField label="相對方"><input style={lgInput} value={f.counterparty_name || ""} onChange={(e) => set("counterparty_name", e.target.value)} placeholder="供應商/客戶名稱"/></LgField>
            <LgField label="金額"><input type="number" style={lgInput} value={f.amount || ""} onChange={(e) => set("amount", e.target.value)}/></LgField>
            <LgField label="狀態"><div style={{ ...lgInput, display: "flex", alignItems: "center", color: "var(--text-2)" }}>草稿 · 後續狀態由正式審查與簽署流程產生</div></LgField>
            <LgField label="生效日"><input type="date" style={lgInput} value={f.effective_date || ""} onChange={(e) => set("effective_date", e.target.value)}/></LgField>
            <LgField label="到期日(到期預警)"><input type="date" style={lgInput} value={f.expiry_date || ""} onChange={(e) => set("expiry_date", e.target.value)}/></LgField>
            <LgField label="風險等級"><select style={lgInput} value={f.risk_level || "low"} onChange={(e) => set("risk_level", e.target.value)}><option value="low">低</option><option value="medium">中</option><option value="high">高</option></select></LgField>
          </div>
          <div className="row gap-8" style={{ marginTop: 16, justifyContent: "flex-end" }}>
            <button className="btn" onClick={() => setForm(null)}>取消</button>
            <button className="btn btn-primary" disabled={busy || !f.title} onClick={() => submit("/api/legal/contracts", f)}>{busy ? "保存中…" : "保存"}</button>
          </div>
        </div>
      </div>
    );
  };
  const licenseForm = () => {
    const f = form.data;
    const set = (k, v) => setForm({ ...form, data: { ...f, [k]: v } });
    return (
      <div className="risk-drawer-mask" style={{ zIndex: 600 }} onClick={() => setForm(null)}>
        <div className="card" style={{ maxWidth: 520, margin: "6vh auto", padding: 20 }} onClick={(e) => e.stopPropagation()}>
          <div className="row spread" style={{ marginBottom: 14 }}><div style={{ fontSize: 16, fontWeight: 900 }}>{f.id ? "編輯證照" : "錄入證照"}</div><button className="btn btn-sm" onClick={() => setForm(null)}><Icon name="x" size={15}/></button></div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div style={{ gridColumn: "1 / -1" }}><LgField label="證照名稱 *"><input style={lgInput} value={f.title || ""} onChange={(e) => set("title", e.target.value)}/></LgField></div>
            <LgField label="權屬"><select style={lgInput} value={f.owner_kind || "self"} onChange={(e) => set("owner_kind", e.target.value)}><option value="self">本企業</option><option value="party">相對方</option></select></LgField>
            {f.owner_kind === "party" && <LgField label="相對方名稱"><input style={lgInput} value={f.owner_name || ""} onChange={(e) => set("owner_name", e.target.value)}/></LgField>}
            <LgField label="類型"><select style={lgInput} value={f.license_type || "business"} onChange={(e) => set("license_type", e.target.value)}>{Object.entries(LG_LTYPE).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></LgField>
            <LgField label="發證機關"><input style={lgInput} value={f.issuer || ""} onChange={(e) => set("issuer", e.target.value)}/></LgField>
            <LgField label="證照編號"><input style={lgInput} value={f.serial_no || ""} onChange={(e) => set("serial_no", e.target.value)}/></LgField>
            <LgField label="有效期至(到期預警)"><input type="date" style={lgInput} value={f.expiry_date || ""} onChange={(e) => set("expiry_date", e.target.value)}/></LgField>
          </div>
          <div className="row gap-8" style={{ marginTop: 16, justifyContent: "flex-end" }}>
            <button className="btn" onClick={() => setForm(null)}>取消</button>
            <button className="btn btn-primary" disabled={busy || !f.title} onClick={() => submit("/api/legal/licenses", f)}>{busy ? "保存中…" : "保存"}</button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="legal-page">
      <div className="risk-topbar">
        <div>
          <div className="risk-title">法務合規</div>
          <div className="risk-sub">AI 秘書接管合同、證照、履約、用印和相對方准入;到期與硬闸進智能預警合規域。</div>
        </div>
        <div className="row gap-8">
          <button className="btn btn-sm" onClick={load} disabled={busy}><Icon name="refresh" size={14}/>刷新</button>
          <button className="btn btn-sm" title="手工表單錄入" onClick={() => setForm({ type: "contract", data: { status: "draft", contract_type: "purchase" } })}><Icon name="clipboard" size={14}/>表單錄入</button>
          <button className="btn btn-primary btn-sm" title="秘書逐項追問並登記入台賬" onClick={askNewContract}><Icon name="sparkle" size={14}/>新建合同</button>
        </div>
      </div>
      {err && <div className="risk-err"><Icon name="alert" size={15}/>{err}</div>}

      <div className="legal-grid">
        <div className="legal-canvas">
          <div className="legal-hero card">
            <div className="legal-hero-main">
              <div className="risk-hero-eyebrow">AI 法務態勢</div>
              <div className="legal-hero-word" style={{ color: health.tone }}>{health.word}</div>
              <div className="risk-hero-line">在管合同 {s.active_count || 0} 份,金額 {lgYuan(s.contract_amount)};當前有 {riskScore} 個風險信號需要法務或業務負責人跟進。</div>
              <div className="legal-hero-actions">
                <button className="btn btn-sm" onClick={askExpiry}><Icon name="sparkle" size={13}/>讓秘書梳理到期</button>
                <label className="btn btn-sm" style={{ cursor: "pointer" }}><Icon name="inbound" size={13}/>OCR 識別合同<input type="file" accept="image/*" style={{ display: "none" }} onChange={(e) => { if (e.target.files[0]) ocrUpload(e.target.files[0]); e.target.value = ""; }}/></label>
              </div>
            </div>
            <div className="legal-hero-score">
              <div className="num" style={{ color: health.tone }}>{riskScore}</div>
              <span>風險信號</span>
            </div>
          </div>

          <div className="legal-metric-grid">
            <LgMetric label="合同總數" value={s.contract_count || 0}/>
            <LgMetric label="生效合同" value={s.active_count || 0} tone={LG.blue}/>
            <LgMetric label="在管合同金額" value={lgYuan(s.contract_amount)} tone={LG.indigo}/>
            <LgMetric label="證照數" value={s.license_count || 0}/>
            <LgMetric label="已過期證照" value={s.license_expired || 0} tone={(s.license_expired || 0) > 0 ? LG.red : LG.green}/>
            <LgMetric label="待辦履約節點" value={s.milestone_open || 0} tone={(s.milestone_open || 0) > 0 ? LG.orange : LG.green}/>
          </div>

          <div className="legal-signal-grid">
            {signalCards.map((item) => (
              <button key={item.title} className="legal-signal card" onClick={item.title === "合同到期" || item.title === "履約逾期" ? () => setTab(item.title === "合同到期" ? "contracts" : "milestones") : item.title === "證照風險" ? () => setTab("licenses") : () => setTab("compliance")}>
                <span className="legal-signal-icon" style={{ background: item.tone + "18", color: item.tone }}><Icon name={item.icon} size={17}/></span>
                <span className="legal-signal-body"><b>{item.title}</b><em>{item.sub}</em></span>
                <span className="num legal-signal-num" style={{ color: item.tone }}>{item.value}</span>
              </button>
            ))}
          </div>

          <div className="legal-listbar">
            <div className="risk-listbar-l">法務工作區 · <b>{tabs.find(([id]) => id === tab)?.[1]}</b></div>
            <div className="legal-tabs">
              {tabs.map(([id, label]) => <button key={id} className={tab === id ? "on" : ""} onClick={() => setTab(id)}>{label}</button>)}
            </div>
          </div>

      {tab === "contracts" && (
        <LgCard title="合同台賬" sub={`${(d.contracts || []).length} 份`} right={<span className="row gap-6"><button className="btn btn-sm" title="手工表單錄入" onClick={() => setForm({ type: "contract", data: { status: "draft", contract_type: "purchase" } })}><Icon name="clipboard" size={14}/>表單</button><button className="btn btn-primary btn-sm" onClick={askNewContract}><Icon name="sparkle" size={14}/>新建合同</button></span>}>
          {(d.contracts || []).length === 0 ? <div className="muted" style={{ fontSize: 13, padding: "14px 0" }}>暫無合同,點右上「新建合同」。</div> : (d.contracts || []).map((c) => (
            <div key={c.id} className="col" style={{ borderTop: `1px solid ${LG.hair}`, padding: "9px 0" }}>
              <div className="row spread" style={{ cursor: "pointer", alignItems: "center" }} onClick={() => { const nx = openContract === c.id ? null : c.id; setOpenContract(nx); if (nx && !seals[c.id]) loadSeals(c.id); }}>
                <div className="col gap-2" style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700 }}>{c.title} <span className="badge" style={{ background: "var(--surface-2)", color: LG.sub, fontSize: 11 }}>{LG_CTYPE[c.contract_type]}</span></div>
                  <div className="num" style={{ fontSize: 11.5, color: LG.sub }}>{c.contract_no} · {c.counterparty_display || c.counterparty_name || "—"} · {lgYuan(c.amount)}{c.milestone_open ? ` · 待辦節點 ${c.milestone_open}` : ""}</div>
                </div>
                <div className="row gap-8" style={{ alignItems: "center" }}>
                  {c.review && c.review.status === "running" && <span className="badge badge-info" style={{ fontSize: 11 }}>審查中 · {c.review.current_node || "處理中"}</span>}
                  {c.expiry_date && <span className="col" style={{ alignItems: "flex-end" }}><span style={{ fontSize: 11.5, color: LG.sub }}>{c.expiry_date}</span>{daysLeftBadge(c.expiry_date)}</span>}
                  <span className="badge" style={{ background: c.status === "active" ? "rgba(52,199,89,0.14)" : "var(--surface-2)", color: c.status === "active" ? LG.green : LG.ink, fontSize: 11 }}>{LG_CSTATUS[c.status]}</span>
                  <button className="btn btn-sm" disabled={busy} onClick={(e) => { e.stopPropagation(); askReview(c); }}>AI秘書審查</button>
                  {c.status === "draft" && <button className="btn btn-sm btn-primary" disabled={busy} onClick={(e) => { e.stopPropagation(); submitReview(c.id); }}>提交審查</button>}
                  {["reviewing", "approved"].includes(c.status) && <button className="btn btn-sm" disabled={busy} onClick={(e) => { e.stopPropagation(); signContract(); }}>前往 2.0 安全簽署</button>}
                  {c.status === "draft" && <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setForm({ type: "contract", data: { ...c } }); }}><Icon name="edit" size={13}/></button>}
                </div>
              </div>
              {openContract === c.id && (
                <div style={{ marginTop: 8, padding: 12, background: LG.bg, borderRadius: 8 }} className="col gap-8">
                  <div style={{ fontSize: 12, fontWeight: 800, color: LG.sub }}>履約里程碑</div>
                  {(d.milestones || []).filter((m) => m.contract_id === c.id).length === 0 && <div className="muted" style={{ fontSize: 12 }}>無待辦節點</div>}
                  {(d.milestones || []).filter((m) => m.contract_id === c.id).map((m) => (
                    <div key={m.id} className="row spread" style={{ alignItems: "center" }}>
                      <span style={{ fontSize: 12.5 }}>{m.name} · {lgYuan(m.amount)} {m.due_date && <span style={{ color: LG.sub }}>應於 {m.due_date}</span>} {daysLeftBadge(m.due_date)}</span>
                      <button className="btn btn-sm" disabled={busy} onClick={() => submit(`/api/legal/milestones/${m.id}/status`, { status: "done" })}>標記完成</button>
                    </div>
                  ))}
                  <div className="row gap-6" style={{ flexWrap: "wrap", alignItems: "center" }}>
                    <input style={{ ...lgInput, width: 130 }} placeholder="節點名稱" value={msName} onChange={(e) => setMsName(e.target.value)}/>
                    <input type="date" style={{ ...lgInput, width: 150 }} value={msDue} onChange={(e) => setMsDue(e.target.value)}/>
                    <input type="number" style={{ ...lgInput, width: 110 }} placeholder="金額" value={msAmt} onChange={(e) => setMsAmt(e.target.value)}/>
                    <button className="btn btn-sm" disabled={busy || !msName} onClick={() => submit(`/api/legal/contracts/${c.id}/milestones`, { name: msName, due_date: msDue || null, amount: msAmt || 0 }, () => { setMsName(""); setMsDue(""); setMsAmt(""); })}>添加節點</button>
                  </div>

                  {/* 防篡改憑證鏈 */}
                  <div className="row spread" style={{ alignItems: "center", marginTop: 4 }}>
                    <div style={{ fontSize: 12, fontWeight: 800, color: LG.sub }}>防篡改憑證鏈 {(seals[c.id] || []).length ? `· ${seals[c.id].length} 道鋼印` : ""}</div>
                    <button className="btn btn-sm" disabled={busy} title="對當前合同狀態封一道防篡改數字鋼印"
                      onClick={() => askLegalSecretary(`請為合同 ID ${c.id}「${c.title}」當前「${LG_STATUS[c.status] || c.status}」狀態用 seal issue 簽發一道防篡改憑證(doc_type 取最貼切的階段:草稿用 contract_draft、已審用 review_passed、已簽用 signed),payload 記錄合同名、相對方、金額、狀態與時間,subject-type=legal_contract subject-id=${c.id}。`)}>
                      <Icon name="shield" size={13}/>封存憑證
                    </button>
                  </div>
                  {(seals[c.id] || []).length === 0
                    ? <div className="muted" style={{ fontSize: 12 }}>暫無憑證。流程每跨一步(起草/審查/簽署)可「封存憑證」生成不可篡改的傳遞介質。</div>
                    : (seals[c.id] || []).map((s) => (
                      <div key={s.serial_no} className="row spread" style={{ alignItems: "center", fontSize: 12.5, padding: "5px 0", borderTop: `1px solid ${LG.hair}` }}>
                        <span style={{ minWidth: 0 }}>
                          <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: 4, marginRight: 6, background: s.verified ? "#0a7f3f" : "#b42318" }}/>
                          {SEAL_DOC[s.doc_type] || s.doc_type} <span className="muted">{s.title}</span>
                          <span className="muted" style={{ fontFamily: "monospace", marginLeft: 6 }}>{s.serial_no} · {s.issued_at}</span>
                        </span>
                        <span className="row gap-6" style={{ flex: "none" }}>
                          <span style={{ fontSize: 11, fontWeight: 800, color: s.verified ? "#0a7f3f" : "#b42318" }}>{s.verified ? "✓ 完好" : "✗ 異常"}</span>
                          <button className="btn btn-sm" onClick={() => verifySeal(s.serial_no)}>驗真</button>
                          <button className="btn btn-sm" onClick={() => downloadCert(s.serial_no)}>下載憑證</button>
                        </span>
                      </div>
                    ))}
                </div>
              )}
            </div>
          ))}
        </LgCard>
      )}

      {tab === "licenses" && (
        <LgCard title="證照台賬" sub={`${(d.licenses || []).length} 項 · 到期自動進預警合規域`} right={<button className="btn btn-primary btn-sm" onClick={() => setForm({ type: "license", data: { owner_kind: "self", license_type: "business" } })}><Icon name="plus" size={14}/>錄入證照</button>}>
          {(d.licenses || []).length === 0 ? <div className="muted" style={{ fontSize: 13, padding: "14px 0" }}>暫無證照,點右上「錄入證照」。</div> : (d.licenses || []).map((l) => (
            <div key={l.id} className="row spread" style={{ borderTop: `1px solid ${LG.hair}`, padding: "9px 0", alignItems: "center" }}>
              <div className="col gap-2" style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13.5, fontWeight: 700 }}>{l.title} <span className="badge" style={{ background: "var(--surface-2)", color: LG.sub, fontSize: 11 }}>{LG_LTYPE[l.license_type]}</span></div>
                <div className="num" style={{ fontSize: 11.5, color: LG.sub }}>{l.owner_kind === "self" ? "本企業" : (l.owner_display || l.owner_name || "相對方")} · {l.serial_no || l.license_no}</div>
              </div>
              <div className="row gap-8" style={{ alignItems: "center" }}>
                {l.expiry_date && <span className="col" style={{ alignItems: "flex-end" }}><span style={{ fontSize: 11.5, color: LG.sub }}>{l.expiry_date}</span>{daysLeftBadge(l.expiry_date)}</span>}
                <span className="badge" style={{ background: l.status === "expired" ? "rgba(255,59,48,0.12)" : "var(--surface-2)", color: l.status === "expired" ? LG.red : LG.ink, fontSize: 11 }}>{LG_LSTATUS[l.status]}</span>
                <button className="btn btn-sm" onClick={() => setForm({ type: "license", data: { ...l } })}><Icon name="edit" size={13}/></button>
              </div>
            </div>
          ))}
        </LgCard>
      )}

      {tab === "milestones" && (
        <LgCard title="待辦履約節點" sub={`${(d.milestones || []).length} 個 · 逾期自動進預警合規域`}>
          {(d.milestones || []).length === 0 ? <div className="muted" style={{ fontSize: 13, padding: "14px 0" }}>無待辦履約節點。</div> : (d.milestones || []).map((m) => (
            <div key={m.id} className="row spread" style={{ borderTop: `1px solid ${LG.hair}`, padding: "9px 0", alignItems: "center" }}>
              <div className="col gap-2"><div style={{ fontSize: 13 }}>{m.contract_title} · <b>{m.name}</b></div><div className="num" style={{ fontSize: 11.5, color: LG.sub }}>{m.contract_no} · {lgYuan(m.amount)} {m.due_date && `· 應於 ${m.due_date}`}</div></div>
              <div className="row gap-8" style={{ alignItems: "center" }}>{daysLeftBadge(m.due_date)}<button className="btn btn-sm" disabled={busy} onClick={() => submit(`/api/legal/milestones/${m.id}/status`, { status: "done" })}>標記完成</button></div>
            </div>
          ))}
        </LgCard>
      )}

      {tab === "seals" && (
        <LgCard title="印章用印" sub={`${(d.seals || []).length} 枚印章 · 用印審批走工作流(簽章本人化)`} right={<button className="btn btn-primary btn-sm" onClick={() => setForm({ type: "seal", data: { seal_type: "company" } })}><Icon name="plus" size={14}/>錄入印章</button>}>
          <div style={{ fontSize: 12, color: LG.sub, marginBottom: 6 }}>用印申請發起後,審批待辦在「招採工作流 / 工作流待辦」頁處理(放行需保管人留用印憑證)。</div>
          {(d.seals || []).length === 0 ? <div className="muted" style={{ fontSize: 13, padding: "10px 0" }}>暫無印章,點右上「錄入印章」。</div> : (d.seals || []).map((sl) => (
            <div key={sl.id} className="row spread" style={{ borderTop: `1px solid ${LG.hair}`, padding: "9px 0", alignItems: "center" }}>
              <div className="col gap-2"><div style={{ fontSize: 13.5, fontWeight: 700 }}>{sl.seal_name} <span className="badge" style={{ background: "var(--surface-2)", color: LG.sub, fontSize: 11 }}>{({ company: "公章", contract: "合同章", finance: "財務章", legal_rep: "法人章", invoice: "發票章", other: "其他" })[sl.seal_type]}</span></div><div className="num" style={{ fontSize: 11.5, color: LG.sub }}>{sl.seal_no} · 保管人 {sl.holder_name || "未指定"}</div></div>
              <div className="row gap-8" style={{ alignItems: "center" }}>
                <button className="btn btn-sm" disabled={busy} onClick={() => { const p = window.prompt("用印用途/文件:"); if (p) submit("/api/legal/seal-use", { purpose: p, seal_id: sl.id }); }}>發起用印</button>
                <button className="btn btn-sm" onClick={() => setForm({ type: "seal", data: { ...sl } })}><Icon name="edit" size={13}/></button>
              </div>
            </div>
          ))}
        </LgCard>
      )}

      {tab === "compliance" && (
        <div className="col gap-14">
          <LgCard title="相對方準入核查" sub="提交合同審查時自動硬閘:黑名單/制裁→阻斷;失信/資質失效/關聯方→警告須披露">
            <div className="row gap-8" style={{ flexWrap: "wrap" }}>
              <input style={{ ...lgInput, maxWidth: 280 }} placeholder="輸入相對方名稱核查" value={checkInput} onChange={(e) => setCheckInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runCheck()}/>
              <button className="btn btn-primary btn-sm" disabled={busy || !checkInput.trim()} onClick={runCheck}><Icon name="shield" size={13}/>核查</button>
              <button className="btn btn-sm" disabled={busy || !checkInput.trim()} onClick={askCounterpartyWeb}><Icon name="sparkle" size={13}/>AI秘書聯網核查</button>
            </div>
            {checkRes && (
              <div style={{ marginTop: 10, padding: 12, borderRadius: 8, background: checkRes.blocked ? "rgba(255,59,48,0.08)" : checkRes.flags.length ? "rgba(255,159,10,0.08)" : "rgba(52,199,89,0.08)" }} className="col gap-6">
                <div style={{ fontWeight: 800, color: checkRes.blocked ? LG.red : checkRes.flags.length ? LG.orange : LG.green }}>
                  {checkRes.party_id ? (checkRes.blocked ? "⛔ 準入阻斷(命中黑名單/制裁)" : checkRes.flags.length ? "⚠ 有合規提示(可提交,須披露/留痕)" : "✓ 通過,無合規問題") : "該相對方尚未建檔,無記錄"}
                </div>
                {(checkRes.flags || []).map((f, i) => <div key={i} style={{ fontSize: 12.5, color: f.level === "red" ? LG.red : LG.orange }}>· {f.detail}</div>)}
              </div>
            )}
          </LgCard>
          <LgCard title="合規名單(黑名單/失信/制裁/利益衝突)" sub={`${(d.watchlist || []).length} 條`} right={<button className="btn btn-primary btn-sm" onClick={() => setForm({ type: "watchlist", data: { list_type: "blacklist" } })}><Icon name="plus" size={14}/>加入名單</button>}>
            {(d.watchlist || []).length === 0 ? <div className="muted" style={{ fontSize: 13, padding: "10px 0" }}>暫無記錄。建合同前會自動核查相對方是否在此名單。</div> : (d.watchlist || []).map((w) => (
              <div key={w.id} className="row spread" style={{ borderTop: `1px solid ${LG.hair}`, padding: "9px 0", alignItems: "center" }}>
                <div className="col gap-2"><div style={{ fontSize: 13.5, fontWeight: 700 }}>{w.party_display || w.party_name} <span className="badge" style={{ background: w.list_type === "blacklist" || w.list_type === "sanction" ? "rgba(255,59,48,0.12)" : "var(--surface-2)", color: w.list_type === "blacklist" || w.list_type === "sanction" ? LG.red : LG.ink, fontSize: 11 }}>{WL_LABEL[w.list_type]}</span></div><div style={{ fontSize: 11.5, color: LG.sub }}>{w.reason || "—"}{w.source ? ` · 來源 ${w.source}` : ""}</div></div>
                <button className="btn btn-sm" onClick={() => setForm({ type: "watchlist", data: { ...w } })}><Icon name="edit" size={13}/></button>
              </div>
            ))}
          </LgCard>
        </div>
      )}

        </div>

        <aside className="legal-copilot card">
          <div className="risk-cop-head">
            <span className="row gap-8" style={{ alignItems: "center" }}><Icon name="sparkle" size={18} color="var(--blue)"/><b style={{ fontSize: 15 }}>公司 AI 秘書</b></span>
            <span className="badge badge-info" style={{ height: 22 }}>法務域</span>
          </div>
          <div className="legal-cop-body">
            <div className="legal-ai-bubble">
              我會先讀取 legal overview,再按權限調用 legal / web 命令。外部公開信息只作線索,合同審查和用印仍保留人工節點與審計。
            </div>
            <div className="legal-chip-grid">
              {secretaryActions.map(([label, fn]) => <button key={label} className="risk-cop-chip" onClick={fn}><Icon name="sparkle" size={12}/>{label}</button>)}
            </div>
            <div className="legal-command-stack">
              <div className="legal-command-title">可調用命令</div>
              {[
                ["legal overview", "讀取合同、證照、履約、用印和合規名單"],
                ["legal check --web", "本地硬闸 + 受控外部公開線索"],
                ["legal contract review", "提交合同審查並觸發合規硬闸"],
                ["legal seal use", "發起用印工作流"],
              ].map(([cmd, desc]) => (
                <div key={cmd} className="legal-command-row"><code>{cmd}</code><span>{desc}</span></div>
              ))}
            </div>
            <div className="legal-checkbox">
              <div style={{ fontSize: 12, fontWeight: 800, color: LG.sub }}>相對方快速核查</div>
              <div className="row gap-8">
                <input style={lgInput} placeholder="輸入相對方名稱" value={checkInput} onChange={(e) => setCheckInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && runCheck()}/>
                <button className="btn btn-sm btn-primary" disabled={busy || !checkInput.trim()} onClick={runCheck}><Icon name="shield" size={13}/>本地</button>
              </div>
              <button className="btn btn-sm" disabled={busy || !checkInput.trim()} onClick={askCounterpartyWeb} style={{ width: "100%" }}><Icon name="sparkle" size={13}/>交給 AI 秘書聯網核查</button>
              {checkRes && (
                <div className={"legal-check-result " + (checkRes.blocked ? "danger" : checkRes.flags.length ? "warn" : "ok")}>
                  {checkRes.party_id ? (checkRes.blocked ? "準入阻斷" : checkRes.flags.length ? "有合規提示" : "本地核查通過") : "未建檔,本地無記錄"}
                </div>
              )}
            </div>
          </div>
        </aside>
      </div>

      {form && form.type === "contract" && contractForm()}
      {form && form.type === "license" && licenseForm()}
      {form && form.type === "watchlist" && (
        <div className="risk-drawer-mask" style={{ zIndex: 600 }} onClick={() => setForm(null)}>
          <div className="card" style={{ maxWidth: 460, margin: "8vh auto", padding: 20 }} onClick={(e) => e.stopPropagation()}>
            <div className="row spread" style={{ marginBottom: 14 }}><div style={{ fontSize: 16, fontWeight: 900 }}>{form.data.id ? "編輯名單" : "加入合規名單"}</div><button className="btn btn-sm" onClick={() => setForm(null)}><Icon name="x" size={15}/></button></div>
            <div className="col gap-12">
              <LgField label="相對方名稱 *"><input style={lgInput} value={form.data.party_name || ""} onChange={(e) => setForm({ ...form, data: { ...form.data, party_name: e.target.value } })}/></LgField>
              <LgField label="名單類型"><select style={lgInput} value={form.data.list_type || "blacklist"} onChange={(e) => setForm({ ...form, data: { ...form.data, list_type: e.target.value } })}><option value="blacklist">黑名單(阻斷)</option><option value="sanction">制裁(阻斷)</option><option value="dishonest">失信(警告)</option><option value="conflict">利益衝突(警告)</option></select></LgField>
              <LgField label="原因"><input style={lgInput} value={form.data.reason || ""} onChange={(e) => setForm({ ...form, data: { ...form.data, reason: e.target.value } })}/></LgField>
              <LgField label="來源"><input style={lgInput} value={form.data.source || ""} onChange={(e) => setForm({ ...form, data: { ...form.data, source: e.target.value } })} placeholder="如:信用中國/內部風控"/></LgField>
            </div>
            <div className="row gap-8" style={{ marginTop: 16, justifyContent: "flex-end" }}><button className="btn" onClick={() => setForm(null)}>取消</button><button className="btn btn-primary" disabled={busy || !form.data.party_name} onClick={() => submit("/api/legal/watchlist", form.data)}>保存</button></div>
          </div>
        </div>
      )}
      {verifyRes && (
        <div className="risk-drawer-mask" style={{ zIndex: 600 }} onClick={() => setVerifyRes(null)}>
          <div className="card" style={{ maxWidth: 520, margin: "8vh auto", padding: 20 }} onClick={(e) => e.stopPropagation()}>
            <div className="row spread" style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 16, fontWeight: 900 }}>憑證驗真</div>
              <button className="btn btn-sm" onClick={() => setVerifyRes(null)}><Icon name="x" size={15}/></button>
            </div>
            {verifyRes.loading ? <div className="muted" style={{ fontSize: 13 }}>驗真中…</div> : (
              <div className="col gap-10">
                <div style={{ fontSize: 14, fontWeight: 900, color: verifyRes.verified ? "#0a7f3f" : "#b42318" }}>
                  {verifyRes.verified ? "✓ 驗真通過,內容完好未被篡改" : `✗ 驗真未通過${verifyRes.error ? ":" + verifyRes.error : ",內容可能已被篡改"}`}
                </div>
                {verifyRes.serial_no && (
                  <div className="col gap-6" style={{ fontSize: 12.5 }}>
                    <div><span className="muted">憑證編號</span> <span style={{ fontFamily: "monospace" }}>{verifyRes.serial_no}</span></div>
                    <div><span className="muted">驗真碼</span> <span style={{ fontFamily: "monospace" }}>{verifyRes.verify_code}</span></div>
                    <div><span className="muted">類型/階段</span> {SEAL_DOC[verifyRes.doc_type] || verifyRes.doc_type || "—"} · {verifyRes.stage || "—"}</div>
                    <div><span className="muted">簽發</span> {verifyRes.issued_by || "—"} · {verifyRes.issued_at || "—"}</div>
                    <div style={{ wordBreak: "break-all" }}><span className="muted">內容哈希</span> <span style={{ fontFamily: "monospace", fontSize: 11 }}>{verifyRes.content_hash}</span></div>
                  </div>
                )}
                <div className="row gap-8" style={{ justifyContent: "flex-end" }}>
                  {verifyRes.serial_no && <button className="btn btn-sm" onClick={() => downloadCert(verifyRes.serial_no)}>下載憑證</button>}
                  <button className="btn btn-sm btn-primary" onClick={() => setVerifyRes(null)}>關閉</button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      {form && form.type === "seal" && (
        <div className="risk-drawer-mask" style={{ zIndex: 600 }} onClick={() => setForm(null)}>
          <div className="card" style={{ maxWidth: 460, margin: "8vh auto", padding: 20 }} onClick={(e) => e.stopPropagation()}>
            <div className="row spread" style={{ marginBottom: 14 }}><div style={{ fontSize: 16, fontWeight: 900 }}>{form.data.id ? "編輯印章" : "錄入印章"}</div><button className="btn btn-sm" onClick={() => setForm(null)}><Icon name="x" size={15}/></button></div>
            <div className="col gap-12">
              <LgField label="印章名稱 *"><input style={lgInput} value={form.data.seal_name || ""} onChange={(e) => setForm({ ...form, data: { ...form.data, seal_name: e.target.value } })}/></LgField>
              <LgField label="類型"><select style={lgInput} value={form.data.seal_type || "company"} onChange={(e) => setForm({ ...form, data: { ...form.data, seal_type: e.target.value } })}><option value="company">公章</option><option value="contract">合同章</option><option value="finance">財務章</option><option value="legal_rep">法人章</option><option value="invoice">發票章</option><option value="other">其他</option></select></LgField>
            </div>
            <div className="row gap-8" style={{ marginTop: 16, justifyContent: "flex-end" }}><button className="btn" onClick={() => setForm(null)}>取消</button><button className="btn btn-primary" disabled={busy || !form.data.seal_name} onClick={() => submit("/api/legal/seals", form.data)}>保存</button></div>
          </div>
        </div>
      )}
    </div>
  );
};
