"""Device-first Pages migration and non-secret runtime distribution contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session
from app.services.database_browser_gateway import (
    browser_access_configuration,
    configure_browser_access,
)
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    workspace_asset_identity,
)
from app.services.pages_runtime import (
    ensure_pages_route,
    invalidate_pages_route_cache,
    pages_runtime_url,
)
from app.services.workspace_deployments import workspace_source_download_target

if TYPE_CHECKING:
    from app.api.deps import ActorContext


DEVICE_AGENT_PORT = 47821
DEVICE_AGENT_FILENAME = "warehouse-device-agent.py"
PAGES_DEVICE_SCHEMA = "warehouse.pages-device-runtime.v1"

_DEFAULT_STATIC_ROOTS = ("frontend", "site", ".", "dist", "build", "public")
_COLLECTIONS_BY_WORKSPACE: dict[str, tuple[str, ...]] = {
    "pd-detection": ("history", "measurements", "exports"),
    "bonfire-coordination": ("coordination", "nodes", "events"),
    "biu-casework": ("cases", "attachments", "agent_runs"),
    "mk7-workspace": ("resources", "modules", "search_history"),
    "mk53-voyager": ("documents", "profiles", "invites", "uploads"),
    "mk4-workspace": ("banks", "classes", "chats", "user_state"),
    "bonfire-qa": ("banks", "classes", "chats", "user_state"),
    "ai-architecture-platform": ("runtime_sessions", "runtime_events", "projects"),
    "hosting-fabric-container-smoke": ("diagnostics", "runtime_events"),
}


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


def _workspace_credential(
    actor: ActorContext,
    workspace_ref: object,
    *,
    manage: bool,
) -> tuple[dict[str, object], WorkspaceCredential]:
    identity = workspace_asset_identity(actor, workspace_ref)
    workspace = identity["workspace"]
    scopes = {"workspace:read", "deploy:read"}
    if manage:
        scopes.add("deploy:write")
    credential = WorkspaceCredential(
        tenant_id=actor.tenant_id,
        workspace_id=UUID(str(workspace["uuid"])),
        credential_id=actor.user_id,
        scopes=frozenset(scopes),
        label="warehouse-device-runtime",
        key_kind="account_session",
        parent_credential_id=None,
    )
    return workspace, credential


def _active_release(
    actor: ActorContext,
    workspace_id: UUID,
) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT d.id,d.source_version_id,d.release_digest,d.status,d.health,
                           d.runtime_profile_key,d.runtime_state,d.result,d.requested_config,
                           w.workspace_key,w.config AS workspace_config,
                           component.runtime AS component_runtime,
                           component.entrypoint,component.build_command,
                           component.start_command,component.config AS component_config,
                           ar.filename,ar.size_bytes,ar.sha256,ar.content_type,
                           ar.storage_provider,ar.storage_pool_key
                    FROM digital_asset.workspaces AS w
                    LEFT JOIN digital_asset.deployments AS d
                      ON d.id=w.active_deployment_id
                    LEFT JOIN digital_asset.workspace_components AS component
                      ON component.id=d.component_id
                    LEFT JOIN digital_asset.artifacts AS ar
                      ON ar.version_id=d.source_version_id
                     AND ar.storage_role='code' AND ar.state='verified'
                    WHERE w.id=:workspace_id
                    """
                ),
                {"workspace_id": workspace_id},
            )
            .mappings()
            .one_or_none()
        )
    return dict(row) if row is not None else None


def _safe_static_root(
    release: dict[str, object] | None,
    settings: Settings,
    configured_root: object = None,
) -> dict[str, object]:
    if release is None:
        return {"available": False, "root": None, "reason": "no_active_release"}
    result = release.get("result") if isinstance(release.get("result"), dict) else {}
    runtime_rel_path = str(result.get("runtime_rel_path") or "").strip()
    if not runtime_rel_path:
        return {"available": False, "root": None, "reason": "release_files_unavailable"}
    release_root = (settings.hosted_runtime_data_root / runtime_rel_path).resolve()
    try:
        release_root.relative_to(settings.hosted_runtime_data_root.resolve())
    except ValueError:
        return {"available": False, "root": None, "reason": "unsafe_release_path"}
    candidates = []
    if configured_root not in (None, ""):
        candidates.append(str(configured_root))
    candidates.extend(value for value in _DEFAULT_STATIC_ROOTS if value not in candidates)
    for relative in candidates:
        candidate = (release_root / relative).resolve() if relative != "." else release_root
        try:
            candidate.relative_to(release_root)
        except ValueError:
            continue
        if (candidate / "index.html").is_file():
            return {
                "available": True,
                "root": relative,
                "reason": "index_detected",
                "runtime_rel_path": runtime_rel_path,
            }
    return {
        "available": False,
        "root": None,
        "reason": "no_static_index",
        "runtime_rel_path": runtime_rel_path,
    }


def pages_static_release(
    site_key: str,
    *,
    settings: Settings,
) -> dict[str, object] | None:
    """Resolve a configured Pages frontend without waking the application Runtime."""

    from app.services.pages_runtime import resolve_pages_site_key

    route = resolve_pages_site_key(site_key)
    if route is None:
        return None
    config = route.get("config") if isinstance(route.get("config"), dict) else {}
    device = (
        config.get("device_runtime")
        if isinstance(config.get("device_runtime"), dict)
        else {}
    )
    frontend = (
        config.get("static_frontend")
        if isinstance(config.get("static_frontend"), dict)
        else {}
    )
    if not bool(frontend.get("enabled")):
        return None
    configured_deployment_id = str(frontend.get("deployment_id") or "")
    active_deployment_id = str(route.get("active_deployment_id") or "")
    configured_runtime_path = str(frontend.get("runtime_rel_path") or "").strip()
    configured_root = str(frontend.get("root") or "").strip()
    if (
        configured_runtime_path
        and configured_deployment_id
        and configured_deployment_id == active_deployment_id
    ):
        relative = Path(configured_runtime_path)
        if configured_root and configured_root != ".":
            relative /= configured_root
        absolute = (settings.hosted_runtime_data_root / relative).resolve()
        try:
            absolute.relative_to(settings.hosted_runtime_data_root.resolve())
        except ValueError:
            return None
        if (absolute / "index.html").is_file():
            return {
                "kind": "static",
                "runtime_rel_path": str(relative),
                "site_key": str(route["site_key"]),
                "workspace_key": str(route["workspace_key"]),
                "device_runtime": device,
                "deployment_id": configured_deployment_id,
                "release_digest": frontend.get("release_digest"),
                "backend_fallback": frontend.get("backend_fallback")
                or "scale_to_zero",
            }
    if not active_deployment_id and bool(frontend.get("generic_fallback")):
        return {
            "kind": "generic",
            "site_key": str(route["site_key"]),
            "workspace_key": str(route["workspace_key"]),
            "device_runtime": device,
            "reason": "no_active_release",
        }
    workspace_id = UUID(str(route["workspace_id"]))
    tenant_id = UUID(str(route["tenant_id"]))
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT d.id,d.release_digest,d.result
                    FROM digital_asset.workspaces AS w
                    LEFT JOIN digital_asset.deployments AS d
                      ON d.id=COALESCE(CAST(:deployment_id AS uuid),w.active_deployment_id)
                    WHERE w.id=:workspace_id
                      AND (d.id IS NULL OR (d.status='ready' AND d.health='healthy'))
                    """
                ),
                {
                    "workspace_id": workspace_id,
                    "deployment_id": route.get("active_deployment_id"),
                },
            )
            .mappings()
            .one_or_none()
        )
    if row is None or row.get("id") is None:
        return {
            "kind": "generic",
            "site_key": str(route["site_key"]),
            "workspace_key": str(route["workspace_key"]),
            "device_runtime": device,
            "reason": "no_active_release",
        }
    release = dict(row)
    detected = _safe_static_root(release, settings, frontend.get("root"))
    if not detected["available"]:
        return {
            "kind": "generic",
            "site_key": str(route["site_key"]),
            "workspace_key": str(route["workspace_key"]),
            "device_runtime": device,
            "deployment_id": str(release["id"]),
            "release_digest": release.get("release_digest"),
            "reason": detected["reason"],
        }
    relative = Path(str(detected["runtime_rel_path"]))
    if detected["root"] != ".":
        relative /= str(detected["root"])
    return {
        "kind": "static",
        "runtime_rel_path": str(relative),
        "site_key": str(route["site_key"]),
        "workspace_key": str(route["workspace_key"]),
        "device_runtime": device,
        "deployment_id": str(release["id"]),
        "release_digest": release.get("release_digest"),
        "backend_fallback": frontend.get("backend_fallback") or "scale_to_zero",
    }


def _browser_rules(workspace_key: str) -> dict[str, object]:
    collections = {
        name: {"read": "owner", "write": "owner"}
        for name in _COLLECTIONS_BY_WORKSPACE.get(
            workspace_key,
            ("app_state", "history", "documents"),
        )
    }
    return {
        "default": {"read": "deny", "write": "deny"},
        "collections": collections,
    }


def device_runtime_manifest(
    actor: ActorContext,
    workspace_ref: object,
    *,
    settings: Settings,
) -> dict[str, object]:
    _require_read(actor)
    workspace, _credential = _workspace_credential(actor, workspace_ref, manage=False)
    workspace_id = UUID(str(workspace["uuid"]))
    release = _active_release(actor, workspace_id)
    with tenant_session(actor.tenant_id) as session:
        route = ensure_pages_route(session, actor.tenant_id, workspace_id)
    route_config = route.get("config") if isinstance(route.get("config"), dict) else {}
    frontend_config = (
        route_config.get("static_frontend")
        if isinstance(route_config.get("static_frontend"), dict)
        else {}
    )
    frontend = _safe_static_root(release, settings, frontend_config.get("root"))
    browser_project = None
    try:
        browser_project = browser_access_configuration(
            actor,
            workspace["workspace_key"],
            settings=settings,
        )["project"]
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
    source_version_id = str((release or {}).get("source_version_id") or "")
    source = None
    if source_version_id:
        source = {
            "version_id": source_version_id,
            "filename": release.get("filename"),
            "size_bytes": release.get("size_bytes"),
            "sha256": release.get("sha256"),
            "download_url": (
                f"/api/workspaces/{workspace['workspace_key']}/device-runtime/source"
            ),
        }
    workspace_config = (
        release.get("workspace_config")
        if release and isinstance(release.get("workspace_config"), dict)
        else {}
    )
    requested_config = (
        release.get("requested_config")
        if release and isinstance(release.get("requested_config"), dict)
        else {}
    )
    component_config = (
        release.get("component_config")
        if release and isinstance(release.get("component_config"), dict)
        else {}
    )
    return {
        "ok": True,
        "schema": PAGES_DEVICE_SCHEMA,
        "workspace": {
            "uuid": str(workspace_id),
            "workspace_key": workspace["workspace_key"],
            "runtime_type": workspace_config.get("runtime_type"),
        },
        "pages": {
            "site_key": route["site_key"],
            "url": settings.public_origin + f"/apps/{route['site_key']}/",
            "origin": pages_runtime_url(str(route["site_key"]), settings),
            "static_frontend": frontend,
        },
        "source": source,
        "launch": {
            "type": workspace_config.get("runtime_type"),
            "runtime": (release or {}).get("component_runtime"),
            "runtime_profile": (release or {}).get("runtime_profile_key"),
            "entrypoint": (release or {}).get("entrypoint"),
            "build_command": (release or {}).get("build_command"),
            "start_command": (release or {}).get("start_command"),
            "health_path": requested_config.get("health_path")
            or component_config.get("health_path")
            or "/",
            "port": requested_config.get("port")
            or component_config.get("port")
            or 8080,
        },
        "device_agent": {
            "download_url": "/api/device-runtime/v1/agent.py",
            "filename": DEVICE_AGENT_FILENAME,
            "loopback_origin": f"http://127.0.0.1:{DEVICE_AGENT_PORT}",
            "workspace_health_path": (
                f"/v1/workspaces/{workspace['workspace_key']}/health"
            ),
            "authentication": "account_or_workspace_key_outside_browser",
            "database_credentials_exposed": False,
        },
        "fallback": {
            "mode": "scale_to_zero",
            "runtime_state": (release or {}).get("runtime_state"),
            "public_service_interruption": False,
        },
        "database_api": browser_project,
        "credentials_exposed": False,
    }


def device_runtime_source_target(
    actor: ActorContext,
    workspace_ref: object,
) -> dict[str, object]:
    _require_read(actor)
    workspace, credential = _workspace_credential(actor, workspace_ref, manage=False)
    release = _active_release(actor, credential.workspace_id)
    source_version_id = str((release or {}).get("source_version_id") or "")
    if not source_version_id:
        raise HTTPException(status_code=404, detail="Active source is unavailable")
    descriptor = workspace_source_download_target(credential, source_version_id)
    descriptor["workspace_key"] = workspace["workspace_key"]
    return descriptor


def migrate_workspace_to_device_pages(
    actor: ActorContext,
    workspace_ref: object,
    *,
    settings: Settings,
    execute: bool,
) -> dict[str, object]:
    if execute:
        _require_manage(actor)
    else:
        _require_read(actor)
    workspace, credential = _workspace_credential(actor, workspace_ref, manage=execute)
    workspace_id = credential.workspace_id
    release = _active_release(actor, workspace_id)
    with tenant_session(actor.tenant_id) as session:
        route = ensure_pages_route(session, actor.tenant_id, workspace_id)
    current_config = route.get("config") if isinstance(route.get("config"), dict) else {}
    current_frontend = (
        current_config.get("static_frontend")
        if isinstance(current_config.get("static_frontend"), dict)
        else {}
    )
    frontend = _safe_static_root(release, settings, current_frontend.get("root"))
    desired_config = {
        **current_config,
        "delivery": "static_assets",
        "compute": "browser",
        "database": "platform_api",
        "static_frontend": {
            "enabled": True,
            "root": frontend.get("root"),
            "runtime_rel_path": frontend.get("runtime_rel_path"),
            "deployment_id": str((release or {}).get("id") or "") or None,
            "release_digest": (release or {}).get("release_digest"),
            "generic_fallback": not bool(frontend.get("available")),
            "backend_fallback": "scale_to_zero",
        },
        "device_runtime": {
            "enabled": True,
            "preference": "local_first",
            "loopback_origin": f"http://127.0.0.1:{DEVICE_AGENT_PORT}",
            "fallback": "scale_to_zero",
        },
    }
    origin = pages_runtime_url(str(route["site_key"]), settings)
    existing_browser: dict[str, object] | None = None
    try:
        existing_browser = browser_access_configuration(
            actor,
            workspace["workspace_key"],
            settings=settings,
        )["project"]
    except HTTPException as exc:
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise
    existing_origins = [
        str(item) for item in (existing_browser or {}).get("allowed_origins") or []
    ]
    desired_origins = list(dict.fromkeys([*existing_origins, origin]))
    if execute and origin not in existing_origins and len(existing_origins) >= 20:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "database_browser_origin_limit_reached",
                "origin": origin,
                "origin_limit": 20,
                "next_action": "remove an obsolete exact origin and retry",
            },
        )
    recommended_rules = _browser_rules(str(workspace["workspace_key"]))
    existing_rules = (
        existing_browser.get("rules")
        if existing_browser and isinstance(existing_browser.get("rules"), dict)
        else {}
    )
    existing_collections = (
        existing_rules.get("collections")
        if isinstance(existing_rules.get("collections"), dict)
        else {}
    )
    desired_rules = {
        **existing_rules,
        "default": {"read": "deny", "write": "deny"},
        "collections": {
            **recommended_rules["collections"],
            **existing_collections,
        },
    }
    database_plan: dict[str, object] = {
        "enabled": True,
        "origin": origin,
        "allowed_origins": desired_origins,
        "rules": desired_rules,
    }
    database_result: dict[str, object] | None = None
    database_error: dict[str, object] | None = None
    database_changed: bool | None = None
    desired_deployment_id = str((release or {}).get("id") or "")
    pages_changed = bool(
        current_config != desired_config
        or (
            desired_deployment_id
            and str(route.get("active_deployment_id") or "") != desired_deployment_id
        )
    )
    if execute and pages_changed:
        with tenant_session(actor.tenant_id) as session:
            updated = (
                session.execute(
                    text(
                        """
                        UPDATE platform.pages_routes
                        SET config=CAST(:config AS jsonb),
                            active_deployment_id=COALESCE(:deployment_id,active_deployment_id),
                            status=CASE WHEN :deployment_id IS NULL THEN status ELSE 'active' END
                        WHERE tenant_id=:tenant_id AND workspace_id=:workspace_id
                        RETURNING id
                        """
                    ),
                    {
                        "config": json.dumps(desired_config, separators=(",", ":")),
                        "deployment_id": (release or {}).get("id"),
                        "tenant_id": actor.tenant_id,
                        "workspace_id": workspace_id,
                    },
                )
                .mappings()
                .one()
            )
            session.execute(
                text(
                    """
                    INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
                    VALUES (
                      :tenant_id,:actor_user_id,'platform.pages_device_migrated',
                      CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "actor_user_id": actor.user_id,
                    "payload": json.dumps(
                        {
                            "route_id": str(updated["id"]),
                            "workspace_id": str(workspace_id),
                            "workspace_key": workspace["workspace_key"],
                            "static_frontend": desired_config["static_frontend"],
                            "device_runtime": desired_config["device_runtime"],
                        },
                        separators=(",", ":"),
                    ),
                },
            )
        invalidate_pages_route_cache()
    if execute:
        browser_unchanged = bool(
            existing_browser
            and bool(existing_browser.get("enabled"))
            and existing_origins == desired_origins
            and existing_rules == desired_rules
        )
        try:
            if browser_unchanged:
                database_result = existing_browser
                database_changed = False
            else:
                database_result = configure_browser_access(
                    actor,
                    workspace["workspace_key"],
                    {
                        "enabled": True,
                        "allowed_origins": desired_origins,
                        "rules": database_plan["rules"],
                        "access_token_ttl_seconds": int(
                            (existing_browser or {}).get("access_token_ttl_seconds")
                            or 900
                        ),
                        "refresh_session_ttl_days": int(
                            (existing_browser or {}).get("refresh_session_ttl_days")
                            or 30
                        ),
                        "rate_limit_per_minute": int(
                            (existing_browser or {}).get("rate_limit_per_minute")
                            or 300
                        ),
                    },
                    settings=settings,
                )["project"]
                database_changed = True
        except HTTPException as exc:
            if exc.status_code not in {status.HTTP_404_NOT_FOUND, status.HTTP_409_CONFLICT}:
                raise
            database_error = {
                "http_status": exc.status_code,
                "detail": exc.detail,
                "resumable": True,
            }
    return {
        "ok": database_error is None,
        "schema": "warehouse.pages-device-migration.v1",
        "executed": execute,
        "workspace": {
            "uuid": str(workspace_id),
            "workspace_key": workspace["workspace_key"],
        },
        "pages": {
            "site_key": route["site_key"],
            "url": settings.public_origin + f"/apps/{route['site_key']}/",
            "static_frontend": frontend,
            "desired_config": desired_config,
            "changed": pages_changed if execute else None,
        },
        "database_plan": {
            **database_plan,
            "changed": database_changed,
        },
        "database_api": database_result,
        "database_error": database_error,
        "fallback": "scale_to_zero",
        "public_service_interruption": False,
    }
