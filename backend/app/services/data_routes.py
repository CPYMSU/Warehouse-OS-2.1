"""Tenant-isolated control-plane definitions for cross-program data routes.

Warehouse stores topology, policy and lifecycle metadata only.  Database
credentials and business query results are deliberately outside this module.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import text

from app.api.deps import ActorContext
from app.db.session import tenant_session

NAMESPACE = "database.data_routes"
ROUTE_KEY_RE = re.compile(r"^[a-z][a-z0-9-]{2,79}$")
NODE_TYPES = frozenset({"program", "input", "filter", "map", "join", "output"})
ROUTE_STATES = frozenset({"draft", "active", "suspended"})
SENSITIVE_KEYS = frozenset(
    {
        "password",
        "database_password",
        "dsn",
        "database_url",
        "connection_string",
        "secret",
        "secret_key",
        "api_key",
        "access_token",
        "refresh_token",
        "private_key",
    }
)


def _require_read(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.read",
        "assets.manage",
        "asset_mgmt.read",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=403, detail="Permission denied")


def _require_manage(actor: ActorContext) -> None:
    if actor.role_level >= 10 or {
        "assets.manage",
        "asset_mgmt.manage",
    }.intersection(actor.permissions):
        return
    raise HTTPException(status_code=403, detail="Permission denied")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: object, name: str, *, maximum: int, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise HTTPException(status_code=422, detail=f"{name} is required")
    if len(result) > maximum:
        raise HTTPException(status_code=422, detail=f"{name} is too long")
    return result


def _contains_sensitive_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).strip().lower() in SENSITIVE_KEYS or _contains_sensitive_key(item):
                return True
    elif isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False


def _normalise_nodes(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list) or len(value) > 40:
        raise HTTPException(status_code=422, detail="nodes must be an array with at most 40 items")
    output: list[dict[str, object]] = []
    identifiers: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail="Each route node must be an object")
        node_id = _text(raw.get("id"), "node.id", maximum=80, required=True)
        node_type = _text(raw.get("type"), "node.type", maximum=20, required=True)
        if node_type not in NODE_TYPES:
            raise HTTPException(status_code=422, detail=f"Unsupported node type: {node_type}")
        if node_id in identifiers:
            raise HTTPException(status_code=422, detail=f"Duplicate node id: {node_id}")
        identifiers.add(node_id)
        try:
            x = max(0, min(1600, int(float(raw.get("x", 0)))))
            y = max(0, min(900, int(float(raw.get("y", 0)))))
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="Node coordinates must be numeric") from exc
        node: dict[str, object] = {
            "id": node_id,
            "type": node_type,
            "label": _text(raw.get("label"), "node.label", maximum=120, required=True),
            "x": x,
            "y": y,
        }
        for field, maximum in (
            ("workspace_key", 160),
            ("resource", 160),
            ("operation", 80),
            ("expression", 500),
            ("output_name", 120),
        ):
            if raw.get(field) not in (None, ""):
                node[field] = _text(raw.get(field), f"node.{field}", maximum=maximum)
        fields = raw.get("fields")
        if fields is not None:
            if not isinstance(fields, list) or len(fields) > 100:
                raise HTTPException(status_code=422, detail="node.fields must be an array")
            node["fields"] = [
                _text(item, "node.fields[]", maximum=120, required=True) for item in fields
            ]
        output.append(node)
    return output


def _normalise_edges(value: object, node_ids: set[str]) -> list[dict[str, str]]:
    if not isinstance(value, list) or len(value) > 80:
        raise HTTPException(status_code=422, detail="edges must be an array with at most 80 items")
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in value:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=422, detail="Each route edge must be an object")
        source = _text(raw.get("source"), "edge.source", maximum=80, required=True)
        target = _text(raw.get("target"), "edge.target", maximum=80, required=True)
        if source == target or source not in node_ids or target not in node_ids:
            raise HTTPException(
                status_code=422, detail="Route edge must connect two different nodes"
            )
        pair = (source, target)
        if pair in seen:
            continue
        seen.add(pair)
        output.append(
            {
                "id": _text(raw.get("id") or f"{source}--{target}", "edge.id", maximum=180),
                "source": source,
                "target": target,
                "label": _text(raw.get("label"), "edge.label", maximum=120),
            }
        )
    return output


def _normalise_payload(
    payload: object, *, existing: dict[str, object] | None = None
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=422, detail="Route definition must be an object")
    if _contains_sensitive_key(payload):
        raise HTTPException(status_code=422, detail="Route definitions cannot contain credentials")
    route_key = _text(
        payload.get("route_key") or (existing or {}).get("route_key"),
        "route_key",
        maximum=80,
        required=True,
    ).lower()
    if not ROUTE_KEY_RE.fullmatch(route_key):
        raise HTTPException(
            status_code=422, detail="route_key must use lowercase letters, numbers and hyphens"
        )
    nodes = _normalise_nodes(payload.get("nodes", (existing or {}).get("nodes", [])))
    edges = _normalise_edges(
        payload.get("edges", (existing or {}).get("edges", [])),
        {str(node["id"]) for node in nodes},
    )
    rules = payload.get("rules", (existing or {}).get("rules", {}))
    if not isinstance(rules, dict):
        raise HTTPException(status_code=422, detail="rules must be an object")
    encoded_rules = json.dumps(rules, ensure_ascii=False)
    if len(encoded_rules.encode("utf-8")) > 32_000:
        raise HTTPException(status_code=422, detail="rules are too large")
    state = _text(payload.get("state", (existing or {}).get("state", "draft")), "state", maximum=20)
    if state not in ROUTE_STATES:
        raise HTTPException(status_code=422, detail="Unsupported route state")
    if state == "active":
        program_count = sum(1 for node in nodes if node["type"] == "program")
        if program_count < 2 or not any(node["type"] == "output" for node in nodes) or not edges:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Published routes require two program nodes, one output node and connections"
                ),
            )
    source = payload.get("source", (existing or {}).get("source", {}))
    if not isinstance(source, dict):
        raise HTTPException(status_code=422, detail="source must be an object")
    normalised_source = {
        "kind": _text(source.get("kind") or "route_manifest", "source.kind", maximum=40),
        "repository": _text(source.get("repository"), "source.repository", maximum=300),
        "ref": _text(source.get("ref"), "source.ref", maximum=160),
        "path": _text(source.get("path"), "source.path", maximum=500),
        "digest": _text(source.get("digest"), "source.digest", maximum=160),
        "parser": _text(source.get("parser"), "source.parser", maximum=120),
        "observed_at": _text(source.get("observed_at") or _now(), "source.observed_at", maximum=80),
    }
    return {
        "id": str((existing or {}).get("id") or uuid4()),
        "route_key": route_key,
        "name": _text(
            payload.get("name", (existing or {}).get("name")), "name", maximum=120, required=True
        ),
        "description": _text(
            payload.get("description", (existing or {}).get("description")),
            "description",
            maximum=500,
        ),
        "state": state,
        "nodes": nodes,
        "edges": edges,
        "rules": rules,
        "source": normalised_source,
        "source_of_truth": "program_code",
        "editable_in_warehouse": False,
        "revision": int((existing or {}).get("revision", 0)) + 1,
        "created_at": str((existing or {}).get("created_at") or _now()),
        "updated_at": _now(),
    }


def _row_payload(row: object) -> dict[str, object] | None:
    if not row:
        return None
    value = row.get("payload") if hasattr(row, "get") else None
    if not isinstance(value, dict):
        return None
    result = dict(value)
    result["revision"] = int(row.get("version") or result.get("revision") or 1)
    result["created_at"] = (
        row.get("created_at").isoformat() if row.get("created_at") else result.get("created_at")
    )
    result["updated_at"] = (
        row.get("updated_at").isoformat() if row.get("updated_at") else result.get("updated_at")
    )
    return result


def list_routes(actor: ActorContext, *, limit: int = 100) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT payload, version, created_at, updated_at
                FROM compatibility.documents
                WHERE namespace=:namespace AND status='active'
                ORDER BY updated_at DESC
                LIMIT :limit
                """
                ),
                {"namespace": NAMESPACE, "limit": max(1, min(int(limit), 200))},
            )
            .mappings()
            .all()
        )
    routes = [route for row in rows if (route := _row_payload(row)) is not None]
    return {
        "routes": routes,
        "count": len(routes),
        "business_data_stored": False,
        "source_of_truth": "program_code",
        "editable_in_warehouse": False,
    }


def get_route(actor: ActorContext, route_key: str) -> dict[str, object]:
    _require_read(actor)
    with tenant_session(actor.tenant_id) as session:
        row = (
            session.execute(
                text(
                    """
                SELECT payload, version, created_at, updated_at
                FROM compatibility.documents
                WHERE namespace=:namespace AND document_key=:route_key AND status='active'
                """
                ),
                {"namespace": NAMESPACE, "route_key": route_key},
            )
            .mappings()
            .one_or_none()
        )
    route = _row_payload(row)
    if route is None:
        raise HTTPException(status_code=404, detail="Data route not found")
    return route


def save_route(
    actor: ActorContext, payload: object, *, route_key: str | None = None
) -> dict[str, object]:
    _require_manage(actor)
    existing = get_route(actor, route_key) if route_key else None
    route = _normalise_payload(payload, existing=existing)
    if route_key and route["route_key"] != route_key:
        raise HTTPException(status_code=409, detail="route_key is immutable")
    expected_revision = payload.get("expected_revision") if isinstance(payload, dict) else None
    if (
        existing is not None
        and expected_revision is not None
        and int(expected_revision) != int(existing["revision"])
    ):
        raise HTTPException(status_code=409, detail="Route revision changed; reload before saving")
    with tenant_session(actor.tenant_id, actor.user_id) as session:
        if existing is None:
            duplicate = session.execute(
                text(
                    """
                    SELECT 1 FROM compatibility.documents
                    WHERE namespace=:namespace AND document_key=:route_key
                    """
                ),
                {"namespace": NAMESPACE, "route_key": route["route_key"]},
            ).scalar_one_or_none()
            if duplicate:
                raise HTTPException(status_code=409, detail="route_key already exists")
            session.execute(
                text(
                    """
                    INSERT INTO compatibility.documents(
                      id,tenant_id,namespace,document_key,payload,source,updated_by
                    ) VALUES (
                      :id,:tenant_id,:namespace,:route_key,
                      CAST(:payload AS jsonb),'native',:updated_by
                    )
                    """
                ),
                {
                    "id": uuid4(),
                    "tenant_id": actor.tenant_id,
                    "namespace": NAMESPACE,
                    "route_key": route["route_key"],
                    "payload": json.dumps(route, ensure_ascii=False),
                    "updated_by": actor.user_id,
                },
            )
        else:
            session.execute(
                text(
                    """
                    UPDATE compatibility.documents
                    SET payload=CAST(:payload AS jsonb), version=version+1,
                        updated_by=:updated_by, updated_at=now()
                    WHERE namespace=:namespace AND document_key=:route_key AND status='active'
                    """
                ),
                {
                    "namespace": NAMESPACE,
                    "route_key": route_key,
                    "payload": json.dumps(route, ensure_ascii=False),
                    "updated_by": actor.user_id,
                },
            )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id,actor_user_id,event_type,payload)
                VALUES (
                  :tenant_id,:actor_user_id,'database.data_route.saved',CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {
                        "route_key": route["route_key"],
                        "state": route["state"],
                        "node_count": len(route["nodes"]),
                        "edge_count": len(route["edges"]),
                        "business_data_stored": False,
                    }
                ),
            },
        )
    return {"ok": True, "route": get_route(actor, str(route["route_key"]))}
