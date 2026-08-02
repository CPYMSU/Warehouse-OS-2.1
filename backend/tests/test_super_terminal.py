from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from fastapi.testclient import TestClient

from app.api.deps import ActorContext, current_actor
from app.main import app
from app.terminal import executor, legacy_catalog
from app.terminal.catalog import (
    ai_capability_candidates,
    ai_capability_gene_index,
    ai_capability_genes,
    platform_entries,
    tenant_entries,
)
from app.terminal.gateway import gateway_contract_ready, match_contract

RESEARCH_TOOLS = {
    entry["tool_name"]
    for entry in legacy_catalog.COMMANDS
    if entry["command"].startswith("research ")
}


class _AuditWriter:
    def record(self, **_kwargs: object) -> str:
        return "00000000-0000-0000-0000-000000000099"


def _actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_slug="example",
        tenant_name="Example",
        industry_template_key="power_system",
        username="owner",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"inventory.read"}),
    )


def _client(monkeypatch) -> TestClient:
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    return TestClient(app)


def test_imported_catalogue_has_complete_legacy_command_counts() -> None:
    assert len(tenant_entries()) == 486
    assert len(platform_entries()) == 22
    assert len({entry["tool_name"] for entry in tenant_entries()}) == 486


def test_retired_contracts_are_excluded_from_model_discovery() -> None:
    retired_tool = "digital_market_site_publish"
    assert retired_tool not in {
        item["tool_name"] for item in ai_capability_gene_index()
    }
    assert retired_tool not in {
        item["tool_name"]
        for item in ai_capability_candidates("發布站點文件", limit=50)
    }
    assert ai_capability_genes([retired_tool]) == []


def test_terminal_advertises_complete_catalogue_with_truthful_states(monkeypatch) -> None:
    client = _client(monkeypatch)
    try:
        response = client.get("/api/cli/commands")
        names = {item["command"] for item in response.json()["commands"]}
        status = client.get("/api/cli/migration-status").json()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(names) == 486
    assert response.json()["total"] == 486
    assert response.json()["executable"] > 2
    states = {item["command"]: item for item in response.json()["commands"]}
    assert states["whoami"]["availability"] == "active"
    assert states["warehouse list"]["allowed"] is True
    assert states["inv list"]["availability"] == "active"
    assert states["inv list"]["allowed"] is True
    assert states["dm site publish"]["availability"] == "retired_2_0"
    assert states["dm site publish"]["allowed"] is False
    assert status["tenant_command_count"] == 486
    assert status["platform_command_count"] == 22
    assert status["active_tenant_command_count"] == 480
    assert status["retired_tenant_command_count"] == 6
    assert status["awaiting_domain_adapter_count"] == 0
    assert status["invalid_contract_count"] == 0


def test_human_and_ai_paths_share_the_same_command_adapter(monkeypatch) -> None:
    # This is a command-boundary unit test. Keep it independent from the
    # developer's configured database (which may be a production SSH tunnel);
    # PostgreSQL routing is covered by the disposable-database integration
    # suite below the full deployment gate.
    monkeypatch.setattr(
        executor,
        "_dispatch",
        lambda entry, actor, values, *, origin: {"warehouses": []},
    )
    client = _client(monkeypatch)
    try:
        human = client.post("/api/cli/exec", json={"line": "warehouse list"})
        ai = client.post(
            "/api/ai/tools/warehouse_list/execute",
            json={"arguments": {}},
        )
        tools = client.get("/api/ai/tools")
    finally:
        app.dependency_overrides.clear()

    assert human.status_code == 200
    assert human.json()["status"] == "succeeded"
    assert isinstance(human.json()["data"]["warehouses"], list)
    assert ai.status_code == 200
    assert ai.json()["status"] == "succeeded"
    assert ai.json()["tool_name"] == human.json()["tool_name"] == "warehouse_list"
    assert ai.json()["data"] == human.json()["data"]
    assert len(tools.json()["tools"]) == 502
    assert len(tools.json()["capability_states"]) == 502
    assert tools.json()["catalogue_scope"] == "global_command_metadata"
    assert tools.json()["data_scope"] == "current_tenant_only"
    states = {item["tool_name"]: item for item in tools.json()["capability_states"]}
    assert states["inventory_list"]["availability"] == "active"
    assert states["p_owner_grant"]["availability"] == "requires_l11_governance"
    assert "digital_market_site_publish" not in states


def test_failed_capability_exposes_optional_atomic_recovery(monkeypatch) -> None:
    def rejected(*_args: object, **_kwargs: object) -> object:
        raise executor.CommandAdapterError(404, {"detail": "not found"})

    monkeypatch.setattr(executor, "_dispatch", rejected)
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())

    result = executor.execute_runtime_tool_call(
        _actor(),
        "digital_market_show",
        {"id": "mk4-workspace"},
    )

    assert result["status"] == "target_rejected"
    recovery = result["data"]["atomic_recovery"]
    assert recovery["decision_owner"] == "auto_runtime"
    assert recovery["workflow_prescribed"] is False
    assert recovery["semantic_contract"]["resource"] == "digital_asset.asset"
    assert "generic_data_observe" in {
        item["tool_name"] for item in recovery["available_capabilities"]
    }


def test_manual_buttons_are_generated_from_the_complete_shared_catalogue(monkeypatch) -> None:
    client = _client(monkeypatch)
    try:
        response = client.get("/api/business/actions")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()
    assert payload["total"] == 508
    assert payload["tenant_total"] == 486
    assert payload["platform_total"] == 22
    actions = {item["tool_name"]: item for item in payload["actions"]}
    assert actions["warehouse_list"]["manual_execution"] == "execute"
    assert actions["item_create"]["parameters"]["required"] == ["name"]
    assert actions["item_create"]["category"] == "inventory"
    assert actions["item_create"]["category_order"] == 0
    assert "出入庫" in actions["item_create"]["category_guide"]
    item_entry = next(
        entry for entry in legacy_catalog.COMMANDS if entry["tool_name"] == "item_create"
    )
    assert (
        actions["item_create"]["parameters"]
        == legacy_catalog.tool_schema(item_entry)["function"]["parameters"]
    )
    assert actions["p_owner_grant"]["manual_execution"] == "unavailable"
    assert actions["research_file_diff"]["command"] == "research file diff"
    assert actions["research_upload_contract"]["command"] == "research upload contract"
    assert actions["research_file_versions"]["command"] == "research file versions"
    assert actions["research_git_log"]["command"] == "research git log"
    assert actions["research_formats_list"]["command"] == "research formats list"
    assert actions["research_cli_show"]["command"] == "research cli show"
    assert actions["research_file_diff"]["category"] == "research"
    assert actions["research_project_list"]["authorized"] is False
    assert actions["research_project_list"]["manual_execution"] == "unavailable"


def test_runtime_skills_exposes_the_complete_uncached_research_catalogue(
    monkeypatch,
) -> None:
    client = _client(monkeypatch)
    try:
        response = client.get("/api/runtime/skills")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    research_items = [
        item for item in response.json()["skills"] if item["category"] == "research"
    ]
    research_skills = {item["skill_id"] for item in research_items}
    assert research_skills == RESEARCH_TOOLS
    assert len(research_skills) == 40
    assert next(
        item for item in research_items if item["skill_id"] == "research_cli_show"
    )["name"] == "research cli show"


def test_manual_button_executes_with_its_own_audited_origin(monkeypatch) -> None:
    audited: list[dict[str, object]] = []

    class _ManualAuditWriter:
        def record(self, **kwargs: object) -> str:
            audited.append(kwargs)
            return "00000000-0000-0000-0000-000000000100"

    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _ManualAuditWriter())
    monkeypatch.setattr(
        executor,
        "_dispatch",
        lambda entry, actor, values, *, origin: {
            "adapter": "test",
            "tool_name": entry["tool_name"],
            "origin": origin,
            "arguments": dict(values),
        },
    )
    client = TestClient(app)
    try:
        response = client.post(
            "/api/business/actions/warehouse_list/execute",
            json={"arguments": {}},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "succeeded"
    assert response.json()["data"]["origin"] == "manual_ui"
    assert audited[0]["origin"] == "manual_ui"


def test_all_tenant_command_contracts_resolve_through_the_shared_gateway() -> None:
    samples: dict[str, object] = {
        "str": "sample",
        "int": 1,
        "float": 1.5,
        "bool": True,
        "flag": True,
        "list": ["sample"],
        "object": {"value": "sample"},
        "array": [{"value": "sample"}],
        "json": {"value": "sample"},
    }
    for entry in tenant_entries():
        assert gateway_contract_ready(entry), entry["tool_name"]
        arguments = {
            parameter["flag"]: samples[parameter["type"]]
            for parameter in entry["params"]
            if parameter["required"]
        }
        values = legacy_catalog.values_from_tool_args(entry, arguments)
        method, target, _body = legacy_catalog.build_request(entry, values)
        parsed = urlsplit(target)
        assert "{" not in parsed.path, entry["tool_name"]
        matched = match_contract(method, parsed.path, tool_name=entry["tool_name"])
        assert matched is not None, entry["tool_name"]
        assert matched.entry["tool_name"] == entry["tool_name"]


def test_no_generic_sql_super_api_is_exposed() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/admin/sql" not in paths
    assert "/api/platform/admin/sql" not in paths
    assert "/api/ai/tools/{tool_name}/execute" in paths
    assert "/api/business/actions" in paths
    assert "/api/business/actions/{tool_name}/execute" in paths


def test_warehouse_v2_routes_are_governed_api_contracts() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    expected = {
        "/api/inventory/batches",
        "/api/inbound/create",
        "/api/outbound/create",
        "/api/replenishment",
        "/api/inventory/shipments",
        "/api/inventory/shipments/dispatch",
        "/api/inventory/shipments/arrive",
        "/api/inventory/shipments/cancel",
        "/api/returns/pending",
        "/api/gis/overview",
        "/api/reports/summary",
    }
    assert expected.issubset(paths)


def test_organization_v2_routes_are_governed_api_contracts() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    expected = {
        "/api/users",
        "/api/permissions/topology",
        "/api/org/structure",
        "/api/org/templates",
        "/api/org/template-preview",
        "/api/org/apply-template",
        "/api/org/departments",
        "/api/org/departments/{unit_id}",
        "/api/org/departments/{unit_id}/archive",
        "/api/org/departments/{unit_id}/permissions",
        "/api/org/departments/{unit_id}/navigation",
        "/api/org/positions",
        "/api/org/positions/{position_id}",
        "/api/org/positions/{position_id}/archive",
        "/api/org/positions/{position_id}/navigation",
        "/api/org/users/{user_id}/assign",
        "/api/org/users/{user_id}/permissions",
        "/api/org/users/{user_id}/navigation",
    }
    assert expected.issubset(paths)
