"""One conversational API for humans, the platform secretary and terminal AIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import current_actor
from app.core.config import Settings, get_settings
from app.services.digital_asset_hosting import authenticate_workspace_key
from app.services.hosting_requirements import (
    CONTRACT_FILENAME,
    STANDARD_FILENAME,
    contract_path,
    requirements_bundle,
    standard_path,
)
from app.services.intelligent_hosting import (
    HostingPrincipal,
    assistant_manifest,
    cancel_session,
    create_session,
    credential_for_actor,
    execute_message,
    get_session,
    list_events,
    provision_for_session,
    record_session_diagnostic,
    record_source_attached,
    session_credential,
)
from app.services.object_storage import object_store_for_provider
from app.services.source_packages import inspect_source_archive
from app.services.workspace_deployments import (
    register_workspace_source,
    workspace_source_upload_target,
)

router = APIRouter(tags=["intelligent-hosting"])
_bearer = HTTPBearer(auto_error=False)
_CLI_PATH = Path(__file__).resolve().parents[1] / "downloads" / "dam.py"
_GUIDE_FILENAME = "digital-asset-custody-guide-2.1.zh-TW.md"


def _guide_path() -> Path:
    source_root = Path(__file__).resolve().parents[3]
    packaged_root = Path(__file__).resolve().parents[2]
    for candidate in (
        source_root / "docs" / _GUIDE_FILENAME,
        packaged_root / "docs" / _GUIDE_FILENAME,
    ):
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=503, detail="dm-guide.md is unavailable")


def _cli_source(request: Request) -> str:
    if not _CLI_PATH.is_file():
        raise HTTPException(status_code=503, detail="dm.py is unavailable")
    base_url = str(request.base_url).rstrip("/")
    return _CLI_PATH.read_text(encoding="utf-8").replace(
        '"__WAREHOUSE_BASE__"', json.dumps(base_url, ensure_ascii=False)
    )


def hosting_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> HostingPrincipal:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account session or workspace API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials.strip()
    if token.startswith("wak_"):
        workspace_credential = authenticate_workspace_key(
            token, signing_secret=settings.integration_secret
        )
        workspace_credential.require("workspace:read")
        return HostingPrincipal(
            tenant_id=workspace_credential.tenant_id,
            auth_kind="workspace_key",
            credential=workspace_credential,
        )
    actor = current_actor(request, credentials, settings)
    return HostingPrincipal(
        tenant_id=actor.tenant_id,
        auth_kind=actor.auth_kind,
        actor=actor,
    )


@router.get("/api/hosting/v2/manifest")
def intelligent_hosting_manifest() -> dict[str, object]:
    return {"ok": True, "manifest": assistant_manifest()}


@router.get("/api/hosting/v2/kit")
def intelligent_hosting_kit(request: Request) -> dict[str, object]:
    manifest = assistant_manifest()
    return {
        "ok": True,
        "base_url": str(request.base_url).rstrip("/"),
        "manifest": manifest,
        "downloads": manifest["downloads"],
        "quick_start": [
            "Download dm.py and dm-guide.md.",
            "Set WAREHOUSE_WORKSPACE_KEY to the asset's wak_ key.",
            "Run: python3 dm.py agent manifest",
            "Start one hosting session and keep its session_id for every retry.",
        ],
    }


@router.get("/api/hosting/v2/dm.py")
def intelligent_hosting_cli(request: Request) -> Response:
    return Response(
        content=_cli_source(request),
        media_type="text/x-python; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="dm.py"',
            "Cache-Control": "public, max-age=300",
        },
    )


@router.get("/api/hosting/v2/dm-guide.md")
def intelligent_hosting_guide() -> FileResponse:
    return FileResponse(
        _guide_path(),
        media_type="text/markdown; charset=utf-8",
        filename="dm-guide.md",
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/api/hosting/v2/requirements")
def intelligent_hosting_requirements() -> dict[str, object]:
    try:
        return requirements_bundle(public_surface="hosting")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=503, detail="Hosting requirements are unavailable") from exc


@router.get("/api/hosting/v2/developer-standard.md")
def intelligent_hosting_developer_standard() -> FileResponse:
    try:
        path = standard_path()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Hosting developer standard is unavailable",
        ) from exc
    return FileResponse(
        path,
        media_type="text/markdown; charset=utf-8",
        filename=STANDARD_FILENAME,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/api/hosting/v2/contract.json")
def intelligent_hosting_contract() -> FileResponse:
    try:
        path = contract_path()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail="Hosting contract is unavailable") from exc
    return FileResponse(
        path,
        media_type="application/json; charset=utf-8",
        filename=CONTRACT_FILENAME,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.post("/api/hosting/v2/sessions", status_code=status.HTTP_201_CREATED)
def intelligent_hosting_session_create(
    response: Response,
    payload: dict[str, object] = Body(default={}),
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    one_time: dict[str, object] | None = None
    if principal.credential is not None:
        credential = principal.credential
    else:
        if principal.actor is None:
            raise HTTPException(status_code=401, detail="Account session is required")
        provision = payload.get("provision")
        if isinstance(provision, dict):
            credential, _identity, one_time = provision_for_session(
                principal.actor, provision, settings
            )
        else:
            workspace_ref = payload.get("workspace_ref")
            if workspace_ref in (None, ""):
                raise HTTPException(
                    status_code=422,
                    detail="workspace_ref or provision is required for an account session",
                )
            credential = credential_for_actor(principal.actor, workspace_ref)
    result = create_session(principal, credential, payload)
    if bool(payload.get("execute")):
        result = execute_message(
            principal,
            result["session"]["id"],
            {
                "message": str(payload.get("message") or payload.get("goal") or ""),
                "desired_state": payload.get("desired_state") or {},
                "execute": True,
            },
            settings,
        )
    if one_time is not None:
        result["one_time"] = one_time
    return result


@router.get("/api/hosting/v2/sessions/{session_id}")
def intelligent_hosting_session_get(
    session_id: str,
    response: Response,
    refresh: bool = Query(default=True),
    principal: HostingPrincipal = Depends(hosting_principal),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return get_session(principal, session_id, refresh=refresh)


@router.post("/api/hosting/v2/sessions/{session_id}/messages")
def intelligent_hosting_message(
    session_id: str,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return execute_message(principal, session_id, payload, settings)


@router.post("/api/hosting/v2/sessions/{session_id}/messages/stream")
def intelligent_hosting_message_stream(
    session_id: str,
    payload: dict[str, object] = Body(default={}),
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    before = list_events(principal, session_id, after=0)
    after_sequence = max(
        [int(event["sequence"]) for event in before["events"]] or [0]
    )
    result = execute_message(principal, session_id, payload, settings)
    emitted = list_events(principal, session_id, after=after_sequence)

    def stream():
        for event in emitted["events"]:
            yield json.dumps(
                {"event": event["event_type"], "payload": event},
                ensure_ascii=False,
                default=str,
            ) + "\n"
        yield json.dumps(
            {"event": "final", "payload": result},
            ensure_ascii=False,
            default=str,
        ) + "\n"

    return StreamingResponse(
        stream(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/hosting/v2/sessions/{session_id}/events")
def intelligent_hosting_events(
    session_id: str,
    response: Response,
    after: int = Query(default=0, ge=0),
    principal: HostingPrincipal = Depends(hosting_principal),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return list_events(principal, session_id, after=after)


@router.post(
    "/api/hosting/v2/sessions/{session_id}/sources",
    status_code=status.HTTP_201_CREATED,
)
def intelligent_hosting_source_upload(
    session_id: str,
    response: Response,
    file: UploadFile = File(...),
    version_no: str | None = Form(default=None),
    component: str | None = Form(default=None),
    expected_sha256: str | None = Form(default=None),
    content_sha256: Annotated[
        str | None, Header(alias="Content-SHA256")
    ] = None,
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    try:
        credential.require("deploy:write")
        target = workspace_source_upload_target(credential, settings)
        remaining = int(target["remaining_bytes"])
        if remaining <= 0:
            raise HTTPException(status_code=507, detail="Workspace quota is exhausted")
        store = object_store_for_provider(settings, str(target["storage_provider"]))
        stored = store.put_stream(
            tenant_id=credential.tenant_id,
            stream=file.file,
            max_bytes=min(settings.asset_max_upload_bytes, remaining),
            expected_sha256=expected_sha256 or content_sha256,
        )
        archive = inspect_source_archive(
            store.path_for(stored.object_key),
            max_uncompressed_bytes=max(remaining, stored.size_bytes),
        )
        source = register_workspace_source(
            credential,
            stored,
            filename=file.filename,
            content_type=file.content_type,
            version_no=version_no,
            component_name=component,
            archive=archive,
        )
    except Exception as exc:
        diagnosis = record_session_diagnostic(
            principal, session_id, "source.upload", exc
        )
        raise HTTPException(
            status_code=(exc.status_code if isinstance(exc, HTTPException) else 500),
            detail={"message": "Source upload failed", "diagnosis": diagnosis},
        ) from exc
    session_result = record_source_attached(principal, session_id, source)
    return {
        "ok": True,
        "source": source,
        "session": session_result["session"],
        "next_action": (
            f"POST /api/hosting/v2/sessions/{session_id}/messages with "
            "desired_state.deployment.state=ready and execute=true"
        ),
    }


@router.post("/api/hosting/v2/sessions/{session_id}/cancel")
def intelligent_hosting_cancel(
    session_id: str,
    response: Response,
    principal: HostingPrincipal = Depends(hosting_principal),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    return cancel_session(principal, session_id)
