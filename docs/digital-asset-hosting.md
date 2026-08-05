# Digital asset hosting contract

The customer-facing Traditional Chinese source of truth is
[`digital-asset-custody-guide-2.1.zh-TW.md`](digital-asset-custody-guide-2.1.zh-TW.md).
The API serves that exact file through `/api/digital-assets/guide` and
`/api/digital-assets/guide/download`. This engineering note explains the
invariants behind that public contract.

Application authors should also use
[`workspace-hosting-developer-standard-2.3.zh-TW.md`](workspace-hosting-developer-standard-2.3.zh-TW.md)
and its machine contract
[`workspace-hosting-contract-2.3.json`](workspace-hosting-contract-2.3.json).

AI 秘書、終端 AI 與前端整合的雙模式、Runtime 指令集和接口連線設計，請以
[`warehouse-hosting-mechanisms-2.3.zh-TW.md`](warehouse-hosting-mechanisms-2.3.zh-TW.md)
為共同指南；智能託管 API 會透過 `/api/hosting/v2/auto-runtime-guide.md` 提供同一份
文件。

Warehouse OS 2.1 treats a custodied program as an asset with one or more
application workspaces. It does not import the Warehouse 2.0 customer-runtime,
database, key, or site-publication contracts.

## Domain boundaries

- `digital_asset.assets`, versions, artifacts and hash-chained custody events
  form the asset and custody ledger.
- A workspace owns components, storage and database bindings, credentials,
  quota and deployments.
- Every workspace receives the stable entry
  `/assets/{tenant_slug}/{workspace_key}/` when it is created.
- The stable entry is a status page until a deployment is both `ready` and
  `healthy` and supplies a verified application URL. Only then does the entry
  redirect to the deployed application.
- Every tenant-owned row carries `tenant_id` and is protected by forced
  PostgreSQL Row Level Security.
- Public numeric IDs remain available as `legacy_id`; internal relationships
  use UUIDs.
- AI and clients never supply tenant IDs, database DSNs, host paths, provider
  secrets or internal ports.

## Provider and readiness states

| Capability | Provider | Truthful state |
|---|---|---|
| Artifact storage | `content_addressed_local` | Working development adapter; immutable object key and server-computed SHA-256 |
| Hosted application database | `warehouse_postgresql_hdd_data_api` | Dedicated PostgreSQL database and role on the HDD data plane; stable Data API remains unchanged |
| Customer-owned application database | `external_postgresql` | Validated, encrypted external DSN; the default binding drives Runtime and relational Data API without exposing credentials |
| Legacy portable database | `warehouse_postgresql_data_api` | SSD control-plane compatibility source retained read-only after verified migration |
| Application runtime | `runtime_controller` | Durable queue, isolated build/runtime, health verification and route activation |

## User-selected dual hosting

Every workspace now keeps the existing cloud hosting path and may explicitly
select terminal hosting. Existing workspaces default to `hosting_mode=cloud`.

- `cloud`: the asset runs on the Warehouse OS server, Vultr or a Mac mini
  compute node. Storage, database and hosting remain compatible with the 2.1
  contract.
- `terminal`: the server records a terminal deployment and emits a durable
  action to the user's paired terminal or AI. It does not enqueue a server
  Runtime or create a `warehouse-runtime-*` container.

The account control API is:

- `GET|PUT /api/workspaces/{workspace}/hosting`
- `GET /api/workspaces/{workspace}/hosting/notifications`
- `POST /api/workspaces/{workspace}/hosting/notifications`
- `POST /api/workspaces/{workspace}/hosting/notifications/{notification}/ack`
- `GET|POST /api/workspaces/{workspace}/compute-usage`

The intelligent hosting API exposes the same choice through
`desired_state.hosting.mode` and provides notification polling at
`/api/hosting/v2/notifications`. A terminal or AI reports a completed terminal
deployment through
`POST /api/hosting/v2/terminal-actions/{deployment}/complete`. It uses only the
workspace key and never receives company control-plane credentials. Cloud
compute usage is recorded separately from storage hosting usage so Warehouse OS
can introduce CPU, memory, GPU or runtime-time billing later without changing
the hosting contract. The same workspace-key surface exposes the current ledger
through `GET /api/hosting/v2/compute-usage`; this is usage evidence, not yet an
invoice.

Before executing, a terminal can fetch the least-privilege action manifest from
`GET /api/hosting/v2/terminal-actions/{deployment}`. It contains the verified
source hash, source download route, runtime intent, data API route and completion
route, but no database DSN, host path or company credential.

The Warehouse Runtime Controller now samples cumulative Docker CPU, memory and
network counters at a bounded interval and writes interval deltas to
`compute_usage_events` with `metering_source=runtime`. The first sample after a
controller restart is only a baseline; it does not fabricate the missing
interval. GPU seconds remain zero until the provider supplies a GPU sampler, and
pricing is intentionally left as a later billing-policy layer.

The built-in sampler is scoped to containers actually owned by the Warehouse
Runtime Controller (`compute_node=warehouse` and the workspace's active
deployment). Vultr and Mac mini workers must report their own counters through
the same compute-usage API; the controller never infers a remote provider from
the workspace label and therefore cannot double-count another node.

Terminal completion does not mark the workspace's server `runtime_status` as
`ready` (or `failed`): that field remains `provisioned` because no Warehouse
Runtime health check or server container was involved. The terminal outcome is
available on the deployment record and in `workspace.config` as
`terminal_last_status`, `terminal_last_deployment_id` and
`terminal_last_completed_at`.

The downloaded `dm.py` client exposes the terminal loop directly:

```bash
dm.py hosting guide --output warehouse-hosting-mechanisms-2.3.zh-TW.md
dm.py hosting mode
dm.py hosting set terminal --notify-targets terminal,ai
dm.py hosting notifications --status pending
dm.py hosting usage
dm.py hosting action <deployment-uuid>
dm.py hosting prepare <deployment-uuid> --directory .warehouse-terminal
dm.py hosting ack <notification-uuid>
dm.py hosting complete <deployment-uuid> --status succeeded --result '{"url":"http://127.0.0.1:8080"}'
```

`hosting prepare` only downloads and verifies the immutable source archive,
safely materializes it under `source/`, and writes `terminal-manifest.json`; it
never runs an untrusted command. Execution must be an explicit, user-approved
sandbox step on the terminal.

Provider keys are control-plane contracts. A production object store or
container runtime can replace a development provider without changing the
public asset, workspace or data-plane API.

Every workspace database consumer resolves the same `database_binding`.
`is_default=true` selects the one binding injected into Runtime as
`DATABASE_URL`. Managed bindings are platform-owned; `external_postgresql`
bindings are customer-owned and store a complete DSN only as encrypted
credential material. External connections require a bounded non-superuser role,
TLS and a public address by default. Private addresses require a separately
governed network connector.

The workspace owner may instead select `workspace_managed` or `none` through
`PUT /api/workspaces/v1/database/policy`. In `workspace_managed` mode the
platform does not force a PostgreSQL binding or inject a platform DSN: the WAK
may run MySQL, MongoDB, SQLite, another datastore, or no database through the
restricted container/Compose fabric and workspace-owned named volumes. This is
workspace-root authority, not host-root authority; host paths, Docker socket,
privileged mode and other tenants remain unreachable.

## Permanent entry and storage quota

`create_workspace` reserves the permanent entry even when no source version or
deployment exists. The response exposes `entry_url` and `hosting_url` for that
stable entry; `application_url` remains separate and is not trusted until the
latest deployment is `ready` and `healthy`.

Every new workspace has exactly 512 MiB of formal storage quota. A different
initial quota is rejected. `POST /api/digital-assets/{asset}/workspace-quota`
accepts exactly one of:

- `delta_mb=512`; or
- `target_mb=current_mb+512`.

The adapter never reduces quota and increments the workspace revision. Clients
should pass `expected_revision` to make concurrent requests fail with HTTP 409
instead of overwriting one another. Each successful increase records before,
after, used bytes and the fixed 512 MiB increase in the audit log.

## Company control API

These routes use the authenticated company identity, never a workspace key.

### Guide and client downloads

- `GET /api/digital-assets/guide`
- `GET /api/digital-assets/guide/download`
- `GET /api/digital-assets/cli`
- `GET /api/digital-assets/hosting-standard`
- `GET /api/digital-assets/hosting-standard/download`
- `GET /api/digital-assets/hosting-contract.json`

### Assets and custody

- `POST /api/digital-assets` or `/api/digital-assets/create`
- `POST /api/digital-assets/provision`
- `POST /api/digital-assets/upload`
- `GET /api/digital-assets/{asset}`
- `POST /api/digital-assets/{asset}/update`
- `POST /api/digital-assets/{asset}/archive`
- `POST /api/digital-assets/{asset}/version`
- `POST /api/digital-assets/{asset}/artifacts`
- `POST /api/digital-assets/{asset}/artifacts/upload`
- `GET /api/digital-assets/{asset}/artifacts/{artifact}/download`
- `POST /api/digital-assets/{asset}/custody`

### Workspaces, data and runtime

- `POST /api/digital-assets/{asset}/workspace`
- `POST /api/digital-assets/{asset}/workspace-quota`
- `POST /api/digital-assets/{asset}/database`
- `POST /api/digital-assets/{asset}/deploy`
- `POST /api/workspaces/{workspace}/databases`
- `POST /api/workspaces/{workspace}/database/migrate-hdd`
- `GET /api/workspaces/{workspace}/database/schema`
- `GET /api/workspaces/{workspace}/database/health`
- `GET /api/workspaces/{workspace}/database/tables/{schema}/{table}/rows`
- `PUT /api/workspaces/{workspace}/database/tables/{schema}/{table}/rows/{key}`
- `GET /api/workspaces/{workspace}/data/{collection}`
- `PUT /api/workspaces/{workspace}/data/{collection}/{record_key}`
- `POST /api/workspaces/{workspace}/runtime`

### Workspace credentials

- `POST /api/workspaces/{workspace}/keys`
- `GET /api/workspaces/{workspace}/keys`
- `POST /api/workspaces/{workspace}/keys/primary/rotate`
- `POST /api/workspaces/{workspace}/keys/{credential}/revoke`

## Deployed-program Data API

`dam.py` is deliberately a data-plane client. It accepts only a `wak_`
workspace credential and never receives company control-plane authority.

Provisioning issues the workspace's unique primary key with every workspace
scope. Additional calls to `POST .../keys` issue independently scoped delegated
keys. Primary rotation atomically revokes the previous primary while delegated
keys remain valid. Send either kind as:

```http
Authorization: Bearer wak_<signed-token>
```

Stable endpoints:

- `GET /api/workspaces/v1/info`
- `GET /api/workspaces/v1/usage`
- `POST /api/workspaces/v1/storage/probe`
- `PUT /api/workspaces/v1/runtime`
- `POST /api/workspaces/v1/sources/upload`
- `POST /api/workspaces/v1/deployments`
- `POST /api/workspaces/v1/deployments/{deployment_id}/repair`
- `POST /api/workspaces/v1/jobs`
- `PUT /api/workspaces/v1/database/policy`
- `GET /api/workspaces/v1/database/control`
- `POST /api/workspaces/v1/database/reconcile`
- `GET /api/workspaces/v1/database/schema`
- `GET /api/workspaces/v1/database/health`
- `GET /api/workspaces/v1/database/tables/{schema}/{table}/rows`
- `PUT /api/workspaces/v1/database/tables/{schema}/{table}/rows/{key}`
- `GET /api/workspaces/v1/data/{collection}`
- `PUT /api/workspaces/v1/data/{collection}/{record_key}`
- `GET /api/workspaces/v1/fabric/manifest`
- `GET /api/workspaces/v1/fabric`
- `POST /api/workspaces/v1/fabric/resources`
- `GET /api/workspaces/v1/fabric/actions/{action_id}`

Keys carry signed tenant/workspace locators and scopes. The server verifies the
stored token hash inside that tenant's RLS transaction; it never scans other
companies' credential tables. Data writes support optimistic concurrency
through `expected_version`; stale writes return HTTP 409.

`usage` refreshes platform-owned measurements for source archives, every
retained Runtime release/build/virtual environment, persistent DATA, managed
data objects and PostgreSQL. It returns component bytes, `measured_at` and an
additive `total_bytes`; workloads never receive host filesystem paths.

The schema response contains both `collections` and real PostgreSQL `tables`.
Collection endpoints remain the portable JSON document contract. Relational
table endpoints operate only on readable tables and require exactly one primary
key for writes; their opaque PostgreSQL row version is returned for optimistic
concurrency. External providers expose relational tables but do not silently
install the platform's `workspace_records` collection table.

## Deployment self-repair

Users never need a host port, SSH, Docker access or a database owner password
to repair their own program. All calls use the platform HTTPS endpoint on port
443 and a workspace key containing `deploy:write`:

```http
POST /api/workspaces/v1/deployments/{deployment_id}/repair
Authorization: Bearer wak_<signed-token>
Content-Type: application/json

{"source":"user","reason":"health check reported a missing runtime"}
```

The call is asynchronous and idempotent. A `ready` deployment may be repaired
only when it is the workspace's active revision; a failed deployment may be
retried without replacing the previous healthy revision first. If the same
deployment is already `queued`, `building` or `deploying`, the API returns the
current deployment with `accepted=false` instead of creating duplicate work.
Observe progress with:

- `GET /api/workspaces/v1/deployments/{deployment_id}`
- `GET /api/workspaces/v1/deployments/{deployment_id}/events`
- `GET /api/workspaces/v1/deployments/{deployment_id}/logs` with `logs:read`

The Runtime Controller separately reconciles every active `ready` deployment.
If a platform-managed container has actually disappeared, it emits
`self_heal_queued` and rebuilds that exact deployment automatically. Temporary
Docker API failures and intentionally stopped containers are not treated as
missing, which prevents a control-plane outage from causing mass redeploys.

An AI Secretary uses the same repair endpoint with `source=ai_secretary`, a
delegated workspace key and a concise reason. It may read redacted events/logs,
classify a retryable failure, and request this bounded action. It never receives
the Docker socket, server SSH key, database DSN or superuser role. Every request
records the credential, source, reason, previous status and active-revision
fact in the deployment event stream. Higher-risk actions such as database
restore, destructive rollback, credential rotation or provider failover remain
separate confirmation-gated operations.

## Standalone database and browser gateway

`POST /api/database-projects` creates an asset, a workspace and its managed
database without requesting or deploying a Runtime. This is the product entry
for a frontend hosted elsewhere, including GitHub Pages. It reuses the same
`database_bindings`, quota and custody model as hosted applications.

The AI Secretary uses the same native control plane through `dm db service
list`, `dm db service create`, `dm db browser show`, `dm db browser configure`,
and `dm db onboarding`. The onboarding command returns the SDK, guide, API map,
public `dbp_` locator and key-delivery policy. It never copies PostgreSQL
credentials into chat; a server-side `wak_` remains a separately confirmed,
one-time secure delivery through the existing workspace-key command.

Browser code must never receive a `wak_` key. An administrator enables the
browser boundary with:

- `GET /api/database-projects`
- `GET|PUT /api/workspaces/{workspace}/database/browser-access`
- `GET /api/workspaces/{workspace}/database/onboarding`
- an exact HTTPS `allowed_origins` list;
- deny-by-default collection rules using `deny`, `session`, or `owner` for
  `read` and `write`;
- a per-project database-backed request limit.

The returned `dbp_` project key is a public signed locator, not a credential.
An allowed browser origin exchanges it at
`POST /api/database-gateway/v1/projects/{dbp}/sessions` for a revocable `wdb_`
access token and rotating `wdr_` refresh token. Access tokens last 5–60 minutes;
changing policy increments the project revision and invalidates existing access
tokens. Disabling browser access revokes every refresh session.

Browser collection CRUD is available at:

- `GET /api/database-gateway/v1/projects/{dbp}/data/{collection}`
- `GET|PUT|DELETE /api/database-gateway/v1/projects/{dbp}/data/{collection}/{key}`
- `GET /api/database-gateway/v1/sdk.js`

`owner` rules inject and atomically enforce the session subject in `owner_id`,
including list, overwrite and delete checks. CORS is evaluated per project and
exact origin. The browser gateway currently targets the managed collection Data
API; customer-owned PostgreSQL remains a server-side Runtime/backend binding.

Runtime configuration accepts `auto`, `static`, `web`, `api`, `worker`,
`agent` and `job`, plus `container` and `compose`. Detection reads the immutable source archive evidence and selects an
enabled database Runtime profile. It never creates a second workspace. Missing
legacy storage bindings are repaired on the same workspace, but `ready` is
persisted only after a create/write/fsync/read/delete probe succeeds.

`POST /api/workspaces/v1/deployments` performs that source-evidence detection
and updates the same workspace component before it queues a build. A caller may
still request an explicit Runtime contract, but an explicit contract that the
verified archive cannot satisfy is rejected before the deployment queue is
mutated. The response uses `source_runtime_mismatch` for an explicit invalid
request and `runtime_contract_mismatch` when a lower-level stale component is
detected; both include a safe corrective next action.

`activate=false` creates and health-checks a release without changing the
workspace's active deployment. A later explicit `/activate` performs the
traffic switch. `POST /api/workspaces/v1/jobs` uses the same immutable source,
read-only source mount and writable workspace data volume, waits for a bounded
exit code, stores redacted logs, and never changes production traffic. A
`database:admin` key may request a safe environment alias for the already
bound database URL, so source-native Alembic/import commands do not require an
operator to reveal or copy a DSN.

## Advanced Hosting Fabric

The fabric is the stable adapter boundary for OCI images and Dockerfiles,
restricted Compose graphs, custom domains and ACME TLS, environment variables,
write-only versioned secrets, replica/autoscaling policy, transactional DDL
migrations, GitHub/GitLab HTTPS synchronization, database backup/restore and
accelerator allocation. Each resource stores desired and observed state under
the key's tenant/workspace boundary. Each apply creates an immutable action
event stream and supports an idempotency key.

Compose route services and single-container runtimes share the same dynamic
1–8 replica reconciler and stable-request-hash failover. Repository resources
can opt into 60–86400 second automatic synchronization. Custom hostnames are
globally claimed before Nginx/ACME execution; the platform origin and all of its
subdomains are reserved.

Provider absence is a first-class `blocked` result. For example, a PITR request
cannot be reported as a logical backup, and a GPU request cannot be reported as
allocated until the Runtime Controller has observed capacity from Docker.
Current-server logical backups are operational; PITR and remote DR remain
blocked until their declared provider capabilities are connected.

Runtime containers always drop Linux capabilities, use no-new-privileges,
disallow host networking and host paths, and mount only immutable application
source plus the workspace's HDD data volume. Secrets are absent from desired
state, API reads and audit requests; they are decrypted only inside the Runtime
Controller immediately before container creation.

## Auto Runtime authorization handoff

The L1 company context contains `hosted_application_world`: current-company
assets, workspaces, permanent entries, components, quota, provider state and
deployment state. Credentials, token hashes, object paths and DSNs are
excluded.

When a user requests a protected mutation, Runtime persists an exact
confirmation action. Passkey verification authorizes that action and revision
and produces a single-use Action Keychain; it does not run business code. The
Runtime consumes that authorization signal, invokes the typed adapter, and
checks the resulting world observation.

A new `wak_` plaintext is removed from execution results and placed in a
15-minute encrypted delivery bound to the current browser tab. Confirmation
responses, conversation history, snapshots and audit rows contain only the key
hint and delivery descriptor. Acknowledgement destroys the ciphertext.

## External-reality rule

The following facts are intentionally distinct:

| Fact | What it proves |
|---|---|
| `permanent_entry_reserved` | Stable workspace URL exists |
| deployment `queued` | Request was persisted |
| workspace `building` | Runtime configuration/build is in progress |
| deployment `ready` + health `healthy` + verified URL | Application is actually online |

No model response, configuration update or user-supplied URL may upgrade an
unverified deployment into external reality.

## HDD/SSD storage policy

Every workspace has two database-backed storage bindings:

- `code`: defaults to the HDD pool. `ssd` is accepted only when the user or AI
  explicitly supplies that choice for core source/build artifacts.
- `data`: always binds to the HDD pool. Attachments, datasets, documents,
  models and runtime-persistent files cannot be routed to the SSD code pool.

Before any source version or `code` artifact exists, the code binding may be
changed in place with `POST /api/workspaces/{workspace}/storage` or
`dm workspace storage --workspace <key> --code-storage ssd|hdd`. The operation
keeps the workspace identity and entry URL, performs no physical copy, and
never changes DATA or database storage. Once source/code exists the same API
returns HTTP 409 `code_storage_migration_required`; Auto Runtime must then plan
a copy + hash verification + binding cutover rather than editing metadata.

The initial 512 MiB and every later 512 MiB increment are one logical limit
across SSD code, HDD objects, HDD runtime persistence and the hosted database's
user tables, indexes and TOAST. No filesystem space is preallocated. Database
writes are measured inside the same transaction and roll back with HTTP 507 if
the combined total would cross the workspace limit. `GET /api/storage/v1/pools`
and `dm storage pools` expose sanitized capacity, service health and
database-configured watermarks without revealing host paths or DSNs.

The platform control PostgreSQL remains on SSD for identity, permission,
audit, binding and quota metadata. User software records live in a second
PostgreSQL 18 cluster whose PGDATA is mounted at
`/mnt/warehouse-data/hosted/postgres-data`. Every workspace using the
`platform_managed` policy receives a dedicated database and non-privileged login role. Only the stable Data API can
resolve the encrypted internal credential; people, frontends and Auto Runtime
never receive a native DSN. This paragraph describes the optional
`platform_managed` provider, not a mandatory application architecture;
`workspace_managed`, `external` and `none` remain valid policy modes.
