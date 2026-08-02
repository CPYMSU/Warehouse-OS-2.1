# Digital asset hosting contract

The customer-facing Traditional Chinese source of truth is
[`digital-asset-custody-guide-2.1.zh-TW.md`](digital-asset-custody-guide-2.1.zh-TW.md).
The API serves that exact file through `/api/digital-assets/guide` and
`/api/digital-assets/guide/download`. This engineering note explains the
invariants behind that public contract.

Application authors should also use
[`workspace-hosting-developer-standard-2.2.zh-TW.md`](workspace-hosting-developer-standard-2.2.zh-TW.md)
and its machine contract
[`workspace-hosting-contract-2.2.json`](workspace-hosting-contract-2.2.json).

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
| Legacy portable database | `warehouse_postgresql_data_api` | SSD control-plane compatibility source retained read-only after verified migration |
| Application runtime | `runtime_controller` | Durable queue, isolated build/runtime, health verification and route activation |

Provider keys are control-plane contracts. A production object store or
container runtime can replace a development provider without changing the
public asset, workspace or data-plane API.

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
- `POST /api/workspaces/v1/storage/probe`
- `PUT /api/workspaces/v1/runtime`
- `POST /api/workspaces/v1/sources/upload`
- `POST /api/workspaces/v1/deployments`
- `GET /api/workspaces/v1/database/schema`
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

Runtime configuration accepts `auto`, `static`, `web`, `api`, `worker` and
`agent`, plus `container` and `compose`. Detection reads the immutable source archive evidence and selects an
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
`/mnt/warehouse-data/hosted/postgres-data`. Every workspace receives a
dedicated database and non-privileged login role. Only the stable Data API can
resolve the encrypted internal credential; people, frontends and Auto Runtime
never receive a native DSN.
