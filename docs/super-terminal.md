# Super Terminal and Auto Runtime

The Super Terminal is a high-density professional interaction surface, not an
unauthenticated database administration console. The Company AI behind it may
subjectively use its governed database Runtime. The Company Secretary,
embedded page assistants, mobile clients, and
the Super Terminal all enter the same Auto Runtime.

```text
interaction surface
        -> POST /api/agent/run/stream
        -> Auto Runtime
           observe -> understand goal -> plan -> act -> reflect
        -> capability adapters / execution world
        -> surface-specific presentation
```

## Codex terminal and database world

The V2 Super Terminal preserves Warehouse's dark, high-density terminal
language: monospace output, an activity stream, workset history, quick
workflows, a status rail, and a live indicator. Those are presentation
choices; physical database access remains an authenticated Company-AI ability
rather than an anonymous browser SQL endpoint.

`GET /api/runtime/world` supplies the terminal's live status rail.  It reads
the authenticated tenant's PostgreSQL data through the ordinary RLS session
and returns only a small permission-filtered world snapshot: inventory risk,
open work, active or delayed shipments, and audit counts.  The same snapshot
is embedded in the Runtime's `observe` event, so the terminal, secretary, and
model reason from the same visible facts.

`GET /api/runtime/skills` retains the imported Warehouse ability universe as a
human-visible Skills catalogue. Its 565 entries are searchable by category,
name, and description: 543 tenant entries and 22 separately L11-governed
platform entries. Six Warehouse 2.0 site-file contracts remain visible only as
retired history; they are unavailable to human execution and excluded from AI
tool schemas, leaving 559 AI-visible genes. Human discovery and
execution display the current account's authorization and lifecycle state,
while Company Runtime receives the complete active current-company
responsibility map.

## Surface contract

`POST /api/agent/run/stream` accepts a goal, optional conversation identifier,
and a `surface` label.  The label is observational context only: it cannot
choose a provider, command set, planner, or execution path.

The NDJSON stream emits:

| Event | Meaning |
| --- | --- |
| `run_start` | The shared Runtime accepted the goal. |
| `runtime_state` / `observe` | Current world and interaction context were assembled. |
| `runtime_state` / `plan` | Runtime published its provisional capability-oriented plan. |
| `runtime_state` / `reflect` | Runtime assessed evidence and completion before responding. |
| `final` | A surface-neutral response for rendering. |

The Runtime expands only the capability genes selected during context
distillation.  An execution uses the same boundary as the human terminal:
registered argument validation, the original method/path contract, tenant
identity, PostgreSQL RLS, confirmation metadata, and durable audit. Existing
native FastAPI domain routes execute first. A catalogue contract without a
native route can also execute through the verified adapter registry. A registry
entry becomes ready only when its tool name, retained method/path contract,
read/write effect, semantic resource and concrete handler all match. This lets
older command names delegate to current domain services without creating 272
temporary HTTP aliases. A contract without either execution proof remains
visible as an `awaiting_domain_adapter` capability gap; it cannot write a
command-shaped compatibility document or claim a business effect.

The first registry batch promotes five retained read abilities: canonical
inventory balances, stock ledger, item categories, physical database schema,
and read-only database query. Their evidence is the tenant RLS session plus,
for SQL, PostgreSQL privileges and a database-enforced read-only transaction.

The second read batch promotes 49 more retained abilities. Native PostgreSQL
tables now answer organization principals, workflow definitions, Company AI
runs, memory, knowledge, risk review and user-profile reads. Explicit
server-owned compatibility namespaces answer records, cases, finance,
collaboration, compliance, asset and import read models. These projection
adapters run in read-only RLS transactions, never create a document, and fail
closed when a requested detail is absent. Workflow preview validates the
current version and running-instance impact and returns a content digest
without publishing. This brought the intermediate tenant catalogue to 266
active, 218 awaiting-domain-adapter and 6 retired entries.

The third batch closes the retained catalogue. It adds 31 specialized reads
and 187 writes through the canonical `business.entities` plus immutable
`business.events` runtime. Every mutation is tenant-RLS scoped, versioned,
idempotent, audited, and read back in the same PostgreSQL transaction. The
registry freezes a SHA-256 of each imported method/path/effect/confirmation
contract, so catalogue drift fails closed. Domain-workflow and Passkey
abilities keep their existing confirmation gates. External reads use named
providers and fail closed when a tenant connection or location is absent. The
weather adapter first uses an explicit tenant configuration and then a
geocoded active warehouse; it never invents a location. Company-AI run detail
uses the UUID returned by `runs list`, while undo refuses a run that has no
recorded reversible steps. A registry invariant also rejects any generic write
that has neither a creation/collection path nor a deterministic target. Thus a
command cannot become Active while its first legal invocation is structurally
guaranteed to return “not found.” External effects require a provider receipt
before completion may be claimed.
The isolated Python runner also stays provider-dependent rather than executing
untrusted code in the API process.

AI Runtime architecture changes use a two-layer verification gate. The normal
backend suite keeps deterministic contract, authorization, transaction and
readback coverage. `ops/run-ai-runtime-verification` then securely loads the
DeepSeek credential from `~/Desktop/KEYS/Deepseek KEY.rtf`, provisions the
disposable PostgreSQL integration database used by `ops/run-full-verification`,
runs the complete suite, and requires live `deepseek-v4-flash` checks. The
credential is held only in the pytest child-process environment and is never
printed, copied into the repository or included in test artifacts.

Every AI Runtime upgrade batch must also pass at least one real secretary E2E
business scenario. A selector-only or mocked-model test is diagnostic coverage,
not acceptance evidence. The E2E gate must enter through
`POST /api/agent/run/stream` with `surface=secretary`, load the encrypted
tenant-scoped DeepSeek connection, let the shared Runtime select and execute the
real Adapter, read the resulting business state back from both the public API
and tenant PostgreSQL, and verify the durable user/assistant transcript, Runtime
snapshot, custody or domain evidence, and command audit. The first mandatory
scenario creates a uniquely named digital-asset master record and proves all of
those evidence sources agree. Live routing gates additionally verify the
provider JSON contract and that registration approval is not substituted with
the semantically different company-join approval gene.
One batched organization gate also requires the model to distinguish department
creation and update, position archival, and member permission overrides from
lookalike navigation, template, archival, and appointment genes.
The research domain has a complete 50-of-50 semantic matrix covering credentials,
projects, immutable files, manuscript drafts, evidence, reviews, isolated
executions, and releases. Its live gate distinguishes starting a refinement
draft, queuing semantic review, accepting a finding, and publishing an immutable
DOCX version from adjacent read, annotation, rejection, and draft-save genes.
The native digital-asset domain likewise has a complete 52-of-52 matrix across
assets, custody, workspaces, hosting sessions, Pages, storage, databases,
browser access, credentials, and the RLS Data API. Its live gate requires the
model to keep one-step provisioning, browser-policy configuration, primary-key
rotation, and read-only collection queries distinct from their component,
observation, subordinate-key, and write lookalikes.

The final tenant status is 537 active, 0 awaiting-domain-adapter and 6 retired.
The verified registry contains 281 adapters: 90 reads and 191 writes. Concrete
FastAPI routes cover 277 genes; 21 genes deliberately have both a native route
and a verified registry adapter. The remaining 256 genes are native-route-only,
not capability gaps. The machine-readable coverage matrix is exposed by
`GET /api/cli/migration-status` and `GET /api/ai/tools`; it reports cold,
unconfigured route scans as unresolved rather than as proven business gaps.
The 22 platform commands remain separately withheld behind L11 governance and
are not counted as tenant commands. “Active” means a truthful execution adapter is
mounted; a call can still be denied, require confirmation, fail a business
invariant, report a missing record, or reject an unconfigured provider.

Auto Runtime may inspect the physical catalog, columns, keys, constraints and
row values, author read-only SQL or database writes under the current
Company-AI identity, use registered semantic resources, or choose another
ability. The server exposes affordances and evidence; it does not hard-code
which fallback the model must use.

## Hierarchical context funnel

Auto Runtime uses `hierarchical_funnel_v2` instead of inserting the entire
company, memory, and active command catalogue into every model call:

```text
company micro-summary + complete domain atlas
        -> model-selected command families
        -> exact tool schemas and parameter contracts
        -> tenant-local live results
        -> incremental reflection + authority evidence projection
```

Every active capability remains conceptually visible. Domains and command
families are generated from non-retired catalogue metadata, so adding or
retiring a command changes discovery without adding a hard-coded business
route. Exact schemas expand only after model judgment. The full company
authority topology is loaded only for an operational working set and is
distilled into responsibility, required permission, referenced position,
active-holder, department, and workflow-node evidence. Another company's data
is never included.

Ordinary conversation completes in the compact top-router call. History,
memory, hosting, live operational snapshots, and full authority are independent
model-requested expansions. Later autonomous rounds receive the previous
reflection plus only newly acquired evidence; they do not resend all earlier
tool results. Each run records per-phase input characters, estimated tokens,
duration, and model-call count in `context_metrics`.

The `final` stream status distinguishes a completed answer (`succeeded`) from
an evidence-bounded diagnosis (`incomplete`) and a genuine human decision
boundary (`requires_user_input`).

## Shared execution boundary

The repository retains `/api/cli/*` for the human terminal and
`/api/ai/tools*` for governed external model clients.  Auto Runtime invokes the
same executor internally after its model decision:

- Tenant, DSN, backend and connection identity are Runtime-owned. Company AI
  may supply physical schema/table names, columns, SQL and parameters after it
  decides database access is useful.
- Direct human calls retain current-account authorization.  Company Runtime can
  reason across every role and capability in its own company.
- Confirmation policy is command metadata, not a hard-coded tool whitelist.
- Every terminal, external-tool, and Runtime execution is audited.
- `!command` remains ordinary goal text in `/api/agent/run/stream`; it is not
  an execution escape hatch.

The historical `terminal.command_executions` schema and Alembic revision are
also retained to preserve deployed migration history and audit data.  Removing
that data requires a separately authorized forward migration and backup plan.
Revision `20260728_0021` synchronizes its database constraints with the shared
executor: `terminal`, `super_terminal`, `ai_tool`, and `auto_runtime` are valid
origins, while completed, denied, confirmation, adapter-rejection, contract,
and failure outcomes remain representable without turning a successful
business read into a database constraint error.

## External Runtime API

Revision `20260728_0023` ports the Warehouse 2.0 tenant-bound `wsk_...` design
to PostgreSQL. The external API calls the same `/api/agent/run/stream` and
`/api/cli/exec` routes used by the retained clients. See
[`runtime-api.md`](runtime-api.md) for the key lifecycle, scopes, NDJSON
contract, live-authority reload, and tenant-isolation boundary.
