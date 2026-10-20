"""Exercise the production static gateway without a database or network."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
import pytest
from app.api import hosted_runtime_gateway as gateway
from app.core.config import Settings
from fastapi import FastAPI, HTTPException
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


@pytest.fixture
def static_site(tmp_path: Path) -> tuple[Path, dict[str, object], Settings]:
    root = tmp_path / "release" / "site"
    root.mkdir(parents=True)
    (root / "index.html").write_text("<html><head></head><body>SPA HOME</body></html>")
    (root / "404.html").write_text(
        '<html><head></head><body>CUSTOM NOT FOUND<a href="/">Home</a></body></html>'
    )
    (root / "known.html").write_text("<html><body>EXISTING PAGE</body></html>")
    (root / "app.12345678.js").write_text("console.log('existing asset')")
    (root / "docs").mkdir()
    (root / "docs" / "index.html").write_text("<html><body>EXISTING DIRECTORY</body></html>")
    route = {
        "kind": "static",
        "runtime_rel_path": "release/site",
        "site_key": "test-site",
        "workspace_key": "test-site",
        "deployment_id": "00000000-0000-0000-0000-000000000005",
        "release_digest": "release-with-custom-404",
        "device_runtime": {"enabled": False},
    }
    return root, route, Settings(hosted_runtime_data_root=tmp_path)


def request(
    path: str,
    *,
    method: str = "GET",
    headers: dict[str, str] | None = None,
    pages_hostname: bool = False,
) -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": "/" + path,
            "headers": [(key.encode(), value.encode()) for key, value in (headers or {}).items()],
            "state": {"pages_hostname_route": {"site_key": "test-site"}} if pages_hostname else {},
        }
    )


def render(surface, route, settings, path, req, monkeypatch):
    if surface == "pages":
        return gateway._pages_static_response(route, path, req, settings)
    monkeypatch.setattr(gateway, "active_workspace_runtime", lambda *_args, **_kw: route)
    return asyncio.run(gateway.runtime_response("acme", "test-site", path, req, settings))


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize("path", ["unknown.html", "nested/unknown", "empty-directory/"])
@pytest.mark.parametrize("navigation", [{"accept": "text/html"}, {"sec-fetch-mode": "navigate"}])
def test_navigation_miss_uses_custom_404(static_site, surface, path, navigation, monkeypatch):
    root, route, settings = static_site
    (root / "empty-directory").mkdir()
    response = render(
        surface, route, settings, path, request(path, headers=navigation), monkeypatch
    )
    assert response.status_code == 404
    assert b"CUSTOM NOT FOUND" in response.body
    assert b"SPA HOME" not in response.body
    assert response.headers["cache-control"] == "no-store"
    assert "etag" not in response.headers
    assert "last-modified" not in response.headers
    assert response.headers["content-type"].startswith("text/html")
    assert int(response.headers["content-length"]) == len(response.body)
    assert response.headers["x-warehouse-release"] == route["release_digest"]
    assert response.headers["x-warehouse-deployment"] == route["deployment_id"]
    assert response.headers["x-content-type-options"] == "nosniff"
    if surface == "pages":
        assert response.headers["x-warehouse-pages-delivery"] == "static-device-first"
    else:
        assert b'href="/assets/acme/test-site/"' in response.body


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize("validator", ["previous-success", "*", '"unrelated"'])
def test_error_never_becomes_304_including_head(static_site, surface, validator, monkeypatch):
    _root, route, settings = static_site
    path = "unknown.html"
    if validator == "previous-success":
        validator = gateway._static_cache_headers(route, path, "text/html")["ETag"]
    headers = {
        "accept": "text/html",
        "if-none-match": validator,
        "if-modified-since": "Wed, 21 Oct 2099 07:28:00 GMT",
    }
    get_response = render(
        surface, route, settings, path, request(path, headers=headers), monkeypatch
    )
    head_response = render(
        surface, route, settings, path, request(path, method="HEAD", headers=headers), monkeypatch
    )
    assert get_response.status_code == head_response.status_code == 404
    assert head_response.body == b""
    assert head_response.headers == get_response.headers
    assert int(head_response.headers["content-length"]) == len(get_response.body)


@pytest.mark.parametrize("surface", ["pages", "compat"])
def test_head_error_is_bodyless_through_asgi(static_site, surface, monkeypatch):
    _root, route, settings = static_site
    monkeypatch.setattr(gateway, "pages_static_release", lambda *_a, **_kw: route)
    monkeypatch.setattr(gateway, "active_workspace_runtime", lambda *_a, **_kw: route)

    async def endpoint(req):
        if surface == "pages":
            req.state.pages_hostname_route = {"site_key": "test-site"}
        return await gateway.runtime_response("acme", "test-site", "unknown.html", req, settings)

    app = Starlette(routes=[Route("/unknown.html", endpoint, methods=["GET", "HEAD"])])

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test.invalid"
        ) as client:
            headers = {"accept": "text/html", "if-none-match": "*"}
            return (
                await client.get("/unknown.html", headers=headers),
                await client.head("/unknown.html", headers=headers),
            )

    get_response, head_response = asyncio.run(exercise())
    assert get_response.status_code == head_response.status_code == 404
    assert head_response.content == b""
    assert head_response.headers == get_response.headers
    assert int(head_response.headers["content-length"]) == len(get_response.content)


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize("path", ["", "known.html", "docs/", "app.12345678.js", "404.html"])
def test_existing_files_keep_success_and_conditional_cache(static_site, surface, path, monkeypatch):
    _root, route, settings = static_site
    response = render(
        surface, route, settings, path, request(path, headers={"accept": "text/html"}), monkeypatch
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] != "no-store"
    cached = render(
        surface,
        route,
        settings,
        path,
        request(path, headers={"accept": "text/html", "if-none-match": response.headers["etag"]}),
        monkeypatch,
    )
    assert cached.status_code == 304


@pytest.mark.parametrize("surface", ["pages", "compat"])
def test_no_custom_page_preserves_original_spa_fallback(static_site, surface, monkeypatch):
    root, route, settings = static_site
    (root / "404.html").unlink()
    path = "unknown/deep-route"
    response = render(
        surface, route, settings, path, request(path, headers={"accept": "text/html"}), monkeypatch
    )
    assert response.status_code == 200
    assert b"SPA HOME" in response.body
    if surface == "pages":
        response = render(
            surface,
            route,
            settings,
            "unknown.html",
            request("unknown.html", headers={"accept": "text/html"}),
            monkeypatch,
        )
        assert response.status_code == 200
    else:
        with pytest.raises(HTTPException) as exc:
            render(
                surface,
                route,
                settings,
                "unknown.html",
                request("unknown.html", headers={"accept": "text/html"}),
                monkeypatch,
            )
        assert exc.value.status_code == 404


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize(
    "path", ["api", "api/items", "missing.js", "image.png", "data.json", "manual.pdf"]
)
def test_api_and_known_asset_paths_never_use_custom_html(static_site, surface, path, monkeypatch):
    _root, route, settings = static_site
    req = request(path, headers={"accept": "text/html", "sec-fetch-mode": "navigate"})
    if surface == "pages":
        assert render(surface, route, settings, path, req, monkeypatch) is None
    else:
        with pytest.raises(HTTPException) as exc:
            render(surface, route, settings, path, req, monkeypatch)
        assert exc.value.status_code == 404


@pytest.mark.parametrize("destination", ["font", "image", "manifest", "script", "style"])
def test_explicit_asset_request_keeps_real_asset_404(static_site, destination):
    _root, route, settings = static_site
    with pytest.raises(HTTPException) as exc:
        gateway._pages_static_response(
            route,
            "missing-resource",
            request(
                "missing-resource", headers={"accept": "text/html", "sec-fetch-dest": destination}
            ),
            settings,
        )
    assert exc.value.status_code == 404
    assert exc.value.detail == "Pages asset not found"


@pytest.mark.parametrize("destination", ["audio", "video", "worker", "serviceworker", "object"])
def test_other_non_document_destinations_keep_runtime_fallthrough(static_site, destination):
    _root, route, settings = static_site
    assert (
        gateway._pages_static_response(
            route,
            "missing-resource",
            request(
                "missing-resource", headers={"accept": "text/html", "sec-fetch-dest": destination}
            ),
            settings,
        )
        is None
    )


def test_non_navigation_api_miss_reaches_existing_runtime(static_site, monkeypatch):
    _root, route, settings = static_site
    monkeypatch.setattr(gateway, "pages_static_release", lambda *_a, **_kw: route)
    monkeypatch.setattr(gateway, "active_workspace_runtime", lambda *_a, **_kw: {"kind": "proxy"})

    async def proxy_response(_route, runtime_path, *_args):
        assert runtime_path == "api/items"
        return JSONResponse({"from_runtime": True}, status_code=404)

    monkeypatch.setattr(gateway, "_proxy_response", proxy_response)
    response = asyncio.run(
        gateway.runtime_response(
            "acme",
            "test-site",
            "api/items",
            request("api/items", headers={"accept": "application/json"}, pages_hostname=True),
            settings,
        )
    )
    assert response.status_code == 404
    assert response.body == b'{"from_runtime":true}'


def test_pages_navigation_error_does_not_wake_runtime(static_site, monkeypatch):
    _root, route, settings = static_site
    monkeypatch.setattr(gateway, "pages_static_release", lambda *_a, **_kw: route)

    def unexpected_runtime(*_args, **_kw):
        pytest.fail("a static custom 404 must not wake the backend")

    monkeypatch.setattr(gateway, "active_workspace_runtime", unexpected_runtime)
    response = asyncio.run(
        gateway.runtime_response(
            "acme",
            "test-site",
            "missing.html",
            request("missing.html", headers={"accept": "text/html"}, pages_hostname=True),
            settings,
        )
    )
    assert response.status_code == 404


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize("escape_kind", ["requested-path", "custom-page-symlink"])
def test_escape_paths_never_disclose_external_files(static_site, surface, escape_kind, monkeypatch):
    root, route, settings = static_site
    outside = root.parent / "outside.html"
    outside.write_text("PRIVATE OUTSIDE CONTENT")
    path = "../outside.html"
    if escape_kind == "custom-page-symlink":
        (root / "404.html").unlink()
        (root / "404.html").symlink_to(outside)
        path = "missing.html"
    with pytest.raises(HTTPException) as exc:
        render(
            surface,
            route,
            settings,
            path,
            request(path, headers={"accept": "text/html"}),
            monkeypatch,
        )
    assert exc.value.status_code == 404
    assert "PRIVATE" not in str(exc.value.detail)


def test_custom_page_does_not_change_non_get_methods(static_site, monkeypatch):
    _root, route, settings = static_site
    req = request("unknown", method="POST", headers={"accept": "text/html"})
    assert gateway._pages_static_response(route, "unknown", req, settings) is None
    response = render("compat", route, settings, "unknown", req, monkeypatch)
    assert response.status_code == 200
    assert b"SPA HOME" in response.body


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize(
    "accept",
    [
        "text/html;q=0,application/json",
        " TEXT/HTML ; Q = 0 , application/json ",
        "application/json, text/html ; q=0.000",
        "text/html;q=invalid,application/json",
        "text/html;q=nan,application/json",
        "text/html;q=1.1,application/json",
        "text/html;q=-0.1,application/json",
        "text/html;q=.5,application/json",
        "text/html;q=0.0001,application/json",
        "text/html;q=,application/json",
        'text/html;q="0.5",application/json',
        "text/html;q=0.5;q=1,application/json",
        "text/html;q=0,*/*;q=1",
        "text/*;q=0,*/*;q=1",
        "application/json",
        "TEXT/HTML; Q=0.2, text/html; q=0",
    ],
)
def test_accept_rejecting_html_keeps_non_html_404(static_site, surface, accept, monkeypatch):
    _root, route, settings = static_site
    monkeypatch.setattr(gateway, "pages_static_release", lambda *_a, **_kw: route)
    active_route = {"kind": "proxy"} if surface == "pages" else route
    monkeypatch.setattr(gateway, "active_workspace_runtime", lambda *_a, **_kw: active_route)

    async def proxy_response(*_args):
        return JSONResponse({"detail": "Runtime file not found"}, status_code=404)

    monkeypatch.setattr(gateway, "_proxy_response", proxy_response)

    async def endpoint(req: Request):
        if surface == "pages":
            req.state.pages_hostname_route = {"site_key": "test-site"}
        return await gateway.runtime_response("acme", "test-site", "unknown.html", req, settings)

    app = FastAPI()
    app.add_api_route("/unknown.html", endpoint, methods=["GET", "HEAD"])

    async def exercise():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test.invalid"
        ) as client:
            return await client.get(
                "/unknown.html", headers={"accept": accept, "sec-fetch-mode": "navigate"}
            )

    response = asyncio.run(exercise())
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("application/json")
    assert "CUSTOM NOT FOUND" not in response.text


@pytest.mark.parametrize("surface", ["pages", "compat"])
@pytest.mark.parametrize(
    "accept",
    [
        "text/html",
        "text/html;q=1",
        "text/html;q=0.5",
        " text/html ; q = 0.001 , application/json ",
        "TEXT/HTML ; Q=1.000",
        "application/json, Text/Html ; charset=UTF-8 ; q = 0.8",
        "text/html;q=0.1,*/*;q=0",
        "*/*;q=0.5",
        "text/*;q=0.5",
        "text/html; charset=utf-8",
        None,
    ],
)
def test_accept_positive_html_quality_keeps_custom_404(static_site, surface, accept, monkeypatch):
    _root, route, settings = static_site
    headers = {"sec-fetch-mode": "navigate"}
    if accept is not None:
        headers["accept"] = accept
    response = render(
        surface,
        route,
        settings,
        "unknown.html",
        request("unknown.html", headers=headers),
        monkeypatch,
    )
    assert response.status_code == 404
    assert b"CUSTOM NOT FOUND" in response.body
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("surface", ["pages", "compat"])
def test_no_custom_page_retains_legacy_qzero_spa_fallback(static_site, surface, monkeypatch):
    root, route, settings = static_site
    (root / "404.html").unlink()
    response = render(
        surface,
        route,
        settings,
        "unknown",
        request("unknown", headers={"accept": "text/html;q=0,application/json"}),
        monkeypatch,
    )
    assert response.status_code == 200
    assert b"SPA HOME" in response.body
