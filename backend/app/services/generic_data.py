"""AI-native semantic resource registry and tenant-isolated Data API.

The model and clients address stable resource and field keys.  Physical SQL
identifiers are loaded only from the server-owned registry created by Alembic;
callers can never supply a schema, table, column, tenant or connection string.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import text

from app.db.session import tenant_session
from app.services.digital_asset_hosting import (
    WORKSPACE_QUOTA_STEP_MB,
    workspace_entry_path,
    workspace_entry_url,
)
from app.terminal import legacy_catalog

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext


_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_RESOURCE_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_ORIGINS = frozenset({"auto_runtime", "manual_ui", "api", "terminal", "super_terminal"})


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, UUID)):
        return value.isoformat() if isinstance(value, datetime) else str(value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _digest(value: object) -> str:
    encoded = json.dumps(
        _json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _identifier(value: object) -> str:
    candidate = str(value or "")
    if not _IDENTIFIER_RE.fullmatch(candidate):
        raise RuntimeError("invalid server-owned resource registry identifier")
    return f'"{candidate}"'


def _resource_key(value: object) -> str:
    candidate = str(value or "").strip().lower()
    if not _RESOURCE_KEY_RE.fullmatch(candidate):
        raise HTTPException(status_code=422, detail="Invalid resource key")
    return candidate


def _registry_definition(session: Session, resource_key: object) -> dict[str, object]:
    key = _resource_key(resource_key)
    resource = (
        session.execute(
            text(
                """
                SELECT * FROM app.resource_types
                WHERE resource_key = :resource_key AND active
                """
            ),
            {"resource_key": key},
        )
        .mappings()
        .one_or_none()
    )
    if resource is None:
        raise HTTPException(status_code=404, detail="Semantic resource is not registered")
    fields = [
        dict(row)
        for row in session.execute(
            text(
                """
                SELECT * FROM app.resource_fields
                WHERE resource_key = :resource_key AND active
                ORDER BY display_order, field_key
                """
            ),
            {"resource_key": key},
        )
        .mappings()
        .all()
    ]
    return {"resource": dict(resource), "fields": fields}


def _public_field(field: dict[str, object]) -> dict[str, object]:
    return {
        "field_key": str(field["field_key"]),
        "label": str(field["label"]),
        "description": str(field.get("semantic_description") or ""),
        "data_type": str(field["data_type"]),
        "format": field.get("data_format"),
        "nullable": bool(field["nullable"]),
        "editable_mode": str(field["editable_mode"]),
        "sensitivity": str(field["sensitivity"]),
        "constraints": dict(field.get("constraints") or {}),
        "examples": list(field.get("examples") or []),
    }


def _public_resource(resource: dict[str, object]) -> dict[str, object]:
    return {
        "resource_key": str(resource["resource_key"]),
        "schema_version": int(resource["schema_version"]),
        "label": str(resource["label"]),
        "description": str(resource.get("description") or ""),
        "identity_fields": list(resource.get("identity_fields") or []),
        "allowed_effects": list(resource.get("allowed_effects") or []),
        "storage_adapter": str(resource["storage_adapter"]),
    }


def list_resources(actor: ActorContext) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                """
                SELECT rt.*,
                       COUNT(rf.field_key) FILTER (WHERE rf.active)::integer AS field_count,
                       COUNT(rf.field_key) FILTER (
                         WHERE rf.active AND rf.editable_mode = 'direct'
                       )::integer AS direct_field_count
                FROM app.resource_types AS rt
                LEFT JOIN app.resource_fields AS rf
                  ON rf.resource_key = rt.resource_key
                WHERE rt.active
                GROUP BY rt.resource_key
                ORDER BY rt.resource_key
                """
            )
        ).mappings().all()
    items = [
        {
            **_public_resource(dict(row)),
            "field_count": int(row["field_count"] or 0),
            "direct_field_count": int(row["direct_field_count"] or 0),
        }
        for row in rows
    ]
    return {"ok": True, "scope": "current_tenant_only", "items": items, "total": len(items)}


def resource_schema(actor: ActorContext, resource_key: object) -> dict[str, object]:
    with tenant_session(actor.tenant_id) as session:
        definition = _registry_definition(session, resource_key)
        key = str(definition["resource"]["resource_key"])
        relations = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT relation_key, source_resource_key, target_resource_key,
                           source_field_key, target_field_key, cardinality,
                           semantic_description
                    FROM app.resource_relations
                    WHERE active AND (
                      source_resource_key = :resource_key
                      OR target_resource_key = :resource_key
                    )
                    ORDER BY relation_key
                    """
                ),
                {"resource_key": key},
            )
            .mappings()
            .all()
        ]
        invariants = [
            _json_safe(dict(row))
            for row in session.execute(
                text(
                    """
                    SELECT invariant_key, description, enforcement, machine_contract
                    FROM app.resource_invariants
                    WHERE resource_key = :resource_key AND active
                    ORDER BY invariant_key
                    """
                ),
                {"resource_key": key},
            )
            .mappings()
            .all()
        ]
    return {
        "ok": True,
        "resource": _public_resource(definition["resource"]),
        "fields": [_public_field(field) for field in definition["fields"]],
        "relations": relations,
        "invariants": invariants,
        "decision_contract": {
            "direct": "AI may use the generic mutation gateway",
            "adapter_only": "AI must select or request a native domain adapter",
            "derived": "read-only state maintained from verified operations",
            "immutable": "stable identity; create a new resource when replacement is intended",
        },
    }


def resource_atlas(actor: ActorContext) -> list[dict[str, object]]:
    """Return the compact, all-resource index used by L0 model routing."""
    return list(list_resources(actor)["items"])


def list_mutations(
    actor: ActorContext,
    *,
    resource_key: str | None = None,
    resource_ref: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    bounded_limit = max(1, min(int(limit), 500))
    clauses = ["tenant_id = :tenant_id"]
    params: dict[str, object] = {
        "tenant_id": actor.tenant_id,
        "limit": bounded_limit,
    }
    if resource_key:
        clauses.append("resource_key = :resource_key")
        params["resource_key"] = _resource_key(resource_key)
    if resource_ref:
        clauses.append("resource_ref = :resource_ref")
        params["resource_ref"] = str(resource_ref).strip()
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                f"""
                SELECT id, operation_id, actor_user_id, run_id, conversation_id,
                       execution_identity, origin, coverage, resource_key,
                       resource_id, resource_ref, effect, status, intent,
                       reasoning_summary, requested_changes, before_state,
                       after_state, expected_version, committed_version,
                       verification, error, created_at, committed_at
                FROM secretariat.data_mutations
                WHERE {' AND '.join(clauses)}
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
    items = [_json_safe(dict(row)) for row in rows]
    return {"ok": True, "items": items, "total": len(items), "limit": bounded_limit}


def list_capability_gaps(
    actor: ActorContext,
    *,
    gap_status: str | None = None,
    limit: int = 100,
) -> dict[str, object]:
    bounded_limit = max(1, min(int(limit), 500))
    params: dict[str, object] = {"tenant_id": actor.tenant_id, "limit": bounded_limit}
    condition = "tenant_id = :tenant_id"
    if gap_status:
        normalized_status = str(gap_status).strip().lower()
        if normalized_status not in {"observed", "reviewing", "promoted", "dismissed"}:
            raise HTTPException(status_code=422, detail="Invalid capability gap status")
        condition += " AND status = :status"
        params["status"] = normalized_status
    with tenant_session(actor.tenant_id) as session:
        rows = session.execute(
            text(
                f"""
                SELECT id, fingerprint, resource_key, capability_key,
                       domain_key, effect, field_set, semantic_contract,
                       last_error,
                       occurrence_count, examples, suggested_tool_name,
                       promotion_reason, status, promoted_tool_name,
                       first_seen_at, last_seen_at
                FROM terminal.capability_gaps
                WHERE {condition}
                ORDER BY occurrence_count DESC, last_seen_at DESC
                LIMIT :limit
                """
            ),
            params,
        ).mappings().all()
    items = [_json_safe(dict(row)) for row in rows]
    return {"ok": True, "items": items, "total": len(items), "limit": bounded_limit}


def record_missing_capability_gap(
    actor: ActorContext,
    *,
    entry: dict[str, object],
    arguments: dict[str, object],
    origin: str,
    reason: str,
) -> dict[str, object] | None:
    """Persist a truthful missing-adapter observation without prescribing recovery.

    Capability concepts may precede their semantic-resource registration.  The
    gap ledger therefore accepts a capability key with an optional resource;
    Auto Runtime remains responsible for choosing generic data, another
    adapter, partial completion, or a human question.
    """

    tool_name = str(entry.get("tool_name") or "").strip()
    if not tool_name:
        return None
    semantic_contract = dict(entry.get("semantic_contract") or {})
    declared_resource = str(semantic_contract.get("resource") or "").strip()
    effect = str(
        semantic_contract.get("effect")
        or ("write" if bool(entry.get("writes")) else "read")
    )[:120]
    domain_key = str(entry.get("domain") or "").strip() or None
    if domain_key is None:
        try:
            domain_key = str(
                legacy_catalog.capability_summary(entry)["category"]
            ).strip() or None
        except (KeyError, TypeError, ValueError):
            domain_key = None
    safe_arguments = {
        str(key): (
            "[redacted]"
            if any(
                secret in str(key).lower()
                for secret in ("password", "secret", "token", "credential", "passkey", "sql")
            )
            else _json_safe(value)
        )
        for key, value in arguments.items()
    }
    fingerprint = _digest(
        {
            "tenant_id": str(actor.tenant_id),
            "capability": tool_name,
            "resource": declared_resource or None,
            "effect": effect,
        }
    )
    example = {
        "origin": origin if origin in _ORIGINS else "api",
        "arguments": safe_arguments,
        "reason": str(reason)[:1000],
        "observed_at": datetime.now(UTC).isoformat(),
    }
    with tenant_session(actor.tenant_id) as session:
        resource_key = None
        if declared_resource and declared_resource != "any_registered_resource":
            resource_key = session.execute(
                text(
                    """
                    SELECT resource_key FROM app.resource_types
                    WHERE resource_key = :resource_key AND active
                    """
                ),
                {"resource_key": declared_resource},
            ).scalar_one_or_none()
        row = session.execute(
            text(
                """
                INSERT INTO terminal.capability_gaps(
                  id, tenant_id, fingerprint, resource_key, capability_key,
                  domain_key, effect, field_set, examples,
                  suggested_tool_name, promotion_reason, semantic_contract,
                  last_error
                ) VALUES (
                  :id, :tenant_id, :fingerprint, :resource_key, :capability_key,
                  :domain_key, :effect, '[]'::jsonb, CAST(:examples AS jsonb),
                  :suggested_tool_name,
                  'A discovered capability has no truthful executable adapter; '
                  'Auto Runtime may use registered semantic data or another atomic ability.',
                  CAST(:semantic_contract AS jsonb), CAST(:last_error AS jsonb)
                )
                ON CONFLICT (tenant_id, fingerprint)
                DO UPDATE SET
                  occurrence_count = terminal.capability_gaps.occurrence_count + 1,
                  last_seen_at = now(),
                  semantic_contract = EXCLUDED.semantic_contract,
                  last_error = EXCLUDED.last_error,
                  examples = CASE
                    WHEN jsonb_array_length(terminal.capability_gaps.examples) < 5
                    THEN terminal.capability_gaps.examples || EXCLUDED.examples
                    ELSE terminal.capability_gaps.examples
                  END
                RETURNING id, fingerprint, occurrence_count, status
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "fingerprint": fingerprint,
                "resource_key": resource_key,
                "capability_key": tool_name,
                "domain_key": domain_key,
                "effect": effect,
                "examples": json.dumps([example], ensure_ascii=False, default=str),
                "suggested_tool_name": tool_name[:128],
                "semantic_contract": json.dumps(semantic_contract, ensure_ascii=False),
                "last_error": json.dumps(
                    {"reason": str(reason)[:2000], "origin": origin},
                    ensure_ascii=False,
                ),
            },
        ).mappings().one()
    return {
        "id": str(row["id"]),
        "fingerprint": str(row["fingerprint"]),
        "capability_key": tool_name,
        "resource_key": resource_key,
        "effect": effect,
        "occurrence_count": int(row["occurrence_count"]),
        "status": str(row["status"]),
    }


def _table_name(resource: dict[str, object]) -> str:
    return f"{_identifier(resource['storage_schema'])}.{_identifier(resource['storage_table'])}"


def _field_map(definition: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(field["field_key"]): field for field in definition["fields"]}


def _resolve_row(
    session: Session,
    definition: dict[str, object],
    ref: object,
    *,
    lock: bool = False,
) -> dict[str, object]:
    resource = definition["resource"]
    fields = _field_map(definition)
    identity_fields = [str(item) for item in resource.get("identity_fields") or []]
    predicates: list[str] = []
    for field_key in identity_fields:
        field = fields.get(field_key)
        column_name = field.get("storage_column") if field else field_key
        predicates.append(f"CAST({_identifier(column_name)} AS text) = :resource_ref")
    if not predicates:
        predicates.append(
            f"CAST({_identifier(resource['id_column'])} AS text) = :resource_ref"
        )
    suffix = " FOR UPDATE" if lock else ""
    rows = (
        session.execute(
            text(
                f"""
                SELECT * FROM {_table_name(resource)}
                WHERE {_identifier(resource['tenant_column'])} = :tenant_id
                  AND ({' OR '.join(predicates)})
                LIMIT 3{suffix}
                """
            ),
            {"tenant_id": session.info.get("tenant_id"), "resource_ref": str(ref).strip()},
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Resource not found")
    if len(rows) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "reason": "resource_ref_ambiguous",
                "resource": resource["resource_key"],
                "ref": str(ref),
                "matches": len(rows),
            },
        )
    return dict(rows[0])


def _extract_value(row: dict[str, object], field: dict[str, object]) -> object:
    value = row.get(str(field["storage_column"]))
    for part in field.get("json_path") or []:
        if not isinstance(value, dict):
            return None
        value = value.get(str(part))
    if str(field.get("sensitivity")) == "credential" and value not in (None, ""):
        return "[redacted]"
    return _json_safe(value)


def _version(resource: dict[str, object], row: dict[str, object]) -> object:
    column = resource.get("version_column")
    return _json_safe(row.get(str(column))) if column else None


def _state(definition: dict[str, object], row: dict[str, object]) -> dict[str, object]:
    resource = definition["resource"]
    return {
        "resource": str(resource["resource_key"]),
        "resource_id": str(row[resource["id_column"]]),
        "version": _version(resource, row),
        "data": {
            str(field["field_key"]): _extract_value(row, field)
            for field in definition["fields"]
        },
    }


def resolve_resource(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    resource_key = payload.get("resource") or payload.get("resource_key")
    ref = payload.get("ref") or payload.get("resource_ref")
    if ref in (None, ""):
        raise HTTPException(status_code=422, detail="resource ref is required")
    with tenant_session(actor.tenant_id) as session:
        session.info["tenant_id"] = actor.tenant_id
        definition = _registry_definition(session, resource_key)
        row = _resolve_row(session, definition, ref)
        result = _state(definition, row)
    return {"ok": True, **result}


def _relation_value(
    definition: dict[str, object], row: dict[str, object], field_key: str
) -> object:
    field = _field_map(definition).get(field_key)
    if field is None:
        # Relation definitions are server-owned registry data.  A relation may
        # reference a structural foreign key that is intentionally omitted
        # from ordinary presentation fields.
        return row.get(field_key)
    value = row.get(str(field["storage_column"]))
    for part in field.get("json_path") or []:
        if not isinstance(value, dict):
            return None
        value = value.get(str(part))
    return value


def _relation_column(definition: dict[str, object], field_key: str) -> str:
    field = _field_map(definition).get(field_key)
    if field is None:
        return _identifier(field_key)
    if field.get("json_path"):
        raise RuntimeError("relations through JSON paths are not supported")
    return _identifier(field["storage_column"])


def observe_resource_graph(
    actor: ActorContext, payload: dict[str, object]
) -> dict[str, object]:
    """Observe one tenant resource and its registered neighbourhood.

    Traversal is driven entirely by the semantic registry.  There are no
    domain routes such as "workspace then database then key" in this engine;
    adding a registered resource or relation automatically expands the world
    that Auto Runtime can observe.
    """

    resource_key = payload.get("resource") or payload.get("resource_key")
    ref = payload.get("ref") or payload.get("resource_ref")
    if ref in (None, ""):
        raise HTTPException(status_code=422, detail="resource ref is required")
    try:
        max_depth = max(0, min(int(payload.get("depth") or 1), 2))
        relation_limit = max(1, min(int(payload.get("relation_limit") or 50), 200))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid graph bounds") from exc

    with tenant_session(actor.tenant_id) as session:
        session.info["tenant_id"] = actor.tenant_id
        root_definition = _registry_definition(session, resource_key)
        root_row = _resolve_row(session, root_definition, ref)
        def enrich_observation(state: dict[str, object]) -> dict[str, object]:
            if state.get("resource") != "digital_asset.workspace":
                return state
            data = state.get("data")
            if not isinstance(data, dict) or not data.get("workspace_key"):
                return state
            key = str(data["workspace_key"])
            data.update(
                {
                    "entry_path": workspace_entry_path(actor.tenant_slug, key),
                    "entry_url": workspace_entry_url(actor.tenant_slug, key),
                    "hosting_url": workspace_entry_url(actor.tenant_slug, key),
                    "hosting_url_status": "active",
                    "application_url": data.get("public_url"),
                    "entry_kind": (
                        "deployed_application"
                        if data.get("public_url")
                        else "workspace_status"
                    ),
                    "next_quota_increment_mb": WORKSPACE_QUOTA_STEP_MB,
                }
            )
            return state

        root_state = enrich_observation(_state(root_definition, root_row))
        queue: list[tuple[int, dict[str, object], dict[str, object]]] = [
            (0, root_definition, root_row)
        ]
        visited = {
            (
                str(root_state["resource"]),
                str(root_state["resource_id"]),
            )
        }
        entities: list[dict[str, object]] = [
            {**root_state, "depth": 0, "root": True}
        ]
        edges: list[dict[str, object]] = []
        relation_observations: list[dict[str, object]] = []

        while queue:
            depth, definition, row = queue.pop(0)
            if depth >= max_depth:
                continue
            current_key = str(definition["resource"]["resource_key"])
            relations = session.execute(
                text(
                    """
                    SELECT * FROM app.resource_relations
                    WHERE active AND (
                      source_resource_key = :resource_key
                      OR target_resource_key = :resource_key
                    )
                    ORDER BY relation_key
                    """
                ),
                {"resource_key": current_key},
            ).mappings().all()
            for relation_row in relations:
                relation = dict(relation_row)
                outgoing = relation["source_resource_key"] == current_key
                current_field = str(
                    relation["source_field_key"]
                    if outgoing
                    else relation["target_field_key"]
                )
                other_key = str(
                    relation["target_resource_key"]
                    if outgoing
                    else relation["source_resource_key"]
                )
                other_field = str(
                    relation["target_field_key"]
                    if outgoing
                    else relation["source_field_key"]
                )
                join_value = _relation_value(definition, row, current_field)
                if join_value is None:
                    continue
                current_id = str(row[definition["resource"]["id_column"]])
                other_definition = _registry_definition(session, other_key)
                other_resource = other_definition["resource"]
                related_rows = session.execute(
                    text(
                        f"""
                        SELECT * FROM {_table_name(other_resource)}
                        WHERE {_identifier(other_resource['tenant_column'])} = :tenant_id
                          AND {_relation_column(other_definition, other_field)} = :join_value
                        ORDER BY {
                            _identifier(
                                other_resource.get("version_column")
                                or other_resource["id_column"]
                            )
                        } DESC
                        LIMIT :limit
                        """
                    ),
                    {
                        "tenant_id": actor.tenant_id,
                        "join_value": join_value,
                        "limit": relation_limit,
                    },
                ).mappings().all()
                relation_observations.append(
                    {
                        "relation": str(relation["relation_key"]),
                        "direction": "outgoing" if outgoing else "incoming",
                        "from": {"resource": current_key, "id": current_id},
                        "related_resource": other_key,
                        "matched_count": len(related_rows),
                        "complete_within_limit": len(related_rows) < relation_limit,
                    }
                )
                for related_row in related_rows:
                    related_dict = dict(related_row)
                    related_state = enrich_observation(
                        _state(other_definition, related_dict)
                    )
                    related_id = str(related_state["resource_id"])
                    source = (
                        {"resource": current_key, "id": current_id}
                        if outgoing
                        else {"resource": other_key, "id": related_id}
                    )
                    target = (
                        {"resource": other_key, "id": related_id}
                        if outgoing
                        else {"resource": current_key, "id": current_id}
                    )
                    edge_key = (
                        str(relation["relation_key"]),
                        source["resource"],
                        source["id"],
                        target["resource"],
                        target["id"],
                    )
                    if not any(
                        (
                            item["relation"],
                            item["source"]["resource"],
                            item["source"]["id"],
                            item["target"]["resource"],
                            item["target"]["id"],
                        )
                        == edge_key
                        for item in edges
                    ):
                        edges.append(
                            {
                                "relation": str(relation["relation_key"]),
                                "cardinality": str(relation["cardinality"]),
                                "description": str(
                                    relation.get("semantic_description") or ""
                                ),
                                "source": source,
                                "target": target,
                            }
                        )
                    entity_key = (other_key, related_id)
                    if entity_key in visited:
                        continue
                    visited.add(entity_key)
                    entities.append(
                        {**related_state, "depth": depth + 1, "root": False}
                    )
                    queue.append((depth + 1, other_definition, related_dict))

    grouped: dict[str, list[dict[str, object]]] = {}
    for entity in entities:
        grouped.setdefault(str(entity["resource"]), []).append(entity)
    return {
        "ok": True,
        "scope": "current_tenant_only",
        "observed_at": datetime.now(UTC).isoformat(),
        "root": root_state,
        "depth": max_depth,
        "entities": entities,
        "entities_by_resource": grouped,
        "relations": edges,
        "relation_observations": relation_observations,
        "empty_related_resources": sorted(
            {
                str(item["related_resource"])
                for item in relation_observations
                if int(item["matched_count"]) == 0
            }
        ),
        "entity_count": len(entities),
        "relation_count": len(edges),
        "world_observation": {
            "schema": "warehouse.world-observation.v1",
            "operation": "semantic_resource_graph.observe",
            "effect": "read",
            "primary_entity": root_state,
            "related_entities": entities[1:],
            "verified_facts": {
                "tenant_scope_enforced": True,
                "registry_driven_traversal": True,
                "entity_count": len(entities),
                "relation_count": len(edges),
                "empty_relation_count": sum(
                    1
                    for item in relation_observations
                    if int(item["matched_count"]) == 0
                ),
            },
            "uncertainties": [],
            "affordances": [],
            "decision_owner": "auto_runtime",
            "workflow_prescribed": False,
        },
    }


def _filter_expression(field: dict[str, object], param: str) -> str:
    column = _identifier(field["storage_column"])
    json_path = [str(item) for item in field.get("json_path") or []]
    if json_path:
        path = ",".join(json_path)
        return f"{column} #> '{{{path}}}' = CAST(:{param} AS jsonb)"
    if str(field["data_type"]) in {"array", "object"}:
        return f"{column} = CAST(:{param} AS jsonb)"
    return f"{column} = :{param}"


def query_resources(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    resource_key = payload.get("resource") or payload.get("resource_key")
    filters = payload.get("filters") or {}
    if not isinstance(filters, dict):
        raise HTTPException(status_code=422, detail="filters must be an object")
    try:
        limit = max(1, min(int(payload.get("limit") or 100), 500))
        offset = max(0, int(payload.get("offset") or 0))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid pagination") from exc
    with tenant_session(actor.tenant_id) as session:
        session.info["tenant_id"] = actor.tenant_id
        definition = _registry_definition(session, resource_key)
        resource = definition["resource"]
        fields = _field_map(definition)
        clauses = [f"{_identifier(resource['tenant_column'])} = :tenant_id"]
        params: dict[str, object] = {
            "tenant_id": actor.tenant_id,
            "limit": limit,
            "offset": offset,
        }
        for index, (field_key, raw_value) in enumerate(filters.items()):
            field = fields.get(str(field_key))
            if field is None:
                raise HTTPException(status_code=422, detail=f"Unknown field: {field_key}")
            value = _validated_value(field, raw_value)
            param = f"filter_{index}"
            clauses.append(_filter_expression(field, param))
            params[param] = (
                json.dumps(value, ensure_ascii=False)
                if field.get("json_path") or str(field["data_type"]) in {"array", "object"}
                else value
            )
        order_column = resource.get("version_column") or resource["id_column"]
        rows = session.execute(
            text(
                f"""
                SELECT * FROM {_table_name(resource)}
                WHERE {' AND '.join(clauses)}
                ORDER BY {_identifier(order_column)} DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings().all()
        items = [_state(definition, dict(row)) for row in rows]
    return {
        "ok": True,
        "resource": str(resource["resource_key"]),
        "items": items,
        "total": len(items),
        "limit": limit,
        "offset": offset,
    }


def _validated_value(field: dict[str, object], value: object) -> object:
    key = str(field["field_key"])
    if value is None:
        if bool(field["nullable"]):
            return None
        raise HTTPException(status_code=422, detail=f"{key} cannot be null")
    data_type = str(field["data_type"])
    if data_type in {"string", "uuid", "datetime"}:
        if not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"{key} must be a string")
        value = value.strip()
        if data_type == "uuid":
            try:
                UUID(value)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{key} must be a UUID") from exc
        if data_type == "datetime":
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=f"{key} must be ISO 8601") from exc
    elif data_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(status_code=422, detail=f"{key} must be an integer")
    elif data_type == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(status_code=422, detail=f"{key} must be a number")
    elif data_type == "boolean" and not isinstance(value, bool):
        raise HTTPException(status_code=422, detail=f"{key} must be a boolean")
    elif data_type == "array" and not isinstance(value, list):
        raise HTTPException(status_code=422, detail=f"{key} must be an array")
    elif data_type == "object" and not isinstance(value, dict):
        raise HTTPException(status_code=422, detail=f"{key} must be an object")

    constraints = dict(field.get("constraints") or {})
    if value is not None and "enum" in constraints and value not in constraints["enum"]:
        raise HTTPException(
            status_code=422,
            detail={"field": key, "reason": "invalid_enum", "allowed": constraints["enum"]},
        )
    if isinstance(value, str):
        minimum = constraints.get("min_length")
        maximum = constraints.get("max_length")
        if minimum is not None and len(value) < int(minimum):
            raise HTTPException(status_code=422, detail=f"{key} is too short")
        if maximum is not None and len(value) > int(maximum):
            raise HTTPException(status_code=422, detail=f"{key} is too long")
        pattern = constraints.get("pattern")
        if pattern and not re.fullmatch(str(pattern), value):
            raise HTTPException(status_code=422, detail=f"{key} has an invalid format")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if constraints.get("minimum") is not None and value < float(constraints["minimum"]):
            raise HTTPException(status_code=422, detail=f"{key} is below minimum")
        if constraints.get("maximum") is not None and value > float(constraints["maximum"]):
            raise HTTPException(status_code=422, detail=f"{key} is above maximum")
        multiple_of = constraints.get("multiple_of")
        if multiple_of is not None and value % int(multiple_of) != 0:
            raise HTTPException(
                status_code=422,
                detail={
                    "field": key,
                    "reason": "invalid_increment",
                    "multiple_of": int(multiple_of),
                },
            )
    return value


def _prepare_changes(
    definition: dict[str, object], changes: object
) -> tuple[dict[str, object], list[dict[str, object]]]:
    if not isinstance(changes, dict) or not changes:
        raise HTTPException(status_code=422, detail="changes must be a non-empty object")
    fields = _field_map(definition)
    accepted: dict[str, object] = {}
    blocked: list[dict[str, object]] = []
    for raw_key, raw_value in changes.items():
        key = str(raw_key)
        field = fields.get(key)
        if field is None:
            raise HTTPException(status_code=422, detail=f"Unknown field: {key}")
        mode = str(field["editable_mode"])
        if mode != "direct":
            blocked.append(
                {
                    "field": key,
                    "mode": mode,
                    "reason": str(field.get("semantic_description") or ""),
                }
            )
            continue
        accepted[key] = _validated_value(field, raw_value)
    return accepted, blocked


def _version_matches(expected: object, current: object) -> bool:
    if expected is None:
        return True
    return str(expected).strip() == str(current).strip()


def _mutation_world_observation(
    *,
    operation: str,
    effect: str,
    state: dict[str, object],
    verified_facts: dict[str, object],
    uncertainties: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema": "warehouse.world-observation.v1",
        "operation": operation,
        "effect": effect,
        "primary_entity": {
            "resource": state["resource"],
            "id": state["resource_id"],
            "ref": state.get("resource_ref"),
            "facts": state.get("data") or {},
        },
        "related_entities": [],
        "verified_facts": verified_facts,
        "uncertainties": uncertainties or [],
        "affordances": [],
        "decision_owner": "auto_runtime",
        "workflow_prescribed": False,
    }


def preview_mutation(actor: ActorContext, payload: dict[str, object]) -> dict[str, object]:
    resource_key = payload.get("resource") or payload.get("resource_key")
    ref = payload.get("ref") or payload.get("resource_ref")
    if ref in (None, ""):
        raise HTTPException(status_code=422, detail="resource ref is required")
    with tenant_session(actor.tenant_id) as session:
        session.info["tenant_id"] = actor.tenant_id
        definition = _registry_definition(session, resource_key)
        row = _resolve_row(session, definition, ref)
        current = _state(definition, row)
        accepted, blocked = _prepare_changes(definition, payload.get("changes"))
        diff = {
            key: {"before": current["data"].get(key), "after": _json_safe(value)}
            for key, value in accepted.items()
            if current["data"].get(key) != _json_safe(value)
        }
        current_version = current["version"]
        expected_version = payload.get("expected_version")
        version_matches = _version_matches(expected_version, current_version)
        invariants = resource_schema(actor, resource_key)["invariants"]
    result = {
        "ok": True,
        "preview": True,
        "resource": current["resource"],
        "resource_id": current["resource_id"],
        "resource_ref": str(ref),
        "current_version": current_version,
        "expected_version": expected_version,
        "version_matches": version_matches,
        "diff": diff,
        "blocked_fields": blocked,
        "invariants": invariants,
        "can_commit": bool(diff) and not blocked and version_matches,
        "configuration_only": (
            current["resource"] == "digital_asset.workspace"
            and set(diff).issubset({"runtime_type", "region", "public_url", "storage_quota_bytes"})
        ),
        "judgment": {
            "decision_owner": "company_ai",
            "preview_is_not_confirmation": True,
            "native_adapter_required": bool(blocked),
        },
    }
    result["world_observation"] = _mutation_world_observation(
        operation="semantic_resource.update.preview",
        effect="read",
        state={**current, "resource_ref": str(ref)},
        verified_facts={
            "preview_only": True,
            "version_matches": version_matches,
            "direct_fields_only": not blocked,
        },
        uncertainties=[
            {
                "fact": "mutation_committed",
                "state": "not_observed",
                "meaning": "preview does not change the database",
            }
        ],
    )
    return result


def _assignment_sql(
    definition: dict[str, object], changes: dict[str, object]
) -> tuple[list[str], dict[str, object]]:
    fields = _field_map(definition)
    assignments: list[str] = []
    params: dict[str, object] = {}
    json_expressions: dict[str, str] = {}
    for index, (key, value) in enumerate(changes.items()):
        field = fields[key]
        column_name = str(field["storage_column"])
        column = _identifier(column_name)
        param = f"change_{index}"
        json_path = [str(item) for item in field.get("json_path") or []]
        if json_path:
            if any(not _IDENTIFIER_RE.fullmatch(item) for item in json_path):
                raise RuntimeError("invalid server-owned JSON path")
            base = json_expressions.get(column_name, f"COALESCE({column}, '{{}}'::jsonb)")
            path = ",".join(json_path)
            json_expressions[column_name] = (
                f"jsonb_set({base}, '{{{path}}}', CAST(:{param} AS jsonb), true)"
            )
            params[param] = json.dumps(value, ensure_ascii=False)
        elif str(field["data_type"]) in {"array", "object"}:
            assignments.append(f"{column} = CAST(:{param} AS jsonb)")
            params[param] = json.dumps(value, ensure_ascii=False)
        else:
            assignments.append(f"{column} = :{param}")
            params[param] = value
    assignments.extend(
        f"{_identifier(column_name)} = {expression}"
        for column_name, expression in json_expressions.items()
    )
    resource = definition["resource"]
    if resource.get("version_strategy") == "integer" and resource.get("version_column"):
        version_column = _identifier(resource["version_column"])
        assignments.append(f"{version_column} = {version_column} + 1")
    return assignments, params


def _idempotent_result(session: Session, actor: ActorContext, key: str) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT * FROM secretariat.data_mutations
                WHERE tenant_id = :tenant_id AND idempotency_key = :idempotency_key
                """
            ),
            {"tenant_id": actor.tenant_id, "idempotency_key": key},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return {
        "ok": str(row["status"]) == "succeeded",
        "idempotent_replay": True,
        "mutation_id": str(row["id"]),
        "operation_id": str(row["operation_id"]),
        "resource": str(row["resource_key"]),
        "resource_id": str(row["resource_id"]),
        "resource_ref": str(row["resource_ref"]),
        "status": str(row["status"]),
        "version": row["committed_version"],
        "data": _json_safe(dict(row["after_state"] or {})),
        "verification": _json_safe(dict(row["verification"] or {})),
    }


def commit_mutation(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    origin: str = "api",
) -> dict[str, object]:
    resource_key = payload.get("resource") or payload.get("resource_key")
    ref = payload.get("ref") or payload.get("resource_ref")
    if ref in (None, ""):
        raise HTTPException(status_code=422, detail="resource ref is required")
    normalized_origin = origin if origin in _ORIGINS else "api"
    supplied_key = str(payload.get("idempotency_key") or "").strip()
    idempotency_key = supplied_key or f"gm_{uuid4().hex}"
    if len(idempotency_key) < 8 or len(idempotency_key) > 240:
        raise HTTPException(status_code=422, detail="Invalid idempotency_key")

    with tenant_session(actor.tenant_id) as session:
        session.info["tenant_id"] = actor.tenant_id
        replay = _idempotent_result(session, actor, idempotency_key)
        if replay is not None:
            return replay
        definition = _registry_definition(session, resource_key)
        resource = definition["resource"]
        if "update" not in list(resource.get("allowed_effects") or []):
            raise HTTPException(status_code=409, detail="Resource does not support generic update")
        row = _resolve_row(session, definition, ref, lock=True)
        before = _state(definition, row)
        accepted, blocked = _prepare_changes(definition, payload.get("changes"))
        if blocked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "reason": "native_adapter_required",
                    "resource": resource["resource_key"],
                    "blocked_fields": blocked,
                },
            )
        actual_changes = {
            key: value
            for key, value in accepted.items()
            if before["data"].get(key) != _json_safe(value)
        }
        expected_version = payload.get("expected_version")
        if not _version_matches(expected_version, before["version"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "reason": "version_conflict",
                    "expected_version": expected_version,
                    "current_version": before["version"],
                },
            )
        if not actual_changes:
            unchanged = {
                "ok": True,
                "changed": False,
                "resource": before["resource"],
                "resource_id": before["resource_id"],
                "resource_ref": str(ref),
                "version": before["version"],
                "data": before["data"],
                "verification": {"read_back": True, "matches_requested_changes": True},
            }
            unchanged["world_observation"] = _mutation_world_observation(
                operation="semantic_resource.update",
                effect="none",
                state={**before, "resource_ref": str(ref)},
                verified_facts={
                    "database_changed": False,
                    "requested_state_already_present": True,
                    "read_back_verified": True,
                },
            )
            return unchanged

        assignments, params = _assignment_sql(definition, actual_changes)
        params["resource_id"] = row[resource["id_column"]]
        updated = dict(
            session.execute(
                text(
                    f"""
                    UPDATE {_table_name(resource)}
                    SET {', '.join(assignments)}
                    WHERE {_identifier(resource['id_column'])} = :resource_id
                    RETURNING *
                    """
                ),
                params,
            )
            .mappings()
            .one()
        )
        after = _state(definition, updated)
        verified = all(
            after["data"].get(key) == _json_safe(value)
            for key, value in actual_changes.items()
        )
        if not verified:
            raise RuntimeError("generic mutation read-back verification failed")

        mutation_id = uuid4()
        operation_id = uuid4()
        now = datetime.now(UTC)
        before_state = dict(before["data"])
        after_state = dict(after["data"])
        session.execute(
            text(
                """
                INSERT INTO secretariat.data_mutations(
                  id, tenant_id, actor_user_id, run_id, conversation_id,
                  operation_id, execution_identity, origin, coverage,
                  resource_key, resource_id, resource_ref, effect, status,
                  intent, reasoning_summary, requested_changes,
                  before_state, after_state, before_digest, after_digest,
                  expected_version, committed_version, idempotency_key,
                  authorization_keychain_id, verification, committed_at
                ) VALUES (
                  :id, :tenant_id, :actor_user_id, :run_id, :conversation_id,
                  :operation_id, :execution_identity, :origin, 'command_missing',
                  :resource_key, :resource_id, :resource_ref, 'update', 'succeeded',
                  :intent, :reasoning_summary, CAST(:requested_changes AS jsonb),
                  CAST(:before_state AS jsonb), CAST(:after_state AS jsonb),
                  :before_digest, :after_digest, :expected_version,
                  :committed_version, :idempotency_key,
                  :authorization_keychain_id, CAST(:verification AS jsonb), :committed_at
                )
                """
            ),
            {
                "id": mutation_id,
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "run_id": _uuid_or_none(payload.get("run_id")),
                "conversation_id": _uuid_or_none(payload.get("conversation_id")),
                "operation_id": operation_id,
                "execution_identity": (
                    "company_ai" if normalized_origin == "auto_runtime" else "requesting_user"
                ),
                "origin": normalized_origin,
                "resource_key": resource["resource_key"],
                "resource_id": after["resource_id"],
                "resource_ref": str(ref),
                "intent": str(payload.get("intent") or "")[:4000],
                "reasoning_summary": str(payload.get("reasoning_summary") or "")[:4000],
                "requested_changes": json.dumps(
                    _json_safe(actual_changes), ensure_ascii=False, sort_keys=True
                ),
                "before_state": json.dumps(before_state, ensure_ascii=False, sort_keys=True),
                "after_state": json.dumps(after_state, ensure_ascii=False, sort_keys=True),
                "before_digest": _digest(before_state),
                "after_digest": _digest(after_state),
                "expected_version": (
                    str(expected_version) if expected_version is not None else None
                ),
                "committed_version": str(after["version"]),
                "idempotency_key": idempotency_key,
                "authorization_keychain_id": _uuid_or_none(
                    payload.get("authorization_keychain_id")
                ),
                "verification": json.dumps(
                    {"read_back": True, "matches_requested_changes": True},
                    ensure_ascii=False,
                ),
                "committed_at": now,
            },
        )
        field_set = sorted(actual_changes)
        fingerprint = _digest(
            {
                "tenant_id": str(actor.tenant_id),
                "resource": resource["resource_key"],
                "effect": "update",
                "fields": field_set,
            }
        )
        example = [
            {
                "intent": str(payload.get("intent") or "")[:500],
                "fields": field_set,
                "succeeded": True,
                "at": now.isoformat(),
            }
        ]
        suggested_tool = f"{str(resource['resource_key']).replace('.', '_')}_update"[:128]
        session.execute(
            text(
                """
                INSERT INTO terminal.capability_gaps(
                  id, tenant_id, fingerprint, resource_key, effect, field_set,
                  examples, suggested_tool_name, promotion_reason
                ) VALUES (
                  :id, :tenant_id, :fingerprint, :resource_key, 'update',
                  CAST(:field_set AS jsonb), CAST(:examples AS jsonb),
                  :suggested_tool_name,
                  'Observed successful generic mutations; promote when frequent or transactional.'
                )
                ON CONFLICT (tenant_id, fingerprint)
                DO UPDATE SET
                  occurrence_count = terminal.capability_gaps.occurrence_count + 1,
                  last_seen_at = now(),
                  examples = CASE
                    WHEN jsonb_array_length(terminal.capability_gaps.examples) < 5
                    THEN terminal.capability_gaps.examples || EXCLUDED.examples
                    ELSE terminal.capability_gaps.examples
                  END
                """
            ),
            {
                "id": uuid4(),
                "tenant_id": actor.tenant_id,
                "fingerprint": fingerprint,
                "resource_key": resource["resource_key"],
                "field_set": json.dumps(field_set, ensure_ascii=False),
                "examples": json.dumps(example, ensure_ascii=False),
                "suggested_tool_name": suggested_tool,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'data.generic_mutation.succeeded',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": json.dumps(
                    {
                        "mutation_id": str(mutation_id),
                        "operation_id": str(operation_id),
                        "resource": resource["resource_key"],
                        "resource_id": after["resource_id"],
                        "resource_ref": str(ref),
                        "fields": field_set,
                        "origin": normalized_origin,
                        "coverage": "command_missing",
                        "before_digest": _digest(before_state),
                        "after_digest": _digest(after_state),
                    },
                    ensure_ascii=False,
                ),
            },
        )
    result = {
        "ok": True,
        "changed": True,
        "mutation_id": str(mutation_id),
        "operation_id": str(operation_id),
        "resource": after["resource"],
        "resource_id": after["resource_id"],
        "resource_ref": str(ref),
        "version": after["version"],
        "data": after["data"],
        "coverage": "command_missing",
        "capability_gap": {
            "fingerprint": fingerprint,
            "suggested_tool_name": suggested_tool,
        },
        "verification": {"read_back": True, "matches_requested_changes": True},
    }
    result["world_observation"] = _mutation_world_observation(
        operation="semantic_resource.update",
        effect="update",
        state={**after, "resource_ref": str(ref)},
        verified_facts={
            "database_changed": True,
            "read_back_verified": True,
            "matches_requested_changes": True,
            "coverage": "command_missing",
        },
    )
    return result


def record_mutation_failure(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    origin: str,
    error: object,
    conflict: bool,
) -> None:
    """Best-effort durable rejection audit without changing the API outcome."""

    normalized_origin = origin if origin in _ORIGINS else "api"
    try:
        with tenant_session(actor.tenant_id) as session:
            session.info["tenant_id"] = actor.tenant_id
            definition = _registry_definition(
                session, payload.get("resource") or payload.get("resource_key")
            )
            resource = definition["resource"]
            ref = str(payload.get("ref") or payload.get("resource_ref") or "unresolved")
            try:
                row = _resolve_row(session, definition, ref)
                current = _state(definition, row)
            except HTTPException:
                current = {
                    "resource_id": "unresolved",
                    "version": None,
                    "data": {},
                }
            state = dict(current["data"])
            mutation_id = uuid4()
            operation_id = uuid4()
            supplied_key = str(payload.get("idempotency_key") or "").strip()
            idempotency_key = supplied_key or f"gm_fail_{uuid4().hex}"
            error_text = json.dumps(_json_safe(error), ensure_ascii=False, default=str)[:4000]
            session.execute(
                text(
                    """
                    INSERT INTO secretariat.data_mutations(
                      id, tenant_id, actor_user_id, operation_id,
                      execution_identity, origin, coverage, resource_key,
                      resource_id, resource_ref, effect, status, intent,
                      reasoning_summary, requested_changes, before_state,
                      after_state, before_digest, after_digest,
                      expected_version, committed_version, idempotency_key,
                      verification, error
                    ) VALUES (
                      :id, :tenant_id, :actor_user_id, :operation_id,
                      :execution_identity, :origin, 'command_missing', :resource_key,
                      :resource_id, :resource_ref, 'update', :status, :intent,
                      :reasoning_summary, CAST(:requested_changes AS jsonb),
                      CAST(:before_state AS jsonb), CAST(:after_state AS jsonb),
                      :before_digest, :after_digest, :expected_version,
                      :committed_version, :idempotency_key,
                      CAST(:verification AS jsonb), :error
                    )
                    ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
                    """
                ),
                {
                    "id": mutation_id,
                    "tenant_id": actor.tenant_id,
                    "actor_user_id": actor.user_id,
                    "operation_id": operation_id,
                    "execution_identity": (
                        "company_ai"
                        if normalized_origin == "auto_runtime"
                        else "requesting_user"
                    ),
                    "origin": normalized_origin,
                    "resource_key": resource["resource_key"],
                    "resource_id": current["resource_id"],
                    "resource_ref": ref,
                    "status": "conflict" if conflict else "rejected",
                    "intent": str(payload.get("intent") or "")[:4000],
                    "reasoning_summary": str(
                        payload.get("reasoning_summary") or ""
                    )[:4000],
                    "requested_changes": json.dumps(
                        _json_safe(payload.get("changes") or {}), ensure_ascii=False
                    ),
                    "before_state": json.dumps(state, ensure_ascii=False, sort_keys=True),
                    "after_state": json.dumps(state, ensure_ascii=False, sort_keys=True),
                    "before_digest": _digest(state),
                    "after_digest": _digest(state),
                    "expected_version": (
                        str(payload.get("expected_version"))
                        if payload.get("expected_version") is not None
                        else None
                    ),
                    "committed_version": (
                        str(current["version"])
                        if current.get("version") is not None
                        else None
                    ),
                    "idempotency_key": idempotency_key,
                    "verification": json.dumps(
                        {"read_back": bool(state), "matches_requested_changes": False}
                    ),
                    "error": error_text,
                },
            )
            session.execute(
                text(
                    """
                    INSERT INTO audit.events(
                      tenant_id, actor_user_id, event_type, payload
                    ) VALUES (
                      :tenant_id, :actor_user_id,
                      'data.generic_mutation.rejected', CAST(:payload AS jsonb)
                    )
                    """
                ),
                {
                    "tenant_id": actor.tenant_id,
                    "actor_user_id": actor.user_id,
                    "payload": json.dumps(
                        {
                            "mutation_id": str(mutation_id),
                            "operation_id": str(operation_id),
                            "resource": resource["resource_key"],
                            "resource_id": current["resource_id"],
                            "resource_ref": ref,
                            "origin": normalized_origin,
                            "status": "conflict" if conflict else "rejected",
                            "error": error_text,
                        },
                        ensure_ascii=False,
                    ),
                },
            )
    except Exception:
        # Failure telemetry must never replace the original validation error.
        return


def _uuid_or_none(value: object) -> UUID | None:
    if value in (None, ""):
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="Invalid UUID context reference") from exc
