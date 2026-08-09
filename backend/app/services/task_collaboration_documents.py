"""Tenant-scoped CRDT documents for native task collaboration workspaces."""

from __future__ import annotations

import hashlib
import io
import json
import re
import secrets
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import tenant_session
from app.services.object_storage import LocalContentAddressedObjectStore
from app.services.task_collaboration import (
    _event,
    _require_member,
    _space,
    _task,
    _uuid,
    _writable,
)

CRDT_FORMAT = "rga-v1"
DOCUMENT_KEY = "working-draft"
ROOT_ELEMENT_ID = "^"
EDITABLE_ROLES = frozenset({"owner", "coordinator", "contributor", "reviewer"})
DOCUMENT_STATES = frozenset({"active", "locked", "archived"})
MAX_VISIBLE_CHARACTERS = 32_000
MAX_NODES = 50_000
MAX_UPDATE_OPERATIONS = 1_000
MAX_UPDATE_BYTES = 96 * 1024
MAX_UPDATES_PER_DOCUMENT = 20_000
SNAPSHOT_INTERVAL = 50
MAX_CLOCK = 9_007_199_254_740_991
MAX_IMAGE_ASSET_BYTES = 2 * 1024 * 1024
MAX_IMAGE_ASSET_DIMENSION = 2_048
MAX_IMAGE_ASSETS_PER_DOCUMENT = 50
MAX_IMAGE_ASSET_BYTES_PER_DOCUMENT = 32 * 1024 * 1024
IMAGE_ASSET_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,179}$")
_ASSET_KEY_RE = re.compile(r"^img_[A-Za-z0-9_-]{20,80}$")
_EMPTY_SNAPSHOT = {"format": CRDT_FORMAT, "nodes": []}


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_EMPTY_SNAPSHOT_HASH = _hash(_canonical(_EMPTY_SNAPSHOT))


def _error(code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=code, detail=detail)


def _identifier(value: object, label: str) -> str:
    result = str(value or "").strip()
    if not _IDENTIFIER_RE.fullmatch(result):
        raise _error(422, f"Invalid {label}")
    return result


def _has_invalid_unicode(value: str) -> bool:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return True
    return False


def _context(
    session: Session, actor: ActorContext, task_id: UUID
) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    task = _task(session, task_id)
    space = _space(session, task_id)
    assert space is not None
    member = _require_member(session, UUID(str(space["id"])), actor.user_id)
    return task, space, member


def _document_row(
    session: Session, space_id: UUID, *, lock: bool = False
) -> dict[str, object] | None:
    suffix = " FOR UPDATE OF d" if lock else ""
    row = (
        session.execute(
            text(
                f"""
                SELECT d.*, creator.username AS creator_username,
                       creator.display_name AS creator_name,
                       updater.username AS updater_username,
                       updater.display_name AS updater_name
                FROM workflow.task_collaboration_documents AS d
                JOIN iam.users AS creator ON creator.id = d.created_by_user_id
                JOIN iam.users AS updater ON updater.id = d.updated_by_user_id
                WHERE d.space_id = :space_id AND d.document_key = :document_key
                {suffix}
                """
            ),
            {"space_id": space_id, "document_key": DOCUMENT_KEY},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def _ensure_document(
    session: Session,
    actor: ActorContext,
    space: dict[str, object],
    *,
    lock: bool = False,
) -> dict[str, object]:
    space_id = UUID(str(space["id"]))
    document = _document_row(session, space_id, lock=lock)
    if document:
        return document
    document_id = uuid4()
    created = session.execute(
        text(
            """
            INSERT INTO workflow.task_collaboration_documents(
              id, tenant_id, space_id, snapshot_hash,
              created_by_user_id, updated_by_user_id
            ) VALUES (
              :id, :tenant_id, :space_id, :snapshot_hash,
              :user_id, :user_id
            )
            ON CONFLICT (tenant_id, space_id, document_key) DO NOTHING
            RETURNING id
            """
        ),
        {
            "id": document_id,
            "tenant_id": actor.tenant_id,
            "space_id": space_id,
            "snapshot_hash": _EMPTY_SNAPSHOT_HASH,
            "user_id": actor.user_id,
        },
    ).scalar_one_or_none()
    if created is not None:
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_document_snapshots(
                  tenant_id, document_id, sequence, snapshot, snapshot_hash,
                  visible_length, node_count, created_by_user_id
                ) VALUES (
                  :tenant_id, :document_id, 0, CAST(:snapshot AS jsonb),
                  :snapshot_hash, 0, 0, :user_id
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "document_id": document_id,
                "snapshot": _canonical(_EMPTY_SNAPSHOT),
                "snapshot_hash": _EMPTY_SNAPSHOT_HASH,
                "user_id": actor.user_id,
            },
        )
        _event(
            session,
            actor,
            space,
            "document_created",
            subject_user_id=actor.user_id,
            payload={"document_id": str(document_id), "sequence": 0},
        )
    document = _document_row(session, space_id, lock=lock)
    if document is None:
        raise _error(500, "Unable to create collaboration document")
    return document


def _snapshot_nodes(raw_snapshot: object) -> dict[str, dict[str, object]]:
    snapshot = raw_snapshot
    if isinstance(snapshot, str):
        try:
            snapshot = json.loads(snapshot)
        except json.JSONDecodeError as exc:
            raise _error(500, "Collaboration document state is corrupt") from exc
    if not isinstance(snapshot, dict) or snapshot.get("format") != CRDT_FORMAT:
        raise _error(500, "Unsupported collaboration document format")
    rows = snapshot.get("nodes")
    if not isinstance(rows, list) or len(rows) > MAX_NODES:
        raise _error(500, "Collaboration document state is corrupt")
    nodes: dict[str, dict[str, object]] = {}
    for raw in rows:
        if not isinstance(raw, dict):
            raise _error(500, "Collaboration document state is corrupt")
        element_id = str(raw.get("id") or "")
        after = str(raw.get("after") or "")
        value = raw.get("value")
        clock = raw.get("clock")
        if (
            not _IDENTIFIER_RE.fullmatch(element_id)
            or element_id in nodes
            or (after != ROOT_ELEMENT_ID and not _IDENTIFIER_RE.fullmatch(after))
            or not isinstance(value, str)
            or len(value) != 1
            or value == "\x00"
            or _has_invalid_unicode(value)
            or not isinstance(clock, int)
            or isinstance(clock, bool)
            or not 1 <= clock <= MAX_CLOCK
            or not isinstance(raw.get("deleted"), bool)
        ):
            raise _error(500, "Collaboration document state is corrupt")
        nodes[element_id] = {
            "id": element_id,
            "after": after,
            "value": value,
            "clock": clock,
            "deleted": raw["deleted"] is True,
        }
    for node in nodes.values():
        predecessor = str(node["after"])
        if predecessor == node["id"] or (
            predecessor != ROOT_ELEMENT_ID and predecessor not in nodes
        ):
            raise _error(500, "Collaboration document state is corrupt")
    colour: dict[str, int] = {}
    for element_id in nodes:
        if colour.get(element_id) == 2:
            continue
        path: list[str] = []
        cursor = element_id
        while cursor != ROOT_ELEMENT_ID:
            state = colour.get(cursor, 0)
            if state == 1:
                raise _error(500, "Collaboration document state is corrupt")
            if state == 2:
                break
            colour[cursor] = 1
            path.append(cursor)
            cursor = str(nodes[cursor]["after"])
        for visited in path:
            colour[visited] = 2
    return nodes


def _ordered_nodes(nodes: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    children: dict[str, list[dict[str, object]]] = {}
    for node in nodes.values():
        children.setdefault(str(node["after"]), []).append(node)
    for values in children.values():
        values.sort(key=lambda item: (int(item["clock"]), str(item["id"])), reverse=True)
    ordered: list[dict[str, object]] = []
    stack = list(reversed(children.get(ROOT_ELEMENT_ID, [])))
    visited: set[str] = set()
    while stack:
        node = stack.pop()
        element_id = str(node["id"])
        if element_id in visited:
            raise _error(500, "Collaboration document state is corrupt")
        visited.add(element_id)
        ordered.append(node)
        stack.extend(reversed(children.get(element_id, [])))
    if len(visited) != len(nodes):
        raise _error(500, "Collaboration document state is corrupt")
    return ordered


def _render(nodes: dict[str, dict[str, object]]) -> str:
    return "".join(
        str(node["value"]) for node in _ordered_nodes(nodes) if not node["deleted"]
    )


def _snapshot(
    nodes: dict[str, dict[str, object]],
) -> tuple[dict[str, object], str, str]:
    value: dict[str, object] = {
        "format": CRDT_FORMAT,
        "nodes": [nodes[element_id] for element_id in sorted(nodes)],
    }
    canonical = _canonical(value)
    return value, canonical, _hash(canonical)


def _public_snapshot(nodes: dict[str, dict[str, object]]) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    for element_id in sorted(nodes):
        node = dict(nodes[element_id])
        if node["deleted"]:
            node["value"] = ""
        rows.append(node)
    return {"format": CRDT_FORMAT, "nodes": rows}


def _normalise_operations(raw: object) -> list[dict[str, object]]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_UPDATE_OPERATIONS:
        raise _error(422, f"ops must contain 1 to {MAX_UPDATE_OPERATIONS} operations")
    operations: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise _error(422, "Invalid CRDT operation")
        kind = str(item.get("type") or "").strip().lower()
        element_id = _identifier(item.get("id"), "element id")
        if kind == "delete":
            operations.append({"type": "delete", "id": element_id})
            continue
        if kind != "insert":
            raise _error(422, "CRDT operations support insert and delete only")
        after = str(item.get("after") or "").strip()
        if after != ROOT_ELEMENT_ID:
            after = _identifier(after, "predecessor")
        value = item.get("value")
        clock = item.get("clock")
        if (
            not isinstance(value, str)
            or len(value) != 1
            or value == "\x00"
            or _has_invalid_unicode(value)
        ):
            raise _error(422, "Each insert must contain one Unicode character")
        if (
            not isinstance(clock, int)
            or isinstance(clock, bool)
            or not 1 <= clock <= MAX_CLOCK
        ):
            raise _error(422, "Invalid CRDT clock")
        operations.append(
            {
                "type": "insert",
                "id": element_id,
                "after": after,
                "value": value,
                "clock": clock,
            }
        )
    return operations


def _apply_operations(
    nodes: dict[str, dict[str, object]], operations: list[dict[str, object]]
) -> tuple[dict[str, dict[str, object]], str, bool]:
    next_nodes = {element_id: dict(node) for element_id, node in nodes.items()}
    changed = False
    current_max_clock = max(
        (int(node["clock"]) for node in next_nodes.values()), default=0
    )
    insert_count = sum(operation["type"] == "insert" for operation in operations)
    maximum_new_clock = current_max_clock + insert_count
    for operation in operations:
        element_id = str(operation["id"])
        if operation["type"] == "insert":
            if element_id in next_nodes:
                raise _error(409, "CRDT element id already exists")
            predecessor = str(operation["after"])
            if predecessor != ROOT_ELEMENT_ID and predecessor not in next_nodes:
                raise _error(409, "CRDT predecessor does not exist")
            if int(operation["clock"]) > maximum_new_clock:
                raise _error(409, "CRDT clock exceeds this update window")
            next_nodes[element_id] = {
                "id": element_id,
                "after": predecessor,
                "value": operation["value"],
                "clock": operation["clock"],
                "deleted": False,
            }
            changed = True
        else:
            if element_id not in next_nodes:
                raise _error(409, "CRDT deletion target does not exist")
            if not next_nodes[element_id]["deleted"]:
                next_nodes[element_id]["deleted"] = True
                changed = True
    if len(next_nodes) > MAX_NODES:
        raise _error(413, "Collaboration document node limit reached")
    content = _render(next_nodes)
    if len(content) > MAX_VISIBLE_CHARACTERS:
        raise _error(
            413,
            f"Collaboration document is limited to {MAX_VISIBLE_CHARACTERS} characters",
        )
    return next_nodes, content, changed


def _verified_state(
    session: Session, document: dict[str, object]
) -> tuple[dict[str, dict[str, object]], str]:
    if (
        document.get("document_key") != DOCUMENT_KEY
        or document.get("crdt_format") != CRDT_FORMAT
        or document.get("state") not in DOCUMENT_STATES
    ):
        raise _error(500, "Unsupported collaboration document format")
    nodes = _snapshot_nodes(document.get("snapshot"))
    _, _, calculated_hash = _snapshot(nodes)
    content = _render(nodes)
    if (
        document.get("snapshot_hash") != calculated_hash
        or int(document.get("visible_length") or 0) != len(content)
        or int(document.get("node_count") or 0) != len(nodes)
    ):
        raise _error(500, "Collaboration document integrity check failed")
    sequence = int(document.get("latest_sequence") or 0)
    latest = (
        session.execute(
            text(
                """
                SELECT sequence, update_payload, update_hash
                FROM workflow.task_collaboration_document_updates
                WHERE document_id = :document_id
                ORDER BY sequence DESC LIMIT 1
                """
            ),
            {"document_id": document["id"]},
        )
        .mappings()
        .one_or_none()
    )
    if sequence == 0 and latest is not None:
        raise _error(500, "Collaboration document integrity check failed")
    if sequence > 0 and (
        latest is None
        or int(latest["sequence"]) != sequence
        or _hash(_canonical(latest["update_payload"])) != latest["update_hash"]
    ):
        raise _error(500, "Collaboration document integrity check failed")
    checkpoint_sequence = sequence if sequence % SNAPSHOT_INTERVAL == 0 else 0
    checkpoint = (
        session.execute(
            text(
                """
                SELECT snapshot, snapshot_hash, visible_length, node_count
                FROM workflow.task_collaboration_document_snapshots
                WHERE document_id = :document_id AND sequence = :sequence
                """
            ),
            {"document_id": document["id"], "sequence": checkpoint_sequence},
        )
        .mappings()
        .one_or_none()
    )
    if checkpoint is None or (
        _hash(_canonical(checkpoint["snapshot"])) != checkpoint["snapshot_hash"]
    ):
        raise _error(500, "Collaboration document integrity check failed")
    if checkpoint_sequence == sequence and (
        checkpoint["snapshot_hash"] != calculated_hash
        or int(checkpoint["visible_length"]) != len(content)
        or int(checkpoint["node_count"]) != len(nodes)
    ):
        raise _error(500, "Collaboration document integrity check failed")
    return nodes, content


def _capabilities(
    task: dict[str, object], member: dict[str, object], document: dict[str, object]
) -> dict[str, bool]:
    terminal = task["status"] in {"completed", "cancelled"}
    editable = bool(
        not terminal
        and document["state"] == "active"
        and member["role"] in EDITABLE_ROLES
    )
    return {
        "can_read": True,
        "can_edit": editable,
        "can_export": True,
        "can_manage": bool(not terminal and member["role"] in {"owner", "coordinator"}),
        "read_only": not editable,
    }


def _asset_view(row: dict[str, object]) -> dict[str, object]:
    return {
        "asset_key": str(row["asset_key"]),
        "file_name": row["file_name"],
        "alt_text": row.get("alt_text") or "",
        "mime_type": row["mime_type"],
        "byte_size": int(row["byte_size"]),
        "width": int(row["width"]),
        "height": int(row["height"]),
        "sha256": row["sha256"],
        "created_by_user_id": str(row["created_by_user_id"]),
        "created_by_name": row.get("creator_name") or row.get("creator_username"),
        "created_at": row["created_at"],
    }


def _assets(session: Session, document_id: UUID) -> list[dict[str, object]]:
    rows = session.execute(
        text(
            """
            SELECT a.*, u.username AS creator_username, u.display_name AS creator_name
            FROM workflow.task_collaboration_document_assets AS a
            JOIN iam.users AS u ON u.id = a.created_by_user_id
            WHERE a.document_id = :document_id ORDER BY a.created_at, a.id
            """
        ),
        {"document_id": document_id},
    ).mappings()
    return [_asset_view(dict(row)) for row in rows]


def _document_view(
    session: Session,
    task: dict[str, object],
    member: dict[str, object],
    document: dict[str, object],
    verified: tuple[dict[str, dict[str, object]], str] | None = None,
) -> dict[str, object]:
    nodes, content = verified or _verified_state(session, document)
    public_snapshot = _public_snapshot(nodes)
    return {
        "document": {
            "id": str(document["id"]),
            "task_id": str(task["id"]),
            "title": document["title"],
            "format": document["crdt_format"],
            "state": document["state"],
            "latest_sequence": int(document["latest_sequence"]),
            "snapshot_hash": _hash(_canonical(public_snapshot)),
            "visible_length": int(document["visible_length"]),
            "node_count": int(document["node_count"]),
            "created_by_user_id": str(document["created_by_user_id"]),
            "created_by_name": document.get("creator_name") or document.get("creator_username"),
            "updated_by_user_id": str(document["updated_by_user_id"]),
            "updated_by_name": document.get("updater_name") or document.get("updater_username"),
            "created_at": document["created_at"],
            "updated_at": document["updated_at"],
        },
        "snapshot": public_snapshot,
        "content": content,
        "assets": _assets(session, UUID(str(document["id"]))),
        "capabilities": _capabilities(task, member, document),
    }


def get_document(actor: ActorContext, task_id: str) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        document = _ensure_document(session, actor, space)
        return _document_view(session, task, member, document)


def append_update_in_session(
    session: Session,
    actor: ActorContext,
    task: dict[str, object],
    space: dict[str, object],
    member: dict[str, object],
    document: dict[str, object],
    *,
    client_id: str,
    client_update_id: str,
    operations: list[dict[str, object]],
) -> dict[str, object]:
    update_value = {"format": CRDT_FORMAT, "ops": operations}
    update_json = _canonical(update_value)
    update_bytes = len(update_json.encode("utf-8"))
    if update_bytes > MAX_UPDATE_BYTES:
        raise _error(413, "Collaboration update is too large")
    update_hash = _hash(update_json)
    existing = (
        session.execute(
            text(
                """
                SELECT sequence, client_id, update_payload, update_hash
                FROM workflow.task_collaboration_document_updates
                WHERE document_id = :document_id
                  AND actor_user_id = :actor_user_id
                  AND client_update_id = :client_update_id
                """
            ),
            {
                "document_id": document["id"],
                "actor_user_id": actor.user_id,
                "client_update_id": client_update_id,
            },
        )
        .mappings()
        .one_or_none()
    )
    if existing is not None:
        if existing["client_id"] != client_id or existing["update_hash"] != update_hash:
            raise _error(409, "client_update_id was already used for another update")
        response = _document_view(session, task, member, document)
        return response | {
            "result": "idempotent",
            "idempotent": True,
            "accepted_sequence": int(existing["sequence"]),
        }
    _writable(task)
    if member["role"] not in EDITABLE_ROLES:
        raise _error(403, "Observer membership cannot edit the collaboration document")
    if document["state"] != "active":
        raise _error(409, "Collaboration document is read-only")
    nodes, _ = _verified_state(session, document)
    next_nodes, content, changed = _apply_operations(nodes, operations)
    previous_sequence = int(document["latest_sequence"])
    if not changed:
        response = _document_view(
            session, task, member, document, verified=(nodes, content)
        )
        return response | {
            "result": "converged_noop",
            "idempotent": True,
            "accepted_sequence": previous_sequence,
        }
    if previous_sequence >= MAX_UPDATES_PER_DOCUMENT:
        raise _error(409, "Collaboration document update limit reached; export and archive it")
    _, snapshot_json, snapshot_hash = _snapshot(next_nodes)
    sequence = previous_sequence + 1
    session.execute(
        text(
            """
            INSERT INTO workflow.task_collaboration_document_updates(
              tenant_id, document_id, sequence, actor_user_id, client_id,
              client_update_id, update_payload, update_hash, byte_size
            ) VALUES (
              :tenant_id, :document_id, :sequence, :actor_user_id, :client_id,
              :client_update_id, CAST(:update AS jsonb), :update_hash, :byte_size
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "document_id": document["id"],
            "sequence": sequence,
            "actor_user_id": actor.user_id,
            "client_id": client_id,
            "client_update_id": client_update_id,
            "update": update_json,
            "update_hash": update_hash,
            "byte_size": update_bytes,
        },
    )
    session.execute(
        text(
            """
            UPDATE workflow.task_collaboration_documents
            SET latest_sequence = :sequence, snapshot = CAST(:snapshot AS jsonb),
                snapshot_hash = :snapshot_hash, visible_length = :visible_length,
                node_count = :node_count, updated_by_user_id = :user_id
            WHERE id = :document_id
            """
        ),
        {
            "sequence": sequence,
            "snapshot": snapshot_json,
            "snapshot_hash": snapshot_hash,
            "visible_length": len(content),
            "node_count": len(next_nodes),
            "user_id": actor.user_id,
            "document_id": document["id"],
        },
    )
    if sequence % SNAPSHOT_INTERVAL == 0:
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_document_snapshots(
                  tenant_id, document_id, sequence, snapshot, snapshot_hash,
                  visible_length, node_count, created_by_user_id
                ) VALUES (
                  :tenant_id, :document_id, :sequence, CAST(:snapshot AS jsonb),
                  :snapshot_hash, :visible_length, :node_count, :user_id
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "document_id": document["id"],
                "sequence": sequence,
                "snapshot": snapshot_json,
                "snapshot_hash": snapshot_hash,
                "visible_length": len(content),
                "node_count": len(next_nodes),
                "user_id": actor.user_id,
            },
        )
    _event(
        session,
        actor,
        space,
        "document_updated",
        subject_user_id=actor.user_id,
        payload={"document_id": str(document["id"]), "sequence": sequence},
    )
    document = _document_row(session, UUID(str(space["id"])))
    assert document is not None
    response = _document_view(
        session, task, member, document, verified=(next_nodes, content)
    )
    return response | {
        "result": "updated",
        "idempotent": False,
        "accepted_sequence": sequence,
    }


def append_update(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    client_id = _identifier(payload.get("client_id"), "client_id")
    client_update_id = _identifier(payload.get("client_update_id"), "client_update_id")
    operations = _normalise_operations(payload.get("ops"))
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        document = _ensure_document(session, actor, space, lock=True)
        return append_update_in_session(
            session,
            actor,
            task,
            space,
            member,
            document,
            client_id=client_id,
            client_update_id=client_update_id,
            operations=operations,
        )


def export_document(actor: ActorContext, task_id: str) -> dict[str, object]:
    response = get_document(actor, task_id)
    document = dict(response["document"])
    content = str(response.get("content") or "")
    return {
        "document_id": document["id"],
        "task_id": document["task_id"],
        "sequence": document["latest_sequence"],
        "snapshot_hash": document["snapshot_hash"],
        "content_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "content_type": "text/markdown; charset=utf-8",
        "filename": f"task-{document['task_id']}-working-draft.md",
        "content": content,
        "created_at": document["updated_at"],
    }


def register_image(
    actor: ActorContext,
    task_id: str,
    *,
    data: bytes,
    file_name: str,
    alt_text: str,
    mime_type: str,
    width: int,
    height: int,
    settings: Settings,
) -> dict[str, object]:
    if not data or len(data) > MAX_IMAGE_ASSET_BYTES:
        raise _error(413, "Image must be between 1 byte and 2 MB")
    if mime_type not in IMAGE_ASSET_MIME_TYPES:
        raise _error(415, "Only PNG, JPEG and WebP images are supported")
    if not 1 <= width <= MAX_IMAGE_ASSET_DIMENSION or not 1 <= height <= MAX_IMAGE_ASSET_DIMENSION:
        raise _error(413, "Image dimensions are limited to 2048 pixels")
    clean_name = Path(str(file_name or "image").replace("\\", "/")).name.strip()
    if (
        not clean_name
        or len(clean_name) > 255
        or any(ord(character) < 32 or ord(character) == 127 for character in clean_name)
    ):
        raise _error(422, "Invalid image filename")
    clean_alt = str(alt_text or "").strip()
    if len(clean_alt) > 160 or any(
        ord(character) < 32 or ord(character) == 127 for character in clean_alt
    ):
        raise _error(422, "Invalid image alternative text")
    checksum = hashlib.sha256(data).hexdigest()
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        task, space, member = _context(session, actor, target_id)
        _writable(task)
        if member["role"] not in EDITABLE_ROLES:
            raise _error(403, "Observer membership cannot upload collaboration images")
        document = _ensure_document(session, actor, space, lock=True)
        if document["state"] != "active":
            raise _error(409, "Collaboration document is read-only")
        _verified_state(session, document)
        existing = (
            session.execute(
                text(
                    """
                    SELECT a.*, u.username AS creator_username,
                           u.display_name AS creator_name
                    FROM workflow.task_collaboration_document_assets AS a
                    JOIN iam.users AS u ON u.id = a.created_by_user_id
                    WHERE a.document_id = :document_id AND a.sha256 = :sha256
                    """
                ),
                {"document_id": document["id"], "sha256": checksum},
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            return {
                "asset": _asset_view(dict(existing)),
                "result": "deduplicated",
                "deduplicated": True,
            }
        quota = session.execute(
            text(
                """
                SELECT count(*) AS asset_count, coalesce(sum(byte_size), 0) AS total_bytes
                FROM workflow.task_collaboration_document_assets
                WHERE document_id = :document_id
                """
            ),
            {"document_id": document["id"]},
        ).mappings().one()
        if int(quota["asset_count"]) >= MAX_IMAGE_ASSETS_PER_DOCUMENT:
            raise _error(413, "Each collaboration document supports up to 50 images")
        if int(quota["total_bytes"]) + len(data) > MAX_IMAGE_ASSET_BYTES_PER_DOCUMENT:
            raise _error(413, "Collaboration document images are limited to 32 MB in total")
        store = LocalContentAddressedObjectStore(settings.asset_storage_root)
        stored = store.put_stream(
            tenant_id=actor.tenant_id,
            stream=io.BytesIO(data),
            max_bytes=MAX_IMAGE_ASSET_BYTES,
            expected_sha256=checksum,
        )
        asset_key = "img_" + secrets.token_urlsafe(24)
        asset_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_document_assets(
                  id, tenant_id, document_id, asset_key, storage_provider, object_key,
                  file_name, alt_text, mime_type, byte_size, width, height, sha256,
                  created_by_user_id
                ) VALUES (
                  :id, :tenant_id, :document_id, :asset_key, :storage_provider,
                  :object_key, :file_name, :alt_text, :mime_type, :byte_size,
                  :width, :height, :sha256, :user_id
                )
                """
            ),
            {
                "id": asset_id,
                "tenant_id": actor.tenant_id,
                "document_id": document["id"],
                "asset_key": asset_key,
                "storage_provider": stored.provider_key,
                "object_key": stored.object_key,
                "file_name": clean_name,
                "alt_text": clean_alt,
                "mime_type": mime_type,
                "byte_size": stored.size_bytes,
                "width": width,
                "height": height,
                "sha256": stored.sha256,
                "user_id": actor.user_id,
            },
        )
        _event(
            session,
            actor,
            space,
            "document_asset_created",
            subject_user_id=actor.user_id,
            payload={"document_id": str(document["id"]), "asset_key": asset_key},
        )
        created = session.execute(
            text(
                """
                SELECT a.*, u.username AS creator_username,
                       u.display_name AS creator_name
                FROM workflow.task_collaboration_document_assets AS a
                JOIN iam.users AS u ON u.id = a.created_by_user_id
                WHERE a.id = :asset_id
                """
            ),
            {"asset_id": asset_id},
        ).mappings().one()
        return {
            "asset": _asset_view(dict(created)),
            "result": "created",
            "deduplicated": False,
        }


def image_descriptor(
    actor: ActorContext, task_id: str, asset_key: str, settings: Settings
) -> dict[str, object]:
    if not _ASSET_KEY_RE.fullmatch(str(asset_key or "")):
        raise _error(404, "Collaboration image not found")
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        _, space, _ = _context(session, actor, target_id)
        document = _document_row(session, UUID(str(space["id"])))
        if document is None:
            raise _error(404, "Collaboration image not found")
        row = (
            session.execute(
                text(
                    """
                    SELECT * FROM workflow.task_collaboration_document_assets
                    WHERE document_id = :document_id AND asset_key = :asset_key
                    """
                ),
                {"document_id": document["id"], "asset_key": asset_key},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise _error(404, "Collaboration image not found")
        descriptor = dict(row)
    if descriptor["storage_provider"] != LocalContentAddressedObjectStore.provider_key:
        raise _error(409, "Collaboration image uses an unsupported storage provider")
    store = LocalContentAddressedObjectStore(settings.asset_storage_root)
    path = store.path_for(str(descriptor["object_key"]))
    if not path.is_file() or path.stat().st_size != int(descriptor["byte_size"]):
        raise _error(404, "Collaboration image object is unavailable")
    with path.open("rb") as source:
        checksum = hashlib.sha256(source.read()).hexdigest()
    if checksum != descriptor["sha256"]:
        raise _error(500, "Collaboration image integrity check failed")
    return {
        "path": path,
        "filename": descriptor["file_name"],
        "mime_type": descriptor["mime_type"],
        "sha256": descriptor["sha256"],
    }


__all__ = [
    "IMAGE_ASSET_MIME_TYPES",
    "MAX_IMAGE_ASSET_BYTES",
    "MAX_IMAGE_ASSET_DIMENSION",
    "_apply_operations",
    "_normalise_operations",
    "_public_snapshot",
    "_snapshot",
    "_snapshot_nodes",
    "append_update",
    "append_update_in_session",
    "export_document",
    "get_document",
    "image_descriptor",
    "register_image",
]
