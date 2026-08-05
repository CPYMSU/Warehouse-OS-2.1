from __future__ import annotations

import json
from uuid import UUID

from fastapi.testclient import TestClient

from app.api import digital_assets
from app.api.deps import ActorContext, current_actor
from app.main import app
from app.services.auto_runtime import _safe_download_markers
from app.terminal import executor, legacy_catalog


class _AuditWriter:
    def record(self, **_kwargs: object) -> str:
        return "00000000-0000-0000-0000-000000000099"


def _actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_slug="guide-test",
        tenant_name="Guide Test",
        industry_template_key="generic_warehouse",
        username="owner",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"ai.use", "asset_mgmt.manage"}),
    )


def test_21_guide_and_cli_are_downloadable_without_legacy_runtime_paths() -> None:
    app.dependency_overrides[current_actor] = _actor
    client = TestClient(app)
    try:
        guide = client.get("/api/digital-assets/guide")
        guide_download = client.get("/api/digital-assets/guide/download")
        cli_download = client.get("/api/digital-assets/cli")
        standard = client.get("/api/digital-assets/hosting-standard")
        standard_download = client.get("/api/digital-assets/hosting-standard/download")
        contract_download = client.get("/api/digital-assets/hosting-contract.json")
    finally:
        app.dependency_overrides.clear()

    assert guide.status_code == 200
    assert guide.json()["version"] == "2.1"
    assert "/api/workspaces/v1/info" in guide.json()["content"]
    assert "/assets/{tenant_slug}/{workspace_key}/" in guide.json()["content"]
    assert "/api/digital-assets/{asset}/workspace-quota" in guide.json()["content"]
    assert "初始固定 512 MiB" in guide.json()["content"]
    assert guide_download.status_code == 200
    assert guide_download.text.startswith("# Warehouse OS 2.1《數字資產託管指南》")
    assert cli_download.status_code == 200
    assert 'DEFAULT_BASE = "http://testserver"' in cli_download.text
    assert '"/api/workspaces/v1/info"' in cli_download.text
    assert '"/api/dam/v1/' not in cli_download.text
    compile(cli_download.text, "dam.py", "exec")
    assert standard.status_code == 200
    assert standard.json()["version"] == "2.3"
    assert standard.json()["schema"] == "warehouse.hosting-application.v2.3"
    assert standard.json()["contract"]["version"] == "2.3"
    assert standard.json()["contract"]["health"]["ready_requires"] == [
        "runtime process is running",
        "health_path succeeds",
        "public route reaches the target deployment",
    ]
    assert standard_download.status_code == 200
    assert standard_download.text.startswith("# Warehouse OS《託管應用技術要求 2.3》")
    assert contract_download.status_code == 200
    assert contract_download.json()["contract"] == ("warehouse.hosting-application.v2.3")


def test_dm_guide_provision_and_key_issue_use_native_21_contracts() -> None:
    guide = legacy_catalog.entry_by_tool_name("digital_market_guide")
    provision = legacy_catalog.entry_by_tool_name("digital_market_provision")
    key_issue = legacy_catalog.entry_by_tool_name("digital_market_key_issue")

    assert guide is not None
    assert provision is not None
    assert key_issue is not None
    assert guide["api_path"] == "/api/digital-assets/guide"
    assert provision["api_path"] == "/api/digital-assets/provision"
    assert key_issue["api_path"] == "/api/workspaces/{workspace_ref}/keys"
    assert "digital_market_provision" not in legacy_catalog.COMPOSITE_STORE_TOOL_NAMES
    assert "digital_market_key_issue" not in legacy_catalog.COMPOSITE_STORE_TOOL_NAMES
    assert legacy_catalog.ai_execution_route_ready(provision) is True
    assert legacy_catalog.ai_execution_route_ready(key_issue) is True
    assert legacy_catalog.confirmation_contract(provision)["mode"] == "passkey"
    assert legacy_catalog.confirmation_contract(key_issue)["mode"] == "passkey"

    provision_values = legacy_catalog.values_from_tool_args(
        provision,
        {
            "name": "Customer Operations",
            "runtime": "api",
            "workspace-key": "customer-operations",
        },
    )
    method, path, body = legacy_catalog.build_request(provision, provision_values)
    assert (method, path) == ("POST", "/api/digital-assets/provision")
    assert body == {
        "name": "Customer Operations",
        "asset_kind": "software",
        "workspace_key": "customer-operations",
        "runtime_type": "api",
        "service_plan": "hosted",
        "code_storage": "hdd",
        "label": "Primary workspace key",
        "expires_days": 90,
    }

    key_values = legacy_catalog.values_from_tool_args(
        key_issue,
        {"workspace": "customer-operations", "label": "Importer"},
    )
    method, path, body = legacy_catalog.build_request(key_issue, key_values)
    assert (method, path) == (
        "POST",
        "/api/workspaces/customer-operations/keys",
    )
    assert body == {
        "label": "Importer",
        "scopes": ["workspace:read", "data:read"],
        "expires_days": 90,
    }


def test_dm_data_contracts_use_native_21_workspace_routes() -> None:
    schema = legacy_catalog.entry_by_tool_name("digital_market_console")
    listing = legacy_catalog.entry_by_tool_name("digital_market_db_query")
    put = legacy_catalog.entry_by_tool_name("digital_market_db_exec")
    binding = legacy_catalog.entry_by_tool_name("digital_market_database_create")

    assert schema["command"] == "dm data schema"
    assert schema["api_path"] == "/api/workspaces/{workspace_ref}/database/schema"
    assert listing["command"] == "dm data list"
    assert listing["api_path"] == "/api/workspaces/{workspace_ref}/data/{collection}"
    assert put["command"] == "dm data put"
    assert put["api_method"] == "PUT"
    assert put["api_path"] == ("/api/workspaces/{workspace_ref}/data/{collection}/{record_key}")
    assert binding["command"] == "dm data bind"
    assert binding["api_path"] == "/api/workspaces/{workspace_ref}/databases"

    values = legacy_catalog.values_from_tool_args(
        put,
        {
            "workspace": "customer-operations",
            "collection": "customers",
            "record-key": "acme",
            "data": {"name": "Acme"},
            "expected-version": 0,
        },
    )
    method, path, body = legacy_catalog.build_request(put, values)
    assert (method, path) == (
        "PUT",
        "/api/workspaces/customer-operations/data/customers/acme?expected_version=0",
    )
    assert body == {"data": {"name": "Acme"}}


def test_pages_commands_share_the_native_console_and_hosting_contracts() -> None:
    status_entry = legacy_catalog.entry_by_tool_name("digital_market_pages_status")
    configure = legacy_catalog.entry_by_tool_name("digital_market_pages_configure")
    design = legacy_catalog.entry_by_tool_name("digital_market_pages_design")
    design_file = legacy_catalog.entry_by_tool_name("digital_market_pages_design_file")
    activate = legacy_catalog.entry_by_tool_name("digital_market_pages_release_activate")

    assert status_entry["api_path"] == "/api/workspaces/{workspace_ref}/pages-console"
    assert design["api_path"] == "/api/workspaces/{workspace_ref}/pages/design"
    assert design_file["api_path"].endswith("/pages/files/{file_path}")
    assert configure["api_path"] == "/api/hosting/v2/sessions"
    assert configure["ai_requires_confirmation"] is True
    assert activate["ai_requires_confirmation"] is True
    assert {
        status_entry["tool_name"],
        configure["tool_name"],
        design["tool_name"],
        design_file["tool_name"],
        activate["tool_name"],
    }.issubset(legacy_catalog.COMPOSITE_STORE_TOOL_NAMES)
    assert all(
        legacy_catalog.ai_execution_route_ready(entry)
        for entry in (status_entry, configure, design, design_file, activate)
    )

    values = legacy_catalog.values_from_tool_args(
        configure,
        {
            "workspace": "mk7-workspace",
            "site-key": "ai-secretary",
            "execute": True,
        },
    )
    method, path, body = legacy_catalog.build_request(configure, values)
    assert (method, path) == ("POST", "/api/hosting/v2/sessions")
    assert body["workspace_ref"] == "mk7-workspace"
    assert body["desired_state"] == {"pages": {"site_key": "ai-secretary"}}
    assert "public_alias_enabled" not in body["desired_state"]["pages"]
    assert body["execute"] is True

    activate_values = legacy_catalog.values_from_tool_args(
        activate,
        {"workspace": "mk7-workspace", "deployment": "release-7"},
    )
    method, path, body = legacy_catalog.build_request(activate, activate_values)
    assert (method, path, body) == (
        "POST",
        "/api/workspaces/mk7-workspace/pages/releases/release-7/activate",
        {},
    )


def test_ai_visible_dm_contracts_do_not_reintroduce_20_hosting() -> None:
    retired = [
        entry for entry in legacy_catalog.COMMANDS if entry.get("lifecycle") == "retired_2_0"
    ]
    assert {entry["command"] for entry in retired} == {
        "dm site publish",
        "dm site put",
        "dm site history",
        "dm site diff",
        "dm site rollback",
        "dm site rm",
    }
    assert all(entry.get("ai_exposed") is False for entry in retired)

    visible_dm = [
        entry
        for entry in legacy_catalog.COMMANDS
        if entry["command"].startswith("dm ")
        and entry.get("ai_exposed", True)
        and entry.get("lifecycle") != "retired_2_0"
    ]
    rendered = json.dumps(visible_dm, ensure_ascii=False)
    for forbidden in (
        "/api/dam/v1",
        "SQLite",
        "dam.py push",
        "dam.py rollback",
        "workspace-db/query",
        "workspace-db/exec",
    ):
        assert forbidden not in rendered


def test_dm_guide_dispatches_to_the_native_route(monkeypatch) -> None:
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    result = executor.execute_tool_call(_actor(), "digital_market_guide", {})

    assert result["status"] == "succeeded"
    assert result["data"]["version"] == "2.1"
    assert result["data"]["downloads"][1]["url"] == "/api/digital-assets/cli"

    markers = _safe_download_markers(result)
    assert [item["url"] for item in markers] == [
        "/api/digital-assets/guide/download",
        "/api/digital-assets/cli",
    ]
    assert (
        _safe_download_markers(
            {"data": {"downloads": [{"url": "https://evil.example/key", "filename": "x"}]}}
        )
        == ()
    )


def test_dm_hosting_requirements_dispatches_and_exposes_safe_downloads(
    monkeypatch,
) -> None:
    entry = legacy_catalog.entry_by_tool_name("digital_market_hosting_requirements")
    assert entry is not None
    assert entry["command"] == "dm hosting requirements"
    assert entry["api_path"] == "/api/digital-assets/hosting-standard"
    assert legacy_catalog.ai_execution_route_ready(entry) is True

    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    result = executor.execute_tool_call(
        _actor(),
        "digital_market_hosting_requirements",
        {},
    )

    assert result["status"] == "succeeded"
    assert result["data"]["version"] == "2.3"
    assert [item["url"] for item in _safe_download_markers(result)] == [
        "/api/digital-assets/hosting-standard/download",
        "/api/digital-assets/hosting-contract.json",
    ]


def test_native_provision_route_composes_asset_workspace_database_and_key(
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def create_asset(_actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
        calls.append(("asset", payload))
        return {
            "ok": True,
            "asset": {"id": 7, "uuid": "asset-uuid", "name": payload["name"]},
            "custody_event": {"event_type": "registered"},
        }

    def create_workspace(
        _actor: ActorContext,
        asset_ref: object,
        payload: dict[str, object],
    ) -> dict[str, object]:
        calls.append(("workspace", asset_ref))
        assert payload["workspace_key"] == "customer-operations"
        return {
            "ok": True,
            "workspace": {"id": 9, "uuid": "workspace-uuid"},
            "components": [{"component_kind": "backend"}],
            "database": {"provider_key": "warehouse_postgresql_data_api"},
            "storage": {
                "code": {"medium": "hdd"},
                "data": {"medium": "hdd"},
            },
        }

    def issue_workspace_key(
        _actor: ActorContext,
        workspace_ref: object,
        payload: dict[str, object],
        *,
        signing_secret: str,
        key_kind: str,
    ) -> dict[str, object]:
        calls.append(("key", workspace_ref))
        assert payload["label"] == "Initial key"
        assert signing_secret
        assert key_kind == "primary"
        return {
            "ok": True,
            "api_key": "wak_once",
            "credential_id": "credential-uuid",
            "key_id": "credential-uuid",
            "label": "Initial key",
        }

    monkeypatch.setattr(digital_assets, "create_asset", create_asset)
    monkeypatch.setattr(digital_assets, "create_workspace", create_workspace)
    monkeypatch.setattr(digital_assets, "issue_workspace_key", issue_workspace_key)
    app.dependency_overrides[current_actor] = _actor
    client = TestClient(app)
    try:
        response = client.post(
            "/api/digital-assets/provision",
            json={
                "name": "Customer Operations",
                "workspace_key": "customer-operations",
                "label": "Initial key",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert calls == [
        (
            "asset",
            {
                "name": "Customer Operations",
                "workspace_key": "customer-operations",
                "label": "Initial key",
            },
        ),
        ("workspace", "asset-uuid"),
        ("key", "workspace-uuid"),
    ]
    assert response.json()["api_key"] == "wak_once"
    assert response.json()["database"]["provider_key"] == "warehouse_postgresql_data_api"
    assert response.json()["guide_download"] == "/api/digital-assets/guide/download"
