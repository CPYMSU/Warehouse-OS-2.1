"""Governed browser journeys with durable tenant-scoped evidence."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from app.core.security import create_access_token
from app.db.session import system_session, tenant_session

if TYPE_CHECKING:
    from app.api.deps import ActorContext
    from app.core.config import Settings

ALLOWED_ACTIONS = frozenset({"navigate", "click", "fill", "press", "observe", "wait", "screenshot"})
ALLOWED_MODES = frozenset({"smoke", "full", "explore"})
ALLOWED_AUTH_MODES = frozenset({"actor", "anonymous"})
ALLOWED_MUTATION_POLICIES = frozenset({"read_only", "allow_writes"})
ALLOWED_LOCATOR_KEYS = frozenset({"role", "name", "label", "text", "test_id", "exact", "nth"})
ALLOWED_KEYS = frozenset(
    {
        "Enter",
        "Tab",
        "Escape",
        "Space",
        "ArrowUp",
        "ArrowDown",
        "ArrowLeft",
        "ArrowRight",
        "Home",
        "End",
        "PageUp",
        "PageDown",
        "Backspace",
        "Delete",
    }
)
ALLOWED_OBSERVATIONS = frozenset(
    {
        "visible",
        "hidden",
        "text_contains",
        "url_contains",
        "title_contains",
        "no_console_errors",
        "no_failed_requests",
    }
)
MAX_STEPS = 80
MAX_MANIFEST_BYTES = 256 * 1024


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (UUID, datetime, date, Decimal)):
        return str(value)
    return value


def _owner(user_id: UUID) -> bool:
    with system_session() as session:
        return bool(
            session.execute(
                text("SELECT is_platform_owner FROM iam.users WHERE id = :id"),
                {"id": user_id},
            ).scalar_one_or_none()
        )


def _can_read(actor: ActorContext) -> bool:
    return (
        actor.role_level >= 10
        or "browser.read" in actor.permissions
        or "browser.run" in actor.permissions
        or _owner(actor.user_id)
    )


def _require_read(actor: ActorContext) -> None:
    if not _can_read(actor):
        raise HTTPException(status_code=403, detail="Browser Runtime requires browser.read")


def _require_run(actor: ActorContext) -> None:
    if not (actor.role_level >= 10 or "browser.run" in actor.permissions or _owner(actor.user_id)):
        raise HTTPException(status_code=403, detail="Browser Runtime requires browser.run")


def _enum(value: object, allowed: frozenset[str], default: str, label: str) -> str:
    normalized = str(value or default).strip().lower()
    if normalized not in allowed:
        raise HTTPException(status_code=422, detail=f"Invalid {label}")
    return normalized


def _path(value: object, default: str = "/") -> str:
    result = str(value or default).strip()
    if not result.startswith("/") or result.startswith("//") or len(result) > 500:
        raise HTTPException(status_code=422, detail="Path must be a same-origin absolute path")
    return result


def _origin(value: object, settings: Settings) -> str:
    raw = (
        str(
            value
            or (settings.browser_allowed_origins[0] if settings.browser_allowed_origins else "")
        )
        .strip()
        .rstrip("/")
    )
    parsed = urlsplit(raw)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            status_code=422, detail="target_origin must contain only scheme and host"
        )
    allowed = {str(item).strip().rstrip("/") for item in settings.browser_allowed_origins}
    if raw not in allowed:
        raise HTTPException(
            status_code=422, detail="target_origin is outside the browser allowlist"
        )
    return raw


def _locator(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not value:
        raise HTTPException(status_code=422, detail="A semantic locator is required")
    unknown = set(map(str, value)) - ALLOWED_LOCATOR_KEYS
    if unknown:
        raise HTTPException(
            status_code=422, detail=f"Unsupported locator fields: {', '.join(sorted(unknown))}"
        )
    result = {str(key): item for key, item in value.items() if item is not None}
    if not any(key in result for key in ("role", "label", "text", "test_id")):
        raise HTTPException(status_code=422, detail="Locator needs role, label, text or test_id")
    for key in ("role", "name", "label", "text", "test_id"):
        if key in result and (not isinstance(result[key], str) or len(result[key]) > 300):
            raise HTTPException(status_code=422, detail=f"Invalid locator {key}")
    if "nth" in result and (not isinstance(result["nth"], int) or not 0 <= result["nth"] <= 100):
        raise HTTPException(status_code=422, detail="locator.nth must be between 0 and 100")
    result["exact"] = bool(result.get("exact", False))
    return result


def validate_steps(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or not value or len(value) > MAX_STEPS:
        raise HTTPException(status_code=422, detail=f"steps must contain 1-{MAX_STEPS} actions")
    normalized: list[dict[str, object]] = []
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail=f"Step {index} must be an object")
        action = str(raw.get("action") or "").strip().lower()
        if action not in ALLOWED_ACTIONS:
            raise HTTPException(status_code=422, detail=f"Step {index} has an unsupported action")
        step: dict[str, object] = {"action": action}
        if action == "navigate":
            step["path"] = _path(raw.get("path"))
        elif action in {"click", "fill", "press"}:
            step["locator"] = _locator(raw.get("locator"))
            if action == "fill":
                value_text = raw.get("value")
                if not isinstance(value_text, str) or len(value_text) > 4000:
                    raise HTTPException(
                        status_code=422, detail=f"Step {index} has an invalid fill value"
                    )
                if raw.get("sensitive") is True:
                    raise HTTPException(
                        status_code=422, detail="Secrets may not be persisted in browser manifests"
                    )
                step["value"] = value_text
            if action == "press":
                key = str(raw.get("key") or "")
                if key not in ALLOWED_KEYS:
                    raise HTTPException(
                        status_code=422, detail=f"Step {index} has an unsupported key"
                    )
                step["key"] = key
        elif action == "observe":
            kind = str(raw.get("kind") or "visible").strip().lower()
            if kind not in ALLOWED_OBSERVATIONS:
                raise HTTPException(
                    status_code=422, detail=f"Step {index} has an unsupported observation"
                )
            step["kind"] = kind
            if kind in {"visible", "hidden", "text_contains"}:
                step["locator"] = _locator(raw.get("locator"))
            if kind in {"text_contains", "url_contains", "title_contains"}:
                expected = str(raw.get("expected") or "")
                if not expected or len(expected) > 1000:
                    raise HTTPException(status_code=422, detail=f"Step {index} needs expected text")
                step["expected"] = expected
        elif action == "wait":
            milliseconds = int(raw.get("milliseconds") or 250)
            if not 50 <= milliseconds <= 5000:
                raise HTTPException(status_code=422, detail="wait milliseconds must be 50-5000")
            step["milliseconds"] = milliseconds
        elif action == "screenshot":
            step["full_page"] = bool(raw.get("full_page", True))
        if "note" in raw:
            step["note"] = str(raw.get("note") or "")[:500]
        normalized.append(step)
    encoded = json.dumps(normalized, ensure_ascii=False, separators=(",", ":")).encode()
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise HTTPException(status_code=422, detail="Browser manifest is too large")
    return normalized


def _default_steps(start_path: str) -> list[dict[str, object]]:
    return [
        {"action": "navigate", "path": start_path},
        {"action": "observe", "kind": "title_contains", "expected": "WAREHOUSE"},
        {"action": "observe", "kind": "no_console_errors"},
        {"action": "observe", "kind": "no_failed_requests"},
        {"action": "screenshot", "full_page": True},
    ]


def capabilities(actor: ActorContext, settings: Settings) -> dict[str, object]:
    _require_read(actor)
    with system_session() as session:
        workers = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """SELECT worker_id, release_id, state, current_run_id, metadata,
                              started_at, last_seen_at,
                              last_seen_at > now() - interval '30 seconds' AS online
                       """
                    "FROM browser_runtime.workers ORDER BY last_seen_at DESC LIMIT 20"
                )
            ).mappings()
        ]
    return {
        "available": bool(settings.browser_runtime_enabled),
        "engine": "playwright",
        "browser": "chromium",
        "protocol": "warehouse-browser-steps/v1",
        "actions": sorted(ALLOWED_ACTIONS),
        "allowed_origins": list(settings.browser_allowed_origins),
        "resource_origins": list(settings.browser_resource_origins),
        "isolation": {
            "tenant_rls": True,
            "raw_javascript": False,
            "arbitrary_selectors": False,
            "external_navigation": False,
            "third_party_resources": "allowlist_get_only",
            "credential_forwarding": False,
            "default_mutation_policy": "read_only",
        },
        "workers": workers,
        "can_run": actor.role_level >= 10
        or "browser.run" in actor.permissions
        or _owner(actor.user_id),
    }


def list_journeys(actor: ActorContext, limit: int = 100) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                """SELECT * FROM browser_runtime.journeys
                   ORDER BY active DESC, updated_at DESC LIMIT :limit"""
            ),
            {"limit": max(1, min(int(limit), 500))},
        ).mappings()
        items = [_json_safe(dict(row)) for row in rows]
    return {"available": True, "journeys": items, "items": items, "count": len(items)}


def create_journey(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    _require_run(actor)
    journey_key = str(payload.get("journey_key") or payload.get("key") or "").strip().lower()
    if not journey_key or len(journey_key) > 80:
        raise HTTPException(status_code=422, detail="journey_key is required")
    name = str(payload.get("name") or "").strip()
    if not name or len(name) > 160:
        raise HTTPException(status_code=422, detail="name is required")
    steps = validate_steps(payload.get("steps"))
    values = {
        "id": uuid4(),
        "tenant_id": actor.tenant_id,
        "journey_key": journey_key,
        "name": name,
        "description": str(payload.get("description") or "")[:4000],
        "mode": _enum(payload.get("mode"), ALLOWED_MODES, "smoke", "mode"),
        "auth_mode": _enum(payload.get("auth_mode"), ALLOWED_AUTH_MODES, "actor", "auth_mode"),
        "mutation_policy": _enum(
            payload.get("mutation_policy"),
            ALLOWED_MUTATION_POLICIES,
            "read_only",
            "mutation_policy",
        ),
        "start_path": _path(payload.get("start_path")),
        "steps": json.dumps(steps, ensure_ascii=False),
        "created_by": actor.user_id,
    }
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """INSERT INTO browser_runtime.journeys(
                     id, tenant_id, journey_key, name, description, mode, auth_mode,
                     mutation_policy, start_path, steps, created_by
                   ) VALUES (
                     :id, :tenant_id, :journey_key, :name, :description, :mode, :auth_mode,
                     :mutation_policy, :start_path, CAST(:steps AS jsonb), :created_by
                   ) RETURNING *"""
                ),
                values,
            )
            .mappings()
            .one()
        )
        session.execute(
            text(
                """INSERT INTO audit.events(
                     tenant_id, actor_user_id, event_type, payload
                   ) VALUES (
                     :tenant_id, :actor, 'browser.journey.created',
                     CAST(:payload AS jsonb)
                   )"""
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor": actor.user_id,
                "payload": json.dumps(
                    {"journey_id": str(values["id"]), "journey_key": journey_key}
                ),
            },
        )
    return {"available": True, "journey": _json_safe(dict(row))}


def _journey(session, reference: object) -> dict[str, object] | None:
    if not reference:
        return None
    row = (
        session.execute(
            text(
                """SELECT * FROM browser_runtime.journeys
                   WHERE active
                     AND (id::text = :ref OR journey_key = :ref)
                   LIMIT 1"""
            ),
            {"ref": str(reference)},
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


def create_run(
    actor: ActorContext, payload: dict[str, object], settings: Settings
) -> dict[str, object]:
    _require_run(actor)
    if not settings.browser_runtime_enabled:
        raise HTTPException(status_code=503, detail="Browser Runtime worker is disabled")
    with tenant_session(actor.tenant_id) as session:
        journey = _journey(session, payload.get("journey") or payload.get("journey_id"))
        start_path = _path(payload.get("start_path"), str((journey or {}).get("start_path") or "/"))
        raw_steps = (
            payload.get("steps")
            if payload.get("steps") is not None
            else (journey or {}).get("steps")
        )
        steps = validate_steps(raw_steps) if raw_steps is not None else _default_steps(start_path)
        mode = _enum(
            payload.get("mode"), ALLOWED_MODES, str((journey or {}).get("mode") or "smoke"), "mode"
        )
        auth_mode = _enum(
            payload.get("auth_mode"),
            ALLOWED_AUTH_MODES,
            str((journey or {}).get("auth_mode") or "actor"),
            "auth_mode",
        )
        mutation_policy = _enum(
            payload.get("mutation_policy"),
            ALLOWED_MUTATION_POLICIES,
            str((journey or {}).get("mutation_policy") or "read_only"),
            "mutation_policy",
        )
        if mutation_policy == "allow_writes" and payload.get("confirm_mutations") is not True:
            raise HTTPException(
                status_code=409, detail="allow_writes requires confirm_mutations=true"
            )
        viewport = payload.get("viewport") or {"width": 1440, "height": 1000}
        if not isinstance(viewport, dict):
            raise HTTPException(status_code=422, detail="viewport must be an object")
        width, height = int(viewport.get("width") or 1440), int(viewport.get("height") or 1000)
        if not 320 <= width <= 2560 or not 480 <= height <= 2160:
            raise HTTPException(status_code=422, detail="viewport is outside supported bounds")
        run_id = uuid4()
        values = {
            "id": run_id,
            "tenant_id": actor.tenant_id,
            "journey_id": (journey or {}).get("id"),
            "journey_version": (journey or {}).get("version"),
            "name": str(payload.get("name") or (journey or {}).get("name") or "Browser smoke")[
                :160
            ],
            "mode": mode,
            "auth_mode": auth_mode,
            "mutation_policy": mutation_policy,
            "target_origin": _origin(payload.get("target_origin"), settings),
            "start_path": start_path,
            "viewport": json.dumps({"width": width, "height": height}),
            "steps": json.dumps(steps, ensure_ascii=False),
            "requested_by": actor.user_id,
        }
        row = (
            session.execute(
                text(
                    """INSERT INTO browser_runtime.runs(
                     id, tenant_id, journey_id, journey_version, name, mode, auth_mode,
                     mutation_policy, target_origin, start_path, viewport,
                     steps_manifest, requested_by
                   ) VALUES (
                     :id, :tenant_id, :journey_id, :journey_version, :name, :mode, :auth_mode,
                     :mutation_policy, :target_origin, :start_path, CAST(:viewport AS jsonb),
                     CAST(:steps AS jsonb), :requested_by
                   ) RETURNING *"""
                ),
                values,
            )
            .mappings()
            .one()
        )
        for ordinal, step in enumerate(steps, start=1):
            session.execute(
                text(
                    """INSERT INTO browser_runtime.steps(
                         tenant_id, run_id, ordinal, action, request
                       ) VALUES (
                         :tenant_id, :run_id, :ordinal, :action,
                         CAST(:request AS jsonb)
                       )"""
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "run_id": run_id,
                    "ordinal": ordinal,
                    "action": step["action"],
                    "request": json.dumps(step, ensure_ascii=False),
                },
            )
        session.execute(
            text(
                """INSERT INTO browser_runtime.events(
                     tenant_id, run_id, event_type, message, payload
                   ) VALUES (
                     :tenant_id, :run_id, 'run.queued', 'Browser run queued',
                     CAST(:payload AS jsonb)
                   )"""
            ),
            {
                "tenant_id": actor.tenant_id,
                "run_id": run_id,
                "payload": json.dumps(
                    {"actor_user_id": str(actor.user_id), "step_count": len(steps)}
                ),
            },
        )
        session.execute(
            text(
                """INSERT INTO audit.events(
                     tenant_id, actor_user_id, event_type, payload
                   ) VALUES (
                     :tenant_id, :actor, 'browser.run.queued',
                     CAST(:payload AS jsonb)
                   )"""
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor": actor.user_id,
                "payload": json.dumps(
                    {
                        "run_id": str(run_id),
                        "mutation_policy": mutation_policy,
                        "step_count": len(steps),
                    }
                ),
            },
        )
    return {"available": True, "run": _json_safe(dict(row))}


def list_runs(actor: ActorContext, limit: int = 100) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                """SELECT r.*, j.journey_key,
                          (SELECT count(*) FROM browser_runtime.steps s
                           WHERE s.run_id = r.id) AS step_count,
                          (SELECT count(*) FROM browser_runtime.steps s
                           WHERE s.run_id = r.id AND s.status = 'failed') AS failed_steps
                   FROM browser_runtime.runs r
                   LEFT JOIN browser_runtime.journeys j ON j.id = r.journey_id
                   ORDER BY r.created_at DESC LIMIT :limit"""
            ),
            {"limit": max(1, min(int(limit), 500))},
        ).mappings()
        items = [_json_safe(dict(row)) for row in rows]
    return {"available": True, "runs": items, "items": items, "count": len(items)}


def run_detail(actor: ActorContext, run_id: UUID) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        run = (
            session.execute(
                text("SELECT * FROM browser_runtime.runs WHERE id = :id"), {"id": run_id}
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            raise HTTPException(status_code=404, detail="Browser run not found")
        steps = [
            _json_safe(dict(row))
            for row in session.execute(
                text("SELECT * FROM browser_runtime.steps WHERE run_id = :id ORDER BY ordinal"),
                {"id": run_id},
            ).mappings()
        ]
        events = [
            _json_safe(dict(row))
            for row in session.execute(
                text("SELECT * FROM browser_runtime.events WHERE run_id = :id ORDER BY id"),
                {"id": run_id},
            ).mappings()
        ]
        artifacts = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    "SELECT * FROM browser_runtime.artifacts WHERE run_id = :id ORDER BY created_at"
                ),
                {"id": run_id},
            ).mappings()
        ]
    return {
        "available": True,
        "run": _json_safe(dict(run)),
        "steps": steps,
        "events": events,
        "artifacts": artifacts,
    }


def cancel_run(actor: ActorContext, run_id: UUID) -> dict[str, object]:
    _require_run(actor)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """UPDATE browser_runtime.runs
                   SET cancel_requested_at = now(),
                       status = CASE WHEN status IN ('queued', 'claimed')
                         THEN 'cancelled' ELSE status END,
                       finished_at = CASE WHEN status IN ('queued', 'claimed')
                         THEN now() ELSE finished_at END
                   WHERE id = :id
                     AND status NOT IN ('succeeded', 'failed', 'cancelled', 'timed_out')
                   RETURNING *"""
                ),
                {"id": run_id},
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            existing = (
                session.execute(
                    text("SELECT * FROM browser_runtime.runs WHERE id = :id"), {"id": run_id}
                )
                .mappings()
                .one_or_none()
            )
            if existing is None:
                raise HTTPException(status_code=404, detail="Browser run not found")
            row = existing
    return {"available": True, "run": _json_safe(dict(row))}


def worker_session_token(
    run_id: UUID,
    tenant_id: UUID,
    worker_id: str,
    worker_token: str,
    settings: Settings,
) -> dict[str, object]:
    expected = settings.browser_worker_token.get_secret_value()
    if not expected or not hmac.compare_digest(worker_token, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid browser worker credential"
        )
    with tenant_session(tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT r.requested_by AS actor_user_id, t.slug AS tenant_slug
                FROM browser_runtime.runs AS r
                JOIN iam.tenants AS t ON t.id = r.tenant_id
                JOIN iam.memberships AS m
                  ON m.tenant_id = r.tenant_id AND m.user_id = r.requested_by
                JOIN iam.users AS u ON u.id = r.requested_by
                WHERE r.id = :run_id
                  AND r.tenant_id = :tenant_id
                  AND r.claimed_by = :worker_id
                  AND r.status IN ('claimed', 'running')
                  AND r.auth_mode = 'actor'
                  AND r.requested_by IS NOT NULL
                  AND r.heartbeat_at > now() - interval '3 minutes'
                  AND t.status = 'active'
                  AND m.active
                  AND u.active
                LIMIT 1
                """
                ),
                {"run_id": run_id, "tenant_id": tenant_id, "worker_id": worker_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Claimed browser run not found")
    return {
        "token": create_access_token(
            settings=settings,
            user_id=row["actor_user_id"],
            tenant_id=tenant_id,
            expires_minutes=10,
        ),
        "tenant": row["tenant_slug"],
        "expires_in_seconds": 600,
    }


def artifact_file(actor: ActorContext, artifact_id: UUID, settings: Settings) -> tuple[Path, str]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """SELECT relative_path, content_type, content_sha256
                       FROM browser_runtime.artifacts WHERE id = :id"""
                ),
                {"id": artifact_id},
            )
            .mappings()
            .one_or_none()
        )
    if row is None:
        raise HTTPException(status_code=404, detail="Browser artifact not found")
    root = settings.browser_runtime_root.expanduser().resolve()
    candidate = (root / str(row["relative_path"])).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Unsafe browser artifact path") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Browser artifact bytes are unavailable")
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    if not hmac.compare_digest(digest, str(row["content_sha256"])):
        raise HTTPException(status_code=409, detail="Browser artifact integrity check failed")
    return candidate, str(row["content_type"])
