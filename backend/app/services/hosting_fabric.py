"""Data-driven advanced hosting resources controlled by one workspace key.

The fabric keeps desired state separate from observed state.  Every mutation is
tenant/workspace bound, idempotent and audited.  Provider-specific execution is
small and explicit; unsupported infrastructure becomes a durable ``blocked``
result instead of a false success.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import tarfile
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services import hosted_database
from app.services.database_release import (
    observe_database_release_gate,
    workspace_database_policy,
)
from app.services.digital_asset_hosting import WORKSPACE_ALL_SCOPES, WorkspaceCredential
from app.services.object_storage import HDD_PROVIDER_KEY, object_store_for_provider
from app.services.source_packages import inspect_source_archive
from app.services.workspace_deployments import (
    register_workspace_source,
    workspace_source_upload_target,
)

RESOURCE_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,159}$")
ENV_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,126}$")
HOSTNAME_RE = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")
IMAGE_RE = re.compile(
    r"^(?:[a-z0-9.-]+(?::[0-9]{1,5})?/)?[a-z0-9][a-z0-9._/-]{0,240}(?::[A-Za-z0-9._-]{1,128}|@sha256:[a-f0-9]{64})?$"
)
MAX_REPLICAS = 8
MAX_SERVICES = 16
RESERVED_ENVIRONMENT = frozenset(
    {
        "DATABASE_URL",
        "PORT",
        "WAREHOUSE_RUNTIME_SECRET",
        "WAREHOUSE_WORKSPACE_ID",
        "WAREHOUSE_WORKSPACE_KEY",
        "DAM_WORKSPACE",
    }
)
SECRETISH = ("SECRET", "PASSWORD", "TOKEN", "API_KEY", "PRIVATE_KEY", "CREDENTIAL")


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.integration_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str, settings: Settings) -> str:
    return "fernet:v1:" + _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def _decrypt(value: str, settings: Settings) -> str:
    if not value.startswith("fernet:v1:"):
        raise HTTPException(status_code=409, detail="Secret ciphertext format is invalid")
    try:
        return (
            _fernet(settings)
            .decrypt(value.removeprefix("fernet:v1:").encode("ascii"))
            .decode("utf-8")
        )
    except InvalidToken as exc:
        raise HTTPException(
            status_code=409, detail="Secret ciphertext cannot be decrypted"
        ) from exc


def fabric_manifest() -> dict[str, object]:
    with system_session() as session:
        drivers = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT driver_key,resource_kind,label,description,execution_mode,"
                    "required_scope,desired_schema,capability_contract,revision "
                    "FROM platform.hosting_fabric_drivers WHERE enabled ORDER BY resource_kind"
                )
            ).mappings()
        ]
    return {
        "schema": "warehouse.hosting-fabric.v1",
        "desired_observed_separation": True,
        "workspace_key_boundary": True,
        "drivers": drivers,
    }


def _workspace(session: object, credential: WorkspaceCredential) -> dict[str, object]:
    row = (
        session.execute(
            text("SELECT * FROM digital_asset.workspaces WHERE id=:id AND status='active'"),
            {"id": credential.workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return dict(row)


def _driver(session: object, kind: str) -> dict[str, object]:
    row = (
        session.execute(
            text(
                "SELECT * FROM platform.hosting_fabric_drivers "
                "WHERE resource_kind=:kind AND enabled"
            ),
            {"kind": kind},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(
            status_code=422, detail={"reason": "unsupported_resource_kind", "kind": kind}
        )
    return dict(row)


def _claim_domain(session: object, credential: WorkspaceCredential, hostname: str) -> None:
    """Atomically reserve one hostname without exposing another tenant's owner."""

    existing = (
        session.execute(
            text(
                "SELECT workspace_id FROM digital_asset.hosting_domain_claims "
                "WHERE hostname=:hostname"
            ),
            {"hostname": hostname},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if UUID(str(existing["workspace_id"])) == credential.workspace_id:
            return
        raise HTTPException(
            status_code=409,
            detail={"reason": "hostname_claimed_by_another_workspace"},
        )
    claimed = session.execute(
        text(
            "INSERT INTO digital_asset.hosting_domain_claims("
            "hostname,tenant_id,workspace_id) VALUES (:hostname,:tenant_id,:workspace_id) "
            "ON CONFLICT (hostname) DO NOTHING RETURNING hostname"
        ),
        {
            "hostname": hostname,
            "tenant_id": credential.tenant_id,
            "workspace_id": credential.workspace_id,
        },
    ).scalar_one_or_none()
    if claimed is None:
        raise HTTPException(
            status_code=409,
            detail={"reason": "hostname_claimed_by_another_workspace"},
        )


def _event(
    session: object,
    *,
    action_id: UUID,
    tenant_id: UUID,
    event_type: str,
    payload: dict[str, object],
) -> None:
    sequence = int(
        session.execute(
            text(
                "SELECT COALESCE(max(sequence),0)+1 FROM digital_asset.hosting_action_events "
                "WHERE action_id=:id"
            ),
            {"id": action_id},
        ).scalar_one()
    )
    session.execute(
        text(
            "INSERT INTO digital_asset.hosting_action_events("
            "tenant_id,action_id,sequence,event_type,payload) "
            "VALUES (:tenant_id,:action_id,:sequence,:event_type,CAST(:payload AS jsonb))"
        ),
        {
            "tenant_id": tenant_id,
            "action_id": action_id,
            "sequence": sequence,
            "event_type": event_type,
            "payload": _canonical(payload),
        },
    )


def _upsert_resource(
    session: object,
    credential: WorkspaceCredential,
    driver: dict[str, object],
    *,
    resource_key: str,
    desired: dict[str, object],
) -> dict[str, object]:
    if not RESOURCE_KEY_RE.fullmatch(resource_key):
        raise HTTPException(status_code=422, detail="Invalid resource_key")
    row = (
        session.execute(
            text(
                """
                INSERT INTO digital_asset.hosting_resources(
                  id,tenant_id,workspace_id,resource_kind,resource_key,driver_key,
                  desired_state,status,created_by_credential_id
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:kind,:key,:driver,
                  CAST(:desired AS jsonb),'planned',:credential_id
                )
                ON CONFLICT (tenant_id,workspace_id,resource_kind,resource_key)
                DO UPDATE SET
                  driver_key=EXCLUDED.driver_key,
                  desired_state=EXCLUDED.desired_state,
                  status='planned',last_error=NULL,
                  revision=digital_asset.hosting_resources.revision+1,
                  created_by_credential_id=EXCLUDED.created_by_credential_id
                RETURNING *
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": credential.tenant_id,
                "workspace_id": credential.workspace_id,
                "kind": driver["resource_kind"],
                "key": resource_key,
                "driver": driver["driver_key"],
                "desired": _canonical(desired),
                "credential_id": credential.credential_id,
            },
        )
        .mappings()
        .one()
    )
    return dict(row)


def _begin_action(
    session: object,
    credential: WorkspaceCredential,
    resource: dict[str, object],
    *,
    action_type: str,
    request: dict[str, object],
    idempotency_key: str | None,
) -> tuple[dict[str, object], bool]:
    digest = hashlib.sha256(_canonical(request).encode("utf-8")).hexdigest()
    if idempotency_key:
        existing = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.hosting_actions "
                    "WHERE workspace_id=:workspace_id AND idempotency_key=:key"
                ),
                {"workspace_id": credential.workspace_id, "key": idempotency_key},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            if str(existing["request_digest"]) != digest:
                raise HTTPException(status_code=409, detail="Idempotency key request mismatch")
            return dict(existing), True
    action_id = uuid4()
    row = dict(
        session.execute(
            text(
                """
                INSERT INTO digital_asset.hosting_actions(
                  id,tenant_id,workspace_id,resource_id,action_type,idempotency_key,
                  request_digest,status,request,requested_by_credential_id
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:resource_id,:action_type,:key,
                  :digest,'running',CAST(:request AS jsonb),:credential_id
                ) RETURNING *
                """
            ),
            {
                "id": action_id,
                "tenant_id": credential.tenant_id,
                "workspace_id": credential.workspace_id,
                "resource_id": resource["id"],
                "action_type": action_type,
                "key": idempotency_key,
                "digest": digest,
                "request": _canonical(request),
                "credential_id": credential.credential_id,
            },
        )
        .mappings()
        .one()
    )
    _event(
        session,
        action_id=action_id,
        tenant_id=credential.tenant_id,
        event_type="requested",
        payload={
            "resource_kind": resource["resource_kind"],
            "resource_key": resource["resource_key"],
        },
    )
    return row, False


def _finish(
    session: object,
    credential: WorkspaceCredential,
    resource: dict[str, object],
    action: dict[str, object],
    *,
    status: str,
    observed: dict[str, object],
    error: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    resource_status = (
        "ready" if status == "succeeded" else "blocked" if status == "blocked" else "failed"
    )
    resource_row = dict(
        session.execute(
            text(
                """
                UPDATE digital_asset.hosting_resources SET
                  status=:status,observed_state=CAST(:observed AS jsonb),
                  last_error=CAST(:error AS jsonb),revision=revision+1
                WHERE id=:id RETURNING *
                """
            ),
            {
                "id": resource["id"],
                "status": resource_status,
                "observed": _canonical(observed),
                "error": _canonical(error) if error else None,
            },
        )
        .mappings()
        .one()
    )
    action_row = dict(
        session.execute(
            text(
                """
                UPDATE digital_asset.hosting_actions SET
                  status=:status,result=CAST(:result AS jsonb),error=CAST(:error AS jsonb),
                  started_at=COALESCE(started_at,now()),completed_at=now()
                WHERE id=:id RETURNING *
                """
            ),
            {
                "id": action["id"],
                "status": status,
                "result": _canonical(observed),
                "error": _canonical(error) if error else None,
            },
        )
        .mappings()
        .one()
    )
    _event(
        session,
        action_id=UUID(str(action["id"])),
        tenant_id=credential.tenant_id,
        event_type=status,
        payload={"observed": observed, "error": error},
    )
    return resource_row, action_row


def _validate_environment(spec: dict[str, object]) -> dict[str, object]:
    variables = spec.get("variables")
    if not isinstance(variables, dict) or not variables or len(variables) > 128:
        raise HTTPException(
            status_code=422, detail="environment.variables must contain 1-128 values"
        )
    clean: dict[str, str] = {}
    for raw_name, raw_value in variables.items():
        name = str(raw_name).strip().upper()
        if (
            not ENV_NAME_RE.fullmatch(name)
            or name in RESERVED_ENVIRONMENT
            or name.startswith("WAREHOUSE_")
        ):
            raise HTTPException(
                status_code=422, detail=f"Reserved or invalid environment name: {name}"
            )
        if any(token in name for token in SECRETISH):
            raise HTTPException(
                status_code=422, detail=f"{name} must be stored as a secret resource"
            )
        value = str(raw_value)
        if len(value.encode("utf-8")) > 16_384:
            raise HTTPException(status_code=422, detail=f"Environment value is too large: {name}")
        clean[name] = value
    return {"component": str(spec.get("component") or "*"), "variables": clean}


def _validate_secret(
    spec: dict[str, object], *, allow_database_url: bool = False
) -> tuple[dict[str, object], str]:
    name = str(spec.get("name") or "").strip().upper()
    value = spec.get("value")
    if not ENV_NAME_RE.fullmatch(name) or (
        name in RESERVED_ENVIRONMENT
        and not (allow_database_url and name == "DATABASE_URL")
    ):
        raise HTTPException(status_code=422, detail="Invalid or reserved secret name")
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 65_536:
        raise HTTPException(status_code=422, detail="Secret value must be 1-65536 bytes")
    return {"name": name, "component": str(spec.get("component") or "*")}, value


def _validate_scaling(spec: dict[str, object]) -> dict[str, object]:
    minimum = int(spec.get("min_replicas") or 1)
    maximum = int(spec.get("max_replicas") or minimum)
    target = int(spec.get("target_cpu_percent") or 70)
    if not 1 <= minimum <= maximum <= MAX_REPLICAS:
        raise HTTPException(
            status_code=422, detail=f"Replicas must satisfy 1 <= min <= max <= {MAX_REPLICAS}"
        )
    if not 10 <= target <= 95:
        raise HTTPException(status_code=422, detail="target_cpu_percent must be 10-95")
    return {
        "component": str(spec.get("component") or "api"),
        "min_replicas": minimum,
        "max_replicas": maximum,
        "target_cpu_percent": target,
        "cooldown_seconds": max(15, min(int(spec.get("cooldown_seconds") or 60), 3600)),
    }


def _safe_relative(value: object, *, default: str) -> str:
    clean = str(value or default).strip().replace("\\", "/")
    path = PurePosixPath(clean)
    if path.is_absolute() or ".." in path.parts or not clean or len(clean) > 240:
        raise HTTPException(status_code=422, detail="Unsafe source-relative path")
    return path.as_posix()


def _validate_container(spec: dict[str, object], *, compose: bool) -> dict[str, object]:
    if compose:
        return {
            "file": _safe_relative(spec.get("file"), default="compose.yaml"),
            "route_service": str(spec.get("route_service") or "web")[:80],
            "max_services": min(
                MAX_SERVICES, max(1, int(spec.get("max_services") or MAX_SERVICES))
            ),
        }
    image = str(spec.get("image") or "").strip()
    dockerfile = _safe_relative(spec.get("dockerfile"), default="Dockerfile")
    if image and not IMAGE_RE.fullmatch(image):
        raise HTTPException(status_code=422, detail="Invalid OCI image reference")
    if not image and not dockerfile:
        raise HTTPException(status_code=422, detail="Container requires image or Dockerfile")
    return {
        "image": image or None,
        "dockerfile": dockerfile,
        "command": str(spec.get("command") or "")[:4096] or None,
        "port": max(1, min(int(spec.get("port") or 8080), 65535)),
        "health_path": str(spec.get("health_path") or "/health")[:240],
        "component": str(spec.get("component") or "api")[:80],
    }


def _database_binding(session: object, credential: WorkspaceCredential) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT b.*, c.secret_ciphertext, c.credential_kind
                FROM digital_asset.database_bindings AS b
                LEFT JOIN digital_asset.database_credentials AS c
                  ON c.database_binding_id=b.id
                WHERE b.workspace_id=:workspace_id AND b.status='ready'
                ORDER BY b.is_default DESC,b.created_at LIMIT 1
                """
            ),
            {"workspace_id": credential.workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None or str(row.get("provider_key")) not in (
        hosted_database.POSTGRESQL_PROVIDER_KEYS
    ):
        raise HTTPException(
            status_code=409, detail="A ready PostgreSQL workspace database is required"
        )
    return dict(row)


def _apply_secret(
    session: object,
    credential: WorkspaceCredential,
    resource: dict[str, object],
    spec: dict[str, object],
    settings: Settings,
    *,
    allow_database_url: bool = False,
) -> dict[str, object]:
    public, value = _validate_secret(
        spec,
        allow_database_url=allow_database_url,
    )
    name = str(public["name"])
    version = int(
        session.execute(
            text(
                "SELECT COALESCE(max(version),0)+1 FROM digital_asset.hosting_secret_versions "
                "WHERE workspace_id=:workspace_id AND name=:name"
            ),
            {"workspace_id": credential.workspace_id, "name": name},
        ).scalar_one()
    )
    session.execute(
        text(
            "UPDATE digital_asset.hosting_secret_versions SET active=false,revoked_at=now() "
            "WHERE workspace_id=:workspace_id AND name=:name AND active"
        ),
        {"workspace_id": credential.workspace_id, "name": name},
    )
    session.execute(
        text(
            """
            INSERT INTO digital_asset.hosting_secret_versions(
              id,tenant_id,workspace_id,resource_id,name,version,ciphertext,
              value_digest,created_by_credential_id
            ) VALUES (
              :id,:tenant_id,:workspace_id,:resource_id,:name,:version,:ciphertext,
              :digest,:credential_id
            )
            """
        ),
        {
            "id": uuid4(),
            "tenant_id": credential.tenant_id,
            "workspace_id": credential.workspace_id,
            "resource_id": resource["id"],
            "name": name,
            "version": version,
            "ciphertext": _encrypt(value, settings),
            "digest": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "credential_id": credential.credential_id,
        },
    )
    return {**public, "version": version, "configured": True, "plaintext_exposed": False}


def _apply_migration(
    session: object,
    credential: WorkspaceCredential,
    spec: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    version = str(spec.get("version") or "").strip()[:120]
    source = str(spec.get("sql") or "").strip()
    if not version or not source:
        raise HTTPException(status_code=422, detail="database_migration requires version and sql")
    checksum = hashlib.sha256(source.encode("utf-8")).hexdigest()
    supplied = str(spec.get("checksum") or "").lower().strip()
    if supplied and supplied != checksum:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "migration_checksum_mismatch",
                "expected": supplied,
                "actual": checksum,
            },
        )
    binding = _database_binding(session, credential)
    existing = (
        session.execute(
            text(
                "SELECT id,checksum,status,applied_at,error "
                "FROM digital_asset.database_migration_history "
                "WHERE workspace_id=:workspace_id "
                "AND database_binding_id=:database_id AND version=:version"
            ),
            {
                "workspace_id": credential.workspace_id,
                "database_id": binding["id"],
                "version": version,
            },
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if str(existing["checksum"]) != checksum:
            raise HTTPException(
                status_code=409, detail="Migration version already has another checksum"
            )
        if str(existing["status"]) == "applied":
            return {
                "version": version,
                "checksum": checksum,
                "idempotent_replay": True,
                "applied_at": existing["applied_at"],
            }
        history_id = existing["id"]
        session.execute(
            text(
                "UPDATE digital_asset.database_migration_history "
                "SET error='migration_started',applied_at=now() WHERE id=:id"
            ),
            {"id": history_id},
        )
    else:
        history_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO digital_asset.database_migration_history(
                  id,tenant_id,workspace_id,database_binding_id,version,checksum,
                  statement_count,status,error,applied_by_credential_id
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:database_id,:version,:checksum,
                  1,'failed','migration_started',:credential_id
                )
                """
            ),
            {
                "id": history_id,
                "tenant_id": credential.tenant_id,
                "workspace_id": credential.workspace_id,
                "database_id": binding["id"],
                "version": version,
                "checksum": checksum,
                "credential_id": credential.credential_id,
            },
        )
    backup = (
        session.execute(
            text(
                """
                SELECT id,sha256,metadata,completed_at
                FROM digital_asset.database_backups
                WHERE workspace_id=:workspace_id
                  AND database_binding_id=:database_id
                  AND status='ready'
                ORDER BY completed_at DESC NULLS LAST,created_at DESC
                LIMIT 1
                """
            ),
            {
                "workspace_id": credential.workspace_id,
                "database_id": binding["id"],
            },
        )
        .mappings()
        .one_or_none()
    )
    backup_metadata = (
        dict(backup["metadata"])
        if backup is not None and isinstance(backup["metadata"], dict)
        else {}
    )
    if (
        backup is None
        or not backup.get("sha256")
        or not bool(backup_metadata.get("checksum_verified"))
        or not bool(backup_metadata.get("restore_verified"))
    ):
        session.execute(
            text(
                "UPDATE digital_asset.database_migration_history "
                "SET status='failed',error='verified_backup_required',applied_at=now() "
                "WHERE id=:id"
            ),
            {"id": history_id},
        )
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "verified_database_backup_required",
                "version": version,
                "history_id": str(history_id),
                "required_evidence": ["sha256", "checksum_verified", "restore_verified"],
                "next_action": "create_logical_backup",
            },
        )
    try:
        capability_evidence = hosted_database.reconcile_capabilities(
            session, binding, settings=settings
        )
        applied = hosted_database.execute_migration(
            session, binding, migration_sql=source, settings=settings
        )
    except Exception as exc:
        session.execute(
            text(
                "UPDATE digital_asset.database_migration_history "
                "SET status='failed',error=:error,applied_at=now() WHERE id=:id"
            ),
            {"id": history_id, "error": f"{type(exc).__name__}: {exc}"[:4000]},
        )
        status_code = (
            503
            if isinstance(exc, hosted_database.HostedDatabaseUnavailable)
            else 422
        )
        raise HTTPException(
            status_code=status_code,
            detail={
                "reason": "database_migration_failed",
                "version": version,
                "history_id": str(history_id),
                "message": str(exc),
            },
        ) from exc
    session.execute(
        text(
            """
            UPDATE digital_asset.database_migration_history
            SET statement_count=:statement_count,status='applied',error=NULL,applied_at=now()
            WHERE id=:id
            """
        ),
        {
            "id": history_id,
            "statement_count": applied["statement_count"],
        },
    )
    return {
        "version": version,
        "checksum": checksum,
        "history_id": str(history_id),
        "backup_id": str(backup["id"]),
        "backup_sha256": str(backup["sha256"]),
        "capabilities": capability_evidence,
        **applied,
        "idempotent_replay": False,
    }


def _backup_object_path(settings: Settings, object_key: str) -> Path:
    return object_store_for_provider(settings, HDD_PROVIDER_KEY).path_for(object_key)


def _apply_backup(
    session: object,
    credential: WorkspaceCredential,
    spec: dict[str, object],
    settings: Settings,
) -> tuple[str, dict[str, object], dict[str, object] | None]:
    operation = str(spec.get("action") or "create").lower()
    mode = str(spec.get("mode") or "logical").lower()
    destination = str(spec.get("destination") or "local").lower()
    if mode not in {"logical", "point_in_time"}:
        raise HTTPException(status_code=422, detail="backup.mode must be logical or point_in_time")
    if destination not in {"local", "remote"}:
        raise HTTPException(status_code=422, detail="backup.destination must be local or remote")
    if mode == "point_in_time" or destination == "remote":
        requested = {
            "operation": operation,
            "mode": mode,
            "destination": destination,
            "target_time": spec.get("target_time"),
        }
        error = {
            "reason": (
                "pitr_provider_unavailable"
                if mode == "point_in_time"
                else "remote_backup_provider_unavailable"
            ),
            "stage": "backup_provider",
            "requested": requested,
            "retryable": True,
            "required_provider_capabilities": (
                ["wal_archive", "base_backup", "timeline_restore"]
                if mode == "point_in_time"
                else ["encrypted_remote_object_store", "retention_policy"]
            ),
        }
        return "blocked", {"configured": False, "requested": requested}, error
    binding = _database_binding(session, credential)
    if str(binding["provider_key"]) == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "external_database_backup_is_customer_managed",
                "next_action": "use the external provider backup service",
            },
        )
    if operation == "create":
        backup_id = uuid4()
        retention_days = max(1, min(int(spec.get("retention_days") or 30), 3650))
        recovery_point = datetime.now(UTC)
        label = str(spec.get("label") or f"backup-{recovery_point.isoformat()}")[:160]
        session.execute(
            text(
                """
                INSERT INTO digital_asset.database_backups(
                  id,tenant_id,workspace_id,database_binding_id,label,backup_kind,
                  storage_provider,size_bytes,status,recovery_point,retention_until,
                  metadata,created_by_credential_id
                ) VALUES (
                  :id,:tenant_id,:workspace_id,:database_id,:label,'logical',
                  :provider,0,'creating',:recovery_point,:retention,
                  CAST(:metadata AS jsonb),:credential_id
                )
                """
            ),
            {
                "id": backup_id,
                "tenant_id": credential.tenant_id,
                "workspace_id": credential.workspace_id,
                "database_id": binding["id"],
                "label": label,
                "provider": HDD_PROVIDER_KEY,
                "recovery_point": recovery_point,
                "retention": recovery_point + timedelta(days=retention_days),
                "metadata": _canonical(
                    {
                        "stage": "creating",
                        "checksum_verified": False,
                        "restore_verified": False,
                    }
                ),
                "credential_id": credential.credential_id,
            },
        )
        try:
            with tempfile.TemporaryDirectory(prefix="warehouse-db-backup-") as temporary:
                dump = Path(temporary) / f"{backup_id}.dump"
                result = hosted_database.backup_database(binding, dump, settings=settings)
                backup_identity = dict(result["backup_identity"])
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.database_bindings
                        SET backup_role_ref=:backup_role_ref,
                            config=config || jsonb_build_object(
                              'backup_identity_observed',CAST(:evidence AS jsonb)
                            ),
                            revision=revision+1
                        WHERE id=:binding_id
                        """
                    ),
                    {
                        "binding_id": binding["id"],
                        "backup_role_ref": backup_identity["role"],
                        "evidence": _canonical(backup_identity),
                    },
                )
                store = object_store_for_provider(settings, HDD_PROVIDER_KEY)
                with dump.open("rb") as stream:
                    stored = store.put_stream(
                        tenant_id=credential.tenant_id,
                        stream=stream,
                        max_bytes=max(dump.stat().st_size, 1),
                        expected_sha256=str(result["sha256"]),
                    )
            verification = dict(result["restore_verification"])
            metadata = {
                "format": result["format"],
                "preserves_ownership": result["preserves_ownership"],
                "stage": "completed",
                "checksum_verified": stored.sha256 == result["sha256"],
                "restore_verified": bool(verification.get("verified")),
                "restore_verification": verification,
                "server_major": result["server_major"],
                "server_version": result["server_version"],
                "pg_dump_version": result["pg_dump_version"],
                "pg_restore_version": result["pg_restore_version"],
                "backup_identity": result["backup_identity"],
            }
            if not metadata["checksum_verified"] or not metadata["restore_verified"]:
                raise hosted_database.HostedDatabaseUnavailable(
                    "Backup evidence did not satisfy checksum and restore gates"
                )
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_backups
                    SET storage_provider=:provider,object_key=:object_key,sha256=:sha256,
                        size_bytes=:size,status='ready',metadata=CAST(:metadata AS jsonb),
                        completed_at=now()
                    WHERE id=:id
                    """
                ),
                {
                    "id": backup_id,
                    "provider": stored.provider_key,
                    "object_key": stored.object_key,
                    "sha256": stored.sha256,
                    "size": stored.size_bytes,
                    "metadata": _canonical(metadata),
                },
            )
        except Exception as exc:
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_backups
                    SET status='failed',metadata=metadata || CAST(:failure AS jsonb),
                        completed_at=now()
                    WHERE id=:id
                    """
                ),
                {
                    "id": backup_id,
                    "failure": _canonical(
                        {
                            "stage": "failed",
                            "error_type": type(exc).__name__,
                            "error": str(exc)[:1200],
                            "checksum_verified": False,
                            "restore_verified": False,
                        }
                    ),
                },
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "reason": "database_backup_failed",
                    "backup_id": str(backup_id),
                    "message": str(exc),
                    "retryable": True,
                },
            ) from exc
        return (
            "succeeded",
            {
                "backup_id": str(backup_id),
                "status": "ready",
                "mode": "logical",
                "destination": "local",
                "sha256": stored.sha256,
                "size_bytes": stored.size_bytes,
                "recovery_point": recovery_point.isoformat(),
                "verification": metadata,
            },
            None,
        )
    if operation != "restore":
        raise HTTPException(status_code=422, detail="backup.action must be create or restore")
    try:
        backup_id = UUID(str(spec.get("backup_id") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="restore requires backup_id") from exc
    backup = (
        session.execute(
            text(
                "SELECT * FROM digital_asset.database_backups "
                "WHERE id=:id AND workspace_id=:workspace_id AND status='ready'"
            ),
            {"id": backup_id, "workspace_id": credential.workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if backup is None:
        raise HTTPException(status_code=404, detail="Ready backup not found")
    path = _backup_object_path(settings, str(backup["object_key"]))
    if not path.is_file():
        raise HTTPException(status_code=409, detail="Backup object is unavailable")
    session.execute(
        text("UPDATE digital_asset.database_backups SET status='restoring' WHERE id=:id"),
        {"id": backup_id},
    )
    try:
        result = hosted_database.restore_database(
            binding, path, expected_sha256=str(backup["sha256"]), settings=settings
        )
        capability_evidence = hosted_database.reconcile_capabilities(
            session,
            binding,
            settings=settings,
        )
        result["capability_evidence"] = capability_evidence
    except Exception as exc:
        session.execute(
            text(
                "UPDATE digital_asset.database_backups SET status='failed',"
                "metadata=metadata || CAST(:failure AS jsonb),completed_at=now() WHERE id=:id"
            ),
            {
                "id": backup_id,
                "failure": _canonical(
                    {
                        "restore_failed_at": datetime.now(UTC).isoformat(),
                        "restore_error_type": type(exc).__name__,
                        "restore_error": str(exc)[:1200],
                    }
                ),
            },
        )
        raise HTTPException(
            status_code=503,
            detail={
                "reason": "database_restore_failed",
                "backup_id": str(backup_id),
                "message": str(exc),
            },
        ) from exc
    session.execute(
        text(
            "UPDATE digital_asset.database_backups SET status='ready',"
            "metadata=metadata || CAST(:restored AS jsonb),completed_at=now() WHERE id=:id"
        ),
        {
            "id": backup_id,
            "restored": _canonical(
                {
                    "last_restore_verified": True,
                    "last_restored_at": datetime.now(UTC).isoformat(),
                }
            ),
        },
    )
    return (
        "succeeded",
        {"backup_id": str(backup_id), "status": "restored", **result},
        None,
    )


def _validate_repository_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Repository URL must be credential-free HTTPS")
    try:
        addresses = {
            item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise HTTPException(
            status_code=422, detail="Repository hostname cannot be resolved"
        ) from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_unspecified
        ):
            raise HTTPException(
                status_code=422,
                detail="Repository hostname resolves to a private or unsafe address",
            )


def _secret_value(
    session: object,
    credential: WorkspaceCredential,
    name: str,
    settings: Settings,
) -> str:
    ciphertext = session.execute(
        text(
            "SELECT ciphertext FROM digital_asset.hosting_secret_versions "
            "WHERE workspace_id=:workspace_id AND name=:name AND active AND revoked_at IS NULL"
        ),
        {"workspace_id": credential.workspace_id, "name": name.upper()},
    ).scalar_one_or_none()
    if ciphertext is None:
        raise HTTPException(
            status_code=409, detail=f"Repository credential secret not found: {name}"
        )
    return _decrypt(str(ciphertext), settings)


def _apply_repository(
    session: object,
    credential: WorkspaceCredential,
    spec: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    url = str(spec.get("url") or "").strip()
    _validate_repository_url(url)
    ref = str(spec.get("ref") or "main").strip()[:240]
    secret_name = str(spec.get("credential_secret") or "").strip().upper()
    environment = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    if secret_name:
        token = _secret_value(session, credential, secret_name, settings)
        environment.update(
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.extraHeader",
                "GIT_CONFIG_VALUE_0": f"Authorization: Bearer {token}",
            }
        )
    target = workspace_source_upload_target(credential, settings)
    with tempfile.TemporaryDirectory(prefix="warehouse-git-sync-") as temporary:
        checkout = Path(temporary) / "repo"
        archive_path = Path(temporary) / "source.tar.gz"
        completed = subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                ref,
                "--no-tags",
                "--single-branch",
                url,
                str(checkout),
            ],
            check=False,
            capture_output=True,
            env=environment,
            timeout=300,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace")[-1200:]
            detail = re.sub(r"https://[^\s@]+@", "https://***@", detail)
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "git_clone_failed",
                    "message": detail.strip() or "Git clone failed",
                },
            )
        commit = subprocess.run(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        ).stdout.strip()
        shutil.rmtree(checkout / ".git", ignore_errors=True)
        with tarfile.open(archive_path, "w:gz") as archive:
            for item in sorted(checkout.rglob("*")):
                archive.add(item, arcname=item.relative_to(checkout), recursive=False)
        store = object_store_for_provider(settings, str(target["storage_provider"]))
        with archive_path.open("rb") as stream:
            stored = store.put_stream(
                tenant_id=credential.tenant_id,
                stream=stream,
                max_bytes=int(target["remaining_bytes"]),
            )
        archive = inspect_source_archive(
            store.path_for(stored.object_key),
            max_uncompressed_bytes=max(int(target["remaining_bytes"]), stored.size_bytes),
        )
        registered = register_workspace_source(
            credential,
            stored,
            filename="source.tar.gz",
            content_type="application/gzip",
            version_no=str(spec.get("version") or commit[:12]),
            component_name=str(spec.get("component") or "") or None,
            archive=archive,
        )
    return {
        "repository": url,
        "ref": ref,
        "commit": commit,
        "synced_at": datetime.now(UTC).isoformat(),
        "source": registered["source"],
        "credential_used": bool(secret_name),
        "credential_exposed": False,
    }


def _accelerator_observation(
    session: object, spec: dict[str, object]
) -> tuple[str, dict[str, object], dict[str, object] | None]:
    kind = str(spec.get("kind") or "gpu").lower()[:80]
    count = max(1, min(int(spec.get("count") or 1), 8))
    pool = (
        session.execute(
            text(
                "SELECT * FROM platform.accelerator_pools WHERE accelerator_kind=:kind "
                "AND status='online' AND allocatable_units>=:count "
                "ORDER BY allocatable_units DESC,pool_key LIMIT 1"
            ),
            {"kind": kind, "count": count},
        )
        .mappings()
        .one_or_none()
    )
    requested = {
        "kind": kind,
        "count": count,
        "memory_mb": int(spec.get("memory_mb") or 0) or None,
    }
    allocated = int(
        session.execute(
            text(
                "SELECT COALESCE(sum((desired_state->>'count')::integer),0) "
                "FROM digital_asset.hosting_resources "
                "WHERE resource_kind='accelerator' AND status='ready' "
                "AND desired_state->>'kind'=:kind"
            ),
            {"kind": kind},
        ).scalar_one()
    )
    if pool is not None and allocated + count > int(pool["allocatable_units"]):
        pool = None
    if pool is None:
        error = {
            "reason": "accelerator_capacity_unavailable",
            "stage": "provider_capacity",
            "requested": requested,
            "retryable": True,
        }
        return "blocked", {"allocated": False, "requested": requested}, error
    return (
        "succeeded",
        {
            "allocated": True,
            "requested": requested,
            "pool_key": pool["pool_key"],
            "provider_key": pool["provider_key"],
        },
        None,
    )


def _host_agent_request(
    settings: Settings,
    payload: dict[str, object],
) -> dict[str, object]:
    token = settings.shield_agent_token.get_secret_value()
    if not token:
        return {
            "ok": False,
            "status": "blocked",
            "error": "hosting_host_agent_not_configured",
        }
    request = {
        **payload,
        "token": token,
        "request_id": str(uuid4()),
    }
    raw = (_canonical(request) + "\n").encode()
    response = bytearray()
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(settings.shield_agent_timeout_seconds)
            client.connect(str(settings.shield_agent_socket))
            client.sendall(raw)
            while len(response) <= settings.shield_agent_max_response_bytes:
                chunk = client.recv(65_536)
                if not chunk:
                    break
                response.extend(chunk)
                if b"\n" in chunk:
                    break
    except (OSError, TimeoutError) as exc:
        return {
            "ok": False,
            "status": "blocked",
            "error": f"hosting_host_agent_unavailable:{type(exc).__name__}",
        }
    try:
        result = json.loads(bytes(response).split(b"\n", 1)[0])
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "ok": False,
            "status": "failed",
            "error": "hosting_host_agent_invalid_response",
        }
    return result if isinstance(result, dict) else {"ok": False, "error": "invalid_response"}


def _apply_domain(
    credential: WorkspaceCredential,
    spec: dict[str, object],
    settings: Settings,
) -> tuple[str, dict[str, object], dict[str, object] | None]:
    with system_session() as session:
        tenant_slug = session.execute(
            text("SELECT slug FROM iam.tenants WHERE id=:id"),
            {"id": credential.tenant_id},
        ).scalar_one()
    with tenant_session(credential.tenant_id) as session:
        workspace_key = session.execute(
            text("SELECT workspace_key FROM digital_asset.workspaces WHERE id=:id"),
            {"id": credential.workspace_id},
        ).scalar_one()
    result = _host_agent_request(
        settings,
        {
            "operation": "hosting_domain_apply",
            "hostname": str(spec["hostname"]),
            "tenant_slug": str(tenant_slug),
            "workspace_key": str(workspace_key),
        },
    )
    observed = dict(result.get("result") or {}) if isinstance(result.get("result"), dict) else {}
    observed.update(
        {
            "hostname": str(spec["hostname"]),
            "dns_verified": bool(result.get("ok")),
            "tls": observed.get("tls") or "pending",
        }
    )
    if result.get("ok"):
        return "succeeded", observed, None
    error = {
        "reason": str(result.get("error") or "domain_tls_blocked"),
        "stage": "dns_tls_provider",
        "retryable": True,
        "provider_result": _json_safe(result),
    }
    return "blocked", observed, error


def apply_fabric_resource(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings,
    *,
    idempotency_key: str | None = None,
) -> dict[str, object]:
    """Apply one desired hosting resource with exact, durable evidence."""

    kind = str(payload.get("kind") or "").strip().lower()
    supplied = payload.get("spec")
    if not isinstance(supplied, dict):
        raise HTTPException(status_code=422, detail="spec must be an object")
    spec = dict(supplied)
    resource_key = str(payload.get("resource_key") or spec.get("name") or kind).strip()
    execute = payload.get("execute") is not False
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace(session, credential)
        database_policy = workspace_database_policy(workspace.get("config"))
        allow_database_url = str(database_policy["mode"]) == "workspace_managed"
        driver = _driver(session, kind)
        credential.require(str(driver["required_scope"]))
        if kind == "secret":
            public, _value = _validate_secret(
                spec,
                allow_database_url=allow_database_url,
            )
            desired = public
            resource_key = str(public["name"])
        elif kind == "environment":
            desired = _validate_environment(spec)
        elif kind == "scaling":
            desired = _validate_scaling(spec)
        elif kind == "container":
            desired = _validate_container(spec, compose=False)
        elif kind == "compose":
            desired = _validate_container(spec, compose=True)
        elif kind == "domain":
            hostname = str(spec.get("hostname") or "").strip().lower().rstrip(".")
            if not HOSTNAME_RE.fullmatch(hostname):
                raise HTTPException(status_code=422, detail="Invalid custom hostname")
            platform_hostname = str(urlsplit(settings.public_origin).hostname or "").lower()
            if platform_hostname and (
                hostname == platform_hostname or hostname.endswith(f".{platform_hostname}")
            ):
                raise HTTPException(
                    status_code=422,
                    detail={
                        "reason": "platform_hostname_is_reserved",
                        "hostname": hostname,
                    },
                )
            desired = {
                "hostname": hostname,
                "redirect_https": spec.get("redirect_https") is not False,
            }
            resource_key = hostname
        elif kind == "database_migration":
            normalized_sql = str(spec.get("sql") or "").strip()
            desired = {
                "version": str(spec.get("version") or "")[:120],
                "checksum": hashlib.sha256(normalized_sql.encode()).hexdigest(),
            }
            resource_key = str(desired["version"] or resource_key)
        elif kind == "repository":
            desired = {key: value for key, value in spec.items() if key != "credential_value"}
            desired["auto_sync"] = spec.get("auto_sync") is True
            desired["sync_interval_seconds"] = max(
                60, min(int(spec.get("sync_interval_seconds") or 300), 86_400)
            )
        elif kind == "backup":
            desired = {
                key: value
                for key, value in spec.items()
                if key not in {"credential", "credential_value"}
            }
            desired["mode"] = str(spec.get("mode") or "logical").lower()
            desired["destination"] = str(spec.get("destination") or "local").lower()
            resource_key = str(spec.get("backup_id") or spec.get("label") or "database")
        elif kind == "accelerator":
            desired = {
                "kind": str(spec.get("kind") or "gpu"),
                "count": max(1, int(spec.get("count") or 1)),
                "memory_mb": int(spec.get("memory_mb") or 0) or None,
                "required": spec.get("required") is not False,
            }
        else:
            desired = spec
        if kind == "domain" and execute:
            _claim_domain(session, credential, str(desired["hostname"]))
        resource = _upsert_resource(
            session, credential, driver, resource_key=resource_key, desired=desired
        )
        request = {"kind": kind, "resource_key": resource_key, "spec": desired, "execute": execute}
        action, replay = _begin_action(
            session,
            credential,
            resource,
            action_type=f"{kind}.apply",
            request=request,
            idempotency_key=idempotency_key,
        )
        if replay:
            replay_status = (
                "ready"
                if action["status"] == "succeeded"
                else "blocked"
                if action["status"] == "blocked"
                else "failed"
                if action["status"] in {"failed", "cancelled"}
                else "planned"
            )
            resource = dict(
                session.execute(
                    text(
                        "UPDATE digital_asset.hosting_resources SET status=:status,"
                        "observed_state=CAST(:observed AS jsonb),"
                        "last_error=CAST(:error AS jsonb) WHERE id=:id RETURNING *"
                    ),
                    {
                        "id": resource["id"],
                        "status": replay_status,
                        "observed": _canonical(action.get("result") or {}),
                        "error": (_canonical(action.get("error")) if action.get("error") else None),
                    },
                )
                .mappings()
                .one()
            )
            return {
                "ok": action["status"] == "succeeded",
                "idempotent_replay": True,
                "resource": _json_safe(resource),
                "action": _json_safe(action),
            }
        if not execute:
            observed = {
                "planned": True,
                "driver": driver["driver_key"],
                "execution_mode": driver["execution_mode"],
            }
            resource_row, action_row = _finish(
                session, credential, resource, action, status="succeeded", observed=observed
            )
            return {
                "ok": True,
                "preview": True,
                "resource": _json_safe(resource_row),
                "action": _json_safe(action_row),
            }
        try:
            if kind == "secret":
                observed = _apply_secret(
                    session,
                    credential,
                    resource,
                    spec,
                    settings,
                    allow_database_url=allow_database_url,
                )
                status, error = "succeeded", None
            elif kind == "database_migration":
                observed = _apply_migration(session, credential, spec, settings)
                status, error = "succeeded", None
            elif kind == "backup":
                status, observed, error = _apply_backup(session, credential, spec, settings)
            elif kind == "repository":
                observed = _apply_repository(session, credential, spec, settings)
                status, error = "succeeded", None
            elif kind == "accelerator":
                status, observed, error = _accelerator_observation(session, spec)
            elif kind == "domain":
                status, observed, error = _apply_domain(credential, desired, settings)
            else:
                status, error = "succeeded", None
                observed = {
                    "configured": True,
                    "driver": driver["driver_key"],
                    "applies_on_next_deployment": kind
                    in {"environment", "scaling", "container", "compose"},
                }
        except HTTPException as exc:
            detail = exc.detail
            reason = (
                str(detail.get("reason") or "provider_operation_rejected")
                if isinstance(detail, dict)
                else "provider_operation_rejected"
            )
            status = "blocked" if exc.status_code in {409, 423, 429, 503} else "failed"
            observed = {"configured": False, "http_status": exc.status_code}
            error = {
                "reason": reason,
                "stage": str(driver["execution_mode"]),
                "detail": _json_safe(detail),
                "http_status": exc.status_code,
                "retryable": exc.status_code in {409, 423, 429, 503},
            }
        except Exception as exc:
            status = "failed"
            observed = {"configured": False}
            error = {
                "reason": type(exc).__name__,
                "stage": str(driver["execution_mode"]),
                "message": str(exc)[:1200],
                "retryable": True,
            }
        resource_row, action_row = _finish(
            session, credential, resource, action, status=status, observed=observed, error=error
        )
    return {
        "ok": status == "succeeded",
        "resource": _json_safe(resource_row),
        "action": _json_safe(action_row),
        "diagnosis": error,
        "workflow_prescribed": False,
    }


def observe_fabric(credential: WorkspaceCredential) -> dict[str, object]:
    credential.require("infra:read")
    with tenant_session(credential.tenant_id) as session:
        _workspace(session, credential)
        resources = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT id,resource_kind,resource_key,driver_key,desired_state,"
                    "observed_state,status,last_error,revision,created_at,updated_at "
                    "FROM digital_asset.hosting_resources WHERE workspace_id=:workspace_id "
                    "ORDER BY resource_kind,resource_key"
                ),
                {"workspace_id": credential.workspace_id},
            ).mappings()
        ]
        actions = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT id,legacy_id,resource_id,action_type,status,result,error,created_at,"
                    "started_at,completed_at FROM digital_asset.hosting_actions "
                    "WHERE workspace_id=:workspace_id ORDER BY created_at DESC LIMIT 100"
                ),
                {"workspace_id": credential.workspace_id},
            ).mappings()
        ]
        secrets = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT name,version,active,created_at,revoked_at FROM "
                    "digital_asset.hosting_secret_versions WHERE workspace_id=:workspace_id "
                    "ORDER BY name,version DESC"
                ),
                {"workspace_id": credential.workspace_id},
            ).mappings()
        ]
        backups = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT id,label,backup_kind,sha256,size_bytes,status,recovery_point,"
                    "retention_until,metadata,created_at,completed_at "
                    "FROM digital_asset.database_backups "
                    "WHERE workspace_id=:workspace_id ORDER BY created_at DESC"
                ),
                {"workspace_id": credential.workspace_id},
            ).mappings()
        ]
    return {
        "ok": True,
        "workspace_id": str(credential.workspace_id),
        "resources": resources,
        "actions": actions,
        "secrets": secrets,
        "backups": backups,
        "secret_plaintext_exposed": False,
    }


def set_workspace_database_policy(
    credential: WorkspaceCredential,
    payload: dict[str, object],
) -> dict[str, object]:
    """Choose who owns the workspace database lifecycle without deleting data."""

    credential.require("database:admin")
    mode = str(payload.get("mode") or "").strip().lower()
    allowed = {"platform_managed", "external", "workspace_managed", "none"}
    if mode not in allowed:
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_database_policy", "allowed_modes": sorted(allowed)},
        )
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace(session, credential)
        binding = (
            session.execute(
                text(
                    """
                    SELECT id,provider_key,status,logical_name
                    FROM digital_asset.database_bindings
                    WHERE workspace_id=:workspace_id AND is_default
                    ORDER BY created_at LIMIT 1
                    """
                ),
                {"workspace_id": credential.workspace_id},
            )
            .mappings()
            .one_or_none()
        )
        provider = str(binding.get("provider_key") or "") if binding is not None else ""
        if mode == "platform_managed" and provider not in {
            hosted_database.HDD_DATABASE_PROVIDER_KEY,
        }:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "managed_postgresql_binding_required",
                    "next_action": "provision_or_select_managed_database",
                },
            )
        if mode == "external" and provider != hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "external_database_binding_required",
                    "next_action": "register_external_database_binding",
                },
            )
        config = dict(workspace.get("config") or {})
        before = workspace_database_policy(config)
        config["database_policy"] = {
            "mode": mode,
            "selected_by_credential_id": str(credential.credential_id),
            "selected_at": datetime.now(UTC).isoformat(),
        }
        session.execute(
            text(
                """
                UPDATE digital_asset.workspaces
                SET config=CAST(:config AS jsonb),revision=revision+1,updated_at=now()
                WHERE id=:workspace_id
                """
            ),
            {
                "workspace_id": credential.workspace_id,
                "config": _canonical(config),
            },
        )
        after = workspace_database_policy(config)
        release_gate = observe_database_release_gate(session, credential.workspace_id)
    return {
        "ok": True,
        "workspace_id": str(credential.workspace_id),
        "before": before,
        "policy": after,
        "release_gate": _json_safe(release_gate),
        "existing_database_binding_retained": binding is not None,
        "database_credentials_exposed": False,
        "workspace_boundary": {
            "source_read_only": True,
            "runtime_and_data_writable": True,
            "host_and_other_workspaces_visible": False,
            "compose_services_and_named_volumes_allowed": True,
        },
    }


def workspace_database_control(
    credential: WorkspaceCredential,
    settings: Settings,
    *,
    reconcile: bool = False,
) -> dict[str, object]:
    """Expose the complete, auditable database control surface to workspace keys."""

    credential.require("database:admin" if reconcile else "infra:read")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace(session, credential)
        database_policy = workspace_database_policy(workspace.get("config"))
        binding_row = (
            session.execute(
                text(
                    """
                    SELECT b.*,c.secret_ciphertext,c.credential_kind
                    FROM digital_asset.database_bindings AS b
                    LEFT JOIN digital_asset.database_credentials AS c
                      ON c.database_binding_id=b.id
                    WHERE b.workspace_id=:workspace_id
                    ORDER BY b.is_default DESC,b.created_at
                    LIMIT 1
                    """
                ),
                {"workspace_id": credential.workspace_id},
            )
            .mappings()
            .one_or_none()
        )
        if binding_row is None:
            raise HTTPException(status_code=404, detail="Workspace database not found")
        binding = dict(binding_row)
        capability_evidence: dict[str, object] | None = None
        if reconcile:
            if str(binding.get("status") or "") != "ready":
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "database_binding_not_ready",
                        "database_binding_id": str(binding["id"]),
                        "status": binding.get("status"),
                    },
                )
            try:
                capability_evidence = hosted_database.reconcile_capabilities(
                    session,
                    binding,
                    settings=settings,
                )
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=503,
                    detail={
                        "reason": "database_capability_reconciliation_failed",
                        "message": str(exc),
                        "retryable": True,
                    },
                ) from exc

        health: dict[str, object]
        if str(binding.get("status") or "") == "ready":
            try:
                health = hosted_database.binding_health(
                    session,
                    binding,
                    settings=settings,
                )
            except hosted_database.HostedDatabaseUnavailable as exc:
                health = {
                    "reachable": False,
                    "reason": "database_unavailable",
                    "message": str(exc),
                    "retryable": True,
                    "credentials_exposed": False,
                }
        else:
            health = {
                "reachable": False,
                "reason": "database_binding_not_ready",
                "binding_status": binding.get("status"),
                "retryable": True,
                "credentials_exposed": False,
            }

        current = dict(
            session.execute(
                text(
                    """
                    SELECT id,logical_name,provider_key,status,ownership_mode,
                           database_ref,role_ref,runtime_role_ref,backup_role_ref,
                           capabilities,config,actual_size_bytes,size_measured_at,
                           created_at,updated_at
                    FROM digital_asset.database_bindings
                    WHERE id=:binding_id
                    """
                ),
                {"binding_id": binding["id"]},
            )
            .mappings()
            .one()
        )
        migration_history = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT id,version,checksum,statement_count,status,error,applied_at
                    FROM digital_asset.database_migration_history
                    WHERE workspace_id=:workspace_id
                      AND database_binding_id=:binding_id
                    ORDER BY applied_at,version
                    """
                ),
                {
                    "workspace_id": credential.workspace_id,
                    "binding_id": binding["id"],
                },
            ).mappings()
        ]
        release_gate = observe_database_release_gate(session, credential.workspace_id)

    scopes = set(credential.scopes)
    return {
        "ok": bool(health.get("reachable")),
        "workspace_id": str(credential.workspace_id),
        "key_kind": credential.key_kind,
        "database_policy": database_policy,
        "reconcile_performed": reconcile,
        "database": _json_safe(current),
        "health": _json_safe(health),
        "capability_evidence": _json_safe(capability_evidence),
        "release_gate": _json_safe(release_gate),
        "migration_history": migration_history,
        "authorized_operations": {
            "observe": "infra:read" in scopes,
            "reconcile_capabilities": "database:admin" in scopes,
            "create_or_restore_backup": "backup:write" in scopes,
            "apply_migration": "database:admin" in scopes,
            "deploy_or_activate": "deploy:write" in scopes,
        },
        "control_surface": {
            "reconcile": "POST /api/workspaces/v1/database/reconcile",
            "backup_or_restore": "POST /api/workspaces/v1/fabric/resources kind=backup",
            "migration": (
                "POST /api/workspaces/v1/fabric/resources kind=database_migration"
            ),
            "deployment": "POST /api/workspaces/v1/deployments",
            "release_observation": "GET /api/workspaces/v1/database/control",
        },
        "credentials_exposed": False,
    }


def observe_action(credential: WorkspaceCredential, action_id: UUID) -> dict[str, object]:
    credential.require("infra:read")
    with tenant_session(credential.tenant_id) as session:
        action = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.hosting_actions "
                    "WHERE id=:id AND workspace_id=:workspace_id"
                ),
                {"id": action_id, "workspace_id": credential.workspace_id},
            )
            .mappings()
            .one_or_none()
        )
        if action is None:
            raise HTTPException(status_code=404, detail="Hosting action not found")
        events = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT sequence,event_type,payload,created_at FROM "
                    "digital_asset.hosting_action_events WHERE action_id=:id ORDER BY sequence"
                ),
                {"id": action_id},
            ).mappings()
        ]
    return {"ok": True, "action": _json_safe(dict(action)), "events": events}


def reconcile_repository_resources(settings: Settings, *, limit: int = 4) -> int:
    """Refresh due Git resources from the trusted Runtime Controller.

    The repository URL and schedule are desired state.  Credentials remain in
    the encrypted workspace secret store and the resulting immutable source
    version is registered through the same workspace boundary as a Key upload.
    One failed repository is persisted as an action failure and does not stop
    other tenants from being reconciled.
    """

    with system_session() as system:
        tenant_ids = [
            UUID(str(value))
            for value in system.execute(text("SELECT id FROM iam.tenants ORDER BY id")).scalars()
        ]
    reconciled = 0
    for tenant_id in tenant_ids:
        if reconciled >= max(1, limit):
            break
        with tenant_session(tenant_id) as session:
            rows = [
                dict(row)
                for row in session.execute(
                    text(
                        "SELECT * FROM digital_asset.hosting_resources "
                        "WHERE resource_kind='repository' "
                        "AND COALESCE((desired_state->>'auto_sync')::boolean,false) "
                        "ORDER BY updated_at LIMIT :limit"
                    ),
                    {"limit": max(1, limit - reconciled)},
                ).mappings()
            ]
            for resource in rows:
                desired = (
                    dict(resource["desired_state"])
                    if isinstance(resource.get("desired_state"), dict)
                    else {}
                )
                observed = (
                    dict(resource["observed_state"])
                    if isinstance(resource.get("observed_state"), dict)
                    else {}
                )
                interval = max(60, min(int(desired.get("sync_interval_seconds") or 300), 86_400))
                try:
                    synced_at = datetime.fromisoformat(str(observed.get("synced_at") or ""))
                    if synced_at.tzinfo is None:
                        synced_at = synced_at.replace(tzinfo=UTC)
                except ValueError:
                    synced_at = datetime.fromtimestamp(0, tz=UTC)
                if datetime.now(UTC) - synced_at < timedelta(seconds=interval):
                    continue
                credential = WorkspaceCredential(
                    tenant_id=tenant_id,
                    workspace_id=UUID(str(resource["workspace_id"])),
                    credential_id=UUID(str(resource["created_by_credential_id"])),
                    scopes=frozenset(WORKSPACE_ALL_SCOPES),
                    label="Hosting repository reconciler",
                    key_kind="internal_reconciler",
                    parent_credential_id=None,
                )
                action, _replay = _begin_action(
                    session,
                    credential,
                    resource,
                    action_type="repository.auto_sync",
                    request={"kind": "repository", "spec": desired, "automatic": True},
                    idempotency_key=None,
                )
                try:
                    result = _apply_repository(session, credential, desired, settings)
                    result.update({"automatic": True, "sync_interval_seconds": interval})
                    _finish(
                        session,
                        credential,
                        resource,
                        action,
                        status="succeeded",
                        observed=result,
                    )
                except Exception as exc:
                    error = {
                        "reason": type(exc).__name__,
                        "stage": "repository_auto_sync",
                        "message": str(getattr(exc, "detail", exc))[:1200],
                        "retryable": True,
                    }
                    _finish(
                        session,
                        credential,
                        resource,
                        action,
                        status="blocked",
                        observed={
                            **observed,
                            "automatic": True,
                            "last_attempt_at": datetime.now(UTC).isoformat(),
                        },
                        error=error,
                    )
                reconciled += 1
                if reconciled >= max(1, limit):
                    break
    return reconciled


def runtime_environment(
    session: object,
    workspace_id: UUID,
    component: str,
    settings: Settings,
) -> tuple[dict[str, str], dict[str, object]]:
    """Resolve non-secret variables and decrypt active secrets for one launch."""

    resources = [
        dict(row)
        for row in session.execute(
            text(
                "SELECT resource_kind,desired_state FROM digital_asset.hosting_resources "
                "WHERE workspace_id=:workspace_id AND status='ready' "
                "AND resource_kind IN ('environment','scaling','accelerator')"
            ),
            {"workspace_id": workspace_id},
        ).mappings()
    ]
    environment: dict[str, str] = {}
    policy: dict[str, object] = {"replicas": 1, "accelerator": None}
    for resource in resources:
        desired = (
            resource.get("desired_state") if isinstance(resource.get("desired_state"), dict) else {}
        )
        target = str(desired.get("component") or "*")
        if target not in {"*", component}:
            continue
        if resource["resource_kind"] == "environment":
            environment.update(
                {str(k): str(v) for k, v in dict(desired.get("variables") or {}).items()}
            )
        elif resource["resource_kind"] == "scaling":
            policy["replicas"] = max(1, min(int(desired.get("min_replicas") or 1), MAX_REPLICAS))
            policy["scaling"] = desired
        elif resource["resource_kind"] == "accelerator":
            policy["accelerator"] = desired
    secrets = session.execute(
        text(
            """
            SELECT s.name,s.ciphertext,r.desired_state
            FROM digital_asset.hosting_secret_versions AS s
            JOIN digital_asset.hosting_resources AS r ON r.id=s.resource_id
            WHERE s.workspace_id=:workspace_id AND s.active AND s.revoked_at IS NULL
              AND r.status='ready'
            """
        ),
        {"workspace_id": workspace_id},
    ).mappings()
    for row in secrets:
        desired = row["desired_state"] if isinstance(row["desired_state"], dict) else {}
        target = str(desired.get("component") or "*")
        if target in {"*", component}:
            environment[str(row["name"])] = _decrypt(str(row["ciphertext"]), settings)
    return environment, policy
