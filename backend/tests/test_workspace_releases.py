from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from app.api.workspace_v1_compat import router as workspace_router
from app.database_migration_controller import _contains_row_mutation
from app.downloads import dam
from app.services import workspace_releases
from app.services.digital_asset_hosting import WorkspaceCredential


def _credential(*scopes: str) -> WorkspaceCredential:
    return WorkspaceCredential(
        tenant_id=UUID("00000000-0000-0000-0000-000000000201"),
        workspace_id=UUID("00000000-0000-0000-0000-000000000202"),
        credential_id=UUID("00000000-0000-0000-0000-000000000203"),
        scopes=frozenset(scopes),
        label="release-test",
        key_kind="primary",
        parent_credential_id=None,
    )


def test_static_release_gate_rejects_server_only_contracts() -> None:
    manifest = {
        "data": {
            "runtime_database_url_env": "DATABASE_URL",
            "migration_database_url_env": "MIGRATION_DATABASE_URL",
        },
        "acceptance": {
            "http": [
                {"name": "root", "path": "/"},
                {"name": "api", "path": "/api/health"},
            ]
        },
    }
    jobs = [
        {
            "name": "migrate",
            "database_access": "migration",
            "required_before_activation": True,
        }
    ]

    blockers = workspace_releases._static_blockers("static", manifest, jobs)

    assert {item["code"] for item in blockers} == {
        "static_requires_database_lifecycle_job",
        "static_requests_runtime_database_environment",
        "static_declares_runtime_api_acceptance",
    }


def test_runtime_delivery_keeps_database_contracts_valid() -> None:
    manifest = {
        "data": {"runtime_database_url_env": "DATABASE_URL"},
        "acceptance": {"http": [{"name": "api", "path": "/api/health"}]},
    }
    jobs = [{"name": "migrate", "database_access": "migration"}]

    assert workspace_releases._static_blockers("python", manifest, jobs) == []


def test_release_candidate_requests_runtime_wake_without_blocking(monkeypatch) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000210")
    statements: list[str] = []

    class _Result:
        def __init__(self, *, mapping=None, scalar=None):
            self.mapping = mapping
            self.scalar = scalar

        def mappings(self):
            return self

        def one_or_none(self):
            return self.mapping

        def scalar_one_or_none(self):
            return self.scalar

    class _Session:
        def execute(self, statement, _parameters=None):
            sql = str(statement)
            statements.append(sql)
            if "SELECT status,health,runtime_state" in sql:
                return _Result(
                    mapping={
                        "status": "ready",
                        "health": "healthy",
                        "runtime_state": "running",
                        "runtime_wake_requested_at": None,
                        "runtime_wake_error": None,
                        "result": {"runtime_kind": "container"},
                    }
                )
            return _Result(scalar=deployment_id)

    @contextmanager
    def fake_tenant_session(_tenant_id):
        yield _Session()

    monkeypatch.setattr(workspace_releases, "tenant_session", fake_tenant_session)

    result = workspace_releases._prepare_candidate_runtime_for_acceptance(
        _credential("deploy:read", "deploy:write"), deployment_id
    )

    assert result == {"ready": False, "requested": True}
    assert any("SET runtime_state='wake_requested'" in sql for sql in statements)


def test_release_candidate_accepts_after_lifecycle_records_running(monkeypatch) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000211")

    class _Result:
        def mappings(self):
            return self

        def one_or_none(self):
            return {
                "status": "ready",
                "health": "healthy",
                "runtime_state": "running",
                "runtime_wake_requested_at": datetime.now(UTC),
                "runtime_wake_error": None,
                "result": {"runtime_kind": "container"},
            }

    class _Session:
        def execute(self, _statement, _parameters=None):
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id):
        yield _Session()

    monkeypatch.setattr(workspace_releases, "tenant_session", fake_tenant_session)

    assert workspace_releases._prepare_candidate_runtime_for_acceptance(
        _credential("deploy:read", "deploy:write"), deployment_id
    ) == {"ready": True, "requested": False}


def test_release_plan_is_side_effect_free_and_reports_missing_scope(monkeypatch) -> None:
    manifest = {
        "schema": "warehouse.hosting-application.v2.3",
        "contract_digest": "manifest-digest",
        "data": {"database_policy": "platform_managed"},
        "lifecycle": {
            "jobs": [
                {
                    "name": "migrate",
                    "database_access": "migration",
                    "required_before_activation": True,
                }
            ]
        },
        "acceptance": {"http": [{"name": "health", "path": "/healthz"}]},
    }

    @contextmanager
    def fake_tenant_session(_tenant_id):
        yield object()

    monkeypatch.setattr(workspace_releases, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        workspace_releases,
        "_workspace_row",
        lambda *_args, **_kwargs: {"active_deployment_id": None, "config": {}},
    )
    monkeypatch.setattr(
        workspace_releases,
        "_verified_source",
        lambda *_args, **_kwargs: {
            "id": UUID("00000000-0000-0000-0000-000000000204"),
            "sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        workspace_releases,
        "_source_signals",
        lambda *_args, **_kwargs: {"hosting_manifest": manifest},
    )
    monkeypatch.setattr(workspace_releases, "_require_manifest_database_policy", lambda *_: None)
    monkeypatch.setattr(
        workspace_releases,
        "_resolve_runtime_contract",
        lambda *_: ("api", {"runtime_family": "python", "profile_key": "python312-v1"}),
    )

    result = workspace_releases.plan_workspace_release(
        _credential("deploy:read", "deploy:write"),
        {"runtime_type": "auto"},
        object(),
    )

    assert result["ok"] is False
    assert result["plan"]["delivery_mode"] == "runtime"
    assert result["plan"]["required_jobs"][0]["name"] == "migrate"
    assert result["plan"]["blockers"] == [
        {
            "code": "workspace_key_missing_scopes",
            "scopes": ["database:admin"],
            "message": "The current workspace key cannot execute this release plan.",
        }
    ]


def test_public_release_requires_explicit_activation() -> None:
    release = workspace_releases._public_release(
        {
            "id": UUID("00000000-0000-0000-0000-000000000205"),
            "legacy_id": 7,
            "state": "awaiting_activation",
            "lease_owner": "worker-private",
            "lease_expires_at": None,
            "request_payload": {"start_command": "private-command"},
        }
    )

    assert release["id"] == 7
    assert release["next_action"] == "activate_release"
    assert "lease_owner" not in release
    assert "request_payload" not in release


def test_release_api_and_cli_expose_the_high_level_workflow() -> None:
    routes = {
        (method, route.path)
        for route in workspace_router.routes
        for method in (getattr(route, "methods", None) or set())
    }
    expected = {
        ("POST", "/api/workspaces/v1/releases/plan"),
        ("POST", "/api/workspaces/v1/releases"),
        ("GET", "/api/workspaces/v1/releases/{release_id}"),
        ("POST", "/api/workspaces/v1/releases/{release_id}/resume"),
        ("POST", "/api/workspaces/v1/releases/{release_id}/activate"),
        ("POST", "/api/workspaces/v1/releases/{release_id}/rollback"),
    }
    assert expected.issubset(routes)

    args = dam._parser().parse_args(
        [
            "--key",
            "wak_test",
            "release",
            "run",
            "--source",
            "00000000-0000-0000-0000-000000000204",
            "--idempotency-key",
            "release-v1",
            "--activate",
        ]
    )
    assert dam.VERSION == "2.8.0"
    assert args.release_command == "run"
    assert args.activate is True


def test_release_migration_enforces_tenant_isolation_and_append_only_events() -> None:
    versions = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration = (versions / "20260815_0094_workspace_release_orchestration.py").read_text(
        encoding="utf-8"
    )
    contract = (versions / "20260815_0095_register_release_orchestration_contract.py").read_text(
        encoding="utf-8"
    )

    assert "CREATE TABLE digital_asset.release_sessions" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "trg_release_events_immutable" in migration
    assert 'warehouse_scope = "schema"' in migration
    assert 'warehouse_scope = "primary_data"' in contract
    assert "manual_activation', true" in contract
    assert "automatic_rollback', true" in contract


def test_schema_policy_distinguishes_constraints_from_executed_row_mutations() -> None:
    ddl = """
    CREATE TABLE sample(child uuid REFERENCES parent(id) ON DELETE CASCADE);
    CREATE TRIGGER touched BEFORE UPDATE ON sample EXECUTE FUNCTION app.touch_updated_at();
    GRANT SELECT, INSERT, UPDATE, DELETE ON sample TO warehouse_os;
    """

    assert _contains_row_mutation(ddl) is False
    assert _contains_row_mutation("UPDATE sample SET touched_at=now()") is True
    assert _contains_row_mutation("WITH changed AS (DELETE FROM sample RETURNING *) SELECT 1")
