"""Authenticated Browser Runtime API and restricted worker exchange."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Query
from fastapi.responses import FileResponse

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.browser_runtime import (
    artifact_file,
    cancel_run,
    capabilities,
    create_journey,
    create_run,
    list_journeys,
    list_runs,
    run_detail,
    worker_session_token,
)

router = APIRouter(tags=["browser-runtime"])


@router.get("/api/browser-runtime/capabilities")
def browser_capabilities(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, object]:
    return capabilities(actor, settings)


@router.get("/api/browser-runtime/journeys")
def browser_journeys(
    actor: Annotated[ActorContext, Depends(current_actor)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    return list_journeys(actor, limit)


@router.post("/api/browser-runtime/journeys", status_code=201)
def browser_journey_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_journey(actor, payload)


@router.get("/api/browser-runtime/runs")
def browser_runs(
    actor: Annotated[ActorContext, Depends(current_actor)],
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, object]:
    return list_runs(actor, limit)


@router.post("/api/browser-runtime/runs", status_code=202)
def browser_run_create(
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    return create_run(actor, payload, settings)


@router.get("/api/browser-runtime/runs/{run_id}")
def browser_run_show(
    run_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return run_detail(actor, run_id)


@router.post("/api/browser-runtime/runs/{run_id}/cancel")
def browser_run_cancel(
    run_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
) -> dict[str, object]:
    return cancel_run(actor, run_id)


@router.get("/api/browser-runtime/artifacts/{artifact_id}")
def browser_artifact_download(
    artifact_id: UUID,
    actor: Annotated[ActorContext, Depends(current_actor)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> FileResponse:
    path, content_type = artifact_file(actor, artifact_id, settings)
    return FileResponse(path, media_type=content_type, filename=path.name)


@router.post("/api/browser-runtime/internal/runs/{run_id}/session", include_in_schema=False)
def browser_worker_session(
    run_id: UUID,
    settings: Annotated[Settings, Depends(get_settings)],
    worker_token: Annotated[str, Header(alias="X-Warehouse-Browser-Worker")],
    worker_id: Annotated[str, Header(alias="X-Warehouse-Browser-Worker-ID")],
    tenant_id: Annotated[UUID, Header(alias="X-Warehouse-Tenant-ID")],
) -> dict[str, object]:
    return worker_session_token(run_id, tenant_id, worker_id, worker_token, settings)
