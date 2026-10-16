from __future__ import annotations

import copy
import hashlib
import json
from contextlib import contextmanager
from uuid import UUID

import httpx
import pytest

from app import runtime_controller_base as runtime
from app.core.config import Settings

TENANT = UUID("10000000-0000-0000-0000-000000000001")
WORKSPACE = UUID("20000000-0000-0000-0000-000000000002")
DEPLOYMENT = UUID("33333333-4444-5555-6666-000000000003")
OTHER = UUID("99999999-aaaa-bbbb-cccc-000000000009")
NAME = f"warehouse-runtime-{DEPLOYMENT.hex[:20]}"
COMPOSE = f"warehouse-runtime-{DEPLOYMENT.hex[:16]}-web-0"


def labels(**overrides: str) -> dict[str, str]:
    return {
        "org.bonfirework.managed": "runtime-controller",
        "org.bonfirework.workspace": str(WORKSPACE),
        "org.bonfirework.deployment": str(DEPLOYMENT),
        **overrides,
    }


def container(name: str = NAME, *, serial: int = 1, **overrides: str) -> dict:
    return {"id": f"{serial:064x}", "name": name, "labels": labels(**overrides)}


class Engine:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.items = [container()]
        self.removed: list[str] = []
        self.closed = False
        self.fail_id: str | None = None
        self.keep_removed = False
        self.replacement: dict | None = None
        self.after_remove = None

    def retention_container_inventory(self) -> list[dict]:
        assert self.store.locked == ["workspace", "deployment"]
        return [
            {"id": item["id"], "names": [item["name"]], "labels": item["labels"]}
            for item in self.items
        ]

    def retention_container(self, reference: str) -> dict | None:
        assert self.store.locked == ["workspace", "deployment"]
        return copy.deepcopy(next(
            (item for item in self.items if reference in (item["name"], item["id"])), None,
        ))

    def remove(self, reference: str) -> None:
        assert self.store.locked == ["workspace", "deployment"]
        assert len(reference) == 64  # Never remove by a reusable name.
        if reference == self.fail_id:
            raise RuntimeError("upstream secret=must-not-be-recorded")
        self.removed.append(reference)
        if not self.keep_removed:
            self.items = [item for item in self.items if item["id"] != reference]
        if self.replacement:
            self.items.append(self.replacement)
        if self.after_remove:
            self.after_remove()

    def close(self) -> None:
        self.closed = True


class Result:
    def __init__(self, value=None) -> None:
        self.value = value

    def mappings(self):
        return self

    def __iter__(self):
        return iter(self.value)

    def one_or_none(self):
        return self.value

    def scalar_one(self):
        return self.value

    def scalar_one_or_none(self):
        return self.value


class Store:
    def __init__(self) -> None:
        self.row = {
            "id": DEPLOYMENT, "workspace_id": WORKSPACE, "status": "rolled_back",
            "requested_config": {},
            "result": {
                "container_names": [NAME], "execution_mode": "service",
                "retention": {"state": "retiring", "run_id": "run-1", "plan_digest": "a" * 64},
            },
        }
        self.selected = None
        self.protected = False
        self.locked: list[str] = []
        self.sql: list[str] = []
        self.events: list[tuple] = []
        self.writes = 0

    def execute(self, statement, params=None):
        sql = str(statement)
        self.sql.append(sql)
        if "SELECT id,workspace_id,result" in sql:
            return Result([copy.deepcopy(self.selected or self.row)])
        if "SELECT id FROM digital_asset.workspaces" in sql:
            assert "FOR UPDATE" in sql
            self.locked.append("workspace")
            return Result(WORKSPACE)
        if "SELECT status,requested_config,result" in sql:
            assert self.locked == ["workspace"] and "FOR UPDATE" in sql
            self.locked.append("deployment")
            return Result(copy.deepcopy(self.row))
        if "SELECT\n                  EXISTS" in sql:
            assert self.locked == ["workspace", "deployment"]
            assert params["release_path"] == (
                f"tenants/{TENANT}/workspaces/{WORKSPACE}/releases/{DEPLOYMENT}"
            )
            assert params["release_prefix"] == params["release_path"] + "/%"
            return Result(self.protected)
        if "SET result=CAST(:result AS jsonb)" in sql:
            self.row["result"] = json.loads(params["result"])
            self.writes += 1
            return Result()
        raise AssertionError(sql)

    @contextmanager
    def session(self, _tenant):
        assert _tenant == TENANT
        assert not self.locked
        try:
            yield self
        finally:
            self.locked.clear()

    @property
    def retention(self):
        return self.row["result"]["retention"]


@pytest.fixture
def harness(monkeypatch):
    store = Store()
    engine = Engine(store)
    controller = runtime.RuntimeController(Settings())
    monkeypatch.setattr(controller, "_tenants", lambda: [TENANT])
    monkeypatch.setattr(runtime, "tenant_session", store.session)
    monkeypatch.setattr(runtime, "DockerEngine", lambda _socket: engine)
    monkeypatch.setattr(runtime, "_event", lambda *args: store.events.append(args))
    return controller, store, engine


def test_retirement_verifies_identity_and_binds_ack(harness):
    controller, store, engine = harness
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.removed == [f"{1:064x}"]
    assert engine.closed
    assert store.retention["containers_retired_at"]
    assert store.retention["containers_retired_run_id"] == "run-1"
    assert store.retention["containers_retired_plan_digest"] == "a" * 64
    assert store.retention["containers_retired_names_digest"] == hashlib.sha256(
        json.dumps([NAME], separators=(",", ":")).encode()
    ).hexdigest()
    assert store.events[0][3] == "retention_containers_retired"
    assert controller.reconcile_retention_runtime_containers() == 0


@pytest.mark.parametrize("raw", [
    [f"warehouse-runtime-{OTHER.hex[:20]}"], [NAME, NAME], ["../escape"],
    "warehouse-runtime-invalid", None, [f"warehouse-runtime-{DEPLOYMENT.hex[:16]}abcd"],
])
def test_invalid_or_foreign_names_never_delete(harness, raw):
    controller, store, engine = harness
    store.row["result"]["container_names"] = raw
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed
    assert store.retention["container_cleanup_error"] == "retention_container_names_invalid"
    assert "containers_retired_at" not in store.retention


@pytest.mark.parametrize("name", [NAME, NAME + "-r2", COMPOSE])
def test_existing_single_service_and_compose_names_are_supported(name):
    assert runtime.RuntimeController._retention_names(
        DEPLOYMENT, {"container_names": [name]},
    ) == [name]


@pytest.mark.parametrize("overrides", [
    {"org.bonfirework.deployment": str(OTHER)},
    {"org.bonfirework.workspace": str(OTHER)},
    {"org.bonfirework.managed": "another-controller"},
    {"org.bonfirework.deployment": ""},
])
def test_labels_must_match_full_deployment_workspace_and_manager(harness, overrides):
    controller, store, engine = harness
    engine.items = [container(**overrides)]
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed
    assert store.retention["container_cleanup_error"] == "retention_container_ownership_mismatch"


def test_preflight_checks_whole_container_set_before_any_removal(harness):
    controller, store, engine = harness
    store.row["result"]["container_names"] = [NAME, COMPOSE]
    engine.items.append(container(COMPOSE, serial=2, **{"org.bonfirework.workspace": str(OTHER)}))
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == []


@pytest.mark.parametrize("missing_metadata", [False, True])
def test_empty_or_missing_names_require_no_owned_containers(harness, missing_metadata):
    controller, store, engine = harness
    if missing_metadata:
        store.row["result"].pop("container_names")
    else:
        store.row["result"]["container_names"] = []
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == []
    assert "containers_retired_at" not in store.retention
    engine.items.clear()
    controller._last_retention_container_reconcile = 0
    assert controller.reconcile_retention_runtime_containers() == 1
    assert store.retention["containers_retired_names_digest"] == hashlib.sha256(b"[]").hexdigest()


def test_other_workspace_inventory_is_untouched(harness):
    controller, store, engine = harness
    foreign = container(
        f"warehouse-runtime-{OTHER.hex[:20]}", serial=2,
        **{"org.bonfirework.workspace": str(OTHER), "org.bonfirework.deployment": str(OTHER)},
    )
    engine.items.append(foreign)
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.items == [foreign]


def test_missing_container_is_idempotent(harness):
    controller, store, engine = harness
    engine.items.clear()
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.removed == []


def test_partial_failure_retries_without_ack_or_raw_upstream_error(harness):
    controller, store, engine = harness
    store.row["result"]["container_names"] = [NAME, NAME + "-r1"]
    engine.items.append(container(NAME + "-r1", serial=2))
    engine.fail_id = f"{2:064x}"
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == [f"{1:064x}"]
    assert "containers_retired_at" not in store.retention
    assert store.retention["container_cleanup_error"] == "retention_container_cleanup_failed"
    assert "must-not-be-recorded" not in json.dumps(store.row["result"])
    engine.fail_id = None
    controller._last_retention_container_reconcile = 0
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.removed == [f"{1:064x}", f"{2:064x}"]


@pytest.mark.parametrize("keep_removed", [True, False])
def test_container_present_or_reused_name_prevents_ack(harness, keep_removed):
    controller, store, engine = harness
    engine.keep_removed = keep_removed
    if not keep_removed:
        engine.replacement = container(serial=2, **{"org.bonfirework.workspace": str(OTHER)})
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == [f"{1:064x}"]
    assert "containers_retired_at" not in store.retention
    assert store.retention["container_cleanup_error"] == "retention_container_still_present"


@pytest.mark.parametrize("reason", [
    "active", "pages", "pages_static_id", "pages_static_path", "previous", "open_release",
])
def test_protected_references_cannot_be_retired(harness, reason):
    controller, store, engine = harness
    store.protected = True
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed and store.writes == 0
    guard = next(sql for sql in store.sql if "SELECT\n                  EXISTS" in sql)
    assert "active_deployment_id" in guard and "platform.pages_routes" in guard
    assert "'{static_frontend,deployment_id}'=CAST(:id AS text)" in guard
    assert "'{static_frontend,runtime_rel_path}'=:release_path" in guard
    assert "LIKE :release_prefix" in guard
    assert "previous_active_deployment_id" in guard
    assert "candidate_deployment_id=:id OR current_job_deployment_id=:id" in guard
    assert "previous_deployment_id=:id" in guard


@pytest.mark.parametrize("status", ["ready", "queued", "building", "deploying"])
def test_repaired_or_reactivated_deployment_cannot_be_retired(harness, status):
    controller, store, engine = harness
    store.row["status"] = status
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed and store.writes == 0


@pytest.mark.parametrize("where,change", [
    ("requested_config", {"execution_mode": "job"}),
    ("result", {"execution_mode": "job"}),
    ("requested_config", {"retention": {"pinned": True}}),
])
def test_job_and_pinned_deployments_are_untouched(harness, where, change):
    controller, store, engine = harness
    store.row[where].update(change)
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed and store.writes == 0


@pytest.mark.parametrize("field,value", [
    ("run_id", "new-run"), ("plan_digest", "b" * 64), ("state", "retired"),
])
def test_stale_operation_does_not_act_or_ack_new_state(harness, field, value):
    controller, store, engine = harness
    store.selected = copy.deepcopy(store.row)
    store.retention[field] = value
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed and store.writes == 0


def test_changed_names_since_candidate_read_do_not_act(harness):
    controller, store, engine = harness
    store.selected = copy.deepcopy(store.row)
    store.row["result"]["container_names"] = [COMPOSE]
    assert controller.reconcile_retention_runtime_containers() == 0
    assert not engine.removed and store.writes == 0


def test_legacy_timestamp_is_not_a_trusted_ack(harness):
    controller, store, engine = harness
    store.retention["containers_retired_at"] = "old"
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.removed == [f"{1:064x}"]
    assert store.retention["containers_retired_at"] != "old"


def test_valid_bound_ack_is_idempotent(harness):
    controller, store, engine = harness
    assert controller.reconcile_retention_runtime_containers() == 1
    controller._last_retention_container_reconcile = 0
    assert controller.reconcile_retention_runtime_containers() == 0
    assert store.writes == 1 and len(store.events) == 1


def test_docker_retention_inspection_returns_only_identity_and_accepts_404():
    calls = []
    def handle(request):
        calls.append(request)
        if request.url.path.endswith("/missing/json"):
            return httpx.Response(404)
        return httpx.Response(200, json={
            "Id": "a" * 64, "Name": "/" + NAME,
            "Config": {"Labels": labels(), "Env": ["SECRET=never-return"]},
        })
    engine = object.__new__(runtime.DockerEngine)
    engine.client = httpx.Client(transport=httpx.MockTransport(handle), base_url="http://docker")
    engine.api_prefix = "/v1.45"
    assert engine.retention_container("missing") is None
    metadata = engine.retention_container(NAME)
    assert set(metadata) == {"id", "name", "labels"}
    assert "never-return" not in json.dumps(metadata)
    engine.close()


def test_docker_retention_inventory_does_not_hide_stopped_or_unknown_names():
    calls = []
    def handle(request):
        calls.append(request)
        return httpx.Response(200, json=[
            {"Id": "a" * 64, "Names": ["/unexpected"], "Labels": labels(), "State": "exited"},
            {"Id": "b" * 64, "Names": ["/unmanaged"], "Labels": None},
        ])
    engine = object.__new__(runtime.DockerEngine)
    engine.client = httpx.Client(transport=httpx.MockTransport(handle), base_url="http://docker")
    engine.api_prefix = "/v1.45"
    result = engine.retention_container_inventory()
    assert result[0]["names"] == ["unexpected"]
    assert result[1]["labels"] == {}
    assert calls[0].url.params["all"] == "true"
    assert "filters" not in calls[0].url.params
    engine.close()


@pytest.mark.parametrize("where", ["requested_config", "result", "both"])
def test_explicit_expired_job_retirement_uses_same_locked_identity_checks(harness, where):
    controller, store, engine = harness
    for key in (("requested_config", "result") if where == "both" else (where,)):
        store.row[key]["execution_mode"] = "job"
    store.retention["retire_terminal_evidence"] = True
    assert controller.reconcile_retention_runtime_containers() == 1
    assert engine.removed == [f"{1:064x}"]
    assert store.retention["containers_retired_run_id"] == "run-1"
    selection = next(sql for sql in store.sql if "SELECT id,workspace_id,result" in sql)
    assert "retire_terminal_evidence" in selection


@pytest.mark.parametrize("flag", [False, None, "true", 1])
def test_job_opt_in_requires_actual_boolean_true(harness, flag):
    controller, store, engine = harness
    store.row["result"]["execution_mode"] = "job"
    store.retention["retire_terminal_evidence"] = flag
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == [] and store.writes == 0


@pytest.mark.parametrize("status", ["ready", "queued", "building", "deploying"])
def test_job_opt_in_never_retires_active_or_nonterminal_status(harness, status):
    controller, store, engine = harness
    store.row["result"]["execution_mode"] = "job"
    store.row["status"] = status
    store.retention["retire_terminal_evidence"] = True
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == []


@pytest.mark.parametrize("protection", ["reference", "pinned"])
def test_opted_in_job_does_not_bypass_current_references_or_pins(harness, protection):
    controller, store, engine = harness
    store.row["result"]["execution_mode"] = "job"
    store.retention["retire_terminal_evidence"] = True
    if protection == "reference":store.protected = True
    else:store.retention["pinned"] = True
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == [] and store.writes == 0


def test_unknown_execution_mode_remains_blocked_with_opt_in(harness):
    controller, store, engine = harness
    store.row["result"]["execution_mode"] = "unknown"
    store.retention["retire_terminal_evidence"] = True
    assert controller.reconcile_retention_runtime_containers() == 0
    assert engine.removed == []
