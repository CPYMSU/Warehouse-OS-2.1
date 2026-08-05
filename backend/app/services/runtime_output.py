"""Single public-output boundary for every Warehouse Intelligence surface."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence

from app.services.language_contract import localized_structure_failure

INTERNAL_MESSAGE_MARKERS = frozenset(
    {
        "interaction_mode",
        "understood_goal",
        "needs_tools",
        "requires_user_input",
        "selected_domains",
        "selected_families",
        "selected_tool_names",
        "context_requests",
        "success_criteria",
        "uncertainties",
        "reasoning",
        "memory_depth",
        "next_decisions",
        "continue_autonomously",
    }
)
SECRET_PATTERNS = (
    re.compile(r"\bwak_[A-Za-z0-9._~-]{12,}\b"),
    re.compile(r"\bwsk_[A-Za-z0-9._~-]{12,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"postgres(?:ql)?(?:\+psycopg)?://[^\s<>'\"]+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~-]{12,}\b", re.IGNORECASE),
)
PRIVATE_DATA_KEYS = frozenset(
    {
        *INTERNAL_MESSAGE_MARKERS,
        "authorization",
        "authorization_header",
        "authorization_keychain_id",
        "access_token",
        "api_key",
        "credential",
        "credentials",
        "database_dsn",
        "database_uri",
        "database_url",
        "decision_reasoning",
        "dsn",
        "error",
        "exception",
        "password",
        "passkey",
        "private_key",
        "provider_api_key",
        "raw",
        "raw_response",
        "refresh_token",
        "secret",
        "stack",
        "system_prompt",
        "token",
        "traceback",
        "user_prompt",
    }
)


def _json_mapping(value: str) -> dict[str, object] | None:
    candidate = value.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        parsed = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def contains_internal_runtime_payload(value: object) -> bool:
    """Identify a model control envelope that must never become chat prose."""

    message = str(value or "").strip()
    if not message:
        return False
    parsed = _json_mapping(message)
    if isinstance(parsed, dict):
        key_count = len(INTERNAL_MESSAGE_MARKERS.intersection(parsed))
        if key_count >= 2:
            return True
    quoted_markers = sum(
        f'"{marker}"' in message or f"'{marker}'" in message
        for marker in INTERNAL_MESSAGE_MARKERS
    )
    if quoted_markers >= 2:
        return True
    lowered = message.lower()
    return any(
        marker in lowered
        for marker in (
            "language contract:",
            "layered_world=",
            "responsibility_for_selected_genes=",
            "traceback (most recent call last)",
            "system_prompt",
            "router_world",
        )
    )


def public_message(value: object, *, locale: str, fallback: str | None = None) -> str:
    """Apply the final model-to-human firewall and redact credential shapes."""

    message = str(value or "").strip()
    safe_fallback = (
        localized_structure_failure(locale) if fallback is None else fallback
    )
    if not message or contains_internal_runtime_payload(message):
        return safe_fallback
    message = message[:24_000]
    for pattern in SECRET_PATTERNS:
        message = pattern.sub("[安全憑證卡]", message)
    return message.strip() or safe_fallback


def public_plan_steps(values: object, *, locale: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return ()
    steps: list[str] = []
    for value in values[:12]:
        step = public_message(value, locale=locale, fallback="")
        if step and not contains_internal_runtime_payload(step):
            steps.append(step[:800])
    return tuple(steps)


def public_data(value: object, *, locale: str, depth: int = 0) -> object:
    """Project structured data onto a bounded, non-secret public shape.

    Business results remain visible, while model control fields, prompts,
    credentials and raw diagnostics stay in protected audit storage.
    """

    if depth >= 8:
        return "[資料層級已截斷]"
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for raw_key, item in list(value.items())[:200]:
            key = str(raw_key)
            if key.lower() in PRIVATE_DATA_KEYS:
                continue
            result[key] = public_data(item, locale=locale, depth=depth + 1)
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [
            public_data(item, locale=locale, depth=depth + 1)
            for item in list(value)[:200]
        ]
    if isinstance(value, str):
        return public_message(value, locale=locale, fallback="")[:24_000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return public_message(str(value), locale=locale, fallback="")[:24_000]
