"""Complete `/api/workspaces/v1/*` compatibility on the autonomous key verifier."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.api.workspace_autonomy import autonomous_workspace_credential
from app.core.config import Settings, get_settings
from app.services.deployment_acceptance import accept_workspace_deployment
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    database_schema,
    list_workspace_records,
    workspace_info,
    workspace_usage,
)
from app.services.hosting_fabric import (
    apply_fabric_resource,
    fabric_manifest,
    observe_action,
    observe_fabric,
    set_workspace_database_policy,
    workspace_database_control,
)
from app.services.object_storage import object_store_read_candidates
from app.services.workspace_deployments import (
    activate_workspace_deployment,
    cancel_workspace_deployment,
    configure_workspace_runtime,
    list_workspace_deployments,
    list_workspace_sources,
    observe_workspace_deployment,
    probe_workspace_storage,
    repair_workspace_deployment,
    request_workspace_deployment,
    resolve_declared_workspace_job,
    workspace_source_download_target,
)

router = APIRouter(tags=["workspace-v1-compat"])


def _deployment_reference(value: str) -> UUID | int:
    try:
        return UUID(value)
    except ValueError:
        if value.isdigit() and int(value) > 0:
            return int(value)
        raise HTTPException(status_code=422, detail="Invalid deployment id") from None


@router.get("/api/workspaces/v1/info")
def customer_workspace_info(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return workspace_info(credential)


@router.get("/api/workspaces/v1/usage")
def customer_workspace_usage(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return workspace_usage(credential)


@router.get("/api/workspaces/v1/fabric/manifest")
def customer_hosting_fabric_manifest(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    credential.require("infra:read")
    return {"ok": True, "manifest": fabric_manifest()}


@router.get("/api/workspaces/v1/fabric")
def customer_hosting_fabric(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return observe_fabric(credential)


@router.post("/api/workspaces/v1/fabric/resources")
def customer_hosting_fabric_apply(
    payload: dict[str, object] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
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
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return observe_action(credential, action_id)


@router.put("/api/workspaces/v1/runtime")
@router.post("/api/workspaces/v1/runtime", include_in_schema=False)
def customer_workspace_runtime_configure(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return configure_workspace_runtime(credential, payload, settings)


@router.post("/api/workspaces/v1/storage/probe")
def customer_workspace_storage_probe(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return probe_workspace_storage(credential, settings)


@router.get("/api/workspaces/v1/sources")
def customer_sources(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return list_workspace_sources(credential)


@router.get("/api/workspaces/v1/sources/{source_id}/download")
def customer_source_download(
    source_id: str,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> FileResponse:
    descriptor = workspace_source_download_target(credential, source_id)
    path = None
    for store in object_store_read_candidates(
        settings, str(descriptor["storage_provider"])
    ):
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
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
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
    if runtime_contract["runtime_type"] == "job":
        deployment_payload.update({"execution_mode": "job", "activate": False})
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


@router.post("/api/workspaces/v1/jobs", status_code=status.HTTP_202_ACCEPTED)
def customer_job_request(
    payload: dict[str, object] = Body(default={}),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Run a bounded one-shot command without changing production traffic."""

    if payload.get("job") not in (None, ""):
        payload = resolve_declared_workspace_job(credential, payload, settings)
    command = str(payload.get("command") or payload.get("start_command") or "").strip()
    if not command:
        raise HTTPException(status_code=422, detail="A one-shot job command is required")
    result = customer_deployment_request(
        {
            **payload,
            "runtime_type": "job",
            "start_command": command,
            "execution_mode": "job",
            "activate": False,
        },
        idempotency_key,
        credential,
        settings,
    )
    result["job"] = result.pop("deployment")
    result["next_action"] = "observe_job"
    return result


@router.get("/api/workspaces/v1/deployments")
def customer_deployments(
    limit: int = Query(default=50, ge=1, le=200),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return list_workspace_deployments(credential, limit=limit)


@router.get("/api/workspaces/v1/deployments/{deployment_id}")
@router.get("/api/workspaces/v1/deployments/{deployment_id}/events")
def customer_deployment_observe(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return observe_workspace_deployment(
        credential, _deployment_reference(deployment_id)
    )


@router.get("/api/workspaces/v1/deployments/{deployment_id}/logs")
def customer_deployment_logs(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    credential.require("logs:read")
    observed = observe_workspace_deployment(
        credential, _deployment_reference(deployment_id)
    )
    return {
        "ok": True,
        "deployment_id": deployment_id,
        "status": observed["deployment"]["status"],
        "events": observed["events"],
        "log_excerpt": (observed["deployment"].get("result") or {}).get(
            "log_excerpt", []
        ),
        "diagnostic": (observed["deployment"].get("result") or {}).get(
            "diagnostic"
        ),
    }


@router.post("/api/workspaces/v1/deployments/{deployment_id}/cancel")
def customer_deployment_cancel(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return cancel_workspace_deployment(
        credential, _deployment_reference(deployment_id)
    )


@router.post(
    "/api/workspaces/v1/deployments/{deployment_id}/repair",
    status_code=status.HTTP_202_ACCEPTED,
)
def customer_deployment_repair(
    deployment_id: str,
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
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
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    return activate_workspace_deployment(
        credential, _deployment_reference(deployment_id)
    )


@router.post("/api/workspaces/v1/deployments/{deployment_id}/accept")
def customer_deployment_accept(
    deployment_id: str,
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
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
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    credential.require("data:read")
    return database_schema(
        tenant_id=credential.tenant_id,
        workspace_ref=credential.workspace_id,
        logical_name=database,
    )


@router.get("/api/workspaces/v1/database/control")
def customer_database_control(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Observe exact database, backup and release-gate evidence with a workspace key."""

    return workspace_database_control(credential, settings)


@router.post("/api/workspaces/v1/database/reconcile")
def customer_database_reconcile(
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Reconcile provider-owned PostgreSQL capabilities without server access."""

    return workspace_database_control(credential, settings, reconcile=True)


@router.put("/api/workspaces/v1/database/policy")
def customer_database_policy(
    payload: dict[str, object] = Body(default={}),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
) -> dict[str, object]:
    """Select platform, external, workspace-managed or no-database lifecycle."""

    return set_workspace_database_policy(credential, payload)


@router.get("/api/workspaces/v1/data/{collection}")
def customer_data_list(
    collection: str,
    database: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    credential: WorkspaceCredential = Depends(autonomous_workspace_credential),
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
