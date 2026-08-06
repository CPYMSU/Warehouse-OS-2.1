"""Backward-compatible intelligent hosting routes on the autonomous key boundary."""

from __future__ import annotations

import json
from typing import Annotated
from uuid import UUID

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
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import current_actor
from app.api.workspace_autonomy import autonomous_workspace_credential
from app.core.config import Settings, get_settings
from app.services.intelligent_hosting import (
    HostingPrincipal,
    cancel_session,
    create_session,
    credential_for_actor,
    execute_message,
    get_session,
    list_events,
    record_session_diagnostic,
    record_source_attached,
    session_credential,
)
from app.services.object_storage import object_store_for_provider
from app.services.source_packages import inspect_source_archive
from app.services.source_uploads import (
    SOURCE_UPLOAD_CHUNK_BYTES,
    complete_source_upload,
    create_source_upload,
    put_source_upload_part,
    source_upload_status,
)
from app.services.workspace_autonomy import (
    SOURCE_UPLOAD_HEADROOM_BYTES,
    ensure_capacity,
    provision_idempotently,
)
from app.services.workspace_deployments import (
    list_workspace_sources,
    register_workspace_source,
    workspace_source_upload_target,
)

router = APIRouter(tags=["intelligent-hosting-compat"])
_bearer = HTTPBearer(auto_error=False)


def _session_upload_response(
    result: dict[str, object],
    session_id: str,
) -> dict[str, object]:
    upload_id = str(result["upload_id"])
    return {
        **result,
        "endpoints": {
            "part": (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/"
                f"{upload_id}/parts/{{part_no}}"
            ),
            "complete": (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/"
                f"{upload_id}/complete"
            ),
            "status": (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/{upload_id}"
            ),
            "attach": f"/api/hosting/v2/sessions/{session_id}/sources/attach",
        },
    }


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
        workspace_credential = autonomous_workspace_credential(credentials, settings)
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


def _provision_for_account(
    principal: HostingPrincipal,
    provision: dict[str, object],
    settings: Settings,
) -> tuple[object, dict[str, object] | None]:
    if principal.actor is None:
        raise HTTPException(status_code=401, detail="Account session is required")
    result = provision_idempotently(principal.actor, provision, settings)
    credential = credential_for_actor(
        principal.actor,
        result["workspace"]["uuid"],
    )
    if result.get("api_key"):
        return credential, {
            "provisioned": {
                "asset": result.get("asset"),
                "workspace": result.get("workspace"),
                "components": result.get("components", []),
                "database": result.get("database"),
                "storage": result.get("storage"),
            },
            "credential": {
                key: value
                for key, value in result.items()
                if key
                in {
                    "credential_id",
                    "key_id",
                    "key_kind",
                    "is_primary",
                    "label",
                    "api_key",
                    "api_key_hint",
                    "scopes",
                    "expires_at",
                    "base_url",
                    "plaintext_exposed_once",
                }
            },
        }
    return credential, None


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
        provision = payload.get("provision")
        if isinstance(provision, dict):
            credential, one_time = _provision_for_account(principal, provision, settings)
        else:
            if principal.actor is None:
                raise HTTPException(status_code=401, detail="Account session is required")
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
    after_sequence = max([int(event["sequence"]) for event in before["events"]] or [0])
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


def _upload_size(file: UploadFile) -> int:
    try:
        position = file.file.tell()
        file.file.seek(0, 2)
        size = int(file.file.tell())
        file.file.seek(position)
        return size
    except (AttributeError, OSError, ValueError):
        return 0


@router.post(
    "/api/hosting/v2/sessions/{session_id}/source-uploads",
    status_code=status.HTTP_201_CREATED,
)
def intelligent_hosting_source_upload_create(
    session_id: str,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    result = create_source_upload(
        credential,
        payload,
        idempotency_key=idempotency_key,
        settings=settings,
    )
    return _session_upload_response(result, session_id)


@router.put(
    "/api/hosting/v2/sessions/{session_id}/source-uploads/"
    "{upload_id}/parts/{part_no}"
)
async def intelligent_hosting_source_upload_part(
    session_id: str,
    upload_id: UUID,
    part_no: int,
    request: Request,
    response: Response,
    content_sha256: str = Header(alias="Content-SHA256"),
    content_length: int | None = Header(default=None, alias="Content-Length"),
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    if content_length is not None and content_length > SOURCE_UPLOAD_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Upload part exceeds the chunk limit")
    content = await request.body()
    if len(content) > SOURCE_UPLOAD_CHUNK_BYTES:
        raise HTTPException(status_code=413, detail="Upload part exceeds the chunk limit")
    result = put_source_upload_part(
        credential,
        upload_id,
        part_no,
        content,
        expected_sha256=content_sha256,
        settings=settings,
    )
    return _session_upload_response(result, session_id)


@router.post(
    "/api/hosting/v2/sessions/{session_id}/source-uploads/{upload_id}/complete",
    status_code=status.HTTP_202_ACCEPTED,
)
def intelligent_hosting_source_upload_complete(
    session_id: str,
    upload_id: UUID,
    response: Response,
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    result = complete_source_upload(credential, upload_id, settings=settings)
    return _session_upload_response(result, session_id)


@router.get(
    "/api/hosting/v2/sessions/{session_id}/source-uploads/{upload_id}"
)
def intelligent_hosting_source_upload_status(
    session_id: str,
    upload_id: UUID,
    response: Response,
    principal: HostingPrincipal = Depends(hosting_principal),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    return _session_upload_response(
        source_upload_status(credential, upload_id),
        session_id,
    )


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
    content_sha256: Annotated[str | None, Header(alias="Content-SHA256")] = None,
    principal: HostingPrincipal = Depends(hosting_principal),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    try:
        credential.require("deploy:write")
        upload_bytes = _upload_size(file)
        if upload_bytes > settings.asset_max_upload_bytes:
            raise HTTPException(status_code=413, detail="Source upload exceeds host limit")
        if credential.key_kind == "primary":
            ensure_capacity(
                credential,
                required_free_bytes=upload_bytes + SOURCE_UPLOAD_HEADROOM_BYTES,
                reason="hosting_session_source_upload",
            )
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
            max_uncompressed_bytes=max(
                remaining,
                stored.size_bytes,
                min(settings.asset_max_upload_bytes * 200, 64 * 1024 * 1024 * 1024),
            ),
        )
        if credential.key_kind == "primary":
            ensure_capacity(
                credential,
                required_free_bytes=(
                    stored.size_bytes + archive.uncompressed_bytes + SOURCE_UPLOAD_HEADROOM_BYTES
                ),
                reason="hosting_session_source_materialization",
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
        diagnosis = record_session_diagnostic(principal, session_id, "source.upload", exc)
        if isinstance(exc, HTTPException):
            detail = exc.detail
            if isinstance(detail, dict):
                detail = {**detail, "diagnosis": diagnosis}
            else:
                detail = {"message": str(detail), "diagnosis": diagnosis}
            raise HTTPException(status_code=exc.status_code, detail=detail) from exc
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Source upload failed",
                "diagnosis": diagnosis,
                "retryable": True,
                "next_action": "repair the reported source.upload stage and resume this session",
            },
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


@router.post("/api/hosting/v2/sessions/{session_id}/sources/attach")
def intelligent_hosting_source_attach(
    session_id: str,
    response: Response,
    payload: dict[str, object] = Body(default={}),
    principal: HostingPrincipal = Depends(hosting_principal),
) -> dict[str, object]:
    """Attach a source already verified by the resumable workspace data plane."""

    response.headers["Cache-Control"] = "no-store"
    _row, credential = session_credential(principal, session_id)
    source_ref = str(payload.get("source_version_id") or payload.get("source_ref") or "").strip()
    if not source_ref:
        raise HTTPException(status_code=422, detail="source_version_id is required")
    sources = list_workspace_sources(credential)["sources"]
    source = next(
        (
            item
            for item in sources
            if source_ref in {str(item.get("uuid") or ""), str(item.get("id") or "")}
        ),
        None,
    )
    if source is None:
        raise HTTPException(status_code=404, detail="Verified workspace source not found")
    source_result = {
        "ok": True,
        "idempotent_replay": True,
        "source": source,
        "artifact": source.get("artifact"),
        "archive": {
            "validated": True,
            "signals": {"hosting_contract": source.get("hosting_contract")},
        },
    }
    session_result = record_source_attached(principal, session_id, source_result)
    return {
        "ok": True,
        "source": source_result,
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
