"""Catalogue-driven PostgreSQL gateway for migrated terminal contracts.

The legacy command catalogue is the routing contract.  This module contains no
per-command business branches: it validates an incoming method/path against the
catalogue and persists transitional domain state in the tenant-isolated
PostgreSQL projection store.  Explicit FastAPI domain routes are mounted before
this gateway and therefore continue to own every contract that has a native
implementation.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import text

from app.db.session import tenant_session
from app.terminal import legacy_catalog

if TYPE_CHECKING:
    from app.api.deps import ActorContext

_SUPPORTED_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})
_SECRET_PARTS = frozenset(
    {"password", "secret", "token", "api_key", "credential", "passkey", "sql"}
)
_ARCHIVE_WORDS = frozenset(
    {
        "archive",
        "cancel",
        "close",
        "delete",
        "disable",
        "dismiss",
        "offboard",
        "reject",
        "remove",
        "revoke",
    }
)


@dataclass(frozen=True)
class ContractMatch:
    """One exact tenant command contract matched to a concrete HTTP request."""

    entry: dict[str, Any]
    path_params: dict[str, str]


def _path_parameter_names(path: str) -> frozenset[str]:
    return frozenset(re.findall(r"\{([^{}]+)\}", path))


def gateway_contract_ready(entry: dict[str, Any]) -> bool:
    """Return whether a catalogue row is structurally routable by the gateway."""

    method = str(entry.get("api_method") or "").upper()
    path = str(entry.get("api_path") or "")
    params = entry.get("params")
    if method not in _SUPPORTED_METHODS or not path.startswith("/api/"):
        return False
    if not isinstance(params, list):
        return False
    destinations: set[str] = set()
    for parameter in params:
        if not isinstance(parameter, dict):
            return False
        destination = str(parameter.get("dest") or "")
        scope, separator, key = destination.partition(".")
        if scope not in {"path", "query", "body"}:
            return False
        if scope != "body" and (not separator or not key):
            return False
        if scope == "body" and separator and not key:
            return False
        destinations.add(destination)
    path_destinations = {
        destination.removeprefix("path.")
        for destination in destinations
        if destination.startswith("path.")
    }
    return path_destinations == set(_path_parameter_names(path))


def _compile_path(path: str) -> re.Pattern[str]:
    cursor = 0
    chunks: list[str] = ["^"]
    for match in re.finditer(r"\{([^{}]+)\}", path):
        chunks.append(re.escape(path[cursor : match.start()]))
        chunks.append(f"(?P<{match.group(1)}>[^/?]+)")
        cursor = match.end()
    chunks.extend((re.escape(path[cursor:]), "$"))
    return re.compile("".join(chunks))


@lru_cache(maxsize=1)
def _contracts() -> tuple[tuple[dict[str, Any], re.Pattern[str]], ...]:
    rows = [
        (entry, _compile_path(str(entry["api_path"])))
        for entry in legacy_catalog.COMMANDS
        if gateway_contract_ready(entry)
    ]
    rows.sort(
        key=lambda row: (
            -len(str(row[0]["api_path"]).replace("{", "").replace("}", "")),
            str(row[0]["tool_name"]),
        )
    )
    return tuple(rows)


def match_contract(
    method: str,
    path: str,
    *,
    tool_name: str | None = None,
) -> ContractMatch | None:
    """Resolve a request without allowing its caller to select another route."""

    normalized_method = method.upper()
    if tool_name:
        entry = next(
            (
                candidate
                for candidate in legacy_catalog.COMMANDS
                if candidate["tool_name"] == tool_name
            ),
            None,
        )
        if (
            entry is None
            or str(entry["api_method"]).upper() != normalized_method
            or not gateway_contract_ready(entry)
        ):
            return None
        matched = _compile_path(str(entry["api_path"])).fullmatch(path)
        return (
            ContractMatch(entry=entry, path_params=matched.groupdict())
            if matched
            else None
        )

    candidates: list[ContractMatch] = []
    for entry, pattern in _contracts():
        if str(entry["api_method"]).upper() != normalized_method:
            continue
        matched = pattern.fullmatch(path)
        if matched:
            candidates.append(
                ContractMatch(entry=entry, path_params=matched.groupdict())
            )
    if not candidates:
        return None
    # Three historical pairs share a method/path.  Direct API callers must name
    # the tool rather than letting registry order silently choose a mutation.
    unique_tools = {str(candidate.entry["tool_name"]) for candidate in candidates}
    return candidates[0] if len(unique_tools) == 1 else None


def _safe_value(key: str, value: object) -> object:
    if any(part in key.lower() for part in _SECRET_PARTS):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(name): _safe_value(str(name), item) for name, item in value.items()}
    if isinstance(value, list):
        return [_safe_value(key, item) for item in value]
    return value


def _safe_mapping(value: dict[str, object] | None) -> dict[str, object]:
    return {
        str(key): _safe_value(str(key), item)
        for key, item in (value or {}).items()
    }


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _namespace(entry: dict[str, Any]) -> str:
    path = str(entry["api_path"]).removeprefix("/api/")
    literal = path.split("/{", 1)[0].strip("/")
    components = [
        re.sub(r"[^a-z0-9_-]+", "_", component.lower()).strip("_")
        for component in literal.split("/")
        if component
    ]
    # A two-component family keeps related create/show/update contracts on the
    # same projection while avoiding one giant catch-all namespace.
    family = ".".join(components[:2]) or "root"
    return f"capability.{family}"[:120]


def _entity_key(
    entry: dict[str, Any],
    path_params: dict[str, str],
    query: dict[str, object],
    body: dict[str, object],
) -> str:
    if path_params:
        return ":".join(str(value) for value in path_params.values())[:240]
    for source in (body, query):
        for key in ("id", "key", "code", "name", "slug"):
            value = source.get(key)
            if value not in (None, ""):
                return str(value)[:240]
        for key, value in source.items():
            if key.endswith("_id") and value not in (None, ""):
                return str(value)[:240]
    if not bool(entry.get("writes")):
        return "default"
    return str(uuid4())


def _operation_words(entry: dict[str, Any]) -> frozenset[str]:
    return frozenset(
        re.findall(
            r"[a-z0-9]+",
            f"{entry.get('command', '')} {entry.get('tool_name', '')}".lower(),
        )
    )


def _documents(
    session: object, namespace: str, *, limit: int
) -> list[dict[str, object]]:
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
        {"namespace": namespace, "limit": max(1, min(limit, 1000))},
    ).mappings().all()
    result: list[dict[str, object]] = []
    for row in rows:
        payload = dict(row["payload"]) if isinstance(row["payload"], dict) else {}
        payload.setdefault("id", str(row["id"]))
        payload.setdefault("document_key", str(row["document_key"]))
        payload.setdefault("source", str(row["source"]))
        payload.setdefault("version", int(row["version"]))
        payload.setdefault("created_at", row["created_at"])
        payload.setdefault("updated_at", row["updated_at"])
        result.append(_json_safe(payload))
    return result


def execute_gateway_contract(
    actor: ActorContext,
    match: ContractMatch,
    *,
    query: dict[str, object] | None = None,
    body: dict[str, object] | None = None,
    origin: str = "api",
) -> dict[str, object]:
    """Execute one catalogue contract against the tenant PostgreSQL projection."""

    entry = match.entry
    query_values = _safe_mapping(query)
    body_values = _safe_mapping(body)
    namespace = _namespace(entry)
    entity_key = _entity_key(entry, match.path_params, query_values, body_values)
    operation_id = str(uuid4())
    now = datetime.now(UTC).isoformat()
    writes = bool(entry["writes"])

    with tenant_session(actor.tenant_id) as session:
        if not writes:
            requested_limit = query_values.get("limit", body_values.get("limit", 100))
            try:
                limit = int(requested_limit)
            except (TypeError, ValueError):
                limit = 100
            rows = _documents(session, namespace, limit=limit)
            if match.path_params:
                rows = [
                    row
                    for row in rows
                    if str(row.get("document_key") or row.get("id")) == entity_key
                ]
            result: dict[str, object] = {
                "ok": True,
                "available": True,
                "adapter": "tenant_postgresql_capability_gateway",
                "tool_name": str(entry["tool_name"]),
                "namespace": namespace,
                "items": rows,
                "rows": rows,
                "total": len(rows),
            }
        else:
            current = session.execute(
                text(
                    """
                    SELECT payload
                    FROM compatibility.documents
                    WHERE namespace = :namespace
                      AND document_key = :document_key
                    LIMIT 1
                    """
                ),
                {"namespace": namespace, "document_key": entity_key},
            ).scalar_one_or_none()
            prior = dict(current) if isinstance(current, dict) else {}
            payload = {
                **prior,
                **body_values,
                "id": str(prior.get("id") or entity_key),
                "document_key": entity_key,
                "last_operation": str(entry["tool_name"]),
                "last_query": query_values,
                "last_path_params": match.path_params,
                "updated_at": now,
            }
            archive = bool(_operation_words(entry).intersection(_ARCHIVE_WORDS))
            status = "archived" if archive else "active"
            row = session.execute(
                text(
                    """
                    INSERT INTO compatibility.documents(
                      id, tenant_id, namespace, document_key, status, payload,
                      source, updated_by
                    ) VALUES (
                      :id, :tenant_id, :namespace, :document_key, :status,
                      CAST(:payload AS jsonb), 'native', :updated_by
                    )
                    ON CONFLICT (tenant_id, namespace, document_key)
                    DO UPDATE SET
                      status = EXCLUDED.status,
                      payload = EXCLUDED.payload,
                      source = 'native',
                      version = compatibility.documents.version + 1,
                      updated_by = EXCLUDED.updated_by
                    RETURNING id, document_key, status, payload, version,
                              created_at, updated_at
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "namespace": namespace,
                    "document_key": entity_key,
                    "status": status,
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                    "updated_by": actor.user_id,
                },
            ).mappings().one()
            result = {
                "ok": True,
                "available": True,
                "adapter": "tenant_postgresql_capability_gateway",
                "tool_name": str(entry["tool_name"]),
                "operation_id": operation_id,
                "entity_id": str(row["id"]),
                "document_key": str(row["document_key"]),
                "status": str(row["status"]),
                "version": int(row["version"]),
                "data": _json_safe(dict(row["payload"])),
                "created_at": _json_safe(row["created_at"]),
                "updated_at": _json_safe(row["updated_at"]),
            }

        session.execute(
            text(
                """
                INSERT INTO audit.events(
                  tenant_id, actor_user_id, event_type, payload
                ) VALUES (
                  :tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "event_type": "capability.gateway.executed",
                "payload": json.dumps(
                    {
                        "operation_id": operation_id,
                        "tool_name": entry["tool_name"],
                        "method": entry["api_method"],
                        "path_template": entry["api_path"],
                        "namespace": namespace,
                        "document_key": entity_key,
                        "writes": writes,
                        "origin": origin,
                    },
                    ensure_ascii=False,
                ),
            },
        )
    return result
