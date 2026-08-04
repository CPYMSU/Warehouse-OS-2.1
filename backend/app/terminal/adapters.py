"""Explicit, verified adapters for legacy capability genes.

Mounted FastAPI routes remain the preferred execution surface.  This registry
exists for retained command contracts whose stable public path differs from a
newer domain service.  Registration is deliberately strict: catalogue method,
path, effect and semantic resource must all match before a command can become
active.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.services.legacy_capability_runtime import (
    SUPPORTED_CAPABILITY_TOOLS as _SUPPORTED_CAPABILITY_TOOLS,
)
from app.services.legacy_capability_runtime import (
    execute_retained_capability,
)
from app.services.legacy_capability_runtime import (
    semantic_resource as _capability_semantic_resource,
)
from app.services.legacy_read_runtime import (
    SUPPORTED_LEGACY_READS as _SUPPORTED_LEGACY_READS,
)
from app.terminal import legacy_catalog as _legacy_catalog

if TYPE_CHECKING:
    from app.api.deps import ActorContext


AdapterHandler = Callable[
    ["ActorContext", Mapping[str, object], str],
    object,
]


@dataclass(frozen=True)
class VerifiedCapabilityAdapter:
    tool_name: str
    api_method: str
    api_path: str
    effect: str
    domain: str
    semantic_resource: str
    verification: str
    handler: AdapterHandler


_ADAPTERS: dict[str, VerifiedCapabilityAdapter] = {}


def _register(adapter: VerifiedCapabilityAdapter) -> None:
    if adapter.tool_name in _ADAPTERS:
        raise RuntimeError(f"duplicate capability adapter: {adapter.tool_name}")
    if adapter.effect not in {"read", "write"}:
        raise RuntimeError(f"invalid adapter effect: {adapter.effect}")
    if not adapter.semantic_resource.strip() or not adapter.verification.strip():
        raise RuntimeError(f"adapter lacks semantic evidence: {adapter.tool_name}")
    _ADAPTERS[adapter.tool_name] = adapter


def _inventory_list(
    actor: ActorContext,
    values: Mapping[str, object],
    _origin: str,
) -> object:
    from app.services.warehouse_operations import inventory_list_payload

    return inventory_list_payload(actor, category=values.get("query.category"))


def _ledger_list(
    actor: ActorContext,
    values: Mapping[str, object],
    _origin: str,
) -> object:
    from app.services.warehouse_operations import stock_ledger_payload

    return stock_ledger_payload(actor, category=values.get("query.category"))


def _category_list(
    actor: ActorContext,
    _values: Mapping[str, object],
    _origin: str,
) -> object:
    from app.services.warehouse_operations import item_categories_payload

    return item_categories_payload(actor)


def _database_schema(
    actor: ActorContext,
    values: Mapping[str, object],
    _origin: str,
) -> object:
    from app.services.database_runtime import legacy_database_schema

    return legacy_database_schema(
        actor,
        {
            "domain": values.get("body.domain"),
            "table": values.get("body.table"),
        },
    )


def _database_query(
    actor: ActorContext,
    values: Mapping[str, object],
    origin: str,
) -> object:
    from app.services.database_runtime import legacy_database_query

    return legacy_database_query(
        actor,
        {
            "sql": values.get("body.sql"),
            "limit": values.get("body.limit"),
        },
        origin=origin,
    )


def _retained_read_handler(tool_name: str) -> AdapterHandler:
    """Bind one frozen catalogue tool to the explicit read-runtime registry."""

    def execute(
        actor: ActorContext,
        values: Mapping[str, object],
        origin: str,
    ) -> object:
        from app.services.legacy_read_runtime import execute_legacy_read

        return execute_legacy_read(tool_name, actor, dict(values), origin=origin)

    return execute


for _adapter in (
    VerifiedCapabilityAdapter(
        tool_name="inventory_list",
        api_method="GET",
        api_path="/api/inventory",
        effect="read",
        domain="inventory",
        semantic_resource="warehouse.inventory_balance",
        verification="postgresql_rls_read",
        handler=_inventory_list,
    ),
    VerifiedCapabilityAdapter(
        tool_name="ledger_list",
        api_method="GET",
        api_path="/api/ledger",
        effect="read",
        domain="inventory",
        semantic_resource="warehouse.stock_ledger",
        verification="postgresql_rls_read",
        handler=_ledger_list,
    ),
    VerifiedCapabilityAdapter(
        tool_name="category_list_tenant",
        api_method="GET",
        api_path="/api/categories",
        effect="read",
        domain="inventory",
        semantic_resource="warehouse.item_category",
        verification="postgresql_rls_read",
        handler=_category_list,
    ),
    VerifiedCapabilityAdapter(
        tool_name="db_schema",
        api_method="POST",
        api_path="/api/db/schema",
        effect="read",
        domain="system",
        semantic_resource="database.physical_schema",
        verification="postgresql_catalog_and_privileges",
        handler=_database_schema,
    ),
    VerifiedCapabilityAdapter(
        tool_name="db_query",
        api_method="POST",
        api_path="/api/db/query",
        effect="read",
        domain="system",
        semantic_resource="database.query_result",
        verification="postgresql_read_only_transaction",
        handler=_database_query,
    ),
):
    _register(_adapter)


# Second migration batch: every tuple freezes the imported method/path and the
# real PostgreSQL resource used for evidence.  The service registry is checked
# independently so a typo cannot advertise a command whose handler is absent.
_RETAINED_READ_ADAPTERS = (
    (
        "record_config",
        "GET",
        "/api/records/config",
        "records",
        "records.configuration",
        "postgresql_rls_read",
    ),
    (
        "record_type_resolve",
        "GET",
        "/api/records/type/resolve",
        "records",
        "records.type_configuration",
        "postgresql_rls_read",
    ),
    (
        "record_principal_resolve",
        "GET",
        "/api/records/principals/resolve",
        "records",
        "iam.tenant_principal",
        "postgresql_rls_read",
    ),
    (
        "case_config",
        "GET",
        "/api/cases/config",
        "records",
        "cases.configuration",
        "postgresql_rls_read",
    ),
    (
        "alerts_rules",
        "GET",
        "/api/alerts/rules",
        "inventory",
        "alerts.rule_configuration",
        "postgresql_rls_read",
    ),
    (
        "alerts_kpi",
        "GET",
        "/api/alerts/kpi",
        "inventory",
        "alerts.kpi_configuration",
        "postgresql_rls_read",
    ),
    (
        "wf_flow_preview",
        "POST",
        "/api/wf/workflows/{workflow}/preview",
        "org",
        "workflow.definition_preview",
        "database_version_checked_readonly_preview",
    ),
    (
        "wf_flow_history",
        "GET",
        "/api/wf/workflows/{workflow}/history",
        "org",
        "workflow.definition_history",
        "postgresql_rls_read",
    ),
    (
        "wf_repair_show",
        "GET",
        "/api/wf/repairs/{case_id}",
        "org",
        "workflow.repair_case",
        "postgresql_rls_read_projection",
    ),
    (
        "wf_repair_watch",
        "GET",
        "/api/wf/repairs/{case_id}",
        "org",
        "workflow.repair_case",
        "postgresql_rls_read_projection",
    ),
    (
        "wf_task_detail",
        "GET",
        "/api/wf/tasks/{id}",
        "org",
        "workflow.task_projection",
        "postgresql_rls_read_projection",
    ),
    (
        "b2b_companies",
        "GET",
        "/api/b2b/companies",
        "erp",
        "b2b.company_directory",
        "postgresql_rls_read_projection",
    ),
    (
        "tender_detail",
        "GET",
        "/api/tender/notices/{id}",
        "erp",
        "procurement.tender_notice",
        "postgresql_rls_read_projection",
    ),
    (
        "shield_diagnose",
        "GET",
        "/api/shield/digest",
        "system",
        "shield.system_observation",
        "provider_observation_with_persisted_evidence",
    ),
    (
        "stocktake_detail",
        "GET",
        "/api/stocktake/{id}",
        "inventory",
        "warehouse.stocktake",
        "postgresql_rls_read_projection",
    ),
    (
        "erp_budget_ledger",
        "GET",
        "/api/erp/budgets/{id}/ledger",
        "erp",
        "erp.budget_ledger_entry",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_accounts",
        "GET",
        "/api/erp/gl/accounts",
        "finance",
        "finance.gl_account",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_assets",
        "GET",
        "/api/erp/gl/assets",
        "finance",
        "finance.fixed_asset",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_tax",
        "GET",
        "/api/erp/gl/tax",
        "finance",
        "finance.tax_ledger",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_posting_failures",
        "GET",
        "/api/erp/gl/posting-failures",
        "finance",
        "finance.posting_failure",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_party_list",
        "GET",
        "/api/erp/finance/parties",
        "finance",
        "finance.party",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_account_list",
        "GET",
        "/api/erp/finance/accounts",
        "finance",
        "finance.cash_account",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_equity_list",
        "GET",
        "/api/erp/finance/equity",
        "finance",
        "finance.equity_ownership",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_fx_list",
        "GET",
        "/api/erp/finance/fx-rates",
        "finance",
        "finance.fx_rate",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_aa_config_get",
        "GET",
        "/api/erp/finance/aa-config",
        "finance",
        "finance.aa_configuration",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_intake_batches",
        "GET",
        "/api/erp/finance/intake-batches",
        "finance",
        "finance.intake_batch",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_intake_list",
        "GET",
        "/api/erp/finance/intake-items",
        "finance",
        "finance.intake_item",
        "postgresql_rls_read_projection",
    ),
    (
        "erp_period_tree",
        "GET",
        "/api/erp/periods",
        "erp",
        "erp.budget_period",
        "postgresql_rls_read_projection",
    ),
    ("people_list", "GET", "/api/collab/people", "org", "iam.tenant_member", "postgresql_rls_read"),
    (
        "msg_inbox",
        "GET",
        "/api/collab/messages",
        "org",
        "collaboration.message",
        "postgresql_rls_read_projection",
    ),
    (
        "collab_edit_list",
        "GET",
        "/api/collab/edit-requests",
        "org",
        "collaboration.edit_request",
        "postgresql_rls_read_projection",
    ),
    (
        "assistant_me",
        "GET",
        "/api/assistant/me",
        "ai",
        "secretariat.assistant_profile",
        "postgresql_rls_read",
    ),
    ("agent_runs_list", "GET", "/api/agent/runs", "ai", "secretariat.run", "postgresql_rls_read"),
    (
        "risk_list",
        "GET",
        "/api/agent/risk-events",
        "ai",
        "shield.ai_risk_review",
        "postgresql_rls_read",
    ),
    (
        "profile_show",
        "GET",
        "/api/agent/profile",
        "ai",
        "secretariat.user_profile",
        "postgresql_rls_read",
    ),
    (
        "lessons_list",
        "GET",
        "/api/agent/lessons",
        "ai",
        "secretariat.procedural_memory",
        "postgresql_rls_read",
    ),
    (
        "knowledge_list",
        "GET",
        "/api/knowledge",
        "ai",
        "secretariat.knowledge_chunk",
        "postgresql_rls_read",
    ),
    (
        "asset_resolve",
        "GET",
        "/api/assets/search",
        "assets",
        "asset.financial",
        "postgresql_rls_read_projection",
    ),
    (
        "asset_analysis_runs",
        "GET",
        "/api/assets/analysis-runs",
        "assets",
        "asset.analysis_run",
        "postgresql_rls_read_projection",
    ),
    (
        "asset_txns",
        "GET",
        "/api/assets/{id}/txns",
        "assets",
        "asset.transaction",
        "postgresql_rls_read_projection",
    ),
    (
        "digital_market_orders",
        "GET",
        "/api/digital-assets/orders",
        "dam",
        "digital_asset.market_order",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_statement_drilldown",
        "GET",
        "/api/erp/gl/drilldown",
        "finance",
        "finance.voucher_line",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_equity_change",
        "GET",
        "/api/erp/gl/equity-change",
        "finance",
        "finance.equity_change",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_notes",
        "GET",
        "/api/erp/gl/notes",
        "finance",
        "finance.statement_note",
        "postgresql_rls_read_projection",
    ),
    (
        "fin_equity_graph",
        "GET",
        "/api/erp/gl/equity-graph",
        "finance",
        "finance.equity_ownership",
        "postgresql_rls_read_projection",
    ),
    (
        "compliance_by_subject",
        "GET",
        "/api/compliance/by-subject",
        "records",
        "compliance.subject_review",
        "postgresql_rls_read_projection",
    ),
    (
        "compliance_cert",
        "GET",
        "/api/compliance/cert",
        "records",
        "compliance.certificate",
        "postgresql_rls_read_projection",
    ),
    (
        "notifications_summary",
        "GET",
        "/api/notifications/summary",
        "org",
        "notification.summary",
        "postgresql_rls_read_projection",
    ),
    (
        "datahub_jobs",
        "GET",
        "/api/datahub/jobs",
        "system",
        "datahub.import_job",
        "postgresql_rls_read_projection",
    ),
)

for (
    _tool_name,
    _api_method,
    _api_path,
    _domain,
    _semantic_resource,
    _verification,
) in _RETAINED_READ_ADAPTERS:
    if _tool_name not in _SUPPORTED_LEGACY_READS:
        raise RuntimeError(f"retained read handler is not implemented: {_tool_name}")
    _register(
        VerifiedCapabilityAdapter(
            tool_name=_tool_name,
            api_method=_api_method,
            api_path=_api_path,
            effect="read",
            domain=_domain,
            semantic_resource=_semantic_resource,
            verification=_verification,
            handler=_retained_read_handler(_tool_name),
        )
    )


_RETAINED_CAPABILITY_CONTRACT_SHA256 = (
    "c19ef2c042f554a4d70a08dabe06482b7475e4790a45305d58243a81aa3e0b96"
)
_retained_contract_rows: list[list[object]] = []
_retained_entries: dict[str, dict[str, object]] = {}
for _entry in _legacy_catalog.COMMANDS:
    if _entry["tool_name"] not in _SUPPORTED_CAPABILITY_TOOLS:
        continue
    _confirmation_mode = str(_legacy_catalog.confirmation_contract(_entry)["mode"])
    _retained_contract_rows.append(
        [
            _entry["tool_name"],
            _entry["api_method"],
            _entry["api_path"],
            bool(_entry["writes"]),
            _confirmation_mode,
        ]
    )
    _retained_entries[str(_entry["tool_name"])] = _entry
_retained_contract_digest = hashlib.sha256(
    json.dumps(_retained_contract_rows, separators=(",", ":")).encode()
).hexdigest()
if _retained_contract_digest != _RETAINED_CAPABILITY_CONTRACT_SHA256:
    raise RuntimeError("retained capability contract changed without adapter review")
if set(_retained_entries) != set(_SUPPORTED_CAPABILITY_TOOLS):
    raise RuntimeError("retained capability registry and catalogue do not match")


def _retained_capability_handler(tool_name: str, confirmation_mode: str) -> AdapterHandler:
    def execute(
        actor: ActorContext,
        values: Mapping[str, object],
        origin: str,
    ) -> object:
        return execute_retained_capability(
            tool_name,
            actor,
            dict(values),
            origin=origin,
            confirmation_mode=confirmation_mode,
        )

    return execute


for _tool_name in sorted(_SUPPORTED_CAPABILITY_TOOLS):
    _entry = _retained_entries[_tool_name]
    _writes = bool(_entry["writes"])
    _confirmation_mode = str(_legacy_catalog.confirmation_contract(_entry)["mode"])
    _register(
        VerifiedCapabilityAdapter(
            tool_name=_tool_name,
            api_method=str(_entry["api_method"]),
            api_path=str(_entry["api_path"]),
            effect="write" if _writes else "read",
            domain=str(_legacy_catalog.capability_summary(_entry)["category"]),
            semantic_resource=_capability_semantic_resource(_tool_name),
            verification=(
                "named_native_or_provider_read"
                if not _writes
                else "passkey_verified_postgresql_event_and_readback"
                if _confirmation_mode == "passkey"
                else "workflow_confirmed_postgresql_event_and_readback"
                if _confirmation_mode == "domain_workflow"
                else "postgresql_rls_atomic_event_and_readback"
            ),
            handler=_retained_capability_handler(_tool_name, _confirmation_mode),
        )
    )


def verified_adapter(entry: Mapping[str, object]) -> VerifiedCapabilityAdapter | None:
    """Return an adapter only when its frozen catalogue contract still matches."""

    adapter = _ADAPTERS.get(str(entry.get("tool_name") or ""))
    if adapter is None:
        return None
    expected = (
        adapter.api_method,
        adapter.api_path,
        adapter.effect == "write",
    )
    actual = (
        str(entry.get("api_method") or "").upper(),
        str(entry.get("api_path") or ""),
        bool(entry.get("writes")),
    )
    return adapter if actual == expected else None


def verified_adapter_ready(entry: Mapping[str, object]) -> bool:
    return verified_adapter(entry) is not None


def execute_verified_adapter(
    entry: Mapping[str, object],
    actor: ActorContext,
    values: Mapping[str, object],
    *,
    origin: str,
) -> object:
    adapter = verified_adapter(entry)
    if adapter is None:
        raise RuntimeError("verified capability adapter is not ready")
    return adapter.handler(actor, values, origin)


def verified_adapter_snapshot() -> dict[str, object]:
    adapters = tuple(_ADAPTERS.values())
    return {
        "count": len(adapters),
        "read_count": sum(adapter.effect == "read" for adapter in adapters),
        "write_count": sum(adapter.effect == "write" for adapter in adapters),
        "domains": sorted({adapter.domain for adapter in adapters}),
        "tool_names": sorted(adapter.tool_name for adapter in adapters),
    }
