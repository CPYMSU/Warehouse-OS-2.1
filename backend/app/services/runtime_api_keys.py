"""Tenant-bound credentials for the shared AI secretary and Super Terminal.

The credential limits which Runtime ingress may be called. It is never a
permission snapshot: every request reloads the owner's active membership,
combined positions, permission ceilings, overrides, and current tenant state.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import text

from app.core.config import Settings
from app.db.session import system_session, tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext

KEY_PREFIX = "wsk"
DEFAULT_EXPIRY_DAYS = 30
MAX_EXPIRY_DAYS = 365
MAX_ACTIVE_KEYS_PER_USER = 10
SCOPE_PERMISSIONS = {
    "assistant": ("ai.use",),
    "terminal": ("terminal.use",),
    "research": ("research.read", "research.write", "research.review"),
}
# Compatibility projection for callers and documentation that need one
# representative permission name. Authorization uses ``SCOPE_PERMISSIONS``.
SCOPE_PERMISSION = {
    scope: permissions[0] for scope, permissions in SCOPE_PERMISSIONS.items()
}
SCOPE_ORDER = tuple(SCOPE_PERMISSION)
_TENANT_PATTERN = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
_KEY_RE = re.compile(
    rf"^{KEY_PREFIX}_({_TENANT_PATTERN})_([a-f0-9]{{12}})_([A-Za-z0-9_-]{{32,}})$"
)


class RuntimeApiKeyError(ValueError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class RuntimeApiCredential:
    key_id: int
    tenant_id: UUID
    tenant_slug: str
    user_id: UUID
    scopes: frozenset[str]
    key_hint: str


def _hash_key(plain: str, settings: Settings) -> str:
    """Return a peppered, domain-separated digest; plaintext is never stored."""
    material = f"warehouse-runtime-api:v1:{plain}".encode()
    return hmac.new(settings.integration_secret.encode(), material, hashlib.sha256).hexdigest()


def _allowed_scopes(actor: ActorContext) -> list[str]:
    return [
        scope
        for scope in SCOPE_ORDER
        if any(
            permission in actor.permissions
            for permission in SCOPE_PERMISSIONS[scope]
        )
    ]


def _require_interactive_manager(
    actor: ActorContext,
    *,
    required_scope: str | None = None,
) -> None:
    if actor.auth_kind != "session":
        raise RuntimeApiKeyError(
            "Runtime API Key cannot issue, list, or revoke another Runtime API Key",
            403,
        )
    if required_scope is not None:
        permissions = SCOPE_PERMISSIONS.get(required_scope)
        if permissions is None:
            raise RuntimeApiKeyError(f"Unsupported Runtime API scope: {required_scope}")
        if not any(permission in actor.permissions for permission in permissions):
            raise RuntimeApiKeyError(
                f"Current account cannot manage {required_scope} Runtime API Keys",
                403,
            )
        return
    if not any(
        permission in actor.permissions
        for permissions in SCOPE_PERMISSIONS.values()
        for permission in permissions
    ):
        raise RuntimeApiKeyError("Current account cannot manage Runtime API Keys", 403)


def _normalize_scopes(value: object, actor: ActorContext) -> list[str]:
    allowed = _allowed_scopes(actor)
    if value in (None, ""):
        requested = list(allowed)
    elif isinstance(value, str):
        requested = [part.strip().lower() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        requested = [str(part).strip().lower() for part in value if str(part).strip()]
    else:
        raise RuntimeApiKeyError("scopes must be an array or comma-separated string")
    unknown = sorted(set(requested).difference(SCOPE_ORDER))
    if unknown:
        raise RuntimeApiKeyError(f"Unsupported Runtime API scope: {', '.join(unknown)}")
    denied = sorted(set(requested).difference(allowed))
    if denied:
        raise RuntimeApiKeyError(
            f"Current account cannot issue these Runtime API scopes: {', '.join(denied)}",
            403,
        )
    selected = [scope for scope in SCOPE_ORDER if scope in set(requested)]
    if not selected:
        raise RuntimeApiKeyError("At least one Runtime API scope is required")
    return selected


def tenant_slug_from_key(plain: object) -> str | None:
    match = _KEY_RE.fullmatch(str(plain or "").strip())
    return match.group(1) if match else None


def _key_parts(plain: object) -> tuple[str, str]:
    match = _KEY_RE.fullmatch(str(plain or "").strip())
    if not match:
        raise RuntimeApiKeyError("Invalid Runtime API Key", 401)
    return match.group(1), match.group(2)


def issue_runtime_api_key(
    actor: ActorContext,
    settings: Settings,
    payload: dict[str, object],
) -> dict[str, object]:
    _require_interactive_manager(actor)
    unknown = set(payload).difference({"label", "name", "scopes", "expires_in_days", "days"})
    if unknown:
        raise RuntimeApiKeyError(f"Unknown Runtime API Key fields: {', '.join(sorted(unknown))}")
    label = str(payload.get("label") or payload.get("name") or "Runtime API").strip()
    if not label or len(label) > 80 or any(not character.isprintable() for character in label):
        raise RuntimeApiKeyError("Runtime API Key label must contain 1 to 80 visible characters")
    scopes = _normalize_scopes(payload.get("scopes"), actor)
    raw_days = payload.get("expires_in_days", payload.get("days", DEFAULT_EXPIRY_DAYS))
    if isinstance(raw_days, bool):
        raise RuntimeApiKeyError("days must be an integer")
    try:
        days = int(raw_days)
    except (TypeError, ValueError) as exc:
        raise RuntimeApiKeyError("days must be an integer") from exc
    if not 1 <= days <= MAX_EXPIRY_DAYS:
        raise RuntimeApiKeyError(f"days must be between 1 and {MAX_EXPIRY_DAYS}")

    public_id = secrets.token_hex(6)
    secret = secrets.token_urlsafe(32)
    plain = f"{KEY_PREFIX}_{actor.tenant_slug}_{public_id}_{secret}"
    hint = f"{KEY_PREFIX}_{actor.tenant_slug}_{public_id}_····{secret[-4:]}"
    expires_at = datetime.now(UTC) + timedelta(days=days)
    with tenant_session(actor.tenant_id) as session:
        active_count = session.execute(
            text(
                """
                SELECT count(*) FROM iam.runtime_api_keys
                WHERE owner_user_id = :owner_user_id
                  AND revoked_at IS NULL AND expires_at > now()
                """
            ),
            {"owner_user_id": actor.user_id},
        ).scalar_one()
        if int(active_count) >= MAX_ACTIVE_KEYS_PER_USER:
            raise RuntimeApiKeyError(
                f"Each account may keep at most {MAX_ACTIVE_KEYS_PER_USER} active Runtime API Keys",
                409,
            )
        key_id = session.execute(
            text(
                """
                INSERT INTO iam.runtime_api_keys(
                  tenant_id, owner_user_id, public_id, label, key_hash, key_hint,
                  scopes, expires_at, created_by_user_id
                ) VALUES (
                  :tenant_id, :owner_user_id, :public_id, :label, :key_hash, :key_hint,
                  CAST(:scopes AS jsonb), :expires_at, :created_by_user_id
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "public_id": public_id,
                "label": label,
                "key_hash": _hash_key(plain, settings),
                "key_hint": hint,
                "scopes": json.dumps(scopes),
                "expires_at": expires_at,
                "created_by_user_id": actor.user_id,
            },
        ).scalar_one()
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'runtime.api_key.issued',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {"key_id": int(key_id), "label": label, "scopes": scopes},
                    ensure_ascii=False,
                ),
            },
        )
    return {
        "ok": True,
        "key_id": int(key_id),
        "label": label,
        "api_key": plain,
        "key_hint": hint,
        "tenant_slug": actor.tenant_slug,
        "scopes": scopes,
        "expires_at": expires_at.isoformat(),
        "endpoints": {
            "assistant_stream": "/api/agent/run/stream",
            "terminal_execute": "/api/cli/exec",
            "research_api": "/api/research/projects",
            "research_upload": "/api/research/projects/{project_ref}/files",
            "identity": "/api/auth/me",
        },
        "note": "The plaintext API Key is shown once. Store it now and revoke it when unused.",
    }


def issue_research_api_key(
    actor: ActorContext,
    settings: Settings,
    payload: dict[str, object],
) -> dict[str, object]:
    """Issue a current-user/current-tenant credential fixed to research only."""
    _require_interactive_manager(actor, required_scope="research")
    unknown = set(payload).difference(
        {"label", "name", "expires_in_days", "days"}
    )
    if unknown:
        raise RuntimeApiKeyError(
            f"Unknown Research API Key fields: {', '.join(sorted(unknown))}"
        )
    result = issue_runtime_api_key(
        actor,
        settings,
        {**payload, "scopes": ["research"]},
    )
    result["research_cli"] = {
        "manifest": "/api/research/cli/manifest",
        "download": "/api/research/cli/download",
        "credential_environment": "WAREHOUSE_RESEARCH_KEY",
        "note": (
            "Pass this key through the environment or a chmod 600 key file; "
            "do not place it in shell history or command-line arguments."
        ),
    }
    return result


def list_runtime_api_keys(
    actor: ActorContext,
    *,
    required_scope: str | None = None,
) -> dict[str, object]:
    _require_interactive_manager(actor, required_scope=required_scope)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, label, key_hint, scopes, expires_at, revoked_at,
                           last_used_at, use_count, created_at
                    FROM iam.runtime_api_keys
                    WHERE owner_user_id = :owner_user_id
                    ORDER BY id DESC
                    """
                ),
                {"owner_user_id": actor.user_id},
            )
            .mappings()
            .all()
        )
    now = datetime.now(UTC)
    keys = []
    for raw in rows:
        item = dict(raw)
        item["expired"] = item["expires_at"] <= now
        item["active"] = not item["revoked_at"] and not item["expired"]
        item["scopes"] = list(item["scopes"] or [])
        if required_scope is not None and required_scope not in item["scopes"]:
            continue
        for field in ("expires_at", "revoked_at", "last_used_at", "created_at"):
            if item[field] is not None:
                item[field] = item[field].isoformat()
        keys.append(item)
    return {"ok": True, "keys": keys, "active": sum(1 for item in keys if item["active"])}


def revoke_runtime_api_key(
    actor: ActorContext,
    key_id: int,
    *,
    required_scope: str | None = None,
) -> dict[str, object]:
    _require_interactive_manager(actor, required_scope=required_scope)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, label, key_hint, scopes, revoked_at
                    FROM iam.runtime_api_keys
                    WHERE id = :key_id AND owner_user_id = :owner_user_id
                    """
                ),
                {"key_id": key_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise RuntimeApiKeyError("Runtime API Key not found", 404)
        if required_scope is not None and required_scope not in (row["scopes"] or []):
            raise RuntimeApiKeyError("Runtime API Key not found", 404)
        if row["revoked_at"] is not None:
            return {
                "ok": True,
                "key_id": key_id,
                "label": row["label"],
                "key_hint": row["key_hint"],
                "already_revoked": True,
            }
        revoked_at = datetime.now(UTC)
        session.execute(
            text(
                """
                UPDATE iam.runtime_api_keys
                SET revoked_at = :revoked_at, revoked_by_user_id = :actor_user_id
                WHERE id = :key_id AND revoked_at IS NULL
                """
            ),
            {
                "revoked_at": revoked_at,
                "actor_user_id": actor.user_id,
                "key_id": key_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'runtime.api_key.revoked',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps({"key_id": key_id}),
            },
        )
    return {
        "ok": True,
        "key_id": key_id,
        "label": row["label"],
        "key_hint": row["key_hint"],
        "revoked": True,
        "revoked_at": revoked_at.isoformat(),
    }


def authenticate_runtime_api_key(
    plain: str,
    settings: Settings,
) -> RuntimeApiCredential:
    tenant_slug, public_id = _key_parts(plain)
    with system_session() as session:
        tenant_id = session.execute(
            text("SELECT id FROM iam.tenants WHERE slug = :slug AND status = 'active'"),
            {"slug": tenant_slug},
        ).scalar_one_or_none()
    if tenant_id is None:
        raise RuntimeApiKeyError("Invalid Runtime API Key", 401)
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, owner_user_id, key_hash, key_hint, scopes,
                           expires_at, revoked_at
                    FROM iam.runtime_api_keys
                    WHERE public_id = :public_id
                    """
                ),
                {"public_id": public_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None or not hmac.compare_digest(
            str(row["key_hash"]), _hash_key(plain, settings)
        ):
            raise RuntimeApiKeyError("Invalid Runtime API Key", 401)
        if row["revoked_at"] is not None:
            raise RuntimeApiKeyError("Runtime API Key has been revoked", 401)
        if row["expires_at"] <= datetime.now(UTC):
            raise RuntimeApiKeyError("Runtime API Key has expired", 401)
        scopes = frozenset(str(scope) for scope in (row["scopes"] or []))
        if not scopes or not scopes.issubset(SCOPE_ORDER):
            raise RuntimeApiKeyError("Runtime API Key scopes are invalid", 401)
        session.execute(
            text(
                """
                UPDATE iam.runtime_api_keys
                SET last_used_at = now(), use_count = use_count + 1
                WHERE id = :key_id
                """
            ),
            {"key_id": row["id"]},
        )
    return RuntimeApiCredential(
        key_id=int(row["id"]),
        tenant_id=tenant_id,
        tenant_slug=tenant_slug,
        user_id=row["owner_user_id"],
        scopes=scopes,
        key_hint=str(row["key_hint"]),
    )
