"""Workspace-key source custody and deployment data plane.

Every public operation is rooted in the authenticated credential's tenant and
workspace.  No caller-supplied asset/workspace locator can widen that scope.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.db.session import system_session, tenant_session
from app.services.database_release import (
    observe_database_release_gate,
    workspace_database_policy,
)
from app.services.digital_asset_hosting import (
    HDD_POOL_KEY,
    LOCAL_PROVIDER_KEYS,
    SSD_POOL_KEY,
    WORKSPACE_QUOTA_STEP_BYTES,
    WorkspaceCredential,
    _audit,
    _custody_event,
    _json_safe,
    _public_deployment,
    _public_version,
    _workspace_billable_usage,
    _workspace_row,
    workspace_entry_url,
)
from app.services.hosting_compatibility import (
    declared_lifecycle_job,
    manifest_runtime_defaults,
)
from app.services.object_storage import (
    HDD_PROVIDER_KEY,
    SSD_PROVIDER_KEY,
    StoredObject,
    object_store_for_provider,
    object_store_read_candidates,
)
from app.services.pages_runtime import mark_pages_deployment_active, set_pages_deployment_pointer
from app.services.source_packages import SourceArchive, inspect_source_archive

WORKSPACE_RUNTIME_TYPES = frozenset(
    {"auto", "static", "web", "api", "worker", "agent", "job", "container", "compose"}
)
DeploymentReference = UUID | int


def _hosting_manifest(signals: dict[str, object]) -> dict[str, object] | None:
    manifest = signals.get("hosting_manifest")
    return dict(manifest) if isinstance(manifest, dict) else None


def _manifest_runtime_intent(
    payload: dict[str, object],
    signals: dict[str, object],
) -> dict[str, object]:
    """Apply source-declared defaults while preserving explicit caller intent."""

    manifest = _hosting_manifest(signals)
    if manifest is None:
        effective = dict(payload)
        effective.pop("compatibility_contract", None)
        effective.pop("lifecycle_job", None)
        return effective
    effective = manifest_runtime_defaults(manifest)
    effective.update(
        {
            key: value
            for key, value in payload.items()
            if value not in (None, "")
            and not (key in {"runtime_type", "type"} and value == "auto")
        }
    )
    deployment = (
        manifest.get("deployment") if isinstance(manifest.get("deployment"), dict) else {}
    )
    if bool(deployment.get("require_acceptance_before_activation")):
        effective["activate"] = False
    effective["compatibility_contract"] = manifest
    return effective


def _require_manifest_database_policy(
    workspace: dict[str, object],
    manifest: dict[str, object] | None,
) -> None:
    if manifest is None:
        return
    data = manifest.get("data") if isinstance(manifest.get("data"), dict) else {}
    declared = str(data.get("database_policy") or "platform_managed")
    observed = str(workspace_database_policy(workspace.get("config"))["mode"])
    if declared != observed:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "hosting_database_policy_mismatch",
                "declared_policy": declared,
                "workspace_policy": observed,
                "next_action": "align_workspace_database_policy_or_upload_new_source",
            },
        )


def _acceptance_ready_for_activation(deployment: dict[str, object]) -> bool:
    requested = (
        deployment.get("requested_config")
        if isinstance(deployment.get("requested_config"), dict)
        else {}
    )
    contract = (
        requested.get("compatibility_contract")
        if isinstance(requested.get("compatibility_contract"), dict)
        else {}
    )
    deployment_contract = (
        contract.get("deployment") if isinstance(contract.get("deployment"), dict) else {}
    )
    if not bool(deployment_contract.get("require_acceptance_before_activation")):
        return True
    result = deployment.get("result") if isinstance(deployment.get("result"), dict) else {}
    acceptance = (
        result.get("acceptance") if isinstance(result.get("acceptance"), dict) else {}
    )
    return bool(acceptance.get("accepted")) and (
        str(acceptance.get("source_version_id")) == str(deployment.get("source_version_id"))
    ) and (
        str(acceptance.get("contract_digest")) == str(contract.get("contract_digest"))
    )


def _deployment_reference_params(reference: DeploymentReference) -> dict[str, object]:
    return {"deployment_reference": str(reference)}


def _ensure_code_binding(
    session: object,
    credential: WorkspaceCredential,
    workspace: dict[str, object],
) -> dict[str, object]:
    config = workspace.get("config") if isinstance(workspace.get("config"), dict) else {}
    medium = "ssd" if str(config.get("code_storage") or "hdd") == "ssd" else "hdd"
    pool_key = SSD_POOL_KEY if medium == "ssd" else HDD_POOL_KEY
    provider_key = SSD_PROVIDER_KEY if medium == "ssd" else HDD_PROVIDER_KEY
    storage_class = "performance" if medium == "ssd" else "standard"
    pool = (
        session.execute(
            text(
                """
                SELECT pool_key, provider_key, status, enabled, storage_class
                FROM platform.storage_pools WHERE pool_key=:pool_key
                """
            ),
            {"pool_key": pool_key},
        )
        .mappings()
        .one_or_none()
    )
    if (
        pool is None
        or not bool(pool["enabled"])
        or str(pool["status"]) != "ready"
        or str(pool["provider_key"]) != provider_key
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "reason": "code_storage_pool_unavailable",
                "pool_key": pool_key,
                "provider_key": provider_key,
            },
        )
    binding = (
        session.execute(
            text(
                """
                SELECT * FROM digital_asset.storage_bindings
                WHERE workspace_id=:workspace_id AND binding_role='code'
                FOR UPDATE
                """
            ),
            {"workspace_id": workspace["id"]},
        )
        .mappings()
        .one_or_none()
    )
    if binding is None:
        binding = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.storage_bindings(
                      id, tenant_id, workspace_id, provider_key, object_prefix,
                      binding_role, pool_key, storage_class, status, config
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :provider_key, :object_prefix,
                      'code', :pool_key, :storage_class, 'provisioning',
                      CAST(:config AS jsonb)
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": credential.tenant_id,
                    "workspace_id": workspace["id"],
                    "provider_key": provider_key,
                    "object_prefix": (
                        f"tenants/{credential.tenant_id}/workspaces/{workspace['id']}/code/"
                    ),
                    "pool_key": pool_key,
                    "storage_class": storage_class,
                    "config": json.dumps({"medium": medium, "selection": "repaired_default"}),
                },
            )
            .mappings()
            .one()
        )
    elif (
        str(binding["provider_key"]) != provider_key
        or str(binding.get("pool_key") or "") != pool_key
    ):
        binding = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.storage_bindings
                    SET provider_key=:provider_key, pool_key=:pool_key,
                        storage_class=:storage_class, status='provisioning',
                        config=config || CAST(:config AS jsonb)
                    WHERE id=:id RETURNING *
                    """
                ),
                {
                    "id": binding["id"],
                    "provider_key": provider_key,
                    "pool_key": pool_key,
                    "storage_class": storage_class,
                    "config": json.dumps(
                        {"medium": medium, "selection": "repaired_from_workspace_intent"}
                    ),
                },
            )
            .mappings()
            .one()
        )
    return dict(binding)


def _ensure_data_binding(
    session: object,
    credential: WorkspaceCredential,
    workspace: dict[str, object],
) -> dict[str, object]:
    """Repair the invariant that all hosted data objects live on the HDD pool."""

    pool = (
        session.execute(
            text(
                """
                SELECT pool_key, provider_key, status, enabled, storage_class
                FROM platform.storage_pools WHERE pool_key=:pool_key
                """
            ),
            {"pool_key": HDD_POOL_KEY},
        )
        .mappings()
        .one_or_none()
    )
    if (
        pool is None
        or not bool(pool["enabled"])
        or str(pool["status"]) != "ready"
        or str(pool["provider_key"]) != HDD_PROVIDER_KEY
    ):
        raise HTTPException(
            status_code=503,
            detail={
                "reason": "data_storage_pool_unavailable",
                "pool_key": HDD_POOL_KEY,
                "provider_key": HDD_PROVIDER_KEY,
            },
        )
    binding = (
        session.execute(
            text(
                """
                SELECT * FROM digital_asset.storage_bindings
                WHERE workspace_id=:workspace_id AND binding_role='data'
                FOR UPDATE
                """
            ),
            {"workspace_id": workspace["id"]},
        )
        .mappings()
        .one_or_none()
    )
    repair = {
        "medium": "hdd",
        "selection": "enforced_data_tier",
        "enforced": True,
    }
    if binding is None:
        binding = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.storage_bindings(
                      id, tenant_id, workspace_id, provider_key, object_prefix,
                      binding_role, pool_key, storage_class, status, config
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :provider_key, :object_prefix,
                      'data', :pool_key, 'standard', 'provisioning', CAST(:config AS jsonb)
                    ) RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": credential.tenant_id,
                    "workspace_id": workspace["id"],
                    "provider_key": HDD_PROVIDER_KEY,
                    "object_prefix": (
                        f"tenants/{credential.tenant_id}/workspaces/{workspace['id']}/data/"
                    ),
                    "pool_key": HDD_POOL_KEY,
                    "config": json.dumps(repair),
                },
            )
            .mappings()
            .one()
        )
    elif (
        str(binding["provider_key"]) != HDD_PROVIDER_KEY
        or str(binding.get("pool_key") or "") != HDD_POOL_KEY
    ):
        binding = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.storage_bindings
                    SET provider_key=:provider_key, pool_key=:pool_key,
                        storage_class='standard', status='provisioning',
                        config=config || CAST(:config AS jsonb)
                    WHERE id=:id RETURNING *
                    """
                ),
                {
                    "id": binding["id"],
                    "provider_key": HDD_PROVIDER_KEY,
                    "pool_key": HDD_POOL_KEY,
                    "config": json.dumps(repair),
                },
            )
            .mappings()
            .one()
        )
    return dict(binding)


def _probe_storage_binding(
    credential: WorkspaceCredential,
    binding: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Persist a real write/read/delete observation for one binding."""

    try:
        observation = object_store_for_provider(
            settings, str(binding["provider_key"])
        ).probe_writable()
    except (HTTPException, OSError, RuntimeError) as exc:
        failed = {
            "write_probe": "failed",
            "write_probe_error": exc.__class__.__name__,
            "write_probe_at": datetime.now(UTC).isoformat(),
        }
        with tenant_session(credential.tenant_id) as session:
            session.execute(
                text(
                    "UPDATE digital_asset.storage_bindings "
                    "SET status='failed', config=config || CAST(:probe AS jsonb) WHERE id=:id"
                ),
                {"id": binding["id"], "probe": json.dumps(failed)},
            )
        raise HTTPException(
            status_code=503,
            detail={
                "reason": f"{binding['binding_role']}_storage_write_probe_failed",
                "pool_key": binding.get("pool_key"),
                "provider_key": binding.get("provider_key"),
                "observation": failed,
            },
        ) from exc
    passed = {
        "write_probe": "passed",
        "write_probe_at": observation["observed_at"],
        "write_probe_latency_ms": observation["latency_ms"],
    }
    with tenant_session(credential.tenant_id) as session:
        session.execute(
            text(
                "UPDATE digital_asset.storage_bindings "
                "SET status='ready', config=config || CAST(:probe AS jsonb) WHERE id=:id"
            ),
            {"id": binding["id"], "probe": json.dumps(passed)},
        )
    return observation


def probe_workspace_storage(
    credential: WorkspaceCredential,
    settings: Settings,
) -> dict[str, object]:
    """Repair bindings and prove both code and data object stores are writable."""

    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        bindings = [
            _ensure_code_binding(session, credential, workspace),
            _ensure_data_binding(session, credential, workspace),
        ]
    observations = {
        str(binding["binding_role"]): _probe_storage_binding(credential, binding, settings)
        for binding in bindings
    }
    return {
        "ok": True,
        "workspace_id": str(credential.workspace_id),
        "probe": "create_write_fsync_read_delete",
        "bindings_repaired": True,
        "observations": observations,
    }


def workspace_source_upload_target(
    credential: WorkspaceCredential,
    settings: Settings,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        binding = _ensure_code_binding(session, credential, workspace)
        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=workspace["asset_id"],
        )
        quota = int(workspace["storage_quota_bytes"])
    observation = _probe_storage_binding(credential, binding, settings)
    return {
        "workspace_id": str(credential.workspace_id),
        "asset_id": str(workspace["asset_id"]),
        "storage_provider": str(binding["provider_key"]),
        "storage_pool_key": str(binding["pool_key"]),
        "code_medium": str((binding.get("config") or {}).get("medium") or "hdd"),
        "quota_bytes": quota,
        "used_bytes": int(usage["total_bytes"]),
        "remaining_bytes": max(quota - int(usage["total_bytes"]), 0),
        "quota_step_bytes": WORKSPACE_QUOTA_STEP_BYTES,
        "storage_observation": observation,
    }


def register_workspace_source(
    credential: WorkspaceCredential,
    stored: StoredObject,
    *,
    filename: str | None,
    content_type: str | None,
    version_no: str | None,
    component_name: str | None,
    archive: SourceArchive,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        asset_id = workspace["asset_id"]
        binding = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.storage_bindings
                WHERE workspace_id = :workspace_id AND binding_role = 'code'
                  AND status = 'ready'
                """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if binding is None or str(binding["provider_key"]) != stored.provider_key:
            raise HTTPException(
                status_code=409, detail="Workspace code storage changed during upload"
            )
        usage = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=asset_id,
        )
        if int(usage["total_bytes"]) + stored.size_bytes > int(workspace["storage_quota_bytes"]):
            raise HTTPException(
                status_code=507, detail="Workspace quota was exceeded during upload"
            )

        existing = (
            session.execute(
                text(
                    """
                SELECT v.*, ar.id AS artifact_id, ar.filename, ar.size_bytes,
                       ar.storage_provider, ar.object_key, ar.state
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar ON ar.version_id = v.id
                WHERE v.asset_id = :asset_id AND ar.sha256 = :sha256
                  AND ar.storage_role = 'code' AND ar.state = 'verified'
                ORDER BY v.created_at DESC LIMIT 1
                """
                ),
                {"asset_id": asset_id, "sha256": stored.sha256},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            return {
                "ok": True,
                "idempotent_replay": True,
                "source": _public_version(dict(existing)),
                "artifact": _json_safe(
                    {
                        "id": existing["artifact_id"],
                        "filename": existing["filename"],
                        "size_bytes": existing["size_bytes"],
                        "sha256": existing["artifact_sha256"],
                        "state": existing["state"],
                    }
                ),
                "archive": archive.public(),
            }

        normalized_version = str(version_no or "").strip()
        if not normalized_version:
            sequence = int(
                session.execute(
                    text(
                        "SELECT count(*) + 1 FROM digital_asset.asset_versions WHERE asset_id=:id"
                    ),
                    {"id": asset_id},
                ).scalar_one()
            )
            normalized_version = f"v{sequence}"
        if len(normalized_version) > 80:
            raise HTTPException(status_code=422, detail="version_no is too long")
        version_conflict = (
            session.execute(
                text(
                    "SELECT id,artifact_sha256 FROM digital_asset.asset_versions "
                    "WHERE asset_id=:asset_id AND version_no=:version_no"
                ),
                {"asset_id": asset_id, "version_no": normalized_version},
            )
            .mappings()
            .one_or_none()
        )
        if version_conflict is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "source_version_number_conflict",
                    "version_no": normalized_version,
                    "existing_sha256": str(version_conflict["artifact_sha256"]),
                    "requested_sha256": stored.sha256,
                    "next_action": "use a new immutable version number",
                },
            )

        issued_by = session.execute(
            text("SELECT issued_by FROM digital_asset.api_credentials WHERE id=:id"),
            {"id": credential.credential_id},
        ).scalar_one_or_none()
        version_id = uuid4()
        version = (
            session.execute(
                text(
                    """
                INSERT INTO digital_asset.asset_versions(
                  id, tenant_id, asset_id, version_no, title, artifact_uri,
                  artifact_sha256, dependencies, change_log, created_by
                ) VALUES (
                  :id, :tenant_id, :asset_id, :version_no, :title, :artifact_uri,
                  :sha256, '[]'::jsonb, :change_log, :created_by
                ) RETURNING *
                """
                ),
                {
                    "id": version_id,
                    "tenant_id": credential.tenant_id,
                    "asset_id": asset_id,
                    "version_no": normalized_version,
                    "title": filename or f"Source {normalized_version}",
                    "artifact_uri": f"custody://sha256/{stored.sha256}",
                    "sha256": stored.sha256,
                    "change_log": "Uploaded through Workspace Deployment API v1",
                    "created_by": issued_by,
                },
            )
            .mappings()
            .one()
        )
        artifact_id = uuid4()
        artifact = (
            session.execute(
                text(
                    """
                INSERT INTO digital_asset.artifacts(
                  id, tenant_id, asset_id, version_id, artifact_kind,
                  filename, content_type, size_bytes, sha256, storage_provider,
                  object_key, storage_role, storage_pool_key,
                  state, verification, created_by
                ) VALUES (
                  :id, :tenant_id, :asset_id, :version_id, 'source',
                  :filename, :content_type, :size_bytes, :sha256, :provider,
                  :object_key, 'code', :pool_key, 'verified',
                  CAST(:verification AS jsonb), :created_by
                ) RETURNING *
                """
                ),
                {
                    "id": artifact_id,
                    "tenant_id": credential.tenant_id,
                    "asset_id": asset_id,
                    "version_id": version_id,
                    "filename": filename,
                    "content_type": content_type,
                    "size_bytes": stored.size_bytes,
                    "sha256": stored.sha256,
                    "provider": stored.provider_key,
                    "object_key": stored.object_key,
                    "pool_key": binding["pool_key"],
                    "verification": json.dumps(
                        {
                            "method": "server_sha256_and_safe_archive",
                            "verified_at": datetime.now(UTC).isoformat(),
                            "archive": archive.public(),
                        }
                    ),
                    "created_by": issued_by,
                },
            )
            .mappings()
            .one()
        )
        _custody_event(
            session,
            tenant_id=credential.tenant_id,
            asset_id=asset_id,
            actor_user_id=issued_by,
            event_type="deposit",
            artifact_sha256=stored.sha256,
            details={
                "origin": "workspace_api",
                "credential_id": str(credential.credential_id),
                "filename": filename,
                "size_bytes": stored.size_bytes,
                "archive": archive.public(),
            },
            version_id=version_id,
            artifact_id=artifact_id,
        )
        component = (
            session.execute(
                text(
                    """
                SELECT id, component_name FROM digital_asset.workspace_components
                WHERE workspace_id=:workspace_id
                  AND (CAST(:component_name AS text) IS NULL OR component_name=:component_name)
                ORDER BY CASE component_kind WHEN 'backend' THEN 0 ELSE 1 END, component_name
                LIMIT 1
                """
                ),
                {"workspace_id": workspace["id"], "component_name": component_name or None},
            )
            .mappings()
            .one_or_none()
        )
        if component_name and component is None:
            raise HTTPException(status_code=404, detail="Workspace component not found")
        if component is not None:
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspace_components
                    SET source_version_id=:version_id, status='configured'
                    WHERE id=:component_id
                    """
                ),
                {"version_id": version_id, "component_id": component["id"]},
            )
        session.execute(
            text(
                """
                UPDATE digital_asset.assets SET status='custodied', lifecycle_stage='custody'
                WHERE id=:asset_id
                """
            ),
            {"asset_id": asset_id},
        )
        _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=asset_id,
        )
        _audit(
            session,
            None,
            "digital_asset.workspace_source_uploaded",
            {
                "workspace_id": str(workspace["id"]),
                "asset_id": str(asset_id),
                "version_id": str(version_id),
                "artifact_id": str(artifact_id),
                "sha256": stored.sha256,
                "credential_id": str(credential.credential_id),
                "hosting_contract": archive.signals.get("hosting_contract"),
            },
            tenant_id=credential.tenant_id,
        )
    return {
        "ok": True,
        "idempotent_replay": False,
        "source": _public_version(dict(version)),
        "artifact": _json_safe(dict(artifact)),
        "archive": archive.public(),
        "component": _json_safe(dict(component)) if component is not None else None,
        "next_action": "request_deployment",
    }


def list_workspace_sources(credential: WorkspaceCredential) -> dict[str, object]:
    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        rows = (
            session.execute(
                text(
                    """
                SELECT v.*, ar.id AS artifact_id, ar.filename, ar.content_type,
                       ar.size_bytes, ar.storage_provider, ar.storage_pool_key, ar.state,
                       ar.verification
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar
                  ON ar.version_id=v.id AND ar.storage_role='code'
                WHERE v.asset_id=:asset_id
                ORDER BY v.created_at DESC
                """
                ),
                {"asset_id": workspace["asset_id"]},
            )
            .mappings()
            .all()
        )
    sources = []
    for row in rows:
        item = _public_version(dict(row))
        item["artifact"] = _json_safe(
            {
                "id": row["artifact_id"],
                "filename": row["filename"],
                "content_type": row["content_type"],
                "size_bytes": row["size_bytes"],
                "storage_provider": row["storage_provider"],
                "storage_pool_key": row["storage_pool_key"],
                "state": row["state"],
            }
        )
        verification = row.get("verification") if isinstance(row.get("verification"), dict) else {}
        archive = (
            verification.get("archive")
            if isinstance(verification.get("archive"), dict)
            else {}
        )
        signals = archive.get("signals") if isinstance(archive.get("signals"), dict) else {}
        item["hosting_contract"] = _json_safe(signals.get("hosting_contract"))
        sources.append(item)
    return {"ok": True, "sources": sources, "count": len(sources)}


def workspace_source_download_target(
    credential: WorkspaceCredential,
    source_ref: str,
) -> dict[str, object]:
    """Resolve one verified source object inside the Key's fixed workspace."""

    credential.require("deploy:read")
    reference = str(source_ref).strip()
    if not reference:
        raise HTTPException(status_code=422, detail="Invalid source version id")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        row = (
            session.execute(
                text(
                    """
                SELECT v.id, v.legacy_id, v.version_no, v.artifact_sha256,
                       ar.id AS artifact_id, ar.filename, ar.content_type,
                       ar.size_bytes, ar.sha256, ar.storage_provider,
                       ar.storage_pool_key, ar.object_key, ar.state
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar
                  ON ar.version_id=v.id AND ar.storage_role='code'
                WHERE v.asset_id=:asset_id
                  AND (
                    CAST(v.id AS text)=:reference
                    OR CAST(v.legacy_id AS text)=:reference
                  )
                  AND ar.state='verified'
                ORDER BY ar.created_at DESC LIMIT 1
                """
                ),
                {"asset_id": workspace["asset_id"], "reference": reference},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Source version not found")
    return _json_safe(dict(row))


def _runtime_profile(session: object, component: dict[str, object], requested: object) -> str:
    explicit = str(requested or "").strip()
    if explicit:
        profile = session.execute(
            text(
                "SELECT profile_key FROM platform.runtime_profiles "
                "WHERE profile_key=:key AND enabled"
            ),
            {"key": explicit},
        ).scalar_one_or_none()
    else:
        runtime = str(component.get("runtime") or "static").lower()
        family = (
            "container"
            if runtime.startswith(("container", "docker", "oci", "compose"))
            else "python"
            if runtime.startswith("python")
            else "node"
            if runtime.startswith("node")
            else "static"
        )
        profile = session.execute(
            text(
                """
                SELECT profile_key FROM platform.runtime_profiles
                WHERE runtime_family=:family AND enabled
                ORDER BY revision DESC, profile_key LIMIT 1
                """
            ),
            {"family": family},
        ).scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=409, detail="No enabled Runtime profile matches this component"
        )
    return str(profile)


def _verified_source(
    session: object,
    workspace: dict[str, object],
    source_ref: object,
) -> dict[str, object] | None:
    source_id = None
    if source_ref not in (None, ""):
        try:
            source_id = UUID(str(source_ref))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid source_version_id") from exc
    row = (
        session.execute(
            text(
                """
                SELECT v.id, v.version_no, ar.storage_provider, ar.object_key,
                       ar.sha256, ar.verification
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar ON ar.version_id=v.id
                WHERE v.asset_id=:asset_id
                  AND (CAST(:source_id AS uuid) IS NULL OR v.id=:source_id)
                  AND ar.storage_role='code' AND ar.state='verified'
                ORDER BY v.created_at DESC LIMIT 1
                """
            ),
            {"asset_id": workspace["asset_id"], "source_id": source_id},
        )
        .mappings()
        .one_or_none()
    )
    if source_ref not in (None, "") and row is None:
        raise HTTPException(status_code=404, detail="Verified source version not found")
    return dict(row) if row is not None else None


def _source_signals(source: dict[str, object] | None, settings: Settings) -> dict[str, object]:
    if source is None:
        return {}
    verification = (
        source.get("verification") if isinstance(source.get("verification"), dict) else {}
    )
    archive = verification.get("archive") if isinstance(verification.get("archive"), dict) else {}
    signals = archive.get("signals") if isinstance(archive.get("signals"), dict) else None
    if signals is not None and "hosting_manifest" in signals:
        return dict(signals)
    for store in object_store_read_candidates(settings, str(source["storage_provider"])):
        path = store.path_for(str(source["object_key"]))
        if path.is_file():
            return inspect_source_archive(
                path,
                max_uncompressed_bytes=settings.asset_max_upload_bytes * 8,
            ).signals
    raise HTTPException(status_code=409, detail="Verified source object is unavailable")


def _source_supports_runtime_family(
    signals: dict[str, object],
    family: str,
    payload: dict[str, object] | None = None,
) -> bool:
    """Return whether verified source evidence can satisfy one Runtime family."""

    intent = payload or {}
    if family == "static":
        return bool(signals.get("index_html"))
    if family == "python":
        return bool(signals.get("python_source"))
    if family == "node":
        return bool(signals.get("package_json") or signals.get("node_source"))
    if family == "container":
        return bool(
            signals.get("dockerfile")
            or signals.get("compose_file")
            or intent.get("image")
            or intent.get("dockerfile")
            or intent.get("compose_file")
        )
    return False


def _resolve_runtime_contract(
    session: object,
    payload: dict[str, object],
    signals: dict[str, object],
) -> tuple[str, dict[str, object]]:
    requested_type = str(payload.get("runtime_type") or payload.get("type") or "auto").lower()
    if requested_type not in WORKSPACE_RUNTIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=("runtime_type must be auto/static/web/api/worker/agent/job/container/compose"),
        )
    requested_profile = str(payload.get("runtime_profile") or "").strip()
    requested_runtime = str(payload.get("runtime") or "").strip().lower()
    explicit_contract = bool(requested_type != "auto" or requested_profile or requested_runtime)
    family = None
    if requested_profile:
        profile = (
            session.execute(
                text("SELECT * FROM platform.runtime_profiles WHERE profile_key=:key AND enabled"),
                {"key": requested_profile},
            )
            .mappings()
            .one_or_none()
        )
        if profile is None:
            raise HTTPException(status_code=422, detail="Requested Runtime profile is unavailable")
        family = str(profile["runtime_family"])
    else:
        if requested_runtime.startswith(("container", "docker", "oci", "compose")):
            family = "container"
        elif requested_runtime.startswith("python"):
            family = "python"
        elif requested_runtime.startswith("node"):
            family = "node"
        elif requested_runtime == "static":
            family = "static"
        elif requested_type == "static":
            family = "static"
        elif requested_type in {"container", "compose"}:
            family = "container"
        elif requested_type in {"api", "worker", "agent", "job"}:
            family = (
                "python"
                if signals.get("python_source")
                else "node"
                if signals.get("node_source") or signals.get("package_json")
                else None
            )
        elif requested_type == "web":
            family = (
                "node"
                if signals.get("package_json")
                else "python"
                if signals.get("python_source") and not signals.get("index_html")
                else "static"
                if signals.get("index_html")
                else None
            )
        else:
            if signals.get("compose_file"):
                requested_type, family = "compose", "container"
            elif signals.get("dockerfile"):
                requested_type, family = "container", "container"
            elif signals.get("worker_entry"):
                requested_type, family = "worker", str(signals.get("worker_family"))
            elif signals.get("agent_entry"):
                requested_type, family = "agent", str(signals.get("agent_family"))
            elif signals.get("python_source"):
                requested_type, family = "api", "python"
            elif signals.get("package_json"):
                requested_type, family = "web", "node"
            elif signals.get("index_html"):
                requested_type, family = "static", "static"
    if family is None:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "runtime_cannot_be_detected",
                "message": (
                    "Specify runtime_type and runtime, or provide recognizable source evidence"
                ),
                "signals": signals,
            },
        )
    if (
        signals
        and explicit_contract
        and not _source_supports_runtime_family(signals, family, payload)
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "source_runtime_mismatch",
                "message": "Verified source does not satisfy the requested Runtime family",
                "requested_runtime_type": requested_type,
                "requested_runtime_family": family,
                "signals": signals,
                "next_action": "use_runtime_type_auto_or_upload_compatible_source",
            },
        )
    if requested_type == "auto":
        requested_type = (
            "static"
            if family == "static"
            else "compose"
            if family == "container" and signals.get("compose_file")
            else "container"
            if family == "container"
            else "api"
        )
    if requested_type == "static" and family != "static":
        raise HTTPException(status_code=422, detail="Static hosting requires a static profile")
    if requested_type in {"api", "worker", "agent", "job"} and family == "static":
        raise HTTPException(status_code=422, detail=f"{requested_type} requires Python or Node")
    if not requested_profile:
        profile = (
            session.execute(
                text(
                    """
                    SELECT * FROM platform.runtime_profiles
                    WHERE runtime_family=:family AND enabled
                    ORDER BY revision DESC, profile_key LIMIT 1
                    """
                ),
                {"family": family},
            )
            .mappings()
            .one_or_none()
        )
        if profile is None:
            raise HTTPException(status_code=409, detail="No enabled Runtime profile matches source")
    return requested_type, dict(profile)


def configure_workspace_runtime(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Configure one same-workspace component from explicit intent or source evidence."""

    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        source = _verified_source(session, workspace, payload.get("source_version_id"))
        signals = _source_signals(source, settings)
        payload = _manifest_runtime_intent(payload, signals)
        manifest = _hosting_manifest(signals)
        _require_manifest_database_policy(workspace, manifest)
        runtime_type, profile = _resolve_runtime_contract(session, payload, signals)
        family = str(profile["runtime_family"])
        kind = {
            "static": "frontend",
            "web": "backend" if family != "static" else "frontend",
            "api": "backend",
            "worker": "worker",
            "agent": "agent",
            "job": "worker",
            "container": "backend",
            "compose": "backend",
        }[runtime_type]
        default_name = {
            "frontend": "frontend",
            "backend": "api",
            "worker": "worker",
            "agent": "agent",
        }[kind]
        if runtime_type == "job":
            default_name = "job"
        component_name = str(payload.get("component") or default_name).strip()
        if not component_name or len(component_name) > 80:
            raise HTTPException(status_code=422, detail="Invalid component name")
        runtime = (
            "static"
            if family == "static"
            else "python3.12"
            if family == "python"
            else "node20"
            if family == "node"
            else "container"
        )
        candidates = list(signals.get("candidate_entrypoints") or [])
        single_root = str(signals.get("single_root") or "").strip("/")
        if single_root:
            candidates = [candidate.removeprefix(single_root + "/") for candidate in candidates]
        basename_order = (
            ["worker.py", "worker.js", "main.py", "index.js"]
            if kind == "worker"
            else ["agent.py", "agent.js", "main.py", "index.js"]
            if kind == "agent"
            else [
                "app.py",
                "main.py",
                "server.py",
                "asgi.py",
                "wsgi.py",
                "server.js",
                "index.js",
            ]
        )
        detected_entrypoint = next(
            (
                candidate
                for name in basename_order
                for candidate in candidates
                if candidate.endswith("/" + name) or candidate == name
            ),
            None,
        )
        entrypoint = str(
            payload.get("entrypoint")
            or detected_entrypoint
            or (
                "index.html"
                if family == "static"
                else "app.py"
                if family == "python"
                else "server.js"
                if family == "node"
                else str(signals.get("compose_file") or "Dockerfile")
            )
        ).strip()
        component_config = {
            key: payload.get(key)
            for key in (
                "image",
                "dockerfile",
                "compose_file",
                "route_service",
                "port",
                "command",
                "activate",
                "execution_mode",
                "database_url_env",
                "database_access",
                "lifecycle_job",
                "compatibility_contract",
                "timeout_seconds",
            )
            if payload.get(key) not in (None, "")
        }
        if runtime_type == "job":
            component_config["execution_mode"] = "job"
            component_config["activate"] = False
        component = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.workspace_components(
                      id, tenant_id, workspace_id, component_name, component_kind,
                      runtime, entrypoint, build_command, start_command,
                      source_version_id, config, status
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :name, :kind,
                      :runtime, :entrypoint, :build, :start, :source,
                      CAST(:component_config AS jsonb), 'configured'
                    )
                    ON CONFLICT (tenant_id, workspace_id, component_name) DO UPDATE SET
                      component_kind=EXCLUDED.component_kind,
                      runtime=EXCLUDED.runtime,
                      entrypoint=EXCLUDED.entrypoint,
                      build_command=EXCLUDED.build_command,
                      start_command=EXCLUDED.start_command,
                      config=digital_asset.workspace_components.config || EXCLUDED.config,
                      source_version_id=COALESCE(EXCLUDED.source_version_id,
                        digital_asset.workspace_components.source_version_id),
                      status='configured', updated_at=now()
                    RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": credential.tenant_id,
                    "workspace_id": workspace["id"],
                    "name": component_name,
                    "kind": kind,
                    "runtime": runtime,
                    "entrypoint": entrypoint,
                    "build": payload.get("build_command"),
                    "start": payload.get("start_command"),
                    "source": source["id"] if source else None,
                    "component_config": json.dumps(component_config),
                },
            )
            .mappings()
            .one()
        )
        config = dict(workspace.get("config") or {})
        requested_type = (
            str(payload.get("runtime_type") or payload.get("type") or "auto").strip().lower()
        )
        runtime_selection = (
            "declared"
            if manifest is not None
            else "explicit"
            if requested_type != "auto"
            or payload.get("runtime_profile") not in (None, "")
            or payload.get("runtime") not in (None, "")
            else "detected"
        )
        config.update(
            {
                "runtime_type": runtime_type,
                "runtime_profile": profile["profile_key"],
                "runtime_selection": runtime_selection,
            }
        )
        session.execute(
            text(
                "UPDATE digital_asset.workspaces SET config=CAST(:config AS jsonb), "
                "runtime_status=CASE "
                "WHEN runtime_status IN ('building','ready') THEN runtime_status "
                "ELSE 'provisioned' END WHERE id=:id"
            ),
            {"config": json.dumps(config), "id": workspace["id"]},
        )
        _audit(
            session,
            None,
            "digital_asset.workspace_runtime_configured_by_key",
            {
                "workspace_id": str(workspace["id"]),
                "credential_id": str(credential.credential_id),
                "runtime_type": runtime_type,
                "runtime_profile": profile["profile_key"],
                "component": component_name,
                "source_version_id": str(source["id"]) if source else None,
                "hosting_contract_digest": (
                    manifest.get("contract_digest") if manifest is not None else None
                ),
            },
            tenant_id=credential.tenant_id,
        )
    result: dict[str, object] = {
        "ok": True,
        "runtime": {
            "runtime_type": runtime_type,
            "runtime_profile": profile["profile_key"],
            "runtime_family": family,
            "selection": config["runtime_selection"],
            "signals": signals,
            "compatibility": (
                {
                    "declared": True,
                    "schema": manifest.get("schema"),
                    "contract_digest": manifest.get("contract_digest"),
                    "deployment": manifest.get("deployment"),
                }
                if manifest is not None
                else {"declared": False, "selection": "platform_detected"}
            ),
        },
        "component": _json_safe(dict(component)),
        "source_version_id": str(source["id"]) if source else None,
        "next_action": "request_deployment" if source else "upload_source",
    }
    if bool(payload.get("deploy")):
        if source is None:
            raise HTTPException(status_code=409, detail="Deployment requires a verified source")
        result["deployment"] = request_workspace_deployment(
            credential,
            {
                "source_version_id": str(source["id"]),
                "component": component_name,
                "runtime_profile": profile["profile_key"],
                "entrypoint": entrypoint,
                "health_path": payload.get("health_path"),
                "activate": payload.get("activate"),
                "execution_mode": payload.get("execution_mode"),
                "database_url_env": payload.get("database_url_env"),
                "timeout_seconds": payload.get("timeout_seconds"),
                **component_config,
            },
            idempotency_key=str(
                payload.get("idempotency_key")
                or f"runtime-{source['id']}-{profile['profile_key']}-{component_name}"
            ),
            settings=settings,
        )["deployment"]
        result["next_action"] = "observe_deployment"
    return result


def resolve_declared_workspace_job(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    """Resolve a named, source-declared lifecycle job without trusting caller commands."""

    credential.require("deploy:write")
    name = str(payload.get("job") or "").strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="A declared lifecycle job name is required")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=False)
        source = _verified_source(session, workspace, payload.get("source_version_id"))
        if source is None:
            raise HTTPException(status_code=409, detail="A verified source version is required")
        signals = _source_signals(source, settings)
        manifest = _hosting_manifest(signals)
        _require_manifest_database_policy(workspace, manifest)
    if manifest is None:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "hosting_manifest_required",
                "message": "Named lifecycle jobs require warehouse.hosting.json",
            },
        )
    job = declared_lifecycle_job(manifest, name)
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={
                "reason": "declared_lifecycle_job_not_found",
                "job": name,
                "available": [
                    item.get("name")
                    for item in (manifest.get("lifecycle") or {}).get("jobs", [])
                    if isinstance(item, dict)
                ],
            },
        )
    database_access = str(job.get("database_access") or "none")
    if database_access != "none":
        credential.require("database:admin")
    runtime = manifest.get("runtime") if isinstance(manifest.get("runtime"), dict) else {}
    resolved = {
        "source_version_id": str(source["id"]),
        "runtime_type": "job",
        "runtime": job.get("runtime") or runtime.get("runtime"),
        "runtime_profile": job.get("runtime_profile") or runtime.get("runtime_profile"),
        "component": f"job-{name}",
        "entrypoint": job.get("entrypoint") or runtime.get("entrypoint"),
        "build_command": job.get("build_command") or runtime.get("build_command"),
        "start_command": job["command"],
        "database_access": database_access,
        "database_url_env": job.get("database_url_env"),
        "timeout_seconds": job["timeout_seconds"],
        "execution_mode": "job",
        "activate": False,
        "lifecycle_job": {
            "name": name,
            "contract_digest": manifest["contract_digest"],
            "required_before_activation": bool(job.get("required_before_activation")),
        },
        "compatibility_contract": manifest,
    }
    resolved.update(
        {
            key: value
            for key, value in payload.items()
            if key in {"runtime", "runtime_profile"} and value not in (None, "")
        }
    )
    return {key: value for key, value in resolved.items() if value not in (None, "")}


def request_workspace_deployment(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    *,
    idempotency_key: str | None,
    settings: Settings | None = None,
) -> dict[str, object]:
    credential.require("deploy:write")
    if payload.get("database_url_env") not in (None, ""):
        credential.require("database:admin")
    execution_mode = str(payload.get("execution_mode") or "service").strip().lower()
    if execution_mode not in {"service", "job"}:
        raise HTTPException(status_code=422, detail="execution_mode must be service or job")
    database_url_env = str(payload.get("database_url_env") or "").strip()
    if database_url_env and not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", database_url_env):
        raise HTTPException(status_code=422, detail="database_url_env must be a safe env name")
    try:
        timeout_seconds = int(payload.get("timeout_seconds") or 1200)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="timeout_seconds must be an integer") from exc
    if not 30 <= timeout_seconds <= 7200:
        raise HTTPException(status_code=422, detail="timeout_seconds must be between 30 and 7200")
    activate_value = payload.get("activate")
    activate_requested = (
        True if activate_value is None else bool(activate_value)
    ) and execution_mode != "job"
    settings = settings or get_settings()
    key = str(idempotency_key or payload.get("idempotency_key") or "").strip() or None
    if key and len(key) > 200:
        raise HTTPException(status_code=422, detail="Idempotency-Key is too long")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id, lock=True)
        if key:
            replay = (
                session.execute(
                    text(
                        """
                    SELECT * FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id AND idempotency_key=:key
                    """
                    ),
                    {"workspace_id": workspace["id"], "key": key},
                )
                .mappings()
                .one_or_none()
            )
            if replay is not None:
                result = _public_deployment(dict(replay))
                result["idempotent_replay"] = True
                return {"ok": True, "deployment": result}
        component_name = str(
            payload.get("component") or payload.get("component_name") or ""
        ).strip()
        component = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.workspace_components
                WHERE workspace_id=:workspace_id
                  AND (CAST(:name AS text)='' OR component_name=:name)
                ORDER BY CASE component_kind WHEN 'backend' THEN 0 ELSE 1 END, component_name
                LIMIT 1
                """
                ),
                {"workspace_id": workspace["id"], "name": component_name},
            )
            .mappings()
            .one_or_none()
        )
        if component is None:
            raise HTTPException(status_code=409, detail="Workspace component not found")
        source_ref = payload.get("source_version_id") or component.get("source_version_id")
        if source_ref:
            try:
                source_id = UUID(str(source_ref))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Invalid source_version_id") from exc
        else:
            source_id = session.execute(
                text(
                    """
                    SELECT v.id FROM digital_asset.asset_versions AS v
                    JOIN digital_asset.artifacts AS ar ON ar.version_id=v.id
                    WHERE v.asset_id=:asset_id AND ar.storage_role='code'
                      AND ar.state='verified'
                    ORDER BY v.created_at DESC LIMIT 1
                    """
                ),
                {"asset_id": workspace["asset_id"]},
            ).scalar_one_or_none()
        source = (
            session.execute(
                text(
                    """
                SELECT v.id, v.artifact_sha256, ar.storage_provider, ar.object_key,
                       ar.verification
                FROM digital_asset.asset_versions AS v
                JOIN digital_asset.artifacts AS ar ON ar.version_id=v.id
                WHERE v.id=:source_id AND v.asset_id=:asset_id
                  AND ar.storage_role='code' AND ar.state='verified'
                LIMIT 1
                """
                ),
                {"source_id": source_id, "asset_id": workspace["asset_id"]},
            )
            .mappings()
            .one_or_none()
        )
        if source is None or str(source["storage_provider"]) not in LOCAL_PROVIDER_KEYS:
            raise HTTPException(
                status_code=409, detail="A verified hosted source version is required"
            )
        signals = _source_signals(dict(source), settings)
        manifest = _hosting_manifest(signals)
        _require_manifest_database_policy(workspace, manifest)
        manifest_defaults = manifest_runtime_defaults(manifest)
        profile_key = _runtime_profile(
            session,
            dict(component),
            payload.get("runtime_profile") or manifest_defaults.get("runtime_profile"),
        )
        profile_family = session.execute(
            text(
                "SELECT runtime_family FROM platform.runtime_profiles "
                "WHERE profile_key=:profile_key AND enabled"
            ),
            {"profile_key": profile_key},
        ).scalar_one()
        runtime_intent = {
            **(component.get("config") if isinstance(component.get("config"), dict) else {}),
            **manifest_defaults,
            **{key: value for key, value in payload.items() if value not in (None, "")},
        }
        if manifest is not None:
            runtime_intent["compatibility_contract"] = manifest
        else:
            runtime_intent.pop("compatibility_contract", None)
            runtime_intent.pop("lifecycle_job", None)
        declared_deployment = (
            manifest.get("deployment")
            if manifest is not None and isinstance(manifest.get("deployment"), dict)
            else {}
        )
        if bool(declared_deployment.get("require_acceptance_before_activation")):
            activate_requested = False
        database_url_env = str(runtime_intent.get("database_url_env") or "").strip()
        if database_url_env:
            credential.require("database:admin")
            if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", database_url_env):
                raise HTTPException(
                    status_code=422,
                    detail="database_url_env must be a safe env name",
                )
        database_access = str(
            runtime_intent.get("database_access")
            or (
                "migration"
                if execution_mode == "job" and database_url_env
                else "runtime"
                if database_url_env
                else "none"
            )
        ).strip().lower()
        if database_access not in {"none", "runtime", "migration"}:
            raise HTTPException(
                status_code=422,
                detail="database_access must be none, runtime, or migration",
            )
        if execution_mode != "job" and database_access == "migration":
            raise HTTPException(
                status_code=422,
                detail="Migration database access is restricted to one-shot jobs",
            )
        lifecycle_job = runtime_intent.get("lifecycle_job")
        if lifecycle_job is not None:
            lifecycle_job = lifecycle_job if isinstance(lifecycle_job, dict) else {}
            lifecycle_name = str(lifecycle_job.get("name") or "")
            declared_job = declared_lifecycle_job(manifest, lifecycle_name)
            job_matches_contract = bool(
                execution_mode == "job"
                and manifest is not None
                and declared_job is not None
                and lifecycle_job.get("contract_digest") == manifest.get("contract_digest")
                and str(runtime_intent.get("start_command") or "")
                == str(declared_job.get("command") or "")
                and database_access == str(declared_job.get("database_access") or "none")
                and (database_url_env or None) == declared_job.get("database_url_env")
            )
            if not job_matches_contract:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "reason": "lifecycle_job_contract_mismatch",
                        "job": lifecycle_name,
                    },
                )
        if not _source_supports_runtime_family(signals, str(profile_family), runtime_intent):
            recommended_type, recommended_profile = _resolve_runtime_contract(
                session, {"runtime_type": "auto"}, signals
            )
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "runtime_contract_mismatch",
                    "message": (
                        "Selected Runtime cannot execute the verified source; "
                        "configure the detected Runtime before deploying"
                    ),
                    "source_version_id": str(source["id"]),
                    "component": component["component_name"],
                    "current_runtime": component.get("runtime"),
                    "current_runtime_profile": profile_key,
                    "current_runtime_family": str(profile_family),
                    "recommended_runtime_type": recommended_type,
                    "recommended_runtime_profile": recommended_profile["profile_key"],
                    "recommended_runtime_family": recommended_profile["runtime_family"],
                    "next_action": "configure_runtime_and_redeploy",
                    "recommended_request": {
                        "method": "PUT",
                        "path": "/api/workspaces/v1/runtime",
                        "body": {
                            "runtime_type": "auto",
                            "source_version_id": str(source["id"]),
                            "deploy": True,
                        },
                    },
                    "retryable": True,
                },
            )
        intent = {
            "workspace_id": str(workspace["id"]),
            "component_id": str(component["id"]),
            "source_version_id": str(source["id"]),
            "source_sha256": source["artifact_sha256"],
            "runtime_profile": profile_key,
            "entrypoint": payload.get("entrypoint") or component.get("entrypoint"),
            "build_command": payload.get("build_command") or component.get("build_command"),
            "start_command": payload.get("start_command") or component.get("start_command"),
            "health_path": payload.get("health_path"),
            "activate": activate_requested,
            "execution_mode": execution_mode,
            "database_url_env": database_url_env or None,
            "database_access": database_access,
            "lifecycle_job": runtime_intent.get("lifecycle_job"),
            "compatibility_contract": runtime_intent.get("compatibility_contract"),
            "timeout_seconds": timeout_seconds,
            **{
                key: (
                    payload.get(key)
                    if payload.get(key) not in (None, "")
                    else (component.get("config") or {}).get(key)
                )
                for key in (
                    "image",
                    "dockerfile",
                    "compose_file",
                    "route_service",
                    "port",
                    "command",
                )
                if payload.get(key) not in (None, "")
                or (component.get("config") or {}).get(key) not in (None, "")
            },
        }
        digest = hashlib.sha256(
            json.dumps(intent, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()
        revision = int(
            session.execute(
                text(
                    """
                    SELECT COALESCE(max(revision),0)+1 FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id AND component_id=:component_id
                    """
                ),
                {"workspace_id": workspace["id"], "component_id": component["id"]},
            ).scalar_one()
        )
        with system_session() as identity_session:
            tenant_slug = identity_session.execute(
                text("SELECT slug FROM iam.tenants WHERE id=:id"),
                {"id": credential.tenant_id},
            ).scalar_one()
        deployment_id = uuid4()
        row = (
            session.execute(
                text(
                    """
                INSERT INTO digital_asset.deployments(
                  id, tenant_id, workspace_id, component_id, source_version_id,
                  revision, provider_key, release_digest, status, health,
                  public_url, requested_config, requested_by,
                  idempotency_key, request_digest, requested_credential_id,
                  runtime_profile_key
                ) VALUES (
                  :id, :tenant_id, :workspace_id, :component_id, :source_version_id,
                  :revision, 'runtime_queue', :release_digest, 'queued', 'pending',
                  :public_url, CAST(:requested_config AS jsonb), :requested_by,
                  :idempotency_key, :request_digest, :credential_id, :profile_key
                ) RETURNING *
                """
                ),
                {
                    "id": deployment_id,
                    "tenant_id": credential.tenant_id,
                    "workspace_id": workspace["id"],
                    "component_id": component["id"],
                    "source_version_id": source["id"],
                    "revision": revision,
                    "release_digest": source["artifact_sha256"],
                    "public_url": workspace_entry_url(
                        str(tenant_slug), str(workspace["workspace_key"])
                    ),
                    "requested_config": json.dumps(intent, ensure_ascii=False, default=str),
                    "requested_by": session.execute(
                        text("SELECT issued_by FROM digital_asset.api_credentials WHERE id=:id"),
                        {"id": credential.credential_id},
                    ).scalar_one_or_none(),
                    "idempotency_key": key,
                    "request_digest": digest,
                    "credential_id": credential.credential_id,
                    "profile_key": profile_key,
                },
            )
            .mappings()
            .one()
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id, tenant_id, sequence, event_type, payload
                ) VALUES (:id, :tenant_id, 1, 'requested', CAST(:payload AS jsonb))
                """
            ),
            {
                "id": deployment_id,
                "tenant_id": credential.tenant_id,
                "payload": json.dumps(
                    {
                        "credential_id": str(credential.credential_id),
                        "component": component["component_name"],
                        "source_sha256": source["artifact_sha256"],
                        "runtime_profile": profile_key,
                    }
                ),
            },
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.workspace_components
                SET source_version_id=:source_id, status='building'
                WHERE id=:component_id
                """
            ),
            {
                "source_id": source["id"],
                "component_id": component["id"],
            },
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.workspaces SET runtime_status='building'
                WHERE id=:workspace_id
                """
            ),
            {"workspace_id": workspace["id"]},
        )
        _audit(
            session,
            None,
            "digital_asset.workspace_deployment_requested",
            {
                "workspace_id": str(workspace["id"]),
                "deployment_id": str(deployment_id),
                "source_sha256": source["artifact_sha256"],
                "credential_id": str(credential.credential_id),
                "request_digest": digest,
            },
            tenant_id=credential.tenant_id,
        )
    deployment = _public_deployment(dict(row))
    deployment["idempotent_replay"] = False
    deployment["next_action"] = "runtime_worker_claim"
    return {"ok": True, "deployment": deployment}


_PRIVATE_RUNTIME_FIELDS = frozenset(
    {
        "container_name",
        "container_names",
        "internal_url",
        "internal_urls",
        "runtime_path",
        "host_path",
    }
)


def _sanitize_runtime_result(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _sanitize_runtime_result(item)
            for key, item in value.items()
            if str(key) not in _PRIVATE_RUNTIME_FIELDS
        }
    if isinstance(value, list):
        return [_sanitize_runtime_result(item) for item in value]
    return value


def _deployment_public(row: dict[str, object]) -> dict[str, object]:
    value = _public_deployment(row)
    result = value.get("result") if isinstance(value.get("result"), dict) else {}
    if result:
        value["result"] = _sanitize_runtime_result(result)
    value["verified_application_url"] = (
        value.get("public_url")
        if value.get("status") == "ready"
        and value.get("health") == "healthy"
        and result.get("public_route_verified") is True
        else None
    )
    return value


def list_workspace_deployments(
    credential: WorkspaceCredential,
    *,
    limit: int = 50,
) -> dict[str, object]:
    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        _workspace_row(session, credential.workspace_id)
        rows = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.deployments
                WHERE workspace_id=:workspace_id
                ORDER BY created_at DESC LIMIT :limit
                """
                ),
                {"workspace_id": credential.workspace_id, "limit": limit},
            )
            .mappings()
            .all()
        )
    deployments = [_deployment_public(dict(row)) for row in rows]
    return {"ok": True, "deployments": deployments, "count": len(deployments)}


def observe_workspace_deployment(
    credential: WorkspaceCredential,
    deployment_id: DeploymentReference,
    *,
    include_events: bool = True,
) -> dict[str, object]:
    credential.require("deploy:read")
    with tenant_session(credential.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.deployments
                WHERE workspace_id=:workspace_id
                  AND (
                    CAST(id AS text)=:deployment_reference
                    OR CAST(legacy_id AS text)=:deployment_reference
                  )
                """
                ),
                {
                    **_deployment_reference_params(deployment_id),
                    "workspace_id": credential.workspace_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Deployment not found")
        resolved_id = UUID(str(row["id"]))
        events = []
        if include_events:
            events = [
                _json_safe(dict(event))
                for event in session.execute(
                    text(
                        """
                        SELECT sequence, event_type, payload, created_at
                        FROM digital_asset.deployment_events
                        WHERE deployment_id=:id ORDER BY sequence
                        """
                    ),
                    {"id": resolved_id},
                )
                .mappings()
                .all()
            ]
    return {"ok": True, "deployment": _deployment_public(dict(row)), "events": events}


def repair_workspace_deployment(
    credential: WorkspaceCredential,
    deployment_id: DeploymentReference,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Idempotently enqueue a bounded repair under the workspace credential."""

    credential.require("deploy:write")
    request = payload or {}
    source = str(request.get("source") or "user").strip().lower()
    if source not in {"user", "ai_secretary", "platform_probe"}:
        raise HTTPException(status_code=422, detail="Invalid deployment repair source")
    reason = str(request.get("reason") or "deployment_runtime_repair").strip()
    if not reason or len(reason) > 240:
        raise HTTPException(status_code=422, detail="Invalid deployment repair reason")

    with tenant_session(credential.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.deployments
                    WHERE workspace_id=:workspace_id
                      AND (
                        CAST(id AS text)=:deployment_reference
                        OR CAST(legacy_id AS text)=:deployment_reference
                      )
                    FOR UPDATE
                    """
                ),
                {
                    **_deployment_reference_params(deployment_id),
                    "workspace_id": credential.workspace_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Deployment not found")
        resolved_id = UUID(str(row["id"]))
        current_status = str(row["status"])
        if current_status in {"queued", "building", "deploying"}:
            return {
                "ok": True,
                "accepted": False,
                "deployment": _deployment_public(dict(row)),
                "next_action": "observe_deployment",
            }
        if current_status not in {"ready", "failed"}:
            raise HTTPException(
                status_code=409,
                detail=f"Deployment cannot be repaired from {current_status}",
            )
        active = bool(
            session.execute(
                text(
                    "SELECT EXISTS(SELECT 1 FROM digital_asset.workspaces "
                    "WHERE id=:workspace_id AND active_deployment_id=:deployment_id)"
                ),
                {
                    "workspace_id": credential.workspace_id,
                    "deployment_id": resolved_id,
                },
            ).scalar_one()
        )
        if current_status == "ready" and not active:
            raise HTTPException(
                status_code=409,
                detail="Only the active ready deployment can be repaired",
            )
        updated = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET status='queued',health='pending',lease_owner=NULL,
                        lease_expires_at=NULL,started_at=NULL,completed_at=NULL,
                        result=result || jsonb_build_object(
                          'repair_requested_at',now(),
                          'repair_source',CAST(:source AS text)
                        )
                    WHERE id=:deployment_id
                    RETURNING *
                    """
                ),
                {"deployment_id": resolved_id, "source": source},
            )
            .mappings()
            .one()
        )
        if active:
            session.execute(
                text(
                    "UPDATE digital_asset.workspaces SET runtime_status='building' "
                    "WHERE id=:workspace_id AND active_deployment_id=:deployment_id"
                ),
                {
                    "workspace_id": credential.workspace_id,
                    "deployment_id": resolved_id,
                },
            )
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence),0)+1 "
                    "FROM digital_asset.deployment_events WHERE deployment_id=:id"
                ),
                {"id": resolved_id},
            ).scalar_one()
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id,tenant_id,sequence,event_type,payload
                ) VALUES (
                  :id,:tenant_id,:sequence,'repair_requested',CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "id": resolved_id,
                "tenant_id": credential.tenant_id,
                "sequence": sequence,
                "payload": json.dumps(
                    {
                        "credential_id": str(credential.credential_id),
                        "source": source,
                        "reason": reason,
                        "previous_status": current_status,
                        "active_deployment": active,
                    }
                ),
            },
        )
    return {
        "ok": True,
        "accepted": True,
        "deployment": _deployment_public(dict(updated)),
        "repair_contract": {
            "execution": "asynchronous",
            "required_scope": "deploy:write",
            "source": source,
            "automatic_runtime_reconciliation": True,
        },
        "next_action": "observe_deployment",
    }


def cancel_workspace_deployment(
    credential: WorkspaceCredential,
    deployment_id: DeploymentReference,
) -> dict[str, object]:
    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                UPDATE digital_asset.deployments
                SET status='cancelled', completed_at=now()
                WHERE workspace_id=:workspace_id
                  AND (
                    CAST(id AS text)=:deployment_reference
                    OR CAST(legacy_id AS text)=:deployment_reference
                  )
                  AND status IN ('queued','building')
                RETURNING *
                """
                ),
                {
                    **_deployment_reference_params(deployment_id),
                    "workspace_id": credential.workspace_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            current = session.execute(
                text(
                    "SELECT status FROM digital_asset.deployments "
                    "WHERE workspace_id=:workspace_id AND ("
                    "CAST(id AS text)=:deployment_reference OR "
                    "CAST(legacy_id AS text)=:deployment_reference)"
                ),
                {
                    **_deployment_reference_params(deployment_id),
                    "workspace_id": credential.workspace_id,
                },
            ).scalar_one_or_none()
            if current is None:
                raise HTTPException(status_code=404, detail="Deployment not found")
            raise HTTPException(
                status_code=409, detail=f"Deployment cannot be cancelled from {current}"
            )
        resolved_id = UUID(str(row["id"]))
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence),0)+1 "
                    "FROM digital_asset.deployment_events WHERE deployment_id=:id"
                ),
                {"id": resolved_id},
            ).scalar_one()
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.deployment_events(
                  deployment_id, tenant_id, sequence, event_type, payload
                ) VALUES (:id,:tenant_id,:sequence,'cancelled',CAST(:payload AS jsonb))
                """
            ),
            {
                "id": resolved_id,
                "tenant_id": credential.tenant_id,
                "sequence": sequence,
                "payload": json.dumps({"credential_id": str(credential.credential_id)}),
            },
        )
    return {"ok": True, "deployment": _deployment_public(dict(row))}


def _record_deployment_event(
    session: object,
    *,
    deployment_id: UUID,
    tenant_id: UUID,
    event_type: str,
    payload: dict[str, object],
) -> None:
    sequence = int(
        session.execute(
            text(
                "SELECT COALESCE(max(sequence),0)+1 "
                "FROM digital_asset.deployment_events WHERE deployment_id=:id"
            ),
            {"id": deployment_id},
        ).scalar_one()
    )
    session.execute(
        text(
            """
            INSERT INTO digital_asset.deployment_events(
              deployment_id, tenant_id, sequence, event_type, payload
            ) VALUES (:id,:tenant_id,:sequence,:event_type,CAST(:payload AS jsonb))
            """
        ),
        {
            "id": deployment_id,
            "tenant_id": tenant_id,
            "sequence": sequence,
            "event_type": event_type,
            "payload": json.dumps(payload),
        },
    )


def _verify_public_deployment_route(
    public_url: str,
    deployment_id: UUID,
    health_path: str,
    *,
    timeout_seconds: int = 20,
) -> dict[str, object]:
    parsed = urlsplit(public_url)
    route = (parsed.path or "/").rstrip("/") + "/" + health_path.lstrip("/")
    if parsed.query:
        route += "?" + parsed.query
    candidates = [
        f"http://api:8080{route}",
        f"http://warehouse-os-api-green:8080{route}",
        f"http://warehouse-os-api-blue:8080{route}",
        public_url,
    ]
    deadline = time.monotonic() + max(1, timeout_seconds)
    last = "not reachable"
    while time.monotonic() < deadline:
        for candidate in candidates:
            try:
                response = httpx.get(
                    candidate,
                    headers={"host": parsed.netloc},
                    timeout=3,
                    follow_redirects=False,
                )
                observed = response.headers.get("x-warehouse-deployment")
                if 200 <= response.status_code < 400 and observed == str(deployment_id):
                    return {
                        "url": public_url,
                        "health_path": health_path,
                        "status": response.status_code,
                        "deployment_id": observed,
                    }
                last = f"HTTP {response.status_code} deployment={observed or 'none'}"
            except httpx.HTTPError as exc:
                last = exc.__class__.__name__
        time.sleep(1)
    raise RuntimeError(f"Public Runtime route verification failed: {last}")


def activate_workspace_deployment(
    credential: WorkspaceCredential,
    deployment_id: DeploymentReference,
) -> dict[str, object]:
    """Switch traffic, verify the exact revision, and restore the former route on failure."""

    credential.require("deploy:write")
    with tenant_session(credential.tenant_id) as session:
        previous_active_deployment_id = session.execute(
            text(
                "SELECT active_deployment_id FROM digital_asset.workspaces "
                "WHERE id=:workspace_id FOR UPDATE"
            ),
            {"workspace_id": credential.workspace_id},
        ).scalar_one()
        deployment = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.deployments
                WHERE workspace_id=:workspace_id
                  AND (
                    CAST(id AS text)=:deployment_reference
                    OR CAST(legacy_id AS text)=:deployment_reference
                  )
                  AND status='ready' AND health='healthy'
                """
                ),
                {
                    **_deployment_reference_params(deployment_id),
                    "workspace_id": credential.workspace_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if deployment is None:
            raise HTTPException(
                status_code=409, detail="Only a healthy deployment can be activated"
            )
        deployment_result = (
            deployment.get("result") if isinstance(deployment.get("result"), dict) else {}
        )
        if str(deployment_result.get("execution_mode") or "service") == "job":
            raise HTTPException(status_code=409, detail="A one-shot job cannot receive traffic")
        requested_config = deployment.get("requested_config")
        requested_config = requested_config if isinstance(requested_config, dict) else {}
        compatibility_contract = requested_config.get("compatibility_contract")
        compatibility_contract = (
            compatibility_contract if isinstance(compatibility_contract, dict) else {}
        )
        deployment_contract = (
            compatibility_contract.get("deployment")
            if isinstance(compatibility_contract.get("deployment"), dict)
            else {}
        )
        if bool(deployment_contract.get("require_acceptance_before_activation")):
            if not _acceptance_ready_for_activation(dict(deployment)):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "deployment_acceptance_required",
                        "deployment_id": str(deployment["id"]),
                        "contract_digest": compatibility_contract.get("contract_digest"),
                        "next_action": (
                            f"POST /api/workspaces/v1/deployments/{deployment['id']}/accept"
                        ),
                    },
                )
        database_release = observe_database_release_gate(
            session,
            credential.workspace_id,
            deployment_config=requested_config,
        )
        if not bool(database_release["ready"]):
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "database_release_gate_blocked",
                    "database_release": _json_safe(database_release),
                },
            )
        resolved_id = UUID(str(deployment["id"]))
        session.execute(
            text(
                """
                UPDATE digital_asset.workspaces
                SET active_deployment_id=:deployment_id, runtime_status='ready'
                WHERE id=:workspace_id
                """
            ),
            {"deployment_id": resolved_id, "workspace_id": credential.workspace_id},
        )
        mark_pages_deployment_active(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=credential.workspace_id,
            deployment_id=resolved_id,
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.deployments
                SET result=result || jsonb_build_object(
                  'activation_requested', true,
                  'activation_deferred', true,
                  'public_route_verified', false,
                  'previous_active_deployment_id', CAST(:previous AS text),
                  'activation_started_at', now()
                )
                WHERE id=:deployment_id
                """
            ),
            {
                "deployment_id": resolved_id,
                "previous": (
                    str(previous_active_deployment_id)
                    if previous_active_deployment_id is not None
                    else None
                ),
            },
        )
        _record_deployment_event(
            session,
            deployment_id=resolved_id,
            tenant_id=credential.tenant_id,
            event_type="route_activation_started",
            payload={
                "credential_id": str(credential.credential_id),
                "manual_activation": True,
                "previous_active_deployment_id": (
                    str(previous_active_deployment_id)
                    if previous_active_deployment_id is not None
                    else None
                ),
            },
        )

    public_url = str(deployment.get("public_url") or "")
    health_path = str(
        deployment_result.get("health_path") or requested_config.get("health_path") or "/"
    )
    try:
        route_evidence = _verify_public_deployment_route(
            public_url,
            resolved_id,
            health_path,
        )
    except RuntimeError as exc:
        with tenant_session(credential.tenant_id) as session:
            current = session.execute(
                text(
                    "SELECT active_deployment_id FROM digital_asset.workspaces "
                    "WHERE id=:workspace_id FOR UPDATE"
                ),
                {"workspace_id": credential.workspace_id},
            ).scalar_one()
            rolled_back = current == resolved_id
            if rolled_back:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET active_deployment_id=CAST(:previous AS uuid),
                            runtime_status=CASE WHEN CAST(:previous AS uuid) IS NULL
                              THEN 'failed' ELSE 'ready' END
                        WHERE id=:workspace_id AND active_deployment_id=:deployment_id
                        """
                    ),
                    {
                        "previous": (
                            str(previous_active_deployment_id)
                            if previous_active_deployment_id is not None
                            else None
                        ),
                        "workspace_id": credential.workspace_id,
                        "deployment_id": resolved_id,
                    },
                )
                set_pages_deployment_pointer(
                    session,
                    tenant_id=credential.tenant_id,
                    workspace_id=credential.workspace_id,
                    deployment_id=previous_active_deployment_id,
                )
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET status='failed',health='unhealthy',
                        result=result || jsonb_build_object(
                          'activation_deferred', true,
                          'public_route_verified', false,
                          'activation_error', CAST(:error AS text),
                          'activation_rolled_back', CAST(:rolled_back AS boolean)
                        )
                    WHERE id=:deployment_id
                    """
                ),
                {
                    "deployment_id": resolved_id,
                    "error": str(exc)[:1000],
                    "rolled_back": rolled_back,
                },
            )
            _record_deployment_event(
                session,
                deployment_id=resolved_id,
                tenant_id=credential.tenant_id,
                event_type=(
                    "route_activation_rolled_back" if rolled_back else "route_activation_superseded"
                ),
                payload={
                    "credential_id": str(credential.credential_id),
                    "error": str(exc)[:1000],
                    "restored_deployment_id": (
                        str(previous_active_deployment_id)
                        if rolled_back and previous_active_deployment_id is not None
                        else None
                    ),
                },
            )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "public_route_verification_failed",
                "deployment_id": str(resolved_id),
                "previous_deployment_restored": rolled_back,
                "message": str(exc),
            },
        ) from exc

    with tenant_session(credential.tenant_id) as session:
        current = session.execute(
            text(
                "SELECT active_deployment_id FROM digital_asset.workspaces "
                "WHERE id=:workspace_id FOR UPDATE"
            ),
            {"workspace_id": credential.workspace_id},
        ).scalar_one()
        if current != resolved_id:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "activation_superseded",
                    "deployment_id": str(resolved_id),
                    "active_deployment_id": str(current) if current is not None else None,
                },
            )
        updated = (
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET result=result || jsonb_build_object(
                      'activation_requested', true,
                      'activation_deferred', false,
                      'public_route_verified', true,
                      'activated_at', now(),
                      'activation_rolled_back', false
                    )
                    WHERE id=:deployment_id
                    RETURNING *
                    """
                ),
                {"deployment_id": resolved_id},
            )
            .mappings()
            .one()
        )
        _record_deployment_event(
            session,
            deployment_id=resolved_id,
            tenant_id=credential.tenant_id,
            event_type="route_activated",
            payload={
                "credential_id": str(credential.credential_id),
                "manual_activation": True,
                **route_evidence,
            },
        )
        _record_deployment_event(
            session,
            deployment_id=resolved_id,
            tenant_id=credential.tenant_id,
            event_type="public_route_verified",
            payload={
                "credential_id": str(credential.credential_id),
                "manual_activation": True,
                **route_evidence,
            },
        )
    return {
        "ok": True,
        "deployment": _deployment_public(dict(updated)),
        "database_release": _json_safe(database_release),
        "route_verification": _json_safe(route_evidence),
        "active": True,
    }


def active_workspace_runtime(
    tenant_slug: str,
    workspace_key: str,
    *,
    register_request: bool = True,
) -> dict[str, object] | None:
    """Return the server-internal route for the workspace's verified revision."""

    with system_session() as session:
        tenant_id = session.execute(
            text("SELECT id FROM iam.tenants WHERE slug=:slug AND status='active'"),
            {"slug": tenant_slug.strip().lower()},
        ).scalar_one_or_none()
    if tenant_id is None:
        return None
    with tenant_session(tenant_id) as session:
        resolved = (
            session.execute(
                text(
                    """
                SELECT d.id, d.result, d.public_url, d.release_digest,
                       d.runtime_profile_key, d.runtime_state,
                       d.runtime_last_request_at
                FROM digital_asset.workspaces AS w
                JOIN digital_asset.deployments AS d ON d.id=w.active_deployment_id
                JOIN digital_asset.assets AS a ON a.id=w.asset_id
                WHERE w.workspace_key=:workspace_key AND w.status='active'
                  AND a.status!='archived'
                  AND d.status='ready' AND d.health='healthy'
                """
                ),
                {"workspace_key": workspace_key.strip().lower()},
            )
            .mappings()
            .one_or_none()
        )
        if resolved is None:
            return None
        row = dict(resolved)
        result = row["result"] if isinstance(row["result"], dict) else {}
        kind = str(result.get("runtime_kind") or "")
        if register_request and kind in {"python", "node", "container"}:
            touch_seconds = max(1, int(get_settings().runtime_activity_touch_seconds))
            lifecycle = (
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments
                        SET runtime_last_request_at=CASE
                              WHEN runtime_last_request_at IS NULL
                                OR runtime_last_request_at
                                  < now() - make_interval(secs => :touch_seconds)
                              THEN now() ELSE runtime_last_request_at END,
                            runtime_state=CASE
                              WHEN runtime_state IN ('suspended','suspending','error')
                              THEN 'wake_requested' ELSE runtime_state END,
                            runtime_wake_requested_at=CASE
                              WHEN runtime_state IN ('suspended','suspending','error')
                              THEN now() ELSE runtime_wake_requested_at END,
                            runtime_state_changed_at=CASE
                              WHEN runtime_state IN ('suspended','suspending','error')
                              THEN now() ELSE runtime_state_changed_at END,
                            runtime_wake_error=CASE
                              WHEN runtime_state IN ('suspended','suspending','error')
                              THEN NULL ELSE runtime_wake_error END
                        WHERE id=:id
                        RETURNING runtime_state,runtime_last_request_at
                        """
                    ),
                    {"id": row["id"], "touch_seconds": touch_seconds},
                )
                .mappings()
                .one()
            )
            row.update(dict(lifecycle))
    result = row["result"] if isinstance(row["result"], dict) else {}
    if result.get("public_route") is False:
        return None
    kind = str(result.get("runtime_kind") or "")
    if kind == "static" and result.get("runtime_rel_path"):
        return {
            "kind": "static",
            "runtime_rel_path": str(result["runtime_rel_path"]),
            "deployment_id": str(row["id"]),
            "release_digest": row["release_digest"],
            "runtime_state": "not_applicable",
        }
    if kind in {"python", "node", "container"} and (
        result.get("internal_url") or result.get("internal_urls")
    ):
        return {
            "kind": "proxy",
            "internal_url": str(result.get("internal_url") or result.get("internal_urls")[0]),
            "internal_urls": [
                str(item)
                for item in (result.get("internal_urls") or [result.get("internal_url")])
                if item
            ],
            "deployment_id": str(row["id"]),
            "release_digest": row["release_digest"],
            "runtime_state": str(row.get("runtime_state") or "running"),
            "health_path": str(result.get("health_path") or "/health"),
        }
    return None
