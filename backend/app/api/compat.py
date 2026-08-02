"""Compatibility API for the retained Warehouse OS 2.0 frontend.

The 2.1 repository intentionally preserved the browser contract while the
PostgreSQL backend is rebuilt module by module.  This router has two jobs:

* expose real PostgreSQL-backed projections where 2.1 already has durable
  tables (tasks, workflows, audit, secretary conversations and IAM); and
* expose an explicit tenant-isolated compatibility projection for legacy
  read models that have not yet received their final domain schema.

Missing compatibility documents return truthful connected-empty states.  They
never inject demonstration data or report a successful business operation that
did not happen; ``empty=true`` distinguishes an available API with no records
from an unavailable service.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import ActorContext, current_actor
from app.db.session import database_is_available, tenant_session
from app.services.auto_runtime import runtime_capability_map
from app.services.digital_asset_hosting import (
    asset_summary as native_digital_asset_summary,
)
from app.services.digital_asset_hosting import (
    list_assets as native_digital_assets,
)
from app.services.task_center import (
    create_task,
    get_task,
    list_tasks,
    task_history,
    task_meta,
    update_task,
    update_task_status,
)
from app.services.warehouse_operations import alerts_by_item

router = APIRouter(tags=["frontend-compatibility"])


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    return value


def _limit(value: int, maximum: int = 1000) -> int:
    return max(1, min(int(value), maximum))


def _unavailable(module: str, **payload: object) -> dict[str, object]:
    return {
        "available": False,
        "status": "not_migrated",
        "reason": f"{module}_not_migrated",
        **payload,
    }


def _document(
    session: Session,
    namespace: str,
    document_key: str = "default",
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT payload
                FROM compatibility.documents
                WHERE namespace = :namespace
                  AND document_key = :document_key
                  AND status = 'active'
                """
            ),
            {"namespace": namespace, "document_key": document_key},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    value = row["payload"]
    return dict(value) if isinstance(value, dict) else {"value": value}


def _documents(
    session: Session,
    namespace: str,
    *,
    limit: int = 100,
    status_filter: str | None = None,
) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text(
                """
                SELECT id, document_key, status, payload, source, version,
                       created_at, updated_at
                FROM compatibility.documents
                WHERE namespace = :namespace
                  AND (
                    CAST(:status_filter AS text) IS NULL
                    OR payload->>'status' = CAST(:status_filter AS text)
                  )
                ORDER BY updated_at DESC, document_key
                LIMIT :limit
                """
            ),
            {
                "namespace": namespace,
                "status_filter": status_filter,
                "limit": _limit(limit),
            },
        )
        .mappings()
        .all()
    )
    output: list[dict[str, object]] = []
    for row in rows:
        payload = (
            dict(row["payload"]) if isinstance(row["payload"], dict) else {"value": row["payload"]}
        )
        payload.setdefault("id", str(row["id"]))
        payload.setdefault("document_key", row["document_key"])
        payload.setdefault("source", row["source"])
        payload.setdefault("version", int(row["version"]))
        payload.setdefault("created_at", row["created_at"])
        payload.setdefault("updated_at", row["updated_at"])
        output.append(_json_safe(payload))
    return output


def _audit(
    session: Session,
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


def _require_admin(actor: ActorContext, *permission_keys: str) -> None:
    if actor.role_level >= 10 or any(key in actor.permissions for key in permission_keys):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")


def _upsert_document(
    actor: ActorContext,
    namespace: str,
    payload: dict[str, object],
    *,
    document_key: str = "default",
    source: str = "native",
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                    INSERT INTO compatibility.documents(
                      id, tenant_id, namespace, document_key, payload, source, updated_by
                    ) VALUES (
                      :id, :tenant_id, :namespace, :document_key,
                      CAST(:payload AS jsonb), :source, :updated_by
                    )
                    ON CONFLICT (tenant_id, namespace, document_key)
                    DO UPDATE SET
                      payload = EXCLUDED.payload,
                      source = EXCLUDED.source,
                      status = 'active',
                      version = compatibility.documents.version + 1,
                      updated_by = EXCLUDED.updated_by
                    RETURNING id, document_key, payload, source, version, created_at, updated_at
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "namespace": namespace,
                    "document_key": document_key,
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                    "source": source,
                    "updated_by": actor.user_id,
                },
            )
            .mappings()
            .one()
        )
        _audit(
            session,
            actor,
            "compatibility.document.upserted",
            {"namespace": namespace, "document_key": document_key, "version": row["version"]},
        )
        return _json_safe(
            {
                "id": row["id"],
                "document_key": row["document_key"],
                "payload": row["payload"],
                "source": row["source"],
                "version": row["version"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )


def _sum(rows: Iterable[dict[str, object]], key: str) -> float:
    total = 0.0
    for row in rows:
        value = row.get(key)
        try:
            total += float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            continue
    return total


def _integration_payload(
    actor: ActorContext,
    provider: str,
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        payload = _document(session, f"integration.{provider}")
    if payload is None:
        return _unavailable(
            f"integration_{provider}",
            provider=provider,
            configured=False,
            enabled=False,
            secret_ref=None,
        )
    protected = {
        key: value
        for key, value in payload.items()
        if not any(token in key.lower() for token in ("api_key", "secret", "password", "token"))
        or key == "secret_ref"
    }
    protected.setdefault("provider", provider)
    protected.setdefault(
        "configured", bool(protected.get("secret_ref") or protected.get("enabled"))
    )
    protected.setdefault("available", True)
    return _json_safe(protected)


# Task center: final PostgreSQL tables already exist.


@router.get("/api/tasks/meta")
def tasks_meta(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return task_meta(actor)


@router.get("/api/tasks")
def tasks(
    scope: str = Query(default="mine"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return list_tasks(actor, scope=scope)


@router.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def tasks_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return create_task(actor, payload)


@router.get("/api/tasks/{task_id}")
def tasks_show(
    task_id: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return get_task(actor, task_id)


@router.get("/api/tasks/{task_id}/history")
def tasks_history(
    task_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    before_id: int | None = Query(default=None, ge=1),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return task_history(actor, task_id, limit=limit, before_id=before_id)


@router.patch("/api/tasks/{task_id}")
@router.post("/api/tasks/{task_id}/update")
def tasks_update(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return update_task(actor, task_id, payload)


@router.patch("/api/tasks/{task_id}/status")
@router.post("/api/tasks/{task_id}/status")
def tasks_status(
    task_id: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return update_task_status(actor, task_id, payload)


# Tenant shell: branding, preferences, navigation and permissions.


@router.get("/api/company/branding")
def company_branding(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "company.branding")
    base: dict[str, object] = {
        "available": True,
        "company_name": actor.tenant_name,
        "name": actor.tenant_name,
        "tenant_slug": actor.tenant_slug,
        "logo_url": None,
        "mark_url": None,
        "accent_color": None,
    }
    if stored:
        base.update(stored)
    base["branding"] = {key: value for key, value in base.items() if key != "branding"}
    return _json_safe(base)


@router.put("/api/company/branding")
@router.patch("/api/company/branding")
def company_branding_update(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_admin(actor, "company.settings", "company.branding")
    return _upsert_document(actor, "company.branding", payload)


@router.get("/api/runtime/preferences")
def runtime_preferences(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    defaults: dict[str, object] = {
        "language": "zh-CN",
        "appearance": "system",
        "density": "comfortable",
        "poll_interval_seconds": 30,
        "reduce_motion": False,
    }
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "runtime.preferences")
    if stored:
        defaults.update(stored)
    return {"available": True, "preferences": defaults, **defaults}


@router.put("/api/runtime/preferences")
@router.patch("/api/runtime/preferences")
def runtime_preferences_update(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    result = _upsert_document(actor, "runtime.preferences", payload)
    return {"ok": True, **result}


@router.get("/api/settings")
def settings_read(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "settings")
    if stored is None:
        return _unavailable("settings", settings={})
    public = _json_safe(stored)
    return {"available": True, "settings": public, **public}


@router.put("/api/settings")
@router.patch("/api/settings")
def settings_update(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_admin(actor, "company.settings")
    return _upsert_document(actor, "settings", payload)


@router.get("/api/permissions")
def permissions(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    identities = [
        {
            "position_code": identity.position_code,
            "name": identity.name,
            "role_level": identity.role_level,
            "appointment_type": identity.appointment_type,
        }
        for identity in actor.identities
    ]
    values = sorted(actor.permissions)
    return {
        "available": True,
        "permissions": values,
        "keys": values,
        "role_level": actor.role_level,
        "topology_level": actor.topology_level,
        "topology_title": actor.topology_title,
        "identities": identities,
    }


@router.get("/api/nav")
def navigation(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        override = (
            session.execute(
                text(
                    """
                    SELECT allow_modules, deny_modules
                    FROM iam.membership_navigation_overrides
                    WHERE user_id = :user_id
                    """
                ),
                {"user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        defaults = (
            session.execute(
                text(
                    """
                    SELECT pnp.navigation_default
                    FROM iam.membership_positions AS mp
                    JOIN iam.position_profiles AS pp
                      ON pp.tenant_id = mp.tenant_id
                     AND pp.position_code = mp.position_code
                    LEFT JOIN iam.position_navigation_policies AS pnp
                      ON pnp.tenant_id = pp.tenant_id
                     AND pnp.position_id = pp.id
                    WHERE mp.user_id = :user_id
                      AND mp.active
                      AND pp.active
                      AND COALESCE(pnp.navigation_default_enabled, false)
                    """
                ),
                {"user_id": actor.user_id},
            )
            .scalars()
            .all()
        )
        stored = _document(session, "navigation")
    allow: set[str] = set()
    for value in defaults:
        if isinstance(value, list):
            allow.update(str(item) for item in value if str(item).strip())
    deny: set[str] = set()
    if override is not None:
        allow.update(str(item) for item in (override["allow_modules"] or []))
        deny.update(str(item) for item in (override["deny_modules"] or []))
    modules = sorted(allow.difference(deny))
    result: dict[str, object] = {
        "available": True,
        "items": {},
        "modules": modules,
        "allow_modules": sorted(allow),
        "deny_modules": sorted(deny),
        "unrestricted": not allow,
    }
    if stored:
        result.update(stored)
    return _json_safe(result)


# Integrations, AI shell and voice.


@router.get("/api/integrations/{provider}")
def integration(
    provider: str,
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    if provider not in {"tavily", "vision", "voice", "deepseek"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown integration")
    return _integration_payload(actor, provider)


@router.put("/api/integrations/{provider}")
@router.patch("/api/integrations/{provider}")
def integration_update(
    provider: str,
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    if provider not in {"tavily", "vision", "voice", "deepseek"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown integration")
    _require_admin(actor, "integrations.manage", "company.settings")
    forbidden = [
        key
        for key in payload
        if any(token in key.lower() for token in ("api_key", "secret", "password", "token"))
        and key != "secret_ref"
    ]
    if forbidden:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Store integration credentials in a secret manager and send only secret_ref",
        )
    return _upsert_document(actor, f"integration.{provider}", payload)


@router.get("/api/voice/status")
def voice_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    payload = _integration_payload(actor, "voice")
    configured = bool(payload.get("configured") or payload.get("enabled"))
    return {
        **payload,
        "status": "ready" if configured else "not_configured",
        "available": configured,
        "configured": configured,
    }


@router.get("/api/ai/health")
def ai_health(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    provider = _integration_payload(actor, "deepseek")
    database_ready = database_is_available()
    configured = bool(provider.get("configured"))
    return {
        "status": "ok" if database_ready and configured else "degraded",
        "database": "ready" if database_ready else "unavailable",
        "provider_configured": configured,
        "provider": provider.get("provider", "deepseek"),
        "capability_map": runtime_capability_map(),
    }


@router.get("/api/prompts")
def prompts(
    limit: int = Query(default=200, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "prompt", limit=limit)
    if not rows:
        return _unavailable("prompts", prompts=[], items=[])
    return {"available": True, "prompts": rows, "items": rows}


@router.get("/api/ai/conversations")
def ai_conversations(
    limit: int = Query(default=100, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, owner_user_id, channel, title, created_at, updated_at
                    FROM secretariat.conversations
                    WHERE owner_user_id = :user_id OR :can_read_all
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "user_id": actor.user_id,
                    "can_read_all": actor.role_level >= 10
                    or "secretariat.conversations.read_all" in actor.permissions,
                    "limit": _limit(limit, 500),
                },
            )
            .mappings()
            .all()
        )
    conversations = [
        _json_safe(
            {
                **dict(row),
                "id": str(row["id"]),
                "owner_user_id": str(row["owner_user_id"]),
            }
        )
        for row in rows
    ]
    return {"available": True, "conversations": conversations, "items": conversations}


@router.get("/api/assistant/bootstrap")
def assistant_bootstrap(
    message_limit: int = Query(default=80, ge=1, le=500),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return {
        "available": True,
        "tenant": {
            "id": str(actor.tenant_id),
            "slug": actor.tenant_slug,
            "name": actor.tenant_name,
        },
        "user": actor.user_payload,
        "conversations": ai_conversations(limit=100, actor=actor)["conversations"],
        "capability_map": runtime_capability_map(),
        "messages": [],
        "message_limit": message_limit,
    }


# Alerts and monitoring.


def _alert_rows(
    actor: ActorContext,
    *,
    limit: int = 1000,
    status_filter: str | None = None,
) -> list[dict[str, object]]:
    with tenant_session(actor.tenant_id) as session:
        return _documents(
            session,
            "alert",
            limit=limit,
            status_filter=status_filter,
        )


@router.get("/api/alerts")
def alerts(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=1000, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    rows = _alert_rows(actor, limit=limit, status_filter=status_filter)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "alerts": rows,
        "items": rows,
        "count": len(rows),
        "reason": None if rows else "no_records",
    }


@router.get("/api/alerts/watch")
def alerts_watch(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    rows = _alert_rows(actor, limit=200, status_filter="open")
    inventory = alerts_by_item(actor)
    cursor = max((str(row.get("updated_at") or "") for row in rows), default="")
    return {
        "available": True,
        "alerts": rows,
        "items": rows,
        "count": len(rows),
        "cursor": cursor,
        "byItem": inventory.get("byItem", {}),
    }


@router.get("/api/alerts/briefing")
def alerts_briefing(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    rows = _alert_rows(actor, limit=1000, status_filter="open")
    severities: dict[str, int] = {}
    for row in rows:
        severity = str(row.get("severity") or row.get("level") or "unknown")
        severities[severity] = severities.get(severity, 0) + 1
    return {
        "available": True,
        "alerts": rows[:20],
        "items": rows[:20],
        "open_count": len(rows),
        "by_severity": severities,
    }


# Records compatibility projection.


@router.get("/api/records/meta")
def records_meta(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "record.meta")
        rows = _documents(session, "record", limit=1000)
    types = sorted({str(row.get("type")) for row in rows if row.get("type")})
    statuses = sorted({str(row.get("status")) for row in rows if row.get("status")})
    base: dict[str, object] = {
        "available": True,
        "empty": not (stored or rows),
        "source": "compatibility",
        "types": types,
        "statuses": statuses,
        "record_types": types,
        "count": len(rows),
    }
    if stored:
        base.update(stored)
    if not stored and not rows:
        base["reason"] = "no_records"
    return _json_safe(base)


@router.post("/api/records/search")
def records_search(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    query = str(payload.get("query") or payload.get("q") or "").strip()
    record_type = str(payload.get("type") or payload.get("record_type") or "").strip() or None
    record_status = str(payload.get("status") or "").strip() or None
    limit = _limit(int(payload.get("limit") or 200), 1000)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, document_key, payload, source, version, created_at, updated_at
                    FROM compatibility.documents
                    WHERE namespace = 'record'
                      AND status = 'active'
                      AND (:query = '' OR payload::text ILIKE '%' || :query || '%')
                      AND (
                        CAST(:record_type AS text) IS NULL
                        OR payload->>'type' = CAST(:record_type AS text)
                      )
                      AND (
                        CAST(:record_status AS text) IS NULL
                        OR payload->>'status' = CAST(:record_status AS text)
                      )
                    ORDER BY updated_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "query": query,
                    "record_type": record_type,
                    "record_status": record_status,
                    "limit": limit,
                },
            )
            .mappings()
            .all()
        )
    records: list[dict[str, object]] = []
    for row in rows:
        item = (
            dict(row["payload"]) if isinstance(row["payload"], dict) else {"value": row["payload"]}
        )
        item.setdefault("id", str(row["id"]))
        item.setdefault("document_key", row["document_key"])
        item.setdefault("source", row["source"])
        item.setdefault("version", int(row["version"]))
        item.setdefault("created_at", row["created_at"])
        item.setdefault("updated_at", row["updated_at"])
        records.append(_json_safe(item))
    return {
        "available": True,
        "empty": not records,
        "source": "compatibility",
        "records": records,
        "items": records,
        "count": len(records),
        "reason": None if records else "no_matching_records",
    }


@router.post("/api/records", status_code=status.HTTP_201_CREATED)
def records_create(
    payload: dict[str, object] = Body(default={}),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    _require_admin(actor, "records.create", "records.manage")
    document_key = str(payload.get("record_no") or payload.get("id") or uuid4())
    return _upsert_document(actor, "record", payload, document_key=document_key)


# Asset compatibility projections.


@router.get("/api/assets")
def financial_assets(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "asset.financial", limit=1000)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "assets": rows,
        "items": rows,
        "reason": None if rows else "no_records",
    }


@router.get("/api/assets/portfolio")
def financial_portfolio(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "asset.portfolio")
        rows = _documents(session, "asset.financial", limit=1000)
    if stored:
        public = _json_safe(stored)
        return {"available": True, **public}
    total_cost = _sum(rows, "total_cost_cny")
    total_value = _sum(rows, "market_value_cny")
    allocation: dict[str, float] = {}
    for row in rows:
        asset_type = str(row.get("asset_type") or "other")
        try:
            value = float(row.get("market_value_cny") or 0)
        except (TypeError, ValueError):
            value = 0.0
        allocation[asset_type] = allocation.get(asset_type, 0.0) + value
    allocation_rows = [
        {
            "type": key,
            "label": key,
            "value_cny": value,
            "pct": value / total_value * 100 if total_value else 0,
        }
        for key, value in sorted(allocation.items())
    ]
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "total_cost_cny": total_cost,
        "total_value_cny": total_value,
        "unrealized_pnl_cny": total_value - total_cost,
        "day_change_cny": _sum(rows, "day_change_cny"),
        "allocation": allocation_rows,
        "reason": None if rows else "no_records",
    }


@router.get("/api/digital-assets")
def digital_assets(
    limit: int = Query(default=300, ge=1, le=1000),
    kind: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    native = native_digital_assets(
        actor,
        limit=limit,
        kind=kind,
        status_filter=status_filter,
    )
    if native["assets"]:
        return native
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "asset.digital", limit=limit)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "assets": rows,
        "items": rows,
        "reason": None if rows else "no_records",
    }


@router.get("/api/digital-assets/summary")
def digital_assets_summary(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    native = native_digital_asset_summary(actor)
    if native["assets"]:
        return native
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, "asset.digital.summary")
        assets = _documents(session, "asset.digital", limit=1000)
        listings = _documents(session, "asset.digital.listing", limit=1000)
    if stored:
        public = _json_safe(stored)
        return {"available": True, **public}
    by_kind: dict[str, int] = {}
    for row in assets:
        kind = str(row.get("asset_kind") or "other")
        by_kind[kind] = by_kind.get(kind, 0) + 1
    by_listing_status: dict[str, int] = {}
    for row in listings:
        listing_status = str(row.get("status") or "unknown")
        by_listing_status[listing_status] = by_listing_status.get(listing_status, 0) + 1
    return {
        "available": True,
        "empty": not (assets or listings),
        "source": "compatibility",
        "by_kind": [{"kind": key, "count": value} for key, value in sorted(by_kind.items())],
        "listings": [
            {"status": key, "count": value} for key, value in sorted(by_listing_status.items())
        ],
        "workspaces": sum(1 for row in assets if row.get("workspace")),
        "latest_valuation_total_cny": _sum(assets, "valuation_cny"),
        "reason": None if assets or listings else "no_records",
    }


@router.get("/api/digital-assets/listings")
def digital_asset_listings(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(
            session,
            "asset.digital.listing",
            limit=limit,
            status_filter=status_filter,
        )
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "listings": rows,
        "items": rows,
        "reason": None if rows else "no_records",
    }


@router.get("/api/digital-assets/common-market")
def digital_asset_common_market(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "asset.digital.common_listing", limit=500)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "listings": rows,
        "items": rows,
        "reason": None if rows else "no_records",
    }


@router.get("/api/digital-assets/trades")
def digital_asset_trades(
    limit: int = Query(default=50, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "asset.digital.trade", limit=limit)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "trades": rows,
        "items": rows,
        "total_amount_cny": _sum(rows, "amount_cny"),
        "pending_acceptance": sum(1 for row in rows if row.get("acceptance_status") == "pending"),
        "disputed_count": sum(1 for row in rows if row.get("acceptance_status") == "disputed"),
        "reason": None if rows else "no_records",
    }


@router.get("/api/digital-assets/revenue")
def digital_asset_revenue(
    limit: int = Query(default=50, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "asset.digital.revenue", limit=limit)
    unpaid = 0
    distributed = 0.0
    for row in rows:
        allocation = row.get("allocation")
        if isinstance(allocation, dict):
            if allocation.get("paid"):
                try:
                    distributed += float(allocation.get("total_cny") or row.get("amount_cny") or 0)
                except (TypeError, ValueError):
                    pass
            elif allocation.get("allocations"):
                unpaid += 1
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "events": rows,
        "items": rows,
        "total_distributed_cny": distributed,
        "unpaid_allocations": unpaid,
        "reason": None if rows else "no_records",
    }


# Workflow, procurement and B2B.


@router.get("/api/wf/workflows")
def workflows(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, workflow_key, name, version, definition, active,
                           created_at, updated_at
                    FROM workflow.definitions
                    WHERE active
                    ORDER BY name, workflow_key, version DESC
                    """
                )
            )
            .mappings()
            .all()
        )
    items = [
        _json_safe(
            {
                **dict(row),
                "id": str(row["id"]),
                "status": "active" if row["active"] else "inactive",
            }
        )
        for row in rows
    ]
    return {"available": True, "workflows": items, "definitions": items, "items": items}


@router.get("/api/wf/my-instances")
def workflow_instances(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT wi.id, wi.definition_id, wd.workflow_key, wd.name,
                           wi.status, wi.subject_type, wi.subject_id, wi.state,
                           wi.created_at, wi.updated_at
                    FROM workflow.instances AS wi
                    JOIN workflow.definitions AS wd
                      ON wd.tenant_id = wi.tenant_id AND wd.id = wi.definition_id
                    WHERE :can_read_all
                       OR wi.state->>'owner_user_id' = :user_id
                       OR wi.state->>'created_by' = :user_id
                       OR wi.state->>'assignee_user_id' = :user_id
                    ORDER BY wi.updated_at DESC
                    """
                ),
                {
                    "user_id": str(actor.user_id),
                    "can_read_all": actor.role_level >= 10
                    or "workflow.read_all" in actor.permissions,
                },
            )
            .mappings()
            .all()
        )
    items = [
        _json_safe(
            {
                **dict(row),
                "id": str(row["id"]),
                "definition_id": str(row["definition_id"]),
                "subject_id": str(row["subject_id"]),
            }
        )
        for row in rows
    ]
    return {"available": True, "instances": items, "items": items}


@router.get("/api/wf/inbox")
def workflow_inbox(
    scope: str = Query(default="mine"),
    domain: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "workflow.inbox", limit=500)
    if scope == "mine":
        rows = [
            row
            for row in rows
            if str(row.get("assignee_user_id") or actor.user_id) == str(actor.user_id)
        ]
    if domain:
        rows = [row for row in rows if row.get("domain") in (None, domain)]
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "tasks": rows,
        "items": rows,
        "count": len(rows),
        "reason": None if rows else "no_records",
    }


def _projection_list(
    actor: ActorContext,
    namespace: str,
    *,
    key: str,
    limit: int = 500,
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, namespace, limit=limit)
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        key: rows,
        "items": rows,
        "count": len(rows),
        "reason": None if rows else "no_records",
    }


@router.get("/api/tender/board")
def tender_board(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _projection_list(actor, "tender.board", key="board")


@router.get("/api/tender/inbox")
def tender_inbox(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _projection_list(actor, "tender.inbox", key="inbox")


@router.get("/api/tender/my-bids")
def tender_my_bids(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _projection_list(actor, "tender.bid", key="bids")


@router.get("/api/tender/market")
def tender_market(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    market = _projection_list(actor, "tender.market", key="tenders")
    market.update(
        {
            "market_scope": "warehouse_os_connected_companies",
            "external_public_sources": {
                "connected": False,
                "coverage": [],
            },
            "screening": {
                "performed": bool(market["count"]),
                "reason": (None if market["count"] else "no_connected_platform_tenders_to_screen"),
            },
        }
    )
    return market


@router.get("/api/b2b/relations")
def b2b_relations(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _projection_list(actor, "b2b.relation", key="relations")


# ERP, finance, legal and compliance read models.


def _single_projection(
    actor: ActorContext,
    namespace: str,
    *,
    document_key: str = "default",
    module: str | None = None,
    defaults: dict[str, object] | None = None,
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        stored = _document(session, namespace, document_key)
    if stored is None:
        return {
            "available": True,
            "empty": True,
            "source": "compatibility",
            "reason": "no_records",
            **(defaults or {}),
        }
    public = _json_safe(stored)
    return {"available": True, **public}


@router.get("/api/erp/overview")
def erp_overview(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _single_projection(
        actor,
        "erp.overview",
        defaults={"kpis": [], "modules": [], "attention": []},
    )


@router.get("/api/erp/gl/income")
def erp_income(
    period: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _single_projection(
        actor,
        "erp.gl.income",
        document_key=period or "default",
        defaults={"period": period, "rows": [], "items": [], "total": 0},
    )


@router.get("/api/erp/gl/cashflow")
def erp_cashflow(
    period: str | None = Query(default=None),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _single_projection(
        actor,
        "erp.gl.cashflow",
        document_key=period or "default",
        defaults={"period": period, "rows": [], "items": [], "total": 0},
    )


@router.get("/api/erp/gl/ap")
def erp_ap(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    result = _projection_list(actor, "erp.gl.ap", key="items")
    result["by_party"] = []
    return result


@router.get("/api/erp/gl/ar")
def erp_ar(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    result = _projection_list(actor, "erp.gl.ar", key="items")
    result["by_party"] = []
    return result


@router.get("/api/erp/gl/balance-sheet")
def erp_balance_sheet(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _single_projection(
        actor,
        "erp.gl.balance_sheet",
        defaults={"assets": [], "liabilities": [], "equity": [], "rows": []},
    )


@router.get("/api/erp/gl/vouchers")
def erp_vouchers(
    limit: int = Query(default=30, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    return _projection_list(actor, "erp.gl.voucher", key="vouchers", limit=limit)


@router.get("/api/erp/finance/events")
def erp_finance_events(
    statuses: str | None = Query(default=None),
    ledger_scope: str | None = Query(default=None),
    unposted: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = _documents(session, "erp.finance.event", limit=limit)
    status_values = {value.strip() for value in (statuses or "").split(",") if value.strip()}
    if status_values:
        rows = [row for row in rows if str(row.get("status")) in status_values]
    if ledger_scope:
        rows = [row for row in rows if row.get("ledger_scope") in (None, ledger_scope)]
    if unposted is not None:
        rows = [row for row in rows if bool(row.get("unposted")) is unposted]
    return {
        "available": True,
        "empty": not rows,
        "source": "compatibility",
        "events": rows,
        "items": rows,
        "count": len(rows),
        "reason": None if rows else "no_records",
    }


@router.get("/api/legal/overview")
def legal_overview(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _single_projection(
        actor,
        "legal.overview",
        defaults={"contracts": [], "seals": [], "cases": [], "attention": []},
    )


@router.get("/api/compliance/chain-check")
def compliance_chain_check(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _single_projection(
        actor,
        "compliance.chain_check",
        defaults={"checks": [], "issues": [], "passed": None},
    )


@router.get("/api/stocktake")
def stocktake(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    return _projection_list(actor, "stocktake", key="stocktakes")


# Audit projections.


def _audit_rows(
    actor: ActorContext,
    *,
    limit: int,
    cli_only: bool,
) -> list[dict[str, object]]:
    clause = "AND (event_type LIKE 'terminal.%' OR event_type LIKE 'cli.%')" if cli_only else ""
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    f"""
                    SELECT id, actor_user_id, event_type, payload, created_at
                    FROM audit.events
                    WHERE TRUE {clause}
                    ORDER BY created_at DESC, id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": _limit(limit, 1000)},
            )
            .mappings()
            .all()
        )
    return [
        _json_safe(
            {
                **dict(row),
                "actor_user_id": str(row["actor_user_id"]) if row["actor_user_id"] else None,
            }
        )
        for row in rows
    ]


@router.get("/api/audit/logs")
def audit_logs(
    limit: int = Query(default=500, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    rows = _audit_rows(actor, limit=limit, cli_only=False)
    return {"available": True, "logs": rows, "events": rows, "items": rows}


@router.get("/api/audit/cli")
def audit_cli(
    limit: int = Query(default=500, ge=1, le=1000),
    actor: ActorContext = Depends(current_actor),
) -> dict[str, object]:
    rows = _audit_rows(actor, limit=limit, cli_only=True)
    return {"available": True, "logs": rows, "events": rows, "items": rows}


@router.get("/api/compatibility/status")
def compatibility_status(actor: ActorContext = Depends(current_actor)) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT namespace, COUNT(*)::integer AS count,
                           MAX(updated_at) AS updated_at
                    FROM compatibility.documents
                    WHERE status = 'active'
                    GROUP BY namespace
                    ORDER BY namespace
                    """
                )
            )
            .mappings()
            .all()
        )
    return {
        "available": True,
        "tenant": actor.tenant_slug,
        "database": "postgresql",
        "namespaces": [_json_safe(dict(row)) for row in rows],
    }
