"""Verified, display-only identity title composition.

Titles are an identity projection, never an authorization input.  Academic
claims come from explicit verified rows; academic appointments and offices
come from active tenant positions.  Free-form profile fields are deliberately
absent from this service so a biography cannot manufacture an official title.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence

from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session

_ACADEMIC_APPOINTMENT_ALIASES: tuple[tuple[tuple[str, ...], str], ...] = (
    (("assistantprofessor", "asstprofessor", "助理教授"), "assistant_professor"),
    (("associateprofessor", "assocprofessor", "副教授"), "associate_professor"),
    (("professor", "教授"), "professor"),
)

_SYSTEM_POSITION_MARKERS = (
    "systemadmin",
    "systemadministrator",
    "platformowner",
    "platformadmin",
    "系統管理員",
    "系统管理员",
    "平台所有者",
    "平台管理員",
    "平台管理员",
)

_OFFICE_MARKERS = (
    "chief",
    "ceo",
    "director",
    "head",
    "manager",
    "supervisor",
    "lead",
    "president",
    "主任",
    "主管",
    "局長",
    "局长",
    "院長",
    "院长",
    "首席",
    "經理",
    "经理",
    "總裁",
    "总裁",
)


def _token(value: object) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return re.sub(r"[^0-9a-z\u3400-\u9fff]+", "", normalized)


def _definition_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "code": str(row.get("code") or ""),
        "category": str(row.get("category") or ""),
        "label": str(row.get("label_zh_hant") or row.get("code") or ""),
        "label_zh_hant": str(row.get("label_zh_hant") or ""),
        "label_zh_hans": str(row.get("label_zh_hans") or row.get("label_zh_hant") or ""),
        "label_en": str(row.get("label_en") or row.get("label_zh_hant") or ""),
        "abbreviation": str(row.get("abbreviation") or ""),
        "priority": int(row.get("priority") or 100),
        "prefix": bool(row.get("name_prefix")),
    }


def _appointment_title_code(position: Mapping[str, object]) -> str:
    explicit = str(position.get("title_code") or "").strip()
    if explicit:
        return explicit
    candidates = (
        _token(position.get("position_code")),
        _token(position.get("name")),
        _token(position.get("name_en")),
    )
    for aliases, code in _ACADEMIC_APPOINTMENT_ALIASES:
        if any(alias and alias in candidate for alias in aliases for candidate in candidates):
            return code
    return ""


def _is_system_position(position: Mapping[str, object]) -> bool:
    values = (
        _token(position.get("position_code")),
        _token(position.get("name")),
        _token(position.get("name_en")),
        _token(position.get("role_name")),
    )
    return any(marker in value for marker in _SYSTEM_POSITION_MARKERS for value in values)


def _is_public_office(position: Mapping[str, object]) -> bool:
    if _is_system_position(position):
        return False
    if bool(position.get("is_manager")) or int(position.get("role_level") or 0) >= 6:
        return True
    values = (
        _token(position.get("position_code")),
        _token(position.get("name")),
        _token(position.get("name_en")),
    )
    return any(marker in value for marker in _OFFICE_MARKERS for value in values)


def compose_official_titles(
    actor: ActorContext,
    *,
    definitions: Sequence[Mapping[str, object]],
    claims: Sequence[Mapping[str, object]],
    positions: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """Compose one deterministic Swiss title stack from verified sources."""

    definitions_by_code = {
        str(row.get("code") or ""): _definition_payload(row)
        for row in definitions
        if row.get("code")
    }
    candidates: list[dict[str, object]] = []

    for claim in claims:
        code = str(claim.get("title_code") or "")
        definition = definitions_by_code.get(code)
        if not definition:
            continue
        candidates.append(
            {
                **definition,
                "kind": "standard",
                "display": definition["abbreviation"] or definition["label"],
                "source_kind": str(claim.get("source_kind") or "verified_record"),
                "source_ref": str(claim.get("source_ref") or ""),
                "verified": True,
                "appointment_type": None,
            }
        )

    office_candidates: list[dict[str, object]] = []
    for position in positions:
        title_code = _appointment_title_code(position)
        definition = definitions_by_code.get(title_code)
        appointment_type = str(position.get("appointment_type") or "concurrent")
        if definition and str(definition["category"]) == "academic_appointment":
            candidates.append(
                {
                    **definition,
                    "kind": "standard",
                    "display": definition["abbreviation"] or definition["label"],
                    "source_kind": "active_appointment",
                    "source_ref": str(position.get("position_code") or ""),
                    "verified": True,
                    "appointment_type": appointment_type,
                }
            )
            continue
        if definition:
            candidates.append(
                {
                    **definition,
                    "kind": "standard",
                    "display": definition["abbreviation"] or definition["label"],
                    "source_kind": "active_appointment",
                    "source_ref": str(position.get("position_code") or ""),
                    "verified": True,
                    "appointment_type": appointment_type,
                }
            )
            continue
        if not _is_public_office(position):
            continue
        label = str(position.get("name") or position.get("position_code") or "").strip()
        if not label:
            continue
        role_level = max(1, min(int(position.get("role_level") or 1), 10))
        office_candidates.append(
            {
                "code": f"office:{position.get('position_code')}",
                "category": "organizational_office",
                "label": label,
                "label_zh_hant": label,
                "label_zh_hans": label,
                "label_en": str(position.get("name_en") or label),
                "abbreviation": "",
                "kind": "custom",
                "display": label,
                "priority": 60
                + ((10 - role_level) * 3)
                + (0 if appointment_type == "primary" else 8),
                "prefix": False,
                "source_kind": "active_appointment",
                "source_ref": str(position.get("position_code") or ""),
                "verified": True,
                "appointment_type": appointment_type,
                "role_level": role_level,
            }
        )
    candidates.extend(office_candidates)

    ordered: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in sorted(
        candidates,
        key=lambda value: (
            int(value.get("priority") or 100),
            str(value.get("display") or "").casefold(),
            str(value.get("code") or ""),
        ),
    ):
        key = str(item.get("code") or item.get("display") or "").casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        public = {key: value for key, value in item.items() if key not in {"priority", "prefix"}}
        public["rank"] = len(ordered) + 1
        ordered.append(public)
        if len(ordered) >= 12:
            break

    academic_prefixes = [
        str(item.get("abbreviation") or "")
        for item in sorted(candidates, key=lambda value: int(value.get("priority") or 100))
        if item.get("prefix") and item.get("abbreviation")
    ]
    academic_prefixes = list(dict.fromkeys(academic_prefixes))
    primary_title = ordered[0] if ordered else None
    primary_office = next(
        (item for item in ordered if item.get("category") == "organizational_office"),
        None,
    )
    academic_title = next(
        (
            str(item.get("code"))
            for item in ordered
            if item.get("category") == "academic_appointment"
        ),
        None,
    )
    has_doctorate = any(item.get("code") == "doctor" for item in ordered)
    return {
        "schema": "warehouse.identity-title-stack.v1",
        "title_prefix": " ".join(academic_prefixes),
        "primary_title": primary_title,
        "primary_office": primary_office,
        "titles": ordered,
        "highest_education": "doctorate" if has_doctorate else None,
        "education_label": "博士" if has_doctorate else None,
        "academic_title": academic_title,
        "academic_title_label": (
            next(
                (
                    str(item.get("label"))
                    for item in ordered
                    if item.get("code") == academic_title
                ),
                None,
            )
            if academic_title
            else None
        ),
        "title_source": {
            "kind": "verified_title_projection",
            "status": "active",
            "source": actor.tenant_name,
            "claim_count": len(claims),
            "appointment_count": len(positions),
            "policy": "academic_then_primary_office",
            "permissions_unchanged": True,
        },
    }


def official_title_profile(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        definitions = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT code, category, label_zh_hant, label_zh_hans,
                           label_en, abbreviation, priority, name_prefix
                    FROM iam.title_definitions
                    WHERE active
                    ORDER BY priority, code
                    """
                )
            ).mappings()
        ]
        claims = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT title_code, source_kind, source_ref
                    FROM iam.person_title_claims
                    WHERE user_id = :user_id AND status = 'active'
                      AND (valid_from IS NULL OR valid_from <= now())
                      AND (valid_until IS NULL OR valid_until > now())
                    ORDER BY created_at, id
                    """
                ),
                {"user_id": actor.user_id},
            ).mappings()
        ]
        positions = [
            dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT pp.position_code, pp.name, pp.name_en, pp.role_name,
                           pp.role_level, pp.is_manager, pp.title_code,
                           mp.appointment_type
                    FROM iam.membership_positions AS mp
                    JOIN iam.position_profiles AS pp
                      ON pp.tenant_id = mp.tenant_id
                     AND pp.position_code = mp.position_code
                    WHERE mp.user_id = :user_id AND mp.active AND pp.active
                    ORDER BY CASE mp.appointment_type WHEN 'primary' THEN 0 ELSE 1 END,
                             pp.role_level DESC, pp.position_code
                    """
                ),
                {"user_id": actor.user_id},
            ).mappings()
        ]
    return compose_official_titles(
        actor,
        definitions=definitions,
        claims=claims,
        positions=positions,
    )
