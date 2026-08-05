/* WAREHOUSE 2.1 · 採購招標 — Swiss 版式,真後端 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "採購招標": "Procurement",
  "流程化採購協作 · 招標評審 · 全程留痕": "Process-driven procurement · tender review · fully audited",
  "待辦 {a} 條 · 進行中 {b} 條 · 頁面只讀,操作交秘書": "{a} to-dos · {b} running · read-only, actions via Secretary",
  "詢價": "Inquiry",
  "發起流程": "Start process",
  "問秘書": "Ask Secretary",
  "刷新": "Refresh",
  "我要發起一個採購或招標流程:請先建立或選擇真實 ERP 採購申請 ID,再追問流程類型;工作流必須綁定該採購主單,標題、金額、部門、預算、供應商和明細均以主單為準,不得建立孤立流程": "Start a procurement or tender process: first create or select a real ERP purchase request ID, then ask for the workflow type. The workflow must be bound to that purchase master record; title, amount, department, budget, supplier and lines all come from it. Never create an orphan workflow.",
  "幫我做一輪詢價:請追問物資名稱、數量和意向供應商,整理成詢價單並跟進報價": "Run a round of price inquiry — ask me for the item, quantity and candidate suppliers, draft the RFQ and chase the quotes",
  "看看採購招標現在的待辦、流程阻塞和權限缺口,按優先級給我可執行的下一步": "Review procurement to-dos, process blockages and permission gaps, and give me prioritised executable next steps",
  "我的待辦": "My to-dos",
  "全部待辦": "All to-dos",
  "受派人": "Assignee",
  "責任部門 / 職位": "Responsible department / position",
  "責任部門": "Responsible department",
  "責任職位": "Responsible position",
  "固定職位": "Fixed position",
  "兼容指派": "Legacy assignment",
  "未綁定部門與職位": "Department and position not bound",
  "節點責任配置": "Node responsibility settings",
  "配置節點責任": "Configure node responsibilities",
  "收起配置": "Close settings",
  "固定部門與職位（推薦）": "Fixed department and position (recommended)",
  "人員更換不影響流程；系統按當前在崗人員動態派單。": "Staff changes do not affect the workflow; tasks are routed to current position holders.",
  "全部部門": "All departments",
  "請選擇部門": "Select a department",
  "請選擇職位": "Select a position",
  "該部門暫無可選職位": "No positions are available in this department",
  "部門與職位必須成對選擇": "Department and position must be selected together",
  "保留舊指派規則（兼容）": "Keep legacy assignment rule (compatibility)",
  "保存節點責任": "Save node responsibilities",
  "保存中…": "Saving…",
  "節點責任已保存": "Node responsibilities saved",
  "節點責任載入失敗": "Failed to load node responsibilities",
  "節點責任保存失敗": "Failed to save node responsibilities",
  "待保存變更 {n} 個節點": "{n} changed node(s) to save",
  "沒有需要保存的變更": "No changes to save",
  "穩定綁定": "Stable binding",
  "管理層可跨部門處理": "Executives may act across departments",
  "動態責任規則": "Dynamic responsibility rule",
  "按實例需求部門的主管職位池": "Manager-position pool of the instance's requesting department",
  "按流程發起人動態處理": "Handled dynamically by the process initiator",
  "外部環節不綁定內部職位": "External steps are not bound to an internal position",
  "外部環節": "External party",
  "系統 / 網關節點不綁定人工職位": "System and gateway nodes are not bound to a human position",
  "未指派": "Unassigned",
  "你不可自審": "You cannot self-approve",
  "已上送管理層": "Escalated to management",
  "同級覆核": "Peer review",
  "審批路由受阻": "Approval routing blocked",
  "待配置上級／同級審批人": "Configure a higher-level or equivalent reviewer",
  "需要對賬補審": "Reconciliation review required",
  "任務已凍結，請先修復審批路由": "Task frozen — repair approval routing first",
  "發起人本人任職主管時先上送管理層；只有最高層級才轉同級覆核。": "If the initiator is the department manager, route upward first; only the highest level falls back to peer review.",
  "流程安全修復": "Safe workflow repair",
  "確定性異常證據 · 缺件引導 · 獨立 Passkey 共簽 · 禁止效果重放": "Deterministic evidence · guided inputs · independent Passkey co-signing · no effect replay",
  "目前沒有進行中的修復案件": "No active repair cases",
  "Guardian 仍會持續掃描；正常流程不需要人工干預。": "Guardian continues scanning; healthy workflows need no manual intervention.",
  "修復案件載入失敗": "Failed to load repair cases",
  "安全掃描": "Safety scan",
  "掃描中…": "Scanning…",
  "請先掃描此受阻流程": "Scan this blocked workflow first",
  "全公司目前沒有待處理任務": "No pending tasks company-wide",
  "我的待辦載入失敗": "Failed to load my to-dos",
  "全部待辦載入失敗": "Failed to load all to-dos",
  "待辦正在更新": "Refreshing to-dos",
  "正在重新確認最新狀態，更新完成前操作已暫停。": "Reconfirming the latest state. Actions are paused until the refresh completes.",
  "身份或公司已切換，請重新開啟此操作": "Your identity or company changed. Reopen this action.",
  "待辦資料尚未重新確認，請先刷新": "Task data has not been reconfirmed. Refresh first.",
  "進行中流程": "Running processes",
  "已閉環": "Closed",
  "流程模板": "Workflow templates",
  "條": "", "個": "", "步": "",
  "{n} 條已逾期": "{n} overdue",
  "無逾期": "none overdue",
  "含已駁回 / 已取消 {n} 條": "incl. {n} rejected / cancelled",
  "全流水可追溯": "full trail retained",
  "招標 · 採購 · 審批鏈": "tender · purchase · approval chains",
  "限時待辦優先 · 推進交秘書": "due tasks first · advance via Secretary",
  "把我的採購待辦按緊急程度排序,逐條給我處理建議,經我確認後推進": "Rank my procurement to-dos by urgency, advise on each, and advance them after my confirmation",
  "把全公司的採購待辦按緊急程度、受派人和流程排序,逐條給我處理建議,經我確認後推進": "Rank company-wide procurement to-dos by urgency, assignee and process, advise on each, and advance them after my confirmation",
  "全部交秘書梳理": "Triage all via Secretary",
  "填報": "Form", "審批": "Approval", "外部留痕": "External", "系統自動": "System",
  "簽章": "Sign-off", "條件分流": "Exclusive gateway", "並行分叉": "Parallel split", "並行匯聚": "Parallel join",
  "步 {n}": "step {n}",
  "限 {d}": "due {d}",
  "已逾期": "overdue",
  "推進": "Advance",
  "前往法務本人簽署": "Open Legal to sign in person",
  "合同簽署必須前往法務頁，上傳審查鎖定文件並完成本人確認": "Contract signing must be completed in Legal by uploading the reviewed file and verifying in person.",
  "推進待辦「{node}」(流程「{title}」,單號 {no}):請先核對必需材料和上下文,建議通過還是駁回,經我確認後執行": "Advance task \"{node}\" (process \"{title}\", no. {no}): check required artifacts and context first, recommend approve or reject, and execute after my confirmation",
  "沒有待你處理的任務": "Nothing waiting on you",
  "流程走到你這一步時,待辦會第一時間出現在這裡。": "When a process reaches your step, the task will surface here first.",
  "採購 / 招標流水": "Procurement / tender ledger",
  "我發起的流程 · 點行看流轉": "processes I started · click a row for the trail",
  "全部": "All", "進行中": "Running", "已駁回": "Rejected", "已取消": "Cancelled", "等待": "Waiting",
  "單號": "No.", "事由": "Title", "流程": "Workflow", "狀態": "Status",
  "業務全鏈": "Business trail", "查看全鏈": "View trail", "流程詳情": "Workflow detail",
  "當前節點": "Current node", "發起時間": "Started", "交給秘書": "Secretary",
  "查進度": "Progress",
  "查一下流程「{title}」(單號 {no})的當前進度、卡在哪個節點,需要催辦就幫我催辦": "Check progress of \"{title}\" (no. {no}), find where it is stuck, and nudge the current owner if needed",
  "還沒有採購 / 招標流水": "No procurement / tender records yet",
  "對秘書說「發起採購」,第一條流水就從這裡開始。": "Tell the Secretary to start a procurement — the first record begins here.",
  "發起第一個流程": "Start the first process",
  "當前篩選下沒有流程": "No processes under current filter",
  "發起於": "Started at", "完成於": "Completed at",
  "流程時間線": "Timeline",
  "暫無時間線記錄": "No timeline entries yet",
  "已留存證明": "Artifacts on file",
  "詳情載入中…": "Loading detail…",
  "催辦這個流程": "Nudge this process",
  "流程「{title}」(單號 {no})推進得怎麼樣?卡住的話幫我催辦當前處理人": "How is process \"{title}\" (no. {no}) going? If it is stuck, nudge the current owner for me",
  "讓秘書登記材料": "File artifacts via Secretary",
  "幫流程「{title}」(單號 {no})登記證明材料:請追問材料類型和憑證編號/說明後登記": "File supporting artifacts for process \"{title}\" (no. {no}): ask me for the artifact kind and reference/notes, then register them",
  "發起": "Started", "激活": "Activated", "通過": "Approved", "駁回": "Rejected", "轉交": "Reassigned", "完成": "Completed", "提交": "Submitted",
  "批復文件": "Approval document", "採購文件": "Procurement document", "採購計劃": "Tender plan",
  "代理委派": "Agent assignment", "招標公告": "Tender notice", "開標記錄": "Bid opening record",
  "評標報告": "Evaluation report", "中標結果": "Award result", "合同草稿": "Contract draft",
  "審批單": "Approval sheet", "簽章憑證": "Signature proof",
  "附件公證": "Notarised attachment",
  "上傳附件公證": "Upload notarised attachment",
  "附件上傳中…": "Uploading attachment…",
  "已公證 {n} 份": "{n} notarised file(s)",
  "尚無附件": "No attachments yet",
  "PDF、Word、Excel、圖片等，單檔上限 15MB；上傳後生成 SHA-256、版本鏈與伺服器簽章。": "PDF, Word, Excel, images and more, up to 15MB each. Uploads receive SHA-256, version chaining and a server signature.",
  "驗證公證": "Verify notarisation",
  "驗證中…": "Verifying…",
  "公證有效": "Notarisation valid",
  "公證驗證異常": "Notarisation verification failed",
  "流程拓撲": "Workflow topology",
  "{s} 階段 · {n} 節點 · 指派與流轉規則": "{s} stages · {n} nodes · assignment & routing rules",
  "秘書研判": "Secretary review",
  "結合流程「{wf}」的拓撲,檢查阻塞節點、權限缺口和外部留痕風險,給我下一步可執行動作": "Review the topology of \"{wf}\": check blocked nodes, permission gaps and external-trail risks, and give me executable next steps",
  "分析流程「{wf}」第 {step} 步「{node}」:處理要點、指派與權限規則、必需材料和下一步流轉": "Analyse step {step} \"{node}\" of workflow \"{wf}\": handling essentials, assignment & permission rules, required artifacts and next routing",
  "發起人": "Initiator", "指定用戶": "Assigned user", "指定角色": "Assigned role",
  "持有權限": "Permission holder", "需求部門負責人": "Requesting dept manager",
  "成本中心負責人": "Cost centre owner", "上下文字段": "Context field", "未配置": "Not configured",
  "未分組": "Ungrouped",
  "缺權限": "No permission",
  "會簽 {n}": "quorum {n}",
  "材料 {n}": "{n} artifacts",
  "SLA {n} 小時": "SLA {n}h",
  "待辦 {n}": "{n} to-dos",
  "流程完成": "process ends",
  "節點": "Node",
  "此流程暫無節點定義": "This workflow has no nodes defined",
  "尚無流程模板": "No workflow templates yet",
  "流程模板由系統預置或管理員配置。先問秘書採購流程怎麼走也可以。": "Workflow templates are preset by the system or configured by an admin. You can also just ask the Secretary how procurement runs.",
  "載入中…": "Loading…",
  "直接吩咐秘書": "Tell the Secretary",
  "2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.1 contract: pages are read-only; changes run through the Secretary with full audit.",
  "流程模板拓撲": "Template topology",
  "節點規則明細": "Node rules",
  "節點指令集": "Node command set",
  "已連結 {n} 項指令": "{n} linked command(s)",
  "選擇指令後，系統會帶入目前流程、實例、待辦與業務單據中已知的欄位；未知欄位留給你補寫。": "Choose a command to prefill known fields from the workflow, instance, task and business record; unknown fields remain for you to complete.",
  "填寫 · {label}": "Fill · {label}",
  "此節點尚未配置指令集": "No command set is configured for this node",
  "節點指令": "Node command",
  "拓撲載入中…": "Loading topology…",
  "去辦理": "Handle it now",
  "秘書研判此節點": "Secretary review of this node",
  "輪到你辦理": "Your turn",
  "輪到你 · 點擊交秘書辦理": "your turn · click to hand to the Secretary",
  "已完成": "Done",
  "未到 / 他人經辦": "not reached / others' step",
  "指派": "Assignment",
  "權限": "Permission",
  "通過後": "On approve",
  "駁回退回": "On reject",
  "材料": "Artifacts",
  "SLA / 會簽": "SLA / quorum",
  "默認": "default",
  "待處理": "Pending",
  "處理中": "In progress",
  "已通過": "Approved",
  "辦理時間": "Decided at",
  "意見": "Comment",
  "節點詳情": "Node detail",
  "分流": "Routed",
  "到達匯聚": "Arrived at join",
  "匯聚放行": "Join released",
  "請幫我辦理流程「{wf}」(單號 {no},實例 {id})第 {step} 步「{node}」:核對材料和上下文後給出通過/駁回建議,經我確認後執行": "Please handle step {step} \"{node}\" of process \"{wf}\" (no. {no}, instance {id}): verify materials and context, recommend approve or reject, and execute after my confirmation",
  "點節點看詳情;紅色節點輪到你,點擊直接交秘書辦理。": "Click a node for details; red nodes are yours — click to hand them to the Secretary.",
  "招標看板": "Tender board",
  "跨公司邀請制招標 · 密封投標 · 鋼印留痕": "Cross-company invited tenders · sealed bids · seal audit trail",
  "發起招標": "New tender",
  "我要發起一次邀請制招標:請先追問真實 ERP 採購申請 ID,核對其已綁定招標工作流且已到允許建立招標的節點,再追問需求、截標時間和已綁定供應商;只建立草稿,發布必須等工作流到發布節點後另行確認": "Start an invited tender: first ask for the real ERP purchase request ID and verify that it is bound to a tender workflow at the node that permits tender creation. Then ask for requirements, bid deadline and bound suppliers. Create only the draft; publishing requires a separate confirmation after the workflow reaches the publish node.",
  "把當前全部招標的狀態、投標和下一步該做什麼給我彙總": "Summarise every tender's status, bids and what to do next for me",
  "把本公司的跨公司合作關係列出來,有待響應的邀請幫我研判": "List our cross-company partnerships and assess any invitations awaiting my response",
  "已生效合作 {n} 家": "{n} active partner companies",
  "公告號": "Notice no.",
  "標題": "Title",
  "截標時間": "Bid deadline",
  "邀請數": "Invites",
  "投標數": "Bids",
  "鋼印": "Seal",
  "草稿": "Draft",
  "招標中": "Bidding open",
  "已截標": "Bidding closed",
  "已開標": "Opened",
  "已評標": "Evaluated",
  "已定標": "Awarded",
  "發布": "Publish",
  "開標": "Open bids",
  "評標": "Evaluate",
  "跟進": "Follow up",
  "發布招標公告「{no}」:請先核對其真實採購申請、關聯工作流及當前節點已允許發布,再核對邀請名單;經我確認後發布,不得越過工作流節點": "Publish tender notice \"{no}\": first verify its real purchase request, linked workflow and that the current node permits publishing, then verify the invite list. Publish after my confirmation; never skip the workflow node.",
  "招標公告「{no}」已到或臨近截標時間,幫我核對投標情況並開標": "Tender notice \"{no}\" is at or near its bid deadline — verify the bids received and open them for me",
  "招標公告「{no}」已開標,幫我比對各家報價與評分,給出評標和定標建議,經我確認後定標": "Tender notice \"{no}\" is opened — compare each bidder's quote and score, advise on evaluation and award, then finalise the award after my confirmation",
  "招標公告「{no}」已定標,請繼續推進關聯工作流的合同、審批與簽章節點;正式 PO 只能在整個採購工作流完成後由系統簽發,不得手工提前下單": "Tender notice \"{no}\" is awarded. Continue the linked workflow through contract, approval and signature nodes. The formal PO may only be issued by the system after the entire procurement workflow completes; never order early by hand.",
  "還沒有招標公告": "No tender notices yet",
  "先建立真實 ERP 採購申請並啟動綁定的招標工作流;流程到建立招標節點後,再由這裡建立草稿。": "First create a real ERP purchase request and start its bound tender workflow. Create the draft here only after the workflow reaches the tender-creation node.",
  "發起第一個招標": "Start the first tender",
  "需求說明": "Requirements",
  "預算上限": "Budget ceiling",
  "定標鋼印": "Award seal",
  "邀請名單": "Invite list",
  "暫無邀請": "No invites yet",
  "比價表": "Bid comparison",
  "密封投標": "Sealed bids",
  "暫無投標": "No bids yet",
  "密封中": "Sealed",
  "驗證通過": "Verified",
  "驗證異常": "Verification failed",
  "平均評分": "Avg. score",
  "交期": "Delivery",
  "已送達": "Sent",
  "已查看": "Viewed",
  "已婉拒": "Declined",
  "已投標": "Bid submitted",
  "中標": "Won",
  "未中標": "Lost",
  "已揭示": "Revealed",
  "已撤回": "Withdrawn",
  "外部協作 · 收到的招標邀請": "External · tender invitations received",
  "同行公司邀請你投標 · 報價經你確認後密封提交": "Peer companies invite your bid · quotes are sealed and submitted after your confirmation",
  "查看招標邀請「{ref}」的需求並幫我準備投標報價,報價需我確認後密封提交": "Review tender invitation \"{ref}\" and help me prepare the bid quote; seal and submit it only after my confirmation",
  "婉拒招標邀請「{ref}」": "Decline tender invitation \"{ref}\"",
  "準備投標": "Prepare bid",
  "婉拒": "Decline",
  "公告鋼印": "Notice seal",
  "截標 {d}": "closes {d}",
  "我的投標": "My bids",
  "密封投標記錄 · 開標前任何人不可見": "Sealed bid records · invisible to anyone before opening",
  "查一下我對招標「{title}」的投標狀態和下一步": "Check the status and next steps of my bid for tender \"{title}\"",
  "查狀態": "Status",
  "公開招標市場": "Public tender market",
  "全平台公開招標 · 報名經 AI 資質審核 · 通過後可密封投標": "Platform-wide public tenders · applications vetted by AI qualification review · sealed bidding once qualified",
  "公開招標市場現在有哪些適合本公司投標的機會?幫我篩一遍": "What public-tender opportunities suit our company right now? Screen them for me",
  "招標公司": "Buyer",
  "需求摘要": "Requirements digest",
  "我的狀態": "My status",
  "面議": "Negotiable",
  "報名": "Apply",
  "報名參與公開招標「{ref}」:請採集本公司資質報名,通過 AI 資質審核後即可投標": "Apply to public tender \"{ref}\": collect our company's qualifications and register; once the AI qualification review passes we can bid",
  "已通過·可投標": "Qualified · may bid",
  "投標": "Bid",
  "我要對已通過資質的公開招標「{ref}」密封投標,報價需我確認後提交": "Place a sealed bid on qualified public tender \"{ref}\"; submit the quote only after my confirmation",
  "資質待覆核": "Qualification under review",
  "資質未通過": "Qualification rejected",
  "暫無公開招標": "No public tenders",
  "有公開招標時會出現在這裡,可對秘書說『幫我找適合的公開招標』。": "Public tenders will appear here — you can also tell the Secretary to find suitable ones for you.",
  "資質": "Qualification",
  "資質通過": "Qualified",
  "待覆核": "Review pending",
  "未通過": "Not qualified",
  "高度相關": "Highly relevant",
  "部分相關": "Partly relevant",
  "關聯較弱": "Weakly related",
  "明顯無關": "Clearly unrelated",
  "主營 {c}": "main {c}",
  "物資 {n} 種": "{n} item kinds",
  "儲值 {v}": "stock value {v}",
  "通過覆核": "Approve review",
  "拒絕": "Reject",
  "覆核公開招標「{no}」中「{name}」的報名資質,通過就放行投標": "Re-review the application qualification of \"{name}\" in public tender \"{no}\"; if it passes, clear them to bid",
  "拒絕公開招標「{no}」中「{name}」的報名資質,並說明理由": "Reject the application qualification of \"{name}\" in public tender \"{no}\" and state the reasons",
  "我要發起一次招標:請先追問真實 ERP 採購申請 ID 和綁定的招標工作流,核對當前節點允許建立招標;再追問邀請制或公開招標、需求與截標時間,只建立草稿,不得同一步發布": "Start a tender: first ask for the real ERP purchase request ID and its bound tender workflow, and verify that the current node permits tender creation. Then ask whether it is invited or public, plus requirements and deadline. Create only the draft; do not publish in the same step.",
  "共 {n} 版": "{n} versions",
  "鋼印 {seal}": "seal {seal}",
  "上傳材料": "Upload material",
  "重新上傳更新": "Re-upload to update",
  "上傳中…": "Uploading…",
  "無權上傳": "Not authorised to upload",
  "上傳失敗:超過 15MB 上限": "Upload failed: exceeds the 15MB limit",
  "上傳失敗": "Upload failed",
  "下載失敗": "Download failed",
  "材料上傳即上鋼印(SHA-256 封存),可下載、可重新上傳更新;齊全後方可推進節點。": "Uploading a material seals it (SHA-256 archive); it can be downloaded or re-uploaded to update; a node can only advance once its materials are complete.",
  "節點材料": "Node materials", "材料齊全": "Materials complete", "缺 {n} 項材料": "{n} material(s) missing",
  "已上傳,可重新上傳更新": "Uploaded — click to replace", "上傳該材料": "Upload this material",
  "無權上傳": "No upload permission", "上傳失敗:超過 15MB 上限": "Upload failed: exceeds 15MB", "上傳失敗": "Upload failed", "下載失敗": "Download failed",
  "通過": "Approve", "駁回": "Reject", "處理中…": "Working…", "確認駁回": "Confirm reject", "取消": "Cancel",
  "交秘書研判": "Ask Secretary to assess",
  "駁回理由(選填,退回發起人時一併帶上)": "Reject reason (optional, sent back to the initiator)",
  "無審批權限或未達要求": "No approval permission or requirements unmet",
  "必需材料未齊全,無法通過": "Required materials incomplete — cannot approve", "操作失敗": "Action failed",
  "當前在崗": "Current position holders", "該職位暫無在崗人員": "No active holder in this position",
  "需要 Passkey 蓋章": "Passkey seal required", "正在取得安全挑戰…": "Requesting a secure challenge…",
  "切換至手機 Passkey QR": "Switch to phone passkey QR", "取消驗證": "Cancel verification",
  "尚未設定 Passkey，請先完成安全設定。剛才的決策沒有執行。": "Set up a passkey first. The decision was not executed.",
  "Passkey 已新增，請重新核對內容，再次點擊通過或確認駁回完成蓋章。": "Passkey added. Review the task, then click approve or confirm reject again to seal the decision.",
});
const { useState: _s, useEffect: _e, useMemo: _mm, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num, HBar, RepairPlanCard } = W2;
const ask = (p) => W2.openSecretary(p);

const arr = (x) => (Array.isArray(x) ? x : []);
const contextPathValue = (source, path) => {
  if (!source || !path) return undefined;
  let value = source;
  for (const part of String(path).split(".")) {
    if (value == null || (typeof value !== "object" && !Array.isArray(value))) return undefined;
    value = value[part];
  }
  return value;
};
const commandArgumentsFor = (action, context) => {
  const output = {
    ...((action && action.arguments && typeof action.arguments === "object") ? action.arguments : {}),
  };
  Object.entries((action && action.bindings && typeof action.bindings === "object") ? action.bindings : {}).forEach(([name, paths]) => {
    for (const path of arr(paths).length ? paths : [paths]) {
      const value = contextPathValue(context, path);
      if (value !== undefined && value !== null && value !== "") {
        output[name] = value;
        break;
      }
    }
  });
  return output;
};
const openNodeCommand = (node, action, commandContext) => {
  if (!action || !action.tool_name) return;
  const base = typeof commandContext === "function" ? commandContext(node) : commandContext;
  const context = {
    ...((base && typeof base === "object") ? base : {}),
    node,
  };
  W2.openBusinessAction({
    tool_name: action.tool_name,
    arguments: commandArgumentsFor(action, context),
    query: action.tool_name,
    filter: "authorized",
  });
};
const taskPasskeyActions = task => arr(task && (task.passkeyRequiredActions || task.passkey_required_actions)).map(String);
const taskRequiresPasskey = (task, action) => taskPasskeyActions(task).includes(String(action));
const taskAssignmentOccupants = task => arr(task && (task.assignmentOccupants || task.assignment_occupants))
  .map(person => ({
    userId: person && (person.userId != null ? person.userId : person.user_id),
    displayName: person && (person.displayName || person.display_name || ""),
    username: person && person.username || "",
  }))
  .filter(person => person.userId != null || person.displayName || person.username);
const taskOccupantsLabel = task => taskAssignmentOccupants(task).map(person => {
  const name = person.displayName || person.username || (person.userId != null ? "#" + person.userId : "—");
  return person.displayName && person.username ? name + " @" + person.username : name;
}).join("、");
const errorCode = error => String(error && ((error.data && error.data.code) || error.code) || "");
const procurementActorKey = actor => String(actor && (
  actor.gid || actor.global_user_id || actor.id || actor.username
) || "user");
const workflowEntityRef = (item) => {
  const supplied = item && W2.parseEntityRef && W2.parseEntityRef(item.entity_ref);
  if (supplied && supplied.type === "wf_instance") return supplied.entity_ref;
  const id = Number(item && item.id);
  return Number.isInteger(id) && id > 0 ? W2.entityRef("wf_instance", id) : "";
};
const workflowBusinessRef = (item) => {
  const direct = [item && item.erp_entity_ref, item && item.source_entity_ref]
    .map(value => W2.parseEntityRef && W2.parseEntityRef(value))
    .find(value => value && value.type === "erp_purchase_request");
  if (direct) return direct.entity_ref;
  const linked = arr(item && item.relations).map(relation => W2.parseEntityRef && W2.parseEntityRef(relation && relation.entity_ref))
    .find(value => value && value.type === "erp_purchase_request");
  return linked ? linked.entity_ref : workflowEntityRef(item);
};
const wfDate = (v) => (v ? String(v).replace("T", " ").slice(0, 16) : "—");
const isOverdue = (v) => {
  if (!v) return false;
  const d = new Date(String(v).replace(" ", "T"));
  return Number.isFinite(d.getTime()) && d.getTime() < Date.now();
};

const KIND = { form: "填報", approval: "審批", external_placeholder: "外部留痕", system_auto: "系統自動", signoff: "簽章", gateway_exclusive: "條件分流", gateway_parallel: "並行分叉", gateway_join: "並行匯聚" };
const KIND_TONE = { approval: "plain", form: "plain", external_placeholder: "warn", system_auto: "plain", signoff: "plain", gateway_exclusive: "plain", gateway_parallel: "plain", gateway_join: "plain" };
const ASSIGN = { initiator: "發起人", user: "指定用戶", role: "指定角色", permission: "持有權限", dept_manager: "需求部門負責人", cost_center_owner: "成本中心負責人", from_context: "上下文字段", external_party: "外部環節" };
const ACT = { start: "發起", activate: "激活", approve: "通過", reject: "駁回", reassign: "轉交", complete: "完成", submit: "提交", gateway: "分流", fork: "並行分叉", arrive: "到達匯聚", join_fire: "匯聚放行" };
const ISTAT = { running: ["plain", "進行中", true], completed: ["ok", "已閉環", true], rejected: ["bad", "已駁回", true], cancelled: ["plain", "已取消", false], waiting: ["warn", "等待", true] };
const ARTS = { batch_doc: "批復文件", procurement_doc: "採購文件", tender_plan: "採購計劃", agent_assignment: "代理委派", tender_notice: "招標公告", bid_opening_record: "開標記錄", eval_report: "評標報告", award_result: "中標結果", contract_draft: "合同草稿", approval_sheet: "審批單", signature_proof: "簽章憑證", node_attachment: "附件公證" };
const kindLabel = (k) => t(KIND[k] || k || "節點");
const artLabel = (k) => t(ARTS[k] || k || "—");
const fsize = (n) => (n == null ? "—" : n < 1024 ? n + "B" : n < 1048576 ? (n / 1024).toFixed(1) + "KB" : (n / 1048576).toFixed(1) + "MB");
const artHasFile = (a) => !!a && (num(a.has_file) === 1 || a.has_file === true || a.has_file === "1");
const responsibilityText = (n) => {
  if (!n) return "";
  const department = n.assignee_department_name || n.assignee_department_code || "";
  const rawPosition = n.assignee_position_name || n.assignee_position_code || "";
  const position = String(rawPosition).startsWith("__WF_") ? "" : rawPosition;
  return [department, position].filter(Boolean).join(" · ");
};
const fixedPositionApplicable = (n) => {
  if (!n) return false;
  /* 後端/SSOT 是唯一判斷來源；既有固定 code 永遠優先，external_placeholder 也可能是內部代表職位。 */
  if (n.assignee_department_code || n.assignee_position_code) return true;
  if (typeof n.position_binding_applicable === "boolean") return n.position_binding_applicable;
  const mode = n.position_binding_mode || n.assignee_binding_mode || "";
  if (["fixed", "fixed_position", "position_pool"].indexOf(mode) >= 0) return true;
  if (["dynamic", "initiator", "context_department_manager", "external_party", "gateway", "system", "none"].indexOf(mode) >= 0) return false;
  if (["gateway_exclusive", "gateway_parallel", "gateway_join", "system_auto", "external_placeholder"].indexOf(n.node_kind) >= 0) return false;
  return ["initiator", "dept_manager", "cost_center_owner", "from_context", "external_party"].indexOf(n.assign_rule) < 0;
};
const dynamicResponsibilityText = (n) => {
  if (!n) return "";
  const mode = n.position_binding_mode || n.assignee_binding_mode || "";
  if (mode === "fixed_position") return "";
  if (mode === "gateway" || ["gateway_exclusive", "gateway_parallel", "gateway_join", "system_auto"].indexOf(n.node_kind) >= 0) return t("系統 / 網關節點不綁定人工職位");
  if (mode === "external_party" || n.node_kind === "external_placeholder" || n.assign_rule === "external_party") return t("外部環節不綁定內部職位");
  if (mode === "context_department_manager" || n.assign_rule === "dept_manager") return t("發起人本人任職主管時先上送管理層；只有最高層級才轉同級覆核。");
  if (mode === "initiator" || n.assign_rule === "initiator") return t("按流程發起人動態處理");
  if (["cost_center_owner", "from_context"].indexOf(n.assign_rule) >= 0) return legacyAssignText(n);
  return "";
};
const legacyAssignText = (n) => {
  const label = t(ASSIGN[n.assign_rule] || n.assign_rule || "未配置");
  return n.assign_value ? label + " · " + n.assign_value : label;
};
const assignText = (n) => responsibilityText(n) || dynamicResponsibilityText(n) || legacyAssignText(n);
const NODE_CONFIG_WRITE_FIELDS = [
  "assignee_department_code", "assignee_position_code", "assign_rule", "assign_value",
  "required_permission", "quorum", "sla_hours",
];
const nodeConfigFieldValue = (node, field) => {
  const value = node && node[field];
  if (field === "quorum") return String(value === null || value === undefined || value === "" ? 1 : Number(value));
  if (field === "sla_hours") return value === null || value === undefined || value === "" ? "" : String(Number(value));
  return value === null || value === undefined ? "" : String(value);
};
const nodeConfigChanged = (node, baseline) => !baseline || NODE_CONFIG_WRITE_FIELDS.some(
  (field) => nodeConfigFieldValue(node, field) !== nodeConfigFieldValue(baseline, field)
);
const nodeConfigPayload = (node, baseline) => {
  const payload = {
    node_key: node.node_key,
    assign_rule: node.assign_rule,
    assign_value: node.assign_value || null,
    required_permission: node.required_permission || null,
    quorum: node.quorum || 1,
    sla_hours: node.sla_hours || null,
  };
  const bindingChanged = !baseline
    || nodeConfigFieldValue(node, "assignee_department_code") !== nodeConfigFieldValue(baseline, "assignee_department_code")
    || nodeConfigFieldValue(node, "assignee_position_code") !== nodeConfigFieldValue(baseline, "assignee_position_code");
  if (bindingChanged) {
    payload.assignee_department_code = node.assignee_department_code || null;
    payload.assignee_position_code = node.assignee_position_code || null;
  }
  return payload;
};
const statTag = (s) => {
  const [tone, label, dot] = ISTAT[s] || ISTAT.running;
  return <T tone={tone} dot={dot && s === "running"}>{t(label)}</T>;
};
const TSTAT = { pending: "待處理", in_progress: "處理中", approved: "已通過", rejected: "已駁回", cancelled: "已取消" };

/* ── B2B 跨公司招標(邀請制密封投標)── */
const cny = (v) => (v == null || v === "" || !Number.isFinite(Number(v))) ? "—" : "¥" + Number(v).toLocaleString("zh-CN", { maximumFractionDigits: 2 });
const shortHash = (h) => (h ? String(h).slice(0, 16) : "—");
const NSTAT = { draft: ["plain", "草稿", false], published: ["warn", "招標中", true], bidding_closed: ["warn", "已截標", false], opened: ["ok", "已開標", false], evaluated: ["ok", "已評標", false], awarded: ["inv", "已定標", false], cancelled: ["plain", "已取消", false] };
const nstatTag = (s) => { const [tone, label, dot] = NSTAT[s] || ["plain", s || "—", false]; return <T tone={tone} dot={dot}>{t(label)}</T>; };
const IVSTAT = { sent: ["plain", "已送達"], viewed: ["plain", "已查看"], declined: ["plain", "已婉拒"], bid_submitted: ["ok", "已投標"] };
const ivTag = (s) => { const [tone, label] = IVSTAT[s] || ["plain", s || "—"]; return <T tone={tone}>{t(label)}</T>; };
const BSTAT = { sealed: ["plain", "密封中"], revealed: ["warn", "已揭示"], won: ["inv", "中標"], lost: ["plain", "未中標"], withdrawn: ["plain", "已撤回"] };
/* 公告按狀態給秘書的下一步:[icon, 按鈕, 指令] */
const noticeAsk = (n) => {
  const no = n.notice_no || (n.id != null ? String(n.id) : "—");
  if (n.status === "draft") return ["check", "發布", t("發布招標公告「{no}」:請先核對其真實採購申請、關聯工作流及當前節點已允許發布,再核對邀請名單;經我確認後發布,不得越過工作流節點", { no })];
  if (n.status === "published" || n.status === "bidding_closed") return ["clock", "開標", t("招標公告「{no}」已到或臨近截標時間,幫我核對投標情況並開標", { no })];
  if (n.status === "opened" || n.status === "evaluated") return ["sparkle", "評標", t("招標公告「{no}」已開標,幫我比對各家報價與評分,給出評標和定標建議,經我確認後定標", { no })];
  if (n.status === "awarded") return ["clipboard", "跟進", t("招標公告「{no}」已定標,請繼續推進關聯工作流的合同、審批與簽章節點;正式 PO 只能在整個採購工作流完成後由系統簽發,不得手工提前下單", { no })];
  return null;
};

/* ── P5 公開招標市場(公開報名 + AI 資質審核)── */
const nearDue = (v) => {
  if (!v) return false;
  const d = new Date(String(v).replace(" ", "T"));
  return Number.isFinite(d.getTime()) && d.getTime() - Date.now() < 48 * 3600 * 1000;
};
const QSTAT = { qualified: ["ok", "資質通過"], pending_review: ["warn", "待覆核"], rejected: ["bad", "未通過"] };
const RELV = { high: "高度相關", medium: "部分相關", low: "關聯較弱", none: "明顯無關" };
const parseQual = (iv) => {
  if (!iv || iv.qualification_json == null) return null;
  try {
    const q = typeof iv.qualification_json === "string" ? JSON.parse(iv.qualification_json) : iv.qualification_json;
    return q && typeof q === "object" ? q : null;
  } catch (e) { return null; }
};

/* ══ 工作流拓撲(純 SVG,分層佈局:列=step,同列縱排)══ */
const isGw = (k) => k === "gateway_exclusive" || k === "gateway_parallel" || k === "gateway_join";
const GW_OPS = { lt: "<", lte: "≤", gt: ">", gte: "≥", eq: "=", ne: "≠" };
const condText = (c) => (c ? [c.field, GW_OPS[c.op] || c.op, c.value].filter((x) => x !== undefined && x !== null && x !== "").join(" ") : "");
const trunc = (s, n) => { s = String(s || ""); return s.length > n ? s.slice(0, n - 1) + "…" : s; };
/* 節點出邊:網關 branches_json(exclusive:{branches:[{target,cond}]} / parallel:{targets:[]} / join:{sources,target})+ on_approve_next / on_reject_target */
const nodeOuts = (n) => {
  const o = []; const br = (n && n.branches) || {};
  if (n.node_kind === "gateway_exclusive") arr(br.branches).forEach((b) => { if (b && b.target) o.push({ to: b.target, kind: "flow", lbl: b.cond ? condText(b.cond) : t("默認") }); });
  else if (n.node_kind === "gateway_parallel") arr(br.targets).forEach((k) => { if (k) o.push({ to: k, kind: "flow" }); });
  else if (n.node_kind === "gateway_join" && br.target) o.push({ to: br.target, kind: "flow" });
  if (n.on_approve_next) o.push({ to: n.on_approve_next, kind: "flow" });
  if (n.on_reject_target) o.push({ to: n.on_reject_target, kind: "reject" });
  return o;
};
const buildTopo = (nodes, compact) => {
  const NW = compact ? 136 : 184, NH = compact ? 50 : 62;
  const CG = compact ? 30 : 46, RG = compact ? 42 : 50, PAD = compact ? 10 : 14;
  const half = compact ? 16 : 20;
  const sorted = arr(nodes).filter((n) => n && n.node_key)
    .sort((a, b) => (num(a.step_no) - num(b.step_no)) || String(a.node_key).localeCompare(String(b.node_key)));
  const steps = [];
  sorted.forEach((n) => { const s = num(n.step_no); if (steps.indexOf(s) < 0) steps.push(s); });
  const pos = {}; let maxRows = 1;
  steps.forEach((s, ci) => {
    const col = sorted.filter((n) => num(n.step_no) === s);
    maxRows = Math.max(maxRows, col.length);
    col.forEach((n, ri) => {
      const x = PAD + ci * (NW + CG), y = PAD + ri * (NH + RG);
      const gw = isGw(n.node_kind), cx = x + NW / 2, cy = y + NH / 2;
      pos[n.node_key] = gw
        ? { x, y, ci, gw, half, cx, cy, lx: cx - half, rx: cx + half, by: cy + half }
        : { x, y, ci, gw, cx, cy, lx: x, rx: x + NW, by: y + NH };
    });
  });
  const edges = []; const seenE = {}; let backs = 0;
  sorted.forEach((n) => {
    const f = pos[n.node_key]; if (!f) return;
    nodeOuts(n).forEach((e) => {
      const tp = pos[e.to]; const id = n.node_key + ">" + e.to + ":" + e.kind;
      if (!tp || e.to === n.node_key || seenE[id]) return;
      seenE[id] = 1;
      const back = tp.ci <= f.ci;
      if (back) backs += 1;
      edges.push({ id, f, tp, kind: e.kind, lbl: back ? null : e.lbl, back });
    });
  });
  const hasGw = sorted.some((n) => isGw(n.node_kind));
  const rowsBottom = PAD + maxRows * NH + (maxRows - 1) * RG + (hasGw ? (compact ? 12 : 15) : 0);
  let lane = 0;
  edges.forEach((e) => {
    const f = e.f, tp = e.tp;
    if (!e.back) {
      if (Math.abs(f.cy - tp.cy) < 1) e.d = `M ${f.rx} ${f.cy} L ${tp.lx} ${tp.cy}`;
      else { const mid = Math.round((f.rx + tp.lx) / 2); e.d = `M ${f.rx} ${f.cy} L ${mid} ${f.cy} L ${mid} ${tp.cy} L ${tp.lx} ${tp.cy}`; }
      if (e.lbl) { e.lx = tp.lx - 5; e.ly = tp.cy - 6; }
    } else {
      const laneY = rowsBottom + 12 + lane * 9; lane += 1;
      e.d = `M ${f.cx} ${f.by} L ${f.cx} ${laneY} L ${tp.cx} ${laneY} L ${tp.cx} ${tp.by}`;
    }
  });
  const W = PAD * 2 + steps.length * NW + Math.max(0, steps.length - 1) * CG;
  const H = (backs ? rowsBottom + 12 + backs * 9 : rowsBottom) + (compact ? 6 : 10);
  return { nodes: sorted, pos, edges, W, H, NW, NH };
};
const TOPO_CSS = `
.w2wf-node{cursor:pointer}
.w2wf-node text{pointer-events:none}
.w2wf-nd{fill:var(--white);stroke:var(--ink-4);stroke-width:1}
.w2wf-sel .w2wf-nd{stroke:var(--ink-2)}
.w2wf-nm{fill:var(--ink-3);font-size:11px;font-weight:650;letter-spacing:-.01em}
.w2wf-rs{fill:var(--ink-4);font-size:8.5px;font-weight:550;letter-spacing:-.01em}
.w2wf-st{fill:var(--ink-4);font-family:var(--f-mono);font-size:8px;font-weight:600;letter-spacing:.1em}
.w2wf-gn{fill:var(--ink-3);font-size:9.5px;font-weight:550}
.w2wf-c .w2wf-nm{font-size:10px}
.w2wf-c .w2wf-rs{font-size:7.5px}
.w2wf-c .w2wf-gn{font-size:8.5px}
.w2wf-done .w2wf-nd{fill:var(--ink);stroke:var(--ink)}
.w2wf-done .w2wf-nm{fill:var(--paper)}
.w2wf-done .w2wf-rs{fill:var(--paper);opacity:.72}
.w2wf-done .w2wf-st{fill:var(--paper);opacity:.65}
.w2wf-done .w2wf-gn{fill:var(--ink-2)}
.w2wf-cur .w2wf-nd{stroke:var(--red);stroke-width:2}
.w2wf-cur .w2wf-nm{fill:var(--ink)}
.w2wf-can .w2wf-nd{stroke:var(--red)}
.w2wf-can .w2wf-nm,.w2wf-can .w2wf-st{fill:var(--red)}
.w2wf-can .w2wf-rs{fill:var(--red);opacity:.8}
.w2wf-can:hover .w2wf-nd{fill:var(--red)}
.w2wf-can:hover .w2wf-nm,.w2wf-can:hover .w2wf-rs,.w2wf-can:hover .w2wf-st{fill:var(--paper)}
.w2wf-can:hover .w2wf-dot{fill:var(--paper)}
.w2wf-dot{fill:var(--red)}
.w2wf-ck{stroke:var(--paper);stroke-width:1.6;fill:none}
.w2wf-e{stroke:var(--ink-3);stroke-width:1;fill:none}
.w2wf-er{stroke:var(--red);stroke-dasharray:3 2;opacity:.7}
.w2wf-el{fill:var(--ink-3);font-family:var(--f-mono);font-size:7.5px}
.w2wf-ma{fill:var(--ink-3)}
.w2wf-mr{fill:var(--red)}
`;
const NOSET = new Set();
let TOPO_UID = 0;
/* 拓撲組件:done=墨底勾 / cur=紅描邊紅點 / act=紅色可點(inbox 有此 (instance,node) 才可辦)/ 其餘灰 */
const WfTopo = ({ nodes, compact, done = NOSET, cur = NOSET, act = NOSET, todoByNode, onAct, onAsk, onAttach, attachmentBusy, attachmentError, attachmentCounts, extraFacts, commandContext }) => {
  const [selKey, setSelKey] = _s("");
  const uid = _mm(() => "w2wf" + (++TOPO_UID) + "_", []);
  const topo = _mm(() => buildTopo(nodes, compact), [nodes, compact]);
  const byKey = _mm(() => { const m = {}; topo.nodes.forEach((n) => { m[n.node_key] = n; }); return m; }, [topo]);
  if (!topo.nodes.length) return null;
  const nm = (k) => (byKey[k] && (byKey[k].name || k)) || k || "—";
  const sel = selKey ? byKey[selKey] : null;
  const factsOf = (n) => {
    const outs = nodeOuts(n).filter((o) => o.kind === "flow");
    const rej = nodeOuts(n).find((o) => o.kind === "reject");
    const extras = [num(n.sla_hours) ? t("SLA {n} 小時", { n: n.sla_hours }) : "", num(n.quorum) > 1 ? t("會簽 {n}", { n: n.quorum }) : ""].filter(Boolean).join(" · ");
    const rows = [
      [t("責任部門 / 職位"), responsibilityText(n) || dynamicResponsibilityText(n) || t("未綁定部門與職位")],
      [t("兼容指派"), legacyAssignText(n)],
      [t("權限"), n.required_permission ? n.required_permission + (n.permissionSatisfied === false ? " · " + t("缺權限") : "") : "—"],
      [t("通過後"), outs.length ? outs.map((o) => nm(o.to)).join(" / ") : t("流程完成")],
      [t("駁回退回"), rej ? nm(rej.to) : "—"],
      [t("材料"), arr(n.artifactKinds).length ? arr(n.artifactKinds).map(artLabel).join("、") : "—"],
      [t("附件公證"), num(attachmentCounts && attachmentCounts[n.node_key]) ? t("已公證 {n} 份", { n: attachmentCounts[n.node_key] }) : t("尚無附件")],
      [t("SLA / 會簽"), extras || "—"],
      [t("節點指令集"), arr(n.actions).length ? arr(n.actions).map((action) => action.tool_name).filter(Boolean).join(" / ") : t("此節點尚未配置指令集")],
    ];
    return extraFacts ? rows.concat(arr(extraFacts(n))) : rows;
  };
  return (
    <>
      <div style={{ overflowX: "auto", background: "var(--white)", border: "1px solid var(--hair)" }}>
        <svg className={compact ? "w2wf-c" : ""} width={topo.W} height={topo.H} viewBox={"0 0 " + topo.W + " " + topo.H} style={{ display: "block" }}>
          <defs>
            <marker id={uid + "a"} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path className="w2wf-ma" d="M0 0L8 4L0 8Z"/></marker>
            <marker id={uid + "r"} viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6.5" markerHeight="6.5" orient="auto-start-reverse"><path className="w2wf-mr" d="M0 0L8 4L0 8Z"/></marker>
          </defs>
          {topo.edges.map((e) => (
            <g key={e.id}>
              <path className={"w2wf-e" + (e.kind === "reject" ? " w2wf-er" : "")} d={e.d} markerEnd={"url(#" + uid + (e.kind === "reject" ? "r" : "a") + ")"}/>
              {e.lbl ? <text className="w2wf-el" x={e.lx} y={e.ly} textAnchor="end">{trunc(e.lbl, 18)}</text> : null}
            </g>
          ))}
          {topo.nodes.map((n) => {
            const p = topo.pos[n.node_key];
            const isDone = done.has(n.node_key), isCur = cur.has(n.node_key), isAct = act.has(n.node_key);
            const cls = ["w2wf-node", isDone && !isAct ? "w2wf-done" : "", isCur ? "w2wf-cur" : "", isAct ? "w2wf-can" : "", selKey === n.node_key ? "w2wf-sel" : ""].filter(Boolean).join(" ");
            const todo = todoByNode ? num(todoByNode[n.node_key]) : 0;
            return (
              <g key={n.node_key} className={cls} onClick={() => setSelKey(n.node_key)}>
                <title>{[(n.step_no == null ? "" : n.step_no + " · ") + (n.name || n.node_key), responsibilityText(n) || legacyAssignText(n)].filter(Boolean).join(" · ")}</title>
                {p.gw ? (
                  <>
                    <path className="w2wf-nd" d={"M " + p.cx + " " + (p.cy - p.half) + " L " + p.rx + " " + p.cy + " L " + p.cx + " " + p.by + " L " + p.lx + " " + p.cy + " Z"}/>
                    <text className="w2wf-st" x={p.cx} y={p.cy + 3} textAnchor="middle">{pad2(num(n.step_no))}</text>
                    <text className="w2wf-gn" x={p.cx} y={p.by + (compact ? 10 : 12)} textAnchor="middle">{trunc(n.name || n.node_key, compact ? 9 : 13)}</text>
                  </>
                ) : (
                  <>
                    <rect className="w2wf-nd" x={p.x} y={p.y} width={topo.NW} height={topo.NH}/>
                    <text className="w2wf-st" x={p.x + 8} y={p.y + (compact ? 12 : 14)}>{pad2(num(n.step_no))}</text>
                    <text className="w2wf-nm" x={p.x + 8} y={p.y + (compact ? 29 : 34)}>{trunc(n.name || n.node_key, compact ? 11 : 15)}</text>
                    <text className="w2wf-rs" x={p.x + 8} y={p.y + topo.NH - (compact ? 7 : 9)}>{trunc(assignText(n), compact ? 17 : 24)}</text>
                    {isDone && !isAct ? <path className="w2wf-ck" d={"M " + (p.x + topo.NW - 21) + " " + (p.y + 10) + " l 4 4 l 7 -8"}/> : null}
                    {isCur ? <circle className="w2wf-dot" cx={p.x + topo.NW - 8} cy={p.y + 8} r="3"/> : null}
                    {!isCur && todo > 0 ? <circle className="w2wf-dot" cx={p.x + topo.NW - 8} cy={p.y + 8} r="2.5"/> : null}
                  </>
                )}
              </g>
            );
          })}
        </svg>
      </div>
      <div className="row g10 wrap" style={{ marginTop: 8, fontSize: 10.5, color: "var(--ink-3)" }}>
        <span className="row g4"><span style={{ width: 9, height: 9, background: "var(--ink)", flexShrink: 0 }}/>{t("已完成")}</span>
        <span className="row g4"><span style={{ width: 9, height: 9, border: "2px solid var(--red)", flexShrink: 0 }}/>{t("當前節點")}</span>
        <span className="row g4" style={{ color: "var(--red)" }}><span style={{ width: 9, height: 9, border: "1px solid var(--red)", flexShrink: 0 }}/>{t("輪到你 · 點擊交秘書辦理")}</span>
        <span className="row g4"><span style={{ width: 9, height: 9, border: "1px solid var(--ink-4)", flexShrink: 0 }}/>{t("未到 / 他人經辦")}</span>
      </div>
      {sel && (
        <div className="fade" style={{ border: "1px solid var(--ink)", background: "var(--white)", padding: compact ? 12 : 14, marginTop: 10 }}>
          <div className="row spread" style={{ marginBottom: 8 }}>
            <div className="row g8 wrap" style={{ alignItems: "baseline", minWidth: 0 }}>
              <span className="mono muted" style={{ fontSize: 10 }}>{t("步 {n}", { n: sel.step_no == null ? "—" : sel.step_no })}</span>
              <span style={{ fontWeight: 700, fontSize: 13.5 }}>{sel.name || sel.node_key}</span>
              <T tone={KIND_TONE[sel.node_kind] || "plain"}>{kindLabel(sel.node_kind)}</T>
              {act.has(sel.node_key) && <T tone="redinv" dot>{t("輪到你辦理")}</T>}
            </div>
            <button className="btn ghost sm" style={{ padding: "0 6px" }} onClick={() => setSelKey("")}><I name="x" size={12}/></button>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: compact ? "1fr" : "1fr 1fr", gap: "6px 16px" }}>
            {factsOf(sel).map(([k, v]) => (
              <div key={k} className="row g8" style={{ fontSize: 11.5, alignItems: "baseline", borderTop: "1px solid var(--hair-soft)", paddingTop: 6 }}>
                <span className="label dim" style={{ fontSize: 8, flexShrink: 0 }}>{k}</span>
                <span style={{ marginLeft: "auto", textAlign: "right", wordBreak: "break-all", minWidth: 0 }}>{v || "—"}</span>
              </div>
            ))}
          </div>
          <div className="row g8 wrap" style={{ marginTop: 12 }}>
            {arr(sel.actions).map((action, index) => (
              <B key={(action.tool_name || "command") + index} kind={index === 0 ? "primary" : undefined} size="sm"
                icon={index === 0 ? "arrow" : "terminal"}
                onClick={() => openNodeCommand(sel, action, commandContext)}>
                {t("填寫 · {label}", { label: t(action.label || action.tool_name || t("節點指令")) })}
              </B>
            ))}
            {act.has(sel.node_key) && onAct && <B kind="red" size="sm" icon="check" onClick={() => onAct(sel)}>{t("去辦理")}</B>}
            {onAsk && <B size="sm" icon="sparkle" onClick={() => onAsk(sel)}>{t("秘書研判此節點")}</B>}
            {onAttach && (
              <label className="btn sm" style={{ cursor: attachmentBusy === sel.node_key ? "default" : "pointer", opacity: attachmentBusy === sel.node_key ? .6 : 1 }}>
                <I name={attachmentBusy === sel.node_key ? "refresh" : "shield"} size={12}/>
                {attachmentBusy === sel.node_key ? t("附件上傳中…") : t("上傳附件公證")}
                <input type="file" style={{ display: "none" }} disabled={attachmentBusy === sel.node_key}
                  accept=".pdf,.doc,.docx,.rtf,.odt,.xls,.xlsx,.ods,.csv,.ppt,.pptx,.odp,.txt,.md,.json,.xml,.png,.jpg,.jpeg,.webp,.tif,.tiff,.zip,.7z,.rar"
                  onChange={(ev) => { const f = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (f) onAttach(sel, f); }}/>
              </label>
            )}
          </div>
          {onAttach ? <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.55, marginTop: 8 }}>
            {t("PDF、Word、Excel、圖片等，單檔上限 15MB；上傳後生成 SHA-256、版本鏈與伺服器簽章。")}
          </div> : null}
          {onAttach && attachmentError && attachmentError[sel.node_key] ? <div style={{ fontSize: 10.5, color: "var(--red)", lineHeight: 1.55, marginTop: 6 }}>
            {attachmentError[sel.node_key]}
          </div> : null}
          {arr(sel.actions).length ? <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.55, marginTop: 8 }}>
            {t("選擇指令後，系統會帶入目前流程、實例、待辦與業務單據中已知的欄位；未知欄位留給你補寫。")}
          </div> : null}
        </div>
      )}
    </>
  );
};

/* 管理員配置只綁定穩定組織拓撲:部門 + 職位。人員隨任職關係動態解析,不寫進模板。 */
const NodeResponsibilityConfig = ({ config, onChange, onSave, busy, error, notice, dirtyCount = 0 }) => {
  const nodes = arr(config && config.nodes);
  const departments = arr(config && config.departments);
  const positions = arr(config && config.positions);
  const users = arr(config && config.users);
  const roles = arr(config && config.roles);
  const permissions = arr(config && config.permissions);
  const assignRules = arr(config && config.assign_rules);
  const hasIncompleteBinding = nodes.some((node) => fixedPositionApplicable(node)
    && (!!node.assignee_department_code !== !!node.assignee_position_code));
  const patchNode = (nodeKey, patch) => onChange((current) => ({
    ...current,
    nodes: arr(current && current.nodes).map((node) => node.node_key === nodeKey ? { ...node, ...patch } : node),
  }));
  const departmentCode = (department) => department.unit_code || department.department_code || department.code || "";
  const departmentName = (department) => department.unit_name || department.department_name || department.name || departmentCode(department);
  const positionCode = (position) => position.position_code || position.code || "";
  const positionName = (position) => position.position_name || position.name || positionCode(position);
  const positionDepartment = (position) => position.org_unit_code || position.unit_code || position.department_code || "";
  const permissionKey = (permission) => typeof permission === "string" ? permission : (permission.key || permission.permission_key || "");
  const legacyValueControl = (node) => {
    if (node.assign_rule === "user") return (
      <select className="field boxed" value={node.assign_value || ""} onChange={(e) => patchNode(node.node_key, { assign_value: e.target.value || null })}>
        <option value="">{t("未配置")}</option>
        {users.map((user) => <option key={user.id} value={user.id}>{user.display_name || user.username || ("#" + user.id)}</option>)}
      </select>
    );
    if (node.assign_rule === "role") return (
      <select className="field boxed" value={node.assign_value || ""} onChange={(e) => patchNode(node.node_key, { assign_value: e.target.value || null })}>
        <option value="">{t("未配置")}</option>
        {roles.map((role) => <option key={role.id || role.role_name} value={role.role_name}>{role.role_name}</option>)}
      </select>
    );
    if (node.assign_rule === "permission") return (
      <select className="field boxed" value={node.assign_value || ""} onChange={(e) => patchNode(node.node_key, { assign_value: e.target.value || null })}>
        <option value="">{t("未配置")}</option>
        {permissions.map((permission) => { const key = permissionKey(permission); return key ? <option key={key} value={key}>{key}</option> : null; })}
      </select>
    );
    if (node.assign_rule === "from_context") return (
      <input className="field boxed" value={node.assign_value || ""} onChange={(e) => patchNode(node.node_key, { assign_value: e.target.value || null })} placeholder="context field"/>
    );
    return <span className="muted" style={{ fontSize: 11.5, padding: "8px 0" }}>{legacyAssignText(node)}</span>;
  };
  return (
    <div className="fade" style={{ borderTop: "2px solid var(--ink)", marginTop: 18, paddingTop: 14 }}>
      <div className="row spread wrap g10" style={{ alignItems: "flex-start", marginBottom: 12 }}>
        <div className="col g4">
          <span style={{ fontWeight: 750, fontSize: 14 }}>{t("節點責任配置")}</span>
          <span className="muted" style={{ fontSize: 11.5 }}>{t("人員更換不影響流程；系統按當前在崗人員動態派單。")}</span>
          <span className="muted" style={{ fontSize: 10.5 }}>{t("管理層可跨部門處理")}</span>
        </div>
        <div className="row g8 wrap">
          {notice ? <T tone="ok" dot>{notice}</T> : null}
          {error ? <T tone="bad" dot>{error}</T> : null}
          {dirtyCount > 0 ? <T tone="plain">{t("待保存變更 {n} 個節點", { n: dirtyCount })}</T> : null}
          {hasIncompleteBinding ? <T tone="warn" dot>{t("部門與職位必須成對選擇")}</T> : null}
          <B kind="primary" size="sm" icon="check" disabled={busy || !nodes.length || !dirtyCount || hasIncompleteBinding} onClick={onSave}>{busy ? t("保存中…") : t("保存節點責任")}</B>
        </div>
      </div>
      {nodes.length ? <WfTopo nodes={nodes} compact commandContext={{
        workflow: { key: config && config.workflow_key },
      }}/> : null}
      <div className="col" style={{ borderTop: "1px solid var(--hair)", marginTop: 14 }}>
        {nodes.map((node, index) => {
          const selectedDepartment = node.assignee_department_code || "";
          const selectedPosition = node.assignee_position_code || "";
          const availablePositions = positions.filter((position) => !selectedDepartment || positionDepartment(position) === selectedDepartment);
          const fixedPosition = fixedPositionApplicable(node);
          const stable = !!selectedDepartment && !!selectedPosition;
          return (
            <div key={node.node_key || index} style={{ padding: "14px 0", borderBottom: "1px solid var(--hair-soft)" }}>
              <div className="row spread wrap g8" style={{ marginBottom: 10 }}>
                <div className="row g8 wrap" style={{ alignItems: "baseline" }}>
                  <span className="mono muted" style={{ fontSize: 9.5 }}>{pad2(num(node.step_no) || index + 1)}</span>
                  <span style={{ fontWeight: 700, fontSize: 13 }}>{node.name || node.node_key}</span>
                  <T tone={KIND_TONE[node.node_kind] || "plain"}>{kindLabel(node.node_kind)}</T>
                  {fixedPosition
                    ? (stable ? <T tone="ok" dot>{t("穩定綁定")}</T> : <T tone="warn" dot>{t("未綁定部門與職位")}</T>)
                    : <T tone="plain">{t("動態責任規則")}</T>}
                </div>
                <span className="mono muted" style={{ fontSize: 9.5 }}>{node.node_key}</span>
              </div>
              {fixedPosition ? <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 10 }}>
                  <label className="col g4">
                    <span className="label dim" style={{ fontSize: 8 }}>{t("責任部門")}</span>
                    <select className="field boxed" value={selectedDepartment} onChange={(e) => {
                      const nextDepartment = e.target.value;
                      const currentPosition = positions.find((position) => positionCode(position) === selectedPosition);
                      patchNode(node.node_key, {
                        assignee_department_code: nextDepartment || null,
                        assignee_department_name: nextDepartment ? departmentName(departments.find((department) => departmentCode(department) === nextDepartment) || {}) : null,
                        assignee_position_code: currentPosition && positionDepartment(currentPosition) === nextDepartment ? selectedPosition : null,
                        assignee_position_name: currentPosition && positionDepartment(currentPosition) === nextDepartment ? positionName(currentPosition) : null,
                      });
                    }}>
                      <option value="">{t("請選擇部門")}</option>
                      {departments.map((department) => { const code = departmentCode(department); return code ? <option key={code} value={code}>{departmentName(department)}</option> : null; })}
                    </select>
                  </label>
                  <label className="col g4">
                    <span className="label dim" style={{ fontSize: 8 }}>{t("責任職位")}</span>
                    <select className="field boxed" disabled={!selectedDepartment || !availablePositions.length} value={selectedPosition} onChange={(e) => {
                      const nextPosition = positions.find((position) => positionCode(position) === e.target.value);
                      patchNode(node.node_key, {
                        assignee_position_code: e.target.value || null,
                        assignee_position_name: nextPosition ? positionName(nextPosition) : null,
                      });
                    }}>
                      <option value="">{selectedDepartment && !availablePositions.length ? t("該部門暫無可選職位") : t("請選擇職位")}</option>
                      {availablePositions.map((position) => { const code = positionCode(position); return code ? <option key={code} value={code}>{positionName(position)}</option> : null; })}
                    </select>
                  </label>
                </div>
                <div className="muted" style={{ fontSize: 10.5, marginTop: 6 }}>
                  {t("固定部門與職位（推薦）")} · {responsibilityText(node) || t("未綁定部門與職位")}
                </div>
              </> : (
                <div style={{ border: "1px solid var(--hair)", background: "var(--paper)", padding: "9px 11px", fontSize: 11.5 }}>
                  <span className="label dim" style={{ fontSize: 8, marginRight: 8 }}>{t("動態責任規則")}</span>
                  {dynamicResponsibilityText(node) || legacyAssignText(node)}
                </div>
              )}
              <details style={{ marginTop: 10 }}>
                <summary className="muted" style={{ cursor: "pointer", fontSize: 11.5 }}>{t("保留舊指派規則（兼容）")} · {legacyAssignText(node)}</summary>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(130px,1fr))", gap: 8, marginTop: 9, alignItems: "end" }}>
                  <label className="col g4"><span className="label dim" style={{ fontSize: 8 }}>{t("指派")}</span>
                    <select className="field boxed" value={node.assign_rule || ""} onChange={(e) => patchNode(node.node_key, { assign_rule: e.target.value, assign_value: null })}>
                      {assignRules.map((rule) => <option key={rule} value={rule}>{t(ASSIGN[rule] || rule)}</option>)}
                    </select>
                  </label>
                  <label className="col g4"><span className="label dim" style={{ fontSize: 8 }}>{t("兼容指派")}</span>{legacyValueControl(node)}</label>
                  <label className="col g4"><span className="label dim" style={{ fontSize: 8 }}>{t("權限")}</span>
                    <select className="field boxed" value={node.required_permission || ""} onChange={(e) => patchNode(node.node_key, { required_permission: e.target.value || null })}>
                      <option value="">—</option>
                      {permissions.map((permission) => { const key = permissionKey(permission); return key ? <option key={key} value={key}>{key}</option> : null; })}
                    </select>
                  </label>
                  <label className="col g4"><span className="label dim" style={{ fontSize: 8 }}>{t("會簽 {n}", { n: "" })}</span><input className="field boxed" type="number" min="1" max="20" value={node.quorum || 1} onChange={(e) => patchNode(node.node_key, { quorum: e.target.value })}/></label>
                  <label className="col g4"><span className="label dim" style={{ fontSize: 8 }}>SLA</span><input className="field boxed" type="number" min="1" max="1440" value={node.sla_hours || ""} onChange={(e) => patchNode(node.node_key, { sla_hours: e.target.value })}/></label>
                </div>
              </details>
            </div>
          );
        })}
      </div>
    </div>
  );
};

/* ── 流水詳情抽屜(GET /api/wf/instances/:id + 該流程 map → 實例進度拓撲)── */
const InstDrawer = ({ item, wfName, inbox, onClose }) => {
  const [d, setD] = _s(null);
  const [map, setMap] = _s(null);
  const [upBusy, setUpBusy] = _s("");
  const [upErr, setUpErr] = _s({});
  const [dlErr, setDlErr] = _s({});
  const [nodeAttachBusy, setNodeAttachBusy] = _s("");
  const [nodeAttachErr, setNodeAttachErr] = _s({});
  const [verifyState, setVerifyState] = _s({});
  _e(() => {
    let on = true;
    setD(null);
    W2.json("/api/wf/instances/" + item.id).then((x) => { if (on) setD(x || {}); }).catch(() => { if (on) setD({}); });
    return () => { on = false; };
  }, [item.id]);
  _e(() => {
    const key = item.workflow_key;
    if (!key) { setMap({}); return; }
    let on = true;
    setMap(null);
    W2.json("/api/wf/workflows/" + key + "/map").then((m) => { if (on) setMap(m || {}); }).catch(() => { if (on) setMap({}); });
    return () => { on = false; };
  }, [item.id, item.workflow_key]);
  const inst = (d && d.instance) || {};
  const timeline = arr(d && d.timeline);
  const artifacts = arr(d && d.artifacts);
  const title = inst.title || item.title || "—";
  const no = inst.instance_no || item.instance_no || "—";
  const entityRef = workflowBusinessRef({ ...item, ...inst, relations: arr(d && d.relations).length ? d.relations : item.relations, id: item.id });
  /* 節點狀態:done=有通過類流轉/最新輪任務已通過;cur=current_node_key+開放任務;act=inbox 有 (本實例,節點) */
  const wfState = _mm(() => {
    const done = new Set(), cur = new Set(), act = new Set(), latest = {};
    arr(d && d.tasks).forEach((tk) => {
      if (!tk || !tk.node_key) return;
      const old = latest[tk.node_key];
      if (!old || num(tk.round_no) > num(old.round_no) || (num(tk.round_no) === num(old.round_no) && num(tk.id) > num(old.id))) latest[tk.node_key] = tk;
    });
    arr(d && d.timeline).forEach((tr) => {
      if (tr && tr.from_node_key && ["approve", "submit", "complete", "gateway", "fork", "arrive", "join_fire"].indexOf(tr.action) >= 0) done.add(tr.from_node_key);
    });
    Object.keys(latest).forEach((k) => {
      const s = latest[k].status;
      if (s === "approved") done.add(k);
      else if (s === "pending" || s === "in_progress") cur.add(k);
    });
    const st = inst.status || item.status;
    if ((st === "running" || st === "waiting") && (inst.current_node_key || item.current_node_key)) cur.add(inst.current_node_key || item.current_node_key);
    if (st === "completed" || st === "rejected" || st === "cancelled") cur.clear();
    cur.forEach((k) => done.delete(k));
    arr(inbox).forEach((tk) => { if (tk && String(tk.instance_id) === String(item.id) && tk.node_key) act.add(tk.node_key); });
    return { done, cur, act, latest };
  }, [d, inbox, item.id]);
  const actNode = (n) => ask(t("請幫我辦理流程「{wf}」(單號 {no},實例 {id})第 {step} 步「{node}」:核對材料和上下文後給出通過/駁回建議,經我確認後執行",
    { wf: wfName(inst.workflow_key || item.workflow_key), no, id: item.id, step: n.step_no == null ? "—" : n.step_no, node: n.name || n.node_key || "—" }));
  const askNode = (n) => ask(t("分析流程「{wf}」第 {step} 步「{node}」:處理要點、指派與權限規則、必需材料和下一步流轉",
    { wf: wfName(inst.workflow_key || item.workflow_key), step: n.step_no == null ? "—" : n.step_no, node: n.name || n.node_key || "—" }));
  const nodeFacts = (n) => {
    const tk = wfState.latest[n.node_key];
    if (!tk) return [];
    const rows = [[t("狀態"), t(TSTAT[tk.status] || tk.status || "—")], [t("辦理時間"), wfDate(tk.decided_at)]];
    if (tk.comment) rows.push([t("意見"), tk.comment]);
    return rows;
  };
  const nodeCommandContext = (node) => {
    const openTask = arr(inbox).find((task) => task
      && String(task.instance_id) === String(item.id)
      && task.node_key === node.node_key
      && (!task.status || ["pending", "in_progress"].indexOf(task.status) >= 0));
    const task = openTask || wfState.latest[node.node_key] || {};
    const mergedInstance = { ...item, ...inst };
    const state = (mergedInstance.state && typeof mergedInstance.state === "object") ? mergedInstance.state : {};
    return {
      workflow: { key: mergedInstance.workflow_key || item.workflow_key },
      instance: mergedInstance,
      item,
      task,
      tender: {
        id: state.tender_notice_id || mergedInstance.tender_notice_id,
        notice_ref: state.tender_notice_ref || mergedInstance.tender_notice_ref,
      },
      contract: { id: state.contract_id || mergedInstance.contract_id },
    };
  };
  /* 靜默重取實例詳情(上傳後刷新材料,不清空抽屜)*/
  const refreshDetail = () => {
    W2.json("/api/wf/instances/" + item.id).then((x) => setD(x || {})).catch(() => {});
  };
  const mapByKey = _mm(() => {
    const m = {};
    arr(map && map.nodes).forEach((n) => { if (n && n.node_key) m[n.node_key] = n; });
    return m;
  }, [map]);
  /* 一般節點附件按 attachment_key 分組；既有必需材料按(節點,材料類型)分組。 */
  const artGroups = _mm(() => {
    const gm = {};
    arr(d && d.artifacts).forEach((a) => {
      if (!a) return;
      const logicalKey = a.attachment_key ? ("attachment\u0000" + a.attachment_key) : ("required\u0000" + (a.node_key || "") + "\u0000" + (a.kind || ""));
      (gm[logicalKey] || (gm[logicalKey] = { node_key: a.node_key, kind: a.kind, attachment_key: a.attachment_key, rows: [] })).rows.push(a);
    });
    return Object.keys(gm).map((gk) => {
      const g = gm[gk];
      g.rows.sort((x, y) => (num(y.version) - num(x.version)) || (num(y.id) - num(x.id)));
      g.current = g.rows[0];
      g.count = g.rows.length;
      return g;
    });
  }, [d]);
  const attachmentCounts = _mm(() => {
    const out = {}, seen = {};
    arr(d && d.artifacts).forEach((a) => {
      if (!a || !a.node_key) return;
      const key = a.node_key + "\u0000" + (a.attachment_key || a.id);
      if (seen[key]) return;
      seen[key] = 1;
      out[a.node_key] = num(out[a.node_key]) + 1;
    });
    return out;
  }, [d]);
  const curFileOf = (nk, kind) => {
    const g = artGroups.find((x) => x.node_key === nk && x.kind === kind);
    return g && artHasFile(g.current);
  };
  /* 當前輪到我辦理的任務(inbox 命中本實例+開放狀態)→ 逐個必需材料類型出上傳控件 */
  const myUploads = _mm(() => {
    const out = [], seen = {};
    arr(inbox).forEach((tk) => {
      if (!tk || String(tk.instance_id) !== String(item.id) || !tk.node_key) return;
      if (tk.status && ["pending", "in_progress"].indexOf(tk.status) < 0) return;
      arr(mapByKey[tk.node_key] && mapByKey[tk.node_key].artifactKinds).forEach((k) => {
        if (!k) return;
        const key = tk.id + "\u0000" + k;
        if (seen[key]) return;
        seen[key] = 1;
        out.push({ taskId: tk.id, node_key: tk.node_key, kind: k });
      });
    });
    return out;
  }, [inbox, item.id, mapByKey]);
  const doUpload = async (taskId, kind, file) => {
    if (!file) return;
    const key = taskId + "\u0000" + kind;
    setUpErr((p) => { const n = { ...p }; delete n[key]; return n; });
    setUpBusy(key);
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("kind", kind);
      const res = await W2.fetch("/api/wf/tasks/" + taskId + "/artifact/upload", { method: "POST", body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error((j && (j.error || j.message)) || (res.status === 403 ? t("無權上傳") : res.status === 400 ? t("上傳失敗:超過 15MB 上限") : t("上傳失敗")));
      refreshDetail();
    } catch (e) {
      setUpErr((p) => ({ ...p, [key]: (e && e.message) || t("上傳失敗") }));
    } finally {
      setUpBusy("");
    }
  };
  const doNodeAttach = async (node, file) => {
    if (!node || !node.node_key || !file) return;
    const nodeKey = node.node_key;
    setNodeAttachErr((p) => { const n = { ...p }; delete n[nodeKey]; return n; });
    setNodeAttachBusy(nodeKey);
    try {
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("kind", "node_attachment");
      const res = await W2.fetch("/api/wf/instances/" + encodeURIComponent(item.id) + "/nodes/" + encodeURIComponent(nodeKey) + "/attachments", { method: "POST", body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error((j && (j.detail || j.error || j.message)) || (res.status === 413 ? t("上傳失敗:超過 15MB 上限") : res.status === 415 ? t("不支援此檔案格式") : res.status === 403 ? t("無權上傳") : t("上傳失敗")));
      refreshDetail();
    } catch (e) {
      setNodeAttachErr((p) => ({ ...p, [nodeKey]: (e && e.message) || t("上傳失敗") }));
    } finally {
      setNodeAttachBusy("");
    }
  };
  const doDownload = async (a) => {
    const id = a && a.id;
    if (id == null) return;
    setDlErr((p) => { const n = { ...p }; delete n[id]; return n; });
    try {
      const res = await W2.fetch(a.download_url || ("/api/wf/artifacts/" + id + "/download"));
      if (!res.ok) throw new Error();
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const el = document.createElement("a");
      el.href = url; el.download = a.file_name || (artLabel(a.kind) || "artifact"); el.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setDlErr((p) => ({ ...p, [id]: t("下載失敗") }));
    }
  };
  const doVerify = async (a) => {
    const id = a && a.id;
    if (!id) return;
    setVerifyState((p) => ({ ...p, [id]: { busy: true } }));
    try {
      const j = await W2.json(a.verify_url || ("/api/wf/node-attachments/" + id + "/verify"));
      setVerifyState((p) => ({ ...p, [id]: { busy: false, verified: j.verified === true, checks: j.checks } }));
    } catch (e) {
      setVerifyState((p) => ({ ...p, [id]: { busy: false, verified: false } }));
    }
  };
  const facts = [
    [t("流程"), wfName(inst.workflow_key || item.workflow_key)],
    [t("當前節點"), inst.current_node_key || item.current_node_key || "—"],
    [t("發起於"), wfDate(inst.created_at || item.created_at)],
    [t("完成於"), wfDate(inst.completed_at || item.completed_at)],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          {statTag(inst.status || item.status)}
          <div className="row g4">
            {entityRef && <B size="sm" icon="layers" onClick={() => W2.openEntity(entityRef, { tab: "workflow", node_key: inst.current_node_key || item.current_node_key })}>{t("業務全鏈")}</B>}
            <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
          </div>
        </div>
        <div style={{ fontSize: 18, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.3 }}>{title}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{no}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {facts.map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span className="num" style={{ fontSize: 13, fontWeight: 650, wordBreak: "break-all" }}>{v || "—"}</span>
            </div>
          ))}
        </div>

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("流程拓撲")}</LB>
        <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 10, marginBottom: 18 }}>
          {map == null ? (
            <div className="muted" style={{ fontSize: 12 }}>{t("拓撲載入中…")}</div>
          ) : arr(map.nodes).length ? (
            <>
              <WfTopo nodes={map.nodes} compact done={wfState.done} cur={wfState.cur} act={wfState.act}
                onAct={actNode} onAsk={askNode} extraFacts={nodeFacts}
                onAttach={doNodeAttach} attachmentBusy={nodeAttachBusy}
                attachmentError={nodeAttachErr} attachmentCounts={attachmentCounts}
                commandContext={nodeCommandContext}/>
              <div className="muted" style={{ fontSize: 10.5, marginTop: 6, lineHeight: 1.6 }}>{t("點節點看詳情;紅色節點輪到你,點擊直接交秘書辦理。")}</div>
            </>
          ) : (
            <div className="muted" style={{ fontSize: 12 }}>{t("此流程暫無節點定義")}</div>
          )}
        </div>

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("流程時間線")}</LB>
        <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 10, marginBottom: 18 }}>
          {d == null ? (
            <div className="muted" style={{ fontSize: 12 }}>{t("詳情載入中…")}</div>
          ) : timeline.length ? (
            <div className="col g8">
              {timeline.map((row, i) => (
                <div key={row.id || i} className="row g8" style={{ fontSize: 12, alignItems: "baseline" }}>
                  <span style={{ width: 7, height: 7, flexShrink: 0, background: row.action === "reject" ? "var(--red)" : row.action === "complete" ? "var(--ok)" : "var(--ink-4)" }}/>
                  <span style={{ fontWeight: 650 }}>{t(ACT[row.action] || row.action || "—")}</span>
                  {row.comment ? <span className="ink2" style={{ flex: 1, minWidth: 0 }}>「{row.comment}」</span> : <span style={{ flex: 1 }}/>}
                  <span className="num muted" style={{ fontSize: 10.5, flexShrink: 0 }}>{wfDate(row.created_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="muted" style={{ fontSize: 12 }}>{t("暫無時間線記錄")}</div>
          )}
        </div>

        {(
          <>
            <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("已留存證明")}</LB>
            <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 10, marginBottom: 18 }} className="col g10">
              {!artGroups.length && !myUploads.length ? <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>
                {t("尚無附件")} · {t("點選上方任意流程節點即可上傳附件公證。")}
              </div> : null}
              {artGroups.map((g, gi) => {
                const a = g.current || {};
                const ver = num(a.version) || 1;
                const verification = verifyState[a.id] || {};
                if (artHasFile(a)) {
                  return (
                    <div key={a.id || gi} className="col g4">
                      <div className="row g8 wrap" style={{ fontSize: 12, alignItems: "baseline" }}>
                        <I name="doc" size={12} color="var(--ink-3)"/>
                        <span style={{ fontWeight: 650 }}>{artLabel(g.kind)}</span>
                        <T tone="plain">{"v" + ver}</T>
                        {g.count > 1 ? <span className="muted" style={{ fontSize: 10 }}>{t("共 {n} 版", { n: g.count })}</span> : null}
                        <span className="num muted" style={{ marginLeft: "auto", fontSize: 10.5, flexShrink: 0 }}>{wfDate(a.created_at)}</span>
                      </div>
                      <div className="row g8 wrap" style={{ marginLeft: 20, alignItems: "baseline", fontSize: 11.5 }}>
                        <span style={{ wordBreak: "break-all", minWidth: 0 }}>{a.file_name || "—"}</span>
                        <span className="num muted" style={{ fontSize: 10.5, flexShrink: 0 }}>{fsize(a.file_size)}</span>
                        <span style={{ marginLeft: "auto", flexShrink: 0 }}>
                          <B size="sm" icon="inbound" onClick={() => doDownload(a)}>{t("下載")}</B>
                        </span>
                      </div>
                      <div className="row g8 wrap" style={{ marginLeft: 20, alignItems: "baseline" }}>
                        {(a.file_seal != null && a.file_seal !== "") ? <T tone="plain"><I name="shield" size={10}/>{" " + t("鋼印 {seal}", { seal: a.file_seal })}</T> : null}
                        {a.file_sha256 ? <span className="mono muted" style={{ fontSize: 9.5, wordBreak: "break-all" }}>{String(a.file_sha256).slice(0, 12)}</span> : null}
                        {a.verify_url ? <B size="sm" icon="shield" onClick={() => doVerify(a)} disabled={verification.busy}>
                          {verification.busy ? t("驗證中…") : t("驗證公證")}
                        </B> : null}
                        {verification.busy !== true && verification.verified === true ? <T tone="ok">{t("公證有效")}</T> : null}
                        {verification.busy !== true && verification.verified === false ? <T tone="bad">{t("公證驗證異常")}</T> : null}
                      </div>
                      {dlErr[a.id] ? <span style={{ marginLeft: 20, fontSize: 10.5, color: "var(--red)" }}>{dlErr[a.id]}</span> : null}
                    </div>
                  );
                }
                return (
                  <div key={a.id || gi} className="row g8 wrap" style={{ fontSize: 12, alignItems: "baseline" }}>
                    <I name="clipboard" size={12} color="var(--ink-3)"/>
                    <span style={{ fontWeight: 650 }}>{artLabel(g.kind)}</span>
                    {ver > 1 ? <T tone="plain">{"v" + ver}</T> : null}
                    {g.count > 1 ? <span className="muted" style={{ fontSize: 10 }}>{t("共 {n} 版", { n: g.count })}</span> : null}
                    <span className="muted num" style={{ marginLeft: "auto", fontSize: 10.5, textAlign: "right", wordBreak: "break-all" }}>{a.content_text || a.title || a.file_url || "—"}</span>
                  </div>
                );
              })}
              {myUploads.length ? (
                <div className="col g8" style={{ borderTop: artGroups.length ? "1px solid var(--hair-soft)" : "none", paddingTop: artGroups.length ? 10 : 0 }}>
                  {myUploads.map((u) => {
                    const key = u.taskId + " " + u.kind;
                    const busy = upBusy === key;
                    const has = curFileOf(u.node_key, u.kind);
                    const err = upErr[key];
                    return (
                      <div key={key} className="col g4">
                        <div className="row g8" style={{ fontSize: 11.5, alignItems: "center" }}>
                          <span className="label dim" style={{ fontSize: 8, flexShrink: 0 }}>{artLabel(u.kind)}</span>
                          <label className="btn sm" style={{ marginLeft: "auto", cursor: busy ? "default" : "pointer", opacity: busy ? .6 : 1 }}>
                            <I name={busy ? "refresh" : "outbound"} size={12}/>{busy ? t("上傳中…") : has ? t("重新上傳更新") : t("上傳材料")}
                            <input type="file" style={{ display: "none" }} disabled={busy}
                              onChange={(ev) => { const f = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (f) doUpload(u.taskId, u.kind, f); }}/>
                          </label>
                        </div>
                        {err ? <span style={{ marginLeft: 4, fontSize: 10.5, color: "var(--red)", wordBreak: "break-word" }}>{err}</span> : null}
                      </div>
                    );
                  })}
                  <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>{t("材料上傳即上鋼印(SHA-256 封存),可下載、可重新上傳更新;齊全後方可推進節點。")}</div>
                </div>
              ) : null}
            </div>
          </>
        )}

        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }}
            onClick={() => ask(t("流程「{title}」(單號 {no})推進得怎麼樣?卡住的話幫我催辦當前處理人", { title, no }))}>
            <I name="clock" size={14}/>{t("催辦這個流程")}
          </button>
          <button className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }}
            onClick={() => ask(t("幫流程「{title}」(單號 {no})登記證明材料:請追問材料類型和憑證編號/說明後登記", { title, no }))}>
            <I name="clipboard" size={14}/>{t("讓秘書登記材料")}
          </button>
        </div>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
      </div>
    </div>
  );
};

/* ── 招標公告詳情(展開行:草稿/招標中=邀請與密封投標;已開標起=比價表)── */
const TenderDetail = ({ det, notice }) => {
  if (det == null) return <div className="muted" style={{ fontSize: 12, padding: "14px 16px" }}>{t("詳情載入中…")}</div>;
  const n = (det && det.notice) || notice || {};
  const invites = arr(det && det.invites);
  const envs = arr(det && det.envelopes);
  const evals = arr(det && det.evaluations);
  const opened = ["opened", "evaluated", "awarded"].indexOf(n.status) >= 0;
  const meanScore = (eid) => {
    const es = evals.filter((x) => x && String(x.envelope_id) === String(eid) && Number.isFinite(Number(x.score)));
    return es.length ? (es.reduce((s, x) => s + Number(x.score), 0) / es.length).toFixed(1) : null;
  };
  const ranked = opened
    ? [...envs].sort((a, b) => {
        const ta = a && a.bid && Number.isFinite(Number(a.bid.total)) ? Number(a.bid.total) : Infinity;
        const tb = b && b.bid && Number.isFinite(Number(b.bid.total)) ? Number(b.bid.total) : Infinity;
        return ta - tb;
      })
    : envs;
  let maxTotal = 0;
  ranked.forEach((ev) => { const v = ev && ev.bid ? Number(ev.bid.total) : NaN; if (Number.isFinite(v)) maxTotal = Math.max(maxTotal, v); });
  return (
    <div className="fade" style={{ padding: "14px 16px", borderTop: "1px solid var(--hair)", background: "var(--white)" }}>
      <div className="col g4" style={{ marginBottom: 10 }}>
        <LB dim style={{ fontSize: 8.5 }}>{t("需求說明")}</LB>
        <span className="ink2" style={{ fontSize: 12.5, lineHeight: 1.65, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{n.requirements_text || "—"}</span>
      </div>
      <div className="row g10 wrap" style={{ fontSize: 11.5, marginBottom: 14, alignItems: "baseline" }}>
        <span className="muted">{t("預算上限")}</span><span className="num" style={{ fontWeight: 650 }}>{cny(n.budget_ceiling)}</span>
        <span className="muted">{t("截標時間")}</span><span className="num">{wfDate(n.bid_deadline)}</span>
        <span className="muted">{t("鋼印")}</span><span className="mono muted" style={{ fontSize: 10 }}>{n.seal_serial || "—"}</span>
        {n.award_seal_serial ? <><span className="muted">{t("定標鋼印")}</span><span className="mono muted" style={{ fontSize: 10 }}>{n.award_seal_serial}</span></> : null}
      </div>

      <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{t("邀請名單")}</LB>
      <div style={{ borderTop: "1px solid var(--hair)", padding: "8px 0 14px" }}>
        {invites.length ? (
          <div className="col g6">
            {invites.map((iv, i) => {
              const applied = iv && iv.source === "applied";
              const qual = applied ? parseQual(iv) : null;
              const qTag = applied ? QSTAT[iv.qualification_status] : null;
              const verdict = qual && qual.verdict && typeof qual.verdict === "object" ? qual.verdict : null;
              const evd = qual && qual.evidence && typeof qual.evidence === "object" ? qual.evidence : null;
              const rel = verdict && RELV[verdict.relevance] ? t(RELV[verdict.relevance]) : "";
              const reasons = verdict ? arr(verdict.reasons).filter(Boolean).join(";") : "";
              const evBits = evd ? [
                evd.industry_template || "",
                arr(evd.categories)[0] ? t("主營 {c}", { c: arr(evd.categories)[0] }) : "",
                num(evd.item_count) > 0 ? t("物資 {n} 種", { n: evd.item_count }) : "",
                Number.isFinite(Number(evd.stock_value_cny)) && Number(evd.stock_value_cny) > 0 ? t("儲值 {v}", { v: cny(evd.stock_value_cny) }) : "",
              ].filter(Boolean) : [];
              const appName = iv.invitee_name || iv.invitee_slug || "—";
              const noticeNo = n.notice_no || (n.id != null ? String(n.id) : "—");
              return (
                <div key={iv.id || i} className="col g4">
                  <div className="row g8" style={{ fontSize: 12, alignItems: "baseline" }}>
                    <span className="mono muted" style={{ fontSize: 10 }}>{pad2(i + 1)}</span>
                    <span style={{ fontWeight: 650 }}>{appName}</span>
                    {ivTag(iv.status)}
                    <span className="num muted" style={{ marginLeft: "auto", fontSize: 10.5 }}>{wfDate(iv.sent_at)}</span>
                  </div>
                  {applied && (qTag || rel || reasons || evBits.length) ? (
                    <div className="col g4" style={{ marginLeft: 22, padding: "4px 0 4px 10px", borderLeft: "2px solid var(--hair)" }}>
                      <div className="row g8 wrap" style={{ alignItems: "baseline" }}>
                        <span className="label dim" style={{ fontSize: 8, flexShrink: 0 }}>{t("資質")}</span>
                        {qTag ? <T tone={qTag[0]}>{t(qTag[1])}</T> : null}
                        {rel ? <T tone="plain">{rel}</T> : null}
                        {evBits.length ? <span className="muted" style={{ fontSize: 10.5 }}>{evBits.join(" · ")}</span> : null}
                      </div>
                      {reasons ? <span className="muted" style={{ fontSize: 10.5, lineHeight: 1.55, wordBreak: "break-word" }}>{reasons}</span> : null}
                      {iv.qualification_status === "pending_review" ? (
                        <div className="row g6" style={{ marginTop: 2 }}>
                          <B size="sm" icon="check" onClick={() => ask(t("覆核公開招標「{no}」中「{name}」的報名資質,通過就放行投標", { no: noticeNo, name: appName }))}>{t("通過覆核")}</B>
                          <B size="sm" icon="x" onClick={() => ask(t("拒絕公開招標「{no}」中「{name}」的報名資質,並說明理由", { no: noticeNo, name: appName }))}>{t("拒絕")}</B>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : (
          <div className="muted" style={{ fontSize: 12 }}>{t("暫無邀請")}</div>
        )}
      </div>

      <LB dim style={{ fontSize: 8.5, marginBottom: 6 }}>{opened ? t("比價表") : t("密封投標")}</LB>
      <div style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
        {!ranked.length ? (
          <div className="muted" style={{ fontSize: 12 }}>{t("暫無投標")}</div>
        ) : opened ? (
          <div className="col g6">
            {ranked.map((ev, i) => {
              const bid = (ev && ev.bid) || {};
              const total = Number(bid.total);
              const has = Number.isFinite(total);
              const verified = num(ev.reveal_verified) === 1;
              const ms = meanScore(ev.id);
              const isWin = n.awarded_envelope_id != null && String(n.awarded_envelope_id) === String(ev.id);
              return (
                <HBar key={ev.id || i} idx={i + 1}
                  name={(ev.bidder_name || ev.bidder_slug || "—") + (isWin ? " · " + t("中標") : "")}
                  w={has && maxTotal > 0 ? Math.max(6, Math.round((total / maxTotal) * 100)) : 6}
                  val={has ? cny(total) : "—"}
                  red={!verified}
                  sub={[t("交期") + " " + (bid.delivery || "—"), verified ? t("驗證通過") : t("驗證異常"), t("平均評分") + " " + (ms == null ? "—" : ms)].join(" · ")}
                  title={ev.bid_hash || ""}/>
              );
            })}
          </div>
        ) : (
          <div className="col g6">
            {ranked.map((ev, i) => (
              <div key={ev.id || i} className="row g8" style={{ fontSize: 12, alignItems: "baseline" }}>
                <span className="mono muted" style={{ fontSize: 10 }}>{pad2(i + 1)}</span>
                <span style={{ fontWeight: 650 }}>{ev.bidder_name || ev.bidder_slug || "—"}</span>
                <T tone="plain">{t("密封中")}</T>
                <span className="mono muted" style={{ marginLeft: "auto", fontSize: 10, textAlign: "right", wordBreak: "break-all" }}>{shortHash(ev.bid_hash)}{ev.seal_serial ? " · " + ev.seal_serial : ""}</span>
                <span className="num muted" style={{ fontSize: 10.5, flexShrink: 0 }}>{wfDate(ev.submitted_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

/* ── 頁面 ── */
const Page = ({ boot }) => {
  const [tasks, setTasks] = _s([]);
  const [mineTasksLoading, setMineTasksLoading] = _s(true);
  const [mineTasksError, setMineTasksError] = _s("");
  const [allTasks, setAllTasks] = _s(null);
  const [allTasksLoading, setAllTasksLoading] = _s(false);
  const [allTasksError, setAllTasksError] = _s("");
  const [taskScope, setTaskScope] = _s("mine");
  const [insts, setInsts] = _s([]);
  const [flows, setFlows] = _s(null);
  const [flowKey, setFlowKey] = _s("");
  const [flowMap, setFlowMap] = _s(null);
  const [nodeConfigOpen, setNodeConfigOpen] = _s(false);
  const [nodeConfig, setNodeConfig] = _s(null);
  const [nodeConfigBaseline, setNodeConfigBaseline] = _s(null);
  const [nodeConfigLoading, setNodeConfigLoading] = _s(false);
  const [nodeConfigBusy, setNodeConfigBusy] = _s(false);
  const [nodeConfigError, setNodeConfigError] = _s("");
  const [nodeConfigNotice, setNodeConfigNotice] = _s("");
  const [scope, setScope] = _s("all");
  const [sel, setSel] = _s(null);
  const [tick, setTick] = _s(0);
  const [board, setBoard] = _s(null);
  const [tOpen, setTOpen] = _s(0);
  const [tDetail, setTDetail] = _s(null);
  const [tInbox, setTInbox] = _s([]);
  const [myBids, setMyBids] = _s([]);
  const [rels, setRels] = _s(null);
  const [market, setMarket] = _s(null);
  const [tkUpBusy, setTkUpBusy] = _s("");   // 待辦上傳中的 "taskId kind"
  const [tkUpErr, setTkUpErr] = _s({});
  const [actBusy, setActBusy] = _s("");     // 審批動作進行中 "taskId action"
  const [actErr, setActErr] = _s({});
  const [actNote, setActNote] = _s({});
  const [actStage, setActStage] = _s("");
  const decisionPasskeyController = _r(null);
  const decisionFallbackController = _r(null);
  const pageAlive = _r(true);
  const mineTasksRequest = _r(0);
  const allTasksRequest = _r(0);
  const passkeyGuideProbe = _r(false);
  const [rejFor, setRejFor] = _s(null);     // 正在填駁回理由的 taskId
  const [rejText, setRejText] = _s("");
  const [repairs, setRepairs] = _s([]);
  const [repairLoading, setRepairLoading] = _s(false);
  const [repairError, setRepairError] = _s("");
  const [repairScanBusy, setRepairScanBusy] = _s(null);
  const userPermissions = new Set(arr(window.W2_USER && window.W2_USER.permissions));
  const canAdminNodes = userPermissions.has("procurement.workflow.admin");
  const canRepairWorkflows = userPermissions.has("procurement.workflow.repair");
  const canViewAllTasks = [
    "procurement.workflow.global.read",
    "procurement.workflow.global.act",
    "procurement.workflow.global.reassign",
    "procurement.workflow.admin",
    "settings.manage",
    "users.manage",
  ]
    .some((permission) => userPermissions.has(permission));
  const visibleTasks = canViewAllTasks && taskScope === "all" ? arr(allTasks) : tasks;
  const taskListLoading = taskScope === "all" ? allTasksLoading : mineTasksLoading;
  const taskListError = taskScope === "all" ? allTasksError : mineTasksError;
  /* A retained snapshot is read-only until its replacement request succeeds.
     Loading and failure are separate UI states, but both make decisions unsafe. */
  const taskListStale = taskListLoading || !!taskListError;
  const dirtyNodeConfigs = _mm(() => {
    const baselineByKey = {};
    arr(nodeConfigBaseline && nodeConfigBaseline.nodes).forEach((node) => { baselineByKey[node.node_key] = node; });
    return arr(nodeConfig && nodeConfig.nodes).filter((node) => nodeConfigChanged(node, baselineByKey[node.node_key]));
  }, [nodeConfig, nodeConfigBaseline]);

  _e(() => {
    pageAlive.current = true;
    return () => {
      pageAlive.current = false;
      mineTasksRequest.current += 1;
      allTasksRequest.current += 1;
      const operation = decisionPasskeyController.current;
      const fallback = decisionFallbackController.current;
      if (operation && !operation.signal.aborted) operation.abort();
      if (fallback && !fallback.signal.aborted) fallback.abort();
      decisionPasskeyController.current = null;
      decisionFallbackController.current = null;
    };
  }, []);

  const openPasskeyGuide = (task, action, key) => {
    const tenantAtOpen = W2.tenant();
    const actorAtOpen = procurementActorKey(window.W2_USER);
    setActErr((previous) => ({
      ...previous,
      [key]: t("尚未設定 Passkey，請先完成安全設定。剛才的決策沒有執行。"),
    }));
    if (!W2.Guides || !W2.Guides.resolve("passkey-enrollment")) return;
    W2.Guides.open("passkey-enrollment", {
      source: "procurement-decision",
      taskId: task.id,
      action,
      taskTitle: task.node_name || task.instance_title || task.task_no,
      taskNo: task.task_no || task.instance_no,
      onEnrolled: async () => {
        if (!pageAlive.current || W2.tenant() !== tenantAtOpen
            || procurementActorKey(window.W2_USER) !== actorAtOpen) return;
        await reloadTasks();
        setActErr((previous) => { const next = { ...previous }; delete next[key]; return next; });
        setActNote((previous) => ({
          ...previous,
          [key]: t("Passkey 已新增，請重新核對內容，再次點擊通過或確認駁回完成蓋章。"),
        }));
      },
    });
  };

  const switchDecisionToPhone = () => {
    const controller = decisionFallbackController.current;
    if (!controller || controller.signal.aborted) return;
    setActStage("authenticator-hybrid-switch");
    controller.abort();
  };
  const cancelDecisionVerification = () => {
    const controller = decisionPasskeyController.current;
    if (!controller || controller.signal.aborted) return;
    setActStage("authenticator-cancel");
    controller.abort();
  };

  /* 審批一鍵動作:服務端 passkeyRequiredActions 是決策蓋章的唯一前端真相；
     approve / reject 都逐次綁定 task + action，新增 Passkey 後絕不自動重放。 */
  const doTaskAct = async (taskId, action, comment) => {
    const key = taskId + " " + action;
    const decisionTenant = W2.tenant();
    const decisionActor = procurementActorKey(window.W2_USER);
    setActErr((p) => { const n = { ...p }; delete n[key]; return n; });
    setActNote((p) => { const n = { ...p }; delete n[key]; return n; });
    setActStage("");
    setActBusy(key);
    try {
      const task = arr(visibleTasks).find((item) => String(item.id) === String(taskId)) || {};
      if (taskListStale) {
        throw new Error(t("待辦資料尚未重新確認，請先刷新"));
      }
      if (task.canAct === false || task.configurationBlocked) {
        throw new Error(t("任務已凍結，請先修復審批路由"));
      }
      if (task.workflow_key === "legal_contract_review_v1" && task.node_key === "n_sign" && (action === "approve" || action === "submit")) {
        throw new Error(t("合同簽署必須前往法務頁，上傳審查鎖定文件並完成本人確認"));
      }
      const requestBody = comment ? { comment } : {};
      if (taskRequiresPasskey(task, action)) {
        if (!W2.Passkeys || !W2.Passkeys.supported()) {
          const unsupported = new Error(t("此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。"));
          unsupported.code = "passkey_unsupported";
          throw unsupported;
        }
        const operationController = typeof AbortController === "function" ? new AbortController() : null;
        const fallbackController = typeof AbortController === "function" ? new AbortController() : null;
        decisionPasskeyController.current = operationController;
        decisionFallbackController.current = fallbackController;
        try {
          requestBody.step_up_token = await W2.Passkeys.requestStepUp(
            "workflow.task.advance", { task_id: taskId, action }, {
              mode: "platform",
              signal: operationController && operationController.signal,
              fallbackToHybrid: true,
              platformTimeoutMs: 30000,
              fallbackSignal: fallbackController && fallbackController.signal,
              onStatus: setActStage,
            }
          );
        } finally {
          if (decisionPasskeyController.current === operationController) decisionPasskeyController.current = null;
          if (decisionFallbackController.current === fallbackController) decisionFallbackController.current = null;
        }
      }
      /* A completed assertion is still not authority to act after navigation,
         logout or a tenant/actor switch.  Re-check immediately before POST. */
      if (!pageAlive.current || W2.tenant() !== decisionTenant
          || procurementActorKey(window.W2_USER) !== decisionActor) {
        const stale = new Error(t("身份或公司已切換，請重新開啟此操作"));
        stale.code = "decision_context_changed";
        throw stale;
      }
      const res = await W2.fetch("/api/wf/tasks/" + taskId + "/" + action, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || j.error) {
        const error = new Error(j.error || (res.status === 403 ? t("無審批權限或未達要求") : res.status === 422 ? t("必需材料未齊全,無法通過") : t("操作失敗")));
        error.status = res.status; error.data = j;
        throw error;
      }
      if (!pageAlive.current) return;
      setRejFor(null); setRejText("");
      await Promise.all([reloadTasks(),
        W2.json("/api/wf/my-instances").then((d) => setInsts(arr(d && d.instances))).catch(() => {})]);
    } catch (e) {
      if (!pageAlive.current) return;
      const task = arr(visibleTasks).find((item) => String(item.id) === String(taskId)) || { id: taskId };
      if (errorCode(e) === "passkey_not_enrolled") openPasskeyGuide(task, action, key);
      else setActErr((p) => ({ ...p, [key]: e.message || t("操作失敗") }));
    } finally {
      if (pageAlive.current) { setActBusy(""); setActStage(""); }
    }
  };

  /* 待辦節點材料:上傳(POST /api/wf/tasks/:id/artifact/upload)→ 刷新待辦 */
  const loadMineTasks = () => {
    const request = ++mineTasksRequest.current;
    setMineTasksLoading(true); setMineTasksError("");
    return W2.json("/api/wf/inbox?scope=mine&domain=procurement")
      .then((d) => {
        if (pageAlive.current && request === mineTasksRequest.current) setTasks(arr(d && d.tasks));
        return d;
      })
      .catch((e) => {
        if (pageAlive.current && request === mineTasksRequest.current) {
          setMineTasksError((e && e.message) || t("我的待辦載入失敗"));
        }
        throw e;
      })
      .finally(() => {
        if (pageAlive.current && request === mineTasksRequest.current) setMineTasksLoading(false);
      });
  };
  const loadAllTasks = () => {
    const request = ++allTasksRequest.current;
    setAllTasksLoading(true); setAllTasksError("");
    return W2.json("/api/wf/inbox?scope=all&domain=procurement")
      .then((d) => {
        if (pageAlive.current && request === allTasksRequest.current) setAllTasks(arr(d && d.tasks));
        return d;
      })
      .catch((e) => {
        if (pageAlive.current && request === allTasksRequest.current) {
          setAllTasksError((e && e.message) || t("全部待辦載入失敗"));
        }
        throw e;
      })
      .finally(() => {
        if (pageAlive.current && request === allTasksRequest.current) setAllTasksLoading(false);
      });
  };
  const reloadTasks = () => Promise.all([
    loadMineTasks().catch(() => {}),
    canViewAllTasks ? loadAllTasks().catch(() => {}) : Promise.resolve(),
  ]);
  const repairEnvelope = (source) => typeof W2.workflowRepairEnvelope === "function"
    ? W2.workflowRepairEnvelope(source) : null;
  const loadRepairs = () => {
    if (!canRepairWorkflows) { setRepairs([]); return Promise.resolve(); }
    setRepairLoading(true); setRepairError("");
    return W2.json("/api/wf/repairs?limit=50")
      .then((data) => setRepairs(arr(data && (data.repairs || data.cases || data.items))))
      .catch((error) => { setRepairError((error && error.message) || t("修復案件載入失敗")); throw error; })
      .finally(() => setRepairLoading(false));
  };
  const updateRepair = (source) => {
    const next = repairEnvelope(source);
    if (!next) return;
    setRepairs((current) => {
      const index = current.findIndex((item) => {
        const envelope = repairEnvelope(item);
        return envelope && envelope.caseId === next.caseId;
      });
      if (index < 0) return [next.raw, ...current];
      const copy = [...current]; copy[index] = next.raw; return copy;
    });
  };
  const scanRepair = async (instanceId) => {
    if (!canRepairWorkflows || repairScanBusy || !Number.isInteger(Number(instanceId))) return;
    setRepairScanBusy(Number(instanceId)); setRepairError("");
    try {
      const data = await W2.post(`/api/wf/instances/${encodeURIComponent(instanceId)}/repair-scan`, {
        reason: "user_requested_from_procurement",
      });
      updateRepair(data);
      await loadRepairs();
    } catch (error) {
      setRepairError((error && error.message) || t("修復案件載入失敗"));
    } finally { setRepairScanBusy(null); }
  };
  const loadNodeConfig = (key = flowKey) => {
    if (!key || !canAdminNodes) return Promise.resolve(null);
    setNodeConfigLoading(true); setNodeConfigError(""); setNodeConfigNotice("");
    return W2.json("/api/wf/workflows/" + key + "/nodes")
      .then((data) => { const loaded = data || {}; setNodeConfig(loaded); setNodeConfigBaseline(loaded); return loaded; })
      .catch((e) => { setNodeConfig(null); setNodeConfigBaseline(null); setNodeConfigError((e && e.message) || t("節點責任載入失敗")); throw e; })
      .finally(() => setNodeConfigLoading(false));
  };
  const saveNodeConfig = async () => {
    if (!flowKey || !nodeConfig || nodeConfigBusy) return;
    if (!dirtyNodeConfigs.length) { setNodeConfigNotice(t("沒有需要保存的變更")); return; }
    setNodeConfigBusy(true); setNodeConfigError(""); setNodeConfigNotice("");
    try {
      const baselineByKey = {};
      arr(nodeConfigBaseline && nodeConfigBaseline.nodes).forEach((node) => { baselineByKey[node.node_key] = node; });
      const nodes = dirtyNodeConfigs.map((node) => nodeConfigPayload(node, baselineByKey[node.node_key]));
      const baseVersion = Number(
        nodeConfigBaseline && nodeConfigBaseline.definition && nodeConfigBaseline.definition.base_version != null
          ? nodeConfigBaseline.definition.base_version
          : nodeConfigBaseline && nodeConfigBaseline.workflow && nodeConfigBaseline.workflow.version
      );
      if (!Number.isInteger(baseVersion) || baseVersion < 1) {
        throw new Error(t("節點配置版本缺失，請重新載入後再保存"));
      }
      const response = await W2.fetch("/api/wf/workflows/" + flowKey + "/nodes", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nodes, base_version: baseVersion }),
      });
      const data = await response.json().catch(() => ({}));
      if (response.status === 202 || data.need_confirm) {
        const exactArguments = data && data.arguments
          ? data.arguments
          : { nodes, base_version: baseVersion };
        const toolArguments = {
          workflow: flowKey,
          "base-version": Number(
            exactArguments.base_version != null
              ? exactArguments.base_version
              : baseVersion
          ),
          nodes: exactArguments.nodes || nodes,
        };
        if (exactArguments.reason) toolArguments.reason = exactArguments.reason;
        const confirmationPrompt = [
          "請為我建立工作流程節點配置的 Passkey 待確認操作卡。",
          "只能調用 wf node set；下列 JSON 已按工具參數名完成無損映射，值不得改寫、補推測或改用其他指令：",
          JSON.stringify(toolArguments),
          "這次只完成正式預驗，尚未保存；請不要聲稱已保存，等待我在操作卡完成 Passkey 確認。",
        ].join("\n");
        if (window.openUnifiedAgent) {
          window.openUnifiedAgent(confirmationPrompt, { autoAsk: true });
        } else {
          window.dispatchEvent(new CustomEvent("company-secretary-open", {
            detail: { prompt: confirmationPrompt, autoAsk: true },
          }));
        }
        setNodeConfigNotice(t("完整驗證已通過，尚未保存；請在 AI 秘書的 Passkey 操作卡確認"));
        return;
      }
      if (!response.ok || data.error) throw new Error(data.error || t("節點責任保存失敗"));
      await Promise.all([
        loadNodeConfig(flowKey),
        W2.json("/api/wf/workflows/" + flowKey + "/map").then((map) => setFlowMap(map || {})),
        reloadTasks(),
      ]);
      setNodeConfigNotice(t("節點責任已保存"));
    } catch (e) {
      setNodeConfigError((e && e.message) || t("節點責任保存失敗"));
    } finally { setNodeConfigBusy(false); }
  };
  const uploadTaskMaterial = async (taskId, kind, file) => {
    if (!file) return;
    const key = taskId + " " + kind;
    setTkUpErr((p) => { const n = { ...p }; delete n[key]; return n; });
    setTkUpBusy(key);
    try {
      const task = arr(visibleTasks).find((item) => String(item.id) === String(taskId)) || {};
      if (taskListStale) {
        throw new Error(t("待辦資料尚未重新確認，請先刷新"));
      }
      if (task.canAct === false || task.configurationBlocked) {
        throw new Error(t("任務已凍結，請先修復審批路由"));
      }
      const fd = new FormData();
      fd.append("file", file, file.name);
      fd.append("kind", kind);
      const res = await W2.fetch("/api/wf/tasks/" + taskId + "/artifact/upload", { method: "POST", body: fd });
      const j = await res.json().catch(() => ({}));
      if (!res.ok || !j.ok) throw new Error(j.error || (res.status === 403 ? t("無權上傳") : res.status === 400 ? t("上傳失敗:超過 15MB 上限") : t("上傳失敗")));
      await reloadTasks();
    } catch (e) {
      setTkUpErr((p) => ({ ...p, [key]: e.message || t("上傳失敗") }));
    } finally { setTkUpBusy(""); }
  };
  const downloadArtifact = async (aid, fname) => {
    try {
      const res = await W2.fetch("/api/wf/artifacts/" + aid + "/download");
      if (!res.ok) throw new Error(t("下載失敗"));
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a"); a.href = url; a.download = fname || ("artifact-" + aid); a.click();
      setTimeout(() => URL.revokeObjectURL(url), 4000);
    } catch (e) {}
  };

  _e(() => {
    loadMineTasks().catch(() => {});
    W2.json("/api/wf/my-instances").then((d) => setInsts(arr(d && d.instances))).catch(() => setInsts([]));
    W2.json("/api/wf/workflows").then((d) => {
      const list = arr(d && d.workflows);
      setFlows(list);
      setFlowKey((k) => (k && list.some((w) => w.workflow_key === k)) ? k : ((list[0] && list[0].workflow_key) || ""));
    }).catch(() => setFlows([]));
  }, [tick]);

  _e(() => {
    if (canRepairWorkflows) loadRepairs().catch(() => {});
  }, [tick, canRepairWorkflows]);

  /* Smart, one-time contextual invitation.  Merely opening the guide never
     starts WebAuthn and never advances a task. */
  _e(() => {
    const candidate = tasks.find(task => task && task.canAct !== false
      && !task.configurationBlocked && taskPasskeyActions(task).length > 0);
    if (mineTasksLoading || mineTasksError || !candidate || passkeyGuideProbe.current || !W2.Passkeys || !W2.Passkeys.supported()
        || !W2.Guides || !W2.Guides.resolve("passkey-enrollment")) return;
    const actor = window.W2_USER || {};
    const tenantAtRequest = W2.tenant();
    const actorAtRequest = procurementActorKey(actor);
    const guideKey = ["w2-guide", "passkey-enrollment-v1", tenantAtRequest, actorAtRequest].join(":");
    try { if (sessionStorage.getItem(guideKey)) return; } catch (error) {}
    let cancelled = false;
    let settled = false;
    passkeyGuideProbe.current = true;
    W2.Passkeys.list().then(items => {
      settled = true;
      if (cancelled || !pageAlive.current || W2.tenant() !== tenantAtRequest
          || procurementActorKey(window.W2_USER) !== actorAtRequest) return;
      if (arr(items).length) return;
      try { sessionStorage.setItem(guideKey, "shown"); } catch (error) {}
      W2.Guides.open("passkey-enrollment", {
        source: "procurement-context",
        taskTitle: candidate.node_name || candidate.instance_title || candidate.task_no,
        taskNo: candidate.task_no || candidate.instance_no,
        onEnrolled: () => {
          if (!pageAlive.current || W2.tenant() !== tenantAtRequest
              || procurementActorKey(window.W2_USER) !== actorAtRequest) return;
          return reloadTasks();
        },
      });
    }).catch(() => {
      settled = true;
      if (!cancelled) passkeyGuideProbe.current = false;
    });
    return () => {
      cancelled = true;
      if (!settled) passkeyGuideProbe.current = false;
    };
  }, [tasks, mineTasksLoading, mineTasksError]);

  _e(() => {
    if (!canViewAllTasks) {
      if (taskScope !== "mine") {
        setMineTasksLoading(true);
        setTaskScope("mine");
        loadMineTasks().catch(() => {});
      }
      return;
    }
    if (taskScope === "all") loadAllTasks().catch(() => {});
  }, [taskScope, tick, canViewAllTasks]);

  _e(() => {
    W2.json("/api/tender/board").then((d) => setBoard(arr(d && d.notices))).catch(() => setBoard([]));
    W2.json("/api/tender/inbox").then((d) => setTInbox(arr(d && d.invites))).catch(() => setTInbox([]));
    W2.json("/api/tender/my-bids").then((d) => setMyBids(arr(d && d.bids))).catch(() => setMyBids([]));
    W2.json("/api/tender/market").then((d) => setMarket(arr(d && d.market))).catch(() => setMarket([]));
    W2.json("/api/b2b/relations").then((d) => setRels(arr(d && d.relations))).catch(() => setRels([]));
  }, [tick]);

  _e(() => {
    if (!tOpen) { setTDetail(null); return; }
    let on = true;
    setTDetail(null);
    W2.json("/api/tender/notices/" + tOpen).then((x) => { if (on) setTDetail(x || {}); }).catch(() => { if (on) setTDetail({}); });
    return () => { on = false; };
  }, [tOpen, tick]);

  _e(() => {
    if (!flowKey) { setFlowMap(null); return; }
    let on = true;
    setFlowMap(null);
    W2.json("/api/wf/workflows/" + flowKey + "/map").then((m) => { if (on) setFlowMap(m || {}); }).catch(() => { if (on) setFlowMap({}); });
    return () => { on = false; };
  }, [flowKey, tick]);

  _e(() => {
    setNodeConfig(null); setNodeConfigBaseline(null); setNodeConfigError(""); setNodeConfigNotice("");
    if (!nodeConfigOpen || !flowKey || !canAdminNodes) return;
    loadNodeConfig(flowKey).catch(() => {});
  }, [nodeConfigOpen, flowKey, canAdminNodes]);

  _e(() => {
    const h = (e) => { if (e.key === "Escape") setSel(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  const wfName = (key) => {
    const w = arr(flows).find((x) => x.workflow_key === key);
    return (w && w.name) || key || "—";
  };

  const running = insts.filter((x) => x.status === "running" || x.status === "waiting");
  const closed = insts.filter((x) => x.status === "completed");
  const dead = insts.filter((x) => x.status === "rejected" || x.status === "cancelled");
  const overdueTasks = tasks.filter((x) => isOverdue(x.due_at));
  const activeRels = arr(rels).filter((r) => r && r.status === "active").length;
  const activeRepairs = repairs.filter((item) => {
    const envelope = repairEnvelope(item);
    return envelope && !["resolved", "cancelled"].includes(String(envelope.repairCase.status || "").toLowerCase());
  });

  const shown = _mm(() => {
    let list = insts;
    if (scope === "running") list = running;
    if (scope === "completed") list = closed;
    if (scope === "rejected") list = list.filter((x) => x.status === "rejected");
    return list;
  }, [insts, scope]);

  /* 流程拓撲:按階段分組 */
  const mapNodes = arr(flowMap && flowMap.nodes);
  const mapStages = arr(flowMap && flowMap.stages);
  const nodeByKey = _mm(() => {
    const m = {};
    mapNodes.forEach((n) => { if (n && n.node_key) m[n.node_key] = n; });
    return m;
  }, [flowMap]);
  const todoByNode = _mm(() => {
    const m = {};
    tasks.filter((x) => x.workflow_key === flowKey).forEach((x) => { m[x.node_key] = (m[x.node_key] || 0) + 1; });
    return m;
  }, [tasks, flowKey]);
  const groups = _mm(() => {
    if (!mapNodes.length) return [];
    const sorted = [...mapNodes].sort((a, b) => num(a.step_no) - num(b.step_no));
    const gs = mapStages.map((s) => ({ key: s.key, name: s.name, nodes: sorted.filter((n) => n.stage_key === s.key) })).filter((g) => g.nodes.length);
    const known = new Set(gs.map((g) => g.key));
    const loose = sorted.filter((n) => !known.has(n.stage_key));
    if (loose.length) gs.push({ key: "_loose", name: gs.length ? t("未分組") : "", nodes: loose });
    return gs;
  }, [flowMap, mapStages]);

  let nodeCounter = 0;

  return (
    <>
      <style>{TOPO_CSS}</style>
      <Folio no="10" en="PROCUREMENT" title={t("採購招標")}
        sub={t("流程化採購協作 · 招標評審 · 全程留痕") + " · " + t("待辦 {a} 條 · 進行中 {b} 條 · 頁面只讀,操作交秘書", { a: tasks.length, b: running.length })}
        right={<>
          <B icon="refresh" onClick={() => {
            setSel(null);
            setMineTasksLoading(true);
            if (canViewAllTasks) setAllTasksLoading(true);
            setTick((x) => x + 1);
          }}>{t("刷新")}</B>
          <B icon="search" onClick={() => ask(t("幫我做一輪詢價:請追問物資名稱、數量和意向供應商,整理成詢價單並跟進報價"))}>{t("詢價")}</B>
          <B icon="plus" onClick={() => W2.openBusinessAction("erp_purchase_create")}>{t("發起流程")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(t("看看採購招標現在的待辦、流程阻塞和權限缺口,按優先級給我可執行的下一步"))}>{t("問秘書")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={t("我的待辦")} value={tasks.length} unit={t("條")} red={tasks.length > 0} delay={0}
          foot={overdueTasks.length
            ? <T tone="bad" dot>{t("{n} 條已逾期", { n: overdueTasks.length })}</T>
            : <span className="muted" style={{ fontSize: 11.5 }}>{t("無逾期")}</span>}/>
        <Kpi label={t("進行中流程")} value={running.length} unit={t("條")} delay={.05}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("招標 · 採購 · 審批鏈")}</span>}/>
        <Kpi label={t("已閉環")} value={closed.length} unit={t("條")} delay={.1}
          foot={dead.length
            ? <span className="muted" style={{ fontSize: 11.5 }}>{t("含已駁回 / 已取消 {n} 條", { n: dead.length })}</span>
            : <span className="muted" style={{ fontSize: 11.5 }}>{t("全流水可追溯")}</span>}/>
        <Kpi label={t("流程模板")} value={arr(flows).length} unit={t("個")} delay={.15}
          foot={<T tone="plain">WORKFLOW</T>}/>
      </div>

      {/* A · 本人待辦 / 管理員明確切換全公司待辦 */}
      <Band no="A" title={t(taskScope === "all" ? "全部待辦" : "我的待辦")} sub={t("限時待辦優先 · 推進交秘書")} delay={.1}
        right={(canViewAllTasks || visibleTasks.length) ? <div className="row g8 wrap">
          {canViewAllTasks ? <div className="seg">
            <button className={taskScope === "mine" ? "on" : ""} onClick={() => {
              setMineTasksLoading(true);
              setTaskScope("mine");
              loadMineTasks().catch(() => {});
            }}>{t("我的待辦")}</button>
            <button className={taskScope === "all" ? "on" : ""} onClick={() => {
              setAllTasksLoading(true);
              if (taskScope === "all") loadAllTasks().catch(() => {});
              else setTaskScope("all");
            }}>{t("全部待辦")}</button>
          </div> : null}
          {visibleTasks.length ? <B size="sm" icon="sparkle" disabled={taskListStale} onClick={() => ask(t(taskScope === "all" ? "把全公司的採購待辦按緊急程度、受派人和流程排序,逐條給我處理建議,經我確認後推進" : "把我的採購待辦按緊急程度排序,逐條給我處理建議,經我確認後推進"))}>{t("全部交秘書梳理")}</B> : null}
        </div> : null}>
        {taskListLoading && visibleTasks.length ? <div className="row g8 wrap" role="status" aria-live="polite" style={{ padding: "9px 0", borderTop: "2px solid var(--rule)", alignItems: "center" }}>
          <T tone="plain" dot>{t("待辦正在更新")}</T>
          <span className="muted" style={{ flex: 1, fontSize: 11.5 }}>{t("正在重新確認最新狀態，更新完成前操作已暫停。")}</span>
        </div> : taskListError && visibleTasks.length ? <div className="row g8 wrap" style={{ padding: "9px 0", borderTop: "2px solid var(--red)", alignItems: "center" }}>
          <T tone="bad" dot>{t(taskScope === "all" ? "全部待辦載入失敗" : "我的待辦載入失敗")}</T>
          <span className="muted" style={{ flex: 1, fontSize: 11.5 }}>{taskListError}</span>
          <B size="sm" icon="refresh" onClick={() => (taskScope === "all" ? loadAllTasks() : loadMineTasks()).catch(() => {})}>{t("刷新")}</B>
        </div> : null}
        {visibleTasks.length ? (
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {visibleTasks.map((task, i) => {
              const od = isOverdue(task.due_at);
              const kinds = arr(task.artifact_kinds);
              const doneKinds = arr(task.uploaded_kinds);
              const allDone = kinds.length > 0 && kinds.every((k) => doneKinds.indexOf(k) >= 0);
              const assigneeLabel = task.assignee_name || task.assignee_username || (task.assignee_user_id ? "#" + task.assignee_user_id : task.configurationBlocked ? t("待配置上級／同級審批人") : t("未指派"));
              const occupants = taskAssignmentOccupants(task);
              const occupantLabel = taskOccupantsLabel(task);
              const assignmentVacant = task.assignmentVacant === true || task.assignment_vacant === true;
              const responsibilityLabel = responsibilityText(task) || dynamicResponsibilityText(task);
              const dedicatedLegalSign = task.workflow_key === "legal_contract_review_v1" && task.node_key === "n_sign";
              const taskRouteBlocked = task.canAct === false || task.configurationBlocked;
              const taskBlocked = taskRouteBlocked || taskListStale;
              const activeDecisionKey = [task.id + " approve", task.id + " reject"].find(key => actBusy === key) || "";
              const decisionAuthenticatorActive = !!activeDecisionKey && ["authenticator", "authenticator-platform", "authenticator-hybrid-timeout", "authenticator-hybrid-switch"].includes(actStage);
              return (
                <div key={task.id || i} className="col g8" style={{ borderBottom: "1px solid var(--hair-soft)", padding: "12px 0" }}>
                  <div className="row g8 wrap" style={{ alignItems: "center" }}>
                    <span className="lr-idx" style={{ flexShrink: 0 }}>{pad2(i + 1)}</span>
                    <div className="col g4" style={{ flex: 1.5, minWidth: 160 }}>
                      <span className="row g8 wrap" style={{ fontWeight: 650, fontSize: 13.5 }}>
                        {task.node_name || task.node_key || "—"}
                        <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".1em" }}>{t("步 {n}", { n: task.step_no == null ? "—" : task.step_no })}</span>
                        {kinds.length ? (allDone ? <T tone="ok" dot>{t("材料齊全")}</T> : <T tone="warn" dot>{t("缺 {n} 項材料", { n: kinds.length - doneKinds.length })}</T>) : null}
                        {task.viewerSelfApprovalBlocked || task.selfApprovalBlocked ? <T tone="bad" dot>{t("你不可自審")}</T> : null}
                        {task.assignmentSource === "management_escalation" ? <T tone="warn" dot>{t("已上送管理層")}</T> : null}
                        {task.assignmentSource === "peer_equivalent" ? <T tone="plain" dot>{t("同級覆核")}</T> : null}
                        {task.assignmentSource === "routing_blocked" ? <T tone="bad" dot>{t("審批路由受阻")}</T> : null}
                        {task.assignmentSource === "reconciliation_required" ? <T tone="bad" dot>{t("需要對賬補審")}</T> : null}
                        {taskPasskeyActions(task).length ? <T tone="plain" dot>{t("需要 Passkey 蓋章")}</T> : null}
                      </span>
                      <span className="muted" style={{ fontSize: 12 }}>{task.instance_title || "—"}<span className="num"> · {task.instance_no || "—"}</span></span>
                      <span style={{ fontSize: 11, color: responsibilityLabel ? "var(--ink-2)" : "var(--ink-4)" }}>
                        {t("責任部門 / 職位")} · {responsibilityLabel || t("未綁定部門與職位")}
                      </span>
                      <span className="muted" style={{ fontSize: 11 }}>
                        {t("受派人")} · {assigneeLabel}
                        {task.assignee_name && task.assignee_username ? <span className="mono"> @{task.assignee_username}</span> : null}
                      </span>
                      {(task.positionPool || task.assignee_role || assignmentVacant) ? <span style={{ fontSize: 11, color: assignmentVacant || !occupants.length ? "var(--red)" : "var(--ink-2)" }}>
                        {t("當前在崗")} · {occupantLabel || t("該職位暫無在崗人員")}
                        {task.assignmentOccupantCount != null && Number(task.assignmentOccupantCount) > occupants.length
                          ? <span className="num"> · {Number(task.assignmentOccupantCount)} PEOPLE</span> : null}
                      </span> : null}
                      {task.configurationBlocked && task.blockedReason ? <span style={{ fontSize: 11, color: "var(--red)", fontWeight: 650 }}>
                        {task.blockedReason}
                      </span> : null}
                    </div>
                    <T tone={KIND_TONE[task.node_kind] || "plain"}>{kindLabel(task.node_kind)}</T>
                    <span className="num" style={{ fontSize: 11.5, width: 150, flexShrink: 0, color: od ? "var(--red)" : "var(--ink-3)", textAlign: "right" }}>
                      {task.due_at ? t("限 {d}", { d: wfDate(task.due_at) }) + (od ? " · " + t("已逾期") : "") : "—"}
                    </span>
                    {taskRouteBlocked && canRepairWorkflows && task.instance_id ? <B size="sm" kind="red" icon="shield"
                      disabled={repairScanBusy === Number(task.instance_id)} onClick={() => scanRepair(task.instance_id)}>
                      {repairScanBusy === Number(task.instance_id) ? t("掃描中…") : t("安全掃描")}
                    </B> : null}
                    {/* 決策類節點(審批/簽章/外部留痕,不填表)給一鍵通過/駁回;填報類仍走秘書 */}
                    {dedicatedLegalSign ? (
                      <B size="sm" kind="primary" icon="user" disabled={taskBlocked}
                        onClick={() => { location.hash = "#/legal"; }}>{t("前往法務本人簽署")}</B>
                    ) : ["approval", "signoff", "external_placeholder"].indexOf(task.node_kind) >= 0 ? (
                      <div className="row g4" style={{ flexShrink: 0 }}>
                        <B size="sm" kind="primary" icon="check" disabled={!!actBusy || taskBlocked}
                          onClick={() => doTaskAct(task.id, "approve")}>{actBusy === task.id + " approve" ? t("處理中…") : t("通過")}</B>
                        <B size="sm" kind="red" icon="x" disabled={!!actBusy || taskBlocked}
                          onClick={() => { setRejFor(rejFor === task.id ? null : task.id); setRejText(""); }}>{t("駁回")}</B>
                        <B size="sm" icon="sparkle" disabled={taskBlocked} title={t("交秘書研判")}
                          onClick={() => ask(t("推進待辦「{node}」(流程「{title}」,單號 {no}):請先核對必需材料和上下文,建議通過還是駁回,經我確認後執行", { node: task.node_name || task.node_key || "—", title: task.instance_title || "—", no: task.instance_no || "—" }))}/>
                      </div>
                    ) : (
                      <B size="sm" icon="check" disabled={taskBlocked} onClick={() => ask(t("推進待辦「{node}」(流程「{title}」,單號 {no}):請先核對必需材料和上下文,建議通過還是駁回,經我確認後執行", { node: task.node_name || task.node_key || "—", title: task.instance_title || "—", no: task.instance_no || "—" }))}>{t("推進")}</B>
                    )}
                  </div>
                  {rejFor === task.id ? (
                    <div className="row g8 wrap" style={{ marginLeft: 30, alignItems: "center" }}>
                      <input className="field boxed" style={{ flex: 1, minWidth: 200, height: 32, fontSize: 12.5 }} value={rejText}
                        placeholder={t("駁回理由(選填,退回發起人時一併帶上)")} onChange={(e) => setRejText(e.target.value)}
                        disabled={taskBlocked}
                        onKeyDown={(e) => { if (e.key === "Enter" && !actBusy && !taskBlocked) doTaskAct(task.id, "reject", rejText.trim()); }}/>
                      <B size="sm" kind="red" icon="check" disabled={!!actBusy || taskBlocked} onClick={() => doTaskAct(task.id, "reject", rejText.trim())}>
                        {actBusy === task.id + " reject" ? t("處理中…") : t("確認駁回")}
                      </B>
                      <B size="sm" onClick={() => { setRejFor(null); setRejText(""); }}>{t("取消")}</B>
                    </div>
                  ) : null}
                  {(actErr[task.id + " approve"] || actErr[task.id + " reject"]) ? (
                    <span style={{ marginLeft: 30, fontSize: 10.5, color: "var(--red)" }}>{actErr[task.id + " approve"] || actErr[task.id + " reject"]}</span>
                  ) : null}
                  {(actNote[task.id + " approve"] || actNote[task.id + " reject"]) ? (
                    <span role="status" style={{ marginLeft: 30, fontSize: 10.5, color: "var(--ok)", fontWeight: 650 }}>{actNote[task.id + " approve"] || actNote[task.id + " reject"]}</span>
                  ) : null}
                  {activeDecisionKey && actStage ? <div className="row g8 wrap" style={{ marginLeft: 30 }} role="status" aria-live="polite">
                    <span className="muted" style={{ fontSize: 11.5 }}>{actStage === "options" ? t("正在取得安全挑戰…") : t("需要 Passkey 蓋章")}</span>
                    {actStage === "authenticator-platform" ? <B size="sm" onClick={switchDecisionToPhone}>{t("切換至手機 Passkey QR")}</B> : null}
                    {decisionAuthenticatorActive ? <B size="sm" onClick={cancelDecisionVerification}>{t("取消驗證")}</B> : null}
                  </div> : null}
                  {kinds.length ? (
                    <div className="row g8 wrap" style={{ marginLeft: 30, alignItems: "center" }}>
                      <span className="label dim" style={{ fontSize: 8, flexShrink: 0 }}>{t("節點材料")}</span>
                      {kinds.map((k) => {
                        const key = task.id + " " + k;
                        const busy = tkUpBusy === key;
                        const has = doneKinds.indexOf(k) >= 0;
                        return (
                          <label key={k} className={"btn sm" + (has ? " ghost" : "")} title={has ? t("已上傳,可重新上傳更新") : t("上傳該材料")}
                            style={{ cursor: busy ? "default" : "pointer", opacity: busy ? .6 : 1, borderColor: has ? "var(--ok)" : undefined }}>
                            <I name={busy ? "refresh" : has ? "check" : "outbound"} size={11} color={has ? "var(--ok)" : undefined}/>
                            {artLabel(k)}{busy ? " · " + t("上傳中…") : has ? " ✓" : ""}
                            <input type="file" style={{ display: "none" }} disabled={busy || taskBlocked}
                              onChange={(ev) => { const f = ev.target.files && ev.target.files[0]; ev.target.value = ""; if (f) uploadTaskMaterial(task.id, k, f); }}/>
                          </label>
                        );
                      })}
                      {kinds.map((k) => tkUpErr[task.id + " " + k]
                        ? <span key={"e" + k} style={{ fontSize: 10.5, color: "var(--red)", width: "100%" }}>{artLabel(k)}:{tkUpErr[task.id + " " + k]}</span> : null)}
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        ) : taskScope === "all" && allTasksLoading ? (
          <div className="muted" style={{ padding: "18px 0", fontSize: 13 }}>{t("載入中…")}</div>
        ) : taskScope === "all" && allTasksError ? (
          <EM icon="alert" title={t("全部待辦載入失敗")} sub={allTasksError} action={<B size="sm" icon="refresh" onClick={() => loadAllTasks().catch(() => {})}>{t("刷新")}</B>}/>
        ) : taskScope === "mine" && mineTasksLoading ? (
          <div className="muted" style={{ padding: "18px 0", fontSize: 13 }}>{t("載入中…")}</div>
        ) : taskScope === "mine" && mineTasksError ? (
          <EM icon="alert" title={t("我的待辦載入失敗")} sub={mineTasksError} action={<B size="sm" icon="refresh" onClick={() => loadMineTasks().catch(() => {})}>{t("刷新")}</B>}/>
        ) : (
          <EM icon="checkCircle" title={t(taskScope === "all" ? "全公司目前沒有待處理任務" : "沒有待你處理的任務")} sub={taskScope === "all" ? null : t("流程走到你這一步時,待辦會第一時間出現在這裡。")}/>
        )}
      </Band>

      {/* B · 採購 / 招標流水 */}
      <Band no="B" title={t("採購 / 招標流水")} sub={t("我發起的流程 · 點行看流轉")} delay={.15}
        right={<div className="seg">
          {[["all", "全部"], ["running", "進行中"], ["completed", "已閉環"], ["rejected", "已駁回"]].map(([id, label]) => (
            <button key={id} className={scope === id ? "on" : ""} onClick={() => { setScope(id); setSel(null); }}>{t(label)}</button>
          ))}
        </div>}>
        {insts.length ? (
          <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
            <div style={{ flex: 1, minWidth: 0, overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th>{t("單號")}</th><th>{t("事由")}</th><th>{t("流程")}</th><th>{t("狀態")}</th><th>{t("當前節點")}</th><th>{t("發起時間")}</th><th style={{ width: 190 }}>{t("業務全鏈")}</th>
                </tr></thead>
                <tbody>
                  {shown.map((it, i) => {
                    const entityRef = workflowBusinessRef(it);
                    return (
                    <tr key={it.id || i} className={sel && sel.id === it.id ? "on" : ""} style={{ cursor: "pointer" }} onClick={() => setSel(it)}>
                      <td><span className="num" style={{ fontWeight: 600, fontSize: 12 }}>{it.instance_no || "—"}</span></td>
                      <td><span style={{ fontWeight: 650 }}>{it.title || "—"}</span></td>
                      <td className="muted" style={{ fontSize: 12.5 }}>{wfName(it.workflow_key)}</td>
                      <td>{statTag(it.status)}</td>
                      <td><span className="num muted" style={{ fontSize: 11.5 }}>{it.current_node_key || "—"}</span></td>
                      <td><span className="num muted" style={{ fontSize: 11.5 }}>{wfDate(it.created_at)}</span></td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <div className="row g4 wrap">
                          {entityRef && <B size="sm" icon="layers" onClick={() => W2.openEntity(entityRef, { tab: "workflow", node_key: it.current_node_key })}>{t("查看全鏈")}</B>}
                          <B size="sm" icon="clock" onClick={() => ask(t("查一下流程「{title}」(單號 {no})的當前進度、卡在哪個節點,需要催辦就幫我催辦", { title: it.title || "—", no: it.instance_no || "—" }))}>{t("查進度")}</B>
                        </div>
                      </td>
                    </tr>
                    );
                  })}
                </tbody>
              </table>
              {!shown.length && <EM icon="search" title={t("當前篩選下沒有流程")}/>}
            </div>
            {sel && <InstDrawer item={sel} wfName={wfName} inbox={tasks} onClose={() => setSel(null)}/>}
          </div>
        ) : (
          <EM icon="doc" title={t("還沒有採購 / 招標流水")} sub={t("對秘書說「發起採購」,第一條流水就從這裡開始。")}
            action={<B icon="plus" onClick={() => W2.openBusinessAction("erp_purchase_create")}>{t("發起第一個流程")}</B>}/>
        )}
      </Band>

      {/* C · 流程模板拓撲 */}
      <Band no="C" title={t("流程模板拓撲")}
        sub={mapNodes.length ? t("{s} 階段 · {n} 節點 · 指派與流轉規則", { s: mapStages.length, n: mapNodes.length }) : ""}
        delay={.2}
        right={flowKey ? <div className="row g8 wrap">
          {canAdminNodes ? <B size="sm" icon="gear" onClick={() => setNodeConfigOpen((open) => !open)}>{t(nodeConfigOpen ? "收起配置" : "配置節點責任")}</B> : null}
          <B size="sm" icon="sparkle" onClick={() => ask(t("結合流程「{wf}」的拓撲,檢查阻塞節點、權限缺口和外部留痕風險,給我下一步可執行動作", { wf: wfName(flowKey) }))}>{t("秘書研判")}</B>
        </div> : null}>
        {flows == null ? (
          <div className="muted" style={{ fontSize: 12.5, padding: "20px 0" }}>{t("載入中…")}</div>
        ) : !arr(flows).length ? (
          <EM icon="layers" title={t("尚無流程模板")} sub={t("流程模板由系統預置或管理員配置。先問秘書採購流程怎麼走也可以。")}
            action={<B icon="sparkle" onClick={() => ask(t("看看採購招標現在的待辦、流程阻塞和權限缺口,按優先級給我可執行的下一步"))}>{t("問秘書")}</B>}/>
        ) : (
          <>
            <div className="row g6 wrap" style={{ marginBottom: 16 }}>
              {arr(flows).map((w) => (
                <button key={w.workflow_key} className={"chip" + (flowKey === w.workflow_key ? " on" : "")} onClick={() => setFlowKey(w.workflow_key)}>
                  {w.name || w.workflow_key}
                </button>
              ))}
            </div>
            {flowMap == null ? (
              <div className="muted" style={{ fontSize: 12.5, padding: "12px 0" }}>{t("載入中…")}</div>
            ) : !mapNodes.length ? (
              <EM icon="layers" title={t("此流程暫無節點定義")}/>
            ) : (
              <>
              <WfTopo nodes={mapNodes} todoByNode={todoByNode}
                commandContext={{ workflow: { key: flowKey } }}
                onAsk={(n) => ask(t("分析流程「{wf}」第 {step} 步「{node}」:處理要點、指派與權限規則、必需材料和下一步流轉", { wf: wfName(flowKey), step: n.step_no == null ? "—" : n.step_no, node: n.name || n.node_key || "—" }))}/>
              <LB dim style={{ padding: "20px 0 6px", borderBottom: "1px solid var(--hair)", marginTop: 10 }}>{t("節點規則明細")}</LB>
              {groups.map((g) => (
                <div key={g.key} style={{ marginBottom: 6 }}>
                  {g.name ? <LB dim style={{ padding: "12px 0 6px", borderBottom: "1px solid var(--hair)" }}>{g.name}</LB> : null}
                  {g.nodes.map((n) => {
                    nodeCounter += 1;
                    const next = n.on_approve_next ? nodeByKey[n.on_approve_next] : null;
                    const todo = todoByNode[n.node_key] || 0;
                    const arts = arr(n.artifactKinds);
                    return (
                      <div key={n.node_key || nodeCounter} className="ledger-row">
                        <span className="lr-idx">{pad2(num(n.step_no) || nodeCounter)}</span>
                        <div className="col g4" style={{ flex: 1.7, minWidth: 0 }}>
                          <span className="row g8 wrap" style={{ fontWeight: 650, fontSize: 13 }}>
                            {n.name || n.node_key || "—"}
                            {todo > 0 && <T tone="redinv">{t("待辦 {n}", { n: todo })}</T>}
                            {arr(n.actions).length > 0 && <T tone="plain">{t("已連結 {n} 項指令", { n: arr(n.actions).length })}</T>}
                          </span>
                          <span className="muted num" style={{ fontSize: 10.5 }}>
                            {n.node_key || "—"}{" → "}{next ? (next.name || next.node_key) : t("流程完成")}
                          </span>
                        </div>
                        <T tone={KIND_TONE[n.node_kind] || "plain"}>{kindLabel(n.node_kind)}</T>
                        <span className="ink2" style={{ fontSize: 12, flex: 1, minWidth: 0 }}>{assignText(n)}</span>
                        <span className="col g4" style={{ width: 170, flexShrink: 0, alignItems: "flex-end" }}>
                          {n.required_permission
                            ? (n.permissionSatisfied === false
                              ? <T tone="bad" dot>{t("缺權限")}</T>
                              : <span className="mono muted" style={{ fontSize: 9.5, wordBreak: "break-all", textAlign: "right" }}>{n.required_permission}</span>)
                            : null}
                          <span className="mono muted" style={{ fontSize: 9.5 }}>
                            {[num(n.quorum) > 1 ? t("會簽 {n}", { n: n.quorum }) : "", arts.length ? t("材料 {n}", { n: arts.length }) : "", n.sla_hours ? t("SLA {n} 小時", { n: n.sla_hours }) : ""].filter(Boolean).join(" · ")}
                          </span>
                        </span>
                        <div className="row g4" style={{ flexShrink: 0 }}>
                          {arr(n.actions)[0] ? <B size="sm" kind="primary" icon="terminal"
                            onClick={() => openNodeCommand(n, arr(n.actions)[0], { workflow: { key: flowKey } })}>
                            {t("節點指令")}
                          </B> : null}
                          <B size="sm" icon="sparkle" onClick={() => ask(t("分析流程「{wf}」第 {step} 步「{node}」:處理要點、指派與權限規則、必需材料和下一步流轉", { wf: wfName(flowKey), step: n.step_no == null ? "—" : n.step_no, node: n.name || n.node_key || "—" }))}/>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
              </>
            )}
          </>
        )}
        {nodeConfigOpen && canAdminNodes ? (
          nodeConfigLoading && !nodeConfig ? (
            <div className="muted" style={{ fontSize: 12.5, padding: "18px 0" }}>{t("載入中…")}</div>
          ) : nodeConfig ? (
            <NodeResponsibilityConfig config={nodeConfig} onChange={setNodeConfig} onSave={saveNodeConfig}
              busy={nodeConfigBusy} error={nodeConfigError} notice={nodeConfigNotice} dirtyCount={dirtyNodeConfigs.length}/>
          ) : (
            <EM icon="alert" title={t("節點責任載入失敗")} sub={nodeConfigError}
              action={<B size="sm" icon="refresh" onClick={() => loadNodeConfig(flowKey).catch(() => {})}>{t("刷新")}</B>}/>
          )
        ) : null}
      </Band>

      {/* D · 招標看板(買方 · 跨公司 B2B)*/}
      <Band no="D" title={t("招標看板")} sub={t("跨公司邀請制招標 · 密封投標 · 鋼印留痕")} delay={.25}
        right={<div className="row g8">
          <B size="sm" icon="plus" onClick={() => W2.openBusinessAction("tender_create")}>{t("發起招標")}</B>
          <B size="sm" icon="sparkle" onClick={() => ask(t("把當前全部招標的狀態、投標和下一步該做什麼給我彙總"))}>{t("問秘書")}</B>
        </div>}>
        {rels != null && (
          <div className="row" style={{ marginBottom: 12 }}>
            <button className="btn ghost sm" style={{ fontSize: 11 }} onClick={() => ask(t("把本公司的跨公司合作關係列出來,有待響應的邀請幫我研判"))}>
              <I name="layers" size={12}/>{t("已生效合作 {n} 家", { n: activeRels })}
            </button>
          </div>
        )}
        {board == null ? (
          <div className="muted" style={{ fontSize: 12.5, padding: "20px 0" }}>{t("載入中…")}</div>
        ) : board.length ? (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th>{t("公告號")}</th><th>{t("標題")}</th><th>{t("截標時間")}</th><th>{t("狀態")}</th><th>{t("邀請數")}</th><th>{t("投標數")}</th><th>{t("鋼印")}</th><th style={{ width: 90 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {board.map((n, i) => {
                  const na = noticeAsk(n);
                  const od = n.status === "published" && isOverdue(n.bid_deadline);
                  return (
                    <React.Fragment key={n.id || i}>
                      <tr className={tOpen === n.id ? "on" : ""} style={{ cursor: "pointer" }} onClick={() => setTOpen(tOpen === n.id ? 0 : n.id)}>
                        <td><span className="num" style={{ fontWeight: 600, fontSize: 12 }}>{n.notice_no || "—"}</span></td>
                        <td><span style={{ fontWeight: 650 }}>{n.title || "—"}</span></td>
                        <td><span className="num" style={{ fontSize: 11.5, color: od ? "var(--red)" : "var(--ink-3)" }}>{wfDate(n.bid_deadline)}{od ? " · " + t("已逾期") : ""}</span></td>
                        <td>{nstatTag(n.status)}</td>
                        <td><span className="num muted" style={{ fontSize: 11.5 }}>{num(n.invite_count)}</span></td>
                        <td><span className="num muted" style={{ fontSize: 11.5 }}>{num(n.bid_count)}</span></td>
                        <td><span className="mono muted" style={{ fontSize: 10 }}>{n.seal_serial || "—"}</span></td>
                        <td onClick={(e) => e.stopPropagation()}>
                          {na ? <B size="sm" icon={na[0]} onClick={() => ask(na[2])}>{t(na[1])}</B> : null}
                        </td>
                      </tr>
                      {tOpen === n.id && (
                        <tr><td colSpan={8} style={{ padding: 0 }}><TenderDetail det={tDetail} notice={n}/></td></tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EM icon="doc" title={t("還沒有招標公告")} sub={t("先建立真實 ERP 採購申請並啟動綁定的招標工作流;流程到建立招標節點後,再由這裡建立草稿。")}
            action={<B icon="plus" onClick={() => W2.openBusinessAction("tender_create")}>{t("發起第一個招標")}</B>}/>
        )}
      </Band>

      {/* E · 外部協作 · 收到的招標邀請(供方)*/}
      {tInbox.length > 0 && (
        <Band no="E" title={t("外部協作 · 收到的招標邀請")} sub={t("同行公司邀請你投標 · 報價經你確認後密封提交")} delay={.3}>
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {tInbox.map((iv, i) => {
              const ref = iv.notice_ref || iv.notice_no || "—";
              const od = iv.notice_status === "published" && isOverdue(iv.bid_deadline);
              return (
                <div key={(iv.notice_ref || "iv") + "_" + i} className="ledger-row">
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <div className="col g4" style={{ flex: 1.6, minWidth: 0 }}>
                    <span className="row g8 wrap" style={{ fontWeight: 650, fontSize: 13.5 }}>
                      {iv.title || "—"}
                      <span className="mono muted" style={{ fontSize: 9.5, letterSpacing: ".1em" }}>{iv.notice_no || ref}</span>
                    </span>
                    <span className="muted" style={{ fontSize: 12 }}>
                      {iv.buyer_name || iv.buyer_slug || "—"}
                      {iv.budget_ceiling != null ? <span className="num"> · {cny(iv.budget_ceiling)}</span> : null}
                    </span>
                    <span className="mono muted" style={{ fontSize: 9 }}>{t("公告鋼印")} {iv.seal_serial || "—"}</span>
                  </div>
                  {nstatTag(iv.notice_status)}
                  {ivTag(iv.status)}
                  <span className="num" style={{ fontSize: 11.5, width: 140, flexShrink: 0, textAlign: "right", color: od ? "var(--red)" : "var(--ink-3)" }}>
                    {iv.bid_deadline ? t("截標 {d}", { d: wfDate(iv.bid_deadline) }) : "—"}
                  </span>
                  <B size="sm" icon="check" onClick={() => ask(t("查看招標邀請「{ref}」的需求並幫我準備投標報價,報價需我確認後密封提交", { ref }))}>{t("準備投標")}</B>
                  <B size="sm" icon="x" onClick={() => ask(t("婉拒招標邀請「{ref}」", { ref }))}>{t("婉拒")}</B>
                </div>
              );
            })}
          </div>
        </Band>
      )}

      {/* F · 我的投標(供方 · 密封記錄)*/}
      {myBids.length > 0 && (
        <Band no="F" title={t("我的投標")} sub={t("密封投標記錄 · 開標前任何人不可見")} delay={.35}>
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {myBids.map((b, i) => {
              const [tone, label] = BSTAT[b.status] || ["plain", b.status || "—"];
              return (
                <div key={b.id || i} className="ledger-row">
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <div className="col g4" style={{ flex: 1.6, minWidth: 0 }}>
                    <span style={{ fontWeight: 650, fontSize: 13.5 }}>{b.notice_title || b.notice_ref || "—"}</span>
                    <span className="muted" style={{ fontSize: 12 }}>{b.buyer_slug || "—"}<span className="num"> · {wfDate(b.created_at)}</span></span>
                  </div>
                  <T tone={tone}>{t(label)}</T>
                  <span className="mono muted" style={{ fontSize: 10, width: 210, flexShrink: 0, textAlign: "right", wordBreak: "break-all" }}>
                    {shortHash(b.bid_hash)}{b.seal_serial ? " · " + b.seal_serial : ""}
                  </span>
                  <B size="sm" icon="sparkle" onClick={() => ask(t("查一下我對招標「{title}」的投標狀態和下一步", { title: b.notice_title || b.notice_ref || "—" }))}>{t("查狀態")}</B>
                </div>
              );
            })}
          </div>
        </Band>
      )}

      {/* G · 公開招標市場(投標方 · 公開報名 + AI 資質審核)*/}
      <Band no="G" title={t("公開招標市場")} sub={t("全平台公開招標 · 報名經 AI 資質審核 · 通過後可密封投標")} delay={.4}
        right={<B size="sm" icon="sparkle" onClick={() => ask(t("公開招標市場現在有哪些適合本公司投標的機會?幫我篩一遍"))}>{t("問秘書")}</B>}>
        {market == null ? (
          <div className="muted" style={{ fontSize: 12.5, padding: "20px 0" }}>{t("載入中…")}</div>
        ) : market.length ? (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th>{t("招標公司")}</th><th>{t("標題")}</th><th>{t("需求摘要")}</th><th>{t("預算上限")}</th><th>{t("截標時間")}</th><th>{t("公告鋼印")}</th><th style={{ width: 160 }}>{t("我的狀態")}</th>
              </tr></thead>
              <tbody>
                {market.map((m, i) => {
                  const ref = m.notice_ref || ((m.buyer_slug || "—") + "#" + (m.id != null ? m.id : "—"));
                  const hasBudget = m.budget_ceiling != null && m.budget_ceiling !== "" && Number.isFinite(Number(m.budget_ceiling));
                  const near = nearDue(m.bid_deadline);
                  const ms = m.my_status || null;
                  const qs = ms && ms.qualification_status;
                  return (
                    <tr key={m.id || i}>
                      <td><span style={{ fontWeight: 650, fontSize: 12.5 }}>{m.buyer_name || m.buyer_slug || "—"}</span></td>
                      <td><span style={{ fontWeight: 650 }}>{m.title || "—"}</span></td>
                      <td><span className="muted" style={{ fontSize: 12 }}>{trunc(m.requirements_text, 40) || "—"}</span></td>
                      <td><span className="num" style={{ fontSize: 11.5 }}>{hasBudget ? cny(m.budget_ceiling) : t("面議")}</span></td>
                      <td><span className="num" style={{ fontSize: 11.5, color: near ? "var(--red)" : "var(--ink-3)" }}>{wfDate(m.bid_deadline)}</span></td>
                      <td><span className="mono muted" style={{ fontSize: 10 }}>{m.seal_serial || "—"}</span></td>
                      <td>
                        {!ms ? (
                          <B size="sm" icon="check" onClick={() => ask(t("報名參與公開招標「{ref}」:請採集本公司資質報名,通過 AI 資質審核後即可投標", { ref }))}>{t("報名")}</B>
                        ) : qs === "qualified" ? (
                          <span className="row g6 wrap">
                            <T tone="ok">{t("已通過·可投標")}</T>
                            <B size="sm" icon="check" onClick={() => ask(t("我要對已通過資質的公開招標「{ref}」密封投標,報價需我確認後提交", { ref }))}>{t("投標")}</B>
                          </span>
                        ) : qs === "rejected" ? (
                          <T tone="bad">{t("資質未通過")}</T>
                        ) : (
                          <T tone="warn">{t("資質待覆核")}</T>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <EM icon="doc" title={t("暫無公開招標")} sub={t("有公開招標時會出現在這裡,可對秘書說『幫我找適合的公開招標』。")}/>
        )}
      </Band>

      {/* R · 低頻修復工具固定置底，不壓過每日採購待辦。錯誤、載入、案件、健康空態互斥。 */}
      {canRepairWorkflows && <Band no="R" title={t("流程安全修復")}
        sub={t("確定性異常證據 · 缺件引導 · 獨立 Passkey 共簽 · 禁止效果重放")} delay={.45}
        right={<B size="sm" icon="refresh" disabled={repairLoading} onClick={() => loadRepairs().catch(() => {})}>{t("刷新")}</B>}>
        {repairError ? (
          <div className="row g8 wrap" role="alert" style={{ padding: "18px 0", color: "var(--red)", borderTop: "2px solid var(--red)" }}>
            <T tone="bad" dot>{t("修復案件載入失敗")}</T>
            <span style={{ fontSize: 11.5, flex: 1 }}>
              {!["修復案件載入失敗", t("修復案件載入失敗")].includes(repairError) ? repairError : null}
            </span>
            <B size="sm" icon="refresh" onClick={() => loadRepairs().catch(() => {})}>{t("刷新")}</B>
          </div>
        ) : repairLoading ? (
          <div className="muted" style={{ padding: "18px 0", fontSize: 12.5 }}>{t("載入中…")}</div>
        ) : activeRepairs.length && typeof RepairPlanCard === "function" ? (
          <div className="col g12" style={{ borderTop: "2px solid var(--rule)", paddingTop: 12 }}>
            {activeRepairs.map((item, index) => {
              const envelope = repairEnvelope(item);
              return <RepairPlanCard key={(envelope && envelope.caseId) || index} repair={item}
                onChange={updateRepair} onAsk={(prompt) => ask(t(prompt))}/>;
            })}
          </div>
        ) : (
          <EM icon="checkCircle" title={t("目前沒有進行中的修復案件")} sub={t("Guardian 仍會持續掃描；正常流程不需要人工干預。")}/>
        )}
      </Band>}
    </>
  );
};

window.W2.PAGES["procurement"] = Page;
})();
