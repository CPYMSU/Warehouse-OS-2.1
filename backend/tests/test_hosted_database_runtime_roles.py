from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest
from pydantic import SecretStr
from sqlalchemy.engine import make_url

from app.core.config import Settings
from app.services import hosted_database

pytestmark = pytest.mark.integration


def test_runtime_reconciliation_skips_workspace_managed_schemas() -> None:
    admin_source = (
        os.environ.get("WAREHOUSE_TEST_HOSTED_DATABASE_ADMIN_URL")
        or os.environ.get("WAREHOUSE_HOSTED_DATABASE_ADMIN_URL")
        or os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    )
    admin_url = make_url(admin_source).set(drivername="postgresql", database="postgres")
    suffix = uuid4().hex[:12]
    database_ref = f"warehouse_scope_{suffix}"
    owner_role_ref = f"who_{suffix}"
    runtime_role_ref = f"wha_{suffix}"
    workspace_role_ref = f"whm_{suffix}"
    workspace_schema = f"workspace_{suffix}"
    owner_password = f"owner-{suffix}"
    runtime_password = f"runtime-{suffix}"
    settings = Settings(
        hosted_database_admin_url=SecretStr(
            admin_url.render_as_string(hide_password=False)
        )
    )

    try:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                psycopg.sql.SQL(
                    "CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
                ).format(
                    psycopg.sql.Identifier(owner_role_ref),
                    psycopg.sql.Literal(owner_password),
                )
            )
            connection.execute(
                psycopg.sql.SQL("CREATE ROLE {} NOLOGIN").format(
                    psycopg.sql.Identifier(workspace_role_ref)
                )
            )
            connection.execute(
                psycopg.sql.SQL("CREATE DATABASE {} OWNER {}").format(
                    psycopg.sql.Identifier(database_ref),
                    psycopg.sql.Identifier(owner_role_ref),
                )
            )

        owner_url = admin_url.set(
            database=database_ref,
            username=owner_role_ref,
            password=owner_password,
            query={"sslmode": "disable"},
        )
        with psycopg.connect(owner_url.render_as_string(hide_password=False)) as connection:
            connection.execute("CREATE SCHEMA app")
            connection.execute("CREATE TABLE app.provider_records(id integer PRIMARY KEY)")
        workspace_database_url = admin_url.set(database=database_ref)
        with psycopg.connect(
            workspace_database_url.render_as_string(hide_password=False)
        ) as connection:
            connection.execute(
                psycopg.sql.SQL("CREATE SCHEMA {} AUTHORIZATION {}").format(
                    psycopg.sql.Identifier(workspace_schema),
                    psycopg.sql.Identifier(workspace_role_ref),
                )
            )
            connection.execute(
                psycopg.sql.SQL("CREATE TABLE {}.governed_records(id integer)").format(
                    psycopg.sql.Identifier(workspace_schema)
                )
            )
            connection.execute(
                psycopg.sql.SQL("ALTER TABLE {}.governed_records OWNER TO {}").format(
                    psycopg.sql.Identifier(workspace_schema),
                    psycopg.sql.Identifier(workspace_role_ref),
                )
            )

        with psycopg.connect(
            owner_url.render_as_string(hide_password=False),
            row_factory=psycopg.rows.dict_row,
        ) as connection:
            observed_schemas = connection.execute(
                """
                SELECT nspname::text AS nspname,
                       pg_get_userbyid(nspowner)::text AS owner_name
                FROM pg_namespace
                WHERE nspname <> 'information_schema' AND nspname !~ '^pg_'
                ORDER BY nspname
                """
            ).fetchall()
        assert [(row["nspname"], row["owner_name"]) for row in observed_schemas] == [
            ("app", owner_role_ref),
            ("public", "pg_database_owner"),
            (workspace_schema, workspace_role_ref),
        ]

        evidence = hosted_database._ensure_managed_runtime_role(  # noqa: SLF001
            settings=settings,
            database_ref=database_ref,
            owner_role_ref=owner_role_ref,
            owner_password=owner_password,
            runtime_role_ref=runtime_role_ref,
            runtime_password=runtime_password,
        )

        assert evidence["schema_scope"] == "provider_owned_only"
        assert evidence["observed_schema_count"] == 3
        assert evidence["schema_count"] == 2
        assert evidence["workspace_managed_schema_count"] == 1
        with psycopg.connect(
            workspace_database_url.render_as_string(hide_password=False)
        ) as connection:
            privileges = connection.execute(
                """
                SELECT has_schema_privilege(%s, 'app', 'USAGE') AS app_usage,
                       has_table_privilege(%s, 'app.provider_records', 'SELECT')
                         AS app_select,
                       has_schema_privilege(%s, %s, 'USAGE') AS workspace_usage,
                       has_table_privilege(%s, %s, 'SELECT') AS workspace_select
                """,
                (
                    runtime_role_ref,
                    runtime_role_ref,
                    runtime_role_ref,
                    workspace_schema,
                    runtime_role_ref,
                    f"{workspace_schema}.governed_records",
                ),
            ).fetchone()
        assert privileges == (True, True, False, False)
    finally:
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
                    psycopg.sql.Identifier(runtime_role_ref)
                )
            )
            connection.execute(
                psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                    psycopg.sql.Identifier(workspace_role_ref)
                )
            )
            connection.execute(
                psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                    psycopg.sql.Identifier(owner_role_ref)
                )
            )
