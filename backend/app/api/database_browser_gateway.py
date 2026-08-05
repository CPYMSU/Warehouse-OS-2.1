"""Standalone database provisioning and browser-safe Data API routes."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.database_browser_gateway import (
    BrowserCredential,
    BrowserProject,
    authenticate_browser_access,
    authorize_collection,
    browser_access_configuration,
    configure_browser_access,
    database_onboarding_bundle,
    issue_browser_session,
    list_database_projects,
    normalize_origin,
    public_project_configuration,
    reconcile_database_project_registry,
    require_project_origin,
)
from app.services.digital_asset_hosting import (
    create_asset,
    create_workspace,
    delete_workspace_record,
    get_workspace_record,
    list_workspace_records,
    put_workspace_record,
)

router = APIRouter(tags=["database-browser-gateway"])
_bearer = HTTPBearer(auto_error=False)
_SDK_PATH = Path(__file__).resolve().parents[1] / "downloads" / "warehouse-data.js"


def _project_and_origin(
    project_key: str,
    origin: Annotated[str | None, Header(alias="Origin")] = None,
    settings: Settings = Depends(get_settings),
) -> tuple[BrowserProject, str]:
    project = require_project_origin(project_key, origin, settings=settings)
    return project, normalize_origin(origin, settings=settings)


def _browser_credential(
    context: tuple[BrowserProject, str] = Depends(_project_and_origin),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> BrowserCredential:
    project, origin = context
    return authenticate_browser_access(
        project,
        credentials.credentials if credentials is not None else None,
        origin=origin,
        settings=settings,
    )


@router.get("/api/database-projects")
def standalone_database_projects_list(
    limit: int = Query(default=100, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return list_database_projects(actor, settings=settings, limit=limit)


@router.post("/api/database-projects", status_code=status.HTTP_201_CREATED)
def standalone_database_project_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Create a managed database project without requiring a hosted Runtime."""

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    provision_payload = {
        **payload,
        "asset_kind": payload.get("asset_kind") or "data",
        "runtime_type": "static",
        "service_plan": payload.get("service_plan") or "managed",
        "metadata": {**metadata, "service_kind": "standalone_database"},
        "no_database": False,
    }
    created = create_asset(actor, provision_payload)
    workspace_result = create_workspace(actor, created["asset"]["uuid"], provision_payload)
    browser_payload = (
        payload.get("browser_access") if isinstance(payload.get("browser_access"), dict) else None
    )
    browser_project = None
    if browser_payload is not None or "allowed_origins" in payload:
        browser_payload = {
            **(browser_payload or {}),
            **(
                {"allowed_origins": payload["allowed_origins"]}
                if "allowed_origins" in payload and "allowed_origins" not in (browser_payload or {})
                else {}
            ),
        }
        browser_payload.setdefault("enabled", True)
        configured = configure_browser_access(
            actor,
            workspace_result["workspace"]["uuid"],
            browser_payload,
            settings=settings,
        )
        browser_project = configured["project"]
    return {
        "ok": True,
        "service_kind": "standalone_database",
        "asset": created["asset"],
        "workspace": workspace_result["workspace"],
        "database": workspace_result["database"],
        "browser_project": browser_project,
        "runtime_required": False,
        "runtime_deployed": False,
    }


@router.post("/api/database-projects/reconcile")
def standalone_database_project_registry_reconcile(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Repair unambiguous legacy registry gaps without provisioning new data."""

    return reconcile_database_project_registry(actor)


@router.get("/api/workspaces/{workspace_ref}/database/onboarding")
def workspace_database_onboarding(
    workspace_ref: str,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return database_onboarding_bundle(actor, workspace_ref, settings=settings)


@router.get("/api/workspaces/{workspace_ref}/database/browser-access")
def workspace_browser_access_get(
    workspace_ref: str,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return browser_access_configuration(actor, workspace_ref, settings=settings)


@router.put("/api/workspaces/{workspace_ref}/database/browser-access")
def workspace_browser_access_put(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return configure_browser_access(actor, workspace_ref, payload, settings=settings)


@router.get("/api/database-gateway/v1/sdk.js")
def database_browser_sdk() -> Response:
    if not _SDK_PATH.is_file():
        raise HTTPException(status_code=503, detail="Browser database SDK is unavailable")
    return Response(
        _SDK_PATH.read_text(encoding="utf-8"),
        media_type="application/javascript; charset=utf-8",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=300",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.options("/api/database-gateway/v1/projects/{project_key}")
@router.options("/api/database-gateway/v1/projects/{project_key}/{remaining_path:path}")
def database_browser_preflight(
    project_key: str,
    remaining_path: str = "",
    context: tuple[BrowserProject, str] = Depends(_project_and_origin),
) -> Response:
    del project_key, remaining_path, context
    return Response(status_code=204)


@router.get("/api/database-gateway/v1/projects/{project_key}")
def database_browser_project(
    context: tuple[BrowserProject, str] = Depends(_project_and_origin),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    project, _ = context
    return public_project_configuration(project, settings=settings)


@router.post("/api/database-gateway/v1/projects/{project_key}/sessions")
def database_browser_session(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    context: tuple[BrowserProject, str] = Depends(_project_and_origin),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    project, origin = context
    request_identity = request.client.host if request.client is not None else "unknown"
    return issue_browser_session(
        project,
        origin=origin,
        refresh_token=payload.get("refresh_token"),
        request_identity=request_identity,
        settings=settings,
    )


@router.get("/api/database-gateway/v1/projects/{project_key}/data/{collection}")
def database_browser_collection_list(
    collection: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    credential: BrowserCredential = Depends(_browser_credential),
) -> dict[str, object]:
    owner_id = authorize_collection(credential, collection, "read")
    return list_workspace_records(
        tenant_id=credential.project.tenant_id,
        workspace_ref=credential.project.workspace_id,
        collection=collection,
        limit=limit,
        offset=offset,
        owner_id=owner_id,
    )


@router.get("/api/database-gateway/v1/projects/{project_key}/data/{collection}/{record_key}")
def database_browser_record_get(
    collection: str,
    record_key: str,
    credential: BrowserCredential = Depends(_browser_credential),
) -> dict[str, object]:
    owner_id = authorize_collection(credential, collection, "read")
    return get_workspace_record(
        tenant_id=credential.project.tenant_id,
        workspace_ref=credential.project.workspace_id,
        collection=collection,
        record_key=record_key,
        owner_id=owner_id,
    )


@router.put("/api/database-gateway/v1/projects/{project_key}/data/{collection}/{record_key}")
def database_browser_record_put(
    collection: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    expected_version: int | None = Query(default=None, ge=0),
    credential: BrowserCredential = Depends(_browser_credential),
) -> dict[str, object]:
    owner_id = authorize_collection(credential, collection, "write")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return put_workspace_record(
        tenant_id=credential.project.tenant_id,
        workspace_ref=credential.project.workspace_id,
        collection=collection,
        record_key=record_key,
        payload=data,
        expected_version=expected_version,
        owner_id=owner_id,
    )


@router.delete("/api/database-gateway/v1/projects/{project_key}/data/{collection}/{record_key}")
def database_browser_record_delete(
    collection: str,
    record_key: str,
    credential: BrowserCredential = Depends(_browser_credential),
) -> dict[str, object]:
    owner_id = authorize_collection(credential, collection, "write")
    return delete_workspace_record(
        tenant_id=credential.project.tenant_id,
        workspace_ref=credential.project.workspace_id,
        collection=collection,
        record_key=record_key,
        owner_id=owner_id,
    )
