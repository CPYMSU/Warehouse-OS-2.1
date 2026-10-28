from contextlib import contextmanager
from datetime import UTC, datetime
import json
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.api import full_stack_identity, router
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, decode_access_token
from app.main import app
from app.services import auth_sessions


@pytest.fixture
def client_and_state(monkeypatch):
    user, tenant_a, tenant_b = UUID(int=1), UUID(int=2), UUID(int=3)
    settings = Settings(environment="production", public_origin="https://bonfirework.org",
                        jwt_secret="j" * 40, integration_secret="i" * 40,
                        webauthn_rp_id="bonfirework.org", webauthn_origins=["https://bonfirework.org"],
                        cors_origins=["https://bonfirework.org", "https://www.bonfirework.org"])
    account = {"id": user, "username": "test", "display_name": "Test", "password_hash": "initial-password-hash", "active": True}
    tenants = {tenant_a: {"id": tenant_a, "slug": "alpha", "name": "Alpha", "industry_template_key": "x", "status": "active"},
               tenant_b: {"id": tenant_b, "slug": "beta", "name": "Beta", "industry_template_key": "x", "status": "active"}}
    state = {"account": account, "tenants": tenants, "memberships": {tenant_a, tenant_b}, "records": {}}

    class Result:
        def __init__(self, value=None): self.value = value
        def mappings(self): return self
        def one_or_none(self): return self.value
        def scalar_one_or_none(self): return self.value

    class Session:
        def __init__(self, tenant=None): self.tenant = tenant
        def execute(self, statement, params=None):
            sql, p = str(statement), params or {}
            if "set_config('app.tenant_id'" in sql:
                self.tenant = UUID(str(p["tenant"]))
                return Result()
            if sql.startswith("INSERT INTO compatibility.documents"):
                state["records"][(p["tenant"], p["key"])] = {"payload": json.loads(p["payload"]), "status": "active"}
                return Result()
            if "SELECT payload FROM compatibility.documents" in sql:
                row = state["records"].get((p["tenant"], p["key"]))
                return Result(row["payload"] if row and row["status"] == "active" else None)
            if "UPDATE compatibility.documents SET status='archived'" in sql:
                state["records"][(p["tenant"], p["key"])]["status"] = "archived"
                return Result()
            if "FROM iam.passkeys" in sql:
                return Result({"user_id": user, "credential_public_key": b"public-key", "sign_count": 0,
                               "rp_id": "bonfirework.org"})
            if "UPDATE iam.passkeys" in sql:
                return Result()
            if "FROM iam.users" in sql:
                ok = state["account"]["active"] and (p.get("id") == user or p.get("username") == "test")
                return Result(dict(state["account"]) if ok else None)
            if "FROM iam.memberships m JOIN iam.tenants" in sql:
                tenant = tenants.get(p["tenant"])
                return Result(1 if p["tenant"] in state["memberships"] and tenant and tenant["status"] == "active" else None)
            if "SELECT id,slug FROM iam.tenants" in sql:
                tenant = next((t for t in tenants.values() if (p.get("id") == t["id"] or p.get("slug") == t["slug"]) and t["status"] == "active"), None)
                return Result(tenant)
            if "SELECT 1 FROM iam.memberships WHERE" in sql:
                return Result(1 if p["tenant"] == self.tenant and p["tenant"] in state["memberships"] and p["user_id"] == user else None)
            raise AssertionError("Unexpected SQL: " + sql)

    @contextmanager
    def tenant_session(tenant, actor=None):
        yield Session(tenant)

    @contextmanager
    def system_session():
        yield Session()

    def active_memberships(user_id):
        return [{**t, "role_level": 10, "topology_level": 1, "topology_title": "Member"}
                for t in tenants.values() if t["id"] in state["memberships"] and t["status"] == "active"]

    monkeypatch.setattr(auth_sessions, "tenant_session", tenant_session)
    monkeypatch.setattr(auth_sessions, "system_session", system_session)
    monkeypatch.setattr(full_stack_identity, "system_session", system_session)
    monkeypatch.setattr(full_stack_identity, "_active_memberships", active_memberships)
    monkeypatch.setattr(full_stack_identity, "_is_owner", lambda _id: False)
    monkeypatch.setattr(full_stack_identity, "verify_password", lambda supplied, stored: supplied == "correct")
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        with TestClient(app, base_url="https://bonfirework.org") as client:
            yield client, state, settings, user, tenant_a, tenant_b
    finally:
        app.dependency_overrides.pop(get_settings, None)


def login(client):
    return client.post("/api/auth/login", json={"username": "test", "password": "correct", "tenant": "alpha"},
                       headers={"Origin": "https://bonfirework.org", "Sec-Fetch-Site": "same-origin"})


def refresh(client, tenant="alpha", origin="https://bonfirework.org", site="same-origin"):
    return client.post("/api/auth/refresh", json={"tenant": tenant}, headers={"Origin": origin, "Sec-Fetch-Site": site})


def test_real_login_route_issues_bounded_cookie_and_renews_both_memberships(client_and_state):
    client, state, settings, user, tenant_a, tenant_b = client_and_state
    result = login(client)
    assert result.status_code == 200
    header = result.headers["set-cookie"].lower()
    assert "secure" in header and "httponly" in header and "samesite=lax" in header
    assert "path=/api/auth" in header and "max-age=604800" in header and "domain=" not in header
    record = next(iter(state["records"].values()))["payload"]
    assert record["password_fingerprint"] != state["account"]["password_hash"]
    assert "secret" not in record and "password_hash" not in record
    for requested, expected_tenant in (("alpha", tenant_a), ("beta", tenant_b), ("alpha", tenant_a)):
        response = refresh(client, requested)
        assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
        assert "set-cookie" not in response.headers
        assert decode_access_token(settings=settings, token=response.json()["token"]) == (user, expected_tenant)
    state["memberships"].remove(tenant_b)
    assert refresh(client, "beta").status_code == 403
    assert refresh(client, "alpha").status_code == 200


def test_cookie_csrf_logout_and_legacy_login(client_and_state):
    client, state, *_ = client_and_state
    assert client.post("/api/auth/refresh", json={}, headers={"Origin": "https://bonfirework.org"}).status_code == 401
    assert login(client).status_code == 200
    assert refresh(client, origin="https://www.bonfirework.org", site="same-site").status_code == 403
    assert refresh(client, origin="null", site="cross-site").status_code == 403
    assert client.post("/api/auth/logout", headers={"Origin": "https://evil.example"}).status_code == 403
    assert refresh(client).status_code == 200
    logout = client.post("/api/auth/logout", headers={"Origin": "https://bonfirework.org", "Sec-Fetch-Site": "same-origin"})
    assert logout.status_code == 204 and "set-cookie" not in logout.headers
    assert refresh(client).status_code == 401
    assert next(iter(state["records"].values()))["status"] == "archived"
    # Legacy non-browser API clients still receive their access token, but no long-lived cookie.
    legacy = client.post("/api/auth/login", json={"username": "test", "password": "correct", "tenant": "alpha"})
    assert legacy.status_code == 200 and "token" in legacy.json() and "set-cookie" not in legacy.headers


def test_passkey_route_issues_the_same_bounded_refresh_session(client_and_state, monkeypatch):
    client, _state, *_ = client_and_state
    monkeypatch.setattr(full_stack_identity, "_consume_challenge", lambda *_: {"challenge": "AA", "user_id": UUID(int=1)})
    monkeypatch.setattr(full_stack_identity, "verify_authentication_response", lambda **_kwargs: SimpleNamespace(
        new_sign_count=1, credential_device_type=SimpleNamespace(value="single_device"), credential_backed_up=False))
    result = client.post("/api/auth/passkeys/login/verify", json={"request_id": "test", "credential": {"id": "test"}},
                         headers={"Origin": "https://bonfirework.org", "Sec-Fetch-Site": "same-origin"})
    assert result.status_code == 200 and "httponly" in result.headers["set-cookie"].lower()
    assert refresh(client).status_code == 200


def test_password_changed_during_login_is_not_promoted_to_a_session(client_and_state, monkeypatch):
    client, state, *_ = client_and_state
    original_memberships = full_stack_identity._active_memberships
    def change_password_before_issuance(user_id):
        memberships = original_memberships(user_id)
        state["account"]["password_hash"] = "changed-during-login"
        return memberships
    monkeypatch.setattr(full_stack_identity, "_active_memberships", change_password_before_issuance)
    result = login(client)
    assert result.status_code == 401 and "set-cookie" not in result.headers
    assert state["records"] == {}


def test_tokens_issued_in_same_second_have_distinct_identity(client_and_state):
    _client, _state, settings, user, tenant, _other = client_and_state
    first = create_access_token(settings=settings, user_id=user, tenant_id=tenant)
    second = create_access_token(settings=settings, user_id=user, tenant_id=tenant)
    assert first != second
    assert decode_access_token(settings=settings, token=first) == (user, tenant)
    assert decode_access_token(settings=settings, token=second) == (user, tenant)


@pytest.mark.parametrize("invalidator", ["password", "user", "tenant", "expiry", "membership"])
def test_session_cannot_renew_after_identity_invalidation(client_and_state, invalidator):
    client, state, _settings, _user, tenant_a, _tenant_b = client_and_state
    assert login(client).status_code == 200
    if invalidator == "password": state["account"]["password_hash"] = "changed-password-hash"
    if invalidator == "user": state["account"]["active"] = False
    if invalidator == "tenant": state["tenants"][tenant_a]["status"] = "suspended"
    if invalidator == "membership": state["memberships"].remove(tenant_a)
    if invalidator == "expiry": next(iter(state["records"].values()))["payload"]["expires_at"] = int(datetime.now(UTC).timestamp()) - 1
    assert refresh(client).status_code == 401
