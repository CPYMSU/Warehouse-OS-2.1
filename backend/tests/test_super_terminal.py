from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

from fastapi.testclient import TestClient

from app.api import capability_gateway
from app.api.deps import ActorContext, current_actor
from app.main import app
from app.services import (
    database_runtime,
    legacy_capability_runtime,
    legacy_read_runtime,
    warehouse_operations,
)
from app.services.legacy_capability_runtime import SUPPORTED_CAPABILITY_TOOLS
from app.terminal import executor, legacy_catalog
from app.terminal.adapters import verified_adapter_snapshot
from app.terminal.catalog import (
    ai_capability_candidates,
    ai_capability_gene_index,
    ai_capability_genes,
    availability,
    platform_entries,
    tenant_entries,
)
from app.terminal.gateway import (
    ContractMatch,
    execute_gateway_contract,
    gateway_contract_ready,
    match_contract,
)

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
    assert len(tenant_entries()) == 504
    assert len(platform_entries()) == 22
    assert len({entry["tool_name"] for entry in tenant_entries()}) == 504


def test_retired_contracts_are_excluded_from_model_discovery() -> None:
    retired_tool = "digital_market_site_publish"
    assert retired_tool not in {item["tool_name"] for item in ai_capability_gene_index()}
    assert retired_tool not in {
        item["tool_name"] for item in ai_capability_candidates("發布站點文件", limit=50)
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
    assert len(names) == 504
    assert response.json()["total"] == 504
    assert response.json()["executable"] > 2
    states = {item["command"]: item for item in response.json()["commands"]}
    assert states["whoami"]["availability"] == "active"
    assert states["warehouse list"]["allowed"] is True
    assert states["inv list"]["availability"] == "active"
    assert states["inv list"]["allowed"] is True
    assert states["inv list"]["execution_kind"] == "verified_adapter"
    assert states["inv list"]["adapter"] == "verified_registry"
    assert states["dm site publish"]["availability"] == "retired_2_0"
    assert states["dm site publish"]["allowed"] is False
    for command in (
        "dm db service list",
        "dm db service create",
        "dm db browser show",
        "dm db browser configure",
        "dm db onboarding",
    ):
        assert states[command]["availability"] == "active"
    assert status["tenant_command_count"] == 504
    assert status["platform_command_count"] == 22
    assert status["active_tenant_command_count"] == 498
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
    assert len(tools.json()["tools"]) == 520
    assert len(tools.json()["capability_states"]) == 520
    assert tools.json()["catalogue_scope"] == "global_command_metadata"
    assert tools.json()["data_scope"] == "current_tenant_only"
    states = {item["tool_name"]: item for item in tools.json()["capability_states"]}
    assert states["inventory_list"]["availability"] == "active"
    assert states["inventory_list"]["execution_kind"] == "verified_adapter"
    assert states["database_catalog"]["availability"] == "active"
    assert states["database_schema"]["availability"] == "active"
    assert states["database_query"]["availability"] == "active"
    assert states["database_execute"]["availability"] == "active"
    assert states["digital_market_database_project_create"]["availability"] == "active"
    assert states["digital_market_database_onboarding"]["availability"] == "active"
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
    assert {
        "database_catalog",
        "database_schema",
        "database_query",
        "database_execute",
    }.issubset({item["tool_name"] for item in recovery["available_capabilities"]})


def test_auto_runtime_repairs_hosting_runtime_scalar_after_exact_422(monkeypatch) -> None:
    observed_values: list[dict[str, object]] = []

    def dispatch(_entry, _actor_value, values, *, origin):
        assert origin == "auto_runtime"
        observed_values.append(dict(values))
        desired_state = values["body.desired_state"]
        if desired_state["runtime"] == "static":
            raise executor.CommandAdapterError(
                422,
                {"detail": "desired_state.runtime must be an object"},
            )
        return {"session": {"status": "planning", "desired_state": desired_state}}

    monkeypatch.setattr(executor, "_dispatch", dispatch)
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())

    result = executor.execute_runtime_tool_call(
        _actor(),
        "digital_market_hosting_start",
        {
            "workspace": "bonfire-qa",
            "message": "convert to static hosting",
            "desired-state": {"runtime": "static", "storage": {"code": "hdd"}},
            "execute": False,
        },
    )

    assert result["status"] == "succeeded"
    assert len(observed_values) == 2
    assert observed_values[1]["body.desired_state"] == {
        "runtime": {"type": "static"},
        "storage": {"code": "hdd"},
    }
    assert result["contract_recovery"]["corrected_fields"] == [
        "body.desired_state.runtime"
    ]
    assert result["contract_recovery"]["retry_count"] == 1


def test_auto_runtime_does_not_rewrite_an_unrelated_422(monkeypatch) -> None:
    attempts = 0

    def rejected(*_args: object, **_kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        raise executor.CommandAdapterError(422, {"detail": "workspace is invalid"})

    monkeypatch.setattr(executor, "_dispatch", rejected)
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())

    result = executor.execute_runtime_tool_call(
        _actor(),
        "digital_market_hosting_start",
        {
            "workspace": "bonfire-qa",
            "message": "convert to static hosting",
            "desired-state": {"runtime": "static"},
        },
    )

    assert result["status"] == "target_rejected"
    assert attempts == 1


def test_verified_inventory_adapter_executes_canonical_service(monkeypatch) -> None:
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    monkeypatch.setattr(
        warehouse_operations,
        "inventory_list_payload",
        lambda _actor, *, category=None: {
            "source": "warehouse.inventory_balance",
            "category": category,
            "items": [{"itemId": "I-1", "stock": 8}],
            "effect_verified": True,
        },
    )

    result = executor.execute_tool_call(
        _actor(),
        "inventory_list",
        {"category": "safety_tool"},
    )

    assert result["status"] == "succeeded"
    assert result["data"] == {
        "source": "warehouse.inventory_balance",
        "category": "safety_tool",
        "items": [{"itemId": "I-1", "stock": 8}],
        "effect_verified": True,
    }


def test_verified_adapter_registry_covers_the_complete_retained_runtime() -> None:
    snapshot = verified_adapter_snapshot()

    assert snapshot["count"] == 281
    assert snapshot["read_count"] == 90
    assert snapshot["write_count"] == 191
    assert set(snapshot["tool_names"]) == (
        legacy_read_runtime.SUPPORTED_LEGACY_READS
        | SUPPORTED_CAPABILITY_TOOLS
        | {
            "category_list_tenant",
            "db_query",
            "db_schema",
            "inventory_list",
            "ledger_list",
            "task_create",
            "task_delete",
            "task_history",
            "task_list",
            "task_meta",
            "task_resolve",
            "task_show",
            "task_status",
            "task_update",
        }
    )


def test_every_generic_retained_write_has_a_creation_or_target_path() -> None:
    special_handlers = {
        "agent_run_undo",
        "db_exec",
        "inventory_reset",
        "profile_reset",
        "record_cli_key_issue",
        "script_run",
        "user_add",
    }
    target_destinations = set(legacy_capability_runtime._ENTITY_KEY_DESTINATIONS)
    unreachable: list[str] = []
    for entry in legacy_catalog.COMMANDS:
        tool_name = str(entry["tool_name"])
        if tool_name not in legacy_capability_runtime.SUPPORTED_WRITE_TOOLS:
            continue
        if tool_name in special_handlers:
            continue
        creates_or_targets_collection = (
            legacy_capability_runtime._is_create(tool_name)
            or legacy_capability_runtime._is_upsert(tool_name)
            or tool_name in legacy_capability_runtime._COLLECTION_OPERATIONS
        )
        parameter_destinations = {
            str(parameter.get("dest") or "") for parameter in entry.get("params") or []
        }
        if not creates_or_targets_collection and not (target_destinations & parameter_destinations):
            unreachable.append(tool_name)

    assert unreachable == []


def test_retained_read_adapter_executes_explicit_read_runtime(monkeypatch) -> None:
    actor = ActorContext(
        **{
            **_actor().__dict__,
            "permissions": frozenset({"records.config.manage"}),
        }
    )
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    monkeypatch.setattr(
        legacy_read_runtime,
        "execute_legacy_read",
        lambda tool_name, _actor, values, *, origin: {
            "tool_name": tool_name,
            "query": values["query.q"],
            "origin": origin,
            "effect_verified": True,
        },
    )

    result = executor.execute_tool_call(
        actor,
        "record_type_resolve",
        {"q": "人員檔案", "limit": 6},
    )

    assert result["status"] == "succeeded"
    assert result["data"] == {
        "tool_name": "record_type_resolve",
        "query": "人員檔案",
        "origin": "ai_tool",
        "effect_verified": True,
    }


def test_retained_read_projection_registry_is_complete() -> None:
    assert legacy_read_runtime.SUPPORTED_LEGACY_READS == (
        frozenset(legacy_read_runtime.PROJECTION_READS) | legacy_read_runtime.CUSTOM_READS
    )
    assert len(legacy_read_runtime.PROJECTION_READS) == 31
    assert len(legacy_read_runtime.CUSTOM_READS) == 18


def test_original_verified_read_adapters_remain_registered() -> None:
    snapshot = verified_adapter_snapshot()

    assert {
        "read_count": snapshot["read_count"],
        "write_count": snapshot["write_count"],
    } == {"read_count": 90, "write_count": 191}
    assert {
        "category_list_tenant",
        "db_query",
        "db_schema",
        "inventory_list",
        "ledger_list",
    }.issubset(snapshot["tool_names"])


def test_retained_db_reader_permission_reaches_verified_adapter(monkeypatch) -> None:
    actor = ActorContext(
        **{
            **_actor().__dict__,
            "permissions": frozenset({"cli.db.read"}),
        }
    )
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    monkeypatch.setattr(
        database_runtime,
        "legacy_database_schema",
        lambda _actor, payload: {
            "legacy_command": "db_schema",
            "domain": payload["domain"],
            "effect_verified": True,
        },
    )

    result = executor.execute_tool_call(actor, "db_schema", {"domain": "warehouse"})

    assert result["status"] == "succeeded"
    assert result["data"]["domain"] == "warehouse"


def test_manual_buttons_are_generated_from_the_complete_shared_catalogue(monkeypatch) -> None:
    client = _client(monkeypatch)
    try:
        response = client.get("/api/business/actions")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()
    assert payload["total"] == 526
    assert payload["tenant_total"] == 504
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
    assert actions["digital_market_database_project_create"]["manual_execution"] == "unavailable"
    assert actions["digital_market_database_project_create"]["confirmation_required"] is True
    assert actions["digital_market_database_onboarding"]["manual_execution"] == "unavailable"
    assert actions["research_file_diff"]["command"] == "research file diff"
    assert actions["research_upload_contract"]["command"] == "research upload contract"
    assert actions["research_file_versions"]["command"] == "research file versions"
    assert actions["research_git_log"]["command"] == "research git log"
    assert actions["research_formats_list"]["command"] == "research formats list"
    assert actions["research_cli_show"]["command"] == "research cli show"
    assert actions["research_file_diff"]["category"] == "research"
    assert actions["research_project_list"]["authorized"] is False
    assert actions["research_project_list"]["manual_execution"] == "unavailable"


def test_digital_asset_topology_actions_share_one_ready_permission_boundary(
    monkeypatch,
) -> None:
    actor = ActorContext(
        **{
            **_actor().__dict__,
            "permissions": frozenset({"asset_mgmt.manage"}),
        }
    )
    app.dependency_overrides[current_actor] = lambda: actor
    monkeypatch.setattr(executor, "command_audit_writer", lambda: _AuditWriter())
    client = TestClient(app)
    try:
        response = client.get("/api/business/actions")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    actions = {item["tool_name"]: item for item in response.json()["actions"]}
    topology_tools = (
        "digital_market_create",
        "digital_market_workspace_create",
        "digital_market_assess",
        "digital_market_listing_create",
    )
    rows = [actions[tool_name] for tool_name in topology_tools]
    assert all("asset_mgmt.manage" in row["permission_any"] for row in rows)
    assert all(row["available"] is True for row in rows)
    assert all(row["authorized"] is True for row in rows)
    assert all(row["manual_execution"] == "execute" for row in rows)


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
    research_items = [item for item in response.json()["skills"] if item["category"] == "research"]
    research_skills = {item["skill_id"] for item in research_items}
    assert research_skills == RESEARCH_TOOLS
    assert len(research_skills) == 40
    assert (
        next(item for item in research_items if item["skill_id"] == "research_cli_show")["name"]
        == "research cli show"
    )


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


def test_every_non_retired_transport_contract_has_a_business_adapter() -> None:
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
    states = [availability(entry) for entry in tenant_entries()]
    assert states.count("active") == 498
    assert states.count("awaiting_domain_adapter") == 0
    assert states.count("retired_2_0") == 6


def test_retained_http_contract_uses_the_shared_execution_boundary(monkeypatch) -> None:
    monkeypatch.setattr(
        capability_gateway,
        "execute_api_contract",
        lambda actor, entry, values, *, origin: {
            "ok": True,
            "status": "succeeded",
            "tool_name": entry["tool_name"],
            "values": dict(values),
            "origin": origin,
        },
    )
    monkeypatch.setattr(
        capability_gateway,
        "current_actor",
        lambda **_kwargs: _actor(),
    )
    client = _client(monkeypatch)
    try:
        response = client.post(
            "/api/digital-assets/68/assess",
            headers={"X-Warehouse-Tool-Name": "digital_market_assess"},
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "ok": True,
        "status": "succeeded",
        "tool_name": "digital_market_assess",
        "values": {"path.id": "68"},
        "origin": "api",
    }


def test_legacy_projection_executor_is_permanently_fail_closed() -> None:
    entry = next(item for item in tenant_entries() if item["tool_name"] == "digital_market_assess")

    result = execute_gateway_contract(
        _actor(),
        ContractMatch(entry=entry, path_params={"id": "68"}),
        body={"claim": "completed"},
        origin="auto_runtime",
    )

    assert result == {
        "ok": False,
        "available": False,
        "status": "awaiting_domain_adapter",
        "reason": "transitional_projection_disabled",
        "tool_name": "digital_market_assess",
        "execution_kind": "capability_gap",
        "origin": "auto_runtime",
        "transitional_projection_authoritative": False,
    }


def test_database_runtime_is_company_scoped_not_a_platform_admin_escape() -> None:
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert "/api/admin/sql" not in paths
    assert "/api/platform/admin/sql" not in paths
    assert "/api/data/v2/database" in paths
    assert "/api/data/v2/database/schema" in paths
    assert "/api/data/v2/database/query" in paths
    assert "/api/data/v2/database/execute" in paths
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
