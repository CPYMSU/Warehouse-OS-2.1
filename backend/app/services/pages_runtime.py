"""Stable Pages host routing and governed source/design inspection."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import stat
import tarfile
import threading
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings, get_settings
from app.db.session import system_session, tenant_session
from app.services.object_storage import object_store_read_candidates
from app.services.pages_app_contract import (
    PAGES_APP_MANIFEST_FILENAME,
    PAGES_APP_SCHEMA,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.services.digital_asset_hosting import WorkspaceCredential


SITE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
RESERVED_SITE_KEYS = frozenset(
    {
        "admin",
        "api",
        "app",
        "assets",
        "auth",
        "cdn",
        "docs",
        "mac-origin",
        "mail",
        "origin",
        "pages",
        "static",
        "status",
        "www",
    }
)
MAX_TEXT_FILE_BYTES = 256 * 1024
MAX_IMAGE_FILE_BYTES = 2 * 1024 * 1024
MAX_DESIGN_FILES = 5_000
_ROUTE_CACHE_SECONDS = 15.0
_route_cache: dict[str, tuple[float, dict[str, object] | None]] = {}
_route_cache_lock = threading.Lock()

_TEXT_EXTENSIONS = frozenset(
    {
        ".astro",
        ".c",
        ".cc",
        ".cjs",
        ".cpp",
        ".css",
        ".csv",
        ".go",
        ".graphql",
        ".h",
        ".hpp",
        ".htm",
        ".html",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".kts",
        ".md",
        ".mdx",
        ".mjs",
        ".py",
        ".pyi",
        ".rs",
        ".scala",
        ".scss",
        ".svg",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".vue",
        ".xml",
        ".yaml",
        ".yml",
    }
)
_IMAGE_EXTENSIONS = frozenset({".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"})
_BROWSER_SOURCE_EXTENSIONS = frozenset(
    {
        ".astro",
        ".cjs",
        ".html",
        ".htm",
        ".js",
        ".jsx",
        ".mjs",
        ".ts",
        ".tsx",
        ".vue",
    }
)
_PYTHON_SOURCE_EXTENSIONS = frozenset({".py", ".pyi"})
_JVM_SOURCE_EXTENSIONS = frozenset({".java", ".kt", ".kts", ".scala"})
_NATIVE_SOURCE_EXTENSIONS = frozenset({".c", ".cc", ".cpp", ".go", ".h", ".hpp", ".rs", ".wasm"})
_COMPUTE_IGNORED_PARTS = frozenset(
    {".git", ".venv", "build", "dist", "node_modules", "vendor", "venv"}
)
_SENSITIVE_SUFFIXES = frozenset({".jks", ".key", ".keystore", ".p12", ".pem", ".pfx"})
_SENSITIVE_NAMES = frozenset(
    {
        ".npmrc",
        ".pypirc",
        "credentials.json",
        "id_ed25519",
        "id_rsa",
        "service-account.json",
        "service_account.json",
        "secrets.json",
    }
)


@dataclass(frozen=True)
class ArchiveMember:
    path: str
    raw_path: str
    size_bytes: int


def validate_site_key(value: object) -> str:
    candidate = str(value or "").strip().lower()
    if not SITE_KEY_RE.fullmatch(candidate):
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "invalid_pages_site_key",
                "message": (
                    "site_key must be one DNS label, 3-63 characters, using "
                    "lowercase letters, numbers and internal hyphens"
                ),
            },
        )
    if candidate in RESERVED_SITE_KEYS:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "reserved_pages_site_key",
                "site_key": candidate,
                "message": "This Pages site name is reserved for platform infrastructure",
            },
        )
    return candidate


def pages_hostname(site_key: str, settings: Settings | None = None) -> str:
    configured = settings or get_settings()
    return f"{validate_site_key(site_key)}.{configured.pages_root_domain}"


def pages_url(site_key: str, settings: Settings | None = None) -> str:
    configured = settings or get_settings()
    return f"{configured.pages_scheme}://{pages_hostname(site_key, configured)}"


def pages_runtime_hostname(site_key: str, settings: Settings | None = None) -> str:
    configured = settings or get_settings()
    return f"{validate_site_key(site_key)}.{configured.pages_runtime_root_domain}"


def pages_runtime_url(site_key: str, settings: Settings | None = None) -> str:
    configured = settings or get_settings()
    return f"{configured.pages_scheme}://{pages_runtime_hostname(site_key, configured)}"


def pages_entry_path(site_key: str, runtime_path: str = "") -> str:
    base = f"/apps/{validate_site_key(site_key)}/"
    suffix = str(runtime_path or "").lstrip("/")
    return base + suffix


def pages_entry_url(
    site_key: str,
    settings: Settings | None = None,
    runtime_path: str = "",
) -> str:
    configured = settings or get_settings()
    return configured.public_origin + pages_entry_path(site_key, runtime_path)


def pages_hostname_site_key(hostname: str, settings: Settings) -> str | None:
    clean = str(hostname or "").strip().lower().rstrip(".")
    if ":" in clean:
        clean = clean.split(":", 1)[0]
    suffix = "." + settings.pages_root_domain
    if not clean.endswith(suffix):
        return None
    candidate = clean[: -len(suffix)]
    return candidate if SITE_KEY_RE.fullmatch(candidate) else None


def pages_runtime_hostname_site_key(hostname: str, settings: Settings) -> str | None:
    clean = str(hostname or "").strip().lower().rstrip(".")
    if ":" in clean:
        clean = clean.split(":", 1)[0]
    suffix = "." + settings.pages_runtime_root_domain
    if not clean.endswith(suffix):
        return None
    candidate = clean[: -len(suffix)]
    if candidate in RESERVED_SITE_KEYS:
        return None
    return candidate if SITE_KEY_RE.fullmatch(candidate) else None


def pages_internal_path(route: dict[str, object], public_path: str) -> str:
    base = f"/assets/{route['tenant_slug']}/{route['workspace_key']}"
    original = "/" + str(public_path or "/").lstrip("/")
    if original == base or original.startswith(base + "/"):
        return original
    return base + original


def invalidate_pages_route_cache() -> None:
    with _route_cache_lock:
        _route_cache.clear()


def _default_route_config() -> dict[str, object]:
    return {
        "delivery": "static_assets",
        "compute": "browser",
        "database": "platform_api",
        "source": "immutable_versions",
        "entry_mode": "warehouse_os",
    }


def _workspace_identity(session: Session, tenant_id: UUID, workspace_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT w.id, w.tenant_id, w.workspace_key, w.active_deployment_id,
                       tenant.slug AS tenant_slug
                FROM digital_asset.workspaces AS w
                JOIN iam.tenants AS tenant ON tenant.id=w.tenant_id
                WHERE w.tenant_id=:tenant_id AND w.id=:workspace_id
                """
            ),
            {"tenant_id": tenant_id, "workspace_id": workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return dict(row)


def ensure_pages_route(session: Session, tenant_id: UUID, workspace_id: UUID) -> dict[str, object]:
    existing = (
        session.execute(
            text(
                "SELECT * FROM platform.pages_routes "
                "WHERE tenant_id=:tenant_id AND workspace_id=:workspace_id"
            ),
            {"tenant_id": tenant_id, "workspace_id": workspace_id},
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        return dict(existing)
    workspace = _workspace_identity(session, tenant_id, workspace_id)
    for attempt in range(100):
        candidate = str(workspace["workspace_key"])
        if attempt:
            suffix = hashlib.sha256(f"{workspace_id}:{attempt}".encode()).hexdigest()[:8]
            candidate = f"{candidate[:53]}-{suffix}"
        if candidate in RESERVED_SITE_KEYS:
            continue
        inserted = (
            session.execute(
                text(
                    """
                    INSERT INTO platform.pages_routes(
                      id, site_key, tenant_id, tenant_slug, workspace_id,
                      workspace_key, active_deployment_id, status, config
                    ) VALUES (
                      :id, :site_key, :tenant_id, :tenant_slug, :workspace_id,
                      :workspace_key, :active_deployment_id, :status,
                      CAST(:config AS jsonb)
                    ) ON CONFLICT DO NOTHING
                    RETURNING *
                    """
                ),
                {
                    "id": uuid4(),
                    "site_key": candidate,
                    "tenant_id": tenant_id,
                    "tenant_slug": workspace["tenant_slug"],
                    "workspace_id": workspace_id,
                    "workspace_key": workspace["workspace_key"],
                    "active_deployment_id": workspace.get("active_deployment_id"),
                    "status": ("active" if workspace.get("active_deployment_id") else "reserved"),
                    "config": json.dumps(_default_route_config()),
                },
            )
            .mappings()
            .one_or_none()
        )
        if inserted is not None:
            return dict(inserted)
        existing = (
            session.execute(
                text(
                    "SELECT * FROM platform.pages_routes "
                    "WHERE tenant_id=:tenant_id AND workspace_id=:workspace_id"
                ),
                {"tenant_id": tenant_id, "workspace_id": workspace_id},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            return dict(existing)
    raise HTTPException(status_code=409, detail="Unable to reserve a unique Pages site key")


def _route_public(route: dict[str, object], settings: Settings) -> dict[str, object]:
    site_key = str(route["site_key"])
    fallback_path = f"/assets/{route['tenant_slug']}/{route['workspace_key']}/"
    internal_path = pages_entry_path(site_key)
    internal_url = pages_entry_url(site_key, settings)
    isolated_origin = pages_runtime_url(site_key, settings)
    alias_origin = pages_url(site_key, settings)
    alias_enabled = bool(route.get("public_alias_enabled", False))
    return {
        "schema": "warehouse.pages-site.v1",
        "site_key": site_key,
        "path": internal_path,
        "url": internal_url,
        "internal_url": internal_url,
        "entry_mode": "warehouse_os",
        "hostname": pages_hostname(site_key, settings) if alias_enabled else None,
        "public_alias": {
            "enabled": alias_enabled,
            "hostname": pages_hostname(site_key, settings) if alias_enabled else None,
            "url": alias_origin + "/" if alias_enabled else None,
        },
        "status": route["status"],
        "active_deployment_id": (
            str(route["active_deployment_id"])
            if route.get("active_deployment_id") is not None
            else None
        ),
        "fallback_path": fallback_path,
        "fallback_url": settings.public_origin + fallback_path,
        "runtime": {
            "delivery": "static_assets",
            "compute": "browser",
            "idle_server_memory": "near_zero",
            "database": "platform_api",
        },
        "database_origin": isolated_origin,
        "security_boundary": {
            "shell_origin": settings.public_origin,
            "runtime_origin": isolated_origin,
            "isolated_from_warehouse_session": True,
        },
        "config": route.get("config") or {},
    }


def get_pages_site(
    credential: WorkspaceCredential, settings: Settings | None = None
) -> dict[str, object]:
    credential.require("workspace:read")
    configured = settings or get_settings()
    with tenant_session(credential.tenant_id) as session:
        route = ensure_pages_route(session, credential.tenant_id, credential.workspace_id)
    return {
        "ok": True,
        "site": _route_public(route, configured),
        "mutation_workflow": {
            "site_name": "PUT /api/workspaces/v1/pages",
            "source": "create a new immutable source version",
            "preview": "deploy and verify without replacing active traffic",
            "publish": "activate only a healthy deployment",
            "active_code_editable_in_place": False,
        },
    }


def configure_pages_site(
    credential: WorkspaceCredential,
    payload: dict[str, object],
    settings: Settings | None = None,
) -> dict[str, object]:
    credential.require("deploy:write")
    configured = settings or get_settings()
    requested = validate_site_key(payload.get("site_key"))
    requested_alias = payload.get("public_alias_enabled")
    if requested_alias is not None and not isinstance(requested_alias, bool):
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "invalid_pages_public_alias_enabled",
                "message": "public_alias_enabled must be a boolean",
            },
        )
    previous_key = ""
    previous_alias = False
    database_origin_state: dict[str, object] = {
        "project_present": False,
        "origin_updated": False,
        "enabled": False,
    }
    try:
        with tenant_session(credential.tenant_id) as session:
            route = ensure_pages_route(session, credential.tenant_id, credential.workspace_id)
            previous_key = str(route["site_key"])
            previous_alias = bool(route.get("public_alias_enabled", False))
            alias_enabled = previous_alias if requested_alias is None else requested_alias
            with session.begin_nested():
                updated = (
                    session.execute(
                        text(
                            """
                            UPDATE platform.pages_routes
                            SET site_key=:site_key,
                                public_alias_enabled=:public_alias_enabled
                            WHERE tenant_id=:tenant_id AND workspace_id=:workspace_id
                            RETURNING *
                            """
                        ),
                        {
                            "site_key": requested,
                            "public_alias_enabled": alias_enabled,
                            "tenant_id": credential.tenant_id,
                            "workspace_id": credential.workspace_id,
                        },
                    )
                    .mappings()
                    .one()
                )
            previous_origin = pages_runtime_url(previous_key, configured)
            requested_origin = pages_runtime_url(requested, configured)
            browser_app = (
                session.execute(
                    text(
                        """
                        SELECT id,enabled,allowed_origins
                        FROM digital_asset.database_browser_apps
                        WHERE workspace_id=:workspace_id
                        FOR UPDATE
                        """
                    ),
                    {"workspace_id": credential.workspace_id},
                )
                .mappings()
                .one_or_none()
            )
            if browser_app is not None:
                origins = [str(item) for item in browser_app["allowed_origins"]]
                origins_changed = False
                if previous_key != requested and previous_origin in origins:
                    origins = [
                        requested_origin if item == previous_origin else item for item in origins
                    ]
                    origins = list(dict.fromkeys(origins))
                    origins_changed = True
                    session.execute(
                        text(
                            """
                            UPDATE digital_asset.database_browser_sessions
                            SET revoked_at=now()
                            WHERE browser_app_id=:browser_app_id
                              AND origin=:origin AND revoked_at IS NULL
                            """
                        ),
                        {
                            "browser_app_id": browser_app["id"],
                            "origin": previous_origin,
                        },
                    )
                elif requested_origin not in origins and len(origins) < 20:
                    origins.append(requested_origin)
                    origins_changed = True
                if origins_changed:
                    session.execute(
                        text(
                            """
                            UPDATE digital_asset.database_browser_apps
                            SET allowed_origins=:origins,revision=revision+1
                            WHERE id=:id
                            """
                        ),
                        {"id": browser_app["id"], "origins": origins},
                    )
                    database_origin_state["origin_updated"] = True
                database_origin_state.update(
                    {
                        "project_present": True,
                        "enabled": bool(browser_app["enabled"]),
                        "origin_allowed": requested_origin in origins,
                    }
                )
            session.execute(
                text(
                    """
                    INSERT INTO audit.events(tenant_id, event_type, payload)
                    VALUES (
                      :tenant_id, 'platform.pages_site_configured',
                      CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "tenant_id": credential.tenant_id,
                    "payload": json.dumps(
                        {
                            "workspace_id": str(credential.workspace_id),
                            "credential_id": str(credential.credential_id),
                            "previous_site_key": previous_key,
                            "site_key": requested,
                            "public_alias_enabled": alias_enabled,
                            "database_origin": database_origin_state,
                        }
                    ),
                },
            )
    except IntegrityError as exc:
        diagnostic = getattr(getattr(exc, "orig", None), "diag", None)
        if getattr(diagnostic, "constraint_name", None) != "pages_routes_site_key_key":
            raise
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "pages_site_key_unavailable",
                "site_key": requested,
                "message": "This Pages site name is already reserved",
            },
        ) from exc
    invalidate_pages_route_cache()
    return {
        "ok": True,
        "changed": (
            previous_key != requested
            or previous_alias != bool(updated.get("public_alias_enabled", False))
        ),
        "site": _route_public(dict(updated), configured),
        "database_origin_action": {
            "required": bool(
                database_origin_state["project_present"]
                and database_origin_state["enabled"]
                and not database_origin_state.get("origin_allowed")
            ),
            "origin": pages_runtime_url(requested, configured),
            "reason": (
                "The Warehouse OS entry embeds an isolated runtime origin; browser "
                "database projects keep using its exact-origin allowlist"
            ),
            **database_origin_state,
        },
    }


def mark_pages_deployment_active(
    session: Session,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    deployment_id: UUID,
) -> None:
    set_pages_deployment_pointer(
        session,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        deployment_id=deployment_id,
    )


def set_pages_deployment_pointer(
    session: Session,
    *,
    tenant_id: UUID,
    workspace_id: UUID,
    deployment_id: UUID | str | None,
) -> None:
    ensure_pages_route(session, tenant_id, workspace_id)
    session.execute(
        text(
            """
            UPDATE platform.pages_routes
            SET active_deployment_id=CAST(:deployment_id AS uuid),
                status=CASE WHEN CAST(:deployment_id AS uuid) IS NULL
                  THEN 'reserved' ELSE 'active' END
            WHERE tenant_id=:tenant_id AND workspace_id=:workspace_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "deployment_id": str(deployment_id) if deployment_id is not None else None,
        },
    )
    invalidate_pages_route_cache()


def pages_route_for_workspace(workspace_id: object) -> dict[str, object] | None:
    try:
        parsed = UUID(str(workspace_id))
    except (TypeError, ValueError):
        return None
    with system_session() as session:
        row = (
            session.execute(
                text("SELECT * FROM platform.pages_routes WHERE workspace_id=:workspace_id"),
                {"workspace_id": parsed},
            )
            .mappings()
            .one_or_none()
        )
    return dict(row) if row is not None else None


def workspace_pages_entry_fields(
    tenant_slug: str,
    row: dict[str, object],
    settings: Settings | None = None,
) -> dict[str, object]:
    configured = settings or get_settings()
    fallback_path = f"/assets/{tenant_slug}/{row['workspace_key']}/"
    route = row.get("_pages_route")
    if not isinstance(route, dict) and row.get("pages_site_key"):
        route = {
            "site_key": row["pages_site_key"],
            "tenant_slug": tenant_slug,
            "workspace_key": row["workspace_key"],
            "status": row.get("pages_status") or "reserved",
            "active_deployment_id": row.get("pages_active_deployment_id"),
            "public_alias_enabled": row.get("pages_public_alias_enabled", False),
            "config": {},
        }
    if not isinstance(route, dict):
        route = pages_route_for_workspace(row.get("id") or row.get("uuid"))
    if route is None or route.get("status") == "disabled":
        entry = configured.public_origin + fallback_path
        return {
            "entry_path": fallback_path,
            "entry_url": entry,
            "hosting_url": entry,
            "hosting_url_status": "legacy",
            "public_path": fallback_path,
            "application_url": row.get("public_url"),
            "entry_kind": ("deployed_application" if row.get("public_url") else "workspace_status"),
        }
    public = _route_public(route, configured)
    return {
        "entry_path": public["path"],
        "entry_url": public["url"],
        "hosting_url": public["url"],
        "hosting_url_status": public["status"],
        "public_path": public["path"],
        "fallback_path": fallback_path,
        "fallback_url": public["fallback_url"],
        "pages": public,
        "pages_site_key": public["site_key"],
        "pages_hostname": public["hostname"],
        "application_url": row.get("public_url"),
        "entry_kind": (
            "deployed_application" if route.get("active_deployment_id") else "workspace_status"
        ),
    }


def resolve_pages_site_key(site_key: str) -> dict[str, object] | None:
    candidate = str(site_key or "").strip().lower()
    if not SITE_KEY_RE.fullmatch(candidate):
        return None
    cache_key = f"site:{candidate}"
    now = time.monotonic()
    with _route_cache_lock:
        cached = _route_cache.get(cache_key)
        if cached is not None and now - cached[0] <= _ROUTE_CACHE_SECONDS:
            return dict(cached[1]) if cached[1] is not None else None
    with system_session() as session:
        row = (
            session.execute(
                text(
                    "SELECT * FROM platform.pages_routes "
                    "WHERE site_key=:site_key AND status<>'disabled'"
                ),
                {"site_key": candidate},
            )
            .mappings()
            .one_or_none()
        )
    route = dict(row) if row is not None else None
    with _route_cache_lock:
        if len(_route_cache) >= 2_048:
            _route_cache.clear()
        _route_cache[cache_key] = (now, route)
    return dict(route) if route is not None else None


def resolve_pages_hostname(
    hostname: str, settings: Settings | None = None
) -> dict[str, object] | None:
    configured = settings or get_settings()
    site_key = pages_hostname_site_key(hostname, configured) or pages_runtime_hostname_site_key(
        hostname, configured
    )
    return resolve_pages_site_key(site_key) if site_key is not None else None


def _source_descriptor(
    credential: WorkspaceCredential, source_ref: str | None
) -> dict[str, object]:
    credential.require("deploy:read")
    reference = str(source_ref or "").strip()
    with tenant_session(credential.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT v.id, v.legacy_id, v.version_no, v.created_at,
                           ar.filename, ar.content_type, ar.size_bytes, ar.sha256,
                           ar.storage_provider, ar.object_key,
                           active.source_version_id AS active_source_version_id
                    FROM digital_asset.workspaces AS workspace
                    JOIN digital_asset.asset_versions AS v
                      ON v.asset_id=workspace.asset_id
                    JOIN digital_asset.artifacts AS ar
                      ON ar.version_id=v.id AND ar.storage_role='code'
                     AND ar.state='verified'
                    LEFT JOIN digital_asset.deployments AS active
                      ON active.id=workspace.active_deployment_id
                    WHERE workspace.id=:workspace_id
                      AND (
                        CAST(:reference AS text)=''
                        OR CAST(v.id AS text)=:reference
                        OR CAST(v.legacy_id AS text)=:reference
                      )
                    ORDER BY
                      CASE WHEN v.id=active.source_version_id THEN 0 ELSE 1 END,
                      v.created_at DESC, ar.created_at DESC
                    LIMIT 1
                    """
                ),
                {
                    "workspace_id": credential.workspace_id,
                    "reference": reference,
                },
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Source version not found")
    return dict(row)


def _source_path(descriptor: dict[str, object], settings: Settings) -> Path:
    for store in object_store_read_candidates(settings, str(descriptor["storage_provider"])):
        candidate = store.path_for(str(descriptor["object_key"]))
        if candidate.is_file():
            return candidate
    raise HTTPException(status_code=404, detail="Source object is unavailable")


def _safe_archive_path(value: str) -> PurePosixPath:
    clean = str(value or "").replace("\\", "/").strip("/")
    path = PurePosixPath(clean)
    if not clean or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise HTTPException(status_code=422, detail="Unsafe source file path")
    return path


def _archive_members(path: Path) -> list[ArchiveMember]:
    raw_members: list[tuple[PurePosixPath, int]] = []
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                mode = item.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise HTTPException(status_code=422, detail="Source archive contains a link")
                raw_members.append((_safe_archive_path(item.filename), int(item.file_size)))
    elif tarfile.is_tarfile(path):
        with tarfile.open(path, mode="r:*") as archive:
            for item in archive:
                if item.isfile():
                    raw_members.append((_safe_archive_path(item.name), int(item.size)))
                elif item.issym() or item.islnk() or item.isdev() or item.isfifo():
                    raise HTTPException(
                        status_code=422, detail="Source archive contains a special file"
                    )
    else:
        raise HTTPException(status_code=422, detail="Source must be a ZIP or TAR archive")
    meaningful = [
        item
        for item in raw_members
        if item[0].parts[0] != "__MACOSX" and item[0].name != ".DS_Store"
    ]
    wrapper = None
    if meaningful and all(len(member.parts) > 1 for member, _size in meaningful):
        roots = {member.parts[0] for member, _size in meaningful}
        wrapper = next(iter(roots)) if len(roots) == 1 else None
    members: list[ArchiveMember] = []
    seen: set[str] = set()
    for raw, size in meaningful:
        exposed = PurePosixPath(*raw.parts[1:]) if wrapper else raw
        exposed_path = exposed.as_posix()
        if exposed_path in seen:
            raise HTTPException(status_code=422, detail="Source archive has duplicate paths")
        seen.add(exposed_path)
        members.append(ArchiveMember(exposed_path, raw.as_posix(), size))
    return sorted(members, key=lambda item: item.path.lower())


def _is_sensitive(path: str) -> bool:
    parsed = PurePosixPath(path)
    lowered_parts = tuple(part.lower() for part in parsed.parts)
    name = parsed.name.lower()
    return bool(
        ".git" in lowered_parts
        or name == ".env"
        or name.startswith(".env.")
        or name in _SENSITIVE_NAMES
        or parsed.stem.lower() in {"credential", "credentials", "private-key", "secret", "secrets"}
        or parsed.suffix.lower() in _SENSITIVE_SUFFIXES
        or any(part in {"credentials", "private-keys", "secrets"} for part in lowered_parts)
    )


def _file_category(path: str) -> str:
    parsed = PurePosixPath(path)
    extension = parsed.suffix.lower()
    lowered = path.lower()
    if extension in _IMAGE_EXTENSIONS or extension == ".svg":
        return "design_asset"
    if extension in {".css", ".scss"}:
        return "style"
    if extension in {".html", ".htm", ".astro", ".vue"}:
        return "layout"
    if extension in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
        return "component"
    if extension in (
        _PYTHON_SOURCE_EXTENSIONS | _JVM_SOURCE_EXTENSIONS | _NATIVE_SOURCE_EXTENSIONS
    ):
        return "compute_source"
    if extension in {".json", ".yaml", ".yml", ".toml", ".ini"}:
        return "configuration"
    if extension in {".md", ".mdx", ".txt"}:
        return "documentation"
    if "design" in lowered or "figma" in lowered or "token" in lowered:
        return "design_source"
    return "other"


def _file_access(member: ArchiveMember) -> tuple[bool, str | None, int]:
    extension = PurePosixPath(member.path).suffix.lower()
    if _is_sensitive(member.path):
        return False, None, 0
    if extension in _TEXT_EXTENSIONS:
        return member.size_bytes <= MAX_TEXT_FILE_BYTES, "utf-8", MAX_TEXT_FILE_BYTES
    if extension in _IMAGE_EXTENSIONS:
        return member.size_bytes <= MAX_IMAGE_FILE_BYTES, "base64", MAX_IMAGE_FILE_BYTES
    return False, None, 0


def _read_archive_member(path: Path, raw_path: str) -> bytes:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return archive.read(raw_path)
    with tarfile.open(path, mode="r:*") as archive:
        item = archive.getmember(raw_path)
        stream = archive.extractfile(item)
        if stream is None:
            raise HTTPException(status_code=404, detail="Source file is unavailable")
        return stream.read()


def _source_public(descriptor: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(descriptor["id"]),
        "legacy_id": int(descriptor["legacy_id"]),
        "version_no": descriptor["version_no"],
        "filename": descriptor["filename"],
        "size_bytes": int(descriptor["size_bytes"]),
        "sha256": descriptor["sha256"],
        "active": str(descriptor.get("active_source_version_id") or "") == str(descriptor["id"]),
    }


def _compute_members(
    members: list[ArchiveMember], extensions: frozenset[str]
) -> list[ArchiveMember]:
    return [
        member
        for member in members
        if PurePosixPath(member.path).suffix.lower() in extensions
        and not _is_sensitive(member.path)
        and not _COMPUTE_IGNORED_PARTS.intersection(
            part.lower() for part in PurePosixPath(member.path).parts
        )
    ]


def _pages_manifest_compute_facts(
    archive_path: Path,
    members: list[ArchiveMember],
) -> dict[str, object]:
    facts: dict[str, object] = {
        "declared": False,
        "readable": False,
        "web_compute": None,
        "data_mode": None,
        "function_count": 0,
        "device_mode": None,
    }
    member = next(
        (
            candidate
            for candidate in members
            if candidate.path.lower() == PAGES_APP_MANIFEST_FILENAME
        ),
        None,
    )
    if member is None:
        return facts
    facts["declared"] = True
    try:
        payload = json.loads(_read_archive_member(archive_path, member.raw_path))
    except (UnicodeDecodeError, json.JSONDecodeError, OSError):
        return facts
    if not isinstance(payload, dict):
        return facts
    web = payload.get("web") if isinstance(payload.get("web"), dict) else {}
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    device = payload.get("device") if isinstance(payload.get("device"), dict) else {}
    functions = payload.get("functions") if isinstance(payload.get("functions"), list) else []
    facts.update(
        {
            "readable": True,
            "web_compute": web.get("compute"),
            "data_mode": data.get("mode"),
            "function_count": len(functions),
            "device_mode": device.get("mode"),
        }
    )
    return facts


def _compute_placement_advice(
    archive_path: Path,
    members: list[ArchiveMember],
    *,
    has_index: bool,
) -> dict[str, object]:
    """Return deterministic advice; never rewrite code or change a deployment."""

    browser = _compute_members(members, _BROWSER_SOURCE_EXTENSIONS)
    python = _compute_members(members, _PYTHON_SOURCE_EXTENSIONS)
    jvm = _compute_members(members, _JVM_SOURCE_EXTENSIONS)
    native = _compute_members(members, _NATIVE_SOURCE_EXTENSIONS)
    manifest = _pages_manifest_compute_facts(archive_path, members)
    function_count = int(manifest["function_count"])
    server_signals = bool(python or jvm or native or function_count)
    if has_index and not server_signals:
        recommended_mode = "pure_static"
    elif has_index:
        recommended_mode = "static_with_on_demand_api"
    else:
        recommended_mode = "on_demand_or_dedicated_runtime_review"

    def evidence(values: list[ArchiveMember]) -> list[str]:
        return [item.path for item in values[:8]]

    items: list[dict[str, object]] = []
    if has_index:
        items.append(
            {
                "id": "keep-browser-safe-work-client-side",
                "recommended_plane": "browser_javascript_typescript",
                "scope": (
                    "rendering, validation, filtering, sorting and non-secret "
                    "deterministic calculations"
                ),
                "reason": (
                    "These operations can run on the user's device without reserving "
                    "server Runtime memory"
                ),
                "evidence": evidence(browser),
                "automatic_change": False,
            }
        )
    if python:
        items.extend(
            [
                {
                    "id": "review-pure-python-for-browser",
                    "recommended_plane": "browser_javascript_typescript_or_webassembly",
                    "scope": "pure, stateless Python modules without secrets or privileged I/O",
                    "reason": (
                        "Small pure calculations can be rewritten in JavaScript/TypeScript; "
                        "scientific code may use a measured Pyodide/WebAssembly build"
                    ),
                    "evidence": evidence(python),
                    "constraints": [
                        "measure initial download size and mobile memory",
                        "do not move secrets, authorization or shared writes into the browser",
                    ],
                    "automatic_change": False,
                },
                {
                    "id": "retain-privileged-python-on-demand",
                    "recommended_plane": "scale_to_zero_function",
                    "scope": "Python that uses secrets, authentication or privileged shared data",
                    "reason": (
                        "The server boundary protects credentials while scale-to-zero removes "
                        "idle Runtime residency"
                    ),
                    "evidence": evidence(python),
                    "automatic_change": False,
                },
            ]
        )
    if jvm:
        items.append(
            {
                "id": "keep-jvm-out-of-ordinary-browser",
                "recommended_plane": "optional_local_agent_or_on_demand_runtime",
                "scope": "Java, Kotlin or Scala code requiring a JVM",
                "reason": (
                    "Ordinary browsers execute JavaScript, not Java; JVM code needs an "
                    "installed local process or a server Runtime"
                ),
                "evidence": evidence(jvm),
                "automatic_change": False,
            }
        )
    if native:
        items.append(
            {
                "id": "review-native-code-for-webassembly",
                "recommended_plane": "browser_webassembly_or_on_demand_runtime",
                "scope": "deterministic Rust, C/C++ or Go computations",
                "reason": (
                    "WebAssembly can move suitable CPU work to the user device, but file, "
                    "network and device access still require an explicit capability boundary"
                ),
                "evidence": evidence(native),
                "automatic_change": False,
            }
        )
    if manifest.get("data_mode") == "platform_api":
        items.append(
            {
                "id": "keep-shared-data-on-platform-api",
                "recommended_plane": "platform_database_api",
                "scope": "persistent shared records, authorization and synchronization",
                "reason": "Browser clients must not receive database credentials",
                "evidence": [PAGES_APP_MANIFEST_FILENAME],
                "automatic_change": False,
            }
        )
    if function_count:
        items.append(
            {
                "id": "keep-declared-privileged-functions-on-demand",
                "recommended_plane": "scale_to_zero_function",
                "scope": f"{function_count} function declaration(s)",
                "reason": (
                    "Declared privileged operations retain a server trust boundary only on demand"
                ),
                "evidence": [PAGES_APP_MANIFEST_FILENAME],
                "automatic_change": False,
            }
        )
    return {
        "schema": "warehouse.compute-placement-advice.v1",
        "advisory_only": True,
        "automatic_code_rewrite": False,
        "confirmation_required_before_new_release": True,
        "recommended_hosting_mode": recommended_mode,
        "confidence": "high" if manifest["readable"] else "medium",
        "detected": {
            "browser_entry": has_index,
            "browser_source_files": len(browser),
            "python_source_files": len(python),
            "jvm_source_files": len(jvm),
            "native_or_wasm_source_files": len(native),
            "pages_manifest": manifest,
        },
        "items": items,
        "guardrails": [
            "JavaScript and Java are different runtimes; an ordinary browser has no JVM",
            (
                "never move secrets, authorization decisions or database credentials "
                "into browser assets"
            ),
            (
                "measure bundle size, startup latency and mobile memory before adopting "
                "Python/WASM in-browser"
            ),
            "publish accepted changes as a new immutable source and verified release",
        ],
    }


def pages_design_context(
    credential: WorkspaceCredential,
    settings: Settings,
    *,
    source_ref: str | None = None,
) -> dict[str, object]:
    descriptor = _source_descriptor(credential, source_ref)
    path = _source_path(descriptor, settings)
    members = _archive_members(path)
    visible: list[dict[str, object]] = []
    sensitive_count = 0
    for member in members[:MAX_DESIGN_FILES]:
        readable, encoding, limit = _file_access(member)
        if _is_sensitive(member.path):
            sensitive_count += 1
            continue
        visible.append(
            {
                "path": member.path,
                "category": _file_category(member.path),
                "size_bytes": member.size_bytes,
                "readable": readable,
                "encoding": encoding,
                "read_limit_bytes": limit or None,
            }
        )
    paths = {str(item["path"]).lower() for item in visible}
    has_index = any(PurePosixPath(item).name == "index.html" for item in paths)
    has_styles = any(PurePosixPath(item).suffix in {".css", ".scss"} for item in paths)
    has_manifest = "warehouse.hosting.json" in paths
    site = get_pages_site(credential, settings)["site"]
    recommendations: list[dict[str, object]] = []
    if not has_manifest:
        recommendations.append(
            {
                "id": "declare-hosting-contract",
                "title": "Add warehouse.hosting.json",
                "reason": "Make build output and browser/runtime intent machine-verifiable",
            }
        )
    if not has_index:
        recommendations.append(
            {
                "id": "add-static-entry",
                "title": "Add an index.html entry",
                "reason": "A Pages release needs a deterministic browser entry point",
            }
        )
    if not has_styles:
        recommendations.append(
            {
                "id": "centralize-design-tokens",
                "title": "Create a shared style and design-token layer",
                "reason": "AI and users can then change typography, color and spacing consistently",
            }
        )
    recommendations.extend(
        [
            {
                "id": "verify-browser-quality",
                "title": "Verify responsive layout, keyboard access and reduced motion",
                "reason": "Pages compute and render on user devices with different capabilities",
            },
            {
                "id": "bind-exact-database-origin",
                "title": "Allow the exact Pages origin on the database project",
                "reason": "Browser database access remains deny-by-default and exact-origin scoped",
                "origin": site["database_origin"],
            },
        ]
    )
    compute_placement = _compute_placement_advice(path, members, has_index=has_index)
    recommendations.append(
        {
            "id": "review-compute-placement",
            "title": "Review where each workload should run",
            "reason": (
                "Prefer browser compute and the platform Data API when safe; retain "
                "privileged work in scale-to-zero or dedicated Runtime boundaries"
            ),
            "recommended_hosting_mode": compute_placement["recommended_hosting_mode"],
            "advisory_only": True,
        }
    )
    source_id = str(descriptor["id"])
    return {
        "ok": True,
        "schema": "warehouse.pages-design-context.v1",
        "site": site,
        "source": _source_public(descriptor),
        "files": visible,
        "file_count": len(visible),
        "truncated": len(members) > MAX_DESIGN_FILES,
        "excluded_sensitive_files": sensitive_count,
        "read_file": ("/api/workspaces/v1/pages/files/{path}?source_ref=" + source_id),
        "application_package": {
            "schema": PAGES_APP_SCHEMA,
            "manifest_filename": PAGES_APP_MANIFEST_FILENAME,
            "contract": ("/api/workspaces/v1/pages/package?source_ref=" + source_id),
            "download": ("/api/workspaces/v1/pages/package/download?source_ref=" + source_id),
        },
        "recommendations": recommendations,
        "compute_placement": compute_placement,
        "change_policy": {
            "active_release_mutable": False,
            "workspace_upload": "POST /api/workspaces/v1/sources/upload",
            "hosting_session_upload": ("POST /api/hosting/v2/sessions/{session_id}/sources"),
            "workflow": [
                "read selected code/design files",
                "create a modified source archive",
                "upload as a new immutable source version",
                "deploy and verify a preview",
                "activate the healthy deployment",
            ],
        },
    }


def pages_source_file(
    credential: WorkspaceCredential,
    settings: Settings,
    file_path: str,
    *,
    source_ref: str | None = None,
) -> dict[str, object]:
    requested = _safe_archive_path(file_path).as_posix()
    descriptor = _source_descriptor(credential, source_ref)
    archive_path = _source_path(descriptor, settings)
    member = next(
        (item for item in _archive_members(archive_path) if item.path == requested),
        None,
    )
    if member is None or _is_sensitive(member.path):
        raise HTTPException(status_code=404, detail="Source file not found")
    readable, encoding, limit = _file_access(member)
    if not readable:
        raise HTTPException(
            status_code=413 if limit and member.size_bytes > limit else 415,
            detail={
                "reason": "source_file_not_inline_readable",
                "path": requested,
                "size_bytes": member.size_bytes,
                "max_bytes": limit or None,
                "next_action": "download the governed full source archive",
            },
        )
    content = _read_archive_member(archive_path, member.raw_path)
    if encoding == "utf-8":
        try:
            rendered = content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=415, detail="Source file is not valid UTF-8") from exc
    else:
        rendered = base64.b64encode(content).decode("ascii")
    return {
        "ok": True,
        "schema": "warehouse.pages-source-file.v1",
        "source": _source_public(descriptor),
        "file": {
            "path": member.path,
            "category": _file_category(member.path),
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "encoding": encoding,
            "content": rendered,
        },
        "change_policy": "upload changes as a new source version; never edit active code",
    }
