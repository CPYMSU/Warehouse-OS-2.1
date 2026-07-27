# Governed Super Terminal

The super terminal has one command contract for people and AI. It is not a
database shell and no caller receives a database DSN, tenant selector, schema
name, or arbitrary SQL capability.

## Current migration state

The imported legacy catalogue contains 441 commands:

- 419 tenant commands;
- 22 platform commands.

The contracts are preserved in
[`backend/app/terminal/legacy_catalog.py`](../backend/app/terminal/legacy_catalog.py).
They retain command grammar, JSON tool schemas, permission alternatives, risk,
confirmation policy, and audit-redaction metadata.

Importing a contract does not make it executable. The current PostgreSQL
foundation enables only the two read-only commands whose new domain adapters
exist:

- `whoami` (`auth_me`)
- `warehouse list` (`warehouse_list`)

Every other tenant command returns `awaiting_domain_adapter`, records an audit
event, and performs no business operation. All 22 platform commands are held
at `requires_l11_governance` until the L11 owner model, delegation, revocation,
and last-owner protection are implemented.

Use these authenticated endpoints:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/cli/commands` | Commands executable by the current actor now |
| `GET /api/cli/migration-status` | Full import/activation progress without false positives |
| `POST /api/cli/exec` | Human terminal command: `{ "line": "warehouse list" }` |
| `GET /api/ai/tools` | All 441 function schemas plus their activation states |
| `POST /api/ai/tools/{tool_name}/execute` | AI tool call: `{ "arguments": {} }` |
| `POST /api/agent/run/stream` | Provider-neutral NDJSON bridge; `!command` uses the same executor |

`/api/admin/sql` is deliberately absent. It would turn an API credential or
model prompt injection into database administration.

## AI knows the command vocabulary; company data remains isolated

AI discovery is global only for non-secret command metadata. `/api/ai/tools`
returns every tenant and platform command plus a state for each: active,
awaiting a domain adapter, or awaiting L11 governance. This lets an AI explain
what is possible or prepare a hand-off instead of pretending a capability does
not exist.

Company databases are absolutely isolated. Every AI run, tool call, audit
record, vector retrieval, and storage-port call is bound to exactly one
`tenant_id`; PostgreSQL RLS is enabled and forced for tenant tables. An AI for
Company A never receives Company B's users, roles, permission assignments,
business records, embeddings, files, or query results. The command vocabulary
is shared; data and authority context are not.

Tool schemas do not contain a permission grant. The future AI execution ledger
will store the AI's decision (`execute`, `request_confirmation`, `delegate`, or
`deny`), the requesting person, target tenant and target user, evidence used,
and the outcome. The server remains responsible for non-delegable invariants:
tenant isolation, active identity, L11 last-owner protection, write
confirmation, idempotency and audit. This prevents a browser from forging an
"AI approved" request while still allowing AI to make the operational
judgment.

There is no cross-company authority graph for AI. Any future L11 governance is
platform identity metadata, not a bypass of tenant data isolation. Until more
domain adapters are active, direct execution stays bound to the authenticated
tenant actor and only the two active read adapters can run.

## Execution model

```text
Human terminal / AI tool call
        -> versioned command catalogue
        -> actor, tenant, permission, risk and confirmation checks
        -> typed domain adapter
        -> storage port (for example WarehouseReader)
        -> PostgreSQL implementation + RLS
        -> terminal.command_executions + audit.events
```

The catalogue is version-controlled code so a deployment cannot silently alter
a command's route or security policy. Execution records are tenant-scoped in
PostgreSQL and `terminal.command_executions` has forced RLS.

## Firebase-like developer experience, without a generic database backdoor

Clients should use stable application APIs such as
`GET /api/warehouses/geo`, not PostgreSQL table access. Command adapters use
small storage ports such as `WarehouseReader` and `CommandAuditWriter` in
[`backend/app/terminal/store.py`](../backend/app/terminal/store.py). PostgreSQL
is one implementation of those ports.

To change database technology later, implement the same ports and preserve the
HTTP/AI command contracts. This is the useful part of the Firebase experience:
the UI and AI keep one API while storage changes behind it. A generic
`/api/database` or unrestricted SQL endpoint is intentionally not compatible
with tenant isolation, validation, audit, financial controls, or safe AI use.

## Activation checklist for each remaining command

1. Migrate its domain tables and typed validation into the new model.
2. Add a domain adapter using a storage port; never issue an internal HTTP call
   or let the command choose its data source.
3. Apply tenant RLS and add role/position permission coverage.
4. For every write, implement a persistent confirmation/approval workflow,
   idempotency key, audit event, and outbox event before activation.
5. Add parser, authorization, adapter, RLS, and API integration tests.
6. Mark the adapter active only after all checks pass; it then becomes visible
   automatically in both `/api/cli/commands` and `/api/ai/tools`.
