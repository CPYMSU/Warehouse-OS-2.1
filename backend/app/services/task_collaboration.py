"""Tenant-scoped task collaboration adapted from the Warehouse 2.0 contract.

The HTTP shape intentionally remains compatible with the existing TASK UI,
while persistence, authority and audit are native PostgreSQL/RLS concerns.
"""

from __future__ import annotations

import json
import re
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session

_DISCOVERABILITIES = frozenset({"team", "company", "hidden"})
_JOIN_POLICIES = frozenset({"open", "request", "invite_only"})
_MEMBER_ROLES = frozenset({"owner", "coordinator", "contributor", "reviewer", "observer"})
_INVITABLE_ROLES = frozenset({"coordinator", "contributor", "reviewer", "observer"})
_REQUEST_ROLES = frozenset({"contributor", "reviewer", "observer"})
_TERMINAL_STATUSES = frozenset({"completed", "cancelled"})
_CLIENT_MESSAGE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")


def _permission(actor: ActorContext, *keys: str) -> bool:
    return actor.role_level >= 10 or any(key in actor.permissions for key in keys)


def _uuid(value: object, label: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label}",
        ) from exc


def _choice(value: object | None, allowed: frozenset[str], label: str, default: str) -> str:
    result = str(value or default).strip()
    if result not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label}",
        )
    return result


def _clean(
    value: object | None,
    label: str,
    maximum: int,
    *,
    required: bool = False,
) -> str | None:
    result = "" if value is None else str(value).strip()
    if required and not result:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} is required",
        )
    if len(result) > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} must be at most {maximum} characters",
        )
    return result or None


def _task(session: Session, task_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT id, created_by, title, description, status, priority, visibility,
                       due_at, start_at, end_at, owner_org_unit_id, version,
                       created_at, updated_at
                FROM workflow.tasks WHERE id = :task_id
                """
            ),
            {"task_id": task_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return dict(row)


def _space(session: Session, task_id: UUID, *, required: bool = True) -> dict[str, object] | None:
    row = (
        session.execute(
            text("SELECT * FROM workflow.task_collaboration_spaces WHERE task_id = :task_id"),
            {"task_id": task_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        if required:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task collaboration workspace not found",
            )
        return None
    return dict(row)


def _member(
    session: Session, space_id: UUID, user_id: UUID, *, active: bool = True
) -> dict[str, object] | None:
    state_clause = "AND m.state = 'active'" if active else ""
    row = (
        session.execute(
            text(
                f"""
                SELECT m.*, u.username, u.display_name
                FROM workflow.task_collaboration_members AS m
                JOIN iam.users AS u ON u.id = m.user_id
                WHERE m.space_id = :space_id AND m.user_id = :user_id {state_clause}
                """
            ),
            {"space_id": space_id, "user_id": user_id},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def _require_member(session: Session, space_id: UUID, user_id: UUID) -> dict[str, object]:
    membership = _member(session, space_id, user_id)
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Workspace membership required"
        )
    return membership


def _task_participant(session: Session, task: dict[str, object], user_id: UUID) -> bool:
    if task["created_by"] == user_id:
        return True
    return bool(
        session.execute(
            text(
                """
                SELECT 1 FROM workflow.task_assignees
                WHERE task_id = :task_id AND user_id = :user_id
                """
            ),
            {"task_id": task["id"], "user_id": user_id},
        ).scalar_one_or_none()
    )


def _same_team(session: Session, task: dict[str, object], user_id: UUID) -> bool:
    unit_id = task.get("owner_org_unit_id")
    if unit_id is None:
        return False
    return bool(
        session.execute(
            text(
                """
                SELECT 1
                FROM iam.membership_positions AS mp
                JOIN iam.position_profiles AS pp
                  ON pp.position_code = mp.position_code AND pp.tenant_id = mp.tenant_id
                JOIN iam.organizational_units AS ou
                  ON ou.unit_code = pp.department_code AND ou.tenant_id = pp.tenant_id
                WHERE mp.user_id = :user_id AND mp.active AND ou.id = :unit_id
                """
            ),
            {"user_id": user_id, "unit_id": unit_id},
        ).scalar_one_or_none()
    )


def _task_visible(session: Session, actor: ActorContext, task: dict[str, object]) -> bool:
    if _permission(actor, "tasks.manage") or _task_participant(session, task, actor.user_id):
        return True
    if task["visibility"] == "company":
        return True
    return task["visibility"] == "team" and _same_team(session, task, actor.user_id)


def _task_manageable(session: Session, actor: ActorContext, task: dict[str, object]) -> bool:
    return bool(
        _permission(actor, "tasks.manage")
        or task["created_by"] == actor.user_id
        or _task_participant(session, task, actor.user_id)
    )


def _discoverable(
    session: Session,
    actor: ActorContext,
    task: dict[str, object],
    space: dict[str, object],
) -> bool:
    discoverability = str(space["discoverability"])
    if discoverability == "hidden" or not _task_visible(session, actor, task):
        return False
    if discoverability == "company":
        return True
    return _task_participant(session, task, actor.user_id) or _same_team(
        session, task, actor.user_id
    )


def _writable(task: dict[str, object]) -> None:
    if task["status"] in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Completed or cancelled tasks are read-only",
        )


def _is_manager(actor: ActorContext, membership: dict[str, object] | None) -> bool:
    return bool(
        membership
        and membership["state"] == "active"
        and (
            membership["role"] in {"owner", "coordinator"}
            or _permission(actor, "tasks.collaboration.manage", "tasks.manage")
        )
    )


def _require_manager(
    session: Session, actor: ActorContext, space: dict[str, object]
) -> dict[str, object]:
    membership = _member(session, UUID(str(space["id"])), actor.user_id)
    if not _is_manager(actor, membership):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Collaboration management permission denied",
        )
    return membership or {}


def _event(
    session: Session,
    actor: ActorContext,
    space: dict[str, object],
    event_type: str,
    *,
    subject_user_id: UUID | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    session.execute(
        text(
            """
            INSERT INTO workflow.task_collaboration_events(
              tenant_id, space_id, task_id, event_type, actor_user_id,
              subject_user_id, payload
            ) VALUES (
              :tenant_id, :space_id, :task_id, :event_type, :actor_user_id,
              :subject_user_id, CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "space_id": space["id"],
            "task_id": space["task_id"],
            "event_type": event_type,
            "actor_user_id": actor.user_id,
            "subject_user_id": subject_user_id,
            "payload": json.dumps(payload or {}, ensure_ascii=False, default=str),
        },
    )


def _audit(
    session: Session, actor: ActorContext, event_type: str, payload: dict[str, object]
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
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _member_view(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "display_name": row.get("display_name") or row.get("username"),
        "username": row.get("username"),
        "role": row.get("role"),
        "state": row.get("state"),
        "joined_at": row.get("joined_at"),
        "left_at": row.get("left_at"),
        "updated_at": row.get("updated_at"),
    }


def _request_view(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "display_name": row.get("display_name") or row.get("username"),
        "username": row.get("username"),
        "requested_role": row.get("requested_role"),
        "message": row.get("message"),
        "status": row.get("status"),
        "decided_by_user_id": (
            str(row["decided_by_user_id"]) if row.get("decided_by_user_id") else None
        ),
        "decided_at": row.get("decided_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def _invitation_view(row: dict[str, object], viewer_user_id: UUID) -> dict[str, object]:
    return {
        "id": str(row["id"]),
        "user_id": str(row["user_id"]),
        "display_name": row.get("display_name") or row.get("username"),
        "username": row.get("username"),
        "role": row.get("role"),
        "message": row.get("message"),
        "status": row.get("status"),
        "invited_by_user_id": str(row["invited_by_user_id"]),
        "invited_by_name": row.get("invited_by_name") or row.get("invited_by_username"),
        "responded_at": row.get("responded_at"),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
        "for_viewer": row["user_id"] == viewer_user_id,
    }


def _task_view(task: dict[str, object], *, redacted: bool = False) -> dict[str, object]:
    if redacted:
        return {
            "id": str(task["id"]),
            "title": None,
            "visibility": task["visibility"],
            "redacted": True,
        }
    return {
        key: task.get(key)
        for key in (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "visibility",
            "due_at",
            "start_at",
            "end_at",
            "owner_org_unit_id",
            "created_by",
        )
    } | {
        "id": str(task["id"]),
        "created_by_user_id": str(task["created_by"]),
        "read_only": task["status"] in _TERMINAL_STATUSES,
    }


def _active_member_count(session: Session, space_id: UUID) -> int:
    return int(
        session.execute(
            text(
                """
                SELECT count(*) FROM workflow.task_collaboration_members
                WHERE space_id = :space_id AND state = 'active'
                """
            ),
            {"space_id": space_id},
        ).scalar_one()
    )


def _space_view(
    session: Session,
    space: dict[str, object],
    membership: dict[str, object] | None = None,
) -> dict[str, object]:
    owner = (
        session.execute(
            text(
                """
                SELECT m.user_id, u.username, u.display_name
                FROM workflow.task_collaboration_members AS m
                JOIN iam.users AS u ON u.id = m.user_id
                WHERE m.space_id = :space_id AND m.state = 'active' AND m.role = 'owner'
                """
            ),
            {"space_id": space["id"]},
        )
        .mappings()
        .one_or_none()
    )
    return {
        "id": str(space["id"]),
        "task_id": str(space["task_id"]),
        "join_policy": space["join_policy"],
        "discoverability": space["discoverability"],
        "max_members": space.get("max_members"),
        "member_count": _active_member_count(session, UUID(str(space["id"]))),
        "created_by_user_id": str(space["created_by_user_id"]),
        "owner": (
            {
                "user_id": str(owner["user_id"]),
                "display_name": owner["display_name"] or owner["username"],
                "username": owner["username"],
            }
            if owner
            else None
        ),
        "membership": _member_view(membership) if membership else None,
        "created_at": space["created_at"],
        "updated_at": space["updated_at"],
    }


def _pending_request(session: Session, space_id: UUID, user_id: UUID) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT r.*, u.username, u.display_name
                FROM workflow.task_collaboration_join_requests AS r
                JOIN iam.users AS u ON u.id = r.user_id
                WHERE r.space_id = :space_id AND r.user_id = :user_id AND r.status = 'pending'
                """
            ),
            {"space_id": space_id, "user_id": user_id},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def _pending_invitation(
    session: Session, space_id: UUID, user_id: UUID
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT i.*, u.username, u.display_name,
                       inviter.username AS invited_by_username,
                       inviter.display_name AS invited_by_name
                FROM workflow.task_collaboration_invitations AS i
                JOIN iam.users AS u ON u.id = i.user_id
                JOIN iam.users AS inviter ON inviter.id = i.invited_by_user_id
                WHERE i.space_id = :space_id AND i.user_id = :user_id AND i.status = 'pending'
                """
            ),
            {"space_id": space_id, "user_id": user_id},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def _capabilities(
    session: Session,
    actor: ActorContext,
    task: dict[str, object],
    space: dict[str, object],
    *,
    membership: dict[str, object] | None = None,
    request: dict[str, object] | None = None,
    invitation: dict[str, object] | None = None,
    discoverable: bool = False,
) -> dict[str, bool]:
    active = bool(membership and membership["state"] == "active")
    read_only = task["status"] in _TERMINAL_STATUSES
    full = bool(
        space.get("max_members") is not None
        and _active_member_count(session, UUID(str(space["id"]))) >= int(space["max_members"])
    )
    available = bool(
        discoverable
        and not active
        and not request
        and not invitation
        and not read_only
        and not full
    )
    manager = _is_manager(actor, membership)
    role = membership.get("role") if membership else None
    return {
        "can_transfer_ownership": bool(active and role == "owner" and not read_only),
        "can_manage": bool(manager and not read_only),
        "can_approve_requests": bool(manager and not read_only),
        "can_reject_requests": bool(manager),
        "can_join": bool(available and space["join_policy"] == "open"),
        "can_request": bool(available and space["join_policy"] == "request"),
        "can_send": bool(active and not read_only and role != "observer"),
        "can_leave": bool(active and role != "owner"),
        "can_read": active,
        "can_respond_invitation": bool(invitation and not active),
        "can_accept_invitation": bool(invitation and not active and not read_only and not full),
        "can_decline_invitation": bool(invitation and not active),
        "read_only": read_only,
        "is_full": full,
        "rtc_available": False,
        "can_join_meeting": False,
        "can_share_screen": False,
        "can_use_camera": False,
        "can_use_document": active,
    }


def _activate_member(
    session: Session,
    actor: ActorContext,
    space: dict[str, object],
    user_id: UUID,
    role: str,
) -> dict[str, object]:
    existing = _member(session, UUID(str(space["id"])), user_id, active=False)
    if existing:
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_members
                SET role = :role, state = 'active', joined_at = now(), left_at = NULL
                WHERE id = :id
                """
            ),
            {"id": existing["id"], "role": role},
        )
    else:
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_members(
                  id, tenant_id, space_id, user_id, role
                ) VALUES (:id, :tenant_id, :space_id, :user_id, :role)
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "space_id": space["id"],
                "user_id": user_id,
                "role": role,
            },
        )
    activated = _member(session, UUID(str(space["id"])), user_id)
    if activated is None:
        raise HTTPException(status_code=500, detail="Unable to activate workspace member")
    return activated


def _general_channel(session: Session, space_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
                SELECT * FROM workflow.task_collaboration_channels
                WHERE space_id = :space_id AND name = 'general'
                """
            ),
            {"space_id": space_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=500, detail="Workspace general channel is unavailable")
    return dict(row)


def discover_spaces(actor: ActorContext, params: dict[str, object]) -> dict[str, object]:
    try:
        limit = min(100, max(1, int(params.get("limit") or 30)))
        offset = max(0, int(params.get("cursor") or 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid collaboration cursor") from exc
    query = str(params.get("q") or "").strip().casefold()
    visibility_filter = params.get("discoverability")
    if visibility_filter not in (None, ""):
        visibility_filter = _choice(
            visibility_filter, _DISCOVERABILITIES, "discoverability", "team"
        )
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT s.*,
                           t.created_by, t.title, t.description, t.status, t.priority,
                           t.visibility, t.due_at, t.start_at, t.end_at,
                           t.owner_org_unit_id, t.version, t.created_at AS task_created_at,
                           t.updated_at AS task_updated_at
                    FROM workflow.task_collaboration_spaces AS s
                    JOIN workflow.tasks AS t ON t.id = s.task_id
                    ORDER BY s.created_at DESC, s.id DESC
                    OFFSET :offset LIMIT 501
                    """
                ),
                {"offset": offset},
            )
            .mappings()
            .all()
        )
        found: list[dict[str, object]] = []
        scanned = 0
        for raw in rows:
            scanned += 1
            space = dict(raw)
            task = {
                "id": raw["task_id"],
                "created_by": raw["created_by"],
                "title": raw["title"],
                "description": raw["description"],
                "status": raw["status"],
                "priority": raw["priority"],
                "visibility": raw["visibility"],
                "due_at": raw["due_at"],
                "start_at": raw["start_at"],
                "end_at": raw["end_at"],
                "owner_org_unit_id": raw["owner_org_unit_id"],
                "version": raw["version"],
                "created_at": raw["task_created_at"],
                "updated_at": raw["task_updated_at"],
            }
            membership = _member(session, UUID(str(space["id"])), actor.user_id)
            request = _pending_request(session, UUID(str(space["id"])), actor.user_id)
            invitation = _pending_invitation(session, UUID(str(space["id"])), actor.user_id)
            relation = (
                "member"
                if membership
                else "requested"
                if request
                else "invited"
                if invitation
                else "available"
            )
            acl_visible = _task_visible(session, actor, task)
            can_discover = _discoverable(session, actor, task, space)
            if visibility_filter and space["discoverability"] != visibility_filter:
                continue
            if not acl_visible and not invitation:
                continue
            if relation == "available" and not can_discover:
                continue
            redacted = not acl_visible
            if query and (redacted or query not in str(task["title"] or "").casefold()):
                continue
            found.append(
                {
                    "task_id": str(task["id"]),
                    "task": _task_view(task, redacted=redacted),
                    "space": _space_view(session, space, membership)
                    if not redacted
                    else {
                        "id": str(space["id"]),
                        "task_id": str(space["task_id"]),
                        "join_policy": space["join_policy"],
                        "discoverability": space["discoverability"],
                        "max_members": space["max_members"],
                        "member_count": _active_member_count(session, UUID(str(space["id"]))),
                        "redacted": True,
                    },
                    "relation": relation,
                    "membership": _member_view(membership) if membership else None,
                    "join_request": _request_view(request) if request else None,
                    "invitation": _invitation_view(invitation, actor.user_id)
                    if invitation
                    else None,
                    "capabilities": _capabilities(
                        session,
                        actor,
                        task,
                        space,
                        membership=membership,
                        request=request,
                        invitation=invitation,
                        discoverable=can_discover,
                    ),
                }
            )
            if len(found) >= limit:
                break
        has_more = scanned < len(rows) or len(rows) == 501
        return {
            "items": found,
            "next_cursor": offset + scanned if has_more and scanned else None,
        }


def get_space(actor: ActorContext, task_id: str) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, target_id)
        space = _space(session, target_id)
        assert space is not None
        space_id = UUID(str(space["id"]))
        membership = _member(session, space_id, actor.user_id)
        request = _pending_request(session, space_id, actor.user_id)
        invitation = _pending_invitation(session, space_id, actor.user_id)
        visible = _task_visible(session, actor, task)
        can_discover = _discoverable(session, actor, task, space)
        if not membership and not invitation and not (visible and (can_discover or request)):
            raise HTTPException(status_code=404, detail="Task collaboration workspace not found")
        capabilities = _capabilities(
            session,
            actor,
            task,
            space,
            membership=membership,
            request=request,
            invitation=invitation,
            discoverable=can_discover,
        )
        relation = (
            "member"
            if membership
            else "invited"
            if invitation
            else "requested"
            if request
            else "available"
        )
        result: dict[str, object] = {
            "viewer_user_id": str(actor.user_id),
            "membership": _member_view(membership) if membership else None,
            "relation": relation,
            "space": _space_view(session, space, membership),
            "task": _task_view(task, redacted=not visible),
            "members": [],
            "channels": [],
            "join_requests": [_request_view(request)] if request else [],
            "invitations": [_invitation_view(invitation, actor.user_id)] if invitation else [],
            "invite_candidates": [],
            "capabilities": capabilities,
        }
        if not membership:
            return result
        result["members"] = [
            _member_view(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT m.*, u.username, u.display_name
                    FROM workflow.task_collaboration_members AS m
                    JOIN iam.users AS u ON u.id = m.user_id
                    WHERE m.space_id = :space_id AND m.state = 'active'
                    ORDER BY CASE m.role WHEN 'owner' THEN 0 WHEN 'coordinator' THEN 1
                      WHEN 'contributor' THEN 2 WHEN 'reviewer' THEN 3 ELSE 4 END,
                      m.joined_at
                    """
                ),
                {"space_id": space_id},
            ).mappings()
        ]
        result["channels"] = [
            {
                **dict(row),
                "id": str(row["id"]),
                "space_id": str(row["space_id"]),
            }
            for row in session.execute(
                text(
                    """
                    SELECT id, space_id, name, display_name, channel_type, created_at
                    FROM workflow.task_collaboration_channels
                    WHERE space_id = :space_id ORDER BY created_at
                    """
                ),
                {"space_id": space_id},
            ).mappings()
        ]
        if _is_manager(actor, membership):
            result["join_requests"] = [
                _request_view(dict(row))
                for row in session.execute(
                    text(
                        """
                        SELECT r.*, u.username, u.display_name
                        FROM workflow.task_collaboration_join_requests AS r
                        JOIN iam.users AS u ON u.id = r.user_id
                        WHERE r.space_id = :space_id AND r.status = 'pending'
                        ORDER BY r.created_at
                        """
                    ),
                    {"space_id": space_id},
                ).mappings()
            ]
            result["invitations"] = [
                _invitation_view(dict(row), actor.user_id)
                for row in session.execute(
                    text(
                        """
                        SELECT i.*, u.username, u.display_name,
                               inviter.username AS invited_by_username,
                               inviter.display_name AS invited_by_name
                        FROM workflow.task_collaboration_invitations AS i
                        JOIN iam.users AS u ON u.id = i.user_id
                        JOIN iam.users AS inviter ON inviter.id = i.invited_by_user_id
                        WHERE i.space_id = :space_id AND i.status = 'pending'
                        ORDER BY i.created_at
                        """
                    ),
                    {"space_id": space_id},
                ).mappings()
            ]
            result["invite_candidates"] = [
                {**dict(row), "id": str(row["id"])}
                for row in session.execute(
                    text(
                        """
                        SELECT u.id, u.username, u.display_name
                        FROM iam.memberships AS tm
                        JOIN iam.users AS u ON u.id = tm.user_id
                        WHERE tm.active AND u.active
                          AND NOT EXISTS (
                            SELECT 1 FROM workflow.task_collaboration_members AS m
                            WHERE m.space_id = :space_id AND m.user_id = u.id AND m.state = 'active'
                          )
                          AND NOT EXISTS (
                            SELECT 1 FROM workflow.task_collaboration_invitations AS i
                            WHERE i.space_id = :space_id
                              AND i.user_id = u.id AND i.status = 'pending'
                          )
                        ORDER BY u.display_name, u.username LIMIT 500
                        """
                    ),
                    {"space_id": space_id},
                ).mappings()
            ]
        return result


def open_space(actor: ActorContext, task_id: str, payload: dict[str, object]) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, target_id)
        _writable(task)
        if not _task_manageable(session, actor, task):
            raise HTTPException(status_code=403, detail="Task collaboration permission denied")
        existing = _space(session, target_id, required=False)
        default_scope = "hidden" if task["visibility"] == "private" else str(task["visibility"])
        default_policy = "invite_only" if task["visibility"] == "private" else "request"
        discoverability = _choice(
            payload.get("discoverability"),
            _DISCOVERABILITIES,
            "discoverability",
            str(existing["discoverability"]) if existing else default_scope,
        )
        join_policy = _choice(
            payload.get("join_policy"),
            _JOIN_POLICIES,
            "join policy",
            str(existing["join_policy"]) if existing else default_policy,
        )
        if task["visibility"] == "private" and (
            discoverability != "hidden" or join_policy != "invite_only"
        ):
            raise HTTPException(
                status_code=422, detail="Private tasks require hidden invite-only collaboration"
            )
        if task["visibility"] == "team" and discoverability == "company":
            raise HTTPException(
                status_code=422, detail="Team tasks cannot open company-wide collaboration"
            )
        max_members = payload.get("max_members")
        if max_members in (None, ""):
            max_members = existing.get("max_members") if existing else None
        else:
            try:
                max_members = int(max_members)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="Invalid maximum member count") from exc
            if not 1 <= max_members <= 500:
                raise HTTPException(status_code=422, detail="Maximum member count must be 1–500")
        if (
            existing
            and max_members is not None
            and max_members < _active_member_count(session, UUID(str(existing["id"])))
        ):
            raise HTTPException(
                status_code=409,
                detail="Maximum member count is below the active membership",
            )
        if existing:
            _require_manager(session, actor, existing)
            session.execute(
                text(
                    """
                    UPDATE workflow.task_collaboration_spaces
                    SET discoverability = :discoverability, join_policy = :join_policy,
                        max_members = :max_members
                    WHERE id = :space_id
                    """
                ),
                {
                    "space_id": existing["id"],
                    "discoverability": discoverability,
                    "join_policy": join_policy,
                    "max_members": max_members,
                },
            )
            _event(
                session,
                actor,
                existing,
                "workspace_updated",
                payload={
                    "discoverability": discoverability,
                    "join_policy": join_policy,
                    "max_members": max_members,
                },
            )
            result = "updated"
        else:
            workspace_id = uuid4()
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_spaces(
                      id, tenant_id, task_id, join_policy, discoverability,
                      max_members, created_by_user_id
                    ) VALUES (
                      :id, :tenant_id, :task_id, :join_policy, :discoverability,
                      :max_members, :created_by_user_id
                    )
                    """
                ),
                {
                    "id": workspace_id,
                    "tenant_id": actor.tenant_id,
                    "task_id": target_id,
                    "join_policy": join_policy,
                    "discoverability": discoverability,
                    "max_members": max_members,
                    "created_by_user_id": actor.user_id,
                },
            )
            existing = _space(session, target_id)
            assert existing is not None
            _activate_member(session, actor, existing, actor.user_id, "owner")
            session.execute(
                text(
                    """
                    INSERT INTO workflow.task_collaboration_channels(
                      id, tenant_id, space_id, name, display_name,
                      channel_type, created_by_user_id
                    ) VALUES (
                      :id, :tenant_id, :space_id, 'general', '一般',
                      'general', :created_by_user_id
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "space_id": workspace_id,
                    "created_by_user_id": actor.user_id,
                },
            )
            _event(session, actor, existing, "workspace_opened", subject_user_id=actor.user_id)
            result = "opened"
        _audit(session, actor, f"task.collaboration.{result}", {"task_id": task_id})
    return get_space(actor, task_id) | {"result": result, "relation": "member"}


def request_or_join(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    target_id = _uuid(task_id, "task id")
    role = _choice(payload.get("role"), _REQUEST_ROLES, "requested role", "contributor")
    message = _clean(payload.get("message"), "message", 1000)
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, target_id)
        _writable(task)
        space = _space(session, target_id)
        assert space is not None
        space_id = UUID(str(space["id"]))
        if _member(session, space_id, actor.user_id):
            return {"result": "joined", "relation": "member", "task_id": task_id}
        invitation = _pending_invitation(session, space_id, actor.user_id)
        if invitation:
            raise HTTPException(status_code=409, detail="Respond to the pending invitation")
        if not _discoverable(session, actor, task, space):
            raise HTTPException(status_code=404, detail="Task collaboration workspace not found")
        if space.get("max_members") is not None and _active_member_count(session, space_id) >= int(
            space["max_members"]
        ):
            raise HTTPException(status_code=409, detail="Workspace member limit reached")
        if space["join_policy"] == "invite_only":
            raise HTTPException(status_code=403, detail="This workspace is invite-only")
        if space["join_policy"] == "open":
            membership = _activate_member(session, actor, space, actor.user_id, role)
            _event(
                session,
                actor,
                space,
                "member_joined",
                subject_user_id=actor.user_id,
                payload={"role": role},
            )
            _audit(session, actor, "task.collaboration.joined", {"task_id": task_id})
            return {
                "result": "joined",
                "relation": "member",
                "membership": _member_view(membership),
            }
        existing = _pending_request(session, space_id, actor.user_id)
        if existing:
            return {
                "result": "requested",
                "relation": "requested",
                "join_request": _request_view(existing),
            }
        request_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_join_requests(
                  id, tenant_id, space_id, user_id, requested_role, message
                ) VALUES (:id, :tenant_id, :space_id, :user_id, :role, :message)
                """
            ),
            {
                "id": request_id,
                "tenant_id": actor.tenant_id,
                "space_id": space_id,
                "user_id": actor.user_id,
                "role": role,
                "message": message,
            },
        )
        _event(
            session,
            actor,
            space,
            "join_requested",
            subject_user_id=actor.user_id,
            payload={"request_id": str(request_id), "role": role},
        )
        return {
            "result": "requested",
            "relation": "requested",
            "join_request": {"id": str(request_id), "status": "pending", "requested_role": role},
        }


def decide_request(
    actor: ActorContext,
    task_id: str,
    request_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    decision = str(payload.get("decision") or "").strip().lower()
    if decision not in {"approve", "reject"}:
        raise HTTPException(status_code=422, detail="Decision must be approve or reject")
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        if decision == "approve":
            _writable(task)
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        _require_manager(session, actor, space)
        row = (
            session.execute(
                text(
                    """
                    SELECT r.*, u.username, u.display_name
                    FROM workflow.task_collaboration_join_requests AS r
                    JOIN iam.users AS u ON u.id = r.user_id
                    WHERE r.id = :request_id AND r.space_id = :space_id AND r.status = 'pending'
                    FOR UPDATE
                    """
                ),
                {"request_id": _uuid(request_id, "join request id"), "space_id": space["id"]},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Pending join request not found")
        request = dict(row)
        next_status = "approved" if decision == "approve" else "rejected"
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_join_requests
                SET status = :status, decided_by_user_id = :actor, decided_at = now()
                WHERE id = :request_id
                """
            ),
            {"status": next_status, "actor": actor.user_id, "request_id": request["id"]},
        )
        membership = None
        if decision == "approve":
            if space.get("max_members") is not None and _active_member_count(
                session, UUID(str(space["id"]))
            ) >= int(space["max_members"]):
                raise HTTPException(status_code=409, detail="Workspace member limit reached")
            approved_role = _choice(
                payload.get("role"),
                _REQUEST_ROLES,
                "approved role",
                str(request["requested_role"]),
            )
            membership = _activate_member(
                session,
                actor,
                space,
                UUID(str(request["user_id"])),
                approved_role,
            )
        _event(
            session,
            actor,
            space,
            f"join_request_{next_status}",
            subject_user_id=UUID(str(request["user_id"])),
            payload={"request_id": str(request["id"])},
        )
        return {
            "result": next_status,
            "relation": "member"
            if decision == "approve" and request["user_id"] == actor.user_id
            else None,
            "membership": _member_view(membership) if membership else None,
        }


def invite_member(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    user_id = _uuid(payload.get("user_id"), "user id")
    role = _choice(payload.get("role"), _INVITABLE_ROLES, "member role", "contributor")
    message = _clean(payload.get("message"), "message", 1000)
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        _writable(task)
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        _require_manager(session, actor, space)
        target = (
            session.execute(
                text(
                    """
                    SELECT u.id, u.username, u.display_name
                    FROM iam.memberships AS m JOIN iam.users AS u ON u.id = m.user_id
                    WHERE m.user_id = :user_id AND m.active AND u.active
                    """
                ),
                {"user_id": user_id},
            )
            .mappings()
            .one_or_none()
        )
        if target is None:
            raise HTTPException(status_code=422, detail="Invitee must be an active tenant member")
        if _member(session, UUID(str(space["id"])), user_id):
            raise HTTPException(status_code=409, detail="User is already a workspace member")
        existing = _pending_invitation(session, UUID(str(space["id"])), user_id)
        if existing:
            return {"result": "invited", "invitation": _invitation_view(existing, actor.user_id)}
        invitation_id = uuid4()
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_join_requests
                SET status = 'cancelled', decided_by_user_id = :actor, decided_at = now()
                WHERE space_id = :space_id AND user_id = :user_id AND status = 'pending'
                """
            ),
            {"actor": actor.user_id, "space_id": space["id"], "user_id": user_id},
        )
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_invitations(
                  id, tenant_id, space_id, user_id, role, message, invited_by_user_id
                ) VALUES (
                  :id, :tenant_id, :space_id, :user_id, :role, :message, :invited_by
                )
                """
            ),
            {
                "id": invitation_id,
                "tenant_id": actor.tenant_id,
                "space_id": space["id"],
                "user_id": user_id,
                "role": role,
                "message": message,
                "invited_by": actor.user_id,
            },
        )
        _event(
            session,
            actor,
            space,
            "member_invited",
            subject_user_id=user_id,
            payload={"invitation_id": str(invitation_id), "role": role},
        )
        return {
            "result": "invited",
            "invitation": {
                "id": str(invitation_id),
                "user_id": str(user_id),
                "display_name": target["display_name"] or target["username"],
                "role": role,
                "status": "pending",
            },
        }


def respond_invitation(
    actor: ActorContext,
    task_id: str,
    invitation_id: str,
    payload: dict[str, object],
) -> dict[str, object]:
    decision = str(payload.get("decision") or "").strip().lower()
    if decision not in {"accept", "decline"}:
        raise HTTPException(status_code=422, detail="Decision must be accept or decline")
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        if decision == "accept":
            _writable(task)
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        invitation = (
            session.execute(
                text(
                    """
                    SELECT * FROM workflow.task_collaboration_invitations
                    WHERE id = :invitation_id AND space_id = :space_id
                      AND user_id = :user_id AND status = 'pending'
                    FOR UPDATE
                    """
                ),
                {
                    "invitation_id": _uuid(invitation_id, "invitation id"),
                    "space_id": space["id"],
                    "user_id": actor.user_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if invitation is None:
            raise HTTPException(status_code=404, detail="Pending invitation not found")
        if (
            decision == "accept"
            and space.get("max_members") is not None
            and _active_member_count(session, UUID(str(space["id"]))) >= int(space["max_members"])
        ):
            raise HTTPException(status_code=409, detail="Workspace member limit reached")
        next_status = "accepted" if decision == "accept" else "declined"
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_invitations
                SET status = :status, responded_at = now() WHERE id = :invitation_id
                """
            ),
            {"status": next_status, "invitation_id": invitation["id"]},
        )
        membership = None
        if decision == "accept":
            membership = _activate_member(
                session, actor, space, actor.user_id, str(invitation["role"])
            )
        _event(
            session,
            actor,
            space,
            f"invitation_{next_status}",
            subject_user_id=actor.user_id,
            payload={"invitation_id": str(invitation["id"])},
        )
        return {
            "result": next_status,
            "relation": "member" if decision == "accept" else "available",
            "membership": _member_view(membership) if membership else None,
        }


def transfer_ownership(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    new_owner_id = _uuid(payload.get("new_owner_user_id"), "new owner user id")
    expected_owner = _uuid(payload.get("expected_owner_user_id"), "expected owner user id")
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        _writable(task)
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        current = _require_member(session, UUID(str(space["id"])), actor.user_id)
        if current["role"] != "owner" or actor.user_id != expected_owner:
            raise HTTPException(
                status_code=409, detail="Workspace ownership changed; refresh first"
            )
        successor = _require_member(session, UUID(str(space["id"])), new_owner_id)
        if successor["role"] == "observer":
            raise HTTPException(status_code=422, detail="Observer cannot own a workspace")
        session.execute(
            text(
                "UPDATE workflow.task_collaboration_members SET role = 'coordinator' WHERE id = :id"
            ),
            {"id": current["id"]},
        )
        session.execute(
            text("UPDATE workflow.task_collaboration_members SET role = 'owner' WHERE id = :id"),
            {"id": successor["id"]},
        )
        _event(
            session,
            actor,
            space,
            "ownership_transferred",
            subject_user_id=new_owner_id,
            payload={"previous_owner_user_id": str(actor.user_id)},
        )
        return {"result": "transferred", "new_owner_user_id": str(new_owner_id)}


def leave_space(actor: ActorContext, task_id: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        membership = _require_member(session, UUID(str(space["id"])), actor.user_id)
        if membership["role"] == "owner":
            raise HTTPException(status_code=409, detail="Transfer ownership before leaving")
        session.execute(
            text(
                """
                UPDATE workflow.task_collaboration_members
                SET state = 'left', left_at = now() WHERE id = :id
                """
            ),
            {"id": membership["id"]},
        )
        _event(session, actor, space, "member_left", subject_user_id=actor.user_id)
        return {"result": "left", "relation": "available", "task_id": task_id}


def list_messages(
    actor: ActorContext, task_id: str, after_id: int, limit: int
) -> dict[str, object]:
    after_id = max(0, after_id)
    limit = min(200, max(1, limit))
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        if not _task_visible(session, actor, task):
            raise HTTPException(status_code=404, detail="Task not found")
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        _require_member(session, UUID(str(space["id"])), actor.user_id)
        channel = _general_channel(session, UUID(str(space["id"])))
        rows = (
            session.execute(
                text(
                    """
                    SELECT m.*, u.username AS sender_username,
                           u.display_name AS sender_name
                    FROM workflow.task_collaboration_messages AS m
                    JOIN iam.users AS u ON u.id = m.sender_user_id
                    WHERE m.channel_id = :channel_id AND m.id > :after_id
                    ORDER BY m.id LIMIT :limit
                    """
                ),
                {"channel_id": channel["id"], "after_id": after_id, "limit": limit + 1},
            )
            .mappings()
            .all()
        )
        has_more = len(rows) > limit
        items = [
            {
                "id": int(row["id"]),
                "channel_id": str(row["channel_id"]),
                "sender_user_id": str(row["sender_user_id"]),
                "sender_name": row["sender_name"] or row["sender_username"],
                "sender_username": row["sender_username"],
                "client_message_id": row["client_message_id"],
                "body": None if row["deleted_at"] else row["body"],
                "reply_to_message_id": row["reply_to_message_id"],
                "created_at": row["created_at"],
                "edited_at": row["edited_at"],
                "deleted_at": row["deleted_at"],
                "is_mine": row["sender_user_id"] == actor.user_id,
            }
            for row in rows[:limit]
        ]
        return {
            "items": items,
            "next_after_id": int(items[-1]["id"]) if items else after_id,
            "has_more": has_more,
        }


def send_message(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    body = _clean(payload.get("body"), "message body", 8000, required=True)
    client_message_id = _clean(
        payload.get("client_message_id"), "client message id", 120, required=True
    )
    if not _CLIENT_MESSAGE_ID.fullmatch(str(client_message_id)):
        raise HTTPException(status_code=422, detail="Invalid client message id")
    reply_id = payload.get("reply_to_message_id")
    if reply_id not in (None, ""):
        try:
            reply_id = int(reply_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Invalid reply message id") from exc
    else:
        reply_id = None
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        _writable(task)
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        membership = _require_member(session, UUID(str(space["id"])), actor.user_id)
        if membership["role"] == "observer":
            raise HTTPException(status_code=403, detail="Observers cannot send messages")
        channel = _general_channel(session, UUID(str(space["id"])))
        if payload.get("channel_id") not in (None, "") and _uuid(
            payload.get("channel_id"), "channel id"
        ) != UUID(str(channel["id"])):
            raise HTTPException(status_code=422, detail="Channel does not belong to this workspace")
        existing = (
            session.execute(
                text(
                    """
                    SELECT m.*, u.username AS sender_username,
                           u.display_name AS sender_name
                    FROM workflow.task_collaboration_messages AS m
                    JOIN iam.users AS u ON u.id = m.sender_user_id
                    WHERE m.channel_id = :channel_id AND m.sender_user_id = :sender
                      AND m.client_message_id = :client_message_id
                    """
                ),
                {
                    "channel_id": channel["id"],
                    "sender": actor.user_id,
                    "client_message_id": client_message_id,
                },
            )
            .mappings()
            .one_or_none()
        )
        if existing:
            if existing["body"] != body or existing["reply_to_message_id"] != reply_id:
                raise HTTPException(
                    status_code=409, detail="Client message id already has different content"
                )
            row = existing
            idempotent = True
        else:
            if (
                reply_id is not None
                and not session.execute(
                    text(
                        """
                    SELECT 1 FROM workflow.task_collaboration_messages
                    WHERE id = :reply_id AND channel_id = :channel_id
                    """
                    ),
                    {"reply_id": reply_id, "channel_id": channel["id"]},
                ).scalar_one_or_none()
            ):
                raise HTTPException(status_code=422, detail="Reply target not found")
            try:
                message_id = session.execute(
                    text(
                        """
                        INSERT INTO workflow.task_collaboration_messages(
                          tenant_id, channel_id, sender_user_id, client_message_id,
                          body, reply_to_message_id
                        ) VALUES (
                          :tenant_id, :channel_id, :sender, :client_message_id,
                          :body, :reply_id
                        ) RETURNING id
                        """
                    ),
                    {
                        "tenant_id": actor.tenant_id,
                        "channel_id": channel["id"],
                        "sender": actor.user_id,
                        "client_message_id": client_message_id,
                        "body": body,
                        "reply_id": reply_id,
                    },
                ).scalar_one()
            except IntegrityError as exc:
                raise HTTPException(
                    status_code=409, detail="Message could not be appended"
                ) from exc
            _event(
                session,
                actor,
                space,
                "message_sent",
                subject_user_id=actor.user_id,
                payload={"message_id": int(message_id), "channel_id": str(channel["id"])},
            )
            row = (
                session.execute(
                    text(
                        """
                        SELECT m.*, u.username AS sender_username,
                               u.display_name AS sender_name
                        FROM workflow.task_collaboration_messages AS m
                        JOIN iam.users AS u ON u.id = m.sender_user_id WHERE m.id = :id
                        """
                    ),
                    {"id": message_id},
                )
                .mappings()
                .one()
            )
            idempotent = False
        message = {
            "id": int(row["id"]),
            "channel_id": str(row["channel_id"]),
            "sender_user_id": str(row["sender_user_id"]),
            "sender_name": row["sender_name"] or row["sender_username"],
            "sender_username": row["sender_username"],
            "client_message_id": row["client_message_id"],
            "body": row["body"],
            "reply_to_message_id": row["reply_to_message_id"],
            "created_at": row["created_at"],
            "edited_at": row["edited_at"],
            "deleted_at": row["deleted_at"],
            "is_mine": True,
        }
        return {
            "result": "idempotent" if idempotent else "sent",
            "idempotent": idempotent,
            "message": message,
        }


def mark_read(actor: ActorContext, task_id: str, payload: dict[str, object]) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        task = _task(session, _uuid(task_id, "task id"))
        space = _space(session, UUID(str(task["id"])))
        assert space is not None
        _require_member(session, UUID(str(space["id"])), actor.user_id)
        channel = _general_channel(session, UUID(str(space["id"])))
        if payload.get("channel_id") not in (None, "") and _uuid(
            payload.get("channel_id"), "channel id"
        ) != UUID(str(channel["id"])):
            raise HTTPException(status_code=422, detail="Channel does not belong to this workspace")
        if payload.get("message_id") in (None, ""):
            message_id = int(
                session.execute(
                    text(
                        """
                        SELECT COALESCE(max(id), 0)
                        FROM workflow.task_collaboration_messages
                        WHERE channel_id = :channel_id
                        """
                    ),
                    {"channel_id": channel["id"]},
                ).scalar_one()
            )
            if message_id == 0:
                return {"result": "read", "message_id": 0}
        else:
            try:
                message_id = int(payload["message_id"])
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail="Invalid message id") from exc
            if message_id < 1:
                raise HTTPException(status_code=422, detail="Invalid message id")
        exists = session.execute(
            text(
                """
                SELECT 1 FROM workflow.task_collaboration_messages
                WHERE id = :message_id AND channel_id = :channel_id
                """
            ),
            {"message_id": message_id, "channel_id": channel["id"]},
        ).scalar_one_or_none()
        if not exists:
            raise HTTPException(status_code=422, detail="Message does not belong to this workspace")
        session.execute(
            text(
                """
                INSERT INTO workflow.task_collaboration_message_reads(
                  tenant_id, channel_id, user_id, last_message_id
                ) VALUES (:tenant_id, :channel_id, :user_id, :message_id)
                ON CONFLICT (tenant_id, channel_id, user_id) DO UPDATE
                SET last_message_id = GREATEST(
                      workflow.task_collaboration_message_reads.last_message_id,
                      EXCLUDED.last_message_id
                    ),
                    updated_at = now()
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "channel_id": channel["id"],
                "user_id": actor.user_id,
                "message_id": message_id,
            },
        )
        return {"result": "read", "message_id": message_id}
