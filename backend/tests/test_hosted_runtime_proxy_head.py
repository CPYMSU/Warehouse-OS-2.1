"""Proxy HEAD must describe GET without manufacturing an HTML body."""

from __future__ import annotations

import asyncio

import httpx
import pytest
from starlette.requests import Request

from app.api import hosted_runtime_gateway as gateway


def _request(method: str) -> Request:
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "scheme": "https",
            "server": ("bonfirework.org", 443),
            "path": "/assets/acme/site/missing.html",
            "query_string": b"probe=x",
            "headers": [(b"host", b"bonfirework.org")],
        },
        receive,
    )


def _upstream(monkeypatch, status: int, content_type: str, content: bytes):
    calls = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, method, url, **kwargs):
            calls.append((method, url, kwargs))
            return httpx.Response(
                status,
                headers={
                    "Content-Type": content_type,
                    "Content-Length": "1423",
                    "Cache-Control": "no-store, no-transform",
                    "Vary": "Accept, Sec-Fetch-Dest",
                },
                content=content,
                request=httpx.Request(method, url),
            )

    monkeypatch.setattr(gateway.httpx, "AsyncClient", lambda **_kwargs: Client())
    return calls


def _proxy(req):
    return gateway._proxy_response(
        {"internal_url": "http://runtime:8080", "deployment_id": "fixture-deployment"},
        "missing.html",
        req,
        "acme",
        "site",
    )


@pytest.mark.parametrize("status", [200, 404, 304])
def test_html_head_never_rewrites_or_sends_body(monkeypatch, status):
    calls = _upstream(monkeypatch, status, "text/html; charset=utf-8", b"")

    def unexpected_rewrite(*_args, **_kwargs):
        raise AssertionError("HEAD must not rewrite the absent upstream representation")

    monkeypatch.setattr(gateway, "_rewrite_text", unexpected_rewrite)
    req = _request("HEAD")
    response = asyncio.run(_proxy(req))
    assert response.status_code == status
    assert response.body == b""
    assert "content-length" not in response.headers
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["cache-control"] == "no-store, no-transform"
    assert response.headers["vary"] == "Accept, Sec-Fetch-Dest"
    assert response.headers["x-warehouse-deployment"] == "fixture-deployment"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert [(method, url) for method, url, _kwargs in calls] == [
        ("HEAD", "http://runtime:8080/missing.html?probe=x")
    ]
    messages = []

    async def send(message):
        messages.append(message)

    asyncio.run(response(req.scope, req.receive, send))
    assert not any(message.get("body") for message in messages)
    assert not any(key.lower() == b"content-length" for key, _ in messages[0]["headers"])


def test_non_html_head_is_bodyless_without_claiming_an_unknown_length(monkeypatch):
    calls = _upstream(monkeypatch, 404, "application/json", b"")
    response = asyncio.run(_proxy(_request("HEAD")))
    assert response.status_code == 404
    assert response.body == b""
    assert "content-length" not in response.headers
    assert response.headers["content-type"] == "application/json"
    assert [method for method, _url, _kwargs in calls] == ["HEAD"]


@pytest.mark.parametrize("status", [200, 404])
def test_get_still_rewrites_html_and_reports_its_actual_length(monkeypatch, status):
    html = b'<html><head></head><body><a href="/">Home</a>UPSTREAM</body></html>'
    calls = _upstream(monkeypatch, status, "text/html; charset=utf-8", html)
    response = asyncio.run(_proxy(_request("GET")))
    assert response.status_code == status
    assert b"UPSTREAM" in response.body
    assert b'href="/assets/acme/site/"' in response.body
    assert b"window.__WAREHOUSE_WORKSPACE_PREFIX__" in response.body
    assert response.body != html
    assert int(response.headers["content-length"]) == len(response.body)
    assert response.headers["cache-control"] == "no-store, no-transform"
    assert response.headers["vary"] == "Accept, Sec-Fetch-Dest"
    assert [method for method, _url, _kwargs in calls] == ["GET"]
