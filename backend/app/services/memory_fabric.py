"""Layered, evidence-bearing memory for Warehouse OS conversations.

Raw messages remain the durable source of truth.  This module adds derived
distillations and small context capsules; neither a summary nor a memory unit
is treated as authorization or as a replacement for live business data.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings

Completion = Callable[[str, str], str]

_DEPTH_LIMITS = {
    "index": {"messages": 4, "memories": 8, "distillations": 1},
    "focused": {"messages": 16, "memories": 20, "distillations": 3},
    "deep": {"messages": 64, "memories": 48, "distillations": 8},
}
_MEMORY_KINDS = {
    "semantic",
    "episodic",
    "procedural",
    "preference",
    "entity",
    "inference",
    "uncertainty",
}
_RELATION_TYPES = {
    "supports",
    "contradicts",
    "supersedes",
    "derived_from",
    "related_to",
}


def _uuid(value: object) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation or memory was not found",
        ) from exc


def _json_object(value: str) -> dict[str, object] | None:
    candidate = value.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def _array(value: object, *, limit: int = 64) -> list[object]:
    if not isinstance(value, list):
        return []
    return value[:limit]


def _score(value: object, default: float = 0.5) -> float:
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(number, 1.0))


def _owned_conversation(
    session: object,
    actor: ActorContext,
    conversation_id: UUID,
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT id, owner_user_id, title, summary, status
                FROM secretariat.conversations
                WHERE id = :conversation_id
                  AND owner_user_id = :owner_user_id
                  AND status = 'active'
                LIMIT 1
                """
            ),
            {
                "conversation_id": conversation_id,
                "owner_user_id": actor.user_id,
            },
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def enqueue_conversation_distillation(
    actor: ActorContext,
    *,
    conversation_id: object,
    source_cursor: int,
    requested_level: int = 2,
) -> str:
    """Coalesce new transcript evidence into one durable steward job."""
    parsed_id = _uuid(conversation_id)
    with tenant_session(actor.tenant_id) as session:
        if _owned_conversation(session, actor, parsed_id) is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        job_id = uuid4()
        stored_id = session.execute(
            text(
                """
                INSERT INTO secretariat.memory_jobs(
                  id, tenant_id, owner_user_id, conversation_id,
                  job_type, status, requested_level, source_cursor
                ) VALUES (
                  :id, :tenant_id, :owner_user_id, :conversation_id,
                  'conversation_distill', 'pending', :requested_level,
                  :source_cursor
                )
                ON CONFLICT (
                  tenant_id, conversation_id, job_type
                ) WHERE status IN ('pending', 'running')
                DO UPDATE SET
                  source_cursor = GREATEST(
                    secretariat.memory_jobs.source_cursor,
                    EXCLUDED.source_cursor
                  ),
                  requested_level = GREATEST(
                    secretariat.memory_jobs.requested_level,
                    EXCLUDED.requested_level
                  ),
                  available_at = CASE
                    WHEN secretariat.memory_jobs.status = 'pending' THEN now()
                    ELSE secretariat.memory_jobs.available_at
                  END,
                  last_error = NULL
                RETURNING id
                """
            ),
            {
                "id": job_id,
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "conversation_id": parsed_id,
                "requested_level": max(1, min(int(requested_level), 9)),
                "source_cursor": max(0, int(source_cursor)),
            },
        ).scalar_one()
    return str(stored_id)


def _claim_job(actor: ActorContext) -> dict[str, object] | None:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, conversation_id, source_cursor,
                           requested_level, attempts
                    FROM secretariat.memory_jobs
                    WHERE owner_user_id = :owner_user_id
                      AND (
                        (status = 'pending' AND available_at <= now())
                        OR (
                          status = 'running'
                          AND lease_until IS NOT NULL
                          AND lease_until < now()
                        )
                      )
                    ORDER BY available_at, created_at
                    FOR UPDATE SKIP LOCKED
                    LIMIT 1
                    """
                ),
                {"owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        session.execute(
            text(
                """
                UPDATE secretariat.memory_jobs
                SET status = 'running',
                    attempts = attempts + 1,
                    lease_until = now() + interval '2 minutes',
                    last_error = NULL
                WHERE id = :id
                """
            ),
            {"id": row["id"]},
        )
    claimed = dict(row)
    claimed["attempts"] = int(claimed["attempts"]) + 1
    return claimed


def _distillation_batch(
    actor: ActorContext,
    *,
    conversation_id: UUID,
    source_cursor: int,
) -> dict[str, object] | None:
    """Return only new evidence ending at a complete assistant turn."""
    with tenant_session(actor.tenant_id) as session:
        if _owned_conversation(session, actor, conversation_id) is None:
            return None
        checkpoint = int(
            session.execute(
                text(
                    """
                    SELECT COALESCE(max(source_sequence_end), 0)
                    FROM secretariat.conversation_distillations
                    WHERE conversation_id = :conversation_id
                    """
                ),
                {"conversation_id": conversation_id},
            ).scalar_one()
        )
        closing_sequence = session.execute(
            text(
                """
                SELECT max(sequence)
                FROM secretariat.messages
                WHERE conversation_id = :conversation_id
                  AND role = 'assistant'
                  AND sequence <= :source_cursor
                """
            ),
            {
                "conversation_id": conversation_id,
                "source_cursor": source_cursor,
            },
        ).scalar_one_or_none()
        if closing_sequence is None or int(closing_sequence) <= checkpoint:
            return None
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, sequence, role, content, metadata, created_at
                    FROM secretariat.messages
                    WHERE conversation_id = :conversation_id
                      AND sequence > :checkpoint
                      AND sequence <= :closing_sequence
                    ORDER BY sequence
                    LIMIT 120
                    """
                ),
                {
                    "conversation_id": conversation_id,
                    "checkpoint": checkpoint,
                    "closing_sequence": closing_sequence,
                },
            )
            .mappings()
            .all()
        )
        if not rows:
            return None
        # A capped batch still ends on an assistant message, so it never
        # distils half a turn.  Later evidence remains queued by source_cursor.
        last_assistant_index = max(
            (
                index
                for index, row in enumerate(rows)
                if str(row["role"]) == "assistant"
            ),
            default=-1,
        )
        if last_assistant_index < 0:
            return None
        selected = [dict(row) for row in rows[: last_assistant_index + 1]]
        previous = (
            session.execute(
                text(
                    """
                    SELECT summary, entities, facts, relations, inferences,
                           uncertainties, open_questions,
                           source_sequence_end, distillation_level
                    FROM secretariat.conversation_distillations
                    WHERE conversation_id = :conversation_id
                    ORDER BY source_sequence_end DESC,
                             distillation_level DESC, updated_at DESC
                    LIMIT 1
                    """
                ),
                {"conversation_id": conversation_id},
            )
            .mappings()
            .one_or_none()
        )
    evidence = [
        {
            "id": str(row["id"]),
            "sequence": int(row["sequence"]),
            "role": row["role"],
            "content": row["content"],
            "created_at": row["created_at"].isoformat(),
        }
        for row in selected
    ]
    source_hash = hashlib.sha256(
        json.dumps(evidence, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "messages": evidence,
        "source_sequence_start": evidence[0]["sequence"],
        "source_sequence_end": evidence[-1]["sequence"],
        "source_hash": source_hash,
        "previous": dict(previous) if previous else None,
    }


def _mark_job_deferred(actor: ActorContext, job_id: UUID) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE secretariat.memory_jobs
                SET status = 'pending', lease_until = NULL,
                    available_at = now() + interval '5 seconds'
                WHERE id = :id
                """
            ),
            {"id": job_id},
        )


def _mark_job_error(
    actor: ActorContext,
    job_id: UUID,
    *,
    attempts: int,
    error: str,
) -> None:
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE secretariat.memory_jobs
                SET status = CASE WHEN :attempts >= 3 THEN 'failed' ELSE 'pending' END,
                    lease_until = NULL,
                    available_at = now() + interval '30 seconds',
                    last_error = :last_error
                WHERE id = :id
                """
            ),
            {
                "id": job_id,
                "attempts": attempts,
                "last_error": error[:1000],
            },
        )


def _persist_distillation(
    actor: ActorContext,
    *,
    job: dict[str, object],
    batch: dict[str, object],
    distilled: dict[str, object],
    model: str,
) -> dict[str, object]:
    summary = str(distilled.get("summary") or "").strip()
    if not summary:
        raise ValueError("Memory Steward returned no durable summary")
    summary = summary[:100_000]
    conversation_id = _uuid(job["conversation_id"])
    start_sequence = int(batch["source_sequence_start"])
    end_sequence = int(batch["source_sequence_end"])
    source_messages = {
        int(item["sequence"]): item
        for item in batch["messages"]
        if isinstance(item, dict)
    }
    arrays = {
        "entities": _array(distilled.get("entities")),
        "facts": _array(distilled.get("facts")),
        "relations": _array(distilled.get("relations")),
        "inferences": _array(distilled.get("inferences")),
        "uncertainties": _array(distilled.get("uncertainties")),
        "open_questions": _array(distilled.get("open_questions")),
    }
    distillation_id = uuid4()
    memory_ids: list[UUID] = []
    with tenant_session(actor.tenant_id) as session:
        stored_distillation_id = session.execute(
            text(
                """
                INSERT INTO secretariat.conversation_distillations(
                  id, tenant_id, conversation_id, owner_user_id,
                  source_sequence_start, source_sequence_end, source_hash,
                  distillation_level, summary, entities, facts, relations,
                  inferences, uncertainties, open_questions, model
                ) VALUES (
                  :id, :tenant_id, :conversation_id, :owner_user_id,
                  :source_sequence_start, :source_sequence_end, :source_hash,
                  :distillation_level, :summary, CAST(:entities AS jsonb),
                  CAST(:facts AS jsonb), CAST(:relations AS jsonb),
                  CAST(:inferences AS jsonb), CAST(:uncertainties AS jsonb),
                  CAST(:open_questions AS jsonb), :model
                )
                ON CONFLICT (
                  tenant_id, conversation_id, source_sequence_end,
                  distillation_level, source_hash
                ) DO UPDATE SET
                  summary = EXCLUDED.summary,
                  entities = EXCLUDED.entities,
                  facts = EXCLUDED.facts,
                  relations = EXCLUDED.relations,
                  inferences = EXCLUDED.inferences,
                  uncertainties = EXCLUDED.uncertainties,
                  open_questions = EXCLUDED.open_questions,
                  model = EXCLUDED.model
                RETURNING id
                """
            ),
            {
                "id": distillation_id,
                "tenant_id": actor.tenant_id,
                "conversation_id": conversation_id,
                "owner_user_id": actor.user_id,
                "source_sequence_start": start_sequence,
                "source_sequence_end": end_sequence,
                "source_hash": batch["source_hash"],
                "distillation_level": max(
                    2, min(int(job.get("requested_level") or 2), 9)
                ),
                "summary": summary,
                **{
                    key: json.dumps(value, ensure_ascii=False, default=str)
                    for key, value in arrays.items()
                },
                "model": model[:256],
            },
        ).scalar_one()

        for item in _array(distilled.get("memories"), limit=24):
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or "").strip().lower()
            content = str(item.get("content") or "").strip()
            if kind not in _MEMORY_KINDS or not content:
                continue
            content = content[:100_000]
            evidence_sequences = {
                int(value)
                for value in _array(item.get("evidence_sequences"), limit=32)
                if str(value).isdigit() and int(value) in source_messages
            }
            if not evidence_sequences:
                evidence_sequences = set(source_messages)
            evidence = [
                {
                    "type": "conversation_message",
                    "conversation_id": str(conversation_id),
                    "message_id": str(source_messages[sequence]["id"]),
                    "sequence": sequence,
                }
                for sequence in sorted(evidence_sequences)
            ]
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            candidate_id = uuid4()
            stored_memory_id = session.execute(
                text(
                    """
                    INSERT INTO secretariat.memory_units(
                      id, tenant_id, owner_user_id, conversation_id,
                      kind, scope, content, content_sha256,
                      confidence, salience, source_sequence_start,
                      source_sequence_end, evidence, metadata
                    ) VALUES (
                      :id, :tenant_id, :owner_user_id, :conversation_id,
                      :kind, 'private', :content, :content_sha256,
                      :confidence, :salience, :source_sequence_start,
                      :source_sequence_end, CAST(:evidence AS jsonb),
                      CAST(:metadata AS jsonb)
                    )
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """
                ),
                {
                    "id": candidate_id,
                    "tenant_id": actor.tenant_id,
                    "owner_user_id": actor.user_id,
                    "conversation_id": conversation_id,
                    "kind": kind,
                    "content": content,
                    "content_sha256": digest,
                    "confidence": _score(item.get("confidence")),
                    "salience": _score(item.get("salience")),
                    "source_sequence_start": min(evidence_sequences),
                    "source_sequence_end": max(evidence_sequences),
                    "evidence": json.dumps(evidence, ensure_ascii=False),
                    "metadata": json.dumps(
                        {
                            "distilled_by": "memory_steward",
                            "distillation_id": str(stored_distillation_id),
                            "reason": item.get("reason"),
                            "memory_is_not_authority": True,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ).scalar_one_or_none()
            if stored_memory_id is None:
                stored_memory_id = session.execute(
                    text(
                        """
                        SELECT id
                        FROM secretariat.memory_units
                        WHERE owner_user_id = :owner_user_id
                          AND scope = 'private'
                          AND kind = :kind
                          AND content_sha256 = :content_sha256
                        LIMIT 1
                        """
                    ),
                    {
                        "owner_user_id": actor.user_id,
                        "kind": kind,
                        "content_sha256": digest,
                    },
                ).scalar_one()
            memory_ids.append(stored_memory_id)

        for relation in _array(distilled.get("memory_relations"), limit=48):
            if not isinstance(relation, dict):
                continue
            relation_type = str(relation.get("relation_type") or "").strip().lower()
            try:
                subject_index = int(relation.get("subject_index"))
                object_index = int(relation.get("object_index"))
                subject_id = memory_ids[subject_index]
                object_id = memory_ids[object_index]
            except (TypeError, ValueError, IndexError):
                continue
            if relation_type not in _RELATION_TYPES or subject_id == object_id:
                continue
            session.execute(
                text(
                    """
                    INSERT INTO secretariat.memory_relations(
                      id, tenant_id, subject_memory_id, object_memory_id,
                      relation_type, confidence, evidence
                    ) VALUES (
                      :id, :tenant_id, :subject_memory_id, :object_memory_id,
                      :relation_type, :confidence, CAST(:evidence AS jsonb)
                    )
                    ON CONFLICT (
                      tenant_id, subject_memory_id, object_memory_id, relation_type
                    ) DO UPDATE SET
                      confidence = GREATEST(
                        secretariat.memory_relations.confidence,
                        EXCLUDED.confidence
                      ),
                      evidence = EXCLUDED.evidence
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "subject_memory_id": subject_id,
                    "object_memory_id": object_id,
                    "relation_type": relation_type,
                    "confidence": _score(relation.get("confidence")),
                    "evidence": json.dumps(
                        [
                            {
                                "type": "conversation_distillation",
                                "id": str(stored_distillation_id),
                            }
                        ]
                    ),
                },
            )

        session.execute(
            text(
                """
                UPDATE secretariat.conversations
                SET summary = :summary
                WHERE id = :conversation_id
                  AND owner_user_id = :owner_user_id
                """
            ),
            {
                "summary": summary,
                "conversation_id": conversation_id,
                "owner_user_id": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                UPDATE secretariat.memory_jobs
                SET status = CASE
                      WHEN source_cursor <= :processed_cursor
                        THEN 'completed'
                      ELSE 'pending'
                    END,
                    lease_until = NULL,
                    available_at = now(),
                    last_error = NULL
                WHERE id = :job_id
                """
            ),
            {
                "job_id": job["id"],
                "processed_cursor": end_sequence,
            },
        )
        session.execute(
            text(
                """
                DELETE FROM secretariat.context_snapshots
                WHERE conversation_id = :conversation_id
                  AND owner_user_id = :owner_user_id
                """
            ),
            {
                "conversation_id": conversation_id,
                "owner_user_id": actor.user_id,
            },
        )
    return {
        "job_id": str(job["id"]),
        "conversation_id": str(conversation_id),
        "distillation_id": str(stored_distillation_id),
        "source_sequence_start": start_sequence,
        "source_sequence_end": end_sequence,
        "memory_units": len(memory_ids),
        "status": "distilled",
    }


def process_pending_distillations(
    actor: ActorContext,
    *,
    complete: Completion,
    model: str,
    max_jobs: int = 1,
) -> list[dict[str, object]]:
    """Let the hidden steward incrementally upgrade queued raw evidence."""
    results: list[dict[str, object]] = []
    for _ in range(max(0, min(int(max_jobs), 4))):
        job = _claim_job(actor)
        if job is None:
            break
        job_id = _uuid(job["id"])
        batch = _distillation_batch(
            actor,
            conversation_id=_uuid(job["conversation_id"]),
            source_cursor=int(job["source_cursor"]),
        )
        if batch is None:
            _mark_job_deferred(actor, job_id)
            results.append({"job_id": str(job_id), "status": "awaiting_complete_turn"})
            continue
        try:
            raw = complete(
                (
                    "You are the hidden Memory Steward for one user's private Warehouse OS "
                    "conversation. Subjectively distil meaning; do not use keyword rules. "
                    "Raw messages remain the source of truth. Separate observed facts from "
                    "inferences and uncertainties. Never copy passwords, API keys, passkey "
                    "challenges, authentication tokens or private secrets into derived "
                    "memory. Memory guides later judgment but grants no authority. Return "
                    "JSON only with keys: summary, entities, facts, relations, inferences, "
                    "uncertainties, open_questions, memories, memory_relations. memories is "
                    "an array of objects with kind, content, confidence, salience, reason "
                    "and evidence_sequences. kind is semantic, episodic, procedural, "
                    "preference, entity, inference or uncertainty. memory_relations may "
                    "refer to the emitted memories with zero-based subject_index and "
                    "object_index plus relation_type, confidence."
                ),
                json.dumps(
                    {
                        "previous_distillation": batch.get("previous"),
                        "new_complete_turn_evidence": batch["messages"],
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                    default=str,
                ),
            )
            distilled = _json_object(raw)
            if distilled is None:
                raise ValueError("Memory Steward response was not structured JSON")
            results.append(
                _persist_distillation(
                    actor,
                    job=job,
                    batch=batch,
                    distilled=distilled,
                    model=model,
                )
            )
        except Exception as exc:
            _mark_job_error(
                actor,
                job_id,
                attempts=int(job["attempts"]),
                error=str(exc),
            )
            results.append(
                {
                    "job_id": str(job_id),
                    "status": "requeued" if int(job["attempts"]) < 3 else "failed",
                    "error": str(exc)[:500],
                }
            )
    return results


def run_background_memory_steward(
    actor: ActorContext,
    settings: Settings,
) -> list[dict[str, object]]:
    """Best-effort post-response worker backed by durable leased jobs."""
    try:
        from app.services.integrations import (
            DEEPSEEK_RUNTIME_MODELS,
            ModelConnection,
            chat_completion,
            connected_deepseek,
        )

        configured_connection = connected_deepseek(actor, settings)
        connection = ModelConnection(
            base_url=configured_connection.base_url,
            model=DEEPSEEK_RUNTIME_MODELS["balanced"],
            api_key=configured_connection.api_key,
        )
        return process_pending_distillations(
            actor,
            complete=lambda system_prompt, user_prompt: chat_completion(
                connection,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                thinking=False,
                max_tokens=1_800,
                json_mode=True,
            ),
            model=connection.model,
            max_jobs=4,
        )
    except Exception:
        # The transcript and pending job are already durable. Foreground chat
        # must never fail because optional memory upkeep could not run.
        return []


def _source_cursor(
    session: object,
    *,
    actor: ActorContext,
    conversation_id: UUID,
) -> tuple[str, dict[str, int]]:
    row = (
        session.execute(
            text(
                """
                SELECT
                  COALESCE((
                    SELECT max(sequence) FROM secretariat.messages
                    WHERE conversation_id = :conversation_id
                  ), 0) AS message_cursor,
                  COALESCE((
                    SELECT max(source_sequence_end)
                    FROM secretariat.conversation_distillations
                    WHERE conversation_id = :conversation_id
                  ), 0) AS distillation_cursor,
                  COALESCE((
                    SELECT max(distillation_level)
                    FROM secretariat.conversation_distillations
                    WHERE conversation_id = :conversation_id
                  ), 0) AS distillation_level,
                  COALESCE((
                    SELECT count(*) FROM secretariat.memory_units
                    WHERE status = 'active'
                      AND (
                        (scope = 'private' AND owner_user_id = :owner_user_id)
                        OR scope = 'company'
                      )
                  ), 0) AS memory_count,
                  COALESCE((
                    SELECT extract(epoch FROM max(updated_at))::bigint
                    FROM secretariat.memory_units
                    WHERE status = 'active'
                      AND (
                        (scope = 'private' AND owner_user_id = :owner_user_id)
                        OR scope = 'company'
                      )
                  ), 0) AS memory_cursor
                """
            ),
            {
                "conversation_id": conversation_id,
                "owner_user_id": actor.user_id,
            },
        )
        .mappings()
        .one()
    )
    state = {key: int(value or 0) for key, value in dict(row).items()}
    digest = hashlib.sha256(
        json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return digest, state


def build_memory_capsule(
    actor: ActorContext,
    *,
    conversation_id: object,
    query: object = "",
    depth: str = "index",
) -> dict[str, object]:
    """Resolve a bounded, cached capsule without treating memory as truth."""
    normalized_depth = str(depth or "index").strip().lower()
    if normalized_depth not in _DEPTH_LIMITS:
        raise ValueError("Memory depth must be index, focused, or deep")
    parsed_id = _uuid(conversation_id)
    normalized_query = " ".join(str(query or "").split())[:16_384]
    query_hash = hashlib.sha256(normalized_query.encode("utf-8")).hexdigest()
    limits = _DEPTH_LIMITS[normalized_depth]

    with tenant_session(actor.tenant_id) as session:
        conversation = _owned_conversation(session, actor, parsed_id)
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )
        source_cursor, source_state = _source_cursor(
            session,
            actor=actor,
            conversation_id=parsed_id,
        )
        cached = session.execute(
            text(
                """
                SELECT payload
                FROM secretariat.context_snapshots
                WHERE owner_user_id = :owner_user_id
                  AND conversation_id = :conversation_id
                  AND query_hash = :query_hash
                  AND source_cursor = :source_cursor
                  AND memory_depth = :memory_depth
                  AND (expires_at IS NULL OR expires_at > now())
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "owner_user_id": actor.user_id,
                "conversation_id": parsed_id,
                "query_hash": query_hash,
                "source_cursor": source_cursor,
                "memory_depth": normalized_depth,
            },
        ).scalar_one_or_none()
        if isinstance(cached, dict):
            return {**cached, "cache": "hit"}

        message_rows = (
            session.execute(
                text(
                    """
                    SELECT id, sequence, role, content, created_at
                    FROM secretariat.messages
                    WHERE conversation_id = :conversation_id
                    ORDER BY sequence DESC
                    LIMIT :limit
                    """
                ),
                {
                    "conversation_id": parsed_id,
                    "limit": limits["messages"],
                },
            )
            .mappings()
            .all()
        )
        distillation_rows = (
            session.execute(
                text(
                    """
                    SELECT id, source_sequence_start, source_sequence_end,
                           distillation_level, summary, entities, facts,
                           relations, inferences, uncertainties,
                           open_questions, model, updated_at
                    FROM secretariat.conversation_distillations
                    WHERE conversation_id = :conversation_id
                      AND owner_user_id = :owner_user_id
                    ORDER BY source_sequence_end DESC,
                             distillation_level DESC, updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "conversation_id": parsed_id,
                    "owner_user_id": actor.user_id,
                    "limit": limits["distillations"],
                },
            )
            .mappings()
            .all()
        )
        memory_rows = (
            session.execute(
                text(
                    """
                    SELECT id, owner_user_id, conversation_id, kind, scope,
                           content, confidence, salience, status,
                           source_sequence_start, source_sequence_end,
                           evidence, metadata, valid_from, valid_to, updated_at
                    FROM secretariat.memory_units
                    WHERE status = 'active'
                      AND (valid_to IS NULL OR valid_to > now())
                      AND (
                        (scope = 'private' AND owner_user_id = :owner_user_id)
                        OR scope = 'company'
                      )
                    ORDER BY
                      CASE WHEN conversation_id = :conversation_id THEN 1 ELSE 0 END DESC,
                      (confidence * salience) DESC,
                      updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "owner_user_id": actor.user_id,
                    "conversation_id": parsed_id,
                    "limit": limits["memories"],
                },
            )
            .mappings()
            .all()
        )
        memory_ids = [str(row["id"]) for row in memory_rows]
        relation_rows = []
        if memory_ids:
            relation_rows = (
                session.execute(
                    text(
                        """
                        SELECT id, subject_memory_id, object_memory_id,
                               relation_type, confidence, evidence, created_at
                        FROM secretariat.memory_relations
                        WHERE subject_memory_id = ANY(CAST(:memory_ids AS uuid[]))
                           OR object_memory_id = ANY(CAST(:memory_ids AS uuid[]))
                        ORDER BY confidence DESC, created_at DESC
                        LIMIT 64
                        """
                    ),
                    {"memory_ids": memory_ids},
                )
                .mappings()
                .all()
            )

        messages = [
            {
                "id": str(row["id"]),
                "sequence": int(row["sequence"]),
                "role": row["role"],
                "content": row["content"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in reversed(message_rows)
        ]
        distillations = [
            {
                **{
                    key: value.isoformat() if isinstance(value, datetime) else value
                    for key, value in dict(row).items()
                },
                "id": str(row["id"]),
            }
            for row in distillation_rows
        ]
        memories = [
            {
                **{
                    key: (
                        str(value)
                        if isinstance(value, UUID)
                        else value.isoformat()
                        if isinstance(value, datetime)
                        else value
                    )
                    for key, value in dict(row).items()
                },
                "memory_is_not_authority": True,
            }
            for row in memory_rows
        ]
        relations = [
            {
                **{
                    key: (
                        str(value)
                        if isinstance(value, UUID)
                        else value.isoformat()
                        if isinstance(value, datetime)
                        else value
                    )
                    for key, value in dict(row).items()
                }
            }
            for row in relation_rows
        ]
        payload = {
            "available": True,
            "trust": "derived_memory_requires_live_verification_for_actions",
            "tenant_scope": "current_tenant_only",
            "privacy_scope": "owner_private_plus_company_shared",
            "conversation_id": str(parsed_id),
            "title": conversation["title"],
            "depth": normalized_depth,
            "distillation_level": source_state["distillation_level"],
            "recent_complete_evidence": messages,
            "distillations": distillations,
            "memory_units": memories,
            "memory_relations": relations,
            "memory_index": {
                **source_state,
                "visible_messages": len(messages),
                "visible_distillations": len(distillations),
                "visible_memories": len(memories),
                "source_cursor": source_cursor,
                "query_hash": query_hash,
                "available_depths": ["index", "focused", "deep"],
            },
            "compiled_at": datetime.now(UTC).isoformat(),
            "cache": "miss",
        }
        session.execute(
            text(
                """
                INSERT INTO secretariat.context_snapshots(
                  id, tenant_id, owner_user_id, conversation_id,
                  query_hash, source_cursor, memory_depth,
                  distillation_level, payload, expires_at
                ) VALUES (
                  :id, :tenant_id, :owner_user_id, :conversation_id,
                  :query_hash, :source_cursor, :memory_depth,
                  :distillation_level, CAST(:payload AS jsonb),
                  now() + interval '10 minutes'
                )
                ON CONFLICT (
                  tenant_id, owner_user_id, conversation_id,
                  query_hash, source_cursor, memory_depth
                ) DO UPDATE SET
                  distillation_level = GREATEST(
                    secretariat.context_snapshots.distillation_level,
                    EXCLUDED.distillation_level
                  ),
                  payload = EXCLUDED.payload,
                  created_at = now(),
                  expires_at = EXCLUDED.expires_at
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "conversation_id": parsed_id,
                "query_hash": query_hash,
                "source_cursor": source_cursor,
                "memory_depth": normalized_depth,
                "distillation_level": source_state["distillation_level"],
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
            },
        )
    return payload


def list_memory_units(
    actor: ActorContext,
    *,
    conversation_id: object | None = None,
    limit: int = 100,
) -> list[dict[str, object]]:
    parsed_id = _uuid(conversation_id) if conversation_id else None
    with tenant_session(actor.tenant_id) as session:
        if parsed_id and _owned_conversation(session, actor, parsed_id) is None:
            raise HTTPException(status_code=404, detail="Conversation not found")
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, conversation_id, kind, scope, content,
                           confidence, salience, status, evidence, metadata,
                           valid_from, valid_to, created_at, updated_at
                    FROM secretariat.memory_units
                    WHERE (
                        (scope = 'private' AND owner_user_id = :owner_user_id)
                        OR scope = 'company'
                      )
                      AND (
                        CAST(:conversation_id AS uuid) IS NULL
                        OR conversation_id = CAST(:conversation_id AS uuid)
                      )
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "owner_user_id": actor.user_id,
                    "conversation_id": parsed_id,
                    "limit": max(1, min(int(limit), 500)),
                },
            )
            .mappings()
            .all()
        )
    return [
        {
            key: (
                str(value)
                if isinstance(value, UUID)
                else value.isoformat()
                if isinstance(value, datetime)
                else value
            )
            for key, value in dict(row).items()
        }
        for row in rows
    ]


def forget_memory_unit(actor: ActorContext, *, memory_id: object) -> dict[str, object]:
    parsed_id = _uuid(memory_id)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    UPDATE secretariat.memory_units
                    SET status = 'forgotten', valid_to = now()
                    WHERE id = :id
                      AND scope = 'private'
                      AND owner_user_id = :owner_user_id
                    RETURNING id, status, valid_to
                    """
                ),
                {"id": parsed_id, "owner_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Private memory not found",
            )
        session.execute(
            text(
                """
                DELETE FROM secretariat.context_snapshots
                WHERE owner_user_id = :owner_user_id
                """
            ),
            {"owner_user_id": actor.user_id},
        )
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "valid_to": row["valid_to"].isoformat(),
    }
