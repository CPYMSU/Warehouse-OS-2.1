"""Workspace-root API overrides and self-service control surface."""

from __future__ import annotations

import hashlib
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    Header,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.db.session import tenant_session
from app.services.digital_asset_hosting import WorkspaceCredential, put_workspace_record
from app.services.object_storage import object_store_for_provider
from app.services.source_packages import inspect_source_archive
from app.services.workspace_autonomy import (
    SOURCE_UPLOAD_HEADROOM_BYTES,
    autonomy_manifest,
    ensure_capacity,
    estimate_record_write_bytes,
    issue_delegated_key,
    list_keys,
    provision_idempotently,
    resize_capacity,
    revoke_delegated_key,
    rotate_primary_key,
)
from app.services.workspace_deployments import (
    register_workspace_source,
    workspace_source_upload_target,
)

router = APIRouter(tags=["workspace-autonomy"])
_bearer = HTTPBearer(auto_error=False)


def autonomous_workspace_credential(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WorkspaceCredential:
    """Authenticate a workspace key with the database as expiry authority."""

    if credentials is None or not credentials.credentials.startswith("wak_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        claims = jwt.decode(
            token.removeprefix("wak_"),
            settings.integration_secret,
            algorithms=["HS256"],
            audience="warehouse-workspace",
            issuer="warehouse-os",
            options={"verify_exp": False},
        )
        tenant_id = UUID(str(claims["tenant_id"]))
        workspace_id = UUID(str(claims["workspace_id"]))
        credential_id = UUID(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid workspace key") from exc

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT c.id,c.workspace_id,c.label,c.scopes,c.key_kind,
                           c.parent_credential_id,c.expires_at
                    FROM digital_asset.api_credentials AS c
                    JOIN digital_asset.workspaces AS w
                      ON w.tenant_id=c.tenant_id AND w.id=c.workspace_id
                    WHERE c.id=:credential_id AND c.workspace_id=:workspace_id
                      AND c.token_hash=:token_hash AND c.revoked_at IS NULL
                      AND w.status='active'
                      AND (
                        c.key_kind='primary'
                        OR c.expires_at IS NULL
                        OR c.expires_at > now()
                      )
                    """
                ),
                {
                    "credential_id": credential_id,
                    "workspace_id": workspace_id,
                    "token_hash": token_hash,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(
                status_code=401, detail="Workspace key is revoked, expired or invalid"
            )
        if str(claims.get("key_kind") or row["key_kind"]) != str(row["key_kind"]):
            raise HTTPException(status_code=401, detail="Workspace key kind mismatch")
        session.execute(
            text("UPDATE digital_asset.api_credentials SET last_used_at=now() WHERE id=:id"),
            {"id": credential_id},
        )
    return WorkspaceCredential(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        credential_id=credential_id,
        scopes=frozenset(str(scope) for scope in row["scopes"]),
        label=str(row["label"]),
        key_kind=str(row["key_kind"]),
        parent_credential_id=row["parent_credential_id"],
    )


@router.get("/api/workspaces/v1/autonomy")
def workspace_autonomy(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return autonomy_manifest(credential)


@router.get("/api/workspaces/v1/keys")
def workspace_key_list(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return list_keys(credential)


@router.post("/api/workspaces/v1/keys", status_code=status.HTTP_201_CREATED)
def workspace_key_issue(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return issue_delegated_key(credential, payload, settings)


@router.post("/api/workspaces/v1/keys/primary/rotate", status_code=status.HTTP_201_CREATED)
def workspace_primary_key_rotate(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return rotate_primary_key(credential, payload, settings)


@router.post("/api/workspaces/v1/keys/{credential_id}/revoke")
def workspace_key_revoke(
    credential_id: UUID,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return revoke_delegated_key(credential, credential_id)


@router.post("/api/workspaces/v1/quota")
def workspace_quota_resize(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return resize_capacity(credential, payload)


@router.put("/api/workspaces/v1/data/{collection}/{record_key}")
def autonomous_data_put(
    collection: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    database: str | None = None,
    expected_version: int | None = None,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    """Write data and transparently grow a primary workspace once if needed."""

    credential.require("data:write")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    try:
        return put_workspace_record(
            tenant_id=credential.tenant_id,
            workspace_ref=credential.workspace_id,
            collection=collection,
            record_key=record_key,
            payload=data,
            expected_version=expected_version,
            credential=credential,
            logical_name=database,
        )
    except HTTPException as exc:
        if exc.status_code != 507 or credential.key_kind != "primary":
            raise
    ensure_capacity(
        credential,
        required_free_bytes=estimate_record_write_bytes(data),
        reason="automatic_primary_data_write",
    )
    return put_workspace_record(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        collection=collection,
        record_key=record_key,
        payload=data,
        expected_version=expected_version,
        credential=credential,
        logical_name=database,
    )


def _upload_size(file: UploadFile) -> int:
    try:
        position = file.file.tell()
        file.file.seek(0, 2)
        size = int(file.file.tell())
        file.file.seek(position)
        return size
    except (AttributeError, OSError, ValueError):
        return 0


@router.post("/api/workspaces/v1/sources/upload", status_code=status.HTTP_201_CREATED)
@router.post(
    "/api/workspaces/v1/source",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def autonomous_source_upload(
    file: UploadFile = File(...),
    version_no: str | None = Form(default=None),
    component: str | None = Form(default=None),
    expected_sha256: str | None = Form(default=None),
    content_sha256: str | None = Header(default=None, alias="Content-SHA256"),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Upload source without forcing a primary-key caller through manual resizing."""

    credential.require("deploy:write")
    upload_bytes = _upload_size(file)
    if upload_bytes > settings.asset_max_upload_bytes:
        raise HTTPException(status_code=413, detail="Source upload exceeds the host upload limit")
    if credential.key_kind == "primary":
        ensure_capacity(
            credential,
            required_free_bytes=upload_bytes + SOURCE_UPLOAD_HEADROOM_BYTES,
            reason="automatic_primary_source_upload",
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
    archive_limit = max(
        remaining,
        stored.size_bytes,
        min(settings.asset_max_upload_bytes * 200, 64 * 1024 * 1024 * 1024),
    )
    archive = inspect_source_archive(
        store.path_for(stored.object_key),
        max_uncompressed_bytes=archive_limit,
    )
    if credential.key_kind == "primary":
        ensure_capacity(
            credential,
            required_free_bytes=(
                stored.size_bytes + archive.uncompressed_bytes + SOURCE_UPLOAD_HEADROOM_BYTES
            ),
            reason="automatic_primary_source_materialization",
        )
    return register_workspace_source(
        credential,
        stored,
        filename=file.filename,
        content_type=file.content_type,
        version_no=version_no,
        component_name=component,
        archive=archive,
    )


@router.post("/api/digital-assets/provision", status_code=status.HTTP_201_CREATED)
def idempotent_digital_asset_provision(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return provision_idempotently(actor, payload, settings)
