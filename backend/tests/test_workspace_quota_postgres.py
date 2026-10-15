"""Exact-quota checks against an explicitly selected disposable PostgreSQL 18."""
from __future__ import annotations

import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from uuid import UUID

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from test_digital_asset_hosting import _actor

from app.api.deps import current_actor
from app.core.config import get_settings
from app.db.session import get_engine, tenant_session
from app.main import app
from app.services import workspace_autonomy as service
from app.services import workspace_autonomy_base as base

pytestmark = pytest.mark.integration
MIB = 1024 * 1024
CURRENT = 2560 * MIB
TARGET = 3072 * MIB


@pytest.fixture
def workspace():
    explicit_url = os.environ.get("WAREHOUSE_QUOTA_TEST_DATABASE_URL")
    if not explicit_url:
        pytest.skip("requires an explicitly selected disposable quota database")
    parsed = make_url(explicit_url)
    assert parsed.host == "127.0.0.1"
    assert parsed.database == "mk4_reclaim_test_20261016"
    assert parsed.port and parsed.port != 5432
    assert explicit_url == get_settings().database_url
    with get_engine().connect() as connection:
        version = int(connection.execute(text("SHOW server_version_num")).scalar_one())
        role = connection.execute(text(
            "SELECT rolsuper,rolbypassrls FROM pg_roles WHERE rolname=current_user"
        )).one()
        assert version >= 180000
        assert not role.rolsuper and not role.rolbypassrls
    actor = _actor("exact-quota")
    app.dependency_overrides[current_actor] = lambda: actor
    try:
        client = TestClient(app)
        response = client.post("/api/digital-assets/provision", json={
            "name": "Disposable Exact Quota",
            "asset_kind": "software",
            "workspace_key": "exact-quota-test",
            "runtime_type": "static",
            "service_plan": "custody",
        })
        assert response.status_code == 201
        headers = {"Authorization": "Bearer " + response.json()["api_key"]}
        manifest_response = client.get("/api/workspaces/v1/autonomy", headers=headers)
        assert manifest_response.status_code == 200
        manifest = manifest_response.json()
        identity = manifest["credential"]
        credential = base.WorkspaceCredential(
            tenant_id=actor.tenant_id,
            workspace_id=UUID(manifest["workspace"]["uuid"]),
            credential_id=UUID(identity["credential_id"]),
            scopes=frozenset(identity["scopes"]),
            key_kind=identity["key_kind"],
            label=identity["label"],
            parent_credential_id=None,
        )
        configured = service.resize_capacity(credential, {
            "target_mb": 2560,
            "expected_revision": manifest["workspace"]["revision"],
        })
        assert configured["quota_bytes"] == CURRENT
        yield credential, configured["revision"]
    finally:
        app.dependency_overrides.clear()


def _row_and_target_audits(credential):
    with tenant_session(credential.tenant_id) as session:
        row = base._workspace_row(session, credential.workspace_id)
        audits = session.execute(text(
            "SELECT payload FROM audit.events "
            "WHERE event_type='digital_asset.workspace_quota_elastic_increase' "
            "AND payload->>'workspace_id'=:workspace "
            "AND (payload->>'after_bytes')::bigint > :before"
        ), {"workspace": str(credential.workspace_id), "before": CURRENT}).scalars().all()
    return row, audits


def _locked_requests(monkeypatch, credential, revision, second_target_mb):
    entered = threading.Event()
    release = threading.Event()
    pids = []
    pid_lock = threading.Lock()
    original_usage = base._workspace_billable_usage
    original_workspace = base._workspace_row

    def observe_workspace(session, workspace_id, *, lock=False):
        pid = session.execute(text("SELECT pg_backend_pid()")).scalar_one()
        with pid_lock:
            pids.append(pid)
        return original_workspace(session, workspace_id, lock=lock)

    def pause_first_usage(*args, **kwargs):
        if not entered.is_set():
            entered.set()
            assert release.wait(10), "test release signal timed out"
        return original_usage(*args, **kwargs)

    monkeypatch.setattr(base, "_workspace_row", observe_workspace)
    monkeypatch.setattr(base, "_workspace_billable_usage", pause_first_usage)

    def resize(target):
        try:
            return service.resize_capacity(credential, {
                "target_mb": target, "expected_revision": revision,
            })
        except HTTPException as error:
            return error

    blocked_on_database_lock = False
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(resize, 3072)
        try:
            assert entered.wait(10), "first transaction did not reach locked measurement"
            second = pool.submit(resize, second_target_mb)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                with pid_lock:
                    second_pid = pids[1] if len(pids) > 1 else None
                if second_pid is not None:
                    with get_engine().connect() as connection:
                        wait = connection.execute(text(
                            "SELECT wait_event_type FROM pg_stat_activity WHERE pid=:pid"
                        ), {"pid": second_pid}).scalar_one_or_none()
                    if wait == "Lock":
                        blocked_on_database_lock = True
                        break
                time.sleep(0.01)
            assert blocked_on_database_lock, "second transaction never waited on a PG row lock"
            assert not second.done()
        finally:
            release.set()
        results = first.result(timeout=10), second.result(timeout=10)
    return results


def test_postgres_same_target_waits_then_returns_noop_once(monkeypatch, workspace):
    credential, revision = workspace
    first, second = _locked_requests(monkeypatch, credential, revision, 3072)
    assert first["changed"] is True
    assert second["changed"] is False
    assert second["target_already_satisfied"] is True
    assert first["quota_bytes"] == second["quota_bytes"] == TARGET
    assert first["revision"] == second["revision"] == revision + 1
    row, audits = _row_and_target_audits(credential)
    assert row["storage_quota_bytes"] == TARGET
    assert row["revision"] == revision + 1
    assert len(audits) == 1
    assert audits[0]["requested_target_bytes"] == TARGET
    assert audits[0]["requested_by_credential_id"] == str(credential.credential_id)


def test_postgres_different_target_waits_then_rejects_stale_revision(monkeypatch, workspace):
    credential, revision = workspace
    first, second = _locked_requests(monkeypatch, credential, revision, 3584)
    assert first["quota_bytes"] == TARGET
    assert isinstance(second, HTTPException)
    assert second.status_code == 409
    row, audits = _row_and_target_audits(credential)
    assert row["storage_quota_bytes"] == TARGET
    assert row["revision"] == revision + 1
    assert len(audits) == 1


def test_postgres_audit_failure_rolls_back_quota_and_revision(workspace):
    credential, revision = workspace
    migration_url = os.environ["WAREHOUSE_MIGRATION_DATABASE_URL"]
    app_url, migration = make_url(get_settings().database_url), make_url(migration_url)
    assert (migration.host, migration.port, migration.database) == (
        app_url.host, app_url.port, app_url.database,
    )
    engine = create_engine(migration_url)
    suffix = credential.workspace_id.hex
    function = "quota_test_reject_" + suffix
    trigger = "quota_test_trigger_" + suffix
    # Both identifiers and the UUID literal come from UUID.hex, never user input.
    with engine.begin() as connection:
        connection.execute(text(f"""
            CREATE FUNCTION app.{function}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
              IF NEW.event_type='digital_asset.workspace_quota_elastic_increase'
                 AND NEW.payload->>'workspace_id'='{credential.workspace_id}' THEN
                RAISE EXCEPTION 'synthetic quota audit rejection';
              END IF;
              RETURN NEW;
            END $$;
            CREATE TRIGGER {trigger} BEFORE INSERT ON audit.events
            FOR EACH ROW EXECUTE FUNCTION app.{function}();
        """))
    try:
        with pytest.raises(DBAPIError, match="synthetic quota audit rejection"):
            service.resize_capacity(credential, {
                "target_mb": 3072, "expected_revision": revision,
            })
        row, audits = _row_and_target_audits(credential)
        assert row["storage_quota_bytes"] == CURRENT
        assert row["revision"] == revision
        assert not audits
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TRIGGER {trigger} ON audit.events"))
            connection.execute(text(f"DROP FUNCTION app.{function}()"))
        engine.dispose()


def test_postgres_tenant_rls_prevents_cross_workspace_resize(workspace):
    credential, revision = workspace
    other = _actor("quota-other-tenant")
    wrong_tenant = replace(credential, tenant_id=other.tenant_id)
    with pytest.raises(HTTPException) as caught:
        service.resize_capacity(wrong_tenant, {
            "target_mb": 3072, "expected_revision": revision,
        })
    assert caught.value.status_code == 404
    row, audits = _row_and_target_audits(credential)
    assert row["storage_quota_bytes"] == CURRENT
    assert row["revision"] == revision
    assert not audits
