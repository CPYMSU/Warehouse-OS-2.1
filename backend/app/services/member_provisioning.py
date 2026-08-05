"""Canonical member and tenant-role provisioning for Auto Runtime.

The model decides whether a request is a single provision, a batch import, or
an explicit RBAC-role change.  These adapters own only the atomic PostgreSQL
effects and never reinterpret an organisation position as an access role.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import tenant_session
from app.templates.industry_blueprints import BLUEPRINT_PERMISSION_KEYS

if TYPE_CHECKING:
    from app.api.deps import ActorContext


_USERNAME_RE = re.compile(r"^[^\s]{3,128}$")
_ROLE_KEY_RE = re.compile(r"^[a-z][a-z0-9_-]{1,79}$")
_ALLOWED_ORIGINS = frozenset({"auto_runtime", "manual_ui", "api", "terminal", "super_terminal"})


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _digest(value: object) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _require_manage(actor: ActorContext) -> None:
    if not {"users.manage", "settings.manage"}.intersection(actor.permissions):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing users.manage")


def _origin(value: object) -> str:
    candidate = str(value or "api").strip()
    return candidate if candidate in _ALLOWED_ORIGINS else "api"


def _strings(value: object, *, field: str) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value]
    else:
        raise HTTPException(status_code=422, detail=f"{field} must be an array")
    return list(dict.fromkeys(item for item in items if item))


def _member_input(payload: Mapping[str, object], *, index: int | None = None) -> dict[str, object]:
    username = (
        str(payload.get("username") or payload.get("account") or payload.get("email") or "")
        .strip()
        .lower()
    )
    display_name = str(payload.get("display_name") or payload.get("name") or username).strip()
    password = str(payload.get("password") or "")
    if not _USERNAME_RE.fullmatch(username):
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_username", "index": index, "username": username},
        )
    if not display_name:
        raise HTTPException(
            status_code=422,
            detail={"reason": "display_name_required", "index": index},
        )
    if not 8 <= len(password) <= 512:
        raise HTTPException(
            status_code=422,
            detail={"reason": "password_length", "index": index, "minimum": 8},
        )
    return {
        "username": username,
        "display_name": display_name,
        "password": password,
        "department_ref": str(
            payload.get("department")
            or payload.get("department_ref")
            or payload.get("department_id")
            or ""
        ).strip(),
        "position_ref": str(
            payload.get("position")
            or payload.get("position_ref")
            or payload.get("position_id")
            or ""
        ).strip(),
        "access_role_ref": str(
            payload.get("access_role") or payload.get("access_role_ref") or ""
        ).strip(),
        "index": index,
    }


def _unique_row(
    rows: list[Mapping[str, object]],
    *,
    kind: str,
    reference: str,
    index: int | None,
) -> dict[str, object]:
    if not rows:
        raise HTTPException(
            status_code=404,
            detail={"reason": f"{kind}_not_found", "ref": reference, "index": index},
        )
    if len(rows) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": f"{kind}_ambiguous",
                "ref": reference,
                "index": index,
                "matches": len(rows),
            },
        )
    return dict(rows[0])


def _department(session: Session, reference: str, index: int | None) -> dict[str, object]:
    rows = (
        session.execute(
            text(
                """
            SELECT id,unit_code,name,unit_type,active
            FROM iam.organizational_units
            WHERE active AND unit_type<>'company' AND (
              id::text=:ref OR lower(unit_code)=lower(:ref) OR lower(name)=lower(:ref)
            )
            ORDER BY unit_code LIMIT 3
            """
            ),
            {"ref": reference},
        )
        .mappings()
        .all()
    )
    return _unique_row(rows, kind="department", reference=reference, index=index)


def _position(session: Session, reference: str, index: int | None) -> dict[str, object]:
    rows = (
        session.execute(
            text(
                """
            SELECT p.id,p.position_code,p.department_code,p.name,p.role_name,
                   p.role_level,p.is_manager,p.permissions,
                   unit.id AS department_id,unit.name AS department_name
            FROM iam.position_profiles AS p
            JOIN iam.organizational_units AS unit
              ON unit.unit_code=p.department_code AND unit.active
            WHERE p.active AND (
              p.id::text=:ref OR lower(p.position_code)=lower(:ref)
              OR lower(p.name)=lower(:ref) OR lower(p.role_name)=lower(:ref)
            )
            ORDER BY p.role_level DESC,p.position_code LIMIT 3
            """
            ),
            {"ref": reference},
        )
        .mappings()
        .all()
    )
    return _unique_row(rows, kind="position", reference=reference, index=index)


def _access_role(session: Session, reference: str, index: int | None) -> dict[str, object]:
    rows = (
        session.execute(
            text(
                """
            SELECT id,role_key,name,level
            FROM iam.roles
            WHERE active AND (
              id::text=:ref OR lower(role_key)=lower(:ref) OR lower(name)=lower(:ref)
            )
            ORDER BY level DESC,role_key LIMIT 3
            """
            ),
            {"ref": reference},
        )
        .mappings()
        .all()
    )
    return _unique_row(rows, kind="access_role", reference=reference, index=index)


def _prepare_member(session: Session, item: dict[str, object]) -> dict[str, object]:
    index = item.get("index")
    username = str(item["username"])
    if session.execute(
        text("SELECT 1 FROM iam.users WHERE lower(username)=lower(:username)"),
        {"username": username},
    ).scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail={"reason": "username_exists", "username": username, "index": index},
        )

    department = None
    position = None
    role = None
    if item["department_ref"]:
        department = _department(session, str(item["department_ref"]), index)
    if item["position_ref"]:
        position = _position(session, str(item["position_ref"]), index)
        if department and position["department_code"] != department["unit_code"]:
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "position_department_mismatch",
                    "index": index,
                    "position": position["name"],
                    "department": department["name"],
                },
            )
        if department is None:
            department = {
                "id": position["department_id"],
                "unit_code": position["department_code"],
                "name": position["department_name"],
            }
    elif department is not None:
        raise HTTPException(
            status_code=422,
            detail={
                "reason": "position_required_for_department_membership",
                "index": index,
                "department": department["name"],
            },
        )
    if item["access_role_ref"]:
        role = _access_role(session, str(item["access_role_ref"]), index)
    return {**item, "department": department, "position": position, "access_role": role}


def _insert_member(
    session: Session, actor: ActorContext, item: dict[str, object]
) -> dict[str, object]:
    user_id = uuid4()
    position = item["position"]
    role = item["access_role"]
    position_level = int(position["role_level"]) if position else 1
    role_level = int(role["level"]) if role else 1
    level = max(position_level, role_level)
    title = str(position["name"]) if position else str(role["name"]) if role else "Member"
    position_code = str(position["position_code"]) if position else None
    session.execute(
        text(
            """
            INSERT INTO iam.users(id,username,display_name,password_hash)
            VALUES (:id,:username,:display_name,:password_hash)
            """
        ),
        {
            "id": user_id,
            "username": item["username"],
            "display_name": item["display_name"],
            "password_hash": hash_password(str(item["password"])),
        },
    )
    session.execute(
        text(
            """
            INSERT INTO iam.memberships(
              tenant_id,user_id,position_code,role_level,topology_level,topology_title
            ) VALUES (
              :tenant_id,:user_id,:position_code,:level,:level,:title
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "user_id": user_id,
            "position_code": position_code,
            "level": level,
            "title": title,
        },
    )
    if position_code:
        session.execute(
            text(
                """
                INSERT INTO iam.membership_positions(
                  tenant_id,user_id,position_code,appointment_type,active
                ) VALUES (:tenant_id,:user_id,:position_code,'primary',true)
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "user_id": user_id,
                "position_code": position_code,
            },
        )
    if role:
        session.execute(
            text(
                """
                INSERT INTO iam.membership_roles(tenant_id,user_id,role_id)
                VALUES (:tenant_id,:user_id,:role_id)
                """
            ),
            {"tenant_id": actor.tenant_id, "user_id": user_id, "role_id": role["id"]},
        )
    result = {
        "user_id": str(user_id),
        "username": item["username"],
        "display_name": item["display_name"],
        "department": (
            {
                "id": str(item["department"]["id"]),
                "unit_code": item["department"]["unit_code"],
                "name": item["department"]["name"],
            }
            if item["department"]
            else None
        ),
        "position": (
            {
                "id": str(position["id"]),
                "position_code": position["position_code"],
                "name": position["name"],
                "role_name": position["role_name"],
                "role_level": int(position["role_level"]),
            }
            if position
            else None
        ),
        "access_role": (
            {
                "id": str(role["id"]),
                "role_key": role["role_key"],
                "name": role["name"],
                "level": int(role["level"]),
            }
            if role
            else None
        ),
        "role_level": level,
    }
    readback = (
        session.execute(
            text(
                """
            SELECT u.id,u.username,u.display_name,m.position_code,m.role_level,
                   m.topology_title,mp.appointment_type
            FROM iam.users AS u
            JOIN iam.memberships AS m ON m.user_id=u.id AND m.tenant_id=:tenant_id
            LEFT JOIN iam.membership_positions AS mp
              ON mp.user_id=u.id AND mp.tenant_id=m.tenant_id AND mp.active
            WHERE u.id=:user_id AND u.active AND m.active
            """
            ),
            {"tenant_id": actor.tenant_id, "user_id": user_id},
        )
        .mappings()
        .one()
    )
    if str(readback["username"]) != item["username"] or readback["position_code"] != position_code:
        raise RuntimeError("member provisioning readback disagrees with requested state")
    return result


def _business_event(
    session: Session,
    actor: ActorContext,
    *,
    tool_name: str,
    resource_type: str,
    entity_key: str,
    request_key: str,
    result: dict[str, object],
    origin: str,
) -> str:
    event_id = uuid4()
    session.execute(
        text(
            """
            INSERT INTO business.events(
              id,tenant_id,tool_name,resource_type,entity_key,operation,
              request_key,confirmation_mode,origin,after_payload,actor_user_id
            ) VALUES (
              :id,:tenant_id,:tool_name,:resource_type,:entity_key,:operation,
              :request_key,'passkey',:origin,CAST(:payload AS jsonb),:actor_user_id
            )
            """
        ),
        {
            "id": event_id,
            "tenant_id": actor.tenant_id,
            "tool_name": tool_name,
            "resource_type": resource_type,
            "entity_key": entity_key,
            "operation": tool_name.replace("_", "."),
            "request_key": request_key,
            "origin": _origin(origin),
            "payload": _json(result),
            "actor_user_id": actor.user_id,
        },
    )
    return str(event_id)


def _replay(
    session: Session, actor: ActorContext, tool_name: str, request_key: str
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
            SELECT id,after_payload FROM business.events
            WHERE tenant_id=:tenant_id AND tool_name=:tool_name AND request_key=:request_key
            """
            ),
            {"tenant_id": actor.tenant_id, "tool_name": tool_name, "request_key": request_key},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return {
        "ok": True,
        **dict(row["after_payload"] or {}),
        "event_id": str(row["id"]),
        "idempotent_replay": True,
        "effect_verified": True,
    }


def provision_member_account(
    actor: ActorContext,
    payload: Mapping[str, object],
    *,
    origin: str = "api",
) -> dict[str, object]:
    _require_manage(actor)
    item = _member_input(payload)
    request_key = _digest(
        {
            key: item[key]
            for key in (
                "username",
                "display_name",
                "department_ref",
                "position_ref",
                "access_role_ref",
            )
        }
    )
    with tenant_session(actor.tenant_id) as session:
        replay = _replay(session, actor, "user_add", request_key)
        if replay is not None:
            return replay
        prepared = _prepare_member(session, item)
        member = _insert_member(session, actor, prepared)
        result = {
            "member": member,
            "tenant_id": str(actor.tenant_id),
            "transaction_committed": True,
            "readback_verified": True,
        }
        event_id = _business_event(
            session,
            actor,
            tool_name="user_add",
            resource_type="iam.member",
            entity_key=member["user_id"],
            request_key=request_key,
            result=result,
            origin=origin,
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
                VALUES (:tenant_id,:actor_user_id,'iam.member.provisioned',CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": _json(
                    {
                        "user_id": member["user_id"],
                        "username": member["username"],
                        "position_code": (member["position"] or {}).get("position_code"),
                    }
                ),
            },
        )
    return {
        "ok": True,
        **result,
        "event_id": event_id,
        "idempotent_replay": False,
        "effect_verified": True,
    }


def import_member_accounts(
    actor: ActorContext,
    payload: Mapping[str, object],
    *,
    origin: str = "api",
) -> dict[str, object]:
    _require_manage(actor)
    raw_members = payload.get("members")
    if not isinstance(raw_members, list) or not 1 <= len(raw_members) <= 200:
        raise HTTPException(status_code=422, detail="members must contain 1-200 objects")
    items = [
        _member_input(member, index=index)
        if isinstance(member, Mapping)
        else (_raise_member_object(index))
        for index, member in enumerate(raw_members)
    ]
    usernames = [str(item["username"]) for item in items]
    duplicates = sorted({name for name in usernames if usernames.count(name) > 1})
    if duplicates:
        raise HTTPException(
            status_code=422,
            detail={"reason": "duplicate_usernames_in_batch", "usernames": duplicates},
        )
    request_key = str(payload.get("request_id") or "").strip() or _digest(
        [
            {
                key: item[key]
                for key in (
                    "username",
                    "display_name",
                    "department_ref",
                    "position_ref",
                    "access_role_ref",
                )
            }
            for item in items
        ]
    )
    with tenant_session(actor.tenant_id) as session:
        replay = _replay(session, actor, "user_import", request_key)
        if replay is not None:
            return replay
        prepared = [_prepare_member(session, item) for item in items]
        members = [_insert_member(session, actor, item) for item in prepared]
        result = {
            "members": members,
            "created_count": len(members),
            "tenant_id": str(actor.tenant_id),
            "transaction_committed": True,
            "readback_verified": True,
        }
        event_id = _business_event(
            session,
            actor,
            tool_name="user_import",
            resource_type="iam.member_batch",
            entity_key=request_key[:240],
            request_key=request_key[:240],
            result=result,
            origin=origin,
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
                VALUES (
                  :tenant_id,:actor_user_id,'iam.member.batch_imported',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": _json(
                    {
                        "created_count": len(members),
                        "user_ids": [member["user_id"] for member in members],
                    }
                ),
            },
        )
    return {
        "ok": True,
        **result,
        "event_id": event_id,
        "idempotent_replay": False,
        "effect_verified": True,
    }


def _raise_member_object(index: int) -> dict[str, object]:
    raise HTTPException(
        status_code=422,
        detail={"reason": "member_must_be_object", "index": index},
    )


def _permissions(value: object) -> list[str]:
    permissions = _strings(value, field="permissions")
    invalid = sorted(set(permissions) - set(BLUEPRINT_PERMISSION_KEYS))
    if invalid:
        raise HTTPException(
            status_code=422,
            detail={"reason": "invalid_permissions", "permissions": invalid},
        )
    return permissions


def _role_readback(session: Session, role_id: object) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
            SELECT role.id,role.role_key,role.name,role.level,role.active,
                   COALESCE(array_agg(permission.permission_key ORDER BY permission.permission_key)
                     FILTER (WHERE permission.permission_key IS NOT NULL),'{}') AS permissions
            FROM iam.roles AS role
            LEFT JOIN iam.role_permissions AS permission ON permission.role_id=role.id
            WHERE role.id=:role_id
            GROUP BY role.id
            """
            ),
            {"role_id": role_id},
        )
        .mappings()
        .one()
    )
    return {
        "id": str(row["id"]),
        "role_key": row["role_key"],
        "name": row["name"],
        "level": int(row["level"]),
        "active": bool(row["active"]),
        "permissions": list(row["permissions"] or []),
    }


def upsert_access_role(
    actor: ActorContext,
    payload: Mapping[str, object],
    *,
    origin: str = "api",
    _capability: str = "role_upsert",
) -> dict[str, object]:
    _require_manage(actor)
    if _capability not in {"role_upsert", "role_update"}:
        raise RuntimeError("invalid internal role capability")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Role name is required")
    try:
        level = int(payload.get("level") or 1)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Role level must be an integer") from exc
    if not 1 <= level <= 10:
        raise HTTPException(status_code=422, detail="Role level must be between 1 and 10")
    permissions = _permissions(payload.get("permissions"))
    requested_key = str(payload.get("role_key") or "").strip().lower()
    role_key = requested_key or f"custom_{_digest(name)[:16]}"
    if not _ROLE_KEY_RE.fullmatch(role_key):
        raise HTTPException(status_code=422, detail="Invalid role key")
    request_key = _digest(
        {"name": name, "role_key": role_key, "level": level, "permissions": permissions}
    )
    with tenant_session(actor.tenant_id) as session:
        replay = _replay(session, actor, _capability, request_key)
        if replay is not None:
            return replay
        existing = (
            session.execute(
                text(
                    """
                SELECT id FROM iam.roles
                WHERE lower(role_key)=lower(:role_key) OR lower(name)=lower(:name)
                ORDER BY created_at LIMIT 2
                """
                ),
                {"role_key": role_key, "name": name},
            )
            .scalars()
            .all()
        )
        if len(existing) > 1:
            raise HTTPException(status_code=409, detail="Role name or key is ambiguous")
        role_id = existing[0] if existing else uuid4()
        if existing:
            session.execute(
                text(
                    """
                    UPDATE iam.roles SET role_key=:role_key,name=:name,level=:level,
                      active=true,updated_at=now() WHERE id=:id
                    """
                ),
                {"id": role_id, "role_key": role_key, "name": name, "level": level},
            )
        else:
            session.execute(
                text(
                    """
                    INSERT INTO iam.roles(id,tenant_id,role_key,name,level)
                    VALUES (:id,:tenant_id,:role_key,:name,:level)
                    """
                ),
                {
                    "id": role_id,
                    "tenant_id": actor.tenant_id,
                    "role_key": role_key,
                    "name": name,
                    "level": level,
                },
            )
        session.execute(text("DELETE FROM iam.role_permissions WHERE role_id=:id"), {"id": role_id})
        for permission in permissions:
            session.execute(
                text(
                    """
                    INSERT INTO iam.role_permissions(tenant_id,role_id,permission_key)
                    VALUES (:tenant_id,:role_id,:permission)
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "role_id": role_id,
                    "permission": permission,
                },
            )
        role = _role_readback(session, role_id)
        result = {"role": role, "transaction_committed": True, "readback_verified": True}
        event_id = _business_event(
            session,
            actor,
            tool_name=_capability,
            resource_type="iam.role",
            entity_key=str(role_id),
            request_key=request_key,
            result=result,
            origin=origin,
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
                VALUES (:tenant_id,:actor_user_id,:event_type,CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "event_type": (
                    "iam.role.updated" if _capability == "role_update" else "iam.role.upserted"
                ),
                "payload": _json(role),
            },
        )
    return {
        "ok": True,
        **result,
        "event_id": event_id,
        "idempotent_replay": False,
        "effect_verified": True,
    }


def update_access_role(
    actor: ActorContext,
    role_ref: str,
    payload: Mapping[str, object],
    *,
    origin: str = "api",
) -> dict[str, object]:
    _require_manage(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id,role_key,name,level FROM iam.roles WHERE active AND (
                  id::text=:ref OR lower(role_key)=lower(:ref) OR lower(name)=lower(:ref)
                ) ORDER BY created_at LIMIT 3
                """
                ),
                {"ref": role_ref},
            )
            .mappings()
            .all()
        )
        current = _unique_row(rows, kind="access_role", reference=role_ref, index=None)
    merged = {
        "role_key": payload.get("role_key") or current["role_key"],
        "name": payload.get("name") or current["name"],
        "level": payload.get("level") or current["level"],
        "permissions": payload.get("permissions") if "permissions" in payload else [],
    }
    if "permissions" not in payload:
        with tenant_session(actor.tenant_id) as session:
            merged["permissions"] = (
                session.execute(
                    text(
                        """
                        SELECT permission_key FROM iam.role_permissions
                        WHERE role_id=:id ORDER BY permission_key
                        """
                    ),
                    {"id": current["id"]},
                )
                .scalars()
                .all()
            )
    return upsert_access_role(actor, merged, origin=origin, _capability="role_update")
