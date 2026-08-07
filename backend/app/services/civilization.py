"""Tenant-owned, fixed-template publishing service for Civilization."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import system_session, tenant_session

TEMPLATE_KEY = "swiss_b_longform_v1"
CONTENT_SCHEMA = "warehouse.civilization.content.v1"
_DOMAINS = frozenset({"judgement", "technology", "organization", "time", "ethics"})
_THOUGHT_COLUMNS = """
id, stable_key, domain, title, prompt, thesis, relations, lenses,
occurred_on, display_order, source, created_by, created_at, updated_at,
revision, template_key, published_content, draft_content,
publication_status, published_revision, published_at,
public_share_enabled, public_share_key, public_shared_at
"""
_PUBLIC_SHARE_RE = re.compile(r"^[a-z0-9_-]{12,64}$")


def _can_manage(actor: ActorContext, created_by: UUID | None) -> bool:
    return (
        actor.role_level >= 10
        or "settings.manage" in actor.permissions
        or created_by == actor.user_id
    )


def _can_delete(actor: ActorContext, created_by: UUID | None) -> bool:
    return _can_manage(actor, created_by)


def _language(locale: str) -> str:
    return "en" if locale.lower().startswith("en") else "zh"


def _localized(value: str, locale: str) -> dict[str, str]:
    return {_language(locale): value}


def _clean_text(
    payload: dict[str, object],
    key: str,
    *,
    maximum: int,
    required: bool = True,
    default: str = "",
) -> str:
    value = str(payload.get(key) if payload.get(key) is not None else default).strip()
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


def _clean_domain(value: object, *, default: str = "judgement") -> str:
    domain = str(value or default).strip().lower()
    if domain not in _DOMAINS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="domain is not supported",
        )
    return domain


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
        lens_text = _clean_text(item, "text", maximum=2000)
        lenses.append({"name": _localized(name, locale), "text": _localized(lens_text, locale)})
    return lenses


def _clean_relations(payload: dict[str, object], locale: str) -> list[dict[str, str]]:
    raw = payload.get("relations") or []
    if not isinstance(raw, list):
        raise HTTPException(status_code=422, detail="relations must be an array")
    if len(raw) > 12:
        raise HTTPException(status_code=422, detail="no more than 12 relations are allowed")
    relations: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            localized = {
                language: str(item.get(language) or "").strip()
                for language in ("zh", "en")
                if str(item.get(language) or "").strip()
            }
            if not localized:
                raise HTTPException(status_code=422, detail=f"relations[{index}] is empty")
            if any(len(value) > 160 for value in localized.values()):
                raise HTTPException(status_code=422, detail=f"relations[{index}] is too long")
            relations.append(localized)
            continue
        value = str(item or "").strip()
        if not value:
            raise HTTPException(status_code=422, detail=f"relations[{index}] is empty")
        if len(value) > 160:
            raise HTTPException(status_code=422, detail=f"relations[{index}] is too long")
        relations.append(_localized(value, locale))
    return relations


def _clean_sections(value: object) -> list[dict[str, object]]:
    if value in (None, ""):
        return []
    if not isinstance(value, list):
        raise HTTPException(status_code=422, detail="content.sections must be an array")
    if len(value) > 24:
        raise HTTPException(status_code=422, detail="content.sections allows at most 24 sections")
    sections: list[dict[str, object]] = []
    total = 0
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise HTTPException(
                status_code=422, detail=f"content.sections[{index}] must be an object"
            )
        marker = _clean_text(raw, "marker", maximum=20, required=False)
        kicker = _clean_text(raw, "kicker", maximum=80, required=False)
        heading = _clean_text(raw, "heading", maximum=300)
        paragraphs_raw = raw.get("paragraphs") or []
        if isinstance(paragraphs_raw, str):
            paragraphs_raw = [part.strip() for part in paragraphs_raw.split("\n\n") if part.strip()]
        if not isinstance(paragraphs_raw, list) or not paragraphs_raw:
            raise HTTPException(
                status_code=422, detail=f"content.sections[{index}].paragraphs is required"
            )
        if len(paragraphs_raw) > 16:
            raise HTTPException(
                status_code=422, detail=f"content.sections[{index}] has too many paragraphs"
            )
        paragraphs = []
        for paragraph_index, raw_paragraph in enumerate(paragraphs_raw):
            paragraph = str(raw_paragraph or "").strip()
            if not paragraph:
                raise HTTPException(
                    status_code=422,
                    detail=f"content.sections[{index}].paragraphs[{paragraph_index}] is empty",
                )
            if len(paragraph) > 5000:
                raise HTTPException(status_code=422, detail="a Civilization paragraph is too long")
            total += len(paragraph)
            paragraphs.append(paragraph)
        sections.append(
            {"marker": marker, "kicker": kicker, "heading": heading, "paragraphs": paragraphs}
        )
    if total > 60000:
        raise HTTPException(status_code=422, detail="Civilization article body is too long")
    return sections


def _clean_content(
    raw: object,
    *,
    domain: str,
    fallback: dict[str, object] | None = None,
) -> dict[str, object]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise HTTPException(status_code=422, detail="content must be an object")
    candidate = {**(fallback or {}), **raw}
    title = _clean_text(candidate, "title", maximum=400)
    short = _clean_text(candidate, "short", maximum=800)
    thesis = _clean_text(candidate, "thesis", maximum=60000)
    return {
        "eyebrow": _clean_text(
            candidate,
            "eyebrow",
            maximum=100,
            required=False,
            default="CIVILIZATION · QUESTION",
        ),
        "category_label": _clean_text(
            candidate,
            "category_label",
            maximum=80,
            required=False,
            default=domain.upper(),
        ),
        "title": title,
        "short": short,
        "thesis": thesis,
        "quote": _clean_text(candidate, "quote", maximum=1200, required=False, default=short),
        "sections": _clean_sections(candidate.get("sections")),
        "footer_left": _clean_text(
            candidate,
            "footer_left",
            maximum=120,
            required=False,
            default="12 COLUMN SYSTEM · ONE QUESTION / MANY LENSES",
        ),
        "footer_right": _clean_text(
            candidate,
            "footer_right",
            maximum=120,
            required=False,
            default="INFORMATION BEFORE DECORATION",
        ),
    }


def _content_locale(content: object, locale: str) -> dict[str, object]:
    if not isinstance(content, dict):
        return {}
    locales = content.get("locales")
    if not isinstance(locales, dict):
        return {}
    language = _language(locale)
    selected = locales.get(language) or locales.get("zh") or locales.get("en") or {}
    return dict(selected) if isinstance(selected, dict) else {}


def _merge_content(
    existing: object,
    replacement: dict[str, object],
    locale: str,
) -> dict[str, object]:
    current = dict(existing) if isinstance(existing, dict) else {}
    raw_locales = current.get("locales")
    locales = dict(raw_locales) if isinstance(raw_locales, dict) else {}
    locales[_language(locale)] = replacement
    return {
        "schema": CONTENT_SCHEMA,
        "template_key": TEMPLATE_KEY,
        "locales": locales,
    }


def _legacy_content(row: dict[str, object]) -> dict[str, object]:
    title = row.get("title") if isinstance(row.get("title"), dict) else {}
    prompt = row.get("prompt") if isinstance(row.get("prompt"), dict) else {}
    thesis = row.get("thesis") if isinstance(row.get("thesis"), dict) else {}
    languages = set(title) | set(prompt) | set(thesis) or {"zh"}
    locales: dict[str, object] = {}
    for language in languages:
        localized_title = str(title.get(language) or title.get("zh") or title.get("en") or "")
        localized_short = str(prompt.get(language) or prompt.get("zh") or prompt.get("en") or "")
        localized_thesis = str(thesis.get(language) or thesis.get("zh") or thesis.get("en") or "")
        locales[str(language)] = {
            "eyebrow": "CIVILIZATION · QUESTION",
            "category_label": str(row.get("domain") or "judgement").upper(),
            "title": localized_title,
            "short": localized_short,
            "thesis": localized_thesis,
            "quote": localized_short,
            "sections": [],
            "footer_left": "12 COLUMN SYSTEM · ONE QUESTION / MANY LENSES",
            "footer_right": "INFORMATION BEFORE DECORATION",
        }
    return {"schema": CONTENT_SCHEMA, "template_key": TEMPLATE_KEY, "locales": locales}


def _effective_content(
    row: dict[str, object], field: str = "published_content"
) -> dict[str, object]:
    value = row.get(field)
    if isinstance(value, dict) and isinstance(value.get("locales"), dict):
        return value
    return _legacy_content(row)


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


def _merged_relations(
    existing: object,
    replacement: list[dict[str, str]],
) -> list[dict[str, str]]:
    current = existing if isinstance(existing, list) else []
    merged: list[dict[str, str]] = []
    for index, item in enumerate(replacement):
        prior = current[index] if index < len(current) else {}
        localized = dict(prior) if isinstance(prior, dict) else {}
        localized.update(item)
        merged.append(
            {str(language): str(value) for language, value in localized.items() if value is not None}
        )
    return merged


def _expected_revision(payload: dict[str, object]) -> int:
    try:
        value = int(payload.get("expected_revision") or 0)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="expected_revision must be an integer") from exc
    if value < 1:
        raise HTTPException(status_code=422, detail="expected_revision is required")
    return value


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


def _serialize(row: dict[str, object], actor: ActorContext, *, number: int) -> dict[str, object]:
    occurred_on = row["occurred_on"]
    created_at = row["created_at"]
    updated_at = row["updated_at"]
    created_by = row.get("created_by")
    published_at = row.get("published_at")
    public_shared_at = row.get("public_shared_at")
    assert isinstance(occurred_on, date)
    assert isinstance(created_at, datetime)
    assert isinstance(updated_at, datetime)
    assert created_by is None or isinstance(created_by, UUID)
    can_manage = _can_manage(actor, created_by)
    public_share_enabled = bool(row.get("public_share_enabled"))
    public_share_key = str(row.get("public_share_key") or "")
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
        "template_key": str(row.get("template_key") or TEMPLATE_KEY),
        "content": _effective_content(row),
        "draft_content": (
            row.get("draft_content") if can_manage and row.get("draft_content") else None
        ),
        "publication_status": str(row.get("publication_status") or "published"),
        "published_revision": int(row.get("published_revision") or 0),
        "published_at": published_at.isoformat() if isinstance(published_at, datetime) else None,
        "has_draft": bool(row.get("draft_content")),
        "can_edit": can_manage,
        "can_publish": can_manage,
        "can_delete": _can_delete(actor, created_by),
        "public_share_enabled": public_share_enabled,
        "public_path": (
            f"/civilization/p/{public_share_key}"
            if public_share_enabled and public_share_key
            else None
        ),
        "public_share_key": public_share_key if can_manage and public_share_key else None,
        "public_shared_at": (
            public_shared_at.isoformat() if isinstance(public_shared_at, datetime) else None
        ),
    }


def _snapshot(row: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "warehouse.civilization.revision.v1",
        "domain": str(row["domain"]),
        "title": row["title"],
        "prompt": row["prompt"],
        "thesis": row["thesis"],
        "relations": row["relations"] or [],
        "lenses": row["lenses"] or [],
        "template_key": str(row.get("template_key") or TEMPLATE_KEY),
        "content": _effective_content(row),
    }


def _insert_revision(session: Session, actor: ActorContext, row: dict[str, object]) -> None:
    session.execute(
        text(
            """
            INSERT INTO civilization.thought_revisions(
              id, tenant_id, thought_id, revision_no, template_key, snapshot, published_by
            ) VALUES (
              :id, :tenant_id, :thought_id, :revision_no, :template_key,
              CAST(:snapshot AS jsonb), :published_by
            )
            """
        ),
        {
            "id": uuid4(),
            "tenant_id": actor.tenant_id,
            "thought_id": row["id"],
            "revision_no": int(row["published_revision"]),
            "template_key": TEMPLATE_KEY,
            "snapshot": json.dumps(_snapshot(row), ensure_ascii=False),
            "published_by": actor.user_id,
        },
    )


def _write_public_snapshot(
    session: Session,
    actor: ActorContext,
    row: dict[str, object],
) -> None:
    """Copy only the current published representation into the public boundary."""

    share_key = str(row.get("public_share_key") or "")
    if not bool(row.get("public_share_enabled")) or not _PUBLIC_SHARE_RE.fullmatch(share_key):
        return
    content = _effective_content(row)
    session.execute(
        text(
            """
            INSERT INTO civilization.public_shares(
              share_key, tenant_id, thought_id, domain, content, lenses,
              occurred_on, published_revision, shared_by
            ) VALUES (
              :share_key, :tenant_id, :thought_id, :domain,
              CAST(:content AS jsonb), CAST(:lenses AS jsonb),
              :occurred_on, :published_revision, :shared_by
            )
            ON CONFLICT (thought_id) DO UPDATE
            SET share_key = EXCLUDED.share_key,
                domain = EXCLUDED.domain,
                content = EXCLUDED.content,
                lenses = EXCLUDED.lenses,
                occurred_on = EXCLUDED.occurred_on,
                published_revision = EXCLUDED.published_revision,
                shared_by = EXCLUDED.shared_by,
                updated_at = now()
            """
        ),
        {
            "share_key": share_key,
            "tenant_id": actor.tenant_id,
            "thought_id": row["id"],
            "domain": str(row["domain"]),
            "content": json.dumps(content, ensure_ascii=False),
            "lenses": json.dumps(row.get("lenses") or [], ensure_ascii=False),
            "occurred_on": row["occurred_on"],
            "published_revision": int(row.get("published_revision") or 0),
            "shared_by": actor.user_id,
        },
    )


def template_catalog(actor: ActorContext) -> dict[str, object]:
    return {
        "templates": [
            {
                "key": TEMPLATE_KEY,
                "name": "Swiss B · International Grid Longform",
                "version": 1,
                "layout_locked": True,
                "editable_slots": [
                    "eyebrow",
                    "category_label",
                    "title",
                    "short",
                    "thesis",
                    "quote",
                    "sections[].marker",
                    "sections[].kicker",
                    "sections[].heading",
                    "sections[].paragraphs[]",
                    "footer_left",
                    "footer_right",
                ],
                "responsive": ["desktop", "tablet", "mobile"],
            }
        ],
        "tenant": actor.tenant_slug,
    }


def list_thoughts(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
                    FROM civilization.thoughts
                    ORDER BY occurred_on, display_order, id
                    """
                )
            )
            .mappings()
            .all()
        )
    visible = [
        dict(row)
        for row in rows
        if str(row["publication_status"]) == "published"
        or _can_manage(actor, row.get("created_by"))
    ]
    return {
        "thoughts": [_serialize(row, actor, number=int(row["display_order"])) for row in visible],
        "can_create": True,
        "template_key": TEMPLATE_KEY,
    }


def get_thought(actor: ActorContext, thought_id: UUID) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    f"SELECT {_THOUGHT_COLUMNS} FROM civilization.thoughts WHERE id = :thought_id"
                ),
                {"thought_id": thought_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Thought not found")
    data = dict(row)
    if data["publication_status"] != "published" and not _can_manage(actor, data.get("created_by")):
        raise HTTPException(status_code=404, detail="Thought not found")
    return {"thought": _serialize(data, actor, number=int(data["display_order"]))}


def create_thought(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    domain = _clean_domain(payload.get("domain"))
    locale = str(payload.get("locale") or "zh")
    raw_content = payload.get("content")
    if not isinstance(raw_content, dict):
        raw_content = {
            key: payload.get(key)
            for key in (
                "title",
                "short",
                "thesis",
                "eyebrow",
                "category_label",
                "quote",
                "sections",
                "footer_left",
                "footer_right",
            )
            if key in payload
        }
    normalized = _clean_content(raw_content, domain=domain)
    lenses = _clean_lenses(payload, locale)
    relations = _clean_relations(payload, locale)
    publish = payload.get("publish", True) is not False
    thought_id = uuid4()
    stable_key = f"thought-{thought_id.hex}"
    content = _merge_content({}, normalized, locale)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": f"civilization:{actor.tenant_id}:display-order"},
        )
        display_order = int(
            session.execute(
                text("SELECT COALESCE(MAX(display_order), 0) + 1 FROM civilization.thoughts")
            ).scalar_one()
        )
        row = dict(
            session.execute(
                text(
                    f"""
                    INSERT INTO civilization.thoughts(
                      id, tenant_id, stable_key, domain, title, prompt, thesis,
                      relations, lenses, occurred_on, display_order, source, created_by,
                      template_key, published_content, draft_content, publication_status,
                      published_revision, published_at
                    ) VALUES (
                      :id, :tenant_id, :stable_key, :domain, CAST(:title AS jsonb),
                      CAST(:prompt AS jsonb), CAST(:thesis AS jsonb), CAST(:relations AS jsonb),
                      CAST(:lenses AS jsonb), CURRENT_DATE, :display_order, 'member', :created_by,
                      :template_key, CAST(:published_content AS jsonb),
                      CAST(:draft_content AS jsonb),
                      :publication_status, :published_revision, :published_at
                    ) RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "id": thought_id,
                    "tenant_id": actor.tenant_id,
                    "stable_key": stable_key,
                    "domain": domain,
                    "title": json.dumps(
                        _localized(str(normalized["title"]), locale), ensure_ascii=False
                    ),
                    "prompt": json.dumps(
                        _localized(str(normalized["short"]), locale), ensure_ascii=False
                    ),
                    "thesis": json.dumps(
                        _localized(str(normalized["thesis"]), locale), ensure_ascii=False
                    ),
                    "lenses": json.dumps(lenses, ensure_ascii=False),
                    "relations": json.dumps(relations, ensure_ascii=False),
                    "display_order": display_order,
                    "created_by": actor.user_id,
                    "template_key": TEMPLATE_KEY,
                    "published_content": json.dumps(content if publish else {}, ensure_ascii=False),
                    "draft_content": json.dumps(None if publish else content, ensure_ascii=False),
                    "publication_status": "published" if publish else "draft",
                    "published_revision": 1 if publish else 0,
                    "published_at": datetime.now().astimezone() if publish else None,
                },
            )
            .mappings()
            .one()
        )
        if publish:
            _insert_revision(session, actor, row)
        _audit(
            session,
            actor,
            "civilization.thought.published" if publish else "civilization.thought.draft_created",
            {"thought_id": str(thought_id), "stable_key": stable_key, "template_key": TEMPLATE_KEY},
        )
    return {"ok": True, "thought": _serialize(row, actor, number=display_order)}


def update_thought(
    actor: ActorContext, thought_id: UUID, payload: dict[str, object]
) -> dict[str, object]:
    """Compatibility PUT: validate a complete payload and publish it atomically."""
    save_draft(actor, thought_id, payload)
    return publish_thought(
        actor, thought_id, {"expected_revision": _latest_revision(actor, thought_id)}
    )


def _latest_revision(actor: ActorContext, thought_id: UUID) -> int:
    with tenant_session(actor.tenant_id) as session:
        value = session.execute(
            text("SELECT revision FROM civilization.thoughts WHERE id = :thought_id"),
            {"thought_id": thought_id},
        ).scalar_one_or_none()
    if value is None:
        raise HTTPException(status_code=404, detail="Thought not found")
    return int(value)


def save_draft(
    actor: ActorContext, thought_id: UUID, payload: dict[str, object]
) -> dict[str, object]:
    expected_revision = _expected_revision(payload)
    locale = str(payload.get("locale") or "zh")
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
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
            raise HTTPException(status_code=404, detail="Thought not found")
        data = dict(current)
        if not _can_manage(actor, data.get("created_by")):
            raise HTTPException(
                status_code=403,
                detail="Only the creator or a company administrator can edit this thought",
            )
        if int(data["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "revision_conflict",
                    "expected_revision": expected_revision,
                    "current_revision": int(data["revision"]),
                },
            )
        domain = _clean_domain(payload.get("domain"), default=str(data["domain"]))
        base_content = data.get("draft_content") or _effective_content(data)
        base_locale = _content_locale(base_content, locale)
        raw_content = payload.get("content")
        if not isinstance(raw_content, dict):
            raw_content = {
                key: payload.get(key)
                for key in (
                    "title",
                    "short",
                    "thesis",
                    "eyebrow",
                    "category_label",
                    "quote",
                    "sections",
                    "footer_left",
                    "footer_right",
                )
                if key in payload
            }
        normalized = _clean_content(raw_content, domain=domain, fallback=base_locale)
        draft_content = _merge_content(base_content, normalized, locale)
        lenses = (
            _merged_lenses(data["lenses"], _clean_lenses(payload, locale))
            if "lenses" in payload
            else data["lenses"]
        )
        relations = (
            _merged_relations(data["relations"], _clean_relations(payload, locale))
            if "relations" in payload
            else data["relations"]
        )
        row = dict(
            session.execute(
                text(
                    f"""
                    UPDATE civilization.thoughts
                    SET domain = :domain, draft_content = CAST(:draft_content AS jsonb),
                        relations = CAST(:relations AS jsonb), lenses = CAST(:lenses AS jsonb),
                        updated_at = now(), revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "domain": domain,
                    "draft_content": json.dumps(draft_content, ensure_ascii=False),
                    "lenses": json.dumps(lenses, ensure_ascii=False),
                    "relations": json.dumps(relations, ensure_ascii=False),
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "civilization.thought.draft_saved",
            {
                "thought_id": str(thought_id),
                "revision": int(row["revision"]),
                "template_key": TEMPLATE_KEY,
            },
        )
    return {
        "ok": True,
        "status": "draft_saved",
        "thought": _serialize(row, actor, number=int(row["display_order"])),
    }


def preview_thought(actor: ActorContext, thought_id: UUID) -> dict[str, object]:
    result = get_thought(actor, thought_id)["thought"]
    assert isinstance(result, dict)
    content = (
        result.get("draft_content")
        if result.get("can_edit") and result.get("draft_content")
        else result.get("content")
    )
    return {
        "ok": True,
        "template_key": TEMPLATE_KEY,
        "layout_locked": True,
        "preview_source": "draft" if result.get("draft_content") else "published",
        "content": content,
        "thought": result,
    }


def _localized_projection(
    content: dict[str, object], fallback: dict[str, object]
) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    raw_locales = content.get("locales")
    locales = raw_locales if isinstance(raw_locales, dict) else {}
    title = dict(fallback.get("title") or {})
    prompt = dict(fallback.get("prompt") or {})
    thesis = dict(fallback.get("thesis") or {})
    for language, raw in locales.items():
        if not isinstance(raw, dict):
            continue
        title[str(language)] = str(raw.get("title") or "")
        prompt[str(language)] = str(raw.get("short") or "")
        thesis[str(language)] = str(raw.get("thesis") or "")
    return title, prompt, thesis


def publish_thought(
    actor: ActorContext, thought_id: UUID, payload: dict[str, object]
) -> dict[str, object]:
    expected_revision = _expected_revision(payload)
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
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
            raise HTTPException(status_code=404, detail="Thought not found")
        data = dict(current)
        if not _can_manage(actor, data.get("created_by")):
            raise HTTPException(
                status_code=403,
                detail="Only the creator or a company administrator can publish this thought",
            )
        if int(data["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "revision_conflict",
                    "expected_revision": expected_revision,
                    "current_revision": int(data["revision"]),
                },
            )
        content = data.get("draft_content") or _effective_content(data)
        assert isinstance(content, dict)
        title, prompt, thesis = _localized_projection(content, data)
        published_revision = int(data.get("published_revision") or 0) + 1
        row = dict(
            session.execute(
                text(
                    f"""
                    UPDATE civilization.thoughts
                    SET title = CAST(:title AS jsonb), prompt = CAST(:prompt AS jsonb),
                        thesis = CAST(:thesis AS jsonb),
                        published_content = CAST(:content AS jsonb),
                        draft_content = NULL, publication_status = 'published',
                        published_revision = :published_revision, published_at = now(),
                        updated_at = now(), revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "title": json.dumps(title, ensure_ascii=False),
                    "prompt": json.dumps(prompt, ensure_ascii=False),
                    "thesis": json.dumps(thesis, ensure_ascii=False),
                    "content": json.dumps(content, ensure_ascii=False),
                    "published_revision": published_revision,
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one()
        )
        _insert_revision(session, actor, row)
        _write_public_snapshot(session, actor, row)
        _audit(
            session,
            actor,
            "civilization.thought.published",
            {
                "thought_id": str(thought_id),
                "published_revision": published_revision,
                "template_key": TEMPLATE_KEY,
            },
        )
    return {
        "ok": True,
        "status": "published",
        "thought": _serialize(row, actor, number=int(row["display_order"])),
    }


def list_revisions(actor: ActorContext, thought_id: UUID) -> dict[str, object]:
    thought = get_thought(actor, thought_id)["thought"]
    assert isinstance(thought, dict)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT revision_no, template_key, published_by, published_at
                    FROM civilization.thought_revisions
                    WHERE thought_id = :thought_id
                    ORDER BY revision_no DESC
                    """
                ),
                {"thought_id": thought_id},
            )
            .mappings()
            .all()
        )
    return {
        "thought_id": str(thought_id),
        "current_published_revision": thought["published_revision"],
        "revisions": [
            {
                "revision_no": int(row["revision_no"]),
                "template_key": str(row["template_key"]),
                "published_by": str(row["published_by"]) if row["published_by"] else None,
                "published_at": row["published_at"].isoformat(),
            }
            for row in rows
        ],
    }


def restore_revision(
    actor: ActorContext,
    thought_id: UUID,
    revision_no: int,
    payload: dict[str, object],
) -> dict[str, object]:
    expected_revision = _expected_revision(payload)
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
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
            raise HTTPException(status_code=404, detail="Thought not found")
        data = dict(current)
        if not _can_manage(actor, data.get("created_by")):
            raise HTTPException(
                status_code=403,
                detail="Only the creator or a company administrator can restore this thought",
            )
        if int(data["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"reason": "revision_conflict", "current_revision": int(data["revision"])},
            )
        snapshot = session.execute(
            text(
                """
                SELECT snapshot
                FROM civilization.thought_revisions
                WHERE thought_id = :thought_id AND revision_no = :revision_no
                """
            ),
            {"thought_id": thought_id, "revision_no": revision_no},
        ).scalar_one_or_none()
        if not isinstance(snapshot, dict):
            raise HTTPException(status_code=404, detail="Civilization revision not found")
        restored = snapshot.get("content")
        if not isinstance(restored, dict):
            raise HTTPException(
                status_code=409, detail="Civilization revision has no restorable content"
            )
        row = dict(
            session.execute(
                text(
                    f"""
                    UPDATE civilization.thoughts
                    SET draft_content = CAST(:content AS jsonb),
                        updated_at = now(), revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "content": json.dumps(restored, ensure_ascii=False),
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "civilization.thought.revision_restored_to_draft",
            {"thought_id": str(thought_id), "revision_no": revision_no},
        )
    return {
        "ok": True,
        "status": "restored_to_draft",
        "source_revision": revision_no,
        "thought": _serialize(row, actor, number=int(row["display_order"])),
    }


def upsert_lens(
    actor: ActorContext,
    thought_id: UUID,
    lens_index: int,
    payload: dict[str, object],
) -> dict[str, object]:
    if not 0 <= lens_index < 12:
        raise HTTPException(status_code=422, detail="lens_index must be between 0 and 11")
    expected_revision = _expected_revision(payload)
    locale = str(payload.get("locale") or "zh")
    replacement = _clean_lenses({"lenses": [payload]}, locale)[0]
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
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
            raise HTTPException(status_code=404, detail="Thought not found")
        data = dict(current)
        if not _can_manage(actor, data.get("created_by")):
            raise HTTPException(
                status_code=403,
                detail="Only the creator or a company administrator can edit lenses",
            )
        if int(data["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={"reason": "revision_conflict", "current_revision": int(data["revision"])},
            )
        lenses = list(data.get("lenses") or [])
        if lens_index > len(lenses):
            raise HTTPException(status_code=422, detail="lenses must be added without gaps")
        if lens_index == len(lenses):
            lenses.append(replacement)
        else:
            lenses[lens_index] = _merged_lenses([lenses[lens_index]], [replacement])[0]
        row = dict(
            session.execute(
                text(
                    f"""
                    UPDATE civilization.thoughts
                    SET lenses = CAST(:lenses AS jsonb),
                        updated_at = now(), revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "lenses": json.dumps(lenses, ensure_ascii=False),
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "civilization.thought.lens_upserted",
            {"thought_id": str(thought_id), "lens_index": lens_index},
        )
    return {"ok": True, "thought": _serialize(row, actor, number=int(row["display_order"]))}


def configure_public_share(
    actor: ActorContext,
    thought_id: UUID,
    payload: dict[str, object],
) -> dict[str, object]:
    expected_revision = _expected_revision(payload)
    enabled_value = payload.get("enabled")
    if not isinstance(enabled_value, bool):
        raise HTTPException(status_code=422, detail="enabled must be a boolean")
    with tenant_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    f"""
                    SELECT {_THOUGHT_COLUMNS}
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
            raise HTTPException(status_code=404, detail="Thought not found")
        data = dict(current)
        if not _can_manage(actor, data.get("created_by")):
            raise HTTPException(
                status_code=403,
                detail="Only the creator or a company administrator can configure sharing",
            )
        if int(data["revision"]) != expected_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "revision_conflict",
                    "expected_revision": expected_revision,
                    "current_revision": int(data["revision"]),
                },
            )
        if enabled_value and str(data.get("publication_status")) != "published":
            raise HTTPException(
                status_code=409,
                detail="Publish the thought before enabling its public page",
            )
        if bool(data.get("public_share_enabled")) == enabled_value:
            if enabled_value:
                _write_public_snapshot(session, actor, data)
            else:
                session.execute(
                    text(
                        """
                        DELETE FROM civilization.public_shares
                        WHERE tenant_id = :tenant_id AND thought_id = :thought_id
                        """
                    ),
                    {"tenant_id": actor.tenant_id, "thought_id": thought_id},
                )
            return {
                "ok": True,
                "status": "public" if enabled_value else "private",
                "unchanged": True,
                "thought": _serialize(data, actor, number=int(data["display_order"])),
            }
        share_key = str(data.get("public_share_key") or "")
        if enabled_value and not share_key:
            share_key = uuid4().hex[:16]
        row = dict(
            session.execute(
                text(
                    f"""
                    UPDATE civilization.thoughts
                    SET public_share_enabled = :enabled,
                        public_share_key = CASE
                          WHEN :share_key = '' THEN public_share_key
                          ELSE :share_key
                        END,
                        public_shared_at = CASE
                          WHEN :enabled THEN COALESCE(public_shared_at, now())
                          ELSE public_shared_at
                        END,
                        updated_at = now(), revision = revision + 1
                    WHERE id = :thought_id AND revision = :expected_revision
                    RETURNING {_THOUGHT_COLUMNS}
                    """
                ),
                {
                    "enabled": enabled_value,
                    "share_key": share_key,
                    "thought_id": thought_id,
                    "expected_revision": expected_revision,
                },
            )
            .mappings()
            .one()
        )
        if enabled_value:
            _write_public_snapshot(session, actor, row)
        else:
            session.execute(
                text(
                    """
                    DELETE FROM civilization.public_shares
                    WHERE tenant_id = :tenant_id AND thought_id = :thought_id
                    """
                ),
                {"tenant_id": actor.tenant_id, "thought_id": thought_id},
            )
        _audit(
            session,
            actor,
            (
                "civilization.thought.public_share_enabled"
                if enabled_value
                else "civilization.thought.public_share_disabled"
            ),
            {
                "thought_id": str(thought_id),
                "share_key": share_key if enabled_value else None,
            },
        )
    return {
        "ok": True,
        "status": "public" if enabled_value else "private",
        "thought": _serialize(row, actor, number=int(row["display_order"])),
    }


def get_public_thought(share_key: str) -> dict[str, object]:
    normalized = str(share_key or "").strip().lower()
    if not _PUBLIC_SHARE_RE.fullmatch(normalized):
        raise HTTPException(status_code=404, detail="Public Civilization post not found")
    with system_session() as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT share_key, domain, content, lenses, occurred_on,
                           published_revision, shared_at, updated_at
                    FROM civilization.public_shares
                    WHERE share_key = :share_key
                    """
                ),
                {"share_key": normalized},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Public Civilization post not found")
    occurred_on = row["occurred_on"]
    assert isinstance(occurred_on, date)
    return {
        "schema": "warehouse.civilization.public-post.v1",
        "share_key": str(row["share_key"]),
        "domain": str(row["domain"]),
        "content": row["content"],
        "lenses": row["lenses"] or [],
        "date": f"{occurred_on.year:04d}—{occurred_on.month:02d}",
        "published_revision": int(row["published_revision"]),
        "shared_at": row["shared_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
        "public_path": f"/civilization/p/{normalized}",
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
            raise HTTPException(status_code=404, detail="Thought not found")
        if not _can_delete(actor, row["created_by"]):
            raise HTTPException(
                status_code=403,
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
