"""Durable, workspace-scoped release orchestration.

The release layer composes the existing deployment, lifecycle-job, acceptance,
activation, public-route verification, and rollback primitives.  It deliberately
does not duplicate those safety-critical implementations.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services.deployment_acceptance import accept_workspace_deployment
from app.services.digital_asset_hosting import WorkspaceCredential, _json_safe, _workspace_row
from app.services.workspace_deployments import (
    _hosting_manifest,
    _manifest_runtime_intent,
    _require_manifest_database_policy,
    _resolve_runtime_contract,
    _source_signals,
    _verified_source,
    activate_workspace_deployment,
    cancel_workspace_deployment,
    configure_workspace_runtime,
    observe_workspace_deployment,
    request_workspace_deployment,
    resolve_declared_workspace_job,
)

ReleaseReference = UUID | int
TERMINAL_STATES = frozenset({"verified", "failed", "rolled_back", "cancelled", "blocked"})
PASSIVE_STATES = frozenset({"awaiting_activation", *TERMINAL_STATES})


def _release_reference(value: ReleaseReference | str) -> str:
    reference = str(value).strip()
    if not reference:
        raise HTTPException(status_code=422, detail="Invalid release id")
    try:
        UUID(reference)
    except ValueError:
        if not reference.isdigit() or int(reference) < 1:
            raise HTTPException(status_code=422, detail="Invalid release id") from None
    return reference


def _request_digest(payload: dict[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _release_event(
    session: object,
    release_id: UUID,
    tenant_id: UUID,
    event_type: str,
    stage: str,
    status: str,
    payload: dict[str, object] | None = None,
) -> None:
    sequence = int(
        session.execute(
            text(
                "SELECT COALESCE(max(sequence),0)+1 FROM digital_asset.release_events "
                "WHERE release_id=:id"
            ),
            {"id": release_id},
        ).scalar_one()
    )
    session.execute(
        text(
            """
            INSERT INTO digital_asset.release_events(
              release_id,tenant_id,sequence,event_type,stage,status,payload
            ) VALUES (
              :id,:tenant_id,:sequence,:event_type,:stage,:status,CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "id": release_id,
            "tenant_id": tenant_id,
            "sequence": sequence,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "payload": json.dumps(payload or {}, ensure_ascii=False, default=str),
        },
    )


def _public_release(row: dict[str, object]) -> dict[str, object]:
    value = dict(row)
    value["uuid"] = value["id"]
    value["id"] = value["legacy_id"]
    for private in ("legacy_id", "lease_owner", "lease_expires_at", "request_payload"):
        value.pop(private, None)
    state = str(value["state"])
    value["next_action"] = {
        "planned": "resume_release",
        "candidate_requested": "wait_for_candidate",
        "candidate_ready": "resume_release",
        "jobs_running": "wait_for_lifecycle_job",
        "accepted": "resume_release",
        "awaiting_activation": "activate_release",
        "activating": "wait_for_public_verification",
        "public_verifying": "wait_for_public_verification",
        "verified": "release_complete",
        "failed": "inspect_release_events",
        "rolled_back": "inspect_release_events",
        "cancelled": "none",
        "blocked": "resolve_blocker_and_create_new_release",
    }[state]
    return _json_safe(value)


def _release_row(
    session: object,
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
    *,
    lock: bool = False,
) -> dict[str, object]:
    suffix = " FOR UPDATE" if lock else ""
    row = (
        session.execute(
            text(
                "SELECT * FROM digital_asset.release_sessions "
                "WHERE workspace_id=:workspace_id AND "
                "(CAST(id AS text)=:reference OR CAST(legacy_id AS text)=:reference)" + suffix
            ),
            {
                "workspace_id": credential.workspace_id,
                "reference": _release_reference(release_ref),
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Release not found")
    return dict(row)


def _transition(
    credential: WorkspaceCredential,
    release_id: UUID,
    expected_state: str,
    state: str,
    *,
    event_type: str,
    payload: dict[str, object] | None = None,
    values: dict[str, object] | None = None,
) -> bool:
    assignments = ["state=:state", "lease_owner=NULL", "lease_expires_at=NULL"]
    params: dict[str, object] = {
        "id": release_id,
        "workspace_id": credential.workspace_id,
        "expected_state": expected_state,
        "state": state,
    }
    for name, value in (values or {}).items():
        if name not in {
            "source_version_id",
            "component_id",
            "candidate_deployment_id",
            "current_job_deployment_id",
            "completed_jobs",
            "evidence",
            "last_error",
            "completed_at",
        }:
            raise ValueError(f"Unsupported release update field: {name}")
        assignments.append(
            f"{name}=CAST(:{name} AS jsonb)"
            if name in {"completed_jobs", "evidence", "last_error"}
            else f"{name}=:{name}"
        )
        params[name] = (
            json.dumps(value, ensure_ascii=False, default=str)
            if name in {"completed_jobs", "evidence", "last_error"}
            else value
        )
    if state in TERMINAL_STATES and "completed_at" not in (values or {}):
        assignments.append("completed_at=now()")
    with tenant_session(credential.tenant_id) as session:
        changed = session.execute(
            text(
                f"UPDATE digital_asset.release_sessions SET {', '.join(assignments)} "
                "WHERE id=:id AND workspace_id=:workspace_id AND state=:expected_state "
                "RETURNING id"
            ),
            params,
        ).scalar_one_or_none()
        if changed is None:
            return False
        _release_event(
            session,
            release_id,
            credential.tenant_id,
            event_type,
            state,
            state,
            payload,
        )
    return True


def _required_jobs(manifest: dict[str, object] | None) -> list[dict[str, object]]:
    lifecycle = manifest.get("lifecycle") if isinstance(manifest, dict) else {}
    lifecycle = lifecycle if isinstance(lifecycle, dict) else {}
    jobs = lifecycle.get("jobs") if isinstance(lifecycle.get("jobs"), list) else []
    return [
        dict(job)
        for job in jobs
        if isinstance(job, dict) and bool(job.get("required_before_activation"))
    ]


def _static_blockers(
    family: str,
    manifest: dict[str, object] | None,
    jobs: list[dict[str, object]],
) -> list[dict[str, object]]:
    if family != "static" or manifest is None:
        return []
    blockers: list[dict[str, object]] = []
    data = manifest.get("data") if isinstance(manifest.get("data"), dict) else {}
    database_jobs = [
        str(job.get("name")) for job in jobs if str(job.get("database_access") or "none") != "none"
    ]
    if database_jobs:
        blockers.append(
            {
                "code": "static_requires_database_lifecycle_job",
                "field": "lifecycle.jobs",
                "jobs": database_jobs,
                "message": "Static delivery cannot run required database lifecycle jobs.",
            }
        )
    runtime_envs = [
        name
        for name in ("runtime_database_url_env", "migration_database_url_env", "database_url_env")
        if data.get(name) not in (None, "")
    ]
    if runtime_envs:
        blockers.append(
            {
                "code": "static_requests_runtime_database_environment",
                "field": "data",
                "environment_fields": runtime_envs,
                "message": "Static delivery has no server process for database URL injection.",
            }
        )
    acceptance = manifest.get("acceptance")
    acceptance = acceptance if isinstance(acceptance, dict) else {}
    probes = acceptance.get("http") if isinstance(acceptance.get("http"), list) else []
    api_paths = [
        str(probe.get("path"))
        for probe in probes
        if isinstance(probe, dict) and str(probe.get("path") or "").startswith("/api/")
    ]
    if api_paths:
        blockers.append(
            {
                "code": "static_declares_runtime_api_acceptance",
                "field": "acceptance.http",
                "paths": api_paths,
                "message": "Static delivery cannot satisfy backend API acceptance routes.",
            }
        )
    return blockers


def plan_workspace_release(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Return an authoritative, side-effect-free plan for one verified source."""

    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=False)
        source = _verified_source(session, workspace, payload.get("source_version_id"))
        if source is None:
            raise HTTPException(status_code=409, detail="A verified source version is required")
        signals = _source_signals(source, settings)
        manifest = _hosting_manifest(signals)
        _require_manifest_database_policy(workspace, manifest)
        effective = _manifest_runtime_intent({**payload, "activate": False}, signals)
        runtime_type, profile = _resolve_runtime_contract(session, effective, signals)
        previous_deployment_id = workspace.get("active_deployment_id")
    family = str(profile["runtime_family"])
    jobs = _required_jobs(manifest)
    blockers = _static_blockers(family, manifest, jobs)
    required_scopes = ["deploy:read", "deploy:write"]
    if any(str(job.get("database_access") or "none") != "none" for job in jobs):
        required_scopes.append("database:admin")
    missing_scopes = sorted(set(required_scopes) - credential.scopes)
    if missing_scopes:
        blockers.append(
            {
                "code": "workspace_key_missing_scopes",
                "scopes": missing_scopes,
                "message": "The current workspace key cannot execute this release plan.",
            }
        )
    kind = (
        "frontend"
        if runtime_type == "static" or (runtime_type == "web" and family == "static")
        else "worker"
        if runtime_type in {"worker", "job"}
        else "agent"
        if (runtime_type == "agent")
        else "backend"
    )
    default_component = {
        "frontend": "frontend",
        "backend": "api",
        "worker": "job" if runtime_type == "job" else "worker",
        "agent": "agent",
    }[kind]
    component = str(payload.get("component") or default_component).strip()
    manifest_digest = str(manifest.get("contract_digest")) if manifest else None
    steps: list[dict[str, object]] = [
        {"name": "candidate", "action": "build_without_activation", "required": True}
    ]
    steps.extend(
        {
            "name": f"lifecycle:{job['name']}",
            "action": "run_declared_job",
            "database_access": job.get("database_access", "none"),
            "required": True,
        }
        for job in jobs
    )
    steps.extend(
        [
            {"name": "acceptance", "action": "probe_immutable_candidate", "required": True},
            {"name": "activation", "action": "await_explicit_request", "required": True},
            {
                "name": "public_route",
                "action": "verify_exact_revision_or_rollback",
                "required": True,
            },
        ]
    )
    plan = {
        "source_version_id": str(source["id"]),
        "source_sha256": str(source.get("sha256") or ""),
        "manifest_schema": manifest.get("schema") if manifest else None,
        "manifest_digest": manifest_digest,
        "runtime_type": runtime_type,
        "runtime_family": family,
        "runtime_profile": profile["profile_key"],
        "delivery_mode": "static" if family == "static" else "runtime",
        "component": component,
        "required_jobs": jobs,
        "required_scopes": required_scopes,
        "previous_deployment_id": (
            str(previous_deployment_id) if previous_deployment_id is not None else None
        ),
        "steps": steps,
        "blockers": blockers,
        "ready": not blockers,
    }
    return {"ok": not blockers, "plan": _json_safe(plan)}


def create_workspace_release(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
    *,
    idempotency_key: str | None,
) -> dict[str, object]:
    credential.require("deploy:write")
    key = str(idempotency_key or payload.get("idempotency_key") or "").strip()
    if not key:
        raise HTTPException(status_code=422, detail="Idempotency-Key is required")
    if len(key) > 200:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long")
    planned = plan_workspace_release(credential, payload, settings)["plan"]
    blockers = planned.get("blockers") if isinstance(planned, dict) else []
    if blockers:
        raise HTTPException(
            status_code=409,
            detail={"reason": "release_plan_blocked", "blockers": blockers, "plan": planned},
        )
    normalized_payload = {
        **{key: value for key, value in payload.items() if key != "idempotency_key"},
        "source_version_id": planned["source_version_id"],
        "component": planned["component"],
        "runtime_profile": planned["runtime_profile"],
        "activate": False,
    }
    digest = _request_digest(normalized_payload)
    release_id = uuid4()
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        replay = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.release_sessions "
                    "WHERE workspace_id=:workspace_id AND idempotency_key=:key"
                ),
                {"workspace_id": credential.workspace_id, "key": key},
            )
            .mappings()
            .one_or_none()
        )
        if replay is not None:
            if str(replay["request_digest"]) != digest:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key was already used for a different release request",
                )
            result = _public_release(dict(replay))
            result["idempotent_replay"] = True
            return {"ok": True, "release": result}
        requested_by = session.execute(
            text("SELECT issued_by FROM digital_asset.api_credentials WHERE id=:id"),
            {"id": credential.credential_id},
        ).scalar_one_or_none()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.release_sessions(
                      id,tenant_id,workspace_id,source_version_id,previous_deployment_id,
                      requested_credential_id,requested_by,idempotency_key,request_digest,
                      manifest_digest,delivery_mode,runtime_type,state,request_payload,
                      release_plan,required_jobs
                    ) VALUES (
                      :id,:tenant_id,:workspace_id,:source_version_id,:previous_deployment_id,
                      :credential_id,:requested_by,:idempotency_key,:request_digest,
                      :manifest_digest,:delivery_mode,:runtime_type,'planned',
                      CAST(:request_payload AS jsonb),CAST(:release_plan AS jsonb),
                      CAST(:required_jobs AS jsonb)
                    ) RETURNING *
                    """
                ),
                {
                    "id": release_id,
                    "tenant_id": credential.tenant_id,
                    "workspace_id": credential.workspace_id,
                    "source_version_id": UUID(str(planned["source_version_id"])),
                    "previous_deployment_id": workspace.get("active_deployment_id"),
                    "credential_id": credential.credential_id,
                    "requested_by": requested_by,
                    "idempotency_key": key,
                    "request_digest": digest,
                    "manifest_digest": planned.get("manifest_digest"),
                    "delivery_mode": planned["delivery_mode"],
                    "runtime_type": planned["runtime_type"],
                    "request_payload": json.dumps(normalized_payload, ensure_ascii=False),
                    "release_plan": json.dumps(planned, ensure_ascii=False),
                    "required_jobs": json.dumps(planned["required_jobs"], ensure_ascii=False),
                },
            )
            .mappings()
            .one()
        )
        _release_event(
            session,
            release_id,
            credential.tenant_id,
            "release_created",
            "planned",
            "planned",
            {"credential_id": str(credential.credential_id), "request_digest": digest},
        )
    return {"ok": True, "release": _public_release(dict(row))}


def observe_workspace_release(
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
    *,
    include_events: bool = True,
) -> dict[str, object]:
    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        row = _release_row(session, credential, release_ref)
        events = []
        if include_events:
            events = [
                _json_safe(dict(event))
                for event in session.execute(
                    text(
                        "SELECT sequence,event_type,stage,status,payload,created_at "
                        "FROM digital_asset.release_events "
                        "WHERE release_id=:id ORDER BY sequence"
                    ),
                    {"id": row["id"]},
                )
                .mappings()
                .all()
            ]
    return {"ok": True, "release": _public_release(row), "events": events}


def list_workspace_releases(
    credential: WorkspaceCredential,
    *,
    limit: int = 50,
) -> dict[str, object]:
    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        _workspace_row(session, credential.workspace_id)
        rows = session.execute(
            text(
                "SELECT * FROM digital_asset.release_sessions "
                "WHERE workspace_id=:workspace_id ORDER BY created_at DESC LIMIT :limit"
            ),
            {"workspace_id": credential.workspace_id, "limit": limit},
        ).mappings()
    releases = [_public_release(dict(row)) for row in rows]
    return {"ok": True, "releases": releases, "count": len(releases)}


def _request_candidate(
    credential: WorkspaceCredential,
    row: dict[str, object],
    settings: Settings,
) -> bool:
    request = dict(row.get("request_payload") or {})
    configured = configure_workspace_runtime(
        credential,
        {**request, "deploy": False, "activate": False},
        settings,
    )
    component = configured["component"]
    runtime = configured["runtime"]
    deployment_payload = {
        **request,
        "source_version_id": configured["source_version_id"],
        "component": component["component_name"],
        "runtime_profile": runtime["runtime_profile"],
        "entrypoint": request.get("entrypoint") or component.get("entrypoint"),
        "build_command": request.get("build_command") or component.get("build_command"),
        "start_command": request.get("start_command") or component.get("start_command"),
        "activate": False,
    }
    requested = request_workspace_deployment(
        credential,
        deployment_payload,
        idempotency_key=f"release:{row['id']}:candidate",
        settings=settings,
    )["deployment"]
    candidate_id = UUID(str(requested["uuid"]))
    return _transition(
        credential,
        UUID(str(row["id"])),
        "planned",
        "candidate_requested",
        event_type="candidate_requested",
        payload={"deployment_id": str(candidate_id)},
        values={
            "source_version_id": UUID(str(configured["source_version_id"])),
            "component_id": UUID(str(component["id"])),
            "candidate_deployment_id": candidate_id,
        },
    )


def _observe_candidate(credential: WorkspaceCredential, row: dict[str, object]) -> bool:
    candidate_id = row.get("candidate_deployment_id")
    if candidate_id is None:
        return _transition(
            credential,
            UUID(str(row["id"])),
            "candidate_requested",
            "failed",
            event_type="release_failed",
            payload={"reason": "candidate_reference_missing"},
            values={"last_error": {"reason": "candidate_reference_missing"}},
        )
    deployment = observe_workspace_deployment(
        credential, UUID(str(candidate_id)), include_events=False
    )["deployment"]
    status = str(deployment["status"])
    if status == "ready" and deployment.get("health") == "healthy":
        return _transition(
            credential,
            UUID(str(row["id"])),
            "candidate_requested",
            "candidate_ready",
            event_type="candidate_ready",
            payload={"deployment_id": str(candidate_id)},
        )
    if status in {"failed", "cancelled", "rolled_back"}:
        error = {"reason": "candidate_failed", "deployment": deployment}
        return _transition(
            credential,
            UUID(str(row["id"])),
            "candidate_requested",
            "failed",
            event_type="release_failed",
            payload={"reason": "candidate_failed", "deployment_id": str(candidate_id)},
            values={"last_error": error},
        )
    return False


def _candidate_ready(
    credential: WorkspaceCredential,
    row: dict[str, object],
    settings: Settings,
) -> bool:
    jobs = list(row.get("required_jobs") or [])
    completed = list(row.get("completed_jobs") or [])
    if len(completed) < len(jobs):
        job = jobs[len(completed)]
        name = str(job["name"])
        resolved = resolve_declared_workspace_job(
            credential,
            {"source_version_id": str(row["source_version_id"]), "job": name},
            settings,
        )
        configured = configure_workspace_runtime(
            credential, {**resolved, "deploy": False, "activate": False}, settings
        )
        component = configured["component"]
        requested = request_workspace_deployment(
            credential,
            {
                **resolved,
                "component": component["component_name"],
                "runtime_profile": configured["runtime"]["runtime_profile"],
                "activate": False,
            },
            idempotency_key=f"release:{row['id']}:job:{name}",
            settings=settings,
        )["deployment"]
        job_id = UUID(str(requested["uuid"]))
        return _transition(
            credential,
            UUID(str(row["id"])),
            "candidate_ready",
            "jobs_running",
            event_type="lifecycle_job_requested",
            payload={"job": name, "deployment_id": str(job_id)},
            values={"current_job_deployment_id": job_id},
        )
    accepted = accept_workspace_deployment(
        credential, UUID(str(row["candidate_deployment_id"])), settings
    )
    if not bool(accepted.get("accepted")):
        error = {"reason": "candidate_acceptance_failed", "acceptance": accepted}
        return _transition(
            credential,
            UUID(str(row["id"])),
            "candidate_ready",
            "failed",
            event_type="acceptance_failed",
            payload={"failures": (accepted.get("evidence") or {}).get("failures", [])},
            values={"last_error": error, "evidence": {"acceptance": accepted}},
        )
    return _transition(
        credential,
        UUID(str(row["id"])),
        "candidate_ready",
        "accepted",
        event_type="candidate_accepted",
        payload={"deployment_id": str(row["candidate_deployment_id"])},
        values={"evidence": {"acceptance": accepted}},
    )


def _observe_job(credential: WorkspaceCredential, row: dict[str, object]) -> bool:
    job_id = row.get("current_job_deployment_id")
    if job_id is None:
        error = {"reason": "lifecycle_job_reference_missing"}
        return _transition(
            credential,
            UUID(str(row["id"])),
            "jobs_running",
            "failed",
            event_type="release_failed",
            payload=error,
            values={"last_error": error},
        )
    deployment = observe_workspace_deployment(credential, UUID(str(job_id)), include_events=False)[
        "deployment"
    ]
    status = str(deployment["status"])
    if status == "ready" and deployment.get("health") == "healthy":
        completed = list(row.get("completed_jobs") or [])
        jobs = list(row.get("required_jobs") or [])
        job = jobs[len(completed)]
        completed.append(
            {
                "name": job["name"],
                "deployment_id": str(job_id),
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        return _transition(
            credential,
            UUID(str(row["id"])),
            "jobs_running",
            "candidate_ready",
            event_type="lifecycle_job_succeeded",
            payload={"job": job["name"], "deployment_id": str(job_id)},
            values={"completed_jobs": completed, "current_job_deployment_id": None},
        )
    if status in {"failed", "cancelled", "rolled_back"}:
        error = {"reason": "lifecycle_job_failed", "deployment": deployment}
        return _transition(
            credential,
            UUID(str(row["id"])),
            "jobs_running",
            "failed",
            event_type="lifecycle_job_failed",
            payload={"deployment_id": str(job_id)},
            values={"last_error": error},
        )
    return False


def resume_workspace_release(
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
    settings: Settings,
    *,
    max_transitions: int = 8,
) -> dict[str, object]:
    credential.require("deploy:write")
    for _ in range(max(1, min(max_transitions, 16))):
        with tenant_session(credential.tenant_id) as session:
            row = _release_row(session, credential, release_ref)
        state = str(row["state"])
        if state in PASSIVE_STATES:
            break
        changed = (
            _request_candidate(credential, row, settings)
            if state == "planned"
            else _observe_candidate(credential, row)
            if state == "candidate_requested"
            else _candidate_ready(credential, row, settings)
            if state == "candidate_ready"
            else _observe_job(credential, row)
            if state == "jobs_running"
            else _transition(
                credential,
                UUID(str(row["id"])),
                "accepted",
                "awaiting_activation",
                event_type="activation_required",
                payload={"manual_activation": True},
            )
            if state == "accepted"
            else False
        )
        if not changed:
            break
    return observe_workspace_release(credential, release_ref)


def activate_workspace_release(
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        row = _release_row(session, credential, release_ref)
    if row["state"] == "verified":
        return observe_workspace_release(credential, release_ref)
    if row["state"] != "awaiting_activation":
        raise HTTPException(
            status_code=409,
            detail=f"Release cannot be activated from {row['state']}",
        )
    release_id = UUID(str(row["id"]))
    if not _transition(
        credential,
        release_id,
        "awaiting_activation",
        "activating",
        event_type="activation_started",
        payload={"deployment_id": str(row["candidate_deployment_id"])},
    ):
        return observe_workspace_release(credential, release_ref)
    if not _transition(
        credential,
        release_id,
        "activating",
        "public_verifying",
        event_type="public_route_verification_started",
        payload={"deployment_id": str(row["candidate_deployment_id"])},
    ):
        return observe_workspace_release(credential, release_ref)
    try:
        activated = activate_workspace_deployment(
            credential, UUID(str(row["candidate_deployment_id"]))
        )
    except HTTPException as exc:
        detail = exc.detail if isinstance(exc.detail, dict) else {"message": str(exc.detail)}
        rolled_back = bool(detail.get("previous_deployment_restored"))
        _transition(
            credential,
            release_id,
            "public_verifying",
            "rolled_back" if rolled_back else "failed",
            event_type="activation_rolled_back" if rolled_back else "activation_failed",
            payload=detail,
            values={"last_error": detail},
        )
        raise
    _transition(
        credential,
        release_id,
        "public_verifying",
        "verified",
        event_type="public_route_verified",
        payload={"deployment_id": str(row["candidate_deployment_id"])},
        values={"evidence": {**dict(row.get("evidence") or {}), "activation": activated}},
    )
    return observe_workspace_release(credential, release_ref)


def cancel_workspace_release(
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        row = _release_row(session, credential, release_ref)
    if str(row["state"]) in TERMINAL_STATES:
        return observe_workspace_release(credential, release_ref)
    for deployment_id in (
        row.get("current_job_deployment_id"),
        row.get("candidate_deployment_id"),
    ):
        if deployment_id is None:
            continue
        try:
            cancel_workspace_deployment(credential, UUID(str(deployment_id)))
        except HTTPException as exc:
            if exc.status_code != 409:
                raise
    _transition(
        credential,
        UUID(str(row["id"])),
        str(row["state"]),
        "cancelled",
        event_type="release_cancelled",
        payload={"credential_id": str(credential.credential_id)},
    )
    return observe_workspace_release(credential, release_ref)


def rollback_workspace_release(
    credential: WorkspaceCredential,
    release_ref: ReleaseReference | str,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        row = _release_row(session, credential, release_ref)
    previous = row.get("previous_deployment_id")
    if previous is None:
        raise HTTPException(status_code=409, detail="Release has no previous deployment")
    if str(row["state"]) not in {"verified", "failed", "rolled_back"}:
        raise HTTPException(
            status_code=409,
            detail=f"Release cannot be rolled back from {row['state']}",
        )
    activated = activate_workspace_deployment(credential, UUID(str(previous)))
    with tenant_session(credential.tenant_id) as session:
        current = _release_row(session, credential, release_ref, lock=True)
        session.execute(
            text(
                "UPDATE digital_asset.release_sessions SET state='rolled_back',"
                "completed_at=now(),evidence=evidence || CAST(:evidence AS jsonb) WHERE id=:id"
            ),
            {
                "id": current["id"],
                "evidence": json.dumps({"rollback": activated}, default=str),
            },
        )
        _release_event(
            session,
            UUID(str(current["id"])),
            credential.tenant_id,
            "release_rolled_back",
            "rolled_back",
            "rolled_back",
            {"deployment_id": str(previous)},
        )
    return observe_workspace_release(credential, release_ref)


def _credential_for_release(tenant_id: UUID, release_id: UUID) -> WorkspaceCredential | None:
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT r.workspace_id,c.id,c.scopes,c.label,c.key_kind,c.parent_credential_id
                    FROM digital_asset.release_sessions AS r
                    JOIN digital_asset.api_credentials AS c
                      ON c.tenant_id=r.tenant_id AND c.id=r.requested_credential_id
                    WHERE r.id=:release_id AND c.revoked_at IS NULL
                      AND (c.expires_at IS NULL OR c.expires_at > now())
                    """
                ),
                {"release_id": release_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        return None
    return WorkspaceCredential(
        tenant_id=tenant_id,
        workspace_id=UUID(str(row["workspace_id"])),
        credential_id=UUID(str(row["id"])),
        scopes=frozenset(str(scope) for scope in row["scopes"]),
        label=str(row["label"]),
        key_kind=str(row["key_kind"]),
        parent_credential_id=(
            UUID(str(row["parent_credential_id"]))
            if row["parent_credential_id"] is not None
            else None
        ),
    )


def reconcile_pending_releases(
    settings: Settings,
    *,
    worker_id: str,
    limit: int = 1,
) -> int:
    """Advance resumable sessions without trusting a disconnected client."""

    with system_session() as session:
        tenants = [
            UUID(str(value))
            for value in session.execute(
                text("SELECT id FROM iam.tenants WHERE status='active' ORDER BY id")
            ).scalars()
        ]
    changed = 0
    for tenant_id in tenants:
        if changed >= max(1, limit):
            break
        with tenant_session(tenant_id) as session:
            expires = datetime.now(UTC) + timedelta(
                seconds=max(30, settings.runtime_controller_lease_seconds)
            )
            release_id = session.execute(
                text(
                    """
                    SELECT id FROM digital_asset.release_sessions
                    WHERE state NOT IN (
                      'awaiting_activation','verified','failed','rolled_back','cancelled','blocked'
                    ) AND (lease_expires_at IS NULL OR lease_expires_at < now())
                    ORDER BY updated_at,id FOR UPDATE SKIP LOCKED LIMIT 1
                    """
                )
            ).scalar_one_or_none()
            if release_id is None:
                continue
            release_id = UUID(str(release_id))
            session.execute(
                text(
                    "UPDATE digital_asset.release_sessions SET lease_owner=:worker,"
                    "lease_expires_at=:expires,attempt_count=attempt_count+1 WHERE id=:id"
                ),
                {"worker": worker_id, "expires": expires, "id": release_id},
            )
        credential = _credential_for_release(tenant_id, release_id)
        if credential is None:
            with tenant_session(tenant_id) as session:
                row = (
                    session.execute(
                        text(
                            "SELECT workspace_id,state FROM "
                            "digital_asset.release_sessions WHERE id=:id"
                        ),
                        {"id": release_id},
                    )
                    .mappings()
                    .one()
                )
            placeholder = WorkspaceCredential(
                tenant_id=tenant_id,
                workspace_id=UUID(str(row["workspace_id"])),
                credential_id=UUID(int=0),
                scopes=frozenset(),
                label="revoked-release-credential",
                key_kind="delegated",
                parent_credential_id=None,
            )
            _transition(
                placeholder,
                release_id,
                str(row["state"]),
                "blocked",
                event_type="release_blocked",
                payload={"reason": "requested_credential_inactive"},
                values={"last_error": {"reason": "requested_credential_inactive"}},
            )
            changed += 1
            continue
        before = observe_workspace_release(credential, release_id, include_events=False)["release"]
        try:
            after = resume_workspace_release(credential, release_id, settings, max_transitions=1)[
                "release"
            ]
        finally:
            with tenant_session(tenant_id) as session:
                session.execute(
                    text(
                        "UPDATE digital_asset.release_sessions SET lease_owner=NULL,"
                        "lease_expires_at=NULL WHERE id=:id AND lease_owner=:worker"
                    ),
                    {"id": release_id, "worker": worker_id},
                )
        if after["state"] != before["state"]:
            changed += 1
    return changed
