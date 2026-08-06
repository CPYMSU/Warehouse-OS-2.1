from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from app.database_migration_controller import (
    REQUEST_SCHEMA,
    MigrationFailure,
    MigrationRequest,
    StateWriter,
    _bootstrap_standby_cursor,
    _failure_details,
    _revision_operations,
    _safe_error,
    build_plan,
    run_request,
    verified_backup,
)


def _policy(root: Path) -> Path:
    alembic = root / "alembic"
    alembic.mkdir(parents=True)
    (alembic / "migration-policy.json").write_text(
        json.dumps(
            {
                "schema": "warehouse.database-migration-policy.v1",
                "legacy_head": "legacy",
                "allowed_scopes": ["schema", "primary_data"],
                "standby_version_table": "alembic_version_standby",
            }
        ),
        encoding="utf-8",
    )
    config = root / "alembic.ini"
    config.write_text("[alembic]\n", encoding="utf-8")
    return config


def _migration(path: Path, scope: str, body: str) -> SimpleNamespace:
    path.write_text(
        f'warehouse_scope = "{scope}"\n\ndef upgrade():\n    {body}\n',
        encoding="utf-8",
    )
    return SimpleNamespace(
        revision=path.stem,
        path=str(path),
        module=SimpleNamespace(warehouse_scope=scope),
    )


class _Script:
    def __init__(self, legacy: SimpleNamespace, pending: list[SimpleNamespace]) -> None:
        self.legacy = legacy
        self.pending = pending

    def iterate_revisions(self, target: str, current: str | None):
        if target == "legacy" and current == "base":
            return iter([self.legacy])
        return iter(reversed(self.pending))


def test_request_validation_and_atomic_state_permissions(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema": REQUEST_SCHEMA,
                "release_id": "20260805T150000Z-abcdef123456-mac-primary-smart",
                "git_sha": "abcdef123456",
                "target_revision": "20260805_0078",
                "node_role": "primary",
                "requested_at": "2026-08-05T15:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    request = MigrationRequest.read(request_path)
    state_path = tmp_path / "status.json"
    StateWriter(state_path, request).write("planning")
    state = json.loads(state_path.read_text(encoding="utf-8"))

    assert state["status"] == "planning"
    assert state["target_revision"] == "20260805_0078"
    assert state_path.stat().st_mode & 0o777 == 0o600


def test_request_rejects_role_or_release_injection(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "schema": REQUEST_SCHEMA,
                "release_id": "release; rm -rf /",
                "git_sha": "abcdef1",
                "target_revision": "head",
                "node_role": "writer",
                "requested_at": "2026-08-05T15:00:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="release_id"):
        MigrationRequest.read(request_path)


def test_diagnostics_redact_database_passwords() -> None:
    error = RuntimeError(
        "connection postgresql+psycopg://warehouse_migrator:top-secret@db/warehouse_os "
        "password=also-secret"
    )
    message = _safe_error(error)

    assert "top-secret" not in message
    assert "also-secret" not in message
    assert message.count("[redacted]") == 2


def test_standby_permission_drift_requests_automatic_reseed() -> None:
    request = MigrationRequest(
        release_id="20260806T130000Z-abcdef123456-vultr-standby-smart",
        git_sha="abcdef123456",
        target_revision="20260806_0079",
        node_role="standby",
        requested_at="2026-08-06T13:00:00Z",
    )

    class InsufficientPrivilege(RuntimeError):
        sqlstate = "42501"

    class DatabaseFailure(RuntimeError):
        orig = InsufficientPrivilege("permission denied for schema app")

    assert _failure_details(request, DatabaseFailure()) == {
        "error_code": "standby_ownership_drift",
        "recovery_action": "reseed_standby_control_database",
    }


def test_revision_operation_scanner_separates_schema_and_data(tmp_path: Path) -> None:
    schema = tmp_path / "schema.py"
    schema.write_text(
        "def upgrade():\n"
        "    op.create_table('jobs')\n"
        "    op.get_bind().exec_driver_sql('ALTER TABLE jobs ADD COLUMN state text')\n",
        encoding="utf-8",
    )
    data = tmp_path / "data.py"
    data.write_text(
        "def upgrade():\n"
        "    op.execute(\"UPDATE jobs SET state='ready'\")\n",
        encoding="utf-8",
    )

    assert _revision_operations(schema) == (True, False, [])
    assert _revision_operations(data) == (False, True, [])


def test_revision_operation_scanner_detects_alembic_bulk_insert(tmp_path: Path) -> None:
    data = tmp_path / "bulk_data.py"
    data.write_text(
        "def upgrade():\n"
        "    op.bulk_insert(account_table, [{'name': 'system'}])\n",
        encoding="utf-8",
    )

    assert _revision_operations(data) == (False, True, [])


def test_policy_rejects_mixed_or_dynamic_sql(tmp_path: Path) -> None:
    config = _policy(tmp_path)
    legacy = SimpleNamespace(revision="legacy")
    mixed = _migration(
        tmp_path / "next_mixed.py",
        "schema",
        "op.execute('ALTER TABLE jobs ADD COLUMN state text; UPDATE jobs SET state=1')",
    )

    with pytest.raises(RuntimeError, match="row mutations"):
        build_plan(_Script(legacy, [mixed]), config, "legacy", mixed.revision, "primary")

    dynamic = _migration(
        tmp_path / "next_dynamic.py",
        "schema",
        "op.execute(build_sql())",
    )
    with pytest.raises(RuntimeError, match="dynamic SQL"):
        build_plan(_Script(legacy, [dynamic]), config, "legacy", dynamic.revision, "primary")


def test_repository_migrations_follow_the_post_baseline_policy() -> None:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    policy = json.loads(
        (config_path.parent / "alembic" / "migration-policy.json").read_text(
            encoding="utf-8"
        )
    )

    assert len(heads) == 1
    build_plan(
        script,
        config_path,
        str(policy["legacy_head"]),
        heads[0],
        "primary",
    )


def test_standby_refuses_legacy_gap_and_accepts_new_schema_revision(tmp_path: Path) -> None:
    config = _policy(tmp_path)
    legacy = SimpleNamespace(revision="legacy")
    script = _Script(legacy, [legacy])

    with pytest.raises(RuntimeError, match="automatic reseed required"):
        build_plan(script, config, None, "legacy", "standby")

    schema = _migration(
        tmp_path / "next_schema.py",
        "schema",
        "op.execute('CREATE TABLE app.jobs(id uuid PRIMARY KEY)')",
    )
    plan = build_plan(
        _Script(legacy, [schema]),
        config,
        "legacy",
        schema.revision,
        "standby",
    )
    assert [(item.revision, item.scope) for item in plan] == [
        ("next_schema", "schema")
    ]


def test_standby_cursor_bootstrap_requests_safe_reseed_without_primary_revision() -> None:
    class _EmptyResult:
        def scalar_one_or_none(self) -> None:
            return None

    class _Connection:
        def exec_driver_sql(self, _statement: str) -> None:
            return None

        def execute(self, _statement: object) -> _EmptyResult:
            return _EmptyResult()

        def commit(self) -> None:
            return None

    with pytest.raises(MigrationFailure) as raised:
        _bootstrap_standby_cursor(_Connection(), "alembic_version_standby")

    assert raised.value.code == "standby_legacy_gap"
    assert raised.value.recovery_action == "reseed_standby_control_database"


def test_verified_backup_keeps_password_out_of_process_arguments(tmp_path: Path) -> None:
    calls: list[tuple[list[str], dict[str, str]]] = []

    def runner(
        command: list[str],
        *,
        check: bool,
        env: dict[str, str],
        capture_output: bool,
        text: bool,
    ) -> SimpleNamespace:
        assert check and capture_output and text
        calls.append((command, env))
        if command[0] == "pg_dump":
            Path(command[command.index("--file") + 1]).write_bytes(b"verified-dump")
        return SimpleNamespace(returncode=0)

    filename, digest = verified_backup(
        "postgresql+psycopg://migrator:secret-value@postgres:5432/warehouse_os",
        tmp_path,
        "20260805T150000Z-abcdef123456-mac-primary-smart",
        runner=runner,
    )

    assert (tmp_path / filename).read_bytes() == b"verified-dump"
    assert digest
    assert all("secret-value" not in " ".join(command) for command, _ in calls)
    assert calls[0][1]["PGPASSWORD"] == "secret-value"
    assert "--no-publications" in calls[0][0]
    assert "--no-subscriptions" in calls[0][0]
    assert os.stat(tmp_path / filename).st_mode & 0o777 == 0o600


def test_safe_error_includes_sanitized_subprocess_stderr() -> None:
    error = subprocess.CalledProcessError(
        1,
        ["pg_dump"],
        stderr=(
            "pg_dump: ERROR: row security blocked token=private-value "
            "postgresql://backup:password-value@postgres/warehouse_os"
        ),
    )

    observed = _safe_error(error)

    assert "row security blocked" in observed
    assert "private-value" not in observed
    assert "password-value" not in observed
    assert "token=[redacted]" in observed


@pytest.mark.skipif(
    os.getenv("WAREHOUSE_RUN_INTEGRATION_TESTS") != "1",
    reason="requires the disposable PostgreSQL verification database",
)
def test_controller_noop_primary_and_standby_jobs_use_independent_cursors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    migration_url = os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    config = Path(__file__).resolve().parents[1] / "alembic.ini"

    def request(role: str, name: str) -> tuple[Path, Path]:
        request_path = tmp_path / f"{name}.request.json"
        status_path = tmp_path / f"{name}.status.json"
        request_path.write_text(
            json.dumps(
                {
                    "schema": REQUEST_SCHEMA,
                    "release_id": f"20260805T15000{name[-1]}Z-abcdef123456-{role}-smart",
                    "git_sha": "abcdef123456",
                    "target_revision": "20260806_0079",
                    "node_role": role,
                    "requested_at": "2026-08-05T15:00:00Z",
                }
            ),
            encoding="utf-8",
        )
        return request_path, status_path

    monkeypatch.setenv("WAREHOUSE_MIGRATION_DATABASE_URL", migration_url)
    monkeypatch.setenv("WAREHOUSE_NODE_ROLE", "primary")
    primary_request, primary_status = request("primary", "primary1")
    assert run_request(primary_request, primary_status, tmp_path / "backups", config) == 0
    assert json.loads(primary_status.read_text(encoding="utf-8"))["changed"] is False

    monkeypatch.setenv("WAREHOUSE_NODE_ROLE", "standby")
    standby_request, standby_status = request("standby", "standby2")
    try:
        assert run_request(standby_request, standby_status, tmp_path / "backups", config) == 0
        assert json.loads(standby_status.read_text(encoding="utf-8"))["status"] == "succeeded"
        engine = create_engine(migration_url)
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT version_num FROM app.alembic_version_standby")
            ).scalar_one() == "20260806_0079"
        engine.dispose()
    finally:
        engine = create_engine(migration_url)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS app.alembic_version_standby"))
        engine.dispose()
