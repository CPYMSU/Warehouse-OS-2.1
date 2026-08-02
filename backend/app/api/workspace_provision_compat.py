"""Preserve the original provision extension point while adding idempotency."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, status

from app.api import digital_assets as legacy
from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.digital_asset_hosting import create_asset as native_create_asset
from app.services.digital_asset_hosting import create_workspace as native_create_workspace
from app.services.digital_asset_hosting import (
    issue_workspace_key as native_issue_workspace_key,
)
from app.services.workspace_autonomy import provision_idempotently

router = APIRouter(tags=["workspace-provision-compat"])


def _legacy_extension_is_active() -> bool:
    """Detect established monkeypatch/plugin hooks used by tests and integrations."""

    return (
        legacy.create_asset is not native_create_asset
        or legacy.create_workspace is not native_create_workspace
        or legacy.issue_workspace_key is not native_issue_workspace_key
    )


def _legacy_compose(
    actor: ActorContext,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    created = legacy.create_asset(actor, payload)
    workspace_result = legacy.create_workspace(actor, created["asset"]["uuid"], payload)
    key_result = legacy.issue_workspace_key(
        actor,
        workspace_result["workspace"]["uuid"],
        payload,
        signing_secret=settings.integration_secret,
        key_kind="primary",
    )
    return {
        "ok": True,
        "asset": created["asset"],
        "custody_event": created["custody_event"],
        "workspace": workspace_result["workspace"],
        "components": workspace_result["components"],
        "database": workspace_result["database"],
        "storage": workspace_result["storage"],
        **{key: value for key, value in key_result.items() if key != "ok"},
        "cli_download": "/api/digital-assets/cli",
        "guide_download": "/api/digital-assets/guide/download",
    }


@router.post("/api/digital-assets/provision", status_code=status.HTTP_201_CREATED)
def digital_asset_provision(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    if _legacy_extension_is_active():
        return _legacy_compose(actor, payload, settings)
    return provision_idempotently(actor, payload, settings)
