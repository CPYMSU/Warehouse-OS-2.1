from __future__ import annotations

import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api import router as api_router
from app.api.deps import ActorContext, current_actor
from app.api.schemas import AgentRunRequest
from app.main import app
from app.services import auto_runtime, integrations, memory_fabric
from app.services.auto_runtime import RuntimeResult, runtime_capability_map
from app.services.runtime_context import expand_capability_domains
from app.services.runtime_output import public_data
from app.terminal.catalog import (
    ai_capability_atlas,
    ai_capability_candidates,
    ai_capability_gene_index,
)


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


def _events(response) -> list[dict[str, object]]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_background_memory_steward_pre_distils_with_flash(monkeypatch) -> None:
    captured: dict[str, object] = {}
    model_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        integrations,
        "connected_deepseek",
        lambda *_args: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="configured-model",
        ),
    )

    def fake_chat_completion(_connection, **kwargs):
        model_calls.append(
            {
                "model": _connection.model,
                **kwargs,
            }
        )
        return "{}"

    def fake_process(_actor, *, complete, model, max_jobs):
        captured.update(model=model, max_jobs=max_jobs)
        complete("Return JSON.", '{"complete_turn":true}')
        return [{"status": "distilled"}]

    monkeypatch.setattr(integrations, "chat_completion", fake_chat_completion)
    monkeypatch.setattr(memory_fabric, "process_pending_distillations", fake_process)

    result = memory_fabric.run_background_memory_steward(_actor(), SimpleNamespace())

    assert result == [{"status": "distilled"}]
    assert captured == {"model": "deepseek-v4-flash", "max_jobs": 4}
    assert model_calls == [
        {
            "model": "deepseek-v4-flash",
            "system_prompt": "Return JSON.",
            "user_prompt": '{"complete_turn":true}',
            "thinking": False,
            "max_tokens": 1_800,
            "json_mode": True,
        }
    ]


def test_runtime_capability_map_is_domain_oriented_not_a_command_list() -> None:
    capabilities = runtime_capability_map()

    assert capabilities
    assert all({"domain", "capability", "kind", "state"}.issubset(item) for item in capabilities)
    assert all("command" not in item and "tool_name" not in item for item in capabilities)


def test_router_repairs_malformed_control_json_without_exposing_it(monkeypatch) -> None:
    malformed = """{
      "interaction_mode": "operational",
      "understood_goal": "托管 AI 智能架构平台并签发 Key,
      "message": "我会建立托管工作区并签发一次性 Key。",
      "needs_tools": true,
      "requires_user_input": false,
      "selected_domains": [],
      "selected_families": [],
      "context_requests": ["authority"],
      "success_criteria": ["工作区已建立"],
      "uncertainties": [],
      "reasoning": "internal route",
      "memory_depth": "index"
    }"""
    repaired = json.dumps(
        {
            "interaction_mode": "operational",
            "understood_goal": "托管 AI 智能架构平台并签发 Key",
            "message": "我會建立託管工作區並透過安全卡交付一次性 Key。",
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": [],
            "selected_families": [],
            "context_requests": ["authority"],
            "success_criteria": ["工作區已建立"],
            "uncertainties": [],
            "reasoning": "internal route",
            "memory_depth": "index",
        },
        ensure_ascii=False,
    )
    phases: list[str] = []

    def fake_completion(*_args, **kwargs):
        phases.append(str(kwargs["phase"]))
        return malformed if len(phases) == 1 else repaired

    monkeypatch.setattr(auto_runtime, "_completion", fake_completion)
    route, raw = auto_runtime._route_goal(
        SimpleNamespace(model="test"),
        "我需要托管 AI 智能架构平台并给我 Key",
        {
            "L0_permanent_world_map": {
                "capability_atlas": [],
                "resource_atlas": [],
                "expansion_protocol": {},
            },
            "L2_current_goal": {"language_contract": {"locale": "zh-Hant"}},
            "L3_execution_working_set": {},
        },
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    assert raw == malformed
    assert phases == ["route", "route_format_repair"]
    assert route["needs_tools"] is True
    assert route["message"] == "我會建立託管工作區並透過安全卡交付一次性 Key。"
    assert "interaction_mode" not in str(route["message"])


def test_router_stops_safely_when_control_json_and_repair_are_malformed(
    monkeypatch,
) -> None:
    leaked = '{"interaction_mode":"operational","reasoning":"private chain"'
    monkeypatch.setattr(auto_runtime, "_completion", lambda *_a, **_k: leaked)

    route, _ = auto_runtime._route_goal(
        SimpleNamespace(model="test"),
        "托管一个新项目",
        {
            "L0_permanent_world_map": {
                "capability_atlas": [],
                "resource_atlas": [],
                "expansion_protocol": {},
            },
            "L2_current_goal": {"language_contract": {"locale": "zh-Hans"}},
            "L3_execution_working_set": {},
        },
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    assert route["needs_tools"] is False
    assert route["requires_user_input"] is True
    assert "interaction_mode" not in str(route["message"])
    assert "private chain" not in str(route["message"])
    assert "格式异常" in str(route["message"])


def test_database_request_router_receives_exact_candidate_input_contract(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_completion(_connection, **kwargs):
        captured.update(kwargs)
        return json.dumps(
            {
                "interaction_mode": "operational",
                "understood_goal": "申请独立托管资料库",
                "message": "请提供专案名称、精确 HTTPS Origin 与集合读写规则。",
                "needs_tools": False,
                "requires_user_input": True,
                "selected_domains": [],
                "selected_families": [],
                "context_requests": [],
                "success_criteria": ["申请参数齐全后生成确认卡"],
                "uncertainties": ["专案名称、Origin 与集合规则尚未提供"],
                "reasoning": "先收集用户明确要求追问的输入",
                "memory_depth": "index",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(auto_runtime, "_completion", fake_completion)
    route, _raw = auto_runtime._route_goal(
        SimpleNamespace(),
        (
            "我要单独申请托管资料库服务，不部署 Runtime；请追问专案名称、"
            "精确 HTTPS Origin 和 owner/session 集合规则。"
        ),
        {
            "L0_permanent_world_map": {
                "capability_atlas": [],
                "resource_atlas": [],
                "expansion_protocol": {},
            },
            "L1_current_company_and_people": {},
            "L2_current_goal": {"language_contract": {"locale": "zh-Hans"}},
            "L3_execution_working_set": {},
        },
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    router_world = json.loads(str(captured["user_prompt"]))["router_world"]
    contract = next(
        item
        for item in router_world["catalogue_candidate_contracts"]
        if item["tool_name"] == "digital_market_database_project_create"
    )
    assert contract["parameters"]["required"] == ["name"]
    assert "allowed-origins" in contract["parameters"]["properties"]
    assert "rules" in contract["parameters"]["properties"]
    assert route["requires_user_input"] is True
    assert route["needs_tools"] is False


def test_model_selected_operational_mode_always_enters_the_evidence_loop(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        auto_runtime,
        "_completion",
        lambda *_args, **_kwargs: json.dumps(
            {
                "interaction_mode": "operational",
                "understood_goal": "取得目前公司的交付物",
                "message": "",
                "needs_tools": False,
                "requires_user_input": False,
                "selected_domains": [],
                "selected_families": [],
                "context_requests": [],
                "success_criteria": ["交付物已由目前世界證據確認"],
                "uncertainties": [],
                "reasoning": "current evidence is required",
                "memory_depth": "index",
            },
            ensure_ascii=False,
        ),
    )

    route, _ = auto_runtime._route_goal(
        SimpleNamespace(),
        "給我目前公司的交付物",
        {
            "L0_permanent_world_map": {
                "capability_atlas": [],
                "resource_atlas": [],
                "expansion_protocol": {},
            },
            "L1_current_company_and_people": {},
            "L2_current_goal": {"language_contract": {"locale": "zh-Hant"}},
            "L3_execution_working_set": {},
        },
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    assert route["interaction_mode"] == "operational"
    assert route["needs_tools"] is True


def test_resource_locator_provenance_does_not_allow_derived_child_paths() -> None:
    entry = "https://bonfirework.org/assets/bonfire/pd-detection/"
    invented = "https://bonfirework.org/assets/bonfire/pd-detection/deploy-guide.md"

    assert (
        auto_runtime._unsupported_resource_locators(
            f"入口：{entry}",
            [{"entry_url": entry}],
        )
        == ()
    )
    assert auto_runtime._unsupported_resource_locators(
        f"文件：{invented}",
        [{"entry_url": entry}],
    ) == (invented,)


def test_grounding_sanitizes_an_unobserved_locator_without_a_model_repair(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        auto_runtime,
        "_completion",
        lambda *_args, **_kwargs: pytest.fail("locator sanitization must be deterministic"),
    )
    message, grounding = auto_runtime._finalize_grounded_message(
        message=("下載：https://bonfirework.org/assets/bonfire/pd-detection/deploy-guide.md"),
        locale="zh-Hant",
        grounding_sources=[{"entry_url": "https://bonfirework.org/assets/bonfire/pd-detection/"}],
        public_origin="https://bonfirework.org",
        unsupported_claims=[],
        force_reconciliation=False,
    )

    assert "deploy-guide.md" not in message
    assert "未驗證地址已移除" in message
    assert grounding["reconciled"] is True
    assert grounding["deterministic_sanitized"] is True


def test_missing_input_question_keeps_the_question_without_an_invented_example_url(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        auto_runtime,
        "_completion",
        lambda *_args, **_kwargs: pytest.fail("waiting-input sanitization must be deterministic"),
    )

    message, grounding = auto_runtime._finalize_grounded_message(
        message=(
            "请提供专案名称、精确 HTTPS Origin（例如 "
            "https://owner.github.io）以及需要 owner 读写的集合。"
        ),
        locale="zh-Hans",
        grounding_sources=[],
        public_origin="https://bonfirework.org",
        unsupported_claims=[],
        force_reconciliation=False,
        waiting_for_human_input=True,
    )

    assert "请提供专案名称" in message
    assert "owner.github.io" not in message
    assert "请填入实际地址" in message
    assert grounding["reconciled"] is False
    assert grounding["waiting_input_sanitized"] is True


def test_operational_completion_requires_observed_world_evidence() -> None:
    reflection = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "已完成。",
            "goal_complete": True,
            "continue_reason": "complete",
            "claims": [],
        },
        interaction_mode="operational",
        ledger=[
            {
                "evidence_id": "input:goal",
                "source_type": "human_report",
                "authority": "reported_not_verified",
            },
            {
                "evidence_id": "context:company_summary",
                "source_type": "current_tenant_context",
                "authority": "observed",
            },
        ],
    )

    assert reflection["goal_complete"] is False
    assert reflection["grounding"]["operational_without_world_evidence"] is True


def test_operational_question_does_not_require_world_evidence() -> None:
    reflection = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "请提供专案名称与精确 HTTPS Origin。",
            "goal_complete": False,
            "requires_user_input": True,
            "claims": [],
        },
        interaction_mode="operational",
        ledger=[
            {
                "evidence_id": "input:goal",
                "source_type": "human_report",
                "authority": "reported_not_verified",
            }
        ],
    )

    assert reflection["grounding"]["operational_without_world_evidence"] is False


def test_planner_question_is_a_deterministic_human_input_boundary() -> None:
    reflection = auto_runtime._apply_human_input_decision_boundary(
        {
            "message": "请提供缺少的申请参数。",
            "goal_complete": True,
            "continue_autonomously": True,
            "requires_user_input": False,
            "next_domains": ["dam"],
        },
        [
            {
                "tool_name": "digital_market_database_project_create",
                "judgment": "ask_person",
                "arguments": {},
            }
        ],
    )

    assert reflection["goal_complete"] is False
    assert reflection["continue_autonomously"] is False
    assert reflection["requires_user_input"] is True
    assert reflection["continue_reason"] == "waiting_for_human_input"
    assert reflection["next_domains"] == []


def test_material_claim_must_reference_an_existing_evidence_record() -> None:
    reflection = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "交付物存在。",
            "goal_complete": True,
            "claims": [
                {
                    "statement": "交付物存在",
                    "requires_evidence": True,
                    "evidence_refs": ["capability:missing"],
                }
            ],
        },
        interaction_mode="knowledge",
        ledger=[
            {
                "evidence_id": "input:goal",
                "source_type": "human_report",
                "authority": "reported_not_verified",
            }
        ],
    )

    assert reflection["goal_complete"] is False
    assert reflection["claims"][0]["evidence_refs"] == []
    assert reflection["claims"][0]["supported"] is False


def test_human_report_cannot_be_used_as_material_world_evidence() -> None:
    reflection = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "资产已建立。",
            "goal_complete": True,
            "continue_reason": "complete",
            "claims": [
                {
                    "statement": "资产已建立",
                    "requires_evidence": True,
                    "evidence_refs": ["input:goal"],
                }
            ],
        },
        interaction_mode="operational",
        ledger=[
            {
                "evidence_id": "input:goal",
                "source_type": "human_report",
                "authority": "reported_not_verified",
            }
        ],
    )

    assert reflection["goal_complete"] is False
    assert reflection["continue_reason"] == "world_evidence_required"
    assert reflection["claims"][0]["evidence_refs"] == []
    assert reflection["claims"][0]["supported"] is False


def test_single_successful_receipt_stages_autonomous_grounding_recovery() -> None:
    layers = {
        "L1_current_company_and_people": {},
        "L3_execution_working_set": {},
    }
    ledger = auto_runtime._evidence_ledger(
        "新开一个 MK53 Voyager 数字资产",
        layers,
        [
            {
                "evidence_id": "tool:1:1:digital_market_provision",
                "runtime_round": 1,
                "tool_name": "digital_market_provision",
                "result": {
                    "ok": True,
                    "signal": "runtime_execution_completed",
                    "action": {
                        "status": "completed",
                        "result": {
                            "asset_no": "DMA-20260804-0AD4019D",
                            "hosting_url": ("https://bonfirework.org/assets/bonfire/mk53-voyager/"),
                        },
                    },
                },
            }
        ],
    )
    reflection = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "MK53 Voyager 已建立。",
            "goal_complete": True,
            "continue_reason": "complete",
            "claims": [
                {
                    "statement": "MK53 Voyager 已建立",
                    "requires_evidence": True,
                    "evidence_refs": [],
                }
            ],
        },
        interaction_mode="operational",
        ledger=ledger,
    )

    claim = reflection["claims"][0]
    assert reflection["goal_complete"] is False
    assert claim["supported"] is False
    assert claim["evidence_refs"] == []

    mode = auto_runtime._stage_autonomous_grounding_recovery(reflection, layers)

    assert mode == "reflect_cumulative_evidence"
    assert reflection["continue_autonomously"] is True
    assert reflection["requires_user_input"] is False
    assert reflection["continue_reason"] == "autonomous_grounding_recovery"
    recovery = layers["L3_execution_working_set"]["grounding_recovery"]
    assert recovery["schema"] == "warehouse.autonomous-grounding-recovery.v1"
    assert recovery["verified_capability_effect_ids"] == ["tool:1:1:digital_market_provision"]

    recovered = auto_runtime._apply_reflection_evidence_contract(
        {
            "message": "MK53 Voyager 已建立。",
            "goal_complete": True,
            "continue_reason": "complete",
            "continue_autonomously": False,
            "requires_user_input": False,
            "claims": [
                {
                    "statement": "MK53 Voyager 已建立",
                    "requires_evidence": True,
                    "evidence_refs": ["tool:1:1:digital_market_provision"],
                }
            ],
        },
        interaction_mode="operational",
        ledger=ledger,
    )

    assert recovered["goal_complete"] is True
    assert recovered["claims"][0]["supported"] is True
    assert auto_runtime._stage_autonomous_grounding_recovery(recovered, layers) is None
    assert "grounding_recovery" not in layers["L3_execution_working_set"]


def test_public_message_firewall_blocks_control_envelopes_and_redacts_keys() -> None:
    blocked = auto_runtime._public_message(
        '{"interaction_mode":"operational","reasoning":"private"}',
        locale="zh-Hant",
    )
    redacted = auto_runtime._public_message(
        "已簽發 wak_abcdefghijklmnopqrstuvwxyz123456",
        locale="zh-Hant",
    )

    assert "interaction_mode" not in blocked
    assert "private" not in blocked
    assert "wak_abcdefghijklmnopqrstuvwxyz123456" not in redacted
    assert "[安全憑證卡]" in redacted


def test_public_structured_data_keeps_business_facts_but_drops_private_fields() -> None:
    projected = public_data(
        {
            "ok": True,
            "workspace": {"name": "mk4", "status": "ready"},
            "reasoning": "private chain",
            "system_prompt": "private prompt",
            "database_uri": "postgresql://owner:password@db.example/mk4",
            "nested": {
                "api_key": "wak_abcdefghijklmnopqrstuvwxyz123456",
                "count": 3,
            },
        },
        locale="zh-Hant",
    )

    assert projected["ok"] is True
    assert projected["workspace"] == {"name": "mk4", "status": "ready"}
    assert projected["nested"] == {"count": 3}
    assert "reasoning" not in projected
    assert "system_prompt" not in projected
    assert "database_uri" not in projected


def test_composite_capability_suppresses_a_redundant_lower_level_step() -> None:
    decisions = auto_runtime._apply_declarative_tool_composition(
        [
            {
                "tool_name": "digital_market_provision",
                "judgment": "execute",
                "arguments": {"name": "mk4"},
            },
            {
                "tool_name": "digital_market_key_issue",
                "judgment": "execute",
                "arguments": {"workspace": "mk4"},
            },
        ]
    )

    assert decisions[0]["judgment"] == "execute"
    assert decisions[1]["judgment"] == "superseded"
    assert decisions[1]["superseded_by"] == "digital_market_provision"


def test_runtime_preserves_world_observations_without_turning_them_into_workflows() -> None:
    observation = {
        "schema": "warehouse.world-observation.v1",
        "operation": "semantic_resource_graph.observe",
        "effect": "read",
        "primary_entity": {
            "resource": "digital_asset.workspace",
            "id": "292eaeca-46e3-4dff-8ffd-ce129360cbd2",
            "ref": "mk4-workspace",
        },
        "verified_facts": {"workspace_belongs_to_asset": True},
        "uncertainties": [],
        "affordances": [{"capability": "generic_data_observe"}],
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
    }

    projected = auto_runtime._world_observation_projection(
        [{"result": {"data": {"world_observation": observation}}}]
    )

    assert projected == [observation]
    assert projected[0]["primary_entity"]["ref"] == "mk4-workspace"
    assert projected[0]["workflow_prescribed"] is False


def test_runtime_preserves_atomic_recovery_as_optional_ai_affordance() -> None:
    recovery = {
        "schema": "warehouse.atomic-recovery.v1",
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
        "failed_capability": "digital_market_show",
        "available_capabilities": [{"tool_name": "generic_data_observe"}],
        "constraints": ["preserve_canonical_resource_identity"],
    }

    projected = auto_runtime._atomic_recovery_projection(
        [{"result": {"data": {"atomic_recovery": recovery}}}]
    )

    assert projected == [recovery]
    assert projected[0]["decision_owner"] == "auto_runtime"
    assert projected[0]["workflow_prescribed"] is False
    assert auto_runtime._recovery_capability_names(projected) == ["generic_data_observe"]


def test_database_structure_survives_bounded_model_projection() -> None:
    projected = auto_runtime._reference_value_projection(
        [
            {
                "tool_name": "database_schema",
                "result": {
                    "data": {
                        "table": "digital_asset.workspaces",
                        "column_headers": [
                            "id",
                            "tenant_id",
                            "workspace_key",
                            "config",
                            "region",
                            "revision",
                        ],
                        "columns": [
                            {"column_name": "id"},
                            {"column_name": "tenant_id"},
                            {"column_name": "workspace_key"},
                        ],
                    }
                },
            }
        ]
    )

    assert projected["table"] == ["digital_asset.workspaces"]
    assert projected["column_headers"] == [
        "id",
        "tenant_id",
        "workspace_key",
        "config",
        "region",
        "revision",
    ]
    assert projected["column_name"] == ["id", "tenant_id", "workspace_key"]


def test_runtime_ignores_unknown_recovery_capabilities() -> None:
    assert auto_runtime._recovery_capability_names(
        [
            {
                "schema": "warehouse.atomic-recovery.v1",
                "available_capabilities": [
                    {"tool_name": "invented_raw_sql_escape"},
                    {"tool_name": "generic_data_resolve"},
                    {"tool_name": "generic_data_resolve"},
                ],
            }
        ]
    ) == ["generic_data_resolve"]


def test_missing_adapter_attempt_cannot_prove_operational_completion() -> None:
    layers = {
        "L1_current_company_and_people": {},
        "L3_execution_working_set": {},
    }
    tool_results = [
        {
            "evidence_id": "tool:1:1:digital_market_assess",
            "runtime_round": 1,
            "tool_name": "digital_market_assess",
            "result": {
                "ok": False,
                "status": "awaiting_domain_adapter",
                "data": {
                    "execution_kind": "capability_gap",
                    "transitional_projection_authoritative": False,
                },
            },
        }
    ]

    ledger = auto_runtime._evidence_ledger("评估 mk4", layers, tool_results)
    capability_evidence = ledger[-1]
    assert capability_evidence["authority"] == "observed_attempt_only"
    assert capability_evidence["effect_verified"] is False

    reflected = auto_runtime._apply_reflection_evidence_contract(
        {
            "goal_complete": True,
            "claims": [
                {
                    "statement": "评估已经完成",
                    "requires_evidence": True,
                    "evidence_refs": [capability_evidence["evidence_id"]],
                }
            ],
        },
        interaction_mode="operational",
        ledger=ledger,
    )

    assert reflected["goal_complete"] is False
    assert reflected["grounding"]["operational_attempt_without_verified_effect"] is True
    assert reflected["grounding"]["verified_capability_effect_ids"] == []


def test_malformed_reflection_keeps_a_deterministic_execution_receipt() -> None:
    receipt = auto_runtime._deterministic_execution_receipt(
        [
            {
                "tool_name": "generic_data_mutate",
                "result": {
                    "ok": True,
                    "status": "succeeded",
                    "execution_id": "exec-123",
                    "data": {"mutation_id": "mutation-456", "secret": "hidden"},
                },
            },
            {
                "tool_name": "digital_market_assess",
                "result": {
                    "ok": False,
                    "status": "awaiting_domain_adapter",
                    "error": "no truthful adapter",
                },
            },
        ],
        locale="zh-Hans",
    )

    assert "不代表目标已完成" in receipt
    assert "generic_data_mutate: succeeded" in receipt
    assert "execution_id=exec-123" in receipt
    assert "digital_market_assess: awaiting_domain_adapter" in receipt
    assert "hidden" not in receipt


def test_authorization_keychain_is_replanned_before_runtime_consumes_it(
    monkeypatch,
) -> None:
    actor = _actor()
    layers = {
        "L0_permanent_world_map": {
            "capability_atlas": ai_capability_atlas(),
            "capability_gene_count": 494,
            "resource_count": 0,
            "resource_atlas": [],
        },
        "L1_current_company_and_people": {
            "company_summary": {"slug": actor.tenant_slug},
            "current_interaction": {},
        },
        "L2_current_goal": {},
        "L3_execution_working_set": {
            "expanded_domains": [],
            "expanded_families": [],
            "domain_capability_index": [],
        },
    }
    signal = {
        "signal": "authorization_granted",
        "business_operation_executed": False,
        "executable": True,
        "goal": "把 mk4-workspace 從 static 升級為 web",
        "action_id": 8,
        "authorization_keychain_id": "00000000-0000-4000-8000-000000000008",
        "tool_name": "digital_market_runtime_upgrade",
        "command": "dm runtime upgrade",
        "expires_at": "2026-08-01T13:20:00+00:00",
        "scope": {"execution_identity": "company_ai", "uses": 1},
        "action_context": {
            "schema": "warehouse.resource-action-context.v1",
            "action_key": "digital_asset.workspace.runtime_upgrade",
            "resource_type": "digital_asset.workspace",
            "resource_ref": "mk4-workspace",
            "suggested_tool_names": ["digital_market_runtime_upgrade"],
        },
        "action": {
            "presentation": {
                "title": "授權 AI 執行 · dm runtime upgrade",
                "fields": [
                    {"key": "workspace", "value": "mk4-workspace"},
                    {"key": "type", "value": "web"},
                ],
            }
        },
    }
    planned_world: dict[str, object] = {}
    consumed: dict[str, object] = {}
    activities: list[dict[str, object]] = []

    monkeypatch.setattr(auto_runtime, "build_router_context", lambda *_a, **_k: layers)
    monkeypatch.setattr(auto_runtime, "_start_run", lambda *_a, **_k: None)
    monkeypatch.setattr(auto_runtime, "_finish_run", lambda *_a, **_k: None)
    monkeypatch.setattr(
        auto_runtime,
        "connected_deepseek",
        lambda *_a, **_k: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="runtime-test",
        ),
    )
    monkeypatch.setattr(
        auto_runtime,
        "_route_goal",
        lambda *_a, **_k: (
            {
                "interaction_mode": "conversation",
                "understood_goal": signal["goal"],
                "message": "",
                "needs_tools": False,
                "requires_user_input": False,
                "selected_tool_names": [],
                "selected_domains": [],
                "selected_families": [],
                "context_requests": [],
                "success_criteria": [],
                "uncertainties": [],
                "memory_depth": "index",
            },
            "{}",
        ),
    )
    monkeypatch.setattr(auto_runtime, "expand_capability_domains", lambda *_a, **_k: [])

    def fake_expand(_layers, selected):
        gene = {
            "tool_name": "digital_market_runtime_upgrade",
            "domain": "asset",
            "command": "dm runtime upgrade",
        }
        _layers["L3_execution_working_set"]["selected_capability_genes"] = [gene]
        assert selected == ["digital_market_runtime_upgrade"]
        return [gene]

    monkeypatch.setattr(auto_runtime, "expand_selected_capabilities", fake_expand)
    monkeypatch.setattr(auto_runtime, "hydrate_company_authority", lambda *_a, **_k: None)
    monkeypatch.setattr(auto_runtime, "responsibility_for_genes", lambda *_a, **_k: {})

    def fake_plan(_connection, goal, plan_layers, *_args, **_kwargs):
        planned_world.update(plan_layers["L3_execution_working_set"])
        assert (
            plan_layers["L2_current_goal"]["action_context"]["resource_ref"]
            == "mk4-workspace"
        )
        return (
            {
                "message": "準備接手已授權操作。",
                "plan": ["重新觀察", "主觀判斷", "執行並核對"],
                "decisions": [
                    {
                        "tool_name": "digital_market_runtime_upgrade",
                        "judgment": "execute",
                        # DeepSeek may place this hand-off marker inside the
                        # argument object despite the planner instruction.
                        # Runtime must consume it before terminal validation.
                        "arguments": {"authorization_action_id": 8},
                        "reasoning": "現況仍需要已授權的 runtime 升級",
                    }
                ],
                "completion_assessment": {"complete": False},
            },
            "{}",
        )

    monkeypatch.setattr(auto_runtime, "_plan_goal", fake_plan)

    def fake_consume(runtime_actor, action_id, **kwargs):
        consumed.update(action_id=action_id, actor=runtime_actor, **kwargs)
        return {
            "ok": True,
            "signal": "runtime_execution_completed",
            "action": {
                "id": 8,
                "status": "completed",
                "credential_deliveries": [
                    {
                        "delivery_id": "acd_test",
                        "credential_count": 1,
                        "status": "pending",
                    }
                ],
            },
        }

    monkeypatch.setattr(
        auto_runtime,
        "execute_authorized_confirmation_action",
        fake_consume,
    )
    reflection_rounds: list[int] = []

    def fake_reflect(*_args, **kwargs):
        round_number = int(kwargs["round_number"])
        reflection_rounds.append(round_number)
        evidence_refs = (
            [] if len(reflection_rounds) == 1 else ["tool:1:1:digital_market_runtime_upgrade"]
        )
        return {
            "message": "已由 AI Runtime 完成並核對。",
            "goal_complete": True,
            "evidence": ["authorization consumed after AI decision"],
            "claims": [
                {
                    "statement": "runtime 升級已完成",
                    "requires_evidence": True,
                    "evidence_refs": evidence_refs,
                }
            ],
            "contradictions": [],
            "revised_plan": [],
            "continue_reason": "goal complete",
            "continue_autonomously": False,
            "requires_user_input": False,
            "next_domains": [],
            "next_families": [],
            "next_decisions": [],
            "memory_candidate": None,
        }

    monkeypatch.setattr(auto_runtime, "_reflect", fake_reflect)

    result = auto_runtime.run_auto_runtime(
        actor,
        SimpleNamespace(),
        str(signal["goal"]),
        conversation_id="00000000-0000-4000-8000-000000000009",
        authorization_signal=signal,
        response_locale="zh-Hant",
        activity_callback=activities.append,
    )

    assert planned_world["authorization_signal"]["business_operation_executed"] is False
    assert consumed["action_id"] == 8
    assert consumed["authorization_keychain_id"] == signal["authorization_keychain_id"]
    assert result.tool_results[0]["result"]["action"]["status"] == "completed"
    assert result.confirmation_actions == ()
    assert reflection_rounds == [1, 2]
    assert result.reflection["goal_complete"] is True
    assert result.reflection["reasoning_rounds"][1]["reasoning_only"] is True
    delivery_activities = [
        item for item in activities if item.get("phase") == "secure_credential_delivery"
    ]
    assert [item["status"] for item in delivery_activities] == [
        "running",
        "succeeded",
    ]
    assert delivery_activities[-1]["elapsed_ms"] >= 0


def test_top_router_receives_compact_recent_turn_referents(monkeypatch) -> None:
    captured: dict[str, object] = {}
    layers = {
        "L0_permanent_world_map": {
            "capability_atlas": [],
            "capability_gene_count": 0,
            "resource_atlas": [],
            "expansion_protocol": {"company_context": []},
        },
        "L1_current_company_and_people": {
            "company_summary": {"company": {"slug": "example"}},
            "current_interaction": {"surface": "assistant"},
        },
        "L2_current_goal": {
            "recent_turn_referents": {
                "messages": [
                    {"role": "assistant", "content": "工作區是 mk4-workspace"},
                    {"role": "user", "content": "上面的網址"},
                ]
            }
        },
        "L3_execution_working_set": {},
    }

    def fake_completion(_connection, **kwargs):
        captured.update(kwargs)
        return json.dumps(
            {
                "interaction_mode": "operational",
                "understood_goal": "查詢 mk4-workspace 的網址",
                "message": "",
                "needs_tools": True,
                "requires_user_input": False,
                "selected_domains": [],
                "selected_families": [],
                "context_requests": [],
                "success_criteria": [],
                "uncertainties": [],
                "reasoning": "resolved from recent referents",
                "memory_depth": "index",
            }
        )

    monkeypatch.setattr(auto_runtime, "_completion", fake_completion)
    route, _raw = auto_runtime._route_goal(
        SimpleNamespace(),
        "上面的網址",
        layers,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    router_payload = json.loads(str(captured["user_prompt"]))
    assert (
        router_payload["router_world"]["recent_turn_referents"]["messages"][0]["content"]
        == "工作區是 mk4-workspace"
    )
    assert "do not ask the human to repeat" in str(captured["system_prompt"])
    assert route["requires_user_input"] is False


def test_pages_action_context_is_bounded_and_advises_the_top_router(monkeypatch) -> None:
    captured: dict[str, object] = {}
    action_context = auto_runtime._bounded_pages_action_context(
        {
            "schema": "warehouse.pages-action-context.v1",
            "action_key": "pages.site.configure",
            "workspace_ref": "mk7-workspace",
            "suggested_tool_names": [
                "digital_market_pages_status",
                "not_a_registered_capability",
                "digital_market_pages_configure",
            ],
        }
    )
    assert action_context is not None
    assert action_context["suggested_tool_names"] == [
        "digital_market_pages_status",
        "digital_market_pages_configure",
    ]

    def fake_completion(_connection, **kwargs):
        captured.update(kwargs)
        return json.dumps(
            {
                "interaction_mode": "operational",
                "understood_goal": "配置 mk7-workspace Pages 网址",
                "message": "请提供短名称。",
                "needs_tools": False,
                "requires_user_input": True,
                "selected_domains": [],
                "selected_families": [],
                "context_requests": [],
                "success_criteria": [],
                "uncertainties": ["短名称尚未提供"],
                "reasoning": "AI judged one human input is missing",
                "memory_depth": "index",
            },
            ensure_ascii=False,
        )

    monkeypatch.setattr(auto_runtime, "_completion", fake_completion)
    route, _raw = auto_runtime._route_goal(
        SimpleNamespace(),
        "帮我设置这个 Pages 网址",
        {
            "L0_permanent_world_map": {
                "capability_atlas": [],
                "resource_atlas": [],
                "expansion_protocol": {},
            },
            "L1_current_company_and_people": {},
            "L2_current_goal": {"action_context": action_context},
            "L3_execution_working_set": {},
        },
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    router_world = json.loads(str(captured["user_prompt"]))["router_world"]
    candidate_names = [item["tool_name"] for item in router_world["catalogue_candidates"]]
    assert candidate_names[:2] == [
        "digital_market_pages_status",
        "digital_market_pages_configure",
    ]
    configure_contract = next(
        item
        for item in router_world["catalogue_candidate_contracts"]
        if item["tool_name"] == "digital_market_pages_configure"
    )
    assert configure_contract["parameters"]["required"] == ["workspace", "site-key"]
    assert router_world["action_context"]["workspace_ref"] == "mk7-workspace"
    assert "never selects a capability" in str(captured["system_prompt"])
    assert route["requires_user_input"] is True


def test_agent_action_context_schema_rejects_unbounded_presentation_input() -> None:
    payload = AgentRunRequest(
        text="配置 Pages",
        action_context={
            "schema": "warehouse.pages-action-context.v1",
            "action_key": "pages.site.configure",
            "workspace_ref": "mk7-workspace",
            "suggested_tool_names": ["digital_market_pages_status"],
        },
    )
    assert payload.action_context is not None
    assert payload.action_context.model_dump(by_alias=True)["schema"] == (
        "warehouse.pages-action-context.v1"
    )

    with pytest.raises(ValidationError):
        AgentRunRequest(
            text="配置 Pages",
            action_context={
                "schema": "warehouse.pages-action-context.v1",
                "action_key": "database.destroy",
                "workspace_ref": "mk7-workspace",
                "suggested_tool_names": [],
            },
        )

    with pytest.raises(ValidationError):
        AgentRunRequest(
            text="配置 Pages",
            action_context={
                "schema": "warehouse.pages-action-context.v1",
                "action_key": "pages.site.configure",
                "workspace_ref": "mk7-workspace",
                "suggested_tool_names": [f"tool_{index}" for index in range(9)],
            },
        )


def test_resource_action_context_preserves_identity_without_selecting_a_tool() -> None:
    payload = AgentRunRequest(
        text="审批这个注册申请",
        action_context={
            "schema": "warehouse.resource-action-context.v1",
            "action_key": "iam.membership_request.approve",
            "resource_type": "iam.membership_request",
            "resource_ref": "7d9ad337-f8dc-432a-9dc7-fca065e0baf6",
            "suggested_tool_names": [
                "registrations_pending",
                "registration_approve",
                "user_add",
                "not_registered",
            ],
        },
    )

    bounded = auto_runtime._bounded_action_context(
        payload.action_context.model_dump(exclude_none=True, by_alias=True)
    )

    assert bounded is not None
    assert bounded["resource_type"] == "iam.membership_request"
    assert bounded["resource_ref"] == "7d9ad337-f8dc-432a-9dc7-fca065e0baf6"
    assert bounded["suggested_tool_names"] == [
        "registrations_pending",
        "registration_approve",
        "user_add",
    ]
    assert "tool selection" in str(bounded["trust_boundary"])

    with pytest.raises(ValidationError):
        AgentRunRequest(
            text="审批",
            action_context={
                "schema": "warehouse.resource-action-context.v1",
                "action_key": "iam.membership_request.approve",
                "resource_type": "iam.membership_request",
                "suggested_tool_names": [],
            },
        )


def test_runtime_atlas_is_dynamically_distilled_from_all_capability_genes() -> None:
    atlas = ai_capability_atlas()
    genes = ai_capability_gene_index()

    assert len(genes) == 537
    assert sum(int(domain["gene_count"]) for domain in atlas) == 537
    assert {gene["scope"] for gene in genes} == {"tenant", "platform"}
    assert all("permission_any" in gene and "availability" in gene for gene in genes)
    observe_gene = next(gene for gene in genes if gene["tool_name"] == "generic_data_observe")
    assert observe_gene["semantic_contract"] == {
        "effect": "observe_related_world",
        "resource": "any_registered_resource",
        "target_identity": "preserve",
        "workflow_prescribed": False,
    }
    assert all("command_families" in domain for domain in atlas)
    assert any(
        domain["domain"] == "org"
        and domain["scope"] == "tenant"
        and "wf" in domain["command_families"]
        for domain in atlas
    )


def test_router_discovery_prefers_graph_observation_for_workspace_console() -> None:
    candidates = ai_capability_candidates(
        "打開數字資產 mk4 的托管工作區 mk4-workspace 匯報站點 數據庫 API Key 狀態"
    )

    assert candidates[0]["tool_name"] == "generic_data_observe"
    assert candidates[0]["writes"] is False


def test_router_discovery_finds_the_research_key_capability() -> None:
    candidates = ai_capability_candidates("可以給我一下科研 API KEY 嗎")

    assert candidates[0] == {
        "tool_name": "research_api_key_issue",
        "command": "research key issue",
        "domain": "research",
        "description": (
            "為本人簽發綁定當前公司、僅可存取科研 API 的密鑰；"
            "明文以一次性安全卡交付，不寫入聊天記錄"
        ),
        "writes": True,
        "confirmation_required": False,
        "availability": "active",
        "execution_kind": "native_adapter",
    }


def test_router_discovery_uses_query_salience_for_a_requested_deliverable() -> None:
    candidates = ai_capability_candidates("部署指南 我需要下载", limit=5)
    expanded = ai_capability_candidates("部署指南 我需要下载", limit=10)

    assert {
        "digital_market_guide",
        "digital_market_hosting_requirements",
    }.issubset({str(item["tool_name"]) for item in candidates})
    assert "digital_market_hosting_start" in {str(item["tool_name"]) for item in expanded}
    assert {str(item["domain"]) for item in candidates}.issubset({"dam", "system"})
    assert "generic_data_observe" in {str(item["tool_name"]) for item in expanded}


def test_runtime_can_expand_one_dynamic_command_family_without_domain_rules() -> None:
    layers = {
        "L3_execution_working_set": {
            "expanded_domains": [],
            "expanded_families": [],
            "domain_capability_index": [],
        }
    }

    index = expand_capability_domains(
        layers,
        ["org"],
        family_keys=["org:wf"],
    )

    assert index
    assert {item["family"] for item in index} == {"wf"}
    assert {"wf_inbox", "wf_workflows"}.issubset({str(item["tool_name"]) for item in index})


def test_authority_projection_joins_observed_references_without_business_rules() -> None:
    layers = {
        "L1_current_company_and_people": {
            "company_authority_world": {
                "responsibility_index": {
                    "procurement.workflow.approve": {
                        "people": ["Owner"],
                        "positions": ["Manager"],
                    }
                },
                "positions": [{"code": "manager", "name": "Manager"}],
                "departments": [{"code": "procurement", "name": "Procurement"}],
                "people": [
                    {
                        "display_name": "Owner",
                        "identities": [{"position_code": "manager"}],
                    }
                ],
            }
        }
    }
    tool_results = [
        {
            "result": {
                "workflow_key": "procurement_tender_v1",
                "nodes": [
                    {
                        "node_key": "approve",
                        "name": "Approve",
                        "required_permission": "procurement.workflow.approve",
                        "assignment": {
                            "position_code": "manager",
                            "department_code": "procurement",
                        },
                    },
                    {"assignment": {"position_code": "missing_position"}},
                ],
            }
        }
    ]

    projection = auto_runtime._authority_evidence_projection(layers, tool_results)

    assert projection["observed_required_permissions"]["procurement.workflow.approve"][
        "people"
    ] == ["Owner"]
    positions = {item["code"]: item for item in projection["observed_position_references"]}
    assert positions["manager"]["active_holders"] == ["Owner"]
    assert positions["manager"]["workflow_nodes"] == [
        {
            "workflow_key": "procurement_tender_v1",
            "node_key": "approve",
            "name": "Approve",
        }
    ]
    assert positions["missing_position"]["exists"] is False


def test_reference_projection_preserves_keys_from_deep_untruncated_results() -> None:
    projection = auto_runtime._reference_value_projection(
        [
            {
                "result": {
                    "data": {
                        "items": [
                            {
                                "workflow_key": "procurement_tender_v1",
                                "definition": {
                                    "nodes": [
                                        {
                                            "node_key": "approve",
                                            "assignment": {"position_code": "manager"},
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                }
            }
        ]
    )

    assert projection["workflow_key"] == ["procurement_tender_v1"]
    assert projection["node_key"] == ["approve"]
    assert projection["position_code"] == ["manager"]


def test_terminal_world_snapshot_uses_the_runtime_database_contract(monkeypatch) -> None:
    snapshot = {
        "source": "tenant_postgresql",
        "scope": "permission-filtered",
        "company": {"slug": "example", "name": "Example"},
        "inventory": {"available": True, "skus": 12, "low_skus": 2},
        "work": {"inbound_open": 1, "outbound_open": 3},
        "governance": {"available": True, "events_24h": 8},
    }
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(api_router, "runtime_world_snapshot", lambda _actor: snapshot)
    try:
        response = TestClient(app).get("/api/runtime/world")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["source"] == "tenant_postgresql"
    assert response.json()["inventory"]["low_skus"] == 2


def test_terminal_skill_catalogue_is_visible_but_not_an_execution_surface(monkeypatch) -> None:
    catalogue = [
        {
            "skill_id": "inventory_list",
            "name": "inv list",
            "description": "List inventory",
            "category": "inventory",
            "category_label": "Warehouse",
            "writes": False,
            "state": "awaiting_domain_adapter",
            "ready": False,
            "authorized": True,
            "scope": "tenant",
            "invocation": "goal_guided",
        }
    ]
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(api_router, "skill_catalogue", lambda _actor: catalogue)
    monkeypatch.setattr(
        api_router,
        "migration_summary",
        lambda _actor: {"revision": "legacy-test"},
    )
    try:
        response = TestClient(app).get("/api/runtime/skills")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["skills"][0]["invocation"] == "goal_guided"
    assert "api_path" not in payload["skills"][0]


def test_runtime_world_snapshot_filters_tenant_database_facts_by_permission(monkeypatch) -> None:
    monkeypatch.setattr(
        auto_runtime,
        "bootstrap_warehouse_payload",
        lambda _actor: {
            "WAREHOUSE_HUB": {
                "access": {
                    "inventory": True,
                    "inbound": False,
                    "outbound": False,
                    "shipments": True,
                },
                "inventory": {"skus": 12, "low_skus": 2, "zero_skus": 1, "stock_value": 45.5},
                "orders": {"inbound_open": 9, "outbound_open": 8},
                "shipments": {"active": 3, "delayed": 1},
                "attention": [{"name": "Critical item", "stock": 1, "safe": 8}],
                "anomalies": [{"label": "Low stock", "count": 2}],
            }
        },
    )
    monkeypatch.setattr(
        auto_runtime,
        "executive_overview_payload",
        lambda _actor: {"modules": {"audit": {"status": "ready", "writes": 7, "failed": 1}}},
    )

    snapshot = auto_runtime.runtime_world_snapshot(_actor())

    assert snapshot["source"] == "tenant_postgresql"
    assert snapshot["inventory"]["low_skus"] == 2
    assert snapshot["work"]["inbound_open"] is None
    assert snapshot["work"]["outbound_open"] is None
    assert snapshot["work"]["shipments_delayed"] == 1
    assert snapshot["governance"]["events_24h"] == 7
    assert snapshot["attention"] == [{"name": "Critical item", "stock": 1, "safe": 8}]


def test_all_surfaces_enter_the_same_goal_runtime(monkeypatch) -> None:
    captured: dict[str, object] = {}
    conversation_id = "00000000-0000-0000-0000-000000000007"

    def fake_runtime(
        actor,
        settings,
        goal,
        *,
        surface,
        conversation_id,
        run_id,
        context_mode,
        response_locale,
        activity_callback,
    ):
        captured.update(
            actor=actor,
            settings=settings,
            goal=goal,
            surface=surface,
            conversation_id=conversation_id,
            run_id=run_id,
            context_mode=context_mode,
            response_locale=response_locale,
        )
        activity_callback(
            {
                "activity_id": "tool:1:1:warehouse_list",
                "kind": "capability",
                "phase": "execute",
                "status": "succeeded",
                "tool_name": "warehouse_list",
                "command": "warehouse list",
                "elapsed_ms": 12,
            }
        )
        return RuntimeResult(
            goal=goal,
            message="Goal understood.",
            model="test-model",
            observations={"world": "warehouse_os", "surface": surface},
            plan=("observe", "plan", "reflect"),
            distillation={"reasoning": "private-router-reasoning"},
            decisions=(
                {
                    "tool_name": "warehouse_list",
                    "judgment": "execute",
                    "arguments": {"password": "private-decision-argument"},
                    "reasoning": "private-decision-reasoning",
                },
            ),
            tool_results=(
                {
                    "tool_name": "warehouse_list",
                    "decision_reasoning": "private-tool-reasoning",
                    "result": {
                        "ok": True,
                        "status": "succeeded",
                        "data": {"secret": "private-tool-result"},
                    },
                },
            ),
            reflection={
                "message": "Goal understood.",
                "goal_complete": True,
                "requires_user_input": False,
                "runtime_stop_reason": "goal_complete",
                "autonomous_rounds": 1,
                "reasoning": "private-reflection-reasoning",
            },
            response_locale=response_locale,
            credentials=(
                {
                    "kind": "runtime_api_key",
                    "value": "wsk_example_test-only-secret",
                    "label": "Research API",
                    "scopes": ["research"],
                },
            ),
            downloads=(
                {
                    "label": "下載指南",
                    "url": "/api/digital-assets/guide/download",
                    "filename": "guide.md",
                },
            ),
        )

    monkeypatch.setattr(api_router, "run_auto_runtime", fake_runtime)
    monkeypatch.setattr(
        api_router,
        "ensure_conversation",
        lambda *_args, **_kwargs: {"id": conversation_id},
    )
    monkeypatch.setattr(
        api_router,
        "messages_for_turn",
        lambda *_args, **_kwargs: [],
    )
    monkeypatch.setattr(
        api_router,
        "append_message",
        lambda *_args, **kwargs: (
            {
                "id": str(UUID(int=8 if kwargs["role"] == "user" else 9)),
                "content": str(kwargs["content"]),
                "metadata": dict(kwargs.get("metadata") or {}),
            },
            True,
        ),
    )
    app.dependency_overrides[current_actor] = _actor
    try:
        response = TestClient(app).post(
            "/api/agent/run/stream",
            json={
                "text": "!warehouse list",
                "conversation_id": conversation_id,
                "surface": "super_terminal",
                "context_mode": "thinking",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["goal"] == "!warehouse list"
    assert captured["surface"] == "super_terminal"
    assert captured["conversation_id"] == conversation_id
    assert captured["context_mode"] == "thinking"
    assert captured["response_locale"] == "en"
    events = _events(response)
    assert [event["event"] for event in events] == [
        "run_start",
        "runtime_activity",
        "runtime_state",
        "runtime_state",
        "runtime_state",
        "final",
    ]
    assert events[1]["tool_name"] == "warehouse_list"
    assert events[1]["status"] == "succeeded"
    assert [event.get("phase") for event in events[2:5]] == ["observe", "plan", "reflect"]
    assert "distillation" not in events[3]
    assert "decisions" not in events[3]
    assert events[3]["capabilities"] == [{"tool_name": "warehouse_list", "judgment": "execute"}]
    assert "tool_results" not in events[4]
    assert "reflection" not in events[4]
    assert events[4]["capability_results"] == [
        {"tool_name": "warehouse_list", "status": "succeeded"}
    ]
    for private_value in (
        "private-router-reasoning",
        "private-decision-argument",
        "private-decision-reasoning",
        "private-tool-reasoning",
        "private-tool-result",
        "private-reflection-reasoning",
    ):
        assert private_value not in response.text
    assert events[-1]["message"] == "Goal understood."
    assert events[-1]["status"] == "succeeded"
    assert events[-1]["credentials"] == [
        {
            "kind": "runtime_api_key",
            "value": "wsk_example_test-only-secret",
            "label": "Research API",
            "scopes": ["research"],
        }
    ]
    assert events[-1]["downloads"] == [
        {
            "label": "下載指南",
            "url": "/api/digital-assets/guide/download",
            "filename": "guide.md",
        }
    ]
    assert events[-1]["cards"] == [{"card_type": "download", "downloads": events[-1]["downloads"]}]
    assert events[0]["context_mode"] == "thinking"
    assert events[0]["response_locale"] == "en"
    assert events[-1]["response_locale"] == "en"
