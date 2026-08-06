from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import pages_app_package
from app.services.pages_actions import pages_action_catalog
from app.services.pages_app_contract import (
    PAGES_APP_MANIFEST_FILENAME,
    PAGES_APP_SCHEMA,
    synthesize_pages_app_manifest,
    validate_pages_app_manifest,
)
from app.services.pages_app_package import build_pages_app_zip
from app.services.source_packages import inspect_source_archive


def _manifest() -> dict[str, object]:
    return {
        "schema": PAGES_APP_SCHEMA,
        "name": "Question Studio",
        "version": "2.1.0",
        "web": {
            "root": "web",
            "entry": "index.html",
            "compute": "browser",
            "navigation_fallback": "index",
            "service_worker": "sw.js",
        },
        "data": {
            "mode": "platform_api",
            "default_access": {"read": "deny", "write": "deny"},
            "collections": [
                {
                    "name": "questions",
                    "access": {"read": "session", "write": "owner"},
                    "offline": True,
                }
            ],
            "sync": {
                "mode": "cursor",
                "offline_store": "indexeddb",
                "cursor_field": "updated_at",
                "pull_limit": 500,
            },
        },
        "functions": [
            {
                "name": "questions.resolve",
                "route": "/api/questions/resolve",
                "methods": ["POST"],
                "runtime": "serverless_node",
                "source": "functions/resolve",
                "handler": "index.resolve",
                "auth": "session",
                "secret_refs": ["AI_PROVIDER_KEY"],
                "timeout_seconds": 30,
            }
        ],
        "device": {"mode": "disabled", "capabilities": []},
        "design": {
            "roots": ["web", "design"],
            "api_schema": "design/openapi.json",
            "components": "design/components.json",
        },
    }


def _source_paths() -> set[str]:
    return {
        "web/index.html",
        "web/sw.js",
        "functions/resolve/index.js",
        "design/openapi.json",
        "design/components.json",
        PAGES_APP_MANIFEST_FILENAME,
    }


def test_pages_manifest_normalizes_data_functions_and_secret_references() -> None:
    result = validate_pages_app_manifest(_manifest(), source_paths=_source_paths())

    assert result["schema"] == PAGES_APP_SCHEMA
    assert result["web"]["compute"] == "browser"
    assert result["data"]["collections"][0]["access"]["write"] == "owner"
    assert result["functions"][0]["secret_refs"] == ["AI_PROVIDER_KEY"]
    assert result["secrets_embedded"] is False
    assert result["database_reconcile"] == "background_control_plane"
    assert len(result["contract_digest"]) == 64


def test_pages_manifest_fails_closed_for_values_and_missing_source_paths() -> None:
    manifest = _manifest()
    manifest["functions"][0]["secret_refs"] = ["sk-live-secret-value"]
    with pytest.raises(HTTPException) as secret_error:
        validate_pages_app_manifest(manifest, source_paths=_source_paths())
    assert secret_error.value.status_code == 422
    assert secret_error.value.detail["field"] == "functions[0].secret_refs"

    manifest = _manifest()
    manifest["web"]["entry"] = "missing.html"
    with pytest.raises(HTTPException) as source_error:
        validate_pages_app_manifest(manifest, source_paths=_source_paths())
    assert source_error.value.detail["field"] == "web.entry"

    manifest = _manifest()
    manifest["data"]["default_access"] = {"read": "session", "write": "deny"}
    with pytest.raises(HTTPException) as default_access_error:
        validate_pages_app_manifest(manifest, source_paths=_source_paths())
    assert default_access_error.value.detail["field"] == "data.default_access"


def test_source_archive_promotes_wrapper_pages_manifest(tmp_path: Path) -> None:
    archive_path = tmp_path / "application.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for relative in _source_paths() - {PAGES_APP_MANIFEST_FILENAME}:
            archive.writestr(f"project/{relative}", "{}")
        archive.writestr(
            f"project/{PAGES_APP_MANIFEST_FILENAME}",
            json.dumps(_manifest()),
        )

    inspected = inspect_source_archive(
        archive_path,
        max_uncompressed_bytes=1024 * 1024,
    )

    assert inspected.signals["pages_contract"]["declared"] is True
    assert inspected.signals["pages_contract"]["schema"] == PAGES_APP_SCHEMA
    assert inspected.signals["pages_manifest"]["web"]["root"] == "web"


def test_legacy_static_source_gets_conservative_generated_contract() -> None:
    manifest = synthesize_pages_app_manifest(
        {"index.html", "app.js", "styles.css"},
        name="Legacy Pages",
    )

    assert manifest["generated"] is True
    assert manifest["web"]["root"] == "."
    assert manifest["data"]["mode"] == "none"
    assert manifest["functions"] == []
    assert manifest["device"]["mode"] == "disabled"


def test_legacy_mixed_source_declares_scale_to_zero_backend() -> None:
    manifest = synthesize_pages_app_manifest(
        {"frontend/index.html", "frontend/app.js", "app.py", "requirements.txt"},
        name="Legacy API Pages",
        legacy_runtime="python",
        legacy_handler="app:app",
    )

    assert manifest["generated"] is True
    assert manifest["web"]["root"] == "frontend"
    assert manifest["functions"] == [
        {
            "name": "legacy.api",
            "route": "/api/*",
            "methods": ["DELETE", "GET", "PATCH", "POST", "PUT"],
            "runtime": "serverless_python",
            "auth": "session",
            "secret_refs": [],
            "timeout_seconds": 60,
            "source": ".",
            "handler": "app:app",
        }
    ]
    assert manifest["device"] == {
        "mode": "optional",
        "capabilities": ["python.runtime"],
    }


def test_pages_zip_is_deterministic_and_excludes_sensitive_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "web").mkdir(parents=True)
    (source / "functions" / "resolve").mkdir(parents=True)
    (source / "design").mkdir()
    (source / ".warehouse").mkdir()
    (source / "web" / "index.html").write_text("<main>Question Studio</main>")
    (source / "web" / "sw.js").write_text("self.skipWaiting();")
    (source / "functions" / "resolve" / "index.js").write_text("export const resolve=1")
    (source / "design" / "openapi.json").write_text("{}")
    (source / "design" / "components.json").write_text("{}")
    (source / ".env.production").write_text("AI_PROVIDER_KEY=never-export")
    (source / ".warehouse" / "old.json").write_text("{}")
    manifest = validate_pages_app_manifest(_manifest(), source_paths=_source_paths())
    metadata = {
        "schema": "warehouse.pages-app-package.v1",
        "source": {"id": "source-v1", "sha256": "a" * 64},
        "security": {"secrets_embedded": False},
        "database_reconcile": "background_control_plane",
    }
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"

    first_excluded, first_checksums = build_pages_app_zip(
        source,
        first,
        manifest=manifest,
        package_metadata=metadata,
    )
    second_excluded, second_checksums = build_pages_app_zip(
        source,
        second,
        manifest=manifest,
        package_metadata=metadata,
    )

    assert first.read_bytes() == second.read_bytes()
    assert first_excluded == second_excluded == 1
    assert first_checksums == second_checksums
    with zipfile.ZipFile(first) as package:
        names = set(package.namelist())
        assert ".env.production" not in names
        assert ".warehouse/old.json" not in names
        assert PAGES_APP_MANIFEST_FILENAME in names
        assert ".warehouse/checksums.json" in names
        package_metadata = json.loads(package.read(".warehouse/package.json"))
        assert package_metadata["security"]["excluded_sensitive_files"] == 1
        assert package_metadata["database_reconcile"] == "background_control_plane"


def test_materialized_package_is_bound_to_the_immutable_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("project/index.html", "<main>Portable</main>")
        archive.writestr("project/.env", "SECRET=never-export")
    manifest = synthesize_pages_app_manifest(
        {"index.html", ".env"},
        name="Portable App",
        version="3",
    )
    descriptor = {
        "filename": "portable-source.zip",
        "size_bytes": archive_path.stat().st_size,
        "sha256": "b" * 64,
    }
    design = {
        "source": {"id": "source-v3", "version_no": "3"},
    }
    monkeypatch.setattr(
        pages_app_package,
        "_package_inputs",
        lambda *_args, **_kwargs: (design, descriptor, archive_path, manifest, False),
    )

    package = pages_app_package.materialize_pages_app_package(
        object(),
        Settings(),
    )
    try:
        assert package.filename == "Portable-App.warehouse-pages.zip"
        assert package.size_bytes == package.path.stat().st_size
        assert len(package.sha256) == 64
        assert package.excluded_sensitive_files == 1
        with zipfile.ZipFile(package.path) as exported:
            assert "index.html" in exported.namelist()
            assert ".env" not in exported.namelist()
            metadata = json.loads(exported.read(".warehouse/package.json"))
            assert metadata["source"] == {
                "id": "source-v3",
                "sha256": "b" * 64,
            }
    finally:
        package.path.unlink(missing_ok=True)


def test_package_contract_exposes_read_only_compute_placement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive_path = tmp_path / "source.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("index.html", "<main>Portable</main>")
    placement = {
        "schema": "warehouse.compute-placement-advice.v1",
        "advisory_only": True,
        "automatic_code_rewrite": False,
        "recommended_hosting_mode": "pure_static",
    }
    design = {
        "schema": "warehouse.pages-design-context.v1",
        "source": {"id": "source-v4", "version_no": "4"},
        "file_count": 1,
        "excluded_sensitive_files": 0,
        "read_file": "/api/workspaces/v1/pages/files/{path}?source_ref=source-v4",
        "compute_placement": placement,
    }
    descriptor = {
        "filename": "portable-source.zip",
        "size_bytes": archive_path.stat().st_size,
        "sha256": "c" * 64,
    }
    manifest = synthesize_pages_app_manifest(
        {"index.html"},
        name="Portable App",
        version="4",
    )
    monkeypatch.setattr(
        pages_app_package,
        "_package_inputs",
        lambda *_args, **_kwargs: (design, descriptor, archive_path, manifest, False),
    )

    contract = pages_app_package.pages_app_package_contract(object(), Settings())

    assert contract["design_context"]["compute_placement"] == placement
    assert contract["design_context"]["compute_placement"]["advisory_only"] is True


def test_pages_action_catalog_exposes_one_read_only_package_export() -> None:
    catalog = pages_action_catalog(
        workspace_ref="question-studio",
        site={"url": "https://bonfirework.org/apps/question-studio/", "config": {}},
        database={"count": 1, "browser": {"project_present": True}},
        releases=[{"uuid": "release-1"}],
        can_manage=False,
    )

    action = next(
        item for item in catalog["items"] if item["action_key"] == "pages.package.download"
    )
    assert action["effect"] == "read"
    assert action["enabled"] is True
    assert action["invocation"] == {
        "mode": "client",
        "client_action": "open_url",
        "url": "/api/workspaces/question-studio/pages/package/download",
    }
    design = next(
        item for item in catalog["items"] if item["action_key"] == "pages.design.review"
    )
    assert "compute_placement" in design["invocation"]["goal"]
    assert "JavaScript/TypeScript" in design["invocation"]["goal"]
