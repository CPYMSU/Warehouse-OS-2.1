from __future__ import annotations

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
    json: dict[str, object] | None = None,
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
    monkeypatch.setenv(
        "WAREHOUSE_ENTRYPOINT", "services/ai-orchestrator/src/auto_runtime/app.py"
    )
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

    assert requests[0][0] == (
        "http://warehouse-os-api-green:8080/assets/bonfire/mk4-workspace/health"
    )
    assert requests[0][1]["headers"] == {"host": "bonfirework.org"}
