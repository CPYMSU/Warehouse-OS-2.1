/* WAREHOUSE 2.1 · 審計日誌 — Swiss 版式,真後端 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "審計日誌": "Audit Log",
  "全平台操作留痕 · 時間戳 · 操作人 · 權限快照 · 頁面只讀,追查交秘書": "Full-platform operation trail · timestamps · operators · permission snapshots · read-only, investigations via Secretary",
  "審計簡報": "Audit briefing",
  "把最近的審計日誌審一遍:標出異常操作、失敗操作和高危 CLI,給我一份審計簡報": "Review the recent audit log: flag anomalies, failures and high-risk CLI, then give me an audit briefing",
  "刷新": "Refresh",
  "留痕總數": "Total entries",
  "寫庫操作": "DB writes",
  "失敗 / 錯誤": "Failed / errors",
  "高危 CLI 執行": "High-risk CLI",
  "條": "", "次": "", "人": "",
  "最新": "latest",
  "AI 來源 {n} 條": "{n} AI-sourced",
  "全部成功": "All succeeded",
  "去追查 →": "Investigate →",
  "把失敗和報錯的操作列出來,逐條分析原因,告訴我要不要處理": "List the failed and errored operations, analyze each cause, and tell me whether action is needed",
  "{n} 次被拒(越權)": "{n} denied (unauthorized)",
  "無越權": "No violations",
  "把被拒絕(越權)的 CLI 操作全部列出來:誰在什麼時候試圖越權、想做什麼,逐條分析": "List all denied (unauthorized) CLI operations: who attempted what and when, analyzed one by one",
  "全部留痕": "All entries",
  "高危 CLI": "High-risk CLI",
  "搜索操作人 / 動作 / 對象 / 指令": "Search operator / action / entity / command",
  "類型": "Type", "人員": "People",
  "全部類型": "All types",
  "全部人員": "All operators",
  "操作流水": "Operation trail",
  "高危 CLI 流水": "High-risk CLI trail",
  "{n} 條記錄": "{n} entries",
  "讀取中…": "Loading…",
  "解釋": "Explain",
  "完成": "Completed", "已執行": "Executed", "待定": "Pending",
  "失敗": "Failed", "錯誤": "Error", "已拒絕": "Rejected",
  "寫": "W", "讀": "R", "寫庫": "Write",
  "審計詳情": "Entry detail",
  "操作人": "Operator", "角色 / 權限": "Role / level", "對象": "Entity",
  "帳號": "Account", "來源": "Source", "狀態": "Status",
  "建立": "Created", "修改 / 刪除": "Updated / deleted",
  "退出碼": "Exit code", "備份": "Backup", "模式": "Mode", "缺權限": "Missing permission", "已備份": "Backed up",
  "請求": "Request", "操作前": "Before", "操作後": "After", "權限快照": "Permission snapshot",
  "完整指令": "Full command",
  "直接吩咐秘書": "Tell the Secretary",
  "解釋這條": "Explain this",
  "追查此人": "Trace this person",
  "追查": "Trace",
  "操作人分佈": "Operators",
  "按留痕條數 · 前 {n} 人": "by entry count · top {n}",
  "暫無審計留痕": "No audit entries yet",
  "所有寫庫操作、AI 動作與高危 CLI 都會自動記錄在這裡,一條不落。": "Every DB write, AI action and high-risk CLI run is recorded here automatically — nothing is missed.",
  "最近系統裡發生了什麼操作?幫我查審計日誌": "What has happened in the system recently? Check the audit log for me",
  "問秘書": "Ask Secretary",
  "當前篩選下沒有記錄": "No entries under current filters",
  "換個條件,或直接讓秘書查:「幫我查◯◯的操作記錄」。": "Change the filters, or just ask the Secretary: \"look up someone's operations\".",
  "還沒有人操作過系統。": "Nobody has operated the system yet.",
  "僅顯示最近 {n} 條 · 更早的記錄請吩咐秘書調取": "Showing latest {n} entries · ask the Secretary for older records",
  "解釋這條審計日誌:{time},{op}({role})執行了「{act}」,對象 {ent},狀態 {st}。說明它具體做了什麼、有沒有風險。": "Explain this audit entry: {time}, {op} ({role}) performed \"{act}\" on {ent}, status {st}. Tell me what it did and whether it carries any risk.",
  "解釋這條高危 CLI 審計:{time},{op} 通過「{kind}」執行了:{cmd}(狀態 {st})。判斷它做了什麼、是否有風險。": "Explain this high-risk CLI entry: {time}, {op} ran via \"{kind}\": {cmd} (status {st}). Assess what it did and whether it is risky.",
  "追查「{name}」最近的操作:把此人的全部審計留痕按時間列出,標出寫庫、失敗與高危 CLI,評估有無異常。": "Trace \"{name}\"'s recent operations: list this person's full audit trail chronologically, flag DB writes, failures and high-risk CLI, and assess anomalies.",
  "新增入庫": "Create inbound", "新增出庫": "Create outbound", "保存設置": "Save settings",
  "AI Action 調用": "AI action call", "寫入日誌": "Write log", "AI 解析降級": "AI parse fallback",
  "SQL 終端": "SQL terminal", "Python 腳本": "Python script", "CLI 指令": "CLI command",
  "平台終端": "Platform terminal", "被拒絕": "Denied", "只讀查詢": "Read-only query",
  "頁面只讀 · 追查與處置交秘書,全程留痕。": "Read-only page · investigations via Secretary, fully audited.",
  "秘書對話": "Secretary chats",
  "對話總數": "Conversations",
  "段": "",
  "查看檔案 →": "Open archive →",
  "寫庫 {w} 次 · AI 來源 {a} 條": "{w} writes · {a} AI-sourced",
  "今天": "Today",
  "昨天": "Yesterday",
  "{n} 段": "{n}",
  "對話檔案庫": "Conversation archive",
  "當前帳號的對話": "this account's conversations",
  "{n} 段對話": "{n} conversations",
  "主題": "Topic",
  "全部主題": "All topics",
  "搜索對話標題 / 摘要": "Search conversation titles / summaries",
  "庫存": "Inventory", "出入庫": "In / out", "財務": "Finance", "採購": "Procurement",
  "預警": "Alerts", "配置": "Settings", "其他": "Other",
  "秘書": "Secretary", "數據站": "DataHub", "系統": "System",
  "(未命名對話)": "(untitled)",
  "有 {n} 段對話沒有標題,列表暫以首句摘要代替(斜體)。": "{n} conversations have no title; the list shows first-message excerpts instead (italic).",
  "讓秘書批量補標題": "Batch-title via Secretary",
  "我在審計頁看到最近有 {n} 段秘書對話沒有標題:請把這些無標題(標題是「新對話」或頻道默認名)的對話逐段讀一遍,各起一個 8 字以內的中文標題並保存到對話記錄。": "On the audit page I see {n} recent secretary conversations without titles: read each untitled conversation (title is the default), give each a title within 8 characters and save it to the conversation record.",
  "總結": "Summarize",
  "讓秘書總結這段對話": "Summarize this conversation",
  "就此話題繼續": "Continue this topic",
  "把對話 #{id}「{title}」完整讀一遍,給我 5 句以內的要點總結:談了什麼、決定了什麼、有沒有待辦。": "Read conversation #{id} \"{title}\" in full and give me a summary within 5 sentences: what was discussed, what was decided, and any follow-ups.",
  "接續對話 #{id}「{title}」的話題:先把該對話的上下文調出來看一遍,然後我們繼續往下談。": "Continue the topic of conversation #{id} \"{title}\": first pull up its context, then let's carry on from there.",
  "把對話 #{id}「{title}」的內容調出來給我看。": "Fetch and show me the content of conversation #{id} \"{title}\".",
  "對話內容讀取失敗": "Failed to load conversation",
  "重新讀取": "Retry",
  "這段對話尚無消息記錄": "This conversation has no messages yet",
  "對話檔案存在,但目前沒有可顯示的消息。": "The conversation exists, but currently has no messages to display.",
  "暫無秘書對話": "No conversations yet",
  "跟秘書聊過的每一段對話都會自動存檔在這裡,包括預警、數據站與採購助手的問答。": "Every conversation with the Secretary is archived here automatically, including alerts, DataHub and procurement assistant Q&A.",
  "你好,幫我看看今天倉庫的整體情況。": "Hello, give me an overview of the warehouse today.",
  "沒有匹配的對話": "No matching conversations",
  "換個關鍵詞或主題,或直接讓秘書搜:「幫我找◯◯那段對話」。": "Try another keyword or topic, or just ask the Secretary: \"find that conversation about ...\".",
  "只列出當前帳號自己的對話,其他帳號的對話互不可見。": "Only this account's own conversations are listed; other accounts' chats are not visible here.",
  "僅顯示最近 {n} 段 · 更早的對話請吩咐秘書調取": "Showing latest {n} conversations · ask the Secretary for older ones",
  "頁面只讀 · 對話檔案僅本帳號可見。": "Read-only page · the conversation archive is visible to this account only.",
  "程序記錄": "Procedure history",
  "案件程序 · 文書流轉 · 審查操作 · 權限快照 · 頁面只讀，追查交秘書": "Case procedures · document flow · review activity · access snapshots · read-only, investigations via Secretary",
  "程序記錄簡報": "Procedure history briefing",
  "程序記錄總數": "Procedure entries",
  "待核查記錄": "Entries to review",
  "系統維護記錄": "System maintenance entries",
  "秘書協作記錄": "Secretary collaboration entries",
  "程序留痕": "Procedure trail",
  "系統記錄": "System records",
  "秘書協作": "Secretary collaboration",
  "程序記錄流水": "Procedure history trail",
  "案件": "Cases", "卷宗": "Records", "程序": "Procedure", "倫理": "Ethics",
  "機構與職位": "Institutions & positions", "指令集": "Instruction sets",
  "程序變更 {w} 次 · 秘書來源 {a} 條": "{w} procedure changes · {a} Secretary-sourced",
  "系統維護流水": "System maintenance history",
  "搜索人員 / 程序動作 / 案件或卷宗": "Search people / procedure actions / cases or records",
  "程序變更": "Procedure change", "查閱": "Viewed",
  "已完成": "Completed",
  "案件收集登記": "Case intake recorded", "案件程序更新": "Case procedure updated",
  "卷宗文書登記": "Record document added", "卷宗文書更新": "Record document updated",
  "卷宗歸檔": "Record archived", "程序工作建立": "Procedure work created",
  "程序工作更新": "Procedure work updated", "職位指派": "Position assigned",
  "權限配置更新": "Access configuration updated", "規則配置更新": "Rule configuration updated",
  "秘書指令調用": "Secretary instruction invoked", "程序記錄登記": "Procedure entry recorded",
  "秘書解析回退": "Secretary parsing fallback", "程序動作": "Procedure action",
  "案件對象": "Case", "卷宗文書": "Record document", "程序工作": "Procedure work",
  "機構職位": "Institution position", "秘書指令": "Secretary instruction", "系統對象": "System object",
  "程序提醒": "Procedure reminder", "卷宗助手": "Record assistant",
  "系統維護": "System maintenance", "系統維護內容已收起": "System maintenance content hidden",
  "核查最近的 BIU 程序記錄：只分析 CASE、RECORD、TASK、機構職位、權限與指令集的異常或失敗，整理一份法律倫理學術工作簡報。": "Review recent BIU procedure history: analyse only anomalies or failures involving CASE, RECORD, TASK, institutions, positions, access, and instruction sets, then prepare a legal-ethics academic briefing.",
  "核查失敗或報錯的 BIU 程序記錄，逐條說明對案件、卷宗、程序工作、機構職位、權限或指令集的影響。": "Review failed BIU procedure entries and explain their impact on cases, records, procedure work, institutions, positions, access, or instruction sets.",
  "核查被權限邊界拒絕的 BIU 系統維護請求，只說明是否影響案件、卷宗、程序工作、機構職位、權限或指令集。": "Review BIU system-maintenance requests rejected by access boundaries and explain only whether they affect cases, records, procedure work, institutions, positions, access, or instruction sets.",
  "查閱「{name}」最近的 BIU 程序記錄：按時間列出案件、卷宗、程序工作、機構職位、權限與指令集變更，標出失敗與待核查項。": "Review {name}'s recent BIU procedure history chronologically, covering cases, records, procedure work, institutions, positions, access, and instruction-set changes, and flag failures or items requiring review.",
  "解釋這條 BIU 程序記錄：{time}，{op}（{role}）登記了「{act}」，對象 {ent}，狀態 {st}。只說明對案件、卷宗或程序工作的影響與是否需要核查。": "Explain this BIU procedure entry: {time}, {op} ({role}) recorded {act} for {ent}, status {st}. Explain only its impact on cases, records, or procedure work and whether review is needed.",
  "解釋這條 BIU 系統維護記錄：{time}，{op}，類型 {kind}，狀態 {st}。只評估是否影響案件、卷宗、程序工作、機構職位、權限或指令集。": "Explain this BIU system-maintenance entry: {time}, {op}, type {kind}, status {st}. Assess only whether it affects cases, records, procedure work, institutions, positions, access, or instruction sets.",
  "暫無 BIU 程序記錄": "No BIU procedure history yet",
  "CASE、RECORD、TASK、機構職位、權限與指令集的變更會記錄在這裡。": "Changes to CASE, RECORD, TASK, institutions, positions, access, and instruction sets are recorded here.",
  "查閱最近的 BIU CASE、RECORD、TASK、機構職位、權限與指令集程序記錄。": "Review recent BIU CASE, RECORD, TASK, institution, position, access, and instruction-set history.",
  "BIU 秘書協作會存檔在這裡，內容限於案件、卷宗、程序工作、機構職位、權限、指令集與法律倫理規則。": "BIU Secretary collaboration is archived here and limited to cases, records, procedure work, institutions, positions, access, instruction sets, and legal-ethics rules.",
  "請先整理我目前可見的 BIU 案件、卷宗與程序工作，列出下一步需要審查的項目。": "Summarise the BIU cases, records, and procedure work visible to me and list the next items requiring review.",
});

const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

const LOG_BIU_COPY = Object.freeze({
  "審計日誌": "程序記錄",
  "全平台操作留痕 · 時間戳 · 操作人 · 權限快照 · 頁面只讀,追查交秘書": "案件程序 · 文書流轉 · 審查操作 · 權限快照 · 頁面只讀，追查交秘書",
  "審計簡報": "程序記錄簡報", "留痕總數": "程序記錄總數",
  "失敗 / 錯誤": "待核查記錄", "高危 CLI 執行": "系統維護記錄",
  "對話總數": "秘書協作記錄", "全部留痕": "程序留痕", "高危 CLI": "系統記錄",
  "秘書對話": "秘書協作", "操作流水": "程序記錄流水",
  "高危 CLI 流水": "系統維護流水",
  "搜索操作人 / 動作 / 對象 / 指令": "搜索人員 / 程序動作 / 案件或卷宗",
  "寫庫 {w} 次 · AI 來源 {a} 條": "程序變更 {w} 次 · 秘書來源 {a} 條",
});
const logText = (biu, value) => t(biu ? (LOG_BIU_COPY[value] || value) : value);

/* ── 詞表與小工具 ── */
const ACTION_LABEL = {
  create_inbound_order: "新增入庫",
  create_outbound_order: "新增出庫",
  save_settings: "保存設置",
  invoke_ai_database_hook: "AI Action 調用",
  write_audit_log: "寫入日誌",
  deepseek_fallback: "AI 解析降級",
};
const BIU_ACTION_LABEL = {
  create_case: "案件收集登記", update_case: "案件程序更新", transition_case: "案件程序更新",
  create_record: "卷宗文書登記", update_record: "卷宗文書更新", archive_record: "卷宗歸檔",
  create_task: "程序工作建立", update_task: "程序工作更新", assign_task: "程序工作更新",
  assign_role: "職位指派", update_permissions: "權限配置更新", save_settings: "規則配置更新",
  invoke_ai_database_hook: "秘書指令調用", write_audit_log: "程序記錄登記", deepseek_fallback: "秘書解析回退",
  create_inbound_order: "程序動作", create_outbound_order: "程序動作",
};
const actLabel = (biu, a) => {
  if (biu) return t(BIU_ACTION_LABEL[a] || "程序動作");
  return ACTION_LABEL[a] ? t(ACTION_LABEL[a]) : (a || "—");
};
const entityLabel = (biu, value) => {
  if (!biu) return S(value);
  const key = String(value || "").toLowerCase();
  if (/case|matter/.test(key)) return t("案件對象");
  if (/record|document|file|dossier/.test(key)) return t("卷宗文書");
  if (/task|workflow|procedure/.test(key)) return t("程序工作");
  if (/role|permission|org|institution|user|account/.test(key)) return t("機構職位");
  if (/prompt|conversation|agent|ai|secretary/.test(key)) return t("秘書指令");
  return t("系統對象");
};
const S = (v) => (v === null || v === undefined || v === "") ? "—" : String(v);
const fmtVal = (v) => {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "object") { try { return JSON.stringify(v, null, 2); } catch (e) { return String(v); } }
  return String(v);
};
const STATUS_META = {
  completed: ["ok", "完成"], executed: ["ok", "已執行"], pending: ["warn", "待定"],
  failed: ["bad", "失敗"], error: ["bad", "錯誤"], rejected: ["bad", "已拒絕"],
};
const StatusTag = ({ s, biu = false }) => {
  const key = String(s || "completed").toLowerCase();
  const meta = STATUS_META[key];
  const label = biu && key === "executed" ? "已完成" : (meta ? meta[1] : key);
  return <T tone={meta ? meta[0] : "plain"} dot>{t(label)}</T>;
};
const SourceTag = ({ s }) => {
  const v = String(s || "system").toLowerCase();
  return v === "ai" ? <T tone="inv">AI</T> : v === "user" ? <T tone="plain">USER</T> : <T tone="plain">SYS</T>;
};
const WriteTag = ({ w, biu = false }) => w === true
  ? <T tone="warn">{t(biu ? "程序變更" : "寫")}</T>
  : w === false ? <T tone="plain">{t(biu ? "查閱" : "讀")}</T> : <T tone="plain">—</T>;
const PRE = { fontFamily: "var(--f-mono)", fontSize: 11, lineHeight: 1.55, whiteSpace: "pre-wrap", wordBreak: "break-word", maxHeight: 170, overflow: "auto", background: "var(--paper-2)", border: "1px solid var(--hair-soft)", padding: 10, margin: 0 };

const explainPrompt = (biu, r) => biu
  ? (r.tab === "cli"
    ? t("解釋這條 BIU 系統維護記錄：{time}，{op}，類型 {kind}，狀態 {st}。只評估是否影響案件、卷宗、程序工作、機構職位、權限或指令集。",
        { time: r.when, op: r.opName, kind: t("系統維護"), st: r.status })
    : t("解釋這條 BIU 程序記錄：{time}，{op}（{role}）登記了「{act}」，對象 {ent}，狀態 {st}。只說明對案件、卷宗或程序工作的影響與是否需要核查。",
        { time: r.when, op: r.opName, role: S(r.role), act: actLabel(true, r.actKey), ent: entityLabel(true, r.entity) + " " + S(r.entityId), st: r.status }))
  : (r.tab === "cli"
    ? t("解釋這條高危 CLI 審計:{time},{op} 通過「{kind}」執行了:{cmd}(狀態 {st})。判斷它做了什麼、是否有風險。",
        { time: r.when, op: r.opName, kind: r.kind, cmd: (r.command || "—").slice(0, 300), st: r.status })
    : t("解釋這條審計日誌:{time},{op}({role})執行了「{act}」,對象 {ent},狀態 {st}。說明它具體做了什麼、有沒有風險。",
        { time: r.when, op: r.opName, role: S(r.role), act: actLabel(false, r.actKey), ent: S(r.entity) + " " + S(r.entityId), st: r.status }));
const tracePrompt = (biu, name) => t(biu
  ? "查閱「{name}」最近的 BIU 程序記錄：按時間列出案件、卷宗、程序工作、機構職位、權限與指令集變更，標出失敗與待核查項。"
  : "追查「{name}」最近的操作:把此人的全部審計留痕按時間列出,標出寫庫、失敗與高危 CLI,評估有無異常。", { name });

/* ── 秘書對話:詞表與小工具 ── */
const CH_LABEL = { assistant: "秘書", agent: "秘書", alerts: "預警", datahub: "數據站", procurement: "採購" };
const BIU_CH_LABEL = { assistant: "秘書", agent: "秘書", alerts: "程序提醒", datahub: "卷宗助手", procurement: "秘書" };
const chLabel = (biu, ch) => {
  const labels = biu ? BIU_CH_LABEL : CH_LABEL;
  return labels[ch] ? t(labels[ch]) : (biu ? t("秘書") : (ch || "—"));
};
/* 後端 title NOT NULL,但默認值(「新對話」/頻道滾動對話默認名)視同無標題 */
const UNTITLED = ["新對話", "AI 秘書", "AI 秘書(內核)", "智能預警 助手", "數據中轉 助手", "招採工作流 助手"];
const TOPIC_ORDER = ["庫存", "出入庫", "財務", "採購", "預警", "配置", "其他"];
const TOPIC_RULES = [
  ["出入庫", /入庫|入库|出庫|出库|收貨|收货|發貨|发货|領用|领用|調撥|调拨|裝卸|装卸|波次/],
  ["庫存", /庫存|库存|盤點|盘点|物資|物资|物料|存量|補貨|补货|貨位|货位|SKU|sku/],
  ["財務", /財務|财务|記賬|记账|憑證|凭证|報銷|报销|發票|发票|分攤|分摊|工資|工资|付款|收款|成本|預算|预算|折舊|折旧|稅|税|AA/],
  ["採購", /採購|采购|招採|招采|供應商|供应商|詢價|询价|比價|比价|訂單|订单|合同/],
  ["預警", /預警|预警|告警|警報|警报|異常|异常|風險|风险|過期|过期|超儲|超储/],
  ["配置", /配置|設置|设置|權限|权限|賬號|账号|用戶|用户|角色|參數|参数|租戶|租户/],
];
const BIU_TOPIC_ORDER = ["案件", "卷宗", "程序", "倫理", "機構與職位", "指令集", "其他"];
const BIU_TOPIC_RULES = [
  ["案件", /案件|case|起訴|起诉|答辯|答辩|原告|被告|上訴|上诉|裁決|裁决|判決|判决/i],
  ["卷宗", /卷宗|文書|文书|證據|证据|檔案|档案|record|dossier|filing/i],
  ["程序", /程序|庭審|庭审|聽證|听证|期限|審查|审查|歸檔|归档|workflow|task/i],
  ["倫理", /倫理|伦理|利益衝突|利益冲突|保密|學術|学术|ethic/i],
  ["機構與職位", /機構|机构|法院|法官|律師|律师|檢察|检察|職位|职位|角色|權限|权限|institution|role/i],
  ["指令集", /秘書|秘书|指令集|提示詞|提示词|prompt|agent|AI/i],
];
const classifyTopic = (biu, text, channel) => {
  const s = String(text || "");
  const rules = biu ? BIU_TOPIC_RULES : TOPIC_RULES;
  for (let i = 0; i < rules.length; i++) if (rules[i][1].test(s)) return rules[i][0];
  if (biu && channel === "alerts") return "程序";
  if (biu) return "其他";
  if (channel === "alerts") return "預警";
  if (channel === "procurement") return "採購";
  return "其他";
};
const parseTs = (s) => {
  if (!s) return null;
  const d = new Date(String(s).replace(" ", "T") + (String(s).length <= 19 ? "Z" : ""));
  return isNaN(d.getTime()) ? null : d;
};
const dayKeyOf = (s) => {
  const d = parseTs(s);
  return d ? d.getFullYear() + "." + pad2(d.getMonth() + 1) + "." + pad2(d.getDate()) : String(s || "").slice(0, 10) || "—";
};
const dayLabel = (s) => {
  const k = dayKeyOf(s);
  const now = new Date(), y = new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1); // 日曆日推算,跨月/跨年/DST 皆安全
  const today = now.getFullYear() + "." + pad2(now.getMonth() + 1) + "." + pad2(now.getDate());
  const yest = y.getFullYear() + "." + pad2(y.getMonth() + 1) + "." + pad2(y.getDate());
  return k === today ? t("今天") : k === yest ? t("昨天") : k;
};
const fmtHM = (s) => {
  const d = parseTs(s);
  return d ? pad2(d.getHours()) + ":" + pad2(d.getMinutes()) : (String(s || "").slice(11, 16) || "—");
};
const summarizePrompt = (biu, id, title) => t(biu
  ? "讀取 BIU 對話 #{id}「{title}」，只總結其中的案件、卷宗、程序工作、機構職位、權限、指令集與法律倫理內容，列出待審查項。"
  : "把對話 #{id}「{title}」完整讀一遍,給我 5 句以內的要點總結:談了什麼、決定了什麼、有沒有待辦。", { id, title });
const continuePrompt = (biu, id, title) => t(biu
  ? "接續 BIU 對話 #{id}「{title}」：先讀取上下文，只在案件、卷宗、程序工作、機構職位、權限、指令集與法律倫理範圍內繼續。"
  : "接續對話 #{id}「{title}」的話題:先把該對話的上下文調出來看一遍,然後我們繼續往下談。", { id, title });

/* 秘書消息:mdToHtml 渲染,CDN 未就緒(返回 null)回退純文本 */
const MdBlock = ({ text }) => {
  const html = W2.mdToHtml ? W2.mdToHtml(text) : null;
  return html != null
    ? <div className="md" style={{ fontSize: 12.5, lineHeight: 1.65, wordBreak: "break-word" }} dangerouslySetInnerHTML={{ __html: html }}/>
    : <div style={{ whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12.5, lineHeight: 1.65 }}>{String(text == null ? "" : text)}</div>;
};

/* ── 對話回放抽屜 ── */
const ConvDrawer = ({ c, onClose, biu = false }) => {
  const [detail, setDetail] = _s(null);
  const [detailError, setDetailError] = _s("");
  const [detailAttempt, setDetailAttempt] = _s(0);
  _e(() => {
    let current = true;
    setDetail(null);
    setDetailError("");
    W2.json("/api/ai/conversations/" + encodeURIComponent(c.id))
      .then(d => { if (current) setDetail(d && typeof d === "object" ? d : {}); })
      .catch(error => {
        if (!current) return;
        setDetail({});
        setDetailError(String((error && error.message) || t("對話內容讀取失敗")));
      });
    return () => { current = false; };
  }, [c.id, detailAttempt]);
  const msgs = (detail && Array.isArray(detail.messages)) ? detail.messages : [];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            <T tone="inv">{chLabel(biu, c.channel)}</T>
            <T tone="plain">{t(c.topic)}</T>
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 18, fontWeight: 750, letterSpacing: "-.02em", lineHeight: 1.3, fontStyle: c.untitled ? "italic" : "normal" }}>
          {c.view_title}
        </div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>
          {dayLabel(c.last)} · {fmtHM(c.created)}–{fmtHM(c.last)} · {t("{n} 條記錄", { n: c.msgs })}
        </div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 300px)", overflowY: "auto" }}>
        {detail === null
          ? <div className="muted num" style={{ padding: "28px 0", textAlign: "center", fontSize: 12 }}>{t("讀取中…")}</div>
          : msgs.length ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 18 }}>
              {msgs.map((m, i) => {
                const role = String((m && m.role) || "");
                const key = m && m.id != null ? m.id : "m" + i;
                if (role === "user") return (
                  <div key={key} style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3 }}>
                    <div className="bubble-u" style={{ fontSize: 12.5, lineHeight: 1.6, padding: "8px 12px", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{S(m.content)}</div>
                    <span className="num muted" style={{ fontSize: 9.5 }}>{fmtHM(m.created_at)}</span>
                  </div>);
                if (role === "system") return (
                  <div key={key} className="muted mono" style={{ fontSize: 10, letterSpacing: ".06em" }}>{t("系統")} · {String((m && m.content) || "").slice(0, 120)}</div>);
                return (
                  <div key={key} style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 3, maxWidth: "94%" }}>
                    <MdBlock text={m && m.content}/>
                    <span className="num muted" style={{ fontSize: 9.5 }}>{fmtHM(m && m.created_at)}</span>
                  </div>);
              })}
            </div>
          ) : detailError ? (
            <EM icon="alert" title={t("對話內容讀取失敗")} sub={detailError}
              action={<B size="sm" icon="refresh" onClick={() => setDetailAttempt(n => n + 1)}>{t("重新讀取")}</B>}/>
          ) : (
            <EM icon="chat" title={t("這段對話尚無消息記錄")} sub={t("對話檔案存在,但目前沒有可顯示的消息。")} />
          )}
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(summarizePrompt(biu, c.id, c.view_title))}>
            <I name="sparkle" size={14}/>{t("讓秘書總結這段對話")}
          </button>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(continuePrompt(biu, c.id, c.view_title))}>
            <I name="arrow" size={14}/>{t("就此話題繼續")}
          </button>
        </div>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("頁面只讀 · 對話檔案僅本帳號可見。")}</div>
      </div>
    </div>
  );
};

/* ── 詳情抽屜 ── */
const AuditDrawer = ({ r, onClose, biu = false }) => {
  const raw = r.raw || {};
  const meta = r.tab === "cli"
    ? [
        [t("操作人"), r.opName],
        [t("角色 / 權限"), S(r.role) + " · L" + S(r.level)],
        [t("來源"), S(r.source)],
        [t(biu ? "程序變更" : "寫庫"), r.write === true ? t(biu ? "程序變更" : "寫") : r.write === false ? t(biu ? "查閱" : "讀") : "—"],
        [t("退出碼"), S(r.detail.exit_code)],
        [t("備份"), S(r.detail.backup)],
      ]
    : [
        [t("操作人"), r.opName],
        [t("角色 / 權限"), S(r.role) + " · L" + S(r.level)],
        [t("對象"), entityLabel(biu, r.entity) + (r.entityId ? " · " + r.entityId : "")],
        [t("帳號"), S(raw.actor)],
        [t("建立"), S(raw.created_at)],
        [t("修改 / 刪除"), S(raw.updated_at) + " / " + S(raw.deleted_at)],
      ];
  const blocks = r.tab === "cli"
    ? [[t("完整指令"), biu ? t("系統維護內容已收起") : (r.command || "—")]]
    : [
        [t("請求"), fmtVal(raw.request !== undefined ? raw.request : raw.request_json)],
        [t("操作前"), fmtVal(raw.before !== undefined ? raw.before : raw.before_json)],
        [t("操作後"), fmtVal(raw.after !== undefined ? raw.after : raw.after_json)],
        [t("權限快照"), fmtVal(raw.permission_snapshot)],
      ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          <div className="row g6">
            {r.tab === "cli" ? <T tone={r.status === "rejected" ? "bad" : "inv"}>{t(biu ? "系統維護" : r.kind)}</T> : <SourceTag s={r.source}/>}
            <StatusTag s={r.status} biu={biu}/>
          </div>
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 18, fontWeight: 750, letterSpacing: "-.02em", lineHeight: 1.3 }}>
          {r.tab === "cli" ? logText(biu, "高危 CLI") : actLabel(biu, r.actKey)}
        </div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{r.when}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 300px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {meta.map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8, minWidth: 0 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 12.5, fontWeight: 650, wordBreak: "break-word" }}>{v}</span>
            </div>
          ))}
        </div>
        {r.tab === "cli" && (
          <div className="row g6 wrap" style={{ marginBottom: 14 }}>
            {r.detail.missing_permission && <T tone="bad">{t("缺權限")} {r.detail.missing_permission}</T>}
            {r.detail.backup && <T tone="plain">{t("已備份")}</T>}
            {r.detail.api && <T tone="plain">{r.detail.api}</T>}
            {r.detail.mode && <T tone="plain">{t("模式")} {r.detail.mode}</T>}
          </div>
        )}
        {blocks.map(([k, v]) => (
          <div key={k} style={{ marginBottom: 14 }}>
            <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{k}</LB>
            <pre style={PRE}>{v}</pre>
          </div>
        ))}
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(explainPrompt(biu, r))}>
            <I name="sparkle" size={14}/>{t("解釋這條")}
          </button>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(tracePrompt(biu, r.opName))}>
            <I name="eye" size={14}/>{t("追查此人")}
          </button>
        </div>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t(biu ? "頁面只讀 · 案件與卷宗核查交秘書，全程留痕。" : "頁面只讀 · 追查與處置交秘書,全程留痕。")}</div>
      </div>
    </div>
  );
};

/* ── 頁面 ── */
const Page = ({ templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const [logs, setLogs] = _s(null);   // /api/audit/logs → {rows, summary}
  const [cli, setCli] = _s(null);     // /api/audit/cli  → {rows, summary}
  const [conv, setConv] = _s(null);   // /api/ai/conversations → {rows, hasMore}(僅當前帳號)
  const [tick, setTick] = _s(0);
  const [tab, setTab] = _s("all");
  const [q, setQ] = _s("");
  const [act, setAct] = _s("all");
  const [op, setOp] = _s("all");
  const [topic, setTopic] = _s("all");
  const [sel, setSel] = _s(null);
  const [csel, setCsel] = _s(null);
  const [deriv, setDeriv] = _s({});   // 無標題對話 id → 首條用戶消息摘要
  const askedRef = React.useRef({});

  _e(() => {
    W2.json("/api/audit/logs?limit=500").then(d => setLogs(d && typeof d === "object" ? d : {})).catch(() => setLogs({}));
    if (biu) {
      setCli({ rows: [], summary: {} });
      setConv({ rows: [], hasMore: false });
    } else {
      W2.json("/api/audit/cli?limit=500").then(d => setCli(d && typeof d === "object" ? d : {})).catch(() => setCli({}));
      W2.json("/api/ai/conversations?limit=100").then(d => setConv(d && typeof d === "object" ? d : {})).catch(() => setConv({}));
    }
  }, [tick, biu]);
  _e(() => {
    const h = (e) => { if (e.key === "Escape") { setSel(null); setCsel(null); } };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const busy = logs === null || cli === null;
  const lsum = (logs && logs.summary) || {};
  const csum = (cli && cli.summary) || {};

  const logRows = _mm(() => (logs && Array.isArray(logs.rows) ? logs.rows : []).map((r, i) => ({
    key: "a" + (r && r.id != null ? r.id : "i" + i), tab: "all",
    when: S(r.occurred_at || r.created_at),
    opName: S(r.operator_name || r.actor),
    role: r.operator_role, level: r.permission_level,
    actKey: r.action || "", entity: r.entity_type, entityId: r.entity_id,
    source: r.source || "system", status: r.operation_status || "completed",
    command: "", kind: "", detail: {}, raw: r || {},
  })), [logs]);
  const cliRows = _mm(() => (cli && Array.isArray(cli.rows) ? cli.rows : []).map((r, i) => ({
    key: "c" + (r && r.id != null ? r.id : "i" + i), tab: "cli",
    when: S(r.when), opName: S(r.operator), role: r.role, level: r.level,
    kind: S(r.kind), command: r.command || "",
    write: r.write, status: r.status || "completed", source: r.source || "system",
    actKey: r.kind_key || "", entity: "", entityId: "",
    detail: (r.detail && typeof r.detail === "object") ? r.detail : {}, raw: r || {},
  })), [cli]);

  /* ── 秘書對話:歸一化 + 摘要標題補齊 + 主題分類 ── */
  const convRows = _mm(() => (conv && Array.isArray(conv.rows) ? conv.rows : []).map((r) => {
    const raw = r || {};
    const title = String(raw.title == null ? "" : raw.title).trim();
    return {
      id: raw.id, title,
      untitled: !title || UNTITLED.indexOf(title) >= 0,
      channel: String(raw.channel || "assistant"),
      msgs: num(raw.message_count),
      created: raw.created_at || "",
      last: raw.last_message_at || raw.updated_at || raw.created_at || "",
      summary: String(raw.summary || ""), snippet: String(raw.snippet || ""),
    };
  }), [conv]);
  _e(() => {  // 無標題 → 拉詳情取首條用戶消息前 24 字作摘要標題(封頂 10 段,不寫庫)
    convRows.filter(r => r.id != null && r.untitled && !askedRef.current[r.id]).slice(0, 10).forEach(r => {
      askedRef.current[r.id] = 1;
      W2.json("/api/ai/conversations/" + encodeURIComponent(r.id)).then(d => {
        const ms = (d && Array.isArray(d.messages)) ? d.messages : [];
        const fu = ms.find(m => m && m.role === "user" && m.content);
        const txt = fu ? String(fu.content).replace(/\s+/g, " ").trim().slice(0, 24) : "";
        if (txt) setDeriv(p => ({ ...p, [r.id]: txt }));
      }).catch(() => {});
    });
  }, [convRows]);
  const convView = _mm(() => convRows.map(r => {
    const dt = r.untitled ? (deriv[r.id] || "") : "";
    return { ...r,
      view_title: r.untitled ? (dt || t("(未命名對話)")) : r.title,
      topic: classifyTopic(biu, (r.untitled ? dt : r.title) + " " + r.summary + " " + r.snippet, r.channel),
    };
  }), [convRows, deriv, biu]);
  const topicChips = _mm(() => {
    const m = {};
    convView.forEach(r => { m[r.topic] = (m[r.topic] || 0) + 1; });
    return (biu ? BIU_TOPIC_ORDER : TOPIC_ORDER).filter(k => m[k]).map(k => [k, m[k]]);
  }, [convView, biu]);
  const convShown = _mm(() => {
    let arr = convView;
    if (topic !== "all") arr = arr.filter(r => r.topic === topic);
    const s = q.trim().toLowerCase();
    if (s) arr = arr.filter(r =>
      [r.view_title, r.title, r.summary, r.snippet, chLabel(biu, r.channel), t(r.topic)]
        .map(x => String(x || "")).join(" ").toLowerCase().includes(s));
    return arr;
  }, [convView, topic, q, biu]);
  const convGroups = _mm(() => {  // 按天歸組(服務端已按 last_message_at 倒序)
    const gs = [], idx = {};
    convShown.forEach(r => {
      const k = dayLabel(r.last);
      if (idx[k] === undefined) { idx[k] = gs.length; gs.push([k, []]); }
      gs[idx[k]][1].push(r);
    });
    return gs;
  }, [convShown]);
  const untitledCount = convView.filter(r => r.untitled).length;
  const convBusy = conv === null;
  const convCount = convBusy ? "—" : String(convRows.length) + (conv && conv.hasMore ? "+" : "");

  const rows = tab === "cli" ? cliRows : logRows;
  const actKeyOf = (r) => tab === "all" ? (r.actKey || "—") : (r.kind || "—");
  const actChips = _mm(() => {
    const m = {};
    rows.forEach(r => { const k = actKeyOf(r); m[k] = (m[k] || 0) + 1; });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 7);
  }, [rows, tab]);
  const opChips = _mm(() => {
    const m = {};
    rows.forEach(r => { if (r.opName && r.opName !== "—") m[r.opName] = (m[r.opName] || 0) + 1; });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [rows, tab]);

  const shown = _mm(() => {
    let arr = rows;
    if (act !== "all") arr = arr.filter(r => actKeyOf(r) === act);
    if (op !== "all") arr = arr.filter(r => r.opName === op);
    const s = q.trim().toLowerCase();
    if (s) arr = arr.filter(r =>
      [r.opName, r.actKey, r.kind, r.entity, r.entityId, r.command, r.when, r.source, r.status]
        .map(x => String(x || "")).join(" ").toLowerCase().includes(s));
    return arr;
  }, [rows, act, op, q, tab]);
  const CAP = 150;
  const visible = shown.slice(0, CAP);

  const switchTab = (k) => { setTab(k); setAct("all"); setOp("all"); setTopic("all"); setSel(null); setCsel(null); };

  const aiCnt = logRows.filter(r => String(r.source).toLowerCase() === "ai").length;
  const total = num(lsum.total) || logRows.length;
  const writes = num(lsum.writes);
  const failed = num(lsum.failed) + num(csum.failed);
  const cliTotal = num(csum.total) || cliRows.length;
  const denied = num(csum.denied);

  const opsAll = _mm(() => {
    const m = {};
    logRows.concat(cliRows).forEach(r => { if (r.opName && r.opName !== "—") m[r.opName] = (m[r.opName] || 0) + 1; });
    return Object.entries(m).sort((a, b) => b[1] - a[1]).slice(0, 6);
  }, [logRows, cliRows]);
  const opsTotal = logRows.length + cliRows.length;

  return (<>
    <Folio no="16" en={biu ? "PROCEDURE HISTORY" : "AUDIT"} title={logText(biu, "審計日誌")}
      sub={logText(biu, "全平台操作留痕 · 時間戳 · 操作人 · 權限快照 · 頁面只讀,追查交秘書")}
      right={<>
        <B icon="refresh" onClick={() => setTick(v => v + 1)}>{t("刷新")}</B>
        <B kind="primary" icon="sparkle" onClick={() => ask(t(biu
          ? "核查最近的 BIU 程序記錄：只分析 CASE、RECORD、TASK、機構職位、權限與指令集的異常或失敗，整理一份法律倫理學術工作簡報。"
          : "把最近的審計日誌審一遍:標出異常操作、失敗操作和高危 CLI,給我一份審計簡報"))}>{logText(biu, "審計簡報")}</B>
      </>}/>

    <div className="kpi-band">
      <Kpi label={logText(biu, "留痕總數")} value={total} unit={t("條")} delay={0}
        foot={<span className="muted num" style={{ fontSize: 11.5 }}>{t(biu ? "程序變更 {w} 次 · 秘書來源 {a} 條" : "寫庫 {w} 次 · AI 來源 {a} 條", { w: writes, a: aiCnt })}</span>}/>
      {/* 原「寫庫操作」格資訊量最低(寫庫數已併入左格 foot,行內另有 寫/讀 標),讓位給對話總數 */}
      <Kpi label={logText(biu, "對話總數")} value={convCount} unit={t("段")} delay={.05}
        foot={<button className="tag plain" style={{ cursor: "pointer" }} onClick={() => switchTab("chat")}>{t("查看檔案 →")}</button>}/>
      <Kpi label={logText(biu, "失敗 / 錯誤")} value={failed} unit={t("次")} red={failed > 0} delay={.1}
        foot={failed > 0
          ? <button className="tag bad" style={{ cursor: "pointer" }} onClick={() => ask(t(biu
              ? "核查失敗或報錯的 BIU 程序記錄，逐條說明對案件、卷宗、程序工作、機構職位、權限或指令集的影響。"
              : "把失敗和報錯的操作列出來,逐條分析原因,告訴我要不要處理"))}>{t("去追查 →")}</button>
          : <T tone="ok" dot>{t("全部成功")}</T>}/>
      <Kpi label={logText(biu, "高危 CLI 執行")} value={cliTotal} unit={t("次")} red={denied > 0} delay={.15}
        foot={denied > 0
          ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t(biu
              ? "核查被權限邊界拒絕的 BIU 系統維護請求，只說明是否影響案件、卷宗、程序工作、機構職位、權限或指令集。"
              : "把被拒絕(越權)的 CLI 操作全部列出來:誰在什麼時候試圖越權、想做什麼,逐條分析"))}>{t("{n} 次被拒(越權)", { n: denied })}</button>
          : <T tone="ok" dot>{t("無越權")}</T>}/>
    </div>

    <div className="row g14 wrap rise" style={{ padding: "18px 0 14px", borderBottom: "1px solid var(--hair)", animationDelay: ".05s" }}>
      <div className="seg">
        {[["all", "全部留痕", "clipboard"], ["cli", "高危 CLI", "shield"], ["chat", "秘書對話", "sparkle"]].map(([k, label, icon]) => (
          <button key={k} className={tab === k ? "on" : ""} onClick={() => switchTab(k)}>
            <span className="row g6"><I name={icon} size={12}/>{logText(biu, label)}</span>
          </button>
        ))}
      </div>
      <div style={{ position: "relative", flex: 1, minWidth: 240 }}>
        <I name="search" size={15} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
        <input className="field" style={{ paddingLeft: 26, height: 38 }} value={q} onChange={e => setQ(e.target.value)}
          placeholder={tab === "chat" ? t("搜索對話標題 / 摘要") : logText(biu, "搜索操作人 / 動作 / 對象 / 指令")}/>
      </div>
    </div>

    {tab === "chat" && !!convView.length && (
      <div className="row g10 wrap rise" style={{ padding: "12px 0 14px", borderBottom: "1px solid var(--hair)", animationDelay: ".08s" }}>
        <LB dim>{t("主題")}</LB>
        <button className={"chip" + (topic === "all" ? " on" : "")} onClick={() => setTopic("all")}>{t("全部主題")}</button>
        {topicChips.map(([k, c]) => (
          <button key={k} className={"chip" + (topic === k ? " on" : "")} onClick={() => setTopic(topic === k ? "all" : k)}>
            {t(k)}<span className="num muted" style={{ fontSize: 10.5 }}>{c}</span>
          </button>
        ))}
      </div>
    )}

    {tab !== "chat" && !!rows.length && (
      <div className="row g10 wrap rise" style={{ padding: "12px 0 14px", borderBottom: "1px solid var(--hair)", animationDelay: ".08s" }}>
        <LB dim>{t("類型")}</LB>
        <button className={"chip" + (act === "all" ? " on" : "")} onClick={() => setAct("all")}>{t("全部類型")}</button>
        {actChips.map(([k, c]) => (
          <button key={k} className={"chip" + (act === k ? " on" : "")} onClick={() => setAct(act === k ? "all" : k)}>
            {tab === "all" ? actLabel(biu, k) : t(biu ? "系統維護" : k)}<span className="num muted" style={{ fontSize: 10.5 }}>{c}</span>
          </button>
        ))}
        <span style={{ width: 1, height: 20, background: "var(--hair)", margin: "0 4px" }}/>
        <LB dim>{t("人員")}</LB>
        <button className={"chip" + (op === "all" ? " on" : "")} onClick={() => setOp("all")}>{t("全部人員")}</button>
        {opChips.map(([k, c]) => (
          <button key={k} className={"chip" + (op === k ? " on" : "")} onClick={() => setOp(op === k ? "all" : k)}>
            {k}<span className="num muted" style={{ fontSize: 10.5 }}>{c}</span>
          </button>
        ))}
      </div>
    )}

    {tab === "chat" && (
    <Band no="A" title={t("對話檔案庫")}
      sub={t("{n} 段對話", { n: convShown.length }) + " · " + t("當前帳號的對話")}
      delay={.1}>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {untitledCount >= 3 && (
            <div className="row spread wrap g10" style={{ padding: "10px 12px", border: "1px solid var(--hair)", background: "var(--paper-2)", marginBottom: 12 }}>
              <span className="muted" style={{ fontSize: 12 }}>{t("有 {n} 段對話沒有標題,列表暫以首句摘要代替(斜體)。", { n: untitledCount })}</span>
              <B size="sm" icon="sparkle" onClick={() => ask(t(biu
                ? "為最近 {n} 段未命名的 BIU 秘書協作逐段補一個 8 字內標題；標題只可概括案件、卷宗、程序工作、機構職位、權限、指令集或法律倫理內容。"
                : "我在審計頁看到最近有 {n} 段秘書對話沒有標題:請把這些無標題(標題是「新對話」或頻道默認名)的對話逐段讀一遍,各起一個 8 字以內的中文標題並保存到對話記錄。", { n: Math.min(untitledCount, 20) }))}>{t("讓秘書批量補標題")}</B>
            </div>
          )}
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {convGroups.map(([label, list]) => (
              <div key={label}>
                <div className="row spread" style={{ padding: "12px 4px 8px", borderBottom: "1px solid var(--hair)" }}>
                  <span className="mono" style={{ fontSize: 10.5, letterSpacing: ".12em", fontWeight: 600 }}>{label}</span>
                  <span className="num muted" style={{ fontSize: 10.5 }}>{t("{n} 段對話", { n: list.length })}</span>
                </div>
                {list.map((r, i) => (
                  <div key={r.id != null ? r.id : "x" + i} className="ledger-row"
                    style={{ cursor: "pointer", ...(csel && csel.id === r.id ? { background: "var(--white)", borderLeft: "2px solid var(--red)", paddingLeft: 2 } : null) }}
                    onClick={() => setCsel(csel && csel.id === r.id ? null : r)}>
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <span className="num muted" style={{ width: 92, fontSize: 11.5, flexShrink: 0 }}>{fmtHM(r.created)}–{fmtHM(r.last)}</span>
                    <div className="col g4" style={{ flex: 1.4, minWidth: 0 }}>
                      <span style={{ fontWeight: 650, fontSize: 13.5, fontStyle: r.untitled ? "italic" : "normal", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.view_title}</span>
                      {(r.snippet || r.summary) && <span className="muted" style={{ fontSize: 11, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{r.snippet || r.summary}</span>}
                    </div>
                    <T tone="inv">{chLabel(biu, r.channel)}</T>
                    <T tone="plain">{t(r.topic)}</T>
                    <span className="num" style={{ width: 58, textAlign: "right", fontSize: 12.5, fontWeight: 650, flexShrink: 0 }}>{r.msgs}<span className="muted" style={{ fontWeight: 400 }}> {t("條")}</span></span>
                    <B size="sm" icon="sparkle" onClick={(e) => { e.stopPropagation(); ask(summarizePrompt(biu, r.id, r.view_title)); }}>{t("總結")}</B>
                  </div>
                ))}
              </div>
            ))}
          </div>
          {!convShown.length && (convBusy
            ? <div className="muted num" style={{ padding: "34px 0", textAlign: "center", fontSize: 12 }}>{t("讀取中…")}</div>
            : convView.length
              ? <EM icon="search" title={t("沒有匹配的對話")} sub={t("換個關鍵詞或主題,或直接讓秘書搜:「幫我找◯◯那段對話」。")}/>
              : <EM icon="sparkle" title={t("暫無秘書對話")} sub={t(biu
                  ? "BIU 秘書協作會存檔在這裡，內容限於案件、卷宗、程序工作、機構職位、權限、指令集與法律倫理規則。"
                  : "跟秘書聊過的每一段對話都會自動存檔在這裡,包括預警、數據站與採購助手的問答。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(t(biu
                    ? "請先整理我目前可見的 BIU 案件、卷宗與程序工作，列出下一步需要審查的項目。"
                    : "你好,幫我看看今天倉庫的整體情況。"))}>{t("問秘書")}</B>}/>)}
          {conv && conv.hasMore && (
            <div className="muted mono" style={{ fontSize: 10.5, letterSpacing: ".08em", padding: "12px 4px 0" }}>
              {t("僅顯示最近 {n} 段 · 更早的對話請吩咐秘書調取", { n: convRows.length })}
            </div>
          )}
          <div className="muted" style={{ fontSize: 10.5, padding: "10px 4px", lineHeight: 1.6 }}>{t("只列出當前帳號自己的對話,其他帳號的對話互不可見。")}</div>
        </div>
        {csel && <ConvDrawer c={csel} biu={biu} onClose={() => setCsel(null)}/>}
      </div>
    </Band>
    )}

    {tab !== "chat" && (
    <Band no="A" title={tab === "all" ? logText(biu, "操作流水") : logText(biu, "高危 CLI 流水")}
      sub={t("{n} 條記錄", { n: shown.length }) + (csum.latest || lsum.latest ? " · " + t("最新") + " " + S(tab === "all" ? lsum.latest : csum.latest) : "")}
      delay={.1}>
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {visible.map((r, i) => (
              <div key={r.key} className="ledger-row" style={{ cursor: "pointer", ...(sel && sel.key === r.key ? { background: "var(--white)", borderLeft: "2px solid var(--red)", paddingLeft: 2 } : null) }}
                onClick={() => setSel(sel && sel.key === r.key ? null : r)}>
                <span className="lr-idx">{pad2(i + 1)}</span>
                <span className="num muted" style={{ width: 138, fontSize: 11.5, flexShrink: 0 }}>{r.when}</span>
                {tab === "all" ? (
                  <div className="col g4" style={{ flex: 1.2, minWidth: 0 }}>
                    <span style={{ fontWeight: 650, fontSize: 13.5 }}>{actLabel(biu, r.actKey)}</span>
                    <span className="num muted" style={{ fontSize: 11 }}>{entityLabel(biu, r.entity)}{r.entityId ? " · " + r.entityId : ""}</span>
                  </div>
                ) : (
                  <div className="col g4" style={{ flex: 1.2, minWidth: 0 }}>
                    <span className="num" style={{ fontSize: 12, fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{biu ? t("系統維護內容已收起") : (r.command || "—")}</span>
                    <span className="muted" style={{ fontSize: 11 }}>{t(biu ? "系統維護" : r.kind)}</span>
                  </div>
                )}
                <div className="col g4" style={{ flex: .8, minWidth: 0 }}>
                  <span style={{ fontWeight: 600, fontSize: 12.5 }}>{r.opName}</span>
                  <span className="num muted" style={{ fontSize: 11 }}>{S(r.role)} · L{S(r.level)}</span>
                </div>
                {tab === "all" ? <SourceTag s={r.source}/> : <WriteTag w={r.write} biu={biu}/>}
                <StatusTag s={r.status} biu={biu}/>
                <B size="sm" icon="sparkle" onClick={(e) => { e.stopPropagation(); ask(explainPrompt(biu, r)); }}>{t("解釋")}</B>
              </div>
            ))}
          </div>
          {!visible.length && (busy
            ? <div className="muted num" style={{ padding: "34px 0", textAlign: "center", fontSize: 12 }}>{t("讀取中…")}</div>
            : rows.length
              ? <EM icon="search" title={t("當前篩選下沒有記錄")} sub={t("換個條件,或直接讓秘書查:「幫我查◯◯的操作記錄」。")}/>
              : <EM icon="shield" title={t(biu ? "暫無 BIU 程序記錄" : "暫無審計留痕")} sub={t(biu
                  ? "CASE、RECORD、TASK、機構職位、權限與指令集的變更會記錄在這裡。"
                  : "所有寫庫操作、AI 動作與高危 CLI 都會自動記錄在這裡,一條不落。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(t(biu
                    ? "查閱最近的 BIU CASE、RECORD、TASK、機構職位、權限與指令集程序記錄。"
                    : "最近系統裡發生了什麼操作?幫我查審計日誌"))}>{t("問秘書")}</B>}/>)}
          {shown.length > CAP && (
            <div className="muted mono" style={{ fontSize: 10.5, letterSpacing: ".08em", padding: "12px 4px" }}>
              {t("僅顯示最近 {n} 條 · 更早的記錄請吩咐秘書調取", { n: CAP })}
            </div>
          )}
        </div>
        {sel && <AuditDrawer r={sel} biu={biu} onClose={() => setSel(null)}/>}
      </div>
    </Band>
    )}

    {tab !== "chat" && (
    <Band no="B" title={t("操作人分佈")} sub={opsAll.length ? t("按留痕條數 · 前 {n} 人", { n: opsAll.length }) : ""} delay={.15}>
      {opsAll.length ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 40px" }}>
          {opsAll.map(([name, cnt]) => (
            <div key={name} className="row g12">
              <div style={{ flex: 1, minWidth: 0 }}>
                <Meter label={name} count={cnt} total={opsTotal} color="var(--ink)"/>
              </div>
              <B size="sm" icon="eye" onClick={() => ask(tracePrompt(biu, name))}>{t("追查")}</B>
            </div>
          ))}
        </div>
      ) : <EM icon="user" title={busy ? t("讀取中…") : t("還沒有人操作過系統。")} sub={busy ? "" : t(biu
        ? "CASE、RECORD、TASK、機構職位、權限與指令集的變更會記錄在這裡。"
        : "所有寫庫操作、AI 動作與高危 CLI 都會自動記錄在這裡,一條不落。")}/>}
    </Band>
    )}
  </>);
};

window.W2.PAGES["logs"] = Page;
})();
