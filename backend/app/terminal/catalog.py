"""Versioned command catalogue and its activation boundary.

`legacy_catalog` deliberately keeps every imported command contract as an
institutional record.  Discovery and execution readiness are independent:
only concrete FastAPI domain adapters are active, while structurally routable
legacy projections remain visible as awaiting a domain adapter.  Retired
contracts remain human-searchable but unavailable, and platform contracts
remain separate until their L11 identity reaches the boundary.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from app.terminal import legacy_catalog
from app.terminal.adapters import verified_adapter, verified_adapter_ready
from app.terminal.gateway import gateway_contract_ready
from app.terminal.readiness import native_adapter_ready, readiness_snapshot

if TYPE_CHECKING:
    from app.api.deps import ActorContext

CATALOGUE_REVISION = "capability-truth-v11-pages-actions.2026-08-06"
RETIRED_LIFECYCLES = frozenset({"retired_2_0"})


def is_retired(entry: dict[str, Any]) -> bool:
    return str(entry.get("lifecycle") or "") in RETIRED_LIFECYCLES


def tenant_entries() -> tuple[dict[str, Any], ...]:
    return tuple(legacy_catalog.COMMANDS)


def platform_entries() -> tuple[dict[str, Any], ...]:
    return tuple(legacy_catalog.PLATFORM_COMMANDS)


def entry_by_tool_name(tool_name: str, *, platform: bool = False) -> dict[str, Any] | None:
    entries = platform_entries() if platform else tenant_entries()
    return next((entry for entry in entries if entry["tool_name"] == tool_name), None)


def availability(entry: dict[str, Any], *, platform: bool = False) -> str:
    if is_retired(entry):
        return str(entry["lifecycle"])
    if platform:
        # Platform commands are withheld until the L11 ownership model is
        # implemented; an L10 tenant administrator must never receive them.
        return "requires_l11_governance"
    if native_adapter_ready(entry) or verified_adapter_ready(entry):
        return "active"
    if gateway_contract_ready(entry):
        return "awaiting_domain_adapter"
    return "invalid_contract"


def execution_kind(entry: dict[str, Any], *, platform: bool = False) -> str:
    """Describe the current affordance without prescribing an AI workflow."""

    state = availability(entry, platform=platform)
    if state == "active":
        if verified_adapter_ready(entry) and not native_adapter_ready(entry):
            return "verified_adapter"
        return "native_adapter"
    if state == "awaiting_domain_adapter":
        return "capability_gap"
    if state == "requires_l11_governance":
        return "platform_governance"
    if is_retired(entry):
        return "retired"
    return "invalid"


def is_authorized(entry: dict[str, Any], permissions: Iterable[str]) -> bool:
    required = set(legacy_catalog.effective_permissions(entry))
    return not required or bool(required.intersection(permissions))


def command_summary(
    entry: dict[str, Any], actor: ActorContext, *, platform: bool = False
) -> dict[str, object]:
    required = list(legacy_catalog.effective_permissions(entry))
    state = availability(entry, platform=platform)
    authorized = is_authorized(entry, actor.permissions)
    registered_adapter = verified_adapter(entry)
    return {
        "command": entry["command"],
        "tool_name": entry["tool_name"],
        "usage": legacy_catalog.usage_of(entry),
        "description": entry["description"],
        "permission": legacy_catalog.effective_permission(entry),
        "permission_any": required,
        "writes": bool(entry["writes"]),
        "risk": entry["risk"],
        "confirmation_policy": legacy_catalog.confirmation_contract(entry),
        "confirmation_required": legacy_catalog.ai_confirmation_required(entry),
        "execution_identity": str(entry.get("execution_identity") or "company_ai"),
        "authorized": authorized,
        "available": state == "active",
        "adapter": (
            "verified_registry"
            if state == "active" and registered_adapter is not None
            else "fastapi_native"
            if state == "active"
            else None
        ),
        "semantic_resource": (registered_adapter.semantic_resource if registered_adapter else None),
        "semantic_contract": dict(entry.get("semantic_contract") or {}),
        "verification": (registered_adapter.verification if registered_adapter else None),
        "execution_kind": execution_kind(entry, platform=platform),
        "transitional_projection_available": False,
        "contract_match_available": gateway_contract_ready(entry),
        # `allowed` is the legacy terminal field and means callable now.
        "allowed": authorized and state == "active",
        "availability": state,
        "examples": entry["examples"],
    }


def command_catalogue(
    actor: ActorContext, *, include_unavailable: bool = False
) -> list[dict[str, object]]:
    summaries = [command_summary(entry, actor) for entry in tenant_entries()]
    if include_unavailable:
        return summaries
    return [summary for summary in summaries if summary["allowed"]]


def business_action_catalogue(actor: ActorContext) -> list[dict[str, object]]:
    """Project every registered capability into one human/AI action contract.

    The form schema is the exact schema used for model tool calls.  The UI
    therefore cannot drift into a second set of parameter names or business
    validation rules.  Platform capabilities remain discoverable for guidance
    but are never made executable inside a tenant session.
    """
    actions: list[dict[str, object]] = []
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            capability = legacy_catalog.capability_summary(entry)
            state = command_summary(entry, actor, platform=platform)
            function = legacy_catalog.tool_schema(entry)["function"]
            actions.append(
                {
                    **state,
                    "scope": "platform" if platform else "tenant",
                    "category": capability["category"],
                    "category_label": capability["category_label"],
                    "category_order": capability["category_order"],
                    "category_guide": capability["category_guide"],
                    "parameters": function["parameters"],
                    "action_description": function["description"],
                    "manual_execution": (
                        "execute"
                        if state["allowed"] and not state["confirmation_required"]
                        else "governed_confirmation"
                        if state["available"] and state["authorized"]
                        else "unavailable"
                    ),
                }
            )
    return actions


def skill_catalogue(actor: ActorContext) -> list[dict[str, object]]:
    """Expose the historic ability universe for human discovery, not execution.

    The Warehouse command set remains valuable institutional knowledge.  This
    projection intentionally retains its names, descriptions, examples, and
    confirmation semantics as searchable Skills while omitting internal API
    routing details.
    """
    skills: list[dict[str, object]] = []
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            summary = legacy_catalog.capability_summary(entry)
            state = availability(entry, platform=platform)
            authorized = is_authorized(entry, actor.permissions)
            skills.append(
                {
                    "skill_id": summary["tool_name"],
                    "name": summary["command"],
                    "description": summary["description"],
                    "category": summary["category"],
                    "category_label": summary["category_label"],
                    "writes": summary["writes"],
                    "risk": summary["risk"],
                    "arguments": summary["arguments"],
                    "examples": entry.get("examples", []),
                    "state": state,
                    "ready": state == "active" and authorized,
                    "authorized": authorized,
                    "scope": "platform" if platform else "tenant",
                    "invocation": "goal_guided",
                }
            )
    return skills


def migration_summary(actor: ActorContext) -> dict[str, object]:
    entries = tenant_entries()
    active = [entry for entry in entries if availability(entry) == "active"]
    awaiting = [entry for entry in entries if availability(entry) == "awaiting_domain_adapter"]
    invalid = [entry for entry in entries if availability(entry) == "invalid_contract"]
    retired = [entry for entry in entries if is_retired(entry)]
    return {
        "revision": CATALOGUE_REVISION,
        "tenant_command_count": len(entries),
        "platform_command_count": len(platform_entries()),
        "active_tenant_command_count": len(active),
        "retired_tenant_command_count": len(retired),
        "awaiting_domain_adapter_count": len(awaiting),
        "invalid_contract_count": len(invalid),
        "readiness": readiness_snapshot(),
        "platform_state": "requires_l11_governance",
        "commands": command_catalogue(actor, include_unavailable=True),
    }


def ai_tool_schemas() -> list[dict[str, object]]:
    """Return the non-retired capability vocabulary to an AI runtime.

    Discovery is global only for command metadata. It contains no tenant data,
    user list, permission assignment, route secret, or database selector. An
    execution always remains bound to exactly one tenant and its RLS scope.
    A schema does not grant execution authority; that decision remains in the
    execution ledger and server-side policy gate.
    """
    return [
        legacy_catalog.tool_schema(entry)
        for entry in (*tenant_entries(), *platform_entries())
        if not is_retired(entry)
    ]


def ai_capability_states() -> list[dict[str, object]]:
    """Non-secret execution state paired with every AI-visible tool schema."""
    states: list[dict[str, object]] = []
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            if is_retired(entry):
                continue
            states.append(
                {
                    "tool_name": entry["tool_name"],
                    "command": entry["command"],
                    "surface": "platform" if platform else "tenant",
                    "availability": availability(entry, platform=platform),
                    "execution_kind": execution_kind(entry, platform=platform),
                    "writes": bool(entry["writes"]),
                    "confirmation_required": legacy_catalog.ai_confirmation_required(entry),
                    "execution_authority": "ai_policy_decision_required",
                }
            )
    return states


def ai_capability_atlas() -> list[dict[str, object]]:
    """Distil the complete command catalogue into a stable domain map.

    Domains and counts come from command metadata itself.  Adding a capability
    gene automatically changes the atlas; the Runtime does not carry a second
    hard-coded list of business abilities.
    """
    groups: dict[tuple[str, str], dict[str, object]] = {}
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            if is_retired(entry):
                continue
            summary = legacy_catalog.capability_summary(entry)
            category = str(summary["category"])
            label = str(summary["category_label"])
            key = ("platform" if platform else "tenant", category)
            group = groups.setdefault(
                key,
                {
                    "domain": category,
                    "label": label,
                    "scope": key[0],
                    "kind": "capability_domain",
                    "gene_count": 0,
                    "active_count": 0,
                    "write_count": 0,
                    "states": set(),
                    "command_families": set(),
                },
            )
            state = availability(entry, platform=platform)
            family = str(entry["command"]).strip().split(maxsplit=1)[0]
            group["gene_count"] = int(group["gene_count"]) + 1
            group["active_count"] = int(group["active_count"]) + int(state == "active")
            group["write_count"] = int(group["write_count"]) + int(bool(entry["writes"]))
            group["states"].add(state)
            if family:
                group["command_families"].add(family)
    return [
        {
            **group,
            "states": sorted(group["states"]),
            "command_families": sorted(group["command_families"]),
        }
        for _, group in sorted(groups.items())
    ]


def ai_capability_gene_index() -> list[dict[str, object]]:
    """Return compact metadata for every non-retired model-discovery gene."""
    genes: list[dict[str, object]] = []
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            if is_retired(entry):
                continue
            summary = legacy_catalog.capability_summary(entry)
            genes.append(
                {
                    "tool_name": entry["tool_name"],
                    "command": entry["command"],
                    "domain": summary["category"],
                    "description": summary["description"],
                    "scope": "platform" if platform else "tenant",
                    "availability": availability(entry, platform=platform),
                    "execution_kind": execution_kind(entry, platform=platform),
                    "permission_any": list(legacy_catalog.effective_permissions(entry)),
                    "writes": bool(entry["writes"]),
                    "risk": entry["risk"],
                    "confirmation_required": legacy_catalog.ai_confirmation_required(entry),
                    "execution_identity": str(entry.get("execution_identity") or "company_ai"),
                    "semantic_contract": dict(entry.get("semantic_contract") or {}),
                }
            )
    return genes


def ai_capability_candidates(
    query: str,
    *,
    limit: int = 8,
) -> list[dict[str, object]]:
    """Return bounded catalogue search hints for the model router.

    Matching is discovery only: it neither selects nor authorizes a command.
    The model still chooses the domain/gene and the execution boundary still
    reloads live tenant authority.
    """
    entries = tuple(
        entry for entry in (*tenant_entries(), *platform_entries()) if not is_retired(entry)
    )
    matches = legacy_catalog.search_capability_entries(
        entries,
        query,
        limit=limit,
    )
    by_name = {str(entry["tool_name"]): entry for entry in entries}
    platform_tool_names = {str(entry["tool_name"]) for entry in platform_entries()}
    candidates: list[dict[str, object]] = []
    for match in matches:
        tool_name = str(match.get("tool_name") or "")
        entry = by_name.get(tool_name)
        if entry is None:
            continue
        summary = legacy_catalog.capability_summary(entry)
        candidates.append(
            {
                "tool_name": tool_name,
                "command": summary["command"],
                "domain": summary["category"],
                "description": summary["description"],
                "writes": summary["writes"],
                "confirmation_required": (legacy_catalog.ai_confirmation_required(entry)),
                "availability": availability(
                    entry,
                    platform=tool_name in platform_tool_names,
                ),
                "execution_kind": execution_kind(
                    entry,
                    platform=tool_name in platform_tool_names,
                ),
            }
        )
    return candidates


def ai_capability_genes(tool_names: Iterable[str]) -> list[dict[str, object]]:
    """Expand model-selected genes without granting or executing them."""
    wanted = {str(name) for name in tool_names if str(name).strip()}
    states = {row["tool_name"]: row for row in ai_capability_states()}
    genes: list[dict[str, object]] = []
    for entry in (*tenant_entries(), *platform_entries()):
        if is_retired(entry) or entry["tool_name"] not in wanted:
            continue
        genes.append(
            {
                "schema": legacy_catalog.tool_schema(entry),
                "state": states[entry["tool_name"]],
                "permission_any": list(legacy_catalog.effective_permissions(entry)),
                "confirmation_policy": legacy_catalog.confirmation_contract(entry),
                "examples": entry.get("examples") or [],
            }
        )
    return genes
