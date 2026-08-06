"""Lease-based Runtime Controller for hosted workspace deployments."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shlex
import socket
import tarfile
import tempfile
import time
import traceback
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx
import yaml
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.db.session import system_session, tenant_session
from app.services.database_release import (
    observe_database_release_gate,
    workspace_database_policy,
)
from app.services.hosted_database import migration_database_url, runtime_database_url
from app.services.hosting_fabric import reconcile_repository_resources, runtime_environment
from app.services.object_storage import object_store_read_candidates
from app.services.pages_runtime import set_pages_deployment_pointer
from app.services.source_packages import application_root, materialize_source_archive
from app.services.workspace_usage import measure_workspace_runtime_storage


def _python_api_launcher_source() -> str:
    """Return a self-contained launcher that preserves entrypoint package context."""

    return (
        "import importlib.util, inspect, itertools, os, sys; "
        "from pathlib import Path; "
        "import uvicorn; "
        "root=Path(os.environ.get('WAREHOUSE_APPLICATION_ROOT', '/workspace/app')).resolve(); "
        "path=(root / os.environ['WAREHOUSE_ENTRYPOINT']).resolve(); "
        "path.relative_to(root); "
        "packages=list(itertools.takewhile(lambda value: "
        "(value / '__init__.py').is_file(), path.parents)); "
        "module_name=('.'.join([value.name for value in reversed(packages)] + "
        "[path.stem]) if packages else 'warehouse_user_app'); "
        "import_root=(packages[-1].parent if packages else path.parent); "
        "sys.path[:0]=[str(import_root), str(root), str(path.parent)]; "
        "spec=importlib.util.spec_from_file_location(module_name, path); "
        "module=importlib.util.module_from_spec(spec); "
        "sys.modules[module_name]=module; "
        "spec.loader.exec_module(module); "
        "application=(getattr(module, 'app', None) or "
        "getattr(module, 'application', None)); "
        "assert application is not None, 'entrypoint must expose app or application'; "
        "interface=('wsgi' if callable(application) and "
        "len(inspect.signature(application).parameters)==2 else 'auto'); "
        "uvicorn.run(application, host='0.0.0.0', "
        "port=int(os.environ['PORT']), interface=interface)"
    )


def _event(
    session: object, deployment_id: UUID, tenant_id: UUID, kind: str, payload: dict[str, object]
) -> None:
    sequence = int(
        session.execute(
            text(
                "SELECT COALESCE(max(sequence),0)+1 FROM digital_asset.deployment_events "
                "WHERE deployment_id=:id"
            ),
            {"id": deployment_id},
        ).scalar_one()
    )
    session.execute(
        text(
            """
            INSERT INTO digital_asset.deployment_events(
              deployment_id, tenant_id, sequence, event_type, payload
            ) VALUES (:id,:tenant_id,:sequence,:kind,CAST(:payload AS jsonb))
            """
        ),
        {
            "id": deployment_id,
            "tenant_id": tenant_id,
            "sequence": sequence,
            "kind": kind,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


class DockerEngine:
    """Narrow Docker Engine adapter; no shell or general host command surface."""

    def __init__(self, socket_path: Path) -> None:
        self.client = httpx.Client(
            transport=httpx.HTTPTransport(uds=str(socket_path)),
            base_url="http://docker",
            timeout=30,
        )
        self.api_version = self._negotiate_api_version()
        self.api_prefix = f"/v{self.api_version}"

    @staticmethod
    def _error_detail(response: httpx.Response) -> str:
        detail = re.sub(r"[\x00-\x1f\x7f]+", " ", response.text).strip()
        return re.sub(r"\s+", " ", detail)[:500]

    @classmethod
    def _raise_engine_error(cls, response: httpx.Response, action: str) -> None:
        detail = cls._error_detail(response)
        message = f"Docker Engine {action} failed: HTTP {response.status_code}"
        if detail:
            message += f" · {detail}"
        raise RuntimeError(message)

    def _negotiate_api_version(self) -> str:
        response = self.client.get("/version")
        if response.status_code != 200:
            self._raise_engine_error(response, "API negotiation")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Docker Engine API negotiation returned invalid JSON") from exc
        api_version = str(payload.get("ApiVersion") or "").strip()
        if not re.fullmatch(r"\d+\.\d+", api_version):
            raise RuntimeError("Docker Engine API negotiation returned no usable version")
        return api_version

    def close(self) -> None:
        self.client.close()

    def create(self, *, name: str, spec: dict[str, object]) -> str:
        response = self.client.post(
            f"{self.api_prefix}/containers/create",
            params={"name": name},
            json=spec,
        )
        if response.status_code == 404 and "No such image" in response.text:
            raise RuntimeError("Runtime image is not installed on the provider")
        if response.status_code != 201:
            self._raise_engine_error(response, "container creation")
        return str(response.json()["Id"])

    def start(self, container_id: str) -> None:
        response = self.client.post(f"{self.api_prefix}/containers/{container_id}/start")
        if response.status_code != 204:
            self._raise_engine_error(response, "container start")

    def stop(self, container_id: str, *, timeout: int = 10) -> None:
        response = self.client.post(
            f"{self.api_prefix}/containers/{container_id}/stop",
            params={"t": str(max(1, timeout))},
        )
        if response.status_code not in {204, 304, 404}:
            self._raise_engine_error(response, "container stop")

    def remove(self, name: str) -> None:
        response = self.client.delete(
            f"{self.api_prefix}/containers/{name}",
            params={"force": "true", "v": "true"},
        )
        if response.status_code not in {204, 404}:
            self._raise_engine_error(response, "container cleanup")

    def logs(self, name: str) -> list[str]:
        response = self.client.get(
            f"{self.api_prefix}/containers/{name}/logs",
            params={"stdout": "true", "stderr": "true", "tail": "120"},
        )
        if response.status_code != 200:
            return []
        clean = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", response.text)
        return [line[-2000:] for line in clean.splitlines()[-120:]]

    def state(self, name: str) -> dict[str, object]:
        response = self.client.get(f"{self.api_prefix}/containers/{name}/json")
        if response.status_code != 200:
            self._raise_engine_error(response, "container inspection")
        state = response.json().get("State") or {}
        return {
            "running": bool(state.get("Running")),
            "status": state.get("Status"),
            "exit_code": state.get("ExitCode"),
        }

    def container_exists(self, name: str) -> bool:
        response = self.client.get(f"{self.api_prefix}/containers/{name}/json")
        if response.status_code == 404:
            return False
        if response.status_code != 200:
            self._raise_engine_error(response, "container inspection")
        return True

    def managed_runtime_containers(self) -> list[dict[str, object]]:
        response = self.client.get(
            f"{self.api_prefix}/containers/json",
            params={
                "all": "true",
                "filters": json.dumps(
                    {
                        "label": [
                            "org.bonfirework.managed=runtime-controller",
                        ]
                    },
                    separators=(",", ":"),
                ),
            },
        )
        if response.status_code != 200:
            self._raise_engine_error(response, "managed container listing")
        try:
            payload = response.json()
        except ValueError as exc:
            raise RuntimeError("Docker Engine container listing returned invalid JSON") from exc
        if not isinstance(payload, list):
            raise RuntimeError("Docker Engine container listing returned invalid data")
        containers: list[dict[str, object]] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            names = item.get("Names")
            labels = item.get("Labels")
            if not isinstance(names, list) or not isinstance(labels, dict):
                continue
            name = next(
                (
                    str(value).removeprefix("/")
                    for value in names
                    if re.fullmatch(
                        r"/?warehouse-runtime-[a-zA-Z0-9_.-]+",
                        str(value),
                    )
                ),
                None,
            )
            if name is None:
                continue
            containers.append(
                {
                    "name": name,
                    "deployment_id": str(
                        labels.get("org.bonfirework.deployment") or ""
                    ),
                    "workspace_id": str(labels.get("org.bonfirework.workspace") or ""),
                    "running": str(item.get("State") or "").lower() == "running",
                }
            )
        return containers

    def wait(self, name: str, *, timeout: int = 1200) -> int:
        """Wait for a bounded one-shot container and return its exit code."""

        response = self.client.post(
            f"{self.api_prefix}/containers/{name}/wait",
            params={"condition": "not-running"},
            timeout=timeout,
        )
        if response.status_code != 200:
            self._raise_engine_error(response, "container wait")
        try:
            return int(response.json()["StatusCode"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("Docker Engine container wait returned no exit code") from exc

    def replica_spec(self, name: str, *, network_alias: str | None = None) -> dict[str, object]:
        """Return a create-safe copy of an existing managed container.

        Docker's inspection payload contains runtime-only fields that cannot be
        posted back to ``containers/create``.  Keep an explicit allow-list so
        autoscaling can clone a Compose route service without giving the
        control plane a general container mutation surface.
        """

        response = self.client.get(f"{self.api_prefix}/containers/{name}/json")
        if response.status_code != 200:
            self._raise_engine_error(response, "container inspection")
        payload = response.json()
        config = payload.get("Config") or {}
        host = payload.get("HostConfig") or {}
        spec = {
            key: config[key]
            for key in (
                "User",
                "Env",
                "Cmd",
                "Healthcheck",
                "Image",
                "Volumes",
                "WorkingDir",
                "Entrypoint",
                "Labels",
                "ExposedPorts",
                "StopSignal",
            )
            if config.get(key) not in (None, "", [], {})
        }
        spec["HostConfig"] = {
            key: host[key]
            for key in (
                "Binds",
                "NetworkMode",
                "ReadonlyRootfs",
                "Tmpfs",
                "CapDrop",
                "SecurityOpt",
                "Memory",
                "NanoCpus",
                "PidsLimit",
                "RestartPolicy",
                "DeviceRequests",
            )
            if host.get(key) not in (None, "", [], {})
        }
        if network_alias:
            network = str(spec["HostConfig"].get("NetworkMode") or "")
            if network:
                spec["NetworkingConfig"] = {
                    "EndpointsConfig": {network: {"Aliases": [network_alias]}}
                }
        return spec

    def stats(self, name: str) -> dict[str, float]:
        response = self.client.get(
            f"{self.api_prefix}/containers/{name}/stats",
            params={"stream": "false", "one-shot": "true"},
            timeout=15,
        )
        if response.status_code != 200:
            self._raise_engine_error(response, "container statistics")
        payload = response.json()
        cpu = payload.get("cpu_stats") or {}
        previous = payload.get("precpu_stats") or {}
        cpu_delta = int((cpu.get("cpu_usage") or {}).get("total_usage") or 0) - int(
            (previous.get("cpu_usage") or {}).get("total_usage") or 0
        )
        system_delta = int(cpu.get("system_cpu_usage") or 0) - int(
            previous.get("system_cpu_usage") or 0
        )
        online_cpus = int(
            cpu.get("online_cpus")
            or len((cpu.get("cpu_usage") or {}).get("percpu_usage") or [])
            or 1
        )
        cpu_percent = (
            max(0.0, cpu_delta / system_delta * online_cpus * 100.0)
            if cpu_delta > 0 and system_delta > 0
            else 0.0
        )
        memory = payload.get("memory_stats") or {}
        memory_usage = float(memory.get("usage") or 0)
        memory_limit = float(memory.get("limit") or 0)
        return {
            "cpu_percent": round(cpu_percent, 3),
            "memory_percent": round(
                memory_usage / memory_limit * 100.0 if memory_limit else 0.0, 3
            ),
        }

    def accelerator_capacity(self) -> dict[str, object]:
        response = self.client.get(f"{self.api_prefix}/info")
        if response.status_code != 200:
            self._raise_engine_error(response, "capacity inspection")
        payload = response.json()
        generic = (
            ((payload.get("Swarm") or {}).get("NodeSpec") or {})
            .get("Resources", {})
            .get("GenericResources", [])
        )
        gpu_ids = {
            str(item.get("DiscreteResourceSpec", {}).get("StringValue"))
            for item in generic
            if str(item.get("DiscreteResourceSpec", {}).get("Kind") or "").upper()
            in {"NVIDIA-GPU", "GPU"}
        }
        runtimes = payload.get("Runtimes") or {}
        available = len({item for item in gpu_ids if item and item != "None"})
        if not available and "nvidia" in runtimes:
            available = 1
        return {
            "kind": "gpu",
            "total_units": available,
            "runtime": "nvidia" if "nvidia" in runtimes else None,
            "observed_ids": len(gpu_ids),
        }

    @staticmethod
    def _stream_error(response: httpx.Response) -> str | None:
        failure = None
        for line in response.iter_lines():
            try:
                payload = json.loads(line)
            except (TypeError, json.JSONDecodeError):
                continue
            if isinstance(payload, dict) and payload.get("error"):
                failure = str(payload["error"])
            detail = payload.get("errorDetail") if isinstance(payload, dict) else None
            if isinstance(detail, dict) and detail.get("message"):
                failure = str(detail["message"])
        return failure

    def pull(self, image: str) -> None:
        with self.client.stream(
            "POST",
            f"{self.api_prefix}/images/create",
            params={"fromImage": image},
            timeout=600,
        ) as response:
            if response.status_code not in {200, 201}:
                self._raise_engine_error(response, "image pull")
            failure = self._stream_error(response)
        if failure:
            raise RuntimeError(f"Docker Engine image pull failed: {failure[:500]}")

    def image_exists(self, image: str) -> bool:
        encoded = quote(image, safe="")
        response = self.client.get(
            f"{self.api_prefix}/images/{encoded}/json",
            timeout=30,
        )
        return response.status_code == 200

    def build(
        self,
        root: Path,
        *,
        dockerfile: str,
        tag: str,
        pull: bool = True,
    ) -> list[str]:
        dockerfile_path = (root / dockerfile).resolve()
        dockerfile_path.relative_to(root.resolve())
        if not dockerfile_path.is_file():
            raise RuntimeError(f"Dockerfile not found: {dockerfile}")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".warehouse-build-", suffix=".tar", dir=root.parent
        )
        os.close(descriptor)
        archive_path = Path(temporary_name)
        try:
            with tarfile.open(archive_path, "w") as archive:
                archive.add(root, arcname=".", recursive=True)
            with archive_path.open("rb") as stream:
                with self.client.stream(
                    "POST",
                    f"{self.api_prefix}/build",
                    params={
                        "t": tag,
                        "dockerfile": dockerfile,
                        "rm": "true",
                        "forcerm": "true",
                        "pull": str(pull).lower(),
                    },
                    headers={"Content-Type": "application/x-tar"},
                    content=stream,
                    timeout=1200,
                ) as response:
                    if response.status_code != 200:
                        self._raise_engine_error(response, "image build")
                    logs: list[str] = []
                    failure = None
                    for line in response.iter_lines():
                        try:
                            payload = json.loads(line)
                        except (TypeError, json.JSONDecodeError):
                            continue
                        if isinstance(payload, dict) and payload.get("stream"):
                            logs.extend(str(payload["stream"]).strip().splitlines())
                        if isinstance(payload, dict) and payload.get("error"):
                            failure = str(payload["error"])
                    if failure:
                        raise RuntimeError(f"Docker image build failed: {failure[:500]}")
            return [line[-2000:] for line in logs[-120:]]
        finally:
            archive_path.unlink(missing_ok=True)


class RuntimeController:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}"
        self._last_capacity_observation = 0.0
        self._last_scaling_reconcile = 0.0
        self._last_repository_reconcile = 0.0
        self._last_runtime_drift_reconcile = 0.0
        self._last_runtime_lifecycle_reconcile = 0.0
        self._last_runtime_orphan_reconcile = 0.0

    def reconcile_repositories(self) -> int:
        if time.monotonic() - self._last_repository_reconcile < 60:
            return 0
        self._last_repository_reconcile = time.monotonic()
        return reconcile_repository_resources(self.settings)

    def observe_capacity(self) -> None:
        if time.monotonic() - self._last_capacity_observation < 60:
            return
        self._last_capacity_observation = time.monotonic()
        engine = DockerEngine(self.settings.runtime_docker_socket)
        try:
            capacity = engine.accelerator_capacity()
        finally:
            engine.close()
        total = int(capacity["total_units"])
        with system_session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO platform.accelerator_pools(
                      pool_key,provider_key,accelerator_kind,total_units,
                      allocatable_units,status,capabilities,last_observed_at
                    ) VALUES (
                      'local-gpu-01','warehouse_runtime_v1','gpu',:total,:total,
                      :status,CAST(:capabilities AS jsonb),now()
                    ) ON CONFLICT (pool_key) DO UPDATE SET
                      total_units=EXCLUDED.total_units,
                      allocatable_units=EXCLUDED.allocatable_units,
                      status=EXCLUDED.status,
                      capabilities=EXCLUDED.capabilities,
                      last_observed_at=now()
                    """
                ),
                {
                    "total": total,
                    "status": "online" if total else "offline",
                    "capabilities": json.dumps(capacity),
                },
            )

    def heartbeat(
        self,
        *,
        status: str = "online",
        claimed: bool = False,
        successful: bool = False,
        error: str | None = None,
    ) -> None:
        with system_session() as session:
            session.execute(
                text(
                    """
                    INSERT INTO platform.runtime_workers(
                      worker_id, provider_key, release_id, status,
                      last_seen_at, last_poll_at, last_claim_at,
                      last_success_at, last_error, metadata
                    ) VALUES (
                      :worker, 'warehouse_runtime_v1', :release, :status,
                      now(), now(),
                      CASE WHEN :claimed THEN now() END,
                      CASE WHEN :successful THEN now() END,
                      CAST(:error AS text),
                      jsonb_build_object('hostname', CAST(:hostname AS text))
                    )
                    ON CONFLICT (worker_id) DO UPDATE SET
                      release_id=EXCLUDED.release_id,
                      status=EXCLUDED.status,
                      last_seen_at=now(),
                      last_poll_at=now(),
                      last_claim_at=CASE WHEN :claimed
                        THEN now() ELSE platform.runtime_workers.last_claim_at END,
                      last_success_at=CASE WHEN :successful
                        THEN now() ELSE platform.runtime_workers.last_success_at END,
                      last_error=CASE
                        WHEN CAST(:error AS text) IS NOT NULL THEN CAST(:error AS text)
                        WHEN :successful THEN NULL
                        ELSE platform.runtime_workers.last_error END,
                      metadata=EXCLUDED.metadata,
                      updated_at=now()
                    """
                ),
                {
                    "worker": self.worker_id,
                    "release": os.getenv("WAREHOUSE_RELEASE_ID"),
                    "status": status,
                    "claimed": claimed,
                    "successful": successful,
                    "error": (error or "")[:2000] or None,
                    "hostname": socket.gethostname(),
                },
            )

    def _tenants(self) -> list[UUID]:
        with system_session() as session:
            return [
                UUID(str(value))
                for value in session.execute(
                    text("SELECT id FROM iam.tenants WHERE status='active' ORDER BY id")
                ).scalars()
            ]

    def claim(self) -> tuple[UUID, UUID] | None:
        expires = datetime.now(UTC) + timedelta(
            seconds=self.settings.runtime_controller_lease_seconds
        )
        for tenant_id in self._tenants():
            with tenant_session(tenant_id) as session:
                row = session.execute(
                    text(
                        """
                        SELECT id FROM digital_asset.deployments
                        WHERE runtime_profile_key IS NOT NULL
                          AND (
                            status='queued'
                            OR (
                              status IN ('building','deploying')
                              AND lease_expires_at < now()
                            )
                          )
                        ORDER BY created_at
                        FOR UPDATE SKIP LOCKED LIMIT 1
                        """
                    )
                ).scalar_one_or_none()
                if row is None:
                    continue
                deployment_id = UUID(str(row))
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments
                        SET status='building', provider_key='warehouse_runtime_v1',
                            lease_owner=:worker, lease_expires_at=:expires,
                            attempt_count=attempt_count+1,
                            started_at=COALESCE(started_at,now())
                        WHERE id=:id
                        """
                    ),
                    {"worker": self.worker_id, "expires": expires, "id": deployment_id},
                )
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "claimed",
                    {"worker": self.worker_id, "lease_expires_at": expires.isoformat()},
                )
                return tenant_id, deployment_id
        return None

    def _snapshot(self, tenant_id: UUID, deployment_id: UUID) -> dict[str, object]:
        with tenant_session(tenant_id) as session:
            row = (
                session.execute(
                    text(
                        """
                    SELECT d.*, w.asset_id, w.workspace_key, w.storage_quota_bytes,
                           w.config AS workspace_config,
                           w.active_deployment_id,
                           c.component_name, c.component_kind, c.runtime,
                           c.entrypoint, c.build_command, c.start_command,
                           ar.storage_provider, ar.object_key, ar.sha256,
                           p.runtime_family, p.image_ref, p.execution_contract,
                           p.resource_limits
                    FROM digital_asset.deployments AS d
                    JOIN digital_asset.workspaces AS w ON w.id=d.workspace_id
                    JOIN digital_asset.workspace_components AS c ON c.id=d.component_id
                    JOIN digital_asset.artifacts AS ar
                      ON ar.version_id=d.source_version_id AND ar.storage_role='code'
                      AND ar.state='verified'
                    JOIN platform.runtime_profiles AS p
                      ON p.profile_key=d.runtime_profile_key AND p.enabled
                    WHERE d.id=:id
                    ORDER BY ar.created_at DESC LIMIT 1
                    """
                    ),
                    {"id": deployment_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise RuntimeError("Deployment source or Runtime profile is unavailable")
            snapshot = dict(row)
            environment = {
                "WAREHOUSE_WORKSPACE_ID": str(snapshot["workspace_id"]),
                "WAREHOUSE_WORKSPACE_KEY": str(snapshot["workspace_key"]),
                "DAM_WORKSPACE": str(snapshot["workspace_key"]),
                "WAREHOUSE_RUNTIME_SECRET": hmac.new(
                    self.settings.integration_secret.encode(),
                    f"workspace-runtime:{snapshot['workspace_id']}".encode(),
                    hashlib.sha256,
                ).hexdigest(),
            }
            database_policy = workspace_database_policy(snapshot.get("workspace_config"))
            snapshot["database_policy"] = database_policy
            if bool(database_policy["platform_database_injected"]):
                database_url = runtime_database_url(
                    session,
                    snapshot["workspace_id"],
                    settings=self.settings,
                )
                if database_url:
                    environment["DATABASE_URL"] = database_url
                    requested = snapshot.get("requested_config") or {}
                    database_url_env = str(requested.get("database_url_env") or "").strip()
                    if database_url_env:
                        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,79}", database_url_env):
                            raise RuntimeError("Database URL environment alias is invalid")
                        execution_mode = str(requested.get("execution_mode") or "service")
                        database_access = str(
                            requested.get("database_access")
                            or ("migration" if execution_mode == "job" else "runtime")
                        )
                        if execution_mode == "job" and database_access == "migration":
                            migration_url = migration_database_url(
                                session,
                                snapshot["workspace_id"],
                                settings=self.settings,
                            )
                            if migration_url:
                                environment[database_url_env] = migration_url
                        elif database_access == "runtime":
                            environment[database_url_env] = database_url
            fabric_environment, hosting_policy = runtime_environment(
                session,
                UUID(str(snapshot["workspace_id"])),
                str(snapshot.get("component_name") or "api"),
                self.settings,
            )
            environment.update(fabric_environment)
            snapshot["runtime_environment"] = environment
            snapshot["hosting_policy"] = hosting_policy
            return snapshot

    def _runtime_paths(self, snapshot: dict[str, object]) -> tuple[Path, Path]:
        relative = (
            Path("tenants")
            / str(snapshot["tenant_id"])
            / "workspaces"
            / str(snapshot["workspace_id"])
            / "releases"
            / str(snapshot["id"])
        )
        controller_path = (self.settings.hosted_runtime_data_root / relative).resolve()
        controller_path.relative_to(self.settings.hosted_runtime_data_root.resolve())
        host_path = (self.settings.runtime_host_data_root / relative).resolve()
        host_path.relative_to(self.settings.runtime_host_data_root.resolve())
        return controller_path, host_path

    @staticmethod
    def _directory_bytes(path: Path) -> int:
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())

    @staticmethod
    def _prepare_runtime_mounts(source_root: Path, data_root: Path) -> None:
        """Make isolated bind mounts usable by arbitrary non-root image users.

        The archive extractor deliberately creates control-plane-only 0750/0640
        paths.  A custom OCI image may declare any numeric non-root UID, so the
        Runtime copy needs read/traverse bits while remaining mounted read-only.
        The data directory is unique to one workspace and is the only writable
        bind; broad mode bits do not grant another container a host path.
        """

        source_root.chmod(source_root.stat().st_mode | 0o055)
        for item in source_root.rglob("*"):
            mode = item.stat().st_mode
            item.chmod(mode | (0o055 if item.is_dir() else 0o044))
        data_root.mkdir(parents=True, exist_ok=True, mode=0o777)
        data_root.chmod(0o777)

    @staticmethod
    def _redact_runtime_logs(snapshot: dict[str, object], lines: list[str]) -> list[str]:
        values = [
            str(value)
            for value in dict(snapshot.get("runtime_environment") or {}).values()
            if len(str(value)) >= 4
        ]
        redacted = []
        for original in lines[-120:]:
            line = str(original)[-2000:]
            for value in values:
                line = line.replace(value, "***")
            line = re.sub(
                r"(?i)\b(password|token|secret|api[_-]?key)\s*=\s*[^\s]+",
                r"\1=***",
                line,
            )
            line = re.sub(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+", "Bearer ***", line)
            redacted.append(line)
        return redacted

    def _materialize(self, snapshot: dict[str, object]) -> tuple[Path, Path, dict[str, object]]:
        store_path = None
        for store in object_store_read_candidates(
            self.settings,
            str(snapshot["storage_provider"]),
        ):
            candidate = store.path_for(str(snapshot["object_key"]))
            if candidate.is_file():
                store_path = candidate
                break
        if store_path is None:
            raise RuntimeError("Custodied source object is unavailable")
        digest = hashlib.sha256(store_path.read_bytes()).hexdigest()
        if digest != str(snapshot["sha256"]):
            raise RuntimeError("Custodied source digest verification failed")
        controller_path, host_path = self._runtime_paths(snapshot)
        source_path = controller_path / "source"
        manifest = materialize_source_archive(
            store_path,
            source_path,
            max_uncompressed_bytes=int(snapshot["storage_quota_bytes"]),
        )
        root = application_root(source_path)
        runtime_bytes = self._directory_bytes(source_path)
        with tenant_session(UUID(str(snapshot["tenant_id"]))) as session:
            usage = (
                session.execute(
                    text(
                        """
                    SELECT total_billable_bytes, runtime_bytes
                    FROM digital_asset.workspace_usage WHERE workspace_id=:id
                    FOR UPDATE
                    """
                    ),
                    {"id": snapshot["workspace_id"]},
                )
                .mappings()
                .one()
            )
            projected = (
                int(usage["total_billable_bytes"]) - int(usage["runtime_bytes"]) + runtime_bytes
            )
            if projected > int(snapshot["storage_quota_bytes"]):
                raise RuntimeError("Expanded Runtime source exceeds the workspace logical quota")
        relative_root = root.relative_to(self.settings.hosted_runtime_data_root.resolve())
        host_root = host_path / root.relative_to(controller_path)
        return (
            root,
            host_root,
            {
                **manifest.public(),
                "runtime_bytes": runtime_bytes,
                "runtime_rel_path": str(relative_root),
            },
        )

    def _container_spec(
        self, snapshot: dict[str, object], host_root: Path, host_data: Path
    ) -> tuple[str, dict[str, object], int, str]:
        family = str(snapshot["runtime_family"])
        image = str(snapshot.get("image_ref") or "")
        contract = snapshot.get("execution_contract") or {}
        limits = snapshot.get("resource_limits") or {}
        port = int(contract.get("port") or 8080)
        health_path = str(
            (snapshot.get("requested_config") or {}).get("health_path")
            or contract.get("health_path")
            or "/health"
        )
        component_kind = str(snapshot.get("component_kind") or "backend")
        process_only = component_kind in {"worker", "agent"}
        one_shot = str(
            (snapshot.get("requested_config") or {}).get("execution_mode") or "service"
        ) == "job"
        runtime_entrypoint: str | None = None
        configured_start = str(
            (snapshot.get("requested_config") or {}).get("start_command")
            or snapshot.get("start_command")
            or ""
        ).strip()
        managed_build = bool(snapshot.get("managed_build"))
        if family == "python":
            entrypoint = str(
                snapshot.get("entrypoint") or contract.get("default_entrypoint") or "app.py"
            )
            entrypoint_path = Path(entrypoint)
            if (
                entrypoint_path.is_absolute()
                or ".." in entrypoint_path.parts
                or entrypoint_path.suffix.lower() != ".py"
            ):
                raise RuntimeError("Python Runtime entrypoint must be a safe .py source path")
            runtime_entrypoint = entrypoint_path.as_posix()
        if configured_start:
            command = configured_start
        elif family == "python":
            dependency_cache = hashlib.sha256(
                (
                    f"{snapshot.get('sha256') or snapshot['id']}:{snapshot.get('image_ref') or ''}"
                ).encode()
            ).hexdigest()[:24]
            dependency_path = f"/workspace/data/.runtime/python/{dependency_cache}"
            install = (
                f"RUNTIME_PYTHON_PATH={dependency_path}; "
                'if [ ! -f "$RUNTIME_PYTHON_PATH/.ready" ]; then '
                'rm -rf "$RUNTIME_PYTHON_PATH"; mkdir -p "$RUNTIME_PYTHON_PATH"; '
                "if [ -f requirements.txt ]; then "
                'pip install --no-cache-dir --upgrade --target "$RUNTIME_PYTHON_PATH" '
                "-r requirements.txt; "
                "elif [ -f pyproject.toml ]; then "
                'RUNTIME_BUILD_ROOT="$(mktemp -d)"; '
                'cp -a . "$RUNTIME_BUILD_ROOT/source"; '
                'pip install --no-cache-dir --upgrade --target "$RUNTIME_PYTHON_PATH" '
                '"$RUNTIME_BUILD_ROOT/source"; '
                'rm -rf "$RUNTIME_BUILD_ROOT"; '
                "fi; "
                'touch "$RUNTIME_PYTHON_PATH/.ready"; '
                "fi; "
                'export PYTHONPATH="$RUNTIME_PYTHON_PATH${PYTHONPATH:+:$PYTHONPATH}"; '
            )
            if process_only:
                command = (
                    "set -eu; cd /workspace/app; "
                    + ("" if managed_build else install)
                    + 'exec python "$WAREHOUSE_ENTRYPOINT"'
                )
            else:
                command = (
                    "set -eu; cd /workspace/app; "
                    + ("" if managed_build else install)
                    + f"exec python -c {shlex.quote(_python_api_launcher_source())}"
                )
        elif family == "node":
            command = (
                "set -eu; cd /workspace/app; "
                "if [ -f package-lock.json ]; then npm ci --omit=dev; "
                "else npm install --omit=dev; fi; "
                "exec npm start"
            )
        elif family == "container":
            command = str((snapshot.get("requested_config") or {}).get("command") or "").strip()
        else:
            raise RuntimeError("Static deployments do not use a container")
        name = f"warehouse-runtime-{str(snapshot['id']).replace('-', '')[:20]}"
        memory = int(limits.get("memory_mb") or 512) * 1024 * 1024
        cpus = int(float(limits.get("cpus") or 0.5) * 1_000_000_000)
        spec: dict[str, object] = {
            "Image": str(snapshot.get("resolved_image") or image),
            "WorkingDir": "/workspace/app",
            "Env": [
                f"PORT={port}",
                "HOST=0.0.0.0",
                "PYTHONDONTWRITEBYTECODE=1",
                "WAREHOUSE_DATA_DIR=/workspace/data",
                "WAREHOUSE_APPLICATION_ROOT=/workspace/app",
                *(
                    [f"WAREHOUSE_ENTRYPOINT={runtime_entrypoint}"]
                    if runtime_entrypoint is not None
                    else []
                ),
                *[
                    f"{key}={value}"
                    for key, value in sorted(
                        dict(snapshot.get("runtime_environment") or {}).items()
                    )
                ],
            ],
            "Labels": {
                "org.bonfirework.managed": "runtime-controller",
                "org.bonfirework.deployment": str(snapshot["id"]),
                "org.bonfirework.workspace": str(snapshot["workspace_id"]),
            },
            "HostConfig": {
                "Binds": [f"{host_root}:/workspace/app:ro", f"{host_data}:/workspace/data:rw"],
                "NetworkMode": self.settings.runtime_docker_network,
                "ReadonlyRootfs": True,
                "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=268435456"},
                "CapDrop": ["ALL"],
                "SecurityOpt": ["no-new-privileges:true"],
                "Memory": memory,
                "NanoCpus": cpus,
                "PidsLimit": int(limits.get("pids") or 128),
                "RestartPolicy": {"Name": "no" if one_shot else "unless-stopped"},
            },
        }
        if command:
            spec["Cmd"] = ["sh", "-lc", command]
        if not process_only:
            spec["ExposedPorts"] = {f"{port}/tcp": {}}
        return name, spec, port, health_path

    def _wait_health(self, url: str, timeout: int) -> None:
        deadline = time.monotonic() + timeout
        last = "not reachable"
        while time.monotonic() < deadline:
            try:
                response = httpx.get(url, timeout=3, follow_redirects=False)
                if 200 <= response.status_code < 400:
                    return
                last = f"HTTP {response.status_code}"
            except httpx.HTTPError as exc:
                last = exc.__class__.__name__
            time.sleep(2)
        raise RuntimeError(f"Runtime health probe failed: {last}")

    @staticmethod
    def _wait_public_route(
        url: str,
        deployment_id: UUID,
        health_path: str,
        timeout: int,
    ) -> None:
        parsed = urlsplit(url)
        route = (parsed.path or "/").rstrip("/") + "/" + health_path.lstrip("/")
        if parsed.query:
            route += "?" + parsed.query
        candidates = [
            f"http://api:8080{route}",
            f"http://warehouse-os-api-green:8080{route}",
            f"http://warehouse-os-api-blue:8080{route}",
            url,
        ]
        deadline = time.monotonic() + timeout
        last = "not reachable"
        while time.monotonic() < deadline:
            for candidate in candidates:
                try:
                    response = httpx.get(
                        candidate,
                        headers={"host": parsed.netloc},
                        timeout=3,
                        follow_redirects=False,
                    )
                    observed = response.headers.get("x-warehouse-deployment")
                    if 200 <= response.status_code < 400 and observed == str(deployment_id):
                        return
                    last = f"HTTP {response.status_code} deployment={observed or 'none'}"
                except httpx.HTTPError as exc:
                    last = exc.__class__.__name__
            time.sleep(1)
        raise RuntimeError(f"Public Runtime route verification failed: {last}")

    @staticmethod
    def _wait_process(engine: DockerEngine, name: str, timeout: int = 15) -> None:
        deadline = time.monotonic() + timeout
        stable_since = None
        last: dict[str, object] = {}
        while time.monotonic() < deadline:
            last = engine.state(name)
            if bool(last.get("running")):
                stable_since = stable_since or time.monotonic()
                if time.monotonic() - stable_since >= 3:
                    return
            else:
                stable_since = None
            time.sleep(0.5)
        raise RuntimeError(f"Runtime process did not remain running: {last}")

    def _prepare_custom_image(
        self,
        engine: DockerEngine,
        snapshot: dict[str, object],
        root: Path,
        *,
        image: str | None = None,
        dockerfile: str | None = None,
        suffix: str = "app",
    ) -> tuple[str, list[str]]:
        requested = snapshot.get("requested_config") or {}
        requested_image = str(image or requested.get("image") or "").strip()
        selected_dockerfile = str(dockerfile or requested.get("dockerfile") or "Dockerfile").strip()
        if requested_image:
            engine.pull(requested_image)
            return requested_image, []
        tag = (
            "warehouse-user/"
            f"{str(snapshot['workspace_id']).replace('-', '')[:20]}-"
            f"{str(snapshot['id']).replace('-', '')[:16]}-{suffix}:latest"
        )
        if engine.image_exists(tag):
            return tag, ["Reused immutable deployment image from the local Docker cache"]
        try:
            logs = engine.build(
                root,
                dockerfile=selected_dockerfile,
                tag=tag,
                pull=True,
            )
        except RuntimeError as exc:
            if engine.image_exists(tag):
                return tag, [
                    "Recovered the immutable deployment image after an interrupted build stream"
                ]
            if not self._transient_registry_failure(str(exc)):
                raise
            logs = [
                "Registry access failed; retried with trusted base images from the local cache"
            ]
            logs.extend(
                engine.build(
                    root,
                    dockerfile=selected_dockerfile,
                    tag=tag,
                    pull=False,
                )
            )
        return tag, logs

    @staticmethod
    def _transient_registry_failure(message: str) -> bool:
        normalized = message.lower()
        return any(
            marker in normalized
            for marker in (
                "connection reset",
                "connection timed out",
                "context deadline exceeded",
                "failed to do request",
                "failed to resolve source metadata",
                "i/o timeout",
                "network is unreachable",
                "no such host",
                "tls handshake timeout",
                "unexpected eof",
            )
        )

    @staticmethod
    def _compose_environment(value: object) -> dict[str, str]:
        if value is None:
            return {}
        if isinstance(value, dict):
            return {str(key): str(item) for key, item in value.items() if item is not None}
        if isinstance(value, list):
            result = {}
            for item in value:
                key, separator, raw = str(item).partition("=")
                if separator:
                    result[key] = raw
            return result
        raise RuntimeError("Compose environment must be an object or KEY=value array")

    def _execute_compose(
        self,
        engine: DockerEngine,
        snapshot: dict[str, object],
        root: Path,
        host_root: Path,
        controller_data: Path,
        host_data: Path,
    ) -> tuple[dict[str, object], list[str]]:
        requested = snapshot.get("requested_config") or {}
        compose_name = str(
            requested.get("compose_file") or requested.get("entrypoint") or "compose.yaml"
        )
        compose_path = (root / compose_name).resolve()
        compose_path.relative_to(root.resolve())
        if not compose_path.is_file():
            alternatives = [
                root / name
                for name in (
                    "compose.yaml",
                    "compose.yml",
                    "docker-compose.yaml",
                    "docker-compose.yml",
                )
                if (root / name).is_file()
            ]
            if not alternatives:
                raise RuntimeError("Compose file is unavailable at the application root")
            compose_path = alternatives[0]
        document = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
        services = document.get("services") if isinstance(document, dict) else None
        if not isinstance(services, dict) or not 1 <= len(services) <= 16:
            raise RuntimeError("Compose must define between 1 and 16 services")
        forbidden = {
            "privileged",
            "network_mode",
            "pid",
            "ipc",
            "devices",
            "cap_add",
            "security_opt",
        }
        route_service = str(requested.get("route_service") or "").strip()
        if not route_service:
            route_service = next(
                (
                    str(name)
                    for name, service in services.items()
                    if isinstance(service, dict) and service.get("ports")
                ),
                str(next(iter(services))),
            )
        if route_service not in services:
            raise RuntimeError("Compose route_service does not exist")
        created: list[str] = []
        service_results: dict[str, object] = {}
        pending = {
            str(name): dict(value) for name, value in services.items() if isinstance(value, dict)
        }
        resolved: set[str] = set()
        policy = snapshot.get("hosting_policy") or {}
        route_replicas = max(1, min(int(policy.get("replicas") or 1), 8))
        while pending:
            progressed = False
            for service_name, service in list(pending.items()):
                if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}", service_name):
                    raise RuntimeError(f"Invalid Compose service name: {service_name}")
                if forbidden.intersection(service):
                    raise RuntimeError(
                        "Compose service requests forbidden host capabilities: "
                        + ", ".join(sorted(forbidden.intersection(service)))
                    )
                dependencies_value = service.get("depends_on") or []
                dependencies = (
                    set(dependencies_value)
                    if isinstance(dependencies_value, (list, dict))
                    else set()
                )
                if not dependencies.issubset(resolved):
                    continue
                volumes = service.get("volumes") or []
                binds = [
                    f"{host_root}:/workspace/app:ro",
                    f"{host_data}:/workspace/data:rw",
                ]
                for volume in volumes:
                    source, separator, destination = str(volume).partition(":")
                    if not separator or source.startswith(("/", ".", "~")) or "/" in source:
                        raise RuntimeError("Compose host paths are forbidden; use named volumes")
                    if not destination.startswith("/"):
                        raise RuntimeError("Compose volume destination must be absolute")
                    volume_root = host_data / "volumes" / source
                    controller_volume_root = controller_data / "volumes" / source
                    controller_volume_root.mkdir(parents=True, exist_ok=True, mode=0o777)
                    controller_volume_root.chmod(0o777)
                    binds.append(f"{volume_root}:{destination}:rw")
                build = service.get("build")
                image = str(service.get("image") or "").strip()
                dockerfile = "Dockerfile"
                if isinstance(build, dict):
                    context = str(build.get("context") or ".")
                    if context not in {".", "./"}:
                        raise RuntimeError("Compose build context must be the application root")
                    dockerfile = str(build.get("dockerfile") or "Dockerfile")
                elif isinstance(build, str) and build not in {".", "./"}:
                    raise RuntimeError("Compose build context must be the application root")
                if build is not None or not image:
                    image, build_logs = self._prepare_custom_image(
                        engine,
                        snapshot,
                        root,
                        image=None,
                        dockerfile=dockerfile,
                        suffix=service_name,
                    )
                else:
                    image, build_logs = self._prepare_custom_image(
                        engine, snapshot, root, image=image, suffix=service_name
                    )
                ports = service.get("ports") or service.get("expose") or []
                first_port = 8080
                if ports:
                    raw_port = str(ports[0]).split("/")[0].split(":")[-1]
                    first_port = int(raw_port)
                command_value = service.get("command")
                command = (
                    " ".join(str(item) for item in command_value)
                    if isinstance(command_value, list)
                    else str(command_value or "").strip()
                )
                replicas = route_replicas if service_name == route_service else 1
                urls: list[str] = []
                for replica in range(replicas):
                    name = (
                        f"warehouse-runtime-{str(snapshot['id']).replace('-', '')[:16]}-"
                        f"{service_name[:24]}-{replica}"
                    ).lower()
                    environment = {
                        **self._compose_environment(service.get("environment")),
                        **{
                            str(key): str(value)
                            for key, value in dict(
                                snapshot.get("runtime_environment") or {}
                            ).items()
                        },
                        "PORT": str(first_port),
                    }
                    spec: dict[str, object] = {
                        "Image": image,
                        "WorkingDir": str(service.get("working_dir") or "/workspace/app"),
                        "Env": [f"{key}={value}" for key, value in sorted(environment.items())],
                        "Labels": {
                            "org.bonfirework.managed": "runtime-controller",
                            "org.bonfirework.deployment": str(snapshot["id"]),
                            "org.bonfirework.workspace": str(snapshot["workspace_id"]),
                            "org.bonfirework.compose.service": service_name,
                        },
                        "ExposedPorts": {f"{first_port}/tcp": {}},
                        "HostConfig": {
                            "Binds": binds,
                            "NetworkMode": self.settings.runtime_docker_network,
                            "ReadonlyRootfs": True,
                            "Tmpfs": {"/tmp": "rw,noexec,nosuid,size=268435456"},
                            "CapDrop": ["ALL"],
                            "SecurityOpt": ["no-new-privileges:true"],
                            "Memory": 512 * 1024 * 1024,
                            "NanoCpus": 500_000_000,
                            "PidsLimit": 128,
                            "RestartPolicy": {"Name": "unless-stopped"},
                        },
                        "NetworkingConfig": {
                            "EndpointsConfig": {
                                self.settings.runtime_docker_network: {"Aliases": [service_name]}
                            }
                        },
                    }
                    if command:
                        spec["Cmd"] = ["sh", "-lc", command]
                    engine.remove(name)
                    engine.create(name=name, spec=spec)
                    engine.start(name)
                    created.append(name)
                    internal_url = f"http://{name}:{first_port}"
                    if service_name == route_service:
                        urls.append(internal_url)
                service_results[service_name] = {
                    "image": image,
                    "replicas": replicas,
                    "internal_urls": urls,
                    "build_log_excerpt": build_logs[-20:],
                }
                resolved.add(service_name)
                pending.pop(service_name)
                progressed = True
            if not progressed:
                raise RuntimeError("Compose dependencies contain a cycle or missing service")
        route_urls = list(service_results[route_service]["internal_urls"])
        health_path = str(requested.get("health_path") or "/health")
        for url in route_urls:
            try:
                self._wait_health(url + health_path, self.settings.runtime_health_timeout_seconds)
            except RuntimeError:
                if health_path != "/":
                    self._wait_health(url + "/", 10)
        return (
            {
                "runtime_kind": "container",
                "orchestration": "compose",
                "route_service": route_service,
                "internal_url": route_urls[0],
                "internal_urls": route_urls,
                "services": service_results,
                "health_path": health_path,
                "public_route": True,
            },
            created,
        )

    def execute(self, tenant_id: UUID, deployment_id: UUID) -> None:
        snapshot = self._snapshot(tenant_id, deployment_id)
        root, host_root, materialized = self._materialize(snapshot)
        requested = snapshot.get("requested_config") or {}
        execution_mode = str(requested.get("execution_mode") or "service").strip().lower()
        one_shot = execution_mode == "job"
        activation_requested = bool(requested.get("activate", True)) and not one_shot
        contract = snapshot.get("execution_contract") or {}
        health_path = str(
            requested.get("health_path")
            or contract.get("health_path")
            or ("/" if snapshot["runtime_family"] == "static" else "/health")
        )
        result: dict[str, object] = {
            "runtime_kind": snapshot["runtime_family"],
            "component_kind": snapshot["component_kind"],
            "public_route": str(snapshot["component_kind"]) not in {"worker", "agent"},
            "execution_mode": execution_mode,
            "activation_requested": activation_requested,
            "runtime_rel_path": materialized["runtime_rel_path"],
            "source_sha256": snapshot["sha256"],
            "archive": {
                key: value
                for key, value in materialized.items()
                if key not in {"runtime_rel_path", "runtime_bytes", "build"}
            },
        }
        compatibility = requested.get("compatibility_contract")
        if isinstance(compatibility, dict):
            result["compatibility"] = {
                "declared": True,
                "schema": compatibility.get("schema"),
                "contract_digest": compatibility.get("contract_digest"),
                "source_read_only": True,
                "persistent_data_path": "/workspace/data",
                "database_access": requested.get("database_access") or "runtime",
                "acceptance_required": bool(
                    (compatibility.get("deployment") or {}).get(
                        "require_acceptance_before_activation"
                    )
                ),
            }
        if materialized.get("build"):
            result["build"] = materialized["build"]
        container_names: list[str] = []
        if snapshot["runtime_family"] == "static":
            if not (root / "index.html").is_file():
                raise RuntimeError("Static Runtime requires index.html at the application root")
        else:
            data_path = (
                self.settings.hosted_runtime_data_root
                / "tenants"
                / str(tenant_id)
                / "workspaces"
                / str(snapshot["workspace_id"])
                / "data"
            )
            host_data = self.settings.runtime_host_data_root / data_path.relative_to(
                self.settings.hosted_runtime_data_root
            )
            data_path.mkdir(parents=True, exist_ok=True, mode=0o750)
            self._prepare_runtime_mounts(root, data_path)
            engine = DockerEngine(self.settings.runtime_docker_socket)
            try:
                is_compose = snapshot["runtime_family"] == "container" and (
                    requested.get("compose_file")
                    or Path(str(requested.get("entrypoint") or "")).name
                    in {
                        "compose.yaml",
                        "compose.yml",
                        "docker-compose.yaml",
                        "docker-compose.yml",
                    }
                )
                if is_compose:
                    compose_result, container_names = self._execute_compose(
                        engine, snapshot, root, host_root, data_path, host_data
                    )
                    result.update(compose_result)
                    health_path = str(compose_result.get("health_path") or health_path)
                else:
                    if snapshot["runtime_family"] == "container":
                        image, build_logs = self._prepare_custom_image(engine, snapshot, root)
                        snapshot["resolved_image"] = image
                        result["image"] = image
                        result["build_log_excerpt"] = build_logs[-20:]
                    name, spec, port, health_path = self._container_spec(
                        snapshot, host_root, host_data
                    )
                    replicas = (
                        max(
                            1,
                            min(
                                int((snapshot.get("hosting_policy") or {}).get("replicas") or 1),
                                8,
                            ),
                        )
                        if bool(result["public_route"])
                        else 1
                    )
                    accelerator = (snapshot.get("hosting_policy") or {}).get("accelerator")
                    if isinstance(accelerator, dict) and str(
                        accelerator.get("kind") or ""
                    ).lower() in {"gpu", "nvidia"}:
                        spec["HostConfig"]["DeviceRequests"] = [
                            {
                                "Driver": "nvidia",
                                "Count": int(accelerator.get("count") or 1),
                                "Capabilities": [["gpu"]],
                            }
                        ]
                    internal_urls = []
                    for replica in range(replicas):
                        replica_name = name if replicas == 1 else f"{name}-r{replica}"
                        engine.remove(replica_name)
                        engine.create(name=replica_name, spec=spec)
                        engine.start(replica_name)
                        container_names.append(replica_name)
                        if one_shot:
                            timeout_seconds = max(
                                30, min(int(requested.get("timeout_seconds") or 1200), 7200)
                            )
                            exit_code = engine.wait(replica_name, timeout=timeout_seconds)
                            job_logs = self._redact_runtime_logs(
                                snapshot, engine.logs(replica_name)
                            )
                            if exit_code != 0:
                                raise RuntimeError(
                                    f"Workspace job failed with exit code {exit_code}"
                                )
                            engine.remove(replica_name)
                            container_names.remove(replica_name)
                            result.update(
                                {
                                    "job": {
                                        "status": "succeeded",
                                        "exit_code": exit_code,
                                        "timeout_seconds": timeout_seconds,
                                    },
                                    "log_excerpt": job_logs,
                                }
                            )
                        elif bool(result["public_route"]):
                            internal_url = f"http://{replica_name}:{port}"
                            try:
                                self._wait_health(
                                    internal_url + health_path,
                                    self.settings.runtime_health_timeout_seconds,
                                )
                            except RuntimeError:
                                if health_path != "/":
                                    self._wait_health(internal_url + "/", 10)
                            internal_urls.append(internal_url)
                        else:
                            self._wait_process(engine, replica_name)
                    if bool(result["public_route"]):
                        result.update(
                            {
                                "container_names": container_names,
                                "internal_url": internal_urls[0],
                                "internal_urls": internal_urls,
                                "replicas": replicas,
                                "load_balancing": "stable_request_hash",
                                "health_path": health_path,
                            }
                        )
                    elif not one_shot:
                        result.update(
                            {
                                "container_names": container_names,
                                "process_health": "running",
                            }
                        )
            except Exception:
                log_excerpt = []
                for failed_name in container_names[-16:]:
                    log_excerpt.extend(engine.logs(failed_name))
                log_excerpt = self._redact_runtime_logs(snapshot, log_excerpt)
                if log_excerpt:
                    result["log_excerpt"] = log_excerpt
                    with tenant_session(tenant_id) as session:
                        session.execute(
                            text(
                                """
                                UPDATE digital_asset.deployments
                                SET result=result || CAST(:logs AS jsonb)
                                WHERE id=:id
                                """
                            ),
                            {
                                "id": deployment_id,
                                "logs": json.dumps({"log_excerpt": log_excerpt}),
                            },
                        )
                try:
                    for failed_name in container_names:
                        engine.remove(failed_name)
                except Exception:
                    pass
                raise
            finally:
                engine.close()

        with tenant_session(tenant_id) as session:
            database_release = observe_database_release_gate(
                session, snapshot["workspace_id"]
            )
        result["database_release"] = database_release
        if activation_requested and not bool(database_release["ready"]):
            if container_names:
                engine = DockerEngine(self.settings.runtime_docker_socket)
                try:
                    for container_name in container_names:
                        engine.remove(container_name)
                finally:
                    engine.close()
            raise RuntimeError(
                "Database release gate blocked activation: "
                + ", ".join(str(item) for item in database_release.get("blockers", []))
            )

        storage_measurement = measure_workspace_runtime_storage(
            self.settings,
            tenant_id=tenant_id,
            workspace_id=snapshot["workspace_id"],
        )
        result["occupancy"] = {
            "runtime_release_bytes": storage_measurement["runtime_release_bytes"],
            "data_volume_bytes": storage_measurement["data_volume_bytes"],
            "measured_at": storage_measurement["measured_at"],
            "measurement_status": storage_measurement["measurement_status"],
        }

        with tenant_session(tenant_id) as session:
            current = session.execute(
                text(
                    "SELECT active_deployment_id FROM digital_asset.workspaces "
                    "WHERE id=:id FOR UPDATE"
                ),
                {"id": snapshot["workspace_id"]},
            ).scalar_one_or_none()
            result["previous_active_deployment_id"] = str(current) if current else None
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET status='ready', health='healthy', result=CAST(:result AS jsonb),
                        runtime_state=CASE
                          WHEN CAST(:dynamic_runtime AS boolean) THEN 'running'
                          ELSE 'not_applicable'
                        END,
                        runtime_last_request_at=CASE
                          WHEN CAST(:dynamic_runtime AS boolean) THEN now()
                          ELSE NULL
                        END,
                        runtime_wake_requested_at=NULL, runtime_suspended_at=NULL,
                        runtime_state_changed_at=now(), runtime_wake_error=NULL,
                        lease_owner=NULL, lease_expires_at=NULL, completed_at=now()
                    WHERE id=:id AND lease_owner=:worker;
                    """
                ),
                {
                    "result": json.dumps(result, default=str),
                    "dynamic_runtime": bool(container_names)
                    and bool(result["public_route"])
                    and not one_shot,
                    "id": deployment_id,
                    "worker": self.worker_id,
                },
            )
            if activation_requested:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET active_deployment_id=:deployment_id, runtime_status='ready'
                        WHERE id=:workspace_id;
                        """
                    ),
                    {"deployment_id": deployment_id, "workspace_id": snapshot["workspace_id"]},
                )
                set_pages_deployment_pointer(
                    session,
                    tenant_id=tenant_id,
                    workspace_id=snapshot["workspace_id"],
                    deployment_id=deployment_id,
                )
            else:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET runtime_status=CASE
                          WHEN active_deployment_id IS NULL THEN 'provisioned' ELSE 'ready'
                        END
                        WHERE id=:workspace_id
                        """
                    ),
                    {"workspace_id": snapshot["workspace_id"]},
                )
            session.execute(
                text("UPDATE digital_asset.workspace_components SET status='ready' WHERE id=:id"),
                {"id": snapshot["component_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspace_usage
                    SET runtime_bytes=:runtime_bytes,
                        data_volume_bytes=:data_volume_bytes,
                        measured_at=:measured_at,
                        revision=revision+1
                    WHERE workspace_id=:workspace_id
                    """
                ),
                {
                    "runtime_bytes": storage_measurement["runtime_release_bytes"],
                    "data_volume_bytes": storage_measurement["data_volume_bytes"],
                    "measured_at": storage_measurement["measured_at"],
                    "workspace_id": snapshot["workspace_id"],
                },
            )
            _event(
                session,
                deployment_id,
                tenant_id,
                "health_verified",
                {"provider": "warehouse_runtime_v1"},
            )
            if activation_requested and bool(result["public_route"]):
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "route_activated",
                    {"public_url": snapshot["public_url"]},
                )

        if one_shot:
            with tenant_session(tenant_id) as session:
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "job_completed",
                    {"exit_code": 0, "production_traffic_changed": False},
                )
            return

        if not bool(result["public_route"]):
            with tenant_session(tenant_id) as session:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments
                        SET result=result || jsonb_build_object(
                          'public_route_verified', false,
                          'runtime_process_verified', true
                        ) WHERE id=:id
                        """
                    ),
                    {"id": deployment_id},
                )
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "runtime_process_verified",
                    {"component_kind": snapshot["component_kind"]},
                )
            return

        if not activation_requested:
            with tenant_session(tenant_id) as session:
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments
                        SET result=result || jsonb_build_object(
                          'public_route_verified', false,
                          'activation_deferred', true
                        ) WHERE id=:id
                        """
                    ),
                    {"id": deployment_id},
                )
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "ready_for_activation",
                    {"production_traffic_changed": False},
                )
            return

        try:
            self._wait_public_route(
                str(snapshot["public_url"]),
                deployment_id,
                health_path,
                20,
            )
        except Exception:
            with tenant_session(tenant_id) as session:
                previous = result.get("previous_active_deployment_id")
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET active_deployment_id=CAST(:previous AS uuid),
                            runtime_status=CASE
                              WHEN CAST(:previous AS uuid) IS NULL THEN 'failed' ELSE 'ready'
                            END
                        WHERE id=:workspace_id
                        """
                    ),
                    {"previous": previous, "workspace_id": snapshot["workspace_id"]},
                )
                set_pages_deployment_pointer(
                    session,
                    tenant_id=tenant_id,
                    workspace_id=snapshot["workspace_id"],
                    deployment_id=previous,
                )
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments
                        SET status='failed', health='unhealthy',
                            result=result || jsonb_build_object(
                              'public_route_verified', false
                            )
                        WHERE id=:id
                        """
                    ),
                    {"id": deployment_id},
                )
                _event(session, deployment_id, tenant_id, "public_route_failed", {})
            if container_names:
                engine = DockerEngine(self.settings.runtime_docker_socket)
                try:
                    for container_name in container_names:
                        engine.remove(container_name)
                finally:
                    engine.close()
            raise
        with tenant_session(tenant_id) as session:
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET result=result || jsonb_build_object(
                      'public_route_verified', true
                    )
                    WHERE id=:id
                    """
                ),
                {"id": deployment_id},
            )
            _event(
                session,
                deployment_id,
                tenant_id,
                "public_route_verified",
                {"url": snapshot["public_url"]},
            )

    def fail(self, tenant_id: UUID, deployment_id: UUID, exc: Exception) -> None:
        message = str(exc).strip()[:1000] or exc.__class__.__name__
        with tenant_session(tenant_id) as session:
            row = (
                session.execute(
                    text(
                        "SELECT workspace_id, component_id "
                        "FROM digital_asset.deployments WHERE id=:id"
                    ),
                    {"id": deployment_id},
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return
            session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET status='failed', health='unhealthy', completed_at=now(),
                        lease_owner=NULL, lease_expires_at=NULL,
                        result=result || CAST(:failure AS jsonb)
                    WHERE id=:id
                    """
                ),
                {"id": deployment_id, "failure": json.dumps({"error": message})},
            )
            session.execute(
                text("UPDATE digital_asset.workspace_components SET status='failed' WHERE id=:id"),
                {"id": row["component_id"]},
            )
            session.execute(
                text(
                    """
                    UPDATE digital_asset.workspaces
                    SET runtime_status=CASE
                      WHEN active_deployment_id IS NULL THEN 'failed' ELSE 'ready'
                    END
                    WHERE id=:id
                    """
                ),
                {"id": row["workspace_id"]},
            )
            _event(session, deployment_id, tenant_id, "failed", {"error": message})

    @staticmethod
    def _runtime_container_names(result: object) -> list[str]:
        payload = dict(result) if isinstance(result, dict) else {}
        return [
            str(value)
            for value in payload.get("container_names") or []
            if re.fullmatch(r"warehouse-runtime-[a-zA-Z0-9_.-]+", str(value))
        ]

    def _runtime_lifecycle_candidates(self) -> list[tuple[UUID, dict[str, object]]]:
        candidates: list[tuple[UUID, dict[str, object]]] = []
        idle_seconds = max(60, int(self.settings.runtime_idle_timeout_seconds))
        for tenant_id in self._tenants():
            with tenant_session(tenant_id) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT d.id AS deployment_id,d.runtime_state,
                               d.runtime_last_request_at,d.result
                        FROM digital_asset.workspaces AS w
                        JOIN digital_asset.deployments AS d
                          ON d.workspace_id=w.id
                        WHERE d.status='ready' AND d.health='healthy'
                          AND d.runtime_state != 'not_applicable'
                          AND d.result->>'runtime_kind' IN ('python','node','container')
                          AND COALESCE((d.result->>'public_route')::boolean,true)
                          AND COALESCE(d.result->>'execution_mode','service')='service'
                          AND (
                            d.runtime_state IN (
                              'wake_requested','waking','suspending'
                            )
                            OR (
                              d.runtime_state='running'
                              AND d.runtime_last_request_at
                                < now() - make_interval(secs => :idle_seconds)
                            )
                          )
                        ORDER BY
                          CASE WHEN d.runtime_state IN ('wake_requested','waking')
                            THEN 0 ELSE 1 END,
                          d.runtime_last_request_at NULLS FIRST
                        LIMIT 32
                        """
                    ),
                    {"idle_seconds": idle_seconds},
                ).mappings()
                candidates.extend((tenant_id, dict(row)) for row in rows)
        return candidates

    def _record_runtime_lifecycle_error(
        self,
        tenant_id: UUID,
        deployment_id: UUID,
        exc: Exception,
    ) -> None:
        message = (str(exc).strip() or exc.__class__.__name__)[:1000]
        with tenant_session(tenant_id) as session:
            updated = session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET runtime_state='error',runtime_state_changed_at=now(),
                        runtime_wake_error=:error
                    WHERE id=:id AND runtime_state IN ('waking','suspending')
                    RETURNING id
                    """
                ),
                {"id": deployment_id, "error": message},
            ).scalar_one_or_none()
            if updated is not None:
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "runtime_lifecycle_error",
                    {"error": message, "worker": self.worker_id},
                )

    def _wake_runtime(
        self,
        engine: DockerEngine,
        tenant_id: UUID,
        deployment_id: UUID,
    ) -> bool:
        with tenant_session(tenant_id) as session:
            result = session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET runtime_state='waking',runtime_state_changed_at=now(),
                        runtime_wake_error=NULL
                    WHERE id=:id
                      AND runtime_state IN ('wake_requested','waking')
                    RETURNING result
                    """
                ),
                {"id": deployment_id},
            ).scalar_one_or_none()
        if result is None:
            return False
        payload = dict(result) if isinstance(result, dict) else {}
        names = self._runtime_container_names(payload)
        if not names:
            raise RuntimeError("Hosted Runtime wake has no managed containers")
        for name in names:
            if not engine.container_exists(name):
                raise RuntimeError(f"Hosted Runtime wake container is missing: {name}")
            if not bool(engine.state(name)["running"]):
                engine.start(name)
        health_path = str(payload.get("health_path") or "/health")
        health_timeout = max(1, int(self.settings.runtime_wake_health_timeout_seconds))
        urls = [
            str(value).rstrip("/")
            for value in payload.get("internal_urls") or [payload.get("internal_url")]
            if value
        ]
        if not urls:
            raise RuntimeError("Hosted Runtime wake has no health-check upstream")
        for url in urls:
            try:
                self._wait_health(url + health_path, health_timeout)
            except RuntimeError:
                if health_path == "/":
                    raise
                self._wait_health(url + "/", min(10, health_timeout))
        with tenant_session(tenant_id) as session:
            updated = session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET runtime_state='running',runtime_state_changed_at=now(),
                        runtime_last_request_at=now(),runtime_suspended_at=NULL,
                        runtime_wake_error=NULL
                    WHERE id=:id AND runtime_state='waking'
                    RETURNING id
                    """
                ),
                {"id": deployment_id},
            ).scalar_one_or_none()
            if updated is not None:
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "runtime_woke",
                    {"container_names": names, "worker": self.worker_id},
                )
        return updated is not None

    def _suspend_runtime(
        self,
        engine: DockerEngine,
        tenant_id: UUID,
        deployment_id: UUID,
    ) -> bool:
        idle_seconds = max(60, int(self.settings.runtime_idle_timeout_seconds))
        with tenant_session(tenant_id) as session:
            result = session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET runtime_state='suspending',runtime_state_changed_at=now(),
                        runtime_wake_error=NULL
                    WHERE id=:id AND (
                      runtime_state='suspending'
                      OR (
                        runtime_state='running'
                        AND runtime_last_request_at
                          < now() - make_interval(secs => :idle_seconds)
                      )
                    )
                    RETURNING result
                    """
                ),
                {"id": deployment_id, "idle_seconds": idle_seconds},
            ).scalar_one_or_none()
        if result is None:
            return False
        names = self._runtime_container_names(result)
        if not names:
            raise RuntimeError("Hosted Runtime suspend has no managed containers")
        for name in reversed(names):
            if engine.container_exists(name) and bool(engine.state(name)["running"]):
                engine.stop(name)
        with tenant_session(tenant_id) as session:
            updated = session.execute(
                text(
                    """
                    UPDATE digital_asset.deployments
                    SET runtime_state='suspended',runtime_suspended_at=now(),
                        runtime_state_changed_at=now(),runtime_wake_error=NULL
                    WHERE id=:id AND runtime_state='suspending'
                    RETURNING id
                    """
                ),
                {"id": deployment_id},
            ).scalar_one_or_none()
            if updated is not None:
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "runtime_suspended",
                    {
                        "container_names": names,
                        "idle_timeout_seconds": idle_seconds,
                        "worker": self.worker_id,
                    },
                )
        return updated is not None

    def reconcile_runtime_lifecycle(self) -> int:
        """Stop idle dynamic runtimes and wake them in place on gateway demand."""

        scan_seconds = max(0.25, float(self.settings.runtime_lifecycle_scan_seconds))
        if time.monotonic() - self._last_runtime_lifecycle_reconcile < scan_seconds:
            return 0
        self._last_runtime_lifecycle_reconcile = time.monotonic()
        candidates = self._runtime_lifecycle_candidates()
        actionable = [
            (tenant_id, row)
            for tenant_id, row in candidates
            if row.get("runtime_state") in {"wake_requested", "waking"}
            or (
                self.settings.runtime_idle_suspend_enabled
                and row.get("runtime_state") in {"running", "suspending"}
            )
        ]
        if not actionable:
            return 0
        engine = DockerEngine(self.settings.runtime_docker_socket)
        changed = 0
        try:
            for tenant_id, row in actionable:
                deployment_id = UUID(str(row["deployment_id"]))
                try:
                    if row.get("runtime_state") in {"wake_requested", "waking"}:
                        changed += int(self._wake_runtime(engine, tenant_id, deployment_id))
                    else:
                        changed += int(self._suspend_runtime(engine, tenant_id, deployment_id))
                except Exception as exc:
                    self._record_runtime_lifecycle_error(tenant_id, deployment_id, exc)
        finally:
            engine.close()
        return changed

    def _runtime_drift_candidates(self) -> list[tuple[UUID, UUID, list[str]]]:
        candidates: list[tuple[UUID, UUID, list[str]]] = []
        for tenant_id in self._tenants():
            with tenant_session(tenant_id) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT d.id AS deployment_id,d.result
                        FROM digital_asset.workspaces AS w
                        JOIN digital_asset.deployments AS d
                          ON d.id=w.active_deployment_id
                        WHERE d.status='ready' AND d.health='healthy'
                          AND d.runtime_profile_key IS NOT NULL
                        ORDER BY d.completed_at NULLS LAST,d.created_at
                        """
                    )
                ).mappings()
                for row in rows:
                    result = dict(row["result"]) if isinstance(row.get("result"), dict) else {}
                    names = [
                        str(value)
                        for value in result.get("container_names") or []
                        if re.fullmatch(r"warehouse-runtime-[a-zA-Z0-9_.-]+", str(value))
                    ]
                    if names:
                        candidates.append(
                            (tenant_id, UUID(str(row["deployment_id"])), names)
                        )
                    if len(candidates) >= 8:
                        return candidates
        return candidates

    def reconcile_runtime_drift(self) -> int:
        """Requeue an active healthy deployment when a managed container vanished."""

        if time.monotonic() - self._last_runtime_drift_reconcile < 15:
            return 0
        self._last_runtime_drift_reconcile = time.monotonic()
        candidates = self._runtime_drift_candidates()
        if not candidates:
            return 0
        missing_by_deployment: list[tuple[UUID, UUID, list[str]]] = []
        engine = DockerEngine(self.settings.runtime_docker_socket)
        try:
            for tenant_id, deployment_id, names in candidates:
                missing = [name for name in names if not engine.container_exists(name)]
                if missing:
                    missing_by_deployment.append((tenant_id, deployment_id, missing))
        finally:
            engine.close()

        repaired = 0
        for tenant_id, deployment_id, missing in missing_by_deployment:
            with tenant_session(tenant_id) as session:
                queued = session.execute(
                    text(
                        """
                        UPDATE digital_asset.deployments AS deployment
                        SET status='queued',health='pending',lease_owner=NULL,
                            lease_expires_at=NULL,started_at=NULL,completed_at=NULL
                        WHERE deployment.id=:deployment_id
                          AND deployment.status='ready'
                          AND deployment.health='healthy'
                          AND EXISTS (
                            SELECT 1 FROM digital_asset.workspaces AS workspace
                            WHERE workspace.active_deployment_id=deployment.id
                          )
                        RETURNING deployment.id
                        """
                    ),
                    {"deployment_id": deployment_id},
                ).scalar_one_or_none()
                if queued is None:
                    continue
                session.execute(
                    text(
                        """
                        UPDATE digital_asset.workspaces
                        SET runtime_status='building'
                        WHERE active_deployment_id=:deployment_id
                        """
                    ),
                    {"deployment_id": deployment_id},
                )
                _event(
                    session,
                    deployment_id,
                    tenant_id,
                    "self_heal_queued",
                    {
                        "reason": "managed_runtime_container_missing",
                        "missing_container_names": missing,
                        "worker": self.worker_id,
                    },
                )
                repaired += 1
        return repaired

    def _resident_runtime_container_names(self) -> set[str]:
        names: set[str] = set()
        for tenant_id in self._tenants():
            with tenant_session(tenant_id) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT d.result
                        FROM digital_asset.workspaces AS w
                        JOIN digital_asset.deployments AS d
                          ON d.id=w.active_deployment_id
                        WHERE d.status='ready' AND d.health='healthy'
                          AND d.runtime_state IN (
                            'wake_requested','waking','running','suspending'
                          )
                        """
                    )
                ).scalars()
                for result in rows:
                    names.update(self._runtime_container_names(result))
        return names

    def reconcile_orphan_runtime_containers(self) -> int:
        """Stop stale managed runtimes without removing rollback artifacts."""

        if time.monotonic() - self._last_runtime_orphan_reconcile < 15:
            return 0
        self._last_runtime_orphan_reconcile = time.monotonic()
        resident_names = self._resident_runtime_container_names()
        engine = DockerEngine(self.settings.runtime_docker_socket)
        stopped = 0
        try:
            for container in engine.managed_runtime_containers():
                name = str(container.get("name") or "")
                if (
                    container.get("running") is True
                    and name
                    and name not in resident_names
                ):
                    engine.stop(name)
                    stopped += 1
        finally:
            engine.close()
        return stopped

    def _scaling_candidates(self) -> list[tuple[UUID, dict[str, object]]]:
        candidates: list[tuple[UUID, dict[str, object]]] = []
        for tenant_id in self._tenants():
            with tenant_session(tenant_id) as session:
                rows = session.execute(
                    text(
                        """
                        SELECT d.id AS deployment_id,d.result,p.runtime_family,
                               c.component_name,r.id AS resource_id,
                               r.desired_state,r.observed_state
                        FROM digital_asset.workspaces AS w
                        JOIN digital_asset.deployments AS d
                          ON d.id=w.active_deployment_id
                        JOIN digital_asset.workspace_components AS c
                          ON c.id=d.component_id
                        JOIN platform.runtime_profiles AS p
                          ON p.profile_key=d.runtime_profile_key
                        JOIN digital_asset.hosting_resources AS r
                          ON r.workspace_id=w.id AND r.resource_kind='scaling'
                         AND r.status='ready'
                        WHERE d.status='ready' AND d.health='healthy'
                          AND d.runtime_state='running'
                          AND (r.desired_state->>'component' IN (c.component_name,'*'))
                        """
                    )
                ).mappings()
                candidates.extend((tenant_id, dict(row)) for row in rows)
        return candidates

    @staticmethod
    def _cooldown_elapsed(row: dict[str, object], desired: dict[str, object]) -> bool:
        observed = row.get("observed_state")
        if not isinstance(observed, dict) or not observed.get("last_scaled_at"):
            return True
        try:
            last = datetime.fromisoformat(str(observed["last_scaled_at"]))
            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)
        except ValueError:
            return True
        return datetime.now(UTC) - last >= timedelta(
            seconds=int(desired.get("cooldown_seconds") or 60)
        )

    def reconcile_scaling(self) -> None:
        """Reconcile observed CPU against database-backed scaling policies."""

        if time.monotonic() - self._last_scaling_reconcile < 15:
            return
        self._last_scaling_reconcile = time.monotonic()
        candidates = self._scaling_candidates()
        if not candidates:
            return
        engine = DockerEngine(self.settings.runtime_docker_socket)
        try:
            for tenant_id, row in candidates:
                desired = (
                    dict(row["desired_state"]) if isinstance(row.get("desired_state"), dict) else {}
                )
                result = dict(row["result"]) if isinstance(row.get("result"), dict) else {}
                names = [str(value) for value in result.get("container_names") or [] if value]
                urls = [str(value) for value in result.get("internal_urls") or [] if value]
                compose = result.get("orchestration") == "compose"
                route_names = (
                    [str(urlsplit(url).hostname) for url in urls if urlsplit(url).hostname]
                    if compose
                    else list(names)
                )
                if not route_names:
                    observation = {
                        "reconciler": "runtime_controller",
                        "reason": "non_container_runtime_or_missing_route",
                        "replicas": 0,
                        "observed_at": datetime.now(UTC).isoformat(),
                    }
                    with tenant_session(tenant_id) as session:
                        session.execute(
                            text(
                                "UPDATE digital_asset.hosting_resources "
                                "SET observed_state=CAST(:value AS jsonb) WHERE id=:id"
                            ),
                            {"id": row["resource_id"], "value": json.dumps(observation)},
                        )
                    continue
                samples = [engine.stats(name) for name in route_names]
                cpu_percent = sum(sample["cpu_percent"] for sample in samples) / len(samples)
                memory_percent = sum(sample["memory_percent"] for sample in samples) / len(samples)
                minimum = max(1, int(desired.get("min_replicas") or 1))
                maximum = min(8, max(minimum, int(desired.get("max_replicas") or minimum)))
                target = int(desired.get("target_cpu_percent") or 70)
                current = len(route_names)
                target_replicas = current
                if self._cooldown_elapsed(row, desired):
                    if cpu_percent > target and current < maximum:
                        target_replicas = current + 1
                    elif cpu_percent < target * 0.35 and current > minimum:
                        target_replicas = current - 1
                observation = {
                    "cpu_percent": round(cpu_percent, 3),
                    "memory_percent": round(memory_percent, 3),
                    "replicas": current,
                    "target_replicas": target_replicas,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "strategy": "cpu_target_with_cooldown",
                    "load_balancing": "stable_request_hash",
                }
                if target_replicas > current:
                    if compose:
                        route_service = str(result.get("route_service") or "web")
                        base = re.sub(r"-\d+$", "", route_names[0])
                        spec = engine.replica_spec(route_names[0], network_alias=route_service)
                        parsed_route = urlsplit(urls[0])
                        port = parsed_route.port or 8080
                        health_path = str(result.get("health_path") or "/health")
                    else:
                        deployment_id = UUID(str(row["deployment_id"]))
                        snapshot = self._snapshot(tenant_id, deployment_id)
                        _root, host_root, _materialized = self._materialize(snapshot)
                        data_path = (
                            self.settings.hosted_runtime_data_root
                            / "tenants"
                            / str(tenant_id)
                            / "workspaces"
                            / str(snapshot["workspace_id"])
                            / "data"
                        )
                        host_data = self.settings.runtime_host_data_root / data_path.relative_to(
                            self.settings.hosted_runtime_data_root
                        )
                        if result.get("image"):
                            snapshot["resolved_image"] = result["image"]
                        base, spec, port, health_path = self._container_spec(
                            snapshot, host_root, host_data
                        )
                        accelerator = (snapshot.get("hosting_policy") or {}).get("accelerator")
                        if isinstance(accelerator, dict):
                            spec["HostConfig"]["DeviceRequests"] = [
                                {
                                    "Driver": "nvidia",
                                    "Count": int(accelerator.get("count") or 1),
                                    "Capabilities": [["gpu"]],
                                }
                            ]
                    suffix = 1
                    while f"{base}-r{suffix}" in names:
                        suffix += 1
                    replica_name = f"{base}-r{suffix}"
                    engine.remove(replica_name)
                    engine.create(name=replica_name, spec=spec)
                    engine.start(replica_name)
                    internal_url = f"http://{replica_name}:{port}"
                    try:
                        self._wait_health(internal_url + health_path, 30)
                    except RuntimeError:
                        if health_path != "/":
                            self._wait_health(internal_url + "/", 10)
                    names.append(replica_name)
                    route_names.append(replica_name)
                    urls.append(internal_url)
                    observation["last_scaled_at"] = datetime.now(UTC).isoformat()
                    observation["decision"] = "scale_up"
                elif target_replicas < current:
                    replica_name = route_names.pop()
                    engine.remove(replica_name)
                    if replica_name in names:
                        names.remove(replica_name)
                    if urls:
                        urls.pop()
                    observation["last_scaled_at"] = datetime.now(UTC).isoformat()
                    observation["decision"] = "scale_down"
                services = dict(result.get("services") or {})
                if compose and services:
                    route_service = str(result.get("route_service") or "web")
                    route_observation = dict(services.get(route_service) or {})
                    route_observation.update({"replicas": len(route_names), "internal_urls": urls})
                    services[route_service] = route_observation
                with tenant_session(tenant_id) as session:
                    session.execute(
                        text(
                            "UPDATE digital_asset.hosting_resources SET "
                            "observed_state=CAST(:observation AS jsonb) WHERE id=:resource_id"
                        ),
                        {
                            "resource_id": row["resource_id"],
                            "observation": json.dumps(observation),
                        },
                    )
                    if target_replicas != current:
                        session.execute(
                            text(
                                "UPDATE digital_asset.deployments SET result=result || "
                                "CAST(:result AS jsonb) WHERE id=:deployment_id"
                            ),
                            {
                                "deployment_id": row["deployment_id"],
                                "result": json.dumps(
                                    {
                                        "container_names": names,
                                        "internal_url": urls[0],
                                        "internal_urls": urls,
                                        "replicas": len(route_names),
                                        "services": services,
                                    }
                                ),
                            },
                        )
                        _event(
                            session,
                            UUID(str(row["deployment_id"])),
                            tenant_id,
                            "autoscaled",
                            observation,
                        )
        finally:
            engine.close()

    def run_once(self) -> bool:
        claimed = self.claim()
        if claimed is None:
            return False
        tenant_id, deployment_id = claimed
        try:
            self.execute(tenant_id, deployment_id)
        except Exception as exc:
            self.fail(tenant_id, deployment_id, exc)
        return True

    def run_forever(self) -> None:
        marker = Path("/tmp/runtime-controller-ready")
        while True:
            marker.write_text(f"{self.worker_id} {datetime.now(UTC).isoformat()}", encoding="utf-8")
            try:
                self.observe_capacity()
                self.reconcile_runtime_lifecycle()
                self.reconcile_runtime_drift()
                self.reconcile_orphan_runtime_containers()
                self.reconcile_scaling()
                self.reconcile_repositories()
                worked = self.run_once()
                self.heartbeat(claimed=worked, successful=True)
                if not worked:
                    time.sleep(max(0.25, self.settings.runtime_controller_poll_seconds))
            except Exception as exc:
                traceback.print_exc()
                try:
                    self.heartbeat(status="degraded", error=str(exc))
                except Exception:
                    traceback.print_exc()
                time.sleep(max(1.0, self.settings.runtime_controller_poll_seconds))


def main() -> None:
    settings = get_settings()
    if not settings.runtime_controller_enabled:
        raise SystemExit("WAREHOUSE_RUNTIME_CONTROLLER_ENABLED is false")
    RuntimeController(settings).run_forever()


if __name__ == "__main__":
    main()
