"""Editable procurement workflow presets for operational industry templates.

These values are seed data, not runtime branches.  Once provisioned,
``workflow.definitions`` is authoritative and administrators may publish a new
version without changing Python code.  Assignments point to stable
responsibility slots and live position codes, never to a person's identity.
The task router can therefore resolve all of a user's active identities at the
time a task is observed or acted on.
"""

from __future__ import annotations

from copy import deepcopy

from app.templates.industry_blueprints import get_blueprint

WORKFLOW_BLUEPRINT_SCHEMA_VERSION = 1
WORKFLOW_BLUEPRINT_REVISION = "2026.07.30.2"
WORKFLOW_COMMAND_BINDING_SCHEMA_VERSION = 1
NON_OPERATIONAL_TEMPLATE_KEYS = frozenset({"biu_legal_ethics_case_lab", "civilization"})

_RESPONSIBILITY_POSITIONS: dict[str, dict[str, str]] = {
    "generic_warehouse": {
        "executive": "general_manager",
        "deputy_executive": "deputy_general_manager",
        "procurement_manager": "procurement_manager",
        "procurement_operator": "buyer",
        "materials_manager": "warehouse_manager",
        "finance_manager": "finance_manager",
        "legal_manager": "finance_manager",
    },
    "power_system": {
        "executive": "grid_general_manager",
        "deputy_executive": "grid_deputy_general_manager",
        "procurement_manager": "grid_supply_manager",
        "procurement_operator": "grid_buyer",
        "materials_manager": "grid_supply_manager",
        "finance_manager": "grid_finance_manager",
        "legal_manager": "legal_manager",
    },
    "manufacturing_factory": {
        "executive": "factory_general_manager",
        "deputy_executive": "factory_deputy_director",
        "procurement_manager": "factory_supply_manager",
        "procurement_operator": "factory_buyer",
        "materials_manager": "factory_supply_manager",
        "finance_manager": "factory_finance_manager",
        "legal_manager": "factory_finance_manager",
    },
    "construction_site": {
        "executive": "construction_general_manager",
        "deputy_executive": "construction_deputy_general_manager",
        "procurement_manager": "contracts_manager",
        "procurement_operator": "construction_buyer",
        "materials_manager": "materials_manager",
        "finance_manager": "construction_finance_manager",
        "legal_manager": "contracts_manager",
    },
    "restaurant_kitchen": {
        "executive": "restaurant_general_manager",
        "deputy_executive": "restaurant_deputy_manager",
        "procurement_manager": "restaurant_supply_manager",
        "procurement_operator": "restaurant_buyer",
        "materials_manager": "restaurant_supply_manager",
        "finance_manager": "restaurant_finance_manager",
        "legal_manager": "restaurant_finance_manager",
    },
    "medical_clinic": {
        "executive": "clinic_director",
        "deputy_executive": "clinic_deputy_director",
        "procurement_manager": "pharmacy_manager",
        "procurement_operator": "pharmacy_storekeeper",
        "materials_manager": "pharmacy_manager",
        "finance_manager": "clinic_finance_manager",
        "legal_manager": "clinic_admin_manager",
    },
    "retail_store": {
        "executive": "retail_general_manager",
        "deputy_executive": "retail_deputy_manager",
        "procurement_manager": "merchandising_manager",
        "procurement_operator": "merchandiser",
        "materials_manager": "replenishment_manager",
        "finance_manager": "retail_finance_manager",
        "legal_manager": "retail_finance_manager",
    },
    "logistics_express": {
        "executive": "logistics_general_manager",
        "deputy_executive": "logistics_deputy_general_manager",
        "procurement_manager": "sorting_manager",
        "procurement_operator": "sorting_storekeeper",
        "materials_manager": "sorting_manager",
        "finance_manager": "logistics_finance_manager",
        "legal_manager": "logistics_finance_manager",
    },
    "research_lab": {
        "executive": "lab_general_manager",
        "deputy_executive": "lab_deputy_general_manager",
        "procurement_manager": "lab_supply_manager",
        "procurement_operator": "lab_buyer",
        "materials_manager": "lab_supply_manager",
        "finance_manager": "lab_finance_manager",
        "legal_manager": "lab_safety_manager",
    },
    "hotel_homestay": {
        "executive": "hotel_general_manager",
        "deputy_executive": "hotel_deputy_general_manager",
        "procurement_manager": "hotel_supply_manager",
        "procurement_operator": "hotel_buyer",
        "materials_manager": "hotel_supply_manager",
        "finance_manager": "hotel_finance_manager",
        "legal_manager": "hotel_finance_manager",
    },
    "it_office_asset": {
        "executive": "it_general_manager",
        "deputy_executive": "it_deputy_general_manager",
        "procurement_manager": "it_procurement_manager",
        "procurement_operator": "it_buyer",
        "materials_manager": "it_asset_manager",
        "finance_manager": "it_finance_manager",
        "legal_manager": "it_procurement_manager",
    },
    "film_equipment": {
        "executive": "film_general_manager",
        "deputy_executive": "film_deputy_general_manager",
        "procurement_manager": "producer",
        "procurement_operator": "production_coordinator",
        "materials_manager": "props_manager",
        "finance_manager": "film_finance_manager",
        "legal_manager": "film_hr_manager",
    },
}


def _assignment(template_key: str, responsibility: str) -> dict[str, object]:
    if responsibility in {
        "initiator",
        "context_department_manager",
        "external_party",
        "gateway",
    }:
        return {
            "strategy": responsibility,
            "resolve_at_runtime": True,
            "identity_mode": "all_active_user_identities",
        }
    position_code = _RESPONSIBILITY_POSITIONS[template_key][responsibility]
    blueprint = get_blueprint(template_key)
    position = next(item for item in blueprint["positions"] if item["code"] == position_code)
    return {
        "strategy": "responsibility_slot",
        "responsibility": responsibility,
        "department_code": position["department"],
        "position_code": position_code,
        "resolve_at_runtime": True,
        "identity_mode": "all_active_user_identities",
    }


def _command(
    tool_name: str,
    label: str,
    *,
    arguments: dict[str, object] | None = None,
    bindings: dict[str, str | tuple[str, ...]] | None = None,
) -> dict[str, object]:
    """Describe one node action using the shared terminal/tool contract.

    ``arguments`` contains workflow-defined constants. ``bindings`` contains
    ordered context paths resolved by the frontend when a user selects a node.
    Missing context is deliberately left blank for the generated action form;
    neither the browser nor the workflow preset invents business values.
    """

    return {
        "tool_name": tool_name,
        "label": label,
        "arguments": deepcopy(arguments or {}),
        "bindings": {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in (bindings or {}).items()
        },
    }


def _workflow_task_action(action: str, label: str) -> dict[str, object]:
    return _command(
        "wf_task_action",
        label,
        arguments={"action": action},
        bindings={"task": ("task.id", "task.task_id")},
    )


def _workflow_map_action() -> dict[str, object]:
    return _command(
        "wf_map",
        "檢視路由規則",
        bindings={"workflow": "workflow.key"},
    )


def _artifact_action(kind: str, label: str = "登記節點材料") -> dict[str, object]:
    return _command(
        "wf_task_artifact",
        label,
        arguments={"kind": kind},
        bindings={"task": ("task.id", "task.task_id")},
    )


def _purchase_intake_actions(workflow_key: str) -> tuple[dict[str, object], ...]:
    purchase_id = (
        "instance.entity_id",
        "instance.subject_id",
        "item.entity_id",
        "item.subject_id",
    )
    return (
        _command(
            "erp_purchase_create",
            "建立採購申請",
            bindings={
                "title": ("instance.title", "item.title"),
                "budget": ("instance.state.budget_id", "item.state.budget_id"),
                "cost-center": (
                    "instance.state.cost_center_id",
                    "item.state.cost_center_id",
                ),
            },
        ),
        _command(
            "erp_purchase_status",
            "提交採購申請",
            arguments={"status": "submitted", "workflow": workflow_key},
            bindings={"id": purchase_id},
        ),
        _command(
            "wf_start",
            "啟動受控流程",
            arguments={
                "workflow": workflow_key,
                "entity-type": "erp_purchase_request",
            },
            bindings={
                "entity-id": purchase_id,
                "title": ("instance.title", "item.title"),
                "amount": ("instance.state.amount", "instance.amount", "item.amount"),
            },
        ),
        _workflow_task_action("submit", "提交並推進節點"),
    )


def _tender_notice_bindings() -> tuple[str, ...]:
    return (
        "tender.id",
        "instance.state.tender_notice_id",
        "instance.tender_notice_id",
        "item.state.tender_notice_id",
        "item.tender_notice_id",
    )


def _purchase_request_bindings() -> tuple[str, ...]:
    return (
        "instance.entity_id",
        "instance.subject_id",
        "item.entity_id",
        "item.subject_id",
    )


def _tender_create_action() -> dict[str, object]:
    return _command(
        "tender_create",
        "建立招標草稿",
        bindings={
            "pr": _purchase_request_bindings(),
            "title": ("instance.title", "item.title"),
            "ceiling": ("instance.state.amount", "instance.amount", "item.amount"),
        },
    )


def _contract_bindings() -> tuple[str, ...]:
    return (
        "contract.id",
        "instance.state.contract_id",
        "instance.contract_id",
        "item.state.contract_id",
        "item.contract_id",
    )


def _node(
    template_key: str,
    key: str,
    step: int,
    stage: str,
    name: str,
    kind: str,
    responsibility: str,
    *,
    next_key: str | None = None,
    reject_key: str | None = None,
    permission: str | None = None,
    artifacts: tuple[str, ...] = (),
    gateway: dict[str, object] | None = None,
    actions: tuple[dict[str, object], ...] = (),
) -> dict[str, object]:
    node: dict[str, object] = {
        "node_key": key,
        "step_no": step,
        "stage_key": stage,
        "name": name,
        "kind": kind,
        "assignment": _assignment(template_key, responsibility),
        "required_permission": permission,
        "on_approve_next": next_key,
        "on_reject_target": reject_key,
        "artifact_kinds": list(artifacts),
        "command_binding_schema_version": WORKFLOW_COMMAND_BINDING_SCHEMA_VERSION,
        "actions": deepcopy(list(actions)),
        "sla": {"mode": "tenant_policy", "default_hours": 72},
        "quorum": {"mode": "tenant_policy", "default": 1},
    }
    if gateway:
        node["gateway"] = gateway
    return node


def _edges(nodes: list[dict[str, object]]) -> list[dict[str, object]]:
    edges: list[dict[str, object]] = []
    for node in nodes:
        source = str(node["node_key"])
        target = node.get("on_approve_next")
        rejected = node.get("on_reject_target")
        if target:
            edges.append({"source": source, "target": target, "outcome": "approve"})
        if rejected:
            edges.append({"source": source, "target": rejected, "outcome": "reject"})
        gateway = node.get("gateway")
        if not isinstance(gateway, dict):
            continue
        for branch in gateway.get("branches") or []:
            if isinstance(branch, dict) and branch.get("target"):
                edges.append(
                    {
                        "source": source,
                        "target": branch["target"],
                        "outcome": "branch",
                        "condition": branch.get("condition"),
                    }
                )
        for branch_target in gateway.get("targets") or []:
            edges.append({"source": source, "target": branch_target, "outcome": "parallel"})
        if gateway.get("target"):
            edges.append(
                {
                    "source": source,
                    "target": gateway["target"],
                    "outcome": "join",
                }
            )
    return edges


def _definition(
    *,
    workflow_key: str,
    name: str,
    description: str,
    start_node_key: str,
    stages: list[dict[str, object]],
    nodes: list[dict[str, object]],
    parameters: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": WORKFLOW_BLUEPRINT_SCHEMA_VERSION,
        "revision": WORKFLOW_BLUEPRINT_REVISION,
        "command_binding_schema_version": WORKFLOW_COMMAND_BINDING_SCHEMA_VERSION,
        "workflow_key": workflow_key,
        "domain": "procurement",
        "name": name,
        "description": description,
        "start_node_key": start_node_key,
        "parameters": parameters or {},
        "stages": stages,
        "nodes": nodes,
        "edges": _edges(nodes),
        "governance": {
            "tenant_editable": True,
            "publish_creates_new_version": True,
            "assignment_resolution": "live_multi_identity",
            "ai_visibility": "all_company_definitions",
            "ai_execution": "contextual_judgment_with_confirmation_contract",
            "cross_tenant_data_access": False,
        },
        "source": {
            "system": "Warehouse 2.0",
            "migration": "postgresql_data_driven",
        },
    }


def _internal_purchase(template_key: str) -> dict[str, object]:
    stages = [
        {"key": "apply", "name": "申請", "seq": 1},
        {"key": "approve", "name": "審批", "seq": 2},
        {"key": "done", "name": "確認", "seq": 3},
    ]
    nodes = [
        _node(
            template_key,
            "submit",
            1,
            "apply",
            "發起採購申請",
            "form",
            "initiator",
            next_key="manager_approve",
            permission="procurement.workflow.use",
            actions=_purchase_intake_actions("internal_purchase_v1"),
        ),
        _node(
            template_key,
            "manager_approve",
            2,
            "approve",
            "需求部門主管審批",
            "approval",
            "context_department_manager",
            next_key="procure_confirm",
            reject_key="submit",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "審批此節點"),),
        ),
        _node(
            template_key,
            "procure_confirm",
            3,
            "done",
            "採購確認執行",
            "approval",
            "procurement_manager",
            reject_key="submit",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "確認採購執行"),),
        ),
    ]
    return _definition(
        workflow_key="internal_purchase_v1",
        name="內部採購審批",
        description="由真實 ERP 採購申請發起的內部採購審批流程。",
        start_node_key="submit",
        stages=stages,
        nodes=nodes,
    )


def _tender_gateway(template_key: str) -> dict[str, object]:
    stages = [
        {"key": "intake", "name": "立項建單", "seq": 1},
        {"key": "gate", "name": "金額分流", "seq": 2},
        {"key": "approve", "name": "並行審批", "seq": 3},
        {"key": "award", "name": "開評定標", "seq": 4},
        {"key": "contract", "name": "合同生效", "seq": 5},
    ]
    nodes = [
        _node(
            template_key,
            "n01",
            1,
            "intake",
            "立項並創建採購申請",
            "form",
            "initiator",
            next_key="gw_amount",
            permission="procurement.workflow.use",
            actions=_purchase_intake_actions("procurement_tender_v2"),
        ),
        _node(
            template_key,
            "gw_amount",
            2,
            "gate",
            "採購方式分流",
            "gateway_exclusive",
            "gateway",
            gateway={
                "branches": [
                    {
                        "target": "gw_fork",
                        "condition": {
                            "field": "amount",
                            "operator": "gte",
                            "parameter_ref": "tender_amount_threshold",
                        },
                    },
                    {"target": "n_direct", "condition": {"fallback": True}},
                ]
            },
            actions=(_workflow_map_action(),),
        ),
        _node(
            template_key,
            "n_direct",
            3,
            "gate",
            "直接採購確認",
            "approval",
            "procurement_manager",
            next_key="n_contract",
            reject_key="n01",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "確認直接採購"),),
        ),
        _node(
            template_key,
            "gw_fork",
            4,
            "approve",
            "並行審批分叉",
            "gateway_parallel",
            "gateway",
            gateway={"targets": ["a_demand", "a_finance", "a_assets"]},
            actions=(_workflow_map_action(),),
        ),
        _node(
            template_key,
            "a_demand",
            5,
            "approve",
            "需求部門審批",
            "approval",
            "context_department_manager",
            next_key="gw_join",
            reject_key="n01",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "完成需求審批"),),
        ),
        _node(
            template_key,
            "a_finance",
            6,
            "approve",
            "財務審批",
            "approval",
            "finance_manager",
            next_key="gw_join",
            reject_key="n01",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "完成財務審批"),),
        ),
        _node(
            template_key,
            "a_assets",
            7,
            "approve",
            "物資審批",
            "approval",
            "materials_manager",
            next_key="gw_join",
            reject_key="n01",
            permission="procurement.workflow.approve",
            actions=(_workflow_task_action("approve", "完成物資審批"),),
        ),
        _node(
            template_key,
            "gw_join",
            8,
            "approve",
            "並行審批匯聚",
            "gateway_join",
            "gateway",
            gateway={
                "sources": ["a_demand", "a_finance", "a_assets"],
                "target": "n_award",
            },
            actions=(_workflow_map_action(),),
        ),
        _node(
            template_key,
            "n_award",
            9,
            "award",
            "開評標並定標",
            "form",
            "procurement_manager",
            next_key="n_contract",
            permission="procurement.workflow.admin",
            artifacts=("eval_report",),
            actions=(
                _tender_create_action(),
                _command(
                    "tender_open",
                    "開標",
                    bindings={"id": _tender_notice_bindings()},
                ),
                _command(
                    "tender_evaluate",
                    "評標",
                    bindings={"id": _tender_notice_bindings()},
                ),
                _command(
                    "tender_award",
                    "定標",
                    bindings={"id": _tender_notice_bindings()},
                ),
                _artifact_action("eval_report", "登記評標報告"),
                _workflow_task_action("submit", "提交並推進節點"),
            ),
        ),
        _node(
            template_key,
            "n_contract",
            10,
            "contract",
            "合同生效",
            "approval",
            "executive",
            permission="procurement.workflow.approve",
            actions=(
                _command(
                    "legal_contract_save",
                    "建立合同草稿",
                    bindings={
                        "id": _contract_bindings(),
                        "title": ("instance.title", "item.title"),
                        "amount": (
                            "instance.state.amount",
                            "instance.amount",
                            "item.amount",
                        ),
                    },
                ),
                _command(
                    "legal_contract_review",
                    "提交合同審查",
                    bindings={"id": _contract_bindings()},
                ),
                _workflow_task_action("approve", "確認合同生效"),
            ),
        ),
    ]
    return _definition(
        workflow_key="procurement_tender_v2",
        name="招標採購流程（網關版）",
        description="可配置金額參數、並行會審、開評定標與合同生效流程。",
        start_node_key="n01",
        stages=stages,
        nodes=nodes,
        parameters={
            "tender_amount_threshold": {
                "type": "money",
                "default": 500000,
                "currency": "tenant_default",
                "tenant_editable": True,
            }
        },
    )


_TENDER_LONG_NODES = (
    ("n01", "batch", "提供批復文件並創建批次號", "form", "initiator", "n02", None, ("batch_doc",)),
    ("n02", "batch", "創建採購申請並掛批次號", "form", "initiator", "n03", None, ()),
    (
        "n03",
        "approval",
        "需求部門負責人審批",
        "approval",
        "context_department_manager",
        "n04",
        "n02",
        (),
    ),
    ("n04", "approval", "項目／資金管理審批", "approval", "finance_manager", "n05", "n02", ()),
    ("n05", "approval", "財務審批", "approval", "finance_manager", "n06", "n02", ()),
    (
        "n06",
        "approval",
        "物資審批並確認採購策略",
        "approval",
        "materials_manager",
        "n07",
        "n02",
        (),
    ),
    (
        "n07",
        "ecp",
        "採購申請傳輸至 ECP",
        "external_placeholder",
        "procurement_operator",
        "n08",
        None,
        (),
    ),
    (
        "n08",
        "ecp",
        "維護採購項目計劃",
        "external_placeholder",
        "procurement_operator",
        "n09",
        None,
        ("tender_plan",),
    ),
    (
        "n09",
        "ecp",
        "分配代理公司",
        "external_placeholder",
        "procurement_manager",
        "n10",
        None,
        ("agent_assignment",),
    ),
    (
        "n10",
        "ecp",
        "物資審核採購文件",
        "external_placeholder",
        "materials_manager",
        "n11",
        None,
        ("procurement_doc",),
    ),
    (
        "n11",
        "ecp",
        "代理公司掛招標公告",
        "external_placeholder",
        "external_party",
        "n12",
        None,
        ("tender_notice",),
    ),
    ("n12", "ecp", "投標人報名投標", "external_placeholder", "external_party", "n13", None, ()),
    (
        "n13",
        "award",
        "開標",
        "external_placeholder",
        "procurement_manager",
        "n14",
        None,
        ("bid_opening_record",),
    ),
    (
        "n14",
        "award",
        "評標委員會評標",
        "external_placeholder",
        "procurement_manager",
        "n15",
        None,
        ("eval_report",),
    ),
    (
        "n15",
        "award",
        "招標人確認結果",
        "external_placeholder",
        "executive",
        "n16",
        None,
        ("award_result",),
    ),
    ("n16", "award", "代理公司發布結果", "external_placeholder", "external_party", "n17", None, ()),
    (
        "n17",
        "award",
        "招標人簽章",
        "external_placeholder",
        "executive",
        "n18",
        None,
        ("signature_proof",),
    ),
    (
        "n18",
        "contract",
        "採購主管分配合同經辦人",
        "approval",
        "procurement_manager",
        "n19",
        None,
        (),
    ),
    (
        "n19",
        "contract",
        "生成合同草稿",
        "form",
        "procurement_operator",
        "n20",
        None,
        ("contract_draft",),
    ),
    ("n20", "contract", "物資審批合同草稿", "approval", "materials_manager", "n21", "n19", ()),
    (
        "n21",
        "contract",
        "投標人維護賣方信息",
        "external_placeholder",
        "external_party",
        "n22",
        None,
        (),
    ),
    ("n22", "contract", "ERP 生成採購訂單", "system_auto", "procurement_operator", "n23", None, ()),
    (
        "n23",
        "contract",
        "法務維護並確定合同內容",
        "approval",
        "legal_manager",
        "n24",
        None,
        ("approval_sheet",),
    ),
    (
        "n24",
        "contract",
        "導出合同文本及審批單",
        "form",
        "legal_manager",
        "n25",
        None,
        ("approval_sheet",),
    ),
    (
        "n25",
        "contract",
        "中標人在 ECP 簽字蓋章",
        "external_placeholder",
        "external_party",
        "n26",
        None,
        ("signature_proof",),
    ),
    (
        "n26",
        "contract",
        "招標人簽字蓋章",
        "external_placeholder",
        "executive",
        "n27",
        None,
        ("signature_proof",),
    ),
    ("n27", "contract", "合同生效", "approval", "procurement_manager", None, None, ()),
)

_TENDER_LONG_ACTIONS: dict[str, tuple[dict[str, object], ...]] = {
    "n01": (
        _artifact_action("batch_doc", "登記批復文件"),
        _workflow_task_action("submit", "提交立項材料"),
    ),
    "n02": _purchase_intake_actions("procurement_tender_v1"),
    "n03": (_workflow_task_action("approve", "完成需求審批"),),
    "n04": (_workflow_task_action("approve", "完成項目／資金審批"),),
    "n05": (_workflow_task_action("approve", "完成財務審批"),),
    "n06": (_workflow_task_action("approve", "確認採購策略"),),
    "n07": (
        _tender_create_action(),
        _workflow_task_action("submit", "確認傳輸並推進"),
    ),
    "n08": (
        _artifact_action("tender_plan", "登記採購項目計劃"),
        _workflow_task_action("submit", "提交項目計劃"),
    ),
    "n09": (
        _artifact_action("agent_assignment", "登記代理委派"),
        _workflow_task_action("submit", "確認代理分配"),
    ),
    "n10": (
        _artifact_action("procurement_doc", "登記採購文件"),
        _workflow_task_action("submit", "提交採購文件"),
    ),
    "n11": (
        _command(
            "tender_publish",
            "發布招標公告",
            bindings={"id": _tender_notice_bindings()},
        ),
        _artifact_action("tender_notice", "登記招標公告"),
        _workflow_task_action("submit", "確認發布並推進"),
    ),
    "n12": (
        _command(
            "tender_submit_bid",
            "提交密封投標",
            bindings={
                "notice": (
                    "tender.notice_ref",
                    "instance.state.tender_notice_ref",
                    "item.state.tender_notice_ref",
                )
            },
        ),
        _workflow_task_action("submit", "確認報名投標"),
    ),
    "n13": (
        _command(
            "tender_open",
            "開標",
            bindings={"id": _tender_notice_bindings()},
        ),
        _artifact_action("bid_opening_record", "登記開標記錄"),
        _workflow_task_action("submit", "確認開標並推進"),
    ),
    "n14": (
        _command(
            "tender_evaluate",
            "評標",
            bindings={"id": _tender_notice_bindings()},
        ),
        _artifact_action("eval_report", "登記評標報告"),
        _workflow_task_action("submit", "提交評標結果"),
    ),
    "n15": (
        _command(
            "tender_award",
            "確認定標",
            bindings={"id": _tender_notice_bindings()},
        ),
        _artifact_action("award_result", "登記中標結果"),
        _workflow_task_action("submit", "確認結果並推進"),
    ),
    "n16": (
        _command(
            "tender_detail",
            "核對發布結果",
            bindings={"id": _tender_notice_bindings()},
        ),
        _workflow_task_action("submit", "確認結果已發布"),
    ),
    "n17": (
        _artifact_action("signature_proof", "登記招標人簽章"),
        _workflow_task_action("submit", "確認簽章並推進"),
    ),
    "n18": (_workflow_task_action("approve", "確認合同經辦分配"),),
    "n19": (
        _command(
            "legal_contract_save",
            "生成合同草稿",
            bindings={
                "id": _contract_bindings(),
                "title": ("instance.title", "item.title"),
                "amount": ("instance.state.amount", "instance.amount", "item.amount"),
                "counterparty": (
                    "instance.state.supplier_name",
                    "item.state.supplier_name",
                ),
            },
        ),
        _artifact_action("contract_draft", "登記合同草稿"),
        _workflow_task_action("submit", "提交合同草稿"),
    ),
    "n20": (_workflow_task_action("approve", "審批合同草稿"),),
    "n21": (_workflow_task_action("submit", "確認賣方信息"),),
    "n22": (
        _command("erp_overview", "檢視自動生成的採購訂單"),
        _command(
            "wf_instance_detail",
            "檢視流程自動節點",
            bindings={"id": ("instance.id", "item.id")},
        ),
    ),
    "n23": (
        _command(
            "legal_contract_review",
            "提交合同審查",
            bindings={"id": _contract_bindings()},
        ),
        _artifact_action("approval_sheet", "登記合同審批單"),
        _workflow_task_action("approve", "確認合同內容"),
    ),
    "n24": (
        _artifact_action("approval_sheet", "登記導出審批單"),
        _workflow_task_action("submit", "確認文本已導出"),
    ),
    "n25": (
        _artifact_action("signature_proof", "登記中標人簽章"),
        _workflow_task_action("submit", "確認中標人簽章"),
    ),
    "n26": (
        _artifact_action("signature_proof", "登記招標人簽章"),
        _workflow_task_action("submit", "確認招標人簽章"),
    ),
    "n27": (_workflow_task_action("approve", "確認合同生效"),),
}


def _tender_long(template_key: str) -> dict[str, object]:
    stages = [
        {"key": "batch", "name": "立項與批次", "seq": 1},
        {"key": "approval", "name": "採購申請審批", "seq": 2},
        {"key": "ecp", "name": "ECP 招標準備", "seq": 3},
        {"key": "award", "name": "開評標與定標", "seq": 4},
        {"key": "contract", "name": "合同與訂單", "seq": 5},
    ]
    nodes = [
        _node(
            template_key,
            key,
            step,
            stage,
            name,
            kind,
            responsibility,
            next_key=next_key,
            reject_key=reject_key,
            permission=(
                "procurement.workflow.external"
                if responsibility == "external_party"
                else (
                    "procurement.workflow.use"
                    if responsibility in {"initiator", "procurement_operator"}
                    else "procurement.workflow.approve"
                )
            ),
            artifacts=artifacts,
            actions=_TENDER_LONG_ACTIONS[key],
        )
        for step, (
            key,
            stage,
            name,
            kind,
            responsibility,
            next_key,
            reject_key,
            artifacts,
        ) in enumerate(_TENDER_LONG_NODES, start=1)
    ]
    return _definition(
        workflow_key="procurement_tender_v1",
        name="完整招標採購流程",
        description="從立項、ECP 招標、開評定標到合同與採購訂單的 27 步長鏈。",
        start_node_key="n01",
        stages=stages,
        nodes=nodes,
    )


def workflow_blueprints_for_industry(template_key: str) -> list[dict[str, object]]:
    """Return tenant-isolated workflow definitions for one industry preset."""
    key = str(template_key or "").strip()
    get_blueprint(key)
    if key in NON_OPERATIONAL_TEMPLATE_KEYS:
        return []
    definitions = [
        _internal_purchase(key),
        _tender_long(key),
        _tender_gateway(key),
    ]
    return deepcopy(definitions)


def validate_workflow_blueprints() -> list[str]:
    errors: list[str] = []
    for template_key, responsibilities in _RESPONSIBILITY_POSITIONS.items():
        blueprint = get_blueprint(template_key)
        positions = {item["code"] for item in blueprint["positions"]}
        for responsibility, position_code in responsibilities.items():
            if position_code not in positions:
                errors.append(f"{template_key}.{responsibility}: unknown position {position_code}")
        definitions = workflow_blueprints_for_industry(template_key)
        counts = {item["workflow_key"]: len(item["nodes"]) for item in definitions}
        expected = {
            "internal_purchase_v1": 3,
            "procurement_tender_v1": 27,
            "procurement_tender_v2": 10,
        }
        if counts != expected:
            errors.append(f"{template_key}: workflow node counts {counts!r}")
        for definition in definitions:
            for node in definition["nodes"]:
                actions = node.get("actions")
                if not isinstance(actions, list) or not actions:
                    errors.append(
                        f"{template_key}.{definition['workflow_key']}."
                        f"{node['node_key']}: missing command actions"
                    )
                    continue
                for action in actions:
                    if not isinstance(action, dict) or not action.get("tool_name"):
                        errors.append(
                            f"{template_key}.{definition['workflow_key']}."
                            f"{node['node_key']}: invalid command action"
                        )
    return errors


WORKFLOW_BLUEPRINT_VALIDATION_ERRORS = tuple(validate_workflow_blueprints())
if WORKFLOW_BLUEPRINT_VALIDATION_ERRORS:
    raise ValueError(
        "invalid workflow blueprints:\n- " + "\n- ".join(WORKFLOW_BLUEPRINT_VALIDATION_ERRORS)
    )


__all__ = [
    "NON_OPERATIONAL_TEMPLATE_KEYS",
    "WORKFLOW_BLUEPRINT_REVISION",
    "WORKFLOW_BLUEPRINT_SCHEMA_VERSION",
    "WORKFLOW_BLUEPRINT_VALIDATION_ERRORS",
    "WORKFLOW_COMMAND_BINDING_SCHEMA_VERSION",
    "validate_workflow_blueprints",
    "workflow_blueprints_for_industry",
]
