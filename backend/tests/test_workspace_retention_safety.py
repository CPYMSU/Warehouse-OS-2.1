from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import workspace_retention as retention


class Result:
    def __init__(self, rows=(), scalar=None):
        self.rows = list(rows)
        self.scalar = scalar

    def mappings(self):
        return self

    def all(self):
        return self.rows

    def scalars(self):
        return self.rows

    def one(self):
        return self.rows[0]

    def scalar_one(self):
        return self.scalar

    def scalar_one_or_none(self):
        return self.scalar

    def __iter__(self):
        return iter(self.rows)


class Database:
    def __init__(self, rows, pages=(), releases=()):
        self.rows = rows
        self.pages = list(pages)
        self.releases = list(releases)
        self.events = []

    def execute(self, statement, params):
        sql = str(statement)
        if "FROM digital_asset.deployments WHERE workspace_id=" in sql:
            return Result(sorted(self.rows, key=lambda x: x["created_at"], reverse=True))
        if "FROM platform.pages_routes " in sql:
            return Result(self.pages)
        if "FROM digital_asset.release_sessions " in sql:
            return Result(self.releases)
        if any(
            x in sql
            for x in (
                "FROM digital_asset.workspace_components ",
                "FROM digital_asset.source_upload_jobs",
                "FROM digital_asset.asset_versions ",
            )
        ):
            return Result()
        if "FROM digital_asset.deployments WHERE id=" in sql:
            return Result([next(x for x in self.rows if x["id"] == params["id"])])
        if "FROM digital_asset.deployment_events " in sql:
            return Result(scalar=len(self.events) + 1)
        if "INSERT INTO digital_asset.deployment_events" in sql:
            self.events.append(params)
            return Result()
        if "UPDATE digital_asset.deployments" in sql:
            row = next(x for x in self.rows if x["id"] == params["id"])
            row["result"] = json.loads(params["result"])
            if "SET status=CASE" in sql and row["status"] == "ready":
                row.update(status="rolled_back", health="unknown")
            return Result()
        if "SELECT issued_by FROM digital_asset.api_credentials" in sql:
            return Result(scalar=None)
        raise AssertionError("Unexpected SQL: " + sql)


def deployment(*, age=72, mode="service", status="ready", component=None, result=None):
    return {
        "id": uuid4(),
        "source_version_id": uuid4(),
        "component_id": component or "api",
        "status": status,
        "health": "healthy",
        "created_at": datetime.now(UTC) - timedelta(hours=age),
        "requested_config": {"execution_mode": mode},
        "result": {"container_names": [], "execution_mode": mode, **(result or {})},
    }


@pytest.fixture
def scope(tmp_path):
    credential = SimpleNamespace(
        tenant_id=uuid4(),
        workspace_id=uuid4(),
        credential_id=uuid4(),
        key_kind="primary",
        require=lambda scope: None,
    )
    settings = Settings(hosted_runtime_data_root=tmp_path / "runtime")
    current, previous, old = deployment(age=1), deployment(age=2), deployment()
    current["result"]["previous_active_deployment_id"] = str(previous["id"])
    workspace = {"asset_id": uuid4(), "active_deployment_id": current["id"]}
    return credential, settings, workspace, [current, previous, old]


def plan(scope, *, extra=(), pages=(), releases=(), payload=None):
    credential, settings, workspace, rows = scope
    db = Database([*rows, *extra], pages, releases)
    policy = retention.RetentionPolicy.from_payload(payload or {})
    return retention._build_plan(db, credential, settings, policy, workspace=workspace)


def candidate_ids(value):
    return {x["id"] for x in value["deployment_candidates"]}


def test_current_previous_static_job_and_pending_roots_survive_recovery(scope):
    current, previous, old = scope[3]
    static, job = deployment(), deployment(mode="job")
    pending, pending_previous = deployment(), deployment()
    for row in (current, previous, static, job, pending, pending_previous):
        row["result"]["retention"] = {"state": "retry_required"}
    route = {
        "active_deployment_id": current["id"],
        "config": {"static_frontend": {"deployment_id": str(static["id"]), "enabled": True}},
    }
    result = plan(
        scope,
        extra=[static, job, pending, pending_previous],
        pages=[route],
        releases=[
            {
                "candidate_deployment_id": pending["id"],
                "previous_deployment_id": pending_previous["id"],
            }
        ],
    )
    assert candidate_ids(result) == {str(old["id"])}
    protected = {x["id"]: x["reasons"] for x in result["protected"]["deployments"]}
    assert "job_evidence" in protected[str(job["id"])]
    assert "pages_static_frontend" in protected[str(static["id"])]


def test_static_path_is_protected_even_if_deployment_id_is_missing(scope):
    static = deployment()
    credential = scope[0]
    route = {
        "active_deployment_id": scope[3][0]["id"],
        "config": {
            "static_frontend": {
                "runtime_rel_path": (
                    f"tenants/{credential.tenant_id}/"
                    f"workspaces/{credential.workspace_id}/"
                    f"releases/{static['id']}/build"
                )
            }
        },
    }
    assert str(static["id"]) not in candidate_ids(plan(scope, extra=[static], pages=[route]))


def test_failed_and_pinned_deployments_are_held_even_on_retry(scope):
    failed = deployment(status="failed")
    pinned = deployment(result={"retention": {"pinned": True, "state": "retry_required"}})
    value = plan(scope, extra=[failed, pinned])
    assert not {str(failed["id"]), str(pinned["id"])} & candidate_ids(value)


def test_explicit_allowlist_is_bound_to_digest_and_empty_means_none(scope):
    second = deployment(age=100)
    one = plan(scope, extra=[second], payload={"deployment_ids": [str(scope[3][2]["id"])]})
    two = plan(scope, extra=[second], payload={"deployment_ids": [str(second["id"])]})
    assert candidate_ids(one) == {str(scope[3][2]["id"])}
    assert one["plan_digest"] != two["plan_digest"]
    assert candidate_ids(plan(scope, payload={"deployment_ids": []})) == set()


def test_allowlist_rejects_unknown_workspace_uuid(scope):
    with pytest.raises(HTTPException) as exc:
        plan(scope, payload={"deployment_ids": [str(uuid4())]})
    assert exc.value.status_code == 422


@pytest.mark.parametrize(
    "field", ["include_sources", "include_expired_uploads", "include_python_environments"]
)
def test_string_false_is_rejected(field):
    with pytest.raises(HTTPException):
        retention.RetentionPolicy.from_payload({field: "false"})


@pytest.mark.parametrize("ids", ["any", [123], ["not-a-uuid"]])
def test_allowlist_must_be_uuid_array(ids):
    with pytest.raises(HTTPException):
        retention.RetentionPolicy.from_payload({"deployment_ids": ids})


def test_duplicate_allowlist_rejected():
    identifier = str(uuid4())
    with pytest.raises(HTTPException):
        retention.RetentionPolicy.from_payload({"deployment_ids": [identifier, identifier]})


@pytest.mark.parametrize("part", ["workspace", "releases", "deployment"])
def test_symlink_ancestor_inside_runtime_root_is_rejected(scope, part):
    credential, settings, _, rows = scope
    release = retention._release_path(
        settings,
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        deployment_id=rows[2]["id"],
    )
    link = {"workspace": release.parent.parent, "releases": release.parent, "deployment": release}[
        part
    ]
    link.parent.mkdir(parents=True)
    alternate = settings.hosted_runtime_data_root / "other-workspace-data"
    alternate.mkdir()
    link.symlink_to(alternate, target_is_directory=True)
    with pytest.raises(RuntimeError, match="Symlinked"):
        retention._release_path(
            settings,
            tenant_id=credential.tenant_id,
            workspace_id=credential.workspace_id,
            deployment_id=rows[2]["id"],
        )


def acknowledged_result(names=()):
    run, digest = str(uuid4()), "a" * 64
    return {
        "container_names": list(names),
        "retention": {
            "state": "retry_required",
            "run_id": run,
            "plan_digest": digest,
            "containers_retired_at": "2026-10-16T00:00:00+00:00",
            "containers_retired_run_id": run,
            "containers_retired_plan_digest": digest,
            "containers_retired_names_digest": retention._container_names_digest(list(names)),
        },
    }


def test_ack_requires_current_run_plan_and_exact_names_even_when_empty():
    result = acknowledged_result()
    assert retention._containers_retired(result)
    for field in (
        "containers_retired_run_id",
        "containers_retired_plan_digest",
        "containers_retired_names_digest",
    ):
        altered = copy.deepcopy(result)
        altered["retention"][field] = "stale"
        assert not retention._containers_retired(altered)
    assert not retention._containers_retired(
        {"retention": {"containers_retired_at": "old-bare-timestamp"}}
    )


def test_modified_container_set_invalidates_ack():
    result = acknowledged_result(["warehouse-runtime-example"])
    result["container_names"].append("warehouse-runtime-other")
    assert not retention._containers_retired(result)


def test_retry_preserves_ack_run_and_original_plan(scope, monkeypatch):
    credential, _, _, rows = scope
    old = rows[2]
    old["result"].update(acknowledged_result())
    saved = copy.deepcopy(old["result"]["retention"])
    db = Database(rows)
    monkeypatch.setattr(retention, "_audit", lambda *args, **kwargs: None)
    value = {
        "deployment_candidates": [{"id": str(old["id"])}],
        "source_candidates": [],
        "expired_uploads": [],
        "plan_digest": "b" * 64,
        "policy": {},
    }
    retention._mark_retiring(db, credential, value, uuid4())
    assert old["result"]["retention"]["run_id"] == saved["run_id"]
    assert old["result"]["retention"]["plan_digest"] == saved["plan_digest"]
    assert retention._containers_retired(old["result"])


def test_environment_flag_never_deletes_unproved_shared_or_unknown_env(scope):
    credential, settings, _, rows = scope
    digest = "c" * 64
    root = retention._workspace_path(
        settings, credential.tenant_id, credential.workspace_id, "data", ".runtime", "python"
    )
    (root / digest).mkdir(parents=True)
    (root / "unknown").mkdir()
    for row in rows:
        row["result"].update(runtime_kind="python", build={"build_digest": digest})
    value = plan(scope, payload={"include_python_environments": True})["python_environments"]
    assert value["status"] == "held"
    assert value["candidates"] == []
    assert value["complete_reference_closure"] is False
    assert len(value["held"]) == 2
    assert (root / digest).is_dir()


def test_binding_change_after_marking_blocks_physical_deletion(scope, monkeypatch):
    credential, settings, workspace, rows = scope
    old = rows[2]
    old["result"].update(acknowledged_result())
    target = retention._release_path(
        settings,
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        deployment_id=old["id"],
    )
    target.mkdir(parents=True)
    (target / "must-survive.txt").write_text("alive")
    db = Database(rows)
    policy = {"deployment_ids": [str(old["id"])]}
    before = retention._build_plan(
        db,
        credential,
        settings,
        retention.RetentionPolicy.from_payload(policy),
        workspace=workspace,
    )

    @contextmanager
    def fake_transaction(_tenant):
        yield db

    monkeypatch.setattr(retention, "tenant_session", fake_transaction)
    monkeypatch.setattr(retention, "_workspace_row", lambda *a, **kw: workspace)
    monkeypatch.setattr(retention, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(retention, "_workspace_billable_usage", lambda *a, **kw: {})
    mark = retention._mark_retiring

    def changed_binding(*args):
        mark(*args)
        workspace["active_deployment_id"] = old["id"]

    monkeypatch.setattr(retention, "_mark_retiring", changed_binding)
    result = retention.apply_workspace_retention(
        credential, settings, {**policy, "confirm_plan_digest": before["plan_digest"]}
    )
    assert result["ok"] is False
    assert result["errors"][0]["error"] == "retention_target_now_protected_or_changed"
    assert (target / "must-survive.txt").read_text() == "alive"


def test_result_job_cannot_be_overridden_by_requested_service(scope):
    job = deployment(result={"execution_mode": "job"})
    assert str(job["id"]) not in candidate_ids(plan(scope, extra=[job]))


def test_two_phase_empty_inventory_ack_and_idempotent_retirement(scope, monkeypatch):
    credential, settings, workspace, rows = scope
    old = rows[2]
    target = retention._release_path(
        settings,
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        deployment_id=old["id"],
    )
    target.mkdir(parents=True)
    (target / "old-runtime.txt").write_bytes(b"retire-me")
    db = Database(rows)
    policy = {
        "deployment_ids": [str(old["id"])],
        "include_sources": False,
        "include_expired_uploads": False,
    }

    @contextmanager
    def transaction(_tenant):
        yield db

    monkeypatch.setattr(retention, "tenant_session", transaction)
    monkeypatch.setattr(retention, "_workspace_row", lambda *a, **kw: workspace)
    monkeypatch.setattr(retention, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(retention, "_workspace_billable_usage", lambda *a, **kw: {})

    def fresh_apply():
        value = retention._build_plan(
            db,
            credential,
            settings,
            retention.RetentionPolicy.from_payload(policy),
            workspace=workspace,
        )
        return retention.apply_workspace_retention(
            credential,
            settings,
            {**policy, "confirm_plan_digest": value["plan_digest"]},
        )

    first = fresh_apply()
    assert first["ok"] is False
    assert first["errors"][0]["error"] == "runtime_controller_cleanup_pending"
    assert target.is_dir()
    saved = old["result"]["retention"]
    saved.update(
        {
            "containers_retired_at": datetime.now(UTC).isoformat(),
            "containers_retired_run_id": saved["run_id"],
            "containers_retired_plan_digest": saved["plan_digest"],
            "containers_retired_names_digest": retention._container_names_digest([]),
        }
    )
    original_execute = db.execute

    def verify_ledger_before_summary(statement, params):
        if "SELECT issued_by" in str(statement) and not target.exists():
            assert old["result"]["retention"]["state"] == "retired"
        return original_execute(statement, params)

    db.execute = verify_ledger_before_summary
    second = fresh_apply()
    assert second["ok"] is True
    assert second["reclaimed"]["runtime_bytes"] == len(b"retire-me")
    assert not target.exists()
    assert old["result"]["retention"]["state"] == "retired"
    third = fresh_apply()
    assert third["ok"] is True
    assert third["counts"]["deployments"] == 0
    assert third["reclaimed"]["runtime_bytes"] == 0


def test_other_retry_completion_cannot_be_regressed_or_counted_twice(scope, monkeypatch):
    credential, settings, workspace, rows = scope
    old = rows[2]
    old["result"].update(acknowledged_result())
    db = Database(rows)
    policy = {
        "deployment_ids": [str(old["id"])],
        "include_sources": False,
        "include_expired_uploads": False,
    }
    original_build = retention._build_plan
    before = original_build(
        db,
        credential,
        settings,
        retention.RetentionPolicy.from_payload(policy),
        workspace=workspace,
    )

    @contextmanager
    def transaction(_tenant):
        yield db

    monkeypatch.setattr(retention, "tenant_session", transaction)
    monkeypatch.setattr(retention, "_workspace_row", lambda *a, **kw: workspace)
    monkeypatch.setattr(retention, "_audit", lambda *a, **kw: None)
    monkeypatch.setattr(retention, "_workspace_billable_usage", lambda *a, **kw: {})
    calls = 0

    def another_retry_finishes(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            old["result"]["retention"].update(state="retired", reclaimed_bytes=123)
        return original_build(*args, **kwargs)

    monkeypatch.setattr(retention, "_build_plan", another_retry_finishes)
    result = retention.apply_workspace_retention(
        credential, settings, {**policy, "confirm_plan_digest": before["plan_digest"]}
    )
    assert result["ok"] is True
    assert result["reclaimed"]["runtime_bytes"] == 0
    assert old["result"]["retention"]["state"] == "retired"
    assert old["result"]["retention"]["reclaimed_bytes"] == 123


def test_recovery_operation_identity_is_bound_to_plan_digest(scope):
    row = scope[3][2]
    row["result"]["retention"] = {
        "state": "retry_required",
        "run_id": "first",
        "plan_digest": "a" * 64,
    }
    first = plan(scope)
    row["result"]["retention"]["run_id"] = "different"
    second = plan(scope)
    assert first["plan_digest"] != second["plan_digest"]
