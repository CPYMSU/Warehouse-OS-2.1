"""User-selectable cloud/terminal hosting controls.

This module deliberately keeps the first dual-hosting slice small:

* ``cloud`` preserves the existing Warehouse/Vultr/Mac mini Runtime path.
* ``terminal`` records a signed, observable hand-off to a user's terminal or
  AI instead of silently starting a server Runtime.
* Notifications are pollable by both account sessions and workspace-key based
  terminal AIs.
* Compute usage is an append-only ledger, separate from storage hosting usage,
  so future cloud-compute pricing can be added without changing the hosting
  contract.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    _audit,
    _json_safe,
    _public_deployment,
    _public_workspace,
    _require_manage,
    _require_read,
    _workspace_row,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


HOSTING_MODES = frozenset({"cloud", "terminal"})
CLOUD_COMPUTE_NODES = frozenset({"warehouse", "vultr", "mac_mini"})
COMPUTE_NODES = CLOUD_COMPUTE_NODES | {"user_terminal"}
NOTIFICATION_TARGETS = frozenset({"terminal", "ai"})
NOTIFICATION_STATUSES = frozenset({"pending", "acknowledged", "expired", "cancelled"})
HOSTING_EVENT_TYPES = frozenset(
    {
        "terminal_registration_required",
        "terminal_action_required",
        "terminal_connected",
        "terminal_succeeded",
        "terminal_failed",
        "cloud_compute_started",
        "cloud_compute_metered",
        "cloud_compute_finished",
    }
)
TERMINAL_WORKSPACE_RUNTIME_STATUS = "provisioned"


def _safe(value: object) -> object:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    return _json_safe(value)


def _terminal_workspace_state(
    deployment_id: UUID,
    successful: bool,
    *,
    completed_at: datetime | None = None,
) -> dict[str, object]:
    """Return workspace state for a terminal result.

    ``workspaces.runtime_status`` describes the Warehouse server Runtime, so a
    terminal result must never set it to ``ready`` (or ``failed``) as if a
    server container had been health-checked.  Keep the terminal outcome in
    the workspace config for UI/AI inspection and leave the server status at
    the provisioned control-plane state.
    """

    return {
        "runtime_status": TERMINAL_WORKSPACE_RUNTIME_STATUS,
        "config": {
            "terminal_last_deployment_id": str(deployment_id),
            "terminal_last_status": "succeeded" if successful else "failed",
            "terminal_last_completed_at": (completed_at or datetime.now(UTC)).isoformat(),
        },
    }


def _parse_targets(value: object, *, default: Iterable[str]) -> list[str]:
    if value is None:
        candidates = list(default)
    elif isinstance(value, str):
        candidates = [item.strip().lower() for item in value.split(",")]
    elif isinstance(value, list):
        candidates = [str(item).strip().lower() for item in value]
    else:
        raise HTTPException(status_code=422, detail="notify_targets must be an array or string")
    targets = list(dict.fromkeys(item for item in candidates if item))
    invalid = sorted(set(targets) - NOTIFICATION_TARGETS)
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_notification_target", "invalid": invalid},
        )
    if not targets:
        raise HTTPException(status_code=422, detail="notify_targets cannot be empty")
    return targets


def _hosting_settings(
    payload: Mapping[str, object], workspace: Mapping[str, object]
) -> dict[str, object]:
    current_config = workspace.get("config") if isinstance(workspace.get("config"), dict) else {}
    current_mode = str(workspace.get("hosting_mode") or "cloud").lower()
    mode = str(payload.get("mode") or payload.get("hosting_mode") or current_mode).strip().lower()
    if mode not in HOSTING_MODES:
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_hosting_mode", "accepted": sorted(HOSTING_MODES)},
        )
    current_node = str(workspace.get("compute_node") or "warehouse").lower()
    default_node = (
        "user_terminal"
        if mode == "terminal"
        else (current_node if current_node in CLOUD_COMPUTE_NODES else "warehouse")
    )
    node = str(payload.get("compute_node") or payload.get("node") or default_node).strip().lower()
    if node not in COMPUTE_NODES:
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_compute_node", "accepted": sorted(COMPUTE_NODES)},
        )
    if mode == "terminal" and node != "user_terminal":
        raise HTTPException(
            status_code=422,
            detail="terminal hosting must use compute_node=user_terminal",
        )
    if mode == "cloud" and node == "user_terminal":
        raise HTTPException(
            status_code=422,
            detail="cloud hosting must use a Warehouse, Vultr or Mac mini compute node",
        )
    old_targets = current_config.get("notify_targets")
    targets = _parse_targets(
        payload.get("notify_targets"),
        default=old_targets if old_targets is not None else ("terminal", "ai"),
    )
    fallback = (
        str(payload.get("cloud_fallback") or current_config.get("cloud_fallback") or "ask")
        .strip()
        .lower()
    )
    if fallback not in {"ask", "never"}:
        raise HTTPException(status_code=422, detail="cloud_fallback must be ask or never")
    budget = payload.get("compute_budget")
    if budget is None:
        budget = current_config.get("compute_budget") or {}
    if not isinstance(budget, dict):
        raise HTTPException(status_code=422, detail="compute_budget must be an object")
    clean_budget: dict[str, object] = {}
    for key in ("max_memory_mb", "max_minutes", "max_cpu_seconds", "max_cost_cny"):
        if key not in budget or budget[key] in (None, ""):
            continue
        try:
            numeric = float(budget[key])
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail=f"compute_budget.{key} must be numeric"
            ) from exc
        if not math.isfinite(numeric) or numeric < 0:
            raise HTTPException(
                status_code=422, detail=f"compute_budget.{key} must be non-negative"
            )
        clean_budget[key] = numeric
    return {
        "hosting_mode": mode,
        "compute_node": node,
        "notify_targets": targets,
        "cloud_fallback": fallback,
        "compute_budget": clean_budget,
    }


def hosting_public(workspace: Mapping[str, object]) -> dict[str, object]:
    config = workspace.get("config") if isinstance(workspace.get("config"), dict) else {}
    stored_budget = config.get("compute_budget")
    if not isinstance(stored_budget, dict):
        stored_budget = {}
    settings = _hosting_settings(
        {
            "mode": workspace.get("hosting_mode") or "cloud",
            "compute_node": workspace.get("compute_node") or "warehouse",
            "notify_targets": config.get("notify_targets") or ["terminal", "ai"],
            "cloud_fallback": config.get("cloud_fallback") or "ask",
            "compute_budget": stored_budget,
        },
        workspace,
    )
    return {
        "mode": settings["hosting_mode"],
        "compute_node": settings["compute_node"],
        "notify_targets": settings["notify_targets"],
        "cloud_fallback": settings["cloud_fallback"],
        "compute_budget": settings["compute_budget"],
        "cloud_compute_billable": settings["compute_node"] in CLOUD_COMPUTE_NODES,
    }


def insert_hosting_notifications(
    session: Session,
    workspace: Mapping[str, object],
    *,
    event_type: str,
    message: str,
    payload: Mapping[str, object] | None = None,
    targets: Iterable[str] | None = None,
    created_by: UUID | None = None,
    deployment_id: UUID | None = None,
) -> list[dict[str, object]]:
    if event_type not in HOSTING_EVENT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported hosting notification event_type")
    clean_message = str(message or "").strip()
    if not clean_message:
        raise HTTPException(status_code=422, detail="Notification message is required")
    selected_targets = _parse_targets(
        list(targets) if targets is not None else None,
        default=("terminal", "ai"),
    )
    rows: list[dict[str, object]] = []
    for target in selected_targets:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.hosting_notifications(
                      id, tenant_id, workspace_id, asset_id, target,
                      event_type, message, payload, deployment_id, created_by
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :asset_id, :target,
                      :event_type, :message, CAST(:payload AS jsonb),
                      :deployment_id, :created_by
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": workspace["tenant_id"],
                    "workspace_id": workspace["id"],
                    "asset_id": workspace["asset_id"],
                    "target": target,
                    "event_type": event_type,
                    "message": clean_message[:2000],
                    "payload": json.dumps(dict(payload or {}), ensure_ascii=False, default=str),
                    "deployment_id": deployment_id,
                    "created_by": created_by,
                },
            )
            .mappings()
            .one()
        )
        rows.append(_safe(dict(row)))
    return rows


def _set_hosting_mode(
    tenant_id: UUID,
    workspace_ref: object,
    payload: dict[str, object],
    *,
    actor: ActorContext | None,
    credential: WorkspaceCredential | None,
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        if credential is not None and workspace["id"] != credential.workspace_id:
            raise HTTPException(
                status_code=403, detail="Workspace key cannot access another workspace"
            )
        settings = _hosting_settings(payload, workspace)
        current_mode = str(workspace.get("hosting_mode") or "cloud")
        config = dict(workspace.get("config") or {})
        config.update(
            {
                "notify_targets": settings["notify_targets"],
                "cloud_fallback": settings["cloud_fallback"],
                "compute_budget": settings["compute_budget"],
            }
        )
        row = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces
                    SET hosting_mode=:hosting_mode,
                        compute_node=:compute_node,
                        config=CAST(:config AS jsonb),
                        revision=revision+1
                    WHERE id=:workspace_id
                    RETURNING *
                    """
                ),
                {
                    "hosting_mode": settings["hosting_mode"],
                    "compute_node": settings["compute_node"],
                    "config": json.dumps(config, ensure_ascii=False, default=str),
                    "workspace_id": workspace["id"],
                },
            )
            .mappings()
            .one()
        )
        notifications: list[dict[str, object]] = []
        if settings["hosting_mode"] == "terminal" and current_mode != "terminal":
            notifications = insert_hosting_notifications(
                session,
                row,
                event_type="terminal_registration_required",
                message=(
                    "This asset now uses terminal hosting. Connect an approved user terminal "
                    "or AI before requesting execution."
                ),
                payload={
                    "hosting_mode": "terminal",
                    "compute_node": "user_terminal",
                    "cloud_fallback": settings["cloud_fallback"],
                },
                targets=settings["notify_targets"],
                created_by=actor.user_id if actor is not None else None,
            )
        _audit(
            session,
            actor,
            "digital_asset.workspace_hosting_mode_changed",
            {
                "workspace_id": str(row["id"]),
                "asset_id": str(row["asset_id"]),
                "from": current_mode,
                "to": settings["hosting_mode"],
                "compute_node": settings["compute_node"],
                "credential_id": str(credential.credential_id) if credential else None,
            },
            tenant_id=tenant_id if actor is None else None,
        )
    return {
        "ok": True,
        "workspace": _public_workspace(dict(row)),
        "hosting": hosting_public(row),
        "notifications": notifications,
        "next_action": (
            "connect_terminal" if settings["hosting_mode"] == "terminal" else "cloud_deploy"
        ),
    }


def set_hosting_mode(
    actor: ActorContext, workspace_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    return _set_hosting_mode(actor.tenant_id, workspace_ref, payload, actor=actor, credential=None)


def set_hosting_mode_for_credential(
    credential: WorkspaceCredential, payload: dict[str, object]
) -> dict[str, object]:
    credential.require("deploy:write")
    return _set_hosting_mode(
        credential.tenant_id,
        credential.workspace_id,
        payload,
        actor=None,
        credential=credential,
    )


def get_hosting_mode(actor: ActorContext, workspace_ref: object) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
    return {
        "ok": True,
        "workspace": _public_workspace(workspace, actor.tenant_slug),
        "hosting": hosting_public(workspace),
    }


def get_hosting_mode_for_credential(credential: WorkspaceCredential) -> dict[str, object]:
    credential.require("workspace:read")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
    return {
        "ok": True,
        "workspace": _public_workspace(workspace),
        "hosting": hosting_public(workspace),
    }


def create_hosting_notification(
    actor: ActorContext, workspace_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    event_type = str(payload.get("event_type") or "terminal_action_required").strip().lower()
    message = str(payload.get("message") or "").strip()
    targets = _parse_targets(
        payload.get("targets") or payload.get("target"), default=("terminal", "ai")
    )
    body = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        notifications = insert_hosting_notifications(
            session,
            workspace,
            event_type=event_type,
            message=message,
            payload=body,
            targets=targets,
            created_by=actor.user_id,
        )
    return {"ok": True, "notifications": notifications, "count": len(notifications)}


def list_hosting_notifications(
    tenant_id: UUID,
    workspace_ref: object,
    *,
    target: str | None = None,
    notification_status: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    if target not in (None, "") and target not in NOTIFICATION_TARGETS:
        raise HTTPException(status_code=422, detail="target must be terminal or ai")
    if notification_status not in (None, "") and notification_status not in NOTIFICATION_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid notification status")
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        rows = [
            _safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.hosting_notifications
                    WHERE workspace_id=:workspace_id
                      AND (:target IS NULL OR target=:target)
                      AND (:status IS NULL OR status=:status)
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "workspace_id": workspace["id"],
                    "target": target or None,
                    "status": notification_status or None,
                    "limit": max(1, min(int(limit), 500)),
                },
            )
            .mappings()
            .all()
        ]
    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "notifications": rows,
        "count": len(rows),
    }


def list_hosting_notifications_for_credential(
    credential: WorkspaceCredential,
    *,
    target: str | None = None,
    notification_status: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    credential.require("workspace:read")
    return list_hosting_notifications(
        credential.tenant_id,
        credential.workspace_id,
        target=target,
        notification_status=notification_status,
        limit=limit,
    )


def acknowledge_hosting_notification(
    tenant_id: UUID,
    workspace_ref: object,
    notification_ref: object,
    *,
    actor_user_id: UUID | None = None,
) -> dict[str, object]:
    try:
        notification_id = UUID(str(notification_ref))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid notification id") from exc
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        row = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.hosting_notifications
                    SET status='acknowledged',
                        delivered_at=COALESCE(delivered_at, now()),
                        acknowledged_at=now()
                    WHERE id=:id AND workspace_id=:workspace_id
                    RETURNING *
                    """
                ),
                {"id": notification_id, "workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Hosting notification not found")
        if actor_user_id is not None:
            _audit(
                session,
                None,
                "digital_asset.hosting_notification_acknowledged",
                {
                    "notification_id": str(notification_id),
                    "workspace_id": str(workspace["id"]),
                    "actor_user_id": str(actor_user_id),
                },
                tenant_id=tenant_id,
            )
    return {"ok": True, "notification": _safe(dict(row))}


def record_compute_usage(
    tenant_id: UUID,
    workspace_ref: object,
    payload: dict[str, object],
    *,
    actor_user_id: UUID | None = None,
) -> dict[str, object]:
    def number(key: str) -> float:
        value = payload.get(key, 0)
        try:
            result = float(value or 0)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=f"{key} must be numeric") from exc
        if not math.isfinite(result) or result < 0:
            raise HTTPException(status_code=422, detail=f"{key} must be non-negative")
        return result

    def timestamp(key: str) -> datetime | None:
        value = payload.get(key)
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"{key} must be an ISO timestamp") from exc

    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        workspace_mode = str(workspace.get("hosting_mode") or "cloud").lower()
        workspace_node = str(workspace.get("compute_node") or "warehouse").lower()
        mode = str(payload.get("hosting_mode") or workspace_mode).lower()
        node = str(payload.get("compute_node") or workspace_node).lower()
        if payload.get("hosting_mode") not in (None, "") and mode != workspace_mode:
            raise HTTPException(
                status_code=409,
                detail="Usage hosting_mode must match the workspace hosting mode",
            )
        if payload.get("compute_node") not in (None, "") and node != workspace_node:
            raise HTTPException(
                status_code=409,
                detail="Usage compute_node must match the workspace compute node",
            )
        if mode not in HOSTING_MODES or node not in COMPUTE_NODES:
            raise HTTPException(status_code=422, detail="Invalid hosting_mode or compute_node")
        if mode == "terminal" and node != "user_terminal":
            raise HTTPException(status_code=422, detail="Terminal usage must use user_terminal")
        if mode == "cloud" and node == "user_terminal":
            raise HTTPException(status_code=422, detail="Cloud usage requires a cloud compute node")
        metering_source = (
            str(payload.get("metering_source") or ("runtime" if mode == "cloud" else "terminal"))
            .strip()
            .lower()
        )
        if metering_source not in {"runtime", "terminal", "operator", "system"}:
            raise HTTPException(status_code=422, detail="Invalid metering_source")
        if actor_user_id is not None and metering_source != "operator":
            raise HTTPException(
                status_code=403,
                detail="Only operator metering is accepted from account sessions",
            )
        deployment_id: UUID | None = None
        deployment_ref = payload.get("deployment_id")
        if deployment_ref not in (None, ""):
            try:
                deployment_id = UUID(str(deployment_ref))
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="deployment_id must be a UUID") from exc
            exists = session.execute(
                text(
                    """
                    SELECT 1 FROM digital_asset.deployments
                    WHERE id=:deployment_id AND workspace_id=:workspace_id
                    """
                ),
                {"deployment_id": deployment_id, "workspace_id": workspace["id"]},
            ).scalar_one_or_none()
            if exists is None:
                raise HTTPException(status_code=404, detail="Deployment not found for workspace")
        key = str(payload.get("idempotency_key") or "").strip() or None
        if key and len(key) > 200:
            raise HTTPException(status_code=422, detail="idempotency_key is too long")
        if key:
            existing = (
                session.execute(
                    text(
                        "SELECT * FROM digital_asset.compute_usage_events "
                        "WHERE tenant_id=:tenant_id AND idempotency_key=:key"
                    ),
                    {"tenant_id": tenant_id, "key": key},
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                return {"ok": True, "idempotent_replay": True, "usage": _safe(dict(existing))}
        billable = mode == "cloud" and node in CLOUD_COMPUTE_NODES
        cost = number("estimated_cost_cny") if billable else 0.0
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.compute_usage_events(
                      id, tenant_id, workspace_id, asset_id, deployment_id,
                      hosting_mode, compute_node, cpu_seconds, memory_mb_seconds,
                      gpu_seconds, network_bytes, estimated_cost_cny,
                      billing_status, metering_source, idempotency_key, metadata,
                      started_at, completed_at
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :asset_id, :deployment_id,
                      :hosting_mode, :compute_node, :cpu_seconds, :memory_mb_seconds,
                      :gpu_seconds, :network_bytes, :estimated_cost_cny,
                      :billing_status, :metering_source, :idempotency_key,
                      CAST(:metadata AS jsonb), :started_at, :completed_at
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": tenant_id,
                    "workspace_id": workspace["id"],
                    "asset_id": workspace["asset_id"],
                    "deployment_id": deployment_id,
                    "hosting_mode": mode,
                    "compute_node": node,
                    "cpu_seconds": number("cpu_seconds"),
                    "memory_mb_seconds": number("memory_mb_seconds"),
                    "gpu_seconds": number("gpu_seconds"),
                    "network_bytes": int(number("network_bytes")),
                    "estimated_cost_cny": cost,
                    "billing_status": "metered" if billable else "not_billable",
                    "metering_source": metering_source,
                    "idempotency_key": key,
                    "metadata": json.dumps(
                        payload.get("metadata")
                        if isinstance(payload.get("metadata"), dict)
                        else {},
                        ensure_ascii=False,
                        default=str,
                    ),
                    "started_at": timestamp("started_at"),
                    "completed_at": timestamp("completed_at"),
                },
            )
            .mappings()
            .one()
        )
        if billable and payload.get("notify_ai", True) is not False:
            insert_hosting_notifications(
                session,
                workspace,
                event_type="cloud_compute_metered",
                message="Cloud compute usage was recorded separately from hosting storage.",
                payload={
                    "compute_node": node,
                    "cpu_seconds": number("cpu_seconds"),
                    "memory_mb_seconds": number("memory_mb_seconds"),
                    "estimated_cost_cny": cost,
                },
                targets=("ai",),
                created_by=actor_user_id,
            )
    return {"ok": True, "idempotent_replay": False, "usage": _safe(dict(row))}


def list_compute_usage(
    tenant_id: UUID, workspace_ref: object, *, limit: int = 100
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        rows = [
            _safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.compute_usage_events
                    WHERE workspace_id=:workspace_id
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"workspace_id": workspace["id"], "limit": max(1, min(int(limit), 500))},
            )
            .mappings()
            .all()
        ]
        summary = (
            session.execute(
                text(
                    """
                SELECT count(*) AS event_count,
                       COALESCE(sum(cpu_seconds), 0) AS cpu_seconds,
                       COALESCE(sum(memory_mb_seconds), 0) AS memory_mb_seconds,
                       COALESCE(sum(gpu_seconds), 0) AS gpu_seconds,
                       COALESCE(sum(network_bytes), 0) AS network_bytes,
                       COALESCE(sum(estimated_cost_cny), 0) AS estimated_cost_cny
                FROM digital_asset.compute_usage_events
                WHERE workspace_id=:workspace_id
                """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one()
        )
    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "summary": _safe(dict(summary)),
        "events": rows,
    }


def list_compute_usage_for_credential(
    credential: WorkspaceCredential,
    *,
    limit: int = 100,
) -> dict[str, object]:
    credential.require("workspace:read")
    return list_compute_usage(credential.tenant_id, credential.workspace_id, limit=limit)


def complete_terminal_deployment(
    credential: WorkspaceCredential,
    deployment_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Accept a terminal result without granting the terminal cloud authority."""

    credential.require("deploy:write")
    try:
        deployment_id = UUID(str(deployment_ref))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid terminal deployment id") from exc
    requested_status = str(payload.get("status") or "succeeded").strip().lower()
    if requested_status not in {"succeeded", "failed"}:
        raise HTTPException(status_code=422, detail="status must be succeeded or failed")
    result_payload = payload.get("result") if isinstance(payload.get("result"), dict) else {}
    successful = requested_status == "succeeded"
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.deployments
                    WHERE id=:deployment_id
                      AND workspace_id=:workspace_id
                      AND provider_key='terminal_queue'
                    FOR UPDATE
                    """
                ),
                {"deployment_id": deployment_id, "workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Terminal deployment not found")
        current_status = str(row.get("status") or "")
        if current_status in {"ready", "failed"}:
            expected_status = "ready" if successful else "failed"
            if current_status != expected_status:
                raise HTTPException(
                    status_code=409,
                    detail=f"Terminal deployment is already {current_status}",
                )
            return {
                "ok": True,
                "idempotent_replay": True,
                "deployment": _public_deployment(dict(row)),
                "notifications": [],
                "next_action": "sync_result" if successful else "repair_terminal_task",
            }
        if current_status not in {"queued", "building", "deploying"}:
            raise HTTPException(
                status_code=409,
                detail=f"Terminal deployment cannot complete from {current_status}",
            )
        updated = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET status=:status,
                        health=:health,
                        result=CAST(:result AS jsonb),
                        completed_at=now()
                    WHERE id=:deployment_id
                    RETURNING *
                    """
                ),
                {
                    "status": "ready" if successful else "failed",
                    "health": "healthy" if successful else "unhealthy",
                    "result": json.dumps(result_payload, ensure_ascii=False, default=str),
                    "deployment_id": deployment_id,
                },
            )
            .mappings()
            .one()
        )
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence), 0)+1 "
                    "FROM digital_asset.deployment_events WHERE deployment_id=:id"
                ),
                {"id": deployment_id},
            ).scalar_one()
        )
        event_type = "terminal_succeeded" if successful else "terminal_failed"
        event_payload = {
            "deployment_id": str(deployment_id),
            "status": requested_status,
            "result": result_payload,
        }
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id, tenant_id, sequence, event_type, payload
                ) VALUES (
                  :deployment_id, :tenant_id, :sequence, :event_type,
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "deployment_id": deployment_id,
                "tenant_id": credential.tenant_id,
                "sequence": sequence,
                "event_type": event_type,
                "payload": json.dumps(event_payload, ensure_ascii=False, default=str),
            },
        )
        # A terminal result is not a server Runtime health result.  Keep the
        # workspace in its provisioned control-plane state and expose the
        # terminal outcome separately in config, so workspace status cannot
        # accidentally claim that a cloud/Vultr/Mac mini Runtime is ready.
        terminal_workspace_state = _terminal_workspace_state(deployment_id, successful)
        session.execute(
            text(
                "UPDATE digital_asset.workspaces "
                "SET runtime_status=:runtime_status, "
                "config=COALESCE(config, '{}'::jsonb) || CAST(:terminal_state AS jsonb) "
                "WHERE id=:id"
            ),
            {
                "runtime_status": terminal_workspace_state["runtime_status"],
                "terminal_state": json.dumps(
                    terminal_workspace_state["config"], ensure_ascii=False
                ),
                "id": workspace["id"],
            },
        )
        config = workspace.get("config") if isinstance(workspace.get("config"), dict) else {}
        targets = config.get("notify_targets")
        if not isinstance(targets, list) or not targets:
            targets = ["terminal", "ai"]
        notifications = insert_hosting_notifications(
            session,
            workspace,
            event_type=event_type,
            message=(
                "Terminal execution completed successfully."
                if successful
                else "Terminal execution failed; inspect the terminal result."
            ),
            payload=event_payload,
            targets=targets,
            created_by=None,
            deployment_id=deployment_id,
        )
    return {
        "ok": True,
        "deployment": _public_deployment(dict(updated)),
        "notifications": notifications,
        "next_action": "sync_result" if successful else "repair_terminal_task",
    }


def terminal_deployment_manifest(
    credential: WorkspaceCredential,
    deployment_ref: object,
) -> dict[str, object]:
    """Return the least-privilege execution manifest for a terminal worker.

    The manifest is intentionally separate from the completion endpoint: a
    terminal can poll, validate and ask its local user/AI for confirmation
    before downloading or executing any source code.
    """

    credential.require("deploy:read")
    reference = str(deployment_ref).strip()
    if not reference:
        raise HTTPException(status_code=422, detail="Invalid terminal deployment id")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id
                      AND provider_key='terminal_queue'
                      AND (
                        CAST(id AS text)=:reference
                        OR CAST(legacy_id AS text)=:reference
                      )
                    """
                ),
                {"workspace_id": workspace["id"], "reference": reference},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Terminal deployment not found")
    deployment = dict(row)
    requested = deployment.get("requested_config")
    requested = requested if isinstance(requested, dict) else {}
    source_version_id = requested.get("source_version_id") or deployment.get("source_version_id")
    deployment_id = str(deployment["id"])
    runtime = requested.get("runtime") if isinstance(requested.get("runtime"), dict) else {}
    manifest = {
        "workspace_id": str(workspace["id"]),
        "deployment_id": deployment_id,
        "status": deployment.get("status"),
        "health": deployment.get("health"),
        "hosting_mode": "terminal",
        "compute_node": "user_terminal",
        "execution_target": "user_terminal",
        "source_version_id": str(source_version_id) if source_version_id else None,
        "source_sha256": requested.get("source_sha256") or deployment.get("release_digest"),
        "component": requested.get("component"),
        "entrypoint": requested.get("entrypoint"),
        "runtime": _safe(runtime),
        "cloud_fallback": requested.get("cloud_fallback") or "ask",
        "notify_targets": requested.get("notify_targets") or ["terminal", "ai"],
        "source_download": (
            f"/api/workspaces/v1/sources/{source_version_id}/download"
            if source_version_id
            else None
        ),
        "data_api": "/api/workspaces/v1/data/{collection}",
        "complete": f"/api/hosting/v2/terminal-actions/{deployment_id}/complete",
        "requested_at": deployment.get("created_at"),
    }
    return {
        "ok": True,
        "manifest": _safe(manifest),
        "deployment": _safe(
            {
                "id": deployment.get("id"),
                "legacy_id": deployment.get("legacy_id"),
                "status": deployment.get("status"),
                "health": deployment.get("health"),
                "provider_key": deployment.get("provider_key"),
                "created_at": deployment.get("created_at"),
                "completed_at": deployment.get("completed_at"),
            }
        ),
        "next_action": (
            "terminal_execute"
            if deployment.get("status") in {"queued", "building", "deploying"}
            else "sync_result"
            if deployment.get("status") == "ready"
            else "inspect_terminal_failure"
        ),
    }
