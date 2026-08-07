from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import CredentialDeviceType

from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password, verify_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services import auto_runtime
from app.services.legacy_capability_runtime import execute_retained_capability
from app.services.templates import provision_tenant_template
from app.terminal import executor
from app.terminal.store import (
    COMMAND_EXECUTION_ORIGINS,
    COMMAND_EXECUTION_STATUSES,
)

pytestmark = pytest.mark.integration


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


def test_identity_settings_cases_records_and_files_round_trip(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.integrations.validate_credentials",
        lambda *_args, **_kwargs: SimpleNamespace(ok=True, latency_ms=7, error=None),
    )
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
        assert (
            client.get("/api/runtime/preferences").json()["appearance"]["accent_color"] == "#0757A6"
        )

        response = client.get("/api/alerts/watch")
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["alerts"] == []

        response = client.get("/api/erp/gl/ap")
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["by_party"] == []

        response = client.get("/api/erp/gl/ar")
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["by_party"] == []

        response = client.get("/api/overview/executive")
        assert response.status_code == 200
        modules = response.json()["modules"]
        assert modules["finance"]["status"] == "ready"
        assert modules["assets"]["status"] == "ready"

        response = client.get("/api/runtime/world")
        assert response.status_code == 200
        world = response.json()
        assert world["source"] == "tenant_postgresql"
        assert world["scope"] == "permission-filtered"
        assert world["company"]["slug"] == actor.tenant_slug
        assert world["inventory"]["available"] is True

        response = client.get("/api/runtime/skills")
        assert response.status_code == 200
        skills = response.json()
        assert skills["total"] == 543
        assert skills["skills"][0]["invocation"] == "goal_guided"
        assert "api_path" not in skills["skills"][0]

        response = client.get("/api/platform/optimizer/overview?window_days=30")
        assert response.status_code == 200
        assert response.json()["feature"]["owner_only"] is True
        assert response.json()["privacy"] == {
            "aggregate_only": True,
            "raw_transcripts_exposed": False,
        }

        response = client.post(
            "/api/integrations/deepseek/save",
            json={"api_key": "test-key", "model": "test-model"},
        )
        assert response.status_code == 200
        assert response.json()["deepseek"]["configured"] is True
        assert response.json()["deepseek"]["connected"] is True
        assert "api_key" not in response.json()["deepseek"]
        assert client.get("/api/integrations/deepseek").json()["deepseek"]["model"] == "test-model"
        with tenant_session(actor.tenant_id) as session:
            stored = session.execute(
                text(
                    """
                    SELECT payload FROM compatibility.documents
                    WHERE namespace = 'integration.deepseek' AND document_key = 'default'
                    """
                )
            ).scalar_one()
        assert "api_key" not in stored
        assert str(stored["secret_ciphertext"]).startswith("fernet:v1:")

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
        records_search = client.post("/api/records/search", json={"query": "Connected"}).json()
        assert records_search["total"] == 2
        assert {item["type_key"] for item in records_search["records"]} == {
            "general_record",
            "personnel_record",
        }

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

        records_meta = client.get("/api/records/meta")
        assert records_meta.status_code == 200
        assert records_meta.json()["can_configure"] is True
        assert records_meta.json()["permissions"]["can_configure"] is True

        configuration = client.get("/api/records/config")
        assert configuration.status_code == 200
        assert configuration.json()["can_configure"] is True
        assert {item["key"] for item in configuration.json()["categories"]} >= {
            "personnel",
            "other",
        }

        category = client.post(
            "/api/records/config/categories",
            json={
                "key": "connected_archive",
                "name": "Connected archive",
                "description": "Integration-owned category",
                "icon": "box",
                "order": 70,
                "confidentiality": "internal",
                "retention": {},
            },
        )
        assert category.status_code == 201
        assert category.json()["category"]["revision_no"] == 1

        record_type = client.post(
            "/api/records/config/types",
            json={
                "key": "connected_record",
                "category_key": "connected_archive",
                "name": "Connected record type",
                "description": "Integration-owned type",
                "lifecycle_mode": "dossier",
                "confidentiality": "internal",
                "fields": [],
            },
        )
        assert record_type.status_code == 201
        assert record_type.json()["type"]["revision_no"] == 1

        revised_payload = {
            "key": "connected_record",
            "category_key": "connected_archive",
            "name": "Connected record type R2",
            "description": "Versioned without rewriting existing records",
            "lifecycle_mode": "dossier",
            "confidentiality": "internal",
            "fields": [],
            "expected_revision_no": 1,
        }
        revised = client.post(
            "/api/records/config/types/connected_record/revisions",
            json=revised_payload,
        )
        assert revised.status_code == 200
        assert revised.json()["type"]["revision_no"] == 2
        assert revised.json()["type"]["managed_by_template"] is False
        assert (
            client.post(
                "/api/records/config/types/connected_record/revisions",
                json=revised_payload,
            ).status_code
            == 409
        )
        disabled = client.post(
            "/api/records/config/types/connected_record/disable",
            json={"expected_revision_no": 2},
        )
        assert disabled.status_code == 200
        assert disabled.json()["type"]["active"] is False
        assert disabled.json()["type"]["revision_no"] == 3

        audit_logs = client.get("/api/audit/logs?limit=50")
        assert audit_logs.status_code == 200
        assert audit_logs.json()["rows"]
        assert audit_logs.json()["summary"]["total"] == len(audit_logs.json()["rows"])
        assert all("operator_name" in row for row in audit_logs.json()["rows"])

        audit_cli = client.get("/api/audit/cli?limit=50")
        assert audit_cli.status_code == 200
        assert isinstance(audit_cli.json()["rows"], list)
        assert "summary" in audit_cli.json()

        response = client.post(
            "/api/ai/conversations",
            json={"title": "Connected conversation", "channel": "assistant"},
        )
        assert response.status_code == 201
        assert response.json()["conversation"]["title"] == "Connected conversation"
        conversations = client.get("/api/ai/conversations?limit=100")
        assert conversations.status_code == 200
        assert conversations.json()["rows"]
        assert conversations.json()["rows"][0]["title"] == "Connected conversation"
    finally:
        app.dependency_overrides.clear()


def test_every_workflow_node_accepts_versioned_notarized_attachments() -> None:
    actor = _actor()
    instance_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        definition = (
            session.execute(
                text(
                    """
                SELECT id, definition
                FROM workflow.definitions
                WHERE active
                ORDER BY workflow_key, version DESC
                LIMIT 1
                """
                )
            )
            .mappings()
            .one()
        )
        node_key = str(definition["definition"]["nodes"][0]["node_key"])
        session.execute(
            text(
                """
                INSERT INTO workflow.instances(
                  id, tenant_id, definition_id, status,
                  subject_type, subject_id, state
                ) VALUES (
                  :id, :tenant_id, :definition_id, 'active',
                  'erp_purchase_request', :subject_id,
                  CAST(:state AS jsonb)
                )
                """
            ),
            {
                "id": instance_id,
                "tenant_id": actor.tenant_id,
                "definition_id": definition["id"],
                "subject_id": uuid4(),
                "state": json.dumps({"current_node_key": node_key}),
            },
        )

    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        first_content = b"%PDF-1.7\nfirst notarized workflow attachment\n"
        first = client.post(
            f"/api/wf/instances/{instance_id}/nodes/{node_key}/attachments",
            data={"kind": "node_attachment"},
            files={"file": ("採購審批.pdf", first_content, "application/pdf")},
        )
        assert first.status_code == 200
        first_attachment = first.json()["attachment"]
        assert first_attachment["version"] == 1
        assert first_attachment["notarized"] is True
        assert len(first_attachment["file_sha256"]) == 64
        assert first_attachment["file_seal"].startswith("WFN-")

        verified = client.get(first_attachment["verify_url"])
        assert verified.status_code == 200
        assert verified.json()["verified"] is True, verified.json()
        assert all(verified.json()["checks"].values())

        download = client.get(first_attachment["download_url"])
        assert download.status_code == 200
        assert download.content == first_content
        assert "filename*=UTF-8''" in download.headers["content-disposition"]

        second = client.post(
            f"/api/wf/instances/{instance_id}/nodes/{node_key}/attachments",
            data={
                "kind": "node_attachment",
                "attachment_key": first_attachment["attachment_key"],
            },
            files={
                "file": (
                    "approval-v2.docx",
                    b"PK\\x03\\x04second notarized workflow attachment",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert second.status_code == 200
        second_attachment = second.json()["attachment"]
        assert second_attachment["version"] == 2
        assert second_attachment["previous_event_hash"] == first_attachment["event_hash"]
        assert client.get(second_attachment["verify_url"]).json()["verified"] is True

        detail = client.get(f"/api/wf/instances/{instance_id}")
        assert detail.status_code == 200
        artifacts = detail.json()["artifacts"]
        assert [item["version"] for item in artifacts] == [2, 1]
        assert all(item["node_key"] == node_key for item in artifacts)

        listed = client.get(f"/api/wf/instances/{instance_id}/nodes/{node_key}/attachments")
        assert listed.status_code == 200
        assert listed.json()["count"] == 2
    finally:
        app.dependency_overrides.clear()


def test_retained_message_command_uses_canonical_evented_business_state() -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        sent = client.post(
            "/api/cli/exec",
            json={"line": 'msg send --to all --text "Capability gateway message"'},
        )
        assert sent.status_code == 200
        if sent.json()["status"] != "succeeded":
            with tenant_session(actor.tenant_id) as session:
                diagnostic = session.execute(
                    text(
                        """
                        SELECT response FROM terminal.command_executions
                        WHERE id = :id
                        """
                    ),
                    {"id": sent.json()["execution_id"]},
                ).scalar_one()
            pytest.fail(f"retained message failed: {sent.json()} audit={diagnostic}")
        assert sent.json()["ok"] is True
        assert sent.json()["data"]["transaction_committed"] is True
        assert sent.json()["data"]["readback_verified"] is True

        replay = client.post(
            "/api/cli/exec",
            json={"line": 'msg send --to all --text "Capability gateway message"'},
        )
        assert replay.json()["status"] == "succeeded"
        assert replay.json()["data"]["idempotent_replay"] is True

        inbox = client.post("/api/cli/exec", json={"line": "msg inbox"})
        assert inbox.status_code == 200
        assert inbox.json()["status"] == "succeeded"
        assert inbox.json()["data"]["messages"][0]["text"] == "Capability gateway message"
        assert inbox.json()["data"]["effect_verified"] is True

        with tenant_session(actor.tenant_id) as session:
            stored = session.execute(
                text(
                    """
                    SELECT count(*)
                    FROM compatibility.documents
                    WHERE namespace IN (
                      'capability.collab.messages', 'collaboration.message'
                    )
                      AND payload->>'text' = 'Capability gateway message'
                    """
                )
            ).scalar_one()
            canonical = session.execute(
                text(
                    """
                    SELECT count(*)
                    FROM business.entities
                    WHERE resource_type = 'collaboration.message'
                      AND payload #>> '{body,text}' = 'Capability gateway message'
                    """
                )
            ).scalar_one()
            events = session.execute(
                text(
                    """
                    SELECT count(*) FROM business.events
                    WHERE tool_name = 'msg_send'
                    """
                )
            ).scalar_one()
        assert int(stored) == 0
        assert int(canonical) == 1
        assert int(events) == 1
    finally:
        app.dependency_overrides.clear()


def test_sensitive_native_retained_mutations_have_real_readback() -> None:
    actor = _actor()
    username = f"created-{uuid4().hex[:12]}"
    created = execute_retained_capability(
        "user_add",
        actor,
        {
            "body.username": username,
            "body.password": "correct-horse-battery-staple",
            "body.display_name": "Created User",
        },
        origin="auto_runtime",
        confirmation_mode="passkey",
    )
    assert created["transaction_committed"] is True
    assert created["readback_verified"] is True
    with system_session() as session:
        login = (
            session.execute(
                text(
                    """
                    SELECT id, password_hash FROM iam.users
                    WHERE username = :username
                    """
                ),
                {"username": username},
            )
            .mappings()
            .one()
        )
    assert verify_password("correct-horse-battery-staple", login["password_hash"])
    with tenant_session(actor.tenant_id) as session:
        membership_tenant = session.execute(
            text("SELECT tenant_id FROM iam.memberships WHERE user_id = :user_id"),
            {"user_id": login["id"]},
        ).scalar_one()
    assert membership_tenant == actor.tenant_id

    category_id = uuid4()
    item_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO warehouse.item_categories(
                  id, tenant_id, category_code, name
                ) VALUES (:category_id, :tenant_id, 'RESET-TEST', 'Reset test')
                """
            ),
            {"category_id": category_id, "tenant_id": actor.tenant_id},
        )
        session.execute(
            text(
                """
                INSERT INTO warehouse.items(
                  id, tenant_id, category_id, item_code, name
                ) VALUES (:item_id, :tenant_id, :category_id, 'RESET-ITEM', 'Reset item')
                """
            ),
            {
                "category_id": category_id,
                "item_id": item_id,
                "tenant_id": actor.tenant_id,
            },
        )
    reset = execute_retained_capability(
        "inventory_reset",
        actor,
        {"body.request_id": f"reset-{uuid4()}", "body.scope": "all"},
        origin="auto_runtime",
        confirmation_mode="passkey",
    )
    assert reset["readback_verified"] is True
    with tenant_session(actor.tenant_id) as session:
        counts = (
            session.execute(
                text(
                    """
                SELECT
                  (SELECT count(*) FROM warehouse.items) AS items,
                  (SELECT count(*) FROM warehouse.item_categories
                   WHERE id = :category_id) AS preserved_category
                """
                ),
                {"category_id": category_id},
            )
            .mappings()
            .one()
        )
    assert int(counts["items"]) == 0
    assert int(counts["preserved_category"]) == 1


def test_registration_and_join_approvals_share_the_real_membership_workflow() -> None:
    base_manager = _actor()
    manager = replace(
        base_manager,
        permissions=frozenset({"users.manage", *base_manager.permissions}),
    )
    client = TestClient(app)
    app.dependency_overrides[current_actor] = lambda: manager
    try:
        registration_username = f"registration-{uuid4().hex[:12]}"
        registration = client.post(
            "/api/auth/register",
            json={
                "tenant_slug": manager.tenant_slug,
                "username": registration_username,
                "display_name": "Registration Applicant",
                "password": "registration-password",
                "reason": "Create my first company account",
            },
        )
        assert registration.status_code == 201
        registration_id = registration.json()["request_id"]

        source_tenant_id = uuid4()
        joining_user_id = uuid4()
        joining_username = f"joining-{joining_user_id.hex[:12]}"
        with system_session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                    VALUES (:id, :slug, 'Joining Source', 'generic_warehouse')
                    """
                ),
                {"id": source_tenant_id, "slug": f"source-{source_tenant_id.hex[:12]}"},
            )
            session.execute(
                text(
                    """
                    INSERT INTO iam.users(id, username, display_name, password_hash)
                    VALUES (:id, :username, 'Joining Applicant', :password_hash)
                    """
                ),
                {
                    "id": joining_user_id,
                    "username": joining_username,
                    "password_hash": hash_password("joining-password"),
                },
            )
        with tenant_session(source_tenant_id) as session:
            session.execute(
                text(
                    """
                    INSERT INTO iam.memberships(
                      tenant_id, user_id, role_level, topology_level, topology_title
                    ) VALUES (:tenant_id, :user_id, 1, 1, 'Member')
                    """
                ),
                {"tenant_id": source_tenant_id, "user_id": joining_user_id},
            )
        joining_actor = ActorContext(
            user_id=joining_user_id,
            tenant_id=source_tenant_id,
            tenant_slug=f"source-{source_tenant_id.hex[:12]}",
            tenant_name="Joining Source",
            industry_template_key="generic_warehouse",
            username=joining_username,
            display_name="Joining Applicant",
            role_level=1,
            topology_level=1,
            topology_title="Member",
        )
        app.dependency_overrides[current_actor] = lambda: joining_actor
        joined = client.post(
            "/api/companies/join",
            json={"slug": manager.tenant_slug, "reason": "Join the managed company"},
        )
        assert joined.status_code == 201
        join_id = joined.json()["request_id"]

        app.dependency_overrides[current_actor] = lambda: manager
        registrations = client.get("/api/auth/registrations?status=pending")
        joins = client.get("/api/memberships/pending?status=pending")
        assert registrations.status_code == 200
        assert joins.status_code == 200
        assert registrations.json()["available"] is True
        assert joins.json()["available"] is True
        assert [row["id"] for row in registrations.json()["requests"]] == [registration_id]
        assert [row["id"] for row in joins.json()["requests"]] == [join_id]
        assert registrations.json()["pending_count"] == 1
        assert joins.json()["pending_count"] == 1

        attacker = replace(
            joining_actor,
            role_level=10,
            topology_level=10,
            permissions=frozenset({"users.manage"}),
        )
        app.dependency_overrides[current_actor] = lambda: attacker
        hidden = client.post(f"/api/memberships/{join_id}/approve", json={})
        assert hidden.status_code == 404

        app.dependency_overrides[current_actor] = lambda: manager
        approved_join = executor.execute_confirmed_runtime_tool_call(
            manager,
            "membership_approve",
            {"id": join_id, "note": "Identity verified"},
        )
        assert approved_join["ok"] is True
        assert approved_join["status"] == "succeeded"
        assert approved_join["data"]["membership_active"] is True
        with tenant_session(manager.tenant_id) as session:
            assert (
                session.execute(
                    text(
                        """
                    SELECT active FROM iam.memberships
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                    """
                    ),
                    {"tenant_id": manager.tenant_id, "user_id": joining_user_id},
                ).scalar_one()
                is True
            )

        approved_history = client.get("/api/memberships/pending?status=approved").json()
        assert [row["id"] for row in approved_history["requests"]] == [join_id]
        assert approved_history["requests"][0]["reviewer_name"] == manager.display_name
        assert approved_history["pending_count"] == 0

        approved_registration = executor.execute_confirmed_runtime_tool_call(
            manager,
            "registration_approve",
            {"id": registration_id, "note": "Registration verified"},
        )
        assert approved_registration["ok"] is True
        assert approved_registration["status"] == "succeeded"
        assert approved_registration["data"]["membership_active"] is True
        assert approved_registration["data"]["verification"] == {
            "schema": "warehouse.domain-readback.v1",
            "verified": True,
            "source": "tenant_membership_readback",
        }
        membership_readback = approved_registration["data"]["membership"]
        assert membership_readback["active"] is True
        assert membership_readback["username"] == registration_username
        assert "position_code" in membership_readback
        assert "role_name" in membership_readback
        observation = approved_registration["data"]["world_observation"]
        assert observation["schema"] == "warehouse.world-observation.v1"
        assert observation["verified_facts"]["assignment_readback"] is True
        assert observation["related_entities"][0]["resource"] == "iam.member"
        approved_registrations = client.get("/api/auth/registrations?status=approved").json()
        assert [row["id"] for row in approved_registrations["requests"]] == [registration_id]
        assert approved_registrations["pending_count"] == 0

        idempotent_approval = executor.execute_confirmed_runtime_tool_call(
            manager,
            "registration_approve",
            {"id": registration_id, "note": "Registration verified"},
        )
        assert idempotent_approval["ok"] is True
        assert idempotent_approval["data"]["already_processed"] is True
        assert idempotent_approval["data"]["membership"] == membership_readback

        rejected_username = f"rejected-{uuid4().hex[:12]}"
        rejected_registration = client.post(
            "/api/auth/register",
            json={
                "tenant_slug": manager.tenant_slug,
                "username": rejected_username,
                "display_name": "Rejected Applicant",
                "password": "rejected-password",
            },
        )
        rejected_id = rejected_registration.json()["request_id"]
        rejected = client.post(
            f"/api/auth/registrations/{rejected_id}/reject",
            json={"note": "Incomplete information"},
        )
        assert rejected.status_code == 200
        rejected_history = client.get("/api/auth/registrations?status=rejected").json()
        assert [row["id"] for row in rejected_history["requests"]] == [rejected_id]
        assert rejected_history["requests"][0]["review_note"] == "Incomplete information"
    finally:
        app.dependency_overrides.clear()


def test_retained_first_write_profile_run_and_weather_paths_are_truthful(monkeypatch) -> None:
    actor = _actor()
    run_id = uuid4()
    warehouse_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO iam.user_profiles(user_id, profile, revision)
                VALUES (:user_id, '{"language":"zh-TW"}'::jsonb, 1)
                """
            ),
            {"user_id": actor.user_id},
        )
        session.execute(
            text(
                """
                INSERT INTO secretariat.runs(
                  id, tenant_id, actor_user_id, task, status, context_snapshot
                ) VALUES (
                  :id, :tenant_id, :actor_user_id, 'readback test',
                  'succeeded', '{}'::jsonb
                )
                """
            ),
            {
                "id": run_id,
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO warehouse.warehouses(
                  id, tenant_id, code, name, warehouse_type, lat, lng
                ) VALUES (
                  :id, :tenant_id, 'WEATHER', 'Weather location',
                  'general', 31.230400, 121.473700
                )
                """
            ),
            {"id": warehouse_id, "tenant_id": actor.tenant_id},
        )

    reset = execute_retained_capability(
        "profile_reset",
        actor,
        {},
        origin="auto_runtime",
        confirmation_mode="domain_workflow",
    )
    assert reset["profile"] == {}
    assert reset["revision"] == 2
    assert reset["readback_verified"] is True

    detail = execute_retained_capability(
        "agent_run_show",
        actor,
        {"query.id": str(run_id)},
        origin="terminal",
        confirmation_mode="direct",
    )
    assert detail["run"]["id"] == str(run_id)
    assert detail["run"]["task"] == "readback test"
    with pytest.raises(HTTPException) as rejected:
        execute_retained_capability(
            "agent_run_undo",
            actor,
            {"body.run_id": str(run_id)},
            origin="terminal",
            confirmation_mode="direct",
        )
    assert rejected.value.status_code == 409
    assert "no recorded reversible write steps" in str(rejected.value.detail)

    class _WeatherResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"current": {"temperature_2m": 28.5}}

    captured: dict[str, object] = {}

    def fake_get(_url: str, **kwargs: object) -> _WeatherResponse:
        captured.update(dict(kwargs.get("params") or {}))
        return _WeatherResponse()

    monkeypatch.setattr("app.services.legacy_capability_runtime.httpx.get", fake_get)
    weather = execute_retained_capability(
        "weather_now",
        actor,
        {},
        origin="terminal",
        confirmation_mode="direct",
    )
    assert weather["location_source"] == "warehouse.warehouses"
    assert float(captured["latitude"]) == pytest.approx(31.2304)
    assert float(captured["longitude"]) == pytest.approx(121.4737)

    posted = execute_retained_capability(
        "fin_post",
        actor,
        {
            "body.request_id": f"journal-{uuid4()}",
            "body.lines_json": json.dumps(
                [
                    {"code": "1002", "debit": 125, "credit": 0},
                    {"code": "6001", "debit": 0, "credit": 125},
                ]
            ),
        },
        origin="auto_runtime",
        confirmation_mode="domain_workflow",
    )
    assert posted["transaction_committed"] is True
    assert posted["entity"]["resource_type"] == "finance.ledger"


def test_manual_and_ai_actions_share_native_inventory_round_trip() -> None:
    actor = replace(
        _actor(),
        permissions=frozenset(
            {
                "settings.manage",
                "cli.catalog",
                "inventory.adjust",
                "inventory.inbound",
                "inventory.outbound",
            }
        ),
    )
    warehouse_id = uuid4()
    item_name = f"Shared action item {uuid4().hex[:8]}"
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO warehouse.warehouses(
                  id, tenant_id, code, name, warehouse_type
                ) VALUES (
                  :id, :tenant_id, 'DEFAULT', 'Default test warehouse', 'general'
                )
                """
            ),
            {"id": warehouse_id, "tenant_id": actor.tenant_id},
        )

    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        created = client.post(
            "/api/business/actions/item_create/execute",
            json={
                "arguments": {
                    "name": item_name,
                    "spec": "M-01",
                    "unit": "件",
                }
            },
        )
        assert created.status_code == 200
        assert created.json()["status"] == "succeeded"
        item_id = created.json()["data"]["item"]["id"]

        updated = client.post(
            "/api/ai/tools/item_update/execute",
            json={"arguments": {"id": item_id, "price": 12.5}},
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "succeeded"

        received = client.post(
            "/api/business/actions/inbound_create/execute",
            json={
                "arguments": {
                    "request-id": f"manual-in-{uuid4().hex}",
                    "item": item_name,
                    "qty": 10,
                    "type": "調撥入庫",
                    "batch": "BATCH-NATIVE-1",
                    "production-date": "2026-07-01",
                    "shelf-life": 30,
                }
            },
        )
        assert received.status_code == 200
        assert received.json()["status"] == "succeeded"

        issued = client.post(
            "/api/ai/tools/outbound_create/execute",
            json={
                "arguments": {
                    "request-id": f"ai-out-{uuid4().hex}",
                    "item": item_name,
                    "qty": 3,
                    "use": "檢修",
                    "target": "Native round trip",
                }
            },
        )
        assert issued.status_code == 200
        assert issued.json()["status"] == "succeeded"

        inventory = client.get("/api/bootstrap").json()["INVENTORY"]
        item_rows = [row for row in inventory if row["itemId"] == item_id]
        assert len(item_rows) == 1
        assert item_rows[0]["stock"] == 7.0
        assert item_rows[0]["unitPrice"] == 12.5

        with tenant_session(actor.tenant_id) as session:
            native = (
                session.execute(
                    text(
                        """
                        SELECT
                          (SELECT count(*) FROM warehouse.inbound_order_lines
                           WHERE item_id = CAST(:item_id AS uuid)) AS inbound_lines,
                          (SELECT count(*) FROM warehouse.outbound_order_lines
                           WHERE item_id = CAST(:item_id AS uuid)) AS outbound_lines,
                          (SELECT COALESCE(SUM(quantity_on_hand), 0)
                           FROM warehouse.stock_lots
                           WHERE item_id = CAST(:item_id AS uuid) AND active) AS stock,
                          (SELECT array_agg(DISTINCT origin ORDER BY origin)
                           FROM terminal.command_executions
                           WHERE tool_name IN (
                             'item_create', 'item_update', 'inbound_create', 'outbound_create'
                           )) AS origins
                        """
                    ),
                    {"item_id": item_id},
                )
                .mappings()
                .one()
            )
        assert int(native["inbound_lines"]) == 1
        assert int(native["outbound_lines"]) == 1
        assert float(native["stock"]) == 7.0
        assert native["origins"] == ["ai_tool", "manual_ui"]
    finally:
        app.dependency_overrides.clear()


def test_command_audit_accepts_runtime_and_all_live_executor_outcomes(
    monkeypatch,
) -> None:
    actor = _actor()

    market = executor.execute_runtime_tool_call(actor, "tender_market", {})
    assert market["status"] == "succeeded"
    assert market["data"]["available"] is True
    assert market["data"]["empty"] is True
    assert market["data"]["reason"] == "no_records"
    assert market["data"]["market_scope"] == "warehouse_os_connected_companies"
    assert market["data"]["external_public_sources"]["connected"] is False
    assert market["data"]["screening"] == {
        "performed": False,
        "reason": "no_connected_platform_tenders_to_screen",
    }
    assert market["execution_id"]

    confirmation = executor.execute_runtime_tool_call(
        actor,
        "record_category_create",
        {"key": "runtime_test", "name": "Runtime test"},
    )
    assert confirmation["status"] == "confirmation_required"
    assert confirmation["execution_id"]

    def reject_target(*_args, **_kwargs) -> object:
        raise executor.CommandAdapterError(409, {"detail": "test rejection"})

    monkeypatch.setattr(executor, "_dispatch", reject_target)
    rejected = executor.execute_runtime_tool_call(actor, "tender_market", {})
    assert rejected["status"] == "target_rejected"
    assert rejected["execution_id"]

    invalid_contract = executor._execute_entry(
        {
            "command": "invalid contract test",
            "tool_name": "invalid_contract_test",
            "api_method": "TRACE",
            "api_path": "/not-an-api-contract",
            "params": [],
            "permission": "",
            "writes": False,
            "risk": "low",
        },
        actor,
        {},
        origin="auto_runtime",
        enforce_actor_permissions=False,
    )
    assert invalid_contract["status"] == "invalid_contract"
    assert invalid_contract["execution_id"]

    with tenant_session(actor.tenant_id) as session:
        audited = (
            session.execute(
                text(
                    """
                SELECT origin, status, tool_name
                FROM terminal.command_executions
                WHERE id = ANY(CAST(:execution_ids AS uuid[]))
                ORDER BY created_at, id
                """
                ),
                {
                    "execution_ids": [
                        market["execution_id"],
                        confirmation["execution_id"],
                        rejected["execution_id"],
                        invalid_contract["execution_id"],
                    ]
                },
            )
            .mappings()
            .all()
        )

    assert {row["origin"] for row in audited} == {"auto_runtime"}
    assert {row["status"] for row in audited} == {
        "succeeded",
        "confirmation_required",
        "target_rejected",
        "invalid_contract",
    }


def test_database_command_audit_constraints_cover_the_application_contract() -> None:
    with system_session() as session:
        constraints = dict(
            session.execute(
                text(
                    """
                    SELECT conname, pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE conrelid = 'terminal.command_executions'::regclass
                      AND conname IN (
                        'command_executions_origin_check',
                        'command_executions_status_check'
                      )
                    """
                )
            ).all()
        )

    origin_contract = constraints["command_executions_origin_check"]
    status_contract = constraints["command_executions_status_check"]
    assert all(f"'{value}'" in origin_contract for value in COMMAND_EXECUTION_ORIGINS)
    assert all(f"'{value}'" in status_contract for value in COMMAND_EXECUTION_STATUSES)


def test_organization_topology_edit_buttons_round_trip() -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        structure = client.get("/api/org/structure")
        assert structure.status_code == 200
        company = next(unit for unit in structure.json()["units"] if unit["unit_type"] == "company")
        assert structure.json()["company"]["id"] == company["id"]
        assert structure.json()["company"]["unit_name"] == actor.tenant_name

        created_department = client.post(
            "/api/org/departments",
            json={
                "unit_name": "可編輯部門",
                "unit_type": "department",
                "parent_id": "company",
                "description": "created by topology round trip",
            },
        )
        assert created_department.status_code == 200
        department_id = created_department.json()["id"]

        updated_department = client.post(
            f"/api/org/departments/{department_id}",
            json={
                "unit_name": "已編輯部門",
                "unit_type": "team",
                "parent_id": "company",
                "manager_user_id": None,
                "description": "edited by topology round trip",
            },
        )
        assert updated_department.status_code == 200

        created_position = client.post(
            "/api/org/positions",
            json={
                "position_name": "可編輯崗位",
                "org_unit_id": department_id,
                "role_id": None,
                "level": 3,
                "is_manager": False,
                "description": "",
            },
        )
        assert created_position.status_code == 200
        position_id = created_position.json()["id"]

        updated_position = client.post(
            f"/api/org/positions/{position_id}",
            json={
                "position_name": "已編輯崗位",
                "org_unit_id": department_id,
                "role_id": "自訂角色",
                "level": 4,
                "is_manager": True,
                "description": "",
            },
        )
        assert updated_position.status_code == 200

        assert (
            client.post(
                f"/api/org/departments/{department_id}/permissions",
                json={"enabled": True, "permissions": ["overview.read"]},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/org/departments/{department_id}/navigation",
                json={"enabled": True, "modules": ["dashboard"]},
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/org/positions/{position_id}/navigation",
                json={"enabled": True, "modules": ["dashboard"]},
            ).status_code
            == 200
        )

        assert client.post(f"/api/org/positions/{position_id}/archive").status_code == 200
        assert client.post(f"/api/org/departments/{department_id}/archive").status_code == 200

        structure = client.get("/api/org/structure").json()
        department = next(unit for unit in structure["units"] if unit["id"] == department_id)
        position = next(item for item in structure["positions"] if item["id"] == position_id)
        assert department["unit_name"] == "已編輯部門"
        assert department["active"] is False
        assert position["position_name"] == "已編輯崗位"
        assert position["active"] is False
    finally:
        app.dependency_overrides.clear()


def test_member_appointments_share_button_ai_contract_and_project_l11() -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        structure = client.get("/api/org/structure").json()
        positions = [row for row in structure["positions"] if row["active"]]
        assert len(positions) >= 3
        primary, first_concurrent, second_concurrent = positions[:3]

        seeded_primary = client.post(
            f"/api/org/users/{actor.user_id}/assign",
            json={"position_code": primary["position_code"]},
        )
        assert seeded_primary.status_code == 200
        assert seeded_primary.json()["member"]["governance_level"] == 11
        assert seeded_primary.json()["member"]["governance_title"] == "平台擁有者"

        action_rows = {
            row["tool_name"]: row for row in client.get("/api/business/actions").json()["actions"]
        }
        for tool_name in (
            "organization_user_appointment_add",
            "organization_user_appointment_update",
            "organization_user_appointment_remove",
        ):
            assert action_rows[tool_name]["available"] is True
            assert action_rows[tool_name]["authorized"] is True
            assert action_rows[tool_name]["manual_execution"] == "execute"
        assert action_rows["organization_user_assign"]["manual_execution"] == (
            "governed_confirmation"
        )

        ai_tool_names = {
            row["function"]["name"] for row in client.get("/api/ai/tools").json()["tools"]
        }
        assert {
            "organization_user_assign",
            "organization_user_appointment_add",
            "organization_user_appointment_update",
            "organization_user_appointment_remove",
        }.issubset(ai_tool_names)

        added = client.post(
            "/api/business/actions/organization_user_appointment_add/execute",
            json={
                "arguments": {
                    "user": str(actor.user_id),
                    "position": first_concurrent["position_code"],
                }
            },
        )
        assert added.status_code == 200
        assert added.json()["status"] == "succeeded"
        added_data = added.json()["data"]
        assert added_data["verification"]["source"] == (
            "tenant_member_appointment_readback"
        )
        assert len(added_data["member"]["appointments"]) == 2
        assert added_data["world_observation"]["verified_facts"]["appointment_count"] == 2

        updated = client.post(
            "/api/business/actions/organization_user_appointment_update/execute",
            json={
                "arguments": {
                    "user": str(actor.user_id),
                    "position": first_concurrent["position_code"],
                    "new-position": second_concurrent["position_code"],
                }
            },
        )
        assert updated.status_code == 200
        assert updated.json()["status"] == "succeeded"
        updated_codes = {
            row["position_code"] for row in updated.json()["data"]["member"]["appointments"]
        }
        assert updated_codes == {primary["position_code"], second_concurrent["position_code"]}

        promoted = client.post(
            f"/api/org/users/{actor.user_id}/assign",
            json={"position_code": second_concurrent["position_code"]},
        ).json()
        appointment_types = {
            row["position_code"]: row["appointment_type"]
            for row in promoted["member"]["appointments"]
        }
        assert appointment_types[second_concurrent["position_code"]] == "primary"
        assert appointment_types[primary["position_code"]] == "concurrent"

        removed = client.post(
            "/api/business/actions/organization_user_appointment_remove/execute",
            json={
                "arguments": {
                    "user": str(actor.user_id),
                    "position": primary["position_code"],
                }
            },
        )
        assert removed.status_code == 200
        assert removed.json()["status"] == "succeeded"
        assert [
            row["position_code"]
            for row in removed.json()["data"]["member"]["appointments"]
        ] == [second_concurrent["position_code"]]

        owner = next(
            row for row in client.get("/api/users").json()["users"]
            if row["id"] == str(actor.user_id)
        )
        assert owner["is_platform_owner"] is True
        assert owner["governance_level"] == 11
        assert owner["governance_title"] == "平台擁有者"
        assert client.get("/api/permissions/topology").json()["actor"]["governance_level"] == 11
    finally:
        app.dependency_overrides.clear()


def test_auto_runtime_distils_all_company_authority_and_capability_genes(monkeypatch) -> None:
    actor = _actor()
    replies = iter(
        [
            {
                "understood_goal": "Understand the warehouse state",
                "success_criteria": ["Current warehouses are observed"],
                "uncertainties": [],
                "selected_tool_names": ["warehouse_list"],
                "context_focus": ["warehouse"],
                "reasoning": "The goal needs a live warehouse observation.",
            },
            {
                "message": "I identified the warehouse observation capability.",
                "plan": ["Observe the warehouse", "Reflect on the result"],
                "decisions": [
                    {
                        "tool_name": "warehouse_list",
                        "judgment": "ask_person",
                        "arguments": {},
                        "reasoning": "Keep this test non-executing.",
                        "continue_after_result": False,
                    }
                ],
                "completion_assessment": {
                    "complete": False,
                    "reason": "The capability has not been invoked.",
                },
            },
            {
                "message": "The capability is available, but the person must decide whether to invoke it.",
                "goal_complete": False,
                "evidence": [],
                "contradictions": [],
                "revised_plan": ["Ask whether the warehouse observation should run"],
                "continue_reason": "The selected judgment explicitly asks the person.",
                "continue_autonomously": False,
                "requires_user_input": True,
                "next_domains": [],
                "next_families": [],
                "next_decisions": [],
            },
        ]
    )

    class _ModelResponse:
        def __init__(self, payload: dict[str, object]):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": json.dumps(self._payload)}}]}

    monkeypatch.setattr(
        auto_runtime,
        "connected_deepseek",
        lambda *_args: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="runtime-test",
        ),
    )
    monkeypatch.setattr(
        auto_runtime.httpx,
        "post",
        lambda *_args, **_kwargs: _ModelResponse(next(replies)),
    )

    result = auto_runtime.run_auto_runtime(
        actor,
        SimpleNamespace(),
        "Please understand the warehouse state",
        surface="super_terminal",
    )

    assert result.observations["context_architecture"] == "hierarchical_funnel_v2"
    assert (
        result.observations["context_strategy"]
        == "domain_then_family_then_exact_tool_then_live_data"
    )
    assert result.observations["capability_genes"] == 537
    assert result.observations["authority_world"]["positions"] >= 1
    assert result.distillation["selected_tool_names"] == ["warehouse_list"]
    assert result.decisions[0]["judgment"] == "ask_person"
    with tenant_session(actor.tenant_id) as session:
        stored = (
            session.execute(
                text(
                    """
                SELECT status, context_snapshot
                FROM secretariat.runs WHERE id = :id
                """
                ),
                {"id": result.run_id},
            )
            .mappings()
            .one()
        )
    assert stored["status"] == "waiting"
    assert stored["context_snapshot"]["architecture"] == "hierarchical_funnel_v2"
    assert "L0_permanent_world_map" in stored["context_snapshot"]["layers"]


def test_auto_runtime_simple_conversation_uses_one_compact_model_call(monkeypatch) -> None:
    actor = _actor()
    calls: list[dict[str, object]] = []

    class _ModelResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "interaction_mode": "conversation",
                                    "understood_goal": "Greet the user",
                                    "message": "您好，我在這裡。",
                                    "needs_tools": False,
                                    "selected_domains": [],
                                    "context_requests": [],
                                    "success_criteria": ["Respond naturally"],
                                    "uncertainties": [],
                                    "reasoning": "No live business evidence is required.",
                                    "memory_depth": "index",
                                }
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(
        auto_runtime,
        "connected_deepseek",
        lambda *_args: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="runtime-test",
        ),
    )

    def fake_post(*_args, **kwargs):
        calls.append(kwargs)
        return _ModelResponse()

    monkeypatch.setattr(auto_runtime.httpx, "post", fake_post)

    result = auto_runtime.run_auto_runtime(
        actor,
        SimpleNamespace(),
        "你好",
        surface="assistant",
    )

    assert result.message == "您好，我在這裡。"
    assert len(calls) == 1
    assert result.observations["expanded_domains"] == []
    metrics = result.observations["context_metrics"]
    assert metrics["model_calls"] == 1
    assert metrics["total_input_chars"] < 20_000
    assert metrics["phases"][0]["phase"] == "route"
    request_body = calls[0]["json"]
    assert request_body["model"] == "deepseek-v4-flash"
    assert request_body["thinking"] == {"type": "disabled"}
    assert request_body["response_format"] == {"type": "json_object"}
    assert request_body["max_tokens"] == 800


def test_auto_runtime_stops_at_model_judged_human_input_boundary(monkeypatch) -> None:
    actor = _actor()
    calls: list[dict[str, object]] = []

    class _ModelResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "interaction_mode": "operational",
                                    "understood_goal": "Draft a contract in stages",
                                    "message": (
                                        "請先提供合同名稱與類型、相對方、標的與金額，"
                                        "以及關鍵商務條件。"
                                    ),
                                    "needs_tools": True,
                                    "requires_user_input": True,
                                    "selected_domains": ["legal"],
                                    "selected_families": [],
                                    "context_requests": ["operational_world"],
                                    "success_criteria": ["Collect essential human inputs"],
                                    "uncertainties": ["Contract terms are not supplied"],
                                    "reasoning": "Human input must precede legal-ledger review.",
                                    "memory_depth": "index",
                                }
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(
        auto_runtime,
        "connected_deepseek",
        lambda *_args: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="runtime-test",
        ),
    )

    def fake_post(*_args, **kwargs):
        calls.append(kwargs)
        return _ModelResponse()

    monkeypatch.setattr(auto_runtime.httpx, "post", fake_post)

    result = auto_runtime.run_auto_runtime(
        actor,
        SimpleNamespace(),
        "先追問合同資料，再讀取法務台帳並起草合同。",
        surface="secretary",
        context_mode="thinking",
    )

    assert len(calls) == 1
    assert calls[0]["json"]["model"] == "deepseek-v4-pro"
    assert calls[0]["json"]["thinking"] == {"type": "enabled"}
    assert result.reflection["goal_complete"] is False
    assert result.reflection["requires_user_input"] is True
    assert result.reflection["runtime_stop_reason"] == "requires_user_input"
    assert result.observations["expanded_domains"] == []
    assert result.message.startswith("請先提供合同名稱")


def test_auto_runtime_autonomously_acquires_missing_evidence(monkeypatch) -> None:
    actor = _actor()
    replies = iter(
        [
            {
                "understood_goal": "Diagnose procurement workflow blockers",
                "success_criteria": ["Blockers are supported by live evidence"],
                "uncertainties": ["Workflow definitions are not yet observed"],
                "selected_tool_names": ["wf_inbox"],
                "context_focus": ["procurement"],
                "reasoning": "Begin with the live procurement inbox.",
            },
            {
                "message": "I will inspect the current procurement inbox.",
                "plan": ["Inspect inbox", "Resolve any remaining evidence gaps"],
                "decisions": [
                    {
                        "tool_name": "wf_inbox",
                        "judgment": "execute",
                        "arguments": {"scope": "all"},
                        "reasoning": "Observe every current-company procurement task.",
                        "continue_after_result": True,
                    }
                ],
                "completion_assessment": {
                    "complete": False,
                    "reason": "Workflow definitions have not been observed.",
                },
            },
            {
                "message": "The inbox is empty; I am checking workflow definitions.",
                "goal_complete": False,
                "evidence": ["The current-company inbox is empty."],
                "contradictions": [],
                "revised_plan": ["Inspect inbox", "Inspect workflow definitions"],
                "continue_reason": "A registered read capability can resolve the gap.",
                "continue_autonomously": True,
                "requires_user_input": False,
                "next_decisions": [
                    {
                        "tool_name": "wf_workflows",
                        "arguments": {},
                        "reasoning": "Confirm whether active definitions exist.",
                    }
                ],
                "memory_candidate": None,
            },
            {
                "message": "No active workflow definition exists, so new procurement tasks cannot start.",
                "goal_complete": True,
                "evidence": [
                    "The inbox is empty.",
                    "The workflow definition list is empty.",
                ],
                "contradictions": [],
                "revised_plan": ["Provision a workflow definition before starting a request"],
                "continue_reason": None,
                "continue_autonomously": False,
                "requires_user_input": False,
                "next_decisions": [],
                "memory_candidate": None,
            },
        ]
    )
    executed: list[tuple[str, dict[str, object]]] = []

    class _ModelResponse:
        def __init__(self, payload: dict[str, object]):
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": json.dumps(self._payload)}}]}

    monkeypatch.setattr(
        auto_runtime,
        "connected_deepseek",
        lambda *_args: SimpleNamespace(
            base_url="https://model.example.test",
            api_key="secret",
            model="runtime-test",
        ),
    )
    monkeypatch.setattr(
        auto_runtime.httpx,
        "post",
        lambda *_args, **_kwargs: _ModelResponse(next(replies)),
    )
    monkeypatch.setattr(
        auto_runtime,
        "execute_runtime_tool_call",
        lambda _actor, tool_name, arguments, **_kwargs: (
            executed.append((tool_name, arguments))
            or {
                "ok": True,
                "data": {
                    "items": [],
                    "count": 0,
                    "reason": "no_records",
                },
            }
        ),
    )

    result = auto_runtime.run_auto_runtime(
        actor,
        SimpleNamespace(),
        "Diagnose procurement workflow blockers",
        surface="super_terminal",
    )

    assert executed == [("wf_inbox", {"scope": "all"}), ("wf_workflows", {})]
    assert result.reflection["goal_complete"] is True
    assert result.reflection["runtime_stop_reason"] == "goal_complete"
    assert result.reflection["autonomous_rounds"] == 2
    assert result.observations["selected_capability_genes"] == [
        "wf_inbox",
        "wf_workflows",
    ]
    assert [item["runtime_round"] for item in result.tool_results] == [1, 2]
    assert (
        max(int(item["input_chars"]) for item in result.observations["context_metrics"]["phases"])
        < 50_000
    )


def test_passkey_registration_login_list_and_delete_round_trip(monkeypatch) -> None:
    actor = _actor()
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    credential_id_bytes = b"verified-passkey-credential"
    credential_id = bytes_to_base64url(credential_id_bytes)
    registration = SimpleNamespace(
        credential_id=credential_id_bytes,
        credential_public_key=b"verified-public-key",
        sign_count=0,
        aaguid="00000000-0000-0000-0000-000000000000",
        credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
        credential_backed_up=False,
    )
    authentication = SimpleNamespace(
        new_sign_count=1,
        credential_device_type=CredentialDeviceType.SINGLE_DEVICE,
        credential_backed_up=False,
    )
    monkeypatch.setattr(
        "app.api.full_stack_identity.verify_registration_response",
        lambda **_: registration,
    )
    monkeypatch.setattr(
        "app.api.full_stack_identity.verify_authentication_response",
        lambda **_: authentication,
    )
    try:
        unknown_rp = client.post(
            "/api/auth/passkeys/login/options",
            json={"username": actor.username},
        )
        assert unknown_rp.status_code == 409
        assert "目前網站" in unknown_rp.json()["detail"]

        discoverable = client.post("/api/auth/passkeys/login/options", json={})
        assert discoverable.status_code == 200
        assert discoverable.json()["publicKey"]["allowCredentials"] == []

        denied = client.post(
            "/api/auth/passkeys/register/options",
            json={"password": "wrong-password"},
        )
        assert denied.status_code == 401

        options = client.post(
            "/api/auth/passkeys/register/options",
            json={"password": "test-password"},
        )
        assert options.status_code == 200
        assert options.json()["publicKey"]["rp"]["id"] == "localhost"

        registered = client.post(
            "/api/auth/passkeys/register/verify",
            json={
                "request_id": options.json()["request_id"],
                "name": "Test device",
                "credential": {
                    "id": credential_id,
                    "rawId": credential_id,
                    "type": "public-key",
                    "response": {"transports": ["internal"]},
                },
            },
        )
        assert registered.status_code == 200
        passkey_id = registered.json()["passkey"]["id"]

        listed = client.get("/api/auth/passkeys")
        assert listed.status_code == 200
        assert listed.json()["passkeys"][0]["name"] == "Test device"
        assert listed.json()["passkeys"][0]["rp_id"] == "localhost"
        assert "credential_id" not in listed.json()["passkeys"][0]

        with system_session() as session:
            session.execute(
                text("UPDATE iam.passkeys SET rp_id = 'bonfirework.org' WHERE id = :id"),
                {"id": passkey_id},
            )
        foreign_rp = client.post(
            "/api/auth/passkeys/login/options",
            json={"username": actor.username},
        )
        assert foreign_rp.status_code == 409
        assert client.get("/api/auth/passkeys").json()["passkeys"] == []
        assert (
            client.post(
                "/api/auth/passkeys/step-up/options",
                json={"purpose": "test", "resource": {"id": "foreign-rp"}},
            ).status_code
            == 409
        )
        assert (
            client.request(
                "DELETE",
                f"/api/auth/passkeys/{passkey_id}",
                json={"password": "test-password"},
            ).status_code
            == 404
        )
        with system_session() as session:
            session.execute(
                text("UPDATE iam.passkeys SET rp_id = 'localhost' WHERE id = :id"),
                {"id": passkey_id},
            )

        login_options = client.post(
            "/api/auth/passkeys/login/options",
            json={"username": actor.username},
        )
        assert login_options.status_code == 200
        assert login_options.json()["publicKey"]["rpId"] == "localhost"

        login = client.post(
            "/api/auth/passkeys/login/verify",
            json={
                "request_id": login_options.json()["request_id"],
                "credential": {
                    "id": credential_id,
                    "rawId": credential_id,
                    "type": "public-key",
                    "response": {},
                },
            },
        )
        assert login.status_code == 200
        assert login.json()["token"]

        denied_delete = client.request(
            "DELETE",
            f"/api/auth/passkeys/{passkey_id}",
            json={"password": "wrong-password"},
        )
        assert denied_delete.status_code == 401
        deleted = client.request(
            "DELETE",
            f"/api/auth/passkeys/{passkey_id}",
            json={"password": "test-password"},
        )
        assert deleted.status_code == 200
        assert client.get("/api/auth/passkeys").json()["passkeys"] == []
    finally:
        app.dependency_overrides.clear()
