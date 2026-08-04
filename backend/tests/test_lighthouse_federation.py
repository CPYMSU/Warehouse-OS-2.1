from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.config import Settings
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.lighthouse_federation import (
    LighthouseFederationError,
    authenticate_device_token,
    create_pairing_challenge,
    create_remote_run,
    enroll_device,
    get_run,
    handle_device_message,
    list_run_events,
    pending_outbox,
)
from app.services.lighthouse_protocol import (
    PROTOCOL,
    LighthouseProtocolError,
    make_envelope,
    parse_device_message,
)


def _actor() -> ActorContext:
    return ActorContext(
        user_id=uuid4(),
        tenant_id=uuid4(),
        tenant_slug="lighthouse-test",
        tenant_name="Lighthouse Test",
        industry_template_key="generic_warehouse",
        username="owner",
        display_name="Owner",
        role_level=10,
        topology_level=10,
        topology_title="System Administrator",
        permissions=frozenset({"ai.use"}),
    )


def test_protocol_round_trip_redacts_credentials() -> None:
    run_id = uuid4()
    message_id = uuid4()
    raw = {
        "protocol": PROTOCOL,
        "message_id": str(message_id),
        "type": "run.completed",
        "sent_at": "2026-08-04T09:00:00Z",
        "payload": {
            "run_id": str(run_id),
            "status": "completed",
            "result": {
                "message": "ready",
                "api_token": "must-not-reach-warehouse-storage",
                "nested": {"password": "also-secret"},
            },
        },
    }

    parsed = parse_device_message(raw)

    assert parsed["message_id"] == str(message_id)
    assert parsed["payload"]["result"] == {
        "message": "ready",
        "api_token": "[redacted]",
        "nested": {"password": "[redacted]"},
    }


def test_protocol_rejects_commands_and_unbound_approval_digests() -> None:
    with pytest.raises(LighthouseProtocolError, match="Unsupported device message"):
        parse_device_message(
            {
                "protocol": PROTOCOL,
                "message_id": str(uuid4()),
                "type": "shell.execute",
                "sent_at": "2026-08-04T09:00:00Z",
                "payload": {},
            }
        )

    with pytest.raises(LighthouseProtocolError, match="SHA-256"):
        parse_device_message(
            {
                "protocol": PROTOCOL,
                "message_id": str(uuid4()),
                "type": "operation.approval_required",
                "sent_at": "2026-08-04T09:00:00Z",
                "payload": {"run_id": str(uuid4()), "operation_digest": "not-a-digest"},
            }
        )


def test_warehouse_envelope_is_versioned_and_idempotent() -> None:
    message_id = uuid4()
    envelope = make_envelope(
        "run.offer",
        {
            "run_id": str(uuid4()),
            "goal": "Summarize the visible workspace status",
            "policy": {"mode": "read_only", "allow_local_write": False},
        },
        message_id=message_id,
    )

    assert envelope["protocol"] == PROTOCOL
    assert envelope["message_id"] == str(message_id)
    assert envelope["type"] == "run.offer"


def test_device_can_acknowledge_a_durable_warehouse_message() -> None:
    acknowledged = uuid4()
    parsed = parse_device_message(
        {
            "protocol": PROTOCOL,
            "message_id": str(uuid4()),
            "type": "message.ack",
            "sent_at": "2026-08-04T09:00:00Z",
            "payload": {"message_id": str(acknowledged)},
        }
    )

    assert parsed["payload"]["message_id"] == str(acknowledged)


def test_write_capable_remote_run_is_closed_before_database_access() -> None:
    with pytest.raises(LighthouseFederationError, match="read-only") as raised:
        create_remote_run(
            _actor(),
            device_id=uuid4(),
            goal="Delete a file",
            read_only=False,
        )

    assert raised.value.status_code == 409


def test_lighthouse_routes_are_native_and_enrollment_is_public(monkeypatch) -> None:
    from app.api import lighthouse_federation as api

    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    monkeypatch.setattr(
        api,
        "list_devices",
        lambda _actor: [
            {
                "id": str(uuid4()),
                "label": "Mac mini",
                "status": "active",
                "online": False,
            }
        ],
    )
    monkeypatch.setattr(
        api,
        "enroll_device",
        lambda _settings, **_payload: {
            "ok": True,
            "device_id": str(uuid4()),
            "device_token": "shown-once",
        },
    )
    client = TestClient(app)
    try:
        devices = client.get("/api/lighthouse/devices")
        enrolled = client.post(
            "/api/lighthouse/device/v1/enroll",
            json={
                "pairing_code": "x" * 40,
                "instance_id": str(uuid4()),
                "label": "Mac mini",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert devices.status_code == 200
    assert devices.json()["devices"][0]["label"] == "Mac mini"
    assert enrolled.status_code == 201
    assert enrolled.json()["device_token"] == "shown-once"


@pytest.mark.integration
def test_pairing_run_delivery_and_device_ack_are_durable_in_postgresql() -> None:
    actor = _actor()
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": actor.tenant_id, "slug": actor.tenant_slug, "name": actor.tenant_name},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": actor.user_id,
                "username": actor.username,
                "display_name": actor.display_name,
                "password_hash": hash_password("federation-integration-test"),
            },
        )
    settings = Settings(
        public_origin="https://warehouse.test",
        integration_secret="federation-test-secret-that-is-at-least-32-bytes",
    )
    challenge = create_pairing_challenge(actor, settings, label="Mac mini")
    instance_id = uuid4()
    enrolled = enroll_device(
        settings,
        pairing_code=challenge["pairing_code"],
        instance_id=instance_id,
        label="Mac mini",
    )
    with pytest.raises(LighthouseFederationError, match="Invalid or expired"):
        enroll_device(
            settings,
            pairing_code=challenge["pairing_code"],
            instance_id=uuid4(),
        )

    principal = authenticate_device_token(enrolled["device_token"], settings)
    run, offer, offer_message_id = create_remote_run(
        actor,
        device_id=enrolled["device_id"],
        goal="Summarize the local workspace",
        client_request_id="federation-integration-run",
    )
    assert [item["message_id"] for item in pending_outbox(principal)] == [
        str(offer_message_id)
    ]
    handle_device_message(
        principal,
        {
            "protocol": PROTOCOL,
            "message_id": str(uuid4()),
            "type": "message.ack",
            "sent_at": "2026-08-04T09:00:00Z",
            "payload": {"message_id": offer["message_id"]},
        },
    )
    assert pending_outbox(principal) == []

    accepted_message_id = uuid4()
    accepted = {
        "protocol": PROTOCOL,
        "message_id": str(accepted_message_id),
        "type": "run.accepted",
        "sent_at": "2026-08-04T09:00:01Z",
        "payload": {"run_id": run["id"], "local_run_ref": "local-run-1"},
    }
    first = handle_device_message(principal, accepted)
    duplicate = handle_device_message(principal, accepted)
    assert first["duplicate"] is False
    assert duplicate["duplicate"] is True

    handle_device_message(
        principal,
        {
            "protocol": PROTOCOL,
            "message_id": str(uuid4()),
            "type": "run.completed",
            "sent_at": "2026-08-04T09:00:02Z",
            "payload": {
                "run_id": run["id"],
                "status": "completed",
                "result": {"message": "Local summary ready"},
            },
        },
    )

    stored_run = get_run(actor, UUID(run["id"]))
    events = list_run_events(actor, UUID(run["id"]))
    assert stored_run["status"] == "completed"
    assert stored_run["result"] == {"message": "Local summary ready"}
    assert [event["type"] for event in events] == ["run.accepted", "run.completed"]
    with tenant_session(actor.tenant_id) as session:
        stored = session.execute(
            text(
                """
                SELECT p.code_hash, d.token_hash
                FROM lighthouse.pairing_challenges p
                JOIN lighthouse.devices d ON d.tenant_id = p.tenant_id
                WHERE p.id = :challenge_id AND d.id = :device_id
                """
            ),
            {
                "challenge_id": UUID(challenge["challenge_id"]),
                "device_id": principal.device_id,
            },
        ).mappings().one()
    assert challenge["pairing_code"] not in stored["code_hash"]
    assert enrolled["device_token"] not in stored["token_hash"]
