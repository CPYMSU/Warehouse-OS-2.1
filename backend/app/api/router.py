from __future__ import annotations

import json
from queue import Empty, Queue
from threading import Thread
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from starlette.background import BackgroundTask

from app.api.deps import ActorContext, current_actor
from app.api.schemas import (
    AgentRunRequest,
    AiToolCallRequest,
    CliExecuteRequest,
    InboundCreateRequest,
    LoginRequest,
    LoginResponse,
    OutboundCreateRequest,
    ReplenishmentRequest,
    ShipmentActionRequest,
    ShipmentDispatchRequest,
    TenantSwitchRequest,
)
from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    hash_password,
    needs_password_rehash,
    verify_password,
)
from app.db.session import database_is_available, system_session, tenant_session
from app.services.auto_runtime import run_auto_runtime, runtime_world_snapshot
from app.services.bootstrap import bootstrap_payload
from app.services.confirmation_actions import authorization_signal_for_runtime
from app.services.conversation_history import (
    append_message,
    ensure_conversation,
    messages_for_turn,
)
from app.services.language_contract import (
    localized_runtime_error,
    resolve_language_contract,
)
from app.services.memory_fabric import (
    build_memory_capsule,
    forget_memory_unit,
    list_memory_units,
    run_background_memory_steward,
)
from app.services.organization import (
    apply_template,
    archive_department,
    archive_position,
    assign_user_position,
    create_department,
    create_position,
    organization_structure,
    set_department_navigation,
    set_department_permissions,
    set_position_navigation,
    set_user_navigation,
    set_user_permissions,
    template_preview,
    templates_payload,
    topology_payload,
    update_department,
    update_position,
    users_payload,
)
from app.services.overview import executive_overview_payload
from app.services.runtime_api_keys import (
    RuntimeApiKeyError,
    issue_research_api_key,
    issue_runtime_api_key,
    list_runtime_api_keys,
    revoke_runtime_api_key,
)
from app.services.runtime_output import public_message
from app.services.templates import get_template_detail, list_template_summaries
from app.services.topology import map_zones_payload
from app.services.warehouse_operations import (
    alerts_by_item,
    archive_item,
    arrive_shipment,
    bootstrap_warehouse_payload,
    cancel_shipment,
    create_inbound,
    create_item,
    create_outbound,
    create_replenishment,
    dispatch_shipment,
    gis_overview,
    inventory_batches,
    pending_returns,
    reports_summary,
    shipment_rows,
    update_item,
)
from app.terminal.catalog import (
    ai_capability_states,
    ai_tool_schemas,
    business_action_catalogue,
    command_catalogue,
    migration_summary,
    skill_catalogue,
)
from app.terminal.executor import execute_cli_line, execute_manual_action, execute_tool_call

router = APIRouter(tags=["warehouse"])


def _active_memberships(user_id: object) -> list[dict[str, object]]:
    """List only the authenticated user's active company memberships.

    The initial global identity lookup happens before this function.  Every
    membership read itself still runs in an explicit tenant RLS transaction;
    this avoids an unscoped cross-tenant membership query.
    """
    with system_session() as session:
        tenants = (
            session.execute(
                text(
                    """
                SELECT id, slug, name, industry_template_key
                FROM iam.tenants
                WHERE status = 'active'
                ORDER BY slug
                """
                )
            )
            .mappings()
            .all()
        )
    memberships: list[dict[str, object]] = []
    for tenant in tenants:
        with tenant_session(tenant["id"]) as session:
            membership = (
                session.execute(
                    text(
                        """
                    SELECT role_level, topology_level, topology_title
                    FROM iam.memberships
                    WHERE tenant_id = :tenant_id AND user_id = :user_id AND active
                    """
                    ),
                    {"tenant_id": tenant["id"], "user_id": user_id},
                )
                .mappings()
                .one_or_none()
            )
        if membership is not None:
            memberships.append({**dict(tenant), **dict(membership)})
    return memberships


def _company_payloads(memberships: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "slug": str(membership["slug"]),
            "name": str(membership["name"]),
            "status": "active",
        }
        for membership in memberships
    ]


def _default_membership(
    memberships: list[dict[str, object]], requested_slug: str | None = None
) -> dict[str, object] | None:
    if requested_slug:
        requested = requested_slug.strip().lower()
        for membership in memberships:
            if membership["slug"] == requested:
                return membership
    # Preserve Bonfire as the continuity default while still supporting any
    # future company a global account joins.
    for membership in memberships:
        if membership["slug"] == "bonfire":
            return membership
    return memberships[0] if memberships else None


def _login_response(
    *,
    account: dict[str, object],
    membership: dict[str, object],
    memberships: list[dict[str, object]],
    settings: Settings,
) -> LoginResponse:
    actor = ActorContext(
        user_id=account["id"],
        tenant_id=membership["id"],
        tenant_slug=str(membership["slug"]),
        tenant_name=str(membership["name"]),
        industry_template_key=str(membership["industry_template_key"]),
        username=str(account["username"]),
        display_name=str(account["display_name"]),
        role_level=int(membership["role_level"]),
        topology_level=int(membership["topology_level"]),
        topology_title=membership["topology_title"],
    )
    return LoginResponse(
        token=create_access_token(
            settings=settings, user_id=actor.user_id, tenant_id=actor.tenant_id
        ),
        tenant=actor.tenant_slug,
        default_tenant=actor.tenant_slug,
        user=actor.user_payload,
        companies=_company_payloads(memberships),
        can_apply_company=actor.role_level >= 4,
    )


@router.get("/api/health")
@router.get("/api/v1/health")
def api_health() -> dict[str, str]:
    if not database_is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PostgreSQL 18 with pgvector is unavailable",
        )
    return {"status": "ok", "database": "postgresql-18-pgvector"}


@router.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, settings: Settings = Depends(get_settings)) -> LoginResponse:
    username = payload.username.strip().lower()
    with system_session() as session:
        account = (
            session.execute(
                text(
                    """
                SELECT id, username, display_name, password_hash
                FROM iam.users
                WHERE username = :username AND active
                """
                ),
                {"username": username},
            )
            .mappings()
            .one_or_none()
        )
    if account is None or not verify_password(payload.password, account["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    memberships = _active_memberships(account["id"])
    membership = _default_membership(memberships, payload.tenant)
    if membership is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if needs_password_rehash(account["password_hash"]):
        with system_session() as session:
            session.execute(
                text("UPDATE iam.users SET password_hash = :password_hash WHERE id = :user_id"),
                {"password_hash": hash_password(payload.password), "user_id": account["id"]},
            )
    return _login_response(
        account=dict(account), membership=membership, memberships=memberships, settings=settings
    )


@router.get("/api/auth/me")
def auth_me(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    memberships = _active_memberships(actor.user_id)
    return {
        "authenticated": True,
        "tenant": actor.tenant_slug,
        "companies": _company_payloads(memberships),
        "user": actor.user_payload,
        "permissions": sorted(actor.permissions),
        "is_platform_owner": False,
        "can_apply_company": actor.role_level >= 4,
        "needs_setup": False,
    }


@router.post("/api/auth/switch-tenant", response_model=LoginResponse)
def switch_tenant(
    payload: TenantSwitchRequest,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    memberships = _active_memberships(actor.user_id)
    membership = _default_membership(memberships, payload.tenant)
    if membership is None or membership["slug"] != payload.tenant.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Company access is unavailable",
        )
    return _login_response(
        account={
            "id": actor.user_id,
            "username": actor.username,
            "display_name": actor.display_name,
        },
        membership=membership,
        memberships=memberships,
        settings=settings,
    )


@router.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    # JWTs are short lived. Revocation and refresh sessions are introduced with the IAM slice.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/api/bootstrap")
def bootstrap(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    payload = bootstrap_payload(actor)
    payload.update(bootstrap_warehouse_payload(actor))
    return payload


@router.get("/api/overview/executive")
def executive_overview(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Return the V2 dashboard snapshot for the authenticated company only."""
    return executive_overview_payload(actor)


@router.get("/api/runtime/world")
def runtime_world(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Small live world snapshot for Runtime surfaces, backed by tenant PostgreSQL."""
    return runtime_world_snapshot(actor)


@router.get("/api/runtime/skills")
def runtime_skills(
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Human-visible legacy ability universe, projected as non-executable Skills."""
    response.headers["Cache-Control"] = "private, no-store"
    skills = skill_catalogue(actor)
    return {
        "catalogue_revision": migration_summary(actor)["revision"],
        "total": len(skills),
        "ready": sum(1 for item in skills if item["ready"]),
        "skills": skills,
    }


@router.get("/api/business/actions")
def business_actions(
    response: Response,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Return the single capability contract used by forms, terminal and AI."""
    response.headers["Cache-Control"] = "private, no-store"
    actions = business_action_catalogue(actor)
    tenant_actions = [item for item in actions if item["scope"] == "tenant"]
    return {
        "catalogue_revision": migration_summary(actor)["revision"],
        "total": len(actions),
        "tenant_total": len(tenant_actions),
        "platform_total": len(actions) - len(tenant_actions),
        "executable": sum(1 for item in actions if item["manual_execution"] == "execute"),
        "governed": sum(
            1 for item in actions if item["manual_execution"] == "governed_confirmation"
        ),
        "actions": actions,
    }


@router.post("/api/business/actions/{tool_name}/execute")
def business_action_execute(
    tool_name: str,
    payload: AiToolCallRequest,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Execute a manual form through the same adapter and validation as AI."""
    return execute_manual_action(actor, tool_name, payload.arguments)


@router.get("/api/map/zones")
def map_zones(actor: ActorContext = Depends(current_actor)) -> dict[str, list[dict[str, object]]]:
    return map_zones_payload(actor)


@router.get("/api/warehouses/geo")
def warehouses_geo(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Stable data API backed by the same typed store used by `warehouse list`."""
    return {"warehouses": bootstrap_warehouse_payload(actor)["warehouse_rows"]}


@router.get("/api/gis/overview")
def gis_overview_route(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return gis_overview(actor)


@router.get("/api/inventory/batches")
def inventory_batches_route(
    item_id: str, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return inventory_batches(actor, item_id)


@router.get("/api/alerts/by-item")
def inventory_alerts(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return alerts_by_item(actor)


@router.get("/api/returns/pending")
def returns_pending(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return pending_returns(actor)


@router.get("/api/reports/summary")
def warehouse_reports_summary(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return reports_summary(actor)


@router.post("/api/items")
def item_create(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_item(actor, payload)


@router.post("/api/items/update")
def item_update(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return update_item(actor, payload)


@router.post("/api/items/delete")
def item_delete(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return archive_item(actor, payload)


@router.post("/api/inbound/create")
def inbound_create(
    payload: InboundCreateRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_inbound(actor, payload.model_dump(exclude_none=True))


@router.post("/api/outbound/create")
def outbound_create(
    payload: OutboundCreateRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_outbound(actor, payload.model_dump(exclude_none=True))


@router.post("/api/replenishment")
def replenishment_create(
    payload: ReplenishmentRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_replenishment(actor, payload.model_dump(exclude_none=True))


@router.get("/api/inventory/shipments")
def shipments(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return {"shipments": shipment_rows(actor)}


@router.post("/api/inventory/shipments/dispatch")
def shipment_dispatch(
    payload: ShipmentDispatchRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return dispatch_shipment(actor, payload.model_dump(by_alias=True, exclude_none=True))


@router.post("/api/inventory/shipments/arrive")
def shipment_arrive(
    payload: ShipmentActionRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return arrive_shipment(actor, payload.shipment_no)


@router.post("/api/inventory/shipments/cancel")
def shipment_cancel(
    payload: ShipmentActionRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return cancel_shipment(actor, payload.shipment_no)


@router.get("/api/users")
def users(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Tenant-local people and role projection used by the V2 permissions page."""
    return users_payload(actor)


@router.get("/api/permissions/topology")
def permissions_topology(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return topology_payload(actor)


@router.get("/api/org/structure")
def org_structure(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return organization_structure(actor)


@router.get("/api/org/templates")
def org_templates(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return templates_payload(actor)


@router.get("/api/org/template-preview")
def org_template_preview(
    template: str, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return template_preview(actor, template)


@router.post("/api/org/apply-template")
def org_apply_template(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return apply_template(actor, payload)


@router.post("/api/org/departments")
def org_department_create(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_department(actor, payload)


@router.post("/api/org/departments/{unit_id}")
def org_department_update(
    unit_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return update_department(actor, unit_id, payload)


@router.post("/api/org/departments/{unit_id}/archive")
def org_department_archive(
    unit_id: str, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return archive_department(actor, unit_id)


@router.post("/api/org/departments/{unit_id}/permissions")
def org_department_permissions(
    unit_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return set_department_permissions(actor, unit_id, payload)


@router.post("/api/org/departments/{unit_id}/navigation")
def org_department_navigation(
    unit_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return set_department_navigation(actor, unit_id, payload)


@router.post("/api/org/positions")
def org_position_create(
    payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return create_position(actor, payload)


@router.post("/api/org/positions/{position_id}")
def org_position_update(
    position_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return update_position(actor, position_id, payload)


@router.post("/api/org/positions/{position_id}/archive")
def org_position_archive(
    position_id: str, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return archive_position(actor, position_id)


@router.post("/api/org/positions/{position_id}/navigation")
def org_position_navigation(
    position_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return set_position_navigation(actor, position_id, payload)


@router.post("/api/org/users/{user_id}/assign")
def org_user_assign(
    user_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return assign_user_position(actor, user_id, payload)


@router.post("/api/org/users/{user_id}/permissions")
def org_user_permissions(
    user_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return set_user_permissions(actor, user_id, payload)


@router.post("/api/org/users/{user_id}/navigation")
def org_user_navigation(
    user_id: str, payload: dict[str, object], actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return set_user_navigation(actor, user_id, payload)


@router.get("/api/memberships/pending")
def pending_memberships(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """State the current limitation explicitly until request workflows are migrated."""
    _ = actor
    return {
        "available": False,
        "requests": [],
        "pending_count": 0,
        "reason": "membership_request_workflow_not_migrated",
    }


@router.get("/api/auth/registrations")
def registrations(
    status: str = "pending", actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    _ = (status, actor)
    return {
        "available": False,
        "requests": [],
        "pending_count": 0,
        "reason": "registration_request_workflow_not_migrated",
    }


@router.get("/api/cli/commands")
def cli_commands(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Return the full catalogue with separate authorization/adapter states."""
    commands = command_catalogue(actor, include_unavailable=True)
    return {
        "commands": commands,
        "total": len(commands),
        "executable": sum(1 for command in commands if command["allowed"]),
    }


def _runtime_key_error(exc: RuntimeApiKeyError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/api/assistant/cli-keys")
@router.post("/api/runtime/keys")
def runtime_api_key_issue(
    payload: dict[str, object],
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Issue one current-user/current-company Runtime credential.

    The secret is returned exactly once. The stored record is only a peppered
    digest and an audience ceiling; every request reloads live authority.
    """
    try:
        return issue_runtime_api_key(actor, settings, payload)
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.get("/api/assistant/cli-keys")
@router.get("/api/runtime/keys")
def runtime_api_key_list(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    try:
        return list_runtime_api_keys(actor)
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.post("/api/assistant/cli-keys/{key_id}/revoke")
@router.delete("/api/runtime/keys/{key_id}")
def runtime_api_key_revoke(
    key_id: int,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    try:
        return revoke_runtime_api_key(actor, key_id)
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.post("/api/research/api-keys")
def research_api_key_issue(
    payload: dict[str, object],
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> dict[str, object]:
    """Issue a self-scoped, current-tenant key whose audience is research only."""
    try:
        return issue_research_api_key(actor, settings, payload)
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.get("/api/research/api-keys")
def research_api_key_list(
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    try:
        return list_runtime_api_keys(actor, required_scope="research")
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.delete("/api/research/api-keys/{key_id}")
def research_api_key_revoke(
    key_id: int,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    try:
        return revoke_runtime_api_key(
            actor,
            key_id,
            required_scope="research",
        )
    except RuntimeApiKeyError as exc:
        raise _runtime_key_error(exc) from exc


@router.get("/api/cli/migration-status")
def cli_migration_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Show imported-command progress without exposing an executable false positive."""
    return migration_summary(actor)


@router.post("/api/cli/exec")
def cli_execute(
    payload: CliExecuteRequest, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    return execute_cli_line(actor, payload.line)


@router.get("/api/ai/tools")
def ai_tools(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    """Return global command metadata, never another tenant's business data."""
    return {
        "tools": ai_tool_schemas(),
        "capability_states": ai_capability_states(),
        "catalogue_scope": "global_command_metadata",
        "data_scope": "current_tenant_only",
    }


@router.post("/api/ai/tools/{tool_name}/execute")
def ai_tool_execute(
    tool_name: str,
    payload: AiToolCallRequest,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return execute_tool_call(actor, tool_name, payload.arguments)


@router.get("/api/ai/memory/capsule")
def ai_memory_capsule(
    conversation_id: str,
    query: str = "",
    depth: str = "index",
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Inspect the same bounded memory capsule visible to Auto Runtime."""
    return build_memory_capsule(
        actor,
        conversation_id=conversation_id,
        query=query,
        depth=depth,
    )


@router.get("/api/ai/memory")
def ai_memories(
    conversation_id: str | None = None,
    limit: int = 100,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    memories = list_memory_units(
        actor,
        conversation_id=conversation_id,
        limit=limit,
    )
    return {
        "available": True,
        "trust": "derived_memory_requires_live_verification_for_actions",
        "memories": memories,
        "items": memories,
        "count": len(memories),
    }


@router.delete("/api/ai/memory/{memory_id}")
def ai_memory_forget(
    memory_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    """Forget a derived private memory without altering source transcripts."""
    return {
        "available": True,
        "memory": forget_memory_unit(actor, memory_id=memory_id),
        "raw_transcript_changed": False,
    }


@router.post("/api/agent/run/stream")
def agent_run_stream(
    payload: AgentRunRequest,
    actor: ActorContext = Depends(current_actor),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:
    """Shared Auto Runtime entry for every AI interaction surface."""
    run_id = str(uuid4())
    conversation = ensure_conversation(
        actor,
        conversation_id=payload.conversation_id,
        seed_text=payload.text,
        channel="assistant" if payload.surface == "secretary" else payload.surface,
    )
    conversation_id = str(conversation["id"])
    turn_id = payload.turn_id or run_id
    language = resolve_language_contract(
        payload.text,
        requested_locale=payload.locale,
        language_mode=payload.language_mode,
    )
    resume_requested = payload.resume_confirmation_action_id is not None
    if resume_requested != bool(payload.authorization_keychain_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "resume_confirmation_action_id and authorization_keychain_id "
                "must be supplied together"
            ),
        )
    existing_turn = messages_for_turn(
        actor,
        conversation_id=conversation_id,
        turn_id=turn_id,
    )
    existing_user = next(
        (message for message in existing_turn if message["role"] == "user"),
        None,
    )
    if existing_user and str(existing_user["content"]).strip() != payload.text.strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Turn identifier is already bound to different content",
        )
    if resume_requested:
        # A Keychain continuation is a server-side authorization signal, not a
        # second user utterance. Keep the immutable transcript free of fake
        # "continue" messages.
        user_message = {"id": None}
    else:
        user_message, _ = append_message(
            actor,
            conversation_id=conversation_id,
            role="user",
            content=payload.text,
            turn_id=turn_id,
            metadata={
                "surface": payload.surface,
                "status": "accepted",
                "context_mode": payload.context_mode,
                "language": language.as_dict(),
            },
        )
    existing_assistant = next(
        (message for message in existing_turn if message["role"] == "assistant"),
        None,
    )

    def events() -> object:
        yield json.dumps(
            {
                "event": "run_start",
                "run_id": run_id,
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "user_message_id": user_message["id"],
                "replayed": bool(existing_assistant),
                "surface": payload.surface,
                "context_mode": payload.context_mode,
                "response_locale": language.locale,
                "language_source": language.source,
                "language_mode": language.mode,
            },
            ensure_ascii=False,
        ) + "\n"

        def safe_runtime_activity(
            source: object,
        ) -> dict[str, object] | None:
            if not isinstance(source, dict):
                return None
            activity_id = str(source.get("activity_id") or "")[:180]
            if not activity_id:
                return None
            allowed: dict[str, object] = {
                "activity_id": activity_id,
                "kind": str(source.get("kind") or "runtime")[:48],
                "phase": str(source.get("phase") or "")[:80],
                "status": str(source.get("status") or "running")[:48],
            }
            for key in (
                "model",
                "tool_name",
                "command",
                "description",
                "judgment",
                "result_status",
            ):
                if source.get(key) not in (None, ""):
                    value = str(source[key])[:500]
                    allowed[key] = (
                        public_message(value, locale=language.locale, fallback="")
                        if key in {"description", "judgment"}
                        else value
                    )
            for key in ("elapsed_ms", "round", "count"):
                if source.get(key) is not None:
                    try:
                        allowed[key] = max(0, int(source[key]))
                    except (TypeError, ValueError):
                        pass
            selected = source.get("selected_tool_names")
            if isinstance(selected, list):
                allowed["selected_tool_names"] = [
                    str(item)[:180] for item in selected[:24] if str(item).strip()
                ]
            return allowed

        if existing_assistant:
            existing_metadata = existing_assistant.get("metadata", {})
            replay_downloads = existing_metadata.get("downloads")
            replay_downloads = (
                [dict(item) for item in replay_downloads if isinstance(item, dict)][:12]
                if isinstance(replay_downloads, list)
                else []
            )
            stored_activities = existing_assistant.get("metadata", {}).get(
                "runtime_activities"
            )
            for stored_activity in (
                stored_activities if isinstance(stored_activities, list) else []
            ):
                activity = safe_runtime_activity(stored_activity)
                if activity:
                    yield json.dumps(
                        {
                            "event": "runtime_activity",
                            "run_id": run_id,
                            "conversation_id": conversation_id,
                            **activity,
                        },
                        ensure_ascii=False,
                    ) + "\n"
            yield (
                json.dumps(
                    {
                        "event": "final",
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "turn_id": turn_id,
                        "message_id": existing_assistant["id"],
                        "status": (
                            existing_assistant.get("metadata", {}).get("status")
                            or "succeeded"
                        ),
                        "message": existing_assistant["content"],
                        "replayed": True,
                        "response_locale": (
                            existing_assistant.get("metadata", {}).get(
                                "response_locale"
                            )
                            or language.locale
                        ),
                        "downloads": replay_downloads,
                        "cards": (
                            [{"card_type": "download", "downloads": replay_downloads}]
                            if replay_downloads
                            else []
                        ),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            return
        text = payload.text.strip()
        activity_queue: Queue[dict[str, object] | object] = Queue()
        activity_sentinel = object()
        worker_state: dict[str, object] = {}
        activity_by_id: dict[str, dict[str, object]] = {}
        activity_order: list[str] = []

        def publish_activity(source: dict[str, object]) -> None:
            allowed = safe_runtime_activity(source)
            if allowed is None:
                return
            activity_id = str(allowed["activity_id"])
            previous = activity_by_id.get(activity_id)
            if previous is None:
                activity_order.append(activity_id)
                activity_by_id[activity_id] = allowed
            else:
                previous.update(allowed)
                allowed = dict(previous)
            activity_queue.put(allowed)

        def run_worker() -> None:
            try:
                if resume_requested:
                    publish_activity(
                        {
                            "activity_id": "authorization:keychain",
                            "kind": "authorization",
                            "phase": "authorization_keychain",
                            "status": "running",
                            "description": "AI Runtime 正在核對授權 Keychain",
                        }
                    )
                    signal = authorization_signal_for_runtime(
                        actor,
                        payload.resume_confirmation_action_id,
                        authorization_keychain_id=payload.authorization_keychain_id,
                        conversation_id=conversation_id,
                        settings=settings,
                    )
                    worker_state["authorization_signal"] = signal
                    publish_activity(
                        {
                            "activity_id": "authorization:keychain",
                            "kind": "authorization",
                            "phase": "authorization_keychain",
                            "status": "succeeded",
                            "description": "授權信號已交給 AI Runtime，尚未執行業務操作",
                        }
                    )
                    if signal.get("executable") is True:
                        worker_state["answer"] = run_auto_runtime(
                            actor,
                            settings,
                            str(signal.get("goal") or text),
                            surface=payload.surface,
                            conversation_id=conversation_id,
                            run_id=run_id,
                            context_mode=payload.context_mode,
                            response_locale=language.locale,
                            activity_callback=publish_activity,
                            authorization_signal=signal,
                        )
                    else:
                        worker_state["resume"] = signal
                else:
                    worker_state["answer"] = run_auto_runtime(
                        actor,
                        settings,
                        text,
                        surface=payload.surface,
                        conversation_id=conversation_id,
                        run_id=run_id,
                        context_mode=payload.context_mode,
                        response_locale=language.locale,
                        activity_callback=publish_activity,
                    )
            except Exception as exc:
                worker_state["error"] = exc
            finally:
                activity_queue.put(activity_sentinel)

        Thread(
            target=run_worker,
            name=f"warehouse-runtime-{run_id[:8]}",
            daemon=True,
        ).start()
        while True:
            try:
                activity = activity_queue.get(timeout=8)
            except Empty:
                yield json.dumps(
                    {"event": "heartbeat", "run_id": run_id},
                    ensure_ascii=False,
                ) + "\n"
                continue
            if activity is activity_sentinel:
                break
            yield json.dumps(
                {
                    "event": "runtime_activity",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    **dict(activity),
                },
                ensure_ascii=False,
            ) + "\n"

        runtime_activities = [
            dict(activity_by_id[activity_id])
            for activity_id in activity_order
            if activity_id in activity_by_id
        ]
        if worker_state.get("error") is not None:
            exc = worker_state["error"]
            failed_message, _ = append_message(
                actor,
                conversation_id=conversation_id,
                role="assistant",
                content=localized_runtime_error(language.locale, exc),
                turn_id=turn_id,
                metadata={
                    "run_id": run_id,
                    "surface": payload.surface,
                    "context_mode": payload.context_mode,
                    "response_locale": language.locale,
                    "language_source": language.source,
                    "language_mode": language.mode,
                    "status": "ai_provider_unavailable",
                    "runtime_activities": runtime_activities,
                },
            )
            yield (
                json.dumps(
                    {
                        "event": "final",
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "turn_id": turn_id,
                        "message_id": failed_message["id"],
                        "status": "ai_provider_unavailable",
                        "message": failed_message["content"],
                        "response_locale": language.locale,
                        "language_source": language.source,
                    }
                )
                + "\n"
            )
            return
        if worker_state.get("resume") is not None:
            resumed = worker_state.get("resume") or {}
            action = resumed.get("action") if isinstance(resumed, dict) else None
            action = action if isinstance(action, dict) else {}
            action_status = str(action.get("status") or "failed")
            succeeded = action_status == "completed"
            command = str(action.get("command") or "已授权操作")
            has_delivery = bool(action.get("credential_deliveries"))
            if succeeded and has_delivery:
                message = (
                    f"已由 AI Runtime 完成 {command}。API Key 已签发，"
                    "请在下方一次性安全卡中领取并立即保存。"
                )
            elif succeeded:
                message = f"已由 AI Runtime 完成 {command}，执行结果已写入业务系统与审计记录。"
            else:
                if language.locale == "zh-Hant":
                    message = (
                        f"AI Runtime 已接手 {command}，但操作未完成。"
                        "原始診斷已保留於受保護的審計記錄。"
                    )
                elif language.locale == "en":
                    message = (
                        f"AI Runtime took over {command}, but the operation did not "
                        "complete. The original diagnostic is retained in the protected "
                        "audit record."
                    )
                else:
                    message = (
                        f"AI Runtime 已接手 {command}，但操作未完成。"
                        "原始诊断已保留在受保护的审计记录中。"
                    )
            yield (
                json.dumps(
                    {
                        "event": "authorization_completed",
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "action": action,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            assistant_message, _ = append_message(
                actor,
                conversation_id=conversation_id,
                role="assistant",
                content=message,
                turn_id=turn_id,
                metadata={
                    "run_id": run_id,
                    "surface": payload.surface,
                    "context_mode": payload.context_mode,
                    "response_locale": language.locale,
                    "status": "succeeded" if succeeded else "failed",
                    "runtime_activities": runtime_activities,
                    "confirmation_action_id": action.get("id"),
                    "authorization_keychain_id": payload.authorization_keychain_id,
                },
            )
            yield (
                json.dumps(
                    {
                        "event": "final",
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "turn_id": turn_id,
                        "message_id": assistant_message["id"],
                        "status": "succeeded" if succeeded else "failed",
                        "message": assistant_message["content"],
                        "response_locale": language.locale,
                        "cards": [
                            {
                                "card_type": "operation_confirmation",
                                "action": action,
                            }
                        ],
                        "credentials": [],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            return
        answer = worker_state["answer"]
        runtime_downloads = [dict(item) for item in answer.downloads]
        authorization_action = None
        if resume_requested:
            authorization = worker_state.get("authorization_signal")
            authorization = authorization if isinstance(authorization, dict) else {}
            candidate = authorization.get("action")
            if isinstance(candidate, dict):
                authorization_action = candidate
            for tool_result in answer.tool_results:
                if not isinstance(tool_result, dict):
                    continue
                result = tool_result.get("result")
                result = result if isinstance(result, dict) else {}
                candidate = result.get("action")
                if (
                    isinstance(candidate, dict)
                    and str(candidate.get("id") or candidate.get("action_id") or "")
                    == str(payload.resume_confirmation_action_id or "")
                ):
                    authorization_action = candidate
            if isinstance(authorization_action, dict):
                authorization_status = str(authorization_action.get("status") or "")
                yield (
                    json.dumps(
                        {
                            "event": (
                                "authorization_completed"
                                if authorization_status
                                in {
                                    "completed",
                                    "cancelled",
                                    "failed",
                                    "expired",
                                    "outcome_unknown",
                                }
                                else "authorization_observed"
                            ),
                            "run_id": run_id,
                            "conversation_id": conversation_id,
                            "action": authorization_action,
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
        for confirmation_action in answer.confirmation_actions:
            yield (
                json.dumps(
                    {
                        "event": "confirmation_required",
                        "run_id": run_id,
                        "conversation_id": conversation_id,
                        "action": confirmation_action,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        yield (
            json.dumps(
                {
                    "event": "runtime_state",
                    "phase": "observe",
                    "observations": answer.observations,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        yield (
            json.dumps(
                {
                    "event": "runtime_state",
                    "phase": "plan",
                    "plan": answer.plan,
                    "capabilities": [
                        {
                            "tool_name": str(item.get("tool_name") or "")[:180],
                            "judgment": str(item.get("judgment") or "")[:48],
                        }
                        for item in answer.decisions
                        if isinstance(item, dict) and item.get("tool_name")
                    ][:24],
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        yield (
            json.dumps(
                {
                    "event": "runtime_state",
                    "phase": "reflect",
                    "status": (
                        "reflected_after_capability_execution"
                        if answer.tool_results
                        else "reflected_without_capability_execution"
                    ),
                    "capability_results": [
                        {
                            "tool_name": str(item.get("tool_name") or "")[:180],
                            "status": str(
                                (
                                    item.get("result")
                                    if isinstance(item.get("result"), dict)
                                    else {}
                                ).get("status")
                                or (
                                    "succeeded"
                                    if (
                                        item.get("result")
                                        if isinstance(item.get("result"), dict)
                                        else {}
                                    ).get("ok") is not False
                                    else "failed"
                                )
                            )[:48],
                        }
                        for item in answer.tool_results
                        if isinstance(item, dict) and item.get("tool_name")
                    ][:24],
                    "summary": {
                        "goal_complete": bool(answer.reflection.get("goal_complete")),
                        "requires_user_input": bool(
                            answer.reflection.get("requires_user_input")
                        ),
                        "runtime_stop_reason": str(
                            answer.reflection.get("runtime_stop_reason") or ""
                        )[:80],
                        "autonomous_rounds": max(
                            0,
                            int(answer.reflection.get("autonomous_rounds") or 0),
                        ),
                    },
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        goal_complete = (
            bool(answer.reflection.get("goal_complete"))
            if answer.reflection
            else True
        )
        answer_status = (
            "waiting_confirmation"
            if answer.confirmation_actions
            else (
                "succeeded"
                if goal_complete
                else (
                    "requires_user_input"
                    if bool(answer.reflection.get("requires_user_input"))
                    else "incomplete"
                )
            )
        )
        assistant_message, _ = append_message(
            actor,
            conversation_id=conversation_id,
            role="assistant",
            content=answer.message,
            turn_id=turn_id,
            metadata={
                "run_id": run_id,
                "surface": payload.surface,
                "context_mode": payload.context_mode,
                "response_locale": answer.response_locale,
                "language_source": language.source,
                "language_mode": language.mode,
                "status": answer_status,
                "engine": answer.model,
                "goal": answer.goal,
                "plan": list(answer.plan),
                "runtime_activities": runtime_activities,
                "downloads": runtime_downloads,
                "confirmation_action_ids": [
                    int(action["id"])
                    for action in answer.confirmation_actions
                    if action.get("id") is not None
                ],
                "authorization_action_id": (
                    authorization_action.get("id")
                    if isinstance(authorization_action, dict)
                    else None
                ),
            },
        )
        yield (
            json.dumps(
                {
                    "event": "final",
                    "run_id": run_id,
                    "conversation_id": conversation_id,
                    "turn_id": turn_id,
                    "message_id": assistant_message["id"],
                    "status": answer_status,
                    "message": assistant_message["content"],
                    "engine": answer.model,
                    "goal": answer.goal,
                    "context_mode": payload.context_mode,
                    "response_locale": answer.response_locale,
                    "language_source": language.source,
                    "downloads": runtime_downloads,
                    "cards": [
                        *(
                            [{"card_type": "download", "downloads": runtime_downloads}]
                            if runtime_downloads
                            else []
                        ),
                        *[
                            {
                                "card_type": "operation_confirmation",
                                "action": action,
                            }
                            for action in answer.confirmation_actions
                        ],
                        *(
                            [
                                {
                                    "card_type": "operation_confirmation",
                                    "action": authorization_action,
                                }
                            ]
                            if isinstance(authorization_action, dict)
                            else []
                        ),
                    ],
                    # One-time secrets are deliberately streamed only on the
                    # first response. They are absent from conversation
                    # messages, run snapshots, audit payloads and replays.
                    "credentials": list(answer.credentials),
                },
                ensure_ascii=False,
            )
            + "\n"
        )

    return StreamingResponse(
        events(),
        media_type="application/x-ndjson",
        background=BackgroundTask(
            run_background_memory_steward,
            actor,
            settings,
        ),
    )


@router.get("/api/platform/templates")
@router.get("/api/industry-templates")
def industry_templates(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return {"templates": list_template_summaries(), "active_template": actor.industry_template_key}


@router.get("/api/industry-templates/{template_key}")
def industry_template(
    template_key: str, actor: ActorContext = Depends(current_actor)
) -> dict[str, object]:
    template = get_template_detail(template_key)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Industry template not found",
        )
    return template
