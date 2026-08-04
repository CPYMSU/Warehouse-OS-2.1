"""PostgreSQL providers behind the stable workspace database binding.

The control-plane PostgreSQL database only stores bindings, encrypted
credentials, audit events and quota facts.  User-created records live in one
dedicated database and login role per workspace on the hosted HDD cluster, or
in a customer-owned PostgreSQL database reached through a validated binding.
Neither managed passwords nor external DSNs leave this trusted provider layer.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
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
EXTERNAL_POSTGRESQL_PROVIDER_KEY = "external_postgresql"
POSTGRESQL_PROVIDER_KEYS = frozenset(
    {HDD_DATABASE_PROVIDER_KEY, EXTERNAL_POSTGRESQL_PROVIDER_KEY}
)
_MANAGED_CREDENTIAL_KIND = "managed_password"
_EXTERNAL_CREDENTIAL_KIND = "external_dsn"
_BLOCKED_EXTERNAL_HOSTS = frozenset(
    {
        "localhost",
        "host.docker.internal",
        "metadata.google.internal",
        "metadata.internal",
    }
)
MANAGED_CAPABILITIES: dict[str, bool] = {
    "runtime_dsn": True,
    "collection_data_api": True,
    "relational_data_api": True,
    "schema_introspection": True,
    "migrations": True,
    "platform_backup": True,
    "platform_quota": True,
    "vector_extension": True,
}
EXTERNAL_CAPABILITIES: dict[str, bool] = {
    "runtime_dsn": True,
    "collection_data_api": False,
    "relational_data_api": True,
    "schema_introspection": True,
    "migrations": True,
    "platform_backup": False,
    "platform_quota": False,
}


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
_VECTOR_EXTENSION_SQL = re.compile(
    r"\bcreate\s+extension\s+(?:if\s+not\s+exists\s+)?(?:\"vector\"|vector)\b",
    re.IGNORECASE,
)
_POSTGRESQL_CLIENT_MAJOR = 18


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


def _external_url(
    database_url: str,
    settings: Settings,
) -> tuple[str, dict[str, object]]:
    """Normalize one customer DSN and enforce the outbound network policy."""

    source = str(database_url or "").strip()
    if not source or len(source.encode("utf-8")) > 16_384:
        raise ValueError("External PostgreSQL URL must be between 1 and 16384 bytes")
    try:
        url = make_url(source)
    except Exception as exc:
        raise ValueError("External PostgreSQL URL is invalid") from exc
    if url.drivername.split("+", 1)[0] != "postgresql":
        raise ValueError("Only external PostgreSQL databases are supported")
    if not url.host or not url.database or not url.username or url.password is None:
        raise ValueError(
            "External PostgreSQL URL requires host, database, username and password"
        )
    host = str(url.host).rstrip(".").lower()
    if host in _BLOCKED_EXTERNAL_HOSTS or host.endswith(".localhost"):
        raise ValueError("External PostgreSQL host is reserved")
    port = int(url.port or 5432)
    if not 1 <= port <= 65535:
        raise ValueError("External PostgreSQL port is invalid")
    try:
        addresses = {
            item[4][0]
            for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise ValueError("External PostgreSQL host cannot be resolved") from exc
    if not addresses:
        raise ValueError("External PostgreSQL host has no reachable address")
    if not settings.external_database_allow_private_hosts:
        for address in addresses:
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as exc:
                raise ValueError("External PostgreSQL host resolved unexpectedly") from exc
            if not parsed.is_global:
                raise ValueError(
                    "External PostgreSQL private or reserved addresses require a governed "
                    "private-network connector"
                )
    sslmode = str(url.query.get("sslmode") or "").strip().lower()
    if settings.external_database_require_tls:
        if sslmode in {"disable", "allow", "prefer"}:
            raise ValueError("External PostgreSQL TLS cannot be disabled")
        if not sslmode:
            url = url.update_query_dict({"sslmode": "require"})
            sslmode = "require"
    normalized = url.set(drivername="postgresql").render_as_string(hide_password=False)
    return normalized, {
        "engine": "postgresql",
        "database": str(url.database),
        "role": str(url.username),
        "port": port,
        "tls_mode": sslmode or "provider_default",
        "address_count": len(addresses),
    }


def validate_external_database_url(
    database_url: str,
    *,
    settings: Settings | None = None,
) -> tuple[str, dict[str, object]]:
    """Verify a bounded, non-privileged external PostgreSQL connection."""

    effective = settings or get_settings()
    normalized, metadata = _external_url(database_url, effective)
    try:
        with psycopg.connect(
            normalized,
            row_factory=dict_row,
            connect_timeout=effective.hosted_database_connect_timeout_seconds,
            application_name="warehouse-workspace-database-validator",
        ) as connection:
            observed = connection.execute(
                """
                SELECT current_database() AS database_name,
                       current_user AS role_name,
                       current_setting('server_version_num')::integer AS server_version_num,
                       pg_is_in_recovery() AS in_recovery,
                       role.rolsuper, role.rolcreatedb, role.rolcreaterole,
                       role.rolreplication, role.rolbypassrls
                FROM pg_roles AS role
                WHERE role.rolname=current_user
                """
            ).fetchone()
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"External PostgreSQL validation failed: {type(exc).__name__}"
        ) from exc
    if observed is None:
        raise HostedDatabaseUnavailable("External PostgreSQL role could not be inspected")
    privileged = [
        key
        for key in ("rolsuper", "rolcreatedb", "rolcreaterole", "rolreplication", "rolbypassrls")
        if bool(observed[key])
    ]
    if privileged:
        raise ValueError(
            "External PostgreSQL must use a bounded application role without "
            "superuser, role, database, replication or RLS-bypass privileges"
        )
    return normalized, {
        **metadata,
        "database": str(observed["database_name"]),
        "role": str(observed["role_name"]),
        "server_version_num": int(observed["server_version_num"]),
        "in_recovery": bool(observed["in_recovery"]),
        "validated": True,
    }


def _credential_secret(
    session: Session,
    binding: dict[str, object],
    settings: Settings,
    *,
    create: bool,
    expected_kind: str = _MANAGED_CREDENTIAL_KIND,
) -> str:
    credential = (
        session.execute(
            text(
                """
                SELECT secret_ciphertext, credential_kind
                FROM digital_asset.database_credentials
                WHERE database_binding_id = :binding_id
                """
            ),
            {"binding_id": binding["id"]},
        )
        .mappings()
        .one_or_none()
    )
    if credential is not None:
        if str(credential["credential_kind"]) != expected_kind:
            raise HostedDatabaseUnavailable("Workspace database credential kind is invalid")
        return _decrypt(str(credential["secret_ciphertext"]), settings)
    if not create:
        raise HostedDatabaseUnavailable("Workspace database credential is missing")
    if expected_kind != _MANAGED_CREDENTIAL_KIND:
        raise HostedDatabaseUnavailable("External database credential must be supplied")
    secret = secrets.token_urlsafe(36)
    session.execute(
        text(
            """
            INSERT INTO digital_asset.database_credentials(
              tenant_id, database_binding_id, secret_ciphertext, credential_kind
            ) VALUES (:tenant_id, :binding_id, :ciphertext, :credential_kind)
            """
        ),
        {
            "tenant_id": binding["tenant_id"],
            "binding_id": binding["id"],
            "ciphertext": _encrypt(secret, settings),
            "credential_kind": _MANAGED_CREDENTIAL_KIND,
        },
    )
    return secret


def provision_external_binding(
    session: Session,
    binding: dict[str, object],
    *,
    database_url: str,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Validate and seal a customer-owned PostgreSQL DSN into one binding."""

    effective = settings or get_settings()
    normalized, observed = validate_external_database_url(database_url, settings=effective)
    session.execute(
        text(
            """
            INSERT INTO digital_asset.database_credentials(
              tenant_id,database_binding_id,secret_ciphertext,credential_kind,
              last_validated_at
            ) VALUES (
              :tenant_id,:binding_id,:ciphertext,:credential_kind,now()
            )
            ON CONFLICT (tenant_id,database_binding_id) DO UPDATE SET
              secret_ciphertext=EXCLUDED.secret_ciphertext,
              credential_kind=EXCLUDED.credential_kind,
              rotated_at=now(),
              last_validated_at=now()
            """
        ),
        {
            "tenant_id": binding["tenant_id"],
            "binding_id": binding["id"],
            "ciphertext": _encrypt(normalized, effective),
            "credential_kind": _EXTERNAL_CREDENTIAL_KIND,
        },
    )
    return dict(
        session.execute(
            text(
                """
                UPDATE digital_asset.database_bindings
                SET provider_key=:provider_key,
                    ownership_mode='customer_managed',
                    isolation_mode='external_database',
                    status='ready',
                    pool_key=NULL,
                    physical_medium=NULL,
                    database_ref=:database_ref,
                    role_ref=:role_ref,
                    actual_size_bytes=0,
                    size_measured_at=NULL,
                    capabilities=CAST(:capabilities AS jsonb),
                    revision=revision+1,
                    config=(config - 'validation_error') || CAST(:config AS jsonb)
                WHERE id=:binding_id
                RETURNING *
                """
            ),
            {
                "provider_key": EXTERNAL_POSTGRESQL_PROVIDER_KEY,
                "database_ref": observed["database"],
                "role_ref": observed["role"],
                "capabilities": json.dumps(EXTERNAL_CAPABILITIES),
                "config": json.dumps(
                    {
                        "portable_data_api": True,
                        "native_dsn_exposed": False,
                        "credential_kind": _EXTERNAL_CREDENTIAL_KIND,
                        "tls_mode": observed["tls_mode"],
                        "server_version_num": observed["server_version_num"],
                        "external_storage_responsibility": "customer",
                        "last_validated": True,
                    }
                ),
                "binding_id": binding["id"],
            },
        )
        .mappings()
        .one()
    )


def _ensure_managed_database_capabilities(
    *,
    settings: Settings,
    database_ref: str,
) -> dict[str, object]:
    """Install privileged per-database capabilities through the provider role."""

    try:
        with psycopg.connect(
            _dsn(settings, database=database_ref),
            row_factory=dict_row,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            available = connection.execute(
                "SELECT default_version, installed_version "
                "FROM pg_available_extensions WHERE name='vector'"
            ).fetchone()
            if available is None:
                raise HostedDatabaseUnavailable(
                    "Required PostgreSQL extension vector is not installed on the provider"
                )
            connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
            observed = connection.execute(
                """
                SELECT current_setting('server_version_num')::integer AS server_version_num,
                       ext.extversion AS vector_version
                FROM pg_extension AS ext
                WHERE ext.extname='vector'
                """
            ).fetchone()
            if observed is None:
                raise HostedDatabaseUnavailable(
                    "Required PostgreSQL extension vector could not be enabled"
                )
        return {
            "server_version_num": int(observed["server_version_num"]),
            "vector_extension": True,
            "vector_version": str(observed["vector_version"]),
            "observed_at": datetime.now(UTC).isoformat(),
        }
    except HostedDatabaseUnavailable:
        raise
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"PostgreSQL capability reconciliation failed: {type(exc).__name__}"
        ) from exc


def _ensure_physical_database(
    *,
    settings: Settings,
    tenant_id: object,
    workspace_id: object,
    database_ref: str,
    role_ref: str,
    password: str,
) -> dict[str, object]:
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

        capability_evidence = _ensure_managed_database_capabilities(
            settings=settings,
            database_ref=database_ref,
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
        return capability_evidence
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


def _external_connection(
    session: Session, binding: dict[str, object], settings: Settings
) -> psycopg.Connection[dict[str, Any]]:
    database_url = _credential_secret(
        session,
        binding,
        settings,
        create=False,
        expected_kind=_EXTERNAL_CREDENTIAL_KIND,
    )
    normalized, _ = _external_url(database_url, settings)
    try:
        return psycopg.connect(
            normalized,
            row_factory=dict_row,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
            application_name="warehouse-workspace-data-api",
        )
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"External PostgreSQL database is unavailable: {type(exc).__name__}"
        ) from exc


def binding_connection(
    session: Session,
    binding: dict[str, object],
    settings: Settings | None = None,
) -> psycopg.Connection[dict[str, Any]]:
    """Resolve a PostgreSQL connection without exposing provider credentials."""

    effective = settings or get_settings()
    provider = str(binding.get("provider_key") or "")
    if provider == HDD_DATABASE_PROVIDER_KEY:
        return _binding_connection(session, binding, effective)
    if provider == EXTERNAL_POSTGRESQL_PROVIDER_KEY:
        return _external_connection(session, binding, effective)
    raise HostedDatabaseUnavailable("Workspace database provider has no PostgreSQL connection")


def reconcile_capabilities(
    session: Session,
    binding: dict[str, object],
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Observe database facts and reconcile provider-owned capabilities."""

    effective = settings or get_settings()
    provider = str(binding.get("provider_key") or "")
    if provider == HDD_DATABASE_PROVIDER_KEY:
        database_ref = str(binding.get("database_ref") or "")
        if not database_ref:
            raise HostedDatabaseUnavailable("Workspace database binding is incomplete")
        evidence = _ensure_managed_database_capabilities(
            settings=effective,
            database_ref=database_ref,
        )
        capabilities = {**MANAGED_CAPABILITIES, "vector_extension": True}
    elif provider == EXTERNAL_POSTGRESQL_PROVIDER_KEY:
        with binding_connection(session, binding, effective) as connection:
            observed = connection.execute(
                "SELECT current_setting('server_version_num')::integer AS server_version_num, "
                "(SELECT extversion FROM pg_extension WHERE extname='vector') AS vector_version"
            ).fetchone()
        evidence = {
            "server_version_num": int(observed["server_version_num"]),
            "vector_extension": bool(observed["vector_version"]),
            "vector_version": observed["vector_version"],
            "observed_at": datetime.now(UTC).isoformat(),
        }
        capabilities = {
            **EXTERNAL_CAPABILITIES,
            "vector_extension": bool(observed["vector_version"]),
        }
    else:
        raise HostedDatabaseUnavailable("Workspace database provider is unsupported")
    session.execute(
        text(
            """
            UPDATE digital_asset.database_bindings
            SET capabilities=CAST(:capabilities AS jsonb),
                config=config || jsonb_build_object(
                  'capabilities_observed',CAST(:evidence AS jsonb)
                ),
                revision=revision+1
            WHERE id=:binding_id
            """
        ),
        {
            "binding_id": binding["id"],
            "capabilities": json.dumps(capabilities),
            "evidence": json.dumps(evidence),
        },
    )
    binding["capabilities"] = capabilities
    return evidence


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
                  AND provider_key IN (:managed_provider,:external_provider)
                ORDER BY is_default DESC, created_at LIMIT 1
                """
            ),
            {
                "workspace_id": UUID(str(workspace_id)),
                "managed_provider": HDD_DATABASE_PROVIDER_KEY,
                "external_provider": EXTERNAL_POSTGRESQL_PROVIDER_KEY,
            },
        )
        .mappings()
        .one_or_none()
    )
    if binding is None:
        return None
    if str(binding.get("status") or "") != "ready":
        raise HostedDatabaseUnavailable(
            f"Default workspace database is {binding.get('status') or 'unavailable'}"
        )
    provider = str(binding.get("provider_key") or "")
    if provider == EXTERNAL_POSTGRESQL_PROVIDER_KEY:
        database_url = _credential_secret(
            session,
            dict(binding),
            effective,
            create=False,
            expected_kind=_EXTERNAL_CREDENTIAL_KIND,
        )
        normalized, _ = _external_url(database_url, effective)
        return normalized
    database_ref = str(binding.get("database_ref") or "")
    role_ref = str(binding.get("role_ref") or "")
    if not database_ref or not role_ref:
        raise HostedDatabaseUnavailable("Workspace database binding is incomplete")
    password = _credential_secret(session, dict(binding), effective, create=False)
    return _dsn(effective, database=database_ref, username=role_ref, password=password)


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
    if "create extension" in normalized:
        without_vector = _VECTOR_EXTENSION_SQL.sub("", source)
        if re.search(r"\bcreate\s+extension\b", without_vector, re.IGNORECASE):
            raise ValueError("Only the platform-managed vector extension may be requested")
    with binding_connection(session, binding, effective) as connection:
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
    if str(binding.get("provider_key")) == HDD_DATABASE_PROVIDER_KEY:
        session.execute(
            text(
                """
                UPDATE digital_asset.database_bindings
                SET actual_size_bytes=:size,size_measured_at=now()
                WHERE id=:binding_id
                """
            ),
            {"size": database_bytes, "binding_id": binding["id"]},
        )
        update_usage(session, binding, database_bytes=database_bytes)
    return {
        "transactional": True,
        "statement_count": 1,
        "database_bytes": database_bytes,
    }


def _credential_secret_from_binding(binding: dict[str, object], settings: Settings) -> str:
    if str(binding.get("credential_kind") or _MANAGED_CREDENTIAL_KIND) != (
        _MANAGED_CREDENTIAL_KIND
    ):
        raise HostedDatabaseUnavailable("Platform backup requires a managed database credential")
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
        "PGAPPNAME": "warehouse-workspace-backup",
    }


def _admin_pg_environment(settings: Settings, *, database: str) -> dict[str, str]:
    url = make_url(_dsn(settings, database=database))
    return {
        **os.environ,
        "PGHOST": str(url.host or "127.0.0.1"),
        "PGPORT": str(url.port or 5432),
        "PGDATABASE": str(url.database or ""),
        "PGUSER": str(url.username or ""),
        "PGPASSWORD": str(url.password or ""),
        "PGCONNECT_TIMEOUT": str(settings.hosted_database_connect_timeout_seconds),
        "PGAPPNAME": "warehouse-workspace-restore-verifier",
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _server_version(binding: dict[str, object], settings: Settings) -> tuple[int, str]:
    environment = _pg_environment(binding, settings)
    try:
        with psycopg.connect(
            host=environment["PGHOST"],
            port=int(environment["PGPORT"]),
            dbname=environment["PGDATABASE"],
            user=environment["PGUSER"],
            password=environment["PGPASSWORD"],
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            version_num, version = connection.execute(
                "SELECT current_setting('server_version_num')::integer, version()"
            ).fetchone()
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"PostgreSQL server version inspection failed: {type(exc).__name__}"
        ) from exc
    return int(version_num) // 10_000, str(version)


def _postgresql_tool(
    name: str,
    *,
    server_major: int,
) -> tuple[str, str]:
    configured_root = os.environ.get("WAREHOUSE_POSTGRESQL_CLIENT_BIN", "").strip()
    candidates = []
    if configured_root:
        candidates.append(str(Path(configured_root) / name))
    candidates.append(f"/usr/lib/postgresql/{_POSTGRESQL_CLIENT_MAJOR}/bin/{name}")
    discovered = shutil.which(name)
    if discovered:
        candidates.append(discovered)
    executable = next((candidate for candidate in candidates if Path(candidate).is_file()), None)
    if executable is None:
        raise HostedDatabaseUnavailable(f"PostgreSQL {name} client is unavailable")
    completed = subprocess.run(
        [executable, "--version"],
        check=False,
        capture_output=True,
        timeout=15,
    )
    output = completed.stdout.decode("utf-8", errors="replace").strip()
    matched = re.search(r"\(PostgreSQL\)\s+(\d+)(?:\.\d+)?", output)
    if completed.returncode != 0 or matched is None:
        raise HostedDatabaseUnavailable(f"PostgreSQL {name} version is unreadable")
    client_major = int(matched.group(1))
    if client_major != server_major:
        raise HostedDatabaseUnavailable(
            f"PostgreSQL {name} major {client_major} is incompatible with server major "
            f"{server_major}"
        )
    return executable, output


def _drop_verification_database(settings: Settings, database_ref: str) -> None:
    with psycopg.connect(
        _dsn(settings),
        autocommit=True,
        connect_timeout=settings.hosted_database_connect_timeout_seconds,
    ) as connection:
        connection.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname=%s AND pid<>pg_backend_pid()",
            (database_ref,),
        )
        connection.execute(
            sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(database_ref))
        )


def _verify_backup_restore(
    binding: dict[str, object],
    source: Path,
    *,
    pg_restore: str,
    settings: Settings,
) -> dict[str, object]:
    verification_database = (
        "whverify_"
        + UUID(str(binding["workspace_id"])).hex[:12]
        + "_"
        + secrets.token_hex(4)
    )
    dropped = False
    try:
        with psycopg.connect(
            _dsn(settings),
            autocommit=True,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            connection.execute(
                sql.SQL("CREATE DATABASE {} TEMPLATE template0 ENCODING 'UTF8'").format(
                    sql.Identifier(verification_database)
                )
            )
        _ensure_managed_database_capabilities(
            settings=settings,
            database_ref=verification_database,
        )
        completed = subprocess.run(
            [
                pg_restore,
                "--no-owner",
                "--no-acl",
                "--single-transaction",
                "--exit-on-error",
                "--dbname",
                verification_database,
                str(source),
            ],
            check=False,
            capture_output=True,
            env=_admin_pg_environment(settings, database=verification_database),
            timeout=900,
        )
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", errors="replace")[-1000:].strip()
            raise HostedDatabaseUnavailable(
                "PostgreSQL backup restore verification failed"
                + (f": {detail}" if detail else "")
            )
        with psycopg.connect(
            _dsn(settings, database=verification_database),
            row_factory=dict_row,
            connect_timeout=settings.hosted_database_connect_timeout_seconds,
        ) as connection:
            observed = connection.execute(
                """
                SELECT count(*)::integer AS relation_count,
                       to_regclass('app.workspace_meta') IS NOT NULL AS workspace_meta_present,
                       (SELECT extversion FROM pg_extension WHERE extname='vector')
                         AS vector_version
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid=c.relnamespace
                WHERE n.nspname NOT IN ('pg_catalog','information_schema')
                  AND n.nspname !~ '^pg_toast'
                  AND c.relkind IN ('r','p','m','v','S')
                """
            ).fetchone()
        if observed is None or int(observed["relation_count"]) < 1:
            raise HostedDatabaseUnavailable(
                "PostgreSQL backup restore verification produced no application relations"
            )
        evidence = {
            "verified": True,
            "method": "ephemeral_database_restore",
            "relation_count": int(observed["relation_count"]),
            "workspace_meta_present": bool(observed["workspace_meta_present"]),
            "vector_version": observed["vector_version"],
            "verified_at": datetime.now(UTC).isoformat(),
        }
        _drop_verification_database(settings, verification_database)
        dropped = True
        evidence["verification_database_disposition"] = "dropped"
        return evidence
    finally:
        if not dropped:
            try:
                _drop_verification_database(settings, verification_database)
            except Exception:
                pass


def backup_database(
    binding: dict[str, object],
    target: Path,
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    """Create one verified custom-format logical backup without exposing DSNs."""

    effective = settings or get_settings()
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
    server_major, server_version = _server_version(binding, effective)
    pg_dump, pg_dump_version = _postgresql_tool("pg_dump", server_major=server_major)
    pg_restore, pg_restore_version = _postgresql_tool(
        "pg_restore", server_major=server_major
    )
    completed = subprocess.run(
        [
            pg_dump,
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
    listed = subprocess.run(
        [pg_restore, "--list", str(target)],
        check=False,
        capture_output=True,
        timeout=120,
    )
    if listed.returncode != 0:
        target.unlink(missing_ok=True)
        raise HostedDatabaseUnavailable("PostgreSQL backup archive validation failed")
    digest = _sha256_file(target)
    restore_verification = _verify_backup_restore(
        binding,
        target,
        pg_restore=pg_restore,
        settings=effective,
    )
    return {
        "sha256": digest,
        "size_bytes": target.stat().st_size,
        "format": "pg_custom",
        "server_major": server_major,
        "server_version": server_version,
        "pg_dump_version": pg_dump_version,
        "pg_restore_version": pg_restore_version,
        "restore_verification": restore_verification,
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
    actual = _sha256_file(source)
    if not secrets.compare_digest(actual, expected_sha256):
        raise HostedDatabaseUnavailable("Backup digest verification failed")
    server_major, _server_version_text = _server_version(binding, effective)
    pg_restore, pg_restore_version = _postgresql_tool(
        "pg_restore", server_major=server_major
    )
    if str(binding.get("provider_key")) == HDD_DATABASE_PROVIDER_KEY:
        _ensure_managed_database_capabilities(
            settings=effective,
            database_ref=str(binding["database_ref"]),
        )
    completed = subprocess.run(
        [
            pg_restore,
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
    return {
        "restored": True,
        "sha256": actual,
        "format": "pg_custom",
        "server_major": server_major,
        "pg_restore_version": pg_restore_version,
    }


def _measure(connection: psycopg.Connection[Any]) -> int:
    row = connection.execute(
        """
        SELECT COALESCE(sum(pg_total_relation_size(c.oid)), 0)::bigint AS bytes
        FROM pg_class AS c
        JOIN pg_namespace AS n ON n.oid = c.relnamespace
        WHERE n.nspname <> 'information_schema'
          AND n.nspname !~ '^pg_'
          AND c.relkind IN ('r','p','m')
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
    capability_evidence = _ensure_physical_database(
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
                    ownership_mode = 'platform_managed',
                    isolation_mode = 'dedicated_database',
                    status = 'ready',
                    pool_key = :pool_key,
                    physical_medium = 'hdd',
                    database_ref = :database_ref,
                    role_ref = :role_ref,
                    actual_size_bytes = :actual_size_bytes,
                    size_measured_at = now(),
                    capabilities = CAST(:capabilities AS jsonb),
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
                "capabilities": json.dumps(MANAGED_CAPABILITIES),
                "config": json.dumps(
                    {
                        "portable_data_api": True,
                        "native_dsn_exposed": False,
                        "migration_state": "hdd_verified",
                        "migrated_records": len(source_rows),
                        "migrated_at": datetime.now(UTC).isoformat(),
                        "billable_size_source": "pg_total_relation_size",
                        "capabilities_observed": capability_evidence,
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
    owner_id: str | None = None,
) -> tuple[list[dict[str, object]], int]:
    with _binding_connection(session, binding, get_settings()) as connection:
        rows = connection.execute(
            """
            SELECT record_key, payload, version, created_at, updated_at
            FROM app.workspace_records
            WHERE collection_name = %s
              AND (%s::text IS NULL OR payload->>'owner_id' = %s::text)
            ORDER BY updated_at DESC, record_key
            LIMIT %s OFFSET %s
            """,
            (collection, owner_id, owner_id, limit, offset),
        ).fetchall()
        size = _measure(connection)
    return [dict(row) for row in rows], size


def get_record(
    session: Session,
    binding: dict[str, object],
    *,
    collection: str,
    record_key: str,
    owner_id: str | None = None,
) -> dict[str, object] | None:
    with _binding_connection(session, binding, get_settings()) as connection:
        row = connection.execute(
            """
            SELECT record_key, payload, version, created_at, updated_at
            FROM app.workspace_records
            WHERE collection_name = %s AND record_key = %s
              AND (%s::text IS NULL OR payload->>'owner_id' = %s::text)
            """,
            (collection, record_key, owner_id, owner_id),
        ).fetchone()
    return dict(row) if row is not None else None


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
    owner_id: str | None = None,
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
                SELECT version, payload FROM app.workspace_records
                WHERE collection_name = %s AND record_key = %s
                FOR UPDATE
                """,
                (collection, record_key),
            ).fetchone()
            current_version = int(current["version"]) if current is not None else 0
            if (
                owner_id is not None
                and current is not None
                and str(current["payload"].get("owner_id") or "") != owner_id
            ):
                raise PermissionError("Record belongs to another browser principal")
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


def delete_record(
    session: Session,
    binding: dict[str, object],
    *,
    collection: str,
    record_key: str,
    owner_id: str | None = None,
) -> HostedWriteResult | None:
    with _binding_connection(session, binding, get_settings()) as connection:
        current = connection.execute(
            """
            SELECT record_key, payload, version, created_at, updated_at
            FROM app.workspace_records
            WHERE collection_name = %s AND record_key = %s
            FOR UPDATE
            """,
            (collection, record_key),
        ).fetchone()
        if current is None:
            return None
        if owner_id is not None and str(current["payload"].get("owner_id") or "") != owner_id:
            raise PermissionError("Record belongs to another browser principal")
        connection.execute(
            """
            DELETE FROM app.workspace_records
            WHERE collection_name = %s AND record_key = %s
            """,
            (collection, record_key),
        )
        return HostedWriteResult(record=dict(current), database_bytes=_measure(connection))


_RELATION_SQL = """
    SELECT n.nspname AS schema_name,
           c.relname AS table_name,
           c.reltuples::bigint AS estimated_rows,
           has_table_privilege(c.oid,'SELECT') AS can_select,
           has_table_privilege(c.oid,'INSERT') AS can_insert,
           has_table_privilege(c.oid,'UPDATE') AS can_update,
           has_table_privilege(c.oid,'DELETE') AS can_delete,
           a.attname AS column_name,
           a.attnum AS ordinal_position,
           format_type(a.atttypid,a.atttypmod) AS data_type,
           a.attnotnull AS not_null,
           a.attidentity <> '' AS identity,
           a.attgenerated <> '' AS generated,
           pg_get_expr(ad.adbin,ad.adrelid) AS default_expression,
           EXISTS (
             SELECT 1 FROM pg_index AS index
             WHERE index.indrelid=c.oid AND index.indisprimary
               AND a.attnum=ANY(index.indkey)
           ) AS primary_key
    FROM pg_class AS c
    JOIN pg_namespace AS n ON n.oid=c.relnamespace
    JOIN pg_attribute AS a ON a.attrelid=c.oid
    LEFT JOIN pg_attrdef AS ad ON ad.adrelid=c.oid AND ad.adnum=a.attnum
    WHERE c.relkind IN ('r','p')
      AND a.attnum > 0 AND NOT a.attisdropped
      AND n.nspname <> 'information_schema'
      AND n.nspname !~ '^pg_'
      AND has_schema_privilege(n.oid,'USAGE')
      AND has_table_privilege(c.oid,'SELECT')
"""


def _relation_descriptors(
    connection: psycopg.Connection[dict[str, Any]],
    *,
    schema_name: str | None = None,
    table_name: str | None = None,
) -> list[dict[str, object]]:
    conditions: list[str] = []
    parameters: list[object] = []
    if schema_name is not None:
        conditions.append("n.nspname=%s")
        parameters.append(schema_name)
    if table_name is not None:
        conditions.append("c.relname=%s")
        parameters.append(table_name)
    source = _RELATION_SQL
    if conditions:
        source += " AND " + " AND ".join(conditions)
    source += " ORDER BY n.nspname,c.relname,a.attnum"
    rows = connection.execute(source, tuple(parameters)).fetchall()
    relations: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        schema = str(row["schema_name"])
        table = str(row["table_name"])
        if schema == "app" and table in {"workspace_meta", "workspace_records"}:
            continue
        key = (schema, table)
        relation = relations.setdefault(
            key,
            {
                "schema": schema,
                "name": table,
                "qualified_name": f"{schema}.{table}",
                "estimated_rows": max(0, int(row["estimated_rows"] or 0)),
                "primary_key": [],
                "columns": [],
                "capabilities": {
                    "read": bool(row["can_select"]),
                    "insert": bool(row["can_insert"]),
                    "update": bool(row["can_update"]),
                    "delete": bool(row["can_delete"]),
                },
            },
        )
        column = {
            "name": str(row["column_name"]),
            "data_type": str(row["data_type"]),
            "nullable": not bool(row["not_null"]),
            "identity": bool(row["identity"]),
            "generated": bool(row["generated"]),
            "has_default": row["default_expression"] is not None,
            "primary_key": bool(row["primary_key"]),
        }
        relation["columns"].append(column)
        if column["primary_key"]:
            relation["primary_key"].append(column["name"])
    return list(relations.values())


def relational_schema(
    session: Session,
    binding: dict[str, object],
) -> list[dict[str, object]]:
    with binding_connection(session, binding) as connection:
        return _relation_descriptors(connection)


def _relation_descriptor(
    connection: psycopg.Connection[dict[str, Any]],
    *,
    schema_name: str,
    table_name: str,
) -> dict[str, object]:
    relations = _relation_descriptors(
        connection,
        schema_name=schema_name,
        table_name=table_name,
    )
    if not relations:
        raise LookupError("Readable database table was not found")
    return relations[0]


def list_relation_rows(
    session: Session,
    binding: dict[str, object],
    *,
    schema_name: str,
    table_name: str,
    limit: int,
    offset: int,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    with binding_connection(session, binding) as connection:
        descriptor = _relation_descriptor(
            connection,
            schema_name=schema_name,
            table_name=table_name,
        )
        primary_key = [str(value) for value in descriptor["primary_key"]]
        order = (
            sql.SQL(",").join(sql.Identifier(column) for column in primary_key)
            if primary_key
            else sql.SQL("ctid")
        )
        rows = connection.execute(
            sql.SQL(
                "SELECT to_jsonb(target) AS data,target.xmin::text AS version "
                "FROM {}.{} AS target ORDER BY {} LIMIT %s OFFSET %s"
            ).format(
                sql.Identifier(schema_name),
                sql.Identifier(table_name),
                order,
            ),
            (limit, offset),
        ).fetchall()
    output: list[dict[str, object]] = []
    for row in rows:
        data = dict(row["data"] or {})
        if len(primary_key) == 1:
            key: object = str(data.get(primary_key[0]))
        elif primary_key:
            key = {column: data.get(column) for column in primary_key}
        else:
            key = None
        output.append({"key": key, "data": data, "version": str(row["version"])})
    return descriptor, output


def _adapt_relation_value(value: object, data_type: str) -> object:
    if data_type in {"json", "jsonb"}:
        return Jsonb(value)
    return value


def put_relation_row(
    session: Session,
    binding: dict[str, object],
    *,
    schema_name: str,
    table_name: str,
    record_key: str,
    payload: dict[str, object],
    expected_version: str | None,
    quota_bytes: int | None = None,
    non_database_bytes: int = 0,
) -> HostedWriteResult:
    settings = get_settings()
    with binding_connection(session, binding, settings) as connection:
        try:
            descriptor = _relation_descriptor(
                connection,
                schema_name=schema_name,
                table_name=table_name,
            )
            capabilities = dict(descriptor["capabilities"])
            primary_key = [str(value) for value in descriptor["primary_key"]]
            if len(primary_key) != 1:
                raise ValueError("Relational writes require exactly one primary-key column")
            pk = primary_key[0]
            columns = {str(item["name"]): dict(item) for item in descriptor["columns"]}
            unknown = sorted(set(payload) - set(columns))
            if unknown:
                raise ValueError(f"Unknown table columns: {', '.join(unknown)}")
            if pk in payload and str(payload[pk]) != record_key:
                raise ValueError("Payload primary key does not match the row key")
            mutable = {
                name: value
                for name, value in payload.items()
                if name != pk
                and not bool(columns[name]["identity"])
                and not bool(columns[name]["generated"])
            }
            current = connection.execute(
                sql.SQL(
                    "SELECT target.xmin::text AS version FROM {}.{} AS target "
                    "WHERE target.{}::text=%s FOR UPDATE"
                ).format(
                    sql.Identifier(schema_name),
                    sql.Identifier(table_name),
                    sql.Identifier(pk),
                ),
                (record_key,),
            ).fetchone()
            current_version = str(current["version"]) if current is not None else "0"
            if expected_version is not None and str(expected_version) != current_version:
                raise ValueError(
                    json.dumps(
                        {
                            "reason": "version_conflict",
                            "expected": str(expected_version),
                            "current": current_version,
                        }
                    )
                )
            if current is None:
                if not bool(capabilities.get("insert")):
                    raise PermissionError("Database role cannot insert this table")
                insert_columns = [pk, *mutable]
                insert_values = [
                    payload.get(pk, record_key),
                    *[
                        _adapt_relation_value(value, str(columns[name]["data_type"]))
                        for name, value in mutable.items()
                    ],
                ]
                placeholders = sql.SQL(",").join(sql.Placeholder() for _ in insert_columns)
                row = connection.execute(
                    sql.SQL(
                        "INSERT INTO {}.{} AS target ({}) VALUES ({}) "
                        "RETURNING to_jsonb(target) AS data,target.xmin::text AS version"
                    ).format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name),
                        sql.SQL(",").join(sql.Identifier(name) for name in insert_columns),
                        placeholders,
                    ),
                    tuple(insert_values),
                ).fetchone()
            elif mutable:
                if not bool(capabilities.get("update")):
                    raise PermissionError("Database role cannot update this table")
                assignments = sql.SQL(",").join(
                    sql.SQL("{}={}").format(sql.Identifier(name), sql.Placeholder())
                    for name in mutable
                )
                values = [
                    _adapt_relation_value(value, str(columns[name]["data_type"]))
                    for name, value in mutable.items()
                ]
                row = connection.execute(
                    sql.SQL(
                        "UPDATE {}.{} AS target SET {} WHERE target.{}::text=%s "
                        "RETURNING to_jsonb(target) AS data,target.xmin::text AS version"
                    ).format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name),
                        assignments,
                        sql.Identifier(pk),
                    ),
                    (*values, record_key),
                ).fetchone()
            else:
                row = connection.execute(
                    sql.SQL(
                        "SELECT to_jsonb(target) AS data,target.xmin::text AS version "
                        "FROM {}.{} AS target WHERE target.{}::text=%s"
                    ).format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name),
                        sql.Identifier(pk),
                    ),
                    (record_key,),
                ).fetchone()
            if row is None:
                raise HostedDatabaseUnavailable("Relational row mutation returned no row")
            database_bytes = (
                _measure(connection)
                if str(binding.get("provider_key")) == HDD_DATABASE_PROVIDER_KEY
                else 0
            )
            if quota_bytes is not None:
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
    data = dict(row["data"] or {})
    return HostedWriteResult(
        record={"key": str(data.get(pk)), "data": data, "version": str(row["version"])},
        database_bytes=database_bytes,
    )


def binding_health(
    session: Session,
    binding: dict[str, object],
    *,
    settings: Settings | None = None,
) -> dict[str, object]:
    effective = settings or get_settings()
    provider = str(binding.get("provider_key") or "")
    try:
        with binding_connection(session, binding, effective) as connection:
            observed = connection.execute(
                """
                SELECT current_database() AS database_name,
                       current_user AS role_name,
                       current_setting('server_version_num')::integer AS server_version_num,
                       pg_is_in_recovery() AS in_recovery
                """
            ).fetchone()
    except HostedDatabaseUnavailable:
        raise
    except Exception as exc:
        raise HostedDatabaseUnavailable(
            f"Workspace PostgreSQL health check failed: {type(exc).__name__}"
        ) from exc
    if provider == EXTERNAL_POSTGRESQL_PROVIDER_KEY:
        session.execute(
            text(
                """
                UPDATE digital_asset.database_credentials
                SET last_validated_at=now()
                WHERE database_binding_id=:binding_id
                """
            ),
            {"binding_id": binding["id"]},
        )
    return {
        "reachable": True,
        "provider_key": provider,
        "ownership_mode": binding.get("ownership_mode"),
        "database": str(observed["database_name"]),
        "role": str(observed["role_name"]),
        "server_version_num": int(observed["server_version_num"]),
        "in_recovery": bool(observed["in_recovery"]),
        "credentials_exposed": False,
    }
