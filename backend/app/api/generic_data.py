"""Stable, database-independent Data API 2.1 for humans and Auto Runtime."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request

from app.api.deps import ActorContext, current_actor
from app.services.database_runtime import (
    database_catalog,
    database_execute,
    database_query,
    database_schema,
)
from app.services.generic_data import (
    commit_mutation,
    list_capability_gaps,
    list_mutations,
    list_resources,
    observe_resource_graph,
    preview_mutation,
    query_resources,
    record_mutation_failure,
    resolve_resource,
    resource_schema,
)

router = APIRouter(tags=["ai-native-data"])


@router.get("/api/data/v2/database")
def data_database_catalog(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return database_catalog(actor)


@router.post("/api/data/v2/database/schema")
def data_database_schema(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return database_schema(actor, payload)


@router.post("/api/data/v2/database/query")
def data_database_query(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return database_query(
        actor,
        payload,
        origin=request.headers.get("X-Warehouse-Execution-Origin") or "api",
    )


@router.post("/api/data/v2/database/execute")
def data_database_execute(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return database_execute(
        actor,
        payload,
        origin=request.headers.get("X-Warehouse-Execution-Origin") or "api",
    )


@router.get("/api/data/v2/resources")
def data_resources(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return list_resources(actor)


@router.get("/api/data/v2/resources/{resource_key}/schema")
def data_resource_schema(
    resource_key: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return resource_schema(actor, resource_key)


@router.get("/api/data/v2/mutations")
def data_mutations(
    resource: str | None = Query(default=None),
    ref: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_mutations(
        actor,
        resource_key=resource,
        resource_ref=ref,
        limit=limit,
    )


@router.get("/api/data/v2/capability-gaps")
def data_capability_gaps(
    gap_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_capability_gaps(actor, gap_status=gap_status, limit=limit)


@router.post("/api/data/v2/resolve")
def data_resolve(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return resolve_resource(actor, payload)


@router.post("/api/data/v2/observe")
def data_observe(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return observe_resource_graph(actor, payload)


@router.post("/api/data/v2/query")
def data_query(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return query_resources(actor, payload)


@router.post("/api/data/v2/mutations/preview")
def data_mutation_preview(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return preview_mutation(actor, payload)


@router.post("/api/data/v2/mutations/commit")
def data_mutation_commit(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    origin = request.headers.get("X-Warehouse-Execution-Origin") or "api"
    try:
        return commit_mutation(actor, payload, origin=origin)
    except HTTPException as exc:
        record_mutation_failure(
            actor,
            payload,
            origin=origin,
            error=exc.detail,
            conflict=exc.status_code == 409,
        )
        raise
    except Exception as exc:
        record_mutation_failure(
            actor,
            payload,
            origin=origin,
            error=str(exc),
            conflict=False,
        )
        raise
