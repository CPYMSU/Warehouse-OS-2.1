/* WAREHOUSE 2.0 · FEATURE 23 · owner-only cross-company AI optimization analysis */
(() => {
const W2 = window.W2;
const { t } = window.W2_LANG;
window.W2_LANG.addEN({
  "進化分析": "Evolution",
  "跨公司 AI 總領分析": "Cross-company AI optimization",
  "獨立研究 AI · 聚合分析秘書對話成效 · 持續保存問題、候選方案與快照": "Independent research AI · aggregate Secretary outcomes · persist findings, candidates and snapshots",
  "實驗性功能": "Experimental",
  "僅平台擁有者": "Platform owner only",
  "聚合資料邊界": "Aggregate data boundary",
  "此頁不接收或顯示原始對話、工具參數或原始模型回應；只接收經結構、敏感資料遮罩與群組門檻驗證的聚合拓撲、統計與優化方案。": "This page never receives or displays raw conversations, tool arguments, or raw model responses; it receives only aggregate topology, statistics, and proposals validated by schema, sensitive-data masking, and cohort thresholds.",
  "資料邊界驗證失敗，已停止呈現分析。": "The data-boundary check failed, so analysis rendering was stopped.",
  "分析視窗": "Analysis window",
  "近 {n} 天": "Last {n} days",
  "刷新快照": "Refresh snapshot",
  "立即分析": "Analyze now",
  "分析中…": "Analyzing…",
  "正在整理跨公司聚合資料…": "Preparing cross-company aggregate data…",
  "分析已完成並保存最新快照。": "Analysis completed and the latest snapshot was saved.",
  "分析載入失敗": "Analysis unavailable",
  "沒有把載入失敗顯示成零值；請重試或檢查平台優化器服務。": "A load failure is not shown as zero. Retry or inspect the platform optimizer service.",
  "重試": "Retry",
  "可分析公司": "Available companies",
  "公司覆蓋": "company coverage",
  "秘書對話": "Secretary conversations",
  "聚合計數": "aggregate count",
  "AI 運行": "AI runs",
  "完成率 {n}": "completion {n}",
  "總 Token": "Total tokens",
  "視窗用量": "window usage",
  "效果訊號": "Outcome signals",
  "只使用聚合結果與正式運行狀態，不以模型自評取代真實結果。": "Uses aggregate outcomes and authoritative run state; model self-evaluation never replaces real results.",
  "運行完成率": "Run completion",
  "運行失敗率": "Run failures",
  "確認完成率": "Confirmation completion",
  "回饋率": "Feedback rate",
  "平均耗時": "Average duration",
  "聚合訊息": "Aggregate messages",
  "確認事件": "Confirmation events",
  "回饋事件": "Feedback events",
  "問題發現": "Findings",
  "由跨公司訊號歸納的可驗證問題；不展示任何單一對話。": "Verifiable issues inferred from cross-company signals; no individual conversation is shown.",
  "目前沒有問題發現": "No findings yet",
  "完成一次分析後，問題模式會以版本化證據持續累積。": "After an analysis, versioned evidence will accumulate into problem patterns.",
  "證據 {n}": "{n} evidence points",
  "涉及 {n} 家公司": "Across {n} companies",
  "建議": "Recommendation",
  "候選方案": "Candidates",
  "每個方案都有狀態、風險與 revision；此頁不直接修改生產秘書。": "Every proposal carries status, risk and revision; this page never edits the production Secretary directly.",
  "目前沒有候選方案": "No candidates yet",
  "分析器提出的方案會保存在這裡，等待離線評估與治理。": "Optimizer proposals will be retained here for offline evaluation and governance.",
  "假設": "Hypothesis",
  "預期影響": "Expected impact",
  "風險": "Risk",
  "版本": "Revision",
  "建立於": "Created",
  "公司快照帳本": "Company snapshot ledger",
  "每家公司只保存本視窗的聚合計數與可用狀態。": "Stores only per-company aggregate counts and availability for this window.",
  "分析歷史": "Analysis history",
  "每次分析都保留聚合規模、發現與候選數量，供平台擁有者追蹤持續迭代。": "Each analysis retains aggregate scope and finding/candidate counts so platform owners can trace continuous iteration.",
  "尚無分析歷史": "No analysis history",
  "分析編號": "Analysis ID",
  "視窗": "Window",
  "覆蓋公司": "Companies",
  "發現": "Findings",
  "候選": "Candidates",
  "目標版本": "Objective",
  "分析引擎": "Engine",
  "建立者": "Created by",
  "公司": "Company",
  "狀態": "Status",
  "對話": "Conversations",
  "訊息": "Messages",
  "運行": "Runs",
  "完成": "Completed",
  "失敗": "Failed",
  "回饋": "Feedback",
  "確認": "Confirmations",
  "可用": "Available",
  "不可用": "Unavailable",
  "尚無公司快照": "No company snapshots",
  "資料生成於 {time}": "Generated {time}",
  "此功能只屬於有效的 Bonfire L11 平台擁有者。": "This feature is reserved for effective Bonfire L11 platform owners.",
  "當前登入沒有 is_platform_owner 權威標記，因此不會探測任何優化器端點。": "The current session has no authoritative is_platform_owner flag, so no optimizer endpoint will be probed.",
  "回總覽": "Back to overview",
  "連續演化實驗室": "Continuous Evolution Lab",
  "獨立合成公司 · 任務完成後立即進入下一個 · 真實 RBAC、路由與 Passkey 鏈": "Isolated synthetic company · immediately claims the next task · real RBAC, routing, and Passkey chain",
  "連續運行": "Continuous",
  "運行異常": "Runner unavailable",
  "已暫停": "Paused",
  "預算已耗盡": "Budget exhausted",
  "供應商限速中": "Provider rate limited",
  "暫停實驗": "Pause lab",
  "恢復實驗": "Resume lab",
  "正在更新…": "Updating…",
  "控制操作失敗": "Control action failed",
  "今日場景": "Cases today",
  "排隊場景": "Queued cases",
  "運行中場景": "Running cases",
  "成功場景": "Completed cases",
  "失敗場景": "Failed cases",
  "降級場景": "Degraded cases",
  "待核對結果": "Outcome unknown",
  "Passkey 完成": "Passkey completed",
  "目前場景": "Current case",
  "尚未領取場景": "No case is currently claimed",
  "最近心跳": "Last heartbeat",
  "最近活動": "Last activity",
  "控制狀態": "Control state",
  "進程狀態": "Process state",
  "任務階段": "Runner phase",
  "循環序號": "Cycle sequence",
  "連續失敗": "Consecutive failures",
  "最近領取嘗試": "Last claim attempt",
  "最近成功領取": "Last successful claim",
  "最近場景完成": "Last case finished",
  "最近穩定錯誤": "Last stable error",
  "實驗運行保護": "Experiment guardrails",
  "只顯示匯總用量與穩定停止原因；不接收或顯示原始需求、提示詞或對話。": "Shows only aggregate usage and stable stop reasons; it never receives or displays raw requirements, prompts, or transcripts.",
  "停止原因": "Stop reason",
  "已由硬性保護機制暫停": "Paused by a hard guardrail",
  "今日模型請求": "Model requests today",
  "今日模型 Token": "Model tokens today",
  "今日供應商耗時": "Provider time today",
  "滾動一分鐘請求": "Requests in rolling minute",
  "滾動一小時請求": "Requests in rolling hour",
  "硬上限 {n}": "Hard limit {n}",
  "UTC 重置": "UTC reset",
  "可重試時間": "Retry at",
  "{n} 秒後可重試": "Retry in {n} seconds",
  "今日模型請求已達上限": "Daily model request limit reached",
  "今日模型 Token 已達上限": "Daily model token limit reached",
  "今日模型 Token 餘額不足": "Insufficient daily model token headroom",
  "今日供應商耗時已達上限": "Daily provider-time limit reached",
  "每分鐘模型請求已達上限": "Per-minute model request limit reached",
  "每小時模型請求已達上限": "Per-hour model request limit reached",
  "實驗資料庫容量已達上限": "Experiment database size limit reached",
  "儲存空間已低於安全保留值": "Free disk space fell below the safety reserve",
  "今日實驗場景已達上限": "Daily experiment case limit reached",
  "實驗錯誤指紋": "Experiment error fingerprints",
  "只顯示穩定錯誤碼與聚合次數，不顯示需求正文、憑證或原始模型回應。": "Shows only stable error codes and aggregate counts, never requirement text, credentials, or raw model responses.",
  "目前沒有實驗錯誤": "No experiment errors yet",
  "Evolution Lab 載入失敗": "Evolution Lab unavailable",
});

const { useEffect, useMemo, useState } = React;
const { Band, Btn: B, Empty: EM, Folio, Icon: I, Kpi, Label: LB, Tag: T } = W2;
const WINDOW_OPTIONS = [7, 30, 90];
const objectOf = value => value && typeof value === "object" && !Array.isArray(value) ? value : {};
const arrayOf = value => Array.isArray(value) ? value : [];
const finite = value => Number.isFinite(Number(value)) ? Number(value) : null;
const count = value => {
  const parsed = finite(value);
  return parsed === null ? null : Math.max(0, Math.trunc(parsed));
};
const safeText = (value, limit = 700) => typeof value === "string"
  ? value.trim().slice(0, limit)
  : "";
const stableCode = value => {
  const code = safeText(value, 120).toLowerCase();
  return /^[a-z0-9][a-z0-9_:-]*$/.test(code) ? code : "";
};
const requiredLabCount = (source, key) => {
  if (
    !Object.prototype.hasOwnProperty.call(source, key) ||
    typeof source[key] !== "number" ||
    !Number.isFinite(source[key]) ||
    source[key] < 0
  ) throw new Error(t("Evolution Lab 載入失敗"));
  return Math.trunc(source[key]);
};
const labCount = (sourceObject, key, required = true) => required
  ? requiredLabCount(sourceObject, key)
  : count(sourceObject[key]);
const displayNumber = value => {
  const parsed = count(value);
  return parsed === null ? "—" : parsed.toLocaleString();
};
const percent = value => {
  const parsed = finite(value);
  if (parsed === null) return "—";
  const scaled = Math.abs(parsed) <= 1 ? parsed * 100 : parsed;
  return Math.max(0, scaled).toFixed(1).replace(/\.0$/, "") + "%";
};
const duration = value => {
  const parsed = finite(value);
  if (parsed === null) return "—";
  if (parsed < 1000) return Math.round(parsed) + " ms";
  return (parsed / 1000).toFixed(parsed < 10000 ? 1 : 0) + " s";
};
const timestamp = value => {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? safeText(String(value), 40) : parsed.toLocaleString();
};
const utcTimestamp = value => {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? safeText(String(value), 40)
    : parsed.toLocaleString(undefined, { timeZone: "UTC", timeZoneName: "short" });
};
const longDuration = value => {
  const parsed = finite(value);
  if (parsed === null) return "—";
  const seconds = Math.max(0, Math.round(parsed / 1000));
  if (seconds < 60) return seconds + " s";
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  if (minutes < 60) return minutes + " m " + remainder + " s";
  const hours = Math.floor(minutes / 60);
  return hours + " h " + (minutes % 60) + " m";
};

const normalizeOverview = payload => {
  const outer = objectOf(payload);
  const source = Object.keys(objectOf(outer.analysis)).length ? objectOf(outer.analysis) : outer;
  const feature = objectOf(source.feature);
  const privacy = objectOf(source.privacy);
  if (
    feature.owner_only !== true ||
    privacy.aggregate_only !== true ||
    privacy.raw_transcripts_exposed !== false
  ) {
    throw new Error(t("資料邊界驗證失敗，已停止呈現分析。"));
  }
  const summary = objectOf(source.summary);
  const metrics = objectOf(source.metrics);
  return {
    feature: {
      id: count(feature.id),
      key: safeText(feature.key, 80),
      experimental: feature.experimental === true,
      owner_only: true,
    },
    summary: {
      window_days: count(summary.window_days),
      generated_at: safeText(summary.generated_at, 80),
      tenant_count: count(summary.tenant_count),
      available_tenant_count: count(summary.available_tenant_count),
      conversation_count: count(summary.conversation_count),
      message_count: count(summary.message_count),
      run_count: count(summary.run_count),
      completed_run_count: count(summary.completed_run_count),
      failed_run_count: count(summary.failed_run_count),
      feedback_count: count(summary.feedback_count),
      confirmation_count: count(summary.confirmation_count),
      total_tokens: count(summary.total_tokens),
      avg_duration_ms: finite(summary.avg_duration_ms),
    },
    metrics: {
      completion_rate: finite(metrics.completion_rate),
      failure_rate: finite(metrics.failure_rate),
      confirmation_completion_rate: finite(metrics.confirmation_completion_rate),
      feedback_rate: finite(metrics.feedback_rate),
    },
    findings: arrayOf(source.findings).map((raw, index) => {
      const item = objectOf(raw);
      return {
        key: safeText(item.key, 120) || "finding-" + index,
        severity: safeText(item.severity, 24).toLowerCase() || "info",
        category: safeText(item.category, 80),
        title: safeText(item.title, 240),
        description: safeText(item.description),
        evidence_count: count(item.evidence_count),
        tenant_count: count(item.tenant_count),
        recommendation: safeText(item.recommendation),
      };
    }),
    candidates: arrayOf(source.candidates).map((raw, index) => {
      const item = objectOf(raw);
      return {
        id: safeText(String(item.id == null ? "" : item.id), 120) || "candidate-" + index,
        status: safeText(item.status, 40).toLowerCase() || "draft",
        title: safeText(item.title, 240),
        hypothesis: safeText(item.hypothesis),
        expected_impact: safeText(item.expected_impact, 500),
        risk_level: safeText(item.risk_level, 40).toLowerCase() || "unknown",
        revision: count(item.revision),
        created_at: safeText(item.created_at, 80),
      };
    }),
    snapshots: arrayOf(source.snapshots).map((raw, index) => {
      const item = objectOf(raw);
      return {
        key: safeText(item.tenant_slug, 100) || "tenant-" + index,
        tenant_slug: safeText(item.tenant_slug, 100),
        tenant_name: safeText(item.tenant_name, 160),
        available: item.available === true,
        conversation_count: count(item.conversation_count),
        message_count: count(item.message_count),
        run_count: count(item.run_count),
        completed_run_count: count(item.completed_run_count),
        failed_run_count: count(item.failed_run_count),
        feedback_count: count(item.feedback_count),
        confirmation_count: count(item.confirmation_count),
        total_tokens: count(item.total_tokens),
        avg_duration_ms: finite(item.avg_duration_ms),
      };
    }),
    analysis_history: arrayOf(source.analysis_history).map((raw, index) => {
      const item = objectOf(raw);
      return {
        key: safeText(String(item.id == null ? "" : item.id), 120) || "analysis-" + index,
        id: safeText(String(item.id == null ? "" : item.id), 120),
        window_days: count(item.window_days),
        tenant_count: count(item.tenant_count),
        available_tenant_count: count(item.available_tenant_count),
        finding_count: count(item.finding_count),
        candidate_count: count(item.candidate_count),
        created_by_username: safeText(item.created_by_username, 120),
        created_at: safeText(item.created_at, 80),
        objective_version: safeText(String(item.objective_version == null ? "" : item.objective_version), 120),
        analysis_engine: safeText(item.analysis_engine, 160),
      };
    }),
    privacy: { aggregate_only: true, raw_transcripts_exposed: false },
  };
};

const normalizeLabStatus = payload => {
  const source = objectOf(payload);
  const feature = objectOf(source.feature);
  if (
    feature.owner_only !== true ||
    feature.synthetic_only !== true ||
    feature.raw_transcripts_exposed !== false
  ) throw new Error(t("資料邊界驗證失敗，已停止呈現分析。"));
  const state = objectOf(source.state);
  if (state.ready !== true) {
    throw new Error(t("Evolution Lab 載入失敗"));
  }
  const today = objectOf(source.today);
  const rawBudget = objectOf(source.budget);
  const budgetMetrics = objectOf(rawBudget.metrics);
  const budgetLimits = objectOf(rawBudget.limits);
  const firstBudgetReason = arrayOf(rawBudget.reasons)
    .map(stableCode)
    .find(Boolean) || "";
  const stopReason = stableCode(
    state.stop_reason || rawBudget.reason || rawBudget.stop_reason
  ) || firstBudgetReason;
  const controlState = stableCode(state.control_state) || "not_ready";
  const processState = stableCode(state.process_state || state.runner_state) || "not_ready";
  return {
    state: {
      ready: true,
      enabled: state.enabled === true,
      control_state: controlState,
      process_state: processState,
      runner_state: processState,
      runner_phase: stableCode(state.runner_phase) || processState,
      runner_active: state.runner_active === true,
      process_active: state.process_active === true,
      work_healthy: state.work_healthy === true,
      heartbeat_stale: state.heartbeat_stale === true,
      heartbeat_at: safeText(state.heartbeat_at, 80),
      cycle_seq: labCount(state, "cycle_seq"),
      consecutive_failures: labCount(state, "consecutive_failures"),
      last_claim_attempt_at: safeText(state.last_claim_attempt_at, 80),
      last_claim_succeeded_at: safeText(state.last_claim_succeeded_at, 80),
      last_case_finished_at: safeText(state.last_case_finished_at, 80),
      last_error_code: stableCode(state.last_error_code),
      backoff_until: safeText(state.backoff_until, 80),
      last_activity_at: safeText(state.last_activity_at, 80),
      current_case_id: safeText(state.current_case_id, 120),
      current_domain: safeText(state.current_domain, 80),
      current_actor: safeText(state.current_actor, 120),
      started_at: safeText(state.started_at, 80),
      stop_reason: stopReason,
    },
    today: {
      date: safeText(today.date, 20),
      total: labCount(today, "total"),
      queued: labCount(today, "queued"),
      running: labCount(today, "running"),
      completed: labCount(today, "completed"),
      degraded: labCount(today, "degraded"),
      failed: labCount(today, "failed"),
      outcome_unknown: labCount(today, "outcome_unknown"),
      confirmation_count: labCount(today, "confirmation_count"),
      passkey_completed: labCount(today, "passkey_completed"),
    },
    budget: {
      exhausted: rawBudget.exhausted === true ||
        rawBudget.budget_exhausted === true || controlState === "budget_exhausted",
      rate_limited: rawBudget.rate_limited === true || controlState === "rate_limited",
      reason: stopReason,
      budget_day: safeText(rawBudget.budget_day, 20),
      reset_at: safeText(rawBudget.reset_at || rawBudget.utc_reset_at, 80),
      retry_at: safeText(rawBudget.retry_at, 80),
      retry_after_seconds: labCount(rawBudget, "retry_after_seconds"),
      metrics: {
        model_requests: labCount(budgetMetrics, "model_requests"),
        model_tokens: labCount(budgetMetrics, "model_tokens"),
        model_elapsed_ms: labCount(budgetMetrics, "model_elapsed_ms"),
        model_requests_rolling_minute: labCount(budgetMetrics, "model_requests_rolling_minute"),
        model_requests_rolling_hour: labCount(budgetMetrics, "model_requests_rolling_hour"),
      },
      limits: {
        max_daily_model_requests: labCount(budgetLimits, "max_daily_model_requests"),
        max_daily_model_tokens: labCount(budgetLimits, "max_daily_model_tokens"),
        max_daily_model_elapsed_ms: labCount(budgetLimits, "max_daily_model_elapsed_ms"),
        max_model_requests_per_minute: labCount(budgetLimits, "max_model_requests_per_minute"),
        max_model_requests_per_hour: labCount(budgetLimits, "max_model_requests_per_hour"),
      },
    },
    findings: arrayOf(source.findings).map((raw, index) => {
      const item = objectOf(raw);
      return {
        key: safeText(item.fingerprint, 120) || "lab-finding-" + index,
        code: safeText(item.code, 120) || "unknown",
        severity: safeText(item.severity, 24).toLowerCase() || "info",
        count: count(item.count),
        last_seen_at: safeText(item.last_seen_at, 80),
      };
    }),
  };
};

const LAB_STOP_REASON_LABELS = {
  daily_model_request_limit_reached: "今日模型請求已達上限",
  daily_model_token_limit_reached: "今日模型 Token 已達上限",
  daily_model_token_headroom_exhausted: "今日模型 Token 餘額不足",
  daily_model_elapsed_limit_reached: "今日供應商耗時已達上限",
  model_minute_rate_limit_reached: "每分鐘模型請求已達上限",
  model_hour_rate_limit_reached: "每小時模型請求已達上限",
  tenant_db_bytes_limit_reached: "實驗資料庫容量已達上限",
  disk_free_bytes_reserve_breached: "儲存空間已低於安全保留值",
  daily_case_limit_reached: "今日實驗場景已達上限",
};
const labStopReasonLabel = reason => reason
  ? t(LAB_STOP_REASON_LABELS[reason] || reason)
  : t("已由硬性保護機制暫停");
const hardNumberLimit = value => count(value) === null
  ? ""
  : t("硬上限 {n}", { n: displayNumber(value) });
const hardDurationLimit = value => count(value) === null
  ? ""
  : t("硬上限 {n}", { n: longDuration(value) });

const severityRank = { critical: 0, high: 1, medium: 2, low: 3, info: 4 };
const severityTone = severity => severity === "critical" || severity === "high"
  ? "bad"
  : severity === "medium" ? "warn" : severity === "low" ? "plain" : "ok";
const statusTone = status => status === "validated" || status === "active"
  ? "ok"
  : status === "rejected" || status === "failed" ? "bad"
    : status === "testing" || status === "queued" ? "warn" : "plain";
const riskTone = risk => risk === "critical" || risk === "high"
  ? "bad"
  : risk === "medium" ? "warn" : "plain";

const AdminMark = () => (
  <div className="row g8 wrap" style={{ paddingTop: 14 }}>
    <span className="label" style={{ color: "var(--red)" }}>ADMIN · FEATURE 23</span>
    <T tone="redinv">{t("實驗性功能")}</T>
    <T tone="plain">{t("僅平台擁有者")}</T>
  </div>
);

const Denied = () => (
  <>
    <AdminMark/>
    <Folio no="22" en="AI OPTIMIZER" title={t("跨公司 AI 總領分析")}
      sub={t("此功能只屬於有效的 Bonfire L11 平台擁有者。")}/>
    <div className="rise" style={{ borderTop: "2px solid var(--red)", padding: "42px 0 64px" }}>
      <div className="mono" style={{ color: "var(--red)", fontSize: 34, fontWeight: 800 }}>ACCESS DENIED</div>
      <p style={{ maxWidth: 680, marginTop: 16, fontSize: 13.5, lineHeight: 1.8 }}>
        {t("當前登入沒有 is_platform_owner 權威標記，因此不會探測任何優化器端點。")}
      </p>
      <B icon="arrow" style={{ marginTop: 18 }} onClick={() => { location.hash = "#/dashboard"; }}>{t("回總覽")}</B>
    </div>
  </>
);

const Metric = ({ label, value, note }) => (
  <div className="panel" style={{ padding: 16, minHeight: 112 }}>
    <LB dim>{t(label)}</LB>
    <div className="mono" style={{ fontSize: 29, fontWeight: 760, marginTop: 13 }}>{value}</div>
    {note && <div className="muted" style={{ fontSize: 10.5, marginTop: 8 }}>{note}</div>}
  </div>
);

const OptimizerMain = () => {
  const [windowDays, setWindowDays] = useState(30);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [lab, setLab] = useState(null);
  const [labError, setLabError] = useState("");
  const [labControlBusy, setLabControlBusy] = useState(false);
  const [labControlError, setLabControlError] = useState("");
  const [reloadNo, setReloadNo] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(""); setSnapshot(null);
    W2.json(
      "/api/platform/optimizer/overview?window_days=" + encodeURIComponent(windowDays),
      { signal: controller.signal }
    )
      .then(data => { if (!controller.signal.aborted) setSnapshot(normalizeOverview(data)); })
      .catch(reason => {
        if (!controller.signal.aborted && (!reason || reason.name !== "AbortError")) {
          setError((reason && reason.message) || String(reason));
        }
      })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [windowDays, reloadNo]);

  useEffect(() => {
    let controller = null;
    let timer = null;
    let disposed = false;
    setLab(null); setLabError("");
    const schedule = delay => {
      if (disposed) return;
      if (timer) window.clearTimeout(timer);
      timer = window.setTimeout(loadLab, delay);
    };
    const loadLab = () => {
      if (disposed) return;
      if (controller) controller.abort();
      controller = new AbortController();
      const request = controller;
      schedule(document.hidden ? 15000 : 10000);
      W2.json("/api/platform/evolution-lab/status", { signal: request.signal })
        .then(data => {
          if (!disposed && !request.signal.aborted) {
            const next = normalizeLabStatus(data);
            setLab(next);
            setLabError("");
            schedule(document.hidden ? 15000 : next.state.runner_active ? 2000 : 5000);
          }
        })
        .catch(reason => {
          if (!disposed && !request.signal.aborted && (!reason || reason.name !== "AbortError")) {
            setLabError((reason && reason.message) || String(reason));
            schedule(document.hidden ? 15000 : 5000);
          }
        });
    };
    const onVisibility = () => {
      if (disposed) return;
      if (document.hidden) schedule(15000);
      else loadLab();
    };
    document.addEventListener("visibilitychange", onVisibility);
    loadLab();
    return () => {
      disposed = true;
      document.removeEventListener("visibilitychange", onVisibility);
      if (timer) window.clearTimeout(timer);
      if (controller) controller.abort();
    };
  }, [reloadNo]);

  const setLabEnabled = async enabled => {
    if (labControlBusy) return;
    setLabControlBusy(true);
    setLabControlError("");
    try {
      await W2.post("/api/platform/evolution-lab/control", { enabled });
      setReloadNo(value => value + 1);
    } catch (reason) {
      setLabControlError((reason && reason.message) || String(reason));
    } finally {
      setLabControlBusy(false);
    }
  };

  const summary = snapshot ? snapshot.summary : {};
  const metrics = snapshot ? snapshot.metrics : {};
  const findings = useMemo(() => snapshot
    ? snapshot.findings.slice().sort((a, b) =>
        (severityRank[a.severity] ?? 9) - (severityRank[b.severity] ?? 9) ||
        (b.evidence_count || 0) - (a.evidence_count || 0))
    : [], [snapshot]);
  const candidates = snapshot ? snapshot.candidates : [];
  const snapshots = snapshot ? snapshot.snapshots : [];
  const analysisHistory = snapshot ? snapshot.analysis_history : [];
  const coverage = summary.tenant_count
    ? Math.round(((summary.available_tenant_count || 0) / summary.tenant_count) * 100) + "%"
    : "—";
  const labHealthy = !!(
    lab && lab.state.enabled && lab.state.runner_active && !lab.state.heartbeat_stale
  );
  const labBudgetExhausted = !!(lab && lab.budget.exhausted);
  const labRateLimited = !!(lab && lab.budget.rate_limited);
  const labStatusLabel = labBudgetExhausted
    ? t("預算已耗盡")
    : labRateLimited ? t("供應商限速中")
      : !lab || !lab.state.enabled ? t("已暫停")
        : labHealthy ? t("連續運行") : t("運行異常");
  const labStatusTone = labBudgetExhausted
    ? "bad"
    : labRateLimited || (lab && !lab.state.enabled) ? "warn"
      : labHealthy ? "ok" : "bad";
  const labRetryText = !lab ? "" : lab.budget.retry_at
    ? t("可重試時間") + " · " + utcTimestamp(lab.budget.retry_at)
    : lab.budget.retry_after_seconds
      ? t("{n} 秒後可重試", { n: displayNumber(lab.budget.retry_after_seconds) })
      : "";

  return (
    <>
      <AdminMark/>
      <Folio no="22" en="AI OPTIMIZER" title={t("跨公司 AI 總領分析")}
        sub={t("獨立研究 AI · 聚合分析秘書對話成效 · 持續保存問題、候選方案與快照")}
        right={<div className="row g8 wrap">
          <label className="row g6" style={{ fontSize: 11.5, fontWeight: 700 }}>
            <span>{t("分析視窗")}</span>
            <select className="field" value={windowDays} disabled={loading}
              onChange={event => setWindowDays(Number(event.target.value))}
              style={{ width: 116, height: 34, fontSize: 11.5 }}>
              {WINDOW_OPTIONS.map(days => <option value={days} key={days}>{t("近 {n} 天", { n: days })}</option>)}
            </select>
          </label>
          <B icon="refresh" disabled={loading} onClick={() => setReloadNo(value => value + 1)}>{t("刷新快照")}</B>
        </div>}/>
      {error && <div role="alert" className="panel" style={{ marginTop: 14, padding: 18, borderColor: "var(--red)" }}>
        <LB red>{t("分析載入失敗")}</LB>
        <div style={{ marginTop: 10, fontSize: 13, fontWeight: 700, color: "var(--red)", overflowWrap: "anywhere" }}>{error}</div>
        <div className="muted" style={{ marginTop: 8, fontSize: 11.5 }}>{t("沒有把載入失敗顯示成零值；請重試或檢查平台優化器服務。")}</div>
        <B size="sm" icon="refresh" style={{ marginTop: 13 }} onClick={() => setReloadNo(value => value + 1)}>{t("重試")}</B>
      </div>}
      {loading && <div className="step-line" style={{ marginTop: 22 }}><I name="refresh" size={11}/>{t("正在整理跨公司聚合資料…")}</div>}

      {labError && <div role="alert" className="panel" style={{ marginTop: 14, padding: 16, borderColor: "var(--red)" }}>
        <LB red>{t("Evolution Lab 載入失敗")}</LB>
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--red)", overflowWrap: "anywhere" }}>{labError}</div>
      </div>}
      {labControlError && <div role="alert" className="panel" style={{ marginTop: 14, padding: 16, borderColor: "var(--red)" }}>
        <LB red>{t("控制操作失敗")}</LB>
        <div style={{ marginTop: 8, fontSize: 12, color: "var(--red)", overflowWrap: "anywhere" }}>{labControlError}</div>
      </div>}
      {lab && <Band no="LAB" title={t("連續演化實驗室")}
        sub={t("獨立合成公司 · 任務完成後立即進入下一個 · 真實 RBAC、路由與 Passkey 鏈")}
        right={<div className="row g8 wrap">
          <T tone={labStatusTone} dot>
            {labStatusLabel}
          </T>
          <B size="sm" icon={lab.state.enabled ? "x" : "check"}
            disabled={labControlBusy}
            onClick={() => setLabEnabled(!lab.state.enabled)}>
            {labControlBusy ? t("正在更新…") : lab.state.enabled ? t("暫停實驗") : t("恢復實驗")}
          </B>
        </div>}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 10 }}>
          <Metric label="今日場景" value={displayNumber(lab.today.total)} note={lab.today.date}/>
          <Metric label="排隊場景" value={displayNumber(lab.today.queued)}/>
          <Metric label="運行中場景" value={displayNumber(lab.today.running)}/>
          <Metric label="成功場景" value={displayNumber(lab.today.completed)}/>
          <Metric label="失敗場景" value={displayNumber(lab.today.failed)}/>
          <Metric label="降級場景" value={displayNumber(lab.today.degraded)}/>
          <Metric label="待核對結果" value={displayNumber(lab.today.outcome_unknown)}/>
          <Metric label="Passkey 完成" value={displayNumber(lab.today.passkey_completed)}
            note={displayNumber(lab.today.confirmation_count) + " confirmations"}/>
        </div>
        <div className="panel" style={{
          marginTop: 12,
          padding: 14,
          borderColor: labBudgetExhausted ? "var(--red)" : labRateLimited ? "var(--warn)" : "var(--rule)",
        }}>
          <div className="row spread g10 wrap">
            <div style={{ flex: 1, minWidth: 240 }}>
              <LB>{t("實驗運行保護")}</LB>
              <div className="muted" style={{ marginTop: 5, fontSize: 11, lineHeight: 1.55 }}>
                {t("只顯示匯總用量與穩定停止原因；不接收或顯示原始需求、提示詞或對話。")}
              </div>
            </div>
            {(lab.budget.reason || labBudgetExhausted || labRateLimited) && <T
              tone={labBudgetExhausted ? "bad" : "warn"} dot>
              {t("停止原因")} · {labStopReasonLabel(lab.budget.reason)}
            </T>}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 10, marginTop: 12 }}>
            <Metric label="今日模型請求"
              value={displayNumber(lab.budget.metrics.model_requests)}
              note={hardNumberLimit(lab.budget.limits.max_daily_model_requests)}/>
            <Metric label="今日模型 Token"
              value={displayNumber(lab.budget.metrics.model_tokens)}
              note={hardNumberLimit(lab.budget.limits.max_daily_model_tokens)}/>
            <Metric label="今日供應商耗時"
              value={longDuration(lab.budget.metrics.model_elapsed_ms)}
              note={hardDurationLimit(lab.budget.limits.max_daily_model_elapsed_ms)}/>
            <Metric label="滾動一分鐘請求"
              value={displayNumber(lab.budget.metrics.model_requests_rolling_minute)}
              note={hardNumberLimit(lab.budget.limits.max_model_requests_per_minute)}/>
            <Metric label="滾動一小時請求"
              value={displayNumber(lab.budget.metrics.model_requests_rolling_hour)}
              note={hardNumberLimit(lab.budget.limits.max_model_requests_per_hour)}/>
          </div>
          {(lab.budget.reset_at || labRetryText) && <div className="row g8 wrap muted mono"
            style={{ marginTop: 11, fontSize: 10.5 }}>
            {lab.budget.reset_at && <span>{t("UTC 重置")} · {utcTimestamp(lab.budget.reset_at)}</span>}
            {labRetryText && <span>{labRetryText}</span>}
          </div>}
        </div>
        <div className="panel" style={{ marginTop: 12, padding: 14 }}>
          <div className="row spread g10 wrap">
            <div style={{ flex: 1, minWidth: 260 }}>
              <LB>{t("目前場景")}</LB>
              <div className="mono" style={{ marginTop: 7, fontSize: 12, overflowWrap: "anywhere" }}>
                {lab.state.current_case_id || t("尚未領取場景")}
              </div>
              {(lab.state.current_domain || lab.state.current_actor) && <div className="muted" style={{ marginTop: 5, fontSize: 11 }}>
                {[lab.state.current_domain, lab.state.current_actor].filter(Boolean).join(" · ")}
              </div>}
              <div className="row g6 wrap" style={{ marginTop: 10 }}>
                <T tone={lab.state.control_state === "running" ? "ok" : "warn"} dot>
                  {t("控制狀態")} · {lab.state.control_state.toUpperCase()}
                </T>
                <T tone={lab.state.process_active ? "ok" : "warn"}>
                  {t("進程狀態")} · {lab.state.process_state.toUpperCase()}
                </T>
                <T tone="plain">{t("任務階段")} · {lab.state.runner_phase.toUpperCase()}</T>
                <T tone="plain">{t("循環序號")} · {displayNumber(lab.state.cycle_seq)}</T>
                <T tone={lab.state.consecutive_failures ? "bad" : "ok"}>
                  {t("連續失敗")} · {displayNumber(lab.state.consecutive_failures)}
                </T>
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <LB dim>{t("最近心跳")}</LB>
              <div className="mono" style={{ marginTop: 7, fontSize: 11 }}>{timestamp(lab.state.heartbeat_at)}</div>
              <div className="muted" style={{ marginTop: 5, fontSize: 10 }}>
                {t("最近活動")} · {timestamp(lab.state.last_activity_at)}
              </div>
            </div>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 8, marginTop: 13, paddingTop: 12, borderTop: "1px solid var(--hair)" }}>
            <div className="mono muted" style={{ fontSize: 10.5 }}>{t("最近領取嘗試")} · {timestamp(lab.state.last_claim_attempt_at)}</div>
            <div className="mono muted" style={{ fontSize: 10.5 }}>{t("最近成功領取")} · {timestamp(lab.state.last_claim_succeeded_at)}</div>
            <div className="mono muted" style={{ fontSize: 10.5 }}>{t("最近場景完成")} · {timestamp(lab.state.last_case_finished_at)}</div>
            {lab.state.last_error_code && <div className="mono" style={{ fontSize: 10.5, color: "var(--red)" }}>
              {t("最近穩定錯誤")} · {lab.state.last_error_code}
            </div>}
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <LB>{t("實驗錯誤指紋")}</LB>
          <div className="muted" style={{ marginTop: 5, fontSize: 11.2 }}>{t("只顯示穩定錯誤碼與聚合次數，不顯示需求正文、憑證或原始模型回應。")}</div>
          {!lab.findings.length
            ? <div className="muted" style={{ marginTop: 12, fontSize: 12 }}>{t("目前沒有實驗錯誤")}</div>
            : <div style={{ marginTop: 10, borderTop: "1px solid var(--rule)" }}>
              {lab.findings.slice(0, 8).map(item => <div className="ledger-row" key={item.key}>
                <T tone={severityTone(item.severity)}>{item.severity.toUpperCase()}</T>
                <code style={{ flex: 1, minWidth: 160, overflowWrap: "anywhere" }}>{item.code}</code>
                <span className="mono">× {displayNumber(item.count)}</span>
                <span className="muted" style={{ fontSize: 10 }}>{timestamp(item.last_seen_at)}</span>
              </div>)}
            </div>}
        </div>
      </Band>}

      {snapshot && <>
        <div className="panel row g12 wrap" style={{ marginTop: 14, padding: 14, borderColor: "var(--ok)" }}>
          <I name="shield" size={18} color="var(--ok)"/>
          <div style={{ flex: 1, minWidth: 240 }}>
            <LB>{t("聚合資料邊界")}</LB>
            <div className="muted" style={{ marginTop: 5, fontSize: 11.5, lineHeight: 1.6 }}>
              {t("此頁不接收或顯示原始對話、工具參數或原始模型回應；只接收經結構、敏感資料遮罩與群組門檻驗證的聚合拓撲、統計與優化方案。")}
            </div>
          </div>
          <T tone="ok" dot>AGGREGATE ONLY</T>
          <T tone="plain">NO RAW TRANSCRIPTS</T>
        </div>

        <div className="kpi-band">
          <Kpi label={t("可分析公司")} value={displayNumber(summary.available_tenant_count)}
            unit={"/ " + displayNumber(summary.tenant_count)} foot={<T tone="plain">{coverage} {t("公司覆蓋")}</T>}/>
          <Kpi label={t("秘書對話")} value={displayNumber(summary.conversation_count)}
            foot={<span className="muted">{t("聚合計數")}</span>}/>
          <Kpi label={t("AI 運行")} value={displayNumber(summary.run_count)}
            foot={<T tone="ok" dot>{t("完成率 {n}", { n: percent(metrics.completion_rate) })}</T>}/>
          <Kpi label={t("總 Token")} value={displayNumber(summary.total_tokens)}
            foot={<span className="muted">{t("視窗用量")}</span>}/>
        </div>

        <Band no="A" title={t("效果訊號")}
          sub={t("只使用聚合結果與正式運行狀態，不以模型自評取代真實結果。")}
          right={<span className="mono muted" style={{ fontSize: 10 }}>
            {t("資料生成於 {time}", { time: timestamp(summary.generated_at) })}
          </span>}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(170px,1fr))", gap: 10 }}>
            <Metric label="運行完成率" value={percent(metrics.completion_rate)}
              note={displayNumber(summary.completed_run_count) + " / " + displayNumber(summary.run_count)}/>
            <Metric label="運行失敗率" value={percent(metrics.failure_rate)}
              note={displayNumber(summary.failed_run_count) + " failed"}/>
            <Metric label="確認完成率" value={percent(metrics.confirmation_completion_rate)}
              note={displayNumber(summary.confirmation_count) + " events"}/>
            <Metric label="回饋率" value={percent(metrics.feedback_rate)}
              note={displayNumber(summary.feedback_count) + " events"}/>
            <Metric label="平均耗時" value={duration(summary.avg_duration_ms)}/>
            <Metric label="聚合訊息" value={displayNumber(summary.message_count)}/>
          </div>
        </Band>

        <Band no="B" title={t("問題發現")}
          sub={t("由跨公司訊號歸納的可驗證問題；不展示任何單一對話。")}>
          {!findings.length
            ? <EM icon="check" title={t("目前沒有問題發現")}
                sub={t("完成一次分析後，問題模式會以版本化證據持續累積。")}/>
            : <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: 12 }}>
                {findings.map(item => <article className="panel" key={item.key}
                  style={{ padding: 16, borderTop: item.severity === "critical" || item.severity === "high" ? "3px solid var(--red)" : "1px solid var(--rule)" }}>
                  <div className="row spread g8 wrap">
                    <T tone={severityTone(item.severity)}>{item.severity.toUpperCase()}</T>
                    {item.category && <span className="label dim">{item.category}</span>}
                  </div>
                  <h3 style={{ marginTop: 13, fontSize: 17, lineHeight: 1.35 }}>{item.title || item.key}</h3>
                  {item.description && <p className="muted" style={{ marginTop: 9, fontSize: 11.8, lineHeight: 1.65 }}>{item.description}</p>}
                  <div className="row g6 wrap" style={{ marginTop: 12 }}>
                    <T tone="plain">{t("證據 {n}", { n: displayNumber(item.evidence_count) })}</T>
                    <T tone="plain">{t("涉及 {n} 家公司", { n: displayNumber(item.tenant_count) })}</T>
                  </div>
                  {item.recommendation && <div style={{ marginTop: 13, paddingTop: 11, borderTop: "1px solid var(--hair)", fontSize: 11.8, lineHeight: 1.65 }}>
                    <LB red>{t("建議")}</LB><div style={{ marginTop: 6 }}>{item.recommendation}</div>
                  </div>}
                </article>)}
              </div>}
        </Band>

        <Band no="C" title={t("候選方案")}
          sub={t("每個方案都有狀態、風險與 revision；此頁不直接修改生產秘書。")}>
          {!candidates.length
            ? <EM icon="sparkle" title={t("目前沒有候選方案")}
                sub={t("分析器提出的方案會保存在這裡，等待離線評估與治理。")}/>
            : <div style={{ borderTop: "2px solid var(--rule)" }}>
                {candidates.map((item, index) => <article className="ledger-row" key={item.id} style={{ alignItems: "flex-start" }}>
                  <span className="lr-idx">{String(index + 1).padStart(2, "0")}</span>
                  <div style={{ flex: 1, minWidth: 240 }}>
                    <div className="row g7 wrap">
                      <strong style={{ fontSize: 13.5 }}>{item.title || item.id}</strong>
                      <T tone={statusTone(item.status)} dot>{item.status.toUpperCase()}</T>
                      <T tone={riskTone(item.risk_level)}>{t("風險")} · {item.risk_level.toUpperCase()}</T>
                    </div>
                    {item.hypothesis && <div className="muted" style={{ marginTop: 7, fontSize: 11.5, lineHeight: 1.6 }}>
                      <b>{t("假設")}:</b> {item.hypothesis}
                    </div>}
                    {item.expected_impact && <div style={{ marginTop: 5, fontSize: 11.5, lineHeight: 1.6 }}>
                      <b>{t("預期影響")}:</b> {item.expected_impact}
                    </div>}
                  </div>
                  <div className="mono muted" style={{ fontSize: 9.5, textAlign: "right", lineHeight: 1.7 }}>
                    <div>{t("版本")} · R{item.revision == null ? "—" : item.revision}</div>
                    <div>{t("建立於")} · {timestamp(item.created_at)}</div>
                  </div>
                </article>)}
              </div>}
        </Band>

        <Band no="D" title={t("公司快照帳本")}
          sub={t("每家公司只保存本視窗的聚合計數與可用狀態。")}>
          {!snapshots.length
            ? <EM icon="building" title={t("尚無公司快照")}/>
            : <div style={{ overflowX: "auto", borderTop: "2px solid var(--rule)" }}>
                <table className="tbl2" style={{ minWidth: 1060 }}>
                  <thead><tr>
                    <th>{t("公司")}</th><th>{t("狀態")}</th><th>{t("對話")}</th><th>{t("訊息")}</th>
                    <th>{t("運行")}</th><th>{t("完成")}</th><th>{t("失敗")}</th><th>{t("回饋")}</th>
                    <th>{t("確認")}</th><th>TOKEN</th><th>{t("平均耗時")}</th>
                  </tr></thead>
                  <tbody>{snapshots.map(item => <tr key={item.key}>
                    <td><strong>{item.tenant_name || item.tenant_slug || "—"}</strong>
                      {item.tenant_slug && <div className="mono muted" style={{ fontSize: 9.5 }}>/{item.tenant_slug}</div>}
                    </td>
                    <td>{item.available ? <T tone="ok" dot>{t("可用")}</T> : <T tone="bad">{t("不可用")}</T>}</td>
                    <td className="num">{displayNumber(item.conversation_count)}</td>
                    <td className="num">{displayNumber(item.message_count)}</td>
                    <td className="num">{displayNumber(item.run_count)}</td>
                    <td className="num">{displayNumber(item.completed_run_count)}</td>
                    <td className="num">{displayNumber(item.failed_run_count)}</td>
                    <td className="num">{displayNumber(item.feedback_count)}</td>
                    <td className="num">{displayNumber(item.confirmation_count)}</td>
                    <td className="num">{displayNumber(item.total_tokens)}</td>
                    <td className="mono">{duration(item.avg_duration_ms)}</td>
                  </tr>)}</tbody>
                </table>
              </div>}
        </Band>

        <Band no="E" title={t("分析歷史")}
          sub={t("每次分析都保留聚合規模、發現與候選數量，供平台擁有者追蹤持續迭代。")}>
          {!analysisHistory.length
            ? <EM icon="clock" title={t("尚無分析歷史")}/>
            : <div style={{ overflowX: "auto", borderTop: "2px solid var(--rule)" }}>
                <table className="tbl2" style={{ minWidth: 940 }}>
                  <thead><tr>
                    <th>{t("分析編號")}</th><th>{t("視窗")}</th><th>{t("覆蓋公司")}</th>
                    <th>{t("發現")}</th><th>{t("候選")}</th><th>{t("目標版本")}</th>
                    <th>{t("分析引擎")}</th><th>{t("建立者")}</th><th>{t("建立於")}</th>
                  </tr></thead>
                  <tbody>{analysisHistory.map(item => <tr key={item.key}>
                    <td className="mono">{item.id || "—"}</td>
                    <td className="num">{item.window_days == null ? "—" : t("近 {n} 天", { n: item.window_days })}</td>
                    <td className="num">{displayNumber(item.available_tenant_count)} / {displayNumber(item.tenant_count)}</td>
                    <td className="num">{displayNumber(item.finding_count)}</td>
                    <td className="num">{displayNumber(item.candidate_count)}</td>
                    <td className="mono">{item.objective_version || "—"}</td>
                    <td>{item.analysis_engine || "—"}</td>
                    <td className="mono">{item.created_by_username ? "@" + item.created_by_username : "—"}</td>
                    <td className="mono">{timestamp(item.created_at)}</td>
                  </tr>)}</tbody>
                </table>
              </div>}
        </Band>
      </>}
    </>
  );
};

/* Keep the authority decision outside OptimizerMain so no hook or API effect is
   mounted until /api/auth/me has supplied the authoritative owner flag. */
const Page = ({ isOwner = false }) => isOwner ? <OptimizerMain/> : <Denied/>;
window.W2.PAGES.optimizer = Page;
})();
