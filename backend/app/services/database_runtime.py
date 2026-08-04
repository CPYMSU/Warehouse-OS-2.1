"""Company-AI PostgreSQL runtime for autonomous inspection, query and writes.

The model receives the real database world visible to its current company
identity. PostgreSQL privileges, RLS and transaction semantics remain the
authority boundary; the application does not replace AI judgment with a
semantic-table allowlist or a business-specific fallback workflow.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import tenant_readonly_session, tenant_session

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext


_ORIGINS = frozenset({"auto_runtime", "manual_ui", "api", "terminal", "super_terminal"})


def _require_company_database_identity(actor: ActorContext) -> None:
    if "ai.database" not in actor.permissions:
        raise HTTPException(
            status_code=403,
            detail="Current identity does not hold the company AI database capability",
        )


def _require_legacy_read_identity(actor: ActorContext) -> None:
    """Honor the retained read-only DB command without widening write access."""

    if not ({"cli.db.read", "settings.manage", "ai.database"} & set(actor.permissions)):
        raise HTTPException(
            status_code=403,
            detail="Current identity cannot inspect the company database",
        )


def _json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def _statement(value: object) -> str:
    statement = str(value or "").strip()
    if not statement:
        raise HTTPException(status_code=422, detail="sql must not be empty")
    if len(statement) > 100_000:
        raise HTTPException(status_code=422, detail="sql exceeds 100000 characters")
    return statement


def _parameters(value: object) -> dict[str, object]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise HTTPException(status_code=422, detail="parameters must be an object")
    return {str(key): item for key, item in value.items()}


def _bounded_limit(value: object, *, default: int = 200) -> int:
    try:
        return max(1, min(int(value or default), 2_000))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="limit must be an integer") from exc


def _digest(statement: str) -> str:
    return hashlib.sha256(statement.encode("utf-8")).hexdigest()


def _database_error(exc: SQLAlchemyError) -> dict[str, object]:
    original = getattr(exc, "orig", None)
    return {
        "type": type(original or exc).__name__,
        "sqlstate": getattr(original, "sqlstate", None),
        "message": str(original or exc)[:8_000],
    }


def _result_rows(
    result: CursorResult[object],
    *,
    limit: int,
) -> dict[str, object]:
    if not result.returns_rows:
        return {
            "columns": [],
            "rows": [],
            "returned_rows": 0,
            "truncated": False,
            "affected_rows": max(0, int(result.rowcount or 0)),
        }
    columns = [str(key) for key in result.keys()]
    fetched = result.mappings().fetchmany(limit + 1)
    truncated = len(fetched) > limit
    rows = [_json_safe(dict(row)) for row in fetched[:limit]]
    return {
        "columns": columns,
        "rows": rows,
        "returned_rows": len(rows),
        "truncated": truncated,
        "affected_rows": max(0, int(result.rowcount or 0)),
    }


def _insert_audit(
    session: Session,
    actor: ActorContext,
    *,
    event_type: str,
    payload: dict[str, object],
) -> None:
    session.execute(
        text(
            """
            INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
            VALUES (
              :tenant_id, :actor_user_id, :event_type, CAST(:payload AS jsonb)
            )
            """
        ),
        {
            "tenant_id": actor.tenant_id,
            "actor_user_id": actor.user_id,
            "event_type": event_type,
            "payload": json.dumps(_json_safe(payload), ensure_ascii=False, default=str),
        },
    )


def _audit_separately(
    actor: ActorContext,
    *,
    event_type: str,
    payload: dict[str, object],
) -> None:
    try:
        with tenant_session(actor.tenant_id) as session:
            _insert_audit(session, actor, event_type=event_type, payload=payload)
    except Exception:
        # The shared terminal execution ledger is a second audit boundary. A
        # telemetry failure must not rewrite the database result seen by AI.
        return


def database_catalog(
    actor: ActorContext,
    *,
    legacy_read_authorized: bool = False,
) -> dict[str, object]:
    """List every non-system relation visible to the current company DB role."""

    if legacy_read_authorized:
        _require_legacy_read_identity(actor)
    else:
        _require_company_database_identity(actor)
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT n.nspname AS schema_name,
                       c.relname AS relation_name,
                       CASE c.relkind
                         WHEN 'r' THEN 'table'
                         WHEN 'p' THEN 'partitioned_table'
                         WHEN 'v' THEN 'view'
                         WHEN 'm' THEN 'materialized_view'
                         WHEN 'f' THEN 'foreign_table'
                         ELSE c.relkind::text
                       END AS relation_type,
                       c.reltuples::bigint AS estimated_rows,
                       c.relrowsecurity AS row_security_enabled,
                       c.relforcerowsecurity AS row_security_forced,
                       obj_description(c.oid, 'pg_class') AS description,
                       has_table_privilege(c.oid, 'SELECT') AS can_select,
                       has_table_privilege(c.oid, 'INSERT') AS can_insert,
                       has_table_privilege(c.oid, 'UPDATE') AS can_update,
                       has_table_privilege(c.oid, 'DELETE') AS can_delete,
                       (
                         SELECT count(*)::integer
                         FROM pg_attribute AS a
                         WHERE a.attrelid = c.oid
                           AND a.attnum > 0 AND NOT a.attisdropped
                       ) AS column_count,
                       COALESCE((
                         SELECT jsonb_agg(a.attname ORDER BY key_part.ordinality)
                         FROM pg_constraint AS con
                         CROSS JOIN LATERAL unnest(con.conkey)
                           WITH ORDINALITY AS key_part(attnum, ordinality)
                         JOIN pg_attribute AS a
                           ON a.attrelid = con.conrelid
                          AND a.attnum = key_part.attnum
                         WHERE con.conrelid = c.oid AND con.contype = 'p'
                       ), '[]'::jsonb) AS primary_key
                FROM pg_class AS c
                JOIN pg_namespace AS n ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
                  AND n.nspname <> 'information_schema'
                  AND n.nspname NOT LIKE 'pg_%'
                  AND (
                    has_table_privilege(c.oid, 'SELECT')
                    OR has_table_privilege(c.oid, 'INSERT')
                    OR has_table_privilege(c.oid, 'UPDATE')
                    OR has_table_privilege(c.oid, 'DELETE')
                  )
                ORDER BY n.nspname, c.relname
                """
                )
            )
            .mappings()
            .all()
        )
    relations = [
        {
            **_json_safe(dict(row)),
            "table": f"{row['schema_name']}.{row['relation_name']}",
        }
        for row in rows
    ]
    return {
        "ok": True,
        "database_identity": "current_company_ai",
        "scope": "database_role_and_rls",
        "relations": relations,
        "total": len(relations),
        "ai_decides_usage": True,
        "world_observation": {
            "schema": "warehouse.world-observation.v1",
            "operation": "database.catalog.inspect",
            "effect": "read",
            "verified_facts": {
                "visible_relation_count": len(relations),
                "physical_schema_visible": True,
                "database_role_enforced": True,
            },
            "uncertainties": [],
            "affordances": [
                {"capability": "database_schema"},
                {"capability": "database_query"},
                {"capability": "database_execute"},
            ],
            "decision_owner": "auto_runtime",
            "workflow_prescribed": False,
        },
    }


def _resolve_relation(
    session: Session,
    table_ref: object,
) -> dict[str, object]:
    candidate = str(table_ref or "").strip()
    if not candidate:
        raise HTTPException(status_code=422, detail="table must not be empty")
    schema_name, separator, relation_name = candidate.partition(".")
    params: dict[str, object] = {"relation_name": relation_name if separator else schema_name}
    condition = "c.relname = :relation_name"
    if separator:
        params["schema_name"] = schema_name
        condition += " AND n.nspname = :schema_name"
    rows = (
        session.execute(
            text(
                f"""
            SELECT c.oid::bigint AS oid, n.nspname AS schema_name,
                   c.relname AS relation_name,
                   c.relkind, c.relrowsecurity, c.relforcerowsecurity,
                   c.reltuples::bigint AS estimated_rows,
                   obj_description(c.oid, 'pg_class') AS description,
                   has_table_privilege(c.oid, 'SELECT') AS can_select,
                   has_table_privilege(c.oid, 'INSERT') AS can_insert,
                   has_table_privilege(c.oid, 'UPDATE') AS can_update,
                   has_table_privilege(c.oid, 'DELETE') AS can_delete
            FROM pg_class AS c
            JOIN pg_namespace AS n ON n.oid = c.relnamespace
            WHERE {condition}
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND n.nspname <> 'information_schema'
              AND n.nspname NOT LIKE 'pg_%'
              AND (
                has_table_privilege(c.oid, 'SELECT')
                OR has_table_privilege(c.oid, 'INSERT')
                OR has_table_privilege(c.oid, 'UPDATE')
                OR has_table_privilege(c.oid, 'DELETE')
              )
            ORDER BY n.nspname
            LIMIT 2
            """
            ),
            params,
        )
        .mappings()
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Visible database table not found")
    if len(rows) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "ambiguous_table_name",
                "matches": [f"{row['schema_name']}.{row['relation_name']}" for row in rows],
            },
        )
    return dict(rows[0])


def database_schema(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    legacy_read_authorized: bool = False,
) -> dict[str, object]:
    """Expose physical columns, keys, constraints, indexes and RLS policies."""

    if legacy_read_authorized:
        _require_legacy_read_identity(actor)
    else:
        _require_company_database_identity(actor)
    with tenant_readonly_session(actor.tenant_id) as session:
        relation = _resolve_relation(
            session,
            payload.get("table") or payload.get("relation"),
        )
        oid = int(relation["oid"])
        columns = (
            session.execute(
                text(
                    """
                SELECT a.attnum AS ordinal_position, a.attname AS column_name,
                       format_type(a.atttypid, a.atttypmod) AS data_type,
                       NOT a.attnotnull AS nullable,
                       pg_get_expr(d.adbin, d.adrelid) AS default_expression,
                       NULLIF(a.attidentity, '') AS identity_kind,
                       NULLIF(a.attgenerated, '') AS generated_kind,
                       col_description(a.attrelid, a.attnum) AS description,
                       has_column_privilege(a.attrelid, a.attname, 'SELECT') AS can_select,
                       has_column_privilege(a.attrelid, a.attname, 'INSERT') AS can_insert,
                       has_column_privilege(a.attrelid, a.attname, 'UPDATE') AS can_update
                FROM pg_attribute AS a
                LEFT JOIN pg_attrdef AS d
                  ON d.adrelid = a.attrelid AND d.adnum = a.attnum
                WHERE a.attrelid = :oid
                  AND a.attnum > 0 AND NOT a.attisdropped
                ORDER BY a.attnum
                """
                ),
                {"oid": oid},
            )
            .mappings()
            .all()
        )
        constraints = (
            session.execute(
                text(
                    """
                SELECT con.conname AS constraint_name,
                       CASE con.contype
                         WHEN 'p' THEN 'primary_key'
                         WHEN 'f' THEN 'foreign_key'
                         WHEN 'u' THEN 'unique'
                         WHEN 'c' THEN 'check'
                         WHEN 'x' THEN 'exclusion'
                         ELSE con.contype::text
                       END AS constraint_type,
                       pg_get_constraintdef(con.oid, true) AS definition,
                       target_ns.nspname AS referenced_schema,
                       target.relname AS referenced_table
                FROM pg_constraint AS con
                LEFT JOIN pg_class AS target ON target.oid = con.confrelid
                LEFT JOIN pg_namespace AS target_ns
                  ON target_ns.oid = target.relnamespace
                WHERE con.conrelid = :oid
                ORDER BY constraint_type, constraint_name
                """
                ),
                {"oid": oid},
            )
            .mappings()
            .all()
        )
        indexes = (
            session.execute(
                text(
                    """
                SELECT indexname AS index_name, indexdef AS definition
                FROM pg_indexes
                WHERE schemaname = :schema_name AND tablename = :relation_name
                ORDER BY indexname
                """
                ),
                {
                    "schema_name": relation["schema_name"],
                    "relation_name": relation["relation_name"],
                },
            )
            .mappings()
            .all()
        )
        policies = (
            session.execute(
                text(
                    """
                SELECT policyname AS policy_name, permissive, roles, cmd,
                       qual AS using_expression,
                       with_check AS check_expression
                FROM pg_policies
                WHERE schemaname = :schema_name AND tablename = :relation_name
                ORDER BY policyname
                """
                ),
                {
                    "schema_name": relation["schema_name"],
                    "relation_name": relation["relation_name"],
                },
            )
            .mappings()
            .all()
        )
    table = f"{relation['schema_name']}.{relation['relation_name']}"
    return {
        "ok": True,
        "database_identity": "current_company_ai",
        "table": table,
        "relation": _json_safe(relation),
        "columns": [_json_safe(dict(row)) for row in columns],
        "column_headers": [str(row["column_name"]) for row in columns],
        "constraints": [_json_safe(dict(row)) for row in constraints],
        "indexes": [_json_safe(dict(row)) for row in indexes],
        "row_security_policies": [_json_safe(dict(row)) for row in policies],
        "ai_decides_usage": True,
        "world_observation": {
            "schema": "warehouse.world-observation.v1",
            "operation": "database.table_schema.inspect",
            "effect": "read",
            "primary_entity": {"type": "database_table", "ref": table},
            "verified_facts": {
                "physical_schema_visible": True,
                "column_count": len(columns),
                "constraint_count": len(constraints),
                "index_count": len(indexes),
                "row_security_enabled": bool(relation["relrowsecurity"]),
            },
            "uncertainties": [],
            "affordances": [
                {"capability": "database_query"},
                {"capability": "database_execute"},
            ],
            "decision_owner": "auto_runtime",
            "workflow_prescribed": False,
        },
    }


def database_query(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    origin: str,
    legacy_read_authorized: bool = False,
) -> dict[str, object]:
    """Execute model-authored SQL in a database-enforced read-only transaction."""

    if legacy_read_authorized:
        _require_legacy_read_identity(actor)
    else:
        _require_company_database_identity(actor)
    operation_id = str(uuid4())
    statement = _statement(payload.get("sql"))
    parameters = _parameters(payload.get("parameters"))
    limit = _bounded_limit(payload.get("limit"))
    audit_base = {
        "operation_id": operation_id,
        "origin": origin if origin in _ORIGINS else "api",
        "mode": "query",
        "sql": statement,
        "statement_digest": _digest(statement),
        "parameters": parameters,
        "run_id": payload.get("run_id"),
        "conversation_id": payload.get("conversation_id"),
    }
    try:
        with tenant_readonly_session(actor.tenant_id) as session:
            result = session.execute(text(statement), parameters)
            rows = _result_rows(result, limit=limit)
    except SQLAlchemyError as exc:
        error = _database_error(exc)
        _audit_separately(
            actor,
            event_type="database.runtime.query.rejected",
            payload={**audit_base, "error": error},
        )
        raise HTTPException(
            status_code=422,
            detail={"reason": "database_query_rejected", **error},
        ) from exc
    _audit_separately(
        actor,
        event_type="database.runtime.query.succeeded",
        payload={**audit_base, **rows},
    )
    return {
        "ok": True,
        "operation_id": operation_id,
        "status": "succeeded",
        "effect": "read",
        "effect_verified": True,
        "database_identity": "current_company_ai",
        **rows,
        "world_observation": {
            "schema": "warehouse.world-observation.v1",
            "operation": "database.sql.query",
            "effect": "read",
            "verified_facts": {
                "query_executed": True,
                "read_only_transaction": True,
                "returned_rows": rows["returned_rows"],
                "truncated": rows["truncated"],
            },
            "uncertainties": [],
            "affordances": [],
            "decision_owner": "auto_runtime",
            "workflow_prescribed": False,
        },
    }


def legacy_database_schema(
    actor: ActorContext,
    payload: dict[str, object],
) -> dict[str, object]:
    """Adapt the retained broad schema command to the physical DB Runtime."""

    table = str(payload.get("table") or "").strip()
    if table:
        result = database_schema(
            actor,
            {"table": table},
            legacy_read_authorized=True,
        )
        return {**result, "legacy_command": "db_schema"}

    domain = str(payload.get("domain") or "").strip().casefold()
    catalog = database_catalog(actor, legacy_read_authorized=True)
    relations = list(catalog["relations"])
    if domain:
        relations = [
            relation
            for relation in relations
            if domain in str(relation.get("table") or "").casefold()
        ]
    return {
        **catalog,
        "relations": relations,
        "tables": relations,
        "total": len(relations),
        "domain": domain or None,
        "legacy_command": "db_schema",
    }


def legacy_database_query(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    """Execute retained db-query syntax in the same read-only RLS boundary."""

    result = database_query(
        actor,
        payload,
        origin=origin,
        legacy_read_authorized=True,
    )
    return {**result, "legacy_command": "db_query"}


def database_execute(
    actor: ActorContext,
    payload: dict[str, object],
    *,
    origin: str,
    legacy_write_authorized: bool = False,
) -> dict[str, object]:
    """Execute model-authored SQL and optional read-back in one transaction."""

    if legacy_write_authorized:
        if not (
            {"cli.db.exec", "cli.db.department", "settings.manage", "ai.database"}
            & set(actor.permissions)
        ):
            raise HTTPException(
                status_code=403,
                detail="Current identity cannot execute a company database mutation",
            )
    else:
        _require_company_database_identity(actor)
    operation_id = str(uuid4())
    statement = _statement(payload.get("sql"))
    parameters = _parameters(payload.get("parameters"))
    verification_statement = str(payload.get("verification_sql") or "").strip()
    verification_parameters = _parameters(payload.get("verification_parameters"))
    limit = _bounded_limit(payload.get("limit"))
    normalized_origin = origin if origin in _ORIGINS else "api"
    audit_base = {
        "operation_id": operation_id,
        "origin": normalized_origin,
        "mode": "write",
        "sql": statement,
        "statement_digest": _digest(statement),
        "parameters": parameters,
        "verification_sql": verification_statement or None,
        "verification_statement_digest": (
            _digest(verification_statement) if verification_statement else None
        ),
        "verification_parameters": verification_parameters,
        "intent": str(payload.get("intent") or "")[:4_000],
        "reasoning_summary": str(payload.get("reasoning_summary") or "")[:4_000],
        "run_id": payload.get("run_id"),
        "conversation_id": payload.get("conversation_id"),
    }
    try:
        with tenant_session(actor.tenant_id) as session:
            result = session.execute(text(statement), parameters)
            rows = _result_rows(result, limit=limit)
            verification = None
            if verification_statement:
                verified_result = session.execute(
                    text(verification_statement),
                    verification_parameters,
                )
                verification = _result_rows(verified_result, limit=limit)
            _insert_audit(
                session,
                actor,
                event_type="database.runtime.write.succeeded",
                payload={
                    **audit_base,
                    **rows,
                    "verification": verification,
                },
            )
    except SQLAlchemyError as exc:
        error = _database_error(exc)
        _audit_separately(
            actor,
            event_type="database.runtime.write.rejected",
            payload={**audit_base, "error": error},
        )
        raise HTTPException(
            status_code=422,
            detail={"reason": "database_write_rejected", **error},
        ) from exc
    return {
        "ok": True,
        "operation_id": operation_id,
        "status": "succeeded",
        "effect": "database_write",
        "effect_verified": True,
        "database_identity": "current_company_ai",
        **rows,
        "verification": verification,
        "world_observation": {
            "schema": "warehouse.world-observation.v1",
            "operation": "database.sql.execute",
            "effect": "database_write",
            "verified_facts": {
                "transaction_committed": True,
                "database_effect_verified": True,
                "affected_rows": rows["affected_rows"],
                "returning_rows": rows["returned_rows"],
                "read_back_executed": verification is not None,
            },
            "uncertainties": (
                []
                if verification is not None or rows["returned_rows"]
                else ["No explicit read-back query was requested"]
            ),
            "affordances": [{"capability": "database_query"}],
            "decision_owner": "auto_runtime",
            "workflow_prescribed": False,
        },
    }
