"""Native digital asset custody and full-stack workspace API."""

from __future__ import annotations

import hashlib
import json
import re
from html import escape
from pathlib import Path
from typing import Annotated
from uuid import UUID

import httpx
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
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.services.deployment_acceptance import accept_workspace_deployment
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    add_version,
    archive_asset,
    artifact_descriptor,
    artifact_upload_target,
    asset_detail,
    authenticate_workspace_key,
    create_asset,
    create_deployment,
    create_workspace,
    database_health,
    database_schema,
    issue_workspace_key,
    list_workspace_keys,
    list_workspace_records,
    list_workspace_relation_rows,
    migrate_workspace_database_to_hdd,
    provision_database,
    public_workspace_status,
    put_workspace_record,
    put_workspace_relation_row,
    record_custody,
    register_artifact,
    resize_workspace_quota,
    revoke_workspace_key,
    rotate_workspace_primary_key,
    storage_pool_overview,
    switch_workspace_code_storage,
    update_asset,
    upgrade_workspace_runtime,
    workspace_asset_identity,
    workspace_info,
    workspace_usage,
)
from app.services.hosting_fabric import (
    apply_fabric_resource,
    fabric_manifest,
    observe_action,
    observe_fabric,
)
from app.services.hosting_requirements import (
    CONTRACT_FILENAME,
    STANDARD_FILENAME,
    contract_path,
    requirements_bundle,
    standard_path,
)
from app.services.object_storage import (
    object_store_for_provider,
    object_store_read_candidates,
)
from app.services.source_packages import inspect_source_archive
from app.services.workspace_deployments import (
    activate_workspace_deployment,
    active_workspace_runtime,
    cancel_workspace_deployment,
    configure_workspace_runtime,
    list_workspace_deployments,
    list_workspace_sources,
    observe_workspace_deployment,
    probe_workspace_storage,
    register_workspace_source,
    repair_workspace_deployment,
    request_workspace_deployment,
    workspace_source_download_target,
    workspace_source_upload_target,
)

router = APIRouter(tags=["digital-asset-hosting"])
_bearer = HTTPBearer(auto_error=False)
_GUIDE_FILENAME = "digital-asset-custody-guide-2.1.zh-TW.md"
_CLI_PATH = Path(__file__).resolve().parents[1] / "downloads" / "dam.py"


async def _active_runtime_response(
    tenant_slug: str,
    workspace_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings,
) -> Response | None:
    route = active_workspace_runtime(tenant_slug, workspace_key)
    if route is None:
        return None
    if route["kind"] == "static":
        root = (settings.hosted_runtime_data_root / str(route["runtime_rel_path"])).resolve()
        try:
            root.relative_to(settings.hosted_runtime_data_root.resolve())
        except ValueError:
            raise HTTPException(status_code=503, detail="Runtime route is unsafe") from None
        target = (root / runtime_path).resolve() if runtime_path else root / "index.html"
        try:
            target.relative_to(root)
        except ValueError:
            raise HTTPException(status_code=404, detail="Hosted file not found") from None
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file() and not Path(runtime_path).suffix:
            target = root / "index.html"
        if not target.is_file():
            raise HTTPException(status_code=404, detail="Hosted file not found")
        return FileResponse(
            target,
            headers={
                "X-Warehouse-Deployment": str(route["deployment_id"]),
                "X-Content-Type-Options": "nosniff",
            },
        )
    upstreams = [
        str(value).rstrip("/")
        for value in (route.get("internal_urls") or [route["internal_url"]])
        if value
    ]
    affinity = hashlib.sha256(
        (
            f"{request.client.host if request.client else ''}|{request.method}|"
            f"{runtime_path}|{request.url.query}"
        ).encode()
    ).digest()
    start_index = int.from_bytes(affinity[:4], "big") % len(upstreams)
    upstreams = upstreams[start_index:] + upstreams[:start_index]
    suffix = "/" + runtime_path.lstrip("/")
    if request.url.query:
        suffix += "?" + request.url.query
    forwarded_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower()
        in {
            "accept",
            "accept-language",
            "content-type",
            "range",
            "user-agent",
            "if-none-match",
            "if-modified-since",
        }
    }
    forwarded_headers["x-forwarded-prefix"] = f"/assets/{tenant_slug}/{workspace_key}"
    forwarded_headers["x-forwarded-host"] = request.headers.get("host", "")
    upstream = None
    selected_internal_url = upstreams[0]
    request_body = await request.body()
    last_error = None
    documentation_location = None
    async with httpx.AsyncClient(timeout=60, follow_redirects=False) as client:
        for internal_url in upstreams:
            try:
                upstream = await client.request(
                    request.method,
                    internal_url + suffix,
                    headers=forwarded_headers,
                    content=request_body,
                )
                selected_internal_url = internal_url
                break
            except httpx.HTTPError as exc:
                last_error = exc
        if (
            upstream is not None
            and request.method == "GET"
            and not runtime_path
            and not request.url.query
            and upstream.status_code == 404
        ):
            try:
                documentation = await client.request(
                    "GET",
                    selected_internal_url + "/docs",
                    headers=forwarded_headers,
                )
                if 200 <= documentation.status_code < 400:
                    documentation_location = (
                        f"/assets/{tenant_slug}/{workspace_key}/docs"
                    )
            except httpx.HTTPError:
                pass
    if upstream is None:
        raise HTTPException(status_code=502, detail="Hosted Runtime is unavailable") from last_error
    if documentation_location is not None:
        return RedirectResponse(
            documentation_location,
            status_code=307,
            headers={"X-Warehouse-Deployment": str(route["deployment_id"])},
        )
    response_headers = {
        key: value
        for key, value in upstream.headers.items()
        if key.lower()
        in {
            "content-type",
            "content-language",
            "cache-control",
            "etag",
            "last-modified",
            "location",
            "accept-ranges",
            "content-range",
        }
    }
    location = response_headers.get("location")
    if location and location.startswith(selected_internal_url):
        response_headers["location"] = (
            f"/assets/{tenant_slug}/{workspace_key}" + location.removeprefix(selected_internal_url)
        )
    response_headers["X-Warehouse-Deployment"] = str(route["deployment_id"])
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
    )


@router.api_route(
    "/assets/{tenant_slug}/{workspace_key}/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def hosted_workspace_entry(
    tenant_slug: str,
    workspace_key: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    """Permanent public entry: status before deploy, application after deploy."""

    runtime = await _active_runtime_response(
        tenant_slug,
        workspace_key,
        "",
        request,
        settings,
    )
    if runtime is not None:
        return runtime
    if request.method != "GET":
        raise HTTPException(status_code=404, detail="Hosted Runtime is not active")

    observed = public_workspace_status(tenant_slug, workspace_key)
    entry = observed["entry"]
    application_url = entry.get("application_url")
    if application_url and application_url != entry["url"]:
        return RedirectResponse(str(application_url), status_code=307)
    asset = observed["asset"]
    workspace = observed["workspace"]
    verified = observed["verified_facts"]
    runtime_type = str(workspace.get("runtime_type") or "static")
    runtime_status = str(workspace.get("runtime_status") or "planned")
    quota_mb = int(workspace.get("storage_quota_bytes") or 0) // (1024 * 1024)
    used_mb = int(workspace.get("storage_used_bytes") or 0) / (1024 * 1024)
    storage_profile = workspace.get("storage") if isinstance(workspace.get("storage"), dict) else {}
    code_storage = (
        storage_profile.get("code") if isinstance(storage_profile.get("code"), dict) else {}
    )
    code_medium = str(code_storage.get("medium") or "hdd").upper()
    database_medium = str(workspace.get("database_medium") or "—").upper()
    source_label = "源碼已接入" if verified.get("source_available") else "等待上傳源碼"
    deployment = observed.get("deployment")
    deployment = deployment if isinstance(deployment, dict) else {}
    failure_reason = str(deployment.get("failure_reason") or "")
    status_label = (
        "應用已上線"
        if verified.get("application_deployed")
        else "部署失敗，入口仍保留"
        if deployment.get("status") == "failed"
        else "托管入口已保留"
    )
    diagnostic_html = (
        '<div class="cell"><div class="k">DIAGNOSTIC</div>'
        '<div class="v">源碼與 Runtime 不相容<br>請重新自動判定並部署</div></div>'
        if failure_reason == "runtime_contract_mismatch"
        else '<div class="cell"><div class="k">DIAGNOSTIC</div>'
        '<div class="v">部署未完成<br>請檢查最新部署記錄</div></div>'
        if deployment.get("status") == "failed"
        else ""
    )
    safe_title = escape(str(asset.get("name") or workspace_key))
    safe_company = escape(str(observed["tenant"].get("name") or tenant_slug))
    safe_asset_no = escape(str(asset.get("asset_no") or ""))
    safe_entry = escape(str(entry["url"]))
    html = f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{safe_title} · Warehouse OS 2.1</title>
<style>
:root{{--ink:#111;--paper:#f3f2ee;--line:#c9c7c0;--muted:#6c6a65;--signal:#ff4d00}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--paper);color:var(--ink)}}
body{{font-family:Arial,"Noto Sans TC",sans-serif}}
main{{min-height:100vh;display:grid;grid-template-rows:auto 1fr auto}}
main{{padding:28px clamp(22px,5vw,72px)}}
header,footer{{display:flex;justify-content:space-between;gap:20px}}
header,footer{{border-bottom:1px solid var(--line);padding-bottom:14px}}
header,footer{{font:700 11px/1.2 monospace;letter-spacing:.12em}}
header,footer{{text-transform:uppercase}}
section{{align-self:center;max-width:900px;padding:64px 0}}
.eyebrow{{font:700 11px/1.2 monospace;letter-spacing:.14em}}
.eyebrow{{color:var(--signal)}}
h1{{font-size:clamp(48px,10vw,118px);line-height:.86}}
h1{{letter-spacing:-.07em;margin:18px 0 32px;overflow-wrap:anywhere}}
.state{{display:inline-flex;border:1px solid var(--ink);border-radius:999px}}
.state{{padding:8px 12px;font:700 11px monospace}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}}
.grid{{gap:1px;background:var(--line);border:1px solid var(--line);margin-top:44px}}
.cell{{background:var(--paper);padding:18px;min-height:110px}}
.k{{font:700 9px monospace;letter-spacing:.12em;color:var(--muted)}}
.v{{font:650 17px/1.25 monospace;margin-top:15px;overflow-wrap:anywhere}}
a{{color:inherit}}
footer{{border:0;border-top:1px solid var(--line);padding-top:14px}}
footer{{padding-bottom:0;color:var(--muted)}}
</style></head><body><main>
<header><span>WAREHOUSE OS 2.1 · HOSTING</span><span>{safe_company}</span></header>
<section>
<div class="eyebrow">PERMANENT WORKSPACE ENTRY · {safe_asset_no}</div>
<h1>{safe_title}</h1>
<span class="state">{status_label}</span>
<div class="grid">
<div class="cell"><div class="k">ENTRY URL</div>
<div class="v"><a href="{safe_entry}">{safe_entry}</a></div></div>
<div class="cell"><div class="k">RUNTIME</div>
<div class="v">{escape(runtime_type)} · {escape(runtime_status)}</div></div>
<div class="cell"><div class="k">SOURCE</div>
<div class="v">{source_label}</div></div>
<div class="cell"><div class="k">STORAGE</div>
<div class="v">CODE {escape(code_medium)} · DATA HDD ·
DB {escape(database_medium)}<br>{used_mb:.2f} / {quota_mb} MB</div></div>
{diagnostic_html}
</div></section>
<footer><span>固定入口不因重新部署而改變</span>
<span>每次可向 AI 申請 +512 MB</span></footer>
</main></body></html>"""
    return HTMLResponse(
        html,
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.api_route(
    "/assets/{tenant_slug}/{workspace_key}/{runtime_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def hosted_workspace_runtime_path(
    tenant_slug: str,
    workspace_key: str,
    runtime_path: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> Response:
    response = await _active_runtime_response(
        tenant_slug,
        workspace_key,
        runtime_path,
        request,
        settings,
    )
    if response is None:
        raise HTTPException(status_code=404, detail="Hosted Runtime is not active")
    return response


def _guide_path() -> Path:
    source_root = Path(__file__).resolve().parents[3]
    packaged_root = Path(__file__).resolve().parents[2]
    for candidate in (
        source_root / "docs" / _GUIDE_FILENAME,
        packaged_root / "docs" / _GUIDE_FILENAME,
    ):
        if candidate.is_file():
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Digital asset custody guide is unavailable",
    )


def _cli_source() -> str:
    if not _CLI_PATH.is_file():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dam.py is unavailable",
        )
    return _CLI_PATH.read_text(encoding="utf-8")


def _external_base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


def _require_asset_read(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.read",
        "assets.manage",
        "asset_mgmt.read",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _require_asset_manage(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.manage",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _require_ai_use(actor: ActorContext) -> None:
    if actor.role_level >= 10 or "ai.use" in actor.permissions:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def workspace_credential(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> WorkspaceCredential:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Workspace key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authenticate_workspace_key(
        credentials.credentials,
        signing_secret=settings.integration_secret,
    )


# Stable customer/deployed-program Data API.  The signed workspace key carries
# the tenant/workspace locator, then the credential is checked inside that
# tenant's RLS transaction.  No cross-tenant database scan is used.


@router.get("/api/workspaces/v1/info")
def customer_workspace_info(
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return workspace_info(credential)


@router.get("/api/workspaces/v1/usage")
def customer_workspace_usage(
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return workspace_usage(credential)


@router.get("/api/workspaces/v1/fabric/manifest")
def customer_hosting_fabric_manifest(
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("infra:read")
    return {"ok": True, "manifest": fabric_manifest()}


@router.get("/api/workspaces/v1/fabric")
def customer_hosting_fabric(
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return observe_fabric(credential)


@router.post("/api/workspaces/v1/fabric/resources")
def customer_hosting_fabric_apply(
    payload: dict[str, object] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return apply_fabric_resource(
        credential,
        payload,
        settings,
        idempotency_key=idempotency_key,
    )


@router.get("/api/workspaces/v1/fabric/actions/{action_id}")
def customer_hosting_fabric_action(
    action_id: UUID,
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return observe_action(credential, action_id)


@router.put("/api/workspaces/v1/runtime")
@router.post("/api/workspaces/v1/runtime", include_in_schema=False)
def customer_workspace_runtime_configure(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return configure_workspace_runtime(credential, payload, settings)


@router.post("/api/workspaces/v1/storage/probe")
def customer_workspace_storage_probe(
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Repair legacy bindings and prove the selected storage is actually writable."""

    return probe_workspace_storage(credential, settings)


@router.post(
    "/api/workspaces/v1/sources/upload",
    status_code=status.HTTP_201_CREATED,
)
@router.post(
    "/api/workspaces/v1/source",
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False,
)
def customer_source_upload(
    file: UploadFile = File(...),
    version_no: str | None = Form(default=None),
    component: str | None = Form(default=None),
    expected_sha256: str | None = Form(default=None),
    content_sha256: str | None = Header(default=None, alias="Content-SHA256"),
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Upload, verify and atomically register one immutable source version."""

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
    return register_workspace_source(
        credential,
        stored,
        filename=file.filename,
        content_type=file.content_type,
        version_no=version_no,
        component_name=component,
        archive=archive,
    )


@router.get("/api/workspaces/v1/sources")
def customer_sources(
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return list_workspace_sources(credential)


@router.get("/api/workspaces/v1/sources/{source_id}/download")
def customer_source_download(
    source_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    descriptor = workspace_source_download_target(credential, source_id)
    path = None
    for store in object_store_read_candidates(settings, str(descriptor["storage_provider"])):
        candidate = store.path_for(str(descriptor["object_key"]))
        if candidate.is_file():
            path = candidate
            break
    if path is None:
        raise HTTPException(status_code=404, detail="Source object is unavailable")
    return FileResponse(
        path,
        media_type=str(descriptor.get("content_type") or "application/octet-stream"),
        filename=str(descriptor.get("filename") or path.name),
        headers={
            "Content-SHA256": str(descriptor["sha256"]),
            "X-Warehouse-Source-Version": str(descriptor["id"]),
        },
    )


@router.post("/api/workspaces/v1/deployments", status_code=status.HTTP_202_ACCEPTED)
def customer_deployment_request(
    payload: dict[str, object] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    configured = configure_workspace_runtime(
        credential,
        {**payload, "deploy": False},
        settings,
    )
    component = configured["component"]
    runtime_contract = configured["runtime"]
    deployment_payload = {
        **payload,
        "source_version_id": configured["source_version_id"],
        "component": component["component_name"],
        "runtime_profile": runtime_contract["runtime_profile"],
        "entrypoint": payload.get("entrypoint") or component.get("entrypoint"),
        "build_command": payload.get("build_command") or component.get("build_command"),
        "start_command": payload.get("start_command") or component.get("start_command"),
    }
    requested = request_workspace_deployment(
        credential,
        deployment_payload,
        idempotency_key=idempotency_key,
        settings=settings,
    )
    return {
        "ok": True,
        "deployment": requested["deployment"],
        "runtime_contract": runtime_contract,
        "component": component,
        "source_version_id": configured["source_version_id"],
        "auto_configured_runtime": runtime_contract["selection"] == "detected",
        "next_action": "observe_deployment",
    }


@router.get("/api/workspaces/v1/deployments")
def customer_deployments(
    limit: int = Query(default=50, ge=1, le=200),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return list_workspace_deployments(credential, limit=limit)


def _deployment_reference(value: str) -> UUID | int:
    try:
        return UUID(value)
    except ValueError:
        if value.isdigit() and int(value) > 0:
            return int(value)
        raise HTTPException(status_code=422, detail="Invalid deployment id") from None


@router.get("/api/workspaces/v1/deployments/{deployment_id}")
@router.get("/api/workspaces/v1/deployments/{deployment_id}/events")
def customer_deployment_observe(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return observe_workspace_deployment(credential, _deployment_reference(deployment_id))


@router.get("/api/workspaces/v1/deployments/{deployment_id}/logs")
def customer_deployment_logs(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("logs:read")
    observed = observe_workspace_deployment(credential, _deployment_reference(deployment_id))
    return {
        "ok": True,
        "deployment_id": deployment_id,
        "status": observed["deployment"]["status"],
        "events": observed["events"],
        "log_excerpt": (observed["deployment"].get("result") or {}).get("log_excerpt", []),
    }


@router.post("/api/workspaces/v1/deployments/{deployment_id}/cancel")
def customer_deployment_cancel(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return cancel_workspace_deployment(credential, _deployment_reference(deployment_id))


@router.post(
    "/api/workspaces/v1/deployments/{deployment_id}/repair",
    status_code=status.HTTP_202_ACCEPTED,
)
def customer_deployment_repair(
    deployment_id: str,
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return repair_workspace_deployment(
        credential,
        _deployment_reference(deployment_id),
        payload,
    )


@router.post("/api/workspaces/v1/deployments/{deployment_id}/activate")
@router.post("/api/workspaces/v1/deployments/{deployment_id}/rollback")
def customer_deployment_activate(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    return activate_workspace_deployment(credential, _deployment_reference(deployment_id))


@router.post("/api/workspaces/v1/deployments/{deployment_id}/accept")
def customer_deployment_accept(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return accept_workspace_deployment(
        credential,
        _deployment_reference(deployment_id),
        settings,
    )


@router.get("/api/workspaces/v1/database/schema")
def customer_database_schema(
    database: str | None = Query(default=None),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:read")
    return database_schema(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        logical_name=database,
    )


@router.get("/api/workspaces/v1/database/health")
def customer_database_health(
    database: str | None = Query(default=None),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:read")
    return database_health(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        logical_name=database,
    )


@router.get("/api/workspaces/v1/database/tables/{schema_name}/{table_name}/rows")
def customer_relation_rows(
    schema_name: str,
    table_name: str,
    database: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:read")
    return list_workspace_relation_rows(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        schema_name=schema_name,
        table_name=table_name,
        logical_name=database,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/api/workspaces/v1/database/tables/{schema_name}/{table_name}/rows/{record_key}"
)
def customer_relation_row_put(
    schema_name: str,
    table_name: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    database: str | None = Query(default=None),
    expected_version: str | None = Query(default=None, max_length=80),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:write")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return put_workspace_relation_row(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        schema_name=schema_name,
        table_name=table_name,
        record_key=record_key,
        payload=data,
        expected_version=expected_version,
        credential=credential,
        logical_name=database,
    )


@router.get("/api/workspaces/v1/data/{collection}")
def customer_data_list(
    collection: str,
    database: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:read")
    return list_workspace_records(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        collection=collection,
        logical_name=database,
        limit=limit,
        offset=offset,
    )


@router.put("/api/workspaces/v1/data/{collection}/{record_key}")
def customer_data_put(
    collection: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    database: str | None = Query(default=None),
    expected_version: int | None = Query(default=None, ge=0),
    credential: WorkspaceCredential = Depends(workspace_credential),
) -> dict[str, object]:
    credential.require("data:write")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
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


# Authenticated company control plane.


@router.get("/api/digital-assets/guide")
def digital_asset_guide(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Return the canonical 2.1 guide to the AI plus formal downloads."""

    _require_ai_use(actor)
    content = _guide_path().read_text(encoding="utf-8")
    return {
        "ok": True,
        "version": "2.1",
        "content": content,
        "downloads": [
            {
                "label": "下載《數字資產託管指南 2.1》",
                "url": "/api/digital-assets/guide/download",
                "filename": _GUIDE_FILENAME,
            },
            {
                "label": "下載 dam.py 2.1",
                "url": "/api/digital-assets/cli",
                "filename": "dam.py",
            },
        ],
        "note": (
            "請依 content 的 2.1 原生契約回答；不要引用 2.0 的 dak_、SQLite 或 /api/dam/v1 路徑。"
        ),
    }


@router.get("/api/digital-assets/hosting-standard")
def digital_asset_hosting_standard(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Return the formal application contract plus direct downloads to the AI."""

    _require_ai_use(actor)
    try:
        return requirements_bundle(public_surface="digital-assets")
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hosting developer standard is unavailable",
        ) from exc


@router.get("/api/storage/v1/pools")
def hosted_storage_pools(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Return sanitized capacity and policy facts without filesystem paths."""

    return storage_pool_overview(actor)


@router.get("/api/digital-assets/guide/download")
def digital_asset_guide_download() -> FileResponse:
    return FileResponse(
        _guide_path(),
        media_type="text/markdown; charset=utf-8",
        filename=_GUIDE_FILENAME,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/api/digital-assets/hosting-standard/download")
def digital_asset_hosting_standard_download() -> FileResponse:
    try:
        path = standard_path()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hosting developer standard is unavailable",
        ) from exc
    return FileResponse(
        path,
        media_type="text/markdown; charset=utf-8",
        filename=STANDARD_FILENAME,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/api/digital-assets/hosting-contract.json")
def digital_asset_hosting_contract_download() -> FileResponse:
    try:
        path = contract_path()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Hosting contract is unavailable",
        ) from exc
    return FileResponse(
        path,
        media_type="application/json; charset=utf-8",
        filename=CONTRACT_FILENAME,
        headers={"Cache-Control": "public, max-age=300"},
    )


@router.get("/api/digital-assets/cli")
def digital_asset_cli_download(request: Request) -> Response:
    source = _cli_source().replace(
        '"__WAREHOUSE_BASE__"',
        json.dumps(_external_base_url(request), ensure_ascii=False),
    )
    return Response(
        content=source,
        media_type="text/x-python; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="dam.py"',
            "Cache-Control": "public, max-age=300",
        },
    )


@router.post("/api/digital-assets", status_code=status.HTTP_201_CREATED)
@router.post("/api/digital-assets/create", status_code=status.HTTP_201_CREATED)
def digital_asset_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_asset(actor, payload)


@router.post("/api/digital-assets/provision", status_code=status.HTTP_201_CREATED)
def digital_asset_provision(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Provision a native 2.1 asset, workspace, Data API and its primary key."""

    created = create_asset(actor, payload)
    workspace_result = create_workspace(actor, created["asset"]["uuid"], payload)
    key_result = issue_workspace_key(
        actor,
        workspace_result["workspace"]["uuid"],
        payload,
        signing_secret=settings.integration_secret,
        key_kind="primary",
    )
    return {
        "ok": True,
        "asset": created["asset"],
        "custody_event": created["custody_event"],
        "workspace": workspace_result["workspace"],
        "components": workspace_result["components"],
        "database": workspace_result["database"],
        "storage": workspace_result["storage"],
        **{key: value for key, value in key_result.items() if key != "ok"},
        "cli_download": "/api/digital-assets/cli",
        "guide_download": "/api/digital-assets/guide/download",
    }


@router.post("/api/digital-assets/upload", status_code=status.HTTP_201_CREATED)
def digital_asset_upload_contract(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    asset_ref = payload.get("asset_ref") or payload.get("asset_id") or payload.get("id")
    workspace_ref = payload.get("workspace_ref") or payload.get("workspace")
    workspace_identity: dict[str, object] | None = None
    if workspace_ref not in (None, ""):
        workspace_identity = workspace_asset_identity(actor, workspace_ref)
        workspace_asset = workspace_identity["asset"]
        if asset_ref not in (None, ""):
            supplied_asset = asset_detail(actor, asset_ref)["asset"]
            if supplied_asset["uuid"] != workspace_asset["uuid"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "asset_workspace_target_mismatch",
                        "asset_ref": str(asset_ref),
                        "workspace_ref": str(workspace_ref),
                    },
                )
        asset_ref = workspace_asset["uuid"]
    created: dict[str, object] | None = None
    if asset_ref in (None, ""):
        if payload.get("create_new_asset") is not True:
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "explicit_new_asset_intent_required",
                    "message": (
                        "Upload must target asset_ref/workspace_ref unless the user "
                        "explicitly intends a new asset"
                    ),
                    "accepted_intent": {"create_new_asset": True},
                },
            )
        declared_hash = (
            str(
                payload.get("artifact_sha256")
                or payload.get("artifact_hash")
                or payload.get("sha256")
                or ""
            )
            .strip()
            .lower()
        )
        # Validate before creating the master record.  A failed artifact
        # registration must never leave an orphan "*-source" asset behind.
        if not re.fullmatch(r"[a-f0-9]{64}", declared_hash):
            raise HTTPException(
                status_code=422,
                detail=(
                    "A new asset upload requires a valid 64-character SHA-256; "
                    "for an existing asset pass asset_ref or workspace_ref"
                ),
            )
        created = create_asset(actor, payload)
        asset_ref = created["asset"]["uuid"]
    upload_kind = str(payload.get("upload_type") or payload.get("artifact_kind") or "package")
    version = None
    version_payload = dict(payload)
    if (
        upload_kind in {"package", "source", "frontend", "backend"}
        or payload.get("version_no")
        or payload.get("version")
    ):
        version = add_version(actor, asset_ref, version_payload)
        version_payload["version_id"] = version["version"]["uuid"]
    artifact = register_artifact(actor, asset_ref, version_payload)
    workspace = None
    if bool(payload.get("create_workspace")):
        workspace = create_workspace(actor, asset_ref, payload)
    return {
        "ok": True,
        "asset": (
            created["asset"] if created is not None else asset_detail(actor, asset_ref)["asset"]
        ),
        **artifact,
        "version": version["version"] if version else None,
        "workspace": workspace["workspace"] if workspace else None,
        "database": workspace["database"] if workspace else None,
        "target_observation": (
            workspace_identity.get("world_observation") if workspace_identity is not None else None
        ),
    }


@router.get("/api/digital-assets/{asset_ref}")
def digital_asset_show(
    asset_ref: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return asset_detail(actor, asset_ref)


@router.post("/api/digital-assets/{asset_ref}/update")
def digital_asset_update(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return update_asset(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/archive")
def digital_asset_archive(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return archive_asset(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/version")
def digital_asset_version_add(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return add_version(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/artifacts")
def digital_asset_artifact_register(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return register_artifact(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/artifacts/upload")
def digital_asset_artifact_upload(
    asset_ref: str,
    file: UploadFile = File(...),
    artifact_kind: str = Form(default="package"),
    version_id: str | None = Form(default=None),
    expected_sha256: str | None = Form(default=None),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _require_asset_manage(actor)
    target = artifact_upload_target(actor, asset_ref, artifact_kind)
    remaining = target.get("remaining_bytes")
    max_bytes = settings.asset_max_upload_bytes
    if isinstance(remaining, int):
        max_bytes = min(max_bytes, remaining)
    store = object_store_for_provider(settings, str(target["storage_provider"]))
    stored = store.put_stream(
        tenant_id=actor.tenant_id,
        stream=file.file,
        max_bytes=max_bytes,
        expected_sha256=expected_sha256,
    )
    return register_artifact(
        actor,
        asset_ref,
        {
            "artifact_kind": artifact_kind,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": stored.size_bytes,
            "sha256": stored.sha256,
            "storage_provider": stored.provider_key,
            "object_key": stored.object_key,
            "storage_role": target["storage_role"],
            "storage_pool_key": target["storage_pool_key"],
            "version_id": version_id,
        },
    )


@router.get("/api/digital-assets/{asset_ref}/artifacts/{artifact_id}/download")
def digital_asset_artifact_download(
    asset_ref: str,
    artifact_id: str,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    descriptor = artifact_descriptor(actor, asset_ref, artifact_id)
    path = None
    for store in object_store_read_candidates(settings, str(descriptor["storage_provider"])):
        candidate = store.path_for(str(descriptor["object_key"]))
        if candidate.is_file():
            path = candidate
            break
    if path is None:
        raise HTTPException(status_code=404, detail="Artifact object is unavailable")
    return FileResponse(
        path,
        media_type=str(descriptor.get("content_type") or "application/octet-stream"),
        filename=str(descriptor.get("filename") or path.name),
    )


@router.post("/api/digital-assets/{asset_ref}/custody")
@router.post("/api/digital-assets/{asset_ref}/custody/events")
def digital_asset_custody_add(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return record_custody(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/workspace")
@router.post("/api/digital-assets/{asset_ref}/workspaces")
def digital_asset_workspace_create(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_workspace(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/workspace-quota")
def digital_asset_workspace_quota(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return resize_workspace_quota(actor, asset_ref, payload)


@router.post("/api/digital-assets/{asset_ref}/database")
def digital_asset_database_create(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    detail = asset_detail(actor, asset_ref)["asset"]
    workspaces = detail.get("workspaces") if isinstance(detail, dict) else []
    if not workspaces:
        result = create_workspace(actor, asset_ref, {**payload, "no_database": False})
        return {"ok": True, "workspace": result["workspace"], "database": result["database"]}
    workspace = workspaces[0]
    return provision_database(actor, workspace["uuid"], payload)


@router.post("/api/digital-assets/{asset_ref}/deploy")
def digital_asset_deploy(
    asset_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_deployment(actor, asset_ref, payload)


@router.post("/api/workspaces/{workspace_ref}/databases")
def workspace_database_create(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return provision_database(actor, workspace_ref, payload)


@router.post("/api/workspaces/{workspace_ref}/database/migrate-hdd")
def workspace_database_migrate_hdd(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return migrate_workspace_database_to_hdd(actor, workspace_ref, payload)


@router.get("/api/workspaces/{workspace_ref}/database/schema")
def workspace_database_schema(
    workspace_ref: str,
    database: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_read(actor)
    return database_schema(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        logical_name=database,
    )


@router.get("/api/workspaces/{workspace_ref}/database/health")
def workspace_database_health(
    workspace_ref: str,
    database: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_read(actor)
    return database_health(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        logical_name=database,
    )


@router.get(
    "/api/workspaces/{workspace_ref}/database/tables/{schema_name}/{table_name}/rows"
)
def workspace_relation_rows(
    workspace_ref: str,
    schema_name: str,
    table_name: str,
    database: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_read(actor)
    return list_workspace_relation_rows(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        schema_name=schema_name,
        table_name=table_name,
        logical_name=database,
        limit=limit,
        offset=offset,
    )


@router.put(
    "/api/workspaces/{workspace_ref}/database/tables/"
    "{schema_name}/{table_name}/rows/{record_key}"
)
def workspace_relation_row_put(
    workspace_ref: str,
    schema_name: str,
    table_name: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    database: str | None = Query(default=None),
    expected_version: str | None = Query(default=None, max_length=80),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_manage(actor)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return put_workspace_relation_row(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        schema_name=schema_name,
        table_name=table_name,
        record_key=record_key,
        payload=data,
        expected_version=expected_version,
        actor=actor,
        logical_name=database,
    )


@router.get("/api/workspaces/{workspace_ref}/data/{collection}")
def workspace_data_list(
    workspace_ref: str,
    collection: str,
    database: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_read(actor)
    return list_workspace_records(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        collection=collection,
        logical_name=database,
        limit=limit,
        offset=offset,
    )


@router.put("/api/workspaces/{workspace_ref}/data/{collection}/{record_key}")
def workspace_data_put(
    workspace_ref: str,
    collection: str,
    record_key: str,
    payload: dict[str, object] = Body(default={}),
    database: str | None = Query(default=None),
    expected_version: Annotated[int | None, Query(ge=0)] = None,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_asset_manage(actor)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return put_workspace_record(
        tenant_id=actor.tenant_id,
        workspace_ref=workspace_ref,
        collection=collection,
        record_key=record_key,
        payload=data,
        expected_version=expected_version,
        actor=actor,
        logical_name=database,
    )


@router.post("/api/workspaces/{workspace_ref}/keys")
def workspace_key_issue(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return issue_workspace_key(
        actor,
        workspace_ref,
        payload,
        signing_secret=settings.integration_secret,
        key_kind="delegated",
    )


@router.post("/api/workspaces/{workspace_ref}/runtime")
def workspace_runtime_upgrade(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return upgrade_workspace_runtime(actor, workspace_ref, payload)


@router.post("/api/workspaces/{workspace_ref}/storage")
def workspace_code_storage_switch(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return switch_workspace_code_storage(actor, workspace_ref, payload)


@router.get("/api/workspaces/{workspace_ref}/keys")
def workspace_keys_list(
    workspace_ref: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_workspace_keys(actor, workspace_ref)


@router.post("/api/workspaces/{workspace_ref}/keys/primary/rotate")
def workspace_primary_key_rotate(
    workspace_ref: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return rotate_workspace_primary_key(
        actor,
        workspace_ref,
        payload,
        signing_secret=settings.integration_secret,
    )


@router.post("/api/workspaces/{workspace_ref}/keys/{credential_ref}/revoke")
def workspace_key_revoke(
    workspace_ref: str,
    credential_ref: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return revoke_workspace_key(actor, workspace_ref, credential_ref)
