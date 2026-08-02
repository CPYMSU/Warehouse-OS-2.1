"""Tenant-isolated integration secrets and outbound provider clients."""

from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext

SUPPORTED_PROVIDERS = frozenset({"deepseek", "vision", "voice", "tavily"})
DEEPSEEK_RUNTIME_MODELS = {
    "balanced": "deepseek-v4-flash",
    "thinking": "deepseek-v4-pro",
}
DEFAULTS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "model": DEEPSEEK_RUNTIME_MODELS["thinking"],
    },
    "tavily": {"base_url": "https://api.tavily.com", "model": "tavily-search"},
    "vision": {"base_url": "", "model": "auto"},
    "voice": {"base_url": "", "model": "auto"},
}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    latency_ms: int
    error: str | None = None


@dataclass(frozen=True)
class ModelConnection:
    """A tenant-scoped model connection for the shared Auto Runtime only."""

    base_url: str
    model: str
    api_key: str


def chat_completion(
    connection: ModelConnection,
    *,
    system_prompt: str,
    user_prompt: str,
    timeout: float = 60.0,
    thinking: bool | None = None,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """Use the tenant-scoped model connection through one shared boundary."""
    request: dict[str, object] = {
        "model": connection.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if thinking is not None:
        request["thinking"] = {
            "type": "enabled" if thinking else "disabled",
        }
    if max_tokens is not None:
        request["max_tokens"] = max_tokens
    if json_mode:
        request["response_format"] = {"type": "json_object"}
    response = httpx.post(
        f"{connection.base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {connection.api_key}",
            "Content-Type": "application/json",
        },
        json=request,
        timeout=timeout,
    )
    response.raise_for_status()
    try:
        message = response.json()["choices"][0]["message"].get("content")
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("AI provider returned an invalid response") from exc
    if not isinstance(message, str) or not message.strip():
        raise ValueError("AI provider returned an empty response")
    return message.strip()


def normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise ValueError("Unsupported integration provider")
    return normalized


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.integration_secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(secret: str, settings: Settings) -> str:
    return "fernet:v1:" + _fernet(settings).encrypt(secret.encode("utf-8")).decode("ascii")


def _decrypt(payload: dict[str, object], settings: Settings) -> str:
    encrypted = str(payload.get("secret_ciphertext") or "")
    if encrypted.startswith("fernet:v1:"):
        try:
            return _fernet(settings).decrypt(encrypted.removeprefix("fernet:v1:").encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Integration credential cannot be decrypted") from exc
    # One-way compatibility for credentials written by the former plaintext route.
    return str(payload.get("api_key") or "")


def _stored(actor: ActorContext, provider: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        value = session.execute(
            text(
                """
                SELECT payload FROM compatibility.documents
                WHERE namespace = :namespace AND document_key = 'default' AND status = 'active'
                """
            ),
            {"namespace": f"integration.{provider}"},
        ).scalar_one_or_none()
    return dict(value) if isinstance(value, dict) else {}


def _write(actor: ActorContext, provider: str, payload: dict[str, object]) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO compatibility.documents(
                  id, tenant_id, namespace, document_key, payload, source, updated_by
                ) VALUES (
                  :id, :tenant_id, :namespace, 'default', CAST(:payload AS jsonb),
                  'native', :updated_by
                )
                ON CONFLICT (tenant_id, namespace, document_key)
                DO UPDATE SET payload = EXCLUDED.payload, status = 'active',
                  source = EXCLUDED.source, version = compatibility.documents.version + 1,
                  updated_by = EXCLUDED.updated_by
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "namespace": f"integration.{provider}",
                "payload": json.dumps(payload, ensure_ascii=False),
                "updated_by": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (:tenant_id, :actor_user_id, 'integration.configuration.updated',
                        CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {"provider": provider, "configured": bool(payload.get("secret_ciphertext"))}
                ),
            },
        )


def public_state(actor: ActorContext, provider: str) -> dict[str, object]:
    provider = normalize_provider(provider)
    stored = _stored(actor, provider)
    configured = bool(stored.get("secret_ciphertext") or stored.get("api_key"))
    connection_status = str(
        stored.get("connection_status")
        or ("pending_validation" if configured else "not_configured")
    )
    connected = configured and connection_status == "connected"
    connection = {
        "ok": connected,
        "status": connection_status,
        "model": stored.get("model") or DEFAULTS[provider]["model"],
        "checked_at": stored.get("checked_at") or stored.get("updated_at"),
        "error": stored.get("last_error"),
    }
    state: dict[str, object] = {
        "provider": provider,
        "configured": configured,
        "connected": connected,
        "connection_status": connection_status,
        "masked_key": stored.get("key_hint") or ("••••" if configured else "—"),
        "model": stored.get("model") or DEFAULTS[provider]["model"],
        "base_url": stored.get("base_url") or DEFAULTS[provider]["base_url"],
        "updated_at": stored.get("updated_at"),
        "connection": connection,
    }
    if provider == "deepseek":
        state["runtime_models"] = dict(DEEPSEEK_RUNTIME_MODELS)
        state["memory_steward"] = {
            "model": DEEPSEEK_RUNTIME_MODELS["balanced"],
            "thinking": False,
            "execution": "background",
            "max_jobs_per_turn": 4,
        }
    return state


def _safe_generic_base_url(value: object) -> str:
    base_url = str(value or "").strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Vision/voice Base URL must be a public HTTPS endpoint")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".local"):
        raise ValueError("Private integration endpoints are not accepted")
    return base_url


def _provider_request(
    provider: str,
    secret: str,
    config: dict[str, object],
    *,
    timeout: float = 12.0,
) -> None:
    headers = {"Authorization": f"Bearer {secret}", "Content-Type": "application/json"}
    if provider == "deepseek":
        response = httpx.get(
            f"{DEFAULTS[provider]['base_url']}/models", headers=headers, timeout=timeout
        )
    elif provider == "tavily":
        response = httpx.post(
            f"{DEFAULTS[provider]['base_url']}/search",
            headers=headers,
            json={"query": "Warehouse OS connectivity check", "max_results": 1},
            timeout=timeout,
        )
    else:
        base_url = _safe_generic_base_url(config.get("base_url"))
        response = httpx.get(f"{base_url}/models", headers=headers, timeout=timeout)
    response.raise_for_status()


def validate_credentials(
    provider: str, secret: str, config: dict[str, object]
) -> ValidationResult:
    started = perf_counter()
    try:
        _provider_request(provider, secret, config)
    except (httpx.HTTPError, ValueError) as exc:
        return ValidationResult(
            ok=False,
            latency_ms=round((perf_counter() - started) * 1000),
            error=str(exc)[:500],
        )
    return ValidationResult(ok=True, latency_ms=round((perf_counter() - started) * 1000))


def save_configuration(
    actor: ActorContext,
    provider: str,
    api_key: str,
    payload: dict[str, object],
    settings: Settings,
) -> tuple[dict[str, object], ValidationResult]:
    provider = normalize_provider(provider)
    secret = api_key.strip()
    if not secret:
        raise ValueError("API key is required")
    config = {
        "provider": provider,
        "secret_ciphertext": _encrypt(secret, settings),
        "key_hint": f"{secret[:4]}…{secret[-4:]}" if len(secret) >= 10 else "••••",
        "model": str(payload.get("model") or DEFAULTS[provider]["model"]),
        "base_url": str(payload.get("base_url") or DEFAULTS[provider]["base_url"]),
        "updated_at": datetime.now(UTC).isoformat(),
        "connection_status": "pending_validation",
        "last_error": None,
    }
    result = validate_credentials(provider, secret, config)
    config.update(
        {
            "connection_status": "connected" if result.ok else "failed",
            "checked_at": datetime.now(UTC).isoformat(),
            "last_error": result.error,
        }
    )
    _write(actor, provider, config)
    return public_state(actor, provider), result


def validate_saved(
    actor: ActorContext, provider: str, settings: Settings
) -> tuple[dict[str, object], ValidationResult]:
    provider = normalize_provider(provider)
    stored = _stored(actor, provider)
    secret = _decrypt(stored, settings)
    if not secret:
        result = ValidationResult(False, 0, "API key is not configured")
        return public_state(actor, provider), result
    result = validate_credentials(provider, secret, stored)
    stored.pop("api_key", None)
    stored["secret_ciphertext"] = _encrypt(secret, settings)
    stored["key_hint"] = stored.get("key_hint") or (
        f"{secret[:4]}…{secret[-4:]}" if len(secret) >= 10 else "••••"
    )
    stored.update(
        {
            "connection_status": "connected" if result.ok else "failed",
            "checked_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "last_error": result.error,
        }
    )
    _write(actor, provider, stored)
    return public_state(actor, provider), result


def connected_deepseek(actor: ActorContext, settings: Settings) -> ModelConnection:
    """Return the validated model connection without exposing it to a surface.

    AI secretary, Super Terminal, embedded assistants, and mobile clients all
    enter Auto Runtime.  They must not receive a provider credential, command
    catalogue, or tool dispatcher of their own.
    """
    stored = _stored(actor, "deepseek")
    secret = _decrypt(stored, settings)
    if not secret:
        raise ValueError("AI engine is not configured for this company")
    if str(stored.get("connection_status")) != "connected":
        raise ValueError("AI engine key has not passed validation")
    return ModelConnection(
        # DeepSeek's connection check intentionally uses the canonical public
        # endpoint; surfaces must not turn a tenant configuration document into
        # an arbitrary outbound Runtime destination.
        base_url=str(DEFAULTS["deepseek"]["base_url"]).rstrip("/"),
        model=str(stored.get("model") or DEFAULTS["deepseek"]["model"]),
        api_key=secret,
    )
