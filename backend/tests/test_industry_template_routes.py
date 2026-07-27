from uuid import UUID

from fastapi.testclient import TestClient

from app.api import router as router_module
from app.api.deps import ActorContext, current_actor
from app.main import app


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
    )


def test_industry_template_catalogue_route(monkeypatch) -> None:
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(
        router_module,
        "list_template_summaries",
        lambda: [{"key": "power_system", "name": "電力系統"}],
    )
    try:
        response = TestClient(app).get("/api/platform/templates")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "templates": [{"key": "power_system", "name": "電力系統"}],
        "active_template": "power_system",
    }


def test_industry_template_detail_route_returns_not_found(monkeypatch) -> None:
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(router_module, "get_template_detail", lambda _key: None)
    try:
        response = TestClient(app).get("/api/industry-templates/missing")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
