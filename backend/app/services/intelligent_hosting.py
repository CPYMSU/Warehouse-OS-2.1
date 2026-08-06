"""Conversational, resumable facade over the native workspace control plane.

The facade does not replace the storage, source, Runtime or deployment domain
services.  It lets a human-facing secretary or an external terminal AI state a
desired outcome, while retaining a durable plan, evidence and exact failure
stage around calls to those authoritative services.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.api.deps import ActorContext
from app.core.config import Settings
from app.db.session import tenant_session
from app.services.digital_asset_hosting import (
    WorkspaceCredential,
    create_asset,
    create_workspace,
    issue_workspace_key,
    workspace_asset_identity,
    workspace_info,
)
from app.services.hosting_fabric import apply_fabric_resource, observe_fabric
from app.services.hosting_requirements import requirement_downloads
from app.services.pages_runtime import (
    configure_pages_site,
    get_pages_site,
    validate_site_key,
)
from app.services.workspace_deployments import (
    activate_workspace_deployment,
    configure_workspace_runtime,
    list_workspace_deployments,
    list_workspace_sources,
    probe_workspace_storage,
)

SESSION_TERMINAL_STATUSES = frozenset({"completed", "cancelled", "failed"})
CLIENT_KINDS = frozenset({"unknown", "web_secretary", "terminal_ai", "external_ai", "automation"})
RUNTIME_TYPES = frozenset(
    {"auto", "static", "web", "api", "worker", "agent", "container", "compose"}
)


@dataclass(frozen=True)
class HostingPrincipal:
    tenant_id: UUID
    auth_kind: str
    actor: ActorContext | None = None
    credential: WorkspaceCredential | None = None

    @property
    def actor_user_id(self) -> UUID | None:
        return self.actor.user_id if self.actor is not None else None

    @property
    def credential_id(self) -> UUID | None:
        return self.credential.credential_id if self.credential is not None else None


def assistant_manifest() -> dict[str, object]:
    """Return a stable machine contract for external AIs and dm.py."""

    return {
        "schema": "warehouse.intelligent-hosting.v2",
        "version": "2.5",
        "purpose": (
            "Converse about one hosting goal, submit a desired state, attach source, "
            "and observe exact deployment evidence without composing low-level routes."
        ),
        "authentication": {
            "workspace_key": {
                "prefix": "wak_",
                "boundary": "the key's own tenant and workspace",
                "recommended_scopes": [
                    "workspace:read",
                    "deploy:read",
                    "deploy:write",
                    "logs:read",
                ],
            },
            "account_session": {
                "boundary": "the active company and the account's live permissions"
            },
        },
        "conversation": {
            "create": "POST /api/hosting/v2/sessions",
            "message": "POST /api/hosting/v2/sessions/{session_id}/messages",
            "message_stream": ("POST /api/hosting/v2/sessions/{session_id}/messages/stream"),
            "status": "GET /api/hosting/v2/sessions/{session_id}?refresh=true",
            "events": "GET /api/hosting/v2/sessions/{session_id}/events",
            "source_upload": {
                "initialize": (
                    "POST /api/hosting/v2/sessions/{session_id}/source-uploads"
                ),
                "part": (
                    "PUT /api/hosting/v2/sessions/{session_id}/source-uploads/"
                    "{upload_id}/parts/{part_no}"
                ),
                "complete": (
                    "POST /api/hosting/v2/sessions/{session_id}/source-uploads/"
                    "{upload_id}/complete"
                ),
                "status": (
                    "GET /api/hosting/v2/sessions/{session_id}/source-uploads/{upload_id}"
                ),
                "attach": (
                    "POST /api/hosting/v2/sessions/{session_id}/sources/attach"
                ),
                "legacy_small_package": (
                    "POST /api/hosting/v2/sessions/{session_id}/sources"
                ),
            },
            "cancel": "POST /api/hosting/v2/sessions/{session_id}/cancel",
        },
        "pages_runtime": {
            "workspace_key_api": {
                "site": "GET /api/workspaces/v1/pages",
                "configure_site": "PUT /api/workspaces/v1/pages",
                "design_context": "GET /api/workspaces/v1/pages/design",
                "read_file": "GET /api/workspaces/v1/pages/files/{path}",
            },
            "hosting_session_api": {
                "site": "GET /api/hosting/v2/sessions/{session_id}/pages",
                "configure_site": "PUT /api/hosting/v2/sessions/{session_id}/pages",
                "design_context": (
                    "GET /api/hosting/v2/sessions/{session_id}/pages/design"
                ),
                "read_file": (
                    "GET /api/hosting/v2/sessions/{session_id}/pages/files/{path}"
                ),
            },
            "stable_url": "https://bonfirework.org/apps/{site_key}/",
            "entry_mode": "warehouse_os",
            "isolated_runtime_origin": "https://{site_key}.bonfirework.org/",
            "public_alias_default": False,
            "code_policy": "read source; upload a new immutable version; verify; activate",
            "active_release_editable_in_place": False,
        },
        "desired_state": {
            "pages": {
                "site_key": (
                    "optional globally unique route name for "
                    "https://bonfirework.org/apps/{site_key}/"
                ),
                "public_alias_enabled": (
                    "optional boolean; defaults to false; advertises the isolated "
                    "{site_key}.apps.bonfirework.org runtime origin as an extra URL"
                ),
            },
            "storage": {"verify": "boolean; defaults to true before deployment"},
            "runtime": {
                "type": "auto|static|web|api|worker|agent|job|container|compose",
                "runtime": "optional runtime hint such as python3.12 or node20",
                "profile": "optional enabled Runtime profile",
                "component": "optional stable component name",
                "entrypoint": "optional source-relative entrypoint",
                "build_command": "optional build command",
                "start_command": "optional start command",
                "health_path": "optional HTTP health path",
                "image": "optional OCI image reference",
                "dockerfile": "optional source-relative Dockerfile",
                "compose_file": "optional source-relative Compose file",
                "route_service": "optional public Compose service",
                "port": "optional container HTTP port",
                "command": "optional container command override",
                "database_url_env": (
                    "optional safe env alias for the workspace database URL; "
                    "requires database:admin"
                ),
                "timeout_seconds": "one-shot job timeout, 30..7200",
            },
            "deployment": {
                "state": "observed|ready",
                "activate_when_healthy": "boolean; defaults to true",
            },
            "resources": {
                "type": "array",
                "items": "{kind, resource_key?, spec, required?}",
                "kinds": [
                    "container",
                    "compose",
                    "domain",
                    "environment",
                    "secret",
                    "scaling",
                    "database_migration",
                    "repository",
                    "backup",
                    "accelerator",
                ],
                "secret_rule": (
                    "Secret plaintext must be submitted directly to the fabric endpoint; "
                    "it is never retained in conversation desired_state."
                ),
            },
        },
        "execution": {
            "preview": "Set execute=false to return a plan without mutation.",
            "run": "Set execute=true after reviewing the returned desired state.",
            "idempotency": "A session/source/runtime tuple is replay-safe.",
            "raw_reasoning_exposed": False,
        },
        "downloads": [
            {
                "name": "dm.py",
                "url": "/api/hosting/v2/dm.py",
                "media_type": "text/x-python",
            },
            {
                "name": "dm-guide.md",
                "url": "/api/hosting/v2/dm-guide.md",
                "media_type": "text/markdown",
            },
            *requirement_downloads(public_surface="hosting"),
        ],
    }


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    return value


def _client_kind(value: object) -> str:
    clean = str(value or "unknown").strip().lower()
    return clean if clean in CLIENT_KINDS else "unknown"


def _merge_desired_state(current: dict[str, object], supplied: object) -> dict[str, object]:
    if supplied is None:
        return dict(current)
    if not isinstance(supplied, dict):
        raise HTTPException(status_code=422, detail="desired_state must be an object")
    merged = dict(current)
    for key, value in supplied.items():
        if key == "resources":
            if not isinstance(value, list) or len(value) > 64:
                raise HTTPException(
                    status_code=422,
                    detail="desired_state.resources must be an array with at most 64 items",
                )
            clean_resources: list[dict[str, object]] = []
            for item in value:
                if not isinstance(item, dict) or not isinstance(item.get("spec"), dict):
                    raise HTTPException(
                        status_code=422,
                        detail="Every desired_state resource requires kind and spec",
                    )
                if str(item.get("kind") or "").lower() == "secret" and "value" in item["spec"]:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Secret plaintext cannot be retained in a conversation; "
                            "apply it through /api/workspaces/v1/fabric/resources"
                        ),
                    )
                clean_resources.append(dict(item))
            merged[key] = clean_resources
            continue
        if key not in {"storage", "runtime", "deployment", "pages"}:
            raise HTTPException(
                status_code=422,
                detail={"reason": "unsupported_desired_state", "field": str(key)},
            )
        if not isinstance(value, dict):
            raise HTTPException(status_code=422, detail=f"desired_state.{key} must be an object")
        base = merged.get(key) if isinstance(merged.get(key), dict) else {}
        merged[key] = {**base, **value}
    pages = merged.get("pages") if isinstance(merged.get("pages"), dict) else {}
    if pages:
        unsupported = set(pages) - {"site_key", "public_alias_enabled"}
        if unsupported:
            raise HTTPException(
                status_code=422,
                detail={
                    "reason": "unsupported_pages_desired_state",
                    "fields": sorted(unsupported),
                },
            )
        pages["site_key"] = validate_site_key(pages.get("site_key"))
        if "public_alias_enabled" in pages and not isinstance(
            pages["public_alias_enabled"], bool
        ):
            raise HTTPException(
                status_code=422,
                detail="desired_state.pages.public_alias_enabled must be a boolean",
            )
        merged["pages"] = pages
    runtime = merged.get("runtime") if isinstance(merged.get("runtime"), dict) else {}
    runtime_type = str(runtime.get("type") or "auto").lower()
    if runtime_type not in RUNTIME_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                "desired_state.runtime.type must be "
                "auto/static/web/api/worker/agent/container/compose"
            ),
        )
    if runtime:
        runtime["type"] = runtime_type
        merged["runtime"] = runtime
    deployment = merged.get("deployment") if isinstance(merged.get("deployment"), dict) else {}
    desired_deployment = str(deployment.get("state") or "observed").lower()
    if desired_deployment not in {"observed", "ready"}:
        raise HTTPException(
            status_code=422,
            detail="desired_state.deployment.state must be observed or ready",
        )
    if deployment:
        deployment["state"] = desired_deployment
        merged["deployment"] = deployment
    return merged


def _actor_can_manage(actor: ActorContext) -> bool:
    return actor.role_level >= 10 or bool(
        {"assets.manage", "asset_mgmt.manage"}.intersection(actor.permissions)
    )


def credential_for_actor(actor: ActorContext, workspace_ref: object) -> WorkspaceCredential:
    """Bind an account-authorized session to an existing active workspace key row."""

    if not _actor_can_manage(actor):
        raise HTTPException(status_code=403, detail="Asset management permission is required")
    identity = workspace_asset_identity(actor, workspace_ref)
    workspace_id = UUID(str(identity["workspace"]["uuid"]))
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    SELECT id, label, scopes, key_kind, parent_credential_id
                    FROM digital_asset.api_credentials
                    WHERE workspace_id=:workspace_id
                      AND revoked_at IS NULL
                      AND (expires_at IS NULL OR expires_at > now())
                    ORDER BY CASE key_kind WHEN 'primary' THEN 0 ELSE 1 END,
                             issued_at DESC
                    LIMIT 1
                    """
                ),
                {"workspace_id": workspace_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "workspace_has_no_active_key",
                "message": "Create or rotate the workspace primary key first",
            },
        )
    return WorkspaceCredential(
        tenant_id=actor.tenant_id,
        workspace_id=workspace_id,
        credential_id=row["id"],
        scopes=frozenset(str(scope) for scope in row["scopes"]),
        label=str(row["label"]),
        key_kind=str(row["key_kind"]),
        parent_credential_id=row["parent_credential_id"],
    )


def provision_for_session(
    actor: ActorContext,
    payload: dict[str, object],
    settings: Settings,
) -> tuple[WorkspaceCredential, dict[str, object], dict[str, object] | None]:
    """Idempotently provision by workspace key and return a one-time key only if new."""

    if not _actor_can_manage(actor):
        raise HTTPException(status_code=403, detail="Asset management permission is required")
    name = str(payload.get("name") or "").strip()
    workspace_key = str(payload.get("workspace_key") or "").strip().lower()
    if not name or not workspace_key:
        raise HTTPException(
            status_code=422, detail="provision.name and provision.workspace_key are required"
        )
    with tenant_session(actor.tenant_id) as session:
        existing_workspace = session.execute(
            text(
                """
                    SELECT w.id FROM digital_asset.workspaces AS w
                    WHERE w.workspace_key=:workspace_key AND w.status='active'
                    """
            ),
            {"workspace_key": workspace_key},
        ).scalar_one_or_none()
        matching_assets = (
            session.execute(
                text(
                    """
                    SELECT id FROM digital_asset.assets
                    WHERE lower(name)=lower(:name) AND status!='archived'
                    ORDER BY created_at DESC LIMIT 2
                    """
                ),
                {"name": name},
            )
            .scalars()
            .all()
        )
    if existing_workspace is not None:
        return (
            credential_for_actor(actor, existing_workspace),
            workspace_asset_identity(actor, existing_workspace),
            None,
        )
    if len(matching_assets) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "ambiguous_existing_asset",
                "message": "Multiple assets have this name; provide workspace_ref instead",
            },
        )
    if matching_assets:
        asset_ref: object = matching_assets[0]
        asset_result: dict[str, object] | None = None
    else:
        asset_result = create_asset(actor, payload)
        asset_ref = asset_result["asset"]["uuid"]
    workspace_result = create_workspace(actor, asset_ref, payload)
    workspace = workspace_result["workspace"]
    key_result = issue_workspace_key(
        actor,
        workspace["uuid"],
        payload,
        signing_secret=settings.integration_secret,
        key_kind="primary",
    )
    credential = credential_for_actor(actor, workspace["uuid"])
    identity = workspace_asset_identity(actor, workspace["uuid"])
    provisioned = {
        "asset": asset_result["asset"] if asset_result else identity["asset"],
        "workspace": workspace,
        "components": workspace_result.get("components", []),
        "database": workspace_result.get("database"),
        "storage": workspace_result.get("storage"),
    }
    return credential, identity, {"provisioned": provisioned, "credential": key_result}


def _event(
    tenant_id: UUID,
    session_id: UUID,
    event_type: str,
    stage: str,
    event_status: str,
    payload: dict[str, object],
) -> dict[str, object]:
    with tenant_session(tenant_id) as session:
        session.execute(
            text("SELECT id FROM digital_asset.hosting_agent_sessions WHERE id=:id FOR UPDATE"),
            {"id": session_id},
        ).scalar_one()
        sequence = int(
            session.execute(
                text(
                    "SELECT COALESCE(max(sequence),0)+1 "
                    "FROM digital_asset.hosting_agent_events WHERE session_id=:id"
                ),
                {"id": session_id},
            ).scalar_one()
        )
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO digital_asset.hosting_agent_events(
                      tenant_id, session_id, sequence, event_type, stage, status, payload
                    ) VALUES (
                      :tenant_id, :session_id, :sequence, :event_type, :stage,
                      :status, CAST(:payload AS jsonb)
                    ) RETURNING *
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "session_id": session_id,
                    "sequence": sequence,
                    "event_type": event_type,
                    "stage": stage,
                    "status": event_status,
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                },
            )
            .mappings()
            .one()
        )
    return _json_safe(dict(row))


def _row(tenant_id: UUID, session_id: object, *, lock: bool = False) -> dict[str, object]:
    try:
        parsed = UUID(str(session_id))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid hosting session id") from exc
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    "SELECT * FROM digital_asset.hosting_agent_sessions "
                    "WHERE id=:id" + (" FOR UPDATE" if lock else "")
                ),
                {"id": parsed},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Hosting session not found")
    return dict(row)


def _assert_principal_session(principal: HostingPrincipal, row: dict[str, object]) -> None:
    if row["tenant_id"] != principal.tenant_id:
        raise HTTPException(status_code=404, detail="Hosting session not found")
    if (
        principal.credential is not None
        and row["workspace_id"] != principal.credential.workspace_id
    ):
        raise HTTPException(
            status_code=403,
            detail="Workspace key cannot access another workspace's hosting session",
        )


def _credential_for_session(
    principal: HostingPrincipal, row: dict[str, object]
) -> WorkspaceCredential:
    _assert_principal_session(principal, row)
    if principal.credential is not None:
        return principal.credential
    if principal.actor is None:
        raise HTTPException(status_code=401, detail="Authentication is required")
    return credential_for_actor(principal.actor, row["workspace_id"])


def _safe_call(label: str, callback: Any) -> dict[str, object]:
    try:
        value = callback()
        return value if isinstance(value, dict) else {"ok": True, "value": value}
    except HTTPException as exc:
        return {
            "ok": False,
            "unavailable": True,
            "source": label,
            "http_status": exc.status_code,
            "detail": exc.detail,
        }


def observe_workspace(credential: WorkspaceCredential) -> dict[str, object]:
    info = workspace_info(credential)
    sources = _safe_call("sources", lambda: list_workspace_sources(credential))
    deployments = _safe_call(
        "deployments", lambda: list_workspace_deployments(credential, limit=20)
    )
    fabric = _safe_call("fabric", lambda: observe_fabric(credential))
    pages = _safe_call("pages", lambda: get_pages_site(credential))
    return {
        "workspace": info.get("workspace"),
        "components": info.get("components", []),
        "databases": info.get("databases", []),
        "credential": info.get("credential"),
        "sources": sources,
        "deployments": deployments,
        "fabric": fabric,
        "pages": pages,
    }


def _wants_ready(desired_state: dict[str, object]) -> bool:
    deployment = (
        desired_state.get("deployment") if isinstance(desired_state.get("deployment"), dict) else {}
    )
    return deployment.get("state") == "ready"


def _plan(desired_state: dict[str, object], snapshot: dict[str, object]) -> dict[str, object]:
    source_payload = snapshot.get("sources") if isinstance(snapshot.get("sources"), dict) else {}
    wants_ready = _wants_ready(desired_state)
    observation_diagnostic: dict[str, object] | None = None
    resources = (
        desired_state.get("resources") if isinstance(desired_state.get("resources"), list) else []
    )
    repository_supplies_source = any(
        isinstance(item, dict) and str(item.get("kind") or "") == "repository" for item in resources
    )
    if wants_ready and not source_payload.get("ok") and not repository_supplies_source:
        observation_diagnostic = failure_diagnostic(
            "source.observe",
            HTTPException(
                status_code=int(source_payload.get("http_status") or 503),
                detail=source_payload.get("detail") or {"reason": "source_observation_unavailable"},
            ),
        )
    source_count = int(source_payload.get("count") or 0) if source_payload.get("ok") else 0
    steps: list[dict[str, object]] = [
        {
            "step": "observe_workspace",
            "status": "succeeded",
            "effect": "read",
        }
    ]
    pages_options = (
        desired_state.get("pages") if isinstance(desired_state.get("pages"), dict) else {}
    )
    if pages_options.get("site_key"):
        pages_observation = (
            snapshot.get("pages") if isinstance(snapshot.get("pages"), dict) else {}
        )
        current_site = (
            pages_observation.get("site")
            if isinstance(pages_observation.get("site"), dict)
            else {}
        )
        steps.append(
            {
                "step": "configure_pages_site",
                "status": (
                    "succeeded"
                    if (
                        current_site.get("site_key") == pages_options.get("site_key")
                        and (
                            "public_alias_enabled" not in pages_options
                            or bool(
                                (
                                    current_site.get("public_alias")
                                    if isinstance(
                                        current_site.get("public_alias"), dict
                                    )
                                    else {}
                                ).get("enabled")
                            )
                            == bool(pages_options.get("public_alias_enabled"))
                        )
                    )
                    else "pending"
                ),
                "effect": "stable_warehouse_os_entry",
                "site_key": pages_options["site_key"],
                "public_alias_enabled": pages_options.get("public_alias_enabled"),
            }
        )
    if resources:
        steps.append(
            {
                "step": "apply_hosting_resources",
                "status": "pending",
                "effect": "bounded_infrastructure_mutation",
                "resource_count": len(resources),
            }
        )
    if wants_ready:
        steps.extend(
            [
                {
                    "step": "verify_storage",
                    "status": "pending",
                    "effect": "write_probe_only",
                },
                {
                    "step": "resolve_verified_source",
                    "status": (
                        "pending"
                        if source_count or repository_supplies_source
                        else "input_required"
                    ),
                    "effect": "read",
                },
                {
                    "step": "detect_and_configure_runtime",
                    "status": (
                        "pending"
                        if source_count or repository_supplies_source
                        else "blocked_by_source"
                    ),
                    "effect": "configuration",
                },
                {
                    "step": "request_deployment",
                    "status": (
                        "pending"
                        if source_count or repository_supplies_source
                        else "blocked_by_source"
                    ),
                    "effect": "reversible_deployment",
                },
                {
                    "step": "verify_and_activate",
                    "status": (
                        "pending"
                        if source_count or repository_supplies_source
                        else "blocked_by_source"
                    ),
                    "effect": "traffic_switch_to_healthy_only",
                },
            ]
        )
    return {
        "schema": "warehouse.hosting-plan.v2",
        "decision_owner": "hosting_runtime",
        "workflow_prescribed": False,
        "blocked": observation_diagnostic is not None,
        "diagnosis": observation_diagnostic,
        "source_available": source_count > 0 or repository_supplies_source,
        "steps": steps,
        "required_input": (
            None
            if not wants_ready or source_count
            else (
                {
                    "kind": "authorization_scope",
                    "required": ["deploy:read"],
                    "message": "Issue or use a workspace key with deploy:read.",
                }
                if observation_diagnostic is not None
                else {
                    "kind": "source_archive",
                    "upload": assistant_manifest()["conversation"]["source_upload"],
                    "accepted": ["zip", "tar", "tar.gz", "tgz"],
                }
            )
        ),
    }


def _planned_status(desired_state: dict[str, object], plan: dict[str, object]) -> tuple[str, str]:
    if plan.get("blocked"):
        diagnosis = plan.get("diagnosis")
        stage = str(diagnosis.get("stage")) if isinstance(diagnosis, dict) else "observe"
        return "blocked", stage
    if _wants_ready(desired_state) and not plan["source_available"]:
        return "awaiting_source", "source"
    return "planning", "plan"


def _update_session(
    tenant_id: UUID,
    session_id: UUID,
    *,
    status_value: str,
    stage: str,
    desired_state: dict[str, object] | None = None,
    plan: dict[str, object] | None = None,
    state: dict[str, object] | None = None,
    diagnosis: dict[str, object] | None = None,
    last_message: str | None = None,
    completed: bool = False,
) -> None:
    assignments = [
        "status=:status",
        "current_stage=:stage",
        "revision=revision+1",
    ]
    values: dict[str, object] = {
        "id": session_id,
        "status": status_value,
        "stage": stage,
    }
    for field, value in (
        ("desired_state", desired_state),
        ("plan", plan),
        ("state", state),
        ("diagnosis", diagnosis),
    ):
        if value is not None:
            assignments.append(f"{field}=CAST(:{field} AS jsonb)")
            values[field] = json.dumps(value, ensure_ascii=False, default=str)
    if last_message is not None:
        assignments.append("last_message=:last_message")
        values["last_message"] = last_message
    if completed:
        assignments.append("completed_at=now()")
    with tenant_session(tenant_id) as session:
        session.execute(
            text(
                "UPDATE digital_asset.hosting_agent_sessions SET "
                + ", ".join(assignments)
                + " WHERE id=:id"
            ),
            values,
        )


def create_session(
    principal: HostingPrincipal,
    credential: WorkspaceCredential,
    payload: dict[str, object],
) -> dict[str, object]:
    credential.require("workspace:read")
    if credential.tenant_id != principal.tenant_id:
        raise HTTPException(status_code=403, detail="Cross-tenant hosting is forbidden")
    goal = str(payload.get("message") or payload.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=422, detail="message is required")
    if len(goal) > 16_384:
        raise HTTPException(status_code=422, detail="message is too long")
    desired_state = _merge_desired_state({}, payload.get("desired_state"))
    session_id = uuid4()
    snapshot = observe_workspace(credential)
    plan = _plan(desired_state, snapshot)
    status_value, initial_stage = _planned_status(desired_state, plan)
    with tenant_session(principal.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO digital_asset.hosting_agent_sessions(
                  id, tenant_id, workspace_id, actor_user_id, credential_id,
                  auth_kind, client_kind, goal, last_message, status,
                  current_stage, desired_state, plan, state, authorization_scope
                ) VALUES (
                  :id, :tenant_id, :workspace_id, :actor_user_id, :credential_id,
                  :auth_kind, :client_kind, :goal, :goal, :status, :stage,
                  CAST(:desired_state AS jsonb), CAST(:plan AS jsonb),
                  CAST(:state AS jsonb), CAST(:authorization_scope AS jsonb)
                )
                """
            ),
            {
                "id": session_id,
                "tenant_id": principal.tenant_id,
                "workspace_id": credential.workspace_id,
                "actor_user_id": principal.actor_user_id,
                "credential_id": credential.credential_id,
                "auth_kind": principal.auth_kind,
                "client_kind": _client_kind(payload.get("client_kind")),
                "goal": goal,
                "status": status_value,
                "stage": initial_stage,
                "desired_state": json.dumps(desired_state, ensure_ascii=False),
                "plan": json.dumps(plan, ensure_ascii=False, default=str),
                "state": json.dumps(snapshot, ensure_ascii=False, default=str),
                "authorization_scope": json.dumps(
                    {
                        "tenant_id": str(principal.tenant_id),
                        "workspace_id": str(credential.workspace_id),
                        "credential_scopes": sorted(credential.scopes),
                        "effects": "bounded_by_desired_state_and_key_scopes",
                    },
                    ensure_ascii=False,
                ),
            },
        )
    _event(
        principal.tenant_id,
        session_id,
        "understood",
        "understand",
        "succeeded",
        {"goal": goal, "desired_state": desired_state},
    )
    _event(
        principal.tenant_id,
        session_id,
        "observed",
        "observe",
        "succeeded",
        snapshot,
    )
    _event(
        principal.tenant_id,
        session_id,
        "plan",
        "plan",
        status_value,
        plan,
    )
    if status_value in {"awaiting_source", "blocked"}:
        _event(
            principal.tenant_id,
            session_id,
            "input_required",
            initial_stage,
            status_value,
            dict(plan["required_input"] or {}),
        )
    return get_session(principal, session_id, refresh=False)


def failure_diagnostic(stage: str, exc: HTTPException | Exception) -> dict[str, object]:
    http_status = exc.status_code if isinstance(exc, HTTPException) else 500
    detail: object = exc.detail if isinstance(exc, HTTPException) else str(exc)
    reason = detail.get("reason") if isinstance(detail, dict) else None
    codes = {
        401: "AUTHENTICATION_REJECTED",
        403: "AUTHORIZATION_SCOPE_MISSING",
        404: "HOSTING_TARGET_NOT_FOUND",
        409: "HOSTING_STATE_CONFLICT",
        422: "HOSTING_CONTRACT_INVALID",
        500: "HOSTING_INTERNAL_FAILURE",
        502: "RUNTIME_UPSTREAM_UNAVAILABLE",
        503: "HOSTING_DEPENDENCY_UNAVAILABLE",
        507: "WORKSPACE_QUOTA_EXHAUSTED",
    }
    error_code = str(reason or codes.get(http_status, "HOSTING_OPERATION_FAILED")).upper()
    error_code = re.sub(r"[^A-Z0-9_]+", "_", error_code).strip("_")
    return {
        "schema": "warehouse.hosting-diagnostic.v2",
        "status": "blocked" if http_status < 500 else "failed",
        "stage": stage,
        "component": stage.split(".", 1)[0],
        "error_code": error_code,
        "http_status": http_status,
        "detail": _json_safe(detail),
        "resumable": http_status not in {401, 403},
        "next_action": (
            "Correct the supplied intent or missing resource, then send another message "
            "to the same session."
            if http_status < 500
            else "Inspect the named dependency and retry the same session after repair."
        ),
        "failed_at": datetime.now(UTC).isoformat(),
    }


def _latest_deployment(snapshot: dict[str, object]) -> dict[str, object] | None:
    payload = snapshot.get("deployments")
    if not isinstance(payload, dict) or not payload.get("ok"):
        return None
    rows = payload.get("deployments")
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        return None
    return dict(rows[0])


def _refresh_state(
    principal: HostingPrincipal,
    row: dict[str, object],
    credential: WorkspaceCredential,
) -> dict[str, object]:
    snapshot = observe_workspace(credential)
    previous_state = row.get("state") if isinstance(row.get("state"), dict) else {}
    if "execution" in previous_state:
        snapshot["execution"] = previous_state["execution"]
    desired_state = dict(row.get("desired_state") or {})
    plan = _plan(desired_state, snapshot)
    latest = _latest_deployment(snapshot)
    status_value = str(row["status"])
    stage = str(row["current_stage"])
    diagnosis = row.get("diagnosis") if isinstance(row.get("diagnosis"), dict) else None
    completed = False
    if _wants_ready(desired_state):
        if plan.get("blocked"):
            status_value, stage = _planned_status(desired_state, plan)
            if isinstance(plan.get("diagnosis"), dict):
                diagnosis = dict(plan["diagnosis"])
        elif not plan["source_available"]:
            status_value, stage = "awaiting_source", "source"
        elif (
            latest is not None
            and latest.get("status") == "ready"
            and latest.get("health") == "healthy"
        ):
            deployment_ref = latest.get("uuid") or latest.get("id")
            workspace_observation = (
                snapshot.get("workspace")
                if isinstance(snapshot.get("workspace"), dict)
                else {}
            )
            already_active = bool(
                deployment_ref
                and str(workspace_observation.get("active_deployment_id") or "")
                == str(deployment_ref)
            )
            pages_observation = (
                snapshot.get("pages") if isinstance(snapshot.get("pages"), dict) else {}
            )
            pages_site = (
                pages_observation.get("site")
                if isinstance(pages_observation.get("site"), dict)
                else {}
            )
            deployment_options = (
                desired_state.get("deployment")
                if isinstance(desired_state.get("deployment"), dict)
                else {}
            )
            runtime_options = (
                desired_state.get("runtime")
                if isinstance(desired_state.get("runtime"), dict)
                else {}
            )
            if (
                str(runtime_options.get("type") or "").lower() != "job"
                and deployment_options.get("activate_when_healthy", True)
                and not already_active
            ):
                activate_workspace_deployment(credential, UUID(str(deployment_ref)))
            status_value, stage, completed = "completed", "ready", True
            diagnosis = None
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "ready",
                "ready",
                "completed",
                {
                    "deployment_id": str(deployment_ref),
                    "application_url": pages_site.get("url")
                    or latest.get("verified_application_url")
                    or latest.get("public_url"),
                    "health": "healthy",
                },
            )
        elif latest is not None and latest.get("status") in {"failed", "cancelled"}:
            result = latest.get("result") if isinstance(latest.get("result"), dict) else {}
            diagnostic_detail = result.get("error") or result.get("detail") or result or latest
            diagnostic_exc = HTTPException(status_code=500, detail=diagnostic_detail)
            diagnosis = failure_diagnostic("runtime.deployment", diagnostic_exc)
            status_value, stage = "failed", "runtime.deployment"
        elif latest is not None:
            status_value, stage = "running", "runtime.deployment"
        else:
            status_value, stage = "planning", "plan"
    _update_session(
        principal.tenant_id,
        UUID(str(row["id"])),
        status_value=status_value,
        stage=stage,
        plan=plan,
        state=snapshot,
        diagnosis=diagnosis,
        completed=completed,
    )
    return _row(principal.tenant_id, row["id"])


def get_session(
    principal: HostingPrincipal, session_id: object, *, refresh: bool = True
) -> dict[str, object]:
    row = _row(principal.tenant_id, session_id)
    credential = _credential_for_session(principal, row)
    if refresh and str(row["status"]) not in SESSION_TERMINAL_STATUSES:
        row = _refresh_state(principal, row, credential)
    public = _json_safe(row)
    public["assistant_kit"] = assistant_manifest()["downloads"]
    public["links"] = {
        "self": f"/api/hosting/v2/sessions/{row['id']}",
        "events": f"/api/hosting/v2/sessions/{row['id']}/events",
        "source": f"/api/hosting/v2/sessions/{row['id']}/sources",
        "source_uploads": f"/api/hosting/v2/sessions/{row['id']}/source-uploads",
        "source_attach": f"/api/hosting/v2/sessions/{row['id']}/sources/attach",
        "messages": f"/api/hosting/v2/sessions/{row['id']}/messages",
        "pages": f"/api/hosting/v2/sessions/{row['id']}/pages",
        "pages_design": f"/api/hosting/v2/sessions/{row['id']}/pages/design",
    }
    return {"ok": True, "session": public}


def _apply_desired_resources(
    principal: HostingPrincipal,
    session_id: UUID,
    credential: WorkspaceCredential,
    desired_state: dict[str, object],
    settings: Settings,
) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    resources = (
        desired_state.get("resources") if isinstance(desired_state.get("resources"), list) else []
    )
    results: list[dict[str, object]] = []
    for index, item in enumerate(resources):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "").lower()
        required = item.get("required") is not False
        if kind == "secret":
            diagnosis = failure_diagnostic(
                "fabric.secret",
                HTTPException(
                    status_code=422,
                    detail={
                        "reason": "secret_value_required_out_of_band",
                        "endpoint": "/api/workspaces/v1/fabric/resources",
                        "plaintext_retained_in_conversation": False,
                    },
                ),
            )
            if required:
                return results, diagnosis
            results.append({"ok": False, "kind": kind, "diagnosis": diagnosis})
            continue
        _event(
            principal.tenant_id,
            session_id,
            "step_started",
            f"fabric.{kind}",
            "running",
            {"resource_key": item.get("resource_key")},
        )
        try:
            resource_digest = hashlib.sha256(
                json.dumps(item, sort_keys=True, default=str).encode()
            ).hexdigest()[:16]
            result = apply_fabric_resource(
                credential,
                {
                    "kind": kind,
                    "resource_key": item.get("resource_key"),
                    "spec": item.get("spec") or {},
                    "execute": True,
                },
                settings,
                idempotency_key=(f"hosting-session-{session_id}-{index}-{resource_digest}"),
            )
        except Exception as exc:
            diagnosis = failure_diagnostic(f"fabric.{kind}", exc)
            _event(
                principal.tenant_id,
                session_id,
                "step_failed",
                f"fabric.{kind}",
                str(diagnosis["status"]),
                diagnosis,
            )
            if required:
                return results, diagnosis
            results.append({"ok": False, "kind": kind, "diagnosis": diagnosis})
            continue
        results.append(result)
        _event(
            principal.tenant_id,
            session_id,
            "step_succeeded" if result.get("ok") else "step_failed",
            f"fabric.{kind}",
            "succeeded" if result.get("ok") else "blocked",
            result,
        )
        if not result.get("ok") and required:
            diagnosis = (
                dict(result["diagnosis"])
                if isinstance(result.get("diagnosis"), dict)
                else failure_diagnostic(
                    f"fabric.{kind}",
                    HTTPException(status_code=409, detail="Hosting resource is blocked"),
                )
            )
            return results, diagnosis
    return results, None


def execute_message(
    principal: HostingPrincipal,
    session_id: object,
    payload: dict[str, object],
    settings: Settings,
) -> dict[str, object]:
    row = _row(principal.tenant_id, session_id)
    credential = _credential_for_session(principal, row)
    if str(row["status"]) in SESSION_TERMINAL_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="This hosting session is terminal; create a new session",
        )
    message = str(payload.get("message") or "").strip()
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    if len(message) > 16_384:
        raise HTTPException(status_code=422, detail="message is too long")
    desired_state = _merge_desired_state(
        dict(row.get("desired_state") or {}), payload.get("desired_state")
    )
    snapshot = observe_workspace(credential)
    plan = _plan(desired_state, snapshot)
    planned_status, planned_stage = _planned_status(desired_state, plan)
    _update_session(
        principal.tenant_id,
        UUID(str(row["id"])),
        status_value=planned_status,
        stage=planned_stage,
        desired_state=desired_state,
        plan=plan,
        state=snapshot,
        last_message=message,
    )
    _event(
        principal.tenant_id,
        UUID(str(row["id"])),
        "message",
        "understand",
        "succeeded",
        {"message": message, "desired_state": desired_state},
    )
    if not bool(payload.get("execute")):
        return get_session(principal, row["id"], refresh=False)
    resource_results, resource_diagnosis = _apply_desired_resources(
        principal,
        UUID(str(row["id"])),
        credential,
        desired_state,
        settings,
    )
    if resource_diagnosis is not None:
        failed_status = str(resource_diagnosis.get("status") or "blocked")
        _update_session(
            principal.tenant_id,
            UUID(str(row["id"])),
            status_value=failed_status,
            stage=str(resource_diagnosis.get("stage") or "fabric"),
            state={**snapshot, "fabric_execution": resource_results},
            diagnosis=resource_diagnosis,
        )
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "diagnosis",
            str(resource_diagnosis.get("stage") or "fabric"),
            failed_status,
            resource_diagnosis,
        )
        return get_session(principal, row["id"], refresh=False)
    if resource_results:
        snapshot = observe_workspace(credential)
        snapshot["fabric_execution"] = resource_results
        plan = _plan(desired_state, snapshot)
        _update_session(
            principal.tenant_id,
            UUID(str(row["id"])),
            status_value="planning",
            stage="plan",
            plan=plan,
            state=snapshot,
            diagnosis={},
        )
    pages_options = (
        desired_state.get("pages") if isinstance(desired_state.get("pages"), dict) else {}
    )
    if pages_options.get("site_key"):
        try:
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "step_started",
                "pages.configure",
                "running",
                {"site_key": pages_options["site_key"]},
            )
            pages_result = configure_pages_site(credential, pages_options, settings)
            snapshot["pages"] = pages_result
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "step_succeeded",
                "pages.configure",
                "succeeded",
                pages_result,
            )
        except Exception as exc:
            diagnostic = failure_diagnostic("pages.configure", exc)
            _update_session(
                principal.tenant_id,
                UUID(str(row["id"])),
                status_value=str(diagnostic["status"]),
                stage="pages.configure",
                state=snapshot,
                diagnosis=diagnostic,
            )
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "diagnosis",
                "pages.configure",
                str(diagnostic["status"]),
                diagnostic,
            )
            return get_session(principal, row["id"], refresh=False)
    if not _wants_ready(desired_state):
        if pages_options.get("site_key"):
            _update_session(
                principal.tenant_id,
                UUID(str(row["id"])),
                status_value="completed",
                stage="pages.ready",
                state=snapshot,
                diagnosis={},
                completed=True,
            )
            return get_session(principal, row["id"], refresh=False)
        return get_session(principal, row["id"], refresh=True)
    if plan.get("blocked"):
        diagnostic = dict(plan.get("diagnosis") or {})
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "diagnosis",
            str(diagnostic.get("stage") or "observe"),
            "blocked",
            diagnostic,
        )
        return get_session(principal, row["id"], refresh=False)
    if not plan["source_available"]:
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "input_required",
            "source",
            "awaiting_source",
            dict(plan["required_input"] or {}),
        )
        return get_session(principal, row["id"], refresh=False)

    try:
        storage_options = (
            desired_state.get("storage") if isinstance(desired_state.get("storage"), dict) else {}
        )
        if storage_options.get("verify", True):
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "step_started",
                "storage.probe",
                "running",
                {},
            )
            storage_result = probe_workspace_storage(credential, settings)
            _event(
                principal.tenant_id,
                UUID(str(row["id"])),
                "step_succeeded",
                "storage.probe",
                "succeeded",
                storage_result,
            )
        source_rows = snapshot["sources"].get("sources", [])
        latest_source = source_rows[0]
        source_ref = latest_source.get("uuid") or latest_source.get("id")
        runtime_options = (
            desired_state.get("runtime") if isinstance(desired_state.get("runtime"), dict) else {}
        )
        deployment_options = (
            desired_state.get("deployment")
            if isinstance(desired_state.get("deployment"), dict)
            else {}
        )
        runtime_type = str(runtime_options.get("type") or "auto").strip().lower()
        activate_when_healthy = bool(deployment_options.get("activate_when_healthy", True))
        if runtime_type == "job":
            activate_when_healthy = False
        runtime_payload = {
            key: value
            for key, value in {
                "runtime_type": runtime_type,
                "runtime": runtime_options.get("runtime"),
                "runtime_profile": runtime_options.get("profile"),
                "component": runtime_options.get("component"),
                "source_version_id": source_ref,
                "entrypoint": runtime_options.get("entrypoint"),
                "build_command": runtime_options.get("build_command"),
                "start_command": runtime_options.get("start_command"),
                "health_path": runtime_options.get("health_path"),
                "image": runtime_options.get("image"),
                "dockerfile": runtime_options.get("dockerfile"),
                "compose_file": runtime_options.get("compose_file"),
                "route_service": runtime_options.get("route_service"),
                "port": runtime_options.get("port"),
                "command": runtime_options.get("command"),
                "database_url_env": runtime_options.get("database_url_env"),
                "timeout_seconds": runtime_options.get("timeout_seconds"),
                "execution_mode": "job" if runtime_type == "job" else "service",
                "activate": activate_when_healthy,
                "deploy": True,
                "idempotency_key": (
                    f"hosting-{row['id']}-{source_ref}-{runtime_options.get('type') or 'auto'}"
                ),
            }.items()
            if value is not None
        }
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "step_started",
            "runtime.configure",
            "running",
            {"intent": runtime_payload},
        )
        runtime_result = configure_workspace_runtime(credential, runtime_payload, settings)
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "step_succeeded",
            "runtime.configure",
            "succeeded",
            runtime_result,
        )
        _update_session(
            principal.tenant_id,
            UUID(str(row["id"])),
            status_value="running",
            stage="runtime.deployment",
            state={**snapshot, "execution": runtime_result},
            diagnosis={},
        )
    except Exception as exc:
        diagnostic = failure_diagnostic("hosting.execute", exc)
        failed_status = str(diagnostic["status"])
        _update_session(
            principal.tenant_id,
            UUID(str(row["id"])),
            status_value=failed_status,
            stage=str(diagnostic["stage"]),
            diagnosis=diagnostic,
        )
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "diagnosis",
            str(diagnostic["stage"]),
            failed_status,
            diagnostic,
        )
    return get_session(principal, row["id"], refresh=True)


def list_events(
    principal: HostingPrincipal, session_id: object, *, after: int = 0
) -> dict[str, object]:
    row = _row(principal.tenant_id, session_id)
    _assert_principal_session(principal, row)
    with tenant_session(principal.tenant_id) as session:
        events = [
            _json_safe(dict(item))
            for item in session.execute(
                text(
                    """
                    SELECT * FROM digital_asset.hosting_agent_events
                    WHERE session_id=:session_id AND sequence>:after
                    ORDER BY sequence LIMIT 500
                    """
                ),
                {"session_id": row["id"], "after": max(0, int(after))},
            )
            .mappings()
            .all()
        ]
    return {"ok": True, "session_id": str(row["id"]), "events": events, "count": len(events)}


def cancel_session(principal: HostingPrincipal, session_id: object) -> dict[str, object]:
    row = _row(principal.tenant_id, session_id)
    _assert_principal_session(principal, row)
    if str(row["status"]) not in SESSION_TERMINAL_STATUSES:
        _update_session(
            principal.tenant_id,
            UUID(str(row["id"])),
            status_value="cancelled",
            stage="cancelled",
            completed=True,
        )
        _event(
            principal.tenant_id,
            UUID(str(row["id"])),
            "cancelled",
            "cancelled",
            "cancelled",
            {"note": "The conversation stopped; an already queued deployment is unchanged."},
        )
    return get_session(principal, row["id"], refresh=False)


def session_credential(
    principal: HostingPrincipal, session_id: object
) -> tuple[dict[str, object], WorkspaceCredential]:
    row = _row(principal.tenant_id, session_id)
    return row, _credential_for_session(principal, row)


def record_session_diagnostic(
    principal: HostingPrincipal,
    session_id: object,
    stage: str,
    exc: HTTPException | Exception,
) -> dict[str, object]:
    """Persist an exact, resumable failure for terminal AIs and the secretary."""

    row = _row(principal.tenant_id, session_id)
    _assert_principal_session(principal, row)
    diagnosis = failure_diagnostic(stage, exc)
    status_value = str(diagnosis["status"])
    _update_session(
        principal.tenant_id,
        UUID(str(row["id"])),
        status_value=status_value,
        stage=stage,
        diagnosis=diagnosis,
    )
    _event(
        principal.tenant_id,
        UUID(str(row["id"])),
        "diagnosis",
        stage,
        status_value,
        diagnosis,
    )
    return diagnosis


def record_source_attached(
    principal: HostingPrincipal,
    session_id: object,
    source: dict[str, object],
) -> dict[str, object]:
    """Attach immutable source evidence to the durable hosting conversation."""

    row = _row(principal.tenant_id, session_id)
    _assert_principal_session(principal, row)
    _event(
        principal.tenant_id,
        UUID(str(row["id"])),
        "source_attached",
        "source.upload",
        "succeeded",
        source,
    )
    return get_session(principal, row["id"], refresh=True)
