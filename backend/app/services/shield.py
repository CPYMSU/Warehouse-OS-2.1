"""SHIELD platform control plane backed by a restricted host agent and PostgreSQL."""

from __future__ import annotations

import json
import socket
from datetime import UTC, datetime
from time import perf_counter
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import system_session, tenant_session
from app.services.integrations import public_state

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings

SHIELD_ACTIONS = frozenset(
    {
        "healthcheck",
        "restart-api",
        "restart-firefighter",
        "reload-nginx",
        "restart-nginx",
        "clear-health-flag",
    }
)
HIGH_RISK_ACTIONS = frozenset({"restart-api", "restart-nginx"})


class ShieldAgentError(RuntimeError):
    """The root-owned host agent was unavailable or rejected a request."""


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    return value


def _is_platform_owner(user_id: UUID) -> bool:
    with system_session() as session:
        return bool(
            session.execute(
                text("SELECT is_platform_owner FROM iam.users WHERE id = :user_id"),
                {"user_id": user_id},
            ).scalar_one_or_none()
        )


def require_shield_access(actor: ActorContext) -> None:
    """Enforce the power-plane boundary at the API, never only in the UI."""
    if actor.auth_kind != "session":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SHIELD does not accept Runtime API credentials",
        )
    if "audit.read" not in actor.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SHIELD requires audit.read",
        )
    future_l11 = max(
        [actor.role_level, *(identity.role_level for identity in actor.identities)],
        default=actor.role_level,
    ) >= 11
    if not future_l11 and not _is_platform_owner(actor.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform owner or L11 access required",
        )


def _agent_request(
    settings: Settings,
    operation: str,
    *,
    action: str | None = None,
    apply: bool = False,
    request_id: str | None = None,
) -> dict[str, object]:
    token = settings.shield_agent_token.get_secret_value()
    if not token:
        raise ShieldAgentError("SHIELD agent token is not configured")
    request = {
        "token": token,
        "operation": operation,
        "action": action,
        "apply": bool(apply),
        "request_id": request_id or str(uuid4()),
    }
    raw = (json.dumps(request, separators=(",", ":")) + "\n").encode()
    response = bytearray()
    try:
        if settings.shield_agent_host and settings.shield_agent_port > 0:
            client_context = socket.create_connection(
                (settings.shield_agent_host, settings.shield_agent_port),
                timeout=settings.shield_agent_timeout_seconds,
            )
        else:
            client_context = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        with client_context as client:
            client.settimeout(settings.shield_agent_timeout_seconds)
            if not settings.shield_agent_host or settings.shield_agent_port <= 0:
                client.connect(str(settings.shield_agent_socket))
            client.sendall(raw)
            while len(response) <= settings.shield_agent_max_response_bytes:
                chunk = client.recv(65536)
                if not chunk:
                    break
                response.extend(chunk)
                if b"\n" in chunk:
                    break
    except (OSError, TimeoutError) as exc:
        raise ShieldAgentError(f"SHIELD host agent unavailable: {type(exc).__name__}") from exc
    if not response or len(response) > settings.shield_agent_max_response_bytes:
        raise ShieldAgentError("SHIELD host agent returned an invalid response")
    try:
        payload = json.loads(bytes(response).split(b"\n", 1)[0])
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ShieldAgentError("SHIELD host agent returned malformed JSON") from exc
    if not isinstance(payload, dict):
        raise ShieldAgentError("SHIELD host agent response must be an object")
    return payload


def _append_audit(
    session: object,
    actor: ActorContext,
    event_type: str,
    payload: dict[str, object],
) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, default=str)
    session.execute(
        text(
            "SELECT shield.append_audit("
            ":tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb))"
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": encoded,
        },
    )


def _write_general_audit(
    session: object,
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


def _alert_signature(alert: dict[str, object]) -> str:
    return str(alert.get("code") or alert.get("label") or "unknown-signal")[:160]


def _persist_status(
    actor: ActorContext,
    vitals: dict[str, object],
) -> None:
    sampled_at = str(vitals.get("sampled_at") or datetime.now(UTC).isoformat())
    state = str(vitals.get("state") or "offline")
    severity = max(0, min(5, int(vitals.get("severity") or 0)))
    health_score_value = vitals.get("health_score")
    health_score = (
        max(0, min(100, int(health_score_value)))
        if isinstance(health_score_value, (int, float))
        else None
    )
    alerts = [item for item in vitals.get("alerts", []) if isinstance(item, dict)]
    signatures = {_alert_signature(alert) for alert in alerts}
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                INSERT INTO shield.snapshots(
                  tenant_id, sampled_at, state, severity, health_score, payload
                ) SELECT
                  :tenant_id, CAST(:sampled_at AS timestamptz), :state,
                  :severity, :health_score, CAST(:payload AS jsonb)
                WHERE NOT EXISTS (
                  SELECT 1 FROM shield.snapshots
                  WHERE sampled_at >= CAST(:sampled_at AS timestamptz) - INTERVAL '1 minute'
                )
                ON CONFLICT (tenant_id, sampled_at) DO NOTHING
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "sampled_at": sampled_at,
                "state": state,
                "severity": severity,
                "health_score": health_score,
                "payload": json.dumps(vitals, ensure_ascii=False, default=str),
            },
        )
        existing = {
            str(row["signature"]): dict(row)
            for row in session.execute(
                text(
                    """
                    SELECT id, signature, title, severity
                    FROM shield.incidents WHERE state = 'open'
                    """
                )
            ).mappings()
        }
        for alert in alerts:
            signature = _alert_signature(alert)
            alert_severity = max(1, min(5, int(alert.get("severity") or severity or 1)))
            title = str(alert.get("label") or signature)[:240]
            if signature in existing:
                session.execute(
                    text(
                        """
                        UPDATE shield.incidents
                        SET title = :title, severity = :severity,
                            details = CAST(:details AS jsonb), last_seen_at = now()
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": existing[signature]["id"],
                        "title": title,
                        "severity": alert_severity,
                        "details": json.dumps(alert, ensure_ascii=False, default=str),
                    },
                )
                continue
            incident_id = session.execute(
                text(
                    """
                    INSERT INTO shield.incidents(
                      tenant_id, signature, title, severity, details
                    ) VALUES (
                      :tenant_id, :signature, :title, :severity,
                      CAST(:details AS jsonb)
                    ) RETURNING id
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "signature": signature,
                    "title": title,
                    "severity": alert_severity,
                    "details": json.dumps(alert, ensure_ascii=False, default=str),
                },
            ).scalar_one()
            _append_audit(
                session,
                actor,
                "incident.opened",
                {
                    "incident_id": str(incident_id),
                    "signature": signature,
                    "severity": alert_severity,
                },
            )
        for signature, incident in existing.items():
            if signature in signatures:
                continue
            session.execute(
                text(
                    """
                    UPDATE shield.incidents
                    SET state = 'resolved', resolved_at = now(), last_seen_at = now()
                    WHERE id = :id AND state = 'open'
                    """
                ),
                {"id": incident["id"]},
            )
            _append_audit(
                session,
                actor,
                "incident.resolved",
                {"incident_id": str(incident["id"]), "signature": signature},
            )

        session.execute(
            text(
                """
                INSERT INTO shield.ai_risk_reviews(
                  tenant_id, execution_id, risk, summary
                )
                SELECT ce.tenant_id, ce.id, COALESCE(ce.response->>'risk', 'high'),
                       jsonb_build_object(
                         'command', ce.command, 'tool_name', ce.tool_name,
                         'origin', ce.origin, 'status', ce.status,
                         'created_at', ce.created_at
                       )
                FROM terminal.command_executions AS ce
                WHERE ce.origin IN ('ai_tool', 'auto_runtime')
                  AND ce.created_at >= now() - INTERVAL '24 hours'
                  AND (
                    ce.response->>'risk' = 'high'
                    OR ce.status IN ('failed', 'denied', 'target_rejected')
                  )
                ON CONFLICT (tenant_id, execution_id) DO NOTHING
                """
            )
        )


def _status_records(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        incidents = [
            {
                **dict(row),
                "id": str(row["id"]),
                "opened_at": row["opened_at"].isoformat(),
                "last_seen_at": row["last_seen_at"].isoformat(),
            }
            for row in session.execute(
                text(
                    """
                    SELECT id, signature, title, severity, state, source,
                           opened_at, last_seen_at, details
                    FROM shield.incidents
                    WHERE state = 'open'
                    ORDER BY severity DESC, opened_at DESC LIMIT 50
                    """
                )
            ).mappings()
        ]
        timeline = [
            {
                "id": int(row["id"]),
                "kind": str(row["event_type"]).replace(".", "_"),
                "content": row["payload"],
                "event_hash": row["event_hash"],
                "previous_hash": row["previous_hash"],
                "ts": row["created_at"].isoformat(),
            }
            for row in session.execute(
                text(
                    """
                    SELECT id, event_type, payload, previous_hash, event_hash, created_at
                    FROM shield.audit_chain ORDER BY id DESC LIMIT 80
                    """
                )
            ).mappings()
        ]
        risks = [
            {
                "id": str(row["id"]),
                "execution_id": str(row["execution_id"]),
                "state": row["state"],
                "risk": row["risk"],
                "summary": row["summary"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in session.execute(
                text(
                    """
                    SELECT id, execution_id, state, risk, summary, created_at
                    FROM shield.ai_risk_reviews
                    WHERE state = 'open' ORDER BY created_at DESC LIMIT 50
                    """
                )
            ).mappings()
        ]
    return {
        "open_incidents": incidents,
        "recent_timeline": timeline,
        "open_ai_risk_events": len(risks),
        "recent_ai_risk_events": risks,
    }


def _enrich_tenant_services(
    actor: ActorContext,
    vitals: dict[str, object],
) -> dict[str, object]:
    enriched = dict(vitals)
    ai = public_state(actor, "deepseek")
    ai_state = (
        "online"
        if ai["connected"]
        else "degraded"
        if ai["configured"]
        else "offline"
    )
    services = [dict(item) for item in enriched.get("services", []) if isinstance(item, dict)]
    services = [item for item in services if item.get("id") != "ai-engine"]
    services.append({"id": "ai-engine", "state": ai_state})
    enriched["services"] = services
    enriched["ai_engine"] = {
        "state": ai_state,
        "provider": ai["provider"],
        "configured": ai["configured"],
        "connected": ai["connected"],
        "model": ai["model"] if ai["connected"] else None,
        "checked_at": ai["connection"]["checked_at"],
    }
    return enriched


def get_shield_status(actor: ActorContext, settings: Settings) -> dict[str, object]:
    require_shield_access(actor)
    try:
        agent = _agent_request(settings, "status")
        agent_ok = agent.get("ok") is True
        vitals = agent.get("system_vitals")
        if not isinstance(vitals, dict):
            raise ShieldAgentError("SHIELD host agent omitted system_vitals")
        vitals = _enrich_tenant_services(actor, vitals)
        guardian_tail = [str(item) for item in agent.get("guardian_tail", [])][-80:]
    except ShieldAgentError as exc:
        agent_ok = False
        guardian_tail = [f"SHIELD AGENT OFFLINE · {exc}"]
        vitals = {
            "schema_version": 1,
            "sampled_at": datetime.now(UTC).isoformat(),
            "poll_hint_seconds": 5,
            "state": "offline",
            "severity": 5,
            "health_score": 0,
            "alerts": [
                {
                    "code": "shield-agent-offline",
                    "label": "SHIELD host agent offline",
                    "severity": 5,
                }
            ],
            "services": [{"id": "firefighter", "state": "offline"}],
            "data_sources": {
                "kernel": {"state": "unknown"},
                "firefighter": {"state": "offline"},
                "guardian": {"state": "alert"},
            },
        }
    _persist_status(actor, vitals)
    records = _status_records(actor)
    state = str(vitals.get("state") or "offline")
    return _json_safe(
        {
            "ok": agent_ok,
            "available": True,
            "status": "ready" if agent_ok else "degraded",
            "state": state,
            "severity": int(vitals.get("severity") or 0),
            "database": "connected",
            "frontend": "connected",
            "backend": "connected",
            "agent": "connected" if agent_ok else "offline",
            "system_vitals": vitals,
            "guardian_tail": guardian_tail,
            **records,
        }
    )


def execute_shield_repair(
    actor: ActorContext,
    settings: Settings,
    *,
    action: str,
    confirm: bool,
    apply_requested: bool,
    request_id: str,
) -> dict[str, object]:
    require_shield_access(actor)
    normalized = action.strip().lower()
    if normalized not in SHIELD_ACTIONS:
        raise HTTPException(status_code=422, detail="Unknown SHIELD action")
    if normalized != "healthcheck" and not confirm:
        raise HTTPException(status_code=409, detail="Explicit SHIELD confirmation is required")
    applied_request = (
        normalized != "healthcheck"
        and apply_requested
        and settings.shield_repair_apply
    )
    started = perf_counter()
    repair_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        prior = session.execute(
            text(
                """
                SELECT id, action, status, applied, result, error,
                       started_at, completed_at
                FROM shield.repair_runs WHERE request_id = :request_id
                """
            ),
            {"request_id": request_id},
        ).mappings().one_or_none()
        if prior is not None:
            stored_result = prior["result"] if isinstance(prior["result"], dict) else {}
            return _json_safe(
                {
                    "ok": prior["status"] != "failed",
                    "repair_id": prior["id"],
                    "action": prior["action"],
                    "status": prior["status"],
                    "applied": prior["applied"],
                    "dry_run": prior["action"] != "healthcheck" and not prior["applied"],
                    "returncode": stored_result.get("returncode"),
                    "result": stored_result.get("result", stored_result),
                    "error": prior["error"],
                    "started_at": prior["started_at"],
                    "completed_at": prior["completed_at"],
                }
            )
        session.execute(
            text(
                """
                INSERT INTO shield.repair_runs(
                  id, tenant_id, actor_user_id, action, confirmation_received,
                  apply_requested, status, request_id, request
                ) VALUES (
                  :id, :tenant_id, :actor_user_id, :action, :confirmation,
                  :apply_requested, 'running', :request_id, CAST(:request AS jsonb)
                )
                """
            ),
            {
                "id": repair_id,
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "action": normalized,
                "confirmation": bool(confirm or normalized == "healthcheck"),
                "apply_requested": applied_request,
                "request_id": request_id,
                "request": json.dumps(
                    {"action": normalized, "requested_apply": bool(apply_requested)},
                    ensure_ascii=False,
                ),
            },
        )
        _append_audit(
            session,
            actor,
            "repair.requested",
            {
                "repair_id": str(repair_id),
                "action": normalized,
                "apply": applied_request,
                "high_risk": normalized in HIGH_RISK_ACTIONS,
                "request_id": request_id,
            },
        )

    try:
        result = _agent_request(
            settings,
            "repair",
            action=normalized,
            apply=applied_request,
            request_id=request_id,
        )
        ok = result.get("ok") is True
        applied = result.get("applied") is True
        run_status = str(result.get("status") or ("succeeded" if ok else "failed"))
        if run_status not in {"scheduled", "succeeded", "failed"}:
            run_status = "succeeded" if ok else "failed"
        error = None if ok else str(result.get("error") or "SHIELD action failed")
    except ShieldAgentError as exc:
        result = {}
        ok = False
        applied = False
        run_status = "failed"
        error = str(exc)
    elapsed_ms = round((perf_counter() - started) * 1000)
    with tenant_session(actor.tenant_id) as session:
        session.execute(
            text(
                """
                UPDATE shield.repair_runs
                SET status = :status, applied = :applied,
                    result = CAST(:result AS jsonb), error = :error,
                    completed_at = now()
                WHERE id = :id
                """
            ),
            {
                "id": repair_id,
                "status": run_status,
                "applied": applied,
                "result": json.dumps(result, ensure_ascii=False, default=str),
                "error": error,
            },
        )
        audit_payload = {
            "repair_id": str(repair_id),
            "action": normalized,
            "status": run_status,
            "applied": applied,
            "elapsed_ms": elapsed_ms,
            "error": error,
        }
        _append_audit(session, actor, f"repair.{run_status}", audit_payload)
        _write_general_audit(session, actor, "shield_repair", audit_payload)
    return _json_safe(
        {
            "ok": ok,
            "repair_id": str(repair_id),
            "action": normalized,
            "status": run_status,
            "applied": applied,
            "dry_run": normalized != "healthcheck" and not applied_request,
            "elapsed_ms": elapsed_ms,
            "returncode": result.get("returncode"),
            "result": result.get("result", result),
            "error": error,
        }
    )


def review_ai_risk(
    actor: ActorContext,
    *,
    execution_id: UUID,
    decision: str,
) -> dict[str, object]:
    require_shield_access(actor)
    normalized = decision.strip().lower()
    if normalized not in {"reviewed", "dismissed"}:
        raise HTTPException(status_code=422, detail="decision must be reviewed or dismissed")
    with tenant_session(actor.tenant_id) as session:
        row = session.execute(
            text(
                """
                UPDATE shield.ai_risk_reviews
                SET state = :state, reviewed_by = :reviewed_by, reviewed_at = now()
                WHERE execution_id = :execution_id AND state = 'open'
                RETURNING id, state, reviewed_at
                """
            ),
            {
                "state": normalized,
                "reviewed_by": actor.user_id,
                "execution_id": execution_id,
            },
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Open AI risk was not found")
        _append_audit(
            session,
            actor,
            "ai-risk.reviewed",
            {"execution_id": str(execution_id), "decision": normalized},
        )
    return _json_safe({"ok": True, **dict(row), "execution_id": execution_id})
