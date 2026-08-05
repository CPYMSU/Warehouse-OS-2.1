"""Truthful read adapters for retained Warehouse command contracts.

The original command catalogue contains useful business vocabulary whose old
HTTP handlers were not part of the PostgreSQL rewrite.  This module restores a
bounded subset without reviving the catch-all compatibility writer:

* native PostgreSQL tables are queried in database-enforced read-only, RLS
  scoped transactions;
* compatibility projections have an explicit, server-owned namespace per
  capability and are never created by a read;
* previews validate current database state and return a digest, but never
  publish a workflow definition;
* missing detail records fail closed instead of returning fabricated objects.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import tenant_readonly_session

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext


@dataclass(frozen=True)
class ProjectionRead:
    namespace: str
    collection: str
    resource: str
    filters: tuple[tuple[str, str, str], ...] = ()
    ref_dest: str | None = None
    ref_fields: tuple[str, ...] = ("id", "legacy_id")
    limit_dest: str | None = "query.limit"
    default_limit: int = 200


# Every projection is a deliberate mapping to an RLS-protected read model.
# Adding a catalogue command here does not activate it by itself; adapters.py
# must independently freeze and verify its method/path/effect contract.
PROJECTION_READS: dict[str, ProjectionRead] = {
    "wf_repair_show": ProjectionRead(
        "workflow.repair",
        "repair_case",
        "workflow.repair_case",
        ref_dest="path.case_id",
        ref_fields=("id", "case_id", "legacy_id"),
    ),
    "wf_repair_watch": ProjectionRead(
        "workflow.repair",
        "repair_case",
        "workflow.repair_case",
        ref_dest="path.case_id",
        ref_fields=("id", "case_id", "legacy_id"),
    ),
    "wf_task_detail": ProjectionRead(
        "workflow.inbox",
        "task",
        "workflow.task_projection",
        ref_dest="path.id",
        ref_fields=("id", "task_id", "legacy_id"),
    ),
    "b2b_companies": ProjectionRead(
        "b2b.company",
        "companies",
        "b2b.company_directory",
    ),
    "tender_detail": ProjectionRead(
        "tender.notice",
        "tender",
        "procurement.tender_notice",
        ref_dest="path.id",
        ref_fields=("id", "notice_id", "legacy_id"),
    ),
    "stocktake_detail": ProjectionRead(
        "stocktake",
        "stocktake",
        "warehouse.stocktake",
        ref_dest="path.id",
        ref_fields=("id", "stocktake_id", "legacy_id"),
    ),
    "erp_budget_ledger": ProjectionRead(
        "erp.budget.ledger",
        "entries",
        "erp.budget_ledger_entry",
        filters=(("path.id", "budget_id", "exact"),),
    ),
    "fin_accounts": ProjectionRead(
        "erp.gl.account",
        "accounts",
        "finance.gl_account",
    ),
    "fin_assets": ProjectionRead(
        "erp.gl.asset",
        "assets",
        "finance.fixed_asset",
    ),
    "fin_tax": ProjectionRead(
        "erp.gl.tax",
        "tax",
        "finance.tax_ledger",
        filters=(("query.period", "period", "exact"),),
    ),
    "fin_posting_failures": ProjectionRead(
        "erp.gl.posting_failure",
        "failures",
        "finance.posting_failure",
        filters=(("query.status", "status", "exact"),),
    ),
    "fin_party_list": ProjectionRead(
        "erp.finance.party",
        "parties",
        "finance.party",
        filters=(
            ("query.q", "name", "contains"),
            ("query.type", "party_type", "exact"),
        ),
    ),
    "fin_account_list": ProjectionRead(
        "erp.finance.account",
        "accounts",
        "finance.cash_account",
        filters=(
            ("query.q", "name", "contains"),
            ("query.owner_party_id", "owner_party_id", "exact"),
            ("query.kind", "kind", "exact"),
        ),
    ),
    "fin_equity_list": ProjectionRead(
        "erp.finance.equity",
        "equity",
        "finance.equity_ownership",
        filters=(("query.as_of", "as_of", "at_or_before"),),
    ),
    "fin_fx_list": ProjectionRead(
        "erp.finance.fx_rate",
        "rates",
        "finance.fx_rate",
    ),
    "fin_aa_config_get": ProjectionRead(
        "erp.finance.aa_config",
        "config",
        "finance.aa_configuration",
        default_limit=20,
    ),
    "fin_intake_batches": ProjectionRead(
        "erp.finance.intake_batch",
        "batches",
        "finance.intake_batch",
        filters=(
            ("query.status", "status", "exact"),
            ("query.q", "search_text", "contains"),
        ),
    ),
    "fin_intake_list": ProjectionRead(
        "erp.finance.intake_item",
        "items",
        "finance.intake_item",
        filters=(
            ("query.batch_id", "batch_id", "exact"),
            ("query.status", "status", "exact"),
            ("query.q", "search_text", "contains"),
        ),
    ),
    "erp_period_tree": ProjectionRead(
        "erp.period",
        "periods",
        "erp.budget_period",
    ),
    "msg_inbox": ProjectionRead(
        "collaboration.message",
        "messages",
        "collaboration.message",
        filters=(("query.box", "box", "exact"),),
    ),
    "collab_edit_list": ProjectionRead(
        "collaboration.edit_request",
        "requests",
        "collaboration.edit_request",
        filters=(("query.box", "box", "exact"),),
    ),
    "digital_market_orders": ProjectionRead(
        "asset.digital.order",
        "orders",
        "digital_asset.market_order",
        filters=(
            ("query.status", "status", "exact"),
            ("query.listing", "listing_id", "exact"),
        ),
    ),
    "fin_statement_drilldown": ProjectionRead(
        "erp.gl.voucher_line",
        "entries",
        "finance.voucher_line",
        filters=(
            ("query.scope", "scope", "exact"),
            ("query.period", "period", "exact"),
            ("query.as_of", "posting_date", "at_or_before"),
            ("query.code", "account_code", "exact"),
        ),
    ),
    "fin_equity_change": ProjectionRead(
        "erp.gl.equity_change",
        "changes",
        "finance.equity_change",
        filters=(("query.period", "period", "exact"),),
    ),
    "fin_notes": ProjectionRead(
        "erp.gl.note",
        "notes",
        "finance.statement_note",
        filters=(("query.period", "period", "exact"),),
    ),
    "fin_equity_graph": ProjectionRead(
        "erp.finance.equity",
        "relations",
        "finance.equity_ownership",
        filters=(("query.as_of", "as_of", "at_or_before"),),
    ),
    "compliance_by_subject": ProjectionRead(
        "compliance.review",
        "reviews",
        "compliance.subject_review",
        filters=(
            ("query.type", "subject_type", "exact"),
            ("query.id", "subject_id", "exact"),
        ),
    ),
    "compliance_cert": ProjectionRead(
        "compliance.certificate",
        "certificate",
        "compliance.certificate",
        filters=(("query.serial", "serial", "exact"),),
        default_limit=2,
    ),
    "datahub_jobs": ProjectionRead(
        "datahub.job",
        "jobs",
        "datahub.import_job",
    ),
    "asset_analysis_runs": ProjectionRead(
        "asset.analysis_run",
        "runs",
        "asset.analysis_run",
        filters=(
            ("query.asset_id", "asset_id", "exact"),
            ("query.type", "analysis_type", "exact"),
        ),
    ),
    "asset_txns": ProjectionRead(
        "asset.transaction",
        "transactions",
        "asset.transaction",
        filters=(("path.id", "asset_id", "exact"),),
    ),
}


CUSTOM_READS = frozenset(
    {
        "record_config",
        "record_type_resolve",
        "record_principal_resolve",
        "case_config",
        "alerts_rules",
        "alerts_kpi",
        "wf_flow_preview",
        "wf_flow_history",
        "shield_diagnose",
        "people_list",
        "assistant_me",
        "agent_runs_list",
        "risk_list",
        "profile_show",
        "lessons_list",
        "knowledge_list",
        "asset_resolve",
        "notifications_summary",
    }
)

SUPPORTED_LEGACY_READS = frozenset(PROJECTION_READS) | CUSTOM_READS

_CANONICAL_RESOURCE_TYPES = {
    "workflow.repair_case": "workflow.repair",
    "workflow.task_projection": "workflow.task",
    "procurement.tender_notice": "procurement.tender",
    "warehouse.stocktake": "warehouse.stocktake",
    "finance.party": "finance.party",
    "finance.cash_account": "finance.account",
    "finance.equity_ownership": "finance.equity",
    "finance.fx_rate": "finance.fx_rate",
    "finance.aa_configuration": "finance.aa_configuration",
    "finance.intake_batch": "finance.intake_batch",
    "finance.intake_item": "finance.intake_item",
    "collaboration.message": "collaboration.message",
    "collaboration.edit_request": "collaboration.edit_request",
    "digital_asset.market_order": "digital_asset.market_order",
    "asset.transaction": "asset.transaction",
    "notification.summary": "notification.receipt",
    "datahub.import_job": "datahub.import",
}


_RECORD_CATEGORIES = (
    {"key": "personnel", "name": "人員檔案", "icon": "user", "active": True},
    {"key": "meeting", "name": "會議檔案", "icon": "clipboard", "active": True},
    {"key": "training", "name": "培訓檔案", "icon": "doc", "active": True},
    {"key": "safety", "name": "安全檔案", "icon": "shield", "active": True},
    {"key": "case", "name": "事務檔案", "icon": "layers", "active": True},
    {"key": "other", "name": "其他檔案", "icon": "box", "active": True},
)
_DEFAULT_RECORD_TYPES = (
    {
        "id": "general_record",
        "key": "general_record",
        "type_key": "general_record",
        "name": "通用檔案",
        "category_key": "other",
        "active": True,
        "revision_no": 1,
        "fields": [],
    },
    {
        "id": "personnel_record",
        "key": "personnel_record",
        "type_key": "personnel_record",
        "name": "人員檔案",
        "category_key": "personnel",
        "active": True,
        "revision_no": 1,
        "fields": [],
    },
)
_DEFAULT_CASE_TYPE = {
    "id": "general",
    "key": "general",
    "name": "通用事務",
    "category": "service",
    "active": True,
    "revision_no": 1,
    "fields": [],
    "sla": {},
}


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
    return value


def _bounded_int(value: object, *, default: int, maximum: int = 1000) -> int:
    try:
        return max(1, min(int(value or default), maximum))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="limit must be an integer") from exc


def _documents(session: Session, namespace: str, *, limit: int = 1000) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text(
                """
            SELECT document_key, payload, source, version, created_at, updated_at
            FROM compatibility.documents
            WHERE namespace = :namespace AND status = 'active'
            ORDER BY updated_at DESC, document_key
            LIMIT :limit
            """
            ),
            {"namespace": namespace, "limit": max(1, min(limit, 2000))},
        )
        .mappings()
        .all()
    )
    items: list[dict[str, object]] = []
    for row in rows:
        payload = dict(row["payload"] or {})
        payload.setdefault("document_key", str(row["document_key"]))
        payload.setdefault("source", str(row["source"]))
        payload.setdefault("version", int(row["version"]))
        payload.setdefault("created_at", row["created_at"])
        payload.setdefault("updated_at", row["updated_at"])
        items.append(dict(_json_safe(payload)))
    return items


def _canonical_entities(
    session: Session,
    resource_type: str,
    *,
    limit: int = 1000,
) -> list[dict[str, object]]:
    rows = (
        session.execute(
            text(
                """
                SELECT legacy_id, entity_key, state, payload, revision,
                       created_at, updated_at
                FROM business.entities
                WHERE resource_type = :resource_type
                ORDER BY updated_at DESC, entity_key
                LIMIT :limit
                """
            ),
            {"resource_type": resource_type, "limit": max(1, min(limit, 2000))},
        )
        .mappings()
        .all()
    )
    items: list[dict[str, object]] = []
    for row in rows:
        payload = dict(row["payload"] or {})
        body = payload.get("body")
        path = payload.get("path")
        item = {
            **(dict(body) if isinstance(body, dict) else {}),
            **(dict(path) if isinstance(path, dict) else {}),
            **payload,
        }
        item.setdefault("id", int(row["legacy_id"]))
        item.setdefault("legacy_id", int(row["legacy_id"]))
        item.setdefault("entity_key", str(row["entity_key"]))
        item.setdefault("state", str(row["state"]))
        item.setdefault("status", str(row["state"]))
        item.setdefault("revision", int(row["revision"]))
        item.setdefault("created_at", row["created_at"])
        item.setdefault("updated_at", row["updated_at"])
        items.append(dict(_json_safe(item)))
    return items


def _normalized(value: object) -> str:
    return str(value or "").strip().casefold()


def _matches(item: dict[str, object], field: str, expected: object, mode: str) -> bool:
    if expected in (None, ""):
        return True
    actual = item.get(field)
    if field == "search_text" and actual in (None, ""):
        actual = " ".join(str(value) for value in item.values() if value is not None)
    if mode == "contains":
        return _normalized(expected) in _normalized(actual)
    if mode == "at_or_before":
        return not actual or str(actual) <= str(expected)
    return _normalized(actual) == _normalized(expected)


def _projection_read(
    actor: ActorContext,
    values: dict[str, object],
    spec: ProjectionRead,
) -> dict[str, object]:
    requested_limit = values.get(spec.limit_dest) if spec.limit_dest else None
    limit = _bounded_int(requested_limit, default=spec.default_limit)
    canonical: list[dict[str, object]] = []
    with tenant_readonly_session(actor.tenant_id) as session:
        items = _documents(session, spec.namespace, limit=max(limit, 1000))
        canonical_resource_type = _CANONICAL_RESOURCE_TYPES.get(spec.resource)
        if canonical_resource_type:
            canonical = _canonical_entities(
                session,
                canonical_resource_type,
                limit=max(limit, 1000),
            )
            seen = {
                str(item.get("id") or item.get("legacy_id") or item.get("document_key"))
                for item in canonical
            }
            items = canonical + [
                item
                for item in items
                if str(item.get("id") or item.get("legacy_id") or item.get("document_key"))
                not in seen
            ]
    if spec.resource == "collaboration.message" and canonical:
        requested_box = str(values.get("query.box") or "inbox").strip().lower()
        scoped_messages: list[dict[str, object]] = []
        for item in items:
            recipient = str(item.get("recipient_user_id") or "")
            sender = str(item.get("last_actor_user_id") or "")
            if requested_box == "sent" and sender == str(actor.user_id):
                item["box"] = "sent"
                scoped_messages.append(item)
            elif requested_box != "sent" and recipient in {"all", str(actor.user_id)}:
                item["box"] = "inbox"
                scoped_messages.append(item)
        items = scoped_messages
    for source, field, mode in spec.filters:
        expected = values.get(source)
        if expected not in (None, ""):
            items = [item for item in items if _matches(item, field, expected, mode)]
    if spec.ref_dest:
        reference = values.get(spec.ref_dest)
        selected = next(
            (
                item
                for item in items
                if any(
                    _normalized(item.get(field)) == _normalized(reference)
                    for field in (*spec.ref_fields, "document_key")
                )
            ),
            None,
        )
        if selected is None:
            raise HTTPException(status_code=404, detail=f"{spec.resource} was not found")
        return {
            "ok": True,
            "available": True,
            "source": (
                "postgresql_canonical_business_state"
                if canonical
                else "postgresql_compatibility_projection"
            ),
            "resource": spec.resource,
            spec.collection: selected,
            "effect_verified": True,
        }
    items = items[:limit]
    return {
        "ok": True,
        "available": True,
        "empty": not items,
        "source": (
            "postgresql_canonical_business_state"
            if canonical
            else "postgresql_compatibility_projection"
        ),
        "resource": spec.resource,
        spec.collection: items,
        "items": items,
        "count": len(items),
        "reason": None if items else "no_records",
        "effect_verified": True,
    }


def _record_configuration(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        categories = _documents(session, "record.category", limit=500)
        record_types = _documents(session, "record.type", limit=500)
    categories = categories or [dict(item) for item in _RECORD_CATEGORIES]
    record_types = record_types or [dict(item) for item in _DEFAULT_RECORD_TYPES]
    category = _normalized(values.get("query.category"))
    type_key = _normalized(values.get("query.type"))
    query = _normalized(values.get("query.q"))
    if category:
        categories = [item for item in categories if _normalized(item.get("key")) == category]
        record_types = [
            item for item in record_types if _normalized(item.get("category_key")) == category
        ]
    if type_key:
        record_types = [
            item
            for item in record_types
            if type_key
            in {
                _normalized(item.get("type_key")),
                _normalized(item.get("key")),
                _normalized(item.get("id")),
            }
        ]
    if query:
        record_types = [
            item
            for item in record_types
            if query
            in _normalized(
                " ".join(
                    str(item.get(key) or "") for key in ("type_key", "key", "name", "description")
                )
            )
        ]
    return {
        "ok": True,
        "available": True,
        "source": "postgresql_rls_configuration",
        "categories": categories,
        "types": record_types,
        "record_types": record_types,
        "revision": max(
            [int(item.get("revision_no") or item.get("version") or 1) for item in record_types]
            or [1]
        ),
        "effect_verified": True,
    }


def _record_type_resolve(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    configuration = _record_configuration(actor, values)
    query = _normalized(values.get("query.q"))
    limit = _bounded_int(values.get("query.limit"), default=8, maximum=50)
    candidates = list(configuration["record_types"])
    ranked: list[tuple[int, dict[str, object]]] = []
    for item in candidates:
        keys = {
            _normalized(item.get("type_key")),
            _normalized(item.get("key")),
            _normalized(item.get("id")),
            _normalized(item.get("name")),
        }
        exact = bool(query and query in keys)
        contains = not query or any(query in value for value in keys if value)
        if contains:
            ranked.append((0 if exact else 1, item))
    ranked.sort(key=lambda pair: (pair[0], _normalized(pair[1].get("name"))))
    matches = [item for _, item in ranked[:limit]]
    exact_match = next(
        (
            item
            for item in matches
            if query
            in {
                _normalized(item.get("type_key")),
                _normalized(item.get("key")),
                _normalized(item.get("id")),
                _normalized(item.get("name")),
            }
        ),
        None,
    )
    return {
        "ok": True,
        "query": values.get("query.q"),
        "resolved": exact_match is not None,
        "type_key": (
            exact_match.get("type_key") or exact_match.get("key") if exact_match else None
        ),
        "type": exact_match,
        "candidates": matches,
        "effect_verified": True,
    }


def _record_principal_resolve(
    actor: ActorContext,
    values: dict[str, object],
) -> dict[str, object]:
    query = _normalized(values.get("query.q"))
    limit = _bounded_int(values.get("query.limit"), default=8, maximum=50)
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT 'user' AS principal_type, u.id AS principal_id,
                       u.display_name AS name, u.username AS secondary,
                       pp.department_code AS unit_code
                FROM iam.memberships AS m
                JOIN iam.users AS u ON u.id = m.user_id AND u.active
                LEFT JOIN iam.position_profiles AS pp
                  ON pp.tenant_id = m.tenant_id AND pp.position_code = m.position_code
                WHERE m.active
                UNION ALL
                SELECT 'unit', ou.id, ou.name, ou.unit_code, ou.unit_code
                FROM iam.organizational_units AS ou WHERE ou.active
                """
                )
            )
            .mappings()
            .all()
        )
    principals = [dict(_json_safe(dict(row))) for row in rows]
    if query:
        principals = [
            item
            for item in principals
            if query
            in _normalized(
                f"{item.get('name', '')} {item.get('secondary', '')} {item.get('unit_code', '')}"
            )
        ]
    principals = principals[:limit]
    return {
        "ok": True,
        "query": values.get("query.q"),
        "principals": principals,
        "candidates": principals,
        "count": len(principals),
        "effect_verified": True,
    }


def _case_configuration(actor: ActorContext) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        case_types = _documents(session, "case.type", limit=500)
        units = (
            session.execute(
                text(
                    """
                SELECT id, unit_code, name, unit_type, parent_unit_code
                FROM iam.organizational_units WHERE active ORDER BY name, unit_code
                """
                )
            )
            .mappings()
            .all()
        )
    case_types = case_types or [dict(_DEFAULT_CASE_TYPE)]
    return {
        "ok": True,
        "available": True,
        "source": "postgresql_rls_configuration",
        "types": case_types,
        "config_types": case_types,
        "units": [_json_safe(dict(row)) for row in units],
        "revision": max(
            [int(item.get("revision_no") or item.get("version") or 1) for item in case_types] or [1]
        ),
        "effect_verified": True,
    }


def _alert_configuration(
    actor: ActorContext,
    *,
    kpi_only: bool,
) -> dict[str, object]:
    namespace = "alert.kpi_rule" if kpi_only else "alert.rule"
    with tenant_readonly_session(actor.tenant_id) as session:
        rules = _documents(session, namespace, limit=500)
        open_alerts = _documents(session, "alert", limit=1000)
    open_alerts = [item for item in open_alerts if item.get("status") in (None, "open")]
    triggered: dict[str, int] = {}
    for alert in open_alerts:
        rule_key = str(alert.get("rule_key") or alert.get("kpi_key") or "unmapped")
        triggered[rule_key] = triggered.get(rule_key, 0) + 1
    for rule in rules:
        key = str(rule.get("rule_key") or rule.get("kpi_key") or rule.get("id") or "")
        rule.setdefault("triggered_count", triggered.get(key, 0))
    result = {
        "ok": True,
        "available": True,
        "source": "postgresql_rls_alert_configuration",
        "rules": rules,
        "items": rules,
        "open_alert_count": len(open_alerts),
        "effect_verified": True,
    }
    if kpi_only:
        result["kpis"] = sorted(
            {str(rule.get("kpi_key")) for rule in rules if str(rule.get("kpi_key") or "").strip()}
        )
    return result


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        _json_safe(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _workflow_preview(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    workflow_key = str(values.get("path.workflow") or "").strip()
    supplied = values.get("body.workflow")
    nodes = values.get("body.nodes")
    if isinstance(supplied, dict) and nodes in (None, []):
        nodes = supplied.get("nodes")
    nodes = list(nodes) if isinstance(nodes, list) else []
    errors: list[dict[str, object]] = []
    node_keys: list[str] = []
    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append({"path": f"nodes[{index}]", "code": "node_must_be_object"})
            continue
        key = str(node.get("key") or node.get("id") or "").strip()
        if not key:
            errors.append({"path": f"nodes[{index}]", "code": "node_key_required"})
        node_keys.append(key)
    duplicates = sorted({key for key in node_keys if key and node_keys.count(key) > 1})
    for key in duplicates:
        errors.append({"path": "nodes", "code": "duplicate_node_key", "value": key})
    with tenant_readonly_session(actor.tenant_id) as session:
        current = (
            session.execute(
                text(
                    """
                SELECT id, version, definition, updated_at
                FROM workflow.definitions
                WHERE workflow_key = :workflow_key
                ORDER BY version DESC LIMIT 1
                """
                ),
                {"workflow_key": workflow_key},
            )
            .mappings()
            .one_or_none()
        )
        running_instances = int(
            session.execute(
                text(
                    """
                    SELECT count(*)
                    FROM workflow.instances AS wi
                    JOIN workflow.definitions AS wd ON wd.id = wi.definition_id
                    WHERE wd.workflow_key = :workflow_key
                      AND wi.status NOT IN ('completed', 'cancelled')
                    """
                ),
                {"workflow_key": workflow_key},
            ).scalar_one()
        )
    current_version = int(current["version"]) if current else 0
    base_version = int(values.get("body.base_version") or current_version)
    if current and base_version != current_version:
        errors.append(
            {
                "path": "base_version",
                "code": "stale_base_version",
                "expected": current_version,
                "received": base_version,
            }
        )
    preview = {
        "workflow_key": workflow_key,
        "base_version": base_version,
        "next_version": current_version + 1,
        "nodes": nodes,
    }
    return {
        "ok": not errors,
        "valid": not errors,
        "errors": errors,
        "definition_preview_hash": _canonical_digest(preview),
        "preview": preview,
        "impact": {"running_instances": running_instances},
        "published": False,
        "effect_verified": True,
    }


def _workflow_history(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    workflow_key = str(values.get("path.workflow") or "").strip()
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id, workflow_key, name, version, definition, active,
                       created_at, updated_at
                FROM workflow.definitions
                WHERE workflow_key = :workflow_key
                ORDER BY version DESC
                """
                ),
                {"workflow_key": workflow_key},
            )
            .mappings()
            .all()
        )
    versions = [dict(_json_safe(dict(row))) for row in rows]
    for version in versions:
        version["definition_hash"] = _canonical_digest(version.get("definition") or {})
    return {
        "ok": True,
        "workflow_key": workflow_key,
        "versions": versions,
        "history": versions,
        "count": len(versions),
        "effect_verified": True,
    }


def _people(actor: ActorContext) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT u.id, u.username, u.display_name, m.position_code,
                       pp.name AS position_name, pp.department_code,
                       ou.name AS department_name
                FROM iam.memberships AS m
                JOIN iam.users AS u ON u.id = m.user_id AND u.active
                LEFT JOIN iam.position_profiles AS pp
                  ON pp.tenant_id = m.tenant_id AND pp.position_code = m.position_code
                LEFT JOIN iam.organizational_units AS ou
                  ON ou.tenant_id = pp.tenant_id AND ou.unit_code = pp.department_code
                WHERE m.active ORDER BY u.display_name, u.username
                """
                )
            )
            .mappings()
            .all()
        )
    people = [dict(_json_safe(dict(row))) for row in rows]
    return {
        "ok": True,
        "people": people,
        "items": people,
        "count": len(people),
        "effect_verified": True,
    }


def _profile_row(session: Session, actor: ActorContext) -> dict[str, object]:
    row = (
        session.execute(
            text(
                """
            SELECT profile, revision, created_at, updated_at
            FROM iam.user_profiles WHERE user_id = :user_id
            """
            ),
            {"user_id": actor.user_id},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return {"profile": {}, "revision": 0, "created_at": None, "updated_at": None}
    return dict(_json_safe(dict(row)))


def _assistant_profile(actor: ActorContext) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        profile = _profile_row(session, actor)
        counts = (
            session.execute(
                text(
                    """
                SELECT
                  (SELECT count(*) FROM secretariat.conversations
                   WHERE owner_user_id = :user_id) AS conversations,
                  (SELECT count(*) FROM secretariat.runs
                   WHERE actor_user_id = :user_id) AS runs,
                  (SELECT count(*) FROM secretariat.memory_units
                   WHERE status = 'active' AND (
                     scope = 'company' OR owner_user_id = :user_id
                   )) AS memories,
                  (SELECT count(*) FROM secretariat.knowledge_chunks) AS knowledge_chunks
                """
                ),
                {"user_id": actor.user_id},
            )
            .mappings()
            .one()
        )
    return {
        "ok": True,
        "assistant": {
            "owner_user_id": str(actor.user_id),
            "owner_name": actor.display_name,
            "tenant": actor.tenant_slug,
            "profile": profile["profile"],
            "profile_revision": profile["revision"],
            "statistics": _json_safe(dict(counts)),
        },
        "effect_verified": True,
    }


def _agent_runs(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    limit = _bounded_int(values.get("query.limit"), default=20, maximum=200)
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT r.id, r.conversation_id, r.task, r.status,
                       r.created_at, r.updated_at,
                       count(o.id)::integer AS operation_count
                FROM secretariat.runs AS r
                LEFT JOIN secretariat.operations AS o ON o.run_id = r.id
                WHERE r.actor_user_id = :user_id
                GROUP BY r.id
                ORDER BY r.created_at DESC LIMIT :limit
                """
                ),
                {"user_id": actor.user_id, "limit": limit},
            )
            .mappings()
            .all()
        )
    runs = [dict(_json_safe(dict(row))) for row in rows]
    return {"ok": True, "runs": runs, "items": runs, "count": len(runs), "effect_verified": True}


def _risk_events(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    requested = str(values.get("query.status") or "open").strip().lower()
    condition = "TRUE" if requested in {"", "all"} else "state = :state"
    params: dict[str, object] = {}
    if condition != "TRUE":
        params["state"] = requested
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    f"""
                SELECT id, execution_id, state, risk, summary,
                       reviewed_by, reviewed_at, created_at, updated_at
                FROM shield.ai_risk_reviews WHERE {condition}
                ORDER BY created_at DESC LIMIT 500
                """
                ),
                params,
            )
            .mappings()
            .all()
        )
    events = [dict(_json_safe(dict(row))) for row in rows]
    return {
        "ok": True,
        "risk_events": events,
        "items": events,
        "count": len(events),
        "effect_verified": True,
    }


def _user_profile(actor: ActorContext) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        profile = _profile_row(session, actor)
        stats = (
            session.execute(
                text(
                    """
                SELECT kind, count(*)::integer AS count,
                       avg(confidence) AS average_confidence,
                       max(updated_at) AS last_updated_at
                FROM secretariat.memory_units
                WHERE status = 'active' AND (
                  scope = 'company' OR owner_user_id = :user_id
                ) GROUP BY kind ORDER BY kind
                """
                ),
                {"user_id": actor.user_id},
            )
            .mappings()
            .all()
        )
    return {
        "ok": True,
        "profile": profile["profile"],
        "revision": profile["revision"],
        "behavior_statistics": [_json_safe(dict(row)) for row in stats],
        "effect_verified": True,
    }


def _lessons(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    limit = _bounded_int(values.get("query.limit"), default=50, maximum=500)
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id, content, confidence, salience, scope, evidence,
                       metadata, valid_from, updated_at
                FROM secretariat.memory_units
                WHERE kind = 'procedural' AND status = 'active'
                  AND (scope = 'company' OR owner_user_id = :user_id)
                ORDER BY salience DESC, confidence DESC, updated_at DESC
                LIMIT :limit
                """
                ),
                {"user_id": actor.user_id, "limit": limit},
            )
            .mappings()
            .all()
        )
    lessons = [dict(_json_safe(dict(row))) for row in rows]
    return {
        "ok": True,
        "lessons": lessons,
        "items": lessons,
        "count": len(lessons),
        "effect_verified": True,
    }


def _knowledge(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    limit = _bounded_int(values.get("query.limit"), default=50, maximum=500)
    source_type = _normalized(values.get("query.type"))
    query = _normalized(values.get("query.q"))
    include_all = bool(values.get("query.all"))
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                SELECT id, source_type, source_id, chunk_index, content,
                       metadata, embedding_model, embedded_at, created_at, updated_at
                FROM secretariat.knowledge_chunks
                ORDER BY updated_at DESC LIMIT :scan_limit
                """
                ),
                {"scan_limit": min(2000, max(limit * 10, limit))},
            )
            .mappings()
            .all()
        )
    items = [dict(_json_safe(dict(row))) for row in rows]
    if source_type:
        items = [item for item in items if _normalized(item.get("source_type")) == source_type]
    if query:
        items = [
            item
            for item in items
            if query in _normalized(f"{item.get('content', '')} {item.get('metadata', '')}")
        ]
    if not include_all:
        items = items[:limit]
    return {
        "ok": True,
        "knowledge": items[:limit],
        "items": items[:limit],
        "count": len(items[:limit]),
        "effect_verified": True,
    }


def _asset_resolve(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    query = _normalized(values.get("query.q"))
    with tenant_readonly_session(actor.tenant_id) as session:
        items = _documents(session, "asset.financial", limit=1000)
    candidates = [
        item
        for item in items
        if not query
        or query
        in _normalized(
            " ".join(
                str(item.get(key) or "")
                for key in ("name", "symbol", "ticker", "code", "pinyin", "exchange")
            )
        )
    ][:50]
    return {
        "ok": True,
        "query": values.get("query.q"),
        "candidates": candidates,
        "items": candidates,
        "count": len(candidates),
        "effect_verified": True,
    }


def _notification_summary(actor: ActorContext) -> dict[str, object]:
    with tenant_readonly_session(actor.tenant_id) as session:
        notifications = _documents(session, "notification", limit=1000)
    unread = [item for item in notifications if not item.get("read_at") and not item.get("read")]
    by_kind: dict[str, int] = {}
    for item in unread:
        kind = str(item.get("kind") or item.get("type") or "general")
        by_kind[kind] = by_kind.get(kind, 0) + 1
    return {
        "ok": True,
        "total": len(notifications),
        "unread": len(unread),
        "by_kind": by_kind,
        "latest": notifications[:20],
        "effect_verified": True,
    }


def execute_legacy_read(
    tool_name: str,
    actor: ActorContext,
    raw_values: dict[str, object],
    *,
    origin: str,
) -> object:
    """Execute one explicitly supported retained read contract."""

    _ = origin
    values = dict(raw_values)
    projection = PROJECTION_READS.get(tool_name)
    if projection is not None:
        return _projection_read(actor, values, projection)
    if tool_name == "record_config":
        return _record_configuration(actor, values)
    if tool_name == "record_type_resolve":
        return _record_type_resolve(actor, values)
    if tool_name == "record_principal_resolve":
        return _record_principal_resolve(actor, values)
    if tool_name == "case_config":
        return _case_configuration(actor)
    if tool_name == "alerts_rules":
        return _alert_configuration(actor, kpi_only=False)
    if tool_name == "alerts_kpi":
        return _alert_configuration(actor, kpi_only=True)
    if tool_name == "wf_flow_preview":
        return _workflow_preview(actor, values)
    if tool_name == "wf_flow_history":
        return _workflow_history(actor, values)
    if tool_name == "shield_diagnose":
        from app.services.shield import get_shield_status

        result = get_shield_status(actor, get_settings())
        return {**result, "effect_verified": True}
    if tool_name == "people_list":
        return _people(actor)
    if tool_name == "assistant_me":
        return _assistant_profile(actor)
    if tool_name == "agent_runs_list":
        return _agent_runs(actor, values)
    if tool_name == "risk_list":
        return _risk_events(actor, values)
    if tool_name == "profile_show":
        return _user_profile(actor)
    if tool_name == "lessons_list":
        return _lessons(actor, values)
    if tool_name == "knowledge_list":
        return _knowledge(actor, values)
    if tool_name == "asset_resolve":
        return _asset_resolve(actor, values)
    if tool_name == "notifications_summary":
        return _notification_summary(actor)
    raise RuntimeError(f"unsupported legacy read adapter: {tool_name}")
