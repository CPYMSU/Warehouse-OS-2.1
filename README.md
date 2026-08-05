# Warehouse OS 2.1

Warehouse OS 2.1 begins as a clean separation of the user-facing products from
the legacy runtime. The frontend designs are preserved here while the backend
and data layer are rebuilt independently for PostgreSQL.

## Included frontend products

| Path | Product |
| --- | --- |
| `frontend/v2/` | Warehouse OS 2.1 web application (the current Swiss/Bonfire design system) |
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

The preserved clients still contain compatibility calls, but Warehouse OS 2.1
does not import the former service runtime, customer databases, secrets or
deployment state. Native 2.1 domains use PostgreSQL 18 with forced tenant RLS;
unmigrated compatibility calls must report an explicit unavailable state rather
than fabricate data or silently fall back to the former system.

See [the rebuild brief](docs/postgresql-backend-rebuild.md) for the original
boundary and the documentation map below for the current contracts.

## Backend foundation

The first PostgreSQL-first API foundation lives in [`backend/`](backend/README.md).
It implements real database-backed health, authentication, bootstrap, and warehouse
map-topology endpoints without importing legacy SQLite routing or demo records.
It also includes 13 versioned industry templates. Each new tenant receives a
template-selected organization, position, permission, and navigation snapshot;
the former "超高壓電網" template is now named "電力系統" (`power_system`).
The [Auto Runtime and Super Terminal](docs/super-terminal.md) make the
Secretary, professional terminal, and embedded assistants different surfaces
of one goal-driven runtime. The retained 480-command catalogue is a legacy
compatibility and capability-discovery boundary; retired contracts remain
searchable as history but cannot be executed or exposed as model tools.

## Current contract documents

| Contract | Document |
| --- | --- |
| Customer digital-asset custody, workspace keys and `dam.py` | [Warehouse OS 2.1《數字資產託管指南》](docs/digital-asset-custody-guide-2.1.zh-TW.md) |
| Digital-asset providers, permanent entry, quota and runtime invariants | [Digital asset hosting contract](docs/digital-asset-hosting.md) |
| AI-native semantic mutation, Passkey and Action Keychain | [AI-native universal action fabric](docs/ai-native-universal-action-fabric.zh-TW.md) |
| Intelligent data decomposition and world observations | [Intelligent database decomposition](docs/intelligent-database-decomposition.zh-TW.md) |
| Runtime API, streaming and key lifecycle | [Runtime API](docs/runtime-api.md) |
| Production release, rollback and backups | [Production deployment](docs/production-deployment.md) |

Local runtime and Cloudflare Tunnel instructions are in
[`infra/LOCAL_RUNTIME.md`](infra/LOCAL_RUNTIME.md).

## Run the connected local stack

Do **not** start `frontend/v2` with a static file server on port 8080. A static
server makes every `/api/...` request return 404 and turns POST requests into
405 responses. Start the frontend, FastAPI routes, migrations, and PostgreSQL
through the governed entry point instead:

```sh
bash scripts/start_local.sh
```

The launcher creates the backend virtual environment, starts the local
PostgreSQL container when Docker is available, applies every Alembic migration,
and serves `frontend/v2` from the FastAPI process at `http://127.0.0.1:8080`.
Every response from the correct process includes:

```text
X-Warehouse-Backend: fastapi-postgresql
```

The retained frontend contract now has a PostgreSQL compatibility projection.
Modules with final 2.1 tables (IAM, tasks, workflows, audit, secretary, and
warehouse operations) read those tables directly. Other retained read models
use tenant-isolated `compatibility.documents`; absent data returns an explicit
`available: false` state and never demonstration data or a silent success.
