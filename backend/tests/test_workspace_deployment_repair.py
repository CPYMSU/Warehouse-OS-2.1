from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.services import workspace_deployments
from app.services.digital_asset_hosting import WorkspaceCredential


def _credential(*scopes: str) -> WorkspaceCredential:
    return WorkspaceCredential(
        tenant_id=UUID("00000000-0000-0000-0000-000000000101"),
        workspace_id=UUID("00000000-0000-0000-0000-000000000102"),
        credential_id=UUID("00000000-0000-0000-0000-000000000103"),
        scopes=frozenset(scopes),
        label="repair-test",
        key_kind="primary",
        parent_credential_id=None,
    )


def test_workspace_repair_requires_deploy_write_scope() -> None:
    with pytest.raises(HTTPException) as raised:
        workspace_deployments.repair_workspace_deployment(
            _credential("deploy:read"),
            UUID("00000000-0000-0000-0000-000000000104"),
        )

    assert raised.value.status_code == 403


def test_workspace_repair_requeues_active_ready_deployment_with_audit_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000104")
    row = {
        "id": deployment_id,
        "legacy_id": 104,
        "workspace_id": _credential("deploy:write").workspace_id,
        "status": "ready",
        "health": "healthy",
        "provider_key": "warehouse_runtime_v1",
        "result": {},
    }
    executed: list[tuple[str, dict[str, object] | None]] = []

    class _Result:
        def __init__(self, *, mapping: dict[str, object] | None = None, scalar: object = None):
            self.mapping = mapping
            self.scalar = scalar

        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object] | None:
            return self.mapping

        def one(self) -> dict[str, object]:
            assert self.mapping is not None
            return self.mapping

        def scalar_one(self) -> object:
            return self.scalar

    class _Session:
        def execute(
            self,
            statement: object,
            parameters: dict[str, object] | None = None,
        ) -> _Result:
            sql = str(statement)
            executed.append((sql, parameters))
            if "SELECT * FROM digital_asset.deployments" in sql:
                return _Result(mapping=row)
            if "SELECT EXISTS" in sql:
                return _Result(scalar=True)
            if "UPDATE digital_asset.deployments" in sql and "RETURNING *" in sql:
                return _Result(mapping={**row, "status": "queued", "health": "pending"})
            if "SELECT COALESCE(max(sequence),0)+1" in sql:
                return _Result(scalar=7)
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(workspace_deployments, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(workspace_deployments, "_deployment_public", lambda value: value)

    result = workspace_deployments.repair_workspace_deployment(
        _credential("deploy:write"),
        deployment_id,
        {"source": "ai_secretary", "reason": "container health drift"},
    )

    assert result["accepted"] is True
    assert result["deployment"]["status"] == "queued"
    assert result["repair_contract"] == {
        "execution": "asynchronous",
        "required_scope": "deploy:write",
        "source": "ai_secretary",
        "automatic_runtime_reconciliation": True,
    }
    event_parameters = next(
        parameters
        for sql, parameters in executed
        if "'repair_requested'" in sql and parameters is not None
    )
    assert event_parameters["sequence"] == 7
    assert '"source": "ai_secretary"' in str(event_parameters["payload"])


def test_workspace_repair_is_idempotent_while_already_queued(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000105")
    row = {
        "id": deployment_id,
        "legacy_id": 105,
        "status": "queued",
        "health": "pending",
        "provider_key": "runtime_queue",
        "result": {},
    }
    statements: list[str] = []

    class _Result:
        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object]:
            return row

    class _Session:
        def execute(self, statement: object, *_args: object, **_kwargs: object) -> _Result:
            statements.append(str(statement))
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(workspace_deployments, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(workspace_deployments, "_deployment_public", lambda value: value)

    result = workspace_deployments.repair_workspace_deployment(
        _credential("deploy:write"),
        deployment_id,
    )

    assert result["accepted"] is False
    assert result["next_action"] == "observe_deployment"
    assert len(statements) == 1
