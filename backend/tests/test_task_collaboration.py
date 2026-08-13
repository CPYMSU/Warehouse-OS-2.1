from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.task_collaboration_realtime import _position_payload

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
    ("get", "/api/tasks/{task_id}/collaboration/position"),
    ("get", "/api/tasks/{task_id}/collaboration/annotations"),
    ("post", "/api/tasks/{task_id}/collaboration/annotations"),
    ("post", "/api/tasks/{task_id}/collaboration/review-changes"),
    (
        "post",
        "/api/tasks/{task_id}/collaboration/review-changes/{annotation_id}/accept",
    ),
    (
        "post",
        "/api/tasks/{task_id}/collaboration/review-changes/{annotation_id}/reject",
    ),
    (
        "post",
        "/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/messages",
    ),
    (
        "post",
        "/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/status",
    ),
    ("get", "/api/tasks/{task_id}/collaboration/events"),
    ("get", "/api/tasks/{task_id}/collaboration/document"),
    ("post", "/api/tasks/{task_id}/collaboration/document/updates"),
    ("post", "/api/tasks/{task_id}/collaboration/document/images"),
    ("get", "/api/tasks/{task_id}/collaboration/document/images/{asset_key}"),
    ("get", "/api/tasks/{task_id}/collaboration/document/export"),
}


def test_task_collaboration_position_contract_is_bounded() -> None:
    position = {
        "format": "document-cursor-v1",
        "mode": "visual",
        "cursor_start": 8,
        "cursor_end": 12,
        "line_index": 2,
        "scroll_top": 420,
        "document_sequence": 7,
        "active": True,
        "start_anchor": {
            "left_id": "client:7",
            "right_id": "client:8",
            "affinity": "forward",
            "fallback": 8,
        },
        "end_anchor": None,
    }
    assert _position_payload(position) == position
    with pytest.raises(HTTPException, match="cursor range"):
        _position_payload({**position, "cursor_start": 13})
    with pytest.raises(HTTPException, match="position"):
        _position_payload({**position, "selected_text": "must never leave the editor"})
    assert _position_payload(
        {
            **position,
            "cursor_start": 100_000,
            "cursor_end": 100_000,
            "line_index": 100_000,
        }
    )["cursor_end"] == 100_000
    with pytest.raises(HTTPException, match="cursor end"):
        _position_payload({**position, "cursor_end": 100_001})


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
        assert document.json()["sync"]["mode"] == "snapshot"
        document_id = document.json()["document"]["id"]
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
        delta = client.get(
            f"/api/tasks/{task_id}/collaboration/document",
            params={"after_sequence": 0, "document_id": document_id},
        )
        assert delta.status_code == 200
        assert delta.json()["sync"]["mode"] == "delta"
        assert delta.json()["sync"]["base_sequence"] == 0
        assert delta.json()["sync"]["latest_sequence"] == 1
        assert delta.json()["sync"]["updates"][0]["payload"]["ops"] == draft_update["ops"]
        assert "snapshot" not in delta.json()
        assert "content" not in delta.json()
        current = client.get(
            f"/api/tasks/{task_id}/collaboration/document",
            params={"after_sequence": 1, "document_id": document_id},
        )
        assert current.status_code == 200
        assert current.json()["sync"]["mode"] == "current"
        assert current.json()["sync"]["updates"] == []
        assert "snapshot" not in current.json()
        reset = client.get(
            f"/api/tasks/{task_id}/collaboration/document",
            params={"after_sequence": 2, "document_id": document_id},
        )
        assert reset.status_code == 200
        assert reset.json()["sync"]["mode"] == "reset"
        assert reset.json()["sync"]["reason"] == "client_ahead"
        assert reset.json()["content"] == "稿"
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

        member_position = {
            "format": "document-cursor-v1",
            "mode": "visual",
            "cursor_start": 1,
            "cursor_end": 1,
            "line_index": 0,
            "scroll_top": 88,
            "document_sequence": 1,
            "active": True,
            "start_anchor": {
                "left_id": "integration:1",
                "right_id": None,
                "affinity": "backward",
                "fallback": 1,
            },
            "end_anchor": {
                "left_id": "integration:1",
                "right_id": None,
                "affinity": "backward",
                "fallback": 1,
            },
        }
        member_presence = client.post(
            f"/api/tasks/{task_id}/collaboration/presence",
            json={
                "client_id": "member-editor",
                "state": "active",
                "typing": False,
                "position": member_position,
                "persist_position": True,
            },
        )
        assert member_presence.status_code == 200
        resumed = client.get(f"/api/tasks/{task_id}/collaboration/position")
        assert resumed.status_code == 200
        assert resumed.json()["position"]["cursor_start"] == 1
        assert resumed.json()["position"]["scroll_top"] == 88

        annotation_response = client.post(
            f"/api/tasks/{task_id}/collaboration/annotations",
            json={
                "client_annotation_id": "member-note-1",
                "client_message_id": "member-note-message-1",
                "start_anchor": {
                    "left_id": "^",
                    "right_id": "integration:1",
                    "affinity": "forward",
                    "fallback": 0,
                },
                "end_anchor": {
                    "left_id": "integration:1",
                    "right_id": None,
                    "affinity": "backward",
                    "fallback": 1,
                },
                "start_offset": 0,
                "end_offset": 1,
                "document_sequence": 1,
                "quote": "稿",
                "body": "Should this term be more specific?",
            },
        )
        assert annotation_response.status_code == 201
        annotation_id = annotation_response.json()["annotation"]["id"]
        replayed_annotation = client.post(
            f"/api/tasks/{task_id}/collaboration/annotations",
            json={
                "client_annotation_id": "member-note-1",
                "client_message_id": "member-note-message-1",
                "start_anchor": {
                    "left_id": "^",
                    "right_id": "integration:1",
                    "affinity": "forward",
                    "fallback": 0,
                },
                "end_anchor": {
                    "left_id": "integration:1",
                    "right_id": None,
                    "affinity": "backward",
                    "fallback": 1,
                },
                "start_offset": 0,
                "end_offset": 1,
                "document_sequence": 1,
                "quote": "稿",
                "body": "Should this term be more specific?",
            },
        )
        assert replayed_annotation.status_code == 201
        assert replayed_annotation.json()["result"] == "idempotent"
        review_response = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes",
            json={
                "client_annotation_id": "member-review-1",
                "client_message_id": "member-review-message-1",
                "start_anchor": {
                    "left_id": "^",
                    "right_id": "integration:1",
                    "affinity": "forward",
                    "fallback": 0,
                },
                "end_anchor": {
                    "left_id": "integration:1",
                    "right_id": None,
                    "affinity": "backward",
                    "fallback": 1,
                },
                "start_offset": 0,
                "end_offset": 1,
                "document_sequence": 1,
                "quote": "稿",
                "proposed_text": "文稿",
                "body": "Expand this term.",
            },
        )
        assert review_response.status_code == 201
        review_id = review_response.json()["annotation"]["id"]
        assert review_response.json()["annotation"]["review_state"] == "pending"
        assert review_response.json()["annotation"]["can_accept"] is False

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
        owner_presence = client.post(
            f"/api/tasks/{task_id}/collaboration/presence",
            json={"client_id": "owner-editor", "state": "active", "typing": False},
        )
        assert owner_presence.status_code == 200
        visible_member = next(
            item
            for item in owner_presence.json()["presence"]
            if item["user_id"] == str(member.user_id)
        )
        assert visible_member["position"]["line_index"] == 0
        annotation_list = client.get(
            f"/api/tasks/{task_id}/collaboration/annotations"
        )
        assert annotation_list.status_code == 200
        assert annotation_list.json()["items"][0]["quote"] == "稿"
        assert annotation_list.json()["items"][0]["messages"][0]["author_name"] == "Task Member"
        reply = client.post(
            f"/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/messages",
            json={"client_message_id": "owner-reply-1", "body": "Yes, please clarify it."},
        )
        assert reply.status_code == 201
        assert len(reply.json()["annotation"]["messages"]) == 2
        resolved = client.post(
            f"/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/status",
            json={"status": "resolved"},
        )
        assert resolved.status_code == 200
        assert resolved.json()["annotation"]["status"] == "resolved"
        reopened = client.post(
            f"/api/tasks/{task_id}/collaboration/annotations/{annotation_id}/status",
            json={"status": "open"},
        )
        assert reopened.status_code == 200
        assert reopened.json()["annotation"]["status"] == "open"
        assert reopened.json()["annotation"]["resolved_at"] is None
        open_annotations = client.get(
            f"/api/tasks/{task_id}/collaboration/annotations?status=open"
        )
        assert open_annotations.status_code == 200
        assert annotation_id in {item["id"] for item in open_annotations.json()["items"]}
        accepted = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes/{review_id}/accept"
        )
        assert accepted.status_code == 200
        assert accepted.json()["annotation"]["review_state"] == "accepted"
        assert accepted.json()["annotation"]["status"] == "resolved"
        assert accepted.json()["annotation"]["accepted_sequence"] == 2
        assert client.get(
            f"/api/tasks/{task_id}/collaboration/document"
        ).json()["content"] == "文稿"
        accepted_replay = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes/{review_id}/accept"
        )
        assert accepted_replay.status_code == 200
        assert accepted_replay.json()["result"] == "idempotent"

        first_review_node = f"review-{review_id.replace('-', '')}:0"
        second_review_node = f"review-{review_id.replace('-', '')}:1"
        conflicted_review = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes",
            json={
                "client_annotation_id": "owner-review-conflict-1",
                "client_message_id": "owner-review-conflict-message-1",
                "start_anchor": {
                    "left_id": "^",
                    "right_id": first_review_node,
                    "affinity": "forward",
                    "fallback": 0,
                },
                "end_anchor": {
                    "left_id": first_review_node,
                    "right_id": second_review_node,
                    "affinity": "backward",
                    "fallback": 1,
                },
                "start_offset": 0,
                "end_offset": 1,
                "document_sequence": 2,
                "quote": "文",
                "proposed_text": "新",
                "body": "This proposal will encounter a concurrent edit.",
            },
        )
        assert conflicted_review.status_code == 201
        conflicted_review_id = conflicted_review.json()["annotation"]["id"]
        concurrent_update = client.post(
            f"/api/tasks/{task_id}/collaboration/document/updates",
            json={
                "client_id": "owner-editor",
                "client_update_id": "owner-conflict-change-1",
                "ops": [
                    {"type": "delete", "id": first_review_node},
                    {
                        "type": "insert",
                        "id": "owner-conflict:1",
                        "after": "^",
                        "value": "改",
                        "clock": 4,
                    },
                ],
            },
        )
        assert concurrent_update.status_code == 200
        conflict = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes/{conflicted_review_id}/accept"
        )
        assert conflict.status_code == 409
        assert conflict.json()["detail"]["reason"] == "source_changed"
        review_items = client.get(
            f"/api/tasks/{task_id}/collaboration/annotations?status=all"
        ).json()["items"]
        conflicted_item = next(
            item for item in review_items if item["id"] == conflicted_review_id
        )
        assert conflicted_item["review_state"] == "conflicted"
        rejected = client.post(
            f"/api/tasks/{task_id}/collaboration/review-changes/{conflicted_review_id}/reject"
        )
        assert rejected.status_code == 200
        assert rejected.json()["annotation"]["review_state"] == "rejected"
        assert client.get(
            f"/api/tasks/{task_id}/collaboration/document"
        ).json()["content"] == "改稿"
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
        assert client.get(f"/api/tasks/{task_id}/collaboration/position").status_code == 404
        assert client.get(f"/api/tasks/{task_id}/collaboration/annotations").status_code == 404

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
