import crypto from "node:crypto";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";

import pg from "pg";
import { chromium } from "playwright";

const { Pool } = pg;
const POLL_MS = 1000;
const HEARTBEAT_MS = 5000;
const LOG_LIMIT = 4000;
const DOM_LIMIT = 40000;
const databaseUrl = String(process.env.WAREHOUSE_DATABASE_URL || "").replace(
  "postgresql+psycopg://",
  "postgresql://",
);
const workerToken = String(process.env.WAREHOUSE_BROWSER_WORKER_TOKEN || "");
const apiBase = String(process.env.WAREHOUSE_BROWSER_API_BASE || "http://api:8080").replace(/\/$/, "");
const artifactRoot = path.resolve(process.env.WAREHOUSE_BROWSER_RUNTIME_ROOT || "/data/browser-runtime");
const releaseId = String(process.env.WAREHOUSE_RELEASE_ID || "development");
const stepTimeoutMs = Math.max(1000, Number(process.env.WAREHOUSE_BROWSER_STEP_TIMEOUT_SECONDS || 15) * 1000);
const runTimeoutMs = Math.max(stepTimeoutMs, Number(process.env.WAREHOUSE_BROWSER_RUN_TIMEOUT_SECONDS || 120) * 1000);
const workerId = String(
  process.env.WAREHOUSE_BROWSER_WORKER_ID || `${os.hostname()}:${process.pid}`,
).slice(0, 160);
const allowedOrigins = new Set(
  String(process.env.WAREHOUSE_BROWSER_ALLOWED_ORIGINS || "http://localhost:8080")
    .split(",")
    .map((item) => item.trim().replace(/\/$/, ""))
    .filter(Boolean),
);
const resourceOrigins = new Set(
  String(process.env.WAREHOUSE_BROWSER_RESOURCE_ORIGINS || "")
    .split(",")
    .map((item) => item.trim().replace(/\/$/, ""))
    .filter(Boolean),
);

if (!databaseUrl) throw new Error("WAREHOUSE_DATABASE_URL is required");
if (workerToken.length < 32) throw new Error("WAREHOUSE_BROWSER_WORKER_TOKEN is required");
if (!allowedOrigins.size) throw new Error("WAREHOUSE_BROWSER_ALLOWED_ORIGINS is required");

const pool = new Pool({ connectionString: databaseUrl, max: 4 });
let stopping = false;
let currentRunId = null;

for (const signal of ["SIGTERM", "SIGINT"]) {
  process.on(signal, () => {
    stopping = true;
  });
}

const cleanText = (value, limit = LOG_LIMIT) => String(value ?? "").replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/g, "").slice(0, limit);
const json = (value) => JSON.stringify(value ?? {});
const sleep = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

async function heartbeat(state = currentRunId ? "busy" : "ready", metadata = {}) {
  await pool.query(
    `INSERT INTO browser_runtime.workers(
       worker_id, release_id, state, current_run_id, metadata, last_seen_at
     ) VALUES ($1, $2, $3, $4, $5::jsonb, now())
     ON CONFLICT (worker_id) DO UPDATE SET
       release_id = EXCLUDED.release_id,
       state = EXCLUDED.state,
       current_run_id = EXCLUDED.current_run_id,
       metadata = EXCLUDED.metadata,
       last_seen_at = now()`,
    [workerId, releaseId, state, currentRunId, json({ engine: "playwright", browser: "chromium", protocol: "warehouse-browser-steps/v1", ...metadata })],
  );
  if (currentRunId) {
    await pool.query(
      "UPDATE browser_runtime.runs SET heartbeat_at = now() WHERE id = $1 AND claimed_by = $2",
      [currentRunId, workerId],
    );
  }
}

async function withTenant(tenantId, callback) {
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    await client.query("SELECT set_config('app.tenant_id', $1, true)", [tenantId]);
    const result = await callback(client);
    await client.query("COMMIT");
    return result;
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

async function claim() {
  const result = await pool.query("SELECT * FROM app.claim_next_browser_run($1)", [workerId]);
  return result.rows[0] || null;
}

async function loadRun(tenantId, runId) {
  return withTenant(tenantId, async (client) => {
    const run = await client.query("SELECT * FROM browser_runtime.runs WHERE id = $1 FOR UPDATE", [runId]);
    if (!run.rows[0]) return null;
    if (run.rows[0].cancel_requested_at || run.rows[0].status === "cancelled") {
      await client.query(
        "UPDATE browser_runtime.runs SET status = 'cancelled', finished_at = COALESCE(finished_at, now()) WHERE id = $1",
        [runId],
      );
      return null;
    }
    const steps = await client.query(
      "SELECT * FROM browser_runtime.steps WHERE run_id = $1 ORDER BY ordinal",
      [runId],
    );
    await client.query(
      "UPDATE browser_runtime.runs SET status = 'running', started_at = COALESCE(started_at, now()), heartbeat_at = now() WHERE id = $1",
      [runId],
    );
    await client.query(
      "INSERT INTO browser_runtime.events(tenant_id, run_id, event_type, message, payload) VALUES ($1, $2, 'run.started', 'Chromium session started', $3::jsonb)",
      [tenantId, runId, json({ worker_id: workerId, release_id: releaseId })],
    );
    return { run: run.rows[0], steps: steps.rows };
  });
}

async function cancelled(tenantId, runId) {
  return withTenant(tenantId, async (client) => {
    const result = await client.query(
      "SELECT cancel_requested_at IS NOT NULL AS cancelled FROM browser_runtime.runs WHERE id = $1",
      [runId],
    );
    return Boolean(result.rows[0]?.cancelled);
  });
}

async function actorSession(runId, tenantId) {
  const response = await fetch(`${apiBase}/api/browser-runtime/internal/runs/${runId}/session`, {
    method: "POST",
    headers: {
      "X-Warehouse-Browser-Worker": workerToken,
      "X-Warehouse-Browser-Worker-ID": workerId,
      "X-Warehouse-Tenant-ID": tenantId,
    },
    signal: AbortSignal.timeout(10000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.token || !payload.tenant) {
    throw new Error(`actor session exchange failed (${response.status})`);
  }
  return payload;
}

function safeArtifactPath(tenantId, runId, filename) {
  const relative = path.posix.join(String(tenantId), String(runId), filename);
  const absolute = path.resolve(artifactRoot, relative);
  if (absolute !== artifactRoot && !absolute.startsWith(`${artifactRoot}${path.sep}`)) {
    throw new Error("unsafe artifact path");
  }
  return { relative, absolute };
}

async function artifact(client, tenantId, runId, stepId, kind, filename, contentType, bytes) {
  const { relative, absolute } = safeArtifactPath(tenantId, runId, filename);
  await fs.mkdir(path.dirname(absolute), { recursive: true, mode: 0o700 });
  await fs.writeFile(absolute, bytes, { mode: 0o600 });
  const digest = crypto.createHash("sha256").update(bytes).digest("hex");
  const id = crypto.randomUUID();
  await client.query(
    `INSERT INTO browser_runtime.artifacts(
       id, tenant_id, run_id, step_id, kind, relative_path,
       content_type, content_sha256, size_bytes
     ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)`,
    [id, tenantId, runId, stepId, kind, relative, contentType, digest, bytes.length],
  );
  return { id, kind, relative_path: relative, content_type: contentType, content_sha256: digest, size_bytes: bytes.length };
}

function locatorFor(page, specification) {
  const exact = Boolean(specification.exact);
  let locator;
  if (specification.test_id) locator = page.getByTestId(specification.test_id);
  else if (specification.label) locator = page.getByLabel(specification.label, { exact });
  else if (specification.role) locator = page.getByRole(specification.role, specification.name ? { name: specification.name, exact } : {});
  else if (specification.text) locator = page.getByText(specification.text, { exact });
  else throw new Error("semantic locator is incomplete");
  return Number.isInteger(specification.nth) ? locator.nth(specification.nth) : locator.first();
}

async function domSnapshot(page) {
  try {
    return cleanText(await page.locator("body").ariaSnapshot({ timeout: stepTimeoutMs }), DOM_LIMIT);
  } catch {
    return cleanText(await page.locator("body").innerText({ timeout: stepTimeoutMs }), DOM_LIMIT);
  }
}

async function executeStep(page, request, telemetry) {
  const action = request.action;
  if (action === "navigate") {
    const origin = new URL(page.url()).origin;
    const destination = new URL(request.path, origin);
    if (!allowedOrigins.has(destination.origin)) throw new Error("navigation left the allowed origin");
    await page.goto(destination.href, { waitUntil: "domcontentloaded", timeout: stepTimeoutMs });
  } else if (action === "click") {
    await locatorFor(page, request.locator).click({ timeout: stepTimeoutMs });
  } else if (action === "fill") {
    await locatorFor(page, request.locator).fill(request.value, { timeout: stepTimeoutMs });
  } else if (action === "press") {
    await locatorFor(page, request.locator).press(request.key, { timeout: stepTimeoutMs });
  } else if (action === "wait") {
    await page.waitForTimeout(request.milliseconds);
  } else if (action === "screenshot") {
    // Captured by the common post-step evidence path.
  } else if (action === "observe") {
    const kind = request.kind;
    if (kind === "visible") await locatorFor(page, request.locator).waitFor({ state: "visible", timeout: stepTimeoutMs });
    else if (kind === "hidden") await locatorFor(page, request.locator).waitFor({ state: "hidden", timeout: stepTimeoutMs });
    else if (kind === "text_contains") {
      const value = await locatorFor(page, request.locator).innerText({ timeout: stepTimeoutMs });
      if (!value.includes(request.expected)) throw new Error(`expected visible text: ${request.expected}`);
    } else if (kind === "url_contains" && !page.url().includes(request.expected)) {
      throw new Error(`expected URL fragment: ${request.expected}`);
    } else if (kind === "title_contains" && !(await page.title()).includes(request.expected)) {
      throw new Error(`expected title fragment: ${request.expected}`);
    } else if (kind === "no_console_errors" && telemetry.consoleErrors.length) {
      throw new Error(`${telemetry.consoleErrors.length} console error(s) observed`);
    } else if (kind === "no_failed_requests" && telemetry.failedRequests.length) {
      throw new Error(`${telemetry.failedRequests.length} failed request(s) observed`);
    }
  }
}

async function finishRun(tenantId, runId, status, summary) {
  await withTenant(tenantId, async (client) => {
    await client.query(
      "UPDATE browser_runtime.runs SET status = $2, result_summary = $3::jsonb, finished_at = now(), heartbeat_at = now() WHERE id = $1",
      [runId, status, json(summary)],
    );
    await client.query(
      "INSERT INTO browser_runtime.events(tenant_id, run_id, event_type, message, payload) VALUES ($1, $2, $3, $4, $5::jsonb)",
      [tenantId, runId, `run.${status}`, `Browser run ${status}`, json(summary)],
    );
    if (status !== "succeeded") {
      await client.query(
        "UPDATE browser_runtime.steps SET status = 'skipped', finished_at = now() WHERE run_id = $1 AND status = 'pending'",
        [runId],
      );
    }
  });
}

async function runClaim(claimed) {
  const tenantId = claimed.tenant_id;
  const runId = claimed.run_id;
  currentRunId = runId;
  const loaded = await loadRun(tenantId, runId);
  if (!loaded) return;
  const { run, steps } = loaded;
  const started = Date.now();
  const telemetry = {
    consoleErrors: [],
    ignoredConsoleErrors: [],
    pageErrors: [],
    failedRequests: [],
    blockedMutations: [],
  };
  let browser;
  let context;
  let page;
  let failure = null;
  let completedSteps = 0;

  try {
    browser = await chromium.launch({ headless: true });
    context = await browser.newContext({
      viewport: run.viewport,
      locale: "zh-TW",
      colorScheme: "light",
      ignoreHTTPSErrors: false,
    });
    await context.tracing.start({ screenshots: true, snapshots: true, sources: false });
    if (run.auth_mode === "actor") {
      const session = await actorSession(runId, tenantId);
      await context.addInitScript(
        ({ token, tenant }) => {
          window.localStorage.setItem("warehouse_auth_token", token);
          window.localStorage.setItem("warehouse_current_tenant", tenant);
        },
        { token: session.token, tenant: session.tenant },
      );
    }
    await context.route("**/*", async (route) => {
      const request = route.request();
      let requestOrigin;
      try { requestOrigin = new URL(request.url()).origin; } catch { requestOrigin = "invalid"; }
      const localProtocol = ["about:", "blob:", "data:"].some((prefix) => request.url().startsWith(prefix));
      const firstParty = allowedOrigins.has(requestOrigin);
      const trustedResource = resourceOrigins.has(requestOrigin);
      if (!firstParty && !trustedResource && !localProtocol) {
        telemetry.failedRequests.push({ type: "blocked_origin", method: request.method(), url: cleanText(request.url(), 1000) });
        await route.abort("blockedbyclient");
        return;
      }
      if (trustedResource) {
        if (request.isNavigationRequest() || !["GET", "HEAD", "OPTIONS"].includes(request.method())) {
          telemetry.blockedMutations.push({ type: "blocked_resource_action", method: request.method(), url: cleanText(request.url(), 1000) });
          await route.abort("blockedbyclient");
          return;
        }
        const headers = await request.allHeaders();
        for (const header of ["authorization", "cookie", "x-warehouse-tenant-id"]) delete headers[header];
        await route.continue({ headers });
        return;
      }
      if (run.mutation_policy === "read_only" && !["GET", "HEAD", "OPTIONS"].includes(request.method())) {
        telemetry.blockedMutations.push({ method: request.method(), url: cleanText(request.url(), 1000) });
        await route.abort("blockedbyclient");
        return;
      }
      await route.continue();
    });
    page = await context.newPage();
    page.setDefaultTimeout(stepTimeoutMs);
    page.on("console", (message) => {
      if (message.type() !== "error") return;
      const entry = { text: cleanText(message.text()), location: message.location() };
      let locationPath = "";
      try { locationPath = new URL(entry.location.url).pathname; } catch {}
      const expectedSandboxNoise = locationPath === "/cdn-cgi/rum"
        && entry.text.includes("ERR_BLOCKED_BY_CLIENT")
        && telemetry.blockedMutations.some((item) => item.url.startsWith(entry.location.url));
      if (expectedSandboxNoise) telemetry.ignoredConsoleErrors.push(entry);
      else telemetry.consoleErrors.push(entry);
    });
    page.on("pageerror", (error) => telemetry.pageErrors.push({ message: cleanText(error.message), name: error.name }));
    page.on("requestfailed", (request) => {
      const failureText = request.failure()?.errorText || "request failed";
      const alreadyTracked = [...telemetry.failedRequests, ...telemetry.blockedMutations]
        .some((item) => item.url === request.url() && item.method === request.method());
      if (!alreadyTracked) telemetry.failedRequests.push({ type: "request_failed", method: request.method(), url: cleanText(request.url(), 1000), error: cleanText(failureText) });
    });
    page.on("response", (response) => {
      if (response.status() >= 400) telemetry.failedRequests.push({ type: "http", method: response.request().method(), url: cleanText(response.url(), 1000), status: response.status() });
    });

    const startUrl = new URL(run.start_path, run.target_origin);
    if (!allowedOrigins.has(startUrl.origin)) throw new Error("run target origin is not allowed by this worker");
    await page.goto(startUrl.href, { waitUntil: "domcontentloaded", timeout: stepTimeoutMs });

    for (const step of steps) {
      if (Date.now() - started > runTimeoutMs) throw Object.assign(new Error("browser run timed out"), { timedOut: true });
      if (await cancelled(tenantId, runId)) throw Object.assign(new Error("browser run cancelled"), { cancelled: true });
      let stepError = null;
      let snapshot = "";
      const request = step.request;
      await withTenant(tenantId, async (client) => {
        await client.query(
          "UPDATE browser_runtime.steps SET status = 'running', started_at = now() WHERE id = $1",
          [step.id],
        );
        await client.query(
          "UPDATE browser_runtime.runs SET current_step = $2, heartbeat_at = now() WHERE id = $1",
          [runId, step.ordinal],
        );
        await client.query(
          "INSERT INTO browser_runtime.events(tenant_id, run_id, step_id, event_type, message, payload) VALUES ($1, $2, $3, 'step.started', $4, $5::jsonb)",
          [tenantId, runId, step.id, `Step ${step.ordinal}: ${step.action}`, json({ ordinal: step.ordinal, action: step.action })],
        );
      });
      try {
        await executeStep(page, request, telemetry);
        snapshot = await domSnapshot(page);
      } catch (error) {
        stepError = error;
        try { snapshot = await domSnapshot(page); } catch { snapshot = ""; }
      }
      await withTenant(tenantId, async (client) => {
        const evidence = [];
        if (request.action === "screenshot" || stepError) {
          const bytes = await page.screenshot({ fullPage: request.full_page !== false });
          evidence.push(await artifact(client, tenantId, runId, step.id, "screenshot", `step-${String(step.ordinal).padStart(3, "0")}.png`, "image/png", bytes));
        }
        if (stepError) {
          evidence.push(await artifact(client, tenantId, runId, step.id, "dom", `step-${String(step.ordinal).padStart(3, "0")}.aria.txt`, "text/plain; charset=utf-8", Buffer.from(snapshot)));
        }
        const observation = {
          url: cleanText(page.url(), 2000),
          title: cleanText(await page.title()),
          dom_excerpt: snapshot.slice(0, 12000),
          console_error_count: telemetry.consoleErrors.length,
          failed_request_count: telemetry.failedRequests.length,
          blocked_mutation_count: telemetry.blockedMutations.length,
          evidence,
        };
        await client.query(
          "UPDATE browser_runtime.steps SET status = $2, observation = $3::jsonb, error = $4, finished_at = now() WHERE id = $1",
          [step.id, stepError ? "failed" : "succeeded", json(observation), stepError ? cleanText(stepError.message) : null],
        );
        await client.query(
          "INSERT INTO browser_runtime.events(tenant_id, run_id, step_id, event_type, message, payload) VALUES ($1, $2, $3, $4, $5, $6::jsonb)",
          [tenantId, runId, step.id, stepError ? "step.failed" : "step.succeeded", `Step ${step.ordinal} ${stepError ? "failed" : "succeeded"}`, json({ ordinal: step.ordinal, action: step.action, error: stepError ? cleanText(stepError.message) : null })],
        );
      });
      if (stepError) throw stepError;
      completedSteps += 1;
    }

    await withTenant(tenantId, async (client) => {
      const tracePath = safeArtifactPath(tenantId, runId, "trace.zip");
      await fs.mkdir(path.dirname(tracePath.absolute), { recursive: true, mode: 0o700 });
      await context.tracing.stop({ path: tracePath.absolute });
      const bytes = await fs.readFile(tracePath.absolute);
      const digest = crypto.createHash("sha256").update(bytes).digest("hex");
      await client.query(
        `INSERT INTO browser_runtime.artifacts(
           id, tenant_id, run_id, kind, relative_path, content_type, content_sha256, size_bytes
         ) VALUES ($1, $2, $3, 'trace', $4, 'application/zip', $5, $6)`,
        [crypto.randomUUID(), tenantId, runId, tracePath.relative, digest, bytes.length],
      );
    });
    await finishRun(tenantId, runId, "succeeded", {
      completed_steps: completedSteps,
      total_steps: steps.length,
      elapsed_ms: Date.now() - started,
      final_url: cleanText(page.url(), 2000),
      console_errors: telemetry.consoleErrors,
      ignored_console_errors: telemetry.ignoredConsoleErrors,
      page_errors: telemetry.pageErrors,
      failed_requests: telemetry.failedRequests,
      blocked_mutations: telemetry.blockedMutations,
    });
  } catch (error) {
    failure = error;
    const finalStatus = error.cancelled ? "cancelled" : error.timedOut ? "timed_out" : "failed";
    try {
      if (context) {
        const tracePath = safeArtifactPath(tenantId, runId, "trace.zip");
        await fs.mkdir(path.dirname(tracePath.absolute), { recursive: true, mode: 0o700 });
        await context.tracing.stop({ path: tracePath.absolute }).catch(() => {});
        const bytes = await fs.readFile(tracePath.absolute).catch(() => null);
        if (bytes) {
          await withTenant(tenantId, (client) => artifact(client, tenantId, runId, null, "trace", "trace-failed.zip", "application/zip", bytes));
        }
      }
    } catch {}
    await finishRun(tenantId, runId, finalStatus, {
      completed_steps: completedSteps,
      total_steps: steps.length,
      elapsed_ms: Date.now() - started,
      error: cleanText(error.message),
      failure_type: cleanText(error.name || "Error"),
      final_url: page ? cleanText(page.url(), 2000) : null,
      console_errors: telemetry.consoleErrors,
      ignored_console_errors: telemetry.ignoredConsoleErrors,
      page_errors: telemetry.pageErrors,
      failed_requests: telemetry.failedRequests,
      blocked_mutations: telemetry.blockedMutations,
    });
  } finally {
    await context?.close().catch(() => {});
    await browser?.close().catch(() => {});
    currentRunId = null;
    await heartbeat(failure ? "error" : "ready", failure ? { last_error: cleanText(failure.message) } : {});
  }
}

await fs.mkdir(artifactRoot, { recursive: true, mode: 0o700 });
await heartbeat("ready");
await fs.writeFile("/tmp/browser-worker-ready", `${workerId}\n`, { mode: 0o600 });
const heartbeatTimer = setInterval(() => {
  heartbeat().catch(() => {});
}, HEARTBEAT_MS);

while (!stopping) {
  try {
    const next = await claim();
    if (next) await runClaim(next);
    else await sleep(POLL_MS);
  } catch (error) {
    await heartbeat("error", { last_error: cleanText(error.message) }).catch(() => {});
    await sleep(Math.min(5000, POLL_MS * 2));
  }
}

clearInterval(heartbeatTimer);
await heartbeat("stopping").catch(() => {});
await pool.end();
