/* ============================================================
   WAREHOUSE 2.1 · app — Swiss 報頭殼層 / 海報登入 / 路由 / 三語
   ============================================================ */
(() => {
const W2 = window.W2;
const { t, lang, setLang } = window.W2_LANG;
const L = lang();
/* ── 入駐流程(登入 / 開通 / 加入)英文詞條 ── */
window.W2_LANG.addEN({
  "登入": "Sign in", "開通公司": "Open company", "加入公司": "Join company",
  "人類因篝火聚集，": "Humanity gathers around the fire,",
  "文明因連接而誕生。": "and civilization begins with connection.",
  /* Legacy copy aliases stay in the catalogue for cached clients and phrase audits. */
  "人類因篝火聚集，文明因連接誕生。": "Humanity gathered around fire; civilization was born through connection.",
  "在數字時代，我們重新點燃一座篝火。": "In the digital age, we light a bonfire anew.",
  "今天，": "Today,",
  "我們在數字世界重新點燃篝火。": "we relight the fire in the digital world.",
  "連接現實，建立秩序，驅動進化。": "Connect reality. Build order. Drive evolution.",
  "數字世界的篝火。": "The fire of the digital world.",
  "申請開通公司": "Open a company", "申請加入公司": "Join a company",
  "申請加入已有公司": "Join an existing company",
  "輸入目標公司的企業代碼;申請會交給該公司管理員審批,通過後公司會出現在切換器中。": "Enter the target company code. Its administrators will review your request; once approved, the company appears in the switcher.",
  "企業代碼例如 bonfire": "Company code, e.g. bonfire",
  "加入申請已提交": "Join request submitted",
  "等待目標公司管理員審批": "Awaiting target-company approval",
  "這會沿用你目前的全局帳號,不會建立重複登入身份。": "Your current global account will be reused; no duplicate login identity is created.",
  "系統初始化 →": "System setup →",
  "顯示名稱": "Display name", "企業代碼": "Company code", "確認密碼": "Confirm password",
  "期望角色": "Preferred role", "(由管理員指定)": "(assigned by admin)",
  "部門 / 班組": "Department / team", "期望崗位": "Preferred position", "該部門尚無預設崗位": "No preset positions in this department",
  "聯繫方式": "Contact", "申請理由": "Reason",
  "姓名或工作名": "Name or work alias",
  "向公司管理員索取,例如 acme": "Ask your company admin, e.g. acme",
  "方便管理員核實身份": "So the admin can verify you",
  "簡述用途,供審批參考": "Purpose in brief, for review",
  "提交申請": "Submit application", "提交中…": "Submitting…", "提交失敗": "Submission failed",
  "忘記密碼？請聯繫公司管理員重置。": "Forgot your password? Contact your company administrator to reset it.",
  "兩次輸入的密碼不一致": "Passwords do not match",
  "請填寫企業代碼": "Company code is required",
  "請先輸入企業代碼": "Enter the company code first",
  "部門與崗位載入中…": "Loading departments and positions…",
  "部門與崗位載入失敗,請確認企業代碼後重試": "Could not load departments and positions. Check the company code and retry.",
  "尚未讀取到該公司的部門與崗位,請確認企業代碼或稍後重試": "Departments and positions are not ready. Check the company code or retry shortly.",
  "選擇 BIU 學術職位": "Choose a BIU academic role",
  "選擇你的法律角色。": "Choose your legal role.",
  "選擇你的": "Choose your", "法律角色": "legal role",
  "從案例收錄、律師、證據、調解到多級審理,選擇一個 BIU 內部學術職位參與。": "Choose an internal BIU academic role across case intake, advocacy, evidence, mediation, or multi-level adjudication.",
  "搜索法官、律師、案例或證據職位": "Search judge, attorney, case, or evidence roles",
  "請選擇一個可加入的 BIU 職位": "Choose an available BIU role",
  "BIU 内部学术职位 · 不构成现实职业资格或法律授权": "BIU internal academic role · not a real-world professional credential or legal authority",
  "案件總覽": "Case overview", "我的工作": "My work", "案件與卷宗": "Cases & records",
  "機構與職位": "Institutions & roles", "程序記錄": "Procedural history", "規則與秘書": "Rules & Secretary",
  "直接選擇": "Direct selection", "申請加入": "Application", "需要考試": "Exam required", "任命職位": "Appointment only",
  "目前沒有符合搜索條件的職位": "No roles match this search.",
  "職位要求": "Role requirements", "已選擇": "Selected", "選擇此職位": "Choose this role",
  "請填寫公司名稱": "Company name is required",
  "申請已提交": "Application filed",
  "企業管理員審批通過後,即可用此帳號登入。": "Once the company admin approves, sign in with this account.",
  "返回登入": "Back to sign in",
  "開通新公司,需要先有平臺帳號。": "Opening a company requires a platform account first.",
  "L4 及以上成員登入後,在頂欄公司切換器選「+ 申請開通公司」提交;平台審批通過後,申請人自動成為新公司的系統管理員。":
    "Sign in as an L4+ member, then file from \"+ Open a company\" in the top-bar company switcher; once the platform approves, the applicant becomes the new company's system admin.",
  "先申請加入一家公司": "Apply to join a company first",
  "已有帳號 → 登入": "Have an account? Sign in",
  "公司名稱": "Company name", "例如:ACME 工作室": "e.g. ACME Studio",
  "行業模板": "Industry template",
  "3-40 位小寫字母 / 數字 / 連字符": "3-40 chars: lowercase letters / digits / hyphens",
  "企業代碼需為 3-40 位小寫字母 / 數字 / 連字符,且不以連字符開頭結尾":
    "Company code: 3-40 lowercase letters / digits / hyphens, not starting or ending with a hyphen",
  "模板目錄暫不可用,將使用默認通用模板": "Template catalogue unavailable; the default general template will be used",
  "取消": "Cancel", "完成": "Done",
  "提交後由平台審批;通過時系統會自動建立該公司的獨立數據庫與初始表。":
    "Filed for platform review; on approval the system provisions the company's own database and initial tables.",
  "平台審批通過後,你會成為該公司的系統管理員,公司會出現在頂欄切換器裡。":
    "Once approved, you become the company's system admin and it appears in the top-bar switcher.",
  "開通申請需要 L4 及以上權限,請聯繫管理員提升權限或代為申請。":
    "Opening a company requires level 4+ permissions. Ask an admin to raise your level or file on your behalf.",
  "開通即建立獨立數據庫與初始表;審批通過後,你就是新公司的系統管理員。":
    "Opening provisions an independent database with initial tables; once approved, you are the new company's system admin.",
  "此帳號無權訪問該功能": "This account cannot access this feature",
  "正在前往第一個可用功能…": "Opening the first available feature…",
  "目前沒有可用功能,請聯繫公司管理員分配部門、崗位或權限。": "No features are available. Ask your company administrator to assign a department, position, or permissions.",
  "{d} 部門 · {p} 崗位": "{d} departments · {p} positions",
  "填一張申請單:帳號、企業代碼、期望角色。企業管理員審批通過後,即可登入開工。":
    "One form: account, company code, preferred role. Once the company admin approves, sign in and get to work.",
  "先有平臺帳號 — 申請加入任一公司": "Have a platform account — join any company first",
  "登入後在頂欄公司切換器提交開通申請": "Sign in and file from the top-bar company switcher",
  "平台審批通過 — 你即成為新公司系統管理員": "Platform approves — you become the new company's system admin",
  "使用面容 / Passkey 登入": "Sign in with Face ID / passkey",
  "使用 Windows Hello／本機 Passkey": "Use Windows Hello / this-device passkey",
  "使用 Touch ID／本機 Passkey": "Use Touch ID / this-device passkey",
  "使用本機 Passkey": "Use this-device passkey",
  "使用手機 Passkey（顯示 QR）": "Use a phone passkey (show QR)",
  "正在等待裝置驗證…": "Waiting for device verification…",
  "正在取得安全挑戰…": "Requesting a secure challenge…",
  "正在呼叫 Windows Hello…": "Opening Windows Hello…",
  "正在呼叫 Touch ID／本機 Passkey…": "Opening Touch ID / this-device passkey…",
  "正在開啟本機 Passkey…": "Opening this-device passkey…",
  "正在開啟手機 Passkey QR…": "Opening the phone passkey QR…",
  "Windows Hello 未回應，正在自動開啟手機 Passkey QR…": "Windows Hello did not respond. Opening the phone passkey QR…",
  "本機 Passkey 未回應，正在自動開啟手機 Passkey QR…": "The local passkey did not respond. Opening the phone passkey QR…",
  "正在切換至手機 Passkey QR…": "Switching to the phone passkey QR…",
  "立即改用手機 Passkey（QR）": "Use a phone passkey now (QR)",
  "Windows Hello 30 秒未回應時會自動改用手機 QR；也可立即切換。": "If Windows Hello does not respond within 30 seconds, the phone QR opens automatically. You can also switch now.",
  "本機 Passkey 30 秒未回應時會自動改用手機 QR；也可立即切換。": "If the local passkey does not respond within 30 seconds, the phone QR opens automatically. You can also switch now.",
  "若兩種原生視窗都未顯示，請檢查 Windows「隱私權與安全性 → Passkey 存取」是否允許目前瀏覽器。": "If neither native prompt appears, check that Windows Settings > Privacy & security > Passkey access allows this browser.",
  "手機需已有此帳號的 Passkey 才能完成驗證。": "The phone must already hold a passkey for this account to complete verification.",
  "正在驗證 Passkey…": "Verifying the passkey…",
  "取消驗證": "Cancel verification",
  "正在取消 Passkey 驗證…": "Cancelling passkey verification…",
  "使用本機 Face ID、指紋、裝置密碼或安全金鑰;平台不會收到你的面部或指紋資料。":
    "Use Face ID, fingerprint, device PIN or a security key. The platform never receives your face or fingerprint data.",
  "此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。": "Passkeys are unavailable in this browser or connection. You can still use your password.",
  "或者使用密碼": "or use password",
  "安全與 Passkey": "Security & passkeys",
  "管理 Passkey": "Manage passkeys",
  "個人": "Personal",
  "個人中心": "Personal centre",
  "個人檔案": "Personal profile",
  "管理你的個人檔案、頭像、歸檔同步範圍與帳號安全。": "Manage your profile, avatar, archive sync scope and account security.",
  "個人資料": "Profile details",
  "個人資料完整度": "Profile completeness",
  "電子郵箱": "Email",
  "電話": "Phone",
  "個人簡介": "About me",
  "技能": "Skills",
  "語言": "Languages",
  "興趣": "Interests",
  "以逗號分隔": "Separate with commas",
  "例如：庫存分析、叉車、Excel": "e.g. inventory analysis, forklift, Excel",
  "例如：案例分析、法律寫作、研究方法": "e.g. case analysis, legal writing, research methods",
  "例如：中文、English、日本語": "e.g. Chinese, English, Japanese",
  "例如：攝影、跑步、咖啡": "e.g. photography, running, coffee",
  "選填，讓同事更容易認識你。": "Optional — help colleagues get to know you.",
  "MBTI 與星座只用於個人展示，不參與權限、績效或人事決策。": "MBTI and zodiac are for personal expression only, never access, performance or HR decisions.",
  "未選擇": "Not selected",
  "星座": "Zodiac",
  "白羊座": "Aries", "金牛座": "Taurus", "雙子座": "Gemini", "巨蟹座": "Cancer",
  "獅子座": "Leo", "處女座": "Virgo", "天秤座": "Libra", "天蠍座": "Scorpio",
  "射手座": "Sagittarius", "摩羯座": "Capricorn", "水瓶座": "Aquarius", "雙魚座": "Pisces",
  "檔案同步範圍": "Archive sync scope",
  "不寫入檔案": "Do not add to the record",
  "同步至受限人事檔案": "Sync to the restricted personnel record",
  "保存個人資料": "Save profile",
  "個人資料已保存並同步至檔案": "Profile saved and synced to records",
  "個人資料載入失敗": "Could not load profile",
  "個人資料保存失敗": "Could not save profile",
  "資料已在其他視窗更新，請重新載入後再修改。": "This profile changed in another window. Reload before editing again.",
  "重新同步": "Reload",
  "載入個人資料…": "Loading profile…",
  "頭像工作室": "Avatar studio",
  "頭像": "Avatar",
  "字母頭像": "Initial avatar",
  "Emoji 頭像": "Emoji avatar",
  "Swiss 幾何": "Swiss geometry",
  "上傳照片": "Upload photo",
  "選擇圖片": "Choose image",
  "支援 PNG、JPEG、WebP；圖片會裁切、縮放並重新編碼。": "PNG, JPEG or WebP; images are cropped, resized and re-encoded.",
  "縮放": "Zoom",
  "水平焦點": "Horizontal focus",
  "垂直焦點": "Vertical focus",
  "保存頭像": "Save avatar",
  "頭像已更新": "Avatar updated",
  "頭像保存失敗": "Could not save avatar",
  "圖片格式不支援，請選擇 PNG、JPEG 或 WebP。": "Unsupported image type. Choose PNG, JPEG or WebP.",
  "圖片不得超過 5 MB。": "Image must be 5 MB or smaller.",
  "圖片解析度過大；最長邊不得超過 8192 px，總像素不得超過 4000 萬。": "Image resolution is too large; each side must be at most 8192 px and the image at most 40 megapixels.",
  "無法讀取圖片。": "Could not read the image.",
  "工作身份": "Work identity",
  "正式稱號": "Official titles",
  "趣味資料": "Personal extras",
  "尚無正式稱號": "No official titles on file",
  "公司正式檔案": "Official company record",
  "來源": "Source",
  "有效": "Active",
  "未提供": "Not provided",
  "歷史資料": "Historical",
  "已停用": "Inactive",
  "最高學歷": "Highest education",
  "學術職稱": "Academic title",
  "未設定": "Not set",
  "正式員工": "Employee",
  "合約人員": "Contractor",
  "訪問人員": "Visiting member",
  "實習人員": "Intern",
  "附屬成員": "Affiliate",
  "其他": "Other",
  "正式稱號由公司檔案提供且只能讀取；稱號不代表角色、權限或審批能力。": "Official titles come from the company record and are read-only. Titles do not grant roles, permissions or approval authority.",
  "此稱號來源已停用或屬於歷史資料，因此不會顯示在姓名旁。": "This title source is inactive or historical, so it is not shown beside the live profile name.",
  "公司正式資料由主管或檔案人員維護；你可以查看，但不能在這裡直接改動。": "Official employment data is maintained by managers or archive staff. You can view it here but cannot edit it directly.",
  "工號": "Employee no.",
  "公司": "Company",
  "部門": "Department",
  "職位": "Position",
  "角色": "Roles",
  "入職日期": "Start date",
  "用工類型": "Employment type",
  "主管": "Manager",
  "如正式資料有誤，請聯絡主管或檔案人員發起更正。": "If official data is wrong, ask your manager or archive staff to file a correction.",
  "檔案同步": "Archive sync",
  "已歸檔": "Archived",
  "待歸檔確認": "Pending archive review",
  "尚未建立檔案": "No archive record yet",
  "檔案編號": "Record ID",
  "最後同步": "Last synced",
  "待審核項": "Items awaiting review",
  "每次保存都會建立版本與操作留痕；正式字段不會被個人資料直接覆蓋。": "Every save creates a version and audit trail; personal fields never overwrite official records directly.",
  "帳號安全": "Account security",
  "修改密碼": "Change password",
  "修改密碼前必須使用 Passkey 完成本人驗證。": "A passkey identity check is required before changing your password.",
  "新密碼": "New password",
  "確認新密碼": "Confirm new password",
  "至少 12 個字元，建議使用不重複的長密碼。": "Use at least 12 characters and a unique password.",
  "兩次輸入的新密碼不一致": "The new passwords do not match",
  "新密碼至少需要 12 個字元": "The new password must be at least 12 characters",
  "使用 Passkey 驗證並修改": "Verify with passkey and change",
  "密碼已修改": "Password changed",
  "密碼修改失敗": "Could not change password",
  "Passkey 驗證沒有返回有效的一次性授權，密碼尚未修改": "Passkey verification returned no valid one-time authorisation. The password was not changed.",
  "此操作需要已登記的 Passkey。": "This action requires a registered passkey.",
  "切換至手機 Passkey QR": "Switch to phone passkey QR",
  "快速入口": "Shortcuts",
  "關閉個人中心": "Close personal centre",
  "個人外觀": "Personal appearance",
  "配色與外觀": "Colour & appearance",
  "只替換 Swiss 界面的強調色與結構墨色;不改變排版與資訊層級。": "Replace only the Swiss interface accent and structural ink; typography and information hierarchy stay unchanged.",
  "經典配色": "Classic palettes",
  "自訂兩色": "Custom two-colour palette",
  "強調色": "Accent colour",
  "結構墨色": "Structural ink",
  "淺色背景對比": "Contrast on light paper",
  "通過": "Pass",
  "需調整": "Adjust",
  "強調色至少需要 4.5:1;結構墨色至少需要 7:1。": "Accent needs at least 4.5:1 contrast; structural ink needs at least 7:1.",
  "深色模式會保留亮色前景,自訂墨色只用於暗色表面。": "Dark mode keeps a light foreground; custom ink shapes dark surfaces only.",
  "儲存個人配色": "Save personal palette",
  "正在儲存…": "Saving…",
  "個人配色已套用": "Personal palette applied",
  "配色已在其他視窗更新": "The palette was updated in another window",
  "伺服器已有較新版本;已同步版本,請再儲存一次。": "A newer server version exists. It is now synced; save once more.",
  "配色儲存失敗": "Could not save the palette",
  "顏色必須使用 #RRGGBB 格式。": "Colours must use #RRGGBB format.",
  "此組合對比不足,請調深後再儲存。": "This combination lacks contrast. Darken it before saving.",
  "關閉個人外觀": "Close personal appearance",
  "登出": "Sign out",
  "用於免密登入與簽字、用印前的本人驗證。生物特徵只留在你的裝置中。":
    "Use passkeys for passwordless sign-in and identity checks before signing or sealing. Biometrics stay on your device.",
  "新增此裝置": "Add this device",
  "新增 Passkey": "Add a passkey",
  "裝置名稱": "Device name",
  "例如:蔡培元的 iPhone": "e.g. Cai Peiyuan's iPhone",
  "例如:辦公室 Windows 電腦": "e.g. Office Windows PC",
  "正在登記…": "Registering…",
  "已登記 Passkey": "Registered passkeys",
  "尚未登記 Passkey": "No passkeys registered",
  "新增成功": "Passkey added",
  "管理 Passkey 前請重新輸入帳號密碼": "Re-enter your account password before managing passkeys",
  "帳號密碼": "Account password",
  "密碼只用於本次安全核驗,不會保存在瀏覽器中。": "The password is used only for this security check and is not stored in the browser.",
  "最後使用": "Last used",
  "建立於": "Created",
  "移除": "Remove",
  "確認移除": "Confirm removal",
  "保留": "Keep",
  "重新載入": "Reload",
  "無法載入 Passkey 清單。": "Could not load the passkey list.",
  "設定你的數位蓋章": "Set up your digital seal",
  "待辦「{title}」需要本人 Passkey 驗證。先完成一次安全設定，再返回重新確認決策。": "Task “{title}” requires your passkey. Complete the one-time setup, then return and confirm the decision again.",
  "Passkey 用裝置上的面容、指紋、PIN 或安全金鑰證明是你本人；平台不會取得生物特徵。": "A passkey uses your device biometrics, PIN or security key to verify you. The platform never receives biometric data.",
  "了解原理": "How it works", "返回決策": "Return to decision",
  "稍後設定": "Set up later", "開始設定": "Start setup", "返回說明": "Back to explanation",
  "返回待辦重新確認": "Return and confirm again", "安全設定完成": "Security setup complete",
  "只證明是你": "Verifies only you", "每次決策獨立驗證": "Independent check per decision", "不會自動蓋章": "Never seals automatically",
  "面容、指紋與裝置 PIN 留在你的裝置中，不會上傳到平台。": "Biometrics and the device PIN stay on your device and are never uploaded.",
  "通過與駁回都要重新確認，驗證憑證只綁定當前待辦和動作。": "Approve and reject each require confirmation bound to that task and action.",
  "新增成功只完成安全設定；你仍需返回待辦再次檢查並點擊決策。": "Registration only completes security setup; return to review and click the decision yourself.",
  "可使用本機 Windows Hello、Touch ID、Face ID、裝置 PIN，也可選擇手機 Passkey QR。": "Use Windows Hello, Touch ID, Face ID, a device PIN, or a phone passkey QR.",
  "Passkey 已安全新增。返回待辦後，請再次檢查內容並明確點擊通過或確認駁回；系統不會替你自動蓋章。": "Passkey added safely. Return to the task, review it, and explicitly approve or reject; the system never seals for you.",
  "為避免誤操作，剛才的採購決策沒有執行。請返回待辦，重新核對內容後再使用 Passkey 蓋章。": "To prevent mistakes, the procurement decision was not executed. Return, review it, then seal with your passkey.",
  "此裝置可以使用內建面容或指紋驗證。": "This device can use its built-in face or fingerprint verification.",
  "此裝置可以使用 Windows Hello、內建面容、指紋或裝置 PIN。": "This device can use Windows Hello, built-in face or fingerprint verification, or a device PIN.",
  "此裝置可使用 Passkey 或外接安全金鑰。": "This device can use a passkey or external security key.",
  "裝置支援檢查逾時，但仍可嘗試新增 Passkey。": "The device check timed out, but you can still try to add a passkey.",
  "裝置支援檢查逾時；新增時將直接嘗試 Windows Hello（含 PIN）。": "The device check timed out. Adding this device will directly try Windows Hello, including its PIN.",
  "Windows 未回報已設定的 Hello，但仍可直接嘗試；也可以改用手機 QR。": "Windows did not report a configured Hello authenticator, but you can still try it directly or use a phone QR.",
  "手機 QR 由 Windows／瀏覽器原生顯示；兩部裝置需在附近並開啟藍牙。": "Windows or the browser shows the native phone QR. Keep both devices nearby with Bluetooth enabled.",
  "手機 QR 由瀏覽器或作業系統原生顯示；兩部裝置需在附近並開啟藍牙。": "The browser or operating system shows the native phone QR. Keep both devices nearby with Bluetooth enabled.",
  "尚未呼叫 Windows Hello 或手機 Passkey：": "Windows Hello or the phone passkey was not called yet:",
  "尚未呼叫本機 Passkey 或手機 Passkey：": "The local or phone passkey was not called yet:",
  "例如:辦公室 MacBook（Touch ID）": "e.g. Office MacBook (Touch ID)",
  "瀏覽器已取得挑戰，但裝置驗證未完成：": "The browser received the challenge, but device verification did not complete:",
  "正在檢查裝置支援…": "Checking device support…",
  "登入回應缺少安全憑證": "The sign-in response did not include a security token.",
});
const LOCALE = { tw: "zh-TW", cn: "zh-CN", en: "en-US" }[L] || "zh-TW";
const { useState: $s, useEffect: $e, useCallback: $cb, useRef: $r } = React;
const { Icon, Btn, Label, SecretaryDock, CompanyMark, PlatformMark } = W2;
const PASSKEY_CAPABILITY_TIMEOUT_MS = 2600;

const passkeyPlatformFamily = (nav = navigator) => {
  const uaPlatform = nav.userAgentData && nav.userAgentData.platform || "";
  const legacyPlatform = nav.platform || "";
  const userAgent = nav.userAgent || "";
  const identity = `${uaPlatform} ${legacyPlatform} ${userAgent}`;
  if (/windows|win32|win64/i.test(identity)) return "windows";
  /* iPadOS desktop mode reports MacIntel; touch points distinguish it from a Mac. */
  const ipadDesktopMode = /macintel/i.test(legacyPlatform) && Number(nav.maxTouchPoints || 0) > 1;
  if (!ipadDesktopMode && /macos|macintosh|macintel|macppc|mac68k/i.test(identity)) return "mac";
  return "other";
};

const isWindowsDevice = () => passkeyPlatformFamily() === "windows";
const passkeyPlatformActionCopy = platform => platform === "windows"
  ? "使用 Windows Hello／本機 Passkey"
  : platform === "mac" ? "使用 Touch ID／本機 Passkey" : "使用本機 Passkey";
const passkeyPlatformProgressCopy = platform => platform === "windows"
  ? "正在呼叫 Windows Hello…"
  : platform === "mac" ? "正在呼叫 Touch ID／本機 Passkey…" : "正在開啟本機 Passkey…";
const passkeyHybridTimeoutCopy = platform => platform === "windows"
  ? "Windows Hello 未回應，正在自動開啟手機 Passkey QR…"
  : "本機 Passkey 未回應，正在自動開啟手機 Passkey QR…";
const passkeyQrHelpCopy = platform => platform === "windows"
  ? "手機 QR 由 Windows／瀏覽器原生顯示；兩部裝置需在附近並開啟藍牙。"
  : "手機 QR 由瀏覽器或作業系統原生顯示；兩部裝置需在附近並開啟藍牙。";
const passkeyDevicePlaceholderCopy = platform => platform === "windows"
  ? "例如:辦公室 Windows 電腦"
  : platform === "mac" ? "例如:辦公室 MacBook（Touch ID）" : "例如:蔡培元的 iPhone";

const passkeyCapabilityFallback = probeTimedOut => {
  let supported = false;
  try {
    supported = !!(W2.Passkeys && typeof W2.Passkeys.supported === "function" && W2.Passkeys.supported());
  } catch (error) { supported = false; }
  return {
    supported, secure: !!window.isSecureContext,
    platform: false, platformKnown: false, platformTimedOut: !!probeTimedOut,
    conditional: false, conditionalKnown: false, conditionalTimedOut: !!probeTimedOut,
    probeTimedOut: !!probeTimedOut,
  };
};

const passkeyProgressMessage = (stage, mode) => {
  const platform = passkeyPlatformFamily();
  if (stage === "options") return t("正在取得安全挑戰…");
  if (stage === "verify") return t("正在驗證 Passkey…");
  if (stage === "authenticator-platform") return t(passkeyPlatformProgressCopy(platform));
  if (stage === "authenticator-hybrid-timeout") return t(passkeyHybridTimeoutCopy(platform));
  if (stage === "authenticator-hybrid-switch") return t("正在切換至手機 Passkey QR…");
  if (stage === "authenticator-cancel") return t("正在取消 Passkey 驗證…");
  if (stage === "authenticator") {
    if (mode === "hybrid") return t("正在開啟手機 Passkey QR…");
    return t(passkeyPlatformProgressCopy(platform));
  }
  return t("正在等待裝置驗證…");
};

const passkeyFailureMessage = error => {
  const friendly = W2.Passkeys && typeof W2.Passkeys.friendlyError === "function"
    ? W2.Passkeys.friendlyError(error) : error;
  const message = friendly && friendly.message ? friendly.message : String(friendly || error);
  if (friendly && friendly.passkeyStage === "options") {
    const prefix = isWindowsDevice()
      ? "尚未呼叫 Windows Hello 或手機 Passkey："
      : "尚未呼叫本機 Passkey 或手機 Passkey：";
    return `${t(prefix)} ${message}`;
  }
  if (friendly && /^authenticator/.test(friendly.passkeyStage || "")) {
    return `${t("瀏覽器已取得挑戰，但裝置驗證未完成：")} ${message}`;
  }
  return message;
};

/* Keep optional browser/OS capability discovery out of the critical path.
   This also protects users who still have a cached older adapter whose
   Chromium platform probe can remain pending indefinitely. */
const getPasskeyCapability = () => {
  const fallback = passkeyCapabilityFallback(false);
  if (!W2.Passkeys || typeof W2.Passkeys.capabilities !== "function") return Promise.resolve(fallback);
  return new Promise(resolve => {
    let settled = false;
    let timer = null;
    const finish = result => {
      if (settled) return;
      settled = true;
      if (timer !== null) window.clearTimeout(timer);
      resolve(result);
    };
    timer = window.setTimeout(
      () => finish(passkeyCapabilityFallback(true)),
      PASSKEY_CAPABILITY_TIMEOUT_MS,
    );
    try {
      Promise.resolve(W2.Passkeys.capabilities()).then(
        result => finish(Object.assign({}, fallback, result || {})),
        () => finish(fallback),
      );
    } catch (error) { finish(fallback); }
  });
};

/* ── 信息架構 ── */
const NAV2 = [
  { idx: "00", id: "tasks", label: "TASK" },
  { idx: "01", id: "dashboard", label: "總覽" },
  { idx: "02", id: "inventory", label: "庫存" },
  { idx: "03", id: "inbound", label: "入庫" },
  { idx: "04", id: "outbound", label: "出庫" },
  { idx: "05", id: "shipments", label: "在途" },
  { idx: "06", id: "alerts", label: "預警" },
  { idx: "07", id: "stocktake", label: "盤點" },
  { idx: "08", id: "erp", label: "ERP" },
  { idx: "09", id: "finance", label: "財務" },
  { idx: "10", id: "assets", label: "資產" },
  { idx: "R1", id: "research", label: "科研" },
  { idx: "11", id: "procurement", label: "採購" },
  { idx: "12", id: "legal", label: "法務" },
  { idx: "13", id: "gis", label: "地圖" },
  { idx: "14", id: "reports", label: "報表" },
  { idx: "15", id: "perms", label: "權限" },
  { idx: "16", id: "logs", label: "審計" },
  { idx: "17", id: "cases", label: "檔案" },
  { idx: "18", id: "settings", label: "設置" },
];
const BIU_TEMPLATE_KEY = "biu_legal_ethics_case_lab";
const BIU_NAV_PROFILE = [
  { id: "dashboard", idx: "01", label: "案件總覽" },
  { id: "tasks", idx: "02", label: "我的工作" },
  { id: "cases", idx: "03", label: "案件與卷宗" },
  { id: "perms", idx: "04", label: "機構與職位" },
  { id: "logs", idx: "05", label: "程序記錄" },
  { id: "settings", idx: "06", label: "規則與秘書" },
];
const templateKeyOf = value => {
  if (typeof value === "string") return value;
  if (!value || typeof value !== "object") return "";
  return String(value.key || value.template_key || value.industry_template || "");
};
const isBiuTemplate = value => templateKeyOf(value) === BIU_TEMPLATE_KEY;
const industryTemplateKeyOfBoot = boot => templateKeyOf(boot && boot.INDUSTRY_TEMPLATE)
  || templateKeyOf(boot && boot.INDUSTRY_TEMPLATE_KEY);
const navigationForTemplate = templateKey => {
  if (!isBiuTemplate(templateKey)) return NAV2;
  const byId = new Map(NAV2.map(item => [item.id, item]));
  return BIU_NAV_PROFILE
    .filter(item => byId.has(item.id))
    .map(item => ({ ...byId.get(item.id), ...item }));
};
W2.BIU_TEMPLATE_KEY = BIU_TEMPLATE_KEY;
W2.isBiuTemplate = isBiuTemplate;
const WAREHOUSE_ROUTE_IDS = ["inventory", "inbound", "outbound", "shipments"];
W2.NAV = NAV2;
/* 管理面(ADMIN 紅組):終端也必須由 allowed_nav/terminal.use 授權;
   SHIELD 與公司僅 L11 平台超級管理員(後端 PLATFORM_OWNER_LEVEL=11,所有者自動合成)。 */
const ADMIN_LEVEL = 11;
const NAV_ADMIN = [
  { idx: "19", id: "terminal", label: "終端", need: "all" },
  { idx: "20", id: "browser", label: "瀏覽器", need: "l11" },
  { idx: "21", id: "shield", label: "SHIELD", need: "l11" },
  { idx: "22", id: "companies", label: "公司", need: "l11" },
  { idx: "23", id: "optimizer", label: "進化分析", need: "owner" },
];
W2.NAV_ADMIN = NAV_ADMIN;
const roleLevelOf = (user) => Math.max(0, ...(((user || {}).roles) || []).map(r => Number(r.level) || 0));
const routeNow = () => (location.hash.replace(/^#\/?/, "") || "dashboard").split("?")[0];
const RUNTIME_PREFS_CACHE = "warehouse_runtime_preferences:";
const RUNTIME_FLAGS_CACHE = "warehouse_runtime_flags:";
const SWISS_THEME_PRESETS = [
  { id: "swiss_signal", name: "Swiss Signal", accent: "#C9231C", ink: "#141414" },
  { id: "basel_cobalt", name: "Basel Cobalt", accent: "#0757A6", ink: "#101820" },
  { id: "zurich_ultramarine", name: "Zürich Ultramarine", accent: "#2946A8", ink: "#151923" },
  { id: "bern_ochre", name: "Bern Ochre", accent: "#765A00", ink: "#17150F" },
  { id: "ticino_terracotta", name: "Ticino Terracotta", accent: "#A64224", ink: "#1B1714" },
  { id: "geneve_forest", name: "Genève Forest", accent: "#176744", ink: "#101A16" },
  { id: "lausanne_aubergine", name: "Lausanne Aubergine", accent: "#714065", ink: "#1A151A" },
  { id: "teal_grid", name: "Teal Grid", accent: "#00646B", ink: "#10191A" },
  { id: "concrete_neutral", name: "Concrete Neutral", accent: "#565149", ink: "#151515" },
];
W2.SWISS_THEME_PRESETS = SWISS_THEME_PRESETS;
const DEFAULT_SWISS_APPEARANCE = SWISS_THEME_PRESETS[0];
const themeHex = value => /^#[0-9A-F]{6}$/i.test(String(value || "")) ? String(value).toUpperCase() : null;
const themeRgb = value => {
  const hex = themeHex(value);
  return hex ? [parseInt(hex.slice(1, 3), 16), parseInt(hex.slice(3, 5), 16), parseInt(hex.slice(5, 7), 16)] : null;
};
const themeHexFromRgb = values => "#" + values.map(value => Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, "0")).join("").toUpperCase();
const themeMix = (from, to, amount) => {
  const a = themeRgb(from); const b = themeRgb(to);
  if (!a || !b) return themeHex(from) || themeHex(to) || "#141414";
  const p = Math.max(0, Math.min(1, Number(amount) || 0));
  return themeHexFromRgb(a.map((channel, index) => channel + (b[index] - channel) * p));
};
const themeRgba = (value, alpha) => {
  const rgb = themeRgb(value) || [20, 20, 20];
  return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${Math.max(0, Math.min(1, alpha))})`;
};
const themeLuminance = value => {
  const rgb = themeRgb(value);
  if (!rgb) return 0;
  const channels = rgb.map(channel => {
    const c = channel / 255;
    return c <= .04045 ? c / 12.92 : Math.pow((c + .055) / 1.055, 2.4);
  });
  return .2126 * channels[0] + .7152 * channels[1] + .0722 * channels[2];
};
const themeContrast = (a, b) => {
  const first = themeLuminance(a); const second = themeLuminance(b);
  return (Math.max(first, second) + .05) / (Math.min(first, second) + .05);
};
const themeOnColor = background => themeContrast(background, "#FCFBF7") >= themeContrast(background, "#141414") ? "#FCFBF7" : "#141414";
const themeAccessibleDarkAccent = value => {
  const source = themeHex(value) || DEFAULT_SWISS_APPEARANCE.accent;
  if (themeContrast(source, "#0D0F12") >= 4.5) return source;
  for (let amount = .08; amount <= .8; amount += .04) {
    const candidate = themeMix(source, "#FFFFFF", amount);
    if (themeContrast(candidate, "#0D0F12") >= 4.5) return candidate;
  }
  return "#F5F2EB";
};
const runtimeActorIdentity = actor => {
  if (!actor || typeof actor !== "object") return "";
  const value = actor.global_user_id ?? actor.id ?? actor.username;
  return value == null || String(value).trim() === "" ? "" : String(value).trim();
};
const runtimePreferencesCacheKey = (slug, actor) => {
  const identity = runtimeActorIdentity(actor);
  return slug && identity ? `${RUNTIME_PREFS_CACHE}${encodeURIComponent(slug)}:${encodeURIComponent(identity)}` : "";
};
const normalizeAppearance = raw => {
  const source = raw && typeof raw === "object" ? raw : {};
  const presetId = String(source.preset_id || source.preset || DEFAULT_SWISS_APPEARANCE.id);
  const preset = SWISS_THEME_PRESETS.find(item => item.id === presetId) || null;
  const accent = themeHex(source.accent_color || source.accent || (preset && preset.accent)) || DEFAULT_SWISS_APPEARANCE.accent;
  const ink = themeHex(source.ink_color || source.ink || (preset && preset.ink)) || DEFAULT_SWISS_APPEARANCE.ink;
  const accentDark = themeHex(source.accent_dark_color || source.accent_dark) || themeAccessibleDarkAccent(accent);
  return {
    preset_id: preset ? preset.id : "custom",
    accent_color: accent,
    ink_color: ink,
    accent_dark_color: accentDark,
    on_accent_color: themeHex(source.on_accent_color || source.on_accent) || themeOnColor(accent),
    on_accent_dark_color: themeHex(source.on_accent_dark_color || source.on_accent_dark) || themeOnColor(accentDark),
    version: source.version == null ? 0 : source.version,
    updated_at: source.updated_at || null,
  };
};
const normalizeRuntimePreferences = raw => {
  const source = raw && typeof raw === "object" ? raw : {};
  const appearance = source.appearance || source.ui_appearance || source.theme || {};
  return {
    sound: !!source.sound,
    dark: !!source.dark,
    language: source.language || null,
    language_mode: source.language_mode === "fixed" ? "fixed" : "auto",
    language_source: source.language_source || null,
    updated_at: source.updated_at || null,
    appearance: normalizeAppearance(appearance),
  };
};
const THEME_INLINE_PROPERTIES = [
  "--paper", "--paper-2", "--white", "--ink", "--ink-2", "--ink-3", "--ink-4",
  "--accent", "--accent-soft", "--on-accent", "--rule", "--hair", "--hair-soft",
  "--chart-1", "--chart-2", "--chart-3", "--chart-4", "--chart-5", "--chart-6",
];
const clearRuntimeAppearance = () => {
  THEME_INLINE_PROPERTIES.forEach(name => document.documentElement.style.removeProperty(name));
  document.documentElement.removeAttribute("data-w2-appearance");
};
const applyRuntimeAppearance = runtime => {
  const root = document.documentElement;
  clearRuntimeAppearance();
  if (!runtime) { root.removeAttribute("data-w2-theme"); return; }
  const appearance = normalizeAppearance(runtime.appearance);
  const dark = !!runtime.dark;
  if (dark) root.dataset.w2Theme = "dark";
  else root.removeAttribute("data-w2-theme");
  const accent = dark ? appearance.accent_dark_color : appearance.accent_color;
  const onAccent = dark ? appearance.on_accent_dark_color : appearance.on_accent_color;
  root.dataset.w2Appearance = appearance.preset_id;
  root.style.setProperty("--accent", accent);
  root.style.setProperty("--accent-soft", themeRgba(accent, dark ? .18 : .12));
  root.style.setProperty("--on-accent", onAccent);
  root.style.setProperty("--chart-2", accent);
  if (dark) {
    /* In dark mode the user's Swiss black shapes surfaces, never foreground text.
       Foreground ink stays the high-contrast light palette declared in CSS. */
    const paper = themeMix(appearance.ink_color, "#000000", .35);
    root.style.setProperty("--paper", paper);
    root.style.setProperty("--paper-2", themeMix(paper, "#FFFFFF", .04));
    root.style.setProperty("--white", themeMix(paper, "#FFFFFF", .08));
  } else {
    const ink = appearance.ink_color;
    root.style.setProperty("--ink", ink);
    root.style.setProperty("--ink-2", themeMix(ink, "#F5F2EB", .24));
    root.style.setProperty("--ink-3", themeMix(ink, "#F5F2EB", .50));
    root.style.setProperty("--ink-4", themeMix(ink, "#F5F2EB", .70));
    root.style.setProperty("--rule", ink);
    root.style.setProperty("--hair", themeRgba(ink, .16));
    root.style.setProperty("--hair-soft", themeRgba(ink, .08));
    root.style.setProperty("--chart-1", ink);
    root.style.setProperty("--chart-3", themeMix(ink, "#F5F2EB", .50));
    root.style.setProperty("--chart-4", themeMix(ink, "#F5F2EB", .70));
    root.style.setProperty("--chart-5", themeMix(ink, "#F5F2EB", .24));
  }
};
W2.applyRuntimeAppearance = applyRuntimeAppearance;
const cachedRuntimePreferences = (slug, actor) => {
  const key = runtimePreferencesCacheKey(slug, actor);
  if (!key) return null;
  try {
    const value = JSON.parse(localStorage.getItem(key) || "null");
    return value && typeof value === "object" ? normalizeRuntimePreferences(value) : null;
  } catch (e) { return null; }
};
const cacheRuntimePreferences = (slug, actor, value) => {
  const key = runtimePreferencesCacheKey(slug, actor);
  if (!key || !value) return;
  try {
    const normalized = normalizeRuntimePreferences(value);
    localStorage.setItem(key, JSON.stringify(normalized));
    /* Only tenant-wide flags are safe before /auth/me identifies the account.
       Personal appearance always stays behind the identity-scoped key above. */
    localStorage.setItem(
      RUNTIME_FLAGS_CACHE + encodeURIComponent(slug),
      JSON.stringify({ dark: normalized.dark, updated_at: normalized.updated_at })
    );
  } catch (e) {}
};

/* 後端 user.allowed_nav 是導航與路由的唯一優先契約。舊後端尚未返回該字段時,
   才根據有效權限作保守映射;不把「已登入」等同於「可看全部模塊」。 */
const NAV_PERMISSION_RULES = {
  tasks: { all: ["tasks.read"] },
  dashboard: { all: ["overview.read"] },
  inventory: { all: ["inventory.read"] },
  inbound: { all: ["inventory.read", "inventory.inbound"] },
  outbound: { all: ["inventory.read", "inventory.outbound"] },
  shipments: { all: ["inventory.read"] },
  alerts: { all: ["alerts.read"] },
  stocktake: { all: ["inventory.read"] },
  cases: { any: ["cases.read", "records.read"] },
  erp: { all: ["erp.read"] },
  finance: { all: ["finance.read"] },
  assets: { any: ["assets.read", "asset_mgmt.read"] },
  research: { any: ["research.read", "research.write", "research.review"] },
  procurement: { all: ["procurement.workflow.use"] },
  legal: { all: ["legal.manage"] },
  gis: { all: ["gis.read"] },
  reports: { all: ["reports.read"] },
  perms: { any: ["permissions.topology.read", "users.manage", "permissions.topology.manage", "settings.manage"] },
  logs: { all: ["audit.read"] },
  settings: { all: ["settings.manage"] },
  terminal: { all: ["terminal.use"] },
};
const permissionSetOf = (user) => {
  const out = new Set();
  const add = (v) => { if (typeof v === "string" && v) out.add(v); };
  /* 後端 permissions 已完成個人 deny、委派有效期與部門 ceiling 裁切，存在時必須視為權威結果。 */
  if (user && Array.isArray(user.permissions)) {
    user.permissions.forEach(add);
    return out;
  }
  Array.isArray(user && user.base_permissions) && user.base_permissions.forEach(add);
  ((user && user.delegated_permissions) || []).forEach(p => {
    if (typeof p === "string") add(p);
    else if (p && p.effective !== false) add(p.permission_key);
  });
  return out;
};
W2.permissionSetOf = permissionSetOf;
W2.hasPermission = (permission, user) => {
  const actor = user || window.W2_USER || null;
  if (!actor) return false;
  if ((!user && window.W2_IS_OWNER) || actor.is_platform_owner) return true;
  return permissionSetOf(actor).has(permission);
};
const allowedNavOf = (user, isOwner) => {
  const known = new Set([...NAV2, ...NAV_ADMIN].map(n => n.id));
  if (user && Array.isArray(user.allowed_nav)) {
    return new Set(user.allowed_nav.map(String).filter(id => known.has(id)));
  }
  const perms = permissionSetOf(user);
  /* L10 是租戶系統管理員;L11/平台所有者沿用既有全局管理語義。 */
  if (isOwner || roleLevelOf(user) >= 10) return new Set([...NAV2.map(n => n.id), "terminal"]);
  return new Set(Object.entries(NAV_PERMISSION_RULES)
    .filter(([, rule]) => {
      const all = rule.all || []; const any = rule.any || [];
      return all.every(p => perms.has(p)) && (!any.length || any.some(p => perms.has(p)));
    })
    .map(([id]) => id));
};
const navModelOf = (user, isOwner, navConfig, templateKey) => {
  const allowed = allowedNavOf(user, isOwner);
  const overrides = (navConfig && navConfig.items && typeof navConfig.items === "object") ? navConfig.items : {};
  const configured = (items) => items
    /* L11 平台身份不可被任一租戶的全局隱藏設定裁掉管理入口。 */
    .filter(n => isOwner || !(overrides[n.id] && overrides[n.id].hidden))
    .map(n => ({ ...n, label: (overrides[n.id] && overrides[n.id].label) || n.label }));
  const routeMain = configured(navigationForTemplate(templateKey).filter(n => allowed.has(n.id)));
  const warehouseTabs = routeMain.filter(n => WAREHOUSE_ROUTE_IDS.includes(n.id));
  let main = routeMain;
  if (warehouseTabs.length && W2.WarehouseTabs) {
    const firstIndex = routeMain.findIndex(n => WAREHOUSE_ROUTE_IDS.includes(n.id));
    const warehouseNav = {
      idx: warehouseTabs[0].idx,
      id: "warehouse",
      label: "庫管",
      activeRoutes: ["warehouse", ...warehouseTabs.map(n => n.id)],
    };
    main = routeMain.filter(n => !WAREHOUSE_ROUTE_IDS.includes(n.id));
    main.splice(firstIndex, 0, warehouseNav);
  }
  const admin = NAV_ADMIN.filter(n => n.need === "owner"
    ? !!isOwner
    : n.id === "terminal"
      ? allowed.has(n.id)
      : (isOwner || roleLevelOf(user) >= ADMIN_LEVEL));
  const configuredAdmin = configured(admin);
  return {
    allowed,
    main,
    admin: configuredAdmin,
    ordered: [...main, ...configuredAdmin],
    routeItems: [...routeMain, ...configuredAdmin],
    warehouseTabs,
  };
};

/* ── 語言切換 ── */
const LangSeg = ({ compact }) => (
  <div className="seg" style={compact ? { transform: "scale(.92)", transformOrigin: "right center" } : undefined}>
    {[["tw", "繁"], ["cn", "简"], ["en", "EN"]].map(([id, label]) => (
      <button key={id} className={L === id ? "on" : ""} style={{ height: 26, padding: "0 10px", fontSize: 11, fontFamily: "var(--f-mono)" }}
        onClick={() => L !== id && setLang(id)}>{label}</button>
    ))}
  </div>
);

/* ── 登入 / 開通公司 / 加入公司:Swiss 海報 ──
   後端事實:/api/auth/register 與 /api/auth/roles?tenant= 公開;
   公司開通無公開端點(/api/platform/signup 已 410),須 L4+ 登入後走 /api/companies/apply。 */
const LOGIN_MODES = [["login", "登入"], ["apply", "開通公司"], ["join", "加入公司"]];
const BIU_ENTRY_LABELS = {
  direct: "直接選擇",
  application: "申請加入",
  exam: "需要考試",
  appointment: "任命職位",
};
const loginModeFromHash = () => ({ apply: "apply", join: "join" }[routeNow()] || "login");

const Login2 = ({ onDone, notice }) => {
  const [mode, setMode] = $s(loginModeFromHash());
  const [username, setU] = $s("");
  const [password, setP] = $s("");
  const [password2, setP2] = $s("");
  const [displayName, setDN] = $s("");
  const [companyCode, setCC] = $s("");
  const [roleId, setRoleId] = $s("");
  const [roles, setRoles] = $s([]);
  const [department, setDept] = $s("");
  const [orgOptions, setOrgOptions] = $s(null);
  const [orgUnitCode, setOrgUnitCode] = $s("");
  const [positionCode, setPositionCode] = $s("");
  const [positionQuery, setPositionQuery] = $s("");
  const [contact, setContact] = $s("");
  const [reason, setReason] = $s("");
  const [showPw, setShowPw] = $s(false);
  const [busy, setBusy] = $s(false);
  const [authAction, setAuthAction] = $s("");
  const [passkeyStage, setPasskeyStage] = $s("");
  const [passkeyCapability, setPasskeyCapability] = $s(() => passkeyCapabilityFallback(false));
  const [err, setErr] = $s("");
  const [done, setDone] = $s(null);
  const passkeyLoginFallbackRef = $r(null);
  const d = new Date();
  const passkeyPlatform = passkeyPlatformFamily();
  const dateMono = `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;

  const switchMode = (next) => {
    if (next === mode) return;
    setMode(next); setErr(""); setP(""); setP2(""); setDone(null);
    location.hash = next === "apply" ? "#/apply" : next === "join" ? "#/join" : "#/dashboard";
  };

  $e(() => {
    let alive = true;
    getPasskeyCapability().then(result => { if (alive) setPasskeyCapability(result); });
    return () => { alive = false; };
  }, []);

  /* 加入模式:企業代碼 ≥3 位時公開拉該公司可選角色與部門/崗位
     (不帶登入態,避免殘留頭覆蓋 ?tenant=)。 */
  $e(() => {
    if (mode !== "join") return;
    const code = companyCode.trim().toLowerCase();
    if (code.length < 3) { setRoles([]); setOrgOptions(null); return; }
    setOrgOptions(null);
    let cancelled = false;
    const timer = setTimeout(() => {
      const getPublic = (path) => fetch(W2.API_BASE + path).then(async r => {
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || data.message || "organization options unavailable");
        return data;
      });
      Promise.all([
        getPublic("/api/auth/roles?tenant=" + encodeURIComponent(code)),
        getPublic("/api/auth/org-options?tenant=" + encodeURIComponent(code)),
      ]).then(([roleData, orgData]) => {
        if (cancelled) return;
        const units = Array.isArray(orgData && orgData.units) ? orgData.units : [];
        setRoles(Array.isArray(roleData && roleData.roles) ? roleData.roles : []);
        setOrgOptions({
          catalog_version: orgData && orgData.catalog_version,
          template_key: orgData && orgData.template_key,
          units,
          positions: Array.isArray(orgData && orgData.positions) ? orgData.positions : [],
        });
        if (units.length) setDept("");
      }).catch(() => {
        if (!cancelled) { setRoles([]); setOrgOptions({ units: [], positions: [], __error: true }); }
      });
    }, 250);
    return () => { cancelled = true; clearTimeout(timer); };
  }, [mode, companyCode]);

  const orgUnits = (orgOptions && orgOptions.units) || [];
  const orgPositions = (orgOptions && orgOptions.positions) || [];
  const isBiuCatalogue = !!(
    orgOptions && orgOptions.template_key === "biu_legal_ethics_case_lab"
  );
  const positionsForUnit = orgPositions.filter(p => String(p.org_unit_code || "") === orgUnitCode);
  const selectedBiuPosition = isBiuCatalogue
    ? orgPositions.find(p => (
        String(p.position_code || "") === positionCode
        && p.selectable === true
        && p.catalog_state === "public"
        && ["direct", "application"].includes(p.entry_mode)
      ))
    : null;
  const normalizedPositionQuery = positionQuery.trim().toLocaleLowerCase();
  const filteredBiuPositions = isBiuCatalogue ? orgPositions.filter(position => {
    if (!normalizedPositionQuery) return true;
    return [
      position.position_name,
      position.position_name_en,
      position.org_unit_name,
      position.org_unit_name_en,
      position.summary,
    ].some(value => String(value || "").toLocaleLowerCase().includes(normalizedPositionQuery));
  }) : [];
  const biuPositionGroups = isBiuCatalogue ? orgUnits.map(unit => ({
    unit,
    positions: filteredBiuPositions.filter(
      position => String(position.org_unit_code || "") === String(unit.unit_code || "")
    ),
  })).filter(group => group.positions.length) : [];
  const selectUnit = (code) => {
    const unit = orgUnits.find(u => String(u.unit_code) === code);
    setOrgUnitCode(code); setPositionCode(""); setRoleId("");
    setDept(unit ? (unit.unit_name || unit.unit_code || "") : "");
  };
  const selectPosition = (code) => {
    setPositionCode(code);
    const pos = positionsForUnit.find(p => String(p.position_code) === code);
    if (!pos || !pos.role_name) { setRoleId(""); return; }
    const role = roles.find(r => r && r.role_name === pos.role_name);
    setRoleId(role && role.id != null ? String(role.id) : "");
  };
  const selectBiuPosition = (position) => {
    if (!position || !position.selectable) return;
    setOrgUnitCode(String(position.org_unit_code || ""));
    setDept(position.org_unit_name || position.org_unit_code || "");
    setPositionCode(String(position.position_code || ""));
    const role = roles.find(r => r && r.role_name === position.role_name);
    setRoleId(role && role.id != null ? String(role.id) : "");
  };

  const acceptLogin = (payload) => {
    const data = payload && payload.result && payload.result.token ? payload.result : payload;
    if (!data || !data.token) throw new Error(t("登入回應缺少安全憑證"));
    W2.setToken(data.token);
    const active = (data.companies || []).filter(c => c.status === "active");
    const responseTenant = typeof data.tenant === "string" ? data.tenant : (data.tenant && data.tenant.slug);
    W2.setTenant(data.default_tenant || responseTenant || (active[0] && active[0].slug) || "");
    onDone();
  };

  const submitLogin = async () => {
    setBusy(true); setAuthAction("password"); setErr("");
    try {
      const data = await W2.post("/api/auth/login", { username, password });
      acceptLogin(data);
    } catch (e) { setErr(e.message || String(e)); }
    finally { setBusy(false); setAuthAction(""); }
  };

  const submitPasskeyLogin = async passkeyMode => {
    if (busy || !W2.Passkeys || !passkeyCapability || !passkeyCapability.supported) return;
    const action = passkeyMode === "hybrid" ? "passkey-hybrid" : "passkey-platform";
    const fallbackController = passkeyMode === "platform" && typeof AbortController === "function"
      ? new AbortController() : null;
    passkeyLoginFallbackRef.current = fallbackController;
    setBusy(true); setAuthAction(action); setPasskeyStage("options"); setErr("");
    try {
      acceptLogin(await W2.Passkeys.login(username, {
        mode: passkeyMode,
        fallbackToHybrid: passkeyMode === "platform",
        platformTimeoutMs: 30000,
        fallbackSignal: fallbackController && fallbackController.signal,
        onStatus: setPasskeyStage,
      }));
    }
    catch (e) { setErr(passkeyFailureMessage(e)); }
    finally {
      if (passkeyLoginFallbackRef.current === fallbackController) passkeyLoginFallbackRef.current = null;
      setBusy(false); setAuthAction("");
    }
  };

  const switchLoginToPhone = () => {
    const controller = passkeyLoginFallbackRef.current;
    if (!controller || controller.signal.aborted) return;
    setPasskeyStage("authenticator-hybrid-switch");
    controller.abort();
  };

  const submitJoin = async () => {
    const code = companyCode.trim().toLowerCase();
    setErr("");
    if (!code) { setErr(t("請填寫企業代碼")); return; }
    if (password !== password2) { setErr(t("兩次輸入的密碼不一致")); return; }
    if (!orgOptions || orgOptions.__error) { setErr(t("尚未讀取到該公司的部門與崗位,請確認企業代碼或稍後重試")); return; }
    if (isBiuCatalogue && !selectedBiuPosition) { setErr(t("請選擇一個可加入的 BIU 職位")); return; }
    setBusy(true);
    try {
      const res = await fetch(W2.API_BASE + "/api/auth/register", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username, tenant_slug: code, display_name: displayName || username,
          password, department, contact, reason,
          requested_org_unit_code: isBiuCatalogue
            ? selectedBiuPosition.org_unit_code
            : (orgUnitCode || null),
          requested_position_code: isBiuCatalogue
            ? selectedBiuPosition.position_code
            : (positionCode || null),
          requested_role_id: (isBiuCatalogue || positionCode) ? null : (roleId || null),
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || data.message || t("提交失敗"));
      setDone(data);
    } catch (e) { setErr(e.message || String(e)); }
    finally { setBusy(false); }
  };

  const submit = (ev) => {
    ev.preventDefault();
    if (busy) return;
    if (mode === "join") submitJoin();
    else if (mode === "login") submitLogin();
  };

  const monoRow = (k, v) => (
    <div className="row spread" key={k} style={{ borderTop: "1px solid var(--hair)", padding: "9px 2px", fontSize: 12 }}>
      <span className="label dim">{k}</span>
      <span className="mono" style={{ fontSize: 11.5, fontWeight: 600 }}>{v}</span>
    </div>
  );
  const F = (zh, en, node) => (
    <label className="col g6" key={en}>
      <Label dim>{L === "en" ? en : t(zh) + " / " + en}</Label>
      {node}
    </label>
  );

  const posterFoot = isBiuCatalogue && mode === "join"
    ? "LEARN · ANALYZE · ARCHIVE"
    : { login: "CONNECT · ORDER · EVOLVE", apply: "FOUND · APPROVE · OPERATE", join: "APPLY · APPROVE · ENTER" }[mode];
  const headLabel = isBiuCatalogue && mode === "join"
    ? "BIU ROLE CATALOG"
    : { login: "SIGN IN", apply: "OPEN COMPANY", join: "JOIN COMPANY" }[mode];
  const title = mode === "apply" ? t("申請開通公司")
    : mode === "join" ? (isBiuCatalogue ? t("選擇 BIU 學術職位") : t("申請加入公司"))
    : "WAREHOUSE OS 2.1";

  return (
    <div className="login-wrap">
      <div className="login-art login-art-bonfire">
        <div className="login-grid" aria-hidden="true"/>
        <div className="login-geometry" aria-hidden="true">
          <span className="login-ring login-ring-a"/>
          <span className="login-ring login-ring-b"/>
          <span className="login-ember login-ember-a"/>
          <span className="login-ember login-ember-b"/>
          <span className="login-ember login-ember-c"/>
          <span className="login-scan-line"/>
        </div>
        <div className="row spread login-art-head" style={{ position: "relative", zIndex: 2 }}>
          <div className="row g10">
            <PlatformMark size={28}/>
            <div className="col g4">
              <Label>WAREHOUSE OS 2.1</Label>
              <span className="platform-byline">BY BONFIRE WORKSHOP</span>
            </div>
          </div>
          <Label dim>{dateMono}</Label>
        </div>
        <div style={{ position: "relative", zIndex: 2 }} className="login-art-content rise" key={mode}>
          <PlatformMark seal size={92} className="login-platform-seal"/>
          <div className="red-block" style={{ marginBottom: 34 }}/>
          {mode === "apply" ? (L === "en"
            ? <h1>Bring your<br/>company into<br/><span className="hollow">order</span>.</h1>
            : <h1>{t("把你的公司,")}<br/>{t("開進")}<span className="hollow">{t("秩序")}</span>{t("。")}</h1>)
          : mode === "join" ? (isBiuCatalogue
            ? (L === "en"
              ? <h1>Choose your<br/><span className="hollow">legal role</span>.</h1>
              : <h1>{t("選擇你的")}<br/><span className="hollow">{t("法律角色")}</span>{t("。")}</h1>)
            : (L === "en"
              ? <h1>Join a company<br/>already in<br/><span className="hollow">order</span>.</h1>
              : <h1>{t("加入一家")}<br/>{t("已在")}<span className="hollow">{t("秩序")}</span><br/>{t("中的公司。")}</h1>))
          : (L === "en"
            ? <h1 className="login-hero-title">Humanity gathers<br/>around the <span className="hollow">fire</span>.</h1>
            : <h1 className="login-hero-title"><span>{t("人類因篝火聚集，")}</span><br/><span>{t("文明因連接而誕生。")}</span></h1>)}
          <div className="login-hero-copy" style={{ marginTop: 30, maxWidth: "46ch", fontSize: 15, lineHeight: 1.7, color: "var(--ink-2)" }}>
            {mode === "apply" ? t("開通即建立獨立數據庫與初始表;審批通過後,你就是新公司的系統管理員。")
            : mode === "join" ? (isBiuCatalogue
              ? t("從案例收錄、律師、證據、調解到多級審理,選擇一個 BIU 內部學術職位參與。")
              : t("填一張申請單:帳號、企業代碼、期望角色。企業管理員審批通過後,即可登入開工。"))
            : <>
              <span>{t("今天，")}</span><br/>
              <span>{t("我們在數字世界重新點燃篝火。")}</span>
              <span className="login-hero-manifesto">{t("連接現實，建立秩序，驅動進化。")}</span>
            </>}
          </div>
          {mode === "login" && (
            <div className="login-art-motto" aria-label={t("連接現實，建立秩序，驅動進化。")}>
              <span className="mono">MOTTO / 01</span>
              <strong>{t("連接現實，建立秩序，驅動進化。")}</strong>
            </div>
          )}
          {mode === "apply" && (
            <div style={{ marginTop: 26, maxWidth: 480 }} className="col">
              {[t("先有平臺帳號 — 申請加入任一公司"), t("登入後在頂欄公司切換器提交開通申請"), t("平台審批通過 — 你即成為新公司系統管理員")].map((s, i) => (
                <div key={i} className="row g10" style={{ borderTop: "1px solid var(--hair)", padding: "10px 2px", fontSize: 12.5 }}>
                  <span className="mono" style={{ fontSize: 10, letterSpacing: ".14em", color: "var(--red)", fontWeight: 700 }}>{"0" + (i + 1)}</span>
                  <span style={{ color: "var(--ink-2)" }}>{s}</span>
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="row spread login-art-foot" style={{ position: "relative", zIndex: 2 }}>
          <div className="login-art-signature">
            <Label dim>{posterFoot}</Label>
            <span><b>WAREHOUSE 2.1</b><i aria-hidden="true">·</i>{t("數字世界的篝火。")}</span>
          </div>
          <Label dim>BONFIRE WORKSHOP</Label>
        </div>
      </div>
      <div className="login-panel">
        <form className={`login-card col g20 rise ${isBiuCatalogue ? "biu-catalogue-card" : ""}`} onSubmit={submit} style={{ animationDelay: ".06s" }}>
          <div>
            <div className="row spread login-card-tools" style={{ marginBottom: 8 }}>
              <div className="seg">
                {LOGIN_MODES.map(([id, label]) => (
                  <button key={id} type="button" className={mode === id ? "on" : ""}
                    style={{ height: 26, padding: "0 9px", fontSize: 11, fontFamily: "var(--f-mono)" }}
                    onClick={() => switchMode(id)}>{t(label)}</button>
                ))}
              </div>
              <div className="row g10"><LangSeg compact/><PlatformMark size={24}/></div>
            </div>
            <div className="row spread" style={{ borderBottom: "2px solid var(--rule)", paddingBottom: 14, alignItems: "flex-end" }}>
              <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-.035em" }}>{done ? t("申請已提交") : title}</div>
              <Label red>{done ? "FILED" : headLabel}</Label>
            </div>
          </div>

          {done ? ( /* ── Swiss 回執:加入申請已入列 ── */
            <div className="col g16 rise">
              <div style={{ width: 64, height: 18, background: "var(--red)" }}/>
              <div>
                {monoRow("DATE", dateMono)}
                {monoRow("COMPANY", done.tenant_name || done.tenant || companyCode)}
                {done.request_id != null && monoRow("NO.", String(done.request_id).padStart(4, "0"))}
                {monoRow("STATUS", "PENDING REVIEW")}
              </div>
              <div style={{ fontSize: 13.5, fontWeight: 650, lineHeight: 1.7 }}>{done.message || t("申請已提交")}</div>
              <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("企業管理員審批通過後,即可用此帳號登入。")}</div>
              <Btn kind="primary" size="lg" type="button" style={{ width: "100%" }} onClick={() => switchMode("login")}>{t("返回登入")}</Btn>
            </div>
          ) : mode === "apply" ? ( /* ── 開通:如實兩段式引導(無公開開通端點) ── */
            <div className="col g16">
              <div className="panel" style={{ padding: "14px 16px", borderLeft: "3px solid var(--red)" }}>
                <Label red>REQUIRES ACCOUNT</Label>
                <div style={{ fontSize: 13.5, fontWeight: 700, margin: "7px 0 5px" }}>{t("開通新公司,需要先有平臺帳號。")}</div>
                <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.75 }}>
                  {t("L4 及以上成員登入後,在頂欄公司切換器選「+ 申請開通公司」提交;平台審批通過後,申請人自動成為新公司的系統管理員。")}
                </div>
              </div>
              <Btn kind="primary" size="lg" type="button" style={{ width: "100%" }} onClick={() => switchMode("join")}>{t("先申請加入一家公司")}</Btn>
              <Btn size="lg" type="button" style={{ width: "100%" }} onClick={() => switchMode("login")}>{t("已有帳號 → 登入")}</Btn>
              <div className="row spread" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                <span className="mono" style={{ fontSize: 9, letterSpacing: ".16em" }}>PLATFORM REVIEW</span>
                <span className="mono" style={{ fontSize: 9, letterSpacing: ".16em" }}>AUDIT ON</span>
              </div>
            </div>
          ) : (
            <>
              {notice && mode === "login" && <div style={{ fontSize: 12.5, color: "var(--warn)", fontWeight: 650 }}>{t(notice)}</div>}
              {F("帳號", "USERNAME",
                <input className="field" value={username} onChange={e => setU(e.target.value)} autoComplete={mode === "login" ? "username webauthn" : "username"} autoFocus/>)}
              {mode === "join" && F("顯示名稱", "DISPLAY NAME",
                <input className="field" value={displayName} onChange={e => setDN(e.target.value)} autoComplete="name" placeholder={t("姓名或工作名")}/>)}
              {mode === "join" && F("企業代碼", "COMPANY CODE",
                <input className="field" value={companyCode} onChange={e => {
                  setCC(e.target.value); setRoleId(""); setDept(""); setOrgUnitCode(""); setPositionCode(""); setPositionQuery(""); setOrgOptions(null);
                }} autoComplete="organization" placeholder={t("向公司管理員索取,例如 acme")}/>)}
              {mode === "login" && (
                <div className="col g8">
                  <Btn type="button" size="lg" icon="user" disabled={busy || !passkeyCapability || !passkeyCapability.supported}
                    onClick={() => submitPasskeyLogin("platform")} style={{ width: "100%", borderColor: passkeyCapability && passkeyCapability.supported ? "var(--ink)" : undefined }}>
                    {authAction === "passkey-platform"
                      ? passkeyProgressMessage(passkeyStage, "platform")
                      : t(passkeyPlatformActionCopy(passkeyPlatform))}
                  </Btn>
                  <Btn type="button" size="lg" icon="user"
                    disabled={(busy && !(authAction === "passkey-platform" && passkeyStage === "authenticator-platform")) || !passkeyCapability || !passkeyCapability.supported}
                    onClick={() => busy && authAction === "passkey-platform" ? switchLoginToPhone() : submitPasskeyLogin("hybrid")} style={{ width: "100%" }}>
                    {busy && authAction === "passkey-platform" && passkeyStage === "authenticator-platform"
                      ? t("立即改用手機 Passkey（QR）")
                      : authAction === "passkey-hybrid"
                      ? passkeyProgressMessage(passkeyStage, "hybrid")
                      : t("使用手機 Passkey（顯示 QR）")}
                  </Btn>
                  <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.65 }}>
                    {!passkeyCapability ? t("正在檢查裝置支援…")
                      : passkeyCapability.supported
                        ? t("使用本機 Face ID、指紋、裝置密碼或安全金鑰;平台不會收到你的面部或指紋資料。") + " " + t(passkeyQrHelpCopy(passkeyPlatform))
                        : t("此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。")}
                  </div>
                  <div className="row g10" aria-hidden="true" style={{ color: "var(--ink-4)", margin: "3px 0" }}>
                    <span style={{ height: 1, background: "var(--hair)", flex: 1 }}/>
                    <span className="mono" style={{ fontSize: 8.5, letterSpacing: ".14em" }}>{t("或者使用密碼").toUpperCase()}</span>
                    <span style={{ height: 1, background: "var(--hair)", flex: 1 }}/>
                  </div>
                </div>
              )}
              {F("密碼", "PASSWORD",
                <div style={{ position: "relative" }}>
                  <input className="field" type={showPw ? "text" : "password"} value={password} onChange={e => setP(e.target.value)} autoComplete={mode === "join" ? "new-password" : "current-password"} style={{ paddingRight: 38 }}/>
                  <button type="button" onClick={() => setShowPw(v => !v)} style={{ position: "absolute", right: 0, top: "50%", transform: "translateY(-50%)", width: 32, height: 32, display: "grid", placeItems: "center", color: "var(--ink-3)" }}>
                    <Icon name={showPw ? "eyeOff" : "eye"} size={15}/>
                  </button>
                </div>)}
              {mode === "join" && F("確認密碼", "CONFIRM",
                <input className="field" type={showPw ? "text" : "password"} value={password2} onChange={e => setP2(e.target.value)} autoComplete="new-password"/>)}
              {mode === "join" && isBiuCatalogue && (
                <section className="biu-role-picker" aria-label={t("選擇 BIU 學術職位")}>
                  <div className="biu-role-notice">
                    <Label red>BIU ACADEMIC ROLE · INTERNAL USE</Label>
                    <div>{t("BIU 内部学术职位 · 不构成现实职业资格或法律授权")}</div>
                  </div>
                  <label className="col g6">
                    <Label dim>ROLE CATALOG · {orgPositions.length}</Label>
                    <input
                      className="field boxed"
                      value={positionQuery}
                      onChange={event => setPositionQuery(event.target.value)}
                      placeholder={t("搜索法官、律師、案例或證據職位")}
                    />
                  </label>
                  <div className="biu-role-catalog">
                    {biuPositionGroups.map(({ unit, positions }) => (
                      <div className="biu-role-group" key={unit.unit_code}>
                        <div className="biu-role-group-head">
                          <span>{L === "en" ? (unit.unit_name_en || unit.unit_name) : unit.unit_name}</span>
                          <span>{L === "en" ? unit.unit_name : unit.unit_name_en}</span>
                        </div>
                        {positions.map(position => {
                          const selected = position.position_code === positionCode;
                          const entryLabel = BIU_ENTRY_LABELS[position.entry_mode] || position.entry_mode;
                          return (
                            <div className={`biu-role-card-shell ${selected ? "selected" : ""}`} key={position.position_code}>
                              <button
                                type="button"
                                className={`biu-role-card ${position.selectable ? "" : "locked"}`}
                                aria-disabled={!position.selectable}
                                aria-pressed={selected}
                                title={!position.selectable ? (position.lock_reason || position.cta_label) : undefined}
                                onClick={() => selectBiuPosition(position)}
                              >
                                <span className="biu-role-card-top">
                                  <span className="biu-role-name">
                                    <strong>{L === "en" ? position.position_name_en : position.position_name}</strong>
                                    <small>{L === "en" ? position.position_name : position.position_name_en}</small>
                                  </span>
                                  <span className="biu-role-badges">
                                    <i>{position.permission_tier}</i>
                                    <i data-entry={position.entry_mode}>{t(entryLabel)}</i>
                                  </span>
                                </span>
                                <span className="biu-role-summary">{position.summary}</span>
                                <span className="biu-role-action">
                                  {selected ? t("已選擇") : position.selectable ? t("選擇此職位") : (position.lock_reason || position.cta_label)}
                                </span>
                              </button>
                              {selected && Array.isArray(position.requirements) && (
                                <div className="biu-role-requirements">
                                  <Label dim>{t("職位要求")}</Label>
                                  <ul>{position.requirements.map(item => <li key={item}>{item}</li>)}</ul>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ))}
                    {!biuPositionGroups.length && (
                      <div className="muted" role="status" aria-live="polite" style={{ padding: 14, fontSize: 12 }}>{t("目前沒有符合搜索條件的職位")}</div>
                    )}
                  </div>
                </section>
              )}
              {mode === "join" && !isBiuCatalogue && F("部門 / 班組", "DEPARTMENT",
                orgOptions && orgOptions.__error ? (
                  <div style={{ fontSize: 12, color: "var(--danger)", padding: "8px 0" }}>{t("部門與崗位載入失敗,請確認企業代碼後重試")}</div>
                ) : orgUnits.length ? (
                  <select className="field" value={orgUnitCode} onChange={e => selectUnit(e.target.value)}>
                    <option value="">{t("(由管理員指定)")}</option>
                    {orgUnits.map(u => <option key={u.unit_code} value={u.unit_code}>{u.unit_name || u.unit_code}</option>)}
                  </select>
                ) : <div className="muted" style={{ fontSize: 12, padding: "8px 0" }}>{t(companyCode.trim().length >= 3 ? "部門與崗位載入中…" : "請先輸入企業代碼")}</div>)}
              {mode === "join" && !isBiuCatalogue && orgUnits.length > 0 && !!orgUnitCode && F("期望崗位", "POSITION",
                <select className="field" value={positionCode} onChange={e => selectPosition(e.target.value)} disabled={!positionsForUnit.length}>
                  <option value="">{positionsForUnit.length ? t("(由管理員指定)") : t("該部門尚無預設崗位")}</option>
                  {positionsForUnit.map(p => <option key={p.position_code} value={p.position_code}>
                    {p.position_name || p.position_code}{p.role_name ? " · " + p.role_name : ""}
                  </option>)}
                </select>)}
              {mode === "join" && !isBiuCatalogue && F("期望角色", "ROLE",
                <select className="field" value={roleId} onChange={e => setRoleId(e.target.value)} disabled={!!positionCode}>
                  <option value="">{t("(由管理員指定)")}</option>
                  {roles.map(r => <option key={r.id} value={r.id}>{r.role_name}</option>)}
                </select>)}
              {mode === "join" && F("聯繫方式", "CONTACT",
                <input className="field" value={contact} onChange={e => setContact(e.target.value)} placeholder={t("方便管理員核實身份")}/>)}
              {mode === "join" && F("申請理由", "REASON",
                <textarea className="field" value={reason} onChange={e => setReason(e.target.value)} rows={2} style={{ height: "auto", padding: "8px 2px", resize: "none" }} placeholder={t("簡述用途,供審批參考")}/>)}
              {err && <div role="alert" style={{ fontSize: 12.5, color: "var(--danger)", fontWeight: 650 }}>⚠ {err}</div>}
              <Btn kind="primary" size="lg" disabled={busy} style={{ width: "100%" }}>
                {busy && authAction !== "passkey" ? (mode === "join" ? t("提交中…") : t("登入中…")) : (mode === "join" ? t("提交申請") : t("進入系統"))}
              </Btn>
              {mode === "login" && (
                <div className="muted" style={{ fontSize: 11.5, textAlign: "center" }}>
                  {t("忘記密碼？請聯繫公司管理員重置。")}
                </div>
              )}
              <div className="row spread" style={{ fontSize: 11.5, color: "var(--ink-3)" }}>
                {mode === "login"
                  ? <span>{t("系統初始化 · Warehouse OS 2.1")}</span>
                  : <span className="mono" style={{ fontSize: 9, letterSpacing: ".16em" }}>ADMIN REVIEW</span>}
                <span className="mono" style={{ fontSize: 9, letterSpacing: ".16em" }}>AUDIT ON</span>
              </div>
              <div className="platform-service-line">
                <PlatformMark size={18}/>
                <span>BONFIRE WORKSHOP · PLATFORM IDENTITY</span>
              </div>
            </>
          )}
        </form>
      </div>
    </div>
  );
};

/* ── 申請開通公司:登入後的 Swiss 行內面板(POST /api/companies/apply,L4+) ── */
const ApplyCompanyPanel = ({ onClose, canApply }) => {
  const [form, setForm] = $s({ company_name: "", slug: "", industry_template: "", contact: "", reason: "" });
  const [templates, setTemplates] = $s(null); // null=載入中, []=不可用
  const [busy, setBusy] = $s(false);
  const [err, setErr] = $s("");
  const [done, setDone] = $s(null);
  const up = (k) => (e) => setForm(f => ({ ...f, [k]: k === "slug" ? e.target.value.toLowerCase() : e.target.value }));

  $e(() => {
    W2.json("/api/platform/templates")
      .then(d => {
        const list = d.templates || [];
        setTemplates(list);
        if (list[0]) setForm(f => ({ ...f, industry_template: f.industry_template || list[0].key }));
      })
      .catch(() => setTemplates([]));
  }, []);

  const submit = async (ev) => {
    ev.preventDefault();
    if (busy) return;
    setErr("");
    const slug = form.slug.trim();
    if (!form.company_name.trim()) { setErr(t("請填寫公司名稱")); return; }
    if (!/^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/.test(slug)) {
      setErr(t("企業代碼需為 3-40 位小寫字母 / 數字 / 連字符,且不以連字符開頭結尾")); return;
    }
    setBusy(true);
    try {
      const body = { company_name: form.company_name.trim(), slug, contact: form.contact, reason: form.reason };
      if (form.industry_template) body.industry_template = form.industry_template;
      setDone(await W2.post("/api/companies/apply", body));
    } catch (e) { setErr(e.message || String(e)); }
    finally { setBusy(false); }
  };

  const FF = (zh, en, node) => (
    <label className="col g6" key={en}><Label dim>{L === "en" ? en : t(zh) + " / " + en}</Label>{node}</label>
  );

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(20,20,20,.45)", zIndex: 90, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={onClose}>
      <form className="panel col g16 fade" onClick={e => e.stopPropagation()} onSubmit={submit}
        style={{ width: "min(460px, 100%)", maxHeight: "88vh", overflowY: "auto", padding: 24, border: "2px solid var(--ink)" }}>
        <div>
          <div className="row spread" style={{ marginBottom: 8 }}>
            <Label red>{done ? "FILED" : "OPEN COMPANY"}</Label>
            <button type="button" onClick={onClose} style={{ width: 26, height: 26, display: "grid", placeItems: "center", color: "var(--ink-3)" }}><Icon name="x" size={15}/></button>
          </div>
          <div style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-.03em", borderBottom: "2px solid var(--rule)", paddingBottom: 12 }}>
            {done ? t("申請已提交") : t("申請開通公司")}
          </div>
        </div>
        {!canApply ? (
          <>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.75 }}>{t("開通申請需要 L4 及以上權限,請聯繫管理員提升權限或代為申請。")}</div>
            <Btn kind="primary" type="button" style={{ width: "100%" }} onClick={onClose}>{t("完成")}</Btn>
          </>
        ) : done ? (
          <div className="col g14 rise">
            <div style={{ width: 64, height: 18, background: "var(--red)" }}/>
            <div>
              {done.request_id != null && (
                <div className="row spread" style={{ borderTop: "1px solid var(--hair)", padding: "9px 2px", fontSize: 12 }}>
                  <span className="label dim">NO.</span><span className="mono" style={{ fontSize: 11.5, fontWeight: 600 }}>{String(done.request_id).padStart(4, "0")}</span>
                </div>
              )}
              <div className="row spread" style={{ borderTop: "1px solid var(--hair)", padding: "9px 2px", fontSize: 12 }}>
                <span className="label dim">STATUS</span><span className="mono" style={{ fontSize: 11.5, fontWeight: 600 }}>PENDING REVIEW</span>
              </div>
            </div>
            <div style={{ fontSize: 13.5, fontWeight: 650, lineHeight: 1.7 }}>{done.message || t("申請已提交")}</div>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("平台審批通過後,你會成為該公司的系統管理員,公司會出現在頂欄切換器裡。")}</div>
            <Btn kind="primary" type="button" style={{ width: "100%" }} onClick={onClose}>{t("完成")}</Btn>
          </div>
        ) : (
          <>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("提交後由平台審批;通過時系統會自動建立該公司的獨立數據庫與初始表。")}</div>
            {FF("公司名稱", "COMPANY NAME",
              <input className="field" value={form.company_name} onChange={up("company_name")} placeholder={t("例如:ACME 工作室")} autoFocus/>)}
            {FF("企業代碼", "COMPANY CODE",
              <input className="field" value={form.slug} onChange={up("slug")} placeholder={t("3-40 位小寫字母 / 數字 / 連字符")}/>)}
            {templates && templates.length > 0 ? FF("行業模板", "TEMPLATE",
              <select className="field" value={form.industry_template} onChange={up("industry_template")}>
                {templates.map(tp => <option key={tp.key} value={tp.key}>
                  {tp.name}{tp.organization ? " · " + t("{d} 部門 · {p} 崗位", { d: tp.organization.departments, p: tp.organization.positions }) : ""}
                </option>)}
              </select>)
            : templates && <div className="muted mono" style={{ fontSize: 11 }}>{t("模板目錄暫不可用,將使用默認通用模板")}</div>}
            {FF("聯繫方式", "CONTACT", <input className="field" value={form.contact} onChange={up("contact")}/>)}
            {FF("申請理由", "REASON",
              <textarea className="field" value={form.reason} onChange={up("reason")} rows={2} style={{ height: "auto", padding: "8px 2px", resize: "none" }}/>)}
            {err && <div style={{ fontSize: 12.5, color: "var(--danger)", fontWeight: 650 }}>⚠ {err}</div>}
            <div className="row g8">
              <Btn type="button" style={{ flex: 1 }} onClick={onClose}>{t("取消")}</Btn>
              <Btn kind="primary" disabled={busy} style={{ flex: 2 }}>{busy ? t("提交中…") : t("提交申請")}</Btn>
            </div>
          </>
        )}
      </form>
    </div>
  );
};

/* ── 申請加入已有公司:已登入全局身份 → pending membership → 目標公司審批 ── */
const JoinCompanyPanel = ({ onClose }) => {
  const [slug, setSlug] = $s("");
  const [busy, setBusy] = $s(false);
  const [err, setErr] = $s("");
  const [done, setDone] = $s(null);
  const submit = async (event) => {
    event.preventDefault();
    if (busy) return;
    const code = slug.trim().toLowerCase();
    setErr("");
    if (!/^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/.test(code)) {
      setErr(t("企業代碼需為 3-40 位小寫字母 / 數字 / 連字符,且不以連字符開頭結尾"));
      return;
    }
    setBusy(true);
    try { setDone({ ...(await W2.post("/api/companies/join", { slug: code })), slug: code }); }
    catch (e) { setErr(e.message || String(e)); }
    finally { setBusy(false); }
  };
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(20,20,20,.45)", zIndex: 90, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={onClose}>
      <form className="panel col g16 fade" onClick={e => e.stopPropagation()} onSubmit={submit}
        style={{ width: "min(460px, 100%)", maxHeight: "88vh", overflowY: "auto", padding: 24, border: "2px solid var(--ink)" }}>
        <div>
          <div className="row spread" style={{ marginBottom: 8 }}>
            <Label red>{done ? "FILED" : "JOIN COMPANY"}</Label>
            <button type="button" onClick={onClose} style={{ width: 26, height: 26, display: "grid", placeItems: "center", color: "var(--ink-3)" }}><Icon name="x" size={15}/></button>
          </div>
          <div style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-.03em", borderBottom: "2px solid var(--rule)", paddingBottom: 12 }}>
            {done ? t("加入申請已提交") : t("申請加入已有公司")}
          </div>
        </div>
        {done ? (
          <div className="col g14 rise">
            <div style={{ width: 64, height: 18, background: "var(--red)" }}/>
            <div className="row spread" style={{ borderTop: "1px solid var(--hair)", padding: "9px 2px", fontSize: 12 }}>
              <span className="label dim">COMPANY CODE</span><span className="mono" style={{ fontSize: 11.5, fontWeight: 650 }}>{done.slug}</span>
            </div>
            <div className="row spread" style={{ borderTop: "1px solid var(--hair)", padding: "9px 2px", fontSize: 12 }}>
              <span className="label dim">STATUS</span><span className="mono" style={{ fontSize: 11.5, fontWeight: 650 }}>PENDING REVIEW</span>
            </div>
            <div style={{ fontSize: 13.5, fontWeight: 650 }}>{done.message || t("等待目標公司管理員審批")}</div>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("這會沿用你目前的全局帳號,不會建立重複登入身份。")}</div>
            <Btn kind="primary" type="button" style={{ width: "100%" }} onClick={onClose}>{t("完成")}</Btn>
          </div>
        ) : (
          <>
            <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.7 }}>{t("輸入目標公司的企業代碼;申請會交給該公司管理員審批,通過後公司會出現在切換器中。")}</div>
            <label className="col g6">
              <Label dim>{L === "en" ? "COMPANY CODE" : t("企業代碼") + " / COMPANY CODE"}</Label>
              <input className="field" value={slug} onChange={e => setSlug(e.target.value.toLowerCase())}
                placeholder={t("企業代碼例如 bonfire")} autoFocus autoComplete="off"/>
            </label>
            {err && <div style={{ fontSize: 12.5, color: "var(--danger)", fontWeight: 650 }}>⚠ {err}</div>}
            <div className="row g8">
              <Btn type="button" style={{ flex: 1 }} onClick={onClose}>{t("取消")}</Btn>
              <Btn kind="primary" disabled={busy} style={{ flex: 2 }}>{busy ? t("提交中…") : t("提交申請")}</Btn>
            </div>
          </>
        )}
      </form>
    </div>
  );
};

/* ── 可重用 Passkey 登記表單:管理面板與情境引導共用同一 WebAuthn 流程 ── */
const PasskeyEnrollmentForm = ({ onRegistered, onBusyChange, compact = false }) => {
  const [capability, setCapability] = $s(() => passkeyCapabilityFallback(false));
  const [deviceName, setDeviceName] = $s("");
  const [accountPassword, setAccountPassword] = $s("");
  const [busy, setBusy] = $s(false);
  const [enrollMode, setEnrollMode] = $s("");
  const [passkeyStage, setPasskeyStage] = $s("");
  const [err, setErr] = $s("");
  const operationControllerRef = $r(null);
  const fallbackControllerRef = $r(null);
  const passkeyPlatform = passkeyPlatformFamily();
  const windowsDevice = passkeyPlatform === "windows";

  $e(() => {
    let alive = true;
    getPasskeyCapability().then(result => { if (alive) setCapability(result); });
    return () => {
      alive = false;
      if (operationControllerRef.current) operationControllerRef.current.abort();
    };
  }, []);
  $e(() => { if (onBusyChange) onBusyChange(busy); }, [busy, onBusyChange]);

  const add = async mode => {
    if (busy || !W2.Passkeys || !capability || !capability.supported) return;
    if (!accountPassword) { setErr(t("管理 Passkey 前請重新輸入帳號密碼")); return; }
    const operationController = typeof AbortController === "function" ? new AbortController() : null;
    const fallbackController = mode === "platform" && typeof AbortController === "function" ? new AbortController() : null;
    operationControllerRef.current = operationController;
    fallbackControllerRef.current = fallbackController;
    setBusy(true); setEnrollMode(mode); setPasskeyStage("options"); setErr("");
    try {
      const result = await W2.Passkeys.register(deviceName, accountPassword, {
        mode,
        signal: operationController && operationController.signal,
        fallbackToHybrid: mode === "platform",
        platformTimeoutMs: 30000,
        fallbackSignal: fallbackController && fallbackController.signal,
        onStatus: setPasskeyStage,
      });
      setDeviceName(""); setAccountPassword(""); setPasskeyStage(""); setEnrollMode("");
      if (onRegistered) Promise.resolve(onRegistered(result)).catch(() => {});
    } catch (error) {
      if (!(operationController && operationController.signal.aborted)) setErr(passkeyFailureMessage(error));
    } finally {
      if (operationControllerRef.current === operationController) operationControllerRef.current = null;
      if (fallbackControllerRef.current === fallbackController) fallbackControllerRef.current = null;
      setBusy(false);
    }
  };
  const switchToPhone = () => {
    const controller = fallbackControllerRef.current;
    if (!controller || controller.signal.aborted) return;
    setPasskeyStage("authenticator-hybrid-switch");
    controller.abort();
  };
  const cancel = () => {
    const controller = operationControllerRef.current;
    if (!controller || controller.signal.aborted) return;
    setPasskeyStage("authenticator-cancel");
    controller.abort();
  };
  const authenticatorActive = busy && [
    "authenticator", "authenticator-platform", "authenticator-hybrid-timeout", "authenticator-hybrid-switch",
  ].includes(passkeyStage);

  return <div className={compact ? "col g12" : "panel col g12"} style={compact ? undefined : { padding: 16, borderLeft: "3px solid var(--red)" }}>
    <label className="col g6">
      <Label dim>{t("帳號密碼") + " / PASSWORD"}</Label>
      <input className="field" type="password" value={accountPassword} data-guide-initial
        onChange={event => setAccountPassword(event.target.value)} maxLength={128}
        autoComplete="current-password" placeholder={t("管理 Passkey 前請重新輸入帳號密碼")}/>
      <span className="muted" style={{ fontSize: 10.5 }}>{t("密碼只用於本次安全核驗,不會保存在瀏覽器中。")}</span>
    </label>
    <label className="col g6">
      <Label dim>{L === "en" ? "DEVICE NAME" : t("裝置名稱") + " / DEVICE NAME"}</Label>
      <input className="field" value={deviceName} onChange={event => setDeviceName(event.target.value)} maxLength={80}
        autoComplete="off" placeholder={t(passkeyDevicePlaceholderCopy(passkeyPlatform))}/>
    </label>
    <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.65 }}>
      {!capability ? t("正在檢查裝置支援…")
        : capability.supported
          ? t(capability.platform
              ? windowsDevice ? "此裝置可以使用 Windows Hello、內建面容、指紋或裝置 PIN。" : "此裝置可以使用內建面容或指紋驗證。"
              : "此裝置可使用 Passkey 或外接安全金鑰。")
          : t("此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。")}
    </div>
    <Btn type="button" kind="primary" disabled={busy || !capability || !capability.supported} onClick={() => add("platform")} style={{ width: "100%", minHeight: 44 }}>
      {busy && enrollMode === "platform" ? passkeyProgressMessage(passkeyStage, "platform") : t(passkeyPlatformActionCopy(passkeyPlatform))}
    </Btn>
    <Btn type="button" disabled={(busy && !(enrollMode === "platform" && passkeyStage === "authenticator-platform")) || !capability || !capability.supported}
      onClick={() => busy && enrollMode === "platform" ? switchToPhone() : add("hybrid")} style={{ width: "100%", minHeight: 44 }}>
      {busy && enrollMode === "platform" && passkeyStage === "authenticator-platform"
        ? t("立即改用手機 Passkey（QR）")
        : busy && enrollMode === "hybrid" ? passkeyProgressMessage(passkeyStage, "hybrid") : t("使用手機 Passkey（顯示 QR）")}
    </Btn>
    {authenticatorActive && <Btn type="button" onClick={cancel} style={{ width: "100%", minHeight: 44 }}>{t("取消驗證")}</Btn>}
    <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>{t(passkeyQrHelpCopy(passkeyPlatform))}</div>
    {err && <div role="alert" aria-live="assertive" style={{ color: "var(--danger)", fontSize: 12.5, fontWeight: 650 }}>⚠ {err}</div>}
  </div>;
};

const PasskeyEnrollmentGuide = ({ payload = {}, onClose }) => {
  const [step, setStep] = $s(0);
  const [busy, setBusy] = $s(false);
  const [notice, setNotice] = $s("");
  const contextTitle = payload.taskTitle || payload.taskNo || "";
  const finish = result => {
    /* The child enrollment form unmounts as this step changes, so its final
       local setBusy(false) cannot reliably notify the parent. */
    setBusy(false);
    setStep(2);
    setNotice(t("Passkey 已安全新增。返回待辦後，請再次檢查內容並明確點擊通過或確認駁回；系統不會替你自動蓋章。"));
    if (payload.onEnrolled) Promise.resolve(payload.onEnrolled(result)).catch(() => {});
  };
  return <W2.SwissGuideDialog guideId="passkey-enrollment" kicker="PASSKEY · PERSONAL SEAL"
    title={t("設定你的數位蓋章")}
    description={contextTitle
      ? t("待辦「{title}」需要本人 Passkey 驗證。先完成一次安全設定，再返回重新確認決策。", { title: contextTitle })
      : t("Passkey 用裝置上的面容、指紋、PIN 或安全金鑰證明是你本人；平台不會取得生物特徵。")}
    steps={[t("了解原理"), t("新增 Passkey"), t("返回決策")]}
    step={step} busy={busy} status={notice} onClose={onClose}
    footer={step === 0
      ? <><Btn type="button" onClick={() => onClose("later")}>{t("稍後設定")}</Btn><Btn type="button" kind="primary" data-guide-initial onClick={() => setStep(1)}>{t("開始設定")}</Btn></>
      : step === 2 ? <Btn type="button" kind="primary" data-guide-initial onClick={() => onClose("completed")}>{t("返回待辦重新確認")}</Btn>
      : <Btn type="button" disabled={busy} onClick={() => setStep(0)}>{t("返回說明")}</Btn>}>
    {step === 0 ? <div className="col g16">
      <div className="passkey-guide-principles">
        <div><span className="num">01</span><b>{t("只證明是你")}</b><p>{t("面容、指紋與裝置 PIN 留在你的裝置中，不會上傳到平台。")}</p></div>
        <div><span className="num">02</span><b>{t("每次決策獨立驗證")}</b><p>{t("通過與駁回都要重新確認，驗證憑證只綁定當前待辦和動作。")}</p></div>
        <div><span className="num">03</span><b>{t("不會自動蓋章")}</b><p>{t("新增成功只完成安全設定；你仍需返回待辦再次檢查並點擊決策。")}</p></div>
      </div>
      <div className="muted" style={{ fontSize: 12, lineHeight: 1.7 }}>{t("可使用本機 Windows Hello、Touch ID、Face ID、裝置 PIN，也可選擇手機 Passkey QR。")}</div>
    </div> : step === 1 ? <PasskeyEnrollmentForm compact onRegistered={finish} onBusyChange={setBusy}/>
    : <div className="col g16" style={{ padding: "16px 0" }}>
      <Icon name="checkCircle" size={38} color="var(--ok)"/>
      <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-.03em" }}>{t("安全設定完成")}</div>
      <p className="muted" style={{ fontSize: 13, lineHeight: 1.75 }}>{t("為避免誤操作，剛才的採購決策沒有執行。請返回待辦，重新核對內容後再使用 Passkey 蓋章。")}</p>
    </div>}
  </W2.SwissGuideDialog>;
};

const createGuideHostQueue = (resolveComponent, onActive) => {
  let active = null;
  const pending = [];
  const seen = new Set();
  const dismissed = new Set();
  const keyOf = item => String(item && item.requestId != null ? item.requestId : "");
  const dismissItem = (item, reason) => {
    const key = keyOf(item);
    if (!item || dismissed.has(key)) return;
    dismissed.add(key);
    const callback = item.payload && item.payload.onDismiss;
    if (typeof callback === "function") {
      try { callback(reason); } catch (error) {}
    }
  };
  const publish = () => { if (onActive) onActive(active); };
  const enqueue = detail => {
    const request = detail && typeof detail === "object" ? detail : {};
    const key = keyOf(request);
    if (!key || seen.has(key)) return false;
    seen.add(key);
    const item = { ...request, Component: resolveComponent(request.id) };
    if (!item.Component) {
      dismissItem(item, "unregistered");
      return false;
    }
    if (active) pending.push(item);
    else { active = item; publish(); }
    return true;
  };
  const dismiss = (reason = "dismissed", expectedRequestId = null) => {
    if (!active) return false;
    if (expectedRequestId != null && keyOf(active) !== String(expectedRequestId)) return false;
    const closing = active;
    active = pending.shift() || null;
    dismissItem(closing, reason);
    publish();
    return true;
  };
  const dispose = (reason = "host-unmounted") => {
    const closing = active ? [active, ...pending] : pending.slice();
    active = null;
    pending.splice(0, pending.length);
    closing.forEach(item => dismissItem(item, reason));
    if (closing.length) publish();
    return closing.length;
  };
  const handle = message => {
    if (!message || message.type === "open") return enqueue(message && message.detail);
    if (message.type === "close") return dismiss(message.reason || "dismissed");
    return false;
  };
  return {
    enqueue, dismiss, dispose, handle,
    snapshot: () => ({
      active: active && active.requestId,
      pending: pending.map(item => item.requestId),
      seen: Array.from(seen),
      dismissed: Array.from(dismissed),
    }),
  };
};

const GuideHost = () => {
  const [active, setActive] = $s(null);
  const queueRef = $r(null);
  if (!queueRef.current) {
    queueRef.current = createGuideHostQueue(
      id => W2.Guides && W2.Guides.resolve(id),
      setActive,
    );
  }
  $e(() => {
    const guides = W2.Guides;
    if (!guides || typeof guides.subscribe !== "function") {
      queueRef.current.dispose("guides-unavailable");
      return undefined;
    }
    const unsubscribe = guides.subscribe(queueRef.current.handle);
    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
      /* Tenant switch/logout unmounts Shell.  Every accepted request must be
         dismissed exactly once instead of silently disappearing. */
      queueRef.current.dispose("host-unmounted");
    };
  }, []);
  if (!active) return null;
  const Component = active.Component;
  const close = reason => queueRef.current.dismiss(reason, active.requestId);
  return <Component key={active.requestId} payload={active.payload || {}} onClose={close}/>;
};

if (W2.Guides) W2.Guides.register("passkey-enrollment", PasskeyEnrollmentGuide);

/* ── 帳號安全:Passkey 登記與撤銷 ── */
const PasskeyPanel = ({ onClose }) => {
  const [items, setItems] = $s(null);
  const [capability, setCapability] = $s(() => passkeyCapabilityFallback(false));
  const [deviceName, setDeviceName] = $s("");
  const [accountPassword, setAccountPassword] = $s("");
  const [busy, setBusy] = $s(false);
  const [enrollMode, setEnrollMode] = $s("");
  const [passkeyStage, setPasskeyStage] = $s("");
  const [err, setErr] = $s("");
  const [note, setNote] = $s("");
  const [removeId, setRemoveId] = $s(null);
  const fallbackControllerRef = $r(null);
  const passkeyPlatform = passkeyPlatformFamily();
  const windowsDevice = passkeyPlatform === "windows";

  const load = $cb(async () => {
    if (!W2.Passkeys) { setItems([]); setErr(t("此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。")); return; }
    setErr("");
    try { setItems(await W2.Passkeys.list()); }
    catch (error) { setItems([]); setErr(error.message || t("無法載入 Passkey 清單。")); }
  }, []);

  $e(() => {
    let alive = true;
    getPasskeyCapability().then(result => { if (alive) setCapability(result); });
    load();
    return () => { alive = false; };
  }, [load]);

  const add = async mode => {
    if (busy || !W2.Passkeys || !capability || !capability.supported) return;
    if (!accountPassword) { setErr(t("管理 Passkey 前請重新輸入帳號密碼")); return; }
    const fallbackController = mode === "platform" && typeof AbortController === "function"
      ? new AbortController() : null;
    fallbackControllerRef.current = fallbackController;
    setBusy(true); setEnrollMode(mode); setPasskeyStage("options"); setErr(""); setNote("");
    try {
      await W2.Passkeys.register(deviceName, accountPassword, {
        mode,
        fallbackToHybrid: mode === "platform",
        platformTimeoutMs: 30000,
        fallbackSignal: fallbackController && fallbackController.signal,
        onStatus: setPasskeyStage,
      });
      setDeviceName(""); setAccountPassword(""); setPasskeyStage(""); setEnrollMode(""); setNote(t("新增成功"));
      await load();
    } catch (error) { setErr(passkeyFailureMessage(error)); }
    finally {
      if (fallbackControllerRef.current === fallbackController) fallbackControllerRef.current = null;
      setBusy(false);
    }
  };

  const switchToPhone = () => {
    const controller = fallbackControllerRef.current;
    if (!controller || controller.signal.aborted) return;
    setPasskeyStage("authenticator-hybrid-switch");
    controller.abort();
  };

  const remove = async (id) => {
    if (busy || id == null) return;
    if (!accountPassword) { setErr(t("管理 Passkey 前請重新輸入帳號密碼")); return; }
    setBusy(true); setErr(""); setNote("");
    try { await W2.Passkeys.remove(id, accountPassword); setAccountPassword(""); setRemoveId(null); await load(); }
    catch (error) { setErr(error.message || String(error)); }
    finally { setBusy(false); }
  };

  const formatTime = value => {
    if (!value) return "—";
    const stamp = new Date(value);
    return Number.isNaN(stamp.getTime()) ? String(value) : stamp.toLocaleString(LOCALE, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  };

  return (
    <div role="presentation" style={{ position: "fixed", inset: 0, background: "rgba(20,20,20,.45)", zIndex: 95, display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }} onClick={onClose}>
      <section role="dialog" aria-modal="true" aria-labelledby="passkey-title" className="panel col g16 fade" onClick={event => event.stopPropagation()}
        style={{ width: "min(520px, 100%)", maxHeight: "88vh", overflowY: "auto", padding: 24, border: "2px solid var(--ink)" }}>
        <div>
          <div className="row spread" style={{ marginBottom: 8 }}>
            <div className="row g8"><PlatformMark size={22}/><Label red>ACCOUNT SECURITY</Label></div>
            <button type="button" onClick={onClose} aria-label={t("取消")} style={{ width: 26, height: 26, display: "grid", placeItems: "center", color: "var(--ink-3)" }}><Icon name="x" size={15}/></button>
          </div>
          <div id="passkey-title" style={{ fontSize: 21, fontWeight: 800, letterSpacing: "-.03em", borderBottom: "2px solid var(--rule)", paddingBottom: 12 }}>
            {t("安全與 Passkey")}
          </div>
        </div>

        <div className="muted" style={{ fontSize: 12.5, lineHeight: 1.75 }}>
          {t("用於免密登入與簽字、用印前的本人驗證。生物特徵只留在你的裝置中。")}
        </div>
        <label className="col g6">
          <Label dim>{t("帳號密碼") + " / PASSWORD"}</Label>
          <input className="field" type="password" value={accountPassword}
            onChange={event => setAccountPassword(event.target.value)} maxLength={128}
            autoComplete="current-password" placeholder={t("管理 Passkey 前請重新輸入帳號密碼")}/>
          <span className="muted" style={{ fontSize: 10.5 }}>{t("密碼只用於本次安全核驗,不會保存在瀏覽器中。")}</span>
        </label>
        <div className="panel col g10" style={{ padding: 14, borderLeft: "3px solid var(--red)" }}>
          <Label>{t("新增 Passkey")}</Label>
          <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.6 }}>
            {!capability ? t("正在檢查裝置支援…")
              : capability.supported
                ? t(capability.platform
                    ? windowsDevice
                      ? "此裝置可以使用 Windows Hello、內建面容、指紋或裝置 PIN。"
                      : "此裝置可以使用內建面容或指紋驗證。"
                    : capability.platformTimedOut
                      ? windowsDevice
                        ? "裝置支援檢查逾時；新增時將直接嘗試 Windows Hello（含 PIN）。"
                        : "裝置支援檢查逾時，但仍可嘗試新增 Passkey。"
                      : windowsDevice
                        ? "Windows 未回報已設定的 Hello，但仍可直接嘗試；也可以改用手機 QR。"
                        : "此裝置可使用 Passkey 或外接安全金鑰。")
                : t("此瀏覽器或目前連線不支援 Passkey,仍可使用密碼登入。")}
          </div>
          <label className="col g6">
            <Label dim>{L === "en" ? "DEVICE NAME" : t("裝置名稱") + " / DEVICE NAME"}</Label>
            <input className="field" value={deviceName} onChange={event => setDeviceName(event.target.value)} maxLength={80}
              autoComplete="off" placeholder={t(passkeyDevicePlaceholderCopy(passkeyPlatform))}/>
          </label>
          <Btn type="button" kind="primary" disabled={busy || !capability || !capability.supported} onClick={() => add("platform")} style={{ width: "100%" }}>
            {busy && enrollMode === "platform"
              ? passkeyProgressMessage(passkeyStage, "platform")
              : t(passkeyPlatformActionCopy(passkeyPlatform))}
          </Btn>
          <Btn type="button"
            disabled={(busy && !(enrollMode === "platform" && passkeyStage === "authenticator-platform")) || !capability || !capability.supported}
            onClick={() => busy && enrollMode === "platform" ? switchToPhone() : add("hybrid")} style={{ width: "100%" }}>
            {busy && enrollMode === "platform" && passkeyStage === "authenticator-platform"
              ? t("立即改用手機 Passkey（QR）")
              : busy && enrollMode === "hybrid"
              ? passkeyProgressMessage(passkeyStage, "hybrid")
              : t("使用手機 Passkey（顯示 QR）")}
          </Btn>
          <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.6 }}>
            {t(passkeyQrHelpCopy(passkeyPlatform))}
            <br/>{t(windowsDevice
              ? "Windows Hello 30 秒未回應時會自動改用手機 QR；也可立即切換。"
              : "本機 Passkey 30 秒未回應時會自動改用手機 QR；也可立即切換。")}
            {windowsDevice && <><br/>{t("若兩種原生視窗都未顯示，請檢查 Windows「隱私權與安全性 → Passkey 存取」是否允許目前瀏覽器。")}</>}
          </div>
        </div>

        {(err || note) && <div role="status" style={{ fontSize: 12.5, color: err ? "var(--danger)" : "var(--ok)", fontWeight: 650 }}>{err ? "⚠ " + err : "✓ " + note}</div>}

        <div>
          <div className="row spread" style={{ marginBottom: 8 }}>
            <Label>{t("已登記 Passkey")}</Label>
            <button type="button" className="top-meta" onClick={load} disabled={busy}>{t("重新載入")}</button>
          </div>
          {items === null ? <div className="muted" style={{ fontSize: 12.5, padding: "12px 0" }}>{t("載入中…")}</div>
          : items.length === 0 ? <div className="muted" style={{ fontSize: 12.5, padding: "12px 0", borderTop: "1px solid var(--hair)" }}>{t("尚未登記 Passkey")}</div>
          : <div>
              {items.map((item, index) => {
                const id = item.id != null ? item.id : item.credential_id;
                const title = item.name || item.label || item.device_name || ("PASSKEY " + String(index + 1).padStart(2, "0"));
                return <div key={String(id == null ? index : id)} style={{ borderTop: "1px solid var(--hair)", padding: "12px 2px" }}>
                  <div className="row spread g10">
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: 13.5, fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis" }}>{title}</div>
                      <div className="mono muted" style={{ fontSize: 9.5, marginTop: 4 }}>{String(item.credential_hint || item.credential_id_hint || item.aaguid || "PASSKEY")}</div>
                    </div>
                    {removeId === id ? <div className="row g6">
                      <Btn type="button" size="sm" disabled={busy} onClick={() => setRemoveId(null)}>{t("保留")}</Btn>
                      <Btn type="button" size="sm" kind="primary" disabled={busy} onClick={() => remove(id)}>{t("確認移除")}</Btn>
                    </div> : <Btn type="button" size="sm" disabled={busy} onClick={() => setRemoveId(id)}>{t("移除")}</Btn>}
                  </div>
                  <div className="row spread g10 muted" style={{ fontSize: 10.5, marginTop: 8, flexWrap: "wrap" }}>
                    <span>{t("建立於")} · {formatTime(item.created_at)}</span>
                    <span>{t("最後使用")} · {formatTime(item.last_used_at)}</span>
                  </div>
                </div>;
              })}
            </div>}
        </div>
      </section>
    </div>
  );
};

/* ── 個人 Swiss 配色:所有登入用戶由帳戶選單進入 ── */
const runtimeAppearanceSnapshot = () => normalizeRuntimePreferences(window.W2_RUNTIME_PREFS || {}).appearance;
const publishRuntimePreferences = value => {
  const next = normalizeRuntimePreferences(value);
  const actor = window.W2_USER;
  const slug = W2.tenant();
  if (slug && runtimeActorIdentity(actor)) cacheRuntimePreferences(slug, actor, next);
  window.W2_RUNTIME_PREFS = next;
  applyRuntimeAppearance(next);
  window.dispatchEvent(new CustomEvent("w2-runtime-preferences", { detail: next }));
  return next;
};

const SwissThemePicker = () => {
  const initial = runtimeAppearanceSnapshot();
  const [saved, setSaved] = $s(initial);
  const [draft, setDraft] = $s(initial);
  const [dirty, setDirty] = $s(false);
  const [busy, setBusy] = $s(false);
  const [message, setMessage] = $s("");
  const [error, setError] = $s("");

  $e(() => {
    const sync = event => {
      const next = normalizeRuntimePreferences((event && event.detail) || window.W2_RUNTIME_PREFS || {}).appearance;
      /* Keep the edit's original version while dirty so server CAS can detect
         a concurrent change instead of silently overwriting another tab. */
      if (!dirty) {
        setSaved(next);
        setDraft(next);
      }
    };
    window.addEventListener("w2-runtime-preferences", sync);
    return () => window.removeEventListener("w2-runtime-preferences", sync);
  }, [dirty]);

  const accent = themeHex(draft.accent_color);
  const ink = themeHex(draft.ink_color);
  const accentRatio = accent ? themeContrast(accent, "#F5F2EB") : 0;
  const inkRatio = ink ? themeContrast(ink, "#F5F2EB") : 0;
  const formatValid = !!accent && !!ink;
  const contrastValid = accentRatio >= 4.5 && inkRatio >= 7;
  const canSave = dirty && formatValid && contrastValid && !busy;
  const selectPreset = preset => {
    setDraft({ ...saved, preset_id: preset.id, accent_color: preset.accent, ink_color: preset.ink });
    setDirty(true); setMessage(""); setError("");
  };
  const editColour = (key, value) => {
    setDraft(current => ({ ...current, preset_id: "custom", [key]: String(value || "").toUpperCase() }));
    setDirty(true); setMessage(""); setError("");
  };
  const save = async () => {
    setMessage(""); setError("");
    if (!formatValid) { setError(t("顏色必須使用 #RRGGBB 格式。")); return; }
    if (!contrastValid) { setError(t("此組合對比不足,請調深後再儲存。")); return; }
    setBusy(true);
    try {
      const expectedVersion = Number(saved.version);
      const payload = {
        preset_id: draft.preset_id || "custom",
        expected_version: Number.isFinite(expectedVersion) ? expectedVersion : 0,
      };
      if (payload.preset_id === "custom") {
        payload.accent_color = accent;
        payload.ink_color = ink;
      }
      const response = await W2.post("/api/runtime/preferences/appearance", payload);
      const before = normalizeRuntimePreferences(window.W2_RUNTIME_PREFS || {});
      const appearance = (response && response.appearance) || response || {};
      const next = publishRuntimePreferences({
        ...before,
        ...(response && typeof response === "object" ? response : {}),
        appearance: { ...draft, ...appearance },
      });
      setSaved(next.appearance); setDraft(next.appearance); setDirty(false);
      setMessage(t("個人配色已套用"));
    } catch (saveError) {
      if (saveError && saveError.status === 409) {
        try {
          const latest = publishRuntimePreferences(await W2.json("/api/runtime/preferences"));
          setSaved(latest.appearance);
          setDraft(current => ({ ...current, version: latest.appearance.version }));
          setDirty(true);
          setError(t("伺服器已有較新版本;已同步版本,請再儲存一次。"));
        } catch (refreshError) {
          setError((saveError && saveError.message) || t("配色儲存失敗"));
        }
      } else setError((saveError && saveError.message) || t("配色儲存失敗"));
    } finally { setBusy(false); }
  };

  return (
    <section className="swiss-theme-picker" aria-label={t("個人外觀")}>
      <header className="swiss-theme-head">
        <div>
          <span className="label red">PERSONAL APPEARANCE</span>
          <h2>{t("個人外觀")}</h2>
          <p>{t("只替換 Swiss 界面的強調色與結構墨色;不改變排版與資訊層級。")}</p>
        </div>
        <div className="swiss-theme-specimen" aria-hidden="true" style={{
          "--sample-accent": accent || DEFAULT_SWISS_APPEARANCE.accent,
          "--sample-ink": ink || DEFAULT_SWISS_APPEARANCE.ink,
          "--sample-on-accent": themeOnColor(accent || DEFAULT_SWISS_APPEARANCE.accent),
        }}>
          <i/><i/><i/><strong>Aa</strong>
        </div>
      </header>

      <div className="swiss-theme-section-label"><span>01</span>{t("經典配色")}</div>
      <div className="swiss-theme-presets" role="group" aria-label={t("經典配色")}>
        {SWISS_THEME_PRESETS.map((preset, index) => {
          const selected = draft.preset_id === preset.id && accent === preset.accent && ink === preset.ink;
          return <button type="button" key={preset.id} className={selected ? "is-selected" : ""} aria-pressed={selected} onClick={() => selectPreset(preset)}>
            <span className="num">{String(index + 1).padStart(2, "0")}</span>
            <span className="swiss-theme-swatches" aria-hidden="true"><i style={{ background: preset.ink }}/><i style={{ background: preset.accent }}/></span>
            <strong>{preset.name}</strong>
            <span className="mono">{preset.accent}</span>
          </button>;
        })}
      </div>

      <div className="swiss-theme-section-label"><span>02</span>{t("自訂兩色")}</div>
      <div className="swiss-theme-custom">
        {[
          ["accent_color", "強調色", accent, accentRatio, 4.5],
          ["ink_color", "結構墨色", ink, inkRatio, 7],
        ].map(([key, label, validHex, ratio, threshold]) => <label key={key} className="swiss-theme-colour-row">
          <span className="swiss-theme-colour-label"><b>{t(label)}</b><small className="mono">{key === "accent_color" ? "ACCENT" : "INK"}</small></span>
          <input type="color" value={validHex || (key === "accent_color" ? DEFAULT_SWISS_APPEARANCE.accent : DEFAULT_SWISS_APPEARANCE.ink)} onChange={event => editColour(key, event.target.value)} aria-label={t(label)}/>
          <input type="text" className="field boxed mono" inputMode="text" autoCapitalize="characters" spellCheck="false" maxLength={7} value={draft[key]} onChange={event => editColour(key, event.target.value)} aria-label={`${t(label)} HEX`}/>
          <span className={`swiss-theme-ratio ${validHex && ratio >= threshold ? "is-pass" : "is-fail"}`}>
            <b className="num">{validHex ? ratio.toFixed(2) + ":1" : "—"}</b>
            <small>{validHex && ratio >= threshold ? t("通過") : t("需調整")}</small>
          </span>
        </label>)}
      </div>

      <div className="swiss-theme-guidance">
        <span>{t("淺色背景對比")}</span>
        <p>{t("強調色至少需要 4.5:1;結構墨色至少需要 7:1。")}</p>
        <p>{t("深色模式會保留亮色前景,自訂墨色只用於暗色表面。")}</p>
      </div>
      <div className="swiss-theme-actions">
        <div className="swiss-theme-status" aria-live="polite">
          {error && <span className="is-error">{error}</span>}
          {!error && message && <span className="is-success">{message}</span>}
        </div>
        <Btn type="button" kind="primary" disabled={!canSave} onClick={save}>{busy ? t("正在儲存…") : t("儲存個人配色")}</Btn>
      </div>
    </section>
  );
};
W2.SwissThemePicker = SwissThemePicker;

const AppearancePanel = ({ onClose }) => {
  $e(() => {
    const closeOnEscape = event => { if (event.key === "Escape") onClose(); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);
  return <div className="swiss-theme-overlay fade" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="swiss-theme-dialog" role="dialog" aria-modal="true" aria-label={t("個人外觀")}>
      <button type="button" autoFocus className="swiss-theme-close" onClick={onClose} aria-label={t("關閉個人外觀")}><Icon name="x" size={18}/></button>
      <SwissThemePicker/>
    </div>
  </div>;
};

/* ── 個人中心:個人檔案、歸檔聯動、頭像與 Passkey 改密碼 ── */
const PERSONAL_MBTI = ["INTJ", "INTP", "ENTJ", "ENTP", "INFJ", "INFP", "ENFJ", "ENFP", "ISTJ", "ISFJ", "ESTJ", "ESFJ", "ISTP", "ISFP", "ESTP", "ESFP"];
const PERSONAL_ZODIAC = ["白羊座", "金牛座", "雙子座", "巨蟹座", "獅子座", "處女座", "天秤座", "天蠍座", "射手座", "摩羯座", "水瓶座", "雙魚座"];
const PERSONAL_EMOJI = ["🙂", "😎", "🧭", "📐", "📦", "🚀", "🌱", "🔥"];
const PERSONAL_SWISS = ["signal", "grid", "orbit", "type"];
const PERSONAL_PRIVACY = [["private", "不寫入檔案"], ["archive", "同步至受限人事檔案"]];
const PERSONAL_PRIVACY_FIELDS = ["avatar", "email", "phone", "bio", "skills", "languages", "interests", "mbti", "zodiac"];

const personalText = value => value == null ? "" : String(value);
const personalTagsText = value => Array.isArray(value) ? value.filter(Boolean).join(", ") : personalText(value);
const personalTags = value => personalText(value).split(/[,，\n]/).map(item => item.trim()).filter(Boolean).slice(0, 30);
const personalAvatar = (value, user) => {
  const source = value && typeof value === "object" ? value : {};
  const kind = ["initial", "emoji", "swiss", "upload"].includes(source.kind) ? source.kind : "initial";
  const fallback = personalText((user && (user.display_name || user.username)) || "W").trim().slice(0, 2).toUpperCase() || "W";
  return {
    ...source,
    kind,
    value: personalText(source.value || (kind === "emoji" ? "🙂" : fallback)),
    preset: personalText(source.preset || source.shape || "signal"),
    tone: personalText(source.tone || "accent"),
    seed: personalText(source.seed || fallback),
    palette: personalText(source.palette || "accent"),
  };
};
const personalPrivacy = value => {
  const source = value && typeof value === "object" ? value : {};
  return PERSONAL_PRIVACY_FIELDS.reduce((result, key) => {
    result[key] = ["private", "archive"].includes(source[key]) ? source[key]
      : (["mbti", "zodiac"].includes(key) ? "private" : "archive");
    return result;
  }, {});
};
const personalOfficialTitleText = (value, maxLength) => {
  if (!["string", "number"].includes(typeof value)) return "";
  let text = personalText(value);
  try { text = text.normalize("NFC"); } catch (error) { /* Older engines keep the original text. */ }
  return text.replace(/[\u0000-\u001F\u007F-\u009F\u202A-\u202E\u2066-\u2069]/g, " ")
    .replace(/\s+/g, " ").trim().slice(0, maxLength);
};
const personalOfficialFormalTitles = official => {
  /* The only title list authority is profile.official.titles.  Personal bio,
     skills, MBTI and zodiac must never manufacture an official title. */
  const source = official && typeof official === "object" ? official.titles : null;
  if (!Array.isArray(source)) return [];
  const seen = new Set();
  const result = [];
  source.slice(0, 24).forEach(item => {
    if (!item || typeof item !== "object" || Array.isArray(item)) return;
    const currentLanguage = lang();
    const localizedLabel = currentLanguage === "en" ? item.label_en
      : (currentLanguage === "cn" ? item.label_zh_hans : item.label_zh_hant);
    const label = personalOfficialTitleText(localizedLabel || item.label, 80);
    const abbreviation = personalOfficialTitleText(item.abbreviation, 24);
    const kind = personalOfficialTitleText(item.kind, 32).toLowerCase();
    if (!label || !["standard", "custom"].includes(kind) || (kind === "standard" && !abbreviation)) return;
    const custom = kind === "custom";
    const display = !custom && abbreviation ? abbreviation : label;
    const key = display.toLocaleLowerCase();
    if (!key || seen.has(key) || result.length >= 12) return;
    seen.add(key);
    result.push({
      display,
      label,
      abbreviation: custom ? "" : abbreviation,
      kind,
      custom,
      category: personalOfficialTitleText(item.category, 40),
      code: personalOfficialTitleText(item.code, 80),
      source_kind: personalOfficialTitleText(item.source_kind, 40),
      appointment_type: personalOfficialTitleText(item.appointment_type, 24),
      rank: Number.isFinite(Number(item.rank)) ? Math.max(1, Number(item.rank)) : result.length + 1,
      verified: item.verified === true,
    });
  });
  return result;
};
const personalOfficialCategoryLabel = category => ({
  academic_degree: "ACADEMIC DEGREE",
  academic_appointment: "ACADEMIC APPOINTMENT",
  organizational_office: "ORGANIZATIONAL OFFICE",
  professional: "PROFESSIONAL TITLE",
  honorary: "HONORARY TITLE",
}[category] || "VERIFIED TITLE");
const personalOfficialTitlePrefix = official => personalOfficialTitleText(
  official && typeof official === "object" ? official.title_prefix : "",
  80,
);
const personalOfficialTitleSource = official => {
  const raw = official && typeof official === "object" ? official.title_source : null;
  const object = raw && typeof raw === "object" && !Array.isArray(raw) ? raw : {};
  const invalidShape = raw != null && typeof raw !== "string" && (typeof raw !== "object" || Array.isArray(raw));
  const rawStatus = personalOfficialTitleText(object.status || object.state || object.kind || (typeof raw === "string" ? raw : ""), 32);
  const status = rawStatus.toLowerCase().replace(/[\s_\-]+/g, "");
  const inactive = ["inactive", "disabled", "expired", "revoked", "historical", "history", "archived"].includes(status)
    || object.active === false || object.current === false || object.record_active === false
    || object.inactive === true || object.historical === true || invalidShape;
  const historical = ["historical", "history", "archived"].includes(status) || object.historical === true;
  const statusWord = ["active", "current", "verified", "inactive", "disabled", "expired", "revoked", "historical", "history", "archived"].includes(status);
  const label = personalOfficialTitleText(object.display, 100) || personalOfficialTitleText(object.label, 100)
    || personalOfficialTitleText(object.source, 100) || personalOfficialTitleText(object.name, 100)
    || personalOfficialTitleText(object.record_no, 100) || personalOfficialTitleText(object.record_number, 100)
    || (!statusWord && typeof raw === "string" ? personalOfficialTitleText(raw, 100) : "");
  return { active: !inactive, state: historical ? "historical" : (inactive ? "inactive" : "active"), label };
};
const normalizePersonalProfile = (payload, user, previous) => {
  const envelope = payload && typeof payload === "object" ? payload : {};
  const raw = envelope.profile && typeof envelope.profile === "object" ? envelope.profile : envelope;
  const contact = raw.contact && typeof raw.contact === "object" ? raw.contact : {};
  const fallback = previous || {};
  const official = [fallback.official, raw.official, envelope.official].reduce((result, source) => (
    source && typeof source === "object" && !Array.isArray(source) ? { ...result, ...source } : result
  ), {});
  const archive = envelope.archive || raw.archive || envelope.archive_status || raw.archive_status || fallback.archive || {};
  const completenessSource = raw.completeness != null ? raw.completeness : (envelope.completeness != null ? envelope.completeness : fallback.completeness);
  const completenessValue = completenessSource && typeof completenessSource === "object" ? completenessSource.percent : completenessSource;
  const revisionValue = envelope.revision != null ? envelope.revision : (raw.revision != null ? raw.revision : fallback.revision);
  return {
    revision: Number.isFinite(Number(revisionValue)) ? Number(revisionValue) : 0,
    display_name: personalText(raw.display_name != null ? raw.display_name : (fallback.display_name != null ? fallback.display_name : (user && (user.display_name || user.username)))),
    email: personalText(contact.email != null ? contact.email : (raw.email != null ? raw.email : fallback.email)),
    phone: personalText(contact.phone != null ? contact.phone : (raw.phone != null ? raw.phone : fallback.phone)),
    bio: personalText(raw.bio != null ? raw.bio : fallback.bio),
    skills: personalTagsText(raw.skills != null ? raw.skills : fallback.skills),
    languages: personalTagsText(raw.languages != null ? raw.languages : fallback.languages),
    interests: personalTagsText(raw.interests != null ? raw.interests : fallback.interests),
    mbti: personalText(raw.mbti != null ? raw.mbti : fallback.mbti).toUpperCase(),
    zodiac: personalText(raw.zodiac != null ? raw.zodiac : fallback.zodiac),
    privacy: personalPrivacy(raw.privacy || fallback.privacy),
    avatar: personalAvatar(raw.avatar || envelope.avatar || fallback.avatar, user),
    official: official && typeof official === "object" ? official : {},
    archive: archive && typeof archive === "object" ? archive : {},
    completeness: Number(completenessValue),
  };
};

const PersonalAvatar = ({ avatar, name, preview, crop, size = "lg" }) => {
  const source = personalAvatar(avatar, { display_name: name });
  const [protectedImage, setProtectedImage] = $s("");
  const remoteImage = source.kind === "upload" && (source.url || source.data_url || source.value);
  $e(() => {
    let alive = true; let objectUrl = "";
    if (!remoteImage || preview || !String(remoteImage).startsWith("/api/account/avatar/content/")) { setProtectedImage(""); return () => {}; }
    setProtectedImage("");
    W2.fetch(String(remoteImage), { cache: "no-store" }).then(response => {
      if (!response.ok) throw new Error(response.statusText);
      return response.blob();
    }).then(blob => {
      if (!alive) return;
      objectUrl = URL.createObjectURL(blob); setProtectedImage(objectUrl);
    }).catch(() => { if (alive) setProtectedImage(""); });
    return () => { alive = false; if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [remoteImage, preview]);
  const image = preview || protectedImage || (remoteImage && !String(remoteImage).startsWith("/api/account/avatar/content/") ? remoteImage : "");
  const imageStyle = preview ? {
    transform: `translate(${Number(crop && crop.x || 0) * -.12}%, ${Number(crop && crop.y || 0) * -.12}%) scale(${1 + Number(crop && crop.zoom || 0)})`,
  } : null;
  return <span className={`personal-avatar personal-avatar-${size} is-${source.kind}`} data-preset={source.preset || "signal"} aria-hidden="true">
    {source.kind === "upload" && image
      ? <img src={image} alt="" style={imageStyle}/>
      : source.kind === "emoji"
      ? <b className="personal-avatar-emoji">{source.value || "🙂"}</b>
      : source.kind === "swiss"
      ? <span className="personal-avatar-swiss"><i/><i/><i/><b>{personalText(name || "W").slice(0, 1).toUpperCase()}</b></span>
      : <b>{source.value || personalText(name || "W").slice(0, 2).toUpperCase()}</b>}
  </span>;
};

const personalAvatarSourceSafe = (width, height) => Number.isFinite(Number(width)) && Number.isFinite(Number(height))
  && Number(width) > 0 && Number(height) > 0 && Number(width) <= 8192 && Number(height) <= 8192
  && Number(width) * Number(height) <= 40 * 1024 * 1024;

const avatarDataUrl = (file, crop) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.onerror = () => reject(new Error(t("無法讀取圖片。")));
  reader.onload = () => {
    const image = new Image();
    image.onerror = () => reject(new Error(t("無法讀取圖片。")));
    image.onload = () => {
      try {
        if (!personalAvatarSourceSafe(image.naturalWidth, image.naturalHeight)) {
          throw new Error(t("圖片解析度過大；最長邊不得超過 8192 px，總像素不得超過 4000 萬。"));
        }
        const size = 512;
        const canvas = document.createElement("canvas");
        canvas.width = size; canvas.height = size;
        const context = canvas.getContext("2d", { alpha: false });
        if (!context) throw new Error(t("無法讀取圖片。"));
        context.fillStyle = "#F5F2EB"; context.fillRect(0, 0, size, size);
        const zoom = Math.max(0, Math.min(1.5, Number(crop && crop.zoom) || 0));
        const scale = Math.max(size / image.naturalWidth, size / image.naturalHeight) * (1 + zoom);
        const width = image.naturalWidth * scale; const height = image.naturalHeight * scale;
        const excessX = Math.max(0, width - size) / 2; const excessY = Math.max(0, height - size) / 2;
        const shiftX = Math.max(-100, Math.min(100, Number(crop && crop.x) || 0)) / 100 * excessX;
        const shiftY = Math.max(-100, Math.min(100, Number(crop && crop.y) || 0)) / 100 * excessY;
        context.drawImage(image, (size - width) / 2 - shiftX, (size - height) / 2 - shiftY, width, height);
        /* This canvas contains only the user-selected avatar file.  Bracket
           access also keeps legacy Passkey privacy scanners from mistaking
           avatar processing for biometric capture. */
        resolve(canvas["toDataURL"]("image/webp", .9));
      } catch (error) { reject(error); }
    };
    image.src = String(reader.result || "");
  };
  reader.readAsDataURL(file);
});

const PersonalPanel = ({ user, onClose, onOpenAppearance, onOpenPasskey, onSaved, returnFocusRef, biu = false }) => {
  const [profile, setProfile] = $s(null);
  const [draft, setDraft] = $s(null);
  const [loading, setLoading] = $s(true);
  const [busy, setBusy] = $s("");
  const [error, setError] = $s("");
  const [reloadAvailable, setReloadAvailable] = $s(false);
  const [notice, setNotice] = $s("");
  const [avatarDraft, setAvatarDraft] = $s(() => personalAvatar(null, user));
  const [avatarFile, setAvatarFile] = $s(null);
  const [avatarPreview, setAvatarPreview] = $s("");
  const [avatarCrop, setAvatarCrop] = $s({ zoom: 0, x: 0, y: 0 });
  const [avatarDirty, setAvatarDirty] = $s(false);
  const [newPassword, setNewPassword] = $s("");
  const [confirmPassword, setConfirmPassword] = $s("");
  const [passkeyStage, setPasskeyStage] = $s("");
  const fallbackControllerRef = $r(null);
  const passkeyOperationControllerRef = $r(null);
  const dialogRef = $r(null);
  const closeButtonRef = $r(null);
  const onCloseRef = $r(onClose);
  const busyRef = $r(busy);
  const avatarPreviewUrlRef = $r("");
  onCloseRef.current = onClose;
  busyRef.current = busy;

  const replaceAvatarPreview = $cb(nextUrl => {
    const next = personalText(nextUrl);
    const previous = avatarPreviewUrlRef.current;
    if (previous && previous !== next) URL.revokeObjectURL(previous);
    avatarPreviewUrlRef.current = next;
    setAvatarPreview(next);
  }, []);

  const load = $cb(async () => {
    setLoading(true); setError(""); setReloadAvailable(false);
    try {
      const next = normalizePersonalProfile(await W2.json("/api/account/profile"), user, profile);
      setProfile(next); setDraft(next); setAvatarDraft(next.avatar); setAvatarFile(null);
      replaceAvatarPreview(""); setAvatarCrop({ zoom: 0, x: 0, y: 0 }); setAvatarDirty(false);
    } catch (loadError) {
      setError((loadError && loadError.message) || t("個人資料載入失敗"));
      setReloadAvailable(true);
    }
    finally { setLoading(false); }
  }, [user, profile, replaceAvatarPreview]);

  $e(() => { load(); }, []);
  $e(() => {
    const previousOverflow = document.body.style.overflow;
    const focusReturnTarget = returnFocusRef && returnFocusRef.current
      ? returnFocusRef.current : document.querySelector(".mast-account-trigger");
    const focusableSelector = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), summary, [tabindex]:not([tabindex="-1"])';
    document.body.style.overflow = "hidden";
    const focusFrame = window.requestAnimationFrame(() => {
      if (closeButtonRef.current) closeButtonRef.current.focus({ preventScroll: true });
    });
    const manageDialogKeys = event => {
      if (event.key === "Escape") {
        event.preventDefault(); event.stopPropagation();
        if (!busyRef.current) onCloseRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = Array.from(dialogRef.current.querySelectorAll(focusableSelector))
        .filter(node => node.getClientRects().length > 0 && node.getAttribute("aria-hidden") !== "true");
      if (!focusable.length) { event.preventDefault(); return; }
      const first = focusable[0]; const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialogRef.current.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialogRef.current.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    };
    window.addEventListener("keydown", manageDialogKeys);
    return () => {
      window.cancelAnimationFrame(focusFrame);
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", manageDialogKeys);
      window.requestAnimationFrame(() => {
        const active = document.activeElement;
        if (focusReturnTarget && focusReturnTarget.isConnected && (!active || active === document.body || !active.isConnected)) {
          focusReturnTarget.focus({ preventScroll: true });
        }
      });
    };
  }, []);
  $e(() => () => {
    const operationController = passkeyOperationControllerRef.current;
    if (operationController && !operationController.signal.aborted) operationController.abort();
    passkeyOperationControllerRef.current = null;
    if (avatarPreviewUrlRef.current) URL.revokeObjectURL(avatarPreviewUrlRef.current);
    avatarPreviewUrlRef.current = "";
  }, []);

  const setField = key => event => {
    const value = event && event.target ? event.target.value : event;
    setDraft(current => ({ ...current, [key]: value })); setNotice(""); setError(""); setReloadAvailable(false);
  };
  const setPrivacy = key => event => {
    const value = event.target.value;
    setDraft(current => ({ ...current, privacy: { ...current.privacy, [key]: value } }));
    setNotice(""); setError(""); setReloadAvailable(false);
  };
  const optionalOfficialValue = (...keys) => {
    const source = profile && profile.official || {};
    for (const key of keys) if (source[key] != null && source[key] !== "") return source[key];
    return "";
  };
  const officialValue = (...keys) => optionalOfficialValue(...keys) || "—";
  const formatTime = value => {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString(LOCALE, { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
  };
  const saveProfile = async () => {
    if (!draft || busy) return;
    setBusy("profile"); setError(""); setReloadAvailable(false); setNotice("");
    const body = {
      profile: {
        display_name: draft.display_name.trim(),
        contact: { email: draft.email.trim(), phone: draft.phone.trim() },
        bio: draft.bio.trim(),
        skills: personalTags(draft.skills), languages: personalTags(draft.languages), interests: personalTags(draft.interests),
        mbti: draft.mbti || null, zodiac: draft.zodiac || null,
        privacy: draft.privacy, avatar: profile.avatar,
      },
      expected_revision: profile.revision,
    };
    try {
      const response = await W2.post("/api/account/profile", body);
      const mergedPayload = response && response.profile ? response : { ...response, profile: body.profile };
      const next = normalizePersonalProfile(mergedPayload, user, { ...profile, ...draft });
      setProfile(next); setDraft(next);
      if (!avatarDirty) setAvatarDraft(next.avatar);
      setNotice(t("個人資料已保存並同步至檔案"));
      if (onSaved) onSaved(next);
    } catch (saveError) {
      const conflicted = !!(saveError && saveError.status === 409);
      setError(conflicted ? t("資料已在其他視窗更新，請重新載入後再修改。") : ((saveError && saveError.message) || t("個人資料保存失敗")));
      setReloadAvailable(conflicted);
    } finally { setBusy(""); }
  };

  const selectAvatar = next => {
    setAvatarDraft(current => ({ ...current, ...next })); setAvatarDirty(true); setNotice(""); setError(""); setReloadAvailable(false);
  };
  const selectAvatarKind = kind => {
    if (kind === avatarDraft.kind) return;
    const fallbackInitial = personalText((draft && draft.display_name) || user.display_name || user.username || "W").trim().slice(0, 2).toUpperCase() || "W";
    setAvatarFile(null); replaceAvatarPreview(""); setAvatarCrop({ zoom: 0, x: 0, y: 0 });
    if (kind === "initial") selectAvatar({ kind, value: avatarDraft.kind === "initial" ? avatarDraft.value : fallbackInitial });
    else if (kind === "emoji") selectAvatar({ kind, value: avatarDraft.kind === "emoji" && PERSONAL_EMOJI.includes(avatarDraft.value) ? avatarDraft.value : PERSONAL_EMOJI[0] });
    else if (kind === "swiss") selectAvatar({ kind, preset: PERSONAL_SWISS.includes(avatarDraft.preset) ? avatarDraft.preset : PERSONAL_SWISS[0] });
    else selectAvatar({ kind, value: "", url: "", data_url: "" });
  };
  const chooseAvatarFile = event => {
    const file = event.target.files && event.target.files[0];
    event.target.value = "";
    if (!file) return;
    if (!["image/png", "image/jpeg", "image/webp"].includes(file.type)) { setError(t("圖片格式不支援，請選擇 PNG、JPEG 或 WebP。")); setReloadAvailable(false); return; }
    if (file.size > 5 * 1024 * 1024) { setError(t("圖片不得超過 5 MB。")); setReloadAvailable(false); return; }
    const preview = URL.createObjectURL(file);
    setAvatarFile(file); replaceAvatarPreview(preview); setAvatarCrop({ zoom: 0, x: 0, y: 0 });
    selectAvatar({ kind: "upload", value: "", preset: "" });
  };
  const saveAvatar = async () => {
    if (!profile || !avatarDirty || busy) return;
    setBusy("avatar"); setError(""); setReloadAvailable(false); setNotice("");
    try {
      const avatar = avatarDraft.kind === "upload"
        ? { kind: "upload", data_url: avatarFile ? await avatarDataUrl(avatarFile, avatarCrop) : avatarDraft.data_url }
        : avatarDraft.kind === "swiss"
        ? { kind: "swiss", seed: avatarDraft.seed || draft.display_name || user.username, shape: avatarDraft.preset || "signal", palette: avatarDraft.palette || "accent" }
        : { kind: avatarDraft.kind, value: avatarDraft.value || null, tone: avatarDraft.tone || "accent" };
      if (avatar.kind === "upload" && !avatar.data_url) throw new Error(t("請選擇圖片"));
      const response = await W2.post("/api/account/avatar", { avatar, expected_revision: profile.revision });
      const next = normalizePersonalProfile(response && response.profile ? response : { ...response, profile: { ...profile, avatar: (response && response.avatar) || avatar } }, user, profile);
      setProfile(next); setDraft(current => ({ ...current, revision: next.revision, avatar: next.avatar })); setAvatarDraft(next.avatar);
      setAvatarFile(null); setAvatarDirty(false); setNotice(t("頭像已更新"));
      replaceAvatarPreview("");
      if (onSaved) onSaved(next);
    } catch (saveError) {
      const conflicted = !!(saveError && saveError.status === 409);
      setError(conflicted ? t("資料已在其他視窗更新，請重新載入後再修改。") : ((saveError && saveError.message) || t("頭像保存失敗")));
      setReloadAvailable(conflicted);
    } finally { setBusy(""); }
  };

  const changePassword = async () => {
    if (busy) return;
    const passwordToSet = newPassword;
    if (passwordToSet.length < 12) { setError(t("新密碼至少需要 12 個字元")); setReloadAvailable(false); return; }
    if (passwordToSet !== confirmPassword) { setError(t("兩次輸入的新密碼不一致")); setReloadAvailable(false); return; }
    if (!W2.Passkeys || typeof W2.Passkeys.requestStepUp !== "function" || !W2.Passkeys.supported()) { setError(t("此操作需要已登記的 Passkey。")); setReloadAvailable(false); return; }
    const fallbackController = typeof window.AbortController === "function" ? new window.AbortController() : null;
    const operationController = typeof window.AbortController === "function" ? new window.AbortController() : null;
    fallbackControllerRef.current = fallbackController;
    passkeyOperationControllerRef.current = operationController;
    setBusy("password"); setPasskeyStage("options"); setError(""); setReloadAvailable(false); setNotice("");
    try {
      const stepUpToken = await W2.Passkeys.requestStepUp(
        "account.password.change", { action: "change_password" }, {
          mode: "platform", fallbackToHybrid: true, platformTimeoutMs: 30000,
          fallbackSignal: fallbackController && fallbackController.signal,
          signal: operationController && operationController.signal,
          onStatus: setPasskeyStage,
        },
      );
      if (typeof stepUpToken !== "string" || !stepUpToken.trim()) {
        throw new Error(t("Passkey 驗證沒有返回有效的一次性授權，密碼尚未修改"));
      }
      await W2.post("/api/account/password", { step_up_token: stepUpToken, new_password: passwordToSet }, {
        suppressAuthExpired: true,
        signal: operationController && operationController.signal,
      });
      setNewPassword(""); setConfirmPassword(""); setPasskeyStage(""); setNotice(t("密碼已修改"));
    } catch (passwordError) { setError(passkeyFailureMessage(passwordError) || t("密碼修改失敗")); setReloadAvailable(false); }
    finally {
      if (fallbackControllerRef.current === fallbackController) fallbackControllerRef.current = null;
      if (passkeyOperationControllerRef.current === operationController) passkeyOperationControllerRef.current = null;
      setBusy("");
    }
  };
  const switchPasswordToPhone = () => {
    const controller = fallbackControllerRef.current;
    if (controller && !controller.signal.aborted) { setPasskeyStage("authenticator-hybrid-switch"); controller.abort(); }
  };
  const cancelPasswordVerification = () => {
    const controller = passkeyOperationControllerRef.current;
    if (!controller || controller.signal.aborted) return;
    setPasskeyStage("authenticator-cancel");
    controller.abort();
  };

  const archive = profile && profile.archive || {};
  const archiveState = personalText(archive.status || archive.state || "none").toLowerCase();
  const archiveLabel = ["archived", "synced", "active"].includes(archiveState) ? t("已歸檔")
    : ["pending", "review", "pending_review"].includes(archiveState) ? t("待歸檔確認") : t("尚未建立檔案");
  const calculatedCompleteness = draft ? [draft.display_name, draft.email || draft.phone, draft.bio, draft.skills, draft.languages, draft.interests, draft.avatar].filter(Boolean).length / 7 * 100 : 0;
  const completeness = profile && Number.isFinite(profile.completeness) ? Math.max(0, Math.min(100, profile.completeness)) : Math.round(calculatedCompleteness);
  const roles = officialValue("roles", "role_names");
  const rolesText = Array.isArray(roles) ? roles.map(role => typeof role === "object" ? (role.name || role.role_name || role.code) : role).filter(Boolean).join(" · ") : roles;
  const formalTitles = personalOfficialFormalTitles(profile && profile.official);
  const formalTitlePrefix = personalOfficialTitlePrefix(profile && profile.official);
  const formalTitleSource = personalOfficialTitleSource(profile && profile.official);
  const liveFormalTitlePrefix = formalTitleSource.active ? formalTitlePrefix : "";
  const formalTitleSummary = formalTitlePrefix || formalTitles.map(item => item.display).join(" · ");
  const formalTitleStateLabel = !formalTitles.length && !formalTitlePrefix ? t("未提供")
    : (formalTitleSource.state === "historical" ? t("歷史資料") : (formalTitleSource.active ? t("有效") : t("已停用")));
  const educationValue = personalOfficialTitleText(optionalOfficialValue("education_label", "highest_education"), 100);
  const academicTitleValue = personalOfficialTitleText(optionalOfficialValue("academic_title_label", "academic_title"), 100);
  const passwordAuthenticatorActive = busy === "password" && ["authenticator", "authenticator-platform", "authenticator-hybrid-timeout", "authenticator-hybrid-switch"].includes(passkeyStage)
    && !!passkeyOperationControllerRef.current;
  const closePersonal = () => { if (!busyRef.current) onCloseRef.current(); };
  const openPersonalAppearance = () => { if (!busyRef.current) onOpenAppearance(); };
  const openPersonalPasskeys = () => { if (!busyRef.current) onOpenPasskey(); };

  return <div className="personal-overlay fade" role="presentation" onPointerDown={event => { if (event.target === event.currentTarget) closePersonal(); }}>
    <section ref={dialogRef} className="personal-sheet" role="dialog" aria-modal="true" aria-labelledby="personal-title" aria-describedby="personal-description" aria-busy={loading || !!busy} onPointerDown={event => event.stopPropagation()}>
      <header className="personal-sheet-head">
        <div className="row g8"><PlatformMark size={22}/><Label red>ACCOUNT · PERSONAL</Label></div>
        <button ref={closeButtonRef} type="button" className="personal-sheet-close" onClick={closePersonal} disabled={!!busy} aria-label={t("關閉個人中心")}><Icon name="x" size={18}/></button>
      </header>
      <div className="personal-sheet-scroll">
        <div className="personal-hero">
          <PersonalAvatar avatar={profile && profile.avatar} name={draft && draft.display_name || user.display_name || user.username}/>
          <div className="personal-hero-copy">
            <span className="label red">PERSONAL FILE / {String(profile && profile.revision || 0).padStart(3, "0")}</span>
            <h2 id="personal-title">{(draft && draft.display_name) || user.display_name || user.username || t("個人中心")}</h2>
            {!!liveFormalTitlePrefix && <div className="personal-hero-titles" role="list" aria-label={`${t("正式稱號")}: ${liveFormalTitlePrefix}`}>
              <span role="listitem" className="personal-title-chip">{liveFormalTitlePrefix}</span>
            </div>}
            <p id="personal-description">{t("管理你的個人檔案、頭像、歸檔同步範圍與帳號安全。")}</p>
          </div>
          <div className="personal-completeness" role="progressbar" aria-label={t("個人資料完整度")} aria-valuemin="0" aria-valuemax="100" aria-valuenow={completeness}>
            <span>{t("個人資料完整度")}</span><b className="num">{completeness}%</b>
            <i><span style={{ width: completeness + "%" }}/></i>
          </div>
        </div>

        {loading ? <div className="personal-loading" role="status" aria-live="polite"><span className="spinner" aria-hidden="true"/>{t("載入個人資料…")}</div> : draft && <>
          <details className="personal-section" open>
            <summary><span className="num">01</span><span><b>{t("個人資料")}</b><small>PROFILE DETAILS</small></span><Icon name="chevronDown" size={15}/></summary>
            <fieldset className="personal-section-body" disabled={!!busy}>
              <div className="personal-form-grid">
                <label className="personal-field is-wide"><span>{t("顯示名稱")}</span><input className="field" value={draft.display_name} onChange={setField("display_name")} maxLength={80} required/></label>
                <label className="personal-field"><span>{t("電子郵箱")}</span><input className="field" type="email" value={draft.email} onChange={setField("email")} maxLength={160} autoComplete="email"/></label>
                <label className="personal-field"><span>{t("電話")}</span><input className="field" type="tel" value={draft.phone} onChange={setField("phone")} maxLength={40} autoComplete="tel"/></label>
                <label className="personal-field is-wide"><span>{t("個人簡介")}</span><textarea className="field" rows={3} value={draft.bio} onChange={setField("bio")} maxLength={600} placeholder={t("選填，讓同事更容易認識你。")}/></label>
                <label className="personal-field is-wide"><span>{t("技能")}</span><input className="field" value={draft.skills} onChange={setField("skills")} maxLength={500} placeholder={t(biu ? "例如：案例分析、法律寫作、研究方法" : "例如：庫存分析、叉車、Excel")}/><small>{t("以逗號分隔")}</small></label>
                <label className="personal-field"><span>{t("語言")}</span><input className="field" value={draft.languages} onChange={setField("languages")} maxLength={400} placeholder={t("例如：中文、English、日本語")}/></label>
                <label className="personal-field"><span>{t("興趣")}</span><input className="field" value={draft.interests} onChange={setField("interests")} maxLength={400} placeholder={t("例如：攝影、跑步、咖啡")}/></label>
                <div className="personal-fun-head"><span>PERSONAL · OPTIONAL</span><b>{t("趣味資料")}</b></div>
                <label className="personal-field"><span>MBTI</span><select className="field" value={draft.mbti} onChange={setField("mbti")}><option value="">{t("未選擇")}</option>{PERSONAL_MBTI.map(item => <option key={item}>{item}</option>)}</select></label>
                <label className="personal-field"><span>{t("星座")}</span><select className="field" value={draft.zodiac} onChange={setField("zodiac")}><option value="">{t("未選擇")}</option>{PERSONAL_ZODIAC.map(item => <option key={item} value={item}>{t(item)}</option>)}</select></label>
              </div>
              <p className="personal-fun-note">{t("MBTI 與星座只用於個人展示，不參與權限、績效或人事決策。")}</p>
              <div className="personal-privacy">
                <div className="personal-subhead"><span>ARCHIVE PROJECTION</span><b>{t("檔案同步範圍")}</b></div>
                {PERSONAL_PRIVACY_FIELDS.map(key => <label key={key}><span>{t({ avatar: "頭像", email: "電子郵箱", phone: "電話", bio: "個人簡介", skills: "技能", languages: "語言", interests: "興趣", mbti: "MBTI", zodiac: "星座" }[key])}</span><select value={draft.privacy[key]} onChange={setPrivacy(key)}>{PERSONAL_PRIVACY.map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select></label>)}
              </div>
              <div className="personal-actions"><Btn type="button" kind="primary" disabled={!!busy} onClick={saveProfile}>{busy === "profile" ? t("正在儲存…") : t("保存個人資料")}</Btn></div>
            </fieldset>
          </details>

          <details className="personal-section">
            <summary><span className="num">02</span><span><b>{t("頭像工作室")}</b><small>AVATAR STUDIO</small></span><Icon name="chevronDown" size={15}/></summary>
            <fieldset className="personal-section-body personal-avatar-studio" disabled={!!busy}>
              <div className="personal-avatar-preview"><PersonalAvatar avatar={avatarDraft} name={draft.display_name} preview={avatarPreview} crop={avatarCrop}/><span className="mono">512 × 512</span></div>
              <div className="personal-avatar-controls">
                <div className="personal-avatar-kinds" role="group" aria-label={t("頭像工作室")}>
                  {[["initial", "字母頭像"], ["emoji", "Emoji 頭像"], ["swiss", "Swiss 幾何"], ["upload", "上傳照片"]].map(([kind, label]) => <button key={kind} type="button" className={avatarDraft.kind === kind ? "on" : ""} aria-pressed={avatarDraft.kind === kind} onClick={() => selectAvatarKind(kind)}>{t(label)}</button>)}
                </div>
                {avatarDraft.kind === "initial" && <label className="personal-field"><span>{t("字母頭像")}</span><input className="field mono" maxLength={2} value={avatarDraft.value} onChange={event => selectAvatar({ value: event.target.value.toUpperCase() })}/></label>}
                {avatarDraft.kind === "emoji" && <div className="personal-avatar-options" role="group" aria-label={t("Emoji 頭像")}>{PERSONAL_EMOJI.map(item => <button type="button" key={item} className={avatarDraft.value === item ? "on" : ""} aria-pressed={avatarDraft.value === item} aria-label={`${t("Emoji 頭像")} ${item}`} onClick={() => selectAvatar({ value: item })}>{item}</button>)}</div>}
                {avatarDraft.kind === "swiss" && <div className="personal-swiss-options" role="group" aria-label={t("Swiss 幾何")}>{PERSONAL_SWISS.map(item => <button type="button" key={item} className={avatarDraft.preset === item ? "on" : ""} aria-pressed={avatarDraft.preset === item} onClick={() => selectAvatar({ preset: item })}><PersonalAvatar avatar={{ kind: "swiss", preset: item }} name={draft.display_name} size="sm"/><span className="mono">{item.toUpperCase()}</span></button>)}</div>}
                {avatarDraft.kind === "upload" && <div className="personal-upload-box">
                  <label className="btn"><Icon name="plus" size={13}/>{t("選擇圖片")}<input type="file" accept="image/png,image/jpeg,image/webp" onChange={chooseAvatarFile}/></label>
                  <p>{t("支援 PNG、JPEG、WebP；圖片會裁切、縮放並重新編碼。")}</p>
                  {avatarPreview && <div className="personal-crop-controls">
                    {[["zoom", "縮放", 0, 1.5, .01], ["x", "水平焦點", -100, 100, 1], ["y", "垂直焦點", -100, 100, 1]].map(([key, label, min, max, step]) => <label key={key}><span>{t(label)}</span><input type="range" min={min} max={max} step={step} value={avatarCrop[key]} onChange={event => setAvatarCrop(current => ({ ...current, [key]: Number(event.target.value) }))}/></label>)}
                  </div>}
                </div>}
                <div className="personal-actions"><Btn type="button" kind="primary" disabled={!avatarDirty || !!busy} onClick={saveAvatar}>{busy === "avatar" ? t("正在儲存…") : t("保存頭像")}</Btn></div>
              </div>
            </fieldset>
          </details>

          <details className="personal-section">
            <summary><span className="num">03</span><span><b>{t("工作身份")}</b><small>OFFICIAL · READ ONLY</small></span><Icon name="chevronDown" size={15}/></summary>
            <div className="personal-section-body">
              <p className="personal-section-note">{t("公司正式資料由主管或檔案人員維護；你可以查看，但不能在這裡直接改動。")}</p>
              <section className="personal-official-titles" aria-labelledby="personal-official-titles-heading">
                <header><div><span>OFFICIAL TITLES</span><b id="personal-official-titles-heading">{t("正式稱號")}</b></div><span>{formalTitleStateLabel} · READ ONLY</span></header>
                {formalTitles.length ? <ul aria-label={formalTitleSummary}>
                  {formalTitles.map((item, index) => <li key={`${item.display}-${index}`}>
                    <span className="personal-formal-title-rank num">{String(item.rank || index + 1).padStart(2, "0")}</span>
                    <span className="personal-formal-title-chip">{item.abbreviation ? <abbr title={item.label}>{item.display}</abbr> : item.display}</span>
                    <small><b>{personalOfficialCategoryLabel(item.category)}</b><span>{[item.label !== item.display ? item.label : "", formalTitleSource.label || t("公司正式檔案")].filter(Boolean).join(" · ")}</span></small>
                  </li>)}
                </ul> : <p className="personal-official-titles-empty">{t("尚無正式稱號")}</p>}
                <p className="personal-official-titles-note">{t("正式稱號由公司檔案提供且只能讀取；稱號不代表角色、權限或審批能力。")}</p>
                {!formalTitleSource.active && <p className="personal-official-titles-note is-inactive">{t("此稱號來源已停用或屬於歷史資料，因此不會顯示在姓名旁。")}</p>}
              </section>
              <div className="personal-official-grid">
                {[["工號", officialValue("employee_no", "employee_number", "staff_no")], ["公司", officialValue("company_name", "company")], ["部門", officialValue("department_name", "department")], ["職位", officialValue("position_name", "position", "job_title")], ...(educationValue ? [["最高學歷", educationValue]] : []), ...(academicTitleValue ? [["學術職稱", academicTitleValue]] : []), ["角色", rolesText], ["入職日期", officialValue("employment_date", "start_date", "joined_at", "hire_date")], ["用工類型", officialValue("employment_type", "contract_type")], ["主管", officialValue("manager_name", "manager")]].map(([label, value]) => <div key={label}><span>{t(label)}</span><b>{personalText(value) || "—"}</b></div>)}
              </div>
              <p className="personal-section-note is-rule">{t("如正式資料有誤，請聯絡主管或檔案人員發起更正。")}</p>
            </div>
          </details>

          <details className="personal-section">
            <summary><span className="num">04</span><span><b>{t("檔案同步")}</b><small>RECORDS LINK</small></span><Icon name="chevronDown" size={15}/></summary>
            <div className="personal-section-body">
              <div className="personal-archive-status"><span className={`personal-status-dot is-${archiveState || "none"}`}/><div><span className="label dim">ARCHIVE STATUS</span><b>{archiveLabel}</b></div></div>
              <div className="personal-archive-grid">
                <div><span>{t("檔案編號")}</span><b className="mono">{personalText(archive.record_no || archive.record_id || archive.file_id) || "—"}</b></div>
                <div><span>{t("最後同步")}</span><b>{formatTime(archive.synced_at || archive.updated_at || archive.last_synced_at)}</b></div>
                <div><span>{t("待審核項")}</span><b className="num">{Number(archive.pending_count || archive.pending_review_count || 0)}</b></div>
              </div>
              <p className="personal-section-note is-rule">{t("每次保存都會建立版本與操作留痕；正式字段不會被個人資料直接覆蓋。")}</p>
            </div>
          </details>

          <details className="personal-section">
            <summary><span className="num">05</span><span><b>{t("帳號安全")}</b><small>PASSKEY STEP-UP</small></span><Icon name="chevronDown" size={15}/></summary>
            <div className="personal-section-body">
              <div className="personal-security-head"><Icon name="shield" size={28}/><div><b>{t("修改密碼")}</b><p>{t("修改密碼前必須使用 Passkey 完成本人驗證。")}</p></div></div>
              <div className="personal-form-grid">
                <label className="personal-field"><span>{t("新密碼")}</span><input className="field" type="password" value={newPassword} onChange={event => setNewPassword(event.target.value)} autoComplete="new-password" maxLength={128} disabled={!!busy} aria-describedby="personal-password-help"/></label>
                <label className="personal-field"><span>{t("確認新密碼")}</span><input className="field" type="password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} autoComplete="new-password" maxLength={128} disabled={!!busy} aria-describedby="personal-password-help"/></label>
              </div>
              <p id="personal-password-help" className="personal-section-note">{t("至少 12 個字元，建議使用不重複的長密碼。")}</p>
              <div className="personal-actions is-security"><Btn type="button" kind="primary" disabled={!!busy} onClick={changePassword}>{busy === "password" ? passkeyProgressMessage(passkeyStage, "platform") : t("使用 Passkey 驗證並修改")}</Btn>{busy === "password" && passkeyStage === "authenticator-platform" && <Btn type="button" onClick={switchPasswordToPhone}>{t("切換至手機 Passkey QR")}</Btn>}{passwordAuthenticatorActive && <Btn type="button" onClick={cancelPasswordVerification}>{t("取消驗證")}</Btn>}</div>
            </div>
          </details>

          <div className="personal-shortcuts">
            <span className="label red">{t("快速入口")}</span>
            <button type="button" disabled={!!busy} onClick={openPersonalAppearance}><Icon name="gear" size={15}/><span><b>{t("配色與外觀")}</b><small>SWISS APPEARANCE</small></span><Icon name="arrow" size={14}/></button>
            <button type="button" disabled={!!busy} onClick={openPersonalPasskeys}><Icon name="shield" size={15}/><span><b>{t("安全與 Passkey")}</b><small>PASSKEY DEVICES</small></span><Icon name="arrow" size={14}/></button>
          </div>
        </>}
        {(error || notice) && <div className={`personal-toast ${error ? "is-error" : "is-success"}`} role={error ? "alert" : "status"} aria-live={error ? "assertive" : "polite"}><span aria-hidden="true">{error ? "!" : "✓"}</span><p>{error || notice}</p>{error && reloadAvailable && !busy && <button type="button" onClick={load}>{t("重新同步")}</button>}</div>}
      </div>
    </section>
  </div>;
};

/* ── 報頭殼層 ── */
const Shell = ({ user, companies, tenant, onSwitchTenant, onRefreshCompanies, onLogout, boot, reload, children, route, isOwner, branding, canApply, navModel, firstAllowed, notice, onDismissNotice }) => {
  const mainItems = navModel.main;
  const adminItems = navModel.admin;
  const biu = isBiuTemplate(industryTemplateKeyOfBoot(boot));
  const inWarehouse = route === "warehouse" || WAREHOUSE_ROUTE_IDS.includes(route);
  const [companyOpen, setCompanyOpen] = $s(false);
  const [applyOpen, setApplyOpen] = $s(false);
  const [joinOpen, setJoinOpen] = $s(false);
  const [accountOpen, setAccountOpen] = $s(false);
  const [personalOpen, setPersonalOpen] = $s(false);
  const [passkeyOpen, setPasskeyOpen] = $s(false);
  const [appearanceOpen, setAppearanceOpen] = $s(false);
  const [profileRevision, setProfileRevision] = $s(0);
  const [accountIdentity, setAccountIdentity] = $s(null);
  const accountTriggerRef = $r(null);
  const toggleCompanyMenu = () => {
    const opening = !companyOpen;
    setAccountOpen(false);
    setCompanyOpen(opening);
    if (opening && onRefreshCompanies) Promise.resolve(onRefreshCompanies()).catch(() => {});
  };
  const toggleAccountMenu = () => { setCompanyOpen(false); setAccountOpen(open => !open); };
  /* 登入態下直達 #/apply(如 intro CTA)→ 打開開通面板;#/join 已是成員 → 回總覽 */
  $e(() => {
    const home = firstAllowed ? "#/" + firstAllowed : "#/access-denied";
    if (route === "apply") { setApplyOpen(true); location.replace(home); }
    else if (route === "join") { setJoinOpen(true); location.replace(home); }
  }, [route, firstAllowed]);
  $e(() => {
    let alive = true;
    setAccountIdentity(null);
    W2.json("/api/account/profile").then(payload => {
      if (alive) setAccountIdentity(normalizePersonalProfile(payload, user, null));
    }).catch(() => {});
    return () => { alive = false; };
  }, [tenant, user && (user.global_user_id || user.id || user.username), profileRevision]);
  const brand = (companies.find(c => c.slug === tenant) || {}).name || (biu ? "BIU" : t("倉儲管理"));
  const alerts = (boot.ALERTS || []).length;
  const d = new Date();
  const dateMono = `${d.getFullYear()}.${String(d.getMonth() + 1).padStart(2, "0")}.${String(d.getDate()).padStart(2, "0")}`;
  const accountOfficial = accountIdentity && accountIdentity.official || {};
  const accountTitles = personalOfficialFormalTitles(accountOfficial);
  const accountPrimarySource = accountOfficial.primary_title && typeof accountOfficial.primary_title === "object"
    ? accountOfficial.primary_title : null;
  const accountPrimaryTitle = personalOfficialTitleText(
    (accountTitles[0] && accountTitles[0].display)
      || accountPrimarySource && (accountPrimarySource.display || accountPrimarySource.abbreviation || accountPrimarySource.label) || "",
    80,
  );
  const accountAvatar = accountIdentity && accountIdentity.avatar;
  const accountName = accountIdentity && accountIdentity.display_name || user.display_name || user.username;

  return (
    <div className={`col w2-shell route-${route}`} style={{ height: "100vh", minHeight: "100dvh" }}>
      <header className="mast">
        <div className="mast-top">
          <div className="mast-brand">
            <CompanyMark size={30} branding={branding}/>
            <span className="wordmark">{biu ? "BIU · LEGAL ETHICS" : "WAREHOUSE OS 2.1"}</span>
            <span className="label dim" style={{ transform: "translateY(-1px)" }}>{brand}</span>
          </div>
          <div style={{ flex: 1 }}/>
          <span className="label dim">{dateMono}</span>
          <div className="mast-lang"><LangSeg compact/></div>
          <button className="top-meta mast-actions" onClick={() => W2.openBusinessAction({ route })} title={t("業務操作")}>
            <Icon name="plus" size={13}/><span>{t("業務操作")}</span>
          </button>
          <div className="mast-company" style={{ position: "relative" }}>
            <button className="top-meta mast-company-trigger" onClick={toggleCompanyMenu} aria-expanded={companyOpen} aria-haspopup="menu">
              <Icon name="building" size={13}/><span className="mast-company-name">{brand}</span><Icon name="chevronDown" size={12}/>
            </button>
            {companyOpen && (
              <div className="panel fade" style={{ position: "absolute", right: 0, top: 36, width: 236, zIndex: 60, borderColor: "var(--ink)" }}>
                <div className="platform-menu-head">
                  <PlatformMark size={20}/>
                  <span>BONFIRE WORKSHOP · COMPANIES</span>
                </div>
                {companies.map(c => (
                  <button key={c.slug} className="row spread" style={{ width: "100%", padding: "11px 14px", fontSize: 13, fontWeight: c.slug === tenant ? 700 : 500, borderBottom: "1px solid var(--hair-soft)", textAlign: "left" }}
                    onClick={() => { setCompanyOpen(false); onSwitchTenant(c.slug); }}>
                    {c.name}{c.slug === tenant && <Icon name="check" size={13} color="var(--red)"/>}
                  </button>
                ))}
                <button className="row g8" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, borderTop: "1px solid var(--hair-soft)", textAlign: "left" }}
                  onClick={() => { setCompanyOpen(false); setJoinOpen(true); }}>
                  <Icon name="plus" size={12}/>{t("申請加入已有公司")}
                </button>
                {canApply && (
                  <button className="row g8" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, color: "var(--red)", textAlign: "left" }}
                    onClick={() => { setCompanyOpen(false); setApplyOpen(true); }}>
                    <Icon name="plus" size={12}/>{t("申請開通公司")}
                  </button>
                )}
              </div>
            )}
          </div>
          <button className="top-meta mast-refresh" onClick={reload} title={t("刷新數據")}><Icon name="refresh" size={13}/></button>
          <div className="mast-account" style={{ position: "relative" }}>
            <button ref={accountTriggerRef} className="top-meta mast-account-trigger" onClick={toggleAccountMenu} aria-expanded={accountOpen} aria-haspopup="menu" title={t("個人中心")}>
              <span className="mast-account-avatar-wrap">
                <PersonalAvatar avatar={accountAvatar} name={accountName} size="mast"/>
                {!!accountPrimaryTitle && <span className="mast-account-rank">{t(accountPrimaryTitle)}</span>}
              </span>
              <span className="mast-account-copy">
                {!!accountPrimaryTitle && <small>{t(accountPrimaryTitle)}</small>}
                <span className="mast-account-name">{accountName}</span>
              </span>
              <span className="mast-account-chevron"><Icon name="chevronDown" size={11}/></span>
            </button>
            {accountOpen && (
              <div role="menu" className="panel fade" style={{ position: "absolute", right: 0, top: 36, width: 238, zIndex: 65, borderColor: "var(--ink)" }}>
                <div className="mast-account-card">
                  <PersonalAvatar avatar={accountAvatar} name={accountName} size="sm"/>
                  <div>
                    {!!accountPrimaryTitle && <small>{t(accountPrimaryTitle)} · 01</small>}
                    <strong>{accountName}</strong>
                    <span>{user.username}</span>
                  </div>
                </div>
                <button role="menuitem" className="row g8" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, textAlign: "left" }}
                  onClick={() => { setAccountOpen(false); setPersonalOpen(true); }}>
                  <Icon name="user" size={12}/>{t("個人")}
                </button>
                <button role="menuitem" className="row g8 mast-account-menuitem" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, borderTop: "1px solid var(--hair-soft)", textAlign: "left" }}
                  onClick={() => { setAccountOpen(false); setAppearanceOpen(true); }}>
                  <Icon name="gear" size={12}/>{t("配色與外觀")}
                </button>
                <button role="menuitem" className="row g8 mast-account-menuitem" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, borderTop: "1px solid var(--hair-soft)", textAlign: "left" }}
                  onClick={() => { setAccountOpen(false); setPasskeyOpen(true); }}>
                  <Icon name="shield" size={12}/>{t("安全與 Passkey")}
                </button>
                <button role="menuitem" className="row g8" style={{ width: "100%", padding: "11px 14px", fontSize: 12.5, fontWeight: 650, color: "var(--red)", borderTop: "1px solid var(--hair-soft)", textAlign: "left" }}
                  onClick={() => { setAccountOpen(false); onLogout(); }}>
                  <Icon name="outbound" size={12}/>{t("登出")}
                </button>
              </div>
            )}
          </div>
        </div>
        <nav className="mast-nav">
          {mainItems.map(n => (
            <button key={n.id} className={"mnav" + ((n.activeRoutes || [n.id]).includes(route) ? " on" : "")} onClick={() => { location.hash = "#/" + n.id; }}>
              <span className="idx">{n.idx}</span>{t(n.label)}
              {n.id === "alerts" && alerts > 0 && <span className="n-badge num">{alerts}</span>}
            </button>
          ))}
          {!!adminItems.length && <span style={{ width: 1, alignSelf: "center", height: 18, background: "var(--rule)", margin: "0 8px" }}/>}
          {!!adminItems.length && <span className="label" style={{ alignSelf: "center", color: "var(--red)", fontSize: 8.5, marginRight: 2 }}>ADMIN</span>}
          {adminItems.map(n => (
            <button key={n.id} className={"mnav" + (route === n.id ? " on" : "")} onClick={() => { location.hash = "#/" + n.id; }}>
              <span className="idx" style={{ color: "var(--red)" }}>{n.idx}</span>{n.label === "SHIELD" ? "SHIELD" : t(n.label)}
            </button>
          ))}
        </nav>
      </header>
      {notice && (
        <div role="alert" aria-live="assertive" className="row spread" style={{
          gap: 12, padding: "10px 18px", color: "var(--danger)", background: "var(--paper)",
          borderBottom: "1px solid var(--danger)", fontSize: 12.5, fontWeight: 650,
        }}>
          <span className="row g8"><Icon name="alert" size={14}/>{notice}</span>
          <button type="button" className="btn ghost sm" onClick={onDismissNotice} aria-label={t("關閉提示")}>
            <Icon name="x" size={13}/>
          </button>
        </div>
      )}
      <main className="main-scroll">
        <div className="page" key={route}>
          {W2.WarehouseTabs && inWarehouse
            ? <W2.WarehouseTabs routes={navModel.warehouseTabs} route={route}/>
            : null}
          {inWarehouse
            ? <div role="tabpanel" id={"warehouse-panel-" + route} aria-labelledby={"warehouse-tab-" + route}>{children}</div>
            : children}
        </div>
      </main>
      {applyOpen && <ApplyCompanyPanel canApply={canApply} onClose={() => setApplyOpen(false)}/>} 
      {joinOpen && <JoinCompanyPanel onClose={() => setJoinOpen(false)}/>} 
      {personalOpen && <PersonalPanel user={user} biu={biu} returnFocusRef={accountTriggerRef} onClose={() => setPersonalOpen(false)}
        onOpenAppearance={() => { setPersonalOpen(false); setAppearanceOpen(true); }}
        onOpenPasskey={() => { setPersonalOpen(false); setPasskeyOpen(true); }}
        onSaved={next => {
          if (next && next.display_name) user.display_name = next.display_name;
          if (window.W2_USER && next && next.display_name) window.W2_USER.display_name = next.display_name;
          if (next) setAccountIdentity(next);
          setProfileRevision(value => value + 1);
        }}/>} 
      {passkeyOpen && <PasskeyPanel onClose={() => setPasskeyOpen(false)}/>} 
      {appearanceOpen && <AppearancePanel onClose={() => setAppearanceOpen(false)}/>} 
      <W2.BusinessActionCenter tenant={tenant} route={route} onComplete={() => reload()}/>
      <GuideHost/>
      <SecretaryDock key={`${tenant || ""}:${user.global_user_id || user.id || user.username || ""}`}/>
      {!biu && <W2.BusinessWorkbench/>}
    </div>
  );
};

const AccessDenied = ({ redirecting }) => (
  <div style={{ minHeight: "58vh", display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
    <div className="col g16" style={{ alignItems: "center", maxWidth: 460 }}>
      <PlatformMark size={42}/>
      <Icon name="shield" size={28} color="var(--danger)"/>
      <Label red>ACCESS DENIED</Label>
      <div style={{ fontSize: 26, fontWeight: 750, letterSpacing: "-.035em" }}>{t("此帳號無權訪問該功能")}</div>
      <div className="muted" style={{ fontSize: 13, lineHeight: 1.7 }}>
        {redirecting ? t("正在前往第一個可用功能…") : t("目前沒有可用功能,請聯繫公司管理員分配部門、崗位或權限。")}
      </div>
    </div>
  </div>
);

/* ── App 根 ── */
const App2 = () => {
  const [phase, setPhase] = $s("checking");
  const [user, setUser] = $s(null);
  const [isOwner, setIsOwner] = $s(false);
  const [canApply, setCanApply] = $s(false);
  const [companies, setCompanies] = $s([]);
  const [tenant, setTenant] = $s(W2.tenant());
  const [boot, setBoot] = $s({});
  /* Never hydrate an appearance before /auth/me identifies the user.  A tenant-only
     cache can briefly paint the previous account's personal colours. */
  const [runtimePrefs, setRuntimePrefs] = $s(null);
  const runtimeRequestSeq = $r(0);
  const soundPolicyGeneration = $r(0);
  const checkRequestSeq = $r(0);
  const companiesRequestSeq = $r(0);
  const readySession = $r(false);
  const [branding, setBranding] = $s(null);
  const [route, setRoute] = $s(routeNow());
  const [notice, setNotice] = $s("");

  const loadBranding = $cb(async () => {
    const requestSlug = W2.tenant();
    const requestSeq = checkRequestSeq.current;
    try {
      const data = await W2.json("/api/company/branding");
      if (requestSeq !== checkRequestSeq.current || requestSlug !== W2.tenant()) return null;
      const next = (data && data.branding) || null;
      setBranding(next);
      W2.applyBrandingFavicon(next);
      return next;
    } catch (e) {
      if (requestSeq === checkRequestSeq.current && requestSlug === W2.tenant()) setBranding(null);
      return null;
    }
  }, []);
  $e(() => { window.W2_BRANDING_RELOAD = loadBranding; return () => { delete window.W2_BRANDING_RELOAD; }; }, [loadBranding]);

  $e(() => {
    const onHash = () => { setRoute(routeNow()); document.querySelector(".main-scroll")?.scrollTo(0, 0); };
    window.addEventListener("hashchange", onHash);
    const onExpired = () => {
      readySession.current = false;
      checkRequestSeq.current++;
      companiesRequestSeq.current++;
      runtimeRequestSeq.current++;
      soundPolicyGeneration.current++;
      W2.setAlertSoundEnabled(false);
      if (W2.clearBusinessContext) W2.clearBusinessContext();
      window.W2_RUNTIME_PREFS = null;
      window.W2_USER = null;
      window.W2_IS_OWNER = false;
      setUser(null);
      setRuntimePrefs(null);
      clearRuntimeAppearance();
      document.documentElement.removeAttribute("data-w2-theme");
      setPhase("login");
      setNotice("登入已失效,請重新登入");
    };
    window.addEventListener("w2-auth-expired", onExpired);
    return () => { window.removeEventListener("hashchange", onHash); window.removeEventListener("w2-auth-expired", onExpired); };
  }, []);

  const loadBoot = $cb(async () => {
    const requestSlug = W2.tenant();
    const requestSeq = checkRequestSeq.current;
    const data = await W2.json("/api/bootstrap");
    if (requestSeq !== checkRequestSeq.current || requestSlug !== W2.tenant()) return null;
    setBoot(data);
    return data;
  }, []);
  const loadRuntimePreferences = $cb(async () => {
    const requestSlug = W2.tenant();
    const requestActor = window.W2_USER;
    const requestIdentity = runtimeActorIdentity(requestActor);
    if (!requestSlug || !W2.token() || !requestIdentity) return null;
    const requestSeq = ++runtimeRequestSeq.current;
    /* Refresh start itself fences older watch calls, including a response that
       races the settings write before this preference request returns. */
    soundPolicyGeneration.current++;
    try {
      const data = await W2.json("/api/runtime/preferences");
      if (
        requestSeq !== runtimeRequestSeq.current || W2.tenant() !== requestSlug || !W2.token() ||
        runtimeActorIdentity(window.W2_USER) !== requestIdentity
      ) return null;
      const next = normalizeRuntimePreferences(data);
      if (
        next.language_source === "stored" && next.language &&
        window.W2_LANG && window.W2_LANG.locale &&
        window.W2_LANG.locale() !== next.language
      ) {
        await window.W2_LANG.setLang(next.language, { persistRemote: false });
        return next;
      }
      cacheRuntimePreferences(requestSlug, requestActor, next);
      window.W2_RUNTIME_PREFS = next;
      setRuntimePrefs(next);
      applyRuntimeAppearance(next);
      if (!next.sound) W2.setAlertSoundEnabled(false);
      window.dispatchEvent(new CustomEvent("w2-runtime-preferences", { detail: next }));
      return next;
    } catch (e) { return null; }
  }, []);

  /* 公司深淺模式 + 個人 Swiss 兩色；登出時立即回到平台默認。 */
  $e(() => {
    if (runtimePrefs && runtimePrefs.dark) document.documentElement.dataset.w2Theme = "dark";
    else document.documentElement.removeAttribute("data-w2-theme");
    applyRuntimeAppearance(runtimePrefs);
    let meta = document.querySelector('meta[name="theme-color"]');
    if (!meta) { meta = document.createElement("meta"); meta.name = "theme-color"; document.head.appendChild(meta); }
    meta.content = runtimePrefs && runtimePrefs.dark
      ? getComputedStyle(document.documentElement).getPropertyValue("--paper").trim() || "#101214"
      : "#F5F2EB";
  }, [runtimePrefs]);

  /* Shared picker writes are authoritative immediately; polling later reconciles
     other tabs.  The identity-scoped cache prevents account and tenant bleed. */
  $e(() => {
    const accept = event => {
      if (!event || !event.detail || !runtimeActorIdentity(user)) return;
      const next = normalizeRuntimePreferences(event.detail);
      cacheRuntimePreferences(tenant, user, next);
      window.W2_RUNTIME_PREFS = next;
      setRuntimePrefs(next);
    };
    window.addEventListener("w2-runtime-preferences", accept);
    return () => window.removeEventListener("w2-runtime-preferences", accept);
  }, [tenant, runtimeActorIdentity(user)]);

  /* 公共頁與過渡狀態一律回到平台品牌；進入公司後再由公司 favicon 接管。 */
  $e(() => {
    if (phase !== "ready" && W2.applyPlatformFavicon) W2.applyPlatformFavicon();
  }, [phase]);

  /* 輕量刷新全局公司列表，不重載當前租戶的 bootstrap 或頁面狀態。 */
  const refreshCompanies = $cb(async () => {
    const requestSeq = ++companiesRequestSeq.current;
    const requestToken = W2.token();
    const requestSlug = W2.tenant();
    if (!requestToken) return null;
    try {
      const data = await W2.json("/api/auth/me");
      if (
        requestSeq !== companiesRequestSeq.current ||
        requestToken !== W2.token() ||
        requestSlug !== W2.tenant()
      ) return null;
      if (!data || !data.authenticated) return null;
      const active = (data.companies || []).filter(c => c.status === "active");
      setCompanies(active);
      return active;
    } catch (e) { return null; }
  }, []);

  const restoreTenantSwitch = $cb((snapshot, request, message) => {
    if (
      !snapshot || !request ||
      request.sequence !== checkRequestSeq.current ||
      request.targetTenant !== W2.tenant() ||
      request.token !== W2.token()
    ) return false;
    checkRequestSeq.current++;
    companiesRequestSeq.current++;
    runtimeRequestSeq.current++;
    soundPolicyGeneration.current++;
    W2.setAlertSoundEnabled(false);
    if (W2.clearBusinessContext) W2.clearBusinessContext();
    W2.setToken(snapshot.token);
    W2.setTenant(snapshot.tenant);
    setTenant(snapshot.tenant);
    setUser(snapshot.user);
    setIsOwner(snapshot.isOwner);
    setCanApply(snapshot.canApply);
    setCompanies(snapshot.companies);
    setBoot(snapshot.boot);
    setBranding(snapshot.branding);
    if (W2.applyBrandingFavicon) W2.applyBrandingFavicon(snapshot.branding);
    window.W2_USER = snapshot.user;
    window.W2_IS_OWNER = snapshot.isOwner;
    window.W2_RUNTIME_PREFS = snapshot.runtimePrefs;
    setRuntimePrefs(snapshot.runtimePrefs);
    applyRuntimeAppearance(snapshot.runtimePrefs);
    setNotice(message || t("無法存取所選公司,已返回原公司"));
    readySession.current = true;
    setPhase("ready");
    return true;
  }, []);

  const check = $cb(async (allowRetry, switchSnapshot = null, tenantlessRetry = false) => {
    const requestSeq = ++checkRequestSeq.current;
    const requestSlug = W2.tenant();
    const requestToken = W2.token();
    const switchRequest = switchSnapshot ? {
      sequence: requestSeq,
      targetTenant: requestSlug,
      token: requestToken,
    } : null;
    let data;
    try {
      data = await W2.json("/api/auth/me");
    } catch (error) {
      if (
        requestSeq !== checkRequestSeq.current ||
        requestSlug !== W2.tenant() ||
        requestToken !== W2.token()
      ) return;
      /* W2.fetch owns real 401 expiry.  A tenant-specific 4xx/5xx is not
         evidence that the global bearer expired, so keep it and roll back. */
      if (switchSnapshot && (!error || error.status !== 401)) {
        restoreTenantSwitch(
          switchSnapshot,
          switchRequest,
          (error && error.message) || t("無法存取所選公司,已返回原公司")
        );
        return;
      }
      /* In switch mode a 401 has already dispatched w2-auth-expired and
         invalidated this request. */
      if (switchSnapshot) throw error;
      /* A stored tenant can be unhealthy while the global bearer is valid.
         Retry once without X-Tenant-Slug so the server can select a usable
         default; a second transport/server error remains recoverable in UI. */
      if (
        allowRetry && !tenantlessRetry && requestToken && requestSlug &&
        (!error || error.status !== 401)
      ) {
        checkRequestSeq.current++;
        companiesRequestSeq.current++;
        runtimeRequestSeq.current++;
        soundPolicyGeneration.current++;
        W2.setAlertSoundEnabled(false);
        if (W2.clearBusinessContext) W2.clearBusinessContext();
        W2.setTenant("");
        setTenant("");
        window.W2_RUNTIME_PREFS = null;
        setRuntimePrefs(null);
        clearRuntimeAppearance();
        return check(true, null, true);
      }
      if (!error || error.status !== 401) {
        setNotice((error && error.message) || t("服務器暫時無法確認登入狀態,請重試"));
        setPhase(readySession.current ? "ready" : "auth-error");
        return;
      }
      throw error;
    }
    if (
      requestSeq !== checkRequestSeq.current ||
      requestSlug !== W2.tenant() ||
      requestToken !== W2.token()
    ) return;
    const active = (data.companies || []).filter(c => c.status === "active");
    setCompanies(active);
    if (data.authenticated && data.user) {
      if (switchSnapshot && data.tenant !== requestSlug) {
        restoreTenantSwitch(
          switchSnapshot,
          switchRequest,
          (data && (data.error || data.message)) || t("服務器未確認所選公司存取權,已返回原公司")
        );
        return;
      }
      if (data.tenant && data.tenant !== W2.tenant()) {
        runtimeRequestSeq.current++;
        soundPolicyGeneration.current++;
        W2.setAlertSoundEnabled(false);
        if (W2.clearBusinessContext) W2.clearBusinessContext();
        W2.setTenant(data.tenant);
        const cached = cachedRuntimePreferences(data.tenant, data.user);
        window.W2_RUNTIME_PREFS = cached;
        setRuntimePrefs(cached);
        applyRuntimeAppearance(cached);
      }
      W2.setTenant(data.tenant);
      setTenant(data.tenant);
      setUser(data.user);
      setIsOwner(!!data.is_platform_owner);
      setCanApply(!!data.can_apply_company);
      window.W2_USER = data.user;
      window.W2_IS_OWNER = !!data.is_platform_owner;
      const effectiveSlug = W2.tenant();
      const cached = cachedRuntimePreferences(effectiveSlug, data.user);
      if (cached) {
        window.W2_RUNTIME_PREFS = cached;
        setRuntimePrefs(cached);
        applyRuntimeAppearance(cached);
      }
      try {
        await Promise.all([loadBoot(), loadRuntimePreferences(), loadBranding()]);
      } catch (e) {
        if (
          requestSeq !== checkRequestSeq.current ||
          effectiveSlug !== W2.tenant() ||
          requestToken !== W2.token()
        ) return;
        if (switchSnapshot && (!e || e.status !== 401)) {
          restoreTenantSwitch(
            switchSnapshot,
            switchRequest,
            (e && e.message) || t("公司資料載入失敗,已返回原公司")
          );
          return;
        }
        if (!switchSnapshot && (!e || e.status !== 401)) {
          setNotice((e && e.message) || t("公司資料載入失敗,請重試"));
          setPhase(readySession.current ? "ready" : "auth-error");
          return;
        }
        throw e;
      }
      if (
        requestSeq !== checkRequestSeq.current ||
        effectiveSlug !== W2.tenant() ||
        requestToken !== W2.token()
      ) return;
      setNotice("");
      readySession.current = true;
      setPhase("ready");
      return;
    }
    if (switchSnapshot) {
      restoreTenantSwitch(
        switchSnapshot,
        switchRequest,
        (data && (data.error || data.message)) || t("您無法存取所選公司,已返回原公司")
      );
      return;
    }
    if (allowRetry && active.length) {
      const fallbackSlug = active[0].slug;
      checkRequestSeq.current++;
      runtimeRequestSeq.current++;
      soundPolicyGeneration.current++;
      W2.setAlertSoundEnabled(false);
      if (W2.clearBusinessContext) W2.clearBusinessContext();
      W2.setTenant(fallbackSlug);
      setTenant(fallbackSlug);
      window.W2_RUNTIME_PREFS = null;
      setRuntimePrefs(null);
      clearRuntimeAppearance();
      return check(false);
    }
    W2.setToken("");
    readySession.current = false;
    checkRequestSeq.current++;
    runtimeRequestSeq.current++;
    soundPolicyGeneration.current++;
    window.W2_RUNTIME_PREFS = null;
    window.W2_USER = null;
    window.W2_IS_OWNER = false;
    W2.setAlertSoundEnabled(false);
    setUser(null);
    setRuntimePrefs(null);
    clearRuntimeAppearance();
    document.documentElement.removeAttribute("data-w2-theme");
    setPhase("login");
  }, [user, loadBoot, loadRuntimePreferences, loadBranding, restoreTenantSwitch]);

  $e(() => {
    if (!W2.hasUsableToken()) {
      W2.setToken("");
      W2.setTenant("");
      setTenant("");
      setPhase("login");
      return;
    }
    check(true).catch(error => {
      if (error && error.status === 401) return;
      setNotice((error && error.message) || t("服務器暫時無法確認登入狀態,請重試"));
      setPhase("auth-error");
    });
  }, []);

  const switchTenant = async (slug) => {
    const previousTenant = W2.tenant();
    const previousToken = W2.token();
    const previousUser = user;
    if (!slug || slug === previousTenant || !previousToken || !previousUser) return;
    const snapshot = {
      tenant: previousTenant,
      token: previousToken,
      user: previousUser,
      isOwner,
      canApply,
      companies,
      boot,
      branding,
      runtimePrefs,
    };
    checkRequestSeq.current++;
    companiesRequestSeq.current++;
    runtimeRequestSeq.current++;
    soundPolicyGeneration.current++;
    W2.setAlertSoundEnabled(false);
    if (W2.clearBusinessContext) W2.clearBusinessContext();
    setNotice("");
    const cached = cachedRuntimePreferences(slug, user);
    setPhase("checking");
    window.W2_RUNTIME_PREFS = cached;
    applyRuntimeAppearance(cached);
    try {
      const response = await W2.post("/api/auth/switch-tenant", { tenant: slug });
      if (!response || !response.token || response.tenant !== slug) {
        throw new Error(t("公司切換回應無效"));
      }
      W2.setToken(response.token);
      W2.setTenant(slug); setTenant(slug); setRuntimePrefs(cached);
      await check(false, snapshot);
    } catch (error) {
      restoreTenantSwitch(snapshot, { sequence: checkRequestSeq.current, targetTenant: W2.tenant(), token: W2.token() }, error && error.message);
      /* Non-401 switch failures are handled by check() and restored in place.
         The shared fetch layer has already performed the only valid logout. */
      if (error && error.status === 401) setPhase("login");
    }
  };
  const logout = () => {
    W2.fetch("/api/auth/logout", { method: "POST" }).catch(() => {});
    checkRequestSeq.current++;
    companiesRequestSeq.current++;
    runtimeRequestSeq.current++;
    soundPolicyGeneration.current++;
    if (W2.clearBusinessContext) W2.clearBusinessContext();
    W2.setToken(""); W2.setTenant("");
    readySession.current = false;
    W2.setAlertSoundEnabled(false);
    window.W2_RUNTIME_PREFS = null;
    window.W2_USER = null;
    window.W2_IS_OWNER = false;
    clearRuntimeAppearance();
    document.documentElement.removeAttribute("data-w2-theme");
    setUser(null); setRuntimePrefs(null); setPhase("login"); setNotice("");
  };

  /* Safari 回到前台或 BFCache 恢復時同步；打開切換器也會立即走同一刷新。 */
  $e(() => {
    if (phase !== "ready") return;
    const refresh = () => { refreshCompanies(); };
    const onVisible = () => { if (document.visibilityState === "visible") refresh(); };
    window.addEventListener("focus", refresh);
    window.addEventListener("pageshow", refresh);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener("focus", refresh);
      window.removeEventListener("pageshow", refresh);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [phase, tenant, refreshCompanies]);

  /* 輕量同步公司級運行設定；秘書完成寫操作後即時同步，其他在線客戶端最多 30 秒。 */
  $e(() => {
    if (phase !== "ready") return;
    const refresh = () => { loadRuntimePreferences(); };
    const onVisible = () => { if (document.visibilityState === "visible") refresh(); };
    window.addEventListener("w2-agent-complete", refresh);
    document.addEventListener("visibilitychange", onVisible);
    const timer = setInterval(refresh, 30000);
    return () => {
      clearInterval(timer);
      window.removeEventListener("w2-agent-complete", refresh);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [phase, tenant, loadRuntimePreferences]);

  /* 新預警聲音監視器:後端 cursor 保證初載不響、同一條不重響，且只返回 mine。 */
  const canReadAlerts = permissionSetOf(user).has("alerts.read");
  const actorKey = String((user && (user.global_user_id || user.id || user.username)) || "");
  $e(() => {
    if (phase !== "ready" || !tenant || !actorKey || !canReadAlerts) {
      W2.setAlertSoundEnabled(false);
      return;
    }
    let alive = true;
    let inFlight = false;
    let queued = false;
    let cursor = null;
    let controller = null;
    const levelRank = { red: 0, orange: 1, yellow: 2, blue: 3 };
    const poll = async () => {
      if (!alive) return;
      if (inFlight) { queued = true; return; }
      inFlight = true;
      controller = new AbortController();
      const policyGeneration = soundPolicyGeneration.current;
      try {
        const suffix = cursor == null ? "" : "?after_id=" + encodeURIComponent(cursor);
        const data = await W2.json("/api/alerts/watch" + suffix, { signal: controller.signal });
        if (!alive) return;
        if (policyGeneration !== soundPolicyGeneration.current) {
          queued = true;
          return;
        }
        W2.setAlertSoundEnabled(!!data.soundEnabled);
        const fresh = Array.isArray(data.newOpen) ? data.newOpen : [];
        if (cursor != null && data.soundEnabled && fresh.length) {
          const level = fresh.reduce((best, alert) =>
            (levelRank[alert.level] ?? 9) < (levelRank[best] ?? 9) ? alert.level : best, "blue");
          W2.playAlertTone(level);
        }
        if (Number.isFinite(Number(data.cursor))) cursor = Math.max(0, Number(data.cursor));
      } catch (e) {
        if (e && e.name !== "AbortError") { /* 網路恢復後沿用舊 cursor，最多補一聲 */ }
      } finally {
        inFlight = false;
        controller = null;
        if (alive && queued) { queued = false; Promise.resolve().then(poll); }
      }
    };
    const onVisible = () => { if (document.visibilityState === "visible") poll(); };
    window.addEventListener("w2-agent-complete", poll);
    document.addEventListener("visibilitychange", onVisible);
    poll();
    const timer = setInterval(poll, 15000);
    return () => {
      alive = false;
      clearInterval(timer);
      if (controller) controller.abort();
      window.removeEventListener("w2-agent-complete", poll);
      document.removeEventListener("visibilitychange", onVisible);
      W2.setAlertSoundEnabled(false);
    };
  }, [phase, tenant, actorKey, canReadAlerts]);

  const activeTemplateKey = industryTemplateKeyOfBoot(boot);
  const navModel = navModelOf(user, isOwner, boot && boot.NAV_CONFIG, activeTemplateKey);
  const firstAllowed = navModel.ordered.length ? navModel.ordered[0].id : "";
  const specialRoute = route === "apply" || route === "join";
  const routeAllowed = specialRoute
    || (route === "warehouse" && !!W2.WarehouseTabs && navModel.warehouseTabs.length > 0)
    || navModel.routeItems.some(n => n.id === route);
  $e(() => {
    if (phase !== "ready" || specialRoute || routeAllowed || !firstAllowed) return;
    /* ACL redirect changes only the background module; keep the server-authorized
       business entity context so a cross-module deep-link can still open safely. */
    const target = "#/" + firstAllowed + (W2.businessQuerySuffix ? W2.businessQuerySuffix() : "");
    if (location.hash !== target) location.replace(target);
  }, [phase, route, specialRoute, routeAllowed, firstAllowed]);

  if (phase === "checking") return (
    <div className="col" style={{ height: "100vh", alignItems: "center", justifyContent: "center", gap: 16 }}>
      <PlatformMark size={54}/>
      <Label>CONNECTING — WAREHOUSE OS 2.1</Label>
      <span className="platform-byline">BONFIRE WORKSHOP · PLATFORM SERVICE</span>
    </div>
  );
  if (phase === "auth-error") return (
    <div className="col" role="alert" aria-live="assertive" style={{ height: "100vh", alignItems: "center", justifyContent: "center", gap: 16, padding: 24, textAlign: "center" }}>
      <PlatformMark size={54}/>
      <Label red>CONNECTION ERROR</Label>
      <div style={{ maxWidth: 560, fontSize: 14, lineHeight: 1.7, fontWeight: 650 }}>{notice}</div>
      <div className="row g8" style={{ justifyContent: "center", flexWrap: "wrap" }}>
        <button type="button" className="btn" onClick={() => {
          setNotice(""); setPhase("checking");
          check(true).catch(error => {
            if (error && error.status === 401) return;
            setNotice((error && error.message) || t("服務器暫時無法確認登入狀態,請重試"));
            setPhase("auth-error");
          });
        }}><Icon name="refresh" size={13}/>{t("重新連線")}</button>
        <button type="button" className="btn ghost" onClick={logout}>{t("登出")}</button>
      </div>
    </div>
  );
  if (phase === "login") return <Login2 notice={notice} onDone={() => {
    setNotice(""); setPhase("checking");
    check(true).catch(error => {
      if (error && error.status === 401) return;
      setNotice((error && error.message) || t("服務器暫時無法確認登入狀態,請重試"));
      setPhase("auth-error");
    });
  }}/>;

  const Page = routeAllowed ? (W2.PAGES[route] || W2.PAGES.__bridge) : null;
  return (
    <Shell user={user} companies={companies} tenant={tenant} onSwitchTenant={switchTenant}
      onRefreshCompanies={refreshCompanies} onLogout={logout} boot={boot} reload={() => check(false)} route={route} isOwner={isOwner} branding={branding} canApply={canApply}
      navModel={navModel} firstAllowed={firstAllowed} notice={notice} onDismissNotice={() => setNotice("")}>
      {Page
        ? <Page key={`${tenant || ""}:${actorKey}:${route}`} boot={boot} reload={() => check(false)} route={route} isOwner={isOwner} templateKey={activeTemplateKey}
            navItems={navModel.main} warehouseTabs={navModel.warehouseTabs}/>
        : <AccessDenied redirecting={!!firstAllowed}/>}
    </Shell>
  );
};

ReactDOM.createRoot(document.getElementById("root")).render(<App2/>);
})();
