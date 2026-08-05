from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password, verify_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.legacy_capability_runtime import execute_retained_capability
from app.services.templates import provision_tenant_template

pytestmark = pytest.mark.integration


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"member-{tenant_id.hex[:10]}"
    username = f"member-owner-{user_id.hex[:10]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id,slug,name,industry_template_key)
                VALUES (:id,:slug,'Member Provision Test','generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id,username,display_name,password_hash)
                VALUES (:id,:username,'Member Owner',:password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        template = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name="Member Provision Test",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id,user_id,position_code,role_level,topology_level,topology_title
                ) VALUES (:tenant_id,:user_id,:position_code,10,10,'Owner')
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "position_code": template["admin_position_code"],
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=slug,
        tenant_name="Member Provision Test",
        industry_template_key="generic_warehouse",
        username=username,
        display_name="Member Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"users.manage", "settings.manage"}),
    )


def _position(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        return dict(
            session.execute(
                text(
                    """
                    SELECT position.position_code,position.name,
                           unit.unit_code AS department_code,unit.name AS department_name
                    FROM iam.position_profiles AS position
                    JOIN iam.organizational_units AS unit
                      ON unit.unit_code=position.department_code
                    WHERE position.active AND unit.active
                    ORDER BY position.role_level DESC,position.position_code
                    LIMIT 1
                    """
                )
            ).mappings().one()
        )


def test_member_single_batch_login_alias_and_role_round_trip() -> None:
    actor = _actor()
    position = _position(actor)
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    password = "MemberTemp-123"
    username = f"created-{uuid4().hex[:10]}@example.test"
    try:
        created_response = client.post(
            "/api/users/create",
            json={
                "username": username,
                "password": password,
                "display_name": "Created Member",
                "department": position["department_name"],
                "position": position["name"],
            },
            headers={"X-Warehouse-Execution-Origin": "auto_runtime"},
        )
        assert created_response.status_code == 200, created_response.text
        created = created_response.json()
        assert created["effect_verified"] is True
        assert created["readback_verified"] is True
        assert created["member"]["position"]["position_code"] == position["position_code"]
        assert created["member"]["department"]["unit_code"] == position["department_code"]
        assert "password" not in str(created).lower()

        with system_session() as session:
            password_hash = session.execute(
                text("SELECT password_hash FROM iam.users WHERE username=:username"),
                {"username": username},
            ).scalar_one()
        assert password_hash != password
        assert verify_password(password, password_hash)

        login = client.post(
            "/api/auth/login",
            json={"username": username, "password": password, "tenant": actor.tenant_slug},
        )
        assert login.status_code == 200, login.text
        assert login.json()["tenant"] == actor.tenant_slug

        resolved = client.post(
            "/api/data/v2/resolve",
            json={"resource": "org:member", "ref": username},
        )
        assert resolved.status_code == 200, resolved.text
        assert resolved.json()["resource"] == "iam.member"
        assert resolved.json()["data"]["position_code"] == position["position_code"]

        batch_id = uuid4().hex
        batch_payload = {
            "request_id": f"member-batch-{batch_id}",
            "members": [
                {
                    "username": f"batch-a-{batch_id}@example.test",
                    "password": "BatchTemp-123",
                    "display_name": "Batch A",
                    "department": position["department_code"],
                    "position": position["position_code"],
                },
                {
                    "username": f"batch-b-{batch_id}@example.test",
                    "password": "BatchTemp-456",
                    "display_name": "Batch B",
                    "department": position["department_code"],
                    "position": position["position_code"],
                },
            ],
        }
        imported = client.post("/api/users/import", json=batch_payload)
        assert imported.status_code == 200, imported.text
        assert imported.json()["created_count"] == 2
        replayed = client.post("/api/users/import", json=batch_payload)
        assert replayed.status_code == 200, replayed.text
        assert replayed.json()["idempotent_replay"] is True

        rollback_username = f"rollback-{uuid4().hex[:10]}@example.test"
        rejected = client.post(
            "/api/users/import",
            json={
                "members": [
                    {
                        "username": rollback_username,
                        "password": "Rollback-123",
                        "display_name": "Must Roll Back",
                        "position": position["position_code"],
                    },
                    {
                        "username": f"invalid-{uuid4().hex[:10]}@example.test",
                        "password": "Rollback-456",
                        "display_name": "Invalid Position",
                        "position": "position-does-not-exist",
                    },
                ]
            },
        )
        assert rejected.status_code == 404
        with system_session() as session:
            assert (
                session.execute(
                    text("SELECT 1 FROM iam.users WHERE username=:username"),
                    {"username": rollback_username},
                ).scalar_one_or_none()
                is None
            )

        role_name = f"Test Role {uuid4().hex[:8]}"
        role_key = f"test_role_{uuid4().hex[:10]}"
        role_response = client.post(
            "/api/roles",
            json={
                "name": role_name,
                "role_key": role_key,
                "level": 4,
                "permissions": ["inventory.read"],
            },
        )
        assert role_response.status_code == 200, role_response.text
        role = role_response.json()["role"]
        assert role["role_key"] == role_key
        assert role["permissions"] == ["inventory.read"]
        updated = client.post(
            f"/api/roles/{role_key}",
            json={"level": 5, "permissions": ["inventory.read", "inventory.adjust"]},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["role"]["level"] == 5
        assert updated.json()["role"]["permissions"] == [
            "inventory.adjust",
            "inventory.read",
        ]
        retained = execute_retained_capability(
            "role_update",
            actor,
            {
                "path.id": role_key,
                "body.level": 6,
                "body.permissions": ["inventory.read"],
            },
            origin="auto_runtime",
            confirmation_mode="passkey",
        )
        assert retained["effect_verified"] is True
        assert retained["role"]["level"] == 6
        with tenant_session(actor.tenant_id) as session:
            assert session.execute(
                text(
                    """
                    SELECT count(*) FROM business.events
                    WHERE tool_name='role_update' AND entity_key=:role_id
                    """
                ),
                {"role_id": role["id"]},
            ).scalar_one() >= 1
    finally:
        app.dependency_overrides.pop(current_actor, None)
