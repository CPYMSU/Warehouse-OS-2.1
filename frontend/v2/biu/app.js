(() => {
  "use strict";

  const BIU_TENANT = "biu";
  const BIU_TEMPLATE_KEY = "biu_legal_ethics_case_lab";
  const TOKEN_KEY = "warehouse_auth_token";
  const ROUTES = new Set(["home", "guide", "visitor", "roles", "lobby", "messages", "court", "archive"]);
  const ENTRY_LABELS = {
    direct: "直接選擇",
    application: "申請加入",
    exam: "需要考試",
    appointment: "內部任命",
  };
  const GUIDE_PATHS = [
    { stage: "experience", entry: "direct", label: "現在可以體驗" },
    { stage: "apply", entry: "application", label: "可以繼續申請" },
    { stage: "challenge", entry: "exam", label: "可以準備挑戰" },
  ];
  const ACTION_LABELS = {
    acknowledge: "確認受理",
    submit: "提交審查",
    triage: "完成案件分流",
    assign: "指派席位",
    start: "進入程序",
    wait: "等待補充材料",
    resume: "恢復程序",
    request_info: "請求補充材料",
    review: "開始評議",
    resolve: "形成意見",
    close: "完整性審查完成",
    reopen: "重新開啟程序",
    cancel: "終止本次程序",
    comment: "補充程序記錄",
  };
  const LOBBY_DESKS = {
    information: {
      code: "00", name: "中央服務台", secretary: "導覽秘書", english: "INFORMATION",
      displayName: "安可", manner: "溫暖、直接，擅長把複雜程序說成下一個清楚的小步驟。",
      greeting: "你好，我是安可。第一次來也不用先讀完整規則；告訴我你想看案件、加入辯論，還是先找一個合適的席位，我陪你走第一步。",
      description: "協助認識大廳、職位與下一個適合前往的櫃檯。",
      prompts: ["我是第一次來，請用三步告訴我可以怎麼參與。", "依照我的目前身份，我可以在 BIU 做哪些法律倫理工作？"],
      actions: [{ key: "guide", label: "接受職位引導" }, { key: "roles", label: "查看完整席位" }],
    },
    filing: {
      code: "01", name: "接案櫃檯", secretary: "接案秘書", english: "FILING",
      displayName: "林書言", manner: "細緻、務實，會逐項補齊來源、摘要與研究邊界。",
      greeting: "我是書言，今天由我接案。你可以先把手上的材料用自己的話說一遍；缺少的欄位我會一項項提醒，不必一次寫得完美。",
      description: "整理來源、研究邊界與必填材料，再以結構化表單建立案件。",
      prompts: ["收錄一個學術案例前，需要先核對哪些來源與倫理條件？", "請幫我判斷應該選哪一種 BIU 案件類型。"],
      actions: [{ key: "case-create", label: "建立案件" }, { key: "cases", label: "查看已收案件" }],
    },
    docket: {
      code: "02", name: "卷宗櫃檯", secretary: "卷宗秘書", english: "DOCKET",
      displayName: "周序", manner: "安靜、準確，只把你有權閱讀的卷宗線索放到桌面上。",
      greeting: "我是周序。把案件編號、題目或你記得的關鍵詞給我，我來替你理出卷宗順序；看不到的內容，我也會直接告訴你下一條可行路徑。",
      description: "查找你可閱讀的案件，選定目前要研究的卷宗。",
      prompts: ["請列出我目前可見案件的程序狀態。", "目前選定案件下一步適合先閱讀什麼？"],
      actions: [{ key: "cases", label: "展開案件目錄" }, { key: "court", label: "攜卷進入庭審場" }],
    },
    position: {
      code: "03", name: "席位櫃檯", secretary: "席位秘書", english: "POSITION",
      displayName: "顧言", manner: "坦率、鼓勵，會依玩家現有身份提出可達成的升級路線。",
      greeting: "我是顧言，負責替每個人找到能真正參與的席位。你不必先證明自己；告訴我喜歡調查、辯論、整理還是判斷，我會給你一條能立刻開始的路。",
      description: "解釋法官、律師、書記員、研究員等席位，以及申請或考試路徑。",
      prompts: ["請解釋我目前職位能負責哪些工作。", "如果我想參與案件分析，下一個適合申請的席位是什麼？"],
      actions: [{ key: "roles", label: "前往職位目錄" }, { key: "guide", label: "重新測試傾向" }],
    },
    procedure: {
      code: "04", name: "程序櫃檯", secretary: "程序秘書", english: "PROCEDURE",
      displayName: "程研", manner: "冷靜、精確，先確認節點與版本，再給出最短的下一步。",
      greeting: "我是程研。程序不需要靠猜：選一份案件，告訴我你想推進到哪裡，我會先核對目前節點，再把可以做與暫時不能做的部分分開說清楚。",
      description: "說明案件目前節點、可用程序與庭審入口；所有推進仍受版本鎖與職位權限控制。",
      prompts: ["請說明目前案件處在哪一個程序節點。", "進入庭審前，我應該核對哪些材料？"],
      actions: [{ key: "court", label: "進入庭審場" }, { key: "cases", label: "改選案件" }],
    },
    collaboration: {
      code: "05", name: "協作櫃檯", secretary: "協作秘書", english: "COLLABORATION",
      displayName: "夏禾", manner: "活潑、敏捷，喜歡把空缺席位、玩家能力與案件需要配成小隊。",
      greeting: "嗨，我是夏禾。這裡不必單打獨鬥：說說你想做的工作和能投入的時間，我幫你找正在缺人的案件工作間。",
      description: "尋找案件工作間、加入協作並前往 Warehouse 2.0 實時消息。",
      prompts: ["我如何找到適合加入的案件工作間？", "加入協作前，應先說明哪些能力與利益衝突？"],
      actions: [{ key: "spaces", label: "展開協作工作間" }, { key: "messages", label: "前往互動消息" }],
    },
    ethics: {
      code: "06", name: "倫理櫃檯", secretary: "倫理秘書", english: "ETHICS",
      displayName: "沈衡", manner: "克制、審慎，會追問利益衝突，但不把合理探索擋在門外。",
      greeting: "我是沈衡。我不會用一句「不可以」把你打發走；把想做的分析告訴我，我們一起找出身份、隱私與引用上的風險，再改成能安全完成的版本。",
      description: "檢查去標識化、利益衝突、引用與純學術邊界。",
      prompts: ["請給我一份案件去標識化檢查清單。", "分析這個案件前，哪些利益衝突需要揭露？"],
      actions: [{ key: "court", label: "帶案件進入程序" }, { key: "roles", label: "查看倫理職位" }],
    },
    archive: {
      code: "07", name: "歸檔櫃檯", secretary: "歸檔秘書", english: "ARCHIVE",
      displayName: "白止", manner: "沉著、惜字，重視每一個程序痕跡能否被下一位玩家讀懂。",
      greeting: "我是白止。流程走完不等於卷宗已經完整；把案件帶來，我會替你核對缺少的記錄，補齊後就讓它安靜地進入檔案。",
      description: "核對程序是否完整；流程完成後進入檔案，不延伸到現實執行。",
      prompts: ["一個 BIU 案件歸檔前需要哪些完整性條件？", "目前案件還缺哪些程序記錄才能歸檔？"],
      actions: [{ key: "archive", label: "前往歸檔台" }, { key: "cases", label: "核對案件" }],
    },
    research: {
      code: "08", name: "研究櫃檯", secretary: "研究秘書", english: "RESEARCH",
      displayName: "蘇問", manner: "好奇、學術化，會把直覺拆成爭點、假說與可驗證來源。",
      greeting: "我是蘇問。先不用急著得出結論，把最困惑你的地方說出來；我會和你一起把它拆成可以查證、可以反駁、也可以寫進卷宗的研究問題。",
      description: "協助整理研究問題、公開來源、爭點與可驗證引用。",
      prompts: ["請幫我把目前案件拆成可以研究的法律與倫理問題。", "如何建立不接觸真實當事人的公開來源研究計畫？"],
      actions: [{ key: "cases", label: "選擇研究案件" }, { key: "roles", label: "查看研究職位" }],
    },
  };

  const state = {
    route: "home",
    catalogReady: false,
    catalogError: "",
    roles: [],
    units: [],
    positions: [],
    templateKey: "",
    entryFilter: "all",
    roleQuery: "",
    selectedRole: null,
    user: null,
    authData: null,
    boot: null,
    sessionError: "",
    cases: [],
    caseMeta: null,
    spaces: [],
    selectedSpaceId: null,
    collaboration: null,
    messages: [],
    selectedCaseId: null,
    selectedCase: null,
    records: [],
    recordMeta: null,
    selectedRecord: null,
    globalIdentityAuthenticated: false,
    guestSeat: null,
    guestCapabilities: null,
    guestCases: [],
    guestCase: null,
    guestStep: null,
    guestFeedback: null,
    guideScreen: "intro",
    guideDefinition: null,
    guideQuestionIndex: 0,
    guideAnswers: [],
    guideProfile: null,
    guideRecommendations: [],
    examDefinition: null,
    examPosition: null,
    examQuestionIndex: 0,
    examAnswers: [],
    examResult: null,
    lobbyDesk: null,
    lobbyPlayer: { x: 50, y: 67 },
    lobbyCaseId: null,
    lobbyConversations: {},
    lobbyTranscripts: {},
    lobbyDrafts: {},
    lobbyRecovery: {},
    lobbyRunSequence: 0,
    lobbyBusy: false,
    lobbyAbortController: null,
    lobbyCaseIdempotencyKey: null,
  };
  let authGeneration = 0;
  let loginAttemptSequence = 0;
  let storageValidationSequence = 0;
  let caseSelectionSequence = 0;
  let spaceSelectionSequence = 0;
  let recordSelectionSequence = 0;
  let guideRequestSequence = 0;
  let examRequestSequence = 0;
  let lobbyMoveSequence = 0;

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const object = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const array = value => Array.isArray(value) ? value : [];
  const first = (...values) => values.find(value => value !== undefined && value !== null && value !== "");
  const text = (...values) => String(first(...values) || "").trim();
  const key = value => String(value || "").trim().toLowerCase();
  const number = value => Number.isFinite(Number(value)) ? Number(value) : 0;
  const own = (value, property) => Object.prototype.hasOwnProperty.call(object(value), property);
  const sessionChanged = error => !!error && error.name === "BiuSessionChanged";
  const h = value => String(value == null ? "" : value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
  const safeLobbyHref = rawHref => {
    const href = String(rawHref == null ? "" : rawHref).trim();
    if (!href || /[\u0000-\u001f\u007f]/.test(href) || href.startsWith("//")) return "";
    if (href.startsWith("#") || href.startsWith("/") || href.startsWith("./") || href.startsWith("../")) return href;
    try {
      const parsed = new URL(href);
      return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "";
    } catch (_) {
      return "";
    }
  };
  const renderLobbyInlineMarkdown = source => {
    const tokens = [];
    const stash = html => `\u0000${tokens.push(html) - 1}\u0000`;
    let value = String(source == null ? "" : source).replaceAll("\u0000", "");
    value = value.replace(/`([^`\n]+)`/g, (_match, code) => stash(`<code>${h(code)}</code>`));
    value = value.replace(/\[([^\]\n]+)\]\(([^)\s]+)(?:\s+["'][^"']*["'])?\)/g, (_match, label, rawHref) => {
      const href = safeLobbyHref(rawHref);
      if (!href) return stash(`<span class="lobby-link-blocked">${h(label)}</span>`);
      const external = !href.startsWith("#") && !href.startsWith("/") && !href.startsWith("./") && !href.startsWith("../");
      return stash(`<a href="${h(href)}"${external ? ' target="_blank" rel="noopener noreferrer nofollow" referrerpolicy="no-referrer"' : ""}>${h(label)}</a>`);
    });
    let html = h(value)
      .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
      .replace(/__([^_\n]+)__/g, "<strong>$1</strong>")
      .replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
    tokens.forEach((token, index) => { html = html.replaceAll(`\u0000${index}\u0000`, token); });
    return html;
  };
  const lobbyTableCells = line => String(line || "").trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(cell => cell.trim());
  const lobbyTableDivider = line => {
    const cells = lobbyTableCells(line);
    return cells.length >= 2 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
  };
  const lobbyMarkdownBlockStart = (lines, index) => {
    const line = lines[index] || "";
    return /^\s*```/.test(line)
      || /^\s{0,3}#{1,4}\s+/.test(line)
      || /^\s*>\s?/.test(line)
      || /^\s*(?:[-+*]|\d+[.)])\s+/.test(line)
      || /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)
      || (line.includes("|") && lobbyTableDivider(lines[index + 1] || ""));
  };
  const renderLobbyMarkdown = source => {
    const lines = String(source == null ? "" : source).replace(/\r\n?/g, "\n").split("\n");
    const blocks = [];
    let index = 0;
    while (index < lines.length) {
      const line = lines[index];
      if (!line.trim()) { index += 1; continue; }
      const fence = line.match(/^\s*```([a-z0-9_-]*)\s*$/i);
      if (fence) {
        const code = [];
        index += 1;
        while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) code.push(lines[index++]);
        if (index < lines.length) index += 1;
        blocks.push(`<pre><code${fence[1] ? ` data-language="${h(fence[1].toLowerCase())}"` : ""}>${h(code.join("\n"))}</code></pre>`);
        continue;
      }
      if (line.includes("|") && lobbyTableDivider(lines[index + 1] || "")) {
        const headings = lobbyTableCells(line);
        index += 2;
        const rows = [];
        while (index < lines.length && lines[index].trim() && lines[index].includes("|")) rows.push(lobbyTableCells(lines[index++]));
        blocks.push(`<div class="lobby-table-wrap"><table><thead><tr>${headings.map(cell => `<th scope="col">${renderLobbyInlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${headings.map((_heading, cellIndex) => `<td>${renderLobbyInlineMarkdown(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
        continue;
      }
      const heading = line.match(/^\s{0,3}(#{1,4})\s+(.+)$/);
      if (heading) {
        const level = Math.min(4, heading[1].length + 1);
        blocks.push(`<h${level}>${renderLobbyInlineMarkdown(heading[2])}</h${level}>`);
        index += 1;
        continue;
      }
      if (/^\s*>\s?/.test(line)) {
        const quote = [];
        while (index < lines.length && /^\s*>\s?/.test(lines[index])) quote.push(lines[index++].replace(/^\s*>\s?/, ""));
        blocks.push(`<blockquote>${quote.map(item => renderLobbyInlineMarkdown(item)).join("<br>")}</blockquote>`);
        continue;
      }
      const list = line.match(/^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/);
      if (list) {
        const ordered = !!list[2];
        const items = [];
        const pattern = ordered ? /^\s*\d+[.)]\s+(.+)$/ : /^\s*[-+*]\s+(.+)$/;
        while (index < lines.length) {
          const match = lines[index].match(pattern);
          if (!match) break;
          items.push(match[1]);
          index += 1;
        }
        const tag = ordered ? "ol" : "ul";
        blocks.push(`<${tag}>${items.map(item => `<li>${renderLobbyInlineMarkdown(item)}</li>`).join("")}</${tag}>`);
        continue;
      }
      if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        blocks.push("<hr>");
        index += 1;
        continue;
      }
      const paragraph = [line.trim()];
      index += 1;
      while (index < lines.length && lines[index].trim() && !lobbyMarkdownBlockStart(lines, index)) paragraph.push(lines[index++].trim());
      blocks.push(`<p>${paragraph.map(item => renderLobbyInlineMarkdown(item)).join("<br>")}</p>`);
    }
    return `<div class="lobby-richtext">${blocks.join("")}</div>`;
  };
  const make = (tagName, className = "", content = "") => {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    if (content !== "") element.textContent = String(content);
    return element;
  };
  const formatDate = value => {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? String(value) : new Intl.DateTimeFormat("zh-Hant", {
      year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
    }).format(date);
  };
  const token = () => {
    try { return localStorage.getItem(TOKEN_KEY) || ""; } catch (_) { return ""; }
  };
  const authFence = () => ({ token: token(), generation: authGeneration });
  const authFenceMatches = fence => !!fence
    && fence.token === token()
    && fence.generation === authGeneration;
  const invalidateSelectionRequests = () => {
    caseSelectionSequence += 1;
    spaceSelectionSequence += 1;
    recordSelectionSequence += 1;
  };
  const invalidateAuthGeneration = () => {
    authGeneration += 1;
    invalidateSelectionRequests();
  };
  const assertAuthFence = fence => {
    if (authFenceMatches(fence)) return;
    const error = new Error("身份已更新，已忽略舊請求");
    error.name = "BiuSessionChanged";
    throw error;
  };
  const setToken = value => {
    const before = token();
    try {
      if (value) localStorage.setItem(TOKEN_KEY, value);
      else localStorage.removeItem(TOKEN_KEY);
    } catch (_) {}
    if (token() !== before) invalidateAuthGeneration();
  };
  const clientRequestId = () => {
    try { if (crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID(); } catch (_) {}
    return `biu-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  };

  async function tenantFetch(path, options = {}) {
    if (typeof path !== "string" || !path.startsWith("/api/")) {
      throw new Error("BIU API path rejected");
    }
    const headers = new Headers(options.headers || {});
    headers.set("X-Tenant-Slug", BIU_TENANT);
    const requestFence = authFence();
    if (requestFence.token) headers.set("Authorization", `Bearer ${requestFence.token}`);
    const response = await fetch(path, { ...options, headers });
    assertAuthFence(requestFence);
    if (response.status === 401) {
      setToken("");
      state.globalIdentityAuthenticated = false;
      resetSensitiveState();
      connection("bad", "Warehouse 2.0 身份已失效");
    }
    return response;
  }

  async function tenantJson(path, options = {}) {
    const requestFence = authFence();
    const response = await tenantFetch(path, options);
    if (response.status !== 401) assertAuthFence(requestFence);
    const data = await response.json().catch(() => ({}));
    if (response.status !== 401) assertAuthFence(requestFence);
    if (!response.ok) {
      const error = new Error(data.error || data.message || response.statusText || "BIU request failed");
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  const tenantPost = (path, body) => tenantJson(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });

  async function tenantAgentStream(body, onEvent, { signal } = {}) {
    const streamFence = authFence();
    const response = await tenantFetch("/api/agent/run/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body || {}),
      signal,
    });
    assertAuthFence(streamFence);
    if (!response.ok || !response.body) {
      const data = await response.json().catch(() => ({}));
      assertAuthFence(streamFence);
      const error = new Error(data.error || data.message || response.statusText || "AI 秘書暫時無法回應");
      error.status = response.status;
      throw error;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalSeen = false;
    const acceptLine = line => {
      if (!line) return;
      assertAuthFence(streamFence);
      let event;
      try { event = JSON.parse(line); } catch (_) { return; }
      if (event && event.event === "error") {
        const payload = object(event.payload);
        const error = new Error(text(event.error, event.message, payload.error, payload.message, "AI 秘書串流失敗"));
        error.status = number(first(event.status, payload.status)) || undefined;
        throw error;
      }
      if (event && event.event === "final") finalSeen = true;
      onEvent(event);
    };
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      assertAuthFence(streamFence);
      buffer += decoder.decode(value, { stream: true });
      let index;
      while ((index = buffer.indexOf("\n")) >= 0) {
        const line = buffer.slice(0, index).trim();
        buffer = buffer.slice(index + 1);
        acceptLine(line);
      }
    }
    acceptLine(buffer.trim());
    if (!finalSeen) {
      const error = new Error("AI 回應中斷；操作結果未知，請先查詢案件狀態，不要重複提交");
      error.outcomeUnknown = true;
      throw error;
    }
  }

  async function publicJson(path, options = {}) {
    if (typeof path !== "string" || !path.startsWith("/api/auth/")) {
      throw new Error("BIU public API path rejected");
    }
    const response = await fetch(path, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || data.message || response.statusText || "Public catalogue unavailable");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function guestJson(path, options = {}) {
    if (typeof path !== "string" || !path.startsWith("/api/biu/guest/")) {
      throw new Error("BIU guest API path rejected");
    }
    const headers = new Headers(options.headers || {});
    headers.delete("Authorization");
    headers.set("X-Tenant-Slug", BIU_TENANT);
    if (options.body != null && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, cache: "no-store", credentials: "omit", headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || data.message || response.statusText || "BIU 訪客體驗暫時無法使用");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function guestNetworkFailure(error) {
    const message = text(error && error.message);
    return error instanceof TypeError
      || /(?:load failed|failed to fetch|networkerror|network request failed)/i.test(message);
  }

  async function guideJson(path, options = {}) {
    if (!["/api/biu/guide", "/api/biu/guide/recommend"].includes(path)) {
      throw new Error("BIU guide API path rejected");
    }
    const headers = new Headers(options.headers || {});
    headers.delete("Authorization");
    headers.set("X-Tenant-Slug", BIU_TENANT);
    if (options.body != null && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
    const response = await fetch(path, { ...options, cache: "no-store", credentials: "omit", headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || data.message || response.statusText || "BIU 職位引導暫時無法使用");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  async function quickRegistrationJson(body) {
    const response = await fetch("/api/biu/register", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-Tenant-Slug": BIU_TENANT },
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(data.error || data.message || "BIU 快速身份建立失敗");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function toast(message) {
    const region = $("#toast-region");
    const item = document.createElement("div");
    item.className = "toast";
    item.textContent = message;
    region.append(item);
    window.setTimeout(() => item.remove(), 4600);
  }

  function openLoginDialog() {
    $("#login-form-status").textContent = "";
    $("#login-dialog").showModal();
    window.setTimeout(() => $("#login-form input[name=username]").focus(), 30);
  }

  function connection(status, message) {
    const light = $("#connection-light");
    light.className = `connection-light${status ? ` ${status}` : ""}`;
    $("#connection-text").textContent = message;
  }

  function routeFromHash() {
    const route = location.hash.replace(/^#\/?/, "").split(/[?&]/)[0] || "home";
    return ROUTES.has(route) ? route : "home";
  }

  function navigate(route, options = {}) {
    const next = ROUTES.has(route) ? route : "home";
    if (location.hash !== `#${next}`) {
      location.hash = next;
      return;
    }
    activateRoute(next, { focusHeading: true, ...options });
  }

  function activateRoute(route, { preserveScroll = false, focusHeading = false } = {}) {
    state.route = route;
    $$("[data-view]").forEach(view => view.classList.toggle("is-active", view.dataset.view === route));
    $$("[data-route]").forEach(link => {
      if (link.closest(".site-nav")) {
        if (link.dataset.route === route) link.setAttribute("aria-current", "page");
        else link.removeAttribute("aria-current");
      }
    });
    $(".site-nav").classList.remove("open");
    $(".menu-button").setAttribute("aria-expanded", "false");
    if (!preserveScroll) window.scrollTo({ top: 0, behavior: "auto" });
    if (focusHeading) {
      const heading = $(`[data-view="${route}"] h1`);
      if (heading) {
        heading.setAttribute("tabindex", "-1");
        heading.focus({ preventScroll: true });
      }
    }
    if (route === "roles" && state.catalogReady) renderRoles();
    if (route === "guide") prepareGuide();
    if (route === "visitor") prepareVisitor();
    if (route === "lobby") {
      prepareLobby();
      if (state.user) loadLobby();
    }
    if (state.user && route === "messages") prepareMessages();
    if (state.user && route === "court") prepareCourt();
    if (state.user && route === "archive") loadRecords();
  }

  function templateKeyOf(boot) {
    const industry = first(object(boot).INDUSTRY_TEMPLATE, object(boot).industry_template, {});
    return text(
      typeof industry === "string" ? industry : object(industry).key,
      object(boot).INDUSTRY_TEMPLATE_KEY,
      object(boot).industry_template_key
    );
  }

  async function loadCatalog() {
    state.catalogError = "";
    state.catalogReady = false;
    connection("", "正在確認 BIU 目錄");
    try {
      const [roleData, orgData] = await Promise.all([
        publicJson(`/api/auth/roles?tenant=${encodeURIComponent(BIU_TENANT)}`),
        publicJson(`/api/auth/org-options?tenant=${encodeURIComponent(BIU_TENANT)}`),
      ]);
      if (text(orgData.template_key) !== BIU_TEMPLATE_KEY) throw new Error("BIU 目錄識別不一致，已停止載入");
      state.roles = array(roleData.roles);
      state.units = array(orgData.units);
      state.positions = array(orgData.positions);
      state.templateKey = text(orgData.template_key);
      state.catalogReady = true;
      $("#home-catalog-count").textContent = `${state.positions.length} 席位`;
      connection("ok", `BIU 目錄已連線 · ${state.positions.length} 個職位`);
      renderRoles();
      renderGuestSeats();
    } catch (error) {
      state.catalogError = error.message || "職位目錄暫時無法載入";
      $("#home-catalog-count").textContent = "目錄待連線";
      connection("bad", state.catalogError);
      renderRoles();
      renderGuestSeats();
    }
  }

  function showGuideScreen(screen) {
    const next = ["intro", "quiz", "results", "exam"].includes(screen) ? screen : "intro";
    state.guideScreen = next;
    $("#guide-intro").hidden = next !== "intro";
    $("#guide-quiz").hidden = next !== "quiz";
    $("#guide-results").hidden = next !== "results";
    $("#guide-exam").hidden = next !== "exam";
  }

  function prepareGuide() {
    showGuideScreen(state.guideScreen);
    if (state.guideScreen === "quiz" && state.guideDefinition) renderGuideQuestion();
    if (state.guideScreen === "results" && state.guideRecommendations.length) renderGuideResults();
    if (state.guideScreen === "exam" && state.examDefinition && !state.examResult) renderExamQuestion();
    if (state.guideScreen === "exam" && state.examResult) renderExamResult();
  }

  function validatePublicQuestions(rawQuestions, { minimum, maximum, binary = false, hideAnswers = false }) {
    const questions = array(rawQuestions);
    if (questions.length < minimum || questions.length > maximum) throw new Error("BIU 題目數量不符合公開契約");
    const questionIds = new Set();
    questions.forEach(questionValue => {
      const question = object(questionValue);
      const questionId = text(question.question_id);
      if (!questionId || questionIds.has(questionId) || !text(question.prompt)) throw new Error("BIU 題目識別不完整");
      questionIds.add(questionId);
      const options = array(question.options);
      if ((binary && options.length !== 2) || (!binary && options.length < 2)) throw new Error("BIU 題目選項不完整");
      const optionIds = new Set();
      options.forEach(optionValue => {
        const option = object(optionValue);
        const optionId = text(option.option_id);
        if (!optionId || optionIds.has(optionId) || !text(option.label)) throw new Error("BIU 選項識別不完整");
        optionIds.add(optionId);
        if (hideAnswers && ["correct", "answer", "score", "weight", "explanation"].some(name => own(option, name))) {
          throw new Error("公開準備評估包含不應公開的答案欄位");
        }
      });
      if (hideAnswers && ["correct", "answer", "correct_option_id", "score", "weight", "explanation"].some(name => own(question, name))) {
        throw new Error("公開準備評估包含不應公開的答案欄位");
      }
    });
    return questions;
  }

  function guideLoading(root, label) {
    root.replaceChildren();
    const loading = make("div", "guide-load-error");
    const bars = make("div", "catalog-skeleton");
    bars.setAttribute("aria-label", label);
    bars.append(make("span"), make("span"));
    loading.append(bars);
    root.append(loading);
  }

  function guideError(root, message, retry, retryLabel) {
    root.replaceChildren();
    const box = make("div", "guide-load-error");
    box.setAttribute("role", "alert");
    box.append(make("p", "", message));
    const button = make("button", "button", retryLabel);
    button.type = "button";
    button.addEventListener("click", retry);
    box.append(button);
    root.append(box);
  }

  function validateGuideDefinition(data) {
    if (text(data.mode) !== "public_read_only") throw new Error("BIU 引導未通過公開邊界檢查");
    const guide = object(data.guide);
    if (!text(guide.guide_id) || !text(guide.title) || !text(guide.disclaimer)) throw new Error("BIU 引導資料不完整");
    const axes = array(guide.axes);
    const axisIds = new Set();
    if (!axes.length) throw new Error("BIU 引導缺少工作傾向");
    axes.forEach(axisValue => {
      const axis = object(axisValue);
      const axisId = text(axis.axis_id);
      if (!axisId || axisIds.has(axisId) || !text(axis.name) || !text(axis.description)) throw new Error("BIU 工作傾向識別不完整");
      axisIds.add(axisId);
    });
    validatePublicQuestions(guide.questions, { minimum: 8, maximum: 10, binary: true });
    return guide;
  }

  async function loadGuide() {
    const sequence = ++guideRequestSequence;
    state.guideDefinition = null;
    state.guideQuestionIndex = 0;
    state.guideAnswers = [];
    state.guideProfile = null;
    state.guideRecommendations = [];
    showGuideScreen("quiz");
    const root = $("#guide-question-stage");
    guideLoading(root, "正在取得 BIU 職位引導");
    $("#guide-progress-label").textContent = "正在打開職位羅盤";
    $("#guide-previous").disabled = true;
    setGuideProgress(0);
    try {
      const data = await guideJson("/api/biu/guide", { cache: "no-store" });
      if (sequence !== guideRequestSequence) return;
      state.guideDefinition = validateGuideDefinition(data);
      renderGuideQuestion();
    } catch (error) {
      if (sequence !== guideRequestSequence) return;
      guideError(root, error.message || "職位引導暫時無法使用", loadGuide, "重新打開職位羅盤");
    }
  }

  function restartGuide() {
    guideRequestSequence += 1;
    examRequestSequence += 1;
    state.guideQuestionIndex = 0;
    state.guideAnswers = [];
    state.guideProfile = null;
    state.guideRecommendations = [];
    clearExamState();
    if (!state.guideDefinition) {
      loadGuide();
      return;
    }
    showGuideScreen("quiz");
    renderGuideQuestion();
  }

  function exitGuide() {
    guideRequestSequence += 1;
    state.guideQuestionIndex = 0;
    state.guideAnswers = [];
    state.guideProfile = null;
    state.guideRecommendations = [];
    showGuideScreen("intro");
    $("#guide-intro-title").focus({ preventScroll: true });
  }

  function setGuideProgress(value) {
    const progress = $("#guide-progress");
    const normalized = Math.max(0, Math.min(100, Number(value) || 0));
    progress.setAttribute("aria-valuenow", String(Math.round(normalized)));
    $("i", progress).style.width = `${normalized}%`;
  }

  function renderGuideQuestion() {
    const guide = object(state.guideDefinition);
    const questions = array(guide.questions);
    if (state.guideQuestionIndex >= questions.length && state.guideAnswers.length === questions.length) {
      renderGuideConfirmation();
      return;
    }
    const question = object(questions[state.guideQuestionIndex]);
    if (!text(question.question_id)) return;
    showGuideScreen("quiz");
    $("#guide-progress-label").textContent = `問題 ${state.guideQuestionIndex + 1} / ${questions.length}`;
    $("#guide-previous").disabled = state.guideQuestionIndex === 0;
    setGuideProgress((state.guideQuestionIndex / questions.length) * 100);
    const root = $("#guide-question-stage");
    root.replaceChildren();
    const card = make("article", "guide-question-card");
    card.append(make("span", "", `SCENARIO / ${String(state.guideQuestionIndex + 1).padStart(2, "0")}`));
    const title = make("h2", "", text(question.prompt));
    title.id = "guide-question-title";
    title.tabIndex = -1;
    card.append(title);
    const options = make("div", "guide-option-list");
    options.setAttribute("role", "group");
    options.setAttribute("aria-label", `問題 ${state.guideQuestionIndex + 1} 的選項`);
    array(question.options).forEach((optionValue, index) => {
      const option = object(optionValue);
      const button = make("button", "guide-option");
      button.type = "button";
      button.dataset.guideOption = text(option.option_id);
      button.append(make("span", "", String(index + 1)), make("b", "", text(option.label)));
      button.addEventListener("click", () => chooseGuideOption(text(option.option_id)));
      options.append(button);
    });
    card.append(options);
    root.append(card);
    window.setTimeout(() => title.focus({ preventScroll: true }), 20);
  }

  function chooseGuideOption(optionId) {
    const guide = object(state.guideDefinition);
    const questions = array(guide.questions);
    const question = object(questions[state.guideQuestionIndex]);
    if (!array(question.options).some(option => text(object(option).option_id) === optionId)) return;
    $$('[data-guide-option]', $("#guide-question-stage")).forEach(button => { button.disabled = true; });
    state.guideAnswers.push({ question_id: text(question.question_id), option_id: optionId });
    if (state.guideAnswers.length === questions.length) {
      state.guideQuestionIndex = questions.length;
      setGuideProgress(100);
      renderGuideConfirmation();
      return;
    }
    state.guideQuestionIndex += 1;
    renderGuideQuestion();
  }

  function renderGuideConfirmation() {
    const questions = array(object(state.guideDefinition).questions);
    if (!questions.length || state.guideAnswers.length !== questions.length) return;
    showGuideScreen("quiz");
    $("#guide-progress-label").textContent = `${questions.length} 個選擇已完成`;
    $("#guide-previous").disabled = false;
    setGuideProgress(100);
    const root = $("#guide-question-stage");
    root.replaceChildren();
    const card = make("article", "guide-confirm");
    card.append(make("span", "", "COMPASS / READY"));
    const title = make("h2", "", "你的方向已經出現。");
    title.id = "guide-question-title";
    title.tabIndex = -1;
    card.append(title, make("p", "", "你可以回看上一題並修改選擇，或讓 BIU 將本次答案與實時職位目錄對照。答案不會寫入帳號或瀏覽器歷史。"));
    const actions = make("div", "guide-actions");
    const back = make("button", "button");
    back.type = "button";
    back.textContent = "← 回看上一題";
    back.addEventListener("click", previousGuideQuestion);
    const submit = make("button", "button primary");
    submit.type = "button";
    submit.textContent = "形成三個職位推薦 →";
    submit.addEventListener("click", submitGuideAnswers);
    actions.append(back, submit);
    card.append(actions);
    root.append(card);
    window.setTimeout(() => title.focus({ preventScroll: true }), 20);
  }

  function previousGuideQuestion() {
    const questions = array(object(state.guideDefinition).questions);
    if (!questions.length || state.guideQuestionIndex <= 0) return;
    guideRequestSequence += 1;
    const nextIndex = Math.min(state.guideQuestionIndex - 1, questions.length - 1);
    state.guideQuestionIndex = nextIndex;
    state.guideAnswers = state.guideAnswers.slice(0, nextIndex);
    renderGuideQuestion();
  }

  function liveGuideRecommendations(data) {
    if (text(data.mode) !== "public_read_only") throw new Error("BIU 推薦未通過公開邊界檢查");
    const recommendations = array(data.recommendations).slice().sort((left, right) => number(left.rank) - number(right.rank));
    if (recommendations.length !== 3) throw new Error("BIU 未返回三個職位推薦");
    const seen = new Set();
    return recommendations.map((recommendationValue, index) => {
      const recommendation = object(recommendationValue);
      const expectedPath = GUIDE_PATHS[index];
      const positionCode = text(recommendation.position_code);
      const position = state.positions.find(item => text(item.position_code) === positionCode);
      const entry = key(position && position.entry_mode);
      const catalogState = key(position && position.catalog_state);
      const recommendationState = key(recommendation.catalog_state);
      const catalogStateAllowed = entry === "exam"
        ? catalogState === "locked"
        : catalogState === "public";
      if (
        number(recommendation.rank) !== index + 1
        || !positionCode
        || seen.has(positionCode)
        || !position
        || !catalogStateAllowed
        || !["direct", "application", "exam"].includes(entry)
        || text(recommendation.path_stage) !== expectedPath.stage
        || entry !== expectedPath.entry
        || recommendationState !== catalogState
        || key(recommendation.entry_mode) !== entry
        || text(recommendation.org_unit_code) !== text(position.org_unit_code)
        || !text(recommendation.reason)
      ) throw new Error("BIU 推薦與 Warehouse 2.0 實時職位不一致");
      seen.add(positionCode);
      return { recommendation, position };
    });
  }

  function validateGuideProfile(data) {
    const profile = object(data.profile);
    const axes = array(profile.axes);
    const expected = new Set(array(object(state.guideDefinition).axes).map(axis => text(object(axis).axis_id)));
    const seen = new Set();
    if (!axes.length || axes.length !== expected.size) throw new Error("BIU 推薦缺少工作傾向說明");
    axes.forEach(axisValue => {
      const axis = object(axisValue);
      const axisId = text(axis.axis_id);
      if (
        !axisId
        || !expected.has(axisId)
        || seen.has(axisId)
        || !text(axis.name)
        || !Number.isFinite(Number(axis.score))
        || number(axis.score) < 0
        || number(axis.score) > 100
        || !text(axis.summary)
      ) {
        throw new Error("BIU 工作傾向結果不完整");
      }
      seen.add(axisId);
    });
    return profile;
  }

  async function submitGuideAnswers() {
    const guide = object(state.guideDefinition);
    const questions = array(guide.questions);
    if (state.guideAnswers.length !== questions.length) return;
    const sequence = ++guideRequestSequence;
    const root = $("#guide-question-stage");
    $("#guide-previous").disabled = true;
    guideLoading(root, "正在對照 Warehouse 2.0 職位目錄");
    $("#guide-progress-label").textContent = "正在形成三個職位推薦";
    try {
      const data = await guideJson("/api/biu/guide/recommend", {
        method: "POST",
        body: JSON.stringify({ answers: state.guideAnswers.map(answer => ({ question_id: answer.question_id, option_id: answer.option_id })) }),
      });
      if (sequence !== guideRequestSequence) return;
      if (!state.catalogReady) await loadCatalog();
      if (sequence !== guideRequestSequence) return;
      if (!state.catalogReady) throw new Error("Warehouse 2.0 實時職位目錄尚未連線，無法確認推薦");
      state.guideProfile = validateGuideProfile(data);
      state.guideRecommendations = liveGuideRecommendations(data);
      renderGuideResults();
    } catch (error) {
      if (sequence !== guideRequestSequence) return;
      $("#guide-previous").disabled = false;
      guideError(root, error.message || "職位推薦暫時無法完成", submitGuideAnswers, "重新形成職位推薦");
    }
  }

  function guideFitAxisNames(recommendation) {
    return array(recommendation.fit_axes).map(value => {
      if (typeof value === "string") {
        const profileAxis = array(object(state.guideProfile).axes).find(axis => text(axis.axis_id) === value);
        return text(profileAxis && profileAxis.name, value);
      }
      return text(object(value).name, object(value).axis_name, object(value).axis_id);
    }).filter(Boolean).slice(0, 4);
  }

  function renderGuideResults() {
    if (state.guideRecommendations.length !== 3) return;
    showGuideScreen("results");
    const axes = array(object(state.guideProfile).axes).slice().sort((left, right) => number(object(right).score) - number(object(left).score));
    $("#guide-result-summary").textContent = axes.slice(0, 2).map(axis => {
      const item = object(axis);
      return text(item.name) && text(item.summary) ? `${text(item.name)}：${text(item.summary)}` : text(item.summary);
    }).filter(Boolean).join(" ") || "以下推薦已與 BIU 實時職位目錄核對。";
    const root = $("#guide-recommendations");
    root.replaceChildren();
    state.guideRecommendations.forEach(({ recommendation, position }, index) => {
      const card = make("article", "guide-recommendation");
      const header = make("header");
      header.append(make("span", "guide-rank", String(index + 1).padStart(2, "0")), make("span", "role-code", text(position.position_code)));
      card.append(header);
      card.append(make("span", "guide-path-stage", GUIDE_PATHS[index].label));
      const title = make("h3", "", text(position.position_name, position.position_code));
      title.append(make("small", "", text(position.position_name_en, position.org_unit_name_en)));
      card.append(title, make("p", "", text(position.summary, recommendation.summary)));
      const axesRoot = make("div", "guide-fit-axes");
      guideFitAxisNames(recommendation).forEach(axisName => axesRoot.append(make("span", "", axisName)));
      card.append(axesRoot);
      const reason = make("div", "guide-reason");
      reason.append(make("span", "", "WHY THIS POSITION"), make("p", "", text(recommendation.reason)));
      card.append(reason);
      const action = make("button", "button primary", key(position.entry_mode) === "exam" ? "進行入席準備評估" : "查看這個職位");
      action.type = "button";
      action.addEventListener("click", () => key(position.entry_mode) === "exam" ? openExamForPosition(position) : openRole(position));
      card.append(action);
      root.append(card);
    });
    window.setTimeout(() => $("#guide-results-title").focus({ preventScroll: true }), 20);
  }

  function clearExamState() {
    examRequestSequence += 1;
    state.examDefinition = null;
    state.examPosition = null;
    state.examQuestionIndex = 0;
    state.examAnswers = [];
    state.examResult = null;
    $("#guide-exam-progress").hidden = true;
    $("#guide-exam-stage").replaceChildren();
  }

  function validateExamDefinition(data, position) {
    if (text(data.mode) !== "public_read_only") throw new Error("準備評估未通過公開邊界檢查");
    const assessment = object(data.assessment);
    if (
      assessment.formal_qualification !== false
      || !text(assessment.assessment_id)
      || text(assessment.position_code) !== text(position.position_code)
      || !text(assessment.title)
      || !text(assessment.disclaimer)
      || !Number.isFinite(Number(assessment.threshold_percent))
      || number(assessment.threshold_percent) < 0
      || number(assessment.threshold_percent) > 100
    ) throw new Error("準備評估資料不完整或資格邊界不安全");
    const questions = validatePublicQuestions(assessment.questions, { minimum: 1, maximum: 50, hideAnswers: true });
    if (number(assessment.question_count) !== questions.length) throw new Error("準備評估題數不一致");
    return assessment;
  }

  async function openExamForPosition(position) {
    if (!position || key(position.entry_mode) !== "exam" || !["public", "locked"].includes(key(position.catalog_state))) {
      toast("此職位目前沒有公開的入席準備評估");
      return;
    }
    if ($("#role-dialog").open) $("#role-dialog").close();
    const sequence = ++examRequestSequence;
    state.examPosition = position;
    state.examDefinition = null;
    state.examQuestionIndex = 0;
    state.examAnswers = [];
    state.examResult = null;
    showGuideScreen("exam");
    navigate("guide", { preserveScroll: true });
    $("#guide-exam-position").textContent = `${text(position.position_name, position.position_code)} · 準備性評估，不是正式資格`;
    $("#guide-exam-progress").hidden = true;
    const root = $("#guide-exam-stage");
    guideLoading(root, "正在取得入席準備評估");
    try {
      const data = await guestJson(`/api/biu/guest/exams/${encodeURIComponent(position.position_code)}`, { cache: "no-store" });
      if (sequence !== examRequestSequence || state.examPosition !== position) return;
      state.examDefinition = validateExamDefinition(data, position);
      $("#guide-exam-position").textContent = `${text(position.position_name, position.position_code)} · ${text(state.examDefinition.title)} · 參考線 ${number(state.examDefinition.threshold_percent)}% · 不是正式資格`;
      state.examQuestionIndex = 0;
      state.examAnswers = [];
      $("#guide-exam-progress").hidden = false;
      renderExamQuestion();
    } catch (error) {
      if (sequence !== examRequestSequence || state.examPosition !== position) return;
      guideError(root, error.message || "入席準備評估暫時無法載入", () => openExamForPosition(position), "重新載入準備評估");
    }
  }

  function setExamProgress(value) {
    const progress = $("#guide-exam-progressbar");
    const normalized = Math.max(0, Math.min(100, Number(value) || 0));
    progress.setAttribute("aria-valuenow", String(Math.round(normalized)));
    $("i", progress).style.width = `${normalized}%`;
  }

  function renderExamQuestion() {
    const assessment = object(state.examDefinition);
    const questions = array(assessment.questions);
    const question = object(questions[state.examQuestionIndex]);
    if (!text(question.question_id)) return;
    showGuideScreen("exam");
    $("#guide-exam-progress").hidden = false;
    $("#guide-exam-progress-label").textContent = `${state.examQuestionIndex + 1} / ${questions.length}`;
    setExamProgress((state.examQuestionIndex / questions.length) * 100);
    const root = $("#guide-exam-stage");
    root.replaceChildren();
    const card = make("article", "guide-exam-card");
    card.append(make("span", "", `PREPARATORY QUESTION / ${String(state.examQuestionIndex + 1).padStart(2, "0")}`));
    const title = make("h3", "", text(question.prompt));
    title.id = "guide-exam-question-title";
    title.tabIndex = -1;
    card.append(title);
    const options = make("div", "guide-option-list");
    options.setAttribute("role", "group");
    options.setAttribute("aria-label", `準備評估第 ${state.examQuestionIndex + 1} 題選項`);
    array(question.options).forEach((optionValue, index) => {
      const option = object(optionValue);
      const button = make("button", "guide-option");
      button.type = "button";
      button.dataset.examOption = text(option.option_id);
      button.append(make("span", "", String(index + 1)), make("b", "", text(option.label)));
      button.addEventListener("click", () => chooseExamOption(text(option.option_id)));
      options.append(button);
    });
    card.append(options);
    root.append(card);
    window.setTimeout(() => title.focus({ preventScroll: true }), 20);
  }

  function chooseExamOption(optionId) {
    const assessment = object(state.examDefinition);
    const questions = array(assessment.questions);
    const question = object(questions[state.examQuestionIndex]);
    if (!array(question.options).some(option => text(object(option).option_id) === optionId)) return;
    $$('[data-exam-option]', $("#guide-exam-stage")).forEach(button => { button.disabled = true; });
    state.examAnswers.push({ question_id: text(question.question_id), option_id: optionId });
    if (state.examAnswers.length === questions.length) {
      setExamProgress(100);
      gradeExam();
      return;
    }
    state.examQuestionIndex += 1;
    renderExamQuestion();
  }

  function validateExamResult(data) {
    const definition = object(state.examDefinition);
    const resultAssessment = object(data.assessment);
    const score = object(data.score);
    const questions = array(definition.questions);
    const results = array(data.results);
    if (
      text(data.mode) !== "public_read_only"
      || resultAssessment.formal_qualification !== false
      || text(resultAssessment.assessment_id) !== text(definition.assessment_id)
      || text(resultAssessment.position_code) !== text(definition.position_code)
      || !Number.isFinite(Number(score.correct))
      || number(score.total) !== questions.length
      || !Number.isFinite(Number(score.percent))
      || number(score.percent) < 0
      || number(score.percent) > 100
      || !Number.isFinite(Number(score.threshold_percent))
      || number(score.threshold_percent) !== number(definition.threshold_percent)
      || number(score.correct) < 0
      || number(score.correct) > number(score.total)
      || typeof score.passed !== "boolean"
      || results.length !== questions.length
    ) throw new Error("準備評估結果未通過完整性檢查");
    const answerMap = new Map(state.examAnswers.map(answer => [answer.question_id, answer.option_id]));
    const seen = new Set();
    results.forEach(resultValue => {
      const result = object(resultValue);
      const questionId = text(result.question_id);
      if (
        !questionId
        || seen.has(questionId)
        || answerMap.get(questionId) !== text(result.selected_option_id)
        || typeof result.correct !== "boolean"
        || !text(result.explanation)
      ) throw new Error("準備評估逐題結果不完整");
      seen.add(questionId);
    });
    return { assessment: resultAssessment, score, results, message: text(data.message), nextAction: text(data.next_action) };
  }

  async function gradeExam() {
    const position = state.examPosition;
    const definition = object(state.examDefinition);
    const questions = array(definition.questions);
    if (!position || state.examAnswers.length !== questions.length) return;
    const sequence = ++examRequestSequence;
    const root = $("#guide-exam-stage");
    guideLoading(root, "正在批改入席準備評估");
    $("#guide-exam-progress-label").textContent = "正在批改";
    try {
      const path = `/api/biu/guest/exams/${encodeURIComponent(position.position_code)}/grade`;
      const requestOptions = {
        method: "POST",
        body: JSON.stringify({ answers: state.examAnswers.map(answer => ({ question_id: answer.question_id, option_id: answer.option_id })) }),
      };
      let data;
      try {
        data = await guestJson(path, requestOptions);
      } catch (error) {
        if (!guestNetworkFailure(error)) throw error;
        if (sequence !== examRequestSequence || state.examPosition !== position) return;
        $("#guide-exam-progress-label").textContent = "網絡波動 · 正在自動重試";
        await new Promise(resolve => window.setTimeout(resolve, 500));
        if (sequence !== examRequestSequence || state.examPosition !== position) return;
        data = await guestJson(path, requestOptions);
      }
      if (sequence !== examRequestSequence || state.examPosition !== position) return;
      state.examResult = validateExamResult(data);
      renderExamResult();
    } catch (error) {
      if (sequence !== examRequestSequence || state.examPosition !== position) return;
      const message = guestNetworkFailure(error)
        ? `網絡連接剛剛中斷；你的 ${state.examAnswers.length} 個答案仍然保留，請重新提交。`
        : error.message || "準備評估暫時無法批改";
      guideError(root, message, gradeExam, "重新提交評估答案");
    }
  }

  function examSelectedLabel(questionId, optionId) {
    const question = array(object(state.examDefinition).questions).find(item => text(object(item).question_id) === questionId);
    const option = array(object(question).options).find(item => text(object(item).option_id) === optionId);
    return text(object(option).label, optionId);
  }

  function renderExamResult() {
    const result = object(state.examResult);
    const score = object(result.score);
    if (!state.examResult || typeof score.passed !== "boolean") return;
    showGuideScreen("exam");
    $("#guide-exam-progress").hidden = true;
    const root = $("#guide-exam-stage");
    root.replaceChildren();
    const card = make("article", "guide-exam-result");
    card.dataset.passed = String(score.passed);
    const scoreLine = make("div", "guide-exam-score");
    scoreLine.append(make("b", "", `${number(score.percent)}%`), make("span", "", `${number(score.correct)} / ${number(score.total)} · 參考線 ${number(score.threshold_percent)}% · 準備性評估`));
    card.append(scoreLine);
    card.append(make("h3", "", score.passed ? "你已具備良好的入席準備。" : "再準備一輪，會更從容。"));
    card.append(make("p", "", text(result.message, "這份結果只用於幫助你準備，不是正式資格，也不會直接授予職位。")));
    const review = make("div", "guide-answer-review");
    array(result.results).forEach((resultValue, index) => {
      const answerResult = object(resultValue);
      const row = make("div", "guide-answer-row");
      row.append(make("span", "", answerResult.correct ? "✓" : String(index + 1).padStart(2, "0")));
      const copy = make("div");
      copy.append(make("b", "", examSelectedLabel(text(answerResult.question_id), text(answerResult.selected_option_id))), make("small", "", text(answerResult.explanation)));
      row.append(copy);
      review.append(row);
    });
    card.append(review);
    const actions = make("div", "guide-actions");
    const redo = make("button", "button primary", "重新進行準備評估");
    redo.type = "button";
    redo.addEventListener("click", restartExam);
    const details = make("button", "button", "查看此職位條件");
    details.type = "button";
    details.addEventListener("click", () => openRole(state.examPosition));
    actions.append(redo, details);
    card.append(actions);
    root.append(card);
    window.setTimeout(() => card.focus({ preventScroll: true }), 20);
    card.tabIndex = -1;
  }

  function restartExam() {
    examRequestSequence += 1;
    state.examQuestionIndex = 0;
    state.examAnswers = [];
    state.examResult = null;
    if (!state.examDefinition && state.examPosition) {
      openExamForPosition(state.examPosition);
      return;
    }
    renderExamQuestion();
  }

  function closeExam() {
    clearExamState();
    if (state.guideRecommendations.length === 3) renderGuideResults();
    else showGuideScreen("intro");
  }

  function handleGuideKeyboard(event) {
    if (state.route !== "guide" || event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return;
    const target = event.target;
    if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
    const index = Number(event.key) - 1;
    if (!Number.isInteger(index) || index < 0) return;
    const root = state.guideScreen === "quiz" ? $("#guide-question-stage") : state.guideScreen === "exam" ? $("#guide-exam-stage") : null;
    if (!root) return;
    const buttons = $$((state.guideScreen === "quiz" ? "[data-guide-option]" : "[data-exam-option]") + ":not(:disabled)", root);
    if (!buttons[index]) return;
    event.preventDefault();
    buttons[index].click();
  }

  const guestEnabledPosition = position => !!position
    && position.guest_enabled === true
    && position.guest_access === "public_read_only"
    && key(position.catalog_state) !== "hidden";
  const quickRegistrationPosition = position => !!position
    && position.quick_registration === true
    && key(position.entry_mode) === "direct"
    && position.selectable === true
    && key(position.catalog_state) === "public";

  function guestPositionCode(position) {
    return text(position && position.position_code, position && position.code);
  }

  function prepareVisitor() {
    if (state.guestSeat) {
      $("#guest-seat-stage").hidden = true;
      $("#guest-experience").hidden = false;
      renderGuestSession();
      renderGuestCases();
      if (!state.guestCases.length) loadGuestCases();
      return;
    }
    $("#guest-seat-stage").hidden = false;
    $("#guest-experience").hidden = true;
    renderGuestSeats();
  }

  function renderGuestSeats() {
    const root = $("#guest-seat-catalog");
    if (!root || state.guestSeat) return;
    if (!state.catalogReady) {
      root.innerHTML = state.catalogError
        ? `<div class="load-error"><p>${h(state.catalogError)}</p><button class="button" type="button" data-retry-guest-catalog>重新讀取公開席位</button></div>`
        : `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
      $("[data-retry-guest-catalog]", root)?.addEventListener("click", loadCatalog);
      return;
    }
    const positions = state.positions.filter(guestEnabledPosition);
    if (!positions.length) {
      root.innerHTML = `<div class="empty-state"><span>—</span><p>Warehouse 2.0 目前沒有啟用公開訪客席位。</p><a class="button" href="#roles" data-route="roles">查看完整職位目錄</a></div>`;
      return;
    }
    root.innerHTML = `<div class="guest-seat-grid">${positions.map(position => `<button class="guest-seat-card" type="button" data-guest-position="${h(guestPositionCode(position))}"><span>${h(guestPositionCode(position))} · ${h(position.guest_access)}</span><h3>${h(first(position.position_name, guestPositionCode(position)))}<small>${h(position.position_name_en)}</small></h3><p>${h(position.summary)}</p><b>領取此訪客席位 →</b></button>`).join("")}</div>`;
    $$("[data-guest-position]", root).forEach(button => button.addEventListener("click", () => {
      const position = state.positions.find(item => guestPositionCode(item) === button.dataset.guestPosition);
      if (position) seatAsGuest(position);
    }));
  }

  async function seatAsGuest(position) {
    if (!guestEnabledPosition(position)) return;
    const positionCode = guestPositionCode(position);
    const root = $("#guest-seat-catalog");
    root.innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    try {
      const data = await guestJson("/api/biu/guest/seat", {
        method: "POST",
        body: JSON.stringify({ position_code: positionCode }),
      });
      const session = object(data.session);
      const capabilities = object(data.capabilities);
      const returnedPosition = object(data.position);
      if (
        session.mode !== "public_read_only"
        || session.persistent !== false
        || session.credential != null
        || capabilities.public_cases !== true
        || capabilities.stateless_hearing !== true
        || capabilities.messages !== false
        || capabilities.protected_case_access !== false
        || guestPositionCode(returnedPosition) !== positionCode
      ) throw new Error("Warehouse 2.0 訪客能力回應未通過安全檢查");
      state.guestSeat = { session, position: returnedPosition };
      state.guestCapabilities = capabilities;
      state.guestCases = [];
      state.guestCase = null;
      state.guestStep = null;
      state.guestFeedback = null;
      if ($("#role-dialog").open) $("#role-dialog").close();
      navigate("visitor");
      await loadGuestCases();
    } catch (error) {
      state.guestSeat = null;
      root.innerHTML = `<div class="load-error"><p>${h(error.message || "訪客席位暫時無法領取")}</p><button class="button" type="button" data-retry-guest-seat>重新領取</button></div>`;
      $("[data-retry-guest-seat]", root)?.addEventListener("click", () => seatAsGuest(position));
    }
  }

  function renderGuestSession() {
    const position = object(state.guestSeat && state.guestSeat.position);
    $("#guest-session-position").textContent = text(position.position_name, guestPositionCode(position), "訪客席位");
    $("#guest-create-identity").textContent = guestIdentityActionLabel(position);
  }

  function guestIdentityActionLabel(seatedPosition) {
    const positionCode = guestPositionCode(seatedPosition);
    const position = state.positions.find(item => guestPositionCode(item) === positionCode) || object(seatedPosition);
    if (quickRegistrationPosition(position)) return "為此席位建立身份";
    return ({
      application: "提交此席位身份申請",
      exam: "查看此席位考試條件",
      appointment: "查看此席位任命條件",
    })[key(position.entry_mode)] || "查看正式入席方式";
  }

  function guestCasesFrom(data) {
    return array(first(object(data).cases, object(data).items, object(object(data).data).cases));
  }

  function guestCaseKey(item) {
    return text(item && item.public_case_key, item && item.case_key, item && item.key);
  }

  async function loadGuestCases() {
    if (!state.guestSeat || object(state.guestCapabilities).public_cases !== true) return;
    const root = $("#guest-case-list");
    root.innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    try {
      const data = await guestJson("/api/biu/guest/cases");
      if (data.mode !== "public_read_only") throw new Error("公開案件回應未通過訪客邊界檢查");
      state.guestCases = guestCasesFrom(data).filter(item => guestCaseKey(item));
      renderGuestCases();
    } catch (error) {
      root.innerHTML = `<div class="load-error"><p>${h(error.message || "公開案件暫時無法載入")}</p><button class="button" type="button" data-retry-guest-cases>重新讀取</button></div>`;
      $("[data-retry-guest-cases]", root)?.addEventListener("click", loadGuestCases);
    }
  }

  function renderGuestCases() {
    const root = $("#guest-case-list");
    if (!root || !state.guestSeat) return;
    if (!state.guestCases.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>Warehouse 2.0 目前沒有返回公開訪客案件。</p></div>`;
      return;
    }
    root.innerHTML = state.guestCases.map(item => `<article class="case-card"><header><span>${h(first(item.case_no, guestCaseKey(item)))}</span><span>${h(first(item.difficulty, "PUBLIC"))}</span></header><h3>${h(first(item.title, "公開案件"))}</h3><p>${h(first(item.summary, "BIU 公開材料"))}</p><div class="guest-case-meta"><span>${h(first(item.matter_track, "CASEWORK"))}</span><span>${h(number(item.estimated_minutes))} MIN</span><span>${h(number(item.step_count))} STEPS</span></div><footer><button type="button" data-guest-case="${h(guestCaseKey(item))}">打開公開卷宗 →</button></footer></article>`).join("");
    $$("[data-guest-case]", root).forEach(button => button.addEventListener("click", () => loadGuestCase(button.dataset.guestCase)));
  }

  function guestStepFrom(data, guestCase) {
    return object(first(
      object(data).current_step,
      object(data).step,
      object(guestCase).current_step,
      object(object(guestCase).hearing).current_step,
      array(object(guestCase).steps)[0]
    ));
  }

  async function loadGuestCase(caseKey) {
    if (!state.guestSeat || object(state.guestCapabilities).stateless_hearing !== true) return;
    $("#guest-hearing-stage").hidden = false;
    $("#guest-hearing-head").innerHTML = `<span class="eyebrow red">STATELESS HEARING</span><h2 id="guest-hearing-title">正在打開公開卷宗</h2><p>不會讀取正式 BIU 案件。</p>`;
    $("#guest-case-file").innerHTML = "";
    $("#guest-step-panel").innerHTML = `<div class="catalog-skeleton"><span></span><span></span></div>`;
    try {
      const data = await guestJson(`/api/biu/guest/cases/${encodeURIComponent(caseKey)}`);
      const guestCase = object(first(data.case, data));
      if (data.mode !== "public_read_only" || guestCase.fictional !== true) throw new Error("公開卷宗未通過訪客邊界檢查");
      if (guestCaseKey(guestCase) !== caseKey) throw new Error("公開案件識別不一致");
      state.guestCase = guestCase;
      state.guestStep = guestStepFrom(data, guestCase);
      state.guestFeedback = null;
      renderGuestHearing();
      $("#guest-hearing-stage").scrollIntoView({ behavior: "smooth", block: "start" });
      focusGuestStepPanel();
    } catch (error) {
      state.guestCase = null;
      state.guestStep = null;
      $("#guest-step-panel").innerHTML = `<div class="load-error"><p>${h(error.message || "公開卷宗無法載入")}</p></div>`;
    }
  }

  function guestStepId(step) {
    return text(step && step.step_id, step && step.id, step && step.key);
  }

  function guestChoices(step) {
    return array(first(object(step).choices, object(step).options));
  }

  function guestChoiceId(choice) {
    return text(choice && choice.choice_id, choice && choice.id, choice && choice.key, choice && choice.value);
  }

  function focusGuestStepPanel() {
    window.requestAnimationFrame(() => {
      const panel = $("#guest-step-panel");
      const target = $("h3", panel) || panel;
      target.setAttribute("tabindex", "-1");
      target.focus({ preventScroll: true });
      panel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  }

  function renderGuestHearing({ completed = false } = {}) {
    const guestCase = object(state.guestCase);
    const step = object(state.guestStep);
    const caseKey = guestCaseKey(guestCase);
    $("#guest-hearing-head").innerHTML = `<span class="eyebrow red">${h(first(guestCase.case_no, caseKey))} · PUBLIC</span><h2 id="guest-hearing-title">${h(first(guestCase.title, guestCase.name, "公開案件"))}</h2><p>無狀態庭審 · 重新整理後不保留進度</p>`;
    const facts = array(guestCase.facts);
    const issues = array(guestCase.issues);
    const roles = array(guestCase.roles);
    const objectives = array(guestCase.learning_objectives);
    $("#guest-case-file").innerHTML = `<span class="eyebrow">PUBLIC CASE FILE</span><h3>${h(first(guestCase.title, "公開案件"))}</h3>${guestCase.summary ? `<p>${h(guestCase.summary)}</p>` : ""}<div class="guest-case-meta"><span>${h(first(guestCase.matter_track, "CASEWORK"))}</span><span>${h(number(guestCase.estimated_minutes))} MIN</span><span>${h(number(object(guestCase.hearing).step_count))} STEPS</span></div>${facts.length ? `<section class="guest-case-section"><b>已知事實</b>${facts.map((fact, index) => `<div class="guest-case-fact"><b>${String(index + 1).padStart(2, "0")}</b> · ${h(fact)}</div>`).join("")}</section>` : ""}${issues.length ? `<section class="guest-case-section"><b>待處理爭點</b>${issues.map(issue => `<p>— ${h(issue)}</p>`).join("")}</section>` : ""}${roles.length ? `<section class="guest-case-section"><b>程序角色</b><div class="guest-case-tags">${roles.map(role => `<span title="${h(role.summary)}">${h(first(role.name, role.role_key))}</span>`).join("")}</div></section>` : ""}${objectives.length ? `<section class="guest-case-section"><b>完成後你會理解</b>${objectives.map(objective => `<p>— ${h(objective)}</p>`).join("")}</section>` : ""}`;
    if (completed || !guestStepId(step)) {
      $("#guest-step-panel").innerHTML = `<span class="eyebrow red">PROCEDURE COMPLETE</span><h3>這次訪客程序已完成。</h3>${state.guestFeedback ? `<div class="guest-feedback">${h(typeof state.guestFeedback === "object" ? first(state.guestFeedback.message, state.guestFeedback.text, state.guestFeedback.summary) : state.guestFeedback)}</div>` : ""}<p>本次選擇沒有寫入資料庫。依照此席位的正式加入方式取得身份後，才可以加入協作、發送消息並形成案件履歷。</p><button class="button primary" type="button" data-guest-upgrade-now>${h(guestIdentityActionLabel(object(state.guestSeat && state.guestSeat.position)))}</button>`;
      $("[data-guest-upgrade-now]")?.addEventListener("click", openGuestIdentity);
      return;
    }
    const choices = guestChoices(step).filter(choice => guestChoiceId(choice));
    $("#guest-step-panel").innerHTML = `<span class="eyebrow">${h(guestStepId(step))}</span><h3>${h(first(step.name, "程序選擇"))}</h3>${step.content ? `<p>${h(step.content)}</p>` : ""}<p class="guest-prompt">${h(first(step.prompt, "請選擇下一項程序動作。"))}</p>${state.guestFeedback ? `<div class="guest-feedback">${h(typeof state.guestFeedback === "object" ? first(state.guestFeedback.message, state.guestFeedback.text, state.guestFeedback.summary) : state.guestFeedback)}</div>` : ""}<div class="guest-choice-list">${choices.map(choice => `<button class="guest-choice" type="button" data-guest-choice="${h(guestChoiceId(choice))}"><b>${h(first(choice.name, guestChoiceId(choice)))}</b>${choice.content ? `<span>${h(choice.content)}</span>` : ""}</button>`).join("")}</div>`;
    $$("[data-guest-choice]", $("#guest-step-panel")).forEach(button => button.addEventListener("click", () => advanceGuestHearing(caseKey, step, button.dataset.guestChoice)));
  }

  async function advanceGuestHearing(caseKey, step, choiceId) {
    const stepId = guestStepId(step);
    if (!state.guestSeat || !caseKey || !stepId || !choiceId) return;
    const buttons = $$("[data-guest-choice]", $("#guest-step-panel"));
    buttons.forEach(button => { button.disabled = true; });
    try {
      const data = await guestJson(`/api/biu/guest/hearings/${encodeURIComponent(caseKey)}/advance`, {
        method: "POST",
        body: JSON.stringify({ step_id: stepId, choice_id: choiceId }),
      });
      if (text(data.case_key) !== caseKey || text(data.current_step) !== stepId) throw new Error("訪客程序回應識別不一致");
      state.guestFeedback = data.feedback || null;
      state.guestStep = object(data.next_step);
      renderGuestHearing({ completed: data.completed === true });
      focusGuestStepPanel();
    } catch (error) {
      $("#guest-step-panel").insertAdjacentHTML("beforeend", `<div class="guest-feedback">${h(error.message || "程序選擇暫時無法提交")}</div>`);
      buttons.forEach(button => { button.disabled = false; });
    }
  }

  function clearGuestExperience() {
    state.guestSeat = null;
    state.guestCapabilities = null;
    state.guestCases = [];
    state.guestCase = null;
    state.guestStep = null;
    state.guestFeedback = null;
    $("#guest-hearing-stage").hidden = true;
    $("#guest-case-list").innerHTML = "";
    $("#guest-case-file").innerHTML = "";
    $("#guest-step-panel").innerHTML = "";
    prepareVisitor();
  }

  function openGuestIdentity() {
    const seatedPosition = object(state.guestSeat && state.guestSeat.position);
    const positionCode = guestPositionCode(seatedPosition);
    const position = state.positions.find(item => guestPositionCode(item) === positionCode);
    if (position) openRole(position);
    else navigate("roles");
  }

  function roleMatches(position) {
    if (state.entryFilter !== "all" && key(position.entry_mode) !== state.entryFilter) return false;
    if (!state.roleQuery) return true;
    const source = [
      position.position_name, position.position_name_en, position.org_unit_name,
      position.org_unit_name_en, position.summary, position.position_code,
    ].join(" ").toLocaleLowerCase();
    return source.includes(state.roleQuery.toLocaleLowerCase());
  }

  function positionAccessBadges(position) {
    const entry = key(position.entry_mode);
    const badges = [];
    if (guestEnabledPosition(position)) badges.push({ label: "可訪客", tone: "guest" });
    if (quickRegistrationPosition(position)) badges.push({ label: "快速建立身份", tone: "" });
    else if (entry === "application") badges.push({ label: "需申請與審核", tone: "" });
    else if (entry === "exam") badges.push({ label: "需考試", tone: "" });
    else if (entry === "appointment") badges.push({ label: "內部任命", tone: "" });
    else if (entry === "direct") badges.push({ label: "直接建立身份", tone: "" });
    return badges;
  }

  function positionCardAction(position, canRequest) {
    const entry = key(position.entry_mode);
    const canVisit = guestEnabledPosition(position);
    if (entry === "exam") return canVisit ? "訪客試席 · 查看考試條件 →" : "查看考試條件 →";
    if (entry === "appointment") return canVisit ? "訪客試席 · 查看任命條件 →" : "查看任命條件 →";
    if (canVisit) return "訪客試席 · 查看正式入席方式 →";
    return text(position.cta_label, canRequest ? "留下這個席位 →" : position.lock_reason, ENTRY_LABELS[entry], "查看職位");
  }

  function renderRoles() {
    const root = $("#role-catalog");
    if (!root) return;
    if (!state.catalogReady) {
      root.innerHTML = state.catalogError
        ? `<div class="load-error" role="alert"><p>${h(state.catalogError)}</p><button class="button" type="button" data-retry-catalog>重新讀取 Warehouse 2.0 目錄</button></div>`
        : `<div class="catalog-skeleton" aria-label="正在從 Warehouse 2.0 讀取職位"><span></span><span></span><span></span><span></span><span></span><span></span></div>`;
      $("[data-retry-catalog]", root)?.addEventListener("click", loadCatalog);
      return;
    }
    const groups = state.units.map(unit => ({
      unit,
      positions: state.positions.filter(position => (
        String(position.org_unit_code || "") === String(unit.unit_code || "") && roleMatches(position)
      )),
    })).filter(group => group.positions.length);
    if (!groups.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>目前沒有符合搜尋條件的職位。請調整關鍵字或加入方式。</p></div>`;
      return;
    }
    root.innerHTML = groups.map(({ unit, positions }) => `
      <section class="role-unit" aria-labelledby="unit-${h(unit.unit_code)}">
        <header class="role-unit-head">
          <h2 id="unit-${h(unit.unit_code)}">${h(first(unit.unit_name, unit.unit_code))}</h2>
          <span>${h(first(unit.unit_name_en, unit.unit_code))} · ${positions.length}</span>
        </header>
        <div class="role-grid">
          ${positions.map(position => {
            const serverSelectable = position.selectable === true;
            const publicPosition = key(position.catalog_state) === "public";
            const entry = key(position.entry_mode);
            const canRequest = serverSelectable && publicPosition && ["direct", "application"].includes(entry);
            const badges = positionAccessBadges(position);
            const action = positionCardAction(position, canRequest);
            return `<button class="role-card" type="button" data-position-code="${h(position.position_code)}">
              <span class="role-card-top"><span class="role-code">${h(position.position_code)}</span><span class="role-tier">${h(first(position.permission_tier, "TIER —"))}</span></span>
              <h3>${h(first(position.position_name, position.position_code))}<small>${h(position.position_name_en)}</small></h3>
              <p>${h(first(position.summary, "職位說明由 BIU 目錄提供。"))}</p>
              <span class="role-access-badges">${badges.map(badge => `<i class="${h(badge.tone)}">${h(badge.label)}</i>`).join("")}</span>
              <span class="role-entry"><span>${h(ENTRY_LABELS[entry] || entry)}</span><b>${h(action)}</b></span>
            </button>`;
          }).join("")}
        </div>
      </section>
    `).join("");
    $$("[data-position-code]", root).forEach(button => button.addEventListener("click", () => {
      const position = state.positions.find(item => String(item.position_code) === button.dataset.positionCode);
      openRole(position);
    }));
  }

  function roleCanRegister(position) {
    return !!position
      && position.selectable === true
      && key(position.catalog_state) === "public"
      && ["direct", "application"].includes(key(position.entry_mode));
  }

  function openRole(position) {
    if (!position) return;
    state.selectedRole = position;
    const dialog = $("#role-dialog");
    const form = $("#role-join-form");
    form.reset();
    form.querySelectorAll("input, textarea").forEach(field => { field.disabled = false; });
    const authenticatedApplication = !!token();
    ["display_name", "username", "password", "password_confirm"].forEach(name => {
      const field = form.elements.namedItem(name);
      if (!field) return;
      field.closest("label").hidden = authenticatedApplication;
      field.required = !authenticatedApplication;
    });
    const entry = key(position.entry_mode);
    const canRegister = roleCanRegister(position);
    const canVisit = guestEnabledPosition(position);
    const quick = quickRegistrationPosition(position);
    const requirements = array(position.requirements);
    $("#selected-role-summary").innerHTML = `<div><h3>${h(first(position.position_name, position.position_code))}</h3><p>${h(first(position.org_unit_name, position.org_unit_code))} · ${h(position.summary)}</p></div><span class="role-tier">${h(first(position.permission_tier, "TIER —"))}</span>`;
    const guestBoundary = canVisit
      ? `<p class="role-guest-note"><b>訪客體驗不授予此職位。</b>你可以先處理公開材料；正式身份仍須依照上方的 ${h(ENTRY_LABELS[entry] || "加入")} 條件辦理。</p>`
      : "";
    const lockedExplanation = entry === "exam"
      ? "正式身份需完成考試條件；你可以先進行不保存結果的入席準備評估。評估不是正式資格，也不會直接授予職位。"
      : entry === "appointment"
        ? "正式身份需經 BIU 內部任命；本頁只展示條件，不會直接授予職位。"
        : text(position.lock_reason, position.cta_label, "此職位目前不能由公開入口提交。");
    $("#join-explainer").innerHTML = (canRegister
      ? `<b>${h(quick ? "快速建立身份" : ENTRY_LABELS[entry])}</b> · ${authenticatedApplication ? (quick ? "將以已驗證的 Warehouse 2.0 身份立即啟用此職位" : "將以已驗證的 Warehouse 2.0 身份提交職位申請") : (quick ? "在本頁建立身份後立即進入 BIU" : "將建立 Warehouse 2.0 全局身份並提交 BIU 職位")}；職位代碼 <code>${h(position.position_code)}</code>。${requirements.length ? `<ul>${requirements.map(item => `<li>${h(item)}</li>`).join("")}</ul>` : ""}`
      : `<b>${h(ENTRY_LABELS[entry] || entry)}</b> · ${h(lockedExplanation)}${requirements.length ? `<ul>${requirements.map(item => `<li>${h(item)}</li>`).join("")}</ul>` : ""}`) + guestBoundary;
    $("#join-fields").hidden = !canRegister;
    $("#role-submit").hidden = !canRegister;
    $("#role-submit").textContent = quick ? (authenticatedApplication ? "立即啟用此職位" : "快速建立 BIU 身份") : (authenticatedApplication ? "提交 BIU 職位申請" : "提交 BIU 身份申請");
    $("#role-guest-seat").hidden = !canVisit;
    $("#role-exam-assessment").hidden = entry !== "exam" || !["public", "locked"].includes(key(position.catalog_state));
    $("#role-form-status").textContent = "";
    dialog.showModal();
  }

  async function refreshSelectedRole(positionCode) {
    const orgData = await publicJson(`/api/auth/org-options?tenant=${encodeURIComponent(BIU_TENANT)}`);
    if (text(orgData.template_key) !== BIU_TEMPLATE_KEY) throw new Error("BIU 目錄識別不一致，提交已停止");
    const position = array(orgData.positions).find(item => String(item.position_code) === String(positionCode));
    if (!roleCanRegister(position)) throw new Error("該職位目前不可由公開入口提交，請重新選擇");
    state.units = array(orgData.units);
    state.positions = array(orgData.positions);
    return position;
  }

  async function submitRole(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const status = $("#role-form-status");
    const submit = $("#role-submit");
    if (!state.selectedRole || !roleCanRegister(state.selectedRole)) {
      status.textContent = "這個職位不能從公開入口提交。";
      return;
    }
    const fields = new FormData(form);
    const submissionFence = authFence();
    const authenticatedApplication = !!submissionFence.token;
    if (!authenticatedApplication && fields.get("password") !== fields.get("password_confirm")) {
      status.textContent = "兩次輸入的密碼不一致。";
      return;
    }
    submit.disabled = true;
    status.textContent = "正在重新確認職位目錄並提交身份……";
    try {
      assertAuthFence(submissionFence);
      const position = await refreshSelectedRole(state.selectedRole.position_code);
      assertAuthFence(submissionFence);
      const quick = quickRegistrationPosition(position);
      let data;
      let immediate = false;
      if (authenticatedApplication && quick) {
        assertAuthFence(submissionFence);
        data = await tenantPost("/api/biu/join", {
          requested_org_unit_code: position.org_unit_code,
          requested_position_code: position.position_code,
        });
        assertAuthFence(submissionFence);
        immediate = true;
      } else if (authenticatedApplication) {
        assertAuthFence(submissionFence);
        data = await tenantPost("/api/companies/join", {
          slug: BIU_TENANT,
          requested_org_unit_code: position.org_unit_code,
          requested_position_code: position.position_code,
          reason: String(fields.get("reason") || "").trim(),
          contact: String(fields.get("contact") || "").trim(),
        });
        assertAuthFence(submissionFence);
      } else if (quick) {
        assertAuthFence(submissionFence);
        data = await quickRegistrationJson({
          username: String(fields.get("username") || "").trim(),
          display_name: String(fields.get("display_name") || fields.get("username") || "").trim(),
          password: String(fields.get("password") || ""),
          requested_org_unit_code: position.org_unit_code,
          requested_position_code: position.position_code,
          contact: String(fields.get("contact") || "").trim(),
          reason: String(fields.get("reason") || "").trim(),
        });
        assertAuthFence(submissionFence);
        const issuedToken = text(data.token);
        if (!issuedToken) throw new Error("BIU 快速身份接口未返回安全憑證");
        setToken(issuedToken);
        state.globalIdentityAuthenticated = true;
        immediate = true;
      } else {
        assertAuthFence(submissionFence);
        const response = await fetch("/api/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: String(fields.get("username") || "").trim(),
            tenant_slug: BIU_TENANT,
            display_name: String(fields.get("display_name") || fields.get("username") || "").trim(),
            password: String(fields.get("password") || ""),
            department: text(position.org_unit_name, position.org_unit_code),
            contact: String(fields.get("contact") || "").trim(),
            reason: String(fields.get("reason") || "").trim(),
            requested_org_unit_code: position.org_unit_code,
            requested_position_code: position.position_code,
            requested_role_id: null,
          }),
        });
        data = await response.json().catch(() => ({}));
        assertAuthFence(submissionFence);
        if (!response.ok) throw new Error(data.error || data.message || "身份提交失敗");
      }
      if (immediate) {
        const activationFence = authFence();
        await loadSession({ required: true });
        assertAuthFence(activationFence);
        if ($("#role-dialog").open) $("#role-dialog").close();
        form.reset();
        toast("BIU 身份已啟用");
        navigate("lobby");
        return;
      }
      assertAuthFence(submissionFence);
      status.textContent = text(data.message, data.status_text, "身份已交由 BIU 處理。你可以使用相同帳號呈交身份。 ");
      form.querySelectorAll("input, textarea").forEach(field => { field.disabled = true; });
      submit.hidden = true;
      toast("BIU 身份已提交至 Warehouse 2.0");
    } catch (error) {
      if (error.status === 409 && !authenticatedApplication) {
        const username = String(fields.get("username") || "").trim();
        if ($("#role-dialog").open) $("#role-dialog").close();
        const loginUsername = $("#login-form input[name=username]");
        loginUsername.value = username;
        openLoginDialog();
        $("#login-form-status").textContent = "這個帳號已存在，請使用原密碼登入。";
        toast("帳號已存在，已為你打開身份驗證");
      } else {
        status.textContent = error.message || "身份提交失敗";
      }
    } finally {
      submit.disabled = false;
    }
  }

  async function login(event) {
    event.preventDefault();
    const attemptSequence = ++loginAttemptSequence;
    invalidateAuthGeneration();
    const loginFence = authFence();
    const form = event.currentTarget;
    const fields = new FormData(form);
    const status = $("#login-form-status");
    const submit = $("#login-submit");
    submit.disabled = true;
    status.textContent = "正在由 Warehouse 2.0 驗證身份……";
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Tenant-Slug": BIU_TENANT },
        body: JSON.stringify({ username: fields.get("username"), password: fields.get("password") }),
      });
      if (attemptSequence !== loginAttemptSequence) throw Object.assign(new Error("已有較新的身份驗證"), { name: "BiuSessionChanged" });
      assertAuthFence(loginFence);
      const payload = await response.json().catch(() => ({}));
      if (attemptSequence !== loginAttemptSequence) throw Object.assign(new Error("已有較新的身份驗證"), { name: "BiuSessionChanged" });
      assertAuthFence(loginFence);
      if (!response.ok) throw new Error(payload.error || payload.message || "身份驗證失敗");
      /* The login response can describe another default tenant.  BIU never
         authorizes from that body: only its global token is accepted here. */
      const loginToken = text(object(payload.result).token, payload.token);
      if (!loginToken) throw new Error("Warehouse 2.0 未返回身份憑證");
      assertAuthFence(loginFence);
      setToken(loginToken);
      const activationFence = authFence();
      state.globalIdentityAuthenticated = true;
      await loadSession({ required: true });
      if (attemptSequence !== loginAttemptSequence) throw Object.assign(new Error("已有較新的身份驗證"), { name: "BiuSessionChanged" });
      assertAuthFence(activationFence);
      $("#login-dialog").close();
      form.reset();
      toast("BIU 身份已驗證");
      activateRoute(state.route, { preserveScroll: true });
    } catch (error) {
      if (attemptSequence !== loginAttemptSequence || sessionChanged(error)) return;
      if (!token()) clearSession();
      status.textContent = error.message || "身份驗證失敗";
    } finally {
      if (attemptSequence === loginAttemptSequence) submit.disabled = false;
    }
  }

  function resetSensitiveViews() {
    $("#lobby-identity").innerHTML = `<span class="eyebrow">IDENTITY</span><strong>等待 Warehouse 2.0 身份</strong><small>尚未載入</small>`;
    $("#practice-name").textContent = "—";
    $("#practice-department").textContent = "—";
    $("#case-list").innerHTML = "";
    $("#space-list").innerHTML = "";
    $("#message-spaces").innerHTML = "";
    $("#conversation-head").innerHTML = `<span class="eyebrow">NO WORKSPACE SELECTED</span><h2>請先從案件大廳選擇工作間</h2>`;
    $("#message-log").innerHTML = `<div class="empty-state"><span>03</span><p>選擇一個有權讀取的工作間後，消息會在這裡顯示。</p></div>`;
    $("#message-input").value = "";
    setMessageComposer(false, "等待工作間權限");
    const caseSelector = $("#court-case-select");
    caseSelector.innerHTML = `<option value="">選擇案件</option>`;
    caseSelector.disabled = true;
    renderCourt();
    $("#case-deep-link").href = "/#/cases";
    $("#archive-list").innerHTML = "";
    clearRecordConsole();
    $("#toast-region").innerHTML = "";
    $("#role-join-form").reset();
    $("#login-form").reset();
    $("#role-form-status").textContent = "";
    $("#login-form-status").textContent = "";
    resetLobbyView();
  }

  function clearRecordConsole() {
    $("#record-console").hidden = true;
    $("#record-console-head").innerHTML = `<span class="eyebrow red">MASTER DOSSIER</span><h2 id="record-console-title">檔案程序台</h2><p>選擇一份檔案後載入服務端程序。</p>`;
    $("#record-event-list").innerHTML = "";
    $("#record-action-form").reset();
    $("#record-action-select").disabled = true;
    $("#record-action-message").disabled = true;
    $("#record-action-form button[type=submit]").disabled = true;
    $("#record-action-status").textContent = "";
  }

  function resetSensitiveState() {
    if (state.lobbyAbortController) state.lobbyAbortController.abort();
    state.lobbyRunSequence += 1;
    invalidateAuthGeneration();
    state.globalIdentityAuthenticated = !!token();
    state.user = null;
    state.authData = null;
    state.boot = null;
    state.sessionError = "";
    state.cases = [];
    state.caseMeta = null;
    state.spaces = [];
    state.selectedSpaceId = null;
    state.collaboration = null;
    state.messages = [];
    state.selectedCaseId = null;
    state.selectedCase = null;
    state.records = [];
    state.recordMeta = null;
    state.selectedRecord = null;
    state.selectedRole = null;
    state.lobbyDesk = null;
    state.lobbyPlayer = { x: 50, y: 67 };
    state.lobbyCaseId = null;
    state.lobbyConversations = {};
    state.lobbyTranscripts = {};
    state.lobbyDrafts = {};
    state.lobbyRecovery = {};
    state.lobbyBusy = false;
    state.lobbyAbortController = null;
    state.lobbyCaseIdempotencyKey = null;
    try { delete window.BIU_USER; } catch (_) { window.BIU_USER = undefined; }
    resetSensitiveViews();
    updateAuthUI();
  }

  function clearSession() { resetSensitiveState(); }

  async function loadSession({ required = false } = {}) {
    const sessionFence = authFence();
    if (!sessionFence.token) {
      clearSession();
      if (required) throw new Error("請先呈交 BIU 身份");
      return null;
    }
    state.globalIdentityAuthenticated = true;
    try {
      const me = await tenantJson("/api/auth/me", { cache: "no-store" });
      assertAuthFence(sessionFence);
      if (me.authenticated !== true || me.tenant !== BIU_TENANT) {
        throw new Error("此 Warehouse 2.0 身份尚未取得 BIU 有效成員資格");
      }
      assertAuthFence(sessionFence);
      const boot = await tenantJson("/api/bootstrap", { cache: "no-store" });
      assertAuthFence(sessionFence);
      const bootTemplate = templateKeyOf(boot);
      if (bootTemplate !== BIU_TEMPLATE_KEY) throw new Error("目前身份不屬於 BIU 工作空間");
      const nextUser = object(first(me.user, me.account, me));
      assertAuthFence(sessionFence);
      state.authData = me;
      state.user = nextUser;
      state.boot = boot;
      state.globalIdentityAuthenticated = true;
      state.sessionError = "";
      window.BIU_USER = state.user;
      updateAuthUI();
      connection("ok", `BIU 已連線 · ${text(state.user.display_name, state.user.username, "已驗證身份")}`);
      return state.user;
    } catch (error) {
      if (sessionChanged(error) || !authFenceMatches(sessionFence)) {
        if (required) throw error;
        return null;
      }
      const sessionError = error.message || "BIU 身份無法讀取";
      resetSensitiveState();
      state.sessionError = sessionError;
      if (error.status === 401) connection("bad", "Warehouse 2.0 身份已失效");
      else connection("bad", state.sessionError);
      if (required) throw error;
      return null;
    }
  }

  function userRoles() {
    return array(first(state.user && state.user.roles, state.authData && state.authData.roles));
  }

  function lobbyPlayerProfile() {
    const user = object(state.user);
    const organization = object(user.organization);
    const roleNames = userRoles().map(roleValue => {
      if (typeof roleValue === "string") return roleValue.trim();
      const role = object(roleValue);
      return text(role.position_name, role.role_name, role.display_name, role.name, role.code);
    }).filter(Boolean);
    return {
      name: text(user.display_name, user.name, user.username, "BIU 參與者"),
      role: text(organization.position_name, organization.role_name, user.position_name, user.role_name, user.position, roleNames[0], "一般參與者"),
      department: text(organization.unit_name, organization.department_name, user.department, user.org_unit_name, user.unit_name, "BIU"),
    };
  }

  function updateAuthUI() {
    const authenticated = !!state.user;
    $$("[data-auth-gate]").forEach(gate => gate.hidden = authenticated);
    $$(".auth-content").forEach(content => content.hidden = !authenticated);
    const headerName = $("#header-identity-name");
    const headerButton = $("#header-auth-button");
    if (!authenticated) {
      headerName.textContent = state.globalIdentityAuthenticated ? "Warehouse 身份已驗證" : "訪客";
      headerButton.textContent = state.globalIdentityAuthenticated ? "退出身份" : "呈交身份";
      if (state.lobbyDesk) renderLobbyDeskPanel();
      return;
    }
    const profile = lobbyPlayerProfile();
    const name = profile.name;
    const department = profile.department;
    $("#lobby-identity").innerHTML = `<span class="eyebrow">IDENTITY / VERIFIED</span><strong>${h(name)}</strong><small>${h(department)}</small>`;
    $("#practice-name").textContent = name;
    $("#practice-department").textContent = department;
    headerName.textContent = name;
    headerButton.textContent = "退出身份";
    if (state.lobbyDesk) renderLobbyDeskPanel();
  }

  async function logout() {
    try { await tenantFetch("/api/auth/logout", { method: "POST" }); } catch (_) {}
    setToken("");
    state.globalIdentityAuthenticated = false;
    resetSensitiveState();
    connection(state.catalogReady ? "ok" : "", state.catalogReady ? `BIU 目錄已連線 · ${state.positions.length} 個職位` : "正在確認 BIU 目錄");
    toast("身份已退出");
  }

  async function handleTokenStorage(event) {
    if (event.key !== TOKEN_KEY || (event.storageArea && event.storageArea !== localStorage)) return;
    invalidateAuthGeneration();
    const sequence = ++storageValidationSequence;
    resetSensitiveState();
    if (!event.newValue) {
      state.globalIdentityAuthenticated = false;
      updateAuthUI();
      connection(state.catalogReady ? "ok" : "", state.catalogReady ? `BIU 目錄已連線 · ${state.positions.length} 個職位` : "正在確認 BIU 目錄");
      return;
    }
    state.globalIdentityAuthenticated = true;
    updateAuthUI();
    connection("", "Warehouse 2.0 身份已變更 · 正在重新驗證 BIU");
    const user = await loadSession();
    if (sequence !== storageValidationSequence || event.newValue !== token()) return;
    if (user) activateRoute(state.route, { preserveScroll: true });
  }

  function lobbyDeskOf(deskId = state.lobbyDesk) {
    return LOBBY_DESKS[key(deskId)] || null;
  }

  function resetLobbyView() {
    lobbyMoveSequence += 1;
    const shell = $("#lobby-shell");
    const panel = $("#lobby-desk-panel");
    const player = $("#lobby-player");
    if (shell) shell.classList.remove("has-panel");
    if (panel) panel.hidden = true;
    if (player) {
      player.style.setProperty("--player-x", "50%");
      player.style.setProperty("--player-y", "67%");
      player.setAttribute("aria-label", "你的方塊，目前在大廳中央");
    }
    $$("[data-lobby-desk]").forEach(button => button.setAttribute("aria-pressed", "false"));
    [$("#lobby-route-x"), $("#lobby-route-y")].forEach(route => {
      if (!route) return;
      route.classList.remove("visible");
      route.removeAttribute("style");
    });
    if ($("#lobby-status")) $("#lobby-status").textContent = "選擇任一櫃檯開始移動";
    if ($("#lobby-case-create")) $("#lobby-case-create").hidden = true;
    if ($("#lobby-case-drawer")) $("#lobby-case-drawer").hidden = true;
    if ($("#lobby-space-drawer")) $("#lobby-space-drawer").hidden = true;
    $("#lobby-case-create-form")?.reset();
    if ($("#lobby-case-create-status")) $("#lobby-case-create-status").textContent = "";
  }

  function prepareLobby() {
    const player = $("#lobby-player");
    if (player) {
      player.style.setProperty("--player-x", `${number(state.lobbyPlayer.x) || 50}%`);
      player.style.setProperty("--player-y", `${number(state.lobbyPlayer.y) || 67}%`);
    }
    populateLobbyCaseSelector();
    if (state.lobbyDesk && lobbyDeskOf()) {
      $("#lobby-shell").classList.add("has-panel");
      $("#lobby-desk-panel").hidden = false;
      renderLobbyDeskPanel();
    }
  }

  function moveLobbyPlayerToDesk(deskId) {
    const button = $(`[data-lobby-desk="${deskId}"]`);
    const player = $("#lobby-player");
    const routeX = $("#lobby-route-x");
    const routeY = $("#lobby-route-y");
    const desk = lobbyDeskOf(deskId);
    if (!button || !player || !routeX || !routeY || !desk) return Promise.resolve(false);
    const moveSequence = ++lobbyMoveSequence;
    const startX = number(state.lobbyPlayer.x) || 50;
    const startY = number(state.lobbyPlayer.y) || 67;
    const targetX = number(button.dataset.x);
    const targetY = number(button.dataset.y);
    routeX.style.left = `${Math.min(startX, targetX)}%`;
    routeX.style.top = `${startY}%`;
    routeX.style.width = `${Math.abs(targetX - startX)}%`;
    routeY.style.left = `${targetX}%`;
    routeY.style.top = `${Math.min(startY, targetY)}%`;
    routeY.style.height = `${Math.abs(targetY - startY)}%`;
    routeX.classList.add("visible");
    routeY.classList.add("visible");
    $("#lobby-status").textContent = `前往 ${desk.code} · ${desk.name}`;
    const reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      player.style.setProperty("--player-x", `${targetX}%`);
      player.style.setProperty("--player-y", `${targetY}%`);
      state.lobbyPlayer = { x: targetX, y: targetY };
      player.setAttribute("aria-label", `你的方塊，已抵達${desk.name}`);
      $("#lobby-status").textContent = `已抵達 ${desk.code} · ${desk.name}`;
      return Promise.resolve(true);
    }
    player.style.setProperty("--player-x", `${targetX}%`);
    return new Promise(resolve => {
      window.setTimeout(() => {
        if (moveSequence !== lobbyMoveSequence) { resolve(false); return; }
        player.style.setProperty("--player-y", `${targetY}%`);
        window.setTimeout(() => {
          if (moveSequence !== lobbyMoveSequence) { resolve(false); return; }
          state.lobbyPlayer = { x: targetX, y: targetY };
          player.setAttribute("aria-label", `你的方塊，已抵達${desk.name}`);
          $("#lobby-status").textContent = `已抵達 ${desk.code} · ${desk.name}`;
          resolve(true);
        }, 250);
      }, 250);
    });
  }

  async function openLobbyDesk(deskId) {
    const desk = lobbyDeskOf(deskId);
    if (!desk) return;
    if (state.lobbyAbortController) state.lobbyAbortController.abort();
    state.lobbyRunSequence += 1;
    state.lobbyAbortController = null;
    state.lobbyBusy = false;
    state.lobbyDesk = key(deskId);
    $("#lobby-shell").classList.remove("has-panel");
    $("#lobby-desk-panel").hidden = true;
    $$("[data-lobby-desk]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.lobbyDesk === state.lobbyDesk)));
    const arrived = await moveLobbyPlayerToDesk(state.lobbyDesk);
    if (!arrived || state.lobbyDesk !== key(deskId) || state.route !== "lobby") return;
    $("#lobby-shell").classList.add("has-panel");
    $("#lobby-desk-panel").hidden = false;
    renderLobbyDeskPanel();
    $("#lobby-desk-panel").focus({ preventScroll: true });
    if (window.innerWidth <= 980) $("#lobby-desk-panel").scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function closeLobbyDesk() {
    if (state.lobbyAbortController) state.lobbyAbortController.abort();
    state.lobbyRunSequence += 1;
    state.lobbyAbortController = null;
    state.lobbyBusy = false;
    state.lobbyDesk = null;
    $("#lobby-shell").classList.remove("has-panel");
    $("#lobby-desk-panel").hidden = true;
    $$("[data-lobby-desk]").forEach(button => button.setAttribute("aria-pressed", "false"));
    $("#lobby-status").textContent = "櫃檯已關閉 · 可選擇下一站";
  }

  function renderLobbyDeskPanel() {
    const desk = lobbyDeskOf();
    if (!desk) return;
    const profile = lobbyPlayerProfile();
    const recovery = object(state.lobbyRecovery[state.lobbyDesk]);
    const panel = $("#lobby-desk-panel");
    if (panel) panel.dataset.desk = state.lobbyDesk;
    $("#lobby-desk-code").textContent = `DESK / ${desk.code} · ${desk.english}`;
    $("#lobby-desk-title").textContent = desk.name;
    $("#lobby-secretary-name").textContent = desk.displayName;
    $("#lobby-secretary-role").textContent = `${desk.secretary} · DESK ${desk.code}`;
    $("#lobby-secretary-manner").textContent = desk.manner;
    $("#lobby-desk-description").textContent = desk.description;
    $("#lobby-capability").textContent = state.user
      ? `${profile.role} · ${desk.name} · 可辦理能力由本櫃檯 × 你的服務端職位即時決定`
      : "訪客模式 · 可參觀，不讀取私人資料";
    const quickRoot = $("#lobby-quick-actions");
    quickRoot.innerHTML = [
      ...desk.actions.map(action => `<button type="button" data-lobby-action="${h(action.key)}">${h(action.label)} →</button>`),
      ...desk.prompts.map((prompt, index) => `<button type="button" data-lobby-prompt="${h(prompt)}">${String(index + 1).padStart(2, "0")} · 問秘書</button>`),
    ].join("");
    $$("[data-lobby-action]", quickRoot).forEach(button => button.addEventListener("click", () => handleLobbyAction(button.dataset.lobbyAction)));
    $$("[data-lobby-prompt]", quickRoot).forEach(button => button.addEventListener("click", () => sendLobbySecretary(button.dataset.lobbyPrompt)));
    $("#lobby-case-create").hidden = true;
    $("#lobby-case-drawer").hidden = !(state.user && desk === LOBBY_DESKS.docket);
    $("#lobby-space-drawer").hidden = !(state.user && desk === LOBBY_DESKS.collaboration);
    populateLobbyCaseSelector();
    renderLobbyTranscript();
    const status = $("#lobby-secretary-state");
    status.textContent = state.lobbyBusy ? "LISTENING" : text(recovery.status, "READY");
    status.classList.toggle("busy", state.lobbyBusy);
    status.classList.toggle("recoverable", !state.lobbyBusy && recovery.status === "RETRY READY");
    const input = $("#lobby-secretary-input");
    const submit = $("#lobby-secretary-form button[type=submit]");
    const cancel = $("#lobby-secretary-cancel");
    const savedDraft = String(state.lobbyDrafts[state.lobbyDesk] || "");
    if (input.value !== savedDraft) input.value = savedDraft;
    input.disabled = state.lobbyBusy || !state.user;
    submit.disabled = state.lobbyBusy || !state.user;
    cancel.hidden = !state.lobbyBusy;
    cancel.disabled = !state.lobbyBusy;
  }

  function handleLobbyAction(action) {
    if (["guide", "roles"].includes(action)) { navigate(action); return; }
    if (!state.user) { openLoginDialog(); return; }
    if (action === "case-create") { openLobbyCaseCreate(); return; }
    if (action === "cases") {
      $("#lobby-case-drawer").hidden = false;
      $("#lobby-space-drawer").hidden = true;
      if (!state.cases.length) loadCases().catch(() => {});
      $("#lobby-case-drawer").scrollIntoView({ block: "nearest", behavior: "smooth" });
      return;
    }
    if (action === "spaces") {
      $("#lobby-space-drawer").hidden = false;
      $("#lobby-case-drawer").hidden = true;
      if (!state.spaces.length) loadSpaces().catch(() => {});
      $("#lobby-space-drawer").scrollIntoView({ block: "nearest", behavior: "smooth" });
      return;
    }
    if (action === "court") {
      if (state.lobbyCaseId) state.selectedCaseId = state.lobbyCaseId;
      navigate("court");
      return;
    }
    if (action === "messages") { navigate("messages"); return; }
    if (action === "archive") navigate("archive");
  }

  function populateLobbyCaseSelector() {
    const select = $("#lobby-case-context-select");
    if (!select) return;
    const previous = state.lobbyCaseId || select.value;
    select.innerHTML = `<option value="">不指定案件</option>${state.cases.map(item => `<option value="${h(item.id)}">${h(first(item.case_no, item.id))} · ${h(first(item.title, "未命名案件"))}</option>`).join("")}`;
    if (previous && state.cases.some(item => String(item.id) === String(previous))) {
      select.value = String(previous);
      state.lobbyCaseId = previous;
    } else if (previous) {
      state.lobbyCaseId = null;
    }
  }

  function appendLobbyTranscript(deskId, message) {
    const deskKey = key(deskId);
    if (!LOBBY_DESKS[deskKey]) return;
    const transcript = array(state.lobbyTranscripts[deskKey]);
    const nextMessage = { id: text(message && message.id, clientRequestId()), ...object(message) };
    const duplicateIndex = nextMessage.confirmationKey
      ? transcript.findIndex(item => item.confirmationKey === nextMessage.confirmationKey)
      : -1;
    state.lobbyTranscripts[deskKey] = duplicateIndex >= 0
      ? transcript.map((item, index) => index === duplicateIndex ? { ...item, ...nextMessage, id: item.id } : item)
      : [...transcript, nextMessage].slice(-80);
    if (state.lobbyDesk === deskKey) renderLobbyTranscript();
  }

  function updateLobbyTranscript(deskId, messageId, patch) {
    const deskKey = key(deskId);
    state.lobbyTranscripts[deskKey] = array(state.lobbyTranscripts[deskKey]).map(message => (
      message.id === messageId ? { ...message, ...object(patch) } : message
    ));
    if (state.lobbyDesk === deskKey) renderLobbyTranscript();
  }

  function setLobbyDraft(deskId, value) {
    const deskKey = key(deskId);
    if (!LOBBY_DESKS[deskKey]) return;
    state.lobbyDrafts[deskKey] = String(value == null ? "" : value);
    const input = $("#lobby-secretary-input");
    if (state.lobbyDesk === deskKey && input && input.value !== state.lobbyDrafts[deskKey]) input.value = state.lobbyDrafts[deskKey];
  }

  function lobbyConfirmationFromEvent(eventValue) {
    const event = object(eventValue);
    const payload = object(event.payload);
    const candidates = [event.action, payload.action, event.confirmation, payload.confirmation, event, payload]
      .map(object);
    const action = candidates.find(candidate => text(candidate.kind)) || {};
    const kindValue = key(first(action.kind, event.kind, payload.kind));
    const rawId = first(action.id, action.action_id, event.action_id, payload.action_id);
    if (kindValue === "record_create" && /^\d+$/.test(String(rawId || "")) && Number(rawId) > 0) {
      const proposal = object(first(action.proposal, action.record, payload.proposal, payload.record));
      return {
        kind: "record_create",
        actionId: String(Number(rawId)),
        confirmationKey: `record_create:${Number(rawId)}`,
        title: text(proposal.title, action.title, payload.title, "建立檔案"),
        summary: text(proposal.summary, proposal.description, action.summary, payload.summary, "請核對提案後決定是否寫入 BIU 檔案庫。"),
        confirmLabel: text(action.confirm_label, "確認建立"),
        rejectLabel: text(action.reject_label, "退回提案"),
      };
    }
    const actionKey = text(action.action_key);
    if (kindValue === "command_confirmation" || actionKey.startsWith("command:")) {
      return {
        kind: "command_confirmation",
        actionId: actionKey.startsWith("command:") ? actionKey.slice("command:".length) : text(rawId),
        confirmationKey: `command_confirmation:${actionKey || text(rawId, clientRequestId())}`,
        title: text(action.title, payload.title, "需要正式確認"),
        summary: text(action.summary, payload.summary, "此操作需要 Warehouse 2.0 的正式身份確認。"),
      };
    }
    return {
      kind: "generic_confirmation",
      actionId: "",
      confirmationKey: `generic_confirmation:${clientRequestId()}`,
      title: "需要正式確認",
      summary: "這項操作沒有可供大廳安全執行的確認契約；請前往 Warehouse 2.0 正式確認。",
    };
  }

  function renderLobbyConfirmation(message) {
    const confirmation = object(message.confirmation);
    const recordCreate = confirmation.kind === "record_create";
    const status = key(message.confirmationStatus || "pending");
    const actionable = recordCreate && ["pending", "error"].includes(status);
    const statusText = ({
      submitting: "正在送交 Warehouse 2.0…",
      completed: "檔案已建立",
      rejected: "提案已退回，沒有寫入",
      expired: "提案已失效，請重新請秘書建立",
      error: "沒有送達；可以重試",
    })[status] || "等待你的決定";
    return `<section class="lobby-confirmation-card ${h(status)}" aria-label="${h(confirmation.title)}">
      <span class="eyebrow red">${recordCreate ? "RECORD CREATE / CONFIRM" : "WAREHOUSE / CONFIRM"}</span>
      <h4>${h(confirmation.title)}</h4>
      ${confirmation.summary ? renderLobbyMarkdown(confirmation.summary) : ""}
      <p class="lobby-confirmation-state"${status === "error" ? ' role="alert"' : ""}>${h(message.confirmationError || statusText)}</p>
      ${actionable ? `<div class="lobby-confirmation-actions"><button type="button" data-lobby-confirm="reject" data-lobby-confirm-message="${h(message.id)}">${h(confirmation.rejectLabel)}</button><button class="primary" type="button" data-lobby-confirm="confirm" data-lobby-confirm-message="${h(message.id)}">${h(status === "error" ? "重新送交確認" : confirmation.confirmLabel)}</button></div>` : ""}
      ${!recordCreate && !["completed", "rejected"].includes(status) ? '<a class="lobby-confirmation-link" href="/#/terminal">前往 Warehouse 正式確認 →</a>' : ""}
    </section>`;
  }

  function renderLobbyTranscript() {
    const root = $("#lobby-transcript");
    const desk = lobbyDeskOf();
    if (!root || !desk) return;
    const messages = array(state.lobbyTranscripts[state.lobbyDesk]);
    const visible = messages.length ? messages : [{
      role: "assistant",
      text: desk.greeting,
    }];
    root.innerHTML = visible.map(message => {
      const role = ["user", "assistant", "step", "confirmation"].includes(message.role) ? message.role : "step";
      const marker = role === "user" ? "YOU" : role === "assistant" ? desk.displayName : role === "confirmation" ? "確認" : "··";
      const body = role === "assistant"
        ? renderLobbyMarkdown(message.text)
        : role === "confirmation"
          ? renderLobbyConfirmation(message)
          : `<p class="lobby-plaintext">${h(message.text)}</p>`;
      const retry = message.retryPrompt
        ? `<button class="lobby-message-retry" type="button" data-lobby-retry-message="${h(message.id)}"${message.retrying ? " disabled" : ""}>${message.retrying ? "正在重試…" : "再次請教"} →</button>`
        : "";
      return `<article class="lobby-message ${role}"><span title="${h(role === "assistant" ? desk.secretary : marker)}">${h(marker)}</span><div>${body}${retry}</div></article>`;
    }).join("");
    $$('[data-lobby-retry-message]', root).forEach(button => button.addEventListener("click", () => {
      const retryMessage = array(state.lobbyTranscripts[state.lobbyDesk]).find(message => message.id === button.dataset.lobbyRetryMessage);
      if (retryMessage && retryMessage.retryPrompt) sendLobbySecretary(retryMessage.retryPrompt, { retryMessageId: retryMessage.id });
    }));
    $$('[data-lobby-confirm]', root).forEach(button => button.addEventListener("click", () => {
      decideLobbyConfirmation(button.dataset.lobbyConfirmMessage, button.dataset.lobbyConfirm);
    }));
    root.scrollTop = root.scrollHeight;
  }

  function runLobbySecretary(event) {
    event.preventDefault();
    const input = $("#lobby-secretary-input");
    const message = input.value.trim();
    if (!message) return;
    sendLobbySecretary(message);
  }

  function cancelLobbySecretary() {
    if (!state.lobbyBusy || !state.lobbyAbortController || !state.lobbyDesk) return;
    const deskId = state.lobbyDesk;
    const controller = state.lobbyAbortController;
    const prompt = String(state.lobbyDrafts[deskId] || "").trim();
    state.lobbyRunSequence += 1;
    state.lobbyAbortController = null;
    state.lobbyBusy = false;
    state.lobbyRecovery[deskId] = { status: "RETRY READY", reason: "manual" };
    controller.abort();
    appendLobbyTranscript(deskId, {
      role: "step",
      text: "已經替你停止這次等候。文字仍在輸入框，想繼續時再送一次就好。",
      retryPrompt: prompt,
    });
    renderLobbyDeskPanel();
  }

  async function decideLobbyConfirmation(messageId, decision) {
    const deskId = state.lobbyDesk;
    const transcript = array(state.lobbyTranscripts[deskId]);
    const message = transcript.find(item => item.id === messageId);
    const confirmation = object(message && message.confirmation);
    const actionId = String(confirmation.actionId || "");
    if (!message || confirmation.kind !== "record_create" || !/^\d+$/.test(actionId) || !["confirm", "reject"].includes(decision)) return;
    if (!["pending", "error"].includes(key(message.confirmationStatus || "pending"))) return;
    const requestFence = authFence();
    updateLobbyTranscript(deskId, messageId, { confirmationStatus: "submitting", confirmationError: "" });
    const endpoint = decision === "confirm"
      ? `/api/agent/record-actions/${encodeURIComponent(actionId)}/confirm`
      : `/api/agent/record-actions/${encodeURIComponent(actionId)}/reject`;
    try {
      const response = await tenantPost(endpoint, {});
      assertAuthFence(requestFence);
      if (String(response.action_id || "") !== actionId) throw new Error("檔案提案回應不匹配");
      if (decision === "reject") {
        if (response.status !== "rejected") throw new Error("退回提案未返回完成狀態");
        updateLobbyTranscript(deskId, messageId, { confirmationStatus: "rejected", confirmationError: "" });
        return;
      }
      if (response.event !== "record_created") throw new Error("建檔確認未返回完成事件");
      const record = object(first(response.record, response.record_summary, object(response.payload).record));
      const recordId = Number(first(record.id, record.record_id, response.record_id));
      if (!Number.isInteger(recordId) || recordId <= 0) throw new Error("建檔完成事件缺少有效檔案編號");
      updateLobbyTranscript(deskId, messageId, { confirmationStatus: "completed", confirmationError: "" });
      appendLobbyTranscript(deskId, {
        role: "assistant",
        text: `已經寫入檔案。\n\n**${text(record.record_no, `RECORD ${recordId}`)}** · ${text(record.title, confirmation.title)}`,
      });
      await loadRecords().catch(error => toast(error.message || "檔案已建立；目錄稍後重新整理"));
    } catch (error) {
      if (sessionChanged(error) || !authFenceMatches(requestFence)) return;
      updateLobbyTranscript(deskId, messageId, {
        confirmationStatus: Number(error.status) === 410 ? "expired" : "error",
        confirmationError: error.message || "確認沒有送達，請重試",
      });
    }
  }

  async function sendLobbySecretary(message, options = null) {
    const deskId = state.lobbyDesk;
    const desk = lobbyDeskOf(deskId);
    const prompt = text(message);
    const retryMessageId = text(object(options).retryMessageId);
    if (!desk || !prompt) return;
    if (!state.user) { openLoginDialog(); return; }
    if (state.lobbyBusy) return;
    const runSequence = ++state.lobbyRunSequence;
    const runDeskId = deskId;
    const controller = typeof AbortController === "function" ? new AbortController() : null;
    state.lobbyAbortController = controller;
    state.lobbyBusy = true;
    state.lobbyRecovery[runDeskId] = { status: "LISTENING" };
    setLobbyDraft(runDeskId, prompt);
    if (retryMessageId) updateLobbyTranscript(runDeskId, retryMessageId, { retrying: true });
    appendLobbyTranscript(runDeskId, { role: "user", text: prompt });
    renderLobbyDeskPanel();
    let finalMessage = "";
    let timedOut = false;
    const timeout = controller ? window.setTimeout(() => {
      timedOut = true;
      state.lobbyRecovery[runDeskId] = { status: "STOPPING", reason: "timeout" };
      controller.abort();
    }, 60000) : null;
    try {
      const context = { desk_id: runDeskId };
      if (state.lobbyCaseId) context.case_id = Number(state.lobbyCaseId);
      await tenantAgentStream({
        text: prompt,
        conversation_id: state.lobbyConversations[runDeskId] || null,
        biu_lobby_context: context,
      }, event => {
        if (runSequence !== state.lobbyRunSequence || state.lobbyDesk !== runDeskId) return;
        if (event.event === "run_start") {
          state.lobbyConversations[runDeskId] = first(event.conversation_id, state.lobbyConversations[runDeskId]);
        } else if (event.event === "step_start") {
          appendLobbyTranscript(runDeskId, { role: "step", text: `查詢 Warehouse · ${text(event.command, event.title, event.tool_name, "讀取資料")}` });
        } else if (event.event === "confirmation_required") {
          const confirmation = lobbyConfirmationFromEvent(event);
          appendLobbyTranscript(runDeskId, {
            role: "confirmation",
            confirmation,
            confirmationKey: confirmation.confirmationKey,
            confirmationStatus: "pending",
          });
        } else if (event.event === "final") {
          finalMessage = text(event.message, object(event.payload).message);
        }
      }, { signal: controller && controller.signal });
      if (runSequence !== state.lobbyRunSequence || state.lobbyDesk !== runDeskId) return;
      appendLobbyTranscript(runDeskId, { role: "assistant", text: finalMessage || `${desk.displayName}已經處理完這次查詢；目前沒有需要補充的文字。` });
      setLobbyDraft(runDeskId, "");
      state.lobbyRecovery[runDeskId] = { status: "READY" };
      if (retryMessageId) updateLobbyTranscript(runDeskId, retryMessageId, { retrying: false, retryPrompt: "" });
    } catch (error) {
      if (runSequence !== state.lobbyRunSequence || state.lobbyDesk !== runDeskId) return;
      const stopped = error && error.name === "AbortError";
      const stoppedManually = stopped && object(state.lobbyRecovery[runDeskId]).reason === "manual";
      const failureText = timedOut
        ? `${desk.displayName}等候回應超過一分鐘，已先停止連線。你的文字還在，可以直接重試。`
        : stoppedManually
          ? `已經替你停止這次等候。你的文字仍在輸入框，想繼續時再送一次就好。`
          : error.outcomeUnknown
            ? error.message
            : `${desk.displayName}剛才沒有接通：${error.message || "服務暫時沒有回應"}。你的文字已保留。`;
      state.lobbyRecovery[runDeskId] = { status: "RETRY READY" };
      appendLobbyTranscript(runDeskId, {
        role: "step",
        text: failureText,
        retryPrompt: error.outcomeUnknown ? "" : prompt,
      });
      if (retryMessageId) updateLobbyTranscript(runDeskId, retryMessageId, { retrying: false });
    } finally {
      if (timeout) window.clearTimeout(timeout);
      if (runSequence !== state.lobbyRunSequence || state.lobbyDesk !== runDeskId) return;
      state.lobbyAbortController = null;
      state.lobbyBusy = false;
      renderLobbyDeskPanel();
    }
  }

  function lobbyCaseTypes() {
    return array(object(state.caseMeta).types).filter(type => type.active !== false);
  }

  function lobbyCaseFieldOptions(field) {
    return array(object(field).options).map(option => {
      if (option && typeof option === "object") return {
        value: text(option.value, option.key, option.id),
        label: text(option.label, option.name, option.value, option.key),
      };
      return { value: text(option), label: text(option) };
    }).filter(option => option.value);
  }

  function populateLobbyCaseTypes() {
    const select = $("#lobby-case-type");
    if (!select) return;
    const types = lobbyCaseTypes();
    const previous = select.value;
    select.innerHTML = `<option value="">選擇案件類型</option>${types.map(type => `<option value="${h(type.id)}">${h(type.name)} · ${h(first(type.owner_unit_name, type.owner_unit_code, "BIU"))}</option>`).join("")}`;
    if (previous && types.some(type => String(type.id) === previous)) select.value = previous;
    renderLobbyCaseFields();
  }

  function renderLobbyCaseFields() {
    const root = $("#lobby-case-fields");
    const type = lobbyCaseTypes().find(item => String(item.id) === String($("#lobby-case-type").value));
    if (!type) {
      root.innerHTML = `<p class="field-note">選擇類型後，這裡會顯示 Warehouse 2.0 定義的必填欄位。</p>`;
      return;
    }
    const fields = array(type.fields);
    if (!fields.length) {
      root.innerHTML = `<p class="field-note">此類型沒有額外欄位。</p>`;
      return;
    }
    const assignees = array(object(state.caseMeta).assignees);
    const units = array(object(state.caseMeta).units);
    root.innerHTML = fields.map(fieldValue => {
      const field = object(fieldValue);
      const fieldKey = text(field.key, field.field_key);
      const label = text(field.label, field.name, fieldKey);
      const kind = key(field.type || "text");
      const required = field.required === true;
      const requiredAttribute = required ? " required" : "";
      const sensitive = field.sensitive === true ? " · 限定資料" : "";
      if (kind === "file") return `<p class="field-note"><strong>${h(label)}</strong>${required ? " · 必填附件" : " · 附件"}：案件建立後請在完整案件頁使用安全附件上傳。</p>`;
      if (kind === "textarea") return `<label><span>${h(label)}${required ? " *" : ""}${h(sensitive)}</span><textarea data-lobby-case-field="${h(fieldKey)}" data-field-kind="textarea" rows="4" maxlength="20000"${requiredAttribute}></textarea></label>`;
      if (kind === "boolean") return `<label class="lobby-case-confirm"><input type="checkbox" data-lobby-case-field="${h(fieldKey)}" data-field-kind="boolean"${requiredAttribute}><span>${h(label)}${required ? " *" : ""}${h(sensitive)}</span></label>`;
      if (kind === "enum" || kind === "multienum") {
        const multiple = kind === "multienum" ? " multiple" : "";
        const options = lobbyCaseFieldOptions(field).map(option => `<option value="${h(option.value)}">${h(option.label)}</option>`).join("");
        return `<label><span>${h(label)}${required ? " *" : ""}${h(sensitive)}</span><select data-lobby-case-field="${h(fieldKey)}" data-field-kind="${kind}"${multiple}${requiredAttribute}><option value="">—</option>${options}</select></label>`;
      }
      if (kind === "user") {
        const options = assignees.map(item => `<option value="${h(item.id)}">${h(first(item.display_name, item.username, item.id))} · ${h(first(item.unit_name, item.position_name, "BIU"))}</option>`).join("");
        return `<label><span>${h(label)}${required ? " *" : ""}${h(sensitive)}</span><select data-lobby-case-field="${h(fieldKey)}" data-field-kind="user"${requiredAttribute}><option value="">—</option>${options}</select></label>`;
      }
      if (kind === "department") {
        const options = units.map(item => `<option value="${h(first(item.id, item.unit_code))}">${h(first(item.unit_name, item.name, item.unit_code))}</option>`).join("");
        return `<label><span>${h(label)}${required ? " *" : ""}</span><select data-lobby-case-field="${h(fieldKey)}" data-field-kind="department"${requiredAttribute}><option value="">—</option>${options}</select></label>`;
      }
      const inputType = kind === "number" ? "number" : kind === "date" ? "date" : kind === "datetime" ? "datetime-local" : "text";
      return `<label><span>${h(label)}${required ? " *" : ""}${h(sensitive)}</span><input type="${inputType}" data-lobby-case-field="${h(fieldKey)}" data-field-kind="${h(kind)}" maxlength="4000"${requiredAttribute}></label>`;
    }).join("");
  }

  async function openLobbyCaseCreate() {
    if (!state.user) { openLoginDialog(); return; }
    if (!state.caseMeta) await loadCases().catch(() => {});
    const permissions = object(object(state.caseMeta).permissions);
    const status = $("#lobby-case-create-status");
    if (permissions.can_create !== true) {
      status.textContent = "目前職位沒有 cases.create；可先前往席位櫃檯查看取得方式。";
      $("#lobby-case-create").hidden = false;
      $("#lobby-case-create-form button[type=submit]").disabled = true;
      return;
    }
    state.lobbyCaseIdempotencyKey = state.lobbyCaseIdempotencyKey || clientRequestId();
    status.textContent = "";
    $("#lobby-case-create-form button[type=submit]").disabled = false;
    $("#lobby-case-create").hidden = false;
    $("#lobby-case-drawer").hidden = true;
    populateLobbyCaseTypes();
    $("#lobby-case-create").scrollIntoView({ block: "nearest", behavior: "smooth" });
  }

  async function submitLobbyCase(event) {
    event.preventDefault();
    if (!state.user) { openLoginDialog(); return; }
    const form = event.currentTarget;
    const submit = form.querySelector("button[type=submit]");
    const status = $("#lobby-case-create-status");
    const type = lobbyCaseTypes().find(item => String(item.id) === String($("#lobby-case-type").value));
    if (!type) { status.textContent = "請選擇案件類型。"; return; }
    if (object(object(state.caseMeta).permissions).can_create !== true) { status.textContent = "目前職位沒有建立案件的權限。"; return; }
    const fields = {};
    for (const input of $$('[data-lobby-case-field]', form)) {
      const fieldKey = input.dataset.lobbyCaseField;
      const kind = input.dataset.fieldKind;
      let value;
      if (kind === "boolean") value = input.checked;
      else if (kind === "multienum") value = [...input.selectedOptions].map(option => option.value).filter(Boolean);
      else if (kind === "number") value = input.value === "" ? "" : Number(input.value);
      else if (kind === "datetime" && input.value) value = new Date(input.value).toISOString();
      else value = input.value.trim();
      if (input.required && (value === "" || value === false || (Array.isArray(value) && !value.length))) {
        status.textContent = `請完成「${input.closest("label")?.innerText.trim() || fieldKey}」。`;
        input.focus();
        return;
      }
      if (value !== "" && (!Array.isArray(value) || value.length)) fields[fieldKey] = value;
    }
    const requestFence = authFence();
    const requestId = state.lobbyCaseIdempotencyKey || clientRequestId();
    state.lobbyCaseIdempotencyKey = requestId;
    submit.disabled = true;
    status.textContent = "正在由 Warehouse 2.0 驗證類型、權限與必填資料…";
    try {
      const result = await tenantPost("/api/cases", {
        type_id: type.id,
        title: $("#lobby-case-title").value.trim(),
        description: $("#lobby-case-description").value.trim(),
        severity: $("#lobby-case-severity").value,
        fields,
        idempotency_key: requestId,
      });
      assertAuthFence(requestFence);
      const created = object(result.case);
      if (!first(created.id, created.case_id)) throw new Error("建立接口未返回案件識別");
      state.lobbyCaseId = first(created.id, created.case_id);
      appendLobbyTranscript("filing", { role: "assistant", text: `案件 ${text(created.case_no, created.id)} 已由結構化接案表單寫入 Warehouse 2.0。` });
      form.reset();
      state.lobbyCaseIdempotencyKey = null;
      $("#lobby-case-create").hidden = true;
      await loadCases();
      assertAuthFence(requestFence);
      populateLobbyCaseSelector();
      status.textContent = "";
      toast("案件已建立並保存在 BIU Warehouse 2.0");
    } catch (error) {
      if (sessionChanged(error)) return;
      status.textContent = `${error.message || "案件建立失敗"}。同一表單保留冪等識別；再次提交不會建立重複案件。`;
    } finally {
      if (authFenceMatches(requestFence)) submit.disabled = object(object(state.caseMeta).permissions).can_create !== true;
    }
  }

  function casesFrom(data) {
    return array(first(object(data).cases, object(data).items, object(object(data).data).cases));
  }

  async function loadCases() {
    const root = $("#case-list");
    if (root) root.innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    try {
      const [meta, data] = await Promise.all([
        tenantJson("/api/cases/meta"),
        tenantPost("/api/cases/search", { limit: 100 }),
      ]);
      state.caseMeta = object(meta);
      state.cases = casesFrom(data);
      renderCases();
      populateCaseSelector();
      populateLobbyCaseSelector();
      return state.cases;
    } catch (error) {
      if (sessionChanged(error)) return [];
      if (root) root.innerHTML = `<div class="load-error"><p>${h(error.message || "案件暫時無法載入")}</p><button class="button" type="button" data-retry-cases>重新讀取</button></div>`;
      $("[data-retry-cases]", root)?.addEventListener("click", loadCases);
      throw error;
    }
  }

  function renderCases() {
    const root = $("#case-list");
    if (!root) return;
    if (!state.cases.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>Warehouse 2.0 目前沒有返回你可閱讀的 BIU 案件。</p></div>`;
      return;
    }
    root.innerHTML = state.cases.map(item => `
      <article class="case-card">
        <header><span>${h(first(item.case_no, item.id))}</span><span>${h(first(item.status, "—"))}</span></header>
        <h3>${h(first(item.title, "未命名案件"))}</h3>
        <p>${h(first(item.type_name_snapshot, item.type_name, "BIU CASE"))} · ${h(first(item.owner_unit_name, item.assignee_name, "待指派"))}</p>
        <footer><button type="button" data-lobby-case="${h(item.id)}">帶到櫃檯</button><button type="button" data-open-court="${h(item.id)}">進入庭審場 →</button><button type="button" data-open-warehouse-case="${h(item.id)}">完整案件 ↗</button></footer>
      </article>
    `).join("");
    $$("[data-lobby-case]", root).forEach(button => button.addEventListener("click", () => {
      state.lobbyCaseId = button.dataset.lobbyCase;
      populateLobbyCaseSelector();
      toast("已把案件帶到目前櫃檯");
    }));
    $$("[data-open-court]", root).forEach(button => button.addEventListener("click", () => {
      selectCase(state.cases.find(item => String(item.id) === String(button.dataset.openCourt)));
      navigate("court");
    }));
    $$("[data-open-warehouse-case]", root).forEach(button => button.addEventListener("click", () => {
      location.href = `/#/cases?case=${encodeURIComponent(button.dataset.openWarehouseCase)}`;
    }));
  }

  function collaborationTaskIdOfCase(item) {
    const source = object(item);
    return first(object(source.collaboration_task).id);
  }

  function selectCase(item) {
    if (!item) return;
    caseSelectionSequence += 1;
    state.selectedCaseId = item.id;
    const bridgedTaskId = collaborationTaskIdOfCase(item);
    if (bridgedTaskId != null && String(bridgedTaskId) !== String(state.selectedSpaceId)) {
      spaceSelectionSequence += 1;
      state.selectedSpaceId = bridgedTaskId;
      state.collaboration = null;
      state.messages = [];
    }
  }

  const collabData = value => object(first(object(value).data, value));
  const collabWorkspace = value => object(first(
    collabData(value).space,
    collabData(value).workspace,
    collabData(value).collaboration,
    object(collabData(value).task).collaboration
  ));
  const collabViewer = value => object(first(
    collabData(value).membership,
    collabWorkspace(value).membership,
    collabData(value).viewer,
    collabWorkspace(value).viewer
  ));
  const collabCapabilities = value => ({
    ...object(collabWorkspace(value).capabilities),
    ...object(collabData(value).capabilities),
    ...object(collabViewer(value).capabilities),
  });
  const collabCollection = value => array(first(
    collabData(value).items,
    collabData(value).workspaces,
    collabData(value).collaborations,
    collabData(value).tasks,
    collabData(value).results
  ));
  const collabMessages = value => array(first(
    collabData(value).items,
    collabData(value).messages,
    object(collabData(value).channel).messages
  ));
  const normalizedSpace = rawValue => {
    const raw = object(rawValue);
    const task = object(first(raw.task, raw.task_summary));
    const workspace = object(first(raw.space, raw.workspace, raw.collaboration));
    const invitation = object(first(raw.invitation, workspace.invitation));
    return {
      raw,
      id: first(task.id, task.task_id, raw.task_id, workspace.task_id),
      spaceId: first(workspace.id, workspace.space_id, raw.space_id),
      title: text(task.title, raw.task_title, raw.title, "未命名工作間"),
      description: text(task.description, raw.task_description, raw.description),
      owner: text(object(first(raw.owner, workspace.owner, task.owner)).display_name, object(first(raw.owner, workspace.owner, task.owner)).name),
      discoverability: key(first(workspace.discoverability, raw.discoverability, "company")),
      joinPolicy: key(first(workspace.join_policy, raw.join_policy, "request")),
      memberCount: number(first(workspace.member_count, raw.member_count, array(workspace.members).length)),
      relation: key(first(raw.relation, raw.membership_status, raw.viewer_status)),
      invitationId: first(raw.invitation_id, invitation.id, invitation.invitation_id),
      capabilities: collabCapabilities(raw),
    };
  };

  async function loadSpaces() {
    const lobbyRoot = $("#space-list");
    if (lobbyRoot) lobbyRoot.innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    try {
      const data = await tenantJson("/api/task-collaboration/discover?limit=50");
      const seen = new Set();
      state.spaces = collabCollection(data).map(normalizedSpace).filter(space => {
        if (space.id == null || seen.has(String(space.id))) return false;
        seen.add(String(space.id));
        return true;
      });
      renderSpaces();
      renderMessageSpaces();
      return state.spaces;
    } catch (error) {
      if (sessionChanged(error)) return [];
      if (lobbyRoot) lobbyRoot.innerHTML = `<div class="load-error"><p>${h(error.message || "協作工作間暫時無法載入")}</p><button class="button" type="button" data-retry-spaces>重新讀取</button></div>`;
      $("[data-retry-spaces]", lobbyRoot)?.addEventListener("click", loadSpaces);
      throw error;
    }
  }

  function renderSpaces() {
    const root = $("#space-list");
    if (!root) return;
    if (!state.spaces.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>Warehouse 2.0 目前沒有返回可探索的 BIU 協作工作間。</p></div>`;
      return;
    }
    root.innerHTML = state.spaces.map(space => {
      const canRead = space.capabilities.can_read === true;
      const canJoin = space.capabilities.can_join === true;
      const canRequest = space.capabilities.can_request === true;
      const invited = ["invited", "invitation"].includes(space.relation) && space.invitationId != null;
      const canAcceptInvitation = invited && space.capabilities.can_accept_invitation === true;
      const pending = ["requested", "request", "pending"].includes(space.relation);
      const action = canAcceptInvitation ? "接受邀請 →" : invited ? "邀請暫不可接受" : pending ? "已申請 · 等待審核" : canRead ? "查看消息 →" : canJoin ? "加入工作間 →" : canRequest ? "申請加入 →" : "目前不可加入";
      const enabled = canAcceptInvitation || (!invited && !pending && (canRead || canJoin || canRequest));
      return `
      <article class="space-row">
        <header><span>${h(space.discoverability.toUpperCase())}</span><span>${space.memberCount} 人</span></header>
        <div><h3>${h(space.title)}</h3><p>${h(first(space.description, space.owner && `負責人：${space.owner}`, "BIU 協作工作間"))}</p></div>
        <button class="button" type="button" data-space-open="${h(space.id)}"${enabled ? "" : " disabled"}>${h(action)}</button>
      </article>
    `; }).join("");
    $$("[data-space-open]", root).forEach(button => button.addEventListener("click", () => openSpace(button.dataset.spaceOpen)));
  }

  async function openSpace(taskId) {
    const space = state.spaces.find(item => String(item.id) === String(taskId));
    if (!space) return;
    if (["requested", "request", "pending"].includes(space.relation)) return;
    if (["invited", "invitation"].includes(space.relation) && space.invitationId != null && space.capabilities.can_accept_invitation === true) {
      const operationSequence = ++spaceSelectionSequence;
      try {
        await tenantPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/invitations/${encodeURIComponent(space.invitationId)}/respond`, { decision: "accept" });
        if (operationSequence !== spaceSelectionSequence) return;
        toast("已接受 BIU 協作邀請");
        await loadSpaces();
        if (operationSequence !== spaceSelectionSequence) return;
        const refreshed = state.spaces.find(item => String(item.id) === String(taskId));
        if (refreshed && refreshed.capabilities.can_read === true) {
          spaceSelectionSequence += 1;
          state.selectedSpaceId = taskId;
          state.collaboration = null;
          state.messages = [];
          navigate("messages");
        }
      } catch (error) {
        toast(error.message || "邀請回應失敗");
      }
      return;
    }
    if (space.capabilities.can_read === true) {
      spaceSelectionSequence += 1;
      state.selectedSpaceId = taskId;
      state.collaboration = null;
      state.messages = [];
      navigate("messages");
      return;
    }
    if (space.capabilities.can_join !== true && space.capabilities.can_request !== true) return;
    const operationSequence = ++spaceSelectionSequence;
    try {
      await tenantPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/join`, { role: "contributor" });
      if (operationSequence !== spaceSelectionSequence) return;
      toast(space.capabilities.can_join === true ? "已加入 BIU 協作工作間" : "加入申請已提交");
      await loadSpaces();
      if (operationSequence !== spaceSelectionSequence) return;
      const refreshed = state.spaces.find(item => String(item.id) === String(taskId));
      if (refreshed && refreshed.capabilities.can_read === true) {
        spaceSelectionSequence += 1;
        state.selectedSpaceId = taskId;
        state.collaboration = null;
        state.messages = [];
        navigate("messages");
      }
    } catch (error) {
      toast(error.message || "協作加入操作失敗");
    }
  }

  async function loadLobby() {
    if (!state.user) return;
    await Promise.allSettled([loadCases(), loadSpaces()]);
  }

  function renderMessageSpaces() {
    const root = $("#message-spaces");
    if (!root) return;
    const readable = state.spaces.filter(space => space.capabilities.can_read === true && !["invited", "invitation"].includes(space.relation));
    if (!readable.length) {
      root.innerHTML = `<div class="empty-state small"><p>沒有可讀取的工作間</p></div>`;
      return;
    }
    root.innerHTML = readable.map(space => `<button class="workspace-choice${String(space.id) === String(state.selectedSpaceId) ? " active" : ""}" type="button" data-message-space="${h(space.id)}"><strong>${h(space.title)}</strong><small>${h(space.relation || space.discoverability)} · ${space.memberCount} MEMBERS</small></button>`).join("");
    $$("[data-message-space]", root).forEach(button => button.addEventListener("click", () => selectMessageSpace(button.dataset.messageSpace)));
  }

  async function prepareMessages() {
    if (!state.user) return;
    if (!state.spaces.length) await loadSpaces().catch(() => {});
    renderMessageSpaces();
    if (state.selectedSpaceId) selectMessageSpace(state.selectedSpaceId);
  }

  async function selectMessageSpace(taskId) {
    const selectionSequence = ++spaceSelectionSequence;
    const requestedTaskId = String(taskId);
    state.selectedSpaceId = taskId;
    state.collaboration = null;
    state.messages = [];
    renderMessageSpaces();
    const space = state.spaces.find(item => String(item.id) === String(taskId));
    $("#conversation-head").innerHTML = `<span class="eyebrow">SYNCING WORKSPACE</span><h2>${h(space ? space.title : "協作工作間")}</h2>`;
    $("#message-log").innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    setMessageComposer(false, "正在讀取工作間權限");
    try {
      const detail = await tenantJson(`/api/tasks/${encodeURIComponent(taskId)}/collaboration`);
      if (selectionSequence !== spaceSelectionSequence || String(state.selectedSpaceId) !== requestedTaskId) return;
      const capabilities = collabCapabilities(detail);
      if (capabilities.can_read !== true) throw new Error("Warehouse 2.0 未授予此工作間的讀取權限");
      const workspace = collabWorkspace(detail);
      const task = object(first(collabData(detail).task, workspace.task, {}));
      state.collaboration = detail;
      const known = state.spaces.find(item => String(item.id) === String(taskId));
      if (known) known.capabilities = capabilities;
      else state.spaces.push({
        id: taskId,
        spaceId: first(workspace.id, workspace.space_id),
        title: text(task.title, "案件協作工作間"),
        description: text(task.description),
        memberCount: number(first(workspace.member_count, array(workspace.members).length)),
        relation: key(first(collabViewer(detail).status, "member")),
        discoverability: key(first(workspace.discoverability, "team")),
        capabilities,
      });
      renderMessageSpaces();
      $("#conversation-head").innerHTML = `<span class="eyebrow">WAREHOUSE 2.0 / LIVE</span><h2>${h(text(task.title, space && space.title, "協作工作間"))}</h2>`;
      setMessageComposer(capabilities.can_send === true, capabilities.can_send === true ? "可發送 · 寫入 Warehouse 2.0" : "只讀 · 由工作間權限決定");
      await loadMessages(taskId, selectionSequence, detail);
    } catch (error) {
      if (sessionChanged(error) || selectionSequence !== spaceSelectionSequence || String(state.selectedSpaceId) !== requestedTaskId) return;
      $("#message-log").innerHTML = `<div class="load-error"><p>${h(error.message || "工作間無法載入")}</p></div>`;
      setMessageComposer(false, "無發送權限");
    }
  }

  function setMessageComposer(canSend, label) {
    const input = $("#message-input");
    const button = $("#message-form button[type=submit]");
    input.disabled = !canSend;
    button.disabled = !canSend;
    $("#message-capability").textContent = label;
  }

  async function loadMessages(taskId = state.selectedSpaceId, selectionSequence = spaceSelectionSequence, collaboration = state.collaboration) {
    if (!taskId || !collaboration) return;
    const requestedTaskId = String(taskId);
    const capabilities = collabCapabilities(collaboration);
    if (capabilities.can_read !== true) return;
    const data = await tenantJson(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/messages?after_id=0&limit=100`);
    if (
      selectionSequence !== spaceSelectionSequence
      || String(state.selectedSpaceId) !== requestedTaskId
      || state.collaboration !== collaboration
    ) return;
    state.messages = collabMessages(data);
    renderMessages();
  }

  function messageId(message) { return number(first(message.id, message.message_id)); }
  function renderMessages() {
    const root = $("#message-log");
    if (!state.messages.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>此工作間目前沒有消息。第一則消息會直接保存在 Warehouse 2.0。</p></div>`;
      return;
    }
    const userId = first(state.user.id, state.user.user_id);
    root.innerHTML = state.messages.sort((a, b) => messageId(a) - messageId(b)).map(message => {
      const sender = object(message.sender);
      const senderId = first(message.sender_user_id, sender.user_id, sender.id);
      const mine = message.is_mine === true || (userId != null && String(senderId) === String(userId));
      return `<article class="message${mine ? " mine" : ""}"><header><strong>${h(text(sender.display_name, sender.name, message.sender_name, "BIU 參與者"))}</strong><time>${h(formatDate(first(message.created_at, message.sent_at)))}</time></header><p>${h(first(message.body, message.message, ""))}</p></article>`;
    }).join("");
    root.scrollTop = root.scrollHeight;
  }

  async function sendMessage(event) {
    event.preventDefault();
    const input = $("#message-input");
    const body = input.value.trim();
    const caps = collabCapabilities(state.collaboration);
    if (!body || !state.selectedSpaceId || caps.can_send !== true) return;
    const taskId = state.selectedSpaceId;
    const selectionSequence = spaceSelectionSequence;
    const collaboration = state.collaboration;
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await tenantPost(`/api/tasks/${encodeURIComponent(taskId)}/collaboration/messages`, {
        body,
        client_message_id: clientRequestId(),
      });
      if (
        selectionSequence !== spaceSelectionSequence
        || String(state.selectedSpaceId) !== String(taskId)
        || state.collaboration !== collaboration
      ) return;
      input.value = "";
      await loadMessages(taskId, selectionSequence, collaboration);
    } catch (error) {
      if (
        selectionSequence === spaceSelectionSequence
        && String(state.selectedSpaceId) === String(taskId)
        && state.collaboration === collaboration
      ) toast(error.message || "消息發送失敗");
    } finally {
      if (
        selectionSequence === spaceSelectionSequence
        && String(state.selectedSpaceId) === String(taskId)
        && state.collaboration === collaboration
      ) button.disabled = caps.can_send !== true;
    }
  }

  function populateCaseSelector() {
    const select = $("#court-case-select");
    const previous = state.selectedCaseId || select.value;
    select.innerHTML = `<option value="">選擇案件</option>${state.cases.map(item => `<option value="${h(item.id)}">${h(first(item.case_no, item.id))} · ${h(first(item.title, "未命名案件"))}</option>`).join("")}`;
    select.disabled = !state.cases.length;
    if (previous && state.cases.some(item => String(item.id) === String(previous))) {
      select.value = String(previous);
      state.selectedCaseId = previous;
    }
  }

  async function prepareCourt() {
    if (!state.user) return;
    if (!state.cases.length) await loadCases().catch(() => {});
    populateCaseSelector();
    if (state.selectedCaseId) loadCaseDetail(state.selectedCaseId);
  }

  async function loadCaseDetail(caseId) {
    const selectionSequence = ++caseSelectionSequence;
    const requestedCaseId = String(caseId || "");
    if (!caseId) {
      state.selectedCaseId = null;
      state.selectedCase = null;
      renderCourt();
      return;
    }
    /* Empty every case-specific panel before another ACL-scoped case loads. */
    state.selectedCaseId = caseId;
    state.selectedCase = null;
    renderCourt();
    $("#hearing-head").innerHTML = `<span class="case-no">SYNCING CASE</span><h2>正在讀取案件程序</h2><p>權限與版本鎖由 Warehouse 2.0 確認。</p>`;
    try {
      const data = await tenantJson(`/api/cases/${encodeURIComponent(caseId)}`);
      if (selectionSequence !== caseSelectionSequence || String(state.selectedCaseId) !== requestedCaseId) return;
      const selectedCase = data.case && typeof data.case === "object"
        ? { ...data.case, collaboration_task: data.collaboration_task || null }
        : object(data);
      if (String(first(selectedCase.id, selectedCase.case_id, "")) !== requestedCaseId) throw new Error("案件回應識別不一致");
      state.selectedCase = selectedCase;
      state.selectedCaseId = first(selectedCase.id, selectedCase.case_id);
      const bridgedTaskId = collaborationTaskIdOfCase(selectedCase);
      if (bridgedTaskId != null && String(bridgedTaskId) !== String(state.selectedSpaceId)) {
        spaceSelectionSequence += 1;
        state.selectedSpaceId = bridgedTaskId;
        state.collaboration = null;
        state.messages = [];
      }
      renderCourt();
    } catch (error) {
      if (sessionChanged(error) || selectionSequence !== caseSelectionSequence || String(state.selectedCaseId) !== requestedCaseId) return;
      state.selectedCaseId = null;
      state.selectedCase = null;
      $("#court-case-select").value = "";
      renderCourt();
      $("#hearing-head").innerHTML = `<span class="case-no">ACCESS ERROR</span><h2>${h(error.message || "案件無法載入")}</h2><p>請返回案件大廳重新選擇。</p>`;
    }
  }

  function renderCourt() {
    const item = state.selectedCase;
    if (!item) {
      $("#hearing-head").innerHTML = `<span class="case-no">NO CASE</span><h2>請選擇一項案件</h2><p>案件標題與程序狀態將從 Warehouse 2.0 載入。</p>`;
      $("#hearing-timeline").innerHTML = `<li class="placeholder"><span>—</span><p>尚無可顯示的程序記錄</p></li>`;
      $("#court-participants").innerHTML = `<div class="empty-state small"><p>選擇案件後載入</p></div>`;
      $("#evidence-list").innerHTML = `<div class="empty-state small"><p>選擇案件後顯示已登記附件與材料欄位</p></div>`;
      renderCourtControls();
      return;
    }
    const collaborationTaskId = collaborationTaskIdOfCase(item);
    const canProcess = object(item.capabilities).can_process === true;
    $("#hearing-head").innerHTML = `<span class="case-no">${h(first(item.case_no, item.id))} · ${h(first(item.status, "—"))}</span><h2>${h(first(item.title, "未命名案件"))}</h2><p>${h(first(item.type_name_snapshot, item.owner_unit_name, "BIU CASE"))}</p>${canProcess ? `<button class="text-button hearing-collab" type="button" id="hearing-collab">${collaborationTaskId != null ? "加入案件工作間 →" : "建立案件工作間 →"}</button>` : ""}`;
    $("#hearing-collab")?.addEventListener("click", openCaseCollaboration);
    const events = array(item.events);
    $("#hearing-timeline").innerHTML = events.length ? events.map((event, index) => `<li><span>${String(index + 1).padStart(2, "0")}</span><div><h3>${h(ACTION_LABELS[event.event_type] || event.event_type || "程序記錄")}</h3>${event.message ? `<p>${h(event.message)}</p>` : ""}<time>${h(text(event.actor_name, event.actor_kind, "BIU"))} · ${h(formatDate(event.created_at))}${event.from_status && event.to_status ? ` · ${h(event.from_status)} → ${h(event.to_status)}` : ""}</time></div></li>`).join("") : `<li class="placeholder"><span>01</span><p>Warehouse 2.0 尚未返回程序記錄</p></li>`;
    const rawParticipants = array(item.participants);
    const returnedParticipants = rawParticipants.map(participant => ({
      label: text(participant.position_name, participant.role_name, participant.participant_role, participant.role, "PARTICIPANT"),
      value: text(participant.display_name, participant.name, participant.username, participant.user_name),
    })).filter(participant => participant.value);
    const dynamicFields = object(item.dynamic_data);
    const fields = Object.keys(dynamicFields).length ? dynamicFields : object(item.fields);
    const fieldConfigs = array(object(item.type_config).fields);
    const fieldConfig = new Map(fieldConfigs.map(field => [String(first(field.key, field.field_key)), field]));
    const configuredSeats = Object.entries(fields).flatMap(([fieldKey, rawValue]) => {
      const config = object(fieldConfig.get(String(fieldKey)));
      if (key(config.type) !== "user" || rawValue == null || rawValue === "") return [];
      return (Array.isArray(rawValue) ? rawValue : [rawValue]).map(userId => {
        const participant = rawParticipants.find(candidate => String(candidate.user_id) === String(userId));
        const resolvedName = participant && text(participant.display_name, participant.name, participant.username, participant.user_name);
        return {
          label: text(config.label, config.name, fieldKey),
          value: resolvedName || `USER ID ${String(userId)} · 未解析`,
        };
      });
    });
    const fallbackParticipants = [
      { label: "REPORTER", value: first(item.reporter_name, item.created_by_name) },
      { label: "ASSIGNEE", value: item.assignee_name },
      { label: "OWNER UNIT", value: first(item.owner_unit_name, item.owner_unit_code_snapshot) },
    ].filter(participant => participant.value);
    const participantValues = [...configuredSeats, ...(returnedParticipants.length ? returnedParticipants : fallbackParticipants)]
      .filter((participant, index, values) => values.findIndex(candidate => candidate.label === participant.label && candidate.value === participant.value) === index);
    $("#court-participants").innerHTML = participantValues.length ? participantValues.map(participant => `<div class="participant"><span>${h(participant.label)}</span><strong>${h(participant.value)}</strong></div>`).join("") : `<div class="empty-state small"><p>案件未返回參與者資料</p></div>`;
    const attachments = array(item.attachments);
    const materials = [
      ...attachments.map(file => ({ title: first(file.file_name, file.name, "附件"), meta: first(file.field_key, file.mime_type, "ATTACHMENT"), attachment: file })),
      ...Object.entries(fields).filter(([fieldKey, value]) => value != null && value !== "" && key(object(fieldConfig.get(String(fieldKey))).type) !== "user").map(([fieldKey, value]) => {
        const config = object(fieldConfig.get(String(fieldKey)));
        return { title: text(config.label, config.name, fieldKey), meta: Array.isArray(value) ? value.join(", ") : String(value) };
      }),
    ];
    $("#evidence-list").innerHTML = materials.length ? materials.map(material => material.attachment && material.attachment.id != null
      ? `<button class="evidence-item evidence-download" type="button" data-attachment-id="${h(material.attachment.id)}"><b>${h(material.title)}</b><small>${h(material.meta)} · 下載 ↗</small></button>`
      : `<div class="evidence-item"><b>${h(material.title)}</b><small>${h(material.meta)}</small></div>`).join("") : `<div class="empty-state small"><p>案件尚未返回附件或材料欄位</p></div>`;
    $$("[data-attachment-id]", $("#evidence-list")).forEach(button => button.addEventListener("click", () => {
      const attachment = attachments.find(file => String(file.id) === String(button.dataset.attachmentId));
      if (attachment) downloadCaseAttachment(item, attachment);
    }));
    $("#case-deep-link").href = `/#/cases?case=${encodeURIComponent(item.id)}`;
    renderCourtControls();
  }

  async function downloadCaseAttachment(item, attachment) {
    try {
      const requestFence = authFence();
      const response = await tenantFetch(`/api/cases/${encodeURIComponent(item.id)}/attachments/${encodeURIComponent(attachment.id)}`);
      assertAuthFence(requestFence);
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        assertAuthFence(requestFence);
        throw new Error(data.error || data.message || "附件下載失敗");
      }
      const blob = await response.blob();
      assertAuthFence(requestFence);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = text(attachment.file_name, attachment.name, `BIU-ATTACHMENT-${attachment.id}`);
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      if (sessionChanged(error)) return;
      toast(error.message || "附件下載失敗");
    }
  }

  async function openCaseCollaboration() {
    const item = state.selectedCase;
    if (!item || object(item.capabilities).can_process !== true) return;
    const selectionSequence = caseSelectionSequence;
    const selectedCaseId = String(first(item.id, item.case_id, ""));
    try {
      /* Idempotent bridge also enrolls an authorized case participant when the
         private task room already exists, so every entry goes through it. */
      const result = await tenantPost(`/api/cases/${encodeURIComponent(item.id)}/collaboration`, {});
      if (selectionSequence !== caseSelectionSequence || String(state.selectedCaseId) !== selectedCaseId) return;
      const task = object(result.task);
      const taskId = task.id;
      if (taskId == null) throw new Error("Warehouse 2.0 未返回案件工作間識別碼");
      state.selectedCase = { ...item, collaboration_task: task };
      toast(result.created === true ? "案件工作間已建立" : "已加入案件工作間");
      spaceSelectionSequence += 1;
      state.selectedSpaceId = taskId;
      state.collaboration = null;
      state.messages = [];
      navigate("messages");
    } catch (error) {
      if (selectionSequence === caseSelectionSequence && String(state.selectedCaseId) === selectedCaseId) {
        toast(error.message || "案件工作間無法開啟");
      }
    }
  }

  function renderCourtControls() {
    const item = state.selectedCase;
    const actions = array(item && object(item.capabilities).available_actions);
    const select = $("#court-action-select");
    select.innerHTML = `<option value="">${actions.length ? "選擇可用動作" : "目前沒有可用動作"}</option>${actions.map(action => `<option value="${h(action)}">${h(ACTION_LABELS[action] || action)}</option>`).join("")}`;
    select.disabled = !actions.length;
    $("#court-note").disabled = !actions.length;
    $("#court-action-form button[type=submit]").disabled = !actions.length;
    $("#court-lock").textContent = `LOCK / ${item && item.lock_version != null ? item.lock_version : "—"}`;
    renderCourtActionExtra();
  }

  function renderCourtActionExtra() {
    const action = $("#court-action-select").value;
    const root = $("#court-action-extra");
    if (action !== "assign") {
      root.innerHTML = "";
      return;
    }
    const assignees = array(state.caseMeta && state.caseMeta.assignees);
    root.innerHTML = `<label><span>指派參與者</span><select id="court-assignee" required><option value="">請選擇 Warehouse 2.0 返回的參與者</option>${assignees.map(user => `<option value="${h(user.id)}"${Number(user.id) === Number(state.selectedCase && state.selectedCase.assignee_user_id) ? " selected" : ""}>${h(text(user.display_name, user.name, user.username, user.id))}</option>`).join("")}</select></label>`;
  }

  async function submitCourtAction(event) {
    event.preventDefault();
    const item = state.selectedCase;
    const action = $("#court-action-select").value;
    const available = array(item && object(item.capabilities).available_actions);
    if (!item || !action || !available.includes(action)) return;
    const button = event.currentTarget.querySelector("button[type=submit]");
    const note = $("#court-note").value.trim();
    const selectionSequence = caseSelectionSequence;
    const submittedCaseId = String(first(item.id, item.case_id, ""));
    button.disabled = true;
    try {
      const body = { action, lock_version: item.lock_version, message: note };
      if (action === "assign") {
        const assigneeId = $("#court-assignee") && $("#court-assignee").value;
        const assignee = array(state.caseMeta && state.caseMeta.assignees).find(user => String(user.id) === String(assigneeId));
        if (!assignee) throw new Error("請選擇 Warehouse 2.0 返回的可指派參與者");
        body.assignee_user_id = Number(assignee.id);
      }
      if (action === "resolve") {
        if (!note) throw new Error("形成意見時請填寫正式記錄");
        body.resolution_summary = note;
        body.root_cause = text(item.root_cause);
        body.corrective_action = text(item.corrective_action);
      }
      if (action === "close") {
        body.root_cause = text(item.root_cause);
        body.corrective_action = text(item.corrective_action);
      }
      const result = await tenantPost(`/api/cases/${encodeURIComponent(item.id)}/actions`, body);
      if (selectionSequence !== caseSelectionSequence || String(state.selectedCaseId) !== submittedCaseId) return;
      const nextCase = object(first(result.case, result));
      if (String(first(nextCase.id, nextCase.case_id, "")) !== submittedCaseId) throw new Error("案件操作回應識別不一致");
      state.selectedCase = nextCase;
      $("#court-note").value = "";
      renderCourt();
      await loadCases().catch(() => {});
      if (selectionSequence === caseSelectionSequence && String(state.selectedCaseId) === submittedCaseId) {
        toast("程序記錄已寫入 Warehouse 2.0");
      }
    } catch (error) {
      if (selectionSequence === caseSelectionSequence && String(state.selectedCaseId) === submittedCaseId) {
        toast(error.message || "程序記錄提交失敗");
      }
    } finally {
      if (selectionSequence === caseSelectionSequence && String(state.selectedCaseId) === submittedCaseId) {
        renderCourtControls();
      }
    }
  }

  const recordsFrom = data => {
    const source = object(data);
    return array(first(source.records, source.items, object(source.data).records));
  };
  const recordFrom = data => object(first(object(data).record, object(data).item, object(object(data).data).record, data));
  const recordIdOf = record => first(record && record.id, record && record.record_id, record && record.uuid);
  const recordActionKey = value => key(typeof value === "object" ? first(value.action, value.key, value.value) : value);

  async function loadRecords() {
    const root = $("#archive-list");
    root.innerHTML = `<div class="catalog-skeleton"><span></span><span></span><span></span></div>`;
    try {
      const [meta, data] = await Promise.all([
        tenantJson("/api/records/meta"),
        tenantPost("/api/records/search", { limit: 100, offset: 0, include_archived: true }),
      ]);
      if (text(meta.template_key) !== BIU_TEMPLATE_KEY) throw new Error("BIU 檔案目錄識別不一致，已停止載入");
      state.recordMeta = object(meta);
      state.records = recordsFrom(data);
      if (state.selectedRecord && !state.records.some(record => String(recordIdOf(record)) === String(recordIdOf(state.selectedRecord)))) {
        recordSelectionSequence += 1;
        state.selectedRecord = null;
        clearRecordConsole();
      }
      renderRecords();
    } catch (error) {
      if (sessionChanged(error)) return;
      root.innerHTML = `<div class="load-error"><p>${h(error.message || "檔案暫時無法載入")}</p><button class="button" type="button" data-retry-records>重新讀取</button></div>`;
      $("[data-retry-records]", root)?.addEventListener("click", loadRecords);
    }
  }

  function renderRecords() {
    const root = $("#archive-list");
    if (!state.records.length) {
      root.innerHTML = `<div class="empty-state"><span>0</span><p>Warehouse 2.0 目前沒有返回你可閱讀的 BIU 檔案。</p></div>`;
      return;
    }
    root.innerHTML = state.records.map(record => `<button class="archive-row${String(recordIdOf(record)) === String(recordIdOf(state.selectedRecord)) ? " active" : ""}" type="button" data-record-id="${h(recordIdOf(record))}"><span>${h(first(record.record_no, record.archive_no, record.id))}</span><h3>${h(first(record.title, record.name, "未命名檔案"))}</h3><small>${h(first(record.status, record.category_name_snapshot, "RECORD"))}</small><small>${h(formatDate(first(record.updated_at, record.created_at)))}</small></button>`).join("");
    $$("[data-record-id]", root).forEach(button => button.addEventListener("click", () => loadRecordDetail(button.dataset.recordId)));
  }

  async function loadRecordDetail(recordId) {
    const selectionSequence = ++recordSelectionSequence;
    const requestedRecordId = String(recordId);
    const consolePanel = $("#record-console");
    consolePanel.hidden = false;
    state.selectedRecord = null;
    $("#record-console-head").innerHTML = `<span class="eyebrow red">MASTER DOSSIER</span><h2 id="record-console-title">正在讀取檔案程序</h2><p>狀態、動作與時間線由 Warehouse 2.0 返回。</p>`;
    $("#record-event-list").innerHTML = "";
    $("#record-action-select").innerHTML = `<option value="">載入中</option>`;
    $("#record-action-select").disabled = true;
    $("#record-action-message").disabled = true;
    $("#record-action-form button[type=submit]").disabled = true;
    $("#record-action-status").textContent = "";
    try {
      const data = await tenantJson(`/api/records/${encodeURIComponent(recordId)}`);
      if (selectionSequence !== recordSelectionSequence) return;
      const record = recordFrom(data);
      if (recordIdOf(record) == null) throw new Error("Warehouse 2.0 未返回檔案資料");
      if (String(recordIdOf(record)) !== requestedRecordId) throw new Error("檔案回應識別不一致");
      state.selectedRecord = record;
      renderRecordConsole();
      renderRecords();
    } catch (error) {
      if (sessionChanged(error) || selectionSequence !== recordSelectionSequence) return;
      state.selectedRecord = null;
      $("#record-console-head").innerHTML = `<span class="eyebrow red">RECORD ERROR</span><h2 id="record-console-title">檔案無法讀取</h2><p>${h(error.message || "請稍後重試")}</p>`;
      $("#record-event-list").innerHTML = `<li><span>—</span><div><b>沒有可顯示的程序資料</b></div></li>`;
    }
  }

  function recordTransitionLabels(record) {
    const transitions = array(object(record.type_config).transitions);
    const transitionLabels = new Map(transitions.map(transition => [
      key(first(transition.action, transition.key, transition.event, transition.to_status, transition.to)),
      text(transition.name, transition.label),
    ]));
    transitionLabels.set("comment", transitionLabels.get("comment") || "補充檔案記錄");
    transitionLabels.set("archive", transitionLabels.get("archive") || "歸檔");
    return transitionLabels;
  }

  function recordActionModel(record) {
    const rawActions = array(first(record.available_actions, object(record.capabilities).available_actions));
    const transitionLabels = recordTransitionLabels(record);
    return rawActions.map(raw => {
      const action = recordActionKey(raw);
      return { action, label: text(transitionLabels.get(action), action) };
    }).filter(item => item.action);
  }

  function renderRecordConsole({ preserveStatus = false } = {}) {
    const record = state.selectedRecord;
    if (!record) return;
    $("#record-console").hidden = false;
    $("#record-console-head").innerHTML = `<span class="eyebrow red">${h(first(record.record_no, record.archive_no, recordIdOf(record)))}</span><h2 id="record-console-title">${h(first(record.title, record.name, "未命名檔案"))}</h2><p>${h(first(record.status, "—"))} · LOCK ${h(first(record.lock_version, "—"))}</p>`;
    const actions = recordActionModel(record);
    const transitions = recordTransitionLabels(record);
    const transitionConfigs = array(object(record.type_config).transitions);
    const events = array(first(record.timeline, record.events, record.history));
    $("#record-event-list").innerHTML = events.length ? events.map((event, index) => {
      const eventKey = key(first(event.action, event.event_type, event.type));
      const statusTransition = event.from_status != null && event.to_status != null
        ? transitionConfigs.find(transition => (
          key(first(transition.from_status, transition.from)) === key(event.from_status)
          && key(first(transition.to_status, transition.to)) === key(event.to_status)
        )) : null;
      const eventLabel = text(
        statusTransition && first(statusTransition.name, statusTransition.label),
        eventKey === "record_archived" && transitions.get("archive"),
        transitions.get(eventKey),
        event.name,
        eventKey,
        "程序記錄"
      );
      return `<li><span>${String(index + 1).padStart(2, "0")}</span><div><b>${h(eventLabel)}</b>${event.message ? `<p>${h(event.message)}</p>` : ""}<time>${h(text(event.actor_name, event.user_name, "BIU"))} · ${h(formatDate(first(event.created_at, event.occurred_at)))}</time></div></li>`;
    }).join("") : `<li><span>01</span><div><b>Warehouse 2.0 尚未返回程序記錄</b></div></li>`;
    const select = $("#record-action-select");
    select.innerHTML = `<option value="">${actions.length ? "選擇可用動作" : "目前沒有可用動作"}</option>${actions.map(item => `<option value="${h(item.action)}">${h(item.label)}</option>`).join("")}`;
    select.disabled = !actions.length;
    $("#record-action-message").disabled = !actions.length;
    $("#record-action-form button[type=submit]").disabled = !actions.length;
    if (!preserveStatus) $("#record-action-status").textContent = "";
  }

  async function submitRecordAction(event) {
    event.preventDefault();
    const record = state.selectedRecord;
    const action = $("#record-action-select").value;
    const available = record ? recordActionModel(record).map(item => item.action) : [];
    if (!record || !available.includes(action)) return;
    if (action === "archive" && !window.confirm("Warehouse 2.0 已將歸檔列為可用動作。確認將此卷宗歸檔？")) return;
    const selectionSequence = recordSelectionSequence;
    const submittedRecordId = String(recordIdOf(record));
    const button = event.currentTarget.querySelector("button[type=submit]");
    button.disabled = true;
    $("#record-action-status").textContent = "正在提交檔案程序……";
    try {
      const data = await tenantPost(`/api/records/${encodeURIComponent(recordIdOf(record))}/actions`, {
        action,
        lock_version: record.lock_version,
        message: $("#record-action-message").value.trim(),
      });
      if (
        selectionSequence !== recordSelectionSequence
        || String(recordIdOf(state.selectedRecord)) !== submittedRecordId
      ) return;
      const next = recordFrom(data);
      if (recordIdOf(next) == null) throw new Error("操作接口未返回檔案資料");
      if (String(recordIdOf(next)) !== submittedRecordId) throw new Error("檔案操作回應識別不一致");
      state.selectedRecord = next;
      $("#record-action-message").value = "";
      renderRecordConsole();
      await loadRecords();
      if (
        selectionSequence === recordSelectionSequence
        && String(recordIdOf(state.selectedRecord)) === submittedRecordId
      ) toast("檔案程序已寫入 Warehouse 2.0");
    } catch (error) {
      if (
        selectionSequence === recordSelectionSequence
        && String(recordIdOf(state.selectedRecord)) === submittedRecordId
      ) $("#record-action-status").textContent = error.message || "檔案程序提交失敗";
    } finally {
      if (
        selectionSequence === recordSelectionSequence
        && String(recordIdOf(state.selectedRecord)) === submittedRecordId
      ) renderRecordConsole({ preserveStatus: true });
    }
  }

  function wireEvents() {
    window.addEventListener("hashchange", () => activateRoute(routeFromHash(), { focusHeading: true }));
    window.addEventListener("storage", handleTokenStorage);
    window.addEventListener("keydown", handleGuideKeyboard);
    $$("[data-route-button]").forEach(button => button.addEventListener("click", () => navigate(button.dataset.routeButton)));
    $(".menu-button").addEventListener("click", event => {
      const open = !$(".site-nav").classList.contains("open");
      $(".site-nav").classList.toggle("open", open);
      event.currentTarget.setAttribute("aria-expanded", String(open));
    });
    $("#role-search").addEventListener("input", event => { state.roleQuery = event.target.value.trim(); renderRoles(); });
    $$("#role-filters [data-entry]").forEach(button => button.addEventListener("click", () => {
      state.entryFilter = button.dataset.entry;
      $$("#role-filters [data-entry]").forEach(item => {
        const active = item === button;
        item.classList.toggle("active", active);
        item.setAttribute("aria-pressed", String(active));
      });
      renderRoles();
    }));
    $("#role-join-form").addEventListener("submit", submitRole);
    $$("#role-dialog .dialog-close, #role-dialog [data-dialog-cancel]").forEach(button => button.addEventListener("click", () => $("#role-dialog").close()));
    $("#role-guest-seat").addEventListener("click", () => {
      if (guestEnabledPosition(state.selectedRole)) seatAsGuest(state.selectedRole);
    });
    $("#role-exam-assessment").addEventListener("click", () => openExamForPosition(state.selectedRole));
    $("#guide-start").addEventListener("click", loadGuide);
    $("#guide-exit").addEventListener("click", exitGuide);
    $("#guide-previous").addEventListener("click", previousGuideQuestion);
    $("#guide-redo").addEventListener("click", restartGuide);
    $("#guide-exam-close").addEventListener("click", closeExam);
    $("#guide-exam-restart").addEventListener("click", restartExam);
    $("#guest-change-seat").addEventListener("click", clearGuestExperience);
    $("#guest-create-identity").addEventListener("click", openGuestIdentity);
    $$("[data-open-login]").forEach(button => button.addEventListener("click", openLoginDialog));
    $("#header-auth-button").addEventListener("click", () => {
      if (token()) logout();
      else openLoginDialog();
    });
    $("#login-form").addEventListener("submit", login);
    $("#login-dialog .dialog-close").addEventListener("click", () => $("#login-dialog").close());
    $("[data-login-to-roles]").addEventListener("click", () => {
      $("#login-dialog").close();
      navigate("roles");
    });
    $("#message-form").addEventListener("submit", sendMessage);
    $$("[data-lobby-desk]").forEach(button => button.addEventListener("click", () => openLobbyDesk(button.dataset.lobbyDesk)));
    $("#lobby-desk-close").addEventListener("click", closeLobbyDesk);
    $("#lobby-secretary-form").addEventListener("submit", runLobbySecretary);
    $("#lobby-secretary-input").addEventListener("input", event => {
      if (state.lobbyDesk) setLobbyDraft(state.lobbyDesk, event.target.value);
    });
    $("#lobby-secretary-cancel").addEventListener("click", cancelLobbySecretary);
    $("#lobby-case-context-select").addEventListener("change", event => { state.lobbyCaseId = event.target.value || null; });
    $("#lobby-case-type").addEventListener("change", renderLobbyCaseFields);
    $("#lobby-case-create-form").addEventListener("submit", submitLobbyCase);
    $("#lobby-case-create-close").addEventListener("click", () => { $("#lobby-case-create").hidden = true; });
    $("#court-case-select").addEventListener("change", event => {
      state.selectedCaseId = event.target.value || null;
      loadCaseDetail(state.selectedCaseId);
    });
    $("#court-action-select").addEventListener("change", renderCourtActionExtra);
    $("#court-action-form").addEventListener("submit", submitCourtAction);
    $("#record-action-form").addEventListener("submit", submitRecordAction);
    $$("[data-refresh]").forEach(button => button.addEventListener("click", () => ({
      cases: loadCases,
      spaces: loadSpaces,
      records: loadRecords,
    })[button.dataset.refresh]?.()));
  }

  async function boot() {
    wireEvents();
    activateRoute(routeFromHash());
    await Promise.allSettled([loadCatalog(), loadSession()]);
    activateRoute(state.route, { preserveScroll: true });
  }

  boot();
})();
