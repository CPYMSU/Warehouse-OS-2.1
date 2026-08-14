from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import database_release, deployment_acceptance, workspace_deployments
from app.services.digital_asset_hosting import WorkspaceCredential


def _credential() -> WorkspaceCredential:
    return WorkspaceCredential(
        tenant_id=UUID("00000000-0000-0000-0000-000000000101"),
        workspace_id=UUID("00000000-0000-0000-0000-000000000102"),
        credential_id=UUID("00000000-0000-0000-0000-000000000103"),
        scopes=frozenset({"deploy:write"}),
        label="deployment-safety-test",
        key_kind="primary",
        parent_credential_id=None,
    )


def test_static_candidate_acceptance_uses_immutable_release_files(tmp_path: Path) -> None:
    release = tmp_path / "tenants" / "tenant" / "releases" / "candidate" / "source"
    course = release / "learn" / "line-stringing"
    course.mkdir(parents=True)
    (release / "index.html").write_text("<main>Catalog</main>", encoding="utf-8")
    (course / "index.html").write_text("<main>Course</main>", encoding="utf-8")
    settings = Settings(hosted_runtime_data_root=tmp_path)
    result = {
        "runtime_kind": "static",
        "runtime_rel_path": str(release.relative_to(tmp_path)),
    }

    root = deployment_acceptance._static_candidate_root(result, settings)
    evidence, failures = deployment_acceptance._static_acceptance(
        root,
        [
            {
                "name": "course",
                "path": "/learn/line-stringing/",
                "expected_status": 200,
                "operator": "status_only",
            }
        ],
    )

    assert failures == []
    assert evidence == [
        {
            "name": "course",
            "path": "/learn/line-stringing/",
            "status": 200,
            "content_type": "text/html",
            "accepted": True,
        }
    ]


def test_static_candidate_acceptance_always_probes_the_root(tmp_path: Path) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "index.html").write_text("<main>Ready</main>", encoding="utf-8")

    evidence, failures = deployment_acceptance._static_acceptance(release, [])

    assert failures == []
    assert evidence[0]["name"] == "static-root"
    assert evidence[0]["accepted"] is True


def test_static_candidate_root_rejects_an_escaping_release_path(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside-release"
    outside.mkdir(exist_ok=True)
    (outside / "index.html").write_text("unsafe", encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe_release_path"):
        deployment_acceptance._static_candidate_root(
            {"runtime_rel_path": "../outside-release"},
            Settings(hosted_runtime_data_root=tmp_path),
        )


def test_static_deployment_acceptance_does_not_require_an_internal_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    release = tmp_path / "release"
    release.mkdir()
    (release / "index.html").write_text("<main>Ready</main>", encoding="utf-8")
    candidate_id = UUID("00000000-0000-0000-0000-000000000104")
    source_id = UUID("00000000-0000-0000-0000-000000000106")
    candidate = {
        "id": candidate_id,
        "status": "ready",
        "health": "healthy",
        "source_version_id": source_id,
        "request_digest": "request-digest",
        "requested_config": {
            "compatibility_contract": {
                "schema": "warehouse.hosting-application.v2.3",
                "contract_digest": "contract-digest",
                "lifecycle": {"jobs": []},
                "acceptance": {
                    "http": [],
                    "database": {"counts": []},
                },
            },
        },
        "result": {
            "runtime_kind": "static",
            "execution_mode": "service",
            "runtime_rel_path": "release",
        },
    }

    class _Result:
        def __init__(
            self,
            *,
            mapping: dict[str, object] | None = None,
            rows: list[dict[str, object]] | None = None,
            scalar: object = None,
        ) -> None:
            self.mapping = mapping
            self.rows = rows or []
            self.scalar = scalar

        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object] | None:
            return self.mapping

        def scalar_one(self) -> object:
            return self.scalar

        def __iter__(self):
            return iter(self.rows)

    class _Session:
        def execute(
            self,
            statement: object,
            _parameters: dict[str, object] | None = None,
        ) -> _Result:
            sql = str(statement)
            if "SELECT * FROM digital_asset.deployments" in sql:
                return _Result(mapping=candidate)
            if "SELECT id,status,health,requested_config" in sql:
                return _Result(rows=[])
            if "SELECT COALESCE(max(sequence),0)+1" in sql:
                return _Result(scalar=2)
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(deployment_acceptance, "tenant_session", fake_tenant_session)

    accepted = deployment_acceptance.accept_workspace_deployment(
        _credential(),
        candidate_id,
        Settings(hosted_runtime_data_root=tmp_path),
    )

    assert accepted["accepted"] is True
    assert accepted["evidence"]["candidate_transport"] == "immutable_static_release"
    assert accepted["evidence"]["http"][0]["name"] == "static-root"


def test_candidate_acceptance_requests_runtime_wake_before_private_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000104")
    statements: list[str] = []

    class _Result:
        def __init__(self, value: object) -> None:
            self.value = value

        def scalar_one_or_none(self) -> object:
            return self.value

        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> object:
            return self.value

    class _Session:
        def execute(
            self,
            statement: object,
            _parameters: dict[str, object] | None = None,
        ) -> _Result:
            sql = str(statement)
            statements.append(sql)
            if "UPDATE digital_asset.deployments" in sql:
                return _Result("wake_requested")
            return _Result({"runtime_state": "running", "runtime_wake_error": None})

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(deployment_acceptance, "tenant_session", fake_tenant_session)

    deployment_acceptance._ensure_candidate_runtime_running(
        _credential(),
        deployment_id,
        Settings(runtime_wake_timeout_seconds=1),
    )

    assert "SET runtime_state='wake_requested'" in statements[0]
    assert any("SELECT runtime_state,runtime_wake_error" in sql for sql in statements)


class _ScalarResult:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one_or_none(self) -> object:
        return self.value


def test_database_gate_ignores_workspace_history_for_database_free_release() -> None:
    class _Session:
        def execute(self, statement: object, _parameters: object = None) -> _ScalarResult:
            assert "SELECT config FROM digital_asset.workspaces" in str(statement)
            return _ScalarResult({"database_policy": {"mode": "platform_managed"}})

    observed = database_release.observe_database_release_gate(
        _Session(),
        UUID("00000000-0000-0000-0000-000000000102"),
        deployment_config={
            "database_access": "none",
            "compatibility_contract": {
                "acceptance": {"database": {"counts": []}},
            },
        },
    )

    assert observed["ready"] is True
    assert observed["required"] is False
    assert observed["reason"] == "deployment_declares_no_database_access"


def test_database_gate_uses_current_v23_lifecycle_instead_of_fabric_history() -> None:
    source_id = "00000000-0000-0000-0000-000000000106"
    job_id = UUID("00000000-0000-0000-0000-000000000107")
    statements: list[str] = []

    class _Result:
        def __init__(
            self,
            *,
            scalar: object = None,
            mapping: dict[str, object] | None = None,
            rows: list[dict[str, object]] | None = None,
        ) -> None:
            self.scalar = scalar
            self.mapping = mapping
            self.rows = rows or []

        def scalar_one_or_none(self) -> object:
            return self.scalar

        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object] | None:
            return self.mapping

        def __iter__(self):
            return iter(self.rows)

    class _Session:
        def execute(
            self,
            statement: object,
            parameters: dict[str, object] | None = None,
        ) -> _Result:
            sql = str(statement)
            statements.append(sql)
            if "SELECT config FROM digital_asset.workspaces" in sql:
                return _Result(scalar={"database_policy": {"mode": "platform_managed"}})
            if "FROM digital_asset.database_bindings" in sql:
                return _Result(
                    mapping={
                        "id": UUID("00000000-0000-0000-0000-000000000108"),
                        "status": "ready",
                        "provider_key": "postgresql",
                        "capabilities": {"vector_extension": True},
                        "config": {},
                    }
                )
            if "FROM digital_asset.deployments" in sql:
                assert parameters is not None
                assert parameters["source_version_id"] == source_id
                return _Result(
                    rows=[
                        {
                            "id": job_id,
                            "status": "ready",
                            "health": "healthy",
                            "requested_config": {
                                "lifecycle_job": {
                                    "name": "migrate",
                                    "contract_digest": "current-contract",
                                }
                            },
                        }
                    ]
                )
            if "FROM digital_asset.database_backups" in sql:
                return _Result(
                    mapping={
                        "id": UUID("00000000-0000-0000-0000-000000000109"),
                        "sha256": "a" * 64,
                        "metadata": {
                            "checksum_verified": True,
                            "restore_verified": True,
                        },
                        "completed_at": None,
                    }
                )
            raise AssertionError(sql)

    observed = database_release.observe_database_release_gate(
        _Session(),
        UUID("00000000-0000-0000-0000-000000000102"),
        deployment_config={
            "source_version_id": source_id,
            "database_access": "runtime",
            "compatibility_contract": {
                "schema": "warehouse.hosting-application.v2.3",
                "contract_digest": "current-contract",
                "lifecycle": {
                    "jobs": [
                        {
                            "name": "migrate",
                            "database_access": "migration",
                            "required_before_activation": True,
                        }
                    ]
                },
                "acceptance": {"database": {"counts": []}},
            },
        },
    )

    assert observed["ready"] is True
    assert observed["migration_evidence_source"] == "deployment_lifecycle"
    assert observed["migrations"][0]["deployment_id"] == str(job_id)
    assert not any("digital_asset.hosting_resources" in sql for sql in statements)


def test_verified_application_url_requires_public_route_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workspace_deployments, "_public_deployment", lambda row: dict(row))
    row = {
        "status": "ready",
        "health": "healthy",
        "public_url": "https://bonfirework.org/assets/acme/example/",
        "result": {"public_route_verified": False},
    }

    staged = workspace_deployments._deployment_public(row)
    verified = workspace_deployments._deployment_public(
        {**row, "result": {"public_route_verified": True}}
    )

    assert staged["verified_application_url"] is None
    assert verified["verified_application_url"] == row["public_url"]


def test_public_route_probe_requires_the_exact_deployment_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000104")

    def fake_get(*_args: object, **_kwargs: object) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"X-Warehouse-Deployment": str(deployment_id)},
        )

    monkeypatch.setattr(workspace_deployments.httpx, "get", fake_get)

    evidence = workspace_deployments._verify_public_deployment_route(
        "https://bonfirework.org/assets/acme/example/",
        deployment_id,
        "/",
    )

    assert evidence["deployment_id"] == str(deployment_id)
    assert evidence["status"] == 200


class _ActivationResult:
    def __init__(self, *, mapping: dict[str, object] | None = None, scalar: object = None):
        self.mapping = mapping
        self.scalar = scalar

    def mappings(self) -> _ActivationResult:
        return self

    def one_or_none(self) -> dict[str, object] | None:
        return self.mapping

    def one(self) -> dict[str, object]:
        assert self.mapping is not None
        return self.mapping

    def scalar_one(self) -> object:
        return self.scalar


class _ActivationSession:
    def __init__(
        self,
        state: dict[str, object],
        deployment: dict[str, object],
    ) -> None:
        self.state = state
        self.deployment = deployment
        self.statements: list[str] = []

    def execute(
        self,
        statement: object,
        parameters: dict[str, object] | None = None,
    ) -> _ActivationResult:
        sql = str(statement)
        self.statements.append(sql)
        parameters = parameters or {}
        if "SELECT active_deployment_id FROM digital_asset.workspaces" in sql:
            return _ActivationResult(scalar=self.state["active"])
        if "SELECT * FROM digital_asset.deployments" in sql:
            return _ActivationResult(mapping=self.deployment)
        if "UPDATE digital_asset.workspaces" in sql:
            if "CAST(:previous AS uuid)" in sql:
                self.state["active"] = parameters["previous"]
            elif "deployment_id" in parameters:
                self.state["active"] = parameters["deployment_id"]
            return _ActivationResult()
        if "UPDATE digital_asset.deployments" in sql and "RETURNING *" in sql:
            updated = {
                **self.deployment,
                "result": {
                    **dict(self.deployment["result"]),
                    "public_route_verified": True,
                },
            }
            return _ActivationResult(mapping=updated)
        if "SELECT COALESCE(max(sequence),0)+1" in sql:
            return _ActivationResult(scalar=4)
        return _ActivationResult()


def _activation_fixture() -> tuple[dict[str, object], dict[str, object], UUID, UUID]:
    previous = UUID("00000000-0000-0000-0000-000000000105")
    candidate = UUID("00000000-0000-0000-0000-000000000104")
    state: dict[str, object] = {"active": previous}
    deployment = {
        "id": candidate,
        "legacy_id": 104,
        "status": "ready",
        "health": "healthy",
        "public_url": "https://bonfirework.org/assets/acme/example/",
        "source_version_id": UUID("00000000-0000-0000-0000-000000000106"),
        "requested_config": {
            "database_access": "none",
            "health_path": "/",
            "compatibility_contract": {
                "deployment": {"require_acceptance_before_activation": False},
            },
        },
        "result": {"runtime_kind": "static", "health_path": "/"},
    }
    return state, deployment, previous, candidate


def test_activation_marks_route_verified_only_after_exact_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, deployment, _previous, candidate = _activation_fixture()
    session = _ActivationSession(state, deployment)

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield session

    monkeypatch.setattr(workspace_deployments, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        workspace_deployments,
        "observe_database_release_gate",
        lambda *_args, **_kwargs: {"required": False, "ready": True},
    )
    monkeypatch.setattr(
        workspace_deployments,
        "mark_pages_deployment_active",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        workspace_deployments,
        "_verify_public_deployment_route",
        lambda *_args, **_kwargs: {"status": 200, "deployment_id": str(candidate)},
    )
    monkeypatch.setattr(workspace_deployments, "_deployment_public", lambda value: value)

    result = workspace_deployments.activate_workspace_deployment(_credential(), candidate)

    assert state["active"] == candidate
    assert result["active"] is True
    assert result["deployment"]["result"]["public_route_verified"] is True


def test_activation_restores_previous_pointer_when_public_probe_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, deployment, previous, candidate = _activation_fixture()
    session = _ActivationSession(state, deployment)
    restored: list[object] = []

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield session

    monkeypatch.setattr(workspace_deployments, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        workspace_deployments,
        "observe_database_release_gate",
        lambda *_args, **_kwargs: {"required": False, "ready": True},
    )
    monkeypatch.setattr(
        workspace_deployments,
        "mark_pages_deployment_active",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(
        workspace_deployments,
        "set_pages_deployment_pointer",
        lambda *_args, **kwargs: restored.append(kwargs["deployment_id"]),
    )
    monkeypatch.setattr(
        workspace_deployments,
        "_verify_public_deployment_route",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("wrong deployment")),
    )

    with pytest.raises(HTTPException) as raised:
        workspace_deployments.activate_workspace_deployment(_credential(), candidate)

    assert raised.value.status_code == 409
    assert raised.value.detail["previous_deployment_restored"] is True
    assert state["active"] == str(previous)
    assert restored == [previous]
