# Workspace Source and Runtime retention

Warehouse keeps deployment, custody, release, and audit rows as historical
evidence. Retention reclaims physical copies; it does not delete that evidence.

## Safety contract

`GET /api/workspaces/v1/retention/plan` is read-only. Its plan automatically
protects:

- the active Deployment and the previous Deployment recorded for rollback;
- every Pages active pointer and every in-progress Deployment or Release;
- at least the two newest healthy service Deployments per component;
- the current Source of each component, Sources used by retained Deployments,
  Sources used by open Releases or uploads, and at least five recent Sources;
- objects carrying an explicit `retention.pinned` marker.

The response contains exact candidates, protection reasons, estimated reclaim
bytes, and a deterministic `plan_digest`. Host paths, object keys, and managed
container names are never returned.

`POST /api/workspaces/v1/retention/apply` requires the workspace primary key,
both `deploy:write` and `infra:write`, the same policy, and
`confirm_plan_digest`. The server locks the workspace, recomputes the plan, and
returns `409 retention_plan_changed` if any pointer or candidate changed.

## Retirement model

- A retired Runtime directory is removed only below the exact
  `tenants/<tenant>/workspaces/<workspace>/releases/<deployment>` boundary.
- A managed container name must match the Runtime Controller namespace before
  it can be removed.
- A Source object is removed only when its tenant, SHA-256, and
  content-addressed key agree and no other live artifact references it.
- Source and Deployment database rows remain. Deployment events, custody
  release events, and workspace audit events record the run and plan digest.
- Interrupted work remains marked `retry_required` and is selected by the next
  plan, rather than being silently reported as reclaimed.
- Expired or cancelled resumable-upload staging is eligible; active uploads are
  never selected.

Example preview:

```text
GET /api/workspaces/v1/retention/plan
  ?keep_recent_deployments=2
  &keep_recent_sources=5
  &min_age_hours=24
```

Example apply body:

```json
{
  "keep_recent_deployments": 2,
  "keep_recent_sources": 5,
  "min_age_hours": 24,
  "include_sources": true,
  "include_expired_uploads": true,
  "confirm_plan_digest": "<the exact digest returned by the preview>"
}
```

The first production pass for a workspace may deliberately use a shorter age
only after an operator reviews all protected IDs and candidates. Routine use
should keep the 24-hour default so a just-finished candidate remains available
for diagnosis.
