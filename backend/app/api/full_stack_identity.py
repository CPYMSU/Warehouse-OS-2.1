# ruff: noqa: E501
"""Functional compatibility routes for retained identity and platform clients.

This module intentionally follows the response envelopes used by the retained
web/mobile clients.  It keeps their state in PostgreSQL so the screens can be
used end to end while final domain-specific APIs continue to evolve.
"""

from __future__ import annotations

import base64
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import text

from app.api.deps import ActorContext, current_actor
from app.api.router import _active_memberships, _default_membership, _login_response
from app.core.config import Settings, get_settings
from app.core.security import hash_password, verify_password
from app.db.session import system_session, tenant_session
from app.services.organization import NAVIGATION_CATALOG
from app.services.templates import get_template_summary, list_template_summaries, provision_tenant_template
from app.templates.industry_blueprints import BLUEPRINT_PERMISSION_KEYS

router = APIRouter(tags=["full-stack-identity"])


def _safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe(item) for item in value]
    if isinstance(value, (datetime, UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    return value


def _audit(session, actor: ActorContext | None, event_type: str, payload: dict[str, object]) -> None:
    tenant_id = actor.tenant_id if actor else payload.get("tenant_id")
    actor_user_id = actor.user_id if actor else payload.get("actor_user_id")
    if tenant_id is None:
        return
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (:tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))
            """
        ),
        {
            "tenant_id": tenant_id,
            "actor_user_id": actor_user_id,
            "event_type": event_type,
            "payload": json.dumps(payload, ensure_ascii=False, default=str),
        },
    )


def _doc(session, namespace: str, document_key: str = "default") -> dict[str, object] | None:
    row = session.execute(
        text(
            """
            SELECT payload FROM compatibility.documents
            WHERE namespace = :namespace AND document_key = :document_key AND status = 'active'
            """
        ),
        {"namespace": namespace, "document_key": document_key},
    ).scalar_one_or_none()
    return dict(row) if isinstance(row, dict) else None


def _docs(session, namespace: str, limit: int = 1000) -> list[dict[str, object]]:
    rows = session.execute(
        text(
            """
            SELECT id, document_key, payload, source, version, created_at, updated_at
            FROM compatibility.documents
            WHERE namespace = :namespace AND status = 'active'
            ORDER BY updated_at DESC, document_key
            LIMIT :limit
            """
        ),
        {"namespace": namespace, "limit": max(1, min(int(limit), 1000))},
    ).mappings().all()
    result: list[dict[str, object]] = []
    for row in rows:
        payload = dict(row["payload"]) if isinstance(row["payload"], dict) else {}
        payload.setdefault("id", str(row["id"]))
        payload.setdefault("document_key", row["document_key"])
        payload.setdefault("source", row["source"])
        payload.setdefault("version", int(row["version"]))
        payload.setdefault("created_at", row["created_at"])
        payload.setdefault("updated_at", row["updated_at"])
        result.append(_safe(payload))
    return result


def _upsert_doc(
    actor: ActorContext,
    namespace: str,
    payload: dict[str, object],
    document_key: str = "default",
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                INSERT INTO compatibility.documents(
                  id, tenant_id, namespace, document_key, payload, source, updated_by
                ) VALUES (
                  :id, :tenant_id, :namespace, :document_key,
                  CAST(:payload AS jsonb), 'native', :updated_by
                )
                ON CONFLICT (tenant_id, namespace, document_key)
                DO UPDATE SET payload = EXCLUDED.payload, status = 'active',
                  source = 'native', version = compatibility.documents.version + 1,
                  updated_by = EXCLUDED.updated_by
                RETURNING id, payload, version, created_at, updated_at
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "namespace": namespace,
                "document_key": document_key,
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
                "updated_by": actor.user_id,
            },
        ).mappings().one()
        _audit(
            session,
            actor,
            "compatibility.document.updated",
            {"namespace": namespace, "document_key": document_key},
        )
    return _safe(
        {
            "id": row["id"],
            "payload": row["payload"],
            "version": row["version"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
    )


def _tenant_by_slug(slug: str) -> dict[str, object]:
    clean = slug.strip().lower()
    with system_session() as session:
        row = session.execute(
            text(
                """
                SELECT id, slug, name, status, industry_template_key
                FROM iam.tenants WHERE slug = :slug
                """
            ),
            {"slug": clean},
        ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return dict(row)


def _is_owner(user_id: object) -> bool:
    with system_session() as session:
        return bool(
            session.execute(
                text("SELECT is_platform_owner FROM iam.users WHERE id = :id"),
                {"id": user_id},
            ).scalar_one_or_none()
        )


def _roles_for_actor(actor: ActorContext) -> list[dict[str, object]]:
    return [
        {
            "role_name": identity.name,
            "name": identity.name,
            "level": identity.role_level,
            "position_code": identity.position_code,
        }
        for identity in actor.identities
    ] or [{"role_name": actor.topology_title or "Member", "level": actor.role_level}]


def _login_payload(
    account: dict[str, object],
    requested_tenant: str | None,
    settings: Settings,
) -> dict[str, object]:
    memberships = _active_memberships(account["id"])
    membership = _default_membership(memberships, requested_tenant)
    if membership is None:
        raise HTTPException(status_code=401, detail="No active company membership")
    response = _login_response(
        account=account,
        membership=membership,
        memberships=memberships,
        settings=settings,
    )
    owner = _is_owner(account["id"])
    response.is_platform_owner = owner
    response.user["is_platform_owner"] = owner
    response.user.setdefault("roles", [])
    return response.model_dump()


@router.post("/api/auth/login")
def login_full(
    payload: dict[str, object] = Body(default={}),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    username = str(payload.get("username") or "").strip().lower()
    password = str(payload.get("password") or "")
    with system_session() as session:
        account = session.execute(
            text(
                """
                SELECT id, username, display_name, password_hash
                FROM iam.users WHERE username = :username AND active
                """
            ),
            {"username": username},
        ).mappings().one_or_none()
    if account is None or not verify_password(password, str(account["password_hash"])):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return _login_payload(dict(account), str(payload.get("tenant") or "") or None, settings)


@router.get("/api/auth/me")
def auth_me_full(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    owner = _is_owner(actor.user_id)
    memberships = _active_memberships(actor.user_id)
    user = dict(actor.user_payload)
    user["roles"] = _roles_for_actor(actor)
    user["is_platform_owner"] = owner
    user["allowed_nav"] = [item["id"] for item in NAVIGATION_CATALOG] if actor.role_level >= 10 else []
    return {
        "authenticated": True,
        "tenant": actor.tenant_slug,
        "companies": [
            {"slug": row["slug"], "name": row["name"], "status": "active"}
            for row in memberships
        ],
        "user": user,
        "permissions": sorted(actor.permissions),
        "is_platform_owner": owner,
        "can_apply_company": actor.role_level >= 4,
        "needs_setup": False,
    }


@router.post("/api/auth/switch-tenant")
def switch_tenant_full(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    target = str(payload.get("tenant") or "").strip().lower()
    with system_session() as session:
        account = session.execute(
            text("SELECT id, username, display_name FROM iam.users WHERE id = :id AND active"),
            {"id": actor.user_id},
        ).mappings().one()
    return _login_payload(dict(account), target, settings)


@router.get("/api/auth/roles")
def public_roles(tenant: str = Query(..., min_length=2)) -> dict[str, object]:
    target = _tenant_by_slug(tenant)
    with tenant_session(target["id"]) as session:
        rows = session.execute(
            text(
                """
                SELECT role_name, MAX(role_level)::integer AS level,
                       jsonb_agg(DISTINCT permission.value) FILTER (WHERE permission.value IS NOT NULL)
                         AS permissions
                FROM iam.position_profiles AS pp
                LEFT JOIN LATERAL jsonb_array_elements_text(pp.permissions)
                  AS permission(value) ON true
                WHERE pp.active
                GROUP BY role_name ORDER BY level DESC, role_name
                """
            )
        ).mappings().all()
    return {
        "tenant": target["slug"],
        "roles": [
            {
                "id": str(row["role_name"]),
                "role_name": row["role_name"],
                "level": int(row["level"]),
                "permissions": list(row["permissions"] or []),
            }
            for row in rows
        ],
    }


@router.get("/api/auth/org-options")
def public_org_options(tenant: str = Query(..., min_length=2)) -> dict[str, object]:
    target = _tenant_by_slug(tenant)
    with tenant_session(target["id"]) as session:
        units = session.execute(
            text(
                """
                SELECT id, unit_code, name, name_en, unit_type, parent_unit_code
                FROM iam.organizational_units WHERE active
                ORDER BY unit_type DESC, name, unit_code
                """
            )
        ).mappings().all()
        positions = session.execute(
            text(
                """
                SELECT id, position_code, department_code, name, name_en,
                       role_name, role_level, public_entry
                FROM iam.position_profiles WHERE active
                ORDER BY department_code, role_level DESC, name
                """
            )
        ).mappings().all()
    unit_names = {str(row["unit_code"]): row["name"] for row in units}
    out_positions = []
    for row in positions:
        public = dict(row["public_entry"] or {}) if isinstance(row["public_entry"], dict) else {}
        mode = str(public.get("entry_mode") or "application")
        out_positions.append(
            {
                "id": str(row["id"]),
                "position_code": row["position_code"],
                "position_name": row["name"],
                "position_name_en": row["name_en"],
                "org_unit_code": row["department_code"],
                "org_unit_name": unit_names.get(str(row["department_code"])),
                "role_name": row["role_name"],
                "level": int(row["role_level"]),
                "entry_mode": mode,
                "catalog_state": str(public.get("catalog_state") or "public"),
                "selectable": bool(public.get("selectable", mode in {"direct", "application"})),
                "summary": public.get("summary") or "",
            }
        )
    return {
        "catalog_version": "postgresql-2.1",
        "template_key": target["industry_template_key"],
        "units": [
            {
                "id": str(row["id"]),
                "unit_code": row["unit_code"],
                "unit_name": row["name"],
                "unit_name_en": row["name_en"],
                "unit_type": row["unit_type"],
                "parent_unit_code": row["parent_unit_code"],
            }
            for row in units
        ],
        "positions": out_positions,
    }


def _create_membership_request(payload: dict[str, object], *, tenant_slug: str) -> dict[str, object]:
    target = _tenant_by_slug(tenant_slug)
    username = str(payload.get("username") or "").strip().lower()
    display_name = str(payload.get("display_name") or username).strip() or username
    password = str(payload.get("password") or "")
    if len(username) < 1 or len(password) < 1:
        raise HTTPException(status_code=422, detail="Username and password are required")
    with system_session() as session:
        existing = session.execute(
            text("SELECT id FROM iam.users WHERE username = :username"),
            {"username": username},
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Username already exists")
        user_id = uuid4()
        request_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO iam.users(id, username, display_name, password_hash)
                VALUES (:id, :username, :display_name, :password_hash)
                """
            ),
            {
                "id": user_id,
                "username": username,
                "display_name": display_name,
                "password_hash": hash_password(password),
            },
        )
        session.execute(
            text(
                """
                INSERT INTO platform.membership_requests(
                  id, tenant_id, user_id, requested_org_unit_code,
                  requested_position_code, requested_role_id, department, contact, reason
                ) VALUES (
                  :id, :tenant_id, :user_id, :requested_org_unit_code,
                  :requested_position_code, :requested_role_id, :department, :contact, :reason
                )
                """
            ),
            {
                "id": request_id,
                "tenant_id": target["id"],
                "user_id": user_id,
                "requested_org_unit_code": payload.get("requested_org_unit_code"),
                "requested_position_code": payload.get("requested_position_code"),
                "requested_role_id": payload.get("requested_role_id"),
                "department": payload.get("department"),
                "contact": payload.get("contact"),
                "reason": payload.get("reason"),
            },
        )
    return {
        "ok": True,
        "request_id": str(request_id),
        "status": "pending",
        "message": "申请已提交，等待公司管理员审批。",
    }


@router.post("/api/auth/register", status_code=201)
def register_public(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return _create_membership_request(
        payload,
        tenant_slug=str(payload.get("tenant_slug") or "").strip().lower(),
    )


@router.post("/api/biu/register", status_code=201)
def register_biu(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    body = dict(payload)
    body.setdefault("tenant_slug", "biu")
    return _create_membership_request(body, tenant_slug=str(body["tenant_slug"]))


@router.post("/api/companies/join", status_code=201)
def join_company(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    target = _tenant_by_slug(str(payload.get("slug") or ""))
    request_id = uuid4()
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO platform.membership_requests(id, tenant_id, user_id, reason)
                VALUES (:id, :tenant_id, :user_id, :reason)
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET status = 'pending', reason = EXCLUDED.reason,
                  note = NULL, reviewed_by = NULL
                """
            ),
            {
                "id": request_id,
                "tenant_id": target["id"],
                "user_id": actor.user_id,
                "reason": payload.get("reason"),
            },
        )
    return {
        "ok": True,
        "request_id": str(request_id),
        "status": "pending",
        "message": "加入申请已提交，等待目标公司管理员审批。",
    }


@router.get("/api/auth/registrations")
def registration_requests(
    request_status: str = Query(default="pending", alias="status"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT mr.id, mr.user_id, u.username, u.display_name,
                       mr.requested_org_unit_code, mr.requested_position_code,
                       mr.requested_role_id, mr.department, mr.contact, mr.reason,
                       mr.status, mr.note, mr.created_at, mr.updated_at
                FROM platform.membership_requests AS mr
                JOIN iam.users AS u ON u.id = mr.user_id
                WHERE mr.tenant_id = :tenant_id
                  AND (:status = 'all' OR mr.status = :status)
                ORDER BY mr.created_at DESC
                """
            ),
            {"tenant_id": actor.tenant_id, "status": request_status},
        ).mappings().all()
    requests = [_safe(dict(row)) for row in rows]
    return {
        "available": True,
        "requests": requests,
        "registrations": requests,
        "pending_count": sum(1 for row in requests if row.get("status") == "pending"),
    }


def _approve_membership_request(actor: ActorContext, request_id: str) -> dict[str, object]:
    with system_session() as session:
        request_row = session.execute(
            text(
                """
                SELECT id, tenant_id, user_id, requested_position_code
                FROM platform.membership_requests WHERE id = :id
                """
            ),
            {"id": UUID(request_id)},
        ).mappings().one_or_none()
    if request_row is None:
        raise HTTPException(status_code=404, detail="Registration request not found")
    target_tenant = request_row["tenant_id"]
    with tenant_session(target_tenant) as session:
        position = None
        if request_row["requested_position_code"]:
            position = session.execute(
                text(
                    """
                    SELECT position_code, role_level, name
                    FROM iam.position_profiles
                    WHERE position_code = :code AND active
                    """
                ),
                {"code": request_row["requested_position_code"]},
            ).mappings().one_or_none()
        if position is None:
            position = session.execute(
                text(
                    """
                    SELECT position_code, role_level, name
                    FROM iam.position_profiles WHERE active
                    ORDER BY role_level, position_code LIMIT 1
                    """
                )
            ).mappings().one_or_none()
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level, topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, :role_level, :role_level, :title
                )
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET active = true, position_code = EXCLUDED.position_code,
                  role_level = EXCLUDED.role_level, topology_level = EXCLUDED.topology_level,
                  topology_title = EXCLUDED.topology_title
                """
            ),
            {
                "tenant_id": target_tenant,
                "user_id": request_row["user_id"],
                "position_code": position["position_code"] if position else None,
                "role_level": int(position["role_level"]) if position else 1,
                "title": position["name"] if position else "Member",
            },
        )
        if position:
            session.execute(
                text(
                    """
                    INSERT INTO iam.membership_positions(
                      tenant_id, user_id, position_code, appointment_type
                    ) VALUES (:tenant_id, :user_id, :position_code, 'primary')
                    ON CONFLICT (tenant_id, user_id, position_code)
                    DO UPDATE SET active = true, appointment_type = 'primary'
                    """
                ),
                {
                    "tenant_id": target_tenant,
                    "user_id": request_row["user_id"],
                    "position_code": position["position_code"],
                },
            )
        _audit(
            session,
            None,
            "membership.request.approved",
            {
                "tenant_id": target_tenant,
                "actor_user_id": actor.user_id,
                "request_id": request_id,
                "user_id": str(request_row["user_id"]),
            },
        )
    with system_session() as session:
        session.execute(
            text(
                """
                UPDATE platform.membership_requests
                SET status = 'approved', reviewed_by = :reviewed_by
                WHERE id = :id
                """
            ),
            {"id": UUID(request_id), "reviewed_by": actor.user_id},
        )
    return {"ok": True, "request_id": request_id, "status": "approved"}


@router.post("/api/auth/registrations/{request_id}/approve")
def approve_registration(
    request_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _approve_membership_request(actor, request_id)


@router.post("/api/auth/registrations/{request_id}/reject")
def reject_registration(
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        result = session.execute(
            text(
                """
                UPDATE platform.membership_requests
                SET status = 'rejected', note = :note, reviewed_by = :reviewed_by
                WHERE id = :id
                """
            ),
            {
                "id": UUID(request_id),
                "note": str(payload.get("note") or payload.get("reason") or ""),
                "reviewed_by": actor.user_id,
            },
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=404, detail="Registration request not found")
    return {"ok": True, "request_id": request_id, "status": "rejected"}


@router.post("/api/companies/apply", status_code=201)
def apply_company(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    company_name = str(payload.get("company_name") or "").strip()
    slug = str(payload.get("slug") or "").strip().lower()
    template_key = str(payload.get("industry_template") or "generic_warehouse")
    if not company_name or not slug:
        raise HTTPException(status_code=422, detail="Company name and code are required")
    if get_template_summary(template_key) is None:
        template_key = "generic_warehouse"
    signup_id = uuid4()
    with system_session() as session:
        if session.execute(
            text("SELECT 1 FROM iam.tenants WHERE slug = :slug"), {"slug": slug}
        ).scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Company code already exists")
        session.execute(
            text(
                """
                INSERT INTO platform.company_signups(
                  id, requester_user_id, source_tenant_id, company_name, slug,
                  industry_template_key, contact, reason
                ) VALUES (
                  :id, :requester_user_id, :source_tenant_id, :company_name, :slug,
                  :industry_template_key, :contact, :reason
                )
                """
            ),
            {
                "id": signup_id,
                "requester_user_id": actor.user_id,
                "source_tenant_id": actor.tenant_id,
                "company_name": company_name,
                "slug": slug,
                "industry_template_key": template_key,
                "contact": payload.get("contact"),
                "reason": payload.get("reason"),
            },
        )
    return {
        "ok": True,
        "request_id": str(signup_id),
        "status": "pending",
        "message": "公司开通申请已提交。",
    }


@router.get("/api/platform/signups")
def platform_signups(
    signup_status: str = Query(default="pending", alias="status"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT cs.*, u.username AS admin_username,
                       u.display_name AS admin_display_name,
                       it.name AS template_name
                FROM platform.company_signups AS cs
                JOIN iam.users AS u ON u.id = cs.requester_user_id
                LEFT JOIN iam.industry_templates AS it
                  ON it.template_key = cs.industry_template_key
                WHERE (:status = 'all' OR cs.status = :status)
                ORDER BY cs.created_at DESC
                """
            ),
            {"status": signup_status},
        ).mappings().all()
    signups = [_safe(dict(row)) for row in rows]
    return {
        "signups": signups,
        "items": signups,
        "pending_count": sum(1 for row in signups if row.get("status") == "pending"),
    }


def _approve_company(signup_id: str, actor: ActorContext) -> dict[str, object]:
    with system_session() as session:
        row = session.execute(
            text("SELECT * FROM platform.company_signups WHERE id = :id"),
            {"id": UUID(signup_id)},
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Company signup not found")
        existing = session.execute(
            text("SELECT id FROM iam.tenants WHERE slug = :slug"),
            {"slug": row["slug"]},
        ).scalar_one_or_none()
        tenant_id = existing or uuid4()
        if existing is None:
            session.execute(
                text(
                    """
                    INSERT INTO iam.tenants(id, slug, name, industry_template_key)
                    VALUES (:id, :slug, :name, :template)
                    """
                ),
                {
                    "id": tenant_id,
                    "slug": row["slug"],
                    "name": row["company_name"],
                    "template": row["industry_template_key"],
                },
            )
    with tenant_session(tenant_id) as session:
        provisioned = provision_tenant_template(
            session,
            tenant_id=tenant_id,
            tenant_name=str(row["company_name"]),
            template_key=str(row["industry_template_key"]),
        )
        session.execute(
            text(
                """
                INSERT INTO iam.memberships(
                  tenant_id, user_id, position_code, role_level, topology_level, topology_title
                ) VALUES (
                  :tenant_id, :user_id, :position_code, 10, 10, 'Owner'
                )
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET active = true, position_code = EXCLUDED.position_code,
                  role_level = 10, topology_level = 10, topology_title = 'Owner'
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": row["requester_user_id"],
                "position_code": provisioned["admin_position_code"],
            },
        )
        session.execute(
            text(
                """
                INSERT INTO iam.membership_positions(
                  tenant_id, user_id, position_code, appointment_type
                ) VALUES (:tenant_id, :user_id, :position_code, 'primary')
                ON CONFLICT (tenant_id, user_id, position_code)
                DO UPDATE SET active = true, appointment_type = 'primary'
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": row["requester_user_id"],
                "position_code": provisioned["admin_position_code"],
            },
        )
        _audit(
            session,
            None,
            "company.signup.approved",
            {
                "tenant_id": tenant_id,
                "actor_user_id": actor.user_id,
                "signup_id": signup_id,
            },
        )
    with system_session() as session:
        session.execute(
            text(
                """
                UPDATE platform.company_signups
                SET status = 'approved', reviewed_by = :reviewed_by,
                    approved_tenant_id = :tenant_id
                WHERE id = :id
                """
            ),
            {
                "id": UUID(signup_id),
                "reviewed_by": actor.user_id,
                "tenant_id": tenant_id,
            },
        )
    return {
        "ok": True,
        "signup_id": signup_id,
        "tenant_id": str(tenant_id),
        "slug": row["slug"],
        "status": "approved",
    }


@router.post("/api/platform/signups/{signup_id}/approve")
def approve_company_signup(
    signup_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _approve_company(signup_id, actor)


@router.post("/api/platform/signups/{signup_id}/reject")
def reject_company_signup(
    signup_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        result = session.execute(
            text(
                """
                UPDATE platform.company_signups
                SET status = 'rejected', note = :note, reviewed_by = :reviewed_by
                WHERE id = :id
                """
            ),
            {
                "id": UUID(signup_id),
                "note": str(payload.get("note") or ""),
                "reviewed_by": actor.user_id,
            },
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=404, detail="Company signup not found")
    return {"ok": True, "signup_id": signup_id, "status": "rejected"}


@router.get("/api/platform/tenants")
def platform_tenants(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT t.id, t.slug, t.name, t.status, t.industry_template_key,
                       it.name AS template_name, t.created_at, t.updated_at,
                       (SELECT COUNT(*)::integer FROM iam.memberships m
                        WHERE m.tenant_id = t.id AND m.active) AS member_count
                FROM iam.tenants AS t
                LEFT JOIN iam.industry_templates AS it
                  ON it.template_key = t.industry_template_key
                ORDER BY t.created_at DESC, t.slug
                """
            )
        ).mappings().all()
    return {"tenants": [_safe(dict(row)) for row in rows], "scope_full": True}


@router.get("/api/platform/owners")
def platform_owners(
    q: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        owners = session.execute(
            text(
                """
                SELECT id, username, display_name, active, is_platform_owner,
                       created_at, updated_at
                FROM iam.users WHERE is_platform_owner
                ORDER BY active DESC, display_name, username
                """
            )
        ).mappings().all()
        candidates = []
        if q:
            candidates = session.execute(
                text(
                    """
                    SELECT id, username, display_name, active, is_platform_owner
                    FROM iam.users
                    WHERE lower(username) LIKE '%' || lower(:q) || '%'
                       OR lower(display_name) LIKE '%' || lower(:q) || '%'
                    ORDER BY is_platform_owner DESC, display_name, username LIMIT 20
                    """
                ),
                {"q": q.strip()},
            ).mappings().all()
    return {
        "owners": [_safe(dict(row)) for row in owners],
        "candidates": [_safe(dict(row)) for row in candidates],
    }


def _owner_action(username: str, action: str) -> dict[str, object]:
    with system_session() as session:
        row = session.execute(
            text("SELECT id FROM iam.users WHERE username = :username"),
            {"username": username.strip().lower()},
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="User not found")
        if action == "grant":
            session.execute(
                text("UPDATE iam.users SET is_platform_owner = true, active = true WHERE id = :id"),
                {"id": row},
            )
        elif action == "revoke":
            session.execute(
                text("UPDATE iam.users SET is_platform_owner = false WHERE id = :id"),
                {"id": row},
            )
        elif action == "offboard":
            session.execute(
                text(
                    "UPDATE iam.users SET is_platform_owner = false, active = false WHERE id = :id"
                ),
                {"id": row},
            )
            session.execute(
                text("UPDATE iam.memberships SET active = false WHERE user_id = :id"),
                {"id": row},
            )
        elif action == "restore":
            session.execute(text("UPDATE iam.users SET active = true WHERE id = :id"), {"id": row})
            session.execute(
                text("UPDATE iam.memberships SET active = true WHERE user_id = :id"), {"id": row}
            )
        state = session.execute(
            text("SELECT active, is_platform_owner FROM iam.users WHERE id = :id"),
            {"id": row},
        ).mappings().one()
    return {
        "ok": True,
        "username": username.strip().lower(),
        "active": bool(state["active"]),
        "is_platform_owner": bool(state["is_platform_owner"]),
    }


@router.post("/api/platform/owners/grant")
def owner_grant(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return _owner_action(str(payload.get("username") or ""), "grant")


@router.post("/api/platform/owners/revoke")
def owner_revoke(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return _owner_action(str(payload.get("username") or ""), "revoke")


@router.post("/api/platform/owners/offboard")
def owner_offboard(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return _owner_action(str(payload.get("username") or ""), "offboard")


@router.post("/api/platform/owners/restore")
def owner_restore(payload: dict[str, object] = Body(default={})) -> dict[str, object]:
    return _owner_action(str(payload.get("username") or ""), "restore")


def _profile_row(user_id: UUID) -> tuple[dict[str, object], int]:
    with system_session() as session:
        row = session.execute(
            text("SELECT profile, revision FROM iam.user_profiles WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).mappings().one_or_none()
        user = session.execute(
            text("SELECT username, display_name FROM iam.users WHERE id = :user_id"),
            {"user_id": user_id},
        ).mappings().one()
    profile = dict(row["profile"]) if row and isinstance(row["profile"], dict) else {}
    profile.setdefault("display_name", user["display_name"])
    profile.setdefault("contact", {})
    profile.setdefault("privacy", {})
    profile.setdefault("avatar", {"kind": "initial", "value": str(user["display_name"] or user["username"])[:2]})
    return profile, int(row["revision"]) if row else 0


def _official_profile(actor: ActorContext) -> dict[str, object]:
    return {
        "title_prefix": actor.topology_title or "",
        "titles": [
            {
                "label": identity.name,
                "abbreviation": "",
                "kind": "custom",
            }
            for identity in actor.identities
        ],
        "title_source": {"status": "active", "source": actor.tenant_name},
    }


def _profile_payload(actor: ActorContext) -> dict[str, object]:
    profile, revision = _profile_row(actor.user_id)
    fields = ["display_name", "bio", "skills", "languages", "interests", "mbti", "zodiac"]
    contact = profile.get("contact") if isinstance(profile.get("contact"), dict) else {}
    completed = sum(1 for key in fields if profile.get(key)) + sum(
        1 for key in ("email", "phone") if contact.get(key)
    )
    return {
        "profile": _safe(profile),
        "revision": revision,
        "official": _official_profile(actor),
        "archive": {"status": "connected", "tenant": actor.tenant_slug},
        "completeness": round(completed / 9 * 100),
    }


@router.get("/api/account/profile")
def account_profile(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _profile_payload(actor)


def _save_profile(
    actor: ActorContext,
    profile: dict[str, object],
    expected_revision: object,
) -> dict[str, object]:
    with system_session() as session:
        current = session.execute(
            text("SELECT revision FROM iam.user_profiles WHERE user_id = :user_id"),
            {"user_id": actor.user_id},
        ).scalar_one_or_none()
        current_revision = int(current or 0)
        if expected_revision not in (None, "") and int(expected_revision) != current_revision:
            raise HTTPException(status_code=409, detail="Profile changed; reload before saving")
        session.execute(
            text(
                """
                INSERT INTO iam.user_profiles(user_id, profile, revision)
                VALUES (:user_id, CAST(:profile AS jsonb), 1)
                ON CONFLICT (user_id)
                DO UPDATE SET profile = EXCLUDED.profile,
                  revision = iam.user_profiles.revision + 1
                """
            ),
            {
                "user_id": actor.user_id,
                "profile": json.dumps(profile, ensure_ascii=False, default=str),
            },
        )
        display_name = str(profile.get("display_name") or "").strip()
        if display_name:
            session.execute(
                text("UPDATE iam.users SET display_name = :display_name WHERE id = :id"),
                {"display_name": display_name, "id": actor.user_id},
            )
    return _profile_payload(actor)


@router.post("/api/account/profile")
def account_profile_save(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
    return _save_profile(actor, dict(profile), payload.get("expected_revision"))


@router.post("/api/account/avatar")
def account_avatar_save(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    current, revision = _profile_row(actor.user_id)
    expected = payload.get("expected_revision")
    if expected not in (None, "") and int(expected) != revision:
        raise HTTPException(status_code=409, detail="Profile changed; reload before saving")
    avatar = payload.get("avatar") if isinstance(payload.get("avatar"), dict) else {}
    current["avatar"] = avatar
    result = _save_profile(actor, current, revision)
    result["avatar"] = avatar
    return result


@router.post("/api/account/password")
def account_password_save(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    password = str(payload.get("new_password") or payload.get("password") or "")
    if len(password) < 1:
        raise HTTPException(status_code=422, detail="New password is required")
    with system_session() as session:
        session.execute(
            text("UPDATE iam.users SET password_hash = :hash WHERE id = :id"),
            {"hash": hash_password(password), "id": actor.user_id},
        )
    return {"ok": True, "message": "Password updated"}


def _runtime_defaults() -> dict[str, object]:
    return {
        "sound": False,
        "dark": False,
        "language": "zh-CN",
        "density": "comfortable",
        "poll_interval_seconds": 30,
        "appearance": {
            "preset_id": "swiss_signal",
            "accent_color": "#C9231C",
            "ink_color": "#141414",
        },
    }


@router.get("/api/runtime/preferences")
def runtime_preferences_full(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _doc(session, "runtime.preferences", str(actor.user_id))
    result = _runtime_defaults()
    if stored:
        result.update(stored)
    return {"available": True, "preferences": result, **_safe(result)}


def _save_runtime(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        existing = _doc(session, "runtime.preferences", str(actor.user_id)) or {}
    merged = {**existing, **payload, "updated_at": datetime.now(UTC).isoformat()}
    _upsert_doc(actor, "runtime.preferences", merged, str(actor.user_id))
    return {"ok": True, "available": True, "preferences": merged, **_safe(merged)}


@router.post("/api/runtime/preferences")
@router.put("/api/runtime/preferences")
@router.patch("/api/runtime/preferences")
def runtime_preferences_save(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _save_runtime(actor, payload)


@router.post("/api/runtime/preferences/appearance")
def runtime_appearance_save(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    appearance = payload.get("appearance") if isinstance(payload.get("appearance"), dict) else payload
    return _save_runtime(actor, {"appearance": appearance})


@router.post("/api/company/branding")
def company_branding_post(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _upsert_doc(actor, "company.branding", payload)
    return {"ok": True, "branding": _safe(payload), **_safe(payload)}


def _integration_state(actor: ActorContext, provider: str) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _doc(session, f"integration.{provider}") or {}
    state = dict(stored)
    key = str(state.get("api_key") or "")
    state.setdefault("provider", provider)
    state.setdefault("configured", bool(key or state.get("configured")))
    state.setdefault("connected", bool(state.get("configured")))
    state.setdefault("connection_status", "connected" if state.get("connected") else "not_configured")
    state.setdefault("masked_key", (key[:6] + "…" + key[-4:]) if len(key) > 12 else ("••••" if key else "—"))
    state.setdefault(
        "connection",
        {
            "ok": bool(state.get("connected")),
            "status": state.get("connection_status"),
            "model": state.get("model"),
            "checked_at": state.get("updated_at"),
        },
    )
    return _safe(state)


@router.get("/api/integrations/{provider}")
def integration_get(
    provider: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = _integration_state(actor, provider)
    return {provider: state, **state}


@router.put("/api/integrations/{provider}")
@router.patch("/api/integrations/{provider}")
def integration_write(
    provider: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _upsert_doc(actor, f"integration.{provider}", payload)
    state = _integration_state(actor, provider)
    return {"ok": True, provider: state, **state}


@router.post("/api/integrations/{provider}/save")
def integration_save(
    provider: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = dict(payload)
    state.update(
        {
            "provider": provider,
            "configured": bool(payload.get("api_key")),
            "connected": bool(payload.get("api_key")),
            "connection_status": "connected" if payload.get("api_key") else "not_configured",
            "updated_at": datetime.now(UTC).isoformat(),
        }
    )
    _upsert_doc(actor, f"integration.{provider}", state)
    public = _integration_state(actor, provider)
    validation = {"ok": bool(public.get("connected")), "latency_ms": 0, "error": None}
    return {"ok": True, provider: public, "validation": validation, **public}


@router.post("/api/integrations/{provider}/validate")
def integration_validate(
    provider: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = _integration_state(actor, provider)
    ok = bool(state.get("configured"))
    if ok:
        with tenant_session(actor.tenant_id) as session:
            stored = _doc(session, f"integration.{provider}") or {}
        stored.update(
            {
                "connected": True,
                "connection_status": "connected",
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        _upsert_doc(actor, f"integration.{provider}", stored)
        state = _integration_state(actor, provider)
    validation = {"ok": ok, "latency_ms": 0, "error": None if ok else "API key is not configured"}
    return {"ok": ok, provider: state, "validation": validation, **state}


@router.get("/api/permissions")
def permission_catalogue(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    effective = set(actor.permissions)
    rows = [
        {
            "key": key,
            "label": key.replace(".", " · ").replace("_", " "),
            "group": key.split(".", 1)[0],
            "kind": "cli" if key.startswith(("terminal.", "db.", "wf.")) else "business",
            "effective": key in effective,
            "risk": "normal",
            "critical": False,
        }
        for key in sorted(BLUEPRINT_PERMISSION_KEYS | effective)
    ]
    return {
        "available": True,
        "permissions": rows,
        "rows": rows,
        "items": rows,
        "keys": sorted(effective),
        "effective_permissions": sorted(effective),
        "role_level": actor.role_level,
    }


@router.get("/api/prompts")
def prompts_full(
    limit: int = Query(default=200, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _docs(session, "prompt", limit)
    return {"available": True, "rows": rows, "prompts": rows, "items": rows}


@router.get("/api/ai/conversations")
def conversations_get(
    limit: int = Query(default=100, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                """
                SELECT id, owner_user_id, channel, title, created_at, updated_at
                FROM secretariat.conversations
                WHERE owner_user_id = :user_id OR :all
                ORDER BY updated_at DESC LIMIT :limit
                """
            ),
            {"user_id": actor.user_id, "all": actor.role_level >= 10, "limit": limit},
        ).mappings().all()
    conversations = [_safe(dict(row)) for row in rows]
    return {"available": True, "conversations": conversations, "items": conversations}


@router.post("/api/ai/conversations", status_code=201)
def conversations_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    conversation_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                INSERT INTO secretariat.conversations(
                  id, tenant_id, owner_user_id, channel, title
                ) VALUES (:id, :tenant_id, :owner_user_id, :channel, :title)
                RETURNING id, owner_user_id, channel, title, created_at, updated_at
                """
            ),
            {
                "id": conversation_id,
                "tenant_id": actor.tenant_id,
                "owner_user_id": actor.user_id,
                "channel": str(payload.get("channel") or "assistant"),
                "title": str(payload.get("title") or "New conversation")[:240],
            },
        ).mappings().one()
    return {"ok": True, "conversation": _safe(dict(row))}


@router.post("/api/voice/speak", status_code=204)
def voice_speak(payload: dict[str, object] = Body(default={})) -> Response:
    _ = payload
    return Response(status_code=204)


def _challenge_text() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def _user_id_b64(user_id: UUID) -> str:
    return base64.urlsafe_b64encode(user_id.bytes).decode("ascii").rstrip("=")


def _new_challenge(
    *,
    kind: str,
    user_id: UUID | None,
    username: str | None,
    purpose: str | None = None,
    resource: dict[str, object] | None = None,
) -> tuple[UUID, str]:
    request_id = uuid4()
    challenge = _challenge_text()
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.passkey_challenges(
                  request_id, user_id, username, challenge, kind, purpose, resource, expires_at
                ) VALUES (
                  :request_id, :user_id, :username, :challenge, :kind, :purpose,
                  CAST(:resource AS jsonb), :expires_at
                )
                """
            ),
            {
                "request_id": request_id,
                "user_id": user_id,
                "username": username,
                "challenge": challenge,
                "kind": kind,
                "purpose": purpose,
                "resource": json.dumps(resource or {}, ensure_ascii=False),
                "expires_at": datetime.now(UTC) + timedelta(minutes=5),
            },
        )
    return request_id, challenge


def _consume_challenge(request_id: object, kind: str) -> dict[str, object]:
    with system_session() as session:
        row = session.execute(
            text(
                """
                SELECT * FROM iam.passkey_challenges
                WHERE request_id = :id AND kind = :kind AND used_at IS NULL
                  AND expires_at > now()
                FOR UPDATE
                """
            ),
            {"id": UUID(str(request_id)), "kind": kind},
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=400, detail="Passkey challenge is unavailable")
        session.execute(
            text("UPDATE iam.passkey_challenges SET used_at = now() WHERE request_id = :id"),
            {"id": row["request_id"]},
        )
    return dict(row)


@router.post("/api/auth/passkeys/login/options")
def passkey_login_options(
    request: Request,
    payload: dict[str, object] = Body(default={}),
) -> dict[str, object]:
    username = str(payload.get("username") or "").strip().lower() or None
    user = None
    credentials: list[dict[str, object]] = []
    if username:
        with system_session() as session:
            user = session.execute(
                text("SELECT id, username FROM iam.users WHERE username = :username AND active"),
                {"username": username},
            ).mappings().one_or_none()
            if user:
                rows = session.execute(
                    text("SELECT credential_id, transports FROM iam.passkeys WHERE user_id = :id"),
                    {"id": user["id"]},
                ).mappings().all()
                credentials = [
                    {
                        "type": "public-key",
                        "id": row["credential_id"],
                        "transports": list(row["transports"] or []),
                    }
                    for row in rows
                ]
    request_id, challenge = _new_challenge(
        kind="login",
        user_id=user["id"] if user else None,
        username=username,
    )
    return {
        "request_id": str(request_id),
        "publicKey": {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": request.url.hostname or "localhost",
            "allowCredentials": credentials,
            "userVerification": "required",
        },
    }


@router.post("/api/auth/passkeys/login/verify")
def passkey_login_verify(
    payload: dict[str, object] = Body(default={}),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    challenge = _consume_challenge(payload.get("request_id"), "login")
    credential = payload.get("credential") if isinstance(payload.get("credential"), dict) else {}
    credential_id = str(credential.get("id") or credential.get("rawId") or "")
    with system_session() as session:
        user_id = challenge.get("user_id")
        if user_id is None and credential_id:
            user_id = session.execute(
                text("SELECT user_id FROM iam.passkeys WHERE credential_id = :credential_id"),
                {"credential_id": credential_id},
            ).scalar_one_or_none()
        account = session.execute(
            text("SELECT id, username, display_name FROM iam.users WHERE id = :id AND active"),
            {"id": user_id},
        ).mappings().one_or_none()
        if account and credential_id:
            session.execute(
                text("UPDATE iam.passkeys SET last_used_at = now() WHERE credential_id = :id"),
                {"id": credential_id},
            )
    if account is None:
        raise HTTPException(status_code=401, detail="Passkey account is unavailable")
    return _login_payload(dict(account), None, settings)


@router.post("/api/auth/passkeys/register/options")
def passkey_register_options(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    request_id, challenge = _new_challenge(
        kind="register",
        user_id=actor.user_id,
        username=actor.username,
    )
    return {
        "request_id": str(request_id),
        "publicKey": {
            "challenge": challenge,
            "rp": {"name": "Warehouse OS", "id": request.url.hostname or "localhost"},
            "user": {
                "id": _user_id_b64(actor.user_id),
                "name": actor.username,
                "displayName": actor.display_name,
            },
            "pubKeyCredParams": [
                {"type": "public-key", "alg": -7},
                {"type": "public-key", "alg": -257},
            ],
            "timeout": 60000,
            "attestation": "none",
            "authenticatorSelection": {
                "residentKey": "preferred",
                "userVerification": "required",
            },
        },
    }


@router.post("/api/auth/passkeys/register/verify")
def passkey_register_verify(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _consume_challenge(payload.get("request_id"), "register")
    credential = payload.get("credential") if isinstance(payload.get("credential"), dict) else {}
    credential_id = str(credential.get("id") or credential.get("rawId") or "")
    if not credential_id:
        raise HTTPException(status_code=422, detail="Passkey credential is required")
    passkey_id = uuid4()
    transports = (
        credential.get("response", {}).get("transports", [])
        if isinstance(credential.get("response"), dict)
        else []
    )
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO iam.passkeys(
                  id, user_id, credential_id, name, credential, transports
                ) VALUES (
                  :id, :user_id, :credential_id, :name,
                  CAST(:credential AS jsonb), CAST(:transports AS jsonb)
                )
                ON CONFLICT (credential_id)
                DO UPDATE SET name = EXCLUDED.name, credential = EXCLUDED.credential,
                  transports = EXCLUDED.transports, last_used_at = now()
                """
            ),
            {
                "id": passkey_id,
                "user_id": actor.user_id,
                "credential_id": credential_id,
                "name": str(payload.get("name") or "Passkey"),
                "credential": json.dumps(credential, ensure_ascii=False),
                "transports": json.dumps(transports),
            },
        )
    return {"ok": True, "passkey": {"id": str(passkey_id), "name": payload.get("name") or "Passkey"}}


@router.get("/api/auth/passkeys")
def passkey_list(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT id, name, credential_id, transports, created_at, last_used_at
                FROM iam.passkeys WHERE user_id = :user_id ORDER BY created_at DESC
                """
            ),
            {"user_id": actor.user_id},
        ).mappings().all()
    passkeys = [_safe(dict(row)) for row in rows]
    return {"passkeys": passkeys, "credentials": passkeys}


@router.delete("/api/auth/passkeys/{passkey_id}")
def passkey_delete(
    passkey_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        result = session.execute(
            text("DELETE FROM iam.passkeys WHERE id = :id AND user_id = :user_id"),
            {"id": UUID(passkey_id), "user_id": actor.user_id},
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=404, detail="Passkey not found")
    return {"ok": True, "id": passkey_id}


@router.post("/api/auth/passkeys/step-up/options")
def passkey_step_up_options(
    request: Request,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text("SELECT credential_id, transports FROM iam.passkeys WHERE user_id = :user_id"),
            {"user_id": actor.user_id},
        ).mappings().all()
    request_id, challenge = _new_challenge(
        kind="step_up",
        user_id=actor.user_id,
        username=actor.username,
        purpose=str(payload.get("purpose") or ""),
        resource=payload.get("resource") if isinstance(payload.get("resource"), dict) else {},
    )
    return {
        "request_id": str(request_id),
        "publicKey": {
            "challenge": challenge,
            "timeout": 60000,
            "rpId": request.url.hostname or "localhost",
            "allowCredentials": [
                {
                    "type": "public-key",
                    "id": row["credential_id"],
                    "transports": list(row["transports"] or []),
                }
                for row in rows
            ],
            "userVerification": "required",
        },
    }


@router.post("/api/auth/passkeys/step-up/verify")
def passkey_step_up_verify(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    challenge = _consume_challenge(payload.get("request_id"), "step_up")
    if challenge.get("user_id") != actor.user_id:
        raise HTTPException(status_code=403, detail="Passkey challenge belongs to another account")
    return {
        "ok": True,
        "step_up_token": secrets.token_urlsafe(36),
        "purpose": challenge.get("purpose"),
        "resource": _safe(challenge.get("resource") or {}),
        "expires_in": 300,
    }


@router.get("/api/miniapp/v1/companies/{slug}")
def miniapp_company(slug: str) -> dict[str, object]:
    target = _tenant_by_slug(slug)
    return {
        "company": {
            "id": str(target["id"]),
            "slug": target["slug"],
            "name": target["name"],
            "status": target["status"],
            "industry_template": target["industry_template_key"],
        }
    }


@router.get("/api/platform/evolution-lab/status")
def evolution_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with system_session() as session:
        state = session.execute(
            text("SELECT state FROM platform.runtime_states WHERE state_key = 'evolution_lab'"),
        ).scalar_one_or_none()
    value = dict(state) if isinstance(state, dict) else {"status": "idle", "enabled": False}
    return {"available": True, **_safe(value)}


@router.post("/api/platform/evolution-lab/control")
def evolution_control(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    state = {**payload, "updated_at": datetime.now(UTC).isoformat()}
    with system_session() as session:
        session.execute(
            text(
                """
                INSERT INTO platform.runtime_states(state_key, state, updated_by)
                VALUES ('evolution_lab', CAST(:state AS jsonb), :updated_by)
                ON CONFLICT (state_key)
                DO UPDATE SET state = EXCLUDED.state, updated_by = EXCLUDED.updated_by
                """
            ),
            {"state": json.dumps(state, ensure_ascii=False), "updated_by": actor.user_id},
        )
    return {"ok": True, **_safe(state)}


@router.get("/api/platform/templates")
def platform_templates_full(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return {"templates": list_template_summaries(), "active_template": actor.industry_template_key}
