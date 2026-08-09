"""CRDT-anchored annotations and discussion threads for TASK collaboration."""

from __future__ import annotations

import json
import re
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.task_collaboration import _event, _uuid, _writable
from app.services.task_collaboration_documents import (
    EDITABLE_ROLES,
    MAX_CLOCK,
    MAX_VISIBLE_CHARACTERS,
    _context,
    _ensure_document,
    _verified_state,
)

_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_NODE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$")
_ANCHOR_KEYS = frozenset({"left_id", "right_id", "affinity", "fallback"})
_STATUSES = frozenset({"open", "resolved"})
_MAX_QUOTE = 2_000
_MAX_MESSAGE = 4_000
_MAX_ANNOTATIONS = 500


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _identifier(value: object, label: str) -> str:
    result = str(value or "").strip()
    if not _CLIENT_ID_RE.fullmatch(result):
        raise _error(422, f"Invalid {label}")
    return result


def _integer(value: object, label: str, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise _error(422, f"Invalid {label}")
    return value


def _anchor(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) - _ANCHOR_KEYS:
        raise _error(422, f"Invalid {label}")
    left_id = str(value.get("left_id") or "^").strip()
    right_value = value.get("right_id")
    right_id = None if right_value is None else str(right_value).strip()
    if left_id != "^" and not _NODE_ID_RE.fullmatch(left_id):
        raise _error(422, f"Invalid {label}")
    if right_id is not None and not _NODE_ID_RE.fullmatch(right_id):
        raise _error(422, f"Invalid {label}")
    affinity = str(value.get("affinity") or "backward").strip().lower()
    if affinity not in {"forward", "backward"}:
        raise _error(422, f"Invalid {label}")
    return {
        "left_id": left_id,
        "right_id": right_id,
        "affinity": affinity,
        "fallback": _integer(
            value.get("fallback", 0), f"{label} fallback", MAX_VISIBLE_CHARACTERS
        ),
    }


def _body(value: object) -> str:
    result = str(value or "").strip()
    if not result or len(result) > _MAX_MESSAGE or "\x00" in result:
        raise _error(422, f"Annotation message must be between 1 and {_MAX_MESSAGE} characters")
    return result


def _quote(value: object) -> str:
    result = str(value or "").strip()
    if not result or len(result) > _MAX_QUOTE or "\x00" in result:
        raise _error(422, f"Annotation quote must be between 1 and {_MAX_QUOTE} characters")
    return result


def _can_write(task: dict[str, object], member: dict[str, object], document: dict[str, object]) -> bool:
    return bool(
        task["status"] not in {"completed", "cancelled"}
        and document["state"] == "active"
        and member["role"] in EDITABLE_ROLES
    )


def _annotation_rows(session: object, document_id: UUID, status: str) -> list[dict[str, object]]:
    status_clause = "" if status == "all" else "AND a.status = :status"
    rows = session.execute(
        text(
            f"""
            SELECT a.*, author.username AS author_username,
                   author.display_name AS author_name,
                   resolver.username AS resolver_username,
                   resolver.display_name AS resolver_name
            FROM workflow.task_collaboration_annotations AS a
            JOIN iam.users AS author ON author.id = a.author_user_id
            LEFT JOIN iam.users AS resolver ON resolver.id = a.resolved_by_user_id
            WHERE a.document_id = :document_id {status_clause}
            ORDER BY CASE WHEN a.status = 'open' THEN 0 ELSE 1 END,
                     a.created_at, a.id
            LIMIT :limit
            """
        ),
        {"document_id": document_id, "status": status, "limit": _MAX_ANNOTATIONS},
    ).mappings()
    return [dict(row) for row in rows]


def _message_rows(session: object, annotation_ids: list[UUID]) -> dict[str, list[dict[str, object]]]:
    if not annotation_ids:
        return {}
    rows = session.execute(
        text(
            """
            SELECT m.*, author.username AS author_username,
                   author.display_name AS author_name
            FROM workflow.task_collaboration_annotation_messages AS m
            JOIN iam.users AS author ON author.id = m.author_user_id
            WHERE m.annotation_id = ANY(:annotation_ids)
            ORDER BY m.annotation_id, m.id
            """
        ),
        {"annotation_ids": annotation_ids},
    ).mappings()
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        item = dict(row)
        grouped.setdefault(str(item["annotation_id"]), []).append(item)
    return grouped


def _message_view(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": int(row["id"]),
        "annotation_id": str(row["annotation_id"]),
        "author_user_id": str(row["author_user_id"]),
        "author_name": row.get("author_name") or row.get("author_username"),
        "body": row["body"],
        "created_at": row["created_at"],
    }


def _annotation_view(
    row: dict[str, object], messages: list[dict[str, object]], actor: ActorContext,
    *, can_manage: bool,
) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "document_id": str(row["document_id"]),
        "author_user_id": str(row["author_user_id"]),
        "author_name": row.get("author_name") or row.get("author_username"),
        "start_anchor": row["start_anchor"],
        "end_anchor": row["end_anchor"],
        "start_offset": int(row["start_offset"]),
        "end_offset": int(row["end_offset"]),
        "document_sequence": int(row["document_sequence"]),
        "quote": row["quote"],
        "status": row["status"],
        "resolved_by_user_id": (
            str(row["resolved_by_user_id"]) if row.get("resolved_by_user_id") else None
        ),
        "resolved_by_name": row.get("resolver_name") or row.get("resolver_username"),
        "resolved_at": row.get("resolved_at"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "can_resolve": bool(can_manage or row["author_user_id"] == actor.user_id),
        "messages": [_message_view(message) for message in messages],
    }


def list_annotations(
    actor: ActorContext, task_id: object, status: str = "all"
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    status_value = str(status or "all").strip().lower()
    if status_value not in _STATUSES | {"all"}:
        raise _error(422, "Invalid annotation status")
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        document = _ensure_document(session, actor, space)
        rows = _annotation_rows(session, UUID(str(document["id"])), status_value)
        messages = _message_rows(session, [UUID(str(row["id"])) for row in rows])
        can_manage = member["role"] in {"owner", "coordinator"}
        return {
            "task_id": str(target_id),
            "document_id": str(document["id"]),
            "document_sequence": int(document["latest_sequence"]),
            "capabilities": {
                "can_read": True,
                "can_annotate": _can_write(task, member, document),
            },
            "items": [
                _annotation_view(
                    row, messages.get(str(row["id"]), []), actor, can_manage=can_manage
                )
                for row in rows
            ],
        }


def create_annotation(
    actor: ActorContext, task_id: object, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    client_annotation_id = _identifier(
        payload.get("client_annotation_id"), "client annotation id"
    )
    client_message_id = _identifier(payload.get("client_message_id"), "client message id")
    start_anchor = _anchor(payload.get("start_anchor"), "annotation start anchor")
    end_anchor = _anchor(payload.get("end_anchor"), "annotation end anchor")
    start_offset = _integer(
        payload.get("start_offset"), "annotation start offset", MAX_VISIBLE_CHARACTERS
    )
    end_offset = _integer(
        payload.get("end_offset"), "annotation end offset", MAX_VISIBLE_CHARACTERS
    )
    if end_offset <= start_offset:
        raise _error(422, "Annotation must select a non-empty range")
    sequence = _integer(payload.get("document_sequence"), "document sequence", MAX_CLOCK)
    quote = _quote(payload.get("quote"))
    body = _body(payload.get("body"))
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        document = _ensure_document(session, actor, space, lock=True)
        if not _can_write(task, member, document):
            raise _error(403, "Observer membership cannot annotate the collaboration document")
        nodes, _ = _verified_state(session, document)
        for anchor in (start_anchor, end_anchor):
            for node_id in (anchor["left_id"], anchor["right_id"]):
                if node_id not in {None, "^"} and node_id not in nodes:
                    raise _error(409, "Annotation selection is stale; select the text again")
        existing = session.execute(
            text(
                """
                SELECT id, start_anchor, end_anchor, start_offset, end_offset,
                       document_sequence, quote
                FROM workflow.task_collaboration_annotations
                WHERE document_id = :document_id AND author_user_id = :user_id
                  AND client_annotation_id = :client_annotation_id
                """
            ),
            {
                "document_id": document["id"],
                "user_id": actor.user_id,
                "client_annotation_id": client_annotation_id,
            },
        ).mappings().one_or_none()
        if existing is None:
            annotation_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_annotations(
                      id, tenant_id, space_id, document_id, author_user_id,
                      client_annotation_id, start_anchor, end_anchor, start_offset,
                      end_offset, document_sequence, quote
                    ) VALUES (
                      :id, :tenant_id, :space_id, :document_id, :user_id,
                      :client_annotation_id, CAST(:start_anchor AS jsonb),
                      CAST(:end_anchor AS jsonb), :start_offset, :end_offset,
                      :document_sequence, :quote
                    )
                    """
                ),
                {
                    "id": annotation_id,
                    "tenant_id": actor.tenant_id,
                    "space_id": space["id"],
                    "document_id": document["id"],
                    "user_id": actor.user_id,
                    "client_annotation_id": client_annotation_id,
                    "start_anchor": json.dumps(start_anchor, separators=(",", ":")),
                    "end_anchor": json.dumps(end_anchor, separators=(",", ":")),
                    "start_offset": start_offset,
                    "end_offset": end_offset,
                    "document_sequence": sequence,
                    "quote": quote,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_annotation_messages(
                      tenant_id, annotation_id, author_user_id, client_message_id, body
                    ) VALUES (
                      :tenant_id, :annotation_id, :user_id, :client_message_id, :body
                    )
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "annotation_id": annotation_id,
                    "user_id": actor.user_id,
                    "client_message_id": client_message_id,
                    "body": body,
                },
            )
            _event(
                session,
                actor,
                space,
                "annotation_created",
                subject_user_id=actor.user_id,
                payload={"annotation_id": str(annotation_id), "document_id": str(document["id"])},
            )
            created = True
        else:
            if (
                existing["start_anchor"] != start_anchor
                or existing["end_anchor"] != end_anchor
                or int(existing["start_offset"]) != start_offset
                or int(existing["end_offset"]) != end_offset
                or int(existing["document_sequence"]) != sequence
                or existing["quote"] != quote
            ):
                raise _error(409, "client_annotation_id was already used for another annotation")
            annotation_id = UUID(str(existing["id"]))
            initial_message = session.execute(
                text(
                    """
                    SELECT body FROM workflow.task_collaboration_annotation_messages
                    WHERE annotation_id = :annotation_id AND author_user_id = :user_id
                      AND client_message_id = :client_message_id
                    """
                ),
                {
                    "annotation_id": annotation_id,
                    "user_id": actor.user_id,
                    "client_message_id": client_message_id,
                },
            ).scalar_one_or_none()
            if initial_message != body:
                raise _error(409, "Annotation retry does not match its original discussion")
            created = False
    response = list_annotations(actor, target_id, "all")
    annotation = next(item for item in response["items"] if item["id"] == str(annotation_id))
    return {"result": "created" if created else "idempotent", "annotation": annotation}


def add_annotation_message(
    actor: ActorContext, task_id: object, annotation_id: object, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    target_annotation_id = _uuid(annotation_id, "annotation id")
    client_message_id = _identifier(payload.get("client_message_id"), "client message id")
    body = _body(payload.get("body"))
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        document = _ensure_document(session, actor, space)
        if not _can_write(task, member, document):
            raise _error(403, "Observer membership cannot discuss collaboration annotations")
        annotation = session.execute(
            text(
                """
                SELECT id FROM workflow.task_collaboration_annotations
                WHERE id = :annotation_id AND document_id = :document_id
                """
            ),
            {"annotation_id": target_annotation_id, "document_id": document["id"]},
        ).scalar_one_or_none()
        if annotation is None:
            raise _error(404, "Collaboration annotation not found")
        existing_message = session.execute(
            text(
                """
                SELECT id, body
                FROM workflow.task_collaboration_annotation_messages
                WHERE annotation_id = :annotation_id AND author_user_id = :user_id
                  AND client_message_id = :client_message_id
                """
            ),
            {
                "annotation_id": target_annotation_id,
                "user_id": actor.user_id,
                "client_message_id": client_message_id,
            },
        ).mappings().one_or_none()
        if existing_message is not None:
            if existing_message["body"] != body:
                raise _error(409, "client_message_id was already used for another message")
            message_id = int(existing_message["id"])
            created = False
        else:
            message_id = int(
                session.execute(
                    text(
                        """
                        INSERT INTO workflow.task_collaboration_annotation_messages(
                          tenant_id, annotation_id, author_user_id, client_message_id, body
                        ) VALUES (
                          :tenant_id, :annotation_id, :user_id, :client_message_id, :body
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "tenant_id": actor.tenant_id,
                        "annotation_id": target_annotation_id,
                        "user_id": actor.user_id,
                        "client_message_id": client_message_id,
                        "body": body,
                    },
                ).scalar_one()
            )
            _event(
                session,
                actor,
                space,
                "annotation_message_created",
                subject_user_id=actor.user_id,
                payload={"annotation_id": str(target_annotation_id), "message_id": message_id},
            )
            created = True
    response = list_annotations(actor, target_id, "all")
    annotation_view = next(
        item for item in response["items"] if item["id"] == str(target_annotation_id)
    )
    return {"result": "created" if created else "idempotent", "annotation": annotation_view}


def update_annotation_status(
    actor: ActorContext, task_id: object, annotation_id: object, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    target_annotation_id = _uuid(annotation_id, "annotation id")
    status = str(payload.get("status") or "").strip().lower()
    if status not in _STATUSES:
        raise _error(422, "Invalid annotation status")
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        document = _ensure_document(session, actor, space)
        annotation = session.execute(
            text(
                """
                SELECT author_user_id FROM workflow.task_collaboration_annotations
                WHERE id = :annotation_id AND document_id = :document_id
                """
            ),
            {"annotation_id": target_annotation_id, "document_id": document["id"]},
        ).mappings().one_or_none()
        if annotation is None:
            raise _error(404, "Collaboration annotation not found")
        if member["role"] not in {"owner", "coordinator"} and annotation["author_user_id"] != actor.user_id:
            raise _error(403, "Only the annotation author or a coordinator can change its status")
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_annotations
                SET status = :status,
                    resolved_by_user_id = CASE WHEN :status = 'resolved' THEN :user_id ELSE NULL END,
                    resolved_at = CASE WHEN :status = 'resolved' THEN now() ELSE NULL END,
                    updated_at = now()
                WHERE id = :annotation_id
                """
            ),
            {"status": status, "user_id": actor.user_id, "annotation_id": target_annotation_id},
        )
        _event(
            session,
            actor,
            space,
            "annotation_status_changed",
            subject_user_id=actor.user_id,
            payload={"annotation_id": str(target_annotation_id), "status": status},
        )
    response = list_annotations(actor, target_id, "all")
    annotation_view = next(
        item for item in response["items"] if item["id"] == str(target_annotation_id)
    )
    return {"result": "updated", "annotation": annotation_view}


__all__ = [
    "add_annotation_message",
    "create_annotation",
    "list_annotations",
    "update_annotation_status",
]
