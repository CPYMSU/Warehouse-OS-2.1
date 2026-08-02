"""PostgreSQL-backed AI secretary conversation history.

The database is the source of truth. Browser storage is deliberately not used
for transcripts, which keeps devices in sync and preserves tenant isolation.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.runtime_output import public_message

if TYPE_CHECKING:
    from app.api.deps import ActorContext

_DEFAULT_TITLES = {"new conversation", "新對話", "新对话"}
_VALID_ROLES = {"user", "assistant", "system", "tool"}


def _safe_uuid(value: object) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc


def _compact_title(value: object, *, fallback: str = "新對話") -> str:
    compact = re.sub(r"\s+", " ", str(value or "")).strip()
    if not compact:
        return fallback
    return compact[:79] + ("…" if len(compact) > 80 else "")


def _message_locale(metadata: dict[str, object]) -> str:
    direct = str(metadata.get("response_locale") or "").strip()
    if direct:
        return direct
    language = metadata.get("language")
    language = language if isinstance(language, dict) else {}
    return str(language.get("locale") or "zh-Hant")


def _message_payload(row: dict[str, object]) -> dict[str, object]:
    metadata = dict(row.get("metadata") or {})
    role = str(row["role"])
    content = str(row["content"])
    if role != "user":
        filtered = public_message(
            content,
            locale=_message_locale(metadata),
        )
        if filtered != content:
            metadata["public_output_filtered"] = True
        content = filtered
    return {
        "id": str(row["id"]),
        "sequence": int(row["sequence"]),
        "conversation_id": str(row["conversation_id"]),
        "turn_id": row.get("turn_id"),
        "role": role,
        "content": content,
        "metadata": metadata,
        "created_at": row["created_at"].isoformat(),
    }


def _conversation_payload(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "owner_user_id": str(row["owner_user_id"]),
        "channel": row["channel"],
        "title": row["title"],
        "status": row["status"],
        "summary": row.get("summary"),
        "message_count": int(row.get("message_count") or 0),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "last_message_at": (
            row["last_message_at"].isoformat() if row.get("last_message_at") else None
        ),
    }


def _owned_conversation(
    session: object,
    actor: ActorContext,
    conversation_id: UUID,
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT c.*,
                       (SELECT count(*) FROM secretariat.messages m
                        WHERE m.conversation_id = c.id) AS message_count
                FROM secretariat.conversations c
                WHERE c.id = :id
                  AND c.owner_user_id = :owner_user_id
                  AND c.status = 'active'
                LIMIT 1
                """
            ),
            {"id": conversation_id, "owner_user_id": actor.user_id},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def create_conversation(
    actor: ActorContext,
    *,
    title: object = None,
    channel: object = "assistant",
) -> dict[str, object]:
    conversation_id = uuid4()
    normalized_channel = re.sub(r"[^a-z0-9_-]", "", str(channel or "").lower())[:64]
    if not normalized_channel:
        normalized_channel = "assistant"
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO secretariat.conversations(
                      id, tenant_id, owner_user_id, channel, title,
                      status, last_message_at
                    ) VALUES (
                      :id, :tenant_id, :owner_user_id, :channel, :title,
                      'active', now()
                    )
                    RETURNING *, 0::bigint AS message_count
                    """
                ),
                {
                    "id": conversation_id,
                    "tenant_id": actor.tenant_id,
                    "owner_user_id": actor.user_id,
                    "channel": normalized_channel,
                    "title": _compact_title(title),
                },
            )
            .mappings()
            .one()
        )
    return _conversation_payload(dict(row))


def ensure_conversation(
    actor: ActorContext,
    *,
    conversation_id: object = None,
    seed_text: object = None,
    channel: object = "assistant",
) -> dict[str, object]:
    if conversation_id not in (None, ""):
        parsed_id = _safe_uuid(conversation_id)
        with tenant_session(actor.tenant_id) as session:
            row = _owned_conversation(session, actor, parsed_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Conversation is unavailable, archived, or belongs to "
                    "another account"
                ),
            )
        return _conversation_payload(row)
    return create_conversation(
        actor,
        title=_compact_title(seed_text),
        channel=channel,
    )


def list_conversations(
    actor: ActorContext,
    *,
    limit: int = 100,
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT c.*,
                           (SELECT count(*) FROM secretariat.messages m
                            WHERE m.conversation_id = c.id) AS message_count
                    FROM secretariat.conversations c
                    WHERE c.owner_user_id = :owner_user_id
                      AND c.status = 'active'
                    ORDER BY c.last_message_at DESC NULLS LAST,
                             c.updated_at DESC, c.id DESC
                    LIMIT :limit
                    """
                ),
                {
                    "owner_user_id": actor.user_id,
                    "limit": max(1, min(int(limit), 500)),
                },
            )
            .mappings()
            .all()
        )
    return [_conversation_payload(dict(row)) for row in rows]


def load_conversation(
    actor: ActorContext,
    *,
    conversation_id: object = None,
    message_limit: int = 80,
    before_sequence: int | None = None,
) -> dict[str, object]:
    limit = max(1, min(int(message_limit), 500))
    with tenant_session(actor.tenant_id) as session:
        if conversation_id not in (None, ""):
            conversation = _owned_conversation(
                session, actor, _safe_uuid(conversation_id)
            )
        else:
            row = (
                session.execute(
                    text(
                        """
                        SELECT c.*,
                               (SELECT count(*) FROM secretariat.messages m
                                WHERE m.conversation_id = c.id) AS message_count
                        FROM secretariat.conversations c
                        WHERE c.owner_user_id = :owner_user_id
                          AND c.status = 'active'
                        ORDER BY c.last_message_at DESC NULLS LAST,
                                 c.updated_at DESC, c.id DESC
                        LIMIT 1
                        """
                    ),
                    {"owner_user_id": actor.user_id},
                )
                .mappings()
                .one_or_none()
            )
            conversation = dict(row) if row else None
        if conversation is None:
            if conversation_id not in (None, ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found",
                )
            return {
                "conversation": None,
                "messages": [],
                "history": {"has_more": False, "oldest_sequence": None},
            }

        rows = (
            session.execute(
                text(
                    """
                    SELECT id, sequence, conversation_id, turn_id, role,
                           content, metadata, created_at
                    FROM secretariat.messages
                    WHERE conversation_id = :conversation_id
                      AND (
                        CAST(:before_sequence AS bigint) IS NULL
                        OR sequence < CAST(:before_sequence AS bigint)
                      )
                    ORDER BY sequence DESC
                    LIMIT :limit
                    """
                ),
                {
                    "conversation_id": conversation["id"],
                    "before_sequence": before_sequence,
                    "limit": limit + 1,
                },
            )
            .mappings()
            .all()
        )
    has_more = len(rows) > limit
    selected = list(rows[:limit])
    selected.reverse()
    messages = [_message_payload(dict(row)) for row in selected]
    return {
        "conversation": _conversation_payload(conversation),
        "messages": messages,
        "history": {
            "has_more": has_more,
            "oldest_sequence": messages[0]["sequence"] if messages else None,
        },
    }


def append_message(
    actor: ActorContext,
    *,
    conversation_id: object,
    role: str,
    content: object,
    turn_id: object = None,
    metadata: dict[str, object] | None = None,
) -> tuple[dict[str, object], bool]:
    normalized_role = str(role or "").strip().lower()
    normalized_content = str(content or "").strip()
    normalized_metadata = dict(metadata or {})
    normalized_turn_id = str(turn_id or "").strip()[:128] or None
    if normalized_role not in _VALID_ROLES:
        raise ValueError("Unsupported conversation role")
    if not normalized_content:
        raise ValueError("Conversation message cannot be empty")
    if normalized_role != "user":
        filtered_content = public_message(
            normalized_content,
            locale=_message_locale(normalized_metadata),
        )
        if filtered_content != normalized_content:
            normalized_metadata["public_output_filtered"] = True
        normalized_content = filtered_content
    if len(normalized_content) > 100_000:
        normalized_content = normalized_content[:100_000]
    parsed_id = _safe_uuid(conversation_id)
    serialized_metadata = json.dumps(
        normalized_metadata,
        ensure_ascii=False,
        default=str,
    )
    with tenant_session(actor.tenant_id) as session:
        conversation = _owned_conversation(session, actor, parsed_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation is no longer available",
            )
        message_id = uuid4()
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO secretariat.messages(
                      id, tenant_id, conversation_id, turn_id, role,
                      content, metadata
                    ) VALUES (
                      :id, :tenant_id, :conversation_id, :turn_id, :role,
                      :content, CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT (
                      tenant_id, conversation_id, turn_id, role
                    ) DO NOTHING
                    RETURNING id, sequence, conversation_id, turn_id, role,
                              content, metadata, created_at
                    """
                ),
                {
                    "id": message_id,
                    "tenant_id": actor.tenant_id,
                    "conversation_id": parsed_id,
                    "turn_id": normalized_turn_id,
                    "role": normalized_role,
                    "content": normalized_content,
                    "metadata": serialized_metadata,
                },
            )
            .mappings()
            .one_or_none()
        )
        inserted = row is not None
        if row is None:
            row = (
                session.execute(
                    text(
                        """
                        SELECT id, sequence, conversation_id, turn_id, role,
                               content, metadata, created_at
                        FROM secretariat.messages
                        WHERE conversation_id = :conversation_id
                          AND turn_id = :turn_id AND role = :role
                        """
                    ),
                    {
                        "conversation_id": parsed_id,
                        "turn_id": normalized_turn_id,
                        "role": normalized_role,
                    },
                )
                .mappings()
                .one()
            )
        next_title = conversation["title"]
        if (
            normalized_role == "user"
            and str(next_title or "").strip().lower() in _DEFAULT_TITLES
        ):
            next_title = _compact_title(normalized_content)
        session.execute(
            text(
                """
                UPDATE secretariat.conversations
                SET title = :title, last_message_at = now()
                WHERE id = :conversation_id
                """
            ),
            {"title": next_title, "conversation_id": parsed_id},
        )
    message = _message_payload(dict(row))
    if inserted:
        # Import locally so the immutable transcript remains independent from
        # optional derived-memory processing.
        from app.services.memory_fabric import enqueue_conversation_distillation

        enqueue_conversation_distillation(
            actor,
            conversation_id=parsed_id,
            source_cursor=int(message["sequence"]),
        )
    return message, inserted


def messages_for_turn(
    actor: ActorContext,
    *,
    conversation_id: object,
    turn_id: object,
) -> list[dict[str, object]]:
    parsed_id = _safe_uuid(conversation_id)
    normalized_turn_id = str(turn_id or "").strip()[:128]
    if not normalized_turn_id:
        return []
    with tenant_session(actor.tenant_id) as session:
        if _owned_conversation(session, actor, parsed_id) is None:
            return []
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, sequence, conversation_id, turn_id, role,
                           content, metadata, created_at
                    FROM secretariat.messages
                    WHERE conversation_id = :conversation_id
                      AND turn_id = :turn_id
                    ORDER BY sequence
                    """
                ),
                {
                    "conversation_id": parsed_id,
                    "turn_id": normalized_turn_id,
                },
            )
            .mappings()
            .all()
        )
    return [_message_payload(dict(row)) for row in rows]


def recent_conversation_context(
    actor: ActorContext,
    conversation_id: object,
    *,
    limit: int = 24,
    character_budget: int = 24_000,
) -> dict[str, object]:
    loaded = load_conversation(
        actor,
        conversation_id=conversation_id,
        message_limit=max(1, min(limit, 40)),
    )
    selected: list[dict[str, object]] = []
    remaining = max(1_000, min(int(character_budget), 40_000))
    for message in reversed(loaded["messages"]):
        content = str(message["content"])
        if len(content) > remaining and selected:
            break
        selected.append(
            {
                "role": message["role"],
                "content": content[:remaining],
                "created_at": message["created_at"],
            }
        )
        remaining -= min(len(content), remaining)
        if remaining <= 0:
            break
    selected.reverse()
    return {
        "trust": "conversation_transcript_data_not_authority",
        "conversation_id": loaded["conversation"]["id"],
        "title": loaded["conversation"]["title"],
        "messages": selected,
        "truncated": bool(loaded["history"]["has_more"]),
    }
