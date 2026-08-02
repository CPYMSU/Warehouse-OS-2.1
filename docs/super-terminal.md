# Super Terminal and Auto Runtime

The Super Terminal is a high-density professional interaction surface.  It is
not a command shell, SQL console, model client, planner, memory store, or tool
router.  The Company Secretary, embedded page assistants, mobile clients, and
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
workflows, a status rail, and a live indicator.  Those are presentation
choices, not an invitation to expose a command shell or SQL console.

`GET /api/runtime/world` supplies the terminal's live status rail.  It reads
the authenticated tenant's PostgreSQL data through the ordinary RLS session
and returns only a small permission-filtered world snapshot: inventory risk,
open work, active or delayed shipments, and audit counts.  The same snapshot
is embedded in the Runtime's `observe` event, so the terminal, secretary, and
model reason from the same visible facts.

`GET /api/runtime/skills` retains the imported Warehouse ability universe as a
human-visible Skills catalogue. Its 502 entries are searchable by category,
name, and description: 480 tenant entries and 22 separately L11-governed
platform entries. Six Warehouse 2.0 site-file contracts remain visible only as
retired history; they are unavailable to human execution and excluded from AI
tool schemas, search candidates and context expansion. Human discovery and
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
identity, PostgreSQL RLS, confirmation metadata, and durable audit.  Existing
native FastAPI domain routes execute first.  A catalogue contract without a
native route is handled by the PostgreSQL capability gateway, which provides a
real tenant-isolated transitional projection until that domain receives a
specialized schema.

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

- Route and database targets are server-owned; neither a human nor a model can
  supply a tenant, DSN, backend, or connection string.
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
