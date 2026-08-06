from __future__ import annotations

import json
import zipfile
from pathlib import Path
from uuid import UUID

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.api import digital_assets as digital_assets_api
from app.api.deps import ActorContext
from app.api.hosted_runtime_gateway import (
    _browser_compatibility_script,
    _pages_shell_document,
    _pages_static_response,
    _static_cache_headers,
)
from app.core.config import Settings
from app.main import app
from app.services import device_runtime, pages_runtime
from app.services.intelligent_hosting import _merge_desired_state, assistant_manifest


class _Credential:
    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    workspace_id = UUID("00000000-0000-0000-0000-000000000002")
    credential_id = UUID("00000000-0000-0000-0000-000000000003")

    def require(self, scope: str) -> None:
        assert scope in {"workspace:read", "deploy:read"}


def _source_descriptor() -> dict[str, object]:
    source_id = UUID("00000000-0000-0000-0000-000000000004")
    return {
        "id": source_id,
        "legacy_id": 4,
        "version_no": "pages-v1",
        "filename": "pages.zip",
        "size_bytes": 512,
        "sha256": "a" * 64,
        "active_source_version_id": source_id,
        "storage_provider": "content_addressed_hdd",
        "object_key": "unused-in-unit-test",
    }


def _source_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("project/index.html", "<main>Hello Pages</main>")
        archive.writestr("project/styles/tokens.css", ":root { --ink: #111; }")
        archive.writestr("project/components/app.js", "export const app = true;")
        archive.writestr("project/assets/mark.svg", "<svg></svg>")
        archive.writestr("project/.env.production", "SECRET=never-return-this")


def test_pages_site_key_and_hostname_are_single_dns_label() -> None:
    settings = Settings(
        public_origin="https://bonfirework.org",
        pages_root_domain="Apps.Bonfirework.org.",
        pages_runtime_root_domain="Bonfirework.org.",
        pages_scheme="https",
    )

    assert pages_runtime.validate_site_key("workspace-key") == "workspace-key"
    assert pages_runtime.pages_hostname("workspace-key", settings) == (
        "workspace-key.apps.bonfirework.org"
    )
    assert pages_runtime.pages_hostname_site_key(
        "workspace-key.apps.bonfirework.org:443", settings
    ) == "workspace-key"
    assert pages_runtime.pages_hostname_site_key(
        "nested.workspace-key.apps.bonfirework.org", settings
    ) is None
    assert pages_runtime.pages_runtime_hostname("workspace-key", settings) == (
        "workspace-key.bonfirework.org"
    )
    assert pages_runtime.pages_runtime_hostname_site_key(
        "workspace-key.bonfirework.org:443", settings
    ) == "workspace-key"
    assert pages_runtime.pages_runtime_hostname_site_key(
        "mac-origin.bonfirework.org", settings
    ) is None
    assert pages_runtime.pages_entry_path("workspace-key") == "/apps/workspace-key/"
    assert pages_runtime.pages_entry_url("workspace-key", settings) == (
        "https://bonfirework.org/apps/workspace-key/"
    )

    with pytest.raises(HTTPException, match="site_key"):
        pages_runtime.validate_site_key("Workspace Key")
    with pytest.raises(HTTPException, match="reserved"):
        pages_runtime.validate_site_key("api")


def test_pages_root_domain_rejects_urls_and_normalizes_dns() -> None:
    assert Settings(pages_root_domain="Apps.Bonfirework.org.").pages_root_domain == (
        "apps.bonfirework.org"
    )
    with pytest.raises(ValueError, match="bare DNS name"):
        Settings(pages_root_domain="https://apps.bonfirework.org")
    assert Settings(
        pages_runtime_root_domain="Bonfirework.org."
    ).pages_runtime_root_domain == "bonfirework.org"
    with pytest.raises(ValueError, match="bare DNS name"):
        Settings(pages_runtime_root_domain="https://bonfirework.org")


def test_runtime_hostname_resolves_the_same_pages_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = {"site_key": "design-lab", "workspace_key": "design-lab"}
    monkeypatch.setattr(
        pages_runtime,
        "resolve_pages_site_key",
        lambda site_key: expected if site_key == "design-lab" else None,
    )

    assert pages_runtime.resolve_pages_hostname(
        "design-lab.bonfirework.org", Settings()
    ) == expected
    assert pages_runtime.resolve_pages_hostname(
        "design-lab.apps.bonfirework.org", Settings()
    ) == expected


def test_pages_internal_path_preserves_platform_compatibility_path() -> None:
    route = {"tenant_slug": "acme", "workspace_key": "design-lab"}

    assert pages_runtime.pages_internal_path(route, "/") == (
        "/assets/acme/design-lab/"
    )
    assert pages_runtime.pages_internal_path(route, "/styles/app.css") == (
        "/assets/acme/design-lab/styles/app.css"
    )
    assert pages_runtime.pages_internal_path(
        route, "/assets/acme/design-lab/styles/app.css"
    ) == "/assets/acme/design-lab/styles/app.css"


def test_warehouse_pages_shell_keeps_the_short_url_and_isolates_runtime() -> None:
    settings = Settings(
        public_origin="https://bonfirework.org",
        pages_root_domain="apps.bonfirework.org",
    )

    document, frame_url = _pages_shell_document(
        site_key="design-lab",
        runtime_path="reports/today",
        query="view=compact&name=%3Cunsafe%3E",
        settings=settings,
    )

    assert frame_url == (
        "https://design-lab.bonfirework.org/reports/today"
        "?view=compact&name=%3Cunsafe%3E"
    )
    assert 'sandbox="' in document
    assert "allow-same-origin" in document
    assert "https://design-lab.bonfirework.org/reports/today" in document
    assert "name=%3Cunsafe%3E" in document


def test_pages_public_contract_defaults_to_warehouse_os_entry() -> None:
    settings = Settings(public_origin="https://bonfirework.org")
    route = {
        "site_key": "design-lab",
        "tenant_slug": "acme",
        "workspace_key": "design-lab",
        "status": "active",
        "active_deployment_id": UUID("00000000-0000-0000-0000-000000000005"),
        "public_alias_enabled": False,
        "config": {},
    }

    public = pages_runtime._route_public(route, settings)

    assert public["url"] == "https://bonfirework.org/apps/design-lab/"
    assert public["entry_mode"] == "warehouse_os"
    assert public["hostname"] is None
    assert public["public_alias"] == {
        "enabled": False,
        "hostname": None,
        "url": None,
    }
    assert public["database_origin"] == "https://design-lab.bonfirework.org"

    route["public_alias_enabled"] = True
    with_alias = pages_runtime._route_public(route, settings)
    assert with_alias["url"] == "https://bonfirework.org/apps/design-lab/"
    assert with_alias["public_alias"] == {
        "enabled": True,
        "hostname": "design-lab.apps.bonfirework.org",
        "url": "https://design-lab.apps.bonfirework.org/",
    }


def test_workspace_entry_fields_use_the_warehouse_os_route() -> None:
    route = {
        "site_key": "design-lab",
        "tenant_slug": "acme",
        "workspace_key": "design-lab",
        "status": "active",
        "active_deployment_id": UUID("00000000-0000-0000-0000-000000000005"),
        "public_alias_enabled": False,
        "config": {},
    }
    fields = pages_runtime.workspace_pages_entry_fields(
        "acme",
        {"workspace_key": "design-lab", "_pages_route": route},
        Settings(public_origin="https://bonfirework.org"),
    )

    assert fields["entry_path"] == "/apps/design-lab/"
    assert fields["entry_url"] == "https://bonfirework.org/apps/design-lab/"
    assert fields["hosting_url"] == fields["entry_url"]
    assert fields["fallback_path"] == "/assets/acme/design-lab/"


def test_static_cache_headers_revalidate_html_and_lock_hashed_assets() -> None:
    route = {
        "deployment_id": "00000000-0000-0000-0000-000000000005",
        "release_digest": "release-20260805",
    }

    html = _static_cache_headers(route, "", "text/html")
    hashed = _static_cache_headers(route, "assets/app.0123abcd.js", "text/javascript")
    plain = _static_cache_headers(route, "assets/app.js", "text/javascript")

    assert "must-revalidate" in html["Cache-Control"]
    assert "immutable" in hashed["Cache-Control"]
    assert "stale-while-revalidate" in plain["Cache-Control"]
    assert html["ETag"] != plain["ETag"]
    assert plain["X-Warehouse-Release"] == "release-20260805"


def test_pages_static_frontend_is_served_without_waking_backend(tmp_path: Path) -> None:
    release = tmp_path / "release" / "frontend"
    release.mkdir(parents=True)
    (release / "index.html").write_text(
        "<!doctype html><html><head></head><body>Device first</body></html>",
        encoding="utf-8",
    )
    route = {
        "kind": "static",
        "runtime_rel_path": "release/frontend",
        "site_key": "design-lab",
        "workspace_key": "design-lab",
        "deployment_id": "00000000-0000-0000-0000-000000000005",
        "release_digest": "release-device-first",
        "device_runtime": {
            "enabled": True,
            "loopback_origin": "http://127.0.0.1:47821",
            "fallback": "scale_to_zero",
        },
    }
    settings = Settings(hosted_runtime_data_root=tmp_path)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"accept", b"text/html")],
        }
    )

    response = _pages_static_response(route, "", request, settings)

    assert response is not None
    assert response.headers["X-Warehouse-Pages-Delivery"] == "static-device-first"
    assert b"__WAREHOUSE_DEVICE_RUNTIME__" in response.body
    assert b"127.0.0.1:47821" in response.body


def test_migrated_static_release_resolves_from_pages_cache_without_database_query(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = "00000000-0000-0000-0000-000000000005"
    frontend = tmp_path / "release" / "frontend"
    frontend.mkdir(parents=True)
    (frontend / "index.html").write_text("<html></html>", encoding="utf-8")
    monkeypatch.setattr(
        pages_runtime,
        "resolve_pages_site_key",
        lambda _site_key: {
            "site_key": "design-lab",
            "workspace_key": "design-lab",
            "workspace_id": "00000000-0000-0000-0000-000000000002",
            "tenant_id": "00000000-0000-0000-0000-000000000001",
            "active_deployment_id": deployment_id,
            "config": {
                "static_frontend": {
                    "enabled": True,
                    "runtime_rel_path": "release",
                    "root": "frontend",
                    "deployment_id": deployment_id,
                    "release_digest": "release-device-first",
                    "backend_fallback": "scale_to_zero",
                },
                "device_runtime": {"enabled": True},
            },
        },
    )
    monkeypatch.setattr(
        device_runtime,
        "tenant_session",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("static cache must not query PostgreSQL")
        ),
    )

    resolved = device_runtime.pages_static_release(
        "design-lab",
        settings=Settings(hosted_runtime_data_root=tmp_path),
    )

    assert resolved is not None
    assert resolved["kind"] == "static"
    assert resolved["runtime_rel_path"] == "release/frontend"


def test_pages_static_frontend_leaves_api_misses_for_runtime_fallback(
    tmp_path: Path,
) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "index.html").write_text("<html></html>", encoding="utf-8")
    route = {
        "kind": "static",
        "runtime_rel_path": "release",
        "deployment_id": "00000000-0000-0000-0000-000000000005",
        "workspace_key": "design-lab",
    }
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/items",
            "headers": [(b"accept", b"application/json")],
        }
    )

    assert _pages_static_response(
        route,
        "api/items",
        request,
        Settings(hosted_runtime_data_root=tmp_path),
    ) is None


def test_browser_contract_routes_fetch_xhr_and_events_to_device_first() -> None:
    script = _browser_compatibility_script(
        "",
        device_runtime={"enabled": True, "fallback": "scale_to_zero"},
        workspace_key="design-lab",
    )

    assert "127.0.0.1:47821" in script
    assert "X-Warehouse-Device-Runtime" in script
    assert "deviceMap(u)" in script
    assert "fallback\":\"scale_to_zero" in script


def test_design_context_excludes_secrets_and_describes_immutable_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "pages.zip"
    _source_archive(archive)
    descriptor = _source_descriptor()
    monkeypatch.setattr(pages_runtime, "_source_descriptor", lambda *_args: descriptor)
    monkeypatch.setattr(pages_runtime, "_source_path", lambda *_args: archive)
    monkeypatch.setattr(
        pages_runtime,
        "get_pages_site",
        lambda *_args: {
            "site": {
                "site_key": "design-lab",
                "database_origin": "https://design-lab.bonfirework.org",
            }
        },
    )

    result = pages_runtime.pages_design_context(
        _Credential(), Settings(), source_ref=None
    )

    paths = {item["path"] for item in result["files"]}
    assert "index.html" in paths
    assert "styles/tokens.css" in paths
    assert ".env.production" not in paths
    assert result["excluded_sensitive_files"] == 1
    assert result["source"]["active"] is True
    assert result["change_policy"]["active_release_mutable"] is False
    assert any(
        item["id"] == "bind-exact-database-origin"
        and item["origin"] == "https://design-lab.bonfirework.org"
        for item in result["recommendations"]
    )


def test_source_file_api_reads_code_but_never_environment_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "pages.zip"
    _source_archive(archive)
    descriptor = _source_descriptor()
    monkeypatch.setattr(pages_runtime, "_source_descriptor", lambda *_args: descriptor)
    monkeypatch.setattr(pages_runtime, "_source_path", lambda *_args: archive)

    result = pages_runtime.pages_source_file(
        _Credential(), Settings(), "components/app.js"
    )

    assert result["file"]["encoding"] == "utf-8"
    assert result["file"]["content"] == "export const app = true;"
    assert len(result["file"]["sha256"]) == 64
    with pytest.raises(HTTPException) as exc:
        pages_runtime.pages_source_file(
            _Credential(), Settings(), ".env.production"
        )
    assert exc.value.status_code == 404


def test_secretary_contract_supports_pages_configuration_and_design_reads() -> None:
    desired = _merge_desired_state(
        {},
        {
            "pages": {
                "site_key": "customer-portal",
                "public_alias_enabled": True,
            }
        },
    )
    manifest = assistant_manifest()

    assert desired["pages"]["site_key"] == "customer-portal"
    assert desired["pages"]["public_alias_enabled"] is True
    assert manifest["version"] == "2.4"
    assert manifest["pages_runtime"]["stable_url"] == (
        "https://bonfirework.org/apps/{site_key}/"
    )
    assert manifest["pages_runtime"]["isolated_runtime_origin"] == (
        "https://{site_key}.bonfirework.org/"
    )
    assert manifest["pages_runtime"]["public_alias_default"] is False
    assert manifest["pages_runtime"]["active_release_editable_in_place"] is False
    assert "/pages/design" in (
        manifest["pages_runtime"]["hosting_session_api"]["design_context"]
    )
    assert manifest["pages_runtime"]["workspace_key_api"]["read_file"].endswith(
        "/pages/files/{path}"
    )

    with pytest.raises(HTTPException, match="must be a boolean"):
        _merge_desired_state(
            {},
            {
                "pages": {
                    "site_key": "customer-portal",
                    "public_alias_enabled": "yes",
                }
            },
        )


def test_account_pages_console_aggregates_non_secret_release_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actor = ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000010"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000011"),
        tenant_slug="acme",
        tenant_name="Acme",
        industry_template_key="default",
        username="owner@example.test",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"asset_mgmt.read", "asset_mgmt.manage"}),
    )
    workspace_id = UUID("00000000-0000-0000-0000-000000000012")
    active_id = UUID("00000000-0000-0000-0000-000000000013")
    historical_id = UUID("00000000-0000-0000-0000-000000000014")
    workspace = {
        "uuid": str(workspace_id),
        "workspace_key": "design-lab",
        "active_deployment_id": str(active_id),
        "config": {"runtime_type": "static"},
    }
    monkeypatch.setattr(
        digital_assets_api,
        "workspace_asset_identity",
        lambda *_args: {"workspace": workspace, "asset": {}},
    )
    monkeypatch.setattr(
        digital_assets_api,
        "workspace_info",
        lambda *_args: {
            "workspace": workspace,
            "databases": [{"logical_name": "app", "status": "ready"}],
            "usage": {"total_bytes": 1024, "quota_bytes": 4096},
        },
    )
    site = {
        "url": "https://bonfirework.org/apps/design-lab/",
        "site_key": "design-lab",
        "database_origin": "https://design-lab.bonfirework.org",
        "public_alias": {"enabled": False, "url": None},
        "runtime": {"delivery": "static_assets", "compute": "browser"},
    }
    monkeypatch.setattr(
        digital_assets_api,
        "get_pages_site",
        lambda *_args: {"site": site},
    )
    monkeypatch.setattr(
        digital_assets_api,
        "browser_access_configuration",
        lambda *_args, **_kwargs: {
            "project": {
                "project_id": "dbp_design_lab",
                "enabled": True,
                "allowed_origins": ["https://design-lab.bonfirework.org"],
                "revision": 3,
            }
        },
    )
    monkeypatch.setattr(
        digital_assets_api,
        "list_workspace_deployments",
        lambda *_args, **_kwargs: {
            "deployments": [
                {
                    "id": 13,
                    "uuid": str(active_id),
                    "status": "ready",
                    "health": "healthy",
                    "release_digest": "release-current",
                    "created_at": "2026-08-05T02:07:00Z",
                },
                {
                    "id": 12,
                    "uuid": str(historical_id),
                    "status": "ready",
                    "health": "healthy",
                    "release_digest": "release-previous",
                    "created_at": "2026-08-04T10:07:00Z",
                },
            ]
        },
    )

    result = digital_assets_api.workspace_pages_console(
        "design-lab",
        limit=20,
        actor=actor,
        settings=Settings(public_origin="https://bonfirework.org"),
    )

    assert result["site"]["url"] == "https://bonfirework.org/apps/design-lab/"
    assert result["runtime"]["mode"] == "static_browser"
    assert result["hosting_classification"] == {
        "is_fully_static": True,
        "frontend_is_static": True,
        "backend_is_device_first": False,
        "pages_shell_is_static": True,
        "application_requires_server_runtime": False,
        "resident_server_runtime_required": False,
        "server_fallback": None,
        "authoritative_runtime_field": "runtime.type",
        "note": (
            "Static frontend delivery is independent from the backend contract. "
            "Non-static backends run on the user's device first and retain a "
            "scale-to-zero platform fallback."
        ),
    }
    assert result["current_release"]["uuid"] == str(active_id)
    assert result["releases"][1]["rollback_eligible"] is True
    assert result["database"]["count"] == 1
    assert result["database"]["browser"]["runtime_origin_allowed"] is True
    assert result["actions"]["schema"] == "warehouse.pages-actions.v1"
    actions = {item["action_key"]: item for item in result["actions"]["items"]}
    assert actions["pages.site.configure"]["invocation"]["action_context"] == {
        "schema": "warehouse.pages-action-context.v1",
        "action_key": "pages.site.configure",
        "workspace_ref": "design-lab",
        "suggested_tool_names": [
            "digital_market_pages_status",
            "digital_market_pages_configure",
            "digital_market_database_browser_access",
        ],
    }
    rollback_key = f"pages.release.activate:{historical_id}"
    assert actions[rollback_key]["invocation"]["tool_name"] == (
        "digital_market_pages_release_activate"
    )
    assert "wak_" not in json.dumps(result)

    workspace["config"] = {"runtime_type": "api"}
    site["config"] = {
        "static_frontend": {
            "enabled": True,
            "backend_fallback": "scale_to_zero",
        },
        "device_runtime": {"enabled": True},
    }
    api_result = digital_assets_api.workspace_pages_console(
        "design-lab",
        limit=20,
        actor=actor,
        settings=Settings(public_origin="https://bonfirework.org"),
    )
    assert api_result["site"]["runtime"]["delivery"] == "static_assets"
    assert api_result["runtime"]["type"] == "api"
    assert api_result["runtime"]["mode"] == "static_frontend_device_first"
    assert api_result["runtime"]["compute_location"] == (
        "browser_then_user_device_with_serverless_fallback"
    )
    assert api_result["runtime"]["idle_server_memory"] == "near_zero"
    assert api_result["hosting_classification"]["is_fully_static"] is False
    assert api_result["hosting_classification"]["pages_shell_is_static"] is True
    assert api_result["hosting_classification"]["application_requires_server_runtime"] is True
    assert (
        api_result["hosting_classification"]["resident_server_runtime_required"]
        is False
    )


def test_pages_api_routes_are_registered_before_the_api_catch_all() -> None:
    def iter_routes(value: object, seen: set[int] | None = None):
        observed = seen if seen is not None else set()
        routes = value if isinstance(value, (list, tuple)) else getattr(value, "routes", ())
        for route in routes:
            if id(route) in observed:
                continue
            observed.add(id(route))
            yield route
            for attribute in ("routes", "router", "original_router", "included_router"):
                nested = getattr(route, attribute, None)
                if nested is not None:
                    yield from iter_routes(nested, observed)

    paths = {getattr(route, "path", "") for route in iter_routes(app.routes)}

    assert "/api/workspaces/v1/pages" in paths
    assert "/api/workspaces/v1/pages/design" in paths
    assert "/api/workspaces/v1/pages/files/{file_path:path}" in paths
    assert "/api/hosting/v2/sessions/{session_id}/pages" in paths
    assert "/api/hosting/v2/sessions/{session_id}/pages/design" in paths
    assert "/api/workspaces/{workspace_ref}/pages" in paths
    assert "/api/workspaces/{workspace_ref}/pages/design" in paths
    assert "/api/workspaces/{workspace_ref}/pages/files/{file_path:path}" in paths
    assert (
        "/api/workspaces/{workspace_ref}/pages/releases/{deployment_id}/activate" in paths
    )
    assert "/api/workspaces/{workspace_ref}/pages-console" in paths
    assert "/apps/{site_key}/" in paths
    assert "/apps/{site_key}/{runtime_path:path}" in paths


def test_pages_migration_keeps_a_global_site_key_and_active_pointer() -> None:
    migration = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/20260805_0077_pages_runtime.py"
    ).read_text(encoding="utf-8")

    assert "CREATE TABLE platform.pages_routes" in migration
    assert "site_key text NOT NULL UNIQUE" in migration
    assert "active_deployment_id" in migration
    assert "public_alias_enabled boolean NOT NULL DEFAULT false" in migration
    assert '"warehouse_os_entry":true' in migration
    assert "immutable_source_versions" in migration
    assert "FOR tenant_row IN SELECT id,slug FROM iam.tenants" in migration
    assert "set_config('app.tenant_id', tenant_row.id::text, true)" in migration
