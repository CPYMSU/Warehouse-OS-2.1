"""Actor-scoped API for durable AI command confirmations."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.confirmation_actions import (
    acknowledge_confirmation_credentials,
    cancel_confirmation_action,
    confirm_confirmation_action,
    edit_confirmation_action,
    execute_authorized_confirmation_action,
    fetch_confirmation_credentials,
    get_confirmation_action,
    list_confirmation_actions,
    propose_confirmation_action,
)
from app.terminal import legacy_catalog
from app.terminal.catalog import availability, entry_by_tool_name, is_authorized

router = APIRouter(tags=["ai-confirmation-actions"])


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.post("/api/business/actions/{tool_name}/propose")
def business_action_propose_confirmation(
    tool_name: str,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Stage a governed button action through the shared AI confirmation contract."""

    _no_store(response)
    entry = entry_by_tool_name(tool_name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Action is not registered")
    if availability(entry) != "active":
        raise HTTPException(status_code=409, detail="Capability adapter is unavailable")
    if not is_authorized(entry, actor.permissions):
        raise HTTPException(status_code=403, detail="Action is not authorized for this user")
    policy = legacy_catalog.confirmation_contract(entry)
    if policy != {"mode": "passkey", "adapter": "staged_action"}:
        raise HTTPException(
            status_code=409,
            detail="Action does not use the Passkey staged-action workflow",
        )
    arguments = payload.get("arguments")
    if not isinstance(arguments, dict):
        raise HTTPException(status_code=422, detail="arguments must be an object")
    proposal_id = str(payload.get("proposal_id") or "").strip()
    if len(proposal_id) < 8:
        raise HTTPException(status_code=422, detail="proposal_id is required")
    action = propose_confirmation_action(
        actor,
        tool_name=tool_name,
        arguments=arguments,
        proposal_id=proposal_id,
        settings=settings,
    )
    return {
        "ok": True,
        "status": "confirmation_required",
        "business_operation_executed": False,
        "action": action,
        "confirmation_action": action,
    }


@router.post(
    "/api/business/actions/confirmation-actions/{action_id}/execute-authorized"
)
def business_action_execute_authorized_confirmation(
    action_id: int,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Consume a manual button action's exact one-use Passkey Keychain."""

    _no_store(response)
    return execute_authorized_confirmation_action(
        actor,
        action_id,
        authorization_keychain_id=payload.get("authorization_keychain_id"),
        conversation_id=None,
        settings=settings,
    )


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
