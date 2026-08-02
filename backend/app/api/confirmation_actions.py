"""Actor-scoped API for durable AI command confirmations."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, Response

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.confirmation_actions import (
    acknowledge_confirmation_credentials,
    cancel_confirmation_action,
    confirm_confirmation_action,
    edit_confirmation_action,
    fetch_confirmation_credentials,
    get_confirmation_action,
    list_confirmation_actions,
)

router = APIRouter(tags=["ai-confirmation-actions"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/api/agent/confirmation-actions")
def confirmation_actions_list(
    response: Response,
    conversation_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    actions = list_confirmation_actions(
        actor,
        conversation_id=conversation_id,
        limit=limit,
    )
    return {"ok": True, "actions": actions, "count": len(actions)}


@router.get("/api/agent/confirmation-actions/{action_id}")
def confirmation_action_get(
    action_id: int,
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    return get_confirmation_action(actor, action_id)


@router.post("/api/agent/confirmation-actions/{action_id}/cancel")
def confirmation_action_cancel(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    return cancel_confirmation_action(
        actor,
        action_id,
        expected_revision=payload.get("expected_revision"),
    )


@router.post("/api/agent/confirmation-actions/{action_id}/edit")
def confirmation_action_edit(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _no_store(response)
    return edit_confirmation_action(
        actor,
        action_id,
        expected_revision=payload.get("expected_revision"),
        values=payload.get("values"),
        settings=settings,
    )


@router.post("/api/agent/confirmation-actions/{action_id}/confirm")
def confirmation_action_confirm(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _no_store(response)
    return confirm_confirmation_action(
        actor,
        action_id,
        expected_revision=payload.get("expected_revision"),
        step_up_token=payload.get("step_up_token"),
        credential_client_id=payload.get("credential_client_id"),
        settings=settings,
    )


@router.post(
    "/api/agent/confirmation-actions/{action_id}/credential-delivery/fetch"
)
def confirmation_credentials_fetch(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _no_store(response)
    return fetch_confirmation_credentials(
        actor,
        action_id,
        delivery_id=payload.get("delivery_id"),
        credential_client_id=payload.get("credential_client_id"),
        settings=settings,
    )


@router.post(
    "/api/agent/confirmation-actions/{action_id}/credential-delivery/ack"
)
def confirmation_credentials_ack(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _no_store(response)
    return acknowledge_confirmation_credentials(
        actor,
        action_id,
        delivery_id=payload.get("delivery_id"),
        credential_client_id=payload.get("credential_client_id"),
    )
