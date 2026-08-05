"""Wire-level invariants for Warehouse × Lighthouse federation v1."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

PROTOCOL = "warehouse-lighthouse-federation/v1"
MAX_MESSAGE_BYTES = 256 * 1024

WAREHOUSE_MESSAGE_TYPES = frozenset(
    {
        "run.offer",
        "run.input",
        "run.cancel",
        "operation.approval_granted",
        "operation.approval_denied",
        "message.ack",
    }
)
DEVICE_MESSAGE_TYPES = frozenset(
    {
        "message.ack",
        "instance.hello",
        "instance.heartbeat",
        "run.accepted",
        "run.rejected",
        "run.event",
        "operation.approval_required",
        "receipt.committed",
        "run.completed",
    }
)
_DIGEST_RE = re.compile(r"^[a-f0-9]{64}$")
_SENSITIVE_KEY_PARTS = (
    "authorization",
    "api_key",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
)


class LighthouseProtocolError(ValueError):
    pass


def _uuid(value: object, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError) as exc:
        raise LighthouseProtocolError(f"{field} must be a UUID") from exc


def redact_projection(value: Any, *, depth: int = 0) -> Any:
    """Remove obvious credential material before a server projection is stored."""

    if depth > 12:
        return "[redacted: nesting limit]"
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, child in value.items():
            key = str(raw_key)[:160]
            lowered = key.lower()
            if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
                result[key] = "[redacted]"
            else:
                result[key] = redact_projection(child, depth=depth + 1)
        return result
    if isinstance(value, list):
        return [redact_projection(item, depth=depth + 1) for item in value[:500]]
    if isinstance(value, str):
        return value[:32_768]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:2_000]


def make_envelope(
    message_type: str,
    payload: dict[str, object],
    *,
    message_id: UUID | str | None = None,
) -> dict[str, object]:
    if message_type not in WAREHOUSE_MESSAGE_TYPES:
        raise LighthouseProtocolError(f"Unsupported Warehouse message type: {message_type}")
    envelope = {
        "protocol": PROTOCOL,
        "message_id": _uuid(message_id or uuid4(), "message_id"),
        "type": message_type,
        "sent_at": datetime.now(UTC).isoformat(),
        "payload": payload,
    }
    if len(json.dumps(envelope, ensure_ascii=False).encode()) > MAX_MESSAGE_BYTES:
        raise LighthouseProtocolError("Federation message exceeds 256 KiB")
    return envelope


def parse_device_message(raw: object) -> dict[str, object]:
    if not isinstance(raw, dict):
        raise LighthouseProtocolError("Federation message must be an object")
    if len(json.dumps(raw, ensure_ascii=False).encode()) > MAX_MESSAGE_BYTES:
        raise LighthouseProtocolError("Federation message exceeds 256 KiB")
    if raw.get("protocol") != PROTOCOL:
        raise LighthouseProtocolError("Unsupported federation protocol")
    message_type = str(raw.get("type") or "")
    if message_type not in DEVICE_MESSAGE_TYPES:
        raise LighthouseProtocolError(f"Unsupported device message type: {message_type}")
    message_id = _uuid(raw.get("message_id"), "message_id")
    sent_at = str(raw.get("sent_at") or "").strip()
    if not sent_at or len(sent_at) > 80:
        raise LighthouseProtocolError("sent_at must be an RFC3339 timestamp")
    payload = raw.get("payload")
    if not isinstance(payload, dict):
        raise LighthouseProtocolError("payload must be an object")

    normalized = redact_projection(payload)
    assert isinstance(normalized, dict)
    if message_type.startswith(("run.", "operation.", "receipt.")):
        normalized["run_id"] = _uuid(normalized.get("run_id"), "payload.run_id")
    if message_type == "message.ack":
        normalized["message_id"] = _uuid(
            normalized.get("message_id"), "payload.message_id"
        )
    if message_type == "run.event":
        normalized["event_id"] = _uuid(normalized.get("event_id"), "payload.event_id")
    if message_type == "operation.approval_required":
        digest = str(normalized.get("operation_digest") or "")
        if not _DIGEST_RE.fullmatch(digest):
            raise LighthouseProtocolError("operation_digest must be a SHA-256 digest")
    if message_type == "receipt.committed":
        digest = str(normalized.get("receipt_digest") or "")
        if not _DIGEST_RE.fullmatch(digest):
            raise LighthouseProtocolError("receipt_digest must be a SHA-256 digest")
    return {
        "protocol": PROTOCOL,
        "message_id": message_id,
        "type": message_type,
        "sent_at": sent_at,
        "payload": normalized,
    }
