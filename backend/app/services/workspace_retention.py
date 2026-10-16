"""Audited, plan-bound retention for hosted workspace source and Runtime data.

Database history is preserved.  Applying a plan only retires physical Runtime
copies, releases unreferenced source objects, and expires abandoned upload
staging.  Every destructive target is derived from tenant/workspace-bound rows
and is re-planned while the workspace row is locked.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    _audit,
    _custody_event,
    _workspace_billable_usage,
    _workspace_row,
)
from app.services.object_storage import object_store_for_provider

_TERMINAL_DEPLOYMENT_STATES = frozenset({"ready", "failed", "rolled_back", "cancelled"})
_SAFE_CONTAINER_NAME = re.compile(r"^warehouse-runtime-[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class RetentionPolicy:
    keep_recent_deployments: int = 2
    keep_recent_sources: int = 5
    min_age_hours: int = 24
    include_sources: bool = True
    include_expired_uploads: bool = True
    include_python_environments: bool = False
    retire_terminal_evidence: bool = False
    rollback_max_age_hours: int | None = None
    deployment_ids: tuple[str, ...] | None = None

    @classmethod
    def from_payload(cls, payload: dict[str, object] | None) -> RetentionPolicy:
        value = payload or {}

        def bounded(name: str, default: int, minimum: int, maximum: int) -> int:
            try:
                observed = int(value.get(name, default))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=f"{name} must be an integer") from exc
            if not minimum <= observed <= maximum:
                raise HTTPException(
                    status_code=422,
                    detail=f"{name} must be between {minimum} and {maximum}",
                )
            return observed

        def boolean(name: str, default: bool = False) -> bool:
            observed = value.get(name, default)
            if not isinstance(observed, bool):
                raise HTTPException(status_code=422, detail=f"{name} must be a boolean")
            return observed

        selected = value.get("deployment_ids")
        if selected is not None:
            if not isinstance(selected, list) or len(selected) > 200:
                raise HTTPException(status_code=422, detail="deployment_ids must be a UUID array")
            try:
                selected = tuple(
                    sorted({str(UUID(item)) for item in selected if isinstance(item, str)})
                )
                if len(selected) != len(value["deployment_ids"]):
                    raise ValueError("Duplicate or non-string deployment ID")
            except (ValueError, TypeError, AttributeError) as exc:
                raise HTTPException(status_code=422, detail="Invalid deployment_ids") from exc

        policy = cls(
            keep_recent_deployments=bounded("keep_recent_deployments", 2, 2, 20),
            keep_recent_sources=bounded("keep_recent_sources", 5, 2, 100),
            min_age_hours=bounded("min_age_hours", 24, 0, 8760),
            include_sources=boolean("include_sources", True),
            include_expired_uploads=boolean("include_expired_uploads", True),
            include_python_environments=boolean("include_python_environments"),
            retire_terminal_evidence=boolean("retire_terminal_evidence"),
            rollback_max_age_hours=(bounded("rollback_max_age_hours",72,72,8760)
                                    if value.get("rollback_max_age_hours") is not None else None),
            deployment_ids=selected,
        )
        if policy.retire_terminal_evidence and policy.min_age_hours < 72:
            raise HTTPException(status_code=422, detail="Evidence-copy retirement requires min_age_hours >= 72")
        return policy

    def public(self) -> dict[str, object]:
        return {
            "keep_recent_deployments": self.keep_recent_deployments,
            "keep_recent_sources": self.keep_recent_sources,
            "min_age_hours": self.min_age_hours,
            "include_sources": self.include_sources,
            "include_expired_uploads": self.include_expired_uploads,
            "include_python_environments": self.include_python_environments,
            # Keep existing clients and plan digests exact when not opted in.
            **({"retire_terminal_evidence": True} if self.retire_terminal_evidence else {}),
            **({"rollback_max_age_hours": self.rollback_max_age_hours}
               if self.rollback_max_age_hours is not None else {}),
            "deployment_ids": list(self.deployment_ids)
            if self.deployment_ids is not None
            else None,
        }


def _retention(value: object) -> dict[str, object]:
    source = value if isinstance(value, dict) else {}
    observed = source.get("retention")
    return dict(observed) if isinstance(observed, dict) else {}


def _pinned(value: object) -> bool:
    return bool(_retention(value).get("pinned"))


def _older_than(value: object, cutoff: datetime) -> bool:
    if not isinstance(value, datetime):
        return False
    observed = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return observed <= cutoff


def _tree_bytes(path: Path) -> int:
    if not path.exists() or path.is_symlink():
        return 0
    total = 0
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            for child in current.iterdir():
                if child.is_symlink():
                    continue
                if child.is_dir():
                    pending.append(child)
                elif child.is_file():
                    total += max(0, int(child.stat().st_size))
        except FileNotFoundError:
            continue
    return total


def _deployment_container_names(
    deployment_id: UUID,
    raw_names: object,
) -> list[str]:
    prefix = f"warehouse-runtime-{str(deployment_id).replace('-', '')[:16]}"
    return [
        str(name)
        for name in (raw_names if isinstance(raw_names, list) else [])
        if _SAFE_CONTAINER_NAME.fullmatch(str(name)) and str(name).startswith(prefix)
    ]


def _container_names_digest(names: list[str]) -> str:
    return hashlib.sha256(
        json.dumps(sorted(names), separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _containers_retired(result: object) -> bool:
    payload = result if isinstance(result, dict) else {}
    retention = _retention(payload)
    names = payload.get("container_names", [])
    if not isinstance(names, list) or any(not isinstance(x, str) for x in names):
        return False
    if len(names) != len(set(names)):
        return False
    return bool(
        retention.get("containers_retired_at")
        and retention.get("run_id")
        and retention.get("plan_digest")
        and retention.get("containers_retired_run_id") == retention.get("run_id")
        and retention.get("containers_retired_plan_digest") == retention.get("plan_digest")
        and retention.get("containers_retired_names_digest") == _container_names_digest(names)
    )


def _workspace_path(settings: Settings, tenant_id: UUID, workspace_id: UUID, *parts: str) -> Path:
    # Inspect lexical ancestors before resolve: resolving first hides symlinks.
    root = settings.hosted_runtime_data_root.absolute()
    target = root / "tenants" / str(tenant_id) / "workspaces" / str(workspace_id)
    for part in parts:
        if not part or part in {".", ".."} or Path(part).name != part:
            raise RuntimeError("Unsafe Runtime retention component")
        target /= part
    for ancestor in [*reversed(target.parents), target]:
        if ancestor.is_symlink():
            raise RuntimeError("Symlinked Runtime retention ancestor")
    target.relative_to(root)
    return target


def _release_path(
    settings: Settings,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    deployment_id: UUID,
) -> Path:
    return _workspace_path(settings, tenant_id, workspace_id, "releases", str(deployment_id))


def _deployment_rows(session: object, workspace_id: UUID) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in session.execute(
            text(
                "SELECT * FROM digital_asset.deployments "
                "WHERE workspace_id=:workspace_id ORDER BY created_at DESC,id DESC"
            ),
            {"workspace_id": workspace_id},
        )
        .mappings()
        .all()
    ]


def _python_environment_review(
    settings: Settings,
    credential: WorkspaceCredential,
    deployments: list[dict[str, object]],
    enabled: bool,
) -> dict[str, object]:
    """Report dependencies, never infer exclusivity from incomplete metadata.

    Directory/container retirement does not establish which retained or unknown
    runtime can consume a shared venv. Until the controller supplies a complete
    workspace reference attestation, every environment remains held.
    """
    if not enabled:
        return {"enabled": False, "status": "disabled", "candidates": [], "held": []}
    consumers: dict[str, list[str]] = {}
    unknown: list[str] = []
    for row in deployments:
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        if _retention(result).get("state") == "retired":
            continue
        build = result.get("build") if isinstance(result.get("build"), dict) else {}
        digest = str(build.get("build_digest") or "")
        if re.fullmatch(r"[a-f0-9]{64}", digest):
            consumers.setdefault(digest, []).append(str(row["id"]))
        elif result.get("runtime_kind") not in {"static", "node"}:
            unknown.append(str(row["id"]))
    root = _workspace_path(
        settings, credential.tenant_id, credential.workspace_id, "data", ".runtime", "python"
    )
    held = []
    if root.exists():
        for child in sorted(root.iterdir(), key=lambda item: item.name):
            reasons = ["workspace_environment_reference_attestation_unavailable"]
            if child.is_symlink():
                reasons.append("symlinked_environment")
            if child.name not in consumers:
                reasons.append("unknown_environment_consumers")
            if unknown:
                reasons.append("deployment_environment_mapping_incomplete")
            held.append(
                {
                    "environment_id": child.name,
                    "known_consumers": sorted(consumers.get(child.name, [])),
                    "reasons": reasons,
                }
            )
    return {
        "enabled": True,
        "status": "held",
        "candidates": [],
        "held": held,
        "unknown_deployment_ids": sorted(unknown),
        "complete_reference_closure": False,
        "reclaimed_bytes": 0,
    }


def _build_plan(
    session: object,
    credential: WorkspaceCredential,
    settings: Settings,
    policy: RetentionPolicy,
    *,
    workspace: dict[str, object] | None = None,
) -> dict[str, object]:
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=policy.min_age_hours)
    rollback_cutoff = (now-timedelta(hours=policy.rollback_max_age_hours)
                       if policy.rollback_max_age_hours is not None else None)
    workspace = workspace or _workspace_row(session, credential.workspace_id)
    asset_id = UUID(str(workspace["asset_id"]))
    active_id = (
        UUID(str(workspace["active_deployment_id"]))
        if workspace.get("active_deployment_id")
        else None
    )
    deployments = _deployment_rows(session, credential.workspace_id)
    by_id = {UUID(str(row["id"])): row for row in deployments}
    protected_deployments: dict[UUID, set[str]] = {}

    def protect_deployment(value: object, reason: str) -> None:
        if value in (None, ""):
            return
        try:
            resolved = UUID(str(value))
        except ValueError:
            return
        if resolved in by_id:
            protected_deployments.setdefault(resolved, set()).add(reason)

    protect_deployment(active_id, "active")
    if active_id is not None:
        active_result = by_id.get(active_id, {}).get("result")
        if isinstance(active_result, dict):
            previous = active_result.get("previous_active_deployment_id")
            try:
                previous_row = by_id.get(UUID(str(previous))) if previous else None
            except (TypeError,ValueError,AttributeError):
                previous_row = None
            active_row = by_id.get(active_id, {})
            can_expire = (rollback_cutoff is not None and previous_row is not None
                          and active_row.get("status")=="ready" and active_row.get("health")=="healthy"
                          and _older_than(previous_row.get("created_at"),rollback_cutoff))
            if not can_expire:
                protect_deployment(previous,"previous_rollback")

    for route in session.execute(
        text(
            "SELECT active_deployment_id,config FROM platform.pages_routes "
            "WHERE workspace_id=:workspace_id"
        ),
        {"workspace_id": credential.workspace_id},
    ).mappings():
        protect_deployment(route.get("active_deployment_id"), "pages_active")
        config = route.get("config") if isinstance(route.get("config"), dict) else {}
        frontend = config.get("static_frontend")
        if isinstance(frontend, dict):
            protect_deployment(frontend.get("deployment_id"), "pages_static_frontend")
            relative = str(frontend.get("runtime_rel_path") or "")
            prefix = (
                f"tenants/{credential.tenant_id}/workspaces/{credential.workspace_id}/releases/"
            )
            if relative.startswith(prefix):
                protect_deployment(
                    relative[len(prefix) :].split("/", 1)[0], "pages_static_frontend_path"
                )

    open_releases = [
        dict(row)
        for row in session.execute(
            text(
                "SELECT * FROM digital_asset.release_sessions "
                "WHERE workspace_id=:workspace_id "
                "AND state NOT IN ('verified','failed','rolled_back','cancelled','blocked')"
            ),
            {"workspace_id": credential.workspace_id},
        )
        .mappings()
        .all()
    ]
    for release in open_releases:
        for field in (
            "candidate_deployment_id",
            "current_job_deployment_id",
            "previous_deployment_id",
        ):
            protect_deployment(release.get(field), "open_release")

    recent_by_component: dict[str, int] = {}
    for row in deployments:
        deployment_id = UUID(str(row["id"]))
        requested = (
            row.get("requested_config") if isinstance(row.get("requested_config"), dict) else {}
        )
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        if str(row["status"]) not in _TERMINAL_DEPLOYMENT_STATES:
            protect_deployment(deployment_id, "in_progress")
        if _pinned(requested) or _pinned(result):
            protect_deployment(deployment_id, "pinned")
        is_service = (
            str(requested.get("execution_mode") or "service") != "job"
            and str(result.get("execution_mode") or "service") != "job"
        )
        expire_evidence_copy = (
            policy.retire_terminal_evidence
            and str(row["status"]) in _TERMINAL_DEPLOYMENT_STATES
            and _older_than(row.get("created_at"), cutoff)
        )
        if not is_service and not expire_evidence_copy:
            protect_deployment(deployment_id, "job_evidence")
        if str(row["status"]) == "failed" and not expire_evidence_copy:
            protect_deployment(deployment_id, "failed_evidence")
        if is_service and str(row["status"]) == "ready" and str(row.get("health")) == "healthy":
            component = str(row.get("component_id") or "workspace")
            count = recent_by_component.get(component, 0)
            if count < policy.keep_recent_deployments and (rollback_cutoff is None or not _older_than(row.get("created_at"),rollback_cutoff)):
                protect_deployment(deployment_id, "recent_service")
                recent_by_component[component] = count + 1

    if policy.deployment_ids is not None:
        if any(UUID(value) not in by_id for value in policy.deployment_ids):
            raise HTTPException(status_code=422, detail="Unknown workspace deployment_ids")
    deployment_candidates: list[dict[str, object]] = []
    for row in deployments:
        deployment_id = UUID(str(row["id"]))
        result = row.get("result") if isinstance(row.get("result"), dict) else {}
        retention = _retention(result)
        recovery = str(retention.get("state") or "") in {"retiring", "retry_required"}
        if str(retention.get("state") or "") == "retired":
            continue
        if deployment_id in protected_deployments:
            continue
        if policy.deployment_ids is not None and str(deployment_id) not in policy.deployment_ids:
            continue
        if not recovery:
            if str(row["status"]) not in _TERMINAL_DEPLOYMENT_STATES:
                continue
            if deployment_id in protected_deployments:
                continue
            if not _older_than(row.get("created_at"), cutoff):
                continue
        target = _release_path(
            settings,
            tenant_id=credential.tenant_id,
            workspace_id=credential.workspace_id,
            deployment_id=deployment_id,
        )
        container_names = _deployment_container_names(
            deployment_id,
            result.get("container_names"),
        )
        deployment_candidates.append(
            {
                "id": str(deployment_id),
                "source_version_id": (
                    str(row["source_version_id"]) if row.get("source_version_id") else None
                ),
                "status": str(row["status"]),
                "created_at": row["created_at"].isoformat(),
                "estimated_runtime_bytes": _tree_bytes(target),
                "_container_names": container_names,
                "_containers_retired": _containers_retired(result),
                "_retention": retention,
                "_path": str(target),
            }
        )

    candidate_deployment_ids = {UUID(str(item["id"])) for item in deployment_candidates}
    protected_sources: dict[UUID, set[str]] = {}

    def protect_source(value: object, reason: str) -> None:
        if value in (None, ""):
            return
        try:
            resolved = UUID(str(value))
        except ValueError:
            return
        protected_sources.setdefault(resolved, set()).add(reason)

    for row in deployments:
        deployment_id = UUID(str(row["id"]))
        retention = _retention(row.get("result"))
        if deployment_id not in candidate_deployment_ids and retention.get("state") != "retired":
            protect_source(row.get("source_version_id"), "retained_deployment")
    for value in session.execute(
        text(
            "SELECT source_version_id FROM digital_asset.workspace_components "
            "WHERE workspace_id=:workspace_id AND source_version_id IS NOT NULL"
        ),
        {"workspace_id": credential.workspace_id},
    ).scalars():
        protect_source(value, "component_current")
    for release in open_releases:
        protect_source(release.get("source_version_id"), "open_release")
    for value in session.execute(
        text(
            "SELECT source_version_id FROM digital_asset.source_upload_jobs "
            "WHERE workspace_id=:workspace_id "
            "AND status IN ('created','uploading','queued','verifying') "
            "AND source_version_id IS NOT NULL"
        ),
        {"workspace_id": credential.workspace_id},
    ).scalars():
        protect_source(value, "active_upload")

    sources = [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT v.id AS source_version_id,v.version_no,v.created_at,
                       ar.id AS artifact_id,ar.size_bytes,ar.sha256,
                       ar.storage_provider,ar.object_key,ar.state,ar.verification
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar
                  ON ar.version_id=v.id AND ar.storage_role='code'
                WHERE v.asset_id=:asset_id
                ORDER BY v.created_at DESC,v.id DESC
                """
            ),
            {"asset_id": asset_id},
        )
        .mappings()
        .all()
    ]
    recent = 0
    for row in sources:
        source_id = UUID(str(row["source_version_id"]))
        if str(row["state"]) == "verified" and recent < policy.keep_recent_sources and (rollback_cutoff is None or not _older_than(row.get("created_at"),rollback_cutoff)):
            protect_source(source_id, "recent_source")
            recent += 1
        if _pinned(row.get("verification")):
            protect_source(source_id, "pinned")

    source_candidates: list[dict[str, object]] = []
    if policy.include_sources:
        for row in sources:
            source_id = UUID(str(row["source_version_id"]))
            retention = _retention(row.get("verification"))
            recovery = str(retention.get("state") or "") in {"retiring", "retry_required"}
            if str(row["state"]) == "released" or retention.get("state") == "retired":
                continue
            if source_id in protected_sources:
                continue
            if not recovery:
                if str(row["state"]) != "verified":
                    continue
                if source_id in protected_sources:
                    continue
                if not _older_than(row.get("created_at"), cutoff):
                    continue
            shared_live_references = int(
                session.execute(
                    text(
                        """
                        SELECT count(*) FROM digital_asset.artifacts
                        WHERE tenant_id=:tenant_id AND id != :artifact_id
                          AND storage_provider=:provider AND object_key=:object_key
                          AND state IN ('pending','stored','verified','quarantined')
                        """
                    ),
                    {
                        "tenant_id": credential.tenant_id,
                        "artifact_id": row["artifact_id"],
                        "provider": row["storage_provider"],
                        "object_key": row["object_key"],
                    },
                ).scalar_one()
            )
            source_candidates.append(
                {
                    "source_version_id": str(source_id),
                    "artifact_id": str(row["artifact_id"]),
                    "version_no": str(row["version_no"]),
                    "created_at": row["created_at"].isoformat(),
                    "logical_bytes": int(row["size_bytes"]),
                    "delete_physical_object": shared_live_references == 0,
                    "_provider": str(row["storage_provider"]),
                    "_object_key": str(row["object_key"]),
                    "_sha256": str(row["sha256"]),
                }
            )

    expired_uploads: list[dict[str, object]] = []
    if policy.include_expired_uploads:
        upload_rows = session.execute(
            text(
                """
                SELECT id,status,storage_provider,received_bytes,expires_at
                FROM digital_asset.source_upload_jobs
                WHERE workspace_id=:workspace_id
                  AND NOT (result ? 'staging_cleaned_at')
                  AND (
                    (status IN ('created','uploading','failed') AND expires_at <= now())
                    OR status IN ('expired','cancelled')
                  )
                ORDER BY created_at
                """
            ),
            {"workspace_id": credential.workspace_id},
        ).mappings()
        for row in upload_rows:
            expired_uploads.append(
                {
                    "upload_id": str(row["id"]),
                    "status": str(row["status"]),
                    "received_bytes": int(row.get("received_bytes") or 0),
                    "expires_at": row["expires_at"].isoformat(),
                    "_provider": str(row["storage_provider"]),
                }
            )

    environment_review = _python_environment_review(
        settings,
        credential,
        deployments,
        policy.include_python_environments,
    )
    digest_payload = {
        "python_environments": environment_review,
        "workspace_id": str(credential.workspace_id),
        "active_deployment_id": str(active_id) if active_id else None,
        "policy": policy.public(),
        "deployment_candidates": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in deployment_candidates
        ],
        "source_candidates": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in source_candidates
        ],
        "expired_uploads": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in expired_uploads
        ],
    }
    # Bind the confirmation to private execution targets as well as the public
    # candidate projection.  The target material is never returned, but a
    # changed object key, digest, provider, or container set invalidates the
    # operator's confirmation.
    digest_material = {
        **digest_payload,
        "execution_targets": {
            "deployments": [
                {
                    "id": item["id"],
                    "container_names": item["_container_names"],
                    "containers_retired": item["_containers_retired"],
                    "retention_state": item["_retention"].get("state"),
                    "retention_run_id": item["_retention"].get("run_id"),
                    "retention_plan_digest": item["_retention"].get("plan_digest"),
                }
                for item in deployment_candidates
            ],
            "sources": [
                {
                    "artifact_id": item["artifact_id"],
                    "provider": item["_provider"],
                    "object_key": item["_object_key"],
                    "sha256": item["_sha256"],
                }
                for item in source_candidates
            ],
            "uploads": [
                {
                    "upload_id": item["upload_id"],
                    "provider": item["_provider"],
                }
                for item in expired_uploads
            ],
        },
    }
    plan_digest = hashlib.sha256(
        json.dumps(
            digest_material,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "ok": True,
        "schema": "warehouse.workspace-retention-plan.v1",
        "generated_at": now.isoformat(),
        "plan_digest": plan_digest,
        "apply_confirmation": plan_digest,
        **digest_payload,
        # Internal execution targets remain available to the apply path.  The
        # API projection strips every underscore-prefixed field.
        "deployment_candidates": deployment_candidates,
        "source_candidates": source_candidates,
        "expired_uploads": expired_uploads,
        "protected": {
            "deployments": [
                {"id": str(item), "reasons": sorted(reasons)}
                for item, reasons in sorted(
                    protected_deployments.items(), key=lambda pair: str(pair[0])
                )
            ],
            "sources": [
                {"id": str(item), "reasons": sorted(reasons)}
                for item, reasons in sorted(
                    protected_sources.items(), key=lambda pair: str(pair[0])
                )
            ],
        },
        "estimated_reclaim": {
            "runtime_bytes": sum(
                int(item["estimated_runtime_bytes"]) for item in deployment_candidates
            ),
            "source_logical_bytes": sum(int(item["logical_bytes"]) for item in source_candidates),
            "upload_staging_bytes": sum(int(item["received_bytes"]) for item in expired_uploads),
        },
    }


def _public_plan(plan: dict[str, object]) -> dict[str, object]:
    def clean(items: object) -> list[dict[str, object]]:
        return [
            {key: value for key, value in dict(item).items() if not key.startswith("_")}
            for item in (items if isinstance(items, list) else [])
        ]

    return {
        **plan,
        "deployment_candidates": clean(plan.get("deployment_candidates")),
        "source_candidates": clean(plan.get("source_candidates")),
        "expired_uploads": clean(plan.get("expired_uploads")),
    }


def plan_workspace_retention(
    credential: WorkspaceCredential,
    settings: Settings,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    credential.require("deploy:read")
    credential.require("infra:read")
    policy = RetentionPolicy.from_payload(payload)
    with tenant_session(credential.tenant_id) as session:
        plan = _build_plan(session, credential, settings, policy)
    return _public_plan(plan)


def _expire_confirmed_previous_reference(session, credential, plan, run_id):
    """Expire only the confirmed old rollback pointer under the workspace lock.

    Current runtime, audit rows and pinned/routed/open references remain intact.
    Clearing the pointer makes the controller's normal reference check accurate;
    it does not add a way to bypass that check.
    """
    hours = plan["policy"].get("rollback_max_age_hours")
    active_id = plan.get("active_deployment_id")
    if hours is None or not active_id:
        return
    active = dict(session.execute(text(
        "SELECT * FROM digital_asset.deployments WHERE id=:id AND workspace_id=:workspace_id FOR UPDATE"
    ), {"id":UUID(active_id),"workspace_id":credential.workspace_id}).mappings().one())
    result = dict(active.get("result") or {})
    previous = str(result.get("previous_active_deployment_id") or "")
    candidate = next((r for r in plan["deployment_candidates"] if r["id"]==previous),None)
    if candidate is None:
        return
    if (active.get("status")!="ready" or active.get("health")!="healthy"
        or not _older_than(datetime.fromisoformat(candidate["created_at"]),datetime.now(UTC)-timedelta(hours=hours))):
        raise RuntimeError("rollback_reference_now_protected")
    result.pop("previous_active_deployment_id")
    result["expired_rollback_reference"]={"deployment_id":previous,"run_id":str(run_id),
        "plan_digest":plan["plan_digest"],"expired_at":datetime.now(UTC).isoformat(),"max_age_hours":hours}
    session.execute(text("UPDATE digital_asset.deployments SET result=CAST(:result AS jsonb) WHERE id=:id"),
                    {"id":UUID(active_id),"result":json.dumps(result,default=str)})
    _audit(session,None,"digital_asset.rollback_window_expired",
           {"workspace_id":str(credential.workspace_id),"active_deployment_id":active_id,
            **result["expired_rollback_reference"]},tenant_id=credential.tenant_id)


def _mark_retiring(
    session: object,
    credential: WorkspaceCredential,
    plan: dict[str, object],
    run_id: UUID,
) -> None:
    now = datetime.now(UTC).isoformat()
    for item in plan["deployment_candidates"]:
        deployment_id = UUID(str(item["id"]))
        row = (
            session.execute(
                text("SELECT status,health,result FROM digital_asset.deployments WHERE id=:id"),
                {"id": deployment_id},
            )
            .mappings()
            .one()
        )
        result = dict(row["result"]) if isinstance(row.get("result"), dict) else {}
        previous = _retention(result)
        continuing = (
            previous.get("state") in {"retiring", "retry_required"}
            and previous.get("run_id")
            and previous.get("plan_digest")
        )
        if not continuing:
            previous = {
                key: value
                for key, value in previous.items()
                if not key.startswith("containers_retired_")
            }
        result["retention"] = {
            **previous,
            "state": "retiring",
            "run_id": previous["run_id"] if continuing else str(run_id),
            "plan_digest": previous["plan_digest"] if continuing else plan["plan_digest"],
            "previous_status": previous.get("previous_status", str(row["status"])),
            "started_at": previous.get("started_at", now) if continuing else now,
        }
        item["_execution_run_id"] = result["retention"]["run_id"]
        item["_execution_plan_digest"] = result["retention"]["plan_digest"]
        session.execute(
            text(
                """
                UPDATE digital_asset.deployments
                SET status=CASE WHEN status='ready' THEN 'rolled_back' ELSE status END,
                    health=CASE WHEN status='ready' THEN 'unknown' ELSE health END,
                    result=CAST(:result AS jsonb)
                WHERE id=:id
                """
            ),
            {"id": deployment_id, "result": json.dumps(result, default=str)},
        )
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence),0)+1 FROM digital_asset.deployment_events "
                    "WHERE deployment_id=:id"
                ),
                {"id": deployment_id},
            ).scalar_one()
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id,tenant_id,sequence,event_type,payload
                ) VALUES (
                  :id,:tenant_id,:sequence,'storage_retirement_started',CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "id": deployment_id,
                "tenant_id": credential.tenant_id,
                "sequence": sequence,
                "payload": json.dumps({"run_id": str(run_id), "plan_digest": plan["plan_digest"]}),
            },
        )
    for item in plan["source_candidates"]:
        artifact_id = UUID(str(item["artifact_id"]))
        row = (
            session.execute(
                text("SELECT state,verification FROM digital_asset.artifacts WHERE id=:id"),
                {"id": artifact_id},
            )
            .mappings()
            .one()
        )
        verification = (
            dict(row["verification"]) if isinstance(row.get("verification"), dict) else {}
        )
        verification["retention"] = {
            **_retention(verification),
            "state": "retiring",
            "run_id": str(run_id),
            "plan_digest": plan["plan_digest"],
            "previous_state": str(row["state"]),
            "started_at": now,
        }
        session.execute(
            text(
                "UPDATE digital_asset.artifacts SET state='quarantined',"
                "verification=CAST(:verification AS jsonb) WHERE id=:id"
            ),
            {"id": artifact_id, "verification": json.dumps(verification, default=str)},
        )
    for item in plan["expired_uploads"]:
        session.execute(
            text(
                "UPDATE digital_asset.source_upload_jobs SET status='expired',updated_at=now() "
                "WHERE id=:id AND status IN ('created','uploading','failed','expired','cancelled')"
            ),
            {"id": UUID(str(item["upload_id"]))},
        )
    _audit(
        session,
        None,
        "digital_asset.workspace_retention_started",
        {
            "workspace_id": str(credential.workspace_id),
            "run_id": str(run_id),
            "plan_digest": plan["plan_digest"],
            "policy": plan["policy"],
            "deployment_count": len(plan["deployment_candidates"]),
            "source_count": len(plan["source_candidates"]),
            "expired_upload_count": len(plan["expired_uploads"]),
            "credential_id": str(credential.credential_id),
        },
        tenant_id=credential.tenant_id,
    )


def _retention_error(exc: Exception) -> str:
    allowed = {
        "retention_target_now_protected_or_changed",
        "retention_container_set_changed",
        "retention_operation_changed",
        "runtime_controller_cleanup_pending",
        "Symlinked Runtime retention ancestor",
        "Unsafe Runtime retention component",
    }
    message = str(exc)
    return message if message in allowed else f"retention_operation_failed:{type(exc).__name__}"


def apply_workspace_retention(
    credential: WorkspaceCredential,
    settings: Settings,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    credential.require("deploy:write")
    credential.require("infra:write")
    if credential.key_kind != "primary":
        raise HTTPException(status_code=403, detail="Retention apply requires the primary key")
    request = payload or {}
    policy = RetentionPolicy.from_payload(request)
    confirmed_digest = str(request.get("confirm_plan_digest") or "").strip().lower()
    if not re.fullmatch(r"[a-f0-9]{64}", confirmed_digest):
        raise HTTPException(status_code=422, detail="confirm_plan_digest is required")
    run_id = uuid4()
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        plan = _build_plan(session, credential, settings, policy, workspace=workspace)
        if plan["plan_digest"] != confirmed_digest:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "retention_plan_changed",
                    "expected_plan_digest": confirmed_digest,
                    "current_plan": _public_plan(plan),
                },
            )
        _expire_confirmed_previous_reference(session, credential, plan, run_id)
        _mark_retiring(session, credential, plan, run_id)

    deployment_results: dict[str, dict[str, object]] = {}
    source_results: dict[str, dict[str, object]] = {}
    upload_results: dict[str, dict[str, object]] = {}

    for item in plan["deployment_candidates"]:
        deployment_id = str(item["id"])
        try:
            # The controller takes locks in this same order. Keep the workspace
            # lock through the physical delete so new bindings cannot interleave.
            with tenant_session(credential.tenant_id) as session:
                workspace = _workspace_row(session, credential.workspace_id, lock=True)
                locked = (
                    session.execute(
                        text(
                            "SELECT result FROM digital_asset.deployments "
                            "WHERE id=:id AND workspace_id=:workspace_id FOR UPDATE"
                        ),
                        {"id": UUID(deployment_id), "workspace_id": credential.workspace_id},
                    )
                    .mappings()
                    .one()
                )
                fresh = _build_plan(session, credential, settings, policy, workspace=workspace)
                current = next(
                    (
                        entry
                        for entry in fresh["deployment_candidates"]
                        if entry["id"] == deployment_id
                    ),
                    None,
                )
                if current is None:
                    raise RuntimeError("retention_target_now_protected_or_changed")
                if current["_container_names"] != item["_container_names"]:
                    raise RuntimeError("retention_container_set_changed")
                if (
                    current["_retention"].get("run_id") != item["_execution_run_id"]
                    or current["_retention"].get("plan_digest") != item["_execution_plan_digest"]
                ):
                    raise RuntimeError("retention_operation_changed")
                if not current["_containers_retired"]:
                    raise RuntimeError("runtime_controller_cleanup_pending")
                target = _release_path(
                    settings,
                    tenant_id=credential.tenant_id,
                    workspace_id=credential.workspace_id,
                    deployment_id=UUID(deployment_id),
                )
                reclaimed = _tree_bytes(target)
                if target.exists():
                    shutil.rmtree(target, ignore_errors=False)
                # Persist this physical outcome before releasing the lifecycle
                # locks. An interrupted aggregate response can be resumed without
                # treating a removed directory as an unrecorded retirement.
                runtime_result = dict(locked["result"] or {})
                runtime_result["retention"] = {
                    **_retention(runtime_result),
                    "state": "retired",
                    "finished_at": datetime.now(UTC).isoformat(),
                    "reclaimed_bytes": reclaimed,
                }
                session.execute(
                    text(
                        "UPDATE digital_asset.deployments SET result=CAST(:result AS jsonb) "
                        "WHERE id=:id"
                    ),
                    {"id": UUID(deployment_id), "result": json.dumps(runtime_result, default=str)},
                )
                deployment_results[deployment_id] = {"ok": True, "reclaimed_bytes": reclaimed}
        except Exception as exc:
            deployment_results[deployment_id] = {
                "ok": False,
                "error": _retention_error(exc),
                "reclaimed_bytes": 0,
            }

    for item in plan["source_candidates"]:
        artifact_id = str(item["artifact_id"])
        try:
            reclaimed = 0
            if bool(item["delete_physical_object"]):
                store = object_store_for_provider(settings, str(item["_provider"]))
                reclaimed = store.retire_content_addressed_object(
                    tenant_id=credential.tenant_id,
                    object_key=str(item["_object_key"]),
                    sha256=str(item["_sha256"]),
                )
            source_results[artifact_id] = {
                "ok": True,
                "reclaimed_physical_bytes": reclaimed,
                "reclaimed_logical_bytes": int(item["logical_bytes"]),
            }
        except Exception as exc:
            source_results[artifact_id] = {
                "ok": False,
                "error": _retention_error(exc),
                "reclaimed_physical_bytes": 0,
                "reclaimed_logical_bytes": 0,
            }

    for item in plan["expired_uploads"]:
        upload_id = str(item["upload_id"])
        try:
            store = object_store_for_provider(settings, str(item["_provider"]))
            store.remove_source_upload(
                tenant_id=credential.tenant_id,
                upload_id=UUID(upload_id),
            )
            upload_results[upload_id] = {
                "ok": True,
                "reclaimed_bytes": int(item["received_bytes"]),
            }
        except Exception as exc:
            upload_results[upload_id] = {
                "ok": False,
                "error": _retention_error(exc),
                "reclaimed_bytes": 0,
            }

    finished_at = datetime.now(UTC).isoformat()
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        actor_user_id = session.execute(
            text("SELECT issued_by FROM digital_asset.api_credentials WHERE id=:id"),
            {"id": credential.credential_id},
        ).scalar_one_or_none()
        for item in plan["deployment_candidates"]:
            deployment_id = str(item["id"])
            outcome = deployment_results[deployment_id]
            row = (
                session.execute(
                    text("SELECT result FROM digital_asset.deployments WHERE id=:id"),
                    {"id": UUID(deployment_id)},
                )
                .mappings()
                .one()
            )
            result = dict(row["result"]) if isinstance(row.get("result"), dict) else {}
            recorded = _retention(result)
            if recorded.get("state") == "retired" and not outcome["ok"]:
                # Another confirmed retry may finish the same operation first.
                # Never regress its durable outcome or count its bytes twice.
                outcome = {"ok": True, "reclaimed_bytes": 0}
                deployment_results[deployment_id] = outcome
                continue
            elif (
                recorded.get("run_id") != item["_execution_run_id"]
                or recorded.get("plan_digest") != item["_execution_plan_digest"]
            ):
                deployment_results[deployment_id] = {
                    "ok": False,
                    "error": "retention_operation_changed",
                    "reclaimed_bytes": 0,
                }
                continue
            result["retention"] = {
                **recorded,
                "state": "retired" if outcome["ok"] else "retry_required",
                "finished_at": finished_at,
                "reclaimed_bytes": int(outcome.get("reclaimed_bytes") or 0),
                **({"error": outcome["error"]} if not outcome["ok"] else {}),
            }
            session.execute(
                text(
                    "UPDATE digital_asset.deployments SET result=CAST(:result AS jsonb) "
                    "WHERE id=:id"
                ),
                {"id": UUID(deployment_id), "result": json.dumps(result, default=str)},
            )
            sequence = int(
                session.execute(
                    text(
                        "SELECT COALESCE(max(sequence),0)+1 FROM digital_asset.deployment_events "
                        "WHERE deployment_id=:id"
                    ),
                    {"id": UUID(deployment_id)},
                ).scalar_one()
            )
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.deployment_events(
                      deployment_id,tenant_id,sequence,event_type,payload
                    ) VALUES (:id,:tenant_id,:sequence,:event_type,CAST(:payload AS jsonb))
                    """
                ),
                {
                    "id": UUID(deployment_id),
                    "tenant_id": credential.tenant_id,
                    "sequence": sequence,
                    "event_type": (
                        "storage_retired" if outcome["ok"] else "storage_retirement_retry_required"
                    ),
                    "payload": json.dumps({"run_id": str(run_id), **outcome}),
                },
            )
        for item in plan["source_candidates"]:
            artifact_id = str(item["artifact_id"])
            outcome = source_results[artifact_id]
            row = (
                session.execute(
                    text("SELECT verification FROM digital_asset.artifacts WHERE id=:id"),
                    {"id": UUID(artifact_id)},
                )
                .mappings()
                .one()
            )
            verification = (
                dict(row["verification"]) if isinstance(row.get("verification"), dict) else {}
            )
            verification["retention"] = {
                **_retention(verification),
                "state": "retired" if outcome["ok"] else "retry_required",
                "finished_at": finished_at,
                "reclaimed_physical_bytes": int(outcome.get("reclaimed_physical_bytes") or 0),
                **({"error": outcome["error"]} if not outcome["ok"] else {}),
            }
            session.execute(
                text(
                    "UPDATE digital_asset.artifacts SET state=:state,"
                    "verification=CAST(:verification AS jsonb) WHERE id=:id"
                ),
                {
                    "id": UUID(artifact_id),
                    "state": "released" if outcome["ok"] else "quarantined",
                    "verification": json.dumps(verification, default=str),
                },
            )
            if outcome["ok"]:
                _custody_event(
                    session,
                    tenant_id=credential.tenant_id,
                    asset_id=UUID(str(workspace["asset_id"])),
                    actor_user_id=actor_user_id,
                    event_type="release",
                    artifact_sha256=str(item["_sha256"]),
                    details={
                        "reason": "workspace_retention_policy",
                        "run_id": str(run_id),
                        "plan_digest": plan["plan_digest"],
                        "logical_bytes": int(item["logical_bytes"]),
                        "physical_object_deleted": bool(item["delete_physical_object"]),
                    },
                    version_id=UUID(str(item["source_version_id"])),
                    artifact_id=UUID(artifact_id),
                )
        for item in plan["expired_uploads"]:
            upload_id = str(item["upload_id"])
            outcome = upload_results[upload_id]
            if not outcome["ok"]:
                continue
            row = (
                session.execute(
                    text("SELECT result FROM digital_asset.source_upload_jobs WHERE id=:id"),
                    {"id": UUID(upload_id)},
                )
                .mappings()
                .one()
            )
            result = dict(row["result"]) if isinstance(row.get("result"), dict) else {}
            result["staging_cleaned_at"] = finished_at
            result["retention"] = {
                "state": "retired",
                "run_id": str(run_id),
                "plan_digest": plan["plan_digest"],
                "finished_at": finished_at,
                "reclaimed_bytes": int(outcome.get("reclaimed_bytes") or 0),
            }
            session.execute(
                text(
                    "UPDATE digital_asset.source_upload_jobs "
                    "SET received_bytes=0,received_parts=0,updated_at=now(),"
                    "result=CAST(:result AS jsonb) WHERE id=:id"
                ),
                {"id": UUID(upload_id), "result": json.dumps(result, default=str)},
            )
        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=credential.workspace_id,
            asset_id=workspace["asset_id"],
            refresh_infrastructure=True,
        )
        errors = [
            {"kind": kind, "id": item_id, "error": str(outcome.get("error") or "")}
            for kind, outcomes in (
                ("deployment", deployment_results),
                ("source", source_results),
                ("upload", upload_results),
            )
            for item_id, outcome in outcomes.items()
            if not bool(outcome.get("ok"))
        ]
        _audit(
            session,
            None,
            "digital_asset.workspace_retention_completed",
            {
                "workspace_id": str(credential.workspace_id),
                "run_id": str(run_id),
                "plan_digest": plan["plan_digest"],
                "errors": errors,
                "usage_after": usage,
                "credential_id": str(credential.credential_id),
            },
            tenant_id=credential.tenant_id,
        )

    return {
        "ok": not errors,
        "python_environments": plan["python_environments"],
        "schema": "warehouse.workspace-retention-result.v1",
        "run_id": str(run_id),
        "plan_digest": plan["plan_digest"],
        "status": "complete" if not errors else "partial_retry_required",
        "reclaimed": {
            "python_environment_bytes": 0,
            "runtime_bytes": sum(
                int(value.get("reclaimed_bytes") or 0) for value in deployment_results.values()
            ),
            "source_logical_bytes": sum(
                int(value.get("reclaimed_logical_bytes") or 0) for value in source_results.values()
            ),
            "source_physical_bytes": sum(
                int(value.get("reclaimed_physical_bytes") or 0) for value in source_results.values()
            ),
            "upload_staging_bytes": sum(
                int(value.get("reclaimed_bytes") or 0) for value in upload_results.values()
            ),
        },
        "counts": {
            "deployments": len(deployment_results),
            "sources": len(source_results),
            "expired_uploads": len(upload_results),
            "errors": len(errors),
        },
        "errors": errors,
        "usage_after": usage,
    }
