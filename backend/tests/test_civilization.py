from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import civilization as civilization_api
from app.api.deps import ActorContext, current_actor
from app.main import app
from app.services.civilization import (
    _can_delete,
    _clean_content,
    _clean_lenses,
    _content_locale,
    _merge_content,
    _merged_lenses,
    _merged_localized,
    template_catalog,
)
from app.terminal.catalog import availability, entry_by_tool_name


def _actor(*, role_level: int = 5, permissions: frozenset[str] = frozenset()) -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="civilization-test",
        tenant_name="Civilization Test",
        industry_template_key="general",
        username="reader@example.test",
        display_name="Reader",
        role_level=role_level,
        topology_level=role_level,
        topology_title=None,
        permissions=permissions,
    )


def test_delete_policy_allows_creator_and_company_administrator() -> None:
    member = _actor()
    another_user = uuid4()

    assert _can_delete(member, member.user_id) is True
    assert _can_delete(member, another_user) is False
    assert _can_delete(_actor(role_level=10), another_user) is True
    assert _can_delete(_actor(permissions=frozenset({"settings.manage"})), another_user) is True


def test_lenses_are_validated_and_localized_for_storage() -> None:
    lenses = _clean_lenses(
        {"lenses": [{"name": "制度", "text": "先看約束，再看選擇。"}]},
        "zh",
    )

    assert lenses == [{"name": {"zh": "制度"}, "text": {"zh": "先看約束，再看選擇。"}}]
    assert _merged_localized({"en": "Question"}, "問題", "zh") == {
        "en": "Question",
        "zh": "問題",
    }
    assert _merged_lenses(
        [{"name": {"en": "System"}, "text": {"en": "Read constraints first."}}],
        lenses,
    ) == [
        {
            "name": {"en": "System", "zh": "制度"},
            "text": {"en": "Read constraints first.", "zh": "先看約束，再看選擇。"},
        }
    ]


def test_swiss_b_content_keeps_layout_and_localized_characters_separate() -> None:
    content = _clean_content(
        {
            "title": "人的成長",
            "short": "成長是網絡位置的改變。",
            "thesis": "因為你的存在，周圍世界更有秩序。",
            "eyebrow": "CIVILIZATION · QUESTION",
            "category_label": "JUDGEMENT",
            "sections": [
                {
                    "marker": "20",
                    "kicker": "ENTER THE NETWORK",
                    "heading": "進入網絡。",
                    "paragraphs": ["學習規則，積累能力。"],
                }
            ],
        },
        domain="judgement",
    )
    stored = _merge_content({}, content, "zh")

    assert stored["template_key"] == "swiss_b_longform_v1"
    assert _content_locale(stored, "zh")["sections"][0]["marker"] == "20"
    assert template_catalog(_actor())["templates"][0]["layout_locked"] is True
    assert "sections[].paragraphs[]" in template_catalog(_actor())["templates"][0]["editable_slots"]


def test_civilization_openapi_exposes_draft_publish_cli_and_revision_lifecycle() -> None:
    route_paths = {getattr(route, "path", "") for route in civilization_api.router.routes}

    assert "/api/civilization/templates" in route_paths
    assert "/api/civilization/cli/manifest" in route_paths
    assert "/api/civilization/api-keys" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/draft" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/preview" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/publish" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/revisions" in route_paths
    assert "/api/civilization/thoughts/{thought_id}/revisions/{revision_no}/restore" in route_paths


def test_civilization_auto_runtime_genes_are_backed_by_native_routes() -> None:
    tool_names = (
        "civilization_api_key_issue",
        "civilization_api_keys_list",
        "civilization_api_key_revoke",
        "civilization_cli_show",
        "civilization_templates_list",
        "civilization_post_list",
        "civilization_post_observe",
        "civilization_post_delete",
        "civilization_post_create",
        "civilization_post_draft_update",
        "civilization_post_preview",
        "civilization_post_publish",
        "civilization_revisions_list",
        "civilization_post_restore",
        "civilization_lens_upsert",
    )

    for tool_name in tool_names:
        entry = entry_by_tool_name(tool_name)
        assert entry is not None
        assert availability(entry) == "active"


def test_civilization_routes_delegate_to_one_tenant_service(monkeypatch) -> None:
    actor = _actor()
    thought_id = uuid4()
    calls: list[tuple[str, object]] = []
    monkeypatch.setattr(
        civilization_api,
        "list_thoughts",
        lambda received: calls.append(("list", received)) or {"thoughts": []},
    )
    monkeypatch.setattr(
        civilization_api,
        "create_thought",
        lambda received, payload: (
            calls.append(("create", (received, payload)))
            or {"ok": True, "thought": {"id": str(thought_id)}}
        ),
    )
    monkeypatch.setattr(
        civilization_api,
        "delete_thought",
        lambda received, received_id: (
            calls.append(("delete", (received, received_id)))
            or {"ok": True, "deleted_id": str(received_id)}
        ),
    )
    monkeypatch.setattr(
        civilization_api,
        "update_thought",
        lambda received, received_id, payload: (
            calls.append(("update", (received, received_id, payload)))
            or {"ok": True, "thought": {"id": str(received_id), "revision": 2}}
        ),
    )
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        assert client.get("/api/civilization/thoughts").status_code == 200
        created = client.post(
            "/api/civilization/thoughts",
            json={"domain": "time", "title": "Question", "short": "Prompt", "thesis": "Thesis"},
        )
        assert created.status_code == 201
        updated = client.put(
            f"/api/civilization/thoughts/{thought_id}",
            json={
                "domain": "time",
                "title": "Question",
                "short": "Prompt",
                "thesis": "Thesis",
                "expected_revision": 1,
            },
        )
        assert updated.status_code == 200
        assert client.delete(f"/api/civilization/thoughts/{thought_id}").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert [call[0] for call in calls] == ["list", "create", "update", "delete"]
    assert calls[0][1] is actor
    assert calls[1][1][0] is actor
    assert calls[2][1][0:2] == (actor, thought_id)
    assert calls[3][1] == (actor, thought_id)
