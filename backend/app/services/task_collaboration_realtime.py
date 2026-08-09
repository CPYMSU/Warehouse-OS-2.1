"""Bounded PostgreSQL-backed event streaming and disposable workspace presence."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections.abc import Iterator
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.task_collaboration import _require_member, _space, _task, _uuid

_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")
_STREAM_SECONDS = 50.0
_HEARTBEAT_SECONDS = 15.0
_POLL_SECONDS = 1.0
_MAX_REPLAY = 1_000
_BATCH_SIZE = 100
_POSITION_FORMAT = "document-cursor-v1"
_POSITION_MODES = frozenset({"visual", "source", "preview"})
_POSITION_MAX_OFFSET = 32_000
_POSITION_MAX_SCROLL = 2_000_000
_POSITION_MAX_LINE = 50_000
_POSITION_KEYS = frozenset(
    {
        "format",
        "mode",
        "cursor_start",
        "cursor_end",
        "line_index",
        "scroll_top",
        "document_sequence",
        "active",
        "start_anchor",
        "end_anchor",
    }
)
_ANCHOR_KEYS = frozenset({"left_id", "right_id", "affinity", "fallback"})
_DOCUMENT_NODE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$")


def _client_id(value: object) -> str:
    result = str(value or "").strip()
    if not _CLIENT_ID_RE.fullmatch(result):
        raise HTTPException(status_code=422, detail="Invalid collaboration client id")
    return result


def _position_integer(value: object, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise HTTPException(status_code=422, detail=f"Invalid collaboration {label}")
    return value


def _position_anchor(value: object, label: str) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - _ANCHOR_KEYS:
        raise HTTPException(status_code=422, detail=f"Invalid collaboration {label}")
    left_id = str(value.get("left_id") or "^").strip()
    right_value = value.get("right_id")
    right_id = None if right_value is None else str(right_value).strip()
    if left_id != "^" and not _DOCUMENT_NODE_ID_RE.fullmatch(left_id):
        raise HTTPException(status_code=422, detail=f"Invalid collaboration {label}")
    if right_id is not None and not _DOCUMENT_NODE_ID_RE.fullmatch(right_id):
        raise HTTPException(status_code=422, detail=f"Invalid collaboration {label}")
    affinity = str(value.get("affinity") or "backward").strip().lower()
    if affinity not in {"forward", "backward"}:
        raise HTTPException(status_code=422, detail=f"Invalid collaboration {label}")
    return {
        "left_id": left_id,
        "right_id": right_id,
        "affinity": affinity,
        "fallback": _position_integer(
            value.get("fallback", 0), f"{label} fallback", _POSITION_MAX_OFFSET
        ),
    }


def _position_payload(value: object) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - _POSITION_KEYS:
        raise HTTPException(status_code=422, detail="Invalid collaboration position")
    if value.get("format") != _POSITION_FORMAT:
        raise HTTPException(status_code=422, detail="Invalid collaboration position format")
    mode = str(value.get("mode") or "").strip().lower()
    if mode not in _POSITION_MODES:
        raise HTTPException(status_code=422, detail="Invalid collaboration position mode")
    cursor_start = _position_integer(
        value.get("cursor_start"), "cursor start", _POSITION_MAX_OFFSET
    )
    cursor_end = _position_integer(
        value.get("cursor_end"), "cursor end", _POSITION_MAX_OFFSET
    )
    if cursor_end < cursor_start:
        raise HTTPException(status_code=422, detail="Invalid collaboration cursor range")
    active = value.get("active")
    if not isinstance(active, bool):
        raise HTTPException(status_code=422, detail="Invalid collaboration cursor state")
    return {
        "format": _POSITION_FORMAT,
        "mode": mode,
        "cursor_start": cursor_start,
        "cursor_end": cursor_end,
        "line_index": _position_integer(
            value.get("line_index", 0), "line index", _POSITION_MAX_LINE
        ),
        "scroll_top": _position_integer(
            value.get("scroll_top", 0), "scroll position", _POSITION_MAX_SCROLL
        ),
        "document_sequence": _position_integer(
            value.get("document_sequence", 0),
            "document sequence",
            9_007_199_254_740_991,
        ),
        "active": active,
        "start_anchor": _position_anchor(value.get("start_anchor"), "start anchor"),
        "end_anchor": _position_anchor(value.get("end_anchor"), "end anchor"),
    }


def _position_view(row: dict[str, object] | None) -> dict[str, object] | None:
    if not row or not isinstance(row.get("position"), dict):
        return None
    result = dict(row["position"])
    result["updated_at"] = row.get("updated_at")
    return result


def _saved_position(
    actor: ActorContext, task_id: UUID, space_id: UUID
) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        _task(session, task_id)
        _require_member(session, space_id, actor.user_id)
        row = (
            session.execute(
                text(
                    """
                    SELECT position, updated_at
                    FROM workflow.task_collaboration_positions
                    WHERE space_id = :space_id AND user_id = :user_id
                    """
                ),
                {"space_id": space_id, "user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        return _position_view(dict(row) if row else None)


def get_position(actor: ActorContext, task_id: object) -> dict[str, object]:
    target_id, space_id, _ = _authorized_context(actor, task_id)
    return {
        "task_id": str(target_id),
        "position": _saved_position(actor, target_id, space_id),
    }


def _authorized_context(
    actor: ActorContext, task_id: object
) -> tuple[UUID, UUID, int]:
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        _task(session, target_id)
        space = _space(session, target_id)
        assert space is not None
        space_id = UUID(str(space["id"]))
        _require_member(session, space_id, actor.user_id)
        cursor = int(
            session.execute(
                text(
                    """
                    SELECT coalesce(max(id), 0)
                    FROM workflow.task_collaboration_events
                    WHERE space_id = :space_id AND task_id = :task_id
                    """
                ),
                {"space_id": space_id, "task_id": target_id},
            ).scalar_one()
        )
    return target_id, space_id, cursor


def authorize_stream(actor: ActorContext, task_id: object) -> dict[str, object]:
    target_id, space_id, cursor = _authorized_context(actor, task_id)
    return {"task_id": target_id, "space_id": space_id, "cursor": cursor}


def _presence_snapshot(
    actor: ActorContext, task_id: UUID, space_id: UUID
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        _task(session, task_id)
        _require_member(session, space_id, actor.user_id)
        session.execute(
            text(
                """
                DELETE FROM workflow.task_collaboration_presence
                WHERE space_id = :space_id AND expires_at <= now()
                """
            ),
            {"space_id": space_id},
        )
        rows = session.execute(
            text(
                """
                WITH active AS (
                  SELECT p.*
                  FROM workflow.task_collaboration_presence AS p
                  WHERE p.space_id = :space_id AND p.expires_at > now()
                ),
                latest AS (
                  SELECT DISTINCT ON (p.user_id)
                         p.user_id, p.position, p.updated_at
                  FROM active AS p
                  ORDER BY p.user_id, (p.position IS NOT NULL) DESC, p.updated_at DESC
                ),
                activity AS (
                  SELECT p.user_id, bool_or(p.typing) AS typing,
                         max(p.updated_at) AS updated_at
                  FROM active AS p GROUP BY p.user_id
                )
                SELECT a.user_id, u.username, u.display_name,
                       a.typing, a.updated_at, latest.position
                FROM activity AS a
                JOIN latest ON latest.user_id = a.user_id
                JOIN iam.users AS u ON u.id = a.user_id
                JOIN workflow.task_collaboration_members AS m
                  ON m.space_id = :space_id AND m.user_id = a.user_id
                 AND m.state = 'active'
                ORDER BY a.updated_at DESC, a.user_id
                """
            ),
            {"space_id": space_id},
        ).mappings()
        return [
            {
                "user_id": str(row["user_id"]),
                "username": row["username"],
                "display_name": row["display_name"] or row["username"],
                "typing": bool(row["typing"]),
                "state": "active",
                "position": row["position"] if isinstance(row["position"], dict) else None,
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]


def update_presence(
    actor: ActorContext, task_id: object, payload: dict[str, object]
) -> dict[str, object]:
    client_id = _client_id(payload.get("client_id"))
    state = str(payload.get("state") or "active").strip().lower()
    if state not in {"active", "offline"}:
        raise HTTPException(status_code=422, detail="Invalid presence state")
    if payload.get("typing") not in {None, True, False}:
        raise HTTPException(status_code=422, detail="typing must be a boolean")
    if payload.get("persist_position") not in {None, True, False}:
        raise HTTPException(status_code=422, detail="persist_position must be a boolean")
    typing = payload.get("typing") is True
    position = _position_payload(payload.get("position"))
    persist_position = payload.get("persist_position") is True
    target_id, space_id, _ = _authorized_context(actor, task_id)
    with tenant_session(actor.tenant_id) as session:
        _task(session, target_id)
        _require_member(session, space_id, actor.user_id)
        if position is not None and persist_position:
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_positions(
                      tenant_id, space_id, user_id, position
                    ) VALUES (
                      :tenant_id, :space_id, :user_id, CAST(:position AS jsonb)
                    )
                    ON CONFLICT (tenant_id, space_id, user_id)
                    DO UPDATE SET position = EXCLUDED.position, updated_at = now()
                    WHERE workflow.task_collaboration_positions.position
                          IS DISTINCT FROM EXCLUDED.position
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "space_id": space_id,
                    "user_id": actor.user_id,
                    "position": json.dumps(position, separators=(",", ":")),
                },
            )
        if state == "offline":
            session.execute(
                text(
                    """
                    DELETE FROM workflow.task_collaboration_presence
                    WHERE space_id = :space_id AND user_id = :user_id
                      AND client_id = :client_id
                    """
                ),
                {
                    "space_id": space_id,
                    "user_id": actor.user_id,
                    "client_id": client_id,
                },
            )
        else:
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_presence(
                      tenant_id, space_id, user_id, client_id, typing, position, expires_at
                    ) VALUES (
                      :tenant_id, :space_id, :user_id, :client_id, :typing,
                      CAST(:position AS jsonb),
                      now() + interval '45 seconds'
                    )
                    ON CONFLICT (tenant_id, space_id, user_id, client_id)
                    DO UPDATE SET typing = EXCLUDED.typing,
                                  position = COALESCE(
                                    EXCLUDED.position,
                                    workflow.task_collaboration_presence.position
                                  ),
                                  expires_at = EXCLUDED.expires_at,
                                  updated_at = now()
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "space_id": space_id,
                    "user_id": actor.user_id,
                    "client_id": client_id,
                    "typing": typing,
                    "position": (
                        json.dumps(position, separators=(",", ":"))
                        if position is not None
                        else None
                    ),
                },
            )
    presence = _presence_snapshot(actor, target_id, space_id)
    return {
        "result": "updated",
        "task_id": str(target_id),
        "state": state,
        "presence": presence,
        "position": _saved_position(actor, target_id, space_id),
        "typing_user_ids": [item["user_id"] for item in presence if item["typing"]],
    }


def _json_line(value: dict[str, object]) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str) + "\n"
    ).encode("utf-8")


def _presence_hash(presence: list[dict[str, object]]) -> str:
    stable = [
        {
            "user_id": item["user_id"],
            "typing": item["typing"],
            "state": item["state"],
            "position": item.get("position"),
        }
        for item in presence
    ]
    return hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _event_view(task_id: UUID, row: dict[str, object]) -> dict[str, object]:
    event_type = str(row["event_type"])
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    if event_type == "message_sent":
        event = "message.created"
        safe_payload = {
            "message_id": payload.get("message_id"),
            "channel_id": payload.get("channel_id"),
        }
    elif event_type in {"document_created", "document_updated"}:
        event = "document.updated"
        safe_payload = {
            "document_id": payload.get("document_id"),
            "document_sequence": payload.get("sequence", 0),
        }
    elif event_type in {
        "annotation_created",
        "annotation_message_created",
        "annotation_status_changed",
    }:
        event = "annotation.changed"
        safe_payload = {
            "annotation_id": payload.get("annotation_id"),
            "status": payload.get("status"),
        }
    else:
        event = "workspace.changed"
        safe_payload = {}
    return {
        "event": event,
        "event_id": int(row["id"]),
        "sequence": int(row["id"]),
        "task_id": str(task_id),
        "occurred_at": row["created_at"],
        "payload": safe_payload,
    }


def _read_events(
    actor: ActorContext,
    task_id: UUID,
    space_id: UUID,
    cursor: int,
) -> tuple[list[dict[str, object]], int, int]:
    with tenant_session(actor.tenant_id) as session:
        _task(session, task_id)
        _require_member(session, space_id, actor.user_id)
        current = int(
            session.execute(
                text(
                    """
                    SELECT coalesce(max(id), 0)
                    FROM workflow.task_collaboration_events
                    WHERE space_id = :space_id AND task_id = :task_id
                    """
                ),
                {"space_id": space_id, "task_id": task_id},
            ).scalar_one()
        )
        rows = session.execute(
            text(
                """
                SELECT id, event_type, payload, created_at
                FROM workflow.task_collaboration_events
                WHERE space_id = :space_id AND task_id = :task_id AND id > :cursor
                ORDER BY id LIMIT :limit
                """
            ),
            {
                "space_id": space_id,
                "task_id": task_id,
                "cursor": cursor,
                "limit": _BATCH_SIZE,
            },
        ).mappings()
        events = [_event_view(task_id, dict(row)) for row in rows]
    next_cursor = int(events[-1]["event_id"]) if events else cursor
    return events, next_cursor, current


def event_stream(
    actor: ActorContext,
    task_id: object,
    after_event_id: int,
) -> Iterator[bytes]:
    target_id, space_id, current = _authorized_context(actor, task_id)
    cursor = max(0, int(after_event_id))
    if cursor == 0:
        cursor = current
    elif cursor > current or current - cursor > _MAX_REPLAY:
        cursor = current
    presence = _presence_snapshot(actor, target_id, space_id)
    presence_hash = _presence_hash(presence)
    resume_position = _saved_position(actor, target_id, space_id)
    yield _json_line(
        {
            "event": "ready",
            "task_id": str(target_id),
            "event_cursor": cursor,
            "presence": presence,
            "resume_position": resume_position,
            "typing_user_ids": [item["user_id"] for item in presence if item["typing"]],
        }
    )
    started = time.monotonic()
    heartbeat_at = started + _HEARTBEAT_SECONDS
    while time.monotonic() - started < _STREAM_SECONDS:
        time.sleep(_POLL_SECONDS)
        try:
            events, cursor, current = _read_events(
                actor, target_id, space_id, cursor
            )
            for event in events:
                yield _json_line(event)
            next_presence = _presence_snapshot(actor, target_id, space_id)
        except HTTPException:
            yield _json_line({"event": "access.revoked", "task_id": str(target_id)})
            return
        next_hash = _presence_hash(next_presence)
        if next_hash != presence_hash:
            presence = next_presence
            presence_hash = next_hash
            yield _json_line(
                {
                    "event": "presence.changed",
                    "task_id": str(target_id),
                    "event_cursor": cursor,
                    "presence": presence,
                    "typing_user_ids": [
                        item["user_id"] for item in presence if item["typing"]
                    ],
                }
            )
        if time.monotonic() >= heartbeat_at:
            yield _json_line(
                {
                    "event": "heartbeat",
                    "task_id": str(target_id),
                    "event_cursor": max(cursor, current),
                    "presence": presence,
                }
            )
            heartbeat_at = time.monotonic() + _HEARTBEAT_SECONDS
    yield _json_line(
        {
            "event": "reconnect",
            "task_id": str(target_id),
            "event_cursor": cursor,
            "retry_after_ms": 0,
        }
    )


__all__ = ["authorize_stream", "event_stream", "get_position", "update_presence"]
