from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import zipfile
from uuid import uuid4

import psycopg
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.api import router as api_router
from app.api.deps import ActorContext, current_actor
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.runtime_controller import RuntimeController
from app.services import digital_asset_hosting, hosted_database
from app.services.auto_runtime import RuntimeResult
from app.services.confirmation_actions import (
    execute_authorized_confirmation_action,
    propose_confirmation_action,
)
from app.services.conversation_history import create_conversation
from app.services.passkey_grants import issue_step_up_grant
from app.services.runtime_context import build_context_layers
from app.services.templates import provision_tenant_template
from app.services.workspace_deployments import request_workspace_deployment
from app.terminal import executor, legacy_catalog

pytestmark = pytest.mark.integration


def _source_zip(files: dict[str, str | bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return buffer.getvalue()


def _actor(label: str) -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"asset-{label}-{tenant_id.hex[:8]}"
    username = f"asset-{label}-{user_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug, "name": f"Asset Test {label}"},
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
                "display_name": f"Asset Owner {label}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=f"Asset Test {label}",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level,
                  topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, 10, 10, 'Owner'
                )
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
        tenant_name=f"Asset Test {label}",
        industry_template_key="generic_warehouse",
        username=username,
        display_name=f"Asset Owner {label}",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset(
            {
                "ai.use",
                "assets.read",
                "assets.manage",
                "asset_mgmt.read",
                "asset_mgmt.manage",
            }
        ),
    )


def test_upload_requires_explicit_new_asset_intent_and_leaves_no_orphan() -> None:
    actor = _actor("upload-intent")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        rejected = client.post(
            "/api/digital-assets/upload",
            json={
                "name": "mk4-workspace-source",
                "asset_kind": "software",
                "upload_type": "source",
                "artifact_hash": "a" * 64,
                "artifact_uri": "custody://mk4/source.zip",
            },
        )
        assert rejected.status_code == 422
        assert rejected.json()["detail"]["reason"] == "explicit_new_asset_intent_required"
        with tenant_session(actor.tenant_id) as session:
            assert (
                session.execute(text("SELECT count(*) FROM digital_asset.assets")).scalar_one() == 0
            )

        created = client.post(
            "/api/digital-assets/upload",
            json={
                "create_new_asset": True,
                "name": "mk4",
                "asset_kind": "software",
                "upload_type": "source",
                "artifact_hash": "a" * 64,
                "artifact_uri": "custody://mk4/source.zip",
            },
        )
        assert created.status_code == 201
        assert created.json()["asset"]["name"] == "mk4"
        orphan = client.post(
            "/api/digital-assets",
            json={"name": "mk4-workspace-source", "asset_kind": "software"},
        )
        assert orphan.status_code == 201
        reconciled = client.post(
            f"/api/digital-assets/{orphan.json()['asset']['uuid']}/archive",
            json={
                "reconciled_into": created.json()["asset"]["uuid"],
                "reason": "Source upload created a duplicate empty identity",
            },
        )
        assert reconciled.status_code == 200
        assert reconciled.json()["asset"]["status"] == "archived"
        assert (
            reconciled.json()["world_observation"]["verified_facts"]["duplicate_reconciled"] is True
        )
        ordinary_list = client.get("/api/digital-assets").json()["assets"]
        assert {item["name"] for item in ordinary_list} == {"mk4"}
        archived_list = client.get("/api/digital-assets", params={"status": "archived"}).json()[
            "assets"
        ]
        assert {item["name"] for item in archived_list} == {"mk4-workspace-source"}
        with tenant_session(actor.tenant_id) as session:
            assert (
                session.execute(text("SELECT count(*) FROM digital_asset.assets")).scalar_one() == 2
            )
    finally:
        app.dependency_overrides.clear()


def test_native_21_guide_cli_and_provision_contract(tmp_path, monkeypatch) -> None:
    actor = _actor("native-guide")
    settings = Settings(asset_storage_root=tmp_path / "digital-assets")
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        guide = client.get("/api/digital-assets/guide")
        assert guide.status_code == 200
        guide_payload = guide.json()
        assert guide_payload["version"] == "2.1"
        assert "wak_" in guide_payload["content"]
        assert "/api/workspaces/v1/info" in guide_payload["content"]
        assert guide_payload["downloads"] == [
            {
                "label": "下載《數字資產託管指南 2.1》",
                "url": "/api/digital-assets/guide/download",
                "filename": "digital-asset-custody-guide-2.1.zh-TW.md",
            },
            {
                "label": "下載 dam.py 2.1",
                "url": "/api/digital-assets/cli",
                "filename": "dam.py",
            },
        ]

        guide_download = client.get("/api/digital-assets/guide/download")
        assert guide_download.status_code == 200
        assert guide_download.text.startswith("# Warehouse OS 2.1《數字資產託管指南》")

        cli_download = client.get("/api/digital-assets/cli")
        assert cli_download.status_code == 200
        assert 'DEFAULT_BASE = "http://testserver"' in cli_download.text
        assert '"/api/workspaces/v1/info"' in cli_download.text
        assert '"/api/dam/v1/' not in cli_download.text
        compile(cli_download.text, "dam.py", "exec")

        provisioned = client.post(
            "/api/digital-assets/provision",
            json={
                "name": "Native Customer Operations",
                "asset_kind": "software",
                "workspace_key": "native-customer-operations",
                "runtime_type": "api",
                "service_plan": "hosted",
                "database_name": "customer_operations",
                "label": "Initial Data API key",
                "scopes": ["workspace:read", "data:read", "data:write"],
                "expires_days": 30,
            },
        )
        assert provisioned.status_code == 201
        payload = provisioned.json()
        assert payload["asset"]["asset_kind"] == "software"
        assert payload["workspace"]["workspace_key"] == "native-customer-operations"
        assert payload["database"]["provider_key"] == "warehouse_postgresql_data_api"
        assert payload["database"]["status"] == "ready"
        assert payload["api_key"].startswith("wak_")
        assert payload["label"] == "Initial Data API key"
        assert payload["key_id"] == payload["credential_id"]
        assert payload["key_kind"] == "primary"
        assert payload["is_primary"] is True
        assert set(payload["scopes"]) == set(digital_asset_hosting.WORKSPACE_ALL_SCOPES)
        assert payload["cli_download"] == "/api/digital-assets/cli"

        info = client.get(
            "/api/workspaces/v1/info",
            headers={"Authorization": f"Bearer {payload['api_key']}"},
        )
        assert info.status_code == 200
        assert info.json()["workspace"]["uuid"] == payload["workspace"]["uuid"]

        listed_keys = client.get(f"/api/workspaces/{payload['workspace']['workspace_key']}/keys")
        assert listed_keys.status_code == 200
        listed_payload = listed_keys.json()
        assert listed_payload["count"] == 1
        assert listed_payload["keys"][0]["id"] == payload["credential_id"]
        assert listed_payload["keys"][0]["status"] == "active"
        assert listed_payload["keys"][0]["key_kind"] == "primary"
        assert listed_payload["summary"]["primary_active"] == 1
        assert listed_payload["summary"]["delegated_active"] == 0
        assert listed_payload["plaintext_exposed"] is False
        assert "token_hash" not in str(listed_payload)
        assert payload["api_key"] not in str(listed_payload)

        primary_revoke = client.post(
            f"/api/workspaces/{payload['workspace']['workspace_key']}/keys/"
            f"{payload['credential_id']}/revoke"
        )
        assert primary_revoke.status_code == 409

        delegated_response = client.post(
            f"/api/workspaces/{payload['workspace']['workspace_key']}/keys",
            json={
                "label": "Reporting client",
                "scopes": ["workspace:read", "data:read"],
                "expires_days": 15,
            },
        )
        assert delegated_response.status_code == 200
        delegated = delegated_response.json()
        assert delegated["key_kind"] == "delegated"
        assert delegated["parent_credential_id"] == payload["credential_id"]

        rotated_response = client.post(
            f"/api/workspaces/{payload['workspace']['workspace_key']}/keys/primary/rotate",
            json={"label": "Rotated primary", "expires_days": 30},
        )
        assert rotated_response.status_code == 200
        rotated = rotated_response.json()
        assert rotated["key_kind"] == "primary"
        assert rotated["replaced_credential_id"] == payload["credential_id"]
        assert set(rotated["scopes"]) == set(payload["scopes"])
        assert (
            client.get(
                "/api/workspaces/v1/info",
                headers={"Authorization": f"Bearer {payload['api_key']}"},
            ).status_code
            == 401
        )
        assert (
            client.get(
                "/api/workspaces/v1/info",
                headers={"Authorization": f"Bearer {delegated['api_key']}"},
            ).status_code
            == 200
        )

        revoked = client.post(
            f"/api/workspaces/{payload['workspace']['workspace_key']}/keys/"
            f"{delegated['credential_id']}/revoke"
        )
        assert revoked.status_code == 200
        assert revoked.json()["credential"]["status"] == "revoked"
        replay = client.post(
            f"/api/workspaces/{payload['workspace']['workspace_key']}/keys/"
            f"{delegated['credential_id']}/revoke"
        )
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True
        assert (
            client.get(
                "/api/workspaces/v1/info",
                headers={"Authorization": f"Bearer {delegated['api_key']}"},
            ).status_code
            == 401
        )

        # The AI path stages the same native provision capability, consumes a
        # purpose/resource-bound one-time grant, and puts plaintext only in a
        # browser-tab-bound encrypted delivery.
        conversation = create_conversation(actor, title="Host MK4")
        action = propose_confirmation_action(
            actor,
            tool_name="digital_market_provision",
            arguments={
                "name": "MK4 Exam Practice",
                "kind": "software",
                "summary": "Question practice software",
                "workspace-key": "mk4-exam-practice",
                "runtime": "web",
            },
            settings=settings,
            conversation_id=conversation["id"],
        )
        assert action["status"] == "pending"
        assert action["passkey_required"] is True
        assert "arguments" not in action
        grant_token = secrets.token_urlsafe(36)
        issue_step_up_grant(
            actor,
            token=grant_token,
            purpose="ai.confirmation.execute",
            resource={"action_id": action["id"], "revision": action["revision"]},
            verification={
                "verified": True,
                "method": "webauthn",
                "operator": actor.username,
            },
        )
        browser_client_id = "w2cc_" + secrets.token_urlsafe(24)
        confirmed = client.post(
            f"/api/agent/confirmation-actions/{action['id']}/confirm",
            json={
                "expected_revision": action["revision"],
                "step_up_token": grant_token,
                "credential_client_id": browser_client_id,
            },
        )
        assert confirmed.status_code == 200
        confirmed_payload = confirmed.json()
        assert confirmed_payload["ok"] is True
        assert confirmed_payload["signal"] == "authorization_granted"
        assert confirmed_payload["business_operation_executed"] is False
        assert confirmed_payload["action"]["status"] == "authorized"
        assert re.search(r"wak_[A-Za-z0-9_-]{20,}", str(confirmed_payload)) is None
        assert client.get("/api/workspaces/mk4-exam-practice/keys").status_code == 404
        continuation = confirmed_payload["action"]["continuation"]
        assert continuation["type"] == "authorization_granted"
        handed_off: dict[str, object] = {}

        def fake_runtime(
            runtime_actor,
            runtime_settings,
            goal,
            **kwargs,
        ):
            signal = kwargs.get("authorization_signal")
            assert isinstance(signal, dict)
            handed_off.update(signal)
            executed = execute_authorized_confirmation_action(
                runtime_actor,
                signal["action_id"],
                authorization_keychain_id=signal["authorization_keychain_id"],
                conversation_id=kwargs.get("conversation_id"),
                settings=runtime_settings,
            )
            return RuntimeResult(
                goal=goal,
                message="AI Runtime 已觀察授權信號並完成託管。",
                model="runtime-test",
                observations={"authorization_signal": True},
                plan=("觀察授權", "執行已授權能力", "核對結果"),
                run_id=kwargs.get("run_id"),
                tool_results=(
                    {
                        "tool_name": signal["tool_name"],
                        "decision_reasoning": "AI 決定消耗已授權 Keychain",
                        "result": executed,
                    },
                ),
                reflection={"goal_complete": True, "requires_user_input": False},
                response_locale="zh-Hant",
            )

        monkeypatch.setattr(api_router, "run_auto_runtime", fake_runtime)
        monkeypatch.setattr(
            api_router,
            "run_background_memory_steward",
            lambda *_args, **_kwargs: [],
        )
        resumed = client.post(
            "/api/agent/run/stream",
            json={
                "text": "請使用已授權的 Keychain 繼續完成原操作。",
                "conversation_id": conversation["id"],
                "surface": "secretary",
                "resume_confirmation_action_id": action["id"],
                "authorization_keychain_id": continuation["authorization_keychain_id"],
                "hidden_user_turn": True,
                "terminal_event": True,
            },
        )
        assert resumed.status_code == 200
        resumed_events = [json.loads(line) for line in resumed.text.splitlines() if line.strip()]
        completion = next(
            event for event in resumed_events if event["event"] == "authorization_completed"
        )
        assert completion["action"]["status"] == "completed"
        assert handed_off["business_operation_executed"] is False
        assert handed_off["tool_name"] == "digital_market_provision"
        assert re.search(r"wak_[A-Za-z0-9_-]{20,}", resumed.text) is None
        assert client.get("/api/workspaces/mk4-exam-practice/keys").status_code == 200
        replayed_resume = client.post(
            "/api/agent/run/stream",
            json={
                "text": "請繼續完成原操作。",
                "conversation_id": conversation["id"],
                "surface": "secretary",
                "resume_confirmation_action_id": action["id"],
                "authorization_keychain_id": continuation["authorization_keychain_id"],
                "hidden_user_turn": True,
                "terminal_event": True,
            },
        )
        assert replayed_resume.status_code == 200
        listed_after_replay = client.get("/api/workspaces/mk4-exam-practice/keys").json()
        assert listed_after_replay["count"] == 1
        delivery = completion["action"]["credential_deliveries"][0]
        fetched = client.post(
            delivery["fetch_path"],
            json={
                "delivery_id": delivery["delivery_id"],
                "credential_client_id": browser_client_id,
            },
        )
        assert fetched.status_code == 200
        fetched_payload = fetched.json()
        assert fetched_payload["requires_ack"] is True
        assert fetched_payload["credentials"][0]["value"].startswith("wak_")
        assert fetched_payload["credentials"][0]["action_key"] == action["action_key"]
        acked = client.post(
            delivery["ack_path"],
            json={
                "delivery_id": delivery["delivery_id"],
                "credential_client_id": browser_client_id,
            },
        )
        assert acked.status_code == 200
        assert acked.json()["plaintext_destroyed"] is True
        assert (
            client.post(
                delivery["fetch_path"],
                json={
                    "delivery_id": delivery["delivery_id"],
                    "credential_client_id": browser_client_id,
                },
            ).status_code
            == 410
        )

        guide_entry = legacy_catalog.entry_by_tool_name("digital_market_guide")
        provision_entry = legacy_catalog.entry_by_tool_name("digital_market_provision")
        key_entry = legacy_catalog.entry_by_tool_name("digital_market_key_issue")
        key_list_entry = legacy_catalog.entry_by_tool_name("digital_market_keys_list")
        key_revoke_entry = legacy_catalog.entry_by_tool_name("digital_market_key_revoke")
        primary_rotate_entry = legacy_catalog.entry_by_tool_name(
            "digital_market_primary_key_rotate"
        )
        assert guide_entry["api_path"] == "/api/digital-assets/guide"
        assert provision_entry["api_path"] == "/api/digital-assets/provision"
        assert key_entry["api_path"] == "/api/workspaces/{workspace_ref}/keys"
        assert key_list_entry["api_path"] == "/api/workspaces/{workspace_ref}/keys"
        assert key_revoke_entry["api_path"] == (
            "/api/workspaces/{workspace_ref}/keys/{credential_ref}/revoke"
        )
        assert primary_rotate_entry["api_path"] == (
            "/api/workspaces/{workspace_ref}/keys/primary/rotate"
        )
        assert {parameter["flag"] for parameter in key_entry["params"]} == {
            "workspace",
            "label",
            "scopes",
            "expires-days",
        }
    finally:
        app.dependency_overrides.clear()


def test_workspace_key_source_and_deployment_contract(tmp_path, monkeypatch) -> None:
    actor = _actor("workspace-deploy")
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        hosted_runtime_data_root=tmp_path / "runtime",
        runtime_host_data_root=tmp_path / "runtime",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        provisioned = client.post(
            "/api/digital-assets/provision",
            json={
                "name": "Workspace Deployment App",
                "asset_kind": "software",
                "workspace_key": "workspace-deployment-app",
                "runtime_type": "static",
                "service_plan": "hosted",
            },
        )
        assert provisioned.status_code == 201, provisioned.text
        key = provisioned.json()["api_key"]
        headers = {"Authorization": f"Bearer {key}"}
        workspace_id = provisioned.json()["workspace"]["uuid"]
        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text("DELETE FROM digital_asset.storage_bindings WHERE workspace_id=:workspace_id"),
                {"workspace_id": workspace_id},
            )
        unbound = client.get("/api/workspaces/v1/info", headers=headers)
        assert unbound.status_code == 200
        assert unbound.json()["workspace"]["storage"]["code"]["status"] == "unbound"
        assert unbound.json()["workspace"]["storage"]["data"]["status"] == "unbound"
        storage_probe = client.post("/api/workspaces/v1/storage/probe", headers=headers)
        assert storage_probe.status_code == 200, storage_probe.text
        assert set(storage_probe.json()["observations"]) == {"code", "data"}
        assert all(item["writable"] for item in storage_probe.json()["observations"].values())
        rebound = client.get("/api/workspaces/v1/info", headers=headers).json()
        assert rebound["workspace"]["storage"]["code"]["write_probe"] == "passed"
        assert rebound["workspace"]["storage"]["data"]["write_probe"] == "passed"
        package = _source_zip(
            {
                "site/index.html": "<!doctype html><title>Workspace Deployment</title>",
                "site/app.js": "globalThis.ready = true;",
            }
        )
        digest = hashlib.sha256(package).hexdigest()
        uploaded = client.post(
            "/api/workspaces/v1/sources/upload",
            headers={**headers, "Content-SHA256": digest},
            files={"file": ("site.zip", package, "application/zip")},
            data={"version_no": "v1.0.0", "component": "frontend"},
        )
        assert uploaded.status_code == 201, uploaded.text
        source = uploaded.json()["source"]
        assert source["artifact_sha256"] == digest
        assert uploaded.json()["archive"]["validated"] is True
        downloaded_source = client.get(
            f"/api/workspaces/v1/sources/{source['uuid']}/download",
            headers=headers,
        )
        assert downloaded_source.status_code == 200
        assert downloaded_source.content == package
        assert downloaded_source.headers["content-sha256"] == digest
        downloaded_source_by_legacy_id = client.get(
            f"/api/workspaces/v1/sources/{source['id']}/download",
            headers=headers,
        )
        assert downloaded_source_by_legacy_id.status_code == 200
        assert downloaded_source_by_legacy_id.content == package
        configured = client.put(
            "/api/workspaces/v1/runtime",
            headers=headers,
            json={
                "runtime_type": "auto",
                "source_version_id": source["uuid"],
                "component": "frontend",
            },
        )
        assert configured.status_code == 200, configured.text
        assert configured.json()["runtime"]["runtime_type"] == "static"
        assert configured.json()["runtime"]["runtime_family"] == "static"
        assert configured.json()["component"]["entrypoint"] == "index.html"

        replay = client.post(
            "/api/workspaces/v1/sources/upload",
            headers={**headers, "Content-SHA256": digest},
            files={"file": ("site.zip", package, "application/zip")},
        )
        assert replay.status_code == 201
        assert replay.json()["idempotent_replay"] is True
        assert client.get("/api/workspaces/v1/sources", headers=headers).json()["count"] == 1

        conflicting_package = _source_zip(
            {"index.html": "<!doctype html><title>Different immutable source</title>"}
        )
        version_conflict = client.post(
            "/api/workspaces/v1/sources/upload",
            headers=headers,
            files={"file": ("different.zip", conflicting_package, "application/zip")},
            data={"version_no": "v1.0.0", "component": "frontend"},
        )
        assert version_conflict.status_code == 409
        assert version_conflict.json()["detail"]["reason"] == "source_version_number_conflict"

        resumable_package = _source_zip(
            {
                "index.html": "<!doctype html><title>Resumable Pages upload</title>",
                "assets/course.bin": secrets.token_bytes(4 * 1024 * 1024 + 1024),
            }
        )
        resumable_digest = hashlib.sha256(resumable_package).hexdigest()
        upload_created = client.post(
            "/api/workspaces/v1/source-uploads",
            headers={**headers, "Idempotency-Key": "resumable-source-v1.1.0"},
            json={
                "filename": "resumable.zip",
                "content_type": "application/zip",
                "size_bytes": len(resumable_package),
                "sha256": resumable_digest,
                "version_no": "v1.1.0",
                "component": "frontend",
            },
        )
        assert upload_created.status_code == 201, upload_created.text
        upload_id = upload_created.json()["upload_id"]
        assert upload_created.json()["status"] == "created"
        assert upload_created.json()["part_count"] == 2
        chunk_size = upload_created.json()["chunk_size_bytes"]
        for part_no in range(2):
            part_content = resumable_package[
                part_no * chunk_size : (part_no + 1) * chunk_size
            ]
            part = client.put(
                f"/api/workspaces/v1/source-uploads/{upload_id}/parts/{part_no}",
                headers={
                    **headers,
                    "Content-SHA256": hashlib.sha256(part_content).hexdigest(),
                },
                content=part_content,
            )
            assert part.status_code == 200, part.text
        assert part.json()["progress"] == 1.0
        first_part = resumable_package[:chunk_size]
        part_replay = client.put(
            f"/api/workspaces/v1/source-uploads/{upload_id}/parts/0",
            headers={
                **headers,
                "Content-SHA256": hashlib.sha256(first_part).hexdigest(),
            },
            content=first_part,
        )
        assert part_replay.status_code == 200
        assert part_replay.json()["idempotent_replay"] is True
        init_replay = client.post(
            "/api/workspaces/v1/source-uploads",
            headers={**headers, "Idempotency-Key": "resumable-source-v1.1.0"},
            json={
                "filename": "resumable.zip",
                "content_type": "application/zip",
                "size_bytes": len(resumable_package),
                "sha256": resumable_digest,
                "version_no": "v1.1.0",
                "component": "frontend",
            },
        )
        assert init_replay.status_code == 201
        assert init_replay.json()["received_parts"] == [0, 1]
        completed_upload = client.post(
            f"/api/workspaces/v1/source-uploads/{upload_id}/complete",
            headers=headers,
            json={},
        )
        assert completed_upload.status_code == 202, completed_upload.text
        assert completed_upload.json()["status"] == "queued"
        assert RuntimeController(settings).run_once() is True
        verified_upload = client.get(
            f"/api/workspaces/v1/source-uploads/{upload_id}", headers=headers
        )
        assert verified_upload.status_code == 200
        assert verified_upload.json()["status"] == "verified"
        assert verified_upload.json()["source"]["artifact_sha256"] == resumable_digest
        assert client.get("/api/workspaces/v1/sources", headers=headers).json()["count"] == 2

        deployment = client.post(
            "/api/workspaces/v1/deployments",
            headers={**headers, "Idempotency-Key": "deploy-v1"},
            json={"source_version_id": source["uuid"], "component": "frontend"},
        )
        assert deployment.status_code == 202, deployment.text
        deployed = deployment.json()["deployment"]
        assert deployed["status"] == "queued"
        assert deployed["runtime_profile_key"] == "static.v1"
        assert deployed["runtime_claimed"] is False
        assert deployed["runtime_available"] is False
        repeated = client.post(
            "/api/workspaces/v1/deployments",
            headers={**headers, "Idempotency-Key": "deploy-v1"},
            json={"source_version_id": source["uuid"], "component": "frontend"},
        )
        assert repeated.status_code == 202
        assert repeated.json()["deployment"]["idempotent_replay"] is True
        observed = client.get(
            f"/api/workspaces/v1/deployments/{deployed['uuid']}",
            headers=headers,
        )
        assert observed.status_code == 200
        assert observed.json()["events"][0]["event_type"] == "requested"
        assert "internal_url" not in observed.text
        observed_by_legacy_id = client.get(
            f"/api/workspaces/v1/deployments/{deployed['id']}",
            headers=headers,
        )
        assert observed_by_legacy_id.status_code == 200
        assert observed_by_legacy_id.json()["deployment"]["uuid"] == deployed["uuid"]
        logs_by_legacy_id = client.get(
            f"/api/workspaces/v1/deployments/{deployed['id']}/logs",
            headers=headers,
        )
        assert logs_by_legacy_id.status_code == 200
        assert logs_by_legacy_id.json()["deployment_id"] == str(deployed["id"])

        monkeypatch.setattr(RuntimeController, "_wait_health", lambda *args, **kwargs: None)
        monkeypatch.setattr(RuntimeController, "_wait_public_route", lambda *args, **kwargs: None)
        controller = RuntimeController(settings)
        controller.heartbeat(successful=True)
        waiting = client.get(
            f"/api/workspaces/v1/deployments/{deployed['uuid']}",
            headers=headers,
        ).json()["deployment"]
        assert waiting["runtime_available"] is True
        assert waiting["runtime_provider_state"] == "online"
        assert waiting["runtime_claimed"] is False
        assert controller.run_once() is True
        ready = client.get(
            f"/api/workspaces/v1/deployments/{deployed['uuid']}",
            headers=headers,
        )
        assert ready.json()["deployment"]["status"] == "ready", ready.text
        assert ready.json()["deployment"]["health"] == "healthy"
        assert ready.json()["deployment"]["runtime_available"] is True
        assert ready.json()["deployment"]["runtime_claimed"] is True
        entry_path = provisioned.json()["workspace"]["entry_path"]
        assert entry_path == "/apps/workspace-deployment-app/"
        landing = client.get(entry_path)
        assert landing.status_code == 200
        assert landing.headers["x-warehouse-pages-site"] == "workspace-deployment-app"
        assert landing.headers["x-warehouse-pages-frame"] == (
            "https://workspace-deployment-app.bonfirework.org/"
        )
        fallback = client.get(provisioned.json()["workspace"]["fallback_path"])
        assert fallback.status_code == 200
        assert "Workspace Deployment" in fallback.text
        assert fallback.headers["x-warehouse-deployment"] == deployed["uuid"]

        unsafe = _source_zip({"../escape.txt": "blocked"})
        rejected = client.post(
            "/api/workspaces/v1/sources/upload",
            headers=headers,
            files={"file": ("unsafe.zip", unsafe, "application/zip")},
        )
        assert rejected.status_code == 422
    finally:
        with system_session() as session:
            session.execute(
                text(
                    "UPDATE platform.runtime_workers "
                    "SET status='draining', last_seen_at=now() - interval '1 hour' "
                    "WHERE worker_id=:worker"
                ),
                {"worker": getattr(locals().get("controller"), "worker_id", "")},
            )
        app.dependency_overrides.clear()


def test_workspace_key_runtime_contract_supports_api_web_worker_and_agent(
    tmp_path,
) -> None:
    actor = _actor("runtime-types")
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        hosted_runtime_data_root=tmp_path / "runtime",
        runtime_host_data_root=tmp_path / "runtime",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        provisioned = client.post(
            "/api/digital-assets/provision",
            json={
                "name": "Universal Runtime App",
                "asset_kind": "software",
                "workspace_key": "universal-runtime-app",
                "runtime_type": "static",
                "service_plan": "hosted",
            },
        )
        assert provisioned.status_code == 201, provisioned.text
        headers = {"Authorization": f"Bearer {provisioned.json()['api_key']}"}
        python_source = _source_zip(
            {
                "python-api/requirements.txt": "fastapi\nuvicorn\n",
                "python-api/app.py": (
                    "from fastapi import FastAPI\n"
                    "app = FastAPI()\n"
                    "@app.get('/health')\n"
                    "def health(): return {'ok': True}\n"
                ),
            }
        )
        uploaded = client.post(
            "/api/workspaces/v1/sources/upload",
            headers=headers,
            files={"file": ("python-api.zip", python_source, "application/zip")},
        )
        assert uploaded.status_code == 201, uploaded.text
        python_source_id = uploaded.json()["source"]["uuid"]

        credential = digital_asset_hosting.authenticate_workspace_key(
            provisioned.json()["api_key"],
            signing_secret=settings.integration_secret,
        )
        with pytest.raises(HTTPException) as stale_component:
            request_workspace_deployment(
                credential,
                {"source_version_id": python_source_id},
                idempotency_key=None,
                settings=settings,
            )
        assert stale_component.value.status_code == 409
        assert stale_component.value.detail["reason"] == "runtime_contract_mismatch"
        assert stale_component.value.detail["recommended_runtime_type"] == "api"

        incompatible = client.post(
            "/api/workspaces/v1/deployments",
            headers=headers,
            json={
                "runtime_type": "static",
                "source_version_id": python_source_id,
                "component": "frontend",
            },
        )
        assert incompatible.status_code == 422, incompatible.text
        assert incompatible.json()["detail"]["reason"] == "source_runtime_mismatch"

        automatic = client.post(
            "/api/workspaces/v1/deployments",
            headers={**headers, "Idempotency-Key": "auto-python-runtime"},
            json={"source_version_id": python_source_id},
        )
        assert automatic.status_code == 202, automatic.text
        automatic_payload = automatic.json()
        assert automatic_payload["auto_configured_runtime"] is True
        assert automatic_payload["runtime_contract"]["runtime_type"] == "api"
        assert automatic_payload["runtime_contract"]["runtime_family"] == "python"
        assert automatic_payload["runtime_contract"]["selection"] == "detected"
        assert automatic_payload["component"]["component_kind"] == "backend"
        assert automatic_payload["component"]["runtime"] == "python3.12"
        assert automatic_payload["component"]["entrypoint"] == "app.py"
        assert (
            automatic_payload["deployment"]["runtime_profile_key"]
            == (automatic_payload["runtime_contract"]["runtime_profile"])
        )
        assert automatic_payload["deployment"]["runtime_profile_key"] != "static.v1"

        staged = client.post(
            "/api/workspaces/v1/deployments",
            headers={**headers, "Idempotency-Key": "staged-python-runtime"},
            json={"source_version_id": python_source_id, "activate": False},
        )
        assert staged.status_code == 202, staged.text
        assert staged.json()["deployment"]["requested_config"]["activate"] is False
        assert staged.json()["deployment"]["requested_config"]["execution_mode"] == "service"

        job = client.post(
            "/api/workspaces/v1/jobs",
            headers={**headers, "Idempotency-Key": "python-migration-job"},
            json={
                "source_version_id": python_source_id,
                "command": "python -m compileall app.py",
            },
        )
        assert job.status_code == 202, job.text
        assert job.json()["component"]["component_kind"] == "worker"
        assert job.json()["job"]["requested_config"]["execution_mode"] == "job"
        assert job.json()["job"]["requested_config"]["activate"] is False
        for queued_id in (
            staged.json()["deployment"]["uuid"],
            job.json()["job"]["uuid"],
        ):
            cancelled = client.post(
                f"/api/workspaces/v1/deployments/{queued_id}/cancel",
                headers=headers,
            )
            assert cancelled.status_code == 200, cancelled.text

        repeated_automatic = client.post(
            "/api/workspaces/v1/deployments",
            headers={**headers, "Idempotency-Key": "auto-python-runtime"},
            json={"source_version_id": python_source_id},
        )
        assert repeated_automatic.status_code == 202, repeated_automatic.text
        assert repeated_automatic.json()["deployment"]["idempotent_replay"] is True
        assert (
            client.get("/api/workspaces/v1/info", headers=headers).json()["workspace"][
                "runtime_status"
            ]
            == "building"
        )

        with tenant_session(actor.tenant_id) as session:
            session.execute(
                text(
                    "UPDATE digital_asset.deployments "
                    "SET status='failed', health='unhealthy', "
                    "result=jsonb_build_object('error', "
                    "'Static Runtime requires index.html at the application root') "
                    "WHERE id=:deployment_id"
                ),
                {"deployment_id": automatic_payload["deployment"]["uuid"]},
            )
            session.execute(
                text(
                    "UPDATE digital_asset.workspaces SET runtime_status='failed' "
                    "WHERE id=:workspace_id"
                ),
                {"workspace_id": provisioned.json()["workspace"]["uuid"]},
            )
        failed_entry = client.get(provisioned.json()["workspace"]["fallback_path"])
        assert failed_entry.status_code == 200
        assert "部署失敗，入口仍保留" in failed_entry.text
        assert "源碼與 Runtime 不相容" in failed_entry.text

        api_runtime = client.put(
            "/api/workspaces/v1/runtime",
            headers=headers,
            json={
                "runtime_type": "auto",
                "source_version_id": python_source_id,
                "component": "api",
            },
        )
        assert api_runtime.status_code == 200, api_runtime.text
        assert api_runtime.json()["runtime"]["runtime_type"] == "api"
        assert api_runtime.json()["runtime"]["runtime_family"] == "python"
        assert api_runtime.json()["component"]["entrypoint"] == "app.py"

        for runtime_type in ("worker", "agent"):
            configured = client.put(
                "/api/workspaces/v1/runtime",
                headers=headers,
                json={
                    "runtime_type": runtime_type,
                    "runtime": "python3.12",
                    "source_version_id": python_source_id,
                    "component": runtime_type,
                    "entrypoint": "app.py",
                },
            )
            assert configured.status_code == 200, configured.text
            assert configured.json()["runtime"]["runtime_type"] == runtime_type
            assert configured.json()["component"]["component_kind"] == runtime_type

        node_source = _source_zip(
            {
                "node-web/package.json": (
                    '{"scripts":{"start":"node server.js"},"dependencies":{"express":"latest"}}'
                ),
                "node-web/server.js": (
                    "const express=require('express'); const app=express(); "
                    "app.get('/health',(_,r)=>r.json({ok:true})); "
                    "app.listen(process.env.PORT||8080);"
                ),
            }
        )
        node_upload = client.post(
            "/api/workspaces/v1/sources/upload",
            headers=headers,
            files={"file": ("node-web.zip", node_source, "application/zip")},
        )
        assert node_upload.status_code == 201, node_upload.text
        web_runtime = client.put(
            "/api/workspaces/v1/runtime",
            headers=headers,
            json={
                "runtime_type": "web",
                "source_version_id": node_upload.json()["source"]["uuid"],
                "component": "web",
            },
        )
        assert web_runtime.status_code == 200, web_runtime.text
        assert web_runtime.json()["runtime"]["runtime_family"] == "node"
        assert web_runtime.json()["component"]["entrypoint"] == "server.js"
    finally:
        app.dependency_overrides.clear()


def test_intelligent_hosting_workspace_key_reaches_healthy_runtime(tmp_path, monkeypatch) -> None:
    actor = _actor("intelligent-hosting")
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        hosted_runtime_data_root=tmp_path / "runtime",
        runtime_host_data_root=tmp_path / "runtime",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    controller: RuntimeController | None = None
    try:
        provisioned = client.post(
            "/api/digital-assets/provision",
            json={
                "name": "Intelligent Hosting App",
                "asset_kind": "software",
                "workspace_key": "intelligent-hosting-app",
                "runtime_type": "static",
                "service_plan": "hosted",
                "no_database": True,
            },
        )
        assert provisioned.status_code == 201, provisioned.text
        headers = {"Authorization": f"Bearer {provisioned.json()['api_key']}"}
        created = client.post(
            "/api/hosting/v2/sessions",
            headers=headers,
            json={
                "message": "Deploy this application and return its verified URL",
                "client_kind": "terminal_ai",
                "desired_state": {
                    "runtime": {"type": "auto"},
                    "deployment": {
                        "state": "ready",
                        "activate_when_healthy": True,
                    },
                },
            },
        )
        assert created.status_code == 201, created.text
        session_id = created.json()["session"]["id"]
        assert created.json()["session"]["status"] == "awaiting_source"
        assert created.json()["session"]["plan"]["required_input"]["kind"] == ("source_archive")

        package = _source_zip(
            {"site/index.html": "<!doctype html><title>Intelligent Hosting</title>"}
        )
        uploaded = client.post(
            f"/api/hosting/v2/sessions/{session_id}/sources",
            headers={
                **headers,
                "Content-SHA256": hashlib.sha256(package).hexdigest(),
            },
            files={"file": ("site.zip", package, "application/zip")},
            data={"version_no": "v1.0.0", "component": "frontend"},
        )
        assert uploaded.status_code == 201, uploaded.text
        assert uploaded.json()["session"]["status"] == "planning"
        attached = client.post(
            f"/api/hosting/v2/sessions/{session_id}/sources/attach",
            headers=headers,
            json={
                "source_version_id": uploaded.json()["source"]["source"]["uuid"]
            },
        )
        assert attached.status_code == 200, attached.text
        assert attached.json()["session"]["status"] == "planning"

        session_package = _source_zip(
            {"index.html": "<!doctype html><title>Session resumable source</title>"}
        )
        session_digest = hashlib.sha256(session_package).hexdigest()
        session_upload = client.post(
            f"/api/hosting/v2/sessions/{session_id}/source-uploads",
            headers={**headers, "Idempotency-Key": "session-resumable-v1.1.0"},
            json={
                "filename": "session-source.zip",
                "content_type": "application/zip",
                "size_bytes": len(session_package),
                "sha256": session_digest,
                "version_no": "v1.1.0",
                "component": "frontend",
            },
        )
        assert session_upload.status_code == 201, session_upload.text
        session_upload_id = session_upload.json()["upload_id"]
        session_part = client.put(
            (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/"
                f"{session_upload_id}/parts/0"
            ),
            headers={**headers, "Content-SHA256": session_digest},
            content=session_package,
        )
        assert session_part.status_code == 200, session_part.text
        session_complete = client.post(
            (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/"
                f"{session_upload_id}/complete"
            ),
            headers=headers,
            json={},
        )
        assert session_complete.status_code == 202, session_complete.text
        assert RuntimeController(settings).run_once() is True
        session_verified = client.get(
            (
                f"/api/hosting/v2/sessions/{session_id}/source-uploads/"
                f"{session_upload_id}"
            ),
            headers=headers,
        )
        assert session_verified.status_code == 200
        assert session_verified.json()["status"] == "verified"
        session_attached = client.post(
            f"/api/hosting/v2/sessions/{session_id}/sources/attach",
            headers=headers,
            json={
                "source_version_id": session_verified.json()["source"]["uuid"]
            },
        )
        assert session_attached.status_code == 200, session_attached.text

        started = client.post(
            f"/api/hosting/v2/sessions/{session_id}/messages",
            headers=headers,
            json={
                "message": "Source is attached; continue to healthy",
                "desired_state": {
                    "runtime": {"type": "auto"},
                    "deployment": {"state": "ready"},
                },
                "execute": True,
            },
        )
        assert started.status_code == 200, started.text
        assert started.json()["session"]["status"] == "running"
        execution = started.json()["session"]["state"]["execution"]
        assert execution["runtime"]["runtime_type"] == "static"
        assert execution["deployment"]["status"] == "queued"

        monkeypatch.setattr(RuntimeController, "_wait_health", lambda *args, **kwargs: None)
        monkeypatch.setattr(RuntimeController, "_wait_public_route", lambda *args, **kwargs: None)
        controller = RuntimeController(settings)
        controller.heartbeat(successful=True)
        assert controller.run_once() is True

        completed = client.get(f"/api/hosting/v2/sessions/{session_id}", headers=headers)
        assert completed.status_code == 200, completed.text
        assert completed.json()["session"]["status"] == "completed"
        assert completed.json()["session"]["current_stage"] == "ready"
        deployment_rows = completed.json()["session"]["state"]["deployments"]
        latest = deployment_rows["deployments"][0]
        assert latest["status"] == "ready"
        assert latest["health"] == "healthy"
        assert latest["verified_application_url"].endswith(
            f"/assets/{actor.tenant_slug}/intelligent-hosting-app/"
        )
        events = client.get(f"/api/hosting/v2/sessions/{session_id}/events", headers=headers)
        assert events.status_code == 200
        event_types = [event["event_type"] for event in events.json()["events"]]
        assert event_types[:3] == ["understood", "observed", "plan"]
        assert "step_succeeded" in event_types
        assert event_types[-1] == "ready"
    finally:
        if controller is not None:
            with system_session() as session:
                session.execute(
                    text(
                        """
                        UPDATE platform.runtime_workers
                        SET status='draining', last_seen_at=now() - interval '1 day'
                        WHERE worker_id=:worker
                        """
                    ),
                    {"worker": controller.worker_id},
                )
        app.dependency_overrides.clear()


def test_full_stack_workspace_database_key_and_deployment_round_trip(tmp_path) -> None:
    actor = _actor("roundtrip")
    settings = Settings(
        asset_storage_root=tmp_path / "digital-assets",
        asset_code_ssd_root=tmp_path / "digital-assets-code-ssd",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    sha256 = "a" * 64
    try:
        created = client.post(
            "/api/digital-assets/create",
            json={
                "name": "Customer Operations Application",
                "asset_kind": "software",
                "summary": "Frontend, API and portable database",
                "tags": ["full-stack", "customer"],
            },
        )
        assert created.status_code == 201
        asset = created.json()["asset"]
        assert isinstance(asset["id"], int)
        assert asset["uuid"]

        version = client.post(
            f"/api/digital-assets/{asset['id']}/version",
            json={
                "version_no": "v1.0.0",
                "artifact_uri": "git://customer/app",
                "artifact_hash": sha256,
            },
        )
        assert version.status_code == 200
        assert version.json()["version"]["artifact_hash"] == sha256

        artifact = client.post(
            f"/api/digital-assets/{asset['id']}/artifacts",
            json={
                "artifact_kind": "source",
                "artifact_uri": "s3://custody/customer-app.tar.zst",
                "artifact_hash": sha256,
                "size_bytes": 2048,
            },
        )
        assert artifact.status_code == 200
        custody = artifact.json()["custody_event"]
        assert custody["event_type"] == "deposit"
        assert custody["event_hash"]

        uploaded = client.post(
            f"/api/digital-assets/{asset['id']}/artifacts/upload",
            data={"artifact_kind": "backend", "expected_sha256": sha256},
            files={"file": ("main.py", b"a" * 64, "text/x-python")},
        )
        actual_sha256 = "ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb"
        assert uploaded.status_code == 422
        uploaded = client.post(
            f"/api/digital-assets/{asset['id']}/artifacts/upload",
            data={"artifact_kind": "backend", "expected_sha256": actual_sha256},
            files={"file": ("main.py", b"a" * 64, "text/x-python")},
        )
        assert uploaded.status_code == 200
        stored_artifact = uploaded.json()["artifact"]
        assert stored_artifact["state"] == "verified"
        assert stored_artifact["storage_provider"] == "content_addressed_hdd"
        assert stored_artifact["storage_role"] == "code"
        assert stored_artifact["storage_pool_key"] == "hosted-hdd-01"
        downloaded = client.get(
            f"/api/digital-assets/{asset['id']}/artifacts/{stored_artifact['id']}/download"
        )
        assert downloaded.status_code == 200
        assert downloaded.content == b"a" * 64

        workspace_response = client.post(
            f"/api/digital-assets/{asset['id']}/workspace",
            json={
                "workspace_key": "customer-operations",
                "runtime_type": "api",
                "service_plan": "hosted",
            },
        )
        assert workspace_response.status_code == 200
        provisioned = workspace_response.json()
        workspace = provisioned["workspace"]
        assert {item["component_kind"] for item in provisioned["components"]} == {
            "frontend",
            "backend",
        }
        assert provisioned["database"]["provider_key"] == "warehouse_postgresql_data_api"
        assert provisioned["database"]["status"] == "ready"
        assert workspace["database_uri"] is None
        assert workspace["storage_quota_bytes"] == 512 * 1024 * 1024
        assert workspace["storage"]["code"]["medium"] == "hdd"
        assert workspace["storage"]["code"]["selection"] == "default"
        assert workspace["storage"]["data"]["medium"] == "hdd"
        assert provisioned["storage"]["data_storage_enforced"] == "hdd"
        assert workspace["entry_path"] == "/apps/customer-operations/"
        assert workspace["entry_url"].endswith("/apps/customer-operations/")

        landing = client.get(workspace["entry_path"])
        assert landing.status_code == 200
        assert landing.headers["x-warehouse-pages-site"] == "customer-operations"
        fallback = client.get(workspace["fallback_path"])
        assert fallback.status_code == 200
        assert "Customer Operations Application" in fallback.text
        assert "512 MB" in fallback.text
        assert "等待上傳源碼" not in fallback.text

        resized = client.post(
            f"/api/digital-assets/{asset['asset_no']}/workspace-quota",
            json={"workspace_ref": workspace["workspace_key"], "delta_mb": 512},
        )
        assert resized.status_code == 200
        assert resized.json()["quota"]["after_mb"] == 1024
        assert resized.json()["quota"]["increase_mb"] == 512
        invalid_resize = client.post(
            f"/api/digital-assets/{asset['asset_no']}/workspace-quota",
            json={"workspace_ref": workspace["workspace_key"], "delta_mb": 256},
        )
        assert invalid_resize.status_code == 422
        assert invalid_resize.json()["detail"]["required_delta_mb"] == 512

        written = client.put(
            f"/api/workspaces/{workspace['id']}/data/customers/acme",
            params={"expected_version": 0},
            json={"name": "Acme", "active": True},
        )
        assert written.status_code == 200
        assert written.json()["record"]["version"] == 1

        updated = client.put(
            f"/api/workspaces/{workspace['id']}/data/customers/acme",
            params={"expected_version": 1},
            json={"name": "Acme", "active": False},
        )
        assert updated.status_code == 200
        assert updated.json()["record"]["version"] == 2

        conflict = client.put(
            f"/api/workspaces/{workspace['id']}/data/customers/acme",
            params={"expected_version": 1},
            json={"name": "Stale update"},
        )
        assert conflict.status_code == 409

        schema = client.get(f"/api/workspaces/{workspace['id']}/database/schema")
        assert schema.status_code == 200
        assert schema.json()["collections"][0]["name"] == "customers"
        assert schema.json()["collections"][0]["records"] == 1

        primary = client.post(
            f"/api/workspaces/{workspace['id']}/keys/primary/rotate",
            json={"label": "Workspace owner"},
        )
        assert primary.status_code == 200
        assert primary.json()["key_kind"] == "primary"

        issued = client.post(
            f"/api/workspaces/{workspace['id']}/keys",
            json={
                "label": "Customer API runtime",
                "scopes": ["workspace:read", "data:read", "data:write"],
            },
        )
        assert issued.status_code == 200
        assert issued.json()["key_kind"] == "delegated"
        assert issued.json()["parent_credential_id"] == primary.json()["credential_id"]
        workspace_key = issued.json()["api_key"]
        assert workspace_key.startswith("wak_")
        headers = {"Authorization": f"Bearer {workspace_key}"}

        info = client.get("/api/workspaces/v1/info", headers=headers)
        assert info.status_code == 200
        assert info.json()["workspace"]["workspace_key"] == "customer-operations"

        external_write = client.put(
            "/api/workspaces/v1/data/orders/order-1",
            headers=headers,
            params={"expected_version": 0},
            json={"total": 125, "currency": "CNY"},
        )
        assert external_write.status_code == 200
        external_list = client.get(
            "/api/workspaces/v1/data/orders",
            headers=headers,
        )
        assert external_list.status_code == 200
        assert external_list.json()["records"][0]["data"]["total"] == 125

        deployment = client.post(
            f"/api/digital-assets/{asset['id']}/deploy",
            json={
                "workspace_id": workspace["id"],
                "deploy_type": "api",
                "runtime": "python3.12",
            },
        )
        assert deployment.status_code == 200
        deployment_payload = deployment.json()["deployment"]
        assert deployment_payload["status"] == "queued"
        assert deployment_payload["runtime_available"] is False
        assert deployment_payload["next_action"] == "runtime_worker_claim"

        listed = client.get("/api/digital-assets")
        assert listed.status_code == 200
        assert listed.json()["source"] == "digital_asset_postgresql"
        assert listed.json()["assets"][0]["workspace"]["workspace_key"] == ("customer-operations")
        assert listed.json()["assets"][0]["workspace"]["entry_url"].endswith(
            "/apps/customer-operations/"
        )
        assert listed.json()["assets"][0]["workspace"]["storage_quota_mb"] == 1024

        runtime_layers = build_context_layers(
            actor,
            "Inspect and maintain the customer application",
            surface="test",
            conversation_id=None,
        )
        hosting_world = runtime_layers["L1_current_company_and_people"]["hosted_application_world"]
        assert hosting_world["totals"]["workspaces"] == 1
        assert hosting_world["workspaces"][0]["workspace_key"] == "customer-operations"
        assert hosting_world["workspaces"][0]["databases"][0]["portable_data_api"] is True
        assert hosting_world["storage_policy"]["default_code_storage"] == "hdd"
        assert hosting_world["storage_policy"]["ssd_requires_explicit_intent"] is True
        assert hosting_world["storage_pools"]
        assert "token_hash" not in str(hosting_world)

        detail = client.get(f"/api/digital-assets/{asset['uuid']}")
        assert detail.status_code == 200
        assert detail.json()["asset"]["workspaces"][0]["databases"][0]["status"] == "ready"
    finally:
        app.dependency_overrides.clear()


def test_core_code_can_explicitly_use_ssd_while_data_stays_on_hdd(tmp_path) -> None:
    actor = _actor("storage-tier")
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "Performance API", "asset_kind": "software"},
        ).json()["asset"]
        workspace = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={
                "workspace_key": "performance-api",
                "runtime_type": "api",
                "code_storage": "ssd",
            },
        )
        assert workspace.status_code == 200
        profile = workspace.json()["storage"]
        assert profile["code"]["medium"] == "ssd"
        assert profile["code"]["selection"] == "explicit"
        assert profile["data"]["medium"] == "hdd"

        source = client.post(
            f"/api/digital-assets/{asset['uuid']}/artifacts/upload",
            data={"artifact_kind": "source"},
            files={"file": ("app.py", b"print('ok')", "text/x-python")},
        )
        assert source.status_code == 200
        assert source.json()["artifact"]["storage_provider"] == "content_addressed_ssd"
        assert any((tmp_path / "ssd").rglob(source.json()["artifact"]["sha256"]))

        data = client.post(
            f"/api/digital-assets/{asset['uuid']}/artifacts/upload",
            data={"artifact_kind": "dataset"},
            files={"file": ("rows.json", b"[]", "application/json")},
        )
        assert data.status_code == 200
        assert data.json()["artifact"]["storage_provider"] == "content_addressed_hdd"
        assert data.json()["artifact"]["storage_role"] == "data"
        assert any((tmp_path / "hdd").rglob(data.json()["artifact"]["sha256"]))

        rejected = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "another-api", "data_storage": "ssd"},
        )
        assert rejected.status_code == 422

        pools = client.get("/api/storage/v1/pools")
        assert pools.status_code == 200
        assert pools.json()["default_code_storage"] == "hdd"
        assert pools.json()["data_storage_enforced"] == "hdd"
        assert {pool["medium"] for pool in pools.json()["pools"]} == {"hdd", "ssd"}
    finally:
        app.dependency_overrides.clear()


def test_empty_workspace_can_switch_code_disk_in_place_until_source_exists(
    tmp_path,
) -> None:
    actor = _actor("empty-storage-switch")
    settings = Settings(
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
    )
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "Disk Flexible App", "asset_kind": "software"},
        ).json()["asset"]
        created = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "disk-flexible-app", "runtime_type": "web"},
        )
        assert created.status_code == 200, created.text
        original = created.json()["workspace"]
        assert created.json()["storage"]["code"]["medium"] == "hdd"

        switched = client.post(
            "/api/workspaces/disk-flexible-app/storage",
            json={
                "code_storage": "ssd",
                "expected_revision": original["revision"],
            },
        )
        assert switched.status_code == 200, switched.text
        switched_payload = switched.json()
        assert switched_payload["changed"] is True
        assert switched_payload["workspace"]["uuid"] == original["uuid"]
        assert switched_payload["workspace"]["workspace_key"] == original["workspace_key"]
        assert switched_payload["workspace"]["revision"] == original["revision"] + 1
        assert switched_payload["workspace"]["storage"]["code"]["medium"] == "ssd"
        assert switched_payload["workspace"]["storage"]["data"]["medium"] == "hdd"
        assert switched_payload["code_storage"] == {
            "from": "hdd",
            "to": "ssd",
            "physical_copy_required": False,
        }
        assert switched_payload["workspace"]["code_storage_switchable"] is True
        assert (
            switched_payload["world_observation"]["verified_facts"]["new_workspace_created"]
            is False
        )

        repeated = client.post(
            "/api/workspaces/disk-flexible-app/storage",
            json={"code_storage": "ssd"},
        )
        assert repeated.status_code == 200
        assert repeated.json()["changed"] is False

        ai_switched_to_hdd = executor.execute_runtime_tool_call(
            actor,
            "digital_market_workspace_storage_switch",
            {
                "workspace": "disk-flexible-app",
                "code-storage": "hdd",
                "expected-revision": repeated.json()["workspace"]["revision"],
            },
        )
        assert ai_switched_to_hdd["status"] == "confirmation_required", ai_switched_to_hdd
        assert ai_switched_to_hdd["data"]["confirmation_policy"] == {
            "mode": "passkey",
            "adapter": "staged_action",
        }
        ai_switched_to_ssd = executor.execute_runtime_tool_call(
            actor,
            "digital_market_workspace_storage_switch",
            {"workspace": "disk-flexible-app", "code-storage": "ssd"},
        )
        assert ai_switched_to_ssd["status"] == "confirmation_required", ai_switched_to_ssd

        unchanged_after_unverified_ai_calls = client.get("/api/digital-assets?limit=300")
        guarded_workspace = next(
            item["workspace"]
            for item in unchanged_after_unverified_ai_calls.json()["assets"]
            if item["uuid"] == asset["uuid"]
        )
        assert guarded_workspace["storage"]["code"]["medium"] == "ssd"

        listed = client.get("/api/digital-assets?limit=300")
        listed_workspace = next(
            item["workspace"] for item in listed.json()["assets"] if item["uuid"] == asset["uuid"]
        )
        assert listed_workspace["code_storage_switchable"] is True
        assert listed_workspace["source_available"] is False
        assert listed_workspace["code_artifact_count"] == 0

        source = client.post(
            f"/api/digital-assets/{asset['uuid']}/artifacts/upload",
            data={"artifact_kind": "source"},
            files={"file": ("app.py", b"print('ready')", "text/x-python")},
        )
        assert source.status_code == 200, source.text
        assert source.json()["artifact"]["storage_provider"] == "content_addressed_ssd"

        blocked = client.post(
            "/api/workspaces/disk-flexible-app/storage",
            json={"code_storage": "hdd"},
        )
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["reason"] == "code_storage_migration_required"
        assert blocked.json()["detail"]["direct_switch_allowed"] is False
        assert blocked.json()["detail"]["code_artifact_count"] == 1

        refreshed = client.get("/api/digital-assets?limit=300")
        refreshed_workspace = next(
            item["workspace"]
            for item in refreshed.json()["assets"]
            if item["uuid"] == asset["uuid"]
        )
        assert refreshed_workspace["storage"]["code"]["medium"] == "ssd"
        assert refreshed_workspace["storage"]["data"]["medium"] == "hdd"
        assert refreshed_workspace["source_available"] is True
        assert refreshed_workspace["code_storage_switchable"] is False

        command = legacy_catalog.entry_by_tool_name("digital_market_workspace_storage_switch")
        assert command["api_path"] == "/api/workspaces/{workspace_ref}/storage"
        assert command["semantic_contract"]["effect"] == "update_if_empty"
        assert legacy_catalog.confirmation_contract(command) == {
            "mode": "passkey",
            "adapter": "staged_action",
        }
        assert legacy_catalog.ai_confirmation_required(command) is True
        schema = legacy_catalog.tool_schema(command)
        assert schema["function"]["parameters"]["properties"]["code-storage"]["enum"] == [
            "hdd",
            "ssd",
        ]
    finally:
        app.dependency_overrides.clear()


def test_workspace_database_uses_dedicated_hdd_provider_and_shared_quota(
    monkeypatch,
) -> None:
    migration_url = os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    admin_source = (
        os.environ.get("WAREHOUSE_TEST_HOSTED_DATABASE_ADMIN_URL")
        or os.environ.get("WAREHOUSE_HOSTED_DATABASE_ADMIN_URL")
        or migration_url
    )
    admin_url = make_url(admin_source).set(drivername="postgresql", database="postgres")
    settings = Settings(
        hosted_database_admin_url=SecretStr(admin_url.render_as_string(hide_password=False)),
        integration_secret="hosted-database-test-secret-" + "x" * 32,
    )
    monkeypatch.setattr(hosted_database, "get_settings", lambda: settings)
    monkeypatch.setattr(digital_asset_hosting, "get_settings", lambda: settings)
    actor = _actor("hosted-database")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    database_ref = None
    role_ref = None
    runtime_role_ref = None
    backup_role_ref = None
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "HDD Data App", "asset_kind": "software"},
        ).json()["asset"]
        created = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={"workspace_key": "hdd-data-app", "runtime_type": "api"},
        )
        assert created.status_code == 200, created.text
        workspace = created.json()["workspace"]
        database = created.json()["database"]
        database_ref = database["database_ref"]
        role_ref = database["role_ref"]
        runtime_role_ref = database["runtime_role_ref"]
        backup_role_ref = database["backup_role_ref"]
        assert runtime_role_ref == f"wha_{workspace['uuid'].replace('-', '')}"
        assert backup_role_ref == f"whb_{workspace['uuid'].replace('-', '')}"
        assert database["provider_key"] == hosted_database.HDD_DATABASE_PROVIDER_KEY
        assert database["pool_key"] == hosted_database.HDD_DATABASE_POOL_KEY
        assert database["physical_medium"] == "hdd"
        assert database["isolation_mode"] == "dedicated_database"
        assert database["capabilities"]["vector_extension"] is True
        assert "password" not in json.dumps(database).lower()

        listed_assets = client.get("/api/digital-assets?limit=300")
        assert listed_assets.status_code == 200
        listed_workspace = next(
            item["workspace"]
            for item in listed_assets.json()["assets"]
            if item["uuid"] == asset["uuid"]
        )
        assert {
            "code_bytes",
            "source_archive_bytes",
            "runtime_bytes",
            "runtime_release_bytes",
            "data_bytes",
            "managed_data_object_bytes",
            "data_volume_bytes",
            "database_bytes",
            "postgresql_bytes",
            "total_bytes",
            "measured_at",
        }.issubset(listed_workspace)
        assert listed_workspace["total_bytes"] == listed_workspace["storage_used_bytes"]

        written = client.put(
            f"/api/workspaces/{workspace['uuid']}/data/questions/q-1",
            params={"expected_version": 0},
            json={"question": "2 + 2", "answer": 4},
        )
        assert written.status_code == 200, written.text
        listed = client.get(f"/api/workspaces/{workspace['uuid']}/data/questions")
        assert listed.status_code == 200
        assert listed.json()["records"][0]["data"]["answer"] == 4

        landing = client.get(workspace["fallback_path"])
        assert landing.status_code == 200
        assert "DB HDD" in landing.text
        usage_match = re.search(r"([0-9]+\.[0-9]{2}) / 512 MB", landing.text)
        assert usage_match is not None
        assert float(usage_match.group(1)) > 0

        with tenant_session(actor.tenant_id) as session:
            runtime_url = make_url(
                hosted_database.runtime_database_url(
                    session,
                    workspace["uuid"],
                    settings=settings,
                )
            )
            assert runtime_url.database == database_ref
            assert runtime_url.username == runtime_role_ref
            assert runtime_url.password
            with psycopg.connect(runtime_url.render_as_string(hide_password=False)) as connection:
                assert connection.execute(
                    "SELECT extversion FROM pg_extension WHERE extname='vector'"
                ).fetchone()[0]
                assert connection.execute(
                    "SELECT payload->>'answer' FROM app.workspace_records "
                    "WHERE collection_name='questions' AND record_key='q-1'"
                ).fetchone()[0] == "4"
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    connection.execute("CREATE TABLE app.runtime_must_not_own(id integer)")
            migration_runtime_url = make_url(
                hosted_database.migration_database_url(
                    session,
                    workspace["uuid"],
                    settings=settings,
                )
            )
            assert migration_runtime_url.database == database_ref
            assert migration_runtime_url.username == role_ref
            with psycopg.connect(
                admin_url.render_as_string(hide_password=False)
            ) as connection:
                runtime_role = connection.execute(
                    """
                    SELECT role.rolsuper,role.rolcreatedb,role.rolcreaterole,
                           role.rolreplication,role.rolbypassrls,
                           pg_get_userbyid(database.datdba)=role.rolname AS database_owner
                    FROM pg_roles AS role
                    JOIN pg_database AS database ON database.datname=%s
                    WHERE role.rolname=%s
                    """,
                    (database_ref, runtime_role_ref),
                ).fetchone()
            assert runtime_role is not None
            assert not any(runtime_role)
            assert (
                session.execute(
                    text(
                        """
                    SELECT count(*) FROM digital_asset.workspace_records
                    WHERE workspace_id = :workspace_id
                    """
                    ),
                    {"workspace_id": workspace["uuid"]},
                ).scalar_one()
                == 0
            )
            usage = (
                session.execute(
                    text(
                        """
                    SELECT database_bytes, total_billable_bytes
                    FROM digital_asset.workspace_usage
                    WHERE workspace_id = :workspace_id
                    """
                    ),
                    {"workspace_id": workspace["uuid"]},
                )
                .mappings()
                .one()
            )
            assert usage["database_bytes"] > 0
            assert usage["total_billable_bytes"] >= usage["database_bytes"]
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces SET storage_quota_bytes = 1
                    WHERE id = :workspace_id
                    """
                ),
                {"workspace_id": workspace["uuid"]},
            )
        rejected = client.put(
            f"/api/workspaces/{workspace['uuid']}/data/questions/q-2",
            json={"question": "quota"},
        )
        assert rejected.status_code == 507
        assert rejected.json()["detail"]["reason"] == "workspace_quota_exceeded"
    finally:
        app.dependency_overrides.clear()
        if database_ref and role_ref and runtime_role_ref:
            with psycopg.connect(
                admin_url.render_as_string(hide_password=False), autocommit=True
            ) as connection:
                connection.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                    (database_ref,),
                )
                connection.execute(
                    psycopg.sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        psycopg.sql.Identifier(database_ref)
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(runtime_role_ref)
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(backup_role_ref)
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(role_ref)
                    )
                )


def test_external_postgresql_binding_drives_runtime_and_relational_data_api(
    monkeypatch,
) -> None:
    migration_source = os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    admin_url = make_url(migration_source).set(drivername="postgresql", database="postgres")
    suffix = uuid4().hex[:12]
    database_ref = f"warehouse_external_{suffix}"
    role_ref = f"warehouse_external_role_{suffix}"
    password = f"external-test-{suffix}"
    external_url = admin_url.set(
        database=database_ref,
        username=role_ref,
        password=password,
        query={"sslmode": "disable"},
    )
    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(
            psycopg.sql.SQL(
                "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION PASSWORD {}"
            ).format(psycopg.sql.Identifier(role_ref), psycopg.sql.Literal(password))
        )
        connection.execute(
            psycopg.sql.SQL("CREATE DATABASE {} OWNER {}")
            .format(psycopg.sql.Identifier(database_ref), psycopg.sql.Identifier(role_ref))
        )
    with psycopg.connect(external_url.render_as_string(hide_password=False)) as connection:
        connection.execute(
            """
            CREATE TABLE public.orders (
              id text PRIMARY KEY,
              total integer NOT NULL,
              metadata jsonb NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )

    settings = Settings(
        external_database_allow_private_hosts=True,
        external_database_require_tls=False,
        integration_secret="external-database-test-secret-" + "x" * 32,
    )
    monkeypatch.setattr(hosted_database, "get_settings", lambda: settings)
    monkeypatch.setattr(digital_asset_hosting, "get_settings", lambda: settings)
    actor = _actor("external-database")
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "External Data App", "asset_kind": "software"},
        ).json()["asset"]
        created = client.post(
            f"/api/digital-assets/{asset['uuid']}/workspace",
            json={
                "workspace_key": "external-data-app",
                "runtime_type": "api",
                "database_name": "customer_data",
                "provider": "external_postgresql",
                "database_url": external_url.render_as_string(hide_password=False),
                "is_default": False,
            },
        )
        assert created.status_code == 200, created.text
        workspace = created.json()["workspace"]
        database = created.json()["database"]
        assert database["provider_key"] == hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
        assert database["ownership_mode"] == "customer_managed"
        assert database["is_default"] is True
        assert database["isolation_mode"] == "external_database"
        assert database["capabilities"]["relational_data_api"] is True
        public_payload = json.dumps(created.json()).lower()
        assert password.lower() not in public_payload
        assert "database_url" not in public_payload

        with tenant_session(actor.tenant_id) as session:
            runtime_url = make_url(
                hosted_database.runtime_database_url(
                    session,
                    workspace["uuid"],
                    settings=settings,
                )
            )
            assert runtime_url.database == database_ref
            assert runtime_url.username == role_ref
            migration_runtime_url = make_url(
                hosted_database.migration_database_url(
                    session,
                    workspace["uuid"],
                    settings=settings,
                )
            )
            assert migration_runtime_url == runtime_url
            credential = (
                session.execute(
                    text(
                        """
                        SELECT credential_kind,secret_ciphertext,last_validated_at
                        FROM digital_asset.database_credentials
                        WHERE database_binding_id=:database_id
                        """
                    ),
                    {"database_id": database["id"]},
                )
                .mappings()
                .one()
            )
            assert credential["credential_kind"] == "external_dsn"
            assert str(credential["secret_ciphertext"]).startswith("fernet:v1:")
            assert password not in str(credential["secret_ciphertext"])
            assert credential["last_validated_at"] is not None

        schema = client.get(f"/api/workspaces/{workspace['uuid']}/database/schema")
        assert schema.status_code == 200, schema.text
        assert schema.json()["collections"] == []
        orders = next(table for table in schema.json()["tables"] if table["name"] == "orders")
        assert orders["schema"] == "public"
        assert orders["primary_key"] == ["id"]
        assert {column["name"] for column in orders["columns"]} == {
            "id",
            "total",
            "metadata",
        }

        inserted = client.put(
            f"/api/workspaces/{workspace['uuid']}/database/tables/public/orders/rows/order-1",
            params={"expected_version": "0"},
            json={"total": 125, "metadata": {"currency": "CNY"}},
        )
        assert inserted.status_code == 200, inserted.text
        first_version = inserted.json()["record"]["version"]
        assert inserted.json()["record"]["data"]["total"] == 125

        stale = client.put(
            f"/api/workspaces/{workspace['uuid']}/database/tables/public/orders/rows/order-1",
            params={"expected_version": "0"},
            json={"total": 126},
        )
        assert stale.status_code == 409
        updated = client.put(
            f"/api/workspaces/{workspace['uuid']}/database/tables/public/orders/rows/order-1",
            params={"expected_version": first_version},
            json={"total": 126},
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["record"]["data"]["total"] == 126

        listed = client.get(
            f"/api/workspaces/{workspace['uuid']}/database/tables/public/orders/rows"
        )
        assert listed.status_code == 200, listed.text
        assert listed.json()["rows"][0]["key"] == "order-1"
        assert listed.json()["rows"][0]["data"]["metadata"]["currency"] == "CNY"

        primary = client.post(
            f"/api/workspaces/{workspace['uuid']}/keys/primary/rotate",
            json={"label": "External database runtime"},
        )
        assert primary.status_code == 200, primary.text
        workspace_headers = {"Authorization": f"Bearer {primary.json()['api_key']}"}
        customer_rows = client.get(
            "/api/workspaces/v1/database/tables/public/orders/rows",
            headers=workspace_headers,
        )
        assert customer_rows.status_code == 200, customer_rows.text
        assert customer_rows.json()["rows"][0]["key"] == "order-1"
        customer_insert = client.put(
            "/api/workspaces/v1/database/tables/public/orders/rows/order-2",
            headers=workspace_headers,
            params={"expected_version": "0"},
            json={"total": 200, "metadata": {"currency": "USD"}},
        )
        assert customer_insert.status_code == 200, customer_insert.text
        customer_health = client.get(
            "/api/workspaces/v1/database/health",
            headers=workspace_headers,
        )
        assert customer_health.status_code == 200, customer_health.text
        assert customer_health.json()["health"]["provider_key"] == (
            hosted_database.EXTERNAL_POSTGRESQL_PROVIDER_KEY
        )

        collections = client.get(f"/api/workspaces/{workspace['uuid']}/data/orders")
        assert collections.status_code == 409
        assert (
            collections.json()["detail"]["reason"]
            == "collection_api_not_supported_by_external_database"
        )
        health = client.get(f"/api/workspaces/{workspace['uuid']}/database/health")
        assert health.status_code == 200, health.text
        assert health.json()["health"]["reachable"] is True
        assert health.json()["health"]["credentials_exposed"] is False
    finally:
        app.dependency_overrides.clear()
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                (database_ref,),
            )
            connection.execute(
                psycopg.sql.SQL("DROP DATABASE IF EXISTS {}").format(
                    psycopg.sql.Identifier(database_ref)
                )
            )
            connection.execute(
                psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                    psycopg.sql.Identifier(role_ref)
                )
            )


def test_company_isolation_and_workspace_scope_are_enforced() -> None:
    owner = _actor("owner")
    other = _actor("other")
    app.dependency_overrides[current_actor] = lambda: owner
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "Owner Private App", "asset_kind": "software"},
        ).json()["asset"]
        workspace = client.post(
            f"/api/digital-assets/{asset['id']}/workspace",
            json={"workspace_key": "owner-private-app", "runtime_type": "api"},
        ).json()["workspace"]
        primary_key = client.post(
            f"/api/workspaces/{workspace['id']}/keys/primary/rotate",
            json={"label": "Owner primary"},
        )
        assert primary_key.status_code == 200
        read_only_key = client.post(
            f"/api/workspaces/{workspace['id']}/keys",
            json={
                "label": "Read only",
                "scopes": ["workspace:read", "data:read"],
            },
        ).json()["api_key"]

        forbidden_write = client.put(
            "/api/workspaces/v1/data/private/record",
            headers={"Authorization": f"Bearer {read_only_key}"},
            json={"secret": True},
        )
        assert forbidden_write.status_code == 403

        app.dependency_overrides[current_actor] = lambda: other
        hidden_asset = client.get(f"/api/digital-assets/{asset['uuid']}")
        assert hidden_asset.status_code == 404
        hidden_workspace = client.get(f"/api/workspaces/{workspace['uuid']}/database/schema")
        assert hidden_workspace.status_code == 404
        with tenant_session(other.tenant_id) as session:
            assert (
                session.execute(text("SELECT count(*) FROM digital_asset.assets")).scalar_one() == 0
            )
            assert (
                session.execute(
                    text("SELECT count(*) FROM digital_asset.workspace_records")
                ).scalar_one()
                == 0
            )
    finally:
        app.dependency_overrides.clear()


def test_static_workspace_can_upgrade_to_web_backend_by_workspace_key() -> None:
    actor = _actor("runtime-upgrade")
    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        asset = client.post(
            "/api/digital-assets",
            json={"name": "mk4", "asset_kind": "software"},
        ).json()["asset"]
        source_version = client.post(
            f"/api/digital-assets/{asset['asset_no']}/version",
            json={
                "version_no": "v1.0.0",
                "title": "MK4 backend source",
                "artifact_uri": "git://mk4/backend",
            },
        )
        assert source_version.status_code == 200
        created = client.post(
            f"/api/digital-assets/{asset['asset_no']}/workspace",
            json={"workspace_key": "mk4-workspace", "runtime_type": "static"},
        )
        assert created.status_code == 200
        assert created.json()["workspace"]["config"]["runtime_type"] == "static"
        assert [item["component_kind"] for item in created.json()["components"]] == ["frontend"]
        repeated_create = client.post(
            f"/api/digital-assets/{asset['asset_no']}/workspace",
            json={"workspace_key": "mk4-workspace", "runtime_type": "static"},
        )
        assert repeated_create.status_code == 200
        assert repeated_create.json()["created"] is False
        assert repeated_create.json()["workspace"]["uuid"] == created.json()["workspace"]["uuid"]
        assert repeated_create.json()["world_observation"]["workflow_prescribed"] is False

        upgraded = client.post(
            "/api/workspaces/mk4-workspace/runtime",
            json={
                "runtime_type": "web",
                "backend_runtime": "node20",
                "component_name": "api",
                "entrypoint": "server.js",
                "start_command": "npm start",
                "source_version_id": source_version.json()["version"]["uuid"],
            },
        )
        assert upgraded.status_code == 200
        result = upgraded.json()
        assert result["workspace"]["workspace_key"] == "mk4-workspace"
        assert result["workspace"]["config"]["runtime_type"] == "web"
        assert result["workspace"]["runtime_status"] == "building"
        assert result["component"]["component_kind"] == "backend"
        assert result["component"]["runtime"] == "node20"
        assert result["component"]["entrypoint"] == "server.js"
        assert result["deployment"]["status"] == "queued"
        assert result["deployment"]["runtime_available"] is False
        assert result["runtime_upgrade"]["from"] == "static"
        assert result["runtime_upgrade"]["to"] == "web"
        assert result["runtime_upgrade"]["actual_runtime_ready"] is False
        assert result["runtime_upgrade"]["deployment_request_created"] is True
        assert result["world_observation"]["verified_facts"]["workspace_updated_in_place"] is True
        assert result["world_observation"]["verified_facts"]["new_workspace_created"] is False
        assert result["world_observation"]["verified_facts"]["permanent_entry_reserved"] is True
        assert result["world_observation"]["primary_entity"]["facts"]["entry_url"].endswith(
            f"/assets/{actor.tenant_slug}/mk4-workspace/"
        )
        assert result["world_observation"]["decision_owner"] == "auto_runtime"

        detail = client.get(f"/api/digital-assets/{asset['asset_no']}")
        assert detail.status_code == 200
        assert detail.json()["asset"]["asset_kind"] == "software"
        runtime_entry = legacy_catalog.entry_by_tool_name("digital_market_runtime_upgrade")
        assert runtime_entry["api_path"] == "/api/workspaces/{workspace_ref}/runtime"
        runtime_schema = legacy_catalog.tool_schema(runtime_entry)
        assert runtime_schema["function"]["parameters"]["properties"]["type"]["enum"] == [
            "web",
            "api",
        ]

        unversioned_asset = client.post(
            "/api/digital-assets",
            json={"name": "No Source Yet", "asset_kind": "software"},
        ).json()["asset"]
        client.post(
            f"/api/digital-assets/{unversioned_asset['id']}/workspace",
            json={"workspace_key": "no-source-yet", "runtime_type": "static"},
        )
        configured_only = client.post(
            "/api/workspaces/no-source-yet/runtime",
            json={"runtime_type": "web/api", "runtime": "python3.12"},
        )
        assert configured_only.status_code == 200
        assert configured_only.json()["deployment"] is None
        assert configured_only.json()["workspace"]["config"]["runtime_type"] == "api"
        assert configured_only.json()["workspace"]["runtime_status"] == "planned"
        assert configured_only.json()["next_action"] == "upload_source_and_create_version"
        assert configured_only.json()["runtime_upgrade"]["deployment_request_created"] is False
        assert (
            configured_only.json()["world_observation"]["uncertainties"][0]["fact"]
            == "deployable_source_version"
        )
    finally:
        app.dependency_overrides.clear()
