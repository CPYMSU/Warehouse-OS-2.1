"""Tenant-scoped employment and personnel-record projections."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session

_EMPLOYMENT_LABELS = {
    "unspecified": "未設定",
    "employee": "正式員工",
    "contractor": "合約人員",
    "visiting": "訪問人員",
    "intern": "實習人員",
    "affiliate": "附屬成員",
    "other": "其他",
}


def _iso(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def official_employment_profile(actor: ActorContext) -> dict[str, object]:
    """Project formal work identity from memberships and active appointments."""

    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                WITH RECURSIVE primary_position AS (
                  SELECT pp.position_code, pp.name, pp.name_en, pp.role_name,
                         pp.department_code
                  FROM iam.membership_positions AS mp
                  JOIN iam.position_profiles AS pp
                    ON pp.tenant_id = mp.tenant_id
                   AND pp.position_code = mp.position_code
                  WHERE mp.user_id = :user_id AND mp.active AND pp.active
                  ORDER BY CASE mp.appointment_type WHEN 'primary' THEN 0 ELSE 1 END,
                           pp.role_level DESC, pp.position_code
                  LIMIT 1
                ), unit_chain AS (
                  SELECT ou.unit_code, ou.name, ou.name_en, ou.parent_unit_code,
                         ou.manager_user_id, 0 AS depth
                  FROM iam.organizational_units AS ou
                  JOIN primary_position AS pp ON pp.department_code = ou.unit_code
                  WHERE ou.active
                  UNION ALL
                  SELECT parent.unit_code, parent.name, parent.name_en,
                         parent.parent_unit_code, parent.manager_user_id,
                         child.depth + 1
                  FROM unit_chain AS child
                  JOIN iam.organizational_units AS parent
                    ON parent.unit_code = child.parent_unit_code
                  WHERE parent.active AND child.depth < 16
                )
                SELECT t.name AS company_name, t.slug AS company_slug,
                       m.created_at AS membership_created_at,
                       ep.employee_no, ep.employment_type, ep.employment_date,
                       pp.position_code, pp.name AS position_name,
                       pp.name_en AS position_name_en, pp.role_name,
                       unit.name AS department_name,
                       unit.name_en AS department_name_en,
                       COALESCE(explicit_manager.display_name, inherited_manager.display_name)
                         AS manager_name,
                       COALESCE(ep.manager_user_id, inherited_manager.id) AS manager_user_id
                FROM iam.memberships AS m
                JOIN iam.tenants AS t ON t.id = m.tenant_id
                LEFT JOIN iam.employment_profiles AS ep
                  ON ep.tenant_id = m.tenant_id AND ep.user_id = m.user_id
                LEFT JOIN primary_position AS pp ON true
                LEFT JOIN unit_chain AS unit ON unit.depth = 0
                LEFT JOIN iam.users AS explicit_manager ON explicit_manager.id = ep.manager_user_id
                LEFT JOIN LATERAL (
                  SELECT manager.id, manager.display_name
                  FROM unit_chain AS candidate
                  JOIN iam.users AS manager ON manager.id = candidate.manager_user_id
                  WHERE candidate.manager_user_id IS NOT NULL
                    AND candidate.manager_user_id <> :user_id
                  ORDER BY candidate.depth
                  LIMIT 1
                ) AS inherited_manager ON true
                WHERE m.user_id = :user_id AND m.active
                """
            ),
            {"user_id": actor.user_id},
        ).mappings().one_or_none()
        role_rows = session.execute(
            text(
                """
                SELECT role_name
                FROM (
                  SELECT pp.role_name, pp.role_level AS sort_level
                  FROM iam.membership_positions AS mp
                  JOIN iam.position_profiles AS pp
                    ON pp.tenant_id = mp.tenant_id
                   AND pp.position_code = mp.position_code
                  WHERE mp.user_id = :user_id AND mp.active AND pp.active
                  UNION
                  SELECT role.name AS role_name, role.level AS sort_level
                  FROM iam.membership_roles AS mr
                  JOIN iam.roles AS role
                    ON role.tenant_id = mr.tenant_id AND role.id = mr.role_id
                  WHERE mr.user_id = :user_id AND role.active
                ) AS formal_roles
                ORDER BY sort_level DESC, role_name
                """
            ),
            {"user_id": actor.user_id},
        ).mappings().all()

    source = dict(row) if row else {}
    employment_type_code = str(source.get("employment_type") or "unspecified")
    employment_date = source.get("employment_date") or (
        source.get("membership_created_at").date()
        if isinstance(source.get("membership_created_at"), datetime)
        else None
    )
    roles = list(dict.fromkeys(str(item["role_name"]) for item in role_rows if item["role_name"]))
    return {
        "employee_no": source.get("employee_no"),
        "company": source.get("company_name") or actor.tenant_name,
        "company_name": source.get("company_name") or actor.tenant_name,
        "company_slug": source.get("company_slug") or actor.tenant_slug,
        "department": source.get("department_name"),
        "department_name": source.get("department_name"),
        "department_name_en": source.get("department_name_en"),
        "position": source.get("position_name"),
        "position_name": source.get("position_name"),
        "position_name_en": source.get("position_name_en"),
        "position_code": source.get("position_code"),
        "roles": roles,
        "role_names": roles,
        "employment_date": _iso(employment_date),
        "joined_at": _iso(source.get("membership_created_at")),
        "employment_type_code": employment_type_code,
        "employment_type": _EMPLOYMENT_LABELS.get(employment_type_code, employment_type_code),
        "manager_user_id": str(source["manager_user_id"])
        if source.get("manager_user_id")
        else None,
        "manager_name": source.get("manager_name"),
        "employment_source": {
            "kind": "tenant_employment_projection",
            "membership_active": bool(row),
            "primary_appointment": source.get("position_code"),
        },
    }


def personnel_archive_status(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                SELECT id, record_no, status, current_version,
                       last_synced_profile_revision, pending_review_count,
                       last_synced_at, created_at, updated_at
                FROM records.personnel_files
                WHERE user_id = :user_id
                """
            ),
            {"user_id": actor.user_id},
        ).mappings().one_or_none()
    if row is None:
        return {
            "status": "none",
            "tenant": actor.tenant_slug,
            "pending_count": 0,
        }
    return {
        "status": row["status"],
        "tenant": actor.tenant_slug,
        "record_id": str(row["id"]),
        "record_no": row["record_no"],
        "version": int(row["current_version"]),
        "profile_revision": int(row["last_synced_profile_revision"]),
        "pending_count": int(row["pending_review_count"]),
        "synced_at": _iso(row["last_synced_at"]),
        "created_at": _iso(row["created_at"]),
        "updated_at": _iso(row["updated_at"]),
        "source": "records.personnel_files",
    }


def _archived_profile(profile: dict[str, object]) -> dict[str, object]:
    privacy = profile.get("privacy") if isinstance(profile.get("privacy"), dict) else {}

    def enabled(field: str, default: bool = True) -> bool:
        value = privacy.get(field)
        return value == "archive" if value in {"archive", "private"} else default

    result: dict[str, object] = {"display_name": profile.get("display_name")}
    contact = profile.get("contact") if isinstance(profile.get("contact"), dict) else {}
    archived_contact = {
        key: contact.get(key)
        for key in ("email", "phone")
        if enabled(key) and contact.get(key)
    }
    if archived_contact:
        result["contact"] = archived_contact
    for key in ("bio", "skills", "languages", "interests", "mbti", "zodiac"):
        if enabled(key, key not in {"mbti", "zodiac"}) and profile.get(key):
            result[key] = profile[key]
    if enabled("avatar") and isinstance(profile.get("avatar"), dict):
        avatar = dict(profile["avatar"])
        avatar.pop("data_url", None)
        avatar.pop("url", None)
        if avatar.get("kind") == "upload":
            avatar.pop("value", None)
        result["avatar"] = avatar
    result["privacy"] = privacy
    return result


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sync_personnel_record(
    session: Session,
    actor: ActorContext,
    *,
    profile: dict[str, object],
    profile_revision: int,
    official: dict[str, object],
) -> dict[str, object]:
    """Append one immutable restricted personnel-file version in the profile transaction."""

    personnel = session.execute(
        text(
            """
            SELECT id, record_no, status, current_version,
                   last_synced_profile_revision, pending_review_count,
                   created_at
            FROM records.personnel_files
            WHERE user_id = :user_id
            FOR UPDATE
            """
        ),
        {"user_id": actor.user_id},
    ).mappings().one_or_none()
    if personnel is None:
        raise RuntimeError("Personnel file was not provisioned for this membership")

    snapshot = {
        "schema": "warehouse.personnel-file.v1",
        "tenant": {"slug": actor.tenant_slug, "name": actor.tenant_name},
        "subject": {"user_id": str(actor.user_id), "username": actor.username},
        "profile_revision": profile_revision,
        "profile": _archived_profile(profile),
        "official": official,
    }
    serialized = _json(snapshot)
    content_hash = "sha256:" + hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    existing_version = session.execute(
        text(
            """
            SELECT version_no FROM records.personnel_file_versions
            WHERE personnel_file_id = :file_id AND profile_revision = :profile_revision
            """
        ),
        {"file_id": personnel["id"], "profile_revision": profile_revision},
    ).scalar_one_or_none()
    if existing_version is None:
        version_no = int(personnel["current_version"]) + 1
        session.execute(
            text(
                """
                INSERT INTO records.personnel_file_versions(
                  tenant_id, personnel_file_id, version_no, profile_revision,
                  snapshot, content_hash, created_by
                ) VALUES (
                  :tenant_id, :file_id, :version_no, :profile_revision,
                  CAST(:snapshot AS jsonb), :content_hash, :created_by
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "file_id": personnel["id"],
                "version_no": version_no,
                "profile_revision": profile_revision,
                "snapshot": serialized,
                "content_hash": content_hash,
                "created_by": actor.user_id,
            },
        )
    else:
        version_no = int(existing_version)

    session.execute(
        text(
            """
            UPDATE records.personnel_files
            SET status = 'active', current_version = :version_no,
                last_synced_profile_revision = :profile_revision,
                pending_review_count = 0, last_synced_at = now()
            WHERE id = :file_id
            """
        ),
        {
            "file_id": personnel["id"],
            "version_no": version_no,
            "profile_revision": profile_revision,
        },
    )

    current_payload = session.execute(
        text(
            """
            SELECT payload FROM compatibility.documents
            WHERE namespace = 'record' AND document_key = :document_key
            """
        ),
        {"document_key": f"personnel:{actor.user_id}"},
    ).scalar_one_or_none()
    current = dict(current_payload) if isinstance(current_payload, dict) else {}
    events = list(current.get("events") or [])[-99:]
    events.append(
        {
            "event_type": "profile_synchronized",
            "actor_name": actor.display_name,
            "profile_revision": profile_revision,
            "version": version_no,
        }
    )
    payload: dict[str, Any] = {
        **current,
        "id": str(personnel["id"]),
        "record_no": personnel["record_no"],
        "type_id": "personnel_record",
        "type_key": "personnel_record",
        "category_key": "personnel",
        "category_name_snapshot": "人員檔案",
        "title": f"{profile.get('display_name') or actor.display_name} · 人員檔案",
        "description": "由個人中心與正式組織資料自動同步",
        "status": "active",
        "confidentiality": "restricted",
        "subject_user_id": str(actor.user_id),
        "lock_version": version_no,
        "profile_revision": profile_revision,
        "latest_snapshot_hash": content_hash,
        "events": events,
        "documents": list(current.get("documents") or []),
        "relations": list(current.get("relations") or []),
        "created_at": current.get("created_at") or personnel["created_at"],
    }
    session.execute(
        text(
            """
            INSERT INTO compatibility.documents(
              id, tenant_id, namespace, document_key, payload, source, updated_by
            ) VALUES (
              :id, :tenant_id, 'record', :document_key,
              CAST(:payload AS jsonb), 'native', :updated_by
            )
            ON CONFLICT (tenant_id, namespace, document_key)
            DO UPDATE SET payload = EXCLUDED.payload, status = 'active',
              source = 'native', version = compatibility.documents.version + 1,
              updated_by = EXCLUDED.updated_by
            """
        ),
        {
            "id": personnel["id"],
            "tenant_id": actor.tenant_id,
            "document_key": f"personnel:{actor.user_id}",
            "payload": _json(payload),
            "updated_by": actor.user_id,
        },
    )
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (
              :tenant_id, :actor_user_id, 'records.personnel_profile.synchronized',
              CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "payload": _json(
                {
                    "personnel_file_id": str(personnel["id"]),
                    "record_no": personnel["record_no"],
                    "version": version_no,
                    "profile_revision": profile_revision,
                    "content_hash": content_hash,
                }
            ),
        },
    )
    return {
        "record_id": str(personnel["id"]),
        "record_no": personnel["record_no"],
        "version": version_no,
        "profile_revision": profile_revision,
        "status": "active",
    }
