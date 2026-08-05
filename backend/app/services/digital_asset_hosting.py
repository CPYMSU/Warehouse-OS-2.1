"""Digital asset custody and full-stack workspace services.

The module is the stable control-plane boundary.  Runtime, database and object
storage providers are represented by bindings, so callers never choose a DSN,
host path or internal port.  The first database provider is a real
PostgreSQL/RLS JSON data plane exposed through the workspace Data API.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

import jwt
import psycopg
from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import system_session, tenant_session
from app.services import hosted_database
from app.services.object_storage import (
    HDD_PROVIDER_KEY,
    LEGACY_PROVIDER_KEY,
    LOCAL_PROVIDER_KEYS,
    SSD_PROVIDER_KEY,
    object_store_for_provider,
)
from app.services.workspace_usage import measure_workspace_runtime_storage

if TYPE_CHECKING:
    from app.api.deps import ActorContext


ASSET_KINDS = frozenset(
    {"data", "process", "knowledge", "software", "model", "agent", "project", "other"}
)
ASSET_STATUSES = frozenset({"draft", "registered", "custodied", "active", "listed", "archived"})
ASSET_LIFECYCLE_STAGES = frozenset(
    {
        "discover",
        "standardize",
        "custody",
        "provisioned",
        "deployed",
        "valuation",
        "listing",
        "trading",
        "retired",
    }
)
RISK_LEVELS = frozenset({"low", "medium", "high", "critical"})
SERVICE_PLANS = frozenset({"custody", "hosted", "managed", "dedicated"})
RUNTIME_TYPES = frozenset({"static", "web", "api", "worker", "agent", "container", "compose"})
COMPONENT_KINDS = frozenset({"frontend", "backend", "worker", "agent"})
ARTIFACT_KINDS = frozenset(
    {
        "package",
        "source",
        "frontend",
        "backend",
        "dataset",
        "model",
        "agent",
        "document",
        "other",
    }
)
WORKSPACE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,62}$")
COLLECTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,119}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
WORKSPACE_ALL_SCOPES = (
    "workspace:read",
    "data:read",
    "data:write",
    "deploy:read",
    "deploy:write",
    "logs:read",
    "infra:read",
    "infra:write",
    "domain:write",
    "secrets:write",
    "database:admin",
    "repository:write",
    "backup:write",
    "accelerator:use",
)
WORKSPACE_SCOPES = frozenset(WORKSPACE_ALL_SCOPES)
DEFAULT_DELEGATED_SCOPES = ("workspace:read", "data:read")
WORKSPACE_QUOTA_STEP_BYTES = 512 * 1024 * 1024
WORKSPACE_QUOTA_STEP_MB = 512
HDD_POOL_KEY = "hosted-hdd-01"
SSD_POOL_KEY = "core-ssd-01"
HDD_DATABASE_POOL_KEY = hosted_database.HDD_DATABASE_POOL_KEY
STORAGE_ROLES = frozenset({"code", "data"})
CODE_STORAGE_MEDIA = frozenset({"hdd", "ssd"})
CODE_ARTIFACT_KINDS = frozenset({"package", "source", "frontend", "backend", "agent"})


@dataclass(frozen=True)
class WorkspaceCredential:
    tenant_id: UUID
    workspace_id: UUID
    credential_id: UUID
    scopes: frozenset[str]
    label: str
    key_kind: str
    parent_credential_id: UUID | None

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Workspace key is missing scope: {scope}",
            )


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, datetime)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    return value


def _require_read(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.read",
        "assets.manage",
        "asset_mgmt.read",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _require_manage(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.manage",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _audit(
    session: Session,
    actor: ActorContext | None,
    event_type: str,
    payload: dict[str, object],
    *,
    tenant_id: UUID | None = None,
) -> None:
    effective_tenant_id = actor.tenant_id if actor is not None else tenant_id
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
            """
        ),
        {
            "tenant_id": effective_tenant_id,
            "actor_user_id": actor.user_id if actor is not None else None,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _normalise_tags(value: object) -> list[str]:
    if isinstance(value, str):
        candidates = value.split(",")
    elif isinstance(value, list):
        candidates = value
    else:
        return []
    return list(
        dict.fromkeys(str(candidate).strip() for candidate in candidates if str(candidate).strip())
    )[:40]


def _code_storage_choice(payload: dict[str, object]) -> str:
    """Default core code to HDD; SSD is accepted only as explicit intent."""

    supplied = payload.get("code_storage", payload.get("core_storage"))
    choice = str(supplied or "hdd").strip().lower()
    if choice not in CODE_STORAGE_MEDIA:
        raise HTTPException(status_code=422, detail="code_storage must be hdd or ssd")
    requested_data = str(payload.get("data_storage") or "hdd").strip().lower()
    if requested_data != "hdd":
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "hosted_data_requires_hdd",
                "accepted_data_storage": "hdd",
                "message": "Hosted data, attachments and persistent files must use HDD",
            },
        )
    return choice


def _storage_binding_rows(session: Session, workspace_id: object) -> list[dict[str, object]]:
    return [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT id, workspace_id, binding_role, pool_key, provider_key,
                       storage_class, status, config, created_at, updated_at
                FROM digital_asset.storage_bindings
                WHERE workspace_id = :workspace_id
                ORDER BY binding_role
                """
            ),
            {"workspace_id": workspace_id},
        )
        .mappings()
        .all()
    ]


def _storage_profile(bindings: list[dict[str, object]]) -> dict[str, object]:
    roles: dict[str, object] = {}
    for row in bindings:
        role = str(row.get("binding_role") or "")
        if role not in STORAGE_ROLES:
            continue
        config = row.get("config") if isinstance(row.get("config"), dict) else {}
        roles[role] = _json_safe(
            {
                "role": role,
                "medium": config.get("medium")
                or ("ssd" if row.get("provider_key") == SSD_PROVIDER_KEY else "hdd"),
                "pool_key": row.get("pool_key"),
                "provider_key": row.get("provider_key"),
                "storage_class": row.get("storage_class"),
                "status": row.get("status"),
                "selection": config.get("selection"),
                "write_probe": config.get("write_probe"),
                "write_probe_at": config.get("write_probe_at"),
                "write_probe_latency_ms": config.get("write_probe_latency_ms"),
            }
        )
    return {
        "code": roles.get("code")
        or {
            "role": "code",
            "medium": "hdd",
            "pool_key": HDD_POOL_KEY,
            "provider_key": HDD_PROVIDER_KEY,
            "storage_class": "standard",
            "status": "unbound",
            "selection": "missing_binding",
        },
        "data": roles.get("data")
        or {
            "role": "data",
            "medium": "hdd",
            "pool_key": HDD_POOL_KEY,
            "provider_key": HDD_PROVIDER_KEY,
            "storage_class": "standard",
            "status": "unbound",
            "selection": "missing_binding",
        },
        "data_storage_enforced": "hdd",
        "quota_is_logical": True,
        "quota_step_bytes": WORKSPACE_QUOTA_STEP_BYTES,
    }


def _workspace_billable_usage(
    session: Session,
    *,
    tenant_id: object,
    workspace_id: object,
    asset_id: object,
    persist: bool = True,
    refresh_infrastructure: bool = False,
) -> dict[str, object]:
    """Measure one aggregate quota across both media and the hosted database."""

    artifacts = (
        session.execute(
            text(
                """
            SELECT
              COALESCE(SUM(size_bytes) FILTER (WHERE storage_role = 'code'), 0)::bigint
                AS code_bytes,
              COALESCE(SUM(size_bytes) FILTER (WHERE storage_role = 'data'), 0)::bigint
                AS data_object_bytes
            FROM digital_asset.artifacts
            WHERE asset_id = :asset_id
              AND state IN ('pending','stored','verified','quarantined','released')
            """
            ),
            {"asset_id": asset_id},
        )
        .mappings()
        .one()
    )
    database_status = "cached"
    if refresh_infrastructure:
        database_measurements = []
        bindings = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.database_bindings
                    WHERE workspace_id=:workspace_id AND status='ready'
                    ORDER BY is_default DESC,created_at
                    """
                ),
                {"workspace_id": workspace_id},
            )
            .mappings()
            .all()
        ]
        for binding in bindings:
            try:
                database_measurements.append(
                    hosted_database.measure_database_size(session, binding)
                )
            except hosted_database.HostedDatabaseUnavailable:
                database_measurements.append(
                    {
                        "database_bytes": max(
                            0, int(binding.get("actual_size_bytes") or 0)
                        ),
                        "measurement_status": "cached_after_error",
                    }
                )
        database_bytes = sum(
            int(measurement["database_bytes"])
            for measurement in database_measurements
        )
        database_status = (
            "complete"
            if all(
                measurement.get("measurement_status")
                in {"complete", "provider_reported"}
                for measurement in database_measurements
            )
            else "partial"
        )
    else:
        database_bytes = int(
            session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(actual_size_bytes), 0)::bigint
                    FROM digital_asset.database_bindings
                    WHERE workspace_id = :workspace_id AND status = 'ready'
                    """
                ),
                {"workspace_id": workspace_id},
            ).scalar_one()
        )
    persisted_runtime = (
        session.execute(
            text(
                """
                SELECT COALESCE(runtime_bytes,0)::bigint AS runtime_bytes,
                       COALESCE(data_volume_bytes,0)::bigint AS data_volume_bytes
                FROM digital_asset.workspace_usage
                WHERE workspace_id=:workspace_id
                """
            ),
            {"workspace_id": workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    runtime_measurement: dict[str, object] = {
        "runtime_release_bytes": int(
            persisted_runtime["runtime_bytes"] if persisted_runtime else 0
        ),
        "data_volume_bytes": int(
            persisted_runtime["data_volume_bytes"] if persisted_runtime else 0
        ),
        "measurement_status": "cached",
        "measured_at": datetime.now(UTC),
    }
    if refresh_infrastructure:
        runtime_measurement = measure_workspace_runtime_storage(
            get_settings(),
            tenant_id=tenant_id,
            workspace_id=workspace_id,
        )
    usage = {
        "code_bytes": int(artifacts["code_bytes"]),
        "data_object_bytes": int(artifacts["data_object_bytes"]),
        "database_bytes": database_bytes,
        "runtime_bytes": int(runtime_measurement["runtime_release_bytes"]),
        "data_volume_bytes": int(runtime_measurement["data_volume_bytes"]),
    }
    usage["total_bytes"] = sum(int(value) for value in usage.values())
    usage["measured_at"] = runtime_measurement["measured_at"]
    usage["measurement_status"] = (
        "complete"
        if runtime_measurement["measurement_status"] == "complete"
        and database_status in {"complete", "cached"}
        else "partial"
    )
    usage["database_measurement_status"] = database_status
    usage["runtime_scan_error_count"] = int(
        runtime_measurement.get("scan_error_count") or 0
    )
    if persist:
        session.execute(
            text(
                """
                INSERT INTO digital_asset.workspace_usage(
                  tenant_id, workspace_id, code_bytes, data_object_bytes,
                  database_bytes, runtime_bytes, data_volume_bytes, measured_at
                ) VALUES (
                  :tenant_id, :workspace_id, :code_bytes, :data_object_bytes,
                  :database_bytes, :runtime_bytes, :data_volume_bytes, :measured_at
                )
                ON CONFLICT (tenant_id, workspace_id) DO UPDATE SET
                  code_bytes = EXCLUDED.code_bytes,
                  data_object_bytes = EXCLUDED.data_object_bytes,
                  database_bytes = EXCLUDED.database_bytes,
                  runtime_bytes = EXCLUDED.runtime_bytes,
                  data_volume_bytes = EXCLUDED.data_volume_bytes,
                  measured_at = EXCLUDED.measured_at,
                  revision = digital_asset.workspace_usage.revision + 1
                """
            ),
            {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "code_bytes": usage["code_bytes"],
                "data_object_bytes": usage["data_object_bytes"],
                "database_bytes": usage["database_bytes"],
                "runtime_bytes": usage["runtime_bytes"],
                "data_volume_bytes": usage["data_volume_bytes"],
                "measured_at": usage["measured_at"],
            },
        )
    return usage


def storage_pool_overview(
    actor: ActorContext, *, enforce_permission: bool = True
) -> dict[str, object]:
    """Expose capacity/health facts without leaking server filesystem paths."""

    if enforce_permission:
        _require_read(actor)
    settings = get_settings()
    with system_session() as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT pool_key, provider_key, label, storage_class, medium,
                       purpose, root_setting, status, enabled, policy, updated_at
                FROM platform.storage_pools
                ORDER BY storage_class, pool_key
                """
                )
            )
            .mappings()
            .all()
        )
    pools: list[dict[str, object]] = []
    database_health: dict[str, object] | None = None
    for raw in rows:
        row = dict(raw)
        policy = row.get("policy") if isinstance(row.get("policy"), dict) else {}
        root = getattr(settings, str(row["root_setting"]))
        observed_status = str(row["status"])
        capacity: dict[str, object] = {"observed": False}
        try:
            usage = shutil.disk_usage(root)
            used_percent = round((usage.used / usage.total) * 100, 2) if usage.total else 0.0
            capacity = {
                "observed": True,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "used_percent": used_percent,
            }
        except OSError:
            used_percent = 100.0
            observed_status = "unavailable"
        service_health = None
        if row["purpose"] == "hosted_database":
            if database_health is None:
                database_health = hosted_database.health(settings)
            service_health = database_health
            if not bool(database_health.get("reachable")):
                observed_status = "unavailable"
        elif str(row["provider_key"]) in LOCAL_PROVIDER_KEYS:
            try:
                service_health = object_store_for_provider(
                    settings, str(row["provider_key"])
                ).probe_writable()
            except (OSError, RuntimeError) as exc:
                observed_status = "unavailable"
                service_health = {
                    "writable": False,
                    "probe": "create_write_fsync_read_delete",
                    "error": exc.__class__.__name__,
                }
        stop_percent = float(policy.get("stop_expansion_percent") or 90)
        pools.append(
            _json_safe(
                {
                    "pool_key": row["pool_key"],
                    "provider_key": row["provider_key"],
                    "label": row["label"],
                    "storage_class": row["storage_class"],
                    "medium": row["medium"],
                    "purpose": row["purpose"],
                    "status": observed_status,
                    "enabled": bool(row["enabled"]),
                    "policy": policy,
                    "capacity": capacity,
                    "service_health": service_health,
                    "expansion_allowed": bool(row["enabled"])
                    and observed_status == "ready"
                    and used_percent < stop_percent,
                    "updated_at": row["updated_at"],
                }
            )
        )
    return {
        "ok": True,
        "source": "platform_storage_pools",
        "default_code_storage": "hdd",
        "ssd_requires_explicit_intent": True,
        "data_storage_enforced": "hdd",
        "quota_is_logical": True,
        "quota_step_bytes": WORKSPACE_QUOTA_STEP_BYTES,
        "pools": pools,
    }


def artifact_upload_target(
    actor: ActorContext, asset_ref: object, artifact_kind: str
) -> dict[str, object]:
    """Resolve an upload through the workspace binding and logical quota."""

    _require_manage(actor)
    normalized_kind = "document" if artifact_kind == "doc" else artifact_kind
    if normalized_kind not in ARTIFACT_KINDS:
        raise HTTPException(status_code=422, detail="Invalid artifact_kind")
    role = "code" if normalized_kind in CODE_ARTIFACT_KINDS else "data"
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref)
        workspace = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.workspaces
                WHERE asset_id = :asset_id AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
                """
                ),
                {"asset_id": asset["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if workspace is None:
            # Custody before workspace creation is always placed on HDD.
            return {
                "storage_role": role,
                "storage_pool_key": HDD_POOL_KEY,
                "storage_provider": HDD_PROVIDER_KEY,
                "quota_bytes": None,
                "used_bytes": 0,
                "remaining_bytes": None,
            }
        binding = (
            session.execute(
                text(
                    """
                SELECT binding_role, pool_key, provider_key, storage_class,
                       status, config
                FROM digital_asset.storage_bindings
                WHERE workspace_id = :workspace_id AND binding_role = :role
                """
                ),
                {"workspace_id": workspace["id"], "role": role},
            )
            .mappings()
            .one_or_none()
        )
        if binding is None or binding["status"] != "ready":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Workspace {role} storage binding is unavailable",
            )
        provider_key = str(binding["provider_key"])
        if role == "data" and provider_key != HDD_PROVIDER_KEY:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Workspace data storage policy is invalid; HDD is required",
            )
        usage = _workspace_billable_usage(
            session,
            tenant_id=actor.tenant_id,
            workspace_id=workspace["id"],
            asset_id=asset["id"],
        )
        used_bytes = usage["total_bytes"]
        quota_bytes = int(workspace["storage_quota_bytes"])
        return {
            "workspace_id": str(workspace["id"]),
            "storage_role": role,
            "storage_pool_key": str(binding["pool_key"]),
            "storage_provider": provider_key,
            "quota_bytes": quota_bytes,
            "used_bytes": used_bytes,
            "remaining_bytes": max(quota_bytes - used_bytes, 0),
            "usage": usage,
        }


def _slug(value: object, *, prefix: str = "app") -> str:
    compact = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    compact = compact[:48] or prefix
    candidate = compact if len(compact) >= 3 else f"{prefix}-{compact}"
    return candidate[:63].rstrip("-")


def _sha256(value: object, *, label: str = "sha256") -> str | None:
    raw = str(value or "").strip().lower()
    if not raw:
        return None
    if not SHA256_RE.fullmatch(raw):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label} must be a 64-character lowercase SHA-256",
        )
    return raw


def _uuid_or_none(value: object) -> UUID | None:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _asset_row(session: Session, asset_ref: object, *, lock: bool = False) -> dict[str, object]:
    suffix = " FOR UPDATE" if lock else ""
    asset_uuid = _uuid_or_none(asset_ref)
    if asset_uuid is not None:
        condition = "id = :asset_uuid"
        params: dict[str, object] = {"asset_uuid": asset_uuid}
    elif str(asset_ref).isdigit():
        condition = "legacy_id = :legacy_id"
        params = {"legacy_id": int(str(asset_ref))}
    else:
        # A human or the Runtime may retain a stable asset number or the exact
        # business name in its working set.  Resolve both, but never silently
        # pick one of several same-name assets.
        condition = "(asset_no = :asset_ref OR lower(name) = lower(:asset_ref))"
        params = {"asset_ref": str(asset_ref).strip()}
    rows = (
        session.execute(
            text(f"SELECT * FROM digital_asset.assets WHERE {condition}{suffix}"),
            params,
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Digital asset not found")
    if len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "asset_ref_ambiguous",
                "ref": str(asset_ref),
                "matches": len(rows),
            },
        )
    return dict(rows[0])


def _workspace_row(
    session: Session, workspace_ref: object, *, lock: bool = False
) -> dict[str, object]:
    suffix = " FOR UPDATE" if lock else ""
    workspace_uuid = _uuid_or_none(workspace_ref)
    if workspace_uuid is not None:
        condition = "id = :workspace_uuid"
        params: dict[str, object] = {"workspace_uuid": workspace_uuid}
    elif str(workspace_ref).isdigit():
        condition = "legacy_id = :legacy_id"
        params = {"legacy_id": int(str(workspace_ref))}
    else:
        condition = "workspace_key = :workspace_key"
        params = {"workspace_key": str(workspace_ref).strip()}
    row = (
        session.execute(
            text(f"SELECT * FROM digital_asset.workspaces WHERE {condition}{suffix}"),
            params,
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return dict(row)


def _public_asset(row: dict[str, object]) -> dict[str, object]:
    return _json_safe(
        {
            **row,
            "id": int(row["legacy_id"]),
            "uuid": row["id"],
            "tags": row.get("tags") or [],
            "metadata": row.get("metadata") or {},
        }
    )


def _public_version(row: dict[str, object]) -> dict[str, object]:
    return _json_safe(
        {
            **row,
            "id": int(row["legacy_id"]),
            "uuid": row["id"],
            "artifact_hash": row.get("artifact_sha256"),
        }
    )


def workspace_entry_path(tenant_slug: str, workspace_key: str) -> str:
    """Return the stable, tenant-safe entry path reserved at workspace creation."""

    return f"/assets/{tenant_slug}/{workspace_key}/"


def workspace_entry_url(tenant_slug: str, workspace_key: str) -> str:
    return f"{get_settings().public_origin}{workspace_entry_path(tenant_slug, workspace_key)}"


def _workspace_entry_fields(tenant_slug: str, row: dict[str, object]) -> dict[str, object]:
    path = workspace_entry_path(tenant_slug, str(row["workspace_key"]))
    entry = workspace_entry_url(tenant_slug, str(row["workspace_key"]))
    verified_application_url = row.get("public_url")
    return {
        "entry_path": path,
        "entry_url": entry,
        "hosting_url": entry,
        "hosting_url_status": "active",
        # Compatibility for the older frontend field. It now means the real
        # reserved entry rather than a guessed, globally ambiguous path.
        "public_path": path,
        "application_url": verified_application_url,
        "entry_kind": ("deployed_application" if verified_application_url else "workspace_status"),
    }


def _public_workspace(row: dict[str, object], tenant_slug: str | None = None) -> dict[str, object]:
    config = row.get("config") if isinstance(row.get("config"), dict) else {}
    payload = {
        **row,
        "id": int(row["legacy_id"]),
        "uuid": row["id"],
        "workspace": row["workspace_key"],
        "database_uri": None,
        "storage": {
            "code": {
                "medium": str(config.get("code_storage") or "hdd"),
                "selection": ("explicit" if config.get("code_storage") == "ssd" else "default"),
            },
            "data": {"medium": "hdd", "selection": "enforced"},
            "data_storage_enforced": "hdd",
            "quota_is_logical": True,
            "quota_step_bytes": WORKSPACE_QUOTA_STEP_BYTES,
        },
    }
    if tenant_slug:
        payload.update(_workspace_entry_fields(tenant_slug, row))
    return _json_safe(payload)


def _public_deployment(row: dict[str, object]) -> dict[str, object]:
    provider = runtime_provider_observation()
    return _json_safe(
        {
            **row,
            "id": int(row["legacy_id"]),
            "uuid": row["id"],
            "runtime_available": provider["runtime_available"],
            "runtime_provider_state": provider["runtime_provider_state"],
            "runtime_observed_at": provider["runtime_observed_at"],
            "runtime_claimed": row.get("provider_key") != "runtime_queue",
        }
    )


def runtime_provider_observation() -> dict[str, object]:
    """Return infrastructure liveness without exposing worker identities."""

    stale_seconds = max(5, get_settings().runtime_controller_stale_seconds)
    try:
        with system_session() as session:
            row = (
                session.execute(
                    text(
                        """
                        SELECT
                          count(*) FILTER (
                            WHERE last_seen_at > now() - make_interval(secs => :stale)
                          ) AS fresh_workers,
                          count(*) FILTER (
                            WHERE status = 'online'
                              AND last_seen_at > now() - make_interval(secs => :stale)
                          ) AS online_workers,
                          max(last_seen_at) AS observed_at
                        FROM platform.runtime_workers
                        """
                    ),
                    {"stale": stale_seconds},
                )
                .mappings()
                .one()
            )
    except Exception:
        return {
            "runtime_available": False,
            "runtime_provider_state": "unobserved",
            "runtime_observed_at": None,
        }
    fresh = int(row["fresh_workers"] or 0)
    online = int(row["online_workers"] or 0)
    return {
        "runtime_available": online > 0,
        "runtime_provider_state": (
            "online" if online > 0 else "degraded" if fresh > 0 else "offline"
        ),
        "runtime_observed_at": row["observed_at"],
    }


def _world_entity(
    resource: str,
    row: dict[str, object],
    *,
    ref_field: str,
    facts: dict[str, object] | None = None,
) -> dict[str, object]:
    """Describe observed world state without prescribing an AI workflow."""

    return _json_safe(
        {
            "resource": resource,
            "id": row.get("id"),
            "legacy_id": row.get("legacy_id"),
            "ref": row.get(ref_field),
            "facts": facts or {},
        }
    )


def _world_observation(
    *,
    operation: str,
    effect: str,
    primary: dict[str, object],
    related: list[dict[str, object]] | None = None,
    verified_facts: dict[str, object] | None = None,
    uncertainties: list[dict[str, object]] | None = None,
    affordances: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Return an Observe–Plan–Act–Reflect evidence packet.

    The packet deliberately contains no next-step decision or fixed state
    transition.  It tells the Runtime what changed, what is known, what is not
    yet known, and which capabilities are relevant.  The AI remains the owner
    of whether and how to continue.
    """

    return {
        "schema": "warehouse.world-observation.v1",
        "operation": operation,
        "effect": effect,
        "primary_entity": primary,
        "related_entities": related or [],
        "verified_facts": _json_safe(verified_facts or {}),
        "uncertainties": _json_safe(uncertainties or []),
        "affordances": _json_safe(affordances or []),
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
    }


def _custody_event(
    session: Session,
    *,
    tenant_id: UUID,
    asset_id: UUID,
    actor_user_id: UUID | None,
    event_type: str,
    artifact_sha256: str | None,
    details: dict[str, object],
    version_id: UUID | None = None,
    artifact_id: UUID | None = None,
) -> dict[str, object]:
    session.execute(
        text("SELECT id FROM digital_asset.assets WHERE id = :asset_id FOR UPDATE"),
        {"asset_id": asset_id},
    ).one()
    previous_hash = session.execute(
        text(
            """
            SELECT event_hash
            FROM digital_asset.custody_events
            WHERE asset_id = :asset_id
            ORDER BY sequence DESC
            LIMIT 1
            """
        ),
        {"asset_id": asset_id},
    ).scalar_one_or_none()
    created_at = datetime.now(UTC)
    event_id = uuid4()
    canonical = json.dumps(
        {
            "id": str(event_id),
            "tenant_id": str(tenant_id),
            "asset_id": str(asset_id),
            "version_id": str(version_id) if version_id else None,
            "artifact_id": str(artifact_id) if artifact_id else None,
            "event_type": event_type,
            "artifact_sha256": artifact_sha256,
            "details": details,
            "previous_event_hash": previous_hash,
            "created_at": created_at.isoformat(),
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    event_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    row = (
        session.execute(
            text(
                """
                INSERT INTO digital_asset.custody_events(
                  id, tenant_id, asset_id, version_id, artifact_id, event_type,
                  artifact_sha256, details, previous_event_hash, event_hash,
                  created_by, created_at
                ) VALUES (
                  :id, :tenant_id, :asset_id, :version_id, :artifact_id, :event_type,
                  :artifact_sha256, CAST(:details AS jsonb), :previous_event_hash,
                  :event_hash, :created_by, :created_at
                )
                RETURNING *
                """
            ),
            {
                "id": event_id,
                "tenant_id": tenant_id,
                "asset_id": asset_id,
                "version_id": version_id,
                "artifact_id": artifact_id,
                "event_type": event_type,
                "artifact_sha256": artifact_sha256,
                "details": json.dumps(details, ensure_ascii=False, default=str),
                "previous_event_hash": previous_hash,
                "event_hash": event_hash,
                "created_by": actor_user_id,
                "created_at": created_at,
            },
        )
        .mappings()
        .one()
    )
    return _json_safe(dict(row))


def create_asset(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require_manage(actor)
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="name is required",
        )
    asset_kind = str(payload.get("asset_kind") or payload.get("kind") or "software").lower()
    risk_level = str(payload.get("risk_level") or "medium").lower()
    if asset_kind not in ASSET_KINDS:
        raise HTTPException(status_code=422, detail="Invalid asset_kind")
    if risk_level not in RISK_LEVELS:
        raise HTTPException(status_code=422, detail="Invalid risk_level")
    asset_id = uuid4()
    asset_no = f"DMA-{datetime.now(UTC):%Y%m%d}-{asset_id.hex[:8].upper()}"
    tags = _normalise_tags(payload.get("tags"))
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.assets(
                      id, tenant_id, asset_no, asset_kind, name, summary,
                      source_module, source_ref_type, source_ref_id,
                      owner_user_id, owner_name, risk_level, tags, metadata,
                      created_by
                    ) VALUES (
                      :id, :tenant_id, :asset_no, :asset_kind, :name, :summary,
                      :source_module, :source_ref_type, :source_ref_id,
                      :owner_user_id, :owner_name, :risk_level,
                      CAST(:tags AS jsonb), CAST(:metadata AS jsonb), :created_by
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": asset_id,
                    "tenant_id": actor.tenant_id,
                    "asset_no": asset_no,
                    "asset_kind": asset_kind,
                    "name": name,
                    "summary": str(payload.get("summary") or "").strip() or None,
                    "source_module": payload.get("source_module"),
                    "source_ref_type": payload.get("source_ref_type"),
                    "source_ref_id": payload.get("source_ref_id"),
                    "owner_user_id": actor.user_id,
                    "owner_name": payload.get("owner_name") or actor.display_name,
                    "risk_level": risk_level,
                    "tags": json.dumps(tags, ensure_ascii=False),
                    "metadata": json.dumps(metadata, ensure_ascii=False, default=str),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        event = _custody_event(
            session,
            tenant_id=actor.tenant_id,
            asset_id=asset_id,
            actor_user_id=actor.user_id,
            event_type="registered",
            artifact_sha256=None,
            details={"asset_no": asset_no, "name": name},
        )
        _audit(
            session,
            actor,
            "digital_asset.created",
            {"asset_id": str(asset_id), "asset_no": asset_no, "kind": asset_kind},
        )
    return {"ok": True, "asset": _public_asset(dict(row)), "custody_event": event}


def update_asset(
    actor: ActorContext,
    asset_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Update the mutable digital-asset master record with an audited event."""

    _require_manage(actor)
    values: dict[str, object] = {}
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="name cannot be empty")
        values["name"] = name[:200]
    if "summary" in payload:
        values["summary"] = str(payload.get("summary") or "").strip() or None
    if "asset_kind" in payload or "kind" in payload:
        asset_kind = str(payload.get("asset_kind") or payload.get("kind") or "").lower()
        if asset_kind not in ASSET_KINDS:
            raise HTTPException(status_code=422, detail="Invalid asset_kind")
        values["asset_kind"] = asset_kind
    if "status" in payload:
        asset_status = str(payload.get("status") or "").lower()
        if asset_status not in ASSET_STATUSES or asset_status == "archived":
            raise HTTPException(
                status_code=422,
                detail="Invalid status; use the archive operation for archived",
            )
        values["status"] = asset_status
    if "lifecycle_stage" in payload:
        lifecycle_stage = str(payload.get("lifecycle_stage") or "").lower()
        if lifecycle_stage not in ASSET_LIFECYCLE_STAGES:
            raise HTTPException(status_code=422, detail="Invalid lifecycle_stage")
        values["lifecycle_stage"] = lifecycle_stage
    if "risk_level" in payload:
        risk_level = str(payload.get("risk_level") or "").lower()
        if risk_level not in RISK_LEVELS:
            raise HTTPException(status_code=422, detail="Invalid risk_level")
        values["risk_level"] = risk_level
    if "tags" in payload:
        values["tags"] = json.dumps(_normalise_tags(payload.get("tags")), ensure_ascii=False)

    if not values:
        raise HTTPException(status_code=422, detail="No supported asset fields supplied")

    json_fields = {"tags"}
    assignments = [
        f"{field} = CAST(:{field} AS jsonb)" if field in json_fields else f"{field} = :{field}"
        for field in values
    ]
    with tenant_session(actor.tenant_id) as session:
        before = _asset_row(session, asset_ref, lock=True)
        row = (
            session.execute(
                text(
                    f"""
                    UPDATE digital_asset.assets
                    SET {", ".join(assignments)}
                    WHERE id = :asset_id
                    RETURNING *
                    """
                ),
                {**values, "asset_id": before["id"]},
            )
            .mappings()
            .one()
        )
        changed = {
            field: {"before": _json_safe(before.get(field)), "after": _json_safe(row[field])}
            for field in values
            if before.get(field) != row[field]
        }
        event = _custody_event(
            session,
            tenant_id=actor.tenant_id,
            asset_id=before["id"],
            actor_user_id=actor.user_id,
            event_type="update",
            artifact_sha256=None,
            details={"changed_fields": changed},
        )
        _audit(
            session,
            actor,
            "digital_asset.updated",
            {
                "asset_id": str(before["id"]),
                "asset_no": before["asset_no"],
                "changed_fields": changed,
            },
        )
    return {
        "ok": True,
        "asset": _public_asset(dict(row)),
        "changed_fields": changed,
        "custody_event": event,
    }


def archive_asset(
    actor: ActorContext,
    asset_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Soft-archive an asset, optionally reconciling an empty duplicate.

    This is a lifecycle invariant rather than an AI workflow.  The operation
    preserves every custody record, refuses to merge non-empty identities, and
    refuses to claim that an externally active deployment was stopped merely
    because database state changed.
    """

    _require_manage(actor)
    reason = str(payload.get("reason") or "").strip() or "Archived by operator"
    expected_asset_no = str(payload.get("asset_no") or "").strip()
    reconcile_ref = payload.get("reconciled_into") or payload.get("target_ref")
    now = datetime.now(UTC)
    with tenant_session(actor.tenant_id) as session:
        source = _asset_row(session, asset_ref, lock=True)
        if expected_asset_no and expected_asset_no != source["asset_no"]:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "asset_identity_mismatch",
                    "expected": expected_asset_no,
                    "observed": source["asset_no"],
                },
            )

        target: dict[str, object] | None = None
        if reconcile_ref not in (None, ""):
            target = _asset_row(session, reconcile_ref, lock=True)
            if target["id"] == source["id"]:
                raise HTTPException(
                    status_code=409,
                    detail={"reason": "reconciliation_target_is_source"},
                )

        counts = dict(
            session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM digital_asset.workspaces
                       WHERE asset_id = :asset_id) AS workspaces,
                      (SELECT count(*) FROM digital_asset.asset_versions
                       WHERE asset_id = :asset_id) AS versions,
                      (SELECT count(*) FROM digital_asset.artifacts
                       WHERE asset_id = :asset_id) AS artifacts,
                      (SELECT count(*)
                       FROM digital_asset.deployments AS d
                       JOIN digital_asset.workspaces AS w ON w.id = d.workspace_id
                       WHERE w.asset_id = :asset_id
                         AND d.status IN ('queued','building','deploying','ready'))
                        AS externally_active_deployments
                    """
                ),
                {"asset_id": source["id"]},
            )
            .mappings()
            .one()
        )
        if int(counts["externally_active_deployments"] or 0) > 0:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "external_deployment_shutdown_required",
                    "observed": counts,
                },
            )
        if target is not None and any(
            int(counts[key] or 0) > 0 for key in ("workspaces", "versions", "artifacts")
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "duplicate_has_owned_resources",
                    "message": "Non-empty identities require an evidence-preserving merge adapter",
                    "observed": counts,
                },
            )

        if source["status"] == "archived":
            row = source
            event = None
            changed = False
        else:
            reconciliation = {
                "archive_reason": reason,
                "archived_at": now.isoformat(),
            }
            if target is not None:
                reconciliation.update(
                    {
                        "reconciliation_kind": "duplicate_identity",
                        "reconciled_into": str(target["id"]),
                        "reconciled_into_asset_no": target["asset_no"],
                    }
                )
            row = dict(
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.assets
                        SET status = 'archived',
                            lifecycle_stage = 'retired',
                            metadata = metadata || CAST(:metadata AS jsonb)
                        WHERE id = :asset_id
                        RETURNING *
                        """
                    ),
                    {
                        "asset_id": source["id"],
                        "metadata": json.dumps(reconciliation, ensure_ascii=False),
                    },
                )
                .mappings()
                .one()
            )
            event = _custody_event(
                session,
                tenant_id=actor.tenant_id,
                asset_id=source["id"],
                actor_user_id=actor.user_id,
                event_type="migration" if target is not None else "release",
                artifact_sha256=None,
                details={
                    "operation": (
                        "duplicate_identity_reconciled" if target is not None else "archive"
                    ),
                    "reason": reason,
                    "reconciled_into": str(target["id"]) if target is not None else None,
                    "owned_resource_counts": counts,
                },
            )
            _audit(
                session,
                actor,
                (
                    "digital_asset.duplicate_reconciled"
                    if target is not None
                    else "digital_asset.archived"
                ),
                {
                    "asset_id": str(source["id"]),
                    "asset_no": source["asset_no"],
                    "reconciled_into": str(target["id"]) if target is not None else None,
                    "reason": reason,
                    "owned_resource_counts": counts,
                },
            )
            changed = True

    related = []
    if target is not None:
        related.append(
            _world_entity(
                "digital_asset.asset",
                target,
                ref_field="asset_no",
                facts={"name": target["name"], "reconciliation_target": True},
            )
        )
    return {
        "ok": True,
        "changed": changed,
        "idempotent_replay": not changed,
        "asset": _public_asset(dict(row)),
        "custody_event": event,
        "owned_resource_counts": counts,
        "world_observation": _world_observation(
            operation="digital_asset.archive",
            effect="archive",
            primary=_world_entity(
                "digital_asset.asset",
                dict(row),
                ref_field="asset_no",
                facts={
                    "name": row["name"],
                    "status": row["status"],
                    "lifecycle_stage": row["lifecycle_stage"],
                },
            ),
            related=related,
            verified_facts={
                "soft_archived": row["status"] == "archived",
                "custody_history_preserved": True,
                "identity_merged": False,
                "duplicate_reconciled": target is not None,
                "new_asset_created": False,
            },
        ),
    }


def list_assets(
    actor: ActorContext,
    *,
    limit: int = 300,
    kind: str | None = None,
    status_filter: str | None = None,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT a.*,
                      (
                        SELECT jsonb_build_object(
                          'id', w.legacy_id,
                          'uuid', w.id,
                          'workspace_key', w.workspace_key,
                          'service_plan', w.service_plan,
                          'runtime_type', w.config->>'runtime_type',
                          'runtime_status', w.runtime_status,
                          'storage_quota_bytes', w.storage_quota_bytes,
                          'storage_quota_mb', (w.storage_quota_bytes / 1048576),
                          'code_bytes', COALESCE((
                            SELECT SUM(ar.size_bytes)::bigint
                            FROM digital_asset.artifacts AS ar
                            WHERE ar.asset_id = a.id
                              AND ar.storage_role = 'code'
                              AND ar.state IN (
                                'pending','stored','verified','quarantined','released'
                              )
                          ), 0),
                          'runtime_bytes', COALESCE((
                            SELECT usage.runtime_bytes
                            FROM digital_asset.workspace_usage AS usage
                            WHERE usage.workspace_id = w.id
                          ), 0),
                          'data_volume_bytes', COALESCE((
                            SELECT usage.data_volume_bytes
                            FROM digital_asset.workspace_usage AS usage
                            WHERE usage.workspace_id = w.id
                          ), 0),
                          'data_bytes', COALESCE((
                            SELECT SUM(ar.size_bytes)::bigint
                            FROM digital_asset.artifacts AS ar
                            WHERE ar.asset_id = a.id
                              AND ar.storage_role = 'data'
                              AND ar.state IN (
                                'pending','stored','verified','quarantined','released'
                              )
                          ), 0),
                          'database_bytes', COALESCE((
                            SELECT SUM(db.actual_size_bytes)::bigint
                            FROM digital_asset.database_bindings AS db
                            WHERE db.workspace_id = w.id AND db.status = 'ready'
                          ), 0),
                          'storage_used_bytes',
                            COALESCE((
                              SELECT SUM(ar.size_bytes)::bigint
                              FROM digital_asset.artifacts AS ar
                              WHERE ar.asset_id = a.id
                                AND ar.state IN (
                                  'pending','stored','verified','quarantined','released'
                                )
                            ), 0)
                            + COALESCE((
                              SELECT SUM(db.actual_size_bytes)::bigint
                              FROM digital_asset.database_bindings AS db
                              WHERE db.workspace_id = w.id AND db.status = 'ready'
                            ), 0)
                            + COALESCE((
                            SELECT usage.runtime_bytes
                              FROM digital_asset.workspace_usage AS usage
                              WHERE usage.workspace_id = w.id
                            ), 0),
                          'total_bytes',
                            COALESCE((
                              SELECT SUM(ar.size_bytes)::bigint
                              FROM digital_asset.artifacts AS ar
                              WHERE ar.asset_id = a.id
                                AND ar.state IN (
                                  'pending','stored','verified','quarantined','released'
                                )
                            ), 0)
                            + COALESCE((
                              SELECT SUM(db.actual_size_bytes)::bigint
                              FROM digital_asset.database_bindings AS db
                              WHERE db.workspace_id = w.id AND db.status = 'ready'
                            ), 0)
                            + COALESCE((
                              SELECT usage.runtime_bytes
                              FROM digital_asset.workspace_usage AS usage
                              WHERE usage.workspace_id = w.id
                            ), 0),
                          'measured_at', COALESCE((
                            SELECT usage.measured_at
                            FROM digital_asset.workspace_usage AS usage
                            WHERE usage.workspace_id = w.id
                          ), now()),
                          'public_url', COALESCE(
                            w.public_url,
                            (
                              SELECT dep.public_url
                              FROM digital_asset.deployments AS dep
                              WHERE dep.workspace_id = w.id
                                AND dep.status = 'ready'
                                AND dep.public_url IS NOT NULL
                              ORDER BY dep.updated_at DESC
                              LIMIT 1
                            )
                          ),
                          'site_status', CASE
                            WHEN EXISTS (
                              SELECT 1 FROM digital_asset.deployments AS dep
                              WHERE dep.workspace_id = w.id
                                AND dep.status = 'ready'
                            ) THEN 'ready'
                            WHEN EXISTS (
                              SELECT 1 FROM digital_asset.deployments AS dep
                              WHERE dep.workspace_id = w.id
                            ) THEN COALESCE((
                              SELECT dep.status
                              FROM digital_asset.deployments AS dep
                              WHERE dep.workspace_id = w.id
                              ORDER BY dep.updated_at DESC
                              LIMIT 1
                            ), 'observed')
                            WHEN EXISTS (
                              SELECT 1 FROM digital_asset.asset_versions AS v
                              WHERE v.asset_id = a.id
                            ) OR EXISTS (
                              SELECT 1 FROM digital_asset.artifacts AS ar
                              WHERE ar.asset_id = a.id
                                AND ar.storage_role = 'code'
                            ) THEN 'not_deployed'
                            ELSE 'source_required'
                          END,
                          'latest_deployment_status', (
                            SELECT dep.status
                            FROM digital_asset.deployments AS dep
                            WHERE dep.workspace_id = w.id
                            ORDER BY dep.updated_at DESC
                            LIMIT 1
                          ),
                          'latest_deployment_health', (
                            SELECT dep.health
                            FROM digital_asset.deployments AS dep
                            WHERE dep.workspace_id = w.id
                            ORDER BY dep.updated_at DESC
                            LIMIT 1
                          ),
                          'source_version_count', (
                            SELECT count(*)::integer
                            FROM digital_asset.asset_versions AS v
                            WHERE v.asset_id = a.id
                          ),
                          'code_artifact_count', (
                            SELECT count(*)::integer
                            FROM digital_asset.artifacts AS ar
                            WHERE ar.asset_id = a.id
                              AND ar.storage_role = 'code'
                          ),
                          'source_available', (
                            EXISTS (
                              SELECT 1 FROM digital_asset.asset_versions AS v
                              WHERE v.asset_id = a.id
                            ) OR EXISTS (
                              SELECT 1 FROM digital_asset.artifacts AS ar
                              WHERE ar.asset_id = a.id
                                AND ar.storage_role = 'code'
                            )
                          ),
                          'code_storage_switchable', (
                            NOT EXISTS (
                              SELECT 1 FROM digital_asset.asset_versions AS v
                              WHERE v.asset_id = a.id
                            ) AND NOT EXISTS (
                              SELECT 1 FROM digital_asset.artifacts AS ar
                              WHERE ar.asset_id = a.id
                                AND ar.storage_role = 'code'
                            )
                          ),
                          'component_count', (
                            SELECT count(*)::integer
                            FROM digital_asset.workspace_components AS c
                            WHERE c.workspace_id = w.id
                          ),
                          'database_name', (
                            SELECT d.logical_name
                            FROM digital_asset.database_bindings AS d
                            WHERE d.workspace_id = w.id
                            ORDER BY d.created_at
                            LIMIT 1
                          ),
                          'database_status', (
                            SELECT d.status
                            FROM digital_asset.database_bindings AS d
                            WHERE d.workspace_id = w.id
                            ORDER BY d.created_at
                            LIMIT 1
                          ),
                          'database_provider', (
                            SELECT d.provider_key
                            FROM digital_asset.database_bindings AS d
                            WHERE d.workspace_id = w.id
                            ORDER BY d.created_at
                            LIMIT 1
                          ),
                          'database_medium', (
                            SELECT d.physical_medium
                            FROM digital_asset.database_bindings AS d
                            WHERE d.workspace_id = w.id
                            ORDER BY d.created_at
                            LIMIT 1
                          ),
                          'database_size_bytes', (
                            SELECT d.actual_size_bytes
                            FROM digital_asset.database_bindings AS d
                            WHERE d.workspace_id = w.id
                            ORDER BY d.created_at
                            LIMIT 1
                          ),
                          'key_summary', jsonb_build_object(
                            'primary_status', COALESCE((
                              SELECT CASE
                                WHEN c.expires_at IS NOT NULL AND c.expires_at <= now()
                                  THEN 'expired'
                                ELSE 'active'
                              END
                              FROM digital_asset.api_credentials AS c
                              WHERE c.workspace_id = w.id
                                AND c.key_kind = 'primary'
                                AND c.revoked_at IS NULL
                              ORDER BY c.issued_at DESC
                              LIMIT 1
                            ), 'missing'),
                            'delegated_active', (
                              SELECT count(*)::integer
                              FROM digital_asset.api_credentials AS c
                              WHERE c.workspace_id = w.id
                                AND c.key_kind = 'delegated'
                                AND c.revoked_at IS NULL
                                AND (c.expires_at IS NULL OR c.expires_at > now())
                            ),
                            'delegated_total', (
                              SELECT count(*)::integer
                              FROM digital_asset.api_credentials AS c
                              WHERE c.workspace_id = w.id
                                AND c.key_kind = 'delegated'
                            )
                          ),
                          'storage', COALESCE((
                            SELECT jsonb_object_agg(
                              sb.binding_role,
                              jsonb_build_object(
                                'role', sb.binding_role,
                                'medium', COALESCE(
                                  sb.config->>'medium',
                                  CASE WHEN sb.provider_key = 'content_addressed_ssd'
                                    THEN 'ssd' ELSE 'hdd' END
                                ),
                                'pool_key', sb.pool_key,
                                'provider_key', sb.provider_key,
                                'storage_class', sb.storage_class,
                                'status', sb.status,
                                'selection', sb.config->>'selection'
                              )
                            )
                            FROM digital_asset.storage_bindings AS sb
                            WHERE sb.workspace_id = w.id
                          ), '{}'::jsonb)
                        )
                        FROM digital_asset.workspaces AS w
                        WHERE w.asset_id = a.id AND w.status = 'active'
                        ORDER BY w.updated_at DESC
                        LIMIT 1
                      ) AS workspace,
                      (
                        SELECT count(*) FROM digital_asset.asset_versions AS v
                        WHERE v.asset_id = a.id
                      ) AS version_count
                    FROM digital_asset.assets AS a
                    WHERE (
                      CAST(:kind AS text) IS NULL
                      OR a.asset_kind = CAST(:kind AS text)
                    )
                      AND (
                        CAST(:status AS text) IS NULL
                        OR a.status = CAST(:status AS text)
                      )
                      AND (
                        CAST(:status AS text) IS NOT NULL
                        OR a.status != 'archived'
                      )
                    ORDER BY a.updated_at DESC, a.legacy_id DESC
                    LIMIT :limit
                    """
                ),
                {
                    "kind": kind,
                    "status": status_filter,
                    "limit": max(1, min(int(limit), 1000)),
                },
            )
            .mappings()
            .all()
        )
    assets = [_public_asset(dict(row)) for row in rows]
    for asset in assets:
        workspace = asset.get("workspace") if isinstance(asset, dict) else None
        if isinstance(workspace, dict) and workspace.get("workspace_key"):
            workspace.update(
                {
                    "source_archive_bytes": int(workspace.get("code_bytes") or 0),
                    "runtime_release_bytes": int(workspace.get("runtime_bytes") or 0),
                    "managed_data_object_bytes": int(workspace.get("data_bytes") or 0),
                    "postgresql_bytes": int(workspace.get("database_bytes") or 0),
                }
            )
            total_bytes = sum(
                int(workspace.get(key) or 0)
                for key in (
                    "source_archive_bytes",
                    "runtime_release_bytes",
                    "data_volume_bytes",
                    "managed_data_object_bytes",
                    "postgresql_bytes",
                )
            )
            workspace["storage_used_bytes"] = total_bytes
            workspace["total_bytes"] = total_bytes
            workspace.update(_workspace_entry_fields(actor.tenant_slug, workspace))
    return {
        "ok": True,
        "available": True,
        "empty": not assets,
        "source": "digital_asset_postgresql",
        "assets": assets,
        "items": assets,
        "total": len(assets),
        "reason": None if assets else "no_records",
    }


def asset_summary(actor: ActorContext) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        kinds = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT asset_kind AS kind, count(*)::integer AS count
                    FROM digital_asset.assets
                    WHERE status != 'archived'
                    GROUP BY asset_kind
                    ORDER BY asset_kind
                    """
                )
            )
            .mappings()
            .all()
        ]
        stages = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT lifecycle_stage AS stage, count(*)::integer AS count
                    FROM digital_asset.assets
                    WHERE status != 'archived'
                    GROUP BY lifecycle_stage
                    ORDER BY lifecycle_stage
                    """
                )
            )
            .mappings()
            .all()
        ]
        totals = dict(
            session.execute(
                text(
                    """
                    SELECT
                      count(*) FILTER (WHERE status != 'archived')::integer AS assets,
                      (
                        SELECT count(*)::integer
                        FROM digital_asset.workspaces
                        WHERE status = 'active'
                      ) AS workspaces,
                      (
                        SELECT count(*)::integer
                        FROM digital_asset.deployments
                        WHERE status = 'ready'
                      ) AS ready_deployments,
                      (
                        SELECT count(*)::integer
                        FROM digital_asset.deployments
                        WHERE status IN ('queued', 'building', 'deploying')
                      ) AS pending_deployments
                    FROM digital_asset.assets
                    """
                )
            )
            .mappings()
            .one()
        )
    return {
        "ok": True,
        "available": True,
        "empty": not totals["assets"],
        "source": "digital_asset_postgresql",
        "by_kind": kinds,
        "by_stage": stages,
        "workspaces": totals["workspaces"],
        "assets": totals["assets"],
        "ready_deployments": totals["ready_deployments"],
        "pending_deployments": totals["pending_deployments"],
        "listings": [],
        "latest_valuation_total_cny": 0,
        "reason": None if totals["assets"] else "no_records",
    }


def asset_detail(actor: ActorContext, asset_ref: object) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref)
        versions = [
            _public_version(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.asset_versions
                    WHERE asset_id = :asset_id
                    ORDER BY created_at DESC
                    """
                ),
                {"asset_id": asset["id"]},
            )
            .mappings()
            .all()
        ]
        custody = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.custody_events
                    WHERE asset_id = :asset_id
                    ORDER BY sequence DESC
                    LIMIT 100
                    """
                ),
                {"asset_id": asset["id"]},
            )
            .mappings()
            .all()
        ]
        workspace_rows = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.workspaces
                    WHERE asset_id = :asset_id
                    ORDER BY updated_at DESC
                    """
                ),
                {"asset_id": asset["id"]},
            )
            .mappings()
            .all()
        ]
        workspaces: list[dict[str, object]] = []
        for workspace in workspace_rows:
            workspace_public = _public_workspace(workspace, actor.tenant_slug)
            measured = _workspace_billable_usage(
                session,
                tenant_id=actor.tenant_id,
                workspace_id=workspace["id"],
                asset_id=workspace["asset_id"],
                refresh_infrastructure=True,
            )
            workspace_public["usage"] = _json_safe(
                {
                    "source_archive_bytes": measured["code_bytes"],
                    "runtime_release_bytes": measured["runtime_bytes"],
                    "data_volume_bytes": measured["data_volume_bytes"],
                    "managed_data_object_bytes": measured["data_object_bytes"],
                    "postgresql_bytes": measured["database_bytes"],
                    "total_bytes": measured["total_bytes"],
                    "measured_at": measured["measured_at"],
                    "measurement_status": measured["measurement_status"],
                }
            )
            workspace_public.update(workspace_public["usage"])
            workspace_public["storage_used_bytes"] = measured["total_bytes"]
            workspace_public["storage"] = _storage_profile(
                _storage_binding_rows(session, workspace["id"])
            )
            workspace_public["components"] = [
                _json_safe(dict(row))
                for row in session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.workspace_components
                        WHERE workspace_id = :workspace_id
                        ORDER BY component_name
                        """
                    ),
                    {"workspace_id": workspace["id"]},
                )
                .mappings()
                .all()
            ]
            workspace_public["databases"] = [
                _json_safe(dict(row))
                for row in session.execute(
                    text(
                        """
                        SELECT id, logical_name, engine, provider_key, isolation_mode,
                               status, endpoint_ref, config, created_at, updated_at
                        FROM digital_asset.database_bindings
                        WHERE workspace_id = :workspace_id
                        ORDER BY logical_name
                        """
                    ),
                    {"workspace_id": workspace["id"]},
                )
                .mappings()
                .all()
            ]
            workspace_public["deployments"] = [
                _public_deployment(dict(row))
                for row in session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.deployments
                        WHERE workspace_id = :workspace_id
                        ORDER BY created_at DESC
                        LIMIT 20
                        """
                    ),
                    {"workspace_id": workspace["id"]},
                )
                .mappings()
                .all()
            ]
            workspaces.append(workspace_public)
    public = _public_asset(asset)
    public.update(
        {
            "versions": versions,
            "custody_events": custody,
            "workspaces": workspaces,
            "workspace": workspaces[0] if workspaces else None,
        }
    )
    return {"ok": True, "available": True, "asset": public}


def add_version(
    actor: ActorContext, asset_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    artifact_sha256 = _sha256(
        payload.get("artifact_sha256") or payload.get("artifact_hash") or payload.get("sha256"),
        label="artifact_hash",
    )
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref, lock=True)
        version_no = str(payload.get("version_no") or payload.get("version") or "").strip()
        if not version_no:
            count = session.execute(
                text(
                    "SELECT count(*) FROM digital_asset.asset_versions WHERE asset_id = :asset_id"
                ),
                {"asset_id": asset["id"]},
            ).scalar_one()
            version_no = f"v{int(count) + 1}"
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.asset_versions(
                      id, tenant_id, asset_id, version_no, title, artifact_uri,
                      artifact_sha256, dependencies, change_log, created_by
                    ) VALUES (
                      :id, :tenant_id, :asset_id, :version_no, :title, :artifact_uri,
                      :artifact_sha256, CAST(:dependencies AS jsonb), :change_log,
                      :created_by
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "asset_id": asset["id"],
                    "version_no": version_no,
                    "title": payload.get("title"),
                    "artifact_uri": payload.get("artifact_uri"),
                    "artifact_sha256": artifact_sha256,
                    "dependencies": json.dumps(payload.get("dependencies") or [], default=str),
                    "change_log": payload.get("change_log"),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.assets
                SET status = CASE WHEN status = 'draft' THEN 'registered' ELSE status END,
                    lifecycle_stage = 'standardize'
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset["id"]},
        )
        _audit(
            session,
            actor,
            "digital_asset.version_added",
            {
                "asset_id": str(asset["id"]),
                "version_id": str(row["id"]),
                "version_no": version_no,
                "sha256": artifact_sha256,
            },
        )
    return {
        "ok": True,
        "version": _public_version(dict(row)),
        "world_observation": _world_observation(
            operation="digital_asset.version.create",
            effect="create",
            primary=_world_entity(
                "digital_asset.asset_version",
                dict(row),
                ref_field="version_no",
                facts={
                    "asset_id": row["asset_id"],
                    "artifact_uri": row.get("artifact_uri"),
                    "artifact_sha256": row.get("artifact_sha256"),
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={"name": asset["name"]},
                )
            ],
            verified_facts={
                "new_asset_created": False,
                "version_attached_to_existing_asset": True,
            },
        ),
    }


def register_artifact(
    actor: ActorContext, asset_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    artifact_sha256 = _sha256(
        payload.get("sha256") or payload.get("artifact_hash"),
        label="artifact_hash",
    )
    if artifact_sha256 is None:
        raise HTTPException(status_code=422, detail="artifact_hash is required")
    artifact_kind = str(payload.get("artifact_kind") or payload.get("upload_type") or "package")
    if artifact_kind == "doc":
        artifact_kind = "document"
    if artifact_kind not in ARTIFACT_KINDS:
        raise HTTPException(status_code=422, detail="Invalid artifact_kind")
    storage_provider = str(payload.get("storage_provider") or "external")
    storage_role = str(
        payload.get("storage_role") or ("code" if artifact_kind in CODE_ARTIFACT_KINDS else "data")
    )
    if storage_role not in STORAGE_ROLES:
        raise HTTPException(status_code=422, detail="Invalid storage_role")
    if storage_role == "data" and storage_provider == SSD_PROVIDER_KEY:
        raise HTTPException(
            status_code=422,
            detail="Hosted data cannot be written to the SSD code pool",
        )
    storage_pool_key = payload.get("storage_pool_key")
    if not storage_pool_key and storage_provider in {HDD_PROVIDER_KEY, LEGACY_PROVIDER_KEY}:
        storage_pool_key = HDD_POOL_KEY
    elif not storage_pool_key and storage_provider == SSD_PROVIDER_KEY:
        storage_pool_key = SSD_POOL_KEY
    verification_method = (
        "content_hash_computed" if storage_provider in LOCAL_PROVIDER_KEYS else "declared_sha256"
    )
    artifact_state = "verified" if verification_method == "content_hash_computed" else "stored"
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref, lock=True)
        workspace = (
            session.execute(
                text(
                    """
                SELECT * FROM digital_asset.workspaces
                WHERE asset_id = :asset_id AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1 FOR UPDATE
                """
                ),
                {"asset_id": asset["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if workspace is not None:
            usage_before = _workspace_billable_usage(
                session,
                tenant_id=actor.tenant_id,
                workspace_id=workspace["id"],
                asset_id=asset["id"],
            )
            requested_size = max(0, int(payload.get("size_bytes") or 0))
            projected = usage_before["total_bytes"] + requested_size
            if projected > int(workspace["storage_quota_bytes"]):
                raise HTTPException(
                    status_code=507,
                    detail={
                        "reason": "workspace_quota_exceeded",
                        "quota_bytes": int(workspace["storage_quota_bytes"]),
                        "used_bytes": usage_before["total_bytes"],
                        "requested_bytes": requested_size,
                        "projected_bytes": projected,
                    },
                )
        version_id = _uuid_or_none(payload.get("version_id"))
        object_key = str(
            payload.get("object_key")
            or payload.get("artifact_uri")
            or f"sha256/{artifact_sha256[:2]}/{artifact_sha256}"
        ).strip()
        artifact_id = uuid4()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.artifacts(
                      id, tenant_id, asset_id, version_id, artifact_kind,
                      filename, content_type, size_bytes, sha256, storage_provider,
                      object_key, storage_role, storage_pool_key,
                      state, verification, created_by
                    ) VALUES (
                      :id, :tenant_id, :asset_id, :version_id, :artifact_kind,
                      :filename, :content_type, :size_bytes, :sha256, :storage_provider,
                      :object_key, :storage_role, :storage_pool_key,
                      :state, CAST(:verification AS jsonb), :created_by
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": artifact_id,
                    "tenant_id": actor.tenant_id,
                    "asset_id": asset["id"],
                    "version_id": version_id,
                    "artifact_kind": artifact_kind,
                    "filename": payload.get("filename"),
                    "content_type": payload.get("content_type"),
                    "size_bytes": int(payload.get("size_bytes") or 0),
                    "sha256": artifact_sha256,
                    "storage_provider": storage_provider,
                    "object_key": object_key,
                    "storage_role": storage_role,
                    "storage_pool_key": storage_pool_key,
                    "state": artifact_state,
                    "verification": json.dumps(
                        {
                            "method": verification_method,
                            "verified_at": (
                                datetime.now(UTC).isoformat()
                                if artifact_state == "verified"
                                else None
                            ),
                        }
                    ),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        custody = _custody_event(
            session,
            tenant_id=actor.tenant_id,
            asset_id=asset["id"],
            actor_user_id=actor.user_id,
            event_type="deposit",
            artifact_sha256=artifact_sha256,
            details={
                "object_key": object_key,
                "storage_provider": storage_provider,
                "storage_role": storage_role,
                "storage_pool_key": storage_pool_key,
                "filename": payload.get("filename"),
                "size_bytes": int(payload.get("size_bytes") or 0),
            },
            version_id=version_id,
            artifact_id=artifact_id,
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.assets
                SET status = 'custodied', lifecycle_stage = 'custody'
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset["id"]},
        )
        _audit(
            session,
            actor,
            "digital_asset.artifact_registered",
            {
                "asset_id": str(asset["id"]),
                "artifact_id": str(artifact_id),
                "sha256": artifact_sha256,
                "storage_role": storage_role,
                "storage_pool_key": storage_pool_key,
            },
        )
        if workspace is not None:
            _workspace_billable_usage(
                session,
                tenant_id=actor.tenant_id,
                workspace_id=workspace["id"],
                asset_id=asset["id"],
            )
    return {
        "ok": True,
        "artifact": _json_safe(dict(row)),
        "custody_event": custody,
        "world_observation": _world_observation(
            operation="digital_asset.artifact.register",
            effect="create",
            primary=_world_entity(
                "digital_asset.artifact",
                dict(row),
                ref_field="object_key",
                facts={
                    "asset_id": row["asset_id"],
                    "version_id": row.get("version_id"),
                    "artifact_kind": row["artifact_kind"],
                    "state": row["state"],
                    "storage_role": row["storage_role"],
                    "storage_pool_key": row.get("storage_pool_key"),
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={"name": asset["name"]},
                )
            ],
            verified_facts={
                "new_asset_created": False,
                "artifact_attached_to_existing_asset": True,
                "custody_event_recorded": True,
            },
        ),
    }


def artifact_descriptor(
    actor: ActorContext, asset_ref: object, artifact_ref: object
) -> dict[str, object]:
    _require_read(actor)
    artifact_uuid = _uuid_or_none(artifact_ref)
    if artifact_uuid is None:
        raise HTTPException(status_code=422, detail="Invalid artifact id")
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref)
        row = (
            session.execute(
                text(
                    """
                    SELECT *
                    FROM digital_asset.artifacts
                    WHERE id = :artifact_id AND asset_id = :asset_id
                    """
                ),
                {"artifact_id": artifact_uuid, "asset_id": asset["id"]},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return _json_safe(dict(row))


def record_custody(
    actor: ActorContext, asset_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    event_type = str(payload.get("event_type") or payload.get("type") or "deposit")
    if event_type not in {
        "deposit",
        "update",
        "verify",
        "quarantine",
        "release",
        "migration",
    }:
        raise HTTPException(status_code=422, detail="Invalid custody event_type")
    artifact_sha256 = _sha256(
        payload.get("artifact_sha256") or payload.get("artifact_hash"),
        label="artifact_hash",
    )
    details = payload.get("details")
    if not isinstance(details, dict):
        details = {"note": str(details)} if details not in (None, "") else {}
    if payload.get("artifact_uri"):
        details["artifact_uri"] = payload["artifact_uri"]
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref, lock=True)
        event = _custody_event(
            session,
            tenant_id=actor.tenant_id,
            asset_id=asset["id"],
            actor_user_id=actor.user_id,
            event_type=event_type,
            artifact_sha256=artifact_sha256,
            details=details,
            version_id=_uuid_or_none(payload.get("version_id")),
            artifact_id=_uuid_or_none(payload.get("artifact_id")),
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.assets
                SET status = CASE
                      WHEN :event_type = 'release' THEN status
                      ELSE 'custodied'
                    END,
                    lifecycle_stage = CASE
                      WHEN :event_type = 'release' THEN lifecycle_stage
                      ELSE 'custody'
                    END
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset["id"], "event_type": event_type},
        )
        _audit(
            session,
            actor,
            "digital_asset.custody_recorded",
            {
                "asset_id": str(asset["id"]),
                "event_type": event_type,
                "event_hash": event["event_hash"],
            },
        )
    return {"ok": True, "custody_event": event}


def _database_provider_request(
    payload: dict[str, object],
) -> tuple[str | None, str | None, bool | None]:
    requested = str(payload.get("provider_key") or payload.get("provider") or "").strip().lower()
    database_url_value = payload.get("database_url")
    database_url = (
        str(database_url_value).strip() if isinstance(database_url_value, str) else None
    )
    if database_url_value is not None and not database_url:
        raise HTTPException(status_code=422, detail="database_url cannot be empty")
    aliases = {
        "": None,
        "managed": "managed",
        "warehouse": "managed",
        "warehouse_managed": "managed",
        hosted_database.HDD_DATABASE_PROVIDER_KEY: "managed",
        "external": hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY,
        "external_postgresql": hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY,
        hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY: (
            hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
        ),
    }
    if requested not in aliases:
        raise HTTPException(status_code=422, detail="Unsupported workspace database provider")
    provider = aliases[requested]
    if database_url and provider in {None, hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY}:
        provider = hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
    if provider == "managed" and database_url:
        raise HTTPException(
            status_code=422,
            detail="database_url is only accepted by the external PostgreSQL provider",
        )
    if provider == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY and not database_url:
        raise HTTPException(
            status_code=422,
            detail="External PostgreSQL provider requires database_url",
        )
    make_default_value = payload.get("is_default", payload.get("default"))
    if make_default_value is not None and not isinstance(make_default_value, bool):
        raise HTTPException(status_code=422, detail="is_default must be a boolean")
    make_default = make_default_value if isinstance(make_default_value, bool) else None
    return provider, database_url, make_default


def _provision_database(
    session: Session,
    *,
    actor: ActorContext,
    workspace: dict[str, object],
    logical_name: str,
    isolation_mode: str = "workspace_rls",
    requested_provider: str | None = None,
    database_url: str | None = None,
    make_default: bool | None = None,
) -> dict[str, object]:
    allowed_isolation = {
        "workspace_rls",
        "dedicated_schema",
        "dedicated_database",
        "dedicated_cluster",
    }
    if isolation_mode not in allowed_isolation:
        raise HTTPException(status_code=422, detail="Invalid database isolation_mode")
    external_provider = requested_provider == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
    hdd_provider = hosted_database.configured()
    if requested_provider == "managed" and not hdd_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"reason": "hosted_database_unavailable"},
        )
    existing = (
        session.execute(
            text(
                """
                SELECT * FROM digital_asset.database_bindings
                WHERE workspace_id=:workspace_id AND logical_name=:logical_name
                FOR UPDATE
                """
            ),
            {"workspace_id": workspace["id"], "logical_name": logical_name},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        existing_row = dict(existing)
        existing_external = (
            str(existing_row["provider_key"])
            == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
        )
        if existing_external != external_provider and requested_provider is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "database_provider_change_requires_new_binding",
                    "logical_name": logical_name,
                    "current_provider": existing_row["provider_key"],
                },
            )
        if existing_external:
            if database_url:
                try:
                    existing_row = hosted_database.provision_external_binding(
                        session,
                        existing_row,
                        database_url=database_url,
                    )
                except ValueError as exc:
                    raise HTTPException(status_code=422, detail=str(exc)) from exc
                except hosted_database.HostedDatabaseUnavailable as exc:
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail={"reason": "external_database_unavailable", "message": str(exc)},
                    ) from exc
        elif hdd_provider:
            try:
                existing_row = hosted_database.migrate_binding(session, existing_row)
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"reason": "hosted_database_unavailable", "message": str(exc)},
                ) from exc
        should_default = make_default is True or not bool(
            session.execute(
                text(
                    "SELECT count(*) FROM digital_asset.database_bindings "
                    "WHERE workspace_id=:workspace_id AND is_default"
                ),
                {"workspace_id": workspace["id"]},
            ).scalar_one()
        )
        if should_default:
            session.execute(
                text(
                    "UPDATE digital_asset.database_bindings SET is_default=false "
                    "WHERE workspace_id=:workspace_id AND id<>:binding_id AND is_default"
                ),
                {"workspace_id": workspace["id"], "binding_id": existing_row["id"]},
            )
            existing_row = dict(
                session.execute(
                    text(
                        "UPDATE digital_asset.database_bindings SET is_default=true "
                        "WHERE id=:binding_id RETURNING *"
                    ),
                    {"binding_id": existing_row["id"]},
                )
                .mappings()
                .one()
            )
        return _json_safe(existing_row)
    if external_provider:
        isolation_mode = "external_database"
        provider_key = hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
        binding_status = "provisioning"
        ownership_mode = "customer_managed"
        capabilities = hosted_database.EXTERNAL_CAPABILITIES
    elif hdd_provider:
        isolation_mode = "dedicated_database"
        provider_key = hosted_database.HDD_DATABASE_PROVIDER_KEY
        binding_status = "provisioning"
        ownership_mode = "platform_managed"
        capabilities = hosted_database.MANAGED_CAPABILITIES
    else:
        provider_key = (
            hosted_database.LEGACY_DATABASE_PROVIDER_KEY
            if isolation_mode == "workspace_rls"
            else "provider_pending"
        )
        binding_status = "ready" if isolation_mode == "workspace_rls" else "provisioning"
        ownership_mode = "platform_managed"
        capabilities = {
            "runtime_dsn": False,
            "collection_data_api": True,
            "relational_data_api": False,
            "schema_introspection": False,
            "migrations": False,
            "platform_backup": False,
            "platform_quota": True,
        }
    binding_id = uuid4()
    endpoint_ref = f"workspace-data://{workspace['id']}/{logical_name}"
    row = dict(
        session.execute(
            text(
                """
                INSERT INTO digital_asset.database_bindings(
                  id, tenant_id, workspace_id, logical_name, engine, provider_key,
                  isolation_mode, status, endpoint_ref, config, created_by,
                  ownership_mode, capabilities
                ) VALUES (
                  :id, :tenant_id, :workspace_id, :logical_name, 'postgresql',
                  :provider_key, :isolation_mode, :status, :endpoint_ref,
                  CAST(:config AS jsonb), :created_by, :ownership_mode,
                  CAST(:capabilities AS jsonb)
                )
                RETURNING *
                """
            ),
            {
                "id": binding_id,
                "tenant_id": actor.tenant_id,
                "workspace_id": workspace["id"],
                "logical_name": logical_name,
                "provider_key": provider_key,
                "isolation_mode": isolation_mode,
                "status": binding_status,
                "endpoint_ref": endpoint_ref,
                "config": json.dumps(
                    {
                        "portable_data_api": True,
                        "native_dsn_exposed": False,
                    }
                ),
                "created_by": actor.user_id,
                "ownership_mode": ownership_mode,
                "capabilities": json.dumps(capabilities),
            },
        )
        .mappings()
        .one()
    )
    if external_provider:
        try:
            row = hosted_database.provision_external_binding(
                session,
                row,
                database_url=str(database_url or ""),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "external_database_unavailable", "message": str(exc)},
            ) from exc
    elif hdd_provider:
        try:
            row = hosted_database.migrate_binding(session, row)
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "reason": "hosted_database_unavailable",
                    "message": str(exc),
                    "physical_medium": "hdd",
                },
            ) from exc
    has_default = bool(
        session.execute(
            text(
                "SELECT count(*) FROM digital_asset.database_bindings "
                "WHERE workspace_id=:workspace_id AND is_default"
            ),
            {"workspace_id": workspace["id"]},
        ).scalar_one()
    )
    should_default = make_default is True or not has_default
    if should_default:
        session.execute(
            text(
                "UPDATE digital_asset.database_bindings SET is_default=false "
                "WHERE workspace_id=:workspace_id AND id<>:binding_id AND is_default"
            ),
            {"workspace_id": workspace["id"], "binding_id": row["id"]},
        )
        row = dict(
            session.execute(
                text(
                    "UPDATE digital_asset.database_bindings SET is_default=true "
                    "WHERE id=:binding_id RETURNING *"
                ),
                {"binding_id": row["id"]},
            )
            .mappings()
            .one()
        )
    return _json_safe(row)


def create_workspace(
    actor: ActorContext, asset_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    service_plan = str(payload.get("service_plan") or payload.get("plan") or "hosted")
    runtime_type = str(payload.get("runtime_type") or payload.get("runtime") or "static")
    if service_plan not in SERVICE_PLANS:
        raise HTTPException(status_code=422, detail="Invalid service_plan")
    if runtime_type not in RUNTIME_TYPES:
        raise HTTPException(status_code=422, detail="Invalid runtime_type")
    code_storage = _code_storage_choice(payload)
    storage_quota_bytes = int(payload.get("storage_quota_bytes") or WORKSPACE_QUOTA_STEP_BYTES)
    if storage_quota_bytes != WORKSPACE_QUOTA_STEP_BYTES:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "new_workspace_quota_is_fixed",
                "default_bytes": WORKSPACE_QUOTA_STEP_BYTES,
                "next_action": "create the workspace, then request 512 MB increments",
            },
        )
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref, lock=True)
        desired_key = _slug(
            payload.get("workspace_key") or f"{asset['name']}-{asset['legacy_id']}",
            prefix="app",
        )
        if not WORKSPACE_KEY_RE.fullmatch(desired_key):
            raise HTTPException(status_code=422, detail="Invalid workspace_key")
        existing = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.workspaces
                    WHERE workspace_key = :workspace_key
                    FOR UPDATE
                    """
                ),
                {"workspace_key": desired_key},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            existing_row = dict(existing)
            if existing_row["asset_id"] != asset["id"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "reason": "workspace_key_owned_by_another_asset",
                        "workspace_key": desired_key,
                    },
                )
            components = [
                _json_safe(dict(component))
                for component in session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.workspace_components
                        WHERE workspace_id = :workspace_id
                        ORDER BY component_name
                        """
                    ),
                    {"workspace_id": existing_row["id"]},
                )
                .mappings()
                .all()
            ]
            database_row = (
                session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.database_bindings
                        WHERE workspace_id = :workspace_id
                        ORDER BY created_at
                        LIMIT 1
                        """
                    ),
                    {"workspace_id": existing_row["id"]},
                )
                .mappings()
                .one_or_none()
            )
            database = _json_safe(dict(database_row)) if database_row is not None else None
            storage = _storage_profile(_storage_binding_rows(session, existing_row["id"]))
            existing_public = _public_workspace(existing_row, actor.tenant_slug)
            existing_public["storage"] = storage
            _audit(
                session,
                actor,
                "digital_asset.workspace_create_observed_existing",
                {
                    "asset_id": str(asset["id"]),
                    "workspace_id": str(existing_row["id"]),
                    "workspace_key": desired_key,
                },
            )
            return {
                "ok": True,
                "created": False,
                "idempotent_replay": True,
                "workspace": existing_public,
                "components": components,
                "database": database,
                "storage": storage,
                "world_observation": _world_observation(
                    operation="digital_asset.workspace.observe_existing",
                    effect="none",
                    primary=_world_entity(
                        "digital_asset.workspace",
                        existing_row,
                        ref_field="workspace_key",
                        facts={
                            "asset_id": existing_row["asset_id"],
                            "runtime_type": (existing_row.get("config") or {}).get("runtime_type"),
                            "runtime_status": existing_row.get("runtime_status"),
                            "entry_url": workspace_entry_url(actor.tenant_slug, desired_key),
                            "hosting_url": workspace_entry_url(actor.tenant_slug, desired_key),
                            "application_url": existing_row.get("public_url"),
                            "storage_quota_bytes": existing_row.get("storage_quota_bytes"),
                            "storage": storage,
                        },
                    ),
                    related=[
                        _world_entity(
                            "digital_asset.asset",
                            asset,
                            ref_field="asset_no",
                            facts={"name": asset["name"]},
                        )
                    ],
                    verified_facts={
                        "workspace_already_exists": True,
                        "workspace_belongs_to_asset": True,
                        "new_workspace_created": False,
                        "permanent_entry_reserved": True,
                        "application_deployed": bool(existing_row.get("public_url")),
                    },
                    affordances=[
                        {
                            "capability": "digital_market_runtime_upgrade",
                            "meaning": "change runtime configuration on this existing workspace",
                        },
                        {
                            "capability": "generic_data_mutate",
                            "meaning": (
                                "change direct workspace fields through the audited "
                                "semantic data layer"
                            ),
                        },
                    ],
                ),
            }
        workspace_id = uuid4()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.workspaces(
                      id, tenant_id, asset_id, workspace_key, service_plan,
                      runtime_status, region, public_url, storage_quota_bytes,
                      config, created_by
                    ) VALUES (
                      :id, :tenant_id, :asset_id, :workspace_key, :service_plan,
                      'provisioned', :region, :public_url, :storage_quota_bytes,
                      CAST(:config AS jsonb), :created_by
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": workspace_id,
                    "tenant_id": actor.tenant_id,
                    "asset_id": asset["id"],
                    "workspace_key": desired_key,
                    "service_plan": service_plan,
                    "region": payload.get("region") or "local",
                    "public_url": payload.get("public_url"),
                    "storage_quota_bytes": storage_quota_bytes,
                    "config": json.dumps(
                        {
                            "runtime_type": runtime_type,
                            "provider_selection": "auto_runtime",
                            "code_storage": code_storage,
                            "data_storage": "hdd",
                        }
                    ),
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        storage_specs = (
            {
                "role": "data",
                "provider": HDD_PROVIDER_KEY,
                "pool": HDD_POOL_KEY,
                "storage_class": "standard",
                "medium": "hdd",
                "selection": "enforced",
            },
            {
                "role": "code",
                "provider": (SSD_PROVIDER_KEY if code_storage == "ssd" else HDD_PROVIDER_KEY),
                "pool": SSD_POOL_KEY if code_storage == "ssd" else HDD_POOL_KEY,
                "storage_class": "performance" if code_storage == "ssd" else "standard",
                "medium": code_storage,
                "selection": "explicit" if code_storage == "ssd" else "default",
            },
        )
        for spec in storage_specs:
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.storage_bindings(
                      id, tenant_id, workspace_id, provider_key, object_prefix,
                      binding_role, pool_key, storage_class, config
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :provider_key, :object_prefix,
                      :binding_role, :pool_key, :storage_class, CAST(:config AS jsonb)
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "workspace_id": workspace_id,
                    "provider_key": spec["provider"],
                    "object_prefix": (
                        f"tenants/{actor.tenant_id}/workspaces/{workspace_id}/{spec['role']}/"
                    ),
                    "binding_role": spec["role"],
                    "pool_key": spec["pool"],
                    "storage_class": spec["storage_class"],
                    "config": json.dumps(
                        {
                            "portable": True,
                            "medium": spec["medium"],
                            "selection": spec["selection"],
                            "data_must_use_hdd": spec["role"] == "data",
                        }
                    ),
                },
            )
        storage = _storage_profile(_storage_binding_rows(session, workspace_id))
        component_specs: list[tuple[str, str, str]] = []
        if runtime_type == "static":
            component_specs.append(("frontend", "frontend", "static"))
        elif runtime_type in {"web", "api"}:
            component_specs.extend(
                [
                    ("frontend", "frontend", "static"),
                    ("api", "backend", str(payload.get("backend_runtime") or "python3.12")),
                ]
            )
        elif runtime_type == "worker":
            component_specs.append(("worker", "worker", "python3.12"))
        elif runtime_type in {"container", "compose"}:
            component_specs.append(("api", "backend", "container"))
        else:
            component_specs.append(("agent", "agent", "python3.12"))
        components: list[dict[str, object]] = []
        for component_name, component_kind, runtime in component_specs:
            component = (
                session.execute(
                    text(
                        """
                        INSERT INTO digital_asset.workspace_components(
                          id, tenant_id, workspace_id, component_name,
                          component_kind, runtime, created_by
                        ) VALUES (
                          :id, :tenant_id, :workspace_id, :component_name,
                          :component_kind, :runtime, :created_by
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": actor.tenant_id,
                        "workspace_id": workspace_id,
                        "component_name": component_name,
                        "component_kind": component_kind,
                        "runtime": runtime,
                        "created_by": actor.user_id,
                    },
                )
                .mappings()
                .one()
            )
            components.append(_json_safe(dict(component)))
        database = None
        no_database = bool(payload.get("no_database")) or service_plan == "custody"
        requested_provider, database_url, make_default = _database_provider_request(payload)
        if no_database and (requested_provider is not None or database_url):
            raise HTTPException(
                status_code=422,
                detail="no_database cannot be combined with a database provider",
            )
        if not no_database:
            logical_name = re.sub(
                r"[^a-z0-9_]+",
                "_",
                str(payload.get("database_name") or f"app_{desired_key}").lower(),
            ).strip("_")[:63]
            if not logical_name or not logical_name[0].isalpha():
                logical_name = f"app_{workspace_id.hex[:12]}"
            database = _provision_database(
                session,
                actor=actor,
                workspace=dict(row),
                logical_name=logical_name,
                isolation_mode=str(payload.get("isolation_mode") or "workspace_rls"),
                requested_provider=requested_provider,
                database_url=database_url,
                make_default=True if make_default is None else make_default,
            )
        session.execute(
            text(
                """
                UPDATE digital_asset.assets
                SET status = CASE
                      WHEN status = 'archived' THEN status
                      ELSE 'active'
                    END,
                    lifecycle_stage = 'provisioned'
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset["id"]},
        )
        _audit(
            session,
            actor,
            "digital_asset.workspace_created",
            {
                "asset_id": str(asset["id"]),
                "workspace_id": str(workspace_id),
                "workspace_key": desired_key,
                "service_plan": service_plan,
                "runtime_type": runtime_type,
                "code_storage": code_storage,
                "data_storage": "hdd",
                "database_provider": database.get("provider_key") if database else None,
            },
        )
    workspace_public = _public_workspace(dict(row), actor.tenant_slug)
    workspace_public["storage"] = storage
    return {
        "ok": True,
        "created": True,
        "workspace": workspace_public,
        "components": components,
        "database": database,
        "storage": storage,
        "world_observation": _world_observation(
            operation="digital_asset.workspace.create",
            effect="create",
            primary=_world_entity(
                "digital_asset.workspace",
                dict(row),
                ref_field="workspace_key",
                facts={
                    "asset_id": row["asset_id"],
                    "runtime_type": (row.get("config") or {}).get("runtime_type"),
                    "runtime_status": row.get("runtime_status"),
                    "entry_url": workspace_entry_url(actor.tenant_slug, str(row["workspace_key"])),
                    "hosting_url": workspace_entry_url(
                        actor.tenant_slug, str(row["workspace_key"])
                    ),
                    "application_url": row.get("public_url"),
                    "storage_quota_bytes": row.get("storage_quota_bytes"),
                    "storage": storage,
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={"name": asset["name"]},
                )
            ],
            verified_facts={
                "workspace_created": True,
                "database_bound": database is not None,
                "component_count": len(components),
                "permanent_entry_reserved": True,
                "application_deployed": False,
                "code_storage_defaulted_to_hdd": code_storage == "hdd",
                "ssd_selected_explicitly": code_storage == "ssd",
                "data_storage_enforced_hdd": True,
            },
        ),
    }


def workspace_asset_identity(actor: ActorContext, workspace_ref: object) -> dict[str, object]:
    """Resolve the canonical asset behind a workspace for Runtime continuity."""

    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        asset = _asset_row(session, workspace["asset_id"])
    return {
        "workspace": _public_workspace(workspace, actor.tenant_slug),
        "asset": _public_asset(asset),
        "world_observation": _world_observation(
            operation="digital_asset.workspace.resolve_asset",
            effect="read",
            primary=_world_entity(
                "digital_asset.workspace",
                workspace,
                ref_field="workspace_key",
                facts={
                    "asset_id": workspace["asset_id"],
                    "entry_url": workspace_entry_url(
                        actor.tenant_slug, str(workspace["workspace_key"])
                    ),
                    "hosting_url": workspace_entry_url(
                        actor.tenant_slug, str(workspace["workspace_key"])
                    ),
                    "application_url": workspace.get("public_url"),
                    "storage_quota_bytes": workspace.get("storage_quota_bytes"),
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={"name": asset["name"]},
                )
            ],
            verified_facts={
                "workspace_belongs_to_asset": True,
                "permanent_entry_reserved": True,
                "application_deployed": bool(workspace.get("public_url")),
            },
        ),
    }


def public_workspace_status(tenant_slug: str, workspace_key: str) -> dict[str, object]:
    """Resolve the non-secret landing state for one permanent workspace entry."""

    with system_session() as session:
        tenant = (
            session.execute(
                text("SELECT id, slug, name FROM iam.tenants WHERE slug = :slug"),
                {"slug": tenant_slug.strip().lower()},
            )
            .mappings()
            .one_or_none()
        )
    if tenant is None:
        raise HTTPException(status_code=404, detail="Hosted workspace not found")
    with tenant_session(tenant["id"]) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT w.*, a.asset_no, a.name AS asset_name,
                       a.asset_kind, a.summary AS asset_summary,
                       COALESCE((
                         SELECT SUM(ar.size_bytes)::bigint
                         FROM digital_asset.artifacts AS ar
                         WHERE ar.asset_id = a.id
                           AND ar.storage_role = 'code'
                           AND ar.state IN (
                             'pending','stored','verified','quarantined','released'
                           )
                       ), 0) AS code_bytes,
                       COALESCE((
                         SELECT SUM(ar.size_bytes)::bigint
                         FROM digital_asset.artifacts AS ar
                         WHERE ar.asset_id = a.id
                           AND ar.storage_role = 'data'
                           AND ar.state IN (
                             'pending','stored','verified','quarantined','released'
                           )
                       ), 0) AS data_bytes,
                       COALESCE((
                         SELECT SUM(db.actual_size_bytes)::bigint
                         FROM digital_asset.database_bindings AS db
                         WHERE db.workspace_id = w.id AND db.status = 'ready'
                       ), 0) AS database_bytes,
                       COALESCE((
                         SELECT usage.runtime_bytes
                         FROM digital_asset.workspace_usage AS usage
                         WHERE usage.workspace_id = w.id
                       ), 0) AS runtime_bytes,
                       COALESCE((
                         SELECT usage.data_volume_bytes
                         FROM digital_asset.workspace_usage AS usage
                         WHERE usage.workspace_id = w.id
                       ), 0) AS data_volume_bytes,
                       COALESCE((
                         SELECT usage.measured_at
                         FROM digital_asset.workspace_usage AS usage
                         WHERE usage.workspace_id = w.id
                       ), now()) AS usage_measured_at,
                       COALESCE((
                         SELECT SUM(ar.size_bytes)::bigint
                         FROM digital_asset.artifacts AS ar
                         WHERE ar.asset_id = a.id
                           AND ar.state IN (
                             'pending','stored','verified','quarantined','released'
                           )
                       ), 0)
                       + COALESCE((
                         SELECT SUM(db.actual_size_bytes)::bigint
                         FROM digital_asset.database_bindings AS db
                         WHERE db.workspace_id = w.id AND db.status = 'ready'
                       ), 0)
                       + COALESCE((
                         SELECT usage.runtime_bytes
                         FROM digital_asset.workspace_usage AS usage
                         WHERE usage.workspace_id = w.id
                       ), 0)
                       + COALESCE((
                         SELECT usage.data_volume_bytes
                         FROM digital_asset.workspace_usage AS usage
                         WHERE usage.workspace_id = w.id
                       ), 0) AS storage_used_bytes,
                       (
                         SELECT db.physical_medium
                         FROM digital_asset.database_bindings AS db
                         WHERE db.workspace_id = w.id
                         ORDER BY db.created_at
                         LIMIT 1
                       ) AS database_medium,
                       (
                         EXISTS (
                           SELECT 1 FROM digital_asset.asset_versions AS v
                           WHERE v.asset_id = a.id
                         ) OR EXISTS (
                           SELECT 1 FROM digital_asset.artifacts AS ar
                           WHERE ar.asset_id = a.id
                             AND ar.storage_role = 'code'
                         )
                       ) AS source_available,
                       (
                         SELECT count(*)::integer
                         FROM digital_asset.asset_versions AS v
                         WHERE v.asset_id = a.id
                       ) AS source_version_count,
                       (
                         SELECT count(*)::integer
                         FROM digital_asset.artifacts AS ar
                         WHERE ar.asset_id = a.id
                           AND ar.storage_role = 'code'
                       ) AS code_artifact_count,
                       COALESCE((
                         SELECT jsonb_agg(
                           jsonb_build_object(
                             'binding_role', sb.binding_role,
                             'pool_key', sb.pool_key,
                             'provider_key', sb.provider_key,
                             'storage_class', sb.storage_class,
                             'status', sb.status,
                             'config', sb.config
                           ) ORDER BY sb.binding_role
                         )
                         FROM digital_asset.storage_bindings AS sb
                         WHERE sb.workspace_id = w.id
                       ), '[]'::jsonb) AS storage_bindings,
                       (
                         SELECT jsonb_build_object(
                           'status', d.status,
                           'health', d.health,
                           'public_url', d.public_url,
                           'updated_at', d.updated_at,
                           'failure_reason', CASE
                             WHEN d.status = 'failed'
                               AND COALESCE(d.result->>'error', '')
                                 ILIKE 'Static Runtime requires index.html%'
                               THEN 'runtime_contract_mismatch'
                             WHEN d.status = 'failed' THEN 'deployment_failed'
                             ELSE NULL
                           END,
                           'next_action', CASE
                             WHEN d.status = 'failed'
                               AND COALESCE(d.result->>'error', '')
                                 ILIKE 'Static Runtime requires index.html%'
                               THEN 'configure_runtime_and_redeploy'
                             WHEN d.status = 'failed' THEN 'inspect_deployment'
                             ELSE NULL
                           END
                         )
                         FROM digital_asset.deployments AS d
                         WHERE d.workspace_id = w.id
                         ORDER BY d.updated_at DESC
                         LIMIT 1
                       ) AS latest_deployment
                FROM digital_asset.workspaces AS w
                JOIN digital_asset.assets AS a ON a.id = w.asset_id
                WHERE w.workspace_key = :workspace_key
                  AND w.status = 'active'
                  AND a.status != 'archived'
                LIMIT 1
                """
                ),
                {"workspace_key": workspace_key.strip().lower()},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Hosted workspace not found")
    state = dict(row)
    deployment = state.get("latest_deployment")
    deployment = deployment if isinstance(deployment, dict) else None
    verified_application_url = (
        deployment.get("public_url")
        if deployment
        and deployment.get("status") == "ready"
        and deployment.get("health") == "healthy"
        else None
    )
    runtime_type = str((state.get("config") or {}).get("runtime_type") or "static")
    storage = _storage_profile(
        state.get("storage_bindings") if isinstance(state.get("storage_bindings"), list) else []
    )
    return _json_safe(
        {
            "ok": True,
            "tenant": {"slug": tenant["slug"], "name": tenant["name"]},
            "asset": {
                "asset_no": state["asset_no"],
                "name": state["asset_name"],
                "asset_kind": state["asset_kind"],
                "summary": state.get("asset_summary"),
            },
            "workspace": {
                "workspace_key": state["workspace_key"],
                "service_plan": state["service_plan"],
                "runtime_status": state["runtime_status"],
                "region": state["region"],
                "storage_quota_bytes": int(state["storage_quota_bytes"]),
                **_workspace_entry_fields(str(tenant["slug"]), state),
                "runtime_type": runtime_type,
                "storage_used_bytes": int(state.get("storage_used_bytes") or 0),
                "code_bytes": int(state.get("code_bytes") or 0),
                "source_archive_bytes": int(state.get("code_bytes") or 0),
                "runtime_bytes": int(state.get("runtime_bytes") or 0),
                "runtime_release_bytes": int(state.get("runtime_bytes") or 0),
                "data_bytes": int(state.get("data_bytes") or 0),
                "managed_data_object_bytes": int(state.get("data_bytes") or 0),
                "data_volume_bytes": int(state.get("data_volume_bytes") or 0),
                "database_bytes": int(state.get("database_bytes") or 0),
                "postgresql_bytes": int(state.get("database_bytes") or 0),
                "total_bytes": int(state.get("storage_used_bytes") or 0),
                "measured_at": state.get("usage_measured_at"),
                "database_medium": state.get("database_medium"),
                "storage": storage,
                "source_available": bool(state.get("source_available")),
                "source_version_count": int(state.get("source_version_count") or 0),
                "code_artifact_count": int(state.get("code_artifact_count") or 0),
                "code_storage_switchable": not bool(state.get("source_available")),
            },
            "deployment": deployment,
            "entry": {
                "url": workspace_entry_url(str(tenant["slug"]), workspace_key),
                "kind": (
                    "deployed_application" if verified_application_url else "workspace_status"
                ),
                "application_url": verified_application_url,
            },
            "verified_facts": {
                "permanent_entry_exists": True,
                "source_available": bool(state.get("source_available")),
                "application_deployed": bool(verified_application_url),
                "runtime_verified_ready": bool(verified_application_url),
            },
        }
    )


def resize_workspace_quota(
    actor: ActorContext,
    asset_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Increase a workspace's storage allocation by one audited 512 MiB unit."""

    _require_manage(actor)
    delta_mb = payload.get("delta_mb")
    target_mb = payload.get("target_mb")
    if (delta_mb in (None, "")) == (target_mb in (None, "")):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly one of delta_mb or target_mb",
        )
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref)
        workspace_ref = payload.get("workspace_ref") or payload.get("workspace")
        if workspace_ref not in (None, ""):
            workspace = _workspace_row(session, workspace_ref, lock=True)
            if workspace["asset_id"] != asset["id"]:
                raise HTTPException(
                    status_code=409,
                    detail="Workspace does not belong to the supplied asset",
                )
        else:
            selected = (
                session.execute(
                    text(
                        """
                    SELECT * FROM digital_asset.workspaces
                    WHERE asset_id = :asset_id AND status = 'active'
                    ORDER BY updated_at DESC
                    LIMIT 1
                    FOR UPDATE
                    """
                    ),
                    {"asset_id": asset["id"]},
                )
                .mappings()
                .one_or_none()
            )
            if selected is None:
                raise HTTPException(status_code=404, detail="Workspace not found")
            workspace = dict(selected)
        expected_revision = payload.get("expected_revision")
        if expected_revision not in (None, "") and int(expected_revision) != int(
            workspace["revision"]
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "revision_conflict",
                    "expected_revision": int(expected_revision),
                    "current_revision": int(workspace["revision"]),
                },
            )
        current_bytes = int(workspace["storage_quota_bytes"])
        current_mb = current_bytes // (1024 * 1024)
        if delta_mb not in (None, ""):
            if int(delta_mb) != WORKSPACE_QUOTA_STEP_MB:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "reason": "quota_increase_must_be_one_step",
                        "required_delta_mb": WORKSPACE_QUOTA_STEP_MB,
                    },
                )
            requested_bytes = current_bytes + WORKSPACE_QUOTA_STEP_BYTES
        else:
            requested_bytes = int(target_mb) * 1024 * 1024
            if requested_bytes != current_bytes + WORKSPACE_QUOTA_STEP_BYTES:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "reason": "quota_target_must_be_next_step",
                        "current_mb": current_mb,
                        "required_target_mb": current_mb + WORKSPACE_QUOTA_STEP_MB,
                    },
                )
        usage = _workspace_billable_usage(
            session,
            tenant_id=actor.tenant_id,
            workspace_id=workspace["id"],
            asset_id=asset["id"],
        )
        used_bytes = usage["total_bytes"]
        updated = dict(
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces
                    SET storage_quota_bytes = :quota,
                        revision = revision + 1
                    WHERE id = :workspace_id
                    RETURNING *
                    """
                ),
                {"quota": requested_bytes, "workspace_id": workspace["id"]},
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "digital_asset.workspace_quota_increased",
            {
                "asset_id": str(asset["id"]),
                "workspace_id": str(workspace["id"]),
                "workspace_key": workspace["workspace_key"],
                "before_bytes": current_bytes,
                "after_bytes": requested_bytes,
                "increase_bytes": WORKSPACE_QUOTA_STEP_BYTES,
                "used_bytes": used_bytes,
            },
        )
    return {
        "ok": True,
        "workspace": _public_workspace(updated, actor.tenant_slug),
        "quota": {
            "used_bytes": used_bytes,
            "before_bytes": current_bytes,
            "after_bytes": requested_bytes,
            "before_mb": current_mb,
            "after_mb": requested_bytes // (1024 * 1024),
            "increase_mb": WORKSPACE_QUOTA_STEP_MB,
            "next_increment_mb": WORKSPACE_QUOTA_STEP_MB,
        },
        "world_observation": _world_observation(
            operation="digital_asset.workspace.quota_increase",
            effect="update",
            primary=_world_entity(
                "digital_asset.workspace",
                updated,
                ref_field="workspace_key",
                facts={
                    "storage_quota_bytes": requested_bytes,
                    "storage_used_bytes": used_bytes,
                    "entry_url": workspace_entry_url(
                        actor.tenant_slug, str(updated["workspace_key"])
                    ),
                    "hosting_url": workspace_entry_url(
                        actor.tenant_slug, str(updated["workspace_key"])
                    ),
                },
            ),
            verified_facts={
                "quota_increased": True,
                "increase_bytes": WORKSPACE_QUOTA_STEP_BYTES,
                "storage_not_reduced": True,
            },
            affordances=[
                {
                    "capability": "digital_market_workspace_resize",
                    "meaning": "request one additional audited 512 MiB allocation",
                    "next_delta_mb": WORKSPACE_QUOTA_STEP_MB,
                }
            ],
        ),
    }


def switch_workspace_code_storage(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Switch an empty workspace's code binding between HDD and SSD.

    This is deliberately a metadata-only operation.  Once source versions or
    code artifacts exist, changing the binding would imply a physical move and
    integrity verification, so the direct switch is rejected and the Runtime
    must choose a migration capability instead.
    """

    _require_manage(actor)
    requested = str(payload.get("code_storage") or payload.get("storage") or "").strip().lower()
    if requested not in CODE_STORAGE_MEDIA:
        raise HTTPException(status_code=422, detail="code_storage must be hdd or ssd")

    expected_revision_raw = payload.get("expected_revision")
    expected_revision: int | None = None
    if expected_revision_raw not in (None, ""):
        try:
            expected_revision = int(expected_revision_raw)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=422, detail="expected_revision must be an integer"
            ) from exc

    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        asset = _asset_row(session, workspace["asset_id"])
        current_revision = int(workspace.get("revision") or 0)
        if expected_revision is not None and expected_revision != current_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "workspace_revision_changed",
                    "expected_revision": expected_revision,
                    "current_revision": current_revision,
                    "message": "Workspace changed; refresh its observed state before retrying",
                },
            )

        code_binding_row = (
            session.execute(
                text(
                    """
                SELECT id, workspace_id, binding_role, pool_key, provider_key,
                       object_prefix, storage_class, status, config
                FROM digital_asset.storage_bindings
                WHERE workspace_id = :workspace_id AND binding_role = 'code'
                FOR UPDATE
                """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        code_binding = dict(code_binding_row) if code_binding_row is not None else None
        binding_config = (
            code_binding.get("config")
            if code_binding is not None and isinstance(code_binding.get("config"), dict)
            else {}
        )
        current = str(
            binding_config.get("medium")
            or (
                "ssd"
                if code_binding is not None and code_binding.get("provider_key") == SSD_PROVIDER_KEY
                else (workspace.get("config") or {}).get("code_storage") or "hdd"
            )
        ).lower()

        source_state = dict(
            session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*)::integer
                       FROM digital_asset.asset_versions
                       WHERE asset_id = :asset_id) AS source_version_count,
                      (SELECT count(*)::integer
                       FROM digital_asset.artifacts
                       WHERE asset_id = :asset_id
                         AND storage_role = 'code') AS code_artifact_count
                    """
                ),
                {"asset_id": workspace["asset_id"]},
            )
            .mappings()
            .one()
        )
        source_version_count = int(source_state.get("source_version_count") or 0)
        code_artifact_count = int(source_state.get("code_artifact_count") or 0)

        if current == requested:
            storage = _storage_profile(_storage_binding_rows(session, workspace["id"]))
            public_workspace = _public_workspace(workspace, actor.tenant_slug)
            public_workspace["storage"] = storage
            public_workspace.update(
                {
                    "source_version_count": source_version_count,
                    "code_artifact_count": code_artifact_count,
                    "source_available": bool(source_version_count or code_artifact_count),
                    "code_storage_switchable": not (source_version_count or code_artifact_count),
                }
            )
            return {
                "ok": True,
                "changed": False,
                "workspace": _json_safe(public_workspace),
                "code_storage": {
                    "from": current,
                    "to": requested,
                    "physical_copy_required": False,
                },
                "next_action": "upload_source",
                "world_observation": _world_observation(
                    operation="digital_asset.workspace.code_storage_observe",
                    effect="none",
                    primary=_world_entity(
                        "digital_asset.workspace",
                        workspace,
                        ref_field="workspace_key",
                        facts={
                            "code_storage": requested,
                            "data_storage": "hdd",
                            "source_version_count": source_version_count,
                            "code_artifact_count": code_artifact_count,
                        },
                    ),
                    verified_facts={
                        "workspace_updated_in_place": True,
                        "binding_already_satisfied": True,
                        "physical_copy_performed": False,
                        "data_storage_unchanged": True,
                        "database_storage_unchanged": True,
                    },
                ),
            }

        if source_version_count or code_artifact_count:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "code_storage_migration_required",
                    "workspace": workspace["workspace_key"],
                    "current_code_storage": current,
                    "requested_code_storage": requested,
                    "source_version_count": source_version_count,
                    "code_artifact_count": code_artifact_count,
                    "direct_switch_allowed": False,
                    "message": (
                        "Existing source/code requires a verified migration; "
                        "the empty-workspace binding switch cannot move stored objects"
                    ),
                },
            )

        target_pool_key = SSD_POOL_KEY if requested == "ssd" else HDD_POOL_KEY
        target_pool_row = (
            session.execute(
                text(
                    """
                SELECT pool_key, provider_key, storage_class, medium, purpose,
                       status, enabled, policy
                FROM platform.storage_pools
                WHERE pool_key = :pool_key
                """
                ),
                {"pool_key": target_pool_key},
            )
            .mappings()
            .one_or_none()
        )
        if (
            target_pool_row is None
            or not bool(target_pool_row["enabled"])
            or str(target_pool_row["status"]) != "ready"
            or str(target_pool_row["medium"]) != requested
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "reason": "code_storage_pool_unavailable",
                    "requested_code_storage": requested,
                    "pool_key": target_pool_key,
                    "message": "The requested code storage pool is not ready",
                },
            )
        target_pool = dict(target_pool_row)
        policy = target_pool.get("policy") if isinstance(target_pool.get("policy"), dict) else {}
        allowed_roles = policy.get("allowed_roles")
        if isinstance(allowed_roles, list) and "code" not in allowed_roles:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "storage_pool_role_rejected",
                    "pool_key": target_pool_key,
                    "required_role": "code",
                },
            )

        next_workspace_config = dict(workspace.get("config") or {})
        next_workspace_config.update(
            {
                "code_storage": requested,
                "code_storage_selection": "explicit",
                "data_storage": "hdd",
            }
        )
        workspace = dict(
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces
                    SET config = CAST(:config AS jsonb),
                        revision = revision + 1
                    WHERE id = :workspace_id
                    RETURNING *
                    """
                ),
                {
                    "workspace_id": workspace["id"],
                    "config": json.dumps(next_workspace_config),
                },
            )
            .mappings()
            .one()
        )
        next_binding_config = dict(binding_config)
        next_binding_config.update(
            {
                "portable": True,
                "medium": requested,
                "selection": "explicit",
                "data_must_use_hdd": False,
            }
        )
        object_prefix = (
            str(code_binding.get("object_prefix"))
            if code_binding is not None and code_binding.get("object_prefix")
            else (f"tenants/{actor.tenant_id}/workspaces/{workspace['id']}/code/")
        )
        session.execute(
            text(
                """
                INSERT INTO digital_asset.storage_bindings(
                  id, tenant_id, workspace_id, provider_key, object_prefix,
                  binding_role, pool_key, storage_class, status, config
                ) VALUES (
                  :id, :tenant_id, :workspace_id, :provider_key, :object_prefix,
                  'code', :pool_key, :storage_class, 'ready', CAST(:config AS jsonb)
                )
                ON CONFLICT (tenant_id, workspace_id, binding_role)
                DO UPDATE SET
                  provider_key = EXCLUDED.provider_key,
                  pool_key = EXCLUDED.pool_key,
                  storage_class = EXCLUDED.storage_class,
                  status = 'ready',
                  config = EXCLUDED.config
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "workspace_id": workspace["id"],
                "provider_key": target_pool["provider_key"],
                "object_prefix": object_prefix,
                "pool_key": target_pool["pool_key"],
                "storage_class": target_pool["storage_class"],
                "config": json.dumps(next_binding_config),
            },
        )
        _audit(
            session,
            actor,
            "digital_asset.workspace_code_storage_switched",
            {
                "asset_id": str(workspace["asset_id"]),
                "workspace_id": str(workspace["id"]),
                "workspace_key": workspace["workspace_key"],
                "from": current,
                "to": requested,
                "source_version_count": 0,
                "code_artifact_count": 0,
                "physical_copy_performed": False,
                "data_storage": "hdd",
            },
        )
        storage = _storage_profile(_storage_binding_rows(session, workspace["id"]))

    public_workspace = _public_workspace(workspace, actor.tenant_slug)
    public_workspace["storage"] = storage
    public_workspace.update(
        {
            "source_version_count": 0,
            "code_artifact_count": 0,
            "source_available": False,
            "code_storage_switchable": True,
        }
    )
    return {
        "ok": True,
        "changed": True,
        "workspace": _json_safe(public_workspace),
        "code_storage": {
            "from": current,
            "to": requested,
            "physical_copy_required": False,
        },
        "next_action": "upload_source",
        "world_observation": _world_observation(
            operation="digital_asset.workspace.code_storage_switch",
            effect="update",
            primary=_world_entity(
                "digital_asset.workspace",
                workspace,
                ref_field="workspace_key",
                facts={
                    "asset_id": workspace["asset_id"],
                    "code_storage": requested,
                    "data_storage": "hdd",
                    "source_version_count": 0,
                    "code_artifact_count": 0,
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={"name": asset["name"], "asset_kind": asset["asset_kind"]},
                )
            ],
            verified_facts={
                "workspace_updated_in_place": True,
                "new_workspace_created": False,
                "source_uploaded": False,
                "physical_copy_performed": False,
                "code_binding_persisted": True,
                "data_storage_unchanged": True,
                "database_storage_unchanged": True,
            },
            affordances=[
                {
                    "capability": "digital_market_upload",
                    "meaning": "attach source to this same workspace using its new code binding",
                    "target": {
                        "asset": str(asset["asset_no"]),
                        "workspace": str(workspace["workspace_key"]),
                    },
                }
            ],
        ),
    }


def upgrade_workspace_runtime(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    """Upgrade a workspace from static hosting to a backend-capable runtime.

    The operation targets the stable workspace key directly, creates or updates
    the backend component, and then records a deployment request.  It never
    guesses a legacy asset id.
    """

    _require_manage(actor)
    runtime_type = str(payload.get("runtime_type") or payload.get("type") or "web").strip().lower()
    # Compatibility for proposals produced before the tool schema exposed an
    # enum. In the explicit "API hosting" flow the old model sometimes copied
    # the human-readable option label "web/api" as a literal value.
    if runtime_type in {"web/api", "api/web"}:
        runtime_type = "api"
    if runtime_type not in {"web", "api"}:
        raise HTTPException(
            status_code=422,
            detail="runtime_type must be web or api for a backend-capable workspace",
        )
    backend_runtime = str(
        payload.get("backend_runtime") or payload.get("runtime") or "python3.12"
    ).strip()[:120]
    if not backend_runtime:
        raise HTTPException(status_code=422, detail="backend_runtime is required")
    component_name = str(payload.get("component_name") or "api").strip().lower()
    if not WORKSPACE_KEY_RE.fullmatch(component_name):
        raise HTTPException(status_code=422, detail="Invalid component_name")

    source_version_id: UUID | None = None
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        asset = _asset_row(session, workspace["asset_id"])
        before_runtime_type = str((workspace.get("config") or {}).get("runtime_type") or "static")
        component = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.workspace_components(
                      id, tenant_id, workspace_id, component_name,
                      component_kind, runtime, entrypoint, build_command,
                      start_command, status, created_by
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :component_name,
                      'backend', :runtime, :entrypoint, :build_command,
                      :start_command, 'configured', :created_by
                    )
                    ON CONFLICT (tenant_id, workspace_id, component_name)
                    DO UPDATE SET
                      component_kind = 'backend',
                      runtime = EXCLUDED.runtime,
                      entrypoint = COALESCE(
                        EXCLUDED.entrypoint,
                        digital_asset.workspace_components.entrypoint
                      ),
                      build_command = COALESCE(
                        EXCLUDED.build_command,
                        digital_asset.workspace_components.build_command
                      ),
                      start_command = COALESCE(
                        EXCLUDED.start_command,
                        digital_asset.workspace_components.start_command
                      ),
                      status = 'configured'
                    RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "workspace_id": workspace["id"],
                    "component_name": component_name,
                    "runtime": backend_runtime,
                    "entrypoint": str(payload.get("entrypoint") or "").strip() or None,
                    "build_command": str(payload.get("build_command") or "").strip() or None,
                    "start_command": str(payload.get("start_command") or "").strip() or None,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        workspace = dict(
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces
                    SET config = jsonb_set(
                          COALESCE(config, '{}'::jsonb),
                          '{runtime_type}', to_jsonb(CAST(:runtime_type AS text)), true
                        ),
                        runtime_status = 'planned',
                        revision = revision + 1
                    WHERE id = :workspace_id
                    RETURNING *
                    """
                ),
                {"workspace_id": workspace["id"], "runtime_type": runtime_type},
            )
            .mappings()
            .one()
        )
        if payload.get("source_version_id") not in (None, ""):
            source_version_id = _uuid_or_none(payload.get("source_version_id"))
            if source_version_id is None:
                raise HTTPException(status_code=422, detail="Invalid source_version_id")
            source_exists = session.execute(
                text(
                    """
                    SELECT 1
                    FROM digital_asset.asset_versions
                    WHERE id = :version_id AND asset_id = :asset_id
                    """
                ),
                {"version_id": source_version_id, "asset_id": workspace["asset_id"]},
            ).scalar_one_or_none()
            if source_exists is None:
                raise HTTPException(
                    status_code=409,
                    detail="Source version does not belong to this workspace asset",
                )
        else:
            source_version_id = session.execute(
                text(
                    """
                    SELECT id
                    FROM digital_asset.asset_versions
                    WHERE asset_id = :asset_id
                    ORDER BY created_at DESC, id
                    LIMIT 1
                    """
                ),
                {"asset_id": workspace["asset_id"]},
            ).scalar_one_or_none()
        _audit(
            session,
            actor,
            "digital_asset.workspace_runtime_upgraded",
            {
                "asset_id": str(workspace["asset_id"]),
                "workspace_id": str(workspace["id"]),
                "workspace_key": workspace["workspace_key"],
                "from_runtime_type": before_runtime_type,
                "to_runtime_type": runtime_type,
                "component_id": str(component["id"]),
                "backend_runtime": backend_runtime,
            },
        )

    deployment = None
    if source_version_id is not None:
        deployment = create_deployment(
            actor,
            workspace["asset_id"],
            {
                "workspace_key": workspace["workspace_key"],
                "component_name": component_name,
                "deploy_type": "api",
                "runtime_type": runtime_type,
                "runtime": backend_runtime,
                "source_version_id": source_version_id,
                "public_url": payload.get("public_url"),
                "entrypoint": payload.get("entrypoint"),
                "build_command": payload.get("build_command"),
                "start_command": payload.get("start_command"),
                "notes": payload.get("notes"),
            },
        )["deployment"]
    with tenant_session(actor.tenant_id) as session:
        refreshed = _workspace_row(session, workspace["id"])
    return {
        "ok": True,
        "workspace": _public_workspace(refreshed, actor.tenant_slug),
        "component": _json_safe(dict(component)),
        "deployment": deployment,
        "runtime_upgrade": {
            "from": before_runtime_type,
            "to": runtime_type,
            "backend_runtime": backend_runtime,
            "deployment_request_created": deployment is not None,
            "actual_runtime_ready": bool(
                deployment
                and deployment.get("status") == "ready"
                and deployment.get("health") == "healthy"
            ),
        },
        "next_action": (
            "runtime_worker_claim" if deployment is not None else "upload_source_and_create_version"
        ),
        "world_observation": _world_observation(
            operation="digital_asset.workspace.runtime_configure",
            effect="update",
            primary=_world_entity(
                "digital_asset.workspace",
                refreshed,
                ref_field="workspace_key",
                facts={
                    "asset_id": refreshed["asset_id"],
                    "runtime_type": (refreshed.get("config") or {}).get("runtime_type"),
                    "runtime_status": refreshed.get("runtime_status"),
                    "public_url": refreshed.get("public_url"),
                    "entry_url": workspace_entry_url(
                        actor.tenant_slug, str(refreshed["workspace_key"])
                    ),
                    "hosting_url": workspace_entry_url(
                        actor.tenant_slug, str(refreshed["workspace_key"])
                    ),
                    "storage_quota_bytes": refreshed.get("storage_quota_bytes"),
                },
            ),
            related=[
                _world_entity(
                    "digital_asset.asset",
                    asset,
                    ref_field="asset_no",
                    facts={
                        "name": asset["name"],
                        "asset_kind": asset["asset_kind"],
                    },
                ),
                _world_entity(
                    "digital_asset.component",
                    dict(component),
                    ref_field="component_name",
                    facts={
                        "workspace_id": component["workspace_id"],
                        "component_kind": component["component_kind"],
                        "runtime": component["runtime"],
                        "entrypoint": component.get("entrypoint"),
                        "source_version_id": component.get("source_version_id"),
                    },
                ),
            ],
            verified_facts={
                "workspace_updated_in_place": True,
                "new_workspace_created": False,
                "runtime_configuration_persisted": True,
                "source_version_resolved": source_version_id is not None,
                "deployment_request_exists": deployment is not None,
                "runtime_verified_ready": bool(
                    deployment
                    and deployment.get("status") == "ready"
                    and deployment.get("health") == "healthy"
                ),
                "permanent_entry_reserved": True,
                "application_deployed": bool(
                    deployment
                    and deployment.get("status") == "ready"
                    and deployment.get("health") == "healthy"
                ),
            },
            uncertainties=(
                []
                if source_version_id is not None
                else [
                    {
                        "fact": "deployable_source_version",
                        "state": "not_observed",
                        "meaning": "no source version is currently linked to this asset",
                    }
                ]
            ),
            affordances=[
                {
                    "capability": "digital_market_upload",
                    "meaning": (
                        "attach source or another artifact to the same observed asset/workspace"
                    ),
                    "target": {
                        "asset": str(asset["asset_no"]),
                        "workspace": str(refreshed["workspace_key"]),
                    },
                },
                {
                    "capability": "digital_market_deploy",
                    "meaning": "request a deployment when sufficient source evidence exists",
                    "target": {
                        "asset": str(asset["asset_no"]),
                        "workspace": str(refreshed["workspace_key"]),
                    },
                },
                {
                    "capability": "generic_data_mutate",
                    "meaning": "audited fallback for direct workspace configuration fields only",
                    "cannot_assert": [
                        "runtime_status",
                        "deployment readiness",
                        "runtime health",
                    ],
                },
            ],
        ),
    }


def provision_database(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_manage(actor)
    requested_provider, database_url, make_default = _database_provider_request(payload)
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        logical_name = re.sub(
            r"[^a-z0-9_]+",
            "_",
            str(payload.get("logical_name") or payload.get("database_name") or "app").lower(),
        ).strip("_")[:63]
        if not logical_name or not logical_name[0].isalpha():
            raise HTTPException(status_code=422, detail="Invalid logical_name")
        database = _provision_database(
            session,
            actor=actor,
            workspace=workspace,
            logical_name=logical_name,
            isolation_mode=str(payload.get("isolation_mode") or "workspace_rls"),
            requested_provider=requested_provider,
            database_url=database_url,
            make_default=make_default,
        )
        _audit(
            session,
            actor,
            "digital_asset.database_provisioned",
            {
                "workspace_id": str(workspace["id"]),
                "database_id": database["id"],
                "provider_key": database["provider_key"],
                "isolation_mode": database["isolation_mode"],
            },
        )
    return {"ok": True, "database": database}


def _database_binding(
    session: Session, workspace_id: UUID, logical_name: str | None = None
) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT *
                FROM digital_asset.database_bindings
                WHERE workspace_id = :workspace_id
                  AND (
                    CAST(:logical_name AS text) IS NULL
                    OR logical_name = CAST(:logical_name AS text)
                  )
                ORDER BY is_default DESC, created_at
                LIMIT 1
                """
            ),
            {"workspace_id": workspace_id, "logical_name": logical_name},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace database not found")
    if row["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Workspace database is {row['status']}",
        )
    return dict(row)


def migrate_workspace_database_to_hdd(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    """Move one workspace Data API database in place without changing its API."""

    _require_manage(actor)
    payload = payload or {}
    logical_name = str(payload.get("logical_name") or "").strip() or None
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        database = _database_binding(session, workspace["id"], logical_name)
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            return {
                "ok": True,
                "migrated": False,
                "idempotent_replay": True,
                "workspace": _public_workspace(workspace, actor.tenant_slug),
                "database": _json_safe(database),
            }
        if database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "customer_managed_database_cannot_migrate_to_hdd_in_place",
                    "next_action": "create a new managed binding and migrate data explicitly",
                },
            )
        try:
            migrated = hosted_database.migrate_binding(session, database)
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "hosted_database_unavailable", "message": str(exc)},
            ) from exc
        _audit(
            session,
            actor,
            "digital_asset.database_migrated_to_hdd",
            {
                "workspace_id": str(workspace["id"]),
                "database_id": str(migrated["id"]),
                "provider_key": migrated["provider_key"],
                "physical_medium": migrated["physical_medium"],
                "actual_size_bytes": migrated["actual_size_bytes"],
            },
        )
    return {
        "ok": True,
        "migrated": True,
        "workspace": _public_workspace(workspace, actor.tenant_slug),
        "database": _json_safe(migrated),
        "verified": {
            "api_contract_unchanged": True,
            "physical_medium": "hdd",
            "legacy_rows_retained_for_rollback": True,
        },
    }


def migrate_tenant_databases_to_hdd(tenant_id: UUID) -> dict[str, object]:
    """Operator entry point used after both blue/green slots understand HDD bindings."""

    with tenant_session(tenant_id) as session:
        binding_ids = list(
            session.execute(
                text(
                    """
                    SELECT id FROM digital_asset.database_bindings
                    WHERE provider_key = :legacy_provider
                    ORDER BY created_at
                    """
                ),
                {"legacy_provider": hosted_database.LEGACY_DATABASE_PROVIDER_KEY},
            ).scalars()
        )
    migrated: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for binding_id in binding_ids:
        try:
            with tenant_session(tenant_id) as session:
                row = (
                    session.execute(
                        text(
                            """
                        SELECT * FROM digital_asset.database_bindings
                        WHERE id = :id FOR UPDATE
                        """
                        ),
                        {"id": binding_id},
                    )
                    .mappings()
                    .one()
                )
                updated = hosted_database.migrate_binding(session, dict(row))
                _audit(
                    session,
                    None,
                    "digital_asset.database_migrated_to_hdd",
                    {
                        "workspace_id": str(updated["workspace_id"]),
                        "database_id": str(updated["id"]),
                        "operator": "deployment_manager",
                        "actual_size_bytes": updated["actual_size_bytes"],
                    },
                    tenant_id=tenant_id,
                )
                migrated.append(
                    {
                        "database_id": str(updated["id"]),
                        "workspace_id": str(updated["workspace_id"]),
                        "actual_size_bytes": int(updated["actual_size_bytes"]),
                    }
                )
        except Exception as exc:  # continue so one damaged legacy binding is observable
            failures.append(
                {
                    "database_id": str(binding_id),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "tenant_id": str(tenant_id),
        "migrated": migrated,
        "failures": failures,
        "ok": not failures,
    }


def database_schema(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    logical_name: str | None = None,
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        database = _database_binding(session, workspace["id"], logical_name)
        tables: list[dict[str, object]] = []
        provider_key = str(database["provider_key"])
        if provider_key == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            try:
                collections, database_bytes = hosted_database.schema(session, database)
                tables = hosted_database.relational_schema(session, database)
            except (hosted_database.HostedDatabaseUnavailable, psycopg.Error) as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "reason": "hosted_database_unavailable",
                        "message": f"PostgreSQL schema inspection failed: {type(exc).__name__}",
                    },
                ) from exc
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_bindings
                    SET actual_size_bytes = :size, size_measured_at = now()
                    WHERE id = :id
                    """
                ),
                {"size": database_bytes, "id": database["id"]},
            )
            database["actual_size_bytes"] = database_bytes
            hosted_database.update_usage(session, database, database_bytes=database_bytes)
        elif provider_key == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            collections = []
            try:
                tables = hosted_database.relational_schema(session, database)
            except (hosted_database.HostedDatabaseUnavailable, psycopg.Error) as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "reason": "external_database_unavailable",
                        "message": f"PostgreSQL schema inspection failed: {type(exc).__name__}",
                    },
                ) from exc
        else:
            collections = [
                _json_safe(dict(row))
                for row in session.execute(
                    text(
                        """
                        SELECT collection_name AS name,
                               count(*)::integer AS records,
                               max(updated_at) AS updated_at
                        FROM digital_asset.workspace_records
                        WHERE workspace_id = :workspace_id
                          AND database_binding_id = :database_id
                        GROUP BY collection_name
                        ORDER BY collection_name
                        """
                    ),
                    {"workspace_id": workspace["id"], "database_id": database["id"]},
                )
                .mappings()
                .all()
            ]
    return {
        "ok": True,
        "database": _json_safe(database),
        "collections": collections,
        "tables": _json_safe(tables),
    }


def database_health(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    logical_name: str | None = None,
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        database = _database_binding(session, workspace["id"], logical_name)
        if str(database["provider_key"]) not in hosted_database.POSTGRESQL_PROVIDER_KEYS:
            return {
                "ok": True,
                "database": _json_safe(database),
                "health": {
                    "reachable": True,
                    "provider_key": database["provider_key"],
                    "connection_kind": "control_plane_collection_api",
                    "credentials_exposed": False,
                },
            }
        try:
            health = hosted_database.binding_health(session, database)
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "workspace_database_unavailable", "message": str(exc)},
            ) from exc
    return {"ok": True, "database": _json_safe(database), "health": _json_safe(health)}


def list_workspace_relation_rows(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    schema_name: str,
    table_name: str,
    logical_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        database = _database_binding(session, workspace["id"], logical_name)
        if str(database["provider_key"]) not in hosted_database.POSTGRESQL_PROVIDER_KEYS:
            raise HTTPException(
                status_code=409,
                detail="Relational Data API requires a PostgreSQL provider binding",
            )
        try:
            table, rows = hosted_database.list_relation_rows(
                session,
                database,
                schema_name=schema_name,
                table_name=table_name,
                limit=max(1, min(int(limit), 1000)),
                offset=max(0, int(offset)),
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except psycopg.Error as exc:
            raise HTTPException(
                status_code=422,
                detail=f"PostgreSQL rejected relational query: {type(exc).__name__}",
            ) from exc
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "workspace_database_unavailable", "message": str(exc)},
            ) from exc
    return {
        "ok": True,
        "database": database["logical_name"],
        "table": _json_safe(table),
        "rows": _json_safe(rows),
        "items": _json_safe(rows),
        "count": len(rows),
        "next_offset": offset + len(rows) if len(rows) == min(limit, 1000) else None,
    }


def put_workspace_relation_row(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    schema_name: str,
    table_name: str,
    record_key: str,
    payload: dict[str, object],
    expected_version: str | None = None,
    credential: WorkspaceCredential | None = None,
    actor: ActorContext | None = None,
    logical_name: str | None = None,
) -> dict[str, object]:
    if not record_key.strip() or len(record_key.strip()) > 512:
        raise HTTPException(status_code=422, detail="Invalid relational row key")
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        if credential is not None and credential.workspace_id != workspace["id"]:
            raise HTTPException(status_code=403, detail="Workspace key scope mismatch")
        database = _database_binding(session, workspace["id"], logical_name)
        if str(database["provider_key"]) not in hosted_database.POSTGRESQL_PROVIDER_KEYS:
            raise HTTPException(
                status_code=409,
                detail="Relational Data API requires a PostgreSQL provider binding",
            )
        quota_bytes: int | None = None
        non_database_bytes = 0
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            usage = _workspace_billable_usage(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace["id"],
                asset_id=workspace["asset_id"],
            )
            non_database_bytes = max(
                0, usage["total_bytes"] - int(database.get("actual_size_bytes") or 0)
            )
            quota_bytes = int(workspace["storage_quota_bytes"])
        try:
            result = hosted_database.put_relation_row(
                session,
                database,
                schema_name=schema_name,
                table_name=table_name,
                record_key=record_key.strip(),
                payload=payload,
                expected_version=expected_version,
                quota_bytes=quota_bytes,
                non_database_bytes=non_database_bytes,
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except OverflowError as exc:
            try:
                detail = json.loads(str(exc))
            except json.JSONDecodeError:
                detail = {"reason": "workspace_quota_exceeded"}
            raise HTTPException(status_code=507, detail=detail) from exc
        except ValueError as exc:
            try:
                conflict = json.loads(str(exc))
            except json.JSONDecodeError:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            if conflict.get("reason") != "version_conflict":
                raise HTTPException(status_code=422, detail=str(exc)) from exc
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "Row version conflict",
                    "expected": conflict.get("expected"),
                    "current": conflict.get("current"),
                },
            ) from exc
        except psycopg.Error as exc:
            raise HTTPException(
                status_code=422,
                detail=f"PostgreSQL rejected relational row mutation: {type(exc).__name__}",
            ) from exc
        except hosted_database.HostedDatabaseUnavailable as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"reason": "workspace_database_unavailable", "message": str(exc)},
            ) from exc
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_bindings
                    SET actual_size_bytes=:size,size_measured_at=now()
                    WHERE id=:id
                    """
                ),
                {"size": result.database_bytes, "id": database["id"]},
            )
            hosted_database.update_usage(
                session,
                database,
                database_bytes=result.database_bytes,
            )
        _audit(
            session,
            actor,
            "digital_asset.database_row_put",
            {
                "workspace_id": str(workspace["id"]),
                "database_id": str(database["id"]),
                "schema": schema_name,
                "table": table_name,
                "record_key": record_key.strip(),
                "version": result.record["version"],
                "credential_id": str(credential.credential_id) if credential else None,
            },
            tenant_id=tenant_id,
        )
    return {"ok": True, "record": _json_safe(result.record)}


def list_workspace_records(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    collection: str,
    logical_name: str | None = None,
    limit: int = 100,
    offset: int = 0,
    owner_id: str | None = None,
) -> dict[str, object]:
    if not COLLECTION_RE.fullmatch(collection):
        raise HTTPException(status_code=422, detail="Invalid collection")
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        database = _database_binding(session, workspace["id"], logical_name)
        bounded_limit = max(1, min(int(limit), 1000))
        bounded_offset = max(0, int(offset))
        if database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "collection_api_not_supported_by_external_database",
                    "next_action": "use the relational table Data API",
                },
            )
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            try:
                rows, database_bytes = hosted_database.list_records(
                    session,
                    database,
                    collection=collection,
                    limit=bounded_limit,
                    offset=bounded_offset,
                    owner_id=owner_id,
                )
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"reason": "hosted_database_unavailable", "message": str(exc)},
                ) from exc
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_bindings
                    SET actual_size_bytes = :size, size_measured_at = now()
                    WHERE id = :id
                    """
                ),
                {"size": database_bytes, "id": database["id"]},
            )
            hosted_database.update_usage(session, database, database_bytes=database_bytes)
        else:
            rows = [
                dict(row)
                for row in session.execute(
                    text(
                        """
                        SELECT record_key, payload, version, created_at, updated_at
                        FROM digital_asset.workspace_records
                        WHERE workspace_id = :workspace_id
                          AND database_binding_id = :database_id
                          AND collection_name = :collection
                          AND (
                            CAST(:owner_id AS text) IS NULL
                            OR payload->>'owner_id' = CAST(:owner_id AS text)
                          )
                        ORDER BY updated_at DESC, record_key
                        LIMIT :limit OFFSET :offset
                        """
                    ),
                    {
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "limit": bounded_limit,
                        "offset": bounded_offset,
                        "owner_id": owner_id,
                    },
                )
                .mappings()
                .all()
            ]
    records = [
        _json_safe(
            {
                "key": row["record_key"],
                "data": row["payload"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )
        for row in rows
    ]
    return {
        "ok": True,
        "collection": collection,
        "records": records,
        "items": records,
        "count": len(records),
        "next_offset": offset + len(records) if len(records) == min(limit, 1000) else None,
    }


def get_workspace_record(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    collection: str,
    record_key: str,
    logical_name: str | None = None,
    owner_id: str | None = None,
) -> dict[str, object]:
    if not COLLECTION_RE.fullmatch(collection):
        raise HTTPException(status_code=422, detail="Invalid collection")
    clean_key = record_key.strip()
    if not clean_key or len(clean_key) > 240:
        raise HTTPException(status_code=422, detail="Invalid record key")
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        database = _database_binding(session, workspace["id"], logical_name)
        if database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "collection_api_not_supported_by_external_database",
                    "next_action": "use the relational table Data API",
                },
            )
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            try:
                row = hosted_database.get_record(
                    session,
                    database,
                    collection=collection,
                    record_key=clean_key,
                    owner_id=owner_id,
                )
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"reason": "hosted_database_unavailable", "message": str(exc)},
                ) from exc
        else:
            row = (
                session.execute(
                    text(
                        """
                        SELECT record_key, payload, version, created_at, updated_at
                        FROM digital_asset.workspace_records
                        WHERE workspace_id=:workspace_id
                          AND database_binding_id=:database_id
                          AND collection_name=:collection
                          AND record_key=:record_key
                          AND (
                            CAST(:owner_id AS text) IS NULL
                            OR payload->>'owner_id'=CAST(:owner_id AS text)
                          )
                        """
                    ),
                    {
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "record_key": clean_key,
                        "owner_id": owner_id,
                    },
                )
                .mappings()
                .one_or_none()
            )
            row = dict(row) if row is not None else None
    if row is None:
        raise HTTPException(status_code=404, detail="Record not found")
    return {
        "ok": True,
        "record": _json_safe(
            {
                "key": row["record_key"],
                "data": row["payload"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        ),
    }


def put_workspace_record(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    collection: str,
    record_key: str,
    payload: dict[str, object],
    expected_version: int | None = None,
    credential: WorkspaceCredential | None = None,
    actor: ActorContext | None = None,
    logical_name: str | None = None,
    owner_id: str | None = None,
) -> dict[str, object]:
    if not COLLECTION_RE.fullmatch(collection):
        raise HTTPException(status_code=422, detail="Invalid collection")
    if not record_key.strip() or len(record_key.strip()) > 240:
        raise HTTPException(status_code=422, detail="Invalid record key")
    if owner_id is not None:
        requested_owner = payload.get("owner_id")
        if requested_owner is not None and str(requested_owner) != owner_id:
            raise HTTPException(status_code=403, detail="Record owner_id cannot be reassigned")
        payload = {**payload, "owner_id": owner_id}
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        if credential is not None and credential.workspace_id != workspace["id"]:
            raise HTTPException(status_code=403, detail="Workspace key scope mismatch")
        database = _database_binding(session, workspace["id"], logical_name)
        if database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "collection_api_not_supported_by_external_database",
                    "next_action": "use the relational table Data API",
                },
            )
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            usage = _workspace_billable_usage(
                session,
                tenant_id=tenant_id,
                workspace_id=workspace["id"],
                asset_id=workspace["asset_id"],
            )
            non_database_bytes = max(
                0, usage["total_bytes"] - int(database.get("actual_size_bytes") or 0)
            )
            try:
                hosted_result = hosted_database.put_record(
                    session,
                    database,
                    workspace_id=workspace["id"],
                    collection=collection,
                    record_key=record_key.strip(),
                    payload=payload,
                    expected_version=expected_version,
                    quota_bytes=int(workspace["storage_quota_bytes"]),
                    non_database_bytes=non_database_bytes,
                    owner_id=owner_id,
                )
            except OverflowError as exc:
                try:
                    detail = json.loads(str(exc))
                except json.JSONDecodeError:
                    detail = {"reason": "workspace_quota_exceeded"}
                raise HTTPException(status_code=507, detail=detail) from exc
            except ValueError as exc:
                try:
                    conflict = json.loads(str(exc))
                except json.JSONDecodeError:
                    conflict = {"reason": "version_conflict"}
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Record version conflict",
                        "expected": conflict.get("expected"),
                        "current": conflict.get("current"),
                    },
                ) from exc
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"reason": "hosted_database_unavailable", "message": str(exc)},
                ) from exc
            row = hosted_result.record
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_bindings
                    SET actual_size_bytes = :size, size_measured_at = now()
                    WHERE id = :id
                    """
                ),
                {"size": hosted_result.database_bytes, "id": database["id"]},
            )
            hosted_database.update_usage(
                session, database, database_bytes=hosted_result.database_bytes
            )
        else:
            current = (
                session.execute(
                    text(
                        """
                        SELECT version, payload
                        FROM digital_asset.workspace_records
                        WHERE workspace_id = :workspace_id
                          AND database_binding_id = :database_id
                          AND collection_name = :collection
                          AND record_key = :record_key
                        FOR UPDATE
                        """
                    ),
                    {
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "record_key": record_key.strip(),
                    },
                )
                .mappings()
                .one_or_none()
            )
            current_version = int(current["version"]) if current is not None else 0
            if (
                owner_id is not None
                and current is not None
                and str(current["payload"].get("owner_id") or "") != owner_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Record belongs to another browser principal",
                )
            if expected_version is not None and expected_version != current_version:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": "Record version conflict",
                        "expected": expected_version,
                        "current": current_version,
                    },
                )
            row = (
                session.execute(
                    text(
                        """
                        INSERT INTO digital_asset.workspace_records(
                          id, tenant_id, workspace_id, database_binding_id,
                          collection_name, record_key, payload
                        ) VALUES (
                          :id, :tenant_id, :workspace_id, :database_id,
                          :collection, :record_key, CAST(:payload AS jsonb)
                        )
                        ON CONFLICT (
                          tenant_id, workspace_id, database_binding_id,
                          collection_name, record_key
                        )
                        DO UPDATE SET
                          payload = EXCLUDED.payload,
                          version = digital_asset.workspace_records.version + 1
                        RETURNING record_key, payload, version, created_at, updated_at
                        """
                    ),
                    {
                        "id": uuid4(),
                        "tenant_id": tenant_id,
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "record_key": record_key.strip(),
                        "payload": json.dumps(payload, ensure_ascii=False, default=str),
                    },
                )
                .mappings()
                .one()
            )
        _audit(
            session,
            actor,
            "digital_asset.data_record_upserted",
            {
                "workspace_id": str(workspace["id"]),
                "collection": collection,
                "record_key": record_key.strip(),
                "version": row["version"],
                "credential_id": (
                    str(credential.credential_id) if credential is not None else None
                ),
            },
            tenant_id=tenant_id,
        )
    return {
        "ok": True,
        "record": _json_safe(
            {
                "key": row["record_key"],
                "data": row["payload"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        ),
    }


def delete_workspace_record(
    *,
    tenant_id: UUID,
    workspace_ref: object,
    collection: str,
    record_key: str,
    logical_name: str | None = None,
    owner_id: str | None = None,
) -> dict[str, object]:
    if not COLLECTION_RE.fullmatch(collection):
        raise HTTPException(status_code=422, detail="Invalid collection")
    clean_key = record_key.strip()
    if not clean_key or len(clean_key) > 240:
        raise HTTPException(status_code=422, detail="Invalid record key")
    with tenant_session(tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        database = _database_binding(session, workspace["id"], logical_name)
        if database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "collection_api_not_supported_by_external_database",
                    "next_action": "use the relational table Data API",
                },
            )
        if database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY:
            try:
                deleted = hosted_database.delete_record(
                    session,
                    database,
                    collection=collection,
                    record_key=clean_key,
                    owner_id=owner_id,
                )
            except PermissionError as exc:
                raise HTTPException(status_code=403, detail=str(exc)) from exc
            except hosted_database.HostedDatabaseUnavailable as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={"reason": "hosted_database_unavailable", "message": str(exc)},
                ) from exc
            if deleted is not None:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.database_bindings
                        SET actual_size_bytes=:size,size_measured_at=now()
                        WHERE id=:id
                        """
                    ),
                    {"size": deleted.database_bytes, "id": database["id"]},
                )
                hosted_database.update_usage(
                    session,
                    database,
                    database_bytes=deleted.database_bytes,
                )
                row = deleted.record
            else:
                row = None
        else:
            current = (
                session.execute(
                    text(
                        """
                        SELECT record_key,payload,version,created_at,updated_at
                        FROM digital_asset.workspace_records
                        WHERE workspace_id=:workspace_id
                          AND database_binding_id=:database_id
                          AND collection_name=:collection AND record_key=:record_key
                        FOR UPDATE
                        """
                    ),
                    {
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "record_key": clean_key,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if (
                current is not None
                and owner_id is not None
                and str(current["payload"].get("owner_id") or "") != owner_id
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Record belongs to another browser principal",
                )
            if current is not None:
                session.execute(
                    text(
                        """
                        DELETE FROM digital_asset.workspace_records
                        WHERE workspace_id=:workspace_id
                          AND database_binding_id=:database_id
                          AND collection_name=:collection AND record_key=:record_key
                        """
                    ),
                    {
                        "workspace_id": workspace["id"],
                        "database_id": database["id"],
                        "collection": collection,
                        "record_key": clean_key,
                    },
                )
                row = dict(current)
            else:
                row = None
    return {"ok": True, "deleted": row is not None, "key": clean_key}


def create_deployment(
    actor: ActorContext, asset_ref: object, payload: dict[str, object]
) -> dict[str, object]:
    _require_manage(actor)
    with tenant_session(actor.tenant_id) as session:
        asset = _asset_row(session, asset_ref, lock=True)
        workspace: dict[str, object] | None = None
        if payload.get("workspace_id") or payload.get("workspace_key"):
            workspace = _workspace_row(
                session,
                payload.get("workspace_id") or payload.get("workspace_key"),
                lock=True,
            )
            if workspace["asset_id"] != asset["id"]:
                raise HTTPException(status_code=409, detail="Workspace belongs to another asset")
        if workspace is None:
            row = (
                session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.workspaces
                        WHERE asset_id = :asset_id AND status = 'active'
                        ORDER BY updated_at DESC
                        LIMIT 1
                        FOR UPDATE
                        """
                    ),
                    {"asset_id": asset["id"]},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise HTTPException(
                    status_code=409,
                    detail="Create a workspace before requesting a deployment",
                )
            workspace = dict(row)
        source_version_id = None
        source_digest = None
        if payload.get("source_version_id") not in (None, ""):
            source_version_id = _uuid_or_none(payload.get("source_version_id"))
            if source_version_id is None:
                raise HTTPException(status_code=422, detail="Invalid source_version_id")
            source_exists = session.execute(
                text(
                    """
                    SELECT 1
                    FROM digital_asset.asset_versions
                    WHERE id = :version_id AND asset_id = :asset_id
                    """
                ),
                {"version_id": source_version_id, "asset_id": asset["id"]},
            ).scalar_one_or_none()
            if source_exists is None:
                raise HTTPException(
                    status_code=409,
                    detail="Source version does not belong to this digital asset",
                )
            source_digest = session.execute(
                text(
                    """
                    SELECT ar.sha256
                    FROM digital_asset.artifacts AS ar
                    WHERE ar.version_id=:version_id AND ar.asset_id=:asset_id
                      AND ar.storage_role='code' AND ar.state='verified'
                    ORDER BY ar.created_at DESC LIMIT 1
                    """
                ),
                {"version_id": source_version_id, "asset_id": asset["id"]},
            ).scalar_one_or_none()
        component_name = str(payload.get("component_name") or "").strip()
        component_kind = str(
            payload.get("deploy_type") or payload.get("component_kind") or ""
        ).strip()
        component = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.workspace_components
                    WHERE workspace_id = :workspace_id
                      AND (
                        CAST(:component_name AS text) = ''
                        OR component_name = CAST(:component_name AS text)
                      )
                      AND (
                        CAST(:component_kind AS text) = ''
                        OR component_kind = CAST(:component_kind AS text)
                        OR (
                          CAST(:component_kind AS text) IN ('web', 'api')
                          AND component_kind = 'backend'
                        )
                      )
                    ORDER BY
                      CASE component_kind WHEN 'backend' THEN 0 WHEN 'frontend' THEN 1 ELSE 2 END,
                      component_name
                    LIMIT 1
                    """
                ),
                {
                    "workspace_id": workspace["id"],
                    "component_name": component_name,
                    "component_kind": component_kind,
                },
            )
            .mappings()
            .one_or_none()
        )
        if component is None:
            raise HTTPException(status_code=409, detail="Workspace component not found")
        runtime_profile_key = None
        if source_digest:
            runtime_name = str(component.get("runtime") or "static").lower()
            runtime_family = (
                "python"
                if runtime_name.startswith("python")
                else "node"
                if runtime_name.startswith("node")
                else "static"
            )
            runtime_profile_key = session.execute(
                text(
                    """
                    SELECT profile_key FROM platform.runtime_profiles
                    WHERE runtime_family=:family AND enabled
                    ORDER BY revision DESC, profile_key LIMIT 1
                    """
                ),
                {"family": runtime_family},
            ).scalar_one_or_none()
        revision = int(
            session.execute(
                text(
                    """
                    SELECT COALESCE(max(revision), 0) + 1
                    FROM digital_asset.deployments
                    WHERE workspace_id = :workspace_id
                      AND component_id = :component_id
                    """
                ),
                {"workspace_id": workspace["id"], "component_id": component["id"]},
            ).scalar_one()
        )
        deployment_id = uuid4()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.deployments(
                      id, tenant_id, workspace_id, component_id, source_version_id,
                      revision, provider_key, status, health, public_url,
                      requested_config, requested_by, release_digest,
                      runtime_profile_key
                    ) VALUES (
                      :id, :tenant_id, :workspace_id, :component_id,
                      :source_version_id, :revision, 'runtime_queue', 'queued',
                      'pending', :public_url, CAST(:requested_config AS jsonb),
                      :requested_by, :release_digest, :runtime_profile_key
                    )
                    RETURNING *
                    """
                ),
                {
                    "id": deployment_id,
                    "tenant_id": actor.tenant_id,
                    "workspace_id": workspace["id"],
                    "component_id": component["id"],
                    "source_version_id": source_version_id,
                    "revision": revision,
                    "public_url": payload.get("public_url")
                    or workspace.get("public_url")
                    or workspace_entry_url(
                        actor.tenant_slug,
                        str(workspace["workspace_key"]),
                    ),
                    "requested_config": json.dumps(payload, ensure_ascii=False, default=str),
                    "requested_by": actor.user_id,
                    "release_digest": source_digest,
                    "runtime_profile_key": runtime_profile_key,
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
                ) VALUES (
                  :deployment_id, :tenant_id, 1, 'requested',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "deployment_id": deployment_id,
                "tenant_id": actor.tenant_id,
                "payload": json.dumps(
                    {
                        "component": component["component_name"],
                        "runtime": component["runtime"],
                        "provider": "runtime_queue",
                    }
                ),
            },
        )
        session.execute(
            text(
                """
                UPDATE digital_asset.workspaces
                SET runtime_status = 'building'
                WHERE id = :workspace_id
                """
            ),
            {"workspace_id": workspace["id"]},
        )
        _audit(
            session,
            actor,
            "digital_asset.deployment_requested",
            {
                "asset_id": str(asset["id"]),
                "workspace_id": str(workspace["id"]),
                "deployment_id": str(deployment_id),
                "revision": revision,
                "provider": "runtime_queue",
            },
        )
    deployment = _public_deployment(dict(row))
    deployment["next_action"] = "runtime_worker_claim"
    return {"ok": True, "deployment": deployment}


def issue_workspace_key(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
    *,
    signing_secret: str,
    key_kind: str = "delegated",
    rotate_primary: bool = False,
) -> dict[str, object]:
    """Issue one workspace credential without exposing any existing secret.

    ``key_kind`` is deliberately an internal argument instead of a request-body
    field.  The public delegated-key endpoint therefore cannot be turned into a
    primary-key issuer by adding JSON fields.  Primary creation is used by the
    composite provision flow; later replacement goes through the dedicated
    rotation endpoint.
    """

    _require_manage(actor)
    if key_kind not in {"primary", "delegated"}:
        raise ValueError("key_kind must be primary or delegated")
    if rotate_primary and key_kind != "primary":
        raise ValueError("Only a primary key can be rotated")

    default_label = "Primary workspace key" if key_kind == "primary" else "Delegated workspace key"
    label = str(payload.get("label") or default_label).strip()[:120]
    if not label:
        raise HTTPException(status_code=422, detail="Workspace key label is required")
    scopes_value = payload.get("scopes")
    if key_kind == "primary":
        scopes = list(WORKSPACE_ALL_SCOPES)
    else:
        candidates = (
            [str(item).strip() for item in scopes_value]
            if isinstance(scopes_value, list)
            else list(DEFAULT_DELEGATED_SCOPES)
        )
        scopes = list(dict.fromkeys(item for item in candidates if item))
        if not scopes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="A delegated workspace key requires at least one scope",
            )
    invalid = sorted(set(scopes) - WORKSPACE_SCOPES)
    if invalid:
        raise HTTPException(status_code=422, detail=f"Invalid scopes: {', '.join(invalid)}")
    expires_days = max(1, min(int(payload.get("expires_days") or 90), 365))
    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(days=expires_days)
    credential_id = uuid4()
    replaced_credential_id: UUID | None = None
    parent_credential_id: UUID | None = None
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        current_primary = (
            session.execute(
                text(
                    """
                    SELECT id, expires_at
                    FROM digital_asset.api_credentials
                    WHERE workspace_id = :workspace_id
                      AND key_kind = 'primary'
                      AND revoked_at IS NULL
                    FOR UPDATE
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        primary_is_usable = bool(
            current_primary is not None
            and (current_primary["expires_at"] is None or current_primary["expires_at"] > issued_at)
        )
        if key_kind == "primary":
            if current_primary is not None and not rotate_primary:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Workspace already has a primary key; use the primary-key rotation endpoint"
                    ),
                )
            if current_primary is not None:
                replaced_credential_id = current_primary["id"]
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.api_credentials
                        SET revoked_at = :revoked_at
                        WHERE id = :credential_id AND revoked_at IS NULL
                        """
                    ),
                    {
                        "credential_id": replaced_credential_id,
                        "revoked_at": issued_at,
                    },
                )
        else:
            if not primary_is_usable:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Workspace has no active primary key; create or rotate "
                        "the primary key first"
                    ),
                )
            parent_credential_id = current_primary["id"]
        claims = {
            "iss": "warehouse-os",
            "aud": "warehouse-workspace",
            "sub": str(credential_id),
            "jti": str(credential_id),
            "tenant_id": str(actor.tenant_id),
            "workspace_id": str(workspace["id"]),
            "scopes": scopes,
            "key_kind": key_kind,
            "iat": issued_at,
            "exp": expires_at,
        }
        if parent_credential_id is not None:
            claims["parent_credential_id"] = str(parent_credential_id)
        token = "wak_" + jwt.encode(claims, signing_secret, algorithm="HS256")
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        token_hint = token[:14] + "····" + token[-6:]
        session.execute(
            text(
                """
                INSERT INTO digital_asset.api_credentials(
                  id, tenant_id, workspace_id, label, token_hash, token_hint,
                  scopes, key_kind, parent_credential_id, issued_by,
                  issued_at, expires_at
                ) VALUES (
                  :id, :tenant_id, :workspace_id, :label, :token_hash, :token_hint,
                  :scopes, :key_kind, :parent_credential_id, :issued_by,
                  :issued_at, :expires_at
                )
                """
            ),
            {
                "id": credential_id,
                "tenant_id": actor.tenant_id,
                "workspace_id": workspace["id"],
                "label": label,
                "token_hash": token_hash,
                "token_hint": token_hint,
                "scopes": scopes,
                "key_kind": key_kind,
                "parent_credential_id": parent_credential_id,
                "issued_by": actor.user_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
            },
        )
        _audit(
            session,
            actor,
            (
                "digital_asset.workspace_primary_key_rotated"
                if replaced_credential_id is not None
                else f"digital_asset.workspace_{key_kind}_key_issued"
            ),
            {
                "workspace_id": str(workspace["id"]),
                "credential_id": str(credential_id),
                "label": label,
                "key_kind": key_kind,
                "parent_credential_id": (
                    str(parent_credential_id) if parent_credential_id else None
                ),
                "replaced_credential_id": (
                    str(replaced_credential_id) if replaced_credential_id else None
                ),
                "scopes": scopes,
                "expires_at": expires_at.isoformat(),
            },
        )
    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "credential_id": str(credential_id),
        "key_id": str(credential_id),
        "label": label,
        "key_kind": key_kind,
        "is_primary": key_kind == "primary",
        "parent_credential_id": (str(parent_credential_id) if parent_credential_id else None),
        "replaced_credential_id": (str(replaced_credential_id) if replaced_credential_id else None),
        "api_key": token,
        "api_key_hint": token_hint,
        "scopes": scopes,
        "expires_at": expires_at.isoformat(),
        "base_url": "/api/workspaces/v1",
        "note": "The API key plaintext is returned only once.",
    }


def rotate_workspace_primary_key(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
    *,
    signing_secret: str,
) -> dict[str, object]:
    """Atomically replace the primary key while preserving delegated keys."""

    return issue_workspace_key(
        actor,
        workspace_ref,
        payload,
        signing_secret=signing_secret,
        key_kind="primary",
        rotate_primary=True,
    )


def list_workspace_keys(
    actor: ActorContext,
    workspace_ref: object,
) -> dict[str, object]:
    """List safe workspace-key metadata without ever returning token material."""

    _require_manage(actor)
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref)
        rows = (
            session.execute(
                text(
                    """
                    SELECT c.id, c.label, c.token_hint, c.scopes,
                           c.key_kind, c.parent_credential_id,
                           c.issued_by, u.display_name AS issued_by_name,
                           c.issued_at, c.expires_at, c.last_used_at, c.revoked_at,
                           CASE
                             WHEN c.revoked_at IS NOT NULL THEN 'revoked'
                             WHEN c.expires_at IS NOT NULL AND c.expires_at <= now()
                               THEN 'expired'
                             ELSE 'active'
                           END AS status
                    FROM digital_asset.api_credentials AS c
                    LEFT JOIN iam.users AS u ON u.id = c.issued_by
                    WHERE c.workspace_id = :workspace_id
                    ORDER BY
                      CASE
                        WHEN c.key_kind = 'primary' AND c.revoked_at IS NULL THEN 0
                        WHEN c.key_kind = 'delegated' AND c.revoked_at IS NULL THEN 1
                        ELSE 2
                      END,
                      c.issued_at DESC, c.id
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .all()
        )
    keys = [
        _json_safe(
            {
                **dict(row),
                "is_primary": row["key_kind"] == "primary",
            }
        )
        for row in rows
    ]
    active = [item for item in keys if item["status"] == "active"]
    return {
        "ok": True,
        "workspace": _public_workspace(workspace, actor.tenant_slug),
        "keys": keys,
        "items": keys,
        "count": len(keys),
        "summary": {
            "primary_status": next(
                (str(item["status"]) for item in keys if item["key_kind"] == "primary"),
                "missing",
            ),
            "primary_active": sum(1 for item in active if item["key_kind"] == "primary"),
            "delegated_active": sum(1 for item in active if item["key_kind"] == "delegated"),
            "delegated_total": sum(1 for item in keys if item["key_kind"] == "delegated"),
        },
        "plaintext_exposed": False,
    }


def revoke_workspace_key(
    actor: ActorContext,
    workspace_ref: object,
    credential_ref: object,
) -> dict[str, object]:
    """Revoke one named workspace credential; repeated calls are idempotent."""

    _require_manage(actor)
    credential_id = _uuid_or_none(credential_ref)
    if credential_id is None:
        raise HTTPException(status_code=422, detail="Invalid workspace credential id")
    with tenant_session(actor.tenant_id) as session:
        workspace = _workspace_row(session, workspace_ref, lock=True)
        current = (
            session.execute(
                text(
                    """
                    SELECT id, label, token_hint, scopes, key_kind,
                           parent_credential_id, issued_at, expires_at,
                           last_used_at, revoked_at
                    FROM digital_asset.api_credentials
                    WHERE id = :credential_id AND workspace_id = :workspace_id
                    FOR UPDATE
                    """
                ),
                {
                    "credential_id": credential_id,
                    "workspace_id": workspace["id"],
                },
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            raise HTTPException(status_code=404, detail="Workspace credential not found")
        idempotent_replay = current["revoked_at"] is not None
        if current["key_kind"] == "primary" and not idempotent_replay:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The active primary key cannot be revoked directly; rotate it instead",
            )
        if not idempotent_replay:
            current = (
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.api_credentials
                        SET revoked_at = now()
                        WHERE id = :credential_id AND workspace_id = :workspace_id
                          AND revoked_at IS NULL
                        RETURNING id, label, token_hint, scopes, key_kind,
                                  parent_credential_id, issued_at, expires_at,
                                  last_used_at, revoked_at
                        """
                    ),
                    {
                        "credential_id": credential_id,
                        "workspace_id": workspace["id"],
                    },
                )
                .mappings()
                .one()
            )
            _audit(
                session,
                actor,
                "digital_asset.workspace_key_revoked",
                {
                    "workspace_id": str(workspace["id"]),
                    "credential_id": str(credential_id),
                    "label": current["label"],
                },
            )
        key = _json_safe({**dict(current), "status": "revoked"})
    return {
        "ok": True,
        "workspace_id": str(workspace["id"]),
        "workspace_key": workspace["workspace_key"],
        "credential": key,
        "key": key,
        "idempotent_replay": idempotent_replay,
    }


def authenticate_workspace_key(token: str, *, signing_secret: str) -> WorkspaceCredential:
    if not token.startswith("wak_"):
        raise HTTPException(status_code=401, detail="Invalid workspace key")
    encoded = token.removeprefix("wak_")
    try:
        claims = jwt.decode(
            encoded,
            signing_secret,
            algorithms=["HS256"],
            audience="warehouse-workspace",
            issuer="warehouse-os",
        )
        tenant_id = UUID(str(claims["tenant_id"]))
        workspace_id = UUID(str(claims["workspace_id"]))
        credential_id = UUID(str(claims["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired workspace key") from exc
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT c.id, c.workspace_id, c.label, c.scopes,
                           c.key_kind, c.parent_credential_id
                    FROM digital_asset.api_credentials AS c
                    JOIN digital_asset.workspaces AS w
                      ON w.tenant_id = c.tenant_id AND w.id = c.workspace_id
                    WHERE c.id = :credential_id
                      AND c.workspace_id = :workspace_id
                      AND c.token_hash = :token_hash
                      AND c.revoked_at IS NULL
                      AND (c.expires_at IS NULL OR c.expires_at > now())
                      AND w.status = 'active'
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
            raise HTTPException(status_code=401, detail="Workspace key is revoked or invalid")
        session.execute(
            text(
                """
                UPDATE digital_asset.api_credentials
                SET last_used_at = now()
                WHERE id = :credential_id
                """
            ),
            {"credential_id": credential_id},
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


def workspace_info(credential: WorkspaceCredential) -> dict[str, object]:
    credential.require("workspace:read")
    with tenant_session(credential.tenant_id) as session:
        workspace = _workspace_row(session, credential.workspace_id)
        databases = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT id, logical_name, engine, provider_key, isolation_mode,
                           status, endpoint_ref, config, created_at, updated_at
                    FROM digital_asset.database_bindings
                    WHERE workspace_id = :workspace_id
                    ORDER BY logical_name
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .all()
        ]
        components = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.workspace_components
                    WHERE workspace_id = :workspace_id
                    ORDER BY component_name
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .all()
        ]
        storage = _storage_profile(_storage_binding_rows(session, workspace["id"]))
        measured = _workspace_billable_usage(
            session,
            tenant_id=credential.tenant_id,
            workspace_id=workspace["id"],
            asset_id=workspace["asset_id"],
            refresh_infrastructure=True,
        )
    with system_session() as session:
        tenant_slug = session.execute(
            text("SELECT slug FROM iam.tenants WHERE id = :tenant_id"),
            {"tenant_id": credential.tenant_id},
        ).scalar_one()
    workspace_public = _public_workspace(workspace, str(tenant_slug))
    workspace_public["storage"] = storage
    usage = _json_safe(
        {
            "source_archive_bytes": int(measured["code_bytes"]),
            "runtime_release_bytes": int(measured["runtime_bytes"]),
            "data_volume_bytes": int(measured["data_volume_bytes"]),
            "managed_data_object_bytes": int(measured["data_object_bytes"]),
            "postgresql_bytes": int(measured["database_bytes"]),
            "total_bytes": int(measured["total_bytes"]),
            "quota_bytes": int(workspace["storage_quota_bytes"]),
            "remaining_bytes": max(
                int(workspace["storage_quota_bytes"]) - int(measured["total_bytes"]),
                0,
            ),
            "measured_at": measured["measured_at"],
            "measurement_status": measured["measurement_status"],
            "database_measurement_status": measured["database_measurement_status"],
            "runtime_scan_error_count": measured["runtime_scan_error_count"],
            "sources": {
                "source_archive": "custody_artifact_ledger",
                "runtime_release": "governed_runtime_filesystem",
                "data_volume": "governed_runtime_filesystem",
                "managed_data_objects": "custody_artifact_ledger",
                "postgresql": "pg_total_relation_size",
            },
        }
    )
    workspace_public.update(
        {
            "storage_used_bytes": usage["total_bytes"],
            "source_archive_bytes": usage["source_archive_bytes"],
            "runtime_release_bytes": usage["runtime_release_bytes"],
            "data_volume_bytes": usage["data_volume_bytes"],
            "postgresql_bytes": usage["postgresql_bytes"],
            "total_bytes": usage["total_bytes"],
            "usage_measured_at": usage["measured_at"],
        }
    )
    return {
        "ok": True,
        "workspace": workspace_public,
        "usage": usage,
        "components": components,
        "databases": databases,
        "credential": {
            "id": str(credential.credential_id),
            "label": credential.label,
            "scopes": sorted(credential.scopes),
            "key_kind": credential.key_kind,
            "is_primary": credential.key_kind == "primary",
            "parent_credential_id": (
                str(credential.parent_credential_id) if credential.parent_credential_id else None
            ),
        },
    }


def workspace_usage(credential: WorkspaceCredential) -> dict[str, object]:
    """Return a fresh platform measurement for one authenticated workspace."""

    info = workspace_info(credential)
    return {
        "ok": True,
        "workspace_id": str(credential.workspace_id),
        "workspace_key": info["workspace"]["workspace_key"],
        "usage": info["usage"],
    }


def runtime_hosting_snapshot(actor: ActorContext) -> dict[str, object]:
    """Return non-secret current-company hosting context for Auto Runtime.

    The Runtime sees every application capability and current-company resource,
    but it never receives API key hashes, object-store paths or a database DSN.
    """
    with tenant_session(actor.tenant_id) as session:
        totals = dict(
            session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*)::integer FROM digital_asset.assets
                       WHERE status != 'archived') AS assets,
                      (SELECT count(*)::integer FROM digital_asset.workspaces
                       WHERE status = 'active') AS workspaces,
                      (SELECT count(*)::integer FROM digital_asset.workspace_components
                       WHERE status != 'suspended') AS components,
                      (SELECT count(*)::integer FROM digital_asset.database_bindings
                       WHERE status = 'ready') AS ready_databases,
                      (SELECT count(*)::integer FROM digital_asset.deployments
                       WHERE status = 'ready') AS ready_deployments,
                      (SELECT count(*)::integer FROM digital_asset.deployments
                       WHERE status IN ('queued', 'building', 'deploying'))
                        AS pending_deployments
                    """
                )
            )
            .mappings()
            .one()
        )
        workspaces = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT
                      w.id, w.workspace_key, w.service_plan, w.runtime_status,
                      w.region, w.public_url, w.storage_quota_bytes, w.revision,
                      (
                        SELECT count(*)::integer
                        FROM digital_asset.asset_versions AS v
                        WHERE v.asset_id = a.id
                      ) AS source_version_count,
                      (
                        SELECT count(*)::integer
                        FROM digital_asset.artifacts AS ar
                        WHERE ar.asset_id = a.id
                          AND ar.storage_role = 'code'
                      ) AS code_artifact_count,
                      (
                        EXISTS (
                          SELECT 1 FROM digital_asset.asset_versions AS v
                          WHERE v.asset_id = a.id
                        ) OR EXISTS (
                          SELECT 1 FROM digital_asset.artifacts AS ar
                          WHERE ar.asset_id = a.id
                            AND ar.storage_role = 'code'
                        )
                      ) AS source_available,
                      COALESCE((
                        SELECT jsonb_object_agg(
                          sb.binding_role,
                          jsonb_build_object(
                            'medium', COALESCE(
                              sb.config->>'medium',
                              CASE WHEN sb.provider_key = 'content_addressed_ssd'
                                THEN 'ssd' ELSE 'hdd' END
                            ),
                            'pool_key', sb.pool_key,
                            'provider_key', sb.provider_key,
                            'storage_class', sb.storage_class,
                            'status', sb.status,
                            'selection', sb.config->>'selection'
                          )
                        )
                        FROM digital_asset.storage_bindings AS sb
                        WHERE sb.workspace_id = w.id
                      ), '{}'::jsonb) AS storage,
                      a.asset_no, a.name AS asset_name,
                      COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'name', c.component_name,
                            'kind', c.component_kind,
                            'runtime', c.runtime,
                            'status', c.status
                          ) ORDER BY c.component_name
                        )
                        FROM digital_asset.workspace_components AS c
                        WHERE c.workspace_id = w.id
                      ), '[]'::jsonb) AS components,
                      COALESCE((
                        SELECT jsonb_agg(
                          jsonb_build_object(
                            'logical_name', d.logical_name,
                            'engine', d.engine,
                            'provider', d.provider_key,
                            'pool_key', d.pool_key,
                            'physical_medium', d.physical_medium,
                            'actual_size_bytes', d.actual_size_bytes,
                            'isolation', d.isolation_mode,
                            'status', d.status,
                            'portable_data_api',
                              COALESCE((d.config->>'portable_data_api')::boolean, false)
                          ) ORDER BY d.logical_name
                        )
                        FROM digital_asset.database_bindings AS d
                        WHERE d.workspace_id = w.id
                      ), '[]'::jsonb) AS databases
                    FROM digital_asset.workspaces AS w
                    JOIN digital_asset.assets AS a ON a.id = w.asset_id
                    WHERE w.status = 'active'
                    ORDER BY w.updated_at DESC
                    LIMIT 50
                    """
                )
            )
            .mappings()
            .all()
        ]
        for workspace in workspaces:
            if isinstance(workspace, dict):
                workspace.update(_workspace_entry_fields(actor.tenant_slug, workspace))
                workspace["next_quota_increment_mb"] = WORKSPACE_QUOTA_STEP_MB
                workspace["code_storage_switchable"] = not bool(workspace.get("source_available"))
    pool_state = storage_pool_overview(actor, enforce_permission=False)
    return {
        "source": "digital_asset_postgresql",
        "scope": "current_tenant_only",
        "capabilities": {
            "custody": True,
            "frontend_hosting": True,
            "backend_control_plane": True,
            "portable_database_api": True,
            "container_runtime": True,
            "runtime_provider_state": "runtime_controller_ready",
        },
        "totals": _json_safe(totals),
        "workspaces": workspaces,
        "storage_policy": {
            "default_code_storage": "hdd",
            "ssd_requires_explicit_intent": True,
            "empty_workspace_code_storage_switch": True,
            "existing_code_requires_verified_migration": True,
            "data_storage_enforced": "hdd",
            "quota_is_logical": True,
            "quota_step_bytes": WORKSPACE_QUOTA_STEP_BYTES,
        },
        "storage_pools": pool_state["pools"],
    }
