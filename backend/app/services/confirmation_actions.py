"""Durable Passkey-gated execution for AI-selected command capabilities."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.action_context import bounded_action_context
from app.services.passkey_grants import consume_step_up_grant
from app.services.runtime_output import public_data
from app.templates.industry_blueprints import BLUEPRINT_PERMISSION_KEYS
from app.terminal import legacy_catalog
from app.terminal.catalog import availability, entry_by_tool_name

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext
    from app.core.config import Settings


_SENSITIVE_PARTS = (
    "password",
    "secret",
    "token",
    "api_key",
    "credential",
    "passkey",
)
_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{20,128}$")
_DELIVERY_ID_RE = re.compile(r"^acd_[A-Za-z0-9_-]{20,80}$")
_TERMINAL_STATUSES = {"completed", "cancelled", "failed", "expired", "outcome_unknown"}


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


def _fernet(signing_secret: str) -> Fernet:
    key = hashlib.sha256(("warehouse-confirmation-v1:" + signing_secret).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def _encrypt_json(signing_secret: str, value: object) -> bytes:
    return _fernet(signing_secret).encrypt(_canonical(value).encode("utf-8"))


def _decrypt_json(signing_secret: str, ciphertext: object) -> object:
    try:
        raw = _fernet(signing_secret).decrypt(bytes(ciphertext)).decode("utf-8")
        return json.loads(raw)
    except (InvalidToken, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=409,
            detail="Confirmation action integrity verification failed",
        ) from exc


def _as_uuid(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        return None


def _safe_datetime(value: object) -> object:
    return value.isoformat() if isinstance(value, datetime) else value


def _sensitive_parameter(parameter: Mapping[str, object]) -> bool:
    name = f"{parameter.get('flag') or ''} {parameter.get('dest') or ''}".lower()
    return any(part in name for part in _SENSITIVE_PARTS)


def _normalized_args(
    entry: Mapping[str, object], arguments: Mapping[str, object]
) -> dict[str, object]:
    supplied = dict(arguments)
    # Validate caller/model field names and types through the same catalogue
    # parser used by direct terminal execution.
    legacy_catalog.values_from_tool_args(dict(entry), supplied)
    normalized = dict(supplied)
    for parameter in entry.get("params") or []:
        if not isinstance(parameter, dict):
            continue
        flag = str(parameter.get("flag") or "")
        if flag and flag not in normalized and parameter.get("default") is not None:
            normalized[flag] = parameter["default"]
    legacy_catalog.values_from_tool_args(dict(entry), normalized)
    return normalized


def _display_value(value: object) -> object:
    if isinstance(value, (dict, list)):
        return _canonical(value)
    return value


def _presentation(
    entry: Mapping[str, object], arguments: Mapping[str, object]
) -> tuple[dict[str, object], list[dict[str, object]]]:
    fields: list[dict[str, object]] = []
    editable: list[dict[str, object]] = []
    type_map = {
        "str": "text",
        "list": "text",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "flag": "boolean",
    }
    for parameter in entry.get("params") or []:
        if not isinstance(parameter, dict):
            continue
        flag = str(parameter.get("flag") or "").strip()
        if not flag or flag not in arguments:
            continue
        label = str(parameter.get("help") or flag).strip()[:180]
        sensitive = _sensitive_parameter(parameter)
        value = "[redacted]" if sensitive else _display_value(arguments[flag])
        fields.append({"key": flag, "label": label, "value": value})
        field_type = type_map.get(str(parameter.get("type") or "str"))
        choices = [str(choice) for choice in (parameter.get("choices") or [])]
        if choices and field_type == "text":
            field_type = "select"
        if sensitive or field_type is None:
            continue
        editable_field = {
            "key": flag,
            "label": label,
            "type": field_type,
            "value": (
                ",".join(str(item) for item in arguments[flag])
                if isinstance(arguments[flag], list)
                else arguments[flag]
            ),
            "required": bool(parameter.get("required")),
        }
        if choices:
            editable_field["choices"] = choices
        editable.append(editable_field)
    return (
        {
            "title": f"授權 AI 執行 · {entry['command']}",
            "summary": str(entry.get("description") or "")[:1200],
            "fields": fields,
        },
        editable,
    )


def _add_event(
    session: Session,
    actor: ActorContext,
    *,
    action_id: int,
    event_type: str,
    revision: int,
    payload: dict[str, object] | None = None,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO secretariat.confirmation_action_events(
              tenant_id, action_id, actor_user_id, event_type, revision, payload
            ) VALUES (
              :tenant_id, :action_id, :actor_user_id, :event_type, :revision,
              CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "action_id": action_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "revision": revision,
            "payload": _canonical(payload or {}),
        },
    )


def _audit(
    session: Session,
    actor: ActorContext,
    event_type: str,
    payload: dict[str, object],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": _canonical(payload),
        },
    )


def _expire_stale(session: Session, actor: ActorContext) -> None:
    session.execute(
        text(
            """
            UPDATE secretariat.execution_keychains
            SET status = 'expired'
            WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
              AND status = 'authorized' AND expires_at <= now()
            """
        ),
        {"tenant_id": actor.tenant_id, "user_id": actor.user_id},
    )
    session.execute(
        text(
            """
            UPDATE secretariat.confirmation_actions
            SET status = 'expired', revision = revision + 1
            WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
              AND (
                (status = 'pending' AND expires_at <= now())
                OR (
                  status = 'authorized' AND EXISTS (
                    SELECT 1 FROM secretariat.execution_keychains k
                    WHERE k.tenant_id = confirmation_actions.tenant_id
                      AND k.action_id = confirmation_actions.id
                      AND k.status = 'expired'
                  )
                )
              )
            """
        ),
        {"tenant_id": actor.tenant_id, "user_id": actor.user_id},
    )
    session.execute(
        text(
            """
            UPDATE secretariat.confirmation_actions
            SET status = 'outcome_unknown', revision = revision + 1,
                error = COALESCE(
                  error,
                  'Execution lease expired; verify business state before retrying'
                )
            WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
              AND status = 'executing'
              AND executing_at < now() - INTERVAL '30 minutes'
            """
        ),
        {"tenant_id": actor.tenant_id, "user_id": actor.user_id},
    )
    session.execute(
        text(
            """
            UPDATE secretariat.confirmation_credential_deliveries
            SET status = 'expired', ciphertext = NULL
            WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
              AND status = 'pending' AND expires_at <= now()
            """
        ),
        {"tenant_id": actor.tenant_id, "user_id": actor.user_id},
    )


def _load_action(
    session: Session,
    actor: ActorContext,
    action_id: object,
    *,
    for_update: bool = False,
) -> Mapping[str, object]:
    try:
        normalized_id = int(action_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Confirmation action not found") from exc
    _expire_stale(session, actor)
    suffix = " FOR UPDATE" if for_update else ""
    row = (
        session.execute(
            text(
                """
                SELECT * FROM secretariat.confirmation_actions
                WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
                  AND id = :id
                """
                + suffix
            ),
            {
                "tenant_id": actor.tenant_id,
                "user_id": actor.user_id,
                "id": normalized_id,
            },
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Confirmation action not found")
    return row


def _delivery_descriptor(row: Mapping[str, object]) -> dict[str, object]:
    action_id = int(row["action_id"])
    return {
        "delivery_id": str(row["delivery_id"]),
        "action_id": action_id,
        "conversation_id": (str(row["conversation_id"]) if row.get("conversation_id") else None),
        "status": str(row["status"]),
        "expires_at": _safe_datetime(row["expires_at"]),
        "credential_count": int(row["credential_count"]),
        "credentials": list(row["descriptors"] or []),
        "fetch_path": (f"/api/agent/confirmation-actions/{action_id}/credential-delivery/fetch"),
        "ack_path": (f"/api/agent/confirmation-actions/{action_id}/credential-delivery/ack"),
    }


def _public_action(session: Session, row: Mapping[str, object]) -> dict[str, object]:
    action_id = int(row["id"])
    status = str(row["status"])
    completion_receipt = None
    if status == "completed" and row.get("completed_at"):
        completion_receipt = {
            "receipt_no": f"ACT-{action_id:08d}",
            "action_id": action_id,
            "action_key": f"command:{action_id}",
            "status": "completed",
            "completed_at": _safe_datetime(row["completed_at"]),
            "execution_id": str(row["execution_id"]) if row.get("execution_id") else None,
        }
    presentation = dict(row["presentation"] or {})
    action_context = bounded_action_context(presentation.pop("_runtime_action_context", None))
    action: dict[str, object] = {
        "id": action_id,
        "action_id": action_id,
        "action_key": f"command:{action_id}",
        "kind": "command_confirmation",
        "status": status,
        "revision": int(row["revision"]),
        "command": str(row["command"]),
        "tool_name": str(row["tool_name"]),
        "source_run_id": str(row["run_id"]) if row.get("run_id") else None,
        "source_step_no": row.get("source_step_no"),
        "conversation_id": (str(row["conversation_id"]) if row.get("conversation_id") else None),
        "risk": str(row["risk"]),
        "passkey_required": True,
        "presentation": presentation,
        "editable_fields": list(row["editable_fields"] or []),
        "result": public_data(row.get("result"), locale="zh-Hant"),
        "error": ("操作未完成；原始診斷已保留於受保護的審計記錄。" if row.get("error") else None),
        "verification": (
            dict(row["verification"]) if isinstance(row.get("verification"), dict) else None
        ),
        "expires_at": _safe_datetime(row["expires_at"]),
        "authorized_at": _safe_datetime(row.get("authorized_at")),
        "executing_at": _safe_datetime(row.get("executing_at")),
        "completed_at": _safe_datetime(row.get("completed_at")),
        "cancelled_at": _safe_datetime(row.get("cancelled_at")),
        "failed_at": _safe_datetime(row.get("failed_at")),
        "created_at": _safe_datetime(row["created_at"]),
        "updated_at": _safe_datetime(row["updated_at"]),
    }
    if action_context is not None:
        action["action_context"] = action_context
    action["timestamps"] = {
        key: action[key]
        for key in (
            "created_at",
            "updated_at",
            "expires_at",
            "authorized_at",
            "executing_at",
            "completed_at",
            "cancelled_at",
            "failed_at",
        )
    }
    action["outcome"] = {
        "status": status,
        "operation_completed": status == "completed",
        "completion_receipt": completion_receipt,
    }
    if completion_receipt:
        action["receipt_no"] = completion_receipt["receipt_no"]
        action["completion_receipt"] = completion_receipt
    keychain = (
        session.execute(
            text(
                """
                SELECT id, action_id, action_revision, status, scope, expires_at,
                       claimed_at, consumed_at, created_at
                FROM secretariat.execution_keychains
                WHERE tenant_id = :tenant_id AND action_id = :action_id
                LIMIT 1
                """
            ),
            {"tenant_id": row["tenant_id"], "action_id": action_id},
        )
        .mappings()
        .one_or_none()
    )
    if keychain is not None:
        keychain_descriptor = {
            "keychain_id": str(keychain["id"]),
            "action_id": action_id,
            "action_revision": int(keychain["action_revision"]),
            "status": str(keychain["status"]),
            "scope": dict(keychain["scope"] or {}),
            "expires_at": _safe_datetime(keychain["expires_at"]),
            "claimed_at": _safe_datetime(keychain.get("claimed_at")),
            "consumed_at": _safe_datetime(keychain.get("consumed_at")),
            "created_at": _safe_datetime(keychain["created_at"]),
            "bearer_secret_exposed": False,
            "single_use": True,
        }
        action["authorization_keychain"] = keychain_descriptor
        if status == "authorized" and str(keychain["status"]) == "authorized":
            action["continuation"] = {
                "type": "authorization_granted",
                "confirmation_action_id": action_id,
                "authorization_keychain_id": str(keychain["id"]),
                "conversation_id": action["conversation_id"],
                "prompt": "請使用已授權的 Keychain 繼續完成原操作。",
                "display_text": "AI 正在接手已授權操作",
                "expires_at": _safe_datetime(keychain["expires_at"]),
            }
            action["outcome"] = {
                "status": "authorized",
                "operation_completed": False,
                "runtime_resume_required": True,
            }
    deliveries = (
        session.execute(
            text(
                """
                SELECT delivery_id, action_id, conversation_id, status, expires_at,
                       credential_count, descriptors
                FROM secretariat.confirmation_credential_deliveries
                WHERE action_id = :action_id AND status = 'pending'
                  AND expires_at > now()
                ORDER BY created_at
                """
            ),
            {"action_id": action_id},
        )
        .mappings()
        .all()
    )
    if deliveries:
        action["credential_deliveries"] = [
            _delivery_descriptor(delivery) for delivery in deliveries
        ]
    return action


def propose_confirmation_action(
    actor: ActorContext,
    *,
    tool_name: str,
    arguments: Mapping[str, object],
    settings: Settings,
    conversation_id: object = None,
    run_id: object = None,
    source_step_no: int | None = None,
    action_context: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Persist one model-selected proposal without executing its mutation."""

    entry = entry_by_tool_name(tool_name)
    if entry is None:
        raise HTTPException(status_code=404, detail="Capability is no longer registered")
    if availability(entry) != "active":
        raise HTTPException(status_code=409, detail="Capability adapter is unavailable")
    policy = legacy_catalog.confirmation_contract(entry)
    if policy["mode"] == "direct":
        raise HTTPException(status_code=409, detail="Capability does not require confirmation")
    try:
        normalized = _normalized_args(entry, arguments)
    except (legacy_catalog.CommandError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    presentation, editable = _presentation(entry, normalized)
    retained_action_context = bounded_action_context(action_context)
    if retained_action_context is not None:
        presentation["_runtime_action_context"] = retained_action_context
    arguments_digest = _digest({"tool_name": tool_name, "arguments": normalized})
    request_digest = _digest(
        {
            "tool_name": tool_name,
            "arguments_digest": arguments_digest,
            "run_id": str(run_id or ""),
            "source_step_no": source_step_no,
            "action_context": retained_action_context,
        }
    )
    conversation_uuid = _as_uuid(conversation_id)
    run_uuid = _as_uuid(run_id)
    expires_at = datetime.now(UTC) + timedelta(minutes=20)
    with tenant_session(actor.tenant_id) as session:
        _expire_stale(session, actor)
        existing = None
        if run_uuid is not None:
            existing = (
                session.execute(
                    text(
                        """
                        SELECT * FROM secretariat.confirmation_actions
                        WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
                          AND run_id = :run_id AND request_digest = :request_digest
                        LIMIT 1
                        """
                    ),
                    {
                        "tenant_id": actor.tenant_id,
                        "user_id": actor.user_id,
                        "run_id": run_uuid,
                        "request_digest": request_digest,
                    },
                )
                .mappings()
                .one_or_none()
            )
        if existing is not None:
            return _public_action(session, existing)
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO secretariat.confirmation_actions(
                      tenant_id, requester_user_id, conversation_id, run_id,
                      source_step_no, tool_name, command, risk,
                      confirmation_mode, confirmation_adapter,
                      arguments_ciphertext, arguments_digest, request_digest,
                      presentation, editable_fields, expires_at
                    ) VALUES (
                      :tenant_id, :requester_user_id, :conversation_id, :run_id,
                      :source_step_no, :tool_name, :command, :risk,
                      :confirmation_mode, :confirmation_adapter,
                      :arguments_ciphertext, :arguments_digest, :request_digest,
                      CAST(:presentation AS jsonb), CAST(:editable_fields AS jsonb),
                      :expires_at
                    ) RETURNING *
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "requester_user_id": actor.user_id,
                    "conversation_id": conversation_uuid,
                    "run_id": run_uuid,
                    "source_step_no": source_step_no,
                    "tool_name": tool_name,
                    "command": entry["command"],
                    "risk": entry["risk"],
                    "confirmation_mode": policy["mode"],
                    "confirmation_adapter": policy["adapter"],
                    "arguments_ciphertext": _encrypt_json(settings.integration_secret, normalized),
                    "arguments_digest": arguments_digest,
                    "request_digest": request_digest,
                    "presentation": _canonical(presentation),
                    "editable_fields": _canonical(editable),
                    "expires_at": expires_at,
                },
            )
            .mappings()
            .one()
        )
        action_id = int(row["id"])
        _add_event(
            session,
            actor,
            action_id=action_id,
            event_type="proposed",
            revision=1,
            payload={"tool_name": tool_name, "command": entry["command"]},
        )
        _audit(
            session,
            actor,
            "ai.confirmation.proposed",
            {
                "action_id": action_id,
                "tool_name": tool_name,
                "command": entry["command"],
                "request_digest": request_digest,
                "status": "pending",
            },
        )
        return _public_action(session, row)


def list_confirmation_actions(
    actor: ActorContext,
    *,
    conversation_id: object = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    bounded_limit = max(1, min(int(limit), 200))
    conversation_uuid = _as_uuid(conversation_id)
    with tenant_session(actor.tenant_id) as session:
        _expire_stale(session, actor)
        rows = (
            session.execute(
                text(
                    """
                    SELECT * FROM secretariat.confirmation_actions
                    WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
                      AND (
                        CAST(:conversation_id AS uuid) IS NULL
                        OR conversation_id = CAST(:conversation_id AS uuid)
                      )
                    ORDER BY id DESC
                    LIMIT :limit
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": actor.user_id,
                    "conversation_id": conversation_uuid,
                    "limit": bounded_limit,
                },
            )
            .mappings()
            .all()
        )
        return [_public_action(session, row) for row in reversed(rows)]


def get_confirmation_action(actor: ActorContext, action_id: object) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id)
        return {"ok": True, "action": _public_action(session, row)}


def cancel_confirmation_action(
    actor: ActorContext,
    action_id: object,
    *,
    expected_revision: object,
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id, for_update=True)
        if str(row["status"]) == "cancelled":
            return {"ok": True, "action": _public_action(session, row), "idempotent_replay": True}
        if str(row["status"]) != "pending":
            raise HTTPException(status_code=409, detail="Confirmation action is no longer pending")
        try:
            revision = int(expected_revision)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="expected_revision is required") from exc
        if revision != int(row["revision"]):
            raise HTTPException(status_code=409, detail="Confirmation action revision changed")
        next_revision = revision + 1
        fresh = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.confirmation_actions
                    SET status = 'cancelled', revision = :next_revision,
                        cancelled_at = now()
                    WHERE id = :id AND status = 'pending' AND revision = :revision
                    RETURNING *
                    """
                ),
                {"id": int(row["id"]), "revision": revision, "next_revision": next_revision},
            )
            .mappings()
            .one_or_none()
        )
        if fresh is None:
            raise HTTPException(status_code=409, detail="Confirmation action changed concurrently")
        _add_event(
            session,
            actor,
            action_id=int(row["id"]),
            event_type="cancelled",
            revision=next_revision,
        )
        _audit(
            session,
            actor,
            "ai.confirmation.cancelled",
            {"action_id": int(row["id"]), "tool_name": row["tool_name"]},
        )
        return {"ok": True, "action": _public_action(session, fresh)}


def edit_confirmation_action(
    actor: ActorContext,
    action_id: object,
    *,
    expected_revision: object,
    values: object,
    settings: Settings,
) -> dict[str, object]:
    if not isinstance(values, dict) or not values:
        raise HTTPException(status_code=422, detail="Editable values are required")
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id, for_update=True)
        if str(row["status"]) != "pending":
            raise HTTPException(status_code=409, detail="Confirmation action is no longer pending")
        try:
            revision = int(expected_revision)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="expected_revision is required") from exc
        if revision != int(row["revision"]):
            raise HTTPException(status_code=409, detail="Confirmation action revision changed")
        allowed = {
            str(field.get("key"))
            for field in (row["editable_fields"] or [])
            if isinstance(field, dict) and field.get("key")
        }
        if not set(values).issubset(allowed):
            raise HTTPException(status_code=422, detail="One or more fields are not editable")
        arguments = _decrypt_json(settings.integration_secret, row["arguments_ciphertext"])
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=409, detail="Stored arguments are invalid")
        for key, value in values.items():
            if value is None:
                arguments.pop(str(key), None)
            else:
                arguments[str(key)] = value
        entry = entry_by_tool_name(str(row["tool_name"]))
        if entry is None:
            raise HTTPException(status_code=409, detail="Capability is no longer registered")
        try:
            normalized = _normalized_args(entry, arguments)
        except (legacy_catalog.CommandError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        presentation, editable = _presentation(entry, normalized)
        arguments_digest = _digest({"tool_name": row["tool_name"], "arguments": normalized})
        request_digest = _digest(
            {
                "tool_name": row["tool_name"],
                "arguments_digest": arguments_digest,
                "run_id": str(row.get("run_id") or ""),
                "source_step_no": row.get("source_step_no"),
            }
        )
        next_revision = revision + 1
        fresh = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.confirmation_actions
                    SET revision = :next_revision,
                        arguments_ciphertext = :arguments_ciphertext,
                        arguments_digest = :arguments_digest,
                        request_digest = :request_digest,
                        presentation = CAST(:presentation AS jsonb),
                        editable_fields = CAST(:editable_fields AS jsonb)
                    WHERE id = :id AND status = 'pending' AND revision = :revision
                    RETURNING *
                    """
                ),
                {
                    "id": int(row["id"]),
                    "revision": revision,
                    "next_revision": next_revision,
                    "arguments_ciphertext": _encrypt_json(settings.integration_secret, normalized),
                    "arguments_digest": arguments_digest,
                    "request_digest": request_digest,
                    "presentation": _canonical(presentation),
                    "editable_fields": _canonical(editable),
                },
            )
            .mappings()
            .one_or_none()
        )
        if fresh is None:
            raise HTTPException(status_code=409, detail="Confirmation action changed concurrently")
        _add_event(
            session,
            actor,
            action_id=int(row["id"]),
            event_type="edited",
            revision=next_revision,
            payload={"fields": sorted(values)},
        )
        return {"ok": True, "action": _public_action(session, fresh)}


def _safe_execution_result(
    result: Mapping[str, object], credentials: list[dict[str, object]]
) -> dict[str, object]:
    data = result.get("data")
    safe = dict(data) if isinstance(data, Mapping) else {"data": data}
    safe["command_status"] = result.get("status")
    safe["execution_id"] = result.get("execution_id")
    for credential in credentials:
        field = str(credential.get("field") or "api_key")
        safe[field] = "已簽發；明文已移至一次性安全卡"
        if credential.get("key_hint"):
            safe[f"{field}_hint"] = credential["key_hint"]
    return safe


def _create_credential_delivery(
    session: Session,
    actor: ActorContext,
    *,
    action: Mapping[str, object],
    credentials: list[dict[str, object]],
    client_id: str | None = None,
    client_id_hash: str | None = None,
    settings: Settings,
) -> dict[str, object] | None:
    if not credentials:
        return None
    import secrets

    delivery_id = "acd_" + secrets.token_urlsafe(24)
    descriptors = [
        {key: value for key, value in credential.items() if key != "value"}
        for credential in credentials
    ]
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    bound_client_hash = str(client_id_hash or "").strip()
    if not bound_client_hash:
        if not client_id:
            raise HTTPException(
                status_code=409,
                detail="Credential delivery is missing its browser binding",
            )
        bound_client_hash = hashlib.sha256(client_id.encode("utf-8")).hexdigest()
    row = (
        session.execute(
            text(
                """
                INSERT INTO secretariat.confirmation_credential_deliveries(
                  delivery_id, tenant_id, action_id, requester_user_id,
                  conversation_id, client_id_hash, ciphertext,
                  credential_count, descriptors, expires_at
                ) VALUES (
                  :delivery_id, :tenant_id, :action_id, :requester_user_id,
                  :conversation_id, :client_id_hash, :ciphertext,
                  :credential_count, CAST(:descriptors AS jsonb), :expires_at
                ) RETURNING delivery_id, action_id, conversation_id, status,
                            expires_at, credential_count, descriptors
                """
            ),
            {
                "delivery_id": delivery_id,
                "tenant_id": actor.tenant_id,
                "action_id": int(action["id"]),
                "requester_user_id": actor.user_id,
                "conversation_id": action.get("conversation_id"),
                "client_id_hash": bound_client_hash,
                "ciphertext": _encrypt_json(settings.integration_secret, credentials),
                "credential_count": len(credentials),
                "descriptors": _canonical(descriptors),
                "expires_at": expires_at,
            },
        )
        .mappings()
        .one()
    )
    return _delivery_descriptor(row)


def confirm_confirmation_action(
    actor: ActorContext,
    action_id: object,
    *,
    expected_revision: object,
    step_up_token: object,
    credential_client_id: object,
    settings: Settings,
) -> dict[str, object]:
    try:
        revision = int(expected_revision)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="expected_revision is required") from exc
    client_id = str(credential_client_id or "").strip()
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id, for_update=True)
        if str(row["status"]) != "pending":
            raise HTTPException(status_code=409, detail="Confirmation action is no longer pending")
        if revision != int(row["revision"]):
            raise HTTPException(status_code=409, detail="Confirmation action revision changed")
        entry = entry_by_tool_name(str(row["tool_name"]))
        if entry is None or availability(entry) != "active":
            raise HTTPException(status_code=409, detail="Capability adapter is unavailable")
        policy = legacy_catalog.confirmation_contract(entry)
        if policy["mode"] != str(row["confirmation_mode"]):
            raise HTTPException(status_code=409, detail="Confirmation policy changed")
        if entry.get("secret_result_fields") and not _CLIENT_ID_RE.fullmatch(client_id):
            raise HTTPException(
                status_code=422,
                detail="A valid credential_client_id is required for one-time delivery",
            )
        arguments = _decrypt_json(settings.integration_secret, row["arguments_ciphertext"])
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=409, detail="Stored arguments are invalid")
        if _digest({"tool_name": row["tool_name"], "arguments": arguments}) != str(
            row["arguments_digest"]
        ):
            raise HTTPException(status_code=409, detail="Confirmation action integrity mismatch")
        try:
            _normalized_args(entry, arguments)
        except (legacy_catalog.CommandError, ValueError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Stored arguments no longer validate",
            ) from exc
        verification = consume_step_up_grant(
            session,
            actor,
            token=step_up_token,
            purpose="ai.confirmation.execute",
            resource={"action_id": int(row["id"]), "revision": revision},
        )
        authorized_revision = revision + 1
        authorized = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.confirmation_actions
                    SET status = 'authorized', revision = :next_revision,
                        authorized_at = now(), verification = CAST(:verification AS jsonb)
                    WHERE id = :id AND status = 'pending' AND revision = :revision
                    RETURNING *
                    """
                ),
                {
                    "id": int(row["id"]),
                    "revision": revision,
                    "next_revision": authorized_revision,
                    "verification": _canonical(verification),
                },
            )
            .mappings()
            .one_or_none()
        )
        if authorized is None:
            raise HTTPException(status_code=409, detail="Confirmation action changed concurrently")
        keychain_id = uuid4()
        # The visible action expiry is the consent window the user reviewed.
        # Keep the server-side hand-off aligned with it so a model/provider
        # retry does not silently lose an otherwise still-valid approval.
        keychain_expiry = row["expires_at"]
        session.execute(
            text(
                """
                INSERT INTO secretariat.execution_keychains(
                  id, tenant_id, action_id, requester_user_id,
                  conversation_id, run_id, action_revision, request_digest,
                  scope, credential_client_id_hash, expires_at
                ) VALUES (
                  :id, :tenant_id, :action_id, :requester_user_id,
                  :conversation_id, :run_id, :action_revision, :request_digest,
                  CAST(:scope AS jsonb), :credential_client_id_hash, :expires_at
                )
                """
            ),
            {
                "id": keychain_id,
                "tenant_id": actor.tenant_id,
                "action_id": int(row["id"]),
                "requester_user_id": actor.user_id,
                "conversation_id": row.get("conversation_id"),
                "run_id": row.get("run_id"),
                "action_revision": authorized_revision,
                "request_digest": row["request_digest"],
                "scope": _canonical(
                    {
                        "action_id": int(row["id"]),
                        "tool_name": str(row["tool_name"]),
                        "arguments_digest": str(row["arguments_digest"]),
                        "request_digest": str(row["request_digest"]),
                        "execution_identity": "company_ai",
                        "uses": 1,
                    }
                ),
                "credential_client_id_hash": (
                    hashlib.sha256(client_id.encode("utf-8")).hexdigest() if client_id else None
                ),
                "expires_at": keychain_expiry,
            },
        )
        _add_event(
            session,
            actor,
            action_id=int(row["id"]),
            event_type="passkey_verified",
            revision=authorized_revision,
            payload={
                "grant_id": verification.get("grant_id"),
                "resource_digest": verification.get("resource_digest"),
                "authorization_keychain_id": str(keychain_id),
            },
        )
        _audit(
            session,
            actor,
            "ai.confirmation.authorized",
            {
                "action_id": int(row["id"]),
                "tool_name": row["tool_name"],
                "authorization_keychain_id": str(keychain_id),
                "business_operation_executed": False,
            },
        )
        return {
            "ok": True,
            "signal": "authorization_granted",
            "business_operation_executed": False,
            "action": _public_action(session, authorized),
        }


def execute_authorized_confirmation_action(
    actor: ActorContext,
    action_id: object,
    *,
    authorization_keychain_id: object,
    conversation_id: object = None,
    settings: Settings,
) -> dict[str, object]:
    """Let Auto Runtime consume one exact Passkey authorization once."""

    keychain_uuid = _as_uuid(authorization_keychain_id)
    if keychain_uuid is None:
        raise HTTPException(status_code=422, detail="authorization_keychain_id is required")
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id, for_update=True)
        requested_conversation = _as_uuid(conversation_id)
        if (
            requested_conversation is None
            or row.get("conversation_id") is None
            or requested_conversation != row.get("conversation_id")
        ):
            raise HTTPException(
                status_code=409,
                detail="Authorization Keychain belongs to a different conversation",
            )
        status = str(row["status"])
        if status in _TERMINAL_STATUSES:
            return {
                "ok": status == "completed",
                "idempotent_replay": True,
                "action": _public_action(session, row),
            }
        if status != "authorized":
            raise HTTPException(status_code=409, detail="Confirmation action is not authorized")
        keychain = (
            session.execute(
                text(
                    """
                    SELECT * FROM secretariat.execution_keychains
                    WHERE tenant_id = :tenant_id
                      AND requester_user_id = :requester_user_id
                      AND action_id = :action_id AND id = :id
                    FOR UPDATE
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "requester_user_id": actor.user_id,
                    "action_id": int(row["id"]),
                    "id": keychain_uuid,
                },
            )
            .mappings()
            .one_or_none()
        )
        if keychain is None:
            raise HTTPException(status_code=404, detail="Authorization Keychain not found")
        if str(keychain["status"]) != "authorized":
            raise HTTPException(
                status_code=409,
                detail="Authorization Keychain is no longer usable",
            )
        if keychain["expires_at"] <= datetime.now(UTC):
            session.execute(
                text(
                    "UPDATE secretariat.execution_keychains SET status = 'expired' WHERE id = :id"
                ),
                {"id": keychain_uuid},
            )
            raise HTTPException(status_code=410, detail="Authorization Keychain expired")
        scope = dict(keychain["scope"] or {})
        if (
            int(scope.get("action_id") or 0) != int(row["id"])
            or str(scope.get("tool_name") or "") != str(row["tool_name"])
            or str(scope.get("arguments_digest") or "") != str(row["arguments_digest"])
            or str(keychain["request_digest"]) != str(row["request_digest"])
        ):
            raise HTTPException(status_code=409, detail="Authorization Keychain scope mismatch")
        entry = entry_by_tool_name(str(row["tool_name"]))
        if entry is None or availability(entry) != "active":
            raise HTTPException(status_code=409, detail="Capability adapter is unavailable")
        arguments = _decrypt_json(settings.integration_secret, row["arguments_ciphertext"])
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=409, detail="Stored arguments are invalid")
        if _digest({"tool_name": row["tool_name"], "arguments": arguments}) != str(
            row["arguments_digest"]
        ):
            raise HTTPException(status_code=409, detail="Confirmation action integrity mismatch")
        _normalized_args(entry, arguments)
        executing_revision = int(row["revision"]) + 1
        executing = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.confirmation_actions
                    SET status = 'executing', revision = :revision, executing_at = now()
                    WHERE id = :id AND status = 'authorized'
                    RETURNING *
                    """
                ),
                {"id": int(row["id"]), "revision": executing_revision},
            )
            .mappings()
            .one_or_none()
        )
        if executing is None:
            raise HTTPException(status_code=409, detail="Confirmation action changed concurrently")
        session.execute(
            text(
                """
                UPDATE secretariat.execution_keychains
                SET status = 'claimed', claimed_at = now()
                WHERE id = :id AND status = 'authorized'
                """
            ),
            {"id": keychain_uuid},
        )
        _add_event(
            session,
            actor,
            action_id=int(row["id"]),
            event_type="runtime_claimed",
            revision=executing_revision,
            payload={"authorization_keychain_id": str(keychain_uuid)},
        )
        client_id_hash = keychain.get("credential_client_id_hash")

    from app.terminal.executor import execute_confirmed_runtime_tool_call

    company_ai = replace(
        actor,
        role_level=max(10, actor.role_level),
        permissions=frozenset(BLUEPRINT_PERMISSION_KEYS),
    )
    try:
        result = execute_confirmed_runtime_tool_call(company_ai, str(row["tool_name"]), arguments)
    except Exception as exc:  # execution may have crossed the adapter boundary
        with tenant_session(actor.tenant_id) as session:
            current = _load_action(session, actor, action_id, for_update=True)
            if str(current["status"]) == "executing":
                fresh = (
                    session.execute(
                        text(
                            """
                            UPDATE secretariat.confirmation_actions
                            SET status = 'outcome_unknown', revision = revision + 1,
                                error = :error, failed_at = now()
                            WHERE id = :id RETURNING *
                            """
                        ),
                        {
                            "id": int(current["id"]),
                            "error": (
                                f"Execution outcome requires verification ({type(exc).__name__})"
                            ),
                        },
                    )
                    .mappings()
                    .one()
                )
                session.execute(
                    text(
                        """
                        UPDATE secretariat.execution_keychains
                        SET status = 'outcome_unknown', consumed_at = now()
                        WHERE id = :id AND status = 'claimed'
                        """
                    ),
                    {"id": keychain_uuid},
                )
                return {"ok": False, "action": _public_action(session, fresh)}
        raise

    credentials = [
        dict(item)
        for item in (result.pop("credentials", []) if isinstance(result, dict) else [])
        if isinstance(item, dict) and item.get("value")
    ]
    succeeded = bool(isinstance(result, dict) and result.get("ok") is True)
    final_status = "completed" if succeeded else "failed"
    safe_result = (
        _safe_execution_result(result, credentials) if isinstance(result, dict) else {"data": None}
    )
    with tenant_session(actor.tenant_id) as session:
        current = _load_action(session, actor, action_id, for_update=True)
        if str(current["status"]) != "executing":
            raise HTTPException(status_code=409, detail="Confirmation action is not executing")
        completed_revision = int(current["revision"]) + 1
        fresh = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.confirmation_actions
                    SET status = :status, revision = :revision,
                        result = CAST(:result AS jsonb), error = :error,
                        execution_id = :execution_id,
                        completed_at = CASE WHEN :status = 'completed' THEN now() ELSE NULL END,
                        failed_at = CASE WHEN :status = 'failed' THEN now() ELSE NULL END
                    WHERE id = :id AND status = 'executing'
                    RETURNING *
                    """
                ),
                {
                    "id": int(current["id"]),
                    "status": final_status,
                    "revision": completed_revision,
                    "result": _canonical(safe_result),
                    "error": (
                        None
                        if succeeded
                        else str(result.get("error") or "Command execution failed")
                    ),
                    "execution_id": _as_uuid(result.get("execution_id")),
                },
            )
            .mappings()
            .one()
        )
        delivery = _create_credential_delivery(
            session,
            actor,
            action=fresh,
            credentials=credentials,
            client_id_hash=str(client_id_hash or "") or None,
            settings=settings,
        )
        session.execute(
            text(
                """
                UPDATE secretariat.execution_keychains
                SET status = 'consumed', consumed_at = now()
                WHERE id = :id AND status = 'claimed'
                """
            ),
            {"id": keychain_uuid},
        )
        _add_event(
            session,
            actor,
            action_id=int(current["id"]),
            event_type=final_status,
            revision=completed_revision,
            payload={
                "execution_id": result.get("execution_id"),
                "credential_delivery_id": delivery.get("delivery_id") if delivery else None,
                "authorization_keychain_id": str(keychain_uuid),
            },
        )
        _audit(
            session,
            actor,
            f"ai.confirmation.{final_status}",
            {
                "action_id": int(current["id"]),
                "tool_name": current["tool_name"],
                "execution_id": result.get("execution_id"),
                "credential_delivery_id": delivery.get("delivery_id") if delivery else None,
                "authorization_keychain_id": str(keychain_uuid),
            },
        )
        return {
            "ok": succeeded,
            "signal": "runtime_execution_completed",
            "action": _public_action(session, fresh),
        }


def authorization_signal_for_runtime(
    actor: ActorContext,
    action_id: object,
    *,
    authorization_keychain_id: object,
    conversation_id: object = None,
    settings: Settings,
) -> dict[str, object]:
    """Validate an authorization Keychain without claiming or executing it.

    The confirmation card is an identity/consent boundary only.  This read-only
    hand-off gives Auto Runtime enough bounded context to make a fresh decision;
    the exact encrypted arguments remain server-side until the Runtime explicitly
    elects to consume this authorization.
    """

    keychain_uuid = _as_uuid(authorization_keychain_id)
    if keychain_uuid is None:
        raise HTTPException(status_code=422, detail="authorization_keychain_id is required")
    requested_conversation = _as_uuid(conversation_id)
    with tenant_session(actor.tenant_id) as session:
        row = _load_action(session, actor, action_id)
        if (
            requested_conversation is None
            or row.get("conversation_id") is None
            or requested_conversation != row.get("conversation_id")
        ):
            raise HTTPException(
                status_code=409,
                detail="Authorization Keychain belongs to a different conversation",
            )
        keychain = (
            session.execute(
                text(
                    """
                    SELECT * FROM secretariat.execution_keychains
                    WHERE tenant_id = :tenant_id
                      AND requester_user_id = :requester_user_id
                      AND action_id = :action_id AND id = :id
                    LIMIT 1
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "requester_user_id": actor.user_id,
                    "action_id": int(row["id"]),
                    "id": keychain_uuid,
                },
            )
            .mappings()
            .one_or_none()
        )
        if keychain is None:
            raise HTTPException(status_code=404, detail="Authorization Keychain not found")

        status = str(row["status"])
        keychain_status = str(keychain["status"])
        if status in _TERMINAL_STATUSES:
            return {
                "signal": "authorization_already_resolved",
                "business_operation_executed": status == "completed",
                "executable": False,
                "goal": str(row["command"]),
                "action_id": int(row["id"]),
                "authorization_keychain_id": str(keychain_uuid),
                "action": _public_action(session, row),
            }
        if status != "authorized" or keychain_status != "authorized":
            raise HTTPException(
                status_code=409,
                detail="Authorization Keychain is no longer usable",
            )
        if keychain["expires_at"] <= datetime.now(UTC):
            raise HTTPException(status_code=410, detail="Authorization Keychain expired")

        scope = dict(keychain["scope"] or {})
        if (
            int(scope.get("action_id") or 0) != int(row["id"])
            or str(scope.get("tool_name") or "") != str(row["tool_name"])
            or str(scope.get("arguments_digest") or "") != str(row["arguments_digest"])
            or str(keychain["request_digest"]) != str(row["request_digest"])
        ):
            raise HTTPException(status_code=409, detail="Authorization Keychain scope mismatch")
        entry = entry_by_tool_name(str(row["tool_name"]))
        if entry is None or availability(entry) != "active":
            raise HTTPException(status_code=409, detail="Capability adapter is unavailable")
        arguments = _decrypt_json(settings.integration_secret, row["arguments_ciphertext"])
        if not isinstance(arguments, dict):
            raise HTTPException(status_code=409, detail="Stored arguments are invalid")
        if _digest({"tool_name": row["tool_name"], "arguments": arguments}) != str(
            row["arguments_digest"]
        ):
            raise HTTPException(status_code=409, detail="Confirmation action integrity mismatch")
        try:
            _normalized_args(entry, arguments)
        except (legacy_catalog.CommandError, ValueError) as exc:
            raise HTTPException(
                status_code=409,
                detail="Stored arguments no longer validate",
            ) from exc
        original_goal = None
        if row.get("run_id"):
            original_goal = session.execute(
                text(
                    """
                    SELECT task FROM secretariat.runs
                    WHERE tenant_id = :tenant_id AND id = :run_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": actor.tenant_id, "run_id": row["run_id"]},
            ).scalar_one_or_none()
        action = _public_action(session, row)
        return {
            "signal": "authorization_granted",
            "business_operation_executed": False,
            "executable": True,
            "goal": str(original_goal or row["command"]),
            "action_id": int(row["id"]),
            "authorization_keychain_id": str(keychain_uuid),
            "tool_name": str(row["tool_name"]),
            "command": str(row["command"]),
            "arguments_digest": str(row["arguments_digest"]),
            "expires_at": _safe_datetime(keychain["expires_at"]),
            "scope": {
                "execution_identity": str(scope.get("execution_identity") or "company_ai"),
                "uses": int(scope.get("uses") or 1),
            },
            "action_context": action.get("action_context"),
            "action": action,
        }


def fetch_confirmation_credentials(
    actor: ActorContext,
    action_id: object,
    *,
    delivery_id: object,
    credential_client_id: object,
    settings: Settings,
) -> dict[str, object]:
    normalized_delivery = str(delivery_id or "").strip()
    client_id = str(credential_client_id or "").strip()
    if not _DELIVERY_ID_RE.fullmatch(normalized_delivery) or not _CLIENT_ID_RE.fullmatch(client_id):
        raise HTTPException(status_code=404, detail="Credential delivery not found")
    with tenant_session(actor.tenant_id) as session:
        action = _load_action(session, actor, action_id)
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM secretariat.confirmation_credential_deliveries
                    WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
                      AND action_id = :action_id AND delivery_id = :delivery_id
                    FOR UPDATE
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": actor.user_id,
                    "action_id": int(action["id"]),
                    "delivery_id": normalized_delivery,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None or str(row["status"]) != "pending" or row["expires_at"] <= datetime.now(UTC):
            raise HTTPException(status_code=410, detail="Credential delivery is unavailable")
        if str(row["client_id_hash"]) != hashlib.sha256(client_id.encode("utf-8")).hexdigest():
            raise HTTPException(
                status_code=403,
                detail="Credential delivery belongs to another browser tab",
            )
        credentials = _decrypt_json(settings.integration_secret, row["ciphertext"])
        if not isinstance(credentials, list) or not credentials:
            raise HTTPException(
                status_code=410,
                detail="Credential plaintext was already destroyed",
            )
        session.execute(
            text(
                """
                UPDATE secretariat.confirmation_credential_deliveries
                SET fetched_at = now()
                WHERE delivery_id = :delivery_id
                """
            ),
            {"delivery_id": normalized_delivery},
        )
        descriptor = _delivery_descriptor(row)
        bound_credentials = [
            {
                **dict(item),
                "action_key": f"command:{int(action['id'])}",
                "escrow_delivery_id": normalized_delivery,
            }
            for item in credentials
            if isinstance(item, dict) and item.get("value")
        ]
        return {
            "ok": True,
            "action_key": f"command:{int(action['id'])}",
            "credentials": bound_credentials,
            "credential_delivery": descriptor,
            "requires_ack": True,
        }


def acknowledge_confirmation_credentials(
    actor: ActorContext,
    action_id: object,
    *,
    delivery_id: object,
    credential_client_id: object,
) -> dict[str, object]:
    normalized_delivery = str(delivery_id or "").strip()
    client_id = str(credential_client_id or "").strip()
    if not _DELIVERY_ID_RE.fullmatch(normalized_delivery) or not _CLIENT_ID_RE.fullmatch(client_id):
        raise HTTPException(status_code=404, detail="Credential delivery not found")
    with tenant_session(actor.tenant_id) as session:
        action = _load_action(session, actor, action_id)
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM secretariat.confirmation_credential_deliveries
                    WHERE tenant_id = :tenant_id AND requester_user_id = :user_id
                      AND action_id = :action_id AND delivery_id = :delivery_id
                    FOR UPDATE
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": actor.user_id,
                    "action_id": int(action["id"]),
                    "delivery_id": normalized_delivery,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Credential delivery not found")
        if str(row["client_id_hash"]) != hashlib.sha256(client_id.encode("utf-8")).hexdigest():
            raise HTTPException(
                status_code=403,
                detail="Credential delivery belongs to another browser tab",
            )
        if str(row["status"]) == "acked":
            return {
                "ok": True,
                "delivery_id": normalized_delivery,
                "status": "acked",
                "plaintext_destroyed": row["ciphertext"] is None,
                "idempotent_replay": True,
            }
        if str(row["status"]) != "pending":
            raise HTTPException(status_code=410, detail="Credential delivery is unavailable")
        session.execute(
            text(
                """
                UPDATE secretariat.confirmation_credential_deliveries
                SET status = 'acked', ciphertext = NULL, acked_at = now()
                WHERE delivery_id = :delivery_id AND status = 'pending'
                """
            ),
            {"delivery_id": normalized_delivery},
        )
        _audit(
            session,
            actor,
            "ai.confirmation.credential_destroyed",
            {"action_id": int(action["id"]), "delivery_id": normalized_delivery},
        )
        return {
            "ok": True,
            "delivery_id": normalized_delivery,
            "status": "acked",
            "plaintext_destroyed": True,
        }
