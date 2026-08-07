"""Authenticated API for the tenant Civilization register."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, status

from app.api.deps import ActorContext, current_actor
from app.services.civilization import create_thought, delete_thought, list_thoughts

router = APIRouter(tags=["civilization"])


@router.get("/api/civilization/thoughts")
def civilization_thoughts(
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return list_thoughts(actor)


@router.post("/api/civilization/thoughts", status_code=status.HTTP_201_CREATED)
def civilization_thought_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_thought(actor, payload)


@router.delete("/api/civilization/thoughts/{thought_id}")
def civilization_thought_delete(
    thought_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return delete_thought(actor, thought_id)
