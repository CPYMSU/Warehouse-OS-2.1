# ruff: noqa: E501
"""Functional compatibility routes for retained identity and platform clients.

This module intentionally follows the response envelopes used by the retained
web/mobile clients.  It keeps their state in PostgreSQL so the screens can be
used end to end while final domain-specific APIs continue to evolve.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from webauthn import verify_authentication_response, verify_registration_response
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.exceptions import (
    InvalidAuthenticationResponse,
    InvalidRegistrationResponse,
)

from app.api.deps import ActorContext, current_actor
from app.api.router import _active_memberships, _default_membership, _login_response
from app.core.config import Settings, get_settings
from app.core.security import hash_password, verify_password
from app.db.session import database_is_available, system_session, tenant_session
from app.services.auto_runtime import runtime_capability_map
from app.services.confirmation_actions import list_confirmation_actions
from app.services.conversation_history import (
    create_conversation,
    list_conversations,
    load_conversation,
)
from app.services.organization import NAVIGATION_CATALOG
from app.services.passkey_grants import issue_step_up_grant
from app.services.integrations import (
    VoiceIntegrationError,
    correct_voice_transcript,
    normalize_provider,
    public_state,
    save_configuration,
    synthesize_voice_speech,
    transcribe_voice_audio,
    validate_saved,
    voice_capability_state,
)
from app.services.identity_titles import official_title_profile
from app.services.identity_employment import (
    official_employment_profile,
    personnel_archive_status,
    sync_personnel_record,
)
from app.services.language_contract import normalize_locale
from app.services.membership_requests import (
    approve_membership_request,
    list_membership_requests,
    reject_membership_request,
)
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
        request_id = session.execute(
            text(
                """
                INSERT INTO platform.membership_requests(id, tenant_id, user_id, reason)
                VALUES (:id, :tenant_id, :user_id, :reason)
                ON CONFLICT (tenant_id, user_id)
                DO UPDATE SET status = 'pending', reason = EXCLUDED.reason,
                  note = NULL, reviewed_by = NULL, created_at = now()
                RETURNING id
                """
            ),
            {
                "id": request_id,
                "tenant_id": target["id"],
                "user_id": actor.user_id,
                "reason": payload.get("reason"),
            },
        ).scalar_one()
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
    result = list_membership_requests(
        actor,
        request_status=request_status,
        request_kind="registration",
    )
    result["registrations"] = result["requests"]
    return result


@router.post("/api/auth/registrations/{request_id}/approve")
def approve_registration(
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return approve_membership_request(
        actor,
        request_id,
        payload,
        expected_kind="registration",
    )


@router.post("/api/auth/registrations/{request_id}/reject")
def reject_registration(
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return reject_membership_request(
        actor,
        request_id,
        payload,
        expected_kind="registration",
    )


@router.get("/api/memberships/pending")
def pending_membership_requests(
    request_status: str = Query(default="pending", alias="status"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_membership_requests(
        actor,
        request_status=request_status,
        request_kind="join",
    )


@router.post("/api/memberships/{request_id}/approve")
def approve_join_request(
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return approve_membership_request(
        actor,
        request_id,
        payload,
        expected_kind="join",
    )


@router.post("/api/memberships/{request_id}/reject")
def reject_join_request(
    request_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return reject_membership_request(
        actor,
        request_id,
        payload,
        expected_kind="join",
    )


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
        **official_title_profile(actor),
        **official_employment_profile(actor),
    }


def _require_title_manager(actor: ActorContext) -> None:
    if actor.role_level < 10 and not ({"users.manage", "records.manage"} & actor.permissions):
        raise HTTPException(status_code=403, detail="Title claim management requires HR authority")


@router.post("/api/org/users/{user_id}/title-claims")
def official_title_claim_issue(
    user_id: UUID,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_title_manager(actor)
    title_code = str(payload.get("title_code") or "").strip().lower()
    source_kind = str(payload.get("source_kind") or "verified_record").strip().lower()
    source_ref = str(payload.get("source_ref") or "").strip()[:240]
    if source_kind not in {
        "verified_record",
        "professional_registry",
        "owner_attestation",
        "legacy_verified",
    }:
        raise HTTPException(status_code=422, detail="Unsupported title claim source")
    with tenant_session(actor.tenant_id) as session:
        definition = session.execute(
            text(
                """
                SELECT code, category FROM iam.title_definitions
                WHERE code = :code AND active AND claimable
                """
            ),
            {"code": title_code},
        ).mappings().one_or_none()
        if definition is None:
            raise HTTPException(status_code=422, detail="Unknown or appointment-derived title")
        member_exists = session.execute(
            text(
                """
                SELECT 1 FROM iam.memberships
                WHERE user_id = :user_id AND active LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).scalar_one_or_none()
        if member_exists is None:
            raise HTTPException(status_code=404, detail="Company member not found")
        claim = session.execute(
            text(
                """
                INSERT INTO iam.person_title_claims(
                  id, tenant_id, user_id, title_code, source_kind, source_ref,
                  status, verified_by, valid_from, valid_until, metadata
                ) VALUES (
                  :id, :tenant_id, :user_id, :title_code, :source_kind, :source_ref,
                  'active', :verified_by, :valid_from, :valid_until, CAST(:metadata AS jsonb)
                )
                ON CONFLICT (tenant_id, user_id, title_code, source_kind, source_ref)
                DO UPDATE SET status = 'active', verified_by = EXCLUDED.verified_by,
                  valid_from = EXCLUDED.valid_from, valid_until = EXCLUDED.valid_until,
                  metadata = EXCLUDED.metadata
                RETURNING id, user_id, title_code, source_kind, source_ref,
                          status, valid_from, valid_until, created_at, updated_at
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "user_id": user_id,
                "title_code": title_code,
                "source_kind": source_kind,
                "source_ref": source_ref,
                "verified_by": actor.user_id,
                "valid_from": payload.get("valid_from"),
                "valid_until": payload.get("valid_until"),
                "metadata": json.dumps(
                    payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {},
                    ensure_ascii=False,
                    default=str,
                ),
            },
        ).mappings().one()
        _audit(
            session,
            actor,
            "identity.title_claim.issued",
            {
                "claim_id": str(claim["id"]),
                "user_id": str(user_id),
                "title_code": title_code,
                "source_kind": source_kind,
                "source_ref": source_ref,
            },
        )
    return {"ok": True, "claim": _safe(dict(claim))}


@router.post("/api/org/users/{user_id}/title-claims/{claim_id}/revoke")
def official_title_claim_revoke(
    user_id: UUID,
    claim_id: UUID,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_title_manager(actor)
    with tenant_session(actor.tenant_id) as session:
        claim = session.execute(
            text(
                """
                UPDATE iam.person_title_claims
                SET status = 'revoked'
                WHERE id = :claim_id AND user_id = :user_id AND status <> 'revoked'
                RETURNING id, user_id, title_code, status, updated_at
                """
            ),
            {"claim_id": claim_id, "user_id": user_id},
        ).mappings().one_or_none()
        if claim is None:
            raise HTTPException(status_code=404, detail="Active title claim not found")
        _audit(
            session,
            actor,
            "identity.title_claim.revoked",
            {"claim_id": str(claim_id), "user_id": str(user_id)},
        )
    return {"ok": True, "claim": _safe(dict(claim))}


_EMPLOYMENT_TYPES = frozenset(
    {"unspecified", "employee", "contractor", "visiting", "intern", "affiliate", "other"}
)


@router.patch("/api/org/users/{user_id}/employment-profile")
def employment_profile_update(
    user_id: UUID,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_title_manager(actor)
    with tenant_session(actor.tenant_id) as session:
        current = session.execute(
            text(
                """
                SELECT employee_no, employment_type, employment_date, manager_user_id, metadata
                FROM iam.employment_profiles
                WHERE user_id = :user_id
                FOR UPDATE
                """
            ),
            {"user_id": user_id},
        ).mappings().one_or_none()
        if current is None:
            raise HTTPException(status_code=404, detail="Employment profile not found")

        employee_no = str(payload.get("employee_no", current["employee_no"]) or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9][A-Z0-9-]{2,31}", employee_no):
            raise HTTPException(status_code=422, detail="Invalid employee number")
        duplicate = session.execute(
            text(
                """
                SELECT 1 FROM iam.employment_profiles
                WHERE employee_no = :employee_no AND user_id <> :user_id
                LIMIT 1
                """
            ),
            {"employee_no": employee_no, "user_id": user_id},
        ).scalar_one_or_none()
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Employee number already exists")

        employment_type = str(
            payload.get("employment_type", current["employment_type"]) or "unspecified"
        ).strip().lower()
        if employment_type not in _EMPLOYMENT_TYPES:
            raise HTTPException(status_code=422, detail="Invalid employment type")

        raw_date = payload.get("employment_date", current["employment_date"])
        try:
            employment_date = date.fromisoformat(str(raw_date)) if raw_date not in (None, "") else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Employment date must use YYYY-MM-DD") from exc

        raw_manager = payload.get("manager_user_id", current["manager_user_id"])
        try:
            manager_user_id = UUID(str(raw_manager)) if raw_manager not in (None, "") else None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid manager user id") from exc
        if manager_user_id == user_id:
            raise HTTPException(status_code=422, detail="A person cannot be their own manager")
        if manager_user_id is not None:
            manager_exists = session.execute(
                text("SELECT 1 FROM iam.memberships WHERE user_id = :user_id AND active LIMIT 1"),
                {"user_id": manager_user_id},
            ).scalar_one_or_none()
            if manager_exists is None:
                raise HTTPException(status_code=422, detail="Manager is not an active company member")

        metadata = dict(current["metadata"] or {}) if isinstance(current["metadata"], dict) else {}
        metadata["last_hr_update_by"] = str(actor.user_id)
        updated = session.execute(
            text(
                """
                UPDATE iam.employment_profiles
                SET employee_no = :employee_no, employment_type = :employment_type,
                    employment_date = :employment_date, manager_user_id = :manager_user_id,
                    metadata = CAST(:metadata AS jsonb)
                WHERE user_id = :user_id
                RETURNING employee_no, employment_type, employment_date,
                          manager_user_id, updated_at
                """
            ),
            {
                "user_id": user_id,
                "employee_no": employee_no,
                "employment_type": employment_type,
                "employment_date": employment_date,
                "manager_user_id": manager_user_id,
                "metadata": json.dumps(metadata, ensure_ascii=False),
            },
        ).mappings().one()
        _audit(
            session,
            actor,
            "identity.employment_profile.updated",
            {
                "user_id": str(user_id),
                "employee_no": employee_no,
                "employment_type": employment_type,
                "employment_date": employment_date,
                "manager_user_id": str(manager_user_id) if manager_user_id else None,
            },
        )
    return {"ok": True, "employment": _safe(dict(updated))}


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
        "archive": personnel_archive_status(actor),
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
    official = _official_profile(actor)
    with tenant_session(actor.tenant_id) as session:
        current = session.execute(
            text("SELECT revision FROM iam.user_profiles WHERE user_id = :user_id"),
            {"user_id": actor.user_id},
        ).scalar_one_or_none()
        current_revision = int(current or 0)
        if expected_revision not in (None, "") and int(expected_revision) != current_revision:
            raise HTTPException(status_code=409, detail="Profile changed; reload before saving")
        next_revision = session.execute(
            text(
                """
                INSERT INTO iam.user_profiles(user_id, profile, revision)
                VALUES (:user_id, CAST(:profile AS jsonb), 1)
                ON CONFLICT (user_id)
                DO UPDATE SET profile = EXCLUDED.profile,
                  revision = iam.user_profiles.revision + 1
                RETURNING revision
                """
            ),
            {
                "user_id": actor.user_id,
                "profile": json.dumps(profile, ensure_ascii=False, default=str),
            },
        ).scalar_one()
        display_name = str(profile.get("display_name") or "").strip()
        if display_name:
            session.execute(
                text("UPDATE iam.users SET display_name = :display_name WHERE id = :id"),
                {"display_name": display_name, "id": actor.user_id},
            )
        sync_personnel_record(
            session,
            actor,
            profile=profile,
            profile_revision=int(next_revision),
            official=official,
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
        "language": "zh-Hant",
        "language_mode": "auto",
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
    language_source = "stored" if stored and stored.get("language") else "default"
    return {
        "available": True,
        "preferences": result,
        "language_source": language_source,
        **_safe(result),
    }


def _save_runtime(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    normalized_payload = dict(payload)
    if "language" in normalized_payload:
        normalized_payload["language"] = normalize_locale(
            normalized_payload.get("language")
        )
    if "language_mode" in normalized_payload:
        normalized_payload["language_mode"] = (
            "fixed"
            if str(normalized_payload.get("language_mode") or "").lower() == "fixed"
            else "auto"
        )
    with tenant_session(actor.tenant_id) as session:
        existing = _doc(session, "runtime.preferences", str(actor.user_id)) or {}
    merged = {
        **existing,
        **normalized_payload,
        "updated_at": datetime.now(UTC).isoformat(),
    }
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


def _require_integration_manager(actor: ActorContext) -> None:
    if actor.role_level < 10 and "settings.manage" not in actor.permissions:
        raise HTTPException(status_code=403, detail="Integration management permission is required")


def _require_voice_user(actor: ActorContext) -> None:
    if "ai.use" not in actor.permissions:
        raise HTTPException(status_code=403, detail="Voice usage requires ai.use permission")


def _voice_error_response(exc: VoiceIntegrationError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": exc.message, "code": exc.code},
        headers={"Cache-Control": "no-store"},
    )


@router.get("/api/integrations/{provider}")
def integration_get(
    provider: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    try:
        state = public_state(actor, provider)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {provider: state, **state}


@router.put("/api/integrations/{provider}")
@router.patch("/api/integrations/{provider}")
def integration_write(
    provider: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return integration_save(provider, payload, actor, settings)


@router.post("/api/integrations/{provider}/save")
def integration_save(
    provider: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _require_integration_manager(actor)
    try:
        normalized = normalize_provider(provider)
        public, result = save_configuration(
            actor, normalized, str(payload.get("api_key") or ""), payload, settings
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    validation = {
        "ok": result.ok,
        "latency_ms": result.latency_ms,
        "error": result.error,
    }
    return {"ok": True, normalized: public, "validation": validation, **public}


@router.post("/api/integrations/{provider}/validate")
def integration_validate(
    provider: str,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _require_integration_manager(actor)
    try:
        normalized = normalize_provider(provider)
        state, result = validate_saved(actor, normalized, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    validation = {
        "ok": result.ok,
        "latency_ms": result.latency_ms,
        "error": result.error,
    }
    return {"ok": result.ok, normalized: state, "validation": validation, **state}


@router.get("/api/voice/status")
def voice_status_full(
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    return voice_capability_state(actor, settings)


@router.post("/api/voice/transcribe")
def voice_transcribe_full(
    request: Request,
    audio: bytes = Body(..., media_type="application/octet-stream"),
    lang: str = Query(default="zh", min_length=1, max_length=16),
    correct: bool = Query(default=False),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    _require_voice_user(actor)
    try:
        result = transcribe_voice_audio(
            actor,
            settings,
            audio,
            request.headers.get("content-type") or "",
            lang,
        )
        text_value = result.text
        corrected = False
        if correct:
            text_value, corrected = correct_voice_transcript(actor, settings, text_value)
        content: dict[str, object] = {
            "ok": True,
            "text": text_value,
            "corrected": corrected,
            "model": result.model,
        }
        if corrected:
            content["raw_text"] = result.text
        if result.trace_id:
            content["trace_id"] = result.trace_id
        return JSONResponse(
            content=content,
            headers={"Cache-Control": "no-store"},
        )
    except VoiceIntegrationError as exc:
        return _voice_error_response(exc)


@router.get("/api/ai/health")
def ai_health_full(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    state = public_state(actor, "deepseek")
    database_ready = database_is_available()
    capability_map = runtime_capability_map()
    return {
        "status": "ok" if database_ready and state["connected"] else "degraded",
        "database": "ready" if database_ready else "unavailable",
        "provider_configured": bool(state["configured"]),
        "provider_connected": bool(state["connected"]),
        "provider": state["provider"],
        "model": state["model"] if state["connected"] else None,
        "capability_universe": {
            "known": len(capability_map),
            "adapter_ready": sum(
                1 for capability in capability_map if capability["state"] == "adapter_ready"
            ),
        },
    }


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
    conversations = list_conversations(actor, limit=limit)
    return {
        "available": True,
        "rows": conversations,
        "hasMore": len(conversations) >= limit,
        "has_more": len(conversations) >= limit,
        "conversations": conversations,
        "items": conversations,
    }


@router.post("/api/ai/conversations", status_code=201)
def conversations_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    conversation = create_conversation(
        actor,
        title=payload.get("title"),
        channel=payload.get("channel"),
    )
    return {"ok": True, "conversation": conversation}


@router.get("/api/ai/conversations/{conversation_id}")
def conversation_detail(
    conversation_id: str,
    message_limit: int = Query(default=80, ge=1, le=500),
    before_sequence: int | None = Query(default=None, ge=1),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    loaded = load_conversation(
        actor,
        conversation_id=conversation_id,
        message_limit=message_limit,
        before_sequence=before_sequence,
    )
    return {"available": True, **loaded}


@router.get("/api/ai/conversation")
def conversation_detail_legacy_query(
    conversation_id: str = Query(alias="id", min_length=1, max_length=128),
    message_limit: int = Query(default=80, ge=1, le=500),
    before_sequence: int | None = Query(default=None, ge=1),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Serve the audit archive's former singular query-string contract.

    Keep this alias on the same owner-scoped loader as the canonical plural
    route so cached frontends remain functional without weakening isolation.
    """
    loaded = load_conversation(
        actor,
        conversation_id=conversation_id,
        message_limit=message_limit,
        before_sequence=before_sequence,
    )
    return {"available": True, **loaded}


@router.get("/api/assistant/bootstrap")
def assistant_bootstrap_full(
    message_limit: int = Query(default=80, ge=1, le=500),
    conversation_id: str | None = Query(default=None, max_length=128),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    loaded = load_conversation(
        actor,
        conversation_id=conversation_id,
        message_limit=message_limit,
    )
    loaded_conversation = loaded.get("conversation")
    confirmation_actions = list_confirmation_actions(
        actor,
        conversation_id=(
            loaded_conversation.get("id")
            if isinstance(loaded_conversation, dict)
            else None
        ),
        limit=100,
    )
    return {
        "available": True,
        "tenant": {
            "id": str(actor.tenant_id),
            "slug": actor.tenant_slug,
            "name": actor.tenant_name,
        },
        "user": actor.user_payload,
        **loaded,
        "state": {
            "actor": actor.user_payload,
            "subjects": [],
            "pending_actions": [],
            "active_task": {"status": "active"},
        },
        "confirmation_actions": confirmation_actions,
        "capability_map": runtime_capability_map(),
        "message_limit": message_limit,
    }


@router.post("/api/voice/speak")
def voice_speak(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> Response:
    _require_voice_user(actor)
    try:
        result = synthesize_voice_speech(actor, settings, str(payload.get("text") or ""))
    except VoiceIntegrationError as exc:
        return _voice_error_response(exc)
    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
    }
    if result.trace_id:
        headers["X-Voice-Trace-Id"] = result.trace_id
    return Response(content=result.audio, media_type=result.content_type, headers=headers)


def _challenge_text() -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii").rstrip("=")


def _user_id_b64(user_id: UUID) -> str:
    return base64.urlsafe_b64encode(user_id.bytes).decode("ascii").rstrip("=")


def _verify_account_password(user_id: UUID, password: object) -> None:
    candidate = str(password or "")
    with system_session() as session:
        password_hash = session.execute(
            text("SELECT password_hash FROM iam.users WHERE id = :id AND active"),
            {"id": user_id},
        ).scalar_one_or_none()
    if password_hash is None or not verify_password(candidate, str(password_hash)):
        raise HTTPException(status_code=401, detail="Password verification failed")


def _webauthn_error(detail: str) -> HTTPException:
    return HTTPException(status_code=400, detail=detail)


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
    payload: dict[str, object] = Body(default={}),
    settings: Settings = Depends(get_settings),
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
                    text(
                        """
                        SELECT credential_id, transports
                        FROM iam.passkeys
                        WHERE user_id = :id AND rp_id = :rp_id
                        ORDER BY created_at DESC
                        """
                    ),
                    {"id": user["id"], "rp_id": settings.webauthn_rp_id},
                ).mappings().all()
                credentials = [
                    {
                        "type": "public-key",
                        "id": row["credential_id"],
                        "transports": list(row["transports"] or []),
                    }
                    for row in rows
                ]
        # Do not send a credential descriptor created for localhost or another
        # RP into a production WebAuthn ceremony.  Browsers otherwise receive
        # an allow-list that cannot possibly match the current RP and may
        # silently time out without ever posting /login/verify.
        if not credentials:
            raise HTTPException(
                status_code=409,
                detail=(
                    "此帳號尚未在目前網站登記 Passkey；"
                    "請先使用密碼登入，再到「安全與 Passkey」新增。"
                ),
            )
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
            "rpId": settings.webauthn_rp_id,
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
        passkey = session.execute(
            text(
                """
                SELECT user_id, credential_public_key, sign_count, rp_id
                FROM iam.passkeys
                WHERE credential_id = :credential_id AND rp_id = :rp_id
                """
            ),
            {"credential_id": credential_id, "rp_id": settings.webauthn_rp_id},
        ).mappings().one_or_none()
        user_id = passkey["user_id"] if passkey else None
        if challenge.get("user_id") is not None and user_id != challenge.get("user_id"):
            raise HTTPException(status_code=401, detail="Passkey account is unavailable")
        if passkey is None or passkey["credential_public_key"] is None:
            raise HTTPException(status_code=401, detail="Passkey must be registered again")
        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(str(challenge["challenge"])),
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=settings.webauthn_origins,
                credential_public_key=bytes(passkey["credential_public_key"]),
                credential_current_sign_count=int(passkey["sign_count"]),
                require_user_verification=True,
            )
        except (InvalidAuthenticationResponse, ValueError, TypeError) as exc:
            raise _webauthn_error("Passkey assertion verification failed") from exc
        account = session.execute(
            text("SELECT id, username, display_name FROM iam.users WHERE id = :id AND active"),
            {"id": user_id},
        ).mappings().one_or_none()
        if account:
            session.execute(
                text(
                    """
                    UPDATE iam.passkeys
                    SET last_used_at = now(), sign_count = :sign_count,
                        device_type = :device_type, backed_up = :backed_up
                    WHERE credential_id = :id AND rp_id = :rp_id
                    """
                ),
                {
                    "id": credential_id,
                    "rp_id": settings.webauthn_rp_id,
                    "sign_count": verification.new_sign_count,
                    "device_type": verification.credential_device_type.value,
                    "backed_up": verification.credential_backed_up,
                },
            )
    if account is None:
        raise HTTPException(status_code=401, detail="Passkey account is unavailable")
    return _login_payload(dict(account), None, settings)


@router.post("/api/auth/passkeys/register/options")
def passkey_register_options(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _verify_account_password(actor.user_id, payload.get("password"))
    request_id, challenge = _new_challenge(
        kind="register",
        user_id=actor.user_id,
        username=actor.username,
    )
    return {
        "request_id": str(request_id),
        "publicKey": {
            "challenge": challenge,
            "rp": {"name": settings.webauthn_rp_name, "id": settings.webauthn_rp_id},
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
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    challenge = _consume_challenge(payload.get("request_id"), "register")
    if challenge.get("user_id") != actor.user_id:
        raise HTTPException(status_code=403, detail="Passkey challenge belongs to another account")
    credential = payload.get("credential") if isinstance(payload.get("credential"), dict) else {}
    credential_id = str(credential.get("id") or credential.get("rawId") or "")
    if not credential_id:
        raise HTTPException(status_code=422, detail="Passkey credential is required")
    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(str(challenge["challenge"])),
            expected_rp_id=settings.webauthn_rp_id,
            expected_origin=settings.webauthn_origins,
            require_user_verification=True,
        )
    except (InvalidRegistrationResponse, ValueError, TypeError) as exc:
        raise _webauthn_error("Passkey registration verification failed") from exc
    verified_credential_id = bytes_to_base64url(verification.credential_id)
    if credential_id != verified_credential_id:
        raise _webauthn_error("Passkey credential ID mismatch")
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
                  id, user_id, credential_id, name, credential, transports,
                  credential_public_key, sign_count, rp_id, aaguid, device_type, backed_up
                ) VALUES (
                  :id, :user_id, :credential_id, :name,
                  CAST(:credential AS jsonb), CAST(:transports AS jsonb),
                  :credential_public_key, :sign_count, :rp_id, :aaguid,
                  :device_type, :backed_up
                )
                ON CONFLICT (credential_id)
                DO UPDATE SET name = EXCLUDED.name, credential = EXCLUDED.credential,
                  transports = EXCLUDED.transports,
                  credential_public_key = EXCLUDED.credential_public_key,
                  sign_count = EXCLUDED.sign_count, rp_id = EXCLUDED.rp_id,
                  aaguid = EXCLUDED.aaguid, device_type = EXCLUDED.device_type,
                  backed_up = EXCLUDED.backed_up, last_used_at = now()
                """
            ),
            {
                "id": passkey_id,
                "user_id": actor.user_id,
                "credential_id": credential_id,
                "name": str(payload.get("name") or "Passkey"),
                "credential": json.dumps(credential, ensure_ascii=False),
                "transports": json.dumps(transports),
                "credential_public_key": verification.credential_public_key,
                "sign_count": verification.sign_count,
                "rp_id": settings.webauthn_rp_id,
                "aaguid": verification.aaguid,
                "device_type": verification.credential_device_type.value,
                "backed_up": verification.credential_backed_up,
            },
        )
    return {"ok": True, "passkey": {"id": str(passkey_id), "name": payload.get("name") or "Passkey"}}


@router.get("/api/auth/passkeys")
def passkey_list(
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT id, name, right(credential_id, 8) AS credential_hint,
                       transports, rp_id, device_type, backed_up, created_at, last_used_at
                FROM iam.passkeys
                WHERE user_id = :user_id AND rp_id = :rp_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": actor.user_id, "rp_id": settings.webauthn_rp_id},
        ).mappings().all()
    passkeys = [_safe(dict(row)) for row in rows]
    return {"passkeys": passkeys, "credentials": passkeys}


@router.delete("/api/auth/passkeys/{passkey_id}")
def passkey_delete(
    passkey_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    _verify_account_password(actor.user_id, payload.get("password"))
    with system_session() as session:
        result = session.execute(
            text(
                """
                DELETE FROM iam.passkeys
                WHERE id = :id AND user_id = :user_id AND rp_id = :rp_id
                """
            ),
            {
                "id": UUID(passkey_id),
                "user_id": actor.user_id,
                "rp_id": settings.webauthn_rp_id,
            },
        )
    if result.rowcount != 1:
        raise HTTPException(status_code=404, detail="Passkey not found")
    return {"ok": True, "id": passkey_id}


@router.post("/api/auth/passkeys/step-up/options")
def passkey_step_up_options(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    with system_session() as session:
        rows = session.execute(
            text(
                """
                SELECT credential_id, transports
                FROM iam.passkeys
                WHERE user_id = :user_id AND rp_id = :rp_id
                ORDER BY created_at DESC
                """
            ),
            {"user_id": actor.user_id, "rp_id": settings.webauthn_rp_id},
        ).mappings().all()
    if not rows:
        raise HTTPException(
            status_code=409,
            detail=(
                "此帳號尚未在目前網站登記 Passkey；"
                "請先到「安全與 Passkey」新增。"
            ),
        )
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
            "rpId": settings.webauthn_rp_id,
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
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    challenge = _consume_challenge(payload.get("request_id"), "step_up")
    if challenge.get("user_id") != actor.user_id:
        raise HTTPException(status_code=403, detail="Passkey challenge belongs to another account")
    credential = payload.get("credential") if isinstance(payload.get("credential"), dict) else {}
    credential_id = str(credential.get("id") or credential.get("rawId") or "")
    with system_session() as session:
        passkey = session.execute(
            text(
                """
                SELECT credential_public_key, sign_count, name
                FROM iam.passkeys
                WHERE user_id = :user_id AND credential_id = :credential_id
                  AND rp_id = :rp_id
                """
            ),
            {
                "user_id": actor.user_id,
                "credential_id": credential_id,
                "rp_id": settings.webauthn_rp_id,
            },
        ).mappings().one_or_none()
        if passkey is None or passkey["credential_public_key"] is None:
            raise HTTPException(status_code=401, detail="Passkey must be registered again")
        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(str(challenge["challenge"])),
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=settings.webauthn_origins,
                credential_public_key=bytes(passkey["credential_public_key"]),
                credential_current_sign_count=int(passkey["sign_count"]),
                require_user_verification=True,
            )
        except (InvalidAuthenticationResponse, ValueError, TypeError) as exc:
            raise _webauthn_error("Passkey assertion verification failed") from exc
        session.execute(
            text(
                """
                UPDATE iam.passkeys
                SET last_used_at = now(), sign_count = :sign_count,
                    device_type = :device_type, backed_up = :backed_up
                WHERE user_id = :user_id AND credential_id = :credential_id
                  AND rp_id = :rp_id
                """
            ),
            {
                "user_id": actor.user_id,
                "credential_id": credential_id,
                "rp_id": settings.webauthn_rp_id,
                "sign_count": verification.new_sign_count,
                "device_type": verification.credential_device_type.value,
                "backed_up": verification.credential_backed_up,
            },
        )
    token = secrets.token_urlsafe(36)
    credential_payload = credential if isinstance(credential, dict) else {}
    response_payload = (
        credential_payload.get("response")
        if isinstance(credential_payload.get("response"), dict)
        else {}
    )
    origin = None
    client_data = response_payload.get("clientDataJSON")
    if isinstance(client_data, str) and client_data:
        try:
            decoded_client_data = json.loads(
                base64url_to_bytes(client_data).decode("utf-8")
            )
            if isinstance(decoded_client_data, dict):
                origin = decoded_client_data.get("origin")
        except (UnicodeDecodeError, ValueError, TypeError):
            origin = None
    verified_at = datetime.now(UTC)
    verification_evidence = {
        "verified": True,
        "method": "webauthn",
        "operator": actor.username,
        "operator_user_id": str(actor.user_id),
        "credential_name": passkey.get("name"),
        "credential_id_hint": (
            "••••" + credential_id[-8:] if credential_id else None
        ),
        "verified_at": verified_at.isoformat(),
        "rp_id": settings.webauthn_rp_id,
        "origin": origin,
        "user_verified": True,
        "sign_count_before": int(passkey["sign_count"]),
        "sign_count_after": int(verification.new_sign_count),
        "evidence_sha256": hashlib.sha256(
            json.dumps(
                credential_payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ).encode("utf-8")
        ).hexdigest(),
    }
    grant = issue_step_up_grant(
        actor,
        token=token,
        purpose=challenge.get("purpose"),
        resource=challenge.get("resource"),
        verification=verification_evidence,
        expires_in_seconds=300,
    )
    return {
        "ok": True,
        "step_up_token": token,
        "purpose": challenge.get("purpose"),
        "resource": _safe(challenge.get("resource") or {}),
        "resource_digest": grant["resource_digest"],
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


def _require_platform_owner(actor: ActorContext) -> None:
    if not _is_owner(actor.user_id):
        raise HTTPException(status_code=403, detail="Platform owner access required")


@router.get("/api/platform/optimizer/overview")
@router.get("/api/platform/optimizer/analyses/active")
def optimizer_overview(
    window_days: int = Query(default=30, ge=1, le=365),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_platform_owner(actor)
    with system_session() as session:
        tenant_count = session.execute(
            text("SELECT COUNT(*)::integer FROM iam.tenants WHERE status = 'active'")
        ).scalar_one()
        conversation_count = session.execute(
            text("""
                SELECT COUNT(*)::integer
                FROM secretariat.conversations
                WHERE created_at >= now() - CAST(:window_days AS integer) * INTERVAL '1 day'
            """),
            {"window_days": window_days},
        ).scalar_one()
        run_counts = session.execute(
            text("""
                SELECT COUNT(*)::integer AS total,
                       COUNT(*) FILTER (WHERE status = 'succeeded')::integer AS completed,
                       COUNT(*) FILTER (WHERE status = 'failed')::integer AS failed
                FROM secretariat.runs
                WHERE created_at >= now() - CAST(:window_days AS integer) * INTERVAL '1 day'
            """),
            {"window_days": window_days},
        ).mappings().one()
    total_runs = int(run_counts["total"] or 0)
    completed_runs = int(run_counts["completed"] or 0)
    failed_runs = int(run_counts["failed"] or 0)
    return {
        "available": True,
        "feature": {
            "id": 23,
            "key": "platform_optimizer",
            "experimental": True,
            "owner_only": True,
        },
        "summary": {
            "window_days": window_days,
            "generated_at": datetime.now(UTC).isoformat(),
            "tenant_count": int(tenant_count or 0),
            "available_tenant_count": int(tenant_count or 0),
            "conversation_count": int(conversation_count or 0),
            "message_count": None,
            "run_count": total_runs,
            "completed_run_count": completed_runs,
            "failed_run_count": failed_runs,
            "feedback_count": None,
            "confirmation_count": None,
            "total_tokens": None,
            "avg_duration_ms": None,
        },
        "metrics": {
            "completion_rate": completed_runs / total_runs if total_runs else None,
            "failure_rate": failed_runs / total_runs if total_runs else None,
            "confirmation_completion_rate": None,
            "feedback_rate": None,
        },
        "findings": [],
        "candidates": [],
        "snapshots": [],
        "analysis_history": [],
        "privacy": {"aggregate_only": True, "raw_transcripts_exposed": False},
    }


@router.get("/api/platform/evolution-lab/status")
def evolution_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    _require_platform_owner(actor)
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
    _require_platform_owner(actor)
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
