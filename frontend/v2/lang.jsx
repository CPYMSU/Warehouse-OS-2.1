/* ============================================================
   WAREHOUSE 2.1 · lang — 三語詞庫(繁中 tw / 简中 cn / 英 en)
   默認:按時區自動(大陸→cn,台港澳→tw,其他→en);手選持久化。
   cn = 短語覆蓋 + 繁→簡字級轉換兜底(動態句子也能兜住)
   en = 完整短語詞典(缺條回退繁中)
   ============================================================ */
(() => {
const LANG_KEY = "w2_lang";
const LANGUAGE_MODE_KEY = "w2_language_mode";
const LOCALE_BY_CODE = Object.freeze({ tw: "zh-Hant", cn: "zh-Hans", en: "en" });
const CODE_BY_LOCALE = Object.freeze({
  tw: "tw", cn: "cn", en: "en",
  "zh-hant": "tw", "zh-tw": "tw", "zh-hk": "tw",
  "zh-hans": "cn", "zh-cn": "cn", "zh-sg": "cn",
});
const normalizeCode = value => CODE_BY_LOCALE[String(value || "").trim().toLowerCase()] || null;

const autoLang = () => {
  try {
    const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || "");
    if (/Shanghai|Chongqing|Harbin|Urumqi|Beijing/i.test(tz)) return "cn";
    if (/Taipei|Hong_Kong|Macau/i.test(tz)) return "tw";
    const nl = (navigator.language || "").toLowerCase();
    if (nl.indexOf("zh") === 0) return /tw|hk|mo|hant/.test(nl) ? "tw" : "cn";
    return "en";
  } catch (e) { return "tw"; }
};
const lang = () => {
  try { return normalizeCode(localStorage.getItem(LANG_KEY)) || autoLang(); }
  catch (e) { return autoLang(); }
};
const locale = () => LOCALE_BY_CODE[lang()] || "zh-Hant";
const languageMode = () => {
  try { return localStorage.getItem(LANGUAGE_MODE_KEY) === "fixed" ? "fixed" : "auto"; }
  catch (e) { return "auto"; }
};
const languageContract = () => ({ locale: locale(), language_mode: languageMode() });
const setLang = async (value, options = {}) => {
  const next = normalizeCode(value) || autoLang();
  const persistRemote = options.persistRemote !== false;
  const reload = options.reload !== false;
  try { localStorage.setItem(LANG_KEY, next); } catch (e) {}
  try {
    document.documentElement.setAttribute("data-lang", next);
    document.documentElement.setAttribute("lang", LOCALE_BY_CODE[next]);
  } catch (e) {}
  if (persistRemote && window.W2 && window.W2.token && window.W2.token()) {
    try {
      await Promise.race([
        window.W2.fetch("/api/runtime/preferences", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ language: LOCALE_BY_CODE[next], language_mode: languageMode() }),
        }),
        new Promise(resolve => setTimeout(resolve, 1500)),
      ]);
    } catch (e) {}
  }
  if (reload) location.reload();
  return next;
};

/* ── 繁→簡 字級轉換(覆蓋本應用用字)── */
const T = "倉儲庫進出預警盤點財務資產採購報表權限審計設置總覽經營治理們個東為說話對賬決定執行審計留痕護秩序門生意帳號密碼進入系統註冊冊初始化經典版錯誤處理優先級輔助決策連續監測運行當前安全線種條達標補齊無檔案保留可追溯活躍去處置實時覆蓋構成類別尚未設數據關注嚴重度排序鍵計劃讓秘書貨零關聯搜索名稱編碼型號類頁面只讀操作交給按問新增物資記錄單位鑑狀態趨勢位圖詢問領用歸還調撥發起請追蹤蹤後臺確認全程蓋章擬辦妥擴驗證們臨時歡迎夜深了早午晚上好見說吩咐咐我來幫低最需要什麼麼刷新分析逐風險方案給圓滿靜掃描第隱藏顯示兩次輸不一致填寫請稍候中鐘按幫我建續續已生成ровер藍紅黃綠燈開關閉環錄樓層貨架區域檢修班組維運維護絕緣手套接地線氣體鋼瓶複合金具帽對講機驅鳥器測距儀壓接鉗衝擊電鑽膠帶墜落帶終端頭批次歷史流轉異動明細供應商價格幣元請聯繫管理員重置找換關詞或者直接沒有很安第條給出經確后會出現這裡邊欄轉圈載入連線斷開網絡逾時稍後再試回退頂欄公司切換器登髮絲網格版式排印刊頭號規線墨紙瑞士紅巨型數字帶豎向分格編年鑑冊行藥丸反白懸停下劃線輸入框海報空心描邊塊紀律裝飾即結構同一份後端損失丟失零遷移隨時互切門面正式舊繼續跑妨礙擾亂衝突衝突退齣";
const S = "仓储库进出预警盘点财务资产采购报表权限审计设置总览经营治理们个东为说话对账决定执行审计留痕护秩序门生意帐号密码进入系统注册册初始化经典版错误处理优先级辅助决策连续监测运行当前安全线种条达标补齐无档案保留可追溯活跃去处置实时覆盖构成类别尚未设数据关注严重度排序键计划让秘书货零关联搜索名称编码型号类页面只读操作交给按问新增物资记录单位鉴状态趋势位图询问领用归还调拨发起请追踪踪后台确认全程盖章拟办妥扩验证们临时欢迎夜深了早午晚上好见说吩咐咐我来帮低最需要什么么刷新分析逐风险方案给圆满静扫描第隐藏显示两次输不一致填写请稍候中钟按帮我建续续已生成ровер蓝红黄绿灯开关闭环录楼层货架区域检修班组维运维护绝缘手套接地线气体钢瓶复合金具帽对讲机驱鸟器测距仪压接钳冲击电钻胶带坠落带终端头批次历史流转异动明细供应商价格币元请联系管理员重置找换关词或者直接没有很安第条给出经确后会出现这里边栏转圈载入连线断开网络逾时稍后再试回退顶栏公司切换器登发丝网格版式排印刊头号规线墨纸瑞士红巨型数字带竖向分格编年鉴册行药丸反白悬停下划线输入框海报空心描边块纪律装饰即结构同一份后端损失丢失零迁移随时互切门面正式旧继续跑妨碍扰乱冲突冲突退出";
const S_MAP = {};
for (let i = 0; i < T.length; i++) S_MAP[T[i]] = S[i] || T[i];
// 常用差異補充(掃描 v2 全部文案後的補漏字 + 詞條)
const EXTRA_T = "駕駛艙場評買潤與筆虧萬億項觀暫遲賣憑漲篩選範圍參約僅議擔諮餘訂閱額詳虛爭費佈間訪識軟準階負責專屬並驟況匯論戶稅禦緊湊屜則許壞刪週駐長閒業於駁將啟該鎖復樣義獲須內輕銷閘樞佔掛張適凍釋過題創語徑債齡貸撿墊攤銀淨幾術從聽縮導緯緒較響視敗飛訴髒恆輪溫觸側質暢變簡廢鏈簽穩節賃勞併譯聲談罰訟誌誰備腳頻滾曆純訊搶減雙陣職畢託撲籤協縱顏盡鑰瀏憶彙傳閃擇潔漢繞織輯槍鐵雞殼淺徵擋離際練偵診脈澱謹強摺疊島傾藝煉濾緩綴橋獨殘塢學鈷燒覺雜鮮";
const EXTRA_S = "驾驶舱场评买润与笔亏万亿项观暂迟卖凭涨筛选范围参约仅议担咨余订阅额详虚争费布间访识软准阶负责专属并骤况汇论户税御紧凑屉则许坏删周驻长闲业于驳将启该锁复样义获须内轻销闸枢占挂张适冻释过题创语径债龄贷捡垫摊银净几术从听缩导纬绪较响视败飞诉脏恒轮温触侧质畅变简废链签稳节赁劳并译声谈罚讼志谁备脚频滚历纯讯抢减双阵职毕托扑签协纵颜尽钥浏忆汇传闪择洁汉绕织辑枪铁鸡壳浅征挡离际练侦诊脉淀谨强折叠岛倾艺炼滤缓缀桥独残坞学钴烧觉杂鲜";
for (let i = 0; i < EXTRA_T.length; i++) S_MAP[EXTRA_T[i]] = EXTRA_S[i];
const CN_EXTRA = { "設置": "设置", "台賬": "台账", "臺賬": "台账", "軟體": "软件", "介面": "界面", "程式": "程序", "嗎": "吗" };
const CN = { ...CN_EXTRA };
const toSimp = (str) => {
  let out = "";
  for (const ch of String(str)) out += S_MAP[ch] || ch;
  for (const k in CN_EXTRA) out = out.split(k).join(CN_EXTRA[k]);
  return out;
};

/* ── 英文詞典(key = 繁中原文)── */
const EN = {
  // 通用
  "總覽": "Overview", "庫存": "Inventory", "入庫": "Inbound", "出庫": "Outbound",
  "預警": "Alerts", "盤點": "Stocktake", "財務": "Finance", "資產": "Assets",
  "採購": "Procurement", "地圖": "Map", "報表": "Reports", "權限": "Access",
  "審計": "Audit", "設置": "Settings", "終端": "Terminal", "倉儲管理": "Warehouse",
  "刷新": "Refresh", "刷新數據": "Refresh data", "經典版": "Classic", "登出": "Sign out", "下載": "Download",
  "秘書": "Secretary", "公司秘書": "Company Secretary", "問秘書": "Ask Secretary",
  "密鑰已簽發，AI 正在核對並準備安全卡": "Key issued · AI is verifying the result and preparing the secure card",
  "簽發結果已核對，正在送達安全卡": "Issuance verified · delivering the secure card",
  // 秘書塢:上傳 / 語音
  "識別圖片中…": "Recognizing image…", "解析文件中…": "Parsing file…", "識別失敗": "Recognition failed",
  "上傳圖片或文件:圖片走視覺識別,Excel/CSV/JSON/SQLite/文本走內置引擎解析":
    "Upload an image or file: images go through vision, Excel/CSV/JSON/SQLite/text through the built-in engine",
  "點擊說話,再點結束(說完自動發送)": "Click to talk, click again to stop (auto-sends when you finish)",
  "對話": "VOICE", "聆聽中…": "Listening…",
  "點擊退出語音對話": "Exit voice chat",
  "進入語音對話:說完自動發送、回覆自動朗讀、可隨時插話打斷":
    "Enter voice chat: auto-send when you finish, replies read aloud, barge-in anytime",
  "吩咐秘書": "Tell Secretary", "交秘書處置": "Hand to Secretary", "先問秘書": "Ask Secretary first",
  "讓秘書補貨": "Restock via Secretary", "一鍵全部補齊": "Restock all",
  "正常": "OK", "低庫存": "Low", "零庫存": "Out of stock", "借還": "Loan",
  // 保鮮生命週期(食材/生鮮)
  "生產日期": "Prod. date", "保鮮期(天)": "Shelf life (days)",
  "{n}天到期": "{n}d to expiry", "已過期{n}天": "Expired {n}d",
  "批次 · 效期(先過期先出)": "Batches · Expiry (FEFO)", "保鮮期 {n} 天": "Shelf life {n}d",
  "產 {d}": "Prod. {d}", "無到期日": "No expiry",
  "需{c}": "Needs {c}", "溫控不當": "Cold-chain risk",
  "常溫": "Ambient", "冷藏": "Chilled", "冷凍": "Frozen",
  "高危": "Critical", "重要": "Major", "留意": "Minor", "提示": "Info",
  // 登入
  "帳號": "Username", "密碼": "Password", "進入系統": "Enter system", "登入中…": "Signing in…",
  "登入已失效,請重新登入": "Session expired. Please sign in again.",
  "註冊 / 初始化 →": "Register / setup →",
  // KPI / 總覽
  "在庫物資 · SKU": "SKUs in stock", "低於安全庫存": "Below safety stock",
  "活躍預警": "Active alerts", "種": "", "條": "", "批": "",
  "共 {n} 種在管": "{n} SKUs managed", "檔案保留 · 可追溯": "Archived · traceable",
  "全部達標": "All safe", "無預警": "No alerts", "去處置 →": "Resolve →",
  "讓秘書補齊 →": "Restock via Secretary →",
  "庫存健康": "Stock health", "安全線覆蓋 · 實時": "Safety coverage · live",
  "達標率": "coverage", "達標": "Safe", "低於安全線": "Below safety",
  "分類構成": "Composition", "{n} 個自定義分類": "{n} categories", "尚未設置": "not set",
  "還沒有分類數據": "No categories yet",
  "對秘書說「幫我建物資分類」即可開始。": "Say \"create material categories\" to the Secretary to begin.",
  "需要關注": "Attention", "按缺口嚴重度排序": "sorted by shortfall",
  "夜深了": "Late night", "早安": "Good morning", "午後好": "Good afternoon", "晚上好": "Good evening",
  "倉庫一切如常。": "All quiet in the warehouse.",
  "今天有": "You have", "件事等你拍板。": "decisions waiting.",
  "看看今天倉庫和經營上有什麼需要處理的,按優先級列出來": "List what needs attention in warehouse and operations today, by priority",
  "把低於安全庫存的物資列出來,給我合併補貨方案": "List items below safety stock and propose a consolidated restock plan",
  "把這 {n} 種告急物資一次性生成合併補貨計劃": "Generate one consolidated restock plan for these {n} urgent items",
  "/ 安全": "/ safety",
  // 庫存頁
  "可用 {a} 種 · 零庫存 {z} 種 · 頁面只讀,操作交秘書 · 按": "{a} available · {z} out of stock · read-only, actions via Secretary · press",
  "搜索": "to search", "新增物資": "New item",
  "我要新增一種物資,幫我登記(名稱、分類、單位、初始庫存、安全庫存)": "Register a new item for me (name, category, unit, initial stock, safety stock)",
  "庫存現在最需要處理的是什麼?": "What needs attention most in inventory right now?",
  "搜索名稱 / 編碼 / 型號": "Search name / code / model",
  "有庫存": "In stock", "全部": "All", "全部分類": "All categories",
  "物資": "Item", "編碼 / 型號": "Code / Model", "分類": "Category",
  "庫存 / 安全": "Stock / Safety", "趨勢": "Trend", "庫位": "Location", "狀態": "Status", "交給秘書": "Secretary",
  "預警數": "alerts",
  "當前篩選下沒有物資": "No items under current filter",
  "換個關鍵詞,或直接對秘書說「幫我找◯◯」。": "Try another keyword, or just ask the Secretary to find it.",
  "當前庫存": "Current stock", "安全庫存": "Safety stock", "供應商": "Supplier",
  "近 7 期庫存趨勢": "Stock trend · last 7 periods",
  "秘書建議": "Secretary suggests",
  "低於安全庫存,建議補": "Below safety stock. Suggest restocking",
  "(含 30% 緩衝)。": "(incl. 30% buffer).",
  "直接吩咐秘書": "Tell the Secretary",
  "出庫領用": "Issue", "入庫上架": "Receive", "調撥 / 借用": "Transfer / Loan", "發起盤點": "Stocktake",
  "2.1 約定:頁面只讀,改動經秘書確認執行,全程留痕。": "2.1 contract: pages are read-only; changes run through the Secretary with full audit.",
  "出庫「{name}」,請追問數量與領用班組後執行": "Issue \"{name}\" — ask me for quantity and requesting team, then execute",
  "「{name}」到貨了,請追問數量後入庫上架": "\"{name}\" has arrived — ask me for quantity, then receive and shelve it",
  "「{name}」需要調撥或借用,請追問去向和數量後辦理": "\"{name}\" needs transfer or loan — ask me for destination and quantity, then proceed",
  "幫「{name}」安排一次盤點": "Schedule a stocktake for \"{name}\"",
  "「{name}」最近的領用和庫存走勢怎麼樣?": "How are recent issues and the stock trend for \"{name}\"?",
  "檢查「{name}」要不要補貨,需要就生成補貨申請": "Check whether \"{name}\" needs restocking; if so create a restock request",
  "「{name}」低於安全庫存,幫我生成補貨申請": "\"{name}\" is below safety stock — create a restock request",
  "搶修必備": "CRITICAL",
  // 預警頁
  "智能預警": "Alerts", "AI 掃描 + 人工拍板": "AI scans · you decide",
  "{n} 條活躍預警 · AI 掃描,人工拍板": "{n} active alerts · AI scans, you decide",
  "當前沒有活躍預警": "No active alerts",
  "全部交秘書分析": "Analyse all via Secretary",
  "把當前全部活躍預警按風險排序,逐條給我處置方案": "Rank all active alerts by risk and give me a resolution plan for each",
  "倉庫很安靜": "All quiet",
  "沒有需要處理的預警。秘書持續掃描中,有風險會第一時間出現在這裡。": "Nothing to resolve. The Secretary keeps scanning — risks will surface here first.",
  "分析並處置這條預警:{t},級別 {lv};建議「{s}」。給出方案,經我確認後執行。": "Analyse and resolve this alert: {t}, level {lv}; suggestion \"{s}\". Propose a plan and execute after my confirmation.",
  "待處理": "pending",
  // 橋接頁
  "此模塊的 2.1 版式在排期中。": "The 2.1 layout for this module is on the roadmap.",
  "功能在經典版一件不少,同一個後端,同一份數據。": "Every feature lives on in Classic — same backend, same data.",
  "在經典版打開": "Open in Classic: ",
  "關於{t}({d}):現在有什麼需要我處理的?": "About {t} ({d}): anything that needs my attention now?",
  "ERP 中樞": "ERP Hub", "採購招標": "Procurement", "審計日誌": "Audit log", "倉庫地圖": "Warehouse map", "法務": "Legal", "公司": "Companies",
  "採購到貨 · 檢修退庫 · 調撥入庫,含批次與單據": "Purchase receipts · maintenance returns · transfers, with batches & documents",
  "領用出庫 · 借用歸還 · 搶修綠色通道": "Issues · loans & returns · emergency fast lane",
  "盤點計劃 · 差異分析 · 賬實核對": "Stocktake plans · variance analysis · reconciliation",
  "預算 · 成本中心 · 採購申請 · 業財一體化": "Budgets · cost centres · purchase requests · finance integration",
  "複式總賬 · 憑證 · 三大報表 · AA 記賬": "Double-entry ledger · vouchers · statements · AA split",
  "金融資產 · 數字資產市場 · AI 評估": "Financial assets · digital asset market · AI appraisal",
  "採購流程 · 招標評審 · 供應商": "Purchasing · tender review · suppliers",
  "倉庫 GIS 定位 · 庫區與貨位可視化": "Warehouse GIS · zones & locations visualised",
  "經營報表 · 導出": "Business reports · export",
  "角色 · 審批 · 成員管理": "Roles · approvals · members",
  "全平台操作留痕回放": "Full platform audit replay",
  "系統與 AI 配置": "System & AI configuration",
  "合同 · 鋼印鏈 · 爭議": "Contracts · seal chain · disputes",
  "多公司開通 · 租戶管理": "Multi-company · tenant management",
  // 秘書塢
  "吩咐一句,我來執行": "Say it. I run it.",
  "「出庫 2 雙絕緣手套給檢修一班」": "\"Issue 2 pairs of insulated gloves to Repair Team 1\"",
  "「今天有什麼要處理的?」·「幫低庫存物資補貨」": "\"What needs handling today?\" · \"Restock low items\"",
  "吩咐秘書…": "Tell the Secretary…", "秘書工作中…": "Secretary working…",
  "執行中…": "running…", "待確認": "awaiting confirmation",
  "待確認（未寫庫）": "awaiting confirmation (no write yet)", "部分完成": "partially completed",
  "(完成,但沒有返回文字)": "(done, no text returned)",
  // 登入海報
  "連接人與 AI、知識、代碼、數據與行動。讓每一個工作區成為共同創造的起點，讓智能成為可以被調用的基礎設施。":
    "Connect people and AI, knowledge, code, data, and action. Make every workspace a starting point for shared creation—and intelligence an infrastructure you can call.",
  "人類因篝火聚集，文明因連接誕生。":
    "Humanity gathered around fire; civilization was born through connection.",
  "在數字時代，我們重新點燃一座篝火。":
    "In the digital age, we light a bonfire anew.",
};

const t = (s, vars) => {
  const L = lang();
  let out = String(s);
  if (L === "en") {
    if (EN[s] != null) out = EN[s];
    else MISSING.en.add(String(s));
  }
  if (L === "cn" && CN[s] != null) out = CN[s];
  if (vars) for (const k in vars) out = out.split("{" + k + "}").join(vars[k]);
  if (L === "cn") out = toSimp(out);
  return out;
};

// 各模塊頁文件自帶英文詞條,加載時註冊(避免並行改本文件)
const addEN = (d) => Object.assign(EN, d);
const addCN = (d) => Object.assign(CN, d);
const addCatalog = (targetLocale, messages) => {
  const code = normalizeCode(targetLocale);
  if (code === "en") addEN(messages || {});
  if (code === "cn") addCN(messages || {});
};
const MISSING = { en: new Set(), cn: new Set() };
const missingKeys = targetLocale => [...(MISSING[normalizeCode(targetLocale)] || [])];
const catalogStats = () => ({
  en: { translated: Object.keys(EN).length, missing: MISSING.en.size },
  cn: { overrides: Object.keys(CN).length, missing: MISSING.cn.size, fallback: "character-map" },
});

// 給 CSS 的語言鉤子(字體棧按語言切換)
try {
  document.documentElement.setAttribute("data-lang", lang());
  document.documentElement.setAttribute("lang", locale());
} catch (e) {}

window.W2_LANG = {
  lang, locale, setLang, t, toSimp, autoLang, addEN, addCN, addCatalog,
  languageMode, languageContract, missingKeys, catalogStats,
};
})();
