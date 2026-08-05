"""Recovery wrapper around the complete workspace-autonomy implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import text

from app.db.session import tenant_session
from app.services import workspace_autonomy_base as _base
from app.services.workspace_autonomy_base import *  # noqa: F403

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings


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
