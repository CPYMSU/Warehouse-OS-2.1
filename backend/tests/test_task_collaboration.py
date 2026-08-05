from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app

COLLABORATION_CONTRACTS = {
    ("get", "/api/task-collaboration/discover"),
    ("get", "/api/tasks/{task_id}/collaboration"),
    ("post", "/api/tasks/{task_id}/collaboration/open"),
    ("post", "/api/tasks/{task_id}/collaboration/join"),
    ("post", "/api/tasks/{task_id}/collaboration/leave"),
    ("post", "/api/tasks/{task_id}/collaboration/invite"),
    ("post", "/api/tasks/{task_id}/collaboration/requests/{request_id}/decision"),
    (
        "post",
        "/api/tasks/{task_id}/collaboration/invitations/{invitation_id}/respond",
    ),
    ("post", "/api/tasks/{task_id}/collaboration/owner/transfer"),
    ("get", "/api/tasks/{task_id}/collaboration/messages"),
    ("post", "/api/tasks/{task_id}/collaboration/messages"),
    ("post", "/api/tasks/{task_id}/collaboration/read"),
    ("post", "/api/tasks/{task_id}/collaboration/presence"),
    ("get", "/api/tasks/{task_id}/collaboration/events"),
    ("get", "/api/tasks/{task_id}/collaboration/document"),
    ("post", "/api/tasks/{task_id}/collaboration/document/updates"),
    ("post", "/api/tasks/{task_id}/collaboration/document/images"),
    ("get", "/api/tasks/{task_id}/collaboration/document/images/{asset_key}"),
    ("get", "/api/tasks/{task_id}/collaboration/document/export"),
}


def test_task_collaboration_contracts_are_native_and_authenticated() -> None:
    paths = app.openapi()["paths"]
    assert [
        f"{method.upper()} {path}"
        for method, path in sorted(COLLABORATION_CONTRACTS)
        if method not in paths.get(path, {})
    ] == []

    response = TestClient(app).get(f"/api/tasks/{uuid4()}/collaboration")
    assert response.status_code == 401
    assert response.headers["X-Warehouse-Backend"] == "fastapi-postgresql"


def _tenant_actor(label: str, role_level: int = 10) -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"task-collab-{label}-{tenant_id.hex[:8]}"
    username = f"task-collab-{label}-{user_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug, "name": f"Task Collaboration {label}"},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "display_name": f"Task Owner {label}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, role_level, topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :role_level, :role_level, 'Owner'
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "role_level": role_level,
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=slug,
        tenant_name=f"Task Collaboration {label}",
        industry_template_key="generic_warehouse",
        username=username,
        display_name=f"Task Owner {label}",
        role_level=role_level,
        topology_level=role_level,
        topology_title="Owner",
        permissions=frozenset({"tasks.read", "tasks.create", "tasks.manage"}),
    )


def _tenant_member(owner: ActorContext) -> ActorContext:
    user_id = uuid4()
    username = f"task-member-{user_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, 'Task Member', :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(owner.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, role_level, topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, 5, 5, 'Member'
                )
                """
            ),
            {
                "tenant_id": owner.tenant_id,
                "user_id": user_id,
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=owner.tenant_id,
        tenant_slug=owner.tenant_slug,
        tenant_name=owner.tenant_name,
        industry_template_key=owner.industry_template_key,
        username=username,
        display_name="Task Member",
        role_level=5,
        topology_level=5,
        topology_title="Member",
        permissions=frozenset({"tasks.read"}),
    )


@pytest.mark.integration
def test_task_workspace_join_chat_history_and_tenant_isolation() -> None:
    owner = _tenant_actor("owner")
    member = _tenant_member(owner)
    outsider = _tenant_actor("outsider")
    active_actor = owner
    app.dependency_overrides[current_actor] = lambda: active_actor
    client = TestClient(app)
    try:
        created_response = client.post(
            "/api/tasks",
            json={
                "title": "Versioned collaboration task",
                "visibility": "company",
                "assignees": [str(owner.user_id)],
            },
        )
        assert created_response.status_code == 201
        task = created_response.json()
        task_id = task["id"]
        assert task["can_update"] is True
        assert task["can_delete"] is True
        assert task["can_status"] is True
        assert task["capabilities"] == {
            "can_update": True,
            "can_change_status": True,
            "can_delete": True,
            "can_reopen": False,
        }

        opened = client.post(
            f"/api/tasks/{task_id}/collaboration/open",
            json={"discoverability": "company", "join_policy": "open"},
        )
        assert opened.status_code == 201
        assert opened.json()["capabilities"]["can_manage"] is True
        assert opened.json()["capabilities"]["can_use_document"] is True

        document = client.get(f"/api/tasks/{task_id}/collaboration/document")
        assert document.status_code == 200
        assert document.json()["snapshot"] == {"format": "rga-v1", "nodes": []}
        draft_update = {
            "client_id": "integration-client",
            "client_update_id": "integration-update-1",
            "ops": [
                {
                    "type": "insert",
                    "id": "integration:1",
                    "after": "^",
                    "value": "稿",
                    "clock": 1,
                }
            ],
        }
        updated_document = client.post(
            f"/api/tasks/{task_id}/collaboration/document/updates",
            json=draft_update,
        )
        assert updated_document.status_code == 200
        assert updated_document.json()["content"] == "稿"
        replay = client.post(
            f"/api/tasks/{task_id}/collaboration/document/updates",
            json=draft_update,
        )
        assert replay.status_code == 200
        assert replay.json()["idempotent"] is True
        assert client.post(
            f"/api/tasks/{task_id}/collaboration/presence",
            json={"client_id": "integration-client", "state": "active", "typing": True},
        ).status_code == 200

        active_actor = member
        discovered = client.get("/api/task-collaboration/discover")
        assert discovered.status_code == 200
        assert [item["task_id"] for item in discovered.json()["items"]] == [task_id]

        joined = client.post(
            f"/api/tasks/{task_id}/collaboration/join",
            json={"role": "contributor"},
        )
        assert joined.status_code == 200
        assert joined.json()["relation"] == "member"

        sent = client.post(
            f"/api/tasks/{task_id}/collaboration/messages",
            json={"body": "The durable workspace is connected.", "client_message_id": "test-1"},
        )
        assert sent.status_code == 201
        message_id = sent.json()["message"]["id"]
        assert (
            client.post(
                f"/api/tasks/{task_id}/collaboration/read", json={"message_id": message_id}
            ).status_code
            == 200
        )
        assert (
            client.get(f"/api/tasks/{task_id}/collaboration/messages").json()["items"][0]["body"]
            == "The durable workspace is connected."
        )

        active_actor = owner
        updated = client.post(
            f"/api/tasks/{task_id}/status",
            json={"status": "in_progress", "expected_version": task["version"]},
        )
        assert updated.status_code == 200
        history = client.get(f"/api/tasks/{task_id}/history").json()["items"]
        assert [event["event_type"] for event in history[:2]] == [
            "status_changed",
            "created",
        ]

        active_actor = outsider
        assert client.get("/api/task-collaboration/discover").json()["items"] == []
        assert client.get(f"/api/tasks/{task_id}/collaboration").status_code == 404

        active_actor = owner
        edited = client.patch(
            f"/api/tasks/{task_id}",
            json={
                "expected_version": updated.json()["version"],
                "title": "Edited collaboration event",
                "kind": "event",
                "category": "meeting",
                "start_at": "2026-08-05T09:00:00+08:00",
                "end_at": "2026-08-05T10:30:00+08:00",
                "due_at": None,
            },
        )
        assert edited.status_code == 200
        assert edited.json()["title"] == "Edited collaboration event"
        assert edited.json()["kind"] == "event"
        assert edited.json()["category"] == "meeting"

        unconfirmed = client.request(
            "DELETE",
            f"/api/tasks/{task_id}",
            json={"expected_version": edited.json()["version"]},
        )
        assert unconfirmed.status_code == 422
        deleted = client.request(
            "DELETE",
            f"/api/tasks/{task_id}",
            json={"expected_version": edited.json()["version"], "confirm": True},
        )
        assert deleted.status_code == 200
        assert deleted.json()["deleted"] is True
        assert deleted.json()["collaboration_removed"] is True
        assert client.get(f"/api/tasks/{task_id}").status_code == 404
        assert client.get(f"/api/tasks/{task_id}/collaboration").status_code == 404
    finally:
        app.dependency_overrides.clear()
