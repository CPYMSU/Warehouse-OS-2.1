from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.deps import ActorContext, current_actor
from app.main import app
from app.terminal import executor
from app.terminal.catalog import platform_entries, tenant_entries


class _AuditWriter:
    def record(self, **_kwargs: object) -> str:
        return "00000000-0000-0000-0000-000000000099"


class _WarehouseReader:
    def list_active(self, _tenant_id: UUID) -> list[dict[str, object]]:
        return [{"id": "warehouse-1", "code": "A01", "name": "Main warehouse", "active": True}]


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
    monkeypatch.setattr(executor, "warehouse_reader", lambda: _WarehouseReader())
    return TestClient(app)


def test_imported_catalogue_has_complete_legacy_command_counts() -> None:
    assert len(tenant_entries()) == 419
    assert len(platform_entries()) == 22
    assert len({entry["tool_name"] for entry in tenant_entries()}) == 419


def test_terminal_only_advertises_currently_executable_commands(monkeypatch) -> None:
    client = _client(monkeypatch)
    try:
        response = client.get("/api/cli/commands")
        names = {item["command"] for item in response.json()["commands"]}
        status = client.get("/api/cli/migration-status").json()
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert names == {"whoami", "warehouse list"}
    assert status["tenant_command_count"] == 419
    assert status["platform_command_count"] == 22
    assert status["active_tenant_command_count"] == 2
    assert status["awaiting_domain_adapter_count"] == 417


def test_human_and_ai_paths_share_the_same_command_adapter(monkeypatch) -> None:
    client = _client(monkeypatch)
    try:
        human = client.post("/api/cli/exec", json={"line": "warehouse list"})
        ai = client.post("/api/ai/tools/auth_me/execute", json={"arguments": {}})
        unready = client.post("/api/cli/exec", json={"line": "inv list"})
        tools = client.get("/api/ai/tools")
    finally:
        app.dependency_overrides.clear()

    assert human.status_code == 200
    assert human.json()["status"] == "succeeded"
    assert human.json()["data"]["warehouses"][0]["code"] == "A01"
    assert ai.status_code == 200
    assert ai.json()["status"] == "succeeded"
    assert ai.json()["data"]["user"]["username"] == "owner"
    assert unready.json()["status"] == "awaiting_domain_adapter"
    assert len(tools.json()["tools"]) == 441
    assert len(tools.json()["capability_states"]) == 441
    assert tools.json()["catalogue_scope"] == "global_command_metadata"
    assert tools.json()["data_scope"] == "current_tenant_only"
    states = {item["tool_name"]: item for item in tools.json()["capability_states"]}
    assert states["inventory_list"]["availability"] == "awaiting_domain_adapter"
    assert states["p_owner_grant"]["availability"] == "requires_l11_governance"


def test_no_generic_sql_super_api_is_exposed() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/admin/sql" not in paths
    assert "/api/platform/admin/sql" not in paths
    assert "/api/ai/tools/{tool_name}/execute" in paths


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
