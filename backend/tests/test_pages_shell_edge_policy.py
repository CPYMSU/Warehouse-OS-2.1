"""Pages shells retain script isolation without edge analytics injection."""
from fastapi import Request
from app.api import hosted_runtime_gateway as gateway
from app.core.config import Settings


def test_pages_shell_prevents_edge_rewriting_without_relaxing_csp(monkeypatch):
    monkeypatch.setattr(gateway, "resolve_pages_site_key", lambda name: {"site_key": name})
    request = Request({"type": "http", "method": "GET", "scheme": "https",
                       "path": "/apps/mk5-ledger-system/", "query_string": b"",
                       "headers": [], "server": ("bonfirework.org", 443)})
    response = gateway._pages_shell_response("mk5-ledger-system", "", request, Settings())
    assert response.status_code == 200
    assert set(response.headers["cache-control"].split(", ")) == {"no-store", "no-transform"}
    policy = response.headers["content-security-policy"]
    assert "default-src 'none'" in policy
    assert "script-src" not in policy
    assert "frame-ancestors 'self'" in policy
    assert "static.cloudflareinsights.com" not in response.body.decode()
    assert "sandbox=" in response.body.decode()


def test_missing_pages_shell_stays_uncached_and_not_found(monkeypatch):
    monkeypatch.setattr(gateway, "resolve_pages_site_key", lambda name: None)
    request = Request({"type": "http", "method": "GET", "scheme": "https",
                       "path": "/apps/missing/", "query_string": b"", "headers": []})
    response = gateway._pages_shell_response("missing", "", request, Settings())
    assert response.status_code == 404
    assert response.headers["cache-control"] == "no-store"
