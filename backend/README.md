# Warehouse OS 2.1 API

This is a clean PostgreSQL 18 + pgvector API foundation. It has no SQLite fallback,
no per-tenant database files, and no seeded demonstration data.

## What is implemented

- FastAPI service with liveness and PostgreSQL 18 + pgvector readiness checks;
- Alembic migration for IAM, warehouse topology, workflow, secretary,
  audit, and outbox foundations;
- PostgreSQL Row Level Security, scoped by `SET LOCAL app.tenant_id` for
  every tenant-domain transaction;
- `pgvector` knowledge chunks and an HNSW cosine-similarity index for the AI
  secretary's permission-scoped retrieval;
- 13 versioned industry templates persisted in PostgreSQL, including
  `power_system` (電力系統), with every template's departments, positions,
  permissions, navigation defaults, and special BIU catalogue metadata;
- tenant provisioning that snapshots the selected template into RLS-protected
  organization and position tables;
- separate administrator, migration, and API database roles: the API role is
  explicitly non-superuser and therefore cannot bypass RLS.
- real `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/bootstrap`, and
  `GET /api/map/zones` compatibility endpoints;
- governed super-terminal foundation: the complete 441-command legacy
  catalogue, a shared human/AI executor, typed storage ports, PostgreSQL audit
  records with forced RLS, and explicitly gated command activation;
- an interactive command for creating the first real tenant administrator.

## Local setup

```sh
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
# Install pgvector once as the database administrator, before running migrations.
/opt/homebrew/opt/postgresql@18/bin/psql -d warehouse_os -c 'CREATE EXTENSION IF NOT EXISTS vector'
.venv/bin/alembic upgrade head
.venv/bin/python -m app.bootstrap_admin \
  --tenant-slug bonfire --tenant-name 'Bonfire Workshop' \
  --username owner --display-name 'Owner' \
  --industry-template power_system
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8080
```

The application must use a PostgreSQL role without `BYPASSRLS` in production.
Install trusted extensions with an administrator account; migrations run with a
separate, non-superuser migration role. Do not expose PostgreSQL's port to the
internet.

## Validation

```sh
.venv/bin/ruff check .
.venv/bin/pytest
curl http://127.0.0.1:8080/health
curl http://127.0.0.1:8080/api/health
```

After signing in, list the provisionable catalogue at
`GET /api/platform/templates` (also available as `GET /api/industry-templates`)
and retrieve one full blueprint at `GET /api/industry-templates/{template_key}`.
See [the super-terminal design](../docs/super-terminal.md) for command state,
AI tool routing, and the database-replacement boundary.
