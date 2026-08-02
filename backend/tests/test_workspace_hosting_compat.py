from __future__ import annotations

import json
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app import runtime_controller
from app.api import hosted_runtime_gateway
from app.core.config import Settings
from app.main import app
from app.services.workspace_autonomy import (
    WORKSPACE_QUOTA_STEP_BYTES,
    allocation_target_bytes,
    estimate_record_write_bytes,
)


def _first_endpoint(path: str):
    return next(route.endpoint for route in app.routes if getattr(route, "path", None) == path)


def test_compatibility_routes_precede_retained_routes() -> None:
    assert _first_endpoint("/api/workspaces/v1/sources/upload").__module__ == (
        "app.api.workspace_autonomy"
    )
    assert _first_endpoint("/api/hosting/v2/sessions").__module__ == (
        "app.api.intelligent_hosting_compat"
    )
    assert _first_endpoint("/assets/{tenant_slug}/{workspace_key}/").__module__ == (
        "app.api.hosted_runtime_gateway"
    )


def test_elastic_quota_rounds_to_units_without_one_step_gate() -> None:
    assert allocation_target_bytes(1) == WORKSPACE_QUOTA_STEP_BYTES
    assert allocation_target_bytes(WORKSPACE_QUOTA_STEP_BYTES) == WORKSPACE_QUOTA_STEP_BYTES
    assert allocation_target_bytes(WORKSPACE_QUOTA_STEP_BYTES + 1) == (
        2 * WORKSPACE_QUOTA_STEP_BYTES
    )
    assert allocation_target_bytes(
        3 * WORKSPACE_QUOTA_STEP_BYTES,
        current_bytes=5 * WORKSPACE_QUOTA_STEP_BYTES,
    ) == 5 * WORKSPACE_QUOTA_STEP_BYTES
    assert estimate_record_write_bytes({"name": "example"}) >= 1024 * 1024


def test_node_runtime_uses_mutable_cache_and_supports_build_only_frontends() -> None:
    controller = runtime_controller.RuntimeController(Settings())
    _name, spec, port, health_path = controller._container_spec(
        {
            "id": "00000000-0000-0000-0000-000000000101",
            "workspace_id": "00000000-0000-0000-0000-000000000102",
            "runtime_family": "node",
            "component_kind": "backend",
            "entrypoint": "server.js",
            "execution_contract": {"port": 8080, "health_path": "/health"},
            "resource_limits": {},
            "requested_config": {},
            "image_ref": "node:20-alpine",
            "runtime_environment": {"DATABASE_URL": "postgresql://workspace/fixture"},
            "sha256": "a" * 64,
        },
        Path("/host/source"),
        Path("/host/data"),
    )

    command = spec["Cmd"][-1]
    assert port == 8080
    assert health_path == "/health"
    assert "/workspace/data/.runtime/node/" in command
    assert 'cp -a /workspace/app/. "$SOURCE_ROOT/"' in command
    assert "npm ci" in command
    assert "--omit=dev" not in command
    assert "npm run build" in command
    assert "WAREHOUSE_STATIC_ROOT" in command
    assert "exec npm start" in command
    assert "DATABASE_URL=postgresql://workspace/fixture" in spec["Env"]


def test_runtime_failure_diagnostic_identifies_failed_stage() -> None:
    diagnostic = runtime_controller._diagnostic(
        RuntimeError("Runtime health probe failed: HTTP 500")
    )
    assert diagnostic["stage"] == "runtime.health"
    assert diagnostic["component"] == "runtime"
    assert diagnostic["error_code"] == "runtime_health_failed"
    assert diagnostic["retryable"] is True
    assert diagnostic["next_action"]


class _ProxyClient:
    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        self.requests: list[dict[str, object]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.response


def test_gateway_preserves_app_auth_cookie_body_redirect_and_cookie_scope(monkeypatch) -> None:
    upstream_response = httpx.Response(
        307,
        headers=[
            ("content-type", "text/html; charset=utf-8"),
            ("location", "/landing"),
            ("set-cookie", "session=abc; Path=/; HttpOnly"),
        ],
        content=b'<html><head></head><body><script src="/app.js"></script></body></html>',
        request=httpx.Request("POST", "http://runtime:8080/echo"),
    )
    client = _ProxyClient(upstream_response)
    monkeypatch.setattr(
        hosted_runtime_gateway,
        "active_workspace_runtime",
        lambda *_args: {
            "kind": "proxy",
            "internal_url": "http://runtime:8080",
            "internal_urls": ["http://runtime:8080"],
            "deployment_id": "00000000-0000-0000-0000-000000000103",
        },
    )
    monkeypatch.setattr(
        hosted_runtime_gateway.httpx,
        "AsyncClient",
        lambda **_kwargs: client,
    )

    response = TestClient(app).post(
        "/assets/bonfire/example/echo?mode=test",
        headers={
            "Authorization": "Bearer user-application-token",
            "Cookie": "theme=dark",
            "X-Request-ID": "request-103",
        },
        json={"hello": "world"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == "/assets/bonfire/example/landing"
    assert "Path=/assets/bonfire/example/" in response.headers["set-cookie"]
    assert response.headers["x-warehouse-deployment"].endswith("0103")
    assert "/assets/bonfire/example/app.js" in response.text
    assert "__WAREHOUSE_WORKSPACE_PREFIX__" in response.text

    sent = client.requests[0]
    sent_headers = httpx.Headers(sent["headers"])
    assert sent["url"] == "http://runtime:8080/echo?mode=test"
    assert sent_headers["authorization"] == "Bearer user-application-token"
    assert sent_headers["cookie"] == "theme=dark"
    assert sent_headers["x-forwarded-prefix"] == "/assets/bonfire/example"
    assert json.loads(sent["content"]) == {"hello": "world"}


def test_workspace_errors_keep_detail_and_add_exact_diagnostic() -> None:
    response = TestClient(app).post(
        "/api/workspaces/v1/sources/upload",
        files={"file": ("source.tar.gz", b"not-an-archive", "application/gzip")},
    )
    assert response.status_code == 401
    payload = response.json()
    assert payload["detail"] == "Workspace key is required"
    assert payload["diagnostic"]["stage"] == "source.upload"
    assert payload["diagnostic"]["component"] == "source"
    assert payload["diagnostic"]["request_id"]
