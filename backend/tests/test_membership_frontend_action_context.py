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
