"""Loopback-only synthetic HTTP integration for the private UHV gateway.

This exercises actual sockets and HTTP framing between two disposable local
processes. The fixture simulates authenticated upstream behavior; it is not
the production ingress, Pages resolver, identity database, or user data.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from pathlib import Path
import resource
import socket
import subprocess
import sys
import time

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
import uvicorn

from app.api import hosted_runtime_gateway as gateway

BLOCK = b"synthetic-uhv-data-" * 4096
BLOCKS = 2048
FILE_SIZE = len(BLOCK) * BLOCKS
DOC = "a" * 64
FILE_PATH = f"api/v1/uhv/documents/{DOC}/file"
UPLOAD_PATH = "api/v1/uhv-intake/sessions/00000000-0000-4000-8000-000000000001/parts/0"
ISOLATED_HOST = "mk7-workspace.bonfirework.org"
ORIGIN = "https://" + ISOLATED_HOST


def upstream_app():
    app = FastAPI()
    state = {"cancelled": 0, "forwarded": 0}

    @app.get("/_test/health")
    async def health():
        return state

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT"])
    async def serve(path: str, request: Request):
        state["forwarded"] += 1
        if path.startswith("api/v1/uhv"):
            if request.headers.get("cookie") != "fixture_session=valid":
                return JSONResponse({"detail": "unauthenticated"}, 401)
            if request.headers.get("origin") != ORIGIN:
                return JSONResponse({"detail": "origin_denied"}, 403)
        if path == UPLOAD_PATH:
            digest = hashlib.sha256(); total = 0
            async for data in request.stream():
                digest.update(data); total += len(data)
            return {"bytes": total, "sha256": digest.hexdigest()}
        if path != FILE_PATH:
            return {"path": path, "host": request.headers.get("host"), "forwarded": request.headers.get("x-forwarded-host")}
        selected = request.headers.get("range")
        if selected:
            if selected != "bytes=3-12":
                return Response(status_code=416)
            return Response(BLOCK[3:13], status_code=206, headers={"Content-Range": f"bytes 3-12/{FILE_SIZE}", "Accept-Ranges": "bytes"}, media_type="application/octet-stream")
        if request.method == "HEAD":
            return Response(status_code=200, headers={"Content-Length": str(FILE_SIZE)}, media_type="application/octet-stream")
        async def generate():
            try:
                for _ in range(BLOCKS):
                    yield BLOCK
                    await asyncio.sleep(0.0005)
            except asyncio.CancelledError:
                state["cancelled"] += 1
                raise
        return StreamingResponse(generate(), headers={"Content-Length": str(FILE_SIZE), "Accept-Ranges": "bytes"}, media_type="application/octet-stream")
    return app


def gateway_app(upstream_port: int):
    app = FastAPI()

    @app.get("/_test/health")
    async def health():
        # macOS ru_maxrss is bytes; Linux uses KiB.
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return {"peak_bytes": peak if sys.platform == "darwin" else peak * 1024}

    @app.api_route("/{path:path}", methods=["GET", "HEAD", "POST", "PUT"])
    async def proxy(path: str, request: Request):
        other = path.startswith("_other/")
        if other:
            path = path[len("_other/"):]
        else:
            request.state.pages_hostname_route = {"tenant_slug": "fixture", "workspace_key": "mk7-workspace"}
        return await gateway._proxy_response(
            {"internal_url": f"http://127.0.0.1:{upstream_port}", "deployment_id": "fixture"},
            path, request, "fixture", "another-workspace" if other else "mk7-workspace",
        )
    return app


def serve(role, listen_fd, upstream_port=0):
    sock = socket.socket(fileno=int(listen_fd))
    app = upstream_app() if role == "upstream" else gateway_app(int(upstream_port))
    uvicorn.Server(uvicorn.Config(app, log_level="error", access_log=False, lifespan="off")).run(sockets=[sock])


@pytest.fixture(scope="module")
def local_servers():
    processes = []; sockets = []
    try:
        for role in ("upstream", "gateway"):
            listener = socket.socket(); listener.bind(("127.0.0.1", 0)); listener.listen(128)
            sockets.append(listener)
            args = [sys.executable, "-B", str(Path(__file__).resolve()), role, str(listener.fileno())]
            if role == "gateway": args.append(str(sockets[0].getsockname()[1]))
            processes.append(subprocess.Popen(args, pass_fds=(listener.fileno(),), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        ports = [s.getsockname()[1] for s in sockets]
        with httpx.Client(trust_env=False, timeout=3) as client:
            for port in ports:
                deadline = time.monotonic() + 15
                while True:
                    try:
                        if client.get(f"http://127.0.0.1:{port}/_test/health").status_code == 200: break
                    except httpx.HTTPError:
                        if time.monotonic() >= deadline: raise
                        time.sleep(0.05)
        yield tuple(f"http://127.0.0.1:{port}" for port in ports)
    finally:
        for p in processes: p.terminate()
        for p in processes:
            try: p.wait(timeout=5)
            except subprocess.TimeoutExpired: p.kill(); p.wait(timeout=5)
        for listener in sockets: listener.close()


def auth_headers():
    return {"host": ISOLATED_HOST, "origin": ORIGIN, "cookie": "fixture_session=valid"}


def test_loopback_range_head_origin_and_other_workspace(local_servers):
    _upstream, route = local_servers
    with httpx.Client(trust_env=False, timeout=20) as client:
        url = route + "/" + FILE_PATH
        head = client.head(url, headers=auth_headers())
        assert head.status_code == 200 and head.content == b"" and int(head.headers["content-length"]) == FILE_SIZE
        part = client.get(url, headers=auth_headers() | {"range": "bytes=3-12"})
        assert part.status_code == 206 and part.content == BLOCK[3:13] and part.headers["content-range"] == f"bytes 3-12/{FILE_SIZE}"
        assert "no-store" in part.headers["cache-control"]
        assert client.get(url, headers={"host": ISOLATED_HOST, "origin": ORIGIN}).status_code == 401
        assert client.get(url, headers=auth_headers() | {"origin": "https://outside.invalid"}).status_code == 403
        # Header is not forwarded to the protected upstream from a caller.
        info = client.get(route + "/api/v1/uhv/documents", headers=auth_headers() | {"x-forwarded-host": "attacker.invalid"})
        assert info.status_code == 200 and info.json()["forwarded"] is None
        other = client.get(route + "/_other/api/v1/uhv/documents", headers={"host": "other.invalid", "origin": ORIGIN, "cookie": "fixture_session=valid"})
        assert other.status_code == 200


def test_loopback_upload_and_bounded_download_memory(local_servers):
    _upstream, route = local_servers
    with httpx.Client(trust_env=False, timeout=60) as client:
        total = 8 * 1024 * 1024
        chunk = b"s" * 65536
        expected = hashlib.sha256(chunk * (total // len(chunk))).hexdigest()
        upload = client.put(route + "/" + UPLOAD_PATH, headers=auth_headers() | {"content-length": str(total)}, content=(chunk for _ in range(total // len(chunk))))
        assert upload.status_code == 200 and upload.json() == {"bytes": total, "sha256": expected}
        baseline = client.get(route + "/_test/health").json()["peak_bytes"]
        count = 0; digest = hashlib.sha256()
        with client.stream("GET", route + "/" + FILE_PATH, headers=auth_headers()) as response:
            assert response.status_code == 200
            for part in response.iter_bytes(): count += len(part); digest.update(part)
        expected_digest = hashlib.sha256()
        for _ in range(BLOCKS): expected_digest.update(BLOCK)
        assert count == FILE_SIZE and digest.hexdigest() == expected_digest.hexdigest()
        peak = client.get(route + "/_test/health").json()["peak_bytes"]
        print(f"synthetic_download_bytes={count} gateway_peak_delta_bytes={peak - baseline}")
        assert peak - baseline < 64 * 1024 * 1024, (baseline, peak, FILE_SIZE)


def test_loopback_download_disconnect_closes_upstream(local_servers):
    upstream, route = local_servers
    with httpx.Client(trust_env=False, timeout=15) as client:
        before = client.get(upstream + "/_test/health").json()["cancelled"]
        with client.stream("GET", route + "/" + FILE_PATH, headers=auth_headers()) as response:
            assert response.status_code == 200
            assert next(response.iter_bytes())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if client.get(upstream + "/_test/health").json()["cancelled"] > before: return
            time.sleep(0.05)
        pytest.fail("upstream stream was not cancelled after downstream disconnect")


if __name__ == "__main__":
    serve(*sys.argv[1:])
