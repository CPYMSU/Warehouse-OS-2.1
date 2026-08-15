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
- append-only secretary transcripts plus a tenant-isolated layered memory
  fabric: complete-turn background distillation, evidence-bearing semantic,
  episodic and procedural memory, conflict relations, cached
  `index`/`focused`/`deep` resolution, and private-memory forgetting without
  deleting source messages;
- 13 versioned industry templates persisted in PostgreSQL, including
  `power_system` (電力系統), with every template's departments, positions,
  permissions, navigation defaults, and special BIU catalogue metadata;
- tenant provisioning that snapshots the selected template into RLS-protected
  organization and position tables;
- separate administrator, migration, and API database roles: the API role is
  explicitly non-superuser and therefore cannot bypass RLS.
- real `POST /api/auth/login`, `GET /api/auth/me`, `GET /api/bootstrap`, and
  `GET /api/map/zones` compatibility endpoints;
- shared Auto Runtime boundary: every current AI surface submits a goal to the
  same observe → understand → plan → act → reflect loop; all 559 non-retired capability
  genes are visible to its layered context, while execution remains bound to
  the current company's identity, PostgreSQL RLS scope, confirmation policy,
  and audit trail;
- catalogue-driven internal API dispatch: all 537 non-retired tenant commands retain their
  registered method/path/parameter contracts, use native FastAPI routes where
  available, and otherwise use a verified tenant-isolated capability adapter;
  the 22 platform commands remain L11-governed;
- an interactive command for creating the first real tenant administrator.

Terminal-based research upload and version inspection are documented in
[`docs/research-api.md`](../docs/research-api.md).
That contract now includes the downloadable, dependency-free
`bonfire-research` CLI for project, file, Git lineage, DMP, protocol, Run,
evidence, review, reproducibility, isolated execution, artifact, and release
automation with a research-only Runtime API Key.

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

Every AI Runtime upgrade batch must additionally run
`ops/run-ai-runtime-verification` from the repository root. That gate loads the
local DeepSeek credential without printing it and requires a real request
through the AI secretary HTTP surface, actual Runtime capability execution,
business-state readback, audit evidence, and durable transcript verification.
Mocked-provider and selector-only tests do not satisfy this acceptance gate.

After signing in, list the provisionable catalogue at
`GET /api/platform/templates` (also available as `GET /api/industry-templates`)
and retrieve one full blueprint at `GET /api/industry-templates/{template_key}`.
See [the Auto Runtime and Super Terminal design](../docs/super-terminal.md)
for the shared-surface contract and legacy compatibility boundary, and
[the Layered Memory Fabric](../docs/layered-memory-fabric.md) for conversation
distillation and resolution.
