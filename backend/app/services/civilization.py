"""Tenant-owned content service for the Civilization module."""

from __future__ import annotations

import json
from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session

_DOMAINS = frozenset({"judgement", "technology", "organization", "time", "ethics"})


def _can_manage(actor: ActorContext, created_by: UUID | None) -> bool:
    return (
        actor.role_level >= 10
        or "settings.manage" in actor.permissions
        or created_by == actor.user_id
    )


def _can_delete(actor: ActorContext, created_by: UUID | None) -> bool:
    return _can_manage(actor, created_by)


def _localized(value: str, locale: str) -> dict[str, str]:
    language = "en" if locale.lower().startswith("en") else "zh"
    return {language: value}


def _clean_text(
    payload: dict[str, object],
    key: str,
    *,
    maximum: int,
    required: bool = True,
) -> str:
    value = str(payload.get(key) or "").strip()
    if required and not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{key} is required",
        )
    if len(value) > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{key} is too long",
        )
    return value


def _clean_lenses(payload: dict[str, object], locale: str) -> list[dict[str, object]]:
    raw = payload.get("lenses") or []
    if not isinstance(raw, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="lenses must be an array",
        )
    if len(raw) > 12:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="no more than 12 lenses are allowed",
        )
    lenses: list[dict[str, object]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"lenses[{index}] must be an object",
            )
        name = _clean_text(item, "name", maximum=80)
        lens_text = _clean_text(item, "text", maximum=500)
        lenses.append(
            {"name": _localized(name, locale), "text": _localized(lens_text, locale)}
        )
    return lenses


def _merged_localized(existing: object, value: str, locale: str) -> dict[str, str]:
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(_localized(value, locale))
    return {str(key): str(item) for key, item in merged.items() if item is not None}


def _merged_lenses(
    existing: object, replacement: list[dict[str, object]]
) -> list[dict[str, object]]:
    current = existing if isinstance(existing, list) else []
    merged: list[dict[str, object]] = []
    for index, item in enumerate(replacement):
        prior = current[index] if index < len(current) and isinstance(current[index], dict) else {}
        prior_name = prior.get("name") if isinstance(prior, dict) else {}
        prior_text = prior.get("text") if isinstance(prior, dict) else {}
        name = dict(prior_name) if isinstance(prior_name, dict) else {}
        lens_text = dict(prior_text) if isinstance(prior_text, dict) else {}
        name.update(item.get("name") if isinstance(item.get("name"), dict) else {})
        lens_text.update(item.get("text") if isinstance(item.get("text"), dict) else {})
        merged.append({"name": name, "text": lens_text})
    return merged


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
            "payload": json.dumps(payload, ensure_ascii=False),
        },
    )


def _serialize(
    row: dict[str, object], actor: ActorContext, *, number: int
) -> dict[str, object]:
    occurred_on = row["occurred_on"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]
    created_by = row.get("created_by")
    assert isinstance(occurred_on, date)
    assert isinstance(created_at, datetime)
    assert isinstance(updated_at, datetime)
    assert created_by is None or isinstance(created_by, UUID)
    return {
        "id": str(row["id"]),
        "stable_key": str(row["stable_key"]),
        "no": f"{number:02d}",
        "domain": str(row["domain"]),
        "title": row["title"],
        "short": row["prompt"],
        "thesis": row["thesis"],
        "relations": row["relations"] or [],
        "lenses": row["lenses"] or [],
        "date": f"{occurred_on.year:04d}—{occurred_on.month:02d}",
        "year": str(occurred_on.year),
        "source": str(row["source"]),
        "created_by": str(created_by) if created_by else None,
        "created_at": created_at.isoformat(),
        "updated_at": updated_at.isoformat(),
        "revision": int(row["revision"]),
        "can_edit": _can_manage(actor, created_by),
        "can_delete": _can_delete(actor, created_by),
    }


def list_thoughts(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, stable_key, domain, title, prompt, thesis, relations,
                           lenses, occurred_on, display_order, source, created_by,
                           created_at, updated_at, revision
                    FROM civilization.thoughts
                    ORDER BY occurred_on, display_order, id
                    """
                )
            )
            .mappings()
            .all()
        )
    return {
        "thoughts": [
            _serialize(dict(row), actor, number=index)
            for index, row in enumerate(rows, start=1)
        ],
        "can_create": True,
    }


def create_thought(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    domain = str(payload.get("domain") or "judgement").strip().lower()
    if domain not in _DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="domain is not supported",
        )
    title = _clean_text(payload, "title", maximum=160)
    prompt = _clean_text(payload, "short", maximum=180)
    thesis = _clean_text(payload, "thesis", maximum=1200)
    locale = str(payload.get("locale") or "zh")
    lenses = _clean_lenses(payload, locale)
    thought_id = uuid4()
    stable_key = f"thought-{thought_id.hex}"
    localized_title = _localized(title, locale)
    localized_prompt = _localized(prompt, locale)
    localized_thesis = _localized(thesis, locale)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"civilization:{actor.tenant_id}:display-order"},
        )
        display_order = int(
            session.execute(
                text(
                    "SELECT COALESCE(MAX(display_order), 0) + 1 "
                    "FROM civilization.thoughts"
                )
            ).scalar_one()
        )
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO civilization.thoughts(
                      id, tenant_id, stable_key, domain, title, prompt, thesis,
                      relations, lenses, occurred_on, display_order, source, created_by
                    ) VALUES (
                      :id, :tenant_id, :stable_key, :domain, CAST(:title AS jsonb),
                      CAST(:prompt AS jsonb), CAST(:thesis AS jsonb), '[]'::jsonb,
                      CAST(:lenses AS jsonb), CURRENT_DATE, :display_order, 'member', :created_by
                    )
                    RETURNING id, stable_key, domain, title, prompt, thesis, relations,
                              lenses, occurred_on, display_order, source, created_by,
                              created_at, updated_at, revision
                    """
                ),
                {
                    "id": thought_id,
                    "tenant_id": actor.tenant_id,
                    "stable_key": stable_key,
                    "domain": domain,
                    "title": json.dumps(localized_title, ensure_ascii=False),
                    "prompt": json.dumps(localized_prompt, ensure_ascii=False),
                    "thesis": json.dumps(localized_thesis, ensure_ascii=False),
                    "lenses": json.dumps(lenses, ensure_ascii=False),
                    "display_order": display_order,
                    "created_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "civilization.thought.created",
            {"thought_id": str(thought_id), "stable_key": stable_key},
        )
    return {"ok": True, "thought": _serialize(dict(row), actor, number=display_order)}


def update_thought(
    actor: ActorContext, thought_id: UUID, payload: dict[str, object]
) -> dict[str, object]:
    domain = str(payload.get("domain") or "judgement").strip().lower()
    if domain not in _DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="domain is not supported",
        )
    title = _clean_text(payload, "title", maximum=160)
    prompt = _clean_text(payload, "short", maximum=180)
    thesis = _clean_text(payload, "thesis", maximum=1200)
    locale = str(payload.get("locale") or "zh")
    lenses = _clean_lenses(payload, locale)
    try:
        expected_revision = int(payload.get("expected_revision") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expected_revision must be an integer",
        ) from exc
    if expected_revision < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="expected_revision is required",
        )

    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    """
                    SELECT id, stable_key, domain, title, prompt, thesis, relations,
                           lenses, occurred_on, display_order, source, created_by,
                           created_at, updated_at, revision
                    FROM civilization.thoughts
                    WHERE id = :thought_id
                    FOR UPDATE
                    """
                ),
                {"thought_id": thought_id},
            )
            .mappings()
            .one_or_none()
        )
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thought not found")
        current_data = dict(current)
        if not _can_manage(actor, current_data.get("created_by")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator or a company administrator can edit this thought",
            )
        current_revision = int(current_data["revision"])
        if current_revision != expected_revision:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "reason": "revision_conflict",
                    "expected_revision": expected_revision,
                    "current_revision": current_revision,
                },
            )
        row = (
            session.execute(
                text(
                    """
                    UPDATE civilization.thoughts
                    SET domain = :domain,
                        title = CAST(:title AS jsonb),
                        prompt = CAST(:prompt AS jsonb),
                        thesis = CAST(:thesis AS jsonb),
                        lenses = CAST(:lenses AS jsonb),
                        updated_at = now(),
                        revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING id, stable_key, domain, title, prompt, thesis, relations,
                              lenses, occurred_on, display_order, source, created_by,
                              created_at, updated_at, revision
                    """
                ),
                {
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                    "domain": domain,
                    "title": json.dumps(
                        _merged_localized(current_data["title"], title, locale),
                        ensure_ascii=False,
                    ),
                    "prompt": json.dumps(
                        _merged_localized(current_data["prompt"], prompt, locale),
                        ensure_ascii=False,
                    ),
                    "thesis": json.dumps(
                        _merged_localized(current_data["thesis"], thesis, locale),
                        ensure_ascii=False,
                    ),
                    "lenses": json.dumps(
                        _merged_lenses(current_data["lenses"], lenses),
                        ensure_ascii=False,
                    ),
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "civilization.thought.updated",
            {
                "thought_id": str(thought_id),
                "stable_key": str(current_data["stable_key"]),
                "revision": int(row["revision"]),
                "lens_count": len(lenses),
            },
        )
    return {
        "ok": True,
        "thought": _serialize(dict(row), actor, number=int(row["display_order"])),
    }


def delete_thought(actor: ActorContext, thought_id: UUID) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, stable_key, created_by
                    FROM civilization.thoughts
                    WHERE id = :thought_id
                    """
                ),
                {"thought_id": thought_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thought not found")
        created_by = row["created_by"]
        if not _can_delete(actor, created_by):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the creator or a company administrator can delete this thought",
            )
        session.execute(
            text("DELETE FROM civilization.thoughts WHERE id = :thought_id"),
            {"thought_id": thought_id},
        )
        _audit(
            session,
            actor,
            "civilization.thought.deleted",
            {"thought_id": str(thought_id), "stable_key": str(row["stable_key"])},
        )
    return {"ok": True, "deleted_id": str(thought_id)}
