/* WAREHOUSE 2.0 · FEATURE 23 · accessible semantic topology enhancement
 *
 * This file is intentionally plain JavaScript.  It can be loaded immediately
 * after pages-optimizer.jsx (or retried as a standalone production asset) and
 * wraps the registered page without changing the original owner gate.
 */
(function installOptimizerTopologyAsset(global) {
  "use strict";

  var WRAPPED = "__warehouseOptimizerTopologyWrapped";
  var MAX_NODES_PER_LAYER = 8;
  var MAX_EDGES = 80;
  var POLL_DELAY_MS = 1400;
  var DISCOVERY_DELAY_MS = 3000;
  var TERMINAL_JOB_STATES = {
    completed: true,
    partial: true,
    failed: true,
    cancelled: true,
  };
  var AUTOMATION_STATES = {
    idle: true,
    scheduled: true,
    queued: true,
    running: true,
    paused: true,
    disabled: true,
    error: true,
  };
  var LAYERS = [
    { id: "need", label: "USER NEED" },
    { id: "intent", label: "INTENT" },
    { id: "instruction", label: "INSTRUCTION" },
    { id: "capability", label: "CAPABILITY" },
    { id: "friction", label: "FRICTION" },
    { id: "outcome", label: "OUTCOME" },
  ];
  var LAYER_INDEX = LAYERS.reduce(function makeLayerIndex(result, layer, index) {
    result[layer.id] = index;
    return result;
  }, Object.create(null));
  var SEVERITIES = { info: true, low: true, watch: true, medium: true, high: true, critical: true };
  var JOB_PHASES = {
    queued: true,
    collecting: true,
    redacting: true,
    mapping: true,
    tenant_reduce: true,
    platform_reduce: true,
    persisting: true,
    completed: true,
  };

  function objectOf(value) {
    return value && typeof value === "object" && !Array.isArray(value) ? value : {};
  }

  function arrayOf(value) {
    return Array.isArray(value) ? value : [];
  }

  function safeText(value, limit) {
    if (typeof value !== "string") return "";
    return value
      .replace(/[\u0000-\u001f\u007f]/g, " ")
      .replace(/\s+/g, " ")
      .trim()
      .slice(0, limit || 96);
  }

  function safeId(value, fallback) {
    var text = typeof value === "number" ? String(value) : safeText(value, 120);
    text = text.replace(/[^A-Za-z0-9:._-]/g, "-").replace(/-+/g, "-");
    return text || fallback || "";
  }

  function finite(value, fallback) {
    var parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : (fallback == null ? 0 : fallback);
  }

  function count(value) {
    return Math.max(0, Math.trunc(finite(value, 0)));
  }

  function unitRate(value) {
    var parsed = finite(value, 0);
    if (parsed > 1 && parsed <= 100) parsed /= 100;
    return Math.max(0, Math.min(1, parsed));
  }

  function score(value) {
    return Math.max(0, Math.min(100, finite(value, 0)));
  }

  function percent(value) {
    return (unitRate(value) * 100).toFixed(1).replace(/\.0$/, "") + "%";
  }

  function displayNumber(value) {
    return count(value).toLocaleString();
  }

  function timestamp(value) {
    var text = safeText(value, 64);
    if (!text) return "—";
    var parsed = new Date(text);
    return Number.isNaN(parsed.getTime()) ? text : parsed.toLocaleString();
  }

  function scheduleEvery(seconds) {
    var value = count(seconds);
    if (!value) return "—";
    if (value % 86400 === 0) return String(value / 86400) + " d";
    if (value % 3600 === 0) return String(value / 3600) + " h";
    if (value % 60 === 0) return String(value / 60) + " min";
    return String(value) + " s";
  }

  function layerFor(rawLayer, rawKind) {
    var layer = safeId(rawLayer, "").toLowerCase();
    var kind = safeId(rawKind, "").toLowerCase();
    if (layer === "blocker") return "friction";
    if (Object.prototype.hasOwnProperty.call(LAYER_INDEX, layer)) return layer;
    if (kind === "need" || kind === "user_need") return "need";
    if (kind === "intent") return "intent";
    if (kind === "instruction" || kind === "instruction_set" || kind === "prompt") return "instruction";
    if (kind === "capability" || kind === "tool" || kind === "workflow") return "capability";
    if (kind === "friction" || kind === "blocker") return "friction";
    if (kind === "outcome") return "outcome";
    return "";
  }

  /* Only explicit aggregate containers are inspected.  Conversation/message
     collections are deliberately not traversed or rendered by this asset. */
  function overviewOf(payload) {
    var outer = objectOf(payload);
    var overview = objectOf(outer.overview);
    if (Object.keys(overview).length) return overview;
    var result = objectOf(outer.result);
    if (Object.keys(objectOf(result.overview)).length) return objectOf(result.overview);
    if (Object.keys(objectOf(result.topology)).length) return result;
    var analysis = objectOf(outer.analysis);
    if (Object.keys(objectOf(analysis.overview)).length) return objectOf(analysis.overview);
    if (Object.keys(objectOf(analysis.topology)).length) return analysis;
    var snapshot = objectOf(outer.snapshot);
    if (Object.keys(objectOf(snapshot.topology)).length) return snapshot;
    return outer;
  }

  function normalizeTopology(payload) {
    var overview = overviewOf(payload);
    var rawTopology = objectOf(overview.topology);
    var rawNodes = arrayOf(rawTopology.nodes);
    var byLayer = LAYERS.reduce(function initializeLayers(result, layer) {
      result[layer.id] = [];
      return result;
    }, Object.create(null));
    var seen = Object.create(null);

    rawNodes.forEach(function normalizeNode(raw, index) {
      var source = objectOf(raw);
      var id = safeId(source.id, "node-" + index);
      var layer = layerFor(source.layer, source.kind);
      if (!layer || seen[id]) return;
      seen[id] = true;
      var severity = safeId(source.severity, "info").toLowerCase();
      if (!SEVERITIES[severity]) severity = "info";
      var lineage = safeId(source.lineage_quality, "unknown").toLowerCase();
      if (lineage !== "exact" && lineage !== "inferred") lineage = "unknown";
      byLayer[layer].push({
        id: id,
        kind: safeId(source.kind, layer),
        layer: layer,
        label: safeText(source.label, 88) || id,
        conversation_count: count(source.conversation_count),
        tenant_count: count(source.tenant_count),
        friction_count: count(source.friction_count),
        friction_rate: unitRate(source.friction_rate),
        blocker_score: score(source.blocker_score),
        confidence: unitRate(source.confidence),
        instruction_set_key: safeId(source.instruction_set_key, ""),
        lineage_quality: lineage,
        severity: severity,
        rank: Math.max(0, finite(source.rank, index)),
      });
    });

    var nodes = [];
    LAYERS.forEach(function sortLayer(layer) {
      byLayer[layer.id].sort(function compareNodes(a, b) {
        return a.rank - b.rank || b.blocker_score - a.blocker_score ||
          b.conversation_count - a.conversation_count || a.id.localeCompare(b.id);
      });
      byLayer[layer.id] = byLayer[layer.id].slice(0, MAX_NODES_PER_LAYER);
      byLayer[layer.id].forEach(function appendNode(node, row) {
        node.row = row;
        nodes.push(node);
      });
    });

    var included = nodes.reduce(function indexNodes(result, node) {
      result[node.id] = node;
      return result;
    }, Object.create(null));
    var edgeIds = Object.create(null);
    var edges = [];
    arrayOf(rawTopology.edges).some(function normalizeEdge(raw, index) {
      if (edges.length >= MAX_EDGES) return true;
      var source = objectOf(raw);
      var from = safeId(source.source, "");
      var to = safeId(source.target, "");
      if (!included[from] || !included[to] || from === to) return false;
      if (LAYER_INDEX[included[from].layer] >= LAYER_INDEX[included[to].layer]) return false;
      var id = safeId(source.id, "edge-" + index);
      if (edgeIds[id]) return false;
      edgeIds[id] = true;
      var severity = safeId(source.severity, "info").toLowerCase();
      if (!SEVERITIES[severity]) severity = "info";
      var kind = safeId(source.kind, "flow").toLowerCase();
      var flowState = safeId(source.flow_state, "").toLowerCase();
      if (flowState !== "blocked" && flowState !== "resolved" && flowState !== "observed") {
        flowState = kind.indexOf("block") >= 0 ? "blocked" :
          (kind.indexOf("resolv") >= 0 ? "resolved" : "observed");
      }
      edges.push({
        id: id,
        source: from,
        target: to,
        kind: kind,
        conversation_count: count(source.conversation_count),
        friction_count: count(source.friction_count),
        friction_rate: unitRate(source.friction_rate),
        confidence: unitRate(source.confidence),
        severity: severity,
        flow_state: flowState,
        blocked: flowState === "blocked",
      });
      return false;
    });

    return {
      schema_version: count(rawTopology.schema_version),
      layers: LAYERS.map(function copyLayer(layer) {
        return { id: layer.id, label: layer.label, nodes: byLayer[layer.id] };
      }),
      nodes: nodes,
      edges: edges,
      by_id: included,
      generated_at: safeText(overview.generated_at || objectOf(overview.summary).generated_at, 48),
    };
  }

  function normalizeMermaid(payload) {
    var overview = overviewOf(payload);
    var raw = objectOf(overview.mermaid);
    var source = typeof raw.source === "string" ? raw.source.trim() : "";
    if (
      !source ||
      source.length > 32768 ||
      !/^flowchart LR(?:\r?\n|$)/.test(source)
    ) {
      source = "";
    }
    var mode = safeId(raw.mode, "").toLowerCase();
    if (mode !== "semantic" && mode !== "aggregate_fallback") mode = "";
    var status = safeId(raw.status, "").toLowerCase();
    if (status !== "completed" && status !== "partial") status = "";
    return {
      source: source,
      mode: mode,
      status: status,
      coverage_rate: unitRate(raw.coverage_rate),
    };
  }

  function normalizeJob(payload) {
    var outer = objectOf(payload);
    var candidates = [outer.analysis_job, outer.job, outer.active_analysis];
    if (outer.id != null && outer.status != null) candidates.unshift(outer);
    if ((outer.job_id != null || outer.analysis_id != null) && outer.status != null) {
      candidates.unshift(outer);
    }
    var analysis = objectOf(outer.analysis);
    if (analysis.id != null && analysis.status != null) candidates.push(analysis);
    var source = {};
    for (var i = 0; i < candidates.length; i += 1) {
      if (Object.keys(objectOf(candidates[i])).length) {
        source = objectOf(candidates[i]);
        break;
      }
    }
    var rawId = source.id != null ? source.id : (source.job_id != null ? source.job_id : source.analysis_id);
    var id = safeId(rawId == null ? "" : String(rawId), "");
    var status = safeId(source.status, "").toLowerCase();
    if (!id || !status) return null;
    var phase = safeId(source.phase, status).toLowerCase();
    if (!JOB_PHASES[phase]) phase = status;
    var errorCounts = arrayOf(source.error_counts).map(function copyErrorCount(item) {
      var sourceItem = objectOf(item);
      return {
        code: safeId(sourceItem.error_code, "").toLowerCase(),
        count: count(sourceItem.evidence_count),
      };
    }).filter(function safeErrorCount(item) {
      return /^[a-z][a-z0-9_]{0,79}$/.test(item.code) && item.count > 0;
    }).sort(function sortErrors(left, right) {
      return left.code.localeCompare(right.code);
    }).slice(0, 12);
    return {
      id: id,
      status: status,
      phase: phase,
      progress: unitRate(source.progress),
      total_conversation_count: count(source.total_conversation_count || source.total_conversations),
      processed_conversation_count: count(source.processed_conversation_count || source.processed_conversations),
      total_message_count: count(source.total_message_count || source.total_messages),
      processed_message_count: count(source.processed_message_count || source.processed_messages),
      total_tenant_count: count(source.total_tenant_count),
      completed_tenant_count: count(source.completed_tenant_count),
      failed_tenant_count: count(source.failed_tenant_count),
      total_batch_count: count(source.total_batch_count),
      completed_batch_count: count(source.completed_batch_count),
      failed_batch_count: count(source.failed_batch_count),
      active_agent_count: count(source.active_agent_count),
      agent_limit: Math.max(1, Math.min(24, count(source.agent_limit) || 1)),
      provider_request_count: count(source.provider_request_count || source.provider_calls),
      prompt_tokens: count(source.prompt_tokens),
      completion_tokens: count(source.completion_tokens),
      coverage_rate: unitRate(source.coverage_rate),
      heartbeat_at: safeText(source.heartbeat_at, 64),
      last_progress_at: safeText(source.last_progress_at, 64),
      error_counts: errorCounts,
      error_code: safeId(source.error_code, ""),
      trigger: safeId(source.trigger_kind || source.trigger || source.trigger_type, "").toLowerCase(),
    };
  }

  function normalizeAutomation(payload) {
    var outer = objectOf(payload);
    var analysis = objectOf(outer.analysis);
    var overview = objectOf(outer.overview);
    var candidates = [
      outer.automation,
      outer.analysis_automation,
      outer.scheduler,
      analysis.automation,
      analysis.analysis_automation,
      overview.automation,
      overview.analysis_automation,
    ];
    var source = null;
    for (var i = 0; i < candidates.length; i += 1) {
      if (Object.keys(objectOf(candidates[i])).length) {
        source = objectOf(candidates[i]);
        break;
      }
    }
    if (!source) return null;
    var enabled = source.enabled === true;
    var state = safeId(source.state || source.status, enabled ? "scheduled" : "disabled").toLowerCase();
    if (!AUTOMATION_STATES[state]) state = enabled ? "scheduled" : "disabled";
    var intervalSeconds = count(source.interval_seconds || source.cadence_seconds);
    if (!intervalSeconds) intervalSeconds = count(source.interval_minutes) * 60;
    return {
      enabled: enabled,
      state: state,
      interval_seconds: intervalSeconds,
      window_days: count(source.window_days),
      last_run_at: safeText(source.last_run_at || source.last_enqueued_at, 64),
      next_run_at: safeText(source.next_run_at || source.next_analysis_at, 64),
      last_job_id: safeId(source.last_job_id == null ? "" : String(source.last_job_id), ""),
      last_status: safeId(source.last_status, "").toLowerCase(),
      error_code: safeId(source.error_code, ""),
    };
  }

  function install() {
    var React = global.React;
    var W2 = global.W2;
    if (!React || !W2 || !W2.PAGES || typeof W2.PAGES.optimizer !== "function") return false;
    if (W2.PAGES.optimizer[WRAPPED]) return true;

    var h = React.createElement;
    var useEffect = React.useEffect;
    var useMemo = React.useMemo;
    var useRef = React.useRef;
    var useState = React.useState;
    var BaseOptimizer = W2.PAGES.optimizer;

    function tr(key, params) {
      if (global.W2_LANG && typeof global.W2_LANG.t === "function") {
        return global.W2_LANG.t(key, params);
      }
      return key;
    }

    if (global.W2_LANG && typeof global.W2_LANG.addEN === "function") {
      global.W2_LANG.addEN({
        "AI 需求摩擦拓撲": "AI need-friction topology",
        "完整語義分析": "Run full semantic analysis",
        "立即重新分析（可選）": "Run again now (optional)",
        "刷新拓撲": "Refresh topology",
        "分析視窗": "Analysis window",
        "近 {n} 天": "Last {n} days",
        "正在載入聚合拓撲…": "Loading aggregate topology…",
        "尚未產生語義拓撲": "No semantic topology yet",
        "自動分析完成後，這裡會顯示需求、意圖、指令集、能力、摩擦與結果之間的聚合路徑。": "After an automatic analysis completes, aggregate paths across needs, intents, instruction sets, capabilities, friction, and outcomes appear here.",
        "僅顯示聚合節點與計數，不顯示對話正文或使用者身份。": "Only aggregate nodes and counts are shown; conversation text and user identities are never rendered.",
        "本機規則會先遮罩已知的身份、地址、專案與敏感特徵型態，再交由已配置的 AI 供應商分類；這是保護性遮罩，不是匿名化保證，平台只保存聚合結果。": "Local rules first mask known identity, address, project, and sensitive-trait patterns before classification by the configured AI provider. This is a protective mask, not an anonymity guarantee; the platform stores only aggregate results.",
        "本期範圍為啟用公司內的 AI 秘書對話；個人模式、平台管理對話與人際協作訊息不納入。": "This release covers AI Secretary conversations in active companies; personal mode, platform-administration conversations, and human collaboration messages are excluded.",
        "拓撲分析請求失敗": "Topology analysis request failed",
        "處理進度": "Processing progress",
        "已處理對話": "Conversations processed",
        "已處理訊息": "Messages processed",
        "公司進度": "Company progress",
        "批次進度": "Batch progress",
        "活躍 Agents": "Active agents",
        "失敗批次": "Failed batches",
        "最後進度": "Last progress",
        "錯誤分類": "Error categories",
        "模型請求": "Model requests",
        "本次 Token": "Tokens this run",
        "自動分析": "Automatic analysis",
        "自動分析已啟用": "Automatic analysis enabled",
        "自動分析未啟用": "Automatic analysis disabled",
        "自動排程狀態未回報": "Automatic schedule status not reported",
        "系統會依排程自動執行；手動操作只用於需要立即更新時。": "The system runs automatically on schedule; the manual action is only for an immediate refresh.",
        "後端明確回報自動分析未啟用。": "The backend explicitly reports that automatic analysis is disabled.",
        "後端沒有回傳排程狀態；不據此推定自動分析正在運作。": "The backend did not return schedule status; this UI does not assume automatic analysis is running.",
        "排程狀態": "Schedule state",
        "運行頻率": "Run frequency",
        "下次運行": "Next run",
        "上次排程": "Last scheduled run",
        "上次結果": "Last result",
        "預設視窗": "Default window",
        "自動觸發": "Automatic trigger",
        "手動觸發": "Manual trigger",
        "拓撲圖例": "Topology legend",
        "正常流": "Observed flow",
        "阻塞流": "Blocked flow",
        "高摩擦節點": "High-friction node",
        "節點詳情": "Node detail",
        "對話數": "Conversations",
        "公司數": "Companies",
        "摩擦數": "Friction signals",
        "摩擦率": "Friction rate",
        "阻塞分數": "Blocker score",
        "置信度": "Confidence",
        "指令集": "Instruction set",
        "歸因品質": "Attribution quality",
        "文字版拓撲": "Text topology",
        "Mermaid 圖源": "Mermaid source",
        "受驗證 Mermaid 圖源": "Validated Mermaid source",
        "部分覆蓋": "Partial coverage",
        "完整語義": "Complete semantic coverage",
        "聚合回退": "Aggregate fallback",
        "本圖使用已完成批次的安全聚合結果生成；部分批次未通過結構或隱私校驗，因此不能視為完整語義分析。": "This graph is generated from safe aggregate results in completed batches. Some batches did not pass structure or privacy validation, so it must not be treated as a complete semantic analysis.",
        "Mermaid 僅作為可核對的受控圖源顯示；前端不執行模型回傳的任意指令。": "Mermaid is shown only as a reviewable, constrained graph source; the frontend does not execute arbitrary model-returned directives.",
        "層級": "Layer",
        "節點": "Node",
        "連線": "Connections",
        "沒有可顯示的聚合節點。": "No aggregate nodes are available.",
      });
    }

    function apiGet(url, signal) {
      if (typeof W2.json !== "function") return Promise.reject(new Error("api_unavailable"));
      return W2.json(url, { signal: signal });
    }

    function apiPost(url, body, signal) {
      if (typeof W2.post !== "function") return Promise.reject(new Error("api_unavailable"));
      return W2.post(url, body, { signal: signal });
    }

    function errorCodeOf(reason) {
      var candidate = objectOf(reason);
      return safeId(candidate.code || candidate.error_code, "request_failed");
    }

    function nodeAriaLabel(node) {
      return [
        node.label,
        tr("對話數") + " " + displayNumber(node.conversation_count),
        tr("摩擦率") + " " + percent(node.friction_rate),
        tr("阻塞分數") + " " + Math.round(node.blocker_score),
      ].join(". ");
    }

    function TopologyLegend() {
      return h("div", { className: "optimizer-topology-legend", "aria-label": tr("拓撲圖例") },
        h("span", null, h("i", { className: "optimizer-legend-line" }), tr("正常流")),
        h("span", null, h("i", { className: "optimizer-legend-line is-blocked" }), tr("阻塞流")),
        h("span", null, h("i", { className: "optimizer-legend-node" }), tr("高摩擦節點"))
      );
    }

    function AnalysisProgress(props) {
      var job = props.job;
      if (!job) return null;
      var total = job.total_conversation_count;
      var processed = job.processed_conversation_count;
      var terminal = !!TERMINAL_JOB_STATES[job.status];
      var progressValue = job.progress;
      if (!progressValue && total) progressValue = Math.min(1, processed / total);
      var statusText = job.status.toUpperCase() + " · " + job.phase.replace(/_/g, " ").toUpperCase();
      var triggerText = job.trigger === "automatic" || job.trigger === "scheduled"
        ? tr("自動觸發")
        : (job.trigger === "manual" ? tr("手動觸發") : "");
      return h("div", {
        className: "optimizer-analysis-progress" + (terminal ? " is-terminal" : ""),
        role: "status",
        "aria-live": "polite",
      },
      h("div", { className: "optimizer-progress-heading" },
        h("span", { className: "optimizer-kicker" }, tr("處理進度") + (triggerText ? " · " + triggerText : "")),
        h("strong", { className: "optimizer-mono" }, statusText)
      ),
      h("progress", {
        max: 1,
        value: progressValue,
        "aria-label": tr("已處理對話"),
      }),
      h("div", { className: "optimizer-progress-metrics" },
        h("span", null, tr("已處理對話"), h("b", null, displayNumber(processed) + " / " + displayNumber(total))),
        h("span", null, tr("已處理訊息"), h("b", null, displayNumber(job.processed_message_count) + " / " + displayNumber(job.total_message_count))),
        h("span", null, tr("公司進度"), h("b", null, displayNumber(job.completed_tenant_count) + " / " + displayNumber(job.total_tenant_count))),
        h("span", null, tr("批次進度"), h("b", null, displayNumber(job.completed_batch_count) + " / " + displayNumber(job.total_batch_count))),
        h("span", null, tr("活躍 Agents"), h("b", null, displayNumber(job.active_agent_count) + " / " + displayNumber(job.agent_limit))),
        h("span", null, tr("失敗批次"), h("b", null, displayNumber(job.failed_batch_count))),
        h("span", null, tr("模型請求"), h("b", null, displayNumber(job.provider_request_count))),
        h("span", null, tr("本次 Token"), h("b", null, displayNumber(job.prompt_tokens + job.completion_tokens)))
      ),
      h("div", { className: "optimizer-progress-live" },
        h("span", null, tr("最後進度") + " · " + timestamp(job.last_progress_at || job.heartbeat_at)),
        job.error_counts.length ? h("span", null,
          tr("錯誤分類") + " · " + job.error_counts.map(function renderError(item) {
            return item.code + " ×" + displayNumber(item.count);
          }).join(" · ")
        ) : null
      ),
      job.error_code ? h("div", { className: "optimizer-progress-error", role: "alert" }, job.error_code) : null
      );
    }

    function AutomationStatus(props) {
      var automation = props.automation;
      if (!automation) {
        return h("section", {
          className: "optimizer-automation-status is-unknown",
          role: "status",
          "aria-live": "polite",
        },
        h("div", { className: "optimizer-automation-heading" },
          h("span", { className: "optimizer-kicker" }, tr("自動分析")),
          h("strong", null, tr("自動排程狀態未回報"))
        ),
        h("p", null, tr("後端沒有回傳排程狀態；不據此推定自動分析正在運作。"))
        );
      }
      var enabled = automation.enabled === true;
      var description = enabled
        ? tr("系統會依排程自動執行；手動操作只用於需要立即更新時。")
        : tr("後端明確回報自動分析未啟用。");
      var lastResult = automation.last_status ? automation.last_status.toUpperCase() : "—";
      if (automation.last_job_id) lastResult += " · #" + automation.last_job_id;
      return h("section", {
        className: "optimizer-automation-status " + (enabled ? "is-enabled" : "is-disabled"),
        role: automation.error_code ? "alert" : "status",
        "aria-live": "polite",
      },
      h("div", { className: "optimizer-automation-heading" },
        h("span", { className: "optimizer-kicker" }, tr("自動分析")),
        h("strong", null, enabled ? tr("自動分析已啟用") : tr("自動分析未啟用"))
      ),
      h("p", null, description),
      h("dl", null,
        h("div", null, h("dt", null, tr("排程狀態")), h("dd", { className: "optimizer-mono" }, automation.state.toUpperCase())),
        h("div", null, h("dt", null, tr("運行頻率")), h("dd", { className: "optimizer-mono" }, scheduleEvery(automation.interval_seconds))),
        h("div", null, h("dt", null, tr("下次運行")), h("dd", { className: "optimizer-mono" }, timestamp(automation.next_run_at))),
        h("div", null, h("dt", null, tr("上次排程")), h("dd", { className: "optimizer-mono" }, timestamp(automation.last_run_at))),
        h("div", null, h("dt", null, tr("上次結果")), h("dd", { className: "optimizer-mono" }, lastResult)),
        h("div", null, h("dt", null, tr("預設視窗")), h("dd", { className: "optimizer-mono" }, automation.window_days ? tr("近 {n} 天", { n: automation.window_days }) : "—"))
      ),
      automation.error_code ? h("div", { className: "optimizer-progress-error" }, automation.error_code) : null
      );
    }

    function TopologyDetail(props) {
      var node = props.node;
      if (!node) return null;
      var layer = LAYERS[LAYER_INDEX[node.layer]];
      var facts = [
        [tr("層級"), layer ? layer.label : node.layer],
        [tr("對話數"), displayNumber(node.conversation_count)],
        [tr("公司數"), displayNumber(node.tenant_count)],
        [tr("摩擦數"), displayNumber(node.friction_count)],
        [tr("摩擦率"), percent(node.friction_rate)],
        [tr("阻塞分數"), Math.round(node.blocker_score) + " / 100"],
        [tr("置信度"), percent(node.confidence)],
      ];
      if (node.instruction_set_key) facts.push([tr("指令集"), node.instruction_set_key]);
      if (node.lineage_quality !== "unknown") facts.push([tr("歸因品質"), node.lineage_quality.toUpperCase()]);
      return h("aside", {
        id: "optimizer-topology-node-detail",
        className: "optimizer-topology-detail",
        "aria-labelledby": "optimizer-topology-detail-title",
      },
      h("span", { className: "optimizer-kicker" }, tr("節點詳情")),
      h("h3", { id: "optimizer-topology-detail-title" }, node.label),
      h("dl", null, facts.map(function renderFact(fact) {
        return h("div", { key: fact[0] }, h("dt", null, fact[0]), h("dd", null, fact[1]));
      })),
      h("p", { className: "optimizer-privacy-note" }, tr("僅顯示聚合節點與計數，不顯示對話正文或使用者身份。"))
      );
    }

    function TextTopology(props) {
      var model = props.model;
      return h("details", { className: "optimizer-topology-fallback", open: true },
        h("summary", null, tr("文字版拓撲")),
        h("div", { className: "optimizer-topology-table-wrap" },
          h("table", { className: "optimizer-topology-table" },
            h("caption", null, tr("僅顯示聚合節點與計數，不顯示對話正文或使用者身份。")),
            h("thead", null, h("tr", null,
              h("th", { scope: "col" }, tr("層級")),
              h("th", { scope: "col" }, tr("節點")),
              h("th", { scope: "col" }, tr("對話數")),
              h("th", { scope: "col" }, tr("摩擦率")),
              h("th", { scope: "col" }, tr("阻塞分數"))
            )),
            h("tbody", null, model.nodes.map(function renderRow(node) {
              var layer = LAYERS[LAYER_INDEX[node.layer]];
              return h("tr", { key: node.id },
                h("td", { className: "optimizer-mono" }, layer ? layer.label : node.layer),
                h("th", { scope: "row" }, node.label),
                h("td", null, displayNumber(node.conversation_count)),
                h("td", null, percent(node.friction_rate)),
                h("td", null, Math.round(node.blocker_score))
              );
            }))
          )
        ),
        h("h4", null, tr("連線")),
        h("ul", { className: "optimizer-topology-edge-list" }, model.edges.map(function renderEdge(edge) {
          var source = model.by_id[edge.source];
          var target = model.by_id[edge.target];
          return h("li", { key: edge.id },
            (source ? source.label : edge.source) + " → " + (target ? target.label : edge.target) +
            " · " + displayNumber(edge.conversation_count)
          );
        }))
      );
    }

    function MermaidSource(props) {
      var mermaid = props.mermaid;
      if (!mermaid || !mermaid.source) return null;
      var mode = mermaid.mode === "aggregate_fallback"
        ? tr("聚合回退")
        : tr("完整語義");
      return h("details", { className: "optimizer-mermaid-source" },
        h("summary", null,
          tr("受驗證 Mermaid 圖源"),
          h("span", { className: "optimizer-mono" },
            mode + " · " + percent(mermaid.coverage_rate)
          )
        ),
        h("p", null, tr("Mermaid 僅作為可核對的受控圖源顯示；前端不執行模型回傳的任意指令。")),
        h("pre", null, h("code", null, mermaid.source))
      );
    }

    function MermaidCoverageNotice(props) {
      var mermaid = props.mermaid;
      if (!mermaid || (mermaid.status !== "partial" && mermaid.mode !== "aggregate_fallback")) {
        return null;
      }
      return h("div", {
        className: "optimizer-mermaid-notice",
        role: "status",
        "aria-live": "polite",
      },
      h("strong", null, tr("部分覆蓋") + " · " + percent(mermaid.coverage_rate)),
      h("p", null, tr("本圖使用已完成批次的安全聚合結果生成；部分批次未通過結構或隱私校驗，因此不能視為完整語義分析。"))
      );
    }

    function TopologyMap(props) {
      var model = props.model;
      var selectedId = props.selectedId;
      var onSelect = props.onSelect;
      var refs = useRef(Object.create(null));
      var nodeWidth = 188;
      var nodeHeight = 80;
      var laneWidth = 238;
      var rowHeight = 116;
      var headerHeight = 64;
      var maxRows = Math.max.apply(null, model.layers.map(function layerSize(layer) { return layer.nodes.length; }).concat([1]));
      var canvasWidth = model.layers.length * laneWidth;
      var canvasHeight = headerHeight + maxRows * rowHeight + 30;
      var positions = Object.create(null);
      model.layers.forEach(function positionLayer(layer, layerIndex) {
        layer.nodes.forEach(function positionNode(node, row) {
          positions[node.id] = {
            x: layerIndex * laneWidth + 24,
            y: headerHeight + row * rowHeight,
          };
        });
      });
      var related = Object.create(null);
      if (selectedId) {
        related[selectedId] = true;
        model.edges.forEach(function indexRelated(edge) {
          if (edge.source === selectedId || edge.target === selectedId) {
            related[edge.source] = true;
            related[edge.target] = true;
          }
        });
      }

      function moveFocus(node, direction) {
        var layerIndex = LAYER_INDEX[node.layer];
        var currentLayer = model.layers[layerIndex];
        var target = null;
        if (direction === "ArrowUp" || direction === "ArrowDown") {
          var delta = direction === "ArrowUp" ? -1 : 1;
          var nextRow = Math.max(0, Math.min(currentLayer.nodes.length - 1, node.row + delta));
          target = currentLayer.nodes[nextRow];
        } else {
          var layerDelta = direction === "ArrowLeft" ? -1 : 1;
          var nextLayer = model.layers[layerIndex + layerDelta];
          if (nextLayer && nextLayer.nodes.length) {
            target = nextLayer.nodes[Math.min(node.row, nextLayer.nodes.length - 1)];
          }
        }
        if (target && refs.current[target.id]) {
          onSelect(target.id);
          refs.current[target.id].focus();
        }
      }

      return h("div", { className: "optimizer-topology-viewport" },
        h("div", {
          className: "optimizer-topology-canvas",
          style: { width: canvasWidth + "px", height: canvasHeight + "px" },
          role: "group",
          "aria-label": tr("AI 需求摩擦拓撲"),
        },
        model.layers.map(function renderLane(layer, index) {
          return h("div", {
            className: "optimizer-topology-lane",
            key: layer.id,
            style: { left: (index * laneWidth) + "px", width: laneWidth + "px" },
            "aria-hidden": "true",
          },
          h("span", null, String(index + 1).padStart(2, "0")),
          h("strong", null, layer.label)
          );
        }),
        h("svg", {
          className: "optimizer-topology-edges",
          width: canvasWidth,
          height: canvasHeight,
          viewBox: "0 0 " + canvasWidth + " " + canvasHeight,
          "aria-hidden": "true",
          focusable: "false",
        }, model.edges.map(function renderPath(edge) {
          var from = positions[edge.source];
          var to = positions[edge.target];
          if (!from || !to) return null;
          var sx = from.x + nodeWidth;
          var sy = from.y + nodeHeight / 2;
          var tx = to.x;
          var ty = to.y + nodeHeight / 2;
          var middle = sx + Math.max(18, (tx - sx) / 2);
          var active = selectedId && (edge.source === selectedId || edge.target === selectedId);
          var muted = selectedId && !active;
          return h("path", {
            key: edge.id,
            className: "optimizer-topology-edge" + (edge.blocked ? " is-blocked" : "") +
              (active ? " is-active" : "") + (muted ? " is-muted" : ""),
            d: "M " + sx + " " + sy + " H " + middle + " V " + ty + " H " + tx,
            style: { strokeWidth: Math.max(1, Math.min(5, 1 + Math.log1p(edge.conversation_count))) },
            vectorEffect: "non-scaling-stroke",
          });
        })),
        model.nodes.map(function renderNode(node) {
          var position = positions[node.id];
          var selected = node.id === selectedId;
          var muted = selectedId && !related[node.id];
          var high = node.severity === "critical" || node.severity === "high" || node.blocker_score >= 60;
          return h("button", {
            type: "button",
            key: node.id,
            ref: function rememberNode(element) { refs.current[node.id] = element; },
            className: "optimizer-topology-node" + (selected ? " is-selected" : "") +
              (muted ? " is-muted" : "") + (high ? " is-blocker" : ""),
            style: { left: position.x + "px", top: position.y + "px", width: nodeWidth + "px", height: nodeHeight + "px" },
            "data-node-id": node.id,
            "aria-label": nodeAriaLabel(node),
            "aria-pressed": selected,
            "aria-controls": "optimizer-topology-node-detail",
            onClick: function selectNode() { onSelect(node.id); },
            onFocus: function selectFocusedNode() { onSelect(node.id); },
            onKeyDown: function navigateNodes(event) {
              if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].indexOf(event.key) >= 0) {
                event.preventDefault();
                moveFocus(node, event.key);
              }
            },
          },
          h("span", { className: "optimizer-node-kind" }, node.kind.replace(/[_-]/g, " ")),
          h("strong", null, node.label),
          h("span", { className: "optimizer-node-metric" }, displayNumber(node.conversation_count) + " · " + percent(node.friction_rate))
          );
        }))
      );
    }

    function TopologyPanel() {
      var _windowState = useState(30);
      var windowDays = _windowState[0];
      var setWindowDays = _windowState[1];
      var _overviewState = useState(null);
      var overview = _overviewState[0];
      var setOverview = _overviewState[1];
      var _jobState = useState(null);
      var job = _jobState[0];
      var setJob = _jobState[1];
      var _automationState = useState(null);
      var automation = _automationState[0];
      var setAutomation = _automationState[1];
      var _loadingState = useState(true);
      var loading = _loadingState[0];
      var setLoading = _loadingState[1];
      var _analyzingState = useState(false);
      var analyzing = _analyzingState[0];
      var setAnalyzing = _analyzingState[1];
      var _errorState = useState("");
      var errorCode = _errorState[0];
      var setErrorCode = _errorState[1];
      var _reloadState = useState(0);
      var reloadNo = _reloadState[0];
      var setReloadNo = _reloadState[1];
      var _selectedState = useState("");
      var selectedId = _selectedState[0];
      var setSelectedId = _selectedState[1];
      var analyzeController = useRef(null);

      var model = useMemo(function buildModel() {
        return normalizeTopology(overview || {});
      }, [overview]);
      var mermaid = useMemo(function buildMermaid() {
        return normalizeMermaid(overview || {});
      }, [overview]);
      var selected = model.by_id[selectedId] || model.nodes[0] || null;

      useEffect(function loadOverviewEffect() {
        var controller = new AbortController();
        setLoading(true);
        setErrorCode("");
        apiGet("/api/platform/optimizer/overview?window_days=" + encodeURIComponent(windowDays), controller.signal)
          .then(function acceptOverview(payload) {
            if (controller.signal.aborted) return;
            setOverview(overviewOf(payload));
            setAutomation(normalizeAutomation(payload));
            var active = normalizeJob(payload);
            if (active && !TERMINAL_JOB_STATES[active.status]) {
              setJob(active);
              setAnalyzing(true);
            } else {
              setJob(null);
              setAnalyzing(false);
            }
          })
          .catch(function rejectOverview(reason) {
            if (!controller.signal.aborted) setErrorCode(errorCodeOf(reason));
          })
          .finally(function finishOverview() {
            if (!controller.signal.aborted) setLoading(false);
          });
        return function abortOverview() { controller.abort(); };
      }, [windowDays, reloadNo]);

      useEffect(function pollAnalysisEffect() {
        if (!job || !job.id || TERMINAL_JOB_STATES[job.status]) return undefined;
        var stopped = false;
        var timer = null;
        var controller = null;

        function refreshAfterCompletion(payload) {
          var completedOverview = overviewOf(payload);
          if (Object.keys(objectOf(completedOverview.topology)).length) {
            setOverview(completedOverview);
            return;
          }
          controller = new AbortController();
          apiGet("/api/platform/optimizer/overview?window_days=" + encodeURIComponent(windowDays), controller.signal)
            .then(function acceptLatest(latest) {
              if (!stopped && !controller.signal.aborted) setOverview(overviewOf(latest));
            })
            .catch(function rejectLatest(reason) {
              if (!stopped && !controller.signal.aborted) setErrorCode(errorCodeOf(reason));
            });
        }

        function tick() {
          timer = global.setTimeout(function requestJob() {
            if (stopped) return;
            controller = new AbortController();
            apiGet("/api/platform/optimizer/analyses/" + encodeURIComponent(job.id), controller.signal)
              .then(function acceptJob(payload) {
                if (stopped || controller.signal.aborted) return;
                var next = normalizeJob(payload);
                if (!next) {
                  setErrorCode("invalid_job_contract");
                  return;
                }
                setJob(next);
                if (TERMINAL_JOB_STATES[next.status]) {
                  setAnalyzing(false);
                  if (next.status === "completed" || next.status === "partial") refreshAfterCompletion(payload);
                  else setErrorCode(next.error_code || "analysis_failed");
                  return;
                }
                tick();
              })
              .catch(function rejectJob(reason) {
                if (stopped || controller.signal.aborted) return;
                setErrorCode(errorCodeOf(reason));
                timer = global.setTimeout(tick, POLL_DELAY_MS * 2);
              });
          }, POLL_DELAY_MS);
        }

        tick();
        return function stopPolling() {
          stopped = true;
          if (timer != null) global.clearTimeout(timer);
          if (controller) controller.abort();
        };
      }, [job && job.id, windowDays]);

      useEffect(function discoverAutomaticAnalysisEffect() {
        if (job && job.id && !TERMINAL_JOB_STATES[job.status]) return undefined;
        var stopped = false;
        var timer = null;
        var controller = null;

        function discover() {
          if (stopped) return;
          controller = new AbortController();
          apiGet(
            "/api/platform/optimizer/analyses/active?window_days=" + encodeURIComponent(windowDays),
            controller.signal
          ).then(function acceptActive(payload) {
            if (stopped || controller.signal.aborted) return;
            var active = normalizeJob(payload);
            if (active && !TERMINAL_JOB_STATES[active.status]) {
              setJob(active);
              setAnalyzing(true);
              setErrorCode("");
            }
          }).catch(function rejectActive(reason) {
            if (!stopped && !controller.signal.aborted) setErrorCode(errorCodeOf(reason));
          }).finally(function scheduleDiscovery() {
            if (!stopped) {
              timer = global.setTimeout(
                discover,
                global.document && global.document.hidden
                  ? DISCOVERY_DELAY_MS * 2
                  : DISCOVERY_DELAY_MS
              );
            }
          });
        }

        discover();
        return function stopDiscovery() {
          stopped = true;
          if (timer != null) global.clearTimeout(timer);
          if (controller) controller.abort();
        };
      }, [windowDays, job && job.id, job && job.status]);

      useEffect(function selectFirstNodeEffect() {
        if (!model.nodes.length) {
          setSelectedId("");
        } else if (!model.by_id[selectedId]) {
          setSelectedId(model.nodes[0].id);
        }
      }, [model, selectedId]);

      useEffect(function cleanupAnalyzeEffect() {
        return function abortAnalyze() {
          if (analyzeController.current) analyzeController.current.abort();
        };
      }, []);

      function analyze() {
        if (analyzing) return;
        if (analyzeController.current) analyzeController.current.abort();
        var controller = new AbortController();
        analyzeController.current = controller;
        setAnalyzing(true);
        setErrorCode("");
        apiPost("/api/platform/optimizer/analyze", { window_days: windowDays, analysis_depth: "full" }, controller.signal)
          .then(function acceptAnalysis(payload) {
            if (controller.signal.aborted) return;
            var nextJob = normalizeJob(payload);
            if (nextJob) {
              setJob(nextJob);
              if (TERMINAL_JOB_STATES[nextJob.status]) {
                setAnalyzing(false);
                setOverview(overviewOf(payload));
              }
              return;
            }
            /* Backward-compatible synchronous response. */
            setOverview(overviewOf(payload));
            setAnalyzing(false);
          })
          .catch(function rejectAnalysis(reason) {
            if (!controller.signal.aborted) {
              setErrorCode(errorCodeOf(reason));
              setAnalyzing(false);
            }
          })
          .finally(function finishAnalysis() {
            if (analyzeController.current === controller) analyzeController.current = null;
          });
      }

      return h("section", {
        className: "optimizer-topology",
        "aria-labelledby": "optimizer-topology-title",
      },
      h("header", { className: "optimizer-topology-head" },
        h("div", null,
          h("span", { className: "optimizer-kicker" }, "FEATURE 23 · MERMAID MAP"),
          h("h2", { id: "optimizer-topology-title" }, tr("AI 需求摩擦拓撲")),
          h("p", null, tr("僅顯示聚合節點與計數，不顯示對話正文或使用者身份。")),
          h("p", { className: "optimizer-topology-privacy-note" }, tr("本機規則會先遮罩已知的身份、地址、專案與敏感特徵型態，再交由已配置的 AI 供應商分類；這是保護性遮罩，不是匿名化保證，平台只保存聚合結果。")),
          h("p", { className: "optimizer-topology-privacy-note" }, tr("本期範圍為啟用公司內的 AI 秘書對話；個人模式、平台管理對話與人際協作訊息不納入。"))
        ),
        h("div", { className: "optimizer-topology-actions" },
          h("label", null,
            h("span", null, tr("分析視窗")),
            h("select", {
              value: windowDays,
              disabled: loading || analyzing,
              onChange: function changeWindow(event) { setWindowDays(Number(event.target.value)); },
            }, [7, 30, 90].map(function renderOption(days) {
              return h("option", { key: days, value: days }, tr("近 {n} 天", { n: days }));
            }))
          ),
          h("button", {
            type: "button",
            className: "optimizer-topology-button",
            disabled: loading || analyzing,
            onClick: function refresh() { setReloadNo(function increment(value) { return value + 1; }); },
          }, tr("刷新拓撲")),
          h("button", {
            type: "button",
            className: "optimizer-topology-button",
            disabled: loading || analyzing,
            onClick: analyze,
          }, analyzing ? tr("分析中…") : tr("立即重新分析（可選）"))
        )
      ),
      h(AutomationStatus, { automation: automation }),
      h(AnalysisProgress, { job: job }),
      h(MermaidCoverageNotice, { mermaid: mermaid }),
      errorCode ? h("div", { className: "optimizer-topology-alert", role: "alert" },
        h("strong", null, tr("拓撲分析請求失敗")), h("span", { className: "optimizer-mono" }, errorCode)
      ) : null,
      loading ? h("div", { className: "optimizer-topology-loading", role: "status" }, tr("正在載入聚合拓撲…")) : null,
      !loading && !model.nodes.length ? h("div", { className: "optimizer-topology-empty" },
        h("strong", null, tr("尚未產生語義拓撲")),
        h("p", null, tr("自動分析完成後，這裡會顯示需求、意圖、指令集、能力、摩擦與結果之間的聚合路徑。"))
      ) : null,
      model.nodes.length ? h(React.Fragment, null,
        h(TopologyLegend),
        h("div", { className: "optimizer-topology-layout" },
          h(TopologyMap, { model: model, selectedId: selected ? selected.id : "", onSelect: setSelectedId }),
          h(TopologyDetail, { node: selected })
        ),
        h(TextTopology, { model: model }),
        h(MermaidSource, { mermaid: mermaid })
      ) : null
      );
    }

    function WrappedOptimizer(props) {
      return h(React.Fragment, null,
        h(BaseOptimizer, props),
        props && props.isOwner === true ? h(TopologyPanel, { key: "optimizer-semantic-topology" }) : null
      );
    }

    WrappedOptimizer.displayName = "OptimizerWithSemanticTopology";
    WrappedOptimizer[WRAPPED] = true;
    WrappedOptimizer.__baseOptimizer = BaseOptimizer;
    W2.PAGES.optimizer = WrappedOptimizer;
    return true;
  }

  var attempts = 0;
  function retryInstall() {
    if (install()) return;
    attempts += 1;
    if (attempts < 120) global.setTimeout(retryInstall, attempts < 8 ? 0 : 25);
  }
  retryInstall();
})(window);
