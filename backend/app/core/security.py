from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError

from app.core.config import Settings

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except UnknownHashError:
        return verify_legacy_pbkdf2_sha256(password, password_hash)


def verify_legacy_pbkdf2_sha256(password: str, password_hash: str) -> bool:
    """Verify the legacy Django-style hash only during an account migration."""
    try:
        algorithm, rounds_text, salt, encoded_digest = password_hash.split("$", 3)
        rounds = int(rounds_text)
        if algorithm != "pbkdf2_sha256" or not 1 <= rounds <= 2_000_000 or not salt:
            return False
        salt_bytes = base64.b64decode(salt.encode("ascii"), validate=True)
        expected = base64.b64decode(encoded_digest.encode("ascii"), validate=True)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt_bytes, rounds
        )
    except (TypeError, ValueError, UnicodeEncodeError, binascii.Error):
        return False
    return hmac.compare_digest(actual, expected)


def needs_password_rehash(password_hash: str) -> bool:
    """Legacy hashes are upgraded to Argon2 after their first successful login."""
    return password_hash.startswith("pbkdf2_sha256$")


def create_access_token(*, settings: Settings, user_id: UUID, tenant_id: UUID) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_minutes)
    return jwt.encode(
        {"sub": str(user_id), "tenant_id": str(tenant_id), "exp": expires_at},
        settings.jwt_secret,
        algorithm="HS256",
    )


def decode_access_token(*, settings: Settings, token: str) -> tuple[UUID, UUID]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return UUID(str(payload["sub"])), UUID(str(payload["tenant_id"]))
    except (KeyError, ValueError, jwt.InvalidTokenError) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
