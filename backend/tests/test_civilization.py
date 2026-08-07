from uuid import uuid4

from fastapi.testclient import TestClient

from app.api import civilization as civilization_api
from app.api.deps import ActorContext, current_actor
from app.main import app
from app.services.civilization import _can_delete


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
        lambda received, payload: calls.append(("create", (received, payload)))
        or {"ok": True, "thought": {"id": str(thought_id)}},
    )
    monkeypatch.setattr(
        civilization_api,
        "delete_thought",
        lambda received, received_id: calls.append(("delete", (received, received_id)))
        or {"ok": True, "deleted_id": str(received_id)},
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
        assert client.delete(f"/api/civilization/thoughts/{thought_id}").status_code == 200
    finally:
        app.dependency_overrides.clear()

    assert [call[0] for call in calls] == ["list", "create", "delete"]
    assert calls[0][1] is actor
    assert calls[1][1][0] is actor
    assert calls[2][1] == (actor, thought_id)
