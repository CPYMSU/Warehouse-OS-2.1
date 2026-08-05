/* WAREHOUSE 2.1 · 設置 — Swiss 版式,真後端(只讀駕駛艙,改動交秘書) */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "設置": "Settings",
  "系統配置一頁盡覽:AI 密鑰 · 監測規則 · 倉庫 · 分類 · 導航 · 提示詞 · 通用開關 · 公司標識;僅 AI 密鑰與公司標識可在此直接配置,其餘改動一律交秘書執行留痕。": "Every system setting on one page: AI keys, company mark, rules, warehouses, categories, nav, prompts, general switches. Only AI keys and the company mark are configured here directly — everything else goes through the Secretary, fully audited.",
  "問秘書": "Ask Secretary",
  "刷新": "Refresh",
  "檢查系統設置:AI 密鑰連接、監測規則、倉庫與分類配置,有什麼需要完善的?": "Review system settings: AI key connections, monitoring rules, warehouse and category setup — what needs attention?",
  "在管倉庫": "Warehouses",
  "物資分類": "Material categories",
  "權限角色": "Permission roles",
  "AI 連接": "AI connections",
  "個": "sites",
  "類": "types",
  "/{n} 已連接": "/{n} connected",
  "共 {n} 個功能區": "{n} zones in total",
  "需歸還 {n} 類": "{n} returnable",
  "分級授權 · 高危可見": "Tiered grants · risk visible",
  "全部就緒": "All connected",
  "有連接失敗": "Connection failed",
  "有待配置": "Setup pending",
  /* 01 AI 密鑰 */
  "AI 引擎與全局密鑰": "AI engines & global keys",
  "管理員配置一次 · 全員共用 · 密鑰入庫保存": "Configured once by an admin · shared by everyone · keys stored in the database",
  "管理員配置一次 · 公司內共用 · 密鑰加密入庫": "Configured once by an admin · shared within this company · encrypted at rest",
  "智能引擎": "AI Engine",
  "圖片識別": "Vision",
  "語音功能": "Voice",
  "Web 搜索": "Web Search",
  "Tavily 為 AI 秘書提供最新公開 Web 資訊;搜索結果只作外部線索。": "Tavily gives the Secretary current public Web information; results are external leads only.",
  "驅動秘書對話與智能分析,全公司共用一把全局 key。": "Powers the Secretary and analytics; one global key for the whole company.",
  "均衡 · Flash": "Balanced · Flash",
  "Thinking · Pro": "Thinking · Pro",
  "記憶 · Flash 後台蒸餾": "Memory · Flash background distillation",
  "圖片識別共用密鑰,後端按接入地址自動識別供應商。": "Shared key for image recognition; provider auto-detected from the base URL.",
  "語音識別與朗讀共用密鑰,未配置時自動降級瀏覽器原生語音。": "Shared key for ASR + TTS; falls back to native browser speech when unset.",
  "可連接": "Connected",
  "連接失敗": "Failed",
  "待驗證": "Unverified",
  "未配置": "Not configured",
  "自動適配": "Auto-detected",
  "共用 Key": "Shared key",
  "模型": "Model",
  "最近驗證": "Last checked",
  "識別": "ASR",
  "朗讀": "TTS",
  "填寫密鑰": "Set key",
  "更換密鑰": "Change key",
  "重新驗證": "Re-validate",
  "填寫全局 API Key": "Set the global API key",
  "更換全局 API Key": "Replace the global API key",
  "接入地址(可選,留空自動探測)": "Base URL (optional; auto-detected when empty)",
  "OpenAI 相容 HTTPS 接入地址": "OpenAI-compatible HTTPS base URL",
  "保存並驗證": "Save & validate",
  "保存中…": "Saving…",
  "驗證中…": "Validating…",
  "取消": "Cancel",
  "顯示密鑰": "Show key",
  "隱藏密鑰": "Hide key",
  "請先輸入 API Key": "Enter the API key first",
  "保存失敗": "Save failed",
  "驗證失敗": "Validation failed",
  "驗證成功": "Validated",
  "密鑰已保存並驗證成功,全公司即刻共用": "Key saved and validated — shared company-wide immediately",
  "密鑰已保存,但驗證失敗:": "Key saved, but validation failed: ",
  "Esc 收起 · 密鑰只寫入服務器,不留在瀏覽器": "Esc to collapse · the key goes to the server only, never kept in this browser",
  "AI 運行時": "AI RUNTIME",
  "狀態": "Status",
  "知識文檔": "Docs",
  "行動計劃": "Plans",
  "活躍對話": "Conversations",
  "記憶": "Memories",
  "經驗": "Lessons",
  "運行時暫無數據": "No runtime data yet",
  "自檢": "Self-check",
  "跑一次 AI 資料庫自檢,把結果彙報給我": "Run an AI database self-check and report the results to me",
  /* 02 公司標識 */
  "公司標識": "Company mark",
  "報頭與瀏覽器標籤同步 · 上傳圖標或設計 Swiss 字標": "Synced to the masthead and favicon · upload an icon or design a Swiss wordmark",
  "當前標識": "Current mark",
  "平臺默認": "Platform default",
  "字標": "Wordmark",
  "上傳圖標": "Uploaded icon",
  "報頭": "Masthead",
  "標識同步顯示在報頭與瀏覽器標籤。": "The mark shows in the masthead and the browser tab.",
  "未配置,使用平臺默認閃電標。": "Not configured — using the platform's default bolt.",
  "恢復默認": "Reset to default",
  "已恢復平臺默認": "Platform default restored",
  "僅 L5 管理員可修改公司標識,請聯繫管理員修改。": "Only L5 admins can change the company mark — please contact an administrator.",
  "方式一 · 上傳圖標": "Option 1 · Upload an icon",
  "任意圖片,瀏覽器內裁成 128×128 方形 PNG 入庫;超限自動降到 96 / 64,原圖不出瀏覽器。": "Any image — cropped in the browser to a 128×128 square PNG; auto-downscaled to 96 / 64 when over the limit. The original never leaves your browser.",
  "選擇圖片": "Choose image",
  "字符數 {n}": "{n} chars",
  "保存": "Save",
  "已保存": "Saved",
  "請選擇圖片文件(PNG / JPEG / WebP)": "Choose an image file (PNG / JPEG / WebP)",
  "圖片壓縮後仍超出大小限制,請換一張更簡潔的圖標": "Still over the size limit after compression — try a simpler icon",
  "圖片讀取失敗,請換一個文件": "Could not read the image — try another file",
  "方式二 · 設計字標": "Option 2 · Design a wordmark",
  "1–2 個字符(字母自動大寫,支持漢字與 Emoji),Swiss 方標實時預覽。": "1–2 characters (letters auto-uppercase; CJK & emoji welcome) with a live Swiss-square preview.",
  "1-2 字,如 WH / 倉 / ⚡": "1-2 chars, e.g. WH / ⚡",
  "底色": "Background",
  "墨": "Ink", "瑞士紅": "Swiss red", "紙": "Paper", "夜藍": "Midnight",
  "鈷藍": "Cobalt", "群青": "Ultramarine", "靛紫": "Indigo", "青碧": "Teal",
  "松綠": "Pine", "森綠": "Forest", "琥珀": "Amber", "燒橙": "Burnt orange",
  "酒紅": "Wine", "玫紅": "Magenta", "深紫": "Violet", "暖灰": "Warm grey",
  "字色自動對比:{c}": "Auto-contrast text: {c}",
  /* 03 規則與邊界 */
  "AI 監測規則與操作邊界": "AI monitoring rules & boundaries",
  "規則開關持久化 · 邊界不可逾越": "Switches persist server-side · boundaries are absolute",
  "低庫存自動預警": "Low-stock auto alert",
  "庫存低於安全庫存時自動生成預警並推送倉管": "Auto-generate an alert and notify keepers when stock falls below the safety line",
  "超期未檢提醒": "Inspection-due reminder",
  "距檢驗到期 ≤15 天自動推送計量班": "Push to the metering team when inspection is due within 15 days",
  "異常出庫檢測": "Abnormal outbound detection",
  "出庫頻率超正常波動 3σ 觸發盤點建議": "Suggest a stocktake when outbound frequency exceeds 3σ of normal",
  "應急缺口預測": "Emergency-gap forecast",
  "結合關聯地點與需求記錄預測應急物資缺口": "Forecast emergency supply gaps from linked sites and demand history",
  "AI 自動草擬單據": "AI drafts documents",
  "AI 可自動草擬補貨/調撥單(高風險仍進覆核)": "AI may draft replenishment/transfer orders (high-risk still reviewed)",
  "AI 托管分庫": "AI-managed sub-warehouses",
  "AI 可根據庫存資料整理倉庫、庫區與庫位關聯": "AI may organise warehouse, zone and location links from inventory data",
  "開啟": "ON",
  "關閉": "OFF",
  "交秘書開啟": "Ask to enable",
  "交秘書關閉": "Ask to disable",
  "交秘書調整": "Ask to adjust",
  "把 AI 監測規則「{name}」打開": "Turn ON the AI monitoring rule \"{name}\"",
  "把 AI 監測規則「{name}」關閉": "Turn OFF the AI monitoring rule \"{name}\"",
  "查一下 AI 監測規則「{name}」現在的狀態,告訴我要不要開": "Check the current state of AI rule \"{name}\" and advise whether to enable it",
  "後端未返回規則配置,以下為規則目錄;可讓秘書逐條查證。": "Backend returned no rule config; catalog shown below — ask the Secretary to verify each.",
  "AI 操作邊界": "AI HARD BOUNDARIES",
  "安全紅線 · 任何人不可越過": "Safety red lines · no one may cross",
  "禁止任意刪庫": "No arbitrary DB deletion",
  "禁止自動大額出庫": "No automatic bulk outbound",
  "禁止私自改權限": "No unauthorised permission edits",
  "禁止繞過審批": "No bypassing approvals",
  "禁止替人簽字": "No signing on someone's behalf",
  /* 04 倉庫與分類 */
  "倉庫與物資分類": "Warehouses & categories",
  "倉庫檔案 · 分類驅動庫存組織與 AI": "Warehouse files · categories drive inventory & AI",
  "新增倉庫": "Add warehouse",
  "新增一個倉庫,幫我登記名稱、編碼和容量使用率": "Add a new warehouse — register its name, code and capacity usage for me",
  "默認庫": "Default",
  "{n} 個功能區": "{n} zones",
  "容量": "Capacity",
  "編輯": "Edit",
  "刪除": "Delete",
  "受保護": "Protected",
  "編輯倉庫「{name}」的資料(名稱/編碼/容量使用率),先展示現在的值": "Edit warehouse \"{name}\" (name / code / capacity usage) — show me the current values first",
  "刪除倉庫「{name}」,先告訴我會影響哪些數據再執行": "Delete warehouse \"{name}\" — tell me what data is affected before executing",
  "暫無倉庫檔案": "No warehouses yet",
  "對秘書說「新增倉庫」即可建立。": "Tell the Secretary \"add a warehouse\" to create one.",
  "新增分類": "Add category",
  "新增一個物資分類,幫我定分類代碼、名稱和是否需歸還": "Add a material category — help me set its code, name and whether it must be returned",
  "需歸還": "Returnable",
  "消耗": "Consumable",
  "編輯分類「{name}」(名稱/是否需歸還/說明),先展示現在的設定": "Edit category \"{name}\" (name / returnable / description) — show current settings first",
  "刪除分類「{name}」,若分類下還有數據先告訴我影響": "Delete category \"{name}\" — if it still holds data, tell me the impact first",
  "暫無分類": "No categories yet",
  "對秘書說「幫我建物資分類」即可開始。": "Tell the Secretary \"create material categories\" to get started.",
  /* 05 角色 */
  "分級授權 · CLI 高危能力一眼可見": "Tiered authorisation · risky CLI powers at a glance",
  "新增角色": "Add role",
  "新增一個權限角色,幫我配置名稱、等級和權限清單": "Create a new permission role — help me set its name, level and permission list",
  "業務權限 {n} 項": "{n} business perms",
  "CLI {n} 項": "{n} CLI",
  "高危 {n} 項": "{n} high-risk",
  "無 CLI 高危能力": "No CLI capabilities",
  "交秘書配置": "Configure",
  "調整角色「{name}」的權限配置,先列出它現在有哪些權限": "Adjust permissions for role \"{name}\" — list its current permissions first",
  "暫無角色": "No roles yet",
  "對秘書說「新增角色」即可配置分級授權。": "Tell the Secretary \"add a role\" to configure tiered authorisation.",
  /* 06 導航 */
  "導航設計": "Navigation design",
  "AI 依行業編排側欄:改名 / 排序 / 隱藏": "AI arranges the nav for your industry: rename / reorder / hide",
  "AI 設計導航": "AI design nav",
  "讓 AI 根據我們公司的行業重新設計側欄導航(改名/排序/隱藏),先給我預覽再保存": "Have the AI redesign our navigation for our industry (rename / reorder / hide) — preview before saving",
  "還原默認": "Reset default",
  "把側欄導航還原成默認配置": "Reset the navigation to its default configuration",
  "{n} 個導航項": "{n} nav items",
  "改名 {n}": "{n} renamed",
  "隱藏 {n}": "{n} hidden",
  "ERP 工作台": "ERP workbench",
  "庫存作業": "Warehouse ops",
  "系統管理": "System admin",
  "物資台賬": "Material ledger",
  "紅塊=已改名 · 劃線=已隱藏 · 「設置」受保護不可隱藏": "Red block = renamed · struck = hidden · Settings is protected",
  "導航目錄未返回": "Nav catalog unavailable",
  "後端未返回導航目錄;可直接讓秘書設計或還原導航。": "Backend returned no nav catalog; ask the Secretary to design or reset it directly.",
  /* 07 提示詞 */
  "提示詞層": "Prompt layers",
  "L0/L1/L2 版本化 · 改動可回滾": "L0/L1/L2 versioned · changes can roll back",
  "作用域": "Scope",
  "層": "Layer",
  "現行版本": "Active ver.",
  "版本數": "Versions",
  "字數": "Chars",
  "更新於": "Updated",
  "更新人": "By",
  "交給秘書": "Via Secretary",
  "調整": "Adjust",
  "回滾": "Rollback",
  "調整提示詞「{scope}」:先給我看現行版本的內容,再說怎麼改": "Adjust prompt \"{scope}\": show me the active version first, then discuss changes",
  "把提示詞「{scope}」回滾到上一個版本,先列出版本歷史": "Roll prompt \"{scope}\" back one version — list the version history first",
  "暫無提示詞版本": "No prompt versions",
  "運行時以資料庫為準;讓秘書初始化或調整提示詞即可。": "Runtime reads from the database; ask the Secretary to initialise or adjust prompts.",
  /* 08 通用與系統 */
  "通用與系統": "General & system",
  "交互開關 · 系統信息 · 數據導出": "Interaction switches · system info · data export",
  "通知與交互": "NOTIFICATIONS & INTERACTION",
  "掃碼槍快速入口": "Scanner quick entry",
  "現場 PDA / 掃碼槍一鍵入出庫": "One-tap in/out with on-site PDA / scanner",
  "預警消息推送": "Alert push",
  "高風險預警即時推送至負責人": "Push high-risk alerts to owners instantly",
  "預警提示音": "Alert sound",
  "新預警只向具備對應處置權限的人員播放;首次頁面互動後啟用": "Only people authorised to handle a new alert hear it; enabled after the first page interaction",
  "深色駕駛艙模式": "Dark cockpit mode",
  "切換為深色科技底色": "Switch to a dark technical theme",
  "把通用設置「{name}」打開": "Turn ON the general setting \"{name}\"",
  "把通用設置「{name}」關閉": "Turn OFF the general setting \"{name}\"",
  "查一下通用設置「{name}」現在的狀態,告訴我要不要開": "Check the general setting \"{name}\" and advise whether to enable it",
  "系統信息": "SYSTEM INFO",
  "後端未返回系統信息。": "Backend returned no system info.",
  "系統版本": "System version",
  "AI 模型": "AI model",
  "接入倉庫": "Warehouses linked",
  "在線人員": "People online",
  "資料庫 CSV 導出": "DATABASE CSV EXPORT",
  "整庫導出 zip:每表一個 CSV + schema + manifest;含敏感表,注意保密。": "Full export as zip: one CSV per table + schema + manifest; includes sensitive tables — handle with care.",
  "交秘書導出": "Export via Secretary",
  "把當前公司資料庫導出成 CSV 壓縮包,告訴我怎麼拿到文件": "Export the current company database as a CSV zip and tell me how to get the file",
  "2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "The 2.1 contract: pages are read-only; changes run through the Secretary with a full audit trail.",
  "規則與秘書": "Rules & Secretary",
  "AI 秘書 · 法律倫理規則 · 工作區導航 · 指令集 · 通用開關 · BIU 標識；關鍵改動經確認後留痕。": "AI Secretary · legal ethics rules · workspace navigation · instruction sets · general switches · BIU identity; key changes are confirmed and recorded",
  "法律倫理規則與秘書邊界": "Legal ethics rules & Secretary boundaries",
  "規則持久化 · 法律倫理與權限邊界不可逾越": "Rules persist · legal ethics and access boundaries are absolute",
  "工作區導航": "Workspace navigation",
  "AI 依 BIU 法律工作編排側欄：改名 / 排序 / 隱藏": "AI arranges the BIU legal-work navigation: rename / reorder / hide",
  "固定六項法律工作區 · 原路由與權限不變": "Fixed six-part legal workspace · original routes and access unchanged",
  "秘書指令集": "Secretary instruction sets",
  "AI 秘書連接": "AI Secretary connections",
  "法律倫理規則": "Legal ethics rules",
  "固定學術邊界": "Fixed academic boundaries",
  "以下邊界由 BIU 模板固定，不在此切換。": "These boundaries are fixed by the BIU template and cannot be toggled here.",
  "僅處理 BIU 內部的案件、卷宗、程序工作、機構職位與法律倫理研究。": "Only BIU-internal cases, records, procedural work, institutions, positions, and legal-ethics study are in scope.",
  "案件材料僅限虛構、改編公開資料、已結案公開資料或獲授權匿名資料。": "Case materials are limited to fictional, adapted public, concluded public, or authorised anonymised materials.",
  "所有職位均為 BIU 內部學術職位，不構成現實職業資格或法律授權。": "All positions are BIU-internal academic positions and do not confer real-world professional qualification or legal authority.",
  "秘書不提供現實個案法律意見，不聯絡現實機構或當事人。": "The Secretary does not advise on active real-world matters or contact real-world institutions or parties.",
  "程序以裁決登記、最終審查、完整性核查與歸檔為止。": "The process ends with decision registration, final review, completeness review, and archiving.",
  "不同案件、職位與卷宗依原有權限隔離，任何人不得繞過。": "Existing access rules isolate cases, positions, and records and cannot be bypassed.",
  "機構與職位": "Institutions & positions",
  "職位權限 {n} 項": "{n} position permissions",
  "學術職位 · 權限依案件與機構範圍分級": "Academic positions · access is scoped by case and institution",
  "秘書記憶": "Secretary memories",
  "指令集 {n} 組": "{n} instruction sets",
  "固定六項法律工作區": "Fixed six-part legal workspace",
  "案件總覽": "Case overview", "我的工作": "My work", "案件與卷宗": "Cases & records",
  "程序記錄": "Procedure history",
  "BIU 導航由模板固定為六項，不在此切換。": "The BIU template fixes these six navigation items; they cannot be switched here.",
  "互動開關 · 系統信息": "Interaction switches · system information",
  "提示音": "Notification sound",
  "程序提醒提示音；首次頁面互動後啟用": "Sound for procedure reminders; enabled after the first page interaction",
  "深色工作區模式": "Dark workspace mode",
  "切換為深色工作區底色": "Switch to a dark workspace theme",
  "檢查 BIU 法律工作區的 CASE、RECORD、TASK、機構職位、權限、指令集與 AI 連接，列出需要核查之處。": "Review BIU CASE, RECORD, TASK, institutions, positions, access, instruction sets, and AI connections, then list anything needing review.",
  "檢查 BIU 秘書的指令集、記憶與連接狀態，只彙報法律倫理學術工作範圍。": "Check BIU Secretary instruction sets, memories, and connections, reporting only within the legal-ethics academic scope.",
  "公開搜索僅用於已結案公開資料的學術線索，不作現實個案工作。": "Public search is only for academic leads from concluded public materials, never active real-world matters.",
  "新增一個 BIU 學術職位，先說明所屬機構、申請方式、等級與案件權限。": "Create a BIU academic position, first describing its institution, application path, level, and case access.",
  "調整 BIU 學術職位「{name}」的案件、卷宗與機構權限，先列出現有配置。": "Adjust case, record, and institution access for BIU academic position \"{name}\" after listing its current configuration.",
  "調整 BIU 指令集「{scope}」：先顯示現行版本，只討論 CASE、RECORD、TASK、機構職位、權限、連接與法律倫理邊界。": "Adjust BIU instruction set \"{scope}\": show the active version first and discuss only CASE, RECORD, TASK, institutions, positions, access, connections, and legal-ethics boundaries.",
  "把 BIU 指令集「{scope}」回滾到上一版本，先列出版本歷史並確認只影響 BIU。": "Roll BIU instruction set \"{scope}\" back one version after listing its history and confirming BIU-only impact.",
  "在 BIU 法律工作區開啟界面偏好「{name}」；只調整本公司界面，不改變 CASE、RECORD、TASK、機構職位、權限或指令集。": "Enable BIU workspace preference \"{name}\"; change only this company's interface, without altering CASE, RECORD, TASK, institutions, positions, access, or instruction sets.",
  "在 BIU 法律工作區關閉界面偏好「{name}」；只調整本公司界面，不改變 CASE、RECORD、TASK、機構職位、權限或指令集。": "Disable BIU workspace preference \"{name}\"; change only this company's interface, without altering CASE, RECORD, TASK, institutions, positions, access, or instruction sets.",
  "查閱 BIU 法律工作區界面偏好「{name}」的狀態；只回覆本公司設定。": "Check BIU workspace preference \"{name}\" and report only this company's setting.",
});
const { useState: _s, useEffect: _e, useMemo: _mm } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Meter, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

const SETTINGS_BIU_COPY = Object.freeze({
  "設置": "規則與秘書",
  "系統配置一頁盡覽:AI 密鑰 · 監測規則 · 倉庫 · 分類 · 導航 · 提示詞 · 通用開關 · 公司標識;僅 AI 密鑰與公司標識可在此直接配置,其餘改動一律交秘書執行留痕。": "AI 秘書 · 法律倫理規則 · 工作區導航 · 指令集 · 通用開關 · BIU 標識；關鍵改動經確認後留痕。",
  "AI 監測規則與操作邊界": "法律倫理規則與秘書邊界",
  "規則開關持久化 · 邊界不可逾越": "規則持久化 · 法律倫理與權限邊界不可逾越",
  "導航設計": "工作區導航",
  "AI 依行業編排側欄:改名 / 排序 / 隱藏": "固定六項法律工作區 · 原路由與權限不變",
  "提示詞層": "秘書指令集",
  "AI 引擎與全局密鑰": "AI 秘書連接",
  "權限角色": "機構與職位",
  "分級授權 · CLI 高危能力一眼可見": "學術職位 · 權限依案件與機構範圍分級",
  "交互開關 · 系統信息 · 數據導出": "互動開關 · 系統信息",
});
const settingsText = (biu, value) => t(biu ? (SETTINGS_BIU_COPY[value] || value) : value);

/* 連接狀態歸一化(deepseek / vision / voice / tavily 四卡同構,任何字段可缺) */
const connState = (st) => {
  st = st || {};
  const conn = st.connection || {};
  const configured = !!st.configured;
  const connected = configured && !!(st.connected || conn.ok || st.connection_status === "connected");
  const failed = configured && (st.connection_status === "failed" || conn.status === "failed");
  return {
    configured, connected, failed,
    tone: connected ? "ok" : failed ? "bad" : configured ? "warn" : "plain",
    text: connected ? "可連接" : failed ? "連接失敗" : configured ? "待驗證" : "未配置",
    model: connected ? (st.model || conn.model || "—") : "—",
    key: st.masked_key || "—",
    checked: conn.checked_at || st.updated_at || "—",
    error: conn.error || "",
  };
};

const KVLine = ({ k, v }) => (
  <div className="row spread" style={{ borderTop: "1px solid var(--hair-soft)", padding: "7px 0", gap: 10 }}>
    <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
    <span className="num" style={{ fontSize: 12, fontWeight: 650, textAlign: "right", wordBreak: "break-all" }}>{v}</span>
  </div>
);

/* ⚠ 鐵律例外(用戶明示授權):新公司秘書未激活前無法用秘書配密鑰(雞生蛋),
   因此「密鑰配置」這一處允許頁面直接寫後端;其餘一切改動仍走秘書。
   真端點(照抄 1.0 / scripts/ai_service.py,字段名不發明):
   POST /api/integrations/<svc>/save     {api_key[, base_url 僅 voice 可選]}
   POST /api/integrations/<svc>/validate {}(驗證已存密鑰並持久化狀態)
   兩者響應都可能帶 {<svc>: 最新狀態, validation: {ok,latency_ms,error…}}。 */
const ConnPanel = ({ icon, title, sub, st, modelOverride, extra, service, onStatus, onCapability, keyPlaceholder = "sk-…" }) => {
  const s = connState(st);
  const name = t(title);
  const [open, setOpen] = _s(false);
  const [key, setKey] = _s("");
  const [base, setBase] = _s("");
  const [show, setShow] = _s(false);
  const [busy, setBusy] = _s("");        // "" | "save" | "verify"
  const [res, setRes] = _s(null);        // {ok, text}
  const touched = React.useRef(false);
  /* 未配置時默認展開表單(首配即雞生蛋場景);用戶手動開合後不再自動干預 */
  _e(() => { if (!touched.current) setOpen(!s.configured); }, [s.configured]);

  const refreshCapability = () => {
    if (service === "voice" && onCapability) {
      W2.json("/api/voice/status").then(d => onCapability(d || {})).catch(() => {});
    }
  };
  const refreshStatus = () =>
    W2.json("/api/integrations/" + service).then(d => onStatus((d && d[service]) || {})).catch(() => {});
  const applyStatus = (d) => {
    if (d && d[service]) onStatus(d[service]); else refreshStatus();
    refreshCapability();
  };
  const openForm = () => {
    touched.current = true;
    setRes(null);
    if (service === "voice" || service === "vision") {
      setBase(st.base_url || (service === "voice" ? "https://api.siliconflow.cn/v1" : ""));
    }
    setOpen(true);
  };
  const closeForm = () => {
    touched.current = true;
    setOpen(false); setShow(false);
    setKey(""); setBase("");           // 收起即清空明文
  };

  const doSave = async () => {
    const k = key.trim();
    if (!k) { setRes({ ok: false, text: t("請先輸入 API Key") }); return; }
    setBusy("save"); setRes(null);
    try {
      const body = { api_key: k };
      if ((service === "voice" || service === "vision") && base.trim()) body.base_url = base.trim();
      const d = await W2.post("/api/integrations/" + service + "/save", body);
      if (!d || !d.ok) throw new Error((d && d.error) || t("保存失敗"));
      applyStatus(d);                   // 保存端點已自動驗證並返回最新狀態
      setKey(""); setBase(""); setShow(false);   // 提交成功立即清空明文
      touched.current = true; setOpen(false);
      const v = d.validation || {};
      setRes(v.ok
        ? { ok: true, text: t("密鑰已保存並驗證成功,全公司即刻共用") + (v.latency_ms != null ? " · " + num(v.latency_ms) + " ms" : "") }
        : { ok: false, text: t("密鑰已保存,但驗證失敗:") + (v.error || t("驗證失敗")) });
    } catch (e) {
      setRes({ ok: false, text: e.message || String(e) });   // 錯誤不清空輸入、表單保持展開
    } finally { setBusy(""); }
  };

  const doVerify = async () => {
    setBusy("verify"); setRes(null);
    try {
      const d = await W2.post("/api/integrations/" + service + "/validate", {});
      applyStatus(d);
      setRes((d && d.ok)
        ? { ok: true, text: t("驗證成功") + (d.latency_ms != null ? " · " + num(d.latency_ms) + " ms" : "") }
        : { ok: false, text: (d && d.error) || t("驗證失敗") });
    } catch (e) {
      setRes({ ok: false, text: e.message || String(e) });
    } finally { setBusy(""); }
  };

  return (
    <div className="panel col" style={{ padding: 18, gap: 12 }}>
      <div className="row spread">
        <div className="row g8"><I name={icon} size={15}/><span style={{ fontWeight: 700, fontSize: 13.5 }}>{name}</span></div>
        <T tone={s.tone} dot>{t(s.text)}</T>
      </div>
      <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55, minHeight: 36 }}>{sub}</div>
      <div className="col">
        <KVLine k={t("共用 Key")} v={s.key}/>
        <KVLine k={t("模型")} v={modelOverride ? (s.configured ? modelOverride : "—") : s.model}/>
        {(service === "voice" || service === "vision") && <KVLine k={t("接入地址")} v={st.base_url || "—"}/>} 
        <KVLine k={t("最近驗證")} v={s.checked}/>
      </div>
      {!res && s.failed && !!s.error && (
        <div style={{ border: "1px solid var(--danger)", padding: "8px 10px", fontSize: 11.5, color: "var(--danger)", lineHeight: 1.5 }}>{s.error}</div>
      )}
      {res && (res.ok
        ? <div className="row g6" style={{ fontSize: 11.5, color: "var(--ok)", fontWeight: 650 }}>
            <I name="checkCircle" size={13} color="var(--ok)"/><span>{res.text}</span>
          </div>
        : <div style={{ border: "1px solid var(--danger)", padding: "8px 10px", fontSize: 11.5, color: "var(--danger)", lineHeight: 1.5, wordBreak: "break-all" }}>{res.text}</div>)}
      {extra}
      {open && (
        <div className="col g10" style={{ borderTop: "2px solid var(--rule)", paddingTop: 10 }}>
          <LB dim style={{ fontSize: 8.5 }}>{s.configured ? t("更換全局 API Key") : t("填寫全局 API Key")}</LB>
          <div className="row g6">
            <input className="field mono" type={show ? "text" : "password"} autoComplete="new-password" spellCheck={false}
              style={{ flex: 1, height: 34, fontSize: 13 }} placeholder={keyPlaceholder} value={key} disabled={busy === "save"}
              onChange={(e) => setKey(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Escape") closeForm(); else if (e.key === "Enter" && !busy && key.trim()) doSave(); }}/>
            <B size="sm" kind="ghost" icon={show ? "eyeOff" : "eye"} title={show ? t("隱藏密鑰") : t("顯示密鑰")}
              disabled={busy === "save"} onClick={() => setShow(v => !v)}/>
          </div>
          {(service === "voice" || service === "vision") && (
            <input className="field mono" type="text" autoComplete="off" spellCheck={false}
              style={{ height: 34, fontSize: 12.5 }} placeholder={service === "voice" ? "https://api.siliconflow.cn/v1" : t("OpenAI 相容 HTTPS 接入地址")} value={base} disabled={busy === "save"}
              onChange={(e) => setBase(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Escape") closeForm(); else if (e.key === "Enter" && !busy && key.trim()) doSave(); }}/>
          )}
          <div className="row g6">
            <B size="sm" kind="primary" icon="shield" disabled={!!busy || !key.trim()} onClick={doSave}>
              {busy === "save" ? t("保存中…") : t("保存並驗證")}
            </B>
            <B size="sm" onClick={closeForm} disabled={busy === "save"}>{t("取消")}</B>
          </div>
          <div className="muted" style={{ fontSize: 10 }}>{t("Esc 收起 · 密鑰只寫入服務器,不留在瀏覽器")}</div>
        </div>
      )}
      <div className="row g6" style={{ marginTop: "auto", paddingTop: 4 }}>
        <B size="sm" icon={s.configured ? "swap" : "plus"} disabled={busy === "save"}
          onClick={() => { if (open) closeForm(); else openForm(); }}>
          {s.configured ? t("更換密鑰") : t("填寫密鑰")}
        </B>
        <B size="sm" icon="refresh" disabled={!!busy || !s.configured} onClick={doVerify}>
          {busy === "verify" ? t("驗證中…") : t("重新驗證")}
        </B>
      </div>
    </div>
  );
};

/* ⚠ 鐵律例外延伸(公司配置):公司標識與 AI 密鑰同屬殼層啟動配置,
   允許本頁直寫後端;其餘一切業務改動仍走秘書。
   契約(以 scripts/ai_service.py 實現為準):
   GET  /api/company/branding → {branding: null | {type:"mono",letters,bg,fg} | {type:"upload",data_url}}
   POST /api/company/branding   body {branding:...};清除傳 {branding:null};
   data_url 僅 png/jpeg/webp 且 ≤120000 字符(客戶端自壓到 ≤110000 留餘量)。 */
const CM = W2.CompanyMark || (() => null);
const BRAND_LIMIT = 110000;
/* 預設底色:16 檔實色覆蓋常用品牌色相;原生調色板已移除
   (Windows 取色器關閉後預設色塊會被渲染成白色混色蒙版,且自由取色也偏離 Swiss 紀律) */
const BRAND_SWATCHES = [
  ["墨", "#141414"], ["瑞士紅", "#E0261C"], ["紙", "#F5F2EB"], ["夜藍", "#0F172A"],
  ["鈷藍", "#1F4FA0"], ["群青", "#2B4C7E"], ["靛紫", "#4338CA"], ["青碧", "#0E7490"],
  ["松綠", "#0F5132"], ["森綠", "#1F7A33"], ["琥珀", "#B26B00"], ["燒橙", "#C2410C"],
  ["酒紅", "#7F1D1D"], ["玫紅", "#BE185D"], ["深紫", "#5B21B6"], ["暖灰", "#85806F"],
];
/* 字素裁剪:emoji(ZWJ/旗幟/變體符)佔多個碼位但算 1 字;
   maxLength 按 UTF-16 截斷可能劈開代理對,先剔除孤立代理防碎片入庫 */
const clampMark = (s) => W2.graphemes(
  Array.from(String(s || "").replace(/\s/g, ""))
    .filter((c) => !(c.length === 1 && c.charCodeAt(0) >= 0xD800 && c.charCodeAt(0) <= 0xDFFF))
    .join("")
).slice(0, 2).join("");
const relLum = (hex) => {
  const h = String(hex || "").replace("#", "");
  const v = h.length === 3 ? h.split("").map(ch => ch + ch).join("") : (h + "000000").slice(0, 6);
  const [r, g, b] = [0, 2, 4].map(i => {
    const c = (parseInt(v.slice(i, i + 2), 16) || 0) / 255;
    return c <= .03928 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4);
  });
  return .2126 * r + .7152 * g + .0722 * b;
};
const fgFor = (bg) => relLum(bg) > .5 ? "#141414" : "#F5F2EB";   /* 淺底墨字 · 深底紙字 */

const BrandingBand = ({ branding, onSaved, canEdit }) => {
  const [busy, setBusy] = _s("");         // "" | "upload" | "mono" | "reset"
  const [res, setRes] = _s(null);         // {where, ok, text}
  const fileRef = React.useRef(null);
  const [pending, setPending] = _s("");   // 待保存的上傳 data_url
  const [letters, setLetters] = _s("");
  const [bg, setBg] = _s("#141414");
  const fg = fgFor(bg);

  const save = async (where, body, okText) => {
    setBusy(where); setRes(null);
    try {
      await W2.post("/api/company/branding", { branding: body });
      onSaved(body);
      try { window.W2_BRANDING_RELOAD && window.W2_BRANDING_RELOAD(); } catch (e) {}
      setRes({ where, ok: true, text: okText });
      return true;
    } catch (e) {
      setRes({ where, ok: false, text: e.message || String(e) });   // 後端原文
      return false;
    } finally { setBusy(""); }
  };

  const Res = ({ where }) => (!res || res.where !== where) ? null : (res.ok
    ? <div className="row g6" style={{ fontSize: 11.5, color: "var(--ok)", fontWeight: 650 }}>
        <I name="checkCircle" size={13} color="var(--ok)"/><span>{res.text}</span>
      </div>
    : <div style={{ border: "1px solid var(--danger)", padding: "8px 10px", fontSize: 11.5, color: "var(--danger)", lineHeight: 1.5, wordBreak: "break-all" }}>{res.text}</div>);

  /* 客戶端壓圖:cover 中心裁方 → 128 PNG,超限降 96 / 64 */
  const pickFile = (ev) => {
    const f = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!f) return;
    setRes(null); setPending("");
    if (!f.type || f.type.indexOf("image/") !== 0) {
      setRes({ where: "upload", ok: false, text: t("請選擇圖片文件(PNG / JPEG / WebP)") });
      return;
    }
    const url = URL.createObjectURL(f);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      if (!img.width || !img.height) { setRes({ where: "upload", ok: false, text: t("圖片讀取失敗,請換一個文件") }); return; }
      let out = "";
      for (const S of [128, 96, 64]) {
        let d = "";
        try {
          const cv = document.createElement("canvas");
          cv.width = S; cv.height = S;
          const cx = cv.getContext("2d");
          const side = Math.min(img.width, img.height);
          cx.drawImage(img, (img.width - side) / 2, (img.height - side) / 2, side, side, 0, 0, S, S);
          d = cv.toDataURL("image/png");
        } catch (e) { d = ""; }
        if (d && d.length <= BRAND_LIMIT) { out = d; break; }
      }
      if (!out) { setRes({ where: "upload", ok: false, text: t("圖片壓縮後仍超出大小限制,請換一張更簡潔的圖標") }); return; }
      setPending(out);
    };
    img.onerror = () => { URL.revokeObjectURL(url); setRes({ where: "upload", ok: false, text: t("圖片讀取失敗,請換一個文件") }); };
    img.src = url;
  };

  return (
    <Band no="08" title={t("公司標識")} sub={t("報頭與瀏覽器標籤同步 · 上傳圖標或設計 Swiss 字標")} delay={.22}>
      <div style={{ display: "grid", gridTemplateColumns: canEdit ? "repeat(auto-fit, minmax(250px, 1fr))" : "minmax(250px, 460px)", gap: 16 }}>

        {/* 當前標識(64 / 報頭 34 兩檔) */}
        <div className="panel col" style={{ padding: 18, gap: 14 }}>
          <div className="row spread">
            <div className="row g8"><I name="logo" size={15}/><span style={{ fontWeight: 700, fontSize: 13.5 }}>{t("當前標識")}</span></div>
            {branding
              ? <T tone="ok" dot>{branding.type === "mono" ? t("字標") : t("上傳圖標")}</T>
              : <T tone="plain">{t("平臺默認")}</T>}
          </div>
          <div className="row g24" style={{ alignItems: "flex-end" }}>
            <div className="col g6">
              <span style={{ display: "inline-block", lineHeight: 0, border: "1px solid var(--hair-soft)" }}><CM size={64} branding={branding}/></span>
              <LB dim style={{ fontSize: 8.5 }}>64</LB>
            </div>
            <div className="col g6">
              <span style={{ display: "inline-block", lineHeight: 0, border: "1px solid var(--hair-soft)" }}><CM size={34} branding={branding}/></span>
              <LB dim style={{ fontSize: 8.5 }}>{t("報頭")} 34</LB>
            </div>
          </div>
          <div className="muted" style={{ fontSize: 11, lineHeight: 1.6 }}>
            {branding ? t("標識同步顯示在報頭與瀏覽器標籤。") : t("未配置,使用平臺默認閃電標。")}
          </div>
          <Res where="reset"/>
          {canEdit
            ? <div style={{ marginTop: "auto" }}>
                <B size="sm" icon="refresh" disabled={!!busy || !branding}
                  onClick={() => save("reset", null, t("已恢復平臺默認"))}>
                  {busy === "reset" ? t("保存中…") : t("恢復默認")}
                </B>
              </div>
            : <div className="muted" style={{ fontSize: 11, marginTop: "auto" }}>{t("僅 L5 管理員可修改公司標識,請聯繫管理員修改。")}</div>}
        </div>

        {/* 方式一 · 上傳圖標 */}
        {canEdit && (
          <div className="panel col" style={{ padding: 18, gap: 12 }}>
            <div className="row g8"><I name="outbound" size={15}/><span style={{ fontWeight: 700, fontSize: 13.5 }}>{t("方式一 · 上傳圖標")}</span></div>
            <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>{t("任意圖片,瀏覽器內裁成 128×128 方形 PNG 入庫;超限自動降到 96 / 64,原圖不出瀏覽器。")}</div>
            <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={pickFile}/>
            {pending ? (
              <div className="col g10">
                <div className="row g14" style={{ alignItems: "flex-end" }}>
                  <img src={pending} width={64} height={64} alt=""
                    style={{ display: "block", objectFit: "cover", border: "1px solid var(--hair)", flexShrink: 0 }}/>
                  <span className="num muted" style={{ fontSize: 11 }}>{t("字符數 {n}", { n: pending.length })}</span>
                </div>
                <div className="row g6">
                  <B size="sm" kind="primary" icon="check" disabled={!!busy}
                    onClick={async () => { if (await save("upload", { type: "upload", data_url: pending }, t("已保存"))) setPending(""); }}>
                    {busy === "upload" ? t("保存中…") : t("保存")}
                  </B>
                  <B size="sm" disabled={!!busy} onClick={() => { setPending(""); setRes(null); }}>{t("取消")}</B>
                </div>
              </div>
            ) : (
              <div><B size="sm" icon="plus" disabled={!!busy} onClick={() => fileRef.current && fileRef.current.click()}>{t("選擇圖片")}</B></div>
            )}
            <Res where="upload"/>
          </div>
        )}

        {/* 方式二 · 設計字標(Swiss 字標設計器) */}
        {canEdit && (
          <div className="panel col" style={{ padding: 18, gap: 12 }}>
            <div className="row g8"><I name="layers" size={15}/><span style={{ fontWeight: 700, fontSize: 13.5 }}>{t("方式二 · 設計字標")}</span></div>
            <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55 }}>{t("1–2 個字符(字母自動大寫,支持漢字與 Emoji),Swiss 方標實時預覽。")}</div>
            <div className="row g14" style={{ alignItems: "center" }}>
              {/* 佔位態不再降透明度:半透明會把底色沖白(瑞士紅→粉),讓人誤以為預設色不準;改用虛線邊示意 */}
              <span style={{ display: "inline-block", lineHeight: 0, border: letters.trim() ? "1px solid var(--hair-soft)" : "1px dashed var(--ink-4)", flexShrink: 0 }}>
                <CM size={64} branding={{ type: "mono", letters: letters.trim() || "A", bg, fg }}/>
              </span>
              <div className="col g8" style={{ flex: 1, minWidth: 0 }}>
                <input className="field" maxLength={32} value={letters} placeholder={t("1-2 字,如 WH / 倉 / ⚡")}
                  spellCheck={false} style={{ height: 36, fontSize: 15, fontFamily: "var(--f-mono)", fontWeight: 700 }}
                  onChange={(e) => setLetters(clampMark(e.target.value.toUpperCase()))}/>
                <div className="row g6 wrap" style={{ alignItems: "center" }}>
                  <LB dim style={{ fontSize: 8.5, marginRight: 2 }}>{t("底色")}</LB>
                  {BRAND_SWATCHES.map(([name, hex]) => (
                    <button key={hex} title={t(name)} onClick={() => setBg(hex)}
                      style={{ width: 26, height: 26, background: hex, border: "1px solid var(--hair)", padding: 0, flexShrink: 0,
                        outline: bg === hex ? "2px solid var(--red)" : "none", outlineOffset: 2 }}/>
                  ))}
                </div>
                <div className="muted" style={{ fontSize: 10.5 }}>{t("字色自動對比:{c}", { c: fg === "#141414" ? t("墨") : t("紙") })}</div>
              </div>
            </div>
            <div className="row g6">
              <B size="sm" kind="primary" icon="check" disabled={!!busy || !letters.trim()}
                onClick={() => save("mono", { type: "mono", letters: letters.trim(), bg, fg }, t("已保存"))}>
                {busy === "mono" ? t("保存中…") : t("保存")}
              </B>
            </div>
            <Res where="mono"/>
          </div>
        )}
      </div>
    </Band>
  );
};

const RULE_META = [
  ["low", "低庫存自動預警", "庫存低於安全庫存時自動生成預警並推送倉管"],
  ["expire", "超期未檢提醒", "距檢驗到期 ≤15 天自動推送計量班"],
  ["abnormal", "異常出庫檢測", "出庫頻率超正常波動 3σ 觸發盤點建議"],
  ["repair", "應急缺口預測", "結合關聯地點與需求記錄預測應急物資缺口"],
  ["auto", "AI 自動草擬單據", "AI 可自動草擬補貨/調撥單(高風險仍進覆核)"],
  ["gis", "AI 托管分庫", "AI 可根據庫存資料整理倉庫、庫區與庫位關聯"],
];
const BOUNDARIES = ["禁止任意刪庫", "禁止自動大額出庫", "禁止私自改權限", "禁止繞過審批", "禁止替人簽字"];
const BIU_RULE_BOUNDARIES = [
  "僅處理 BIU 內部的案件、卷宗、程序工作、機構職位與法律倫理研究。",
  "案件材料僅限虛構、改編公開資料、已結案公開資料或獲授權匿名資料。",
  "所有職位均為 BIU 內部學術職位，不構成現實職業資格或法律授權。",
  "秘書不提供現實個案法律意見，不聯絡現實機構或當事人。",
  "程序以裁決登記、最終審查、完整性核查與歸檔為止。",
  "不同案件、職位與卷宗依原有權限隔離，任何人不得繞過。",
];
const BIU_NAV_ITEMS = [
  ["dashboard", "案件總覽"], ["tasks", "我的工作"], ["cases", "案件與卷宗"],
  ["perms", "機構與職位"], ["logs", "程序記錄"], ["settings", "規則與秘書"],
];
const BIU_PROMPT_SCOPE_SUFFIX = ".biu_legal_ethics_case_lab";
const BIU_SHARED_PROMPT_SCOPES = new Set(["explain.system", "account.preamble"]);
const BIU_GENERAL_KEYS = new Set(["sound", "dark"]);
const BIU_SYSTEM_INFO_KEYS = new Set(["系統版本", "AI 模型", "在線人員"]);
const GENERAL_META = [
  ["scan", "掃碼槍快速入口", "現場 PDA / 掃碼槍一鍵入出庫"],
  ["push", "預警消息推送", "高風險預警即時推送至負責人"],
  ["sound", "預警提示音", "新預警只向具備對應處置權限的人員播放;首次頁面互動後啟用"],
  ["dark", "深色駕駛艙模式", "切換為深色科技底色"],
];

/* 開關行(只讀呈現 + 交秘書切換);rules 為 null 時狀態未知 */
const SwitchRow = ({ idx, title, desc, val, known, onPrompt, offPrompt, checkPrompt }) => (
  <div className="ledger-row">
    <span className="lr-idx">{pad2(idx + 1)}</span>
    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
      <span style={{ fontWeight: 650, fontSize: 13.5 }}>{t(title)}</span>
      {!!desc && <span className="muted" style={{ fontSize: 11.5 }}>{t(desc)}</span>}
    </div>
    {known
      ? (val ? <T tone="ok" dot>{t("開啟")}</T> : <T tone="plain">{t("關閉")}</T>)
      : <span className="num muted" style={{ fontSize: 12 }}>—</span>}
    <B size="sm" onClick={() => ask(known ? (val ? offPrompt : onPrompt) : checkPrompt)}>
      {known ? (val ? t("交秘書關閉") : t("交秘書開啟")) : t("交秘書調整")}
    </B>
  </div>
);

const MiniHead = ({ label, count, right }) => (
  <div className="row spread" style={{ borderTop: "2px solid var(--rule)", padding: "10px 0", marginBottom: 2 }}>
    <div className="row g10"><LB>{label}</LB><span className="num muted" style={{ fontSize: 11 }}>{count}</span></div>
    {right}
  </div>
);

const Page = ({ boot, isOwner, templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const bt = boot || {};
  const [cfg, setCfg] = _s(null);          // /api/settings
  const [brandCfg, setBrandCfg] = _s(null); // /api/company/branding
  const [ds, setDs] = _s(null);            // /api/integrations/deepseek
  const [vis, setVis] = _s({});
  const [voi, setVoi] = _s({});
  const [web, setWeb] = _s({});
  const [voiceStat, setVoiceStat] = _s({});
  const [health, setHealth] = _s({});
  const [nav, setNav] = _s({});
  const [prompts, setPrompts] = _s({});
  const [permMeta, setPermMeta] = _s({});
  const [rev, setRev] = _s(0);

  _e(() => {
    W2.json("/api/settings").then(d => setCfg(d || {})).catch(() => setCfg({}));
    W2.json("/api/company/branding").then(d => setBrandCfg((d && d.branding) || null)).catch(() => setBrandCfg(null));
    W2.json("/api/integrations/deepseek").then(d => setDs((d && d.deepseek) || {})).catch(() => setDs({}));
    W2.json("/api/integrations/vision").then(d => setVis((d && d.vision) || {})).catch(() => setVis({}));
    W2.json("/api/integrations/voice").then(d => setVoi((d && d.voice) || {})).catch(() => setVoi({}));
    W2.json("/api/integrations/tavily").then(d => setWeb((d && d.tavily) || {})).catch(() => setWeb({}));
    W2.json("/api/voice/status").then(d => setVoiceStat(d || {})).catch(() => setVoiceStat({}));
    W2.json("/api/ai/health").then(d => setHealth(d || {})).catch(() => setHealth({}));
    W2.json("/api/nav").then(d => setNav(d || {})).catch(() => setNav({}));
    W2.json("/api/prompts").then(d => setPrompts(d || {})).catch(() => setPrompts({}));
    W2.json("/api/permissions").then(d => {
      const m = {};
      ((d && d.permissions) || []).forEach(p => { if (p && p.key) m[p.key] = p; });
      setPermMeta(m);
    }).catch(() => setPermMeta({}));
  }, [rev]);

  /* 秘書切換 sound/dark 後由 App 的輕量運行設定同步即時回填，不必手動刷新。 */
  _e(() => {
    const sync = (event) => {
      const next = event && event.detail;
      if (!next || typeof next !== "object") return;
      setCfg(prev => ({
        ...(prev || {}),
        general: { ...(((prev || {}).general) || {}), sound: !!next.sound, dark: !!next.dark },
      }));
    };
    window.addEventListener("w2-runtime-preferences", sync);
    return () => window.removeEventListener("w2-runtime-preferences", sync);
  }, []);

  const c = cfg || {};
  /* 倉庫:settings 富形狀優先,bootstrap 名單兜底(可能是純字串) */
  const asObj = (x) => (typeof x === "string" ? { name: x } : (x && typeof x === "object" ? x : {}));
  const whs = ((Array.isArray(c.warehouses) && c.warehouses.length)
    ? c.warehouses
    : (Array.isArray(bt.WAREHOUSES) ? bt.WAREHOUSES : [])).map(asObj);
  const cats = ((Array.isArray(c.ledger_categories) && c.ledger_categories.length)
    ? c.ledger_categories
    : (Array.isArray(bt.LEDGER_CATEGORIES) ? bt.LEDGER_CATEGORIES : [])).map(asObj);
  const roles = ((Array.isArray(c.roles) && c.roles.length) ? c.roles : (Array.isArray(bt.ROLES) ? bt.ROLES : []))
    .map(asObj).map(r => ({ id: r.id, name: r.name || r.role_name || "—", level: r.level, perms: Array.isArray(r.perms) ? r.perms : [] }));
  const rules = c.ai_rules && typeof c.ai_rules === "object" ? c.ai_rules : null;
  const gen = c.general && typeof c.general === "object" ? c.general : null;
  /* 去品牌鐵律:後端 system_info 的「AI 模型」值是真實模型名(帶供應商),對用戶只顯示通用名 */
  const sysInfo = (Array.isArray(c.system_info) ? c.system_info : []).map(p =>
    (p && p[0] === "AI 模型" && p[1] && p[1] !== "—") ? [p[0], t("智能引擎")] : p);
  const visibleSysInfo = biu
    ? sysInfo.filter(pair => pair && BIU_SYSTEM_INFO_KEYS.has(pair[0]))
    : sysInfo;
  const dsSt = (ds && Object.keys(ds).length ? ds : c.deepseek) || {};
  /* 公司標識僅 L5 / 平臺所有者可改;其餘人只讀預覽 */
  const me = window.W2_USER || {};
  const canBrand = !!isOwner || Math.max(0, ...((Array.isArray(me.roles) ? me.roles : []).map(r => Number(r.level) || 0))) >= 5;

  const engines = [connState(dsSt), connState(vis), connState(voi), connState(web)];
  const connectedN = engines.filter(e => e.connected).length;
  const anyFailed = engines.some(e => e.failed);
  const zonesTotal = whs.reduce((s, w) => s + num(w.zones), 0);
  const returnableN = cats.filter(x => x.requires_return || x.requiresReturn).length;

  /* 導航目錄分組 */
  const navGroups = _mm(() => {
    if (biu) return [{
      group: "固定六項法律工作區",
      items: BIU_NAV_ITEMS.map(([id, label], order) => ({ id, label, original: label, renamed: false, hidden: false, order })),
    }];
    const catalog = (nav && Array.isArray(nav.catalog)) ? nav.catalog : [];
    const items = (nav && nav.config && nav.config.items && typeof nav.config.items === "object") ? nav.config.items : {};
    const order = [], by = {};
    catalog.forEach((it, i) => {
      if (!it || !it.id) return;
      const g = it.group || "—";
      if (!by[g]) { by[g] = []; order.push(g); }
      const ov = items[it.id] || {};
      by[g].push({
        id: it.id,
        label: ov.label || it.default_label || it.id,
        original: it.default_label || it.id,
        renamed: !!ov.label && ov.label !== it.default_label,
        hidden: !!ov.hidden,
        order: ov.order != null ? ov.order : i,
      });
    });
    return order.map(g => ({ group: g, items: by[g].slice().sort((a, b) => a.order - b.order) }));
  }, [nav, biu]);
  const navFlat = navGroups.reduce((a, g) => a.concat(g.items), []);
  const renamedN = navFlat.filter(x => x.renamed).length;
  const hiddenN = navFlat.filter(x => x.hidden).length;

  /* 提示詞:按 scope 聚合(現行版 + 版本數) */
  const promptScopes = _mm(() => {
    const rows = (prompts && Array.isArray(prompts.rows)) ? prompts.rows : [];
    const order = [], map = {};
    rows.forEach(r => {
      if (!r) return;
      const k = r.scope_key || "—";
      if (biu && !(k.endsWith(BIU_PROMPT_SCOPE_SUFFIX) || BIU_SHARED_PROMPT_SCOPES.has(k))) return;
      if (!map[k]) { map[k] = { scope: k, layer: r.layer || "—", versions: 0, active: null, latest: null }; order.push(k); }
      const e = map[k];
      e.versions += 1;
      if (r.active) e.active = r;
      if (!e.latest || num(r.version) > num(e.latest.version)) e.latest = r;
    });
    return order.map(k => { const e = map[k]; return { ...e, cur: e.active || e.latest || {} }; });
  }, [prompts, biu]);

  const generalMeta = biu ? GENERAL_META.filter(([key]) => BIU_GENERAL_KEYS.has(key)) : GENERAL_META;

  const roleStats = (perms) => {
    let cli = 0, danger = 0;
    perms.forEach(k => {
      const p = permMeta[k];
      if (p && p.kind === "cli") { cli += 1; if (p.critical || p.risk === "critical" || p.risk === "high") danger += 1; }
    });
    return { total: perms.length, cli, danger };
  };

  const healthReady = health && (health.status || health.model || health.search_documents != null);
  const healthCells = [
    ["狀態", healthReady ? (health.status || "—") : "—"],
    ["知識文檔", healthReady ? num(health.search_documents) : "—"],
    ["行動計劃", healthReady ? num(health.plans) : "—"],
    ["活躍對話", healthReady ? num(health.conversations) : "—"],
    ["記憶", healthReady ? num(health.memories) : "—"],
    ["經驗", healthReady ? num(health.lessons) : "—"],
  ];

  return (
    <>
      <Folio no="18" en="SETTINGS" title={settingsText(biu, "設置")}
        sub={settingsText(biu, "系統配置一頁盡覽:AI 密鑰 · 監測規則 · 倉庫 · 分類 · 導航 · 提示詞 · 通用開關 · 公司標識;僅 AI 密鑰與公司標識可在此直接配置,其餘改動一律交秘書執行留痕。")}
        right={<>
          <B icon="refresh" onClick={() => setRev(r => r + 1)}>{t("刷新")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(t(biu
            ? "檢查 BIU 法律工作區的 CASE、RECORD、TASK、機構職位、權限、指令集與 AI 連接，列出需要核查之處。"
            : "檢查系統設置:AI 密鑰連接、監測規則、倉庫與分類配置,有什麼需要完善的?"))}>{t("問秘書")}</B>
        </>}/>

      <div className="kpi-band">
        {biu ? <>
          <Kpi label={t("法律倫理規則")} value={BIU_RULE_BOUNDARIES.length} unit={t("條")} delay={0}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("固定學術邊界")}</span>}/>
          <Kpi label={t("機構與職位")} value={roles.length} unit={t("類")} delay={.05}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("學術職位 · 權限依案件與機構範圍分級")}</span>}/>
          <Kpi label={t("秘書記憶")} value={healthReady ? num(health.memories) : "—"} unit={t("條")} delay={.1}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("指令集 {n} 組", { n: promptScopes.length })}</span>}/>
        </> : <>
          <Kpi label={t("在管倉庫")} value={whs.length} unit={t("個")} delay={0}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("共 {n} 個功能區", { n: zonesTotal })}</span>}/>
          <Kpi label={t("物資分類")} value={cats.length} unit={t("類")} delay={.05}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("需歸還 {n} 類", { n: returnableN })}</span>}/>
          <Kpi label={t("權限角色")} value={roles.length} unit={t("類")} delay={.1}
            foot={<span className="muted" style={{ fontSize: 11.5 }}>{t("分級授權 · 高危可見")}</span>}/>
        </>}
        <Kpi label={t("AI 連接")} value={connectedN} unit={t("/{n} 已連接", { n: engines.length })} red={anyFailed} delay={.15}
          foot={connectedN === engines.length ? <T tone="ok" dot>{t("全部就緒")}</T> : anyFailed ? <T tone="bad" dot>{t("有連接失敗")}</T> : <T tone="warn" dot>{t("有待配置")}</T>}/>
      </div>

      {/* 01 · AI 引擎與全局密鑰 */}
      <Band no="01" title={settingsText(biu, "AI 引擎與全局密鑰")} sub={t("管理員配置一次 · 公司內共用 · 密鑰加密入庫")} delay={.05}
        right={<B size="sm" icon="sparkle" onClick={() => ask(t(biu
          ? "檢查 BIU 秘書的指令集、記憶與連接狀態，只彙報法律倫理學術工作範圍。"
          : "跑一次 AI 資料庫自檢,把結果彙報給我"))}>{t("自檢")}</B>}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
          <ConnPanel icon="cpu" title="智能引擎" st={dsSt} modelOverride={t("智能引擎")}
            service="deepseek" onStatus={(v) => setDs(v || {})}
            sub={t("驅動秘書對話與智能分析,全公司共用一把全局 key。")}
            extra={<div className="row g6 wrap">
              <T tone="plain">{t("均衡 · Flash")}</T>
              <T tone="plain">{t("Thinking · Pro")}</T>
              <T tone="plain">{t("記憶 · Flash 後台蒸餾")}</T>
            </div>}/>
          <ConnPanel icon="eye" title="圖片識別" st={vis} modelOverride={t("自動適配")}
            service="vision" onStatus={(v) => setVis(v || {})}
            sub={t("圖片識別共用密鑰,後端按接入地址自動識別供應商。")}/>
          <ConnPanel icon="bell" title="語音功能" st={voi} modelOverride={t("自動適配")}
            service="voice" onStatus={(v) => setVoi(v || {})} onCapability={(v) => setVoiceStat(v || {})}
            sub={t("語音識別與朗讀共用密鑰,未配置時自動降級瀏覽器原生語音。")}
            extra={<div className="row g6">
              <T tone={voiceStat.asr ? "ok" : "plain"} dot>{t("識別")}</T>
              <T tone={voiceStat.tts ? "ok" : "plain"} dot>{t("朗讀")}</T>
            </div>}/>
          <ConnPanel icon="search" title="Web 搜索" st={web} modelOverride="Tavily Search"
            service="tavily" onStatus={(v) => setWeb(v || {})} keyPlaceholder="tvly-…"
            sub={t(biu ? "公開搜索僅用於已結案公開資料的學術線索，不作現實個案工作。" : "Tavily 為 AI 秘書提供最新公開 Web 資訊;搜索結果只作外部線索。")}/>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "110px repeat(6, 1fr)", borderTop: "1px solid var(--hair)", marginTop: 18, paddingTop: 12, gap: 8, alignItems: "center" }}>
          <LB dim>{t("AI 運行時")}</LB>
          {healthCells.map(([k, v]) => (
            <div key={k} className="col g4">
              <LB dim style={{ fontSize: 8.5 }}>{t(k)}</LB>
              <span className="num" style={{ fontSize: 15, fontWeight: 700 }}>{v}</span>
            </div>
          ))}
        </div>
        {!healthReady && <div className="muted" style={{ fontSize: 11, marginTop: 8 }}>{t("運行時暫無數據")}</div>}
      </Band>

      {/* 02 · AI 監測規則與操作邊界 */}
      <Band no="02" title={settingsText(biu, "AI 監測規則與操作邊界")} sub={settingsText(biu, "規則開關持久化 · 邊界不可逾越")} delay={.1}>
        {biu ? <div className="col g12">
          <div className="row g8"><I name="shield" size={15} color="var(--red)"/><LB red>{t("固定學術邊界")}</LB></div>
          <div className="muted" style={{ fontSize: 11.5 }}>{t("以下邊界由 BIU 模板固定，不在此切換。")}</div>
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {BIU_RULE_BOUNDARIES.map((boundary, i) => (
              <div key={boundary} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <I name="checkCircle" size={14} color="var(--red)"/>
                <span style={{ fontSize: 12.5, fontWeight: 650 }}>{t(boundary)}</span>
                <T tone="plain">FIXED</T>
              </div>
            ))}
          </div>
        </div> : <div style={{ display: "grid", gridTemplateColumns: "1.7fr 1fr", gap: 28, alignItems: "start" }}>
          <div>
            {!rules && <div className="muted" style={{ fontSize: 11.5, padding: "0 0 10px" }}>{t("後端未返回規則配置,以下為規則目錄;可讓秘書逐條查證。")}</div>}
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {RULE_META.map(([k, title, desc], i) => (
                <SwitchRow key={k} idx={i} title={title} desc={desc}
                  known={!!rules && rules[k] != null} val={!!(rules && rules[k])}
                  onPrompt={t("把 AI 監測規則「{name}」打開", { name: t(title) })}
                  offPrompt={t("把 AI 監測規則「{name}」關閉", { name: t(title) })}
                  checkPrompt={t("查一下 AI 監測規則「{name}」現在的狀態,告訴我要不要開", { name: t(title) })}/>
              ))}
            </div>
          </div>
          <div className="panel col" style={{ padding: 18, gap: 12 }}>
            <div className="row g8"><I name="shield" size={15} color="var(--red)"/><LB red>{t("AI 操作邊界")}</LB></div>
            <div className="muted" style={{ fontSize: 11.5 }}>{t("安全紅線 · 任何人不可越過")}</div>
            <div className="col g8">
              {BOUNDARIES.map(b => (
                <div key={b} className="row g8" style={{ borderTop: "1px solid var(--hair-soft)", paddingTop: 8 }}>
                  <span style={{ width: 6, height: 6, background: "var(--red)", flexShrink: 0 }}/>
                  <span style={{ fontSize: 12.5, fontWeight: 650 }}>{t(b)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>}
      </Band>

      {/* 03 · 倉庫與物資分類 */}
      {!biu && <Band no="03" title={t("倉庫與物資分類")} sub={t("倉庫檔案 · 分類驅動庫存組織與 AI")} delay={.12}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 28, alignItems: "start" }}>
          <div>
            <MiniHead label={t("在管倉庫")} count={whs.length}
              right={<B size="sm" icon="plus" onClick={() => ask(t("新增一個倉庫,幫我登記名稱、編碼和容量使用率"))}>{t("新增倉庫")}</B>}/>
            {whs.length ? whs.map((w, i) => (
              <div key={w.id || w.name || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span className="row g8" style={{ fontWeight: 650, fontSize: 13.5 }}>
                    {w.name || "—"}{(w.main || w.is_default) && <T tone="inv">{t("默認庫")}</T>}
                  </span>
                  <span className="num muted" style={{ fontSize: 11 }}>
                    {(w.code || "—") + " · " + t("{n} 個功能區", { n: num(w.zones) })}
                  </span>
                </div>
                <div className="col g4" style={{ width: 120 }}>
                  <span className="muted num" style={{ fontSize: 10.5 }}>{t("容量")} {w.cap != null ? num(w.cap) + "%" : "—"}</span>
                  <div className="bar"><i style={{ width: Math.min(100, num(w.cap)) + "%", background: num(w.cap) >= 90 ? "var(--red)" : "var(--ink)" }}/></div>
                </div>
                <div className="row g4">
                  <B size="sm" onClick={() => ask(t("編輯倉庫「{name}」的資料(名稱/編碼/容量使用率),先展示現在的值", { name: w.name || "—" }))}>{t("編輯")}</B>
                  {w.can_delete === false
                    ? <T tone="plain">{t("受保護")}</T>
                    : <B size="sm" kind="red" onClick={() => ask(t("刪除倉庫「{name}」,先告訴我會影響哪些數據再執行", { name: w.name || "—" }))}>{t("刪除")}</B>}
                </div>
              </div>
            )) : <EM icon="building" title={t("暫無倉庫檔案")} sub={t("對秘書說「新增倉庫」即可建立。")}/>}
          </div>
          <div>
            <MiniHead label={t("物資分類")} count={cats.length}
              right={<B size="sm" icon="plus" onClick={() => ask(t("新增一個物資分類,幫我定分類代碼、名稱和是否需歸還"))}>{t("新增分類")}</B>}/>
            {cats.length ? cats.map((cItem, i) => (
              <div key={cItem.id || i} className="ledger-row">
                <span className="lr-idx">{pad2(i + 1)}</span>
                <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                  <span className="row g8" style={{ fontWeight: 650, fontSize: 13.5 }}>
                    {cItem.name || "—"}
                    {(cItem.requires_return || cItem.requiresReturn)
                      ? <T tone="warn">{t("需歸還")}</T>
                      : <T tone="plain">{t("消耗")}</T>}
                  </span>
                  <span className="num muted" style={{ fontSize: 11 }}>{cItem.id || "—"}{cItem.description ? " · " + cItem.description : ""}</span>
                </div>
                <div className="row g4">
                  <B size="sm" onClick={() => ask(t("編輯分類「{name}」(名稱/是否需歸還/說明),先展示現在的設定", { name: cItem.name || "—" }))}>{t("編輯")}</B>
                  <B size="sm" kind="red" onClick={() => ask(t("刪除分類「{name}」,若分類下還有數據先告訴我影響", { name: cItem.name || "—" }))}>{t("刪除")}</B>
                </div>
              </div>
            )) : <EM icon="layers" title={t("暫無分類")} sub={t("對秘書說「幫我建物資分類」即可開始。")}/>}
          </div>
        </div>
      </Band>}

      {/* 04 · 權限角色 */}
      <Band no="04" title={settingsText(biu, "權限角色")} sub={settingsText(biu, "分級授權 · CLI 高危能力一眼可見")} delay={.14}
        right={<B size="sm" icon="plus" onClick={() => ask(t(biu
          ? "新增一個 BIU 學術職位，先說明所屬機構、申請方式、等級與案件權限。"
          : "新增一個權限角色,幫我配置名稱、等級和權限清單"))}>{t("新增角色")}</B>}>
        {roles.length ? (
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {roles.map((r, i) => {
              const st = roleStats(r.perms);
              return (
                <div key={r.id || i} className="ledger-row">
                  <span className="lr-idx">{pad2(i + 1)}</span>
                  <div className="row g10" style={{ flex: 1, minWidth: 0, flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 650, fontSize: 13.5 }}>{r.name}</span>
                    <T tone="inv">L{num(r.level) || "—"}</T>
                  </div>
                  {biu ? <div className="row g6 wrap">
                    <T tone="plain">{t("職位權限 {n} 項", { n: st.total })}</T>
                  </div> : <div className="row g6 wrap">
                    <T tone="plain">{t("業務權限 {n} 項", { n: Math.max(0, st.total - st.cli) })}</T>
                    {st.cli > 0 ? <T tone="warn">{t("CLI {n} 項", { n: st.cli })}</T> : <T tone="plain">{t("無 CLI 高危能力")}</T>}
                    {st.danger > 0 && <T tone="bad" dot>{t("高危 {n} 項", { n: st.danger })}</T>}
                  </div>}
                  <B size="sm" icon="shield" onClick={() => ask(t(biu
                    ? "調整 BIU 學術職位「{name}」的案件、卷宗與機構權限，先列出現有配置。"
                    : "調整角色「{name}」的權限配置,先列出它現在有哪些權限", { name: r.name }))}>{t("交秘書配置")}</B>
                </div>
              );
            })}
          </div>
        ) : <EM icon="shield" title={t("暫無角色")} sub={t("對秘書說「新增角色」即可配置分級授權。")}/>}
      </Band>

      {/* 05 · 導航設計 */}
      <Band no="05" title={settingsText(biu, "導航設計")} sub={settingsText(biu, "AI 依行業編排側欄:改名 / 排序 / 隱藏")} delay={.16}
        right={biu ? <T tone="plain">{t("固定六項法律工作區")}</T> : <>
          <B size="sm" icon="sparkle" onClick={() => ask(t("讓 AI 根據我們公司的行業重新設計側欄導航(改名/排序/隱藏),先給我預覽再保存"))}>{t("AI 設計導航")}</B>
          <B size="sm" icon="refresh" onClick={() => ask(t("把側欄導航還原成默認配置"))}>{t("還原默認")}</B>
        </>}>
        {navFlat.length ? (
          <div className="col g14">
            <div className="row g10 wrap">
              <T tone="plain">{t("{n} 個導航項", { n: navFlat.length })}</T>
              <T tone={renamedN ? "warn" : "plain"}>{t("改名 {n}", { n: renamedN })}</T>
              <T tone={hiddenN ? "warn" : "plain"}>{t("隱藏 {n}", { n: hiddenN })}</T>
            </div>
            {navGroups.map(g => (
              <div key={g.group} className="col g8">
                <LB dim style={{ fontSize: 8.5 }}>{t(String(g.group || "—"))}</LB>
                <div className="row g6 wrap">
                  {g.items.map(it => (
                    <span key={it.id} className="chip" title={it.renamed ? it.original + " → " + it.label : it.id}
                      style={it.hidden ? { opacity: .4, textDecoration: "line-through" } : undefined}>
                      {it.renamed && <span style={{ width: 6, height: 6, background: "var(--red)", flexShrink: 0 }}/>}
                      {it.label}
                    </span>
                  ))}
                </div>
              </div>
            ))}
            <div className="muted" style={{ fontSize: 10.5 }}>{t(biu ? "BIU 導航由模板固定為六項，不在此切換。" : "紅塊=已改名 · 劃線=已隱藏 · 「設置」受保護不可隱藏")}</div>
          </div>
        ) : (
          <EM icon="layers" title={t("導航目錄未返回")} sub={t("後端未返回導航目錄;可直接讓秘書設計或還原導航。")}
            action={<B size="sm" icon="sparkle" onClick={() => ask(t("讓 AI 根據我們公司的行業重新設計側欄導航(改名/排序/隱藏),先給我預覽再保存"))}>{t("AI 設計導航")}</B>}/>
        )}
      </Band>

      {/* 06 · 提示詞層 */}
      <Band no="06" title={settingsText(biu, "提示詞層")} sub={t("L0/L1/L2 版本化 · 改動可回滾")} delay={.18}>
        {promptScopes.length ? (
          <div style={{ overflowX: "auto" }}>
            <table className="tbl2">
              <thead><tr>
                <th>{t("作用域")}</th><th>{t("層")}</th><th>{t("現行版本")}</th><th>{t("版本數")}</th><th>{t("字數")}</th><th>{t("更新於")}</th><th>{t("更新人")}</th><th style={{ width: 150 }}>{t("交給秘書")}</th>
              </tr></thead>
              <tbody>
                {promptScopes.map((p) => (
                  <tr key={p.scope}>
                    <td><span className="num" style={{ fontWeight: 650 }}>{p.scope}</span></td>
                    <td><T tone="plain">{p.cur.layer || p.layer}</T></td>
                    <td><span className="num" style={{ fontWeight: 700 }}>v{num(p.cur.version) || "—"}</span></td>
                    <td className="num muted">{p.versions}</td>
                    <td className="num muted">{p.cur.content_length != null ? num(p.cur.content_length) : "—"}</td>
                    <td className="num muted" style={{ fontSize: 12 }}>{p.cur.updated_at || "—"}</td>
                    <td className="muted" style={{ fontSize: 12 }}>{p.cur.updated_by || "—"}</td>
                    <td>
                      <div className="row g4">
                        <B size="sm" onClick={() => ask(t(biu
                          ? "調整 BIU 指令集「{scope}」：先顯示現行版本，只討論 CASE、RECORD、TASK、機構職位、權限、連接與法律倫理邊界。"
                          : "調整提示詞「{scope}」:先給我看現行版本的內容,再說怎麼改", { scope: p.scope }))}>{t("調整")}</B>
                        <B size="sm" onClick={() => ask(t(biu
                          ? "把 BIU 指令集「{scope}」回滾到上一版本，先列出版本歷史並確認只影響 BIU。"
                          : "把提示詞「{scope}」回滾到上一個版本,先列出版本歷史", { scope: p.scope }))}>{t("回滾")}</B>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : <EM icon="doc" title={t("暫無提示詞版本")} sub={t("運行時以資料庫為準;讓秘書初始化或調整提示詞即可。")}/>}
      </Band>

      {/* 07 · 通用與系統 */}
      <Band no="07" title={t("通用與系統")} sub={settingsText(biu, "交互開關 · 系統信息 · 數據導出")} delay={.2}>
        <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr", gap: 28, alignItems: "start" }}>
          <div>
            <MiniHead label={t("通知與交互")} count={generalMeta.length}/>
            {generalMeta.map(([k, rawTitle, rawDesc], i) => {
              const title = biu && k === "sound" ? "提示音" : biu && k === "dark" ? "深色工作區模式" : rawTitle;
              const desc = biu && k === "sound" ? "程序提醒提示音；首次頁面互動後啟用" : biu && k === "dark" ? "切換為深色工作區底色" : rawDesc;
              return (
              <SwitchRow key={k} idx={i} title={title} desc={desc}
                known={!!gen && gen[k] != null} val={!!(gen && gen[k])}
                onPrompt={t(biu
                  ? "在 BIU 法律工作區開啟界面偏好「{name}」；只調整本公司界面，不改變 CASE、RECORD、TASK、機構職位、權限或指令集。"
                  : "把通用設置「{name}」打開", { name: t(title) })}
                offPrompt={t(biu
                  ? "在 BIU 法律工作區關閉界面偏好「{name}」；只調整本公司界面，不改變 CASE、RECORD、TASK、機構職位、權限或指令集。"
                  : "把通用設置「{name}」關閉", { name: t(title) })}
                checkPrompt={t(biu
                  ? "查閱 BIU 法律工作區界面偏好「{name}」的狀態；只回覆本公司設定。"
                  : "查一下通用設置「{name}」現在的狀態,告訴我要不要開", { name: t(title) })}/>
            );})}
          </div>
          <div className="col g16">
            <div>
              <MiniHead label={t("系統信息")} count={visibleSysInfo.length}/>
              {visibleSysInfo.length ? (
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  {visibleSysInfo.map((pair, i) => (
                    <div key={i} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
                      <LB dim style={{ fontSize: 8.5 }}>{t(String((pair && pair[0]) || "—"))}</LB>
                      <span className="num" style={{ fontSize: 13.5, fontWeight: 650 }}>{(pair && pair[1]) || "—"}</span>
                    </div>
                  ))}
                </div>
              ) : <div className="muted" style={{ fontSize: 11.5 }}>{t("後端未返回系統信息。")}</div>}
            </div>
            {!biu && <div className="panel col" style={{ padding: 16, gap: 10 }}>
              <LB>{t("資料庫 CSV 導出")}</LB>
              <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{t("整庫導出 zip:每表一個 CSV + schema + manifest;含敏感表,注意保密。")}</div>
              <div><B size="sm" icon="outbound" onClick={() => ask(t("把當前公司資料庫導出成 CSV 壓縮包,告訴我怎麼拿到文件"))}>{t("交秘書導出")}</B></div>
            </div>}
            <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>{t("2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。")}</div>
          </div>
        </div>
      </Band>

      {/* 08 · 公司標識(直寫例外:公司配置;置底 — 一次配好極少再動) */}
      <BrandingBand branding={brandCfg} canEdit={canBrand} onSaved={(b) => setBrandCfg(b)}/>
    </>
  );
};

window.W2.PAGES["settings"] = Page;
})();
