from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from uuid import UUID

import httpx
import pytest
import uvicorn

from app import runtime_controller
from app.core.config import Settings
from app.runtime_controller import DockerEngine, _python_api_launcher_source


class _FakeDockerClient:
    def __init__(self, responses: list[httpx.Response]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, str, dict[str, object]]] = []
        self.closed = False

    def _next(self, method: str, path: str, **kwargs: object) -> httpx.Response:
        self.requests.append((method, path, kwargs))
        return self.responses.pop(0)

    def get(self, path: str, **kwargs: object) -> httpx.Response:
        return self._next("GET", path, **kwargs)

    def post(self, path: str, **kwargs: object) -> httpx.Response:
        return self._next("POST", path, **kwargs)

    def delete(self, path: str, **kwargs: object) -> httpx.Response:
        return self._next("DELETE", path, **kwargs)

    def close(self) -> None:
        self.closed = True


def _response(
    status: int,
    *,
    json: object | None = None,
    text: str = "",
) -> httpx.Response:
    request = httpx.Request("GET", "http://docker/test")
    if json is not None:
        return httpx.Response(status, request=request, json=json)
    return httpx.Response(status, request=request, text=text)


def test_docker_engine_negotiates_server_api_for_every_container_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53", "MinAPIVersion": "1.44"}),
            _response(404),
            _response(201, json={"Id": "container-1"}),
            _response(204),
            _response(200, json={"State": {"Running": True, "Status": "running"}}),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))
    engine.remove("runtime-1")
    assert engine.create(name="runtime-1", spec={"Image": "python:3.12"}) == "container-1"
    engine.start("runtime-1")
    assert engine.state("runtime-1")["running"] is True
    engine.close()

    assert [path for _, path, _ in fake.requests] == [
        "/version",
        "/v1.53/containers/runtime-1",
        "/v1.53/containers/create",
        "/v1.53/containers/runtime-1/start",
        "/v1.53/containers/runtime-1/json",
    ]
    assert fake.closed is True


def test_docker_engine_stops_container_without_removing_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(204),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))
    engine.stop("runtime-1", timeout=7)

    assert fake.requests[-1] == (
        "POST",
        "/v1.53/containers/runtime-1/stop",
        {"params": {"t": "7"}},
    )


def test_docker_engine_error_includes_sanitized_daemon_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.44"}),
            _response(
                400,
                text="client version 1.43 is too old\nminimum supported version is 1.44\x00",
            ),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))
    with pytest.raises(RuntimeError) as raised:
        engine.remove("runtime-2")

    assert str(raised.value) == (
        "Docker Engine container cleanup failed: HTTP 400 · "
        "client version 1.43 is too old minimum supported version is 1.44"
    )


def test_docker_engine_rejects_missing_negotiated_version(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient([_response(200, json={"Version": "29.2.1"})])
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    with pytest.raises(RuntimeError, match="no usable version"):
        DockerEngine(Path("/var/run/docker.sock"))


def test_docker_engine_waits_for_one_shot_builder_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(200, json={"StatusCode": 0}),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))

    assert engine.wait("runtime-builder", timeout=321) == 0
    assert fake.requests[-1] == (
        "POST",
        "/v1.53/containers/runtime-builder/wait",
        {"params": {"condition": "not-running"}, "timeout": 321},
    )


def test_docker_engine_distinguishes_missing_managed_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(404),
            _response(200, json={"State": {"Running": True}}),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))

    assert engine.container_exists("warehouse-runtime-missing") is False
    assert engine.container_exists("warehouse-runtime-present") is True


def test_docker_engine_lists_only_managed_runtime_containers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(
                200,
                json=[
                    {
                        "Names": ["/warehouse-runtime-active"],
                        "State": "running",
                        "Labels": {
                            "org.bonfirework.managed": "runtime-controller",
                            "org.bonfirework.deployment": "deployment-1",
                            "org.bonfirework.workspace": "workspace-1",
                        },
                    },
                    {
                        "Names": ["/unrelated-container"],
                        "State": "running",
                        "Labels": {
                            "org.bonfirework.managed": "runtime-controller",
                        },
                    },
                ],
            ),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))

    assert engine.managed_runtime_containers() == [
        {
            "name": "warehouse-runtime-active",
            "deployment_id": "deployment-1",
            "workspace_id": "workspace-1",
            "running": True,
        }
    ]
    assert fake.requests[-1][2]["params"] == {
        "all": "true",
        "filters": '{"label":["org.bonfirework.managed=runtime-controller"]}',
    }


def test_docker_engine_reads_one_shot_cpu_and_memory_statistics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(
                200,
                json={
                    "cpu_stats": {
                        "cpu_usage": {"total_usage": 300},
                        "system_cpu_usage": 1400,
                        "online_cpus": 2,
                    },
                    "precpu_stats": {
                        "cpu_usage": {"total_usage": 100},
                        "system_cpu_usage": 1000,
                    },
                    "memory_stats": {"usage": 256, "limit": 1024},
                },
            ),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))
    assert engine.stats("runtime-1") == {
        "cpu_percent": 100.0,
        "memory_percent": 25.0,
    }
    assert fake.requests[-1][2]["params"] == {
        "stream": "false",
        "one-shot": "true",
    }


def test_docker_engine_builds_create_safe_compose_replica_spec(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeDockerClient(
        [
            _response(200, json={"ApiVersion": "1.53"}),
            _response(
                200,
                json={
                    "Id": "runtime-id",
                    "Config": {
                        "Image": "example/api:1",
                        "Env": ["TOKEN=runtime-only"],
                        "Cmd": ["python", "app.py"],
                        "WorkingDir": "/workspace/app",
                        "Labels": {"org.bonfirework.managed": "runtime-controller"},
                        "Hostname": "runtime-id",
                    },
                    "HostConfig": {
                        "Binds": ["/host/data:/workspace/data:rw"],
                        "NetworkMode": "warehouse-os_default",
                        "ReadonlyRootfs": True,
                        "Memory": 536870912,
                        "PortBindings": {"8080/tcp": [{"HostPort": "12345"}]},
                    },
                    "NetworkSettings": {"IPAddress": "172.18.0.10"},
                },
            ),
        ]
    )
    monkeypatch.setattr(runtime_controller.httpx, "Client", lambda **kwargs: fake)

    engine = DockerEngine(Path("/var/run/docker.sock"))
    spec = engine.replica_spec("runtime-api-0", network_alias="api")

    assert spec["Image"] == "example/api:1"
    assert spec["Env"] == ["TOKEN=runtime-only"]
    assert "Hostname" not in spec
    assert "PortBindings" not in spec["HostConfig"]
    assert spec["NetworkingConfig"] == {
        "EndpointsConfig": {"warehouse-os_default": {"Aliases": ["api"]}}
    }


def test_runtime_container_receives_workspace_environment_without_persisting_it() -> None:
    controller = runtime_controller.RuntimeController(Settings())
    _, spec, _, _ = controller._container_spec(
        {
            "id": "00000000-0000-0000-0000-000000000011",
            "workspace_id": "00000000-0000-0000-0000-000000000012",
            "runtime_family": "python",
            "component_kind": "backend",
            "entrypoint": "services/ai-orchestrator/src/auto_runtime/app.py",
            "execution_contract": {"port": 8080, "health_path": "/health"},
            "resource_limits": {},
            "requested_config": {},
            "image_ref": "python:3.12",
            "runtime_environment": {
                "DATABASE_URL": "postgresql://workspace:secret@hosted-postgres/app",
                "WAREHOUSE_RUNTIME_SECRET": "stable-secret",
            },
        },
        Path("/host/app"),
        Path("/host/data"),
    )

    assert spec["Env"] == [
        "PORT=8080",
        "HOST=0.0.0.0",
        "PYTHONDONTWRITEBYTECODE=1",
        "WAREHOUSE_DATA_DIR=/workspace/data",
        "WAREHOUSE_APPLICATION_ROOT=/workspace/app",
        "WAREHOUSE_ENTRYPOINT=services/ai-orchestrator/src/auto_runtime/app.py",
        "DATABASE_URL=postgresql://workspace:secret@hosted-postgres/app",
        "WAREHOUSE_RUNTIME_SECRET=stable-secret",
    ]
    command = spec["Cmd"][-1]
    assert "pip install --no-cache-dir --upgrade --target" in command
    assert "/workspace/data/.runtime/python/" in command
    assert 'RUNTIME_BUILD_ROOT="$(mktemp -d)"' in command
    assert 'cp -a . "$RUNTIME_BUILD_ROOT/source"' in command
    assert "exec python -c" in command
    assert "itertools.takewhile" in command


def test_managed_python_build_activates_artifact_venv_and_src_layout() -> None:
    controller = runtime_controller.RuntimeController(Settings())
    _, spec, _, _ = controller._container_spec(
        {
            "id": "00000000-0000-0000-0000-000000000031",
            "workspace_id": "00000000-0000-0000-0000-000000000032",
            "runtime_family": "python",
            "component_kind": "backend",
            "entrypoint": "src/mk7_platform/api/main.py",
            "execution_contract": {"port": 8080, "health_path": "/healthz"},
            "resource_limits": {},
            "requested_config": {
                "build_command": "python -m pip install -r requirements.hosting.txt",
                "start_command": ("uvicorn mk7_platform.api.main:app --host 0.0.0.0 --port $PORT"),
            },
            "image_ref": "python:3.12",
            "runtime_environment": {},
            "managed_build": True,
            "managed_build_digest": "a" * 64,
            "managed_build_src_layout": True,
        },
        Path("/host/build"),
        Path("/host/data"),
    )

    command = spec["Cmd"][-1]
    assert "VIRTUAL_ENV=/workspace/data/.runtime/python/" in command
    assert command.count("/venv") >= 1
    assert 'PATH="$VIRTUAL_ENV/bin:$PATH"' in command
    assert 'PYTHONPATH="/workspace/app/src${PYTHONPATH:+:$PYTHONPATH}"' in command
    assert "uvicorn mk7_platform.api.main:app" in command
    assert "pip install -r requirements.hosting.txt" not in command
    assert "WAREHOUSE_ENTRYPOINT=src/mk7_platform/api/main.py" in spec["Env"]


def test_node_explicit_start_command_is_not_replaced_by_automatic_launcher() -> None:
    controller = runtime_controller.RuntimeController(Settings())
    _, spec, _, _ = controller._container_spec(
        {
            "id": "00000000-0000-0000-0000-000000000041",
            "workspace_id": "00000000-0000-0000-0000-000000000042",
            "runtime_family": "node",
            "component_kind": "backend",
            "entrypoint": "server.js",
            "execution_contract": {"port": 8080, "health_path": "/"},
            "resource_limits": {},
            "requested_config": {"start_command": "node custom-server.js"},
            "image_ref": "node:20-alpine",
            "runtime_environment": {},
            "managed_build": True,
        },
        Path("/host/build"),
        Path("/host/data"),
    )

    assert spec["Cmd"] == ["sh", "-lc", "node custom-server.js"]


def test_workspace_job_uses_no_restart_policy_and_database_alias() -> None:
    controller = runtime_controller.RuntimeController(Settings())
    _, spec, _, _ = controller._container_spec(
        {
            "id": "00000000-0000-0000-0000-000000000051",
            "workspace_id": "00000000-0000-0000-0000-000000000052",
            "runtime_family": "python",
            "component_kind": "worker",
            "entrypoint": "app.py",
            "execution_contract": {"port": 8080, "health_path": "/health"},
            "resource_limits": {},
            "requested_config": {
                "execution_mode": "job",
                "start_command": "alembic upgrade head",
                "database_url_env": "MK7_MIGRATION_DATABASE_URL",
            },
            "image_ref": "python:3.12",
            "runtime_environment": {
                "DATABASE_URL": "postgresql://workspace:secret@hosted-postgres/app",
                "MK7_MIGRATION_DATABASE_URL": (
                    "postgresql://workspace:secret@hosted-postgres/app"
                ),
            },
        },
        Path("/host/app"),
        Path("/host/data"),
    )

    assert spec["HostConfig"]["RestartPolicy"] == {"Name": "no"}
    assert spec["Cmd"] == ["sh", "-lc", "alembic upgrade head"]
    assert "ExposedPorts" not in spec
    assert any(
        item.startswith("MK7_MIGRATION_DATABASE_URL=postgresql://")
        for item in spec["Env"]
    )


def test_workspace_job_snapshot_separates_runtime_and_migration_database_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000061")
    deployment_id = UUID("00000000-0000-0000-0000-000000000062")
    workspace_id = UUID("00000000-0000-0000-0000-000000000063")
    row = {
        "id": deployment_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "workspace_key": "mk7-job",
        "workspace_config": {"database_policy": {"mode": "platform_managed"}},
        "component_name": "api",
        "requested_config": {
            "execution_mode": "job",
            "database_url_env": "MK7_MIGRATION_DATABASE_URL",
        },
    }

    class _Result:
        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object]:
            return row

    class _Session:
        def execute(self, *_args: object, **_kwargs: object) -> _Result:
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(runtime_controller.base, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        runtime_controller.base,
        "runtime_database_url",
        lambda *_args, **_kwargs: "postgresql://runtime:secret@postgres/workspace",
    )
    monkeypatch.setattr(
        runtime_controller.base,
        "migration_database_url",
        lambda *_args, **_kwargs: "postgresql://owner:secret@postgres/workspace",
    )
    monkeypatch.setattr(
        runtime_controller.base,
        "runtime_environment",
        lambda *_args, **_kwargs: ({}, {}),
    )

    snapshot = runtime_controller.RuntimeController(Settings())._snapshot(
        tenant_id,
        deployment_id,
    )

    assert snapshot["runtime_environment"]["DATABASE_URL"].startswith(
        "postgresql://runtime:"
    )
    assert snapshot["runtime_environment"]["MK7_MIGRATION_DATABASE_URL"].startswith(
        "postgresql://owner:"
    )


def test_runtime_access_job_never_receives_migration_owner_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000071")
    deployment_id = UUID("00000000-0000-0000-0000-000000000072")
    workspace_id = UUID("00000000-0000-0000-0000-000000000073")
    row = {
        "id": deployment_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "workspace_key": "runtime-job",
        "workspace_config": {"database_policy": {"mode": "platform_managed"}},
        "component_name": "job-import",
        "requested_config": {
            "execution_mode": "job",
            "database_access": "runtime",
            "database_url_env": "APP_JOB_DATABASE_URL",
        },
    }

    class _Result:
        def mappings(self) -> _Result:
            return self

        def one_or_none(self) -> dict[str, object]:
            return row

    class _Session:
        def execute(self, *_args: object, **_kwargs: object) -> _Result:
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    monkeypatch.setattr(runtime_controller.base, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        runtime_controller.base,
        "runtime_database_url",
        lambda *_args, **_kwargs: "postgresql://runtime:secret@postgres/workspace",
    )
    monkeypatch.setattr(
        runtime_controller.base,
        "migration_database_url",
        lambda *_args, **_kwargs: pytest.fail("migration identity must not be resolved"),
    )
    monkeypatch.setattr(
        runtime_controller.base,
        "runtime_environment",
        lambda *_args, **_kwargs: ({}, {}),
    )

    snapshot = runtime_controller.RuntimeController(Settings())._snapshot(
        tenant_id,
        deployment_id,
    )

    assert snapshot["runtime_environment"]["APP_JOB_DATABASE_URL"].startswith(
        "postgresql://runtime:"
    )


def test_detected_build_commands_cover_python_hosting_and_node_builds(
    tmp_path: Path,
) -> None:
    python_root = tmp_path / "python"
    python_root.mkdir()
    (python_root / "requirements.hosting.txt").write_text("fastapi\n")
    (python_root / "pyproject.toml").write_text("[build-system]\n")
    node_root = tmp_path / "node"
    node_root.mkdir()
    (node_root / "package.json").write_text(
        '{"scripts":{"build":"vite build","start":"node server.js"}}'
    )
    (node_root / "package-lock.json").write_text("{}")

    python_command, python_selection = runtime_controller.RuntimeController._resolved_build_command(
        {"runtime_family": "python", "requested_config": {}}, python_root
    )
    node_command, node_selection = runtime_controller.RuntimeController._resolved_build_command(
        {"runtime_family": "node", "requested_config": {}}, node_root
    )

    assert python_selection == "detected"
    assert python_command == (
        "python -m pip install --no-cache-dir -r requirements.hosting.txt "
        "&& python -m pip install --no-cache-dir ."
    )
    assert node_selection == "detected"
    assert node_command == "npm ci && npm run build"


def test_managed_build_uses_writable_copy_then_returns_read_only_runtime_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000051")
    workspace_id = UUID("00000000-0000-0000-0000-000000000052")
    deployment_id = UUID("00000000-0000-0000-0000-000000000053")
    settings = Settings(
        hosted_runtime_data_root=tmp_path / "controller",
        runtime_host_data_root=tmp_path / "host",
    )
    controller = runtime_controller.RuntimeController(settings)
    snapshot = {
        "id": deployment_id,
        "tenant_id": tenant_id,
        "workspace_id": workspace_id,
        "runtime_family": "python",
        "component_kind": "backend",
        "entrypoint": "src/mk7_platform/api/main.py",
        "sha256": "a" * 64,
        "image_ref": "python:3.12",
        "execution_contract": {"port": 8080},
        "resource_limits": {},
        "runtime_environment": {},
        "requested_config": {"build_command": "python -m pip install ."},
        "storage_quota_bytes": 128 * 1024 * 1024,
    }
    controller_path, host_path = controller._runtime_paths(snapshot)
    source_root = controller_path / "source"
    package = source_root / "src" / "mk7_platform" / "api"
    package.mkdir(parents=True)
    (package / "main.py").write_text("app = object()\n")

    class _Result:
        def mappings(self) -> _Result:
            return self

        def one(self) -> dict[str, int]:
            return {"total_billable_bytes": 1, "runtime_bytes": 0}

    class _Session:
        def execute(self, *_args: object, **_kwargs: object) -> _Result:
            return _Result()

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    observed: dict[str, object] = {}

    class _Engine:
        def __init__(self, _socket: Path) -> None:
            pass

        def remove(self, name: str) -> None:
            observed.setdefault("removed", []).append(name)

        def create(self, *, name: str, spec: dict[str, object]) -> str:
            observed.update({"name": name, "spec": spec})
            return name

        def start(self, name: str) -> None:
            observed["started"] = name

        def wait(self, name: str) -> int:
            observed["waited"] = name
            return 0

        def logs(self, _name: str) -> list[str]:
            return ["build complete"]

        def close(self) -> None:
            observed["closed"] = True

    monkeypatch.setattr(runtime_controller.base, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(runtime_controller.base, "_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(runtime_controller, "DockerEngine", _Engine)

    root, host_root, result = controller._run_managed_build(
        snapshot,
        source_root,
        {"runtime_bytes": 1, "runtime_rel_path": "release/source"},
    )

    assert root == controller_path / "build"
    assert host_root == host_path / "build"
    assert (root / "src" / "mk7_platform" / "api" / "main.py").is_file()
    assert result["build"]["status"] == "succeeded"
    assert result["build"]["selection"] == "declared"
    assert snapshot["managed_build"] is True
    assert snapshot["managed_build_src_layout"] is True
    assert observed["spec"]["HostConfig"]["Binds"][0].endswith(":/workspace/app:ro")
    builder_command = observed["spec"]["Cmd"][-1]
    assert "python -m venv /workspace/data/.runtime/python/" in builder_command
    assert "/venv" in builder_command
    assert 'RUNTIME_BUILD_ROOT="$(mktemp -d /tmp/warehouse-python-build.' in builder_command
    assert 'cp -a /workspace/app/. "$RUNTIME_BUILD_ROOT/source"' in builder_command
    assert 'cd "$RUNTIME_BUILD_ROOT/source"' in builder_command
    assert builder_command.endswith("python -m pip install .")
    assert observed["waited"] == observed["name"]
    assert observed["closed"] is True


def test_python_api_launcher_restores_package_context_for_relative_imports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "services" / "ai-orchestrator" / "src" / "auto_runtime"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "catalog.py").write_text("APPLICATION = object()\n")
    (package / "app.py").write_text("from .catalog import APPLICATION\napp = APPLICATION\n")
    observed: dict[str, object] = {}
    monkeypatch.setenv("WAREHOUSE_APPLICATION_ROOT", str(tmp_path))
    monkeypatch.setenv("WAREHOUSE_ENTRYPOINT", "services/ai-orchestrator/src/auto_runtime/app.py")
    monkeypatch.setenv("PORT", "8099")
    monkeypatch.setattr(
        uvicorn,
        "run",
        lambda app, **kwargs: observed.update({"app": app, **kwargs}),
    )

    exec(_python_api_launcher_source(), {})

    assert observed["app"] is not None
    assert observed["host"] == "0.0.0.0"
    assert observed["port"] == 8099


def test_runtime_container_rejects_unsafe_python_entrypoint() -> None:
    controller = runtime_controller.RuntimeController(Settings())

    with pytest.raises(RuntimeError, match="safe .py source path"):
        controller._container_spec(
            {
                "id": "00000000-0000-0000-0000-000000000021",
                "workspace_id": "00000000-0000-0000-0000-000000000022",
                "runtime_family": "python",
                "component_kind": "backend",
                "entrypoint": "../outside.py",
                "execution_contract": {"port": 8080, "health_path": "/health"},
                "resource_limits": {},
                "requested_config": {},
                "image_ref": "python:3.12",
                "runtime_environment": {},
            },
            Path("/host/app"),
            Path("/host/data"),
        )


def test_runtime_controller_reconciles_due_git_resources_at_a_bounded_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Settings] = []
    monkeypatch.setattr(
        runtime_controller,
        "reconcile_repository_resources",
        lambda settings: calls.append(settings) or 2,
    )
    controller = runtime_controller.RuntimeController(Settings())

    assert controller.reconcile_repositories() == 2
    assert controller.reconcile_repositories() == 0
    assert calls == [controller.settings]


def test_custom_image_build_falls_back_to_cached_base_on_registry_outage(
    tmp_path: Path,
) -> None:
    calls: list[bool] = []

    class _Engine:
        def image_exists(self, _image: str) -> bool:
            return False

        def build(
            self,
            _root: Path,
            *,
            dockerfile: str,
            tag: str,
            pull: bool,
        ) -> list[str]:
            assert dockerfile == "Dockerfile"
            assert tag.startswith("warehouse-user/")
            calls.append(pull)
            if pull:
                raise RuntimeError(
                    "Docker image build failed: failed to resolve source metadata: "
                    "context deadline exceeded"
                )
            return ["offline build complete"]

    tag, logs = runtime_controller.RuntimeController(Settings())._prepare_custom_image(
        _Engine(),
        {
            "workspace_id": "00000000-0000-0000-0000-000000000081",
            "id": "00000000-0000-0000-0000-000000000082",
            "requested_config": {},
        },
        tmp_path,
    )

    assert tag.startswith("warehouse-user/")
    assert calls == [True, False]
    assert logs == [
        "Registry access failed; retried with trusted base images from the local cache",
        "offline build complete",
    ]


def test_runtime_drift_requeues_only_active_ready_deployment_with_missing_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000091")
    deployment_id = UUID("00000000-0000-0000-0000-000000000092")
    executed: list[str] = []
    events: list[tuple[object, ...]] = []

    class _Result:
        def __init__(self, value: object = None) -> None:
            self.value = value

        def scalar_one_or_none(self) -> object:
            return self.value

    class _Session:
        def execute(self, statement: object, *_args: object, **_kwargs: object) -> _Result:
            sql = str(statement)
            executed.append(sql)
            return _Result(deployment_id if "RETURNING deployment.id" in sql else None)

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    class _Engine:
        def __init__(self, _socket: Path) -> None:
            pass

        def container_exists(self, name: str) -> bool:
            return name.endswith("present")

        def close(self) -> None:
            pass

    controller = runtime_controller.RuntimeController(Settings())
    monkeypatch.setattr(
        controller,
        "_runtime_drift_candidates",
        lambda: [
            (
                tenant_id,
                deployment_id,
                ["warehouse-runtime-present", "warehouse-runtime-missing"],
            )
        ],
    )
    monkeypatch.setattr(runtime_controller.base, "DockerEngine", _Engine)
    monkeypatch.setattr(runtime_controller.base, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(
        runtime_controller.base,
        "_event",
        lambda *args, **_kwargs: events.append(args),
    )

    assert controller.reconcile_runtime_drift() == 1
    assert any("status='queued'" in sql and "health='pending'" in sql for sql in executed)
    assert any("runtime_status='building'" in sql for sql in executed)
    assert events[0][3] == "self_heal_queued"
    assert events[0][4]["missing_container_names"] == ["warehouse-runtime-missing"]
    assert controller.reconcile_runtime_drift() == 0


def test_runtime_orphan_reconcile_stops_only_nonresident_managed_containers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    class _Engine:
        def __init__(self, _socket: Path) -> None:
            observed["created"] = True

        def managed_runtime_containers(self) -> list[dict[str, object]]:
            return [
                {"name": "warehouse-runtime-active", "running": True},
                {"name": "warehouse-runtime-orphan", "running": True},
                {"name": "warehouse-runtime-stopped", "running": False},
            ]

        def stop(self, name: str) -> None:
            observed.setdefault("stopped", []).append(name)

        def close(self) -> None:
            observed["closed"] = True

    controller = runtime_controller.RuntimeController(Settings())
    monkeypatch.setattr(
        controller,
        "_resident_runtime_container_names",
        lambda: {"warehouse-runtime-active"},
    )
    monkeypatch.setattr(runtime_controller.base, "DockerEngine", _Engine)

    assert controller.reconcile_orphan_runtime_containers() == 1
    assert observed["stopped"] == ["warehouse-runtime-orphan"]
    assert observed["closed"] is True
    assert controller.reconcile_orphan_runtime_containers() == 0


def test_runtime_lifecycle_stops_idle_container_and_wakes_same_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tenant_id = UUID("00000000-0000-0000-0000-000000000094")
    deployment_id = UUID("00000000-0000-0000-0000-000000000095")
    payload = {
        "container_names": ["warehouse-runtime-fixture"],
        "internal_url": "http://warehouse-runtime-fixture:8080",
        "internal_urls": ["http://warehouse-runtime-fixture:8080"],
        "health_path": "/health",
    }

    class _Result:
        def __init__(self, value: object) -> None:
            self.value = value

        def scalar_one_or_none(self) -> object:
            return self.value

    queued_results: list[object] = []

    class _Session:
        def execute(self, *_args: object, **_kwargs: object) -> _Result:
            return _Result(queued_results.pop(0))

    @contextmanager
    def fake_tenant_session(_tenant_id: UUID):
        yield _Session()

    class _Engine:
        running = True

        def __init__(self) -> None:
            self.started: list[str] = []
            self.stopped: list[str] = []

        def container_exists(self, _name: str) -> bool:
            return True

        def state(self, _name: str) -> dict[str, object]:
            return {"running": self.running}

        def start(self, name: str) -> None:
            self.started.append(name)
            self.running = True

        def stop(self, name: str) -> None:
            self.stopped.append(name)
            self.running = False

    health_checks: list[tuple[str, int]] = []
    controller = runtime_controller.RuntimeController(
        Settings(runtime_idle_timeout_seconds=60)
    )
    monkeypatch.setattr(runtime_controller.base, "tenant_session", fake_tenant_session)
    monkeypatch.setattr(runtime_controller.base, "_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        controller,
        "_wait_health",
        lambda url, timeout: health_checks.append((url, timeout)),
    )
    engine = _Engine()

    queued_results[:] = [payload, deployment_id]
    assert controller._suspend_runtime(engine, tenant_id, deployment_id) is True
    assert engine.stopped == ["warehouse-runtime-fixture"]
    assert engine.running is False

    queued_results[:] = [payload, deployment_id]
    assert controller._wake_runtime(engine, tenant_id, deployment_id) is True
    assert engine.started == ["warehouse-runtime-fixture"]
    assert health_checks == [
        (
            "http://warehouse-runtime-fixture:8080/health",
            controller.settings.runtime_wake_health_timeout_seconds,
        )
    ]


def test_runtime_mounts_support_arbitrary_non_root_image_users(tmp_path: Path) -> None:
    source = tmp_path / "source"
    nested = source / "nested"
    data = tmp_path / "data"
    nested.mkdir(parents=True, mode=0o750)
    application = nested / "app.py"
    application.write_text("print('ok')", encoding="utf-8")
    source.chmod(0o750)
    nested.chmod(0o750)
    application.chmod(0o640)

    runtime_controller.RuntimeController._prepare_runtime_mounts(source, data)

    assert source.stat().st_mode & 0o005 == 0o005
    assert nested.stat().st_mode & 0o005 == 0o005
    assert application.stat().st_mode & 0o004 == 0o004
    assert data.stat().st_mode & 0o777 == 0o777


def test_runtime_failure_logs_redact_injected_secret_values() -> None:
    assert runtime_controller.RuntimeController._redact_runtime_logs(
        {"runtime_environment": {"MODEL_TOKEN": "top-secret-value"}},
        [
            "MODEL_TOKEN=top-secret-value",
            "Authorization: Bearer abc.def.ghi",
            "safe diagnostic",
        ],
    ) == [
        "MODEL_TOKEN=***",
        "Authorization: Bearer ***",
        "safe diagnostic",
    ]


def test_production_deployer_connects_runtime_controller_to_hosted_database() -> None:
    project_root = Path(__file__).resolve().parents[2]
    deployer = (project_root / "ops/server/warehouse-deploy").read_text()
    runtime_controller_block = deployer.split("start_runtime_controller()", 1)[1].split(
        "wait_health_container()", 1
    )[0]

    assert "WAREHOUSE_HOSTED_DATABASE_ADMIN_URL=" in runtime_controller_block
    assert "${HOSTED_DATABASE_CONTAINER}:5432/postgres" in runtime_controller_block


def test_public_route_verification_uses_internal_api_and_deployment_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    deployment_id = UUID("00000000-0000-0000-0000-000000000048")
    requests: list[tuple[str, dict[str, object]]] = []

    def fake_get(url: str, **kwargs: object) -> httpx.Response:
        requests.append((url, kwargs))
        return httpx.Response(
            200,
            headers={"X-Warehouse-Deployment": str(deployment_id)},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(runtime_controller.httpx, "get", fake_get)

    runtime_controller.RuntimeController._wait_public_route(
        "https://bonfirework.org/assets/bonfire/mk4-workspace/",
        deployment_id,
        "/health",
        1,
    )

    assert requests[0][0] == "http://api:8080/assets/bonfire/mk4-workspace/health"
    assert requests[0][1]["headers"] == {"host": "bonfirework.org"}
