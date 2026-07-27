/* WAREHOUSE 2.0 · 權限(Folio 13 · ACCESS)— Swiss 版式,真後端
   模板控制台:目錄(/api/org/templates)· 差異預覽(/api/org/template-preview)· 確認套用(/api/org/apply-template)
   讀視圖:成員清單(/api/users,退回 boot.PEOPLE)· 註冊/加入審批(/api/auth/registrations、/api/memberships/pending)
   · 角色×等級矩陣(topology/users/boot.ROLES)· 權限分享(/api/permissions/topology)
   組織拓撲支援手動編輯與秘書指令:部門/崗位 CRUD、人員移動、部門權限上限與人員直接權限 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "權限": "Access",
  "模板控制台 · 成員 · 角色 · 審批 · 權限分享 —— 模板確認套用,細項交秘書調整": "Template console · members · roles · approvals · delegation — apply templates with confirmation, tune details via the Secretary",
  "模板 · 組織拓撲 · 部門上限 · 人員權限 —— 可視化手動編輯,同一指令亦可交秘書執行": "Templates · organisation topology · department ceilings · member access — edit visually or run the same operations through the Secretary",
  "行業模板控制台": "Industry template console",
  "選擇預設,先預覽部門、崗位、角色、事務與檔案分類差異,確認後再套用": "Choose a preset, preview organisation, case and record-catalogue changes, then confirm before applying",
  "選擇行業模板": "Choose industry template",
  "目前使用": "Current",
  "已生效": "Active",
  "模板目錄載入中…": "Loading template catalogue…",
  "模板目錄暫不可用": "Template catalogue is temporarily unavailable",
  "沒有可用的行業模板": "No industry templates are available",
  "重試": "Retry",
  "預覽差異": "Preview changes",
  "預覽載入中…": "Loading preview…",
  "模板預覽暫不可用": "Template preview is temporarily unavailable",
  "部門新增": "Departments to add", "部門同步": "Departments to sync",
  "崗位新增": "Positions to add", "崗位同步": "Positions to sync",
  "角色新增": "Roles to add", "角色重用": "Roles to reuse",
  "事務類型新增": "Case types to add", "事務類型歸檔": "Case types to archive",
  "檔案分類新增": "Record categories to add", "檔案分類歸檔": "Record categories to archive",
  "檔案類型新增": "Record types to add", "檔案類型歸檔": "Record types to archive",
  "部門導航同步": "Department nav sync", "崗位導航同步": "Position nav sync",
  "{n} 項手動導航設定會保留,不會被行業模板覆蓋。": "{n} manual navigation settings will be preserved and not overwritten by the industry template.",
  "將歸檔 {p} 個舊崗位、{d} 個舊部門和 {c} 個舊事務類型;有成員的崗位會保留。": "{p} old positions, {d} old departments and {c} old case types will be archived; positions with members are retained.",
  "另將停用 {c} 個舊檔案分類和 {t} 個舊檔案類型;歷史檔案與類型版本不會刪除。": "{c} old record categories and {t} old record types will also be disabled; historical records and type revisions are retained.",
  "{o} 個公司自定義或已封存的同碼部門/崗位將保持不變;{c} 個舊部門因仍有下級部門而保留。": "{o} company-overridden or archived same-code departments/positions will remain unchanged; {c} old departments are retained because they still have child units.",
  "合併套用只同步模板管理的架構,保留公司自訂資料,不刪除既有業務記錄。": "Merge apply only synchronises template-managed structures, preserves company customisations, and does not delete existing business records.",
  "套用此模板": "Apply this template",
  "重新同步此模板": "Resynchronise this template",
  "確認套用「{name}」?": "Apply “{name}”?",
  "套用後會同步部門、崗位、預設角色權限、導航可見範圍、事務類型與檔案分類。": "This will synchronise organisation, access, case types and the records catalogue.",
  "當前帳號可以預覽,但沒有套用行業模板的權限。": "This account can preview templates but cannot apply them.",
  "確認套用": "Confirm apply",
  "取消": "Cancel",
  "正在套用…": "Applying…",
  "行業模板「{name}」已套用,組織與權限資料已刷新。": "Industry template “{name}” was applied; organisation and access data were refreshed.",
  "套用模板失敗": "Failed to apply template",
  "AI 協助調整": "Adjust with AI",
  "模板建立共通架構;公司特有的部門、崗位與角色權限可繼續透過 AI 精細調整。": "Templates establish the common structure; company-specific departments, positions and role permissions can then be refined with AI.",
  "AI 調整部門": "AI: departments",
  "AI 調整崗位": "AI: positions",
  "AI 調整角色權限": "AI: roles & access",
  "我要在目前的「{name}」行業模板基礎上調整公司部門設計。請先讀取現有組織結構,逐項詢問新增、改名、上級關係或停用需求,先列出變更預覽與影響,經我明確確認後再執行。": "I want to refine our department design on top of the current “{name}” industry template. Read the existing organisation first, ask about additions, renaming, parent relationships or deactivation, show a change preview and impact, then execute only after my explicit confirmation.",
  "我要在目前的「{name}」行業模板基礎上調整公司崗位設計。請先列出各部門現有崗位、主管關係、預設角色與職級,逐項確認變更並預覽人員影響,經我明確確認後再執行。": "I want to refine our position design on top of the current “{name}” industry template. First list each department’s positions, manager relationships, default roles and levels, confirm changes item by item, preview member impact, then execute only after my explicit confirmation.",
  "我要調整目前公司的角色與權限設計。請先列出角色、成員、權限和導航可見範圍,指出過度授權或缺權風險,提出最小權限方案,經我逐項確認後再執行。": "I want to refine our roles and permissions. First list roles, members, permissions and navigation visibility, flag excessive or missing access, propose a least-privilege design, then execute only after I confirm each change.",
  "組織結構": "Organisation",
  "部門 · 崗位 · 成員歸屬 —— 目前生效的行業模板結果": "Departments · positions · assignments — output of the active industry template",
  "行業模板 {name} · 版本 {version}": "Industry template {name} · version {version}",
  "部門": "Departments", "崗位": "Positions", "已分配成員": "Assigned members", "未分配成員": "Unassigned members",
  "組織結構載入中…": "Loading organisation…", "組織結構暫不可用": "Organisation is temporarily unavailable",
  "刷新後仍無法讀取時,請確認當前帳號具有組織查看權限。": "If refresh still fails, check that this account can view the organisation.",
  "尚未建立部門": "No departments yet", "尚未建立崗位": "No positions yet", "尚未分配成員": "No member assignments yet",
  "部門名稱": "Department", "部門代碼": "Department code", "類型": "Type", "上級部門": "Parent", "負責人": "Manager", "說明": "Description",
  "崗位名稱": "Position", "崗位代碼": "Position code", "所屬部門": "Department", "預設角色": "Default role", "主管崗位": "Manager position",
  "BIU 內部學術": "BIU internal academics",
  "直接加入": "Direct entry", "申請審核": "Application", "資格測評": "Exam", "機構委任": "Appointment",
  "權限層級": "Access tier", "目錄公開": "Public", "目錄鎖定": "Locked", "目錄隱藏": "Hidden",
  "BIU 職位僅用於內部法律與倫理學術工作；不代表現實司法身分、執業資格或公共權力。": "BIU positions are solely for internal academic work in law and ethics; they do not represent real judicial identity, professional qualification, or public authority.",
  "成員歸屬": "Member assignments", "主要歸屬": "Primary", "是": "Yes", "否": "No", "人數": "People",
  "交秘書檢查": "Ask Secretary to check",
  "檢查目前行業模板生成的部門、崗位與成員歸屬,列出未分配人員、缺少負責人的部門與權限風險;先給我建議,不要直接修改": "Review the departments, positions and member assignments generated by the current industry template. List unassigned users, departments without managers and access risks; advise me first and do not modify anything.",
  "互動組織權限拓撲": "Interactive organisation & access topology",
  "公司 → 部門 → 崗位 → 人員;點擊節點查看與編輯,權限由部門上限向下約束": "Company → department → position → people; select a node to inspect or edit it, with access constrained by the department ceiling",
  "拓撲圖": "Topology", "詳情與編輯": "Details & editing",
  "縮小": "Zoom out", "放大": "Zoom in", "重設視圖": "Reset view", "搜索拓撲節點": "Search topology nodes",
  "單擊節點查看詳情;雙擊或使用箭頭展開 / 收起下級。": "Select a node for details; double-click it or use the arrow to expand/collapse descendants.",
  "公司根節點": "Company root", "未分配": "Unassigned", "未分配成員": "Unassigned members",
  "展開下級": "Expand descendants", "收起下級": "Collapse descendants", "已選擇": "Selected",
  "新增部門": "Add department", "新增下級部門": "Add subdepartment", "編輯部門": "Edit department", "封存部門": "Archive department",
  "新增崗位": "Add position", "編輯崗位": "Edit position", "封存崗位": "Archive position",
  "返回詳情": "Back to details", "儲存變更": "Save changes", "建立部門": "Create department", "建立崗位": "Create position",
  "操作成功,組織拓撲已刷新。": "Saved successfully; the organisation topology has been refreshed.", "操作失敗": "Operation failed",
  "確認封存部門「{name}」?封存前必須先遷移其人員、崗位、下級部門及業務引用。": "Archive department “{name}”? Its people, positions, child departments and business references must be moved first.",
  "確認封存崗位「{name}」?封存前必須先將崗位內人員移走。": "Archive position “{name}”? Its members must be reassigned first.",
  "基本資料": "Basic details", "部門類型": "Department type", "選擇上級部門": "Choose parent department", "選擇角色": "Choose role",
  "自動生成": "Generated automatically", "公司直屬": "Reports to company", "無預設角色": "No default role", "主管崗位標記": "Manager position",
  "工作流節點職責": "Workflow node responsibilities",
  "按節點類型與階段顯示；責任綁定以採購工作流節點設定為唯一事實來源，本頁不另存副本。": "Grouped by node type and stage. Procurement workflow node settings are the single source of truth for responsibility bindings; this page stores no duplicate copy.",
  "暫無已綁定的工作流節點": "No workflow nodes are currently assigned",
  "節點類型": "Node type", "流程階段": "Workflow stage", "未指定階段": "No stage", "一般節點": "General node",
  "工作流已停用": "Workflow disabled", "節點已停用": "Node disabled", "所需權限": "Required permission", "綁定來源": "Binding source",
  "前往節點配置": "Open node configuration", "交秘書配置": "Configure with Secretary",
  "我要調整崗位「{name}」（崗位代碼：{code}）的工作流節點職責。請先讀取現有 workflow 與 node binding，以採購工作流節點配置為唯一事實來源，逐項列出 workflow_key、node_key、node_kind、stage_key、目前的 department/position binding 與權限影響；先給出變更預覽，經我逐項明確確認後才修改。不得在崗位資料建立或複製第二套職責表。": "I want to change workflow-node responsibilities for position “{name}” (position code: {code}). First read the existing workflow and node bindings. Treat procurement workflow node configuration as the single source of truth, and list each workflow_key, node_key, node_kind, stage_key, current department/position binding, and access impact. Show a change preview first and modify only after my explicit item-by-item confirmation. Do not create or copy a second responsibility table into the position record.",
  "請選擇所屬部門": "Choose a department",
  "目前沒有可用部門。請先返回並新增或啟用部門，再建立崗位。": "No active department is available. Go back and add or enable a department before creating a position.",
  "請填寫部門名稱。": "Enter a department name.", "請填寫崗位名稱。": "Enter a position name.",
  "請選擇有效的所屬部門。": "Choose a valid active department.",
  "職級必須是 1 至 10 的整數。": "Level must be an integer from 1 to 10.",
  "部門權限上限": "Department permission ceiling", "啟用權限上限": "Enable permission ceiling",
  "一般人員的有效權限受此上限約束；L10/L11 身份可跨部門掛職，且不因部門權限上限而降級；崗位角色仍按治理規則同步。": "Regular members remain constrained by this ceiling. L10/L11 identities may hold cross-department appointments and are not downgraded by the department ceiling; position roles still synchronise under governance rules.",
  "搜索權限": "Search permissions", "全選可見": "Select visible", "清除": "Clear", "儲存權限上限": "Save permission ceiling",
  "尚未設定權限上限": "No permission ceiling configured", "已啟用上限": "Ceiling enabled", "未啟用上限": "Ceiling disabled",
  "直接權限調整": "Direct permission overrides", "允許": "Allow", "拒絕": "Deny", "繼承": "Inherit", "儲存人員權限": "Save member access",
  "直接允許仍受部門權限上限限制;拒絕會優先於角色與委託權限。": "Direct allows remain constrained by the department ceiling; denies override role and delegated access.",
  "有效權限": "Effective permissions", "沒有有效權限": "No effective permissions", "權限鍵": "Permission key",
  "移動人員 / 調整崗位": "Move member / change position", "選擇目標崗位": "Choose target position", "確認移動": "Confirm move",
  "切換崗位會同步更新部門、崗位預設角色與職級。": "Changing position also synchronises the department, position-default role and level.",
  "掛職成功；原有全局／平台權限不變，部門業務操作仍受業務域規則與審計約束。": "Appointment saved; existing global/platform privileges are unchanged, while department business operations remain subject to domain rules and audit.",
  "平台擁有者本人於組織權限拓撲調整崗位": "Platform owner selected their own company position in the organisation topology",
  "平台擁有者或運營員身份不可由租戶端修改，請使用平台身份流程。": "Platform-owner or operator identities cannot be changed through tenant administration; use the platform identity workflow.",
  "您正在設定自己的公司崗位；此操作將由平台身份流程完成並保留審計記錄。": "You are setting your own company position; the platform identity workflow will apply it with a full audit trail.",
  "目前缺少有效的平台身份資料，請重新登入後再試。": "Valid platform identity data is unavailable. Sign in again and retry.",
  "部門人員": "Department people", "崗位人員": "Position members", "沒有下級資料": "No descendants", "沒有可用崗位": "No available positions",
  "模板管理": "Template-managed", "公司自訂": "Company custom", "權限上限 {n} 項": "{n} permission ceiling items",
  "您沒有直接編輯組織與權限的權限,仍可查看拓撲。": "You can view the topology, but cannot edit organisation or access settings directly.",
  "選擇左側節點查看部門、崗位或人員詳情。": "Select a node on the left to inspect a department, position or person.",
  "尚無權限目錄可供編輯": "No permission catalogue is available for editing",
  "導航": "Navigation", "導航可見範圍": "Navigation visibility",
  "按職能只顯示工作需要的功能;隱藏導航不會授予或撤銷底層權限。": "Show only the features needed for this job; hiding navigation neither grants nor revokes underlying permissions.",
  "導航設定預覽": "Navigation settings preview", "實際可見 {n} 項": "{n} visible items",
  "導航預覽 {n} 項": "Preview: {n} items",
  "啟用部門導航上限": "Enable department navigation ceiling", "啟用崗位導航預設": "Enable position navigation preset",
  "部門內人員的導航不會超出此範圍。": "Navigation for people in this department cannot exceed this range.",
  "人員會先繼承此崗位預設,再套用個人顯示或隱藏調整。": "People inherit this position preset before personal show or hide overrides are applied.",
  "個人顯示仍受功能權限與部門導航上限約束。": "Personal visibility remains constrained by feature permissions and the department navigation ceiling.",
  "儲存導航設定": "Save navigation settings", "尚無導航目錄可供編輯": "No navigation catalogue is available for editing",
  "來源 {s}": "Source: {s}", "行業預設": "Industry preset", "部門繼承": "Department inheritance", "崗位預設": "Position preset",
  "個人自訂": "Personal override", "手動設定": "Manual", "未設定": "Not configured",
  "功能權限": "Feature permissions", "受保護身份": "Protected identity", "全部恢復繼承": "Reset all to inherited",
  "顯示": "Show", "隱藏": "Hide", "缺少功能權限": "Missing feature permission", "超出部門導航上限": "Outside department navigation ceiling",
  "已由公司全局隱藏": "Hidden company-wide", "超出功能權限或上級部門上限": "Outside feature capability or parent-department ceiling",
  "超出操作者可管理範圍": "Outside the operator's manageable scope",
  "此身份的導航由平台保護,不可在租戶端修改。": "This identity's navigation is platform-protected and cannot be changed by the tenant.",
  "L10/L11 管理身份保留完整導航，不能由租戶組織策略降級": "L10/L11 management identities retain full navigation and cannot be reduced by tenant organisation policy.",
  "此管理身份可由獲授權的同級治理者調整導航；核心救援能力不會因此撤銷。": "An authorised peer governor may adjust this management identity's navigation; core recovery capabilities remain protected.",
  "L11 僅可由 L11 治理者管理；L10 可由其他 L10 或 L11 管理。": "L11 identities may be managed only by L11 governors; L10 identities may be managed by another L10 or an L11.",
  "目標平台身份映射不完整，已安全停用調崗；請重新載入或先修復身份映射。": "The target platform identity mapping is incomplete, so reassignment is safely disabled. Reload or repair the identity mapping first.",
  "此受保護身份目前沒有安全的組織調整路由。": "This protected identity currently has no safe organisation-management route.",
  "您正在調整另一位 L11 的公司崗位；此操作將由平台身份流程完成並保留雙重審計記錄。": "You are changing another L11's company position through the platform identity workflow with dual audit trails.",
  "沒有實際可見的導航項": "No navigation items are effectively visible", "導航來源部門": "Navigation source departments",
  "設定已儲存,但畫面重新整理失敗;請手動刷新確認最新狀態。": "Settings were saved, but the page refresh failed. Refresh manually to confirm the latest state.",
  "新增成員": "Add member",
  "問秘書": "Ask Secretary",
  "成員帳號": "Member accounts",
  "人": "", "筆": "", "個": "",
  "啟用 {a} · 停用 {b}": "{a} active · {b} disabled",
  "待審批申請": "Pending approvals",
  "讓秘書逐條審批 →": "Secretary: review all →",
  "全部處理完畢": "All clear",
  "角色": "Roles",
  "最高等級 L{l}": "Top level L{l}",
  "尚未定義角色": "No roles defined",
  "權限分享": "Delegations",
  "{n} 項核心權限不可分享": "{n} core permissions locked",
  "審計標記來源": "Audit-tagged source",
  "註冊 / 加入審批": "Registrations & joins",
  "審批通過即建帳號 · 全程留痕": "Approval creates the account · fully audited",
  "待審批": "Pending", "已通過": "Approved", "已駁回": "Rejected",
  "加入申請": "Join request", "註冊申請": "Registration",
  "期望角色": "Requested role",
  "(未指定)": "(unspecified)",
  "通過": "Approve", "駁回": "Reject",
  "載入中…": "Loading…",
  "暫無待審批申請": "No pending requests",
  "暫無已通過申請": "No approved requests",
  "暫無已駁回申請": "No rejected requests",
  "新申請會第一時間出現在這裡;也可以讓秘書代發邀請。": "New requests appear here instantly; the Secretary can also send invites.",
  "審批人 {r}": "Reviewer {r}",
  "角色 {r}": "Role {r}",
  "備註 {r}": "Note {r}",
  "成員清單": "Members",
  "{n} 個帳號 · 動作全部交秘書": "{n} accounts · all actions via Secretary",
  "{n} 位成員(花名冊視圖)· 動作全部交秘書": "{n} members (roster view) · all actions via Secretary",
  "搜索姓名 / 帳號 / 角色": "Search name / username / role",
  "全部": "All", "啟用": "Active", "停用": "Disabled",
  "成員": "Member", "帳號": "Username", "職級": "Level", "狀態": "Status", "交給秘書": "Via Secretary",
  "(無角色)": "(no role)",
  "調角色": "Change role", "重置密碼": "Reset password",
  "停用帳號": "Disable account", "啟用帳號": "Enable account", "刪除帳號": "Delete account",
  "調整角色": "Change role", "調整職級": "Set level",
  "調整部門 / 崗位": "Change department / position",
  "當前篩選下沒有成員": "No members match the filter",
  "還沒有成員數據": "No member data yet",
  "對秘書說「幫我建立帳號」即可開始。": "Tell the Secretary \"create an account\" to get started.",
  "角色 × 等級矩陣": "Role × level matrix",
  "等級越高授權越大 · 職級不提升角色權限": "Higher level, broader authority · level never elevates permissions",
  "成員數": "Members", "權限數": "Perms",
  "還沒有角色數據": "No role data yet",
  "對秘書說「幫我規劃角色體系」即可開始。": "Tell the Secretary \"design our role system\" to get started.",
  "分享記錄": "Delegation log",
  "只能分享自己持有且非核心的權限": "Only own, non-core permissions can be shared",
  "撤回": "Revoke",
  "至 {d}": "until {d}",
  "暫無有效分享": "No active delegations",
  "權限分享會列在這裡,審計日誌會標記委託來源。": "Delegations show up here; audit logs tag the delegated source.",
  "花名冊": "Roster",
  "建立時間": "Created",
  "職位": "Title",
  "直接吩咐秘書": "Tell the Secretary",
  "帳號與權限細項經秘書確認執行;模板切換需在控制台明確確認,全程留痕。": "Account and access details run through the Secretary; template switches require explicit console confirmation and are fully audited.",
  /* 秘書指令 */
  "權限與帳號現在有什麼需要處理的?有沒有待審批的申請?": "Anything to handle on access & accounts? Any approvals waiting?",
  "我要新增或批量導入成員帳號,請追問名單(姓名、帳號、部門、崗位)後按崗位預設建立": "I want to add or bulk-import member accounts. Ask for name, username, department and position, then create them with the position preset.",
  "把待審批的註冊與加入申請逐條給我,建議每條的角色分配,經我確認後執行審批": "Walk me through every pending registration and join request, suggest a role for each, and approve after my confirmation.",
  "審批通過「{u}」的加入申請(#{id}),期望角色「{r}」;請確認分配角色後執行": "Approve join request #{id} from {u}, requested role {r}; confirm the assigned role with me, then execute.",
  "駁回「{u}」的加入申請(#{id}),請追問駁回理由後執行": "Reject join request #{id} from {u}; ask me for the reason, then execute.",
  "審批通過「{u}」的註冊申請(#{id}),期望角色「{r}」;請確認分配角色後執行並建立帳號": "Approve registration #{id} from {u}, requested role {r}; confirm the role with me, then create the account.",
  "駁回「{u}」的註冊申請(#{id}),請追問駁回理由後執行": "Reject registration #{id} from {u}; ask me for the reason, then execute.",
  "調整成員「{u}」的角色(當前:{r}),請列出可選角色,經我確認後執行": "Change the role of member {u} (current: {r}); list the available roles and execute after my confirmation.",
  "調整成員「{u}」的部門與崗位;先列出目前行業模板中的部門和崗位,經我確認後用 org assign 執行": "Change the department and position of member {u}; list the current industry-template options first, then use org assign after I confirm.",
  "調整「{u}」的拓撲職級(當前 L{l}),請追問目標職級與職位標籤後執行": "Adjust the topology level of {u} (now L{l}); ask me for the target level and title, then execute.",
  "重置「{u}」的登入密碼,生成臨時密碼;重置後提醒我線下告知本人": "Reset the password of {u} and generate a temporary one; remind me to hand it over offline.",
  "停用帳號「{u}」,停用後登入立即失效;請與我確認後執行": "Disable the account {u} (sign-in is cut immediately); confirm with me before executing.",
  "啟用帳號「{u}」,請與我確認後執行": "Enable the account {u}; confirm with me before executing.",
  "刪除帳號「{u}」,此操作不可恢復;請再次與我確認後執行": "Delete the account {u} — irreversible; double-confirm with me before executing.",
  "把角色「{r}」(L{l})的權限清單和成員給我,並指出風險點": "Show me the permission list and members of role {r} (L{l}), and flag any risks.",
  "撤回權限分享:{g} 分享給 {e} 的「{p}」;請與我確認後執行": "Revoke the delegation of {p} from {g} to {e}; confirm with me before executing.",
  "機構與職位": "Institutions & positions",
  "機構架構 · 職位目錄 · 加入資格 · 職位權限 —— 可視化管理，亦可交秘書協助": "Institution structure · position catalogue · entry criteria · position access — manage visually or with the Secretary",
  "BIU 機構與職位模板": "BIU institution & position template",
  "預覽機構、職位、加入方式、角色、案件與卷宗差異，確認後再套用": "Preview institutions, positions, entry paths, roles, cases, and records before applying",
  "機構與職位結構": "Institution & position structure",
  "BIU → 機構 → 職位 → 成員；點擊節點查看與編輯，權限由機構上限向下約束": "BIU → institution → position → member; select a node to inspect or edit, with access constrained by the institution ceiling",
  "參與成員": "Participants",
  "待審核加入": "Pending entries",
  "職位角色": "Position roles",
  "授權記錄": "Access grants",
  "加入與職位申請": "Entry & position applications",
  "審核通過後建立帳號與職位歸屬 · 全程留痕": "Approval creates the account and position assignment · fully recorded",
  "職位角色 × 等級矩陣": "Position role × level matrix",
});
const { useState: _s, useEffect: _e, useRef: _r } = React;
const { Icon: I, Btn: B, Tag: T, Label: LB, Empty: EM, Kpi, Folio, Band, pad2, num } = W2;
const ask = (p) => W2.openSecretary(p);

const PERMS_BIU_COPY = Object.freeze({
  "權限": "機構與職位",
  "模板 · 組織拓撲 · 部門上限 · 人員權限 —— 可視化手動編輯,同一指令亦可交秘書執行": "機構架構 · 職位目錄 · 加入資格 · 職位權限 —— 可視化管理，亦可交秘書協助",
  "行業模板控制台": "BIU 機構與職位模板",
  "選擇預設,先預覽部門、崗位、角色、事務與檔案分類差異,確認後再套用": "預覽機構、職位、加入方式、角色、案件與卷宗差異，確認後再套用",
  "互動組織權限拓撲": "機構與職位結構",
  "公司 → 部門 → 崗位 → 人員;點擊節點查看與編輯,權限由部門上限向下約束": "BIU → 機構 → 職位 → 成員；點擊節點查看與編輯，權限由機構上限向下約束",
  "成員帳號": "參與成員", "待審批申請": "待審核加入", "角色": "職位角色",
  "權限分享": "授權記錄", "註冊 / 加入審批": "加入與職位申請",
  "審批通過即建帳號 · 全程留痕": "審核通過後建立帳號與職位歸屬 · 全程留痕",
  "成員清單": "參與成員", "角色 × 等級矩陣": "職位角色 × 等級矩陣", "分享記錄": "授權記錄",
});
const permsText = (biu, value) => t(biu ? (PERMS_BIU_COPY[value] || value) : value);

const uref = (name, username) => (name || username || "—") + (username ? " @" + username : "");
const REG_TABS = [["pending", "待審批"], ["approved", "已通過"], ["rejected", "已駁回"]];
const REG_EMPTY = { pending: "暫無待審批申請", approved: "暫無已通過申請", rejected: "暫無已駁回申請" };

/* ── 成員詳情抽屜 ── */
const MemberDrawer = ({ m, onClose }) => {
  const u = uref(m.name, m.username);
  const roleStr = m.roles.length ? m.roles.join("、") : t("(無角色)");
  const acts = [
    ["building", "調整部門 / 崗位", t("調整成員「{u}」的部門與崗位;先列出目前行業模板中的部門和崗位,經我確認後用 org assign 執行", { u })],
    ["swap", "調整角色", t("調整成員「{u}」的角色(當前:{r}),請列出可選角色,經我確認後執行", { u, r: roleStr })],
    ["layers", "調整職級", t("調整「{u}」的拓撲職級(當前 L{l}),請追問目標職級與職位標籤後執行", { u, l: m.level })],
    ["shield", "重置密碼", t("重置「{u}」的登入密碼,生成臨時密碼;重置後提醒我線下告知本人", { u })],
    m.active
      ? ["x", "停用帳號", t("停用帳號「{u}」,停用後登入立即失效;請與我確認後執行", { u })]
      : ["check", "啟用帳號", t("啟用帳號「{u}」,請與我確認後執行", { u })],
  ];
  return (
    <div className="drawer">
      <div style={{ padding: "16px 18px", borderBottom: "2px solid var(--rule)" }}>
        <div className="row spread" style={{ marginBottom: 10 }}>
          {m.active ? <T tone="ok" dot>{t("啟用")}</T> : <T tone="plain">{t("停用")}</T>}
          <button className="btn ghost sm" style={{ padding: "0 7px" }} onClick={onClose} title="Esc"><I name="x" size={13}/></button>
        </div>
        <div style={{ fontSize: 19, fontWeight: 750, letterSpacing: "-.025em", lineHeight: 1.25 }}>{m.name}</div>
        <div className="num muted" style={{ fontSize: 11.5, marginTop: 5 }}>{m.username ? "@" + m.username : t("花名冊")}</div>
      </div>
      <div style={{ padding: 18, maxHeight: "calc(100vh - 280px)", overflowY: "auto" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 18 }}>
          {[[t("角色"), roleStr], [t("職級"), "L" + (m.level || 1) + (m.title ? " · " + m.title : "")], [t("狀態"), m.active ? t("啟用") : t("停用")], [t("建立時間"), m.created || "—"]].map(([k, v]) => (
            <div key={k} className="col g4" style={{ borderTop: "1px solid var(--hair)", paddingTop: 8 }}>
              <LB dim style={{ fontSize: 8.5 }}>{k}</LB>
              <span style={{ fontSize: 13.5, fontWeight: 650, lineHeight: 1.4 }}>{v}</span>
            </div>
          ))}
        </div>
        <LB dim style={{ fontSize: 8.5, marginBottom: 8 }}>{t("直接吩咐秘書")}</LB>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          {acts.map(([icon, label, prompt]) => (
            <button key={label} className="btn" style={{ height: 40, justifyContent: "flex-start", fontSize: 12.5 }} onClick={() => ask(prompt)}>
              <I name={icon} size={14}/>{t(label)}
            </button>
          ))}
        </div>
        <button className="btn red" style={{ width: "100%", marginTop: 8, height: 38, fontSize: 12.5 }}
          onClick={() => ask(t("刪除帳號「{u}」,此操作不可恢復;請再次與我確認後執行", { u }))}>
          <I name="alert" size={13}/>{t("刪除帳號")}
        </button>
        <div className="muted" style={{ fontSize: 10.5, marginTop: 12, lineHeight: 1.6 }}>{t("帳號與權限細項經秘書確認執行;模板切換需在控制台明確確認,全程留痕。")}</div>
      </div>
    </div>
  );
};

const templateKeyOf = (item) => {
  if (typeof item === "string") return item;
  return item && (item.key || item.template_key) ? String(item.key || item.template_key) : "";
};
const templateNameOf = (item) => {
  if (typeof item === "string") return item;
  return (item && (item.name || item.label || templateKeyOf(item))) || "—";
};
const templateListOf = (catalog) => {
  const raw = catalog && catalog.templates;
  if (Array.isArray(raw)) return raw.map(item => typeof item === "string" ? { key: item, name: item } : item).filter(item => templateKeyOf(item));
  if (raw && typeof raw === "object") return Object.keys(raw).map(key => {
    const value = raw[key];
    return value && typeof value === "object" ? { key, ...value } : { key, name: value || key };
  });
  return [];
};

/* ── 行業模板控制台:選擇 → 預覽 → 明確確認 → 套用 ── */
const TemplateConsole = ({ onApplied, refreshSeq, biu = false }) => {
  const [catalog, setCatalog] = _s(null);
  const [catalogError, setCatalogError] = _s("");
  const [selectedKey, setSelectedKey] = _s("");
  const [preview, setPreview] = _s(null);
  const [previewLoading, setPreviewLoading] = _s(false);
  const [previewError, setPreviewError] = _s("");
  const [confirming, setConfirming] = _s(false);
  const [applying, setApplying] = _s(false);
  const [applyError, setApplyError] = _s("");
  const [notice, setNotice] = _s("");
  const catalogSeq = _r(0);
  const previewSeq = _r(0);

  const loadPreview = async (key) => {
    const cleanKey = String(key || "").trim();
    const seq = ++previewSeq.current;
    setPreview(null);
    setPreviewError("");
    if (!cleanKey) { setPreviewLoading(false); return; }
    setPreviewLoading(true);
    try {
      const data = await W2.json("/api/org/template-preview?template=" + encodeURIComponent(cleanKey));
      if (seq === previewSeq.current) setPreview(data && typeof data === "object" ? data : {});
    } catch (e) {
      if (seq === previewSeq.current) setPreviewError((e && e.message) || t("模板預覽暫不可用"));
    } finally {
      if (seq === previewSeq.current) setPreviewLoading(false);
    }
  };

  const loadCatalog = async (preferredKey) => {
    const seq = ++catalogSeq.current;
    setCatalog(null);
    setCatalogError("");
    setConfirming(false);
    setApplyError("");
    try {
      const data = await W2.json("/api/org/templates");
      if (seq !== catalogSeq.current) return;
      const nextCatalog = data && typeof data === "object" ? data : {};
      const list = templateListOf(nextCatalog);
      const currentKey = templateKeyOf(nextCatalog.current_template);
      const nextKey = (preferredKey && list.some(item => templateKeyOf(item) === preferredKey))
        ? preferredKey : (currentKey || (list[0] && templateKeyOf(list[0])) || "");
      setCatalog(nextCatalog);
      setSelectedKey(nextKey);
      await loadPreview(nextKey);
    } catch (e) {
      if (seq === catalogSeq.current) setCatalogError((e && e.message) || t("模板目錄暫不可用"));
    }
  };

  _e(() => { loadCatalog(); }, [refreshSeq]);

  const list = templateListOf(catalog);
  const currentKey = templateKeyOf(catalog && catalog.current_template);
  const canApply = !!(catalog && catalog.can_apply !== false);
  const currentMeta = list.find(item => templateKeyOf(item) === currentKey) || (catalog && catalog.current_template) || null;
  const selectedMeta = list.find(item => templateKeyOf(item) === selectedKey) || (preview && preview.template) || null;
  const currentName = templateNameOf(currentMeta) || currentKey || "—";
  const selectedName = templateNameOf((preview && preview.template) || selectedMeta) || selectedKey || "—";
  const summary = preview && preview.summary && typeof preview.summary === "object" ? preview.summary : {};
  const summaryCards = [
    ["部門新增", "departments_create"], ["部門同步", "departments_sync"],
    ["崗位新增", "positions_create"], ["崗位同步", "positions_sync"],
    ["角色新增", "roles_create"], ["角色重用", "roles_reuse"],
    ["部門導航同步", "nav_ceilings_sync"], ["崗位導航同步", "position_nav_defaults_sync"],
    ["事務類型新增", "case_types_create"], ["事務類型歸檔", "case_types_archive"],
    ["檔案分類新增", "record_categories_create"], ["檔案分類歸檔", "record_categories_archive"],
    ["檔案類型新增", "record_types_create"], ["檔案類型歸檔", "record_types_archive"],
  ];
  const archive = {
    positions: num(summary.positions_archive),
    departments: num(summary.departments_archive),
    cases: num(summary.case_types_archive),
    recordCategories: num(summary.record_categories_archive),
    recordTypes: num(summary.record_types_archive),
  };
  const hasArchive = archive.positions + archive.departments + archive.cases + archive.recordCategories + archive.recordTypes > 0;
  const preservedOverrides = num(summary.departments_preserve_override)
    + num(summary.departments_preserve_archived)
    + num(summary.positions_preserve_override)
    + num(summary.positions_preserve_archived);
  const retainedChildren = num(summary.departments_retain_with_children);
  const preservedNavigation = num(summary.nav_ceilings_preserve_manual)
    + num(summary.position_nav_defaults_preserve_manual);
  const modules = preview && preview.template && Array.isArray(preview.template.enabled_modules) ? preview.template.enabled_modules : [];

  const selectTemplate = (key) => {
    setSelectedKey(key);
    setConfirming(false);
    setApplyError("");
    setNotice("");
    loadPreview(key);
  };
  const applyTemplate = async () => {
    if (!selectedKey || applying || !preview || !preview.preview_token || previewError) return;
    setApplying(true);
    setApplyError("");
    setNotice("");
    try {
      const result = await W2.post("/api/org/apply-template", {
        template_key: selectedKey,
        preview_token: preview.preview_token,
        confirm: true,
      });
      setConfirming(false);
      setNotice(t("行業模板「{name}」已套用,組織與權限資料已刷新。", { name: selectedName }));
      if (onApplied) await Promise.resolve(onApplied(result));
      await loadCatalog(selectedKey);
    } catch (e) {
      setApplyError((e && e.message) || t("套用模板失敗"));
    } finally {
      setApplying(false);
    }
  };

  const aiActions = [
    ["building", "AI 調整部門", t("我要在目前的「{name}」行業模板基礎上調整公司部門設計。請先讀取現有組織結構,逐項詢問新增、改名、上級關係或停用需求,先列出變更預覽與影響,經我明確確認後再執行。", { name: currentName })],
    ["layers", "AI 調整崗位", t("我要在目前的「{name}」行業模板基礎上調整公司崗位設計。請先列出各部門現有崗位、主管關係、預設角色與職級,逐項確認變更並預覽人員影響,經我明確確認後再執行。", { name: currentName })],
    ["shield", "AI 調整角色權限", t("我要調整目前公司的角色與權限設計。請先列出角色、成員、權限和導航可見範圍,指出過度授權或缺權風險,提出最小權限方案,經我逐項確認後再執行。")],
  ];

  return (
    <Band no="T" title={permsText(biu, "行業模板控制台")}
      sub={permsText(biu, "選擇預設,先預覽部門、崗位、角色、事務與檔案分類差異,確認後再套用")}
      delay={.06}
      right={<div className="row g8 wrap">
        {currentKey && <T tone="ok" dot>{t("目前使用")}: {currentName}</T>}
        <B size="sm" icon="refresh" disabled={applying} onClick={() => loadCatalog(selectedKey)}>{t("刷新")}</B>
      </div>}>
      {catalog === null && !catalogError && <div className="muted" style={{ fontSize: 12.5, padding: "16px 4px" }}>{t("模板目錄載入中…")}</div>}
      {catalogError && (
        <EM icon="alert" title={t("模板目錄暫不可用")} sub={catalogError}
          action={<B size="sm" icon="refresh" onClick={() => loadCatalog()}>{t("重試")}</B>}/>
      )}
      {catalog && !list.length && (
        <EM icon="building" title={t("沒有可用的行業模板")}/>
      )}

      {catalog && list.length > 0 && <div style={{ borderTop: "2px solid var(--rule)", paddingTop: 18 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 360px), 1fr))", gap: 28, alignItems: "start" }}>
          <div className="col g12">
            <LB red>{t("選擇行業模板")}</LB>
            <select className="field boxed" value={selectedKey} disabled={applying}
              onChange={e => selectTemplate(e.target.value)}
              style={{ width: "100%", height: 42, padding: "0 10px", fontSize: 13.5, background: "var(--paper)" }}>
              {list.map(item => {
                const key = templateKeyOf(item);
                return <option key={key} value={key}>{templateNameOf(item)}{key === currentKey ? " · " + t("已生效") : ""}</option>;
              })}
            </select>
            {selectedMeta && <div className="col g6" style={{ padding: "12px 0", borderBottom: "1px solid var(--hair)" }}>
              <div className="row g6 wrap">
                <T tone={selectedKey === currentKey ? "ok" : "inv"} dot={selectedKey === currentKey}>{selectedKey === currentKey ? t("已生效") : selectedKey}</T>
                {selectedMeta.department_count != null && <T tone="plain">{t("部門")} {num(selectedMeta.department_count)}</T>}
                {selectedMeta.position_count != null && <T tone="plain">{t("崗位")} {num(selectedMeta.position_count)}</T>}
              </div>
              {selectedMeta.description && <span className="muted" style={{ fontSize: 12, lineHeight: 1.65 }}>{selectedMeta.description}</span>}
              {(selectedMeta.revision || selectedMeta.schema_version) && <span className="mono muted" style={{ fontSize: 10.5 }}>
                {selectedMeta.revision ? "REV " + selectedMeta.revision : ""}{selectedMeta.schema_version ? " · SCHEMA " + selectedMeta.schema_version : ""}
              </span>}
            </div>}
            <B size="sm" icon="search" disabled={previewLoading || applying} onClick={() => loadPreview(selectedKey)}>{t("預覽差異")}</B>
          </div>

          <div>
            {previewLoading && <div className="muted" style={{ fontSize: 12.5, padding: "14px 4px" }}>{t("預覽載入中…")}</div>}
            {previewError && (
              <EM icon="alert" title={t("模板預覽暫不可用")} sub={previewError}
                action={<B size="sm" icon="refresh" onClick={() => loadPreview(selectedKey)}>{t("重試")}</B>}/>
            )}
            {!previewLoading && preview && !previewError && <div className="col g14">
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(88px, 1fr))", gap: 1, background: "var(--hair)" }}>
                {summaryCards.map(([label, key]) => <div key={key} style={{ background: "var(--paper)", padding: "10px 11px" }}>
                  <LB dim style={{ fontSize: 8 }}>{t(label)}</LB>
                  <div className="num" style={{ fontSize: 20, fontWeight: 750, marginTop: 5 }}>{num(summary[key])}</div>
                </div>)}
              </div>
              {modules.length > 0 && <div className="row g4 wrap">{modules.map(module => <T key={module} tone="plain">{module}</T>)}</div>}
              {hasArchive && <div style={{ background: "var(--red-soft)", borderLeft: "3px solid var(--red)", padding: "10px 12px", color: "var(--ink-2)", fontSize: 12, lineHeight: 1.6 }}>
                {t("將歸檔 {p} 個舊崗位、{d} 個舊部門和 {c} 個舊事務類型;有成員的崗位會保留。", { p: archive.positions, d: archive.departments, c: archive.cases })}
                {(archive.recordCategories > 0 || archive.recordTypes > 0) && <div style={{ marginTop: 4 }}>{t("另將停用 {c} 個舊檔案分類和 {t} 個舊檔案類型;歷史檔案與類型版本不會刪除。", { c: archive.recordCategories, t: archive.recordTypes })}</div>}
              </div>}
              {(preservedOverrides > 0 || retainedChildren > 0) && <div style={{ background: "var(--paper-2)", borderLeft: "3px solid var(--ink)", padding: "10px 12px", color: "var(--ink-2)", fontSize: 12, lineHeight: 1.6 }}>
                {t("{o} 個公司自定義或已封存的同碼部門/崗位將保持不變;{c} 個舊部門因仍有下級部門而保留。", { o: preservedOverrides, c: retainedChildren })}
              </div>}
              {preservedNavigation > 0 && <div style={{ background: "var(--paper-2)", borderLeft: "3px solid var(--blue)", padding: "10px 12px", color: "var(--ink-2)", fontSize: 12, lineHeight: 1.6 }}>{t("{n} 項手動導航設定會保留,不會被行業模板覆蓋。", { n: preservedNavigation })}</div>}
              <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{t("合併套用只同步模板管理的架構,保留公司自訂資料,不刪除既有業務記錄。")}</div>
              {!canApply && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{t("當前帳號可以預覽,但沒有套用行業模板的權限。")}</div>}
              {!confirming ? <B kind="primary" icon="check" disabled={applying || !canApply} onClick={() => { setConfirming(true); setApplyError(""); }}>
                {selectedKey === currentKey ? t("重新同步此模板") : t("套用此模板")}
              </B> : <div style={{ border: "1px solid var(--red)", padding: 14, background: "var(--red-soft)" }}>
                <div style={{ fontWeight: 750, fontSize: 14 }}>{t("確認套用「{name}」?", { name: selectedName })}</div>
                <div style={{ fontSize: 12, lineHeight: 1.65, marginTop: 5 }}>{t("套用後會同步部門、崗位、預設角色權限、導航可見範圍、事務類型與檔案分類。")}</div>
                <div className="row g8 wrap" style={{ marginTop: 12 }}>
                  <B kind="red" icon="check" disabled={applying} onClick={applyTemplate}>{applying ? t("正在套用…") : t("確認套用")}</B>
                  <B disabled={applying} onClick={() => { setConfirming(false); setApplyError(""); }}>{t("取消")}</B>
                </div>
              </div>}
              {applyError && <div style={{ color: "var(--red)", fontSize: 12, lineHeight: 1.55 }}>{applyError}</div>}
              {notice && <div style={{ borderLeft: "3px solid var(--ink)", padding: "9px 12px", fontSize: 12.5, lineHeight: 1.55 }}>{notice}</div>}
            </div>}
          </div>
        </div>
      </div>}

      <div style={{ borderTop: "1px solid var(--hair)", marginTop: 22, paddingTop: 16 }}>
        <div className="row spread wrap g12">
          <div className="col g4" style={{ maxWidth: 620 }}>
            <LB red>{t("AI 協助調整")}</LB>
            <span className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{t("模板建立共通架構;公司特有的部門、崗位與角色權限可繼續透過 AI 精細調整。")}</span>
          </div>
          <div className="row g8 wrap">
            {aiActions.map(([icon, label, prompt]) => <B key={label} size="sm" icon={icon} onClick={() => ask(prompt)}>{t(label)}</B>)}
          </div>
        </div>
      </div>
    </Band>
  );
};

/* ── Swiss / Mermaid-like 互動組織權限拓撲 ── */
const orgFlag = (v) => v === true || v === 1 || v === "1" || v === "true";
const orgArray = (value) => {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (value && typeof value === "object") {
    const nested = value.permissions || value.keys || value.allow;
    return Array.isArray(nested) ? nested.map(String).filter(Boolean) : [];
  }
  if (typeof value !== "string" || !value.trim()) return [];
  try {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
  } catch (_) {
    return value.split(",").map(v => v.trim()).filter(Boolean);
  }
};
const permissionKey = (p) => String((p && (p.key || p.permission_key)) || p || "");
const permissionLabel = (p) => (p && (p.description || p.label)) || permissionKey(p);
const permissionGroup = (p) => (p && p.group) || t("權限");
const BIU_PERMISSION_KEYS = new Set([
  "ai.use", "audit.read", "cases.all.manage", "cases.analytics.read",
  "cases.assign", "cases.close", "cases.config.manage", "cases.create",
  "cases.process", "cases.read", "overview.read", "permissions.delegate",
  "permissions.topology.manage", "permissions.topology.read",
  "records.all.manage", "records.archive", "records.cli.manage",
  "records.config.manage", "records.create", "records.edit", "records.read",
  "settings.manage", "tasks.assign", "tasks.create", "tasks.manage",
  "tasks.read", "users.manage",
]);
const BIU_NAV_MODULE_ORDER = ["dashboard", "tasks", "cases", "perms", "logs", "settings"];
const BIU_NAV_MODULE_IDS = new Set(BIU_NAV_MODULE_ORDER);
const biuPermissionValues = (values, biu) => {
  const rows = orgArray(values);
  return biu ? rows.filter(key => BIU_PERMISSION_KEYS.has(key)) : rows;
};
const biuPermissionCatalog = (values, biu) => {
  const rows = Array.isArray(values) ? values : [];
  return biu ? rows.filter(item => BIU_PERMISSION_KEYS.has(permissionKey(item))) : rows;
};
const biuNavValues = (values, biu) => {
  const rows = orgArray(values);
  if (!biu) return rows;
  const selected = new Set(rows.filter(moduleId => BIU_NAV_MODULE_IDS.has(moduleId)));
  return BIU_NAV_MODULE_ORDER.filter(moduleId => selected.has(moduleId));
};
const biuNavCatalog = (values, biu) => {
  const rows = Array.isArray(values) ? values : [];
  if (!biu) return rows;
  const byId = new Map();
  rows.forEach(item => {
    const id = String((item && item.id) || item || "");
    if (BIU_NAV_MODULE_IDS.has(id) && !byId.has(id)) {
      byId.set(id, item && typeof item === "object" ? item : { id, label: id });
    }
  });
  return BIU_NAV_MODULE_ORDER.filter(id => byId.has(id)).map((id, order) => ({
    ...byId.get(id), id, order,
  }));
};
const BIU_ENTRY_LABELS = { direct: "直接加入", application: "申請審核", exam: "資格測評", appointment: "機構委任" };
const BIU_CATALOG_LABELS = { public: "目錄公開", locked: "目錄鎖定", hidden: "目錄隱藏" };
const BiuPositionBadges = ({ position }) => {
  const p = position || {};
  if (!p.entry_mode || !p.permission_tier) return null;
  const modeTone = p.entry_mode === "direct" ? "ok" : p.entry_mode === "exam" ? "inv" : "plain";
  return <span className="row g5 wrap"><T tone={modeTone}>{t(BIU_ENTRY_LABELS[p.entry_mode] || p.entry_mode)}</T><T tone="plain">{t("權限層級")} {p.permission_tier}</T>{p.catalog_state && <T tone="plain">{t(BIU_CATALOG_LABELS[p.catalog_state] || p.catalog_state)}</T>}</span>;
};

const OrgTopologyStyles = () => <style>{`
  .org-topology-shell{border-top:2px solid var(--rule);margin-top:18px}
  .org-topology-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:12px 0;border-bottom:1px solid var(--hair);flex-wrap:wrap}
  .org-topology-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(330px,390px);min-height:560px;border-bottom:1px solid var(--hair)}
  .org-map-pane{min-width:0;padding:14px 18px 18px 0}
  .org-map-viewport{position:relative;overflow:auto;height:650px;border:1px solid var(--hair);background-color:var(--paper);background-image:linear-gradient(var(--hair-soft) 1px,transparent 1px),linear-gradient(90deg,var(--hair-soft) 1px,transparent 1px);background-size:24px 24px}
  .org-map-canvas{position:relative;transform-origin:0 0}
  .org-map-node{position:absolute;width:196px;height:64px;border:1.5px solid var(--ink);background:var(--paper);box-shadow:4px 4px 0 rgba(0,0,0,.08);transition:box-shadow .16s,border-color .16s,opacity .16s}
  .org-map-node.root{background:var(--ink);color:var(--paper);border-color:var(--ink)}
  .org-map-node.position{background:var(--paper-2)}
  .org-map-node.person{height:58px;border-width:1px;box-shadow:2px 2px 0 rgba(0,0,0,.06)}
  .org-map-node.group{border-style:dashed}
  .org-map-node.selected{border-color:var(--red);box-shadow:5px 5px 0 var(--red-soft)}
  .org-map-node.dimmed{opacity:.22}
  .org-node-main{appearance:none;border:0;background:transparent;color:inherit;width:100%;height:100%;text-align:left;padding:9px 34px 8px 11px;cursor:pointer;display:flex;flex-direction:column;justify-content:center;min-width:0}
  .org-node-main:focus-visible,.org-node-toggle:focus-visible{outline:2px solid var(--red);outline-offset:2px}
  .org-node-kicker{font:700 8px/1.1 var(--mono,monospace);letter-spacing:.12em;text-transform:uppercase;opacity:.62;margin-bottom:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .org-node-title{font-size:12.5px;line-height:1.25;font-weight:750;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:100%}
  .org-node-meta{font:500 9.5px/1.3 var(--mono,monospace);opacity:.62;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;width:100%}
  .org-node-toggle{position:absolute;right:7px;top:7px;width:22px;height:22px;padding:0;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer;font-size:13px;line-height:18px}
  .org-inspector{border-left:2px solid var(--rule);padding:18px 0 18px 22px;max-height:702px;overflow:auto;position:relative}
  .org-inspector-head{padding-bottom:14px;border-bottom:2px solid var(--rule);margin-bottom:16px}
  .org-inspector-title{font-size:20px;font-weight:800;letter-spacing:-.035em;line-height:1.15;margin-top:7px}
  .org-inspector-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:14px 0}
  .org-inspector-stat{border-top:1px solid var(--hair);padding-top:7px;min-width:0}
  .org-action-grid{display:grid;grid-template-columns:1fr 1fr;gap:7px;margin:12px 0 18px}
  .org-form{display:flex;flex-direction:column;gap:13px}
  .org-form-grid{display:grid;grid-template-columns:1fr 1fr;gap:11px}
  .org-form label{display:flex;flex-direction:column;gap:5px;font-size:10px;font-weight:750;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
  .org-form .field{font-size:12.5px;text-transform:none;letter-spacing:normal;color:var(--ink);min-height:38px}
  .org-form textarea.field{padding:9px;min-height:78px;resize:vertical}
  .org-perm-box{border-top:2px solid var(--rule);padding-top:13px;margin-top:18px}
  .org-perm-list{max-height:270px;overflow:auto;border:1px solid var(--hair);margin-top:9px}
  .org-perm-row{display:grid;grid-template-columns:22px minmax(0,1fr);gap:7px;align-items:start;padding:8px 9px;border-bottom:1px solid var(--hair-soft);font-size:11.5px;cursor:pointer}
  .org-perm-row:last-child{border-bottom:0}.org-perm-row:hover{background:var(--paper-2)}
  .org-perm-row.blocked{background:var(--paper-2);color:var(--ink-3)}
  .org-perm-key{font:600 9px/1.35 var(--mono,monospace);color:var(--ink-3);word-break:break-all;margin-top:2px;display:block}
  .org-override-row{display:grid;grid-template-columns:minmax(0,1fr) 62px 62px;gap:5px;align-items:center;padding:8px;border-bottom:1px solid var(--hair-soft)}
  .org-override-state{height:27px;border:1px solid var(--hair);background:var(--paper);font-size:10px;font-weight:700;cursor:pointer}.org-override-state.on.allow{background:var(--ink);color:var(--paper);border-color:var(--ink)}.org-override-state.on.deny{background:var(--red);color:#fff;border-color:var(--red)}
  .org-nav-preview{display:flex;gap:5px;overflow:auto;padding:9px 0 2px;scrollbar-width:thin}
  .org-nav-preview-item{flex:0 0 auto;display:inline-flex;align-items:center;gap:6px;border:1px solid var(--hair);background:var(--paper);padding:6px 8px;font-size:10.5px;font-weight:700;white-space:nowrap}
  .org-nav-preview-item .idx{font:700 8.5px/1 var(--mono,monospace);color:var(--red)}
  .org-nav-group{border-top:1px solid var(--hair);padding-top:10px;margin-top:12px}
  .org-nav-policy-row{display:grid;grid-template-columns:minmax(0,1fr) 54px 54px 54px;gap:5px;align-items:center;padding:8px;border-bottom:1px solid var(--hair-soft)}
  .org-nav-policy-row.blocked{background:var(--paper-2)}
  .org-nav-state{height:27px;border:1px solid var(--hair);background:var(--paper);font-size:9.5px;font-weight:700;cursor:pointer;padding:0 4px}.org-nav-state.on.inherit{border-color:var(--ink);box-shadow:inset 0 -2px 0 var(--ink)}.org-nav-state.on.show{background:var(--ink);color:var(--paper);border-color:var(--ink)}.org-nav-state.on.hide{background:var(--red);color:#fff;border-color:var(--red)}
  .org-nav-state:disabled{cursor:not-allowed;opacity:.42}
  .org-person-list{display:flex;flex-direction:column;border-top:1px solid var(--hair);margin-top:8px}.org-person-link{appearance:none;border:0;border-bottom:1px solid var(--hair-soft);background:transparent;padding:9px 2px;text-align:left;cursor:pointer;display:flex;justify-content:space-between;gap:9px;font-size:12px}.org-person-link:hover{color:var(--red)}
  .org-notice{padding:9px 11px;border-left:3px solid var(--ink);font-size:11.5px;line-height:1.5;margin:10px 0}.org-notice.error{border-color:var(--red);color:var(--red);background:var(--red-soft)}
  @media(max-width:980px){.org-topology-layout{grid-template-columns:1fr}.org-inspector{border-left:0;border-top:2px solid var(--rule);padding-left:0;max-height:none}.org-map-pane{padding-right:0}.org-map-viewport{height:560px}}
  @media(max-width:620px){.org-form-grid,.org-inspector-grid,.org-action-grid{grid-template-columns:1fr}.org-topology-toolbar .field{width:100%!important}.org-topology-layout{display:block}.org-nav-policy-row{grid-template-columns:minmax(0,1fr) repeat(3,46px)}.org-nav-state{font-size:9px}}
  @media(max-width:420px){.org-nav-policy-row{grid-template-columns:repeat(3,1fr)}.org-nav-policy-row>div:first-child{grid-column:1/-1}.org-nav-state{min-width:0}}
`}</style>;

const DepartmentPermissionEditor = ({ unit, permissions, biu = false, disabled, busy, onSave }) => {
  const rawCeiling = unit && (unit.permission_ceiling || unit.permission_ceiling_keys || unit.permission_ceiling_json);
  const initial = biuPermissionValues(rawCeiling, biu);
  const initialEnabled = orgFlag(unit && unit.permission_ceiling_enabled) || !!(rawCeiling && typeof rawCeiling === "object" && orgFlag(rawCeiling.enabled));
  const [enabled, setEnabled] = _s(initialEnabled);
  const [selected, setSelected] = _s(initial);
  const [query, setQuery] = _s("");
  _e(() => { setEnabled(initialEnabled); setSelected(initial); setQuery(""); }, [unit && unit.id, biu, initial.join("|")]);
  const q = query.trim().toLowerCase();
  const rows = (permissions || []).filter(p => !q || (permissionKey(p) + " " + permissionLabel(p) + " " + permissionGroup(p)).toLowerCase().includes(q));
  const selectedSet = new Set(selected);
  const toggle = (key) => setSelected(selectedSet.has(key) ? selected.filter(v => v !== key) : selected.concat([key]));
  const visibleKeys = rows.map(permissionKey).filter(Boolean);
  return <div className="org-perm-box">
    <div className="row spread g8 wrap">
      <div className="col g4"><LB red>{t("部門權限上限")}</LB><span className="muted" style={{ fontSize: 11, lineHeight: 1.5 }}>{t("一般人員的有效權限受此上限約束；L10/L11 身份可跨部門掛職，且不因部門權限上限而降級；崗位角色仍按治理規則同步。")}</span></div>
      <T tone={enabled ? "inv" : "plain"}>{t(enabled ? "已啟用上限" : "未啟用上限")}</T>
    </div>
    <label className="row g8" style={{ marginTop: 12, fontSize: 12, fontWeight: 650 }}><input type="checkbox" checked={enabled} disabled={disabled || busy} onChange={e => setEnabled(e.target.checked)}/>{t("啟用權限上限")}</label>
    <div className="row g6 wrap" style={{ marginTop: 9 }}>
      <input className="field" value={query} onChange={e => setQuery(e.target.value)} placeholder={t("搜索權限")} style={{ height: 32, flex: 1, minWidth: 140, fontSize: 11.5 }}/>
      <button className="btn sm" type="button" disabled={disabled || busy || !enabled || !visibleKeys.length} onClick={() => setSelected(Array.from(new Set(selected.concat(visibleKeys))))}>{t("全選可見")}</button>
      <button className="btn sm" type="button" disabled={disabled || busy || !selected.length} onClick={() => setSelected([])}>{t("清除")}</button>
    </div>
    {permissions && permissions.length ? <div className="org-perm-list">{rows.map(p => { const key = permissionKey(p); return <label key={key} className="org-perm-row"><input type="checkbox" checked={selectedSet.has(key)} disabled={disabled || busy || !enabled} onChange={() => toggle(key)}/><span><span style={{ fontWeight: 650 }}>{permissionLabel(p)}</span><span className="org-perm-key">{permissionGroup(p)} · {key}</span></span></label>; })}</div> : <div className="muted" style={{ fontSize: 11.5, padding: "12px 0" }}>{t("尚無權限目錄可供編輯")}</div>}
    <button className="btn primary" type="button" style={{ width: "100%", marginTop: 10 }} disabled={disabled || busy} onClick={() => onSave({ permissions: selected, enabled })}><I name="shield" size={13}/>{busy ? t("載入中…") : t("儲存權限上限")}</button>
  </div>;
};

const UserPermissionEditor = ({ person, permissions, biu = false, disabled, busy, onSave }) => {
  const rawOverrides = person && (person.permission_overrides || person.direct_permissions);
  const overrides = rawOverrides && typeof rawOverrides === "object" ? rawOverrides : {};
  const initialAllow = biuPermissionValues((person && (person.direct_allow || person.permission_allow || person.direct_permissions_allow)) || overrides.allow, biu);
  const initialDeny = biuPermissionValues((person && (person.direct_deny || person.permission_deny || person.direct_permissions_deny)) || overrides.deny, biu);
  const [allow, setAllow] = _s(initialAllow);
  const [deny, setDeny] = _s(initialDeny);
  const [query, setQuery] = _s("");
  _e(() => { setAllow(initialAllow); setDeny(initialDeny); setQuery(""); }, [person && person.id, biu, initialAllow.join("|"), initialDeny.join("|")]);
  const allowSet = new Set(allow); const denySet = new Set(deny);
  const q = query.trim().toLowerCase();
  const rows = (permissions || []).filter(p => !q || (permissionKey(p) + " " + permissionLabel(p)).toLowerCase().includes(q));
  const setState = (key, state) => {
    setAllow(state === "allow" ? Array.from(new Set(allow.concat([key]))) : allow.filter(v => v !== key));
    setDeny(state === "deny" ? Array.from(new Set(deny.concat([key]))) : deny.filter(v => v !== key));
  };
  return <div className="org-perm-box">
    <LB red>{t("直接權限調整")}</LB><div className="muted" style={{ fontSize: 11, lineHeight: 1.55, marginTop: 5 }}>{t("直接允許仍受部門權限上限限制;拒絕會優先於角色與委託權限。")}</div>
    <input className="field" value={query} onChange={e => setQuery(e.target.value)} placeholder={t("搜索權限")} style={{ height: 32, width: "100%", fontSize: 11.5, marginTop: 10 }}/>
    {permissions && permissions.length ? <div className="org-perm-list">{rows.map(p => { const key = permissionKey(p); const state = allowSet.has(key) ? "allow" : denySet.has(key) ? "deny" : "inherit"; return <div key={key} className="org-override-row"><div style={{ minWidth: 0 }}><div style={{ fontSize: 11.5, fontWeight: 650, overflow: "hidden", textOverflow: "ellipsis" }}>{permissionLabel(p)}</div><div className="org-perm-key">{key} · {t(state === "inherit" ? "繼承" : state === "allow" ? "允許" : "拒絕")}</div></div><button type="button" className={"org-override-state allow " + (state === "allow" ? "on" : "")} aria-pressed={state === "allow"} disabled={disabled || busy} onClick={() => setState(key, state === "allow" ? "inherit" : "allow")}>{t("允許")}</button><button type="button" className={"org-override-state deny " + (state === "deny" ? "on" : "")} aria-pressed={state === "deny"} disabled={disabled || busy} onClick={() => setState(key, state === "deny" ? "inherit" : "deny")}>{t("拒絕")}</button></div>; })}</div> : <div className="muted" style={{ fontSize: 11.5, padding: "12px 0" }}>{t("尚無權限目錄可供編輯")}</div>}
    <button className="btn primary" type="button" style={{ width: "100%", marginTop: 10 }} disabled={disabled || busy} onClick={() => onSave({ allow, deny })}><I name="shield" size={13}/>{busy ? t("載入中…") : t("儲存人員權限")}</button>
  </div>;
};

const navSourceLabel = (source) => {
  const key = String(source || "").toLowerCase();
  const labels = {
    template: "行業預設", industry: "行業預設", inherited: "部門繼承",
    department: "部門繼承", position: "崗位預設", role: "崗位預設",
    manual: "手動設定", user: "個人自訂", personal: "個人自訂",
    permission: "功能權限", protected: "受保護身份",
    unset: "未設定",
  };
  return t(labels[key] || source || "未設定");
};

const NavigationVisibilityEditor = ({ scope, entity, catalog, manageableModules, biu = false, disabled, allowProtectedEdit = false, busy, onSave }) => {
  const fallback = biuNavCatalog([]
    .concat(Array.isArray(W2.NAV) ? W2.NAV : [])
    .concat((Array.isArray(W2.NAV_ADMIN) ? W2.NAV_ADMIN : []).filter(item => item && item.id === "terminal")), biu);
  const scopedCatalog = biuNavCatalog(catalog, biu);
  const sourceCatalog = scopedCatalog.length ? scopedCatalog : fallback;
  const seen = new Set();
  const navIndex = new Map(fallback.map(item => [String(item && item.id || ""), String(item && item.idx || "")]));
  const modules = sourceCatalog.map((item, index) => ({
    id: String(item && item.id || ""),
    label: String(item && (item.label || item.default_label) || item && item.id || ""),
    group: String(item && item.group || t("導航可見範圍")),
    permission: item && item.permission,
    tenantHidden: !!(item && item.tenant_hidden),
    order: item && item.order != null ? Number(item.order) : index,
  })).filter(item => { if (!item.id || seen.has(item.id)) return false; seen.add(item.id); return true; })
    .sort((a, b) => a.order - b.order);
  const personScope = scope === "person";
  const policy = entity && entity.navigation_policy && typeof entity.navigation_policy === "object" ? entity.navigation_policy : {};
  const overrides = entity && entity.nav_overrides && typeof entity.nav_overrides === "object" ? entity.nav_overrides : {};
  const configured = biuNavValues(scope === "department" ? entity && entity.nav_ceiling : entity && entity.nav_default, biu);
  const configuredEnabled = orgFlag(scope === "department" ? entity && entity.nav_ceiling_enabled : entity && entity.nav_default_enabled);
  const initialAllow = biuNavValues(overrides.allow, biu);
  const initialDeny = biuNavValues(overrides.deny, biu);
  const [enabled, setEnabled] = _s(configuredEnabled);
  const [selected, setSelected] = _s(configured);
  const [allow, setAllow] = _s(initialAllow);
  const [deny, setDeny] = _s(initialDeny);
  _e(() => {
    setEnabled(configuredEnabled); setSelected(configured);
    setAllow(initialAllow); setDeny(initialDeny);
  }, [scope, entity && entity.id, biu, configuredEnabled, configured.join("|"), initialAllow.join("|"), initialDeny.join("|")]);

  const effective = biuNavValues(personScope
    ? (Array.isArray(policy.effective_modules) ? policy.effective_modules : entity && entity.allowed_nav)
    : scope === "department" ? entity && entity.effective_nav_ceiling : entity && entity.effective_nav_default, biu);
  const permissionModulesPresent = Array.isArray(policy.permission_modules);
  const ceilingModulesPresent = Array.isArray(policy.ceiling_modules);
  const permissionSet = new Set(biuNavValues(policy.permission_modules, biu));
  const ceilingSet = new Set(biuNavValues(policy.ceiling_modules, biu));
  const selectedSet = new Set(selected); const allowSet = new Set(allow); const denySet = new Set(deny);
  const manageableModulesPresent = Array.isArray(manageableModules);
  const manageableSet = new Set(biuNavValues(manageableModules, biu));
  const editableModulesPresent = Array.isArray(entity && entity.nav_editable_modules);
  const editableSet = new Set(biuNavValues(entity && entity.nav_editable_modules, biu));
  const bypassTenantHidden = personScope && orgFlag(policy.tenant_hidden_bypassed);
  const protectedPolicy = orgFlag(policy.protected) || orgFlag(policy.is_protected) || !!policy.protected_reason || policy.protected === "platform" || policy.protected === "platform_owner";
  const locked = !!disabled || !!busy || (protectedPolicy && !allowProtectedEdit);
  const source = personScope
    ? ((initialAllow.length || initialDeny.length) ? "user" : (policy.source || "position"))
    : scope === "department" ? entity && entity.nav_ceiling_source : entity && entity.nav_default_source;
  const grouped = []; const groupMap = new Map();
  modules.forEach(module => {
    if (!groupMap.has(module.group)) { const group = { name: module.group, modules: [] }; groupMap.set(module.group, group); grouped.push(group); }
    groupMap.get(module.group).modules.push(module);
  });
  const effectiveSet = new Set(effective);
  const actorCanManage = (id) => !manageableModulesPresent || manageableSet.has(id);
  const canShow = (id) => {
    const module = modules.find(item => item.id === id);
    return actorCanManage(id) && !(module && module.tenantHidden && !bypassTenantHidden) && (!permissionModulesPresent || permissionSet.has(id)) && (!ceilingModulesPresent || ceilingSet.has(id));
  };
  const previewSet = (() => {
    if (personScope) {
      const base = new Set(Array.isArray(policy.baseline_modules) ? biuNavValues(policy.baseline_modules, biu) : effective);
      allow.forEach(id => { if (canShow(id)) base.add(id); });
      deny.forEach(id => base.delete(id));
      return base;
    }
    if (!enabled) return editableModulesPresent ? editableSet : effectiveSet;
    return new Set(selected.filter(id => !editableModulesPresent || editableSet.has(id)));
  })();
  const previewModules = modules.filter(module => previewSet.has(module.id) && (!module.tenantHidden || bypassTenantHidden));
  const blockedReason = (id) => !bypassTenantHidden && modules.some(module => module.id === id && module.tenantHidden)
    ? t("已由公司全局隱藏")
    : !actorCanManage(id)
    ? t("超出操作者可管理範圍")
    : permissionModulesPresent && !permissionSet.has(id)
    ? t("缺少功能權限")
    : ceilingModulesPresent && !ceilingSet.has(id) ? t("超出部門導航上限") : "";
  const setPersonalState = (id, state) => {
    setAllow(state === "show" ? Array.from(new Set(allow.concat([id]))) : allow.filter(value => value !== id));
    setDeny(state === "hide" ? Array.from(new Set(deny.concat([id]))) : deny.filter(value => value !== id));
  };
  const sourceUnits = Array.isArray(policy.source_units) ? policy.source_units : [];
  const save = () => onSave(personScope ? { allow, deny } : { enabled, modules: enabled ? selected : [] });
  const scopeHint = personScope
    ? t("個人顯示仍受功能權限與部門導航上限約束。")
    : scope === "department" ? t("部門內人員的導航不會超出此範圍。") : t("人員會先繼承此崗位預設,再套用個人顯示或隱藏調整。");

  return <div className="org-perm-box">
    <div className="row spread g8 wrap">
      <div className="col g4"><LB red>{t("導航可見範圍")}</LB><span className="muted" style={{ fontSize: 11, lineHeight: 1.5 }}>{t("按職能只顯示工作需要的功能;隱藏導航不會授予或撤銷底層權限。")}</span></div>
      <div className="row g5 wrap"><T tone="plain">{t("導航預覽 {n} 項", { n: previewModules.length })}</T><T tone={source === "manual" || source === "user" ? "inv" : "plain"}>{t("來源 {s}", { s: navSourceLabel(source) })}</T></div>
    </div>
    <div style={{ marginTop: 11 }}><LB dim>{t("導航設定預覽")}</LB>{previewModules.length ? <div className="org-nav-preview">{previewModules.map((module, index) => <span className="org-nav-preview-item" key={module.id} title={module.id}><span className="idx">{navIndex.get(module.id) || String(index + 1).padStart(2, "0")}</span>{t(module.label)}</span>)}</div> : <div className="muted" style={{ fontSize: 11.5, padding: "10px 0 2px" }}>{t("沒有實際可見的導航項")}</div>}</div>
    <div className="muted" style={{ fontSize: 11, lineHeight: 1.55, marginTop: 8 }}>{scopeHint}</div>
    {protectedPolicy && <div className="org-notice" role="status">{allowProtectedEdit ? t("此管理身份可由獲授權的同級治理者調整導航；核心救援能力不會因此撤銷。") : policy.protected_reason ? t(policy.protected_reason) : t("此身份的導航由平台保護,不可在租戶端修改。")}</div>}
    {!personScope && <label className="row g8" style={{ marginTop: 12, fontSize: 12, fontWeight: 650 }}><input type="checkbox" checked={enabled} disabled={locked} onChange={event => setEnabled(event.target.checked)}/>{t(scope === "department" ? "啟用部門導航上限" : "啟用崗位導航預設")}</label>}
    {sourceUnits.length > 0 && <div style={{ marginTop: 10 }}><LB dim>{t("導航來源部門")}</LB><div className="row g4 wrap" style={{ marginTop: 6 }}>{sourceUnits.map((unit, index) => <T key={(unit && typeof unit === "object" && (unit.id || unit.org_unit_id || unit.unit_code)) || String(unit) || index} tone="plain">{typeof unit === "string" ? unit : unit && (unit.unit_name || unit.name || unit.unit_code) || "—"}</T>)}</div></div>}
    {modules.length ? <div>{grouped.map(group => <div className="org-nav-group" key={group.name}><div className="row spread"><LB dim>{t(group.name)}</LB><span className="mono muted" style={{ fontSize: 9 }}>{group.modules.filter(module => previewSet.has(module.id)).length}/{group.modules.length}</span></div><div className="org-perm-list" style={{ maxHeight: "none" }}>{group.modules.map(module => {
      if (!personScope) { const reason = module.tenantHidden ? t("已由公司全局隱藏") : !actorCanManage(module.id) ? t("超出操作者可管理範圍") : editableModulesPresent && !editableSet.has(module.id) ? t("超出功能權限或上級部門上限") : ""; return <label key={module.id} className={"org-perm-row" + (reason ? " blocked" : "")} title={reason}><input type="checkbox" checked={selectedSet.has(module.id)} disabled={locked || !enabled || (!!reason && !selectedSet.has(module.id))} onChange={() => setSelected(selectedSet.has(module.id) ? selected.filter(value => value !== module.id) : selected.concat([module.id]))}/><span><span style={{ fontWeight: 650 }}>{t(module.label)}{reason ? <T tone="plain">{reason}</T> : null}</span><span className="org-perm-key">{module.id}{previewSet.has(module.id) ? " · PREVIEW" : effectiveSet.has(module.id) ? " · CURRENT" : ""}</span></span></label>; }
      const state = denySet.has(module.id) ? "hide" : allowSet.has(module.id) ? "show" : "inherit";
      const reason = blockedReason(module.id);
      return <div key={module.id} className={"org-nav-policy-row" + (reason ? " blocked" : "")}><div style={{ minWidth: 0 }}><div className="row g5 wrap"><span style={{ fontSize: 11.5, fontWeight: 650 }}>{t(module.label)}</span>{reason && <T tone="plain">{reason}</T>}</div><span className="org-perm-key">{module.id}{previewSet.has(module.id) ? " · PREVIEW" : effectiveSet.has(module.id) ? " · CURRENT" : ""}</span></div><button type="button" className={"org-nav-state inherit " + (state === "inherit" ? "on" : "")} aria-pressed={state === "inherit"} disabled={locked} onClick={() => setPersonalState(module.id, "inherit")}>{t("繼承")}</button><button type="button" className={"org-nav-state show " + (state === "show" ? "on" : "")} aria-pressed={state === "show"} disabled={locked || !canShow(module.id)} title={reason} onClick={() => setPersonalState(module.id, "show")}>{t("顯示")}</button><button type="button" className={"org-nav-state hide " + (state === "hide" ? "on" : "")} aria-pressed={state === "hide"} disabled={locked} onClick={() => setPersonalState(module.id, "hide")}>{t("隱藏")}</button></div>;
    })}</div></div>)}</div> : <div className="muted" style={{ fontSize: 11.5, padding: "12px 0" }}>{t("尚無導航目錄可供編輯")}</div>}
    {!personScope && modules.length > 0 && <div className="row g6 wrap" style={{ marginTop: 10 }}><button className="btn sm" type="button" disabled={locked || !enabled} onClick={() => setSelected(modules.filter(module => actorCanManage(module.id) && !module.tenantHidden && (!editableModulesPresent || editableSet.has(module.id))).map(module => module.id))}>{t("全選可見")}</button><button className="btn sm" type="button" disabled={locked || !enabled || !selected.length} onClick={() => setSelected([])}>{t("清除")}</button></div>}
    {personScope && modules.length > 0 && <button className="btn sm" type="button" style={{ marginTop: 10 }} disabled={locked || (!allow.length && !deny.length)} onClick={() => { setAllow([]); setDeny([]); }}>{t("全部恢復繼承")}</button>}
    <button className="btn primary" type="button" style={{ width: "100%", marginTop: 10 }} disabled={locked || !modules.length} onClick={save}><I name="layers" size={13}/>{busy ? t("載入中…") : t("儲存導航設定")}</button>
  </div>;
};

const workflowResponsibilityNodes = (position) => {
  const responsibilities = position && position.workflow_responsibilities;
  if (!responsibilities || typeof responsibilities !== "object") return [];
  const nodes = Array.isArray(responsibilities.nodes)
    ? responsibilities.nodes.filter(node => node && typeof node === "object") : [];
  if (nodes.length) return nodes;
  return (Array.isArray(responsibilities.categories) ? responsibilities.categories : [])
    .reduce((all, category) => all.concat(
      Array.isArray(category && category.nodes)
        ? category.nodes.filter(node => node && typeof node === "object") : [],
    ), []);
};

const WorkflowResponsibilityPanel = ({ position, ask: askSecretary }) => {
  const responsibilities = position && position.workflow_responsibilities;
  const nodes = workflowResponsibilityNodes(position);
  const grouped = [];
  const groupByKey = new Map();
  nodes.forEach((node) => {
    const kind = String(node.node_kind || "").trim() || t("一般節點");
    const stage = String(node.stage_key || "").trim() || t("未指定階段");
    const key = kind + "\u0000" + stage;
    let group = groupByKey.get(key);
    if (!group) {
      group = { key, kind, stage, nodes: [] };
      groupByKey.set(key, group);
      grouped.push(group);
    }
    group.nodes.push(node);
  });
  grouped.sort((a, b) => a.kind.localeCompare(b.kind) || a.stage.localeCompare(b.stage));
  const declaredCount = Number(responsibilities && responsibilities.count);
  const count = Number.isFinite(declaredCount) ? Math.max(nodes.length, declaredCount) : nodes.length;
  const name = String(position && (position.position_name || position.name) || "—");
  const code = String(position && position.position_code || "—");
  const secretaryPrompt = t(
    "我要調整崗位「{name}」（崗位代碼：{code}）的工作流節點職責。請先讀取現有 workflow 與 node binding，以採購工作流節點配置為唯一事實來源，逐項列出 workflow_key、node_key、node_kind、stage_key、目前的 department/position binding 與權限影響；先給出變更預覽，經我逐項明確確認後才修改。不得在崗位資料建立或複製第二套職責表。",
    { name, code },
  );
  return <div className="org-perm-box" data-position-workflow-responsibilities={code}>
    <div className="row spread g8 wrap">
      <div className="col g4">
        <LB red>{t("工作流節點職責")}</LB>
        <span className="muted" style={{ fontSize: 11, lineHeight: 1.55 }}>{t("按節點類型與階段顯示；責任綁定以採購工作流節點設定為唯一事實來源，本頁不另存副本。")}</span>
      </div>
      <T tone={count ? "inv" : "plain"}>{count}</T>
    </div>
    {grouped.length ? <div style={{ marginTop: 10 }}>
      {grouped.map(group => <div key={group.key} style={{ padding: "10px 0", borderTop: "1px solid var(--hair-soft)" }}>
        <div className="row g5 wrap" style={{ marginBottom: 7 }}>
          <T tone="inv">{t("節點類型")} · {group.kind}</T>
          <T tone="plain">{t("流程階段")} · {group.stage}</T>
        </div>
        <div className="col g6">{group.nodes.map((node, index) => {
          const workflowInactive = node.workflow_active != null && !orgFlag(node.workflow_active);
          const nodeInactive = node.node_active != null && !orgFlag(node.node_active);
          const workflowLabel = node.workflow_name || node.workflow_key || "—";
          const nodeLabel = node.node_name || node.node_key || "—";
          const bindingMeta = [
            node.assignee_department_code ? t("所屬部門") + " " + node.assignee_department_code : "",
            t("崗位代碼") + " " + (node.assignee_position_code || code),
            node.required_permission ? t("所需權限") + " " + node.required_permission : "",
            node.assignee_binding_source ? t("綁定來源") + " " + node.assignee_binding_source : "",
          ].filter(Boolean).join(" · ");
          return <div key={(node.workflow_key || "workflow") + ":" + (node.node_key || node.node_id || index)} style={{ padding: "8px 9px", border: "1px solid var(--hair-soft)", background: "var(--paper-2)" }}>
            <div className="row spread g8 wrap"><span style={{ minWidth: 0, fontSize: 11.5, fontWeight: 700 }}>{workflowLabel} / {nodeLabel}</span><div className="row g4 wrap">{workflowInactive && <T tone="plain">{t("工作流已停用")}</T>}{nodeInactive && <T tone="plain">{t("節點已停用")}</T>}</div></div>
            <div className="mono muted" style={{ fontSize: 9.5, lineHeight: 1.5, marginTop: 3, wordBreak: "break-word" }}>{[node.workflow_key, node.node_key].filter(Boolean).join(" / ") || "—"}</div>
            {bindingMeta && <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.5, marginTop: 4, wordBreak: "break-word" }}>{bindingMeta}</div>}
          </div>;
        })}</div>
      </div>)}
    </div> : <div className="muted" style={{ fontSize: 11.5, padding: "12px 0 4px" }}>{t("暫無已綁定的工作流節點")}</div>}
    <div className="row g6 wrap" style={{ marginTop: 10 }}>
      <a className="btn sm" href="#/procurement"><I name="layers" size={12}/>{t("前往節點配置")}</a>
      <button className="btn sm" type="button" disabled={typeof askSecretary !== "function"} onClick={() => askSecretary(secretaryPrompt)}><I name="sparkle" size={12}/>{t("交秘書配置")}</button>
    </div>
  </div>;
};

const OrgEntityForm = ({ mode, entity, seedParentId, units, memberships, roles, busy, onSubmit, onCancel, ask }) => {
  const isDepartment = mode.indexOf("department-") === 0;
  const isCreate = mode.endsWith("-create");
  const blank = isDepartment ? { name: "", code: "", type: "department", parent_id: String(seedParentId || ""), manager_user_id: "", description: "" } : { name: "", code: "", org_unit_id: String(seedParentId || ""), role_id: "", level: "1", is_manager: false, description: "" };
  const [form, setForm] = _s(blank);
  const [formError, setFormError] = _s("");
  _e(() => {
    if (isDepartment) setForm(isCreate ? blank : { name: entity.unit_name || "", code: entity.unit_code || "", type: entity.unit_type || "department", parent_id: String(entity.parent_id || seedParentId || ""), manager_user_id: String(entity.manager_user_id || ""), description: entity.description || "" });
    else setForm(isCreate ? blank : { name: entity.position_name || "", code: entity.position_code || "", org_unit_id: String(entity.org_unit_id || seedParentId || ""), role_id: String(entity.role_id || ""), level: String(entity.level || 1), is_manager: orgFlag(entity.is_manager), description: entity.description || "" });
    setFormError("");
  }, [mode, entity && entity.id, seedParentId]);
  const set = (key, value) => { setForm({ ...form, [key]: value }); setFormError(""); };
  const departmentUnits = (units || []).filter(u => {
    const id = String((u && u.id) || "").trim();
    const active = !(u && (u.active === false || u.active === 0 || u.active === "0" || String(u.active).toLowerCase() === "false"));
    const isCompany = String((u && u.unit_type) || "").toLowerCase() === "company";
    // Only a department editor must exclude its own unit. A position-create form
    // receives the selected department as `entity`, so excluding entity.id here
    // removed exactly the department that should have been preselected.
    const isSelf = isDepartment && !isCreate && entity && String(u.id) === String(entity.id);
    return !!id && active && !isCompany && !isSelf;
  });
  const departmentIds = new Set(departmentUnits.map(u => String(u.id)));
  const managerChoices = isCreate || !entity ? [] : (memberships || []).filter(m => String(m.org_unit_id) === String(entity.id));
  const submit = async (e) => {
    e.preventDefault(); let path; let body;
    const name = form.name.trim();
    if (!name) { setFormError(t(isDepartment ? "請填寫部門名稱。" : "請填寫崗位名稱。")); return; }
    if (isDepartment) {
      path = isCreate ? "/api/org/departments" : "/api/org/departments/" + entity.id;
      body = { unit_name: name, unit_type: form.type, parent_id: form.parent_id || null, description: form.description };
      if (isCreate && form.code.trim()) body.unit_code = form.code.trim();
      if (!isCreate) body.manager_user_id = form.manager_user_id || null;
    } else {
      const level = Number(form.level);
      if (!departmentIds.has(String(form.org_unit_id))) { setFormError(t("請選擇有效的所屬部門。")); return; }
      if (!Number.isInteger(level) || level < 1 || level > 10) { setFormError(t("職級必須是 1 至 10 的整數。")); return; }
      path = isCreate ? "/api/org/positions" : "/api/org/positions/" + entity.id;
      body = { position_name: name, org_unit_id: form.org_unit_id, role_id: form.role_id || null, level, is_manager: !!form.is_manager, description: form.description };
      if (isCreate && form.code.trim()) body.position_code = form.code.trim();
    }
    const ok = await onSubmit(path, body); if (ok) onCancel();
  };
  return <form className="org-form" onSubmit={submit}>
    <div className="row spread g8"><LB red>{t(isCreate ? (isDepartment ? "新增部門" : "新增崗位") : (isDepartment ? "編輯部門" : "編輯崗位"))}</LB><button className="btn ghost sm" type="button" onClick={onCancel}>{t("返回詳情")}</button></div>
    <div className="org-form-grid"><label>{t(isDepartment ? "部門名稱" : "崗位名稱")}<input className="field boxed" required maxLength="120" value={form.name} onChange={e => set("name", e.target.value)}/></label><label>{t(isDepartment ? "部門代碼" : "崗位代碼")}<input className="field boxed mono" disabled={!isCreate} maxLength="80" value={form.code} placeholder={t("自動生成")} onChange={e => set("code", e.target.value)}/></label></div>
    {isDepartment ? <><div className="org-form-grid"><label>{t("部門類型")}<select className="field boxed" value={form.type} onChange={e => set("type", e.target.value)}><option value="department">department</option><option value="team">team</option><option value="project">project</option><option value="other">other</option></select></label><label>{t("選擇上級部門")}<select className="field boxed" required value={form.parent_id} onChange={e => set("parent_id", e.target.value)}>{(units || []).filter(u => String(u.id) !== String(entity && entity.id)).map(u => <option key={u.id} value={u.id}>{String(u.unit_type) === "company" ? t("公司直屬") + " · " : ""}{u.unit_name || u.unit_code}</option>)}</select></label></div>{!isCreate && <label>{t("負責人")}<select className="field boxed" value={form.manager_user_id} onChange={e => set("manager_user_id", e.target.value)}><option value="">—</option>{managerChoices.map(m => <option key={m.user_id} value={m.user_id}>{m.display_name || m.username}</option>)}</select></label>}</> : <><div className="org-form-grid"><label>{t("所屬部門")}<select className="field boxed" required disabled={!departmentUnits.length} value={form.org_unit_id} onChange={e => set("org_unit_id", e.target.value)}><option value="">{t("請選擇所屬部門")}</option>{departmentUnits.map(u => <option key={u.id} value={u.id}>{u.unit_name || u.unit_code}</option>)}</select></label><label>{t("選擇角色")}<select className="field boxed" value={form.role_id} onChange={e => set("role_id", e.target.value)}><option value="">{t("無預設角色")}</option>{(roles || []).map(r => <option key={r.id} value={r.id}>{r.role_name} · L{r.level || 0}</option>)}</select></label></div>{!departmentUnits.length && <div className="org-notice" role="status">{t("目前沒有可用部門。請先返回並新增或啟用部門，再建立崗位。")}</div>}<div className="org-form-grid"><label>{t("職級")}<input className="field boxed" type="number" min="1" max="10" step="1" required value={form.level} onChange={e => set("level", e.target.value)}/></label><label style={{ justifyContent: "flex-end", paddingBottom: 9 }}><span className="row g8" style={{ textTransform: "none", letterSpacing: 0, color: "var(--ink)", fontSize: 12 }}><input type="checkbox" checked={form.is_manager} onChange={e => set("is_manager", e.target.checked)}/>{t("主管崗位標記")}</span></label></div></>}
    <label>{t("說明")}<textarea className="field boxed" maxLength="800" value={form.description} onChange={e => set("description", e.target.value)}/></label>
    {!isDepartment && !isCreate && <WorkflowResponsibilityPanel position={entity} ask={ask}/>}
    {formError && <div className="org-notice error" role="alert">{formError}</div>}
    <button className="btn primary" type="submit" disabled={busy || (!isDepartment && !departmentUnits.length)}><I name="check" size={13}/>{busy ? t("載入中…") : t(isCreate ? (isDepartment ? "建立部門" : "建立崗位") : "儲存變更")}</button>
  </form>;
};

const makeOrgTree = (data, topology, biu = false) => {
  const allUnits = Array.isArray(data.units) ? data.units : [];
  const navigationCatalog = biuNavCatalog(data.navigation_catalog, biu);
  const departments = allUnits.filter(u => String(u.unit_type || "") !== "company");
  const positions = Array.isArray(data.positions) ? data.positions : [];
  const memberships = Array.isArray(data.memberships) ? data.memberships : [];
  const users = topology && Array.isArray(topology.users) ? topology.users : [];
  const allowedRoleNames = new Set(
    (topology && Array.isArray(topology.roles) ? topology.roles : [])
      .map(role => String(role && role.role_name || "")).filter(Boolean),
  );
  const userById = new Map(users.map(u => [String(u.id), u]));
  const positionById = new Map(positions.map(p => [String(p.id), p]));
  const unitById = new Map(departments.map(u => [String(u.id), u]));
  const company = allUnits.find(u => String(u.unit_type || "") === "company") || { id: "company", unit_code: "ORG-ROOT", unit_name: (data.template && data.template.name) || t("公司根節點"), unit_type: "company" };
  const childUnits = new Map();
  departments.forEach(u => { const key = String(u.parent_id == null ? "" : u.parent_id); if (!childUnits.has(key)) childUnits.set(key, []); childUnits.get(key).push(u); });
  childUnits.forEach(list => list.sort((a, b) => String(a.unit_name || "").localeCompare(String(b.unit_name || ""))));
  const posByUnit = new Map();
  positions.forEach(p => { const key = String(p.org_unit_id); if (!posByUnit.has(key)) posByUnit.set(key, []); posByUnit.get(key).push(p); });
  posByUnit.forEach(list => list.sort((a, b) => Number(b.level || 0) - Number(a.level || 0) || String(a.position_name || "").localeCompare(String(b.position_name || ""))));
  const memByPos = new Map(); const looseByUnit = new Map();
  memberships.forEach(m => {
    const pid = m.position_id == null ? "" : String(m.position_id); const uid = String(m.org_unit_id == null ? "" : m.org_unit_id);
    if (pid && positionById.has(pid)) { if (!memByPos.has(pid)) memByPos.set(pid, []); memByPos.get(pid).push(m); }
    else { if (!looseByUnit.has(uid)) looseByUnit.set(uid, []); looseByUnit.get(uid).push(m); }
  });
  const personNode = (m, suffix) => {
    const user = userById.get(String(m.user_id)) || {};
    const merged = { ...m, ...user, id: user.id != null ? user.id : m.user_id };
    const rawRoles = merged.role_names || (merged.role_name ? [merged.role_name] : []);
    const roles = (Array.isArray(rawRoles) ? rawRoles : orgArray(rawRoles))
      .filter(roleName => !biu || allowedRoleNames.has(String(roleName)));
    const personNav = biuNavValues(merged.navigation_policy && merged.navigation_policy.effective_modules || merged.allowed_nav, biu);
    return { key: "person:" + String(merged.id || merged.username) + ":" + suffix, kind: "person", label: merged.display_name || merged.username || "—", code: merged.username ? "@" + merged.username : "", meta: [roles.join(" · ") || merged.position_name || "", personNav.length + " NAV"].filter(Boolean).join(" · "), entity: merged, membership: m, user, children: [] };
  };
  const positionNode = (p) => {
    const memberNodes = (memByPos.get(String(p.id)) || []).map((m, i) => personNode(m, String(m.id || p.id + "-" + i)));
    const positionNav = biuNavValues(p.effective_nav_default, biu);
    const roleName = !biu || allowedRoleNames.has(String(p.role_name || "")) ? p.role_name : "";
    const catalogueMeta = p.entry_mode && p.permission_tier ? t(BIU_ENTRY_LABELS[p.entry_mode] || p.entry_mode) + " · " + p.permission_tier : "";
    return { key: "position:" + p.id, kind: "position", label: p.position_name || p.position_code || "—", code: p.position_code || "", meta: [(roleName || t("無預設角色")) + " · L" + (p.level || 1) + " · " + positionNav.length + " NAV", catalogueMeta].filter(Boolean).join(" · "), entity: p, count: memberNodes.length, children: memberNodes };
  };
  const buildDepartment = (u, ancestors) => {
    const id = String(u.id); const seen = new Set(ancestors || []); if (seen.has(id)) return null; seen.add(id);
    const nested = (childUnits.get(id) || []).map(c => buildDepartment(c, seen)).filter(Boolean);
    const posNodes = (posByUnit.get(id) || []).map(positionNode);
    const loose = looseByUnit.get(id) || [];
    if (loose.length) posNodes.push({ key: "group:loose:" + id, kind: "group", label: t("未分配"), code: "NO POSITION", meta: t("未分配成員"), virtual: true, entity: { org_unit_id: u.id }, count: loose.length, children: loose.map((m, i) => personNode(m, "loose-" + (m.id || i))) });
    const directPeople = memberships.filter(m => String(m.org_unit_id) === id).length;
    const ceiling = biuPermissionValues(u.permission_ceiling || u.permission_ceiling_keys || u.permission_ceiling_json, biu);
    const departmentNav = biuNavValues(u.effective_nav_ceiling, biu);
    return { key: "department:" + id, kind: "department", label: u.unit_name || u.unit_code || "—", code: u.unit_code || "", meta: directPeople + " " + t("人") + " · " + ceiling.length + " PERM · " + departmentNav.length + " NAV", entity: u, count: directPeople, children: nested.concat(posNodes) };
  };
  const top = departments.filter(u => String(u.parent_id) === String(company.id) || !unitById.has(String(u.parent_id)));
  // The tenant root can legitimately own executive and system-administrator
  // positions directly.  Those positions used to be indexed in `posByUnit`
  // but never attached to a visible node, making real L10 members disappear
  // from the topology even though `/api/org/structure` returned them.
  const rootPositions = (posByUnit.get(String(company.id)) || []).map(positionNode);
  const rootChildren = rootPositions.concat(top.map(u => buildDepartment(u, new Set())).filter(Boolean));
  const assignedIds = new Set(memberships.map(m => String(m.user_id)));
  const unassigned = users.filter(u => !assignedIds.has(String(u.id)));
  if (unassigned.length) rootChildren.push({ key: "group:unassigned", kind: "group", label: t("未分配"), code: "UNASSIGNED", meta: t("未分配成員"), virtual: true, entity: {}, count: unassigned.length, children: unassigned.map((u, i) => personNode({ user_id: u.id, username: u.username, display_name: u.display_name }, "unassigned-" + i)) });
  const root = { key: "company:" + company.id, kind: "root", label: company.unit_name || t("公司根節點"), code: company.unit_code || "ORG-ROOT", meta: departments.length + " DEPT · " + positions.length + " POS", entity: company, children: rootChildren };
  return { root, allUnits, departments, positions, memberships, users, userById, company, navigationCatalog };
};

const layoutOrgTree = (root, collapsed) => {
  const nodes = []; const edges = []; let leaf = 0; let maxDepth = 0;
  const visit = (node, depth) => {
    maxDepth = Math.max(maxDepth, depth);
    const visibleChildren = collapsed.has(node.key) ? [] : (node.children || []);
    const childLayouts = visibleChildren.map(child => visit(child, depth + 1));
    const centerY = childLayouts.length ? (childLayouts[0].centerY + childLayouts[childLayouts.length - 1].centerY) / 2 : 48 + (leaf++) * 88;
    const height = node.kind === "person" ? 58 : 64;
    const item = { node, x: 22 + depth * 232, y: centerY - height / 2, width: 196, height, centerY, depth };
    nodes.push(item); childLayouts.forEach(child => edges.push({ parent: item, child })); return item;
  };
  visit(root, 0);
  return { nodes, edges, width: Math.max(620, 22 + (maxDepth + 1) * 232 + 12), height: Math.max(420, 70 + Math.max(leaf, 1) * 88) };
};

const OrgTopologyCanvas = ({ root, selectedKey, collapsed, zoom, query, onSelect, onToggle }) => {
  const layout = layoutOrgTree(root, collapsed); const q = query.trim().toLowerCase();
  return <div className="org-map-viewport" aria-label={t("互動組織權限拓撲")}><div className="org-map-canvas" style={{ width: layout.width, height: layout.height, transform: "scale(" + zoom + ")" }}>
    <svg width={layout.width} height={layout.height} viewBox={"0 0 " + layout.width + " " + layout.height} style={{ position: "absolute", inset: 0, overflow: "visible", pointerEvents: "none" }} aria-hidden="true">
      {layout.edges.map((edge, i) => { const x1 = edge.parent.x + edge.parent.width; const x2 = edge.child.x; const y1 = edge.parent.centerY; const y2 = edge.child.centerY; const mid = x1 + (x2 - x1) * .5; const hot = selectedKey === edge.parent.node.key || selectedKey === edge.child.node.key; return <path key={i} d={`M${x1} ${y1} C${mid} ${y1},${mid} ${y2},${x2} ${y2}`} fill="none" stroke={hot ? "var(--red)" : "var(--ink)"} strokeWidth={hot ? 2 : 1.25} vectorEffect="non-scaling-stroke"/>; })}
    </svg>
    {layout.nodes.map(item => { const node = item.node; const hasChildren = !!(node.children && node.children.length); const isCollapsed = collapsed.has(node.key); const corpus = (node.label + " " + node.code + " " + node.meta).toLowerCase(); const dim = q && !corpus.includes(q); return <div key={node.key} id={"org-node-" + node.key.replace(/[^a-zA-Z0-9_-]/g, "-")} className={"org-map-node " + node.kind + (node.virtual ? " group" : "") + (selectedKey === node.key ? " selected" : "") + (dim ? " dimmed" : "")} style={{ left: item.x, top: item.y }}>
      <button type="button" className="org-node-main" onClick={() => onSelect(node)} onDoubleClick={() => hasChildren && onToggle(node.key)} aria-label={(selectedKey === node.key ? t("已選擇") + ": " : "") + node.label}><span className="org-node-kicker">{node.kind === "root" ? t("公司根節點") : node.kind === "department" ? t("部門") : node.kind === "person" ? t("成員") : t("崗位")} · {node.code}</span><span className="org-node-title">{node.label}</span><span className="org-node-meta">{node.meta || "—"}</span></button>
      {hasChildren && <button type="button" className="org-node-toggle" title={t(isCollapsed ? "展開下級" : "收起下級")} aria-label={t(isCollapsed ? "展開下級" : "收起下級") + ": " + node.label} aria-expanded={!isCollapsed} onClick={() => onToggle(node.key)}>{isCollapsed ? "+" : "−"}</button>}
    </div>; })}
  </div></div>;
};

const OrgInspector = ({ node, mode, setMode, model, topology, biu = false, canManageOrganization, canManagePermissions, busy, mutate, onSelect, ask }) => {
  const units = model.allUnits; const positions = model.positions; const memberships = model.memberships;
  const navigationCatalog = biuNavCatalog(model.navigationCatalog || [], biu);
  const roles = topology && Array.isArray(topology.roles) ? topology.roles : [];
  const allowedRoleNames = new Set(roles.map(role => String(role && role.role_name || "")).filter(Boolean));
  const visibleRoleName = (roleName) => !biu || allowedRoleNames.has(String(roleName || "")) ? roleName : "";
  const permissions = biuPermissionCatalog(topology && topology.permissions, biu);
  const actorNavigationModules = topology && topology.actor && Array.isArray(topology.actor.navigation_manageable_modules)
    ? biuNavValues(topology.actor.navigation_manageable_modules, biu) : [];
  const unitById = new Map(units.map(u => [String(u.id), u]));
  const posById = new Map(positions.map(p => [String(p.id), p]));
  const formEntity = node && node.entity ? node.entity : {};
  const currentMembership = node && (node.membership || node.entity) || {};
  const currentPosition = posById.get(String(currentMembership.position_id));
  const currentUserId = node && node.entity && (node.entity.id || node.entity.user_id);
  const [targetPosition, setTargetPosition] = _s((currentPosition && currentPosition.position_code) || currentMembership.position_code || "");
  _e(() => setTargetPosition((currentPosition && currentPosition.position_code) || currentMembership.position_code || ""), [currentUserId, currentMembership.position_id]);
  const seedParent = mode === "department-create" ? (node && node.kind === "department" ? formEntity.id : model.company.id) : mode === "position-create" ? (node && node.kind === "department" ? formEntity.id : "") : "";
  const archive = async (kind, entity) => {
    const prompt = kind === "department" ? t("確認封存部門「{name}」?封存前必須先遷移其人員、崗位、下級部門及業務引用。", { name: entity.unit_name || entity.unit_code }) : t("確認封存崗位「{name}」?封存前必須先將崗位內人員移走。", { name: entity.position_name || entity.position_code });
    if (!window.confirm(prompt)) return;
    await mutate("/api/org/" + (kind === "department" ? "departments/" : "positions/") + entity.id + "/archive", {});
  };
  if (mode !== "view") return <OrgEntityForm mode={mode} entity={formEntity} seedParentId={seedParent} units={units} memberships={memberships} roles={roles} busy={busy} onSubmit={mutate} onCancel={() => setMode("view")} ask={ask}/>;
  if (!node) return <div className="muted" style={{ fontSize: 12, lineHeight: 1.6 }}>{t("選擇左側節點查看部門、崗位或人員詳情。")}</div>;
  if (node.kind === "root") return <>
    <div className="org-inspector-head"><T tone="inv">ORG ROOT</T><div className="org-inspector-title">{node.label}</div><div className="mono muted" style={{ fontSize: 10.5, marginTop: 6 }}>{node.code}</div></div>
    <div className="org-inspector-grid"><div className="org-inspector-stat"><LB dim>{t("部門")}</LB><b className="num">{model.departments.length}</b></div><div className="org-inspector-stat"><LB dim>{t("崗位")}</LB><b className="num">{positions.length}</b></div><div className="org-inspector-stat"><LB dim>{t("成員")}</LB><b className="num">{model.users.length}</b></div><div className="org-inspector-stat"><LB dim>{t("未分配成員")}</LB><b className="num">{Math.max(0, model.users.length - new Set(memberships.map(m => m.user_id)).size)}</b></div></div>
    {canManageOrganization && <div className="org-action-grid"><button className="btn" onClick={() => setMode("department-create")}><I name="plus" size={13}/>{t("新增部門")}</button></div>}
  </>;
  if (node.kind === "department") {
    const u = node.entity; const deptPositions = positions.filter(p => String(p.org_unit_id) === String(u.id)); const deptMembers = memberships.filter(m => String(m.org_unit_id) === String(u.id)); const ceiling = biuPermissionValues(u.permission_ceiling || u.permission_ceiling_keys || u.permission_ceiling_json, biu); const navCeiling = biuNavValues(u.effective_nav_ceiling, biu);
    return <>
      <div className="org-inspector-head"><div className="row g6 wrap"><T tone="inv">{t("部門")}</T><T tone="plain">{orgFlag(u.managed_by_template) ? t("模板管理") : t("公司自訂")}</T></div><div className="org-inspector-title">{u.unit_name || "—"}</div><div className="mono muted" style={{ fontSize: 10.5, marginTop: 6 }}>{u.unit_code || "—"}</div></div>
      <div className="org-inspector-grid">{[[t("部門類型"), u.unit_type || "—"], [t("上級部門"), (unitById.get(String(u.parent_id)) || {}).unit_name || t("公司直屬")], [t("負責人"), u.manager_name || "—"], [t("權限數"), ceiling.length], [t("導航"), navCeiling.length]].map(([k, v]) => <div className="org-inspector-stat" key={k}><LB dim>{k}</LB><div style={{ fontSize: 12.5, fontWeight: 700, marginTop: 4 }}>{v}</div></div>)}</div>
      {u.description && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6, marginBottom: 12 }}>{u.description}</div>}
      {canManageOrganization ? <div className="org-action-grid"><button className="btn" onClick={() => setMode("department-edit")}><I name="gear" size={13}/>{t("編輯部門")}</button><button className="btn" onClick={() => setMode("department-create")}><I name="plus" size={13}/>{t("新增下級部門")}</button><button className="btn" onClick={() => setMode("position-create")}><I name="layers" size={13}/>{t("新增崗位")}</button><button className="btn red" onClick={() => archive("department", u)}><I name="x" size={13}/>{t("封存部門")}</button></div> : !canManagePermissions && <div className="org-notice">{t("您沒有直接編輯組織與權限的權限,仍可查看拓撲。")}</div>}
      <div style={{ marginTop: 13 }}><div className="row spread"><LB red>{t("崗位")}</LB><span className="num muted">{deptPositions.length}</span></div><div className="org-person-list">{deptPositions.map(p => <button className="org-person-link" key={p.id} onClick={() => onSelect({ key: "position:" + p.id, kind: "position", label: p.position_name, entity: p, children: [] })}><span><b>{p.position_name}</b>{p.position_name_en && <span className="muted" style={{ display: "block", fontSize: 10 }}>{p.position_name_en}</span>}<span className="mono muted" style={{ display: "block", fontSize: 9.5 }}>{p.position_code}</span></span><span className="col g4" style={{ alignItems: "flex-end" }}><span className="muted">{visibleRoleName(p.role_name) || "—"} · L{p.level || 1}</span><BiuPositionBadges position={p}/></span></button>)}{!deptPositions.length && <span className="muted" style={{ padding: "10px 0", fontSize: 11.5 }}>{t("尚未建立崗位")}</span>}</div></div>
      <div style={{ marginTop: 15 }}><div className="row spread"><LB red>{t("部門人員")}</LB><span className="num muted">{deptMembers.length}</span></div><div className="org-person-list">{deptMembers.map((m, i) => <button className="org-person-link" key={(m.id || i) + ":member"} onClick={() => { const user = model.userById.get(String(m.user_id)) || {}; onSelect({ key: "person:" + m.user_id + ":inspector", kind: "person", label: m.display_name || m.username, entity: { ...m, ...user, id: user.id || m.user_id }, membership: m, user, children: [] }); }}><span><b>{m.display_name || m.username}</b><span className="mono muted" style={{ display: "block", fontSize: 9.5 }}>{m.username ? "@" + m.username : ""}</span></span><span className="muted">{m.position_name || t("未分配")}</span></button>)}</div></div>
      <DepartmentPermissionEditor unit={u} permissions={permissions} biu={biu} disabled={!canManagePermissions} busy={busy} onSave={body => mutate("/api/org/departments/" + u.id + "/permissions", body)}/>
      <NavigationVisibilityEditor scope="department" entity={u} catalog={navigationCatalog} manageableModules={actorNavigationModules} biu={biu} disabled={!canManagePermissions} busy={busy} onSave={body => mutate("/api/org/departments/" + u.id + "/navigation", body)}/>
    </>;
  }
  if (node.kind === "position" || node.kind === "group") {
    const p = node.entity || {}; const virtual = !!node.virtual || node.kind === "group";
    const members = virtual ? (node.children || []).map(child => child.membership || child.entity) : memberships.filter(m => String(m.position_id) === String(p.id));
    const dept = unitById.get(String(p.org_unit_id));
    return <>
      <div className="org-inspector-head"><div className="row g6 wrap"><T tone="plain">{t("崗位")}</T>{orgFlag(p.is_manager) && <T tone="inv">{t("主管崗位標記")}</T>}<BiuPositionBadges position={p}/></div><div className="org-inspector-title">{node.label || p.position_name || "—"}</div>{p.position_name_en && <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{p.position_name_en}</div>}<div className="mono muted" style={{ fontSize: 10.5, marginTop: 6 }}>{p.position_code || node.code || "—"}</div></div>
      <div className="org-inspector-grid">{[[t("所屬部門"), (dept && dept.unit_name) || "—"], [t("預設角色"), visibleRoleName(p.role_name) || t("無預設角色")], [t("職級"), p.level != null ? "L" + p.level : "—"], [t("人數"), members.length], [t("導航"), biuNavValues(p.effective_nav_default, biu).length]].map(([k, v]) => <div className="org-inspector-stat" key={k}><LB dim>{k}</LB><div style={{ fontSize: 12.5, fontWeight: 700, marginTop: 4 }}>{v}</div></div>)}</div>
      {p.description && <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>{p.description}</div>}
      {canManageOrganization && !virtual && <div className="org-action-grid"><button className="btn" onClick={() => setMode("position-edit")}><I name="gear" size={13}/>{t("編輯崗位")}</button><button className="btn red" onClick={() => archive("position", p)}><I name="x" size={13}/>{t("封存崗位")}</button></div>}
      {!virtual && <WorkflowResponsibilityPanel position={p} ask={ask}/>}
      <div style={{ marginTop: 15 }}><div className="row spread"><LB red>{t("崗位人員")}</LB><span className="num muted">{members.length}</span></div><div className="org-person-list">{members.map((m, i) => <button className="org-person-link" key={(m.id || m.user_id || i) + ":posmember"} onClick={() => { const user = model.userById.get(String(m.user_id || m.id)) || {}; onSelect({ key: "person:" + (m.user_id || m.id) + ":inspector", kind: "person", label: m.display_name || m.username, entity: { ...m, ...user, id: user.id || m.user_id || m.id }, membership: m, user, children: [] }); }}><span><b>{m.display_name || m.username}</b><span className="mono muted" style={{ display: "block", fontSize: 9.5 }}>{m.username ? "@" + m.username : ""}</span></span><span className="muted">{visibleRoleName(m.role_name) || "—"}</span></button>)}{!members.length && <span className="muted" style={{ padding: "10px 0", fontSize: 11.5 }}>{t("尚未分配成員")}</span>}</div></div>
      {!virtual && <NavigationVisibilityEditor scope="position" entity={p} catalog={navigationCatalog} manageableModules={actorNavigationModules} biu={biu} disabled={!canManagePermissions} busy={busy} onSave={body => mutate("/api/org/positions/" + p.id + "/navigation", body)}/>}
    </>;
  }
  const person = node.entity || {}; const membership = node.membership || person; const userId = person.id || person.user_id; const dept = unitById.get(String(membership.org_unit_id)); const pos = posById.get(String(membership.position_id));
  const allRoleNames = Array.isArray(person.role_names) ? person.role_names : (Array.isArray(person.roles) ? person.roles.map(r => r && (r.role_name || r)).filter(Boolean) : orgArray(person.role_names));
  const roleNames = allRoleNames.filter(roleName => !biu || allowedRoleNames.has(String(roleName)));
  const membershipRoleName = visibleRoleName(membership.role_name);
  const currentActor = window.W2_USER || {};
  const governanceActor = topology && topology.actor || {};
  const selectedUsername = String(person.username || membership.username || (node.user && node.user.username) || "").trim();
  const currentUsername = String(currentActor.username || "").trim();
  const selectedTenantUserId = person.id != null ? person.id : (person.user_id != null ? person.user_id : membership.user_id);
  const currentTenantUserId = currentActor.id != null ? currentActor.id : currentActor.user_id;
  const usernameIdentityMatch = !!selectedUsername && !!currentUsername && selectedUsername.toLowerCase() === currentUsername.toLowerCase();
  const idIdentityMatch = selectedTenantUserId != null && currentTenantUserId != null && String(selectedTenantUserId) === String(currentTenantUserId);
  const selectedIsCurrentActor = usernameIdentityMatch || ((!selectedUsername || !currentUsername) && idIdentityMatch);
  const selectedRoleLevel = Math.max(0, ...(Array.isArray(person.roles) ? person.roles.map(r => Number(r && r.level) || 0) : []));
  const selectedOwnerFlag = orgFlag(person.is_platform_owner) || orgFlag(membership.is_platform_owner);
  const selectedGovernanceLevel = Math.max(
    selectedOwnerFlag ? 11 : 0,
    Number(person.governance_level || membership.governance_level || 0),
    selectedRoleLevel,
    Number(person.topology_level || person.role_level || 0),
  );
  const selectedIsPlatformOwner = selectedOwnerFlag || selectedGovernanceLevel >= 11
    || allRoleNames.some(name => String(name).toLowerCase() === "平台擁有者");
  const actorGovernanceLevel = Math.max(
    Number(governanceActor.governance_level || governanceActor.level || 0),
    window.W2_IS_OWNER ? 11 : 0,
  );
  const canGovernSelected = actorGovernanceLevel >= 11
    || (actorGovernanceLevel >= 10 && selectedGovernanceLevel <= 10);
  const governanceBlocked = selectedGovernanceLevel >= 10 && !canGovernSelected;
  const platformOwnerSelf = !!window.W2_IS_OWNER && selectedIsPlatformOwner && selectedIsCurrentActor;
  const currentActorGid = currentActor.gid != null ? currentActor.gid : currentActor.global_user_id;
  const selectedGlobalUserId = person.global_user_id != null
    ? person.global_user_id
    : membership.global_user_id != null
    ? membership.global_user_id
    : selectedIsCurrentActor
    ? currentActorGid
    : null;
  const organizationManagementRoute = String(
    person.organization_management_route || membership.organization_management_route || (selectedIsPlatformOwner ? "" : "tenant"),
  ).trim().toLowerCase();
  const platformOrganizationRoute = ["platform", "platform_identity", "platform_identity_route"].includes(organizationManagementRoute)
    || organizationManagementRoute.startsWith("/api/platform/");
  const targetNeedsPlatformRoute = selectedIsPlatformOwner || platformOrganizationRoute;
  const currentTenantSlug = String((W2.tenant && W2.tenant()) || "").trim();
  const platformIdentityReady = actorGovernanceLevel >= 11 && !!selectedUsername
    && selectedGlobalUserId != null && !!currentTenantSlug && platformOrganizationRoute;
  const platformTargetBlocked = platformOrganizationRoute && actorGovernanceLevel < 11;
  const organizationRouteBlocked = governanceBlocked || platformTargetBlocked || organizationManagementRoute === "blocked"
    || (targetNeedsPlatformRoute && !platformIdentityReady);
  const personalConfigurationBlocked = governanceBlocked || platformTargetBlocked || organizationManagementRoute === "blocked";
  const assignPosition = () => {
    if (organizationRouteBlocked) return false;
    if (targetNeedsPlatformRoute) {
      if (!platformIdentityReady) return false;
      return mutate(
        "/api/platform/tenants/" + encodeURIComponent(currentTenantSlug) + "/members/" + encodeURIComponent(String(selectedGlobalUserId)) + "/organization",
        {
          username: selectedUsername,
          confirm: selectedUsername,
          reason: t(platformOwnerSelf ? "平台擁有者本人於組織權限拓撲調整崗位" : "L11 治理者於組織權限拓撲調整同級平台擁有者崗位"),
          position_code: targetPosition,
        },
      );
    }
    return mutate("/api/org/users/" + userId + "/assign", { position_code: targetPosition });
  };
  const inferredRolePermissions = Array.from(new Set(roles.filter(r => roleNames.includes(r.role_name)).reduce((acc, r) => acc.concat(biuPermissionValues(r.permissions, biu)), [])));
  const hasOwn = (obj, key) => !!obj && Object.prototype.hasOwnProperty.call(obj, key);
  const effectiveProvided = hasOwn(person, "effective_permissions") || hasOwn(person, "permissions") || hasOwn(membership, "effective_permissions");
  const effectiveSource = hasOwn(person, "effective_permissions") ? person.effective_permissions : hasOwn(person, "permissions") ? person.permissions : membership.effective_permissions;
  const effective = effectiveProvided ? biuPermissionValues(effectiveSource, biu) : inferredRolePermissions;
  const effectiveNav = biuNavValues(person.navigation_policy && person.navigation_policy.effective_modules || person.allowed_nav, biu);
  return <>
    <div className="org-inspector-head"><div className="row g6 wrap"><T tone={person.active === false || person.active === 0 ? "plain" : "ok"} dot={person.active !== false && person.active !== 0}>{t(person.active === false || person.active === 0 ? "停用" : "啟用")}</T>{orgFlag(membership.is_primary) && <T tone="plain">{t("主要歸屬")}</T>}</div><div className="org-inspector-title">{person.display_name || person.username || node.label}</div><div className="mono muted" style={{ fontSize: 10.5, marginTop: 6 }}>{person.username ? "@" + person.username : "USER #" + userId}</div></div>
    <div className="org-inspector-grid">{[[t("所屬部門"), (dept && dept.unit_name) || membership.unit_name || t("未分配")], [t("崗位"), (pos && pos.position_name) || membership.position_name || t("未分配")], [t("角色"), roleNames.join("、") || membershipRoleName || t("(無角色)")], [t("職級"), "L" + (person.topology_level || person.role_level || (pos && pos.level) || 1) + (person.topology_title ? " · " + person.topology_title : "")], [t("導航"), effectiveNav.length], [t("建立時間"), person.created_at || membership.created_at || "—"], ["USER ID", userId ? "#" + userId : "—"]].map(([k, v]) => <div className="org-inspector-stat" key={k}><LB dim>{k}</LB><div style={{ fontSize: 12.5, fontWeight: 700, marginTop: 4, wordBreak: "break-word" }}>{v}</div></div>)}</div>
    {canManageOrganization && <div className="org-perm-box" style={{ marginTop: 8 }}><LB red>{t("移動人員 / 調整崗位")}</LB><div className="muted" style={{ fontSize: 11, lineHeight: 1.55, marginTop: 5 }}>{t("切換崗位會同步更新部門、崗位預設角色與職級。")}</div>{governanceBlocked && <div className="org-notice" role="status">{t("L11 僅可由 L11 治理者管理；L10 可由其他 L10 或 L11 管理。")}</div>}{targetNeedsPlatformRoute && canGovernSelected && organizationManagementRoute !== "blocked" && !platformIdentityReady && <div className="org-notice error" role="alert">{t("目標平台身份映射不完整，已安全停用調崗；請重新載入或先修復身份映射。")}</div>}{organizationManagementRoute === "blocked" && !governanceBlocked && <div className="org-notice" role="status">{t("此受保護身份目前沒有安全的組織調整路由。")}</div>}{targetNeedsPlatformRoute && platformIdentityReady && <div className="org-notice" role="status">{t(platformOwnerSelf ? "您正在設定自己的公司崗位；此操作將由平台身份流程完成並保留審計記錄。" : "您正在調整另一位 L11 的公司崗位；此操作將由平台身份流程完成並保留雙重審計記錄。")}</div>}<select className="field boxed" value={targetPosition} disabled={busy || organizationRouteBlocked} onChange={e => setTargetPosition(e.target.value)} style={{ width: "100%", height: 38, marginTop: 10, fontSize: 12 }}><option value="">{t("選擇目標崗位")}</option>{positions.map(p => <option key={p.id} value={p.position_code}>{(unitById.get(String(p.org_unit_id)) || {}).unit_name || "—"} / {p.position_name} · {visibleRoleName(p.role_name) || "—"}</option>)}</select><button className="btn primary" type="button" style={{ width: "100%", marginTop: 8 }} disabled={busy || !targetPosition || organizationRouteBlocked || (!targetNeedsPlatformRoute && !userId)} onClick={assignPosition}><I name="swap" size={13}/>{busy ? t("載入中…") : t("確認移動")}</button></div>}
    <NavigationVisibilityEditor scope="person" entity={person} catalog={navigationCatalog} manageableModules={actorNavigationModules} biu={biu} disabled={!canManagePermissions || personalConfigurationBlocked} allowProtectedEdit={selectedGovernanceLevel >= 10 && canGovernSelected && !personalConfigurationBlocked} busy={busy} onSave={body => mutate("/api/org/users/" + userId + "/navigation", body)}/>
    <div className="org-perm-box"><div className="row spread"><LB red>{t("有效權限")}</LB><T tone="plain">{effective.length}</T></div>{effective.length ? <div className="row g4 wrap" style={{ marginTop: 9 }}>{effective.slice(0, 28).map(key => <T key={key} tone="plain">{key}</T>)}{effective.length > 28 && <T tone="inv">+{effective.length - 28}</T>}</div> : <div className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>{t("沒有有效權限")}</div>}</div>
    <UserPermissionEditor person={person} permissions={permissions} biu={biu} disabled={!canManagePermissions || personalConfigurationBlocked} busy={busy} onSave={body => mutate("/api/org/users/" + userId + "/permissions", body)}/>
  </>;
};

const OrgStructure = ({ data, topology, onChanged, biu = false, ask }) => {
  const [selectedKey, setSelectedKey] = _s(""); const [selectedOverride, setSelectedOverride] = _s(null);
  const [collapsed, setCollapsed] = _s(new Set()); const [zoom, setZoom] = _s(1); const [query, setQuery] = _s("");
  const [mode, setMode] = _s("view"); const [busy, setBusy] = _s(false); const [notice, setNotice] = _s(""); const [error, setError] = _s("");
  const ready = data && !data.__error; const model = ready ? makeOrgTree(data, topology, biu) : null; const nodeMap = new Map();
  if (model) { const walk = n => { nodeMap.set(n.key, n); (n.children || []).forEach(walk); }; walk(model.root); }
  const selectedNode = selectedOverride || (model && (nodeMap.get(selectedKey) || model.root));
  const actor = (topology && topology.actor) || {};
  const canManageOrganization = actor.can_edit_organization == null ? !!actor.can_manage : !!actor.can_edit_organization;
  const canManagePermissions = actor.can_edit_permissions == null ? !!actor.can_manage : !!actor.can_edit_permissions;
  _e(() => { if (!model) return; if (!selectedKey || !nodeMap.has(selectedKey)) { setSelectedKey(model.root.key); setSelectedOverride(null); } }, [data, topology && topology.summary && topology.summary.users]);
  _e(() => { const closeEditor = (e) => { if (e.key === "Escape") setMode("view"); }; window.addEventListener("keydown", closeEditor); return () => window.removeEventListener("keydown", closeEditor); }, []);
  const selectNode = (node) => {
    let resolved = node;
    if (node && node.kind === "person" && !nodeMap.has(node.key)) {
      const uid = String(node.entity && (node.entity.id || node.entity.user_id) || "");
      for (const candidate of nodeMap.values()) {
        if (candidate.kind === "person" && String(candidate.entity && (candidate.entity.id || candidate.entity.user_id) || "") === uid) { resolved = candidate; break; }
      }
    }
    setSelectedKey(resolved.key); setSelectedOverride(nodeMap.has(resolved.key) ? null : resolved); setMode("view"); setError(""); setNotice("");
  };
  const toggle = (key) => setCollapsed(prev => { const next = new Set(prev); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  const mutate = async (path, body) => {
    if (busy) return false; setBusy(true); setError(""); setNotice("");
    let result = null;
    try { result = await W2.post(path, body || {}); }
    catch (e) { setError((e && e.message) || t("操作失敗")); setBusy(false); return false; }
    const warningMessage = result && result.warning && result.warning.message;
    setNotice(warningMessage ? t(warningMessage) : t("操作成功,組織拓撲已刷新。"));
    try { if (onChanged) await Promise.resolve(onChanged()); }
    catch (_) { setNotice(t("設定已儲存,但畫面重新整理失敗;請手動刷新確認最新狀態。")); }
    finally { setBusy(false); }
    return true;
  };
  if (data === null) return <Band no="O" title={permsText(biu, "互動組織權限拓撲")} sub={permsText(biu, "公司 → 部門 → 崗位 → 人員;點擊節點查看與編輯,權限由部門上限向下約束")} delay={.08}><div className="muted" style={{ fontSize: 12.5, padding: "16px 4px" }}>{t("組織結構載入中…")}</div></Band>;
  if (data.__error) return <Band no="O" title={permsText(biu, "互動組織權限拓撲")} sub={permsText(biu, "公司 → 部門 → 崗位 → 人員;點擊節點查看與編輯,權限由部門上限向下約束")} delay={.08}><EM icon="building" title={t("組織結構暫不可用")} sub={t("刷新後仍無法讀取時,請確認當前帳號具有組織查看權限。")}/></Band>;
  const template = data.template && typeof data.template === "object" ? data.template : {}; const summary = data.summary && typeof data.summary === "object" ? data.summary : {}; const summaryValue = (key, fallback) => summary[key] != null ? num(summary[key]) : fallback;
  return <Band no="O" title={permsText(biu, "互動組織權限拓撲")} sub={permsText(biu, "公司 → 部門 → 崗位 → 人員;點擊節點查看與編輯,權限由部門上限向下約束")} delay={.08} right={<><T tone="plain">{template.key || "CUSTOM"}</T><B size="sm" icon="sparkle" onClick={() => ask(t("檢查目前行業模板生成的部門、崗位與成員歸屬,列出未分配人員、缺少負責人的部門與權限風險;先給我建議,不要直接修改"))}>{t("交秘書檢查")}</B></>}>
    <OrgTopologyStyles/>
    {template.key === "biu_legal_ethics_case_lab" && <div className="org-notice" role="note" style={{ marginTop: 14 }}><div className="row g6 wrap"><T tone="inv">{t("BIU 內部學術")}</T><span>{t("BIU 職位僅用於內部法律與倫理學術工作；不代表現實司法身分、執業資格或公共權力。")}</span></div></div>}
    <div className="kpi-band" style={{ borderTop: "1px solid var(--hair)" }}><Kpi label={t("部門")} value={summaryValue("departments", model.departments.length)} delay={0}/><Kpi label={t("崗位")} value={summaryValue("positions", model.positions.length)} delay={.03}/><Kpi label={t("已分配成員")} value={summaryValue("assigned_users", new Set(model.memberships.map(m => m.user_id)).size)} delay={.06}/><Kpi label={t("未分配成員")} value={summaryValue("unassigned_users", Math.max(0, model.users.length - new Set(model.memberships.map(m => m.user_id)).size))} red={summaryValue("unassigned_users", 0) > 0} delay={.09}/></div>
    <div className="org-topology-shell"><div className="org-topology-toolbar"><div className="row g8 wrap"><LB red>{t("拓撲圖")}</LB><T tone="plain">{t("行業模板 {name} · 版本 {version}", { name: template.name || template.key || "—", version: template.version || "—" })}</T></div><div className="row g6 wrap"><input className="field" value={query} onChange={e => setQuery(e.target.value)} placeholder={t("搜索拓撲節點")} aria-label={t("搜索拓撲節點")} style={{ width: 190, height: 32, fontSize: 11.5 }}/><button className="btn sm" aria-label={t("縮小")} title={t("縮小")} disabled={zoom <= .65} onClick={() => setZoom(Math.max(.65, +(zoom - .1).toFixed(2)))}>−</button><span className="mono muted" style={{ width: 38, textAlign: "center", fontSize: 10 }}>{Math.round(zoom * 100)}%</span><button className="btn sm" aria-label={t("放大")} title={t("放大")} disabled={zoom >= 1.35} onClick={() => setZoom(Math.min(1.35, +(zoom + .1).toFixed(2)))}>+</button><button className="btn sm" title={t("重設視圖")} onClick={() => { setZoom(1); setCollapsed(new Set()); setQuery(""); }}><I name="refresh" size={12}/>{t("重設視圖")}</button>{canManageOrganization && <button className="btn primary sm" onClick={() => { setSelectedKey(model.root.key); setSelectedOverride(null); setMode("department-create"); }}><I name="plus" size={12}/>{t("新增部門")}</button>}</div></div>
      <div className="org-topology-layout"><div className="org-map-pane"><OrgTopologyCanvas root={model.root} selectedKey={selectedKey} collapsed={collapsed} zoom={zoom} query={query} onSelect={selectNode} onToggle={toggle}/><div className="muted" style={{ fontSize: 10.5, lineHeight: 1.5, marginTop: 8 }}>{t("單擊節點查看詳情;雙擊或使用箭頭展開 / 收起下級。")}</div></div><aside className="org-inspector" aria-label={t("詳情與編輯")}>{error && <div className="org-notice error" role="alert">{error}</div>}{notice && <div className="org-notice" role="status">{notice}</div>}<OrgInspector node={selectedNode} mode={mode} setMode={setMode} model={model} topology={topology || {}} biu={biu} canManageOrganization={canManageOrganization} canManagePermissions={canManagePermissions} busy={busy} mutate={mutate} onSelect={selectNode} ask={ask}/></aside></div>
    </div>
  </Band>;
};

const Page = ({ boot, reload, templateKey = "" }) => {
  const biu = !!(W2.isBiuTemplate && W2.isBiuTemplate(templateKey));
  const [usersData, setUsersData] = _s(null);   // /api/users → {users, roles}
  const [members, setMembers] = _s(null);       // /api/memberships/pending → {requests, pending_count}
  const [topo, setTopo] = _s(null);             // /api/permissions/topology
  const [org, setOrg] = _s(null);               // /api/org/structure → template/units/positions/memberships/summary
  const [regStatus, setRegStatus] = _s("pending");
  const [regs, setRegs] = _s(null);             // /api/auth/registrations?status=…
  const [q, setQ] = _s("");
  const [scope, setScope] = _s("all");
  const [sel, setSel] = _s(null);
  const [templateRefreshSeq, setTemplateRefreshSeq] = _s(0);

  const safe = (d) => (d && typeof d === "object" && !Array.isArray(d)) ? d : {};
  const loadBase = () => {
    setOrg(null);
    W2.json("/api/users").then(d => setUsersData(safe(d))).catch(() => setUsersData({}));
    W2.json("/api/memberships/pending").then(d => setMembers(safe(d))).catch(() => setMembers({}));
    W2.json("/api/permissions/topology").then(d => setTopo(safe(d))).catch(() => setTopo({}));
    W2.json("/api/org/structure").then(d => setOrg(safe(d))).catch(() => setOrg({ __error: true }));
  };
  const loadRegs = (status) => {
    setRegs(null);
    W2.json("/api/auth/registrations?status=" + encodeURIComponent(status)).then(d => setRegs(safe(d))).catch(() => setRegs({}));
  };
  _e(() => { loadBase(); loadRegs("pending"); }, []);
  _e(() => {
    const refreshAfterSecretary = () => {
      loadBase();
      loadRegs(regStatus);
      if (reload) reload();
    };
    window.addEventListener("w2-agent-complete", refreshAfterSecretary);
    return () => window.removeEventListener("w2-agent-complete", refreshAfterSecretary);
  }, [regStatus, reload]);
  _e(() => {
    const h = (e) => { if (e.key === "Escape") setSel(null); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, []);

  /* ── 成員行規整:/api/users 優先,退回 boot.PEOPLE 花名冊 ── */
  const topoRoles = (topo && Array.isArray(topo.roles)) ? topo.roles : [];
  const biuRoleNames = new Set(
    topoRoles.map(role => String(role && (role.role_name || role.name) || "")).filter(Boolean),
  );
  const visibleMemberRoles = (roleNames) => {
    const names = Array.isArray(roleNames) ? roleNames.filter(Boolean) : [];
    return biu ? names.filter(roleName => biuRoleNames.has(String(roleName))) : names;
  };
  const apiUsers = (usersData && Array.isArray(usersData.users)) ? usersData.users : [];
  const bootPeople = Array.isArray(boot.PEOPLE) ? boot.PEOPLE : [];
  const managed = apiUsers.length > 0;
  const rowsAll = (managed
    ? apiUsers.map((u) => ({
        key: "u" + (u.id != null ? u.id : u.username),
        name: u.display_name || u.username || "—",
        username: u.username || "",
        roles: visibleMemberRoles(Array.isArray(u.roles) ? u.roles.map(r => r && r.role_name).filter(Boolean)
          : (Array.isArray(u.role_names) ? u.role_names : [])),
        level: Math.max(1, Math.min(10, num(u.topology_level) || num(u.role_level) || 1)),
        title: u.topology_title || "",
        active: !(u.active === 0 || u.active === false),
        created: u.created_at || "",
      }))
    : bootPeople.map((p, i) => ({
        key: "p" + (p.id != null ? p.id : i),
        name: p.name || "—",
        username: "",
        roles: visibleMemberRoles((p.role && p.role !== "—") ? [p.role] : []),
        level: Math.max(1, Math.min(10, num(p.level) || 1)),
        title: (p.dept && p.dept !== "—") ? p.dept : "",
        active: p.online !== undefined ? !!p.online : true,
        created: "",
      }))
  ).sort((a, b) => (b.level - a.level) || String(a.name).localeCompare(String(b.name), "zh"));

  let rows = rowsAll;
  if (scope === "on") rows = rows.filter(r => r.active);
  if (scope === "off") rows = rows.filter(r => !r.active);
  if (q) { const k = q.toLowerCase(); rows = rows.filter(r => (r.name + " " + r.username + " " + r.roles.join(" ") + " " + r.title).toLowerCase().includes(k)); }

  /* ── 角色規整:topology → /api/users.roles → boot.ROLES ── */
  const apiRoles = (usersData && Array.isArray(usersData.roles)) ? usersData.roles : [];
  const bootRoles = Array.isArray(boot.ROLES) ? boot.ROLES : [];
  const rolesRaw = biu ? topoRoles : (topoRoles.length ? topoRoles : (apiRoles.length ? apiRoles : bootRoles));
  const roles = rolesRaw.map((r) => {
    const name = (r && (r.role_name || r.name)) || "—";
    const fromRows = rowsAll.filter(m => m.roles.indexOf(name) >= 0).length;
    return {
      name,
      level: Math.max(1, Math.min(10, num(r && r.level) || 1)),
      perms: biu
        ? biuPermissionValues((r && (r.permissions || r.perms)) || [], true).length
        : num(r && r.permission_count) || (Array.isArray(r && r.permissions) ? r.permissions.length : (Array.isArray(r && r.perms) ? r.perms.length : 0)),
      members: num(r && r.user_count) || fromRows,
    };
  }).sort((a, b) => (b.level - a.level) || String(a.name).localeCompare(String(b.name), "zh"));
  const topLevel = roles.length ? roles[0].level : 0;
  const LMAX = Math.min(10, Math.max(5, topLevel));
  const levels = []; for (let l = 1; l <= LMAX; l++) levels.push(l);
  const gridCols = `minmax(120px, 1.3fr) repeat(${LMAX}, minmax(22px, 1fr)) 56px 56px`;

  /* ── 審批與分享 ── */
  const memList = (members && Array.isArray(members.requests)) ? members.requests : [];
  const regList = (regs && Array.isArray(regs.requests)) ? regs.requests : [];
  const pendingTotal = num(members ? members.pending_count : 0) + num(regs ? regs.pending_count : 0);
  const approvalUnavailable = !!((members && members.available === false) || (regs && regs.available === false));
  const delsRaw = (topo && Array.isArray(topo.delegations)) ? topo.delegations : [];
  const dels = biu ? delsRaw.filter(row => BIU_PERMISSION_KEYS.has(String(row && row.permission_key || ""))) : delsRaw;
  const delCount = biu ? dels.length : ((topo && topo.summary && topo.summary.delegations != null) ? num(topo.summary.delegations) : dels.length);
  const protectedCount = biuPermissionValues(topo && topo.protected_permissions, biu).length;
  const onCount = rowsAll.filter(r => r.active).length;
  const regLoading = regs === null;

  /* ── 審批行 ── */
  const pendRow = (r, i, kind) => {
    const id = r.id != null ? r.id : "—";
    const u = uref(r.display_name, r.username);
    const requestedRole = r.requested_role_name || "";
    const role = (biu ? visibleMemberRoles([requestedRole])[0] : requestedRole) || t("(未指定)");
    const departmentName = r.requested_org_unit_name || r.department || "";
    const positionName = r.requested_position_name || "";
    const assignment = [departmentName, positionName].filter(Boolean).join(" / ");
    const meta = [assignment, r.contact, r.reason].filter(v => v && v !== "—").join(" · ");
    const orgHint = assignment ? t(",期望部門 / 崗位「{o}」", { o: assignment }) : "";
    const approve = kind === "mem"
      ? t("審批通過「{u}」的加入申請(#{id}),期望角色「{r}」{o};請核對後只使用 membership_approve 執行完整審批,不得用 user_add 或 organization_user_assign 代替", { u, id, r: role, o: orgHint })
      : t("審批通過「{u}」的註冊申請(#{id}),期望角色「{r}」{o};請按崗位預設確認後執行並建立帳號", { u, id, r: role, o: orgHint });
    const reject = kind === "mem"
      ? t("駁回「{u}」的加入申請(#{id}),請追問理由後只使用 membership_reject 執行", { u, id })
      : t("駁回「{u}」的註冊申請(#{id}),請追問駁回理由後執行", { u, id });
    return (
      <div key={kind + id + ":" + i} className="ledger-row">
        <span className="lr-idx">{pad2(i + 1)}</span>
        <div className="col g4" style={{ flex: 1.6, minWidth: 0 }}>
          <span className="row g8 wrap" style={{ fontWeight: 650, fontSize: 13.5 }}>
            {r.display_name || r.username || "—"}
            {r.username && <span className="num muted" style={{ fontSize: 11, fontWeight: 400 }}>@{r.username}</span>}
            <T tone={kind === "mem" ? "inv" : "plain"}>{t(kind === "mem" ? "加入申請" : "註冊申請")}</T>
          </span>
          <span className="muted" style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={meta}>
            {meta || "—"}{r.created_at ? " · " + r.created_at : ""}
          </span>
        </div>
        <div className="col g4" style={{ width: 180, flexShrink: 0 }}>
          <LB dim style={{ fontSize: 8 }}>{t("期望崗位 / 角色")}</LB>
          <span style={{ fontSize: 12.5, fontWeight: 600 }}>{positionName || "—"}</span>
          <span className="muted" style={{ fontSize: 11.5 }}>{role}</span>
        </div>
        <div className="row g6">
          <B size="sm" icon="check" onClick={() => ask(approve)}>{t("通過")}</B>
          <B size="sm" kind="red" onClick={() => ask(reject)}>{t("駁回")}</B>
        </div>
      </div>
    );
  };
  const doneRow = (r, i) => {
    const tone = r.status === "approved" ? "ok" : "plain";
    const meta = [
      r.reviewer_name ? t("審批人 {r}", { r: r.reviewer_name }) : "",
      r.assigned_role_name ? t("角色 {r}", { r: r.assigned_role_name }) : "",
      r.review_note ? t("備註 {r}", { r: r.review_note }) : "",
      r.reviewed_at || "",
    ].filter(Boolean).join(" · ");
    return (
      <div key={"d" + (r.id != null ? r.id : i)} className="ledger-row">
        <span className="lr-idx">{pad2(i + 1)}</span>
        <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
          <span className="row g8" style={{ fontWeight: 650, fontSize: 13.5 }}>
            {r.display_name || r.username || "—"}
            {r.username && <span className="num muted" style={{ fontSize: 11, fontWeight: 400 }}>@{r.username}</span>}
          </span>
          <span className="muted" style={{ fontSize: 11.5, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={meta}>{meta || "—"}</span>
        </div>
        <T tone={tone} dot={r.status === "approved"}>{t(r.status === "approved" ? "已通過" : "已駁回")}</T>
      </div>
    );
  };

  return (
    <>
      <Folio no="14" en="ACCESS" title={permsText(biu, "權限")}
        sub={permsText(biu, "模板 · 組織拓撲 · 部門上限 · 人員權限 —— 可視化手動編輯,同一指令亦可交秘書執行")}
        right={<>
          <B icon="refresh" onClick={() => { loadBase(); loadRegs(regStatus); setTemplateRefreshSeq(v => v + 1); reload && reload(); }}>{t("刷新")}</B>
          <B icon="plus" onClick={() => ask(t("我要新增或批量導入成員帳號,請追問名單(姓名、帳號、部門、崗位)後按崗位預設建立"))}>{t("新增成員")}</B>
          <B kind="primary" icon="sparkle" onClick={() => ask(t("權限與帳號現在有什麼需要處理的?有沒有待審批的申請?"))}>{t("問秘書")}</B>
        </>}/>

      <div className="kpi-band">
        <Kpi label={permsText(biu, "成員帳號")} value={rowsAll.length} unit={t("人")} delay={0}
          foot={<><span className="muted" style={{ fontSize: 11.5 }}>{t("啟用 {a} · 停用 {b}", { a: onCount, b: rowsAll.length - onCount })}</span><T tone="plain">{managed ? "MANAGED" : "ROSTER"}</T></>}/>
        <Kpi label={permsText(biu, "待審批申請")} value={pendingTotal} unit={t("筆")} red={pendingTotal > 0} delay={.05}
          foot={approvalUnavailable
            ? <T tone="plain">{t("審批流程待遷移")}</T>
            : pendingTotal
            ? <button className="tag redinv" style={{ cursor: "pointer" }} onClick={() => ask(t("把待審批的註冊與加入申請逐條給我,建議每條的角色分配,經我確認後執行審批"))}>{t("讓秘書逐條審批 →")}</button>
            : <T tone="ok" dot>{t("全部處理完畢")}</T>}/>
        <Kpi label={permsText(biu, "角色")} value={roles.length} unit={t("個")} delay={.1}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{roles.length ? t("最高等級 L{l}", { l: topLevel }) : t("尚未定義角色")}</span>}/>
        <Kpi label={permsText(biu, "權限分享")} value={delCount} unit={t("筆")} delay={.15}
          foot={<span className="muted" style={{ fontSize: 11.5 }}>{protectedCount ? t("{n} 項核心權限不可分享", { n: protectedCount }) : t("審計標記來源")}</span>}/>
      </div>

      {!biu && <TemplateConsole refreshSeq={templateRefreshSeq} onApplied={() => { loadBase(); reload && reload(); }} biu={false}/>}

      <OrgStructure data={org} topology={topo} onChanged={() => { loadBase(); return reload ? Promise.resolve(reload()) : undefined; }} biu={biu} ask={ask}/>

      {/* A · 註冊 / 加入審批 */}
      <Band no="A" title={permsText(biu, "註冊 / 加入審批")} sub={permsText(biu, "審批通過即建帳號 · 全程留痕")} delay={.1}
        right={<div className="seg">
          {REG_TABS.map(([id, label]) => (
            <button key={id} className={regStatus === id ? "on" : ""} onClick={() => { setRegStatus(id); loadRegs(id); }}>{t(label)}</button>
          ))}
        </div>}>
        {regLoading && <div className="muted" style={{ fontSize: 12.5, padding: "14px 4px" }}>{t("載入中…")}</div>}
        {!regLoading && approvalUnavailable && <div className="org-notice" role="status">{t("註冊與加入審批工作流尚未移植到新資料庫；此處不會把「沒有資料」誤顯示為「全部處理完畢」。目前可由系統管理員直接建立或調整既有帳號。")}</div>}
        {!regLoading && !approvalUnavailable && regStatus === "pending" && (memList.length || regList.length ? (
          <div style={{ borderTop: "2px solid var(--rule)" }}>
            {memList.map((m, i) => pendRow(m, i, "mem"))}
            {regList.map((r, i) => pendRow(r, memList.length + i, "reg"))}
          </div>
        ) : <EM icon="clipboard" title={t(REG_EMPTY.pending)} sub={t("新申請會第一時間出現在這裡;也可以讓秘書代發邀請。")}
              action={<B size="sm" icon="sparkle" onClick={() => ask(t("我要新增或批量導入成員帳號,請追問名單(姓名、帳號、部門、崗位)後按崗位預設建立"))}>{t("新增成員")}</B>}/>)}
        {!regLoading && !approvalUnavailable && regStatus !== "pending" && (regList.length ? (
          <div style={{ borderTop: "2px solid var(--rule)" }}>{regList.map(doneRow)}</div>
        ) : <EM icon="doc" title={t(REG_EMPTY[regStatus] || REG_EMPTY.pending)}/>)}
      </Band>

      {/* B · 成員清單 + 抽屜 */}
      <Band no="B" title={permsText(biu, "成員清單")}
        sub={managed ? t("{n} 個帳號 · 動作全部交秘書", { n: rowsAll.length }) : t("{n} 位成員(花名冊視圖)· 動作全部交秘書", { n: rowsAll.length })}
        delay={.15}
        right={<div className="row g12 wrap">
          <div style={{ position: "relative", width: 220 }}>
            <I name="search" size={14} color="var(--ink-4)" style={{ position: "absolute", left: 0, top: "50%", transform: "translateY(-50%)" }}/>
            <input className="field" style={{ paddingLeft: 22, height: 32, fontSize: 12.5 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t("搜索姓名 / 帳號 / 角色")}/>
          </div>
          <div className="seg">
            {[["all", "全部"], ["on", "啟用"], ["off", "停用"]].map(([id, label]) => (
              <button key={id} className={scope === id ? "on" : ""} onClick={() => setScope(id)}>{t(label)}</button>
            ))}
          </div>
        </div>}>
        <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ overflowX: "auto" }}>
              <table className="tbl2">
                <thead><tr>
                  <th style={{ width: 34 }}>#</th><th>{t("成員")}</th><th>{t("帳號")}</th><th>{t("角色")}</th><th>{t("職級")}</th><th>{t("狀態")}</th><th style={{ width: 118 }}>{t("交給秘書")}</th>
                </tr></thead>
                <tbody>
                  {rows.map((m, i) => {
                    const u = uref(m.name, m.username);
                    return (
                      <tr key={m.key} className={sel && sel.key === m.key ? "on" : ""} onClick={() => setSel(m)} style={{ cursor: "pointer" }}>
                        <td className="num muted" style={{ fontSize: 11 }}>{pad2(i + 1)}</td>
                        <td>
                          <div className="col g2">
                            <span style={{ fontWeight: 650 }}>{m.name}</span>
                            {m.title && <span className="muted" style={{ fontSize: 11 }}>{m.title}</span>}
                          </div>
                        </td>
                        <td className="num muted">{m.username ? "@" + m.username : "—"}</td>
                        <td>
                          <div className="row g6 wrap">
                            {m.roles.length ? m.roles.map(r => <T key={r} tone="plain">{r}</T>) : <span className="muted" style={{ fontSize: 12 }}>{t("(無角色)")}</span>}
                          </div>
                        </td>
                        <td><span className="num" style={{ fontWeight: 700 }}>L{m.level}</span></td>
                        <td>{m.active ? <T tone="ok" dot>{t("啟用")}</T> : <T tone="plain">{t("停用")}</T>}</td>
                        <td onClick={e => e.stopPropagation()}>
                          <div className="row g4">
                            <button className="btn sm" title={t("調角色")} style={{ padding: "0 8px" }}
                              onClick={() => ask(t("調整成員「{u}」的角色(當前:{r}),請列出可選角色,經我確認後執行", { u, r: m.roles.join("、") || t("(無角色)") }))}><I name="swap" size={12}/></button>
                            <button className="btn sm" title={t("重置密碼")} style={{ padding: "0 8px" }}
                              onClick={() => ask(t("重置「{u}」的登入密碼,生成臨時密碼;重置後提醒我線下告知本人", { u }))}><I name="shield" size={12}/></button>
                            <button className="btn sm" title={m.active ? t("停用帳號") : t("啟用帳號")} style={{ padding: "0 8px" }}
                              onClick={() => ask(m.active
                                ? t("停用帳號「{u}」,停用後登入立即失效;請與我確認後執行", { u })
                                : t("啟用帳號「{u}」,請與我確認後執行", { u }))}><I name={m.active ? "x" : "check"} size={12}/></button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {!rows.length && (rowsAll.length
              ? <EM icon="search" title={t("當前篩選下沒有成員")}/>
              : <EM icon="user" title={t("還沒有成員數據")} sub={t("對秘書說「幫我建立帳號」即可開始。")}
                  action={<B size="sm" icon="sparkle" onClick={() => ask(t("我要新增或批量導入成員帳號,請追問名單(姓名、帳號、部門、崗位)後按崗位預設建立"))}>{t("新增成員")}</B>}/>)}
          </div>
          {sel && <MemberDrawer m={sel} onClose={() => setSel(null)}/>}
        </div>
      </Band>

      {/* C+D · 角色×等級矩陣 / 權限分享 */}
      <div style={{ display: "grid", gridTemplateColumns: "3fr 2fr", gap: 0 }}>
        <div style={{ paddingRight: 28, minWidth: 0 }}>
        <Band no="C" title={permsText(biu, "角色 × 等級矩陣")} sub={t("等級越高授權越大 · 職級不提升角色權限")} delay={.2}>
          {roles.length ? (
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              <div style={{ display: "grid", gridTemplateColumns: gridCols, alignItems: "center", padding: "8px 0", borderBottom: "1px solid var(--hair)" }}>
                <LB dim style={{ fontSize: 8.5 }}>{t("角色")}</LB>
                {levels.map(l => <span key={l} className="mono" style={{ fontSize: 9, color: "var(--ink-3)", textAlign: "center" }}>L{l}</span>)}
                <LB dim style={{ fontSize: 8.5, textAlign: "right" }}>{t("成員數")}</LB>
                <LB dim style={{ fontSize: 8.5, textAlign: "right" }}>{t("權限數")}</LB>
              </div>
              {roles.map((r, i) => (
                <div key={r.name + ":" + i}
                  style={{ display: "grid", gridTemplateColumns: gridCols, alignItems: "center", padding: "11px 0", borderBottom: "1px solid var(--hair-soft)", cursor: "pointer" }}
                  title={t("把角色「{r}」(L{l})的權限清單和成員給我,並指出風險點", { r: r.name, l: r.level })}
                  onClick={() => ask(t("把角色「{r}」(L{l})的權限清單和成員給我,並指出風險點", { r: r.name, l: r.level }))}>
                  <span className="row g6" style={{ fontWeight: 650, fontSize: 12.5, minWidth: 0 }}>
                    <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.name}</span>
                  </span>
                  {levels.map(l => (
                    <span key={l} style={{
                      height: 13, margin: "0 2px", display: "block",
                      background: l < r.level ? "var(--paper-2)" : l === r.level ? (r.level === topLevel ? "var(--red)" : "var(--ink)") : "transparent",
                      border: "1px solid " + (l <= r.level ? "var(--hair)" : "var(--hair-soft)"),
                    }}/>
                  ))}
                  <span className="num" style={{ fontWeight: 700, textAlign: "right", fontSize: 13 }}>{r.members}</span>
                  <span className="num muted" style={{ textAlign: "right", fontSize: 12 }}>{r.perms || "—"}</span>
                </div>
              ))}
            </div>
          ) : <EM icon="layers" title={t("還沒有角色數據")} sub={t("對秘書說「幫我規劃角色體系」即可開始。")}/>}
        </Band>
        </div>

        <div style={{ borderLeft: "1px solid var(--hair)", paddingLeft: 28, minWidth: 0 }}>
        <Band no="D" title={permsText(biu, "分享記錄")} sub={t("只能分享自己持有且非核心的權限")} delay={.25}>
          {dels.length ? (
            <div style={{ borderTop: "2px solid var(--rule)" }}>
              {dels.slice(0, 8).map((d, i) => {
                const g = d.grantor_name || d.grantor_username || "—";
                const e2 = d.grantee_name || d.grantee_username || "—";
                const p = d.permission_label || d.permission_key || "—";
                return (
                  <div key={d.id != null ? d.id : i} className="ledger-row">
                    <span className="lr-idx">{pad2(i + 1)}</span>
                    <div className="col g4" style={{ flex: 1, minWidth: 0 }}>
                      <span className="mono" style={{ fontSize: 12, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{p}</span>
                      <span className="muted" style={{ fontSize: 11.5 }}>
                        {g} → {e2}{d.expires_at ? " · " + t("至 {d}", { d: String(d.expires_at).slice(0, 10) }) : ""}
                      </span>
                    </div>
                    <B size="sm" onClick={() => ask(t("撤回權限分享:{g} 分享給 {e} 的「{p}」;請與我確認後執行", { g, e: e2, p: d.permission_key || p }))}>{t("撤回")}</B>
                  </div>
                );
              })}
            </div>
          ) : <EM icon="shield" title={t("暫無有效分享")} sub={t("權限分享會列在這裡,審計日誌會標記委託來源。")}/>}
        </Band>
        </div>
      </div>
    </>
  );
};

window.W2.PAGES["perms"] = Page;
})();
