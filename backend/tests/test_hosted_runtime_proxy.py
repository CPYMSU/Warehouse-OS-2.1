from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.api import digital_assets, hosted_runtime_gateway
from app.main import app


class _RuntimeClient:
    def __init__(self, *, docs_status: int) -> None:
        self.docs_status = docs_status
        self.requests: list[str] = []

    async def __aenter__(self) -> _RuntimeClient:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def request(self, method: str, url: str, **_kwargs: object) -> httpx.Response:
        self.requests.append(url)
        status = self.docs_status if url.endswith("/docs") else 404
        return httpx.Response(status, request=httpx.Request(method, url))


def test_api_entry_redirects_to_available_upstream_docs(monkeypatch) -> None:
    runtime_client = _RuntimeClient(docs_status=200)
    monkeypatch.setattr(
        hosted_runtime_gateway,
        "active_workspace_runtime",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        digital_assets,
        "active_workspace_runtime",
        lambda *_args: {
            "kind": "proxy",
            "internal_url": "http://runtime:8080",
            "internal_urls": ["http://runtime:8080"],
            "deployment_id": "00000000-0000-0000-0000-000000000091",
        },
    )
    monkeypatch.setattr(
        digital_assets.httpx,
        "AsyncClient",
        lambda **_kwargs: runtime_client,
    )

    response = TestClient(app).get(
        "/assets/bonfire/ai-architecture-platform/",
        follow_redirects=False,
    )

    assert response.status_code == 307
    assert response.headers["location"] == (
        "/assets/bonfire/ai-architecture-platform/docs"
    )
    assert response.headers["x-warehouse-deployment"] == (
        "00000000-0000-0000-0000-000000000091"
    )
    assert runtime_client.requests == ["http://runtime:8080/", "http://runtime:8080/docs"]


def test_api_entry_preserves_upstream_404_when_docs_are_unavailable(monkeypatch) -> None:
    runtime_client = _RuntimeClient(docs_status=404)
    monkeypatch.setattr(
        hosted_runtime_gateway,
        "active_workspace_runtime",
        lambda *_args: None,
    )
    monkeypatch.setattr(
        digital_assets,
        "active_workspace_runtime",
        lambda *_args: {
            "kind": "proxy",
            "internal_url": "http://runtime:8080",
            "internal_urls": ["http://runtime:8080"],
            "deployment_id": "00000000-0000-0000-0000-000000000092",
        },
    )
    monkeypatch.setattr(
        digital_assets.httpx,
        "AsyncClient",
        lambda **_kwargs: runtime_client,
    )

    response = TestClient(app).get(
        "/assets/bonfire/no-docs-app/",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.headers["x-warehouse-deployment"] == (
        "00000000-0000-0000-0000-000000000092"
    )


def test_gateway_waits_for_sleeping_runtime_to_pass_wake_health_gate(monkeypatch) -> None:
    runtime_client = _RuntimeClient(docs_status=404)
    states = iter(["wake_requested", "waking", "running"])
    observed: list[tuple[str, bool]] = []

    def active_runtime(
        _tenant: str,
        _workspace: str,
        *,
        register_request: bool = True,
    ) -> dict[str, object]:
        state = next(states)
        observed.append((state, register_request))
        return {
            "kind": "proxy",
            "internal_url": "http://runtime:8080",
            "internal_urls": ["http://runtime:8080"],
            "deployment_id": "00000000-0000-0000-0000-000000000093",
            "runtime_state": state,
        }

    async def no_wait(_seconds: float) -> None:
        return None

    monkeypatch.setattr(hosted_runtime_gateway, "active_workspace_runtime", active_runtime)
    monkeypatch.setattr(hosted_runtime_gateway.asyncio, "sleep", no_wait)
    monkeypatch.setattr(
        hosted_runtime_gateway.httpx,
        "AsyncClient",
        lambda **_kwargs: runtime_client,
    )

    response = TestClient(app).get(
        "/assets/bonfire/sleeping-api/health",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.headers["x-warehouse-deployment"].endswith("0093")
    assert observed == [
        ("wake_requested", True),
        ("waking", False),
        ("running", False),
    ]
