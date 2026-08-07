"""Tenant-scoped registration and company membership request workflow."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import system_session, tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext


# Public registration creates the global account and request in one transaction,
# so PostgreSQL gives both rows the exact same ``now()`` timestamp.  An authenticated
# company join always uses an account created by an earlier transaction.  This is
# stable after review and does not cross the tenant RLS boundary to inspect another
# company's memberships.
_JOIN_REQUEST_SQL = "u.created_at < mr.created_at"


def _safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, (datetime, UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    return value


def _require_manager(actor: ActorContext) -> None:
    if actor.role_level < 10 and "users.manage" not in actor.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing users.manage",
        )


def _request_uuid(request_id: str) -> UUID:
    try:
        return UUID(str(request_id))
    except (AttributeError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Membership request not found") from exc


def _validate_status(request_status: str) -> str:
    normalized = str(request_status or "pending").strip().lower()
    if normalized not in {"pending", "approved", "rejected", "all"}:
        raise HTTPException(status_code=422, detail="Invalid membership request status")
    return normalized


def _validate_kind(request_kind: str) -> str:
    normalized = str(request_kind or "all").strip().lower()
    if normalized not in {"registration", "join", "all"}:
        raise HTTPException(status_code=422, detail="Invalid membership request kind")
    return normalized


def list_membership_requests(
    actor: ActorContext,
    *,
    request_status: str = "pending",
    request_kind: str = "all",
) -> dict[str, object]:
    """Return real requests for the current tenant, split by their stable origin."""

    _require_manager(actor)
    normalized_status = _validate_status(request_status)
    normalized_kind = _validate_kind(request_kind)
    kind_predicate = f"""
      AND (
        :kind = 'all'
        OR (:kind = 'join' AND {_JOIN_REQUEST_SQL})
        OR (:kind = 'registration' AND NOT {_JOIN_REQUEST_SQL})
      )
    """
    query = text(
        f"""
        SELECT mr.id, mr.user_id, u.username, u.display_name,
               mr.requested_org_unit_code,
               COALESCE(requested_unit.name, mr.department) AS requested_org_unit_name,
               mr.requested_position_code,
               requested_position.name AS requested_position_name,
               mr.requested_role_id,
               COALESCE(requested_role.name, requested_position.role_name,
                        mr.requested_role_id) AS requested_role_name,
               mr.department, mr.contact, mr.reason, mr.status, mr.note,
               mr.note AS review_note, mr.created_at, mr.updated_at,
               CASE WHEN mr.status = 'pending' THEN NULL ELSE mr.updated_at END AS reviewed_at,
               reviewer.display_name AS reviewer_name,
               assigned_position.name AS assigned_position_name,
               assigned_role.name AS assigned_role_name,
               CASE WHEN {_JOIN_REQUEST_SQL} THEN 'join' ELSE 'registration' END AS request_kind
        FROM platform.membership_requests AS mr
        JOIN iam.users AS u ON u.id = mr.user_id
        LEFT JOIN iam.users AS reviewer ON reviewer.id = mr.reviewed_by
        LEFT JOIN iam.organizational_units AS requested_unit
          ON requested_unit.tenant_id = mr.tenant_id
         AND requested_unit.unit_code = mr.requested_org_unit_code
        LEFT JOIN iam.position_profiles AS requested_position
          ON requested_position.tenant_id = mr.tenant_id
         AND requested_position.position_code = mr.requested_position_code
        LEFT JOIN iam.roles AS requested_role
          ON requested_role.tenant_id = mr.tenant_id
         AND (requested_role.id::text = mr.requested_role_id
              OR requested_role.role_key = mr.requested_role_id)
        LEFT JOIN iam.memberships AS assigned_membership
          ON assigned_membership.tenant_id = mr.tenant_id
         AND assigned_membership.user_id = mr.user_id
         AND assigned_membership.active
        LEFT JOIN iam.position_profiles AS assigned_position
          ON assigned_position.tenant_id = assigned_membership.tenant_id
         AND assigned_position.position_code = assigned_membership.position_code
        LEFT JOIN LATERAL (
          SELECT role.name
          FROM iam.membership_roles AS membership_role
          JOIN iam.roles AS role
            ON role.tenant_id = membership_role.tenant_id
           AND role.id = membership_role.role_id
          WHERE membership_role.tenant_id = mr.tenant_id
            AND membership_role.user_id = mr.user_id
          ORDER BY role.level DESC, role.name
          LIMIT 1
        ) AS assigned_role ON true
        WHERE mr.tenant_id = :tenant_id
          AND (:request_status = 'all' OR mr.status = :request_status)
          {kind_predicate}
        ORDER BY mr.created_at DESC
        """
    )
    count_query = text(
        f"""
        SELECT count(*)
        FROM platform.membership_requests AS mr
        JOIN iam.users AS u ON u.id = mr.user_id
        WHERE mr.tenant_id = :tenant_id
          AND mr.status = 'pending'
          {kind_predicate}
        """
    )
    params = {
        "tenant_id": actor.tenant_id,
        "request_status": normalized_status,
        "kind": normalized_kind,
    }
    with system_session() as session:
        rows = session.execute(query, params).mappings().all()
        pending_count = int(session.execute(count_query, params).scalar_one())
    return {
        "available": True,
        "requests": [_safe(dict(row)) for row in rows],
        "pending_count": pending_count,
        "request_kind": normalized_kind,
    }


def _load_request_for_review(
    actor: ActorContext,
    request_id: str,
    *,
    expected_kind: str | None,
) -> dict[str, object]:
    _require_manager(actor)
    parsed_id = _request_uuid(request_id)
    expected = _validate_kind(expected_kind) if expected_kind else "all"
    with system_session() as session:
        row = (
            session.execute(
                text(
                    f"""
                SELECT mr.id, mr.tenant_id, mr.user_id, mr.status,
                       mr.requested_org_unit_code, mr.requested_position_code,
                       mr.requested_role_id,
                       CASE WHEN {_JOIN_REQUEST_SQL}
                            THEN 'join' ELSE 'registration' END AS request_kind
                FROM platform.membership_requests AS mr
                JOIN iam.users AS u ON u.id = mr.user_id
                WHERE mr.id = :id AND mr.tenant_id = :tenant_id
                """
                ),
                {"id": parsed_id, "tenant_id": actor.tenant_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None or (expected != "all" and row["request_kind"] != expected):
        raise HTTPException(status_code=404, detail="Membership request not found")
    return dict(row)


def _active_membership_readback(
    actor: ActorContext,
    user_id: object,
) -> dict[str, object]:
    """Read the actual tenant assignment after a membership transition."""

    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT m.user_id, u.username, u.display_name, m.active,
                       m.position_code, m.role_level, m.topology_level,
                       m.topology_title,
                       position.name AS position_name,
                       position.department_code AS org_unit_code,
                       org_unit.name AS org_unit_name,
                       assigned_role.id AS role_id,
                       assigned_role.role_key,
                       assigned_role.name AS role_name,
                       assigned_role.level AS access_role_level
                FROM iam.memberships AS m
                JOIN iam.users AS u ON u.id = m.user_id
                LEFT JOIN iam.position_profiles AS position
                  ON position.tenant_id = m.tenant_id
                 AND position.position_code = m.position_code
                LEFT JOIN iam.organizational_units AS org_unit
                  ON org_unit.tenant_id = position.tenant_id
                 AND org_unit.unit_code = position.department_code
                LEFT JOIN LATERAL (
                  SELECT role.id, role.role_key, role.name, role.level
                  FROM iam.membership_roles AS membership_role
                  JOIN iam.roles AS role
                    ON role.tenant_id = membership_role.tenant_id
                   AND role.id = membership_role.role_id
                  WHERE membership_role.tenant_id = m.tenant_id
                    AND membership_role.user_id = m.user_id
                    AND role.active
                  ORDER BY role.level DESC, role.name
                  LIMIT 1
                ) AS assigned_role ON true
                WHERE m.tenant_id = :tenant_id AND m.user_id = :user_id
                  AND m.active
                """
                ),
                {"tenant_id": actor.tenant_id, "user_id": user_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approved request has no active tenant membership",
        )
    return _safe(dict(row))


def _approval_result(
    actor: ActorContext,
    request_row: dict[str, object],
    *,
    already_processed: bool = False,
) -> dict[str, object]:
    membership = _active_membership_readback(actor, request_row["user_id"])
    request_id = str(request_row["id"])
    request_kind = str(request_row["request_kind"])
    observation = {
        "schema": "warehouse.world-observation.v1",
        "operation": "membership_request.approve",
        "effect": "membership_activated",
        "primary_entity": {
            "resource": "iam.membership_request",
            "id": request_id,
            "ref": request_id,
            "facts": {"status": "approved", "request_kind": request_kind},
        },
        "related_entities": [
            {
                "resource": "iam.member",
                "id": membership["user_id"],
                "ref": membership["username"],
                "facts": membership,
            }
        ],
        "verified_facts": {
            "request_status": "approved",
            "request_kind": request_kind,
            "membership_active": membership["active"] is True,
            "assignment_readback": True,
            "org_unit_code": membership.get("org_unit_code"),
            "position_code": membership.get("position_code"),
            "role_id": membership.get("role_id"),
        },
        "uncertainties": [],
        "affordances": [],
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
    }
    return {
        "ok": True,
        "request_id": request_id,
        "status": "approved",
        "request_kind": request_kind,
        "membership_active": True,
        "membership": membership,
        "verification": {
            "schema": "warehouse.domain-readback.v1",
            "verified": True,
            "source": "tenant_membership_readback",
        },
        "world_observation": observation,
        **({"already_processed": True} if already_processed else {}),
    }


def _audit(
    session,
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
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def approve_membership_request(
    actor: ActorContext,
    request_id: str,
    payload: dict[str, object] | None = None,
    *,
    expected_kind: str | None = None,
) -> dict[str, object]:
    """Activate the real tenant membership and close the platform request."""

    body = dict(payload or {})
    request_row = _load_request_for_review(
        actor,
        request_id,
        expected_kind=expected_kind,
    )
    if request_row["status"] == "approved":
        return _approval_result(actor, request_row, already_processed=True)
    if request_row["status"] != "pending":
        raise HTTPException(status_code=409, detail="Membership request is already rejected")

    org_unit_code = str(
        body.get("org_unit_code")
        or body.get("department")
        or request_row.get("requested_org_unit_code")
        or ""
    ).strip()
    position_code = str(
        body.get("position_code")
        or body.get("position")
        or request_row.get("requested_position_code")
        or ""
    ).strip()
    role_ref = str(
        body.get("role_id") or body.get("role") or request_row.get("requested_role_id") or ""
    ).strip()

    with tenant_session(actor.tenant_id) as session:
        position = None
        if position_code:
            position = (
                session.execute(
                    text(
                        """
                    SELECT position_code, department_code, role_level, role_name, name
                    FROM iam.position_profiles
                    WHERE tenant_id = :tenant_id AND position_code = :code AND active
                    """
                    ),
                    {"tenant_id": actor.tenant_id, "code": position_code},
                )
                .mappings()
                .one_or_none()
            )
            if position is None:
                raise HTTPException(status_code=422, detail="Requested position is unavailable")
            if org_unit_code and str(position["department_code"]) != org_unit_code:
                raise HTTPException(
                    status_code=422,
                    detail="Position does not belong to the requested organization unit",
                )
        if position is None:
            position = (
                session.execute(
                    text(
                        """
                    SELECT position_code, department_code, role_level, role_name, name
                    FROM iam.position_profiles
                    WHERE tenant_id = :tenant_id AND active
                      AND (:org_unit_code = '' OR department_code = :org_unit_code)
                    ORDER BY role_level, position_code
                    LIMIT 1
                    """
                    ),
                    {"tenant_id": actor.tenant_id, "org_unit_code": org_unit_code},
                )
                .mappings()
                .one_or_none()
            )

        role = None
        if role_ref:
            role = (
                session.execute(
                    text(
                        """
                    SELECT id, role_key, name, level
                    FROM iam.roles
                    WHERE tenant_id = :tenant_id AND active
                      AND (id::text = :role_ref OR role_key = :role_ref OR name = :role_ref)
                    ORDER BY level DESC
                    LIMIT 1
                    """
                    ),
                    {"tenant_id": actor.tenant_id, "role_ref": role_ref},
                )
                .mappings()
                .one_or_none()
            )
        if role is None and position is not None:
            role = (
                session.execute(
                    text(
                        """
                    SELECT id, role_key, name, level
                    FROM iam.roles
                    WHERE tenant_id = :tenant_id AND active
                      AND (role_key = :role_name OR name = :role_name)
                    ORDER BY level DESC
                    LIMIT 1
                    """
                    ),
                    {"tenant_id": actor.tenant_id, "role_name": position["role_name"]},
                )
                .mappings()
                .one_or_none()
            )

        position_level = int(position["role_level"]) if position else 1
        role_level = int(role["level"]) if role else 1
        effective_level = max(position_level, role_level)
        title = str(position["name"]) if position else str(role["name"]) if role else "Member"
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level,
                  topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, :role_level,
                  :role_level, :title
                )
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET active = true, position_code = EXCLUDED.position_code,
                  role_level = EXCLUDED.role_level,
                  topology_level = EXCLUDED.topology_level,
                  topology_title = EXCLUDED.topology_title
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "user_id": request_row["user_id"],
                "position_code": position["position_code"] if position else None,
                "role_level": effective_level,
                "title": title,
            },
        )
        if position:
            session.execute(
                text(
                    """
                    UPDATE iam.membership_positions
                    SET appointment_type = 'concurrent'
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                      AND active AND appointment_type = 'primary'
                      AND position_code <> :position_code
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": request_row["user_id"],
                    "position_code": position["position_code"],
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO iam.membership_positions(
                      tenant_id, user_id, position_code, appointment_type, active
                    ) VALUES (:tenant_id, :user_id, :position_code, 'primary', true)
                    ON CONFLICT (tenant_id, user_id, position_code)
                    DO UPDATE SET active = true, appointment_type = 'primary'
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": request_row["user_id"],
                    "position_code": position["position_code"],
                },
            )
        if role:
            session.execute(
                text(
                    """
                    INSERT INTO iam.membership_roles(tenant_id, user_id, role_id)
                    VALUES (:tenant_id, :user_id, :role_id)
                    ON CONFLICT (tenant_id, user_id, role_id) DO NOTHING
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "user_id": request_row["user_id"],
                    "role_id": role["id"],
                },
            )
        _audit(
            session,
            actor,
            "membership.request.approved",
            {
                "request_id": str(request_row["id"]),
                "user_id": str(request_row["user_id"]),
                "request_kind": request_row["request_kind"],
                "position_code": position["position_code"] if position else None,
                "role_id": str(role["id"]) if role else None,
            },
        )

    note = str(body.get("note") or "").strip()
    with system_session() as session:
        result = session.execute(
            text(
                """
                UPDATE platform.membership_requests
                SET status = 'approved', reviewed_by = :reviewed_by,
                    note = NULLIF(:note, '')
                WHERE id = :id AND tenant_id = :tenant_id AND status = 'pending'
                """
            ),
            {
                "id": request_row["id"],
                "tenant_id": actor.tenant_id,
                "reviewed_by": actor.user_id,
                "note": note,
            },
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Membership request changed during approval")
    return _approval_result(actor, request_row)


def reject_membership_request(
    actor: ActorContext,
    request_id: str,
    payload: dict[str, object] | None = None,
    *,
    expected_kind: str | None = None,
) -> dict[str, object]:
    """Reject the current tenant's request and retain the review reason."""

    body = dict(payload or {})
    request_row = _load_request_for_review(
        actor,
        request_id,
        expected_kind=expected_kind,
    )
    if request_row["status"] == "rejected":
        return {
            "ok": True,
            "request_id": str(request_row["id"]),
            "status": "rejected",
            "already_processed": True,
        }
    if request_row["status"] != "pending":
        raise HTTPException(status_code=409, detail="Membership request is already approved")
    note = str(body.get("note") or body.get("reason") or "").strip()
    with system_session() as session:
        result = session.execute(
            text(
                """
                UPDATE platform.membership_requests
                SET status = 'rejected', note = NULLIF(:note, ''),
                    reviewed_by = :reviewed_by
                WHERE id = :id AND tenant_id = :tenant_id AND status = 'pending'
                """
            ),
            {
                "id": request_row["id"],
                "tenant_id": actor.tenant_id,
                "note": note,
                "reviewed_by": actor.user_id,
            },
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=409, detail="Membership request changed during review")
    with tenant_session(actor.tenant_id) as session:
        _audit(
            session,
            actor,
            "membership.request.rejected",
            {
                "request_id": str(request_row["id"]),
                "user_id": str(request_row["user_id"]),
                "request_kind": request_row["request_kind"],
                "note": note,
            },
        )
    return {
        "ok": True,
        "request_id": str(request_row["id"]),
        "status": "rejected",
        "request_kind": request_row["request_kind"],
    }
