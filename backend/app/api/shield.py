"""Authenticated SHIELD telemetry, repair and risk-review endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, Request

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.shield import execute_shield_repair, get_shield_status, review_ai_risk

router = APIRouter(tags=["shield"])


@router.get("/api/shield/status")
def shield_status(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return get_shield_status(actor, settings)


@router.post("/api/shield/repair")
def shield_repair(
    request: Request,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    return execute_shield_repair(
        actor,
        settings,
        action=str(payload.get("action") or "healthcheck"),
        confirm=payload.get("confirm") is True,
        apply_requested=payload.get("apply") is True,
        request_id=request_id,
    )


@router.post("/api/shield/risks/{execution_id}/review")
def shield_risk_review(
    execution_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return review_ai_risk(
        actor,
        execution_id=execution_id,
        decision=str(payload.get("decision") or "reviewed"),
    )
