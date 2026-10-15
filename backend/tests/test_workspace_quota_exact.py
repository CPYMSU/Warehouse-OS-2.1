from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import workspace_autonomy as service
from app.services import workspace_autonomy_base as base

MIB = 1024 * 1024
STEP = 512 * MIB
CURRENT = 5 * STEP
TARGET = 6 * STEP


@pytest.fixture
def quota(monkeypatch):
    """Transaction-aware fake; no database, host files, or credentials are used."""

    credential = base.WorkspaceCredential(
        tenant_id=UUID(int=1),
        workspace_id=UUID(int=2),
        credential_id=UUID(int=3),
        scopes=frozenset({"infra:write"}),
        label="synthetic quota test",
        key_kind="primary",
        parent_credential_id=None,
    )
    state = {
        "workspace": {
            "id": credential.workspace_id,
            "asset_id": UUID(int=4),
            "workspace_key": "synthetic-quota",
            "storage_quota_bytes": CURRENT,
            "revision": 7,
        },
        "audits": [],
    }
    observations = [CURRENT - 100 * MIB]
    calls = []

    class Result:
        def mappings(self):
            return self

        def one(self):
            return dict(state["workspace"])

    class Session:
        locked = False

        def execute(self, query, params):
            assert self.locked
            assert "UPDATE digital_asset.workspaces" in str(query)
            assert params["id"] == credential.workspace_id
            calls.append(("update", self, params["target"]))
            state["workspace"]["storage_quota_bytes"] = params["target"]
            state["workspace"]["revision"] += 1
            return Result()

    @contextmanager
    def transaction(tenant_id):
        assert tenant_id == credential.tenant_id
        snapshot = deepcopy(state)
        session = Session()
        calls.append(("transaction", session))
        try:
            yield session
        except Exception:
            state.clear()
            state.update(snapshot)
            raise

    def workspace(session, workspace_id, *, lock=False):
        assert workspace_id == credential.workspace_id
        session.locked = lock
        calls.append(("workspace", session, lock))
        return dict(state["workspace"])

    def usage(session, **kwargs):
        assert kwargs["tenant_id"] == credential.tenant_id
        assert kwargs["workspace_id"] == credential.workspace_id
        calls.append(("usage", session, session.locked))
        value = observations.pop(0) if len(observations) > 1 else observations[0]
        return {"total_bytes": value}

    def audit(session, actor, event, payload, *, tenant_id):
        assert session.locked
        assert actor is None
        assert tenant_id == credential.tenant_id
        assert event == "digital_asset.workspace_quota_elastic_increase"
        calls.append(("audit", session))
        state["audits"].append(deepcopy(payload))

    monkeypatch.setattr(service, "tenant_session", transaction)
    monkeypatch.setattr(base, "tenant_session", transaction)
    monkeypatch.setattr(base, "_workspace_row", workspace)
    monkeypatch.setattr(base, "_workspace_billable_usage", usage)
    monkeypatch.setattr(base, "_audit", audit)
    return credential, state, observations, calls


@pytest.mark.parametrize("change", [1, 196608, 80 * MIB, -196608, -600 * MIB])
def test_absolute_target_does_not_drift_with_usage(quota, change):
    credential, state, observations, calls = quota
    initial_usage = CURRENT - 100 * MIB
    observations[:] = [initial_usage, initial_usage + change]

    result = service.resize_capacity(
        credential, {"target_mb": 3072, "expected_revision": 7}
    )

    assert result["quota_bytes"] == TARGET
    assert result["allocation_units_added"] == 1
    assert state["workspace"]["storage_quota_bytes"] == TARGET
    assert len([call for call in calls if call[0] == "transaction"]) == 1
    assert [call[2] for call in calls if call[0] == "workspace"] == [True]
    assert [call[2] for call in calls if call[0] == "usage"] == [True]
    assert len({id(call[1]) for call in calls}) == 1


def test_usage_exceeding_requested_target_does_not_authorize_extra_capacity(quota):
    credential, state, observations, _calls = quota
    observations[:] = [TARGET + 1]
    result = service.resize_capacity(
        credential, {"target_bytes": TARGET, "expected_revision": 7}
    )
    assert result["quota_bytes"] == TARGET
    assert result["remaining_bytes"] == 0
    assert result["used_bytes"] == TARGET + 1
    assert state["audits"][0]["after_bytes"] == TARGET


def test_exact_target_retry_with_old_revision_is_noop_and_not_double_audited(quota):
    credential, state, _observations, calls = quota
    request = {"target_mb": 3072, "expected_revision": 7}
    first = service.resize_capacity(credential, request)
    second = service.resize_capacity(credential, request)
    assert first["changed"] is True
    assert second["changed"] is False
    assert second["target_already_satisfied"] is True
    assert second["allocation_units_added"] == 0
    assert first["revision"] == second["revision"] == 8
    assert first["quota_bytes"] == second["quota_bytes"] == TARGET
    assert len(state["audits"]) == 1
    assert len([call for call in calls if call[0] == "update"]) == 1


def test_different_target_with_stale_revision_conflicts_before_measurement(quota):
    credential, state, _observations, calls = quota
    state["workspace"]["revision"] = 8
    with pytest.raises(HTTPException) as caught:
        service.resize_capacity(credential, {"target_mb": 3072, "expected_revision": 7})
    assert caught.value.status_code == 409
    assert caught.value.detail["current_revision"] == 8
    assert state["workspace"]["storage_quota_bytes"] == CURRENT
    assert not state["audits"]
    assert not any(call[0] in {"usage", "update"} for call in calls)


def test_target_smaller_than_current_is_never_reported_as_retry_success(quota):
    credential, state, _observations, _calls = quota
    state["workspace"]["storage_quota_bytes"] = TARGET + STEP
    state["workspace"]["revision"] = 9
    with pytest.raises(HTTPException) as caught:
        service.resize_capacity(credential, {"target_mb": 3072, "expected_revision": 7})
    assert caught.value.status_code == 422
    assert state["workspace"]["storage_quota_bytes"] == TARGET + STEP
    assert not state["audits"]


@pytest.mark.parametrize("payload", [
    {"target_mb": "3072", "expected_revision": "7"},
    {"target_bytes": str(TARGET), "expected_revision": 7},
    {"target_mb": 3072},
])
def test_exact_target_accepts_documented_units_and_optional_revision(quota, payload):
    credential, state, _observations, _calls = quota
    result = service.resize_capacity(credential, payload)
    assert result["quota_bytes"] == TARGET
    assert state["audits"][0]["requested_target_bytes"] == TARGET


def test_explicit_multiple_allocation_units_remain_supported(quota):
    credential, state, _observations, _calls = quota
    result = service.resize_capacity(
        credential, {"target_mb": 4096, "expected_revision": 7}
    )
    assert result["quota_bytes"] == 4096 * MIB
    assert result["allocation_units_added"] == 3
    assert state["audits"][0]["allocation_units_added"] == 3


@pytest.mark.parametrize("payload", [
    {"target_mb": True},
    {"target_mb": 3072.9},
    {"target_mb": -1},
    {"target_mb": "3072.0"},
    {"target_mb": []},
    {"target_mb": 3073},
    {"target_bytes": TARGET + 1},
    {"target_bytes": 1 << 63},
    {"target_mb": 1 << 63},
    {"target_mb": 3072, "expected_revision": True},
    {"target_mb": 3072, "expected_revision": 7.2},
    {"target_mb": 3072, "expected_revision": -1},
    {"target_mb": 3072, "expected_revision": "wrong"},
    {"target_mb": 3072, "target_bytes": TARGET},
    {"target_mb": 3072, "delta_mb": 512},
    {},
])
def test_invalid_or_ambiguous_requests_do_not_change_quota(quota, payload):
    credential, state, _observations, calls = quota
    with pytest.raises(HTTPException) as caught:
        service.resize_capacity(credential, payload)
    assert caught.value.status_code == 422
    assert state["workspace"]["storage_quota_bytes"] == CURRENT
    assert state["workspace"]["revision"] == 7
    assert not state["audits"]
    assert not any(call[0] == "update" for call in calls)


@pytest.mark.parametrize("field", ["additional_mb", "delta_mb"])
def test_additional_mode_retains_multiple_unit_elastic_behavior(quota, field):
    credential, state, _observations, _calls = quota
    result = service.resize_capacity(credential, {field: 1024, "expected_revision": 7})
    assert result["quota_bytes"] == CURRENT + 1024 * MIB
    assert result["allocation_units_added"] == 2
    assert state["audits"][0]["after_bytes"] == CURRENT + 1024 * MIB


def test_minimum_free_mode_retains_free_space_rounding(quota):
    credential, _state, observations, _calls = quota
    observations[:] = [CURRENT - 100 * MIB]
    result = service.resize_capacity(
        credential, {"minimum_free_mb": 800, "expected_revision": 7}
    )
    assert result["quota_bytes"] == CURRENT + 2 * STEP
    assert result["remaining_bytes"] >= 800 * MIB


def test_automatic_capacity_function_is_unchanged():
    assert service.ensure_capacity is base.ensure_capacity


@pytest.mark.parametrize("kind,scopes", [
    ("delegated", frozenset({"infra:write"})),
    ("primary", frozenset({"infra:read"})),
])
def test_resize_requires_primary_and_infra_write_before_database_access(quota, kind, scopes):
    credential, state, _observations, calls = quota
    restricted = base.WorkspaceCredential(
        tenant_id=credential.tenant_id,
        workspace_id=credential.workspace_id,
        credential_id=credential.credential_id,
        scopes=scopes,
        label=credential.label,
        key_kind=kind,
        parent_credential_id=None,
    )
    with pytest.raises(HTTPException) as caught:
        service.resize_capacity(restricted, {"target_mb": 3072, "expected_revision": 7})
    assert caught.value.status_code == 403
    assert calls == []
    assert not state["audits"]


def test_audit_and_resize_use_one_transaction_and_roll_back_together(quota, monkeypatch):
    credential, state, _observations, _calls = quota

    def audit_failure(*args, **kwargs):
        raise RuntimeError("synthetic audit insertion failure")

    monkeypatch.setattr(base, "_audit", audit_failure)
    with pytest.raises(RuntimeError, match="audit insertion failure"):
        service.resize_capacity(credential, {"target_mb": 3072, "expected_revision": 7})
    assert state["workspace"]["storage_quota_bytes"] == CURRENT
    assert state["workspace"]["revision"] == 7
    assert state["audits"] == []
