from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api import browser_runtime as browser_api
from app.api.deps import ActorContext
from app.core.config import Settings
from app.core.security import decode_access_token
from app.db.session import system_session, tenant_session
from app.services import browser_runtime


def _actor(*, tenant_id: UUID | None = None, user_id: UUID | None = None) -> ActorContext:
    return ActorContext(
        user_id=user_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        tenant_slug="browser-test",
        tenant_name="Browser Test",
        industry_template_key="generic_warehouse",
        username="browser-admin",
        display_name="Browser Admin",
        role_level=10,
        topology_level=10,
        topology_title="System Administrator",
        permissions=frozenset({"browser.read", "browser.run"}),
    )


def test_browser_protocol_rejects_raw_selectors_secrets_and_unbounded_waits() -> None:
    valid = browser_runtime.validate_steps(
        [
            {"action": "navigate", "path": "/#/dashboard"},
            {"action": "click", "locator": {"role": "button", "name": "Refresh"}},
            {"action": "observe", "kind": "no_console_errors"},
            {"action": "screenshot"},
        ]
    )
    assert [step["action"] for step in valid] == ["navigate", "click", "observe", "screenshot"]

    with pytest.raises(HTTPException):
        browser_runtime.validate_steps([{"action": "click", "locator": {"selector": "#danger"}}])
    with pytest.raises(HTTPException):
        browser_runtime.validate_steps(
            [
                {
                    "action": "fill",
                    "locator": {"label": "Password"},
                    "value": "secret",
                    "sensitive": True,
                }
            ]
        )
    with pytest.raises(HTTPException):
        browser_runtime.validate_steps([{"action": "wait", "milliseconds": 6000}])


def test_browser_routes_are_native_and_worker_exchange_is_hidden() -> None:
    paths = {getattr(route, "path", ""): route for route in browser_api.router.routes}
    assert {
        "/api/browser-runtime/capabilities",
        "/api/browser-runtime/journeys",
        "/api/browser-runtime/runs",
        "/api/browser-runtime/runs/{run_id}",
        "/api/browser-runtime/runs/{run_id}/cancel",
        "/api/browser-runtime/artifacts/{artifact_id}",
        "/api/browser-runtime/internal/runs/{run_id}/session",
    } == set(paths)
    assert paths["/api/browser-runtime/internal/runs/{run_id}/session"].include_in_schema is False


@pytest.mark.integration
def test_browser_run_round_trip_and_short_lived_actor_exchange() -> None:
    tenant_id, user_id = uuid4(), uuid4()
    slug = f"browser-{tenant_id.hex[:12]}"
    with system_session() as session:
        session.execute(
            text(
                """INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                   VALUES (:id, :slug, 'Browser Test', 'generic_warehouse')"""
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                """INSERT INTO iam.users(id, username, display_name, password_hash)
                   VALUES (:id, :username, 'Browser Admin', 'unused')"""
            ),
            {"id": user_id, "username": f"browser-{user_id.hex[:12]}"},
        )
    with tenant_session(tenant_id) as session:
        session.execute(
            text(
                """INSERT INTO iam.memberships(
                     tenant_id, user_id, role_level, topology_level, topology_title
                   ) VALUES (
                     :tenant_id, :user_id, 10, 10, 'System Administrator'
                   )"""
            ),
            {"tenant_id": tenant_id, "user_id": user_id},
        )
    actor = _actor(tenant_id=tenant_id, user_id=user_id)
    settings = Settings(
        browser_runtime_enabled=True,
        browser_allowed_origins=["http://localhost:8080"],
        browser_worker_token="w" * 64,
        jwt_secret="j" * 64,
    )
    journey = browser_runtime.create_journey(
        actor,
        {
            "journey_key": "dashboard-smoke",
            "name": "Dashboard smoke",
            "steps": [
                {"action": "navigate", "path": "/#/dashboard"},
                {"action": "screenshot"},
            ],
        },
    )["journey"]
    created = browser_runtime.create_run(
        actor,
        {"journey": journey["journey_key"]},
        settings,
    )["run"]
    run_id = UUID(created["id"])
    assert created["status"] == "queued"
    assert len(browser_runtime.run_detail(actor, run_id)["steps"]) == 2

    worker_id = "pytest-browser-worker"
    claimed = system_session()
    with claimed as session:
        row = (
            session.execute(
                text("SELECT * FROM app.claim_next_browser_run(:worker)"),
                {"worker": worker_id},
            )
            .mappings()
            .one()
        )
    assert row["run_id"] == run_id
    exchange = browser_runtime.worker_session_token(
        run_id, tenant_id, worker_id, "w" * 64, settings
    )
    token_user_id, token_tenant_id = decode_access_token(settings=settings, token=exchange["token"])
    assert token_user_id == user_id
    assert token_tenant_id == tenant_id
    assert exchange["tenant"] == slug

    with pytest.raises(HTTPException) as denied:
        browser_runtime.worker_session_token(run_id, tenant_id, worker_id, "bad", settings)
    assert denied.value.status_code == 401
    with pytest.raises(HTTPException) as wrong_tenant:
        browser_runtime.worker_session_token(run_id, uuid4(), worker_id, "w" * 64, settings)
    assert wrong_tenant.value.status_code == 404
    cancelled = browser_runtime.cancel_run(actor, run_id)["run"]
    assert cancelled["cancel_requested_at"] is not None

    with tenant_session(tenant_id) as session:
        assert session.execute(text("SELECT count(*) FROM browser_runtime.runs")).scalar_one() == 1
        assert session.execute(text("SELECT count(*) FROM browser_runtime.steps")).scalar_one() == 2
