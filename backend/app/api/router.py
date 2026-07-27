from __future__ import annotations

import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import text

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
from app.services.bootstrap import bootstrap_payload
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
from app.services.templates import get_template_detail, list_template_summaries
from app.services.topology import map_zones_payload
from app.services.warehouse_operations import (
    alerts_by_item,
    arrive_shipment,
    bootstrap_warehouse_payload,
    cancel_shipment,
    create_inbound,
    create_outbound,
    create_replenishment,
    dispatch_shipment,
    gis_overview,
    inventory_batches,
    pending_returns,
    reports_summary,
    shipment_rows,
)
from app.terminal.catalog import (
    ai_capability_states,
    ai_tool_schemas,
    command_catalogue,
    migration_summary,
)
from app.terminal.executor import execute_cli_line, execute_tool_call

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
    """Return only commands that this actor can execute now."""
    return {"commands": command_catalogue(actor)}


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


@router.post("/api/agent/run/stream")
def agent_run_stream(
    payload: AgentRunRequest, actor: ActorContext = Depends(current_actor)
) -> StreamingResponse:
    """A provider-neutral AI bridge; direct `!command` calls use the governed path.

    A model provider is intentionally not embedded here.  An AI integration
    first fetches `/api/ai/tools`, then invokes the tool endpoint above with
    the actor's delegated session; it never receives a database credential.
    """
    run_id = str(uuid4())

    def events() -> object:
        yield json.dumps({"event": "run_start", "run_id": run_id}) + "\n"
        text = payload.text.strip()
        if text.startswith("!") and text[1:].strip():
            yield json.dumps({"event": "step_start", "step_no": 1, "name": "command"}) + "\n"
            result = execute_cli_line(actor, text[1:].strip(), origin="ai_tool")
            yield json.dumps({"event": "step", "step_no": 1, "result": result}) + "\n"
            message = "Command completed" if result.get("ok") else str(result.get("error"))
            yield (
                json.dumps(
                    {
                        "event": "final",
                        "run_id": run_id,
                        "status": result["status"],
                        "message": message,
                    }
                )
                + "\n"
            )
            return
        yield (
            json.dumps(
                {
                    "event": "final",
                    "run_id": run_id,
                    "status": "awaiting_ai_provider",
                    "message": (
                        "AI provider is not configured. Direct commands can use !command; "
                        "providers must use /api/ai/tools."
                    ),
                }
            )
            + "\n"
        )

    return StreamingResponse(events(), media_type="application/x-ndjson")


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
