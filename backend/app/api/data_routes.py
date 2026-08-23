"""Warehouse 09.4 data-route design and lifecycle API."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import ActorContext, current_actor
from app.services.data_routes import get_route, list_routes, save_route

router = APIRouter(tags=["database-data-routes"])


@router.get("/api/data-routes")
def data_routes_list(
    limit: int = Query(default=100, ge=1, le=200),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_routes(actor, limit=limit)


@router.get("/api/data-routes/{route_key}")
def data_route_get(
    route_key: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return {"route": get_route(actor, route_key)}


@router.post("/api/data-routes", status_code=status.HTTP_201_CREATED)
def data_route_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return save_route(actor, payload)


@router.put("/api/data-routes/{route_key}")
def data_route_update(
    route_key: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return save_route(actor, payload, route_key=route_key)
