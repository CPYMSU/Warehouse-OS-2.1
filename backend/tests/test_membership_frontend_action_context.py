from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_membership_review_buttons_send_resource_context_not_tool_orders() -> None:
    source = (ROOT / "frontend/v2/pages/pages-perms.jsx").read_text(encoding="utf-8")

    assert 'schema: "warehouse.resource-action-context.v1"' in source
    assert 'resource_type: "iam.membership_request"' in source
    assert "resource_ref: String(id)" in source
    assert "registrations_pending" in source
    assert "registration_approve" in source
    assert "只使用 membership_approve" not in source
    assert "不得用 user_add" not in source


def test_secretary_accepts_pages_and_generic_resource_action_contexts() -> None:
    source = (ROOT / "frontend/v2/core.jsx").read_text(encoding="utf-8")

    assert "warehouse.pages-action-context.v1" in source
    assert "warehouse.resource-action-context.v1" in source
    assert "related_resources" in source


def test_department_and_appointment_buttons_use_shared_capability_contracts() -> None:
    source = (ROOT / "frontend/v2/pages/pages-perms.jsx").read_text(encoding="utf-8")

    assert 'openOrgAction("organization_department_create"' in source
    assert 'openOrgAction("organization_user_assign"' in source
    assert 'openOrgAction("organization_user_appointment_add"' in source
    assert 'openOrgAction("organization_user_appointment_update"' in source
    assert 'openOrgAction("organization_user_appointment_remove"' in source
    assert "governanceLabelOf(governanceIdentity)" in source
    assert "Math.min(11, governanceLevelOf(u))" in source


def test_department_create_keeps_company_root_available_as_parent() -> None:
    source = (ROOT / "frontend/v2/pages/pages-perms.jsx").read_text(encoding="utf-8")

    assert "const isSelf = !isCreate" in source
    assert 't("公司本體 · 直屬公司")' in source
    assert ": [company].concat(rawUnits)" in source
