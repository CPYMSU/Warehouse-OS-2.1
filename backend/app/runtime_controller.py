"""Compatibility-hardened Runtime Controller entrypoint.

The original controller remains byte-identical in ``runtime_controller_base``.
This module fixes mutable Node builds, elastic primary-key materialisation and
structured failure evidence without changing the queue or deployment schema.
"""

from __future__ import annotations

import hashlib
import json
import shlex
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
        "return res.end('{\"status\":\"ok\"}');}"
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


def _node_command(snapshot: dict[str, object]) -> str:
    digest = hashlib.sha256(
        f"{snapshot.get('sha256') or snapshot['id']}:{snapshot.get('image_ref') or ''}".encode()
    ).hexdigest()[:24]
    entrypoint = shlex.quote(str(snapshot.get("entrypoint") or "").strip())
    server_source = shlex.quote(_node_static_server_source())
    return (
        "set -eu; "
        f"RUNTIME_NODE_ROOT=/workspace/data/.runtime/node/{digest}; "
        "SOURCE_ROOT=\"$RUNTIME_NODE_ROOT/source\"; "
        "mkdir -p /workspace/data/.runtime/npm-cache /workspace/data/.runtime/home; "
        "export npm_config_cache=/workspace/data/.runtime/npm-cache; "
        "export HOME=/workspace/data/.runtime/home; "
        "if [ ! -f \"$RUNTIME_NODE_ROOT/.deps-ready\" ]; then "
        "rm -rf \"$RUNTIME_NODE_ROOT\"; mkdir -p \"$SOURCE_ROOT\"; "
        "cp -a /workspace/app/. \"$SOURCE_ROOT/\"; cd \"$SOURCE_ROOT\"; "
        "if [ -f package-lock.json ]; then npm ci; else npm install; fi; "
        "touch \"$RUNTIME_NODE_ROOT/.deps-ready\"; fi; cd \"$SOURCE_ROOT\"; "
        "if node -e \"const p=require('./package.json');"
        "process.exit(p.scripts&&p.scripts.build?0:1)\"; then "
        "if [ ! -f \"$RUNTIME_NODE_ROOT/.build-ready\" ]; then npm run build; "
        "touch \"$RUNTIME_NODE_ROOT/.build-ready\"; fi; fi; "
        "if node -e \"const p=require('./package.json');"
        "process.exit(p.scripts&&p.scripts.start?0:1)\"; then exec npm start; fi; "
        "for OUTPUT in dist build public; do if [ -f \"$OUTPUT/index.html\" ]; then "
        f"export WAREHOUSE_STATIC_ROOT=\"$SOURCE_ROOT/$OUTPUT\"; "
        f"exec node -e {server_source}; fi; done; "
        "MAIN=\"$(node -p \"require('./package.json').main||''\" 2>/dev/null || true)\"; "
        "if [ -n \"$MAIN\" ] && [ -f \"$MAIN\" ]; then exec node \"$MAIN\"; fi; "
        f"ENTRY={entrypoint}; if [ -n \"$ENTRY\" ] && [ -f \"$ENTRY\" ]; "
        "then exec node \"$ENTRY\"; fi; "
        "for ENTRY in server.js index.js app.js; do if [ -f \"$ENTRY\" ]; "
        "then exec node \"$ENTRY\"; fi; done; "
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
        name, spec, port, health_path = super()._container_spec(
            snapshot, host_root, host_data
        )
        if str(snapshot.get("runtime_family")) == "node":
            spec["Cmd"] = ["sh", "-lc", _node_command(snapshot)]
        return name, spec, port, health_path

    def _materialize(
        self, snapshot: dict[str, object]
    ) -> tuple[Path, Path, dict[str, object]]:
        quota_failure: RuntimeError | None = None
        try:
            return super()._materialize(snapshot)
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
            usage = session.execute(
                text(
                    "SELECT total_billable_bytes,runtime_bytes "
                    "FROM digital_asset.workspace_usage "
                    "WHERE workspace_id=:id FOR UPDATE"
                ),
                {"id": snapshot["workspace_id"]},
            ).mappings().one_or_none()
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
        return super()._materialize(snapshot)

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
                    "diagnostic": json.dumps(
                        {"diagnostic": diagnostic}, ensure_ascii=False
                    ),
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
