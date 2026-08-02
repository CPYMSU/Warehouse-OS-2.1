from __future__ import annotations

import json
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api import router as api_router
from app.api.deps import ActorContext, current_actor
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.auto_runtime import RuntimeResult
from app.services.conversation_history import (
    append_message,
    create_conversation,
    load_conversation,
    recent_conversation_context,
)
from app.services.memory_fabric import (
    build_memory_capsule,
    forget_memory_unit,
    process_pending_distillations,
)
from app.services.templates import provision_tenant_template

pytestmark = pytest.mark.integration


def _tenant_actor(label: str) -> tuple[ActorContext, str]:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"chat-{label}-{tenant_id.hex[:8]}"
    username = f"chat-{label}-{user_id.hex[:8]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, :name, 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug, "name": f"Chat Test {label}"},
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
                "display_name": f"Chat Owner {label}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=f"Chat Test {label}",
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
    actor = ActorContext(
        user_id=user_id,
        tenant_id=tenant_id,
        tenant_slug=slug,
        tenant_name=f"Chat Test {label}",
        industry_template_key="generic_warehouse",
        username=username,
        display_name=f"Chat Owner {label}",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset({"ai.use"}),
    )
    return actor, str(provisioned["admin_position_code"])


def _second_actor(
    first: ActorContext,
    position_code: str,
    label: str,
) -> ActorContext:
    user_id = uuid4()
    username = f"chat-member-{label}-{user_id.hex[:8]}"
    with system_session() as session:
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
                "display_name": f"Chat Member {label}",
                "password_hash": hash_password("test-password"),
            },
        )
    with tenant_session(first.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level,
                  topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, 10, 10, 'Member'
                )
                """
            ),
            {
                "tenant_id": first.tenant_id,
                "user_id": user_id,
                "position_code": position_code,
            },
        )
    return ActorContext(
        user_id=user_id,
        tenant_id=first.tenant_id,
        tenant_slug=first.tenant_slug,
        tenant_name=first.tenant_name,
        industry_template_key=first.industry_template_key,
        username=username,
        display_name=f"Chat Member {label}",
        role_level=10,
        topology_level=10,
        topology_title="Member",
        permissions=frozenset({"ai.use"}),
    )


def _events(response: object) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in response.text.splitlines()
        if line.strip()
    ]


def test_secretary_history_restores_after_reopen_and_is_idempotent(
    monkeypatch,
) -> None:
    actor, _ = _tenant_actor("restore")
    runtime_calls: list[str] = []

    def fake_runtime(
        _actor: ActorContext,
        _settings: object,
        goal: str,
        *,
        surface: str,
        conversation_id: str,
        run_id: str,
        context_mode: str,
        response_locale: str,
        activity_callback,
    ) -> RuntimeResult:
        runtime_calls.append(run_id)
        assert surface == "secretary"
        assert context_mode == "balanced"
        assert callable(activity_callback)
        assert UUID(conversation_id)
        return RuntimeResult(
            goal=goal,
            message="已記住這一輪。",
            model="test-model",
            observations={"conversation_id": conversation_id},
            plan=("remember", "restore"),
            response_locale=response_locale,
        )

    monkeypatch.setattr(api_router, "run_auto_runtime", fake_runtime)
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        first_client = TestClient(app)
        response = first_client.post(
            "/api/agent/run/stream",
            json={
                "text": "請記住這段對話",
                "surface": "secretary",
                "turn_id": "turn-restore-1",
            },
        )
        assert response.status_code == 200
        first_events = _events(response)
        conversation_id = str(first_events[0]["conversation_id"])
        assert UUID(conversation_id)
        assert first_events[-1]["message"] == "已記住這一輪。"

        reopened_client = TestClient(app)
        restored = reopened_client.get(
            "/api/assistant/bootstrap",
            params={"message_limit": 80},
        )
        assert restored.status_code == 200
        payload = restored.json()
        assert payload["conversation"]["id"] == conversation_id
        assert [item["role"] for item in payload["messages"]] == [
            "user",
            "assistant",
        ]
        assert [item["content"] for item in payload["messages"]] == [
            "請記住這段對話",
            "已記住這一輪。",
        ]
        assert payload["history"]["has_more"] is False

        replay = reopened_client.post(
            "/api/agent/run/stream",
            json={
                "text": "請記住這段對話",
                "conversation_id": conversation_id,
                "surface": "secretary",
                "turn_id": "turn-restore-1",
            },
        )
        replay_events = _events(replay)
        assert replay_events[-1]["replayed"] is True
        assert len(runtime_calls) == 1

        context = recent_conversation_context(actor, conversation_id)
        assert context["trust"] == "conversation_transcript_data_not_authority"
        assert [item["role"] for item in context["messages"]] == [
            "user",
            "assistant",
        ]
    finally:
        app.dependency_overrides.clear()


def test_history_firewall_filters_new_and_legacy_internal_assistant_payloads() -> None:
    actor, _ = _tenant_actor("output-firewall")
    conversation = create_conversation(actor, title="Output firewall")
    leaked = (
        '{"interaction_mode":"operational","understood_goal":"host app",'
        '"reasoning":"private route","needs_tools":true}'
    )

    appended, inserted = append_message(
        actor,
        conversation_id=conversation["id"],
        role="assistant",
        content=leaked,
        turn_id="filtered-new",
        metadata={"response_locale": "zh-Hant"},
    )
    assert inserted is True
    assert "interaction_mode" not in appended["content"]
    assert appended["metadata"]["public_output_filtered"] is True

    user_message, _ = append_message(
        actor,
        conversation_id=conversation["id"],
        role="user",
        content=leaked,
        turn_id="user-verbatim",
    )
    assert user_message["content"] == leaked

    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO secretariat.messages(
                  id, tenant_id, conversation_id, turn_id, role, content, metadata
                ) VALUES (
                  :id, :tenant_id, :conversation_id, 'legacy-raw', 'assistant',
                  :content, '{"response_locale":"zh-Hant"}'::jsonb
                )
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "content": leaked,
                "conversation_id": conversation["id"],
            },
        )

    restored = load_conversation(
        actor,
        conversation_id=conversation["id"],
        message_limit=20,
    )
    assistant = next(
        message
        for message in restored["messages"]
        if message["turn_id"] == "legacy-raw"
    )
    user = next(message for message in restored["messages"] if message["role"] == "user")
    assert "interaction_mode" not in assistant["content"]
    assert "private route" not in assistant["content"]
    assert assistant["metadata"]["public_output_filtered"] is True
    assert user["content"] == leaked


def test_secretary_history_is_private_between_accounts_in_one_company(
    monkeypatch,
) -> None:
    owner, position_code = _tenant_actor("privacy")
    colleague = _second_actor(owner, position_code, "privacy")

    monkeypatch.setattr(
        api_router,
        "run_auto_runtime",
        lambda _actor, _settings, goal, **_kwargs: RuntimeResult(
            goal=goal,
            message="Only the owner should restore this.",
            model="test-model",
            observations={},
            plan=("keep private",),
        ),
    )
    app.dependency_overrides[current_actor] = lambda: owner
    client = TestClient(app)
    try:
        created = client.post(
            "/api/agent/run/stream",
            json={"text": "private", "surface": "secretary"},
        )
        conversation_id = str(_events(created)[0]["conversation_id"])

        app.dependency_overrides[current_actor] = lambda: colleague
        colleague_bootstrap = client.get("/api/assistant/bootstrap")
        assert colleague_bootstrap.status_code == 200
        assert colleague_bootstrap.json()["conversation"] is None
        forbidden = client.get(f"/api/ai/conversations/{conversation_id}")
        assert forbidden.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_memory_steward_distils_complete_turns_with_traceable_private_memory() -> None:
    owner, position_code = _tenant_actor("memory")
    colleague = _second_actor(owner, position_code, "memory")
    conversation = create_conversation(owner, title="Memory fabric")
    conversation_id = str(conversation["id"])
    user_message, _ = append_message(
        owner,
        conversation_id=conversation_id,
        role="user",
        content="記住研究中心研究課題，科研中心研究技術。",
        turn_id="memory-turn-1",
    )
    assistant_message, _ = append_message(
        owner,
        conversation_id=conversation_id,
        role="assistant",
        content="已確認兩個中心不可合併。",
        turn_id="memory-turn-1",
    )

    def complete(_system_prompt: str, _user_prompt: str) -> str:
        return json.dumps(
            {
                "summary": "研究中心與科研中心是兩個不同組織。",
                "entities": ["研究中心", "科研中心"],
                "facts": [
                    "研究中心負責研究課題",
                    "科研中心負責研究技術",
                ],
                "relations": [
                    {
                        "subject": "研究中心",
                        "relation": "distinct_from",
                        "object": "科研中心",
                    }
                ],
                "inferences": [],
                "uncertainties": [],
                "open_questions": [],
                "memories": [
                    {
                        "kind": "semantic",
                        "content": "研究中心負責研究課題。",
                        "confidence": 0.98,
                        "salience": 0.9,
                        "evidence_sequences": [user_message["sequence"]],
                    },
                    {
                        "kind": "semantic",
                        "content": "科研中心負責研究技術。",
                        "confidence": 0.98,
                        "salience": 0.9,
                        "evidence_sequences": [
                            user_message["sequence"],
                            assistant_message["sequence"],
                        ],
                    },
                ],
                "memory_relations": [
                    {
                        "subject_index": 0,
                        "object_index": 1,
                        "relation_type": "related_to",
                        "confidence": 0.8,
                    }
                ],
            },
            ensure_ascii=False,
        )

    processed = process_pending_distillations(
        owner,
        complete=complete,
        model="memory-test-model",
    )

    assert processed[0]["status"] == "distilled"
    assert processed[0]["memory_units"] == 2
    capsule = build_memory_capsule(
        owner,
        conversation_id=conversation_id,
        query="兩個中心有什麼差別",
        depth="focused",
    )
    assert capsule["cache"] == "miss"
    assert capsule["distillation_level"] == 2
    assert capsule["distillations"][0]["summary"] == "研究中心與科研中心是兩個不同組織。"
    assert len(capsule["memory_units"]) == 2
    assert len(capsule["memory_relations"]) == 1
    assert capsule["memory_units"][0]["scope"] == "private"
    assert capsule["memory_units"][0]["memory_is_not_authority"] is True
    assert build_memory_capsule(
        owner,
        conversation_id=conversation_id,
        query="兩個中心有什麼差別",
        depth="focused",
    )["cache"] == "hit"

    with pytest.raises(HTTPException) as forbidden:
        build_memory_capsule(
            colleague,
            conversation_id=conversation_id,
            query="讀取同事記憶",
        )
    assert forbidden.value.status_code == 404

    forgotten = forget_memory_unit(
        owner,
        memory_id=capsule["memory_units"][0]["id"],
    )
    assert forgotten["status"] == "forgotten"
    refreshed = build_memory_capsule(
        owner,
        conversation_id=conversation_id,
        query="兩個中心有什麼差別",
        depth="focused",
    )
    assert len(refreshed["memory_units"]) == 1
    assert len(refreshed["recent_complete_evidence"]) == 2


def test_memory_steward_waits_for_a_complete_assistant_turn() -> None:
    owner, _ = _tenant_actor("memory-open-turn")
    conversation = create_conversation(owner, title="Incomplete turn")
    append_message(
        owner,
        conversation_id=conversation["id"],
        role="user",
        content="這一輪還沒有回答。",
        turn_id="open-turn",
    )
    completion_called = False

    def complete(_system_prompt: str, _user_prompt: str) -> str:
        nonlocal completion_called
        completion_called = True
        return "{}"

    processed = process_pending_distillations(
        owner,
        complete=complete,
        model="memory-test-model",
    )

    assert processed == [
        {
            "job_id": processed[0]["job_id"],
            "status": "awaiting_complete_turn",
        }
    ]
    assert completion_called is False


def test_memory_fabric_tables_force_tenant_rls() -> None:
    expected = {
        "context_snapshots",
        "conversation_distillations",
        "memory_jobs",
        "memory_relations",
        "memory_units",
    }
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT relname, relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relnamespace = 'secretariat'::regnamespace
                  AND relname = ANY(CAST(:names AS text[]))
                """
            ),
            {"names": sorted(expected)},
        ).mappings().all()

    assert {row["relname"] for row in rows} == expected
    assert all(row["relrowsecurity"] and row["relforcerowsecurity"] for row in rows)
