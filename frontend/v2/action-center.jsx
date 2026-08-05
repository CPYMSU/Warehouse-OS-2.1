/* WAREHOUSE OS 2.1 · 共用業務操作中心
   所有表單均由後端指令 schema 生成，與 AI tools 共用同一執行邊界。 */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
const { useEffect, useMemo, useRef, useState } = React;
const { Icon } = W2;

window.W2_LANG.addEN({
  "業務操作": "Business actions",
  "手動與 AI 共用同一份能力契約": "Manual work and AI share one capability contract",
  "搜尋業務、指令或參數…": "Search business actions, commands or parameters…",
  "全部能力": "All capabilities",
  "可直接執行": "Executable",
  "需受控確認": "Governed confirmation",
  "我有權使用": "Authorised for me",
  "寫入業務": "Business writes",
  "只讀查詢": "Read-only queries",
  "平台能力": "Platform capabilities",
  "共 {n} 項": "{n} actions",
  "已連接 {n} 項": "{n} connected",
  "載入業務能力中…": "Loading business capabilities…",
  "業務能力暫時無法載入": "Business capabilities are temporarily unavailable",
  "重新載入能力": "Reload capabilities",
  "選擇左側操作": "Choose an action on the left",
  "表單字段直接來自指令契約；手動操作與 AI 不會使用兩套參數。": "Form fields come directly from the command contract, so manual work and AI never use different parameters.",
  "需要權限": "Permission required",
  "目前公司可用": "Available in this company",
  "需要平台 L11 治理": "Requires platform L11 governance",
  "需要專用確認流程": "Requires a dedicated confirmation flow",
  "立即寫入並留痕": "Writes immediately with an audit trail",
  "只讀，不改動資料": "Read-only; does not change data",
  "必填": "Required",
  "選填": "Optional",
  "布林值": "Boolean",
  "JSON 陣列": "JSON array",
  "JSON 物件": "JSON object",
  "多個值可用逗號分隔或輸入 JSON 陣列": "Separate values with commas or enter a JSON array",
  "請填寫所有必填字段": "Complete every required field",
  "字段格式不正確：{name}": "Invalid field format: {name}",
  "覆核操作": "Review action",
  "執行查詢": "Run query",
  "確認並執行": "Confirm and execute",
  "提交受治理提案": "Submit governed proposal",
  "返回修改": "Back to edit",
  "操作覆核": "Action review",
  "即將執行的能力": "Capability to execute",
  "參數": "Arguments",
  "無需參數": "No arguments required",
  "執行中…": "Executing…",
  "操作已完成": "Action completed",
  "操作未完成": "Action not completed",
  "執行結果": "Execution result",
  "執行編號": "Execution ID",
  "再次執行": "Run again",
  "關閉業務操作": "Close business actions",
  "沒有符合條件的操作": "No matching actions",
  "指令集拓撲": "Command-set topology",
  "預設折疊 · 依業務域展開操作層級": "Collapsed by default · expand each business domain",
  "全部折疊": "Collapse all",
  "展開結果": "Expand results",
  "查詢層": "Query layer",
  "執行層": "Execution layer",
  "治理層": "Governance layer",
  "平台層": "Platform layer",
  "只讀取得業務資訊": "Read business information without changing it",
  "錄入、更新與完成業務": "Record, update and complete business work",
  "需要專用確認或多人治理": "Requires dedicated confirmation or multi-party governance",
  "跨公司平台治理入口": "Cross-company platform governance entry",
  "執行身份": "Execution identity",
  "請求帳號": "Requesting user",
  "公司 AI": "Company AI",
  "確認策略": "Confirmation policy",
  "語義資源": "Semantic resource",
  "驗證方式": "Verification",
  "適配器": "Adapter",
  "{n} 個分支": "{n} branches",
  "{n} 項可執行": "{n} executable",
  "受治理操作不會由通用按鈕繞過確認；系統會返回它所需的專用流程。": "Governed actions never bypass confirmation through this general button; the system returns the dedicated flow required.",
  "敏感值只傳送到後端，不會顯示在覆核摘要或審計參數中。": "Sensitive values are sent only to the backend and are hidden from the review and audited arguments.",
});

const EVENT = "w2-open-business-action";
const TOPOLOGY_BRANCHES = [
  { key: "read", code: "READ", label: "查詢層", description: "只讀取得業務資訊" },
  { key: "write", code: "WRITE", label: "執行層", description: "錄入、更新與完成業務" },
  { key: "governed", code: "GOV", label: "治理層", description: "需要專用確認或多人治理" },
  { key: "platform", code: "L11", label: "平台層", description: "跨公司平台治理入口" },
];
const topologyBranchFor = action => {
  if (action.scope === "platform") return "platform";
  if (action.confirmation_required) return "governed";
  return action.writes ? "write" : "read";
};
const secretName = name => /password|secret|token|api.?key|credential|passkey|sql/i.test(String(name || ""));
const textOf = value => String(value == null ? "" : value);
const actionSearchText = action => [
  action.command, action.tool_name, action.description, action.category,
  action.category_label, action.usage, action.execution_identity,
  action.semantic_resource, action.verification, action.adapter,
  ...Object.keys((action.parameters && action.parameters.properties) || {}),
].join(" ").toLowerCase();
const requestId = () => {
  try { if (crypto && typeof crypto.randomUUID === "function") return crypto.randomUUID(); }
  catch (error) {}
  return "manual-" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 10);
};
const initialValuesFor = (action, supplied = {}) => {
  const properties = action && action.parameters && action.parameters.properties || {};
  const values = {};
  Object.entries(properties).forEach(([name, property]) => {
    if (property.default !== undefined && property.default !== null) values[name] = property.default;
    else if (/^(request-id|idempotency-key)$/i.test(name)) values[name] = requestId();
    else if (property.type === "boolean") values[name] = false;
  });
  return { ...values, ...(supplied && typeof supplied === "object" ? supplied : {}) };
};

const parseFieldValue = (name, property, raw) => {
  const type = property.type || "string";
  if (type === "boolean") return !!raw;
  if (raw === "" || raw == null) return undefined;
  if (type === "integer") {
    const value = Number(raw);
    if (!Number.isInteger(value)) throw new Error(name);
    return value;
  }
  if (type === "number") {
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error(name);
    return value;
  }
  if (type === "array") {
    if (Array.isArray(raw)) return raw;
    const source = textOf(raw).trim();
    if (!source) return [];
    if (source.startsWith("[")) {
      const value = JSON.parse(source);
      if (!Array.isArray(value)) throw new Error(name);
      return value;
    }
    return source.split(",").map(value => value.trim()).filter(Boolean);
  }
  if (type === "object") {
    const value = typeof raw === "object" ? raw : JSON.parse(textOf(raw));
    if (!value || Array.isArray(value) || typeof value !== "object") throw new Error(name);
    return value;
  }
  return textOf(raw);
};

const stateLabel = action => {
  if (action.scope === "platform") return t("需要平台 L11 治理");
  if (!action.authorized) return t("需要權限");
  if (action.confirmation_required) return t("需要專用確認流程");
  return action.writes ? t("立即寫入並留痕") : t("只讀，不改動資料");
};
const executionIdentityLabel = action => action.execution_identity === "requesting_user"
  ? t("請求帳號")
  : t("公司 AI");

const ActionField = ({ name, property, required, value, onChange, disabled }) => {
  const type = property.type || "string";
  const description = property.description || "";
  const inputId = "business-action-" + name.replace(/[^A-Za-z0-9_-]/g, "-");
  if (Array.isArray(property.enum) && property.enum.length) return <label className="business-action-field" htmlFor={inputId}>
    <span className="business-action-field-label"><b>{name}</b><em>{required ? t("必填") : t("選填")}</em></span>
    <select id={inputId} className="field" disabled={disabled} value={value == null ? "" : value}
      onChange={event => onChange(event.target.value)}>
      {!required && property.default == null && <option value="">{t("未指定")}</option>}
      {property.enum.map(option => <option key={String(option)} value={String(option)}>{String(option).toUpperCase()}</option>)}
    </select>
    {!!description && <small>{description}</small>}
  </label>;
  if (type === "boolean") return <label className="business-action-boolean" htmlFor={inputId}>
    <input id={inputId} type="checkbox" checked={!!value} disabled={disabled}
      onChange={event => onChange(event.target.checked)}/>
    <span><b>{name}</b><small>{description || t("布林值")} · {required ? t("必填") : t("選填")}</small></span>
  </label>;
  const jsonLike = type === "array" || type === "object" || /json/i.test(name);
  const inputValue = (type === "array" || type === "object") && value != null && typeof value !== "string"
    ? JSON.stringify(value, null, type === "object" ? 2 : 0)
    : value == null ? "" : value;
  const common = {
    id: inputId,
    disabled,
    value: inputValue,
    onChange: event => onChange(event.target.value),
    placeholder: type === "array" ? t("JSON 陣列") : type === "object" ? t("JSON 物件") : "",
    autoComplete: secretName(name) ? "new-password" : "off",
  };
  return <label className="business-action-field" htmlFor={inputId}>
    <span className="business-action-field-label"><b>{name}</b><em>{required ? t("必填") : t("選填")}</em></span>
    {jsonLike
      ? <textarea {...common} rows={type === "object" ? 5 : 3}/>
      : <input {...common} type={secretName(name) ? "password" : ["integer", "number"].includes(type) ? "number" : "text"}
          step={type === "integer" ? "1" : type === "number" ? "any" : undefined}/>}
    {!!description && <small>{description}</small>}
    {type === "array" && <small>{t("多個值可用逗號分隔或輸入 JSON 陣列")}</small>}
  </label>;
};

const BusinessActionCenter = ({ tenant, route, onComplete }) => {
  const [open, setOpen] = useState(false);
  const [catalogue, setCatalogue] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [filter, setFilter] = useState("authorized");
  const [selectedName, setSelectedName] = useState("");
  const [values, setValues] = useState({});
  const [stage, setStage] = useState("edit");
  const [parsed, setParsed] = useState({});
  const [formError, setFormError] = useState("");
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(() => new Set());
  const [expandedBranches, setExpandedBranches] = useState(() => new Set());
  const pendingSelection = useRef("");
  const pendingArguments = useRef({});

  const actions = catalogue && Array.isArray(catalogue.actions) ? catalogue.actions : [];
  const selected = actions.find(action => action.tool_name === selectedName) || null;
  const categories = useMemo(() => {
    const rows = new Map();
    actions.forEach(action => {
      if (action.scope !== "tenant") return;
      rows.set(action.category, {
        label: action.category_label || action.category,
        order: Number.isFinite(Number(action.category_order)) ? Number(action.category_order) : 999,
      });
    });
    return [...rows.entries()].sort((a, b) => a[1].order - b[1].order);
  }, [actions]);

  const load = async (force = false) => {
    if (loading || (catalogue && !force)) return;
    setLoading(true); setLoadError("");
    try {
      const next = await W2.json("/api/business/actions", { cache: "no-store" });
      setCatalogue(next && typeof next === "object" ? next : null);
    } catch (error) {
      setLoadError(error && error.message ? error.message : t("業務能力暫時無法載入"));
    } finally { setLoading(false); }
  };

  useEffect(() => {
    const handler = event => {
      const detail = event && event.detail && typeof event.detail === "object" ? event.detail : {};
      pendingSelection.current = textOf(detail.tool_name || detail.toolName);
      pendingArguments.current = detail.arguments && typeof detail.arguments === "object" ? detail.arguments : {};
      setOpen(true);
      setQuery(textOf(detail.query || ""));
      setCategory("all");
      setFilter(detail.filter || "authorized");
      setSelectedName("");
      setValues({});
      setExpandedCategories(new Set());
      setExpandedBranches(new Set());
      setStage("edit"); setResult(null); setFormError("");
      // The catalogue is versioned server state. Re-opening the sheet must
      // never reuse an older in-memory topology after a hot deployment.
      load(true);
    };
    window.addEventListener(EVENT, handler);
    return () => window.removeEventListener(EVENT, handler);
  }, [catalogue, loading]);

  useEffect(() => {
    setCatalogue(null); setSelectedName(""); setOpen(false);
  }, [tenant]);

  useEffect(() => {
    if (!actions.length) return;
    if (pendingSelection.current) {
      const requested = actions.find(action => action.tool_name === pendingSelection.current);
      pendingSelection.current = "";
      if (requested) {
        setSelectedName(requested.tool_name);
        setValues(initialValuesFor(requested, pendingArguments.current));
        setExpandedCategories(new Set([requested.category || "other"]));
        setExpandedBranches(new Set([
          (requested.category || "other") + ":" + topologyBranchFor(requested),
        ]));
        pendingArguments.current = {};
        return;
      }
    }
  }, [actions, selectedName]);

  useEffect(() => {
    if (!open) return;
    const close = event => { if (event.key === "Escape" && !busy) setOpen(false); };
    window.addEventListener("keydown", close);
    document.documentElement.classList.add("business-action-open");
    return () => {
      window.removeEventListener("keydown", close);
      document.documentElement.classList.remove("business-action-open");
    };
  }, [open, busy]);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    return actions.filter(action => {
      if (category !== "all" && action.category !== category) return false;
      if (filter === "authorized" && !(action.authorized && action.available)) return false;
      if (filter === "write" && !action.writes) return false;
      if (filter === "read" && action.writes) return false;
      if (filter === "governed" && !action.confirmation_required) return false;
      if (filter === "platform" && action.scope !== "platform") return false;
      return !term || actionSearchText(action).includes(term);
    }).sort((a, b) =>
      Number(b.manual_execution === "execute") - Number(a.manual_execution === "execute")
      || Number(b.writes) - Number(a.writes)
      || String(a.command).localeCompare(String(b.command))
    );
  }, [actions, category, filter, query]);

  const topology = useMemo(() => {
    const nodes = new Map();
    filtered.forEach(action => {
      const categoryKey = action.category || "other";
      if (!nodes.has(categoryKey)) {
        nodes.set(categoryKey, {
          key: categoryKey,
          label: action.category_label || categoryKey,
          guide: action.category_guide || "",
          order: Number.isFinite(Number(action.category_order)) ? Number(action.category_order) : 999,
          actions: [],
          branches: new Map(),
        });
      }
      const node = nodes.get(categoryKey);
      const branchKey = topologyBranchFor(action);
      if (!node.branches.has(branchKey)) node.branches.set(branchKey, []);
      node.branches.get(branchKey).push(action);
      node.actions.push(action);
    });
    return [...nodes.values()]
      .sort((a, b) => a.order - b.order || a.label.localeCompare(b.label))
      .map(node => ({
        ...node,
        branches: TOPOLOGY_BRANCHES
          .filter(branch => node.branches.has(branch.key))
          .map(branch => ({ ...branch, actions: node.branches.get(branch.key) })),
      }));
  }, [filtered]);

  const queryExpandsTopology = !!query.trim();
  const categoryForcesOpen = category !== "all";
  const toggleCategory = key => {
    setExpandedCategories(previous => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };
  const toggleBranch = key => {
    setExpandedBranches(previous => {
      const next = new Set(previous);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };
  const collapseTopology = () => {
    setExpandedCategories(new Set());
    setExpandedBranches(new Set());
  };
  const expandTopology = () => {
    setExpandedCategories(new Set(topology.map(node => node.key)));
    setExpandedBranches(new Set(topology.flatMap(node =>
      node.branches.map(branch => node.key + ":" + branch.key)
    )));
  };

  const choose = action => {
    setSelectedName(action.tool_name);
    setValues(initialValuesFor(action));
    setExpandedCategories(previous => new Set(previous).add(action.category || "other"));
    setExpandedBranches(previous => new Set(previous).add(
      (action.category || "other") + ":" + topologyBranchFor(action)
    ));
    setStage("edit");
    setParsed({});
    setResult(null);
    setFormError("");
  };

  const prepare = () => {
    if (!selected) return;
    const schema = selected.parameters || {};
    const properties = schema.properties || {};
    const required = new Set(schema.required || []);
    const next = {};
    try {
      Object.entries(properties).forEach(([name, property]) => {
        const raw = values[name];
        if (required.has(name) && (raw === "" || raw == null || (property.type === "array" && !textOf(raw).trim()))) {
          throw new Error("__required__");
        }
        const value = parseFieldValue(name, property, raw);
        if (value !== undefined) next[name] = value;
      });
    } catch (error) {
      setFormError(error.message === "__required__"
        ? t("請填寫所有必填字段")
        : t("字段格式不正確：{name}", { name: error.message || "—" }));
      return;
    }
    setParsed(next);
    setFormError("");
    if (selected.writes) setStage("review");
    else execute(next);
  };

  const execute = async (argumentsValue = parsed) => {
    if (!selected || busy || selected.manual_execution === "unavailable") return;
    setBusy(true); setFormError("");
    try {
      const response = await W2.post(
        "/api/business/actions/" + encodeURIComponent(selected.tool_name) + "/execute",
        { arguments: argumentsValue }
      );
      setResult(response);
      setStage("result");
      if (response && response.ok) {
        window.dispatchEvent(new CustomEvent("w2-business-action-complete", { detail: response }));
        window.dispatchEvent(new CustomEvent("w2-agent-complete", { detail: response }));
        if (onComplete) await onComplete(response);
      }
    } catch (error) {
      setResult({ ok: false, status: "request_failed", error: error && error.message ? error.message : String(error) });
      setStage("result");
    } finally { setBusy(false); }
  };

  if (!open) return null;
  const properties = selected && selected.parameters && selected.parameters.properties || {};
  const required = new Set(selected && selected.parameters && selected.parameters.required || []);
  const safeParsed = Object.fromEntries(Object.entries(parsed).map(([name, value]) => [
    name, secretName(name) ? "••••••••" : value,
  ]));
  const canExecute = selected && selected.manual_execution !== "unavailable";

  return <div className="business-action-overlay" role="presentation" onMouseDown={event => {
    if (event.target === event.currentTarget && !busy) setOpen(false);
  }}>
    <section className="business-action-sheet" role="dialog" aria-modal="true" aria-label={t("業務操作")}>
      <header className="business-action-head">
        <div>
          <span className="label red">ACTION TOPOLOGY · {catalogue ? catalogue.total : "450"}</span>
          <h2>{t("業務操作")}</h2>
          <p>{t("手動與 AI 共用同一份能力契約")}</p>
        </div>
        <div className="business-action-head-stats">
          <b>{catalogue ? catalogue.tenant_total : "—"}</b><span>TENANT</span>
          <b>{catalogue ? catalogue.executable : "—"}</b><span>READY</span>
        </div>
        <button type="button" className="business-action-close" disabled={busy} onClick={() => setOpen(false)} aria-label={t("關閉業務操作")}><Icon name="x" size={17}/></button>
      </header>

      <div className="business-action-toolbar">
        <label><Icon name="search" size={14}/><input autoFocus value={query} onChange={event => setQuery(event.target.value)} placeholder={t("搜尋業務、指令或參數…")}/></label>
        <select value={category} onChange={event => {
          const value = event.target.value;
          setCategory(value);
          setExpandedCategories(value === "all" ? new Set() : new Set([value]));
          setExpandedBranches(new Set());
        }} aria-label={t("全部能力")}>
          <option value="all">{t("全部能力")}</option>
          {categories.map(([key, item]) => <option key={key} value={key}>{item.label}</option>)}
        </select>
        <select value={filter} onChange={event => setFilter(event.target.value)}>
          <option value="authorized">{t("我有權使用")}</option>
          <option value="write">{t("寫入業務")}</option>
          <option value="read">{t("只讀查詢")}</option>
          <option value="governed">{t("需受控確認")}</option>
          <option value="platform">{t("平台能力")}</option>
          <option value="all">{t("全部能力")}</option>
        </select>
      </div>

      <div className="business-action-body">
        <aside className="business-action-list" aria-label={t("全部能力")}>
          {loading && !catalogue && <div className="business-action-loading"><span className="spinner"/>{t("載入業務能力中…")}</div>}
          {!loading && loadError && !catalogue && <div className="business-action-load-error"><Icon name="alert" size={20}/><b>{t("業務能力暫時無法載入")}</b><small>{loadError}</small><button className="btn sm" onClick={() => load(true)}>{t("重新載入能力")}</button></div>}
          {!!catalogue && <div className="business-action-count">
            <span><b>{t("指令集拓撲")}</b><small>{t("共 {n} 項", { n: filtered.length })} · {t("預設折疊 · 依業務域展開操作層級")}</small></span>
            <span className="business-action-topology-controls">
              <button type="button" disabled={loading} onClick={() => load(true)}>
                {loading ? t("載入業務能力中…") : t("重新載入能力")}
              </button>
              <button type="button" onClick={collapseTopology}>{t("全部折疊")}</button>
              <button type="button" onClick={expandTopology}>{t("展開結果")}</button>
            </span>
          </div>}
          {!!catalogue && <nav className="business-action-topology" aria-label={t("指令集拓撲")}>
            {topology.map((node, index) => {
              const categoryOpen = queryExpandsTopology || categoryForcesOpen || expandedCategories.has(node.key);
              const categoryId = "business-action-category-" + node.key.replace(/[^A-Za-z0-9_-]/g, "-");
              const readyCount = node.actions.filter(action => action.manual_execution === "execute").length;
              return <section className={"business-action-category" + (categoryOpen ? " is-open" : "")} key={node.key}>
                <button type="button" className="business-action-category-trigger"
                  aria-expanded={categoryOpen} aria-controls={categoryId}
                  onClick={() => toggleCategory(node.key)}>
                  <span className="business-action-category-index">{String(index + 1).padStart(2, "0")}</span>
                  <span className="business-action-category-copy"><b>{node.label}</b><small>{node.guide || node.key}</small></span>
                  <span className="business-action-category-meta"><b>{node.actions.length}</b><small>{t("{n} 個分支", { n: node.branches.length })} · {t("{n} 項可執行", { n: readyCount })}</small></span>
                  <Icon name="chevronDown" size={14}/>
                </button>
                {categoryOpen && <div className="business-action-branches" id={categoryId}>
                  {node.branches.map(branch => {
                    const branchIdentity = node.key + ":" + branch.key;
                    const branchOpen = queryExpandsTopology || categoryForcesOpen || expandedBranches.has(branchIdentity);
                    const branchId = "business-action-branch-" + branchIdentity.replace(/[^A-Za-z0-9_-]/g, "-");
                    return <section className={"business-action-branch is-" + branch.key + (branchOpen ? " is-open" : "")} key={branch.key}>
                      <button type="button" className="business-action-branch-trigger"
                        aria-expanded={branchOpen} aria-controls={branchId}
                        onClick={() => toggleBranch(branchIdentity)}>
                        <span>{branch.code}</span>
                        <span><b>{t(branch.label)}</b><small>{t(branch.description)}</small></span>
                        <em>{branch.actions.length}</em>
                        <Icon name="chevronDown" size={12}/>
                      </button>
                      {branchOpen && <div className="business-action-branch-actions" id={branchId}>
                        {branch.actions.map(action => <button type="button" key={action.tool_name}
                          className={"business-action-row" + (selectedName === action.tool_name ? " is-selected" : "")}
                          onClick={() => choose(action)}>
                          <span className={"business-action-state is-" + (action.manual_execution === "execute" ? "ready" : action.confirmation_required ? "governed" : "locked")}/>
                          <span><b>{action.command}</b><small>{[
                            action.description || action.tool_name,
                            action.semantic_resource,
                          ].filter(Boolean).join(" · ")}</small></span>
                          <em>{String(action.risk || "low").toUpperCase()}</em>
                        </button>)}
                      </div>}
                    </section>;
                  })}
                </div>}
              </section>;
            })}
          </nav>}
          {!loading && catalogue && !filtered.length && <div className="business-action-empty">{t("沒有符合條件的操作")}</div>}
        </aside>

        <main className="business-action-form">
          {!selected && <div className="business-action-placeholder"><Icon name="layers" size={34}/><b>{t("選擇左側操作")}</b><p>{t("表單字段直接來自指令契約；手動操作與 AI 不會使用兩套參數。")}</p></div>}
          {selected && <>
            <div className="business-action-title">
              <div><span className="mono">{selected.tool_name}</span><h3>{selected.command}</h3><p>{selected.description}</p></div>
              <div className="business-action-badges">
                <span>{selected.category_label || selected.category}</span>
                <span className={"is-" + (selected.risk || "low")}>{String(selected.risk || "low").toUpperCase()}</span>
                <span className={selected.writes ? "is-write" : "is-read"}>{selected.writes ? "WRITE" : "READ"}</span>
              </div>
            </div>
            <div className={"business-action-policy is-" + (selected.manual_execution === "execute" ? "ready" : "governed")}>
              <Icon name={selected.manual_execution === "execute" ? "checkCircle" : "shield"} size={15}/>
              <span><b>{stateLabel(selected)}</b>{selected.confirmation_required && <small>{t("受治理操作不會由通用按鈕繞過確認；系統會返回它所需的專用流程。")}</small>}</span>
            </div>
            <div className="business-action-contract" aria-label={t("指令集拓撲")}>
              <span><small>{t("執行身份")}</small><b>{executionIdentityLabel(selected)}</b></span>
              <span><small>{t("確認策略")}</small><b>{selected.confirmation_policy && selected.confirmation_policy.mode || "direct"}</b></span>
              <span><small>{t("語義資源")}</small><b>{selected.semantic_resource || "—"}</b></span>
              <span><small>{t("驗證方式")}</small><b>{selected.verification || "—"}</b></span>
              <span><small>{t("適配器")}</small><b>{selected.adapter || selected.execution_kind || "—"}</b></span>
            </div>

            {stage === "edit" && <div className="business-action-fields">
              {!Object.keys(properties).length && <div className="business-action-no-args">{t("無需參數")}</div>}
              {Object.entries(properties).map(([name, property]) => <ActionField key={name} name={name} property={property}
                required={required.has(name)} value={values[name]} disabled={busy}
                onChange={value => setValues(previous => ({ ...previous, [name]: value }))}/>)}
              {Object.keys(properties).some(secretName) && <p className="business-action-security"><Icon name="shield" size={13}/>{t("敏感值只傳送到後端，不會顯示在覆核摘要或審計參數中。")}</p>}
              {!!formError && <div className="business-action-error" role="alert">{formError}</div>}
              <div className="business-action-footer">
                <button type="button" className="btn primary" disabled={!canExecute || busy} onClick={prepare}>
                  <Icon name={selected.writes ? "arrow" : "search"} size={13}/>{selected.writes ? t("覆核操作") : t("執行查詢")}
                </button>
                {!selected.authorized && <span>{t("需要權限")} · {(selected.permission_any || []).join(" / ") || "—"}</span>}
              </div>
            </div>}

            {stage === "review" && <div className="business-action-review">
              <span className="label red">{t("操作覆核")}</span>
              <dl><dt>{t("即將執行的能力")}</dt><dd>{selected.command}</dd><dt>{t("參數")}</dt><dd><pre>{JSON.stringify(safeParsed, null, 2)}</pre></dd></dl>
              <div className="business-action-review-warning"><Icon name="alert" size={15}/>{stateLabel(selected)}</div>
              <div className="business-action-footer">
                <button type="button" className="btn" disabled={busy} onClick={() => setStage("edit")}>{t("返回修改")}</button>
                <button type="button" className="btn primary" disabled={!canExecute || busy} onClick={() => execute()}>
                  <Icon name={busy ? "clock" : selected.confirmation_required ? "shield" : "check"} size={13}/>
                  {busy ? t("執行中…") : selected.confirmation_required ? t("提交受治理提案") : t("確認並執行")}
                </button>
              </div>
            </div>}

            {stage === "result" && <div className={"business-action-result " + (result && result.ok ? "is-ok" : "is-error")}>
              <Icon name={result && result.ok ? "checkCircle" : "alert"} size={30}/>
              <h3>{result && result.ok ? t("操作已完成") : t("操作未完成")}</h3>
              <p>{result && (result.error || result.hint || result.status)}</p>
              {result && result.execution_id && <small>{t("執行編號")} · <span className="mono">{result.execution_id}</span></small>}
              <details><summary>{t("執行結果")}</summary><pre>{JSON.stringify(result, null, 2)}</pre></details>
              <div className="business-action-footer">
                <button type="button" className="btn" onClick={() => { setStage("edit"); setResult(null); }}>{t("再次執行")}</button>
                <button type="button" className="btn primary" onClick={() => setOpen(false)}>{t("關閉業務操作")}</button>
              </div>
            </div>}
          </>}
        </main>
      </div>
    </section>
  </div>;
};

W2.openBusinessAction = options => {
  window.dispatchEvent(new CustomEvent(EVENT, {
    detail: typeof options === "string" ? { tool_name: options } : (options || {}),
  }));
};
W2.BusinessActionCenter = BusinessActionCenter;
})();
