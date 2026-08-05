from __future__ import annotations

import os
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.api.deps import ActorContext
from app.core.config import Settings, get_settings
from app.core.security import hash_password
from app.db.session import system_session, tenant_session
from app.main import app
from app.services import digital_asset_hosting, hosted_database
from app.services.templates import provision_tenant_template

pytestmark = pytest.mark.integration


def _actor() -> ActorContext:
    tenant_id = uuid4()
    user_id = uuid4()
    slug = f"fabric-{tenant_id.hex[:10]}"
    username = f"fabric-{user_id.hex[:10]}"
    with system_session() as session:
        session.execute(
            text(
                "INSERT INTO iam.tenants(id,slug,name,industry_template_key) "
                "VALUES (:id,:slug,'Hosting Fabric Test','generic_warehouse')"
            ),
            {"id": tenant_id, "slug": slug},
        )
        session.execute(
            text(
                "INSERT INTO iam.users(id,username,display_name,password_hash) "
                "VALUES (:id,:username,'Fabric Owner',:password_hash)"
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
            tenant_name="Hosting Fabric Test",
            template_key="generic_warehouse",
        )
        session.execute(
            text(
                "INSERT INTO iam.memberships(tenant_id,user_id,position_code,role_level) "
                "VALUES (:tenant_id,:user_id,:position_code,10)"
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
        tenant_name="Hosting Fabric Test",
        industry_template_key="generic_warehouse",
        username=username,
        display_name="Fabric Owner",
        role_level=10,
        topology_level=10,
        topology_title="Owner",
        permissions=frozenset(
            {"ai.use", "assets.read", "assets.manage", "asset_mgmt.read", "asset_mgmt.manage"}
        ),
    )


def test_primary_workspace_key_controls_fabric_without_secret_disclosure(tmp_path) -> None:
    actor = _actor()
    settings = Settings(
        public_origin="https://bonfirework.org",
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        integration_secret="fabric-integration-test-secret-32",
    )
    asset = digital_asset_hosting.create_asset(
        actor, {"name": "Fabric Application", "asset_kind": "software"}
    )
    workspace = digital_asset_hosting.create_workspace(
        actor,
        asset["asset"]["uuid"],
        {
            "workspace_key": f"fabric-app-{actor.tenant_id.hex[:8]}",
            "service_plan": "custody",
            "runtime_type": "compose",
        },
    )
    issued = digital_asset_hosting.issue_workspace_key(
        actor,
        workspace["workspace"]["uuid"],
        {"label": "Primary fabric key", "expires_days": 1},
        signing_secret=settings.integration_secret,
        key_kind="primary",
    )
    assert set(issued["scopes"]) == set(digital_asset_hosting.WORKSPACE_ALL_SCOPES)
    headers = {"Authorization": f"Bearer {issued['api_key']}"}
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        manifest = client.get("/api/workspaces/v1/fabric/manifest", headers=headers)
        assert manifest.status_code == 200
        assert {item["resource_kind"] for item in manifest.json()["manifest"]["drivers"]} == {
            "container",
            "compose",
            "domain",
            "environment",
            "secret",
            "scaling",
            "database_migration",
            "repository",
            "backup",
            "accelerator",
        }

        database_policy = client.put(
            "/api/workspaces/v1/database/policy",
            headers=headers,
            json={"mode": "workspace_managed"},
        )
        assert database_policy.status_code == 200, database_policy.text
        assert database_policy.json()["policy"]["mode"] == "workspace_managed"
        assert database_policy.json()["release_gate"]["ready"] is True
        assert database_policy.json()["release_gate"]["required"] is False
        assert database_policy.json()["existing_database_binding_retained"] is False

        custom_database_url = "mysql://workspace:private@database:3306/application"
        database_secret = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers=headers,
            json={
                "kind": "secret",
                "spec": {
                    "name": "DATABASE_URL",
                    "value": custom_database_url,
                    "component": "api",
                },
            },
        )
        assert database_secret.status_code == 200, database_secret.text
        assert database_secret.json()["action"]["status"] == "succeeded"
        assert custom_database_url not in database_secret.text

        environment_body = {
            "kind": "environment",
            "resource_key": "api-environment",
            "spec": {
                "component": "api",
                "variables": {"APP_MODE": "production"},
            },
        }
        environment = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "environment-v1"},
            json=environment_body,
        )
        assert environment.status_code == 200
        assert environment.json()["resource"]["status"] == "ready"
        replay = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "environment-v1"},
            json=environment_body,
        )
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True
        assert replay.json()["resource"]["status"] == "ready"

        plaintext = "never-return-this-value"
        secret = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "secret-v1"},
            json={
                "kind": "secret",
                "spec": {
                    "name": "MODEL_API_TOKEN",
                    "value": plaintext,
                    "component": "api",
                },
            },
        )
        assert secret.status_code == 200
        assert secret.json()["action"]["status"] == "succeeded"
        assert plaintext not in secret.text

        pitr = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "pitr-v1"},
            json={
                "kind": "backup",
                "spec": {
                    "action": "create",
                    "mode": "point_in_time",
                    "destination": "remote",
                },
            },
        )
        assert pitr.status_code == 200
        assert pitr.json()["action"]["status"] == "blocked"
        assert pitr.json()["diagnosis"]["reason"] == "pitr_provider_unavailable"

        reserved_domain = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers=headers,
            json={"kind": "domain", "spec": {"hostname": "app.bonfirework.org"}},
        )
        assert reserved_domain.status_code == 422
        assert reserved_domain.json()["detail"]["reason"] == "platform_hostname_is_reserved"

        claimed_domain = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers=headers,
            json={"kind": "domain", "spec": {"hostname": "fabric.example.com"}},
        )
        assert claimed_domain.status_code == 200
        assert claimed_domain.json()["action"]["status"] == "blocked"

        other_asset = digital_asset_hosting.create_asset(
            actor, {"name": "Other Fabric Application", "asset_kind": "software"}
        )
        other_workspace = digital_asset_hosting.create_workspace(
            actor,
            other_asset["asset"]["uuid"],
            {
                "workspace_key": f"other-fabric-{actor.tenant_id.hex[:8]}",
                "service_plan": "custody",
                "runtime_type": "container",
            },
        )
        other_key = digital_asset_hosting.issue_workspace_key(
            actor,
            other_workspace["workspace"]["uuid"],
            {"label": "Other primary fabric key", "expires_days": 1},
            signing_secret=settings.integration_secret,
            key_kind="primary",
        )
        duplicate_domain = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={"Authorization": f"Bearer {other_key['api_key']}"},
            json={"kind": "domain", "spec": {"hostname": "fabric.example.com"}},
        )
        assert duplicate_domain.status_code == 409
        assert (
            duplicate_domain.json()["detail"]["reason"] == "hostname_claimed_by_another_workspace"
        )

        world = client.get("/api/workspaces/v1/fabric", headers=headers)
        assert world.status_code == 200
        assert plaintext not in world.text
        assert world.json()["secret_plaintext_exposed"] is False
        action_id = environment.json()["action"]["id"]
        action = client.get(f"/api/workspaces/v1/fabric/actions/{action_id}", headers=headers)
        assert action.status_code == 200
        assert action.json()["events"][-1]["event_type"] == "succeeded"
    finally:
        app.dependency_overrides.clear()


def test_logical_backup_is_restore_verified_before_database_migration(
    monkeypatch, tmp_path
) -> None:
    migration_url = os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    admin_source = (
        os.environ.get("WAREHOUSE_TEST_HOSTED_DATABASE_ADMIN_URL")
        or os.environ.get("WAREHOUSE_HOSTED_DATABASE_ADMIN_URL")
        or migration_url
    )
    admin_url = make_url(admin_source).set(drivername="postgresql", database="postgres")
    settings = Settings(
        public_origin="https://bonfirework.org",
        asset_storage_root=tmp_path / "hdd",
        asset_code_ssd_root=tmp_path / "ssd",
        hosted_database_admin_url=SecretStr(
            admin_url.render_as_string(hide_password=False)
        ),
        integration_secret="fabric-database-release-test-secret-32",
    )
    monkeypatch.setattr(hosted_database, "get_settings", lambda: settings)
    monkeypatch.setattr(digital_asset_hosting, "get_settings", lambda: settings)
    actor = _actor()
    asset = digital_asset_hosting.create_asset(
        actor, {"name": "Fabric Database Release", "asset_kind": "software"}
    )
    workspace = digital_asset_hosting.create_workspace(
        actor,
        asset["asset"]["uuid"],
        {
            "workspace_key": f"fabric-db-{actor.tenant_id.hex[:8]}",
            "service_plan": "hosted",
            "runtime_type": "api",
        },
    )
    database = workspace["database"]
    backup_role_ref = database["backup_role_ref"]
    assert backup_role_ref == f"whb_{workspace['workspace']['uuid'].replace('-', '')}"
    issued = digital_asset_hosting.issue_workspace_key(
        actor,
        workspace["workspace"]["uuid"],
        {"label": "Database release key", "expires_days": 1},
        signing_secret=settings.integration_secret,
        key_kind="primary",
    )
    headers = {"Authorization": f"Bearer {issued['api_key']}"}
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        client = TestClient(app)
        control = client.get(
            "/api/workspaces/v1/database/control",
            headers=headers,
        )
        assert control.status_code == 200, control.text
        assert control.json()["health"]["reachable"] is True
        assert all(control.json()["authorized_operations"].values())
        assert control.json()["credentials_exposed"] is False

        usage_response = client.get("/api/workspaces/v1/usage", headers=headers)
        assert usage_response.status_code == 200, usage_response.text
        usage = usage_response.json()["usage"]
        assert {
            "source_archive_bytes",
            "runtime_release_bytes",
            "data_volume_bytes",
            "managed_data_object_bytes",
            "postgresql_bytes",
            "total_bytes",
            "measured_at",
            "measurement_status",
        }.issubset(usage)
        assert usage["total_bytes"] == sum(
            usage[key]
            for key in (
                "source_archive_bytes",
                "runtime_release_bytes",
                "data_volume_bytes",
                "managed_data_object_bytes",
                "postgresql_bytes",
            )
        )
        assert usage["postgresql_bytes"] > 0

        reconcile = client.post(
            "/api/workspaces/v1/database/reconcile",
            headers=headers,
        )
        assert reconcile.status_code == 200, reconcile.text
        reconcile_body = reconcile.json()
        assert reconcile_body["reconcile_performed"] is True
        assert reconcile_body["database"]["capabilities"]["vector_extension"] is True
        assert reconcile_body["database"]["runtime_role_ref"].startswith("wha_")
        assert reconcile_body["database"]["runtime_role_ref"] != database["role_ref"]
        assert reconcile_body["capability_evidence"]["vector_extension"] is True
        assert reconcile_body["capability_evidence"]["runtime_role"]["database_owner"] is False
        assert reconcile_body["capability_evidence"]["runtime_role"]["bypass_rls"] is False
        assert reconcile_body["capability_evidence"]["backup_role"]["can_login"] is False
        assert reconcile_body["capability_evidence"]["backup_role"]["bypass_rls"] is True
        assert (
            reconcile_body["capability_evidence"]["backup_role"][
                "runtime_can_assume_backup"
            ]
            is False
        )
        assert reconcile_body["health"]["reachable"] is True

        with tenant_session(actor.tenant_id) as session:
            owner_url = hosted_database.migration_database_url(
                session,
                workspace["workspace"]["uuid"],
                settings=settings,
            )
        assert owner_url is not None
        with psycopg.connect(owner_url) as connection:
            connection.execute(
                "CREATE TABLE app.force_rls_backup_probe(id integer PRIMARY KEY,payload text)"
            )
            connection.execute(
                "INSERT INTO app.force_rls_backup_probe VALUES (1,'first'),(2,'second')"
            )
            connection.execute("ALTER TABLE app.force_rls_backup_probe ENABLE ROW LEVEL SECURITY")
            connection.execute("CREATE POLICY deny_workspace_runtime ON "
                               "app.force_rls_backup_probe USING (false)")
            connection.execute("ALTER TABLE app.force_rls_backup_probe FORCE ROW LEVEL SECURITY")
        with psycopg.connect(owner_url) as connection:
            assert connection.execute(
                "SELECT count(*) FROM app.force_rls_backup_probe"
            ).fetchone()[0] == 0

        backup = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "database-backup-v1"},
            json={
                "kind": "backup",
                "spec": {"action": "create", "mode": "logical", "label": "pre-v1"},
            },
        )
        assert backup.status_code == 200, backup.text
        backup_body = backup.json()
        assert backup_body["action"]["status"] == "succeeded"
        verification = backup_body["action"]["result"]["verification"]
        assert verification["checksum_verified"] is True
        assert verification["restore_verified"] is True
        assert verification["preserves_ownership"] is True
        assert verification["backup_identity"]["can_login"] is False
        assert verification["backup_identity"]["bypass_rls"] is True
        assert verification["backup_identity"]["runtime_can_assume_backup"] is False
        assert verification["restore_verification"]["force_rls"]["verified"] is True
        assert verification["restore_verification"]["force_rls"]["table_count"] >= 1
        assert verification["restore_verification"]["force_rls"]["source_row_count"] >= 2
        assert (
            verification["restore_verification"]["force_rls"]["source_row_count"]
            == verification["restore_verification"]["force_rls"]["restored_row_count"]
        )
        assert (
            verification["restore_verification"]["verification_database_disposition"]
            == "dropped"
        )
        with tenant_session(actor.tenant_id) as session:
            backup_binding = session.execute(
                text(
                    "SELECT backup_role_ref,config->'backup_identity_observed' AS evidence "
                    "FROM digital_asset.database_bindings WHERE id=:id"
                ),
                {"id": database["id"]},
            ).mappings().one()
        assert backup_binding["backup_role_ref"] == backup_role_ref
        assert backup_binding["evidence"]["bypass_rls"] is True
        assert backup_binding["evidence"]["runtime_can_assume_backup"] is False

        migration = client.post(
            "/api/workspaces/v1/fabric/resources",
            headers={**headers, "Idempotency-Key": "database-migration-v1"},
            json={
                "kind": "database_migration",
                "spec": {
                    "version": "mk7-v1",
                    "sql": "\nCREATE TABLE app.mk7_release_gate(id integer PRIMARY KEY)\n",
                },
            },
        )
        assert migration.status_code == 200, migration.text
        migration_result = migration.json()["action"]["result"]
        assert migration_result["backup_id"] == backup_body["action"]["result"]["backup_id"]
        assert migration_result["capabilities"]["vector_extension"] is True
        assert migration_result["transactional"] is True
        assert migration.json()["resource"]["desired_state"]["checksum"] == (
            migration_result["checksum"]
        )
        with tenant_session(actor.tenant_id) as session:
            assert session.execute(
                text(
                    "SELECT status FROM digital_asset.database_migration_history "
                    "WHERE workspace_id=:workspace_id AND version='mk7-v1'"
                ),
                {"workspace_id": workspace["workspace"]["uuid"]},
            ).scalar_one() == "applied"
    finally:
        app.dependency_overrides.clear()
        database_ref = database.get("database_ref") if database else None
        role_ref = database.get("role_ref") if database else None
        runtime_role_ref = database.get("runtime_role_ref") if database else None
        if database_ref and role_ref and runtime_role_ref:
            with psycopg.connect(
                admin_url.render_as_string(hide_password=False), autocommit=True
            ) as connection:
                connection.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s",
                    (database_ref,),
                )
                connection.execute(
                    psycopg.sql.SQL("DROP DATABASE IF EXISTS {}").format(
                        psycopg.sql.Identifier(str(database_ref))
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(str(runtime_role_ref))
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(str(backup_role_ref))
                    )
                )
                connection.execute(
                    psycopg.sql.SQL("DROP ROLE IF EXISTS {}").format(
                        psycopg.sql.Identifier(str(role_ref))
                    )
                )
