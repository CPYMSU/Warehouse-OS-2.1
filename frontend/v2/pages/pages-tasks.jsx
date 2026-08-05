/* WAREHOUSE OS 2.1 · PERSONAL TASK
   Mobile-first Swiss workspace shared by the standalone TASK route and Records. */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { useState: S, useEffect: E, useLayoutEffect: LE, useMemo: M, useCallback: C, useRef: R } = React;
const { Icon: I, Btn: B, Label: L, Empty } = W2;

window.W2_LANG.addEN({
  "任務": "Tasks", "任務與計劃": "Tasks & plans", "個人行動中心": "Personal action centre",
  "今天": "Today", "收件匣": "Inbox", "日曆": "Calendar", "計劃": "Plans", "透視": "Insights",
  "所有與你相關的操作、安排與檔案跟進，都在同一條時間線。": "Every operation, schedule and record follow-up connected to you, on one timeline.",
  "新增": "Add", "新增任務": "New task", "新增日程": "New event", "新增計劃": "New plan",
  "建立跟進任務": "Create follow-up task", "從此檔案建立跟進任務": "Create a follow-up task from this record",
  "任務標題": "Task title", "日程名稱": "Event title", "計劃名稱": "Plan title",
  "說明與交付標準": "Notes & completion criteria", "開始": "Start", "截止": "Due",
  "全天": "All day", "時間": "Time", "優先級": "Priority", "負責人": "Assignee",
  "負責部門": "Owning team",
  "類別": "Category", "可見範圍": "Visibility", "地點": "Location", "選填地點或會議連結": "Optional place or meeting link",
  "工作": "Work", "會議": "Meeting", "出差": "Travel", "考試": "Exam", "個人": "Personal", "檔案": "Record", "其他": "Other",
  "僅自己": "Private", "團隊": "Team", "全公司": "Company",
  "未指定": "Unassigned", "所屬計劃": "Plan", "不加入計劃": "No plan",
  "本人（預設）": "Myself (default)",
  "建立任務": "Create task", "建立日程": "Create event", "建立計劃": "Create plan",
  "建立中…": "Creating…", "任務已建立": "Task created", "無法建立任務": "Could not create task",
  "任務資料暫時無法載入": "Tasks are temporarily unavailable", "任務服務尚未啟用或暫時無法連線。": "The task service is not enabled or is temporarily unreachable.",
  "重新載入": "Reload", "同步中": "Syncing", "剛剛同步": "Synced just now",
  "待開始": "Planned", "進行中": "In progress", "已暫停": "Paused", "已完成": "Completed", "已取消": "Cancelled",
  "立即開始": "Start now", "繼續": "Resume", "暫停": "Pause", "等待": "Wait", "完成": "Complete", "取消任務": "Cancel task",
  "重新進行": "Reopen", "任務已完成": "Task completed", "撤銷": "Undo",
  "編輯": "Edit", "編輯任務": "Edit task", "儲存更改": "Save changes", "儲存中…": "Saving…",
  "任務已更新": "Task updated", "更新失敗": "Update failed",
  "刪除任務": "Delete task", "確定刪除？": "Delete this task?", "保留任務": "Keep task",
  "刪除中…": "Deleting…", "任務已刪除": "Task deleted", "刪除失敗": "Delete failed",
  "此操作無法撤銷。若任務已開啟協作，聊天、文件與成員記錄也會一併刪除。": "This cannot be undone. If collaboration is enabled, its chat, documents and membership records will also be deleted.",
  "狀態更新失敗": "Could not update status", "逾期": "Overdue", "今天截止": "Due today", "即將開始": "Starting soon",
  "高": "High", "普通": "Normal", "低": "Low", "緊急": "Urgent",
  "我的今日": "My day", "今日重點": "Today focus", "已排程": "Scheduled", "未完成": "Open", "完成率": "Completion",
  "今日沒有排定任務": "Nothing scheduled today", "把下一個行動放進今天，或從檔案建立跟進。": "Add the next action to today, or create a follow-up from a record.",
  "查看全部任務": "View all tasks", "全部": "All", "未結束": "Open", "已結束": "Closed",
  "搜尋任務、計劃或來源": "Search tasks, plans or sources", "沒有符合條件的任務": "No tasks match these filters",
  "清除篩選": "Clear filters", "本月": "This month", "上一個月": "Previous month", "下一個月": "Next month",
  "當日安排": "Day agenda", "這一天尚無安排": "No schedule for this day", "加入這一天": "Add to this day",
  "週一": "MON", "週二": "TUE", "週三": "WED", "週四": "THU", "週五": "FRI", "週六": "SAT", "週日": "SUN",
  "沒有計劃": "No plans yet", "用計劃把多個任務組成一段可追蹤的工作。": "Use a plan to turn related tasks into trackable work.",
  "未歸入計劃": "No plan", "項任務": "tasks", "來源分佈": "Source mix", "類別分佈": "Category mix", "狀態結構": "Status structure",
  "未來七日負載": "Next 7 days", "過去七日完成": "Completed in 7 days", "本週容量": "Weekly capacity",
  "無排程": "Unscheduled", "來自檔案": "From records", "系統操作": "System operation", "個人建立": "Personal",
  "來源": "Source", "打開來源": "Open source", "更多狀態": "More status actions", "關閉": "Close",
  "需要標題": "A title is required", "截止時間不得早於開始時間": "Due time cannot be earlier than the start time",
  "日": "day", "月": "month", "年": "year", "今日": "TODAY", "已完成工作": "Completed work",
  "管理任務、日程與部門計劃，並保留與原始檔案的關聯。": "Manage tasks, events and team plans while preserving links to source records.",
  "資料權限由任務發起人、負責人、參與者與部門範圍共同決定。": "Visibility follows creator, assignee, participant and department scope.",
  "選擇類型": "Choose type", "任務 API 回傳格式不完整": "The task API returned an incomplete response",
  "我的工作": "My work",
  "程序會議": "Procedure meeting",
  "程序日程": "Procedure schedule",
  "資格考核": "Qualification assessment",
  "案件工作": "Case work",
  "個人研修": "Individual study",
  "卷宗整理": "Record preparation",
  "倫理研究": "Ethics research",
  "案件程序": "Case procedure",
  "自行建立": "Created here",
  "案件工作中心": "Case work centre",
  "今日工作": "Today's work",
  "工作清單": "Work list",
  "程序日曆": "Procedure calendar",
  "程序計畫": "Procedure plans",
  "工作分析": "Work insights",
  "工作事項": "Work item",
  "新增工作事項": "New work item",
  "建立工作事項": "Create work item",
  "案件程序中的個人工作、日程與卷宗跟進，統一顯示在同一條時間線。": "Personal work, schedules, and record follow-ups for case procedures on one timeline.",
  "管理工作事項、程序日程與程序計畫，並保留與案件卷宗的關聯。": "Manage work items, procedure schedules, and plans while preserving links to case records.",
  "協作廣場": "Collaboration hub",
  "探索公司內可加入的任務協作，或回到自己的工作間。": "Discover task collaborations across your company, or return to your own workspaces.",
  "搜尋協作任務": "Search collaborative tasks",
  "所有範圍": "All scopes",
  "公司可見": "Company",
  "團隊可見": "Team",
  "隱藏": "Hidden",
  "暫無可探索的協作": "No collaborations to discover",
  "調整搜尋或範圍，或從任務卡開啟新的協作。": "Change the search or scope, or open collaboration from a task card.",
  "載入更多": "Load more",
  "協作資料暫時無法載入": "Collaboration is temporarily unavailable",
  "您已無權存取此協作工作間": "You no longer have access to this workspace",
  "打開工作間": "Open workspace",
  "協作工作間": "Collaboration workspace",
  "概覽": "Overview",
  "成員": "Members",
  "聊天": "Chat",
  "開啟協作": "Enable collaboration",
  "尚未開啟協作": "Collaboration is not enabled yet",
  "設定誰能找到此任務，以及加入方式。": "Choose who can discover this task and how people join.",
  "探索範圍": "Discoverability",
  "加入方式": "Join policy",
  "自由加入": "Open join",
  "申請審批": "Request approval",
  "僅限邀請": "Invite only",
  "加入協作": "Join",
  "申請加入": "Request to join",
  "申請已送出": "Request sent",
  "離開協作": "Leave workspace",
  "接受邀請": "Accept invitation",
  "婉拒邀請": "Decline invitation",
  "等待負責人審批": "Awaiting owner approval",
  "待處理申請": "Pending requests",
  "批准": "Approve",
  "拒絕": "Reject",
  "邀請同事": "Invite a colleague",
  "選擇同事": "Choose a colleague",
  "發送邀請": "Send invitation",
  "目前沒有成員": "No members yet",
  "目前沒有待處理申請": "No pending requests",
  "目前沒有邀請": "No invitations",
  "移交負責人": "Transfer ownership",
  "確定將協作負責人移交給": "Transfer workspace ownership to",
  "訊息": "Message",
  "輸入訊息": "Write a message",
  "發送": "Send",
  "語音會議": "Voice meeting",
  "影音會議": "Video meeting",
  "加入語音會議": "Join voice meeting",
  "加入影音會議": "Join video meeting",
  "離開語音會議": "Leave voice meeting",
  "離開影音會議": "Leave video meeting",
  "麥克風靜音": "Mute microphone",
  "取消靜音": "Unmute microphone",
  "開啟鏡頭": "Turn camera on",
  "關閉鏡頭": "Turn camera off",
  "鏡頭已開啟": "Camera on",
  "鏡頭連線中": "Connecting camera",
  "分享螢幕": "Share screen",
  "停止分享": "Stop sharing",
  "正在取得麥克風權限": "Requesting microphone access",
  "正在加入會議": "Joining meeting",
  "會議連線中": "In meeting",
  "會議重新連線中": "Reconnecting meeting",
  "目前有人正在分享螢幕": "Someone is already sharing their screen",
  "目前沒有螢幕分享": "No screen is being shared",
  "你的螢幕": "Your screen",
  "你的鏡頭": "Your camera",
  "會議參與者": "Meeting participants",
  "會議控制": "Meeting controls",
  "返回會議": "Return to meeting",
  "點擊播放會議音訊": "Play meeting audio",
  "瀏覽器阻止自動播放會議音訊。": "The browser blocked automatic meeting audio playback.",
  "這個瀏覽器不支援語音會議": "This browser does not support voice meetings",
  "這個瀏覽器不支援視訊鏡頭": "This browser does not support camera video",
  "這個瀏覽器不支援螢幕分享": "This browser does not support screen sharing",
  "語音會議需要安全的 HTTPS 連線": "Voice meetings require a secure HTTPS connection",
  "麥克風權限被拒絕，請在瀏覽器或系統設定中允許後重試。": "Microphone access was denied. Allow it in browser or system settings, then retry.",
  "找不到可用的麥克風": "No microphone is available",
  "麥克風正被其他程式使用或無法讀取": "The microphone is busy or cannot be read",
  "鏡頭權限被拒絕，請在瀏覽器或系統設定中允許後重試。": "Camera access was denied. Allow it in browser or system settings, then retry.",
  "找不到可用的鏡頭": "No camera is available",
  "鏡頭正被其他程式使用或無法讀取": "The camera is busy or cannot be read",
  "螢幕分享權限被拒絕或已取消": "Screen sharing was denied or cancelled",
  "找不到可分享的螢幕或視窗": "No screen or window is available to share",
  "螢幕擷取無法啟動，請檢查系統隱私設定。": "Screen capture could not start. Check system privacy settings.",
  "會議連線失敗，請稍後重試": "Could not connect to the meeting. Try again shortly.",
  "會議連線已過期，請重新加入。": "The meeting connection expired. Join again.",
  "會議功能已更新，請重新整理頁面後再加入": "Meeting features were updated. Reload the page before joining.",
  "語音會議服務目前無法使用，請稍後再試。": "Voice meetings are currently unavailable. Try again later.",
  "會議已達六人上限": "This meeting has reached its six-person limit",
  "已靜音": "Muted",
  "分享中": "Sharing",
  "目前沒有訊息": "No messages yet",
  "訊息載入失敗，將稍後重試。": "Messages could not be loaded. Retrying shortly.",
  "協作操作失敗": "Collaboration action failed",
  "協作負責人": "Owner",
  "協作者": "Collaborator",
  "邀請中": "Invited",
  "共編": "Co-edit",
  "協作工作稿": "Shared working draft",
  "所有協作者可在同一份工作稿中安全共編。": "Everyone in the workspace can safely co-edit the same working draft.",
  "編輯": "Edit",
  "預覽": "Preview",
  "視覺共編": "Visual co-editing",
  "原文": "Source",
  "回到視覺共編": "Back to visual co-editing",
  "格式": "Format",
  "正文": "Body",
  "一級標題": "Heading 1",
  "二級標題": "Heading 2",
  "粗體": "Bold",
  "斜體": "Italic",
  "貼上的粗體、標題、清單與表格會安全轉換。": "Pasted bold text, headings, lists, and tables are converted safely.",
  "插入圖片": "Insert image",
  "插入表格": "Insert table",
  "插入公式": "Insert formula",
  "公式": "Formula",
  "公式內容": "Formula source",
  "智能格式": "Smart format",
  "新增一列": "Add row",
  "刪除末列": "Remove last row",
  "新增一欄": "Add column",
  "刪除末欄": "Remove last column",
  "刪除表格": "Remove table",
  "刪除公式": "Remove formula",
  "刪除圖片": "Remove image",
  "可編輯表格": "Editable table",
  "欄位": "Column",
  "內容": "Content",
  "字體": "Type",
  "文件字體": "Document type",
  "瑞士無襯線": "Swiss Sans",
  "編輯襯線": "Editorial Serif",
  "技術等寬": "Technical Mono",
  "小": "Small",
  "標準": "Standard",
  "舒展": "Reading",
  "圖片上傳中": "Uploading image",
  "圖片上傳失敗": "Image upload failed",
  "圖片": "Image",
  "已保存圖片": "Saved images",
  "圖片預覽已達上限": "Image preview limit reached",
  "圖片已安全保存，但未能插入工作稿；可從已保存圖片重新插入。": "The image was saved securely but could not be inserted. Reinsert it from Saved images.",
  "只支援 PNG、JPEG 或 WebP 圖片，最大 2MB。": "PNG, JPEG, or WebP only, up to 2 MB.",
  "圖片無法載入": "Image could not be loaded",
  "安全圖文預覽": "Safe rich preview",
  "預覽內容較長，請在編輯模式查看其餘內容。": "This draft is long. Switch to edit mode to view the rest.",
  "匯出": "Export",
  "工作稿尚未有內容": "The working draft is empty",
  "開始整理共同目標、決定與下一步。": "Start capturing shared goals, decisions, and next steps.",
  "輸入協作工作稿": "Write in the shared working draft",
  "工作稿已同步": "Draft synced",
  "正在同步工作稿": "Syncing draft",
  "等待同步": "Waiting to sync",
  "唯讀模式": "Read-only",
  "工作稿載入失敗": "Could not load the working draft",
  "工作稿同步失敗，已保留在此裝置。": "Sync failed; the draft remains saved on this device.",
  "工作稿連線逾時，將稍後重試。": "The draft request timed out. It will retry shortly.",
  "工作稿已在另一處更新，正在合併。": "The draft changed elsewhere; merging updates.",
  "此任務已結束，工作稿已鎖定。重新進行任務後可繼續編輯。": "This task is closed and its draft is locked. Reopen the task to continue editing.",
  "觀察者可閱讀工作稿，但不能修改。": "Observers can read the draft but cannot edit it.",
  "本機儲存空間不足，請先保持此頁開啟並重新連線。": "Local storage is full. Keep this page open and reconnect before leaving.",
  "工作稿最多 32000 個字": "The working draft is limited to 32,000 characters",
  "工作稿包含無效字元": "The working draft contains an invalid character",
  "偵測到無法讀取的本機工作稿；原始資料已保留且不會自動載入。": "An unreadable local draft was detected. Its original data was preserved and will not be loaded automatically.",
  "即時連線": "Live",
  "正在連線": "Connecting",
  "正在重新連線": "Reconnecting",
  "即時連線中斷，改用定期同步": "Live connection interrupted; using periodic sync",
  "目前離線，草稿已保留": "You are offline; your draft is preserved",
  "人在線": "online",
  "在線": "Online",
  "離線": "Offline",
  "狀態未知": "Status unknown",
  "正在輸入訊息": "typing",
  "查看新訊息": "View new messages",
  "則新訊息": "new messages",
  "聊天訊息": "Chat messages",
  "人參與": "members",
  "查看任務協作": "View task collaboration",
  "重新整理協作": "Refresh collaboration",
  "確定離開此協作？": "Leave this collaboration?",
  "貢獻者": "Contributor",
  "審閱者": "Reviewer",
  "觀察者": "Observer",
  "協調員": "Coordinator",
  "角色": "Role",
});

const BIU_TASK_COPY = Object.freeze({
  "任務": "工作事項", "新增任務": "新增工作事項", "建立任務": "建立工作事項",
  "任務與計劃": "程序計畫", "個人行動中心": "案件工作中心",
  "今天": "今日工作", "收件匣": "工作清單", "日曆": "程序日曆", "計劃": "程序計畫", "透視": "工作分析",
  "所有與你相關的操作、安排與檔案跟進，都在同一條時間線。": "案件程序中的個人工作、日程與卷宗跟進，統一顯示在同一條時間線。",
  "管理任務、日程與部門計劃，並保留與原始檔案的關聯。": "管理工作事項、程序日程與程序計畫，並保留與案件卷宗的關聯。",
});
const taskText = (biu, value) => t(biu ? (BIU_TASK_COPY[value] || value) : value);

const arr = value => Array.isArray(value) ? value : [];
const obj = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
const first = (...values) => values.find(value => value !== undefined && value !== null && value !== "");
const optionalText = (...values) => String(first(...values) ?? "");
const key = value => String(value == null ? "" : value).trim().toLowerCase();
const pad = value => String(value).padStart(2, "0");
const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
const dateObject = value => {
  if (!value) return null;
  let date;
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const parts = value.split("-").map(Number);
    date = new Date(parts[0], parts[1] - 1, parts[2], 12, 0, 0);
  } else date = value instanceof Date ? new Date(value.getTime()) : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
};
const dateKey = value => {
  const date = dateObject(value);
  return date ? `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` : "";
};
const todayKey = () => dateKey(new Date());
const addDays = (value, amount) => {
  const date = dateObject(value) || new Date();
  date.setDate(date.getDate() + amount);
  return date;
};
const dayDiff = value => {
  const date = dateObject(value);
  if (!date) return null;
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const now = new Date();
  const base = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  return Math.round((target - base) / 86400000);
};
const coversDay = (task, token) => {
  const start = dateKey(task && (task.start || task.due));
  const end = dateKey(task && (task.due || task.start));
  if (!start && !end) return false;
  const lower = start || end;
  const upper = end && end >= lower ? end : lower;
  return token >= lower && token <= upper;
};
const locale = () => ({ tw: "zh-TW", cn: "zh-CN", en: "en-US" }[window.W2_LANG.lang()] || "zh-TW");
const dayLabel = value => {
  const date = dateObject(value);
  if (!date) return t("無排程");
  return new Intl.DateTimeFormat(locale(), { month: "short", day: "numeric", weekday: "short" }).format(date);
};
const timeLabel = (value, allDay) => {
  const date = dateObject(value);
  if (!date) return "—";
  if (allDay) return t("全天");
  return new Intl.DateTimeFormat(locale(), { hour: "2-digit", minute: "2-digit", hour12: false }).format(date);
};
const monthLabel = value => new Intl.DateTimeFormat(locale(), { year: "numeric", month: "long" }).format(value);
const inputDate = value => dateKey(value);
const inputTime = value => {
  const date = dateObject(value);
  return date ? `${pad(date.getHours())}:${pad(date.getMinutes())}` : "09:00";
};
const toISO = (day, time, allDay, endOfDay) => {
  if (!day) return null;
  const parts = day.split("-").map(Number);
  const clock = allDay ? (endOfDay ? [23, 59] : [0, 0]) : String(time || "09:00").split(":").map(Number);
  const date = new Date(parts[0], parts[1] - 1, parts[2], clock[0] || 0, clock[1] || 0, endOfDay && allDay ? 59 : 0);
  return date.toISOString();
};
const isTerminal = status => ["completed", "cancelled"].includes(status);
const canonicalStatus = value => ({
  todo: "planned", open: "planned", pending: "planned", assigned: "planned", scheduled: "planned", planned: "planned",
  active: "active", doing: "active", in_progress: "active", started: "active",
  paused: "paused", waiting: "paused", blocked: "paused", on_hold: "paused",
  completed: "completed", complete: "completed", done: "completed", closed: "completed",
  cancelled: "cancelled", canceled: "cancelled",
}[key(value)] || key(value) || "planned");
const actionStatus = value => {
  const normalized = key(value);
  if (["start", "resume", "activate", "in_progress"].includes(normalized)) return "active";
  if (["pause", "wait", "waiting", "hold"].includes(normalized)) return "paused";
  if (["complete", "completed", "done", "close"].includes(normalized)) return "completed";
  if (["cancel", "cancelled", "canceled"].includes(normalized)) return "cancelled";
  const mapped = canonicalStatus(normalized);
  return ["planned", "active", "paused", "completed", "cancelled"].includes(mapped) ? mapped : "";
};
const statusLabel = status => ({ planned: "待開始", active: "進行中", paused: "已暫停", completed: "已完成", cancelled: "已取消" }[status] || status);
const statusTone = status => ({ planned: "plan", active: "active", paused: "pause", completed: "done", cancelled: "cancel" }[status] || "plan");
const priorityValue = value => {
  const normalized = key(value);
  if (["urgent", "critical", "p0", "0"].includes(normalized)) return "urgent";
  if (["high", "p1", "1"].includes(normalized)) return "high";
  if (["low", "p3", "3"].includes(normalized)) return "low";
  return "normal";
};
const priorityLabel = value => ({ urgent: "緊急", high: "高", normal: "普通", low: "低" }[value] || value);
const categoryLabel = (value, biu = false) => {
  const normalized = key(value);
  if (biu) return ({ meeting: "程序會議", travel: "程序日程", exam: "資格考核", work: "案件工作", personal: "個人研修", record: "卷宗整理", other: "倫理研究" }[normalized] || "倫理研究");
  return ({ meeting: "會議", travel: "出差", exam: "考試", work: "工作", personal: "個人", record: "檔案", other: "其他" }[normalized] || value || "其他");
};
const kindValue = task => {
  const value = key(first(task.kind, task.task_kind, task.task_type, task.type, task.category));
  if (["event", "calendar", "calendar_event", "meeting", "travel", "exam"].includes(value)) return "event";
  if (["plan", "project", "milestone"].includes(value)) return "plan";
  return "task";
};
const tasksFrom = data => {
  if (Array.isArray(data)) return data;
  const source = obj(data);
  return arr(first(source.tasks, source.items, source.results, source.data));
};
const taskFrom = data => {
  const source = obj(data);
  return obj(first(source.task, source.item, source.result, source.data, source));
};
const normalizeTask = rawValue => {
  const raw = obj(rawValue);
  const sourceValue = first(raw.source, raw.linked_entity, raw.origin, {});
  const source = obj(sourceValue);
  const assignee = obj(first(raw.assignee, arr(raw.assignees)[0], raw.owner, raw.responsible_user, {}));
  const plan = obj(first(raw.plan, raw.parent_plan, {}));
  const start = first(raw.starts_at, raw.start_at, raw.scheduled_start, raw.planned_start, raw.start_date);
  const due = first(raw.due_at, raw.ends_at, raw.end_at, raw.scheduled_end, raw.planned_end, raw.due_date, raw.end_date, start);
  const sourceType = optionalText(raw.source_type, typeof sourceValue === "string" ? sourceValue : null, source.type);
  const implicitSourceRef = typeof sourceValue === "string" && raw.source_id != null ? `${sourceValue}:${raw.source_id}` : "";
  const explicitSourceRef = optionalText(raw.source_ref, raw.source_entity_ref, raw.entity_ref, source.entity_ref, source.ref);
  const sourceRef = explicitSourceRef || (["task", "native", "personal"].includes(key(sourceType)) ? "" : implicitSourceRef);
  const capabilities = obj(raw.capabilities);
  const actions = arr(first(raw.allowed_actions, raw.actions, capabilities.actions))
    .map(action => actionStatus(typeof action === "object" ? first(action.status, action.target_status, action.action, action.key) : action))
    .filter(Boolean);
  const lockVersion = first(raw.lock_version, raw.version);
  return {
    raw,
    id: first(raw.id, raw.task_id, raw.uuid, raw.key),
    title: optionalText(raw.title, raw.task_name, raw.name, raw.summary, t("未命名")),
    description: optionalText(raw.description, raw.notes, raw.detail, raw.details),
    kind: kindValue(raw), category: key(first(raw.category, "other")), status: canonicalStatus(raw.status), priority: priorityValue(raw.priority),
    visibility: key(first(raw.visibility, raw.scope, "private")),
    start, due, allDay: raw.all_day === true || raw.is_all_day === true,
    timezone: optionalText(raw.timezone) || "UTC",
    location: optionalText(raw.location),
    ownerOrgUnitId: first(raw.owner_org_unit_id, raw.org_unit_id),
    assigneeId: first(raw.assignee_user_id, raw.assignee_id, assignee.id, assignee.user_id),
    assigneeName: optionalText(raw.assignee_name, raw.assignee_user_name, assignee.display_name, assignee.name, assignee.username),
    creatorName: optionalText(raw.creator_name, raw.created_by_name, raw.reporter_name),
    planId: first(raw.plan_id, raw.parent_plan_id, plan.id, plan.plan_id),
    planTitle: optionalText(raw.plan_title, raw.plan_name, plan.title, plan.name),
    sourceRef,
    sourceTitle: optionalText(raw.source_title, raw.source_name, source.title, source.name),
    sourceType,
    completedAt: first(raw.completed_at, raw.closed_at),
    progress: clamp(number(first(raw.progress, raw.progress_percent, 0)), 0, 100),
    actions,
    lockVersion,
    canUpdate: raw.read_only !== true && (raw.can_update === true || capabilities.can_update === true) && lockVersion != null,
    canDelete: raw.read_only !== true && (raw.can_delete === true || capabilities.can_delete === true) && lockVersion != null,
    canStatus: raw.read_only !== true && (raw.can_status === true || capabilities.can_change_status === true || capabilities.can_update === true) && lockVersion != null,
    canReopen: raw.read_only !== true && (raw.can_reopen === true || capabilities.can_reopen === true) && lockVersion != null,
  };
};
const uniqueTasks = values => {
  const seen = new Set();
  return values.filter(task => {
    const token = String(first(task.id, `${task.title}|${task.start}|${task.due}`));
    if (seen.has(token)) return false;
    seen.add(token); return true;
  });
};
const usersFromMeta = meta => arr(first(meta.users, meta.assignees, obj(meta.options).assignees, obj(meta.data).users));
const plansFromMeta = meta => arr(first(meta.plans, obj(meta.options).plans, obj(meta.data).plans));
const orgUnitsFromMeta = meta => arr(first(meta.org_units, meta.owner_org_units, obj(meta.options).org_units, obj(meta.data).org_units));
const capabilitiesFromMeta = meta => obj(first(meta.capabilities, obj(meta.data).capabilities, meta.permissions));
const clientRequestId = () => {
  try { if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID(); } catch (error) {}
  return `task-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};
const idValue = value => /^\d+$/.test(String(value || "")) ? Number(value) : (value || null);
const sourceParts = value => {
  const match = String(value || "").match(/^([a-z][a-z0-9_-]*):(.+)$/i);
  if (!match) return { type: null, id: null };
  return { type: match[1].toLowerCase(), id: /^\d+$/.test(match[2]) ? Number(match[2]) : match[2] };
};

/* Collaboration failures stay local to the workspace UI. The backend uses
   403/404 for scoped denials, while W2 still owns genuine session expiry. */
const collabJson = (path, options = {}) => W2.json(path, options);
const collabPost = (path, body = {}) => W2.post(path, body);
const collabData = value => obj(first(obj(value).data, value));
const collabWorkspace = value => obj(first(
  collabData(value).space,
  collabData(value).workspace,
  collabData(value).collaboration,
  obj(collabData(value).task).collaboration
));
const collabMembers = value => arr(first(
  collabData(value).members,
  collabWorkspace(value).members,
  collabData(value).participants
));
const collabRequests = value => arr(first(
  collabData(value).join_requests,
  collabData(value).pending_requests,
  collabData(value).requests,
  collabWorkspace(value).join_requests
));
const collabInvitations = value => {
  const data = collabData(value);
  const collection = arr(first(data.invitations, data.pending_invitations, collabWorkspace(value).invitations));
  if (collection.length) return collection;
  const invitation = obj(first(data.invitation, collabWorkspace(value).invitation));
  return Object.keys(invitation).length ? [invitation] : [];
};
const collabMessages = value => arr(first(
  collabData(value).items,
  collabData(value).messages,
  obj(collabData(value).channel).messages
));
const collabTask = value => obj(first(
  collabData(value).task,
  collabWorkspace(value).task,
  obj(collabData(value).item).task
));
const collabTaskId = value => first(
  collabTask(value).id,
  collabTask(value).task_id,
  collabData(value).task_id,
  collabWorkspace(value).task_id
);
const collabDisplayName = (value, fallback = "") => optionalText(
  obj(value).display_name,
  obj(value).name,
  obj(value).username,
  obj(value).user_name,
  obj(value).email,
  fallback
);
const collabViewer = value => obj(first(
  collabData(value).membership,
  collabWorkspace(value).membership,
  collabData(value).viewer,
  collabWorkspace(value).viewer
));
const collabCapabilities = value => ({
  ...obj(collabWorkspace(value).capabilities),
  ...obj(collabData(value).capabilities),
  ...obj(collabViewer(value).capabilities),
});
const collabCan = (value, name) => collabCapabilities(value)[name] === true;
const collabStatus = value => key(first(
  collabViewer(value).status,
  collabViewer(value).state,
  collabData(value).membership_status,
  collabWorkspace(value).membership_status
));
const collabMemberId = value => first(
  obj(value).user_id,
  obj(value).member_user_id,
  obj(value).id
);
const collabMessageId = value => number(first(obj(value).id, obj(value).message_id));
const collabCollection = value => arr(first(
  collabData(value).items,
  collabData(value).workspaces,
  collabData(value).collaborations,
  collabData(value).tasks,
  collabData(value).results
));
const normalizeCollabCard = rawValue => {
  const raw = obj(rawValue);
  const task = obj(first(raw.task, raw.task_summary));
  const workspace = obj(first(raw.space, raw.workspace, raw.collaboration));
  return {
    raw,
    spaceId: first(workspace.id, workspace.space_id, raw.space_id),
    id: first(task.id, task.task_id, raw.task_id, workspace.task_id),
    title: optionalText(task.title, raw.task_title, raw.title, t("未命名")),
    description: optionalText(task.description, raw.task_description, raw.description),
    owner: collabDisplayName(first(raw.owner, workspace.owner, task.owner), ""),
    discoverability: key(first(workspace.discoverability, raw.discoverability, "company")),
    joinPolicy: key(first(workspace.join_policy, raw.join_policy, "request")),
    memberCount: number(first(workspace.member_count, raw.member_count, arr(workspace.members).length)),
    relation: key(first(raw.relation, raw.membership_status, raw.viewer_status)),
  };
};
const collabCardIdentity = item => optionalText(obj(item).id, obj(item).spaceId);
const uniqueCollabCards = values => {
  const seen = new Set();
  return arr(values).filter(item => {
    const identity = collabCardIdentity(item);
    if (!identity || seen.has(identity)) return false;
    seen.add(identity);
    return true;
  });
};
const collabScopeLabel = value => ({
  company: "公司可見", team: "團隊可見", hidden: "隱藏",
}[key(value)] || "公司可見");
const collabJoinLabel = value => ({
  open: "自由加入", request: "申請審批", invite_only: "僅限邀請",
}[key(value)] || "申請審批");
const collabRoleLabel = value => ({
  owner: "協作負責人", contributor: "貢獻者", reviewer: "審閱者",
  observer: "觀察者", coordinator: "協調員",
}[key(value)] || "協作者");
const collabTime = value => {
  const date = dateObject(value);
  if (!date) return "";
  return new Intl.DateTimeFormat(locale(), {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  }).format(date);
};

const COLLAB_REALTIME_STATES = Object.freeze({
  IDLE: "idle",
  CONNECTING: "connecting",
  LIVE: "live",
  RETRYING: "retrying",
  FALLBACK: "fallback",
  OFFLINE: "offline",
});
const COLLAB_REALTIME_TYPES = new Set([
  "ready", "message.created", "workspace.changed", "task.status.changed", "document.updated", "presence.changed",
  "heartbeat", "reconnect", "access.revoked", "resync", "resync.required",
  "rtc.room.snapshot", "rtc.signal",
]);
const COLLAB_MEETING_STATES = Object.freeze({
  IDLE: "idle",
  ACQUIRING: "acquiring",
  JOINING: "joining",
  CONNECTED: "connected",
  RECONNECTING: "reconnecting",
  LEAVING: "leaving",
  ERROR: "error",
});
const COLLAB_MEETING_MAX_PARTICIPANTS = 6;
const COLLAB_MEETING_MEDIA_PROTOCOL = "camera-screen-v2";
const COLLAB_MEETING_ACK_DEBOUNCE_MS = 250;
const COLLAB_MEETING_ACK_RETRY_DELAYS = Object.freeze([750, 2000, 5000]);
const COLLAB_MEETING_ACK_COMPLETION_LIMIT = 128;
const COLLAB_MEETING_SIGNAL_RETRY_DELAYS = Object.freeze([250, 750]);
const COLLAB_MEETING_SIGNAL_REPLAY_DELAYS = Object.freeze([750, 2000, 5000, 10000]);
const COLLAB_MEETING_RTC_REFRESH_RETRY_DELAYS = Object.freeze([1000, 3000, 7000]);
const COLLAB_MEETING_RTC_REFRESH_RATIO = 0.5;
const COLLAB_MEETING_RTC_REFRESH_REQUEST_TIMEOUT_MS = 10000;
const COLLAB_MEETING_RTC_TTL_MIN_SECONDS = 60;
const COLLAB_MEETING_RTC_TTL_MAX_SECONDS = 14400;
const COLLAB_MEETING_LEAVE_TIMEOUT_MS = 3000;
const COLLAB_CHAT_PAGE_LIMIT = 100;
const COLLAB_CHAT_DRAIN_PAGES = 10;
const COLLAB_CHAT_RETAINED_MESSAGES = 1000;
const COLLAB_CHAT_CONTINUE_DELAY = 25;
const collabRealtimeType = value => key(first(obj(value).event, obj(value).type));
const collabRealtimePayload = value => obj(first(obj(value).payload, obj(value).data, value));
const collabRealtimeEventId = value => number(first(
  obj(value).event_id,
  obj(value).sequence,
  obj(value).id,
  obj(value).event_cursor,
  collabRealtimePayload(value).event_id,
  collabRealtimePayload(value).sequence,
  collabRealtimePayload(value).event_cursor
));
const collabRealtimeCursor = value => first(
  obj(value).event_cursor,
  collabRealtimePayload(value).event_cursor
);
const collabRealtimeTaskId = value => first(
  obj(value).task_id,
  collabRealtimePayload(value).task_id
);
const collabRtcSignalCursor = value => number(first(
  obj(value).signal_id,
  obj(value).signal_cursor,
  collabRealtimePayload(value).signal_id,
  collabRealtimePayload(value).signal_cursor
));
const collabDocumentSequence = value => number(first(
  collabRealtimePayload(value).document_sequence,
  collabRealtimePayload(value).latest_sequence,
  collabRealtimePayload(value).sequence
));
const collabPresenceEntries = value => {
  const payload = collabRealtimePayload(value);
  const collection = arr(first(payload.presence, payload.members, payload.users));
  const typingIds = new Set(arr(payload.typing_user_ids).map(userId => String(userId)));
  if (collection.length) return collection.map(item => {
    const entry = obj(item);
    const user = obj(first(entry.user, entry.member, entry.profile));
    const userId = first(entry.user_id, entry.member_user_id, user.user_id, user.id);
    return { ...entry, typing: entry.typing === true || (userId != null && typingIds.has(String(userId))) };
  });
  const candidate = obj(first(payload.presence, payload.member, payload.user));
  if (Object.keys(candidate).length) return [{ ...payload, user: candidate }];
  return first(payload.user_id, payload.member_user_id) != null ? [payload] : [];
};
const normalizeCollabPresence = (value, now = Date.now()) => {
  const item = obj(value);
  const user = obj(first(item.user, item.member, item.profile));
  const userId = first(item.user_id, item.member_user_id, user.user_id, user.id);
  if (userId == null) return null;
  const state = key(first(item.state, item.presence_state, item.status, "active"));
  return {
    userId: String(userId),
    displayName: collabDisplayName(first(user, item), ""),
    state: ["offline", "left", "inactive"].includes(state) ? "offline" : "active",
    typing: item.typing === true,
    expiresAt: now + 45000,
    typingExpiresAt: item.typing === true ? now + 7000 : 0,
  };
};
const collabRealtimeLabel = (state, onlineCount = 0) => {
  if (state === COLLAB_REALTIME_STATES.LIVE) return t("即時連線") + " · " + onlineCount + " " + t("人在線");
  if (state === COLLAB_REALTIME_STATES.CONNECTING) return t("正在連線");
  if (state === COLLAB_REALTIME_STATES.RETRYING) return t("正在重新連線");
  if (state === COLLAB_REALTIME_STATES.FALLBACK) return t("即時連線中斷，改用定期同步");
  if (state === COLLAB_REALTIME_STATES.OFFLINE) return t("目前離線，草稿已保留");
  return "";
};

const useCollaborationRealtime = ({ taskId, tenant, enabled }) => {
  const [transport, setTransport] = S(COLLAB_REALTIME_STATES.IDLE);
  const [presence, setPresence] = S({});
  const [messageSignal, setMessageSignal] = S(0);
  const [workspaceSignal, setWorkspaceSignal] = S(0);
  const [documentSignal, setDocumentSignal] = S(0);
  const [documentSequence, setDocumentSequence] = S(0);
  const [restartSignal, setRestartSignal] = S(0);
  const [networkOnline, setNetworkOnline] = S(() => !window.navigator || window.navigator.onLine !== false);
  const generation = R(0);
  const controller = R(null);
  const reader = R(null);
  const retryTimer = R(null);
  const watchdogTimer = R(null);
  const failures = R(0);
  const lastEventId = R(0);
  const lastSignalId = R(0);
  const blocked = R(false);
  const selfTyping = R(false);
  const clientId = R(clientRequestId());
  const rtcListeners = R(new Set());
  const realtimeContext = R({ taskId, tenant });
  realtimeContext.current = { taskId, tenant };
  E(() => {
    lastEventId.current = 0;
    lastSignalId.current = 0;
    setDocumentSequence(0);
  }, [taskId, tenant]);

  const contextMatches = C(() => (
    enabled && taskId != null && tenant === W2.tenant()
  ), [enabled, taskId, tenant]);
  const subscribeRtc = C(listener => {
    if (typeof listener !== "function") return () => {};
    rtcListeners.current.add(listener);
    return () => rtcListeners.current.delete(listener);
  }, []);
  const setRtcSignalCursor = C(value => {
    lastSignalId.current = Math.max(0, number(value));
    setRestartSignal(current => current + 1);
  }, []);
  const confirmRtcSignalCursor = C(value => {
    const cursor = number(value);
    if (!Number.isSafeInteger(cursor) || cursor < 0) return false;
    lastSignalId.current = Math.max(lastSignalId.current, cursor);
    return true;
  }, []);

  const updatePresence = C((event, replace = false) => {
    const now = Date.now();
    const entries = collabPresenceEntries(event)
      .map(item => normalizeCollabPresence(item, now))
      .filter(Boolean);
    setPresence(current => {
      const next = replace ? {} : { ...current };
      entries.forEach(item => {
        if (item.state === "offline") delete next[item.userId];
        else next[item.userId] = item;
      });
      return next;
    });
  }, []);

  const clearTyping = C(() => {
    setPresence(current => {
      let changed = false;
      const next = { ...current };
      Object.entries(next).forEach(([userId, item]) => {
        if (!item.typing) return;
        next[userId] = { ...item, typing: false, typingExpiresAt: 0 };
        changed = true;
      });
      return changed ? next : current;
    });
  }, []);

  const refreshPresenceExpiry = C(() => {
    const expiresAt = Date.now() + 45000;
    setPresence(current => {
      const entries = Object.entries(current);
      if (!entries.length) return current;
      const next = {};
      entries.forEach(([userId, item]) => {
        next[userId] = { ...item, expiresAt };
      });
      return next;
    });
  }, []);

  const postPresence = C(async (
    state = "active",
    typing = false,
    { keepalive = false, suppressRevoke = false } = {}
  ) => {
    if (taskId == null || tenant !== W2.tenant()) return false;
    const requestGeneration = generation.current;
    const requestTaskId = taskId;
    const requestTenant = tenant;
    const invocationContext = realtimeContext.current;
    if (
      !suppressRevoke
      && (
        String(requestTaskId) !== String(invocationContext.taskId)
        || requestTenant !== invocationContext.tenant
      )
    ) return false;
    selfTyping.current = state === "active" && typing === true;
    try {
      const response = await W2.fetch("/api/tasks/" + encodeURIComponent(taskId) + "/collaboration/presence", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId.current, state, typing: typing === true }),
        keepalive,
      });
      const currentContext = realtimeContext.current;
      const responseMatchesContext = (
        requestGeneration === generation.current
        && String(requestTaskId) === String(currentContext.taskId)
        && requestTenant === currentContext.tenant
        && requestTenant === W2.tenant()
      );
      if (
        !suppressRevoke
        && responseMatchesContext
        && (response.status === 403 || response.status === 404)
      ) {
        blocked.current = true;
        if (controller.current) controller.current.abort();
        setPresence({});
        setWorkspaceSignal(current => current + 1);
      }
      return response.ok;
    } catch (error) {
      return false;
    }
  }, [taskId, tenant]);

  E(() => {
    const online = () => setNetworkOnline(true);
    const offline = () => setNetworkOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);

  E(() => {
    if (!enabled) return undefined;
    const timer = window.setInterval(() => {
      const now = Date.now();
      setPresence(current => {
        let changed = false;
        const next = {};
        Object.entries(current).forEach(([userId, item]) => {
          if (item.expiresAt <= now) { changed = true; return; }
          if (item.typing && item.typingExpiresAt <= now) {
            next[userId] = { ...item, typing: false, typingExpiresAt: 0 };
            changed = true;
          } else next[userId] = item;
        });
        return changed ? next : current;
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [enabled]);

  E(() => {
    const currentGeneration = ++generation.current;
    blocked.current = false;
    failures.current = 0;
    const valid = () => (
      generation.current === currentGeneration
      && enabled
      && taskId != null
      && tenant === W2.tenant()
      && !blocked.current
    );
    const clearConnection = () => {
      const ownedRetryTimer = retryTimer.current;
      const ownedWatchdog = watchdogTimer.current;
      const ownedReader = reader.current;
      const ownedController = controller.current;
      if (ownedRetryTimer != null && retryTimer.current === ownedRetryTimer) {
        window.clearTimeout(ownedRetryTimer);
        retryTimer.current = null;
      }
      if (ownedWatchdog != null && watchdogTimer.current === ownedWatchdog) {
        window.clearTimeout(ownedWatchdog);
        watchdogTimer.current = null;
      }
      if (ownedReader && reader.current === ownedReader) {
        reader.current = null;
        ownedReader.cancel().catch(() => {});
      }
      if (ownedController && controller.current === ownedController) {
        controller.current = null;
        ownedController.abort();
      }
    };
    if (!enabled || taskId == null) {
      setTransport(COLLAB_REALTIME_STATES.IDLE);
      setPresence({});
      return () => { generation.current += 1; clearConnection(); };
    }
    if (!networkOnline) {
      setTransport(COLLAB_REALTIME_STATES.OFFLINE);
      clearTyping();
      return () => { generation.current += 1; clearConnection(); };
    }

    let disposed = false;
    const schedule = (delay, preserveLive = false) => {
      if (!valid() || disposed) return;
      retryTimer.current = window.setTimeout(() => connect(preserveLive), delay);
    };
    const connect = async (preserveLive = false) => {
      if (!valid() || disposed) return;
      if (!preserveLive && failures.current < 1) setTransport(COLLAB_REALTIME_STATES.CONNECTING);
      const streamController = new AbortController();
      controller.current = streamController;
      const startedAt = Date.now();
      let ready = false;
      let plannedReconnect = false;
      let reconnectDelay = 0;
      let accessRevoked = false;
      let buffer = "";
      let localReader = null;
      let localWatchdog = null;
      const clearLocalWatchdog = () => {
        if (localWatchdog == null) return;
        window.clearTimeout(localWatchdog);
        if (watchdogTimer.current === localWatchdog) watchdogTimer.current = null;
        localWatchdog = null;
      };
      const armWatchdog = (timeout = 65000) => {
        clearLocalWatchdog();
        localWatchdog = window.setTimeout(() => streamController.abort(), timeout);
        watchdogTimer.current = localWatchdog;
      };
      const handleEvent = event => {
        if (!valid() || disposed) return "stop";
        const type = collabRealtimeType(event);
        if (!COLLAB_REALTIME_TYPES.has(type)) return "continue";
        const eventTaskId = collabRealtimeTaskId(event);
        if (eventTaskId != null && String(eventTaskId) !== String(taskId)) return "continue";
        const eventId = collabRealtimeEventId(event);
        const serverCursor = collabRealtimeCursor(event);
        const serverAuthoritativeCursor = type === "ready"
          || type === "resync"
          || type === "resync.required";
        if (serverAuthoritativeCursor && serverCursor != null && serverCursor !== "") {
          lastEventId.current = Math.max(0, number(serverCursor));
        } else if (eventId > 0) {
          lastEventId.current = Math.max(lastEventId.current, eventId);
        }
        if (type === "ready") {
          ready = true;
          failures.current = 0;
          setTransport(COLLAB_REALTIME_STATES.LIVE);
          updatePresence(event, true);
          postPresence("active", selfTyping.current).catch(() => {});
          rtcListeners.current.forEach(listener => {
            try { listener(event); } catch (ignored) {}
          });
        } else if (type === "message.created") {
          setMessageSignal(current => current + 1);
        } else if (type === "document.updated") {
          const sequence = collabDocumentSequence(event);
          if (sequence > 0) setDocumentSequence(current => Math.max(current, sequence));
          else setDocumentSignal(current => current + 1);
        } else if (type === "workspace.changed" || type === "task.status.changed") {
          setWorkspaceSignal(current => current + 1);
          if (type === "task.status.changed") setDocumentSignal(current => current + 1);
        } else if (type === "presence.changed") {
          updatePresence(event, true);
        } else if (type === "rtc.room.snapshot" || type === "rtc.signal") {
          rtcListeners.current.forEach(listener => {
            try { listener(event); } catch (ignored) {}
          });
        } else if (type === "heartbeat") {
          refreshPresenceExpiry();
          if (collabPresenceEntries(event).length) updatePresence(event, false);
        } else if (type === "resync" || type === "resync.required") {
          setMessageSignal(current => current + 1);
          setWorkspaceSignal(current => current + 1);
          setDocumentSignal(current => current + 1);
        } else if (type === "access.revoked") {
          accessRevoked = true;
          blocked.current = true;
          setPresence({});
          setWorkspaceSignal(current => current + 1);
          setTransport(COLLAB_REALTIME_STATES.IDLE);
          clearTyping();
          rtcListeners.current.forEach(listener => {
            try { listener(event); } catch (ignored) {}
          });
          return "stop";
        } else if (type === "reconnect") {
          plannedReconnect = true;
          reconnectDelay = clamp(number(first(
            collabRealtimePayload(event).retry_after_ms,
            obj(event).retry_after_ms
          )), 0, 5000);
          return "reconnect";
        }
        return "continue";
      };
      try {
        armWatchdog(15000);
        const response = await W2.fetch(
          "/api/tasks/" + encodeURIComponent(taskId)
            + "/collaboration/events?after_event_id=" + encodeURIComponent(lastEventId.current)
            + "&after_signal_id=" + encodeURIComponent(lastSignalId.current)
            + "&client_id=" + encodeURIComponent(clientId.current),
          {
            headers: { Accept: "application/x-ndjson" },
            cache: "no-store",
            signal: streamController.signal,
          }
        );
        if (!valid() || disposed) return;
        if (!response.ok) {
          const failure = new Error(response.statusText || "realtime stream unavailable");
          failure.status = response.status;
          throw failure;
        }
        if (!response.body || typeof response.body.getReader !== "function") throw new Error("streaming response unavailable");
        localReader = response.body.getReader();
        reader.current = localReader;
        const decoder = new TextDecoder();
        armWatchdog();
        while (valid() && !disposed) {
          const chunk = await localReader.read();
          if (!valid() || disposed) break;
          if (chunk.done) break;
          armWatchdog();
          buffer += decoder.decode(chunk.value, { stream: true });
          if (buffer.length > 262144) throw new Error("realtime event buffer exceeded");
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) continue;
            let event;
            try { event = JSON.parse(line); } catch (error) { continue; }
            const action = handleEvent(event);
            if (action === "reconnect" || action === "stop") break;
          }
          if (plannedReconnect || accessRevoked) break;
        }
        clearLocalWatchdog();
        if (!valid() || disposed || accessRevoked) return;
        const boundedHandoff = ready && Date.now() - startedAt >= 45000;
        if (plannedReconnect || boundedHandoff) {
          schedule(plannedReconnect ? reconnectDelay : 0, true);
          return;
        }
        throw new Error("realtime stream ended early");
      } catch (error) {
        clearLocalWatchdog();
        if (!valid() || disposed || accessRevoked) return;
        if (error && error.status === 401) {
          blocked.current = true;
          setTransport(COLLAB_REALTIME_STATES.IDLE);
          return;
        }
        if (error && (error.status === 403 || error.status === 404)) {
          blocked.current = true;
          setPresence({});
          setTransport(COLLAB_REALTIME_STATES.IDLE);
          setWorkspaceSignal(current => current + 1);
          return;
        }
        failures.current += 1;
        clearTyping();
        const fallback = failures.current >= 3;
        setTransport(fallback ? COLLAB_REALTIME_STATES.FALLBACK : COLLAB_REALTIME_STATES.RETRYING);
        const base = Math.min(15000, 1000 * (2 ** Math.min(failures.current - 1, 4)));
        const jitter = Math.floor(Math.random() * Math.max(250, base * .35));
        schedule(base + jitter, false);
      } finally {
        clearLocalWatchdog();
        if (localReader) {
          try { localReader.releaseLock(); } catch (ignored) {}
          if (reader.current === localReader) reader.current = null;
          localReader = null;
        }
        if (controller.current === streamController) controller.current = null;
      }
    };
    connect(false);
    return () => {
      if (tenant === W2.tenant()) {
        postPresence("offline", false, {
          keepalive: true,
          suppressRevoke: true,
        }).catch(() => {});
      }
      selfTyping.current = false;
      disposed = true;
      generation.current += 1;
      clearConnection();
      setPresence({});
    };
  }, [enabled, taskId, tenant, networkOnline, restartSignal, updatePresence, clearTyping, refreshPresenceExpiry, postPresence]);

  E(() => {
    if (!enabled || transport !== COLLAB_REALTIME_STATES.LIVE) return undefined;
    postPresence("active", selfTyping.current).catch(() => {});
    const timer = window.setInterval(() => {
      postPresence("active", selfTyping.current).catch(() => {});
    }, 20000);
    return () => window.clearInterval(timer);
  }, [enabled, transport, postPresence]);

  const reconnect = C(() => {
    blocked.current = false;
    failures.current = 0;
    setNetworkOnline(!window.navigator || window.navigator.onLine !== false);
    setRestartSignal(current => current + 1);
  }, []);
  const sendTyping = C(active => {
    if (!contextMatches() || transport !== COLLAB_REALTIME_STATES.LIVE) return Promise.resolve(false);
    return postPresence("active", active === true);
  }, [contextMatches, transport, postPresence]);
  const onlineCount = transport === COLLAB_REALTIME_STATES.LIVE
    ? Object.values(presence).filter(item => item.state === "active" && item.expiresAt > Date.now()).length
    : 0;
  return {
    transport, presence, onlineCount, messageSignal, workspaceSignal, documentSignal, documentSequence,
    clientId: clientId.current, subscribeRtc, setRtcSignalCursor,
    confirmRtcSignalCursor,
    sendTyping, reconnect,
  };
};

const queryFromHash = () => {
  const raw = String(location.hash || "").split("?")[1] || "";
  try { return new URLSearchParams(raw); } catch (error) { return new URLSearchParams(); }
};
const composerHref = options => {
  const params = new URLSearchParams();
  params.set("view", options && options.view || "inbox");
  params.set("create", options && options.mode || "task");
  Object.entries(obj(options)).forEach(([name, value]) => {
    if (["view", "mode"].includes(name) || value == null || value === "") return;
    params.set(name, String(value));
  });
  return "#/tasks?" + params.toString();
};
W2.openTaskComposer = options => {
  const detail = obj(options);
  if ((location.hash || "").startsWith("#/tasks")) {
    window.dispatchEvent(new CustomEvent("w2-open-task-composer", { detail }));
    return;
  }
  location.hash = composerHref(detail);
};

const SourceMark = ({ task, biu = false }) => {
  if (!task.sourceRef && !task.sourceTitle) return null;
  const open = event => {
    event.stopPropagation();
    const parsed = W2.parseEntityRef && W2.parseEntityRef(task.sourceRef);
    if (parsed && parsed.type === "record") {
      location.hash = `#/cases?record=${encodeURIComponent(parsed.id)}`;
      return;
    }
    if (biu && parsed && parsed.type === "case") {
      location.hash = "#/cases";
      return;
    }
    if (parsed && parsed.type === "ai_confirmation_action" && W2.openSecretary) {
      W2.openSecretary("");
      return;
    }
    if (task.sourceRef && W2.openEntity && W2.openEntity(task.sourceRef)) return;
    const fallbackRoute = parsed && ({ alert: "alerts", work_task: "erp", wf_task: "procurement" }[parsed.type]);
    if (fallbackRoute) location.hash = `#/${fallbackRoute}`;
  };
  return <button type="button" className="task-source" onClick={open} disabled={!task.sourceRef} title={t("打開來源")}>
    <I name="doc" size={11}/><span>{task.sourceTitle || task.sourceRef}</span><I name="arrow" size={10}/>
  </button>;
};

const TaskCard = ({ task, onStatus, onEdit, onDelete, onCollaboration, busy, compact = false, biu = false }) => {
  const dueDiff = dayDiff(task.due);
  const overdue = !isTerminal(task.status) && dueDiff != null && dueDiff < 0;
  const dueToday = !isTerminal(task.status) && dueDiff === 0;
  const allowed = status => !task.actions.length || task.actions.includes(status);
  const options = (task.status === "planned" ? [["active", "立即開始"], ["paused", "等待"], ["completed", "完成"], ["cancelled", "取消任務"]]
    : task.status === "active" ? [["completed", "完成"], ["paused", "暫停"], ["cancelled", "取消任務"]]
    : task.status === "paused" ? [["active", "繼續"], ["completed", "完成"], ["cancelled", "取消任務"]]
    : task.status === "completed" && task.canReopen ? [["active", "重新進行"]] : []).filter(([status]) => allowed(status));
  const primary = options.find(([status]) => status === "completed") || options[0] || [];
  const next = primary[0] || "";
  const nextLabel = t(primary[1] || "");
  const alternatives = options.filter(option => option !== primary);
  return <article className={`task-card is-${statusTone(task.status)} priority-${task.priority}${compact ? " compact" : ""}`}>
    <div className="task-card-rule"/>
    <div className="task-card-main">
      <div className="task-card-meta">
        <span className={`task-status is-${statusTone(task.status)}`}><i/>{t(statusLabel(task.status))}</span>
        <span className="task-category">{t(categoryLabel(task.category, biu))}</span>
        {task.priority !== "normal" && <span className={`task-priority ${task.priority}`}>{t(priorityLabel(task.priority))}</span>}
        {overdue && <span className="task-deadline danger">{t("逾期")} {Math.abs(dueDiff)}D</span>}
        {dueToday && <span className="task-deadline">{t("今天截止")}</span>}
      </div>
      <h3>{task.title}</h3>
      {!compact && task.description && <p>{task.description}</p>}
      <div className="task-card-facts">
        <span><I name="clock" size={12}/>{task.start ? `${dayLabel(task.start)} · ${timeLabel(task.start, task.allDay)}` : t("無排程")}</span>
        {task.assigneeName && <span><I name="user" size={12}/>{task.assigneeName}</span>}
        {task.planTitle && <span><I name="layers" size={12}/>{task.planTitle}</span>}
      </div>
      <SourceMark task={task} biu={biu}/>
      {onCollaboration && task.id != null && task.lockVersion != null && <button type="button" className="task-collab-link" onClick={() => onCollaboration(task)}>
        <I name="user" size={12}/><span>{t("查看任務協作")}</span><I name="arrow" size={11}/>
      </button>}
    </div>
    {(!!options.length || task.canUpdate || task.canDelete) && <div className="task-card-actions">
      {next && <button type="button" className="task-action-primary" disabled={busy} onClick={() => onStatus(task, next)}>
        <I name={next === "completed" ? "check" : "arrow"} size={13}/>{busy ? "…" : nextLabel}
      </button>}
      {task.canUpdate && <button type="button" className="task-action-edit" disabled={busy} onClick={() => onEdit(task)}><I name="gear" size={13}/>{t("編輯")}</button>}
      {(!!alternatives.length || task.canDelete) && <details className="task-action-more"><summary aria-label={t("更多狀態")}>•••</summary><div>{alternatives.map(([status, label]) => <button type="button" key={status} disabled={busy} onClick={() => onStatus(task, status)}>{t(label)}</button>)}{task.canDelete && <button type="button" className="danger" disabled={busy} onClick={() => onDelete(task)}>{t("刪除任務")}</button>}</div></details>}
    </div>}
  </article>;
};

const ViewEmpty = ({ view, onCreate }) => {
  const copy = view === "today"
    ? ["clock", "今日沒有排定任務", "把下一個行動放進今天，或從檔案建立跟進。"]
    : view === "plans" ? ["layers", "沒有計劃", "用計劃把多個任務組成一段可追蹤的工作。"]
    : ["clipboard", "沒有符合條件的任務", "所有與你相關的操作、安排與檔案跟進，都在同一條時間線。"];
  return <Empty icon={copy[0]} title={t(copy[1])} sub={t(copy[2])} action={onCreate ? <B kind="primary" icon="plus" onClick={onCreate}>{t("新增")}</B> : null}/>;
};

const TodayView = ({ tasks, onStatus, onEdit, onDelete, onCollaboration, busyId, onCreate, onViewAll, biu = false }) => {
  const today = todayKey();
  const scheduled = tasks.filter(task => coversDay(task, today));
  const overdue = tasks.filter(task => !isTerminal(task.status) && dateKey(task.due) && dateKey(task.due) < today);
  const visible = uniqueTasks([...overdue, ...scheduled]).sort((a, b) => String(a.start || a.due || "").localeCompare(String(b.start || b.due || "")));
  const open = visible.filter(task => !isTerminal(task.status)).length;
  const completed = visible.filter(task => task.status === "completed").length;
  const rate = visible.length ? Math.round(completed / visible.length * 100) : 0;
  return <div className="task-view task-today-view">
    <section className="task-day-poster">
      <div><L red>{t("我的今日")}</L><h2>{new Intl.DateTimeFormat(locale(), { weekday: "long", month: "long", day: "numeric" }).format(new Date())}</h2></div>
      <div className="task-day-score"><strong>{pad(open)}</strong><span>{t("未完成")}</span></div>
      <div className="task-day-score"><strong>{pad(completed)}</strong><span>{t("已完成")}</span></div>
      <div className="task-day-score red"><strong>{rate}<small>%</small></strong><span>{t("完成率")}</span></div>
    </section>
    <div className="task-section-head"><div><span>01</span><h2>{t("今日重點")}</h2></div><button type="button" onClick={onViewAll}>{t("查看全部任務")} →</button></div>
    {visible.length ? <div className="task-list">{visible.map(task => <TaskCard key={task.id || task.title} task={task} busy={busyId === task.id} onStatus={onStatus} onEdit={onEdit} onDelete={onDelete} onCollaboration={onCollaboration} biu={biu}/>)}</div> : <ViewEmpty view="today" onCreate={onCreate}/>} 
  </div>;
};

const InboxView = ({ tasks, onStatus, onEdit, onDelete, onCollaboration, busyId, onCreate, biu = false }) => {
  const [filter, setFilter] = S("open");
  const [search, setSearch] = S("");
  const shown = tasks.filter(task => {
    if (filter === "open" && isTerminal(task.status)) return false;
    if (filter === "closed" && !isTerminal(task.status)) return false;
    const needle = key(search);
    return !needle || key([task.title, task.description, task.planTitle, task.sourceTitle, task.assigneeName].join(" ")).includes(needle);
  }).sort((a, b) => {
    const terminal = Number(isTerminal(a.status)) - Number(isTerminal(b.status));
    if (terminal) return terminal;
    const priority = { urgent: 0, high: 1, normal: 2, low: 3 };
    return priority[a.priority] - priority[b.priority] || String(a.due || "9999").localeCompare(String(b.due || "9999"));
  });
  return <div className="task-view">
    <div className="task-filterbar">
      <div className="task-segments" role="tablist" aria-label={t("收件匣")}>{[["all", "全部"], ["open", "未結束"], ["closed", "已結束"]].map(([id, label]) => <button type="button" role="tab" aria-selected={filter === id} className={filter === id ? "on" : ""} key={id} onClick={() => setFilter(id)}>{t(label)}<b>{id === "all" ? tasks.length : tasks.filter(task => id === "closed" ? isTerminal(task.status) : !isTerminal(task.status)).length}</b></button>)}</div>
      <label className="task-search"><I name="search" size={14}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder={t("搜尋任務、計劃或來源")}/>{search && <button type="button" onClick={() => setSearch("")} aria-label={t("清除篩選")}><I name="x" size={12}/></button>}</label>
    </div>
    {shown.length ? <div className="task-list">{shown.map(task => <TaskCard key={task.id || task.title} task={task} busy={busyId === task.id} onStatus={onStatus} onEdit={onEdit} onDelete={onDelete} onCollaboration={onCollaboration} biu={biu}/>)}</div> : <ViewEmpty view="inbox" onCreate={onCreate}/>} 
  </div>;
};

const CalendarView = ({ tasks, onStatus, onEdit, onDelete, onCollaboration, busyId, onCreate, biu = false }) => {
  const now = new Date();
  const [month, setMonth] = S(new Date(now.getFullYear(), now.getMonth(), 1));
  const [selected, setSelected] = S(todayKey());
  const firstDay = new Date(month.getFullYear(), month.getMonth(), 1);
  const offset = (firstDay.getDay() + 6) % 7;
  const gridStart = addDays(firstDay, -offset);
  const days = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));
  const byDay = M(() => {
    const map = {};
    tasks.forEach(task => {
      const start = dateObject(task.start || task.due);
      const end = dateObject(task.due || task.start) || start;
      if (!start) return;
      const cursor = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 12);
      const rawLast = end >= start ? end : start;
      const last = new Date(rawLast.getFullYear(), rawLast.getMonth(), rawLast.getDate(), 12);
      for (let days = 0; cursor <= last && days < 367; days += 1) {
        const value = dateKey(cursor);
        (map[value] = map[value] || []).push(task);
        cursor.setDate(cursor.getDate() + 1);
      }
    });
    return map;
  }, [tasks]);
  const agenda = arr(byDay[selected]).slice().sort((a, b) => String(a.start || "").localeCompare(String(b.start || "")));
  const move = delta => setMonth(current => new Date(current.getFullYear(), current.getMonth() + delta, 1));
  return <div className="task-view task-calendar-view">
    <section className="task-calendar">
      <header><div><L red>CALENDAR</L><h2>{monthLabel(month)}</h2></div><div className="task-calendar-controls"><button type="button" onClick={() => { setMonth(new Date(now.getFullYear(), now.getMonth(), 1)); setSelected(todayKey()); }}>{t("本月")}</button><button type="button" onClick={() => move(-1)} aria-label={t("上一個月")}>←</button><button type="button" onClick={() => move(1)} aria-label={t("下一個月")}>→</button></div></header>
      <div className="task-weekdays">{["週一", "週二", "週三", "週四", "週五", "週六", "週日"].map(day => <span key={day}>{t(day)}</span>)}</div>
      <div className="task-month-grid">{days.map(day => {
        const token = dateKey(day); const items = arr(byDay[token]); const outside = day.getMonth() !== month.getMonth();
        return <button type="button" key={token} className={`${selected === token ? "selected " : ""}${token === todayKey() ? "today " : ""}${outside ? "outside" : ""}`} onClick={() => setSelected(token)}>
          <span className="task-day-number">{day.getDate()}</span><span className="task-day-dots">{items.slice(0, 3).map((item, index) => <i key={item.id || index} className={`is-${statusTone(item.status)}`}/>)}</span>{items.length > 3 && <small>+{items.length - 3}</small>}
        </button>;
      })}</div>
    </section>
    <aside className="task-agenda"><div className="task-section-head"><div><span>02</span><h2>{t("當日安排")}</h2></div>{onCreate && <button type="button" onClick={() => onCreate("event", { date: selected })}>+ {t("加入這一天")}</button>}</div><div className="task-agenda-date">{dayLabel(selected + "T12:00:00")}</div>{agenda.length ? <div className="task-list compact-list">{agenda.map(task => <TaskCard compact key={task.id || task.title} task={task} busy={busyId === task.id} onStatus={onStatus} onEdit={onEdit} onDelete={onDelete} onCollaboration={onCollaboration} biu={biu}/>)}</div> : <Empty icon="clock" title={t("這一天尚無安排")}/>}</aside>
  </div>;
};

const PlansView = ({ tasks, meta, onStatus, onEdit, onDelete, onCollaboration, busyId, onCreate, biu = false }) => {
  const metaPlans = plansFromMeta(meta).map(item => ({ id: first(item.id, item.plan_id), title: String(first(item.title, item.name, item.plan_name, t("未命名"))), raw: item }));
  const planItems = tasks.filter(task => task.kind === "plan").map(task => ({ id: task.id, title: task.title, raw: task.raw, progress: task.progress }));
  const derived = tasks.filter(task => task.planId || task.planTitle).map(task => ({ id: task.planId || task.planTitle, title: task.planTitle || String(task.planId), raw: {} }));
  const plans = [];
  [...metaPlans, ...planItems, ...derived].forEach(plan => { if (!plans.some(item => String(item.id) === String(plan.id))) plans.push(plan); });
  const unplanned = tasks.filter(task => task.kind !== "plan" && !task.planId && !task.planTitle && !isTerminal(task.status));
  if (!plans.length && !unplanned.length) return <div className="task-view"><ViewEmpty view="plans" onCreate={onCreate ? () => onCreate("plan") : null}/></div>;
  const groups = [...plans.map(plan => ({ ...plan, tasks: tasks.filter(task => task.kind !== "plan" && (String(task.planId || task.planTitle) === String(plan.id) || (!task.planId && task.planTitle === plan.title))) })), ...(unplanned.length ? [{ id: "__none", title: t("未歸入計劃"), tasks: unplanned }] : [])];
  return <div className="task-view task-plans-view"><div className="task-section-head"><div><span>01</span><h2>{t("計劃")}</h2></div>{onCreate && <button type="button" onClick={() => onCreate("plan")}>+ {t("新增計劃")}</button>}</div><div className="task-plan-grid">{groups.map((plan, index) => {
    const complete = plan.tasks.filter(task => task.status === "completed").length;
    const progress = plan.tasks.length ? Math.round(complete / plan.tasks.length * 100) : number(first(plan.progress, plan.raw.progress, plan.raw.progress_percent));
    return <section className="task-plan" key={String(plan.id)}><header><span className="task-plan-index">P{pad(index + 1)}</span><span className="task-plan-progress">{progress}%</span></header><h2>{plan.title}</h2><div className="task-progress"><i style={{ width: `${clamp(progress, 0, 100)}%` }}/></div><div className="task-plan-meta"><span>{plan.tasks.length} {t("項任務")}</span><span>{complete} {t("已完成")}</span></div>{plan.tasks.length ? <div className="task-list compact-list">{plan.tasks.slice(0, 5).map(task => <TaskCard compact key={task.id || task.title} task={task} busy={busyId === task.id} onStatus={onStatus} onEdit={onEdit} onDelete={onDelete} onCollaboration={onCollaboration} biu={biu}/>)}</div> : <div className="task-plan-empty">—</div>}</section>;
  })}</div></div>;
};

const Bar = ({ label, value, total, red }) => <div className="task-bar"><div><span>{label}</span><b>{value}</b></div><i><em style={{ width: `${total ? value / total * 100 : 0}%`, background: red ? "var(--red)" : "var(--ink)" }}/></i></div>;
const InsightsView = ({ tasks, biu = false }) => {
  const measurable = tasks.filter(task => task.kind !== "plan" && task.status !== "cancelled");
  const completed = measurable.filter(task => task.status === "completed");
  const completion = measurable.length ? Math.round(completed.length / measurable.length * 100) : 0;
  const last7 = Array.from({ length: 7 }, (_, index) => addDays(new Date(), index - 6));
  const next7 = Array.from({ length: 7 }, (_, index) => addDays(new Date(), index));
  const completeSeries = last7.map(day => completed.filter(task => dateKey(task.completedAt || task.due) === dateKey(day)).length);
  const loadSeries = next7.map(day => tasks.filter(task => !isTerminal(task.status) && coversDay(task, dateKey(day))).length);
  const maxLoad = Math.max(1, ...loadSeries, ...completeSeries);
  const sourceCounts = tasks.reduce((map, task) => {
    const source = task.sourceRef ? (task.sourceRef.startsWith("record:") ? t("來自檔案") : t(biu ? "案件程序" : "系統操作")) : t(biu ? "自行建立" : "個人建立");
    map[source] = (map[source] || 0) + 1; return map;
  }, {});
  const categoryCounts = tasks.reduce((map, task) => {
    const label = t(categoryLabel(task.category, biu));
    map[label] = (map[label] || 0) + 1; return map;
  }, {});
  return <div className="task-view task-insights-view">
    <section className="task-insight-lead"><div><L red>{t("完成率")}</L><strong>{completion}<small>%</small></strong></div><p>{t("已完成工作")}<b>{completed.length}</b><br/>{t("未完成")}<b>{measurable.filter(task => !isTerminal(task.status)).length}</b></p></section>
    <div className="task-insight-grid">
      <section><div className="task-section-head"><div><span>01</span><h2>{t("狀態結構")}</h2></div></div>{["planned", "active", "paused", "completed", "cancelled"].map((status, index) => <Bar key={status} label={t(statusLabel(status))} value={tasks.filter(task => task.status === status).length} total={tasks.length} red={index === 1}/>)}</section>
      <section><div className="task-section-head"><div><span>02</span><h2>{t("類別分佈")}</h2></div></div>{Object.entries(categoryCounts).map(([label, value]) => <Bar key={label} label={label} value={value} total={tasks.length}/>)}</section>
      <section><div className="task-section-head"><div><span>03</span><h2>{t("來源分佈")}</h2></div></div>{Object.entries(sourceCounts).map(([label, value]) => <Bar key={label} label={label} value={value} total={tasks.length}/>)}</section>
      <section className="wide"><div className="task-section-head"><div><span>04</span><h2>{t("未來七日負載")}</h2></div><b>{loadSeries.reduce((sum, value) => sum + value, 0)} {t("項任務")}</b></div><div className="task-week-chart">{next7.map((day, index) => <div key={dateKey(day)}><span className="task-chart-value">{loadSeries[index]}</span><i><em style={{ height: `${loadSeries[index] / maxLoad * 100}%` }}/></i><small>{new Intl.DateTimeFormat(locale(), { weekday: "short" }).format(day)}</small></div>)}</div></section>
    </div>
  </div>;
};

const CollaborationPlaza = ({ onOpen, refreshSignal = 0 }) => {
  const tenant = W2.tenant();
  const [items, setItems] = S([]);
  const [nextCursor, setNextCursor] = S(null);
  const [search, setSearch] = S("");
  const [scope, setScope] = S("all");
  const [loading, setLoading] = S(true);
  const [error, setError] = S("");
  const mounted = R(true);
  const requestSequence = R(0);
  const pendingLoad = R(null);
  E(() => () => {
    mounted.current = false;
    requestSequence.current += 1;
  }, []);

  const load = C(async ({ append = false, cursor = null } = {}) => {
    const params = new URLSearchParams();
    params.set("limit", "24");
    if (search.trim()) params.set("q", search.trim());
    if (scope !== "all") params.set("discoverability", scope);
    if (append && cursor != null && cursor !== "") params.set("cursor", String(cursor));
    const loadKey = `${tenant}:${refreshSignal}:${append ? "append" : "replace"}:${params.toString()}`;
    if (pendingLoad.current && pendingLoad.current.key === loadKey) return pendingLoad.current.promise;
    const request = ++requestSequence.current;
    const promise = (async () => {
      if (!append) setLoading(true);
      setError("");
      try {
        const data = await collabJson("/api/task-collaboration/discover?" + params.toString());
        if (!mounted.current || request !== requestSequence.current || tenant !== W2.tenant()) return;
        const incoming = uniqueCollabCards(collabCollection(data).map(normalizeCollabCard).filter(item => item.id != null));
        setItems(current => uniqueCollabCards(append ? [...current, ...incoming] : incoming));
        setNextCursor(first(collabData(data).next_cursor, null));
      } catch (exception) {
        if (mounted.current && request === requestSequence.current && tenant === W2.tenant()) {
          setError(exception.message || t("協作資料暫時無法載入"));
          if (!append) setItems([]);
        }
      } finally {
        if (mounted.current && request === requestSequence.current) setLoading(false);
      }
    })();
    pendingLoad.current = { key: loadKey, promise };
    try {
      return await promise;
    } finally {
      if (pendingLoad.current && pendingLoad.current.promise === promise) pendingLoad.current = null;
    }
  }, [tenant, search, scope, refreshSignal]);
  E(() => {
    const timer = window.setTimeout(() => load(), 250);
    return () => window.clearTimeout(timer);
  }, [load, refreshSignal]);
  return <div className="task-view task-collab-plaza">
    <section className="task-collab-intro">
      <div><L red>COLLABORATION</L><h2>{t("協作廣場")}</h2><p>{t("探索公司內可加入的任務協作，或回到自己的工作間。")}</p></div>
      <button type="button" className="task-collab-refresh" disabled={loading} onClick={() => load()} aria-label={t("重新整理協作")}><I name="refresh" size={15}/></button>
    </section>
    <div className="task-collab-filters">
      <label className="task-search"><I name="search" size={14}/><input value={search} onChange={event => setSearch(event.target.value)} placeholder={t("搜尋協作任務")}/>{search && <button type="button" onClick={() => setSearch("")} aria-label={t("清除篩選")}><I name="x" size={12}/></button>}</label>
      <div className="task-segments" role="tablist" aria-label={t("探索範圍")}>{[["all", "所有範圍"], ["company", "公司可見"], ["team", "團隊可見"]].map(([id, label]) => <button type="button" role="tab" aria-selected={scope === id} className={scope === id ? "on" : ""} key={id} onClick={() => setScope(id)}>{t(label)}</button>)}</div>
    </div>
    {error && <div className="task-inline-error" role="alert"><span>{error}</span><button type="button" onClick={() => load()}>{t("重新載入")}</button></div>}
    {loading && !items.length
      ? <div className="task-loading" aria-live="polite"><span/><span/><span/><small>{t("同步中")}</small></div>
      : items.length ? <div className="task-collab-grid">{items.map(item => <article className="task-collab-card" key={collabCardIdentity(item)} data-task-id={String(item.id)} data-space-id={optionalText(item.spaceId)}>
        <header><span>{t(collabScopeLabel(item.discoverability))}</span><b>{t(collabJoinLabel(item.joinPolicy))}</b></header>
        <h3>{item.title}</h3>
        {item.description && <p>{item.description}</p>}
        <div className="task-collab-card-meta">
          {item.owner && <span><I name="user" size={11}/>{item.owner}</span>}
          <span><I name="user" size={11}/>{item.memberCount} {t("人參與")}</span>
          {item.relation && !["available", "discoverable"].includes(item.relation) && <span className={"task-collab-relation is-" + item.relation}>{["requested", "request"].includes(item.relation) ? t("等待負責人審批") : ["invited", "invitation"].includes(item.relation) ? t("邀請中") : t("協作者")}</span>}
        </div>
        <button type="button" onClick={() => onOpen({ id: item.id, title: item.title, relation: item.relation, raw: item.raw })}><span>{t("打開工作間")}</span><I name="arrow" size={13}/></button>
      </article>)}</div>
      : <Empty icon="user" title={t("暫無可探索的協作")} sub={t("調整搜尋或範圍，或從任務卡開啟新的協作。")}/>}
    {nextCursor != null && nextCursor !== "" && <div className="task-collab-more"><B disabled={loading} onClick={() => load({ append: true, cursor: nextCursor })}>{t("載入更多")}</B></div>}
  </div>;
};

const CollaborationChat = ({
  taskId, active, canSend, viewerUserId, realtimeState, presence,
  members, messageSignal, onTyping, lastMessageIdRef,
}) => {
  const tenant = W2.tenant();
  const [messages, setMessages] = S([]);
  const [draft, setDraft] = S("");
  const [loading, setLoading] = S(false);
  const [sending, setSending] = S(false);
  const [error, setError] = S("");
  const [newMessageCount, setNewMessageCount] = S(0);
  const mounted = R(true);
  const polling = R(false);
  const pendingLoad = R(false);
  const loadGeneration = R(0);
  const loadController = R(null);
  const drainTimer = R(null);
  const localMaxSeenMessageId = R(0);
  const maxSeenMessageId = lastMessageIdRef || localMaxSeenMessageId;
  const contiguousFetchCursor = R(0);
  const readCursor = R(0);
  const readPending = R(0);
  const listRef = R(null);
  const nearBottom = R(true);
  const forceScroll = R(true);
  const draftRef = R("");
  const typingStarted = R(false);
  const typingLastSent = R(0);
  const typingStartTimer = R(null);
  const typingRefreshTimer = R(null);
  const typingStopTimer = R(null);
  const typingCallback = R(onTyping);
  E(() => { typingCallback.current = onTyping; }, [onTyping]);
  const clearTypingTimers = C(() => {
    if (typingStartTimer.current) window.clearTimeout(typingStartTimer.current);
    if (typingRefreshTimer.current) window.clearTimeout(typingRefreshTimer.current);
    if (typingStopTimer.current) window.clearTimeout(typingStopTimer.current);
    typingStartTimer.current = null;
    typingRefreshTimer.current = null;
    typingStopTimer.current = null;
  }, []);
  const transmitTyping = C(activeTyping => {
    typingStarted.current = activeTyping === true;
    typingLastSent.current = Date.now();
    const callback = typingCallback.current;
    if (typeof callback === "function") Promise.resolve(callback(activeTyping === true)).catch(() => {});
  }, []);
  const stopTyping = C((notify = true) => {
    clearTypingTimers();
    if (typingStarted.current && notify) transmitTyping(false);
    else typingStarted.current = false;
  }, [clearTypingTimers, transmitTyping]);
  const queueTyping = C(value => {
    draftRef.current = value;
    const eligible = active
      && canSend
      && realtimeState === COLLAB_REALTIME_STATES.LIVE
      && value.trim().length > 0;
    if (!eligible) { stopTyping(true); return; }
    if (typingStopTimer.current) window.clearTimeout(typingStopTimer.current);
    typingStopTimer.current = window.setTimeout(() => stopTyping(true), 3000);
    if (!typingStarted.current) {
      if (!typingStartTimer.current) {
        typingStartTimer.current = window.setTimeout(() => {
          typingStartTimer.current = null;
          if (draftRef.current.trim()) transmitTyping(true);
        }, 300);
      }
      return;
    }
    const wait = Math.max(0, 2000 - (Date.now() - typingLastSent.current));
    if (wait === 0) transmitTyping(true);
    else if (!typingRefreshTimer.current) {
      typingRefreshTimer.current = window.setTimeout(() => {
        typingRefreshTimer.current = null;
        if (draftRef.current.trim()) transmitTyping(true);
      }, wait);
    }
  }, [active, canSend, realtimeState, stopTyping, transmitTyping]);
  E(() => () => {
    mounted.current = false;
    loadGeneration.current += 1;
    if (loadController.current) loadController.current.abort();
    if (drainTimer.current) window.clearTimeout(drainTimer.current);
    loadController.current = null;
    drainTimer.current = null;
    pendingLoad.current = false;
    polling.current = false;
    clearTypingTimers();
    if (typingStarted.current && typeof typingCallback.current === "function") {
      Promise.resolve(typingCallback.current(false)).catch(() => {});
    }
    typingStarted.current = false;
  }, [clearTypingTimers]);
  E(() => {
    if (!active || !canSend || realtimeState !== COLLAB_REALTIME_STATES.LIVE) stopTyping(true);
  }, [active, canSend, realtimeState, stopTyping]);
  const mergeMessages = C((current, incoming, reset) => {
    const source = reset ? incoming : [...current, ...incoming];
    const seen = new Map();
    source.forEach(message => {
      const id = collabMessageId(message);
      if (id > 0) seen.set(String(id), message);
    });
    return [...seen.values()]
      .sort((a, b) => collabMessageId(a) - collabMessageId(b))
      .slice(-COLLAB_CHAT_RETAINED_MESSAGES);
  }, []);
  const markRead = C(messageId => {
    const safeMessageId = Math.min(number(messageId), contiguousFetchCursor.current);
    if (!safeMessageId || safeMessageId <= Math.max(readCursor.current, readPending.current)) return;
    if (!active || document.visibilityState !== "visible" || !nearBottom.current) return;
    readPending.current = safeMessageId;
    collabPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/read`, {
      message_id: safeMessageId,
    }).then(() => {
      if (mounted.current && tenant === W2.tenant()) {
        readCursor.current = Math.max(readCursor.current, safeMessageId);
      }
    }).catch(() => {}).finally(() => {
      if (readPending.current === safeMessageId) readPending.current = 0;
    });
  }, [active, taskId, tenant]);
  const loadMessages = C(async (reset = false) => {
    if (!active || taskId == null) return;
    if (polling.current) { pendingLoad.current = true; return; }
    polling.current = true;
    pendingLoad.current = false;
    const request = ++loadGeneration.current;
    if (loadController.current) loadController.current.abort();
    const requestController = new AbortController();
    loadController.current = requestController;
    if (reset) setLoading(true);
    let pageAfterId = reset ? 0 : contiguousFetchCursor.current;
    let incoming = [];
    let shouldContinue = false;
    let stalled = false;
    try {
      for (let page = 0; page < COLLAB_CHAT_DRAIN_PAGES && incoming.length < COLLAB_CHAT_RETAINED_MESSAGES; page += 1) {
        const data = await collabJson(
          `/api/tasks/${encodeURIComponent(taskId)}/collaboration/messages?after_id=${encodeURIComponent(pageAfterId)}&limit=${COLLAB_CHAT_PAGE_LIMIT}`,
          { signal: requestController.signal }
        );
        if (!mounted.current || request !== loadGeneration.current || tenant !== W2.tenant()) return;
        const pageMessages = collabMessages(data);
        incoming = [...incoming, ...pageMessages];
        const dataPage = collabData(data);
        const maxIncoming = pageMessages.reduce(
          (maximum, message) => Math.max(maximum, collabMessageId(message)),
          pageAfterId
        );
        const rawNextCursor = first(dataPage.next_cursor, null);
        const next = number(first(dataPage.next_after_id, rawNextCursor, maxIncoming, pageAfterId));
        const nextAfterId = Math.max(pageAfterId, next, maxIncoming);
        const hasMore = dataPage.has_more === true
          || (dataPage.has_more == null && rawNextCursor != null && rawNextCursor !== "");
        if (!hasMore) { shouldContinue = false; pageAfterId = nextAfterId; break; }
        if (nextAfterId <= pageAfterId) { stalled = true; shouldContinue = false; break; }
        pageAfterId = nextAfterId;
        shouldContinue = true;
      }
      if (!mounted.current || request !== loadGeneration.current || tenant !== W2.tenant()) return;
      contiguousFetchCursor.current = Math.max(contiguousFetchCursor.current, pageAfterId);
      const maxIncomingSeen = incoming.reduce(
        (maximum, message) => Math.max(maximum, collabMessageId(message)),
        0
      );
      maxSeenMessageId.current = Math.max(maxSeenMessageId.current, maxIncomingSeen);
      setMessages(current => mergeMessages(current, incoming, reset));
      if (reset) {
        nearBottom.current = true;
        forceScroll.current = true;
        setNewMessageCount(0);
      } else if (incoming.length && nearBottom.current) {
        forceScroll.current = true;
      } else if (incoming.length) {
        setNewMessageCount(current => current + incoming.length);
      }
      setError(stalled ? t("訊息載入失敗，將稍後重試。") : "");
    } catch (exception) {
      if (exception && exception.name === "AbortError") return;
      if (mounted.current && request === loadGeneration.current && tenant === W2.tenant()) {
        setError(t("訊息載入失敗，將稍後重試。"));
      }
    } finally {
      if (loadController.current === requestController) loadController.current = null;
      polling.current = false;
      if (mounted.current && request === loadGeneration.current) setLoading(false);
      const continueDrain = !stalled && (shouldContinue || pendingLoad.current);
      pendingLoad.current = false;
      if (continueDrain && mounted.current && request === loadGeneration.current && tenant === W2.tenant()) {
        if (drainTimer.current) window.clearTimeout(drainTimer.current);
        drainTimer.current = window.setTimeout(() => {
          drainTimer.current = null;
          if (mounted.current && request === loadGeneration.current && tenant === W2.tenant()) loadMessages(false);
        }, COLLAB_CHAT_CONTINUE_DELAY);
      }
    }
  }, [active, taskId, tenant, mergeMessages]);
  const pollingDelay = realtimeState === COLLAB_REALTIME_STATES.LIVE
    ? 30000
    : realtimeState === COLLAB_REALTIME_STATES.FALLBACK ? 2500 : null;
  E(() => {
    if (!active || taskId == null) return undefined;
    contiguousFetchCursor.current = 0;
    maxSeenMessageId.current = 0;
    readCursor.current = 0;
    readPending.current = 0;
    nearBottom.current = true;
    forceScroll.current = true;
    setMessages([]);
    setNewMessageCount(0);
    setError("");
    loadMessages(true);
    const onVisible = () => {
      if (document.visibilityState === "visible") loadMessages(false);
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      loadGeneration.current += 1;
      if (loadController.current) loadController.current.abort();
      if (drainTimer.current) window.clearTimeout(drainTimer.current);
      loadController.current = null;
      drainTimer.current = null;
      pendingLoad.current = false;
      polling.current = false;
    };
  }, [active, taskId, tenant, loadMessages]);
  E(() => {
    if (!active || taskId == null || pollingDelay == null) return undefined;
    loadMessages(false);
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") loadMessages(false);
    }, pollingDelay);
    return () => window.clearInterval(timer);
  }, [active, taskId, pollingDelay, loadMessages]);
  E(() => {
    if (active && messageSignal > 0) loadMessages(false);
  }, [active, messageSignal, loadMessages]);
  const scrollToBottom = C(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
    nearBottom.current = true;
    forceScroll.current = false;
    setNewMessageCount(0);
    markRead(maxSeenMessageId.current);
  }, [maxSeenMessageId, markRead]);
  const onMessageScroll = C(() => {
    const list = listRef.current;
    if (!list) return;
    const atBottom = list.scrollHeight - list.scrollTop - list.clientHeight <= 48;
    nearBottom.current = atBottom;
    if (atBottom) {
      setNewMessageCount(0);
      markRead(maxSeenMessageId.current);
    }
  }, [maxSeenMessageId, markRead]);
  E(() => {
    if (!active || !listRef.current) return;
    const frame = window.requestAnimationFrame(() => {
      if (forceScroll.current || nearBottom.current) scrollToBottom();
      else markRead(maxSeenMessageId.current);
    });
    return () => window.cancelAnimationFrame(frame);
  }, [active, messages.length, maxSeenMessageId, markRead, scrollToBottom]);
  const send = async event => {
    event.preventDefault();
    const body = draft.trim();
    if (!body || !canSend || sending) return;
    setSending(true);
    setError("");
    try {
      const data = await collabPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/messages`, {
        body,
        client_message_id: clientRequestId(),
      });
      if (!mounted.current || tenant !== W2.tenant()) return;
      const sent = obj(first(collabData(data).message, collabData(data).item));
      if (collabMessageId(sent) > 0) {
        maxSeenMessageId.current = Math.max(maxSeenMessageId.current, collabMessageId(sent));
        forceScroll.current = true;
        setMessages(current => mergeMessages(current, [sent], false));
        loadMessages(false);
      } else {
        await loadMessages(false);
      }
      setDraft("");
      draftRef.current = "";
      stopTyping(true);
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant()) setError(exception.message || t("協作操作失敗"));
    } finally {
      if (mounted.current) setSending(false);
    }
  };
  const typingUsers = Object.values(obj(presence)).filter(item => (
    item.typing
    && item.typingExpiresAt > Date.now()
    && item.state === "active"
    && (viewerUserId == null || String(item.userId) !== String(viewerUserId))
  ));
  const typingNames = typingUsers.slice(0, 2).map(item => {
    const member = arr(members).find(candidate => String(collabMemberId(candidate)) === String(item.userId));
    return item.displayName || collabDisplayName(member, t("協作者"));
  }).join("、");
  const typingExtra = Math.max(0, typingUsers.length - 2);
  const offline = realtimeState === COLLAB_REALTIME_STATES.OFFLINE;
  return <section className="task-collab-chat">
    {error && <div className="task-inline-error" role="alert"><span>{error}</span><button type="button" onClick={() => loadMessages(false)}>{t("重新載入")}</button></div>}
    <div className="task-collab-message-window">
      <div className="task-collab-messages" ref={listRef} role="log" aria-label={t("聊天訊息")} aria-live="polite" aria-relevant="additions text" aria-atomic="false" aria-busy={loading} tabIndex="0" onScroll={onMessageScroll}>
        {loading && !messages.length
          ? <div className="task-collab-chat-empty">{t("同步中")}</div>
          : messages.length ? messages.map(message => {
            const senderId = first(message.sender_user_id, obj(message.sender).user_id, obj(message.sender).id);
            const mine = message.is_mine === true || (viewerUserId != null && String(senderId) === String(viewerUserId));
            return <article className={"task-collab-message" + (mine ? " mine" : "")} key={collabMessageId(message)}>
              <header><strong>{collabDisplayName(first(message.sender, { display_name: message.sender_name }), t("協作者"))}</strong><time>{collabTime(first(message.created_at, message.sent_at))}</time></header>
              <p>{optionalText(message.body, message.message)}</p>
            </article>;
          }) : <div className="task-collab-chat-empty">{t("目前沒有訊息")}</div>}
      </div>
      {newMessageCount > 0 && <button type="button" className="task-collab-new-messages" onClick={scrollToBottom} aria-label={newMessageCount + " " + t("則新訊息")}>{newMessageCount} {t("則新訊息")} · {t("查看新訊息")}</button>}
    </div>
    <div className="task-collab-typing" role="status" aria-live="polite" aria-atomic="true">{typingUsers.length ? <span><strong>{typingNames}</strong>{typingExtra > 0 && <b> +{typingExtra}</b>} {t("正在輸入訊息")}…</span> : null}</div>
    {canSend && <form className="task-collab-compose" onSubmit={send}>
      <label><span className="sr-only">{t("輸入訊息")}</span><textarea rows="2" maxLength="4000" value={draft} onChange={event => { setDraft(event.target.value); queueTyping(event.target.value); }} onBlur={() => stopTyping(true)} placeholder={offline ? t("目前離線，草稿已保留") : t("輸入訊息")}/></label>
      <B type="submit" kind="primary" disabled={sending || offline || !draft.trim()}>{sending ? "…" : t("發送")}</B>
    </form>}
  </section>;
};

/* The shared working draft uses the same deterministic RGA contract as the
   server. Pending updates are tenant/task scoped and remain idempotent across
   reloads; realtime events only prompt a canonical GET and never carry text. */
const COLLAB_DOCUMENT_FORMAT = "rga-v1";
const COLLAB_DOCUMENT_ROOT = "^";
const COLLAB_DOCUMENT_MAX_CHARACTERS = 32000;
const COLLAB_DOCUMENT_MAX_NODES = 50000;
const COLLAB_DOCUMENT_MAX_TABLE_ROWS = 200;
const COLLAB_DOCUMENT_MAX_PREVIEW_BLOCKS = 1000;
const COLLAB_DOCUMENT_MAX_PREVIEW_IMAGES = 100;
const COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS = 512;
const COLLAB_DOCUMENT_MAX_FORMULA_DEPTH = 12;
const COLLAB_DOCUMENT_MAX_FORMULA_NODES = 256;
const COLLAB_DOCUMENT_MAX_FORMULAS = 100;
const COLLAB_DOCUMENT_UPDATE_CHUNK = 350;
const COLLAB_DOCUMENT_MAX_UPDATE_BYTES = 80 * 1024;
const COLLAB_DOCUMENT_MAX_PENDING_UPDATES = 160;
const COLLAB_DOCUMENT_MAX_QUEUE_BYTES = 4 * 1024 * 1024;
const COLLAB_DOCUMENT_GET_TIMEOUT_MS = 15000;
const COLLAB_DOCUMENT_UPDATE_TIMEOUT_MS = 20000;
const COLLAB_DOCUMENT_MAX_TRANSIENT_RETRIES = 5;
const COLLAB_DOCUMENT_QUEUE_VERSION = 1;
const COLLAB_DOCUMENT_ID_RE = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$/;
const collabDocumentValidCharacter = value => {
  const text = String(value == null ? "" : value);
  if (Array.from(text).length !== 1 || text === "\u0000") return false;
  const point = text.codePointAt(0);
  return point < 0xD800 || point > 0xDFFF;
};
const collabDocumentUpdateSeed = () => {
  let entropy = "";
  try {
    if (window.crypto && typeof window.crypto.getRandomValues === "function") {
      const values = new Uint32Array(2);
      window.crypto.getRandomValues(values);
      entropy = Array.from(values).map(value => value.toString(36)).join("");
    }
  } catch (error) {}
  if (!entropy) entropy = Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
  return `c${Date.now().toString(36)}${entropy}`.slice(0, 48);
};
const collabDocumentStorageKey = (tenant, taskId, viewerUserId) => (
  `w2:task-collaboration-document:${String(tenant)}:${String(taskId)}:${String(viewerUserId)}`
);
const collabDocumentFreshQueue = clientId => ({
  version: COLLAB_DOCUMENT_QUEUE_VERSION,
  client_id: COLLAB_DOCUMENT_ID_RE.test(String(clientId || "")) ? String(clientId) : clientRequestId(),
  updates: [],
});
const collabDocumentStoredOperation = (rawOperation, insertedIds) => {
  const operation = obj(rawOperation);
  const type = key(operation.type);
  const id = String(operation.id || "");
  if (!COLLAB_DOCUMENT_ID_RE.test(id)) throw new Error("invalid stored collaboration operation id");
  if (type === "delete") return { type: "delete", id };
  if (type !== "insert") throw new Error("invalid stored collaboration operation type");
  const after = String(operation.after || "");
  const value = String(operation.value == null ? "" : operation.value);
  if (
    insertedIds.has(id)
    || (after !== COLLAB_DOCUMENT_ROOT && !COLLAB_DOCUMENT_ID_RE.test(after))
    || !collabDocumentValidCharacter(value)
    || typeof operation.clock !== "number"
    || !Number.isSafeInteger(operation.clock)
    || operation.clock < 1
  ) throw new Error("invalid stored collaboration insertion");
  insertedIds.add(id);
  return { type: "insert", id, after, value, clock: operation.clock };
};
const collabDocumentReadQueue = (tenant, taskId, viewerUserId, fallbackClientId) => {
  const fresh = collabDocumentFreshQueue(fallbackClientId);
  if (viewerUserId == null || viewerUserId === "") return fresh;
  let raw = "";
  try {
    raw = window.localStorage.getItem(collabDocumentStorageKey(tenant, taskId, viewerUserId)) || "";
    if (!raw) return fresh;
    if (new Blob([raw]).size > COLLAB_DOCUMENT_MAX_QUEUE_BYTES) throw new Error("stored collaboration queue is too large");
    const stored = JSON.parse(raw);
    if (
      obj(stored).version !== COLLAB_DOCUMENT_QUEUE_VERSION
      || !COLLAB_DOCUMENT_ID_RE.test(String(obj(stored).client_id || ""))
      || !Array.isArray(obj(stored).updates)
      || obj(stored).updates.length > COLLAB_DOCUMENT_MAX_PENDING_UPDATES
    ) throw new Error("invalid collaboration draft queue header");
    const updateIds = new Set();
    const insertedIds = new Set();
    const updates = stored.updates.map(value => {
      const update = obj(value);
      const updateId = String(update.client_update_id || "");
      if (
        !COLLAB_DOCUMENT_ID_RE.test(updateId)
        || updateIds.has(updateId)
        || !Array.isArray(update.ops)
        || !update.ops.length
        || update.ops.length > COLLAB_DOCUMENT_UPDATE_CHUNK
        || new Blob([JSON.stringify({ format: COLLAB_DOCUMENT_FORMAT, ops: update.ops })]).size > COLLAB_DOCUMENT_MAX_UPDATE_BYTES
      ) throw new Error("invalid collaboration draft queue");
      if (update.dispatched != null && typeof update.dispatched !== "boolean") {
        throw new Error("invalid collaboration draft dispatch state");
      }
      updateIds.add(updateId);
      return {
        client_update_id: updateId,
        ops: update.ops.map(operation => collabDocumentStoredOperation(operation, insertedIds)),
        dispatched: update.dispatched === true,
      };
    });
    return { version: COLLAB_DOCUMENT_QUEUE_VERSION, client_id: String(stored.client_id), updates };
  } catch (error) {
    if (raw) {
      try {
        window.localStorage.setItem(
          collabDocumentStorageKey(tenant, taskId, viewerUserId) + ":quarantine",
          raw
        );
      } catch (ignored) {}
      return { ...fresh, recovery_warning: true };
    }
    return fresh;
  }
};
const collabDocumentSaveQueue = (tenant, taskId, viewerUserId, queue) => {
  if (viewerUserId == null || viewerUserId === "") return false;
  try {
    if (queue.updates.length > COLLAB_DOCUMENT_MAX_PENDING_UPDATES) return false;
    const serialized = JSON.stringify({
      version: COLLAB_DOCUMENT_QUEUE_VERSION,
      client_id: queue.client_id,
      updates: queue.updates,
    });
    if (new Blob([serialized]).size > COLLAB_DOCUMENT_MAX_QUEUE_BYTES) return false;
    window.localStorage.setItem(
      collabDocumentStorageKey(tenant, taskId, viewerUserId),
      serialized
    );
    return true;
  } catch (error) {
    return false;
  }
};
const collabDocumentNodes = snapshotValue => {
  const snapshot = obj(snapshotValue);
  if (first(snapshot.format, COLLAB_DOCUMENT_FORMAT) !== COLLAB_DOCUMENT_FORMAT) {
    throw new Error("unsupported collaboration document format");
  }
  const source = arr(snapshot.nodes);
  if (source.length > COLLAB_DOCUMENT_MAX_NODES) throw new Error("collaboration document is too large");
  const nodes = Object.create(null);
  source.forEach(rawNode => {
    const item = obj(rawNode);
    const id = String(item.id || "");
    const after = String(item.after || "");
    const value = String(item.value == null ? "" : item.value);
    const clock = Number(item.clock);
    if (
      !COLLAB_DOCUMENT_ID_RE.test(id)
      || Object.prototype.hasOwnProperty.call(nodes, id)
      || (after !== COLLAB_DOCUMENT_ROOT && !COLLAB_DOCUMENT_ID_RE.test(after))
      || (!(item.deleted === true && value === "") && !collabDocumentValidCharacter(value))
      || typeof item.clock !== "number"
      || !Number.isSafeInteger(clock)
      || clock < 1
    ) throw new Error("invalid collaboration document snapshot");
    nodes[id] = { id, after, value, clock, deleted: item.deleted === true };
  });
  Object.values(nodes).forEach(node => {
    if (node.after !== COLLAB_DOCUMENT_ROOT && !Object.prototype.hasOwnProperty.call(nodes, node.after)) {
      throw new Error("collaboration document has a missing predecessor");
    }
  });
  return nodes;
};
const collabDocumentCompareSiblings = (left, right) => {
  if (left.clock !== right.clock) return right.clock - left.clock;
  const leftId = String(left.id);
  const rightId = String(right.id);
  return leftId === rightId ? 0 : leftId < rightId ? 1 : -1;
};
const collabDocumentOrderedNodes = nodes => {
  const children = Object.create(null);
  Object.values(nodes).forEach(node => {
    if (!Object.prototype.hasOwnProperty.call(children, node.after)) children[node.after] = [];
    children[node.after].push(node);
  });
  Object.values(children).forEach(values => values.sort(collabDocumentCompareSiblings));
  const ordered = [];
  const visited = new Set();
  const stack = [...arr(children[COLLAB_DOCUMENT_ROOT])].reverse();
  while (stack.length) {
    const node = stack.pop();
    if (!node || visited.has(node.id)) throw new Error("collaboration document contains a cycle");
    visited.add(node.id);
    ordered.push(node);
    stack.push(...[...arr(children[node.id])].reverse());
  }
  if (visited.size !== Object.keys(nodes).length) throw new Error("collaboration document is disconnected");
  return ordered;
};
const collabDocumentView = nodes => {
  const ordered = collabDocumentOrderedNodes(nodes);
  const visible = ordered.filter(node => !node.deleted);
  if (visible.length > COLLAB_DOCUMENT_MAX_CHARACTERS) throw new Error("collaboration document is too long");
  return {
    content: visible.map(node => node.value).join(""),
    visibleIds: visible.map(node => node.id),
    maxClock: ordered.reduce((maximum, node) => Math.max(maximum, number(node.clock)), 0),
  };
};
const collabDocumentApply = (sourceNodes, operations) => {
  const nodes = Object.create(null);
  Object.entries(obj(sourceNodes)).forEach(([id, node]) => { nodes[id] = { ...node }; });
  arr(operations).forEach(rawOperation => {
    const operation = obj(rawOperation);
    const type = key(operation.type);
    const id = String(operation.id || "");
    if (!COLLAB_DOCUMENT_ID_RE.test(id)) throw new Error("invalid collaboration document operation");
    if (type === "insert") {
      const after = String(operation.after || "");
      const value = String(operation.value == null ? "" : operation.value);
      const clock = Number(operation.clock);
      const existing = Object.prototype.hasOwnProperty.call(nodes, id) ? nodes[id] : null;
      if (existing) {
        const valueMatches = existing.value === value || (existing.deleted === true && existing.value === "");
        if (existing.after !== after || !valueMatches || existing.clock !== clock) {
          throw new Error("conflicting collaboration document element");
        }
        return;
      }
      if (
        (after !== COLLAB_DOCUMENT_ROOT && !Object.prototype.hasOwnProperty.call(nodes, after))
        || !collabDocumentValidCharacter(value)
        || typeof operation.clock !== "number"
        || !Number.isSafeInteger(clock)
        || clock < 1
      ) throw new Error("invalid collaboration document insertion");
      nodes[id] = { id, after, value, clock, deleted: false };
    } else if (type === "delete") {
      if (!Object.prototype.hasOwnProperty.call(nodes, id)) throw new Error("collaboration document deletion target is missing");
      nodes[id].deleted = true;
    } else throw new Error("unsupported collaboration document operation");
  });
  if (Object.keys(nodes).length > COLLAB_DOCUMENT_MAX_NODES) throw new Error("collaboration document node limit reached");
  return nodes;
};
const collabDocumentOperations = (nodes, nextText, updateSeed) => {
  const view = collabDocumentView(nodes);
  const before = Array.from(view.content);
  const after = Array.from(String(nextText));
  let prefix = 0;
  while (prefix < before.length && prefix < after.length && before[prefix] === after[prefix]) prefix += 1;
  let suffix = 0;
  while (
    suffix < before.length - prefix
    && suffix < after.length - prefix
    && before[before.length - 1 - suffix] === after[after.length - 1 - suffix]
  ) suffix += 1;
  const operations = view.visibleIds
    .slice(prefix, before.length - suffix)
    .map(id => ({ type: "delete", id }));
  let predecessor = prefix > 0 ? view.visibleIds[prefix - 1] : COLLAB_DOCUMENT_ROOT;
  after.slice(prefix, after.length - suffix).forEach((value, index) => {
    const id = `${updateSeed}:${index}`;
    operations.push({ type: "insert", id, after: predecessor, value, clock: view.maxClock + index + 1 });
    predecessor = id;
  });
  return operations;
};
const collabDocumentRangeOperations = (nodes, startValue, endValue, replacementValue, updateSeed) => {
  const view = collabDocumentView(nodes);
  const index = collabDocumentSelectionIndex(nodes);
  const start = clamp(number(startValue), 0, view.content.length);
  const end = clamp(number(endValue), start, view.content.length);
  const aligned = offset => offset === 0 || offset === view.content.length || index.visible.some(item => (
    item.start === offset || item.end === offset
  ));
  if (!aligned(start) || !aligned(end)) throw new Error("collaboration document range splits a character");
  const operations = index.visible.filter(item => item.start >= start && item.end <= end)
    .map(item => ({ type: "delete", id: item.id }));
  const predecessor = [...index.visible].reverse().find(item => item.end <= start);
  let after = predecessor ? predecessor.id : COLLAB_DOCUMENT_ROOT;
  Array.from(String(replacementValue || "")).forEach((value, replacementIndex) => {
    const id = `${updateSeed}:${replacementIndex}`;
    operations.push({
      type: "insert", id, after, value,
      clock: view.maxClock + replacementIndex + 1,
    });
    after = id;
  });
  return operations;
};
const collabDocumentMapSelection = (beforeValue, afterValue, offsetValue) => {
  const before = String(beforeValue || "");
  const after = String(afterValue || "");
  const offset = clamp(number(offsetValue), 0, before.length);
  let prefix = 0;
  while (prefix < before.length && prefix < after.length && before[prefix] === after[prefix]) prefix += 1;
  let suffix = 0;
  while (
    suffix < before.length - prefix
    && suffix < after.length - prefix
    && before[before.length - 1 - suffix] === after[after.length - 1 - suffix]
  ) suffix += 1;
  if (offset <= prefix) return offset;
  if (offset >= before.length - suffix) return clamp(after.length - (before.length - offset), 0, after.length);
  return prefix;
};
const collabDocumentSelectionIndex = nodesValue => {
  const nodes = obj(nodesValue);
  const before = new Map([[COLLAB_DOCUMENT_ROOT, 0]]);
  const after = new Map([[COLLAB_DOCUMENT_ROOT, 0]]);
  const visible = [];
  let offset = 0;
  collabDocumentOrderedNodes(nodes).forEach(node => {
    before.set(node.id, offset);
    if (!node.deleted) {
      const length = String(node.value || "").length;
      visible.push({ id: node.id, start: offset, end: offset + length });
      offset += length;
    }
    after.set(node.id, offset);
  });
  return { before, after, visible, total: offset };
};
const collabDocumentCaptureBoundary = (index, offsetValue, affinityValue = "backward") => {
  const offset = clamp(number(offsetValue), 0, index.total);
  const affinity = affinityValue === "forward" ? "forward" : "backward";
  let leftId = COLLAB_DOCUMENT_ROOT;
  let rightId = null;
  for (const item of index.visible) {
    if (offset <= item.start) {
      rightId = item.id;
      break;
    }
    if (offset < item.end) {
      if (affinity === "forward") rightId = item.id;
      else leftId = item.id;
      return { leftId, rightId, affinity, fallback: offset };
    }
    leftId = item.id;
  }
  return { leftId, rightId, affinity, fallback: offset };
};
const collabDocumentResolveBoundary = (index, anchor, fallbackValue) => {
  const fallback = clamp(number(fallbackValue == null ? obj(anchor).fallback : fallbackValue), 0, index.total);
  const leftId = String(obj(anchor).leftId || COLLAB_DOCUMENT_ROOT);
  const rightId = obj(anchor).rightId == null ? null : String(anchor.rightId);
  if (anchor && anchor.affinity === "forward") {
    if (rightId != null && index.before.has(rightId)) return index.before.get(rightId);
    if (rightId == null) return index.total;
    if (index.after.has(leftId)) return index.after.get(leftId);
  } else {
    if (index.after.has(leftId)) return index.after.get(leftId);
    if (rightId != null && index.before.has(rightId)) return index.before.get(rightId);
  }
  return fallback;
};
const collabDocumentSelectionMapper = (beforeNodesValue, afterNodesValue) => {
  const beforeIndex = collabDocumentSelectionIndex(beforeNodesValue);
  const afterIndex = collabDocumentSelectionIndex(afterNodesValue);
  return (offsetValue, affinityValue = "backward") => {
    const anchor = collabDocumentCaptureBoundary(beforeIndex, offsetValue, affinityValue);
    return collabDocumentResolveBoundary(afterIndex, anchor, offsetValue);
  };
};
const collabDocumentChunkUpdates = (operations, seed) => {
  const updates = [];
  let nextOps = [];
  let nextBytes = new Blob([JSON.stringify({ format: COLLAB_DOCUMENT_FORMAT, ops: [] })]).size;
  operations.forEach(operation => {
    const operationBytes = new Blob([JSON.stringify(operation)]).size + (nextOps.length ? 1 : 0);
    if (
      nextOps.length
      && (nextOps.length >= COLLAB_DOCUMENT_UPDATE_CHUNK || nextBytes + operationBytes > COLLAB_DOCUMENT_MAX_UPDATE_BYTES)
    ) {
      updates.push({ client_update_id: `${seed}-${updates.length + 1}`, ops: nextOps, dispatched: false });
      nextOps = [];
      nextBytes = new Blob([JSON.stringify({ format: COLLAB_DOCUMENT_FORMAT, ops: [] })]).size;
    }
    nextOps.push(operation);
    nextBytes += operationBytes;
  });
  if (nextOps.length) updates.push({ client_update_id: `${seed}-${updates.length + 1}`, ops: nextOps, dispatched: false });
  return updates;
};
const collabDocumentMergePendingUpdates = (queue, incomingUpdates, lockFirst) => {
  const current = queue.updates.map(update => ({ ...update, ops: [...update.ops] }));
  const incoming = incomingUpdates.map(update => ({ ...update, ops: [...update.ops] }));
  const lastIndex = current.length - 1;
  const canMergeLast = lastIndex >= 0
    && current[lastIndex].dispatched !== true
    && (!lockFirst || lastIndex > 0);
  if (canMergeLast && incoming.length && current[lastIndex].ops.length < COLLAB_DOCUMENT_UPDATE_CHUNK) {
    const room = COLLAB_DOCUMENT_UPDATE_CHUNK - current[lastIndex].ops.length;
    let take = Math.min(room, incoming[0].ops.length);
    while (
      take > 0
      && new Blob([JSON.stringify({
        format: COLLAB_DOCUMENT_FORMAT,
        ops: [...current[lastIndex].ops, ...incoming[0].ops.slice(0, take)],
      })]).size > COLLAB_DOCUMENT_MAX_UPDATE_BYTES
    ) take -= 1;
    if (take > 0) {
      current[lastIndex] = {
        ...current[lastIndex],
        ops: [...current[lastIndex].ops, ...incoming[0].ops.slice(0, take)],
      };
      incoming[0] = { ...incoming[0], ops: incoming[0].ops.slice(take) };
    }
  }
  return { ...queue, updates: [...current, ...incoming.filter(update => update.ops.length)] };
};
const collabDocumentResponse = value => {
  const data = collabData(value);
  const seenAssets = new Set();
  const assets = arr(first(data.assets, obj(data.document).assets)).map(rawAsset => {
    const asset = obj(rawAsset);
    const assetKey = optionalText(asset.asset_key);
    const mimeType = key(asset.mime_type);
    if (
      !/^img_[A-Za-z0-9_-]{20,80}$/.test(assetKey)
      || seenAssets.has(assetKey)
      || !["image/png", "image/jpeg", "image/webp"].includes(mimeType)
    ) return null;
    seenAssets.add(assetKey);
    return {
      asset_key: assetKey,
      mime_type: mimeType,
      file_name: optionalText(asset.file_name),
      byte_size: number(asset.byte_size),
      width: number(asset.width),
      height: number(asset.height),
      alt_text: optionalText(asset.alt_text),
      created_at: optionalText(asset.created_at),
    };
  }).filter(Boolean);
  return {
    document: obj(data.document),
    snapshot: obj(first(data.snapshot, obj(data.document).snapshot, { format: COLLAB_DOCUMENT_FORMAT, nodes: [] })),
    content: optionalText(data.content),
    capabilities: obj(first(data.capabilities, obj(data.document).capabilities)),
    assets,
  };
};

const collabDocumentAssetToken = /!\[([^\]\n]{0,160})\]\(w2-image:(img_[A-Za-z0-9_-]{20,80})\)/g;
const collabDocumentImageCache = new Map();
const collabDocumentImageCacheKey = (tenant, taskId, assetKey) => JSON.stringify([
  String(tenant || ""), String(taskId || ""), String(assetKey || ""),
]);
const collabDocumentAcquireImage = (tenant, taskId, asset) => {
  const cacheKey = collabDocumentImageCacheKey(tenant, taskId, asset.asset_key);
  let entry = collabDocumentImageCache.get(cacheKey);
  if (!entry) {
    const controller = new AbortController();
    entry = { cacheKey, controller, refs: 0, url: "", promise: null };
    entry.promise = W2.fetch(
      `/api/tasks/${encodeURIComponent(taskId)}/collaboration/document/images/${encodeURIComponent(asset.asset_key)}`,
      { signal: controller.signal, cache: "no-store" }
    ).then(async response => {
      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(payload.error || payload.message || response.statusText);
      }
      const blob = await response.blob();
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(key(blob.type))) {
        throw new Error('invalid collaboration image response');
      }
      if (collabDocumentImageCache.get(cacheKey) !== entry || entry.refs < 1) return '';
      entry.url = window.URL.createObjectURL(blob);
      return entry.url;
    });
    collabDocumentImageCache.set(cacheKey, entry);
  }
  entry.refs += 1;
  return entry;
};
const collabDocumentReleaseImage = entry => {
  if (!entry) return;
  entry.refs = Math.max(0, entry.refs - 1);
  if (entry.refs > 0) return;
  if (collabDocumentImageCache.get(entry.cacheKey) === entry) {
    collabDocumentImageCache.delete(entry.cacheKey);
  }
  if (entry.url) window.URL.revokeObjectURL(entry.url);
  else entry.controller.abort();
};
const collabDocumentAssetAlt = asset => optionalText(
  obj(asset).alt_text, obj(asset).file_name, t('圖片')
).replace(/[\]\\|\r\n]/g, ' ').trim().slice(0, 160);
const COLLAB_DOCUMENT_STYLE_RE = /^<!-- w2-style:v1 rev=(\d{1,16}) actor=([A-Za-z0-9._:-]{1,80}) font=(swiss|editorial|mono) size=(sm|md|lg) -->$/;
const COLLAB_DOCUMENT_FORMULA_RE = /^\s*\\\[([\s\S]{0,512})\\\]\s*$/;
const COLLAB_DOCUMENT_IMAGE_LINE_RE = /^!\[([^\]\n]{0,160})\]\(w2-image:(img_[A-Za-z0-9_-]{20,80})\)$/;
const collabDocumentStyle = contentValue => {
  const lines = String(contentValue || "").split("\n");
  const candidates = [];
  let lineCount = 0;
  while (lineCount < Math.min(lines.length, 8)) {
    const match = lines[lineCount].match(COLLAB_DOCUMENT_STYLE_RE);
    if (!match) break;
    candidates.push({
      rev: Number(match[1]), actor: match[2], font: match[3], size: match[4],
    });
    lineCount += 1;
  }
  candidates.sort((left, right) => left.rev - right.rev || left.actor.localeCompare(right.actor));
  return { font: "swiss", size: "md", ...(candidates[candidates.length - 1] || {}), lineCount };
};
const collabDocumentStyleToken = (fontValue, sizeValue, actorValue) => {
  const font = ["swiss", "editorial", "mono"].includes(fontValue) ? fontValue : "swiss";
  const size = ["sm", "md", "lg"].includes(sizeValue) ? sizeValue : "md";
  const actor = String(actorValue || "client").replace(/[^A-Za-z0-9._:-]/g, "").slice(0, 80) || "client";
  return `<!-- w2-style:v1 rev=${Date.now()} actor=${actor} font=${font} size=${size} -->`;
};
const collabDocumentLineRecords = contentValue => {
  const content = String(contentValue || "");
  const lines = content.split("\n");
  let offset = 0;
  return lines.map((value, index) => {
    const record = { value, index, start: offset, end: offset + value.length };
    offset = record.end + (index < lines.length - 1 ? 1 : 0);
    return record;
  });
};
const collabDocumentPipeEscaped = (line, index) => {
  let slashes = 0;
  for (let cursor = index - 1; cursor >= 0 && line[cursor] === "\\"; cursor -= 1) slashes += 1;
  return slashes % 2 === 1;
};
const collabDocumentUnescapeTableCell = value => String(value || "").replace(/\\([\\|])/g, "$1");
const collabDocumentEscapeTableCell = value => String(value == null ? "" : value)
  .replace(/[\r\n]+/g, " ")
  .replace(/\\/g, "\\\\")
  .replace(/\|/g, "\\|");
const collabDocumentTableRawOffset = (rawValue, visibleOffsetValue) => {
  const raw = String(rawValue || "");
  const target = Math.max(0, number(visibleOffsetValue));
  let source = 0;
  let visible = 0;
  while (source < raw.length && visible < target) {
    source += raw[source] === "\\" && source + 1 < raw.length && /[\\|]/.test(raw[source + 1]) ? 2 : 1;
    visible += 1;
  }
  return source;
};
const collabDocumentTableVisibleOffset = (rawValue, sourceOffsetValue, affinityValue = "backward") => {
  const raw = String(rawValue || "");
  const target = clamp(number(sourceOffsetValue), 0, raw.length);
  const affinity = affinityValue === "forward" ? "forward" : "backward";
  let source = 0;
  let visible = 0;
  while (source < raw.length && source < target) {
    const width = raw[source] === "\\" && source + 1 < raw.length && /[\\|]/.test(raw[source + 1]) ? 2 : 1;
    if (source + width > target) return affinity === "forward" ? visible + 1 : visible;
    source += width;
    visible += 1;
  }
  return visible;
};
const collabDocumentParseTableLine = (lineValue, lineOffset = 0) => {
  const sourceLine = String(lineValue || "");
  const leadingWhitespace = (sourceLine.match(/^\s*/) || [""])[0].length;
  const trailingWhitespace = (sourceLine.match(/\s*$/) || [""])[0].length;
  const contentEndIndex = Math.max(leadingWhitespace, sourceLine.length - trailingWhitespace);
  const line = sourceLine.slice(leadingWhitespace, contentEndIndex);
  const contentOffset = lineOffset + leadingWhitespace;
  if (!line) return null;
  const pipes = [];
  for (let index = 0; index < line.length; index += 1) {
    if (line[index] === "|" && !collabDocumentPipeEscaped(line, index)) pipes.push(index);
  }
  if (!pipes.length) return null;
  const leadingPipe = pipes[0] === 0;
  const trailingPipe = pipes[pipes.length - 1] === line.length - 1;
  const regions = [];
  let cursor = leadingPipe ? 1 : 0;
  pipes.forEach(pipe => {
    if (pipe < cursor) return;
    regions.push([cursor, pipe]);
    cursor = pipe + 1;
  });
  if (cursor < line.length || !trailingPipe) regions.push([cursor, line.length]);
  if (regions.length < 2 || regions.length > 12) return null;
  const cells = regions.map(([segmentStart, segmentEnd]) => {
    const segment = line.slice(segmentStart, segmentEnd);
    const leading = (segment.match(/^\s*/) || [""])[0].length;
    const trailing = (segment.match(/\s*$/) || [""])[0].length;
    const contentStart = Math.min(segmentEnd, segmentStart + leading);
    const contentEnd = Math.max(contentStart, segmentEnd - trailing);
    return {
      value: collabDocumentUnescapeTableCell(line.slice(contentStart, contentEnd)),
      raw: line.slice(contentStart, contentEnd),
      sourceStart: contentOffset + contentStart,
      sourceEnd: contentOffset + contentEnd,
      segmentStart: contentOffset + segmentStart,
      segmentEnd: contentOffset + segmentEnd,
    };
  });
  return {
    cells, leadingPipe, trailingPipe, source: sourceLine,
    trailingPipeOffset: trailingPipe ? contentOffset + pipes[pipes.length - 1] : null,
    start: lineOffset, end: lineOffset + sourceLine.length, contentStart: contentOffset,
    contentEnd: contentOffset + line.length,
  };
};
const collabDocumentTableCells = lineValue => {
  const parsed = collabDocumentParseTableLine(String(lineValue || "").trim(), 0);
  return parsed ? parsed.cells.map(cell => cell.value.trim()) : [];
};
const collabDocumentTableDivider = (lineValue, columnCount = null) => {
  const cells = collabDocumentTableCells(lineValue);
  return cells.length >= 2
    && (columnCount == null || cells.length === columnCount)
    && cells.every(cell => /^:?-{3,}:?$/.test(cell));
};
const collabDocumentParseTableAt = (records, index) => {
  if (index + 1 >= records.length) return null;
  const header = collabDocumentParseTableLine(records[index].value, records[index].start);
  const divider = collabDocumentParseTableLine(records[index + 1].value, records[index + 1].start);
  if (
    !header || !divider || header.cells.length < 2
    || divider.cells.length !== header.cells.length
    || !divider.cells.every(cell => /^:?-{3,}:?$/.test(cell.value.trim()))
  ) return null;
  const rows = [];
  let cursor = index + 2;
  let overflow = false;
  while (cursor < records.length && records[cursor].value.trim()) {
    const row = collabDocumentParseTableLine(records[cursor].value, records[cursor].start);
    if (!row || row.cells.length !== header.cells.length) break;
    if (rows.length >= COLLAB_DOCUMENT_MAX_TABLE_ROWS) {
      overflow = true;
      break;
    }
    rows.push(row);
    cursor += 1;
  }
  if (overflow) return null;
  const lines = [header, divider, ...rows];
  return {
    type: "table", lineIndex: index, start: header.start, end: lines[lines.length - 1].end,
    header, divider, rows, lines, columnCount: header.cells.length, nextLine: cursor,
  };
};
const collabDocumentParseFormulaLine = record => {
  const match = record.value.match(COLLAB_DOCUMENT_FORMULA_RE);
  if (!match) return null;
  const open = record.value.indexOf("\\[");
  const close = record.value.lastIndexOf("\\]");
  return {
    type: "formula", lineIndex: record.index, start: record.start, end: record.end,
    sourceStart: record.start + open + 2, sourceEnd: record.start + close, value: match[1],
  };
};
const collabDocumentParseBlocks = contentValue => {
  const content = String(contentValue || "");
  const records = collabDocumentLineRecords(content);
  const style = collabDocumentStyle(content);
  const blocks = [];
  let formulaCount = 0;
  let index = style.lineCount;
  while (index < records.length && blocks.length < COLLAB_DOCUMENT_MAX_PREVIEW_BLOCKS) {
    const table = collabDocumentParseTableAt(records, index);
    if (table) {
      blocks.push(table);
      index = table.nextLine;
      continue;
    }
    const formula = collabDocumentParseFormulaLine(records[index]);
    if (formula && formulaCount < COLLAB_DOCUMENT_MAX_FORMULAS) {
      blocks.push(formula);
      formulaCount += 1;
      index += 1;
      continue;
    }
    const image = records[index].value.match(COLLAB_DOCUMENT_IMAGE_LINE_RE);
    if (image) {
      blocks.push({
        type: "image", lineIndex: index, start: records[index].start, end: records[index].end,
        alt: image[1], assetKey: image[2], altStart: records[index].start + 2,
        altEnd: records[index].start + 2 + image[1].length,
      });
      index += 1;
      continue;
    }
    const heading = records[index].value.match(/^(#{1,3})\s+(.*)$/);
    const list = !heading ? records[index].value.match(/^((?:[-*])|(?:\d+\.))\s+(.*)$/) : null;
    const prefixLength = heading ? heading[1].length + 1 : list ? list[1].length + 1 : 0;
    blocks.push({
      type: "text", lineIndex: index, start: records[index].start, end: records[index].end,
      sourceStart: records[index].start + prefixLength, sourceEnd: records[index].end,
      value: heading ? heading[2] : list ? list[2] : records[index].value,
      level: heading ? heading[1].length : 0,
      listMarker: list ? list[1] : "", source: records[index].value,
    });
    index += 1;
  }
  if (index < records.length) {
    blocks.push({
      type: "source", lineIndex: index, start: records[index].start, end: content.length,
      value: content.slice(records[index].start),
    });
  }
  return { blocks, style };
};

const collabFormulaForbidden = /\\(?:href|url|includegraphics|input|write|html|class|style|def|newcommand|require)\b/i;
const collabFormulaNormalize = value => {
  let formula = String(value || "").slice(0, COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS).trim();
  const fullWidth = { "＝": "=", "＋": "+", "－": "-", "＊": "*", "／": "/", "（": "(", "）": ")" };
  formula = formula.replace(/[＝＋－＊／（）]/g, character => fullWidth[character] || character);
  formula = formula.replace(/\*\*/g, "^")
    .replace(/!=/g, "\\ne ").replace(/<=/g, "\\le ").replace(/>=/g, "\\ge ")
    .replace(/\bsqrt\s*\(([^()]{1,180})\)/gi, "\\sqrt{$1}");
  const greek = { alpha: "alpha", beta: "beta", gamma: "gamma", delta: "delta", theta: "theta", lambda: "lambda", mu: "mu", pi: "pi", sigma: "sigma", phi: "phi", omega: "omega" };
  Object.keys(greek).forEach(name => {
    formula = formula.replace(new RegExp(`(^|[^\\\\A-Za-z])${name}(?=$|[^A-Za-z])`, "gi"), `$1\\${greek[name]}`);
  });
  const fraction = formula.match(/^([A-Za-z0-9]+(?:\^[A-Za-z0-9]+)?)\s*\/\s*([A-Za-z0-9]+(?:\^[A-Za-z0-9]+)?)$/);
  if (fraction) formula = `\\frac{${fraction[1]}}{${fraction[2]}}`;
  return formula.replace(/\s+/g, " ").trim();
};
const collabFormulaAst = formulaValue => {
  const source = collabFormulaNormalize(formulaValue);
  if (!source || source.length > COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS || collabFormulaForbidden.test(source)) {
    return { valid: false, source };
  }
  let cursor = 0;
  let nodeCount = 0;
  let valid = true;
  const make = (type, extra = {}) => {
    nodeCount += 1;
    if (nodeCount > COLLAB_DOCUMENT_MAX_FORMULA_NODES) valid = false;
    return { type, ...extra };
  };
  const symbols = {
    alpha: "α", beta: "β", gamma: "γ", delta: "δ", theta: "θ", lambda: "λ", mu: "μ", pi: "π", sigma: "σ", phi: "φ", omega: "ω",
    sum: "∑", prod: "∏", int: "∫", lim: "lim", le: "≤", ge: "≥", ne: "≠", times: "×", div: "÷", pm: "±", infty: "∞",
  };
  const parseSequence = (stop = "", depth = 0) => {
    if (depth > COLLAB_DOCUMENT_MAX_FORMULA_DEPTH) {
      valid = false;
      return make("row", { children: [] });
    }
    const children = [];
    const argument = () => {
      while (source[cursor] === " ") cursor += 1;
      if (source[cursor] === "{") {
        cursor += 1;
        const result = parseSequence("}", depth + 1);
        if (source[cursor] !== "}") valid = false;
        else cursor += 1;
        return result;
      }
      if (cursor >= source.length) {
        valid = false;
        return make("text", { value: "" });
      }
      const character = source[cursor++];
      return make(/[0-9]/.test(character) ? "number" : "identifier", { value: character });
    };
    while (cursor < source.length && (!stop || source[cursor] !== stop)) {
      const character = source[cursor];
      if (character === "\\") {
        cursor += 1;
        const match = source.slice(cursor).match(/^[A-Za-z]+/);
        if (!match) {
          valid = false;
          break;
        }
        const command = match[0];
        cursor += command.length;
        if (command === "frac") children.push(make("fraction", { numerator: argument(), denominator: argument() }));
        else if (command === "sqrt") children.push(make("sqrt", { body: argument() }));
        else if (command === "text") children.push(make("text", { value: collabFormulaPlainText(argument()) }));
        else if (Object.prototype.hasOwnProperty.call(symbols, command)) children.push(make(command === "lim" ? "text" : "operator", { value: symbols[command] }));
        else {
          valid = false;
          break;
        }
        continue;
      }
      if (character === "^" || character === "_") {
        cursor += 1;
        if (!children.length) {
          valid = false;
          break;
        }
        const base = children.pop();
        const script = argument();
        if (base.type === "scripts") {
          children.push(make("scripts", { base: base.base, sub: character === "_" ? script : base.sub, sup: character === "^" ? script : base.sup }));
        } else children.push(make("scripts", { base, sub: character === "_" ? script : null, sup: character === "^" ? script : null }));
        continue;
      }
      if (character === "{") {
        cursor += 1;
        const group = parseSequence("}", depth + 1);
        if (source[cursor] !== "}") valid = false;
        else cursor += 1;
        children.push(group);
        continue;
      }
      if (character === "}") break;
      if (/\s/.test(character)) {
        cursor += 1;
        children.push(make("space"));
        continue;
      }
      const numberMatch = source.slice(cursor).match(/^\d+(?:\.\d+)?/);
      if (numberMatch) {
        cursor += numberMatch[0].length;
        children.push(make("number", { value: numberMatch[0] }));
        continue;
      }
      const identifierMatch = source.slice(cursor).match(/^[A-Za-z]+/);
      if (identifierMatch) {
        cursor += identifierMatch[0].length;
        children.push(make("identifier", { value: identifierMatch[0] }));
        continue;
      }
      cursor += 1;
      children.push(make(/[=+\-*/<>()[\],.:×÷≤≥≠]/.test(character) ? "operator" : "identifier", { value: character }));
    }
    return make("row", { children });
  };
  const ast = parseSequence("", 0);
  if (cursor !== source.length) valid = false;
  return { valid: valid && nodeCount <= COLLAB_DOCUMENT_MAX_FORMULA_NODES, source, ast };
};
function collabFormulaPlainText(node) {
  if (!node) return "";
  if (node.value != null) return String(node.value);
  if (node.children) return node.children.map(collabFormulaPlainText).join("");
  return "";
}
const collabFormulaElement = (node, path = "m") => {
  if (!node) return <mrow key={path}/>;
  if (node.type === "row") return <mrow key={path}>{node.children.map((child, index) => collabFormulaElement(child, `${path}-${index}`))}</mrow>;
  if (node.type === "number") return <mn key={path}>{node.value}</mn>;
  if (node.type === "identifier") return <mi key={path}>{node.value}</mi>;
  if (node.type === "operator") return <mo key={path}>{node.value}</mo>;
  if (node.type === "text") return <mtext key={path}>{node.value}</mtext>;
  if (node.type === "space") return <mspace key={path} width=".35em"/>;
  if (node.type === "fraction") return <mfrac key={path}>{collabFormulaElement(node.numerator, `${path}-n`)}{collabFormulaElement(node.denominator, `${path}-d`)}</mfrac>;
  if (node.type === "sqrt") return <msqrt key={path}>{collabFormulaElement(node.body, `${path}-r`)}</msqrt>;
  if (node.type === "scripts") {
    if (node.sub && node.sup) return <msubsup key={path}>{collabFormulaElement(node.base, `${path}-b`)}{collabFormulaElement(node.sub, `${path}-s`)}{collabFormulaElement(node.sup, `${path}-p`)}</msubsup>;
    if (node.sub) return <msub key={path}>{collabFormulaElement(node.base, `${path}-b`)}{collabFormulaElement(node.sub, `${path}-s`)}</msub>;
    return <msup key={path}>{collabFormulaElement(node.base, `${path}-b`)}{collabFormulaElement(node.sup, `${path}-p`)}</msup>;
  }
  return <mtext key={path}>{collabFormulaPlainText(node)}</mtext>;
};
const CollaborativeDocumentFormulaMath = ({ value }) => {
  const parsed = collabFormulaAst(value);
  return parsed.valid
    ? <math display="block" aria-label={parsed.source}>{collabFormulaElement(parsed.ast)}</math>
    : <code>{String(value || "")}</code>;
};

const collabDocumentInlineCharacterEscaped = (source, index) => {
  let slashes = 0;
  for (let cursor = index - 1; cursor >= 0 && source[cursor] === "\\"; cursor -= 1) slashes += 1;
  return slashes % 2 === 1;
};
const collabDocumentEscapeInlineContent = value => String(value == null ? "" : value)
  .replace(/\\/g, "\\\\").replace(/\*/g, "\\*");
const collabDocumentUnescapeInlineContent = value => String(value || "").replace(/\\([\\*])/g, "$1");
const collabDocumentInlineRawToVisible = (rawValue, sourceOffsetValue) => {
  const raw = String(rawValue || "");
  const limit = clamp(number(sourceOffsetValue), 0, raw.length);
  let cursor = 0;
  let visible = 0;
  while (cursor < limit) {
    if (raw[cursor] === "\\" && cursor + 1 < raw.length && /[\\*]/.test(raw[cursor + 1])) {
      if (cursor + 1 >= limit) break;
      cursor += 2;
    } else cursor += 1;
    visible += 1;
  }
  return visible;
};
const collabDocumentInlineVisibleToRaw = (rawValue, visibleOffsetValue) => {
  const raw = String(rawValue || "");
  const target = Math.max(0, number(visibleOffsetValue));
  let cursor = 0;
  let visible = 0;
  while (cursor < raw.length && visible < target) {
    if (raw[cursor] === "\\" && cursor + 1 < raw.length && /[\\*]/.test(raw[cursor + 1])) cursor += 2;
    else cursor += 1;
    visible += 1;
  }
  return cursor;
};
const collabDocumentInlineParts = value => {
  const source = String(value || "");
  const parts = [];
  const pushText = (start, end) => {
    if (end <= start && source.length) return;
    const raw = source.slice(start, end);
    parts.push({
      type: "text", value: collabDocumentUnescapeInlineContent(raw), raw,
      start, contentStart: start, contentEnd: end, end,
    });
  };
  let emitted = 0;
  let scan = 0;
  while (scan < source.length) {
    if (source[scan] !== "*" || collabDocumentInlineCharacterEscaped(source, scan)) {
      scan += 1;
      continue;
    }
    let openingRun = 1;
    while (source[scan + openingRun] === "*") openingRun += 1;
    const markerLength = Math.min(3, openingRun);
    let close = -1;
    let cursor = scan + markerLength;
    let invalid = cursor >= source.length;
    while (!invalid && cursor < source.length) {
      if (source[cursor] === "\n") {
        invalid = true;
        break;
      }
      if (source[cursor] !== "*" || collabDocumentInlineCharacterEscaped(source, cursor)) {
        cursor += 1;
        continue;
      }
      let closingRun = 1;
      while (source[cursor + closingRun] === "*") closingRun += 1;
      if (closingRun >= markerLength) close = cursor;
      else invalid = true;
      break;
    }
    if (invalid || close <= scan + markerLength) {
      scan += openingRun;
      continue;
    }
    if (scan > emitted) pushText(emitted, scan);
    const raw = source.slice(scan + markerLength, close);
    parts.push({
      type: markerLength === 3 ? "bolditalic" : markerLength === 2 ? "bold" : "italic",
      value: collabDocumentUnescapeInlineContent(raw), raw, start: scan,
      contentStart: scan + markerLength, contentEnd: close, end: close + markerLength,
    });
    emitted = close + markerLength;
    scan = emitted;
  }
  if (emitted < source.length) pushText(emitted, source.length);
  if (!source.length) pushText(0, 0);
  return parts;
};
const collabDocumentInlineRuns = value => {
  let visibleOffset = 0;
  return collabDocumentInlineParts(value).map(part => {
    const start = visibleOffset;
    const end = start + part.value.length;
    visibleOffset = end;
    return {
      value: part.value, start, end,
      bold: part.type === "bold" || part.type === "bolditalic",
      italic: part.type === "italic" || part.type === "bolditalic",
    };
  });
};
const collabDocumentSerializeInlineRuns = runValues => {
  const merged = [];
  const append = run => {
    String(run.value || "").split(/(\n)/).forEach(value => {
      if (!value) return;
      if (value === "\n") {
        merged.push({ value, bold: false, italic: false });
        return;
      }
      const bold = run.bold === true;
      const italic = run.italic === true;
      const previous = merged[merged.length - 1];
      if (previous && previous.value !== "\n" && previous.bold === bold && previous.italic === italic) previous.value += value;
      else merged.push({ value, bold, italic });
    });
  };
  arr(runValues).forEach(append);
  return merged.map(run => {
    if (run.value === "\n") return "\n";
    const escaped = collabDocumentEscapeInlineContent(run.value);
    if (!run.bold && !run.italic) return escaped;
    return run.bold && run.italic ? `***${escaped}***`
      : run.bold ? `**${escaped}**` : `*${escaped}*`;
  }).join("");
};
const collabDocumentInlineRunSlice = (value, visibleStartValue, visibleEndValue) => {
  const start = Math.max(0, number(visibleStartValue));
  const end = Math.max(start, number(visibleEndValue));
  const slices = [];
  collabDocumentInlineRuns(value).forEach(run => {
    const overlapStart = Math.max(run.start, start);
    const overlapEnd = Math.min(run.end, end);
    if (overlapStart >= overlapEnd) return;
    slices.push({
      value: run.value.slice(overlapStart - run.start, overlapEnd - run.start),
      bold: run.bold, italic: run.italic,
    });
  });
  return slices;
};
const collabDocumentInlineSlice = (value, visibleStartValue, visibleEndValue) => (
  collabDocumentSerializeInlineRuns(collabDocumentInlineRunSlice(value, visibleStartValue, visibleEndValue))
);
const collabDocumentInlineElements = (value, keyPrefix = "inline") => collabDocumentInlineParts(value).map((part, index) => (
  part.type === "bold"
    ? <strong key={`${keyPrefix}-${index}`}>{part.value}</strong>
    : part.type === "bolditalic" ? <strong key={`${keyPrefix}-${index}`}><em>{part.value}</em></strong>
    : part.type === "italic" ? <em key={`${keyPrefix}-${index}`}>{part.value}</em>
    : <React.Fragment key={`${keyPrefix}-${index}`}>{part.value}</React.Fragment>
));
const collabDocumentRenderEditable = (root, value) => {
  if (!root) return false;
  const fragment = document.createDocumentFragment();
  collabDocumentInlineParts(value).forEach(part => {
    if (!part.value) return;
    const textNode = document.createTextNode(part.value);
    if (part.type === "bold") {
      const strong = document.createElement("strong");
      strong.appendChild(textNode);
      fragment.appendChild(strong);
      return;
    }
    if (part.type === "italic") {
      const emphasis = document.createElement("em");
      emphasis.appendChild(textNode);
      fragment.appendChild(emphasis);
      return;
    }
    if (part.type === "bolditalic") {
      const strong = document.createElement("strong");
      const emphasis = document.createElement("em");
      emphasis.appendChild(textNode);
      strong.appendChild(emphasis);
      fragment.appendChild(strong);
      return;
    }
    fragment.appendChild(textNode);
  });
  root.replaceChildren(fragment);
  return true;
};
const collabDocumentTextSurfaceTag = block => (
  block.level === 1 ? "h1" : block.level === 2 ? "h2" : block.level === 3 ? "h3" : "div"
);
const collabDocumentTextSurfaceClass = block => (
  `task-collab-document-paragraph${block.level ? ` is-heading-${block.level}` : ""}${block.listMarker ? " is-list" : ""}`
);
const collabDocumentRenderTextSurface = (root, blockValues, showPlaceholder = false) => {
  if (!root) return false;
  const blocks = arr(blockValues);
  const fragment = document.createDocumentFragment();
  blocks.forEach((block, index) => {
    const paragraph = document.createElement(collabDocumentTextSurfaceTag(block));
    paragraph.className = collabDocumentTextSurfaceClass(block);
    paragraph.dataset.collabLineIndex = String(block.lineIndex);
    if (block.listMarker) paragraph.dataset.listMarker = block.listMarker;
    if (showPlaceholder && index === 0 && !block.value) {
      paragraph.dataset.placeholder = t("開始整理共同目標、決定與下一步。");
      paragraph.setAttribute("aria-placeholder", t("開始整理共同目標、決定與下一步。"));
    }
    collabDocumentRenderEditable(paragraph, block.value);
    fragment.appendChild(paragraph);
  });
  root.replaceChildren(fragment);
  return true;
};
const collabDocumentTextSurfaceMatches = (root, blockValues, showPlaceholder = false) => {
  if (!root) return false;
  const blocks = arr(blockValues);
  const children = Array.from(root.children || []);
  if (children.length !== blocks.length) return false;
  return blocks.every((block, index) => {
    const paragraph = children[index];
    if (
      String(paragraph.tagName || "").toLowerCase() !== collabDocumentTextSurfaceTag(block)
      || paragraph.className !== collabDocumentTextSurfaceClass(block)
      || String(paragraph.dataset.collabLineIndex || "") !== String(block.lineIndex)
      || String(paragraph.dataset.listMarker || "") !== String(block.listMarker || "")
      || collabDocumentSerializeEditable(paragraph) !== block.value
    ) return false;
    if (!block.value && paragraph.childNodes.length) return false;
    const expectedPlaceholder = showPlaceholder && index === 0 && !block.value;
    return paragraph.hasAttribute("data-placeholder") === expectedPlaceholder;
  });
};
const collabDocumentTextSurfaceSnapshot = root => Array.from((root && root.children) || [])
  .map(paragraph => `${String(paragraph.dataset.collabLineIndex || "")}:${collabDocumentSerializeEditable(paragraph)}`)
  .join("\n");
const collabDocumentTextSurfaceProjection = (root, blockValues) => {
  if (!root) return { value: "", selection: null };
  const blocks = arr(blockValues);
  const byLine = new Map(blocks.map(block => [number(block.lineIndex), block]));
  const nodes = Array.from(root.childNodes || []).filter(node => (
    node.nodeType !== window.Node.TEXT_NODE || String(node.nodeValue || "").length > 0
  ));
  let cursor = 0;
  const projectedLinePrefixes = new Set();
  const parts = nodes.map((node, index) => {
    const hasLineIndex = node.nodeType === window.Node.ELEMENT_NODE
      && typeof node.hasAttribute === "function" && node.hasAttribute("data-collab-line-index");
    const lineIndex = hasLineIndex ? number(node.dataset.collabLineIndex) : Number.NaN;
    const block = Number.isFinite(lineIndex) ? byLine.get(lineIndex) : null;
    const usePrefix = block && !projectedLinePrefixes.has(lineIndex);
    if (block) projectedLinePrefixes.add(lineIndex);
    const prefix = usePrefix
      ? String(block.source || "").slice(0, block.sourceStart - block.start) : "";
    const body = collabDocumentSerializeEditable(node);
    const start = cursor + (index ? 1 : 0);
    cursor = start + prefix.length + body.length;
    return { node, prefix, body, start };
  });
  const value = parts.map(part => part.prefix + part.body).join("\n");
  const domSelection = window.getSelection && window.getSelection();
  if (!domSelection || !domSelection.rangeCount) return { value, selection: null };
  const range = domSelection.getRangeAt(0);
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) {
    return { value, selection: null };
  }
  const pointOffset = (container, offsetValue, affinity) => {
    if (container === root) {
      const boundary = clamp(number(offsetValue), 0, Array.from(root.childNodes || []).length);
      const before = new Set(Array.from(root.childNodes || []).slice(0, boundary));
      const included = parts.filter(part => before.has(part.node));
      const next = parts.find(part => !before.has(part.node));
      if (next && affinity === "forward") return next.start + next.prefix.length;
      if (included.length) {
        const previous = included[included.length - 1];
        return previous.start + previous.prefix.length + previous.body.length;
      }
      if (next) return next.start + next.prefix.length;
      return included.length ? value.length : 0;
    }
    const part = parts.find(item => (
      item.node === container
      || (typeof item.node.contains === "function" && item.node.contains(container))
    ));
    if (!part) return null;
    const visible = collabDocumentDomOffset(part.node, container, offsetValue);
    return part.start + part.prefix.length
      + collabDocumentInlineSourceOffset(part.body, visible, affinity);
  };
  const startAffinity = collabDocumentDomAffinity(range.startContainer, range.startOffset, "forward");
  const endAffinity = range.collapsed ? startAffinity
    : collabDocumentDomAffinity(range.endContainer, range.endOffset, "backward");
  const start = pointOffset(range.startContainer, range.startOffset, startAffinity);
  const end = pointOffset(range.endContainer, range.endOffset, endAffinity);
  if (start == null || end == null) return { value, selection: null };
  const direction = range.collapsed ? "none" : (
    domSelection.anchorNode === range.endContainer && domSelection.anchorOffset === range.endOffset
      ? "backward" : "forward"
  );
  return {
    value,
    selection: { start, end, startAffinity, endAffinity, direction },
  };
};
const collabDocumentSerializeTextSurface = (root, blockValues) => (
  collabDocumentTextSurfaceProjection(root, blockValues).value
);
const collabDocumentVisualGroups = blockValues => {
  const groups = [];
  arr(blockValues).forEach(block => {
    const previous = groups[groups.length - 1];
    if (block.type === "text" && previous && previous.type === "text-surface") {
      previous.blocks.push(block);
      previous.endLineIndex = block.lineIndex;
      return;
    }
    if (block.type === "text") {
      groups.push({
        type: "text-surface", lineIndex: block.lineIndex,
        endLineIndex: block.lineIndex, blocks: [block],
      });
      return;
    }
    groups.push(block);
  });
  return groups;
};
const collabDocumentStructuredRemoval = (contentValue, blockValue) => {
  const content = String(contentValue || "");
  const block = obj(blockValue);
  let start = clamp(number(block.start), 0, content.length);
  let end = clamp(number(block.end), start, content.length);
  if (end < content.length && content[end] === "\n") end += 1;
  else if (start > 0 && content[start - 1] === "\n") start -= 1;
  const expected = content.slice(start, end);
  const remaining = content.slice(0, start) + content.slice(end);
  const replacement = collabDocumentParseBlocks(remaining).blocks.length ? "" : "\n";
  return { start, end, expected, replacement };
};
const collabDocumentInlineSourceOffset = (value, visibleOffset, affinity = "backward") => {
  const source = String(value || "");
  const target = Math.max(0, number(visibleOffset));
  let visible = 0;
  for (const part of collabDocumentInlineParts(source)) {
    const partEnd = visible + part.value.length;
    if (target < partEnd || (target === partEnd && affinity !== "forward")) {
      const within = target - visible;
      return part.contentStart + collabDocumentInlineVisibleToRaw(part.raw, within);
    }
    visible = partEnd;
  }
  return source.length;
};
const collabDocumentInlineVisibleOffset = (value, sourceOffsetValue) => {
  const source = String(value || "");
  const target = clamp(number(sourceOffsetValue), 0, source.length);
  let visible = 0;
  for (const part of collabDocumentInlineParts(source)) {
    if (target <= part.start) return visible;
    if (target <= part.contentStart) return visible;
    if (target <= part.contentEnd) return visible + collabDocumentInlineRawToVisible(part.raw, target - part.contentStart);
    if (target <= part.end) return visible + part.value.length;
    visible += part.value.length;
  }
  return visible;
};
const collabDocumentFormatInline = (value, sourceStartValue, sourceEndValue, format, enabledValue = null) => {
  const source = String(value || "");
  const runs = collabDocumentInlineRuns(source);
  let visibleStart = collabDocumentInlineVisibleOffset(source, clamp(number(sourceStartValue), 0, source.length));
  let visibleEnd = collabDocumentInlineVisibleOffset(source, clamp(number(sourceEndValue), 0, source.length));
  if (visibleEnd < visibleStart) [visibleStart, visibleEnd] = [visibleEnd, visibleStart];
  if (visibleStart === visibleEnd) {
    const run = runs.find(item => visibleStart >= item.start && visibleStart < item.end)
      || [...runs].reverse().find(item => item.end === visibleStart && item.end > item.start);
    if (!run) return { value: source, sourceStart: number(sourceStartValue), sourceEnd: number(sourceEndValue), changed: false };
    visibleStart = run.start;
    visibleEnd = run.end;
  }
  if (visibleStart === visibleEnd || !["bold", "italic"].includes(format)) {
    return { value: source, sourceStart: number(sourceStartValue), sourceEnd: number(sourceEndValue), changed: false };
  }
  const selectedRuns = runs.filter(run => run.end > visibleStart && run.start < visibleEnd);
  const removeFormat = selectedRuns.length > 0 && selectedRuns.every(run => run[format] === true);
  const enabled = enabledValue == null ? !removeFormat : enabledValue === true;
  const nextRuns = [];
  const append = run => {
    if (!run.value) return;
    const previous = nextRuns[nextRuns.length - 1];
    if (previous && previous.bold === run.bold && previous.italic === run.italic) previous.value += run.value;
    else nextRuns.push({ value: run.value, bold: run.bold, italic: run.italic });
  };
  runs.forEach(run => {
    const selectedStart = Math.max(run.start, visibleStart);
    const selectedEnd = Math.min(run.end, visibleEnd);
    if (selectedStart >= selectedEnd) {
      append(run);
      return;
    }
    const beforeLength = selectedStart - run.start;
    const selectedLength = selectedEnd - selectedStart;
    append({ value: run.value.slice(0, beforeLength), bold: run.bold, italic: run.italic });
    append({ ...run, value: run.value.slice(beforeLength, beforeLength + selectedLength), [format]: enabled });
    append({ value: run.value.slice(beforeLength + selectedLength), bold: run.bold, italic: run.italic });
  });
  const next = collabDocumentSerializeInlineRuns(nextRuns);
  return {
    value: next,
    sourceStart: collabDocumentInlineSourceOffset(next, visibleStart, "forward"),
    sourceEnd: collabDocumentInlineSourceOffset(next, visibleEnd, "backward"),
    changed: next !== source,
  };
};
const collabDocumentSerializeEditable = root => {
  if (!root) return "";
  const segments = (node, inherited = { bold: false, italic: false }) => {
    if (node.nodeType === window.Node.TEXT_NODE) return [{ value: String(node.nodeValue || "").replace(/\u0000/g, ""), ...inherited }];
    if (node.nodeType !== window.Node.ELEMENT_NODE) return [];
    const tag = String(node.tagName || "").toLowerCase();
    if (["script", "style", "iframe", "object", "embed", "img", "svg"].includes(tag)) return [];
    if (tag === "br") return [{ value: "\n", bold: false, italic: false }];
    const formatting = {
      bold: inherited.bold || tag === "strong" || tag === "b",
      italic: inherited.italic || tag === "em" || tag === "i",
    };
    const body = Array.from(node.childNodes || []).flatMap(child => segments(child, formatting));
    if ((tag === "div" || tag === "p") && node !== root) body.push({ value: "\n", bold: false, italic: false });
    return body;
  };
  return collabDocumentSerializeInlineRuns(segments(root)).replace(/\n$/, "");
};
const collabDocumentDomOffset = (root, node, value) => {
  if (!root || !node) return 0;
  const probe = document.createRange();
  probe.selectNodeContents(root);
  try { probe.setEnd(node, value); } catch (error) { return 0; }
  return probe.toString().length;
};
const collabDocumentDomAffinity = (node, value, fallback = "backward") => {
  if (node && node.nodeType === window.Node.TEXT_NODE) {
    const length = String(node.nodeValue || "").length;
    if (value <= 0) return "forward";
    if (value >= length) return "backward";
  }
  if (node && node.nodeType === window.Node.ELEMENT_NODE) {
    return value < Array.from(node.childNodes || []).length ? "forward" : "backward";
  }
  return fallback;
};
const collabDocumentDomSelection = root => {
  const selection = window.getSelection && window.getSelection();
  if (!root || !selection || !selection.rangeCount) {
    return { start: 0, end: 0, startAffinity: "forward", endAffinity: "forward", contained: false };
  }
  const range = selection.getRangeAt(0);
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) {
    return { start: 0, end: 0, startAffinity: "forward", endAffinity: "forward", contained: false };
  }
  const start = collabDocumentDomOffset(root, range.startContainer, range.startOffset);
  const end = collabDocumentDomOffset(root, range.endContainer, range.endOffset);
  const startAffinity = collabDocumentDomAffinity(range.startContainer, range.startOffset, "forward");
  const endAffinity = range.collapsed
    ? startAffinity : collabDocumentDomAffinity(range.endContainer, range.endOffset, "backward");
  const direction = range.collapsed ? "none" : (
    selection.anchorNode === range.endContainer && selection.anchorOffset === range.endOffset
      ? "backward" : "forward"
  );
  return { start, end, startAffinity, endAffinity, direction, contained: true };
};
const collabDocumentClosestTextRoot = (visual, node) => {
  if (!visual || !node) return null;
  const element = node.nodeType === window.Node.ELEMENT_NODE ? node : node.parentElement;
  const root = element && typeof element.closest === "function"
    ? element.closest("[data-collab-line-index]") : null;
  return root && visual.contains(root) ? root : null;
};
const collabDocumentVisualTextSelection = (visual, blocks) => {
  const selection = window.getSelection && window.getSelection();
  if (!visual || !selection || !selection.rangeCount) return null;
  const range = selection.getRangeAt(0);
  const startRoot = collabDocumentClosestTextRoot(visual, range.startContainer);
  const endRoot = collabDocumentClosestTextRoot(visual, range.endContainer);
  if (!startRoot || !endRoot) return null;
  const byLine = blocks instanceof Map ? blocks
    : new Map(arr(blocks).filter(block => block.type === "text").map(block => [number(block.lineIndex), block]));
  const startBlock = byLine.get(number(startRoot.dataset.collabLineIndex));
  const endBlock = byLine.get(number(endRoot.dataset.collabLineIndex));
  if (!startBlock || !endBlock) return null;
  const startVisible = collabDocumentDomOffset(startRoot, range.startContainer, range.startOffset);
  const endVisible = collabDocumentDomOffset(endRoot, range.endContainer, range.endOffset);
  const startAffinity = collabDocumentDomAffinity(range.startContainer, range.startOffset, "forward");
  const endAffinity = range.collapsed ? startAffinity
    : collabDocumentDomAffinity(range.endContainer, range.endOffset, "backward");
  const direction = range.collapsed ? "none" : (
    selection.anchorNode === range.endContainer && selection.anchorOffset === range.endOffset
      ? "backward" : "forward"
  );
  const start = startBlock.sourceStart + collabDocumentInlineSourceOffset(startBlock.value, startVisible, startAffinity);
  const end = endBlock.sourceStart + collabDocumentInlineSourceOffset(endBlock.value, endVisible, endAffinity);
  return {
    start, end, startAffinity, endAffinity, direction, startVisible, endVisible,
    startLineIndex: startBlock.lineIndex, endLineIndex: endBlock.lineIndex,
    crossBlock: startRoot !== endRoot,
  };
};
const collabDocumentPlaceCaretFromPoint = (root, clientX, clientY) => {
  if (!root || !window.getSelection) return false;
  try { root.focus({ preventScroll: true }); } catch (error) { root.focus(); }
  let range = null;
  if (typeof document.caretPositionFromPoint === "function") {
    const point = document.caretPositionFromPoint(clientX, clientY);
    if (point) {
      range = document.createRange();
      try { range.setStart(point.offsetNode, point.offset); range.collapse(true); } catch (error) { range = null; }
    }
  }
  if (!range && typeof document.caretRangeFromPoint === "function") range = document.caretRangeFromPoint(clientX, clientY);
  if (!range || !root.contains(range.startContainer)) return false;
  try {
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    return true;
  } catch (error) {
    return false;
  }
};
const collabDocumentDomPoint = (root, targetValue, affinityValue = "backward") => {
  if (!root || !document.createTreeWalker) return null;
  const target = Math.max(0, number(targetValue));
  const affinity = affinityValue === "forward" ? "forward" : "backward";
  const walker = document.createTreeWalker(root, window.NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  let previous = null;
  let consumed = 0;
  while (node) {
    const length = String(node.nodeValue || "").length;
    if (target < consumed + length) return [node, Math.max(0, target - consumed)];
    if (target === consumed) {
      if (affinity === "forward" || !previous) return [node, 0];
      return [previous, String(previous.nodeValue || "").length];
    }
    if (target === consumed + length && affinity !== "forward") return [node, length];
    consumed += length;
    previous = node;
    node = walker.nextNode();
  }
  return previous ? [previous, String(previous.nodeValue || "").length] : [root, 0];
};
const collabDocumentRestoreDomRange = (
  startRoot, startValue, endRoot, endValue,
  startAffinityValue = "backward", endAffinityValue = "backward", directionValue = "forward"
) => {
  if (!startRoot || !endRoot || !window.getSelection || !document.createRange) return false;
  const start = Math.max(0, number(startValue));
  const end = Math.max(0, number(endValue));
  const startAffinity = startAffinityValue === "forward" ? "forward" : "backward";
  const endAffinity = startRoot === endRoot && start === end ? startAffinity
    : endAffinityValue === "forward" ? "forward" : "backward";
  const startPoint = collabDocumentDomPoint(startRoot, start, startAffinity);
  const endPoint = collabDocumentDomPoint(endRoot, end, endAffinity);
  if (!startPoint || !endPoint) return false;
  const range = document.createRange();
  try {
    range.setStart(startPoint[0], startPoint[1]);
    range.setEnd(endPoint[0], endPoint[1]);
    const selection = window.getSelection();
    selection.removeAllRanges();
    if (directionValue === "backward" && typeof selection.setBaseAndExtent === "function") {
      selection.setBaseAndExtent(endPoint[0], endPoint[1], startPoint[0], startPoint[1]);
    } else selection.addRange(range);
    return true;
  } catch (error) {
    return false;
  }
};
const collabDocumentRestoreDomSelection = (
  root, startValue, endValue, startAffinityValue = "backward", endAffinityValue = "backward"
) => {
  const start = Math.max(0, number(startValue));
  const end = Math.max(start, number(endValue));
  return collabDocumentRestoreDomRange(
    root, start, root, end, startAffinityValue, endAffinityValue
  );
};
const COLLAB_DOCUMENT_INTERNAL_CLIPBOARD_MIME = "application/x-warehouse-collaboration-document";
const collabDocumentHtmlEscape = value => String(value == null ? "" : value)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
const collabDocumentInlineClipboard = (value, startValue, endValue) => {
  const runs = collabDocumentInlineRunSlice(value, startValue, endValue);
  const canonical = collabDocumentSerializeInlineRuns(runs);
  const plain = runs.map(run => run.value).join("");
  const html = runs.map(run => {
    let body = collabDocumentHtmlEscape(run.value).replace(/\n/g, "<br>");
    if (run.italic) body = `<em>${body}</em>`;
    if (run.bold) body = `<strong>${body}</strong>`;
    return body;
  }).join("");
  return { canonical, plain, html };
};
const collabDocumentSelectionClipboard = (contentValue, blockValues, selectedValue) => {
  const content = String(contentValue || "");
  const selected = obj(selectedValue);
  const start = clamp(number(selected.start), 0, content.length);
  const end = clamp(number(selected.end), start, content.length);
  if (start === end) return null;
  const firstLine = Math.min(number(selected.startLineIndex), number(selected.endLineIndex));
  const lastLine = Math.max(number(selected.startLineIndex), number(selected.endLineIndex));
  const canonical = [];
  const plain = [];
  const html = [];
  arr(blockValues).forEach(block => {
    if (number(block.lineIndex) < firstLine || number(block.lineIndex) > lastLine) return;
    if (block.type !== "text") {
      const from = Math.max(start, number(block.start));
      const to = Math.min(end, number(block.end));
      if (to <= from) return;
      const source = content.slice(from, to);
      canonical.push(source);
      plain.push(source);
      html.push(`<pre>${collabDocumentHtmlEscape(source)}</pre>`);
      return;
    }
    const visibleLength = collabDocumentInlineRuns(block.value).reduce((total, run) => total + run.value.length, 0);
    const visibleStart = number(block.lineIndex) === number(selected.startLineIndex)
      ? clamp(number(selected.startVisible), 0, visibleLength) : 0;
    const visibleEnd = number(block.lineIndex) === number(selected.endLineIndex)
      ? clamp(number(selected.endVisible), visibleStart, visibleLength) : visibleLength;
    const inline = collabDocumentInlineClipboard(block.value, visibleStart, visibleEnd);
    const wholeStart = visibleStart === 0 && visibleEnd > visibleStart;
    const prefix = wholeStart ? (block.level ? `${"#".repeat(block.level)} ` : block.listMarker ? `${block.listMarker} ` : "") : "";
    canonical.push(prefix + inline.canonical);
    plain.push((wholeStart && block.listMarker ? `${block.listMarker} ` : "") + inline.plain);
    const emptyEndpoint = visibleStart === visibleEnd && (
      number(block.lineIndex) === number(selected.startLineIndex)
      || number(block.lineIndex) === number(selected.endLineIndex)
    );
    if (emptyEndpoint) return;
    if (wholeStart && block.listMarker) {
      const ordered = /^\d+\.$/.test(block.listMarker);
      const ordinal = ordered ? clamp(parseInt(block.listMarker, 10) || 1, -999999, 999999) : 1;
      html.push(`<${ordered ? `ol start="${ordinal}"` : "ul"}><li>${inline.html}</li></${ordered ? "ol" : "ul"}>`);
    } else if (wholeStart && block.level) html.push(`<h${block.level}>${inline.html}</h${block.level}>`);
    else html.push(`<p>${inline.html}</p>`);
  });
  return { canonical: canonical.join("\n"), plain: plain.join("\n"), html: html.join("") };
};
const collabDocumentPlainClipboardCanonical = value => {
  const plain = String(value || "").replace(/\r\n?/g, "\n");
  const records = collabDocumentLineRecords(plain);
  const output = [];
  let index = 0;
  const plainInline = text => collabDocumentSerializeInlineRuns([{
    value: String(text || ""), bold: false, italic: false,
  }]);
  const tableLine = record => {
    const sourceLine = record && record.value != null ? record.value : obj(record).source;
    const parsed = collabDocumentParseTableLine(sourceLine, 0);
    if (!parsed) return plainInline(sourceLine);
    const cells = parsed.cells.map(cell => (
      collabDocumentEscapeTableCell(plainInline(cell.value))
    ));
    return `| ${cells.join(" | ")} |`;
  };
  while (index < records.length) {
    const record = records[index];
    const formula = record.value.match(COLLAB_DOCUMENT_FORMULA_RE);
    const image = record.value.match(COLLAB_DOCUMENT_IMAGE_LINE_RE);
    if (formula || image) {
      output.push(record.value);
      index += 1;
      continue;
    }
    const table = collabDocumentParseTableAt(records, index);
    if (table) {
      table.lines.forEach(line => output.push(tableLine(line)));
      index = table.nextLine;
      continue;
    }
    const prefixed = record.value.match(/^(\s*(?:#{1,3}\s+|(?:-|\*|\d+\.)\s+))(.*)$/);
    output.push(prefixed ? prefixed[1] + plainInline(prefixed[2]) : plainInline(record.value));
    index += 1;
  }
  return output.join("\n");
};
const collabDocumentClipboardCanonical = clipboardData => {
  if (!clipboardData) return "";
  const internal = String(clipboardData.getData(COLLAB_DOCUMENT_INTERNAL_CLIPBOARD_MIME) || "").replace(/\r\n?/g, "\n");
  const internalCharacters = Array.from(internal);
  if (
    internalCharacters.length > 0
    && internalCharacters.length <= COLLAB_DOCUMENT_MAX_CHARACTERS
    && internalCharacters.every(collabDocumentValidCharacter)
  ) return internal;
  const plain = String(clipboardData.getData("text/plain") || "").replace(/\r\n?/g, "\n");
  const html = String(clipboardData.getData("text/html") || "");
  const safePlain = () => collabDocumentPlainClipboardCanonical(plain);
  if (!html || typeof window.DOMParser !== "function") return safePlain();
  if (html.length > 128 * 1024) return safePlain();
  let parsed;
  try { parsed = new window.DOMParser().parseFromString(html, "text/html"); } catch (error) { return safePlain(); }
  let conversionFailed = false;
  const inlineSegments = (node, depth = 0, inherited = { bold: false, italic: false }) => {
    if (!node) return [];
    if (depth > 24) {
      conversionFailed = true;
      return [];
    }
    if (node.nodeType === window.Node.TEXT_NODE) return [{ value: String(node.nodeValue || "").replace(/\u0000/g, ""), ...inherited }];
    if (node.nodeType !== window.Node.ELEMENT_NODE) return [];
    const tag = String(node.tagName || "").toLowerCase();
    if (["script", "style", "iframe", "object", "embed", "img", "svg", "video", "audio"].includes(tag)) return [];
    if (tag === "table") {
      conversionFailed = true;
      return [];
    }
    if (tag === "br") return [{ value: "\n", bold: false, italic: false }];
    const style = node.style || {};
    const weight = String(style.fontWeight || "").trim().toLowerCase();
    const fontStyle = String(style.fontStyle || "").trim().toLowerCase();
    const numericWeight = /^[1-9]00$/.test(weight) ? Number(weight) : null;
    let bold = inherited.bold || tag === "strong" || tag === "b";
    let italic = inherited.italic || tag === "em" || tag === "i";
    if (weight === "normal" || (numericWeight != null && numericWeight <= 500)) bold = false;
    else if (weight === "bold" || weight === "bolder" || (numericWeight != null && numericWeight >= 600)) bold = true;
    if (fontStyle === "normal") italic = false;
    else if (fontStyle === "italic" || /^oblique(?:\s+-?(?:\d+(?:\.\d+)?|\.\d+)(?:deg|grad|rad|turn))?$/.test(fontStyle)) italic = true;
    return Array.from(node.childNodes || []).flatMap(child => inlineSegments(child, depth + 1, { bold, italic }));
  };
  const inlineCanonical = segments => collabDocumentSerializeInlineRuns(segments);
  const inline = (node, depth = 0) => inlineCanonical(inlineSegments(node, depth));
  const table = node => {
    const sourceRows = Array.from(node.rows || []);
    if (
      sourceRows.length > COLLAB_DOCUMENT_MAX_TABLE_ROWS + 1
      || sourceRows.some(row => {
        const cells = Array.from(row.cells || []);
        return cells.length < 2 || cells.length > 12 || cells.some(cell => number(cell.colSpan) > 1 || number(cell.rowSpan) > 1);
      })
    ) {
      conversionFailed = true;
      return "";
    }
    const rows = sourceRows.map(row => (
      Array.from(row.cells || []).map(cell => (
        collabDocumentEscapeTableCell(inline(cell).replace(/\s*\n\s*/g, " ").trim())
      ))
    )).filter(row => row.length >= 2);
    if (!rows.length) return "";
    const width = Math.max(...rows.map(row => row.length));
    if (width < 2) return "";
    const normalized = rows.map(row => Array.from({ length: width }, (_, index) => row[index] || ""));
    return [
      `| ${normalized[0].join(" | ")} |`,
      `| ${normalized[0].map(() => "---").join(" | ")} |`,
      ...normalized.slice(1).map(row => `| ${row.join(" | ")} |`),
    ].join("\n");
  };
  const list = (node, depth = 0) => {
    if (!node || depth > 20) {
      if (node) conversionFailed = true;
      return "";
    }
    const ordered = String(node.tagName || "").toLowerCase() === "ol";
    const items = Array.from(node.children || []).filter(child => String(child.tagName || "").toLowerCase() === "li");
    const lines = [];
    let ordinal = ordered ? clamp(number(node.start), -999999, 999999) : 0;
    items.forEach(item => {
      if (ordered && typeof item.hasAttribute === "function" && item.hasAttribute("value")) {
        ordinal = clamp(number(item.value), -999999, 999999);
      }
      let label = "";
      const nested = [];
      Array.from(item.childNodes || []).forEach(child => {
        const childTag = child.nodeType === window.Node.ELEMENT_NODE
          ? String(child.tagName || "").toLowerCase() : "";
        if (childTag === "ul" || childTag === "ol") nested.push(child);
        else {
          const value = inline(child, depth + 1);
          const blockChild = ["p", "div", "section", "article", "blockquote"].includes(childTag);
          if (blockChild && label && !label.endsWith("\n")) label += "\n";
          label += value;
          if (blockChild && label && !label.endsWith("\n")) label += "\n";
        }
      });
      const labelLines = label.split(/\n+/).map(value => value.trim()).filter(Boolean);
      if (labelLines.length) {
        lines.push(`${ordered ? `${ordinal}.` : "-"} ${labelLines[0]}`);
        labelLines.slice(1).forEach(value => lines.push(`  ${value}`));
      }
      if (ordered) ordinal += 1;
      nested.forEach(child => {
        const nestedValue = list(child, depth + 1);
        if (nestedValue) lines.push(nestedValue);
      });
    });
    return lines.join("\n");
  };
  const block = (node, depth = 0) => {
    if (!node) return "";
    if (depth > 20) {
      conversionFailed = true;
      return "";
    }
    if (node.nodeType === window.Node.TEXT_NODE) return inline(node);
    if (node.nodeType !== window.Node.ELEMENT_NODE) return "";
    const tag = String(node.tagName || "").toLowerCase();
    if (["script", "style", "iframe", "object", "embed", "img", "svg", "video", "audio"].includes(tag)) return "";
    if (tag === "table") return `${table(node)}\n\n`;
    if (/^h[1-6]$/.test(tag)) return `${"#".repeat(Math.min(3, Number(tag[1])))} ${inline(node).trim()}\n\n`;
    if (tag === "ul" || tag === "ol") {
      return `${list(node, depth)}\n\n`;
    }
    if (tag === "p") return `${inline(node).trimEnd()}\n\n`;
    if (tag === "body" || tag === "div" || tag === "section" || tag === "article" || tag === "main" || tag === "header" || tag === "footer" || tag === "blockquote") {
      let output = "";
      let inlineBuffer = "";
      const flushInline = () => {
        if (!inlineBuffer.trim()) {
          inlineBuffer = "";
          return;
        }
        output += `${inlineBuffer.trimEnd()}\n\n`;
        inlineBuffer = "";
      };
      Array.from(node.childNodes || []).forEach(child => {
        const childTag = child.nodeType === window.Node.ELEMENT_NODE
          ? String(child.tagName || "").toLowerCase() : "";
        if (/^h[1-6]$/.test(childTag) || ["p", "div", "section", "article", "main", "header", "footer", "blockquote", "ul", "ol", "table"].includes(childTag)) {
          flushInline();
          output += block(child, depth + 1);
        } else inlineBuffer += inline(child, depth + 1);
      });
      flushInline();
      return output;
    }
    return inline(node, depth + 1);
  };
  const converted = block(parsed.body).replace(/\n{3,}/g, "\n\n").trim();
  return conversionFailed ? safePlain() : converted || safePlain();
};

const CollaborativeDocumentImage = ({ taskId, asset, alt }) => {
  const tenant = W2.tenant();
  const [source, setSource] = S("");
  const [failed, setFailed] = S(false);
  E(() => {
    if (!asset || !asset.asset_key) return undefined;
    let active = true;
    setSource("");
    setFailed(false);
    const entry = collabDocumentAcquireImage(tenant, taskId, asset);
    entry.promise.then(objectUrl => {
      if (active && objectUrl && tenant === W2.tenant()) setSource(objectUrl);
    }).catch(exception => {
      if (active && (!exception || exception.name !== "AbortError")) setFailed(true);
    });
    return () => {
      active = false;
      collabDocumentReleaseImage(entry);
    };
  }, [taskId, tenant, asset && asset.asset_key]);
  if (failed) return <span className="task-collab-document-image-error" role="img" aria-label={alt || t("圖片無法載入")}>{t("圖片無法載入")}</span>;
  if (!source) return <span className="task-collab-document-image-loading" aria-label={t("同步中")}/>;
  return <img src={source} alt={alt || asset.alt_text || asset.file_name || ""} width={asset.width || undefined} height={asset.height || undefined} loading="lazy" decoding="async"/>;
};

const collabDocumentRichInline = (lineValue, taskId, assetMap, keyPrefix, imageBudget) => {
  const line = String(lineValue || "");
  const output = [];
  let cursor = 0;
  let match;
  collabDocumentAssetToken.lastIndex = 0;
  while ((match = collabDocumentAssetToken.exec(line)) !== null) {
    if (match.index > cursor) output.push(...collabDocumentInlineElements(line.slice(cursor, match.index), `${keyPrefix}-text-${cursor}`));
    const asset = assetMap.get(match[2]);
    const withinBudget = !imageBudget
      || imageBudget.count < COLLAB_DOCUMENT_MAX_PREVIEW_IMAGES;
    if (asset && withinBudget && imageBudget) imageBudget.count += 1;
    output.push(asset && withinBudget
      ? <CollaborativeDocumentImage key={`${keyPrefix}-${match.index}-${match[2]}`} taskId={taskId} asset={asset} alt={match[1]}/>
      : <span className="task-collab-document-image-error" key={`${keyPrefix}-${match.index}-missing`}>{t(asset ? "圖片預覽已達上限" : "圖片無法載入")}</span>);
    cursor = match.index + match[0].length;
  }
  if (cursor < line.length) output.push(...collabDocumentInlineElements(line.slice(cursor), `${keyPrefix}-text-${cursor}`));
  return output.length ? output : collabDocumentInlineElements(line, `${keyPrefix}-text`);
};

const CollaborativeDocumentPreview = ({ taskId, content, assets }) => {
  const assetMap = M(() => new Map(arr(assets).map(asset => [asset.asset_key, asset])), [assets]);
  const projection = M(() => collabDocumentParseBlocks(content), [content]);
  const rendered = [];
  const imageBudget = { count: 0 };
  projection.blocks.forEach((block, blockIndex) => {
    if (block.type === "table") {
      rendered.push(<div className="task-collab-document-table-wrap" key={`table-${block.lineIndex}`}><table>
        <thead><tr>{block.header.cells.map((cell, column) => <th key={column}>{collabDocumentRichInline(cell.value, taskId, assetMap, `th-${block.lineIndex}-${column}`, imageBudget)}</th>)}</tr></thead>
        <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>{block.header.cells.map((_, column) => <td key={column}>{collabDocumentRichInline(row.cells[column].value, taskId, assetMap, `td-${block.lineIndex}-${rowIndex}-${column}`, imageBudget)}</td>)}</tr>)}</tbody>
      </table></div>);
      return;
    }
    if (block.type === "formula") {
      rendered.push(<div className="task-collab-document-formula-preview" key={`formula-${block.lineIndex}`}><CollaborativeDocumentFormulaMath value={block.value}/></div>);
      return;
    }
    if (block.type === "image") {
      const asset = assetMap.get(block.assetKey);
      rendered.push(<p key={`image-${block.lineIndex}`}>{asset && imageBudget.count < COLLAB_DOCUMENT_MAX_PREVIEW_IMAGES
        ? <CollaborativeDocumentImage taskId={taskId} asset={asset} alt={block.alt}/>
        : <span className="task-collab-document-image-error">{t(asset ? "圖片預覽已達上限" : "圖片無法載入")}</span>}</p>);
      if (asset) imageBudget.count += 1;
      return;
    }
    if (block.type === "source") {
      rendered.push(<pre className="task-collab-document-preview-limit" key={`source-${blockIndex}`}>{block.value}</pre>);
      return;
    }
    if (!block.value) {
      rendered.push(<div className="task-collab-document-spacer" key={`blank-${block.lineIndex}`} aria-hidden="true"/>);
      return;
    }
    const body = collabDocumentRichInline(block.value, taskId, assetMap, `line-${block.lineIndex}`, imageBudget);
    if (block.level === 1) rendered.push(<h1 key={`line-${block.lineIndex}`}>{body}</h1>);
    else if (block.level === 2) rendered.push(<h2 key={`line-${block.lineIndex}`}>{body}</h2>);
    else if (block.level === 3) rendered.push(<h3 key={`line-${block.lineIndex}`}>{body}</h3>);
    else if (block.listMarker) rendered.push(<p className="task-collab-document-list-line" key={`line-${block.lineIndex}`}><b aria-hidden="true">{block.listMarker}</b>{body}</p>);
    else rendered.push(<p key={`line-${block.lineIndex}`}>{body}</p>);
  });
  const fontClass = `is-font-${projection.style.font} is-size-${projection.style.size}`;
  return <div className={`task-collab-document-rich ${fontClass}`}><L dim>{t("安全圖文預覽")}</L>{rendered}</div>;
};

const CollaborativeDocumentTextSurface = ({ blocks, documentContent, readOnly, showPlaceholder, selectionRef, resolveSelection, onCopySelection, onReplace, onComposeStart, onComposeEnd, onBlur }) => {
  const rootRef = R(null);
  const compositionActive = R(false);
  const postCompositionValue = R(null);
  const postCompositionFrame = R(null);
  const lastCommittedValue = R(null);
  const structuralInputPending = R(false);
  const compositionSelection = R(null);
  const crossComposition = R(null);
  const surfaceBlocks = arr(blocks);
  const surfaceBlocksRef = R(surfaceBlocks);
  const showPlaceholderRef = R(showPlaceholder);
  surfaceBlocksRef.current = surfaceBlocks;
  showPlaceholderRef.current = showPlaceholder;
  const firstBlock = surfaceBlocks[0];
  const blockAtLine = lineIndex => surfaceBlocks.find(item => item.lineIndex === number(lineIndex)) || null;
  const paragraphForBlock = block => rootRef.current && block
    ? rootRef.current.querySelector(`[data-collab-line-index="${block.lineIndex}"]`) : null;
  const clearPostCompositionGuard = () => {
    if (postCompositionFrame.current != null) window.cancelAnimationFrame(postCompositionFrame.current);
    postCompositionFrame.current = null;
    postCompositionValue.current = null;
  };
  const armPostCompositionGuard = value => {
    clearPostCompositionGuard();
    postCompositionValue.current = value;
    postCompositionFrame.current = window.requestAnimationFrame(() => {
      postCompositionFrame.current = null;
      postCompositionValue.current = null;
    });
  };
  const rememberSelection = (activeValue = true) => {
    const root = rootRef.current;
    const local = collabDocumentDomSelection(root);
    const resolved = typeof resolveSelection === "function" ? resolveSelection(root) : null;
    if (!resolved && local.contained !== true) return { ...local, unresolved: true };
    const selection = resolved ? {
      ...local, start: resolved.startVisible, end: resolved.endVisible,
      startAffinity: resolved.startAffinity, endAffinity: resolved.endAffinity,
      sourceStart: resolved.start, sourceEnd: resolved.end,
      startLineIndex: resolved.startLineIndex, endLineIndex: resolved.endLineIndex,
      crossBlock: resolved.crossBlock, direction: resolved.direction || "none",
    } : local;
    const locked = selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true);
    if (locked) return selection;
    const startBlock = resolved ? blockAtLine(resolved.startLineIndex) : firstBlock;
    const endBlock = resolved ? blockAtLine(resolved.endLineIndex) : startBlock;
    if (!startBlock || !endBlock) return { ...selection, unresolved: true };
    const sourceStart = resolved ? resolved.start : startBlock.sourceStart + collabDocumentInlineSourceOffset(
      startBlock.value, selection.start, selection.startAffinity
    );
    const sourceEnd = resolved ? resolved.end : endBlock.sourceStart + collabDocumentInlineSourceOffset(
      endBlock.value, selection.end, selection.endAffinity
    );
    const current = selectionRef.current;
    const preserveAnchors = current && current.start === sourceStart && current.end === sourceEnd;
    selectionRef.current = {
      type: "text", lineIndex: resolved ? resolved.startLineIndex : startBlock.lineIndex,
      endLineIndex: resolved ? resolved.endLineIndex : endBlock.lineIndex,
      startVisible: selection.start, endVisible: selection.end,
      crossBlock: resolved ? resolved.crossBlock : false,
      start: sourceStart, end: sourceEnd,
      startAffinity: selection.startAffinity, endAffinity: selection.endAffinity,
      direction: selection.direction || "none",
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
      level: startBlock.level, active: activeValue !== false, restoring: false, pending: false,
    };
    return selection;
  };
  const commitRoot = fallbackSelection => {
    const root = rootRef.current;
    if (!root) return false;
    let selection = rememberSelection();
    if (selection.unresolved && fallbackSelection && fallbackSelection.crossBlock !== true) {
      selection = fallbackSelection;
    }
    if (selection.unresolved || selection.crossBlock) return false;
    const block = blockAtLine(selection.startLineIndex || selection.lineIndex) || firstBlock;
    const paragraph = paragraphForBlock(block);
    if (!block || !paragraph) return false;
    const next = collabDocumentSerializeEditable(paragraph);
    const commitKey = `${block.lineIndex}:${next}`;
    if (next === block.value || commitKey === lastCommittedValue.current) return true;
    const committed = onReplace(block.sourceStart, block.sourceEnd, next, block.value);
    if (committed) {
      lastCommittedValue.current = commitKey;
      const sourceStart = block.sourceStart + collabDocumentInlineSourceOffset(
        next, selection.start, selection.startAffinity
      );
      const sourceEnd = block.sourceStart + collabDocumentInlineSourceOffset(
        next, selection.end, selection.endAffinity
      );
      selectionRef.current = {
        type: "text", lineIndex: block.lineIndex, start: sourceStart, end: sourceEnd,
        startAffinity: selection.startAffinity, endAffinity: selection.endAffinity,
        level: block.level, active: true, pending: next.includes("\n"),
      };
    }
    if (committed && !next.includes("\n")) {
      window.requestAnimationFrame(() => {
        const current = rootRef.current;
        if (!current || document.activeElement !== current) return;
        collabDocumentRestoreDomSelection(
          paragraphForBlock(block), selection.start, selection.end, selection.startAffinity, selection.endAffinity
        );
      });
    }
    return committed;
  };
  const commitSurfaceStructure = () => {
    const root = rootRef.current;
    const first = surfaceBlocks[0];
    const last = surfaceBlocks[surfaceBlocks.length - 1];
    if (!root || !first || !last) return false;
    const projection = collabDocumentTextSurfaceProjection(root, surfaceBlocks);
    const next = projection.value;
    const expected = String(documentContent || "").slice(first.start, last.end);
    if (next === expected) return true;
    const committed = onReplace(first.start, last.end, next, expected);
    if (committed) {
      const projectedSelection = projection.selection || {
        start: next.length, end: next.length,
        startAffinity: "backward", endAffinity: "backward", direction: "none",
      };
      const relativeStart = clamp(number(projectedSelection.start), 0, next.length);
      const relativeEnd = clamp(number(projectedSelection.end), relativeStart, next.length);
      const parsedTextBlocks = collabDocumentParseBlocks(next).blocks.filter(block => block.type === "text");
      const blockFor = (position, affinity) => {
        const candidates = parsedTextBlocks.filter(block => (
          position >= block.sourceStart && position <= block.sourceEnd
        ));
        if (candidates.length) return affinity === "forward" ? candidates[candidates.length - 1] : candidates[0];
        return [...parsedTextBlocks].reverse().find(block => position >= block.start)
          || parsedTextBlocks[0] || null;
      };
      const startBlock = blockFor(relativeStart, projectedSelection.startAffinity);
      const endBlock = blockFor(relativeEnd, projectedSelection.endAffinity) || startBlock;
      selectionRef.current = {
        type: "text",
        lineIndex: first.lineIndex + number(startBlock && startBlock.lineIndex),
        endLineIndex: first.lineIndex + number(endBlock && endBlock.lineIndex),
        start: first.start + relativeStart, end: first.start + relativeEnd,
        startAffinity: projectedSelection.startAffinity,
        endAffinity: projectedSelection.endAffinity,
        direction: projectedSelection.direction,
        active: true, restoring: true, pending: true,
      };
    }
    return committed;
  };
  LE(() => {
    const root = rootRef.current;
    if (!root || compositionActive.current) return;
    if (lastCommittedValue.current != null && !surfaceBlocks.some(block => (
      lastCommittedValue.current === `${block.lineIndex}:${block.value}`
    ))) {
      lastCommittedValue.current = null;
    }
    if (collabDocumentTextSurfaceMatches(root, surfaceBlocks, showPlaceholder)) return;
    collabDocumentRenderTextSurface(root, surfaceBlocks, showPlaceholder);
  });
  const insertCanonical = (insertedValue, { allowEmpty = false, forceInline = false, selectionOverride = null } = {}) => {
    const inserted = String(insertedValue || "");
    if (!inserted && !allowEmpty) return false;
    const selection = selectionOverride || rememberSelection();
    if (selection.unresolved) return false;
    const insertedProjection = collabDocumentParseBlocks(inserted);
    const blockContent = !forceInline && (inserted.includes("\n") || insertedProjection.blocks.some(item => (
      ["table", "formula", "image"].includes(item.type)
      || (item.type === "text" && (item.level || item.listMarker))
    )));
    if (selection.crossBlock) {
      const before = String(documentContent || "");
      const textBlocks = collabDocumentParseBlocks(before).blocks.filter(item => item.type === "text");
      const startBlock = textBlocks.find(item => item.lineIndex === selection.startLineIndex)
        || textBlocks.find(item => number(selection.sourceStart) >= item.sourceStart && number(selection.sourceStart) <= item.sourceEnd);
      const endBlock = textBlocks.find(item => item.lineIndex === selection.endLineIndex)
        || [...textBlocks].reverse().find(item => number(selection.sourceEnd) >= item.sourceStart && number(selection.sourceEnd) <= item.sourceEnd);
      if (!startBlock || !endBlock) return false;
      const startVisible = clamp(number(selection.start), 0, collabDocumentInlineRuns(startBlock.value).reduce((total, run) => total + run.value.length, 0));
      const endVisible = clamp(number(selection.end), 0, collabDocumentInlineRuns(endBlock.value).reduce((total, run) => total + run.value.length, 0));
      const leftRuns = collabDocumentInlineRunSlice(startBlock.value, 0, startVisible);
      const rightRuns = collabDocumentInlineRunSlice(endBlock.value, endVisible, Number.MAX_SAFE_INTEGER);
      const left = collabDocumentSerializeInlineRuns(leftRuns);
      const right = collabDocumentSerializeInlineRuns(rightRuns);
      const replacePrefix = blockContent && !left && startBlock.sourceStart > startBlock.start;
      const replaceStart = replacePrefix ? startBlock.start : startBlock.sourceStart;
      const replaceEnd = endBlock.sourceEnd;
      let replacement;
      let relativeCaret;
      if (blockContent) {
        const rightPrefix = right && endBlock.sourceStart > endBlock.start
          ? before.slice(endBlock.start, endBlock.sourceStart) : "";
        const structuredRight = rightPrefix + right;
        const leading = left && !left.endsWith("\n") && !inserted.startsWith("\n") ? "\n" : "";
        const insertedEnd = left + leading + inserted;
        const trailing = structuredRight && !insertedEnd.endsWith("\n") && !structuredRight.startsWith("\n") ? "\n" : "";
        replacement = left + leading + inserted + trailing + structuredRight;
        relativeCaret = left.length + leading.length + inserted.length;
      } else {
        const insertedRuns = collabDocumentInlineRuns(inserted);
        const insertedLength = insertedRuns.reduce((total, run) => total + run.value.length, 0);
        replacement = collabDocumentSerializeInlineRuns([...leftRuns, ...insertedRuns, ...rightRuns]);
        relativeCaret = collabDocumentInlineSourceOffset(
          replacement, startVisible + insertedLength, "forward"
        );
      }
      const committed = onReplace(replaceStart, replaceEnd, replacement, before.slice(replaceStart, replaceEnd));
      if (committed) {
        const caret = replaceStart + relativeCaret;
        selectionRef.current = {
          type: "text", lineIndex: startBlock.lineIndex, endLineIndex: startBlock.lineIndex,
          start: caret, end: caret, startAffinity: "forward", endAffinity: "forward",
          active: true, restoring: true, pending: true,
        };
      }
      return committed;
    }
    const block = blockAtLine(selection.startLineIndex || selection.lineIndex) || firstBlock;
    if (!block) return false;
    const leftRuns = collabDocumentInlineRunSlice(block.value, 0, selection.start);
    const rightRuns = collabDocumentInlineRunSlice(block.value, selection.end, Number.MAX_SAFE_INTEGER);
    const left = collabDocumentSerializeInlineRuns(leftRuns);
    const right = collabDocumentSerializeInlineRuns(rightRuns);
    let leading = "";
    let next;
    let relativeCaret;
    if (blockContent) {
      const rightPrefix = right && block.sourceStart > block.start
        ? block.source.slice(0, block.sourceStart - block.start) : "";
      const structuredRight = rightPrefix + right;
      leading = left && !left.endsWith("\n") && !inserted.startsWith("\n") ? "\n" : "";
      const insertedEnd = left + leading + inserted;
      const trailing = structuredRight && !insertedEnd.endsWith("\n") && !structuredRight.startsWith("\n") ? "\n" : "";
      next = left + leading + inserted + trailing + structuredRight;
      relativeCaret = left.length + leading.length + inserted.length;
    } else {
      const insertedRuns = collabDocumentInlineRuns(inserted);
      const insertedLength = insertedRuns.reduce((total, run) => total + run.value.length, 0);
      next = collabDocumentSerializeInlineRuns([...leftRuns, ...insertedRuns, ...rightRuns]);
      relativeCaret = collabDocumentInlineSourceOffset(
        next, selection.start + insertedLength, "forward"
      );
    }
    const replacePrefix = blockContent && selection.start === 0 && block.sourceStart > block.start;
    const replaceStart = replacePrefix ? block.start : block.sourceStart;
    const committed = onReplace(replaceStart, block.sourceEnd, next, replacePrefix ? block.source : block.value);
    if (committed) {
      const caret = replaceStart + relativeCaret;
      selectionRef.current = {
        type: "text", lineIndex: block.lineIndex, start: caret, end: caret,
        startAffinity: "forward", endAffinity: "forward",
        level: block.level, active: true, pending: true,
      };
    }
    return committed;
  };
  const insertTransfer = transfer => insertCanonical(collabDocumentClipboardCanonical(transfer));
  const mergeTextBoundary = (event, inputType, selectionValue = null) => {
    const selection = selectionValue || rememberSelection();
    if (selection.unresolved || selection.crossBlock) return false;
    const block = blockAtLine(selection.startLineIndex || selection.lineIndex) || firstBlock;
    if (!block) return false;
    const collapsed = number(selection.start) === number(selection.end);
    const visibleLength = collabDocumentInlineRuns(block.value)
      .reduce((total, run) => total + run.value.length, 0);
    const backward = [
      "deleteContentBackward", "deleteWordBackward",
      "deleteSoftLineBackward", "deleteHardLineBackward",
    ].includes(inputType);
    const forward = [
      "deleteContentForward", "deleteWordForward",
      "deleteSoftLineForward", "deleteHardLineForward",
    ].includes(inputType);
    const atBackwardBoundary = collapsed && backward && number(selection.start) === 0;
    const atForwardBoundary = collapsed && forward && number(selection.end) === visibleLength;
    if (!atBackwardBoundary && !atForwardBoundary) return false;
    const before = String(documentContent || "");
    const blocks = collabDocumentParseBlocks(before).blocks;
    const blockIndex = blocks.findIndex(item => item.type === "text" && item.lineIndex === block.lineIndex);
    const neighbor = blockIndex < 0 ? null : blocks[blockIndex + (atBackwardBoundary ? -1 : 1)];
    if (!neighbor || neighbor.type !== "text") return false;
    const replaceStart = atBackwardBoundary ? neighbor.sourceEnd : block.sourceEnd;
    const replaceEnd = atBackwardBoundary ? block.sourceStart : neighbor.sourceStart;
    if (replaceEnd <= replaceStart) return false;
    event.preventDefault();
    if (!event.defaultPrevented) {
      structuralInputPending.current = inputType;
      return false;
    }
    const committed = onReplace(replaceStart, replaceEnd, "", before.slice(replaceStart, replaceEnd));
    if (committed) {
      selectionRef.current = {
        type: "text", lineIndex: atBackwardBoundary ? neighbor.lineIndex : block.lineIndex,
        start: replaceStart, end: replaceStart,
        startAffinity: "forward", endAffinity: "forward",
        active: true, restoring: true, pending: true,
      };
    }
    return true;
  };
  const insertTextLineBreak = selectionValue => {
    const selection = selectionValue || rememberSelection();
    if (selection.unresolved) return false;
    if (selection.crossBlock) {
      return insertCanonical("\n", { allowEmpty: true, selectionOverride: selection });
    }
    const block = blockAtLine(selection.startLineIndex || selection.lineIndex) || firstBlock;
    if (!block) return false;
    const left = collabDocumentInlineSlice(block.value, 0, selection.start);
    const right = collabDocumentInlineSlice(block.value, selection.end, Number.MAX_SAFE_INTEGER);
    const next = `${left}\n${right}`;
    const committed = onReplace(block.sourceStart, block.sourceEnd, next, block.value);
    if (committed) {
      const caret = block.sourceStart + left.length + 1;
      selectionRef.current = {
        type: "text", lineIndex: block.lineIndex, start: caret, end: caret,
        startAffinity: "forward", endAffinity: "forward",
        level: 0, active: true, restoring: true, pending: true,
      };
    }
    return committed;
  };
  const beforeInput = event => {
    if (readOnly) return;
    const nativeEvent = event.nativeEvent || event;
    if (compositionActive.current || nativeEvent.isComposing) return;
    const inputType = String(nativeEvent.inputType || "");
    if (postCompositionValue.current != null && [
      "insertCompositionText", "insertText", "insertReplacementText",
      "insertParagraph", "insertLineBreak",
    ].includes(inputType)) {
      event.preventDefault();
      return;
    }
    const selection = rememberSelection();
    if (selection.unresolved) return;
    if (!selection.crossBlock) {
      if (["insertParagraph", "insertLineBreak"].includes(inputType)) {
        event.preventDefault();
        if (event.defaultPrevented) insertTextLineBreak(selection);
        else structuralInputPending.current = inputType;
        return;
      }
      mergeTextBoundary(event, inputType, selection);
      return;
    }
    let inserted = null;
    let forceInline = false;
    if (["insertText", "insertReplacementText"].includes(inputType)) {
      inserted = collabDocumentSerializeInlineRuns([{
        value: String(nativeEvent.data || ""), bold: false, italic: false,
      }]);
      forceInline = true;
    } else if (["insertParagraph", "insertLineBreak"].includes(inputType)) inserted = "\n";
    else if (inputType.startsWith("delete")) {
      inserted = "";
      forceInline = true;
    }
    if (inserted == null) return;
    event.preventDefault();
    if (event.defaultPrevented) {
      insertCanonical(inserted, { allowEmpty: true, forceInline, selectionOverride: selection });
    }
  };
  LE(() => {
    const root = rootRef.current;
    if (!root || readOnly) return undefined;
    root.addEventListener("beforeinput", beforeInput);
    return () => root.removeEventListener("beforeinput", beforeInput);
  });
  const paste = event => {
    if (readOnly) return;
    event.preventDefault();
    insertTransfer(event.clipboardData);
  };
  const drop = event => {
    if (readOnly) return;
    event.preventDefault();
    if (!collabDocumentPlaceCaretFromPoint(rootRef.current, event.clientX, event.clientY)) return;
    insertTransfer(event.dataTransfer);
  };
  const copy = event => {
    if (!event.clipboardData || typeof onCopySelection !== "function") return;
    const selection = rememberSelection(true);
    if (selection.unresolved) return;
    onCopySelection(event, selection);
  };
  const cut = event => {
    if (readOnly || !event.clipboardData || typeof onCopySelection !== "function") return;
    const selection = rememberSelection(true);
    if (
      selection.unresolved
      || number(selection.sourceStart) === number(selection.sourceEnd)
    ) return;
    if (!onCopySelection(event, selection)) return;
    insertCanonical("", { allowEmpty: true, forceInline: true, selectionOverride: selection });
  };
  const navigateTextBlocks = event => {
    if (
      readOnly || !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)
      || event.altKey || event.ctrlKey || event.metaKey
      || (event.nativeEvent && event.nativeEvent.isComposing)
    ) return false;
    const domSelection = window.getSelection && window.getSelection();
    if (!domSelection || !domSelection.rangeCount) return false;
    const range = domSelection.getRangeAt(0);
    const visual = rootRef.current && rootRef.current.closest(".task-collab-document-visual");
    if (!visual) return false;
    const blocks = collabDocumentParseBlocks(documentContent).blocks;
    const blockByLine = new Map(
      blocks.filter(item => item.type === "text").map(item => [number(item.lineIndex), item])
    );
    const pointFromDom = (node, offsetValue) => {
      const root = collabDocumentClosestTextRoot(visual, node);
      const pointBlock = root && blockByLine.get(number(root.dataset.collabLineIndex));
      if (!root || !pointBlock) return null;
      const visibleLength = collabDocumentInlineRuns(pointBlock.value)
        .reduce((total, run) => total + run.value.length, 0);
      const visible = clamp(collabDocumentDomOffset(root, node, offsetValue), 0, visibleLength);
      const affinity = collabDocumentDomAffinity(node, offsetValue, visible ? "backward" : "forward");
      return {
        root, block: pointBlock, visible, visibleLength, affinity,
        source: pointBlock.sourceStart + collabDocumentInlineSourceOffset(
          pointBlock.value, visible, affinity
        ),
      };
    };
    const pointAt = (pointBlock, visibleValue, affinityValue) => {
      const root = visual.querySelector(`[data-collab-line-index="${pointBlock.lineIndex}"]`);
      if (!root) return null;
      const visibleLength = collabDocumentInlineRuns(pointBlock.value)
        .reduce((total, run) => total + run.value.length, 0);
      const visible = clamp(number(visibleValue), 0, visibleLength);
      const affinity = affinityValue === "forward" ? "forward" : "backward";
      return {
        root, block: pointBlock, visible, visibleLength, affinity,
        source: pointBlock.sourceStart + collabDocumentInlineSourceOffset(
          pointBlock.value, visible, affinity
        ),
      };
    };
    const anchor = pointFromDom(domSelection.anchorNode, domSelection.anchorOffset);
    const focus = pointFromDom(domSelection.focusNode, domSelection.focusOffset);
    if (!anchor || !focus) return false;
    const backward = event.key === "ArrowLeft" || event.key === "ArrowUp";
    const horizontal = event.key === "ArrowLeft" || event.key === "ArrowRight";
    const crossBlock = anchor.block.lineIndex !== focus.block.lineIndex;
    let target = null;
    if (!event.shiftKey && !range.collapsed) {
      if (!crossBlock) return false;
      target = backward
        ? (anchor.source <= focus.source ? anchor : focus)
        : (anchor.source >= focus.source ? anchor : focus);
    } else if (event.shiftKey && crossBlock && horizontal) {
      if (backward && focus.visible > 0) {
        target = pointAt(focus.block, focus.visible - 1, "backward");
      } else if (!backward && focus.visible < focus.visibleLength) {
        target = pointAt(focus.block, focus.visible + 1, "forward");
      }
    }
    if (!target) {
      const atBoundary = backward ? focus.visible === 0 : focus.visible === focus.visibleLength;
      if (!atBoundary) return false;
      const blockIndex = blocks.findIndex(item => (
        item.type === "text" && item.lineIndex === focus.block.lineIndex
      ));
      const neighbor = blockIndex < 0 ? null : blocks[blockIndex + (backward ? -1 : 1)];
      if (!neighbor || neighbor.type !== "text") return false;
      const neighborLength = collabDocumentInlineRuns(neighbor.value)
        .reduce((total, run) => total + run.value.length, 0);
      target = pointAt(neighbor, backward ? neighborLength : 0, backward ? "backward" : "forward");
    }
    if (!target) return false;
    const keepAnchor = event.shiftKey ? anchor : target;
    const startPoint = keepAnchor.source <= target.source ? keepAnchor : target;
    const endPoint = keepAnchor.source <= target.source ? target : keepAnchor;
    const direction = keepAnchor.source === target.source ? "none"
      : keepAnchor.source < target.source ? "forward" : "backward";
    const nextSelection = {
      type: "text", lineIndex: startPoint.block.lineIndex, endLineIndex: endPoint.block.lineIndex,
      startVisible: startPoint.visible, endVisible: endPoint.visible,
      crossBlock: startPoint.block.lineIndex !== endPoint.block.lineIndex,
      start: startPoint.source, end: endPoint.source,
      startAffinity: startPoint.affinity, endAffinity: endPoint.affinity,
      direction, active: true, restoring: true, pending: true,
    };
    selectionRef.current = nextSelection;
    event.preventDefault();
    const focusRoot = direction === "forward" ? endPoint.root : startPoint.root;
    const focusSurface = focusRoot.closest("[data-collab-text-surface]") || rootRef.current;
    try { focusSurface.focus({ preventScroll: true }); } catch (error) { focusSurface.focus(); }
    const restored = collabDocumentRestoreDomRange(
      startPoint.root, startPoint.visible, endPoint.root, endPoint.visible,
      startPoint.affinity, endPoint.affinity, direction
    );
    selectionRef.current = { ...nextSelection, restoring: false, pending: false };
    return restored;
  };
  const handleTextKeyDown = event => {
    const nativeEvent = event.nativeEvent || event;
    if (compositionActive.current || nativeEvent.isComposing) return;
    if (postCompositionValue.current != null && event.key === "Enter") {
      event.preventDefault();
      return;
    }
    if (number(nativeEvent.keyCode) === 229) return;
    if (navigateTextBlocks(event)) return;
    if (!readOnly && event.key === "Backspace") {
      if (mergeTextBoundary(event, "deleteContentBackward")) return;
    } else if (!readOnly && event.key === "Delete") {
      if (mergeTextBoundary(event, "deleteContentForward")) return;
    }
    if (readOnly || event.key !== "Enter" || (event.nativeEvent && event.nativeEvent.isComposing)) return;
    event.preventDefault();
    if (event.defaultPrevented) insertTextLineBreak();
  };
  E(() => () => {
    if (postCompositionFrame.current != null) window.cancelAnimationFrame(postCompositionFrame.current);
    postCompositionFrame.current = null;
    postCompositionValue.current = null;
    structuralInputPending.current = false;
    compositionSelection.current = null;
    crossComposition.current = null;
    if (!compositionActive.current) return;
    compositionActive.current = false;
    onComposeEnd();
  }, []);
  return <div
    ref={rootRef}
    className="task-collab-document-text-surface"
    contentEditable={!readOnly}
    suppressContentEditableWarning={true}
    role="textbox"
    aria-multiline="true"
    aria-readonly={readOnly}
    aria-placeholder={showPlaceholder && !readOnly ? t("開始整理共同目標、決定與下一步。") : undefined}
    data-collab-text-surface="true"
    spellCheck="true"
    onFocus={() => rememberSelection(true)}
    onSelect={() => rememberSelection(true)}
    onKeyUp={() => rememberSelection(true)}
    onMouseUp={() => rememberSelection(true)}
    onKeyDown={handleTextKeyDown}
    onInput={event => {
      const nativeEvent = event.nativeEvent || event;
      if (compositionActive.current || nativeEvent.isComposing) return;
      if (structuralInputPending.current) {
        structuralInputPending.current = false;
        clearPostCompositionGuard();
        commitSurfaceStructure();
        return;
      }
      if (postCompositionValue.current != null) {
        clearPostCompositionGuard();
        window.requestAnimationFrame(() => {
          const root = rootRef.current;
          const currentBlocks = surfaceBlocksRef.current;
          if (
            !root || compositionActive.current
            || collabDocumentTextSurfaceMatches(root, currentBlocks, showPlaceholderRef.current)
          ) return;
          collabDocumentRenderTextSurface(root, currentBlocks, showPlaceholderRef.current);
          const selected = selectionRef.current;
          const startBlock = selected && currentBlocks.find(block => (
            selected.start >= block.sourceStart && selected.start <= block.sourceEnd
          ));
          const endBlock = selected && [...currentBlocks].reverse().find(block => (
            selected.end >= block.sourceStart && selected.end <= block.sourceEnd
          ));
          const startRoot = startBlock && paragraphForBlock(startBlock);
          const endRoot = endBlock && paragraphForBlock(endBlock);
          if (selected && selected.active === true && startRoot && endRoot) {
            collabDocumentRestoreDomRange(
              startRoot,
              collabDocumentInlineVisibleOffset(startBlock.value, selected.start - startBlock.sourceStart),
              endRoot,
              collabDocumentInlineVisibleOffset(endBlock.value, selected.end - endBlock.sourceStart),
              selected.startAffinity, selected.endAffinity, selected.direction
            );
          }
        });
        return;
      }
      commitRoot();
    }}
    onPaste={paste}
    onCopy={copy}
    onCut={cut}
    onDragOver={event => { if (!readOnly) event.preventDefault(); }}
    onDrop={drop}
    onCompositionStart={() => {
      const alreadyComposing = compositionActive.current;
      compositionActive.current = true;
      clearPostCompositionGuard();
      structuralInputPending.current = false;
      const selection = rememberSelection(true);
      compositionSelection.current = selection && !selection.unresolved ? selection : null;
      crossComposition.current = selection && selection.crossBlock ? selection : null;
      if (!alreadyComposing) onComposeStart();
    }}
    onCompositionEnd={event => {
      const wasComposing = compositionActive.current;
      compositionActive.current = false;
      if (!wasComposing) {
        clearPostCompositionGuard();
        compositionSelection.current = null;
        crossComposition.current = null;
        return;
      }
      armPostCompositionGuard(collabDocumentTextSurfaceSnapshot(rootRef.current));
      const selected = crossComposition.current;
      const fallbackSelection = compositionSelection.current;
      crossComposition.current = null;
      compositionSelection.current = null;
      if (selected) {
        const data = String((event.nativeEvent && event.nativeEvent.data) || event.data || "");
        onComposeEnd(() => {
          if (!data) return false;
          const inserted = collabDocumentSerializeInlineRuns([{ value: data, bold: false, italic: false }]);
          return insertCanonical(inserted, {
            allowEmpty: true, forceInline: true, selectionOverride: selected,
          });
        });
      } else onComposeEnd(() => commitRoot(fallbackSelection));
    }}
    onBlur={() => {
      const unfinishedComposition = compositionActive.current;
      compositionActive.current = false;
      if (unfinishedComposition) {
        clearPostCompositionGuard();
        const fallbackSelection = compositionSelection.current;
        compositionSelection.current = null;
        onComposeEnd(() => commitRoot(fallbackSelection));
      } else commitRoot();
      const selection = rememberSelection(false);
      const current = selectionRef.current;
      if (
        selection.unresolved && current
        && current.pending !== true && current.restoring !== true
      ) selectionRef.current = { ...current, active: false };
      clearPostCompositionGuard();
      structuralInputPending.current = false;
      onBlur();
    }}
  />;
};

const CollaborativeDocumentTableEditor = ({ block, readOnly, selectionRef, onReplace, onSplices, onRemove, onComposeStart, onComposeEnd, onBlur }) => {
  const ignorePostCompositionChange = R(null);
  const updateCell = (cell, value) => onReplace(
    cell.sourceStart, cell.sourceEnd, collabDocumentEscapeTableCell(value), cell.raw
  );
  const rememberCell = (cell, rowIndex, column, event, active) => {
    if (selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true)) return;
    const input = event.currentTarget;
    const visibleStart = clamp(number(input.selectionStart), 0, cell.value.length);
    const visibleEnd = clamp(number(input.selectionEnd), visibleStart, cell.value.length);
    const currentValue = String(input.value || "");
    const raw = currentValue === cell.value ? cell.raw : collabDocumentEscapeTableCell(currentValue);
    const sourceStart = cell.sourceStart + collabDocumentTableRawOffset(raw, visibleStart);
    const sourceEnd = cell.sourceStart + collabDocumentTableRawOffset(raw, visibleEnd);
    const current = selectionRef.current;
    const preserveAnchors = current && current.start === sourceStart && current.end === sourceEnd;
    selectionRef.current = {
      type: "table", lineIndex: block.lineIndex, rowIndex, column,
      start: sourceStart, end: sourceEnd,
      startAffinity: sourceStart === sourceEnd ? "backward" : "forward",
      endAffinity: "backward",
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
      controlStart: visibleStart, controlEnd: visibleEnd, active, pending: false,
    };
  };
  const cellInput = (cell, label, header, rowIndex, column) => <input
    className="task-collab-document-cell"
    data-collab-table-row={rowIndex}
    data-collab-table-column={column}
    value={cell.value}
    readOnly={readOnly}
    aria-label={label}
    maxLength="1000"
    spellCheck={header ? "false" : "true"}
    onChange={event => {
      if (ignorePostCompositionChange.current === cell.sourceStart) {
        ignorePostCompositionChange.current = null;
        return;
      }
      if (!(event.nativeEvent && event.nativeEvent.isComposing)) updateCell(cell, event.currentTarget.value);
    }}
    onCompositionStart={() => { ignorePostCompositionChange.current = null; onComposeStart(); }}
    onCompositionEnd={event => {
      const value = event.currentTarget.value;
      ignorePostCompositionChange.current = cell.sourceStart;
      window.setTimeout(() => { if (ignorePostCompositionChange.current === cell.sourceStart) ignorePostCompositionChange.current = null; }, 0);
      onComposeEnd(() => updateCell(cell, value));
    }}
    onFocus={event => rememberCell(cell, rowIndex, column, event, true)}
    onSelect={event => rememberCell(cell, rowIndex, column, event, true)}
    onBlur={event => { rememberCell(cell, rowIndex, column, event, false); onBlur(); }}
  />;
  const addRow = () => {
    if (readOnly || block.rows.length >= COLLAB_DOCUMENT_MAX_TABLE_ROWS) return;
    onReplace(block.end, block.end, `\n| ${block.header.cells.map(() => t("內容")).join(" | ")} |`, "");
  };
  const removeRow = () => {
    if (readOnly || !block.rows.length) return;
    const row = block.rows[block.rows.length - 1];
    const start = Math.max(block.divider.end, row.start - 1);
    onReplace(start, row.end, "", `\n${row.source}`);
  };
  const addColumn = () => {
    if (readOnly || block.columnCount >= 12) return;
    const splices = block.lines.map((line, index) => {
      const value = index === 1 ? "---" : index === 0 ? `${t("欄位")} ${block.columnCount + 1}` : t("內容");
      const position = line.trailingPipe ? line.trailingPipeOffset : line.contentEnd;
      return { start: position, end: position, replacement: line.trailingPipe ? `| ${collabDocumentEscapeTableCell(value)} ` : ` | ${collabDocumentEscapeTableCell(value)}`, expected: "" };
    });
    onSplices(splices);
  };
  const removeColumn = () => {
    if (readOnly || block.columnCount <= 2) return;
    const splices = block.lines.map(line => {
      const cell = line.cells[line.cells.length - 1];
      const previous = line.cells[line.cells.length - 2];
      const start = previous.segmentEnd;
      const end = cell.segmentEnd;
      return { start, end, replacement: "" };
    });
    onSplices(splices);
  };
  return <div className="task-collab-document-table-editor" data-collab-block-line-index={block.lineIndex}>
    <div className="task-collab-document-table-toolbar"><span>{t("可編輯表格")} · {block.columnCount}×{block.rows.length}</span>{!readOnly && <div className="task-collab-document-table-actions">
      <button type="button" onClick={addRow} disabled={block.rows.length >= COLLAB_DOCUMENT_MAX_TABLE_ROWS}>{t("新增一列")}</button>
      <button type="button" onClick={removeRow} disabled={!block.rows.length}>{t("刪除末列")}</button>
      <button type="button" onClick={addColumn} disabled={block.columnCount >= 12}>{t("新增一欄")}</button>
      <button type="button" onClick={removeColumn} disabled={block.columnCount <= 2}>{t("刪除末欄")}</button>
      <button type="button" className="is-danger" onClick={() => onRemove(block)}>{t("刪除表格")}</button>
    </div>}</div>
    <table><thead><tr>{block.header.cells.map((cell, column) => <th key={column}>{cellInput(cell, `${t("欄位")} ${column + 1}`, true, -1, column)}</th>)}</tr></thead>
      <tbody>{block.rows.map((row, rowIndex) => <tr key={rowIndex}>{row.cells.map((cell, column) => <td key={column}>{cellInput(cell, `${rowIndex + 1} / ${column + 1}`, false, rowIndex, column)}</td>)}</tr>)}</tbody>
    </table>
  </div>;
};

const CollaborativeDocumentFormulaEditor = ({ block, readOnly, selectionRef, onReplace, onRemove, onComposeStart, onComposeEnd, onBlur }) => {
  const ignorePostCompositionChange = R(false);
  const update = (value, expectedValue = block.value) => onReplace(block.sourceStart, block.sourceStart + String(expectedValue).length, String(value || "").slice(0, COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS), expectedValue);
  const remember = (event, active) => {
    if (selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true)) return;
    const input = event.currentTarget;
    const controlStart = clamp(number(input.selectionStart), 0, block.value.length);
    const controlEnd = clamp(number(input.selectionEnd), controlStart, block.value.length);
    const sourceStart = block.sourceStart + controlStart;
    const sourceEnd = block.sourceStart + controlEnd;
    const current = selectionRef.current;
    const preserveAnchors = current && current.start === sourceStart && current.end === sourceEnd;
    selectionRef.current = {
      type: "formula", lineIndex: block.lineIndex, start: sourceStart, end: sourceEnd,
      startAffinity: sourceStart === sourceEnd ? "backward" : "forward",
      endAffinity: "backward",
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
      controlStart, controlEnd, active, pending: false,
    };
  };
  const normalize = event => {
    if (selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true)) return;
    const currentValue = String(event.currentTarget.value || "").slice(0, COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS);
    const normalized = collabFormulaNormalize(currentValue);
    const currentStart = clamp(number(event.currentTarget.selectionStart), 0, currentValue.length);
    const currentEnd = clamp(number(event.currentTarget.selectionEnd), currentStart, currentValue.length);
    const controlStart = collabDocumentMapSelection(currentValue, normalized, currentStart);
    const controlEnd = collabDocumentMapSelection(currentValue, normalized, currentEnd);
    if (normalized !== currentValue) update(normalized, currentValue);
    selectionRef.current = {
      type: "formula", lineIndex: block.lineIndex, start: block.sourceStart + controlStart,
      end: block.sourceStart + controlEnd,
      startAffinity: controlStart === controlEnd ? "backward" : "forward",
      endAffinity: "backward", controlStart, controlEnd, active: false, pending: false,
    };
    onBlur();
  };
  return <div className="task-collab-document-formula" data-collab-block-line-index={block.lineIndex}>
    {!readOnly && <button type="button" className="task-collab-document-block-remove" onClick={() => onRemove(block)}>{t("刪除公式")}</button>}
    <div className="task-collab-document-formula-preview"><CollaborativeDocumentFormulaMath value={block.value}/></div>
    <label><span className="sr-only">{t("公式內容")}</span><textarea className="task-collab-document-formula-source" rows="2" value={block.value} readOnly={readOnly} maxLength={COLLAB_DOCUMENT_MAX_FORMULA_CHARACTERS} spellCheck="false" onChange={event => { if (ignorePostCompositionChange.current) { ignorePostCompositionChange.current = false; return; } if (!(event.nativeEvent && event.nativeEvent.isComposing)) update(event.currentTarget.value); }} onCompositionStart={() => { ignorePostCompositionChange.current = false; onComposeStart(); }} onCompositionEnd={event => { const value = event.currentTarget.value; ignorePostCompositionChange.current = true; window.setTimeout(() => { ignorePostCompositionChange.current = false; }, 0); onComposeEnd(() => update(value)); }} onFocus={event => remember(event, true)} onSelect={event => remember(event, true)} onBlur={normalize}/></label>
  </div>;
};

const CollaborativeDocumentImageEditor = ({ taskId, block, asset, withinBudget, readOnly, selectionRef, onReplace, onRemove, onComposeStart, onComposeEnd, onBlur }) => {
  const ignorePostCompositionChange = R(false);
  const safeAlt = value => String(value || "").replace(/[\]\\\r\n]/g, " ").slice(0, 160);
  const update = (value, expectedValue = block.alt) => onReplace(block.altStart, block.altStart + String(expectedValue).length, safeAlt(value), expectedValue);
  const remember = (event, active) => {
    if (selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true)) return;
    const input = event.currentTarget;
    const controlStart = clamp(number(input.selectionStart), 0, block.alt.length);
    const controlEnd = clamp(number(input.selectionEnd), controlStart, block.alt.length);
    const sourceStart = block.altStart + controlStart;
    const sourceEnd = block.altStart + controlEnd;
    const current = selectionRef.current;
    const preserveAnchors = current && current.start === sourceStart && current.end === sourceEnd;
    selectionRef.current = {
      type: "image", lineIndex: block.lineIndex, start: sourceStart, end: sourceEnd,
      startAffinity: sourceStart === sourceEnd ? "backward" : "forward",
      endAffinity: "backward",
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
      controlStart, controlEnd, active, pending: false,
    };
  };
  return <figure className="task-collab-document-visual-image" data-collab-block-line-index={block.lineIndex}>
    {!readOnly && <button type="button" className="task-collab-document-block-remove" onClick={() => onRemove(block)}>{t("刪除圖片")}</button>}
    {asset && withinBudget ? <CollaborativeDocumentImage taskId={taskId} asset={asset} alt={block.alt}/> : <span className="task-collab-document-image-error">{t(asset ? "圖片預覽已達上限" : "圖片無法載入")}</span>}
    <input value={block.alt} readOnly={readOnly} maxLength="160" aria-label={t("圖片")}
      onChange={event => { if (ignorePostCompositionChange.current) { ignorePostCompositionChange.current = false; return; } if (!(event.nativeEvent && event.nativeEvent.isComposing)) update(event.currentTarget.value); }}
      onCompositionStart={() => { ignorePostCompositionChange.current = false; onComposeStart(); }}
      onCompositionEnd={event => { const value = event.currentTarget.value; ignorePostCompositionChange.current = true; window.setTimeout(() => { ignorePostCompositionChange.current = false; }, 0); onComposeEnd(() => update(value)); }}
      onFocus={event => remember(event, true)} onSelect={event => remember(event, true)}
      onBlur={event => { remember(event, false); onBlur(); }}/>
  </figure>;
};

const CollaborativeDocumentSourceEditor = ({ block, readOnly, selectionRef, onReplace, onComposeStart, onComposeEnd, onBlur }) => {
  const ignorePostCompositionChange = R(false);
  const update = (value, expectedValue = block.value) => onReplace(block.start, block.start + String(expectedValue).length, String(value || ""), expectedValue);
  const remember = (event, active) => {
    if (selectionRef.current && (selectionRef.current.pending === true || selectionRef.current.restoring === true)) return;
    const input = event.currentTarget;
    const controlStart = clamp(number(input.selectionStart), 0, block.value.length);
    const controlEnd = clamp(number(input.selectionEnd), controlStart, block.value.length);
    const sourceStart = block.start + controlStart;
    const sourceEnd = block.start + controlEnd;
    const current = selectionRef.current;
    const preserveAnchors = current && current.start === sourceStart && current.end === sourceEnd;
    selectionRef.current = {
      type: "source", lineIndex: block.lineIndex, start: sourceStart, end: sourceEnd,
      startAffinity: sourceStart === sourceEnd ? "backward" : "forward",
      endAffinity: "backward",
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
      controlStart, controlEnd, active, pending: false,
    };
  };
  return <textarea className="task-collab-document-source-block" data-collab-block-line-index={block.lineIndex}
    value={block.value} readOnly={readOnly} rows="6"
    onChange={event => { if (ignorePostCompositionChange.current) { ignorePostCompositionChange.current = false; return; } if (!(event.nativeEvent && event.nativeEvent.isComposing)) update(event.currentTarget.value); }}
    onCompositionStart={() => { ignorePostCompositionChange.current = false; onComposeStart(); }}
    onCompositionEnd={event => { const value = event.currentTarget.value; ignorePostCompositionChange.current = true; window.setTimeout(() => { ignorePostCompositionChange.current = false; }, 0); onComposeEnd(() => update(value)); }}
    onFocus={event => remember(event, true)} onSelect={event => remember(event, true)}
    onBlur={event => { remember(event, false); onBlur(); }}/>
};

const CollaborativeDocumentVisualEditor = ({ taskId, content, assets, readOnly, selectionRef, onReplace, onSplices, onComposeStart, onComposeEnd, onBlur }) => {
  const projection = M(() => collabDocumentParseBlocks(content), [content]);
  const visualGroups = M(() => collabDocumentVisualGroups(projection.blocks), [projection]);
  const assetMap = M(() => new Map(arr(assets).map(asset => [asset.asset_key, asset])), [assets]);
  const textBlocksByLine = M(() => new Map(
    projection.blocks.filter(block => block.type === "text").map(block => [number(block.lineIndex), block])
  ), [projection]);
  const visualRef = R(null);
  const documentIsEmpty = projection.blocks.length === 1
    && projection.blocks[0].type === "text"
    && !projection.blocks[0].value
    && !projection.blocks[0].level
    && !projection.blocks[0].listMarker;
  const resolveTextSelection = () => collabDocumentVisualTextSelection(visualRef.current, textBlocksByLine);
  const copyTextSelection = (event, selectedValue) => {
    if (!event || !event.clipboardData) return false;
    const selected = obj(selectedValue);
    const payload = collabDocumentSelectionClipboard(content, projection.blocks, {
      ...selected,
      start: selected.sourceStart,
      end: selected.sourceEnd,
    });
    if (!payload) return false;
    try {
      event.clipboardData.setData("text/plain", payload.plain);
    } catch (error) {
      return false;
    }
    try { event.clipboardData.setData("text/html", payload.html); } catch (error) {}
    try { event.clipboardData.setData(COLLAB_DOCUMENT_INTERNAL_CLIPBOARD_MIME, payload.canonical); } catch (error) {}
    event.preventDefault();
    return true;
  };
  E(() => {
    const selectionChanged = () => {
      const current = selectionRef.current;
      if (current && (current.pending === true || current.restoring === true)) return;
      const visual = visualRef.current;
      if (!visual || !visual.contains(document.activeElement)) return;
      const selected = resolveTextSelection();
      if (!selected) return;
      const preserveAnchors = current && current.start === selected.start && current.end === selected.end;
      const startBlock = projection.blocks.find(block => block.type === "text" && block.lineIndex === selected.startLineIndex);
      selectionRef.current = {
        type: "text", lineIndex: selected.startLineIndex, endLineIndex: selected.endLineIndex,
        startVisible: selected.startVisible, endVisible: selected.endVisible,
        crossBlock: selected.crossBlock, start: selected.start, end: selected.end,
        startAffinity: selected.startAffinity, endAffinity: selected.endAffinity,
        direction: selected.direction || "none",
        startAnchor: preserveAnchors ? current.startAnchor : null,
        endAnchor: preserveAnchors ? current.endAnchor : null,
        level: startBlock ? startBlock.level : 0,
        active: true, restoring: false, pending: false,
      };
    };
    document.addEventListener("selectionchange", selectionChanged);
    return () => document.removeEventListener("selectionchange", selectionChanged);
  }, [projection, selectionRef]);
  E(() => {
    const selected = selectionRef.current ? { ...selectionRef.current } : null;
    if (!selected || selected.active !== true || selected.pending !== true) return;
    const rememberedTextBlock = selected.type === "text" ? projection.blocks.find(item => (
      item.type === "text" && item.lineIndex === selected.lineIndex
      && selected.start >= item.start && selected.start <= item.end
    )) : null;
    const block = rememberedTextBlock
      || projection.blocks.find(item => selected.start >= item.start && selected.start <= item.end);
    if (!block) {
      selectionRef.current = { ...selected, restoring: false, pending: false };
      return;
    }
    selected.lineIndex = block.lineIndex;
    selected.restoring = true;
    selectionRef.current = selected;
    const frame = window.requestAnimationFrame(() => {
      if (selectionRef.current !== selected) return;
      const abandonRestore = () => {
        if (selectionRef.current === selected) {
          selectionRef.current = { ...selected, restoring: false, pending: false };
        }
      };
      const visual = visualRef.current;
      if (!visual) { abandonRestore(); return; }
      if (block.type !== "text") {
        const container = visual.querySelector(`[data-collab-block-line-index="${block.lineIndex}"]`);
        let mappedTableEntry = null;
        if (block.type === "table" && selected.type === "table") {
          const entries = [
            ...block.header.cells.map((cell, column) => ({ cell, rowIndex: -1, column })),
            ...block.rows.flatMap((row, rowIndex) => (
              row.cells.map((cell, column) => ({ cell, rowIndex, column }))
            )),
          ];
          mappedTableEntry = entries.find(entry => (
            selected.start >= entry.cell.sourceStart && selected.start <= entry.cell.sourceEnd
          ));
          if (!mappedTableEntry && selected.startAffinity === "forward") {
            mappedTableEntry = entries.find(entry => entry.cell.sourceStart >= selected.start) || null;
          }
          if (!mappedTableEntry) {
            mappedTableEntry = [...entries].reverse().find(entry => entry.cell.sourceEnd <= selected.start) || null;
          }
        }
        const tableRow = mappedTableEntry ? mappedTableEntry.rowIndex : selected.rowIndex;
        const tableColumn = mappedTableEntry ? mappedTableEntry.column : selected.column;
        const tableTarget = block.type === "table" && selected.type === "table"
          ? `[data-collab-table-row="${tableRow}"][data-collab-table-column="${tableColumn}"]` : "";
        const target = container && (block.type === "source" ? container : block.type === "table"
          ? (tableTarget && container.querySelector(tableTarget)) || container.querySelector("tbody tr:last-child td:last-child input") || container.querySelector("input")
          : container.querySelector("textarea, input"));
        if (!target) { abandonRestore(); return; }
        target.focus({ preventScroll: true });
        if (typeof target.setSelectionRange === "function") {
          const length = String(target.value || "").length;
          let start = length;
          let end = length;
          let rowIndex = selected.rowIndex;
          let column = selected.column;
          let tableCell = null;
          if (block.type === "table") {
            rowIndex = number(target.dataset.collabTableRow);
            column = number(target.dataset.collabTableColumn);
            tableCell = rowIndex < 0 ? block.header.cells[column] : block.rows[rowIndex] && block.rows[rowIndex].cells[column];
            if (tableCell && selected.type === "table") {
              start = collabDocumentTableVisibleOffset(
                tableCell.raw, clamp(number(selected.start) - tableCell.sourceStart, 0, tableCell.raw.length), selected.startAffinity
              );
              end = collabDocumentTableVisibleOffset(
                tableCell.raw, clamp(number(selected.end) - tableCell.sourceStart, 0, tableCell.raw.length), selected.endAffinity
              );
            }
          } else if (block.type === "formula" && selected.type === "formula") {
            start = clamp(number(selected.start) - block.sourceStart, 0, length);
            end = clamp(number(selected.end) - block.sourceStart, start, length);
          } else if (block.type === "image" && selected.type === "image") {
            start = clamp(number(selected.start) - block.altStart, 0, length);
            end = clamp(number(selected.end) - block.altStart, start, length);
          } else if (block.type === "source" && selected.type === "source") {
            start = clamp(number(selected.start) - block.start, 0, length);
            end = clamp(number(selected.end) - block.start, start, length);
          }
          try { target.setSelectionRange(start, end); } catch (ignored) {}
          const sourceStart = block.type === "table" && tableCell ? tableCell.sourceStart + collabDocumentTableRawOffset(tableCell.raw, start)
            : block.type === "formula" ? block.sourceStart + start
            : block.type === "image" ? block.altStart + start
            : block.type === "source" ? block.start + start
            : selected.start;
          const sourceEnd = block.type === "table" && tableCell ? tableCell.sourceStart + collabDocumentTableRawOffset(tableCell.raw, end)
            : block.type === "formula" ? block.sourceStart + end
            : block.type === "image" ? block.altStart + end
            : block.type === "source" ? block.start + end
            : selected.end;
          selectionRef.current = {
            ...selected, type: block.type, lineIndex: block.lineIndex, rowIndex, column,
            start: sourceStart, end: sourceEnd, controlStart: start, controlEnd: end,
            startAffinity: sourceStart === sourceEnd ? "backward" : "forward",
            endAffinity: "backward",
            active: true, restoring: false, pending: false,
          };
        }
        return;
      }
      const root = visual.querySelector(`[data-collab-line-index="${block.lineIndex}"]`);
      if (!root) { abandonRestore(); return; }
      const rememberedEndBlock = selected.crossBlock === true ? projection.blocks.find(item => (
        item.type === "text" && item.lineIndex === selected.endLineIndex
        && selected.end >= item.start && selected.end <= item.end
      )) : null;
      const endBlock = rememberedEndBlock || (selected.crossBlock === true
        ? [...projection.blocks].reverse().find(item => (
          item.type === "text" && selected.end >= item.sourceStart && selected.end <= item.sourceEnd
        )) : block) || block;
      const endRoot = visual.querySelector(`[data-collab-line-index="${endBlock.lineIndex}"]`);
      if (!endRoot) { abandonRestore(); return; }
      const start = collabDocumentInlineVisibleOffset(block.value, clamp(selected.start, block.sourceStart, block.sourceEnd) - block.sourceStart);
      const end = collabDocumentInlineVisibleOffset(endBlock.value, clamp(selected.end, endBlock.sourceStart, endBlock.sourceEnd) - endBlock.sourceStart);
      const focusRoot = selected.direction === "forward" ? endRoot : root;
      const focusSurface = focusRoot.closest("[data-collab-text-surface]") || focusRoot;
      focusSurface.focus({ preventScroll: true });
      if (!collabDocumentRestoreDomRange(
        root, start, endRoot, end, selected.startAffinity, selected.endAffinity, selected.direction
      )) { abandonRestore(); return; }
      selectionRef.current = {
        ...selected, type: "text", lineIndex: block.lineIndex, endLineIndex: endBlock.lineIndex,
        startVisible: start, endVisible: end, crossBlock: block.lineIndex !== endBlock.lineIndex,
        start: selected.start, end: selected.end, active: true, restoring: false, pending: false,
      };
    });
    return () => window.cancelAnimationFrame(frame);
  }, [content, projection, selectionRef]);
  const focusDocumentEnd = event => {
    if (readOnly || event.target !== event.currentTarget) return;
    const canvas = event.currentTarget;
    const lastElement = canvas.lastElementChild;
    if (lastElement && number(event.clientY) < lastElement.getBoundingClientRect().bottom) return;
    const lastBlock = projection.blocks[projection.blocks.length - 1];
    if (!lastBlock) {
      const insertion = projection.style.lineCount && !content.endsWith("\n") ? "\n" : "";
      if (!insertion) return;
      const committed = onReplace(content.length, content.length, insertion, "");
      if (committed) {
        const caret = content.length + insertion.length;
        selectionRef.current = {
          type: "text", lineIndex: projection.style.lineCount, endLineIndex: projection.style.lineCount,
          start: caret, end: caret, startAffinity: "forward", endAffinity: "forward",
          active: true, restoring: true, pending: true,
        };
      }
      return;
    }
    if (lastBlock && lastBlock.type !== "text") {
      const committed = onReplace(content.length, content.length, "\n", "");
      if (committed) {
        const caret = content.length + 1;
        selectionRef.current = {
          type: "text", lineIndex: number(lastBlock.lineIndex) + 1,
          endLineIndex: number(lastBlock.lineIndex) + 1,
          start: caret, end: caret, startAffinity: "forward", endAffinity: "forward",
          active: true, restoring: true, pending: true,
        };
      }
      return;
    }
    const textBlock = lastBlock && lastBlock.type === "text" ? lastBlock : null;
    const visual = visualRef.current;
    const root = textBlock && visual && visual.querySelector(`[data-collab-line-index="${textBlock.lineIndex}"]`);
    if (!root) return;
    const visibleLength = collabDocumentInlineRuns(textBlock.value)
      .reduce((total, run) => total + run.value.length, 0);
    const surface = root.closest("[data-collab-text-surface]") || root;
    try { surface.focus({ preventScroll: true }); } catch (error) { surface.focus(); }
    collabDocumentRestoreDomSelection(root, visibleLength, visibleLength, "backward", "backward");
    selectionRef.current = {
      type: "text", lineIndex: textBlock.lineIndex, endLineIndex: textBlock.lineIndex,
      startVisible: visibleLength, endVisible: visibleLength, crossBlock: false,
      start: textBlock.sourceEnd, end: textBlock.sourceEnd,
      startAffinity: "backward", endAffinity: "backward", direction: "none",
      level: textBlock.level, active: true, restoring: false, pending: false,
    };
  };
  const removeStructuredBlock = blockValue => {
    if (readOnly || !["table", "formula", "image"].includes(blockValue && blockValue.type)) return false;
    const removal = collabDocumentStructuredRemoval(content, blockValue);
    if (removal.end <= removal.start) return false;
    const committed = onReplace(removal.start, removal.end, removal.replacement, removal.expected);
    if (committed) {
      const caret = removal.start + removal.replacement.length;
      selectionRef.current = {
        type: "text", lineIndex: number(blockValue.lineIndex), endLineIndex: number(blockValue.lineIndex),
        start: caret, end: caret,
        startAffinity: "forward", endAffinity: "forward",
        active: true, restoring: true, pending: true,
      };
    }
    return committed;
  };
  const imageBudget = { count: 0 };
  return <div ref={visualRef} className="task-collab-document-visual" aria-label={t("視覺共編")}>
    <div className={`task-collab-document-canvas is-font-${projection.style.font} is-size-${projection.style.size}${readOnly ? " is-readonly" : ""}`} onClick={focusDocumentEnd}>
      {visualGroups.map((block, index) => {
        if (block.type === "text-surface") return <CollaborativeDocumentTextSurface key={`text-surface-${index}`} blocks={block.blocks} documentContent={content} readOnly={readOnly} showPlaceholder={documentIsEmpty && index === 0} selectionRef={selectionRef} resolveSelection={resolveTextSelection} onCopySelection={copyTextSelection} onReplace={onReplace} onComposeStart={onComposeStart} onComposeEnd={onComposeEnd} onBlur={onBlur}/>;
        if (block.type === "table") return <CollaborativeDocumentTableEditor key={`table-${block.lineIndex}`} block={block} readOnly={readOnly} selectionRef={selectionRef} onReplace={onReplace} onSplices={onSplices} onRemove={removeStructuredBlock} onComposeStart={onComposeStart} onComposeEnd={onComposeEnd} onBlur={onBlur}/>;
        if (block.type === "formula") return <CollaborativeDocumentFormulaEditor key={`formula-${block.lineIndex}`} block={block} readOnly={readOnly} selectionRef={selectionRef} onReplace={onReplace} onRemove={removeStructuredBlock} onComposeStart={onComposeStart} onComposeEnd={onComposeEnd} onBlur={onBlur}/>;
        if (block.type === "image") {
          const asset = assetMap.get(block.assetKey);
          const withinBudget = imageBudget.count < COLLAB_DOCUMENT_MAX_PREVIEW_IMAGES;
          imageBudget.count += 1;
          return <CollaborativeDocumentImageEditor key={`image-${block.lineIndex}`} taskId={taskId} block={block} asset={asset} withinBudget={withinBudget} readOnly={readOnly} selectionRef={selectionRef} onReplace={onReplace} onRemove={removeStructuredBlock} onComposeStart={onComposeStart} onComposeEnd={onComposeEnd} onBlur={onBlur}/>;
        }
        if (block.type === "source") return <CollaborativeDocumentSourceEditor key={`source-${block.lineIndex}`} block={block} readOnly={readOnly} selectionRef={selectionRef} onReplace={onReplace} onComposeStart={onComposeStart} onComposeEnd={onComposeEnd} onBlur={onBlur}/>;
        return null;
      })}
    </div>
  </div>;
};

const CollaborativeDocument = ({ taskId, task, role, viewerUserId, clientId, realtimeState, documentSignal, documentSequence }) => {
  const tenant = W2.tenant();
  const initialQueue = R(null);
  if (!initialQueue.current) initialQueue.current = collabDocumentReadQueue(tenant, taskId, viewerUserId, clientId);
  const queueRef = R(initialQueue.current);
  const nodesRef = R({});
  const adoptedSequence = R(0);
  const contentRef = R("");
  const editorRef = R(null);
  const sourceSelectionRef = R(null);
  const restoringSourceSelection = R(false);
  const visualSelectionRef = R(null);
  const imageInputRef = R(null);
  const composing = R(false);
  const reloadAfterComposition = R(false);
  const capabilitiesRef = R({ can_read: true, can_edit: false, can_export: true, read_only: true });
  const mounted = R(true);
  const generation = R(0);
  const loadController = R(null);
  const updateController = R(null);
  const assetUploadController = R(null);
  const flushTimer = R(null);
  const retryTimer = R(null);
  const documentReloadTimer = R(null);
  const documentReloadQueuedAt = R(0);
  const automaticRetryBlocked = R(false);
  const transientRetryCount = R(0);
  const reloadAfterFlush = R(false);
  const reloadDocumentLatest = R(null);
  const flushing = R(false);
  const flushLatest = R(null);
  const lastDocumentSignal = R(documentSignal);
  const lastDocumentSequence = R(documentSequence);
  const [content, setContent] = S("");
  const [assets, setAssets] = S([]);
  const [mode, setMode] = S("edit");
  const [editorView, setEditorView] = S("visual");
  const [toolPanel, setToolPanel] = S("");
  const [loading, setLoading] = S(true);
  const [saving, setSaving] = S(false);
  const [exporting, setExporting] = S(false);
  const [uploadingImage, setUploadingImage] = S(false);
  const [pendingCount, setPendingCount] = S(queueRef.current.updates.length);
  const [capabilities, setCapabilities] = S({ can_read: true, can_edit: false, can_export: true, read_only: true });
  const [documentMeta, setDocumentMeta] = S({});
  const [error, setError] = S("");
  const [storageWarning, setStorageWarning] = S(() => (
    queueRef.current.recovery_warning
      ? t("偵測到無法讀取的本機工作稿；原始資料已保留且不會自動載入。") : ""
  ));
  const [networkOnline, setNetworkOnline] = S(() => !window.navigator || window.navigator.onLine !== false);
  const previousNetworkOnline = R(networkOnline);

  const persistQueue = C(() => {
    const saved = collabDocumentSaveQueue(tenant, taskId, viewerUserId, queueRef.current);
    setStorageWarning(saved ? "" : t("本機儲存空間不足，請先保持此頁開啟並重新連線。"));
    return saved;
  }, [tenant, taskId, viewerUserId]);
  const adopt = C((rawResponse, pendingUpdates = queueRef.current.updates) => {
    const response = collabDocumentResponse(rawResponse);
    const sequence = number(response.document.latest_sequence);
    if (sequence < adoptedSequence.current) return null;
    if (composing.current) {
      reloadAfterComposition.current = true;
      return response;
    }
    let nodes = collabDocumentNodes(response.snapshot);
    pendingUpdates.forEach(update => { nodes = collabDocumentApply(nodes, update.ops); });
    const view = collabDocumentView(nodes);
    const editor = editorRef.current;
    const rememberedSource = sourceSelectionRef.current;
    const sourceStart = rememberedSource ? rememberedSource.start : editor && editor.selectionStart;
    const sourceEnd = rememberedSource ? rememberedSource.end : editor && editor.selectionEnd;
    const selection = editor ? {
      start: sourceStart,
      end: sourceEnd,
      startAffinity: rememberedSource ? rememberedSource.startAffinity
        : sourceStart === sourceEnd ? "backward" : "forward",
      endAffinity: rememberedSource ? rememberedSource.endAffinity : "backward",
      direction: rememberedSource ? rememberedSource.direction : editor.selectionDirection || "none",
      active: document.activeElement === editor,
      startAnchor: rememberedSource ? rememberedSource.startAnchor : null,
      endAnchor: rememberedSource ? rememberedSource.endAnchor : null,
    } : null;
    const visualSelection = visualSelectionRef.current
      ? { ...visualSelectionRef.current } : null;
    const beforeSelectionIndex = collabDocumentSelectionIndex(nodesRef.current);
    const afterSelectionIndex = collabDocumentSelectionIndex(nodes);
    const mapPoint = (offsetValue, affinityValue, anchorValue) => {
      const anchor = anchorValue || collabDocumentCaptureBoundary(
        beforeSelectionIndex, offsetValue, affinityValue
      );
      return {
        offset: collabDocumentResolveBoundary(afterSelectionIndex, anchor, offsetValue),
        anchor,
      };
    };
    nodesRef.current = nodes;
    adoptedSequence.current = sequence;
    capabilitiesRef.current = response.capabilities;
    contentRef.current = view.content;
    setContent(view.content);
    setAssets(response.assets);
    setCapabilities(response.capabilities);
    setDocumentMeta(response.document);
    if (visualSelection) {
      const mappedStart = mapPoint(
        visualSelection.start, visualSelection.startAffinity, visualSelection.startAnchor
      );
      const mappedEnd = mapPoint(
        visualSelection.end, visualSelection.endAffinity, visualSelection.endAnchor
      );
      let mappedText = {};
      if (visualSelection.type === "text") {
        const textBlocks = collabDocumentParseBlocks(view.content).blocks.filter(block => block.type === "text");
        const startBlock = textBlocks.find(block => mappedStart.offset >= block.sourceStart && mappedStart.offset <= block.sourceEnd);
        const endBlock = [...textBlocks].reverse().find(block => mappedEnd.offset >= block.sourceStart && mappedEnd.offset <= block.sourceEnd);
        if (startBlock && endBlock) {
          mappedText = {
            lineIndex: startBlock.lineIndex, endLineIndex: endBlock.lineIndex,
            startVisible: collabDocumentInlineVisibleOffset(startBlock.value, mappedStart.offset - startBlock.sourceStart),
            endVisible: collabDocumentInlineVisibleOffset(endBlock.value, mappedEnd.offset - endBlock.sourceStart),
            crossBlock: startBlock.lineIndex !== endBlock.lineIndex,
          };
        }
      }
      visualSelectionRef.current = {
        ...visualSelection,
        ...mappedText,
        start: mappedStart.offset, end: mappedEnd.offset,
        startAnchor: mappedStart.anchor, endAnchor: mappedEnd.anchor,
        restoring: visualSelection.active === true,
        pending: visualSelection.active === true,
      };
    }
    if (selection) {
      const mappedStart = mapPoint(selection.start, selection.startAffinity, selection.startAnchor);
      const mappedEnd = mapPoint(selection.end, selection.endAffinity, selection.endAnchor);
      const mappedSelection = {
        ...selection, start: mappedStart.offset, end: mappedEnd.offset,
        startAnchor: mappedStart.anchor, endAnchor: mappedEnd.anchor,
        restoring: selection.active === true,
      };
      sourceSelectionRef.current = mappedSelection;
      window.requestAnimationFrame(() => {
        const currentEditor = editorRef.current;
        if (!mounted.current || !currentEditor || composing.current) {
          if (sourceSelectionRef.current === mappedSelection) {
            sourceSelectionRef.current = { ...mappedSelection, restoring: false };
          }
          return;
        }
        if (sourceSelectionRef.current !== mappedSelection) return;
        restoringSourceSelection.current = true;
        try {
          currentEditor.setSelectionRange(
            mappedSelection.start, mappedSelection.end, mappedSelection.direction
          );
        } catch (error) {}
        if (sourceSelectionRef.current === mappedSelection) {
          sourceSelectionRef.current = { ...mappedSelection, restoring: false };
        }
        window.requestAnimationFrame(() => { restoringSourceSelection.current = false; });
      });
    }
    return response;
  }, []);
  const loadDocument = C(async ({ quiet = false } = {}) => {
    if (taskId == null) return false;
    const request = ++generation.current;
    if (loadController.current) loadController.current.abort();
    const controller = new AbortController();
    loadController.current = controller;
    let timedOut = false;
    const timeout = window.setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, COLLAB_DOCUMENT_GET_TIMEOUT_MS);
    if (!quiet) setLoading(true);
    try {
      const response = await collabJson(
        `/api/tasks/${encodeURIComponent(taskId)}/collaboration/document`,
        { signal: controller.signal, cache: "no-store" }
      );
      if (!mounted.current || request !== generation.current || tenant !== W2.tenant()) return false;
      if (!adopt(response, queueRef.current.updates)) return false;
      if (!automaticRetryBlocked.current || !queueRef.current.updates.length) setError("");
      return true;
    } catch (exception) {
      if (exception && exception.name === "AbortError" && !timedOut) return false;
      if (mounted.current && request === generation.current && tenant === W2.tenant()) {
        setError(timedOut ? t("工作稿連線逾時，將稍後重試。") : (exception.message || t("工作稿載入失敗")));
      }
      return false;
    } finally {
      window.clearTimeout(timeout);
      if (loadController.current === controller) loadController.current = null;
      if (mounted.current && request === generation.current) setLoading(false);
    }
  }, [taskId, tenant, adopt]);
  const clearScheduledFlush = C(() => {
    if (flushTimer.current != null) window.clearTimeout(flushTimer.current);
    if (retryTimer.current != null) window.clearTimeout(retryTimer.current);
    if (documentReloadTimer.current != null) window.clearTimeout(documentReloadTimer.current);
    flushTimer.current = null;
    retryTimer.current = null;
    documentReloadTimer.current = null;
    documentReloadQueuedAt.current = 0;
  }, []);
  const invalidateDocumentLoads = C(() => {
    generation.current += 1;
    if (loadController.current) loadController.current.abort();
    loadController.current = null;
  }, []);
  const scheduleFlush = C((delay = 500, retry = false) => {
    const timerRef = retry ? retryTimer : flushTimer;
    if (timerRef.current != null) window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(() => {
      timerRef.current = null;
      if (flushLatest.current) flushLatest.current();
    }, delay);
  }, []);
  const flush = C(async () => {
    const head = queueRef.current.updates[0];
    const exactRetry = head && head.dispatched === true;
    if (flushing.current || automaticRetryBlocked.current || taskId == null || !networkOnline || (!exactRetry && capabilitiesRef.current.can_edit !== true) || !head) return false;
    flushing.current = true;
    setSaving(true);
    setError("");
    let success = true;
    let updateTimedOut = false;
    const batchUpdateIds = new Set(queueRef.current.updates.map(update => update.client_update_id));
    try {
      while (
        mounted.current
        && tenant === W2.tenant()
        && networkOnline
        && queueRef.current.updates.length
        && batchUpdateIds.has(queueRef.current.updates[0].client_update_id)
      ) {
        let update = queueRef.current.updates[0];
        if (update.dispatched !== true && capabilitiesRef.current.can_edit !== true) {
          success = false;
          break;
        }
        if (update.dispatched !== true) {
          const sealedQueue = {
            ...queueRef.current,
            updates: queueRef.current.updates.map((item, index) => (
              index === 0 ? { ...item, dispatched: true } : item
            )),
          };
          if (!collabDocumentSaveQueue(tenant, taskId, viewerUserId, sealedQueue)) {
            success = false;
            setStorageWarning(t("本機儲存空間不足，請先保持此頁開啟並重新連線。"));
            break;
          }
          queueRef.current = sealedQueue;
          update = sealedQueue.updates[0];
          setStorageWarning("");
        }
        invalidateDocumentLoads();
        const controller = new AbortController();
        updateController.current = controller;
        updateTimedOut = false;
        const updateTimeout = window.setTimeout(() => {
          updateTimedOut = true;
          controller.abort();
        }, COLLAB_DOCUMENT_UPDATE_TIMEOUT_MS);
        let response;
        try {
          response = await W2.post(
            `/api/tasks/${encodeURIComponent(taskId)}/collaboration/document/updates`,
            {
              client_id: queueRef.current.client_id,
              client_update_id: update.client_update_id,
              ops: update.ops,
            },
            { signal: controller.signal }
          );
        } finally {
          window.clearTimeout(updateTimeout);
          if (updateController.current === controller) updateController.current = null;
        }
        if (!mounted.current || tenant !== W2.tenant()) return false;
        invalidateDocumentLoads();
        const remaining = queueRef.current.updates.filter(item => item.client_update_id !== update.client_update_id);
        automaticRetryBlocked.current = false;
        transientRetryCount.current = 0;
        queueRef.current = { ...queueRef.current, updates: remaining };
        setPendingCount(remaining.length);
        persistQueue();
        adopt(response, remaining);
      }
    } catch (exception) {
      success = false;
      if (mounted.current && tenant === W2.tenant()) {
        setError(updateTimedOut ? t("工作稿連線逾時，將稍後重試。") : t("工作稿同步失敗，已保留在此裝置。"));
        if (exception && [403, 404, 409].includes(exception.status)) {
          automaticRetryBlocked.current = true;
          transientRetryCount.current = 0;
          loadDocument({ quiet: true }).then(loaded => {
            if (loaded && mounted.current) setError(t("工作稿同步失敗，已保留在此裝置。"));
          });
        } else if (!window.navigator || window.navigator.onLine !== false) {
          transientRetryCount.current += 1;
          if (transientRetryCount.current > COLLAB_DOCUMENT_MAX_TRANSIENT_RETRIES) {
            automaticRetryBlocked.current = true;
          } else {
            const base = Math.min(15000, 1000 * (2 ** (transientRetryCount.current - 1)));
            const jitter = Math.floor(Math.random() * Math.max(250, base * .3));
            scheduleFlush(base + jitter, true);
          }
        }
      }
    } finally {
      flushing.current = false;
      if (mounted.current) setSaving(false);
      if (success && mounted.current && queueRef.current.updates.length) scheduleFlush(500);
      if (reloadAfterFlush.current && mounted.current && reloadDocumentLatest.current) {
        reloadAfterFlush.current = false;
        reloadDocumentLatest.current(0);
      }
    }
    return success;
  }, [taskId, tenant, viewerUserId, networkOnline, persistQueue, adopt, invalidateDocumentLoads, scheduleFlush, loadDocument]);
  flushLatest.current = flush;
  const scheduleDocumentReload = C((delay = 120) => {
    const now = Date.now();
    if (!documentReloadQueuedAt.current) documentReloadQueuedAt.current = now;
    const boundedDelay = Math.max(0, Math.min(delay, 500 - (now - documentReloadQueuedAt.current)));
    if (documentReloadTimer.current != null) window.clearTimeout(documentReloadTimer.current);
    documentReloadTimer.current = window.setTimeout(() => {
      documentReloadTimer.current = null;
      documentReloadQueuedAt.current = 0;
      if (!mounted.current || tenant !== W2.tenant()) return;
      if (composing.current) {
        reloadAfterComposition.current = true;
        return;
      }
      if (flushing.current) {
        reloadAfterFlush.current = true;
        return;
      }
      loadDocument({ quiet: true }).then(loaded => {
        if (loaded && !automaticRetryBlocked.current && capabilitiesRef.current.can_edit === true && queueRef.current.updates.length) scheduleFlush(0);
      });
    }, boundedDelay);
  }, [tenant, loadDocument, scheduleFlush]);
  reloadDocumentLatest.current = scheduleDocumentReload;

  E(() => {
    mounted.current = true;
    loadDocument().then(loaded => {
      if (loaded && queueRef.current.updates.length && (!window.navigator || window.navigator.onLine !== false)) scheduleFlush(0);
    });
    return () => {
      mounted.current = false;
      generation.current += 1;
      if (loadController.current) loadController.current.abort();
      if (updateController.current) updateController.current.abort();
      if (assetUploadController.current) assetUploadController.current.abort();
      loadController.current = null;
      updateController.current = null;
      assetUploadController.current = null;
      clearScheduledFlush();
      nodesRef.current = {};
      adoptedSequence.current = 0;
      contentRef.current = "";
      editorRef.current = null;
      sourceSelectionRef.current = null;
      restoringSourceSelection.current = false;
      visualSelectionRef.current = null;
      imageInputRef.current = null;
      composing.current = false;
      reloadAfterComposition.current = false;
      transientRetryCount.current = 0;
      automaticRetryBlocked.current = true;
      capabilitiesRef.current = { can_read: false, can_edit: false, can_export: false, read_only: true };
      queueRef.current = { version: COLLAB_DOCUMENT_QUEUE_VERSION, client_id: "cleared", updates: [] };
      reloadAfterFlush.current = false;
      reloadDocumentLatest.current = null;
    };
  }, [loadDocument, scheduleFlush, clearScheduledFlush]);
  E(() => {
    const online = () => setNetworkOnline(true);
    const offline = () => setNetworkOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);
  E(() => {
    const wasOnline = previousNetworkOnline.current;
    previousNetworkOnline.current = networkOnline;
    if (!networkOnline || wasOnline) return;
    transientRetryCount.current = 0;
    automaticRetryBlocked.current = false;
    loadDocument({ quiet: true }).then(loaded => {
      if (loaded && queueRef.current.updates.length) scheduleFlush(0);
    });
  }, [networkOnline, loadDocument, scheduleFlush]);
  E(() => {
    if (documentSignal <= lastDocumentSignal.current) return;
    lastDocumentSignal.current = documentSignal;
    automaticRetryBlocked.current = false;
    transientRetryCount.current = 0;
    scheduleDocumentReload();
  }, [documentSignal, scheduleDocumentReload]);
  E(() => {
    if (documentSequence <= lastDocumentSequence.current) return;
    lastDocumentSequence.current = documentSequence;
    if (documentSequence <= adoptedSequence.current) return;
    scheduleDocumentReload();
  }, [documentSequence, scheduleDocumentReload]);
  const documentReconcileDelay = realtimeState === COLLAB_REALTIME_STATES.LIVE
    ? 30000
    : realtimeState === COLLAB_REALTIME_STATES.FALLBACK ? 4000
    : realtimeState === COLLAB_REALTIME_STATES.RETRYING ? 8000 : null;
  E(() => {
    if (documentReconcileDelay == null || !networkOnline) return undefined;
    const reconcile = () => {
      if (document.visibilityState !== "visible" || flushing.current) return;
      loadDocument({ quiet: true }).then(loaded => {
        if (loaded && !automaticRetryBlocked.current && capabilitiesRef.current.can_edit === true && queueRef.current.updates.length) scheduleFlush(0);
      });
    };
    const timer = window.setInterval(reconcile, documentReconcileDelay);
    const onVisible = () => {
      if (document.visibilityState === "visible") reconcile();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [documentReconcileDelay, networkOnline, loadDocument, scheduleFlush]);

  const validateDocumentText = nextText => {
    if (capabilities.can_edit !== true || loading) return false;
    const nextCharacters = Array.from(nextText);
    if (nextCharacters.length > COLLAB_DOCUMENT_MAX_CHARACTERS) {
      setError(t("工作稿最多 32000 個字"));
      return false;
    }
    if (nextCharacters.some(value => !collabDocumentValidCharacter(value))) {
      setError(t("工作稿包含無效字元"));
      return false;
    }
    return true;
  };
  const commitDocumentOperations = (nextText, operations, updateSeed) => {
    if (!operations.length) return true;
    const updates = collabDocumentChunkUpdates(operations, `du-${updateSeed}`);
    const nextQueue = collabDocumentMergePendingUpdates(queueRef.current, updates, flushing.current);
    if (nextQueue.updates.length > COLLAB_DOCUMENT_MAX_PENDING_UPDATES) {
      setError(t("工作稿同步失敗，已保留在此裝置。"));
      return false;
    }
    try {
      const nextNodes = collabDocumentApply(nodesRef.current, operations);
      const view = collabDocumentView(nextNodes);
      if (view.content !== String(nextText)) throw new Error("collaboration document projection mismatch");
      if (!collabDocumentSaveQueue(tenant, taskId, viewerUserId, nextQueue)) {
        setStorageWarning(t("本機儲存空間不足，請先保持此頁開啟並重新連線。"));
        return false;
      }
      nodesRef.current = nextNodes;
      queueRef.current = nextQueue;
      contentRef.current = view.content;
      setContent(view.content);
      setPendingCount(queueRef.current.updates.length);
      setError("");
      setStorageWarning("");
      scheduleFlush(500);
      return true;
    } catch (exception) {
      setError(t("工作稿同步失敗，已保留在此裝置。"));
      loadDocument({ quiet: true });
      return false;
    }
  };
  const commitDocumentText = nextText => {
    if (!validateDocumentText(nextText)) return false;
    const seed = collabDocumentUpdateSeed();
    const operations = collabDocumentOperations(nodesRef.current, nextText, seed);
    return commitDocumentOperations(nextText, operations, seed);
  };
  const replaceDocumentRange = (startValue, endValue, replacementValue, expectedValue = null) => {
    const before = contentRef.current;
    const start = clamp(number(startValue), 0, before.length);
    const end = clamp(number(endValue), start, before.length);
    if (expectedValue != null && before.slice(start, end) !== String(expectedValue)) {
      setError(t("工作稿已在另一處更新，正在合併。"));
      scheduleDocumentReload(0);
      return false;
    }
    const replacement = String(replacementValue || "");
    const next = before.slice(0, start) + replacement + before.slice(end);
    if (next === before) return true;
    if (!validateDocumentText(next)) return false;
    try {
      const seed = collabDocumentUpdateSeed();
      const operations = collabDocumentRangeOperations(nodesRef.current, start, end, replacement, seed);
      return commitDocumentOperations(next, operations, seed);
    } catch (exception) {
      setError(t("工作稿同步失敗，已保留在此裝置。"));
      loadDocument({ quiet: true });
      return false;
    }
  };
  const applyDocumentSplices = spliceValues => {
    const before = contentRef.current;
    const splices = arr(spliceValues).map(raw => ({
      start: clamp(number(obj(raw).start), 0, before.length),
      end: clamp(number(obj(raw).end), 0, before.length),
      replacement: String(obj(raw).replacement || ""),
      expected: obj(raw).expected,
    })).sort((left, right) => right.start - left.start || right.end - left.end);
    let previousStart = before.length + 1;
    for (const splice of splices) {
      if (splice.end < splice.start || splice.end > previousStart) return false;
      if (splice.expected != null && before.slice(splice.start, splice.end) !== String(splice.expected)) {
        setError(t("工作稿已在另一處更新，正在合併。"));
        scheduleDocumentReload(0);
        return false;
      }
      previousStart = splice.start;
    }
    const seed = collabDocumentUpdateSeed();
    let next = before;
    let temporaryNodes = nodesRef.current;
    const operations = [];
    try {
      splices.forEach((splice, index) => {
        const intermediate = next.slice(0, splice.start) + splice.replacement + next.slice(splice.end);
        const stepOperations = collabDocumentRangeOperations(
          temporaryNodes, splice.start, splice.end, splice.replacement, `${seed}:${index}`
        );
        temporaryNodes = collabDocumentApply(temporaryNodes, stepOperations);
        operations.push(...stepOperations);
        next = intermediate;
      });
    } catch (exception) {
      setError(t("工作稿同步失敗，已保留在此裝置。"));
      loadDocument({ quiet: true });
      return false;
    }
    if (!validateDocumentText(next)) return false;
    return commitDocumentOperations(next, operations, seed);
  };
  const onVisualCompositionStart = () => { composing.current = true; };
  const onVisualCompositionEnd = callback => {
    composing.current = false;
    if (typeof callback === "function") callback();
    if (reloadAfterComposition.current) {
      reloadAfterComposition.current = false;
      scheduleDocumentReload(0);
    }
  };
  const flushDocumentOnBlur = () => {
    if (!composing.current && queueRef.current.updates.length) scheduleFlush(0);
  };
  const updateDocumentStyle = (fontValue, sizeValue) => {
    const before = contentRef.current;
    const current = collabDocumentStyle(before);
    const lines = before.split("\n");
    const body = lines.slice(current.lineCount).join("\n");
    const token = collabDocumentStyleToken(fontValue || current.font, sizeValue || current.size, queueRef.current.client_id);
    const next = `${token}\n${body}`;
    const selected = visualSelectionRef.current ? { ...visualSelectionRef.current } : null;
    const committed = commitDocumentText(next);
    if (committed && selected) {
      const start = collabDocumentMapSelection(before, next, selected.start);
      const end = collabDocumentMapSelection(before, next, selected.end);
      const target = collabDocumentParseBlocks(next).blocks.find(block => start >= block.start && start <= block.end);
      visualSelectionRef.current = {
        ...selected, start, end, lineIndex: target ? target.lineIndex : selected.lineIndex,
        restoring: selected.active === true,
        pending: selected.active === true,
      };
    }
    return committed;
  };
  const activeTextBlock = () => {
    const selected = visualSelectionRef.current;
    if (!selected || selected.type !== "text") return null;
    const blocks = collabDocumentParseBlocks(contentRef.current).blocks.filter(block => block.type === "text");
    return blocks.find(block => selected.start >= block.start && selected.start <= block.end)
      || blocks.find(block => block.lineIndex === selected.lineIndex) || null;
  };
  const rememberFormattedSelection = (startValue, endValue, lineIndex) => {
    const current = visualSelectionRef.current || {};
    visualSelectionRef.current = {
      ...current, type: "text", lineIndex, start: Math.max(0, number(startValue)),
      end: Math.max(0, number(endValue)), startAffinity: "forward", endAffinity: "backward",
      startAnchor: null, endAnchor: null,
      restoring: current.active === true, pending: current.active === true,
    };
  };
  const applyHeading = levelValue => {
    const block = activeTextBlock();
    const selected = visualSelectionRef.current;
    if (!block || !selected) return false;
    const level = clamp(number(levelValue), 0, 2);
    const selectionStart = Math.min(number(selected.start), number(selected.end));
    const selectionEnd = Math.max(number(selected.start), number(selected.end));
    const textBlocks = collabDocumentParseBlocks(contentRef.current).blocks.filter(item => item.type === "text");
    const hasRange = selectionEnd > selectionStart;
    const touched = hasRange ? textBlocks.filter(item => (
      selectionStart < item.sourceEnd && selectionEnd > item.sourceStart
    )) : [block];
    if (hasRange) {
      if (!touched.length) return false;
      const before = contentRef.current;
      const nextPrefixLength = level ? level + 1 : 0;
      const edits = touched.map(item => {
        const replacement = `${level ? `${"#".repeat(level)} ` : ""}${item.value}`;
        return {
          item,
          splice: {
            start: item.start, end: item.end, replacement,
            expected: before.slice(item.start, item.end),
          },
        };
      });
      const splices = edits.map(edit => edit.splice);
      let next = before;
      [...splices].sort((left, right) => right.start - left.start).forEach(splice => {
        next = next.slice(0, splice.start) + splice.replacement + next.slice(splice.end);
      });
      const committed = applyDocumentSplices(splices);
      if (committed) {
        const mapHeadingPoint = offsetValue => {
          const offset = clamp(number(offsetValue), 0, before.length);
          let delta = 0;
          for (const edit of edits) {
            const item = edit.item;
            if (offset < item.start) return offset + delta;
            if (offset <= item.end) {
              const relative = clamp(offset - item.sourceStart, 0, item.value.length);
              return item.start + delta + nextPrefixLength + relative;
            }
            delta += edit.splice.replacement.length - (item.end - item.start);
          }
          return offset + delta;
        };
        const mappedStart = mapHeadingPoint(selectionStart);
        const mappedEnd = mapHeadingPoint(selectionEnd);
        const target = collabDocumentParseBlocks(next).blocks.find(item => mappedStart >= item.start && mappedStart <= item.end);
        rememberFormattedSelection(mappedStart, mappedEnd, target ? target.lineIndex : touched[0].lineIndex);
      }
      return committed;
    }
    const replacement = `${level ? `${"#".repeat(level)} ` : ""}${block.value}`;
    const previousPrefixLength = block.sourceStart - block.start;
    const nextPrefixLength = level ? level + 1 : 0;
    const remembered = { ...selected };
    const committed = replaceDocumentRange(block.start, block.end, replacement, contentRef.current.slice(block.start, block.end));
    if (committed && remembered.start != null) {
      const delta = nextPrefixLength - previousPrefixLength;
      rememberFormattedSelection(number(remembered.start) + delta, number(remembered.end) + delta, block.lineIndex);
    }
    return committed;
  };
  const applyInlineFormat = format => {
    const selected = visualSelectionRef.current;
    const block = activeTextBlock();
    if (!block || !selected || !["bold", "italic"].includes(format)) return false;
    const selectionStart = Math.min(number(selected.start), number(selected.end));
    const selectionEnd = Math.max(number(selected.start), number(selected.end));
    const textBlocks = collabDocumentParseBlocks(contentRef.current).blocks.filter(item => item.type === "text");
    const hasRange = selectionEnd > selectionStart;
    const touched = hasRange ? textBlocks.filter(item => (
      selectionStart < item.sourceEnd && selectionEnd > item.sourceStart
    )) : [block];
    if (hasRange) {
      if (!touched.length) return false;
      const before = contentRef.current;
      const selectedRuns = touched.flatMap(item => {
        const relativeStart = clamp(selectionStart - item.sourceStart, 0, item.value.length);
        const relativeEnd = clamp(selectionEnd - item.sourceStart, relativeStart, item.value.length);
        const visibleStart = collabDocumentInlineVisibleOffset(item.value, relativeStart);
        const visibleEnd = collabDocumentInlineVisibleOffset(item.value, relativeEnd);
        return collabDocumentInlineRuns(item.value).filter(run => run.end > visibleStart && run.start < visibleEnd);
      });
      if (!selectedRuns.length) return false;
      const enabled = !selectedRuns.every(run => run[format] === true);
      const splices = touched.map(item => {
        const relativeStart = clamp(selectionStart - item.sourceStart, 0, item.value.length);
        const relativeEnd = clamp(selectionEnd - item.sourceStart, relativeStart, item.value.length);
        const formatted = collabDocumentFormatInline(item.value, relativeStart, relativeEnd, format, enabled);
        return formatted.changed ? {
          start: item.sourceStart, end: item.sourceEnd,
          replacement: formatted.value, expected: item.value,
        } : null;
      }).filter(Boolean);
      if (!splices.length) return false;
      let next = before;
      [...splices].sort((left, right) => right.start - left.start).forEach(splice => {
        next = next.slice(0, splice.start) + splice.replacement + next.slice(splice.end);
      });
      const committed = applyDocumentSplices(splices);
      if (committed) {
        const mappedStart = collabDocumentMapSelection(before, next, selectionStart);
        const mappedEnd = collabDocumentMapSelection(before, next, selectionEnd);
        const target = collabDocumentParseBlocks(next).blocks.find(item => mappedStart >= item.start && mappedStart <= item.end);
        rememberFormattedSelection(mappedStart, mappedEnd, target ? target.lineIndex : touched[0].lineIndex);
      }
      return committed;
    }
    const relativeStart = clamp(number(selected.start) - block.sourceStart, 0, block.value.length);
    const relativeEnd = clamp(number(selected.end) - block.sourceStart, relativeStart, block.value.length);
    const formatted = collabDocumentFormatInline(block.value, relativeStart, relativeEnd, format);
    if (!formatted.changed) return false;
    const committed = replaceDocumentRange(block.sourceStart, block.sourceEnd, formatted.value, block.value);
    if (committed) rememberFormattedSelection(
      block.sourceStart + formatted.sourceStart,
      block.sourceStart + formatted.sourceEnd,
      block.lineIndex
    );
    return committed;
  };
  const applyBold = () => applyInlineFormat("bold");
  const applyItalic = () => applyInlineFormat("italic");
  const rememberSourceSelection = (event, activeValue = true, forceClear = false) => {
    const editor = event && event.currentTarget;
    if (!editor) return;
    const current = sourceSelectionRef.current;
    if (current && (current.restoring === true || restoringSourceSelection.current)) return;
    const start = clamp(number(editor.selectionStart), 0, String(editor.value || "").length);
    const end = clamp(number(editor.selectionEnd), start, String(editor.value || "").length);
    const preserveAnchors = !forceClear && current && (
      restoringSourceSelection.current || (current.start === start && current.end === end)
    );
    sourceSelectionRef.current = {
      start, end,
      startAffinity: start === end ? "backward" : "forward",
      endAffinity: "backward", direction: editor.selectionDirection || "none",
      active: activeValue !== false, restoring: false,
      startAnchor: preserveAnchors ? current.startAnchor : null,
      endAnchor: preserveAnchors ? current.endAnchor : null,
    };
  };
  const onChange = event => {
    rememberSourceSelection(event, true, true);
    const nextText = event.target.value;
    if (composing.current || (event.nativeEvent && event.nativeEvent.isComposing)) {
      contentRef.current = nextText;
      setContent(nextText);
      return;
    }
    commitDocumentText(nextText);
  };
  const onCompositionStart = event => {
    rememberSourceSelection(event, true, true);
    composing.current = true;
    contentRef.current = event.currentTarget.value;
  };
  const onCompositionEnd = event => {
    rememberSourceSelection(event, true, true);
    const nextText = event.currentTarget.value;
    composing.current = false;
    contentRef.current = nextText;
    commitDocumentText(nextText);
    if (reloadAfterComposition.current) {
      reloadAfterComposition.current = false;
      scheduleDocumentReload(0);
    }
  };
  const insertDocumentSnippet = snippetValue => {
    if (capabilities.can_edit !== true || loading || composing.current) return false;
    const snippet = String(snippetValue || "");
    if (!snippet) return false;
    const editor = editorRef.current;
    const before = contentRef.current;
    const visualSelection = editorView === "visual" ? visualSelectionRef.current : null;
    let caret = before.length;
    let committed = false;
    if (!editor && visualSelection) {
      const selectedStart = clamp(number(visualSelection.start), 0, before.length);
      const selectedEnd = clamp(number(visualSelection.end), selectedStart, before.length);
      const block = collabDocumentParseBlocks(before).blocks.find(item => selectedStart >= item.start && selectedStart <= item.end);
      if (block && block.type === "text") {
        const visibleStart = collabDocumentInlineVisibleOffset(block.value, clamp(selectedStart - block.sourceStart, 0, block.value.length));
        const visibleEnd = collabDocumentInlineVisibleOffset(block.value, clamp(selectedEnd - block.sourceStart, 0, block.value.length));
        const left = collabDocumentInlineSlice(block.value, 0, visibleStart);
        const right = collabDocumentInlineSlice(block.value, visibleEnd, Number.MAX_SAFE_INTEGER);
        const leading = left ? "\n\n" : "";
        const trailing = right ? "\n\n" : "";
        const replacePrefix = visibleStart === 0 && block.sourceStart > block.start;
        const replaceStart = replacePrefix ? block.start : block.sourceStart;
        committed = replaceDocumentRange(
          replaceStart, block.sourceEnd, left + leading + snippet + trailing + right,
          replacePrefix ? block.source : block.value
        );
        caret = replaceStart + left.length + leading.length + snippet.length;
      } else {
        const start = block ? block.end : selectedStart;
        const leading = start > 0 && before.slice(start - 1, start) !== "\n" ? "\n\n" : "";
        const trailing = start < before.length && before.slice(start, start + 1) !== "\n" ? "\n\n" : "";
        const insertion = leading + snippet + trailing;
        committed = replaceDocumentRange(start, start, insertion, "");
        caret = start + leading.length + snippet.length;
      }
    } else {
      const rawStart = editor ? editor.selectionStart : before.length;
      const rawEnd = editor ? editor.selectionEnd : rawStart;
      const start = clamp(number(rawStart), 0, before.length);
      const end = clamp(number(rawEnd), start, before.length);
      const leading = start > 0 && before.slice(start - 1, start) !== "\n" ? "\n\n" : "";
      const trailing = end < before.length && before.slice(end, end + 1) !== "\n" ? "\n\n" : "";
      const insertion = leading + snippet + trailing;
      committed = commitDocumentText(before.slice(0, start) + insertion + before.slice(end));
      caret = start + leading.length + snippet.length;
    }
    if (!committed) return false;
    setMode("edit");
    setEditorView("visual");
    visualSelectionRef.current = {
      type: "insert", start: caret, end: caret,
      startAffinity: "forward", endAffinity: "forward", active: true, pending: true,
    };
    return true;
  };
  const insertSavedImage = asset => insertDocumentSnippet(
    `![${collabDocumentAssetAlt(asset)}](w2-image:${optionalText(obj(asset).asset_key)})`
  );
  const insertTable = () => insertDocumentSnippet(
    "| 欄位 1 | 欄位 2 |\n| --- | --- |\n| 內容 | 內容 |"
  );
  const insertFormula = () => insertDocumentSnippet("\\[x^2 + y^2 = z^2\\]");
  const uploadDocumentImage = async event => {
    const input = event.currentTarget;
    const file = input.files && input.files[0];
    input.value = "";
    if (!file || uploadingImage || capabilities.can_edit !== true || !networkOnline) return;
    if (
      !["image/png", "image/jpeg", "image/webp"].includes(key(file.type))
      || file.size <= 0
      || file.size > 2 * 1024 * 1024
    ) {
      setError(t("只支援 PNG、JPEG 或 WebP 圖片，最大 2MB。"));
      return;
    }
    if (assetUploadController.current) assetUploadController.current.abort();
    const controller = new AbortController();
    assetUploadController.current = controller;
    setUploadingImage(true);
    setError("");
    try {
      const form = new FormData();
      form.append("image", file, file.name);
      form.append("alt_text", file.name.replace(/\.[^.]+$/, "").slice(0, 160));
      const response = await W2.fetch(
        `/api/tasks/${encodeURIComponent(taskId)}/collaboration/document/images`,
        { method: "POST", body: form, signal: controller.signal }
      );
      const raw = await response.json().catch(() => ({}));
      if (!response.ok) throw Object.assign(new Error(raw.error || raw.message || t("圖片上傳失敗")), { status: response.status });
      if (!mounted.current || tenant !== W2.tenant()) return;
      const payload = collabData(raw);
      const asset = collabDocumentResponse({ assets: [payload.asset] }).assets[0];
      if (!asset) throw new Error(t("圖片上傳失敗"));
      setAssets(current => {
        const next = current.filter(item => item.asset_key !== asset.asset_key);
        return [...next, asset];
      });
      if (!insertSavedImage(asset)) {
        setError(t("圖片已安全保存，但未能插入工作稿；可從已保存圖片重新插入。"));
      }
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant() && (!exception || exception.name !== "AbortError")) {
        setError(exception.message || t("圖片上傳失敗"));
      }
    } finally {
      if (assetUploadController.current === controller) assetUploadController.current = null;
      if (mounted.current) setUploadingImage(false);
    }
  };
  const exportDocument = async () => {
    if (exporting || pendingCount || saving || !networkOnline) return;
    setExporting(true);
    setError("");
    try {
      const raw = await collabJson(
        `/api/tasks/${encodeURIComponent(taskId)}/collaboration/document/export`,
        { cache: "no-store" }
      );
      if (!mounted.current || tenant !== W2.tenant()) return;
      const value = collabData(raw);
      const blob = new Blob([optionalText(value.content)], { type: "text/markdown;charset=utf-8" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = optionalText(value.filename) || `task-${taskId}-working-draft.md`;
      link.rel = "noopener";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => window.URL.revokeObjectURL(url), 0);
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant()) setError(exception.message || t("協作操作失敗"));
    } finally {
      if (mounted.current) setExporting(false);
    }
  };
  const retryDocument = async () => {
    automaticRetryBlocked.current = false;
    transientRetryCount.current = 0;
    const loaded = await loadDocument();
    const pendingHead = queueRef.current.updates[0];
    if (loaded && pendingHead && (pendingHead.dispatched === true || capabilitiesRef.current.can_edit === true)) scheduleFlush(0);
  };
  const terminal = ["completed", "cancelled"].includes(canonicalStatus(first(obj(task).status, obj(task).task_status)));
  const observer = key(role) === "observer";
  const offline = !networkOnline || realtimeState === COLLAB_REALTIME_STATES.OFFLINE;
  const state = offline ? "offline"
    : capabilities.can_edit !== true ? "readonly"
    : saving ? "saving"
    : pendingCount ? "pending"
    : error ? "error" : "saved";
  const statusLabel = state === "offline" ? t("目前離線，草稿已保留")
    : state === "readonly" ? t("唯讀模式")
    : state === "saving" ? t("正在同步工作稿")
    : state === "pending" ? t("等待同步")
    : state === "error" ? t("工作稿同步失敗，已保留在此裝置。")
    : t("工作稿已同步");
  const readOnlyMessage = terminal
    ? t("此任務已結束，工作稿已鎖定。重新進行任務後可繼續編輯。")
    : observer ? t("觀察者可閱讀工作稿，但不能修改。") : "";
  const documentStyle = collabDocumentStyle(content);
  const visualToolsDisabled = capabilities.can_edit !== true || loading || mode !== "edit" || editorView !== "visual";

  return <section className="task-collab-document" data-sequence={number(documentMeta.latest_sequence)}>
    <header className="task-collab-document-head">
      <div><L red>SHARED · RGA/01</L><h3>{t("協作工作稿")}</h3><p>{t("所有協作者可在同一份工作稿中安全共編。")}</p></div>
      <div className="task-collab-document-tools">
        <div className="task-collab-document-modes" role="group" aria-label={t("協作工作稿")}>
          <button type="button" className={mode === "edit" ? "on" : ""} aria-pressed={mode === "edit"} onClick={() => { setMode("edit"); setToolPanel(""); }}>{t("編輯")}</button>
          <button type="button" className={mode === "preview" ? "on" : ""} aria-pressed={mode === "preview"} onClick={() => { setMode("preview"); setToolPanel(""); }}>{t("預覽")}</button>
        </div>
        <button type="button" className="task-collab-document-export" disabled={exporting || pendingCount > 0 || saving || offline || capabilities.can_export === false || !documentMeta.id} onClick={exportDocument}><I name="arrow" size={12}/>{exporting ? "…" : t("匯出")}</button>
      </div>
    </header>
    <div className={"task-collab-document-status is-" + state} role="status" aria-live="polite" aria-atomic="true"><i aria-hidden="true"/><span>{statusLabel}</span>{pendingCount > 0 && <b>{pendingCount}</b>}</div>
    {(error || storageWarning) && <div className="task-inline-error" role="alert"><span>{storageWarning || error}</span><button type="button" onClick={retryDocument}>{t("重新載入")}</button></div>}
    {readOnlyMessage && <p className="task-collab-document-readonly">{readOnlyMessage}</p>}
    <div className="task-collab-document-insert" role="toolbar" aria-label={t("協作工作稿")}>
      <input ref={imageInputRef} className="sr-only" type="file" accept="image/png,image/jpeg,image/webp" tabIndex="-1" onChange={uploadDocumentImage}/>
      <button type="button" disabled={capabilities.can_edit !== true || loading || offline || uploadingImage} onClick={() => imageInputRef.current && imageInputRef.current.click()}><I name="image" size={14}/><span>{uploadingImage ? t("圖片上傳中") + "…" : t("插入圖片")}</span></button>
      <button type="button" disabled={capabilities.can_edit !== true || loading} onClick={insertTable}><I name="table" size={14}/><span>{t("插入表格")}</span></button>
      <button type="button" disabled={capabilities.can_edit !== true || loading} onClick={insertFormula}><span aria-hidden="true">∑</span><span>{t("插入公式")}</span></button>
      <button type="button" disabled={visualToolsDisabled} aria-pressed={toolPanel === "format"} onClick={() => setToolPanel(current => current === "format" ? "" : "format")}><span aria-hidden="true">B</span><span>{t("格式")}</span></button>
      <button type="button" disabled={visualToolsDisabled} aria-pressed={toolPanel === "type"} onClick={() => setToolPanel(current => current === "type" ? "" : "type")}><span aria-hidden="true">Aa</span><span>{t("字體")}</span></button>
      <button type="button" disabled={loading || mode !== "edit"} aria-pressed={editorView === "source"} onClick={() => { setEditorView(current => current === "source" ? "visual" : "source"); setToolPanel(""); }}><span aria-hidden="true">&lt;/&gt;</span><span>{editorView === "source" ? t("回到視覺共編") : t("原文")}</span></button>
      <small>{t("只支援 PNG、JPEG 或 WebP 圖片，最大 2MB。")}</small>
    </div>
    {mode === "edit" && editorView === "visual" && toolPanel === "format" && <div className="task-collab-document-type-tools" role="toolbar" aria-label={t("格式")}>
      <span className="task-collab-document-type-control"><span className="task-collab-document-font-specimen">H</span><button type="button" disabled={visualToolsDisabled} onPointerDown={event => event.preventDefault()} onClick={() => applyHeading(0)}>{t("正文")}</button><button type="button" disabled={visualToolsDisabled} onPointerDown={event => event.preventDefault()} onClick={() => applyHeading(1)}>{t("一級標題")}</button><button type="button" disabled={visualToolsDisabled} onPointerDown={event => event.preventDefault()} onClick={() => applyHeading(2)}>{t("二級標題")}</button></span>
      <span className="task-collab-document-type-control"><span className="task-collab-document-font-specimen">B</span><button type="button" disabled={visualToolsDisabled} onPointerDown={event => event.preventDefault()} onClick={applyBold}>{t("粗體")}</button><button type="button" disabled={visualToolsDisabled} onPointerDown={event => event.preventDefault()} onClick={applyItalic}><em>I</em> · {t("斜體")}</button></span>
      <small>{t("貼上的粗體、標題、清單與表格會安全轉換。")}</small>
    </div>}
    {mode === "edit" && editorView === "visual" && toolPanel === "type" && <div className="task-collab-document-type-tools" role="group" aria-label={t("文件字體")}>
      <label className="task-collab-document-type-control"><span className="task-collab-document-font-specimen">Aa</span><span>{t("字體")}</span><select value={documentStyle.font} disabled={visualToolsDisabled} onChange={event => updateDocumentStyle(event.currentTarget.value, documentStyle.size)}><option value="swiss">{t("瑞士無襯線")}</option><option value="editorial">{t("編輯襯線")}</option><option value="mono">{t("技術等寬")}</option></select></label>
      <label className="task-collab-document-type-control"><span className="task-collab-document-font-specimen">16</span><span>{t("標準")}</span><select value={documentStyle.size} disabled={visualToolsDisabled} onChange={event => updateDocumentStyle(documentStyle.font, event.currentTarget.value)}><option value="sm">{t("小")}</option><option value="md">{t("標準")}</option><option value="lg">{t("舒展")}</option></select></label>
    </div>}
    {!!assets.length && <details className="task-collab-document-assets">
      <summary>{t("已保存圖片")} · {assets.length}</summary>
      <div>{assets.map(asset => <button type="button" key={asset.asset_key} disabled={capabilities.can_edit !== true || loading} onClick={() => insertSavedImage(asset)}>
        <I name="image" size={13}/><span>{collabDocumentAssetAlt(asset)}</span><small>{number(asset.width)}×{number(asset.height)}</small>
      </button>)}</div>
    </details>}
    {loading ? <div className="task-loading" aria-live="polite"><span/><span/><span/><small>{t("同步中")}</small></div>
    : mode === "edit" && editorView === "source" ? <label className="task-collab-document-editor"><span className="sr-only">{t("輸入協作工作稿")}</span><textarea ref={editorRef} value={content} rows="18" readOnly={capabilities.can_edit !== true} aria-readonly={capabilities.can_edit !== true} spellCheck="true" onCompositionStart={onCompositionStart} onCompositionEnd={onCompositionEnd} onChange={onChange} onFocus={event => rememberSourceSelection(event, true)} onSelect={event => rememberSourceSelection(event, true)} onBlur={event => { rememberSourceSelection(event, false); flushDocumentOnBlur(); }} placeholder={t("開始整理共同目標、決定與下一步。")}/></label>
    : mode === "edit" ? <CollaborativeDocumentVisualEditor taskId={taskId} content={content} assets={assets} readOnly={capabilities.can_edit !== true} selectionRef={visualSelectionRef} onReplace={replaceDocumentRange} onSplices={applyDocumentSplices} onComposeStart={onVisualCompositionStart} onComposeEnd={onVisualCompositionEnd} onBlur={flushDocumentOnBlur}/>
    : <div className="task-collab-document-preview" aria-label={t("預覽")}>{content ? <CollaborativeDocumentPreview taskId={taskId} content={content} assets={assets}/> : <div className="task-collab-document-empty"><strong>{t("工作稿尚未有內容")}</strong><p>{t("開始整理共同目標、決定與下一步。")}</p></div>}</div>}
  </section>;
};

const collaborationOpenDefaults = task => {
  const visibility = key(first(obj(task).visibility, obj(task).scope, "private"));
  if (visibility === "private") return { discoverability: "hidden", join_policy: "invite_only" };
  if (visibility === "team") return { discoverability: "team", join_policy: "request" };
  return { discoverability: "company", join_policy: "request" };
};
const CollaborationOpenForm = ({ task, busy, error, onSubmit }) => {
  const visibility = key(first(obj(task).visibility, obj(task).scope, "private"));
  const [form, setForm] = S(() => collaborationOpenDefaults(task));
  const scopes = visibility === "private"
    ? [["hidden", "隱藏"]]
    : visibility === "team" ? [["team", "團隊可見"], ["hidden", "隱藏"]]
    : [["company", "公司可見"], ["team", "團隊可見"], ["hidden", "隱藏"]];
  const policies = visibility === "private"
    ? [["invite_only", "僅限邀請"]]
    : [["open", "自由加入"], ["request", "申請審批"], ["invite_only", "僅限邀請"]];
  const submit = event => {
    event.preventDefault();
    onSubmit(form);
  };
  return <form className="task-collab-open-form" onSubmit={submit}>
    <div className="task-collab-unopened"><I name="user" size={24}/><div><h3>{t("尚未開啟協作")}</h3><p>{t("設定誰能找到此任務，以及加入方式。")}</p></div></div>
    <label className="task-field"><L dim>{t("探索範圍")}</L><select value={form.discoverability} disabled={scopes.length === 1} onChange={event => setForm(current => ({ ...current, discoverability: event.target.value }))}>{scopes.map(([id, label]) => <option key={id} value={id}>{t(label)}</option>)}</select></label>
    <label className="task-field"><L dim>{t("加入方式")}</L><select value={form.join_policy} disabled={policies.length === 1} onChange={event => setForm(current => ({ ...current, join_policy: event.target.value }))}>{policies.map(([id, label]) => <option key={id} value={id}>{t(label)}</option>)}</select></label>
    {error && <div className="task-form-error" role="alert">{error}</div>}
    <B type="submit" kind="primary" disabled={busy}>{busy ? "…" : t("開啟協作")}</B>
  </form>;
};

const CollaborationMembers = ({
  detail, meta, busy, onInvite, onDecision, onTransferOwnership,
  realtimeState, presence,
}) => {
  const members = collabMembers(detail);
  const requests = collabRequests(detail).filter(request => !request.status || key(request.status) === "pending");
  const invitations = collabInvitations(detail).filter(invitation => !invitation.status || key(invitation.status) === "pending");
  const canManage = collabCan(detail, "can_manage");
  const capabilities = collabCapabilities(detail);
  const canApproveRequests = capabilities.can_approve_requests === true
    || (capabilities.can_approve_requests == null && canManage);
  const canRejectRequests = capabilities.can_reject_requests === true
    || (capabilities.can_reject_requests == null && canManage);
  const canReviewRequests = canApproveRequests || canRejectRequests;
  const canTransferOwnership = capabilities.can_transfer_ownership === true;
  const ownerUserId = first(obj(collabWorkspace(detail).owner).user_id);
  const memberIds = new Set(members.map(member => String(collabMemberId(member))));
  const candidateUsers = [...arr(collabData(detail).invite_candidates), ...usersFromMeta(meta)].filter((user, index, all) => {
    const id = first(user.id, user.user_id);
    return id != null && all.findIndex(candidate => String(first(candidate.id, candidate.user_id)) === String(id)) === index;
  });
  const users = candidateUsers.filter(user => {
    const id = first(user.id, user.user_id);
    return id != null && !memberIds.has(String(id));
  });
  const [inviteId, setInviteId] = S("");
  const [inviteRole, setInviteRole] = S("contributor");
  const invite = event => {
    event.preventDefault();
    if (!inviteId) return;
    onInvite(idValue(inviteId), inviteRole).then(ok => { if (ok) setInviteId(""); });
  };
  return <div className="task-collab-members">
    <section>
      <div className="task-section-head"><div><span>01</span><h2>{t("成員")}</h2></div><b>{members.length}</b></div>
      {members.length ? <div className="task-collab-people">{members.map((member, index) => {
        const memberId = collabMemberId(member);
        const memberRole = key(first(member.role, member.member_role));
        const canTransferToMember = canTransferOwnership
          && key(member.state) === "active"
          && memberRole !== "owner"
          && memberRole !== "observer"
          && memberId != null
          && ownerUserId != null
          && String(memberId) !== String(ownerUserId);
        const memberName = collabDisplayName(member, t("協作者"));
        const currentPresence = obj(obj(presence)[String(memberId)]);
        const presenceState = realtimeState !== COLLAB_REALTIME_STATES.LIVE
          ? "unknown" : currentPresence.state === "active" ? "online" : "offline";
        const presenceLabel = presenceState === "online" ? t("在線") : presenceState === "offline" ? t("離線") : t("狀態未知");
        return <article key={String(memberId || index)}>
          <span className="task-collab-avatar">{collabDisplayName(member, "?").slice(0, 1).toUpperCase()}<i className={"is-" + presenceState} aria-hidden="true"/></span>
          <div className="task-collab-member-copy"><strong>{memberName}</strong><small>{t(collabRoleLabel(memberRole))}</small><span className={"task-collab-member-presence is-" + presenceState}><i aria-hidden="true"/>{presenceLabel}</span></div>
          {canTransferToMember && <button type="button" className="task-collab-transfer" disabled={busy} aria-label={t("移交負責人") + " · " + memberName} onClick={() => onTransferOwnership(memberId, memberName)}>{t("移交負責人")}</button>}
        </article>;
      })}</div> : <Empty icon="user" title={t("目前沒有成員")}/>}
    </section>
    {canReviewRequests && <section>
      <div className="task-section-head"><div><span>02</span><h2>{t("待處理申請")}</h2></div><b>{requests.length}</b></div>
      {requests.length ? <div className="task-collab-requests">{requests.map((request, index) => {
        const requestId = first(request.id, request.request_id, request.join_request_id);
        return <article key={String(requestId || index)}><div><strong>{collabDisplayName(first(request.user, request.requester, request), t("協作者"))}</strong>{request.message && <p>{request.message}</p>}</div><div>{canRejectRequests && <button type="button" disabled={busy} onClick={() => onDecision(requestId, "reject")}>{t("拒絕")}</button>}{canApproveRequests && <button type="button" className="primary" disabled={busy} onClick={() => onDecision(requestId, "approve")}>{t("批准")}</button>}</div></article>;
      })}</div> : <p className="task-collab-muted">{t("目前沒有待處理申請")}</p>}
    </section>}
    {canManage && <section>
      <div className="task-section-head"><div><span>03</span><h2>{t("邀請同事")}</h2></div><b>{invitations.length}</b></div>
      {users.length ? <form className="task-collab-invite" onSubmit={invite}><label className="task-field"><L dim>{t("選擇同事")}</L><select value={inviteId} onChange={event => setInviteId(event.target.value)}><option value="">{t("選擇同事")}</option>{users.map((user, index) => <option key={first(user.id, user.user_id, index)} value={optionalText(user.id, user.user_id)}>{collabDisplayName(user, optionalText(user.id, user.user_id))}</option>)}</select></label><label className="task-field"><L dim>{t("角色")}</L><select value={inviteRole} onChange={event => setInviteRole(event.target.value)}>{["contributor", "reviewer", "observer", "coordinator"].map(role => <option key={role} value={role}>{t(collabRoleLabel(role))}</option>)}</select></label><B type="submit" kind="primary" disabled={busy || !inviteId}>{t("發送邀請")}</B></form> : <p className="task-collab-muted">{t("目前沒有邀請")}</p>}
      {!!invitations.length && <div className="task-collab-invites">{invitations.map((invitation, index) => <span key={first(invitation.id, invitation.invitation_id, index)}>{collabDisplayName(first(invitation.user, invitation.invitee, invitation), t("邀請中"))}</span>)}</div>}
    </section>}
  </div>;
};

const meetingPeerId = value => optionalText(
  obj(value).peer_id,
  obj(value).id
);
const meetingPeerName = value => collabDisplayName(
  first(obj(value).user, obj(value).member, obj(value)),
  t("協作者")
);
const meetingPeerUserId = value => first(
  obj(value).user_id,
  obj(obj(value).user).id,
  obj(obj(value).member).user_id
);
const enrichMeetingPeer = (value, members) => {
  const peer = obj(value);
  const userId = meetingPeerUserId(peer);
  const member = userId == null ? null : arr(members).find(item => (
    String(collabMemberId(item)) === String(userId)
  ));
  if (!member) return peer;
  return {
    ...peer,
    user_id: first(peer.user_id, userId),
    display_name: optionalText(peer.display_name, collabDisplayName(member, "")),
  };
};
const meetingMediaError = (error, kind = "microphone") => {
  const name = optionalText(obj(error).name);
  if (!window.isSecureContext) return t("語音會議需要安全的 HTTPS 連線");
  if (kind === "camera") {
    if (name === "NotAllowedError" || name === "SecurityError") return t("鏡頭權限被拒絕，請在瀏覽器或系統設定中允許後重試。");
    if (name === "NotFoundError" || name === "OverconstrainedError") return t("找不到可用的鏡頭");
    if (name === "NotReadableError" || name === "AbortError") return t("鏡頭正被其他程式使用或無法讀取");
    return t("這個瀏覽器不支援視訊鏡頭");
  }
  if (kind === "screen") {
    if (name === "NotAllowedError" || name === "AbortError" || name === "InvalidStateError") return t("螢幕分享權限被拒絕或已取消");
    if (name === "NotFoundError") return t("找不到可分享的螢幕或視窗");
    if (name === "NotReadableError") return t("螢幕擷取無法啟動，請檢查系統隱私設定。");
    return t("這個瀏覽器不支援螢幕分享");
  }
  if (name === "NotAllowedError" || name === "SecurityError") return t("麥克風權限被拒絕，請在瀏覽器或系統設定中允許後重試。");
  if (name === "NotFoundError") return t("找不到可用的麥克風");
  if (name === "NotReadableError" || name === "AbortError") return t("麥克風正被其他程式使用或無法讀取");
  return t("會議連線失敗，請稍後重試");
};
const stopMeetingStream = stream => {
  if (!stream || typeof stream.getTracks !== "function") return;
  stream.getTracks().forEach(track => {
    try { track.stop(); } catch (ignored) {}
  });
};
const meetingRtcConfiguration = value => {
  const raw = obj(value);
  const requestedPolicy = key(first(raw.iceTransportPolicy, raw.ice_transport_policy, "all"));
  const iceTransportPolicy = ["all", "relay"].includes(requestedPolicy) ? requestedPolicy : "all";
  const servers = arr(first(raw.iceServers, raw.ice_servers)).slice(0, 8).map(serverValue => {
    const server = obj(serverValue);
    const rawUrls = first(server.urls, server.url);
    const urls = (Array.isArray(rawUrls) ? rawUrls : [rawUrls])
      .map(url => optionalText(url))
      .filter(url => /^(stun|stuns|turn|turns):/i.test(url))
      .slice(0, 8);
    if (!urls.length) return null;
    return {
      urls,
      ...(server.username != null ? { username: optionalText(server.username) } : {}),
      ...(server.credential != null ? { credential: optionalText(server.credential) } : {}),
    };
  }).filter(Boolean);
  return {
    iceServers: servers,
    iceTransportPolicy,
    bundlePolicy: "max-bundle",
    iceCandidatePoolSize: 0,
  };
};
const meetingRtcCredentialLease = (
  value,
  requestStartedAtValue,
  expectedRequestIdValue
) => {
  const raw = obj(value);
  const requestStartedAt = number(requestStartedAtValue);
  const expectedRequestId = optionalText(expectedRequestIdValue);
  const issuedAt = number(first(
    raw.credentialIssuedAt,
    raw.credential_issued_at
  ));
  const ttlSeconds = number(first(
    raw.credentialTtlSeconds,
    raw.credential_ttl_seconds
  ));
  const expiresAt = number(first(
    raw.credentialExpiresAt,
    raw.credential_expires_at
  ));
  const requestId = optionalText(first(
    raw.credentialRequestId,
    raw.credential_request_id
  ));
  const configuration = meetingRtcConfiguration(raw);
  const hasTurn = configuration.iceServers.some(server => (
    arr(server.urls).some(url => /^turns?:/i.test(optionalText(url)))
    && !!optionalText(server.username)
    && !!optionalText(server.credential)
  ));
  if (
    !Number.isSafeInteger(ttlSeconds)
    || ttlSeconds < COLLAB_MEETING_RTC_TTL_MIN_SECONDS
    || ttlSeconds > COLLAB_MEETING_RTC_TTL_MAX_SECONDS
    || !Number.isSafeInteger(issuedAt)
    || issuedAt <= 0
    || !Number.isSafeInteger(expiresAt)
    || expiresAt <= 0
    || expiresAt - issuedAt !== ttlSeconds
    || !Number.isSafeInteger(requestStartedAt)
    || requestStartedAt <= 0
    || requestStartedAt > Date.now()
    || !expectedRequestId
    || requestId !== expectedRequestId
    || !hasTurn
  ) return null;
  const deadlineMs = requestStartedAt + ttlSeconds * 1000;
  const remainingMs = deadlineMs - Date.now();
  if (remainingMs <= 1000) return null;
  return {
    configuration,
    ttlSeconds,
    issuedAt,
    expiresAt,
    requestId,
    deadlineMs,
    remainingMs,
  };
};

const MeetingAudio = ({ peerId, stream, onBlocked, onPlaying, register }) => {
  const ref = R(null);
  E(() => {
    const audio = ref.current;
    if (!audio) return undefined;
    audio.srcObject = stream || null;
    if (register) register(peerId, audio);
    if (stream) {
      const playback = audio.play();
      if (playback && typeof playback.catch === "function") {
        playback.then(() => onPlaying && onPlaying(peerId)).catch(() => onBlocked && onBlocked(peerId));
      }
    }
    return () => {
      if (register) register(peerId, null);
      if (audio.srcObject === stream) audio.srcObject = null;
    };
  }, [peerId, stream, onBlocked, onPlaying, register]);
  return <audio ref={ref} autoPlay playsInline aria-hidden="true" data-peer-id={peerId}/>;
};

const MeetingVideo = ({ stream, label, local = false }) => {
  const ref = R(null);
  E(() => {
    const video = ref.current;
    if (!video) return undefined;
    video.srcObject = stream || null;
    if (stream) {
      const playback = video.play();
      if (playback && typeof playback.catch === "function") playback.catch(() => {});
    }
    return () => { if (video.srcObject === stream) video.srcObject = null; };
  }, [stream]);
  return <video ref={ref} className={local ? "is-local" : ""} autoPlay playsInline muted aria-label={label}/>;
};

const useCollaborationMeeting = ({
  taskId, tenant, enabled, canShare, canUseCamera, viewerUserId, members,
  clientId, subscribeRtc, setRtcSignalCursor, confirmRtcSignalCursor,
  realtimeState,
}) => {
  const [status, setStatus] = S(COLLAB_MEETING_STATES.IDLE);
  const [participants, setParticipants] = S([]);
  const [muted, setMuted] = S(false);
  const [cameraOn, setCameraOn] = S(false);
  const [sharing, setSharing] = S(false);
  const [screenPeerId, setScreenPeerId] = S("");
  const [localScreen, setLocalScreen] = S(null);
  const [localCamera, setLocalCamera] = S(null);
  const [remoteAudio, setRemoteAudio] = S({});
  const [remoteCameras, setRemoteCameras] = S({});
  const [remoteScreens, setRemoteScreens] = S({});
  const [error, setError] = S("");
  const mounted = R(true);
  const generation = R(0);
  const session = R(null);
  const rtcConfiguration = R({ iceServers: [], iceTransportPolicy: "all" });
  const peers = R(new Map());
  const localAudio = R(null);
  const cameraStream = R(null);
  const cameraEnded = R(null);
  const cameraActive = R(false);
  const displayStream = R(null);
  const displayEnded = R(null);
  const screenActive = R(false);
  const joinController = R(null);
  const joining = R(false);
  const leaving = R(false);
  const cameraStarting = R(false);
  const cameraOperation = R(0);
  const screenStarting = R(false);
  const screenOperation = R(0);
  const desiredState = R({ muted: false, sharing: false, camera_on: false });
  const stateQueue = R(Promise.resolve());
  const stateRevision = R(0);
  const signalAckTimer = R(null);
  const signalReplayTimer = R(null);
  const signalAck = R(null);
  const flushSignalAckRef = R(null);
  const leaveRef = R(null);
  const rtcRefreshTimer = R(null);
  const rtcRefreshController = R(null);
  const rtcRefreshRetry = R(0);
  const rtcRefreshDeadline = R(0);
  const refreshRtcConfigurationRef = R(null);
  const context = R({ taskId, tenant, enabled, canShare, canUseCamera });
  context.current = { taskId, tenant, enabled, canShare, canUseCamera };

  const contextCurrent = C(requestGeneration => (
    mounted.current
    && requestGeneration === generation.current
    && context.current.enabled
    && String(context.current.taskId) === String(taskId)
    && context.current.tenant === tenant
    && tenant === W2.tenant()
  ), [taskId, tenant]);

  const updateParticipant = C((peerId, changes) => {
    if (!mounted.current || !peerId) return;
    setParticipants(current => {
      const index = current.findIndex(item => meetingPeerId(item) === String(peerId));
      if (index < 0) return [...current, { peer_id: String(peerId), ...changes }];
      const next = [...current];
      next[index] = { ...next[index], ...changes };
      return next;
    });
  }, []);

  const closePeer = C(peerIdValue => {
    const peerId = optionalText(peerIdValue);
    const record = peers.current.get(peerId);
    if (!record) return;
    record.closed = true;
    const pc = record.pc;
    pc.onnegotiationneeded = null;
    pc.onicecandidate = null;
    pc.ontrack = null;
    pc.onconnectionstatechange = null;
    pc.oniceconnectionstatechange = null;
    try { pc.close(); } catch (ignored) {}
    peers.current.delete(peerId);
    if (mounted.current) {
      setRemoteAudio(current => {
        const next = { ...current }; delete next[peerId]; return next;
      });
      setRemoteCameras(current => {
        const next = { ...current }; delete next[peerId]; return next;
      });
      setRemoteScreens(current => {
        const next = { ...current }; delete next[peerId]; return next;
      });
    }
  }, []);

  const meetingPost = C((suffix, body, activeSession, options = {}) => {
    const current = activeSession || session.current;
    if (!current || !current.peerToken) return Promise.reject(new Error("meeting session unavailable"));
    const scopedTaskId = first(current.taskId, taskId);
    const path = `/api/tasks/${encodeURIComponent(scopedTaskId)}/collaboration/meeting/${suffix}`;
    const scopedTenant = optionalText(current.tenant);
    if (
      suffix === "leave"
      && options.keepalive === true
      && scopedTenant
      && scopedTenant !== W2.tenant()
    ) {
      const headers = new Headers({
        ...(options.headers || {}),
        "Content-Type": "application/json",
        "X-Tenant-Slug": scopedTenant,
        "X-Collaboration-Peer-Token": current.peerToken,
      });
      const token = W2.token ? W2.token() : "";
      if (token) headers.set("Authorization", "Bearer " + token);
      const requestOptions = {
        ...options,
        method: "POST",
        headers,
        body: JSON.stringify(body || {}),
      };
      return fetch(
        /^https?:/.test(path) ? path : W2.API_BASE + path,
        requestOptions
      ).then(async response => {
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          const exception = new Error(
            data.error || data.message || response.statusText
          );
          exception.status = response.status;
          exception.data = data;
          throw exception;
        }
        return data;
      });
    }
    return W2.post(
      path,
      body,
      {
        ...options,
        headers: {
          ...(options.headers || {}),
          "X-Collaboration-Peer-Token": current.peerToken,
        },
      }
    );
  }, [taskId]);

  const clearRtcRefreshTimer = C(() => {
    if (rtcRefreshTimer.current == null) return;
    window.clearTimeout(rtcRefreshTimer.current);
    rtcRefreshTimer.current = null;
  }, []);

  const cancelRtcConfigurationRefresh = C(() => {
    clearRtcRefreshTimer();
    if (rtcRefreshController.current) {
      rtcRefreshController.current.abort();
      rtcRefreshController.current = null;
    }
    rtcRefreshRetry.current = 0;
    rtcRefreshDeadline.current = 0;
  }, [clearRtcRefreshTimer]);

  const clearSignalAckTimer = C(() => {
    if (signalAckTimer.current == null) return;
    window.clearTimeout(signalAckTimer.current);
    signalAckTimer.current = null;
  }, []);

  const clearSignalReplayTimer = C(() => {
    if (signalReplayTimer.current == null) return;
    window.clearTimeout(signalReplayTimer.current);
    signalReplayTimer.current = null;
  }, []);

  const signalAckSessionActive = C((tracker, activeSession) => (
    tracker
    && signalAck.current === tracker
    && activeSession
    && tracker.session === activeSession
    && session.current === activeSession
    && activeSession.generation === generation.current
    && String(activeSession.taskId) === String(context.current.taskId)
    && activeSession.tenant === context.current.tenant
    && activeSession.tenant === W2.tenant()
  ), []);

  const resetSignalAck = C((activeSession = null, cursorValue = 0) => {
    clearSignalAckTimer();
    clearSignalReplayTimer();
    const cursor = number(cursorValue);
    const initialCursor = Number.isSafeInteger(cursor) && cursor >= 0 ? cursor : 0;
    signalAck.current = activeSession ? {
      session: activeSession,
      pendingSignalId: initialCursor,
      ackedSignalId: initialCursor,
      retryCount: 0,
      retryPaused: false,
      inFlight: null,
      epoch: 1,
      nextOrder: 1,
      commitOrder: 1,
      completions: new Map(),
      seenSignalIds: new Set(),
      replayCount: 0,
    } : null;
  }, [clearSignalAckTimer, clearSignalReplayTimer]);

  const scheduleSignalAck = C((
    delay = COLLAB_MEETING_ACK_DEBOUNCE_MS,
    { resume = false } = {}
  ) => {
    const tracker = signalAck.current;
    const activeSession = tracker && tracker.session;
    if (!signalAckSessionActive(tracker, activeSession)) return false;
    if (resume) {
      tracker.retryCount = 0;
      tracker.retryPaused = false;
    }
    if (
      tracker.pendingSignalId <= tracker.ackedSignalId
      || tracker.inFlight
      || tracker.retryPaused
      || signalAckTimer.current != null
    ) return false;
    const wait = Math.max(0, number(delay));
    const timer = window.setTimeout(() => {
      if (signalAckTimer.current === timer) signalAckTimer.current = null;
      if (!signalAckSessionActive(tracker, activeSession)) return;
      if (flushSignalAckRef.current) {
        flushSignalAckRef.current({ activeSession, keepalive: true });
      }
    }, wait);
    signalAckTimer.current = timer;
    return true;
  }, [signalAckSessionActive]);

  const flushSignalAck = C(({
    activeSession = session.current,
    keepalive = true,
  } = {}) => {
    const tracker = signalAck.current;
    if (!signalAckSessionActive(tracker, activeSession)) return Promise.resolve(false);
    if (tracker.inFlight) return tracker.inFlight;
    const requestedSignalId = tracker.pendingSignalId;
    if (requestedSignalId <= tracker.ackedSignalId) return Promise.resolve(true);
    clearSignalAckTimer();
    let retryDelay = null;
    let succeeded = false;
    const request = meetingPost("ack", {
      signal_id: requestedSignalId,
    }, activeSession, {
      keepalive,
    }).then(rawResponse => {
      const response = collabData(rawResponse);
      if (
        !Number.isSafeInteger(response.acked_signal_id)
        || response.acked_signal_id !== requestedSignalId
        || typeof response.released !== "boolean"
        || typeof response.idempotent !== "boolean"
      ) throw new Error("invalid meeting signal ACK response");
      succeeded = true;
      if (signalAckSessionActive(tracker, activeSession)) {
        tracker.ackedSignalId = Math.max(
          tracker.ackedSignalId,
          requestedSignalId
        );
        tracker.retryCount = 0;
        tracker.retryPaused = false;
      }
      return true;
    }).catch(exception => {
      if (!signalAckSessionActive(tracker, activeSession)) return false;
      tracker.retryCount += 1;
      if (tracker.retryCount <= COLLAB_MEETING_ACK_RETRY_DELAYS.length) {
        const serverDelay = number(first(
          obj(obj(exception).data).retry_after_ms,
          obj(exception).retry_after_ms
        ));
        retryDelay = Math.max(
          COLLAB_MEETING_ACK_RETRY_DELAYS[tracker.retryCount - 1],
          serverDelay > 0 ? clamp(serverDelay, 250, 5000) : 0
        );
      } else {
        tracker.retryPaused = true;
      }
      return false;
    }).finally(() => {
      if (tracker.inFlight === request) tracker.inFlight = null;
      if (!signalAckSessionActive(tracker, activeSession)) return;
      if (retryDelay != null) scheduleSignalAck(retryDelay);
      else if (
        succeeded
        && tracker.pendingSignalId > tracker.ackedSignalId
      ) scheduleSignalAck();
    });
    tracker.inFlight = request;
    return request;
  }, [
    clearSignalAckTimer, meetingPost, scheduleSignalAck,
    signalAckSessionActive,
  ]);
  flushSignalAckRef.current = flushSignalAck;

  const scheduleSignalReplay = C((tracker, activeSession) => {
    if (
      !signalAckSessionActive(tracker, activeSession)
      || signalReplayTimer.current != null
      || typeof setRtcSignalCursor !== "function"
    ) return false;
    const delay = COLLAB_MEETING_SIGNAL_REPLAY_DELAYS[Math.min(
      tracker.replayCount,
      COLLAB_MEETING_SIGNAL_REPLAY_DELAYS.length - 1
    )];
    tracker.replayCount += 1;
    const timer = window.setTimeout(() => {
      if (signalReplayTimer.current === timer) signalReplayTimer.current = null;
      if (!signalAckSessionActive(tracker, activeSession)) return;
      setRtcSignalCursor(tracker.pendingSignalId);
    }, delay);
    signalReplayTimer.current = timer;
    return true;
  }, [setRtcSignalCursor, signalAckSessionActive]);

  const beginSignalProcessing = C(event => {
    const envelope = obj(event);
    const current = session.current;
    const tracker = signalAck.current;
    if (!signalAckSessionActive(tracker, current)) return null;
    const roomId = optionalText(envelope.room_id, obj(envelope.room).id);
    const toPeerId = optionalText(envelope.to_peer_id, envelope.target_peer_id);
    const fromPeerId = optionalText(envelope.from_peer_id, envelope.peer_id);
    const signalId = collabRtcSignalCursor(envelope);
    if (
      !roomId
      || roomId !== current.roomId
      || (toPeerId && toPeerId !== current.peerId)
      || !fromPeerId
      || fromPeerId === current.peerId
      || !Number.isSafeInteger(signalId)
      || signalId <= 0
    ) return null;
    if (
      signalId <= tracker.pendingSignalId
      || tracker.seenSignalIds.has(signalId)
      || tracker.completions.size >= COLLAB_MEETING_ACK_COMPLETION_LIMIT
    ) return null;
    const order = tracker.nextOrder++;
    tracker.seenSignalIds.add(signalId);
    tracker.completions.set(order, {
      signalId,
      accepted: null,
    });
    return {
      tracker,
      session: current,
      epoch: tracker.epoch,
      order,
      signalId,
    };
  }, [signalAckSessionActive]);

  const settleSignalProcessing = C((ticket, accepted) => {
    if (!ticket) return false;
    const tracker = signalAck.current;
    if (
      tracker !== ticket.tracker
      || tracker.epoch !== ticket.epoch
      || !signalAckSessionActive(tracker, ticket.session)
    ) return false;
    const completion = tracker.completions.get(ticket.order);
    if (!completion || completion.signalId !== ticket.signalId) return false;
    completion.accepted = accepted === true;
    let nextSignalId = tracker.pendingSignalId;
    while (true) {
      const next = tracker.completions.get(tracker.commitOrder);
      if (!next || next.accepted !== true) break;
      tracker.completions.delete(tracker.commitOrder);
      tracker.seenSignalIds.delete(next.signalId);
      tracker.commitOrder += 1;
      nextSignalId = Math.max(nextSignalId, next.signalId);
    }
    const blocked = tracker.completions.get(tracker.commitOrder);
    if (nextSignalId > tracker.pendingSignalId) {
      tracker.pendingSignalId = nextSignalId;
      if (
        typeof confirmRtcSignalCursor !== "function"
        || !confirmRtcSignalCursor(nextSignalId)
      ) return false;
      tracker.replayCount = 0;
      clearSignalReplayTimer();
      scheduleSignalAck();
    }
    if (blocked && blocked.accepted === false) {
      scheduleSignalReplay(tracker, ticket.session);
    }
    return true;
  }, [
    clearSignalReplayTimer, confirmRtcSignalCursor, scheduleSignalAck,
    scheduleSignalReplay, signalAckSessionActive,
  ]);

  const resumeSignalProcessing = C(() => {
    const tracker = signalAck.current;
    const activeSession = tracker && tracker.session;
    if (!signalAckSessionActive(tracker, activeSession)) return false;
    clearSignalReplayTimer();
    tracker.epoch += 1;
    tracker.nextOrder = 1;
    tracker.commitOrder = 1;
    tracker.completions.clear();
    tracker.seenSignalIds.clear();
    scheduleSignalAck(COLLAB_MEETING_ACK_DEBOUNCE_MS, { resume: true });
    return true;
  }, [
    clearSignalReplayTimer, scheduleSignalAck, signalAckSessionActive,
  ]);

  const sendSignal = C(async (record, kind, payload, negotiationId) => {
    const current = session.current;
    if (!current || record.closed || record.generation !== current.generation) return false;
    const signalBody = {
      to_peer_id: record.peerId,
      kind,
      client_signal_id: clientRequestId(),
      negotiation_id: negotiationId || clientRequestId(),
      payload,
    };
    let lastException = null;
    for (
      let attempt = 0;
      attempt <= COLLAB_MEETING_SIGNAL_RETRY_DELAYS.length;
      attempt += 1
    ) {
      if (
        session.current !== current
        || record.closed
        || record.generation !== current.generation
        || tenant !== W2.tenant()
      ) return false;
      try {
        const response = collabData(await meetingPost(
          "signal",
          signalBody,
          current
        ));
        if (
          response.accepted !== true
          || !Number.isSafeInteger(response.signal_id)
          || response.signal_id <= 0
          || typeof response.idempotent !== "boolean"
        ) throw new Error("invalid meeting signal response");
        return true;
      } catch (exception) {
        lastException = exception;
        if (attempt >= COLLAB_MEETING_SIGNAL_RETRY_DELAYS.length) break;
        const serverDelay = number(first(
          obj(obj(exception).data).retry_after_ms,
          obj(exception).retry_after_ms
        ));
        const delay = Math.max(
          COLLAB_MEETING_SIGNAL_RETRY_DELAYS[attempt],
          serverDelay > 0 ? clamp(serverDelay, 250, 2000) : 0
        );
        await new Promise(resolve => window.setTimeout(resolve, delay));
      }
    }
    if (mounted.current && session.current === current && tenant === W2.tenant()) {
      setError(lastException && lastException.message
        ? lastException.message
        : t("會議連線失敗，請稍後重試"));
    }
    return false;
  }, [meetingPost, tenant]);

  const queuePeerOperation = C((record, operation) => {
    const queued = record.signalChain.catch(() => {}).then(operation);
    record.signalChain = queued.catch(() => {});
    return queued;
  }, []);

  const ensurePeer = C(peerValue => {
    const remotePeerId = meetingPeerId(peerValue);
    const current = session.current;
    if (!current || !remotePeerId || remotePeerId === current.peerId) return null;
    const existing = peers.current.get(remotePeerId);
    if (existing) {
      existing.peer = { ...existing.peer, ...obj(peerValue) };
      updateParticipant(remotePeerId, {
        ...existing.peer,
        connection_state: existing.connectionState || "connecting",
      });
      return existing;
    }
    if (peers.current.size >= COLLAB_MEETING_MAX_PARTICIPANTS - 1) {
      setError(t("會議已達六人上限"));
      return null;
    }
    let pc;
    let audioTransceiver;
    let cameraTransceiver;
    let screenTransceiver;
    try {
      pc = new window.RTCPeerConnection(rtcConfiguration.current);
      audioTransceiver = pc.addTransceiver("audio", { direction: "sendrecv" });
      cameraTransceiver = pc.addTransceiver("video", { direction: "sendrecv" });
      screenTransceiver = pc.addTransceiver("video", { direction: "sendrecv" });
    } catch (exception) {
      if (pc) {
        try { pc.close(); } catch (ignored) {}
      }
      setError(t("這個瀏覽器不支援語音會議"));
      return null;
    }
    const record = {
      pc,
      peerId: remotePeerId,
      peer: obj(peerValue),
      generation: current.generation,
      polite: String(current.peerId).localeCompare(remotePeerId) > 0,
      makingOffer: false,
      ignoreOffer: false,
      isSettingRemoteAnswerPending: false,
      ignoredNegotiationId: "",
      ignoredNegotiationIds: new Set(),
      localNegotiationId: "",
      remoteNegotiationId: "",
      pendingCandidates: [],
      signalChain: Promise.resolve(),
      restartCount: 0,
      connectionState: "connecting",
      closed: false,
      audioTransceiver,
      cameraTransceiver,
      screenTransceiver,
    };
    peers.current.set(remotePeerId, record);
    updateParticipant(remotePeerId, { ...record.peer, connection_state: "connecting" });
    const micTrack = localAudio.current && localAudio.current.getAudioTracks()[0];
    const cameraTrack = cameraActive.current && cameraStream.current && cameraStream.current.getVideoTracks()[0];
    const screenTrack = screenActive.current && displayStream.current && displayStream.current.getVideoTracks()[0];
    record.audioTransceiver.sender.replaceTrack(micTrack || null).catch(() => {});
    record.cameraTransceiver.sender.replaceTrack(cameraTrack || null).catch(() => {});
    record.screenTransceiver.sender.replaceTrack(screenTrack || null).catch(() => {});

    const active = () => {
      const live = session.current;
      return !!live
        && !record.closed
        && live.generation === record.generation
        && peers.current.get(remotePeerId) === record
        && tenant === W2.tenant();
    };
    pc.onnegotiationneeded = () => {
      queuePeerOperation(record, async () => {
        if (!active()) return;
        const negotiationId = clientRequestId();
        try {
          record.makingOffer = true;
          record.localNegotiationId = negotiationId;
          await pc.setLocalDescription();
          if (!active()) return;
          const description = pc.localDescription;
          if (!description || !["offer", "answer"].includes(description.type)) return;
          await sendSignal(record, description.type, {
            type: description.type,
            sdp: description.sdp,
          }, negotiationId);
        } catch (exception) {
          if (active()) setError(t("會議連線失敗，請稍後重試"));
        } finally {
          record.makingOffer = false;
        }
      }).catch(() => {});
    };
    pc.onicecandidate = event => {
      if (!active() || !event.candidate) return;
      const candidate = typeof event.candidate.toJSON === "function"
        ? event.candidate.toJSON()
        : {
          candidate: event.candidate.candidate,
          sdpMid: event.candidate.sdpMid,
          sdpMLineIndex: event.candidate.sdpMLineIndex,
          usernameFragment: event.candidate.usernameFragment,
        };
      sendSignal(
        record,
        "ice",
        candidate,
        record.localNegotiationId || clientRequestId()
      ).catch(() => {});
    };
    pc.ontrack = event => {
      if (!active()) return;
      const stream = event.streams && event.streams[0]
        ? event.streams[0]
        : new window.MediaStream([event.track]);
      const setter = event.track.kind === "audio"
        ? setRemoteAudio
        : event.transceiver === record.cameraTransceiver ? setRemoteCameras : setRemoteScreens;
      setter(currentStreams => ({ ...currentStreams, [remotePeerId]: stream }));
      event.track.addEventListener("ended", () => {
        if (!mounted.current) return;
        setter(currentStreams => {
          if (currentStreams[remotePeerId] !== stream) return currentStreams;
          const next = { ...currentStreams }; delete next[remotePeerId]; return next;
        });
      }, { once: true });
    };
    const connectionChanged = () => {
      if (!active()) return;
      const nextState = pc.connectionState || pc.iceConnectionState || "connecting";
      record.connectionState = nextState;
      updateParticipant(remotePeerId, { connection_state: nextState });
      if (nextState === "connected") {
        record.restartCount = 0;
        if (mounted.current) setStatus(COLLAB_MEETING_STATES.CONNECTED);
      } else if (nextState === "failed" && record.restartCount < 2) {
        record.restartCount += 1;
        if (mounted.current) setStatus(COLLAB_MEETING_STATES.RECONNECTING);
        try { pc.restartIce(); } catch (ignored) {}
      }
    };
    pc.onconnectionstatechange = connectionChanged;
    pc.oniceconnectionstatechange = connectionChanged;
    return record;
  }, [queuePeerOperation, sendSignal, tenant, updateParticipant]);

  const applySignal = C(event => {
    const envelope = obj(event);
    const current = session.current;
    if (!current) return Promise.resolve(false);
    const roomId = optionalText(envelope.room_id, obj(envelope.room).id);
    const toPeerId = optionalText(envelope.to_peer_id, envelope.target_peer_id);
    const fromPeerId = optionalText(envelope.from_peer_id, envelope.peer_id);
    if (
      !roomId
      || roomId !== current.roomId
      || (toPeerId && toPeerId !== current.peerId)
      || !fromPeerId
      || fromPeerId === current.peerId
    ) return Promise.resolve(false);
    const kind = key(envelope.kind);
    const negotiationId = optionalText(envelope.negotiation_id);
    const wirePayload = obj(envelope.payload);
    const validDescription = (
      (kind === "offer" || kind === "answer")
      && wirePayload.type === kind
      && typeof wirePayload.sdp === "string"
    );
    const validCandidate = (
      kind === "ice"
      && typeof wirePayload.candidate === "string"
      && !!wirePayload.candidate
    );
    if (!negotiationId || (!validDescription && !validCandidate)) {
      return Promise.resolve(false);
    }
    const record = ensurePeer({
      ...enrichMeetingPeer(obj(envelope.peer), members),
      peer_id: fromPeerId,
    });
    if (!record || record.closed) return Promise.resolve(false);
    const pc = record.pc;
    const run = async () => {
      const active = () => (
        session.current === current
        && !record.closed
        && record.generation === current.generation
        && peers.current.get(fromPeerId) === record
        && tenant === W2.tenant()
      );
      if (!active()) return false;
      if (kind === "offer" || kind === "answer") {
        const description = { type: kind, sdp: wirePayload.sdp };
        const readyForOffer = !record.makingOffer
          && (pc.signalingState === "stable" || record.isSettingRemoteAnswerPending);
        const offerCollision = kind === "offer" && !readyForOffer;
        record.ignoreOffer = !record.polite && offerCollision;
        record.ignoredNegotiationId = record.ignoreOffer ? negotiationId : "";
        if (record.ignoreOffer) {
          if (record.ignoredNegotiationIds.size >= 32) {
            record.ignoredNegotiationIds.delete(record.ignoredNegotiationIds.values().next().value);
          }
          if (negotiationId) record.ignoredNegotiationIds.add(negotiationId);
          record.pendingCandidates = record.pendingCandidates.filter(item => (
            item.negotiationId !== negotiationId
          ));
          return true;
        }
        try {
          if (offerCollision && record.polite && pc.signalingState !== "stable") {
            await pc.setLocalDescription({ type: "rollback" });
          }
          if (!active()) return false;
          record.isSettingRemoteAnswerPending = kind === "answer";
          await pc.setRemoteDescription(description);
          record.isSettingRemoteAnswerPending = false;
          if (!active()) return false;
          record.remoteNegotiationId = negotiationId;
          const matchingCandidates = [];
          const remainingCandidates = [];
          for (const item of record.pendingCandidates.splice(0)) {
            if (record.ignoredNegotiationIds.has(item.negotiationId)) continue;
            if (!item.negotiationId || !negotiationId || item.negotiationId === negotiationId) {
              matchingCandidates.push(item);
            } else if (remainingCandidates.length < 128) {
              remainingCandidates.push(item);
            }
          }
          record.pendingCandidates = remainingCandidates;
          for (const item of matchingCandidates) {
            if (item.candidate != null) await pc.addIceCandidate(item.candidate);
          }
          if (kind === "offer") {
            record.localNegotiationId = negotiationId || clientRequestId();
            await pc.setLocalDescription();
            if (!active()) return false;
            const answer = pc.localDescription;
            if (!answer || answer.type !== "answer") return false;
            const answerAccepted = await sendSignal(record, "answer", {
              type: answer.type,
              sdp: answer.sdp,
            }, record.localNegotiationId);
            if (!answerAccepted) return false;
          }
          return true;
        } catch (exception) {
          record.isSettingRemoteAnswerPending = false;
          if (!record.ignoreOffer && active()) setError(t("會議連線失敗，請稍後重試"));
          return false;
        }
      }
      if (kind !== "ice") return false;
      if (record.ignoredNegotiationIds.has(negotiationId)) return true;
      const candidate = {
        candidate: wirePayload.candidate,
        ...(wirePayload.sdpMid != null ? { sdpMid: wirePayload.sdpMid } : {}),
        ...(wirePayload.sdpMLineIndex != null ? { sdpMLineIndex: wirePayload.sdpMLineIndex } : {}),
        ...(wirePayload.usernameFragment != null ? { usernameFragment: wirePayload.usernameFragment } : {}),
      };
      try {
        if (
          !pc.remoteDescription
          || !pc.remoteDescription.type
          || (
            negotiationId
            && record.remoteNegotiationId
            && negotiationId !== record.remoteNegotiationId
          )
        ) {
          if (record.pendingCandidates.length < 128) record.pendingCandidates.push({ candidate, negotiationId });
        } else {
          await pc.addIceCandidate(candidate);
        }
        return true;
      } catch (exception) {
        if (!record.ignoreOffer && active()) setError(t("會議連線失敗，請稍後重試"));
        return false;
      }
    };
    return queuePeerOperation(record, run);
  }, [ensurePeer, members, queuePeerOperation, sendSignal, tenant]);

  const applySnapshot = C(event => {
    const data = collabRealtimePayload(event);
    const current = session.current;
    if (!current) return;
    const room = obj(first(data.room, data));
    const roomId = optionalText(data.room_id, room.id);
    if (roomId && roomId !== current.roomId) return;
    const incoming = arr(first(data.peers, room.peers))
      .filter(peer => meetingPeerId(peer) && meetingPeerId(peer) !== current.peerId)
      .map(peer => enrichMeetingPeer(peer, members))
      .slice(0, COLLAB_MEETING_MAX_PARTICIPANTS - 1);
    const keep = new Set(incoming.map(meetingPeerId));
    incoming.forEach(ensurePeer);
    [...peers.current.keys()].forEach(peerId => { if (!keep.has(peerId)) closePeer(peerId); });
    const selfMember = arr(members).find(member => String(collabMemberId(member)) === String(viewerUserId));
    const selfPeer = {
      peer_id: current.peerId,
      user_id: viewerUserId,
      display_name: collabDisplayName(selfMember, t("本人（預設）")),
      muted: desiredState.current.muted,
      camera_on: desiredState.current.camera_on,
      sharing: desiredState.current.sharing,
      is_self: true,
      connection_state: "connected",
    };
    setParticipants([selfPeer, ...incoming.map(peer => {
      const record = peers.current.get(meetingPeerId(peer));
      return {
        ...peer,
        connection_state: record && record.connectionState
          ? record.connectionState
          : optionalText(peer.connection_state, "connecting"),
      };
    })]);
    const nextScreenPeerId = optionalText(data.screen_peer_id, room.screen_peer_id);
    setScreenPeerId(nextScreenPeerId);
  }, [closePeer, ensurePeer, members, viewerUserId]);

  const disposeLocal = C((nextStatus = COLLAB_MEETING_STATES.IDLE) => {
    const activeSession = session.current;
    if (activeSession) {
      flushSignalAck({ activeSession, keepalive: true }).catch(() => {});
    }
    cancelRtcConfigurationRefresh();
    resetSignalAck();
    generation.current += 1;
    if (joinController.current) joinController.current.abort();
    joinController.current = null;
    const camera = cameraStream.current;
    const cameraTrack = camera && camera.getVideoTracks()[0];
    if (cameraTrack && cameraEnded.current) cameraTrack.removeEventListener("ended", cameraEnded.current);
    cameraEnded.current = null;
    cameraStream.current = null;
    cameraActive.current = false;
    cameraOperation.current += 1;
    cameraStarting.current = false;
    stopMeetingStream(camera);
    const screen = displayStream.current;
    const screenTrack = screen && screen.getVideoTracks()[0];
    if (screenTrack && displayEnded.current) screenTrack.removeEventListener("ended", displayEnded.current);
    displayEnded.current = null;
    displayStream.current = null;
    screenActive.current = false;
    screenOperation.current += 1;
    screenStarting.current = false;
    stopMeetingStream(screen);
    stopMeetingStream(localAudio.current);
    localAudio.current = null;
    rtcConfiguration.current = { iceServers: [], iceTransportPolicy: "all" };
    [...peers.current.keys()].forEach(closePeer);
    session.current = null;
    joining.current = false;
    desiredState.current = { muted: false, sharing: false, camera_on: false };
    stateQueue.current = Promise.resolve();
    stateRevision.current += 1;
    if (mounted.current) {
      setStatus(nextStatus);
      setParticipants([]);
      setMuted(false);
      setCameraOn(false);
      setSharing(false);
      setScreenPeerId("");
      setLocalScreen(null);
      setLocalCamera(null);
      setRemoteAudio({});
      setRemoteCameras({});
      setRemoteScreens({});
    }
  }, [
    cancelRtcConfigurationRefresh, closePeer, flushSignalAck, resetSignalAck,
  ]);

  const enqueueState = C(operation => {
    const queued = stateQueue.current.catch(() => {}).then(operation);
    stateQueue.current = queued.catch(() => {});
    return queued;
  }, []);

  const postState = C((changes, { applyUi = true, silent = false } = {}) => {
    const current = session.current;
    if (!current) return Promise.resolve(false);
    const requested = {
      muted: changes.muted != null ? changes.muted === true : desiredState.current.muted,
      sharing: changes.sharing != null ? changes.sharing === true : desiredState.current.sharing,
      camera_on: changes.camera_on != null ? changes.camera_on === true : desiredState.current.camera_on,
    };
    desiredState.current = requested;
    const revision = ++stateRevision.current;
    return enqueueState(async () => {
      if (session.current !== current || current.generation !== generation.current) return false;
      try {
        const response = collabData(await meetingPost("state", requested, current));
        if (
          typeof response.muted !== "boolean"
          || typeof response.sharing !== "boolean"
          || typeof response.camera_on !== "boolean"
          || (response.peer_id != null && String(response.peer_id) !== String(current.peerId))
          || (response.room_id != null && String(response.room_id) !== String(current.roomId))
        ) throw new Error(t("會議連線失敗，請稍後重試"));
        if (
          mounted.current
          && session.current === current
          && revision === stateRevision.current
        ) {
          desiredState.current = {
            muted: response.muted,
            sharing: response.sharing,
            camera_on: response.camera_on,
          };
          if (applyUi) {
            setMuted(response.muted);
            setCameraOn(response.camera_on);
            setSharing(response.sharing);
            updateParticipant(current.peerId, {
              muted: response.muted,
              camera_on: response.camera_on,
              sharing: response.sharing,
            });
            setScreenPeerId(value => (
              response.sharing ? current.peerId : value === current.peerId ? "" : value
            ));
          }
        }
        return response;
      } catch (exception) {
        if (
          exception.status === 404
          && session.current === current
        ) {
          disposeLocal(COLLAB_MEETING_STATES.ERROR);
          if (mounted.current) {
            setError(t("會議連線已過期，請重新加入。"));
          }
          return false;
        }
        if (!silent && mounted.current && session.current === current) {
          setError(exception.message || t("會議連線失敗，請稍後重試"));
        }
        return false;
      }
    });
  }, [disposeLocal, enqueueState, meetingPost, updateParticipant]);

  const scheduleRtcConfigurationRefresh = C((activeSession, delayMs) => {
    clearRtcRefreshTimer();
    const delay = number(delayMs);
    if (
      !activeSession
      || session.current !== activeSession
      || activeSession.generation !== generation.current
      || activeSession.tenant !== tenant
      || tenant !== W2.tenant()
      || !Number.isFinite(delay)
      || delay < 0
    ) return false;
    rtcRefreshTimer.current = window.setTimeout(() => {
      rtcRefreshTimer.current = null;
      if (refreshRtcConfigurationRef.current) {
        refreshRtcConfigurationRef.current(activeSession);
      }
    }, Math.max(1000, Math.round(delay)));
    return true;
  }, [clearRtcRefreshTimer, tenant]);

  const installRtcConfiguration = C((
    rawConfiguration,
    activeSession,
    {
      updatePeers = false,
      requestStartedAt = 0,
      expectedRequestId = "",
    } = {}
  ) => {
    if (!activeSession || session.current !== activeSession) {
      throw new Error("stale meeting RTC configuration");
    }
    const lease = meetingRtcCredentialLease(
      rawConfiguration,
      requestStartedAt,
      expectedRequestId
    );
    if (!lease) throw new Error("invalid meeting RTC configuration");
    const peerUpdates = updatePeers
      ? [...peers.current.values()]
        .filter(record => (
          !record.closed
          && record.generation === activeSession.generation
        ))
        .map(record => ({
          record,
          peer: { ...obj(record.peer), peer_id: record.peerId },
          rebuild: false,
        }))
      : [];
    peerUpdates.forEach(update => {
      const pc = update.record.pc;
      if (!pc || typeof pc.setConfiguration !== "function") {
        update.rebuild = true;
        return;
      }
      try {
        pc.setConfiguration(lease.configuration);
      } catch (ignored) {
        update.rebuild = true;
      }
    });
    if (
      session.current !== activeSession
      || activeSession.generation !== generation.current
    ) throw new Error("stale meeting RTC configuration");
    rtcConfiguration.current = lease.configuration;
    rtcRefreshRetry.current = 0;
    rtcRefreshDeadline.current = lease.deadlineMs;
    scheduleRtcConfigurationRefresh(
      activeSession,
      lease.remainingMs * COLLAB_MEETING_RTC_REFRESH_RATIO
    );
    peerUpdates.forEach(update => {
      const { record } = update;
      if (!update.rebuild && typeof record.pc.restartIce === "function") {
        try {
          record.restartCount = 0;
          record.pc.restartIce();
          return;
        } catch (ignored) {
          update.rebuild = true;
        }
      } else {
        update.rebuild = true;
      }
      closePeer(record.peerId);
      ensurePeer(update.peer);
    });
    return lease;
  }, [
    closePeer, ensurePeer, scheduleRtcConfigurationRefresh,
  ]);

  const refreshRtcConfiguration = C(async activeSession => {
    const current = activeSession || session.current;
    if (
      !current
      || session.current !== current
      || current.generation !== generation.current
      || current.tenant !== tenant
      || tenant !== W2.tenant()
      || rtcRefreshController.current
    ) return false;
    const remainingLeaseMs = rtcRefreshDeadline.current - Date.now();
    if (remainingLeaseMs <= 1000) {
      disposeLocal(COLLAB_MEETING_STATES.ERROR);
      if (mounted.current) {
        setError(t("會議網路憑證已過期，請重新加入。"));
      }
      return false;
    }
    const controller = new AbortController();
    rtcRefreshController.current = controller;
    const credentialRequestId = clientRequestId();
    const credentialRequestStartedAt = Date.now();
    let requestTimedOut = false;
    const requestTimeout = window.setTimeout(() => {
      requestTimedOut = true;
      controller.abort();
    }, Math.max(
      1000,
      Math.min(
        COLLAB_MEETING_RTC_REFRESH_REQUEST_TIMEOUT_MS,
        remainingLeaseMs - 1000
      )
    ));
    try {
      const response = collabData(await meetingPost(
        "configuration",
        { client_configuration_id: credentialRequestId },
        current,
        { signal: controller.signal }
      ));
      if (
        optionalText(response.room_id) !== current.roomId
        || optionalText(response.peer_id) !== current.peerId
      ) throw new Error("invalid meeting RTC configuration response");
      installRtcConfiguration(
        response.rtc_configuration,
        current,
        {
          updatePeers: true,
          requestStartedAt: credentialRequestStartedAt,
          expectedRequestId: credentialRequestId,
        }
      );
      return true;
    } catch (exception) {
      if (
        (controller.signal.aborted && !requestTimedOut)
        || session.current !== current
        || current.generation !== generation.current
        || current.tenant !== tenant
        || tenant !== W2.tenant()
      ) return false;
      const statusCode = number(obj(exception).status);
      if (
        Number.isSafeInteger(statusCode)
        && statusCode >= 400
        && statusCode < 500
        && statusCode !== 429
      ) {
        disposeLocal(COLLAB_MEETING_STATES.ERROR);
        if (mounted.current) {
          setError(t("會議連線已過期，請重新加入。"));
        }
        return false;
      }
      const retryIndex = rtcRefreshRetry.current;
      if (retryIndex < COLLAB_MEETING_RTC_REFRESH_RETRY_DELAYS.length) {
        const serverDelay = number(first(
          obj(obj(exception).data).retry_after_ms,
          obj(exception).retry_after_ms
        ));
        const retryDelay = Math.max(
          COLLAB_MEETING_RTC_REFRESH_RETRY_DELAYS[retryIndex],
          serverDelay > 0 ? clamp(serverDelay, 1000, 10000) : 0
        );
        if (
          rtcRefreshDeadline.current > 0
          && Date.now() + retryDelay < rtcRefreshDeadline.current
        ) {
          rtcRefreshRetry.current = retryIndex + 1;
          scheduleRtcConfigurationRefresh(current, retryDelay);
          return false;
        }
      }
      disposeLocal(COLLAB_MEETING_STATES.ERROR);
      if (mounted.current) {
        setError(t("會議網路憑證無法續期，請重新加入。"));
      }
      return false;
    } finally {
      window.clearTimeout(requestTimeout);
      if (rtcRefreshController.current === controller) {
        rtcRefreshController.current = null;
      }
    }
  }, [
    disposeLocal, installRtcConfiguration, meetingPost,
    scheduleRtcConfigurationRefresh, tenant,
  ]);
  refreshRtcConfigurationRef.current = refreshRtcConfiguration;

  const leave = C(async ({ keepalive = false } = {}) => {
    if (leaving.current) return false;
    const current = session.current;
    if (!current) { disposeLocal(); return true; }
    leaving.current = true;
    if (mounted.current) setStatus(COLLAB_MEETING_STATES.LEAVING);
    flushSignalAck({ activeSession: current, keepalive: true }).catch(() => {});
    const request = meetingPost("leave", {}, current, { keepalive }).catch(() => null);
    disposeLocal(COLLAB_MEETING_STATES.LEAVING);
    let leaveTimer = null;
    const timeout = new Promise(resolve => {
      leaveTimer = window.setTimeout(
        () => resolve(null),
        COLLAB_MEETING_LEAVE_TIMEOUT_MS
      );
    });
    try { await Promise.race([request, timeout]); } finally {
      if (leaveTimer != null) window.clearTimeout(leaveTimer);
      leaving.current = false;
      if (mounted.current) setStatus(COLLAB_MEETING_STATES.IDLE);
    }
    return true;
  }, [disposeLocal, flushSignalAck, meetingPost]);
  leaveRef.current = leave;

  const join = C(async () => {
    if (joining.current || leaving.current || session.current || !enabled) return false;
    if (!window.isSecureContext) { setError(t("語音會議需要安全的 HTTPS 連線")); return false; }
    if (!window.RTCPeerConnection || !window.MediaStream || !navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError(t("這個瀏覽器不支援語音會議"));
      return false;
    }
    joining.current = true;
    const requestGeneration = ++generation.current;
    const controller = new AbortController();
    joinController.current = controller;
    setError("");
    setStatus(COLLAB_MEETING_STATES.ACQUIRING);
    let stream = null;
    let joinedSession = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: { ideal: true },
          noiseSuppression: { ideal: true },
          autoGainControl: { ideal: true },
        },
        video: false,
      });
      if (!contextCurrent(requestGeneration)) { stopMeetingStream(stream); return false; }
      localAudio.current = stream;
      setStatus(COLLAB_MEETING_STATES.JOINING);
      const joinRequestId = clientRequestId();
      const joinRequestStartedAt = Date.now();
      const data = collabData(await W2.post(
        `/api/tasks/${encodeURIComponent(taskId)}/collaboration/meeting/join`,
        {
          client_id: clientId,
          client_join_id: joinRequestId,
          media_protocol: COLLAB_MEETING_MEDIA_PROTOCOL,
        },
        { signal: controller.signal }
      ));
      if (optionalText(data.media_protocol) !== COLLAB_MEETING_MEDIA_PROTOCOL) {
        throw new Error(t("會議功能已更新，請重新整理頁面後再加入"));
      }
      const roomId = optionalText(data.room_id);
      const peerId = optionalText(data.peer_id);
      const peerToken = optionalText(data.peer_token);
      if (!roomId || !peerId || !peerToken) throw new Error(t("會議連線失敗，請稍後重試"));
      const activeSession = {
        roomId,
        peerId,
        peerToken,
        generation: requestGeneration,
        taskId,
        tenant,
      };
      joinedSession = activeSession;
      if (!contextCurrent(requestGeneration)) {
        stopMeetingStream(stream);
        if (localAudio.current === stream) localAudio.current = null;
        meetingPost("leave", {}, activeSession, { keepalive: true }).catch(() => {});
        return false;
      }
      const incoming = arr(data.peers)
        .filter(peer => meetingPeerId(peer) && meetingPeerId(peer) !== peerId)
        .map(peer => enrichMeetingPeer(peer, members));
      if (incoming.length > COLLAB_MEETING_MAX_PARTICIPANTS - 1) throw new Error(t("會議已達六人上限"));
      session.current = activeSession;
      resetSignalAck(activeSession, data.signal_cursor);
      installRtcConfiguration(
        data.rtc_configuration,
        activeSession,
        {
          requestStartedAt: joinRequestStartedAt,
          expectedRequestId: joinRequestId,
        }
      );
      desiredState.current = { muted: false, sharing: false, camera_on: false };
      setRtcSignalCursor(data.signal_cursor);
      setScreenPeerId(optionalText(data.screen_peer_id));
      const selfMember = arr(members).find(member => String(collabMemberId(member)) === String(viewerUserId));
      incoming.forEach(ensurePeer);
      setParticipants([{
        peer_id: peerId,
        user_id: viewerUserId,
        display_name: collabDisplayName(selfMember, t("本人（預設）")),
        is_self: true,
        muted: false,
        camera_on: false,
        sharing: false,
        connection_state: "connected",
      }, ...incoming.map(peer => {
        const record = peers.current.get(meetingPeerId(peer));
        return {
          ...peer,
          connection_state: record && record.connectionState
            ? record.connectionState
            : "connecting",
        };
      })]);
      setStatus(COLLAB_MEETING_STATES.CONNECTED);
      postState({ muted: false, sharing: false, camera_on: false });
      return true;
    } catch (exception) {
      const stale = requestGeneration !== generation.current
        || !mounted.current
        || tenant !== W2.tenant();
      const ownsAttempt = (
        joinController.current === controller
        && requestGeneration === generation.current
      );
      const joined = joinedSession;
      if (joined) meetingPost("leave", {}, joined, { keepalive: true }).catch(() => {});
      if (!ownsAttempt) {
        if (localAudio.current === stream) localAudio.current = null;
        stopMeetingStream(stream);
        return false;
      }
      disposeLocal(COLLAB_MEETING_STATES.ERROR);
      if (!stale && mounted.current && tenant === W2.tenant()) {
        const mediaErrorNames = ["NotAllowedError", "NotFoundError", "NotReadableError", "AbortError", "SecurityError", "OverconstrainedError"];
        const protocolMismatch = number(exception.status) === 400
          || optionalText(exception.message) === "會議功能已更新，請重新整理頁面後再加入";
        setError(protocolMismatch
          ? t("會議功能已更新，請重新整理頁面後再加入")
          : exception.status === 503
          ? t("語音會議服務目前無法使用，請稍後再試。")
          : mediaErrorNames.includes(optionalText(obj(exception).name))
            ? meetingMediaError(exception, "microphone")
            : (exception.message || t("會議連線失敗，請稍後重試")));
        setStatus(COLLAB_MEETING_STATES.ERROR);
      }
      return false;
    } finally {
      if (joinController.current === controller) {
        joinController.current = null;
        joining.current = false;
      }
    }
  }, [clientId, contextCurrent, disposeLocal, enabled, ensurePeer, installRtcConfiguration, meetingPost, members, postState, resetSignalAck, setRtcSignalCursor, taskId, tenant, viewerUserId]);

  const toggleMute = C(() => {
    const stream = localAudio.current;
    if (!stream) return;
    const previousMuted = desiredState.current.muted;
    const nextMuted = !previousMuted;
    desiredState.current = { ...desiredState.current, muted: nextMuted };
    stream.getAudioTracks().forEach(track => { track.enabled = !nextMuted; });
    setMuted(nextMuted);
    const current = session.current;
    if (current) updateParticipant(current.peerId, { muted: nextMuted });
    postState({ muted: nextMuted }).then(result => {
      if (
        result
        || !mounted.current
        || session.current !== current
        || desiredState.current.muted !== nextMuted
      ) return;
      desiredState.current = { ...desiredState.current, muted: previousMuted };
      stateRevision.current += 1;
      stream.getAudioTracks().forEach(track => { track.enabled = !previousMuted; });
      setMuted(previousMuted);
      if (current) updateParticipant(current.peerId, { muted: previousMuted });
    });
  }, [postState, updateParticipant]);

  const stopCamera = C(async ({
    notify = true,
    silent = false,
    expectedStream = null,
    expectedSession = null,
  } = {}) => {
    const current = session.current;
    if (
      (expectedStream && cameraStream.current !== expectedStream)
      || (expectedSession && current !== expectedSession)
    ) {
      stopMeetingStream(expectedStream);
      return false;
    }
    const operation = ++cameraOperation.current;
    const stream = cameraStream.current;
    const track = stream && stream.getVideoTracks()[0];
    if (track && cameraEnded.current) track.removeEventListener("ended", cameraEnded.current);
    cameraEnded.current = null;
    cameraStream.current = null;
    cameraActive.current = false;
    cameraStarting.current = false;
    desiredState.current = { ...desiredState.current, camera_on: false };
    stopMeetingStream(stream);
    await Promise.allSettled([...peers.current.values()].map(record => (
      record.cameraTransceiver.sender.replaceTrack(null)
    )));
    if (cameraOperation.current !== operation || session.current !== current) return false;
    setLocalCamera(null);
    setCameraOn(false);
    if (current) {
      updateParticipant(current.peerId, { camera_on: false });
      if (notify) return !!(await postState({ camera_on: false }, { applyUi: false, silent }));
    }
    return true;
  }, [postState, updateParticipant]);

  const startCamera = C(async () => {
    const current = session.current;
    if (!current || !canUseCamera || cameraStream.current || cameraStarting.current) return false;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      setError(t("這個瀏覽器不支援視訊鏡頭"));
      return false;
    }
    cameraStarting.current = true;
    const operation = ++cameraOperation.current;
    const ownsOperation = () => (
      cameraOperation.current === operation
      && session.current === current
      && tenant === W2.tenant()
    );
    setError("");
    let stream;
    let reserved = false;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false,
        video: {
          facingMode: { ideal: "user" },
          width: { ideal: 640, max: 960 },
          height: { ideal: 360, max: 540 },
          frameRate: { ideal: 15, max: 24 },
        },
      });
      if (!ownsOperation()) { stopMeetingStream(stream); return false; }
      stream.getAudioTracks().forEach(track => track.stop());
      const track = stream.getVideoTracks()[0];
      if (!track) throw Object.assign(new Error(t("找不到可用的鏡頭")), { name: "NotFoundError" });
      const ended = () => {
        if (cameraStream.current === stream) {
          stopCamera({
            notify: true,
            expectedStream: stream,
            expectedSession: current,
          });
        }
      };
      cameraStream.current = stream;
      cameraEnded.current = ended;
      track.addEventListener("ended", ended, { once: true });
      const reservation = await postState({ camera_on: true }, { applyUi: false });
      if (!reservation || reservation.camera_on !== true || !ownsOperation()) {
        if (cameraStream.current === stream) {
          await stopCamera({
            notify: reservation && reservation.camera_on === true,
            silent: true,
            expectedStream: stream,
            expectedSession: current,
          });
        } else stopMeetingStream(stream);
        return false;
      }
      reserved = true;
      cameraActive.current = true;
      await Promise.all([...peers.current.values()].map(record => (
        record.cameraTransceiver.sender.replaceTrack(track)
      )));
      if (!ownsOperation() || cameraStream.current !== stream) {
        await stopCamera({
          notify: true,
          silent: true,
          expectedStream: stream,
          expectedSession: current,
        });
        return false;
      }
      setLocalCamera(stream);
      setCameraOn(true);
      updateParticipant(current.peerId, { camera_on: true });
      cameraStarting.current = false;
      return true;
    } catch (exception) {
      if (ownsOperation() && cameraStream.current === stream) {
        await stopCamera({
          notify: reserved,
          silent: true,
          expectedStream: stream,
          expectedSession: current,
        });
      } else stopMeetingStream(stream);
      if (mounted.current && session.current === current) setError(meetingMediaError(exception, "camera"));
      return false;
    } finally {
      if (cameraOperation.current === operation) cameraStarting.current = false;
    }
  }, [canUseCamera, postState, stopCamera, tenant, updateParticipant]);

  const stopSharing = C(async ({
    notify = true,
    silent = false,
    retry = true,
    expectedStream = null,
    expectedSession = null,
  } = {}) => {
    const current = session.current;
    if (
      (expectedStream && displayStream.current !== expectedStream)
      || (expectedSession && current !== expectedSession)
    ) {
      stopMeetingStream(expectedStream);
      return false;
    }
    const operation = ++screenOperation.current;
    const stream = displayStream.current;
    const track = stream && stream.getVideoTracks()[0];
    if (track && displayEnded.current) track.removeEventListener("ended", displayEnded.current);
    displayEnded.current = null;
    displayStream.current = null;
    screenActive.current = false;
    screenStarting.current = false;
    desiredState.current = { ...desiredState.current, sharing: false };
    stopMeetingStream(stream);
    await Promise.allSettled([...peers.current.values()].map(record => (
      record.screenTransceiver.sender.replaceTrack(null)
    )));
    if (
      screenOperation.current !== operation
      || session.current !== current
    ) return false;
    setLocalScreen(null);
    setSharing(false);
    if (current) {
      setScreenPeerId(value => value === current.peerId ? "" : value);
      updateParticipant(current.peerId, { sharing: false });
      if (notify) {
        let result = await postState({ sharing: false }, { applyUi: false, silent });
        if (!result && retry && session.current === current) {
          result = await postState(
            { sharing: false },
            { applyUi: false, silent: true }
          );
        }
        return !!result;
      }
    }
    return true;
  }, [postState, updateParticipant]);

  const startSharing = C(async () => {
    const current = session.current;
    if (!current || !canShare || displayStream.current || screenStarting.current) return false;
    if (screenPeerId && screenPeerId !== current.peerId) {
      setError(t("目前有人正在分享螢幕"));
      return false;
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setError(t("這個瀏覽器不支援螢幕分享"));
      return false;
    }
    screenStarting.current = true;
    const operation = ++screenOperation.current;
    const ownsOperation = () => (
      screenOperation.current === operation
      && session.current === current
      && tenant === W2.tenant()
    );
    setError("");
    let stream;
    let reserved = false;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: { ideal: 15, max: 30 } },
        audio: false,
      });
      if (!ownsOperation()) {
        stopMeetingStream(stream);
        return false;
      }
      const track = stream.getVideoTracks()[0];
      if (!track) throw new Error(t("找不到可分享的螢幕或視窗"));
      const ended = () => {
        if (displayStream.current === stream) {
          stopSharing({
            notify: true,
            expectedStream: stream,
            expectedSession: current,
          });
        }
      };
      displayStream.current = stream;
      displayEnded.current = ended;
      track.addEventListener("ended", ended, { once: true });
      const reservation = await postState({ sharing: true }, { applyUi: false });
      if (!reservation || reservation.sharing !== true) {
        if (ownsOperation() && displayStream.current === stream) {
          desiredState.current = { ...desiredState.current, sharing: false };
          stateRevision.current += 1;
          await stopSharing({
            notify: true,
            silent: true,
            expectedStream: stream,
            expectedSession: current,
          });
        } else stopMeetingStream(stream);
        return false;
      }
      reserved = true;
      if (
        !ownsOperation()
        || displayStream.current !== stream
      ) {
        if (displayStream.current === stream && session.current === current) {
          await stopSharing({
            notify: true,
            expectedStream: stream,
            expectedSession: current,
          });
        } else stopMeetingStream(stream);
        return false;
      }
      screenActive.current = true;
      await Promise.all([...peers.current.values()].map(record => (
        record.screenTransceiver.sender.replaceTrack(track)
      )));
      if (!ownsOperation() || displayStream.current !== stream) {
        stopMeetingStream(stream);
        return false;
      }
      setLocalScreen(stream);
      setSharing(true);
      setScreenPeerId(current.peerId);
      updateParticipant(current.peerId, { sharing: true });
      screenStarting.current = false;
      return true;
    } catch (exception) {
      if (
        ownsOperation()
        && displayStream.current === stream
      ) {
        await stopSharing({
          notify: reserved,
          expectedStream: stream,
          expectedSession: current,
        });
      }
      else stopMeetingStream(stream);
      if (mounted.current && session.current === current) {
        setError(meetingMediaError(exception, "screen"));
      }
      return false;
    } finally {
      if (screenOperation.current === operation) {
        screenStarting.current = false;
      }
    }
  }, [canShare, postState, screenPeerId, stopSharing, tenant, updateParticipant]);

  const validateMeetingSession = C(() => {
    const current = session.current;
    if (!current) return Promise.resolve(false);
    if (mounted.current) setStatus(COLLAB_MEETING_STATES.RECONNECTING);
    return postState(
      { ...desiredState.current },
      { applyUi: false, silent: true }
    ).then(result => {
      if (
        result
        && mounted.current
        && session.current === current
      ) setStatus(COLLAB_MEETING_STATES.CONNECTED);
      return !!result;
    });
  }, [postState]);

  E(() => {
    if (typeof subscribeRtc !== "function") return undefined;
    return subscribeRtc(event => {
      const type = collabRealtimeType(event);
      if (type === "ready") {
        resumeSignalProcessing();
        validateMeetingSession();
      } else if (type === "access.revoked") {
        if (leaveRef.current) leaveRef.current({ keepalive: true });
      } else if (type === "rtc.room.snapshot") {
        applySnapshot(event);
      } else if (type === "rtc.signal") {
        const ticket = beginSignalProcessing(event);
        if (!ticket) return;
        Promise.resolve()
          .then(() => applySignal(event))
          .then(
            accepted => settleSignalProcessing(ticket, accepted),
            () => settleSignalProcessing(ticket, false)
          );
      }
    });
  }, [
    applySignal, applySnapshot, beginSignalProcessing,
    resumeSignalProcessing, settleSignalProcessing, subscribeRtc,
    validateMeetingSession,
  ]);

  E(() => {
    if (!session.current) return;
    if ([COLLAB_REALTIME_STATES.RETRYING, COLLAB_REALTIME_STATES.FALLBACK, COLLAB_REALTIME_STATES.OFFLINE].includes(realtimeState)) {
      setStatus(COLLAB_MEETING_STATES.RECONNECTING);
    }
  }, [realtimeState]);

  E(() => {
    if (
      !session.current
      || ![COLLAB_MEETING_STATES.CONNECTED, COLLAB_MEETING_STATES.RECONNECTING].includes(status)
    ) return undefined;
    const timer = window.setInterval(() => {
      if (!session.current) return;
      postState({ ...desiredState.current }, { applyUi: false, silent: true });
    }, 20000);
    return () => window.clearInterval(timer);
  }, [postState, status]);

  E(() => {
    if (
      !enabled
      && leaveRef.current
      && (session.current || joining.current || localAudio.current || cameraStream.current || displayStream.current)
    ) leaveRef.current({ keepalive: true });
  }, [enabled]);

  E(() => {
    if (!canShare && displayStream.current) stopSharing({ notify: true });
  }, [canShare, stopSharing]);

  E(() => {
    if (!canUseCamera && cameraStream.current) stopCamera({ notify: true });
  }, [canUseCamera, stopCamera]);

  E(() => {
    const onPageHide = () => {
      if (leaveRef.current) leaveRef.current({ keepalive: true });
    };
    window.addEventListener("pagehide", onPageHide);
    return () => {
      window.removeEventListener("pagehide", onPageHide);
      mounted.current = false;
      if (leaveRef.current) leaveRef.current({ keepalive: true });
      else disposeLocal();
    };
  }, [disposeLocal]);

  const voiceSupported = !!(window.isSecureContext && window.RTCPeerConnection && window.MediaStream && navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
  const cameraSupported = voiceSupported;
  const sharingSupported = !!(navigator.mediaDevices && navigator.mediaDevices.getDisplayMedia);
  const joined = !!session.current && [COLLAB_MEETING_STATES.CONNECTED, COLLAB_MEETING_STATES.RECONNECTING].includes(status);
  return {
    status, joined, participants, muted, cameraOn, sharing, screenPeerId,
    localScreen, localCamera, remoteAudio, remoteCameras, remoteScreens, error,
    voiceSupported, cameraSupported, cameraAllowed: canUseCamera === true, sharingSupported,
    join, leave, toggleMute, startCamera, stopCamera, startSharing, stopSharing,
  };
};

const meetingStatusLabel = state => ({
  [COLLAB_MEETING_STATES.ACQUIRING]: "正在取得麥克風權限",
  [COLLAB_MEETING_STATES.JOINING]: "正在加入會議",
  [COLLAB_MEETING_STATES.CONNECTED]: "會議連線中",
  [COLLAB_MEETING_STATES.RECONNECTING]: "會議重新連線中",
  [COLLAB_MEETING_STATES.LEAVING]: "離開影音會議",
}[state] || "影音會議");

const CollaborationMeetingAudioHost = ({ meeting }) => {
  const [blockedAudio, setBlockedAudio] = S([]);
  const audioElements = R(new Map());
  const registerAudio = C((peerId, element) => {
    if (element) audioElements.current.set(peerId, element);
    else audioElements.current.delete(peerId);
  }, []);
  const audioBlocked = C(peerId => {
    setBlockedAudio(current => current.includes(peerId) ? current : [...current, peerId]);
  }, []);
  const audioPlaying = C(peerId => {
    setBlockedAudio(current => current.filter(value => value !== peerId));
  }, []);
  const retryAudio = C(async () => {
    const attempts = [...audioElements.current.entries()].map(([peerId, audio]) => {
      try {
        return Promise.resolve(audio.play()).then(() => null).catch(() => peerId);
      } catch (ignored) {
        return Promise.resolve(peerId);
      }
    });
    const results = await Promise.all(attempts);
    setBlockedAudio(results.filter(Boolean));
  }, []);
  E(() => {
    const active = new Set(Object.keys(meeting.remoteAudio));
    setBlockedAudio(current => current.filter(peerId => active.has(peerId)));
  }, [meeting.remoteAudio]);
  return <div className="task-collab-audio-host" role="region" aria-label={t("影音會議")}>
    <div className="task-collab-audio-rack" aria-hidden="true">{Object.entries(meeting.remoteAudio).map(([peerId, stream]) => (
      <MeetingAudio key={peerId} peerId={peerId} stream={stream} register={registerAudio} onBlocked={audioBlocked} onPlaying={audioPlaying}/>
    ))}</div>
    {!!blockedAudio.length && <div className="task-collab-playback-blocked" role="alert">
      <span>{t("瀏覽器阻止自動播放會議音訊。")}</span><button type="button" onClick={retryAudio}>{t("點擊播放會議音訊")}</button>
    </div>}
  </div>;
};

const CollaborationMeeting = ({ meeting, canShare }) => {
  const screenOwner = meeting.participants.find(peer => meetingPeerId(peer) === meeting.screenPeerId);
  const remoteScreen = meeting.screenPeerId && !meeting.sharing
    ? meeting.remoteScreens[meeting.screenPeerId]
    : null;
  const cameraTiles = meeting.participants.map(peer => {
    const peerId = meetingPeerId(peer);
    const stream = peer.is_self ? meeting.localCamera : meeting.remoteCameras[peerId];
    return peer.camera_on === true ? { peer, peerId, stream } : null;
  }).filter(Boolean);
  const hasScreen = !!(meeting.localScreen || remoteScreen);
  const busy = [COLLAB_MEETING_STATES.ACQUIRING, COLLAB_MEETING_STATES.JOINING, COLLAB_MEETING_STATES.LEAVING].includes(meeting.status);
  if (!meeting.joined) return <section className="task-collab-meeting is-idle" aria-labelledby="task-collab-meeting-title">
    <div className="task-collab-meeting-welcome">
      <I name="camera" size={28}/>
      <div><L red>VIDEO · P2P/01</L><h3 id="task-collab-meeting-title">{t("影音會議")}</h3><p>{t("加入影音會議")}</p></div>
    </div>
    {meeting.error && <div className="task-form-error" role="alert">{meeting.error}</div>}
    {!meeting.voiceSupported && !meeting.error && <div className="task-form-error" role="alert">{t("這個瀏覽器不支援語音會議")}</div>}
    <button type="button" className="task-collab-meeting-join" disabled={busy || !meeting.voiceSupported} onClick={meeting.join}>
      <I name="camera" size={17}/><span>{busy ? t(meetingStatusLabel(meeting.status)) : t("加入影音會議")}</span>
    </button>
  </section>;
  return <section className={"task-collab-meeting is-" + meeting.status} aria-labelledby="task-collab-meeting-title">
    <header className="task-collab-meeting-head">
      <div><L red>VIDEO · P2P/01</L><h3 id="task-collab-meeting-title">{t("影音會議")}</h3></div>
      <span className="task-collab-meeting-status" role="status" aria-live="polite" aria-atomic="true"><i aria-hidden="true"/>{t(meetingStatusLabel(meeting.status))} · {meeting.participants.length}/{COLLAB_MEETING_MAX_PARTICIPANTS}</span>
    </header>
    {meeting.error && <div className="task-inline-error" role="alert"><span>{meeting.error}</span></div>}
    <div className="task-collab-meeting-layout">
      <figure className={"task-collab-meeting-stage" + (hasScreen ? " has-screen" : " has-cameras")}>
        {meeting.localScreen
          ? <MeetingVideo stream={meeting.localScreen} label={t("你的螢幕")}/>
          : remoteScreen
            ? <MeetingVideo stream={remoteScreen} label={meetingPeerName(screenOwner)}/>
            : cameraTiles.length
              ? <div className="task-collab-camera-grid">{cameraTiles.map(({ peer, peerId, stream }) => <div className={"task-collab-camera-tile" + (peer.is_self ? " is-self" : "")} key={peerId}>
                {stream ? <MeetingVideo stream={stream} label={peer.is_self ? t("你的鏡頭") : meetingPeerName(peer)} local={peer.is_self}/> : <div className="task-collab-camera-wait"><span>{meetingPeerName(peer).slice(0, 1).toUpperCase()}</span><small>{t("鏡頭連線中")}</small></div>}
                <b>{peer.is_self ? t("你的鏡頭") : meetingPeerName(peer)}</b>
              </div>)}</div>
              : <div className="task-collab-meeting-stage-empty"><I name="camera" size={30}/><strong>{t("開啟鏡頭")}</strong></div>}
        {hasScreen && cameraTiles.length > 0 && <div className="task-collab-camera-rail">{cameraTiles.map(({ peer, peerId, stream }) => <div className={"task-collab-camera-tile" + (peer.is_self ? " is-self" : "")} key={peerId}>
          {stream ? <MeetingVideo stream={stream} label={peer.is_self ? t("你的鏡頭") : meetingPeerName(peer)} local={peer.is_self}/> : <div className="task-collab-camera-wait"><span>{meetingPeerName(peer).slice(0, 1).toUpperCase()}</span></div>}
          <b>{peer.is_self ? t("你的鏡頭") : meetingPeerName(peer)}</b>
        </div>)}</div>}
        {hasScreen && <figcaption>{meeting.localScreen ? t("你的螢幕") : meetingPeerName(screenOwner)}</figcaption>}
      </figure>
      <aside className="task-collab-meeting-participants" aria-labelledby="task-collab-participants-title">
        <div className="task-section-head"><div><span>01</span><h2 id="task-collab-participants-title">{t("會議參與者")}</h2></div><b>{meeting.participants.length}</b></div>
        <ul>{meeting.participants.map(peer => {
          const peerId = meetingPeerId(peer);
          const peerMuted = peer.muted === true;
          const peerCamera = peer.camera_on === true;
          const peerSharing = peer.sharing === true || peerId === meeting.screenPeerId;
          return <li key={peerId} className={peer.is_self ? "is-self" : ""}>
            <span className="task-collab-avatar">{meetingPeerName(peer).slice(0, 1).toUpperCase()}</span>
            <div><strong>{meetingPeerName(peer)}</strong><small>{peer.connection_state || "connected"}</small></div>
            <span className="task-collab-meeting-peer-state">{peerMuted && <b>{t("已靜音")}</b>}{peerCamera && <b>{t("鏡頭已開啟")}</b>}{peerSharing && <b>{t("分享中")}</b>}</span>
          </li>;
        })}</ul>
      </aside>
    </div>
    <div className="task-collab-meeting-controls" role="toolbar" aria-label={t("會議控制")}>
      <button type="button" className={meeting.muted ? "is-on" : ""} aria-pressed={meeting.muted} onClick={meeting.toggleMute}><I name="mic" size={17}/><span>{t(meeting.muted ? "取消靜音" : "麥克風靜音")}</span></button>
      <button type="button" className={meeting.cameraOn ? "is-on" : ""} aria-pressed={meeting.cameraOn} disabled={!meeting.cameraSupported || !meeting.cameraAllowed} title={!meeting.cameraSupported ? t("這個瀏覽器不支援視訊鏡頭") : ""} onClick={meeting.cameraOn ? () => meeting.stopCamera() : meeting.startCamera}><I name="camera" size={17}/><span>{t(meeting.cameraOn ? "關閉鏡頭" : "開啟鏡頭")}</span></button>
      <button type="button" className={meeting.sharing ? "is-on" : ""} aria-pressed={meeting.sharing} disabled={(!meeting.sharing && !canShare) || !meeting.sharingSupported || (!!meeting.screenPeerId && !meeting.sharing)} title={!meeting.sharingSupported ? t("這個瀏覽器不支援螢幕分享") : ""} onClick={meeting.sharing ? () => meeting.stopSharing() : meeting.startSharing}><I name="eye" size={17}/><span>{t(meeting.sharing ? "停止分享" : "分享螢幕")}</span></button>
      <button type="button" className="danger" onClick={() => meeting.leave()}><I name="x" size={17}/><span>{t("離開影音會議")}</span></button>
    </div>
  </section>;
};

const CollaborationMeetingMini = ({ meeting, onOpen }) => (
  <aside className="task-collab-meeting-mini" aria-label={t("影音會議")}>
    <span role="status" aria-live="polite" aria-atomic="true"><i aria-hidden="true"/>{t(meetingStatusLabel(meeting.status))}{meeting.cameraOn && " · " + t("鏡頭已開啟")}{meeting.sharing && " · " + t("分享中")}</span>
    <div role="toolbar" aria-label={t("會議控制")}>
      <button type="button" aria-pressed={meeting.muted} aria-label={t(meeting.muted ? "取消靜音" : "麥克風靜音")} onClick={meeting.toggleMute}><I name="mic" size={15}/></button>
      <button type="button" className={meeting.cameraOn ? "is-on" : ""} aria-pressed={meeting.cameraOn} disabled={!meeting.cameraSupported || !meeting.cameraAllowed} aria-label={t(meeting.cameraOn ? "關閉鏡頭" : "開啟鏡頭")} onClick={meeting.cameraOn ? () => meeting.stopCamera() : meeting.startCamera}><I name="camera" size={15}/></button>
      <button type="button" onClick={onOpen}>{t("返回會議")}</button>
      <button type="button" className="danger" onClick={() => meeting.leave()}>{t("離開影音會議")}</button>
    </div>
  </aside>
);

const CollaborationWorkspace = ({ target, meta, onClose, onChanged }) => {
  const tenant = W2.tenant();
  const taskId = first(obj(target).id, collabTaskId(obj(target).raw), collabTaskId(target));
  const seedTask = M(() => {
    const source = obj(first(obj(obj(target).raw).task, obj(target).raw, target));
    return {
      ...source,
      id: first(source.id, source.task_id, taskId),
      title: optionalText(source.title, obj(target).title, t("未命名")),
      description: optionalText(source.description, obj(target).description),
      visibility: key(first(source.visibility, obj(target).visibility, "private")),
    };
  }, [target, taskId]);
  const [detail, setDetail] = S(null);
  const [notOpened, setNotOpened] = S(false);
  const [loading, setLoading] = S(true);
  const [busy, setBusy] = S(false);
  const [error, setError] = S("");
  const [tab, setTab] = S("overview");
  const [relationOverride, setRelationOverride] = S(() => key(first(obj(target).relation, obj(obj(target).raw).relation)));
  const [accessRestricted, setAccessRestricted] = S(false);
  const mounted = R(true);
  const busyGuard = R(false);
  const requestSequence = R(0);
  const lastMessageIdRef = R(0);
  const realtimeWorkspaceSeen = R(0);
  E(() => () => {
    mounted.current = false;
    requestSequence.current += 1;
  }, []);
  const load = C(async ({ quiet = false, force = false } = {}) => {
    if (taskId == null) {
      setError(t("協作資料暫時無法載入"));
      setLoading(false);
      return;
    }
    const request = ++requestSequence.current;
    if (!quiet) setLoading(true);
    try {
      const data = await collabJson(`/api/tasks/${encodeURIComponent(taskId)}/collaboration`);
      if (!mounted.current || request !== requestSequence.current || tenant !== W2.tenant()) return;
      const hasSpace = Object.keys(collabWorkspace(data)).length > 0 && collabWorkspace(data).task_id != null;
      const refreshedState = collabStatus(data);
      const refreshedRelation = ["active", "member", "owner"].includes(refreshedState)
        ? "member" : key(collabData(data).relation);
      setDetail(data);
      setAccessRestricted(false);
      if (refreshedRelation) setRelationOverride(refreshedRelation);
      setNotOpened(!hasSpace);
      setError("");
    } catch (exception) {
      if (!mounted.current || request !== requestSequence.current || tenant !== W2.tenant()) return;
      if (exception.status === 404) {
        setDetail({ task: seedTask, capabilities: {} });
        setNotOpened(true);
        setAccessRestricted(false);
        setRelationOverride("");
        setTab("overview");
        setError("");
      } else if (exception.status === 403) {
        const restrictedDetail = {
          task: {
            id: taskId,
            title: t("協作工作間"),
            description: "",
            visibility: "private",
          },
          capabilities: {},
        };
        setDetail(restrictedDetail);
        setNotOpened(false);
        setAccessRestricted(true);
        setRelationOverride("");
        setTab("overview");
        setError(t("您已無權存取此協作工作間"));
        let fallback = null;
        try {
          const params = new URLSearchParams({ limit: "50", q: seedTask.title });
          const discovered = await collabJson("/api/task-collaboration/discover?" + params.toString());
          if (!mounted.current || request !== requestSequence.current || tenant !== W2.tenant()) return;
          fallback = collabCollection(discovered).find(item => String(collabTaskId(item)) === String(taskId)) || null;
        } catch (ignored) {}
        if (!mounted.current || request !== requestSequence.current || tenant !== W2.tenant()) return;
        if (fallback) {
          setDetail(fallback);
          setNotOpened(false);
          setAccessRestricted(false);
          setRelationOverride(key(first(collabData(fallback).relation, fallback.relation, "available")));
          setError("");
        }
      } else {
        setError(exception.message || t("協作資料暫時無法載入"));
      }
    } finally {
      if (mounted.current && request === requestSequence.current) setLoading(false);
    }
  }, [taskId, tenant, seedTask]);
  E(() => { load(); }, [load]);
  E(() => {
    const closeOnEscape = event => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  const mutate = C(async (path, body) => {
    if (busyGuard.current || busy || taskId == null) return false;
    busyGuard.current = true;
    setBusy(true);
    setError("");
    try {
      const resultData = await collabPost(path, body);
      if (!mounted.current || tenant !== W2.tenant()) return false;
      const result = key(first(collabData(resultData).result, collabData(resultData).status));
      let nextRelation = key(collabData(resultData).relation);
      if (!nextRelation && (result.includes("request") || result === "pending")) nextRelation = "requested";
      else if (!nextRelation && ["joined", "accepted", "member", "active"].includes(result)) nextRelation = "member";
      else if (!nextRelation && ["left", "declined", "available"].includes(result)) nextRelation = "available";
      if (nextRelation) {
        setRelationOverride(nextRelation);
        setDetail(current => ({ ...collabData(current), relation: nextRelation }));
      }
      await load({ quiet: true, force: true });
      if (onChanged) onChanged();
      return true;
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant()) setError(exception.message || t("協作操作失敗"));
      return false;
    } finally {
      busyGuard.current = false;
      if (mounted.current) setBusy(false);
    }
  }, [busy, taskId, tenant, load, onChanged]);
  const open = form => mutate(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/open`, form);
  const join = () => mutate(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/join`, { role: "contributor" });
  const leave = async () => {
    if (!window.confirm(t("確定離開此協作？"))) return;
    if (busy || taskId == null) return;
    setBusy(true);
    setError("");
    try {
      await meeting.leave({ keepalive: true });
      await collabPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/leave`, {});
      if (!mounted.current || tenant !== W2.tenant()) return;
      if (onChanged) onChanged();
      onClose();
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant()) setError(exception.message || t("協作操作失敗"));
    } finally {
      if (mounted.current) setBusy(false);
    }
  };
  const invite = (userId, role) => mutate(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/invite`, { user_id: userId, role });
  const decide = (requestId, decision) => {
    if (requestId == null) return Promise.resolve(false);
    return mutate(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/requests/${encodeURIComponent(requestId)}/decision`, { decision });
  };
  const respond = async (invitationId, decision) => {
    const path = `/api/tasks/${encodeURIComponent(taskId)}/collaboration/invitations/${encodeURIComponent(invitationId)}/respond`;
    if (decision !== "decline") return mutate(path, { decision });
    if (busy) return false;
    setBusy(true);
    setError("");
    try {
      await collabPost(path, { decision });
      if (!mounted.current || tenant !== W2.tenant()) return false;
      if (onChanged) onChanged();
      onClose();
      return true;
    } catch (exception) {
      if (mounted.current && tenant === W2.tenant()) setError(exception.message || t("協作操作失敗"));
      return false;
    } finally {
      if (mounted.current) setBusy(false);
    }
  };
  const task = { ...seedTask, ...collabTask(detail) };
  const space = collabWorkspace(detail);
  const capabilities = collabCapabilities(detail);
  const canRead = capabilities.can_read === true;
  const canUseDocument = capabilities.can_use_document !== false;
  const realtime = useCollaborationRealtime({ taskId, tenant, enabled: canRead });
  const rtcAvailable = capabilities.rtc_available === true;
  const canJoinMeeting = capabilities.can_join_meeting === true && rtcAvailable;
  const canShareScreen = capabilities.can_share_screen === true && rtcAvailable;
  const canUseCamera = capabilities.can_use_camera === true && rtcAvailable;
  const canManage = capabilities.can_manage === true;
  const canJoin = capabilities.can_join === true;
  const canRequest = capabilities.can_request === true;
  const canLeave = capabilities.can_leave === true;
  const canSend = capabilities.can_send === true;
  const canRespondInvitation = capabilities.can_respond_invitation === true;
  const canAcceptInvitation = capabilities.can_accept_invitation === true
    || (capabilities.can_accept_invitation == null && canRespondInvitation && capabilities.read_only !== true);
  const canDeclineInvitation = capabilities.can_decline_invitation === true
    || (capabilities.can_decline_invitation == null && canRespondInvitation);
  const ownerUserId = first(obj(space.owner).user_id);
  const canTransferOwnership = capabilities.can_transfer_ownership === true;
  const transferOwnership = C((newOwnerUserId, displayName) => {
    if (!canTransferOwnership || busy || newOwnerUserId == null || ownerUserId == null) {
      return Promise.resolve(false);
    }
    if (!window.confirm(t("確定將協作負責人移交給") + " " + displayName + "？")) {
      return Promise.resolve(false);
    }
    return mutate(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/owner/transfer`, {
      new_owner_user_id: newOwnerUserId,
      expected_owner_user_id: ownerUserId,
    });
  }, [canTransferOwnership, busy, ownerUserId, taskId, mutate]);
  const membership = collabViewer(detail);
  const viewerUserId = first(
    membership.user_id,
    membership.member_user_id,
    collabData(detail).viewer_user_id,
    obj(meta).current_user_id,
    obj(obj(meta).user).id
  );
  const meeting = useCollaborationMeeting({
    taskId,
    tenant,
    enabled: canJoinMeeting,
    canShare: canShareScreen,
    canUseCamera,
    viewerUserId,
    members: collabMembers(detail),
    clientId: realtime.clientId,
    subscribeRtc: realtime.subscribeRtc,
    setRtcSignalCursor: realtime.setRtcSignalCursor,
    confirmRtcSignalCursor: realtime.confirmRtcSignalCursor,
    realtimeState: realtime.transport,
  });
  const membershipState = collabStatus(detail);
  const membershipRelation = ["active", "member", "owner"].includes(membershipState) ? "member" : "";
  const relation = accessRestricted ? "" : key(first(
    membershipRelation,
    relationOverride,
    collabData(detail).relation,
    obj(target).relation,
    obj(obj(target).raw).relation
  ));
  const viewerInvitation = collabInvitations(detail).find(invitation => {
    const invitee = first(invitation.invitee_user_id, invitation.user_id, obj(invitation.invitee).id);
    return invitation.for_viewer === true || (viewerUserId != null && invitee != null && String(invitee) === String(viewerUserId));
  }) || (relation === "invited" ? collabInvitations(detail)[0] : null);
  const invitationId = viewerInvitation && first(viewerInvitation.id, viewerInvitation.invitation_id);
  const tabs = [
    ["overview", "概覽", "doc"],
    ...(canRead && canUseDocument ? [["document", "共編", "doc"]] : []),
    ...(canRead ? [["members", "成員", "user"]] : []),
    ...(canJoinMeeting ? [["meeting", "影音會議", "camera"]] : []),
    ...(canRead ? [["chat", "聊天", "bell"]] : []),
  ];
  E(() => {
    if (realtime.workspaceSignal <= realtimeWorkspaceSeen.current) return;
    realtimeWorkspaceSeen.current = realtime.workspaceSignal;
    load({ quiet: true, force: true });
  }, [realtime.workspaceSignal, load]);
  const workspaceReconcileDelay = realtime.transport === COLLAB_REALTIME_STATES.LIVE
    ? 30000
    : realtime.transport === COLLAB_REALTIME_STATES.FALLBACK ? 5000 : null;
  E(() => {
    if (!canRead || taskId == null) return undefined;
    const reconcile = () => {
      if (document.visibilityState === "visible") load({ quiet: true, force: true });
    };
    if (workspaceReconcileDelay != null) reconcile();
    const timer = workspaceReconcileDelay == null
      ? null
      : window.setInterval(reconcile, workspaceReconcileDelay);
    const onVisible = () => {
      if (document.visibilityState === "visible") load({ quiet: true, force: true });
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      if (timer != null) window.clearInterval(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [canRead, taskId, workspaceReconcileDelay, load]);
  E(() => {
    if ((["chat", "members"].includes(tab) && !canRead)
      || (tab === "document" && (!canRead || !canUseDocument))
      || (tab === "meeting" && !canJoinMeeting)) setTab("overview");
  }, [tab, canRead, canUseDocument, canJoinMeeting]);
  const onTabKeyDown = (event, index) => {
    let nextIndex = null;
    if (event.key === "ArrowRight") nextIndex = (index + 1) % tabs.length;
    else if (event.key === "ArrowLeft") nextIndex = (index - 1 + tabs.length) % tabs.length;
    else if (event.key === "Home") nextIndex = 0;
    else if (event.key === "End") nextIndex = tabs.length - 1;
    if (nextIndex == null) return;
    event.preventDefault();
    const nextId = tabs[nextIndex][0];
    setTab(nextId);
    window.requestAnimationFrame(() => {
      const nextTab = document.getElementById("task-collab-tab-" + taskId + "-" + nextId);
      if (nextTab) nextTab.focus();
    });
  };
  const overviewActions = !notOpened && <div className="task-collab-actions">
    {invitationId != null && relation === "invited" && canDeclineInvitation && <button type="button" disabled={busy} onClick={() => respond(invitationId, "decline")}>{t("婉拒邀請")}</button>}
    {invitationId != null && relation === "invited" && canAcceptInvitation && <button type="button" className="primary" disabled={busy} onClick={() => respond(invitationId, "accept")}>{t("接受邀請")}</button>}
    {relation === "requested" && <span className="task-collab-pending">{t("等待負責人審批")}</span>}
    {!invitationId && canJoin && <button type="button" className="primary" disabled={busy} onClick={join}>{t("加入協作")}</button>}
    {!invitationId && !canJoin && canRequest && <button type="button" className="primary" disabled={busy} onClick={join}>{t("申請加入")}</button>}
    {canLeave && <button type="button" className="danger" disabled={busy} onClick={leave}>{t("離開協作")}</button>}
  </div>;
  return <div className="task-collab-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="task-collab-workspace" role="dialog" aria-modal="true" aria-labelledby="task-collab-title">
      <header className="task-collab-workspace-head">
        <div><L red>COLLABORATION WORKSPACE</L><h2 id="task-collab-title">{task.title}</h2><div className="task-collab-workspace-meta"><p>{t("協作工作間")} · #{taskId}</p>{canRead && <span className={"task-collab-realtime is-" + realtime.transport} role="status" aria-live="polite" aria-atomic="true"><i aria-hidden="true"/>{collabRealtimeLabel(realtime.transport, realtime.onlineCount)}</span>}</div></div>
        <button type="button" onClick={onClose} aria-label={t("關閉")}><I name="x" size={17}/></button>
      </header>
      {loading && !detail ? <div className="task-loading"><span/><span/><span/><small>{t("同步中")}</small></div>
      : <><nav className="task-collab-tabs" role="tablist" aria-label={t("協作工作間")}>{tabs.map(([id, label, icon], index) => <button type="button" role="tab" id={"task-collab-tab-" + taskId + "-" + id} aria-controls={"task-collab-panel-" + taskId} aria-selected={tab === id} tabIndex={tab === id ? 0 : -1} className={tab === id ? "on" : ""} key={id} onClick={() => setTab(id)} onKeyDown={event => onTabKeyDown(event, index)}><I name={icon} size={14}/><span>{t(label)}</span>{id === "members" && realtime.transport === COLLAB_REALTIME_STATES.LIVE && <b className="task-collab-online-count">{realtime.onlineCount}</b>}</button>)}</nav>
        {error && !notOpened && <div className="task-inline-error" role="alert"><span>{error}</span><button type="button" onClick={() => load()}>{t("重新載入")}</button></div>}
        <div className={"task-collab-workspace-body" + (meeting.joined && tab !== "meeting" ? " has-meeting-mini" : "")} role="tabpanel" id={"task-collab-panel-" + taskId} aria-labelledby={"task-collab-tab-" + taskId + "-" + tab}>
          {notOpened ? <CollaborationOpenForm task={task} busy={busy} error={error} onSubmit={open}/>
          : tab === "overview" ? <div className="task-collab-overview">
            <section><L red>{t(collabScopeLabel(space.discoverability))}</L><h3>{task.title}</h3>{task.description && <p>{task.description}</p>}<div className="task-collab-facts"><span>{t(collabJoinLabel(space.join_policy))}</span><span>{number(first(space.member_count, collabMembers(detail).length))} {t("人參與")}</span>{task.due_at && <span>{t("截止")} · {collabTime(task.due_at)}</span>}</div></section>
            {overviewActions}
          </div>
          : tab === "document" ? <CollaborativeDocument key={String(tenant) + ":" + String(taskId) + ":" + String(viewerUserId)} taskId={taskId} task={task} role={first(membership.role, membership.member_role)} viewerUserId={viewerUserId} clientId={realtime.clientId} realtimeState={realtime.transport} documentSignal={realtime.documentSignal} documentSequence={realtime.documentSequence}/>
          : tab === "members" ? <CollaborationMembers detail={detail} meta={meta} busy={busy} onInvite={invite} onDecision={decide} onTransferOwnership={transferOwnership} realtimeState={realtime.transport} presence={realtime.presence}/>
          : tab === "meeting" ? <CollaborationMeeting meeting={meeting} canShare={canShareScreen}/>
          : <CollaborationChat key={String(taskId)} taskId={taskId} active={tab === "chat"} canSend={canSend} viewerUserId={viewerUserId} realtimeState={realtime.transport} presence={realtime.presence} members={collabMembers(detail)} messageSignal={realtime.messageSignal} onTyping={realtime.sendTyping} lastMessageIdRef={lastMessageIdRef}/>}
        </div>
      </>}
      {meeting.joined && <CollaborationMeetingAudioHost meeting={meeting}/>}
      {meeting.joined && tab !== "meeting" && <CollaborationMeetingMini meeting={meeting} onOpen={() => setTab("meeting")}/>}
    </section>
  </div>;
};

const categoriesFor = (mode, sourceRef, biu = false) => {
  if (biu) return mode === "event" ? ["meeting", "exam", "work"]
    : mode === "plan" ? ["work", "record"]
    : (String(sourceRef || "").startsWith("record:") ? ["record", "work", "other"] : ["work", "record", "other"]);
  return mode === "event" ? ["meeting", "travel", "exam", "personal", "work"]
    : mode === "plan" ? ["work", "personal"]
    : (String(sourceRef || "").startsWith("record:") ? ["record", "work", "other"] : ["work", "record", "other"]);
};
const initialForm = (mode, seed = {}, biu = false) => {
  const day = seed.startDate || seed.date || todayKey();
  const dueDay = seed.dueDate || day;
  const sourceRef = seed.source_ref || seed.sourceRef || "";
  const choices = categoriesFor(mode || "task", sourceRef, biu);
  const category = choices.includes(seed.category) ? seed.category : choices[0];
  return {
    mode: mode || "task", title: seed.title || seed.source_title || "", description: seed.description || "", priority: seed.priority || "normal", category,
    startDate: day, startTime: seed.startTime || "09:00", dueDate: dueDay, dueTime: seed.dueTime || (mode === "event" ? "10:00" : "17:00"), allDay: seed.allDay != null ? !!seed.allDay : mode === "plan",
    visibility: seed.visibility || "private", location: seed.location || "", assigneeId: seed.assigneeId || "", ownerOrgUnitId: seed.ownerOrgUnitId || "", planId: seed.planId || "", sourceRef, sourceTitle: seed.source_title || seed.sourceTitle || "",
  };
};
const taskFormSeed = task => ({
  title: task.title, description: task.description, priority: task.priority, category: task.category,
  startDate: inputDate(task.start || task.due) || todayKey(), startTime: inputTime(task.start || task.due),
  dueDate: inputDate(task.due || task.start) || todayKey(), dueTime: inputTime(task.due || task.start),
  allDay: task.allDay, visibility: task.visibility, location: task.location,
  assigneeId: task.assigneeId, ownerOrgUnitId: task.ownerOrgUnitId, planId: task.planId,
  sourceRef: task.sourceRef, sourceTitle: task.sourceTitle,
});
const TaskComposer = ({ mode: initialMode, seed, task = null, requestKey, meta, tasks, onClose, onCreated, onSaved, biu = false }) => {
  const editing = !!(task && task.id != null);
  const [form, setForm] = S(() => initialForm(initialMode, editing ? taskFormSeed(task) : seed, biu));
  const [busy, setBusy] = S(false);
  const [error, setError] = S("");
  const requestId = R(requestKey || clientRequestId());
  const capabilities = capabilitiesFromMeta(meta);
  const canManage = capabilities.can_manage === true;
  const canAssign = canManage || capabilities.can_assign === true;
  const users = usersFromMeta(meta);
  const orgUnits = orgUnitsFromMeta(meta);
  const plans = [];
  [...plansFromMeta(meta), ...tasks.filter(task => task.kind === "plan").map(task => ({ id: task.id, title: task.title }))].forEach(plan => {
    const id = first(plan.id, plan.plan_id);
    if (id != null && !plans.some(existing => String(first(existing.id, existing.plan_id)) === String(id))) plans.push(plan);
  });
  const update = (name, value) => setForm(current => ({ ...current, [name]: value }));
  const setMode = mode => setForm(current => {
    const choices = categoriesFor(mode, current.sourceRef, biu);
    return { ...current, mode, category: choices.includes(current.category) ? current.category : choices[0], planId: mode === "plan" ? "" : current.planId };
  });
  const submit = async event => {
    event.preventDefault(); setError("");
    if (!form.title.trim()) { setError(t("需要標題")); return; }
    const startsAt = toISO(form.startDate, form.startTime, form.allDay, false);
    const dueAt = toISO(form.dueDate, form.dueTime, form.allDay, true);
    if (startsAt && dueAt && new Date(dueAt) < new Date(startsAt)) { setError(t("截止時間不得早於開始時間")); return; }
    const source = sourceParts(form.sourceRef);
    const payload = {
      title: form.title.trim(), description: form.description.trim() || null,
      kind: form.mode, category: form.category, priority: form.priority, visibility: form.visibility,
      start_at: startsAt, end_at: ["event", "plan"].includes(form.mode) ? dueAt : null, due_at: form.mode === "task" ? dueAt : null,
      all_day: !!form.allDay, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC", location: form.location.trim() || null,
      owner_org_unit_id: idValue(form.ownerOrgUnitId), plan_id: form.mode === "plan" ? null : idValue(form.planId),
    };
    if (!editing || canAssign) payload.assignees = form.assigneeId ? [idValue(form.assigneeId)] : [];
    if (!editing) Object.assign(payload, { client_request_id: requestId.current, source_type: source.type, source_entity_id: source.id });
    else payload.expected_version = task.lockVersion;
    setBusy(true);
    const submitTenant = W2.tenant();
    try {
      const data = editing
        ? await W2.json(`/api/tasks/${encodeURIComponent(task.id)}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) })
        : await W2.post("/api/tasks", payload);
      if (submitTenant === W2.tenant()) {
        if (editing) await onSaved(taskFrom(data));
        else await onCreated(taskFrom(data));
      }
    }
    catch (exception) { setError(exception.message || t(editing ? "更新失敗" : "無法建立任務")); }
    finally { setBusy(false); }
  };
  return <div className="task-sheet-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="task-sheet" role="dialog" aria-modal="true" aria-labelledby="task-composer-title">
      <header><div><L red>{editing ? "EDIT ACTION" : "NEW ACTION"}</L><h2 id="task-composer-title">{editing ? t("編輯任務") : taskText(biu, form.mode === "event" ? "新增日程" : form.mode === "plan" ? "新增計劃" : "新增任務")}</h2></div><button type="button" onClick={onClose} aria-label={t("關閉")}><I name="x" size={16}/></button></header>
      <form onSubmit={submit}>
        <div className="task-kind-switch" role="tablist" aria-label={t("選擇類型")}>{[["task", "任務", "clipboard"], ["event", "日曆", "clock"], ["plan", "計劃", "layers"]].map(([id, label, icon]) => <button type="button" role="tab" aria-selected={form.mode === id} className={form.mode === id ? "on" : ""} key={id} onClick={() => setMode(id)}><I name={icon} size={14}/>{taskText(biu, label)}</button>)}</div>
        {form.sourceRef && <div className="task-linked-source"><I name="doc" size={13}/><div><L dim>{t("來源")}</L><strong>{form.sourceTitle || form.sourceRef}</strong></div></div>}
        <label className="task-field full"><L dim>{t(form.mode === "event" ? "日程名稱" : form.mode === "plan" ? "計劃名稱" : "任務標題")} *</L><input autoFocus maxLength="240" value={form.title} onChange={event => update("title", event.target.value)}/></label>
        <label className="task-field full"><L dim>{t("說明與交付標準")}</L><textarea maxLength="2000" value={form.description} onChange={event => update("description", event.target.value)}/></label>
        <label className="task-field"><L dim>{t("類別")}</L><select value={form.category} onChange={event => update("category", event.target.value)}>{categoriesFor(form.mode, form.sourceRef, biu).map(category => <option key={category} value={category}>{t(categoryLabel(category, biu))}</option>)}</select></label>
        <label className="task-field"><L dim>{t("可見範圍")}</L><select value={form.visibility} onChange={event => update("visibility", event.target.value)}><option value="private">{t("僅自己")}</option>{canAssign && <option value="team">{t("團隊")}</option>}{canManage && <option value="company">{t("全公司")}</option>}</select></label>
        {form.mode === "event" && <label className="task-field full"><L dim>{t("地點")}</L><input maxLength="240" value={form.location} onChange={event => update("location", event.target.value)} placeholder={t("選填地點或會議連結")}/></label>}
        <label className="task-field"><L dim>{t("開始")}</L><input type="date" value={form.startDate} onChange={event => update("startDate", event.target.value)}/></label>
        {!form.allDay && <label className="task-field"><L dim>{t("時間")}</L><input type="time" value={form.startTime} onChange={event => update("startTime", event.target.value)}/></label>}
        <label className="task-field"><L dim>{t("截止")}</L><input type="date" value={form.dueDate} min={form.startDate} onChange={event => update("dueDate", event.target.value)}/></label>
        {!form.allDay && <label className="task-field"><L dim>{t("時間")}</L><input type="time" value={form.dueTime} onChange={event => update("dueTime", event.target.value)}/></label>}
        <label className="task-check full"><input type="checkbox" checked={form.allDay} onChange={event => update("allDay", event.target.checked)}/><span><I name="clock" size={13}/>{t("全天")}</span></label>
        <label className="task-field"><L dim>{t("優先級")}</L><select value={form.priority} onChange={event => update("priority", event.target.value)}><option value="urgent">{t("緊急")}</option><option value="high">{t("高")}</option><option value="normal">{t("普通")}</option><option value="low">{t("低")}</option></select></label>
        {canAssign && !!users.length && <label className="task-field"><L dim>{t("負責人")}</L><select value={form.assigneeId} onChange={event => update("assigneeId", event.target.value)}><option value="">{t("本人（預設）")}</option>{users.map((user, index) => <option key={first(user.id, user.user_id, index)} value={optionalText(user.id, user.user_id)}>{first(user.display_name, user.name, user.username, user.id)}</option>)}</select></label>}
        {canManage && !!orgUnits.length && <label className="task-field"><L dim>{t("負責部門")}</L><select value={form.ownerOrgUnitId} onChange={event => update("ownerOrgUnitId", event.target.value)}><option value="">{t("未指定")}</option>{orgUnits.map((unit, index) => <option key={first(unit.id, unit.org_unit_id, unit.unit_id, index)} value={optionalText(unit.id, unit.org_unit_id, unit.unit_id)}>{first(unit.name, unit.org_unit_name, unit.unit_name, unit.code, unit.id)}</option>)}</select></label>}
        {!!plans.length && form.mode !== "plan" && <label className="task-field full"><L dim>{t("所屬計劃")}</L><select value={form.planId} onChange={event => update("planId", event.target.value)}><option value="">{t("不加入計劃")}</option>{plans.map((plan, index) => <option key={first(plan.id, plan.plan_id, index)} value={optionalText(plan.id, plan.plan_id)}>{first(plan.title, plan.name, plan.plan_name, plan.id)}</option>)}</select></label>}
        {error && <div className="task-form-error full" role="alert">{error}</div>}
        <footer className="full"><B type="button" onClick={onClose}>{t("取消")}</B><B type="submit" kind="primary" icon={editing ? "check" : "plus"} disabled={busy}>{busy ? t(editing ? "儲存中…" : "建立中…") : editing ? t("儲存更改") : taskText(biu, form.mode === "event" ? "建立日程" : form.mode === "plan" ? "建立計劃" : "建立任務")}</B></footer>
      </form>
    </section>
  </div>;
};

const TaskDeleteDialog = ({ task, busy, error, onClose, onConfirm }) => <div className="task-delete-backdrop" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget && !busy) onClose(); }}>
  <section className="task-delete-dialog" role="alertdialog" aria-modal="true" aria-labelledby="task-delete-title" aria-describedby="task-delete-description">
    <L red>DELETE ACTION</L>
    <h2 id="task-delete-title">{t("確定刪除？")}</h2>
    <strong>{task.title}</strong>
    <p id="task-delete-description">{t("此操作無法撤銷。若任務已開啟協作，聊天、文件與成員記錄也會一併刪除。")}</p>
    {error && <div className="task-form-error" role="alert">{error}</div>}
    <footer><B type="button" disabled={busy} onClick={onClose}>{t("保留任務")}</B><B type="button" kind="danger" disabled={busy} onClick={onConfirm}>{busy ? t("刪除中…") : t("刪除任務")}</B></footer>
  </section>
</div>;

const VIEWS = [["today", "今天", "check"], ["inbox", "收件匣", "clipboard"], ["calendar", "日曆", "clock"], ["plans", "計劃", "layers"], ["insights", "透視", "chart"], ["collaboration", "協作廣場", "user"]];
const TaskManagementPanel = ({ embedded = false, initialView, boot, templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const query = queryFromHash();
  const viewOptions = embedded ? VIEWS.filter(item => ["inbox", "plans", "insights"].includes(item[0])) : VIEWS;
  const validViews = viewOptions.map(item => item[0]);
  const [view, setView] = S(() => validViews.includes(initialView) ? initialView : validViews.includes(query.get("view")) ? query.get("view") : embedded ? "inbox" : "today");
  const [tasks, setTasks] = S([]);
  const [meta, setMeta] = S({});
  const [loading, setLoading] = S(true);
  const [error, setError] = S("");
  const [metaWarning, setMetaWarning] = S("");
  const [busyId, setBusyId] = S(null);
  const [composer, setComposer] = S(null);
  const [deleteTarget, setDeleteTarget] = S(null);
  const [deleteError, setDeleteError] = S("");
  const [collabTarget, setCollabTarget] = S(null);
  const [collabVersion, setCollabVersion] = S(0);
  const [undoCompletion, setUndoCompletion] = S(null);
  const [syncedAt, setSyncedAt] = S(null);
  const mounted = R(true);
  const loadSequence = R(0);
  const tenant = W2.tenant();
  const canCreate = capabilitiesFromMeta(meta).can_create === true || (W2.hasPermission && W2.hasPermission("tasks.create"));
  E(() => () => { mounted.current = false; }, []);
  const load = C(async ({ quiet = false } = {}) => {
    const request = ++loadSequence.current;
    if (!quiet) setLoading(true);
    let nextMeta = {};
    try {
      nextMeta = obj(await W2.json("/api/tasks/meta"));
      if (mounted.current && request === loadSequence.current) { setMeta(nextMeta); setMetaWarning(""); }
    } catch (exception) {
      if (mounted.current && request === loadSequence.current) setMetaWarning(exception.message || "");
    }
    if (!mounted.current || request !== loadSequence.current) return;
    const capabilities = capabilitiesFromMeta(nextMeta);
    const scope = embedded && (capabilities.can_assign === true || capabilities.can_manage === true) ? "managed" : "mine";
    try {
      const data = await W2.json(`/api/tasks?scope=${scope}`);
      if (!mounted.current || request !== loadSequence.current) return;
      setTasks(tasksFrom(data).map(normalizeTask));
      if (Object.keys(obj(data.capabilities)).length) setMeta(current => ({ ...current, capabilities: { ...capabilitiesFromMeta(current), ...obj(data.capabilities) } }));
      setError(""); setSyncedAt(new Date());
    } catch (exception) {
      if (mounted.current && request === loadSequence.current) setError(exception.message || t("任務服務尚未啟用或暫時無法連線。"));
    } finally { if (mounted.current && request === loadSequence.current) setLoading(false); }
  }, [tenant, embedded]);
  E(() => {
    setTasks([]); setMeta({}); setError(""); setMetaWarning(""); setBusyId(null); setComposer(null); setDeleteTarget(null); setDeleteError(""); setCollabTarget(null); setUndoCompletion(null);
    load();
  }, [load]);
  E(() => {
    if (!undoCompletion) return undefined;
    const timer = window.setTimeout(() => setUndoCompletion(null), 8000);
    return () => window.clearTimeout(timer);
  }, [undoCompletion]);
  E(() => {
    const onVisible = () => { if (document.visibilityState === "visible") load({ quiet: true }); };
    const onPageShow = () => load({ quiet: true });
    const onDomainChange = () => load({ quiet: true });
    document.addEventListener("visibilitychange", onVisible); window.addEventListener("pageshow", onPageShow);
    window.addEventListener("w2-agent-complete", onDomainChange); window.addEventListener("w2-record-created", onDomainChange);
    return () => {
      document.removeEventListener("visibilitychange", onVisible); window.removeEventListener("pageshow", onPageShow);
      window.removeEventListener("w2-agent-complete", onDomainChange); window.removeEventListener("w2-record-created", onDomainChange);
    };
  }, [load]);
  E(() => {
    if (embedded || !canCreate) return undefined;
    const initialQuery = queryFromHash();
    const requested = initialQuery.get("create");
    if (["task", "event", "plan"].includes(requested)) setComposer({ mode: requested, requestKey: clientRequestId(), seed: { source_ref: initialQuery.get("source_ref") || "", source_title: initialQuery.get("source_title") || "", date: initialQuery.get("date") || "" } });
    const open = event => setComposer({ mode: obj(event.detail).mode || "task", requestKey: clientRequestId(), seed: obj(event.detail) });
    window.addEventListener("w2-open-task-composer", open);
    return () => window.removeEventListener("w2-open-task-composer", open);
  }, [embedded, canCreate]);
  const chooseView = next => {
    setView(next);
    if (!embedded && (location.hash || "").startsWith("#/tasks")) history.replaceState(null, "", `#/tasks?view=${encodeURIComponent(next)}`);
  };
  const openCreate = (mode = "task", seed = {}) => { if (canCreate) setComposer({ mode, seed, requestKey: clientRequestId() }); };
  const openEdit = task => { if (task && task.canUpdate) setComposer({ mode: task.kind, seed: {}, task, requestKey: clientRequestId() }); };
  const openDelete = task => { if (task && task.canDelete) { setDeleteError(""); setDeleteTarget(task); } };
  const openCollaboration = target => {
    if (target && first(target.id, collabTaskId(target.raw), collabTaskId(target)) != null) setCollabTarget(target);
  };
  const updateStatus = async (task, status) => {
    if (busyId != null) return;
    const actionTenant = W2.tenant();
    setBusyId(task.id); setError("");
    try {
      const apiStatus = ({ active: "in_progress", paused: "waiting" }[status] || status);
      const body = { status: apiStatus, expected_version: task.lockVersion };
      const data = await W2.post(`/api/tasks/${encodeURIComponent(task.id)}/status`, body);
      if (actionTenant !== W2.tenant()) return;
      const updatedRaw = taskFrom(data);
      const updated = Object.keys(updatedRaw).length ? normalizeTask(updatedRaw) : { ...task, status: canonicalStatus(apiStatus) };
      setTasks(current => current.map(item => String(item.id) === String(task.id) ? updated : item));
      if (apiStatus === "completed" && updated.canReopen) setUndoCompletion({ task: updated });
      else if (apiStatus === "in_progress") setUndoCompletion(null);
      setSyncedAt(new Date());
    } catch (exception) { setError(exception.message || t("狀態更新失敗")); }
    finally { setBusyId(null); }
  };
  const created = async raw => {
    setComposer(null);
    if (raw && Object.keys(raw).length) setTasks(current => uniqueTasks([normalizeTask(raw), ...current]));
    await load({ quiet: true });
  };
  const saved = async raw => {
    const updated = normalizeTask(raw);
    setComposer(null);
    setTasks(current => current.map(item => String(item.id) === String(updated.id) ? updated : item));
    setSyncedAt(new Date());
    await load({ quiet: true });
  };
  const removeTask = async () => {
    const target = deleteTarget;
    if (!target || busyId != null) return;
    const actionTenant = W2.tenant();
    setBusyId(target.id); setDeleteError("");
    try {
      await W2.json(`/api/tasks/${encodeURIComponent(target.id)}`, { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ expected_version: target.lockVersion, confirm: true }) });
      if (actionTenant !== W2.tenant()) return;
      setTasks(current => current.filter(item => String(item.id) !== String(target.id)));
      setDeleteTarget(null); setUndoCompletion(null); setSyncedAt(new Date());
      if (collabTarget && String(first(collabTarget.id, collabTaskId(collabTarget.raw))) === String(target.id)) setCollabTarget(null);
      await load({ quiet: true });
    } catch (exception) { setDeleteError(exception.message || t("刪除失敗")); }
    finally { setBusyId(null); }
  };
  const availableViews = viewOptions;
  const content = view === "collaboration"
    ? <CollaborationPlaza key={tenant} refreshSignal={collabVersion} onOpen={openCollaboration}/>
    : loading && !tasks.length
    ? <div className="task-loading" aria-live="polite"><span/><span/><span/><small>{t("同步中")}</small></div>
    : error && !tasks.length ? <div className="task-api-error" role="alert"><I name="alert" size={24}/><h2>{t("任務資料暫時無法載入")}</h2><p>{error}</p><B icon="refresh" onClick={() => load()}>{t("重新載入")}</B></div>
    : view === "today" ? <TodayView tasks={tasks} busyId={busyId} onStatus={updateStatus} onEdit={openEdit} onDelete={openDelete} onCollaboration={openCollaboration} onCreate={canCreate ? () => openCreate("task") : null} onViewAll={() => chooseView("inbox")} biu={biu}/>
    : view === "inbox" ? <InboxView tasks={tasks} busyId={busyId} onStatus={updateStatus} onEdit={openEdit} onDelete={openDelete} onCollaboration={openCollaboration} onCreate={canCreate ? () => openCreate("task") : null} biu={biu}/>
    : view === "calendar" ? <CalendarView tasks={tasks} busyId={busyId} onStatus={updateStatus} onEdit={openEdit} onDelete={openDelete} onCollaboration={openCollaboration} onCreate={canCreate ? openCreate : null} biu={biu}/>
    : view === "plans" ? <PlansView tasks={tasks} meta={meta} busyId={busyId} onStatus={updateStatus} onEdit={openEdit} onDelete={openDelete} onCollaboration={openCollaboration} onCreate={canCreate ? openCreate : null} biu={biu}/>
    : <InsightsView tasks={tasks} biu={biu}/>;
  return <section className={`task-workspace${embedded ? " embedded" : ""}`}>
    <header className="task-hero">
      <div className="task-hero-title"><L red>{embedded ? (biu ? "CASES × WORK" : "RECORDS × TASK") : (biu ? "00 · LEGAL ACADEMIC WORK" : "00 · PERSONAL OPERATIONS")}</L><h1>{biu ? (embedded ? taskText(true, "任務與計劃") : t("我的工作")) : (embedded ? t("任務與計劃") : "TASK.")}</h1><p>{taskText(biu, embedded ? "管理任務、日程與部門計劃，並保留與原始檔案的關聯。" : "所有與你相關的操作、安排與檔案跟進，都在同一條時間線。")}</p></div>
      <div className="task-hero-actions"><button type="button" className="task-sync" onClick={() => load()} disabled={loading} aria-label={t("重新載入")}><I name="refresh" size={14}/><span>{loading ? t("同步中") : t("剛剛同步")}</span></button>{canCreate && <button type="button" className="task-create" onClick={() => openCreate("task")}><I name="plus" size={17}/><span>{t("新增")}</span></button>}</div>
    </header>
    <nav className="task-view-nav" role="tablist" aria-label={taskText(biu, "個人行動中心")}>{availableViews.map(([id, label, icon], index) => <button type="button" role="tab" aria-selected={view === id} className={view === id ? "on" : ""} key={id} onClick={() => chooseView(id)}><span>{pad(index + 1)}</span><I name={icon} size={15}/><b>{taskText(biu, label)}</b></button>)}</nav>
    {(error && tasks.length > 0) && <div className="task-inline-error" role="alert"><span>{error}</span><button type="button" onClick={() => load()}>{t("重新載入")}</button></div>}
    {metaWarning && !error && <div className="task-meta-warning" title={metaWarning}>{t("資料權限由任務發起人、負責人、參與者與部門範圍共同決定。")}</div>}
    {undoCompletion && <div className="task-undo-completion" role="status" aria-live="polite"><span><i/>{t("任務已完成")}</span><button type="button" disabled={busyId != null} onClick={() => updateStatus(undoCompletion.task, "active")}>{t("撤銷")}</button></div>}
    {content}
    {!embedded && <nav className="task-mobile-nav" aria-label={taskText(biu, "個人行動中心")}>{VIEWS.map(([id, label, icon]) => <button type="button" className={view === id ? "on" : ""} key={id} onClick={() => chooseView(id)}><I name={icon} size={18}/><span>{taskText(biu, label)}</span></button>)}</nav>}
    {composer && <TaskComposer key={composer.requestKey} requestKey={composer.requestKey} mode={composer.mode} seed={composer.seed} task={composer.task || null} meta={meta} tasks={tasks} onClose={() => setComposer(null)} onCreated={created} onSaved={saved} biu={biu}/>} 
    {deleteTarget && <TaskDeleteDialog task={deleteTarget} busy={busyId === deleteTarget.id} error={deleteError} onClose={() => { setDeleteTarget(null); setDeleteError(""); }} onConfirm={removeTask}/>} 
    {collabTarget && <CollaborationWorkspace key={tenant + "-" + first(collabTarget.id, collabTaskId(collabTarget.raw))} target={collabTarget} meta={meta} onClose={() => setCollabTarget(null)} onChanged={() => setCollabVersion(current => current + 1)}/>}
  </section>;
};

const TaskPage = props => <div className="task-page"><TaskManagementPanel key={W2.tenant()} {...props}/></div>;
W2.TaskManagementPanel = TaskManagementPanel;
W2.PAGES.tasks = TaskPage;
})();
