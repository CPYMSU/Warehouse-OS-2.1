"""Bounded, revocable browser renewal sessions for the platform login.

The random bearer secret is delivered only in a host-only HttpOnly cookie;
the tenant-scoped store contains its hash, never the cookie itself. Sessions
have an absolute lifetime and are intentionally not rotated on refresh, so
simultaneous tabs cannot invalidate each other's in-flight renewals.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, Response
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session

COOKIE_NAME = "warehouse_refresh_session"
COOKIE_PATH = "/api/auth"
SESSION_NAMESPACE = "iam.refresh_session"
SESSION_SECONDS = 7 * 24 * 60 * 60
SECRET_PATTERN = re.compile(r"^[A-Za-z0-9_-]{43}$")


def same_origin(request: Request, settings: Settings) -> bool:
    """Only configured platform origins may exercise cookie-bearing actions."""
    origin = str(request.headers.get("origin") or "").strip().rstrip("/")
    allowed = {settings.public_origin.rstrip("/")} if settings.public_origin else set()
    # Browsers send Sec-Fetch-Site on current versions. Reject sibling-site
    # requests even when an administrator also lists that host in CORS.
    fetch_site = str(request.headers.get("sec-fetch-site") or "").lower()
    return bool(origin and origin != "null" and origin in allowed
                and fetch_site in ("", "same-origin"))


def require_same_origin(request: Request, settings: Settings) -> None:
    if not same_origin(request, settings):
        raise HTTPException(status_code=403, detail="A same-origin browser request is required")


def _secret_hash(secret: str) -> str:
    return hashlib.sha256(secret.encode("ascii")).hexdigest()


def _password_fingerprint(password_hash: str, settings: Settings) -> str:
    # A keyed digest avoids storing the password hash in the session record.
    return hmac.new(settings.jwt_secret.encode("utf-8"),
                    b"warehouse-refresh-password-v1\0" + password_hash.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def _parse_cookie(value: object) -> tuple[UUID, UUID, str] | None:
    if not isinstance(value, str) or len(value) > 160:
        return None
    try:
        version, tenant, identifier, secret = value.split(".")
        if version != "v1" or not SECRET_PATTERN.fullmatch(secret):
            return None
        return UUID(tenant), UUID(identifier), secret
    except (TypeError, ValueError):
        return None


def _account(user_id: UUID) -> dict[str, object] | None:
    with system_session() as session:
        row = session.execute(text("SELECT id,username,display_name,password_hash FROM iam.users "
                                   "WHERE id=:id AND active"), {"id": user_id}).mappings().one_or_none()
    return dict(row) if row is not None else None


def issue_session(request: Request, response: Response, *, user_id: UUID, tenant_id: UUID, settings: Settings,
                  expected_password_hash: str | None = None) -> bool:
    """Issue a cookie after a real login; legacy non-browser clients stay compatible."""
    if not same_origin(request, settings):
        return False
    account = _account(user_id)
    if account is None:
        raise HTTPException(status_code=401, detail="Session is no longer valid")
    # If a password was changed after verification, do not turn the old
    # credential into a session bound to the new password hash.
    if expected_password_hash is not None and not hmac.compare_digest(
        str(account["password_hash"]), expected_password_hash
    ):
        raise HTTPException(status_code=401, detail="Credentials changed; please sign in again")
    identifier = uuid4()
    secret = secrets.token_urlsafe(32)
    assert SECRET_PATTERN.fullmatch(secret)
    deadline = datetime.now(UTC) + timedelta(seconds=SESSION_SECONDS)
    payload = {"user_id": str(user_id), "secret_hash": _secret_hash(secret),
               "password_fingerprint": _password_fingerprint(str(account["password_hash"]), settings),
               "expires_at": int(deadline.timestamp())}
    with tenant_session(tenant_id, user_id) as session:
        session.execute(text("INSERT INTO compatibility.documents "
                             "(id,tenant_id,namespace,document_key,payload,source,updated_by) "
                             "VALUES (:id,:tenant,:namespace,:key,CAST(:payload AS jsonb),'native',:user_id)"),
                        {"id": uuid4(), "tenant": tenant_id, "namespace": SESSION_NAMESPACE,
                         "key": str(identifier), "payload": json.dumps(payload), "user_id": user_id})
    response.set_cookie(COOKIE_NAME, f"v1.{tenant_id}.{identifier}.{secret}",
                        max_age=SESSION_SECONDS, path=COOKIE_PATH, secure=settings.environment == "production",
                        httponly=True, samesite="lax")
    return True


@contextmanager
def authenticate_session(request: Request, settings: Settings):
    """Hold the session lock through token issuance, serializing logout."""
    require_same_origin(request, settings)
    parsed = _parse_cookie(request.cookies.get(COOKIE_NAME))
    invalid = HTTPException(status_code=401, detail="Refresh session is unavailable or expired")
    if parsed is None:
        raise invalid
    tenant_id, identifier, secret = parsed
    with tenant_session(tenant_id) as session:
        payload = session.execute(text("SELECT payload FROM compatibility.documents "
                                       "WHERE tenant_id=:tenant AND namespace=:namespace AND document_key=:key "
                                       "AND status='active' FOR UPDATE"),
                                  {"tenant": tenant_id, "namespace": SESSION_NAMESPACE,
                                   "key": str(identifier)}).scalar_one_or_none()
        if not isinstance(payload, dict):
            raise invalid
        try:
            user_id = UUID(str(payload["user_id"]))
            expires_at = int(payload["expires_at"])
            expected = str(payload["secret_hash"])
            fingerprint = str(payload["password_fingerprint"])
        except (KeyError, TypeError, ValueError):
            raise invalid from None
        if expires_at <= int(datetime.now(UTC).timestamp()) or not hmac.compare_digest(expected, _secret_hash(secret)):
            raise invalid
        account_row = session.execute(text("SELECT id,username,display_name,password_hash FROM iam.users "
                                           "WHERE id=:id AND active FOR SHARE"),
                                      {"id": user_id}).mappings().one_or_none()
        account = dict(account_row) if account_row is not None else None
        if account is None or not hmac.compare_digest(
            fingerprint, _password_fingerprint(str(account["password_hash"]), settings)
        ):
            raise invalid
        # The cookie's original tenant must remain active for this user;
        # authorization for a requested target tenant is checked separately.
        active = session.execute(text("SELECT 1 FROM iam.memberships m JOIN iam.tenants t ON t.id=m.tenant_id "
                                      "WHERE m.tenant_id=:tenant AND m.user_id=:user_id AND m.active AND t.status='active'"),
                                 {"tenant": tenant_id, "user_id": user_id}).scalar_one_or_none()
        if not active:
            raise invalid
        yield account, tenant_id, session


def revoke_session(request: Request, settings: Settings) -> None:
    """Revoke only the matching secret, including after access JWT expiry."""
    require_same_origin(request, settings)
    parsed = _parse_cookie(request.cookies.get(COOKIE_NAME))
    if parsed is None:
        return
    tenant_id, identifier, secret = parsed
    with tenant_session(tenant_id) as session:
        row = session.execute(text("SELECT payload FROM compatibility.documents WHERE tenant_id=:tenant "
                                   "AND namespace=:namespace AND document_key=:key AND status='active' FOR UPDATE"),
                              {"tenant": tenant_id, "namespace": SESSION_NAMESPACE,
                               "key": str(identifier)}).scalar_one_or_none()
        if isinstance(row, dict) and hmac.compare_digest(str(row.get("secret_hash") or ""), _secret_hash(secret)):
            session.execute(text("UPDATE compatibility.documents SET status='archived',version=version+1 "
                                 "WHERE tenant_id=:tenant AND namespace=:namespace AND document_key=:key"),
                            {"tenant": tenant_id, "namespace": SESSION_NAMESPACE, "key": str(identifier)})
    # Do not emit a delete-cookie response: an older logout response may arrive
    # after a different tab logs in and erase that newer valid cookie. The
    # revoked cookie is inert and the next login replaces it.
