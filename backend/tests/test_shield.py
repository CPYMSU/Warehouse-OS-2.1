from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api import shield as shield_api
from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import system_session, tenant_session
from app.services import shield


def _context(
    *,
    user_id: UUID | None = None,
    tenant_id: UUID | None = None,
    permissions: frozenset[str] = frozenset({"audit.read"}),
    auth_kind: str = "session",
) -> ActorContext:
    return ActorContext(
        user_id=user_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        tenant_slug="shield-test",
        tenant_name="SHIELD Test",
        industry_template_key="generic_warehouse",
        username="shield-owner",
        display_name="SHIELD Owner",
        role_level=10,
        topology_level=10,
        topology_title="Platform Owner",
        permissions=permissions,
        auth_kind=auth_kind,
    )


def _agent_status(
    *,
    alerts: list[dict[str, object]] | None = None,
    sampled_at: str = "2026-07-31T12:00:00+00:00",
) -> dict[str, object]:
    return {
        "ok": True,
        "system_vitals": {
            "schema_version": 1,
            "sampled_at": sampled_at,
            "poll_hint_seconds": 5,
            "state": "degraded" if alerts else "healthy",
            "severity": 3 if alerts else 0,
            "health_score": 76 if alerts else 100,
            "alerts": alerts or [],
            "services": [{"id": "warehouse-api", "state": "online"}],
            "data_sources": {"kernel": {"state": "online"}},
        },
        "guardian_tail": ["SHIELD fixture sample"],
    }


def test_shield_contract_is_closed_and_power_plane_is_enforced(monkeypatch) -> None:
    route_paths = {getattr(route, "path", "") for route in shield_api.router.routes}
    assert route_paths == {
        "/api/shield/status",
        "/api/shield/repair",
        "/api/shield/risks/{execution_id}/review",
    }
    assert shield.SHIELD_ACTIONS == {
        "healthcheck",
        "restart-api",
        "restart-firefighter",
        "reload-nginx",
        "restart-nginx",
        "clear-health-flag",
    }

    monkeypatch.setattr(shield, "_is_platform_owner", lambda _user_id: True)
    shield.require_shield_access(_context())
    with pytest.raises(HTTPException) as missing_audit:
        shield.require_shield_access(_context(permissions=frozenset()))
    assert missing_audit.value.status_code == 403
    with pytest.raises(HTTPException) as runtime_key:
        shield.require_shield_access(_context(auth_kind="runtime_api_key"))
    assert runtime_key.value.status_code == 403


@pytest.mark.integration
def test_shield_status_incident_repair_and_hash_chain_round_trip(monkeypatch) -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, 'SHIELD Test', 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": f"shield-{tenant_id.hex[:12]}"},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(
                  id, username, display_name, password_hash, is_platform_owner
                ) VALUES (:id, :username, 'SHIELD Owner', 'unused', true)
                """
            ),
            {"id": user_id, "username": f"shield-owner-{user_id.hex[:12]}"},
        )
    actor = _context(user_id=user_id, tenant_id=tenant_id)
    settings = Settings(
        shield_agent_token="x" * 64,
        shield_repair_apply=False,
    )
    responses = [
        _agent_status(
            alerts=[
                {
                    "code": "api-latency",
                    "label": "API latency above threshold",
                    "severity": 3,
                }
            ]
        ),
        _agent_status(sampled_at="2026-07-31T12:00:05+00:00"),
    ]

    def fake_agent(_settings, operation, **kwargs):
        if operation == "status":
            return responses.pop(0)
        assert operation == "repair"
        assert kwargs["apply"] is False
        return {
            "ok": True,
            "status": "succeeded",
            "applied": False,
            "result": {"status": "dry-run", "action": kwargs["action"]},
        }

    monkeypatch.setattr(shield, "_agent_request", fake_agent)

    first = shield.get_shield_status(actor, settings)
    assert first["ok"] is True
    assert first["state"] == "degraded"
    assert len(first["open_incidents"]) == 1

    second = shield.get_shield_status(actor, settings)
    assert second["state"] == "healthy"
    assert second["open_incidents"] == []

    with pytest.raises(HTTPException) as confirmation:
        shield.execute_shield_repair(
            actor,
            settings,
            action="restart-api",
            confirm=False,
            apply_requested=True,
            request_id=str(uuid4()),
        )
    assert confirmation.value.status_code == 409

    request_id = str(uuid4())
    repair = shield.execute_shield_repair(
        actor,
        settings,
        action="restart-api",
        confirm=True,
        apply_requested=True,
        request_id=request_id,
    )
    assert repair["ok"] is True
    assert repair["applied"] is False
    assert repair["dry_run"] is True

    repeated = shield.execute_shield_repair(
        actor,
        settings,
        action="restart-api",
        confirm=True,
        apply_requested=True,
        request_id=request_id,
    )
    assert repeated["repair_id"] == repair["repair_id"]
    assert repeated["action"] == repair["action"]
    assert repeated["result"] == repair["result"]

    with tenant_session(tenant_id) as session:
        snapshot_count = session.execute(text("SELECT count(*) FROM shield.snapshots")).scalar_one()
        incident = session.execute(
            text("SELECT state, resolved_at FROM shield.incidents")
        ).mappings().one()
        repair_row = session.execute(
            text("SELECT status, applied FROM shield.repair_runs")
        ).mappings().one()
        chain = session.execute(
            text(
                """
                SELECT event_type, previous_hash, event_hash
                FROM shield.audit_chain ORDER BY id
                """
            )
        ).mappings().all()
        general_audit = session.execute(
            text("SELECT count(*) FROM audit.events WHERE event_type = 'shield_repair'")
        ).scalar_one()

    assert snapshot_count == 1
    assert incident["state"] == "resolved"
    assert incident["resolved_at"] is not None
    assert repair_row == {"status": "succeeded", "applied": False}
    assert general_audit == 1
    assert [row["event_type"] for row in chain] == [
        "incident.opened",
        "incident.resolved",
        "repair.requested",
        "repair.succeeded",
    ]
    assert chain[0]["previous_hash"] is None
    for previous, current in zip(chain, chain[1:]):
        assert current["previous_hash"] == previous["event_hash"]
