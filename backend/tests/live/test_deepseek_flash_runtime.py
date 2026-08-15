"""Live DeepSeek Flash gates for Warehouse AI Runtime design changes.

These tests are intentionally skipped by ordinary offline pytest runs. The
repository-level ``ops/run-ai-runtime-verification`` command loads the local
DeepSeek credential without printing it, requires these tests, and runs them
alongside the complete deterministic backend suite.
"""

from __future__ import annotations

import json
import os

import pytest

from app.main import app as _configured_app  # noqa: F401
from app.services import auto_runtime
from app.services.integrations import ModelConnection, chat_completion
from app.terminal.catalog import ai_capability_gene_index


def _deepseek_flash() -> ModelConnection:
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    required = os.environ.get("WAREHOUSE_REQUIRE_DEEPSEEK_LIVE") == "1"
    if not api_key:
        if required:
            pytest.fail("DeepSeek live verification was required but no API key was loaded")
        pytest.skip("DeepSeek live verification requires ops/run-ai-runtime-verification")
    return ModelConnection(
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        model="deepseek-v4-flash",
        api_key=api_key,
    )


def test_deepseek_flash_supports_runtime_json_contract() -> None:
    response = chat_completion(
        _deepseek_flash(),
        system_prompt=(
            "Return one JSON object only. Use exactly these keys: "
            "runtime, model_contract, ready."
        ),
        user_prompt=(
            'Return {"runtime":"warehouse","model_contract":"flash",'
            '"ready":true} without prose.'
        ),
        thinking=False,
        max_tokens=120,
        json_mode=True,
    )

    assert json.loads(response) == {
        "runtime": "warehouse",
        "model_contract": "flash",
        "ready": True,
    }


def test_deepseek_flash_keeps_registration_and_join_approval_distinct() -> None:
    tool_names = {
        "company_join_request",
        "memberships_pending",
        "membership_approve",
        "membership_reject",
        "registrations_pending",
        "registration_approve",
        "registration_reject",
    }
    domain_index = [
        gene for gene in ai_capability_gene_index() if gene["tool_name"] in tool_names
    ]
    goal = (
        "审批通过 Honey 的注册申请 65640632-3608-41ec-9515-c6aff6bcecc4；"
        "先观察真实注册申请、现有全局身份和岗位预设，再审批。"
    )
    selected, _raw = auto_runtime._select_tools(
        _deepseek_flash(),
        goal,
        {
            "interaction_mode": "operational",
            "understood_goal": goal,
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": ["org", "other"],
            "selected_families": ["other:registrations"],
            "context_requests": ["authority"],
            "success_criteria": ["注册申请被原子审批并完成成员关系回读"],
            "uncertainties": [],
            "memory_depth": "focused",
        },
        domain_index,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    chosen = set(selected["selected_tool_names"])
    assert "registrations_pending" in chosen
    assert "registration_approve" in chosen
    assert "membership_approve" not in chosen
    assert "membership_reject" not in chosen


def test_deepseek_flash_distinguishes_organization_mutation_effects() -> None:
    tool_names = {
        "organization_template_apply",
        "organization_department_create",
        "organization_department_update",
        "organization_department_archive",
        "organization_department_permissions",
        "organization_department_navigation",
        "organization_position_create",
        "organization_position_update",
        "organization_position_archive",
        "organization_position_navigation",
        "organization_user_assign",
        "user_permission_overrides_set",
        "user_navigation_overrides_set",
    }
    domain_index = [
        gene for gene in ai_capability_gene_index() if gene["tool_name"] in tool_names
    ]
    goal = (
        "请选择完成以下四项独立操作的精确能力："
        "一、建立新部门；二、修改现有部门 3；"
        "三、封存空岗位 9；四、为用户 12 设置业务权限 allow/deny。"
        "不要设置导航，不要套用组织模板，也不要分配人员岗位。"
    )
    selected, _raw = auto_runtime._select_tools(
        _deepseek_flash(),
        goal,
        {
            "interaction_mode": "operational",
            "understood_goal": goal,
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": ["org"],
            "selected_families": ["org:org", "org:user"],
            "context_requests": ["authority", "operational_world"],
            "success_criteria": ["四项操作分别使用精确且互不混淆的能力"],
            "uncertainties": [],
            "memory_depth": "focused",
        },
        domain_index,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    chosen = set(selected["selected_tool_names"])
    assert {
        "organization_department_create",
        "organization_department_update",
        "organization_position_archive",
        "user_permission_overrides_set",
    }.issubset(chosen)
    assert chosen.isdisjoint(
        {
            "organization_template_apply",
            "organization_department_archive",
            "organization_department_navigation",
            "organization_position_create",
            "organization_position_navigation",
            "organization_user_assign",
            "user_navigation_overrides_set",
        }
    )


def test_deepseek_flash_distinguishes_manuscript_refinement_effects() -> None:
    tool_names = {
        "research_file_preview",
        "research_document_review",
        "research_manuscript_refinement",
        "research_manuscript_semantic_show",
        "research_manuscript_semantic_refresh",
        "research_manuscript_agent_chat",
        "research_manuscript_annotate",
        "research_manuscript_finding_accept",
        "research_manuscript_finding_reject",
        "research_manuscript_draft_save",
        "research_manuscript_submit",
        "research_document_annotate",
    }
    domain_index = [
        gene for gene in ai_capability_gene_index() if gene["tool_name"] in tool_names
    ]
    goal = (
        "对 MK51 的 manuscript/paper.docx 完成四项精确操作："
        "启动或恢复结构化精修草稿；按全文内容哈希排程 logic 评审；"
        "接受指定 finding 并安全写入草稿；最后把已同步 revision 4 "
        "正式提交成新的不可变 DOCX 版本。"
        "不要只查看语义，不要普通保存草稿，不要拒绝 finding，也不要新增批注。"
    )
    selected, _raw = auto_runtime._select_tools(
        _deepseek_flash(),
        goal,
        {
            "interaction_mode": "operational",
            "understood_goal": goal,
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": ["research"],
            "selected_families": ["research:research"],
            "context_requests": ["authority", "operational_world"],
            "success_criteria": ["四项稿件操作分别使用精确且互不混淆的能力"],
            "uncertainties": [],
            "memory_depth": "focused",
        },
        domain_index,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    chosen = set(selected["selected_tool_names"])
    assert {
        "research_manuscript_refinement",
        "research_manuscript_semantic_refresh",
        "research_manuscript_finding_accept",
        "research_manuscript_submit",
    }.issubset(chosen)
    assert chosen.isdisjoint(
        {
            "research_file_preview",
            "research_document_review",
            "research_manuscript_semantic_show",
            "research_manuscript_agent_chat",
            "research_manuscript_annotate",
            "research_manuscript_finding_reject",
            "research_document_annotate",
        }
    )


def test_deepseek_flash_distinguishes_hosting_bundle_and_workspace_effects() -> None:
    tool_names = {
        "digital_market_create",
        "digital_market_workspace_create",
        "digital_market_database_create",
        "digital_market_provision",
        "digital_market_key_issue",
        "digital_market_primary_key_rotate",
        "digital_market_keys_list",
        "digital_market_database_browser_access",
        "digital_market_database_browser_configure",
        "digital_market_console",
        "digital_market_db_query",
        "digital_market_db_exec",
    }
    domain_index = [
        gene for gene in ai_capability_gene_index() if gene["tool_name"] in tool_names
    ]
    goal = (
        "请选择完成以下四项独立操作的精确能力："
        "一、一步托管一个全新软件，同时建立资产、工作区、PostgreSQL Data API "
        "和唯一主 Key；二、配置既有工作区数据库的浏览器 Origins 与默认拒绝规则；"
        "三、轮换既有工作区的唯一主 Key；四、只读分页查询 customers 集合。"
        "不要拆成建立资产、建立工作区、建立数据库或签发附属 Key，"
        "不要只查看浏览器配置，也不要写入集合。"
    )
    selected, _raw = auto_runtime._select_tools(
        _deepseek_flash(),
        goal,
        {
            "interaction_mode": "operational",
            "understood_goal": goal,
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": ["dam"],
            "selected_families": ["dam:dm"],
            "context_requests": ["authority", "operational_world"],
            "success_criteria": ["四项操作分别使用精确且互不重复的能力"],
            "uncertainties": [],
            "memory_depth": "focused",
        },
        domain_index,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    chosen = set(selected["selected_tool_names"])
    assert {
        "digital_market_provision",
        "digital_market_database_browser_configure",
        "digital_market_primary_key_rotate",
        "digital_market_db_query",
    }.issubset(chosen)
    assert chosen.isdisjoint(
        {
            "digital_market_create",
            "digital_market_workspace_create",
            "digital_market_database_create",
            "digital_market_key_issue",
            "digital_market_keys_list",
            "digital_market_database_browser_access",
            "digital_market_console",
            "digital_market_db_exec",
        }
    )


def test_deepseek_flash_distinguishes_tenant_wsk_from_workspace_wak() -> None:
    tool_names = {
        "secretary_cli_key_issue",
        "secretary_cli_keys_list",
        "secretary_cli_key_revoke",
        "digital_market_provision",
        "digital_market_key_issue",
        "digital_market_primary_key_rotate",
        "digital_market_key_revoke",
        "digital_market_keys_list",
    }
    domain_index = [
        gene for gene in ai_capability_gene_index() if gene["tool_name"] in tool_names
    ]
    goal = (
        "請簽發一把 wsk_ Warehouse AI 秘書／CLI Runtime Key，"
        "綁定目前登入帳號與目前公司，scopes 是 assistant,terminal，有效 30 天。"
        "這不是 wak_ 數字資產工作區 Key，不需要 workspace 或 warehouse UUID。"
    )
    selected, _raw = auto_runtime._select_tools(
        _deepseek_flash(),
        goal,
        {
            "interaction_mode": "operational",
            "understood_goal": goal,
            "needs_tools": True,
            "requires_user_input": False,
            "selected_domains": ["ai", "dam"],
            "selected_families": ["ai:ai", "dam:dm"],
            "context_requests": ["authority"],
            "success_criteria": ["簽發目前使用者與公司的 wsk_ 並一次性安全交付"],
            "uncertainties": [],
            "memory_depth": "focused",
        },
        domain_index,
        [],
        context_mode="balanced",
        activity_callback=None,
    )

    chosen = set(selected["selected_tool_names"])
    assert chosen == {"secretary_cli_key_issue"}
