from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.templates import provision_tenant_template


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"test-{tenant_id.hex[:12]}"
    username = f"owner-{user_id.hex[:12]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, 'Full Stack Test', 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash, is_platform_owner)
                VALUES (:id, :username, 'Test Owner', :password_hash, true)
                """
            ),
            {"id": user_id, "username": username, "password_hash": hash_password("test-password")},
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name="Full Stack Test",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level, topology_level, topology_title
                ) VALUES (:tenant_id, :user_id, :position_code, 10, 10, 'Owner')
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "position_code": provisioned["admin_position_code"],
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=slug,
        tenant_name="Full Stack Test",
        industry_template_key="generic_warehouse",
        username=username,
        display_name="Test Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"settings.manage", "records.manage", "cases.manage"}),
    )


def test_identity_settings_cases_records_and_files_round_trip() -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        response = client.post(
            "/api/account/profile",
            json={
                "profile": {
                    "display_name": "Connected Owner",
                    "bio": "Full-stack PostgreSQL test",
                    "contact": {"email": "owner@example.test"},
                },
                "expected_revision": 0,
            },
        )
        assert response.status_code == 200
        assert response.json()["profile"]["display_name"] == "Connected Owner"

        response = client.post(
            "/api/runtime/preferences/appearance",
            json={"appearance": {"preset_id": "basel_cobalt", "accent_color": "#0757A6"}},
        )
        assert response.status_code == 200
        assert response.json()["appearance"]["preset_id"] == "basel_cobalt"
        assert client.get("/api/runtime/preferences").json()["appearance"]["accent_color"] == "#0757A6"

        response = client.post(
            "/api/integrations/deepseek/save",
            json={"api_key": "test-key", "model": "test-model"},
        )
        assert response.status_code == 200
        assert response.json()["deepseek"]["configured"] is True
        assert client.get("/api/integrations/deepseek").json()["deepseek"]["model"] == "test-model"

        response = client.post(
            "/api/cases",
            json={"title": "Connected case", "description": "Database round trip"},
        )
        assert response.status_code == 201
        case_id = response.json()["case"]["id"]
        assert client.post("/api/cases/search", json={"query": "Connected"}).json()["total"] == 1

        response = client.post(
            f"/api/cases/{case_id}/attachments",
            data={"field_key": "evidence"},
            files={"file": ("evidence.txt", b"case evidence", "text/plain")},
        )
        assert response.status_code == 200
        attachment_id = response.json()["attachment"]["id"]
        download = client.get(f"/api/cases/{case_id}/attachments/{attachment_id}")
        assert download.status_code == 200
        assert download.content == b"case evidence"

        response = client.post(
            "/api/records",
            json={"title": "Connected record", "type_key": "general_record"},
        )
        assert response.status_code == 201
        record_id = response.json()["record"]["id"]
        assert client.post("/api/records/search", json={"query": "Connected"}).json()["total"] == 1

        response = client.post(
            f"/api/records/{record_id}/documents",
            data={"field_key": "document", "title": "Primary file", "visibility": "record"},
            files={"file": ("record.txt", b"record document", "text/plain")},
        )
        assert response.status_code == 200
        version_id = response.json()["version"]["version_id"]
        download = client.get(f"/api/records/{record_id}/documents/{version_id}/download")
        assert download.status_code == 200
        assert download.content == b"record document"

        response = client.post(
            "/api/ai/conversations",
            json={"title": "Connected conversation", "channel": "assistant"},
        )
        assert response.status_code == 201
        assert response.json()["conversation"]["title"] == "Connected conversation"
    finally:
        app.dependency_overrides.clear()
