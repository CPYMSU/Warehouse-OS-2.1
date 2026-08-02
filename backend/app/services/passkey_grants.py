"""Single-use, purpose-bound grants produced by a verified Passkey ceremony."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import tenant_session

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_step_up_grant(
    actor: ActorContext,
    *,
    token: str,
    purpose: object,
    resource: object,
    verification: dict[str, object],
    expires_in_seconds: int = 300,
) -> dict[str, object]:
    """Persist only a hash of a newly verified, one-time grant token."""

    normalized_purpose = str(purpose or "").strip()
    normalized_resource = resource if isinstance(resource, dict) else {}
    if not normalized_purpose:
        raise HTTPException(status_code=400, detail="Step-up purpose is required")
    expires_at = datetime.now(UTC) + timedelta(
        seconds=max(30, min(int(expires_in_seconds), 600))
    )
    grant_id = uuid4()
    resource_digest = _digest(normalized_resource)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO iam.step_up_grants(
                  id, tenant_id, user_id, token_hash, purpose, resource,
                  resource_digest, verification, expires_at
                ) VALUES (
                  :id, :tenant_id, :user_id, :token_hash, :purpose,
                  CAST(:resource AS jsonb), :resource_digest,
                  CAST(:verification AS jsonb), :expires_at
                )
                """
            ),
            {
                "id": grant_id,
                "tenant_id": actor.tenant_id,
                "user_id": actor.user_id,
                "token_hash": _token_hash(token),
                "purpose": normalized_purpose,
                "resource": _canonical(normalized_resource),
                "resource_digest": resource_digest,
                "verification": _canonical(verification),
                "expires_at": expires_at,
            },
        )
    return {
        "grant_id": str(grant_id),
        "resource_digest": resource_digest,
        "expires_at": expires_at.isoformat(),
    }


def consume_step_up_grant(
    session: Session,
    actor: ActorContext,
    *,
    token: object,
    purpose: str,
    resource: dict[str, object],
) -> dict[str, object]:
    """Atomically consume a grant bound to this tenant, user, purpose and resource."""

    candidate = str(token or "").strip()
    if not candidate:
        raise HTTPException(status_code=403, detail="Passkey verification is required")
    row = (
        session.execute(
            text(
                """
                SELECT id, purpose, resource, resource_digest, verification,
                       expires_at, used_at, created_at
                FROM iam.step_up_grants
                WHERE tenant_id = :tenant_id AND user_id = :user_id
                  AND token_hash = :token_hash
                FOR UPDATE
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "user_id": actor.user_id,
                "token_hash": _token_hash(candidate),
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=403, detail="Passkey grant is invalid")
    if row["used_at"] is not None:
        raise HTTPException(status_code=409, detail="Passkey grant was already used")
    if row["expires_at"] <= datetime.now(UTC):
        raise HTTPException(status_code=410, detail="Passkey grant has expired")
    expected_digest = _digest(resource)
    if str(row["purpose"]) != purpose or str(row["resource_digest"]) != expected_digest:
        raise HTTPException(
            status_code=403,
            detail="Passkey grant is bound to another operation",
        )
    stored_resource = row["resource"] if isinstance(row["resource"], dict) else {}
    if _canonical(stored_resource) != _canonical(resource):
        raise HTTPException(
            status_code=403,
            detail="Passkey grant resource does not match",
        )
    changed = session.execute(
        text(
            """
            UPDATE iam.step_up_grants
            SET used_at = now()
            WHERE id = :id AND used_at IS NULL AND expires_at > now()
            """
        ),
        {"id": row["id"]},
    )
    if changed.rowcount != 1:
        raise HTTPException(status_code=409, detail="Passkey grant was already consumed")
    verification = dict(row["verification"]) if isinstance(row["verification"], dict) else {}
    return {
        **verification,
        "verified": True,
        "method": "webauthn",
        "grant_id": str(row["id"]),
        "resource_digest": expected_digest,
    }
