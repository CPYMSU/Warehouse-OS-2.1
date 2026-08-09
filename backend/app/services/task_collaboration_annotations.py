"""CRDT-anchored annotations and discussion threads for TASK collaboration."""

from __future__ import annotations

import json
import re
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session
from app.services.task_collaboration import _event, _uuid, _writable
from app.services.task_collaboration_documents import (
    EDITABLE_ROLES,
    MAX_CLOCK,
    MAX_UPDATES_PER_DOCUMENT,
    MAX_VISIBLE_CHARACTERS,
    ROOT_ELEMENT_ID,
    _context,
    _document_row,
    _ensure_document,
    _ordered_nodes,
    _verified_state,
    append_update_in_session,
)

_CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_NODE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$")
_ANCHOR_KEYS = frozenset({"left_id", "right_id", "affinity", "fallback"})
_STATUSES = frozenset({"open", "resolved"})
_KINDS = frozenset({"comment", "suggestion"})
_REVIEW_STATES = frozenset({"none", "pending", "accepted", "rejected", "conflicted"})
_REVIEWER_ROLES = frozenset({"owner", "coordinator", "reviewer"})
_MAX_QUOTE = 2_000
_MAX_PROPOSED_TEXT = 2_000
_MAX_MESSAGE = 4_000
_MAX_ANNOTATIONS = 500
_REVIEW_UPDATE_CHUNK = 300


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
    result = str(value or "")
    if not result.strip() or len(result) > _MAX_QUOTE or "\x00" in result:
        raise _error(422, f"Annotation quote must be between 1 and {_MAX_QUOTE} characters")
    return result


def _proposed_text(value: object) -> str:
    if not isinstance(value, str):
        raise _error(422, "Review change must include proposed_text")
    if len(value) > _MAX_PROPOSED_TEXT or "\x00" in value:
        raise _error(
            422,
            f"Review change proposal must contain at most {_MAX_PROPOSED_TEXT} characters",
        )
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise _error(422, "Review change proposal contains invalid Unicode") from exc
    return value


def _selection_index(
    nodes: dict[str, dict[str, object]],
) -> tuple[dict[str, int], dict[str, int], list[dict[str, object]], str, int]:
    before = {ROOT_ELEMENT_ID: 0}
    after = {ROOT_ELEMENT_ID: 0}
    visible: list[dict[str, object]] = []
    content: list[str] = []
    offset = 0
    for node in _ordered_nodes(nodes):
        element_id = str(node["id"])
        before[element_id] = offset
        if not node["deleted"]:
            value = str(node["value"])
            length = len(value.encode("utf-16-le")) // 2
            visible.append(
                {
                    "id": element_id,
                    "start": offset,
                    "end": offset + length,
                    "value": value,
                }
            )
            content.append(value)
            offset += length
        after[element_id] = offset
    return before, after, visible, "".join(content), offset


def _resolve_boundary(
    before: dict[str, int],
    after: dict[str, int],
    total: int,
    anchor: object,
    fallback_value: object,
) -> int:
    value = anchor if isinstance(anchor, dict) else {}
    fallback = min(max(int(fallback_value or value.get("fallback") or 0), 0), total)
    left_id = str(value.get("left_id") or ROOT_ELEMENT_ID)
    right_value = value.get("right_id")
    right_id = None if right_value is None else str(right_value)
    if value.get("affinity") == "forward":
        if right_id is not None and right_id in before:
            return before[right_id]
        if right_id is None:
            return total
        if left_id in after:
            return after[left_id]
    else:
        if left_id in after:
            return after[left_id]
        if right_id is not None and right_id in before:
            return before[right_id]
    return fallback


def _resolved_range(
    row: dict[str, object],
    index: tuple[dict[str, int], dict[str, int], list[dict[str, object]], str, int],
) -> dict[str, object]:
    before, after, visible, content, total = index
    start = _resolve_boundary(
        before, after, total, row["start_anchor"], row["start_offset"]
    )
    end = max(
        start,
        _resolve_boundary(
            before, after, total, row["end_anchor"], row["end_offset"]
        ),
    )
    current_quote = "".join(
        str(item["value"])
        for item in visible
        if int(item["start"]) >= start and int(item["end"]) <= end
    )
    original = str(row["quote"])
    anchor_state = "exact" if current_quote == original else (
        "deleted" if end <= start or not current_quote else "modified"
    )
    return {
        "start": start,
        "end": end,
        "current_quote": current_quote,
        "anchor_state": anchor_state,
        "visible": visible,
        "content": content,
    }


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
                   resolver.display_name AS resolver_name,
                   reviewer.username AS reviewer_username,
                   reviewer.display_name AS reviewer_name
            FROM workflow.task_collaboration_annotations AS a
            JOIN iam.users AS author ON author.id = a.author_user_id
            LEFT JOIN iam.users AS resolver ON resolver.id = a.resolved_by_user_id
            LEFT JOIN iam.users AS reviewer ON reviewer.id = a.reviewed_by_user_id
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
    *, can_manage: bool, can_review: bool,
    resolved: dict[str, object],
) -> dict[str, object]:
    kind = str(row.get("kind") or "comment")
    review_state = str(row.get("review_state") or "none")
    anchor_state = str(resolved["anchor_state"])
    effective_review_state = (
        "conflicted"
        if kind == "suggestion" and review_state == "pending" and anchor_state != "exact"
        else review_state
    )
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
        "current_quote": resolved["current_quote"],
        "anchor_state": anchor_state,
        "kind": kind,
        "proposed_text": row.get("proposed_text"),
        "review_state": review_state,
        "effective_review_state": effective_review_state,
        "status": row["status"],
        "resolved_by_user_id": (
            str(row["resolved_by_user_id"]) if row.get("resolved_by_user_id") else None
        ),
        "resolved_by_name": row.get("resolver_name") or row.get("resolver_username"),
        "resolved_at": row.get("resolved_at"),
        "reviewed_by_user_id": (
            str(row["reviewed_by_user_id"]) if row.get("reviewed_by_user_id") else None
        ),
        "reviewed_by_name": row.get("reviewer_name") or row.get("reviewer_username"),
        "reviewed_at": row.get("reviewed_at"),
        "accepted_sequence": (
            int(row["accepted_sequence"]) if row.get("accepted_sequence") is not None else None
        ),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "can_resolve": bool(
            kind == "comment" and (can_manage or row["author_user_id"] == actor.user_id)
        ),
        "can_accept": bool(
            kind == "suggestion" and can_review
            and review_state in {"pending", "conflicted"}
            and anchor_state == "exact"
        ),
        "can_reject": bool(
            kind == "suggestion" and can_review
            and review_state in {"pending", "conflicted"}
        ),
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
        nodes, _ = _verified_state(session, document)
        selection_index = _selection_index(nodes)
        rows = _annotation_rows(session, UUID(str(document["id"])), status_value)
        messages = _message_rows(session, [UUID(str(row["id"])) for row in rows])
        can_manage = member["role"] in {"owner", "coordinator"}
        can_review = member["role"] in _REVIEWER_ROLES
        return {
            "task_id": str(target_id),
            "document_id": str(document["id"]),
            "document_sequence": int(document["latest_sequence"]),
            "capabilities": {
                "can_read": True,
                "can_annotate": _can_write(task, member, document),
                "can_propose": _can_write(task, member, document),
                "can_review": bool(_can_write(task, member, document) and can_review),
            },
            "items": [
                _annotation_view(
                    row,
                    messages.get(str(row["id"]), []),
                    actor,
                    can_manage=can_manage,
                    can_review=can_review,
                    resolved=_resolved_range(row, selection_index),
                )
                for row in rows
            ],
        }


def create_annotation(
    actor: ActorContext, task_id: object, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    kind = str(payload.get("kind") or "comment").strip().lower()
    if kind not in _KINDS:
        raise _error(422, "Invalid annotation kind")
    proposed_text = _proposed_text(payload.get("proposed_text")) if kind == "suggestion" else None
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
    if kind == "suggestion" and proposed_text == quote:
        raise _error(422, "Review change proposal must differ from the selected text")
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
                       document_sequence, quote, kind, proposed_text
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
                      end_offset, document_sequence, quote, kind, proposed_text,
                      review_state
                    ) VALUES (
                      :id, :tenant_id, :space_id, :document_id, :user_id,
                      :client_annotation_id, CAST(:start_anchor AS jsonb),
                      CAST(:end_anchor AS jsonb), :start_offset, :end_offset,
                      :document_sequence, :quote, :kind, :proposed_text,
                      :review_state
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
                    "kind": kind,
                    "proposed_text": proposed_text,
                    "review_state": "pending" if kind == "suggestion" else "none",
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
                "review_change_created" if kind == "suggestion" else "annotation_created",
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
                or existing["kind"] != kind
                or existing["proposed_text"] != proposed_text
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


def create_review_change(
    actor: ActorContext, task_id: object, payload: dict[str, object]
) -> dict[str, object]:
    value = dict(payload)
    value["kind"] = "suggestion"
    return create_annotation(actor, task_id, value)


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
                SELECT author_user_id, kind FROM workflow.task_collaboration_annotations
                WHERE id = :annotation_id AND document_id = :document_id
                """
            ),
            {"annotation_id": target_annotation_id, "document_id": document["id"]},
        ).mappings().one_or_none()
        if annotation is None:
            raise _error(404, "Collaboration annotation not found")
        if annotation["kind"] == "suggestion":
            raise _error(409, "Review changes must be accepted or rejected")
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


def _review_annotation(
    session: Session, document_id: object, annotation_id: UUID
) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT * FROM workflow.task_collaboration_annotations
                WHERE id = :annotation_id AND document_id = :document_id
                FOR UPDATE
                """
            ),
            {"annotation_id": annotation_id, "document_id": document_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise _error(404, "Review change not found")
    value = dict(row)
    if value["kind"] != "suggestion":
        raise _error(409, "This annotation is not a review change")
    if value["review_state"] not in _REVIEW_STATES - {"none"}:
        raise _error(500, "Review change state is corrupt")
    return value


def _review_view(
    actor: ActorContext, task_id: UUID, annotation_id: UUID, result: str
) -> dict[str, object]:
    response = list_annotations(actor, task_id, "all")
    annotation = next(
        item for item in response["items"] if item["id"] == str(annotation_id)
    )
    return {"result": result, "annotation": annotation}


def accept_review_change(
    actor: ActorContext, task_id: object, annotation_id: object
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    target_annotation_id = _uuid(annotation_id, "review change id")
    conflicted: dict[str, object] | None = None
    result = "accepted"
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        document = _ensure_document(session, actor, space, lock=True)
        annotation = _review_annotation(session, document["id"], target_annotation_id)
        review_state = str(annotation["review_state"])
        if review_state == "accepted":
            result = "idempotent"
        elif review_state == "rejected":
            raise _error(409, "Rejected review changes are terminal")
        else:
            if member["role"] not in _REVIEWER_ROLES:
                raise _error(403, "Only an owner, coordinator, or reviewer can accept changes")
            nodes, _ = _verified_state(session, document)
            resolved = _resolved_range(annotation, _selection_index(nodes))
            if resolved["anchor_state"] != "exact":
                session.execute(
                    text(
                        """
                        UPDATE workflow.task_collaboration_annotations
                        SET review_state = 'conflicted', updated_at = now()
                        WHERE id = :annotation_id
                        """
                    ),
                    {"annotation_id": target_annotation_id},
                )
                _event(
                    session,
                    actor,
                    space,
                    "review_change_conflicted",
                    subject_user_id=actor.user_id,
                    payload={
                        "annotation_id": str(target_annotation_id),
                        "document_id": str(document["id"]),
                        "anchor_state": resolved["anchor_state"],
                    },
                )
                conflicted = {
                    "reason": "source_changed",
                    "anchor_state": resolved["anchor_state"],
                    "current_quote": resolved["current_quote"],
                }
            else:
                visible = list(resolved["visible"])
                start = int(resolved["start"])
                end = int(resolved["end"])
                operations: list[dict[str, object]] = [
                    {"type": "delete", "id": str(item["id"])}
                    for item in visible
                    if int(item["start"]) >= start and int(item["end"]) <= end
                ]
                predecessor = next(
                    (
                        str(item["id"])
                        for item in reversed(visible)
                        if int(item["end"]) <= start
                    ),
                    ROOT_ELEMENT_ID,
                )
                max_clock = max((int(node["clock"]) for node in nodes.values()), default=0)
                for index, character in enumerate(str(annotation["proposed_text"])):
                    element_id = f"review-{target_annotation_id.hex}:{index}"
                    operations.append(
                        {
                            "type": "insert",
                            "id": element_id,
                            "after": predecessor,
                            "value": character,
                            "clock": max_clock + index + 1,
                        }
                    )
                    predecessor = element_id
                chunks = [
                    operations[index : index + _REVIEW_UPDATE_CHUNK]
                    for index in range(0, len(operations), _REVIEW_UPDATE_CHUNK)
                ]
                if int(document["latest_sequence"]) + len(chunks) > MAX_UPDATES_PER_DOCUMENT:
                    raise _error(
                        409,
                        "Collaboration document update limit reached; export and archive it",
                    )
                accepted_sequence = int(document["latest_sequence"])
                for chunk_index, chunk in enumerate(chunks, start=1):
                    response = append_update_in_session(
                        session,
                        actor,
                        task,
                        space,
                        member,
                        document,
                        client_id="review-agent",
                        client_update_id=(
                            f"review-{target_annotation_id.hex}-{chunk_index}"
                        ),
                        operations=chunk,
                    )
                    accepted_sequence = int(response["accepted_sequence"])
                    document = _document_row(
                        session, UUID(str(space["id"])), lock=True
                    )
                    assert document is not None
                session.execute(
                    text(
                        """
                        UPDATE workflow.task_collaboration_annotations
                        SET status = 'resolved', review_state = 'accepted',
                            reviewed_by_user_id = :user_id, reviewed_at = now(),
                            accepted_sequence = :accepted_sequence,
                            resolved_by_user_id = :user_id, resolved_at = now(),
                            updated_at = now()
                        WHERE id = :annotation_id
                        """
                    ),
                    {
                        "user_id": actor.user_id,
                        "accepted_sequence": accepted_sequence,
                        "annotation_id": target_annotation_id,
                    },
                )
                _event(
                    session,
                    actor,
                    space,
                    "review_change_accepted",
                    subject_user_id=actor.user_id,
                    payload={
                        "annotation_id": str(target_annotation_id),
                        "document_id": str(document["id"]),
                        "accepted_sequence": accepted_sequence,
                    },
                )
    if conflicted is not None:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "The selected source changed; review the conflict before retrying",
                **conflicted,
            },
        )
    return _review_view(actor, target_id, target_annotation_id, result)


def reject_review_change(
    actor: ActorContext, task_id: object, annotation_id: object
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    target_annotation_id = _uuid(annotation_id, "review change id")
    result = "rejected"
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        document = _ensure_document(session, actor, space, lock=True)
        annotation = _review_annotation(session, document["id"], target_annotation_id)
        review_state = str(annotation["review_state"])
        if review_state == "rejected":
            result = "idempotent"
        elif review_state == "accepted":
            raise _error(409, "Accepted review changes are terminal")
        else:
            if member["role"] not in _REVIEWER_ROLES:
                raise _error(403, "Only an owner, coordinator, or reviewer can reject changes")
            session.execute(
                text(
                    """
                    UPDATE workflow.task_collaboration_annotations
                    SET status = 'resolved', review_state = 'rejected',
                        reviewed_by_user_id = :user_id, reviewed_at = now(),
                        accepted_sequence = NULL,
                        resolved_by_user_id = :user_id, resolved_at = now(),
                        updated_at = now()
                    WHERE id = :annotation_id
                    """
                ),
                {"user_id": actor.user_id, "annotation_id": target_annotation_id},
            )
            _event(
                session,
                actor,
                space,
                "review_change_rejected",
                subject_user_id=actor.user_id,
                payload={
                    "annotation_id": str(target_annotation_id),
                    "document_id": str(document["id"]),
                },
            )
    return _review_view(actor, target_id, target_annotation_id, result)


__all__ = [
    "accept_review_change",
    "add_annotation_message",
    "create_annotation",
    "create_review_change",
    "list_annotations",
    "reject_review_change",
    "update_annotation_status",
]
