"""Safe browser access for standalone managed workspace databases.

The public ``dbp_`` value is only a signed locator.  Browser data calls use a
short-lived, revocable ``wdb_`` access token; the long-lived ``wak_`` workspace
key and PostgreSQL credentials never cross this boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status
from sqlalchemy import text

from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import tenant_session

PROJECT_PREFIX = "dbp_"
ACCESS_PREFIX = "wdb_"
REFRESH_PREFIX = "wdr_"
PROJECT_AUDIENCE = "warehouse-database-project"
ACCESS_AUDIENCE = "warehouse-database-browser"
ISSUER = "warehouse-os"
COLLECTION_RE = re.compile(r"^[a-z][a-z0-9_.-]{0,119}$")
RULE_MODES = frozenset({"deny", "session", "owner"})
DEFAULT_RULES: dict[str, object] = {
    "default": {"read": "deny", "write": "deny"},
    "collections": {},
}


@dataclass(frozen=True)
class BrowserProject:
    tenant_id: UUID
    workspace_id: UUID
    app_id: UUID
    project_id: UUID
    workspace_key: str
    enabled: bool
    allowed_origins: tuple[str, ...]
    rules: dict[str, object]
    access_token_ttl_seconds: int
    refresh_session_ttl_days: int
    rate_limit_per_minute: int
    revision: int
    database_provider: str


@dataclass(frozen=True)
class BrowserCredential:
    project: BrowserProject
    session_id: UUID
    subject_id: UUID
    origin: str


def _require_manage(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.manage",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=403, detail="Permission denied")


def _require_read(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.read",
        "assets.manage",
        "asset_mgmt.read",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=403, detail="Permission denied")


def normalize_origin(value: object, *, settings: Settings) -> str:
    source = str(value or "").strip().rstrip("/")
    if not source or len(source) > 500:
        raise HTTPException(status_code=422, detail="Invalid browser origin")
    parsed = urlsplit(source)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(status_code=422, detail=f"Invalid browser origin: {source}")
    hostname = parsed.hostname.lower()
    if parsed.scheme != "https" and not (
        settings.environment != "production" and hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise HTTPException(status_code=422, detail="Browser origins must use HTTPS")
    default_port = 443 if parsed.scheme == "https" else 80
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid browser origin: {source}") from exc
    host = f"[{hostname}]" if ":" in hostname else hostname
    authority = host if port is None or port == default_port else f"{host}:{port}"
    return f"{parsed.scheme}://{authority}"


def normalize_origins(values: object, *, settings: Settings) -> list[str]:
    if not isinstance(values, list):
        raise HTTPException(status_code=422, detail="allowed_origins must be an array")
    origins = list(dict.fromkeys(normalize_origin(value, settings=settings) for value in values))
    if len(origins) > 20:
        raise HTTPException(status_code=422, detail="At most 20 browser origins are allowed")
    return origins


def normalize_rules(value: object) -> dict[str, object]:
    if value is None:
        return json.loads(json.dumps(DEFAULT_RULES))
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail="rules must be an object")
    unknown = set(value) - {"default", "collections"}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unknown rules fields: {sorted(unknown)}")

    def actions(raw: object, *, label: str) -> dict[str, str]:
        if not isinstance(raw, dict) or set(raw) - {"read", "write"}:
            raise HTTPException(status_code=422, detail=f"{label} must define read/write rules")
        result: dict[str, str] = {}
        for action in ("read", "write"):
            mode = str(raw.get(action) or "deny").strip().lower()
            if mode not in RULE_MODES:
                raise HTTPException(
                    status_code=422,
                    detail=f"{label}.{action} must be deny, session, or owner",
                )
            result[action] = mode
        return result

    default = actions(value.get("default") or DEFAULT_RULES["default"], label="rules.default")
    raw_collections = value.get("collections") or {}
    if not isinstance(raw_collections, dict) or len(raw_collections) > 100:
        raise HTTPException(status_code=422, detail="rules.collections must have at most 100 items")
    collections: dict[str, object] = {}
    for collection, rule in raw_collections.items():
        name = str(collection)
        if not COLLECTION_RE.fullmatch(name):
            raise HTTPException(status_code=422, detail=f"Invalid collection rule: {name}")
        collections[name] = actions(rule, label=f"rules.collections.{name}")
    return {"default": default, "collections": collections}


def project_key(project: BrowserProject, *, settings: Settings) -> str:
    claims = {
        "iss": ISSUER,
        "aud": PROJECT_AUDIENCE,
        "typ": "database_project",
        "sub": str(project.project_id),
        "tenant_id": str(project.tenant_id),
        "workspace_id": str(project.workspace_id),
        "app_id": str(project.app_id),
    }
    return PROJECT_PREFIX + jwt.encode(claims, settings.integration_secret, algorithm="HS256")


def _project_claims(value: str, *, settings: Settings) -> tuple[UUID, UUID, UUID, UUID]:
    if not value.startswith(PROJECT_PREFIX):
        raise HTTPException(status_code=404, detail="Database project not found")
    try:
        claims = jwt.decode(
            value.removeprefix(PROJECT_PREFIX),
            settings.integration_secret,
            algorithms=["HS256"],
            audience=PROJECT_AUDIENCE,
            issuer=ISSUER,
        )
        if claims.get("typ") != "database_project":
            raise ValueError("wrong token type")
        return (
            UUID(str(claims["tenant_id"])),
            UUID(str(claims["workspace_id"])),
            UUID(str(claims["app_id"])),
            UUID(str(claims["sub"])),
        )
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Database project not found") from exc


def _project_from_row(row: dict[str, object]) -> BrowserProject:
    rules = row["rules"] if isinstance(row["rules"], dict) else json.loads(str(row["rules"]))
    return BrowserProject(
        tenant_id=UUID(str(row["tenant_id"])),
        workspace_id=UUID(str(row["workspace_id"])),
        app_id=UUID(str(row["id"])),
        project_id=UUID(str(row["project_id"])),
        workspace_key=str(row["workspace_key"]),
        enabled=bool(row["enabled"]),
        allowed_origins=tuple(str(item) for item in row["allowed_origins"]),
        rules=rules,
        access_token_ttl_seconds=int(row["access_token_ttl_seconds"]),
        refresh_session_ttl_days=int(row["refresh_session_ttl_days"]),
        rate_limit_per_minute=int(row["rate_limit_per_minute"]),
        revision=int(row["revision"]),
        database_provider=str(row["database_provider"]),
    )


_PROJECT_QUERY = """
    SELECT a.*,w.workspace_key,d.provider_key AS database_provider
    FROM digital_asset.database_browser_apps AS a
    JOIN digital_asset.workspaces AS w
      ON w.tenant_id=a.tenant_id AND w.id=a.workspace_id
    JOIN digital_asset.database_bindings AS d
      ON d.tenant_id=a.tenant_id AND d.workspace_id=a.workspace_id AND d.is_default
    WHERE a.id=:app_id AND a.project_id=:project_id
      AND a.workspace_id=:workspace_id AND w.status='active' AND d.status='ready'
      AND COALESCE((d.capabilities->>'collection_data_api')::boolean,false)
"""


def resolve_project(value: str, *, settings: Settings) -> BrowserProject:
    tenant_id, workspace_id, app_id, project_id = _project_claims(value, settings=settings)
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(_PROJECT_QUERY),
                {
                    "app_id": app_id,
                    "project_id": project_id,
                    "workspace_id": workspace_id,
                },
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Database project not found")
    return _project_from_row(dict(row))


def require_project_origin(
    value: str,
    origin: object,
    *,
    settings: Settings,
) -> BrowserProject:
    project = resolve_project(value, settings=settings)
    if not project.enabled:
        raise HTTPException(status_code=403, detail="Browser database access is disabled")
    normalized = normalize_origin(origin, settings=settings)
    if normalized not in project.allowed_origins:
        raise HTTPException(status_code=403, detail="Browser origin is not allowed")
    return project


def origin_is_allowed(value: str, origin: object, *, settings: Settings) -> bool:
    try:
        require_project_origin(value, origin, settings=settings)
        return True
    except HTTPException:
        return False


def _project_payload(
    project: BrowserProject,
    *,
    settings: Settings,
    admin: bool,
) -> dict[str, object]:
    key = project_key(project, settings=settings)
    base = f"{settings.public_origin}/api/database-gateway/v1/projects/{key}"
    result: dict[str, object] = {
        "project_id": str(project.project_id),
        "project_key": key,
        "workspace_id": str(project.workspace_id),
        "workspace_key": project.workspace_key,
        "enabled": project.enabled,
        "endpoint": base,
        "sdk_url": f"{settings.public_origin}/api/database-gateway/v1/sdk.js",
        "authentication": "anonymous_refresh_session",
        "access_token_ttl_seconds": project.access_token_ttl_seconds,
        "database_provider": project.database_provider,
        "workspace_key_exposed": False,
        "database_credentials_exposed": False,
    }
    if admin:
        result.update(
            {
                "allowed_origins": list(project.allowed_origins),
                "rules": project.rules,
                "refresh_session_ttl_days": project.refresh_session_ttl_days,
                "rate_limit_per_minute": project.rate_limit_per_minute,
                "revision": project.revision,
            }
        )
    return result


def configure_browser_access(
    actor: ActorContext,
    workspace_ref: object,
    payload: dict[str, object],
    *,
    settings: Settings,
) -> dict[str, object]:
    _require_manage(actor)
    with tenant_session(actor.tenant_id) as session:
        workspace = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.workspaces
                    WHERE (id::text=:workspace_ref OR workspace_key=:workspace_ref)
                      AND status='active'
                    FOR UPDATE
                    """
                ),
                {"workspace_ref": str(workspace_ref).strip()},
            )
            .mappings()
            .one_or_none()
        )
        if workspace is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        database = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.database_bindings
                    WHERE workspace_id=:workspace_id AND is_default
                    FOR UPDATE
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if database is None or database["status"] != "ready":
            raise HTTPException(status_code=409, detail="Workspace default database is not ready")
        capabilities = database["capabilities"] or {}
        if not bool(capabilities.get("collection_data_api")):
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "browser_gateway_requires_collection_data_api",
                    "provider": database["provider_key"],
                    "next_action": "use a platform-managed database or a server-side backend",
                },
            )
        existing = (
            session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.database_browser_apps
                    WHERE workspace_id=:workspace_id FOR UPDATE
                    """
                ),
                {"workspace_id": workspace["id"]},
            )
            .mappings()
            .one_or_none()
        )
        current = dict(existing) if existing is not None else {}
        origins = (
            normalize_origins(payload["allowed_origins"], settings=settings)
            if "allowed_origins" in payload
            else list(current.get("allowed_origins") or [])
        )
        rules = (
            normalize_rules(payload.get("rules"))
            if "rules" in payload
            else current.get("rules") or normalize_rules(None)
        )
        enabled = bool(payload.get("enabled", current.get("enabled", False)))
        if enabled and not origins:
            raise HTTPException(
                status_code=422,
                detail="At least one allowed origin is required before enabling browser access",
            )
        access_ttl = int(
            payload.get("access_token_ttl_seconds", current.get("access_token_ttl_seconds", 900))
        )
        refresh_days = int(
            payload.get("refresh_session_ttl_days", current.get("refresh_session_ttl_days", 30))
        )
        rate_limit = int(
            payload.get("rate_limit_per_minute", current.get("rate_limit_per_minute", 120))
        )
        if not 300 <= access_ttl <= 3600:
            raise HTTPException(status_code=422, detail="Access token TTL must be 300-3600 seconds")
        if not 1 <= refresh_days <= 90:
            raise HTTPException(status_code=422, detail="Refresh session TTL must be 1-90 days")
        if not 10 <= rate_limit <= 10000:
            raise HTTPException(status_code=422, detail="Rate limit must be 10-10000 per minute")
        if existing is None:
            app_id = uuid4()
            project_id = uuid4()
            row = (
                session.execute(
                    text(
                        """
                        INSERT INTO digital_asset.database_browser_apps(
                          id,tenant_id,workspace_id,project_id,enabled,allowed_origins,
                          rules,access_token_ttl_seconds,refresh_session_ttl_days,
                          rate_limit_per_minute,created_by
                        ) VALUES (
                          :id,:tenant_id,:workspace_id,:project_id,:enabled,:allowed_origins,
                          CAST(:rules AS jsonb),:access_ttl,:refresh_days,:rate_limit,:created_by
                        ) RETURNING *
                        """
                    ),
                    {
                        "id": app_id,
                        "tenant_id": actor.tenant_id,
                        "workspace_id": workspace["id"],
                        "project_id": project_id,
                        "enabled": enabled,
                        "allowed_origins": origins,
                        "rules": json.dumps(rules, separators=(",", ":")),
                        "access_ttl": access_ttl,
                        "refresh_days": refresh_days,
                        "rate_limit": rate_limit,
                        "created_by": actor.user_id,
                    },
                )
                .mappings()
                .one()
            )
        else:
            row = (
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.database_browser_apps
                        SET enabled=:enabled,allowed_origins=:allowed_origins,
                            rules=CAST(:rules AS jsonb),
                            access_token_ttl_seconds=:access_ttl,
                            refresh_session_ttl_days=:refresh_days,
                            rate_limit_per_minute=:rate_limit,
                            revision=revision+1
                        WHERE id=:id RETURNING *
                        """
                    ),
                    {
                        "id": existing["id"],
                        "enabled": enabled,
                        "allowed_origins": origins,
                        "rules": json.dumps(rules, separators=(",", ":")),
                        "access_ttl": access_ttl,
                        "refresh_days": refresh_days,
                        "rate_limit": rate_limit,
                    },
                )
                .mappings()
                .one()
            )
        if not enabled:
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_browser_sessions
                    SET revoked_at=COALESCE(revoked_at,now())
                    WHERE browser_app_id=:app_id AND revoked_at IS NULL
                    """
                ),
                {"app_id": row["id"]},
            )
        project = _project_from_row(
            {
                **dict(row),
                "workspace_key": workspace["workspace_key"],
                "database_provider": database["provider_key"],
            }
        )
    return {"ok": True, "project": _project_payload(project, settings=settings, admin=True)}


def browser_access_configuration(
    actor: ActorContext,
    workspace_ref: object,
    *,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT a.*,w.workspace_key,d.provider_key AS database_provider
                    FROM digital_asset.database_browser_apps AS a
                    JOIN digital_asset.workspaces AS w ON w.id=a.workspace_id
                    JOIN digital_asset.database_bindings AS d
                      ON d.workspace_id=w.id AND d.is_default
                    WHERE (w.id::text=:workspace_ref OR w.workspace_key=:workspace_ref)
                      AND w.status='active'
                    """
                ),
                {"workspace_ref": str(workspace_ref).strip()},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Browser database project not configured")
    project = _project_from_row(dict(row))
    return {"ok": True, "project": _project_payload(project, settings=settings, admin=True)}


def list_database_projects(
    actor: ActorContext,
    *,
    settings: Settings,
    limit: int = 100,
) -> dict[str, object]:
    """List every active workspace database through one safe control-plane view.

    This intentionally includes databases attached to hosted applications as
    well as standalone database services.  It is the AI secretary's inventory
    surface and never returns a DSN, role password, workspace key plaintext, or
    browser session token.
    """

    _require_read(actor)
    bounded_limit = max(1, min(int(limit), 500))
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT
                      a.id AS asset_id,a.asset_no,a.name,a.asset_kind,
                      a.status AS asset_status,a.summary,a.metadata,
                      w.id AS workspace_id,w.workspace_key,w.service_plan,
                      w.runtime_status,w.storage_quota_bytes,w.created_at,
                      d.id AS database_id,d.logical_name,d.provider_key,
                      d.isolation_mode,d.status AS database_status,
                      d.actual_size_bytes,d.capabilities,
                      ba.id AS browser_app_id,ba.project_id AS browser_project_id,
                      ba.enabled AS browser_enabled,
                      ba.allowed_origins AS browser_allowed_origins,
                      ba.rules AS browser_rules,
                      ba.access_token_ttl_seconds AS browser_access_ttl,
                      ba.refresh_session_ttl_days AS browser_refresh_days,
                      ba.rate_limit_per_minute AS browser_rate_limit,
                      ba.revision AS browser_revision
                    FROM digital_asset.assets AS a
                    JOIN digital_asset.workspaces AS w
                      ON w.asset_id=a.id AND w.status='active'
                    JOIN digital_asset.database_bindings AS d
                      ON d.workspace_id=w.id AND d.is_default
                    LEFT JOIN digital_asset.database_browser_apps AS ba
                      ON ba.workspace_id=w.id
                    WHERE a.status<>'archived'
                    ORDER BY w.created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": bounded_limit},
            )
            .mappings()
            .all()
        )

    projects: list[dict[str, object]] = []
    for raw in rows:
        row = dict(raw)
        metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        browser_project = None
        if row.get("browser_app_id") is not None:
            browser_project = _project_payload(
                BrowserProject(
                    tenant_id=actor.tenant_id,
                    workspace_id=UUID(str(row["workspace_id"])),
                    app_id=UUID(str(row["browser_app_id"])),
                    project_id=UUID(str(row["browser_project_id"])),
                    workspace_key=str(row["workspace_key"]),
                    enabled=bool(row["browser_enabled"]),
                    allowed_origins=tuple(
                        str(item) for item in (row.get("browser_allowed_origins") or [])
                    ),
                    rules=(
                        row["browser_rules"]
                        if isinstance(row.get("browser_rules"), dict)
                        else json.loads(str(row["browser_rules"]))
                    ),
                    access_token_ttl_seconds=int(row["browser_access_ttl"]),
                    refresh_session_ttl_days=int(row["browser_refresh_days"]),
                    rate_limit_per_minute=int(row["browser_rate_limit"]),
                    revision=int(row["browser_revision"]),
                    database_provider=str(row["provider_key"]),
                ),
                settings=settings,
                admin=True,
            )
        projects.append(
            {
                "service_kind": metadata.get("service_kind") or "workspace_database",
                "asset": {
                    "uuid": str(row["asset_id"]),
                    "asset_no": row["asset_no"],
                    "name": row["name"],
                    "kind": row["asset_kind"],
                    "status": row["asset_status"],
                    "summary": row["summary"],
                },
                "workspace": {
                    "uuid": str(row["workspace_id"]),
                    "workspace_key": row["workspace_key"],
                    "service_plan": row["service_plan"],
                    "runtime_status": row["runtime_status"],
                    "storage_quota_bytes": int(row["storage_quota_bytes"]),
                    "created_at": (
                        row["created_at"].isoformat()
                        if isinstance(row.get("created_at"), datetime)
                        else row.get("created_at")
                    ),
                },
                "database": {
                    "uuid": str(row["database_id"]),
                    "logical_name": row["logical_name"],
                    "provider": row["provider_key"],
                    "isolation_mode": row["isolation_mode"],
                    "status": row["database_status"],
                    "actual_size_bytes": int(row["actual_size_bytes"] or 0),
                    "capabilities": row.get("capabilities") or {},
                    "credentials_exposed": False,
                },
                "browser_project": browser_project,
            }
        )
    return {
        "ok": True,
        "projects": projects,
        "count": len(projects),
        "credentials_exposed": False,
    }


def database_onboarding_bundle(
    actor: ActorContext,
    workspace_ref: object,
    *,
    settings: Settings,
) -> dict[str, object]:
    """Return the complete non-secret integration hand-off for one database."""

    inventory = list_database_projects(actor, settings=settings, limit=500)
    reference = str(workspace_ref).strip()
    selected = next(
        (
            item
            for item in inventory["projects"]
            if reference
            in {
                str(item["workspace"]["uuid"]),
                str(item["workspace"]["workspace_key"]),
            }
        ),
        None,
    )
    if selected is None:
        raise HTTPException(status_code=404, detail="Workspace database not found")

    workspace_key = str(selected["workspace"]["workspace_key"])
    browser_project = selected.get("browser_project")
    browser_key = (
        str(browser_project["project_key"])
        if isinstance(browser_project, dict) and browser_project.get("project_key")
        else None
    )
    public_origin = settings.public_origin.rstrip("/")
    browser_base = (
        f"{public_origin}/api/database-gateway/v1/projects/{browser_key}"
        if browser_key
        else None
    )
    sdk_url = f"{public_origin}/api/database-gateway/v1/sdk.js"
    quickstart = None
    if browser_key:
        quickstart = (
            f'import {{ createWarehouseDataClient }} from "{sdk_url}";\n'
            f'const db = createWarehouseDataClient({{ projectKey: "{browser_key}" }});\n'
            "await db.connect();\n"
            'const result = await db.list("your_collection");'
        )
    return {
        "ok": True,
        "project": selected,
        "files": [
            {
                "kind": "javascript_sdk",
                "url": sdk_url,
                "format": "esm",
                "required_for": "static_browser_frontend",
            },
            {
                "kind": "database_guide",
                "url": f"{public_origin}/api/digital-assets/guide/download",
                "format": "markdown",
            },
        ],
        "apis": {
            "company_control_plane": {
                "schema": f"{public_origin}/api/workspaces/{workspace_key}/database/schema",
                "health": f"{public_origin}/api/workspaces/{workspace_key}/database/health",
                "browser_access": (
                    f"{public_origin}/api/workspaces/{workspace_key}/database/browser-access"
                ),
            },
            "server_integration": {
                "base": f"{public_origin}/api/workspaces/v1",
                "authentication": "Bearer wak_ (server-side only)",
                "schema": f"{public_origin}/api/workspaces/v1/database/schema",
                "collection": f"{public_origin}/api/workspaces/v1/data/{{collection}}",
                "record": (
                    f"{public_origin}/api/workspaces/v1/data/{{collection}}/{{record_key}}"
                ),
            },
            "browser_integration": (
                {
                    "project": browser_base,
                    "sessions": f"{browser_base}/sessions",
                    "collection": f"{browser_base}/data/{{collection}}",
                    "record": f"{browser_base}/data/{{collection}}/{{record_key}}",
                }
                if browser_base
                else None
            ),
        },
        "keys": {
            "public_project_key": browser_key,
            "public_project_key_kind": "dbp_signed_locator",
            "browser_tokens": "wdb_ and wdr_ are issued directly to an allowed Origin",
            "workspace_api_key": {
                "prefix": "wak_",
                "delivery": "one_time_secure_delivery_after_user_confirmation",
                "issuance_tool": "digital_market_key_issue",
                "inventory_tool": "digital_market_keys_list",
                "plaintext_in_ai_chat": False,
                "browser_allowed": False,
            },
            "database_password": {
                "exposed": False,
                "delivery": "runtime_secret_injection_only",
            },
        },
        "quickstart": quickstart,
        "next_action": (
            "Use the supplied SDK and public project key"
            if browser_key
            else "Configure exact HTTPS Origins and deny-by-default collection rules"
        ),
    }


def public_project_configuration(
    project: BrowserProject,
    *,
    settings: Settings,
) -> dict[str, object]:
    return {"ok": True, "project": _project_payload(project, settings=settings, admin=False)}


def _consume_rate_limit(
    project: BrowserProject,
    *,
    identity: str,
) -> None:
    identity_hash = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    with tenant_session(project.tenant_id) as session:
        accepted = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.database_browser_rate_limits(
                      tenant_id,browser_app_id,bucket_start,identity_hash,request_count
                    ) VALUES (
                      :tenant_id,:app_id,date_trunc('minute',now()),:identity_hash,1
                    )
                    ON CONFLICT (tenant_id,browser_app_id,bucket_start,identity_hash)
                    DO UPDATE SET request_count=
                          digital_asset.database_browser_rate_limits.request_count+1,
                        updated_at=now()
                    WHERE digital_asset.database_browser_rate_limits.request_count < :limit
                    RETURNING request_count
                    """
                ),
                {
                    "tenant_id": project.tenant_id,
                    "app_id": project.app_id,
                    "identity_hash": identity_hash,
                    "limit": project.rate_limit_per_minute,
                },
            )
            .mappings()
            .one_or_none()
        )
    if accepted is None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Browser database rate limit exceeded",
            headers={"Retry-After": "60"},
        )


def _new_refresh_token() -> str:
    return REFRESH_PREFIX + secrets.token_urlsafe(48)


def _refresh_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _access_token(
    project: BrowserProject,
    *,
    session_id: UUID,
    subject_id: UUID,
    origin: str,
    settings: Settings,
) -> tuple[str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=project.access_token_ttl_seconds)
    claims = {
        "iss": ISSUER,
        "aud": ACCESS_AUDIENCE,
        "typ": "database_browser_access",
        "sub": str(subject_id),
        "jti": str(session_id),
        "tenant_id": str(project.tenant_id),
        "workspace_id": str(project.workspace_id),
        "app_id": str(project.app_id),
        "project_id": str(project.project_id),
        "origin": origin,
        "revision": project.revision,
        "iat": now,
        "exp": expires_at,
    }
    token = ACCESS_PREFIX + jwt.encode(
        claims,
        settings.integration_secret,
        algorithm="HS256",
    )
    return token, expires_at


def issue_browser_session(
    project: BrowserProject,
    *,
    origin: str,
    refresh_token: object,
    request_identity: str,
    settings: Settings,
) -> dict[str, object]:
    _consume_rate_limit(project, identity=f"session:{origin}:{request_identity}")
    now = datetime.now(UTC)
    new_refresh = _new_refresh_token()
    with tenant_session(project.tenant_id) as session:
        if refresh_token:
            supplied = str(refresh_token)
            if not supplied.startswith(REFRESH_PREFIX) or len(supplied) > 512:
                raise HTTPException(status_code=401, detail="Invalid browser refresh token")
            current = (
                session.execute(
                    text(
                        """
                        SELECT * FROM digital_asset.database_browser_sessions
                        WHERE browser_app_id=:app_id AND refresh_token_hash=:token_hash
                          AND origin=:origin AND revoked_at IS NULL AND expires_at>now()
                        FOR UPDATE
                        """
                    ),
                    {
                        "app_id": project.app_id,
                        "token_hash": _refresh_hash(supplied),
                        "origin": origin,
                    },
                )
                .mappings()
                .one_or_none()
            )
            if current is None:
                raise HTTPException(status_code=401, detail="Browser refresh token is expired")
            session_id = UUID(str(current["id"]))
            subject_id = UUID(str(current["subject_id"]))
            session.execute(
                text(
                    """
                    UPDATE digital_asset.database_browser_sessions
                    SET refresh_token_hash=:token_hash,last_used_at=now()
                    WHERE id=:session_id
                    """
                ),
                {"token_hash": _refresh_hash(new_refresh), "session_id": session_id},
            )
        else:
            session_id = uuid4()
            subject_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.database_browser_sessions(
                      id,tenant_id,browser_app_id,subject_id,refresh_token_hash,
                      origin,expires_at
                    ) VALUES (
                      :id,:tenant_id,:app_id,:subject_id,:token_hash,:origin,:expires_at
                    )
                    """
                ),
                {
                    "id": session_id,
                    "tenant_id": project.tenant_id,
                    "app_id": project.app_id,
                    "subject_id": subject_id,
                    "token_hash": _refresh_hash(new_refresh),
                    "origin": origin,
                    "expires_at": now + timedelta(days=project.refresh_session_ttl_days),
                },
            )
    access, expires_at = _access_token(
        project,
        session_id=session_id,
        subject_id=subject_id,
        origin=origin,
        settings=settings,
    )
    return {
        "ok": True,
        "token_type": "Bearer",
        "access_token": access,
        "expires_in": project.access_token_ttl_seconds,
        "expires_at": expires_at.isoformat(),
        "refresh_token": new_refresh,
        "subject": str(subject_id),
        "session_id": str(session_id),
    }


def authenticate_browser_access(
    project: BrowserProject,
    token: object,
    *,
    origin: str,
    settings: Settings,
) -> BrowserCredential:
    value = str(token or "")
    if not value.startswith(ACCESS_PREFIX):
        raise HTTPException(status_code=401, detail="Browser access token is required")
    try:
        claims = jwt.decode(
            value.removeprefix(ACCESS_PREFIX),
            settings.integration_secret,
            algorithms=["HS256"],
            audience=ACCESS_AUDIENCE,
            issuer=ISSUER,
        )
        if claims.get("typ") != "database_browser_access":
            raise ValueError("wrong token type")
        session_id = UUID(str(claims["jti"]))
        subject_id = UUID(str(claims["sub"]))
        claim_project = UUID(str(claims["project_id"]))
        claim_app = UUID(str(claims["app_id"]))
        claim_workspace = UUID(str(claims["workspace_id"]))
        revision = int(claims["revision"])
        claim_origin = str(claims["origin"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired browser access token",
        ) from exc
    if (
        claim_project != project.project_id
        or claim_app != project.app_id
        or claim_workspace != project.workspace_id
        or claim_origin != origin
        or revision != project.revision
    ):
        raise HTTPException(status_code=401, detail="Browser access token is stale")
    with tenant_session(project.tenant_id) as session:
        active = session.execute(
            text(
                """
                    SELECT 1 FROM digital_asset.database_browser_sessions
                    WHERE id=:session_id AND browser_app_id=:app_id
                      AND subject_id=:subject_id AND origin=:origin
                      AND revoked_at IS NULL AND expires_at>now()
                    """
            ),
            {
                "session_id": session_id,
                "app_id": project.app_id,
                "subject_id": subject_id,
                "origin": origin,
            },
        ).scalar_one_or_none()
    if active is None:
        raise HTTPException(status_code=401, detail="Browser session is revoked or expired")
    _consume_rate_limit(project, identity=f"access:{subject_id}")
    return BrowserCredential(
        project=project,
        session_id=session_id,
        subject_id=subject_id,
        origin=origin,
    )


def authorize_collection(
    credential: BrowserCredential,
    collection: str,
    action: str,
) -> str | None:
    if not COLLECTION_RE.fullmatch(collection):
        raise HTTPException(status_code=422, detail="Invalid collection")
    collections = credential.project.rules.get("collections") or {}
    default = credential.project.rules.get("default") or DEFAULT_RULES["default"]
    rule = collections.get(collection, default) if isinstance(collections, dict) else default
    mode = str(rule.get(action) or "deny") if isinstance(rule, dict) else "deny"
    if mode == "deny":
        raise HTTPException(
            status_code=403,
            detail=f"Database rule denies {action} on {collection}",
        )
    if mode == "owner":
        return str(credential.subject_id)
    if mode == "session":
        return None
    raise HTTPException(status_code=403, detail="Database rule is invalid")
