from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi.testclient import TestClient

from app.api import router
from app.api.deps import ActorContext, current_actor
from app.main import app


def _actor() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=UUID("00000000-0000-0000-0000-000000000002"),
        tenant_slug="example",
        tenant_name="Example",
        industry_template_key="generic_warehouse",
        username="owner",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset(),
    )


def test_executive_overview_contract_is_permission_filtered(monkeypatch) -> None:
    snapshot = {
        "scope": "permission-filtered",
        "generated_at": datetime.now(UTC),
        "access": {"gis": True, "permissions": True, "audit": True},
        "modules": {
            "gis": {"status": "ready", "warehouses": 1},
            "permissions": {"status": "ready", "users": 3},
            "audit": {"status": "ready", "events": 2},
            "warehouse": {"status": "unavailable"},
        },
    }
    app.dependency_overrides[current_actor] = _actor
    monkeypatch.setattr(router, "executive_overview_payload", lambda _actor: snapshot)
    try:
        response = TestClient(app).get("/api/overview/executive")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"] == "permission-filtered"
    assert payload["access"]["gis"] is True
    assert payload["modules"]["warehouse"]["status"] == "unavailable"
