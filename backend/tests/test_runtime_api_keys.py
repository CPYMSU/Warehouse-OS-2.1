from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.api import router as api_router
from app.api.deps import ActorContext, _runtime_api_scope, current_actor
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services.auto_runtime import RuntimeResult
from app.services.templates import provision_tenant_template
from app.terminal.executor import execute_cli_line

pytestmark = pytest.mark.integration

_CREATED_ACTORS: list[ActorContext] = []


@pytest.fixture(autouse=True)
def _cleanup_runtime_test_tenants():
    yield
    app.dependency_overrides.clear()
    # Integration tests are permitted only against a disposable database. Do
    # not weaken append-only audit/message triggers just to delete fixtures;
    # the full verification runner drops the entire database after the suite.
    _CREATED_ACTORS.clear()


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"runtime-{tenant_id.hex[:12]}"
    username = f"runtime-owner-{user_id.hex[:12]}"
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                VALUES (:id, :slug, 'Runtime API Test', 'generic_warehouse')
                """
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, 'Runtime Owner', :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "password_hash": hash_password("runtime-test-password"),
            },
        )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name="Runtime API Test",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level,
                  topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, 10, 10, 'System Administrator'
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "position_code": provisioned["admin_position_code"],
            },
        )
        session.execute(
            text(
                """
                INSERT INTO iam.membership_positions(
                  tenant_id, user_id, position_code, appointment_type
                ) VALUES (:tenant_id, :user_id, :position_code, 'primary')
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
        tenant_name="Runtime API Test",
        industry_template_key="generic_warehouse",
        username=username,
        display_name="Runtime Owner",
        role_level=10,
        topology_level=10,
        topology_title="System Administrator",
        permissions=frozenset(
            {
                "ai.use",
                "terminal.use",
                "settings.manage",
                "research.read",
                "research.write",
            }
        ),
    )
    _CREATED_ACTORS.append(actor)
    return actor


def _events(response) -> list[dict[str, object]]:
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_runtime_api_key_calls_the_same_secretary_and_terminal_backends(monkeypatch) -> None:
    actor = _actor()
    observed: dict[str, object] = {}

    def fake_runtime(
        actor,
        settings,
        goal,
        *,
        surface,
        conversation_id,
        run_id,
        context_mode,
        response_locale,
        activity_callback,
    ):
        observed.update(
            actor=actor,
            goal=goal,
            surface=surface,
            conversation_id=conversation_id,
            run_id=run_id,
            context_mode=context_mode,
        )
        return RuntimeResult(
            goal=goal,
            message="Runtime API reached the shared Auto Runtime.",
            model="deepseek-v4-pro",
            observations={"shared_backend": True},
            plan=("observe", "plan", "reflect"),
            response_locale=response_locale,
        )

    monkeypatch.setattr(api_router, "run_auto_runtime", fake_runtime)
    monkeypatch.setattr(api_router, "run_background_memory_steward", lambda *_args: None)
    monkeypatch.setattr(
        api_router,
        "execute_cli_line",
        lambda live_actor, line: {
            "ok": True,
            "line": line,
            "auth_kind": live_actor.auth_kind,
            "credential_scopes": sorted(live_actor.credential_scopes),
        },
    )

    client = TestClient(app)
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        issued = client.post(
            "/api/assistant/cli-keys",
            json={
                "label": "Codex integration test",
                "scopes": ["assistant", "terminal"],
                "expires_in_days": 30,
            },
        )
    finally:
        app.dependency_overrides.clear()
    assert issued.status_code == 200
    payload = issued.json()
    api_key = payload["api_key"]
    key_id = int(payload["key_id"])
    assert api_key.startswith(f"wsk_{actor.tenant_slug}_")
    assert payload["endpoints"] == {
        "assistant_stream": "/api/agent/run/stream",
        "terminal_execute": "/api/cli/exec",
        "research_api": "/api/research/projects",
        "research_upload": "/api/research/projects/{project_ref}/files",
        "civilization_api": "/api/civilization/thoughts",
        "identity": "/api/auth/me",
    }

    with tenant_session(actor.tenant_id) as session:
        stored = session.execute(
            text(
                """
                SELECT key_hash, key_hint, scopes
                FROM iam.runtime_api_keys WHERE id = :key_id
                """
            ),
            {"key_id": key_id},
        ).mappings().one()
    assert api_key not in str(stored)
    assert len(stored["key_hash"]) == 64
    assert stored["key_hint"] == payload["key_hint"]
    assert stored["scopes"] == ["assistant", "terminal"]

    headers = {"Authorization": f"Bearer {api_key}"}
    identity = client.get("/api/auth/me", headers=headers)
    assert identity.status_code == 200
    assert identity.json()["tenant"] == actor.tenant_slug

    assistant = client.post(
        "/api/agent/run/stream",
        headers=headers,
        json={
            "text": "Use the real shared Runtime.",
            "surface": "secretary",
            "turn_id": f"runtime-api-{uuid4()}",
        },
    )
    assert assistant.status_code == 200
    events = _events(assistant)
    assert events[-1]["status"] == "succeeded"
    assert events[-1]["engine"] == "deepseek-v4-pro"
    assert observed["actor"].auth_kind == "runtime_api_key"
    assert observed["surface"] == "secretary"

    terminal = client.post(
        "/api/cli/exec",
        headers=headers,
        json={"line": "warehouse list"},
    )
    assert terminal.status_code == 200
    assert terminal.json() == {
        "ok": True,
        "line": "warehouse list",
        "auth_kind": "runtime_api_key",
        "credential_scopes": ["assistant", "terminal"],
    }

    assert client.get("/api/settings", headers=headers).status_code == 403
    assert client.get("/api/assistant/cli-keys", headers=headers).status_code == 403

    app.dependency_overrides[current_actor] = lambda: actor
    try:
        revoked = client.post(f"/api/assistant/cli-keys/{key_id}/revoke")
    finally:
        app.dependency_overrides.clear()
    assert revoked.status_code == 200
    assert revoked.json()["revoked"] is True
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_runtime_api_key_scopes_are_independent_live_audience_ceilings(monkeypatch) -> None:
    actor = _actor()
    client = TestClient(app)
    monkeypatch.setattr(api_router, "run_background_memory_steward", lambda *_args: None)
    monkeypatch.setattr(
        api_router,
        "run_auto_runtime",
        lambda actor, settings, goal, **kwargs: RuntimeResult(
            goal=goal,
            message="assistant-ok",
            model="deepseek-v4-pro",
        ),
    )
    monkeypatch.setattr(
        api_router,
        "execute_cli_line",
        lambda actor, line: {"ok": True, "line": line},
    )

    app.dependency_overrides[current_actor] = lambda: actor
    try:
        assistant_key = client.post(
            "/api/runtime/keys",
            json={"label": "Assistant only", "scopes": ["assistant"]},
        ).json()["api_key"]
        terminal_key = client.post(
            "/api/runtime/keys",
            json={"label": "Terminal only", "scopes": ["terminal"]},
        ).json()["api_key"]
    finally:
        app.dependency_overrides.clear()

    assistant_headers = {"Authorization": f"Bearer {assistant_key}"}
    terminal_headers = {"Authorization": f"Bearer {terminal_key}"}
    assert (
        client.post(
            "/api/agent/run/stream",
            headers=assistant_headers,
            json={"text": "hello", "turn_id": f"assistant-{uuid4()}"},
        ).status_code
        == 200
    )
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE iam.position_profiles
                SET permissions = permissions - 'ai.use'
                WHERE tenant_id = :tenant_id
                  AND position_code IN (
                    SELECT position_code FROM iam.membership_positions
                    WHERE user_id = :user_id AND active
                  )
                """
            ),
            {"tenant_id": actor.tenant_id, "user_id": actor.user_id},
        )
    assert (
        client.post(
            "/api/agent/run/stream",
            headers=assistant_headers,
            json={"text": "hello again", "turn_id": f"assistant-live-{uuid4()}"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/cli/exec",
            headers=assistant_headers,
            json={"line": "warehouse list"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/cli/exec",
            headers=terminal_headers,
            json={"line": "warehouse list"},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/agent/run/stream",
            headers=terminal_headers,
            json={"text": "hello", "turn_id": f"terminal-{uuid4()}"},
        ).status_code
        == 403
    )


def test_research_runtime_scope_streams_upload_and_exposes_git_lineage(
    tmp_path: Path,
) -> None:
    actor = _actor()
    settings = Settings(
        asset_storage_root=tmp_path / "research-objects",
        research_repository_root=tmp_path / "research-git",
    )
    client = TestClient(app)
    app.dependency_overrides[current_actor] = lambda: actor
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        issued = client.post(
            "/api/runtime/keys",
            json={"label": "Research terminal", "scopes": ["research"]},
        )
    finally:
        app.dependency_overrides.pop(current_actor, None)
    assert issued.status_code == 200
    api_key = issued.json()["api_key"]
    headers = {"Authorization": f"Bearer {api_key}"}

    cli_manifest = client.get("/api/research/cli/manifest", headers=headers)
    assert cli_manifest.status_code == 200
    assert cli_manifest.json()["credential_scope"] == "research"
    cli_download = client.get("/api/research/cli/download", headers=headers)
    assert cli_download.status_code == 200
    assert cli_download.headers["x-content-sha256"] == cli_manifest.json()["sha256"]

    formats = client.get("/api/research/formats", headers=headers)
    assert formats.status_code == 200
    assert formats.json()["upload"]["creates_git_commit"] is True

    created = client.post(
        "/api/research/projects",
        headers=headers,
        json={"title": "Runtime custody verification", "research_area": "TEST"},
    )
    assert created.status_code == 201
    project = created.json()["project"]

    contract = client.get(
        f"/api/research/projects/{project['id']}/upload-contract",
        headers=headers,
    )
    assert contract.status_code == 200
    assert contract.json()["request"]["runtime_scope"] == "research"
    assert "WAREHOUSE_RESEARCH_KEY" in contract.json()["curl_template"]

    content = b"sample,value\nA,1\nB,2\n"
    uploaded = client.post(
        f"/api/research/projects/{project['id']}/files",
        headers=headers,
        files={"file": ("observations.csv", content, "text/csv")},
        data={
            "logical_path": "data/observations.csv",
            "commit_message": "Add observations",
        },
    )
    assert uploaded.status_code == 201
    upload = uploaded.json()
    assert upload["version"]["version"] == 1
    assert len(upload["version"]["content_sha256"]) == 64
    assert len(upload["git"]["sha"]) == 40
    file_id = upload["file"]["id"]

    detail_response = client.get(
        f"/api/research/projects/{project['slug']}",
        headers=headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["files"][0]["id"] == file_id
    assert detail["files"][0]["preview_available"] is True
    assert "preview" not in detail["files"][0]
    assert detail["files"][0]["versions"][0]["preview_available"] is True
    assert "preview" not in detail["files"][0]["versions"][0]
    assert len(detail_response.content) < 20_000

    versions = client.get(
        f"/api/research/projects/{project['slug']}/files/{file_id}/versions",
        headers=headers,
    )
    assert versions.status_code == 200
    assert versions.json()["total"] == 1
    assert "preview" in versions.json()["versions"][0]

    downloaded = client.get(
        f"/api/research/projects/{project['slug']}/files/{file_id}/content",
        headers=headers,
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content
    assert downloaded.headers["x-content-sha256"] == upload["version"]["content_sha256"]

    commits = client.get(
        f"/api/research/projects/{project['slug']}/commits",
        headers=headers,
    )
    assert commits.status_code == 200
    assert [item["message"] for item in commits.json()["commits"][:2]] == [
        "Add observations",
        "Initialize research project",
    ]

    assert client.get("/api/settings", headers=headers).status_code == 403
    app.dependency_overrides.clear()


def test_research_key_command_is_self_scoped_and_audit_redacted() -> None:
    actor = _actor()

    issued = execute_cli_line(
        actor,
        'research key issue --label "Laboratory simulator" --days 30',
    )

    assert issued["ok"] is True
    assert issued["status"] == "succeeded"
    assert "api_key" not in issued["data"]
    credentials = issued["credentials"]
    assert len(credentials) == 1
    plain = credentials[0]["value"]
    assert plain.startswith(f"wsk_{actor.tenant_slug}_")
    assert credentials[0]["scopes"] == ["research"]
    key_id = int(credentials[0]["key_id"])

    listed = execute_cli_line(actor, "research key list")
    assert listed["ok"] is True
    assert {
        int(item["id"]) for item in listed["data"]["keys"]
    } == {key_id}
    assert all(item["scopes"] == ["research"] for item in listed["data"]["keys"])

    audit_engine = create_engine(get_settings().migration_database_url)
    with audit_engine.begin() as connection:
        connection.execute(
            text(
                "SELECT set_config('app.tenant_id', CAST(:tenant_id AS text), true)"
            ),
            {"tenant_id": actor.tenant_id},
        )
        audit_response = connection.execute(
            text(
                """
                SELECT response
                FROM terminal.command_executions
                WHERE tool_name = 'research_api_key_issue'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
        ).scalar_one()
    audit_engine.dispose()
    serialized_audit = json.dumps(audit_response, ensure_ascii=False)
    assert plain not in serialized_audit
    assert '"credentials": "[redacted]"' in serialized_audit

    revoked = execute_cli_line(
        actor,
        f"research key revoke --key-id {key_id}",
    )
    assert revoked["ok"] is True
    assert revoked["data"]["revoked"] is True


def test_research_write_permission_can_issue_research_only_key() -> None:
    actor = _actor()
    write_only = ActorContext(
        **{
            **actor.__dict__,
            "permissions": frozenset({"research.write"}),
        }
    )
    app.dependency_overrides[current_actor] = lambda: write_only
    try:
        response = TestClient(app).post(
            "/api/research/api-keys",
            json={
                "label": "Write-only research integration",
                "expires_in_days": 7,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["scopes"] == ["research"]
    assert response.json()["research_cli"] == {
        "manifest": "/api/research/cli/manifest",
        "download": "/api/research/cli/download",
        "credential_environment": "WAREHOUSE_RESEARCH_KEY",
        "note": (
            "Pass this key through the environment or a chmod 600 key file; "
            "do not place it in shell history or command-line arguments."
        ),
    }


def test_runtime_research_audience_is_explicit() -> None:
    from starlette.requests import Request

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/research/projects/example/files",
            "query_string": b"",
            "headers": [],
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
            "scheme": "http",
        }
    )
    assert _runtime_api_scope(request) == "research"
