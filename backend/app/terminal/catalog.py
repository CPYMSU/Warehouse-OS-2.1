"""Versioned command catalogue and its activation boundary.

`legacy_catalog` deliberately keeps every imported command contract.  A
contract is not executable merely because it is catalogued: an adapter must be
registered against the new PostgreSQL domain model before it becomes visible
to the terminal or an AI tool caller.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any

from app.terminal import legacy_catalog

if TYPE_CHECKING:
    from app.api.deps import ActorContext

CATALOGUE_REVISION = "legacy-441.2026-07-27"

# These adapters use only the new PostgreSQL domain model.  Every other
# imported contract remains queryable for migration work but fails closed.
ACTIVE_TENANT_TOOLS = frozenset({"auth_me", "warehouse_list"})


def tenant_entries() -> tuple[dict[str, Any], ...]:
    return tuple(legacy_catalog.COMMANDS)


def platform_entries() -> tuple[dict[str, Any], ...]:
    return tuple(legacy_catalog.PLATFORM_COMMANDS)


def entry_by_tool_name(tool_name: str, *, platform: bool = False) -> dict[str, Any] | None:
    entries = platform_entries() if platform else tenant_entries()
    return next((entry for entry in entries if entry["tool_name"] == tool_name), None)


def availability(entry: dict[str, Any], *, platform: bool = False) -> str:
    if platform:
        # Platform commands are withheld until the L11 ownership model is
        # implemented; an L10 tenant administrator must never receive them.
        return "requires_l11_governance"
    if entry.get("tool_name") in ACTIVE_TENANT_TOOLS:
        return "active"
    return "awaiting_domain_adapter"


def is_authorized(entry: dict[str, Any], permissions: Iterable[str]) -> bool:
    required = set(legacy_catalog.effective_permissions(entry))
    return not required or bool(required.intersection(permissions))


def command_summary(
    entry: dict[str, Any], actor: ActorContext, *, platform: bool = False
) -> dict[str, object]:
    required = list(legacy_catalog.effective_permissions(entry))
    state = availability(entry, platform=platform)
    authorized = is_authorized(entry, actor.permissions)
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
        "authorized": authorized,
        "available": state == "active",
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


def migration_summary(actor: ActorContext) -> dict[str, object]:
    entries = tenant_entries()
    active = [entry for entry in entries if availability(entry) == "active"]
    return {
        "revision": CATALOGUE_REVISION,
        "tenant_command_count": len(entries),
        "platform_command_count": len(platform_entries()),
        "active_tenant_command_count": len(active),
        "awaiting_domain_adapter_count": len(entries) - len(active),
        "platform_state": "requires_l11_governance",
        "commands": command_catalogue(actor, include_unavailable=True),
    }


def ai_tool_schemas() -> list[dict[str, object]]:
    """Return the whole non-tenant capability vocabulary to an AI runtime.

    Discovery is global only for command metadata. It contains no tenant data,
    user list, permission assignment, route secret, or database selector. An
    execution always remains bound to exactly one tenant and its RLS scope.
    A schema does not grant execution authority; that decision remains in the
    execution ledger and server-side policy gate.
    """
    return [
        legacy_catalog.tool_schema(entry)
        for entry in (*tenant_entries(), *platform_entries())
    ]


def ai_capability_states() -> list[dict[str, object]]:
    """Non-secret execution state paired with every AI-visible tool schema."""
    states: list[dict[str, object]] = []
    for platform, entries in ((False, tenant_entries()), (True, platform_entries())):
        for entry in entries:
            states.append(
                {
                    "tool_name": entry["tool_name"],
                    "command": entry["command"],
                    "surface": "platform" if platform else "tenant",
                    "availability": availability(entry, platform=platform),
                    "writes": bool(entry["writes"]),
                    "confirmation_required": legacy_catalog.ai_confirmation_required(entry),
                    "execution_authority": "ai_policy_decision_required",
                }
            )
    return states
