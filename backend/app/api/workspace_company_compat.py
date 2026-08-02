"""Company-control-plane compatibility for permanent workspace primary keys."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.digital_asset_hosting import _require_manage
from app.services.workspace_autonomy import rotate_primary_for_actor

router = APIRouter(tags=["workspace-company-compat"])


@router.post("/api/workspaces/{workspace_ref}/keys/primary/rotate")
def workspace_primary_key_rotate(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _require_manage(actor)
    return rotate_primary_for_actor(actor, workspace_ref, payload, settings)
