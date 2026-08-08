from app.api import full_stack_identity
from app.templates.industry_blueprints import (
    INDUSTRY_BLUEPRINT_KEYS,
    assert_valid_blueprints,
    blueprint_permission_ceilings,
    get_blueprint,
    list_blueprints,
)
from app.templates.workflow_blueprints import (
    NON_OPERATIONAL_TEMPLATE_KEYS,
    validate_workflow_blueprints,
    workflow_blueprints_for_industry,
)
from app.terminal.legacy_catalog import entry_by_tool_name


def test_all_built_in_blueprints_are_available() -> None:
    assert_valid_blueprints()

    templates = list_blueprints()
    assert len(templates) == 14
    assert tuple(template["key"] for template in templates) == INDUSTRY_BLUEPRINT_KEYS


def test_civilization_is_a_creator_isolated_direct_registration_preset() -> None:
    template = get_blueprint("civilization")
    positions = {item["code"]: item for item in template["positions"]}
    member = positions["civilization_member"]

    assert template["enabled_modules"] == ["civilization", "perms", "settings"]
    assert template["registration_policy"] == {
        "mode": "direct",
        "approval_required": False,
        "default_position_code": "civilization_member",
        "requested_position_policy": "ignore",
        "audit_event": "civilization.registration.completed",
    }
    assert template["data_policy"]["draft_visibility"] == "creator_only"
    assert set(member["permissions"]) == {"civilization.read", "civilization.write"}
    assert member["public_entry"]["quick_registration"] is True
    assert positions["civilization_system_admin"]["database_access_mode"] == "tenant_scoped"


def test_direct_registration_is_resolved_from_the_reviewed_template_contract(monkeypatch) -> None:
    blueprint = get_blueprint("civilization")
    monkeypatch.setattr(
        full_stack_identity,
        "get_template_detail",
        lambda _key: {"blueprint": blueprint},
    )

    policy = full_stack_identity._self_service_registration_policy(
        {"industry_template_key": "civilization"}
    )

    assert policy is not None
    assert policy["default_position_code"] == "civilization_member"

    compromised = get_blueprint("civilization")
    member = next(
        item for item in compromised["positions"] if item["code"] == "civilization_member"
    )
    member["permissions"].append("settings.manage")
    monkeypatch.setattr(
        full_stack_identity,
        "get_template_detail",
        lambda _key: {"blueprint": compromised},
    )
    assert (
        full_stack_identity._self_service_registration_policy(
            {"industry_template_key": "civilization"}
        )
        is None
    )


def test_power_grid_blueprint_is_renamed_to_power_system() -> None:
    assert "power_grid_uhv" not in INDUSTRY_BLUEPRINT_KEYS
    template = get_blueprint("power_system")

    assert template["name"] == "電力系統"
    assert template["admin_position_code"] == "grid_system_admin"
    assert len(template["departments"]) == 10
    assert len(template["positions"]) == 20


def test_research_lab_has_separate_management_research_scientific_and_laboratory_centres() -> None:
    template = get_blueprint("research_lab")
    departments = {item["code"]: item for item in template["departments"]}
    positions = {item["code"]: item for item in template["positions"]}

    assert departments["management"]["name"] == "管理層"
    assert departments["research"]["name"] == "研究中心"
    assert departments["lab_research_technology"]["name"] == "科研中心"
    assert departments["lab_operations"]["name"] == "實驗室"

    management_positions = {
        item["name"] for item in positions.values() if item["department"] == "management"
    }
    assert management_positions == {"總經理", "副總經理", "系統管理員"}

    assert positions["lab_director"]["department"] == "lab_operations"
    assert positions["lab_deputy_director"]["department"] == "lab_operations"
    assert positions["research_center_director"]["department"] == "research"
    assert positions["research_center_deputy_director"]["department"] == "research"
    assert positions["principal_investigator"]["department"] == "research"
    assert (
        positions["scientific_research_center_director"]["department"] == "lab_research_technology"
    )
    assert (
        positions["scientific_research_center_deputy_director"]["department"]
        == "lab_research_technology"
    )
    assert positions["research_technology_manager"]["department"] == "lab_research_technology"
    assert {"research.read", "research.write", "research.review"}.issubset(
        positions["principal_investigator"]["permissions"]
    )
    assert {"research.read", "research.write"}.issubset(
        positions["researcher"]["permissions"]
    )
    assert {"research.read", "research.write", "research.review"}.issubset(
        positions["lab_system_admin"]["permissions"]
    )
    assert {"research.read", "research.review"}.issubset(
        positions["lab_general_manager"]["permissions"]
    )
    assert "research.write" not in positions["lab_general_manager"]["permissions"]


def test_every_industry_department_ceiling_is_derived_from_its_positions() -> None:
    for template_key in INDUSTRY_BLUEPRINT_KEYS:
        template = get_blueprint(template_key)
        ceilings = blueprint_permission_ceilings(template)
        department_codes = {item["code"] for item in template["departments"]}

        assert set(ceilings) == department_codes
        for position in template["positions"]:
            assert set(position["permissions"]).issubset(ceilings[position["department"]])


def test_operational_industries_have_editable_procurement_workflow_presets() -> None:
    assert validate_workflow_blueprints() == []

    for template_key in INDUSTRY_BLUEPRINT_KEYS:
        definitions = workflow_blueprints_for_industry(template_key)
        if template_key in NON_OPERATIONAL_TEMPLATE_KEYS:
            assert definitions == []
            continue

        assert {item["workflow_key"] for item in definitions} == {
            "internal_purchase_v1",
            "procurement_tender_v1",
            "procurement_tender_v2",
        }
        assert {item["workflow_key"]: len(item["nodes"]) for item in definitions} == {
            "internal_purchase_v1": 3,
            "procurement_tender_v1": 27,
            "procurement_tender_v2": 10,
        }
        for definition in definitions:
            assert definition["governance"]["tenant_editable"] is True
            assert definition["governance"]["assignment_resolution"] == "live_multi_identity"
            assert definition["command_binding_schema_version"] == 1
            for node in definition["nodes"]:
                assert node["assignment"]["identity_mode"] == ("all_active_user_identities")
                assert node["command_binding_schema_version"] == 1
                assert node["actions"]
                for action in node["actions"]:
                    assert entry_by_tool_name(action["tool_name"]) is not None
                    assert isinstance(action["arguments"], dict)
                    assert isinstance(action["bindings"], dict)


def test_procurement_node_commands_prefill_shared_business_action_contracts() -> None:
    definitions = {
        item["workflow_key"]: item
        for item in workflow_blueprints_for_industry("research_lab")
    }

    internal_nodes = {
        item["node_key"]: item
        for item in definitions["internal_purchase_v1"]["nodes"]
    }
    assert [
        action["tool_name"] for action in internal_nodes["submit"]["actions"]
    ] == [
        "erp_purchase_create",
        "erp_purchase_status",
        "wf_start",
        "wf_task_action",
    ]
    assert internal_nodes["manager_approve"]["actions"][0]["arguments"] == {
        "action": "approve"
    }

    tender_nodes = {
        item["node_key"]: item
        for item in definitions["procurement_tender_v1"]["nodes"]
    }
    assert tender_nodes["n07"]["actions"][0]["tool_name"] == "tender_create"
    assert tender_nodes["n11"]["actions"][0]["tool_name"] == "tender_publish"
    assert tender_nodes["n13"]["actions"][0]["tool_name"] == "tender_open"
    assert tender_nodes["n14"]["actions"][0]["tool_name"] == "tender_evaluate"
    assert tender_nodes["n15"]["actions"][0]["tool_name"] == "tender_award"
    assert tender_nodes["n19"]["actions"][0]["tool_name"] == "legal_contract_save"
    assert tender_nodes["n23"]["actions"][0]["tool_name"] == "legal_contract_review"
