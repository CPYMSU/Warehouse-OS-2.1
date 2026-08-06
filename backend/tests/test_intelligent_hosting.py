from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api import intelligent_hosting as hosting_api
from app.main import app
from app.services import intelligent_hosting
from app.services.digital_asset_hosting import WorkspaceCredential
from app.services.intelligent_hosting import (
    HostingPrincipal,
    _merge_desired_state,
    _plan,
    assistant_manifest,
    failure_diagnostic,
)
from app.terminal import legacy_catalog


def _credential() -> WorkspaceCredential:
    return WorkspaceCredential(
        tenant_id=UUID("00000000-0000-0000-0000-000000000001"),
        workspace_id=UUID("00000000-0000-0000-0000-000000000002"),
        credential_id=UUID("00000000-0000-0000-0000-000000000003"),
        scopes=frozenset({"workspace:read", "deploy:read", "deploy:write", "logs:read"}),
        label="Test workspace key",
        key_kind="delegated",
        parent_credential_id=UUID("00000000-0000-0000-0000-000000000004"),
    )


def _principal() -> HostingPrincipal:
    credential = _credential()
    return HostingPrincipal(
        tenant_id=credential.tenant_id,
        auth_kind="workspace_key",
        credential=credential,
    )


def test_manifest_is_a_single_machine_contract_for_terminal_ai() -> None:
    manifest = assistant_manifest()

    assert manifest["schema"] == "warehouse.intelligent-hosting.v2"
    assert manifest["authentication"]["workspace_key"]["prefix"] == "wak_"
    assert manifest["conversation"]["create"] == "POST /api/hosting/v2/sessions"
    assert manifest["desired_state"]["runtime"]["type"].endswith("compose")
    assert "accelerator" in manifest["desired_state"]["resources"]["kinds"]
    assert manifest["execution"]["raw_reasoning_exposed"] is False
    assert [item["name"] for item in manifest["downloads"]] == [
        "dm.py",
        "dm-guide.md",
        "workspace-hosting-developer-standard-2.3.zh-TW.md",
        "workspace-hosting-contract-2.3.json",
    ]


def test_desired_state_is_flexible_but_schema_bounded() -> None:
    desired = _merge_desired_state(
        {"storage": {"verify": True}},
        {
            "runtime": {"type": "api", "runtime": "python3.12"},
            "deployment": {"state": "ready"},
        },
    )
    assert desired == {
        "storage": {"verify": True},
        "runtime": {"type": "api", "runtime": "python3.12"},
        "deployment": {"state": "ready"},
    }

    try:
        _merge_desired_state({}, {"database_raw_sql": {"execute": True}})
    except HTTPException as exc:
        assert exc.status_code == 422
        assert exc.detail["reason"] == "unsupported_desired_state"
    else:  # pragma: no cover - protects the safety boundary
        raise AssertionError("unsupported desired state was accepted")


def test_plan_waits_for_source_without_creating_a_second_workspace() -> None:
    desired = {"runtime": {"type": "auto"}, "deployment": {"state": "ready"}}
    snapshot = {
        "sources": {"ok": True, "sources": [], "count": 0},
        "deployments": {"ok": True, "deployments": [], "count": 0},
    }
    plan = _plan(desired, snapshot)

    assert plan["workflow_prescribed"] is False
    assert plan["source_available"] is False
    assert plan["required_input"]["kind"] == "source_archive"
    assert not any(step["step"] == "create_workspace" for step in plan["steps"])


def test_plan_reports_missing_key_scope_instead_of_claiming_source_is_empty() -> None:
    desired = {"runtime": {"type": "auto"}, "deployment": {"state": "ready"}}
    snapshot = {
        "sources": {
            "ok": False,
            "unavailable": True,
            "http_status": 403,
            "detail": "Workspace key is missing scope: deploy:read",
        },
        "deployments": {
            "ok": False,
            "unavailable": True,
            "http_status": 403,
        },
    }

    plan = _plan(desired, snapshot)

    assert plan["blocked"] is True
    assert plan["required_input"] == {
        "kind": "authorization_scope",
        "required": ["deploy:read"],
        "message": "Issue or use a workspace key with deploy:read.",
    }
    assert plan["diagnosis"]["stage"] == "source.observe"
    assert plan["diagnosis"]["error_code"] == "AUTHORIZATION_SCOPE_MISSING"


def test_failure_diagnostic_names_exact_stage_and_recovery() -> None:
    diagnostic = failure_diagnostic(
        "storage.persist",
        HTTPException(
            status_code=503,
            detail={
                "reason": "storage_provider_not_writable",
                "provider": "content_addressed_hdd",
            },
        ),
    )

    assert diagnostic["stage"] == "storage.persist"
    assert diagnostic["component"] == "storage"
    assert diagnostic["error_code"] == "STORAGE_PROVIDER_NOT_WRITABLE"
    assert diagnostic["http_status"] == 503
    assert diagnostic["resumable"] is True
    assert diagnostic["detail"]["provider"] == "content_addressed_hdd"


def test_dm_and_guide_are_delivered_by_the_intelligent_interface() -> None:
    client = TestClient(app)

    manifest = client.get("/api/hosting/v2/manifest")
    kit = client.get("/api/hosting/v2/kit")
    cli = client.get("/api/hosting/v2/dm.py")
    guide = client.get("/api/hosting/v2/dm-guide.md")
    requirements = client.get("/api/hosting/v2/requirements")
    standard = client.get("/api/hosting/v2/developer-standard.md")
    contract = client.get("/api/hosting/v2/contract.json")

    assert manifest.status_code == 200
    assert kit.status_code == 200
    assert cli.status_code == 200
    assert 'DEFAULT_BASE = "http://testserver"' in cli.text
    assert 'VERSION = "2.6.0"' in cli.text
    assert "/api/workspaces/v1/usage" in cli.text
    assert 'commands.add_parser("job"' in cli.text
    assert 'commands.add_parser("database"' in cli.text
    assert '"fabric"' in cli.text
    assert 'source_subcommands.add_parser("pull"' in cli.text
    assert '"/api/hosting/v2/sessions"' in cli.text
    assert 'commands.add_parser("hosting"' in cli.text
    assert '"/api/hosting/v2/requirements"' in cli.text
    assert 'prog="dm.py"' in cli.text
    compile(cli.text, "dm.py", "exec")
    assert guide.status_code == 200
    assert "給終端 AI：優先使用智能託管接口" in guide.text
    assert "/api/hosting/v2/manifest" in guide.text
    assert requirements.status_code == 200
    assert requirements.json()["version"] == "2.3"
    assert standard.status_code == 200
    assert standard.text.startswith("# Warehouse OS《託管應用技術要求 2.3》")
    assert contract.status_code == 200
    assert contract.json()["example_manifest"]["runtime"]["health_path"] == ("/healthz")


def test_workspace_key_session_surface_uses_one_conversation_contract(monkeypatch) -> None:
    principal = _principal()
    app.dependency_overrides[hosting_api.hosting_principal] = lambda: principal
    calls: list[tuple[str, object]] = []

    def fake_create(_principal, credential, payload):
        calls.append(("create", credential.workspace_id))
        return {
            "ok": True,
            "session": {
                "id": "00000000-0000-0000-0000-000000000009",
                "status": "planning",
                "desired_state": payload["desired_state"],
            },
        }

    def fake_execute(_principal, session_id, payload, _settings):
        calls.append(("execute", session_id))
        return {
            "ok": True,
            "session": {
                "id": session_id,
                "status": "running",
                "desired_state": payload["desired_state"],
            },
        }

    monkeypatch.setattr(hosting_api, "create_session", fake_create)
    monkeypatch.setattr(hosting_api, "execute_message", fake_execute)
    try:
        response = TestClient(app).post(
            "/api/hosting/v2/sessions",
            json={
                "message": "Deploy this source",
                "client_kind": "terminal_ai",
                "desired_state": {
                    "runtime": {"type": "auto"},
                    "deployment": {"state": "ready"},
                },
                "execute": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["session"]["status"] == "running"
    assert calls == [
        ("create", principal.credential.workspace_id),
        ("execute", "00000000-0000-0000-0000-000000000009"),
    ]


def test_intelligent_hosting_routes_are_published_before_api_fallback() -> None:
    paths = app.openapi()["paths"]
    for path in (
        "/api/hosting/v2/manifest",
        "/api/hosting/v2/kit",
        "/api/hosting/v2/dm.py",
        "/api/hosting/v2/dm-guide.md",
        "/api/hosting/v2/requirements",
        "/api/hosting/v2/developer-standard.md",
        "/api/hosting/v2/contract.json",
        "/api/hosting/v2/sessions",
        "/api/hosting/v2/sessions/{session_id}",
        "/api/hosting/v2/sessions/{session_id}/messages",
        "/api/hosting/v2/sessions/{session_id}/messages/stream",
        "/api/hosting/v2/sessions/{session_id}/events",
        "/api/hosting/v2/sessions/{session_id}/sources",
        "/api/workspaces/v1/fabric/manifest",
        "/api/workspaces/v1/fabric",
        "/api/workspaces/v1/fabric/resources",
        "/api/workspaces/v1/fabric/actions/{action_id}",
    ):
        assert path in paths


def test_platform_secretary_commands_use_the_same_hosting_session_api() -> None:
    entry, values = legacy_catalog.parse_line(
        "dm hosting start --workspace mk4-workspace "
        "--message 'deploy to a healthy URL' "
        '--desired-state \'{"runtime":{"type":"auto"},'
        '"deployment":{"state":"ready"}}\' --execute true'
    )
    method, path, body = legacy_catalog.build_request(entry, values)

    assert entry["tool_name"] == "digital_market_hosting_start"
    assert method == "POST"
    assert path == "/api/hosting/v2/sessions"
    assert body == {
        "workspace_ref": "mk4-workspace",
        "message": "deploy to a healthy URL",
        "desired_state": {
            "runtime": {"type": "auto"},
            "deployment": {"state": "ready"},
        },
        "execute": True,
        "client_kind": "web_secretary",
    }


def test_refresh_completes_an_already_active_healthy_deployment(monkeypatch) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000009")
    session_id = UUID("00000000-0000-0000-0000-000000000010")
    updates: list[dict[str, object]] = []
    snapshot = {
        "workspace": {"active_deployment_id": str(deployment_id)},
        "sources": {"ok": True, "sources": [{"id": "source-1"}], "count": 1},
        "deployments": {
            "ok": True,
            "deployments": [
                {
                    "uuid": str(deployment_id),
                    "status": "ready",
                    "health": "healthy",
                }
            ],
        },
        "pages": {"ok": True, "site": {"url": "https://example.test/app/"}},
    }
    row = {
        "id": session_id,
        "status": "running",
        "current_stage": "runtime.deployment",
        "desired_state": {
            "runtime": {"type": "api"},
            "deployment": {"state": "ready", "activate_when_healthy": True},
        },
        "state": {},
        "diagnosis": None,
    }

    monkeypatch.setattr(intelligent_hosting, "observe_workspace", lambda _credential: snapshot)
    monkeypatch.setattr(
        intelligent_hosting,
        "activate_workspace_deployment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("an already active deployment must not be activated again")
        ),
    )
    monkeypatch.setattr(
        intelligent_hosting,
        "_update_session",
        lambda *_args, **kwargs: updates.append(kwargs),
    )
    monkeypatch.setattr(intelligent_hosting, "_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        intelligent_hosting,
        "_row",
        lambda *_args, **_kwargs: {**row, "status": "completed", "current_stage": "ready"},
    )

    result = intelligent_hosting._refresh_state(_principal(), row, _credential())

    assert result["status"] == "completed"
    assert updates[0]["status_value"] == "completed"
    assert updates[0]["stage"] == "ready"
    assert updates[0]["completed"] is True
