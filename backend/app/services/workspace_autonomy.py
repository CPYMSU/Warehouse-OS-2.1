"""Recovery wrapper around the complete workspace-autonomy implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import tenant_session
from app.services import workspace_autonomy_base as _base
from app.services.workspace_autonomy_base import *  # noqa: F403

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


def _quota_integer(value: object, name: str) -> int:
    """Do not silently truncate JSON floats or accept booleans as byte counts."""

    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise HTTPException(status_code=422, detail=f"{name} must be an integer")
    try:
        amount = int(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an integer") from exc
    if amount < 0:
        raise HTTPException(status_code=422, detail=f"{name} cannot be negative")
    return amount


def resize_capacity(
    credential: _base.WorkspaceCredential,
    payload: dict[str, object],
) -> dict[str, object]:
    """Set an explicit quota target atomically, independently of usage changes.

    Relative and minimum-free requests retain the elastic allocation contract.
    An absolute target is a quota, not a free-space reservation: translating it
    into free bytes and measuring usage again can accidentally add another unit.
    """

    _base._require_primary(credential)
    values = {
        "target_bytes": payload.get("target_bytes"),
        "target_mb": payload.get("target_mb"),
        "additional_bytes": payload.get("additional_bytes", payload.get("delta_bytes")),
        "additional_mb": payload.get("additional_mb", payload.get("delta_mb")),
        "minimum_free_bytes": payload.get("minimum_free_bytes"),
        "minimum_free_mb": payload.get("minimum_free_mb"),
    }
    supplied = [name for name, value in values.items() if value not in (None, "")]
    if len(supplied) != 1 or not supplied[0].startswith("target"):
        return _base.resize_capacity(credential, payload)

    credential.require("infra:write")
    name = supplied[0]
    target = _quota_integer(values[name], name)
    if name == "target_mb":
        target *= 1024 * 1024
    if target > _base.MAX_POSTGRES_BIGINT:
        raise HTTPException(status_code=422, detail="Requested workspace quota is too large")
    if target % _base.WORKSPACE_QUOTA_STEP_BYTES:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "quota_target_not_allocation_aligned",
                "allocation_unit_bytes": _base.WORKSPACE_QUOTA_STEP_BYTES,
            },
        )
    expected_raw = payload.get("expected_revision")
    expected_revision = (
        None if expected_raw in (None, "") else _quota_integer(expected_raw, "expected_revision")
    )
    with tenant_session(credential.tenant_id) as session:
        workspace = _base._workspace_row(session, credential.workspace_id, lock=True)
        revision = int(workspace.get("revision") or 0)
        before = int(workspace["storage_quota_bytes"])
        if target < before:
            raise HTTPException(status_code=422, detail="Workspace quota cannot be reduced")
        changed = target > before
        # A retry after a successful but lost response must not allocate again.
        # A stale revision is harmless only when the requested target is already
        # the exact current quota; otherwise it remains a conflict.
        if changed and expected_revision is not None and expected_revision != revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "workspace_revision_changed",
                    "expected_revision": expected_revision,
                    "current_revision": revision,
                },
            )
        usage = _base._workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=workspace["asset_id"],
        )
        required_free = max(0, target - int(usage["total_bytes"]))
        if changed:
            workspace = dict(
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET storage_quota_bytes=:target, revision=revision+1
                        WHERE id=:id RETURNING *
                        """
                    ),
                    {"target": target, "id": workspace["id"]},
                )
                .mappings()
                .one()
            )
            _base._audit(
                session,
                None,
                "digital_asset.workspace_quota_elastic_increase",
                {
                    "workspace_id": str(workspace["id"]),
                    "requested_by_credential_id": str(credential.credential_id),
                    "reason": "explicit_primary_key_resize",
                    "used_bytes": int(usage["total_bytes"]),
                    "required_free_bytes": required_free,
                    "requested_target_bytes": target,
                    "expected_revision": expected_revision,
                    "before_bytes": before,
                    "after_bytes": target,
                    "allocation_units_added": (target - before) // _base.WORKSPACE_QUOTA_STEP_BYTES,
                },
                tenant_id=credential.tenant_id,
            )
    return {
        "ok": True,
        "changed": changed,
        "target_already_satisfied": not changed,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "used_bytes": int(usage["total_bytes"]),
        "required_free_bytes": required_free,
        "quota_bytes": int(workspace["storage_quota_bytes"]),
        "remaining_bytes": required_free,
        "revision": int(workspace.get("revision") or revision),
        "allocation_unit_bytes": _base.WORKSPACE_QUOTA_STEP_BYTES,
        "allocation_units_added": (target - before) // _base.WORKSPACE_QUOTA_STEP_BYTES,
    }


def provision_idempotently(
    actor: ActorContext,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Provision safely and recover a missing/expired primary-key tail step."""

    result = _base.provision_idempotently(actor, payload, settings)
    if result.get("api_key"):
        return result
    workspace_id = UUID(str(result["workspace"]["uuid"]))
    with tenant_session(actor.tenant_id) as session:
        primary = (
            session.execute(
                text(
                    """
                    SELECT id, (expires_at IS NULL OR expires_at > now()) AS usable
                    FROM digital_asset.api_credentials
                    WHERE workspace_id=:workspace_id AND key_kind='primary'
                      AND revoked_at IS NULL
                    FOR UPDATE
                    """
                ),
                {"workspace_id": workspace_id},
            )
            .mappings()
            .one_or_none()
        )
    if primary is not None and bool(primary["usable"]):
        return result
    key_result = _base._issue_workspace_key(
        tenant_id=actor.tenant_id,
        workspace_id=workspace_id,
        signing_secret=settings.integration_secret,
        payload=payload,
        key_kind="primary",
        issued_by_user_id=actor.user_id,
        requested_by_credential_id=None,
        rotate_primary=primary is not None,
    )
    return {
        **result,
        **{key: value for key, value in key_result.items() if key != "ok"},
        "recovered_primary_key": True,
        "key_delivery": "one_time_recovery",
    }


def rotate_primary_for_actor(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Rotate through the company control plane with permanent-by-default semantics."""

    with tenant_session(actor.tenant_id) as session:
        workspace = _base._workspace_row(session, workspace_ref)
    return _base._issue_workspace_key(
        tenant_id=actor.tenant_id,
        workspace_id=UUID(str(workspace["id"])),
        signing_secret=settings.integration_secret,
        payload=payload,
        key_kind="primary",
        issued_by_user_id=actor.user_id,
        requested_by_credential_id=None,
        rotate_primary=True,
    )
