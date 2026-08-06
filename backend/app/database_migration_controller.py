"""Background, single-writer database migration controller.

Release deployment submits an immutable request and starts this module as a
detached one-shot worker.  The worker owns backup, policy validation, database
locking, Alembic execution and durable status reporting.  API processes never
receive the migration identity and never run migrations during startup.

Future migrations must declare one of these module-level scopes::

    warehouse_scope = "schema"
    warehouse_scope = "primary_data"

Schema revisions run on the standby before the primary.  Primary-data
revisions execute only on the primary; the standby advances a node-local
Alembic cursor so subscriber-local writes can never conflict with the primary
``app.alembic_version`` row carried by logical replication.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from alembic import command

STATE_SCHEMA = "warehouse.database-migration-state.v1"
REQUEST_SCHEMA = "warehouse.database-migration-request.v1"
ADVISORY_LOCK_ID = 0x57484D4947524154  # ASCII-ish "WHMIGRAT", signed int64 safe.
ALLOWED_SCOPES = {"schema", "primary_data"}
RELEASE_PATTERN = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[A-Za-z0-9._-]{1,100}$")
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,128}$")
SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")
SQL_DML = re.compile(r"\b(?:INSERT|UPDATE|DELETE|MERGE|COPY)\b", re.IGNORECASE)
SQL_DDL = re.compile(
    r"\b(?:CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE|COMMENT|REINDEX|CLUSTER)\b",
    re.IGNORECASE,
)
ALEMBIC_DDL_CALLS = {
    "add_column",
    "alter_column",
    "create_check_constraint",
    "create_exclude_constraint",
    "create_foreign_key",
    "create_index",
    "create_primary_key",
    "create_table",
    "create_unique_constraint",
    "drop_column",
    "drop_constraint",
    "drop_index",
    "drop_table",
    "rename_table",
}
ALEMBIC_DML_CALLS = {"bulk_insert"}


class MigrationFailure(RuntimeError):
    def __init__(self, message: str, *, code: str, recovery_action: str = "") -> None:
        super().__init__(message)
        self.code = code
        self.recovery_action = recovery_action


def _failure_details(
    request: MigrationRequest | None, exc: BaseException
) -> dict[str, object]:
    if isinstance(exc, MigrationFailure):
        details: dict[str, object] = {"error_code": exc.code}
        if exc.recovery_action:
            details["recovery_action"] = exc.recovery_action
        return details
    database_error = getattr(exc, "orig", exc)
    sqlstate = str(
        getattr(database_error, "sqlstate", "")
        or getattr(database_error, "pgcode", "")
    )
    if request is not None and request.node_role == "standby" and sqlstate == "42501":
        return {
            "error_code": "standby_ownership_drift",
            "recovery_action": "reseed_standby_control_database",
        }
    return {}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _safe_error(exc: BaseException) -> str:
    """Return bounded diagnostics without credentials or connection strings."""

    diagnostics = [str(exc)]
    if isinstance(exc, subprocess.CalledProcessError):
        diagnostics.extend(
            value for value in (exc.stderr, exc.stdout) if isinstance(value, str)
        )
    value = " ".join(diagnostics).replace("\x00", " ")
    value = re.sub(
        r"(?i)(password|passwd|pwd|token|secret)\s*[=:]\s*[^\s,;]+",
        r"\1=[redacted]",
        value,
    )
    value = re.sub(
        r"(?i)(postgres(?:ql)?(?:\+[^:]+)?://[^:/\s]+:)[^@\s]+@",
        r"\1[redacted]@",
        value,
    )
    return " ".join(value.split())[:1200] or exc.__class__.__name__


def _atomic_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class MigrationRequest:
    release_id: str
    git_sha: str
    target_revision: str
    node_role: Literal["primary", "standby"]
    requested_at: str

    @classmethod
    def read(cls, path: Path) -> MigrationRequest:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or raw.get("schema") != REQUEST_SCHEMA:
            raise ValueError("migration request schema is invalid")
        release_id = str(raw.get("release_id") or "")
        git_sha = str(raw.get("git_sha") or "")
        target_revision = str(raw.get("target_revision") or "")
        node_role = str(raw.get("node_role") or "")
        requested_at = str(raw.get("requested_at") or "")
        if not RELEASE_PATTERN.fullmatch(release_id):
            raise ValueError("migration release_id is invalid")
        if not SHA_PATTERN.fullmatch(git_sha):
            raise ValueError("migration git_sha is invalid")
        if not IDENTIFIER_PATTERN.fullmatch(target_revision):
            raise ValueError("migration target_revision is invalid")
        if node_role not in {"primary", "standby"}:
            raise ValueError("migration node_role must be primary or standby")
        try:
            datetime.fromisoformat(requested_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("migration requested_at is invalid") from exc
        return cls(
            release_id=release_id,
            git_sha=git_sha,
            target_revision=target_revision,
            node_role=node_role,  # type: ignore[arg-type]
            requested_at=requested_at,
        )


@dataclass(frozen=True)
class RevisionPlan:
    revision: str
    scope: Literal["legacy", "schema", "primary_data"]


class StateWriter:
    def __init__(self, path: Path, request: MigrationRequest) -> None:
        self.path = path
        self.request = request
        self.started_at = _now()
        self.attempt = 1
        if path.is_file():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
                if previous.get("release_id") == request.release_id:
                    self.attempt = max(1, int(previous.get("attempt") or 0) + 1)
            except (OSError, ValueError, TypeError):
                pass

    def write(self, status: str, **details: object) -> None:
        payload: dict[str, object] = {
            "schema": STATE_SCHEMA,
            "release_id": self.request.release_id,
            "git_sha": self.request.git_sha,
            "target_revision": self.request.target_revision,
            "node_role": self.request.node_role,
            "status": status,
            "attempt": self.attempt,
            "requested_at": self.request.requested_at,
            "started_at": self.started_at,
            "updated_at": _now(),
        }
        payload.update(details)
        _atomic_json(self.path, payload)


def _call_name(node: ast.Call) -> str:
    function = node.func
    if isinstance(function, ast.Attribute):
        return function.attr
    if isinstance(function, ast.Name):
        return function.id
    return ""


def _literal_sql(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Call) and _call_name(node) in {"text", "sql"} and node.args:
        return _literal_sql(node.args[0])
    return None


def _revision_operations(path: Path) -> tuple[bool, bool, list[str]]:
    """Return (has_ddl, has_dml, dynamic_sql_calls) for one migration file."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    has_ddl = False
    has_dml = False
    dynamic: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node)
        if name in ALEMBIC_DDL_CALLS:
            has_ddl = True
            continue
        if name in ALEMBIC_DML_CALLS:
            has_dml = True
            continue
        if name not in {"execute", "exec_driver_sql"} or not node.args:
            continue
        sql = _literal_sql(node.args[0])
        if sql is None:
            dynamic.append(f"line {getattr(node, 'lineno', '?')}")
            continue
        has_ddl = has_ddl or bool(SQL_DDL.search(sql))
        has_dml = has_dml or bool(SQL_DML.search(sql))
    return has_ddl, has_dml, dynamic


def _policy(config_path: Path) -> dict[str, object]:
    path = config_path.parent / "alembic" / "migration-policy.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "warehouse.database-migration-policy.v1":
        raise RuntimeError("database migration policy schema is invalid")
    if not IDENTIFIER_PATTERN.fullmatch(str(raw.get("legacy_head") or "")):
        raise RuntimeError("database migration policy legacy_head is invalid")
    if set(raw.get("allowed_scopes") or []) != ALLOWED_SCOPES:
        raise RuntimeError("database migration policy scopes are invalid")
    version_table = str(raw.get("standby_version_table") or "")
    if not re.fullmatch(r"[a-z][a-z0-9_]{2,62}", version_table):
        raise RuntimeError("database migration standby version table is invalid")
    return raw


def build_plan(
    script: ScriptDirectory,
    config_path: Path,
    current_revision: str | None,
    target_revision: str,
    node_role: str,
) -> list[RevisionPlan]:
    policy = _policy(config_path)
    legacy_head = str(policy["legacy_head"])
    legacy_revisions = {
        revision.revision for revision in script.iterate_revisions(legacy_head, "base")
    }
    try:
        pending = list(reversed(list(script.iterate_revisions(target_revision, current_revision))))
    except Exception as exc:
        raise RuntimeError("target revision is not a forward descendant of the database") from exc
    plan: list[RevisionPlan] = []
    for revision in pending:
        if revision.revision in legacy_revisions:
            if node_role == "standby":
                raise MigrationFailure(
                    "standby is behind the controller legacy baseline; automatic reseed required",
                    code="standby_legacy_gap",
                    recovery_action="reseed_standby_control_database",
                )
            plan.append(RevisionPlan(revision.revision, "legacy"))
            continue
        scope = getattr(revision.module, "warehouse_scope", None)
        if scope not in ALLOWED_SCOPES:
            raise RuntimeError(
                f"migration {revision.revision} must declare warehouse_scope as "
                "schema or primary_data"
            )
        if not revision.path:
            raise RuntimeError(f"migration {revision.revision} has no inspectable source path")
        has_ddl, has_dml, dynamic = _revision_operations(Path(revision.path))
        if dynamic:
            raise RuntimeError(
                f"migration {revision.revision} uses dynamic SQL at {', '.join(dynamic)}"
            )
        if scope == "schema" and has_dml:
            raise RuntimeError(f"schema migration {revision.revision} contains row mutations")
        if scope == "primary_data" and has_ddl:
            raise RuntimeError(f"primary_data migration {revision.revision} contains DDL")
        plan.append(RevisionPlan(revision.revision, scope))
    return plan


def _current_revision(connection: Connection, version_table: str) -> str | None:
    context = MigrationContext.configure(
        connection,
        opts={"version_table_schema": "app", "version_table": version_table},
    )
    heads = tuple(context.get_current_heads())
    if len(heads) > 1:
        raise RuntimeError("database has multiple Alembic heads")
    return heads[0] if heads else None


def _bootstrap_standby_cursor(connection: Connection, version_table: str) -> None:
    connection.exec_driver_sql(
        f"""
        CREATE TABLE IF NOT EXISTS app.{version_table} (
          version_num varchar(32) NOT NULL PRIMARY KEY
        )
        """
    )
    local_revision = connection.execute(
        text(f"SELECT version_num FROM app.{version_table}")
    ).scalar_one_or_none()
    if local_revision is None:
        primary_revision = connection.execute(
            text("SELECT version_num FROM app.alembic_version")
        ).scalar_one_or_none()
        if primary_revision is None:
            raise MigrationFailure(
                "standby cannot bootstrap without the replicated primary revision",
                code="standby_legacy_gap",
                recovery_action="reseed_standby_control_database",
            )
        connection.execute(
            text(f"INSERT INTO app.{version_table}(version_num) VALUES (:revision)"),
            {"revision": str(primary_revision)},
        )
    connection.commit()


def _backup_environment(database_url: str) -> tuple[dict[str, str], str]:
    parsed = make_url(database_url)
    environment = os.environ.copy()
    if parsed.host:
        environment["PGHOST"] = parsed.host
    if parsed.port:
        environment["PGPORT"] = str(parsed.port)
    if parsed.username:
        environment["PGUSER"] = parsed.username
    if parsed.password:
        environment["PGPASSWORD"] = parsed.password
    database = parsed.database or "warehouse_os"
    return environment, database


def verified_backup(
    database_url: str,
    backup_dir: Path,
    release_id: str,
    *,
    runner: Any = subprocess.run,
) -> tuple[str, str]:
    backup_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_dir, 0o700)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"{timestamp}-{release_id}-control.dump"
    final = backup_dir / filename
    partial = backup_dir / f".{filename}.partial"
    environment, database = _backup_environment(database_url)
    partial.unlink(missing_ok=True)
    try:
        runner(
            [
                "pg_dump",
                "--dbname",
                database,
                "--format",
                "custom",
                "--no-publications",
                "--no-subscriptions",
                "--file",
                str(partial),
            ],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
        runner(
            ["pg_restore", "--list", str(partial)],
            check=True,
            env=environment,
            capture_output=True,
            text=True,
        )
        os.chmod(partial, 0o600)
        digest = hashlib.sha256(partial.read_bytes()).hexdigest()
        os.replace(partial, final)
        checksum = final.with_suffix(final.suffix + ".sha256")
        checksum.write_text(f"{digest}  {filename}\n", encoding="ascii")
        os.chmod(checksum, 0o600)
        return filename, digest
    except Exception:
        partial.unlink(missing_ok=True)
        raise


class DatabaseMigrationController:
    def __init__(
        self,
        request: MigrationRequest,
        state: StateWriter,
        config_path: Path,
        backup_dir: Path,
        database_url: str,
        backup_database_url: str | None = None,
        *,
        engine: Engine | None = None,
    ) -> None:
        self.request = request
        self.state = state
        self.config_path = config_path
        self.backup_dir = backup_dir
        self.database_url = database_url
        self.backup_database_url = backup_database_url or database_url
        self.engine = engine or create_engine(database_url, poolclass=NullPool, pool_pre_ping=True)

    def _alembic_config(self, connection: Connection, version_table: str) -> Config:
        config = Config(str(self.config_path))
        config.attributes["connection"] = connection
        config.attributes["version_table"] = version_table
        return config

    def run(self) -> None:
        configured_role = os.getenv("WAREHOUSE_NODE_ROLE", self.request.node_role)
        if configured_role != self.request.node_role:
            raise RuntimeError("migration request node_role does not match the configured node")
        version_table = "alembic_version"
        policy = _policy(self.config_path)
        if self.request.node_role == "standby":
            version_table = str(policy["standby_version_table"])
        self.state.write("planning")
        connection = self.engine.connect()
        locked = False
        try:
            connection.exec_driver_sql("SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE")
            connection.commit()
            locked = bool(
                connection.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"),
                    {"lock_id": ADVISORY_LOCK_ID},
                ).scalar_one()
            )
            connection.commit()
            if not locked:
                raise RuntimeError("another database migration controller holds the migration lock")
            if self.request.node_role == "standby":
                _bootstrap_standby_cursor(connection, version_table)
            current = _current_revision(connection, version_table)
            connection.commit()
            config = self._alembic_config(connection, version_table)
            script = ScriptDirectory.from_config(config)
            if script.get_revision(self.request.target_revision) is None:
                raise RuntimeError("requested Alembic target does not exist in the candidate image")
            plan = build_plan(
                script,
                self.config_path,
                current,
                self.request.target_revision,
                self.request.node_role,
            )
            plan_payload = [
                {"revision": item.revision, "scope": item.scope} for item in plan
            ]
            if not plan:
                self.state.write(
                    "succeeded",
                    current_revision=current,
                    plan=[],
                    changed=False,
                    completed_at=_now(),
                )
                return
            backup_name: str | None = None
            backup_sha256: str | None = None
            if self.request.node_role == "primary":
                self.state.write("backing_up", current_revision=current, plan=plan_payload)
                backup_name, backup_sha256 = verified_backup(
                    self.backup_database_url,
                    self.backup_dir,
                    self.request.release_id,
                )
            self.state.write(
                "migrating",
                current_revision=current,
                plan=plan_payload,
                backup=backup_name,
                backup_sha256=backup_sha256,
            )
            for item in plan:
                if self.request.node_role == "standby" and item.scope == "primary_data":
                    command.stamp(config, item.revision)
                else:
                    command.upgrade(config, item.revision)
                connection.commit()
            self.state.write(
                "verifying",
                current_revision=current,
                plan=plan_payload,
                backup=backup_name,
                backup_sha256=backup_sha256,
            )
            observed = _current_revision(connection, version_table)
            connection.commit()
            if observed != self.request.target_revision:
                raise RuntimeError(
                    f"migration verification expected {self.request.target_revision}, "
                    f"observed {observed}"
                )
            self.state.write(
                "succeeded",
                current_revision=observed,
                plan=plan_payload,
                backup=backup_name,
                backup_sha256=backup_sha256,
                changed=True,
                completed_at=_now(),
            )
        finally:
            if locked:
                try:
                    connection.execute(
                        text("SELECT pg_advisory_unlock(:lock_id)"),
                        {"lock_id": ADVISORY_LOCK_ID},
                    )
                    connection.commit()
                except Exception:
                    pass
            connection.close()
            self.engine.dispose()


def run_request(
    request_path: Path,
    status_path: Path,
    backup_dir: Path,
    config_path: Path,
) -> int:
    request: MigrationRequest | None = None
    state: StateWriter | None = None
    try:
        request = MigrationRequest.read(request_path)
        state = StateWriter(status_path, request)
        database_url = os.getenv("WAREHOUSE_MIGRATION_DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("WAREHOUSE_MIGRATION_DATABASE_URL is required")
        backup_database_url = os.getenv("WAREHOUSE_BACKUP_DATABASE_URL", "").strip()
        DatabaseMigrationController(
            request,
            state,
            config_path,
            backup_dir,
            database_url,
            backup_database_url,
        ).run()
        return 0
    except Exception as exc:
        message = _safe_error(exc)
        failure_details = _failure_details(request, exc)
        if state is not None:
            state.write("failed", error=message, completed_at=_now(), **failure_details)
        else:
            _atomic_json(
                status_path,
                {
                    "schema": STATE_SCHEMA,
                    "status": "failed",
                    "error": message,
                    **failure_details,
                    "updated_at": _now(),
                    "completed_at": _now(),
                },
            )
        print(json.dumps({"status": "failed", "error": message}), file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument(
        "--alembic-config",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "alembic.ini",
    )
    arguments = parser.parse_args(argv)
    raise SystemExit(
        run_request(
            arguments.request,
            arguments.status,
            arguments.backup_dir,
            arguments.alembic_config,
        )
    )


if __name__ == "__main__":
    main()
