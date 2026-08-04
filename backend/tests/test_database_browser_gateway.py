from __future__ import annotations

from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.templates import provision_tenant_template

pytestmark = pytest.mark.integration


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"browser-db-{tenant_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id,slug,name,industry_template_key)
                VALUES (:id,:slug,'Browser Database Test','generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id,username,display_name,password_hash)
                VALUES (:id,:username,'Database Owner',:password_hash)
                """
            ),
            {
                "id": user_id,
                "username": f"database-owner-{user_id.hex[:8]}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        template = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name="Browser Database Test",
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
        tenant_name="Browser Database Test",
        industry_template_key="generic_warehouse",
        username="database-owner",
        display_name="Database Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"assets.read", "assets.manage"}),
    )


def test_standalone_database_browser_gateway_owner_isolation_and_revocation() -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    origin = "https://example.github.io"
    try:
        created_response = client.post(
            "/api/database-projects",
            json={
                "name": "GitHub Pages Tasks",
                "workspace_key": f"github-tasks-{actor.tenant_id.hex[:8]}",
                "allowed_origins": [origin],
                "browser_access": {
                    "rules": {
                        "default": {"read": "deny", "write": "deny"},
                        "collections": {
                            "tasks": {"read": "owner", "write": "owner"},
                            "announcements": {"read": "session", "write": "deny"},
                        },
                    },
                    "rate_limit_per_minute": 100,
                },
            },
        )
        assert created_response.status_code == 201, created_response.text
        created = created_response.json()
        assert created["service_kind"] == "standalone_database"
        assert created["runtime_required"] is False
        assert created["runtime_deployed"] is False
        assert created["database"]["status"] == "ready"
        project = created["browser_project"]
        project_key = project["project_key"]
        assert project_key.startswith("dbp_")
        assert project["workspace_key_exposed"] is False
        assert project["database_credentials_exposed"] is False
        assert "api_key" not in created
        base = f"/api/database-gateway/v1/projects/{project_key}"
        workspace_key = created["workspace"]["workspace_key"]

        inventory_response = client.get("/api/database-projects")
        assert inventory_response.status_code == 200, inventory_response.text
        inventory = inventory_response.json()
        listed = next(
            item
            for item in inventory["projects"]
            if item["workspace"]["workspace_key"] == workspace_key
        )
        assert listed["service_kind"] == "standalone_database"
        assert listed["browser_project"]["project_key"] == project_key
        assert listed["database"]["credentials_exposed"] is False

        onboarding_response = client.get(
            f"/api/workspaces/{workspace_key}/database/onboarding"
        )
        assert onboarding_response.status_code == 200, onboarding_response.text
        onboarding = onboarding_response.json()
        assert onboarding["keys"]["public_project_key"] == project_key
        assert onboarding["keys"]["workspace_api_key"]["plaintext_in_ai_chat"] is False
        assert onboarding["keys"]["database_password"]["exposed"] is False
        assert onboarding["files"][0]["url"].endswith("/api/database-gateway/v1/sdk.js")
        assert "createWarehouseDataClient" in onboarding["quickstart"]

        reader = replace(
            actor,
            role_level=1,
            topology_level=1,
            permissions=frozenset({"assets.read"}),
        )
        app.dependency_overrides[current_actor] = lambda: reader
        assert client.get("/api/database-projects").status_code == 200
        assert (
            client.get(
                f"/api/workspaces/{workspace_key}/database/browser-access"
            ).status_code
            == 200
        )
        assert (
            client.get(
                f"/api/workspaces/{workspace_key}/database/onboarding"
            ).status_code
            == 200
        )
        assert (
            client.put(
                f"/api/workspaces/{workspace_key}/database/browser-access",
                json={"enabled": False},
            ).status_code
            == 403
        )
        app.dependency_overrides[current_actor] = lambda: actor

        secretary_response = client.post(
            "/api/ai/tools/digital_market_database_onboarding/execute",
            json={"arguments": {"workspace": workspace_key}},
        )
        assert secretary_response.status_code == 200, secretary_response.text
        secretary = secretary_response.json()
        assert secretary["status"] == "succeeded"
        assert secretary["data"]["keys"]["public_project_key"] == project_key
        assert "credentials" not in secretary

        create_proposal = client.post(
            "/api/ai/tools/digital_market_database_project_create/execute",
            json={"arguments": {"name": "Secretary confirmation probe"}},
        )
        assert create_proposal.status_code == 200, create_proposal.text
        assert create_proposal.json()["status"] == "confirmation_required"

        preflight = client.options(
            f"{base}/data/tasks",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert preflight.status_code == 204
        assert preflight.headers["access-control-allow-origin"] == origin
        assert "Authorization" in preflight.headers["access-control-allow-headers"]
        assert (
            client.options(
                f"{base}/data/tasks",
                headers={"Origin": "https://attacker.example"},
            ).status_code
            == 403
        )

        first_session_response = client.post(f"{base}/sessions", headers={"Origin": origin})
        assert first_session_response.status_code == 200, first_session_response.text
        first_session = first_session_response.json()
        assert first_session["access_token"].startswith("wdb_")
        assert first_session["refresh_token"].startswith("wdr_")
        assert "wak_" not in str(first_session)
        first_headers = {
            "Origin": origin,
            "Authorization": f"Bearer {first_session['access_token']}",
        }

        inserted = client.put(
            f"{base}/data/tasks/task-1",
            json={"data": {"title": "Ship from GitHub Pages"}},
            headers=first_headers,
        )
        assert inserted.status_code == 200, inserted.text
        record = inserted.json()["record"]
        assert record["data"]["owner_id"] == first_session["subject"]
        assert client.get(f"{base}/data/tasks/task-1", headers=first_headers).status_code == 200

        second_session = client.post(f"{base}/sessions", headers={"Origin": origin}).json()
        second_headers = {
            "Origin": origin,
            "Authorization": f"Bearer {second_session['access_token']}",
        }
        isolated = client.get(f"{base}/data/tasks", headers=second_headers)
        assert isolated.status_code == 200
        assert isolated.json()["count"] == 0
        assert (
            client.put(
                f"{base}/data/tasks/task-1",
                json={"data": {"title": "Take over"}},
                headers=second_headers,
            ).status_code
            == 403
        )

        refreshed_response = client.post(
            f"{base}/sessions",
            json={"refresh_token": first_session["refresh_token"]},
            headers={"Origin": origin},
        )
        assert refreshed_response.status_code == 200
        refreshed = refreshed_response.json()
        assert refreshed["subject"] == first_session["subject"]
        assert refreshed["refresh_token"] != first_session["refresh_token"]
        assert (
            client.post(
                f"{base}/sessions",
                json={"refresh_token": first_session["refresh_token"]},
                headers={"Origin": origin},
            ).status_code
            == 401
        )

        updated = client.put(
            f"/api/workspaces/{workspace_key}/database/browser-access",
            json={
                "enabled": True,
                "allowed_origins": [origin],
                "rules": project["rules"],
            },
        )
        assert updated.status_code == 200
        assert updated.json()["project"]["revision"] == project["revision"] + 1
        stale_headers = {
            "Origin": origin,
            "Authorization": f"Bearer {refreshed['access_token']}",
        }
        assert client.get(f"{base}/data/tasks", headers=stale_headers).status_code == 401

        current_session = client.post(
            f"{base}/sessions",
            json={"refresh_token": refreshed["refresh_token"]},
            headers={"Origin": origin},
        )
        assert current_session.status_code == 200
        current_headers = {
            "Origin": origin,
            "Authorization": f"Bearer {current_session.json()['access_token']}",
        }
        deleted = client.delete(f"{base}/data/tasks/task-1", headers=current_headers)
        assert deleted.status_code == 200

        disabled = client.put(
            f"/api/workspaces/{workspace_key}/database/browser-access",
            json={"enabled": False},
        )
        assert disabled.status_code == 200
        assert client.post(f"{base}/sessions", headers={"Origin": origin}).status_code == 403

        sdk = client.get("/api/database-gateway/v1/sdk.js")
        assert sdk.status_code == 200
        assert sdk.headers["access-control-allow-origin"] == "*"
        assert "createWarehouseDataClient" in sdk.text
        assert "wak_" in sdk.text
        assert "Authorization: `Bearer ${token}`" in sdk.text
    finally:
        app.dependency_overrides.clear()
