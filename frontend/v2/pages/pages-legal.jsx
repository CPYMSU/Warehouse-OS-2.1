/* WAREHOUSE 2.0 · 法務 — Swiss 版式,真後端
   讀:/api/legal/overview(合同/證照/里程碑/印章/名單/匯總)
       /api/compliance/chain-check(鋼印全鏈完整性)
       /api/compliance/by-subject(單合同鋼印鏈)
   寫:一律交秘書(起草/登記/審查/封印/核驗/跟進爭議/續期/用印/核查) */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "法務": "Legal",
  "刷新": "Refresh",
  "合同 {a} 份 · 證照 {b} 項 · 鋼印 {c} 道 · 頁面只讀,操作交秘書": "{a} contracts · {b} licenses · {c} seals · read-only, actions via Secretary",
  "讀取法務數據中…": "Loading legal data…",
  "起草合同": "Draft contract",
  "新建合同": "New contract",
  "在管合同": "Active contracts",
  "份": "", "項": "", "道": "", "個": "",
  "共 {n} 份台賬": "{n} on ledger",
  "在管金額": "Active amount",
  "元": "CNY", "萬元": "×10⁴ CNY", "億元": "×10⁸ CNY",
  "生效 · 履約 · 已簽合計": "Active + performing + signed",
  "風險信號": "Risk signals",
  "讓秘書梳理 →": "Secretary triage →",
  "全部平穩": "All clear",
  "鋼印鏈": "Seal chain",
  "鏈條連續": "Chain intact",
  "交秘書核驗 →": "Verify via Secretary →",
  "流程跨步即封印": "Seal at each step",
  "搜索合同 / 編號 / 相對方": "Search contract / no. / counterparty",
  "全部": "All", "生效履約": "Active", "草稿審查": "Drafting", "關閉歸檔": "Closed",
  "合同台賬": "Contract ledger",
  "{n} 份 · 點行看詳情與鋼印鏈": "{n} contracts · click a row for details & seal chain",
  "合同": "Contract", "相對方": "Counterparty", "金額": "Amount", "到期": "Expiry",
  "履約節點": "Milestones", "狀態": "Status", "交給秘書": "Secretary",
  "待辦 {n}": "{n} open",
  "暫無合同": "No contracts yet",
  "對秘書說「新建合同」即可登記第一份;或先讓秘書起草條款框架。": "Tell the Secretary \"new contract\" to register the first one — or have it draft the clause framework first.",
  "當前篩選下沒有合同": "No contracts under this filter",
  "換個篩選或關鍵詞,或直接問秘書「幫我找◯◯合同」。": "Try another filter, or just ask the Secretary to find it.",
  "秘書審查": "Review", "封存鋼印": "Issue seal", "跟進爭議": "Follow up dispute",
  "採購": "Purchase", "銷售": "Sales", "服務": "Service", "租賃": "Lease",
  "勞動": "Labor", "框架": "Framework", "其他": "Other",
  "草稿": "Draft", "審查中": "In review", "已批": "Approved", "已簽": "Signed",
  "生效": "Active", "履約中": "Performing", "完成": "Completed",
  "終止": "Terminated", "歸檔": "Archived",
  "逾期 {n} 天": "{n}d overdue", "剩 {n} 天": "{n}d left",
  "簽署日": "Sign date", "生效日": "Effective", "到期日": "Expiry date", "風險等級": "Risk level",
  "低": "Low", "中": "Medium", "高": "High",
  "鋼印鏈 · 防篡改": "Seal chain · tamper-proof",
  "讀取鋼印鏈…": "Loading seal chain…",
  "暫無鋼印。流程每跨一步(起草/審查/簽署)封一道不可篡改鋼印,事後改動立即可見。": "No seals yet. Each step (draft / review / sign) leaves one tamper-proof seal — later edits show at once.",
  "完好": "Intact", "異常": "Broken", "驗真": "Verify",
  "起草封存": "Draft sealed", "審查通過": "Review passed", "用印": "Seal use", "簽署": "Signed",
  "直接吩咐秘書": "Tell the Secretary",
  "提交審查": "Submit review", "核驗鋼印": "Verify seals",
  "2.0 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.0 rule: read-only page; changes run via Secretary confirmation, fully audited.",
  "鋼印鏈完整性": "Seal-chain integrity",
  "哈希鏈 + HMAC 簽名": "Hash chain + HMAC signature",
  "全鏈核驗": "Verify full chain",
  "連續": "INTACT", "有斷裂": "BROKEN", "尚無鋼印": "NO SEALS",
  "完好 {a} / 共 {b} 道": "{a} of {b} intact",
  "斷裂環節": "Broken links",
  "每跨一步封一道鋼印:內容哈希 + 簽名 + 前後相扣的哈希鏈。起草、審查、簽署、用印、歸檔各留一道,事後任何改動都會讓鏈條當場斷裂。": "One seal per step: content hash + signature + interlocked hash chain. Draft, review, signing, seal-use and archiving each leave a seal — any later edit snaps the chain on the spot.",
  "風險與爭議": "Risk & disputes",
  "逾期履約 · 到期合同證照 · 硬閘名單": "Overdue milestones · expiring contracts & licenses · hard-gate list",
  "全部交秘書跟進": "Secretary follow-up on all",
  "硬閘名單": "Hard-gate hit", "履約逾期": "Milestone overdue",
  "合同到期": "Contract expiring", "證照到期": "License expiring",
  "目前沒有風險與爭議事項": "No risks or disputes",
  "合同、證照、履約與名單全部平穩。秘書持續盯防,有風吹草動會第一時間出現在這裡。": "Contracts, licenses, milestones and watchlist are all clear. The Secretary keeps watch — anything off shows up here first.",
  "交秘書跟進": "Follow up",
  "應於 {d}": "due {d}",
  "證照台賬": "License ledger",
  "{n} 項 · 到期進預警": "{n} · expiry feeds alerts",
  "暫無證照。對秘書說「錄入證照」即可登記。": "No licenses. Tell the Secretary \"add license\" to register one.",
  "營業執照": "Business license", "資質證書": "Qualification", "許可證": "Permit",
  "認證": "Certification", "人員證書": "Personnel cert",
  "有效": "Valid", "臨期": "Expiring", "已過期": "Expired", "吊銷": "Revoked",
  "本企業": "Own company",
  "安排續期": "Renew",
  "印章與合規名單": "Seals & watchlist",
  "用印走工作流 · 名單提交審查時硬閘": "Seal-use via workflow · watchlist hard-gates reviews",
  "印章": "Company seals",
  "暫無印章。對秘書說「錄入印章」即可登記。": "No seals registered. Tell the Secretary \"add a seal\" to register one.",
  "發起用印": "Request seal use",
  "本人確認簽署": "Confirm signing",
  "Face ID / Passkey 本人確認": "Face ID / passkey verification",
  "選擇要簽署的最終文件": "Choose the final document to sign",
  "選擇已蓋章文件": "Choose the stamped document",
  "平台會把本人驗證、文件 SHA-256、當前合同版本與公司綁定;不會收到你的面部或指紋資料。": "The platform binds device verification to the file SHA-256, current contract revision and company. Your face or fingerprint never reaches the platform.",
  "完成本人確認": "Verify and complete",
  "正在計算文件哈希…": "Hashing document…",
  "正在等待裝置驗證…": "Waiting for device verification…",
  "正在安全歸檔…": "Archiving securely…",
  "請先選擇文件": "Choose a file first",
  "所選文件不是審查鎖定版本，請改選已審批的合同文件。": "The selected file is not the reviewed contract revision. Choose the approved file.",
  "此操作需要先在帳號安全中新增 Passkey。": "Add a passkey under Account Security first.",
  "已完成並留證": "Completed and archived",
  "待完成用印": "Approved seal uses",
  "審批已完成;上傳實際蓋章後的掃描件，再以本人 Passkey 完成留證。": "Approval is complete. Upload the actually stamped scan, then verify with your passkey to archive the evidence.",
  "完成用印留證": "Archive stamped evidence",
  "暫無已批准、待留證的用印事項": "No approved seal uses awaiting evidence",
  "本系統本人確認是可稽核的簽署留證;若業務要求法定 CA 電子簽章，仍須接入合規電子簽服務。": "This is auditable identity evidence. Where a regulated CA e-signature is required, use an approved e-sign provider.",
  "公章": "Company seal", "合同章": "Contract seal", "財務章": "Finance seal",
  "法人章": "Legal-rep seal", "發票章": "Invoice seal",
  "保管人": "Holder", "未指定": "Unassigned",
  "合規名單": "Compliance watchlist",
  "黑名單": "Blacklist", "制裁": "Sanction", "失信": "Dishonest", "利益衝突": "Conflict of interest",
  "暫無名單記錄。建合同前會自動核查相對方。": "No watchlist entries. Counterparties are auto-checked before contracts.",
  "核查": "Check",
  "已逾期 {n} 天": "{n} days overdue", "將於 {d} 到期": "expiring on {d}",
  // 秘書指令(用戶氣泡可見,一併翻譯)
  "我要起草一份合同。請先追問我:合同名稱與類型、相對方、標的與金額、關鍵商務條件;之後讀取法務台賬上下文,產出條款框架、審查清單、履約里程碑建議與合規注意事項,並聲明需法務人工覆核。":
    "I want to draft a contract. Ask me first: title & type, counterparty, subject & amount, key commercial terms; then read the legal ledger context and produce a clause framework, review checklist, milestone suggestions and compliance notes, stating that human legal review is required.",
  "我要新建一份合同並登記進台賬。請逐項追問:①名稱 ②類型 ③相對方(先做准入核查,命中黑名單/制裁要告知)④金額 ⑤簽署/生效/到期日期 ⑥風險等級;齊全後登記為草稿並回報合同編號。":
    "I want to register a new contract. Ask item by item: 1) title 2) type 3) counterparty (run the access check first, flag blacklist/sanction hits) 4) amount 5) sign/effective/expiry dates 6) risk level; then register it as a draft and report the contract number.",
  "請審查合同 {no}「{title}」(相對方:{cp}):先讀法務台賬與相對方准入核查,輸出審查問題、合規硬閘、需補充文件與簽署前置條件,經我確認後再推進。":
    "Review contract {no} \"{title}\" (counterparty: {cp}): read the legal ledger and the counterparty access check first, then output review issues, compliance hard gates, missing documents and signing preconditions. Proceed only after my confirmation.",
  "合同 {no}「{title}」還是草稿,請提交合同審查流程;若相對方命中黑名單/制裁,先停下來告訴我,經我確認再處理。":
    "Contract {no} \"{title}\" is still a draft — submit it for review. If the counterparty hits the blacklist/sanction list, stop and tell me first.",
  "請為合同 {no}「{title}」當前「{st}」狀態封存一道防篡改鋼印,payload 記錄合同名、相對方、金額、狀態與時間,並回報鋼印編號。":
    "Issue one tamper-proof seal for contract {no} \"{title}\" at its current \"{st}\" state; record title, counterparty, amount, status and time in the payload, and report the seal serial.",
  "請核驗合同 {no}「{title}」的鋼印鏈:逐道驗真內容哈希、簽名與鏈條連續性,發現異常立刻告訴我。":
    "Verify the seal chain of contract {no} \"{title}\": check content hash, signature and chain continuity seal by seal; report any anomaly at once.",
  "請驗真鋼印 {serial}({doc}):回報內容是否完好、簽名是否有效、鏈條是否連續。":
    "Verify seal {serial} ({doc}): report whether the content is intact, the signature valid and the chain continuous.",
  "合同 {no}「{title}」可能有爭議,請整理履約節點、款項與鋼印留證形成證據清單,再給我跟進與談判方案;先不要對外發任何函件。":
    "Contract {no} \"{title}\" may be in dispute. Compile milestones, payments and seal evidence into an evidence list, then give me a follow-up and negotiation plan. Do not send anything externally yet.",
  "請對防篡改鋼印做一次全鏈完整性核驗,定位被破壞的環節並回報處置建議。":
    "Run a full-chain integrity check on the tamper-proof seals, locate any broken link and report remediation advice.",
  "請梳理快到期/已逾期的合同、證照與履約里程碑,按風險排序,給出續簽、續期與責任人跟進建議。":
    "Triage expiring/overdue contracts, licenses and milestones; rank by risk and give renewal and owner follow-up suggestions.",
  "證照「{title}」{when},請安排續期:列出辦理機關、所需材料與時限,並設置提醒。":
    "License \"{title}\" is {when}. Arrange renewal: list the issuing authority, required documents and deadlines, and set a reminder.",
  "我要使用印章「{name}」,請追問用印用途與文件後發起用印工作流(保管人留憑證)。":
    "I need to use the seal \"{name}\". Ask for the purpose and document, then start the seal-use workflow (holder keeps evidence).",
  "請核查相對方「{name}」:先做本地名單硬閘核查,再查公開失信/制裁/行政處罰/訴訟線索,列出來源與日期;只作線索不作法律意見。":
    "Check counterparty \"{name}\": run the local hard-gate list first, then public dishonesty/sanction/penalty/litigation leads, citing sources and dates. Leads only, not legal advice.",
  "跟進這件法務事項:{kind} — {title}({sub})。請核實現狀,給出處置步驟與責任人建議;需要動台賬先問我。":
    "Follow up this legal item: {kind} — {title} ({sub}). Verify the current state and give handling steps and an owner suggestion; ask me before touching the ledger.",
  "把法務的風險與爭議事項全部過一遍:逾期履約、快到期合同與證照、硬閘名單命中,逐條給我跟進方案與優先級。":
    "Go through all legal risk & dispute items: overdue milestones, expiring contracts and licenses, hard-gate hits — give me a follow-up plan and priority for each.",
});
const { useState: _s, useEffect: _e, useMemo: _mm, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

/* ── 字典(1.0 對齊)── */
const CTYPE = { purchase: "採購", sales: "銷售", service: "服務", lease: "租賃", labor: "勞動", framework: "框架", other: "其他" };
const CSTAT = {
  draft: ["plain", "草稿"], reviewing: ["warn", "審查中"], approved: ["ok", "已批"], signed: ["ok", "已簽"],
  active: ["ok", "生效"], performing: ["ok", "履約中"], completed: ["plain", "完成"],
  terminated: ["bad", "終止"], expired: ["bad", "到期"], archived: ["plain", "歸檔"],
};
const LTYPE = { business: "營業執照", qualification: "資質證書", permit: "許可證", certification: "認證", personnel: "人員證書", other: "其他" };
const LSTAT = { valid: ["ok", "有效"], expiring: ["warn", "臨期"], expired: ["bad", "已過期"], revoked: ["bad", "吊銷"] };
const STYPE = { company: "公章", contract: "合同章", finance: "財務章", legal_rep: "法人章", invoice: "發票章", other: "其他" };
const SEAL_DOC = { contract_draft: "起草封存", review_passed: "審查通過", seal_use: "用印", signed: "簽署", archived: "歸檔" };
const WL = { blacklist: ["bad", "黑名單"], sanction: ["bad", "制裁"], dishonest: ["warn", "失信"], conflict: ["warn", "利益衝突"] };

const yuan = (v) => (v == null || v === "") ? "—" : "¥" + Number(v || 0).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const daysTo = (s) => { if (!s) return null; const d = Math.ceil((new Date(s) - Date.now()) / 86400000); return Number.isFinite(d) ? d : null; };
const DayTag = ({ date }) => {
  const n = daysTo(date);
  if (n === null) return null;
  if (n < 0) return <T tone="bad" dot>{t("逾期 {n} 天", { n: -n })}</T>;
  if (n <= 30) return <T tone="warn" dot>{t("剩 {n} 天", { n })}</T>;
  if (n <= 60) return <T tone="warn">{t("剩 {n} 天", { n })}</T>;
  return <span className="muted num" style={{ fontSize: 11 }}>{t("剩 {n} 天", { n })}</span>;
};
const statTag = (map, key) => { const [tone, label] = map[key] || ["plain", key || "—"]; return <T tone={tone}>{t(label)}</T>; };

/* ── 秘書指令 ── */
const pDraft = () => t("我要起草一份合同。請先追問我:合同名稱與類型、相對方、標的與金額、關鍵商務條件;之後讀取法務台賬上下文,產出條款框架、審查清單、履約里程碑建議與合規注意事項,並聲明需法務人工覆核。");
const pNew = () => t("我要新建一份合同並登記進台賬。請逐項追問:①名稱 ②類型 ③相對方(先做准入核查,命中黑名單/制裁要告知)④金額 ⑤簽署/生效/到期日期 ⑥風險等級;齊全後登記為草稿並回報合同編號。");
const cRef = (c) => ({ no: c.contract_no || c.id || "—", title: c.title || "—" });
const pReview = (c) => t("請審查合同 {no}「{title}」(相對方:{cp}):先讀法務台賬與相對方准入核查,輸出審查問題、合規硬閘、需補充文件與簽署前置條件,經我確認後再推進。", { ...cRef(c), cp: c.counterparty_display || c.counterparty_name || "—" });
const pSubmit = (c) => t("合同 {no}「{title}」還是草稿,請提交合同審查流程;若相對方命中黑名單/制裁,先停下來告訴我,經我確認再處理。", cRef(c));
const pSealIssue = (c) => t("請為合同 {no}「{title}」當前「{st}」狀態封存一道防篡改鋼印,payload 記錄合同名、相對方、金額、狀態與時間,並回報鋼印編號。", { ...cRef(c), st: t((CSTAT[c.status] || ["", c.status || "—"])[1]) });
const pSealVerify = (c) => t("請核驗合同 {no}「{title}」的鋼印鏈:逐道驗真內容哈希、簽名與鏈條連續性,發現異常立刻告訴我。", cRef(c));
const pSealOne = (s) => t("請驗真鋼印 {serial}({doc}):回報內容是否完好、簽名是否有效、鏈條是否連續。", { serial: s.serial_no || "—", doc: t(SEAL_DOC[s.doc_type] || s.doc_type || "—") });
const pDispute = (c) => t("合同 {no}「{title}」可能有爭議,請整理履約節點、款項與鋼印留證形成證據清單,再給我跟進與談判方案;先不要對外發任何函件。", cRef(c));
const pChainAll = () => t("請對防篡改鋼印做一次全鏈完整性核驗,定位被破壞的環節並回報處置建議。");
const pExpiry = () => t("請梳理快到期/已逾期的合同、證照與履約里程碑,按風險排序,給出續簽、續期與責任人跟進建議。");
const pLicense = (l) => { const n = daysTo(l.expiry_date); const when = n !== null && n < 0 ? t("已逾期 {n} 天", { n: -n }) : t("將於 {d} 到期", { d: l.expiry_date || "—" }); return t("證照「{title}」{when},請安排續期:列出辦理機關、所需材料與時限,並設置提醒。", { title: l.title || "—", when }); };
const pSealUse = (sl) => t("我要使用印章「{name}」,請追問用印用途與文件後發起用印工作流(保管人留憑證)。", { name: sl.seal_name || "—" });
const pWatch = (w) => t("請核查相對方「{name}」:先做本地名單硬閘核查,再查公開失信/制裁/行政處罰/訴訟線索,列出來源與日期;只作線索不作法律意見。", { name: w.party_display || w.party_name || "—" });
const pRisk = (r) => t("跟進這件法務事項:{kind} — {title}({sub})。請核實現狀,給出處置步驟與責任人建議;需要動台賬先問我。", { kind: t(r.kind), title: r.title, sub: r.sub });
const pRiskAll = () => t("把法務的風險與爭議事項全部過一遍:逾期履約、快到期合同與證照、硬閘名單命中,逐條給我跟進方案與優先級。");

const fileEvidence = async (file) => {
  if (!file) throw new Error(t("請先選擇文件"));
  if (file.size > 5 * 1024 * 1024) throw new Error("文件超過 5MB 限制");
  const data = await file.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", data);
  const sha256 = Array.from(new Uint8Array(digest)).map(x => x.toString(16).padStart(2, "0")).join("");
  const bytes = new Uint8Array(data);
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode.apply(null, bytes.subarray(offset, Math.min(offset + 0x8000, bytes.length)));
  }
  return { sha256, base64: btoa(binary), name: file.name || "document.bin", mime: file.type || "application/octet-stream" };
};

const LegalIdentityDialog = ({ action, onClose, onDone }) => {
  const [file, setFile] = _s(null);
  const [busy, setBusy] = _s(false);
  const [stage, setStage] = _s("");
  const [err, setErr] = _s("");
  const isContract = action && action.kind === "contract";
  const target = action && action.target || {};
  const submit = async () => {
    if (busy) return;
    if (!file) { setErr(t("請先選擇文件")); return; }
    if (!W2.Passkeys || !W2.Passkeys.supported()) { setErr(t("此操作需要先在帳號安全中新增 Passkey。")); return; }
    setBusy(true); setErr("");
    try {
      setStage(t("正在計算文件哈希…"));
      const evidence = await fileEvidence(file);
      if (isContract) {
        if (target.review_document_sha256 && target.review_document_sha256 !== evidence.sha256) {
          throw new Error(t("所選文件不是審查鎖定版本，請改選已審批的合同文件。"));
        }
        const resource = { contract_id: target.id, document_sha256: evidence.sha256 };
        setStage(t("正在等待裝置驗證…"));
        const stepUpToken = await W2.Passkeys.requestStepUp("legal.contract.sign", resource);
        setStage(t("正在安全歸檔…"));
        await W2.post(`/api/legal/contracts/${encodeURIComponent(target.id)}/sign`, {
          document_sha256: evidence.sha256,
          document_base64: evidence.base64,
          file_name: evidence.name,
          file_mime: evidence.mime,
          step_up_token: stepUpToken,
        }, { suppressAuthExpired: true });
      } else {
        const resource = {
          seal_id: target.seal_id,
          wf_instance_id: target.wf_instance_id,
          document_sha256: target.document_sha256,
          stamped_doc_sha256: evidence.sha256,
        };
        setStage(t("正在等待裝置驗證…"));
        const stepUpToken = await W2.Passkeys.requestStepUp("legal.seal.stamp", resource);
        setStage(t("正在安全歸檔…"));
        await W2.post(`/api/legal/seals/${encodeURIComponent(target.seal_id)}/stamp`, {
          wf_instance_id: target.wf_instance_id,
          purpose: target.purpose,
          document_name: evidence.name,
          document_sha256: target.document_sha256,
          stamped_doc_base64: evidence.base64,
          step_up_token: stepUpToken,
        }, { suppressAuthExpired: true });
      }
      setStage(t("已完成並留證"));
      await onDone();
    } catch (error) {
      const friendly = W2.Passkeys && W2.Passkeys.friendlyError ? W2.Passkeys.friendlyError(error) : error;
      setErr((friendly && friendly.message) || String(error));
      setBusy(false); setStage("");
    }
  };
  if (!action) return null;
  return (
    <div role="presentation" onClick={() => !busy && onClose()} style={{ position: "fixed", inset: 0, zIndex: 180, background: "rgba(10,10,10,.45)", display: "grid", placeItems: "center", padding: 18 }}>
      <section role="dialog" aria-modal="true" aria-labelledby="legal-passkey-title" className="panel col g16" onClick={event => event.stopPropagation()} style={{ width: "min(560px,100%)", maxHeight: "90vh", overflowY: "auto", padding: 22, border: "2px solid var(--rule)", background: "var(--paper)" }}>
        <div className="row spread">
          <div>
            <LB dim>{t("Face ID / Passkey 本人確認")}</LB>
            <div id="legal-passkey-title" style={{ fontSize: 20, fontWeight: 800, marginTop: 5 }}>{isContract ? t("本人確認簽署") : t("完成用印留證")}</div>
          </div>
          <button className="btn ghost sm" disabled={busy} onClick={onClose}><I name="x" size={14}/></button>
        </div>
        <div style={{ borderTop: "2px solid var(--rule)", paddingTop: 14 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{isContract ? (target.title || target.contract_no) : (target.seal_name || target.instance_no)}</div>
          <div className="muted num" style={{ fontSize: 11.5, marginTop: 4, wordBreak: "break-all" }}>
            {isContract ? (target.contract_no || "—") : `${target.instance_no || "—"} · ${target.document_sha256 || "—"}`}
          </div>
        </div>
        <label className="col g8">
          <LB>{isContract ? t("選擇要簽署的最終文件") : t("選擇已蓋章文件")}</LB>
          <input className="field" type="file" disabled={busy} onChange={event => setFile(event.target.files && event.target.files[0] || null)}/>
        </label>
        <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.7 }}>{t("平台會把本人驗證、文件 SHA-256、當前合同版本與公司綁定;不會收到你的面部或指紋資料。")}</div>
        {isContract && <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>{t("本系統本人確認是可稽核的簽署留證;若業務要求法定 CA 電子簽章，仍須接入合規電子簽服務。")}</div>}
        {err && <div role="alert" style={{ color: "var(--red)", fontSize: 12.5, lineHeight: 1.6 }}>{err}</div>}
        <div className="row spread wrap g8">
          <span className="muted" aria-live="polite" style={{ fontSize: 11.5 }}>{stage}</span>
          <div className="row g8"><B disabled={busy} onClick={onClose}>{t("取消")}</B><B kind="primary" icon="user" disabled={busy || !file} onClick={submit}>{t("完成本人確認")}</B></div>
        </div>
      </section>
    </div>
  );
};

/* ── 合同抽屜:詳情 + 鋼印鏈 ── */
const ContractDrawer = ({ c, seals, onClose, onSign }) => {
  const stat = CSTAT[c.status] || ["plain", c.status || "—"];
  const canSign = ["reviewing", "approved"].includes(c.status)
    && c.review && ["running", "waiting"].includes(c.review.status)
    && c.review.current_node_key === "n_sign";
  const facts = [
    [t("相對方"), c.counterparty_display || c.counterparty_name || "—"],
    [t("金額"), yuan(c.amount)],
    [t("簽署日"), c.sign_date || "—"],
    [t("生效日"), c.effective_date || "—"],
    [t("到期日"), c.expiry_date || "—"],
    [t("風險等級"), t({ low: "低", medium: "中", high: "高" }[c.risk_level] || c.risk_level || "—")],
  ];
  const acts = [
    c.status === "draft"
      ? ["clipboard", "提交審查", pSubmit(c)]
      : ["sparkle", "秘書審查", pReview(c)],
    ["shield", "封存鋼印", pSealIssue(c)],
    ["scan", "核驗鋼印", pSealVerify(c)],
    ["gavel", "跟進爭議", pDispute(c)],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            <T tone={stat[0]} dot>{t(stat[1])}</T>
            <T tone="plain">{t(CTYPE[c.contract_type] || "其他")}</T>
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 18, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.3 }}>{c.title || "—"}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{c.contract_no || "—"}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 270px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {facts.map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 13.5, fontWeight: 650, wordBreak: "break-all" }}>{v}</span>
            </div>
          ))}
        </div>

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("鋼印鏈 · 防篡改")}</LB>
        <div style={{ borderTop: "2px solid var(--rule)", marginBottom: 18 }}>
          {seals === undefined && <div className="muted" style={{ fontSize: 12, padding: "10px 0" }}>{t("讀取鋼印鏈…")}</div>}
          {Array.isArray(seals) && !seals.length &&
            <div className="muted" style={{ fontSize: 12, padding: "10px 0", lineHeight: 1.6 }}>{t("暫無鋼印。流程每跨一步(起草/審查/簽署)封一道不可篡改鋼印,事後改動立即可見。")}</div>}
          {Array.isArray(seals) && seals.map((s, i) => (
            <div key={s.serial_no || i} className="row g10" style={{ padding: "9px 0", borderBottom: "1px solid var(--hair-soft)" }}>
              <span className="lr-idx" style={{ width: 20 }}>{pad2(i + 1)}</span>
              <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                <span className="row g8" style={{ fontSize: 12.5, fontWeight: 650 }}>
                  {t(SEAL_DOC[s.doc_type] || s.doc_type || "—")}
                  {s.verified === false ? <T tone="bad" dot>{t("異常")}</T> : s.verified ? <T tone="ok" dot>{t("完好")}</T> : null}
                </span>
                <span className="num muted" style={{ fontSize: 10.5, wordBreak: "break-all" }}>{s.serial_no || "—"}{s.issued_at ? " · " + s.issued_at : ""}</span>
              </div>
              <button className="btn sm" style={{ padding: "0 9px" }} onClick={() => ask(pSealOne(s))}>{t("驗真")}</button>
            </div>
          ))}
        </div>

        {canSign && (
          <div style={{ border: "2px solid var(--rule)", padding: 12, marginBottom: 18 }}>
            <div className="row spread wrap g8">
              <div className="col g4" style={{ flex: 1, minWidth: 180 }}>
                <LB dim>{t("Face ID / Passkey 本人確認")}</LB>
                <span className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>{t("平台會把本人驗證、文件 SHA-256、當前合同版本與公司綁定;不會收到你的面部或指紋資料。")}</span>
              </div>
              <B kind="primary" size="sm" icon="user" onClick={() => onSign(c)}>{t("本人確認簽署")}</B>
            </div>
          </div>
        )}

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {acts.map(([icon, label, prompt]) => (
            <button key={label} className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(prompt)}>
              <I name={icon} size={14}/>{t(label)}
            </button>
          ))}
        </div>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("2.0 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
      </div>
    </div>
  );
};

/* ═══ 16 · 法務 ═══ */
const Page = () => {
  const [d, setD] = _s(null);
  const [chain, setChain] = _s(null);
  const [q, setQ] = _s("");
  const [scope, setScope] = _s("all");
  const [sel, setSel] = _s(null);
  const [identityAction, setIdentityAction] = _s(null);
  const [sealMap, setSealMap] = _s({});
  const searchRef = _r(null);

  const load = () => {
    W2.json("/api/legal/overview").then(x => setD(x && typeof x === "object" ? x : {})).catch(() => setD({}));
    W2.json("/api/compliance/chain-check").then(x => setChain(x && typeof x === "object" ? x : {})).catch(() => setChain({}));
  };
  _e(() => {
    load();
    const h = (e) => {
      if (e.key === "/" && document.activeElement !== searchRef.current) { e.preventDefault(); searchRef.current && searchRef.current.focus(); }
      if (e.key === "Escape") setSel(null);
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);
  _e(() => {
    const cid = sel && sel.id;
    if (!cid || sealMap[cid] !== undefined) return;
    W2.json("/api/compliance/by-subject?type=legal_contract&id=" + encodeURIComponent(cid))
      .then(j => setSealMap(m => ({ ...m, [cid]: Array.isArray(j && j.seals) ? j.seals : [] })))
      .catch(() => setSealMap(m => ({ ...m, [cid]: [] })));
  }, [sel]);

  if (d === null) return (
    <>
      <Folio no="16" en="LEGAL" title={t("法務")}/>
      <div className="muted" style={{ fontSize: 13, padding: "26px 0" }}>{t("讀取法務數據中…")}</div>
    </>
  );

  const s = d.summary || {};
  const contracts = Array.isArray(d.contracts) ? d.contracts : [];
  const licenses = Array.isArray(d.licenses) ? d.licenses : [];
  const milestones = Array.isArray(d.milestones) ? d.milestones : [];
  const stamps = Array.isArray(d.seals) ? d.seals : [];      // 實體印章
  const approvedSealUses = Array.isArray(d.approved_seal_uses) ? d.approved_seal_uses : [];
  const watchlist = Array.isArray(d.watchlist) ? d.watchlist : [];
  const ch = chain || {};
  const chTotal = num(ch.total);
  const chBroken = num(ch.broken_count);

  /* 風險與爭議(讀視圖推導,與 1.0 信號卡同源) */
  const closed = ["terminated", "completed", "archived"];
  const expCon = contracts.filter(c => { const n = daysTo(c.expiry_date); return n !== null && n <= 60 && closed.indexOf(c.status) < 0; });
  const expLic = licenses.filter(l => { const n = daysTo(l.expiry_date); return (n !== null && n <= 60) || l.status === "expired" || l.status === "expiring"; });
  const overMs = milestones.filter(m => { const n = daysTo(m.due_date); return n !== null && n < 0; });
  const hardWl = watchlist.filter(w => w.list_type === "blacklist" || w.list_type === "sanction");
  const risks = [
    ...hardWl.map(w => ({ tone: "bad", kind: "硬閘名單", title: w.party_display || w.party_name || "—", sub: t((WL[w.list_type] || ["", w.list_type])[1]) + (w.reason ? " · " + w.reason : ""), prompt: pWatch(w) })),
    ...overMs.map(m => { const n = daysTo(m.due_date); return { tone: "bad", kind: "履約逾期", title: (m.contract_title || "—") + " · " + (m.name || "—"), sub: t("應於 {d}", { d: m.due_date || "—" }) + (n !== null ? " · " + t("逾期 {n} 天", { n: -n }) : ""), prompt: pDispute({ contract_no: m.contract_no, id: m.contract_id, title: m.contract_title }) }; }),
    ...expCon.map(c => { const n = daysTo(c.expiry_date); return { tone: "warn", kind: "合同到期", title: c.title || "—", sub: (c.expiry_date || "—") + (n !== null ? " · " + (n < 0 ? t("逾期 {n} 天", { n: -n }) : t("剩 {n} 天", { n })) : ""), prompt: pReview(c) }; }),
    ...expLic.map(l => { const n = daysTo(l.expiry_date); return { tone: "warn", kind: "證照到期", title: l.title || "—", sub: (l.expiry_date || "—") + (n !== null ? " · " + (n < 0 ? t("逾期 {n} 天", { n: -n }) : t("剩 {n} 天", { n })) : ""), prompt: pLicense(l) }; }),
  ].slice(0, 12);
  const riskN = hardWl.length + overMs.length + expCon.length + expLic.length;

  /* KPI:金額緊湊格式 */
  const amt = num(s.contract_amount);
  const amtV = amt >= 1e8 ? (amt / 1e8).toFixed(amt >= 1e9 ? 0 : 1) : amt >= 1e4 ? (amt / 1e4).toFixed(amt >= 1e6 ? 0 : 1) : String(Math.round(amt));
  const amtU = amt >= 1e8 ? "億元" : amt >= 1e4 ? "萬元" : "元";

  /* 合同篩選 */
  const SCOPES = {
    all: null,
    live: ["active", "performing", "signed"],
    pre: ["draft", "reviewing", "approved"],
    end: ["completed", "terminated", "expired", "archived"],
  };
  let list = contracts;
  if (SCOPES[scope]) list = list.filter(c => SCOPES[scope].indexOf(c.status) >= 0);
  if (q) list = list.filter(c => ((c.title || "") + (c.contract_no || "") + (c.counterparty_display || "") + (c.counterparty_name || "")).toLowerCase().includes(q.toLowerCase()));

  const chWord = chain === null ? "…" : chTotal === 0 ? t("尚無鋼印") : chBroken ? t("有斷裂") : t("連續");
  const chColor = chBroken ? "var(--red)" : chTotal ? "var(--ink)" : "var(--ink-3)";

  return (
    <>
      <Folio no="16" en="LEGAL" title={t("法務")}
        sub={t("合同 {a} 份 · 證照 {b} 項 · 鋼印 {c} 道 · 頁面只讀,操作交秘書", { a: num(s.contract_count), b: num(s.license_count), c: chTotal })}
        right={<>
          <B icon="refresh" onClick={() => { setD(null); setChain(null); setSealMap({}); setSel(null); load(); }}>{t("刷新")}</B>
          <B icon="doc" onClick={() => ask(pDraft())}>{t("起草合同")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(pNew())}>{t("新建合同")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={t("在管合同")} value={num(s.active_count)} unit={t("份")} delay={0}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("共 {n} 份台賬", { n: num(s.contract_count) })}</span>}/>
        <Kpi label={t("在管金額")} value={amtV} unit={t(amtU)} delay={.05}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("生效 · 履約 · 已簽合計")}</span>}/>
        <Kpi label={t("風險信號")} value={riskN} unit={t("個")} red={riskN > 0} delay={.1}
          foot={riskN
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(pExpiry())}>{t("讓秘書梳理 →")}</button>
            : <T tone="ok" dot>{t("全部平穩")}</T>}/>
        <Kpi label={t("鋼印鏈")} value={chTotal} unit={t("道")} red={chBroken > 0} delay={.15}
          foot={chBroken
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(pChainAll())}>{t("交秘書核驗 →")}</button>
            : chTotal
              ? <T tone="ok" dot>{t("鏈條連續")}</T>
              : <span className="muted" style={{ fontSize: 11.5 }}>{t("流程跨步即封印")}</span>}/>
      </div>

      <div className="row g14 wrap rise" style={{ padding: "18px 0 16px", borderBottom: "1px solid var(--hair)", animationDelay: ".05s" }}>
        <div style={{ position: "relative", flex: 1, minWidth: 260 }}>
          <I name="search" size={15} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
          <input ref={searchRef} className="field" style={{ paddingLeft: 26, height: 38 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t("搜索合同 / 編號 / 相對方")}/>
        </div>
        <div className="seg">
          {[["all", "全部"], ["live", "生效履約"], ["pre", "草稿審查"], ["end", "關閉歸檔"]].map(([id, label]) => (
            <button key={id} className={scope === id ? "on" : ""} onClick={() => setScope(id)}>{t(label)}</button>
          ))}
        </div>
      </div>

      <Band no="A" title={t("合同台賬")} sub={t("{n} 份 · 點行看詳情與鋼印鏈", { n: list.length })} delay={.1}>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("合同")}</th><th>{t("相對方")}</th><th>{t("金額")}</th><th>{t("到期")}</th><th>{t("履約節點")}</th><th>{t("狀態")}</th><th style={{ width: 118 }}>{t("交給秘書")}</th>
                </tr></thead>
                <tbody>
                  {list.map((c, idx) => {
                    const stat = CSTAT[c.status] || ["plain", c.status || "—"];
                    const msOpen = num(c.milestone_open), msAll = num(c.milestone_count);
                    return (
                      <tr key={(c.id || c.contract_no || idx) + ":" + idx} className={sel && sel.id === c.id ? "on" : ""} onClick={() => setSel(c)} style={{ cursor: "pointer" }}>
                        <td>
                          <div className="col g4" style={{ minWidth: 0 }}>
                            <span className="row g8" style={{ fontWeight: 650 }}>{c.title || "—"}<T tone="plain">{t(CTYPE[c.contract_type] || "其他")}</T></span>
                            <span className="num muted" style={{ fontSize: 11 }}>{c.contract_no || "—"}</span>
                          </div>
                        </td>
                        <td className="ink2" style={{ fontSize: 13 }}>{c.counterparty_display || c.counterparty_name || "—"}</td>
                        <td><span className="num" style={{ fontWeight: 650 }}>{yuan(c.amount)}</span></td>
                        <td>
                          <div className="col g4">
                            <span className="num" style={{ fontSize: 12 }}>{c.expiry_date || "—"}</span>
                            <DayTag date={c.expiry_date}/>
                          </div>
                        </td>
                        <td>
                          {msAll
                            ? <span className="num"><b style={{ color: msOpen ? "var(--red)" : "var(--ink)" }}>{msOpen}</b><span className="muted"> / {msAll}</span></span>
                            : <span className="muted">—</span>}
                          {msOpen > 0 && <div className="muted num" style={{ fontSize: 10.5, marginTop: 3 }}>{t("待辦 {n}", { n: msOpen })}</div>}
                        </td>
                        <td>
                          <div className="col g4" style={{ alignItems: "flex-start" }}>
                            <T tone={stat[0]} dot>{t(stat[1])}</T>
                            {c.review && c.review.status === "running" && <T tone="warn">{t("審查中")}{c.review.current_node ? " · " + c.review.current_node : ""}</T>}
                          </div>
                        </td>
                        <td onClick={e => e.stopPropagation()}>
                          <div className="row g4">
                            <button className="btn sm" title={t("秘書審查")} style={{ padding: "0 8px" }} onClick={() => ask(c.status === "draft" ? pSubmit(c) : pReview(c))}><I name="sparkle" size={12}/></button>
                            <button className="btn sm" title={t("封存鋼印")} style={{ padding: "0 8px" }} onClick={() => ask(pSealIssue(c))}><I name="shield" size={12}/></button>
                            <button className="btn sm" title={t("跟進爭議")} style={{ padding: "0 8px" }} onClick={() => ask(pDispute(c))}><I name="gavel" size={12}/></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!list.length && (contracts.length
              ? <EM icon="search" title={t("當前篩選下沒有合同")} sub={t("換個篩選或關鍵詞,或直接問秘書「幫我找◯◯合同」。")}/>
              : <EM icon="doc" title={t("暫無合同")} sub={t("對秘書說「新建合同」即可登記第一份;或先讓秘書起草條款框架。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(pNew())}>{t("新建合同")}</B>}/>)}
          </div>
          {sel && <ContractDrawer c={sel} seals={sel.id ? sealMap[sel.id] : []} onClose={() => setSel(null)} onSign={contract => setIdentityAction({ kind: "contract", target: contract })}/>}
        </div>
      </Band>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
        <Band no="B" title={t("鋼印鏈完整性")} sub={<span style={{ paddingRight: 28, display: "inline-block" }}>{t("哈希鏈 + HMAC 簽名")}</span>} delay={.15}>
          <div className="col g14" style={{ paddingRight: 28 }}>
            <div className="row g8" style={{ alignItems: "baseline" }}>
              <span className="num" style={{ fontSize: 46, fontWeight: 700, letterSpacing: "-.04em", color: chColor }}>{chWord}</span>
              <span className="muted" style={{ fontSize: 12 }}>{t("完好 {a} / 共 {b} 道", { a: Math.max(0, chTotal - chBroken), b: chTotal })}</span>
            </div>
            <Meter label={t("完好")} count={Math.max(0, chTotal - chBroken)} total={chTotal} color="var(--ink)"/>
            {chBroken > 0 && <Meter label={t("斷裂環節")} count={chBroken} total={chTotal} color="var(--red)"/>}
            {(Array.isArray(ch.broken) ? ch.broken : []).slice(0, 5).map((b, i) => (
              <div key={b.serial_no || i} className="row spread" style={{ fontSize: 12, borderTop: "1px solid var(--hair-soft)", paddingTop: 8 }}>
                <span className="num" style={{ color: "var(--red)", wordBreak: "break-all" }}>{b.serial_no || "—"}</span>
                <button className="btn sm" onClick={() => ask(pSealOne(b))}>{t("驗真")}</button>
              </div>
            ))}
            <div><B size="sm" icon="scan" onClick={() => ask(pChainAll())}>{t("全鏈核驗")}</B></div>
          </div>
        </Band>
        <Band no="C" title={t("風險與爭議")} sub={t("逾期履約 · 到期合同證照 · 硬閘名單")} delay={.2}
          right={!!risks.length && <B size="sm" icon="sparkle" onClick={() => ask(pRiskAll())}>{t("全部交秘書跟進")}</B>}>
          <div style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
            {!risks.length && <EM icon="checkCircle" title={t("目前沒有風險與爭議事項")} sub={t("合同、證照、履約與名單全部平穩。秘書持續盯防,有風吹草動會第一時間出現在這裡。")}/>}
            {!!risks.length && (
              <div style={{ borderTop: "2px solid var(--rule)" }}>
                {risks.map((r, i) => (
                  <div key={i} className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                      <span className="row g8" style={{ fontWeight: 650, fontSize: 13 }}>
                        <T tone={r.tone} dot>{t(r.kind)}</T>{r.title}
                      </span>
                      <span className="muted" style={{ fontSize: 11.5 }}>{r.sub}</span>
                    </div>
                    <B size="sm" onClick={() => ask(r.prompt)}>{t("交秘書跟進")}</B>
                  </div>
                ))}
              </div>
            )}
          </div>
        </Band>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
        <Band no="D" title={t("證照台賬")} sub={<span style={{ paddingRight: 28, display: "inline-block" }}>{t("{n} 項 · 到期進預警", { n: licenses.length })}</span>} delay={.25}>
          <div style={{ paddingRight: 28 }}>
            {!licenses.length && <div className="muted" style={{ fontSize: 12.5, padding: "12px 0", lineHeight: 1.6 }}>{t("暫無證照。對秘書說「錄入證照」即可登記。")}</div>}
            {licenses.slice(0, 10).map((l, i) => (
              <div key={l.id || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span className="row g8" style={{ fontWeight: 650, fontSize: 13 }}>{l.title || "—"}<T tone="plain">{t(LTYPE[l.license_type] || "其他")}</T></span>
                  <span className="muted num" style={{ fontSize: 11 }}>
                    {l.owner_kind === "self" ? t("本企業") : (l.owner_display || l.owner_name || "—")}
                    {(l.serial_no || l.license_no) ? " · " + (l.serial_no || l.license_no) : ""}
                    {l.expiry_date ? " · " + l.expiry_date : ""}
                  </span>
                </div>
                <DayTag date={l.expiry_date}/>
                {statTag(LSTAT, l.status)}
                <B size="sm" onClick={() => ask(pLicense(l))}>{t("安排續期")}</B>
              </div>
            ))}
          </div>
        </Band>
        <Band no="E" title={t("印章與合規名單")} sub={t("用印走工作流 · 名單提交審查時硬閘")} delay={.3}>
          <div style={{ paddingLeft: 28, borderLeft: "1px solid var(--hair)" }}>
            <LB dim style={{ marginBottom: 6 }}>{t("印章")}</LB>
            {!stamps.length && <div className="muted" style={{ fontSize: 12.5, padding: "8px 0", lineHeight: 1.6 }}>{t("暫無印章。對秘書說「錄入印章」即可登記。")}</div>}
            {stamps.slice(0, 6).map((sl, i) => (
              <div key={sl.id || i} className="ledger-row" style={{ padding: "10px 0" }}>
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span className="row g8" style={{ fontWeight: 650, fontSize: 13 }}>{sl.seal_name || "—"}<T tone="plain">{t(STYPE[sl.seal_type] || "其他")}</T></span>
                  <span className="muted num" style={{ fontSize: 11 }}>{sl.seal_no || "—"} · {t("保管人")} {sl.holder_name || t("未指定")}</span>
                </div>
                <B size="sm" onClick={() => ask(pSealUse(sl))}>{t("發起用印")}</B>
              </div>
            ))}
            <LB dim style={{ margin: "16px 0 6px" }}>{t("待完成用印")}</LB>
            <div className="muted" style={{ fontSize: 10.8, lineHeight: 1.6, marginBottom: 6 }}>{t("審批已完成;上傳實際蓋章後的掃描件，再以本人 Passkey 完成留證。")}</div>
            {!approvedSealUses.length && <div className="muted" style={{ fontSize: 12, padding: "7px 0" }}>{t("暫無已批准、待留證的用印事項")}</div>}
            {approvedSealUses.slice(0, 8).map((approval, i) => (
              <div key={approval.wf_instance_id || i} className="ledger-row" style={{ padding: "10px 0" }}>
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span style={{ fontWeight: 650, fontSize: 13 }}>{approval.seal_name || `#${approval.seal_id}`}</span>
                  <span className="muted" style={{ fontSize: 11 }}>{approval.purpose || approval.title || "—"}{approval.contract_title ? ` · ${approval.contract_title}` : ""}</span>
                  <span className="muted num" style={{ fontSize: 9.5, overflow: "hidden", textOverflow: "ellipsis" }}>{approval.document_sha256}</span>
                </div>
                <B kind="primary" size="sm" icon="user" onClick={() => setIdentityAction({ kind: "seal", target: approval })}>{t("完成用印留證")}</B>
              </div>
            ))}
            <LB dim style={{ margin: "16px 0 6px" }}>{t("合規名單")}</LB>
            {!watchlist.length && <div className="muted" style={{ fontSize: 12.5, padding: "8px 0", lineHeight: 1.6 }}>{t("暫無名單記錄。建合同前會自動核查相對方。")}</div>}
            {watchlist.slice(0, 6).map((w, i) => {
              const [tone, label] = WL[w.list_type] || ["plain", w.list_type || "—"];
              return (
                <div key={w.id || i} className="ledger-row" style={{ padding: "10px 0" }}>
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                    <span className="row g8" style={{ fontWeight: 650, fontSize: 13 }}>{w.party_display || w.party_name || "—"}<T tone={tone} dot>{t(label)}</T></span>
                    <span className="muted" style={{ fontSize: 11.5 }}>{w.reason || "—"}{w.source ? " · " + w.source : ""}</span>
                  </div>
                  <B size="sm" onClick={() => ask(pWatch(w))}>{t("核查")}</B>
                </div>
              );
            })}
          </div>
        </Band>
      </div>
      {identityAction && (
        <LegalIdentityDialog
          action={identityAction}
          onClose={() => setIdentityAction(null)}
          onDone={async () => { setIdentityAction(null); setSel(null); load(); }}/>
      )}
    </>
  );
};

window.W2.PAGES["legal"] = Page;
})();
