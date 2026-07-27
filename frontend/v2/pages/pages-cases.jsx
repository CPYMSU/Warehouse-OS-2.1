/* WAREHOUSE 2.0 · 通用事務管理中心
   行業類型 + 公司自訂表單 + SLA + 行級授權 + 不可變時間線。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "事務": "Cases", "事務管理": "Case management", "跨行業記錄 · 分派 · SLA · 根因與趨勢分析": "Cross-industry records · assignment · SLA · root-cause and trend analysis",
  "事務台賬": "Case ledger", "處置看板": "Work board", "分析": "Analytics", "類型設定": "Type settings",
  "新建事務": "New case", "搜尋編號、標題或內容": "Search number, title or content", "全部狀態": "All statuses", "全部類型": "All types", "全部級別": "All severities", "只看我的": "Mine only",
  "未結事務": "Open cases", "逾期": "Overdue", "已完成": "Completed", "總記錄": "All records",
  "編號": "Number", "標題": "Title", "類型": "Type", "級別": "Severity", "狀態": "Status", "責任部門": "Owning department", "受理人": "Assignee", "SLA": "SLA", "更新": "Updated",
  "尚無事務記錄": "No cases yet", "選擇行業預設類型或建立公司自訂類型，即可開始記錄。": "Choose an industry preset or create a company type to begin.",
  "請先選擇事務類型": "Choose a case type first", "事務類型": "Case type", "嚴重程度": "Severity", "發生時間": "Occurred at", "位置": "Location", "描述": "Description", "提交並啟動 SLA": "Submit and start SLA", "提交中…": "Submitting…",
  "必填": "Required", "一般": "Medium", "緊急": "High", "重大": "Critical", "低": "Low",
  "已提交": "Submitted", "已分流": "Triaged", "已指派": "Assigned", "處理中": "In progress", "等待外部": "Waiting", "待覆核": "Pending review", "已解決": "Resolved", "已結案": "Closed", "已取消": "Cancelled", "草稿": "Draft",
  "響應時限": "Response due", "解決時限": "Resolution due", "已響應": "Responded", "已超時": "Breached", "剩餘": "Remaining", "按時完成": "Completed on time", "逾期完成": "Completed late",
  "基本資料": "Core details", "類型欄位": "Type fields", "處置動作": "Actions", "完整時間線": "Timeline", "參與人": "Participants", "關聯": "Links", "附件": "Attachments",
  "處置說明 / 留言": "Action note / comment", "執行": "Run", "留言": "Comment", "解決摘要": "Resolution summary", "根因": "Root cause", "改善措施": "Corrective action", "滿意度": "Satisfaction",
  "提交": "Submit", "分流受理": "Triage", "指派": "Assign", "開始處理": "Start work", "恢復處理": "Resume", "提交覆核": "Send for review", "解決": "Resolve", "結案": "Close", "重開": "Reopen", "取消": "Cancel", "建立": "Created",
  "動作完成": "Action completed", "操作失敗": "Action failed", "載入失敗": "Load failed", "建立失敗": "Create failed",
  "平均首次響應": "Avg. first response", "平均解決時間": "Avg. resolution", "SLA 達標率": "SLA hit rate", "平均滿意度": "Avg. satisfaction", "分鐘": "min", "小時": "hours",
  "狀態分佈": "Status mix", "類型排行": "Top types", "部門負荷": "Department load", "近 30 日新增 / 解決": "30-day created / resolved", "新增": "Created", "解決": "Resolved",
  "公司可自訂類型": "Company-defined types", "行業預設只作起點；修改後會轉為公司版本，後續模板升級不會覆蓋。": "Industry presets are a starting point. Once edited, a company-owned revision is preserved from future template updates.",
  "新增自訂類型": "New custom type", "編輯": "Edit", "啟用": "Active", "停用": "Inactive", "行業預設": "Industry preset", "公司自訂": "Company custom",
  "類型名稱": "Type name", "類型代碼": "Type key", "類別": "Category", "說明": "Description", "預設部門": "Default department", "保密級別": "Confidentiality", "內部": "Internal", "敏感": "Sensitive", "受限": "Restricted",
  "協作部門": "Collaborating departments", "按住 Ctrl / Command 可多選": "Hold Ctrl / Command to select multiple", "分析指標": "Analytics metrics", "等待外部時暫停 SLA": "Pause SLA while waiting externally",
  "動態欄位": "Dynamic fields", "新增欄位": "Add field", "欄位名稱": "Field label", "欄位代碼": "Field key", "欄位類型": "Field type", "選項（逗號分隔）": "Options (comma separated)", "敏感欄位": "Sensitive field", "刪除": "Remove",
  "可見範圍": "Audience", "事務可見人員": "Case viewers", "事務參與人": "Case participants", "責任部門": "Owning department", "管理人員": "Managers",
  "SLA（分鐘，屬公司目標而非法定期限）": "SLA (minutes; company targets, not statutory deadlines)", "首次響應": "First response", "完成解決": "Resolution", "自然時間": "Elapsed time", "工作時間": "Business time", "保存版本": "Save revision", "保存中…": "Saving…", "保存失敗": "Save failed",
  "沒有權限查看分析": "Analytics permission is not available", "沒有權限配置類型": "Type configuration permission is not available", "分析載入失敗": "Analytics failed to load", "重試": "Retry",
  "刷新": "Refresh", "全部妥當": "On track", "資料已按本人、參與人與管理部門範圍裁剪。": "Data is scoped to the reporter, participants and managed departments.",
  "選擇附件": "Choose files", "上傳附件": "Upload files", "附件上傳中…": "Uploading files…", "附件上傳失敗": "Attachment upload failed", "附件下載失敗": "Attachment download failed", "尚無附件": "No files yet", "待上傳": "Ready to upload", "新增附件": "File added", "單個附件最大 15MB": "15 MB maximum per file", "事務已建立；再次提交會續傳附件，不會重複建立。": "The case was created. Submit again to resume uploads without creating a duplicate.",
  "行業指標": "Industry metrics", "根因排行": "Top root causes", "處置活動": "Case activity", "涉及事務": "Cases represented", "轉派": "Transfers",
  "案件程序": "Case procedure", "案件階段 · 承辦分派 · 程序期限 · 爭點與進度分析": "Case stages · assignment · procedural deadlines · issues and progress",
  "案件清單": "Case list", "程序看板": "Procedure board", "程序分析": "Procedure analytics", "流程模板": "Workflow templates",
  "新建案件階段": "New case stage", "進行中案件": "Active cases", "案件總數": "Total cases", "全部優先級": "All priorities",
  "程序優先級": "Procedural priority", "承辦機構": "Responsible institution", "承辦人": "Case owner", "程序期限": "Procedural deadline",
  "案件階段類型": "Case-stage type", "提交並啟動程序期限": "Submit and start procedural deadline",
  "程序進行中": "Procedure in progress", "等待材料": "Awaiting materials", "待評議": "Pending deliberation", "結論已形成": "Conclusion recorded", "程序已完成": "Procedure completed",
  "程序動作": "Procedural actions", "程序時間線": "Procedural timeline", "程序說明 / 留言": "Procedure note / comment",
  "結論摘要": "Conclusion summary", "核心爭點": "Core issue", "後續建議": "Follow-up recommendation", "學術回饋": "Academic feedback",
  "受理分流": "Intake triage", "開始程序": "Start procedure", "恢復程序": "Resume procedure", "提交評議": "Submit for deliberation",
  "形成結論": "Record conclusion", "完成程序": "Complete procedure", "重啟程序": "Restart procedure",
  "平均程序時長": "Average procedure time", "程序期限達標率": "Procedural deadline compliance", "機構負荷": "Institution workload",
  "近 30 日新增 / 形成結論": "30-day created / conclusions", "核心爭點排行": "Top core issues", "程序活動": "Procedural activity", "涉及案件": "Cases represented",
  "待受理 / 指派": "Pending intake / assignment", "等待材料 / 評議": "Materials / deliberation", "結論 / 完成": "Conclusion / completed",
  "程序期限（分鐘，屬 BIU 內部學術目標而非法定期限）": "Procedural deadline (minutes; an internal BIU academic target, not a statutory deadline)",
  "等待材料時暫停程序期限": "Pause the procedural deadline while awaiting materials",
  "尚無案件記錄": "No cases yet", "選擇案件階段類型或建立流程模板，即可開始記錄。": "Choose a case-stage type or create a workflow template to begin.",
  "首次程序回應期限": "Initial procedure response deadline",
  "程序完成期限": "Procedure completion deadline",
  "可自訂流程模板": "Customisable workflow templates",
  "BIU 預設提供流程起點；修改後保留為 BIU 自訂版本，後續模板升級不會覆蓋。": "BIU presets provide a workflow starting point. Edited revisions remain BIU custom versions and are not overwritten by later template upgrades.",
  "新增流程模板": "New workflow template",
  "BIU 預設": "BIU preset",
  "BIU 自訂": "BIU custom",
  "程序指標": "Procedure metrics",
  "資料已按本人、參與人與承辦機構範圍裁剪。": "Data is scoped to the reporter, participants, and responsible institutions.",
});

const { useState: S, useEffect: E, useRef: R } = React;
const { Icon: I, Btn: B, Tag: T, Label: L, Empty: Empty, Kpi, Meter, StackBar, Folio, Band, pad2 } = W2;

const STATUS = {
  draft: "草稿", submitted: "已提交", triaged: "已分流", assigned: "已指派",
  in_progress: "處理中", waiting_external: "等待外部", pending_review: "待覆核",
  resolved: "已解決", closed: "已結案", cancelled: "已取消",
};
const SEVERITY = { critical: "重大", high: "緊急", medium: "一般", low: "低" };
const METRIC_LABELS = {
  first_response:"首次響應", resolution_time:"解決時間", sla_hit:"SLA 達標",
  backlog:"未結積壓", aging:"積壓時長", reopen:"重開", transfer:"轉派",
  recurrence:"重複根因", cost:"成本", satisfaction:"滿意度", downtime:"停機時長",
  affected_count:"受影響數", customer_minutes:"客戶中斷分鐘", loss_value:"損失金額",
  compensation:"補償金額", rectification_overdue:"逾期整改",
};
const AUDIENCE = { case: "事務可見人員", case_participants: "事務參與人", owner_department: "責任部門", managers: "管理人員" };
const ACTION = {
  submit: "提交", triage: "分流受理", assign: "指派", start: "開始處理",
  wait: "等待外部", resume: "恢復處理", review: "提交覆核", resolve: "解決",
  close: "結案", reopen: "重開", cancel: "取消", comment: "留言", attachment_added: "新增附件",
};
const BIU_COPY = Object.freeze({
  "事務管理": "案件程序", "跨行業記錄 · 分派 · SLA · 根因與趨勢分析": "案件階段 · 承辦分派 · 程序期限 · 爭點與進度分析",
  "事務台賬": "案件清單", "處置看板": "程序看板", "分析": "程序分析", "類型設定": "流程模板",
  "新建事務": "新建案件階段", "未結事務": "進行中案件", "總記錄": "案件總數", "全部級別": "全部優先級",
  "級別": "程序優先級", "嚴重程度": "程序優先級", "責任部門": "承辦機構", "受理人": "承辦人", "SLA": "程序期限",
  "事務類型": "案件階段類型", "提交並啟動 SLA": "提交並啟動程序期限",
  "處理中": "程序進行中", "等待外部": "等待材料", "待覆核": "待評議", "已解決": "結論已形成", "已結案": "程序已完成",
  "處置動作": "程序動作", "完整時間線": "程序時間線", "處置說明 / 留言": "程序說明 / 留言",
  "解決摘要": "結論摘要", "根因": "核心爭點", "改善措施": "後續建議", "滿意度": "學術回饋",
  "分流受理": "受理分流", "開始處理": "開始程序", "恢復處理": "恢復程序", "提交覆核": "提交評議",
  "解決": "形成結論", "結案": "完成程序", "重開": "重啟程序",
  "平均解決時間": "平均程序時長", "SLA 達標率": "程序期限達標率", "部門負荷": "機構負荷",
  "近 30 日新增 / 解決": "近 30 日新增 / 形成結論", "根因排行": "核心爭點排行", "處置活動": "程序活動", "涉及事務": "涉及案件",
  "SLA（分鐘，屬公司目標而非法定期限）": "程序期限（分鐘，屬 BIU 內部學術目標而非法定期限）",
  "等待外部時暫停 SLA": "等待材料時暫停程序期限",
  "尚無事務記錄": "尚無案件記錄", "選擇行業預設類型或建立公司自訂類型，即可開始記錄。": "選擇案件階段類型或建立流程模板，即可開始記錄。",
  "已完成": "程序已完成", "響應時限": "首次程序回應期限", "解決時限": "程序完成期限",
  "執行": "提交", "公司可自訂類型": "可自訂流程模板",
  "行業預設只作起點；修改後會轉為公司版本，後續模板升級不會覆蓋。": "BIU 預設提供流程起點；修改後保留為 BIU 自訂版本，後續模板升級不會覆蓋。",
  "新增自訂類型": "新增流程模板", "行業預設": "BIU 預設", "公司自訂": "BIU 自訂",
  "行業指標": "程序指標",
  "資料已按本人、參與人與管理部門範圍裁剪。": "資料已按本人、參與人與承辦機構範圍裁剪。",
});
const caseText = (biu, key) => t(biu ? (BIU_COPY[key] || key) : key);
const statusText = (biu, status) => caseText(biu, STATUS[status] || status);
const actionText = (biu, action) => caseText(biu, ACTION[action] || action);
const EVENT_METRIC_LABEL = { assign: "指派", reopen: "重開", transfer: "轉派" };
const statusTone = s => s === "closed" || s === "resolved" ? "ok" : s === "cancelled" ? "plain" : s === "waiting_external" || s === "pending_review" ? "warn" : "plain";
const severityTone = s => s === "critical" ? "redinv" : s === "high" ? "bad" : s === "medium" ? "warn" : "plain";
const utcDate = value => {
  if (!value) return null;
  let raw = String(value).trim();
  if (!raw) return null;
  raw = raw.replace(" ", "T");
  if (!/(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw)) raw += "Z";
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
};
const dt = value => {
  const d = utcDate(value);
  if (!d) return "—";
  const p = n => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};
const localToUtc = value => {
  if (!value) return undefined;
  const parsed = new Date(String(value));
  return Number.isNaN(parsed.getTime()) ? value : parsed.toISOString();
};
const duration = mins => mins == null ? "—" : Number(mins) >= 120 ? (Number(mins) / 60).toFixed(1) + " " + t("小時") : Math.round(Number(mins)) + " " + t("分鐘");
const agoDue = (value, reference) => {
  const due = utcDate(value);
  if (!due) return "—";
  const ref = utcDate(reference);
  const ms = due.getTime() - (ref ? ref.getTime() : Date.now());
  const m = Math.round(Math.abs(ms) / 60000);
  return ms < 0 ? t("已超時") + " " + duration(m) : t("剩餘") + " " + duration(m);
};
const slaState = (item, biu = false) => {
  if (!item || item.status === "cancelled") return { text: caseText(biu, item && item.status === "cancelled" ? "已取消" : "—"), breached: false };
  const due = utcDate(item.resolution_due_at);
  if (["resolved", "closed"].includes(item.status)) {
    const finished = utcDate(item.resolved_at || item.closed_at);
    if (!due || !finished) return { text: caseText(biu, "已完成"), breached: false };
    const breached = !!(due && finished && finished.getTime() > due.getTime());
    return { text: t(breached ? "逾期完成" : "按時完成"), breached };
  }
  return { text: agoDue(item.resolution_due_at, item.sla_pause_started_at), breached: !!item.overdue };
};
const pct = v => v == null ? "—" : Number(v).toFixed(1) + "%";
const safeNum = v => Number.isFinite(Number(v)) ? Number(v) : 0;
const fileSize = value => {
  const bytes = safeNum(value);
  if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + " MB";
  if (bytes >= 1024) return Math.round(bytes / 1024) + " KB";
  return bytes + " B";
};
const newIdempotencyKey = () => {
  try { if (crypto && crypto.randomUUID) return "web-" + crypto.randomUUID(); } catch (e) {}
  return "web-" + Date.now() + "-" + Math.random().toString(36).slice(2);
};
const responseError = async (res, fallback) => {
  const data = await res.json().catch(() => ({}));
  throw new Error(data.error || data.message || fallback || res.statusText);
};
const uploadCaseFile = async (caseId, fieldKey, file) => {
  const form = new FormData();
  form.append("field_key", fieldKey);
  form.append("file", file, file.name);
  const res = await W2.fetch(`/api/cases/${caseId}/attachments`, { method: "POST", body: form });
  if (!res.ok) return responseError(res, t("附件上傳失敗"));
  return res.json();
};
const downloadCaseFile = async (caseId, attachment) => {
  const res = await W2.fetch(`/api/cases/${caseId}/attachments/${attachment.id}`);
  if (!res.ok) return responseError(res, t("附件下載失敗"));
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url; anchor.download = attachment.file_name || "attachment";
  document.body.appendChild(anchor); anchor.click(); anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

const FieldLabel = ({ field }) => (
  <div className="row g6" style={{ marginBottom: 5 }}>
    <L dim>{t(field.label || field.key)}</L>
    {field.required && <span style={{ color: "var(--red)", fontSize: 10 }}>{t("必填")}</span>}
    {field.sensitive && <T tone="warn">{t("敏感")}</T>}
  </div>
);

const DynamicField = ({ field, value, onChange }) => {
  const kind = field.type || "text";
  if (kind === "file") {
    const files = Array.isArray(value) ? value : [];
    return (
      <div>
        <FieldLabel field={field}/>
        <label className="case-file-picker">
          <I name="plus" size={13}/><span>{t("選擇附件")}</span>
          <input type="file" multiple onChange={e => onChange(Array.from(e.target.files || []))}/>
        </label>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 5 }}>{t("單個附件最大 15MB")}</div>
        {!!files.length && <div className="case-file-queue">{files.map((file, i) => <span key={file.name + i}>{file.name} · {fileSize(file.size)} · {t("待上傳")}</span>)}</div>}
      </div>
    );
  }
  if (kind === "boolean") return (
    <label className="row g8" style={{ minHeight: 42, borderBottom: "1px solid var(--hair)", cursor: "pointer" }}>
      <input type="checkbox" checked={!!value} onChange={e => onChange(e.target.checked)}/>
      <span style={{ fontSize: 13.5 }}>{t(field.label || field.key)}</span>
      {field.required && <span style={{ color: "var(--red)" }}>*</span>}
    </label>
  );
  const select = kind === "enum" || kind === "multienum";
  return (
    <div>
      <FieldLabel field={field}/>
      {select ? (
        <select className="field boxed" multiple={kind === "multienum"}
          value={kind === "multienum" ? (value || []) : (value || "")}
          onChange={e => onChange(kind === "multienum" ? Array.from(e.target.selectedOptions).map(o => o.value) : e.target.value)}>
          {kind === "enum" && <option value="">—</option>}
          {(field.options || []).map(o => <option key={o.value} value={o.value}>{t(o.label || o.value)}</option>)}
        </select>
      ) : kind === "textarea" ? (
        <textarea className="field boxed" style={{ height: 88, paddingTop: 10, resize: "vertical" }} value={value || ""} onChange={e => onChange(e.target.value)} placeholder={field.help || ""}/>
      ) : kind === "department" ? (
        <input className="field boxed" value={value || ""} onChange={e => onChange(e.target.value)} placeholder={field.help || ""}/>
      ) : (
        <input className="field boxed"
          type={kind === "number" ? "number" : kind === "date" ? "date" : kind === "datetime" ? "datetime-local" : "text"}
          value={value == null ? "" : value} onChange={e => onChange(kind === "number" && e.target.value !== "" ? Number(e.target.value) : e.target.value)}
          placeholder={field.help || ""}/>
      )}
    </div>
  );
};

const CreateDrawer = ({ meta, onClose, onDone, biu = false }) => {
  const types = ((meta && meta.types) || []).filter(x => x.active !== false);
  const [typeId, setTypeId] = S(types[0] ? String(types[0].id) : "");
  const [title, setTitle] = S("");
  const [description, setDescription] = S("");
  const [severity, setSeverity] = S(types[0] ? types[0].default_severity : "medium");
  const [occurredAt, setOccurredAt] = S("");
  const [location, setLocation] = S("");
  const [fields, setFields] = S({});
  const [idempotencyKey] = S(newIdempotencyKey);
  const [busy, setBusy] = S(false);
  const [err, setErr] = S("");
  const type = types.find(x => String(x.id) === typeId) || null;
  const selectType = id => {
    const next = types.find(x => String(x.id) === id);
    setTypeId(id); setSeverity(next ? next.default_severity : "medium"); setFields({}); setErr("");
  };
  const submit = async () => {
    if (!type || !title.trim()) { setErr(!type ? caseText(biu, "請先選擇事務類型") : t("請填寫標題")); return; }
    setBusy(true); setErr("");
    let caseCreated = false;
    try {
      const dynamic = {};
      for (const field of (type.fields || [])) {
        if (field.type === "file") continue;
        const value = fields[field.key];
        dynamic[field.key] = field.type === "datetime" && value ? localToUtc(value) : value;
      }
      const data = await W2.post("/api/cases", {
        type_id: type.id, title: title.trim(), description: description.trim(), severity,
        occurred_at: localToUtc(occurredAt), location: location.trim(), fields: dynamic,
        idempotency_key: idempotencyKey,
      });
      caseCreated = true;
      let item = data.case;
      for (const field of (type.fields || []).filter(f => f.type === "file")) {
        for (const file of (fields[field.key] || [])) {
          const uploaded = await uploadCaseFile(item.id, field.key, file);
          item = uploaded.case;
        }
      }
      onDone(item);
    } catch (e) {
      const suffix = caseCreated ? " " + t("事務已建立；再次提交會續傳附件，不會重複建立。") : "";
      setErr((e.message || t("建立失敗")) + suffix);
    }
    finally { setBusy(false); }
  };
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread"><div><L red>NEW CASE</L><div style={{ fontSize: 19, fontWeight: 760, marginTop: 5 }}>{caseText(biu, "新建事務")}</div></div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 210px)", overflowY: "auto" }}>
        <div className="col g14">
          <div><L dim>{caseText(biu, "事務類型")}</L><select className="field boxed" value={typeId} onChange={e => selectType(e.target.value)}><option value="">—</option>{types.map(x => <option key={x.id} value={x.id}>{x.name} · {x.owner_unit_name || x.owner_unit_code}</option>)}</select></div>
          {type && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>{type.description}</div>}
          <div><L dim>{t("標題")}</L><input className="field boxed" value={title} onChange={e => setTitle(e.target.value)} maxLength="200"/></div>
          <div><L dim>{t("描述")}</L><textarea className="field boxed" style={{ height: 96, paddingTop: 10 }} value={description} onChange={e => setDescription(e.target.value)}/></div>
          <div className="case-form-grid">
            <div><L dim>{caseText(biu, "嚴重程度")}</L><select className="field boxed" value={severity} onChange={e => setSeverity(e.target.value)}>{Object.entries(SEVERITY).map(([k,v]) => <option key={k} value={k}>{t(v)}</option>)}</select></div>
            <div><L dim>{t("發生時間")}</L><input className="field boxed" type="datetime-local" value={occurredAt} onChange={e => setOccurredAt(e.target.value)}/></div>
          </div>
          <div><L dim>{t("位置")}</L><input className="field boxed" value={location} onChange={e => setLocation(e.target.value)}/></div>
          {!!(type && type.fields && type.fields.length) && <><div style={{ borderTop: "2px solid var(--rule)", paddingTop: 12 }}><L red>{t("類型欄位")}</L></div>{type.fields.map(f => <DynamicField key={f.key} field={f} value={fields[f.key]} onChange={v => setFields(old => ({...old, [f.key]: v}))}/>)}</>}
          {err && <div style={{ color: "var(--red)", fontSize: 12.5, lineHeight: 1.5 }}>{err}</div>}
          <B kind="primary" icon="plus" disabled={busy || !type} onClick={submit}>{busy ? t("提交中…") : caseText(biu, "提交並啟動 SLA")}</B>
          <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.55 }}>{caseText(biu, "SLA（分鐘，屬公司目標而非法定期限）")}</div>
        </div>
      </div>
    </div>
  );
};

const dynamicDisplay = (field, value) => {
  if (value == null || value === "") return "—";
  if (field.type === "datetime") return dt(value);
  if (field.type === "boolean") return value ? "✓" : "—";
  if (field.type === "enum" || field.type === "multienum") {
    const labels = new Map((field.options || []).map(option => [String(option.value), option.label || option.value]));
    const values = Array.isArray(value) ? value : [value];
    return values.map(item => t(labels.get(String(item)) || item)).join(", ");
  }
  return Array.isArray(value) ? value.join(", ") : String(value);
};

const DetailDrawer = ({ item, meta, onClose, onChanged, biu = false }) => {
  const [action, setAction] = S("");
  const [message, setMessage] = S("");
  const [assignee, setAssignee] = S(item.assignee_user_id ? String(item.assignee_user_id) : "");
  const [resolution, setResolution] = S(item.resolution_summary || "");
  const [rootCause, setRootCause] = S(item.root_cause || "");
  const [corrective, setCorrective] = S(item.corrective_action || "");
  const [rating, setRating] = S(item.satisfaction_rating || "");
  const [busy, setBusy] = S(false);
  const [uploading, setUploading] = S("");
  const [downloading, setDownloading] = S(0);
  const [err, setErr] = S("");
  E(() => { setAction(""); setMessage(""); setAssignee(item.assignee_user_id ? String(item.assignee_user_id) : ""); setResolution(item.resolution_summary || ""); setRootCause(item.root_cause || ""); setCorrective(item.corrective_action || ""); setRating(item.satisfaction_rating || ""); }, [item.id, item.lock_version]);
  const available = (item.capabilities && item.capabilities.available_actions) || [];
  const capabilities = item.capabilities || {};
  const typeConfig = item.type_config || {};
  const currentUser = window.W2_USER || {};
  const permissions = new Set(currentUser.permissions || []);
  const topRole = Math.max(0, ...((currentUser.roles || []).map(role => Number(role.level) || 0)));
  const companyWide = permissions.has("cases.all.manage") || topRole >= 10 || !!window.W2_IS_OWNER;
  const allowedUnitCodes = new Set([
    item.owner_unit_code_snapshot || typeConfig.owner_unit_code,
    ...(typeConfig.collaborator_unit_codes || []),
  ].filter(Boolean).map(String));
  const assignees = (meta.assignees || []).filter(user => {
    if (companyWide || Number(user.id) === Number(item.assignee_user_id)) return true;
    const unitCodes = Array.isArray(user.unit_codes) && user.unit_codes.length ? user.unit_codes : [user.unit_code];
    return unitCodes.some(code => allowedUnitCodes.has(String(code || "")));
  });
  const ended = ["closed", "cancelled"].includes(item.status);
  const canUpload = (
    Number(currentUser.id) === Number(item.reporter_user_id)
    || capabilities.can_process
    || capabilities.can_assign
  ) && (!ended || capabilities.can_close);
  const run = async () => {
    if (!action) return;
    setBusy(true); setErr("");
    try {
      const body = { action, lock_version: item.lock_version, message };
      if (action === "assign") body.assignee_user_id = Number(assignee);
      if (action === "resolve") { body.resolution_summary = resolution; body.root_cause = rootCause; body.corrective_action = corrective; }
      if (action === "close") { body.root_cause = rootCause; body.corrective_action = corrective; if (rating) body.satisfaction_rating = Number(rating); }
      const data = await W2.post(`/api/cases/${item.id}/actions`, body);
      onChanged(data.case);
      setMessage(""); setAction("");
    } catch (e) { setErr(e.message || t("操作失敗")); }
    finally { setBusy(false); }
  };
  const configFields = (item.type_config && item.type_config.fields) || [];
  const dataFields = configFields.filter(field => field.type !== "file");
  const fileFields = configFields.filter(field => field.type === "file");
  const uploadFiles = async (fieldKey, selected) => {
    const files = Array.from(selected || []);
    if (!files.length) return;
    setUploading(fieldKey); setErr("");
    let latest = item;
    try {
      for (const file of files) {
        const data = await uploadCaseFile(item.id, fieldKey, file);
        latest = data.case;
      }
      onChanged(latest);
    } catch (e) {
      if (latest !== item) onChanged(latest);
      setErr(e.message || t("附件上傳失敗"));
    } finally { setUploading(""); }
  };
  const download = async attachment => {
    setDownloading(attachment.id); setErr("");
    try { await downloadCaseFile(item.id, attachment); }
    catch (e) { setErr(e.message || t("附件下載失敗")); }
    finally { setDownloading(0); }
  };
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 8 }}><div className="row g6"><T tone={severityTone(item.severity)}>{t(SEVERITY[item.severity] || item.severity)}</T><T tone={statusTone(item.status)} dot>{statusText(biu, item.status)}</T>{item.overdue && <T tone="bad" dot>{t("逾期")}</T>}</div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div>
        <div className="num muted" style={{ fontSize: 11 }}>{item.case_no}</div>
        <div style={{ fontSize: 18, fontWeight: 760, lineHeight: 1.3, marginTop: 5 }}>{item.title}</div>
        <div className="muted" style={{ fontSize: 11.5, marginTop: 5 }}>{item.type_name_snapshot} · {item.owner_unit_name || item.owner_unit_code_snapshot}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 220px)", overflowY: "auto" }} className="col g18">
        <section><L red>{t("基本資料")}</L><div className="case-detail-grid">
          {[[t("報告人"), item.reporter_name], [caseText(biu, "受理人"), item.assignee_name || "—"], [t("發生時間"), dt(item.occurred_at)], [t("位置"), item.location_text || "—"], [caseText(biu, "響應時限"), dt(item.response_due_at)], [caseText(biu, "解決時限"), dt(item.resolution_due_at)]].map(([k,v]) => <div key={k} style={{ borderTop: "1px solid var(--hair)", paddingTop: 6 }}><L dim>{k}</L><div style={{ fontSize: 12.5, marginTop: 3 }}>{v}</div></div>)}
        </div>{item.description && <div style={{ marginTop: 12, fontSize: 12.5, whiteSpace: "pre-wrap", lineHeight: 1.65 }}>{item.description}</div>}</section>
        {!!dataFields.length && <section><L red>{t("類型欄位")}</L><div style={{ marginTop: 8, borderTop: "1px solid var(--rule)" }}>{dataFields.map(f => <div key={f.key} className="row spread g10" style={{ padding: "8px 0", borderBottom: "1px solid var(--hair-soft)", alignItems: "flex-start" }}><span className="muted" style={{ fontSize: 11.5 }}>{t(f.label)}</span><span style={{ fontSize: 12.5, textAlign: "right", maxWidth: "58%", whiteSpace: "pre-wrap" }}>{dynamicDisplay(f, (item.dynamic_data || {})[f.key])}</span></div>)}</div></section>}
        {!!fileFields.length && <section><L red>{t("附件")}</L><div className="col g10" style={{ marginTop: 8 }}>
          {fileFields.map(field => {
            const attached = (item.attachments || []).filter(file => file.field_key === field.key);
            return <div key={field.key} className="case-attachment-field"><div className="row spread g8"><div><span style={{ fontSize: 12.5, fontWeight: 650 }}>{t(field.label || field.key)}</span>{field.sensitive && <T tone="warn" style={{ marginLeft: 6 }}>{t("敏感")}</T>}</div>{canUpload && <label className={`btn sm ${uploading ? "disabled" : ""}`}><I name="plus" size={12}/>{uploading === field.key ? t("附件上傳中…") : t("上傳附件")}<input type="file" multiple disabled={!!uploading} onChange={e => { const files = Array.from(e.target.files || []); e.target.value = ""; uploadFiles(field.key, files); }}/></label>}</div>
              {!attached.length ? <div className="muted" style={{ fontSize: 10.5, marginTop: 7 }}>{t("尚無附件")}</div> : <div className="case-attachment-list">{attached.map(file => <button type="button" key={file.id} onClick={() => download(file)} disabled={!!downloading}><span className="case-attachment-name">{file.file_name}</span><span className="num muted">{downloading === file.id ? "…" : fileSize(file.file_size)}</span></button>)}</div>}
            </div>;
          })}
        </div></section>}
        {err && <div style={{ color: "var(--red)", fontSize: 12, lineHeight: 1.5 }}>{err}</div>}
        <section><L red>{caseText(biu, "處置動作")}</L><div className="row g6" style={{ flexWrap: "wrap", marginTop: 8 }}>{available.map(a => <button key={a} className={`chip ${action === a ? "on" : ""}`} onClick={() => { setAction(a); setErr(""); }}>{actionText(biu, a)}</button>)}</div>
          {action && <div className="col g10" style={{ marginTop: 12, padding: 12, background: "var(--paper-2)", borderTop: "1px solid var(--rule)" }}>
            {action === "assign" && <select className="field boxed" value={assignee} onChange={e => setAssignee(e.target.value)}><option value="">— {caseText(biu, "受理人")} —</option>{assignees.map(u => <option key={u.id} value={u.id}>{u.display_name} · {u.unit_name || "—"}</option>)}</select>}
            <textarea className="field boxed" style={{ height: 74, paddingTop: 9 }} value={message} onChange={e => setMessage(e.target.value)} placeholder={caseText(biu, "處置說明 / 留言")}/>
            {action === "resolve" && <><textarea className="field boxed" style={{ height: 74, paddingTop: 9 }} value={resolution} onChange={e => setResolution(e.target.value)} placeholder={caseText(biu, "解決摘要")}/><textarea className="field boxed" style={{ height: 64, paddingTop: 9 }} value={rootCause} onChange={e => setRootCause(e.target.value)} placeholder={caseText(biu, "根因")}/><textarea className="field boxed" style={{ height: 64, paddingTop: 9 }} value={corrective} onChange={e => setCorrective(e.target.value)} placeholder={caseText(biu, "改善措施")}/></>}
            {action === "close" && <><textarea className="field boxed" style={{ height: 64, paddingTop: 9 }} value={rootCause} onChange={e => setRootCause(e.target.value)} placeholder={caseText(biu, "根因")}/><textarea className="field boxed" style={{ height: 64, paddingTop: 9 }} value={corrective} onChange={e => setCorrective(e.target.value)} placeholder={caseText(biu, "改善措施")}/><select className="field boxed" value={rating} onChange={e => setRating(e.target.value)}><option value="">— {caseText(biu, "滿意度")} —</option>{[1,2,3,4,5].map(x => <option key={x} value={x}>{x} / 5</option>)}</select></>}
            <B kind="primary" disabled={busy || (action === "assign" && !assignee)} onClick={run}>{busy ? "…" : caseText(biu, "執行") + " · " + actionText(biu, action)}</B>
          </div>}
        </section>
        <section><L red>{caseText(biu, "完整時間線")}</L><div style={{ borderTop: "2px solid var(--rule)", marginTop: 8 }}>{(item.events || []).slice().reverse().map((e,i) => <div key={e.id} style={{ display: "grid", gridTemplateColumns: "24px 1fr", gap: 8, padding: "9px 0", borderBottom: "1px solid var(--hair-soft)" }}><span className="num muted" style={{ fontSize: 9 }}>{pad2((item.events || []).length - i)}</span><div><div className="row spread g8"><span style={{ fontSize: 12.5, fontWeight: 650 }}>{e.event_type === "created" ? t("建立") : actionText(biu, e.event_type)}</span><span className="num muted" style={{ fontSize: 9.5 }}>{dt(e.created_at)}</span></div><div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{e.actor_name || e.actor_kind}{e.from_status && e.to_status && ` · ${statusText(biu, e.from_status)} → ${statusText(biu, e.to_status)}`}</div>{e.message && <div style={{ fontSize: 12, lineHeight: 1.5, marginTop: 4, whiteSpace: "pre-wrap" }}>{e.message}</div>}</div></div>)}</div></section>
      </div>
    </div>
  );
};

const BarList = ({ rows, labelKey = "label", getLabel }) => {
  const max = Math.max(1, ...(rows || []).map(x => safeNum(x.count)));
  return <div className="col g10">{(rows || []).slice(0, 8).map((x,i) => <div key={(x[labelKey] || x.key || i)}><div className="row spread" style={{ fontSize: 12 }}><span>{getLabel ? getLabel(x) : t(x[labelKey] || x.key || "—")}</span><span className="num" style={{ fontWeight: 700 }}>{x.count}</span></div><div className="bar" style={{ marginTop: 5 }}><i style={{ width: safeNum(x.count) / max * 100 + "%", background: i === 0 ? "var(--red)" : "var(--ink)" }}/></div></div>)}</div>;
};

const Analytics = ({ data, error, loading, canAnalyze, onRetry, biu = false }) => {
  if (!canAnalyze) return <Empty icon="chart" title={t("沒有權限查看分析")}/>;
  if (!data && (loading || !error)) return <div className="muted" style={{ padding: 42, textAlign: "center" }}>LOADING…</div>;
  if (!data) return <Empty icon="alert" title={t("分析載入失敗")} sub={error || t("載入失敗")} action={<B icon="refresh" onClick={onRetry}>{t("重試")}</B>}/>;
  const z = data.totals || {};
  const created = (data.trend || []).map(x => safeNum(x.created));
  const resolved = (data.trend || []).map(x => safeNum(x.resolved));
  const max = Math.max(1, ...created, ...resolved);
  const industry = Array.isArray(data.industry_metrics) ? data.industry_metrics : [];
  const causes = Array.isArray(data.by_root_cause) ? data.by_root_cause : [];
  const events = Array.isArray(data.event_metrics)
    ? data.event_metrics.map(item => ({ label: item.label || EVENT_METRIC_LABEL[item.key] || item.key, count: safeNum(item.count != null ? item.count : item.value) }))
    : Object.entries(data.event_metrics || {}).map(([key, value]) => ({
        label: EVENT_METRIC_LABEL[key] || key,
        count: safeNum(value && typeof value === "object" ? (value.count != null ? value.count : value.value) : value),
      }));
  return <>
    {error && <div style={{ color: "var(--red)", fontSize: 11.5, padding: "10px 0" }}>{error} · <button onClick={onRetry} style={{ textDecoration: "underline" }}>{t("重試")}</button></div>}
    <div className="kpi-band case-kpi-grid"><Kpi label={caseText(biu, "未結事務")} value={z.open || 0}/><Kpi label={t("逾期")} value={z.overdue || 0} red={z.overdue > 0}/><Kpi label={t("平均首次響應")} value={duration(z.avg_response_minutes)}/><Kpi label={caseText(biu, "SLA 達標率")} value={pct(z.resolution_sla_hit_pct)}/></div>
    <div className="case-analytics-grid"><Band no="A" title={t("狀態分佈")}><BarList rows={data.by_status} labelKey="key" getLabel={row => statusText(biu, row.key)}/></Band><Band no="B" title={t("類型排行")}><BarList rows={data.by_type}/></Band></div>
    <div className="case-analytics-grid wide"><Band no="C" title={caseText(biu, "部門負荷")}><BarList rows={data.by_department}/></Band><Band no="D" title={caseText(biu, "近 30 日新增 / 解決")}><div style={{ height: 210, display: "flex", alignItems: "flex-end", gap: 3, borderBottom: "1px solid var(--rule)", paddingTop: 20 }}>{created.map((v,i) => <div key={i} title={`${(data.trend[i] || {}).day}: ${t("新增")} ${v} / ${caseText(biu, "解決")} ${resolved[i]}`} style={{ flex: 1, height: "100%", display: "flex", alignItems: "flex-end", gap: 1 }}><i style={{ display: "block", width: "50%", height: Math.max(v ? 3 : 0, v/max*100) + "%", background: "var(--ink)" }}/><i style={{ display: "block", width: "50%", height: Math.max(resolved[i] ? 3 : 0, resolved[i]/max*100) + "%", background: "var(--red)" }}/></div>)}</div><div className="row g16 muted" style={{ fontSize: 10.5, marginTop: 8 }}><span>■ {t("新增")}</span><span style={{ color: "var(--red)" }}>■ {caseText(biu, "解決")}</span></div></Band></div>
    {!!industry.length && <Band no="E" title={caseText(biu, "行業指標")}><div className="case-metric-grid">{industry.map((metric, index) => <div key={metric.key || index} className="case-metric"><L dim>{t(metric.label || metric.key)}</L><div className="num" style={{ fontSize: 26, fontWeight: 720, marginTop: 7 }}>{metric.value == null ? "—" : metric.value}{metric.unit && <span style={{ fontSize: 11, marginLeft: 4 }}>{t(metric.unit)}</span>}</div>{metric.cases_with_data != null && <div className="muted" style={{ fontSize: 10.5, marginTop: 5 }}>{caseText(biu, "涉及事務")} · {metric.cases_with_data}</div>}</div>)}</div></Band>}
    {(!!causes.length || !!events.length) && <div className="case-analytics-grid">{!!causes.length && <Band no="F" title={caseText(biu, "根因排行")}><BarList rows={causes} getLabel={row => t(row.label || row.root_cause || row.key || "—")}/></Band>}{!!events.length && <Band no="G" title={caseText(biu, "處置活動")}><BarList rows={events}/></Band>}</div>}
    <div className="muted" style={{ fontSize: 10.5, marginTop: 12 }}>{caseText(biu, "資料已按本人、參與人與管理部門範圍裁剪。")}</div>
  </>;
};

const TypeEditor = ({ current, meta, onClose, onSaved, biu = false }) => {
  const isNew = !current;
  const [form, setForm] = S(() => current ? JSON.parse(JSON.stringify(current)) : {
    key: "", name: "", category: "service", description: "", owner_unit_code: (meta.units.find(x => x.unit_type !== "company") || {}).unit_code || "",
    default_severity: "medium", confidentiality: "internal", active: true, pause_sla_on_waiting: true,
    sla: { clock_mode: "business", levels: { critical:{response_minutes:5,resolution_minutes:60}, high:{response_minutes:15,resolution_minutes:240}, medium:{response_minutes:60,resolution_minutes:480}, low:{response_minutes:240,resolution_minutes:1440} } },
    fields: [], metrics: ["first_response","resolution_time","sla_hit","backlog"],
  });
  const [busy, setBusy] = S(false), [err, setErr] = S("");
  const set = (k,v) => setForm(old => ({...old,[k]:v}));
  const setSla = (sev,k,v) => setForm(old => ({...old,sla:{...(old.sla||{}),levels:{...((old.sla||{}).levels||{}),[sev]:{...((((old.sla||{}).levels||{})[sev])||{}),[k]:Number(v)}}}}));
  const updateField = (i,k,v) => setForm(old => ({...old,fields:(old.fields||[]).map((f,n) => {
    if (n !== i) return f;
    const next = {...f,[k]:v};
    if (k === "type" && v === "file") next.required = false;
    if (k === "sensitive" && v && !next.audience) next.audience = "case_participants";
    return next;
  })}));
  const addField = () => setForm(old => ({...old,fields:[...(old.fields||[]),{key:"field_"+((old.fields||[]).length+1),label:"",type:"text",required:false,sensitive:false}]}));
  const save = async () => {
    setBusy(true); setErr("");
    try {
      const payload = JSON.parse(JSON.stringify(form));
      payload.fields = (payload.fields || []).map(f => {
        if (f.type === "file") f.required = false;
        if (f.sensitive && !f.audience) f.audience = "case_participants";
        if (!f.sensitive) delete f.audience;
        if (f.type === "enum" || f.type === "multienum") {
          const values = Array.isArray(f.options) ? f.options.map(o => typeof o === "object" ? o.value : o) : String(f.optionText || "").split(",");
          f.options = values.map(x => String(x).trim()).filter(Boolean).map(x => ({value:x,label:x}));
        } else delete f.options;
        delete f.optionText; return f;
      });
      const data = await W2.post(isNew ? "/api/cases/types" : `/api/cases/types/${current.id}`, payload);
      onSaved(data);
    } catch (e) { setErr(e.message || t("保存失敗")); }
    finally { setBusy(false); }
  };
  return <div className="drawer"><div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}><div className="row spread"><div><L red>CASE TYPE</L><div style={{ fontSize: 18, fontWeight: 750, marginTop: 4 }}>{isNew ? caseText(biu, "新增自訂類型") : t("編輯") + " · " + current.name}</div></div><button className="btn ghost sm" onClick={onClose}><I name="x" size={13}/></button></div></div><div className="col g13" style={{ padding:18,maxHeight:"calc(100vh - 210px)",overflowY:"auto" }}>
    <div className="case-editor-grid"><div><L dim>{t("類型名稱")}</L><input className="field boxed" value={form.name||""} onChange={e=>set("name",e.target.value)}/></div><div><L dim>{t("類型代碼")}</L><input className="field boxed" disabled={!isNew} value={form.key||""} onChange={e=>set("key",e.target.value.toLowerCase().replace(/[^a-z0-9_]/g,"_"))}/></div></div>
    <div><L dim>{t("說明")}</L><textarea className="field boxed" style={{height:70,paddingTop:9}} value={form.description||""} onChange={e=>set("description",e.target.value)}/></div>
    <div className="case-editor-grid"><div><L dim>{t("類別")}</L><input className="field boxed" value={form.category||""} onChange={e=>set("category",e.target.value)}/></div><div><L dim>{t("預設部門")}</L><select className="field boxed" value={form.owner_unit_code||""} onChange={e=>set("owner_unit_code",e.target.value)}>{meta.units.filter(x=>x.unit_type!=="company").map(x=><option key={x.id} value={x.unit_code}>{x.unit_name}</option>)}</select></div></div>
    <div><L dim>{t("協作部門")} · {t("按住 Ctrl / Command 可多選")}</L><select multiple className="field boxed" style={{height:92,paddingTop:7}} value={form.collaborator_unit_codes||[]} onChange={e=>set("collaborator_unit_codes",Array.from(e.target.selectedOptions).map(option=>option.value))}>{meta.units.filter(x=>x.unit_type!=="company"&&x.unit_code!==form.owner_unit_code).map(x=><option key={x.id} value={x.unit_code}>{x.unit_name}</option>)}</select></div>
    <div className="case-editor-grid"><div><L dim>{caseText(biu, "嚴重程度")}</L><select className="field boxed" value={form.default_severity||"medium"} onChange={e=>set("default_severity",e.target.value)}>{Object.entries(SEVERITY).map(([k,v])=><option key={k} value={k}>{t(v)}</option>)}</select></div><div><L dim>{t("保密級別")}</L><select className="field boxed" value={form.confidentiality||"internal"} onChange={e=>set("confidentiality",e.target.value)}><option value="internal">{t("內部")}</option><option value="sensitive">{t("敏感")}</option><option value="restricted">{t("受限")}</option></select></div></div>
    <div style={{borderTop:"2px solid var(--rule)",paddingTop:10}}><div className="row spread"><L red>{caseText(biu, "SLA（分鐘，屬公司目標而非法定期限）")}</L><select className="field boxed" style={{width:130}} value={(form.sla||{}).clock_mode||"business"} onChange={e=>setForm(old=>({...old,sla:{...(old.sla||{}),clock_mode:e.target.value}}))}><option value="business">{t("工作時間")}</option><option value="elapsed">{t("自然時間")}</option></select></div><div className="case-sla-grid"><span/><L dim>{t("首次響應")}</L><L dim>{t("完成解決")}</L>{["critical","high","medium","low"].map(sev=><React.Fragment key={sev}><span style={{fontSize:11.5}}>{t(SEVERITY[sev])}</span><input className="field boxed" type="number" value={((((form.sla||{}).levels||{})[sev]||{}).response_minutes)||0} onChange={e=>setSla(sev,"response_minutes",e.target.value)}/><input className="field boxed" type="number" value={((((form.sla||{}).levels||{})[sev]||{}).resolution_minutes)||0} onChange={e=>setSla(sev,"resolution_minutes",e.target.value)}/></React.Fragment>)}</div></div>
    <label className="row g8"><input type="checkbox" checked={form.pause_sla_on_waiting!==false} onChange={e=>set("pause_sla_on_waiting",e.target.checked)}/>{caseText(biu, "等待外部時暫停 SLA")}</label>
    <div style={{borderTop:"2px solid var(--rule)",paddingTop:10}}><L red>{t("分析指標")}</L><div className="case-metric-options">{Object.entries(METRIC_LABELS).map(([key,label])=><label key={key} className="row g6"><input type="checkbox" checked={(form.metrics||[]).includes(key)} onChange={e=>setForm(old=>({...old,metrics:e.target.checked?Array.from(new Set([...(old.metrics||[]),key])):(old.metrics||[]).filter(value=>value!==key)}))}/>{t(label)}</label>)}</div></div>
    <div style={{borderTop:"2px solid var(--rule)",paddingTop:10}}><div className="row spread"><L red>{t("動態欄位")}</L><B size="sm" icon="plus" onClick={addField}>{t("新增欄位")}</B></div><div className="col g10" style={{marginTop:9}}>{(form.fields||[]).map((f,i)=><div key={i} style={{border:"1px solid var(--hair)",padding:10}}><div className="case-editor-grid compact"><input className="field boxed" placeholder={t("欄位名稱")} value={f.label||""} onChange={e=>updateField(i,"label",e.target.value)}/><input className="field boxed" placeholder={t("欄位代碼")} value={f.key||""} onChange={e=>updateField(i,"key",e.target.value.toLowerCase().replace(/[^a-z0-9_]/g,"_"))}/><select className="field boxed" value={f.type||"text"} onChange={e=>updateField(i,"type",e.target.value)}>{["text","textarea","number","boolean","enum","multienum","date","datetime","user","department","location","asset","inventory_item","customer","file"].map(x=><option key={x} value={x}>{x}</option>)}</select><input className="field boxed" placeholder={t("選項（逗號分隔）")} disabled={!/enum/.test(f.type||"")} value={f.optionText != null ? f.optionText : (f.options||[]).map(o=>typeof o==="object"?o.value:o).join(",")} onChange={e=>updateField(i,"optionText",e.target.value)}/></div><div className="row g14" style={{marginTop:8,fontSize:11.5,flexWrap:"wrap"}}><label className="row g5"><input type="checkbox" disabled={f.type==="file"} checked={f.type==="file"?false:!!f.required} onChange={e=>updateField(i,"required",e.target.checked)}/>{t("必填")}</label><label className="row g5"><input type="checkbox" checked={!!f.sensitive} onChange={e=>updateField(i,"sensitive",e.target.checked)}/>{t("敏感欄位")}</label>{f.sensitive&&<label className="row g5"><span>{t("可見範圍")}</span><select className="field boxed case-audience" value={f.audience||"case_participants"} onChange={e=>updateField(i,"audience",e.target.value)}>{Object.entries(AUDIENCE).map(([key,label])=><option key={key} value={key}>{t(label)}</option>)}</select></label>}<button style={{marginLeft:"auto",color:"var(--red)"}} onClick={()=>setForm(old=>({...old,fields:old.fields.filter((_,n)=>n!==i)}))}>{t("刪除")}</button></div></div>)}</div></div>
    {!isNew && <label className="row g8"><input type="checkbox" checked={form.active !== false} onChange={e=>set("active",e.target.checked)}/>{t("啟用")}</label>}{err&&<div style={{color:"var(--red)",fontSize:12}}>{err}</div>}<B kind="primary" disabled={busy} onClick={save}>{busy?t("保存中…"):t("保存版本")}</B>
  </div></div>;
};

const TypesPanel = ({ meta, onMeta, biu = false }) => {
  const [editing,setEditing]=S(undefined);
  if (!(meta.permissions||{}).can_configure) return <Empty icon="gear" title={t("沒有權限配置類型")}/>;
  const saved = data => {
    onMeta(old => {
      const configured = data.config_types || data.types || old.config_types || old.types || [];
      const active = (data.types || configured).filter(item => item.active !== false);
      return {...old, ...data, types: active, config_types: configured};
    });
    setEditing(undefined);
  };
  return <div style={{display:"flex",gap:18,alignItems:"flex-start"}}><div style={{flex:1,minWidth:0}}><div className="row spread" style={{marginBottom:14}}><div><L red>{caseText(biu, "公司可自訂類型")}</L><div className="muted" style={{fontSize:11.5,marginTop:5,maxWidth:680}}>{caseText(biu, "行業預設只作起點；修改後會轉為公司版本，後續模板升級不會覆蓋。")}</div></div><B kind="primary" icon="plus" onClick={()=>setEditing(null)}>{caseText(biu, "新增自訂類型")}</B></div><div style={{display:"grid",gridTemplateColumns:"repeat(auto-fill,minmax(260px,1fr))",gap:12}}>{(meta.config_types||meta.types||[]).map(x=><button key={x.id} onClick={()=>setEditing(x)} style={{textAlign:"left",background:"var(--white)",border:"1px solid var(--hair)",padding:14}}><div className="row spread"><T tone={x.active?"ok":"plain"} dot>{x.active?t("啟用"):t("停用")}</T><span className="num muted" style={{fontSize:9}}>R{x.revision_no}</span></div><div style={{fontSize:15,fontWeight:720,marginTop:9}}>{x.name}</div><div className="muted" style={{fontSize:11.5,lineHeight:1.5,marginTop:5,minHeight:34}}>{x.description||"—"}</div><div className="row spread" style={{marginTop:10}}><span style={{fontSize:11}}>{x.owner_unit_name||x.owner_unit_code}</span><T tone="plain">{caseText(biu, x.managed_by_template?"行業預設":"公司自訂")}</T></div></button>)}</div></div>{editing !== undefined && <TypeEditor current={editing} meta={meta} biu={biu} onClose={()=>setEditing(undefined)} onSaved={saved}/>}</div>;
};

const Board = ({ cases, summary, onSelect, biu = false }) => {
  const groups = [
    ["draft", "submitted", "triaged", "assigned"], ["in_progress"],
    ["waiting_external", "pending_review"], ["resolved", "closed", "cancelled"],
  ];
  const names = biu ? ["待受理 / 指派", "程序進行中", "等待材料 / 評議", "結論 / 完成"] : ["待受理 / 指派", "處理中", "等待 / 覆核", "已解決 / 結案"];
  const byStatus = (summary && summary.by_status) || {};
  return <div className="case-board">{groups.map((statuses,i)=>{
    const list=cases.filter(x=>statuses.includes(x.status));
    const count=statuses.reduce((sum,key)=>sum+safeNum(byStatus[key]),0) || list.length;
    return <div key={i} className="case-board-column" style={{borderTopColor:i===2?"var(--red)":"var(--rule)"}}><div className="row spread" style={{marginBottom:10}}><L>{t(names[i])}</L><span className="num" style={{fontSize:12,fontWeight:700}}>{count}</span></div><div className="col g8">{list.map(x=><button key={x.id} onClick={()=>onSelect(x.id)} className="case-board-card"><div className="row spread"><span className="num muted" style={{fontSize:9}}>{x.case_no}</span>{x.overdue&&<span style={{width:6,height:6,borderRadius:"50%",background:"var(--red)"}}/>}</div><div style={{fontSize:12.5,fontWeight:680,lineHeight:1.35,marginTop:5}}>{x.title}</div><div className="muted" style={{fontSize:10.5,marginTop:6}}>{x.type_name_snapshot} · {x.assignee_name||x.owner_unit_name||"—"}</div></button>)}</div></div>;
  })}</div>;
};

const EMPTY_SUMMARY = { total: 0, open: 0, completed: 0, overdue: 0, by_status: {} };
const Page = ({ initialCaseId = null, onInitialCaseOpened = null, templateKey = "" } = {}) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const [tab,setTab]=S("ledger"), [meta,setMeta]=S(null), [rows,setRows]=S([]), [total,setTotal]=S(0), [summary,setSummary]=S(EMPTY_SUMMARY), [analytics,setAnalytics]=S(null);
  const [q,setQ]=S(""), [status,setStatus]=S(""), [typeKey,setTypeKey]=S(""), [severity,setSeverity]=S(""), [mine,setMine]=S(false);
  const [loading,setLoading]=S(true), [err,setErr]=S(""), [create,setCreate]=S(false), [selected,setSelected]=S(null);
  const [analyticsLoading,setAnalyticsLoading]=S(false), [analyticsError,setAnalyticsError]=S("");
  const listSequence=R(0);
  const detailSequence=R(0);
  const initialCaseOpened=R(null);
  const loadMeta = async () => { const m=await W2.json("/api/cases/meta"); setMeta(m); return m; };
  const loadList = async () => {
    const request=++listSequence.current;
    const filters={limit:200};
    if(q.trim())filters.q=q.trim(); if(status)filters.status=status; if(typeKey)filters.type_key=typeKey;
    if(severity)filters.severity=severity; if(mine)filters.mine=true;
    const d=await W2.post("/api/cases/search",filters);
    if(request!==listSequence.current)return d;
    setRows(d.cases||[]); setTotal(d.total==null?0:d.total); setSummary(d.summary||{...EMPTY_SUMMARY,total:d.total||0});
    return d;
  };
  const loadAnalytics = async m => {
    const context=m||meta||{};
    if(!context.permissions?.can_analyze){setAnalytics(null);setAnalyticsError("");return;}
    setAnalyticsLoading(true);setAnalyticsError("");
    try{setAnalytics(await W2.json("/api/cases/analytics"));}
    catch(e){setAnalyticsError(e.message||t("分析載入失敗"));}
    finally{setAnalyticsLoading(false);}
  };
  const refresh = async () => {setLoading(true);setErr("");try{const m=meta||await loadMeta();await loadList();if(tab==="analytics")await loadAnalytics(m);}catch(e){setErr(e.message||t("載入失敗"));}finally{setLoading(false);}};
  E(()=>{refresh();},[]);
  E(()=>()=>{detailSequence.current+=1;},[]);
  E(()=>{if(!meta)return;const timer=setTimeout(()=>loadList().catch(e=>setErr(e.message||t("載入失敗"))),220);return()=>clearTimeout(timer);},[q,status,typeKey,severity,mine]);
  E(()=>{if(tab==="analytics"&&meta)loadAnalytics(meta);},[tab,meta]);
  const openDetail = async id => {
    const request=++detailSequence.current;
    setErr("");
    try{
      const d=await W2.json(`/api/cases/${id}`);
      if(request===detailSequence.current)setSelected(d.case);
    }catch(e){
      if(request===detailSequence.current)setErr(e.message||t("載入失敗"));
    }
  };
  E(()=>{
    if(initialCaseId==null||initialCaseId===""){initialCaseOpened.current=null;return;}
    const initialKey=String(initialCaseId);
    if(initialCaseOpened.current===initialKey)return;
    initialCaseOpened.current=initialKey;
    setTab("ledger");
    openDetail(initialCaseId).finally(() => {
      if(typeof onInitialCaseOpened==="function")onInitialCaseOpened(initialCaseId);
    });
  },[initialCaseId]);
  const closeDetail = () => {detailSequence.current+=1;setSelected(null);};
  const reloadAfterChange = () => {loadList().catch(e=>setErr(e.message||t("載入失敗")));if(tab==="analytics"||analytics)loadAnalytics(meta);};
  const changed = item => {setSelected(item);reloadAfterChange();};
  const created = item => {setCreate(false);setSelected(item);reloadAfterChange();};
  const counts={open:safeNum(summary.open),overdue:safeNum(summary.overdue),done:safeNum(summary.completed)};
  const tabs=[["ledger","01","事務台賬"],["board","02","處置看板"],["analytics","03","分析"],["types","04","類型設定"]];
  return <><Folio no="17" en="CASES" title={caseText(biu, "事務管理")} sub={caseText(biu, "跨行業記錄 · 分派 · SLA · 根因與趨勢分析")}/><div className="subnav" style={{marginBottom:18}}>{tabs.filter(x=>x[0]!=="types"||(meta&&meta.permissions?.can_configure)).map(([id,no,label])=><button key={id} className={tab===id?"on":""} onClick={()=>setTab(id)}><span className="sn-no">{no}</span>{caseText(biu, label)}{id==="ledger"&&<span className="sn-count">{total}</span>}</button>)}</div>
    {err&&<div style={{color:"var(--red)",fontSize:12.5,marginBottom:12}}>{err}</div>}
    {tab==="ledger"&&<div style={{display:"flex",gap:18,alignItems:"flex-start"}}><div style={{flex:1,minWidth:0}}><div className="kpi-band case-kpi-grid"><Kpi label={caseText(biu, "未結事務")} value={counts.open}/><Kpi label={t("逾期")} value={counts.overdue} red={counts.overdue>0}/><Kpi label={caseText(biu, "已完成")} value={counts.done}/><Kpi label={caseText(biu, "總記錄")} value={safeNum(summary.total)}/></div><div className="row g8" style={{margin:"16px 0",flexWrap:"wrap"}}><div style={{position:"relative",flex:"1 1 230px"}}><input className="field boxed" value={q} onChange={e=>setQ(e.target.value)} placeholder={t("搜尋編號、標題或內容")}/></div><select className="field boxed" style={{width:135}} value={status} onChange={e=>setStatus(e.target.value)}><option value="">{t("全部狀態")}</option>{Object.entries(STATUS).map(([k])=><option key={k} value={k}>{statusText(biu, k)}</option>)}</select><select className="field boxed" style={{width:165}} value={typeKey} onChange={e=>setTypeKey(e.target.value)}><option value="">{t("全部類型")}</option>{(meta?.types||[]).map(x=><option key={x.id} value={x.key}>{x.name}</option>)}</select><select className="field boxed" style={{width:125}} value={severity} onChange={e=>setSeverity(e.target.value)}><option value="">{caseText(biu, "全部級別")}</option>{Object.entries(SEVERITY).map(([k,v])=><option key={k} value={k}>{t(v)}</option>)}</select><button className={`chip ${mine?"on":""}`} onClick={()=>setMine(!mine)}>{t("只看我的")}</button><B size="sm" icon="refresh" onClick={refresh}>{t("刷新")}</B>{meta?.permissions?.can_create&&<B kind="primary" size="sm" icon="plus" onClick={()=>setCreate(true)}>{caseText(biu, "新建事務")}</B>}</div>
      {loading&&!rows.length?<div className="muted" style={{padding:40,textAlign:"center"}}>LOADING…</div>:rows.length?<div style={{overflowX:"auto",borderTop:"2px solid var(--rule)"}}><table className="tbl2"><thead><tr><th>{t("編號")}</th><th>{t("標題")}</th><th>{t("類型")}</th><th>{caseText(biu, "級別")}</th><th>{t("狀態")}</th><th>{caseText(biu, "責任部門")}</th><th>{caseText(biu, "受理人")}</th><th>{caseText(biu, "SLA")}</th><th>{t("更新")}</th></tr></thead><tbody>{rows.map(x=>{const sla=slaState(x, biu);return <tr key={x.id} onClick={()=>openDetail(x.id)} style={{cursor:"pointer"}}><td className="num" style={{fontSize:10.5}}>{x.case_no}</td><td style={{fontWeight:650,maxWidth:240}}>{x.title}</td><td>{x.type_name_snapshot}</td><td><T tone={severityTone(x.severity)}>{t(SEVERITY[x.severity]||x.severity)}</T></td><td><T tone={statusTone(x.status)} dot>{statusText(biu, x.status)}</T></td><td>{x.owner_unit_name||"—"}</td><td>{x.assignee_name||"—"}</td><td style={{color:sla.breached?"var(--red)":"inherit",fontSize:11}}>{sla.text}</td><td className="num muted" style={{fontSize:10}}>{dt(x.updated_at)}</td></tr>;})}</tbody></table></div>:<Empty icon="clipboard" title={caseText(biu, "尚無事務記錄")} sub={caseText(biu, "選擇行業預設類型或建立公司自訂類型，即可開始記錄。")} action={meta?.permissions?.can_create&&<B kind="primary" icon="plus" onClick={()=>setCreate(true)}>{caseText(biu, "新建事務")}</B>}/>}</div>{create&&meta&&<CreateDrawer meta={meta} biu={biu} onClose={()=>setCreate(false)} onDone={created}/>} {!create&&selected&&meta&&<DetailDrawer item={selected} meta={meta} biu={biu} onClose={closeDetail} onChanged={changed}/>}</div>}
    {tab==="board"&&<Board cases={rows} summary={summary} biu={biu} onSelect={openDetail}/>} {tab==="board"&&selected&&meta&&<DetailDrawer item={selected} meta={meta} biu={biu} onClose={closeDetail} onChanged={changed}/>} {tab==="analytics"&&<Analytics data={analytics} error={analyticsError} loading={analyticsLoading} canAnalyze={!!meta?.permissions?.can_analyze} biu={biu} onRetry={()=>loadAnalytics(meta)}/>} {tab==="types"&&meta&&<TypesPanel meta={meta} onMeta={setMeta} biu={biu}/>}</>;
};

window.W2.PAGES["cases"] = Page;
})();
