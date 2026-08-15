"""Real DeepSeek acceptance gate for the public AI secretary workflow.

This is deliberately not a selector or prompt-unit test.  It enters through
the same NDJSON HTTP endpoint as the secretary UI, uses a tenant-persisted
DeepSeek connection, lets Auto Runtime choose and execute the business
capability, and then verifies the resulting world state and transcript.
"""

from __future__ import annotations

import json
import os
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


def _require_secretary_e2e() -> str:
    live_required = os.environ.get("WAREHOUSE_REQUIRE_DEEPSEEK_LIVE") == "1"
    secretary_required = os.environ.get("WAREHOUSE_REQUIRE_SECRETARY_E2E") == "1"
    if live_required and not secretary_required:
        pytest.fail(
            "The AI Runtime live gate must require a real AI secretary E2E scenario"
        )
    if not secretary_required:
        pytest.skip(
            "Real AI secretary E2E requires ops/run-ai-runtime-verification"
        )
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        pytest.fail("AI secretary E2E was required but no DeepSeek key was loaded")
    return api_key


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"secretary-e2e-{tenant_id.hex[:10]}"
    username = f"secretary-e2e-{user_id.hex[:10]}"
    tenant_name = "DeepSeek Secretary E2E"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug, "name": tenant_name},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, 'AI Secretary E2E Owner', :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=tenant_name,
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
        tenant_name=tenant_name,
        industry_template_key="generic_warehouse",
        username=username,
        display_name="AI Secretary E2E Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset(
            {
                "ai.use",
                "settings.manage",
                "assets.read",
                "assets.manage",
                "asset_mgmt.read",
                "asset_mgmt.manage",
            }
        ),
    )


def _ndjson_events(response_text: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in response_text.splitlines()
        if line.strip()
    ]


def test_real_deepseek_secretary_creates_and_reads_back_business_asset() -> None:
    """Prove one natural-language secretary request completes in the real world."""

    api_key = _require_secretary_e2e()
    actor = _actor()
    unique_suffix = uuid4().hex[:12]
    asset_name = f"AI秘書真實鏈路驗收-{unique_suffix}"
    asset_summary = "真實 DeepSeek、AI 秘書、Runtime、Adapter 與 PostgreSQL 全鏈路驗收"
    turn_id = f"secretary-e2e-{unique_suffix}"

    app.dependency_overrides[current_actor] = lambda: actor
    client = TestClient(app)
    try:
        # Persist and validate the same tenant-scoped connection used by the
        # production secretary.  No model boundary or credential lookup is
        # monkeypatched in this test.
        configured = client.post(
            "/api/integrations/deepseek/save",
            json={"api_key": api_key, "model": "deepseek-v4-flash"},
        )
        assert configured.status_code == 200, configured.text
        configured_payload = configured.json()
        assert configured_payload["validation"]["ok"] is True
        assert configured_payload["deepseek"]["connected"] is True

        request_text = (
            "請直接完成正式業務操作，不要只說明步驟，也不要詢問："
            f"在本公司的數字資產主檔建立一項全新資產，名稱「{asset_name}」，"
            f"類型 knowledge，說明「{asset_summary}」。"
            "所有必要欄位都已提供。建立後請依真實執行結果確認資產編號、名稱、"
            "類型與狀態。不要建立工作區、資料庫、版本、上市項目或 API Key。"
        )
        response = client.post(
            "/api/agent/run/stream",
            json={
                "text": request_text,
                "turn_id": turn_id,
                "surface": "secretary",
                "context_mode": "balanced",
                "locale": "zh-Hant",
                "language_mode": "fixed",
            },
        )
        assert response.status_code == 200, response.text
        events = _ndjson_events(response.text)

        starts = [event for event in events if event.get("event") == "run_start"]
        finals = [event for event in events if event.get("event") == "final"]
        assert len(starts) == 1
        assert starts[0]["surface"] == "secretary"
        assert len(finals) == 1
        final = finals[0]
        assert final["status"] == "succeeded", final
        assert final["engine"] == "deepseek-v4-flash"
        assert asset_name in str(final["message"])
        assert not any(event.get("event") == "confirmation_required" for event in events)

        activities = [
            event for event in events if event.get("event") == "runtime_activity"
        ]
        assert any(
            activity.get("model") == "deepseek-v4-flash" for activity in activities
        )
        assert any(
            "digital_market_create" in (activity.get("selected_tool_names") or [])
            for activity in activities
        )
        assert any(
            activity.get("tool_name") == "digital_market_create"
            and activity.get("phase") == "execute"
            and activity.get("status") == "succeeded"
            for activity in activities
        )

        reflections = [
            event
            for event in events
            if event.get("event") == "runtime_state" and event.get("phase") == "reflect"
        ]
        assert len(reflections) == 1
        assert reflections[0]["summary"]["goal_complete"] is True
        assert {
            item["tool_name"]: item["status"]
            for item in reflections[0]["capability_results"]
        }.get("digital_market_create") == "succeeded"

        # Business API readback proves that success was not merely model prose.
        listed = client.get("/api/digital-assets", params={"limit": 1000})
        assert listed.status_code == 200
        matching_assets = [
            item for item in listed.json()["assets"] if item.get("name") == asset_name
        ]
        assert len(matching_assets) == 1
        asset = matching_assets[0]
        assert asset["asset_kind"] == "knowledge"
        assert asset["summary"] == asset_summary
        assert asset["status"] == "registered"
        assert str(asset["asset_no"]).startswith("DMA-")

        # PostgreSQL, custody, command audit, and Runtime snapshot must all
        # independently agree that the effect completed under this tenant.
        with tenant_session(actor.tenant_id) as session:
            stored_asset = (
                session.execute(
                    text(
                        """
                        SELECT id, asset_no, name, asset_kind, summary, status
                        FROM digital_asset.assets
                        WHERE name = :name
                        """
                    ),
                    {"name": asset_name},
                )
                .mappings()
                .one()
            )
            custody_count = session.execute(
                text(
                    """
                    SELECT count(*) FROM digital_asset.custody_events
                    WHERE asset_id = :asset_id AND event_type = 'registered'
                    """
                ),
                {"asset_id": stored_asset["id"]},
            ).scalar_one()
            command_audit = (
                session.execute(
                    text(
                        """
                        SELECT origin, status
                        FROM terminal.command_executions
                        WHERE tool_name = 'digital_market_create'
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    )
                )
                .mappings()
                .one()
            )
            runtime_run = (
                session.execute(
                    text(
                        """
                        SELECT status, context_snapshot
                        FROM secretariat.runs
                        WHERE id = :run_id
                        """
                    ),
                    {"run_id": final["run_id"]},
                )
                .mappings()
                .one()
            )
        assert stored_asset["asset_no"] == asset["asset_no"]
        assert custody_count == 1
        assert dict(command_audit) == {"origin": "auto_runtime", "status": "succeeded"}
        assert runtime_run["status"] == "succeeded"
        snapshot_results = runtime_run["context_snapshot"]["tool_results"]
        assert any(
            result.get("tool_name") == "digital_market_create"
            and (result.get("result") or {}).get("status") == "succeeded"
            for result in snapshot_results
        )

        # The actual secretary transcript is durable and tied to the same turn.
        conversation_id = str(final["conversation_id"])
        conversation = client.get(f"/api/ai/conversations/{conversation_id}")
        assert conversation.status_code == 200
        messages = conversation.json()["messages"]
        turn_messages = [message for message in messages if message["turn_id"] == turn_id]
        assert [message["role"] for message in turn_messages] == ["user", "assistant"]
        assert turn_messages[0]["content"] == request_text
        assert turn_messages[1]["content"] == final["message"]
        assert turn_messages[1]["metadata"]["status"] == "succeeded"
        assert turn_messages[1]["metadata"]["engine"] == "deepseek-v4-flash"
    finally:
        app.dependency_overrides.clear()
