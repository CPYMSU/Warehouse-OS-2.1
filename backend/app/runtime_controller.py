"""Compatibility-hardened Runtime Controller entrypoint.

This module adds a real build/run boundary for inferred Python and Node
workloads, elastic primary-key materialisation and structured failure evidence
without widening the Runtime Controller's Docker authority.
"""

from __future__ import annotations

import hashlib
import json
import shlex
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy import text

from app import runtime_controller_base as base
from app.services.workspace_autonomy import allocation_target_bytes

DockerEngine = base.DockerEngine
httpx = base.httpx
reconcile_repository_resources = base.reconcile_repository_resources
_python_api_launcher_source = base._python_api_launcher_source


def _node_static_server_source() -> str:
    return (
        "const http=require('http'),fs=require('fs'),path=require('path');"
        "const root=path.resolve(process.env.WAREHOUSE_STATIC_ROOT);"
        "const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8',"
        "'.mjs':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8',"
        "'.json':'application/json; charset=utf-8','.svg':'image/svg+xml',"
        "'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp',"
        "'.woff':'font/woff','.woff2':'font/woff2'};"
        "http.createServer((req,res)=>{const u=new URL(req.url,'http://runtime');"
        "if(u.pathname==='/health'||u.pathname==='/healthz'){"
        "res.writeHead(200,{'content-type':'application/json'});"
        'return res.end(\'{"status":"ok"}\');}'
        "let decoded;try{decoded=decodeURIComponent(u.pathname)}"
        "catch(e){res.writeHead(400);return res.end();}"
        "let target=path.resolve(root,'.'+decoded);"
        "if(target!==root&&!target.startsWith(root+path.sep)){"
        "res.writeHead(403);return res.end();}"
        "if(fs.existsSync(target)&&fs.statSync(target).isDirectory())"
        "target=path.join(target,'index.html');"
        "if(!fs.existsSync(target))target=path.join(root,'index.html');"
        "fs.readFile(target,(error,body)=>{if(error){res.writeHead(404);"
        "return res.end('Not found');}res.writeHead(200,{"
        "'content-type':mime[path.extname(target).toLowerCase()]||'application/octet-stream'});"
        "res.end(body);});}).listen(Number(process.env.PORT),'0.0.0.0');"
    )


def _configured_command(snapshot: dict[str, object], key: str) -> str:
    return str((snapshot.get("requested_config") or {}).get(key) or snapshot.get(key) or "").strip()


def _managed_python_venv(snapshot: dict[str, object]) -> str:
    digest = str(snapshot.get("managed_build_digest") or "").strip().lower()
    if not digest or any(character not in "0123456789abcdef" for character in digest):
        raise RuntimeError("Managed Python build digest is unavailable")
    return f"/workspace/data/.runtime/python/{digest}/venv"


def _node_command(snapshot: dict[str, object]) -> str:
    digest = hashlib.sha256(
        f"{snapshot.get('sha256') or snapshot['id']}:{snapshot.get('image_ref') or ''}".encode()
    ).hexdigest()[:24]
    entrypoint = shlex.quote(str(snapshot.get("entrypoint") or "").strip())
    server_source = shlex.quote(_node_static_server_source())
    if snapshot.get("managed_build"):
        setup = (
            "set -eu; cd /workspace/app; "
            "mkdir -p /workspace/data/.runtime/npm-cache /workspace/data/.runtime/home; "
            "export npm_config_cache=/workspace/data/.runtime/npm-cache; "
            "export HOME=/workspace/data/.runtime/home; "
        )
        source_root = "/workspace/app"
    else:
        setup = (
            "set -eu; "
            f"RUNTIME_NODE_ROOT=/workspace/data/.runtime/node/{digest}; "
            'SOURCE_ROOT="$RUNTIME_NODE_ROOT/source"; '
            "mkdir -p /workspace/data/.runtime/npm-cache /workspace/data/.runtime/home; "
            "export npm_config_cache=/workspace/data/.runtime/npm-cache; "
            "export HOME=/workspace/data/.runtime/home; "
            'if [ ! -f "$RUNTIME_NODE_ROOT/.deps-ready" ]; then '
            'rm -rf "$RUNTIME_NODE_ROOT"; mkdir -p "$SOURCE_ROOT"; '
            'cp -a /workspace/app/. "$SOURCE_ROOT/"; cd "$SOURCE_ROOT"; '
            "if [ -f package-lock.json ]; then npm ci; else npm install; fi; "
            'touch "$RUNTIME_NODE_ROOT/.deps-ready"; fi; cd "$SOURCE_ROOT"; '
            "if node -e \"const p=require('./package.json');"
            'process.exit(p.scripts&&p.scripts.build?0:1)"; then '
            'if [ ! -f "$RUNTIME_NODE_ROOT/.build-ready" ]; then npm run build; '
            'touch "$RUNTIME_NODE_ROOT/.build-ready"; fi; fi; '
        )
        source_root = "$SOURCE_ROOT"
    return (
        setup + "if node -e \"const p=require('./package.json');"
        'process.exit(p.scripts&&p.scripts.start?0:1)"; then exec npm start; fi; '
        'for OUTPUT in dist build public; do if [ -f "$OUTPUT/index.html" ]; then '
        f'export WAREHOUSE_STATIC_ROOT="{source_root}/$OUTPUT"; '
        f"exec node -e {server_source}; fi; done; "
        "MAIN=\"$(node -p \"require('./package.json').main||''\" 2>/dev/null || true)\"; "
        'if [ -n "$MAIN" ] && [ -f "$MAIN" ]; then exec node "$MAIN"; fi; '
        f'ENTRY={entrypoint}; if [ -n "$ENTRY" ] && [ -f "$ENTRY" ]; '
        'then exec node "$ENTRY"; fi; '
        'for ENTRY in server.js index.js app.js; do if [ -f "$ENTRY" ]; '
        'then exec node "$ENTRY"; fi; done; '
        "echo 'No runnable Node start script, build output, main field or entrypoint was found' "
        ">&2; exit 64"
    )


def _diagnostic(exc: Exception) -> dict[str, object]:
    message = str(exc).strip()[:1000] or exc.__class__.__name__
    lowered = message.lower()
    if "digest" in lowered or "source object" in lowered or "archive" in lowered:
        values = (
            "source.materialize",
            "source",
            "source_materialization_failed",
            "verify the archive and upload a new immutable source version",
        )
    elif "quota" in lowered or "storage" in lowered:
        values = (
            "storage.allocate",
            "storage",
            "workspace_storage_failed",
            "inspect usage and retry after capacity is available",
        )
    elif any(token in lowered for token in ("npm", "pip", "build", "docker image")):
        values = (
            "runtime.build",
            "build",
            "runtime_build_failed",
            "open redacted logs, correct dependencies or build commands, then redeploy",
        )
    elif "database" in lowered or "postgres" in lowered:
        values = (
            "database.connect",
            "database",
            "workspace_database_unavailable",
            "verify the database binding and rerun its connectivity probe",
        )
    elif "public runtime route" in lowered or "public route" in lowered:
        values = (
            "route.verify",
            "public_route",
            "public_route_verification_failed",
            "inspect proxy and health-path evidence; the previous revision remains active",
        )
    elif "health probe" in lowered or "did not remain running" in lowered:
        values = (
            "runtime.health",
            "runtime",
            "runtime_health_failed",
            "correct PORT, health_path or the start command using the redacted logs",
        )
    elif "docker engine" in lowered or "container" in lowered:
        values = (
            "runtime.start",
            "container",
            "runtime_container_failed",
            "inspect provider capacity and container diagnostics, then retry",
        )
    else:
        values = (
            "runtime.execute",
            "runtime",
            "runtime_execution_failed",
            "inspect the event stream and redacted logs before retrying",
        )
    stage, component, error_code, next_action = values
    return {
        "stage": stage,
        "component": component,
        "error_code": error_code,
        "message": message,
        "retryable": True,
        "next_action": next_action,
        "raw_reasoning_exposed": False,
    }


class RuntimeController(base.RuntimeController):
    def reconcile_repositories(self) -> int:
        if base.time.monotonic() - self._last_repository_reconcile < 60:
            return 0
        self._last_repository_reconcile = base.time.monotonic()
        return reconcile_repository_resources(self.settings)

    def _container_spec(
        self, snapshot: dict[str, object], host_root: Path, host_data: Path
    ) -> tuple[str, dict[str, object], int, str]:
        name, spec, port, health_path = super()._container_spec(snapshot, host_root, host_data)
        family = str(snapshot.get("runtime_family"))
        configured_start = _configured_command(snapshot, "start_command")
        if family == "node" and not configured_start:
            spec["Cmd"] = ["sh", "-lc", _node_command(snapshot)]
        if family == "python" and snapshot.get("managed_build"):
            command = str((spec.get("Cmd") or ["", "", ""])[-1])
            venv = _managed_python_venv(snapshot)
            python_path = (
                'export PYTHONPATH="/workspace/app/src${PYTHONPATH:+:$PYTHONPATH}"; '
                if snapshot.get("managed_build_src_layout")
                else ""
            )
            spec["Cmd"] = [
                "sh",
                "-lc",
                f"set -eu; export VIRTUAL_ENV={venv}; "
                'export PATH="$VIRTUAL_ENV/bin:$PATH"; ' + python_path + command,
            ]
        return name, spec, port, health_path

    @staticmethod
    def _builder_command(snapshot: dict[str, object], build_command: str) -> str:
        family = str(snapshot.get("runtime_family") or "")
        common = (
            "set -eu; cd /workspace/app; "
            "mkdir -p /workspace/data/.runtime/home "
            "/workspace/data/.runtime/pip-cache /workspace/data/.runtime/npm-cache; "
            "export HOME=/workspace/data/.runtime/home; "
            "export PIP_CACHE_DIR=/workspace/data/.runtime/pip-cache; "
            "export npm_config_cache=/workspace/data/.runtime/npm-cache; "
        )
        if family == "python":
            venv = _managed_python_venv(snapshot)
            common += (
                f"mkdir -p {venv.rsplit('/', 1)[0]}; "
                f"if [ ! -x {venv}/bin/python ]; then "
                f"python -m venv {venv}; fi; "
                f"export VIRTUAL_ENV={venv}; "
                'export PATH="$VIRTUAL_ENV/bin:$PATH"; '
                'RUNTIME_BUILD_ROOT="$(mktemp -d /tmp/warehouse-python-build.XXXXXX)"; '
                'cp -a /workspace/app/. "$RUNTIME_BUILD_ROOT/source"; '
                'cd "$RUNTIME_BUILD_ROOT/source"; '
            )
        return common + build_command

    @staticmethod
    def _resolved_build_command(snapshot: dict[str, object], root: Path) -> tuple[str, str]:
        configured = _configured_command(snapshot, "build_command")
        if configured:
            return configured, "declared"
        family = str(snapshot.get("runtime_family") or "")
        if family == "python":
            commands = []
            requirements = next(
                (
                    candidate
                    for candidate in ("requirements.hosting.txt", "requirements.txt")
                    if (root / candidate).is_file()
                ),
                None,
            )
            if requirements:
                commands.append(
                    f"python -m pip install --no-cache-dir -r {shlex.quote(requirements)}"
                )
            if (root / "pyproject.toml").is_file() or (root / "setup.py").is_file():
                commands.append("python -m pip install --no-cache-dir .")
            return " && ".join(commands), "detected"
        if family == "node" and (root / "package.json").is_file():
            commands = ["npm ci" if (root / "package-lock.json").is_file() else "npm install"]
            try:
                package = json.loads((root / "package.json").read_text(encoding="utf-8"))
            except (OSError, TypeError, ValueError):
                package = {}
            scripts = package.get("scripts") if isinstance(package, dict) else {}
            if isinstance(scripts, dict) and scripts.get("build"):
                commands.append("npm run build")
            return " && ".join(commands), "detected"
        return "", "none"

    def _run_managed_build(
        self,
        snapshot: dict[str, object],
        root: Path,
        materialized: dict[str, object],
    ) -> tuple[Path, Path, dict[str, object]]:
        build_command, build_selection = self._resolved_build_command(snapshot, root)
        family = str(snapshot.get("runtime_family") or "")
        if not build_command or family not in {"python", "node"}:
            _controller_path, host_path = self._runtime_paths(snapshot)
            host_root = host_path / root.relative_to(_controller_path)
            return root, host_root, materialized

        tenant_id = UUID(str(snapshot["tenant_id"]))
        controller_path, host_path = self._runtime_paths(snapshot)
        build_root = controller_path / "build"
        host_build_root = host_path / "build"
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
        digest = hashlib.sha256(
            (
                f"{snapshot.get('sha256') or snapshot['id']}:"
                f"{snapshot.get('image_ref') or ''}:{family}:{build_command}"
            ).encode()
        ).hexdigest()
        snapshot["managed_build_digest"] = digest
        marker = build_root / ".warehouse-build-ready.json"
        cached = False
        if marker.is_file():
            try:
                cached = json.loads(marker.read_text(encoding="utf-8")).get("digest") == digest
            except (OSError, ValueError, TypeError):
                cached = False

        log_excerpt: list[str] = []
        if not cached:
            if build_root.exists():
                shutil.rmtree(build_root)
            shutil.copytree(root, build_root)
            data_path.mkdir(parents=True, exist_ok=True, mode=0o750)
            self._prepare_runtime_mounts(build_root, data_path)
            builder_name = f"warehouse-build-{str(snapshot['id']).replace('-', '')[:20]}"
            contract = snapshot.get("execution_contract") or {}
            limits = snapshot.get("resource_limits") or {}
            environment = [
                f"PORT={int(contract.get('port') or 8080)}",
                "PYTHONDONTWRITEBYTECODE=1",
                "WAREHOUSE_DATA_DIR=/workspace/data",
                *[
                    f"{key}={value}"
                    for key, value in sorted(
                        dict(snapshot.get("runtime_environment") or {}).items()
                    )
                ],
            ]
            spec: dict[str, object] = {
                "Image": str(snapshot.get("image_ref") or ""),
                "WorkingDir": "/workspace/app",
                "Env": environment,
                "Cmd": ["sh", "-lc", self._builder_command(snapshot, build_command)],
                "Labels": {
                    "org.bonfirework.managed": "runtime-builder",
                    "org.bonfirework.deployment": str(snapshot["id"]),
                    "org.bonfirework.workspace": str(snapshot["workspace_id"]),
                },
                "HostConfig": {
                    "Binds": [
                        (
                            f"{host_build_root}:/workspace/app:ro"
                            if family == "python"
                            else f"{host_build_root}:/workspace/app:rw"
                        ),
                        f"{host_data}:/workspace/data:rw",
                    ],
                    "NetworkMode": self.settings.runtime_docker_network,
                    "ReadonlyRootfs": True,
                    "Tmpfs": {"/tmp": "rw,nosuid,size=536870912"},
                    "CapDrop": ["ALL"],
                    "SecurityOpt": ["no-new-privileges:true"],
                    "Memory": int(limits.get("memory_mb") or 512) * 1024 * 1024,
                    "NanoCpus": int(float(limits.get("cpus") or 0.5) * 1_000_000_000),
                    "PidsLimit": int(limits.get("pids") or 128),
                    "RestartPolicy": {"Name": "no"},
                },
            }
            with base.tenant_session(tenant_id) as session:
                base._event(
                    session,
                    UUID(str(snapshot["id"])),
                    tenant_id,
                    "build_started",
                    {
                        "runtime_family": family,
                        "build_digest": digest,
                        "selection": build_selection,
                    },
                )
            engine = DockerEngine(self.settings.runtime_docker_socket)
            exit_code: int | None = None
            engine_failure: Exception | None = None
            try:
                engine.remove(builder_name)
                engine.create(name=builder_name, spec=spec)
                engine.start(builder_name)
                exit_code = engine.wait(builder_name)
            except Exception as exc:
                engine_failure = exc
            finally:
                try:
                    log_excerpt = self._redact_runtime_logs(snapshot, engine.logs(builder_name))
                except Exception:
                    log_excerpt = []
                try:
                    engine.remove(builder_name)
                except Exception:
                    pass
                engine.close()
            if engine_failure is not None or exit_code != 0:
                with base.tenant_session(tenant_id) as session:
                    session.execute(
                        text(
                            "UPDATE digital_asset.deployments SET result=result || "
                            "CAST(:build AS jsonb) WHERE id=:id"
                        ),
                        {
                            "id": snapshot["id"],
                            "build": json.dumps(
                                {
                                    "build": {
                                        "status": "failed",
                                        "exit_code": exit_code,
                                        "build_digest": digest,
                                        "selection": build_selection,
                                    },
                                    "build_log_excerpt": log_excerpt,
                                },
                                ensure_ascii=False,
                            ),
                        },
                    )
                if engine_failure is not None:
                    raise RuntimeError("Runtime build container failed") from engine_failure
                raise RuntimeError(f"Runtime build command failed with exit code {exit_code}")
            marker.write_text(json.dumps({"digest": digest}, ensure_ascii=True), encoding="utf-8")
            with base.tenant_session(tenant_id) as session:
                base._event(
                    session,
                    UUID(str(snapshot["id"])),
                    tenant_id,
                    "build_succeeded",
                    {
                        "runtime_family": family,
                        "build_digest": digest,
                        "selection": build_selection,
                    },
                )

        runtime_bytes = self._directory_bytes(controller_path)
        with base.tenant_session(tenant_id) as session:
            usage = (
                session.execute(
                    text(
                        "SELECT total_billable_bytes,runtime_bytes "
                        "FROM digital_asset.workspace_usage "
                        "WHERE workspace_id=:id FOR UPDATE"
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
                key_kind = session.execute(
                    text(
                        "SELECT key_kind FROM digital_asset.api_credentials "
                        "WHERE id=:id AND workspace_id=:workspace_id"
                    ),
                    {
                        "id": snapshot.get("requested_credential_id"),
                        "workspace_id": snapshot["workspace_id"],
                    },
                ).scalar_one_or_none()
                if key_kind != "primary":
                    shutil.rmtree(build_root, ignore_errors=True)
                    raise RuntimeError("Built Runtime exceeds the workspace logical quota")
                target = allocation_target_bytes(
                    projected + 8 * 1024 * 1024,
                    current_bytes=int(snapshot["storage_quota_bytes"]),
                )
                session.execute(
                    text(
                        "UPDATE digital_asset.workspaces "
                        "SET storage_quota_bytes=:target,revision=revision+1 WHERE id=:id"
                    ),
                    {"target": target, "id": snapshot["workspace_id"]},
                )
                snapshot["storage_quota_bytes"] = target

        snapshot["managed_build"] = True
        snapshot["managed_build_src_layout"] = (build_root / "src").is_dir()
        return (
            build_root,
            host_build_root,
            {
                **materialized,
                "runtime_bytes": runtime_bytes,
                "runtime_rel_path": str(
                    build_root.relative_to(self.settings.hosted_runtime_data_root.resolve())
                ),
                "build": {
                    "status": "cached" if cached else "succeeded",
                    "build_digest": digest,
                    "selection": build_selection,
                    "log_excerpt": log_excerpt,
                },
            },
        )

    def _materialize(self, snapshot: dict[str, object]) -> tuple[Path, Path, dict[str, object]]:
        quota_failure: RuntimeError | None = None
        try:
            materialized = super()._materialize(snapshot)
        except RuntimeError as exc:
            if "workspace logical quota" not in str(exc).lower():
                raise
            quota_failure = exc
            tenant_id = UUID(str(snapshot["tenant_id"]))
            with base.tenant_session(tenant_id) as session:
                key_kind = session.execute(
                    text(
                        "SELECT key_kind FROM digital_asset.api_credentials "
                        "WHERE id=:id AND workspace_id=:workspace_id"
                    ),
                    {
                        "id": snapshot.get("requested_credential_id"),
                        "workspace_id": snapshot["workspace_id"],
                    },
                ).scalar_one_or_none()
                if key_kind != "primary":
                    raise quota_failure
                controller_path, _host_path = self._runtime_paths(snapshot)
                runtime_bytes = self._directory_bytes(controller_path / "source")
                usage = (
                    session.execute(
                        text(
                            "SELECT total_billable_bytes,runtime_bytes "
                            "FROM digital_asset.workspace_usage "
                            "WHERE workspace_id=:id FOR UPDATE"
                        ),
                        {"id": snapshot["workspace_id"]},
                    )
                    .mappings()
                    .one_or_none()
                )
                if usage is None:
                    raise quota_failure
                required = (
                    int(usage["total_billable_bytes"])
                    - int(usage["runtime_bytes"])
                    + runtime_bytes
                    + 8 * 1024 * 1024
                )
                target = allocation_target_bytes(
                    required,
                    current_bytes=int(snapshot["storage_quota_bytes"]),
                )
                session.execute(
                    text(
                        "UPDATE digital_asset.workspaces "
                        "SET storage_quota_bytes=:target, revision=revision+1 WHERE id=:id"
                    ),
                    {"target": target, "id": snapshot["workspace_id"]},
                )
                base._audit(
                    session,
                    None,
                    "digital_asset.runtime_primary_quota_recovered",
                    {
                        "workspace_id": str(snapshot["workspace_id"]),
                        "deployment_id": str(snapshot["id"]),
                        "before_bytes": int(snapshot["storage_quota_bytes"]),
                        "after_bytes": target,
                        "runtime_bytes": runtime_bytes,
                    },
                    tenant_id=tenant_id,
                )
                snapshot["storage_quota_bytes"] = target
            materialized = super()._materialize(snapshot)
        return self._run_managed_build(snapshot, materialized[0], materialized[2])

    def fail(self, tenant_id: UUID, deployment_id: UUID, exc: Exception) -> None:
        diagnostic = _diagnostic(exc)
        super().fail(tenant_id, deployment_id, exc)
        with base.tenant_session(tenant_id) as session:
            session.execute(
                text(
                    "UPDATE digital_asset.deployments SET result=result || "
                    "CAST(:diagnostic AS jsonb) WHERE id=:id"
                ),
                {
                    "id": deployment_id,
                    "diagnostic": json.dumps({"diagnostic": diagnostic}, ensure_ascii=False),
                },
            )
            base._event(
                session,
                deployment_id,
                tenant_id,
                "diagnostic",
                diagnostic,
            )


def main() -> None:
    settings = base.get_settings()
    if not settings.runtime_controller_enabled:
        raise SystemExit("WAREHOUSE_RUNTIME_CONTROLLER_ENABLED is false")
    RuntimeController(settings).run_forever()


if __name__ == "__main__":
    main()
