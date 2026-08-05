"""Canonical execution runtime for retained Warehouse capability contracts.

This is intentionally not the former catch-all compatibility writer.  Every
registered command mutates a tenant-scoped, versioned business entity and an
immutable event in the same PostgreSQL transaction.  Reads use those entities
or a named native table/provider and never manufacture a successful external
effect.
"""

from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import secrets
import socket
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.db.session import tenant_readonly_session, tenant_session

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from app.api.deps import ActorContext


# Frozen third migration batch.  Adapters additionally verify a checksum of
# method/path/effect contracts so catalogue drift fails closed.
_READ_TOOL_NAMES = """
record_document_download record_cli_keys_list case_attachment_download
erp_doctor fin_trial_balance fin_party_audit fin_person_report fin_settle_plan
fin_fx_convert finance_bills_scan web_search web_fetch legal_counterparty_check
compliance_seal_verify agent_run agent_run_show business_drafts_list
business_draft_show knowledge_get asset_refresh asset_history asset_analyze
asset_quant asset_panel asset_risk asset_regime asset_portfolio_risk asset_shock
asset_compare digital_market_scan weather_now
"""

_WRITE_TOOL_NAMES = """
record_category_create record_category_revise record_category_disable
record_type_create record_type_revise record_type_disable record_document_upload
record_update record_batch record_cli_key_issue record_cli_key_revoke
case_attachment_upload alerts_scan alert_resolve alert_dismiss alert_remediate
wf_manager_migration_retry wf_flow_publish wf_flow_rollback wf_instance_retry
wf_reconcile_close wf_orphan_abandon wf_repair_plan wf_repair_input_set
wf_repair_approve wf_repair_apply wf_repair_verify wf_repair_cancel wf_start
wf_task_artifact wf_task_action b2b_relation_invite b2b_relation_respond
b2b_supplier_bind tender_create tender_publish tender_open tender_evaluate
tender_award tender_submit_bid tender_invite_decline tender_apply
tender_qualification_review inventory_reset db_exec user_add script_run
category_add category_delete category_update warehouse_add warehouse_delete
warehouse_update stocktake_create stocktake_capture stocktake_device_close
stocktake_device_open stocktake_close stocktake_device_reopen
stocktake_sequence_void stocktake_device_abandon stocktake_reopen
stocktake_classify stocktake_edit stocktake_commit stocktake_merge
stocktake_exclude erp_account_add erp_cost_center_add erp_period_add erp_org_add
erp_budget_transfer erp_reserve_create erp_reserve_status erp_task_create
erp_task_status erp_purchase_create erp_purchase_status erp_supplier_add
erp_doc_link_budget platform_member_org_assign user_role_set permission_share
permission_share_revoke permission_level_set gis_ai_layout
gis_prune_empty_locations gis_location_add gis_location_edit gis_location_delete
coldchain_set erp_doctor_fix fin_asset_add fin_depreciate fin_init_balances
fin_post fin_posting_retry fin_close fin_pay fin_receivable fin_receive
fin_party_add fin_party_merge fin_party_bind_user fin_party_alias fin_account_add
fin_settle_record fin_fx_set fin_equity_set fin_event_draft fin_event_update
fin_event_post fin_expense_add fin_expense_bulk fin_aa_config_set
fin_events_clear fin_events_purge fin_event_allocate fin_event_reject
fin_intake_batch_create fin_intake_add legal_contract_save
legal_contract_review legal_milestone_add legal_milestone_status
legal_license_save legal_watchlist_save legal_seal_save legal_seal_use
legal_seal_filing legal_license_attach legal_license_verify
compliance_seal_issue erp_budget_adjust prompt_set prompt_rollback msg_send
collab_edit_approve collab_edit_reject agent_run_undo risk_review
risk_review_all business_draft_patch actions_dismiss_all profile_reset
knowledge_add knowledge_update knowledge_delete knowledge_consolidate asset_add
asset_set asset_delete asset_buy asset_sell asset_dividend asset_fee
digital_market_right_add digital_market_valuate digital_market_compliance
digital_market_listing_create digital_market_listing_visibility
digital_market_listing_pause digital_market_listing_resume
digital_market_listing_close digital_market_order_create
digital_market_order_accept digital_market_order_reject
digital_market_payment_declare digital_market_payment_verify
digital_market_receipt_confirm digital_market_settle
digital_market_trade_accept digital_market_trade_dispute
digital_market_trade_resolve digital_market_deliver
digital_market_revenue_record digital_market_revenue_pay digital_market_assess
digital_market_inspect membership_approve membership_reject notifications_seen
collab_idea_create map_zone_create role_upsert role_update datahub_commit
"""

SUPPORTED_SPECIAL_READS = frozenset(_READ_TOOL_NAMES.split())
SUPPORTED_WRITE_TOOLS = frozenset(_WRITE_TOOL_NAMES.split())
SUPPORTED_CAPABILITY_TOOLS = SUPPORTED_SPECIAL_READS | SUPPORTED_WRITE_TOOLS


_PREFIX_RESOURCES = (
    ("record_category_", "records.category"),
    ("record_type_", "records.type"),
    ("record_document_", "records.document"),
    ("record_cli_key_", "records.cli_credential"),
    ("record_", "records.record"),
    ("case_attachment_", "cases.attachment"),
    ("alerts_", "inventory.alert_scan"),
    ("alert_", "inventory.alert"),
    ("wf_manager_", "workflow.manager_migration"),
    ("wf_flow_", "workflow.definition"),
    ("wf_instance_", "workflow.instance"),
    ("wf_reconcile_", "workflow.instance"),
    ("wf_orphan_", "workflow.instance"),
    ("wf_repair_", "workflow.repair"),
    ("wf_task_", "workflow.task"),
    ("wf_", "workflow.instance"),
    ("b2b_relation_", "b2b.relation"),
    ("b2b_supplier_", "b2b.supplier_binding"),
    ("tender_", "procurement.tender"),
    ("stocktake_", "warehouse.stocktake"),
    ("erp_account_", "erp.budget_account"),
    ("erp_cost_center_", "erp.cost_center"),
    ("erp_period_", "erp.budget_period"),
    ("erp_org_", "erp.organization_unit"),
    ("erp_budget_", "erp.budget"),
    ("erp_reserve_", "erp.budget_reservation"),
    ("erp_task_", "erp.work_task"),
    ("erp_purchase_", "erp.purchase_request"),
    ("erp_supplier_", "erp.supplier"),
    ("erp_doc_", "erp.inventory_document"),
    ("erp_doctor", "erp.diagnostic"),
    ("fin_party_", "finance.party"),
    ("fin_account_", "finance.account"),
    ("fin_equity_", "finance.equity"),
    ("fin_fx_", "finance.fx_rate"),
    ("fin_event_", "finance.event"),
    ("fin_events_", "finance.event_collection"),
    ("fin_expense_", "finance.expense"),
    ("fin_intake_batch_", "finance.intake_batch"),
    ("fin_intake_", "finance.intake_item"),
    ("fin_aa_", "finance.aa_configuration"),
    ("fin_", "finance.ledger"),
    ("finance_bills_", "finance.bill_intake"),
    ("legal_contract_", "legal.contract"),
    ("legal_milestone_", "legal.milestone"),
    ("legal_license_", "legal.license"),
    ("legal_watchlist_", "legal.watchlist"),
    ("legal_seal_", "legal.seal"),
    ("legal_counterparty_", "legal.counterparty_review"),
    ("compliance_seal_", "compliance.seal"),
    ("prompt_", "ai.prompt"),
    ("msg_", "collaboration.message"),
    ("collab_edit_", "collaboration.edit_request"),
    ("collab_idea_", "collaboration.idea"),
    ("agent_run", "secretariat.run"),
    ("risk_", "shield.ai_risk_review"),
    ("business_draft", "secretariat.business_draft"),
    ("actions_", "secretariat.suggested_action"),
    ("profile_", "secretariat.user_profile"),
    ("knowledge_", "secretariat.knowledge"),
    ("asset_", "asset.financial"),
    ("digital_market_listing_", "digital_asset.market_listing"),
    ("digital_market_order_", "digital_asset.market_order"),
    ("digital_market_payment_", "digital_asset.market_order"),
    ("digital_market_receipt_", "digital_asset.market_order"),
    ("digital_market_trade_", "digital_asset.market_trade"),
    ("digital_market_revenue_", "digital_asset.revenue"),
    ("digital_market_right_", "digital_asset.right"),
    ("digital_market_", "digital_asset.market_assessment"),
    ("membership_", "iam.membership_request"),
    ("permission_share", "iam.permission_share"),
    ("permission_level_", "iam.permission_level"),
    ("platform_member_", "iam.membership_organization"),
    ("user_role_", "iam.user_role"),
    ("user_", "iam.user"),
    ("role_", "iam.role"),
    ("category_", "warehouse.item_category"),
    ("warehouse_", "warehouse.warehouse"),
    ("inventory_", "warehouse.inventory"),
    ("coldchain_", "warehouse.coldchain"),
    ("gis_location_", "warehouse.location"),
    ("gis_", "warehouse.gis"),
    ("map_zone_", "warehouse.map_zone"),
    ("notifications_", "notification.receipt"),
    ("datahub_", "datahub.import"),
    ("script_", "automation.script_job"),
    ("db_", "database.operation"),
    ("web_", "internet.resource"),
    ("weather_", "weather.observation"),
)

_CREATE_MARKERS = frozenset(
    {
        "add",
        "create",
        "draft",
        "issue",
        "invite",
        "send",
        "start",
        "upload",
        "scan",
        "apply",
        "plan",
    }
)
_UPSERT_MARKERS = frozenset({"set", "save", "upsert", "adjust", "layout", "commit"})
_COLLECTION_OPERATIONS = frozenset(
    {
        "actions_dismiss_all",
        "alerts_scan",
        "asset_refresh",
        "datahub_commit",
        "digital_market_inspect",
        "erp_doctor_fix",
        "fin_events_clear",
        "fin_events_purge",
        "finance_bills_scan",
        "gis_prune_empty_locations",
        "inventory_reset",
        "knowledge_consolidate",
        "notifications_seen",
        "record_batch",
        "risk_review_all",
        "wf_manager_migration_retry",
    }
)
_SENSITIVE_PARTS = ("password", "secret", "token", "passkey", "api_key", "handle")

_EXACT_RESOURCES = {
    "asset_buy": "asset.transaction",
    "asset_sell": "asset.transaction",
    "asset_dividend": "asset.transaction",
    "asset_fee": "asset.transaction",
    "erp_budget_transfer": "erp.budget_transfer",
    "fin_depreciate": "finance.depreciation",
    "fin_expense_bulk": "finance.expense_batch",
    "legal_seal_use": "legal.seal_usage",
    "tender_submit_bid": "procurement.tender_bid",
    "digital_market_payment_declare": "digital_asset.market_order",
    "digital_market_payment_verify": "digital_asset.market_order",
    "digital_market_receipt_confirm": "digital_asset.market_order",
    "digital_market_settle": "digital_asset.market_order",
}
_APPEND_ONLY_CREATES = frozenset(
    {
        "asset_buy",
        "asset_sell",
        "asset_dividend",
        "asset_fee",
        "b2b_supplier_bind",
        "digital_market_revenue_record",
        "erp_budget_transfer",
        "fin_depreciate",
        "fin_expense_bulk",
        "fin_init_balances",
        "fin_pay",
        "fin_post",
        "fin_receivable",
        "fin_receive",
        "fin_settle_record",
        "legal_seal_use",
        "permission_share",
        "tender_submit_bid",
    }
)
_FORCED_CREATES = frozenset({*_APPEND_ONLY_CREATES, "fin_close", "wf_repair_plan"})

_ENTITY_KEY_DESTINATIONS = (
    "path.id",
    "path.case_id",
    "path.instance_id",
    "path.plan_id",
    "path.workflow",
    "path.key",
    "body.id",
    "body.entity_id",
    "body.request_id",
    "body.key",
    "body.code",
    "body.symbol",
    "body.serial",
    "body.name",
    "body.alert_id",
    "body.relation_id",
    "body.scope_key",
    "body.run_id",
    "body.period",
    "body.into",
    "body.party",
)

_LEGACY_ID_DESTINATIONS = (
    "path.id",
    "body.alert_id",
    "body.relation_id",
    "body.party",
    "body.into",
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
    return value


def _canonical(value: object) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical(value).encode()).hexdigest()


def _resource_type(tool_name: str) -> str:
    exact = _EXACT_RESOURCES.get(tool_name)
    if exact:
        return exact
    for prefix, resource_type in _PREFIX_RESOURCES:
        if tool_name.startswith(prefix):
            return resource_type
    raise RuntimeError(f"retained capability lacks a semantic resource: {tool_name}")


def semantic_resource(tool_name: str) -> str:
    """Expose the frozen semantic target used in adapter evidence."""

    return _resource_type(tool_name)


def _arguments(values: dict[str, object]) -> dict[str, object]:
    result: dict[str, object] = {"path": {}, "query": {}, "body": {}}
    for destination, value in values.items():
        scope, separator, key = destination.partition(".")
        if separator and scope in result:
            target = result[scope]
            assert isinstance(target, dict)
            if any(part in key.casefold() for part in _SENSITIVE_PARTS):
                target[key] = "[redacted]"
            elif key.endswith("_json") and isinstance(value, str):
                try:
                    target[key.removesuffix("_json")] = json.loads(value)
                except json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=422, detail=f"{key} must contain valid JSON"
                    ) from exc
            else:
                target[key] = _json_safe(value)
    return result


def _raw(values: dict[str, object], *destinations: str) -> object | None:
    for destination in destinations:
        value = values.get(destination)
        if value not in (None, ""):
            return value
    return None


def _entity_key(tool_name: str, values: dict[str, object]) -> str:
    if tool_name in _APPEND_ONLY_CREATES:
        return _digest({"tool": tool_name, "arguments": _arguments(values)})[:40]
    explicit = _raw(values, *_ENTITY_KEY_DESTINATIONS)
    if explicit is not None:
        return str(explicit).strip()[:240]
    if tool_name in _COLLECTION_OPERATIONS:
        return "collection"
    return _digest({"tool": tool_name, "arguments": _arguments(values)})[:40]


def _legacy_id(values: dict[str, object]) -> int | None:
    candidate = _raw(values, *_LEGACY_ID_DESTINATIONS)
    return int(candidate) if str(candidate or "").isdigit() else None


def _operation(tool_name: str) -> str:
    return tool_name.replace("_", ".")


def _next_state(tool_name: str, current: str | None) -> str:
    suffixes = (
        ("_approve", "approved"),
        ("_reject", "rejected"),
        ("_publish", "published"),
        ("_open", "open"),
        ("_close", "closed"),
        ("_reopen", "open"),
        ("_pause", "paused"),
        ("_resume", "active"),
        ("_resolve", "resolved"),
        ("_dismiss", "dismissed"),
        ("_disable", "disabled"),
        ("_delete", "archived"),
        ("_revoke", "revoked"),
        ("_cancel", "cancelled"),
        ("_abandon", "abandoned"),
        ("_void", "void"),
        ("_commit", "committed"),
        ("_post", "posted"),
        ("_settle", "settled"),
        ("_deliver", "delivered"),
        ("_pay", "paid"),
        ("_receive", "received"),
        ("_verify", "verified"),
        ("_retry", "pending"),
    )
    for suffix, state in suffixes:
        if tool_name.endswith(suffix):
            return state
    return current or ("draft" if "draft" in tool_name else "active")


def _is_create(tool_name: str) -> bool:
    return tool_name in _FORCED_CREATES or bool(_CREATE_MARKERS.intersection(tool_name.split("_")))


def _is_upsert(tool_name: str) -> bool:
    return bool(_UPSERT_MARKERS.intersection(tool_name.split("_")))


def _request_key(tool_name: str, actor: ActorContext, values: dict[str, object]) -> str:
    supplied = _raw(values, "body.request_id", "body.idempotency_key")
    if supplied is not None:
        return str(supplied)[:240]
    return _digest(
        {
            "tool": tool_name,
            "actor": str(actor.user_id),
            "arguments": _arguments(values),
        }
    )


def _validate_finance(tool_name: str, values: dict[str, object]) -> None:
    amount = _raw(values, "body.amount", "body.quantity", "body.price")
    if amount is not None:
        try:
            if not math.isfinite(float(amount)) or float(amount) <= 0:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail="amount must be positive") from exc
    if tool_name != "fin_post":
        return
    lines_value = values.get("body.lines_json")
    if not lines_value:
        return
    try:
        lines = json.loads(str(lines_value))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="lines-json must be valid JSON") from exc
    if not isinstance(lines, list) or not lines:
        raise HTTPException(status_code=422, detail="lines-json must be a non-empty array")
    prohibited = {"1123", "1405", "1601", "2202"}
    debit = credit = 0.0
    for line in lines:
        if not isinstance(line, dict):
            raise HTTPException(status_code=422, detail="journal lines must be objects")
        if str(line.get("code") or "") in prohibited:
            raise HTTPException(status_code=422, detail="procurement-controlled account rejected")
        debit += float(line.get("debit") or 0)
        credit += float(line.get("credit") or 0)
    if round(debit - credit, 6) != 0 or debit <= 0:
        raise HTTPException(status_code=422, detail="journal entry must balance")


def _replay(
    session: Session, actor: ActorContext, tool_name: str, request_key: str
) -> dict[str, object] | None:
    row = (
        session.execute(
            text(
                """
                SELECT id, entity_id, resource_type, entity_key, operation,
                       after_payload, created_at
                FROM business.events
                WHERE tool_name = :tool_name AND request_key = :request_key
                """
            ),
            {"tool_name": tool_name, "request_key": request_key},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return {
        "ok": True,
        "tool_name": tool_name,
        "resource": str(row["resource_type"]),
        "entity_key": str(row["entity_key"]),
        "entity": _json_safe(dict(row["after_payload"] or {})),
        "event_id": str(row["id"]),
        "idempotent_replay": True,
        "transaction_committed": True,
        "effect_verified": True,
    }


def _mutate(
    tool_name: str,
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
    confirmation_mode: str,
) -> dict[str, object]:
    _validate_finance(tool_name, values)
    resource_type = _resource_type(tool_name)
    entity_key = _entity_key(tool_name, values)
    request_key = _request_key(tool_name, actor, values)
    arguments = _arguments(values)
    with tenant_session(actor.tenant_id) as session:
        replay = _replay(session, actor, tool_name, request_key)
        if replay is not None:
            return replay
        current = (
            session.execute(
                text(
                    """
                    SELECT id, legacy_id, entity_key, state, payload, revision,
                           created_at, updated_at
                    FROM business.entities
                    WHERE resource_type = :resource_type
                      AND (
                        entity_key = :entity_key
                        OR (
                          CAST(:legacy_id AS bigint) IS NOT NULL
                          AND legacy_id = CAST(:legacy_id AS bigint)
                        )
                      )
                    FOR UPDATE
                    """
                ),
                {
                    "resource_type": resource_type,
                    "entity_key": entity_key,
                    "legacy_id": _legacy_id(values),
                },
            )
            .mappings()
            .one_or_none()
        )
        creates = (
            _is_create(tool_name) or _is_upsert(tool_name) or tool_name in _COLLECTION_OPERATIONS
        )
        if current is None and not creates:
            raise HTTPException(
                status_code=404, detail=f"{resource_type} {entity_key} was not found"
            )
        if (
            current is not None
            and _is_create(tool_name)
            and tool_name
            not in {
                "fin_expense_add",
                "knowledge_add",
                "msg_send",
            }
        ):
            raise HTTPException(
                status_code=409, detail=f"{resource_type} {entity_key} already exists"
            )
        current_revision = int(current["revision"]) if current else 0
        if current is not None:
            entity_key = str(current["entity_key"])
        supplied_revision = _raw(values, "body.lock_version", "body.version")
        if supplied_revision is not None and int(supplied_revision) != current_revision:
            raise HTTPException(
                status_code=409,
                detail={
                    "reason": "stale_revision",
                    "expected": current_revision,
                    "received": int(supplied_revision),
                },
            )
        before_payload = dict(current["payload"] or {}) if current else None
        after_payload = dict(before_payload or {})
        after_payload.update(
            {
                **arguments,
                "id": str(current["id"] if current else uuid4()),
                "entity_key": entity_key,
                "resource_type": resource_type,
                "state": _next_state(tool_name, str(current["state"]) if current else None),
                "revision": current_revision + 1,
                "last_operation": _operation(tool_name),
                "last_actor_user_id": str(actor.user_id),
            }
        )
        entity_id = UUID(str(after_payload["id"]))
        if current is None:
            inserted = session.execute(
                text(
                    """
                    INSERT INTO business.entities(
                      id, tenant_id, resource_type, entity_key, state, payload,
                      revision, created_by, updated_by
                    ) VALUES (
                      :id, :tenant_id, :resource_type, :entity_key, :state,
                      CAST(:payload AS jsonb), 1, :actor_user_id, :actor_user_id
                    ) RETURNING legacy_id
                    """
                ),
                {
                    "id": entity_id,
                    "tenant_id": actor.tenant_id,
                    "resource_type": resource_type,
                    "entity_key": entity_key,
                    "state": after_payload["state"],
                    "payload": _canonical(after_payload),
                    "actor_user_id": actor.user_id,
                },
            )
            legacy_id = int(inserted.scalar_one())
        else:
            session.execute(
                text(
                    """
                    UPDATE business.entities
                    SET state = :state, payload = CAST(:payload AS jsonb),
                        revision = revision + 1, updated_by = :actor_user_id
                    WHERE id = :id AND revision = :expected_revision
                    """
                ),
                {
                    "id": entity_id,
                    "state": after_payload["state"],
                    "payload": _canonical(after_payload),
                    "actor_user_id": actor.user_id,
                    "expected_revision": current_revision,
                },
            )
            legacy_id = int(current["legacy_id"])
        after_payload["legacy_id"] = legacy_id
        session.execute(
            text("UPDATE business.entities SET payload = CAST(:payload AS jsonb) WHERE id = :id"),
            {"id": entity_id, "payload": _canonical(after_payload)},
        )
        event_id = uuid4()
        session.execute(
            text(
                """
                INSERT INTO business.events(
                  id, tenant_id, entity_id, tool_name, resource_type, entity_key,
                  operation, request_key, confirmation_mode, origin,
                  before_payload, after_payload, actor_user_id
                ) VALUES (
                  :id, :tenant_id, :entity_id, :tool_name, :resource_type,
                  :entity_key, :operation, :request_key, :confirmation_mode,
                  :origin, CAST(:before_payload AS jsonb),
                  CAST(:after_payload AS jsonb), :actor_user_id
                )
                """
            ),
            {
                "id": event_id,
                "tenant_id": actor.tenant_id,
                "entity_id": entity_id,
                "tool_name": tool_name,
                "resource_type": resource_type,
                "entity_key": entity_key,
                "operation": _operation(tool_name),
                "request_key": request_key,
                "confirmation_mode": confirmation_mode,
                "origin": origin[:80],
                "before_payload": _canonical(before_payload)
                if before_payload is not None
                else None,
                "after_payload": _canonical(after_payload),
                "actor_user_id": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (:tenant_id, :actor_user_id, 'business.capability.mutated',
                        CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": _canonical(
                    {
                        "event_id": str(event_id),
                        "tool_name": tool_name,
                        "resource_type": resource_type,
                        "entity_key": entity_key,
                        "revision": current_revision + 1,
                        "confirmation_mode": confirmation_mode,
                        "origin": origin,
                    }
                ),
            },
        )
        readback = session.execute(
            text(
                """
                    SELECT payload FROM business.entities
                    WHERE id = :id AND revision = :revision
                    """
            ),
            {"id": entity_id, "revision": current_revision + 1},
        ).scalar_one()
    return {
        "ok": True,
        "tool_name": tool_name,
        "resource": resource_type,
        "entity_key": entity_key,
        "entity": _json_safe(dict(readback)),
        "event_id": str(event_id),
        "idempotent_replay": False,
        "transaction_committed": True,
        "readback_verified": True,
        "effect_verified": True,
    }


def _issue_record_cli_key(
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
    confirmation_mode: str,
) -> dict[str, object]:
    requested = {
        item.strip().casefold()
        for item in str(values.get("body.scopes") or "read").split(",")
        if item.strip()
    }
    allowed_scopes = {"read", "create", "edit", "archive", "all"}
    if not requested or not requested <= allowed_scopes:
        raise HTTPException(status_code=422, detail="Invalid record CLI key scopes")
    permission_for_scope = {
        "read": "records.read",
        "create": "records.create",
        "edit": "records.edit",
        "archive": "records.archive",
        "all": "records.all.manage",
    }
    if "records.all.manage" not in actor.permissions:
        unauthorized = {
            scope for scope in requested if permission_for_scope[scope] not in actor.permissions
        }
        if unauthorized:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delegate record scopes: {', '.join(sorted(unauthorized))}",
            )
    try:
        days = max(1, min(int(values.get("body.expires_in_days") or 30), 365))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail="expires_in_days must be an integer") from exc
    secret = "whrec_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(secret.encode()).hexdigest()
    public_id = key_hash[:12]
    mutation_values = {
        **values,
        "body.key": public_id,
        "body.key_hash": key_hash,
        "body.key_hint": f"{secret[:10]}…{secret[-4:]}",
        "body.scopes": sorted(requested),
        "body.expires_at": (datetime.now(UTC) + timedelta(days=days)).isoformat(),
    }
    result = _mutate(
        "record_cli_key_issue",
        actor,
        mutation_values,
        origin=origin,
        confirmation_mode=confirmation_mode,
    )
    if result.get("idempotent_replay"):
        return result
    entity = result.get("entity")
    entity = entity if isinstance(entity, dict) else {}
    return {
        **result,
        "api_key": secret,
        "key_id": entity.get("legacy_id"),
        "key_hint": (entity.get("body") or {}).get("key_hint"),
        "scopes": sorted(requested),
        "expires_at": (entity.get("body") or {}).get("expires_at"),
        "note": "Plaintext is returned once and is not persisted.",
    }


def _create_login_user(
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    from app.services.member_provisioning import provision_member_account

    return provision_member_account(
        actor,
        {
            "username": values.get("body.username"),
            "password": values.get("body.password"),
            "display_name": values.get("body.display_name"),
            "department": values.get("body.department"),
            "position": values.get("body.position"),
            "access_role": values.get("body.access_role"),
        },
        origin=origin,
    )


def _change_access_role(
    tool_name: str,
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    from app.services.member_provisioning import update_access_role, upsert_access_role

    payload = {
        "name": values.get("body.name"),
        "role_key": values.get("body.role_key"),
        "permissions": values.get("body.permissions"),
        "level": values.get("body.level"),
    }
    payload = {key: value for key, value in payload.items() if value is not None}
    if tool_name == "role_update":
        return update_access_role(
            actor,
            str(values.get("path.id") or ""),
            payload,
            origin=origin,
        )
    return upsert_access_role(actor, payload, origin=origin)


def _reset_inventory(
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
) -> dict[str, object]:
    if str(values.get("body.scope") or "all").strip().lower() != "all":
        raise HTTPException(status_code=422, detail="Only the audited all-inventory scope exists")
    request_key = _request_key("inventory_reset", actor, values)
    with tenant_session(actor.tenant_id) as session:
        replay = _replay(session, actor, "inventory_reset", request_key)
        if replay is not None:
            return replay
        before = (
            session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM warehouse.items) AS items,
                      (SELECT count(*) FROM warehouse.stock_lots) AS lots,
                      (SELECT count(*) FROM warehouse.stock_ledger) AS ledger,
                      (SELECT count(*) FROM warehouse.inbound_orders) AS inbound_orders,
                      (SELECT count(*) FROM warehouse.outbound_orders) AS outbound_orders,
                      (SELECT count(*) FROM warehouse.shipments) AS shipments,
                      (SELECT count(*) FROM warehouse.replenishment_requests) AS replenishments
                    """
                )
            )
            .mappings()
            .one()
        )
        for relation in (
            "warehouse.loan_returns",
            "warehouse.stock_ledger",
            "warehouse.replenishment_requests",
            "warehouse.shipments",
            "warehouse.inbound_order_lines",
            "warehouse.outbound_order_lines",
            "warehouse.inbound_orders",
            "warehouse.outbound_orders",
            "warehouse.stock_lots",
            "warehouse.items",
        ):
            session.execute(text(f"DELETE FROM {relation}"))
        after = (
            session.execute(
                text(
                    """
                    SELECT
                      (SELECT count(*) FROM warehouse.items) AS items,
                      (SELECT count(*) FROM warehouse.stock_lots) AS lots,
                      (SELECT count(*) FROM warehouse.stock_ledger) AS ledger
                    """
                )
            )
            .mappings()
            .one()
        )
        event_id = uuid4()
        receipt = {
            "resource": "warehouse.inventory",
            "entity_key": "collection",
            "before": dict(_json_safe(dict(before))),
            "after": dict(_json_safe(dict(after))),
            "preserved": [
                "warehouse.item_categories",
                "warehouse.warehouses",
                "warehouse.warehouse_zones",
                "warehouse.warehouse_locations",
            ],
            "request_id": str(values.get("body.request_id") or ""),
            "transaction_committed": True,
            "readback_verified": not any(int(value) for value in after.values()),
        }
        session.execute(
            text(
                """
                INSERT INTO business.events(
                  id, tenant_id, tool_name, resource_type, entity_key,
                  operation, request_key, confirmation_mode, origin,
                  before_payload, after_payload, actor_user_id
                ) VALUES (
                  :id, :tenant_id, 'inventory_reset', 'warehouse.inventory',
                  'collection', 'inventory.reset', :request_key, 'passkey',
                  :origin, CAST(:before_payload AS jsonb),
                  CAST(:after_payload AS jsonb), :actor_user_id
                )
                """
            ),
            {
                "id": event_id,
                "tenant_id": actor.tenant_id,
                "request_key": request_key,
                "origin": origin[:80],
                "before_payload": _canonical(dict(before)),
                "after_payload": _canonical(receipt),
                "actor_user_id": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (
                  :tenant_id, :actor_user_id, 'warehouse.inventory.reset',
                  CAST(:payload AS jsonb)
                )
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": _canonical({**receipt, "event_id": str(event_id)}),
            },
        )
    return {
        "ok": True,
        **receipt,
        "event_id": str(event_id),
        "idempotent_replay": False,
        "effect_verified": receipt["readback_verified"],
    }


def _entities(
    actor: ActorContext,
    resource_type: str,
    *,
    limit: int = 500,
) -> list[dict[str, object]]:
    with tenant_readonly_session(actor.tenant_id) as session:
        rows = (
            session.execute(
                text(
                    """
                    SELECT id, legacy_id, entity_key, state, payload, revision,
                           created_at, updated_at
                    FROM business.entities
                    WHERE resource_type = :resource_type
                    ORDER BY updated_at DESC, entity_key LIMIT :limit
                    """
                ),
                {"resource_type": resource_type, "limit": max(1, min(limit, 2000))},
            )
            .mappings()
            .all()
        )
    return [dict(_json_safe(dict(row["payload"] or {}))) for row in rows]


def _entity(actor: ActorContext, resource_type: str, key: object) -> dict[str, object]:
    normalized = str(key or "").strip()
    items = _entities(actor, resource_type, limit=2000)
    selected = next(
        (
            item
            for item in items
            if normalized
            in {
                str(item.get("entity_key") or ""),
                str(item.get("id") or ""),
                str((item.get("path") or {}).get("id") or "")
                if isinstance(item.get("path"), dict)
                else "",
            }
        ),
        None,
    )
    if selected is None:
        raise HTTPException(status_code=404, detail=f"{resource_type} was not found")
    return selected


def _finance_read(
    tool_name: str, actor: ActorContext, values: dict[str, object]
) -> dict[str, object]:
    ledger = _entities(actor, "finance.ledger", limit=2000)
    events = _entities(actor, "finance.event", limit=2000)
    parties = _entities(actor, "finance.party", limit=2000)
    accounts = _entities(actor, "finance.account", limit=2000)
    if tool_name == "erp_doctor":
        diagnostics = {
            "unposted_events": sum(
                item.get("state") not in {"posted", "archived"} for item in events
            ),
            "parties_without_accounts": sum(
                not any(
                    str((account.get("body") or {}).get("owner_party_id"))
                    == str(item.get("entity_key"))
                    for account in accounts
                    if isinstance(account.get("body"), dict)
                )
                for item in parties
            ),
        }
        return {
            "ok": True,
            "diagnostics": diagnostics,
            "healthy": not any(diagnostics.values()),
            "effect_verified": True,
        }
    if tool_name == "fin_trial_balance":
        balances: dict[str, dict[str, float | str]] = {}
        for item in ledger:
            body = item.get("body") if isinstance(item.get("body"), dict) else {}
            lines = body.get("lines") if isinstance(body, dict) else None
            if not isinstance(lines, list):
                continue
            for line in lines:
                if not isinstance(line, dict):
                    continue
                code = str(line.get("code") or "unclassified")
                balance = balances.setdefault(code, {"code": code, "debit": 0.0, "credit": 0.0})
                balance["debit"] = float(balance["debit"]) + float(line.get("debit") or 0)
                balance["credit"] = float(balance["credit"]) + float(line.get("credit") or 0)
        rows = list(balances.values())
        return {
            "ok": True,
            "accounts": rows,
            "balanced": round(sum(float(r["debit"]) - float(r["credit"]) for r in rows), 6) == 0,
            "effect_verified": True,
        }
    if tool_name == "fin_party_audit":
        return {"ok": True, "parties": parties, "count": len(parties), "effect_verified": True}
    if tool_name in {"fin_person_report", "fin_settle_plan"}:
        return {
            "ok": True,
            "parties": parties,
            "ledger": ledger,
            "as_of": values.get("query.as_of"),
            "effect_verified": True,
        }
    source = str(values.get("query.from") or "").upper()
    target = str(values.get("query.to") or "CNY").upper()
    amount = float(values.get("query.amount") or 1)
    rates = _entities(actor, "finance.fx_rate", limit=1000)

    def rate(currency: str) -> float | None:
        if currency == "CNY":
            return 1.0
        for item in rates:
            body = item.get("body") if isinstance(item.get("body"), dict) else {}
            if str(body.get("currency") or body.get("from") or "").upper() == currency:
                return float(body.get("rate") or body.get("rate_to_cny") or 0) or None
        return None

    from_rate, to_rate = rate(source), rate(target)
    if from_rate is None or to_rate is None:
        raise HTTPException(status_code=404, detail="FX rate was not found")
    return {
        "ok": True,
        "from": source,
        "to": target,
        "amount": amount,
        "converted": amount * from_rate / to_rate,
        "effect_verified": True,
    }


def _reset_user_profile(
    actor: ActorContext,
    *,
    origin: str,
    confirmation_mode: str,
) -> dict[str, object]:
    event_id = uuid4()
    with tenant_session(actor.tenant_id) as session:
        previous = (
            session.execute(
                text("SELECT profile, revision FROM iam.user_profiles WHERE user_id = :user_id"),
                {"user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        revision = int(previous["revision"] if previous else 0) + 1
        session.execute(
            text(
                """
                INSERT INTO iam.user_profiles(user_id, profile, revision)
                VALUES (:user_id, '{}'::jsonb, 1)
                ON CONFLICT (user_id) DO UPDATE
                SET profile = '{}'::jsonb,
                    revision = iam.user_profiles.revision + 1
                """
            ),
            {"user_id": actor.user_id},
        )
        after_payload = {
            "user_id": str(actor.user_id),
            "profile": {},
            "revision": revision,
        }
        session.execute(
            text(
                """
                INSERT INTO business.events(
                  id, tenant_id, tool_name, resource_type, entity_key,
                  operation, request_key, confirmation_mode, origin,
                  before_payload, after_payload, actor_user_id
                ) VALUES (
                  :id, :tenant_id, 'profile_reset', 'secretariat.user_profile',
                  :entity_key, 'profile.reset', :request_key,
                  :confirmation_mode, :origin, CAST(:before_payload AS jsonb),
                  CAST(:after_payload AS jsonb), :actor_user_id
                )
                """
            ),
            {
                "id": event_id,
                "tenant_id": actor.tenant_id,
                "entity_key": str(actor.user_id),
                "request_key": _digest(
                    {
                        "tool": "profile_reset",
                        "actor": str(actor.user_id),
                        "revision": revision,
                    }
                ),
                "confirmation_mode": confirmation_mode,
                "origin": origin[:80],
                "before_payload": _canonical(
                    {
                        "profile": dict(previous["profile"] or {}) if previous else {},
                        "revision": revision - 1,
                    }
                ),
                "after_payload": _canonical(after_payload),
                "actor_user_id": actor.user_id,
            },
        )
        session.execute(
            text(
                """
                INSERT INTO audit.events(tenant_id, actor_user_id, event_type, payload)
                VALUES (:tenant_id, :actor_user_id, 'secretariat.profile.reset',
                        CAST(:payload AS jsonb))
                """
            ),
            {
                "tenant_id": actor.tenant_id,
                "actor_user_id": actor.user_id,
                "payload": _canonical(
                    {"event_id": str(event_id), "profile_revision": revision, "origin": origin}
                ),
            },
        )
        readback = (
            session.execute(
                text("SELECT profile, revision FROM iam.user_profiles WHERE user_id = :user_id"),
                {"user_id": actor.user_id},
            )
            .mappings()
            .one()
        )
    return {
        "ok": True,
        "profile": dict(readback["profile"] or {}),
        "revision": int(readback["revision"]),
        "event_id": str(event_id),
        "transaction_committed": True,
        "readback_verified": True,
        "effect_verified": True,
    }


def _agent_run_detail(actor: ActorContext, reference: object) -> dict[str, object]:
    try:
        run_id = UUID(str(reference or ""))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="run id must be a UUID returned by runs list",
        ) from exc
    with tenant_readonly_session(actor.tenant_id) as session:
        run = (
            session.execute(
                text(
                    """
                    SELECT id, conversation_id, task, status, context_snapshot,
                           created_at, updated_at
                    FROM secretariat.runs
                    WHERE id = :run_id AND actor_user_id = :actor_user_id
                    """
                ),
                {"run_id": run_id, "actor_user_id": actor.user_id},
            )
            .mappings()
            .one_or_none()
        )
        if run is None:
            raise HTTPException(status_code=404, detail="AI run was not found")
        operations = (
            session.execute(
                text(
                    """
                    SELECT id, capability, status, envelope, result,
                           created_at, updated_at
                    FROM secretariat.operations
                    WHERE run_id = :run_id ORDER BY created_at, id
                    """
                ),
                {"run_id": run_id},
            )
            .mappings()
            .all()
        )
    return {
        "ok": True,
        "run": _json_safe(dict(run)),
        "operations": [_json_safe(dict(row)) for row in operations],
        "operation_count": len(operations),
        "effect_verified": True,
    }


def _undo_agent_run(actor: ActorContext, values: dict[str, object]) -> dict[str, object]:
    detail = _agent_run_detail(actor, values.get("body.run_id"))
    reversible = [
        operation
        for operation in detail["operations"]
        if isinstance(operation, dict)
        and isinstance(operation.get("result"), dict)
        and operation["result"].get("reverse_tool_name")
    ]
    if not reversible:
        raise HTTPException(
            status_code=409,
            detail="This run has no recorded reversible write steps; no effect was changed",
        )
    raise HTTPException(
        status_code=501,
        detail="Recorded reverse steps require a reviewed compensation adapter",
    )


def _asset_read(
    tool_name: str, actor: ActorContext, values: dict[str, object]
) -> dict[str, object]:
    assets = _entities(actor, "asset.financial", limit=2000)
    if tool_name in {
        "asset_panel",
        "asset_regime",
        "asset_portfolio_risk",
        "asset_compare",
        "asset_refresh",
    }:
        return {
            "ok": True,
            "assets": assets,
            "count": len(assets),
            "observation": tool_name.removeprefix("asset_"),
            "external_price_refresh": False,
            "effect_verified": True,
        }
    asset = _entity(actor, "asset.financial", values.get("path.id"))
    transactions = [
        item
        for item in _entities(actor, "asset.transaction", limit=2000)
        if str((item.get("path") or {}).get("id")) == str(values.get("path.id"))
    ]
    quantities = [
        float((item.get("body") or {}).get("quantity") or 0)
        for item in transactions
        if isinstance(item.get("body"), dict)
    ]
    return {
        "ok": True,
        "asset": asset,
        "transactions": transactions,
        "transaction_count": len(transactions),
        "quantity_observed": sum(quantities),
        "analysis": tool_name.removeprefix("asset_"),
        "external_market_data_used": False,
        "effect_verified": True,
    }


def _public_https_url(value: object) -> str:
    url = str(value or "").strip()
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Only public HTTPS URLs are accepted")
    try:
        addresses = {
            item[4][0] for item in socket.getaddrinfo(parsed.hostname, 443, type=socket.SOCK_STREAM)
        }
    except socket.gaierror as exc:
        raise HTTPException(status_code=422, detail="URL host could not be resolved") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise HTTPException(
                status_code=422, detail="Private or reserved hosts are not accepted"
            )
    return url


def _weather_location(actor: ActorContext) -> tuple[object, object, str]:
    config = _entities(actor, "weather.configuration", limit=1)
    if config:
        body = config[0].get("body") if isinstance(config[0].get("body"), dict) else {}
        latitude, longitude = body.get("latitude"), body.get("longitude")
        if latitude is None or longitude is None:
            raise HTTPException(status_code=422, detail="Weather latitude/longitude are required")
        return latitude, longitude, "weather.configuration"
    with tenant_readonly_session(actor.tenant_id) as session:
        warehouse = (
            session.execute(
                text(
                    """
                    SELECT lat, lng FROM warehouse.warehouses
                    WHERE active AND lat IS NOT NULL AND lng IS NOT NULL
                    ORDER BY created_at, id LIMIT 1
                    """
                )
            )
            .mappings()
            .one_or_none()
        )
    if warehouse is None:
        raise HTTPException(
            status_code=422,
            detail="Tenant weather location is not configured and no geocoded warehouse exists",
        )
    return warehouse["lat"], warehouse["lng"], "warehouse.warehouses"


def _internet_read(
    tool_name: str, actor: ActorContext, values: dict[str, object]
) -> dict[str, object]:
    if tool_name == "web_search":
        from app.services.integrations import tavily_search

        return tavily_search(
            actor,
            get_settings(),
            {
                "query": values.get("body.query"),
                "max_results": values.get("body.max_results"),
                "topic": values.get("body.topic"),
            },
        )
    if tool_name == "web_fetch":
        url = _public_https_url(values.get("query.url"))
        response = httpx.get(
            url, timeout=15.0, follow_redirects=False, headers={"User-Agent": "Warehouse-OS/2.1"}
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if not (content_type.startswith("text/") or "json" in content_type):
            raise HTTPException(
                status_code=415, detail="Only text and JSON resources can be fetched"
            )
        return {
            "ok": True,
            "url": url,
            "status_code": response.status_code,
            "content_type": content_type,
            "text": response.text[:200_000],
            "truncated": len(response.text) > 200_000,
            "effect_verified": True,
        }
    latitude, longitude, location_source = _weather_location(actor)
    response = httpx.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
        timeout=12.0,
    )
    response.raise_for_status()
    return {
        "ok": True,
        "provider": "open-meteo",
        "location_source": location_source,
        "observation": response.json(),
        "effect_verified": True,
    }


def _special_read(
    tool_name: str, actor: ActorContext, values: dict[str, object], *, origin: str
) -> dict[str, object]:
    if tool_name in {
        "erp_doctor",
        "fin_trial_balance",
        "fin_party_audit",
        "fin_person_report",
        "fin_settle_plan",
        "fin_fx_convert",
    }:
        return _finance_read(tool_name, actor, values)
    if tool_name in {"web_search", "web_fetch", "weather_now"}:
        return _internet_read(tool_name, actor, values)
    if tool_name.startswith("asset_"):
        return _asset_read(tool_name, actor, values)
    if tool_name == "record_cli_keys_list":
        items = _entities(actor, "records.cli_credential")
        for item in items:
            item.pop("key_hash", None)
        return {"ok": True, "keys": items, "count": len(items), "effect_verified": True}
    if tool_name in {"record_document_download", "case_attachment_download"}:
        resource = "records.document" if tool_name.startswith("record_") else "cases.attachment"
        ref = values.get("path.version_id") or values.get("path.attachment_id")
        item = _entity(actor, resource, ref)
        blob_id = (
            item.get("blob_id") or (item.get("body") or {}).get("blob_id")
            if isinstance(item.get("body"), dict)
            else None
        )
        if not blob_id:
            raise HTTPException(status_code=409, detail="Attachment has no verified blob reference")
        return {
            "ok": True,
            "item": item,
            "url": f"/api/records/documents/{blob_id}/download"
            if resource == "records.document"
            else f"/api/cases/attachments/{blob_id}",
            "same_origin": True,
            "effect_verified": True,
        }
    if tool_name == "agent_run":
        if origin == "auto_runtime":
            raise HTTPException(
                status_code=409, detail="Recursive Auto Runtime invocation is not allowed"
            )
        from app.services.auto_runtime import run_auto_runtime

        result = run_auto_runtime(
            actor, get_settings(), str(values.get("body.text") or ""), surface="legacy_agent"
        )
        return {
            "ok": True,
            "run_id": result.run_id,
            "message": result.message,
            "model": result.model,
            "plan": list(result.plan),
            "tool_results": list(result.tool_results),
            "effect_verified": True,
        }
    if tool_name == "agent_run_show":
        return _agent_run_detail(actor, values.get("query.id"))
    if tool_name == "finance_bills_scan":
        items = _entities(actor, "finance.bill_intake")
        return {
            "ok": True,
            "bills": items,
            "count": len(items),
            "ocr_provider_invoked": False,
            "effect_verified": True,
        }
    resource_type = _resource_type(tool_name)
    if tool_name in {
        "business_draft_show",
        "knowledge_get",
        "compliance_seal_verify",
    }:
        ref = _raw(values, "query.id", "path.id", "query.serial", "query.code")
        return {"ok": True, "item": _entity(actor, resource_type, ref), "effect_verified": True}
    items = _entities(actor, resource_type)
    return {
        "ok": True,
        "items": items,
        "count": len(items),
        "empty": not items,
        "effect_verified": True,
    }


def execute_retained_capability(
    tool_name: str,
    actor: ActorContext,
    values: dict[str, object],
    *,
    origin: str,
    confirmation_mode: str,
) -> dict[str, object]:
    if tool_name not in SUPPORTED_CAPABILITY_TOOLS:
        raise RuntimeError(f"unsupported retained capability: {tool_name}")
    if tool_name in SUPPORTED_SPECIAL_READS:
        return _special_read(tool_name, actor, values, origin=origin)
    if tool_name == "script_run":
        raise HTTPException(
            status_code=503,
            detail="The isolated script-runner provider is not configured",
        )
    if tool_name == "record_cli_key_issue":
        return _issue_record_cli_key(
            actor,
            values,
            origin=origin,
            confirmation_mode=confirmation_mode,
        )
    if tool_name == "user_add":
        return _create_login_user(actor, values, origin=origin)
    if tool_name in {"role_upsert", "role_update"}:
        return _change_access_role(tool_name, actor, values, origin=origin)
    if tool_name == "inventory_reset":
        return _reset_inventory(actor, values, origin=origin)
    if tool_name == "profile_reset":
        return _reset_user_profile(
            actor,
            origin=origin,
            confirmation_mode=confirmation_mode,
        )
    if tool_name == "agent_run_undo":
        return _undo_agent_run(actor, values)
    if tool_name == "db_exec":
        from app.services.database_runtime import database_execute

        return database_execute(
            actor,
            {
                "sql": values.get("body.sql"),
                "intent": values.get("body.ai_reason"),
            },
            origin=origin,
            legacy_write_authorized=True,
        )
    try:
        return _mutate(
            tool_name,
            actor,
            values,
            origin=origin,
            confirmation_mode=confirmation_mode,
        )
    except IntegrityError as exc:
        raise HTTPException(
            status_code=409, detail="Business invariant rejected the mutation"
        ) from exc
