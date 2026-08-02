"""Independent HDD-backed PostgreSQL provider for hosted workspaces.

The control-plane PostgreSQL database only stores bindings, encrypted
credentials, audit events and quota facts.  User-created records live in one
dedicated database and login role per workspace on the hosted HDD cluster.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
from cryptography.fernet import Fernet, InvalidToken
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings

HDD_DATABASE_PROVIDER_KEY = "warehouse_postgresql_hdd_data_api"
HDD_DATABASE_POOL_KEY = "hosted-db-hdd-01"
LEGACY_DATABASE_PROVIDER_KEY = "warehouse_postgresql_data_api"


class HostedDatabaseUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class HostedWriteResult:
    record: dict[str, object]
    database_bytes: int


_FORBIDDEN_MIGRATION_SQL = (
    "alter system",
    "create database",
    "drop database",
    "create role",
    "alter role",
    "drop role",
    "create tablespace",
    "copy program",
    "copy ",
    "set role",
    "session authorization",
    "grant ",
    "revoke ",
    "pg_read_file",
    "pg_write_file",
    "lo_import",
    "lo_export",
    "workspace_meta",
)


def configured(settings: Settings | None = None) -> bool:
    effective = settings or get_settings()
    return bool(effective.hosted_database_admin_url.get_secret_value().strip())


def health(settings: Settings | None = None) -> dict[str, object]:
    effective = settings or get_settings()
    if not configured(effective):
        return {"configured": False, "reachable": False}
    try:
        with psycopg.connect(
            _dsn(effective),
            connect_timeout=effective.hosted_database_connect_timeout_seconds,
        ) as connection:
            version, recovery = connection.execute(
                "SELECT current_setting('server_version_num')::integer, pg_is_in_recovery()"
            ).fetchone()
        return {
            "configured": True,
            "reachable": True,
            "server_version_num": int(version),
            "in_recovery": bool(recovery),
            "physical_medium": "hdd",
        }
    except Exception as exc:
        return {
            "configured": True,
            "reachable": False,
            "error": type(exc).__name__,
        }


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.integration_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(secret: str, settings: Settings) -> str:
    token = _fernet(settings).encrypt(secret.encode("utf-8")).decode("ascii")
    return f"fernet:v1:{token}"


def _decrypt(ciphertext: str, settings: Settings) -> str:
    if not ciphertext.startswith("fernet:v1:"):
        raise HostedDatabaseUnavailable("Workspace database credential format is invalid")
    try:
        return (
            _fernet(settings)
            .decrypt(ciphertext.removeprefix("fernet:v1:").encode("ascii"))
            .decode("utf-8")
        )
    except InvalidToken as exc:
        raise HostedDatabaseUnavailable(
            "Workspace database credential cannot be decrypted"
        ) from exc


def _identifiers(workspace_id: object) -> tuple[str, str]:
    compact = UUID(str(workspace_id)).hex
    return f"whdb_{compact}", f"whr_{compact}"


def _dsn(
    settings: Settings,
    *,
    database: str | None = None,
    username: str | None = None,
    password: str | None = None,
) -> str:
    raw = settings.hosted_database_admin_url.get_secret_value().strip()
    if not raw:
        raise HostedDatabaseUnavailable("HDD workspace database provider is not configured")
    url = make_url(raw).set(drivername="postgresql")
    if database is not None:
        url = url.set(database=database)
    if username is not None:
        url = url.set(username=username)
    if password is not None:
        url = url.set(password=password)
    return url.render_as_string(hide_password=False)


def _credential_secret(
    session: Session,
    binding: dict[str, object],
    settings: Settings,
    *,
    create: bool,
) -> str:
    ciphertext = session.execute(
        text(
            """
            SELECT secret_ciphertext
            FROM digital_asset.database_credentials
            WHERE database_binding_id = :binding_id
            """
        ),
        {"binding_id": binding["id"]},
    ).scalar_one_or_none()
    if ciphertext is not None:
        return _decrypt(str(ciphertext), settings)
    if not create:
        raise HostedDatabaseUnavailable("Workspace database credential is missing")
    secret = secrets.token_urlsafe(36)
    session.execute(
        text(
            """
            INSERT INTO digital_asset.database_credentials(
              tenant_id, database_binding_id, secret_ciphertext
            ) VALUES (:tenant_id, :binding_id, :ciphertext)
            """
        ),
        {
            "tenant_id": binding["tenant_id"],
            "binding_id": binding["id"],
            "ciphertext": _encrypt(secret, settings),
        },
    )
    return secret


def _ensure_physical_database(
    *,
    settings: Settings,
    tenant_id: object,
    workspace_id: object,
    database_ref: str,
    role_ref: str,
    password: str,
) -> None:
    try:
        with psycopg.connect(
            _dsn(settings),
            autocommit=True,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            role_exists = connection.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role_ref,)
            ).fetchone()
            if role_exists is None:
                connection.execute(
                    sql.SQL(
                        "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                        "NOINHERIT NOREPLICATION PASSWORD {}"
                    ).format(sql.Identifier(role_ref), sql.Literal(password))
                )
            else:
                connection.execute(
                    sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                        sql.Identifier(role_ref), sql.Literal(password)
                    )
                )
            database_exists = connection.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (database_ref,)
            ).fetchone()
            if database_exists is None:
                connection.execute(
                    sql.SQL(
                        "CREATE DATABASE {} OWNER {} TEMPLATE template0 ENCODING 'UTF8'"
                    ).format(sql.Identifier(database_ref), sql.Identifier(role_ref))
                )
            connection.execute(
                sql.SQL("REVOKE CONNECT ON DATABASE {} FROM PUBLIC").format(
                    sql.Identifier(database_ref)
                )
            )
            connection.execute(
                sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database_ref), sql.Identifier(role_ref)
                )
            )

        with psycopg.connect(
            _dsn(
                settings,
                database=database_ref,
                username=role_ref,
                password=password,
            ),
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            connection.execute("CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION CURRENT_USER")
            connection.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app.workspace_meta (
                  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
                  tenant_id uuid NOT NULL,
                  workspace_id uuid NOT NULL UNIQUE,
                  schema_version integer NOT NULL DEFAULT 1,
                  created_at timestamptz NOT NULL DEFAULT now()
                )
                """
            )
            existing = connection.execute(
                "SELECT tenant_id, workspace_id FROM app.workspace_meta WHERE singleton"
            ).fetchone()
            if existing is not None and (
                str(existing[0]) != str(tenant_id) or str(existing[1]) != str(workspace_id)
            ):
                raise HostedDatabaseUnavailable(
                    "Hosted database is already bound to another workspace"
                )
            connection.execute(
                """
                INSERT INTO app.workspace_meta(singleton, tenant_id, workspace_id)
                VALUES (true, %s, %s)
                ON CONFLICT (singleton) DO NOTHING
                """,
                (tenant_id, workspace_id),
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS app.workspace_records (
                  collection_name text NOT NULL
                    CHECK (collection_name ~ '^[a-z][a-z0-9_.-]{0,119}$'),
                  record_key text NOT NULL
                    CHECK (length(trim(record_key)) BETWEEN 1 AND 240),
                  payload jsonb NOT NULL DEFAULT '{}'::jsonb
                    CHECK (jsonb_typeof(payload) = 'object'),
                  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
                  created_at timestamptz NOT NULL DEFAULT now(),
                  updated_at timestamptz NOT NULL DEFAULT now(),
                  PRIMARY KEY (collection_name, record_key)
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workspace_records_updated
                  ON app.workspace_records(collection_name, updated_at DESC, record_key)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_workspace_records_payload
                  ON app.workspace_records USING gin(payload jsonb_path_ops)
                """
            )
    except HostedDatabaseUnavailable:
        raise
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"HDD workspace database is unavailable: {type(exc).__name__}"
        ) from exc


def _binding_connection(
    session: Session, binding: dict[str, object], settings: Settings
) -> psycopg.Connection[dict[str, Any]]:
    database_ref = str(binding.get("database_ref") or "")
    role_ref = str(binding.get("role_ref") or "")
    if not database_ref or not role_ref:
        raise HostedDatabaseUnavailable("Workspace database binding is incomplete")
    password = _credential_secret(session, binding, settings, create=False)
    try:
        return psycopg.connect(
            _dsn(
                settings,
                database=database_ref,
                username=role_ref,
                password=password,
            ),
            row_factory=dict_row,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        )
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"HDD workspace database is unavailable: {type(exc).__name__}"
        ) from exc


def runtime_database_url(
    session: Session,
    workspace_id: object,
    *,
    settings: Settings | None = None,
) -> str | None:
    """Return a workspace-role DSN for the trusted Runtime Controller only."""

    effective = settings or get_settings()
    binding = (
        session.execute(
            text(
                """
                SELECT * FROM digital_asset.database_bindings
                WHERE workspace_id=:workspace_id
                  AND provider_key=:provider_key
                  AND status='ready'
                ORDER BY created_at LIMIT 1
                """
            ),
            {
                "workspace_id": UUID(str(workspace_id)),
                "provider_key": HDD_DATABASE_PROVIDER_KEY,
            },
        )
        .mappings()
        .one_or_none()
    )
    if binding is None:
        return None
    database_ref = str(binding.get("database_ref") or "")
    role_ref = str(binding.get("role_ref") or "")
    if not database_ref or not role_ref:
        raise HostedDatabaseUnavailable("Workspace database binding is incomplete")
    password = _credential_secret(session, dict(binding), effective, create=False)
    return _dsn(
        effective,
        database=database_ref,
        username=role_ref,
        password=password,
    )


def execute_migration(
    session: Session,
    binding: dict[str, object],
    *,
    migration_sql: str,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Apply one transactional SQL batch as the bounded workspace role."""

    effective = settings or get_settings()
    source = str(migration_sql or "").strip()
    if not source or len(source.encode("utf-8")) > 2 * 1024 * 1024:
        raise ValueError("Migration SQL must be between 1 byte and 2 MiB")
    normalized = " ".join(source.lower().split())
    forbidden = next((term for term in _FORBIDDEN_MIGRATION_SQL if term in normalized), None)
    if forbidden:
        raise ValueError(f"Migration SQL contains a forbidden operation: {forbidden.strip()}")
    if "create extension" in normalized and "create extension vector" not in normalized:
        raise ValueError("Only the pre-approved vector extension may be requested")
    with _binding_connection(session, binding, effective) as connection:
        try:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (str(binding["workspace_id"]),),
            )
            connection.execute("SET LOCAL search_path TO app, public")
            connection.execute("SET LOCAL lock_timeout TO '10s'")
            connection.execute("SET LOCAL statement_timeout TO '120s'")
            connection.execute(source, prepare=False)
            database_bytes = _measure(connection)
        except Exception:
            connection.rollback()
            raise
    return {
        "transactional": True,
        "statement_count": 1,
        "database_bytes": database_bytes,
    }


def _credential_secret_from_binding(binding: dict[str, object], settings: Settings) -> str:
    ciphertext = str(binding.get("secret_ciphertext") or "")
    if not ciphertext:
        raise HostedDatabaseUnavailable("Workspace database credential is missing")
    return _decrypt(ciphertext, settings)


def _pg_environment(binding: dict[str, object], settings: Settings) -> dict[str, str]:
    password = _credential_secret_from_binding(binding, settings)
    url = make_url(
        _dsn(
            settings,
            database=str(binding["database_ref"]),
            username=str(binding["role_ref"]),
            password=password,
        )
    )
    return {
        **os.environ,
        "PGHOST": str(url.host or "127.0.0.1"),
        "PGPORT": str(url.port or 5432),
        "PGDATABASE": str(url.database or ""),
        "PGUSER": str(url.username or ""),
        "PGPASSWORD": str(url.password or ""),
        "PGCONNECT_TIMEOUT": str(settings.hosted_database_connect_timeout_seconds),
    }


def backup_database(
    binding: dict[str, object],
    target: Path,
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Create one verified custom-format logical backup without exposing DSNs."""

    effective = settings or get_settings()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    completed = subprocess.run(
        [
            "pg_dump",
            "--format=custom",
            "--compress=6",
            "--no-owner",
            "--no-acl",
            "--file",
            str(target),
        ],
        check=False,
        capture_output=True,
        env=_pg_environment(binding, effective),
        timeout=600,
    )
    if completed.returncode != 0 or not target.is_file():
        target.unlink(missing_ok=True)
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise HostedDatabaseUnavailable(
            "PostgreSQL backup failed" + (f": {detail}" if detail else "")
        )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {
        "sha256": digest,
        "size_bytes": target.stat().st_size,
        "format": "pg_custom",
    }


def restore_database(
    binding: dict[str, object],
    source: Path,
    *,
    expected_sha256: str,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Restore a same-workspace verified backup through the workspace role."""

    effective = settings or get_settings()
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if not secrets.compare_digest(actual, expected_sha256):
        raise HostedDatabaseUnavailable("Backup digest verification failed")
    completed = subprocess.run(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-acl",
            "--single-transaction",
            "--exit-on-error",
            str(source),
        ],
        check=False,
        capture_output=True,
        env=_pg_environment(binding, effective),
        timeout=900,
    )
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
        raise HostedDatabaseUnavailable(
            "PostgreSQL restore failed" + (f": {detail}" if detail else "")
        )
    return {"restored": True, "sha256": actual, "format": "pg_custom"}


def _measure(connection: psycopg.Connection[Any]) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(pg_total_relation_size(c.oid), 0)::bigint AS bytes
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname = 'app' AND c.relname = 'workspace_records'
          AND c.relkind = 'r'
        """
    ).fetchone()
    if row is None:
        return 0
    if isinstance(row, dict):
        return int(row["bytes"])
    return int(row[0])


def migrate_binding(
    session: Session,
    binding: dict[str, object],
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Idempotently copy a legacy control-plane record set to the HDD DB."""

    effective = settings or get_settings()
    if not configured(effective):
        raise HostedDatabaseUnavailable("HDD workspace database provider is not configured")
    database_ref, role_ref = _identifiers(binding["workspace_id"])
    secret = _credential_secret(session, binding, effective, create=True)
    _ensure_physical_database(
        settings=effective,
        tenant_id=binding["tenant_id"],
        workspace_id=binding["workspace_id"],
        database_ref=database_ref,
        role_ref=role_ref,
        password=secret,
    )
    source_rows = [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT collection_name, record_key, payload, version,
                       created_at, updated_at
                FROM digital_asset.workspace_records
                WHERE workspace_id = :workspace_id
                  AND database_binding_id = :database_id
                ORDER BY collection_name, record_key
                """
            ),
            {"workspace_id": binding["workspace_id"], "database_id": binding["id"]},
        )
        .mappings()
        .all()
    ]
    target_binding = {
        **binding,
        "database_ref": database_ref,
        "role_ref": role_ref,
    }
    with _binding_connection(session, target_binding, effective) as connection:
        for row in source_rows:
            connection.execute(
                """
                INSERT INTO app.workspace_records(
                  collection_name, record_key, payload, version,
                  created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (collection_name, record_key) DO UPDATE SET
                  payload = EXCLUDED.payload,
                  version = EXCLUDED.version,
                  updated_at = EXCLUDED.updated_at
                """,
                (
                    row["collection_name"],
                    row["record_key"],
                    Jsonb(row["payload"]),
                    row["version"],
                    row["created_at"],
                    row["updated_at"],
                ),
            )
        target_rows = connection.execute(
            """
            SELECT collection_name, record_key, payload, version
            FROM app.workspace_records
            ORDER BY collection_name, record_key
            """
        ).fetchall()
        target_count = len(target_rows)
        if target_count < len(source_rows):
            raise HostedDatabaseUnavailable("HDD workspace database copy verification failed")
        target_index = {(row["collection_name"], row["record_key"]): row for row in target_rows}
        for source in source_rows:
            target = target_index.get((source["collection_name"], source["record_key"]))
            source_payload = json.dumps(
                source["payload"], sort_keys=True, separators=(",", ":"), default=str
            )
            target_payload = json.dumps(
                target["payload"] if target else None,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            if (
                target is None
                or int(target["version"]) != int(source["version"])
                or target_payload != source_payload
            ):
                raise HostedDatabaseUnavailable(
                    "HDD workspace database content verification failed"
                )
        database_bytes = _measure(connection)

    updated = dict(
        session.execute(
            text(
                """
                UPDATE digital_asset.database_bindings
                SET provider_key = :provider_key,
                    isolation_mode = 'dedicated_database',
                    status = 'ready',
                    pool_key = :pool_key,
                    physical_medium = 'hdd',
                    database_ref = :database_ref,
                    role_ref = :role_ref,
                    actual_size_bytes = :actual_size_bytes,
                    size_measured_at = now(),
                    revision = revision + 1,
                    config = config || CAST(:config AS jsonb)
                WHERE id = :binding_id
                RETURNING *
                """
            ),
            {
                "provider_key": HDD_DATABASE_PROVIDER_KEY,
                "pool_key": HDD_DATABASE_POOL_KEY,
                "database_ref": database_ref,
                "role_ref": role_ref,
                "actual_size_bytes": database_bytes,
                "config": json.dumps(
                    {
                        "portable_data_api": True,
                        "native_dsn_exposed": False,
                        "migration_state": "hdd_verified",
                        "migrated_records": len(source_rows),
                        "migrated_at": datetime.now(UTC).isoformat(),
                        "billable_size_source": "pg_total_relation_size",
                    }
                ),
                "binding_id": binding["id"],
            },
        )
        .mappings()
        .one()
    )
    update_usage(session, updated, database_bytes=database_bytes)
    return updated


def update_usage(
    session: Session,
    binding: dict[str, object],
    *,
    database_bytes: int,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO digital_asset.workspace_usage(
              tenant_id, workspace_id, database_bytes, measured_at
            ) VALUES (:tenant_id, :workspace_id, :database_bytes, now())
            ON CONFLICT (tenant_id, workspace_id) DO UPDATE SET
              database_bytes = EXCLUDED.database_bytes,
              measured_at = now(),
              revision = digital_asset.workspace_usage.revision + 1
            """
        ),
        {
            "tenant_id": binding["tenant_id"],
            "workspace_id": binding["workspace_id"],
            "database_bytes": max(0, int(database_bytes)),
        },
    )


def schema(session: Session, binding: dict[str, object]) -> tuple[list[dict[str, object]], int]:
    with _binding_connection(session, binding, get_settings()) as connection:
        rows = connection.execute(
            """
            SELECT collection_name AS name, count(*)::integer AS records,
                   max(updated_at) AS updated_at
            FROM app.workspace_records
            GROUP BY collection_name
            ORDER BY collection_name
            """
        ).fetchall()
        size = _measure(connection)
    return [dict(row) for row in rows], size


def list_records(
    session: Session,
    binding: dict[str, object],
    *,
    collection: str,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, object]], int]:
    with _binding_connection(session, binding, get_settings()) as connection:
        rows = connection.execute(
            """
            SELECT record_key, payload, version, created_at, updated_at
            FROM app.workspace_records
            WHERE collection_name = %s
            ORDER BY updated_at DESC, record_key
            LIMIT %s OFFSET %s
            """,
            (collection, limit, offset),
        ).fetchall()
        size = _measure(connection)
    return [dict(row) for row in rows], size


def put_record(
    session: Session,
    binding: dict[str, object],
    *,
    workspace_id: object,
    collection: str,
    record_key: str,
    payload: dict[str, object],
    expected_version: int | None,
    quota_bytes: int,
    non_database_bytes: int,
) -> HostedWriteResult:
    settings = get_settings()
    with _binding_connection(session, binding, settings) as connection:
        try:
            connection.execute(
                "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                (str(workspace_id),),
            )
            current = connection.execute(
                """
                SELECT version FROM app.workspace_records
                WHERE collection_name = %s AND record_key = %s
                FOR UPDATE
                """,
                (collection, record_key),
            ).fetchone()
            current_version = int(current["version"]) if current is not None else 0
            if expected_version is not None and expected_version != current_version:
                raise ValueError(
                    json.dumps(
                        {
                            "reason": "version_conflict",
                            "expected": expected_version,
                            "current": current_version,
                        }
                    )
                )
            row = connection.execute(
                """
                INSERT INTO app.workspace_records(
                  collection_name, record_key, payload
                ) VALUES (%s, %s, %s)
                ON CONFLICT (collection_name, record_key) DO UPDATE SET
                  payload = EXCLUDED.payload,
                  version = app.workspace_records.version + 1,
                  updated_at = now()
                RETURNING record_key, payload, version, created_at, updated_at
                """,
                (collection, record_key, Jsonb(payload)),
            ).fetchone()
            database_bytes = _measure(connection)
            total = max(0, int(non_database_bytes)) + database_bytes
            if total > int(quota_bytes):
                raise OverflowError(
                    json.dumps(
                        {
                            "reason": "workspace_quota_exceeded",
                            "quota_bytes": int(quota_bytes),
                            "used_bytes": total,
                            "database_bytes": database_bytes,
                        }
                    )
                )
        except Exception:
            connection.rollback()
            raise
    return HostedWriteResult(record=dict(row), database_bytes=database_bytes)
