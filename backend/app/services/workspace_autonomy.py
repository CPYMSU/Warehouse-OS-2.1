"""Workspace-root autonomy for digital-asset hosting.

A primary ``wak_`` credential is the complete authority inside one tenant-bound
workspace. This module removes control-plane round trips for workspace-local
operations while preserving tenant/workspace isolation, provider capacity,
immutable audit evidence, and host safety.
"""

from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services.digital_asset_hosting import (
    DEFAULT_DELEGATED_SCOPES,
    WORKSPACE_ALL_SCOPES,
    WORKSPACE_QUOTA_STEP_BYTES,
    WORKSPACE_SCOPES,
    WorkspaceCredential,
    _audit,
    _json_safe,
    _public_asset,
    _public_workspace,
    _slug,
    _storage_binding_rows,
    _storage_profile,
    _workspace_billable_usage,
    _workspace_row,
    asset_detail,
    create_asset,
    create_workspace,
)

if TYPE_CHECKING:
    from app.api.deps import ActorContext

MAX_POSTGRES_BIGINT = (1 << 63) - 1
DEFAULT_DELEGATED_EXPIRY_DAYS = 90
MAX_EXPLICIT_EXPIRY_DAYS = 3650
RECORD_WRITE_HEADROOM_BYTES = 1024 * 1024
SOURCE_UPLOAD_HEADROOM_BYTES = 8 * 1024 * 1024


def allocation_target_bytes(required_total_bytes: int, *, current_bytes: int = 0) -> int:
    """Round a requirement to allocation units without imposing a one-unit gate."""

    required = max(0, int(required_total_bytes), int(current_bytes))
    if required == 0:
        return 0
    units = math.ceil(required / WORKSPACE_QUOTA_STEP_BYTES)
    target = units * WORKSPACE_QUOTA_STEP_BYTES
    if target > MAX_POSTGRES_BIGINT:
        raise HTTPException(
            status_code=422, detail="Requested workspace quota is too large"
        )
    return target


def estimate_record_write_bytes(payload: dict[str, object]) -> int:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return max(RECORD_WRITE_HEADROOM_BYTES, len(encoded) * 4 + 65_536)


def _require_primary(credential: WorkspaceCredential) -> None:
    if credential.key_kind != "primary":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "reason": "primary_workspace_key_required",
                "message": "This workspace-root operation requires the primary wak_ key",
            },
        )


def _expiry(
    payload: dict[str, object],
    *,
    primary: bool,
) -> tuple[datetime | None, int | None]:
    supplied = "expires_days" in payload or "expires_in_days" in payload
    raw = payload.get("expires_days", payload.get("expires_in_days"))
    if not supplied:
        if primary:
            return None, None
        raw = DEFAULT_DELEGATED_EXPIRY_DAYS
    if raw in (None, "", 0, "0", "never", "none", "permanent"):
        return None, None
    if isinstance(raw, bool):
        raise HTTPException(status_code=422, detail="expires_days must be an integer or null")
    try:
        days = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="expires_days must be an integer or null"
        ) from exc
    if not 1 <= days <= MAX_EXPLICIT_EXPIRY_DAYS:
        raise HTTPException(
            status_code=422,
            detail=f"expires_days must be between 1 and {MAX_EXPLICIT_EXPIRY_DAYS}, or null",
        )
    return datetime.now(UTC) + timedelta(days=days), days


def _issue_workspace_key(
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    signing_secret: str,
    payload: dict[str, object],
    key_kind: str,
    issued_by_user_id: UUID | None,
    requested_by_credential_id: UUID | None,
    rotate_primary: bool,
) -> dict[str, object]:
    if key_kind not in {"primary", "delegated"}:
        raise ValueError("key_kind must be primary or delegated")
    default_label = (
        "Primary workspace key" if key_kind == "primary" else "Delegated workspace key"
    )
    label = str(payload.get("label") or default_label).strip()[:120]
    if not label:
        raise HTTPException(status_code=422, detail="Workspace key label is required")

    supplied_scopes = payload.get("scopes")
    if key_kind == "primary":
        scopes = list(WORKSPACE_ALL_SCOPES)
    else:
        if isinstance(supplied_scopes, str):
            candidates = [part.strip() for part in supplied_scopes.split(",")]
        elif isinstance(supplied_scopes, list):
            candidates = [str(item).strip() for item in supplied_scopes]
        elif supplied_scopes in (None, ""):
            candidates = list(DEFAULT_DELEGATED_SCOPES)
        else:
            raise HTTPException(status_code=422, detail="scopes must be an array or string")
        scopes = list(dict.fromkeys(item for item in candidates if item))
        if not scopes:
            raise HTTPException(status_code=422, detail="At least one delegated scope is required")
    invalid = sorted(set(scopes) - WORKSPACE_SCOPES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid scopes: {', '.join(invalid)}")

    issued_at = datetime.now(UTC)
    expires_at, expires_days = _expiry(payload, primary=key_kind == "primary")
    credential_id = uuid4()
    replaced_credential_id: UUID | None = None
    parent_credential_id: UUID | None = None

    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_id, lock=True)
        current_primary = (
            session.execute(
                text(
                    """
                    SELECT id, expires_at FROM digital_asset.api_credentials
                    WHERE workspace_id=:workspace_id AND key_kind='primary'
                      AND revoked_at IS NULL
                    FOR UPDATE
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if key_kind == "primary":
            if current_primary is not None and not rotate_primary:
                raise HTTPException(
                    status_code=409,
                    detail="Workspace already has a primary key; rotate it instead",
                )
            if current_primary is not None:
                replaced_credential_id = UUID(str(current_primary["id"]))
                session.execute(
                    text(
                        "UPDATE digital_asset.api_credentials SET revoked_at=:now "
                        "WHERE id=:id AND revoked_at IS NULL"
                    ),
                    {"id": replaced_credential_id, "now": issued_at},
                )
        else:
            if current_primary is None:
                raise HTTPException(status_code=409, detail="Workspace has no active primary key")
            parent_credential_id = UUID(str(current_primary["id"]))

        claims: dict[str, object] = {
            "iss": "warehouse-os",
            "aud": "warehouse-workspace",
            "sub": str(credential_id),
            "jti": str(credential_id),
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace["id"]),
            "scopes": scopes,
            "key_kind": key_kind,
            "iat": issued_at,
        }
        if expires_at is not None:
            claims["exp"] = expires_at
        if parent_credential_id is not None:
            claims["parent_credential_id"] = str(parent_credential_id)
        token = "wak_" + jwt.encode(claims, signing_secret, algorithm="HS256")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        token_hint = token[:14] + "····" + token[-6:]
        session.execute(
            text(
                """
                INSERT INTO digital_asset.api_credentials(
                  id,tenant_id,workspace_id,label,token_hash,token_hint,scopes,
                  key_kind,parent_credential_id,issued_by,issued_at,expires_at
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:label,:token_hash,:token_hint,:scopes,
                  :key_kind,:parent_credential_id,:issued_by,:issued_at,:expires_at
                )
                """
            ),
            {
                "id": credential_id,
                "tenant_id": tenant_id,
                "workspace_id": workspace["id"],
                "label": label,
                "token_hash": token_hash,
                "token_hint": token_hint,
                "scopes": scopes,
                "key_kind": key_kind,
                "parent_credential_id": parent_credential_id,
                "issued_by": issued_by_user_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
            },
        )
        _audit(
            session,
            None,
            "digital_asset.workspace_primary_key_rotated"
            if replaced_credential_id is not None
            else f"digital_asset.workspace_{key_kind}_key_issued",
            {
                "workspace_id": str(workspace["id"]),
                "credential_id": str(credential_id),
                "requested_by_credential_id": (
                    str(requested_by_credential_id) if requested_by_credential_id else None
                ),
                "label": label,
                "key_kind": key_kind,
                "scopes": scopes,
                "expires_at": expires_at.isoformat() if expires_at else None,
                "replaced_credential_id": (
                    str(replaced_credential_id) if replaced_credential_id else None
                ),
            },
            tenant_id=tenant_id,
        )

    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "credential_id": str(credential_id),
        "key_id": str(credential_id),
        "key_kind": key_kind,
        "is_primary": key_kind == "primary",
        "label": label,
        "api_key": token,
        "api_key_hint": token_hint,
        "scopes": scopes,
        "expires_at": expires_at.isoformat() if expires_at else None,
        "expires_days": expires_days,
        "replaced_credential_id": (
            str(replaced_credential_id) if replaced_credential_id else None
        ),
        "base_url": "/api/workspaces/v1",
        "plaintext_exposed_once": True,
    }


def issue_delegated_key(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_primary(credential)
    credential.require("workspace:read")
    requested = payload.get("scopes")
    requested_values = (
        [part.strip() for part in requested.split(",")]
        if isinstance(requested, str)
        else [str(item).strip() for item in requested]
        if isinstance(requested, list)
        else list(DEFAULT_DELEGATED_SCOPES)
    )
    denied = sorted(set(requested_values) - set(credential.scopes))
    if denied:
        raise HTTPException(
            status_code=403,
            detail=f"Primary key lacks scopes: {', '.join(denied)}",
        )
    return _issue_workspace_key(
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        signing_secret=settings.integration_secret,
        payload=payload,
        key_kind="delegated",
        issued_by_user_id=None,
        requested_by_credential_id=credential.credential_id,
        rotate_primary=False,
    )


def rotate_primary_key(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    _require_primary(credential)
    return _issue_workspace_key(
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        signing_secret=settings.integration_secret,
        payload=payload,
        key_kind="primary",
        issued_by_user_id=None,
        requested_by_credential_id=credential.credential_id,
        rotate_primary=True,
    )


def list_keys(credential: WorkspaceCredential) -> dict[str, object]:
    _require_primary(credential)
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        rows = (
            session.execute(
                text(
                    """
                    SELECT id,label,token_hint,scopes,key_kind,parent_credential_id,
                           issued_at,expires_at,last_used_at,revoked_at,
                           CASE
                             WHEN revoked_at IS NOT NULL THEN 'revoked'
                             WHEN expires_at IS NOT NULL AND expires_at <= now() THEN 'expired'
                             ELSE 'active'
                           END AS status
                    FROM digital_asset.api_credentials
                    WHERE workspace_id=:workspace_id
                    ORDER BY
                      CASE WHEN key_kind='primary' AND revoked_at IS NULL THEN 0
                           WHEN key_kind='delegated' AND revoked_at IS NULL THEN 1 ELSE 2 END,
                      issued_at DESC
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .all()
        )
    items = [_json_safe(dict(row)) for row in rows]
    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "items": items,
        "keys": items,
        "count": len(items),
        "plaintext_exposed": False,
    }


def revoke_delegated_key(
    credential: WorkspaceCredential,
    credential_ref: object,
) -> dict[str, object]:
    _require_primary(credential)
    try:
        target_id = UUID(str(credential_ref))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid credential id") from exc
    with tenant_session(credential.tenant_id) as session:
        _workspace_row(session, credential.workspace_id, lock=True)
        row = (
            session.execute(
                text(
                    """
                    SELECT id,label,token_hint,scopes,key_kind,revoked_at
                    FROM digital_asset.api_credentials
                    WHERE id=:id AND workspace_id=:workspace_id
                    FOR UPDATE
                    """
                ),
                {"id": target_id, "workspace_id": credential.workspace_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Workspace credential not found")
        if row["key_kind"] == "primary" and row["revoked_at"] is None:
            raise HTTPException(status_code=409, detail="Rotate the primary key instead")
        replay = row["revoked_at"] is not None
        if not replay:
            row = (
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.api_credentials SET revoked_at=now()
                        WHERE id=:id AND workspace_id=:workspace_id AND revoked_at IS NULL
                        RETURNING id,label,token_hint,scopes,key_kind,revoked_at
                        """
                    ),
                    {"id": target_id, "workspace_id": credential.workspace_id},
                )
                .mappings()
                .one()
            )
            _audit(
                session,
                None,
                "digital_asset.workspace_key_revoked",
                {
                    "workspace_id": str(credential.workspace_id),
                    "credential_id": str(target_id),
                    "requested_by_credential_id": str(credential.credential_id),
                },
                tenant_id=credential.tenant_id,
            )
    return {"ok": True, "credential": _json_safe(dict(row)), "idempotent_replay": replay}


def ensure_capacity(
    credential: WorkspaceCredential,
    *,
    required_free_bytes: int,
    expected_revision: int | None = None,
    reason: str = "workspace_operation",
) -> dict[str, object]:
    credential.require("infra:write")
    required_free = max(0, int(required_free_bytes))
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        revision = int(workspace.get("revision") or 0)
        if expected_revision is not None and int(expected_revision) != revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "workspace_revision_changed",
                    "expected_revision": int(expected_revision),
                    "current_revision": revision,
                },
            )
        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=workspace["asset_id"],
        )
        before = int(workspace["storage_quota_bytes"])
        target = allocation_target_bytes(
            int(usage["total_bytes"]) + required_free,
            current_bytes=before,
        )
        changed = target > before
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
            _audit(
                session,
                None,
                "digital_asset.workspace_quota_elastic_increase",
                {
                    "workspace_id": str(workspace["id"]),
                    "requested_by_credential_id": str(credential.credential_id),
                    "reason": reason,
                    "used_bytes": int(usage["total_bytes"]),
                    "required_free_bytes": required_free,
                    "before_bytes": before,
                    "after_bytes": target,
                    "allocation_units_added": (target - before) // WORKSPACE_QUOTA_STEP_BYTES,
                },
                tenant_id=credential.tenant_id,
            )
    return {
        "ok": True,
        "changed": changed,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "used_bytes": int(usage["total_bytes"]),
        "required_free_bytes": required_free,
        "quota_bytes": int(workspace["storage_quota_bytes"]),
        "remaining_bytes": max(
            int(workspace["storage_quota_bytes"]) - int(usage["total_bytes"]), 0
        ),
        "revision": int(workspace.get("revision") or revision),
        "allocation_unit_bytes": WORKSPACE_QUOTA_STEP_BYTES,
        "allocation_units_added": (target - before) // WORKSPACE_QUOTA_STEP_BYTES,
    }


def resize_capacity(
    credential: WorkspaceCredential,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_primary(credential)
    expected_raw = payload.get("expected_revision")
    try:
        expected_revision = (
            None if expected_raw in (None, "") else int(expected_raw)
        )
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422, detail="expected_revision must be an integer"
        ) from exc
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=workspace["asset_id"],
            persist=False,
        )
        current = int(workspace["storage_quota_bytes"])
    values = {
        "target_bytes": payload.get("target_bytes"),
        "target_mb": payload.get("target_mb"),
        "additional_bytes": payload.get("additional_bytes", payload.get("delta_bytes")),
        "additional_mb": payload.get("additional_mb", payload.get("delta_mb")),
        "minimum_free_bytes": payload.get("minimum_free_bytes"),
        "minimum_free_mb": payload.get("minimum_free_mb"),
    }
    supplied = [name for name, value in values.items() if value not in (None, "")]
    if len(supplied) != 1:
        raise HTTPException(
            status_code=422,
            detail="Supply exactly one target, additional, or minimum-free quota field",
        )
    name = supplied[0]
    raw = values[name]
    try:
        amount = int(raw)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an integer") from exc
    if amount < 0:
        raise HTTPException(status_code=422, detail="Workspace quota cannot be reduced")
    if name.endswith("_mb"):
        amount *= 1024 * 1024
    if name.startswith("target"):
        required_total = amount
    elif name.startswith("additional"):
        required_total = current + amount
    else:
        required_total = int(usage["total_bytes"]) + amount
    if required_total < current:
        raise HTTPException(status_code=422, detail="Workspace quota cannot be reduced")
    required_free = max(0, required_total - int(usage["total_bytes"]))
    return ensure_capacity(
        credential,
        required_free_bytes=required_free,
        expected_revision=expected_revision,
        reason="explicit_primary_key_resize",
    )


def autonomy_manifest(credential: WorkspaceCredential) -> dict[str, object]:
    from app.services.digital_asset_hosting import workspace_info

    info = workspace_info(credential)
    missing = sorted(set(WORKSPACE_ALL_SCOPES) - set(credential.scopes))
    return {
        "ok": True,
        "schema": "warehouse.workspace-autonomy.v1",
        "workspace": info.get("workspace"),
        "credential": {
            "credential_id": str(credential.credential_id),
            "key_kind": credential.key_kind,
            "label": credential.label,
            "scopes": sorted(credential.scopes),
            "complete_primary_authority": credential.key_kind == "primary" and not missing,
            "missing_primary_scopes": missing,
        },
        "guarantees": {
            "tenant_and_workspace_bound": True,
            "workspace_local_passkey_required": False,
            "workspace_local_company_session_required": False,
            "primary_key_non_expiring_by_default": True,
            "elastic_quota_multi_unit": True,
            "automatic_quota_growth_for_primary_data_writes": True,
            "host_paths_or_platform_credentials_exposed": False,
        },
        "capabilities": {
            "data": ["schema", "list", "put"],
            "source_and_runtime": ["upload", "configure", "deploy", "observe", "activate"],
            "infrastructure": [
                "container",
                "compose",
                "domain",
                "environment",
                "secret",
                "scaling",
                "database_migration",
                "repository",
                "backup",
                "accelerator",
            ],
            "credential_management": ["list", "issue_delegated", "rotate_primary", "revoke"],
            "quota": ["observe", "resize", "automatic_growth"],
        },
    }


def _existing_provision_result(actor: ActorContext, workspace_key: str) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT w.*, a.id AS asset_uuid, a.legacy_id AS asset_legacy_id,
                           a.asset_no,a.name,a.asset_kind,a.summary,a.status AS asset_status,
                           a.lifecycle_stage,a.risk_level,a.tags,a.metadata,
                           a.created_at AS asset_created_at,a.updated_at AS asset_updated_at
                    FROM digital_asset.workspaces AS w
                    JOIN digital_asset.assets AS a ON a.id=w.asset_id
                    WHERE w.workspace_key=:workspace_key AND w.status='active'
                    """
                ),
                {"workspace_key": workspace_key},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        workspace = dict(row)
        asset = {
            "id": row["asset_uuid"],
            "legacy_id": row["asset_legacy_id"],
            "asset_no": row["asset_no"],
            "name": row["name"],
            "asset_kind": row["asset_kind"],
            "summary": row["summary"],
            "status": row["asset_status"],
            "lifecycle_stage": row["lifecycle_stage"],
            "risk_level": row["risk_level"],
            "tags": row["tags"],
            "metadata": row["metadata"],
            "created_at": row["asset_created_at"],
            "updated_at": row["asset_updated_at"],
        }
        storage = _storage_profile(_storage_binding_rows(session, row["id"]))
        database = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.database_bindings "
                    "WHERE workspace_id=:workspace_id ORDER BY created_at LIMIT 1"
                ),
                {"workspace_id": row["id"]},
            )
            .mappings()
            .one_or_none()
        )
    public_workspace = _public_workspace(workspace, actor.tenant_slug)
    public_workspace["storage"] = storage
    return {
        "ok": True,
        "created": False,
        "idempotent_replay": True,
        "asset": _public_asset(asset),
        "workspace": public_workspace,
        "database": _json_safe(dict(database)) if database is not None else None,
        "storage": storage,
        "api_key": None,
        "key_delivery": "not_replayed",
        "next_action": "use_the_existing_primary_key_or_rotate_it",
    }


def provision_idempotently(
    actor: ActorContext,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    name = str(payload.get("name") or payload.get("title") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name is required")
    workspace_key = _slug(payload.get("workspace_key") or name, prefix="app")
    normalized = {**payload, "workspace_key": workspace_key}
    lock_key = f"warehouse:workspace-provision:{actor.tenant_id}:{workspace_key}"

    with system_session() as lock_session:
        lock_session.execute(
            text("SELECT pg_advisory_lock(hashtextextended(:key,0))"),
            {"key": lock_key},
        )
        try:
            existing = _existing_provision_result(actor, workspace_key)
            if existing is not None:
                if str(existing["asset"]["name"]).casefold() != name.casefold():
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "reason": "workspace_key_owned_by_another_asset",
                            "workspace_key": workspace_key,
                            "existing_asset": existing["asset"]["name"],
                        },
                    )
                return existing

            with tenant_session(actor.tenant_id) as session:
                matches = (
                    session.execute(
                        text(
                            "SELECT id FROM digital_asset.assets "
                            "WHERE lower(name)=lower(:name) AND status!='archived' "
                            "ORDER BY created_at DESC LIMIT 2"
                        ),
                        {"name": name},
                    )
                    .scalars()
                    .all()
                )
            if len(matches) > 1:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "ambiguous_existing_asset",
                        "message": (
                            "Multiple active assets have this name; "
                            "use a unique workspace_key"
                        ),
                    },
                )
            if matches:
                asset = asset_detail(actor, matches[0])["asset"]
                custody_event = None
                asset_ref = asset["uuid"]
            else:
                created = create_asset(actor, normalized)
                asset = created["asset"]
                custody_event = created.get("custody_event")
                asset_ref = asset["uuid"]
            workspace_result = create_workspace(actor, asset_ref, normalized)
            key_result = _issue_workspace_key(
                tenant_id=actor.tenant_id,
                workspace_id=UUID(str(workspace_result["workspace"]["uuid"])),
                signing_secret=settings.integration_secret,
                payload=normalized,
                key_kind="primary",
                issued_by_user_id=actor.user_id,
                requested_by_credential_id=None,
                rotate_primary=False,
            )
            return {
                "ok": True,
                "created": True,
                "idempotent_replay": False,
                "asset": asset,
                "custody_event": custody_event,
                "workspace": workspace_result["workspace"],
                "components": workspace_result.get("components", []),
                "database": workspace_result.get("database"),
                "storage": workspace_result.get("storage"),
                **{key: value for key, value in key_result.items() if key != "ok"},
                "cli_download": "/api/digital-assets/cli",
                "guide_download": "/api/digital-assets/guide/download",
            }
        finally:
            lock_session.execute(
                text("SELECT pg_advisory_unlock(hashtextextended(:key,0))"),
                {"key": lock_key},
            )
