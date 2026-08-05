"""Audited, tenant-scoped implementation of the V2 task center."""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext
from app.db.session import tenant_session

_KINDS = frozenset({"task", "event", "plan"})
_STATUSES = frozenset({"planned", "in_progress", "waiting", "completed", "cancelled"})
_PRIORITIES = frozenset({"urgent", "high", "normal", "low"})
_VISIBILITIES = frozenset({"private", "team", "company"})
_TRANSITIONS = {
    "planned": frozenset({"in_progress", "waiting", "completed", "cancelled"}),
    "in_progress": frozenset({"waiting", "completed", "cancelled"}),
    "waiting": frozenset({"in_progress", "completed", "cancelled"}),
    "completed": frozenset({"in_progress"}),
    "cancelled": frozenset(),
}


def _permission(actor: ActorContext, *keys: str) -> bool:
    return actor.role_level >= 10 or any(key in actor.permissions for key in keys)


def _require(actor: ActorContext, *keys: str) -> None:
    if not _permission(actor, *keys):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _uuid(value: object, *, label: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label}",
        ) from exc


def _optional_uuid(value: object | None, *, label: str) -> UUID | None:
    return None if value in (None, "") else _uuid(value, label=label)


def _clean(value: object | None, *, maximum: int) -> str | None:
    if value is None:
        return None
    result = str(value).strip()
    if len(result) > maximum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Field must be at most {maximum} characters",
        )
    return result or None


def _enum(value: object | None, allowed: frozenset[str], *, label: str, default: str) -> str:
    result = str(value or default).strip()
    if result not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {label}",
        )
    return result


def _audit(
    session: Session, actor: ActorContext, event_type: str, payload: dict[str, object]
) -> None:
    session.execute(
        text("""
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
        """),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _task_event(
    session: Session,
    actor: ActorContext,
    task_id: UUID,
    event_type: str,
    payload: dict[str, object],
) -> None:
    session.execute(
        text("""
            INSERT INTO workflow.task_events(
              tenant_id, task_id, actor_user_id, event_type, payload
            ) VALUES (
              :tenant_id, :task_id, :actor_user_id, :event_type, CAST(:payload AS jsonb)
            )
        """),
        {
            "tenant_id": actor.tenant_id,
            "task_id": task_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _member_exists(session: Session, user_id: UUID) -> bool:
    return bool(
        session.execute(
            text("SELECT 1 FROM iam.memberships WHERE user_id = :user_id AND active"),
            {"user_id": user_id},
        ).scalar_one_or_none()
    )


def _assignees(actor: ActorContext, session: Session, values: object) -> list[UUID]:
    if not isinstance(values, list):
        values = []
    result = list(dict.fromkeys(_uuid(value, label="assignee id") for value in values))
    if not result:
        return [actor.user_id]
    if not _permission(actor, "tasks.assign", "tasks.manage") and set(result) != {actor.user_id}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Assignment permission denied"
        )
    for user_id in result:
        if not _member_exists(session, user_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Assignee must be an active tenant member",
            )
    return result


def _task_row(session: Session, task_id: UUID) -> dict[str, object]:
    row = (
        session.execute(
            text("""
            SELECT id, created_by, title, description, kind, category, status, priority,
                   visibility, start_at, end_at, due_at, all_day, timezone, location,
                   owner_org_unit_id, plan_id, source_type, source_entity_id, version,
                   completed_at, created_at, updated_at
            FROM workflow.tasks WHERE id = :task_id
        """),
            {"task_id": task_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return dict(row)


def _can_manage_task(actor: ActorContext, session: Session, task: dict[str, object]) -> bool:
    if _permission(actor, "tasks.manage") or task["created_by"] == actor.user_id:
        return True
    return bool(
        session.execute(
            text("""
                SELECT 1 FROM workflow.task_assignees
                WHERE task_id = :task_id AND user_id = :user_id
            """),
            {"task_id": task["id"], "user_id": actor.user_id},
        ).scalar_one_or_none()
    )


def _serialize(session: Session, actor: ActorContext, task: dict[str, object]) -> dict[str, object]:
    assignees = (
        session.execute(
            text("""
            SELECT u.id, u.username, u.display_name
            FROM workflow.task_assignees AS ta JOIN iam.users AS u ON u.id = ta.user_id
            WHERE ta.task_id = :task_id ORDER BY u.display_name, u.username
        """),
            {"task_id": task["id"]},
        )
        .mappings()
        .all()
    )
    plan_title = None
    if task["plan_id"] is not None:
        plan_title = session.execute(
            text("SELECT title FROM workflow.tasks WHERE id = :plan_id"),
            {"plan_id": task["plan_id"]},
        ).scalar_one_or_none()
    can_status = _can_manage_task(actor, session, task)
    can_update = can_status
    can_delete = can_status
    can_reopen = can_status and task["status"] == "completed"
    return {
        "id": str(task["id"]),
        "title": task["title"],
        "description": task["description"],
        "kind": task["kind"],
        "category": task["category"],
        "status": task["status"],
        "priority": task["priority"],
        "visibility": task["visibility"],
        "start_at": task["start_at"],
        "end_at": task["end_at"],
        "due_at": task["due_at"],
        "all_day": bool(task["all_day"]),
        "timezone": task["timezone"],
        "location": task["location"],
        "owner_org_unit_id": str(task["owner_org_unit_id"]) if task["owner_org_unit_id"] else None,
        "plan_id": str(task["plan_id"]) if task["plan_id"] else None,
        "plan_title": plan_title,
        "source_type": task["source_type"],
        "source_entity_id": task["source_entity_id"],
        "version": int(task["version"]),
        "lock_version": int(task["version"]),
        "completed_at": task["completed_at"],
        "created_at": task["created_at"],
        "updated_at": task["updated_at"],
        "assignees": [
            {"id": str(row["id"]), "username": row["username"], "display_name": row["display_name"]}
            for row in assignees
        ],
        "assignee_name": assignees[0]["display_name"] if assignees else None,
        "can_status": can_status,
        "can_update": can_update,
        "can_delete": can_delete,
        "can_reopen": can_reopen,
        "capabilities": {
            "can_update": can_update,
            "can_change_status": can_status,
            "can_delete": can_delete,
            "can_reopen": can_reopen,
        },
        "actions": sorted(_TRANSITIONS[str(task["status"])]),
    }


def task_meta(actor: ActorContext) -> dict[str, object]:
    can_create = _permission(actor, "tasks.create", "tasks.manage")
    can_assign = _permission(actor, "tasks.assign", "tasks.manage")
    can_manage = _permission(actor, "tasks.manage")
    with tenant_session(actor.tenant_id) as session:
        users = (
            session.execute(
                text("""
                SELECT u.id, u.username, u.display_name
                FROM iam.memberships AS m JOIN iam.users AS u ON u.id = m.user_id
                WHERE m.active AND u.active ORDER BY u.display_name, u.username
            """)
            )
            .mappings()
            .all()
        )
        org_units = (
            session.execute(
                text("""
                SELECT id, name AS unit_name, unit_code FROM iam.organizational_units
                WHERE active AND unit_type <> 'company' ORDER BY name, unit_code
            """)
            )
            .mappings()
            .all()
        )
        plans = (
            session.execute(
                text("""
                    SELECT id, title FROM workflow.tasks
                    WHERE kind = 'plan' AND status <> 'cancelled'
                    ORDER BY created_at DESC
                """)
            )
            .mappings()
            .all()
        )
    return {
        "capabilities": {
            "can_create": can_create,
            "can_assign": can_assign,
            "can_manage": can_manage,
        },
        "users": [{**dict(row), "id": str(row["id"])} for row in users],
        "org_units": [{**dict(row), "id": str(row["id"])} for row in org_units],
        "plans": [{**dict(row), "id": str(row["id"])} for row in plans],
    }


def list_tasks(actor: ActorContext, scope: str = "mine") -> dict[str, object]:
    if scope not in {"mine", "managed"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid task scope"
        )
    can_manage = _permission(actor, "tasks.manage")
    with tenant_session(actor.tenant_id) as session:
        predicate = """
            t.created_by = :user_id OR EXISTS (
              SELECT 1 FROM workflow.task_assignees AS ta
              WHERE ta.task_id = t.id AND ta.user_id = :user_id
            )
        """
        if scope == "managed" and can_manage:
            predicate = "TRUE"
        rows = (
            session.execute(
                text(
                    f"""
                SELECT t.id, t.created_by, t.title, t.description, t.kind, t.category, t.status,
                       t.priority, t.visibility, t.start_at, t.end_at, t.due_at, t.all_day,
                       t.timezone, t.location, t.owner_org_unit_id, t.plan_id, t.source_type,
                       t.source_entity_id, t.version, t.completed_at, t.created_at, t.updated_at
                FROM workflow.tasks AS t WHERE {predicate}
                ORDER BY COALESCE(t.due_at, t.start_at, t.created_at) ASC, t.created_at DESC
                """
                ),
                {"user_id": actor.user_id},
            )
            .mappings()
            .all()
        )
        items = [_serialize(session, actor, dict(row)) for row in rows]
    return {
        "items": items,
        "tasks": items,
        "capabilities": {
            "can_assign": _permission(actor, "tasks.assign", "tasks.manage"),
            "can_manage": can_manage,
        },
    }


def get_task(actor: ActorContext, task_id: str) -> dict[str, object]:
    _require(actor, "tasks.read", "tasks.create", "tasks.manage")
    with tenant_session(actor.tenant_id) as session:
        task = _task_row(session, _uuid(task_id, label="task id"))
        if not _can_manage_task(actor, session, task):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return _serialize(session, actor, task)


def task_history(
    actor: ActorContext,
    task_id: str,
    *,
    limit: int = 100,
    before_id: int | None = None,
) -> dict[str, object]:
    _require(actor, "tasks.read", "tasks.create", "tasks.manage")
    safe_limit = min(500, max(1, int(limit)))
    with tenant_session(actor.tenant_id) as session:
        task = _task_row(session, _uuid(task_id, label="task id"))
        if not _can_manage_task(actor, session, task):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        rows = (
            session.execute(
                text("""
                    SELECT e.id, e.event_type, e.actor_user_id, e.payload, e.created_at,
                           u.username AS actor_username,
                           u.display_name AS actor_display_name
                    FROM workflow.task_events AS e
                    LEFT JOIN iam.users AS u ON u.id = e.actor_user_id
                    WHERE e.task_id = :task_id
                      AND (
                        CAST(:before_id AS bigint) IS NULL
                        OR e.id < CAST(:before_id AS bigint)
                      )
                    ORDER BY e.id DESC LIMIT :limit
                """),
                {
                    "task_id": task["id"],
                    "before_id": before_id,
                    "limit": safe_limit + 1,
                },
            )
            .mappings()
            .all()
        )
        has_more = len(rows) > safe_limit
        items = [
            {
                **dict(row),
                "id": int(row["id"]),
                "actor_user_id": str(row["actor_user_id"]) if row["actor_user_id"] else None,
                "actor_name": row["actor_display_name"] or row["actor_username"],
            }
            for row in rows[:safe_limit]
        ]
        return {
            "task_id": str(task["id"]),
            "items": items,
            "has_more": has_more,
            "next_before_id": int(items[-1]["id"]) if has_more and items else None,
        }


def create_task(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "tasks.create", "tasks.manage")
    title = _clean(payload.get("title"), maximum=240)
    if title is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Task title is required"
        )
    kind = _enum(payload.get("kind"), _KINDS, label="task kind", default="task")
    priority = _enum(payload.get("priority"), _PRIORITIES, label="priority", default="normal")
    visibility = _enum(
        payload.get("visibility"), _VISIBILITIES, label="visibility", default="private"
    )
    task_id = uuid4()
    request_id = _clean(payload.get("client_request_id"), maximum=160)
    with tenant_session(actor.tenant_id) as session:
        if request_id:
            existing = session.execute(
                text("""
                    SELECT id FROM workflow.tasks
                    WHERE created_by = :user_id AND client_request_id = :request_id
                """),
                {"user_id": actor.user_id, "request_id": request_id},
            ).scalar_one_or_none()
            if existing is not None:
                return _serialize(session, actor, _task_row(session, existing))
        owner_org_unit_id = _optional_uuid(
            payload.get("owner_org_unit_id"), label="organization unit id"
        )
        if owner_org_unit_id is not None:
            active_unit = session.execute(
                text("SELECT 1 FROM iam.organizational_units WHERE id = :id AND active"),
                {"id": owner_org_unit_id},
            ).scalar_one_or_none()
            if active_unit is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Organization unit is unavailable",
                )
        plan_id = _optional_uuid(payload.get("plan_id"), label="plan id")
        if plan_id is not None:
            plan = session.execute(
                text("SELECT 1 FROM workflow.tasks WHERE id = :id AND kind = 'plan'"),
                {"id": plan_id},
            ).scalar_one_or_none()
            if plan is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Plan is unavailable"
                )
        assignees = _assignees(actor, session, payload.get("assignees"))
        session.execute(
            text("""
                INSERT INTO workflow.tasks(
                  id, tenant_id, created_by, title, description, kind, category, status,
                  priority, visibility, start_at, end_at, due_at, all_day, timezone, location,
                  owner_org_unit_id, plan_id, source_type, source_entity_id, client_request_id
                ) VALUES (
                  :id, :tenant_id, :created_by, :title, :description, :kind, :category, 'planned',
                  :priority, :visibility, :start_at, :end_at, :due_at, :all_day,
                  :timezone, :location,
                  :owner_org_unit_id, :plan_id, :source_type, :source_entity_id, :client_request_id
                )
            """),
            {
                "id": task_id,
                "tenant_id": actor.tenant_id,
                "created_by": actor.user_id,
                "title": title,
                "description": _clean(payload.get("description"), maximum=2000),
                "kind": kind,
                "category": _clean(payload.get("category"), maximum=80) or "work",
                "priority": priority,
                "visibility": visibility,
                "start_at": _clean(payload.get("start_at"), maximum=64),
                "end_at": _clean(payload.get("end_at"), maximum=64),
                "due_at": _clean(payload.get("due_at"), maximum=64),
                "all_day": bool(payload.get("all_day")),
                "timezone": _clean(payload.get("timezone"), maximum=80) or "UTC",
                "location": _clean(payload.get("location"), maximum=240),
                "owner_org_unit_id": owner_org_unit_id,
                "plan_id": plan_id,
                "source_type": _clean(payload.get("source_type"), maximum=80),
                "source_entity_id": _clean(payload.get("source_entity_id"), maximum=160),
                "client_request_id": request_id,
            },
        )
        for user_id in assignees:
            session.execute(
                text("""
                    INSERT INTO workflow.task_assignees(tenant_id, task_id, user_id, assigned_by)
                    VALUES (:tenant_id, :task_id, :user_id, :assigned_by)
                """),
                {
                    "tenant_id": actor.tenant_id,
                    "task_id": task_id,
                    "user_id": user_id,
                    "assigned_by": actor.user_id,
                },
            )
        task = _task_row(session, task_id)
        _audit(
            session,
            actor,
            "task.created",
            {
                "task_id": str(task_id),
                "kind": kind,
                "assignees": [str(value) for value in assignees],
            },
        )
        _task_event(
            session,
            actor,
            task_id,
            "created",
            {"kind": kind, "assignees": [str(value) for value in assignees]},
        )
        return _serialize(session, actor, task)


def update_task(actor: ActorContext, task_id: str, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "tasks.read", "tasks.create", "tasks.manage")
    expected_version = payload.get("expected_version")
    if not isinstance(expected_version, int) or expected_version < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expected task version is required",
        )
    target_id = _uuid(task_id, label="task id")
    with tenant_session(actor.tenant_id) as session:
        task = _task_row(session, target_id)
        if not _can_manage_task(actor, session, task):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Task update permission denied",
            )
        values: dict[str, object] = {}
        aliases = {
            "start_at": ("start_at", "starts_at"),
            "end_at": ("end_at", "ends_at"),
            "due_at": ("due_at",),
        }
        for column, keys in aliases.items():
            supplied = next((key for key in keys if key in payload), None)
            if supplied is not None:
                values[column] = _clean(payload.get(supplied), maximum=64)
        for column, maximum in {
            "title": 240,
            "description": 2000,
            "category": 80,
            "timezone": 80,
            "location": 240,
        }.items():
            if column in payload:
                values[column] = _clean(payload.get(column), maximum=maximum)
        if "title" in values and values["title"] is None:
            raise HTTPException(status_code=422, detail="Task title is required")
        if "priority" in payload:
            values["priority"] = _enum(
                payload.get("priority"), _PRIORITIES, label="priority", default=""
            )
        if "visibility" in payload:
            values["visibility"] = _enum(
                payload.get("visibility"), _VISIBILITIES, label="visibility", default=""
            )
        if "kind" in payload:
            values["kind"] = _enum(
                payload.get("kind"), _KINDS, label="task kind", default=""
            )
        if "all_day" in payload:
            values["all_day"] = bool(payload["all_day"])
        if "owner_org_unit_id" in payload:
            unit_id = _optional_uuid(payload.get("owner_org_unit_id"), label="organization unit id")
            if (
                unit_id is not None
                and not session.execute(
                    text("SELECT 1 FROM iam.organizational_units WHERE id = :id AND active"),
                    {"id": unit_id},
                ).scalar_one_or_none()
            ):
                raise HTTPException(status_code=422, detail="Organization unit is unavailable")
            values["owner_org_unit_id"] = unit_id
        if "plan_id" in payload:
            plan_id = _optional_uuid(payload.get("plan_id"), label="plan id")
            if (
                plan_id is not None
                and not session.execute(
                    text("SELECT 1 FROM workflow.tasks WHERE id = :id AND kind = 'plan'"),
                    {"id": plan_id},
                ).scalar_one_or_none()
            ):
                raise HTTPException(status_code=422, detail="Plan is unavailable")
            values["plan_id"] = plan_id
        effective_kind = str(values.get("kind") or task["kind"])
        if task["kind"] == "plan" and effective_kind != "plan":
            child_exists = session.execute(
                text("SELECT 1 FROM workflow.tasks WHERE plan_id = :plan_id LIMIT 1"),
                {"plan_id": target_id},
            ).scalar_one_or_none()
            if child_exists is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Move tasks out of this plan before changing its type",
                )
        if effective_kind == "plan":
            values["plan_id"] = None
        assignees = None
        if "assignees" in payload:
            assignees = _assignees(actor, session, payload.get("assignees"))
        if not values and assignees is None:
            return _serialize(session, actor, task)
        assignments = ", ".join(f"{column} = :{column}" for column in values)
        if assignments:
            assignments += ", "
        result = session.execute(
            text(
                f"""
                UPDATE workflow.tasks
                SET {assignments}version = version + 1
                WHERE id = :task_id AND version = :expected_version
                """
            ),
            {**values, "task_id": target_id, "expected_version": expected_version},
        )
        if result.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task changed; refresh before updating",
            )
        if assignees is not None:
            session.execute(
                text("DELETE FROM workflow.task_assignees WHERE task_id = :task_id"),
                {"task_id": target_id},
            )
            for user_id in assignees:
                session.execute(
                    text("""
                        INSERT INTO workflow.task_assignees(
                          tenant_id, task_id, user_id, assigned_by
                        ) VALUES (:tenant_id, :task_id, :user_id, :assigned_by)
                    """),
                    {
                        "tenant_id": actor.tenant_id,
                        "task_id": target_id,
                        "user_id": user_id,
                        "assigned_by": actor.user_id,
                    },
                )
        changed_fields = sorted([*values, *(["assignees"] if assignees is not None else [])])
        _task_event(session, actor, target_id, "updated", {"fields": changed_fields})
        _audit(
            session,
            actor,
            "task.updated",
            {"task_id": task_id, "fields": changed_fields},
        )
        return _serialize(session, actor, _task_row(session, target_id))


def delete_task(actor: ActorContext, task_id: str, payload: dict[str, object]) -> dict[str, object]:
    _require(actor, "tasks.read", "tasks.create", "tasks.manage")
    expected_version = payload.get("expected_version")
    if not isinstance(expected_version, int) or expected_version < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expected task version is required",
        )
    if payload.get("confirm") is not True:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Task deletion must be explicitly confirmed",
        )
    target_id = _uuid(task_id, label="task id")
    with tenant_session(actor.tenant_id) as session:
        task = _task_row(session, target_id)
        if not _can_manage_task(actor, session, task):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Task delete permission denied",
            )
        collaboration_removed = bool(
            session.execute(
                text(
                    "SELECT 1 FROM workflow.task_collaboration_spaces "
                    "WHERE task_id = :task_id LIMIT 1"
                ),
                {"task_id": target_id},
            ).scalar_one_or_none()
        )
        detached_plan_tasks = int(
            session.execute(
                text("SELECT count(*) FROM workflow.tasks WHERE plan_id = :task_id"),
                {"task_id": target_id},
            ).scalar_one()
        )
        result = session.execute(
            text(
                "DELETE FROM workflow.tasks "
                "WHERE id = :task_id AND version = :expected_version"
            ),
            {"task_id": target_id, "expected_version": expected_version},
        )
        if result.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Task changed; refresh before deleting",
            )
        _audit(
            session,
            actor,
            "task.deleted",
            {
                "task_id": str(target_id),
                "title": task["title"],
                "kind": task["kind"],
                "version": expected_version,
                "collaboration_removed": collaboration_removed,
                "detached_plan_tasks": detached_plan_tasks,
            },
        )
        return {
            "ok": True,
            "deleted": True,
            "task_id": str(target_id),
            "collaboration_removed": collaboration_removed,
            "detached_plan_tasks": detached_plan_tasks,
        }


def update_task_status(
    actor: ActorContext, task_id: str, payload: dict[str, object]
) -> dict[str, object]:
    _require(actor, "tasks.read", "tasks.create", "tasks.manage")
    target_status = _enum(payload.get("status"), _STATUSES, label="task status", default="")
    expected_version = payload.get("expected_version")
    if not isinstance(expected_version, int) or expected_version < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Expected task version is required",
        )
    with tenant_session(actor.tenant_id) as session:
        task = _task_row(session, _uuid(task_id, label="task id"))
        if not _can_manage_task(actor, session, task):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Task update permission denied"
            )
        if target_status not in _TRANSITIONS[str(task["status"])]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Invalid task status transition"
            )
        result = session.execute(
            text("""
                UPDATE workflow.tasks
                SET status = :status, version = version + 1,
                    completed_at = CASE WHEN :status = 'completed' THEN now() ELSE NULL END
                WHERE id = :task_id AND version = :expected_version
            """),
            {"status": target_status, "task_id": task["id"], "expected_version": expected_version},
        )
        if result.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Task changed; refresh before updating"
            )
        updated = _task_row(session, task["id"])
        _audit(
            session,
            actor,
            "task.status_changed",
            {"task_id": str(task["id"]), "from": task["status"], "to": target_status},
        )
        _task_event(
            session,
            actor,
            UUID(str(task["id"])),
            "status_changed",
            {
                "from": task["status"],
                "to": target_status,
                "note": _clean(payload.get("note"), maximum=1000),
            },
        )
        return _serialize(session, actor, updated)


def allowed_task_statuses(current: str) -> frozenset[str]:
    """Expose transition policy for unit tests and future workflow adapters."""
    return _TRANSITIONS.get(current, frozenset())
