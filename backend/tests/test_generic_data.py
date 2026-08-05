from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services import auto_runtime
from app.services.templates import provision_tenant_template
from app.terminal.executor import execute_runtime_tool_call

pytestmark = pytest.mark.integration


def _actor(label: str) -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"data-{label}-{tenant_id.hex[:8]}"
    username = f"data-{label}-{user_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug, "name": f"Data Test {label}"},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "display_name": f"Data Owner {label}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=f"Data Test {label}",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level,
                  topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, 10, 10, 'Owner'
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "position_code": provisioned["admin_position_code"],
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=slug,
        tenant_name=f"Data Test {label}",
        industry_template_key="generic_warehouse",
        username=username,
        display_name=f"Data Owner {label}",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset(
            {"ai.use", "ai.database", "assets.read", "assets.manage"}
        ),
    )


def test_data_api_semantic_mutation_audit_gap_and_tenant_isolation() -> None:
    actor = _actor("fabric")
    outsider = _actor("outsider")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        resources = client.get("/api/data/v2/resources")
        assert resources.status_code == 200
        resource_keys = {item["resource_key"] for item in resources.json()["items"]}
        assert {
            "digital_asset.asset",
            "digital_asset.workspace",
            "digital_asset.asset_version",
            "digital_asset.artifact",
            "digital_asset.component",
            "digital_asset.database_binding",
            "digital_asset.api_credential",
            "digital_asset.deployment",
            "iam.organizational_unit",
            "iam.position_profile",
        }.issubset(resource_keys)

        workspace_schema = client.get(
            "/api/data/v2/resources/digital_asset.workspace/schema"
        )
        assert workspace_schema.status_code == 200
        field_modes = {
            field["field_key"]: field["editable_mode"]
            for field in workspace_schema.json()["fields"]
        }
        assert field_modes["runtime_type"] == "direct"
        assert field_modes["runtime_status"] == "derived"
        assert field_modes["public_url"] == "adapter_only"
        assert workspace_schema.json()["invariants"]

        asset = client.post(
            "/api/digital-assets",
            json={"name": "mk4", "asset_kind": "software"},
        ).json()["asset"]
        workspace = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "mk4-workspace", "runtime_type": "static"},
        ).json()["workspace"]
        assert workspace["revision"] == 1

        graph = client.post(
            "/api/data/v2/observe",
            json={
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
                "depth": 2,
            },
        )
        assert graph.status_code == 200
        graph_payload = graph.json()
        assert graph_payload["root"]["data"]["asset_id"] == asset["uuid"]
        assert graph_payload["world_observation"]["workflow_prescribed"] is False
        assert {
            "digital_asset.asset",
            "digital_asset.workspace",
            "digital_asset.component",
            "digital_asset.database_binding",
            "digital_asset.storage_binding",
        }.issubset(graph_payload["entities_by_resource"])
        assert any(
            relation["relation"] == "digital_asset.workspace.belongs_to_asset"
            for relation in graph_payload["relations"]
        )
        assert "digital_asset.deployment" in graph_payload["empty_related_resources"]
        assert any(
            observation["related_resource"] == "digital_asset.deployment"
            and observation["matched_count"] == 0
            for observation in graph_payload["relation_observations"]
        )

        resolved = client.post(
            "/api/data/v2/resolve",
            json={"resource": "digital_asset.workspace", "ref": "mk4-workspace"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["data"]["runtime_type"] == "static"

        preview = client.post(
            "/api/data/v2/mutations/preview",
            json={
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
                "expected_version": 1,
                "changes": {"runtime_type": "web"},
                "intent": "把 MK4 改成 Web 託管類型",
            },
        )
        assert preview.status_code == 200
        assert preview.json()["can_commit"] is True
        assert preview.json()["configuration_only"] is True
        assert preview.json()["judgment"]["preview_is_not_confirmation"] is True
        assert preview.json()["world_observation"]["decision_owner"] == "auto_runtime"

        request = {
            "resource": "digital_asset.workspace",
            "ref": "mk4-workspace",
            "expected_version": 1,
            "changes": {"runtime_type": "web"},
            "intent": "把 MK4 改成 Web 託管類型",
            "reasoning_summary": "普通配置欄位，沒有觸發部署副作用",
            "idempotency_key": f"test-{uuid4()}",
        }
        committed = client.post("/api/data/v2/mutations/commit", json=request)
        assert committed.status_code == 200
        payload = committed.json()
        assert payload["changed"] is True
        assert payload["coverage"] == "command_missing"
        assert payload["data"]["runtime_type"] == "web"
        assert payload["data"]["runtime_status"] == "provisioned"
        assert payload["version"] == 2
        assert payload["verification"]["matches_requested_changes"] is True
        assert payload["world_observation"]["verified_facts"]["database_changed"] is True

        replay = client.post("/api/data/v2/mutations/commit", json=request)
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True
        assert replay.json()["mutation_id"] == payload["mutation_id"]

        blocked = client.post(
            "/api/data/v2/mutations/commit",
            json={
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
                "changes": {"runtime_status": "ready"},
                "intent": "不能用配置修改假裝部署完成",
            },
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["reason"] == "native_adapter_required"

        false_site = client.post(
            "/api/data/v2/mutations/commit",
            json={
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
                "changes": {"public_url": "https://unverified.example.test"},
                "intent": "不能用資料庫欄位假裝站點已部署",
            },
        )
        assert false_site.status_code == 409
        assert false_site.json()["detail"]["reason"] == "native_adapter_required"

        queried = client.post(
            "/api/data/v2/query",
            json={
                "resource": "digital_asset.asset",
                "filters": {"name": "mk4"},
            },
        )
        assert queried.status_code == 200
        assert queried.json()["total"] == 1
        assert queried.json()["items"][0]["data"]["asset_kind"] == "software"

        run_id = uuid4()
        runtime_result = execute_runtime_tool_call(
            actor,
            "generic_data_mutate",
            {
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
                "changes": {"region": "ap-east"},
                "expected-version": "2",
                "intent": "調整 MK4 工作區區域配置",
                "reasoning": "已解析真實工作區，欄位可直接修改",
            },
            execution_context={"run_id": str(run_id)},
        )
        assert runtime_result["status"] == "succeeded"
        assert runtime_result["data"]["data"]["region"] == "ap-east"

        with tenant_session(actor.tenant_id) as session:
            mutations = session.execute(
                text(
                    """
                    SELECT origin, coverage, execution_identity, run_id, status
                    FROM secretariat.data_mutations
                    ORDER BY created_at
                    """
                )
            ).mappings().all()
            gaps = session.execute(
                text(
                    """
                    SELECT resource_key, occurrence_count, suggested_tool_name
                    FROM terminal.capability_gaps
                    ORDER BY resource_key, suggested_tool_name
                    """
                )
            ).mappings().all()
        assert len(mutations) == 4
        assert mutations[0]["origin"] == "api"
        assert mutations[0]["execution_identity"] == "requesting_user"
        assert mutations[1]["status"] == "conflict"
        assert mutations[2]["status"] == "conflict"
        assert mutations[3]["origin"] == "auto_runtime"
        assert mutations[3]["execution_identity"] == "company_ai"
        assert mutations[3]["run_id"] == run_id
        assert all(row["coverage"] == "command_missing" for row in mutations)
        assert {row["suggested_tool_name"] for row in gaps} == {
            "digital_asset_workspace_update"
        }

        mutation_timeline = client.get(
            "/api/data/v2/mutations",
            params={
                "resource": "digital_asset.workspace",
                "ref": "mk4-workspace",
            },
        )
        assert mutation_timeline.status_code == 200
        assert mutation_timeline.json()["total"] == 4
        assert mutation_timeline.json()["items"][0]["verification"]["read_back"] is True

        gap_timeline = client.get(
            "/api/data/v2/capability-gaps",
            params={"status": "observed"},
        )
        assert gap_timeline.status_code == 200
        assert gap_timeline.json()["total"] == 2
        assert {
            tuple(item["field_set"]) for item in gap_timeline.json()["items"]
        } == {("region",), ("runtime_type",)}

        app.dependency_overrides[current_actor] = lambda: outsider
        isolated = client.post(
            "/api/data/v2/resolve",
            json={"resource": "digital_asset.workspace", "ref": "mk4-workspace"},
        )
        assert isolated.status_code == 404
    finally:
        app.dependency_overrides.pop(current_actor, None)


def test_auto_runtime_sees_resource_atlas_and_executes_generic_mutation(
    monkeypatch,
) -> None:
    actor = _actor("runtime-fabric")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "Runtime MK4", "asset_kind": "software"},
        ).json()["asset"]
        client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "runtime-mk4", "runtime_type": "static"},
        )

        replies = iter(
            [
                {
                    "interaction_mode": "operational",
                    "understood_goal": "把 Runtime MK4 工作區類型改成 Web",
                    "message": "我會解析並修改託管工作區配置。",
                    "needs_tools": True,
                    "requires_user_input": False,
                    "selected_tool_names": ["generic_data_mutate"],
                    "selected_domains": ["system"],
                    "selected_families": ["system:data"],
                    "context_requests": [],
                    "success_criteria": ["runtime_type 已讀回為 web"],
                    "uncertainties": [],
                    "reasoning": "這是普通配置欄位修改，不需要偽造部署狀態。",
                    "memory_depth": "index",
                },
                {
                    "message": "準備修改並核驗。",
                    "plan": ["修改 runtime_type", "讀回核驗"],
                    "decisions": [
                        {
                            "tool_name": "generic_data_mutate",
                            "judgment": "execute",
                            "arguments": {
                                "resource": "digital_asset.workspace",
                                "ref": "runtime-mk4",
                                "changes": {"runtime_type": "web"},
                                "expected-version": "1",
                                "intent": "把 Runtime MK4 改成 Web 託管類型",
                                "reasoning": "欄位為 direct，部署狀態保持不變",
                            },
                            "reasoning": "使用通用語義資料能力完成缺少指令的修改。",
                            "continue_after_result": True,
                        }
                    ],
                    "completion_assessment": {
                        "complete": False,
                        "reason": "等待讀回結果",
                    },
                },
                {
                    "message": (
                        "已把 Runtime MK4 的託管類型改為 Web；"
                        "這只是配置修改，尚未宣稱後端已部署。"
                    ),
                    "goal_complete": True,
                    "evidence": ["generic mutation read-back verified"],
                    "contradictions": [],
                    "revised_plan": [],
                    "continue_reason": "goal complete",
                    "continue_autonomously": False,
                    "requires_user_input": False,
                    "next_domains": [],
                    "next_families": [],
                    "next_decisions": [],
                    "memory_candidate": None,
                },
            ]
        )
        calls: list[dict[str, object]] = []

        class _ModelResponse:
            def __init__(self, payload: dict[str, object]):
                self.payload = payload

            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, object]:
                return {
                    "choices": [
                        {"message": {"content": json.dumps(self.payload, ensure_ascii=False)}}
                    ]
                }

        monkeypatch.setattr(
            auto_runtime,
            "connected_deepseek",
            lambda *_args: SimpleNamespace(
                base_url="https://model.example.test",
                api_key="secret",
                model="runtime-test",
            ),
        )

        def fake_post(*_args, **kwargs):
            calls.append(kwargs)
            return _ModelResponse(next(replies))

        monkeypatch.setattr(auto_runtime.httpx, "post", fake_post)
        result = auto_runtime.run_auto_runtime(
            actor,
            SimpleNamespace(),
            "把 Runtime MK4 工作區類型改成 Web",
            surface="assistant",
        )

        assert result.reflection["goal_complete"] is True
        assert result.tool_results[0]["tool_name"] == "generic_data_mutate"
        assert result.tool_results[0]["result"]["status"] == "succeeded"
        assert "尚未宣稱後端已部署" in result.message
        assert result.observations["semantic_resources"] >= 4
        first_request = calls[0]["json"]
        assert "digital_asset.workspace" in first_request["messages"][-1]["content"]

        resolved = client.post(
            "/api/data/v2/resolve",
            json={"resource": "digital_asset.workspace", "ref": "runtime-mk4"},
        ).json()
        assert resolved["data"]["runtime_type"] == "web"
        assert resolved["data"]["runtime_status"] == "provisioned"

        with tenant_session(actor.tenant_id) as session:
            mutation = session.execute(
                text(
                    """
                    SELECT run_id, origin, execution_identity
                    FROM secretariat.data_mutations
                    WHERE resource_ref = 'runtime-mk4'
                    """
                )
            ).mappings().one()
        assert str(mutation["run_id"]) == result.run_id
        assert mutation["origin"] == "auto_runtime"
        assert mutation["execution_identity"] == "company_ai"
    finally:
        app.dependency_overrides.pop(current_actor, None)


def test_company_ai_database_runtime_inspects_queries_and_writes_real_tables() -> None:
    actor = _actor("database-runtime")
    outsider = _actor("database-outsider")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        human_only_actor = replace(
            actor,
            permissions=actor.permissions - {"ai.database"},
        )
        app.dependency_overrides[current_actor] = lambda: human_only_actor
        denied_catalog = client.get("/api/data/v2/database")
        assert denied_catalog.status_code == 403
        app.dependency_overrides[current_actor] = lambda: actor

        asset = client.post(
            "/api/digital-assets",
            json={"name": "Database MK4", "asset_kind": "software"},
        ).json()["asset"]
        client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "database-mk4", "runtime_type": "static"},
        )

        catalog = client.get("/api/data/v2/database")
        assert catalog.status_code == 200
        assert catalog.json()["ai_decides_usage"] is True
        relation = next(
            item
            for item in catalog.json()["relations"]
            if item["table"] == "digital_asset.workspaces"
        )
        assert relation["can_select"] is True
        assert relation["can_update"] is True
        assert "id" in relation["primary_key"]

        schema = client.post(
            "/api/data/v2/database/schema",
            json={"table": "digital_asset.workspaces"},
        )
        assert schema.status_code == 200
        assert {"id", "tenant_id", "workspace_key", "region"}.issubset(
            schema.json()["column_headers"]
        )
        assert any(
            item["constraint_type"] == "primary_key"
            for item in schema.json()["constraints"]
        )
        assert schema.json()["world_observation"]["verified_facts"][
            "physical_schema_visible"
        ] is True

        legacy_schema = execute_runtime_tool_call(
            actor,
            "db_schema",
            {"table": "digital_asset.workspaces"},
        )
        assert legacy_schema["status"] == "succeeded"
        assert legacy_schema["data"]["legacy_command"] == "db_schema"
        assert "workspace_key" in legacy_schema["data"]["column_headers"]

        inventory = execute_runtime_tool_call(actor, "inventory_list", {})
        categories = execute_runtime_tool_call(actor, "category_list_tenant", {})
        ledger = execute_runtime_tool_call(
            actor,
            "ledger_list",
            {"category": "safety_tool"},
        )
        assert inventory["status"] == "succeeded"
        assert inventory["data"]["source"] == "warehouse.inventory_balance"
        assert categories["status"] == "succeeded"
        assert categories["data"]["source"] == "warehouse.item_category"
        assert ledger["status"] == "succeeded"
        assert ledger["data"]["source"] == "warehouse.stock_ledger"

        queried = execute_runtime_tool_call(
            actor,
            "database_query",
            {
                "sql": (
                    "SELECT workspace_key, config->>'runtime_type' AS runtime_type, region "
                    "FROM digital_asset.workspaces "
                    "WHERE workspace_key=:workspace_key"
                ),
                "parameters": {"workspace_key": "database-mk4"},
                "limit": 20,
            },
            execution_context={"run_id": str(uuid4())},
        )
        assert queried["status"] == "succeeded"
        assert queried["data"]["columns"] == [
            "workspace_key",
            "runtime_type",
            "region",
        ]
        assert queried["data"]["rows"][0]["workspace_key"] == "database-mk4"

        legacy_queried = execute_runtime_tool_call(
            actor,
            "db_query",
            {
                "sql": (
                    "SELECT workspace_key FROM digital_asset.workspaces "
                    "WHERE workspace_key='database-mk4'"
                ),
                "limit": 20,
            },
        )
        assert legacy_queried["status"] == "succeeded"
        assert legacy_queried["data"]["legacy_command"] == "db_query"
        assert legacy_queried["data"]["rows"] == [
            {"workspace_key": "database-mk4"}
        ]

        run_id = uuid4()
        written = execute_runtime_tool_call(
            actor,
            "database_execute",
            {
                "sql": (
                    "UPDATE digital_asset.workspaces SET region=:region "
                    "WHERE workspace_key=:workspace_key "
                    "RETURNING id, workspace_key, region"
                ),
                "parameters": {
                    "workspace_key": "database-mk4",
                    "region": "ai-selected-region",
                },
                "verification-sql": (
                    "SELECT workspace_key, region FROM digital_asset.workspaces "
                    "WHERE workspace_key=:workspace_key"
                ),
                "verification-parameters": {"workspace_key": "database-mk4"},
                "intent": "AI 判断直接通过数据库完成区域字段更新",
                "reasoning": "当前公司数据库身份有写权限，使用同事务读回核验",
            },
            execution_context={"run_id": str(run_id)},
        )
        assert written["status"] == "succeeded"
        assert written["data"]["rows"][0]["region"] == "ai-selected-region"
        assert written["data"]["verification"]["rows"] == [
            {"workspace_key": "database-mk4", "region": "ai-selected-region"}
        ]
        assert written["data"]["world_observation"]["verified_facts"][
            "transaction_committed"
        ] is True

        rejected_write_on_query = client.post(
            "/api/data/v2/database/query",
            json={
                "sql": (
                    "UPDATE digital_asset.workspaces SET region='must-not-change' "
                    "WHERE workspace_key='database-mk4'"
                )
            },
        )
        assert rejected_write_on_query.status_code == 422
        assert rejected_write_on_query.json()["detail"]["reason"] == (
            "database_query_rejected"
        )

        app.dependency_overrides[current_actor] = lambda: outsider
        isolated = client.post(
            "/api/data/v2/database/query",
            json={
                "sql": (
                    "SELECT workspace_key, region FROM digital_asset.workspaces "
                    "WHERE workspace_key=:workspace_key"
                ),
                "parameters": {"workspace_key": "database-mk4"},
            },
        )
        assert isolated.status_code == 200
        assert isolated.json()["rows"] == []

        with tenant_session(actor.tenant_id) as session:
            write_audit = session.execute(
                text(
                    """
                    SELECT payload
                    FROM audit.events
                    WHERE event_type = 'database.runtime.write.succeeded'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
            ).scalar_one()
        assert write_audit["run_id"] == str(run_id)
        assert "UPDATE digital_asset.workspaces" in write_audit["sql"]
    finally:
        app.dependency_overrides.pop(current_actor, None)
