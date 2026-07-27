# Warehouse OS 2.1

Warehouse OS 2.1 begins as a clean separation of the user-facing products from
the legacy runtime. The frontend designs are preserved here while the backend
and data layer are rebuilt independently for PostgreSQL.

## Included frontend products

| Path | Product |
| --- | --- |
| `frontend/v2/` | Warehouse OS 2.0 web application (the current Swiss/Bonfire design system) |
| `frontend/` | Classic web application and mobile web variants |
| `mobile/` | React Native mobile application |
| `wechat-miniapp/` | WeChat Mini Program |
| `screenshots/` | Visual design references |

`frontend/v2/` is self-contained and includes its versioned browser assets and
precompiled bundles. Rebuild or verify the V2 bundles with:

```sh
node scripts/build_v2_frontend.cjs
node scripts/build_v2_frontend.cjs --check
```

The applications still call the former `/api/...` contract. That is intentional:
no legacy service code, SQLite databases, secrets, deployment configuration, or
database migrations were copied into this repository. The new API contract will
be implemented by the backend rewrite and backed exclusively by PostgreSQL 18
with pgvector for permission-scoped AI retrieval.

See [the rebuild brief](docs/postgresql-backend-rebuild.md) for the proposed
starting boundary.

## Backend foundation

The first PostgreSQL-first API foundation lives in [`backend/`](backend/README.md).
It implements real database-backed health, authentication, bootstrap, and warehouse
map-topology endpoints without importing legacy SQLite routing or demo records.
It also includes 13 versioned industry templates. Each new tenant receives a
template-selected organization, position, permission, and navigation snapshot;
the former "超高壓電網" template is now named "電力系統" (`power_system`).
The [governed super terminal](docs/super-terminal.md) imports the 441-command
catalogue and exposes a single human/AI command contract with typed storage
ports; commands are activated only after their PostgreSQL domain adapter,
permissions, RLS, audit, and write-confirmation controls are ready.

Local runtime and Cloudflare Tunnel instructions are in
[`infra/LOCAL_RUNTIME.md`](infra/LOCAL_RUNTIME.md).
