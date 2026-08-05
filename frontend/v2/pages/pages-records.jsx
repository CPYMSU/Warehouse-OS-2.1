/* WAREHOUSE 2.1 · 通用檔案管理前端
   保留 cases 內部路由與 allowed_nav 契約，並把原事務頁收納為「事務檔案」。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const LegacyCasePage = window.W2.LEGACY_CASE_PAGE || window.W2.PAGES.cases;
if (!window.W2.LEGACY_CASE_PAGE && LegacyCasePage) window.W2.LEGACY_CASE_PAGE = LegacyCasePage;

window.W2_LANG.addEN({
  "檔案管理": "Records management",
  "企業卷宗 · 分類歸檔 · 版本留痕 · 到期治理": "Enterprise records · classification · versions · retention",
  "總覽": "Overview",
  "全部檔案": "All records",
  "分類庫": "Categories",
  "到期提醒": "Expiry alerts",
  "任務與計劃": "Tasks & plans",
  "建立跟進任務": "Create follow-up task",
  "從此檔案建立跟進任務": "Create a follow-up task from this record",
  "任務工作區未載入": "Task workspace is not loaded",
  "事務檔案": "Case records",
  "通用檔案": "General records",
  "來源": "Source",
  "通用": "General",
  "事務": "Case",
  "已收錄事務檔案": "Existing case records",
  "保留原事務流程與權限，不重複搬移資料。": "The original case workflow and permissions are preserved without duplicating data.",
  "查看事務檔案": "View case records",
  "類型設定": "Type settings",
  "檔案總數": "Total records",
  "有效檔案": "Active records",
  "即將到期": "Expiring soon",
  "受限檔案": "Restricted records",
  "新建檔案": "New record",
  "交給 AI 秘書": "Ask AI Secretary",
  "份檔案": "records",
  "個類型": "types",
  "個分類": "categories",
  "我要建立一份檔案": "I want to create a record",
  "需要 AI 秘書權限": "AI Secretary access required",
  "搜尋編號、標題、對象或內容": "Search number, title, subject or content",
  "全部分類": "All categories",
  "全部狀態": "All statuses",
  "全部密級": "All classifications",
  "刷新": "Refresh",
  "載入中…": "Loading…",
  "檔案管理 API 尚未啟用或暫時無法連線。": "The records API is not available yet.",
  "現有事務仍可在「事務檔案」頁籤使用。": "Existing cases remain available under Case records.",
  "重試": "Retry",
  "尚無檔案": "No records yet",
  "目前篩選條件下沒有檔案記錄。": "No records match the current filters.",
  "尚無分類": "No categories yet",
  "後端啟用分類預設後會顯示於此。": "Categories will appear here when presets are enabled.",
  "類型": "Type",
  "分類": "Category",
  "標題": "Title",
  "摘要": "Summary",
  "狀態": "Status",
  "密級": "Classification",
  "歸屬部門": "Owning department",
  "檔案對象": "Record subject",
  "生效日期": "Effective date",
  "到期日期": "Expiry date",
  "更新": "Updated",
  "建立檔案": "Create",
  "建立中…": "Creating…",
  "結構欄位": "Structured fields",
  "關聯": "Relations",
  "文件版本": "Document versions",
  "新增文件": "Add document",
  "上傳新版": "Upload new version",
  "選擇文件": "Choose files",
  "上傳中…": "Uploading…",
  "上傳進度": "Upload progress",
  "文件上傳失敗": "Document upload failed",
  "文件下載失敗": "Document download failed",
  "文件標題": "Document title",
  "文件欄位": "Document field",
  "可見範圍": "Visibility",
  "檔案可見者": "Record viewers",
  "參與者": "Participants",
  "管理者": "Managers",
  "建立人／負責人／保管人": "Creator / owner / custodian",
  "目前版本": "Current",
  "下載": "Download",
  "請先選擇文件": "Choose at least one file",
  "沒有上傳文件的權限": "Document upload is not permitted",
  "請先建立檔案，再於詳情的文件版本區加入文件。": "Create the record first, then add documents under Document versions.",
  "時間線": "Timeline",
  "可用動作": "Available actions",
  "操作說明": "Action note",
  "執行": "Run",
  "尚無關聯": "No relations",
  "尚無文件版本": "No document versions",
  "尚無時間線": "No timeline",
  "原事務頁未載入": "Legacy case page is not loaded",
  "請確認 pages-cases.jsx 先於本頁載入。": "Load pages-cases.jsx before this page.",
  "類型配置由行業預設及公司設定提供。": "Types are supplied by industry presets and company settings.",
  "欄位": "fields",
  "版本": "Revision",
  "API 上線後可在此管理檔案類型、欄位及治理規則。": "Type, field and governance editing will be available when its API is enabled.",
  "分類設定": "Category settings",
  "新增分類": "New category",
  "新增類型": "New type",
  "修訂": "Revise",
  "停用": "Disable",
  "公司自管": "Company managed",
  "行業模板": "Industry template",
  "修訂後轉為公司自管": "Revising this template item makes it company managed",
  "配置代碼": "Configuration key",
  "建立後不可修改": "Cannot be changed after creation",
  "名稱": "Name",
  "說明": "Description",
  "圖示": "Icon",
  "排序": "Order",
  "責任部門代碼": "Owner unit code",
  "生命週期": "Lifecycle",
  "保管規則 JSON": "Retention JSON",
  "高級配置 JSON": "Advanced config JSON",
  "高級配置只可包含欄位、狀態、流轉、提醒與保管規則。": "Advanced config may contain only fields, statuses, transitions, reminders and retention rules.",
  "預覽變更": "Preview changes",
  "完整提交預覽": "Full submission preview",
  "返回修改": "Back to edit",
  "確認提交": "Confirm and submit",
  "確認停用": "Confirm disable",
  "配置 JSON 必須是物件": "Configuration JSON must be an object",
  "配置 JSON 格式不正確": "Configuration JSON is invalid",
  "請填寫配置代碼與名稱": "Enter a configuration key and name",
  "請選擇分類": "Choose a category",
  "配置已更新": "Configuration updated",
  "只有具備 records.config.manage 權限者可修改分類與類型。": "Only users with records.config.manage may change categories and types.",
  "現有檔案繼續使用原版本；新版本只套用於後續建檔。": "Existing records keep their original revision; the new revision applies only to future records.",
  "人員檔案": "Personnel records",
  "會議檔案": "Meeting records",
  "培訓檔案": "Training records",
  "安全檔案": "Safety records",
  "其他檔案": "Other records",
  "包含封存": "Include archived",
  "載入更多": "Load more",
  "已載入": "Loaded",
  "案件與卷宗": "Cases & records",
  "案件主卷 · 法律文書 · 版本留痕 · 期限與歸檔": "Case files · legal documents · version history · deadlines & filing",
  "案件總覽": "Case overview",
  "卷宗庫": "Record library",
  "文書類型": "Document types",
  "期限管理": "Deadline management",
  "程序計畫": "Procedure plans",
  "進行中案件": "Active cases",
  "流程模板": "Workflow templates",
  "新建卷宗／文書": "New record / document",
  "建立卷宗／文書": "Create record / document",
  "卷宗總數": "Total case files",
  "卷宗與文書": "Records & documents",
  "已收錄進行中案件": "Active cases included",
  "保留案件階段、權限與留痕，不重複搬移資料。": "Case stages, permissions, and history remain in place without duplicating data.",
  "查看進行中案件": "View active cases",
  "案件程序狀態": "Case procedure status",
  "案件對象": "Case subject",
  "案件": "Case",
  "卷宗": "Record",
  "草擬中": "Drafting",
  "待程序覆核": "Awaiting procedural review",
  "進行中": "In progress",
  "已結案歸檔": "Closed and filed",
  "已逾程序期限": "Procedure deadline passed",
  "暫停歸檔": "Filing paused",
  "已結案": "Closed",
  "已提交審查": "Submitted for review",
  "已完成分流": "Triage complete",
  "已分派承辦": "Assigned",
  "程序進行中": "Procedure in progress",
  "等待當事人材料": "Awaiting party materials",
  "程序已完成": "Procedure complete",
  "已排入程序": "Procedure scheduled",
  "已完成程序": "Procedure completed",
  "已撤回": "Withdrawn",
  "審查中": "Under review",
  "重啟程序": "Reopen procedure",
  "程序留言": "Procedure note",
  "案件收集": "Case intake",
  "倫理與範圍審核": "Ethics & scope review",
  "已建立程序卷宗": "Procedure record opened",
  "書狀階段": "Pleadings",
  "證據審查": "Evidence review",
  "庭前整理": "Pre-hearing preparation",
  "庭審階段": "Hearing",
  "評議階段": "Deliberation",
  "已登記裁決": "Decision recorded",
  "上訴期限": "Appeal window",
  "上訴審查": "Appellate review",
  "最終審查": "Final review",
  "卷宗完整性核查": "Record completeness review",
  "待結案歸檔": "Ready to close and file",
  "不予收錄": "Intake rejected",
  "開始倫理審核": "Start ethics review",
  "建立程序卷宗": "Open procedure record",
  "開始書狀階段": "Start pleadings",
  "開始證據審查": "Start evidence review",
  "開始庭前整理": "Start pre-hearing preparation",
  "開始庭審": "Start hearing",
  "開始評議": "Start deliberation",
  "登記裁決": "Record decision",
  "開始上訴期限": "Open appeal window",
  "開始上訴審查": "Start appellate review",
  "送交最終審查": "Send to final review",
  "完成上訴審查": "Complete appellate review",
  "完成最終審查": "Complete final review",
  "確認卷宗完整": "Confirm record completeness",
  "退回補充": "Return for completion",
  "我要建立一份案件卷宗／文書": "I want to create a case record / document",
});

const { useState: S, useEffect: E, useRef: R } = React;
const { Icon: I, Btn: B, Tag: T, Label: L, Empty, Kpi, Folio, Band } = W2;

const DEFAULT_CATEGORIES = [
  { key: "personnel", name: "人員檔案", description: "任職、資格、考核與人員相關卷宗", icon: "user" },
  { key: "meeting", name: "會議檔案", description: "議程、紀要、決議與跟進材料", icon: "clipboard" },
  { key: "training", name: "培訓檔案", description: "計畫、簽到、考核與證明材料", icon: "doc" },
  { key: "safety", name: "安全檔案", description: "檢查、隱患、事件與整改記錄", icon: "shield" },
  { key: "case", name: "事務檔案", description: "由原事務管理形成的處置卷宗", icon: "layers" },
  { key: "other", name: "其他檔案", description: "公司自訂及尚未歸類的檔案", icon: "box" },
];

const STATUS_LABELS = {
  draft: "草稿", active: "有效", current: "有效", pending_review: "待覆核",
  archived: "已歸檔", expired: "已到期", superseded: "已被取代",
  legal_hold: "保留中", destroyed: "已銷毀", closed: "已結束",
  submitted: "已提交", triaged: "已分流", assigned: "已指派",
  in_progress: "處理中", waiting_external: "等待外部", resolved: "已完成",
  inactive: "已停用", planned: "已計畫", completed: "已完成", cancelled: "已取消",
  in_review: "覆核中", effective: "已生效", open: "待處理",
};
const BIU_STATUS_LABELS = Object.freeze({
  draft: "草擬中", active: "進行中", current: "進行中", pending_review: "待程序覆核",
  archived: "已結案歸檔", expired: "已逾程序期限", legal_hold: "暫停歸檔", closed: "已結案",
  submitted: "已提交審查", triaged: "已完成分流", assigned: "已分派承辦",
  in_progress: "程序進行中", waiting_external: "等待當事人材料", resolved: "程序已完成",
  planned: "已排入程序", completed: "已完成程序", cancelled: "已撤回",
  in_review: "審查中", effective: "已生效", open: "待處理", inactive: "已停用",
  superseded: "已被取代", destroyed: "已銷毀",
  intake: "案件收集", ethics_review: "倫理與範圍審核", docketed: "已建立程序卷宗",
  pleadings: "書狀階段", evidence_review: "證據審查", pre_hearing: "庭前整理",
  hearing: "庭審階段", deliberation: "評議階段", decision_issued: "已登記裁決",
  appeal_window: "上訴期限", appellate_review: "上訴審查", final_review: "最終審查",
  completeness_review: "卷宗完整性核查", ready_to_archive: "待結案歸檔", intake_rejected: "不予收錄",
});
const CONF_LABELS = {
  public: "公開", internal: "內部", sensitive: "敏感", restricted: "受限",
  confidential: "機密", secret: "秘密",
};
const CONF_RANK = { public: -1, internal: 0, sensitive: 1, restricted: 2, confidential: 2, secret: 2 };
const VISIBILITY_LABELS = {
  record: "檔案可見者", participants: "參與者", managers: "管理者", private: "建立人／負責人／保管人",
};
const ACTION_LABELS = {
  submit: "提交", activate: "生效", review: "覆核", archive: "歸檔",
  renew: "續期", supersede: "取代", hold: "法律保留", release_hold: "解除保留",
  destroy: "銷毀", close: "結束", reopen: "重開", comment: "留言",
  restore: "恢復", set_status: "變更狀態", created: "建立", updated: "更新", version_added: "新增版本",
};
const BIU_ACTION_LABELS = Object.freeze({
  ...ACTION_LABELS,
  activate: "進入程序", review: "程序覆核", archive: "結案歸檔", renew: "延長期限",
  hold: "暫停歸檔", release_hold: "恢復歸檔", close: "結案", reopen: "重啟程序",
  comment: "程序留言", set_status: "更新程序狀態",
  start_ethics_review: "開始倫理審核", accept_docket: "建立程序卷宗", reject_intake: "不予收錄",
  open_pleadings: "開始書狀階段", start_evidence_review: "開始證據審查",
  start_pre_hearing: "開始庭前整理", open_hearing: "開始庭審", start_deliberation: "開始評議",
  issue_decision: "登記裁決", open_appeal_window: "開始上訴期限",
  open_appellate_review: "開始上訴審查", send_final_review: "送交最終審查",
  finish_appellate_review: "完成上訴審查", complete_final_review: "完成最終審查",
  complete_completeness_review: "確認卷宗完整", return_for_completion: "退回補充",
});
const BIU_COPY = Object.freeze({
  "檔案管理": "案件與卷宗",
  "企業卷宗 · 分類歸檔 · 版本留痕 · 到期治理": "案件主卷 · 法律文書 · 版本留痕 · 期限與歸檔",
  "總覽": "案件總覽", "全部檔案": "卷宗庫", "分類庫": "文書類型",
  "到期提醒": "期限管理", "任務與計劃": "程序計畫", "事務檔案": "進行中案件",
  "類型設定": "流程模板", "新建檔案": "新建卷宗／文書", "建立檔案": "建立卷宗／文書",
  "檔案總數": "卷宗總數", "通用檔案": "卷宗與文書",
  "已收錄事務檔案": "已收錄進行中案件",
  "保留原事務流程與權限，不重複搬移資料。": "保留案件階段、權限與留痕，不重複搬移資料。",
  "查看事務檔案": "查看進行中案件", "事務": "案件", "通用": "卷宗",
  "狀態": "案件程序狀態", "檔案對象": "案件對象",
  "執行": "提交",
});
const recordText = (biu, key) => t(biu ? (BIU_COPY[key] || key) : key);
const recordStatusLabel = (biu, value) => t((biu ? BIU_STATUS_LABELS : STATUS_LABELS)[keyOf(value)] || keyOf(value) || "—");
const recordActionLabel = (biu, value) => t((biu ? BIU_ACTION_LABELS : ACTION_LABELS)[keyOf(value)] || keyOf(value) || "—");
const confidentialityRank = value => Object.prototype.hasOwnProperty.call(CONF_RANK, keyOf(value))
  ? CONF_RANK[keyOf(value)] : CONF_RANK.internal;
const minimumConfidentialityOf = type => keyOf(first(type && type.minimum_confidentiality, type && type.confidentiality, "internal"));
const defaultConfidentialityOf = type => {
  const minimum = minimumConfidentialityOf(type);
  const preferred = keyOf(first(type && type.default_confidentiality, minimum));
  return confidentialityRank(preferred) >= confidentialityRank(minimum) ? preferred : minimum;
};

const grid = (min = 230) => ({
  display: "grid",
  gridTemplateColumns: `repeat(auto-fill,minmax(${min}px,1fr))`,
  gap: 12,
});
const card = {
  background: "var(--white)", border: "1px solid var(--hair)", padding: 14,
  textAlign: "left", minWidth: 0,
};
const sectionRule = { borderTop: "2px solid var(--rule)", paddingTop: 10 };

const arr = value => Array.isArray(value) ? value : [];
const object = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
const keyOf = value => String(value == null ? "" : value);
const first = (...values) => values.find(value => value !== undefined && value !== null && value !== "");
const safeNum = value => Number.isFinite(Number(value)) ? Number(value) : 0;
const recordFrom = data => object(data).record || object(data).item || object(data).result || data;
const recordsFrom = data => arr(object(data).records).length ? object(data).records
  : arr(object(data).items).length ? object(data).items
  : arr(object(data).results);
const typeKeyOf = value => keyOf(first(value && value.key, value && value.type_key, value && value.type_key_snapshot, value && value.code, value && value.id));
const categoryKeyOf = value => keyOf(first(value && value.key, value && value.category_key, value && value.code, value && value.id));
const recordId = value => first(value && value.id, value && value.record_id, value && value.uuid);
const isLegacyRecord = value => keyOf(value && value.source) === "legacy_case";
const legacyCaseIdOf = value => {
  const direct = first(value && value.legacy_case_id, value && value.case_id);
  if (direct != null && direct !== "") return direct;
  const id = keyOf(recordId(value));
  return id.startsWith("case:") ? id.slice(5) : null;
};
const recordNo = value => first(value && value.record_no, value && value.archive_no, value && value.file_no, value && value.case_no, recordId(value), "—");
const recordTitle = value => first(value && value.title, value && value.name, value && value.subject, "未命名檔案");
const statusOf = value => keyOf(first(value && value.status, value && value.lifecycle_status, "draft"));
const confOf = value => keyOf(first(value && value.confidentiality, value && value.classification, value && value.security_level, "internal"));
const labelOf = (map, value) => t(map[keyOf(value)] || keyOf(value) || "—");
const textValue = value => {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "✓" : "—";
  if (Array.isArray(value)) return value.map(textValue).join("、");
  if (typeof value === "object") {
    return first(value.label, value.name, value.title, value.display_name, value.value, JSON.stringify(value));
  }
  return String(value);
};
const dateValue = value => {
  if (!value) return "—";
  let raw = String(value).trim().replace(" ", "T");
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw) && raw.includes("T")) raw += "Z";
  const date = new Date(raw);
  if (Number.isNaN(date.getTime())) return String(value);
  const pad = number => String(number).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
};
const shortDate = value => {
  const rendered = dateValue(value);
  return rendered === "—" ? rendered : rendered.slice(0, 10);
};
const localDateTimeToUtc = value => {
  if (!value) return value;
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? value : date.toISOString();
};
const newIdempotencyKey = () => "records-web-" + (window.crypto && window.crypto.randomUUID
  ? window.crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const newRecordCreateRequestId = () => "record-create-" + (window.crypto && window.crypto.randomUUID
  ? window.crypto.randomUUID()
  : `${Date.now()}-${Math.random().toString(36).slice(2)}`);
const createTypeContext = type => ({
  key: typeKeyOf(type),
  name: first(type && type.name, type && type.label, typeKeyOf(type)),
  category: keyOf(first(type && type.category_key, type && type.category)),
  lifecycle: keyOf(first(type && type.lifecycle_mode, type && type.lifecycle, "dossier")),
  minimum_confidentiality: minimumConfidentialityOf(type),
  required_fields: arr(first(type && type.fields, type && type.form_fields, type && type.schema && type.schema.fields, []))
    .filter(field => field && field.required && !["file", "document"].includes(keyOf(first(field.type, field.kind))))
    .map(field => {
      const options = optionItems(field.options);
      return {
        key: keyOf(field.key), label: first(field.label, field.name, field.key),
        type: keyOf(first(field.type, field.kind, "text")),
        ...(options.length ? { options: options.map(option => ({ value: option.value, label: option.label })) } : {}),
      };
    }),
  required_documents: arr(first(type && type.fields, type && type.form_fields, type && type.schema && type.schema.fields, []))
    .filter(field => field && field.required && ["file", "document"].includes(keyOf(first(field.type, field.kind))))
    .map(field => ({ key: keyOf(field.key), label: first(field.label, field.name, field.key) })),
});
const sizeValue = value => {
  const bytes = safeNum(value);
  if (!bytes) return "—";
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  if (bytes >= 1024) return Math.round(bytes / 1024) + " KB";
  return bytes + " B";
};
const safeFileName = (value, fallback = "document") => {
  let name = String(value || "").split(/[\\/]/).pop()
    .replace(/[\u0000-\u001f\u007f\u200e\u200f\u202a-\u202e\u2066-\u2069]/g, "").trim();
  name = name.replace(/[<>:"|?*]/g, "_").slice(0, 180);
  if (/^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(name)) name = "_" + name;
  return !name || name === "." || name === ".." ? fallback : name;
};
const contentDispositionName = (header, fallback) => {
  const value = String(header || "");
  const encoded = value.match(/filename\*\s*=\s*([^;]+)/i);
  if (encoded) {
    let candidate = encoded[1].trim().replace(/^['"]|['"]$/g, "");
    candidate = candidate.replace(/^UTF-8'[^']*'/i, "");
    try { candidate = decodeURIComponent(candidate); } catch (error) {}
    return safeFileName(candidate, fallback);
  }
  const plain = value.match(/filename\s*=\s*(?:"([^"]*)"|([^;]+))/i);
  return safeFileName(plain ? first(plain[1], plain[2]) : fallback, fallback);
};
const responseError = async (response, fallback) => {
  const data = await response.clone().json().catch(() => ({}));
  throw new Error(data.error || data.message || fallback || response.statusText);
};
const downloadDocumentVersion = async (record, version) => {
  const id = recordId(record);
  const versionId = first(version && version.id, version && version.version_id);
  if (id == null || versionId == null) throw new Error(t("文件下載失敗"));
  const response = await W2.fetch(`/api/records/${encodeURIComponent(id)}/documents/${encodeURIComponent(versionId)}`);
  if (!response.ok) return responseError(response, t("文件下載失敗"));
  const blob = await response.blob();
  const fallback = safeFileName(first(version.file_name, version.filename, `${recordNo(record)}-document`));
  const filename = contentDispositionName(response.headers.get("Content-Disposition"), fallback);
  const url = URL.createObjectURL(blob);
  try {
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = filename;
    document.body.appendChild(anchor); anchor.click(); anchor.remove();
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
};
const statusTone = value => ["active", "current", "archived", "resolved"].includes(keyOf(value)) ? "ok"
  : ["expired", "destroyed"].includes(keyOf(value)) ? "bad"
  : ["pending_review", "legal_hold", "in_progress"].includes(keyOf(value)) ? "warn" : "plain";
const confTone = value => ["restricted", "confidential", "secret"].includes(keyOf(value)) ? "bad"
  : keyOf(value) === "sensitive" ? "warn" : "plain";

const optionItems = values => arr(values).map(value => typeof value === "object"
  ? { value: keyOf(first(value.value, value.key, value.code, value.id)), label: first(value.label, value.name, value.title, value.value, value.key) }
  : { value: keyOf(value), label: keyOf(value) });
const statusesOf = meta => {
  const values = optionItems(first(meta && meta.statuses, meta && meta.record_statuses, []));
  return values.length ? values : optionItems(["draft", "active", "pending_review", "archived", "expired", "legal_hold"]);
};
const confidentialitiesOf = meta => {
  const values = optionItems(first(meta && meta.confidentialities, meta && meta.classifications, meta && meta.security_levels, []));
  return values.length ? values : optionItems(["internal", "sensitive", "restricted"]);
};
const typesOf = meta => arr(first(meta && meta.types, meta && meta.record_types, meta && meta.type_definitions, []));
const categoriesOf = meta => {
  const supplied = arr(first(meta && meta.categories, meta && meta.record_categories, meta && meta.classifications_catalogue, []));
  if (supplied.length) return supplied;
  const derived = [];
  const seen = new Set();
  typesOf(meta).forEach(type => {
    const key = keyOf(first(type.category_key, type.category));
    if (!key || seen.has(key)) return;
    seen.add(key);
    derived.push({ key, name: first(type.category_name, type.category_label, key) });
  });
  return derived.length ? derived : (meta == null ? DEFAULT_CATEGORIES : []);
};
const categoryName = (meta, key) => {
  const match = categoriesOf(meta).find(value => categoryKeyOf(value) === keyOf(key));
  return first(match && match.name, match && match.label, match && match.title, key, "—");
};
const typeName = (meta, record) => {
  if (first(record && record.type_name, record && record.type_name_snapshot)) return first(record.type_name, record.type_name_snapshot);
  const key = keyOf(first(record && record.type_key, record && record.type_key_snapshot, record && record.record_type_key, record && record.type_id));
  const match = typesOf(meta).find(value => typeKeyOf(value) === key);
  return first(match && match.name, match && match.label, key, "—");
};
const categoryOfRecord = record => keyOf(first(record && record.category_key, record && record.category_key_snapshot, record && record.category, record && record.record_category_key));
const expiresOf = record => first(record && record.expires_at, record && record.effective_until, record && record.expiry_date, record && record.retention_due_at, record && record.due_at);
const updatedOf = record => first(record && record.updated_at, record && record.modified_at, record && record.created_at);

const Loading = ({ label = "載入中…" }) => (
  <div className="muted" style={{ padding: 44, textAlign: "center", letterSpacing: ".08em" }}>{t(label)}</div>
);

const ApiError = ({ message, onRetry }) => (
  <div style={{ ...card, borderTop: "3px solid var(--red)", marginBottom: 14 }}>
    <div className="row g10" style={{ alignItems: "flex-start" }}>
      <I name="alert" size={18} color="var(--red)"/>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 13.5, fontWeight: 720 }}>{t("檔案管理 API 尚未啟用或暫時無法連線。")}</div>
        <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55, marginTop: 5 }}>
          {message || t("現有事務仍可在「事務檔案」頁籤使用。")}
        </div>
      </div>
      {onRetry && <B size="sm" icon="refresh" onClick={onRetry}>{t("重試")}</B>}
    </div>
  </div>
);

const CategoryCards = ({ meta, summary, selected, onSelect, compact = false }) => {
  const byCategory = object(first(summary && summary.by_category, summary && summary.categories, {}));
  const categories = categoriesOf(meta);
  if (!categories.length) return <Empty icon="layers" title={t("尚無分類")} sub={t("後端啟用分類預設後會顯示於此。")} />;
  return <div style={grid(compact ? 190 : 230)}>{categories.map((category, index) => {
    const key = categoryKeyOf(category);
    const count = first(category.count, category.record_count, byCategory[key], 0);
    const suppliedTypes = arr(category && category.types);
    const typeCount = (suppliedTypes.length ? suppliedTypes : typesOf(meta).filter(type => (
      keyOf(first(type && type.category_key, type && type.category)) === key
    ))).filter(type => type && type.active !== false).length;
    const active = selected && keyOf(selected) === key;
    return <button type="button" key={key || index} onClick={() => onSelect && onSelect(key)} style={{
      ...card, cursor: onSelect ? "pointer" : "default", minHeight: compact ? 112 : 132,
      borderTop: `3px solid ${active ? "var(--red)" : "var(--rule)"}`,
      background: active ? "var(--paper-2)" : "var(--white)",
    }}>
      <div className="row spread g8">
        <span style={{ width: 30, height: 30, border: "1px solid var(--hair)", display: "grid", placeItems: "center" }}>
          <I name={category.icon || "doc"} size={15}/>
        </span>
        <span className="num" style={{ fontSize: 13, fontWeight: 760 }}>{safeNum(count)} <small className="muted">{t("份檔案")}</small></span>
      </div>
      <div style={{ fontSize: 14, fontWeight: 720, marginTop: 10 }}>{t(first(category.name, category.label, category.title, key, "未命名分類"))}</div>
      {!compact && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.5, marginTop: 5 }}>{t(first(category.description, category.help, ""))}</div>}
      <div className="muted" style={{ fontSize: 10.5, marginTop: 7 }}>{typeCount} {t("個類型")}</div>
    </button>;
  })}</div>;
};

const RecordTable = ({ rows, meta, loading, onOpen, biu = false }) => {
  if (loading && !rows.length) return <Loading/>;
  if (!rows.length) return <Empty icon="doc" title={t("尚無檔案")} sub={t("目前篩選條件下沒有檔案記錄。")} />;
  return <div style={{ overflowX: "auto", borderTop: "2px solid var(--rule)", opacity: loading ? .62 : 1 }}>
    <table className="tbl2">
      <thead><tr>
        <th>{t("來源")}</th><th>{t("編號")}</th><th>{t("標題")}</th><th>{t("分類")}</th><th>{t("類型")}</th>
        <th>{recordText(biu, "狀態")}</th><th>{t("密級")}</th><th>{recordText(biu, "檔案對象")}</th><th>{t("到期日期")}</th><th>{t("更新")}</th>
      </tr></thead>
      <tbody>{rows.map((record, index) => <tr key={recordId(record) || index} onClick={() => onOpen(record)} style={{ cursor: recordId(record) != null ? "pointer" : "default" }}>
        <td><T tone={isLegacyRecord(record) ? "warn" : "plain"}>{recordText(biu, isLegacyRecord(record) ? "事務" : "通用")}</T></td>
        <td className="num" style={{ fontSize: 10.5 }}>{recordNo(record)}</td>
        <td style={{ fontWeight: 680, maxWidth: 250 }}>{recordTitle(record)}</td>
        <td>{t(first(record.category_name_snapshot, record.category_name, categoryName(meta, categoryOfRecord(record))))}</td>
        <td>{t(typeName(meta, record))}</td>
        <td><T tone={statusTone(statusOf(record))} dot>{recordStatusLabel(biu, statusOf(record))}</T></td>
        <td><T tone={confTone(confOf(record))}>{labelOf(CONF_LABELS, confOf(record))}</T></td>
        <td>{first(record.subject_name, record.subject, record.owner_user_name, record.owner_name, record.person_name, "—")}</td>
        <td className="num" style={{ fontSize: 10.5 }}>{shortDate(expiresOf(record))}</td>
        <td className="num muted" style={{ fontSize: 10 }}>{dateValue(updatedOf(record))}</td>
      </tr>)}</tbody>
    </table>
  </div>;
};

const FieldInput = ({ field, value, onChange }) => {
  const kind = keyOf(first(field.type, field.kind, "text"));
  const label = first(field.label, field.name, field.key, "欄位");
  const options = optionItems(field.options);
  if (kind === "file" || kind === "document") return <div>
    <L dim>{t(label)}</L>
    <div style={{ border: "1px dashed var(--hair)", padding: 10, marginTop: 5, fontSize: 11.5 }} className="muted">
      {t("請先建立檔案，再於詳情的文件版本區加入文件。")}
    </div>
  </div>;
  if (kind === "boolean") return <label className="row g8" style={{ minHeight: 40, cursor: "pointer" }}>
    <input type="checkbox" checked={!!value} onChange={event => onChange(event.target.checked)}/>
    <span>{t(label)}</span>{field.required && <span style={{ color: "var(--red)" }}>*</span>}
  </label>;
  if (kind === "enum" || kind === "select" || kind === "multienum" || kind === "multiselect") return <div>
    <L dim>{t(label)}{field.required ? " *" : ""}</L>
    <select className="field boxed" multiple={kind.startsWith("multi")}
      value={kind.startsWith("multi") ? arr(value) : keyOf(value)}
      onChange={event => onChange(kind.startsWith("multi")
        ? Array.from(event.target.selectedOptions).map(option => option.value)
        : event.target.value)}>
      {!kind.startsWith("multi") && <option value="">—</option>}
      {options.map(option => <option key={option.value} value={option.value}>{t(option.label)}</option>)}
    </select>
  </div>;
  if (kind === "textarea" || kind === "richtext") return <div>
    <L dim>{t(label)}{field.required ? " *" : ""}</L>
    <textarea className="field boxed" style={{ height: 84, paddingTop: 9, resize: "vertical" }} value={value || ""}
      onChange={event => onChange(event.target.value)} placeholder={field.help || field.placeholder || ""}/>
  </div>;
  const inputType = kind === "number" ? "number" : kind === "date" ? "date" : kind === "datetime" ? "datetime-local" : "text";
  return <div>
    <L dim>{t(label)}{field.required ? " *" : ""}</L>
    <input className="field boxed" type={inputType} value={value == null ? "" : value}
      onChange={event => onChange(kind === "number" && event.target.value !== "" ? Number(event.target.value) : event.target.value)}
      placeholder={field.help || field.placeholder || ""}/>
  </div>;
};

const CreateDrawer = ({ meta, initialTypeKey = "", initialCategoryKey = "", onClose, onDone, biu = false }) => {
  const types = typesOf(meta).filter(type => type.active !== false && type.can_create !== false);
  const preferredType = types.find(type => typeKeyOf(type) === keyOf(initialTypeKey))
    || types.find(type => keyOf(first(type && type.category_key, type && type.category)) === keyOf(initialCategoryKey))
    || (!initialTypeKey && !initialCategoryKey ? types[0] : null);
  const [typeId, setTypeId] = S(preferredType ? typeKeyOf(preferredType) : "");
  const selectedType = types.find(type => typeKeyOf(type) === typeId) || null;
  const categoryDefault = keyOf(first(selectedType && selectedType.category_key, selectedType && selectedType.category));
  const initialStatus = keyOf(first(selectedType && selectedType.initial_status, "draft"));
  const minimumConfidentiality = minimumConfidentialityOf(selectedType);
  const availableConfidentialities = confidentialitiesOf(meta)
    .filter(item => confidentialityRank(item.value) >= confidentialityRank(minimumConfidentiality));
  const [title, setTitle] = S("");
  const [description, setDescription] = S("");
  const [confidentiality, setConfidentiality] = S(defaultConfidentialityOf(selectedType));
  const [effectiveAt, setEffectiveAt] = S("");
  const [expiresAt, setExpiresAt] = S("");
  const [fields, setFields] = S({});
  const [busy, setBusy] = S(false);
  const [error, setError] = S("");
  const idempotencyKey = R("");
  if (!idempotencyKey.current) idempotencyKey.current = newIdempotencyKey();
  const definitions = arr(first(selectedType && selectedType.fields, selectedType && selectedType.form_fields, selectedType && selectedType.schema && selectedType.schema.fields, []));
  const chooseType = value => {
    const type = types.find(item => typeKeyOf(item) === value);
    setTypeId(value);
    setConfidentiality(defaultConfidentialityOf(type));
    setFields({}); setError("");
  };
  const submit = async () => {
    if (!selectedType || !title.trim()) { setError(!selectedType ? "請選擇檔案類型" : "請填寫標題"); return; }
    const missing = definitions.find(field => field.required && !["file", "document"].includes(keyOf(field.type))
      && (fields[field.key] == null || fields[field.key] === "" || (Array.isArray(fields[field.key]) && !fields[field.key].length)));
    if (missing) { setError(`請填寫${first(missing.label, missing.name, missing.key)}`); return; }
    setBusy(true); setError("");
    try {
      const dynamic = {};
      definitions.forEach(field => {
        if (["file", "document"].includes(keyOf(field.type))) return;
        const value = fields[field.key];
        if (value !== undefined && value !== "") {
          dynamic[field.key] = keyOf(first(field.type, field.kind)) === "datetime" ? localDateTimeToUtc(value) : value;
        }
      });
      const typeNumericId = Number(selectedType.id);
      const data = await W2.post("/api/records", {
        type_id: Number.isFinite(typeNumericId) && typeNumericId > 0 ? typeNumericId : undefined,
        type_key: first(selectedType.key, selectedType.type_key, selectedType.code),
        category_key: categoryDefault || undefined,
        title: title.trim(), description: description.trim(), status: initialStatus,
        confidentiality, effective_at: effectiveAt || undefined, expires_at: expiresAt || undefined,
        fields: dynamic,
        idempotency_key: idempotencyKey.current,
      });
      const created = recordFrom(data);
      if (!created || typeof created !== "object") throw new Error("建立接口未返回檔案資料");
      onDone(created);
    } catch (exception) { setError(exception.message || "建立失敗"); }
    finally { setBusy(false); }
  };
  return <div className="drawer">
    <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
      <div className="row spread"><div><L red>NEW RECORD</L><div style={{ fontSize: 19, fontWeight: 760, marginTop: 5 }}>{recordText(biu, "新建檔案")}</div></div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div>
    </div>
    <div className="col g14" style={{ padding: 18, maxHeight: "calc(100vh - 205px)", overflowY: "auto" }}>
      <div><L dim>{t("類型")}</L><select className="field boxed" value={typeId} onChange={event => chooseType(event.target.value)}><option value="">—</option>{types.map(type => <option key={typeKeyOf(type)} value={typeKeyOf(type)}>{t(first(type.name, type.label, type.key))}</option>)}</select></div>
      {selectedType && selectedType.description && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>{t(selectedType.description)}</div>}
      <div><L dim>{t("標題")} *</L><input className="field boxed" maxLength="240" value={title} onChange={event => setTitle(event.target.value)}/></div>
      <div><L dim>{t("摘要")}</L><textarea className="field boxed" style={{ height: 88, paddingTop: 9 }} value={description} onChange={event => setDescription(event.target.value)}/></div>
      <div style={grid(150)}>
        <div><L dim>{t("分類")}</L><input className="field boxed" disabled value={t(categoryName(meta, categoryDefault))}/></div>
        <div><L dim>{recordText(biu, "狀態")}</L><input className="field boxed" disabled value={recordStatusLabel(biu, initialStatus)}/></div>
        <div><L dim>{t("密級")}</L><select className="field boxed" value={confidentiality} onChange={event => setConfidentiality(event.target.value)}>{availableConfidentialities.map(item => <option key={item.value} value={item.value}>{labelOf(CONF_LABELS, item.label || item.value)}</option>)}</select></div>
      </div>
      <div style={grid(180)}>
        <div><L dim>{t("生效日期")}</L><input className="field boxed" type="date" value={effectiveAt} onChange={event => setEffectiveAt(event.target.value)}/></div>
        <div><L dim>{t("到期日期")}</L><input className="field boxed" type="date" value={expiresAt} onChange={event => setExpiresAt(event.target.value)}/></div>
      </div>
      {!!definitions.length && <><div style={sectionRule}><L red>{t("結構欄位")}</L></div>{definitions.map((field, index) => <FieldInput key={field.key || index} field={field} value={fields[field.key]} onChange={value => setFields(old => ({ ...old, [field.key]: value }))}/>)}</>}
      {error && <div style={{ color: "var(--danger)", fontSize: 12.5, lineHeight: 1.5 }}>{error}</div>}
      {!types.length && <div className="muted" style={{ fontSize: 11.5 }}>{t("類型配置由行業預設及公司設定提供。")}</div>}
      <B kind="primary" icon="plus" disabled={busy || !selectedType} onClick={submit}>{busy ? t("建立中…") : recordText(biu, "建立檔案")}</B>
    </div>
  </div>;
};

const DetailDrawer = ({ initial, meta, onClose, onChanged, biu = false }) => {
  const [record, setRecord] = S(initial);
  const [action, setAction] = S("");
  const [message, setMessage] = S("");
  const [busy, setBusy] = S(false);
  const [error, setError] = S("");
  const [documentForm, setDocumentForm] = S({ field_key: "", title: "", visibility: "record" });
  const [uploading, setUploading] = S(null);
  const [downloading, setDownloading] = S(null);
  const [documentError, setDocumentError] = S("");
  E(() => { setRecord(initial); }, [recordId(initial), initial && initial.lock_version]);
  E(() => {
    setAction(""); setMessage(""); setError("");
    setDocumentForm({ field_key: "", title: "", visibility: "record" });
    setUploading(null); setDownloading(null); setDocumentError("");
  }, [recordId(initial)]);
  const definitions = arr(first(record && record.type_config && record.type_config.fields, record && record.type_fields, []));
  const fieldValues = object(first(record && record.fields, record && record.structured_data, record && record.dynamic_data, {}));
  const fieldLabels = new Map(definitions.map(field => [keyOf(field.key), first(field.label, field.name, field.key)]));
  const relations = arr(first(record && record.relations, record && record.links, record && record.related_records, []));
  const directVersions = arr(first(record && record.document_versions, record && record.versions, []));
  const documents = arr(record && record.documents);
  const versions = directVersions.length ? directVersions : documents.flatMap(document => arr(document.versions).length
    ? document.versions.map(version => ({ ...version, document_name: first(document.name, document.title, document.file_name) }))
    : [document]);
  const documentRequirements = arr(record && record.document_requirements);
  const documentFields = documentRequirements.length ? documentRequirements : definitions
    .filter(field => ["file", "document"].includes(keyOf(field.type)))
    .map(field => ({ field_key: field.key, label: first(field.label, field.name, field.key), required: !!field.required, count: 0, satisfied: false }));
  const documentGroups = documents.length ? documents : (versions.length ? [{ id: null, title: t("文件版本"), versions }] : []);
  const canUploadDocuments = !!(record && record.capabilities && record.capabilities.can_edit);
  const events = arr(first(record && record.timeline, record && record.events, record && record.history, []));
  const rawActions = arr(first(record && record.available_actions, record && record.capabilities && record.capabilities.available_actions, []));
  const actions = rawActions.map(value => typeof value === "object" ? value : { action: value });
  const canCreateTask = !!(W2.hasPermission && W2.hasPermission("tasks.create"));
  const openFollowUpTask = () => {
    const id = recordId(record);
    if (id == null) return;
    const sourceRef = W2.entityRef ? W2.entityRef("record", id) : `record:${id}`;
    const detail = { mode: "task", view: "inbox", source_ref: sourceRef, source_title: recordTitle(record) };
    if (W2.openTaskComposer) W2.openTaskComposer(detail);
    else location.hash = `#/tasks?view=inbox&create=task&source_ref=${encodeURIComponent(sourceRef)}&source_title=${encodeURIComponent(recordTitle(record))}`;
  };
  const reloadRecord = async fallback => {
    try {
      const data = await W2.json(`/api/records/${encodeURIComponent(recordId(record))}`);
      const fresh = recordFrom(data);
      if (fresh && typeof fresh === "object" && recordId(fresh) != null) return fresh;
    } catch (exception) {
      if (!fallback) throw exception;
    }
    return fallback;
  };
  const uploadDocuments = async (selectedFiles, overrides = {}) => {
    const files = Array.from(selectedFiles || []);
    if (!files.length) { setDocumentError(t("請先選擇文件")); return; }
    if (!canUploadDocuments) { setDocumentError(t("沒有上傳文件的權限")); return; }
    setDocumentError("");
    let latest = record;
    try {
      for (let index = 0; index < files.length; index += 1) {
        const file = files[index];
        setUploading({ current: index + 1, total: files.length, name: safeFileName(file.name) });
        const form = new FormData();
        const owns = key => Object.prototype.hasOwnProperty.call(overrides, key);
        const fieldKey = owns("field_key") ? overrides.field_key : documentForm.field_key;
        const title = owns("title") ? overrides.title : documentForm.title;
        const visibility = owns("visibility") ? overrides.visibility : (documentForm.visibility || "record");
        const documentId = owns("document_id") ? overrides.document_id : overrides.documentId;
        if (fieldKey) form.append("field_key", fieldKey);
        if (title) form.append("title", title);
        if (visibility) form.append("visibility", visibility);
        if (documentId != null && documentId !== "") form.append("document_id", String(documentId));
        form.append("lock_version", String(first(latest && latest.lock_version, record.lock_version)));
        form.append("file", file, safeFileName(file.name));
        const response = await W2.fetch(`/api/records/${encodeURIComponent(recordId(record))}/documents`, {
          method: "POST", body: form,
        });
        if (!response.ok) await responseError(response, t("文件上傳失敗"));
        const data = await response.json().catch(() => ({}));
        const candidate = recordFrom(data);
        if (candidate && typeof candidate === "object" && recordId(candidate) != null) latest = candidate;
      }
      latest = await reloadRecord(latest);
      if (latest) { setRecord(latest); onChanged(latest); }
      setDocumentForm(old => ({ ...old, title: "" }));
    } catch (exception) {
      const applied = await reloadRecord(latest).catch(() => latest);
      if (applied) { setRecord(applied); onChanged(applied); }
      setDocumentError(exception.message || t("文件上傳失敗"));
    } finally { setUploading(null); }
  };
  const downloadVersion = async version => {
    const versionId = first(version && version.id, version && version.version_id);
    setDownloading(versionId); setDocumentError("");
    try { await downloadDocumentVersion(record, version); }
    catch (exception) { setDocumentError(exception.message || t("文件下載失敗")); }
    finally { setDownloading(null); }
  };
  const run = async () => {
    if (!action) return;
    setBusy(true); setError("");
    try {
      const data = await W2.post(`/api/records/${encodeURIComponent(recordId(record))}/actions`, {
        action, message, lock_version: record.lock_version,
      });
      const next = recordFrom(data);
      if (!next || typeof next !== "object") throw new Error("操作接口未返回檔案資料");
      setRecord(next); setAction(""); setMessage(""); onChanged(next);
    } catch (exception) { setError(exception.message || "操作失敗"); }
    finally { setBusy(false); }
  };
  return <div className="drawer">
    <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
      <div className="row spread" style={{ marginBottom: 8 }}><div className="row g6"><T tone={statusTone(statusOf(record))} dot>{recordStatusLabel(biu, statusOf(record))}</T><T tone={confTone(confOf(record))}>{labelOf(CONF_LABELS, confOf(record))}</T></div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div>
      <div className="num muted" style={{ fontSize: 10.5 }}>{recordNo(record)}</div>
      <div style={{ fontSize: 19, fontWeight: 760, lineHeight: 1.3, marginTop: 5 }}>{recordTitle(record)}</div>
      <div className="muted" style={{ fontSize: 11.5, marginTop: 5 }}>{t(first(record.category_name_snapshot, record.category_name, categoryName(meta, categoryOfRecord(record))))} · {t(typeName(meta, record))}</div>
      {canCreateTask && <B size="sm" icon="clipboard" onClick={openFollowUpTask} style={{ marginTop: 12 }}>{t("建立跟進任務")}</B>}
    </div>
    <div className="col g18" style={{ padding: 18, maxHeight: "calc(100vh - 215px)", overflowY: "auto" }}>
      <section><L red>{t("基本資料")}</L><div style={{ ...grid(165), marginTop: 8 }}>
        {[
          ["檔案對象", first(record.subject_name, record.subject, record.owner_user_name, record.owner_name, record.person_name)],
          ["歸屬部門", first(record.owner_unit_name, record.department_name, record.owner_department)],
          ["生效日期", shortDate(first(record.effective_at, record.effective_from, record.effective_date))],
          ["到期日期", shortDate(expiresOf(record))],
          ["建立人", first(record.created_by_name, record.creator_name, record.reporter_name)],
          ["更新", dateValue(updatedOf(record))],
        ].map(([label, value]) => <div key={label} style={{ borderTop: "1px solid var(--hair)", paddingTop: 6 }}><L dim>{t(label)}</L><div style={{ fontSize: 12.5, marginTop: 3 }}>{value || "—"}</div></div>)}
      </div>{first(record.description, record.summary) && <div style={{ fontSize: 12.5, lineHeight: 1.65, whiteSpace: "pre-wrap", marginTop: 12 }}>{first(record.description, record.summary)}</div>}</section>

      <section><L red>{t("結構欄位")}</L>{Object.keys(fieldValues).length
        ? <div style={{ marginTop: 8, borderTop: "1px solid var(--rule)" }}>{Object.entries(fieldValues).map(([key, value]) => <div key={key} className="row spread g12" style={{ padding: "8px 0", borderBottom: "1px solid var(--hair-soft)", alignItems: "flex-start" }}><span className="muted" style={{ fontSize: 11.5 }}>{t(fieldLabels.get(key) || key)}</span><span style={{ fontSize: 12.5, maxWidth: "62%", textAlign: "right", whiteSpace: "pre-wrap" }}>{textValue(value)}</span></div>)}</div>
        : <div className="muted" style={{ fontSize: 11.5, marginTop: 7 }}>—</div>}</section>

      <section><L red>{t("關聯")}</L>{relations.length
        ? <div style={{ ...grid(180), marginTop: 8 }}>{relations.map((relation, index) => <div key={relation.id || index} style={card}><div style={{ fontSize: 12.5, fontWeight: 680 }}>{first(relation.label, relation.title, relation.name, relation.target_name, relation.linked_id, "—")}</div><div className="muted" style={{ fontSize: 10.5, marginTop: 5 }}>{first(relation.relation, relation.type, relation.linked_type, "related")}</div></div>)}</div>
        : <div className="muted" style={{ fontSize: 11.5, marginTop: 7 }}>{t("尚無關聯")}</div>}</section>

      <section>
        <div className="row spread g10"><L red>{t("文件版本")}</L>{!!documentGroups.length && <span className="num muted" style={{ fontSize: 10 }}>{documentGroups.length}</span>}</div>
        {!!documentFields.length && <div className="row g6" style={{ flexWrap: "wrap", marginTop: 8 }}>{documentFields.map((field, index) => <T key={field.field_key || index} tone={field.required && !field.satisfied ? "warn" : "plain"} dot={field.required}>{t(first(field.label, field.field_key, "文件"))} · {safeNum(field.count)}</T>)}</div>}

        {canUploadDocuments && <div className="col g8" style={{ marginTop: 10, padding: 11, background: "var(--paper-2)", borderTop: "1px solid var(--rule)" }}>
          <div className="row spread"><span style={{ fontSize: 12.5, fontWeight: 680 }}>{t("新增文件")}</span><I name="inbound" size={14}/></div>
          <div style={grid(145)}>
            <div><L dim>{t("文件欄位")}</L><select className="field boxed" value={documentForm.field_key} onChange={event => setDocumentForm(old => ({ ...old, field_key: event.target.value }))}><option value="">—</option>{documentFields.map(field => <option key={field.field_key} value={field.field_key}>{t(first(field.label, field.field_key))}</option>)}</select></div>
            <div><L dim>{t("文件標題")}</L><input className="field boxed" maxLength="180" value={documentForm.title} onChange={event => setDocumentForm(old => ({ ...old, title: event.target.value }))}/></div>
            <div><L dim>{t("可見範圍")}</L><select className="field boxed" value={documentForm.visibility} onChange={event => setDocumentForm(old => ({ ...old, visibility: event.target.value }))}><option value="record">{t("檔案可見者")}</option><option value="participants">{t("參與者")}</option><option value="managers">{t("管理者")}</option><option value="private">{t("建立人／負責人／保管人")}</option></select></div>
          </div>
          <label className={`btn sm ${uploading ? "disabled" : ""}`} style={{ alignSelf: "flex-start", cursor: uploading ? "wait" : "pointer" }}>
            <I name="inbound" size={12}/>{uploading ? t("上傳中…") : t("選擇文件")}
            <input type="file" multiple disabled={!!uploading} style={{ display: "none" }} onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ""; uploadDocuments(files); }}/>
          </label>
        </div>}

        {uploading && <div className="row g8" style={{ marginTop: 8, fontSize: 11.5 }}><I name="refresh" size={12}/><span>{t("上傳進度")} · {uploading.current}/{uploading.total} · {uploading.name}</span></div>}
        {documentError && <div style={{ color: "var(--red)", fontSize: 12, lineHeight: 1.5, marginTop: 8 }}>{documentError}</div>}

        {documentGroups.length ? <div className="col g10" style={{ marginTop: 10 }}>{documentGroups.map((documentItem, documentIndex) => {
          const itemVersions = arr(documentItem.versions).length ? documentItem.versions : (first(documentItem.file_name, documentItem.filename) ? [documentItem] : []);
          return <div key={documentItem.id || documentIndex} style={{ ...card, padding: 11 }}>
            <div className="row spread g8"><div style={{ minWidth: 0 }}><div style={{ fontSize: 12.5, fontWeight: 690, overflow: "hidden", textOverflow: "ellipsis" }}>{first(documentItem.title, documentItem.name, documentItem.document_name, "未命名文件")}</div><div className="muted" style={{ fontSize: 10.5, marginTop: 3 }}>{documentItem.field_key ? `${t("文件欄位")} · ${t(fieldLabels.get(keyOf(documentItem.field_key)) || documentItem.field_key)}` : t("一般文件")} · {labelOf(VISIBILITY_LABELS, first(documentItem.visibility, "record"))}</div></div>
              {canUploadDocuments && documentItem.id != null && <label className={`btn sm ${uploading ? "disabled" : ""}`} style={{ cursor: uploading ? "wait" : "pointer", flexShrink: 0 }}><I name="plus" size={11}/>{t("上傳新版")}<input type="file" disabled={!!uploading} style={{ display: "none" }} onChange={event => { const files = Array.from(event.target.files || []); event.target.value = ""; uploadDocuments(files.slice(0, 1), { document_id: documentItem.id, field_key: documentItem.field_key, title: documentItem.title, visibility: documentItem.visibility }); }}/></label>}
            </div>
            {itemVersions.length ? <div style={{ borderTop: "1px solid var(--rule)", marginTop: 8 }}>{itemVersions.map((version, versionIndex) => {
              const versionId = first(version.id, version.version_id);
              const current = Number(documentItem.current_version_id || 0) === Number(versionId || -1);
              return <button type="button" key={versionId || versionIndex} disabled={downloading != null} onClick={() => downloadVersion(version)} style={{ width: "100%", display: "grid", gridTemplateColumns: "42px minmax(0,1fr) auto", gap: 9, padding: "9px 0", borderBottom: "1px solid var(--hair-soft)", alignItems: "center", textAlign: "left", cursor: downloading != null ? "wait" : "pointer" }}><span className="num" style={{ fontSize: 10, fontWeight: 720 }}>V{first(version.version_no, version.version, versionIndex + 1)}</span><span style={{ minWidth: 0 }}><span style={{ display: "block", fontSize: 12.5, fontWeight: 650, overflow: "hidden", textOverflow: "ellipsis" }}>{first(version.file_name, version.filename, version.document_name, version.title, "未命名文件")}</span><span className="muted" style={{ display: "block", fontSize: 10.5, marginTop: 3 }}>{dateValue(first(version.created_at, version.uploaded_at))}{current ? ` · ${t("目前版本")}` : ""}</span></span><span className="num muted" style={{ fontSize: 10 }}>{downloading === versionId ? "…" : sizeValue(first(version.file_size, version.size))}</span></button>;
            })}</div> : <div className="muted" style={{ fontSize: 11, marginTop: 7 }}>{t("尚無文件版本")}</div>}
          </div>;
        })}</div> : <div className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>{t("尚無文件版本")}</div>}
      </section>

      {!!actions.length && <section><L red>{t("可用動作")}</L><div className="row g6" style={{ flexWrap: "wrap", marginTop: 8 }}>{actions.map((item, index) => {
        const key = keyOf(first(item.action, item.key, item.id));
        const rawLabel = keyOf(item.label);
        return <button key={key || index} className={`chip ${action === key ? "on" : ""}`} onClick={() => { setAction(key); setError(""); }}>{biu && (!rawLabel || rawLabel === key) ? recordActionLabel(true, key) : t(first(item.label, ACTION_LABELS[key], key))}</button>;
      })}</div>{action && <div className="col g9" style={{ marginTop: 11, padding: 12, background: "var(--paper-2)", borderTop: "1px solid var(--rule)" }}><textarea className="field boxed" style={{ height: 70, paddingTop: 9 }} value={message} onChange={event => setMessage(event.target.value)} placeholder={t("操作說明")}/><B kind="primary" disabled={busy} onClick={run}>{busy ? "…" : `${recordText(biu, "執行")} · ${recordActionLabel(biu, action)}`}</B></div>}</section>}
      {error && <div style={{ color: "var(--danger)", fontSize: 12.5 }}>{error}</div>}

      <section><L red>{t("時間線")}</L>{events.length
        ? <div style={{ borderTop: "2px solid var(--rule)", marginTop: 8 }}>{events.slice().reverse().map((event, index) => {
          const eventKey = keyOf(first(event.event_type, event.action, event.type));
          const rawLabel = keyOf(event.label);
          return <div key={event.id || index} style={{ display: "grid", gridTemplateColumns: "26px minmax(0,1fr)", gap: 8, padding: "9px 0", borderBottom: "1px solid var(--hair-soft)" }}><span className="num muted" style={{ fontSize: 9 }}>{String(events.length - index).padStart(2, "0")}</span><div><div className="row spread g8"><span style={{ fontSize: 12.5, fontWeight: 650 }}>{biu && (!rawLabel || rawLabel === eventKey) ? recordActionLabel(true, eventKey || "updated") : t(first(event.label, ACTION_LABELS[eventKey], eventKey, "更新"))}</span><span className="num muted" style={{ fontSize: 9.5 }}>{dateValue(first(event.created_at, event.occurred_at))}</span></div><div className="muted" style={{ fontSize: 10.5, marginTop: 3 }}>{first(event.actor_name, event.created_by_name, event.actor_kind, "system")}</div>{first(event.message, event.note, event.description) && <div style={{ fontSize: 12, lineHeight: 1.5, whiteSpace: "pre-wrap", marginTop: 4 }}>{first(event.message, event.note, event.description)}</div>}</div></div>;
        })}</div>
        : <div className="muted" style={{ fontSize: 11.5, marginTop: 7 }}>{t("尚無時間線")}</div>}</section>
    </div>
  </div>;
};

class LegacyBoundary extends React.Component {
  constructor(props) { super(props); this.state = { failed: false }; }
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error) { if (window.console) console.error("Legacy case page failed", error); }
  render() {
    if (this.state.failed) return <Empty icon="alert" title={t("原事務頁載入失敗")} sub={t("請刷新頁面後重試。")}/>;
    return this.props.children;
  }
}

const LegacyPanel = ({ initialCaseId, onInitialCaseOpened, templateKey = "" }) => {
  if (typeof LegacyCasePage !== "function") return <Empty icon="alert" title={t("原事務頁未載入")} sub={t("請確認 pages-cases.jsx 先於本頁載入。")}/>;
  return <LegacyBoundary><LegacyCasePage initialCaseId={initialCaseId} onInitialCaseOpened={onInitialCaseOpened} templateKey={templateKey}/></LegacyBoundary>;
};

const TYPE_ADVANCED_CONFIG_KEYS = [
  "fields", "statuses", "initial_status", "terminal_statuses",
  "transitions", "reminders", "retention",
];
const configRevisionOf = value => Math.max(1, safeNum(first(value && value.revision_no, value && value.version, 1)));
const typeAdvancedConfigOf = type => {
  const result = {};
  TYPE_ADVANCED_CONFIG_KEYS.forEach(key => {
    if (type && type[key] !== undefined) result[key] = type[key];
  });
  return result;
};
const prettyConfig = value => JSON.stringify(value == null ? {} : value, null, 2);
const parseConfigObject = (source, label) => {
  let parsed;
  try { parsed = JSON.parse(String(source || "{}")); }
  catch (exception) { throw new Error(`${label}：${t("配置 JSON 格式不正確")}`); }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error(`${label}：${t("配置 JSON 必須是物件")}`);
  return parsed;
};

const ConfigMutationDrawer = ({ kind, action, target, meta, onClose, onDone }) => {
  const isType = kind === "type";
  const plural = isType ? "types" : "categories";
  const targetKey = isType ? typeKeyOf(target) : categoryKeyOf(target);
  const revisionNo = configRevisionOf(target);
  const activeCategories = categoriesOf(meta).filter(item => item.active !== false);
  const [form, setForm] = S({
    key: action === "create" ? "" : targetKey,
    name: first(target && target.name, target && target.label, ""),
    description: first(target && target.description, ""),
    icon: first(target && target.icon, "doc"),
    order: safeNum(first(target && target.order, target && target.sort_order, 0)),
    category_key: first(target && target.category_key, target && target.category, activeCategories[0] && categoryKeyOf(activeCategories[0]), ""),
    lifecycle_mode: first(target && target.lifecycle_mode, "dossier"),
    owner_unit_code: first(target && target.owner_unit_code, ""),
    confidentiality: first(target && target.confidentiality, "internal"),
  });
  const [retentionText, setRetentionText] = S(prettyConfig(first(target && target.retention, {})));
  const [advancedText, setAdvancedText] = S(prettyConfig(typeAdvancedConfigOf(target)));
  const endpoint = action === "create"
    ? `/api/records/config/${plural}`
    : `/api/records/config/${plural}/${encodeURIComponent(targetKey)}/${action === "disable" ? "disable" : "revisions"}`;
  const disablePayload = { expected_revision_no: revisionNo };
  const [preview, setPreview] = S(action === "disable" ? {
    operation: `${isType ? t("類型") : t("分類")} · ${t("停用")}`,
    endpoint,
    payload: disablePayload,
  } : null);
  const [busy, setBusy] = S(false);
  const [error, setError] = S("");
  const templateFork = action === "revise" && !!(target && target.managed_by_template);
  const setValue = (key, value) => { setForm(current => ({ ...current, [key]: value })); setError(""); };

  const preparePreview = () => {
    try {
      const key = keyOf(form.key).trim();
      const name = String(form.name || "").trim();
      if (!key || !name) throw new Error(t("請填寫配置代碼與名稱"));
      if (!/^[a-z][a-z0-9_]{2,79}$/.test(key)) throw new Error("配置代碼只可使用小寫字母、數字與底線，長度 3-80");
      let payload;
      if (isType) {
        if (!form.category_key) throw new Error(t("請選擇分類"));
        const advanced = parseConfigObject(advancedText, t("高級配置 JSON"));
        const unknown = Object.keys(advanced).filter(keyName => !TYPE_ADVANCED_CONFIG_KEYS.includes(keyName));
        if (unknown.length) throw new Error(`高級配置包含不支援欄位：${unknown.join("、")}`);
        payload = {
          ...advanced,
          key,
          category_key: form.category_key,
          name,
          description: String(form.description || "").trim(),
          lifecycle_mode: form.lifecycle_mode,
          owner_unit_code: String(form.owner_unit_code || "").trim(),
          confidentiality: form.confidentiality,
        };
      } else {
        payload = {
          key,
          name,
          description: String(form.description || "").trim(),
          icon: String(form.icon || "").trim(),
          order: Math.trunc(safeNum(form.order)),
          owner_unit_code: String(form.owner_unit_code || "").trim(),
          confidentiality: form.confidentiality,
          retention: parseConfigObject(retentionText, t("保管規則 JSON")),
        };
      }
      if (action === "revise") payload.expected_revision_no = revisionNo;
      setPreview({
        operation: `${isType ? t("類型") : t("分類")} · ${action === "create" ? t("新增") : t("修訂")}`,
        endpoint,
        payload,
      });
      setError("");
    } catch (exception) { setError(exception.message || t("配置 JSON 格式不正確")); }
  };
  const submitPreview = async () => {
    if (!preview || busy) return;
    setBusy(true); setError("");
    try {
      const result = await W2.post(preview.endpoint, preview.payload);
      onClose();
      if (onDone) await onDone(result);
    } catch (exception) { setError(exception.message || "配置提交失敗"); }
    finally { setBusy(false); }
  };

  return <div className="drawer">
    <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
      <div className="row spread"><div><L red>RECORD CONFIG</L><div style={{ fontSize: 19, fontWeight: 760, marginTop: 5 }}>{t(action === "create" ? (isType ? "新增類型" : "新增分類") : action === "disable" ? "停用" : "修訂")}</div></div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div>
    </div>
    <div className="col g14" style={{ padding: 18, maxHeight: "calc(100vh - 160px)", overflowY: "auto" }}>
      {templateFork && <div style={{ border: "1px solid var(--red)", padding: 11, fontSize: 12.5, lineHeight: 1.5 }}><strong>{t("修訂後轉為公司自管")}</strong><div className="muted" style={{ marginTop: 4 }}>{t("現有檔案繼續使用原版本；新版本只套用於後續建檔。")}</div></div>}
      {!preview && <>
        <div><L dim>{t("配置代碼")} *</L><input className="field boxed" disabled={action !== "create"} value={form.key} onChange={event => setValue("key", event.target.value)} placeholder="lowercase_key"/>{action !== "create" && <div className="muted" style={{ fontSize: 10.5, marginTop: 4 }}>{t("建立後不可修改")}</div>}</div>
        <div><L dim>{t("名稱")} *</L><input className="field boxed" value={form.name} onChange={event => setValue("name", event.target.value)}/></div>
        <div><L dim>{t("說明")}</L><textarea className="field boxed" style={{ height: 75, paddingTop: 9 }} value={form.description} onChange={event => setValue("description", event.target.value)}/></div>
        {isType ? <>
          <div style={grid(170)}>
            <div><L dim>{t("分類")} *</L><select className="field boxed" value={form.category_key} onChange={event => setValue("category_key", event.target.value)}><option value="">—</option>{activeCategories.map(item => <option key={categoryKeyOf(item)} value={categoryKeyOf(item)}>{t(first(item.name, item.label, categoryKeyOf(item)))}</option>)}</select></div>
            <div><L dim>{t("生命週期")}</L><select className="field boxed" value={form.lifecycle_mode} onChange={event => setValue("lifecycle_mode", event.target.value)}>{["dossier", "event", "document", "workflow"].map(value => <option key={value} value={value}>{value}</option>)}</select></div>
          </div>
          <div style={grid(170)}>
            <div><L dim>{t("責任部門代碼")}</L><input className="field boxed" value={form.owner_unit_code} onChange={event => setValue("owner_unit_code", event.target.value)}/></div>
            <div><L dim>{t("密級")}</L><select className="field boxed" value={form.confidentiality} onChange={event => setValue("confidentiality", event.target.value)}>{["internal", "sensitive", "restricted"].map(value => <option key={value} value={value}>{labelOf(CONF_LABELS, value)}</option>)}</select></div>
          </div>
          <div><L dim>{t("高級配置 JSON")}</L><textarea className="field boxed num" spellCheck="false" style={{ minHeight: 260, paddingTop: 9, fontSize: 11.5, lineHeight: 1.55 }} value={advancedText} onChange={event => { setAdvancedText(event.target.value); setError(""); }}/><div className="muted" style={{ fontSize: 10.5, marginTop: 4 }}>{t("高級配置只可包含欄位、狀態、流轉、提醒與保管規則。")}</div></div>
        </> : <>
          <div style={grid(160)}>
            <div><L dim>{t("圖示")}</L><input className="field boxed" value={form.icon} onChange={event => setValue("icon", event.target.value)}/></div>
            <div><L dim>{t("排序")}</L><input className="field boxed" type="number" value={form.order} onChange={event => setValue("order", event.target.value)}/></div>
          </div>
          <div style={grid(170)}>
            <div><L dim>{t("責任部門代碼")}</L><input className="field boxed" value={form.owner_unit_code} onChange={event => setValue("owner_unit_code", event.target.value)}/></div>
            <div><L dim>{t("密級")}</L><select className="field boxed" value={form.confidentiality} onChange={event => setValue("confidentiality", event.target.value)}>{["internal", "sensitive", "restricted"].map(value => <option key={value} value={value}>{labelOf(CONF_LABELS, value)}</option>)}</select></div>
          </div>
          <div><L dim>{t("保管規則 JSON")}</L><textarea className="field boxed num" spellCheck="false" style={{ minHeight: 150, paddingTop: 9, fontSize: 11.5, lineHeight: 1.55 }} value={retentionText} onChange={event => { setRetentionText(event.target.value); setError(""); }}/></div>
        </>}
        <B kind="primary" icon="eye" onClick={preparePreview}>{t("預覽變更")}</B>
      </>}
      {preview && <>
        <div><L red>{t("完整提交預覽")}</L><pre style={{ margin: "8px 0 0", padding: 12, border: "1px solid var(--hair)", background: "var(--paper-2)", fontSize: 11.5, lineHeight: 1.55, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(preview, null, 2)}</pre></div>
        {action === "revise" && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.5 }}>{t("現有檔案繼續使用原版本；新版本只套用於後續建檔。")}</div>}
        <div className="row g8"><B disabled={busy} onClick={() => { if (action === "disable") onClose(); else setPreview(null); }}>{t(action === "disable" ? "取消" : "返回修改")}</B><B kind="primary" icon={action === "disable" ? "archive" : "check"} disabled={busy} onClick={submitPreview}>{busy ? "…" : t(action === "disable" ? "確認停用" : "確認提交")}</B></div>
      </>}
      {error && <div style={{ color: "var(--danger)", fontSize: 12.5, lineHeight: 1.5 }}>{error}</div>}
    </div>
  </div>;
};

const TypesPanel = ({ meta, onChanged }) => {
  const canConfigure = !!(meta && meta.can_configure === true);
  const [catalogMeta, setCatalogMeta] = S(meta);
  const [editor, setEditor] = S(null);
  const [configError, setConfigError] = S("");
  const loadConfiguration = async () => {
    if (!canConfigure) { setCatalogMeta(meta); return; }
    try {
      const next = object(await W2.json("/api/records/config"));
      setCatalogMeta(next); setConfigError("");
    } catch (exception) { setConfigError(exception.message || "配置載入失敗"); }
  };
  E(() => { loadConfiguration(); }, [canConfigure, meta && meta.template_revision]);
  const mutationDone = async () => {
    await loadConfiguration();
    if (onChanged) await onChanged();
  };
  const sourceMeta = canConfigure ? (catalogMeta || meta) : meta;
  const types = typesOf(sourceMeta);
  const categories = categoriesOf(sourceMeta);
  const openEditor = (kind, action, target = null) => setEditor({ kind, action, target });
  const sourceTag = value => value && value.managed_by_template
    ? <T tone="warn">{t("行業模板")}</T> : <T tone="plain">{t("公司自管")}</T>;
  return <div className="col g18">
    <div className="row spread g12" style={{ alignItems: "flex-start" }}><div><L red>{t("類型設定")}</L><div className="muted" style={{ fontSize: 11.5, marginTop: 5 }}>{t(canConfigure ? "現有檔案繼續使用原版本；新版本只套用於後續建檔。" : "只有具備 records.config.manage 權限者可修改分類與類型。")}</div></div><T tone="plain">{types.length}</T></div>
    {configError && <div style={{ color: "var(--red)", fontSize: 12.5 }}>{configError}</div>}

    {canConfigure && <section>
      <div className="row spread g10" style={{ marginBottom: 10 }}><div><L red>{t("分類設定")}</L><div className="muted" style={{ fontSize: 10.5, marginTop: 4 }}>{categories.length} {t("個分類")}</div></div><B kind="primary" size="sm" icon="plus" onClick={() => openEditor("category", "create")}>{t("新增分類")}</B></div>
      <div style={grid(250)}>{categories.map((category, index) => <div key={categoryKeyOf(category) || index} style={{ ...card, borderTop: `3px solid ${category.active === false ? "var(--hair)" : "var(--rule)"}` }}>
        <div className="row spread g8"><div className="row g6"><T tone={category.active === false ? "plain" : "ok"} dot>{category.active === false ? t("停用") : t("啟用")}</T>{sourceTag(category)}</div><span className="num muted" style={{ fontSize: 9 }}>R{configRevisionOf(category)}</span></div>
        <div style={{ fontSize: 14.5, fontWeight: 720, marginTop: 9 }}>{t(first(category.name, category.label, category.key, "未命名分類"))}</div>
        <div className="muted num" style={{ fontSize: 9.5, marginTop: 4 }}>{categoryKeyOf(category)}</div>
        <div className="muted" style={{ fontSize: 11.5, minHeight: 34, lineHeight: 1.5, marginTop: 5 }}>{t(first(category.description, ""))}</div>
        {category.active !== false && <div className="row g6" style={{ marginTop: 10 }}><B size="sm" onClick={() => openEditor("category", "revise", category)}>{t("修訂")}</B><B size="sm" onClick={() => openEditor("category", "disable", category)}>{t("停用")}</B></div>}
      </div>)}</div>
    </section>}

    <section>
      <div className="row spread g10" style={{ marginBottom: 10 }}><L red>{t("類型")}</L>{canConfigure && <B kind="primary" size="sm" icon="plus" disabled={!categories.some(item => item.active !== false)} onClick={() => openEditor("type", "create")}>{t("新增類型")}</B>}</div>
      {!types.length ? <Empty icon="gear" title={t("尚無檔案類型")} sub={t("類型配置由行業預設及公司設定提供。")} /> : <div style={grid(250)}>{types.map((type, index) => <div key={typeKeyOf(type) || index} style={{ ...card, borderTop: "3px solid var(--rule)" }}>
        <div className="row spread g8"><div className="row g6"><T tone={type.active === false ? "plain" : "ok"} dot>{type.active === false ? t("停用") : t("啟用")}</T>{canConfigure && sourceTag(type)}</div><span className="num muted" style={{ fontSize: 9 }}>R{configRevisionOf(type)}</span></div>
        <div style={{ fontSize: 14.5, fontWeight: 720, marginTop: 9 }}>{t(first(type.name, type.label, type.key, "未命名類型"))}</div>
        <div className="muted num" style={{ fontSize: 9.5, marginTop: 4 }}>{typeKeyOf(type)}</div>
        <div className="muted" style={{ fontSize: 11.5, minHeight: 34, lineHeight: 1.5, marginTop: 5 }}>{t(first(type.description, ""))}</div>
        <div className="row spread g8" style={{ marginTop: 10 }}><span style={{ fontSize: 11 }}>{t(categoryName(sourceMeta, first(type.category_key, type.category)))}</span><span className="num muted" style={{ fontSize: 10 }}>{arr(first(type.fields, type.form_fields, [])).length} {t("欄位")}</span></div>
        {canConfigure && type.active !== false && <div className="row g6" style={{ marginTop: 10 }}><B size="sm" onClick={() => openEditor("type", "revise", type)}>{t("修訂")}</B><B size="sm" onClick={() => openEditor("type", "disable", type)}>{t("停用")}</B></div>}
      </div>)}</div>}
    </section>
    {editor && <ConfigMutationDrawer key={`${editor.kind}:${editor.action}:${editor.target ? (editor.kind === "type" ? typeKeyOf(editor.target) : categoryKeyOf(editor.target)) : "new"}`} kind={editor.kind} action={editor.action} target={editor.target} meta={sourceMeta} onClose={() => setEditor(null)} onDone={mutationDone}/>}
  </div>;
};

const RecordsPage = ({ templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const [tab, setTab] = S("overview");
  const [meta, setMeta] = S(null);
  const [rows, setRows] = S([]);
  const [overviewExpiringRows, setOverviewExpiringRows] = S([]);
  const [summary, setSummary] = S({});
  const [total, setTotal] = S(0);
  const [hasMore, setHasMore] = S(false);
  const [query, setQuery] = S("");
  const [category, setCategory] = S("");
  const [typeKey, setTypeKey] = S("");
  const [status, setStatus] = S("");
  const [confidentiality, setConfidentiality] = S("");
  const [includeArchived, setIncludeArchived] = S(false);
  const [loading, setLoading] = S(true);
  const [listLoading, setListLoading] = S(false);
  const [error, setError] = S("");
  const [selected, setSelected] = S(null);
  const [creating, setCreating] = S(false);
  const [legacyCaseId, setLegacyCaseId] = S(null);
  const [detailLoading, setDetailLoading] = S(false);
  const mounted = R(true);
  const initialDone = R(false);
  const listSequence = R(0);
  const expirySequence = R(0);
  const detailSequence = R(0);
  const refreshRef = R(null);
  const openDetailRef = R(null);

  E(() => () => { mounted.current = false; }, []);

  const filterBody = (expiring = false, offset = 0) => {
    const body = { limit: 100, offset };
    if (query.trim()) body.q = query.trim();
    if (category) body.category_key = category;
    if (typeKey) body.type_key = typeKey;
    if (status) body.status = status;
    if (confidentiality) body.confidentiality = confidentiality;
    if (includeArchived) body.include_archived = true;
    if (expiring) { body.expiring_only = true; body.expiring_days = 30; }
    else if (!biu) body.include_legacy = true;
    return body;
  };
  const overviewExpiryBody = () => ({ limit: 8, offset: 0, expiring_only: true, expiring_days: 30 });
  const acceptList = (data, append = false, offset = 0) => {
    const found = recordsFrom(data);
    const nextTotal = safeNum(first(data && data.total, data && data.count, found.length));
    setRows(current => {
      if (!append) return found;
      const merged = [...current];
      const known = new Set(current.map(record => recordId(record)).filter(id => id != null).map(String));
      found.forEach(record => {
        const id = recordId(record);
        if (id == null || !known.has(String(id))) merged.push(record);
        if (id != null) known.add(String(id));
      });
      return merged;
    });
    setTotal(nextTotal);
    setHasMore(offset + found.length < nextTotal);
    setSummary(object(first(data && data.summary, data && data.facets, {})));
  };
  const loadList = async (expiring = tab === "expiring", options = {}) => {
    const append = !!options.append;
    const offset = append ? rows.length : 0;
    const request = ++listSequence.current;
    setListLoading(true);
    try {
      const data = await W2.post("/api/records/search", filterBody(expiring, offset));
      if (!mounted.current || request !== listSequence.current) return;
      acceptList(data || {}, append, offset); setError("");
    } catch (exception) {
      if (mounted.current && request === listSequence.current) setError(exception.message || t("檔案管理 API 尚未啟用或暫時無法連線。"));
    } finally {
      if (mounted.current && request === listSequence.current) setListLoading(false);
    }
  };
  const loadOverviewExpiring = async () => {
    const request = ++expirySequence.current;
    try {
      const data = await W2.post("/api/records/search", overviewExpiryBody());
      if (mounted.current && request === expirySequence.current) setOverviewExpiringRows(recordsFrom(data));
    } catch (exception) {}
  };
  const refresh = async () => {
    const request = ++listSequence.current;
    const expiryRequest = ++expirySequence.current;
    setLoading(true); setError("");
    const results = await Promise.allSettled([
      W2.json("/api/records/meta"),
      W2.post("/api/records/search", filterBody(tab === "expiring", 0)),
      W2.post("/api/records/search", overviewExpiryBody()),
    ]);
    if (!mounted.current || request !== listSequence.current) return;
    const messages = [];
    if (results[0].status === "fulfilled") setMeta(object(results[0].value));
    else messages.push(results[0].reason && results[0].reason.message);
    if (results[1].status === "fulfilled") acceptList(results[1].value || {});
    else messages.push(results[1].reason && results[1].reason.message);
    if (results[2].status === "fulfilled" && expiryRequest === expirySequence.current) {
      setOverviewExpiringRows(recordsFrom(results[2].value));
    }
    setError(messages.filter(Boolean).join(" · "));
    setLoading(false); setListLoading(false); initialDone.current = true;
  };

  E(() => { refresh(); }, []);
  E(() => {
    if (!initialDone.current || !["overview", "all", "expiring"].includes(tab)) return undefined;
    const timer = setTimeout(() => loadList(tab === "expiring"), 240);
    return () => clearTimeout(timer);
  }, [query, category, typeKey, status, confidentiality, includeArchived, tab]);

  const openDetail = async record => {
    setCreating(false);
    if (!biu && isLegacyRecord(record)) {
      const caseId = legacyCaseIdOf(record);
      if (caseId != null && caseId !== "") {
        detailSequence.current += 1;
        setSelected(null); setDetailLoading(false);
        setLegacyCaseId(caseId);
        setTab("legacy");
      }
      return;
    }
    const id = record && typeof record === "object" ? recordId(record) : record;
    if (id == null) return;
    const request = ++detailSequence.current;
    setDetailLoading(true); setError("");
    try {
      const data = await W2.json(`/api/records/${encodeURIComponent(id)}`);
      if (mounted.current && request === detailSequence.current) setSelected(recordFrom(data));
    } catch (exception) {
      if (mounted.current && request === detailSequence.current) setError(exception.message || "檔案詳情載入失敗");
    } finally {
      if (mounted.current && request === detailSequence.current) setDetailLoading(false);
    }
  };
  refreshRef.current = refresh;
  openDetailRef.current = openDetail;
  E(() => {
    const rawQuery = String(location.hash || "").split("?")[1] || "";
    const params = new URLSearchParams(rawQuery);
    const recordIdFromTask = params.get("record");
    if (!/^\d+$/.test(recordIdFromTask || "")) return undefined;
    const timer = setTimeout(() => { if (openDetailRef.current) openDetailRef.current(Number(recordIdFromTask)); }, 0);
    return () => clearTimeout(timer);
  }, []);
  E(() => {
    const onRecordCreated = async event => {
      const detail = object(event && event.detail);
      const record = object(first(detail.record, detail.record_summary, {}));
      const id = Number(first(detail.record_id, record.id, record.record_id));
      if (!Number.isInteger(id) || id <= 0) return;
      try {
        if (refreshRef.current) await refreshRef.current();
        if (mounted.current && openDetailRef.current) await openDetailRef.current(id);
      } catch (exception) {
        if (mounted.current) setError(exception.message || t("檔案詳情載入失敗"));
      }
    };
    window.addEventListener("w2-record-created", onRecordCreated);
    return () => window.removeEventListener("w2-record-created", onRecordCreated);
  }, []);
  const closeDetail = () => {
    detailSequence.current += 1;
    setSelected(null); setDetailLoading(false);
  };
  const openCreate = () => {
    detailSequence.current += 1;
    setSelected(null); setDetailLoading(false);
    setCreating(true);
  };
  const changed = next => {
    setSelected(next);
    loadList(tab === "expiring");
    loadOverviewExpiring();
  };
  const directCreated = async created => {
    setCreating(false);
    await refresh();
    const id = recordId(created);
    if (id != null) await openDetail(id);
  };
  const chooseCategory = key => {
    if (!biu && keyOf(key) === "case_index") { setTab("legacy"); return; }
    setCategory(key); setTab("all");
  };
  const permissions = object(meta && meta.permissions);
  const canCreate = !!Object.keys(object(meta)).length && permissions.can_create === true;
  const canUseAI = permissions.can_use_ai === true;
  const askCreateRecord = () => {
    if (!canCreate || !canUseAI) return;
    const filters = {
      ...(category ? { category_key: category } : {}),
      ...(typeKey ? { type_key: typeKey } : {}),
    };
    const context = {
      page: "records", intent: "create_record", request_id: newRecordCreateRequestId(), tab,
      filters,
      types: typesOf(meta).filter(type => type.active !== false && type.can_create !== false).map(createTypeContext),
    };
    const prompt = [
      "[RECORD_CREATE_ENTRY_V1]",
      "我要建立一份檔案。首輪只能查詢檔案 meta、協助選型並追問，不得呼叫 create 或 record_create。",
      "每次只追問 1-3 個問題；不得猜測任何缺失值。必要資料齊全後直接呼叫 record_create 產生確認卡，不要在聊天中再次要求確認摘要。",
      "文字回覆不得聲稱檔案已建立；真正建立只由確認卡的「確認建立」按鈕完成。",
      "若所選類型含 required_documents，建檔完成後提醒使用者到檔案詳情上傳；不得猜測或省略必要文件。",
      `CONTEXT_JSON=${JSON.stringify(context)}`,
    ].join("\n");
    W2.openSecretary(prompt, { display_text: biu ? t("我要建立一份案件卷宗／文書") : t("我要建立一份檔案"), intent: "record_create" });
  };
  const createButtons = () => canCreate ? <div className="row g6">
    {canUseAI && <B size="sm" icon="sparkle" onClick={askCreateRecord}>{t("交給 AI 秘書")}</B>}
    <B kind="primary" size="sm" icon="plus" onClick={openCreate}>{recordText(biu, "新建檔案")}</B>
  </div> : null;
  const metaTotals = object(meta && meta.summary);
  const totals = { ...summary, ...metaTotals };
  const recordsTotal = safeNum(first(metaTotals.records_total, total));
  const legacyCount = biu ? 0 : safeNum(metaTotals.legacy_cases);
  const allTotal = biu
    ? safeNum(first(metaTotals.records_total, total))
    : safeNum(first(metaTotals.total, total));
  const categoryCount = categoriesOf(meta).length;
  const expiringRows = overviewExpiringRows;
  const canReadTasks = !!(W2.hasPermission && W2.hasPermission("tasks.read"));
  E(() => {
    if ((tab === "tasks" && !canReadTasks) || (biu && tab === "legacy")) {
      setTab("overview");
    }
  }, [tab, canReadTasks, biu]);
  const selectTab = id => {
    if (id === "tasks") {
      detailSequence.current += 1;
      setSelected(null);
      setDetailLoading(false);
      setCreating(false);
    }
    setTab(id);
  };
  const taskTab = { id: "tasks", no: "05", label: "任務與計劃" };
  const tabs = [
    ["overview", "01", "總覽"], ["all", "02", "全部檔案"], ["categories", "03", "分類庫"],
    ["expiring", "04", "到期提醒"], ...(canReadTasks ? [[taskTab.id, taskTab.no, taskTab.label]] : []),
    ...(!biu ? [["legacy", "06", "事務檔案"]] : []), ["types", "07", "類型設定"],
  ];
  const filterBar = <div className="row g8" style={{ flexWrap: "wrap", marginBottom: 15 }}>
    <div style={{ position: "relative", flex: "1 1 230px" }}><I name="search" size={14} style={{ position: "absolute", left: 10, top: 13, pointerEvents: "none" }}/><input className="field boxed" style={{ paddingLeft: 32 }} value={query} onChange={event => setQuery(event.target.value)} placeholder={t("搜尋編號、標題、對象或內容")}/></div>
    <select className="field boxed" style={{ width: 150 }} value={category} onChange={event => setCategory(event.target.value)}><option value="">{t("全部分類")}</option>{categoriesOf(meta).map(item => <option key={categoryKeyOf(item)} value={categoryKeyOf(item)}>{t(first(item.name, item.label, categoryKeyOf(item)))}</option>)}</select>
    <select className="field boxed" style={{ width: 155 }} value={typeKey} onChange={event => setTypeKey(event.target.value)}><option value="">{t("全部類型")}</option>{typesOf(meta).map(item => <option key={typeKeyOf(item)} value={typeKeyOf(item)}>{t(first(item.name, item.label, typeKeyOf(item)))}</option>)}</select>
    <select className="field boxed" style={{ width: 135 }} value={status} onChange={event => setStatus(event.target.value)}><option value="">{t("全部狀態")}</option>{statusesOf(meta).map(item => <option key={item.value} value={item.value}>{biu && (!item.label || keyOf(item.label) === keyOf(item.value)) ? recordStatusLabel(true, item.value) : labelOf(STATUS_LABELS, item.label || item.value)}</option>)}</select>
    <select className="field boxed" style={{ width: 125 }} value={confidentiality} onChange={event => setConfidentiality(event.target.value)}><option value="">{t("全部密級")}</option>{confidentialitiesOf(meta).map(item => <option key={item.value} value={item.value}>{labelOf(CONF_LABELS, item.label || item.value)}</option>)}</select>
    <label className={`chip ${includeArchived ? "on" : ""}`} style={{ cursor: "pointer" }}><input type="checkbox" checked={includeArchived} onChange={event => setIncludeArchived(event.target.checked)}/><span>{t("包含封存")}</span></label>
    <B size="sm" icon="refresh" onClick={() => loadList(tab === "expiring")}>{t("刷新")}</B>
    {createButtons()}
  </div>;
  const listFooter = hasMore ? <div className="row spread g10" style={{ marginTop: 12 }}>
    <span className="muted" style={{ fontSize: 11 }}>{t("已載入")} {rows.length} / {total}</span>
    <B size="sm" disabled={listLoading} onClick={() => loadList(tab === "expiring", { append: true })}>{t("載入更多")}</B>
  </div> : null;

  return <>
    <Folio no="17" en="RECORDS" title={recordText(biu, "檔案管理")} sub={recordText(biu, "企業卷宗 · 分類歸檔 · 版本留痕 · 到期治理")}
      right={!(["legacy", "tasks"].includes(tab)) ? createButtons() : null}/>
    <div className="subnav" style={{ marginBottom: 18 }}>{tabs.map(([id, no, label]) => <button key={id} className={tab === id ? "on" : ""} onClick={() => selectTab(id)}><span className="sn-no">{no}</span>{recordText(biu, label)}{id === "all" && <span className="sn-count">{allTotal}</span>}{id === "legacy" && legacyCount > 0 && <span className="sn-count">{legacyCount}</span>}</button>)}</div>

    <div className="records-workspace" style={{ display: "flex", gap: 18, alignItems: "flex-start" }}>
      <div className="records-workspace-main" style={{ flex: 1, minWidth: 0 }}>

        {!(["legacy", "tasks"].includes(tab)) && error && <ApiError message={error} onRetry={refresh}/>}
        {detailLoading && <div className="muted" style={{ fontSize: 11.5, marginBottom: 10 }}>{t("檔案詳情載入中…")}</div>}

        {!biu && tab === "legacy" && <LegacyPanel initialCaseId={legacyCaseId} onInitialCaseOpened={openedId => setLegacyCaseId(current => keyOf(current) === keyOf(openedId) ? null : current)} templateKey={templateKey}/>}

        {tab === "tasks" && canReadTasks && (W2.TaskManagementPanel
          ? <W2.TaskManagementPanel key={W2.tenant()} embedded initialView="inbox" templateKey={templateKey}/>
          : <Empty icon="clipboard" title={t("任務工作區未載入")} sub={t("請刷新頁面後重試。")} />)}

        {tab === "overview" && <div className="col g18">
      <div className="kpi-band" style={{ ...grid(170), gap: 0 }}>
        <Kpi label={recordText(biu, "檔案總數")} value={safeNum(first(totals.total, total))}/>
        <Kpi label={recordText(biu, "通用檔案")} value={recordsTotal}/>
        {!biu && <Kpi label={recordText(biu, "事務檔案")} value={legacyCount}/>}
        <Kpi label={recordText(biu, "即將到期")} value={safeNum(first(totals.expiring, totals.expiring_soon))} red={safeNum(first(totals.expiring, totals.expiring_soon)) > 0}/>
        <Kpi label={t("受限檔案")} value={safeNum(first(totals.restricted, totals.sensitive))}/>
        <Kpi label={t("分類") } value={safeNum(first(totals.category_count, categoryCount))}/>
      </div>
      {!biu && legacyCount > 0 && <button type="button" onClick={() => setTab("legacy")} style={{ ...card, cursor: "pointer", borderTop: "3px solid var(--red)", display: "grid", gridTemplateColumns: "40px minmax(0,1fr) auto", gap: 12, alignItems: "center" }}>
        <span style={{ width: 40, height: 40, border: "1px solid var(--hair)", display: "grid", placeItems: "center" }}><I name="layers" size={18}/></span>
        <span style={{ minWidth: 0, textAlign: "left" }}><span style={{ display: "block", fontSize: 14, fontWeight: 730 }}>{recordText(biu, "已收錄事務檔案")}</span><span className="muted" style={{ display: "block", fontSize: 11.5, marginTop: 4 }}>{recordText(biu, "保留原事務流程與權限，不重複搬移資料。")}</span></span>
        <span className="row g8"><span className="num" style={{ fontSize: 22, fontWeight: 780 }}>{legacyCount}</span><span className="chip">{recordText(biu, "查看事務檔案")}</span></span>
      </button>}
      <Band no="A" title={recordText(biu, "分類庫")} right={<button className="chip" onClick={() => setTab("categories")}>{t("查看全部")}</button>}>
        <CategoryCards meta={meta} summary={totals} onSelect={chooseCategory} compact/>
      </Band>
      <div className="records-overview-split">
        <Band no="B" title={t("最近更新")}><RecordTable rows={rows.slice(0, 8)} meta={meta} loading={loading || listLoading} onOpen={openDetail} biu={biu}/></Band>
        <Band no="C" title={recordText(biu, "到期提醒")} right={<button className="chip" onClick={() => setTab("expiring")}>{t("查看全部")}</button>}>
          {expiringRows.length
            ? <div className="col g8">{expiringRows.map((record, index) => <button key={recordId(record) || index} onClick={() => openDetail(record)} style={{ ...card, padding: 11, cursor: "pointer" }}><div className="row spread g8"><span style={{ fontSize: 12.5, fontWeight: 680 }}>{recordTitle(record)}</span><T tone="warn">{shortDate(expiresOf(record))}</T></div><div className="muted" style={{ fontSize: 10.5, marginTop: 5 }}>{recordNo(record)} · {t(first(record.category_name_snapshot, record.category_name, categoryName(meta, categoryOfRecord(record))))}</div></button>)}</div>
            : <Empty icon="clock" title={t("暫無到期提醒")}/>}
        </Band>
      </div>
    </div>}

        {tab === "all" && <div>{filterBar}<RecordTable rows={rows} meta={meta} loading={loading || listLoading} onOpen={openDetail} biu={biu}/>{listFooter}</div>}

        {tab === "categories" && <div>
      <div className="row spread" style={{ marginBottom: 14 }}><div><L red>{recordText(biu, "分類庫")}</L><div className="muted" style={{ fontSize: 11.5, marginTop: 5 }}>{t("選擇分類查看其中的檔案與類型。")}</div></div><span className="num" style={{ fontSize: 12, fontWeight: 720 }}>{categoryCount}</span></div>
      <CategoryCards meta={meta} summary={totals} selected={category} onSelect={chooseCategory}/>
    </div>}

        {tab === "expiring" && <div>{filterBar}<div className="row g8" style={{ marginBottom: 12 }}><T tone="warn" dot>{t("即將到期與已到期")}</T><span className="muted" style={{ fontSize: 11.5 }}>{t("結果由後端保管期限規則計算。")}</span></div><RecordTable rows={rows} meta={meta} loading={loading || listLoading} onOpen={openDetail} biu={biu}/>{listFooter}</div>}

        {tab === "types" && (loading && !Object.keys(object(meta)).length ? <Loading/> : <TypesPanel meta={meta} onChanged={refresh}/>)}
      </div>

      {selected && <DetailDrawer initial={selected} meta={meta} onClose={closeDetail} onChanged={changed} biu={biu}/>}
      {creating && <CreateDrawer meta={meta} initialTypeKey={typeKey} initialCategoryKey={category} onClose={() => setCreating(false)} onDone={directCreated} biu={biu}/>}
    </div>
  </>;
};

window.W2.PAGES.cases = RecordsPage;
})();
