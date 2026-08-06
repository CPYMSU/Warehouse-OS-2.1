#!/usr/bin/env python3
"""Warehouse Pages local runtime agent (stdlib-only bootstrap)."""

from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

AGENT_VERSION = "1.0.0"


def _request(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": f"WarehouseDeviceAgent/{AGENT_VERSION}",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _safe_target(root: Path, name: str) -> Path:
    target = (root / name).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"Unsafe archive path: {name}") from exc
    return target


def _extract_archive(archive: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                destination = _safe_target(target, member.filename)
                mode = member.external_attr >> 16
                if (mode & 0o170000) == 0o120000:
                    raise RuntimeError("Source archive contains a symbolic link")
                if member.is_dir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(member) as source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        return
    if tarfile.is_tarfile(archive):
        with tarfile.open(archive) as bundle:
            for member in bundle.getmembers():
                if member.issym() or member.islnk() or member.isdev():
                    raise RuntimeError("Source archive contains an unsupported link or device")
                destination = _safe_target(target, member.name)
                if member.isdir():
                    destination.mkdir(parents=True, exist_ok=True)
                    continue
                if not member.isfile():
                    continue
                source = bundle.extractfile(member)
                if source is None:
                    continue
                destination.parent.mkdir(parents=True, exist_ok=True)
                with source, destination.open("wb") as output:
                    shutil.copyfileobj(source, output)
        return
    raise RuntimeError("Source package must be a ZIP or TAR archive")


def _application_root(extracted: Path) -> Path:
    children = [
        item
        for item in extracted.iterdir()
        if item.name not in {"__MACOSX", ".warehouse-source-sha256"}
    ]
    if len(children) == 1 and children[0].is_dir():
        return children[0]
    return extracted


def _load_contract(root: Path) -> dict[str, object]:
    path = root / "warehouse.hosting.json"
    if not path.is_file():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("warehouse.hosting.json must be an object")
    runtime = value.get("runtime")
    return runtime if isinstance(runtime, dict) else {}


def _default_command(root: Path, runtime: dict[str, object]) -> str | None:
    configured = str(runtime.get("start_command") or "").strip()
    if configured:
        return configured
    if (root / "package.json").is_file():
        return "npm start"
    configured_entrypoint = str(runtime.get("entrypoint") or "").strip()
    if configured_entrypoint and (root / configured_entrypoint).is_file():
        entrypoint = Path(configured_entrypoint)
        if entrypoint.suffix == ".js":
            return f"node {shlex.quote(entrypoint.as_posix())}"
        if entrypoint.suffix == ".py":
            module = entrypoint.with_suffix("").as_posix().replace("/", ".")
            return f"python -m uvicorn {shlex.quote(module)}:app --host 127.0.0.1 --port $PORT"
    for entrypoint in ("app.py", "main.py"):
        if (root / entrypoint).is_file():
            module = Path(entrypoint).stem
            return f"python -m uvicorn {module}:app --host 127.0.0.1 --port $PORT"
    if (root / "server.js").is_file():
        return "node server.js"
    return None


def _run_build(root: Path, runtime: dict[str, object], enabled: bool) -> None:
    command = str(runtime.get("build_command") or "").strip()
    if not enabled or not command:
        return
    subprocess.run(command, cwd=root, env=os.environ.copy(), shell=True, check=True)


def _start_runtime(
    root: Path,
    runtime: dict[str, object],
    args: argparse.Namespace,
) -> subprocess.Popen[bytes]:
    runtime_type = str(runtime.get("type") or "").lower()
    if not args.command and runtime_type == "container" and (root / "Dockerfile").is_file():
        if shutil.which("docker") is None:
            raise RuntimeError("Docker is required for this container Runtime")
        image = "warehouse-device-" + hashlib.sha256(str(root).encode()).hexdigest()[:12]
        subprocess.run(
            ["docker", "build", "-t", image, "."],
            cwd=root,
            check=True,
        )
        container_port = int(runtime.get("port") or 8080)
        command = [
            "docker",
            "run",
            "--rm",
            "-p",
            f"127.0.0.1:{args.runtime_port}:{container_port}",
        ]
        for name in ("DATABASE_URL", "APP_DATABASE_URL"):
            if os.environ.get(name):
                command.extend(["-e", name])
        command.append(image)
        print(f"Starting local container: {image}")
        return subprocess.Popen(command, cwd=root)
    command = args.command or _default_command(root, runtime)
    if not command:
        raise RuntimeError("No local start command was detected; pass --command explicitly")
    environment = os.environ.copy()
    environment["PORT"] = str(args.runtime_port)
    environment["HOST"] = "127.0.0.1"
    environment["WAREHOUSE_DEVICE_RUNTIME"] = "1"
    print(f"Starting local runtime: {command}")
    return subprocess.Popen(command, cwd=root, env=environment, shell=True)


def _wait_for_runtime(
    port: int,
    process: subprocess.Popen[bytes],
    *,
    health_path: str,
) -> None:
    deadline = time.monotonic() + 45
    path = health_path if health_path.startswith("/") else "/"
    url = f"http://127.0.0.1:{port}{path}"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Local runtime stopped with exit code {process.returncode}")
        try:
            urllib.request.urlopen(url, timeout=1).close()
            return
        except urllib.error.HTTPError as exc:
            if path == "/" and exc.code < 500:
                return
            time.sleep(0.25)
        except OSError:
            time.sleep(0.25)
    raise RuntimeError("Local runtime did not open its loopback port within 45 seconds")


class DeviceGateway(http.server.BaseHTTPRequestHandler):
    server_version = "WarehouseDeviceAgent/1.0"

    @property
    def config(self) -> dict[str, object]:
        return self.server.config  # type: ignore[attr-defined]

    def _allowed_origin(self) -> str | None:
        origin = self.headers.get("Origin", "").rstrip("/")
        return origin if origin in self.config["allowed_origins"] else None

    def _cors(self) -> None:
        origin = self._allowed_origin()
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header(
                "Access-Control-Allow-Methods",
                "GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS",
            )
            self.send_header(
                "Access-Control-Allow-Headers",
                "Content-Type, Authorization, X-Warehouse-Device-Runtime",
            )
            self.send_header("Access-Control-Allow-Private-Network", "true")
            self.send_header("Access-Control-Max-Age", "600")

    def do_OPTIONS(self) -> None:
        if not self._allowed_origin():
            self.send_error(403, "Origin is not allowed")
            return
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _health(self) -> None:
        payload = json.dumps(
            {
                "ready": True,
                "workspace_key": self.config["workspace_key"],
                "agent_version": AGENT_VERSION,
            },
            separators=(",", ":"),
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _proxy(self) -> None:
        if not self._allowed_origin():
            self.send_error(403, "Device runtime request rejected")
            return
        prefix = f"/v1/workspaces/{urllib.parse.quote(str(self.config['workspace_key']))}"
        if not self.path.startswith(prefix):
            self.send_error(404)
            return
        suffix = self.path[len(prefix) :] or "/"
        target = f"http://127.0.0.1:{self.config['runtime_port']}{suffix}"
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        excluded = {"host", "content-length", "connection", "origin", "x-warehouse-device-runtime"}
        headers = {key: value for key, value in self.headers.items() if key.lower() not in excluded}
        request = urllib.request.Request(target, data=body, headers=headers, method=self.command)
        try:
            response = urllib.request.urlopen(request, timeout=120)
        except urllib.error.HTTPError as exc:
            response = exc
        except OSError as exc:
            self.send_error(502, f"Local runtime unavailable: {exc}")
            return
        content = response.read()
        self.send_response(response.status)
        for key, value in response.headers.items():
            if key.lower() not in {
                "connection",
                "content-length",
                "content-encoding",
                "transfer-encoding",
                "access-control-allow-origin",
            }:
                self.send_header(key, value)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Warehouse-Execution", "device")
        self._cors()
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(content)

    def _dispatch(self) -> None:
        workspace = urllib.parse.quote(str(self.config["workspace_key"]))
        health_path = f"/v1/workspaces/{workspace}/health"
        if urllib.parse.urlsplit(self.path).path == health_path:
            if not self._allowed_origin():
                self.send_error(403, "Origin is not allowed")
                return
            self._health()
            return
        self._proxy()

    do_GET = _dispatch
    do_HEAD = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_PATCH = _dispatch
    do_DELETE = _dispatch

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("device-agent: " + (format % args) + "\n")


def _prepare(args: argparse.Namespace) -> tuple[dict[str, object], Path]:
    token = args.token or os.environ.get("WAREHOUSE_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("Set WAREHOUSE_ACCESS_TOKEN or pass --token")
    base = args.base_url.rstrip("/")
    workspace = urllib.parse.quote(args.workspace, safe="")
    manifest = json.loads(_request(f"{base}/api/workspaces/{workspace}/device-runtime", token))
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else None
    if not source or not source.get("download_url"):
        raise RuntimeError("This workspace has no active source package")
    digest = str(source.get("sha256") or "").lower()
    if not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise RuntimeError("Manifest source SHA-256 is invalid")
    release_root = Path(args.workdir).expanduser().resolve() / args.workspace / digest[:16]
    marker = release_root / ".warehouse-source-sha256"
    if marker.is_file() and marker.read_text().strip() == digest:
        return manifest, _application_root(release_root)
    release_root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="warehouse-source-", delete=False) as temporary:
        archive = Path(temporary.name)
        temporary.write(_request(base + str(source["download_url"]), token))
    try:
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if not digest or actual != digest:
            raise RuntimeError(f"Source SHA-256 mismatch: expected {digest}, received {actual}")
        _extract_archive(archive, release_root)
        marker.write_text(digest + "\n", encoding="utf-8")
    finally:
        archive.unlink(missing_ok=True)
    return manifest, _application_root(release_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Warehouse Pages backend on this device")
    parser.add_argument("--workspace", required=True, help="Workspace key")
    parser.add_argument("--base-url", default="https://bonfirework.org")
    parser.add_argument("--token", help="Account access token; prefer WAREHOUSE_ACCESS_TOKEN")
    parser.add_argument("--workdir", default="~/.warehouse/device-runtimes")
    parser.add_argument("--port", type=int, default=47821, help="Browser gateway loopback port")
    parser.add_argument("--runtime-port", type=int, default=47822)
    parser.add_argument("--command", help="Override the local start command")
    parser.add_argument(
        "--build",
        action="store_true",
        help="Run the source-declared build command",
    )
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", args.workspace):
        parser.error("--workspace must be a valid Warehouse workspace key")
    manifest, root = _prepare(args)
    print(f"Verified source at {root}")
    if args.prepare_only:
        return 0
    launch = manifest.get("launch") if isinstance(manifest.get("launch"), dict) else {}
    runtime = {**launch, **_load_contract(root)}
    _run_build(root, runtime, args.build)
    process = _start_runtime(root, runtime, args)
    try:
        _wait_for_runtime(
            args.runtime_port,
            process,
            health_path=str(runtime.get("health_path") or "/"),
        )
        pages = manifest.get("pages") if isinstance(manifest.get("pages"), dict) else {}
        origin = str(pages.get("origin") or "").rstrip("/")
        if not origin.startswith("https://"):
            raise RuntimeError("Manifest did not provide a secure Pages origin")
        server = http.server.ThreadingHTTPServer(("127.0.0.1", args.port), DeviceGateway)
        server.config = {
            "workspace_key": args.workspace,
            "runtime_port": args.runtime_port,
            "allowed_origins": {origin},
        }
        print(f"Device runtime ready on http://127.0.0.1:{args.port} for {origin}")
        server.serve_forever()
    finally:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:
        print(f"device-agent: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
